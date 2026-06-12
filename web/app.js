/**
 * Telepresence Manager — Frontend Logic
 * Calls Python API via pywebview's js_api bridge.
 */

// pywebview API reference (set after window is ready)
let api = null;

// State
let contexts = [];

// === Initialization ===

window.addEventListener('pywebviewready', () => {
    api = window.pywebview.api;
    checkTools();
    scanConfigs();
});

// === Tool Check ===

let toolsInfo = null;

async function checkTools() {
    const el = document.getElementById('toolsStatus');
    try {
        const res = await api.check_tools();
        toolsInfo = res;
        if (res.telepresence && res.kubectl) {
            // Extract short version strings
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
        }
    } catch (e) {
        el.textContent = '✗ 检测失败';
        el.className = 'tools-status error';
    }
}

function _extractVersion(fullStr, key) {
    if (!fullStr) return 'N/A';
    // Try to extract "vX.Y.Z" or version after a key like "Client Version: v1.36.1"
    for (const line of fullStr.split('\n')) {
        if (line.includes(key)) {
            const match = line.match(/v?[\d]+\.[\d]+\.[\d]+[\w.-]*/);
            if (match) return match[0];
        }
    }
    // Fallback: find any version-like string
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

    // Close on click outside
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
    } catch (e) {
        setFooter('扫描失败: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '⟳ 扫描配置';
    }
}

// === Render Context List ===

function renderList() {
    const container = document.getElementById('configList');
    const empty = document.getElementById('emptyState');

    if (contexts.length === 0) {
        container.innerHTML = '';
        container.appendChild(createEmptyState());
        return;
    }

    container.innerHTML = '';
    contexts.forEach((ctx, idx) => {
        container.appendChild(createContextCard(ctx, idx));
    });
}

function createEmptyState() {
    const div = document.createElement('div');
    div.className = 'empty-state';
    div.innerHTML = '<p>未找到 K8s 配置，请确认 ~/.kube/ 下存在 config 文件</p>';
    return div;
}

