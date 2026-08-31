"""Typed parameter states, precedence, provenance, and bounded inference.

This module is a passive contract and deterministic resolver. It does not load
configuration, call a provider, or create another settings authority. Owners
provide exact sources. The resolver selects one value and records why.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping

PARAMETER_SCHEMA_VERSION = "parameter_definition/v1"

class ParameterValueState(str, Enum):
    """States that ordinary ``None`` and truth tests cannot distinguish."""

    OMITTED = "OMITTED"
    EXPLICIT_NULL = "EXPLICIT_NULL"
    EMPTY_COLLECTION = "EMPTY_COLLECTION"
    EMPTY_STRING = "EMPTY_STRING"
    FALSE = "FALSE"
    ZERO = "ZERO"
    VALUE = "VALUE"
    RESOLVED_DEFAULT = "RESOLVED_DEFAULT"
    INHERITED_VALUE = "INHERITED_VALUE"

class ParameterSourceKind(str, Enum):
    """Closed precedence vocabulary for one parameter resolution request."""

    EXPLICIT_INVOCATION = "explicit_invocation"
    RUN_OVERRIDE = "run_override"
    LOOP_PROFILE = "loop_profile"
    CAPABILITY_PROFILE = "capability_profile"
    DOMAIN_POLICY = "domain_policy"
    DEPLOYMENT_CONFIGURATION = "deployment_configuration"
    REPOSITORY_DEFAULT = "repository_default"
    DERIVED_VALUE = "derived_value"
    INTELLIGENCE_PROPOSAL = "intelligence_proposal"

SOURCE_PRECEDENCE = {
    ParameterSourceKind.EXPLICIT_INVOCATION: 1,
    ParameterSourceKind.RUN_OVERRIDE: 2,
    ParameterSourceKind.LOOP_PROFILE: 3,
    ParameterSourceKind.CAPABILITY_PROFILE: 4,
    ParameterSourceKind.DOMAIN_POLICY: 5,
    ParameterSourceKind.DEPLOYMENT_CONFIGURATION: 6,
    ParameterSourceKind.REPOSITORY_DEFAULT: 7,
    ParameterSourceKind.DERIVED_VALUE: 8,
    ParameterSourceKind.INTELLIGENCE_PROPOSAL: 9,
}

class ParameterResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    REJECTED = "REJECTED"

class ParameterResolutionError(ValueError):
    """A parameter contract or resolution request is structurally invalid."""

def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str,
        ensure_ascii=False).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class ParameterInput:
    """One tagged parameter input that preserves omission semantics."""

    state: ParameterValueState
    value: Any = None

    def __post_init__(self) -> None:
        state = ParameterValueState(self.state)
        object.__setattr__(self, "state", state)
        valueless = {
            ParameterValueState.OMITTED, ParameterValueState.EXPLICIT_NULL,
        }
        if state in valueless and self.value is not None:
            raise ParameterResolutionError(
                f"{state.value} cannot carry a value")
        if state == ParameterValueState.EMPTY_STRING and self.value != "":
            raise ParameterResolutionError("EMPTY_STRING must carry empty text")
        if state == ParameterValueState.EMPTY_COLLECTION and (
                not isinstance(self.value, (tuple, list, dict, set))
                or bool(self.value)):
            raise ParameterResolutionError(
                "EMPTY_COLLECTION must carry an empty collection")
        if state == ParameterValueState.FALSE and self.value is not False:
            raise ParameterResolutionError("FALSE must carry False")
        if state == ParameterValueState.ZERO and (
                isinstance(self.value, bool) or self.value != 0):
            raise ParameterResolutionError("ZERO must carry numeric zero")
        if state in {
                ParameterValueState.RESOLVED_DEFAULT,
                ParameterValueState.INHERITED_VALUE}:
            raise ParameterResolutionError(
                "resolved-only states cannot be supplied as input")

    @classmethod
    def omitted(cls) -> "ParameterInput":
        return cls(ParameterValueState.OMITTED)

    @classmethod
    def explicit_null(cls) -> "ParameterInput":
        return cls(ParameterValueState.EXPLICIT_NULL)

    @classmethod
    def from_value(cls, value: Any) -> "ParameterInput":
        if value is None:
            return cls.explicit_null()
        if value is False:
            return cls(ParameterValueState.FALSE, False)
        if isinstance(value, (int, float)) and not isinstance(value, bool) \
                and value == 0:
            return cls(ParameterValueState.ZERO, value)
        if value == "":
            return cls(ParameterValueState.EMPTY_STRING, "")
        if isinstance(value, (tuple, list, dict, set)) and not value:
            return cls(ParameterValueState.EMPTY_COLLECTION, value)
        return cls(ParameterValueState.VALUE, value)

    @property
    def material_value(self) -> Any:
        if self.state == ParameterValueState.EXPLICIT_NULL:
            return None
        if self.state == ParameterValueState.OMITTED:
            raise ParameterResolutionError("an omitted input has no value")
        return self.value

@dataclass(frozen=True)
class ParameterDefinition:
    """Versioned semantic owner for one material parameter."""

    parameter_id: str
    semantic_name: str
    description: str
    semantic_type: str
    owner_ref: str
    scope: str
    required: bool = False
    nullable: bool = False
    sensitivity: str = "public"
    override_policy_ref: str = "explicit_or_owned_precedence/v1"
    default_input: ParameterInput = field(
        default_factory=ParameterInput.omitted)
    constraints: Mapping[str, Any] = field(default_factory=dict)
    aliases: tuple[str, ...] = ()
    deprecated_aliases: tuple[str, ...] = ()
    intelligence_allowed: bool = False
    minimum_intelligence_confidence: "float | None" = None
    affects_semantic_identity: bool = True
    affects_qualification: bool = True
    introduced_in_version: str = "1.0.0"
    schema_version: str = PARAMETER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_.-]*", self.parameter_id):
            raise ParameterResolutionError("parameter_id is invalid")
        if self.schema_version != PARAMETER_SCHEMA_VERSION:
            raise ParameterResolutionError("parameter schema version is unsupported")
        if self.semantic_type not in {
                "any", "text", "integer", "number", "boolean",
                "text_sequence", "mapping"}:
            raise ParameterResolutionError("parameter semantic_type is invalid")
        if self.sensitivity not in {"public", "internal", "sensitive"}:
            raise ParameterResolutionError("parameter sensitivity is invalid")
        if not self.owner_ref or not self.scope or not self.description:
            raise ParameterResolutionError("parameter owner and meaning are required")
        if self.required and self.default_input.state != ParameterValueState.OMITTED:
            raise ParameterResolutionError(
                "a required no-default parameter cannot declare a default")
        if (self.minimum_intelligence_confidence is not None
                and not 0.0 <= self.minimum_intelligence_confidence <= 1.0):
            raise ParameterResolutionError(
                "minimum intelligence confidence must be between zero and one")
        if (self.intelligence_allowed
                and self.minimum_intelligence_confidence is None):
            raise ParameterResolutionError(
                "inference-eligible parameter needs an owned confidence policy")
        if (not self.intelligence_allowed
                and self.minimum_intelligence_confidence is not None):
            raise ParameterResolutionError(
                "confidence policy is invalid when intelligence is prohibited")

@dataclass(frozen=True)
class ParameterSource:
    """One exact candidate source considered by the resolver."""

    source_kind: ParameterSourceKind
    source_ref: str
    source_version: str
    input: ParameterInput
    authorized: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_kind",
                           ParameterSourceKind(self.source_kind))
        if not self.source_ref or not self.source_version:
            raise ParameterResolutionError(
                "parameter source needs exact identity and version")

@dataclass(frozen=True)
class ParameterIntelligenceProposal:
    """Untrusted bounded proposal. It never grants its own authority."""

    proposed_input: ParameterInput
    confidence: float
    evidence_refs: tuple[str, ...]
    assumptions: tuple[str, ...]
    unknowns: tuple[str, ...]
    alternatives: tuple[str, ...]
    abstained: bool
    rejection_reason: str
    recommended_validator: str
    intelligence_profile_ref: str
    model_runtime_ref: str
    prompt_bundle_ref: str
    context_digest: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ParameterResolutionError(
                "intelligence confidence must be between zero and one")
        if not all((self.intelligence_profile_ref, self.model_runtime_ref,
                    self.prompt_bundle_ref, self.context_digest,
                    self.recommended_validator)):
            raise ParameterResolutionError(
                "intelligence proposal identity and validator are required")
        if self.abstained and not self.rejection_reason:
            raise ParameterResolutionError(
                "an abstaining proposal needs a reason")

    def to_source(self) -> ParameterSource:
        return ParameterSource(
            ParameterSourceKind.INTELLIGENCE_PROPOSAL,
            self.intelligence_profile_ref,
            self.model_runtime_ref,
            self.proposed_input)

@dataclass(frozen=True)
class ParameterResolutionTrace:
    """One source consultation, including rejection or omission."""

    source_kind: str
    source_ref: str
    source_version: str
    precedence_rank: int
    requested_state: str
    disposition: str
    reason: str

@dataclass(frozen=True)
class ResolvedParameter:
    """Resolved value plus safe provenance and every source considered."""

    parameter_ref: str
    status: ParameterResolutionStatus
    requested_state: ParameterValueState
    resolved_state: ParameterValueState
    value: Any
    resolved_value_digest: "str | None"
    source_kind: "str | None"
    source_ref: "str | None"
    source_version: "str | None"
    precedence_rank: "int | None"
    validation_status: str
    coercions_applied: tuple[str, ...]
    warnings: tuple[str, ...]
    intelligence_invoked: bool
    intelligence_record_ref: "str | None"
    fallback_reason: "str | None"
    resolution_trace: tuple[ParameterResolutionTrace, ...]
    sensitive: bool

    def to_dict(self) -> dict[str, Any]:
        value = "<redacted>" if self.sensitive and self.status \
            == ParameterResolutionStatus.RESOLVED else self.value
        return {
            "record_type": "resolved_parameter/v1",
            "parameter_ref": self.parameter_ref,
            "status": self.status.value,
            "requested_state": self.requested_state.value,
            "resolved_state": self.resolved_state.value,
            "resolved_value": value,
            "resolved_value_digest": self.resolved_value_digest,
            "source_kind": self.source_kind, "source_ref": self.source_ref,
            "source_version": self.source_version,
            "precedence_rank": self.precedence_rank,
            "validation_status": self.validation_status,
            "coercions_applied": list(self.coercions_applied),
            "warnings": list(self.warnings),
            "intelligence_invoked": self.intelligence_invoked,
            "intelligence_record_ref": self.intelligence_record_ref,
            "fallback_reason": self.fallback_reason,
            "resolution_trace": [asdict(item) for item in self.resolution_trace],
        }

@dataclass(frozen=True)
class ParameterResolutionRequest:
    definition: ParameterDefinition
    sources: tuple[ParameterSource, ...]
    intelligence_proposal: "ParameterIntelligenceProposal | None" = None

    def __post_init__(self) -> None:
        kinds = [source.source_kind for source in self.sources]
        if len(kinds) != len(set(kinds)):
            raise ParameterResolutionError(
                "a resolution request may contain one source per scope")

@dataclass(frozen=True)
class LoopConfigResolutionRecord:
    """Safe parameter provenance for one resolved Loop configuration."""

    record_id: str
    definition_ref: str
    parameters: tuple[ResolvedParameter, ...]

    @classmethod
    def from_parameters(
            cls, definition_ref: str,
            parameters: tuple[ResolvedParameter, ...]) \
            -> "LoopConfigResolutionRecord":
        body = [item.to_dict() for item in parameters]
        return cls(
            f"loop_config_resolution.sha256_{_digest(body)}",
            definition_ref, parameters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "loop_config_resolution/v1",
            "record_id": self.record_id,
            "definition_ref": self.definition_ref,
            "parameters": [item.to_dict() for item in self.parameters],
        }

def _validate_value(
        definition: ParameterDefinition, value: Any) -> tuple[bool, str]:
    if value is None:
        return (definition.nullable,
                "valid explicit null" if definition.nullable
                else "parameter is not nullable")
    type_valid = {
        "any": True,
        "text": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "text_sequence": (isinstance(value, (tuple, list))
                          and all(isinstance(item, str) for item in value)),
        "mapping": isinstance(value, Mapping),
    }[definition.semantic_type]
    if not type_valid:
        return False, f"value does not satisfy {definition.semantic_type}"
    constraints = dict(definition.constraints)
    if "allowed_values" in constraints:
        allowed = tuple(constraints["allowed_values"])
        candidates = tuple(value) if definition.semantic_type == "text_sequence" \
            else (value,)
        if any(item not in allowed for item in candidates):
            return False, "value is outside the closed allowed set"
    if constraints.get("non_empty") and not value:
        return False, "value must not be empty"
    if "minimum" in constraints and value < constraints["minimum"]:
        return False, "value is below the declared minimum"
    if "maximum" in constraints and value > constraints["maximum"]:
        return False, "value exceeds the declared maximum"
    return True, "value satisfies type and constraints"

def _requested_state(sources: tuple[ParameterSource, ...]) \
        -> ParameterValueState:
    explicit = next((source for source in sources if source.source_kind in {
        ParameterSourceKind.EXPLICIT_INVOCATION,
        ParameterSourceKind.RUN_OVERRIDE}), None)
    return explicit.input.state if explicit else ParameterValueState.OMITTED

def resolve_parameter(request: ParameterResolutionRequest) -> ResolvedParameter:
    """Resolve one material value with deterministic, visible precedence."""
    definition = request.definition
    sources = list(request.sources)
    if (definition.default_input.state != ParameterValueState.OMITTED
            and not any(source.source_kind
                        == ParameterSourceKind.REPOSITORY_DEFAULT
                        for source in sources)):
        sources.append(ParameterSource(
            ParameterSourceKind.REPOSITORY_DEFAULT,
            definition.owner_ref, definition.introduced_in_version,
            definition.default_input))
    if request.intelligence_proposal is not None:
        sources.append(request.intelligence_proposal.to_source())
    sources.sort(key=lambda source: SOURCE_PRECEDENCE[source.source_kind])
    requested_state = _requested_state(tuple(sources))
    traces = []
    for source in sources:
        rank = SOURCE_PRECEDENCE[source.source_kind]
        if not source.authorized:
            traces.append(ParameterResolutionTrace(
                source.source_kind.value, source.source_ref,
                source.source_version, rank, source.input.state.value,
                "REJECTED", "source lacks authority"))
            continue
        if source.input.state == ParameterValueState.OMITTED:
            traces.append(ParameterResolutionTrace(
                source.source_kind.value, source.source_ref,
                source.source_version, rank, source.input.state.value,
                "OMITTED", "source supplied no value"))
            continue
        if source.source_kind == ParameterSourceKind.INTELLIGENCE_PROPOSAL:
            proposal = request.intelligence_proposal
            if proposal is None or not definition.intelligence_allowed:
                reason = "parameter does not permit intelligence inference"
            elif proposal.abstained:
                reason = proposal.rejection_reason
            elif not proposal.evidence_refs:
                reason = "intelligence proposal has no supporting evidence"
            elif proposal.confidence < (definition.minimum_intelligence_confidence
                                        or 1.0):
                reason = "intelligence proposal is below the owned confidence policy"
            else:
                reason = ""
            if reason:
                traces.append(ParameterResolutionTrace(
                    source.source_kind.value, source.source_ref,
                    source.source_version, rank, source.input.state.value,
                    "REJECTED", reason))
                continue
        value = source.input.material_value
        valid, reason = _validate_value(definition, value)
        if not valid:
            traces.append(ParameterResolutionTrace(
                source.source_kind.value, source.source_ref,
                source.source_version, rank, source.input.state.value,
                "REJECTED", reason))
            if source.source_kind in {
                    ParameterSourceKind.EXPLICIT_INVOCATION,
                    ParameterSourceKind.RUN_OVERRIDE}:
                return ResolvedParameter(
                    definition.parameter_id, ParameterResolutionStatus.REJECTED,
                    requested_state, source.input.state, None, None,
                    source.source_kind.value, source.source_ref,
                    source.source_version, rank, "invalid_explicit_value", (),
                    (reason,), False, None,
                    "invalid explicit value cannot fall back",
                    tuple(traces), definition.sensitivity == "sensitive")
            continue
        traces.append(ParameterResolutionTrace(
            source.source_kind.value, source.source_ref,
            source.source_version, rank, source.input.state.value,
            "SELECTED", reason))
        if source.source_kind == ParameterSourceKind.REPOSITORY_DEFAULT:
            resolved_state = ParameterValueState.RESOLVED_DEFAULT
        elif source.source_kind in {
                ParameterSourceKind.EXPLICIT_INVOCATION,
                ParameterSourceKind.RUN_OVERRIDE}:
            resolved_state = source.input.state
        else:
            resolved_state = ParameterValueState.INHERITED_VALUE
        intelligence = source.source_kind \
            == ParameterSourceKind.INTELLIGENCE_PROPOSAL
        return ResolvedParameter(
            definition.parameter_id, ParameterResolutionStatus.RESOLVED,
            requested_state, resolved_state, value, _digest(value),
            source.source_kind.value, source.source_ref,
            source.source_version, rank, "valid", (), (), intelligence,
            (request.intelligence_proposal.intelligence_profile_ref
             if intelligence and request.intelligence_proposal else None),
            ("higher-precedence sources were omitted or unavailable"
             if rank > 1 else None), tuple(traces),
            definition.sensitivity == "sensitive")
    status = (ParameterResolutionStatus.REJECTED
              if any(trace.disposition == "REJECTED" for trace in traces)
              else ParameterResolutionStatus.UNRESOLVED)
    reason = ("all supplied sources were rejected" if status
              == ParameterResolutionStatus.REJECTED
              else "no source supplied a value")
    return ResolvedParameter(
        definition.parameter_id, status, requested_state,
        ParameterValueState.OMITTED, None, None, None, None, None, None,
        "unresolved", (), (reason,), False, None, reason, tuple(traces),
        definition.sensitivity == "sensitive")

@dataclass(frozen=True)
class ParameterInferenceRequest:
    """Bounded context and admitted candidates for one Intelligence Loop."""

    definition: ParameterDefinition
    allowed_values: tuple[Any, ...]
    context: Mapping[str, Any]
    context_digest: str
    prompt_bundle_ref: str
    intelligence_profile_ref: str = "intelligence.context.frame@1.0.0"
    model_runtime_ref: str = "injected-fixture/v1"
    maximum_model_calls: int = 1

    def __post_init__(self) -> None:
        if not self.definition.intelligence_allowed:
            raise ParameterResolutionError(
                "parameter definition does not permit inference")
        if not self.allowed_values or self.maximum_model_calls != 1:
            raise ParameterResolutionError(
                "bounded inference needs candidates and exactly one call")
        if not self.context_digest or not self.prompt_bundle_ref:
            raise ParameterResolutionError(
                "bounded inference needs exact context and prompt identity")

def run_parameter_inference_as_loop(
        request: ParameterInferenceRequest,
        proposer: Callable[..., ParameterIntelligenceProposal]) \
        -> tuple[ParameterIntelligenceProposal, Mapping[str, Any]]:
    """Run one proposal through a canonical bounded Intelligence Loop."""
    from ..loop.loop_role import (
        LoopRelationship, LoopRole, LoopRoleIdentity)
    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome

    holder: dict[str, Any] = {}
    loop = Loop(
        f"infer eligible parameter {request.definition.parameter_id}",
        LoopConfig(
            framework="custom", custom_steps=("propose", "validate_shape"),
            allowable_modes=("hybrid",), preferred_modes=("hybrid",),
            delegated_modes=("deterministic", "non_deterministic"),
            power="light",
            llm_thinking_power="medium", max_model_calls=1,
            exit_condition="steps_complete"),
        identity=LoopRoleIdentity(
            LoopRole.INTELLIGENCE, "intelligence.context.frame"),
        relationship=LoopRelationship.starting())

    def handler(_active: Loop, step: str, _state: dict) -> StepOutcome:
        if step == "propose":
            import inspect
            packet = {
                "parameter_id": request.definition.parameter_id,
                "semantic_type": request.definition.semantic_type,
                "allowed_values": request.allowed_values,
                "context": dict(request.context),
                "context_digest": request.context_digest,
                "abstention_allowed": True,
            }
            parameters = inspect.signature(proposer).parameters
            proposal = (proposer(packet, _active) if len(parameters) >= 2
                        else proposer(packet))
            if not isinstance(proposal, ParameterIntelligenceProposal):
                return StepOutcome(
                    "proposal has the wrong type", "hybrid", 0.0,
                    failed=True, model_calls=1)
            holder["proposal"] = proposal
            return StepOutcome(
                "bounded parameter proposal returned", "hybrid",
                proposal.confidence, model_calls=1)
        proposal = holder["proposal"]
        candidate = proposal.proposed_input
        valid_shape = proposal.abstained or (
            candidate.state != ParameterValueState.OMITTED
            and candidate.material_value in request.allowed_values)
        return StepOutcome(
            "proposal shape validated" if valid_shape
            else "proposal is outside admitted candidates",
            "hybrid", 1.0 if valid_shape else 0.0,
            failed=not valid_shape)

    result = loop.run(handler=handler, max_steps=3)
    if "proposal" not in holder:
        raise ParameterResolutionError(
            "parameter inference did not produce a typed proposal")
    return holder["proposal"], {
        "record_type": "parameter_inference_run/v1",
        "loop_id": result.loop_id, "runtime_type": "Loop",
        "profile_ref": request.intelligence_profile_ref,
        "selected_mode": "hybrid", "model_call_count": 1,
        "accepted_shape": result.accepted,
        "prompt_bundle_ref": request.prompt_bundle_ref,
        "context_digest": request.context_digest,
    }

def self_test() -> dict[str, Any]:
    """Prove precedence, states, redaction, and bounded intelligence limits."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    definition = ParameterDefinition(
        "test.retry_limit", "retry limit", "bounded retry count", "integer",
        "test.profile@1.0.0", "invocation", nullable=True,
        default_input=ParameterInput.from_value(4),
        constraints={"minimum": 0, "maximum": 20})

    def source(kind: ParameterSourceKind, value: ParameterInput,
               ref: str) -> ParameterSource:
        return ParameterSource(kind, ref, "1.0.0", value)

    resolved = resolve_parameter(ParameterResolutionRequest(
        definition, (
            source(ParameterSourceKind.EXPLICIT_INVOCATION,
                   ParameterInput.from_value(9), "call"),
            source(ParameterSourceKind.LOOP_PROFILE,
                   ParameterInput.from_value(7), "profile"),
            source(ParameterSourceKind.DOMAIN_POLICY,
                   ParameterInput.from_value(6), "policy"),
            source(ParameterSourceKind.DEPLOYMENT_CONFIGURATION,
                   ParameterInput.from_value(5), "deployment"),
        )))
    check("explicit_invocation_wins_owned_precedence",
          resolved.value == 9 and resolved.precedence_rank == 1
          and resolved.requested_state == ParameterValueState.VALUE)
    profile = resolve_parameter(ParameterResolutionRequest(
        definition, (
            source(ParameterSourceKind.EXPLICIT_INVOCATION,
                   ParameterInput.omitted(), "call"),
            source(ParameterSourceKind.LOOP_PROFILE,
                   ParameterInput.from_value(7), "profile"),
            source(ParameterSourceKind.DOMAIN_POLICY,
                   ParameterInput.from_value(6), "policy"),
        )))
    check("profile_wins_after_explicit_omission",
          profile.value == 7
          and profile.source_kind == ParameterSourceKind.LOOP_PROFILE.value)
    domain = resolve_parameter(ParameterResolutionRequest(
        definition, (source(
            ParameterSourceKind.DOMAIN_POLICY,
            ParameterInput.from_value(6), "policy"),)))
    deployment = resolve_parameter(ParameterResolutionRequest(
        definition, (source(
            ParameterSourceKind.DEPLOYMENT_CONFIGURATION,
            ParameterInput.from_value(5), "deployment"),)))
    defaulted = resolve_parameter(ParameterResolutionRequest(definition, ()))
    check("domain_deployment_and_repository_default_are_distinct",
          domain.value == 6 and deployment.value == 5
          and defaulted.value == 4
          and defaulted.resolved_state
          == ParameterValueState.RESOLVED_DEFAULT)
    no_default = ParameterDefinition(
        "test.required", "required", "required input", "text",
        "test.contract@1.0.0", "invocation", required=True)
    unresolved = resolve_parameter(ParameterResolutionRequest(no_default, ()))
    check("required_no_default_remains_unresolved",
          unresolved.status == ParameterResolutionStatus.UNRESOLVED)
    rejected = resolve_parameter(ParameterResolutionRequest(
        definition, (source(
            ParameterSourceKind.EXPLICIT_INVOCATION,
            ParameterInput.from_value(100), "call"),)))
    check("invalid_explicit_value_does_not_fall_back",
          rejected.status == ParameterResolutionStatus.REJECTED
          and rejected.value is None)
    states = {
        ParameterInput.omitted().state,
        ParameterInput.explicit_null().state,
        ParameterInput.from_value(()).state,
        ParameterInput.from_value("").state,
        ParameterInput.from_value(False).state,
        ParameterInput.from_value(0).state,
    }
    check("omitted_null_empty_false_and_zero_are_distinct",
          states == {
              ParameterValueState.OMITTED, ParameterValueState.EXPLICIT_NULL,
              ParameterValueState.EMPTY_COLLECTION,
              ParameterValueState.EMPTY_STRING, ParameterValueState.FALSE,
              ParameterValueState.ZERO})
    nullable = resolve_parameter(ParameterResolutionRequest(
        definition, (source(
            ParameterSourceKind.EXPLICIT_INVOCATION,
            ParameterInput.explicit_null(), "call"),)))
    zero = resolve_parameter(ParameterResolutionRequest(
        definition, (source(
            ParameterSourceKind.EXPLICIT_INVOCATION,
            ParameterInput.from_value(0), "call"),)))
    check("explicit_null_and_zero_resolve_without_conflation",
          nullable.status == ParameterResolutionStatus.RESOLVED
          and nullable.value is None
          and zero.value == 0
          and zero.resolved_state == ParameterValueState.ZERO)
    sensitive_definition = ParameterDefinition(
        "test.secret_ref", "secret ref", "credential handle", "text",
        "test.settings@1.0.0", "deployment", sensitivity="sensitive")
    sensitive = resolve_parameter(ParameterResolutionRequest(
        sensitive_definition, (source(
            ParameterSourceKind.EXPLICIT_INVOCATION,
            ParameterInput.from_value("env:TEST_KEY"), "call"),)))
    check("sensitive_resolution_record_is_redacted_but_digest_bound",
          sensitive.to_dict()["resolved_value"] == "<redacted>"
          and len(sensitive.resolved_value_digest or "") == 64)

    inference_definition = ParameterDefinition(
        "test.selection", "selection", "low-risk admitted selection", "text",
        "test.profile@1.0.0", "invocation", intelligence_allowed=True,
        minimum_intelligence_confidence=0.8,
        constraints={"allowed_values": ("stable", "fast")})
    inference_request = ParameterInferenceRequest(
        inference_definition, ("stable", "fast"),
        {"task_class": "repeatable"}, _digest({"task_class": "repeatable"}),
        "test.parameter_inference@1.0.0")

    def proposer(_packet: Mapping[str, Any]) -> ParameterIntelligenceProposal:
        return ParameterIntelligenceProposal(
            ParameterInput.from_value("stable"), 0.9,
            ("context:task_class",), ("task class is accurate",), (),
            ("fast",), False, "", "closed_candidate_validator/v1",
            "intelligence.context.frame@1.0.0", "fixture-model/v1",
            "test.parameter_inference@1.0.0",
            inference_request.context_digest)

    proposal, inference_run = run_parameter_inference_as_loop(
        inference_request, proposer)
    inferred = resolve_parameter(ParameterResolutionRequest(
        inference_definition, (), proposal))
    check("bounded_intelligence_proposal_runs_as_loop_and_is_validated",
          inference_run["runtime_type"] == "Loop"
          and inference_run["model_call_count"] == 1
          and inferred.value == "stable" and inferred.intelligence_invoked)
    explicit = resolve_parameter(ParameterResolutionRequest(
        inference_definition, (source(
            ParameterSourceKind.EXPLICIT_INVOCATION,
            ParameterInput.from_value("fast"), "call"),), proposal))
    check("intelligence_cannot_override_explicit_value",
          explicit.value == "fast" and not explicit.intelligence_invoked)
    invalid_proposal = ParameterIntelligenceProposal(
        ParameterInput.from_value("unknown"), 0.95, ("context:x",), (), (),
        ("stable",), False, "", "closed_candidate_validator/v1",
        "intelligence.context.frame@1.0.0", "fixture-model/v1",
        "test.parameter_inference@1.0.0", inference_request.context_digest)
    invalid = resolve_parameter(ParameterResolutionRequest(
        inference_definition, (), invalid_proposal))
    low_confidence = resolve_parameter(ParameterResolutionRequest(
        inference_definition, (), ParameterIntelligenceProposal(
            ParameterInput.from_value("stable"), 0.2, ("context:x",), (), (),
            ("fast",), False, "", "closed_candidate_validator/v1",
            "intelligence.context.frame@1.0.0", "fixture-model/v1",
            "test.parameter_inference@1.0.0", inference_request.context_digest)))
    check("invalid_or_low_confidence_intelligence_fails_safely",
          invalid.status == ParameterResolutionStatus.REJECTED
          and low_confidence.status == ParameterResolutionStatus.REJECTED)
    check("deterministic_resolution_uses_zero_intelligence_calls",
          not resolved.intelligence_invoked)
    from .runtime_settings import (
        LoopConfigOverride, RuntimeSettings, SettingsError)
    runtime_settings = RuntimeSettings()
    runtime_config, runtime_record = runtime_settings.loop_config_with_record(
        LoopConfigOverride(
            max_depth=ParameterInput.explicit_null(),
            success_confidence_min=ParameterInput.from_value(0)))
    runtime_parameters = {
        item.parameter_ref: item for item in runtime_record.parameters}
    check("runtime_settings_preserve_explicit_null_and_zero",
          runtime_config.max_depth is None
          and runtime_config.success_confidence_min == 0
          and runtime_parameters["loop.config.max_depth"].requested_state
          == ParameterValueState.EXPLICIT_NULL
          and runtime_parameters[
              "loop.config.success_confidence_min"].requested_state
          == ParameterValueState.ZERO)
    legacy_config, legacy_record = runtime_settings.loop_config_with_record(
        LoopConfigOverride())
    check("legacy_omission_inherits_with_visible_source",
          legacy_config.framework == runtime_settings.loop.framework
          and all(item.source_kind is not None
                  for item in legacy_record.parameters))
    empty_rejected = False
    try:
        runtime_settings.loop_config(LoopConfigOverride(
            allowable_modes=ParameterInput.from_value(())))
    except SettingsError:
        empty_rejected = True
    check("explicit_empty_modes_do_not_silently_inherit", empty_rejected)
    deterministic_config, deterministic_record = \
        runtime_settings.loop_config_with_record(LoopConfigOverride(
            allowable_modes=ParameterInput.from_value(("deterministic",)),
            preferred_modes=ParameterInput.from_value(("deterministic",)),
            delegated_modes=ParameterInput.from_value(("deterministic",))))
    thinking_record = next(
        item for item in deterministic_record.parameters
        if item.parameter_ref == "loop.config.llm_thinking_power")
    check("deterministic_loop_derives_no_model_setting_without_intelligence",
          deterministic_config.llm_thinking_power == ""
          and thinking_record.source_kind
          == ParameterSourceKind.DERIVED_VALUE.value
          and not thinking_record.intelligence_invoked)
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "parameter_resolution_self_test/v1",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }
