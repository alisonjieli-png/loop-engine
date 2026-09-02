"""AST conformance for small, typed call boundaries.

The checker enforces a default of at most three direct parameters on
hand-written public and cross-module callables. ``self`` and ``cls`` do not
count. Generated schema constructors are absent from the source AST and are
therefore not treated as hand-written call boundaries.

The checker also rejects common ways to hide an oversized boundary. It reports
variadic escape hatches, untyped option bags, mutable defaults, boolean-flag
explosions, passive argument containers named as Loops, and invalid exception
records. It never treats a request object as operational work.
"""

from __future__ import annotations

import ast
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from pathlib import Path
import re
from typing import Any

import yaml


MAX_DIRECT_PARAMETERS = 3
BOOLEAN_FLAG_THRESHOLD = 2
SCHEMA = "parameter_boundary_scan/v1"

EXEMPTABLE_RULES = frozenset({
    "parameter_count",
    "varargs_escape",
    "kwargs_escape",
    "untyped_options_bag",
    "mutable_default",
    "boolean_flag_explosion",
    "loop_argument_container",
})

_OPTION_BAG_NAMES = frozenset({
    "options", "opts", "params", "parameters", "kwargs",
    "option_map", "config_dict", "settings_dict",
})
_MUTABLE_FACTORIES = frozenset({"dict", "list", "set", "defaultdict"})
_GLOB_CHARACTERS = frozenset("*?[")
_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


@dataclass(frozen=True)
class BoundaryPolicy:
    """Versioned limits used by one repository scan."""

    max_direct_parameters: int = MAX_DIRECT_PARAMETERS
    boolean_flag_threshold: int = BOOLEAN_FLAG_THRESHOLD


@dataclass(frozen=True)
class ScanRequest:
    """Passive input contract for one repository scan."""

    root: Path
    source_paths: tuple[str, ...] = ("src/loop_engine", "devtools/src")
    exception_registry: Path | None = None
    focus_files: tuple[str, ...] = ()
    current_version: str = "0.0.0"
    as_of: date = field(default_factory=date.today)
    revision: str = "UNKNOWN"
    require_registry: bool = False


@dataclass(frozen=True)
class BoundaryViolation:
    """One deterministic finding from the call-boundary scan."""

    rule: str
    file: str
    symbol: str
    line: int
    detail: str
    boundary: str = ""
    approved: bool = False
    exception_id: str | None = None


@dataclass(frozen=True)
class ExceptionRecord:
    """One exact, reviewable exception to a single detector."""

    exception_id: str
    file: str
    symbol: str
    rule: str
    external_contract: str
    reason: str
    owner: str
    test: str
    introduced_version: str
    removal_version: str | None = None
    permanent_justification: str | None = None
    expires_on: str | None = None


@dataclass(frozen=True)
class ParameterInfo:
    """AST-level parameter facts without executing source code."""

    name: str
    annotation: str | None
    default: ast.expr | None


@dataclass(frozen=True)
class SourceUnit:
    """One parsed first-party Python file."""

    path: Path
    relative: str
    module: str
    tree: ast.Module


@dataclass(frozen=True)
class CallableContext:
    """Location and visibility facts for one callable."""

    unit: SourceUnit
    qualname: str
    class_names: tuple[str, ...]
    exported_names: frozenset[str]
    cross_module_symbols: frozenset[str]


@dataclass(frozen=True)
class RawScan:
    """Unapproved AST findings before registry application."""

    violations: tuple[BoundaryViolation, ...]
    files_scanned: int
    callables_scanned: int


@dataclass(frozen=True)
class RegistryLoad:
    """Validated registry contents and registry-level findings."""

    policy: BoundaryPolicy
    exceptions: tuple[ExceptionRecord, ...]
    violations: tuple[BoundaryViolation, ...]


def _normal_path(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _module_name(relative: str) -> str:
    parts = Path(relative).with_suffix("").parts
    if parts[:2] == ("devtools", "src"):
        parts = parts[2:]
    elif parts[:1] == ("src",):
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _source_files(request: ScanRequest) -> list[Path]:
    found: set[Path] = set()
    for source in request.source_paths:
        target = request.root / source
        if target.is_file() and target.suffix == ".py":
            found.add(target)
            continue
        if not target.is_dir():
            continue
        for path in target.rglob("*.py"):
            if "__pycache__" not in path.parts:
                found.add(path)
    return sorted(found)


def _parse_sources(request: ScanRequest) -> tuple[list[SourceUnit], list[BoundaryViolation]]:
    units: list[SourceUnit] = []
    violations: list[BoundaryViolation] = []
    for path in _source_files(request):
        relative = _normal_path(str(path.relative_to(request.root)))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            violations.append(BoundaryViolation(
                rule="parse_error",
                file=relative,
                symbol="<module>",
                line=getattr(exc, "lineno", 0) or 0,
                detail=str(exc),
                boundary="source_file",
            ))
            continue
        units.append(SourceUnit(path, relative, _module_name(relative), tree))
    return units, violations


def _literal_exports(tree: ast.Module) -> frozenset[str]:
    exports: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "__all__"
                   for target in targets):
            continue
        value = node.value
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            for element in value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    exports.add(element.value)
    return frozenset(exports)


def _resolve_import(module: str, node: ast.ImportFrom) -> str:
    imported_module = node.module or ""
    if node.level == 0:
        return imported_module
    package = module.rsplit(".", 1)[0] if "." in module else module
    parts = package.split(".") if package else []
    remove = max(0, node.level - 1)
    if remove:
        parts = parts[:-remove]
    if imported_module:
        parts.extend(imported_module.split("."))
    return ".".join(parts)


def _cross_module_symbols(units: list[SourceUnit]) -> frozenset[str]:
    symbols: set[str] = set()
    local_modules = {unit.module for unit in units}
    for unit in units:
        for node in ast.walk(unit.tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            module = _resolve_import(unit.module, node)
            if module not in local_modules:
                continue
            for alias in node.names:
                if alias.name != "*":
                    symbols.add(f"{module}.{alias.name}")
    return frozenset(symbols)


def _annotation_text(annotation: ast.expr | None) -> str | None:
    if annotation is None:
        return None
    try:
        return ast.unparse(annotation)
    except (AttributeError, ValueError):
        return None


def _parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ParameterInfo]:
    positional = [*node.args.posonlyargs, *node.args.args]
    missing = len(positional) - len(node.args.defaults)
    defaults: list[ast.expr | None] = [None] * missing + list(node.args.defaults)
    # strict: each pair is equal length by construction above, so a silent
    # truncation here would quietly under-report a boundary rather than fail.
    paired = list(zip(positional, defaults, strict=True))
    paired += list(zip(node.args.kwonlyargs, node.args.kw_defaults,
                       strict=True))
    return [
        ParameterInfo(arg.arg, _annotation_text(arg.annotation), default)
        for arg, default in paired
        if arg.arg not in {"self", "cls"}
    ]


def _is_mutable_default(default: ast.expr | None) -> bool:
    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
        return True
    if not isinstance(default, ast.Call):
        return False
    if isinstance(default.func, ast.Name):
        return default.func.id in _MUTABLE_FACTORIES
    if isinstance(default.func, ast.Attribute):
        return default.func.attr in _MUTABLE_FACTORIES
    return False


def _is_bool_parameter(parameter: ParameterInfo) -> bool:
    annotation = (parameter.annotation or "").replace("typing.", "").strip()
    return annotation == "bool" or (
        isinstance(parameter.default, ast.Constant)
        and isinstance(parameter.default.value, bool)
    )


def _is_untyped_bag(parameter: ParameterInfo) -> bool:
    if parameter.name.lower() not in _OPTION_BAG_NAMES:
        return False
    if parameter.annotation is None:
        return True
    annotation = parameter.annotation.replace(" ", "").lower()
    annotation = annotation.replace("typing.", "")
    if annotation in {"any", "object", "dict", "mapping", "mutablemapping"}:
        return True
    is_mapping = any(token in annotation for token in ("dict[", "mapping["))
    return is_mapping and any(token in annotation for token in ("any", "object"))


def _boundary_kind(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    context: CallableContext,
) -> str | None:
    if context.class_names:
        if any(name.startswith("_") for name in context.class_names):
            return None
        if node.name == "__init__":
            return "public_constructor"
        if node.name.startswith("__") and node.name.endswith("__"):
            return "protocol_method"
        if not node.name.startswith("_"):
            return "public_method"
        return None
    full_symbol = f"{context.unit.module}.{node.name}"
    if node.name in context.exported_names:
        return "explicit_export"
    if full_symbol in context.cross_module_symbols:
        return "cross_module_function"
    if not node.name.startswith("_"):
        return "public_function"
    return None


def _callable_violations(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    context: CallableContext,
    policy: BoundaryPolicy,
) -> list[BoundaryViolation]:
    boundary = _boundary_kind(node, context)
    if boundary is None:
        return []
    parameters = _parameters(node)
    common = {
        "file": context.unit.relative,
        "symbol": context.qualname,
        "line": node.lineno,
        "boundary": boundary,
    }
    violations: list[BoundaryViolation] = []
    if len(parameters) > policy.max_direct_parameters:
        violations.append(BoundaryViolation(
            rule="parameter_count",
            detail=(f"{len(parameters)} direct parameters exceed the limit of "
                    f"{policy.max_direct_parameters}"),
            **common,
        ))
    if node.args.vararg is not None:
        violations.append(BoundaryViolation(
            rule="varargs_escape",
            detail=f"*{node.args.vararg.arg} hides the direct parameter contract",
            **common,
        ))
    if node.args.kwarg is not None:
        violations.append(BoundaryViolation(
            rule="kwargs_escape",
            detail=f"**{node.args.kwarg.arg} hides the direct parameter contract",
            **common,
        ))
    bags = [parameter.name for parameter in parameters if _is_untyped_bag(parameter)]
    if bags:
        violations.append(BoundaryViolation(
            rule="untyped_options_bag",
            detail=f"untyped or Any-valued option bag: {', '.join(bags)}",
            **common,
        ))
    mutable = [
        parameter.name for parameter in parameters
        if _is_mutable_default(parameter.default)
    ]
    if mutable:
        violations.append(BoundaryViolation(
            rule="mutable_default",
            detail=f"mutable default parameter: {', '.join(mutable)}",
            **common,
        ))
    boolean_flags = [parameter.name for parameter in parameters
                     if _is_bool_parameter(parameter)]
    if len(boolean_flags) >= policy.boolean_flag_threshold:
        violations.append(BoundaryViolation(
            rule="boolean_flag_explosion",
            detail=(f"{len(boolean_flags)} boolean flags form an implicit mode matrix: "
                    f"{', '.join(boolean_flags)}"),
            **common,
        ))
    return violations


def _class_field_count(node: ast.ClassDef) -> int:
    fields = sum(isinstance(item, (ast.AnnAssign, ast.Assign)) for item in node.body)
    for item in node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if item.name != "__init__":
            continue
        for statement in ast.walk(item):
            if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                continue
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if any(isinstance(target, ast.Attribute)
                   and isinstance(target.value, ast.Name)
                   and target.value.id == "self" for target in targets):
                fields += 1
    return fields


def _is_loop_argument_container(node: ast.ClassDef) -> bool:
    base_names = {
        ast.unparse(base).rsplit(".", 1)[-1]
        for base in node.bases
    }
    loop_named = node.name != "Loop" and (
        node.name.endswith("Loop") or "Loop" in base_names
    )
    if not loop_named or _class_field_count(node) == 0:
        return False
    methods = {
        item.name for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    operational = methods & {
        "run", "run_next_iteration", "start", "execute", "spawn",
        "pause", "resume", "verify", "stop",
    }
    passive_methods = methods <= {"__init__", "__post_init__", "validate"}
    decorators = {ast.unparse(decorator).rsplit(".", 1)[-1]
                  for decorator in node.decorator_list}
    return not operational and (passive_methods or "dataclass" in decorators)


def _scan_class(
    unit: SourceUnit,
    node: ast.ClassDef,
    shared: tuple[frozenset[str], frozenset[str], BoundaryPolicy],
) -> tuple[list[BoundaryViolation], int]:
    exports, cross_module, policy = shared
    violations: list[BoundaryViolation] = []
    count = 0
    if _is_loop_argument_container(node):
        violations.append(BoundaryViolation(
            rule="loop_argument_container",
            file=unit.relative,
            symbol=node.name,
            line=node.lineno,
            detail="passive argument or schema fields are named as an operational Loop",
            boundary="class",
        ))
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            context = CallableContext(
                unit=unit,
                qualname=f"{node.name}.{item.name}",
                class_names=(node.name,),
                exported_names=exports,
                cross_module_symbols=cross_module,
            )
            if _boundary_kind(item, context) is not None:
                count += 1
            violations.extend(_callable_violations(item, context, policy))
        elif isinstance(item, ast.ClassDef):
            nested, nested_count = _scan_nested_class(unit, item, shared, (node.name,))
            violations.extend(nested)
            count += nested_count
    return violations, count


def _scan_nested_class(
    unit: SourceUnit,
    node: ast.ClassDef,
    state: tuple[tuple[frozenset[str], frozenset[str], BoundaryPolicy], tuple[str, ...]],
) -> tuple[list[BoundaryViolation], int]:
    shared, parents = state
    exports, cross_module, policy = shared
    class_names = (*parents, node.name)
    violations: list[BoundaryViolation] = []
    count = 0
    if _is_loop_argument_container(node):
        violations.append(BoundaryViolation(
            rule="loop_argument_container",
            file=unit.relative,
            symbol=".".join(class_names),
            line=node.lineno,
            detail="passive argument or schema fields are named as an operational Loop",
            boundary="class",
        ))
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            context = CallableContext(
                unit=unit,
                qualname=".".join((*class_names, item.name)),
                class_names=class_names,
                exported_names=exports,
                cross_module_symbols=cross_module,
            )
            if _boundary_kind(item, context) is not None:
                count += 1
            violations.extend(_callable_violations(item, context, policy))
        elif isinstance(item, ast.ClassDef):
            nested, nested_count = _scan_nested_class(
                unit, item, (shared, class_names))
            violations.extend(nested)
            count += nested_count
    return violations, count


def _scan_units(units: list[SourceUnit], policy: BoundaryPolicy) -> RawScan:
    cross_module = _cross_module_symbols(units)
    violations: list[BoundaryViolation] = []
    callable_count = 0
    for unit in units:
        exports = _literal_exports(unit.tree)
        shared = (exports, cross_module, policy)
        for node in unit.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                context = CallableContext(
                    unit=unit,
                    qualname=node.name,
                    class_names=(),
                    exported_names=exports,
                    cross_module_symbols=cross_module,
                )
                if _boundary_kind(node, context) is not None:
                    callable_count += 1
                violations.extend(_callable_violations(node, context, policy))
            elif isinstance(node, ast.ClassDef):
                class_violations, class_count = _scan_class(unit, node, shared)
                violations.extend(class_violations)
                callable_count += class_count
    return RawScan(tuple(violations), len(units), callable_count)


def _registry_problem(rule: str, detail: str, line: int = 0) -> BoundaryViolation:
    return BoundaryViolation(
        rule=rule,
        file="docs/architecture/call-boundary-exceptions.yaml",
        symbol="<exception_registry>",
        line=line,
        detail=detail,
        boundary="exception_registry",
    )


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    if not _SEMVER.fullmatch(value):
        return None
    core = re.split(r"[-+]", value, maxsplit=1)[0]
    major, minor, patch = core.split(".")
    return int(major), int(minor), int(patch)


def _is_broad_exception(raw: dict[str, Any]) -> bool:
    file = str(raw.get("file", ""))
    symbol = str(raw.get("symbol", ""))
    rule = str(raw.get("rule", ""))
    if any(character in file + symbol + rule for character in _GLOB_CHARACTERS):
        return True
    normalized = _normal_path(file)
    return (
        Path(file).is_absolute()
        or ".." in Path(normalized).parts
        or not normalized.endswith(".py")
        or normalized in {"src/loop_engine", "devtools/src"}
        or not _SYMBOL.fullmatch(symbol)
        or rule not in EXEMPTABLE_RULES
    )


def _exception_from_raw(raw: dict[str, Any]) -> ExceptionRecord:
    return ExceptionRecord(
        exception_id=str(raw["exception_id"]),
        file=_normal_path(str(raw["file"])),
        symbol=str(raw["symbol"]),
        rule=str(raw["rule"]),
        external_contract=str(raw["external_contract"]),
        reason=str(raw["reason"]),
        owner=str(raw["owner"]),
        test=str(raw["test"]),
        introduced_version=str(raw["introduced_version"]),
        removal_version=(str(raw["removal_version"])
                         if raw.get("removal_version") is not None else None),
        permanent_justification=(str(raw["permanent_justification"])
                                 if raw.get("permanent_justification") is not None
                                 else None),
        expires_on=(str(raw["expires_on"])
                    if raw.get("expires_on") is not None else None),
    )


def _exception_errors(raw: dict[str, Any]) -> list[str]:
    required = {
        "exception_id", "file", "symbol", "rule", "external_contract",
        "reason", "owner", "test", "introduced_version",
    }
    errors = [f"missing required field {name}"
              for name in sorted(required - raw.keys())]
    for name in sorted(required & raw.keys()):
        if not isinstance(raw[name], str) or not raw[name].strip():
            errors.append(f"{name} must be a non-empty string")
    introduced = raw.get("introduced_version")
    if isinstance(introduced, str) and _version_tuple(introduced) is None:
        errors.append("introduced_version must be semantic version text")
    removal = raw.get("removal_version")
    permanent = raw.get("permanent_justification")
    if bool(removal) == bool(permanent):
        errors.append(
            "declare exactly one of removal_version or permanent_justification")
    if removal and (not isinstance(removal, str) or _version_tuple(removal) is None):
        errors.append("removal_version must be semantic version text")
    if permanent is not None and (
        not isinstance(permanent, str) or not permanent.strip()
    ):
        errors.append("permanent_justification must be non-empty")
    return errors


def _exception_expired(record: ExceptionRecord, request: ScanRequest) -> str | None:
    current = _version_tuple(request.current_version)
    removal = _version_tuple(record.removal_version) if record.removal_version else None
    if current is not None and removal is not None and current >= removal:
        return (f"{record.exception_id} expired at package version "
                f"{record.removal_version}")
    if record.expires_on:
        try:
            expiry = date.fromisoformat(record.expires_on)
        except ValueError:
            return f"{record.exception_id} has invalid expires_on date"
        if request.as_of >= expiry:
            return f"{record.exception_id} expired on {record.expires_on}"
    return None


def _load_registry(request: ScanRequest) -> RegistryLoad:
    path = request.exception_registry
    if path is None:
        if request.require_registry:
            return RegistryLoad(
                BoundaryPolicy(), (),
                (_registry_problem("invalid_exception", "exception registry is required"),),
            )
        return RegistryLoad(BoundaryPolicy(), (), ())
    if not path.is_absolute():
        path = request.root / path
    if not path.is_file():
        return RegistryLoad(
            BoundaryPolicy(), (),
            (_registry_problem("invalid_exception", f"registry not found: {path}"),),
        )
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return RegistryLoad(
            BoundaryPolicy(), (),
            (_registry_problem("invalid_exception", f"registry unreadable: {exc}"),),
        )
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return RegistryLoad(
            BoundaryPolicy(), (),
            (_registry_problem("invalid_exception", "schema_version must equal 1"),),
        )
    raw_policy = document.get("policy", {})
    if not isinstance(raw_policy, dict):
        raw_policy = {}
    policy = BoundaryPolicy(
        max_direct_parameters=int(
            raw_policy.get("max_direct_parameters", MAX_DIRECT_PARAMETERS)),
        boolean_flag_threshold=int(
            raw_policy.get("boolean_flag_threshold", BOOLEAN_FLAG_THRESHOLD)),
    )
    raw_exceptions = document.get("exceptions", [])
    if not isinstance(raw_exceptions, list):
        return RegistryLoad(
            policy, (),
            (_registry_problem("invalid_exception", "exceptions must be a list"),),
        )
    records: list[ExceptionRecord] = []
    problems: list[BoundaryViolation] = []
    targets: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_exceptions):
        if not isinstance(raw, dict):
            problems.append(_registry_problem(
                "invalid_exception", f"exception {index} must be a mapping"))
            continue
        errors = _exception_errors(raw)
        if errors:
            problems.extend(_registry_problem(
                "invalid_exception", f"exception {index}: {error}")
                for error in errors)
            continue
        if _is_broad_exception(raw):
            problems.append(_registry_problem(
                "broad_exception",
                f"{raw['exception_id']} must name one exact file, symbol, and rule"))
            continue
        record = _exception_from_raw(raw)
        expired = _exception_expired(record, request)
        if expired:
            problems.append(_registry_problem("expired_exception", expired))
            continue
        target = (record.file, record.symbol, record.rule)
        if target in targets:
            problems.append(_registry_problem(
                "invalid_exception", f"duplicate exception target: {target}"))
            continue
        targets.add(target)
        records.append(record)
    return RegistryLoad(policy, tuple(records), tuple(problems))


