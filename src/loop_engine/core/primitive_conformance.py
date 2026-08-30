"""AST conformance for strict and governed-semantic primitive profiles.

The repository still contains a measured legacy baseline outside the adaptive
prompt path. New strict modules must have zero native semantic string or JSON
operations. The audit reports every remaining occurrence so later migration
can remove it symbol by symbol without a broad folder exception.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


STRICT_MODULES = (
    "core/adaptive_practitioner_prompting.py",
    "loop/atomic_primitives.py",
)
INTRINSIC_MODULE = "loop/intrinsic_kernel.py"
GOVERNED_SEMANTIC_NATIVE = {
    ("core/adaptive_practitioner_prompting.py", "_render_packet_governed")}


@dataclass(frozen=True)
class NativeSemanticOperation:
    """One exact native operation found outside or inside the intrinsic seam."""

    path: str
    line: int
    symbol: str
    operation: str
    intrinsic_allowed: bool

    def to_dict(self) -> dict:
        return {
            "path": self.path, "line": self.line, "symbol": self.symbol,
            "operation": self.operation,
            "intrinsic_allowed": self.intrinsic_allowed,
        }


def _operation(node: ast.AST) -> str:
    if isinstance(node, ast.JoinedStr):
        return "f_string"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        if (isinstance(node.left, (ast.Constant, ast.JoinedStr))
                or isinstance(node.right, (ast.Constant, ast.JoinedStr))):
            return "string_add"
    if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)
            and isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str)):
        return "percent_format"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "join":
            return "string_join"
        if node.func.attr == "format":
            return "string_format"
        if (isinstance(node.func.value, ast.Name)
                and node.func.value.id == "json"
                and node.func.attr in ("dumps", "loads")):
            return "json_" + node.func.attr
    return ""


class _Visitor(ast.NodeVisitor):
    def __init__(self, path: str, intrinsic: bool) -> None:
        self.path = path
        self.intrinsic = intrinsic
        self.symbols = ["<module>"]
        self.findings: list[NativeSemanticOperation] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.symbols.append(node.name)
        self.generic_visit(node)
        self.symbols.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def generic_visit(self, node: ast.AST) -> None:
        operation = _operation(node)
        if operation:
            self.findings.append(NativeSemanticOperation(
                self.path, int(getattr(node, "lineno", 0)),
                self.symbols[-1], operation, self.intrinsic))
        super().generic_visit(node)


def scan_native_semantic_operations(package_root: Path) -> list[dict]:
    """Return exact file, symbol, and line findings for the installed source."""
    findings = []
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        visitor = _Visitor(relative, relative == INTRINSIC_MODULE)
        visitor.visit(tree)
        findings.extend(item.to_dict() for item in visitor.findings)
    return findings


def _mutation_detected(source: str) -> bool:
    tree = ast.parse(source)
    visitor = _Visitor("mutation.py", False)
    visitor.visit(tree)
    return bool(visitor.findings)


def self_test() -> dict:
    """Enforce the strict path now and preserve the full migration baseline."""
    root = Path(__file__).resolve().parents[1]
    findings = scan_native_semantic_operations(root)
    governed = [item for item in findings if (
        item["path"], item["symbol"]) in GOVERNED_SEMANTIC_NATIVE]
    strict = [item for item in findings if item["path"] in STRICT_MODULES
              and (item["path"], item["symbol"])
              not in GOVERNED_SEMANTIC_NATIVE]
    direct_intrinsic = []
    for path in root.rglob("*.py"):
        relative = path.relative_to(root).as_posix()
        if relative in (INTRINSIC_MODULE, "loop/atomic_primitives.py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "execute_intrinsic"):
                direct_intrinsic.append({"path": relative, "line": node.lineno})
    mutations = all(_mutation_detected(source) for source in (
        "def bad(x):\n return f'value={x}'\n",
        "def bad(x):\n return ','.join(x)\n",
        "import json\ndef bad(x):\n return json.dumps(x)\n",
    ))
    tests = [{
        "test": "strict_atomic_symbols_have_no_native_bypass",
        "passed": not strict,
        "detail": str(strict[:10]),
    }, {
        "test": "governed_semantic_native_allowance_is_one_exact_function",
        "passed": bool(governed) and all(
            (item["path"], item["symbol"])
            in GOVERNED_SEMANTIC_NATIVE for item in governed),
        "detail": str(governed[:10]),
    }, {
        "test": "intrinsic_kernel_has_one_exact_call_boundary",
        "passed": not direct_intrinsic,
        "detail": str(direct_intrinsic[:10]),
    }, {
        "test": "direct_semantic_operation_mutations_are_detected",
        "passed": mutations,
        "detail": "f-string, join, and JSON mutations detected",
    }, {
        "test": "repository_native_operation_baseline_is_measured",
        "passed": bool(findings),
        "detail": f"{len(findings)} exact findings remain for migration",
    }]
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "strict_primitive_conformance/v1",
        "migration_complete": not findings,
        "remaining_findings": len(findings),
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }
