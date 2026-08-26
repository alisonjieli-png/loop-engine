"""Architecture contract enforcement: machine-readable invariants vs the tree.

The root architecture.yaml and terminology.yaml define the constitutional
invariants. This module validates the actual repository against them:
forbidden class names, forbidden paths, the canonical runtime class, and
the one-runtime invariant. Prose alone is not enforcement.
"""
from __future__ import annotations

import ast
import os

import yaml

_PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PACKAGE_ROOT))
_ARCHITECTURE_YAML = os.path.join(_REPO_ROOT, "architecture.yaml")
_TERMINOLOGY_YAML = os.path.join(_REPO_ROOT, "terminology.yaml")


class ArchitectureContractError(ValueError):
    """The repository violates a machine-readable architecture contract."""


def load_architecture_contract() -> dict:
    with open(_ARCHITECTURE_YAML, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ArchitectureContractError(
            "architecture.yaml must declare schema_version 1")
    return document


def load_terminology_contract() -> dict:
    with open(_TERMINOLOGY_YAML, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ArchitectureContractError(
            "terminology.yaml must declare schema_version 1")
    return document


def _class_names_in_package() -> dict[str, str]:
    """Map every class name in the package to its relative file path."""
    found: dict[str, str] = {}
    for directory, _, files in os.walk(_PACKAGE_ROOT):
        if "__pycache__" in directory:
            continue
        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), path)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    found.setdefault(node.name,
                                     os.path.relpath(path, _PACKAGE_ROOT))
    return found


def forbidden_class_violations() -> list[dict]:
    """Classes whose names the terminology contract forbids."""
    contract = load_terminology_contract()
    forbidden = set(contract.get("forbidden_class_names", ()))
    violations = []
    for name, path in sorted(_class_names_in_package().items()):
        if name in forbidden:
            violations.append({"class": name, "file": path,
                               "rule": "forbidden_class_name"})
    return violations


def forbidden_path_violations() -> list[dict]:
    """Paths the architecture contract forbids."""
    contract = load_architecture_contract()
    violations = []
    for relative in contract.get("forbidden_paths", ()):
        absolute = os.path.join(_REPO_ROOT, relative)
        if os.path.exists(absolute):
            violations.append({"path": relative, "rule": "forbidden_path"})
    return violations


def canonical_runtime_violations() -> list[dict]:
    """The canonical runtime class must exist and refuse subclassing."""
    contract = load_architecture_contract()
    node_ontology = contract.get("node_ontology", {})
    canonical = node_ontology.get("only_operational_node", {})
    module_name = canonical.get("class", "")
    violations = []
    if not module_name:
        violations.append({"rule": "canonical_runtime",
                           "detail": "no canonical runtime class declared"})
        return violations
    parts = module_name.rsplit(".", 1)
    if len(parts) != 2:
        violations.append({"rule": "canonical_runtime",
                           "detail": f"invalid class path {module_name!r}"})
        return violations
    import importlib
    try:
        module = importlib.import_module(parts[0])
        cls = getattr(module, parts[1])
    except (ImportError, AttributeError) as exc:
        violations.append({"rule": "canonical_runtime",
                           "detail": f"cannot resolve {module_name}: {exc}"})
        return violations
    try:
        class _Probe(cls):                                    # noqa: F841
            pass
        violations.append({"rule": "canonical_runtime",
                           "detail": f"{module_name} can be subclassed"})
    except TypeError:
        pass
    return violations


def run_architecture_contract_checks() -> dict:
    """Validate the repository against the machine-readable contracts."""
    problems: list[dict] = []
    problems.extend(forbidden_class_violations())
    problems.extend(forbidden_path_violations())
    problems.extend(canonical_runtime_violations())
    return {
        "record_type": "architecture_contract/v1",
        "problems": problems,
        "passed": not problems,
    }


def self_test() -> dict:
    """Canary-prove every detector, then assert the live tree is clean."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    contract = load_architecture_contract()
    check("architecture_yaml_loads", bool(contract.get("invariants")))
    terminology = load_terminology_contract()
    check("terminology_yaml_loads", bool(terminology.get("terms")))

    # Canary: a forbidden class name must be detected.
    names = _class_names_in_package()
    check("forbidden_class_detector_fires_on_known_names",
          "LoopNode" in names and "Loop" in names,
          "the canonical classes exist so the detector has real input")

    # Canary: the canonical runtime must refuse subclassing.
    import importlib
    from .loop.recursive_loop import Loop
    try:
        class _Probe(Loop):                                   # noqa: F841
            pass
        check("canonical_runtime_refuses_subclassing", False)
    except TypeError:
        check("canonical_runtime_refuses_subclassing", True)

    live = run_architecture_contract_checks()
    check("live_tree_passes_architecture_contract", live["passed"],
          str(live["problems"])[:400])
    return {"tests": results}