def _apply_exceptions(
    violations: list[BoundaryViolation],
    registry: RegistryLoad,
) -> tuple[list[BoundaryViolation], list[BoundaryViolation]]:
    by_target = {
        (record.file, record.symbol, record.rule): record
        for record in registry.exceptions
    }
    matched: set[str] = set()
    resolved: list[BoundaryViolation] = []
    for violation in violations:
        record = by_target.get((violation.file, violation.symbol, violation.rule))
        if record is None:
            resolved.append(violation)
            continue
        matched.add(record.exception_id)
        resolved.append(replace(
            violation, approved=True, exception_id=record.exception_id))
    stale = [
        _registry_problem(
            "stale_exception",
            f"{record.exception_id} no longer matches a live violation",
        )
        for record in registry.exceptions
        if record.exception_id not in matched
    ]
    return resolved, stale


def _counts(violations: list[BoundaryViolation]) -> dict[str, int]:
    return dict(sorted(Counter(item.rule for item in violations).items()))


def scan_repository(request: ScanRequest) -> dict[str, Any]:
    """Scan first-party source without importing or executing it."""
    registry = _load_registry(request)
    units, parse_problems = _parse_sources(request)
    raw = _scan_units(units, registry.policy)
    candidates = [*parse_problems, *raw.violations]
    resolved, stale = _apply_exceptions(candidates, registry)
    violations = [*resolved, *registry.violations, *stale]
    violations.sort(key=lambda item: (
        item.file, item.line, item.symbol, item.rule, item.detail))
    approved = [item for item in violations if item.approved]
    unapproved = [item for item in violations if not item.approved]
    focused_names = {_normal_path(name) for name in request.focus_files}
    focused = [item for item in unapproved if item.file in focused_names]
    return {
        "record_type": SCHEMA,
        "revision": request.revision,
        "root": str(request.root),
        "source_paths": list(request.source_paths),
        "policy": asdict(registry.policy),
        "files_scanned": raw.files_scanned,
        "callables_scanned": raw.callables_scanned,
        "exceptions_loaded": len(registry.exceptions),
        "exceptions_applied": len({item.exception_id for item in approved}),
        "violations_total": len(violations),
        "approved_violations": len(approved),
        "unapproved_violations": len(unapproved),
        "unapproved_by_rule": _counts(unapproved),
        "focus_files": sorted(focused_names),
        "focused_unapproved_violations": len(focused),
        "focused_by_rule": _counts(focused),
        "passed": not unapproved,
        "violations": [asdict(item) for item in violations],
    }


def self_test() -> dict[str, Any]:
    """Canary-prove every detector with intentionally bad source fixtures."""
    from .parameter_boundary_checks import self_test as run_checks
    return run_checks()


def main() -> int:
    """Run the focused checker or its mutation self-test."""
    from .parameter_boundary_checks import main as run_cli
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
