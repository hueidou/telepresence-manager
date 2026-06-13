/**
 * Telepresence Manager — Frontend Logic
 * Calls Python API via pywebview's js_api bridge.
 */

/* global t, initI18n */

// pywebview API reference (set after window is ready)
let api = null;

// ── State ──
let contexts = [];
let connectionStates = new Map(); // contextName -> boolean (connected)
let autoRefreshTimer = null;
let AUTO_REFRESH_INTERVAL = 30000; // 30s default, overridden by config
let toolsInfo = null;

// ── Initialization ──

window.addEventListener('pywebviewready', async () => {
    api = window.pywebview.api;

    // Init i18n first (loads config + system language)
    await initI18n();

    // Apply language to static HTML elements
    document.querySelector('.header h1').textContent = t('app.title');
    document.getElementById('btnScan').textContent = t('header.scan');
    document.getElementById('btnScan').title = 'Ctrl+R';
    document.getElementById('searchInput').placeholder = t('search.placeholder');
    document.getElementById('footerMsg').textContent = t('footer.ready');

    // Load config and apply settings
    await applyConfig();

    // Start normal init
    checkTools();
    scanConfigs();
    checkForUpdate();
    setupKeyboardShortcuts();
});

async function applyConfig() {
    try {
        const cfg = await api.get_config();
        if (cfg.refreshInterval && cfg.refreshInterval > 0) {
            AUTO_REFRESH_INTERVAL = cfg.refreshInterval * 1000;
        }
    } catch (e) {
        // Use defaults
    }
}

// ── Update Check ──

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
                <span class="update-banner-title">${t('update.available', version)}</span>
                ${notesExcerpt ? `<span class="update-banner-notes">${escapeHtml(notesExcerpt)}</span>` : ''}
            </div>
            <div class="update-banner-actions">
                <button class="btn btn-primary btn-sm" onclick="startUpdate()">${t('update.updateNow')}</button>
                <button class="btn btn-sm" onclick="dismissUpdate()">${t('update.later')}</button>
            </div>
        </div>
        <div class="update-progress hidden" id="updateProgress">
            <div class="update-progress-bar" id="updateProgressBar"></div>
            <span class="update-progress-text" id="updateProgressText">${t('update.downloading')} 0%</span>
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
    textEl.textContent = t('update.preparing');

    try {
        showToast(t('update.toastDownloading'), 'info', 10000);
        barEl.classList.add('indeterminate');
        textEl.textContent = t('update.downloading');

        const res = await api.download_and_update();

        // If we reach here, update failed (success means the process exits)
        barEl.classList.remove('indeterminate');
        barEl.style.width = '100%';
        barEl.style.background = 'var(--danger)';
        textEl.textContent = t('update.failed', res.message || t('update.unknownError'));
        actionsEl.style.display = '';
        showToast(t('update.failed', res.message || t('update.unknownError')), 'error');
    } catch (e) {
        // The process is exiting (os._exit from backend); show "Restarting..."
        barEl.classList.remove('indeterminate');
        barEl.style.width = '100%';
        barEl.style.background = 'var(--success)';
        textEl.textContent = t('update.restarting');
    }
}

// Called from Python via evaluate_js to report download progress
function _updateProgress(pct) {
    const barEl = document.getElementById('updateProgressBar');
    const textEl = document.getElementById('updateProgressText');
    if (!barEl || !textEl) return;
    barEl.classList.remove('indeterminate');
    barEl.style.width = pct + '%';
    textEl.textContent = t('update.downloadingWithProgress', pct);
}

// ── Keyboard Shortcuts ──

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
            closeSettingsPanel();
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

// ── Toast Notifications ──

