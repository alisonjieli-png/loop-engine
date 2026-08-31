"""Digest-bound repository orientation for the Development Assurance Plane.

This module discovers repository authority from a source checkout. It is not
imported by the product package and it is not used on product invocation hot
paths. The resulting records are passive development evidence.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping

try:  # Python 3.10 uses the base dependency declared by Loop Engine.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10 CI
    import tomli as tomllib


ORIENTATION_SCHEMA_VERSION = "repository_orientation_snapshot/v1"

_EXCLUDED_PARTS = frozenset({
    ".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "build", "dist", "node_modules", "artifacts",
    "checkpoints", "example-output",
})

_AUTHORITY_FILE_RULES = (
    ("AGENTS.md", "agent_instructions", 0.80),
    ("CONSTITUTION.md", "architecture_constitution", 1.00),
    ("architecture.yaml", "machine_architecture", 1.00),
    ("terminology.yaml", "terminology_authority", 1.00),
    ("pyproject.toml", "package_metadata", 1.00),
    ("README.md", "component_or_product_guide", 0.60),
    ("ARCHITECTURE-MAP.md", "generated_architecture_projection", 0.45),
)


@dataclass(frozen=True)
class BindingRequirement:
    """One conceptual concern and symbol names used only as discovery seeds."""

    concern: str
    candidate_symbols: tuple[str, ...]
    expected_kinds: tuple[str, ...] = ("class", "function", "assignment")
    required: bool = True


DEFAULT_BINDING_REQUIREMENTS = (
    BindingRequirement("canonical_runtime", ("Loop",), ("class",)),
    BindingRequirement("loop_definition", ("LoopDefinition",), ("class",)),
    BindingRequirement("execution_modes", ("MODES",), ("assignment",)),
    BindingRequirement("role_taxonomy", ("LoopRole",), ("class",)),
    BindingRequirement("role_profiles", ("LoopProfileSpec",), ("class",)),
    BindingRequirement("typed_loop_contract", ("LoopContract",), ("class",)),
    BindingRequirement("runtime_settings", ("RuntimeSettings",), ("class",)),
    BindingRequirement(
        "settings_loading", ("load_runtime_settings",), ("function",)),
    BindingRequirement(
        "capability_admission", ("CodeAssetAdmissionRecord",), ("class",)),
    BindingRequirement(
        "capability_lifecycle", ("CapabilityAuthority",), ("class",)),
    BindingRequirement("catalog", ("UnifiedCatalog",), ("class",)),
    BindingRequirement(
        "reactive_execution", ("AsyncReactiveWorker",), ("class",)),
    BindingRequirement("run_history", ("RunHistory",), ("class",)),
    BindingRequirement("model_gateway", ("ModelGateway",), ("class",)),
    BindingRequirement(
        "effect_authority", ("EffectApprovalService",), ("class",)),
    BindingRequirement(
        "intelligence_layers", ("LAYERS",), ("assignment",)),
    BindingRequirement(
        "prompt_resources", ("PromptFragment",), ("class",), False),
    BindingRequirement(
        "call_boundary_audit", ("scan_repository",), ("function",), False),
)


@dataclass(frozen=True)
class SymbolRecord:
    """One parsed symbol definition in the discovered source tree."""

    name: str
    qualified_name: str
    kind: str
    module: str
    path: str
    line: int
    signature: str


@dataclass(frozen=True)
class AuthoritySource:
    """One file that may contribute authority or a derived projection."""

    path: str
    source_kind: str
    content_digest: str
    authority_confidence: float
    generated_or_projected: bool


@dataclass(frozen=True)
class AuthorityBinding:
    """A conceptual concern bound to one exact live symbol."""

    concern: str
    source_ref: str
    symbol_ref: str
    symbol_kind: str
    enforcement_refs: tuple[str, ...]
    consumer_refs: tuple[str, ...]
    duplicate_refs: tuple[str, ...]
    confidence: float
    action: str


@dataclass(frozen=True)
class OrientationDrift:
    """Freshness result for a previously built orientation snapshot."""

    fresh: bool
    changed_dependencies: tuple[str, ...]
    missing_dependencies: tuple[str, ...]
    current_snapshot_id: str
    recorded_snapshot_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RepositoryOrientationSnapshot:
    """Passive, machine-readable bindings for one exact source state."""

    snapshot_id: str
    schema_version: str
    repository_root_ref: str
    repository_commit: str
    working_tree_digest: str
    generated_at: str
    package_roots: tuple[str, ...]
    public_entry_points: tuple[Mapping[str, str], ...]
    supported_runtime_versions: tuple[str, ...]
    authority_sources: tuple[AuthoritySource, ...]
    authority_bindings: tuple[AuthorityBinding, ...]
    symbol_index: tuple[SymbolRecord, ...]
    import_graph: Mapping[str, tuple[str, ...]]
    call_graph: Mapping[str, tuple[str, ...]]
    configuration_flow_graph: Mapping[str, tuple[str, ...]]
    semantic_authority_graph: Mapping[str, str]
    unresolved_questions: tuple[Mapping[str, str], ...]
    contradictions: tuple[Mapping[str, Any], ...]
    assumptions: tuple[Mapping[str, str], ...]
    source_digests: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "authority_sources": [asdict(item)
                                  for item in self.authority_sources],
            "authority_bindings": [asdict(item)
                                   for item in self.authority_bindings],
            "symbol_index": [asdict(item) for item in self.symbol_index],
        }


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256_bytes(json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8"))


def _run_git(root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ("git", "-C", str(root), *arguments), check=True,
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def discover_repository_root(start: "str | Path | None" = None) -> Path:
    """Find a source repository without trusting the process directory."""
    current = Path(start or Path.cwd()).expanduser().resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        project = candidate / "pyproject.toml"
        if not project.is_file():
            continue
        try:
            metadata = tomllib.loads(project.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name = str(metadata.get("project", {}).get("name", ""))
        if name == "loop-engine" or (candidate / "AGENTS.md").is_file():
            return candidate
    git_root = _run_git(current, "rev-parse", "--show-toplevel")
    if git_root:
        return Path(git_root).resolve()
    raise ValueError("could not discover a Loop Engine repository root")


def repository_files(root: Path) -> tuple[Path, ...]:
    """Return source-controlled and untracked source files, excluding outputs."""
    listed = _run_git(
        root, "ls-files", "--cached", "--others", "--exclude-standard")
    if listed:
        candidates = (root / line for line in listed.splitlines() if line)
    else:
        candidates = root.rglob("*")
    result = []
    for path in candidates:
        try:
            relative = path.resolve().relative_to(root.resolve())
        except (OSError, ValueError):
            continue
        if (_EXCLUDED_PARTS.intersection(relative.parts)
                or not path.is_file() or path.is_symlink()):
            continue
        result.append(path)
    return tuple(sorted(set(result), key=lambda item: item.as_posix()))


def _module_name(root: Path, path: Path, package_roots: Iterable[str]) -> str:
    for raw_root in sorted(package_roots, key=len, reverse=True):
        source_root = (root / raw_root).resolve()
        try:
            relative = path.resolve().relative_to(source_root)
        except ValueError:
            continue
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
    return path.relative_to(root).with_suffix("").as_posix().replace("/", ".")


def _parse_projects(root: Path) -> tuple[
        tuple[str, ...], tuple[Mapping[str, str], ...], tuple[str, ...]]:
    package_roots: set[str] = set()
    entry_points: list[Mapping[str, str]] = []
    runtime_versions: set[str] = set()
    for project in repository_files(root):
        if project.name != "pyproject.toml":
            continue
        try:
            document = tomllib.loads(project.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        relative_parent = project.parent.relative_to(root)
        setuptools = document.get("tool", {}).get("setuptools", {})
        package_dir = setuptools.get("package-dir", {})
        raw_source = package_dir.get("", "src")
        source = (relative_parent / str(raw_source)).as_posix()
        if (root / source).is_dir():
            package_roots.add(source)
        project_body = document.get("project", {})
        requires = str(project_body.get("requires-python", ""))
        if requires:
            runtime_versions.add(requires)
        for name, target in sorted(project_body.get("scripts", {}).items()):
            entry_points.append({
                "distribution": str(project_body.get("name", "")),
                "group": "console_scripts", "name": str(name),
                "target": str(target), "metadata_path":
                    project.relative_to(root).as_posix(),
            })
    return (tuple(sorted(package_roots)),
            tuple(sorted(entry_points, key=lambda item: (
                item["distribution"], item["name"]))),
            tuple(sorted(runtime_versions)))


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, module: str, path: str) -> None:
        self.module = module
        self.path = path
        self.scope: list[str] = []
        self.records: list[SymbolRecord] = []
        self.calls: dict[str, set[str]] = {}
        self.current_callable: list[str] = []

    def _qualified(self, name: str) -> str:
        local = ".".join((*self.scope, name))
        return f"{self.module}:{local}" if self.module else local

    def _signature(self, node: ast.AST) -> str:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            try:
                return ast.unparse(node.args)
            except (AttributeError, ValueError):
                return ""
        if isinstance(node, ast.ClassDef):
            try:
                return ", ".join(ast.unparse(base) for base in node.bases)
            except (AttributeError, ValueError):
                return ""
        return ""

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = self._qualified(node.name)
        self.records.append(SymbolRecord(
            node.name, qualified, "class", self.module, self.path,
            node.lineno, self._signature(node)))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def _visit_function(self, node: "ast.FunctionDef | ast.AsyncFunctionDef") \
            -> None:
        qualified = self._qualified(node.name)
        self.records.append(SymbolRecord(
            node.name, qualified, "function", self.module, self.path,
            node.lineno, self._signature(node)))
        self.scope.append(node.name)
        self.current_callable.append(qualified)
        self.calls.setdefault(qualified, set())
        self.generic_visit(node)
        self.current_callable.pop()
        self.scope.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and not self.scope:
                self.records.append(SymbolRecord(
                    target.id, self._qualified(target.id), "assignment",
                    self.module, self.path, node.lineno, ""))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and not self.scope:
            self.records.append(SymbolRecord(
                node.target.id, self._qualified(node.target.id), "assignment",
                self.module, self.path, node.lineno, ""))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self.current_callable:
            if isinstance(node.func, ast.Name):
                called = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called = node.func.attr
            else:
                called = ""
            if called:
                self.calls[self.current_callable[-1]].add(called)
        self.generic_visit(node)


def _index_python(
        root: Path, files: Iterable[Path], package_roots: tuple[str, ...]) \
        -> tuple[tuple[SymbolRecord, ...], dict[str, tuple[str, ...]],
                 dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    symbols: list[SymbolRecord] = []
    imports: dict[str, set[str]] = {}
    calls: dict[str, set[str]] = {}
    configuration: dict[str, set[str]] = {}
    for path in files:
        if path.suffix != ".py":
            continue
        relative = path.relative_to(root).as_posix()
        module = _module_name(root, path, package_roots)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        visitor = _SymbolVisitor(module, relative)
        visitor.visit(tree)
        symbols.extend(visitor.records)
        calls.update({key: tuple(sorted(value))
                      for key, value in visitor.calls.items()})
        module_imports = imports.setdefault(module, set())
        config_refs = configuration.setdefault(module, set())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module_imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_imports.add(node.module)
            elif isinstance(node, ast.Call):
                function = node.func
                if (isinstance(function, ast.Attribute)
                        and function.attr in {"getenv", "get"}
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    config_refs.add(node.args[0].value)
            elif (isinstance(node, ast.Subscript)
                  and isinstance(node.value, ast.Attribute)
                  and node.value.attr == "environ"):
                value = node.slice
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    config_refs.add(value.value)
    return (
        tuple(sorted(symbols, key=lambda item: (
            item.path, item.line, item.qualified_name))),
        {key: tuple(sorted(value)) for key, value in sorted(imports.items())},
        {key: tuple(sorted(value)) for key, value in sorted(calls.items())},
        {key: tuple(sorted(value))
         for key, value in sorted(configuration.items()) if value},
    )


def _authority_sources(root: Path, files: Iterable[Path]) \
        -> tuple[AuthoritySource, ...]:
    sources = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        for filename, source_kind, confidence in _AUTHORITY_FILE_RULES:
            if path.name != filename:
                continue
            projected = (source_kind.startswith("generated_")
                         or "/generated/" in f"/{relative}/")
            sources.append(AuthoritySource(
                relative, source_kind, _sha256_file(path), confidence,
                projected))
            break
    return tuple(sorted(sources, key=lambda item: item.path))


def _references_by_name(
        root: Path, files: Iterable[Path], names: Iterable[str]) \
        -> dict[str, list[str]]:
    wanted = set(names)
    found: dict[str, list[str]] = {name: [] for name in wanted}
    for path in files:
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        relative = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            name = ""
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            if name in wanted:
                found[name].append(f"{relative}:{getattr(node, 'lineno', 0)}")
    return found


def _bind_authorities(
        root: Path, files: tuple[Path, ...], symbols: tuple[SymbolRecord, ...],
        requirements: Iterable[BindingRequirement]) \
        -> tuple[tuple[AuthorityBinding, ...], tuple[Mapping[str, str], ...],
                 tuple[Mapping[str, Any], ...]]:
    requirements = tuple(requirements)
    references = _references_by_name(
        root, files,
        (name for requirement in requirements
         for name in requirement.candidate_symbols))
    by_name: dict[str, list[SymbolRecord]] = {}
    for symbol in symbols:
        by_name.setdefault(symbol.name, []).append(symbol)
    bindings = []
    unresolved = []
    contradictions = []
    for requirement in requirements:
        candidates = [
            symbol for name in requirement.candidate_symbols
            for symbol in by_name.get(name, ())
            if symbol.kind in requirement.expected_kinds
        ]
        candidates.sort(key=lambda item: (
            not item.path.startswith("src/loop_engine/"),
            item.path.startswith(("examples/", "tests/")),
            item.path, item.line))
        if not candidates:
            if requirement.required:
                unresolved.append({
                    "concern": requirement.concern,
                    "question": "No exact live symbol matched the discovery seeds.",
                })
            continue
        selected = candidates[0]
        refs = tuple(sorted(set(references.get(selected.name, ()))))
        self_ref = f"{selected.path}:{selected.line}"
        refs = tuple(ref for ref in refs if ref != self_ref)
        enforcement = tuple(ref for ref in refs if any(token in ref for token in (
            "_checks.py", "_test.py", "conformance", "test_")))[:30]
        consumers = tuple(ref for ref in refs if ref not in enforcement)[:30]
        duplicates = tuple(
            f"{item.path}:{item.line}" for item in candidates[1:])
        confidence = 1.0 if enforcement else 0.90
        action = "REUSE_EXISTING" if not duplicates else "REUSE_AND_REVIEW_DUPLICATES"
        bindings.append(AuthorityBinding(
            requirement.concern, selected.path, selected.qualified_name,
            selected.kind, enforcement, consumers, duplicates, confidence,
            action))
        if duplicates:
            contradictions.append({
                "concern": requirement.concern,
                "claim": "More than one definition matched an authority seed.",
                "selected": self_ref,
                "other_definitions": list(duplicates),
                "resolution": "Production source and enforcing references lead; "
                              "duplicates remain visible for review.",
            })
    return tuple(bindings), tuple(unresolved), tuple(contradictions)


def _working_tree_digest(root: Path, files: tuple[Path, ...]) -> str:
    return _canonical_digest([
        (path.relative_to(root).as_posix(), _sha256_file(path))
        for path in files
    ])


def build_orientation_snapshot(
        start: "str | Path | None" = None, *,
        requirements: Iterable[BindingRequirement] =
        DEFAULT_BINDING_REQUIREMENTS) -> RepositoryOrientationSnapshot:
    """Discover and bind the current repository without model assistance."""
    root = discover_repository_root(start)
    files = repository_files(root)
    package_roots, entry_points, runtimes = _parse_projects(root)
    symbols, imports, calls, configuration = _index_python(
        root, files, package_roots)
    authority_sources = _authority_sources(root, files)
    bindings, unresolved, contradictions = _bind_authorities(
        root, files, symbols, requirements)
    dependency_paths = {
        source.path for source in authority_sources
        if source.authority_confidence >= 0.80
        and not source.generated_or_projected
    } | {
        binding.source_ref for binding in bindings
    } | {
        ref.rsplit(":", 1)[0]
        for binding in bindings for ref in binding.enforcement_refs
    }
    source_digests = {
        relative: _sha256_file(root / relative)
        for relative in sorted(dependency_paths)
        if (root / relative).is_file()
    }
    commit = _run_git(root, "rev-parse", "HEAD") or "unversioned"
    identity_body = {
        "schema_version": ORIENTATION_SCHEMA_VERSION,
        "repository_commit": commit,
        "package_roots": package_roots,
        "entry_points": entry_points,
        "bindings": [asdict(item) for item in bindings],
        "source_digests": source_digests,
        "unresolved": unresolved,
        "contradictions": contradictions,
    }
    snapshot_id = f"orientation.sha256_{_canonical_digest(identity_body)}"
    return RepositoryOrientationSnapshot(
        snapshot_id=snapshot_id,
        schema_version=ORIENTATION_SCHEMA_VERSION,
        repository_root_ref=str(root),
        repository_commit=commit,
        working_tree_digest=_working_tree_digest(root, files),
        generated_at=datetime.now(timezone.utc).isoformat(),
        package_roots=package_roots,
        public_entry_points=entry_points,
        supported_runtime_versions=runtimes,
        authority_sources=authority_sources,
        authority_bindings=bindings,
        symbol_index=symbols,
        import_graph=imports,
        call_graph=calls,
        configuration_flow_graph=configuration,
        semantic_authority_graph={
            item.concern: item.symbol_ref for item in bindings},
        unresolved_questions=unresolved,
        contradictions=contradictions,
        assumptions=({
            "classification": "DISCOVERY_SEED",
            "statement": "Concrete symbol names are search seeds, not authority.",
            "consequence": "Every binding is re-resolved from parsed source.",
        }, {
            "classification": "REPOSITORY_INVARIANT",
            "statement": "Development orientation is outside product hot paths.",
            "consequence": "The product package never imports devtools.",
        }),
        source_digests=source_digests,
    )


def run_orientation_as_loop(
        start: "str | Path | None" = None, *,
        requirements: Iterable[BindingRequirement] =
        DEFAULT_BINDING_REQUIREMENTS) \
        -> tuple[RepositoryOrientationSnapshot, Mapping[str, Any]]:
    """Run repository orientation through one canonical Practitioner Loop."""
    from loop_engine import Loop, LoopConfig, StepOutcome
    from loop_engine.loop.loop_role import (
        LoopRelationship, LoopRole, LoopRoleIdentity)

    root = discover_repository_root(start)
    holder: dict[str, Any] = {}
    loop = Loop(
        "orient the current repository authority",
        LoopConfig(
            framework="custom", custom_steps=("discover", "verify"),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",), power="standard",
            exit_condition="steps_complete"),
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.verifier"),
        relationship=LoopRelationship.starting())

    def handler(_active: Loop, step: str, _state: dict) -> StepOutcome:
        if step == "discover":
            holder["snapshot"] = build_orientation_snapshot(
                root, requirements=requirements)
            output = {
                "snapshot_id": holder["snapshot"].snapshot_id,
                "bindings": len(holder["snapshot"].authority_bindings),
            }
        elif step == "verify":
            snapshot = holder["snapshot"]
            if snapshot.unresolved_questions:
                return StepOutcome(
                    {"unresolved": len(snapshot.unresolved_questions)},
                    "deterministic", 0.0, failed=True)
            output = {
                "source_digests": len(snapshot.source_digests),
                "contradictions": len(snapshot.contradictions),
            }
        else:  # pragma: no cover - LoopConfig owns the closed step set
            raise ValueError(f"unknown orientation step {step!r}")
        return StepOutcome(output, "deterministic", 1.0)

    result = loop.run(handler=handler, max_steps=3)
    if not result.accepted or "snapshot" not in holder:
        raise ValueError("repository orientation did not reach acceptance")
    snapshot = holder["snapshot"]
    return snapshot, {
        "record_type": "repository_orientation_run/v1",
        "loop_id": result.loop_id, "runtime_type": "Loop",
        "profile_id": "practitioner.verifier",
        "selected_mode": "deterministic",
        "snapshot_id": snapshot.snapshot_id,
    }


def validate_orientation_snapshot(
        snapshot: RepositoryOrientationSnapshot,
        start: "str | Path | None" = None) -> OrientationDrift:
    """Rebuild bindings and report only authority dependency drift."""
    current = build_orientation_snapshot(start)
    changed = tuple(sorted(
        path for path, digest in snapshot.source_digests.items()
        if current.source_digests.get(path) not in (None, digest)))
    missing = tuple(sorted(
        path for path in snapshot.source_digests
        if path not in current.source_digests))
    fresh = not changed and not missing \
        and current.snapshot_id == snapshot.snapshot_id
    return OrientationDrift(
        fresh, changed, missing, current.snapshot_id, snapshot.snapshot_id)


def snapshot_from_dict(value: Mapping[str, Any]) \
        -> RepositoryOrientationSnapshot:
    """Load a snapshot written by :func:`write_orientation_snapshot`."""
    return RepositoryOrientationSnapshot(
        snapshot_id=str(value["snapshot_id"]),
        schema_version=str(value["schema_version"]),
        repository_root_ref=str(value["repository_root_ref"]),
        repository_commit=str(value["repository_commit"]),
        working_tree_digest=str(value["working_tree_digest"]),
        generated_at=str(value["generated_at"]),
        package_roots=tuple(value.get("package_roots", ())),
        public_entry_points=tuple(value.get("public_entry_points", ())),
        supported_runtime_versions=tuple(
            value.get("supported_runtime_versions", ())),
        authority_sources=tuple(
            AuthoritySource(**item)
            for item in value.get("authority_sources", ())),
        authority_bindings=tuple(
            AuthorityBinding(
                **{**item,
                   "enforcement_refs": tuple(item.get("enforcement_refs", ())),
                   "consumer_refs": tuple(item.get("consumer_refs", ())),
                   "duplicate_refs": tuple(item.get("duplicate_refs", ()))})
            for item in value.get("authority_bindings", ())),
        symbol_index=tuple(SymbolRecord(**item)
                           for item in value.get("symbol_index", ())),
        import_graph={key: tuple(item) for key, item
                      in value.get("import_graph", {}).items()},
        call_graph={key: tuple(item) for key, item
                    in value.get("call_graph", {}).items()},
        configuration_flow_graph={key: tuple(item) for key, item
                                  in value.get(
                                      "configuration_flow_graph", {}).items()},
        semantic_authority_graph=dict(
            value.get("semantic_authority_graph", {})),
        unresolved_questions=tuple(value.get("unresolved_questions", ())),
        contradictions=tuple(value.get("contradictions", ())),
        assumptions=tuple(value.get("assumptions", ())),
        source_digests=dict(value.get("source_digests", {})),
    )


def write_orientation_snapshot(
        snapshot: RepositoryOrientationSnapshot, path: "str | Path") -> Path:
    """Write one exact snapshot to an explicitly selected development path."""
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(
        snapshot.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return target


def self_test() -> dict[str, Any]:
    """Canary-prove discovery, stable identity, and targeted invalidation."""
    tests: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "src" / "loop_engine").mkdir(parents=True)
        (root / "tests").mkdir()
        (root / "pyproject.toml").write_text(
            "[project]\nname='loop-engine'\nversion='0.0.0'\n"
            "requires-python='>=3.10'\n"
            "[project.scripts]\nloop-engine='loop_engine:main'\n"
            "[tool.setuptools]\npackage-dir={''='src'}\n",
            encoding="utf-8")
        (root / "architecture.yaml").write_text(
            "schema: architecture/v1\n", encoding="utf-8")
        (root / "terminology.yaml").write_text(
            "schema: terminology/v1\n", encoding="utf-8")
        runtime = root / "src" / "loop_engine" / "runtime.py"
        runtime.write_text(
            "class Loop:\n    pass\nMODES=('deterministic','hybrid',"
            "'non_deterministic')\n", encoding="utf-8")
        (root / "tests" / "test_runtime_checks.py").write_text(
            "from loop_engine.runtime import Loop\n"
            "def test_loop():\n    assert Loop\n", encoding="utf-8")
        first = build_orientation_snapshot(root, requirements=(
            BindingRequirement("canonical_runtime", ("Loop",), ("class",)),
            BindingRequirement("execution_modes", ("MODES",),
                               ("assignment",)),
        ))
        second = build_orientation_snapshot(root, requirements=(
            BindingRequirement("canonical_runtime", ("Loop",), ("class",)),
            BindingRequirement("execution_modes", ("MODES",),
                               ("assignment",)),
        ))
        check("repository_root_is_discovered_from_nested_path",
              discover_repository_root(runtime) == root)
        check("package_and_entry_point_are_discovered_from_metadata",
              first.package_roots == ("src",)
              and first.public_entry_points[0]["name"] == "loop-engine")
        check("concepts_bind_to_exact_parsed_symbols",
              first.semantic_authority_graph["canonical_runtime"]
              == "loop_engine.runtime:Loop")
        check("snapshot_identity_ignores_generation_time",
              first.snapshot_id == second.snapshot_id)
        (root / "README.md").write_text("irrelevant guide edit\n",
                                        encoding="utf-8")
        third = build_orientation_snapshot(root, requirements=(
            BindingRequirement("canonical_runtime", ("Loop",), ("class",)),
            BindingRequirement("execution_modes", ("MODES",),
                               ("assignment",)),
        ))
        check("unrelated_guide_change_does_not_change_binding_identity",
              third.snapshot_id == first.snapshot_id
              and third.working_tree_digest != first.working_tree_digest)
        runtime.write_text(
            "class Loop:\n    runtime_version=2\n"
            "MODES=('deterministic','hybrid','non_deterministic')\n",
            encoding="utf-8")
        fourth = build_orientation_snapshot(root, requirements=(
            BindingRequirement("canonical_runtime", ("Loop",), ("class",)),
            BindingRequirement("execution_modes", ("MODES",),
                               ("assignment",)),
        ))
        check("authority_source_change_invalidates_snapshot",
              fourth.snapshot_id != first.snapshot_id)
        loop_snapshot, run_record = run_orientation_as_loop(
            root, requirements=(
                BindingRequirement(
                    "canonical_runtime", ("Loop",), ("class",)),
                BindingRequirement(
                    "execution_modes", ("MODES",), ("assignment",)),
            ))
        check("orientation_operation_runs_through_canonical_loop",
              run_record["runtime_type"] == "Loop"
              and run_record["selected_mode"] == "deterministic"
              and run_record["snapshot_id"] == loop_snapshot.snapshot_id)
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "repository_orientation_self_test/v1",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }
