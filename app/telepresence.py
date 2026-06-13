"""Telepresence and kubectl CLI wrappers."""

import subprocess
import json
import os
import shutil
import sys
from app.logger import debug, info, error as log_error, exception

# Cache for discovered executable paths
_tool_cache = {}


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
            full_path = find_executable(tool_name)
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
        debug("cmd=%s returncode=%d", resolved_cmd[0], r.returncode)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        log_error("Command not found: %s", resolved_cmd[0])
        return -1, "", f"Command not found: {resolved_cmd[0]}"
    except subprocess.TimeoutExpired:
        log_error("Command timed out: %s (timeout=%ds)", resolved_cmd[0], timeout)
        return -2, "", "Command timed out"


def find_executable(name):
    """Find full path of an executable, checking PATH and common install locations.

    Results are cached to avoid repeated filesystem scans.
    """
    if name in _tool_cache:
        return _tool_cache[name]

    path = shutil.which(name)
    if path:
        _tool_cache[name] = path
        return path

    # Check common Windows install locations
    if os.name == "nt":
        search_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Kubernetes"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Docker", "Docker", "resources", "bin"),
        ]
        # Also scan WinGet Packages for telepresence/kubectl
        winget_pkg = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
        if os.path.isdir(winget_pkg):
            search_paths.append(winget_pkg)

        target = f"{name}.exe"
        for base in search_paths:
            if not os.path.isdir(base):
                continue
            for root, dirs, files in os.walk(base):
                for f in files:
                    if f.lower() == target:
                        result = os.path.join(root, f)
                        _tool_cache[name] = result
                        return result
                # Limit recursion depth to 3 levels
                if root.count(os.sep) - base.count(os.sep) >= 3:
                    dirs.clear()

    elif sys.platform == "darwin":
        # macOS: check Homebrew and MacPorts locations
        search_paths = [
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/usr/local/bin",
            "/usr/local/kubectl/bin",
        ]
        for base in search_paths:
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate):
                _tool_cache[name] = candidate
                return candidate

    else:
        # Linux: check snap and flatpak locations
        search_paths = [
            "/snap/bin",
            "/var/lib/flatpak/exports/bin",
        ]
        for base in search_paths:
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate):
                _tool_cache[name] = candidate
                return candidate

    _tool_cache[name] = ""
    return ""


def check_telepresence():
    """Check if telepresence CLI is available and get version.

    Returns dict: {installed: bool, version: str|None, path: str}
    """
    path = find_executable("telepresence")
    if not path:
        return {"installed": False, "version": None, "path": ""}

    code, out, _ = _run(["telepresence", "version"])
    installed = code == 0 or "OSS Client" in out or "Client" in out
    version = out if out else None
    return {"installed": installed, "version": version, "path": path}


def check_kubectl():
    """Check if kubectl is available and get version.

    Returns dict: {installed: bool, version: str|None, path: str}
    """
    path = find_executable("kubectl")
    if not path:
        return {"installed": False, "version": None, "path": ""}

    code, out, _ = _run(["kubectl", "version", "--client"])
    version = out if code == 0 else None
    return {"installed": code == 0, "version": version, "path": path}


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
    env_extra = {"KUBECONFIG": kubeconfig_path} if kubeconfig_path else None

    for ns in ("ambassador", "default"):
        cmd = [
            "kubectl", "--context", context,
            "get", "deployment", "traffic-manager",
            "-n", ns,
            "-o", "jsonpath={.metadata.name}",
        ]
        code, out, _ = _run(cmd, timeout=10, env_extra=env_extra)
        if code == 0 and "traffic-manager" in out:
            return {"installed": True, "error": None}

    return {"installed": False, "error": None}


