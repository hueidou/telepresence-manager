"""Kubeconfig file discovery and parsing."""

import os
import glob
import yaml


def scan_kube_dir(kube_dir=None):
    """Scan ~/.kube/ for valid kubernetes config files.

    Returns list of dicts:
      {name, cluster, server, source_file, is_current}
    """
    if kube_dir is None:
        kube_dir = os.path.join(os.path.expanduser("~"), ".kube")

    if not os.path.isdir(kube_dir):
        return []

    results = []
    # Collect all files: config, *.txt, and any other non-hidden files
    patterns = [
        os.path.join(kube_dir, "config"),
        os.path.join(kube_dir, "*.txt"),
        os.path.join(kube_dir, "*.yml"),
        os.path.join(kube_dir, "*.yaml"),
    ]
    seen = set()
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            if filepath not in seen:
                seen.add(filepath)
                results.append(filepath)

    # Also pick up any other regular files not matched above
    for entry in os.listdir(kube_dir):
        full = os.path.join(kube_dir, entry)
        if os.path.isfile(full) and full not in seen and not entry.startswith("."):
            seen.add(full)
            results.append(full)

    contexts = []
    for filepath in results:
        parsed = _parse_config_file(filepath)
        contexts.extend(parsed)

    return contexts


def _parse_config_file(filepath):
    """Parse a single file, return list of context dicts if valid k8s config."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    # Try parsing as YAML (may be multi-document)
    try:
        docs = list(yaml.safe_load_all(content))
    except yaml.YAMLError:
        return []

    results = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        # Heuristic: valid k8s config must have 'clusters' or 'contexts' key
        if not _is_kube_config(doc):
            continue

        current_ctx = doc.get("current-context", "")
        clusters_map = {}
        for c in doc.get("clusters", []):
            if isinstance(c, dict) and "name" in c and "cluster" in c:
                clusters_map[c["name"]] = c["cluster"].get("server", "")

        for ctx in doc.get("contexts", []):
            if not isinstance(ctx, dict) or "name" not in ctx:
                continue
            ctx_detail = ctx.get("context", {})
            cluster_name = ctx_detail.get("cluster", "")
            results.append({
                "name": ctx["name"],
                "cluster": cluster_name,
                "server": clusters_map.get(cluster_name, ""),
                "source_file": filepath,
                "is_current": ctx["name"] == current_ctx,
            })

    return results


def _is_kube_config(doc):
    """Check if a YAML document looks like a kubernetes config."""
    if not isinstance(doc, dict):
        return False
    # Must have apiVersion or clusters/contexts
    if doc.get("kind") == "Config":
        return True
    if "clusters" in doc and "contexts" in doc:
        return True
    if "apiVersion" in doc and ("clusters" in doc or "users" in doc):
        return True
    return False
