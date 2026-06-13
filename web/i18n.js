/**
 * Telepresence Manager — Internationalization
 *
 * Supported: zh (Chinese), en (English)
 * Language detected from: navigator.language → config override
 */

const LOCALES = {
    zh: {
        // ── App ──
        'app.title': 'Telepresence Manager',
        'app.loading': '加载中...',

        // ── Header ──
        'header.scan': '⟳ 扫描配置',
        'header.scanning': '扫描中...',

        // ── Tools ──
        'tools.ok': '✓ TP {0} · kubectl {1}',
        'tools.missing': '✗ 缺少: {0}',
        'tools.checkFailed': '✗ 检测失败',
        'tools.installed': '已安装',
        'tools.notInstalled': '未安装',
        'tools.version': '版本',
        'tools.path': '路径',
        'tools.detail': 'ℹ',

        // ── Context Card ──
        'context.current': '当前',
        'context.connect': '▶ 连接',
        'context.disconnect': '■ 断开',
        'context.shell': '>_ 命令行',
        'context.status': '⟳ 状态',
        'context.copy': '复制 context 名称',
        'context.copied': '已复制: {0}',
        'context.server': 'N/A',

        // ── Status Panel ──
        'status.title': '查询中...',
        'status.collapse': '✕ 收起',
        'status.connected': '已连接',
        'status.disconnected': '未连接',
        'status.connectionState': '连接状态',
        'status.userDaemon': '用户守护进程',
        'status.rootDaemon': '根守护进程',
        'status.trafficManager': '流量管理器',
        'status.tmInstalled': 'TM 已安装',
        'status.yes': '是',
        'status.no': '否',
        'status.nodeCount': '节点数量',
        'status.node': '节点',
        'status.cluster': '集群',
        'status.error': '错误',
        'status.version': '版本',
        'status.queryFailed': '查询失败: {0}',
        'status.installTm': '📦 安装 Traffic Manager',
        'status.installingTm': '安装中...',
        'status.tmInstallSuccess': 'Traffic Manager 安装成功',
        'status.tmInstallFailed': '安装失败: {0}',
        'status.dash': '-',

        // ── Connect / Disconnect ──
        'connect.title': '断开连接',
        'connect.confirmMsg': '确认断开 Telepresence 连接？当前连接的 context 可能正在使用中。',
        'connect.connecting': '正在连接 {0}...',
        'connect.connected': '已连接到 {0}',
        'connect.connectFailed': '连接失败: {0}',
        'connect.disconnecting': '正在断开 telepresence...',
        'connect.disconnected': '已断开连接',
        'connect.disconnectFailed': '断开失败: {0}',
        'connect.foundExisting': '检测到已有 Telepresence 连接',

        // ── Shell ──
        'shell.opening': '正在为 {0} 打开命令行...',
        'shell.opened': '已打开命令行 ({0})',
        'shell.openFailed': '打开命令行失败: {0}',

        // ── Scan ──
        'scan.scanning': '正在扫描 ~/.kube/ 配置文件...',
        'scan.complete': '扫描完成，发现 {0} 个 context',
        'scan.failed': '扫描失败: {0}',
        'scan.initial': '点击「扫描配置」加载 ~/.kube/ 下的 K8s 配置',

        // ── Search ──
        'search.placeholder': '搜索 context...',
        'search.noMatch': '没有匹配的 context',

        // ── Empty State ──
        'empty.title': '未找到 K8s 配置',
        'empty.hint': '请确认 <code>~/.kube/</code> 目录下存在配置文件：<br><code>config</code>、<code>*.yaml</code>、<code>*.yml</code>、<code>*.txt</code><br><br>或通过以下命令生成：<br><code>kubectl config view --flatten > ~/.kube/config</code>',

        // ── Update ──
        'update.available': '🆕 发现新版本 v{0}',
        'update.updateNow': '立即更新',
        'update.later': '稍后',
        'update.preparing': '准备下载...',
        'update.downloading': '下载中...',
        'update.restarting': '正在重启...',
        'update.downloadingWithProgress': '下载中... {0}%',
        'update.toastDownloading': '正在下载更新，完成后将自动重启...',
        'update.failed': '更新失败: {0}',
        'update.unknownError': '未知错误',

        // ── Footer ──
        'footer.ready': '就绪',

        // ── Dialog ──
        'dialog.cancel': '取消',
        'dialog.confirm': '确认',

        // ── Config / Settings ──
        'settings.title': '设置',
        'settings.language': '语言',
        'settings.langAuto': '自动',
        'settings.langZh': '中文',
        'settings.langEn': 'English',
        'settings.refreshInterval': '刷新间隔（秒）',
        'settings.close': '关闭',
        'settings.saved': '设置已保存',
        'settings.saveFailed': '保存设置失败',

        // ── Toast ──
        'toast.success': '成功',
        'toast.error': '错误',
        'toast.info': '信息',

        // ── Tool Detail Panel ──
        'toolDetail.telepresence': 'Telepresence',
        'toolDetail.kubectl': 'kubectl',
    },

    en: {
        // ── App ──
        'app.title': 'Telepresence Manager',
        'app.loading': 'Loading...',

        // ── Header ──
        'header.scan': '⟳ Scan Configs',
        'header.scanning': 'Scanning...',

        // ── Tools ──
        'tools.ok': '✓ TP {0} · kubectl {1}',
        'tools.missing': '✗ Missing: {0}',
        'tools.checkFailed': '✗ Check failed',
        'tools.installed': 'Installed',
        'tools.notInstalled': 'Not installed',
        'tools.version': 'Version',
        'tools.path': 'Path',
        'tools.detail': 'ℹ',

        // ── Context Card ──
        'context.current': 'current',
        'context.connect': '▶ Connect',
        'context.disconnect': '■ Disconnect',
        'context.shell': '>_ Shell',
        'context.status': '⟳ Status',
        'context.copy': 'Copy context name',
        'context.copied': 'Copied: {0}',
        'context.server': 'N/A',

        // ── Status Panel ──
        'status.title': 'Querying...',
        'status.collapse': '✕ Collapse',
        'status.connected': 'Connected',
        'status.disconnected': 'Disconnected',
        'status.connectionState': 'Connection',
        'status.userDaemon': 'User Daemon',
        'status.rootDaemon': 'Root Daemon',
        'status.trafficManager': 'Traffic Manager',
        'status.tmInstalled': 'TM Installed',
        'status.yes': 'Yes',
        'status.no': 'No',
        'status.nodeCount': 'Nodes',
        'status.node': 'Node',
        'status.cluster': 'Cluster',
        'status.error': 'Error',
        'status.version': 'Version',
        'status.queryFailed': 'Query failed: {0}',
        'status.installTm': '📦 Install Traffic Manager',
        'status.installingTm': 'Installing...',
        'status.tmInstallSuccess': 'Traffic Manager installed',
        'status.tmInstallFailed': 'Install failed: {0}',
        'status.dash': '-',

        // ── Connect / Disconnect ──
        'connect.title': 'Disconnect',
        'connect.confirmMsg': 'Are you sure you want to disconnect Telepresence? The current connection may be in use.',
        'connect.connecting': 'Connecting to {0}...',
        'connect.connected': 'Connected to {0}',
        'connect.connectFailed': 'Connection failed: {0}',
        'connect.disconnecting': 'Disconnecting telepresence...',
        'connect.disconnected': 'Disconnected',
        'connect.disconnectFailed': 'Disconnect failed: {0}',
        'connect.foundExisting': 'Existing Telepresence connection detected',

        // ── Shell ──
        'shell.opening': 'Opening shell for {0}...',
        'shell.opened': 'Shell opened ({0})',
        'shell.openFailed': 'Failed to open shell: {0}',

        // ── Scan ──
        'scan.scanning': 'Scanning ~/.kube/ config files...',
        'scan.complete': 'Scan complete, found {0} context(s)',
        'scan.failed': 'Scan failed: {0}',
        'scan.initial': 'Click "Scan Configs" to load K8s configs from ~/.kube/',

        // ── Search ──
        'search.placeholder': 'Search context...',
        'search.noMatch': 'No matching context',

        // ── Empty State ──
        'empty.title': 'No K8s configs found',
        'empty.hint': 'Make sure there are config files in <code>~/.kube/</code>:<br><code>config</code>, <code>*.yaml</code>, <code>*.yml</code>, <code>*.txt</code><br><br>Or generate one with:<br><code>kubectl config view --flatten > ~/.kube/config</code>',

        // ── Update ──
        'update.available': '🆕 New version v{0} available',
        'update.updateNow': 'Update Now',
        'update.later': 'Later',
        'update.preparing': 'Preparing download...',
        'update.downloading': 'Downloading...',
        'update.restarting': 'Restarting...',
        'update.downloadingWithProgress': 'Downloading... {0}%',
        'update.toastDownloading': 'Downloading update, will restart automatically...',
        'update.failed': 'Update failed: {0}',
        'update.unknownError': 'Unknown error',

        // ── Footer ──
        'footer.ready': 'Ready',

        // ── Dialog ──
        'dialog.cancel': 'Cancel',
        'dialog.confirm': 'Confirm',

        // ── Config / Settings ──
        'settings.title': 'Settings',
        'settings.language': 'Language',
        'settings.langAuto': 'Auto',
        'settings.langZh': '中文',
        'settings.langEn': 'English',
        'settings.refreshInterval': 'Refresh interval (s)',
        'settings.close': 'Close',
        'settings.saved': 'Settings saved',
        'settings.saveFailed': 'Failed to save settings',

        // ── Toast ──
        'toast.success': 'Success',
        'toast.error': 'Error',
        'toast.info': 'Info',

        // ── Tool Detail Panel ──
        'toolDetail.telepresence': 'Telepresence',
        'toolDetail.kubectl': 'kubectl',
    },
};

