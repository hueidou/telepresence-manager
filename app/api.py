"""Python API exposed to the frontend via pywebview."""

from app import kubeconfig, telepresence


class Api:
    """API class exposed to JavaScript via pywebview js_api."""

    def check_tools(self):
        """Check if telepresence and kubectl are installed, return version and path info."""
        tp = telepresence.check_installed()
        kc = telepresence.check_kubectl_installed()
        tp_ver = telepresence.get_telepresence_version() if tp else None
        kc_ver = telepresence.get_kubectl_version() if kc else None
        tp_path = telepresence.get_telepresence_path()
        kc_path = telepresence.get_kubectl_path()
        return {
            "telepresence": tp,
            "kubectl": kc,
            "telepresence_version": tp_ver,
            "kubectl_version": kc_ver,
            "telepresence_path": tp_path,
            "kubectl_path": kc_path,
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
        """Get combined status: telepresence status + nodes + traffic manager."""
        tp_status = telepresence.get_status(context)
        nodes = telepresence.get_nodes(context, kubeconfig_path)
        cluster = telepresence.get_cluster_info(context, kubeconfig_path)
        tm = telepresence.check_traffic_manager(context, kubeconfig_path)
        return {
            "telepresence": tp_status,
            "nodes": nodes,
            "cluster": cluster,
            "traffic_manager_installed": tm["installed"],
        }

    def install_traffic_manager(self, context, kubeconfig_path=None):
        """Install telepresence traffic manager."""
        return telepresence.install_traffic_manager(context, kubeconfig_path)

    def open_shell(self, context, kubeconfig_path=None):
        """Open a new cmd.exe shell with the given context."""
        return telepresence.open_shell(context, kubeconfig_path)
