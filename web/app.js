/**
 * Telepresence Manager — Frontend Logic
 * Calls Python API via pywebview's js_api bridge.
 */

// pywebview API reference (set after window is ready)
let api = null;

// State
let contexts = [];
let expandedStatus = new Set(); // Track which cards have status panel open
let autoRefreshTimer = null;
const AUTO_REFRESH_INTERVAL = 30000; // 30s

// === Initialization ===

window.addEventListener('pywebviewready', () => {
    api = window.pywebview.api;
    checkTools();
    scanConfigs();
    checkForUpdate();
    setupKeyboardShortcuts();
});

// === Update Check ===

async function checkForUpdate() {
    try {
        const res = await api.check_update();
        if (res.available) {
            showUpdateBanner(res.latest_version, res.body);
        }
    } catch (e) {
        // Silent fail — update check is non-critical
    }
}

function showUpdateBanner(version, releaseNotes) {
    // Don't show if already dismissed this session
    if (sessionStorage.getItem('updateDismissed')) return;

    const main = document.querySelector('.main');
    const existing = document.getElementById('updateBanner');
    if (existing) existing.remove();

    // Extract first few lines of release notes
    let notesExcerpt = '';
    if (releaseNotes) {
        const lines = releaseNotes.split('\n').filter(l => l.trim().startsWith('-')).slice(0, 5);
        notesExcerpt = lines.map(l => l.replace(/^-\s*\*\*([^*]+)\*\*:?\s*/, '$1: ')).join('；');
    }

    const banner = document.createElement('div');
    banner.id = 'updateBanner';
    banner.className = 'update-banner';
    banner.innerHTML = `
        <div class="update-banner-content">
            <div class="update-banner-text">
                <span class="update-banner-title">🆕 发现新版本 v${escapeHtml(version)}</span>
                ${notesExcerpt ? `<span class="update-banner-notes">${escapeHtml(notesExcerpt)}</span>` : ''}
            </div>
            <div class="update-banner-actions">
                <button class="btn btn-primary btn-sm" onclick="startUpdate()">立即更新</button>
                <button class="btn btn-sm" onclick="dismissUpdate()">稍后</button>
            </div>
        </div>
        <div class="update-progress hidden" id="updateProgress">
            <div class="update-progress-bar" id="updateProgressBar"></div>
            <span class="update-progress-text" id="updateProgressText">下载中... 0%</span>
        </div>
    `;
    main.prepend(banner);
}

function dismissUpdate() {
    const banner = document.getElementById('updateBanner');
    if (banner) banner.remove();
    sessionStorage.setItem('updateDismissed', '1');
}

async function startUpdate() {
    const progressEl = document.getElementById('updateProgress');
    const barEl = document.getElementById('updateProgressBar');
    const textEl = document.getElementById('updateProgressText');
    const actionsEl = document.querySelector('.update-banner-actions');

    // Hide action buttons, show progress
    actionsEl.style.display = 'none';
    progressEl.classList.remove('hidden');
    textEl.textContent = '准备下载...';

    // Poll for download progress via a separate status check
    // Since pywebview JS API is synchronous per call, we'll show indeterminate progress
    try {
        showToast('正在下载更新，完成后将自动重启...', 'info', 10000);
        barEl.style.width = '50%';
        textEl.textContent = '下载中...';

        const res = await api.download_and_update();

        // If we reach here, update failed (success means the process exits)
        barEl.style.width = '100%';
        barEl.style.background = 'var(--danger)';
        textEl.textContent = '更新失败: ' + (res.message || '未知错误');
        actionsEl.style.display = '';
        showToast('更新失败: ' + (res.message || '未知错误'), 'error');
    } catch (e) {
        // This may fire if the process exits during download — that's expected
        barEl.style.width = '100%';
        barEl.style.background = 'var(--success)';
        textEl.textContent = '正在重启...';
    }
}

// === Keyboard Shortcuts ===

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl+R or F5: scan configs
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            e.preventDefault();
            scanConfigs();
        }
        // Escape: close panels
        if (e.key === 'Escape') {
            closeToolDetailPanel();
            closeConfirmDialog();
        }
        // Ctrl+F: focus search
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const input = document.getElementById('searchInput');
            if (input) input.focus();
        }
    });
}

// === Toast Notifications ===

function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fadeOut');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// === Confirm Dialog ===

function showConfirm(title, message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';
        overlay.innerHTML = `
            <div class="confirm-dialog">
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(message)}</p>
                <div class="confirm-actions">
                    <button class="btn btn-sm" id="confirmCancel">取消</button>
                    <button class="btn btn-sm btn-danger" id="confirmOk">确认</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const cleanup = (result) => {
            overlay.remove();
            resolve(result);
        };

        overlay.querySelector('#confirmCancel').onclick = () => cleanup(false);
        overlay.querySelector('#confirmOk').onclick = () => cleanup(true);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) cleanup(false);
        });
    });
}

function closeConfirmDialog() {
    const overlay = document.querySelector('.confirm-overlay');
    if (overlay) overlay.remove();
}

// === Tool Check ===

let toolsInfo = null;

async function checkTools() {
    const el = document.getElementById('toolsStatus');
    try {
        const res = await api.check_tools();
        toolsInfo = res;
        if (res.telepresence && res.kubectl) {
            const tpVer = _extractVersion(res.telepresence_version, 'OSS Client');
            const kcVer = _extractVersion(res.kubectl_version, 'Client Version');
            el.innerHTML = `<span class="tool-ok">✓</span> TP ${tpVer} · kubectl ${kcVer} <span class="tool-detail-btn" onclick="toggleToolDetail()">ℹ</span>`;
            el.className = 'tools-status ok';
        } else {
            const missing = [];
            if (!res.telepresence) missing.push('telepresence');
            if (!res.kubectl) missing.push('kubectl');
            el.textContent = `✗ 缺少: ${missing.join(', ')}`;
            el.className = 'tools-status error';
            showToast(`缺少工具: ${missing.join(', ')}`, 'error', 5000);
        }
    } catch (e) {
        el.textContent = '✗ 检测失败';
        el.className = 'tools-status error';
        showToast('工具检测失败', 'error');
    }
}

function _extractVersion(fullStr, key) {
    if (!fullStr) return 'N/A';
    for (const line of fullStr.split('\n')) {
        if (line.includes(key)) {
            const match = line.match(/v?[\d]+\.[\d]+\.[\d]+[\w.-]*/);
            if (match) return match[0];
        }
    }
    const match = fullStr.match(/v?[\d]+\.[\d]+\.[\d]+[\w.-]*/);
    return match ? match[0] : fullStr.split('\n')[0];
}

function toggleToolDetail() {
    let panel = document.getElementById('toolDetailPanel');
    if (panel) {
        panel.remove();
        return;
    }
    if (!toolsInfo) return;

    panel = document.createElement('div');
    panel.id = 'toolDetailPanel';
    panel.className = 'tool-detail-panel';
    panel.innerHTML = `
        <div class="tool-detail-row">
            <span class="tool-detail-label">Telepresence</span>
            <span class="tool-detail-value ${toolsInfo.telepresence ? 'ok' : 'error'}">${toolsInfo.telepresence ? '已安装' : '未安装'}</span>
        </div>
        ${toolsInfo.telepresence_version ? `<div class="tool-detail-row">
            <span class="tool-detail-label">  版本</span>
            <span class="tool-detail-value">${escapeHtml(toolsInfo.telepresence_version.split('\n')[0])}</span>
        </div>` : ''}
        ${toolsInfo.telepresence_path ? `<div class="tool-detail-row">
            <span class="tool-detail-label">  路径</span>
            <span class="tool-detail-value path">${escapeHtml(toolsInfo.telepresence_path)}</span>
        </div>` : ''}
        <div class="tool-detail-row">
            <span class="tool-detail-label">kubectl</span>
            <span class="tool-detail-value ${toolsInfo.kubectl ? 'ok' : 'error'}">${toolsInfo.kubectl ? '已安装' : '未安装'}</span>
        </div>
        ${toolsInfo.kubectl_version ? `<div class="tool-detail-row">
            <span class="tool-detail-label">  版本</span>
            <span class="tool-detail-value">${escapeHtml(toolsInfo.kubectl_version.split('\n')[0])}</span>
        </div>` : ''}
        ${toolsInfo.kubectl_path ? `<div class="tool-detail-row">
            <span class="tool-detail-label">  路径</span>
            <span class="tool-detail-value path">${escapeHtml(toolsInfo.kubectl_path)}</span>
        </div>` : ''}
    `;
    document.querySelector('.header-right').appendChild(panel);

    setTimeout(() => {
        document.addEventListener('click', _closeToolDetail, { once: true });
    }, 0);
}

function _closeToolDetail(e) {
    const panel = document.getElementById('toolDetailPanel');
    if (panel && !panel.contains(e.target) && !e.target.classList.contains('tool-detail-btn')) {
        panel.remove();
    }
}

function closeToolDetailPanel() {
    const panel = document.getElementById('toolDetailPanel');
    if (panel) panel.remove();
}

// === Scan Configs ===

async function scanConfigs() {
    const btn = document.getElementById('btnScan');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 扫描中...';
    setFooter('正在扫描 ~/.kube/ 配置文件...');

    try {
        const res = await api.scan_configs();
        contexts = res.contexts || [];
        renderList();
        setFooter(`扫描完成，发现 ${contexts.length} 个 context`);

        // Check existing connections on startup / re-scan
        checkExistingConnections();
    } catch (e) {
        setFooter('扫描失败: ' + e.message);
        showToast('扫描配置失败', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '⟳ 扫描配置';
    }
}

// === Search / Filter ===

function filterContexts() {
    const query = document.getElementById('searchInput').value.toLowerCase().trim();
    const cards = document.querySelectorAll('.context-card');
    let visibleCount = 0;

    cards.forEach(card => {
        const name = (card.dataset.ctxName || '').toLowerCase();
        const cluster = (card.dataset.ctxCluster || '').toLowerCase();
        const server = (card.dataset.ctxServer || '').toLowerCase();
        const source = (card.dataset.ctxSource || '').toLowerCase();

        const match = !query || name.includes(query) || cluster.includes(query) || server.includes(query) || source.includes(query);
        card.classList.toggle('hidden', !match);
        if (match) visibleCount++;
    });

    // Show/hide empty state
    const container = document.getElementById('configList');
    let noResult = container.querySelector('.no-result');
    if (query && visibleCount === 0) {
        if (!noResult) {
            noResult = document.createElement('div');
            noResult.className = 'empty-state no-result';
            noResult.innerHTML = '<p>没有匹配的 context</p>';
            container.appendChild(noResult);
        }
    } else if (noResult) {
        noResult.remove();
    }
}

// === Auto Refresh ===

function startAutoRefresh() {
    if (autoRefreshTimer) return;
    autoRefreshTimer = setInterval(async () => {
        if (contexts.length === 0) return;
        try {
            // Check telepresence status silently
            const status = await api.get_status();
            updateConnectionDots(status);
        } catch (e) {
            // Silent fail for auto-refresh
        }
    }, AUTO_REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
    }
}

function updateConnectionDots(tpStatus) {
    if (!tpStatus) return;
    const isConnected = tpStatus.connected;

    // Update all cards based on global telepresence status
    contexts.forEach((ctx, idx) => {
        const dot = document.getElementById(`dot-${idx}`);
        const btn = document.getElementById(`btn-conn-${idx}`);
        if (!dot || !btn) return;

        if (isConnected) {
            dot.className = 'dot connected';
            btn.innerHTML = '■ 断开';
            btn.className = 'btn btn-danger btn-sm';
        } else {
            dot.className = 'dot';
            btn.innerHTML = '▶ 连接';
            btn.className = 'btn btn-success btn-sm';
        }
    });
}

async function checkExistingConnections() {
    try {
        const status = await api.get_status();
        if (status.connected) {
            updateConnectionDots(status);
            showToast('检测到已有 Telepresence 连接', 'info');
        }
        startAutoRefresh();
    } catch (e) {
        // Silent fail
    }
}

// === Render Context List ===

function renderList() {
    const container = document.getElementById('configList');

    if (contexts.length === 0) {
        container.innerHTML = '';
        container.appendChild(createEmptyState());
        stopAutoRefresh();
        return;
    }

    // Reconcile: reuse existing cards where possible
    const existingCards = container.querySelectorAll('.context-card');
    const existingMap = new Map();
    existingCards.forEach(card => {
        const name = card.dataset.ctxName;
        if (name) existingMap.set(name, card);
    });

    const newNames = new Set(contexts.map(c => c.name));

    // Remove cards that no longer exist
    existingCards.forEach(card => {
        if (!newNames.has(card.dataset.ctxName)) {
            card.remove();
        }
    });

    // Remove empty state if present
    const emptyState = container.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    // Add or update cards in order
    let prevSibling = null;
    contexts.forEach((ctx, idx) => {
        const existing = existingMap.get(ctx.name);
        if (existing) {
            _updateCardData(existing, ctx, idx);
            if (prevSibling && existing.previousElementSibling !== prevSibling) {
                prevSibling.after(existing);
            }
            prevSibling = existing;
        } else {
            const card = createContextCard(ctx, idx);
            if (prevSibling) {
                prevSibling.after(card);
            } else {
                container.prepend(card);
            }
            prevSibling = card;
        }
    });

    // Restore expanded status panels
    expandedStatus.forEach(name => {
        const idx = contexts.findIndex(c => c.name === name);
        if (idx >= 0) {
            const statusEl = document.getElementById(`status-${idx}`);
            if (statusEl) {
                statusEl.classList.remove('hidden');
                refreshStatus(idx, true); // silent refresh
            }
        }
    });
}

function _updateCardData(card, ctx, idx) {
    card.id = `card-${idx}`;
    card.dataset.ctxName = ctx.name;
    card.dataset.ctxCluster = ctx.cluster;
    card.dataset.ctxServer = ctx.server || '';
    card.dataset.ctxSource = ctx.source_file;

    // Update badge
    const badge = card.querySelector('.card-badge');
    if (badge) badge.textContent = ctx.cluster;

    // Update current badge
    let currentBadge = card.querySelector('.card-current-badge');
    if (ctx.is_current) {
        if (!currentBadge) {
            currentBadge = document.createElement('span');
            currentBadge.className = 'card-badge card-current-badge';
            currentBadge.style.color = 'var(--accent)';
            currentBadge.textContent = '当前';
            card.querySelector('.card-name').appendChild(currentBadge);
        }
    } else if (currentBadge) {
        currentBadge.remove();
    }

    // Update meta
    const metaSpans = card.querySelectorAll('.card-meta span');
    if (metaSpans[0]) {
        metaSpans[0].innerHTML = `🌐 <span class="url-text">${escapeHtml(ctx.server || 'N/A')}</span>`;
    }
    if (metaSpans[1]) metaSpans[1].textContent = `📁 ${shortenPath(ctx.source_file)}`;

    // Update button handlers with new index
    const connBtn = card.querySelector(`[id^="btn-conn-"]`);
    if (connBtn) {
        connBtn.id = `btn-conn-${idx}`;
        connBtn.setAttribute('onclick', `toggleConnect(${idx})`);
    }
    const statusBtn = card.querySelector(`[id^="btn-status-"]`);
    if (statusBtn) {
        statusBtn.id = `btn-status-${idx}`;
        statusBtn.setAttribute('onclick', `refreshStatus(${idx})`);
    }
    const shellBtn = card.querySelector('.card-actions .btn:nth-child(2)');
    if (shellBtn) {
        shellBtn.setAttribute('onclick', `openShell(${idx})`);
    }
    const copyBtn = card.querySelector('.card-actions .btn-icon');
    if (copyBtn) {
        copyBtn.setAttribute('onclick', `copyContextName(${idx})`);
    }

    // Update status panel id
    const statusEl = card.querySelector('.card-status');
    if (statusEl) statusEl.id = `status-${idx}`;

    // Update dot id
    const dot = card.querySelector('.dot');
    if (dot) dot.id = `dot-${idx}`;
}

function createEmptyState() {
    const div = document.createElement('div');
    div.className = 'empty-state';
    div.innerHTML = `
        <p>未找到 K8s 配置</p>
        <div class="hint">
            请确认 <code>~/.kube/</code> 目录下存在配置文件：<br>
            <code>config</code>、<code>*.yaml</code>、<code>*.yml</code>、<code>*.txt</code><br><br>
            或通过以下命令生成：<br>
            <code>kubectl config view --flatten > ~/.kube/config</code>
        </div>
    `;
    return div;
}

function createContextCard(ctx, idx) {
    const card = document.createElement('div');
    card.className = 'context-card';
    card.id = `card-${idx}`;
    card.dataset.ctxName = ctx.name;
    card.dataset.ctxCluster = ctx.cluster;
    card.dataset.ctxServer = ctx.server || '';
    card.dataset.ctxSource = ctx.source_file;

    const currentBadge = ctx.is_current
        ? '<span class="card-badge card-current-badge" style="color:var(--accent)">当前</span>'
        : '';

    card.innerHTML = `
        <div class="card-top">
            <div class="card-name">
                <span class="dot" id="dot-${idx}"></span>
                <h3>${escapeHtml(ctx.name)}</h3>
                ${currentBadge}
            </div>
            <span class="card-badge">${escapeHtml(ctx.cluster)}</span>
        </div>
        <div class="card-meta">
            <span>🌐 <span class="url-text">${escapeHtml(ctx.server || 'N/A')}</span></span>
            <span>📁 ${escapeHtml(shortenPath(ctx.source_file))}</span>
        </div>
        <div class="card-actions">
            <button class="btn btn-success btn-sm" id="btn-conn-${idx}" onclick="toggleConnect(${idx})">
                ▶ 连接
            </button>
            <button class="btn btn-sm" onclick="openShell(${idx})">
                >_ 命令行
            </button>
            <button class="btn btn-sm" id="btn-status-${idx}" onclick="refreshStatus(${idx})">
                ⟳ 状态
            </button>
            <button class="btn-icon" onclick="copyContextName(${idx})" title="复制 context 名称">📋</button>
        </div>
        <div class="card-status hidden" id="status-${idx}"></div>
    `;
    return card;
}

// === Copy ===

async function copyContextName(idx) {
    const ctx = contexts[idx];
    try {
        await navigator.clipboard.writeText(ctx.name);
        showToast(`已复制: ${ctx.name}`, 'success', 2000);
    } catch (e) {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = ctx.name;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        textarea.remove();
        showToast(`已复制: ${ctx.name}`, 'success', 2000);
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(`已复制`, 'success', 2000);
    }).catch(() => {});
}

// === Connect / Disconnect ===

async function toggleConnect(idx) {
    const ctx = contexts[idx];
    const btn = document.getElementById(`btn-conn-${idx}`);
    const dot = document.getElementById(`dot-${idx}`);

    const isCurrentlyConnected = dot.classList.contains('connected');

    // Confirm disconnect
    if (isCurrentlyConnected) {
        const confirmed = await showConfirm(
            '断开连接',
            `确认断开 Telepresence 连接？当前连接的 context 可能正在使用中。`
        );
        if (!confirmed) return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>';

    if (isCurrentlyConnected) {
        setFooter('正在断开 telepresence...');
        dot.className = 'dot';
        try {
            const res = await api.disconnect();
            if (res.success) {
                btn.innerHTML = '▶ 连接';
                btn.className = 'btn btn-success btn-sm';
                setFooter('已断开连接');
                showToast('已断开 Telepresence 连接', 'success');
            } else {
                dot.className = 'dot connected';
                setFooter('断开失败: ' + res.message);
                showToast('断开失败: ' + res.message, 'error');
            }
        } catch (e) {
            dot.className = 'dot connected';
            setFooter('断开失败: ' + e.message);
            showToast('断开失败', 'error');
        }
    } else {
        setFooter(`正在连接 ${ctx.name}...`);
        dot.className = 'dot connecting';
        try {
            const res = await api.connect(ctx.name, ctx.source_file);
            if (res.success) {
                dot.className = 'dot connected';
                btn.innerHTML = '■ 断开';
                btn.className = 'btn btn-danger btn-sm';
                setFooter(`已连接到 ${ctx.name}`);
                showToast(`已连接到 ${ctx.name}`, 'success');
            } else {
                dot.className = 'dot';
                btn.innerHTML = '▶ 连接';
                setFooter('连接失败: ' + res.message);
                showToast('连接失败: ' + res.message, 'error');
            }
        } catch (e) {
            dot.className = 'dot';
            btn.innerHTML = '▶ 连接';
            setFooter('连接失败: ' + e.message);
            showToast('连接失败', 'error');
        }
    }

    btn.disabled = false;
}

// === Open Shell ===

async function openShell(idx) {
    const ctx = contexts[idx];
    setFooter(`正在为 ${ctx.name} 打开命令行...`);
    try {
        const res = await api.open_shell(ctx.name, ctx.source_file);
        if (res.success) {
            setFooter(`已打开命令行 (${ctx.name})`);
            showToast(`已打开命令行: ${ctx.name}`, 'success', 2000);
        } else {
            setFooter('打开失败: ' + res.message);
            showToast('打开命令行失败: ' + res.message, 'error');
        }
    } catch (e) {
        setFooter('打开失败: ' + e.message);
        showToast('打开命令行失败', 'error');
    }
}

// === Status ===

async function refreshStatus(idx, silent = false) {
    const ctx = contexts[idx];
    const statusEl = document.getElementById(`status-${idx}`);
    const btn = document.getElementById(`btn-status-${idx}`);

    // Toggle: if already visible and not silent refresh, hide it
    if (!silent && !statusEl.classList.contains('hidden')) {
        statusEl.classList.add('hidden');
        statusEl.innerHTML = '';
        btn.innerHTML = '⟳ 状态';
        expandedStatus.delete(ctx.name);
        return;
    }

    // Mark as expanded
    expandedStatus.add(ctx.name);
    statusEl.classList.remove('hidden');
    if (!silent) {
        statusEl.innerHTML = '<span class="spinner"></span> 查询中...';
        btn.innerHTML = '✕ 收起';
        setFooter(`正在查询 ${ctx.name} 状态...`);
    }

    try {
        const res = await api.get_full_status(ctx.name, ctx.source_file);
        renderStatus(idx, ctx, res);
        if (!silent) {
            setFooter(`状态查询完成 (${ctx.name})`);
        }
    } catch (e) {
        statusEl.innerHTML = `<div class="status-value error">查询失败: ${escapeHtml(e.message)}</div>`;
        if (!silent) {
            setFooter('状态查询失败');
            showToast('状态查询失败', 'error');
        }
    }
}

async function installTrafficManager(idx) {
    const ctx = contexts[idx];
    const btn = document.getElementById(`btn-tm-install-${idx}`);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 安装中...';
    setFooter(`正在为 ${ctx.name} 安装 Traffic Manager...`);
    showToast(`正在安装 Traffic Manager...`, 'info', 5000);

    try {
        const res = await api.install_traffic_manager(ctx.name, ctx.source_file);
        if (res.success) {
            setFooter(`Traffic Manager 安装成功 (${ctx.name})`);
            showToast('Traffic Manager 安装成功', 'success');
            await refreshStatus(idx, true);
        } else {
            setFooter('安装失败: ' + res.message);
            showToast('安装失败: ' + res.message, 'error');
            btn.innerHTML = '📦 安装 Traffic Manager';
            btn.disabled = false;
        }
    } catch (e) {
        setFooter('安装失败: ' + e.message);
        showToast('安装 Traffic Manager 失败', 'error');
        btn.innerHTML = '📦 安装 Traffic Manager';
        btn.disabled = false;
    }
}

function renderStatus(idx, ctx, data) {
    const content = document.getElementById(`status-${idx}`);
    const tp = data.telepresence || {};
    const nodes = data.nodes || {};
    const cluster = data.cluster || {};

    // Update connection dot based on status
    const dot = document.getElementById(`dot-${idx}`);
    const connBtn = document.getElementById(`btn-conn-${idx}`);
    if (tp.connected) {
        dot.className = 'dot connected';
        connBtn.innerHTML = '■ 断开';
        connBtn.className = 'btn btn-danger btn-sm';
    } else {
        dot.className = 'dot';
        connBtn.innerHTML = '▶ 连接';
        connBtn.className = 'btn btn-success btn-sm';
    }

    const nodeRows = (nodes.nodes || []).map(n =>
        `<div class="status-row">
            <span class="status-label">节点</span>
            <span class="status-value">${escapeHtml(n.name)}</span>
            <span class="status-value ${n.status === 'Ready' ? 'ok' : 'error'}">(${n.status})</span>
        </div>`
    ).join('');

    const tmInstalled = data.traffic_manager_installed;

    content.innerHTML = `
        <div class="status-inner">
            <div class="status-row">
                <span class="status-label">连接状态</span>
                <span class="status-value ${tp.connected ? 'ok' : 'error'}">${tp.connected ? '已连接' : '未连接'}</span>
            </div>
            <div class="status-row">
                <span class="status-label">用户守护进程</span>
                <span class="status-value">${escapeHtml(tp.user_daemon || '-')}</span>
            </div>
            <div class="status-row">
                <span class="status-label">根守护进程</span>
                <span class="status-value">${escapeHtml(tp.root_daemon || '-')}</span>
            </div>
            <div class="status-row">
                <span class="status-label">流量管理器</span>
                <span class="status-value">${escapeHtml(tp.traffic_manager || '-')}</span>
            </div>
            <div class="status-row">
                <span class="status-label">TM 已安装</span>
                <span class="status-value ${tmInstalled ? 'ok' : 'error'}">${tmInstalled ? '是' : '否'}</span>
            </div>
            ${tp.version ? `<div class="status-row"><span class="status-label">版本</span><span class="status-value">${escapeHtml(tp.version)}</span></div>` : ''}
            <div class="status-row">
                <span class="status-label">节点数量</span>
                <span class="status-value">${nodes.count || 0}</span>
            </div>
            ${nodeRows}
            ${cluster.connected ? `<div class="status-row"><span class="status-label">集群</span><span class="status-value ok">${escapeHtml(cluster.server || '已连接')}</span></div>` : ''}
            ${nodes.error ? `<div class="status-row"><span class="status-label">错误</span><span class="status-value error">${escapeHtml(nodes.error)}</span></div>` : ''}
            ${!tmInstalled ? `<div class="status-actions"><button class="btn btn-sm btn-primary" id="btn-tm-install-${idx}" onclick="installTrafficManager(${idx})">📦 安装 Traffic Manager</button></div>` : ''}
        </div>
    `;
}

// === Utilities ===

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function shortenPath(path) {
    if (!path) return '';
    const kubeIdx = path.indexOf('.kube');
    if (kubeIdx >= 0) {
        return '~/' + path.substring(kubeIdx);
    }
    return path;
}

function setFooter(msg) {
    document.getElementById('footerMsg').textContent = msg;
}
