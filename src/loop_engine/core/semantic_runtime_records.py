"""Passive Semantic ABI, trust-state, realization, and evidence records.

These immutable records add no runtime type. They bind an implementationless
semantic specification to one exact ``LoopDefinition`` and describe candidate,
verified, authorized, committed, reliability, and strategy evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from ..loop.loop_definition import LoopDefinitionRef


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MODES = ("deterministic", "hybrid", "non_deterministic")
_TRUST_LABELS = (
    "verified_fact", "trusted_policy", "untrusted_input",
    "untrusted_retrieval", "untrusted_tool_output")


class SemanticRuntimeContractError(ValueError):
    """A Semantic ABI record is malformed or internally inconsistent."""


class SemanticDisposition(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABSTAINED = "abstained"
    ESCALATED = "escalated"
    REPAIR_REQUIRED = "repair_required"


class SemanticRealizationKind(str, Enum):
    DETERMINISTIC_CODE = "deterministic_code"
    CACHED_PROCEDURE = "cached_procedure"
    PROMOTED_COMPOSITE = "promoted_composite"
    HYBRID_SEMANTIC = "hybrid_semantic"
    DIRECT_SEMANTIC = "direct_semantic"
    NOVEL_GENERATION = "novel_generation"
    HUMAN_AUTHORITY = "human_authority"


def canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SemanticRuntimeContractError(
            "semantic record value must be strict JSON") from exc


def semantic_digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _identifier(label: str, value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise SemanticRuntimeContractError(f"{label} is invalid")
    return value


def _version(label: str, value: str) -> str:
    if not isinstance(value, str) or not _SEMVER.fullmatch(value):
        raise SemanticRuntimeContractError(
            f"{label} must use MAJOR.MINOR.PATCH")
    return value


def _digest(label: str, value: str) -> str:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise SemanticRuntimeContractError(
            f"{label} must be a lowercase SHA-256 digest")
    return value


def _names(label: str, values, *, required: bool = False) -> tuple[str, ...]:
    result = tuple(values or ())
    if ((required and not result)
            or len(result) != len(set(result))
            or any(not isinstance(item, str) or not item.strip()
                   for item in result)):
        raise SemanticRuntimeContractError(
            f"{label} must contain unique non-empty strings")
    return result


def _pairs(label: str, values) -> tuple[tuple[str, str], ...]:
    if isinstance(values, Mapping):
        values = tuple(values.items())
    result = tuple(values or ())
    if (len({key for key, _value in result}) != len(result)
            or any(not isinstance(key, str) or not key.strip()
                   or not isinstance(value, str)
                   for key, value in result)):
        raise SemanticRuntimeContractError(
            f"{label} must contain unique string key-value pairs")
    return tuple(sorted(result))


@dataclass(frozen=True)
class SemanticLoopContractDraft:
    """Complete implementation-independent behavior before definition binding."""

    contract_id: str
    version: str
    intent: str
    specification: str
    input_schema_ref: str
    output_schema_ref: str
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    permitted_effects: tuple[str, ...]
    prohibited_effects: tuple[str, ...]
    required_context: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    resolution_policy_ref: str
    interpreter_policy_ref: str
    verification_policy_ref: str
    completion_policy: str
    failure_policy: str
    abstention_policy: str
    execution_record_policy_ref: str
    reliability_budget_ppm: int
    risk_class: str
    supported_modes: tuple[str, ...] = _MODES
    semantic_abi_version: str = "semantic_abi/v1"

    def __post_init__(self) -> None:
        _identifier("contract_id", self.contract_id)
        _version("version", self.version)
        for label in (
                "intent", "specification", "input_schema_ref",
                "output_schema_ref", "resolution_policy_ref",
                "interpreter_policy_ref", "verification_policy_ref",
                "completion_policy", "failure_policy", "abstention_policy",
                "execution_record_policy_ref", "risk_class",
                "semantic_abi_version"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise SemanticRuntimeContractError(f"{label} is required")
        for label in (
                "preconditions", "postconditions", "required_context",
                "evidence_requirements"):
            object.__setattr__(
                self, label, _names(label, getattr(self, label), required=True))
        for label in ("permitted_effects", "prohibited_effects"):
            object.__setattr__(self, label, _names(label, getattr(self, label)))
        if set(self.permitted_effects) & set(self.prohibited_effects):
            raise SemanticRuntimeContractError(
                "an effect cannot be both permitted and prohibited")
        modes = _names("supported_modes", self.supported_modes, required=True)
        if any(mode not in _MODES for mode in modes):
            raise SemanticRuntimeContractError(
                "semantic contract uses an unknown canonical mode")
        object.__setattr__(self, "supported_modes", modes)
        if (not isinstance(self.reliability_budget_ppm, int)
                or isinstance(self.reliability_budget_ppm, bool)
                or not 0 <= self.reliability_budget_ppm <= 1_000_000):
            raise SemanticRuntimeContractError(
                "reliability budget must be integer parts per million")

    def to_dict(self) -> dict:
        return {
            "semantic_abi_version": self.semantic_abi_version,
            "contract_id": self.contract_id, "version": self.version,
            "intent": self.intent, "specification": self.specification,
            "input_schema_ref": self.input_schema_ref,
            "output_schema_ref": self.output_schema_ref,
            "preconditions": list(self.preconditions),
            "postconditions": list(self.postconditions),
            "permitted_effects": list(self.permitted_effects),
            "prohibited_effects": list(self.prohibited_effects),
            "required_context": list(self.required_context),
            "evidence_requirements": list(self.evidence_requirements),
            "resolution_policy_ref": self.resolution_policy_ref,
            "interpreter_policy_ref": self.interpreter_policy_ref,
            "verification_policy_ref": self.verification_policy_ref,
            "completion_policy": self.completion_policy,
            "failure_policy": self.failure_policy,
            "abstention_policy": self.abstention_policy,
            "execution_record_policy_ref": self.execution_record_policy_ref,
            "reliability_budget_ppm": self.reliability_budget_ppm,
            "risk_class": self.risk_class,
            "supported_modes": list(self.supported_modes),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]
                  ) -> "SemanticLoopContractDraft":
        body = dict(value)
        for name in (
                "preconditions", "postconditions", "permitted_effects",
                "prohibited_effects", "required_context",
                "evidence_requirements", "supported_modes"):
            body[name] = tuple(body.get(name) or ())
        return cls(**body)

    @property
    def specification_digest(self) -> str:
        return semantic_digest(self.to_dict())


@dataclass(frozen=True)
class SemanticLoopContract:
    """Semantic contract bound into one exact canonical Loop definition."""

    draft: SemanticLoopContractDraft
    loop_definition_ref: LoopDefinitionRef
    record_type: str = "semantic_loop_contract/v1"

    def __post_init__(self) -> None:
        if (not isinstance(self.draft, SemanticLoopContractDraft)
                or not isinstance(self.loop_definition_ref, LoopDefinitionRef)
                or self.record_type != "semantic_loop_contract/v1"):
            raise SemanticRuntimeContractError(
                "bound semantic contract has an invalid shape")
        if (self.loop_definition_ref.definition_id != self.draft.contract_id
                or self.loop_definition_ref.version != self.draft.version):
            raise SemanticRuntimeContractError(
                "semantic contract and Loop definition identities differ")

    @property
    def contract_digest(self) -> str:
        return semantic_digest(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "draft": self.draft.to_dict(),
            "specification_digest": self.draft.specification_digest,
            "loop_definition_ref": self.loop_definition_ref.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "SemanticLoopContract":
        body = dict(value)
        if set(body) != {
                "record_type", "draft", "specification_digest",
                "loop_definition_ref"}:
            raise SemanticRuntimeContractError(
                "semantic contract record has an invalid shape")
        draft = SemanticLoopContractDraft.from_dict(body["draft"])
        if body["specification_digest"] != draft.specification_digest:
            raise SemanticRuntimeContractError(
                "semantic specification digest does not match")
        return cls(draft, LoopDefinitionRef.from_dict(
            body["loop_definition_ref"]), str(body["record_type"]))


@dataclass(frozen=True)
class SemanticContextItem:
    item_ref: str
    value: object
    provenance: str
    trust_label: str

    def __post_init__(self) -> None:
        if (not self.item_ref.strip() or not self.provenance.strip()
                or self.trust_label not in _TRUST_LABELS):
            raise SemanticRuntimeContractError("semantic context item is invalid")
        canonical_json(self.value)

    def to_dict(self) -> dict:
        return {
            "item_ref": self.item_ref, "value": self.value,
            "value_digest": semantic_digest(self.value),
            "provenance": self.provenance,
            "trust_label": self.trust_label,
        }


@dataclass(frozen=True)
class SemanticContextPack:
    pack_id: str
    assembler_id: str
    assembler_version: str
    policy_digest: str
    items: tuple[SemanticContextItem, ...]
    maximum_bytes: int
    token_estimate: int

    def __post_init__(self) -> None:
        _identifier("pack_id", self.pack_id)
        _identifier("assembler_id", self.assembler_id)
        _version("assembler_version", self.assembler_version)
        _digest("policy_digest", self.policy_digest)
        items = tuple(self.items)
        if (not items or any(not isinstance(item, SemanticContextItem)
                             for item in items)
                or len({item.item_ref for item in items}) != len(items)):
            raise SemanticRuntimeContractError(
                "context pack needs unique typed items")
        object.__setattr__(self, "items", items)
        if (not isinstance(self.maximum_bytes, int) or self.maximum_bytes < 1
                or not isinstance(self.token_estimate, int)
                or self.token_estimate < 0
                or len(canonical_json(self.to_body()).encode("utf-8"))
                > self.maximum_bytes):
            raise SemanticRuntimeContractError(
                "context pack exceeds its explicit size budget")

    def to_body(self) -> dict:
        return {
            "pack_id": self.pack_id, "assembler_id": self.assembler_id,
            "assembler_version": self.assembler_version,
            "policy_digest": self.policy_digest,
            "items": [item.to_dict() for item in self.items],
            "maximum_bytes": self.maximum_bytes,
            "token_estimate": self.token_estimate,
        }

    @property
    def digest(self) -> str:
        return semantic_digest(self.to_body())


@dataclass(frozen=True)
class SemanticInterpreterProfile:
    profile_id: str
    version: str
    provider_id: str
    model_id: str
    runtime_instruction_digest: str
    context_policy_digest: str
    tool_catalog_digest: str
    structured_output_policy_digest: str
    decoding_policy_digest: str
    maximum_model_calls: int
    maximum_total_tokens: int | None

    def __post_init__(self) -> None:
        _identifier("profile_id", self.profile_id)
        _version("version", self.version)
        for label in ("provider_id", "model_id"):
            _identifier(label, getattr(self, label))
        for label in (
                "runtime_instruction_digest", "context_policy_digest",
                "tool_catalog_digest", "structured_output_policy_digest",
                "decoding_policy_digest"):
            _digest(label, getattr(self, label))
        if (not isinstance(self.maximum_model_calls, int)
                or not 1 <= self.maximum_model_calls <= 16
                or self.maximum_total_tokens is not None
                and (not isinstance(self.maximum_total_tokens, int)
                     or self.maximum_total_tokens < 1)):
            raise SemanticRuntimeContractError(
                "semantic interpreter budgets are invalid")

    @property
    def digest(self) -> str:
        return semantic_digest(self.to_dict())

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class SemanticInterpreterQualification:
    qualification_id: str
    contract_digest: str
    interpreter_profile_digest: str
    fixture_population_digest: str
    verifier_profile_digest: str
    producer_id: str
    verifier_id: str
    passed: bool
    evidence_refs: tuple[str, ...]
    predecessor_profile_digest: str = ""
    rollback_profile_digest: str = ""

    def __post_init__(self) -> None:
        _identifier("qualification_id", self.qualification_id)
        for label in (
                "contract_digest", "interpreter_profile_digest",
                "fixture_population_digest", "verifier_profile_digest"):
            _digest(label, getattr(self, label))
        for label in ("predecessor_profile_digest", "rollback_profile_digest"):
            if getattr(self, label):
                _digest(label, getattr(self, label))
        if (not self.producer_id.strip() or not self.verifier_id.strip()
                or self.producer_id.casefold() == self.verifier_id.casefold()
                or not isinstance(self.passed, bool)):
            raise SemanticRuntimeContractError(
                "interpreter qualification needs independent identities")
        object.__setattr__(
            self, "evidence_refs",
            _names("evidence_refs", self.evidence_refs, required=True))

    @property
    def digest(self) -> str:
        return semantic_digest({
            **self.__dict__, "evidence_refs": list(self.evidence_refs)})


@dataclass(frozen=True)
class SemanticRealizationBinding:
    binding_id: str
    version: str
    contract_digest: str
    realization_kind: SemanticRealizationKind
    run_mode: str
    lifecycle: str
    qualification_digest: str
    interpreter_profile_digest: str = ""
    artifact_ref: str = ""
    artifact_digest: str = ""
    coverage_regions: tuple[str, ...] = ()
    unsupported_regions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier("binding_id", self.binding_id)
        _version("version", self.version)
        _digest("contract_digest", self.contract_digest)
        _digest("qualification_digest", self.qualification_digest)
        if (not isinstance(self.realization_kind, SemanticRealizationKind)
                or self.run_mode not in _MODES
                or self.lifecycle not in (
                    "candidate", "validated", "registered", "deprecated",
                    "quarantined", "superseded", "retired")):
            raise SemanticRuntimeContractError(
                "semantic realization classification is invalid")
        if self.interpreter_profile_digest:
            _digest("interpreter_profile_digest",
                    self.interpreter_profile_digest)
        if self.artifact_digest:
            _digest("artifact_digest", self.artifact_digest)
        if self.realization_kind in (
                SemanticRealizationKind.DIRECT_SEMANTIC,
                SemanticRealizationKind.HYBRID_SEMANTIC
                ) and not self.interpreter_profile_digest:
            raise SemanticRuntimeContractError(
                "semantic realization requires an interpreter profile")
        if self.realization_kind is SemanticRealizationKind.DETERMINISTIC_CODE \
                and (not self.artifact_ref or not self.artifact_digest):
            raise SemanticRuntimeContractError(
                "deterministic realization requires exact code identity")
        for label in ("coverage_regions", "unsupported_regions"):
            object.__setattr__(self, label, _names(label, getattr(self, label)))
        if set(self.coverage_regions) & set(self.unsupported_regions):
            raise SemanticRuntimeContractError(
                "coverage and unsupported regions cannot overlap")

    @property
    def digest(self) -> str:
        return semantic_digest({
            **self.__dict__,
            "realization_kind": self.realization_kind.value,
            "coverage_regions": list(self.coverage_regions),
            "unsupported_regions": list(self.unsupported_regions),
        })


@dataclass(frozen=True)
class TrustedStateSnapshot:
    state_id: str
    version: int
    values: tuple[tuple[str, str], ...]
    committed_idempotency: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _identifier("state_id", self.state_id)
        if not isinstance(self.version, int) or self.version < 0:
            raise SemanticRuntimeContractError("state version is invalid")
        object.__setattr__(self, "values", _pairs("values", self.values))
        object.__setattr__(
            self, "committed_idempotency",
            _pairs("committed_idempotency", self.committed_idempotency))

    @property
    def digest(self) -> str:
        return semantic_digest({
            "state_id": self.state_id, "version": self.version,
            "values": dict(self.values),
            "committed_idempotency": dict(self.committed_idempotency),
        })


@dataclass(frozen=True)
class ProposedStateDelta:
    base_state_id: str
    base_state_version: int
    writes: tuple[tuple[str, str], ...]
    declared_effects: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    idempotency_key: str

    def __post_init__(self) -> None:
        _identifier("base_state_id", self.base_state_id)
        _identifier("idempotency_key", self.idempotency_key)
        if not isinstance(self.base_state_version, int) \
                or self.base_state_version < 0:
            raise SemanticRuntimeContractError(
                "delta base state version is invalid")
        object.__setattr__(self, "writes", _pairs("writes", self.writes))
        for label in ("declared_effects", "evidence_refs"):
            object.__setattr__(self, label, _names(label, getattr(self, label)))

    @property
    def digest(self) -> str:
        return semantic_digest({
            "base_state_id": self.base_state_id,
            "base_state_version": self.base_state_version,
            "writes": dict(self.writes),
            "declared_effects": list(self.declared_effects),
            "evidence_refs": list(self.evidence_refs),
            "idempotency_key": self.idempotency_key,
        })


@dataclass(frozen=True)
class SemanticCandidateOutput:
    candidate_id: str
    contract_digest: str
    realization_binding_digest: str
    output_json: str
    proposed_delta: ProposedStateDelta
    evidence_refs: tuple[str, ...]
    model_calls: int

    def __post_init__(self) -> None:
        _identifier("candidate_id", self.candidate_id)
        _digest("contract_digest", self.contract_digest)
        _digest("realization_binding_digest", self.realization_binding_digest)
        try:
            value = json.loads(self.output_json)
        except (TypeError, ValueError) as exc:
            raise SemanticRuntimeContractError(
                "candidate output must be canonical JSON") from exc
        object.__setattr__(self, "output_json", canonical_json(value))
        if not isinstance(self.proposed_delta, ProposedStateDelta):
            raise SemanticRuntimeContractError(
                "candidate needs a ProposedStateDelta")
        object.__setattr__(
            self, "evidence_refs", _names("evidence_refs", self.evidence_refs))
        if not isinstance(self.model_calls, int) or self.model_calls < 0:
            raise SemanticRuntimeContractError("candidate model calls are invalid")

    @property
    def output(self) -> object:
        return json.loads(self.output_json)

    @property
    def digest(self) -> str:
        return semantic_digest({
            "candidate_id": self.candidate_id,
            "contract_digest": self.contract_digest,
            "realization_binding_digest": self.realization_binding_digest,
            "output": self.output,
            "proposed_delta_digest": self.proposed_delta.digest,
            "evidence_refs": list(self.evidence_refs),
            "model_calls": self.model_calls,
        })


@dataclass(frozen=True)
class SemanticVerificationRecord:
    verification_id: str
    candidate_digest: str
    verifier_id: str
    verifier_version: str
    structurally_valid: bool
    contract_valid: bool
    evidence_valid: bool
    postconditions_valid: bool
    accepted: bool
    abstained: bool
    reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    _authority_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        _identifier("verification_id", self.verification_id)
        _digest("candidate_digest", self.candidate_digest)
        _identifier("verifier_id", self.verifier_id)
        _version("verifier_version", self.verifier_version)
        if any(not isinstance(value, bool) for value in (
                self.structurally_valid, self.contract_valid,
                self.evidence_valid, self.postconditions_valid,
                self.accepted, self.abstained)):
            raise SemanticRuntimeContractError(
                "semantic verification flags must be boolean")
        if self.accepted and self.abstained:
            raise SemanticRuntimeContractError(
                "verification cannot both accept and abstain")
        if self.accepted and not all((
                self.structurally_valid, self.contract_valid,
                self.evidence_valid, self.postconditions_valid)):
            raise SemanticRuntimeContractError(
                "accepted verification requires every public check")
        for label in ("reasons", "evidence_refs"):
            object.__setattr__(self, label, _names(label, getattr(self, label)))

    @property
    def digest(self) -> str:
        return semantic_digest(self.to_dict())

    def to_dict(self) -> dict:
        return {
            key: (list(value) if isinstance(value, tuple) else value)
            for key, value in self.__dict__.items()
            if key != "_authority_token"
        }


@dataclass(frozen=True)
class SemanticEffectAuthorization:
    authorization_id: str
    candidate_digest: str
    delta_digest: str
    controller_id: str
    allowed: bool
    effect_record_refs: tuple[str, ...]
    reasons: tuple[str, ...]
    _authority_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        _identifier("authorization_id", self.authorization_id)
        _digest("candidate_digest", self.candidate_digest)
        _digest("delta_digest", self.delta_digest)
        _identifier("controller_id", self.controller_id)
        if not isinstance(self.allowed, bool):
            raise SemanticRuntimeContractError("effect authorization is invalid")
        for label in ("effect_record_refs", "reasons"):
            object.__setattr__(self, label, _names(label, getattr(self, label)))

    @property
    def digest(self) -> str:
        return semantic_digest({
            key: (list(value) if isinstance(value, tuple) else value)
            for key, value in self.__dict__.items()
            if key != "_authority_token"
        })


@dataclass(frozen=True)
class CommittedSemanticResult:
    commit_id: str
    candidate_digest: str
    verification_digest: str
    authorization_digest: str
    state_before: TrustedStateSnapshot
    state_after: TrustedStateSnapshot
    replayed: bool

    def __post_init__(self) -> None:
        _identifier("commit_id", self.commit_id)
        for label in (
                "candidate_digest", "verification_digest",
                "authorization_digest"):
            _digest(label, getattr(self, label))
        if (not isinstance(self.state_before, TrustedStateSnapshot)
                or not isinstance(self.state_after, TrustedStateSnapshot)
                or not isinstance(self.replayed, bool)):
            raise SemanticRuntimeContractError("semantic commit record is invalid")

    @property
    def digest(self) -> str:
        return semantic_digest({
            "commit_id": self.commit_id,
            "candidate_digest": self.candidate_digest,
            "verification_digest": self.verification_digest,
            "authorization_digest": self.authorization_digest,
            "state_before_digest": self.state_before.digest,
            "state_after_digest": self.state_after.digest,
            "replayed": self.replayed,
        })


@dataclass(frozen=True)
class SemanticProgramIdentity:
    contract_digest: str
    loop_definition_digest: str
    realization_binding_digest: str
    interpreter_profile_digest: str
    context_pack_digest: str
    tool_catalog_digest: str
    verification_policy_digest: str
    effect_policy_digest: str

    def __post_init__(self) -> None:
        for label, value in self.__dict__.items():
            _digest(label, value)

    @property
    def program_id(self) -> str:
        return semantic_digest(self.__dict__)

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, value: Mapping[str, object]
                  ) -> "SemanticProgramIdentity":
        return cls(**dict(value))


@dataclass(frozen=True)
class SemanticExecutionRecord:
    execution_record_id: str
    request_id: str
    program: SemanticProgramIdentity
    realization_kind: SemanticRealizationKind
    mode_used: str
    candidate_digest: str
    verification_digest: str
    authorization_digest: str
    committed_result_digest: str
    trust_transitions: tuple[str, ...]
    disposition: SemanticDisposition
    model_calls: int
    prompt_tokens: int | None
    output_tokens: int | None
    cost: float | None
    latency_ms: float
    failure_class: str = ""
    record_type: str = "semantic_execution_record/v1"

    def __post_init__(self) -> None:
        _identifier("execution_record_id", self.execution_record_id)
        _identifier("request_id", self.request_id)
        if self.record_type != "semantic_execution_record/v1":
            raise SemanticRuntimeContractError(
                "semantic execution record type is unsupported")
        if (not isinstance(self.program, SemanticProgramIdentity)
                or not isinstance(self.realization_kind, SemanticRealizationKind)
                or self.mode_used not in _MODES
                or not isinstance(self.disposition, SemanticDisposition)):
            raise SemanticRuntimeContractError("semantic execution_record identity is invalid")
        for label in (
                "candidate_digest", "verification_digest",
                "authorization_digest", "committed_result_digest"):
            value = getattr(self, label)
            if value:
                _digest(label, value)
        object.__setattr__(
            self, "trust_transitions",
            _names("trust_transitions", self.trust_transitions))
        if not isinstance(self.model_calls, int) or self.model_calls < 0:
            raise SemanticRuntimeContractError("execution_record model calls are invalid")
        for value in (self.prompt_tokens, self.output_tokens):
            if value is not None and (not isinstance(value, int) or value < 0):
                raise SemanticRuntimeContractError("execution_record token usage is invalid")
        if not isinstance(self.latency_ms, (int, float)) or self.latency_ms < 0:
            raise SemanticRuntimeContractError("execution_record latency is invalid")

    @property
    def digest(self) -> str:
        return semantic_digest(self.to_dict())

    def to_dict(self) -> dict:
        return {
            **self.__dict__, "program": self.program.to_dict(),
            "realization_kind": self.realization_kind.value,
            "trust_transitions": list(self.trust_transitions),
            "disposition": self.disposition.value,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]
                  ) -> "SemanticExecutionRecord":
        body = dict(value)
        body["program"] = SemanticProgramIdentity.from_dict(body["program"])
        body["realization_kind"] = SemanticRealizationKind(
            body["realization_kind"])
        body["trust_transitions"] = tuple(body.get("trust_transitions") or ())
        body["disposition"] = SemanticDisposition(body["disposition"])
        return cls(**body)


__all__ = (
    "CommittedSemanticResult", "ProposedStateDelta",
    "SemanticCandidateOutput", "SemanticContextItem", "SemanticContextPack",
    "SemanticDisposition", "SemanticEffectAuthorization",
    "SemanticExecutionRecord", "SemanticInterpreterProfile",
    "SemanticInterpreterQualification", "SemanticLoopContract",
    "SemanticLoopContractDraft", "SemanticProgramIdentity",
    "SemanticRealizationBinding", "SemanticRealizationKind",
    "SemanticRuntimeContractError",
    "SemanticVerificationRecord", "TrustedStateSnapshot", "canonical_json",
    "semantic_digest",
)
