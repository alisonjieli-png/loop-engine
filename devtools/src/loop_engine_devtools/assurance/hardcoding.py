"""Context-aware hardcoding audit for the Development Assurance Plane.

The audit classifies values by syntax, owner, consumers, and runtime role. It
does not assume that every literal is a defect. Broad rules start in report
mode, and only stable new high-severity findings are suitable for CI gating.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Mapping

import yaml

from .orientation import discover_repository_root, repository_files

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 CI
    import tomli as tomllib


AUDIT_SCHEMA_VERSION = "hardcoding_audit/v1"
ALLOWLIST_SCHEMA_VERSION = "hardcoding_allowlist/v1"

CLASSIFICATIONS = (
    "INTENTIONAL_LOCAL_LITERAL",
    "CONSTITUTIONAL_INVARIANT",
    "PROTOCOL_OR_SCHEMA_IDENTIFIER",
    "COMPATIBILITY_ALIAS",
    "CLOSED_CONTROLLED_VOCABULARY",
    "OPEN_TAXONOMY_OR_REGISTRY_VALUE",
    "INVOCATION_PARAMETER",
    "OPTIONAL_PARAMETER_WITH_DEFAULT",
    "LOOP_PROFILE_SETTING",
    "DOMAIN_OR_TENANT_POLICY",
    "DEPLOYMENT_CONFIGURATION",
    "SECRET_OR_CREDENTIAL_REFERENCE",
    "DERIVED_VALUE",
    "STRATEGY_OR_PROVIDER_BINDING",
    "RESOURCE_OR_TEMPLATE",
    "USER_FACING_COPY",
    "DIAGNOSTIC_OR_OBSERVABILITY_TEXT",
    "TEST_FIXTURE_OR_EXAMPLE",
    "INTELLIGENCE_RESOLVED_PROPOSAL",
    "DUPLICATE_OR_DRIFTED_AUTHORITY",
    "DEAD_OR_UNREACHABLE_LITERAL",
    "UNRESOLVED_REQUIRES_EXPERIMENT",
)

ABSTRACTION_FOR_CLASSIFICATION = {
    "INTENTIONAL_LOCAL_LITERAL": "keep_local",
    "CONSTITUTIONAL_INVARIANT": "existing_constitutional_authority",
    "PROTOCOL_OR_SCHEMA_IDENTIFIER": "versioned_schema_or_contract",
    "COMPATIBILITY_ALIAS": "translation_boundary",
    "CLOSED_CONTROLLED_VOCABULARY": "enum_literal_or_terminology_authority",
    "OPEN_TAXONOMY_OR_REGISTRY_VALUE": "existing_registry_catalog_or_ontology",
    "INVOCATION_PARAMETER": "typed_required_parameter",
    "OPTIONAL_PARAMETER_WITH_DEFAULT": "typed_optional_parameter_and_default",
    "LOOP_PROFILE_SETTING": "versioned_loop_profile_setting",
    "DOMAIN_OR_TENANT_POLICY": "versioned_policy",
    "DEPLOYMENT_CONFIGURATION": "typed_runtime_settings",
    "SECRET_OR_CREDENTIAL_REFERENCE": "approved_secret_reference",
    "DERIVED_VALUE": "deterministic_derivation",
    "STRATEGY_OR_PROVIDER_BINDING": "admitted_strategy_or_provider_binding",
    "RESOURCE_OR_TEMPLATE": "versioned_resource_bundle",
    "USER_FACING_COPY": "owned_copy_or_localization_resource",
    "DIAGNOSTIC_OR_OBSERVABILITY_TEXT": "stable_reason_code_plus_local_text",
    "TEST_FIXTURE_OR_EXAMPLE": "isolated_fixture",
    "INTELLIGENCE_RESOLVED_PROPOSAL": "bounded_intelligence_loop_proposal",
    "DUPLICATE_OR_DRIFTED_AUTHORITY": "identify_and_reuse_canonical_owner",
    "DEAD_OR_UNREACHABLE_LITERAL": "remove_after_reference_proof",
    "UNRESOLVED_REQUIRES_EXPERIMENT": "bounded_behavior_experiment",
}

_SUPPORTED_SUFFIXES = frozenset({
    ".py", ".pyi", ".yaml", ".yml", ".json", ".jsonl", ".toml",
    ".sql", ".sh", ".bash", ".md", ".txt", ".html", ".css", ".js",
    ".mjs", ".ts",
})
_TEXT_FILENAMES = frozenset({"Dockerfile", "Makefile"})
_MAX_TEXT_BYTES = 5_000_000
_AUDIT_CONTROL_PATHS = frozenset({
    "devtools/hardcoding-ci-baseline.json",
    "devtools/hardcoding-allowlist.yaml",
})
_STATE_WORDS = frozenset({
    "status", "state", "mode", "role", "lifecycle", "action", "event",
    "reason", "verdict", "decision", "kind", "type", "tier", "scope",
    "relationship", "phase", "stage", "outcome", "terminal", "dispatch",
})
_SETTING_WORDS = frozenset({
    "timeout", "retry", "attempt", "limit", "maximum", "minimum", "max",
    "min", "threshold", "margin", "score", "confidence", "token", "top_k",
    "candidate", "depth", "batch", "worker", "concurrency", "lease", "ttl",
    "poll", "backoff", "temperature", "seed", "budget", "interval",
})
_PROVIDER_WORDS = frozenset({
    "provider", "model", "endpoint", "route", "backend", "executor",
    "strategy", "wire", "adapter", "image",
})
_OPEN_WORDS = frozenset({
    "plugin", "extension", "provider", "capability", "operation_family",
    "intelligence", "entry_point", "registry", "catalog",
})
_SECRET_WORDS = frozenset({
    "secret", "credential", "password", "passwd", "api_key",
    "authorization", "cookie", "private_key",
})
_PATH_WORDS = frozenset({
    "path", "dir", "directory", "root", "file", "filename", "suffix",
    "prefix", "workspace", "database", "db", "store",
})
_PROMPT_WORDS = frozenset({
    "prompt", "instruction", "system", "rubric", "persona", "directive",
    "few_shot", "example", "template",
})


@dataclass(frozen=True)
class AuditRequest:
    """Scope and policy for one deterministic source audit."""

    repository_root: Path
    include_low_risk: bool = False
    allowlist_path: "Path | None" = None
    source_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class HardcodingFinding:
    """One secret-safe, source-located abstraction finding."""

    finding_id: str
    schema_version: str
    repository_snapshot_id: str
    path: str
    symbol_ref: "str | None"
    start_line: "int | None"
    end_line: "int | None"
    syntactic_context: str
    semantic_context: "str | None"
    literal_kind: str
    literal_preview: "str | None"
    literal_digest: str
    sensitive_value_redacted: bool
    occurrence_group_id: "str | None"
    reference_count: int
    affected_callers: tuple[str, ...]
    affected_contracts: tuple[str, ...]
    classification: str
    secondary_tags: tuple[str, ...]
    proposed_abstraction_kind: str
    proposed_authority_ref: "str | None"
    proposed_parameter_scope: "str | None"
    owner: str
    change_frequency_estimate: str
    blast_radius: str
    security_risk: str
    compatibility_risk: str
    behavior_risk: str
    testability: str
    severity: str
    confidence: float
    rationale: str
    evidence_refs: tuple[str, ...]
    suggested_next_action: str
    suppressed: bool = False
    suppression_ref: "str | None" = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AllowlistEntry:
    """One exact, owned exception. Wildcards are intentionally unsupported."""

    finding_id: str
    owner: str
    rationale: str
    classification: str
    created_on: str
    expires_on: "str | None" = None


@dataclass(frozen=True)
class _LiteralContext:
    symbol: str
    syntactic: str
    semantic: str
    role_name: str
    is_default: bool
    default_parameter: str
    default_kind: str
    is_dict_key: bool
    is_compare: bool
    is_exception_text: bool
    is_user_copy: bool
    call_name: str


def _digest(value: Any) -> str:
    serialized = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _normal_words(value: str) -> set[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value)
    tokens = set(re.findall(r"[a-z0-9_]+", separated.casefold()))
    return tokens | {
        part for token in tokens for part in token.split("_") if part}


def _safe_preview(value: Any, sensitive: bool) -> "str | None":
    if sensitive:
        return "<redacted>"
    if value is None:
        return "null"
    rendered = repr(value)
    if len(rendered) > 160:
        return rendered[:157] + "..."
    return rendered


def _literal_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, bytes):
        return "bytes"
    if isinstance(value, (list, tuple, dict, set)) and not value:
        return "empty_collection"
    return type(value).__name__


def _contains_secret_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.search(
        r"(?i)(?:bearer\s+[a-z0-9._-]{12,}|sk-[a-z0-9_-]{12,}|"
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----)", value))


def _is_secret_reference(role: str, value: Any) -> bool:
    """Recognize a credential boundary without treating its name as a secret."""
    if _contains_secret_value(value):
        return True
    normalized_role = role.casefold()
    role_tail = re.split(r"[.\[\]: ]+", normalized_role)[-1]
    role_has_reference = bool(re.fullmatch(
        r"(?:api_key|access_token|auth_token|private_key|secret|credential|"
        r"credential_env|password|passwd|token|[a-z0-9_]+_api_key)",
        role_tail))
    environment_reference = isinstance(value, str) and bool(re.fullmatch(
        r"[A-Z][A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET|"
        r"PASSWORD|CREDENTIAL)", value))
    return role_has_reference or environment_reference


def _is_url(value: Any) -> bool:
    return isinstance(value, str) and bool(re.match(r"https?://", value))


def _is_path(value: Any, role_words: set[str]) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return bool(role_words & _PATH_WORDS) and (
        "/" in value or "\\" in value or value.startswith((".", "~")))


def _looks_like_prompt(value: Any, role_words: set[str]) -> bool:
    if not isinstance(value, str):
        return False
    lower = value.casefold()
    instruction_signals = sum(fragment in lower for fragment in (
        "you are ", "return only", "do not ", "must ", "respond with",
        "your task", "output schema", "instructions:"))
    return (bool(role_words & _PROMPT_WORDS) and len(value) >= 80) \
        or (len(value) >= 160 and instruction_signals >= 2)


def _is_sql(value: Any) -> bool:
    return isinstance(value, str) and bool(re.match(
        r"\s*(select|insert|update|delete|create\s+table|alter\s+table)\b",
        value, re.I))


def _is_test_or_example(path: str) -> bool:
    parts = Path(path).parts
    name = Path(path).name
    return (any(part in {"tests", "examples", "benchmarks", "fixtures"}
                for part in parts)
            or name.startswith(("test_", "_self_test", "_checks"))
            or name.endswith(("_test.py", "_checks.py")))


def _is_generated_or_reference(path: str) -> bool:
    parts = Path(path).parts
    return (path.endswith(("package-lock.json", "architecture_conformance.json"))
            or parts[:2] == ("docs", "evidence")
            or (parts and parts[0] in {"showcase", "example-output"}))


def _role_tail(role: str) -> str:
    parts = [part for part in re.split(r"[.\[\]: ]+", role.casefold())
             if part and not part.isdigit()]
    return parts[-1] if parts else ""


def _owner(path: str, symbol: str) -> str:
    module = path.replace("/", ".")
    if module.endswith(".py"):
        module = module[:-3]
    if module.startswith("src."):
        module = module[4:]
    return f"{module}:{symbol}" if symbol else module


def _proposed_authority(classification: str, owner: str) -> str:
    if classification == "DEPLOYMENT_CONFIGURATION":
        return "loop_engine.core.runtime_settings:RuntimeSettings"
    if classification == "SECRET_OR_CREDENTIAL_REFERENCE":
        return "approved secret resolver through RuntimeSettings"
    if classification == "CLOSED_CONTROLLED_VOCABULARY":
        return "current Enum, schema, or terminology authority"
    if classification == "OPEN_TAXONOMY_OR_REGISTRY_VALUE":
        return "current admitted registry, catalog, ontology, or entry point"
    if classification == "RESOURCE_OR_TEMPLATE":
        return "current Context Intelligence or prompt-resource authority"
    return owner


def _classification(
        path: str, value: Any, context: _LiteralContext) \
        -> tuple[str, tuple[str, ...], str, float, str]:
    role_words = _normal_words(
        " ".join((_role_tail(context.role_name), context.call_name)))
    symbol_words = _normal_words(context.symbol.rsplit(".", 1)[-1])
    tags: list[str] = []
    if (_is_test_or_example(path) or _is_generated_or_reference(path)
            or context.symbol == "self_test"
            or context.symbol.endswith(".self_test")):
        return ("TEST_FIXTURE_OR_EXAMPLE", (), "low", 0.98,
                "The value is isolated in test, example, benchmark, or check code.")
    if _contains_secret_value(value):
        return ("SECRET_OR_CREDENTIAL_REFERENCE", ("security_sensitive",),
                "critical", 0.98,
                "The literal has the shape of a credential value and must be redacted.")
    if context.is_dict_key:
        return ("PROTOCOL_OR_SCHEMA_IDENTIFIER", ("raw_dictionary_key",),
                "low", 0.85,
                "A dictionary key may participate in a serialized or internal schema.")
    if context.is_user_copy:
        return ("USER_FACING_COPY", (), "low", 0.90,
                "This text is presented to an operator or user.")
    if _is_secret_reference(
            " ".join((context.role_name, context.call_name)), value):
        return ("SECRET_OR_CREDENTIAL_REFERENCE", ("credential_reference",),
                "high", 0.94,
                "A credential reference must resolve through approved secret infrastructure.")
    if (path.endswith("/strings/prompt_fragments.py")
            and ("prompt" in symbol_words or "prompt" in role_words)):
        return ("RESOURCE_OR_TEMPLATE", ("governed_prompt_resource",),
                "low", 0.98,
                "The text is already owned by a versioned typed prompt resource.")
    if context.is_default:
        tags.append("default")
        if context.default_kind == "dataclass":
            tags.append("dataclass_default")
        if value is None:
            tags.append("ambiguous_null_or_omitted")
        if value is False:
            tags.append("explicit_false")
        if value == 0 and not isinstance(value, bool):
            tags.append("explicit_zero")
        owner_name = context.symbol.split(".", 1)[0]
        if (context.default_kind == "dataclass"
                and not owner_name.endswith((
                    "Override", "Request", "Options", "Input"))):
            return ("LOOP_PROFILE_SETTING", tuple(tags), "medium", 0.94,
                    "A typed record default is owned by its profile or contract.")
        return ("OPTIONAL_PARAMETER_WITH_DEFAULT", tuple(tags), "medium", 0.98,
                "A call boundary default is part of the parameter contract.")
    if (context.call_name.endswith(("getenv", "environ.get"))
            or _role_tail(context.role_name) in {
                "environment", "environ", "env", "environment_variable"}):
        return ("DEPLOYMENT_CONFIGURATION", ("environment_read",), "high",
                0.94, "A deployment value is read at a source boundary.")
    if _looks_like_prompt(value, role_words | (symbol_words & _PROMPT_WORDS)):
        severity = "high" if isinstance(value, str) and len(value) >= 400 \
            else "medium"
        return ("RESOURCE_OR_TEMPLATE", ("prompt_like_text",), severity,
                0.91,
                "Long executable instructions need versioned identity and typed slots.")
    if _is_sql(value):
        return ("RESOURCE_OR_TEMPLATE", ("sql",), "medium", 0.95,
                "A query has an independent contract and change lifecycle.")
    if _is_url(value):
        return ("STRATEGY_OR_PROVIDER_BINDING", ("url",), "high", 0.90,
                "An endpoint or external identity should be bound at its owner.")
    if _is_path(value, role_words):
        return ("DEPLOYMENT_CONFIGURATION", ("path",), "medium", 0.88,
                "A filesystem location may vary by deployment or workspace.")
    if context.is_exception_text:
        return ("DIAGNOSTIC_OR_OBSERVABILITY_TEXT", (), "low", 0.96,
                "Human-readable diagnostics should not become machine state.")
    if (path.endswith("/assurance/hardcoding.py")
            and context.symbol.rsplit(".", 1)[-1] in {
                "_classification", "_risk_fields", "_action", "_summary",
                "_literal_kind", "_structured_findings", "_text_findings",
                "_PythonLiteralVisitor._emit"}):
        return ("CONSTITUTIONAL_INVARIANT", ("audit_vocabulary",), "low",
                0.98, "The detector compares its own closed typed vocabulary.")
    if context.is_compare and role_words & _STATE_WORDS:
        return ("CLOSED_CONTROLLED_VOCABULARY", ("raw_state_comparison",),
                "high", 0.94,
                "A raw token directly controls state, routing, or lifecycle behavior.")
    if role_words & _SETTING_WORDS:
        return ("LOOP_PROFILE_SETTING", ("behavior_limit_or_threshold",),
                "medium", 0.83,
                "A behavior limit or threshold needs one semantic owner.")
    if role_words & _PROVIDER_WORDS:
        return ("STRATEGY_OR_PROVIDER_BINDING", (), "medium", 0.82,
                "A replaceable implementation identity appears in behavior code.")
    if role_words & _OPEN_WORDS and isinstance(value, str):
        return ("OPEN_TAXONOMY_OR_REGISTRY_VALUE", (), "medium", 0.72,
                "The named concept appears extensible and needs admission ownership.")
    if (context.role_name.isupper() and isinstance(value, str)
            and context.role_name in {"MODES", "LOOP_ROLES", "LAYERS"}):
        return ("CONSTITUTIONAL_INVARIANT", (), "low", 0.95,
                "The value belongs to a declared architecture vocabulary authority.")
    if context.is_compare and isinstance(value, (str, bool)):
        return ("CLOSED_CONTROLLED_VOCABULARY", ("behavior_comparison",),
                "medium", 0.72,
                "A literal comparison participates in behavior selection.")
    return ("INTENTIONAL_LOCAL_LITERAL", (), "low", 0.60,
            "No evidence currently justifies a broader abstraction.")


def _risk_fields(
        classification: str, severity: str, references: int) \
        -> tuple[str, str, str, str, str]:
    security = "high" if classification in {
        "SECRET_OR_CREDENTIAL_REFERENCE", "DOMAIN_OR_TENANT_POLICY"} \
        else "medium" if classification in {
            "DEPLOYMENT_CONFIGURATION", "STRATEGY_OR_PROVIDER_BINDING"} \
        else "low"
    compatibility = "high" if classification in {
        "PROTOCOL_OR_SCHEMA_IDENTIFIER", "COMPATIBILITY_ALIAS",
        "CLOSED_CONTROLLED_VOCABULARY"} else "medium" if references > 3 else "low"
    behavior = "high" if severity in {"critical", "high"} \
        else "medium" if severity == "medium" else "low"
    blast = "cross_module" if references > 3 else "module" if references else "local"
    frequency = "deployment" if classification == "DEPLOYMENT_CONFIGURATION" \
        else "per_invocation" if classification in {
            "INVOCATION_PARAMETER", "OPTIONAL_PARAMETER_WITH_DEFAULT"} \
        else "versioned_or_rare"
    return security, compatibility, behavior, blast, frequency


def _action(classification: str) -> str:
    if classification == "INTENTIONAL_LOCAL_LITERAL":
        return "Keep local unless new consumers prove shared semantic ownership."
    if classification == "TEST_FIXTURE_OR_EXAMPLE":
        return "Keep isolated and prevent it from becoming a production default."
    if classification == "DIAGNOSTIC_OR_OBSERVABILITY_TEXT":
        return "Pair with a stable code only if another component consumes it."
    if classification == "PROTOCOL_OR_SCHEMA_IDENTIFIER":
        return "Confirm the schema owner before centralizing or changing it."
    return "Review the owner and migrate through the proposed typed abstraction."


class _PythonLiteralVisitor(ast.NodeVisitor):
    def __init__(
            self, root: Path, path: Path, tree: ast.Module,
            repository_snapshot_id: str, include_low_risk: bool,
            callers_by_name: Mapping[str, tuple[str, ...]]) -> None:
        self.root = root
        self.path = path
        self.relative = path.relative_to(root).as_posix()
        self.tree = tree
        self.snapshot_id = repository_snapshot_id
        self.include_low_risk = include_low_risk
        self.callers_by_name = callers_by_name
        self.parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                self.parents[child] = parent
        self.docstrings = self._docstring_nodes()
        self.default_roots, self.dataclass_default_roots = \
            self._default_roots()
        self.scope: list[str] = []
        self.findings: list[HardcodingFinding] = []
        self.literal_count = 0
        self.identity_occurrences: dict[tuple[str, ...], int] = defaultdict(int)

    def _docstring_nodes(self) -> set[ast.AST]:
        result = set()
        for owner in ast.walk(self.tree):
            if not isinstance(owner, (
                    ast.Module, ast.ClassDef, ast.FunctionDef,
                    ast.AsyncFunctionDef)) or not owner.body:
                continue
            first = owner.body[0]
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                result.add(first.value)
        return result

    def _default_roots(self) -> tuple[dict[ast.AST, str], set[ast.AST]]:
        result: dict[ast.AST, str] = {}
        dataclass_roots: set[ast.AST] = set()
        for node in ast.walk(self.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            positional = [*node.args.posonlyargs, *node.args.args]
            if node.args.defaults:
                for argument, default in zip(
                        positional[-len(node.args.defaults):],
                        node.args.defaults):
                    result[default] = argument.arg
            for argument, default in zip(
                    node.args.kwonlyargs, node.args.kw_defaults):
                if default is not None:
                    result[default] = argument.arg
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            decorator_names = set()
            for item in node.decorator_list:
                target = item.func if isinstance(item, ast.Call) else item
                decorator_names.add(ast.unparse(target).rsplit(".", 1)[-1])
            base_names = {
                ast.unparse(item).rsplit(".", 1)[-1] for item in node.bases}
            if not (decorator_names & {"dataclass", "define", "frozen"}
                    or base_names & {"BaseModel", "Model", "TypedModel"}):
                continue
            for statement in node.body:
                if (isinstance(statement, ast.AnnAssign)
                        and statement.value is not None
                        and isinstance(statement.target, ast.Name)):
                    result[statement.value] = statement.target.id
                    dataclass_roots.add(statement.value)
                elif (isinstance(statement, ast.Assign)
                      and statement.value is not None
                      and statement.targets
                      and isinstance(statement.targets[0], ast.Name)):
                    result[statement.value] = statement.targets[0].id
                    dataclass_roots.add(statement.value)
        return result, dataclass_roots

    def _ancestor(self, node: ast.AST, kinds: Any) -> "ast.AST | None":
        current = self.parents.get(node)
        while current is not None:
            if isinstance(current, kinds):
                return current
            current = self.parents.get(current)
        return None

    def _default_parameter(self, node: ast.AST) -> tuple[str, str]:
        current: "ast.AST | None" = node
        while current is not None:
            if current in self.default_roots:
                return (self.default_roots[current],
                        "dataclass" if current in self.dataclass_default_roots
                        else "invocation")
            current = self.parents.get(current)
        return "", ""

    def _assignment_name(self, node: ast.AST) -> str:
        current: "ast.AST | None" = node
        while current is not None:
            parent = self.parents.get(current)
            if isinstance(parent, ast.Assign) and current is parent.value:
                target = parent.targets[0] if parent.targets else None
                if isinstance(target, ast.Name):
                    return target.id
                if isinstance(target, ast.Attribute):
                    return target.attr
            if isinstance(parent, ast.AnnAssign) and current is parent.value:
                target = parent.target
                if isinstance(target, ast.Name):
                    return target.id
                if isinstance(target, ast.Attribute):
                    return target.attr
            if isinstance(parent, ast.keyword) and current is parent.value:
                return parent.arg or "keyword"
            current = parent
        return ""

    def _call_name(self, node: ast.AST) -> str:
        call = self._ancestor(node, ast.Call)
        if not isinstance(call, ast.Call):
            return ""
        parts = []
        current: ast.AST = call.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _is_dict_key(self, node: ast.AST) -> bool:
        parent = self.parents.get(node)
        return isinstance(parent, ast.Dict) and node in parent.keys

    def _context(self, node: ast.AST) -> _LiteralContext:
        default_parameter, default_kind = self._default_parameter(node)
        assignment = self._assignment_name(node)
        call_name = self._call_name(node)
        compare = bool(self._ancestor(node, (ast.Compare, ast.Match)))
        exception_text = bool(self._ancestor(node, (ast.Raise, ast.Assert)))
        call_words = _normal_words(call_name)
        user_copy = bool(call_words & {"print", "help", "description"})
        parent = self.parents.get(node)
        syntactic = type(parent).__name__ if parent is not None else "Module"
        role_name = default_parameter or assignment
        if not role_name and isinstance(parent, ast.keyword):
            role_name = parent.arg or ""
        comparison = self._ancestor(node, ast.Compare)
        if not role_name and isinstance(comparison, ast.Compare):
            if isinstance(comparison.left, ast.Name):
                role_name = comparison.left.id
            elif isinstance(comparison.left, ast.Attribute):
                role_name = comparison.left.attr
        match = self._ancestor(node, ast.Match)
        if not role_name and isinstance(match, ast.Match):
            if isinstance(match.subject, ast.Name):
                role_name = match.subject.id
            elif isinstance(match.subject, ast.Attribute):
                role_name = match.subject.attr
        semantic = ":".join(part for part in (
            "default" if default_parameter else "",
            "dict_key" if self._is_dict_key(node) else "",
            "comparison" if compare else "", call_name) if part)
        return _LiteralContext(
            symbol=".".join(self.scope), syntactic=syntactic,
            semantic=semantic or "local_expression", role_name=role_name,
            is_default=bool(default_parameter),
            default_parameter=default_parameter,
            default_kind=default_kind,
            is_dict_key=self._is_dict_key(node), is_compare=compare,
            is_exception_text=exception_text, is_user_copy=user_copy,
            call_name=call_name)

    def _emit(self, node: ast.AST, value: Any) -> None:
        self.literal_count += 1
        if node in self.docstrings:
            return
        context = self._context(node)
        classification, tags, severity, confidence, rationale = \
            _classification(self.relative, value, context)
        if severity == "low" and not self.include_low_risk:
            return
        raw_digest = _digest({"type": _literal_kind(value), "value": value})
        sensitive = _contains_secret_value(value)
        line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", line)
        symbol = context.symbol or None
        identity_key = (
            symbol or "", _literal_kind(value), raw_digest,
            context.semantic, context.role_name)
        occurrence = self.identity_occurrences[identity_key]
        self.identity_occurrences[identity_key] += 1
        identity = _digest({
            "path": self.relative, "symbol": symbol,
            "literal_kind": _literal_kind(value), "digest": raw_digest,
            "context": context.semantic, "role": context.role_name,
            "same_context_ordinal": occurrence,
        })[:24]
        callers = self.callers_by_name.get(
            context.symbol.rsplit(".", 1)[-1], ()) if context.symbol else ()
        owner = _owner(self.relative, context.symbol)
        security, compatibility, behavior, blast, frequency = _risk_fields(
            classification, severity, len(callers))
        parameter_scope = "invocation" if classification in {
            "INVOCATION_PARAMETER", "OPTIONAL_PARAMETER_WITH_DEFAULT"} \
            else "deployment" if classification == "DEPLOYMENT_CONFIGURATION" \
            else None
        self.findings.append(HardcodingFinding(
            finding_id=f"hardcoding.{identity}",
            schema_version=AUDIT_SCHEMA_VERSION,
            repository_snapshot_id=self.snapshot_id,
            path=self.relative, symbol_ref=symbol,
            start_line=line, end_line=end_line,
            syntactic_context=context.syntactic,
            semantic_context=context.semantic,
            literal_kind=_literal_kind(value),
            literal_preview=_safe_preview(value, sensitive),
            literal_digest=raw_digest,
            sensitive_value_redacted=sensitive,
            occurrence_group_id=None, reference_count=1,
            affected_callers=tuple(callers[:20]),
            affected_contracts=(), classification=classification,
            secondary_tags=tags,
            proposed_abstraction_kind=
                ABSTRACTION_FOR_CLASSIFICATION[classification],
            proposed_authority_ref=_proposed_authority(classification, owner),
            proposed_parameter_scope=parameter_scope, owner=owner,
            change_frequency_estimate=frequency, blast_radius=blast,
            security_risk=security, compatibility_risk=compatibility,
            behavior_risk=behavior, testability="deterministic_static_and_fixture",
            severity=severity, confidence=confidence, rationale=rationale,
            evidence_refs=(f"{self.relative}:{line or 0}",),
            suggested_next_action=_action(classification)))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def _visit_function(self, node: "ast.FunctionDef | ast.AsyncFunctionDef") \
            -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, (str, int, float, bool, bytes)) \
                or node.value is None:
            self._emit(node, node.value)

    def _visit_collection(self, node: ast.AST, value: Any) -> None:
        if not list(ast.iter_child_nodes(node)):
            self._emit(node, value)
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        self._visit_collection(node, [])

    def visit_Tuple(self, node: ast.Tuple) -> None:
        self._visit_collection(node, ())

    def visit_Set(self, node: ast.Set) -> None:
        self._visit_collection(node, set())

    def visit_Dict(self, node: ast.Dict) -> None:
        self._visit_collection(node, {})


def _python_units(files: Iterable[Path], root: Path) \
        -> tuple[dict[Path, ast.Module], dict[str, tuple[str, ...]], list[dict]]:
    trees: dict[Path, ast.Module] = {}
    callers: dict[str, set[str]] = defaultdict(set)
    parse_problems = []
    for path in files:
        if path.suffix not in {".py", ".pyi"}:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            parse_problems.append({"path": relative, "detail": str(exc)})
            continue
        trees[path] = tree
        scope: list[str] = []

        class CallVisitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()

            def _function(self, node: Any) -> None:
                scope.append(node.name)
                caller = f"{relative}:{'.'.join(scope)}:{node.lineno}"
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            callers[child.func.id].add(caller)
                        elif isinstance(child.func, ast.Attribute):
                            callers[child.func.attr].add(caller)
                scope.pop()

            visit_FunctionDef = _function
            visit_AsyncFunctionDef = _function

        CallVisitor().visit(tree)
    return trees, {key: tuple(sorted(value)) for key, value in callers.items()}, \
        parse_problems


def _resource_classification(
        path: str, key_path: str, value: Any, runtime_consumed: bool) \
        -> tuple[str, tuple[str, ...], str, float, str]:
    synthetic = _LiteralContext(
        symbol=key_path, syntactic="structured_scalar",
        semantic="runtime_resource" if runtime_consumed else "source_resource",
        role_name=key_path, is_default="default" in _normal_words(key_path),
        default_parameter=key_path if "default" in _normal_words(key_path) else "",
        default_kind="resource" if "default" in _normal_words(key_path) else "",
        is_dict_key=False, is_compare=False, is_exception_text=False,
        is_user_copy=False, call_name="")
    return _classification(path, value, synthetic)


def _walk_structured(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            yield child + ".<key>", str(key)
            yield from _walk_structured(item, child)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            yield from _walk_structured(item, child)
    elif isinstance(value, (str, int, float, bool)) or value is None:
        yield prefix, value


def _parse_structured(path: Path) -> tuple[Any, "str | None"]:
    try:
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".yaml", ".yml"}:
            return yaml.safe_load(text), None
        if path.suffix == ".json":
            return json.loads(text), None
        if path.suffix == ".toml":
            return tomllib.loads(text), None
        if path.suffix == ".jsonl":
            return [json.loads(line) for line in text.splitlines()
                    if line.strip()], None
    except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
        return None, str(exc)
    return None, None


def _structured_findings(
        root: Path, path: Path, snapshot_id: str, include_low_risk: bool,
        runtime_consumed: bool) -> tuple[list[HardcodingFinding], int]:
    value, error = _parse_structured(path)
    relative = path.relative_to(root).as_posix()
    if error:
        identity = _digest({"path": relative, "parse_error": error})[:24]
        finding = HardcodingFinding(
            f"hardcoding.{identity}", AUDIT_SCHEMA_VERSION, snapshot_id,
            relative, None, None, None, "parse_error", "structured_resource",
            "parse_error", None, _digest(error), False, None, 1, (), (),
            "UNRESOLVED_REQUIRES_EXPERIMENT", ("parse_error",),
            ABSTRACTION_FOR_CLASSIFICATION["UNRESOLVED_REQUIRES_EXPERIMENT"],
            _owner(relative, ""), None, _owner(relative, ""),
            "unknown", "file", "low", "unknown", "unknown",
            "parse_after_source_correction", "medium", 1.0,
            "The structured source could not be parsed.", (relative,),
            "Correct or explicitly classify the malformed source.")
        return [finding], 0
    if value is None:
        return [], 0
    findings = []
    count = 0
    for key_path, item in _walk_structured(value):
        count += 1
        classification, tags, severity, confidence, rationale = \
            _resource_classification(relative, key_path, item, runtime_consumed)
        if key_path.endswith(".<key>"):
            classification = "PROTOCOL_OR_SCHEMA_IDENTIFIER"
            tags = ("structured_key",)
            severity = "low"
            confidence = 0.90
            rationale = "A structured key participates in a stored schema."
        if severity == "low" and not include_low_risk:
            continue
        sensitive = _contains_secret_value(item)
        secret_reference = _is_secret_reference(key_path, item)
        if sensitive or secret_reference:
            classification = "SECRET_OR_CREDENTIAL_REFERENCE"
            tags = tuple(sorted(set(tags) | {
                "security_sensitive" if sensitive else "credential_reference"}))
            severity = "critical" if sensitive else "high"
            confidence = 0.98
            rationale = ("A structured value has a secret shape."
                         if sensitive else
                         "A structured field declares a credential reference.")
        raw_digest = _digest({"type": _literal_kind(item), "value": item})
        identity = _digest({
            "path": relative, "key_path": key_path,
            "kind": _literal_kind(item), "digest": raw_digest})[:24]
        owner = _owner(relative, key_path)
        security, compatibility, behavior, blast, frequency = _risk_fields(
            classification, severity, 0)
        findings.append(HardcodingFinding(
            f"hardcoding.{identity}", AUDIT_SCHEMA_VERSION, snapshot_id,
            relative, key_path or None, None, None, "structured_scalar",
            "runtime_resource" if runtime_consumed else "source_resource",
            _literal_kind(item), _safe_preview(item, sensitive), raw_digest,
            sensitive, None, 1, (), (), classification, tags,
            ABSTRACTION_FOR_CLASSIFICATION[classification],
            _proposed_authority(classification, owner),
            "deployment" if classification == "DEPLOYMENT_CONFIGURATION"
            else None, owner, frequency, blast, security, compatibility,
            behavior, "schema_parse_and_fixture", severity, confidence,
            rationale, (f"{relative}:{key_path}",), _action(classification)))
    return findings, count


def _text_findings(
        root: Path, path: Path, snapshot_id: str, include_low_risk: bool,
        runtime_consumed: bool) -> tuple[list[HardcodingFinding], int, str]:
    relative = path.relative_to(root).as_posix()
    try:
        if path.stat().st_size > _MAX_TEXT_BYTES:
            return [], 0, "size_limit"
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], 0, "unreadable"
    findings = []
    candidates = 0
    identity_occurrences: dict[tuple[str, str, str], int] = defaultdict(int)
    patterns = (
        ("url", re.compile(r"https?://[^\s)\]>'\"]+")),
        ("environment", re.compile(
            r"(?:\$\{([A-Z][A-Z0-9_]{3,})\}|\$([A-Z][A-Z0-9_]{3,}))")),
        ("assignment", re.compile(
            r"^\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*[:=]\s*(.+)$", re.M)),
    )
    for kind, pattern in patterns:
        for match in pattern.finditer(text):
            candidates += 1
            role = match.group(1) if kind == "assignment" else kind
            raw = match.group(2).strip() if kind == "assignment" else match.group(0)
            if len(raw) > 500:
                raw = raw[:500]
            synthetic = _LiteralContext(
                symbol=role, syntactic=f"text_{kind}",
                semantic="runtime_resource" if runtime_consumed else "text_source",
                role_name=role, is_default="default" in _normal_words(role),
                default_parameter=role if "default" in _normal_words(role) else "",
                default_kind="resource" if "default" in _normal_words(role)
                else "",
                is_dict_key=False, is_compare=False, is_exception_text=False,
                is_user_copy=path.suffix in {".md", ".html"}, call_name="")
            classification, tags, severity, confidence, rationale = \
                _classification(relative, raw, synthetic)
            if severity == "low" and not include_low_risk:
                continue
            sensitive = _contains_secret_value(raw)
            secret_reference = _is_secret_reference(role, raw)
            if sensitive or (secret_reference and not synthetic.is_user_copy):
                classification = "SECRET_OR_CREDENTIAL_REFERENCE"
                tags = tuple(sorted(set(tags) | {
                    "security_sensitive" if sensitive
                    else "credential_reference"}))
                severity = "critical" if sensitive else "high"
            digest = _digest({"type": "text", "value": raw})
            line = text[:match.start()].count("\n") + 1
            identity_key = (kind, role, digest)
            occurrence = identity_occurrences[identity_key]
            identity_occurrences[identity_key] += 1
            identity = _digest({
                "path": relative, "kind": kind, "role": role,
                "digest": digest,
                "same_context_ordinal": occurrence})[:24]
            owner = _owner(relative, role)
            security, compatibility, behavior, blast, frequency = _risk_fields(
                classification, severity, 0)
            findings.append(HardcodingFinding(
                f"hardcoding.{identity}", AUDIT_SCHEMA_VERSION, snapshot_id,
                relative, role, line, line, f"text_{kind}",
                synthetic.semantic, "string", _safe_preview(raw, sensitive),
                digest, sensitive, None, 1, (), (), classification, tags,
                ABSTRACTION_FOR_CLASSIFICATION[classification],
                _proposed_authority(classification, owner), None, owner,
                frequency, blast, security, compatibility, behavior,
                "text_fixture", severity, confidence, rationale,
                (f"{relative}:{line}",), _action(classification)))
    return findings, candidates, ""


def _cluster_findings(
        findings: Iterable[HardcodingFinding]) -> tuple[HardcodingFinding, ...]:
    findings = tuple(findings)
    groups: dict[tuple[str, str], list[HardcodingFinding]] = defaultdict(list)
    for finding in findings:
        groups[(finding.literal_kind, finding.literal_digest)].append(finding)
    result = []
    for finding in findings:
        group = groups[(finding.literal_kind, finding.literal_digest)]
        if len(group) > 1:
            group_id = "literal_group." + _digest({
                "kind": finding.literal_kind,
                "digest": finding.literal_digest})[:20]
            finding = replace(
                finding, occurrence_group_id=group_id,
                reference_count=len(group),
                suggested_next_action=(
                    finding.suggested_next_action
                    + " Matching text alone does not prove shared meaning."))
        result.append(finding)
    return tuple(sorted(result, key=lambda item: (
        item.path, item.start_line or 0, item.finding_id)))


def _load_allowlist(
        path: "Path | None", findings: Mapping[str, HardcodingFinding], *,
        require_present: bool) \
        -> tuple[dict[str, AllowlistEntry], list[dict[str, str]]]:
    if path is None or not path.is_file():
        return {}, []
    problems = []
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return {}, [{"rule": "allowlist_parse", "detail": str(exc)}]
    if not isinstance(value, dict) or value.get("schema") != ALLOWLIST_SCHEMA_VERSION:
        return {}, [{
            "rule": "allowlist_schema",
            "detail": f"allowlist must declare {ALLOWLIST_SCHEMA_VERSION}"}]
    entries = {}
    today = date.today()
    for index, raw in enumerate(value.get("entries", ())):
        if not isinstance(raw, dict):
            problems.append({"rule": "allowlist_entry",
                             "detail": f"entry {index} must be a mapping"})
            continue
        required = {"finding_id", "owner", "rationale", "classification",
                    "created_on"}
        if not required <= set(raw) or any(
                not str(raw.get(name, "")).strip() for name in required):
            problems.append({"rule": "allowlist_entry",
                             "detail": f"entry {index} lacks owned rationale"})
            continue
        finding_id = str(raw["finding_id"])
        if "*" in finding_id or "?" in finding_id:
            problems.append({"rule": "allowlist_scope",
                             "detail": f"{finding_id} is not an exact ID"})
            continue
        expiration = raw.get("expires_on")
        if expiration:
            try:
                expired = date.fromisoformat(str(expiration)) < today
            except ValueError:
                expired = True
            if expired:
                problems.append({"rule": "allowlist_expired",
                                 "detail": finding_id})
                continue
        finding = findings.get(finding_id)
        if finding is None:
            if require_present:
                problems.append({"rule": "allowlist_stale",
                                 "detail": finding_id})
            continue
        if raw["classification"] != finding.classification:
            problems.append({"rule": "allowlist_classification",
                             "detail": finding_id})
            continue
        entries[finding_id] = AllowlistEntry(
            finding_id, str(raw["owner"]), str(raw["rationale"]),
            str(raw["classification"]), str(raw["created_on"]),
            str(expiration) if expiration else None)
    return entries, problems


def _summary(
        root: Path, files: tuple[Path, ...], findings: tuple[HardcodingFinding, ...],
        literal_count: int, skipped: tuple[Mapping[str, str], ...],
        allowlist_problems: list[dict[str, str]]) -> dict[str, Any]:
    unsuppressed = [item for item in findings if not item.suppressed]
    by = lambda attribute: dict(sorted(Counter(
        getattr(item, attribute) for item in unsuppressed).items()))

    def subsystem(item: HardcodingFinding) -> str:
        parts = Path(item.path).parts
        if parts[:2] == ("src", "loop_engine") and len(parts) >= 3:
            return "/".join(parts[:3])
        if parts and parts[0] in {"docs", "devtools", "examples",
                                 "benchmarks", ".github", "tools"}:
            return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
        return parts[0] if parts else "repository_root"
    file_types = Counter(
        path.suffix.lower() or path.name for path in files)
    prompt_items = [item for item in findings
                    if item.classification == "RESOURCE_OR_TEMPLATE"]
    state_items = [item for item in findings
                   if "raw_state_comparison" in item.secondary_tags]
    configuration_items = [item for item in findings if item.classification in {
        "DEPLOYMENT_CONFIGURATION", "SECRET_OR_CREDENTIAL_REFERENCE",
        "LOOP_PROFILE_SETTING", "DOMAIN_OR_TENANT_POLICY"}]
    return {
        "record_type": "hardcoding_audit_summary/v1",
        "schema_version": AUDIT_SCHEMA_VERSION,
        "repository_root_ref": str(root),
        "files_scanned": len(files),
        "files_by_type": dict(sorted(file_types.items())),
        "literal_candidates_scanned": literal_count,
        "findings": len(findings),
        "unsuppressed_findings": len(unsuppressed),
        "suppressed_findings": len(findings) - len(unsuppressed),
        "by_classification": by("classification"),
        "by_severity": by("severity"),
        "by_owner": dict(sorted(Counter(
            subsystem(item) for item in unsuppressed).items())),
        "by_subsystem": dict(sorted(Counter(
            subsystem(item) for item in unsuppressed).items())),
        "by_proposed_abstraction": by("proposed_abstraction_kind"),
        "prompt_resource_findings": len(prompt_items),
        "string_state_findings": len(state_items),
        "configuration_findings": len(configuration_items),
        "skipped_files": list(skipped),
        "allowlist_problems": allowlist_problems,
    }


def scan_hardcoding(request: AuditRequest) -> dict[str, Any]:
    """Audit all relevant source files and return typed report-mode findings."""
    root = discover_repository_root(request.repository_root)
    all_files = repository_files(root)
    files = tuple(path for path in all_files
                  if path.relative_to(root).as_posix()
                  not in _AUDIT_CONTROL_PATHS
                  if (path.suffix.lower() in _SUPPORTED_SUFFIXES
                      or path.name in _TEXT_FILENAMES)
                  and (not request.source_prefixes or any(
                      path.relative_to(root).as_posix().startswith(prefix)
                      for prefix in request.source_prefixes)))
    tree_digest = _digest([
        (path.relative_to(root).as_posix(), hashlib.sha256(
            path.read_bytes()).hexdigest()) for path in files
    ])
    snapshot_id = f"hardcoding_source.sha256_{tree_digest}"
    trees, callers, parse_problems = _python_units(files, root)
    findings: list[HardcodingFinding] = []
    literal_count = 0
    skipped: list[Mapping[str, str]] = []
    python_strings = set()
    for tree in trees.values():
        python_strings.update(
            node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str))
    for path, tree in trees.items():
        visitor = _PythonLiteralVisitor(
            root, path, tree, snapshot_id, request.include_low_risk, callers)
        visitor.visit(tree)
        findings.extend(visitor.findings)
        literal_count += visitor.literal_count
    for problem in parse_problems:
        relative = problem["path"]
        identity = _digest(problem)[:24]
        findings.append(HardcodingFinding(
            f"hardcoding.{identity}", AUDIT_SCHEMA_VERSION, snapshot_id,
            relative, None, None, None, "parse_error", "python_source",
            "parse_error", None, _digest(problem["detail"]), False, None, 1,
            (), (), "UNRESOLVED_REQUIRES_EXPERIMENT", ("parse_error",),
            ABSTRACTION_FOR_CLASSIFICATION["UNRESOLVED_REQUIRES_EXPERIMENT"],
            _owner(relative, ""), None, _owner(relative, ""), "unknown",
            "file", "low", "unknown", "unknown", "parse_after_correction",
            "medium", 1.0, "The Python source could not be parsed.",
            (relative,), "Correct or explicitly classify the malformed source."))
    structured_suffixes = {".yaml", ".yml", ".json", ".jsonl", ".toml"}
    for path in files:
        if path in trees:
            continue
        relative = path.relative_to(root).as_posix()
        runtime_consumed = (
            relative.startswith("src/loop_engine/data/")
            or relative.startswith("src/loop_engine/intelligence/")
            or relative in python_strings or path.name in python_strings)
        if path.suffix.lower() in structured_suffixes:
            found, count = _structured_findings(
                root, path, snapshot_id, request.include_low_risk,
                runtime_consumed)
            findings.extend(found)
            literal_count += count
        else:
            found, count, reason = _text_findings(
                root, path, snapshot_id, request.include_low_risk,
                runtime_consumed)
            findings.extend(found)
            literal_count += count
            if reason:
                skipped.append({"path": relative, "reason": reason})
    clustered = _cluster_findings(findings)
    by_id = {item.finding_id: item for item in clustered}
    allowlist, allowlist_problems = _load_allowlist(
        request.allowlist_path, by_id,
        require_present=request.include_low_risk)
    if allowlist:
        clustered = tuple(replace(
            item, suppressed=True,
            suppression_ref=f"{request.allowlist_path}:{item.finding_id}")
            if item.finding_id in allowlist else item
            for item in clustered)
    summary = _summary(
        root, files, clustered, literal_count, tuple(skipped),
        allowlist_problems)
    report_identity = _digest({
        "snapshot_id": snapshot_id,
        "finding_ids": [item.finding_id for item in clustered],
        "allowlist": sorted(allowlist),
    })
    return {
        "record_type": AUDIT_SCHEMA_VERSION,
        "audit_id": f"hardcoding_audit.sha256_{report_identity}",
        "repository_snapshot_id": snapshot_id,
        "summary": summary,
        "findings": [item.to_dict() for item in clustered],
    }


def run_hardcoding_audit_as_loop(
        request: AuditRequest) -> tuple[dict[str, Any], Mapping[str, Any]]:
    """Run one report-mode audit through a canonical Practitioner Loop."""
    from loop_engine import Loop, LoopConfig, StepOutcome
    from loop_engine.loop.loop_role import (
        LoopRelationship, LoopRole, LoopRoleIdentity)

    holder: dict[str, Any] = {}
    loop = Loop(
        "audit repository abstraction ownership",
        LoopConfig(
            framework="custom", custom_steps=("scan", "verify"),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",), power="standard",
            exit_condition="steps_complete"),
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.verifier"),
        relationship=LoopRelationship.starting())

    def handler(_active: Loop, step: str, _state: dict) -> StepOutcome:
        if step == "scan":
            holder["report"] = scan_hardcoding(request)
            summary = holder["report"]["summary"]
            output = {
                "files": summary["files_scanned"],
                "literal_candidates": summary["literal_candidates_scanned"],
            }
        elif step == "verify":
            summary = holder["report"]["summary"]
            if summary["allowlist_problems"]:
                return StepOutcome(
                    {"allowlist_problems": summary["allowlist_problems"]},
                    "deterministic", 0.0, failed=True)
            output = {"material_findings": summary["unsuppressed_findings"]}
        else:  # pragma: no cover - LoopConfig owns the closed step set
            raise ValueError(f"unknown hardcoding audit step {step!r}")
        return StepOutcome(output, "deterministic", 1.0)

    result = loop.run(handler=handler, max_steps=3)
    if not result.accepted or "report" not in holder:
        raise ValueError("hardcoding audit did not reach acceptance")
    return holder["report"], {
        "record_type": "hardcoding_audit_run/v1",
        "loop_id": result.loop_id, "runtime_type": "Loop",
        "profile_id": "practitioner.verifier",
        "selected_mode": "deterministic",
        "audit_id": holder["report"]["audit_id"],
    }


def write_audit_jsonl(report: Mapping[str, Any], path: "str | Path") -> Path:
    """Write a summary header followed by one finding per JSONL record."""
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({
            **report["summary"], "audit_id": report["audit_id"],
            "repository_snapshot_id": report["repository_snapshot_id"],
        }, sort_keys=True) + "\n")
        for finding in report["findings"]:
            handle.write(json.dumps({
                "record_type": "hardcoding_finding/v1", **finding},
                sort_keys=True) + "\n")
    return target


def load_audit_finding_ids(path: "str | Path") -> dict[str, str]:
    """Load finding IDs and severities from JSON or JSONL audit evidence."""
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    if source.suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        return {str(row["finding_id"]): str(row.get("severity", "low"))
                for row in rows if row.get("finding_id")}
    value = json.loads(text)
    return {str(item["finding_id"]): str(item.get("severity", "low"))
            for item in value.get("findings", ())}


def compare_with_baseline(
        report: Mapping[str, Any], baseline: Mapping[str, str]) -> dict[str, Any]:
    """Compare stable finding IDs without hiding retained findings."""
    current = {str(item["finding_id"]): str(item["severity"])
               for item in report["findings"] if not item.get("suppressed")}
    new_ids = sorted(set(current) - set(baseline))
    resolved_ids = sorted(set(baseline) - set(current))
    retained_ids = sorted(set(current) & set(baseline))
    return {
        "record_type": "hardcoding_audit_delta/v1",
        "baseline_findings": len(baseline), "current_findings": len(current),
        "new_finding_ids": new_ids,
        "resolved_finding_ids": resolved_ids,
        "retained_findings": len(retained_ids),
        "retained_finding_digest": _digest(retained_ids),
        "new_by_severity": dict(sorted(Counter(
            current[item] for item in new_ids).items())),
    }


def new_findings_at_or_above(
        delta: Mapping[str, Any], report: Mapping[str, Any], severity: str) \
        -> tuple[str, ...]:
    """Return new finding IDs at a configured CI severity threshold."""
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    threshold = order[severity]
    current = {item["finding_id"]: item for item in report["findings"]}
    return tuple(item for item in delta["new_finding_ids"]
                 if order.get(current[item]["severity"], 0) >= threshold)


def self_test() -> dict[str, Any]:
    """Canary-prove context, redaction, distinction, delta, and allowlisting."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with TemporaryDirectory() as directory:
        root = Path(directory)
        package = root / "src" / "loop_engine"
        package.mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            "[project]\nname='loop-engine'\nversion='0.0.0'\n"
            "[tool.setuptools]\npackage-dir={''='src'}\n", encoding="utf-8")
        source = package / "sample.py"
        source.write_text(
            "import os\n"
            "SYSTEM_PROMPT = ('You are a bounded reviewer. Do not authorize '"
            "                 'changes. Return only structured JSON with '"
            "                 'evidence, assumptions, and an abstention.')\n"
            "def choose(status='pending', enabled=False, count=0, value=None):\n"
            "    key = os.getenv('SERVICE_API_KEY', '')\n"
            "    planted_secret = 'sk-fixture0123456789abcdef'\n"
            "    if status == 'active':\n"
            "        return {'status': 'ready', 'key': key}\n"
            "    return {'status': 'ready'}\n",
            encoding="utf-8")
        (package / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        initial = scan_hardcoding(AuditRequest(root, include_low_risk=True))
        findings = initial["findings"]
        check("inline_prompt_is_a_resource_finding", any(
            item["classification"] == "RESOURCE_OR_TEMPLATE"
            and item["symbol_ref"] is None for item in findings))
        check("direct_environment_read_is_detected", any(
            item["classification"] == "SECRET_OR_CREDENTIAL_REFERENCE"
            and "credential_reference" in item["secondary_tags"]
            and not item["sensitive_value_redacted"]
            for item in findings))
        check("secret_shaped_value_is_redacted", any(
            item["sensitive_value_redacted"]
            and item["literal_preview"] == "<redacted>"
            for item in findings))
        default_tags = {tag for item in findings
                        if item["classification"]
                        == "OPTIONAL_PARAMETER_WITH_DEFAULT"
                        for tag in item["secondary_tags"]}
        check("null_false_and_zero_defaults_remain_distinct",
              {"ambiguous_null_or_omitted", "explicit_false",
               "explicit_zero"} <= default_tags)
        check("raw_state_comparison_is_detected", any(
            "raw_state_comparison" in item["secondary_tags"]
            for item in findings))
        check("malformed_source_is_bounded_not_fatal", any(
            item["literal_kind"] == "parse_error" for item in findings))
        duplicate_ready = [item for item in findings
                           if item["literal_preview"] == "'ready'"]
        check("duplicate_text_is_grouped_without_forced_centralization",
              len(duplicate_ready) == 2
              and all(item["occurrence_group_id"] for item in duplicate_ready)
              and all("does not prove shared meaning"
                      in item["suggested_next_action"]
                      for item in duplicate_ready))
        stable_before = {
            item["finding_id"] for item in findings
            if item["path"].endswith("sample.py")}
        source.write_text(
            "# unrelated line movement\n" + source.read_text(encoding="utf-8"),
            encoding="utf-8")
        moved = scan_hardcoding(AuditRequest(root, include_low_risk=True))
        stable_after = {
            item["finding_id"] for item in moved["findings"]
            if item["path"].endswith("sample.py")}
        check("finding_ids_survive_unrelated_line_movement",
              stable_before == stable_after)
        source.write_text(
            source.read_text(encoding="utf-8").removeprefix(
                "# unrelated line movement\n"), encoding="utf-8")
        local = next(item for item in findings
                     if item["classification"] == "INTENTIONAL_LOCAL_LITERAL")
        allowlist_path = root / "allowlist.yaml"
        allowlist_path.write_text(yaml.safe_dump({
            "schema": ALLOWLIST_SCHEMA_VERSION,
            "entries": [{
                "finding_id": local["finding_id"], "owner": "test-owner",
                "rationale": "The one-use value is clearer beside its owner.",
                "classification": local["classification"],
                "created_on": "2026-08-31",
            }]}), encoding="utf-8")
        allowed = scan_hardcoding(AuditRequest(
            root, include_low_risk=True, allowlist_path=allowlist_path))
        check("exact_owned_allowlist_retains_and_marks_finding", any(
            item["finding_id"] == local["finding_id"] and item["suppressed"]
            for item in allowed["findings"]))
        baseline = {item["finding_id"]: item["severity"] for item in findings}
        source.write_text(source.read_text(encoding="utf-8")
                          + "\nMODE='unsafe'\nif MODE == 'override':\n    pass\n",
                          encoding="utf-8")
        changed = scan_hardcoding(AuditRequest(root, include_low_risk=True))
        delta = compare_with_baseline(changed, baseline)
        check("new_violation_is_visible_in_delta",
              bool(delta["new_finding_ids"]))
        check("representative_new_high_violation_blocks_ci_gate",
              bool(new_findings_at_or_above(delta, changed, "high")))
        loop_report, run_record = run_hardcoding_audit_as_loop(
            AuditRequest(root, include_low_risk=False))
        check("audit_operation_runs_through_canonical_loop",
              run_record["runtime_type"] == "Loop"
              and run_record["selected_mode"] == "deterministic"
              and run_record["audit_id"] == loop_report["audit_id"])
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "hardcoding_audit_self_test/v1",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }
