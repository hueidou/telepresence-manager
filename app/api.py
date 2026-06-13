"""Python API exposed to the frontend via pywebview."""

import sys
from concurrent.futures import ThreadPoolExecutor
from app import kubeconfig, telepresence, updater, config
from app.logger import debug, info, error as log_error, exception


class Api:
    """API class exposed to JavaScript via pywebview js_api."""

    def __init__(self):
        self._current_version = None
        self._last_update_info = None

    def set_version(self, version):
        """Set the current app version (called from main)."""
        self._current_version = version
        info("App version set to %s", version)

    # ── Config ──────────────────────────────────────────────────────

    def get_config(self):
        """Load app config from ~/.kube/telepresence-manager.json.

        Returns dict with keys: language, refreshInterval.
        """
        return config.load()

    def save_config(self, cfg):
        """Save app config to ~/.kube/telepresence-manager.json.

        Args:
            cfg: dict of config values to save.

        Returns:
            dict: {success: bool, message: str}
        """
        if config.save(cfg):
            return {"success": True, "message": "Config saved"}
        return {"success": False, "message": "Failed to save config"}

    def get_system_language(self):
        """Detect system UI language.

        Returns:
            str: "zh" or "en"
        """
        return config.get_system_language()

    def check_tools(self):
        """Check if telepresence and kubectl are installed, return version and path info."""
        tp = telepresence.check_telepresence()
        kc = telepresence.check_kubectl()
        result = {
            "telepresence": tp["installed"],
            "kubectl": kc["installed"],
            "telepresence_version": tp["version"],
            "kubectl_version": kc["version"],
            "telepresence_path": tp["path"],
            "kubectl_path": kc["path"],
        }
        info("Tool check: telepresence=%s kubectl=%s", tp["installed"], kc["installed"])
        return result

    def scan_configs(self):
        """Scan ~/.kube/ for config files and return contexts."""
        contexts = kubeconfig.scan_kube_dir()
        info("Scanned %d contexts from ~/.kube/", len(contexts))
        return {"contexts": contexts}

    def connect(self, context, kubeconfig_path=None):
        """Connect telepresence to a cluster context."""
        info("Connecting to context: %s", context)
        result = telepresence.connect(context, kubeconfig_path)
        if result.get("success"):
            info("Connected to %s successfully", context)
        else:
            log_error("Connect to %s failed: %s", context, result.get("message"))
        return result

    def disconnect(self):
        """Disconnect telepresence."""
        info("Disconnecting telepresence")
        result = telepresence.disconnect()
        if result.get("success"):
            info("Disconnected successfully")
        else:
            log_error("Disconnect failed: %s", result.get("message"))
        return result

    def get_status(self, context=None):
        """Get telepresence connection status."""
        result = telepresence.get_status(context)
        debug("Status check: connected=%s", result.get("connected"))
        return result

    def get_nodes(self, context, kubeconfig_path=None):
        """Get cluster nodes."""
        return telepresence.get_nodes(context, kubeconfig_path)

    def get_full_status(self, context, kubeconfig_path=None):
        """Get combined status: telepresence status + nodes + traffic manager.

        Runs all queries in parallel for faster response.
        """
        info("Querying full status for context: %s", context)
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_tp = executor.submit(telepresence.get_status, context)
            f_nodes = executor.submit(telepresence.get_nodes, context, kubeconfig_path)
            f_cluster = executor.submit(telepresence.get_cluster_info, context, kubeconfig_path)
            f_tm = executor.submit(telepresence.check_traffic_manager, context, kubeconfig_path)

            result = {
                "telepresence": f_tp.result(),
                "nodes": f_nodes.result(),
                "cluster": f_cluster.result(),
                "traffic_manager_installed": f_tm.result()["installed"],
            }
            debug("Full status: connected=%s, nodes=%d, TM=%s",
                  result["telepresence"].get("connected"),
                  result["nodes"].get("count", 0),
                  result["traffic_manager_installed"])
            return result

    def install_traffic_manager(self, context, kubeconfig_path=None):
        """Install telepresence traffic manager."""
        info("Installing traffic manager for context: %s", context)
        return telepresence.install_traffic_manager(context, kubeconfig_path)

    def open_shell(self, context, kubeconfig_path=None):
        """Open a new terminal window with the given context."""
        info("Opening shell for context: %s", context)
        return telepresence.open_shell(context, kubeconfig_path)

    def check_update(self):
        """Check for application updates via GitHub Releases."""
        if not self._current_version:
            return {"available": False, "error": "Version not set"}
        info("Checking for updates (current: %s)", self._current_version)
        update_info = updater.check_for_update(self._current_version)
        self._last_update_info = update_info
        if update_info["available"]:
            info("Update available: %s", update_info["latest_version"])
        else:
            debug("No update available (current=%s)", self._current_version)
        return update_info

    def download_and_update(self):
        """Download the latest version and apply the update (restart app)."""
        if not self._current_version:
            return {"success": False, "message": "Version not set"}

        # Use cached info if available, otherwise fetch fresh
        update_info = self._last_update_info or updater.check_for_update(self._current_version)
        if not update_info["available"] or not update_info["download_url"]:
            return {"success": False, "message": "No update available"}

        info("Downloading update from: %s", update_info["download_url"])
        downloaded = updater.download_update(update_info["download_url"])
        if not downloaded:
            log_error("Download failed")
            return {"success": False, "message": "Download failed"}

        info("Downloaded to: %s, applying update...", downloaded)
        # Apply update (launches batch/shell script to replace exe)
        if updater.apply_update(downloaded):
            info("Update script launched, exiting current process")
            # Exit current process — the update script will handle the rest
            sys.exit(0)
        else:
            log_error("Failed to apply update")
            return {"success": False, "message": "Failed to apply update"}
