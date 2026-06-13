"""Backend unit tests for Telepresence Manager.

Run with: python -m pytest tests/test_backend.py -v
"""

import json
import os
import sys
import tempfile

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.telepresence import get_status
from app.kubeconfig import _parse_config_file, _is_kube_config
from app.updater import _parse_version
from app.config import get_system_language


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_TELEPRESENCE_STATUS_CONNECTED = """\
OSS User Daemon: Running
  Version           : 2.28.0
  Executable        : C:\\Users\\hueid\\AppData\\Local\\Microsoft\\WinGet\\Links\\telepresence.exe
  Install ID        : a1d74fd4-a112-4caa-a54c-679a007eea1e
  Status            : Connected
  Kubernetes server : https://127.0.0.1:6443
  Kubernetes context: rancher-desktop
  Namespace         : default
  Manager namespace : ambassador
  Mapped namespaces : [ambassador default kube-public]
OSS Root Daemon: Running
  Version: v2.28.0
  DNS    :
    Local addresses : [127.0.0.1:58902]
    VIF Address     : 10.42.0.19:53
    Exclude suffixes: [.com .io .net .org .ru]
    Include suffixes: []
    Timeout         : 4s
  Subnets: (2 subnets)
    - 10.43.0.0/16
    - 10.42.0.0/24
OSS Traffic Manager: Connected
  Version      : v2.28.0
  Traffic Agent: ghcr.io/telepresenceio/tel2:2.28.0
"""

SAMPLE_TELEPRESENCE_STATUS_DISCONNECTED = """\
OSS User Daemon: Running
  Version           : 2.28.0
  Executable        : C:\\Users\\hueid\\AppData\\Local\\Microsoft\\WinGet\\Links\\telepresence.exe
  Install ID        : a1d74fd4-a112-4caa-a54c-679a007eea1e
  Status            : Not connected
OSS Root Daemon: Running
  Version: v2.28.0
OSS Traffic Manager: Not connected
"""

SAMPLE_TELEPRESENCE_STATUS_K3S = """\
OSS User Daemon: Running
  Version           : 2.28.0
  Status            : Connected
  Kubernetes server : https://192.168.68.186:6443
  Kubernetes context: default
  Namespace         : default
  Manager namespace : ambassador
OSS Root Daemon: Running
  Version: v2.28.0
OSS Traffic Manager: Connected
  Version      : v2.28.0
"""

SAMPLE_KUBECONFIG = """\
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://1.2.3.4:6443
  name: my-cluster
- cluster:
    server: https://5.6.7.8:6443
  name: other-cluster
contexts:
- context:
    cluster: my-cluster
    user: my-user
    namespace: default
  name: my-context
- context:
    cluster: other-cluster
    user: other-user
  name: other-context
current-context: my-context
users:
- name: my-user
  user:
    token: abc123
"""

