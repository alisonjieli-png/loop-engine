"""Static checks for reviewable public Python interfaces.

This module checks public function and method signatures without importing the
modules it scans. The first rule limits visible parameters. A typed request,
configuration, or result object should carry cohesive values when a boundary
would otherwise expose a long list of commas and optional keywords.

Existing exceptions are read from ``forbidden_paths.json``. Each exception
needs a reason and a replacement plan. New long signatures fail conformance.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile


MAX_PUBLIC_PARAMETERS = 9


def _parameter_count(node: "ast.FunctionDef | ast.AsyncFunctionDef") -> int:
    count = (len(node.args.posonlyargs) + len(node.args.args)
             + len(node.args.kwonlyargs))
    if node.args.args and node.args.args[0].arg in ("self", "cls"):
        count -= 1
    return count


def _public_functions(tree: ast.Module):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                yield node, node.name
        elif isinstance(node, ast.ClassDef):
            for spawned in node.body:
                if (isinstance(spawned, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not spawned.name.startswith("_")):
                    yield spawned, f"{node.name}.{spawned.name}"


def scan_public_signatures(root: "str | None" = None,
                           rules: "dict | None" = None) -> list[dict]:
    """Return every public signature above the cap without an exception."""
    package_root = root or os.path.dirname(os.path.dirname(__file__))
    if rules is None:
        rules_path = os.path.join(package_root, "forbidden_paths.json")
        with open(rules_path, encoding="utf-8") as stream:
            rules = json.load(stream)
    cap = int(rules.get("public_parameter_hard_cap",
                        MAX_PUBLIC_PARAMETERS))
    exceptions = rules.get("long_signature_exceptions", {})
    violations = []
    for dirpath, dirnames, filenames in os.walk(package_root):
        dirnames[:] = [name for name in dirnames if name != "__pycache__"]
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            path = os.path.join(dirpath, filename)
            relative = os.path.relpath(path, package_root).replace(os.sep, "/")
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError:
                continue
            for node, qualified_name in _public_functions(tree):
                count = _parameter_count(node)
                key = f"{relative}:{qualified_name}"
                if count <= cap or key in exceptions:
                    continue
                violations.append({
                    "rule": "public_signature_over_parameter_cap",
                    "file": relative,
                    "line": node.lineno,
                    "detail": (
                        f"{qualified_name} exposes {count} parameters, above "
                        f"the cap of {cap}. Use a typed request, config, or "
                        "result object."),
                })
    return violations


def exception_report(rules: "dict | None" = None) -> list[dict]:
    """List visible legacy exceptions and their required replacement plans."""
    if rules is None:
        root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(root, "forbidden_paths.json"),
                  encoding="utf-8") as stream:
            rules = json.load(stream)
    return [{"signature": key, "plan": value}
            for key, value in sorted(
                rules.get("long_signature_exceptions", {}).items())]


def self_test() -> dict:
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="loop-engine-api-quality-") as root:
        path = os.path.join(root, "fixture.py")
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(
                '"""Three\nline\ncontext."""\n'
                "def too_many(a,b,c,d,e,f,g,h,i,j):\n    return a\n"
                "def typed(request):\n    return request\n")
        planted = scan_public_signatures(root, {
            "public_parameter_hard_cap": 9,
            "long_signature_exceptions": {},
        })
        check("a_planted_long_public_signature_is_detected",
              len(planted) == 1 and planted[0]["line"] == 4,
              str(planted))

    live = scan_public_signatures()
    check("the_live_tree_adds_no_unapproved_long_public_signatures",
          not live, str(live[:3]))
    report = exception_report()
    check("each_legacy_exception_has_a_named_replacement_plan",
          bool(report) and all(len(item["plan"].strip()) >= 20
                               for item in report),
          f"{len(report)} visible exceptions")
    passed = sum(1 for test in results if test["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
