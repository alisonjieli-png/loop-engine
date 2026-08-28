"""Repository component and symbol inventory through the canonical Loop.

The inventory is an audit projection, not a source of runtime authority. It
parses every first-party Python file, lists material symbols without guessing
their semantics, and joins explicit component, interaction, folder, and strict
native-operation records from their canonical sources.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from ..loop.atomic_primitives import ATOMIC_PRIMITIVES
from ..loop.encapsulate import as_practitioner_loop
from .component_contracts import load_component_resource
from .practitioner_context import load_practitioner_context
from .primitive_conformance import scan_native_semantic_operations
from .runtime_settings import RuntimeSettings


@dataclass(frozen=True)
class ComponentInventoryRequest:
    """One package root to inspect without modifying it."""

    package_root: str

    def __post_init__(self) -> None:
        root = Path(self.package_root)
        if not root.is_dir() or not (root / "__init__.py").is_file():
            raise ValueError("component inventory needs a Python package root")


def _file_record(path: Path, root: Path, tree: ast.Module) -> dict:
    relative = path.relative_to(root).as_posix()
    public = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                public.append(node.name)
    return {
        "record_type": "component_file_inventory/v1",
        "path": relative,
        "module": relative[:-3].replace("/", "."),
        "folder_semantic_owner": relative.split("/", 1)[0],
        "public_symbols": public,
        "class_count": sum(isinstance(node, ast.ClassDef)
                           for node in ast.walk(tree)),
        "function_count": sum(isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef))
            for node in ast.walk(tree)),
        "import_count": sum(isinstance(
            node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)),
        "semantic_classification": "requires_explicit_component_mapping",
    }


def _symbol_records(path: Path, root: Path, tree: ast.Module) -> list[dict]:
    relative = path.relative_to(root).as_posix()
    records = []
    for node in tree.body:
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        records.append({
            "record_type": "component_symbol_inventory/v1",
            "path": relative,
            "symbol": node.name,
            "symbol_kind": (
                "class" if isinstance(node, ast.ClassDef) else "function"),
            "public": not node.name.startswith("_"),
            "line": node.lineno,
            "component_mapping": "unclassified",
            "runtime_or_passive": "requires_review",
            "tests": [],
        })
    return records


def _explicit_components() -> list[dict]:
    portfolio = load_practitioner_context()
    values = [portfolio.component_definition().to_dict()]
    values.extend(item.component_definition().to_dict()
                  for item in portfolio.guidance)
    values.extend(item.component_definition().to_dict()
                  for item in portfolio.perspectives)
    values.append(portfolio.persona.component_definition().to_dict())
    values.extend(item.component_definition().to_dict()
                  for item in portfolio.steps)
    values.extend(item.component_definition().to_dict()
                  for item in portfolio.assembly_profiles)
    values.append(RuntimeSettings().component_definition().to_dict())
    values.extend({
        "record_type": "atomic_primitive_definition/v1",
        "primitive_id": item.primitive_id,
        "input_contract_refs": list(item.input_contract_refs),
        "output_contract_ref": item.output_contract_ref,
        "intrinsic_id": item.intrinsic_id,
        "default_mode": item.default_mode,
        "purity": item.purity,
        "idempotent": item.idempotent,
        "cacheable": item.cacheable,
        "fusion_allowed": item.fusion_allowed,
    } for item in ATOMIC_PRIMITIVES.values())
    return values


def _build_inventory(request: ComponentInventoryRequest) -> dict:
    root = Path(request.package_root).resolve()
    files = []
    symbols = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        files.append(_file_record(path, root, tree))
        symbols.extend(_symbol_records(path, root, tree))
    interactions = load_component_resource(
        "component_interactions.yaml", "component_interaction_catalog/v1")
    folders = load_component_resource(
        "component_folder_map.yaml", "component_folder_map/v1")
    return {
        "record_type": "repository_component_inventory/v1",
        "package_root": str(root),
        "files": files,
        "symbols": symbols,
        "explicit_components": _explicit_components(),
        "interactions": interactions["interactions"],
        "folder_map": folders,
        "native_semantic_operations": scan_native_semantic_operations(root),
    }


def run_component_inventory(request: ComponentInventoryRequest) -> dict:
    """Build the read-only inventory inside a deterministic Practitioner Loop."""
    if not isinstance(request, ComponentInventoryRequest):
        raise TypeError("run_component_inventory needs ComponentInventoryRequest")
    wrapped = as_practitioner_loop(
        "inventory repository components", lambda: _build_inventory(request))
    return {**wrapped["value"], "inventory_loop_id": wrapped["loop_id"]}


def self_test() -> dict:
    """Prove the current package is inventoried through one Loop."""
    root = Path(__file__).resolve().parents[1]
    inventory = run_component_inventory(ComponentInventoryRequest(str(root)))
    tests = [{
        "test": "component_inventory_runs_through_practitioner_loop",
        "passed": inventory["inventory_loop_id"].startswith("loop"),
        "detail": inventory["inventory_loop_id"],
    }, {
        "test": "component_inventory_covers_every_python_file",
        "passed": len(inventory["files"]) == len(tuple(root.rglob("*.py"))),
        "detail": "full first-party Python inventory",
    }, {
        "test": "component_inventory_preserves_unclassified_symbols",
        "passed": any(item["component_mapping"] == "unclassified"
                      for item in inventory["symbols"]),
        "detail": "unknown semantics are not guessed",
    }]
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "component_inventory_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
