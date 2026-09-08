"""Reachability: which capability modules a live entry point can actually reach.

A module with passing self-tests and no caller is proven correct and inert.
The self-test total counts it, the conformance gates classify it, and no run
ever executes it. A measurement of this repository on 2026-09-07 found that an
end to end solve imported 129 of 406 modules, and one of twenty memory
modules, while every one of those memory modules held typed records and
passing tests.

This module measures reachability as a static import closure: starting at an
entry point, follow every import in every reached module, including imports
written inside functions, because a lazily imported module is still wired.
That is the generous reading, so a module this report calls dark is dark under
any reading.

An inventory names the modules each entry point is expected to reach. One that
is not reachable fails with its name in the message. The count of modules
outside the inventory is reported and never gated, because the command line
interface, the studio, the record tooling and the benchmarks are separate
entry points with their own legitimate module sets.

Owns:
    - reachability_report(): the measurement for one entry point.
    - REQUIRED_REACHABLE: what each entry point must reach.

Does not own: the entry points themselves, or what any module does once it is
reached.
"""
from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = "loop_engine"

#: Live entry points, named by the module a caller actually imports.
#: The curated public API in ``__init__`` resolves its names lazily from a map
#: of strings, so no static reader can follow it. The entry module named here
#: is therefore the one that actually runs the work, not the facade.
LIVE_ENTRY_POINTS = {
    "solve_path": f"{PACKAGE}.code_nodes.solve_runtime",
    "command_line": f"{PACKAGE}.__main__",
}

#: What each entry point must reach. This is an inventory of capability, not
#: an allowlist of everything present: a module belongs here once something on
#: the path is supposed to use it, and its absence is then a defect rather
#: than a preference. Entries are added as capability is wired, so the list
#: grows only when the engine genuinely reaches further.
REQUIRED_REACHABLE = {
    "solve_path": (
        # the two pre-check projections the solve path applies
        f"{PACKAGE}.code_nodes.solve_region_evidence",
        f"{PACKAGE}.code_nodes.solve_learned_memory",
        # the governed learning journal the second projection reads
        f"{PACKAGE}.memory.storage.learning_cycle",
        f"{PACKAGE}.memory.storage.learning_records",
        f"{PACKAGE}.memory.storage.store",
        f"{PACKAGE}.memory.query.query",
        f"{PACKAGE}.memory.semantic.record",
        f"{PACKAGE}.memory.model.memory_type",
    ),
}


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _module_name(path: Path, root: Path) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    return ".".join((PACKAGE,) + parts)


def shipped_modules() -> dict:
    """Every shipped module name mapped to its file."""
    root = _package_root()
    return {_module_name(path, root): path
            for path in sorted(root.rglob("*.py"))
            if "__pycache__" not in str(path)}


def _imports_of(path: Path, module: str) -> set:
    """Absolute in-package module names this file imports, at any depth."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError):
        return set()
    package_parts = module.split(".")
    if path.name == "__init__.py":
        package_parts = package_parts[:-1] if package_parts[-1] == "__init__" \
            else package_parts
    else:
        package_parts = package_parts[:-1]
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(PACKAGE):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[:len(package_parts) - node.level + 1]
                target = list(base) + ([node.module] if node.module else [])
            elif node.module and node.module.startswith(PACKAGE):
                target = node.module.split(".")
            else:
                continue
            prefix = ".".join(target)
            found.add(prefix)
            for alias in node.names:
                found.add(f"{prefix}.{alias.name}")
    return found


def _resolve(name: str, shipped: dict) -> "str | None":
    """A dotted name to the module that provides it, if any."""
    if name in shipped:
        return name
    package_init = f"{name}.__init__"
    if package_init in shipped:
        return package_init
    parent = name.rsplit(".", 1)[0] if "." in name else ""
    if parent and parent in shipped:
        return parent
    parent_init = f"{parent}.__init__" if parent else ""
    return parent_init if parent_init in shipped else None


def reachable_from(entry_module: str) -> set:
    """The static import closure of one entry module."""
    shipped = shipped_modules()
    start = _resolve(entry_module, shipped)
    if start is None:
        raise ValueError(f"entry module {entry_module!r} is not shipped")
    seen, pending = set(), [start]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for name in _imports_of(shipped[current], current):
            resolved = _resolve(name, shipped)
            if resolved is not None and resolved not in seen:
                pending.append(resolved)
    return seen


def reachability_report(entry_point: str = "solve_path") -> dict:
    """Measure one entry point: what it reaches, and what it must reach."""
    if entry_point not in LIVE_ENTRY_POINTS:
        raise ValueError(
            f"unknown entry point {entry_point!r}; "
            f"declared: {sorted(LIVE_ENTRY_POINTS)}")
    shipped = shipped_modules()
    reached = reachable_from(LIVE_ENTRY_POINTS[entry_point])
    required = set(REQUIRED_REACHABLE.get(entry_point, ()))
    undeclared = sorted(item for item in required if item not in shipped)
    dark = sorted(required - reached - set(undeclared))
    return {
        "record_type": "reachability_report/v1",
        "entry_point": entry_point,
        "entry_module": LIVE_ENTRY_POINTS[entry_point],
        "shipped_modules": len(shipped),
        "reached_modules": len(reached),
        "required_modules": len(required),
        "dark_required_modules": dark,
        "undeclared_required_modules": undeclared,
        # Reported, never gated: other entry points own the remainder.
        "unreached_modules": len(shipped) - len(reached),
        "reached": not dark and not undeclared,
    }


def self_test() -> dict:
    """Prove that every module an inventory names is reachable, by name."""
    tests = []
    for entry_point in sorted(LIVE_ENTRY_POINTS):
        report = reachability_report(entry_point)
        dark = report["dark_required_modules"]
        undeclared = report["undeclared_required_modules"]
        tests.append({
            "test": f"{entry_point}_reaches_every_module_its_inventory_names",
            "passed": report["reached"],
            "detail": (
                f"{report['reached_modules']}/{report['shipped_modules']} "
                "modules reachable; "
                + (f"DARK: {dark}" if dark else "no dark required module")
                + (f"; UNDECLARED: {undeclared}" if undeclared else "")),
        })
    # The measure has to be able to fail, or it is decoration. A module that
    # is shipped and genuinely unreachable from the entry point proves it.
    control = "loop_engine.memory.procedural.control_assessment_checks"
    reached = reachable_from(LIVE_ENTRY_POINTS["solve_path"])
    tests.append({
        "test": "the_measure_can_distinguish_a_reached_module_from_a_dark_one",
        "passed": (control in shipped_modules() and control not in reached
                   and f"{PACKAGE}.code_nodes.solve_learned_memory" in reached),
        "detail": f"{control} is shipped and not reachable from the solve entry",
    })
    refused = False
    try:
        reachability_report("not_an_entry_point")
    except ValueError:
        refused = True
    tests.append({
        "test": "an_undeclared_entry_point_is_refused_by_name",
        "passed": refused,
        "detail": "the declared set is the vocabulary",
    })
    return {"module": "reachability_report",
            "passed": all(item["passed"] for item in tests), "tests": tests}
