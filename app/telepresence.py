"""Telepresence and kubectl CLI wrappers."""

import subprocess
import json
import os
import shutil


def _run(cmd, timeout=30, env_extra=None):
    """Run a command, return (returncode, stdout, stderr)."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    # Resolve full path for known tools if not already absolute
    resolved_cmd = list(cmd)
    if resolved_cmd and not os.path.isabs(resolved_cmd[0]):
        tool_name = os.path.basename(resolved_cmd[0]).replace(".exe", "")
        if tool_name in ("telepresence", "kubectl"):
            full_path = _find_executable(tool_name)
            if full_path:
                resolved_cmd[0] = full_path

    try:
        r = subprocess.run(
            resolved_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Command not found: {resolved_cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", "Command timed out"


def _find_executable(name):
    """Find full path of an executable, checking PATH and common install locations."""
    path = shutil.which(name)
    if path:
        return path
    # Check common Windows install locations
    if os.name == "nt":
        search_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Kubernetes"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Docker", "Docker", "resources", "bin"),
        ]
        for base in search_paths:
            if not os.path.isdir(base):
                continue
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.lower() == f"{name}.exe":
                        return os.path.join(root, f)
                # Don't recurse too deep
                if root.count(os.sep) - base.count(os.sep) >= 3:
                    dirs.clear()
    return ""


def check_installed():
    """Check if telepresence CLI is available."""
    path = _find_executable("telepresence")
    if not path:
        return False
    # Also try running version (may fail if daemon not running, but binary exists)
    code, out, err = _run(["telepresence", "version"])
    return code == 0 or "OSS Client" in out or "Client" in out


def get_telepresence_version():
    """Get telepresence version string."""
    code, out, err = _run(["telepresence", "version"])
    if out:
        return out
    return None


def get_telepresence_path():
    """Get telepresence executable path."""
    return _find_executable("telepresence")


def check_kubectl_installed():
    """Check if kubectl is available."""
    code, out, err = _run(["kubectl", "version", "--client"])
    return code == 0


def get_kubectl_version():
    """Get kubectl version string."""
    code, out, err = _run(["kubectl", "version", "--client"])
    if code == 0:
        return out
    return None


def get_kubectl_path():
    """Get kubectl executable path."""
    return _find_executable("kubectl")


def get_status(context=None):
    """Get telepresence connection status.

    Returns dict:
      {connected: bool, user_daemon: str, root_daemon: str, traffic_manager: str, version: str, error: str|None}
    """
    cmd = ["telepresence", "status"]

    code, out, err = _run(cmd, timeout=15)
    raw = out if out else err

    # Parse each field from raw output
    result = {
        "connected": False,
        "user_daemon": "Unknown",
        "root_daemon": "Unknown",
        "traffic_manager": "Unknown",
        "version": "",
        "error": None,
    }

    for line in raw.split("\n"):
        line = line.strip()
        if not line or "has been deprecated" in line.lower():
            continue
        lower = line.lower()
        if "user daemon" in lower:
            result["user_daemon"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif "root daemon" in lower:
            result["root_daemon"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif "traffic manager" in lower:
            result["traffic_manager"] = line.split(":", 1)[-1].strip() if ":" in line else line
        elif lower.startswith("version"):
            result["version"] = line.split(":", 1)[-1].strip() if ":" in line else line

    result["connected"] = result["traffic_manager"].lower() == "connected"
    if code != 0 and not any(v != "Unknown" for v in [result["user_daemon"], result["root_daemon"], result["traffic_manager"]]):
        result["error"] = raw

    return result


def check_traffic_manager(context, kubeconfig_path=None):
    """Check if traffic manager is installed in the cluster.

    Returns dict:
      {installed: bool, error: str|None}
    """
    env_extra = {}
    if kubeconfig_path:
        env_extra["KUBECONFIG"] = kubeconfig_path

    # Try kubectl to check for traffic-manager deployment
    cmd = [
        "kubectl", "--context", context,
        "get", "deployment", "traffic-manager",
        "-n", "ambassador",
        "-o", "jsonpath={.metadata.name}",
    ]
    code, out, err = _run(cmd, timeout=10, env_extra=env_extra or None)
    if code == 0 and "traffic-manager" in out:
        return {"installed": True, "error": None}

    # Also check in default namespace
    cmd[5] = "default"
    code, out, err = _run(cmd, timeout=10, env_extra=env_extra or None)
    if code == 0 and "traffic-manager" in out:
        return {"installed": True, "error": None}

    return {"installed": False, "error": None}


def install_traffic_manager(context, kubeconfig_path=None):
    """Install telepresence traffic manager via helm.

    Returns dict:
      {success: bool, message: str}
    """
    env_extra = {}
    if kubeconfig_path:
        env_extra["KUBECONFIG"] = kubeconfig_path

    # Try install first
    cmd = ["telepresence", "helm", "install"]
    if context:
        cmd.extend(["--context", context])

    code, out, err = _run(cmd, timeout=120, env_extra=env_extra or None)
    if code == 0:
        return {"success": True, "message": out or "Traffic Manager installed"}

    # If already installed, try upgrade
    combined = (out or "") + (err or "")
    if "already installed" in combined.lower():
        cmd_upgrade = ["telepresence", "helm", "upgrade"]
        if context:
            cmd_upgrade.extend(["--context", context])
        code2, out2, err2 = _run(cmd_upgrade, timeout=120, env_extra=env_extra or None)
        if code2 == 0:
            return {"success": True, "message": out2 or "Traffic Manager upgraded"}
        return {"success": False, "message": err2 or out2 or "Upgrade failed"}

    return {"success": False, "message": err or out or "Install failed"}


def connect(context, kubeconfig_path=None):
    """Connect telepresence to a cluster context.

    Returns dict:
      {success: bool, message: str}
    """
    cmd = ["telepresence", "connect"]
    if context:
        cmd.extend(["--context", context])

    env_extra = {}
    if kubeconfig_path:
        env_extra["KUBECONFIG"] = kubeconfig_path

    code, out, err = _run(cmd, timeout=60, env_extra=env_extra or None)
    if code == 0:
        return {"success": True, "message": out or "Connected successfully"}
    return {"success": False, "message": err or out or "Connection failed"}


def disconnect():
    """Disconnect telepresence.

    Returns dict:
      {success: bool, message: str}
    """
    code, out, err = _run(["telepresence", "quit"], timeout=15)
    if code == 0:
        return {"success": True, "message": out or "Disconnected"}
    return {"success": False, "message": err or out or "Disconnect failed"}


def get_nodes(context, kubeconfig_path=None):
    """Get cluster nodes info via kubectl.

    Returns dict:
      {count: int, nodes: list, error: str|None}
    """
    cmd = ["kubectl", "--context", context, "get", "nodes", "-o", "json"]
    env_extra = {}
    if kubeconfig_path:
        env_extra["KUBECONFIG"] = kubeconfig_path

    code, out, err = _run(cmd, timeout=15, env_extra=env_extra or None)
    if code != 0:
        return {"count": 0, "nodes": [], "error": err or out}

    try:
        data = json.loads(out)
        items = data.get("items", [])
        nodes = []
        for item in items:
            name = item.get("metadata", {}).get("name", "unknown")
            status = "Ready"
            for cond in item.get("status", {}).get("conditions", []):
                if cond.get("type") == "Ready":
                    status = "Ready" if cond.get("status") == "True" else "NotReady"
                    break
            nodes.append({"name": name, "status": status})
        return {"count": len(nodes), "nodes": nodes, "error": None}
    except (json.JSONDecodeError, KeyError):
        return {"count": 0, "nodes": [], "error": "Failed to parse kubectl output"}


def get_cluster_info(context, kubeconfig_path=None):
    """Get cluster info summary.

    Returns dict:
      {connected: bool, server: str, error: str|None}
    """
    cmd = ["kubectl", "--context", context, "cluster-info"]
    env_extra = {}
    if kubeconfig_path:
        env_extra["KUBECONFIG"] = kubeconfig_path

    code, out, err = _run(cmd, timeout=15, env_extra=env_extra or None)
    if code == 0:
        # Extract control plane URL from output
        server = ""
        for line in out.split("\n"):
            if "is running at" in line:
                server = line.strip()
                break
        return {"connected": True, "server": server or out, "error": None}
    return {"connected": False, "server": "", "error": err or out}


def open_shell(context, kubeconfig_path=None):
    """Open a new cmd.exe window with the given context.

    Returns dict:
      {success: bool, message: str}
    """
    if os.name != "nt":
        return {"success": False, "message": "Only Windows is supported"}

    # Build the command to run in the new shell
    parts = []
    if kubeconfig_path:
        parts.append(f'set "KUBECONFIG={kubeconfig_path}"')
    parts.append(f"kubectl --context {context} cluster-info")
    parts.append("echo.")
    parts.append(f"echo Context: {context}")
    parts.append("echo Type 'kubectl' to interact with the cluster.")
    parts.append("cmd /k")

    inner_cmd = " & ".join(parts)

    try:
        subprocess.Popen(
            ["cmd.exe", "/k", inner_cmd],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return {"success": True, "message": "Shell opened"}
    except Exception as e:
        return {"success": False, "message": str(e)}
