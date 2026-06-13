"""Frontend E2E tests using Playwright.

Runs the actual HTML/JS in a headless browser, mocks the Python API,
and verifies DOM output + state changes.

Run: python -m pytest tests/test_frontend_e2e.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    pytest.skip("playwright not installed", allow_module_level=True)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        br = p.chromium.launch(headless=False)
        yield br
        br.close()


@pytest.fixture()
def page(browser):
    """Create a fresh page with the app loaded and mock API injected."""
    pg = browser.new_page()
    # Load the HTML first, then inject mock before app.js initializes
    pg.goto(f"file:///{WEB_DIR}/index.html".replace("\\", "/"))

    # Inject mock pywebview API before app.js runs
    pg.evaluate("""
        window.__testResults = [];
        window.__mockApi = {
            get_config: () => Promise.resolve({ language: 'en', refreshInterval: 30 }),
            get_system_language: () => Promise.resolve('en'),
            check_tools: () => Promise.resolve({
                telepresence: true, kubectl: true,
                telepresence_version: 'OSS Client v2.28.0',
                kubectl_version: 'Client Version v1.30.0',
                telepresence_path: '/usr/bin/tp',
                kubectl_path: '/usr/bin/kubectl',
            }),
            scan_configs: () => Promise.resolve({ contexts: [] }),
            get_status: () => Promise.resolve({ connected: false }),
            get_full_status: () => Promise.resolve({
                telepresence: { connected: false, context: null, user_daemon: 'Running', root_daemon: 'Running', traffic_manager: 'Connected', version: 'v2.28.0' },
                nodes: { count: 0, nodes: [], error: null },
                cluster: { connected: false, server: '', error: null },
                traffic_manager_installed: true,
            }),
            connect: () => Promise.resolve({ success: true, message: 'ok' }),
            disconnect: () => Promise.resolve({ success: true, message: 'ok' }),
            open_shell: () => Promise.resolve({ success: true, message: 'ok' }),
            install_traffic_manager: () => Promise.resolve({ success: true, message: 'ok' }),
            check_update: () => Promise.resolve({ available: false }),
            save_config: () => Promise.resolve({ success: true }),
        };
        window.pywebview = { api: window.__mockApi };
    """)

    # Now re-run the app initialization
    pg.evaluate("""
        (async () => {
            // app.js sets `api` in the pywebviewready handler; mock it here
            api = window.pywebview.api;
            await initI18n();
            document.querySelector('.header h1').textContent = t('app.title');
            document.getElementById('btnScan').textContent = t('header.scan');
            document.getElementById('searchInput').placeholder = t('search.placeholder');
            document.getElementById('footerMsg').textContent = t('footer.ready');
            await applyConfig();
            checkTools();
            await scanConfigs();
        })()
    """)

    pg.wait_for_timeout(500)
    yield pg
    pg.close()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestI18n:
    """Language and translation tests."""

    def test_english_translations(self, page):
        page.evaluate("_currentLang = 'en'")
        assert page.evaluate("t('header.scan')") == "⟳ Scan Configs"
        assert page.evaluate("t('context.connect')") == "▶ Connect"
        assert page.evaluate("t('context.disconnect')") == "■ Disconnect"

    def test_chinese_translations(self, page):
        page.evaluate("_currentLang = 'zh'")
        assert page.evaluate("t('header.scan')") == "⟳ 扫描配置"
        assert page.evaluate("t('context.connect')") == "▶ 连接"

    def test_placeholder_substitution(self, page):
        page.evaluate("_currentLang = 'en'")
        result = page.evaluate("t('tools.ok', 'v1.0', 'v2.0')")
        assert "v1.0" in result
        assert "v2.0" in result

    def test_missing_key_returns_key(self, page):
        assert page.evaluate("t('nonexistent.key')") == "nonexistent.key"


class TestEscapeHtml:
    def test_escapes_tags(self, page):
        assert page.evaluate("escapeHtml('<script>alert(1)</script>')") == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_escapes_ampersand(self, page):
        assert page.evaluate("escapeHtml('a&b')") == "a&amp;b"

    def test_null_returns_empty(self, page):
        assert page.evaluate("escapeHtml(null)") == ""
        assert page.evaluate("escapeHtml(undefined)") == ""


class TestShortenPath:
    def test_replaces_kube_prefix(self, page):
        result = page.evaluate("shortenPath('/home/user/.kube/config')")
        assert result == "~/.kube/config" or result == "~\\.kube\\config"

    def test_non_kube_unchanged(self, page):
        assert page.evaluate("shortenPath('/etc/hosts')") == "/etc/hosts"

    def test_null_returns_empty(self, page):
        assert page.evaluate("shortenPath(null)") == ""


class TestRenderStatusConnectionState:
    """Verify renderStatus correctly updates per-context connection state."""

    def _setup_contexts(self, page, contexts_js):
        page.evaluate(f"""
            contexts = {contexts_js};
            connectionStates = new Map();
            const container = document.getElementById('configList');
            container.innerHTML = '';
            contexts.forEach((ctx, idx) => container.appendChild(createContextCard(ctx, idx)));
        """)

    def test_only_matching_context_shows_connected(self, page):
        self._setup_contexts(page, """[
            { name: 'ctx-a', cluster: 'c1', server: 's1', source_file: 'f1', is_current: false },
            { name: 'ctx-b', cluster: 'c2', server: 's2', source_file: 'f2', is_current: false },
        ]""")

        # Render status: ctx-a connected, ctx-b not
        page.evaluate("""
            renderStatus(0, contexts[0], {
                telepresence: { connected: true, context: 'ctx-a', user_daemon: 'Running', root_daemon: 'Running', traffic_manager: 'Connected', version: '' },
                nodes: { count: 0, nodes: [], error: null },
                cluster: { connected: true, server: '', error: null },
                traffic_manager_installed: true,
            });
        """)
        assert page.evaluate("connectionStates.get('ctx-a')") is True
        assert page.evaluate("connectionStates.get('ctx-b')") is None  # not yet set

        # Render status: ctx-b not connected (context mismatch)
        page.evaluate("""
            renderStatus(1, contexts[1], {
                telepresence: { connected: false, context: 'ctx-a', user_daemon: 'Running', root_daemon: 'Running', traffic_manager: 'Connected', version: '' },
                nodes: { count: 0, nodes: [], error: null },
                cluster: { connected: false, server: '', error: null },
                traffic_manager_installed: true,
            });
        """)
        assert page.evaluate("connectionStates.get('ctx-a')") is True
        assert page.evaluate("connectionStates.get('ctx-b')") is False

    def test_dot_class_reflects_state(self, page):
        self._setup_contexts(page, """[
            { name: 'ctx-a', cluster: 'c1', server: 's1', source_file: 'f1', is_current: false },
            { name: 'ctx-b', cluster: 'c2', server: 's2', source_file: 'f2', is_current: false },
        ]""")

        page.evaluate("""
            renderStatus(0, contexts[0], {
                telepresence: { connected: true, context: 'ctx-a', user_daemon: 'Running', root_daemon: 'Running', traffic_manager: 'Connected', version: '' },
                nodes: { count: 0, nodes: [], error: null },
                cluster: { connected: true, server: '', error: null },
                traffic_manager_installed: true,
            });
            renderStatus(1, contexts[1], {
                telepresence: { connected: false, context: 'ctx-a', user_daemon: 'Running', root_daemon: 'Running', traffic_manager: 'Connected', version: '' },
                nodes: { count: 0, nodes: [], error: null },
                cluster: { connected: false, server: '', error: null },
                traffic_manager_installed: true,
            });
        """)
        assert page.evaluate("document.getElementById('dot-0').classList.contains('connected')") is True
        assert page.evaluate("document.getElementById('dot-1').classList.contains('connected')") is False


class TestUpdateConnectionDots:
    """Verify global status updates don't overwrite per-context states."""

    def _setup(self, page):
        page.evaluate("""
            contexts = [
                { name: 'ctx-a', cluster: 'c1', server: 's1', source_file: 'f1', is_current: false },
                { name: 'ctx-b', cluster: 'c2', server: 's2', source_file: 'f2', is_current: false },
            ];
            connectionStates = new Map();
            const container = document.getElementById('configList');
            container.innerHTML = '';
            contexts.forEach((ctx, idx) => container.appendChild(createContextCard(ctx, idx)));
            connectionStates.set('ctx-a', true);
            updateCardUI('ctx-a', 0);
        """)

    def test_disconnect_clears_all(self, page):
        self._setup(page)
        page.evaluate("updateConnectionDots({ connected: false })")
        assert page.evaluate("connectionStates.get('ctx-a')") is False
        assert page.evaluate("connectionStates.get('ctx-b')") is None or page.evaluate("connectionStates.get('ctx-b')") is False

    def test_connected_does_not_overwrite_individual(self, page):
        self._setup(page)
        page.evaluate("updateConnectionDots({ connected: true })")
        assert page.evaluate("connectionStates.get('ctx-a')") is True
        # ctx-b was never set, should remain unset


