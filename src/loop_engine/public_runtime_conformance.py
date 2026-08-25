"""Static checks for the one-runtime package surface.

This root-plumbing module inspects only ``loop_engine.__init__``. Internal
modules may retain deprecated algorithm aliases, but the package root may
expose only the canonical recursive ``Loop`` runtime.
"""
from __future__ import annotations

import ast
import os


def public_parallel_runtime_violations(
        root: str, forbidden_names) -> list[dict]:
    """Return forbidden root-visible names with their source locations."""
    path = os.path.join(root, "__init__.py")
    if not os.path.isfile(path):
        return []
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except SyntaxError:
        return []
    locations: dict[str, int] = {}

    def remember(name: str, line: int) -> None:
        if name and not name.startswith("_"):
            locations.setdefault(name, line)

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                remember(alias.asname or alias.name.split(".")[0], node.lineno)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef,
                               ast.AsyncFunctionDef)):
            remember(node.name, node.lineno)
        elif isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets
                       if isinstance(target, ast.Name)]
            if "__all__" in targets and isinstance(
                    node.value, (ast.List, ast.Tuple, ast.Set)):
                for item in node.value.elts:
                    if isinstance(item, ast.Constant) \
                            and isinstance(item.value, str):
                        remember(item.value, getattr(item, "lineno", node.lineno))
            if "_PUBLIC" in targets and isinstance(node.value, ast.Dict):
                for key in node.value.keys:
                    if isinstance(key, ast.Constant) \
                            and isinstance(key.value, str):
                        remember(key.value, getattr(key, "lineno", node.lineno))
    forbidden = set(forbidden_names)
    return [{
        "rule": "public_parallel_runtime_surface",
        "file": "__init__.py",
        "line": locations[name],
        "detail": (f"root public name {name!r} competes with the canonical "
                   "recursive_loop.Loop runtime"),
    } for name in sorted(forbidden & set(locations))]