def install_traffic_manager(context, kubeconfig_path=None):
    """Install telepresence traffic manager via helm.

    Returns dict:
      {success: bool, message: str}
    """
    env_extra = {"KUBECONFIG": kubeconfig_path} if kubeconfig_path else None

    # Try install first
    cmd = ["telepresence", "helm", "install"]
    if context:
        cmd.extend(["--context", context])

    code, out, err = _run(cmd, timeout=120, env_extra=env_extra)
    if code == 0:
        return {"success": True, "message": out or "Traffic Manager installed"}

    # If already installed, try upgrade
    combined = (out or "") + (err or "")
    if "already installed" in combined.lower():
        cmd_upgrade = ["telepresence", "helm", "upgrade"]
        if context:
            cmd_upgrade.extend(["--context", context])
        code2, out2, err2 = _run(cmd_upgrade, timeout=120, env_extra=env_extra)
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

    env_extra = {"KUBECONFIG": kubeconfig_path} if kubeconfig_path else None

    code, out, err = _run(cmd, timeout=60, env_extra=env_extra)
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
    env_extra = {"KUBECONFIG": kubeconfig_path} if kubeconfig_path else None

    code, out, err = _run(cmd, timeout=15, env_extra=env_extra)
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
    env_extra = {"KUBECONFIG": kubeconfig_path} if kubeconfig_path else None

    code, out, err = _run(cmd, timeout=15, env_extra=env_extra)
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
    """Open a new terminal window with the given context.

    Platform support:
      - Windows: cmd.exe with CREATE_NEW_CONSOLE
      - macOS:   Terminal.app via osascript
      - Linux:   auto-detect gnome-terminal / konsole / xterm

    Returns dict:
      {success: bool, message: str}
    """
    # Build the shell init commands
    shell_parts = []
    if kubeconfig_path:
        if os.name == "nt":
            shell_parts.append(f'set "KUBECONFIG={kubeconfig_path}"')
        else:
            shell_parts.append(f'export KUBECONFIG="{kubeconfig_path}"')
    shell_parts.append(f"kubectl --context {context} cluster-info")
    shell_parts.append("echo.")
    shell_parts.append(f"echo Context: {context}")
    shell_parts.append("echo Type 'kubectl' to interact with the cluster.")

    try:
        if os.name == "nt":
            # ── Windows ──────────────────────────────────────
            shell_parts.append("cmd /k")
            inner_cmd = " & ".join(shell_parts)
            subprocess.Popen(
                ["cmd.exe", "/k", inner_cmd],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

        elif sys.platform == "darwin":
            # ── macOS ────────────────────────────────────────
            shell_cmd = "; ".join(shell_parts)
            # Use osascript to open a new Terminal window
            script = (
                f'tell application "Terminal"\n'
                f'  do script "{shell_cmd.replace(chr(34), chr(92) + chr(34))}; exec $SHELL"\n'
                f'  activate\n'
                f'end tell'
            )
            subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        else:
            # ── Linux ────────────────────────────────────────
            shell_cmd = "; ".join(shell_parts) + "; exec $SHELL"
            # Detect available terminal emulator
            terminals = ["gnome-terminal", "konsole", "xfce4-terminal", "lxterminal", "xterm"]
            term = None
            for t in terminals:
                if shutil.which(t):
                    term = t
                    break
            if not term:
                return {"success": False, "message": "No supported terminal found"}

            if term == "gnome-terminal":
                subprocess.Popen(
                    ["gnome-terminal", "--", "bash", "-c", shell_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif term in ("konsole", "xfce4-terminal", "lxterminal"):
                subprocess.Popen(
                    [term, "-e", "bash", "-c", shell_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                # xterm fallback
                subprocess.Popen(
                    ["xterm", "-e", "bash", "-c", shell_cmd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        platform_name = "Windows" if os.name == "nt" else ("macOS" if sys.platform == "darwin" else "Linux")
        info("Shell opened for context '%s' via %s", context, platform_name)
        return {"success": True, "message": "Shell opened"}

    except Exception as e:
        log_error("Failed to open shell for context '%s': %s", context, e)
        return {"success": False, "message": str(e)}