function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');

    // Limit visible toasts to 3 — remove oldest if exceeded
    const existing = container.querySelectorAll('.toast');
    if (existing.length >= 3) {
        existing[0].remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fadeOut');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ── Confirm Dialog ──

function showConfirm(title, message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';
        overlay.innerHTML = `
            <div class="confirm-dialog">
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(message)}</p>
                <div class="confirm-actions">
                    <button class="btn btn-sm" id="confirmCancel">${t('dialog.cancel')}</button>
                    <button class="btn btn-sm btn-danger" id="confirmOk">${t('dialog.confirm')}</button>
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

// ── Tool Check ──

async function checkTools() {
    const el = document.getElementById('toolsStatus');
    try {
        const res = await api.check_tools();
        toolsInfo = res;
        if (res.telepresence && res.kubectl) {
            const tpVer = _extractVersion(res.telepresence_version, 'OSS Client');
            const kcVer = _extractVersion(res.kubectl_version, 'Client Version');
            el.innerHTML = `<span class="tool-ok">✓</span> ${t('tools.ok', tpVer, kcVer)} <span class="tool-detail-btn" onclick="toggleToolDetail()">${t('tools.detail')}</span>`;
            el.className = 'tools-status ok';
        } else {
            const missing = [];
            if (!res.telepresence) missing.push('telepresence');
            if (!res.kubectl) missing.push('kubectl');
            el.textContent = t('tools.missing', missing.join(', '));
            el.className = 'tools-status error';
            showToast(t('tools.missing', missing.join(', ')), 'error', 5000);
        }
    } catch (e) {
        el.textContent = t('tools.checkFailed');
        el.className = 'tools-status error';
        showToast(t('tools.checkFailed'), 'error');
    }
}

function _extractVersion(fullStr, key) {
    if (!fullStr) return 'N/A';
    for (const line of fullStr.split('\n')) {
        if (line.includes(key)) {
            const match = line.match(/v?\d+\.\d+\.\d+[\w.-]*/);
            if (match) return match[0];
        }
    }
    const match = fullStr.match(/v?\d+\.\d+\.\d+[\w.-]*/);
    return match ? match[0] : fullStr.split('\n')[0];
}

function toggleToolDetail() {
    const panel = document.getElementById('toolDetailPanel');
    if (panel) {
        panel.remove();
        return;
    }
    if (!toolsInfo) return;

    const el = document.createElement('div');
    el.id = 'toolDetailPanel';
    el.className = 'tool-detail-panel';
    el.innerHTML = `
        <div class="tool-detail-row">
            <span class="tool-detail-label">${t('toolDetail.telepresence')}</span>
            <span class="tool-detail-value ${toolsInfo.telepresence ? 'ok' : 'error'}">
                ${toolsInfo.telepresence ? t('tools.installed') : t('tools.notInstalled')}
            </span>
        </div>
        ${toolsInfo.telepresence_version ? `
        <div class="tool-detail-row">
            <span class="tool-detail-label">${t('tools.version')}</span>
            <span class="tool-detail-value">${escapeHtml(toolsInfo.telepresence_version.split('\n')[0])}</span>
        </div>` : ''}
        ${toolsInfo.telepresence_path ? `
        <div class="tool-detail-row">
            <span class="tool-detail-label">${t('tools.path')}</span>
            <span class="tool-detail-value path">${escapeHtml(toolsInfo.telepresence_path)}</span>
        </div>` : ''}
        <div class="tool-detail-row">
            <span class="tool-detail-label">${t('toolDetail.kubectl')}</span>
            <span class="tool-detail-value ${toolsInfo.kubectl ? 'ok' : 'error'}">
                ${toolsInfo.kubectl ? t('tools.installed') : t('tools.notInstalled')}
            </span>
        </div>
        ${toolsInfo.kubectl_version ? `
        <div class="tool-detail-row">
            <span class="tool-detail-label">${t('tools.version')}</span>
            <span class="tool-detail-value">${escapeHtml(toolsInfo.kubectl_version.split('\n')[0])}</span>
        </div>` : ''}
        ${toolsInfo.kubectl_path ? `
        <div class="tool-detail-row">
            <span class="tool-detail-label">${t('tools.path')}</span>
            <span class="tool-detail-value path">${escapeHtml(toolsInfo.kubectl_path)}</span>
        </div>` : ''}
    `;
    document.querySelector('.header-right').appendChild(el);

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

// ── Settings Panel ──

function toggleSettings() {
    const existing = document.getElementById('settingsPanel');
    if (existing) {
        existing.remove();
        return;
    }

    const panel = document.createElement('div');
    panel.id = 'settingsPanel';
    panel.className = 'settings-panel';

    // Get current config values
    const loadAndRender = async () => {
        let currentLang = 'auto';
        let currentInterval = 30;
        try {
            const cfg = await api.get_config();
            currentLang = cfg.language || 'auto';
            currentInterval = cfg.refreshInterval || 30;
        } catch (e) {
            // Use defaults
        }

        panel.innerHTML = `
            <h3>${t('settings.title')}</h3>
            <div class="settings-row">
                <span class="settings-label">${t('settings.language')}</span>
                <select class="settings-select" id="settingsLang">
                    <option value="auto" ${currentLang === 'auto' ? 'selected' : ''}>${t('settings.langAuto')}</option>
                    <option value="zh" ${currentLang === 'zh' ? 'selected' : ''}>${t('settings.langZh')}</option>
                    <option value="en" ${currentLang === 'en' ? 'selected' : ''}>${t('settings.langEn')}</option>
                </select>
            </div>
            <div class="settings-row">
                <span class="settings-label">${t('settings.refreshInterval')}</span>
                <select class="settings-select" id="settingsInterval">
                    <option value="15" ${currentInterval === 15 ? 'selected' : ''}>15</option>
                    <option value="30" ${currentInterval === 30 ? 'selected' : ''}>30</option>
                    <option value="60" ${currentInterval === 60 ? 'selected' : ''}>60</option>
                    <option value="120" ${currentInterval === 120 ? 'selected' : ''}>120</option>
                </select>
            </div>
            <div class="settings-actions">
                <button class="btn btn-sm" onclick="closeSettingsPanel()">${t('settings.close')}</button>
                <button class="btn btn-sm btn-primary" onclick="saveSettings()">${t('dialog.confirm')}</button>
            </div>
        `;
    };

    loadAndRender();
    document.querySelector('.header-right').appendChild(panel);

    setTimeout(() => {
        document.addEventListener('click', _closeSettings, { once: true });
    }, 0);
}

function _closeSettings(e) {
    const panel = document.getElementById('settingsPanel');
    if (panel && !panel.contains(e.target) && !e.target.classList.contains('settings-btn')) {
        panel.remove();
    }
}

function closeSettingsPanel() {
    const panel = document.getElementById('settingsPanel');
    if (panel) panel.remove();
}

async function saveSettings() {
    const lang = document.getElementById('settingsLang').value;
    const interval = parseInt(document.getElementById('settingsInterval').value, 10) || 30;

    try {
        const res = await api.save_config({ language: lang, refreshInterval: interval });
        if (res.success) {
            showToast(t('settings.saved'), 'success');
            closeSettingsPanel();
            // Reload to apply new language & interval
            location.reload();
        } else {
            showToast(t('settings.saveFailed'), 'error');
        }
    } catch (e) {
        showToast(t('settings.saveFailed'), 'error');
    }
}

// ── Scan Configs ──

async function scanConfigs() {
    const btn = document.getElementById('btnScan');
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> ${t('header.scanning')}`;
    setFooter(t('scan.scanning'));

    try {
        const res = await api.scan_configs();
        contexts = res.contexts || [];
        renderList();
        setFooter(t('scan.complete', contexts.length));

        // Check existing connections on startup / re-scan
        checkExistingConnections();
    } catch (e) {
        setFooter(t('scan.failed', e.message));
        showToast(t('scan.failed', ''), 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = t('header.scan');
    }
}

// ── Search / Filter ──

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
            noResult.innerHTML = `<p>${t('search.noMatch')}</p>`;
            container.appendChild(noResult);
        }
    } else if (noResult) {
        noResult.remove();
    }
}

