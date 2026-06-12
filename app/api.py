"""Python API exposed to the frontend via pywebview."""

import sys
from concurrent.futures import ThreadPoolExecutor
from app import kubeconfig, telepresence, updater


class Api:
    """API class exposed to JavaScript via pywebview js_api."""

    def __init__(self):
        self._current_version = None

    def set_version(self, version):
        """Set the current app version (called from main)."""
        self._current_version = version

    def check_tools(self):
        """Check if telepresence and kubectl are installed, return version and path info."""
        tp = telepresence.check_telepresence()
        kc = telepresence.check_kubectl()
        return {
            "telepresence": tp["installed"],
            "kubectl": kc["installed"],
            "telepresence_version": tp["version"],
            "kubectl_version": kc["version"],
            "telepresence_path": tp["path"],
            "kubectl_path": kc["path"],
        }

    def scan_configs(self):
        """Scan ~/.kube/ for config files and return contexts."""
        contexts = kubeconfig.scan_kube_dir()
        return {"contexts": contexts}

    def connect(self, context, kubeconfig_path=None):
        """Connect telepresence to a cluster context."""
        return telepresence.connect(context, kubeconfig_path)

    def disconnect(self):
        """Disconnect telepresence."""
        return telepresence.disconnect()

    def get_status(self, context=None):
        """Get telepresence connection status."""
        return telepresence.get_status(context)

    def get_nodes(self, context, kubeconfig_path=None):
        """Get cluster nodes."""
        return telepresence.get_nodes(context, kubeconfig_path)

    def get_full_status(self, context, kubeconfig_path=None):
        """Get combined status: telepresence status + nodes + traffic manager.

        Runs all queries in parallel for faster response.
        """
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_tp = executor.submit(telepresence.get_status, context)
            f_nodes = executor.submit(telepresence.get_nodes, context, kubeconfig_path)
            f_cluster = executor.submit(telepresence.get_cluster_info, context, kubeconfig_path)
            f_tm = executor.submit(telepresence.check_traffic_manager, context, kubeconfig_path)

            return {
                "telepresence": f_tp.result(),
                "nodes": f_nodes.result(),
                "cluster": f_cluster.result(),
                "traffic_manager_installed": f_tm.result()["installed"],
            }

    def install_traffic_manager(self, context, kubeconfig_path=None):
        """Install telepresence traffic manager."""
        return telepresence.install_traffic_manager(context, kubeconfig_path)

    def open_shell(self, context, kubeconfig_path=None):
        """Open a new cmd.exe shell with the given context."""
        return telepresence.open_shell(context, kubeconfig_path)

    def check_update(self):
        """Check for application updates via GitHub Releases."""
        if not self._current_version:
            return {"available": False, "error": "Version not set"}
        return updater.check_for_update(self._current_version)

    def download_and_update(self):
        """Download the latest version and apply the update (restart app)."""
        if not self._current_version:
            return {"success": False, "message": "Version not set"}

        # Check for update first to get download URL
        info = updater.check_for_update(self._current_version)
        if not info["available"] or not info["download_url"]:
            return {"success": False, "message": "No update available"}

        # Download
        downloaded = updater.download_update(info["download_url"])
        if not downloaded:
            return {"success": False, "message": "Download failed"}

        # Apply update (launches batch script to replace exe)
        if updater.apply_update(downloaded):
            # Exit current process — the batch script will handle the rest
            sys.exit(0)
        else:
            return {"success": False, "message": "Failed to apply update"}
