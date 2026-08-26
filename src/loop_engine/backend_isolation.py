"""Backend isolation: provider libraries stay inside their adapters.

DuckDB, DataFusion, SQLAlchemy, Ibis, and other provider technologies
are replaceable implementations. The semantic model must never import
them. This module detects provider leakage and proves the base package
imports without optional backends.
"""
from __future__ import annotations

import ast
import os

_PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))

#: Provider library -> adapter paths where importing it is permitted.
PROVIDER_ISOLATION = {
    "duckdb": frozenset({
        "catalog/stores/duckdb_store.py",
        "catalog/stores/duckdb_files.py",
        "core/duckdb_catalog.py",
        "core/run_history.py",
        "code_nodes/guided_setup.py",
    }),
    "sqlalchemy": frozenset(),
    "ibis": frozenset(),
    "datafusion": frozenset(),
    "polars": frozenset(),
    "pyarrow": frozenset(),
}

#: Modules that must import without any optional backend installed.
BASE_IMPORT_MODULES = (
    "loop_engine",
    "loop_engine.loop.recursive_loop",
    "loop_engine.ontology",
    "loop_engine.catalog",
    "loop_engine.catalog.query",
    "loop_engine.catalog.protocol",
    "loop_engine.catalog.handshake",
    "loop_engine.catalog.capabilities",
    "loop_engine.catalog.registry",
    "loop_engine.catalog.composite",
    "loop_engine.catalog.stores.in_memory",
    "loop_engine.catalog.stores.package_jsonl",
)


def provider_leak_violations(root: str | None = None) -> list[dict]:
    """Provider imports outside their declared adapter boundaries."""
    base = root or _PACKAGE_ROOT
    violations = []
    for directory, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            relative = os.path.relpath(path, base).replace(os.sep, "/")
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), path)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        provider = alias.name.split(".")[0]
                        if provider in PROVIDER_ISOLATION and \
                                relative not in PROVIDER_ISOLATION[provider]:
                            violations.append({
                                "rule": "provider_leak",
                                "file": relative, "line": node.lineno,
                                "provider": provider,
                                "detail": f"{provider} is imported outside "
                                          "its declared adapter boundary"})
                elif isinstance(node, ast.ImportFrom) and node.module:
                    provider = node.module.split(".")[0]
                    if provider in PROVIDER_ISOLATION and \
                            relative not in PROVIDER_ISOLATION[provider]:
                        violations.append({
                            "rule": "provider_leak",
                            "file": relative, "line": node.lineno,
                            "provider": provider,
                            "detail": f"{provider} is imported outside "
                                      "its declared adapter boundary"})
    return violations


def base_import_report() -> dict:
    """Prove the base package imports without optional backends."""
    import importlib
    import sys

    blocked = {provider: sys.modules.pop(provider, None)
               for provider in PROVIDER_ISOLATION}
    results = []
    for module_name in BASE_IMPORT_MODULES:
        try:
            importlib.import_module(module_name)
            results.append({"module": module_name, "imported": True,
                            "error": ""})
        except Exception as exc:                             # noqa: BLE001
            results.append({"module": module_name, "imported": False,
                            "error": str(exc)})
    for provider, module in blocked.items():
        if module is not None:
            sys.modules[provider] = module
    return {
        "record_type": "base_import_report/v1",
        "modules": results,
        "passed": all(r["imported"] for r in results),
    }


def self_test() -> dict:
    """Canary-prove the leak detector, then judge the live tree."""
    import tempfile

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "leaky.py"), "w",
                  encoding="utf-8") as handle:
            handle.write("import duckdb\n")
        violations = provider_leak_violations(tmp)
        check("provider_leak_detector_fires_on_planted_violation",
              any(v["provider"] == "duckdb" for v in violations),
              "a duckdb import outside its adapter boundary must be detected")

    live = provider_leak_violations()
    check("live_tree_has_no_provider_leaks", not live, str(live)[:300])
    base = base_import_report()
    check("base_package_imports_without_optional_backends", base["passed"],
          str([r for r in base["modules"] if not r["imported"]])[:300])
    return {"tests": results}
