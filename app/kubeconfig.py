"""Kubeconfig file discovery and parsing."""

import os
import yaml
from app.logger import debug, info, error as log_error


def scan_kube_dir(kube_dir=None):
    """Scan ~/.kube/ for valid kubernetes config files.

    Returns list of dicts:
      {name, cluster, server, source_file, is_current}
    """
    if kube_dir is None:
        kube_dir = os.path.join(os.path.expanduser("~"), ".kube")

    if not os.path.isdir(kube_dir):
        debug("kube dir not found: %s", kube_dir)
        return []

    # Collect all non-hidden files in ~/.kube/
    filepaths = []
    for entry in os.listdir(kube_dir):
        if entry.startswith("."):
            continue
        full = os.path.join(kube_dir, entry)
        if os.path.isfile(full):
            filepaths.append(full)

    info("Scanning %d files in %s", len(filepaths), kube_dir)
    contexts = []
    for filepath in sorted(filepaths):
        parsed = _parse_config_file(filepath)
        if parsed:
            debug("Parsed %d contexts from %s", len(parsed), filepath)
        contexts.extend(parsed)

    info("Found %d contexts total", len(contexts))
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
    if doc.get("kind") == "Config":
        return True
    if "clusters" in doc and "contexts" in doc:
        return True
    if "apiVersion" in doc and ("clusters" in doc or "users" in doc):
        return True
    return False
