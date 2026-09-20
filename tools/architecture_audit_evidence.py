"""Join current source identities to recorded offline component checks.

This development projection does not run tests or infer provider readiness.
A recorded suite applies only to its complete declared source population.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT_CONTRACTS = ("pyproject.toml", "architecture.yaml", "terminology.yaml")


def source_identity(repository: Path) -> dict:
    """Hash package behavior and configuration, excluding generated reports."""
    package_paths = tuple((repository / "src/loop_engine").rglob("*"))
    if any(path.is_symlink() for path in package_paths):
        raise ValueError("source identity refuses package symbolic links")
    paths = [path for path in package_paths
             if path.is_file() and not path.is_symlink()
             and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
             and path.name != "architecture_conformance.json"]
    paths.extend(repository / name for name in ROOT_CONTRACTS)
    hashes = {path.relative_to(repository).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(paths) if path.is_file()}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"digest": digest, "files": hashes,
            "scope": "package code and data plus root architecture, terminology, and distribution contracts"}


def check_evidence(repository: Path, path: Path) -> dict:
    """Refuse stale or malformed evidence without turning it into a pass."""
    if not path.is_file():
        return {"state": "not_recorded", "modules": {}}
    report = json.loads(path.read_text("utf-8"))
    if report.get("record_type") != "architecture_check_capture/v1":
        raise ValueError("unsupported architecture check capture")
    before, after = report.get("source_before", {}), report.get("source_after", {})
    current = source_identity(repository)
    if before != after or after != current:
        return {"state": "stale_source", "modules": {}, "report": path.name,
                "detail": "recorded tests do not cover the complete current source identity"}
    modules = defaultdict(lambda: {"passed": 0, "failed": 0, "not_tested": 0})
    records = report.get("suite", {}).get("tests")
    if not isinstance(records, list) or not records:
        raise ValueError("architecture check capture has no test records")
    for row in records:
        owner = row.get("owner_module", "")
        if not isinstance(owner, str) or not owner.startswith("loop_engine."):
            raise ValueError("recorded checks need an engine-owned module identity")
        if row.get("not_tested") is True and row.get("passed") is None:
            modules[owner]["not_tested"] += 1
        elif type(row.get("passed")) is bool:
            modules[owner]["passed" if row["passed"] else "failed"] += 1
        else:
            raise ValueError("recorded checks need explicit pass, failure, or unavailable state")
    return {"state": "current_offline_evidence", "report": path.name,
            "source_digest": current["digest"], "modules": dict(modules),
            "counts": {key: sum(row[key] for row in modules.values())
                       for key in ("passed", "failed", "not_tested")},
            "provider_qualification": False,
            "detail": "module-owned offline checks; not complete behavioral coverage or observed provider use"}


def component_rows(inventory: dict) -> list[dict]:
    """Project one row per shipped Python file, keeping evidence axes separate."""
    closure = {name: set(report["modules"]) for name, report in inventory.get("entry_points", {}).items()}
    results = inventory.get("check_evidence", {}).get("modules", {})
    files = {row["path"]: row for row in inventory["files"]}
    rows = []
    for path, parsed in inventory["python"].items():
        if not path.startswith("src/loop_engine/"):
            continue
        module = parsed["module"]
        rows.append({
            "path": path, "module": module, "folder": files[path]["folder"],
            "description": parsed["module_description"], "source_sha256": files[path].get("sha256"),
            "lines": files[path].get("lines"),
            "classes": [row["name"] for row in parsed["symbols"] if row["kind"] == "class"],
            "public_callables": [row["name"] for row in parsed["symbols"]
                                 if row["kind"] == "function" and not row["name"].startswith("_")],
            "record_type_literals": sorted({row["value"] for row in parsed["references"]
                                             if row["kind"] == "record_type_literal"}),
            "static_import_paths": [name for name, modules in closure.items() if module in modules],
            "observed_invocation": "not_measured_by_this_inventory",
            "offline_checks": results.get(module),
            "test_declarations": len(parsed["tests"]),
            "review": files[path]["semantic_review"],
        })
    return rows
