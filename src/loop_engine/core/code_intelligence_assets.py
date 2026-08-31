"""Flexible Code Intelligence cards, templates, and lazy loop capsules.

Architectural role: internal Code Intelligence schema and materialization service.

Owns: Code asset templates for functions, files, packages, repositories,
services, dataset-backed systems, template repositories, large frameworks,
worker systems, and LLM harnesses. Search cards stay small while bodies,
datasets, and large source trees remain behind immutable references.

Does not own: downloading untrusted code, dependency installation, sandboxing,
authorization, or promotion. Loading and execution are separate loops.

Public entry points: ``CodeAssetSpec``, ``code_asset_record``,
``code_asset_capsule``, and ``execute_code_ref``.

Verification: ``self_test()`` models a forty-file, million-line system without
putting its body into the search card, then loads and executes one entry point.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from typing import Mapping

from ..loop.loop_capsule import ExternalPayloadRef as ExternalBodyRef


CODE_ASSET_KINDS = (
    "function", "single_file", "module", "package", "repository",
    "template_repository", "service", "dataset_backed_system", "container",
    "large_framework", "worker_system", "llm_harness", "command_line_tool",
    "core_plugin", "agent_skill_bundle", "workflow",
    "notebook")

LOAD_STRATEGIES = (
    "import", "entrypoint", "selective_file", "package_install",
    "repository_checkout", "service_call", "container_run",
    "dataset_mount", "manifest_then_select")

SOURCE_KINDS = (
    "local_path", "python_package", "pypi", "github", "gitlab", "git",
    "http_api", "container_registry", "object_store", "database", "other")

CODE_ASSET_LIFECYCLE = (
    "draft", "candidate", "validated", "registered", "deprecated",
    "quarantined", "rejected", "superseded", "retired")


class CodeAssetAdmissionError(ValueError):
    """An exact Code Intelligence admission invariant failed."""


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_sha256(label: str, value: str) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef"
                   for character in value)):
        raise CodeAssetAdmissionError(
            f"{label} must be a lowercase SHA-256 digest")

CODE_INTELLIGENCE_TEMPLATES = {
    "pure_function": {
        "asset_kind": "function", "load_strategy": "import",
        "components": ("callable", "input_contract", "output_contract", "tests"),
        "description": "One bounded callable executed inside a component loop."},
    "single_file_component": {
        "asset_kind": "single_file", "load_strategy": "selective_file",
        "components": ("file_ref", "entrypoint", "contract", "tests"),
        "description": "One source file loaded only after its card is selected."},
    "multi_file_module": {
        "asset_kind": "module", "load_strategy": "manifest_then_select",
        "components": ("module_manifest", "entrypoints", "contracts", "tests"),
        "description": "A module card with file references and named entry points."},
    "pypi_package": {
        "asset_kind": "package", "load_strategy": "package_install",
        "components": ("distribution", "version", "entrypoints", "license", "lock"),
        "description": "A pinned Python distribution represented by metadata and imports."},
    "github_repository": {
        "asset_kind": "repository", "load_strategy": "repository_checkout",
        "components": ("repository", "commit", "manifest", "entrypoints", "license"),
        "description": "A commit-pinned repository loaded selectively after retrieval."},
    "template_repository": {
        "asset_kind": "template_repository",
        "load_strategy": "manifest_then_select",
        "components": ("template_manifest", "variables", "files", "validation"),
        "description": "A repository template with parameters and expected outputs."},
    "service_adapter": {
        "asset_kind": "service", "load_strategy": "service_call",
        "components": ("endpoint", "request_contract", "response_contract", "effects"),
        "description": "A remote or local service called through a declared adapter loop."},
    "dataset_backed_system": {
        "asset_kind": "dataset_backed_system",
        "load_strategy": "dataset_mount",
        "components": ("code_ref", "dataset_refs", "schema", "entrypoint", "tests"),
        "description": "Code and datasets stored separately and joined by references."},
    "large_framework": {
        "asset_kind": "large_framework",
        "load_strategy": "manifest_then_select",
        "components": ("root_manifest", "subsystems", "entrypoints", "contracts",
                       "dependency_lock", "test_map"),
        "description": "A large codebase represented as subsystem cards, never one body."},
    "worker_system": {
        "asset_kind": "worker_system",
        "load_strategy": "manifest_then_select",
        "components": ("preflight", "execute", "postflight", "diagnostics",
                       "logging", "configuration", "contracts", "test_map"),
        "description": "A worker framework split into lifecycle subsystem loops."},
    "llm_harness": {
        "asset_kind": "llm_harness",
        "load_strategy": "entrypoint",
        "components": ("adapter", "model_policy", "tool_contracts", "effects",
                       "transcript", "verification"),
        "description": "An LLM harness wrapped as an opaque governed loop."},
    "command_line_tool": {
        "asset_kind": "command_line_tool", "load_strategy": "entrypoint",
        "components": ("distribution", "version", "command", "arguments",
                       "environment", "effects", "tests"),
        "description": "A pinned command-line tool invoked through one component loop."},
    "core_plugin": {
        "asset_kind": "core_plugin",
        "load_strategy": "entrypoint",
        "components": ("registration_function", "capability_handshake",
                       "operations", "effects", "auth", "tests"),
        "description": "A manually registered capability with local discovery and loop-bound invocation."},
    "agent_skill_bundle": {
        "asset_kind": "agent_skill_bundle",
        "load_strategy": "manifest_then_select",
        "components": ("context_refs", "code_refs", "assets", "triggers",
                       "permissions", "verification"),
        "description": "A skill manifest that links Context records and optional Code assets without merging their layers."},
    "workflow": {
        "asset_kind": "workflow", "load_strategy": "manifest_then_select",
        "components": ("steps", "entrypoints", "contracts", "effects",
                       "checkpoints", "tests"),
        "description": "A multi-step executable workflow represented by a manifest and step loops."},
    "notebook": {
        "asset_kind": "notebook", "load_strategy": "selective_file",
        "components": ("notebook_ref", "environment_lock", "inputs",
                       "outputs", "effects", "tests"),
        "description": "A pinned notebook treated as an executable artifact, not copied into a search row."},
}


def _reference_dict(value):
    """Normalize a dataset or artifact locator without reading its body."""
    if isinstance(value, ExternalBodyRef):
        return value.to_dict()
    if isinstance(value, dict):
        return dict(value)
    return {"uri": str(value)}


@dataclass(frozen=True)
class CodeAssetSpec:
    """The small searchable card for one Code Intelligence asset."""
    asset_id: str
    name: str
    description: str
    asset_kind: str
    source_kind: str
    body_ref: ExternalBodyRef
    entrypoints: tuple = ()
    modes: tuple = ("deterministic",)
    input_contract: str = "any"
    output_contract: str = "any"
    effects: tuple = ("pure",)
    dependencies: tuple = ()
    data_refs: tuple = ()
    file_count: int = 1
    line_count: int = 0
    load_strategy: str = "manifest_then_select"
    template_id: str = ""
    version: str = "1.0.0"
    license: str = "unknown"
    lifecycle: str = "candidate"
    admission_ref: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.asset_kind not in CODE_ASSET_KINDS:
            raise ValueError(f"asset_kind must be one of {CODE_ASSET_KINDS}")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(f"source_kind must be one of {SOURCE_KINDS}")
        if self.load_strategy not in LOAD_STRATEGIES:
            raise ValueError(f"load_strategy must be one of {LOAD_STRATEGIES}")
        if self.template_id and self.template_id not in CODE_INTELLIGENCE_TEMPLATES:
            raise ValueError(f"unknown Code Intelligence template {self.template_id}")
        if self.file_count < 1 or self.line_count < 0:
            raise ValueError("file_count must be positive and line_count nonnegative")
        from ..loop.recursive_loop import MODES
        from .facets import EFFECTS
        if any(mode not in MODES for mode in self.modes):
            raise ValueError(f"modes must be drawn from {MODES}")
        if any(effect not in EFFECTS for effect in self.effects):
            raise ValueError(f"effects must be drawn from {EFFECTS}")
        if self.lifecycle not in CODE_ASSET_LIFECYCLE:
            raise ValueError("unknown Code asset lifecycle")
        if self.lifecycle == "registered" and not self.admission_ref:
            raise ValueError("registered Code assets require an admission_ref")
        secret_keys = {"secret", "token", "password", "api_key", "credential"}

        def keys(value):
            if not isinstance(value, dict):
                return set()
            found = {str(key).lower() for key in value}
            for nested in value.values():
                found |= keys(nested)
            return found

        if any(any(part in key for part in secret_keys)
               for key in keys(self.metadata)):
            raise ValueError("search metadata cannot contain secret-shaped keys")

    @property
    def card_digest(self) -> str:
        body = {"asset_id": self.asset_id, "name": self.name,
                "description": self.description, "version": self.version,
                "asset_kind": self.asset_kind, "source_kind": self.source_kind,
                "body_ref": self.body_ref.to_dict(),
                "entrypoints": list(self.entrypoints), "modes": list(self.modes),
                "contracts": [self.input_contract, self.output_contract],
                "effects": list(self.effects),
                "dependencies": list(self.dependencies),
                "data_refs": [_reference_dict(ref) for ref in self.data_refs],
                "file_count": self.file_count,
                "line_count": self.line_count,
                "load_strategy": self.load_strategy,
                "template_id": self.template_id, "license": self.license,
                "lifecycle": self.lifecycle,
                "admission_ref": self.admission_ref,
                "metadata": dict(self.metadata)}
        return hashlib.sha256(
            json.dumps(body, sort_keys=True).encode()).hexdigest()

    @property
    def dependency_digest(self) -> str:
        return _sha256(list(self.dependencies))

    @property
    def contract_digest(self) -> str:
        return _sha256({
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
        })

    @property
    def effect_digest(self) -> str:
        return _sha256(list(self.effects))

    @property
    def qualification_digest(self) -> str:
        """Stable executable identity unaffected by lifecycle transitions."""
        return _sha256({
            "asset_id": self.asset_id,
            "version": self.version,
            "body_digest": self.body_ref.digest,
            "entrypoints": list(self.entrypoints),
            "modes": list(self.modes),
            "dependency_digest": self.dependency_digest,
            "contract_digest": self.contract_digest,
            "effect_digest": self.effect_digest,
            "load_strategy": self.load_strategy,
        })

    def to_dict(self) -> dict:
        return {
            "record_type": "code_asset_spec/v1",
            "asset_id": self.asset_id,
            "name": self.name,
            "description": self.description,
            "asset_kind": self.asset_kind,
            "source_kind": self.source_kind,
            "body_ref": self.body_ref.to_dict(),
            "entrypoints": list(self.entrypoints),
            "modes": list(self.modes),
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "effects": list(self.effects),
            "dependencies": list(self.dependencies),
            "data_refs": [_reference_dict(ref) for ref in self.data_refs],
            "file_count": self.file_count,
            "line_count": self.line_count,
            "load_strategy": self.load_strategy,
            "template_id": self.template_id,
            "version": self.version,
            "license": self.license,
            "lifecycle": self.lifecycle,
            "admission_ref": self.admission_ref,
            "metadata": dict(self.metadata),
            "card_digest": self.card_digest,
            "qualification_digest": self.qualification_digest,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CodeAssetSpec":
        body = dict(value)
        if body.pop("record_type", "") != "code_asset_spec/v1":
            raise ValueError("CodeAssetSpec record type is unsupported")
        expected_card = str(body.pop("card_digest", ""))
        expected_qualification = str(body.pop("qualification_digest", ""))
        payload = body.get("body_ref")
        if not isinstance(payload, Mapping):
            raise ValueError("CodeAssetSpec body_ref must be an object")
        body["body_ref"] = ExternalBodyRef(**dict(payload))
        for name in ("entrypoints", "modes", "effects", "dependencies",
                     "data_refs"):
            body[name] = tuple(body.get(name) or ())
        spec = cls(**body)
        if (expected_card != spec.card_digest
                or expected_qualification != spec.qualification_digest):
            raise ValueError("CodeAssetSpec digest does not match its content")
        return spec


@dataclass(frozen=True)
class CodeAssetAdmissionRecord:
    """Independent qualification authority for one exact Code asset."""

    admission_id: str
    asset_id: str
    asset_version: str
    qualification_digest: str
    body_digest: str
    dependency_digest: str
    contract_digest: str
    effect_digest: str
    producer_id: str
    verifier_id: str
    evidence_refs: tuple[str, ...]
    evidence_digest: str
    schema_version: str = "code_asset_admission/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "code_asset_admission/v1":
            raise CodeAssetAdmissionError(
                "unsupported Code asset admission schema")
        for label, value in (
                ("admission_id", self.admission_id),
                ("asset_id", self.asset_id),
                ("asset_version", self.asset_version),
                ("producer_id", self.producer_id),
                ("verifier_id", self.verifier_id)):
            if not isinstance(value, str) or not value.strip():
                raise CodeAssetAdmissionError(f"{label} is required")
        if self.producer_id.casefold() == self.verifier_id.casefold():
            raise CodeAssetAdmissionError(
                "a Code asset producer cannot be its sole verifier")
        for label, value in (
                ("qualification_digest", self.qualification_digest),
                ("body_digest", self.body_digest),
                ("dependency_digest", self.dependency_digest),
                ("contract_digest", self.contract_digest),
                ("effect_digest", self.effect_digest),
                ("evidence_digest", self.evidence_digest)):
            _require_sha256(label, value)
        refs = tuple(self.evidence_refs)
        if (not refs or len(refs) != len(set(refs))
                or any(not isinstance(item, str) or not item.strip()
                       for item in refs)):
            raise CodeAssetAdmissionError(
                "Code asset admission needs unique evidence references")
        object.__setattr__(self, "evidence_refs", refs)

    @property
    def digest(self) -> str:
        return _sha256(self._body())

    def _body(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "admission_id": self.admission_id,
            "asset_id": self.asset_id,
            "asset_version": self.asset_version,
            "qualification_digest": self.qualification_digest,
            "body_digest": self.body_digest,
            "dependency_digest": self.dependency_digest,
            "contract_digest": self.contract_digest,
            "effect_digest": self.effect_digest,
            "producer_id": self.producer_id,
            "verifier_id": self.verifier_id,
            "evidence_refs": list(self.evidence_refs),
            "evidence_digest": self.evidence_digest,
        }

    def to_dict(self) -> dict:
        return {**self._body(), "record_digest": self.digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]
                  ) -> "CodeAssetAdmissionRecord":
        body = dict(value)
        expected = str(body.pop("record_digest", ""))
        body["evidence_refs"] = tuple(body.get("evidence_refs") or ())
        record = cls(**body)
        if expected != record.digest:
            raise CodeAssetAdmissionError(
                "Code asset admission digest does not match")
        return record


def admit_code_asset(
        spec: CodeAssetSpec,
        admission: CodeAssetAdmissionRecord) -> CodeAssetSpec:
    """Promote one exact validated Code asset without changing its body."""
    if not isinstance(spec, CodeAssetSpec):
        raise CodeAssetAdmissionError("admission requires CodeAssetSpec")
    if not isinstance(admission, CodeAssetAdmissionRecord):
        raise CodeAssetAdmissionError(
            "admission requires CodeAssetAdmissionRecord")
    expected = (
        spec.asset_id, spec.version, spec.qualification_digest,
        spec.body_ref.digest, spec.dependency_digest, spec.contract_digest,
        spec.effect_digest)
    observed = (
        admission.asset_id, admission.asset_version,
        admission.qualification_digest, admission.body_digest,
        admission.dependency_digest, admission.contract_digest,
        admission.effect_digest)
    if expected != observed:
        raise CodeAssetAdmissionError(
            "admission does not bind this exact artifact and contract set")
    if spec.lifecycle not in ("candidate", "validated"):
        raise CodeAssetAdmissionError(
            "only a candidate or validated Code asset can be admitted")
    return replace(
        spec, lifecycle="registered", admission_ref=admission.admission_id)


def spec_from_template(template_id: str, **values) -> CodeAssetSpec:
    """Create a Code asset card from one declared template."""
    try:
        template = CODE_INTELLIGENCE_TEMPLATES[template_id]
    except KeyError as exc:
        raise ValueError(f"unknown template {template_id!r}") from exc
    return CodeAssetSpec(
        template_id=template_id, asset_kind=template["asset_kind"],
        load_strategy=template["load_strategy"], **values)


def code_asset_record(spec: CodeAssetSpec):
    """Project a Code asset into one small flexible search card."""
    from .store_serve import StoreRecord
    from .facets import code_facets
    maturity = spec.lifecycle
    tier = "core" if maturity in ("registered", "implemented") else "experimental"
    body = {
        "role": "code_asset", "asset_kind": spec.asset_kind,
        "description": spec.description, "source_kind": spec.source_kind,
        "payload_ref": spec.body_ref.uri, "body_digest": spec.body_ref.digest,
        "body_size_bytes": spec.body_ref.size_bytes,
        "body_inline": False, "entrypoints": list(spec.entrypoints),
        "input_contract": spec.input_contract,
        "output_contract": spec.output_contract,
        "dependencies": list(spec.dependencies),
        "data_refs": [_reference_dict(ref) for ref in spec.data_refs],
        "file_count": spec.file_count, "line_count": spec.line_count,
        "load_strategy": spec.load_strategy, "template_id": spec.template_id,
        "version": spec.version, "license": spec.license,
        "admission_ref": spec.admission_ref,
        "maturity": maturity, "card_digest": spec.card_digest,
        "qualification_digest": spec.qualification_digest,
        "dependency_digest": spec.dependency_digest,
        "contract_digest": spec.contract_digest,
        "effect_digest": spec.effect_digest,
        "metadata": dict(spec.metadata),
        "facets": code_facets(
            execution_mode="code_only" if spec.modes == ("deterministic",)
            else "hybrid",
            determinism="deterministic" if spec.modes == ("deterministic",)
            else "stochastic",
            locality="api_calling" if "network" in spec.effects
            else "local_machine", effects=spec.effects,
            cost_class="metered" if "network" in spec.effects else "free",
            role="execute", lifecycle=maturity)}
    tags = ("code_asset", spec.asset_kind, spec.source_kind,
            spec.load_strategy, spec.template_id or "custom")
    return StoreRecord(spec.asset_id, "node", spec.name, body=body,
                       tags=tags, tier=tier, source=spec.source_kind)


def code_asset_capsule(spec: CodeAssetSpec):
    """Wrap the card as a lazy Code Intelligence package."""
    from ..loop.loop_capsule import IntelligenceItemPackage, IntelligenceItemHandshake
    handshake = IntelligenceItemHandshake(
        item_id=spec.asset_id, layer="code_intelligence",
        supported_modes=spec.modes,
        input_contract=spec.input_contract,
        output_contract="code_asset_ref",
        effects=tuple(spec.effects),
        cost_class="metered" if "network" in spec.effects else "free",
        maturity=spec.lifecycle, version=spec.version)
    return IntelligenceItemPackage(
        item_id=spec.asset_id, layer="code_intelligence",
        handshake=handshake,
        payload_ref=spec.body_ref.uri, payload_digest=spec.body_ref.digest,
        provenance=spec.source_kind,
        lifecycle=spec.lifecycle if spec.lifecycle in (
            "draft", "candidate", "validated", "registered", "deprecated",
            "retired") else "candidate",
        facets={"asset_kind": spec.asset_kind,
                "load_strategy": spec.load_strategy,
                "body_digest": spec.body_ref.digest})


def subsystem_records(spec: CodeAssetSpec) -> list:
    """Project a large system into independently searchable subsystem cards."""
    from .store_serve import StoreRecord
    names = tuple((spec.metadata or {}).get("subsystems") or ())
    entrypoint_map = dict((spec.metadata or {}).get("subsystem_entrypoints")
                          or {})
    records = []
    for name in names:
        slug = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
        records.append(StoreRecord(
            f"{spec.asset_id}.subsystem.{slug}", "node",
            f"{spec.name} subsystem: {str(name).replace('_', ' ')}",
            body={"role": "code_asset_subsystem", "parent_asset": spec.asset_id,
                  "payload_ref": spec.body_ref.uri,
                  "body_digest": spec.body_ref.digest,
                  "entrypoints": list(entrypoint_map.get(name)
                                      or entrypoint_map.get(slug) or (
                                          entrypoint for entrypoint
                                          in spec.entrypoints
                                          if slug in entrypoint.lower())),
                  "asset_kind": "module", "body_inline": False,
                  "load_strategy": "manifest_then_select",
                  "maturity": spec.lifecycle,
                  "facets": {"category": "code_subsystem",
                             "subcategory": slug, "scope": "package",
                             "lifecycle": spec.lifecycle}},
            tags=("code_subsystem", spec.asset_id, slug),
            tier="core" if spec.lifecycle == "registered" else "experimental",
            source=spec.source_kind))
    return records


class MaterializationCache:
    """Resolve one immutable external body once and reuse its local handle."""
    def __init__(self, resolver):
        self.resolver = resolver
        self._by_digest = {}
        self.calls = 0

    def __call__(self, payload_ref: str, payload_digest: str = ""):
        key = payload_digest or payload_ref
        if key not in self._by_digest:
            self.calls += 1
            self._by_digest[key] = self.resolver(payload_ref, payload_digest)
        return self._by_digest[key]


@dataclass(frozen=True)
class CodeRefExecutionRequest:
    """Passive input for loading and executing one selected Code reference."""

    ref: object
    resolver: object
    entrypoint: str = ""
    bind: object | None = None
    inputs: object | None = None


@dataclass(frozen=True)
class CodeRefExecutionContext:
    """Optional Loop ownership context for Code reference execution."""

    ledger: object | None = None
    parent: object | None = None


def execute_code_ref(
        request: CodeRefExecutionRequest,
        context: CodeRefExecutionContext | None = None):
    """Materialize a selected Code ref, then execute it in a component loop."""
    from ..loop.loop_capsule import (
        IntelligenceLoadContext, IntelligenceLoadRequest,
        load_intelligence_ref)
    from ..loop.encapsulate import as_component_loop
    selected_context = context or CodeRefExecutionContext()
    loaded = load_intelligence_ref(
        IntelligenceLoadRequest(request.ref, request.resolver),
        IntelligenceLoadContext(
            selected_context.ledger, selected_context.parent))
    payload = loaded["value"]
    operation = payload
    if not callable(operation) and request.bind is not None:
        operation = request.bind(payload, request.entrypoint)
    elif not callable(operation) and isinstance(payload, dict):
        operation = payload.get(request.entrypoint)
    if not callable(operation):
        raise TypeError("the selected Code asset did not resolve the entrypoint")
    executed = as_component_loop(
        f"execute Code Intelligence {request.ref.handshake.item_id}",
        operation, inputs=request.inputs, ledger=selected_context.ledger,
        parent=selected_context.parent)
    return {"materialization": loaded, "execution": executed,
            "value": executed["value"]}


def code_template_records() -> list:
    """The reusable Code Intelligence templates as searchable Code records."""
    from .store_serve import StoreRecord
    records = []
    for template_id, body in CODE_INTELLIGENCE_TEMPLATES.items():
        records.append(StoreRecord(
            f"code_template.{template_id}", "node", body["description"],
            body={"role": "code_asset_template", "template_id": template_id,
                  "asset_kind": body["asset_kind"],
                  "load_strategy": body["load_strategy"],
                  "components": list(body["components"]),
                  "description": body["description"],
                  "maturity": "registered",
                  "facets": {"category": "code_asset_template",
                             "subcategory": body["asset_kind"],
                             "scope": "package", "lifecycle": "registered"}},
            tags=("code_asset_template", template_id, body["asset_kind"]),
            source="code_asset_templates"))
    return records


def self_test() -> dict:
    from ..loop.recursive_loop import LoopLedger
    million_line_ref = ExternalBodyRef(
        "git+https://github.com/example/large-worker.git@0123456789abcdef",
        digest="a" * 64, size_bytes=180_000_000,
        media_type="application/vnd.git.repository")
    spec = spec_from_template(
        "worker_system", asset_id="code.large_worker", name="Large worker",
        description=("Forty-file worker with preflight, execution, postflight, "
                     "diagnostics, logging, and configuration subsystems."),
        source_kind="github", body_ref=million_line_ref,
        entrypoints=("worker.preflight", "worker.run", "worker.postflight",
                     "worker.diagnostics", "worker.log", "worker.configure"),
        input_contract="work_packet",
        output_contract="work_result",
        data_refs=(ExternalBodyRef(
            "s3://example-bucket/worker-fixtures.parquet", "d" * 64,
            size_bytes=9_000_000_000,
            media_type="application/vnd.apache.parquet"),),
        file_count=40, line_count=1_000_000,
        license="Apache-2.0", lifecycle="registered",
        admission_ref="promotion:test-worker-v1",
        metadata={"subsystems": ["preflight", "execute", "postflight",
                                 "diagnostics", "logging", "configuration"],
                  "subsystem_entrypoints": {
                      "preflight": ["worker.preflight"],
                      "execute": ["worker.run"],
                      "postflight": ["worker.postflight"],
                      "diagnostics": ["worker.diagnostics"],
                      "logging": ["worker.log"],
                      "configuration": ["worker.configure"]}})
    record = code_asset_record(spec)
    capsule = code_asset_capsule(spec)
    ref = capsule.to_ref(score=0.9, source="code_intelligence")
    lazy_before = not capsule.materialised
    ledger = LoopLedger()
    from ..loop.loop_capsule import MaterializedPayload
    cache = MaterializationCache(
        lambda payload_ref, payload_digest: MaterializedPayload(
            {"worker.run": lambda value: value + 1}, payload_digest,
            local_ref="/cache/large-worker"))
    resolver = lambda payload_ref: cache(payload_ref, million_line_ref.digest)
    out = execute_code_ref(CodeRefExecutionRequest(
        ref, resolver, entrypoint="worker.run", inputs=41),
        CodeRefExecutionContext(ledger=ledger))
    out_again = execute_code_ref(CodeRefExecutionRequest(
        ref, resolver, entrypoint="worker.run", inputs=9),
        CodeRefExecutionContext(ledger=ledger))
    records = code_template_records()
    subsystems = subsystem_records(spec)
    bad_digest = False
    try:
        execute_code_ref(CodeRefExecutionRequest(
            ref, lambda payload_ref: MaterializedPayload(
                {"worker.run": lambda value: value}, "b" * 64),
            entrypoint="worker.run", inputs=1))
    except ValueError:
        bad_digest = True
    self_admission = False
    try:
        spec_from_template(
            "pure_function", asset_id="code.unreviewed", name="Unreviewed",
            description="unreviewed", source_kind="local_path",
            body_ref=ExternalBodyRef("path:fn.py", "c" * 64),
            lifecycle="registered")
    except ValueError:
        self_admission = True
    admission = CodeAssetAdmissionRecord(
        "admission-large-worker", spec.asset_id, spec.version,
        spec.qualification_digest, spec.body_ref.digest,
        spec.dependency_digest, spec.contract_digest, spec.effect_digest,
        "producer-loop", "verifier-loop", ("suite:large-worker",),
        _sha256({"suite": "large-worker", "passed": True}))
    admission_candidate = replace(
        spec, lifecycle="candidate", admission_ref="")
    registered = admit_code_asset(admission_candidate, admission)
    changed_proof_refused = False
    try:
        admit_code_asset(
            admission_candidate,
            replace(admission, body_digest="b" * 64))
    except CodeAssetAdmissionError:
        changed_proof_refused = True
    tests = [
        {"test": "large_system_search_card_contains_no_large_body",
         "passed": record.body["body_inline"] is False
         and record.body["file_count"] == 40
         and record.body["line_count"] == 1_000_000
         and "source" not in record.body.get("metadata", {})
         and len(json.dumps(record.to_dict())) < 5000},
        {"test": "large_code_is_lazy_then_executes_through_two_loops",
         "passed": lazy_before and out["value"] == 42
         and out_again["value"] == 10 and cache.calls == 1
         and out["materialization"]["local_ref"] == "/cache/large-worker"
         and out["materialization"]["model_calls"] == 0
         and out["execution"]["model_calls"] == 0
         and len(ledger.loops()) >= 2},
        {"test": "code_templates_cover_packages_repositories_and_workers",
         "passed": len(records) == len(CODE_INTELLIGENCE_TEMPLATES) >= 16
         and {record.body["template_id"] for record in records}
         >= {"pypi_package", "github_repository", "template_repository",
             "large_framework", "worker_system", "llm_harness",
             "command_line_tool", "core_plugin",
             "agent_skill_bundle", "workflow", "notebook"}},
        {"test": "large_framework_is_split_into_searchable_subsystem_cards",
         "passed": len(subsystems) == 6
         and all(record.body["body_inline"] is False for record in subsystems)
         and all(record.body["entrypoints"] for record in subsystems)
         and {record.body["facets"]["subcategory"] for record in subsystems}
         >= {"preflight", "postflight", "diagnostics", "logging"}},
        {"test": "payload_digest_and_admission_fail_closed",
         "passed": bad_digest and self_admission},
        {"test": "independent_admission_binds_exact_executable_identity",
         "passed": registered.lifecycle == "registered"
         and registered.admission_ref == admission.admission_id
         and registered.body_ref.digest == spec.body_ref.digest
         and registered.qualification_digest == spec.qualification_digest},
        {"test": "changed_artifact_cannot_reuse_prior_admission",
         "passed": changed_proof_refused},
        {"test": "large_datasets_remain_separate_digest_bound_references",
         "passed": record.body["data_refs"][0]["uri"].startswith("s3://")
         and record.body["data_refs"][0]["digest"] == "d" * 64
         and record.body["data_refs"][0]["size_bytes"] == 9_000_000_000
         and "worker-fixtures" not in json.dumps(record.body.get(
             "metadata", {}))},
    ]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
