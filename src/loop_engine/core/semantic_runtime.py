"""Transactional semantic execution through the canonical Loop runtime.

This module binds a complete semantic contract into ``LoopDefinition`` and
executes one selected realization. Model output remains a candidate until a
spawned verifier Loop, effect controller Loop, and trusted-state commit Loop
admit it. No second runtime or decorator executor is introduced.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Callable, Mapping

from ..loop.encapsulate import as_loop
from ..loop.loop_definition import (
    ConfigurationFacts, LoopDefinition, LoopStartRequest)
from ..loop.loop_profile_catalog import LoopProfileRef
from ..loop.loop_profile_ontology import resolve_profile
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopLedger, StepOutcome
from ..loop.runtime_context import (
    InternalRuntimeBinding, InternalRuntimeMechanics, LoopRuntimeContext)
from .reusable_capability_flywheel import CapabilityAuthority
from .semantic_runtime_records import (
    CommittedSemanticResult,
    ProposedStateDelta,
    SemanticCandidateOutput,
    SemanticContextPack,
    SemanticDisposition,
    SemanticEffectAuthorization,
    SemanticExecutionRecord,
    SemanticInterpreterProfile,
    SemanticInterpreterQualification,
    SemanticLoopContract,
    SemanticLoopContractDraft,
    SemanticProgramIdentity,
    SemanticRealizationBinding,
    SemanticRealizationKind,
    SemanticRuntimeContractError,
    SemanticVerificationRecord,
    canonical_json,
    semantic_digest,
)
from .semantic_state import (
    CatalogTrustedSemanticState, SemanticEffectController,
    SemanticStateError, SemanticVerifier)


class SemanticExecutionError(RuntimeError):
    """A semantic invocation failed safely before trusted commit."""


def bind_semantic_loop_contract(
        draft: SemanticLoopContractDraft,
        definition: LoopDefinition) -> tuple[LoopDefinition, SemanticLoopContract]:
    """Bind one semantic specification digest into an exact Loop definition."""
    if (not isinstance(draft, SemanticLoopContractDraft)
            or not isinstance(definition, LoopDefinition)):
        raise SemanticExecutionError(
            "semantic binding requires typed draft and Loop definition")
    if (definition.definition_id != draft.contract_id
            or definition.version != draft.version
            or not set(draft.supported_modes) <= set(definition.supported_modes)):
        raise SemanticExecutionError(
            "semantic draft is incompatible with the Loop definition")
    facts = definition.configuration_facts.to_dict()
    facts.update({
        "semantic_abi_version": draft.semantic_abi_version,
        "semantic_specification_digest": draft.specification_digest,
    })
    bound_definition = replace(
        definition,
        configuration_facts=ConfigurationFacts.from_mapping(facts))
    contract = SemanticLoopContract(draft, bound_definition.ref)
    return bound_definition, contract


@dataclass(frozen=True)
class SemanticInterpreterResult:
    """Exact provider result from one interpreter call."""

    payload: Mapping[str, object]
    provider_id: str
    model_id: str
    prompt_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = None
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.payload, Mapping):
            raise SemanticExecutionError(
                "semantic interpreter payload must be an object")
        canonical_json(dict(self.payload))
        if not self.provider_id.strip() or not self.model_id.strip():
            raise SemanticExecutionError(
                "semantic interpreter identity is required")
        for value in (self.prompt_tokens, self.output_tokens):
            if value is not None and (not isinstance(value, int) or value < 0):
                raise SemanticExecutionError(
                    "semantic interpreter token usage is invalid")
        if not isinstance(self.latency_ms, (int, float)) or self.latency_ms < 0:
            raise SemanticExecutionError(
                "semantic interpreter latency is invalid")


@dataclass(frozen=True)
class SemanticInterpreterPort:
    """Profile-bound model boundary injected into one semantic execution."""

    profile: SemanticInterpreterProfile
    invoke: Callable[[dict], SemanticInterpreterResult] = field(
        repr=False, compare=False)

    def __post_init__(self) -> None:
        if (not isinstance(self.profile, SemanticInterpreterProfile)
                or not callable(self.invoke)):
            raise SemanticExecutionError(
                "semantic interpreter port configuration is invalid")

    def call(self, packet: dict) -> SemanticInterpreterResult:
        result = self.invoke(packet)
        if (not isinstance(result, SemanticInterpreterResult)
                or result.provider_id != self.profile.provider_id
                or result.model_id != self.profile.model_id):
            raise SemanticExecutionError(
                "semantic interpreter returned another provider or model")
        return result


@dataclass(frozen=True)
class SemanticExecutionRequest:
    request_id: str
    contract: SemanticLoopContract
    definition: LoopDefinition
    binding: SemanticRealizationBinding
    input_value: object
    context_pack: SemanticContextPack
    state_id: str
    idempotency_key: str
    requested_regions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (not self.request_id.strip()
                or not isinstance(self.contract, SemanticLoopContract)
                or not isinstance(self.definition, LoopDefinition)
                or not isinstance(self.binding, SemanticRealizationBinding)
                or not isinstance(self.context_pack, SemanticContextPack)
                or not self.state_id.strip() or not self.idempotency_key.strip()):
            raise SemanticExecutionError(
                "semantic execution request is invalid")
        canonical_json(self.input_value)
        regions = tuple(self.requested_regions)
        if (len(regions) != len(set(regions))
                or any(not isinstance(item, str) or not item.strip()
                       for item in regions)):
            raise SemanticExecutionError(
                "semantic requested regions must be unique strings")
        object.__setattr__(self, "requested_regions", regions)


@dataclass(frozen=True)
class SemanticExecutionServices:
    interpreter_ports: tuple[SemanticInterpreterPort, ...]
    deterministic_executors: tuple[
        tuple[str, Callable[[SemanticExecutionRequest, SemanticContextPack,
                             object], Mapping[str, object]]], ...]
    input_validator: Callable[[object], bool]
    precondition_checker: Callable[
        [SemanticLoopContract, object, SemanticContextPack, object],
        tuple[bool, tuple[str, ...]]]
    verifier: SemanticVerifier
    effect_controller: SemanticEffectController
    state_store: CatalogTrustedSemanticState
    qualifications: tuple[SemanticInterpreterQualification, ...] = ()
    code_authority: CapabilityAuthority | None = None

    def __post_init__(self) -> None:
        ports = tuple(self.interpreter_ports)
        executors = tuple(self.deterministic_executors)
        qualifications = tuple(self.qualifications)
        if (any(not isinstance(item, SemanticInterpreterPort) for item in ports)
                or len({item.profile.digest for item in ports}) != len(ports)
                or any(not isinstance(item, tuple) or len(item) != 2
                       or not isinstance(item[0], str) or not item[0].strip()
                       or not callable(item[1]) for item in executors)
                or len({item[0] for item in executors}) != len(executors)
                or not callable(self.input_validator)
                or not callable(self.precondition_checker)
                or not isinstance(self.verifier, SemanticVerifier)
                or not isinstance(
                    self.effect_controller, SemanticEffectController)
                or not isinstance(
                    self.state_store, CatalogTrustedSemanticState)
                or any(not isinstance(
                    item, SemanticInterpreterQualification)
                    for item in qualifications)
                or self.code_authority is not None
                and not isinstance(self.code_authority, CapabilityAuthority)):
            raise SemanticExecutionError(
                "semantic execution services are invalid")
        object.__setattr__(self, "interpreter_ports", ports)
        object.__setattr__(self, "deterministic_executors", executors)
        object.__setattr__(self, "qualifications", qualifications)

    def interpreter(self, digest: str) -> SemanticInterpreterPort:
        try:
            return next(item for item in self.interpreter_ports
                        if item.profile.digest == digest)
        except StopIteration as exc:
            raise SemanticExecutionError(
                "selected interpreter profile is not installed") from exc

    def deterministic_executor(self, binding_id: str):
        try:
            return dict(self.deterministic_executors)[binding_id]
        except KeyError as exc:
            raise SemanticExecutionError(
                "selected deterministic realization is not installed") from exc


@dataclass(frozen=True)
class SemanticExecutionResult:
    output: object
    candidate: SemanticCandidateOutput | None
    verification: SemanticVerificationRecord | None
    authorization: SemanticEffectAuthorization | None
    committed: CommittedSemanticResult | None
    execution_record: SemanticExecutionRecord
    loop_id: str
    verifier_loop_id: str = ""
    commit_loop_id: str = ""


def select_semantic_realization(
        contract: SemanticLoopContract,
        bindings: tuple[SemanticRealizationBinding, ...],
        qualifications: tuple[SemanticInterpreterQualification, ...],
        requested_regions: tuple[str, ...] = (),
        code_authority: CapabilityAuthority | None = None
        ) -> SemanticRealizationBinding | None:
    """Choose the cheapest hard-eligible realization without model ranking."""
    priorities = {
        SemanticRealizationKind.DETERMINISTIC_CODE: 0,
        SemanticRealizationKind.CACHED_PROCEDURE: 1,
        SemanticRealizationKind.PROMOTED_COMPOSITE: 2,
        SemanticRealizationKind.HYBRID_SEMANTIC: 3,
        SemanticRealizationKind.DIRECT_SEMANTIC: 4,
        SemanticRealizationKind.NOVEL_GENERATION: 5,
        SemanticRealizationKind.HUMAN_AUTHORITY: 6,
    }
    qualification_by_digest = {
        item.digest: item for item in qualifications if item.passed}
    eligible = []
    requested = set(requested_regions)
    for binding in bindings:
        if (binding.contract_digest != contract.contract_digest
                or binding.lifecycle != "registered"
                or binding.run_mode not in contract.draft.supported_modes
                or requested & set(binding.unsupported_regions)
                or binding.coverage_regions
                and not requested <= set(binding.coverage_regions)):
            continue
        if binding.realization_kind in (
                SemanticRealizationKind.DIRECT_SEMANTIC,
                SemanticRealizationKind.HYBRID_SEMANTIC):
            qualification = qualification_by_digest.get(
                binding.qualification_digest)
            if (qualification is None
                    or qualification.contract_digest
                    != contract.contract_digest
                    or qualification.interpreter_profile_digest
                    != binding.interpreter_profile_digest):
                continue
        elif binding.realization_kind is \
                SemanticRealizationKind.DETERMINISTIC_CODE:
            if code_authority is None or not binding.artifact_ref.startswith(
                    "code_asset:"):
                continue
            identity = binding.artifact_ref.removeprefix("code_asset:")
            try:
                asset_id, version = identity.rsplit("@", 1)
                spec = code_authority.active_spec(asset_id, version)
            except Exception:  # noqa: BLE001 - ineligible realization
                continue
            if (spec.body_ref.digest != binding.artifact_digest
                    or spec.qualification_digest
                    != binding.qualification_digest):
                continue
        eligible.append(binding)
    if not eligible:
        return None
    return sorted(eligible, key=lambda item: (
        priorities[item.realization_kind], item.binding_id))[0]


def _program_identity(
        request: SemanticExecutionRequest,
        services: SemanticExecutionServices) -> SemanticProgramIdentity:
    profile_digest = request.binding.interpreter_profile_digest or \
        semantic_digest({"deterministic_artifact": request.binding.artifact_digest})
    tool_digest = (services.interpreter(profile_digest).profile.tool_catalog_digest
                   if request.binding.interpreter_profile_digest
                   else semantic_digest({"tool_catalog": "none"}))
    return SemanticProgramIdentity(
        request.contract.contract_digest,
        request.definition.content_digest,
        request.binding.digest,
        profile_digest,
        request.context_pack.digest,
        tool_digest,
        services.verifier.policy_digest,
        services.effect_controller.policy_digest)


def _parse_candidate(
        raw: Mapping[str, object], request: SemanticExecutionRequest,
        state_snapshot, model_calls: int) -> SemanticCandidateOutput:
    if not isinstance(raw, Mapping) or set(raw) != {
            "output", "proposed_state_delta", "evidence_refs"}:
        raise SemanticExecutionError(
            "semantic realization returned an invalid envelope")
    delta_value = raw["proposed_state_delta"]
    if not isinstance(delta_value, Mapping) or set(delta_value) != {
            "base_state_id", "base_state_version", "writes",
            "declared_effects", "evidence_refs", "idempotency_key"}:
        raise SemanticExecutionError(
            "semantic realization returned an invalid state delta")
    writes = delta_value["writes"]
    if not isinstance(writes, Mapping):
        raise SemanticExecutionError("semantic state writes must be an object")
    delta = ProposedStateDelta(
        str(delta_value["base_state_id"]),
        int(delta_value["base_state_version"]),
        tuple(sorted((str(key), str(value))
                     for key, value in writes.items())),
        tuple(delta_value["declared_effects"] or ()),
        tuple(delta_value["evidence_refs"] or ()),
        str(delta_value["idempotency_key"]))
    if (delta.base_state_id != state_snapshot.state_id
            or delta.idempotency_key != request.idempotency_key):
        raise SemanticExecutionError(
            "semantic realization changed state or idempotency identity")
    identity = semantic_digest({
        "request_id": request.request_id,
        "contract_digest": request.contract.contract_digest,
        "binding_digest": request.binding.digest,
        "output": raw["output"], "delta_digest": delta.digest,
    })[:24]
    return SemanticCandidateOutput(
        "semantic-candidate." + identity,
        request.contract.contract_digest, request.binding.digest,
        canonical_json(raw["output"]), delta,
        tuple(raw["evidence_refs"] or ()), model_calls)


def execute_semantic_loop(
        request: SemanticExecutionRequest,
        services: SemanticExecutionServices, *, ledger=None
        ) -> SemanticExecutionResult:
    """Execute one implementationless or deterministic semantic transaction."""
    if (not isinstance(request, SemanticExecutionRequest)
            or not isinstance(services, SemanticExecutionServices)):
        raise SemanticExecutionError(
            "semantic execution requires typed request and services")
    facts = request.definition.configuration_facts.to_dict()
    if (request.definition.ref != request.contract.loop_definition_ref
            or facts.get("semantic_specification_digest")
            != request.contract.draft.specification_digest
            or request.binding.contract_digest
            != request.contract.contract_digest
            or request.binding.lifecycle != "registered"):
        raise SemanticExecutionError(
            "semantic execution identities are not exactly bound")
    if request.binding.realization_kind in (
            SemanticRealizationKind.DIRECT_SEMANTIC,
            SemanticRealizationKind.HYBRID_SEMANTIC):
        qualification = next((
            item for item in services.qualifications
            if item.digest == request.binding.qualification_digest), None)
        if (qualification is None or not qualification.passed
                or qualification.contract_digest
                != request.contract.contract_digest
                or qualification.interpreter_profile_digest
                != request.binding.interpreter_profile_digest):
            raise SemanticExecutionError(
                "semantic realization lacks exact passed qualification")
    elif request.binding.realization_kind is \
            SemanticRealizationKind.DETERMINISTIC_CODE:
        if (services.code_authority is None
                or not request.binding.artifact_ref.startswith("code_asset:")):
            raise SemanticExecutionError(
                "deterministic realization lacks Code Intelligence authority")
        identity = request.binding.artifact_ref.removeprefix("code_asset:")
        try:
            asset_id, version = identity.rsplit("@", 1)
            active_spec = services.code_authority.active_spec(asset_id, version)
        except Exception as exc:
            raise SemanticExecutionError(
                "deterministic realization authority is unavailable") from exc
        if (active_spec.body_ref.digest != request.binding.artifact_digest
                or active_spec.qualification_digest
                != request.binding.qualification_digest):
            raise SemanticExecutionError(
                "deterministic realization differs from active authority")
    if request.binding.run_mode not in request.definition.installed_executor_modes:
        raise SemanticExecutionError(
            "selected semantic realization has no installed executor")
    program = _program_identity(request, services)
    selected_ledger = ledger or LoopLedger()
    verifier_capabilities = resolve_profile(LoopProfileRef(
        "practitioner.verifier", "1.0.0")).required_capabilities
    runtime_capabilities = tuple(sorted(set(
        request.definition.required_capabilities) | set(
            verifier_capabilities)))
    runtime_context = LoopRuntimeContext(internal=InternalRuntimeMechanics(
        bindings=(InternalRuntimeBinding(
            "semantic-runtime", services,
            runtime_capabilities),),
        permissions=request.definition.permissions,
        executor_modes=request.definition.installed_executor_modes))
    loop = Loop(LoopStartRequest(
        request.contract.draft.intent, request.definition,
        LoopRelationship.starting(), runtime_context, selected_ledger))
    holder: dict[str, object] = {}
    started = time.perf_counter()

    def handler(active: Loop, step: str, _context: dict) -> StepOutcome:
        if step not in active.steps():
            return StepOutcome(
                f"{step}:unexpected", request.binding.run_mode, 0.0,
                failed=True)
        try:
            state_before = services.state_store.snapshot(request.state_id)
            if not services.input_validator(request.input_value):
                raise SemanticExecutionError("input schema validation failed")
            preconditions_ok, precondition_reasons = \
                services.precondition_checker(
                    request.contract, request.input_value,
                    request.context_pack, state_before)
            if not preconditions_ok:
                raise SemanticExecutionError(
                    "preconditions failed: " + "; ".join(
                        precondition_reasons))
            model_calls = 0
            prompt_tokens = output_tokens = None
            cost = None
            interpreter_latency = 0.0
            if request.binding.realization_kind in (
                    SemanticRealizationKind.DIRECT_SEMANTIC,
                    SemanticRealizationKind.HYBRID_SEMANTIC):
                port = services.interpreter(
                    request.binding.interpreter_profile_digest)
                packet = {
                    "record_type": "semantic_interpreter_request/v1",
                    "request_id": request.request_id,
                    "idempotency_key": request.idempotency_key,
                    "program_id": program.program_id,
                    "contract": request.contract.to_dict(),
                    "input": request.input_value,
                    "context": request.context_pack.to_body(),
                    "trusted_state": {
                        "state_id": state_before.state_id,
                        "version": state_before.version,
                        "values": dict(state_before.values),
                        "digest": state_before.digest,
                    },
                    "required_output": {
                        "output_schema_ref":
                            request.contract.draft.output_schema_ref,
                        "proposed_state_delta": True,
                    },
                }
                interpreted = port.call(packet)
                raw = interpreted.payload
                model_calls = 1
                prompt_tokens = interpreted.prompt_tokens
                output_tokens = interpreted.output_tokens
                cost = interpreted.cost
                interpreter_latency = interpreted.latency_ms
            elif request.binding.realization_kind is \
                    SemanticRealizationKind.DETERMINISTIC_CODE:
                raw = services.deterministic_executor(
                    request.binding.binding_id)(
                        request, request.context_pack, state_before)
            else:
                raise SemanticExecutionError(
                    "selected realization kind is not installed in this runtime")
            candidate = _parse_candidate(
                raw, request, state_before, model_calls)
            verifier_run = as_loop(
                "verify semantic candidate against public contract",
                lambda: services.verifier.verify(
                    request.contract, candidate, request.input_value,
                    request.context_pack),
                parent=active,
                identity=LoopRoleIdentity(
                    LoopRole.PRACTITIONER, "practitioner.verifier"),
                relationship=LoopRelationship.spawned_by(active.loop_id))
            verification = verifier_run["value"]
            authorization = None
            committed = None
            commit_loop_id = ""
            transitions = ["candidate"]
            if verification.structurally_valid:
                transitions.append("structurally_valid")
            if verification.contract_valid:
                transitions.append("contract_valid")
            if verification.accepted or verification.abstained:
                transitions.append("verified")
            if verification.accepted:
                authorization_run = as_loop(
                    "authorize semantic candidate effects",
                    lambda: services.effect_controller.authorize(
                        request.contract, candidate), parent=active,
                    identity=LoopRoleIdentity(
                        LoopRole.PRACTITIONER, "practitioner.verifier"),
                    relationship=LoopRelationship.spawned_by(active.loop_id))
                authorization = authorization_run["value"]
                if authorization.allowed:
                    transitions.append("effect_authorized")
                    commit_run = as_loop(
                        "commit verified semantic result",
                        lambda: services.state_store.commit(
                            candidate, verification, authorization,
                            services.verifier, services.effect_controller),
                        parent=active,
                        identity=LoopRoleIdentity(
                            LoopRole.PRACTITIONER, "practitioner.verifier"),
                        relationship=LoopRelationship.spawned_by(active.loop_id))
                    committed = commit_run["value"]
                    commit_loop_id = commit_run["loop_id"]
                    transitions.append("committed")
                    disposition = SemanticDisposition.ACCEPTED
                else:
                    disposition = SemanticDisposition.REJECTED
            elif verification.abstained:
                disposition = SemanticDisposition.ABSTAINED
            else:
                disposition = SemanticDisposition.REJECTED
            elapsed = (time.perf_counter() - started) * 1000.0
            execution_record = SemanticExecutionRecord(
                "semantic-execution-record." + semantic_digest({
                    "request_id": request.request_id,
                    "program_id": program.program_id,
                    "candidate_digest": candidate.digest,
                })[:24],
                request.request_id, program,
                request.binding.realization_kind,
                request.binding.run_mode, candidate.digest,
                verification.digest,
                authorization.digest if authorization else "",
                committed.digest if committed else "",
                tuple(transitions), disposition, model_calls,
                prompt_tokens, output_tokens, cost,
                max(elapsed, interpreter_latency))
            holder.update({
                "output": candidate.output, "candidate": candidate,
                "verification": verification,
                "authorization": authorization, "committed": committed,
                "execution_record": execution_record,
                "verifier_loop_id": verifier_run["loop_id"],
                "commit_loop_id": commit_loop_id,
            })
            return StepOutcome(
                f"semantic:{disposition.value}", request.binding.run_mode,
                0.95, model_calls=model_calls)
        except Exception as exc:  # noqa: BLE001 - safe terminal evidence
            holder["error"] = exc
            return StepOutcome(
                f"semantic:rejected:{type(exc).__name__}",
                request.binding.run_mode, 0.0,
                model_calls=int(holder.get("model_calls", 0)), failed=True)

    loop_result = loop.run(handler=handler, max_steps=2)
    if "execution_record" not in holder:
        elapsed = (time.perf_counter() - started) * 1000.0
        error = holder.get("error")
        execution_record = SemanticExecutionRecord(
            "semantic-execution-record." + semantic_digest({
                "request_id": request.request_id,
                "program_id": program.program_id,
                "failure": type(error).__name__ if error else "unknown",
            })[:24],
            request.request_id, program, request.binding.realization_kind,
            request.binding.run_mode, "", "", "", "", (),
            SemanticDisposition.REJECTED, loop_result.model_calls,
            None, None, None, elapsed,
            type(error).__name__ if error else "UNKNOWN_FAILURE")
        return SemanticExecutionResult(
            None, None, None, None, None, execution_record, loop.loop_id)
    execution_record = holder["execution_record"]
    if execution_record.model_calls != loop_result.model_calls:
        raise SemanticExecutionError(
            "semantic model call accounting is inconsistent")
    return SemanticExecutionResult(
        holder["output"], holder["candidate"], holder["verification"],
        holder["authorization"], holder["committed"], execution_record,
        loop.loop_id, str(holder["verifier_loop_id"]),
        str(holder["commit_loop_id"]))


__all__ = (
    "SemanticExecutionError", "SemanticExecutionRequest",
    "SemanticExecutionResult", "SemanticExecutionServices",
    "SemanticInterpreterPort", "SemanticInterpreterResult",
    "bind_semantic_loop_contract", "execute_semantic_loop",
    "select_semantic_realization",
)