// ── Current language (set during init) ──
let _currentLang = 'zh';

// ── Translation function ──

function t(key, ...args) {
    const locale = LOCALES[_currentLang] || LOCALES.zh;
    let str = locale[key];
    if (str === undefined) {
        // Fallback to zh
        str = LOCALES.zh[key];
    }
    if (str === undefined) {
        console.warn(`[i18n] Missing key: ${key}`);
        return key;
    }
    // Replace {0}, {1}, etc.
    if (args.length > 0) {
        str = str.replace(/\{(\d+)\}/g, (match, num) => {
            const idx = parseInt(num, 10);
            return idx < args.length ? args[idx] : match;
        });
    }
    return str;
}

// ── Language resolution ──

function resolveLanguage(configLang, systemLang) {
    if (configLang && configLang !== 'auto') {
        return configLang;
    }
    // Detect from browser
    const navLang = (navigator.language || '').toLowerCase();
    if (navLang.startsWith('zh')) {
        return 'zh';
    }
    // Fall back to system locale from Python
    if (systemLang === 'zh') {
        return 'zh';
    }
    return 'en';
}

// ── Initialize i18n ──

async function initI18n() {
    let configLang = 'auto';
    let systemLang = 'en';

    try {
        if (window.pywebview && window.pywebview.api) {
            const [cfg, sysLang] = await Promise.all([
                window.pywebview.api.get_config(),
                window.pywebview.api.get_system_language(),
            ]);
            configLang = cfg.language || 'auto';
            systemLang = sysLang || 'en';
        }
    } catch (e) {
        // Use defaults
    }

    _currentLang = resolveLanguage(configLang, systemLang);
    document.documentElement.lang = _currentLang === 'zh' ? 'zh-CN' : 'en';
}