// ── Auto Refresh ──

function startAutoRefresh() {
    if (autoRefreshTimer) return;
    autoRefreshTimer = setInterval(async () => {
        if (contexts.length === 0) return;
        try {
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

    if (!isConnected) {
        // Telepresence is fully disconnected — safe to clear all states
        contexts.forEach((ctx, idx) => {
            connectionStates.set(ctx.name, false);
            updateCardUI(ctx.name, idx);
        });
    } else if (tpStatus.context) {
        // Mark the specific connected context
        contexts.forEach((ctx, idx) => {
            const shouldBeConnected = ctx.name === tpStatus.context;
            connectionStates.set(ctx.name, shouldBeConnected);
            updateCardUI(ctx.name, idx);
        });
    }
}

function updateCardUI(ctxName, idx) {
    const dot = document.getElementById(`dot-${idx}`);
    const btn = document.getElementById(`btn-conn-${idx}`);
    if (!dot || !btn) return;

    const connected = connectionStates.get(ctxName) || false;

    dot.className = connected ? 'dot connected' : 'dot';
    if (connected) {
        btn.innerHTML = t('context.disconnect');
        btn.className = 'btn btn-danger btn-sm';
    } else {
        btn.innerHTML = t('context.connect');
        btn.className = 'btn btn-success btn-sm';
    }
}

async function checkExistingConnections() {
    try {
        const status = await api.get_status();
        if (status.connected) {
            showToast(t('connect.foundExisting'), 'info');
            // Update card UI to reflect existing connection
            updateConnectionDots(status);
        }
        startAutoRefresh();
    } catch (e) {
        // Silent fail
    }
}

// ── Render Context List ──

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

}

function _updateCardData(card, ctx, idx) {
    card.id = `card-${idx}`;
    card.dataset.ctxName = ctx.name;
    card.dataset.ctxCluster = ctx.cluster;
    card.dataset.ctxServer = ctx.server || '';
    card.dataset.ctxSource = ctx.source_file;

    // Update badge
    const badge = card.querySelector('.card-top-right .card-badge');
    if (badge) badge.textContent = ctx.cluster;

    // Update meta
    const metaSpans = card.querySelectorAll('.card-meta span');
    if (metaSpans[0]) {
        metaSpans[0].innerHTML = `🌐 <span class="url-text">${escapeHtml(ctx.server || t('context.server'))}</span>`;
    }
    if (metaSpans[1]) metaSpans[1].textContent = `📁 ${shortenPath(ctx.source_file)}`;

    // Update button handlers with new index
    const connBtn = card.querySelector('[id^="btn-conn-"]');
    if (connBtn) {
        connBtn.id = `btn-conn-${idx}`;
        connBtn.setAttribute('onclick', `toggleConnect(${idx})`);
    }
    const statusBtn = card.querySelector('[id^="btn-status-"]');
    if (statusBtn) {
        statusBtn.id = `btn-status-${idx}`;
        statusBtn.setAttribute('onclick', `refreshStatus(${idx})`);
    }
    const shellBtn = card.querySelector('[data-action="shell"]');
    if (shellBtn) {
        shellBtn.setAttribute('onclick', `openShell(${idx})`);
    }
    const copyBtn = card.querySelector('.card-actions .btn-icon');
    if (copyBtn) {
        copyBtn.setAttribute('onclick', `copyContextName(${idx})`);
    }

    // Update status indicator id
    const statusEl = card.querySelector('.card-status-indicator');
    if (statusEl) statusEl.id = `status-${idx}`;

    // Update dot id
    const dot = card.querySelector('.dot');
    if (dot) dot.id = `dot-${idx}`;
}

function createEmptyState() {
    const div = document.createElement('div');
    div.className = 'empty-state';
    div.innerHTML = `
        <p>${t('empty.title')}</p>
        <div class="hint">
            ${t('empty.hint')}
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

    card.innerHTML = `
        <div class="card-top">
            <div class="card-name">
                <span class="dot" id="dot-${idx}"></span>
                <h3>${escapeHtml(ctx.name)}</h3>
            </div>
            <div class="card-top-right">
                <span class="card-status-indicator" id="status-${idx}">-</span>
                <span class="card-badge">${escapeHtml(ctx.cluster)}</span>
            </div>
        </div>
        <div class="card-meta">
            <span>🌐 <span class="url-text">${escapeHtml(ctx.server || t('context.server'))}</span></span>
            <span>📁 ${escapeHtml(shortenPath(ctx.source_file))}</span>
        </div>
        <div class="card-actions">
            <button class="btn btn-success btn-sm" id="btn-conn-${idx}" onclick="toggleConnect(${idx})">
                ${t('context.connect')}
            </button>
            <button class="btn btn-sm" data-action="shell" onclick="openShell(${idx})">
                ${t('context.shell')}
            </button>
            <button class="btn btn-sm" id="btn-status-${idx}" onclick="refreshStatus(${idx})">
                ${t('context.status')}
            </button>
            <button class="btn-icon" onclick="copyContextName(${idx})" title="${t('context.copy')}">📋</button>
        </div>
    `;
    return card;
}

// ── Copy ──

async function copyContextName(idx) {
    const ctx = contexts[idx];
    try {
        await navigator.clipboard.writeText(ctx.name);
        showToast(t('context.copied', ctx.name), 'success', 2000);
    } catch (e) {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = ctx.name;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        textarea.remove();
        showToast(t('context.copied', ctx.name), 'success', 2000);
    }
}

// ── Connect / Disconnect ──

async function toggleConnect(idx) {
    const ctx = contexts[idx];
    const btn = document.getElementById(`btn-conn-${idx}`);
    const dot = document.getElementById(`dot-${idx}`);

    const isCurrentlyConnected = connectionStates.get(ctx.name) || false;

    // Confirm disconnect
    if (isCurrentlyConnected) {
        const confirmed = await showConfirm(
            t('connect.title'),
            t('connect.confirmMsg')
        );
        if (!confirmed) return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>';

    if (isCurrentlyConnected) {
        setFooter(t('connect.disconnecting'));
        dot.className = 'dot';
        try {
            const res = await api.disconnect();
            if (res.success) {
                connectionStates.set(ctx.name, false);
                updateCardUI(ctx.name, idx);
                setFooter(t('connect.disconnected'));
                showToast(t('connect.disconnected'), 'success');
            } else {
                connectionStates.set(ctx.name, true);
                updateCardUI(ctx.name, idx);
                setFooter(t('connect.disconnectFailed', res.message));
                showToast(t('connect.disconnectFailed', res.message), 'error');
            }
        } catch (e) {
            connectionStates.set(ctx.name, true);
            updateCardUI(ctx.name, idx);
            setFooter(t('connect.disconnectFailed', e.message));
            showToast(t('connect.disconnectFailed', ''), 'error');
        }
    } else {
        setFooter(t('connect.connecting', ctx.name));
        dot.className = 'dot connecting';
        try {
            const res = await api.connect(ctx.name, ctx.source_file);
            if (res.success) {
                connectionStates.set(ctx.name, true);
                updateCardUI(ctx.name, idx);
                setFooter(t('connect.connected', ctx.name));
                showToast(t('connect.connected', ctx.name), 'success');
            } else {
                connectionStates.set(ctx.name, false);
                updateCardUI(ctx.name, idx);
                setFooter(t('connect.connectFailed', res.message));
                showToast(t('connect.connectFailed', res.message), 'error');
            }
        } catch (e) {
            connectionStates.set(ctx.name, false);
            updateCardUI(ctx.name, idx);
            setFooter(t('connect.connectFailed', e.message));
            showToast(t('connect.connectFailed', ''), 'error');
        }
    }

    btn.disabled = false;
}

// ── Open Shell ──

async function openShell(idx) {
    const ctx = contexts[idx];
    setFooter(t('shell.opening', ctx.name));
    try {
        const res = await api.open_shell(ctx.name, ctx.source_file);
        if (res.success) {
            setFooter(t('shell.opened', ctx.name));
            showToast(t('shell.opened', ctx.name), 'success', 2000);
        } else {
            setFooter(t('shell.openFailed', res.message));
            showToast(t('shell.openFailed', res.message), 'error');
        }
    } catch (e) {
        setFooter(t('shell.openFailed', e.message));
        showToast(t('shell.openFailed', ''), 'error');
    }
}

// ── Status ──

async function refreshStatus(idx, silent = false) {
    const ctx = contexts[idx];
    const statusEl = document.getElementById(`status-${idx}`);
    const btn = document.getElementById(`btn-status-${idx}`);

    if (!silent) {
        statusEl.innerHTML = `<span class="spinner"></span>`;
        btn.disabled = true;
    }

    try {
        const res = await api.get_full_status(ctx.name, ctx.source_file);
        renderStatus(idx, ctx, res);
    } catch (e) {
        statusEl.textContent = '-';
        statusEl.className = 'card-status-indicator';
        if (!silent) {
            showToast(t('status.queryFailed', e.message), 'error');
        }
    } finally {
        if (!silent) {
            btn.disabled = false;
        }
    }
}

async function installTrafficManager(idx) {
    const ctx = contexts[idx];
    const btn = document.getElementById(`btn-tm-install-${idx}`);
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> ${t('status.installingTm')}`;
    setFooter(t('status.installingTm'));
    showToast(t('status.installingTm'), 'info', 5000);

    try {
        const res = await api.install_traffic_manager(ctx.name, ctx.source_file);
        if (res.success) {
            setFooter(t('status.tmInstallSuccess'));
            showToast(t('status.tmInstallSuccess'), 'success');
            await refreshStatus(idx, true);
        } else {
            setFooter(t('status.tmInstallFailed', res.message));
            showToast(t('status.tmInstallFailed', res.message), 'error');
            btn.innerHTML = t('status.installTm');
            btn.disabled = false;
        }
    } catch (e) {
        setFooter(t('status.tmInstallFailed', e.message));
        showToast(t('status.tmInstallFailed', ''), 'error');
        btn.innerHTML = t('status.installTm');
        btn.disabled = false;
    }
}

function renderStatus(idx, ctx, data) {
    const statusEl = document.getElementById(`status-${idx}`);
    const tp = data.telepresence || {};
    const nodes = data.nodes || {};
    const cluster = data.cluster || {};
    const tmInstalled = data.traffic_manager_installed;

    const isConnected = tp.connected || false;
    connectionStates.set(ctx.name, isConnected);
    updateCardUI(ctx.name, idx);

    // Build a compact status summary on the right side of the card
    const parts = [];
    if (isConnected) {
        parts.push(`<span class="status-value ok">${t('status.connected')}</span>`);
    } else {
        parts.push(`<span class="status-value error">${t('status.disconnected')}</span>`);
    }
    if (tp.version) {
        const ver = tp.version.startsWith('v') ? tp.version : 'v' + tp.version;
        parts.push(`<span class="status-value dim">${escapeHtml(ver)}</span>`);
    }
    parts.push(`<span class="status-value dim" title="${t('status.nodeCount')}">${nodes.count || 0} ${t('status.node')}</span>`);
    if (!tmInstalled) {
        parts.push(`<span class="status-value error" title="${t('status.installTm')}" style="cursor:pointer" onclick="installTrafficManager(${idx})">TM?</span>`);
    }

    statusEl.innerHTML = parts.join(' ');
    statusEl.className = 'card-status-indicator' + (isConnected ? ' connected' : '');
}

// ── Utilities ──

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