SAMPLE_KUBECONFIG_MINIMAL = """\
apiVersion: v1
clusters:
- cluster:
    server: https://10.0.0.1:6443
  name: default
contexts:
- context:
    cluster: default
    user: default
  name: default
current-context: default
kind: Config
users:
- name: default
  user:
    token: xyz
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_get_status(raw_output, context=None):
    """Run get_status parsing logic with mocked telepresence output."""
    result = {
        "connected": False,
        "context": None,
        "user_daemon": "Unknown",
        "root_daemon": "Unknown",
        "traffic_manager": "Unknown",
        "version": "",
        "error": None,
    }
    for line in raw_output.split("\n"):
        line = line.strip()
        if not line or "has been deprecated" in line.lower():
            continue
        lower = line.lower()
        if "kubernetes context" in lower or lower.startswith("context"):
            result["context"] = line.split(":", 1)[-1].strip() if ":" in line else None
        elif "user daemon" in lower:
            result["user_daemon"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif "root daemon" in lower:
            result["root_daemon"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif "traffic manager" in lower:
            result["traffic_manager"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif lower.startswith("version"):
            result["version"] = line.split(":", 1)[-1].strip() if ":" in line else line

    tm_connected = result["traffic_manager"].lower() == "connected"
    if tm_connected:
        if context:
            result["connected"] = result["context"] == context
        else:
            result["connected"] = True
    return result


def _write_temp_file(content, suffix=".yaml"):
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


# ── Tests: get_status parsing ─────────────────────────────────────────────────

class TestGetStatusParsing:
    """Test telepresence status output parsing with context matching."""

    def test_connected_matching_context(self):
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_CONNECTED, "rancher-desktop")
        assert r["connected"] is True
        assert r["context"] == "rancher-desktop"
        assert r["traffic_manager"] == "Connected"
        assert r["user_daemon"] == "Running"
        assert r["root_daemon"] == "Running"
        assert r["version"] == "v2.28.0"

    def test_connected_non_matching_context(self):
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_CONNECTED, "default")
        assert r["connected"] is False
        assert r["context"] == "rancher-desktop"

    def test_connected_no_context_requested(self):
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_CONNECTED)
        assert r["connected"] is True
        assert r["context"] == "rancher-desktop"

    def test_disconnected(self):
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_DISCONNECTED)
        assert r["connected"] is False
        assert r["traffic_manager"] == "Not connected"

    def test_disconnected_with_context(self):
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_DISCONNECTED, "rancher-desktop")
        assert r["connected"] is False

    def test_traffic_manager_not_overwritten_by_kubernetes_context(self):
        """'Kubernetes context' line must NOT overwrite traffic_manager field."""
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_CONNECTED)
        assert r["traffic_manager"] == "Connected"  # not "rancher-desktop"

    def test_k3s_context_parsed(self):
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_K3S, "default")
        assert r["connected"] is True
        assert r["context"] == "default"

    def test_k3s_wrong_context(self):
        r = _mock_get_status(SAMPLE_TELEPRESENCE_STATUS_K3S, "other")
        assert r["connected"] is False


# ── Tests: kubeconfig parsing ─────────────────────────────────────────────────

class TestKubeconfigParsing:
    """Test kubeconfig file parsing."""

    def test_parse_standard_config(self):
        path = _write_temp_file(SAMPLE_KUBECONFIG)
        try:
            contexts = _parse_config_file(path)
            assert len(contexts) == 2
            names = [c["name"] for c in contexts]
            assert "my-context" in names
            assert "other-context" in names
        finally:
            os.unlink(path)

    def test_current_context_flagged(self):
        path = _write_temp_file(SAMPLE_KUBECONFIG)
        try:
            contexts = _parse_config_file(path)
            current = [c for c in contexts if c["is_current"]]
            assert len(current) == 1
            assert current[0]["name"] == "my-context"
        finally:
            os.unlink(path)

    def test_server_extracted(self):
        path = _write_temp_file(SAMPLE_KUBECONFIG)
        try:
            contexts = _parse_config_file(path)
            ctx = next(c for c in contexts if c["name"] == "my-context")
            assert ctx["server"] == "https://1.2.3.4:6443"
            assert ctx["cluster"] == "my-cluster"
        finally:
            os.unlink(path)

    def test_source_file_set(self):
        path = _write_temp_file(SAMPLE_KUBECONFIG)
        try:
            contexts = _parse_config_file(path)
            for ctx in contexts:
                assert ctx["source_file"] == path
        finally:
            os.unlink(path)

    def test_minimal_config(self):
        path = _write_temp_file(SAMPLE_KUBECONFIG_MINIMAL)
        try:
            contexts = _parse_config_file(path)
            assert len(contexts) == 1
            assert contexts[0]["name"] == "default"
        finally:
            os.unlink(path)

    def test_invalid_yaml_returns_empty(self):
        path = _write_temp_file("not: valid: yaml: [")
        try:
            contexts = _parse_config_file(path)
            assert contexts == []
        finally:
            os.unlink(path)

    def test_non_kube_yaml_returns_empty(self):
        path = _write_temp_file("name: my-app\nversion: 1.0")
        try:
            contexts = _parse_config_file(path)
            assert contexts == []
        finally:
            os.unlink(path)

    def test_nonexistent_file_returns_empty(self):
        contexts = _parse_config_file("/nonexistent/path/file.yaml")
        assert contexts == []


class TestIsKubeConfig:
    """Test kubeconfig detection heuristic."""

    def test_kind_config(self):
        assert _is_kube_config({"kind": "Config", "clusters": []}) is True

    def test_clusters_and_contexts(self):
        assert _is_kube_config({"clusters": [], "contexts": []}) is True

    def test_apiversion_and_clusters(self):
        assert _is_kube_config({"apiVersion": "v1", "clusters": []}) is True

    def test_plain_dict(self):
        assert _is_kube_config({"name": "my-app"}) is False

    def test_non_dict(self):
        assert _is_kube_config("string") is False
        assert _is_kube_config(None) is False


# ── Tests: version parsing ────────────────────────────────────────────────────

class TestParseVersion:
    """Test semantic version parsing."""

    def test_standard_version(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_with_v_prefix(self):
        assert _parse_version("v1.2.3") == (1, 2, 3)

    def test_comparison(self):
        assert _parse_version("1.2.3") < _parse_version("1.2.4")
        assert _parse_version("1.2.3") < _parse_version("1.3.0")
        assert _parse_version("1.2.3") < _parse_version("2.0.0")
        assert _parse_version("0.5.1") > _parse_version("0.5.0")

    def test_invalid_version(self):
        assert _parse_version("abc") == (0, 0, 0)
        assert _parse_version("") == (0, 0, 0)


# ── Tests: system language detection ──────────────────────────────────────────

class TestSystemLanguage:
    """Test system language detection."""

    def test_returns_string(self):
        lang = get_system_language()
        assert lang in ("zh", "en")