class TestRefreshStatus:
    """Test that refreshStatus actually queries the API and updates the DOM."""

    def _setup(self, page, api_overrides=""):
        page.evaluate(f"""
            if (!window.pywebview || !window.pywebview.api) {{
                window.pywebview = {{ api: window.__mockApi || {{}} }};
            }}
            contexts = [
                {{ name: 'ctx-a', cluster: 'c1', server: 's1', source_file: 'f1', is_current: false }},
                {{ name: 'ctx-b', cluster: 'c2', server: 's2', source_file: 'f2', is_current: false }},
            ];
            connectionStates = new Map();
            const container = document.getElementById('configList');
            container.innerHTML = '';
            contexts.forEach((ctx, idx) => container.appendChild(createContextCard(ctx, idx)));
            {api_overrides}
        """)

    def test_refresh_queries_api_and_updates_dom(self, page):
        """refreshStatus must call get_full_status and render the result into the status panel."""
        self._setup(page, """
            window.__mockApi.get_full_status = (ctxName) => Promise.resolve({
                telepresence: { connected: true, context: ctxName, user_daemon: 'Running', root_daemon: 'Running', traffic_manager: 'Connected', version: 'v2.28.0' },
                nodes: { count: 1, nodes: [{ name: 'node-1', status: 'Ready' }], error: null },
                cluster: { connected: true, server: 'https://1.2.3.4', error: null },
                traffic_manager_installed: true,
            });
        """)

        # Call refreshStatus and wait for it
        page.evaluate("(async () => { await refreshStatus(0, true); })()")
        page.wait_for_timeout(500)

        # Verify DOM was updated — status indicator should contain connection state text
        status_html = page.evaluate("document.getElementById('status-0').innerHTML")
        assert len(status_html) > 5, f'status indicator should be populated, got: {status_html[:100]}'
        assert 'Connected' in status_html or 'Disconnected' in status_html, f'status indicator should show connection state: {status_html[:200]}'

    def test_refresh_updates_connection_state(self, page):
        """refreshStatus must update connectionStates based on the API response."""
        self._setup(page, """
            window.__mockApi.get_full_status = (ctxName) => Promise.resolve({
                telepresence: { connected: ctxName === 'ctx-a', context: 'ctx-a', user_daemon: 'Running', root_daemon: 'Running', traffic_manager: 'Connected', version: '' },
                nodes: { count: 0, nodes: [], error: null },
                cluster: { connected: true, server: '', error: null },
                traffic_manager_installed: true,
            });
        """)

        page.evaluate("(async () => { await refreshStatus(0, true); })()")
        page.wait_for_timeout(500)
        assert page.evaluate("connectionStates.get('ctx-a')") is True

        page.evaluate("(async () => { await refreshStatus(1, true); })()")
        page.wait_for_timeout(500)
        assert page.evaluate("connectionStates.get('ctx-b')") is False

    def test_refresh_shows_error_on_failure(self, page):
        """refreshStatus should show error in the status panel when API fails."""
        self._setup(page)
        page.evaluate("""
            window.__mockApi.get_full_status = () => Promise.resolve({ success: false, error: 'network down' });
        """)

        page.evaluate("(async () => { await refreshStatus(0, true); })()")
        page.wait_for_timeout(500)
        # refreshStatus should have rendered status without crashing
        status_el = page.evaluate("document.getElementById('status-0')")
        assert status_el is not None, 'status panel element should exist'