function createContextCard(ctx, idx) {
    const card = document.createElement('div');
    card.className = 'context-card';
    card.id = `card-${idx}`;

    const currentBadge = ctx.is_current
        ? '<span class="card-badge" style="color:var(--accent)">当前</span>'
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
            <span>🌐 ${escapeHtml(ctx.server || 'N/A')}</span>
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
        </div>
        <div class="card-status hidden" id="status-${idx}"></div>
    `;
    return card;
}

// === Connect / Disconnect ===

async function toggleConnect(idx) {
    const ctx = contexts[idx];
    const btn = document.getElementById(`btn-conn-${idx}`);
    const dot = document.getElementById(`dot-${idx}`);

    // Check current state
    const isCurrentlyConnected = dot.classList.contains('connected');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>';

    if (isCurrentlyConnected) {
        // Disconnect
        setFooter(`正在断开 telepresence...`);
        dot.className = 'dot';
        try {
            const res = await api.disconnect();
            if (res.success) {
                btn.innerHTML = '▶ 连接';
                btn.className = 'btn btn-success btn-sm';
                setFooter('已断开连接');
            } else {
                setFooter('断开失败: ' + res.message);
            }
        } catch (e) {
            setFooter('断开失败: ' + e.message);
        }
    } else {
        // Connect
        setFooter(`正在连接 ${ctx.name}...`);
        dot.className = 'dot connecting';
        try {
            const res = await api.connect(ctx.name, ctx.source_file);
            if (res.success) {
                dot.className = 'dot connected';
                btn.innerHTML = '■ 断开';
                btn.className = 'btn btn-danger btn-sm';
                setFooter(`已连接到 ${ctx.name}`);
            } else {
                dot.className = 'dot';
                btn.innerHTML = '▶ 连接';
                setFooter('连接失败: ' + res.message);
            }
        } catch (e) {
            dot.className = 'dot';
            btn.innerHTML = '▶ 连接';
            setFooter('连接失败: ' + e.message);
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
        } else {
            setFooter('打开失败: ' + res.message);
        }
    } catch (e) {
        setFooter('打开失败: ' + e.message);
    }
}

// === Status ===

async function refreshStatus(idx) {
    const ctx = contexts[idx];
    const statusEl = document.getElementById(`status-${idx}`);
    const btn = document.getElementById(`btn-status-${idx}`);

    // Toggle: if already visible, hide it
    if (!statusEl.classList.contains('hidden')) {
        statusEl.classList.add('hidden');
        statusEl.innerHTML = '';
        btn.innerHTML = '⟳ 状态';
        return;
    }

    statusEl.classList.remove('hidden');
    statusEl.innerHTML = '<span class="spinner"></span> 查询中...';
    btn.innerHTML = '✕ 收起';
    setFooter(`正在查询 ${ctx.name} 状态...`);

    try {
        const res = await api.get_full_status(ctx.name, ctx.source_file);
        renderStatus(idx, ctx, res);
        setFooter(`状态查询完成 (${ctx.name})`);
    } catch (e) {
        statusEl.innerHTML = `<div class="status-value error">查询失败: ${escapeHtml(e.message)}</div>`;
        setFooter('状态查询失败');
    }
}

async function installTrafficManager(idx) {
    const ctx = contexts[idx];
    const btn = document.getElementById(`btn-tm-install-${idx}`);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 安装中...';
    setFooter(`正在为 ${ctx.name} 安装 Traffic Manager...`);

    try {
        const res = await api.install_traffic_manager(ctx.name, ctx.source_file);
        if (res.success) {
            setFooter(`Traffic Manager 安装成功 (${ctx.name})`);
            // Refresh status to show updated state
            await refreshStatus(idx);
        } else {
            setFooter('安装失败: ' + res.message);
            btn.innerHTML = '📦 安装 Traffic Manager';
            btn.disabled = false;
        }
    } catch (e) {
        setFooter('安装失败: ' + e.message);
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
    const tmInstallBtn = !tmInstalled
        ? `<button class="btn btn-sm btn-primary" id="btn-tm-install-${idx}" onclick="installTrafficManager(${idx})">📦 安装 Traffic Manager</button>`
        : '';

    content.innerHTML = `
        <div class="status-inner">
            <div class="status-row">
                <span class="status-label">Telepresence</span>
                <span class="status-value ${tp.connected ? 'ok' : 'error'}">${tp.connected ? '已连接' : '未连接'}</span>
            </div>
            <div class="status-row">
                <span class="status-label">User Daemon</span>
                <span class="status-value">${escapeHtml(tp.user_daemon || '-')}</span>
            </div>
            <div class="status-row">
                <span class="status-label">Root Daemon</span>
                <span class="status-value">${escapeHtml(tp.root_daemon || '-')}</span>
            </div>
            <div class="status-row">
                <span class="status-label">Traffic Mgr</span>
                <span class="status-value">${escapeHtml(tp.traffic_manager || '-')}</span>
            </div>
            <div class="status-row">
                <span class="status-label">TM 已安装</span>
                <span class="status-value ${tmInstalled ? 'ok' : 'error'}">${tmInstalled ? '是' : '否'}</span>
                ${tmInstallBtn}
            </div>
            ${tp.version ? `<div class="status-row"><span class="status-label">Version</span><span class="status-value">${escapeHtml(tp.version)}</span></div>` : ''}
            <div class="status-row">
                <span class="status-label">节点数量</span>
                <span class="status-value">${nodes.count || 0}</span>
            </div>
            ${nodeRows}
            ${cluster.connected ? `<div class="status-row"><span class="status-label">Cluster</span><span class="status-value ok">${escapeHtml(cluster.server || 'Connected')}</span></div>` : ''}
            ${nodes.error ? `<div class="status-row"><span class="status-label">错误</span><span class="status-value error">${escapeHtml(nodes.error)}</span></div>` : ''}
        </div>
    `;
}

// === Utilities ===

function escapeHtml(str, preserveNewlines) {
    if (!str) return '';
    let s = str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    if (preserveNewlines) {
        s = s.replace(/\n/g, '<br>');
    }
    return s;
}

function shortenPath(path) {
    if (!path) return '';
    const home = path.includes('\\') ? 'C:\\Users\\' : '/home/';
    // Try to shorten to ~/
    const kubeIdx = path.indexOf('.kube');
    if (kubeIdx >= 0) {
        return '~/' + path.substring(kubeIdx);
    }
    return path;
}

function setFooter(msg) {
    document.getElementById('footerMsg').textContent = msg;
}
