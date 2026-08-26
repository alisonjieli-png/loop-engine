"""Bootstrap verifier: runs without importing Loop Engine.

The bootstrap checks the repository with plain Python only. A broken
LoopNode runtime must never be able to disable all review. This module
is the base case of the Development Assurance Plane.
"""
from __future__ import annotations

import ast
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

#: The only node-named class permitted in the production package.
ALLOWED_NODE_CLASSES = frozenset({"LoopNode"})

#: Forbidden top-level production paths.
FORBIDDEN_PATHS = (
    "src/loop_engine/static_architecture",
    "src/loop_engine/node/node.py",
)

#: Production must never import development packages.
FORBIDDEN_IMPORT_ROOTS = ("loop_engine_devtools", "devtools", "tests",
                          "examples", "benchmarks")


def check_syntax() -> list[dict]:
    """Every Python file must parse."""
    problems = []
    for root in ("src", "devtools"):
        base = os.path.join(_REPO_ROOT, root)
        if not os.path.isdir(base):
            continue
        for directory, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(directory, filename)
                try:
                    ast.parse(open(path, encoding="utf-8").read(), path)
                except (OSError, SyntaxError) as exc:
                    problems.append({"rule": "syntax", "file": path,
                                     "detail": str(exc)})
    return problems


def check_node_classes() -> list[dict]:
    """No node-named class outside the allowlist."""
    problems = []
    base = os.path.join(_REPO_ROOT, "src", "loop_engine")
    for directory, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), path)
            except (OSError, SyntaxError):
                continue
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and (
                        node.name == "Node" or (
                            node.name.endswith("Node")
                            and node.name not in ALLOWED_NODE_CLASSES)):
                    problems.append({"rule": "node_class", "file": path,
                                     "line": node.lineno,
                                     "class": node.name})
    return problems


def check_forbidden_paths() -> list[dict]:
    """Forbidden legacy paths must not exist."""
    problems = []
    for relative in FORBIDDEN_PATHS:
        if os.path.exists(os.path.join(_REPO_ROOT, relative)):
            problems.append({"rule": "forbidden_path", "path": relative})
    return problems


def check_import_direction() -> list[dict]:
    """Production must not import development packages."""
    problems = []
    base = os.path.join(_REPO_ROOT, "src", "loop_engine")
    for directory, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), path)
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                            problems.append({"rule": "import_direction",
                                             "file": path,
                                             "line": node.lineno,
                                             "import": alias.name})
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                        problems.append({"rule": "import_direction",
                                         "file": path,
                                         "line": node.lineno,
                                         "import": node.module})
    return problems


def run_bootstrap() -> dict:
    """Run every bootstrap check without importing Loop Engine."""
    problems: list[dict] = []
    problems.extend(check_syntax())
    problems.extend(check_node_classes())
    problems.extend(check_forbidden_paths())
    problems.extend(check_import_direction())
    return {"record_type": "devtools_bootstrap/v1",
            "problems": problems, "passed": not problems}


def main() -> int:
    report = run_bootstrap()
    for problem in report["problems"]:
        print(f"{problem['rule']}: {problem.get('file', problem.get('path', ''))}"
              f" - {problem.get('detail', problem.get('class', ''))}")
    print("BOOTSTRAP PASS" if report["passed"] else "BOOTSTRAP FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