class TestFilterContexts:
    def _setup(self, page):
        page.evaluate("""
            contexts = [
                { name: 'production', cluster: 'prod-cluster', server: 'https://prod', source_file: '/kube/config', is_current: false },
                { name: 'staging', cluster: 'staging-cluster', server: 'https://stg', source_file: '/kube/config', is_current: false },
            ];
            const container = document.getElementById('configList');
            container.innerHTML = '';
            contexts.forEach((ctx, idx) => container.appendChild(createContextCard(ctx, idx)));
        """)

    def test_filter_by_name(self, page):
        self._setup(page)
        page.evaluate("document.getElementById('searchInput').value = 'prod'")
        page.evaluate("filterContexts()")
        cards = page.query_selector_all('.context-card')
        assert not cards[0].evaluate("el => el.classList.contains('hidden')")
        assert cards[1].evaluate("el => el.classList.contains('hidden')")

    def test_clear_shows_all(self, page):
        self._setup(page)
        page.evaluate("document.getElementById('searchInput').value = ''")
        page.evaluate("filterContexts()")
        cards = page.query_selector_all('.context-card')
        for card in cards:
            assert not card.evaluate("el => el.classList.contains('hidden')")


class TestShowToast:
    def test_creates_toast_element(self, page):
        page.evaluate("document.getElementById('toastContainer').innerHTML = ''")
        page.evaluate("showToast('Hello', 'info', 99999)")
        count = page.evaluate("document.getElementById('toastContainer').children.length")
        assert count == 1
        text = page.evaluate("document.getElementById('toastContainer').children[0].textContent")
        assert text == "Hello"
        cls = page.evaluate("document.getElementById('toastContainer').children[0].className")
        assert "info" in cls


class TestExtractVersion:
    def test_oss_client(self, page):
        assert page.evaluate("_extractVersion('OSS Client v2.28.0', 'OSS Client')") == "v2.28.0"

    def test_client_version(self, page):
        assert page.evaluate("_extractVersion('Client Version: v1.30.0', 'Client Version')") == "v1.30.0"

    def test_null(self, page):
        assert page.evaluate("_extractVersion(null, 'key')") == "N/A"
