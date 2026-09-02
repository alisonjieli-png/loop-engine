"""Bounded assistance stages under the one canonical hybrid run mode.

Profiles are passive policy data. This module runs one structured semantic
operation through ``Loop`` and validates its proposal before trusted use.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from typing import Callable, Mapping

import yaml

from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
from .reusable_capability_records import (
    CapabilityNeed,
    HybridAssistanceProfile,
    HybridAssistanceStage,
    ReusableCapabilityContractError,
)


class HybridAssistanceError(RuntimeError):
    """A bounded model proposal failed its assistance contract."""


@dataclass(frozen=True)
class HybridAssistanceRequest:
    profile: HybridAssistanceProfile
    payload: Mapping[str, object]
    model_call: Callable[[dict], Mapping[str, object]]


@dataclass(frozen=True)
class HybridAssistanceResult:
    profile_ref: str
    stage_outputs: tuple[tuple[str, Mapping[str, object]], ...]
    model_calls: int
    loop_id: str

    def output_for(self, stage: HybridAssistanceStage) -> Mapping[str, object]:
        try:
            return next(value for name, value in self.stage_outputs
                        if name == stage.value)
        except StopIteration as exc:
            raise HybridAssistanceError(
                f"assistance output has no {stage.value} stage") from exc


def load_hybrid_assistance_profiles() \
        -> tuple[HybridAssistanceProfile, ...]:
    """Load the named stage presets from a packaged policy resource."""
    path = files("loop_engine").joinpath(
        "data/reusable_capability_hybrid_profiles.yaml")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict)
            or value.get("record_type") != "hybrid_assistance_profiles/v1"
            or not isinstance(value.get("profiles"), list)):
        raise HybridAssistanceError(
            "hybrid assistance profile resource is malformed")
    profiles = []
    for item in value["profiles"]:
        if not isinstance(item, dict):
            raise HybridAssistanceError(
                "hybrid assistance profile must be an object")
        try:
            profiles.append(HybridAssistanceProfile(
                str(item.get("profile_id") or ""),
                str(item.get("version") or ""),
                tuple(HybridAssistanceStage(stage)
                      for stage in item.get("stages") or ()),
                item.get("maximum_model_calls"),
                item.get("maximum_repair_attempts"),
                item.get("candidate_limit_before_model")))
        except (ValueError, ReusableCapabilityContractError) as exc:
            raise HybridAssistanceError(
                "hybrid assistance profile is invalid") from exc
    if len({item.profile_id for item in profiles}) != len(profiles):
        raise HybridAssistanceError(
            "hybrid assistance profile IDs cannot repeat")
    return tuple(profiles)


def hybrid_assistance_profile(profile_id: str) -> HybridAssistanceProfile:
    try:
        return next(item for item in load_hybrid_assistance_profiles()
                    if item.profile_id == profile_id)
    except StopIteration as exc:
        raise HybridAssistanceError(
            f"hybrid assistance profile {profile_id!r} is not installed") \
            from exc


def run_hybrid_assistance_as_loop(
        request: HybridAssistanceRequest, *, ledger=None, parent=None
        ) -> HybridAssistanceResult:
    """Make one coherent model call and validate every requested stage.

    The model receives a bounded packet, not a catalog or source tree. It may
    propose normalization, selection, adaptation, diagnosis, repair, or
    composition. It cannot make a candidate eligible or mutate trusted state.
    """
    if not isinstance(request, HybridAssistanceRequest):
        raise HybridAssistanceError(
            "hybrid assistance requires its typed request")
    profile = request.profile
    if profile.maximum_model_calls is None:
        raise HybridAssistanceError(
            "hybrid model work requires an explicit call budget")
    if profile.maximum_model_calls < 1:
        raise HybridAssistanceError(
            "hybrid assistance call budget does not permit a model call")
    if not callable(request.model_call):
        raise HybridAssistanceError("hybrid model boundary must be callable")
    if HybridAssistanceStage.CANDIDATE_RERANKING in profile.stages:
        refs = request.payload.get("eligible_candidate_refs")
        limit = profile.candidate_limit_before_model
        if (limit is None or limit < 1 or not isinstance(refs, (list, tuple))
                or not refs or len(refs) > limit
                or len(refs) != len(set(refs))
                or any(not isinstance(item, str) or not item.strip()
                       for item in refs)):
            raise HybridAssistanceError(
                "candidate reranking requires a bounded unique eligible set")
    if HybridAssistanceStage.BOUNDED_REPAIR in profile.stages:
        attempt = request.payload.get("repair_attempt")
        maximum = profile.maximum_repair_attempts
        if (maximum is None or maximum < 1
                or not isinstance(attempt, int) or isinstance(attempt, bool)
                or attempt < 1 or attempt > maximum):
            raise HybridAssistanceError(
                "bounded repair attempt exceeds the profile policy")
    config = LoopConfig(
        framework="custom", custom_steps=("assist",), power="light",
        allowable_modes=("hybrid",), preferred_modes=("hybrid",),
        delegated_modes=("hybrid",), llm_thinking_power="medium",
        exit_condition="accepted_success")
    identity = LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.solver")
    relationship = (LoopRelationship.spawned_by(parent.loop_id)
                    if parent is not None else LoopRelationship.starting())
    loop = (parent.spawn(
        f"bounded hybrid assistance {profile.profile_id}", config,
        identity=identity, relationship=relationship)
        if parent is not None else Loop(
            f"bounded hybrid assistance {profile.profile_id}", config,
            ledger=ledger, identity=identity, relationship=relationship))
    holder: dict[str, object] = {}
    calls = 0

    def handler(_loop, step: str, _context: dict) -> StepOutcome:
        nonlocal calls
        if step != "assist":
            return StepOutcome(
                f"{step}:unexpected", "hybrid", 0.0, failed=True)
        packet = {
            "record_type": "hybrid_assistance_request/v1",
            "profile_id": profile.profile_id,
            "profile_version": profile.version,
            "stages": [stage.value for stage in profile.stages],
            "payload": dict(request.payload),
        }
        calls += 1
        try:
            response = request.model_call(packet)
            if not isinstance(response, Mapping):
                raise HybridAssistanceError(
                    "hybrid model response must be an object")
            if (response.get("profile_id") != profile.profile_id
                    or response.get("profile_version") != profile.version):
                raise HybridAssistanceError(
                    "hybrid response profile identity does not match")
            outputs = response.get("stage_outputs")
            if not isinstance(outputs, Mapping):
                raise HybridAssistanceError(
                    "hybrid response needs stage_outputs")
            expected = {stage.value for stage in profile.stages}
            if set(outputs) != expected or any(
                    not isinstance(outputs[name], Mapping)
                    for name in expected):
                raise HybridAssistanceError(
                    "hybrid response must cover exactly the enabled stages")
            holder["outputs"] = tuple(
                (stage.value, dict(outputs[stage.value]))
                for stage in profile.stages)
            return StepOutcome(
                "assist:structured-proposal", "hybrid", 0.6,
                model_calls=1)
        except Exception as exc:
            holder["error"] = exc
            return StepOutcome(
                f"assist:rejected:{type(exc).__name__}", "hybrid", 0.0,
                model_calls=1, failed=True)

    result = loop.run(handler=handler, max_steps=2)
    if calls > profile.maximum_model_calls:
        raise HybridAssistanceError(
            "hybrid assistance exceeded its model call budget")
    if "error" in holder:
        raise HybridAssistanceError(
            f"hybrid assistance failed inside Loop {result.loop_id}") \
            from holder["error"]
    if result.model_calls != calls:
        raise HybridAssistanceError(
            "hybrid assistance model accounting is inconsistent")
    return HybridAssistanceResult(
        f"{profile.profile_id}@{profile.version}",
        holder["outputs"], calls, result.loop_id)


def normalized_need_from_assistance(
        original: CapabilityNeed,
        result: HybridAssistanceResult,
        allowed_operation_families: tuple[str, ...]) -> CapabilityNeed:
    """Apply a bounded vocabulary proposal without changing hard contracts."""
    output = result.output_for(HybridAssistanceStage.NEED_NORMALIZATION)
    required = {"goal", "operation_family", "semantic_summary", "search_terms"}
    if set(output) != required:
        raise HybridAssistanceError(
            "need normalization output has an invalid shape")
    operation_family = str(output["operation_family"])
    if operation_family not in set(allowed_operation_families):
        raise HybridAssistanceError(
            "normalized operation family is outside the controlled vocabulary")
    terms = output["search_terms"]
    if (not isinstance(terms, (list, tuple))
            or any(not isinstance(item, str) or not item.strip()
                   for item in terms)):
        raise HybridAssistanceError(
            "normalized search terms must be non-empty strings")
    return CapabilityNeed(
        original.need_id, original.originating_run_id,
        original.originating_loop_profile_ref, str(output["goal"]),
        operation_family, str(output["semantic_summary"]),
        original.input_contract_ref, original.input_contract_digest,
        original.output_contract_ref, original.output_contract_digest,
        original.allowed_effects, original.required_capabilities,
        original.prohibited_capabilities,
        original.environment_constraints,
        original.dependency_constraints, original.privacy_scope,
        original.tenant_scope, tuple(terms), original.schema_version)


def selected_candidate_from_assistance(
        result: HybridAssistanceResult,
        eligible_candidate_refs: tuple[str, ...]) -> str:
    """Validate a model comparison against the already eligible set."""
    output = result.output_for(HybridAssistanceStage.CANDIDATE_RERANKING)
    if set(output) != {"selected_capability_ref", "rationale"}:
        raise HybridAssistanceError(
            "candidate reranking output has an invalid shape")
    selected = str(output["selected_capability_ref"])
    if selected not in set(eligible_candidate_refs):
        raise HybridAssistanceError(
            "hybrid reranking cannot resurrect an ineligible capability")
    if not str(output["rationale"]).strip():
        raise HybridAssistanceError(
            "candidate reranking needs an advisory rationale")
    return selected


@dataclass(frozen=True)
class AdapterExecutionRequest:
    adapter: Callable[[object], object]
    inputs: object
    verifier: Callable[[object], bool]


def execute_ephemeral_adapter_as_loop(
        request: AdapterExecutionRequest, *, ledger=None, parent=None) -> dict:
    """Validate and run an ephemeral adapter without promoting it."""
    if (not isinstance(request, AdapterExecutionRequest)
            or not callable(request.adapter)
            or not callable(request.verifier)):
        raise HybridAssistanceError(
            "adapter execution requires callable adapter and verifier")

    def adapt() -> object:
        value = request.adapter(request.inputs)
        if not request.verifier(value):
            raise HybridAssistanceError(
                "ephemeral adapter failed its typed postcondition")
        return value

    from ..loop.encapsulate import as_component_loop
    result = as_component_loop(
        "execute verified ephemeral capability adapter", adapt,
        ledger=ledger, parent=parent)
    if result["model_calls"] != 0:
        raise HybridAssistanceError(
            "ephemeral adapter execution made an unexpected model call")
    return result


__all__ = (
    "AdapterExecutionRequest", "HybridAssistanceError",
    "HybridAssistanceRequest", "HybridAssistanceResult",
    "execute_ephemeral_adapter_as_loop", "hybrid_assistance_profile",
    "load_hybrid_assistance_profiles", "normalized_need_from_assistance",
    "run_hybrid_assistance_as_loop", "selected_candidate_from_assistance",
)
