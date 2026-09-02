"""Repository structure inspection: tree, files, folders, and drift detection.

This module provides the command-line structure tools: listing the
semantic folder tree, checking every folder against the architecture
contract, detecting unapproved variations, and producing a
machine-readable structure report that an LLM can answer questions
against.

The structure report is derived data. The authoritative rules live in
architecture.yaml, terminology.yaml, and the folder ontology.
"""
from __future__ import annotations

import os


_PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PACKAGE_ROOT))

#: Top-level folders the repository contract permits.
APPROVED_TOP_LEVEL = frozenset({
    "src", "tests", "docs", "examples", "benchmarks", "devtools",
    "migrations", "plugins", "runtime_plugins", "dev_plugins", "deploy",
    ".github", "case-studies", "showcase", "dist", "checkpoint",
    "example-output", "tools",
})

#: Junk-drawer names that must never appear as architecture folders.
FORBIDDEN_FOLDER_NAMES = frozenset({
    "utils", "helpers", "common", "misc", "shared", "legacy", "new", "v2",
    "temp", "tmp", "old", "backup", "stuff", "junk",
})

#: Semantic folders that must carry a README.
SEMANTIC_README_REQUIRED = frozenset({
    "ontology", "intelligence", "governance", "runtime", "kernel",
    "catalog", "node", "loop_node", "core",
})


def list_tree(root: str | None = None, *, max_depth: int = 4) -> list[dict]:
    """One record per directory: path, depth, children, has_readme."""
    base = root or _PACKAGE_ROOT
    records = []
    for directory, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in ("__pycache__", ".git"))
        relative = os.path.relpath(directory, base).replace(os.sep, "/")
        depth = 0 if relative == "." else relative.count("/") + 1
        if depth > max_depth:
            dirnames[:] = []
            continue
        records.append({
            "path": relative,
            "depth": depth,
            "subdirectories": list(dirnames),
            "files": sorted(filenames),
            "has_readme": "README.md" in filenames,
        })
    return records


def structure_violations(root: str | None = None) -> list[dict]:
    """Unapproved top-level folders, junk drawers, and missing READMEs.

    The top-level check applies only when the scan root is the repository
    root. When the scan root is the package root, top-level folders are
    package subpackages and are governed by the architecture map instead.
    """
    base = root or _PACKAGE_ROOT
    is_repo_root = os.path.basename(os.path.abspath(base)) == "loop-engine"
    violations = []
    for directory, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in ("__pycache__", ".git"))
        relative = os.path.relpath(directory, base).replace(os.sep, "/")
        depth = 0 if relative == "." else relative.count("/") + 1
        if depth == 0 and is_repo_root:
            for name in dirnames:
                if name not in APPROVED_TOP_LEVEL:
                    violations.append({
                        "rule": "unapproved_top_level_folder",
                        "path": name,
                        "detail": f"top-level folder {name!r} is not in the "
                                  "approved repository contract"})
        for name in dirnames:
            if name in FORBIDDEN_FOLDER_NAMES:
                violations.append({
                    "rule": "junk_drawer_folder",
                    "path": f"{relative}/{name}".strip("/"),
                    "detail": f"folder name {name!r} is a junk-drawer name"})
        if depth > 0 and relative.split("/")[-1] in SEMANTIC_README_REQUIRED \
                and "README.md" not in filenames:
            violations.append({
                "rule": "missing_semantic_readme",
                "path": relative,
                "detail": "semantic folder must carry a README.md"})
    return violations


def structure_report(root: str | None = None) -> dict:
    """Machine-readable structure report for humans and LLMs."""
    base = root or _PACKAGE_ROOT
    tree = list_tree(base)
    violations = structure_violations(base)
    return {
        "record_type": "repository_structure/v1",
        "root": base,
        "directories": len(tree),
        "violations": violations,
        "passed": not violations,
        "tree": tree,
    }


def render_structure_text(report: dict) -> str:
    """Human-readable tree with violation markers."""
    lines = ["REPOSITORY STRUCTURE"]
    for record in report["tree"]:
        depth = record["depth"]
        name = record["path"].split("/")[-1] if record["path"] != "." else "."
        prefix = "  " * depth
        marker = " [NO README]" if (
            record["path"].split("/")[-1] in SEMANTIC_README_REQUIRED
            and not record["has_readme"]) else ""
        lines.append(f"{prefix}{name}/{marker}")
    if report["violations"]:
        lines.append("")
        lines.append("VIOLATIONS")
        for violation in report["violations"]:
            lines.append(f"  {violation['rule']}: {violation['path']} - "
                         f"{violation['detail']}")
    else:
        lines.append("")
        lines.append("STRUCTURE PASSES")
    return "\n".join(lines)


def self_test() -> dict:
    """Canary-prove the structure detectors, then judge the live tree."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "loop-engine")
        os.makedirs(os.path.join(repo, "utils"))
        os.makedirs(os.path.join(repo, "unapproved_thing"))
        os.makedirs(os.path.join(repo, "src", "loop_engine", "kernel"))
        violations = structure_violations(repo)
        check("junk_drawer_folder_is_detected",
              any(v["rule"] == "junk_drawer_folder" for v in violations))
        check("unapproved_top_level_folder_is_detected",
              any(v["rule"] == "unapproved_top_level_folder"
                  and v["path"] == "unapproved_thing" for v in violations))
        check("missing_semantic_readme_is_detected",
              any(v["rule"] == "missing_semantic_readme"
                  and v["path"].endswith("kernel") for v in violations))

    live = structure_report()
    check("live_tree_passes_structure_checks", live["passed"],
          str(live["violations"])[:400])
    check("live_tree_reports_directories",
          live["directories"] > 20,
          f"reported {live['directories']} directories")
    return {"tests": results}
