"""Stage observation and assistance records for the owning Practitioner Loop.

Owns stage fingerprints, exposure records, assistance decisions, and bounded
instrumentation failures. These helpers consume the existing run services;
they do not create another store, runtime, selection policy, or authority.
Callers import these helpers from this owning module.
"""
from __future__ import annotations

import hashlib
import json

from ...loop.kernel_runtime import current_kernel_owner
from ..adaptive_practitioner_validation import AdaptivePractitionerError
from ..convergence import CACHE_ASSIST, experiment_arm
from ..model_demand import ladder_from_observations
from ..solve_control_manifest import ADVISORY_MODE, ASSISTANCE_MODES, SHADOW_MODE
from ..stage_assistance_runtime_records import (
    StageAssistanceRuntimeRecordError, physical_exposure, validate_decision)
from ..stage_fingerprint import SemanticStageFingerprint
from ..stage_store import StageObservation


def _stage_for(services, request) -> SemanticStageFingerprint | None:
    """Name the cognitive situation of one model step.

    Built from what the step already carries — its responsibility, the
    orientation in force, and what remains open — so that naming a stage
    costs nothing and cannot fail a run. A step whose situation cannot be
    described is simply not named.
    """
    try:
        orientation = None
        if services.orientation_by_version:
            orientation = services.orientation_by_version[
                max(services.orientation_by_version)]
        return SemanticStageFingerprint(
            semantic_responsibility=request.objective[:200]
            or request.step_id,
            cognitive_phase=request.step_id,
            ultimate_horizon=getattr(orientation, "ultimate_goal", "")[:200],
            medium_horizon=getattr(orientation, "desired_state", "")[:200],
            near_horizon=getattr(orientation, "immediate_goal", "")[:200],
            micro_horizon=request.objective[:200],
            unknowns=tuple(getattr(orientation, "unknowns", ()) or ())[:8],
            knowns=tuple(getattr(orientation, "knowns", ()) or ())[:8],
            consumer="practitioner",
            task_ref=services.run_id,
            branch_depth=len(services.project_attempts))
    except Exception as exc:                            # noqa: BLE001
        _stage_degraded(
            services, "build_stage_fingerprint", exc,
            procedure_step=str(getattr(request, "step_id", "")))
        return None


def _stage_degraded(services, operation: str, exc: BaseException,
                    **fields) -> None:
    """Keep stage instrumentation failure visible without failing the task."""
    record = {
        "record_type": "stage_evidence_degraded/v1",
        "operation": operation,
        "error_type": type(exc).__name__,
        "error": str(exc)[:300],
        **fields,
    }
    sink = getattr(services, "stage_evidence_degradations", None)
    if isinstance(sink, list):
        sink.append(record)
    try:
        services.diagnostic("stage_evidence_degraded", record)
    except Exception:                                   # noqa: BLE001
        try:
            services.publish(
                "practitioner.diagnostic",
                diagnostic_code="stage_evidence_degraded",
                diagnostic_detail=json.dumps(record, sort_keys=True))
        except Exception:                               # noqa: BLE001
            # The bounded in-memory record above remains readable in the
            # product result even when both event sinks are unavailable.
            return


def _stage_event(services, custom_kind: str, observation, **fields) -> None:
    """Append one exact stage fact to the owning Loop ledger."""
    owner = current_kernel_owner()
    if owner is None:
        raise AdaptivePractitionerError(
            f"{custom_kind} has no active Practitioner Loop owner")
    owner.ledger.record(
        loop_id=owner.loop_id, event="custom", custom_kind=custom_kind,
        stage_occurrence_id=observation.occurrence_id,
        stage_observation_ref=observation.observation_ref,
        semantic_call_id=observation.semantic_call_id,
        owner_loop_id=observation.owner_loop_id,
        semantic_stage_signature=observation.digest,
        pass_number=observation.pass_number,
        **fields)


def _observe_stage(services, stage) -> StageObservation | None:
    """Record this stage, if there is one, and ask what the record advises.

    Returns the observation so its outcome can be graded when this step's
    own result is known, rather than inheriting whatever the run does.

    The advice is written down and not followed. Below the evidence floor
    the ladder declines to advise at all, and even above it the
    recommendation is a hypothesis about a stage shape rather than a fact
    about this stage. Recording it now is what makes checking it possible
    later; acting on it now would make the check impossible, because the
    record would only ever confirm what it already said.
    """
    if not hasattr(stage, "digest"):
        # A situation that could not be described is simply not observed.
        return None
    try:
        prior_status = services.prior_stages.to_dict()
        if (prior_status.get("degraded")
                and not services.prior_stage_degradation_reported):
            services.prior_stage_degradation_reported = True
            _stage_degraded(
                services, "load_prior_stages",
                RuntimeError(str(prior_status.get("last_storage_error")
                                 or "stored stage evidence is degraded")),
                write_failures=prior_status.get("write_failures", 0),
                read_failures=prior_status.get("read_failures", 0),
                unreadable_rows=prior_status.get("unreadable_rows", 0))
        # One occurrence of this region, identified so that independent
        # occurrences can fall on both sides while retries of this one
        # cannot drift between them.
        owner = current_kernel_owner()
        if owner is None:
            raise AdaptivePractitionerError(
                "stage occurrence has no active Practitioner Loop owner")
        material = json.dumps({
            "run_id": services.run_id,
            "owner_loop_id": owner.loop_id,
            "pass_number": int(
                getattr(services, "active_pass_number", 0) or 0),
            "position": len(services.stage_store.observations),
            "semantic_signature": stage.digest,
        }, sort_keys=True, separators=(",", ":"))
        occurrence = "stage-occurrence:sha256:" + hashlib.sha256(
            material.encode("utf-8")).hexdigest()
        semantic_call_id = "semantic-stage-" + hashlib.sha256(
            (occurrence + "\0" + stage.digest).encode("utf-8")
        ).hexdigest()[:48]
        binding = services.request.stage_assistance
        assigned_arm = experiment_arm(CACHE_ASSIST, stage.digest, occurrence)
        priors = []
        typed_candidates = ()
        typed_materials = ()
        retrieval_performed = False
        if binding.mode == ADVISORY_MODE:
            typed_candidates = tuple(
                item for item in binding.candidates
                if item.semantic_signature == stage.digest)
            candidate_refs = {item.candidate_ref for item in typed_candidates}
            typed_materials = tuple(
                item for item in binding.materials
                if item.candidate_ref in candidate_refs
                and item.semantic_signature == stage.digest
            )
            retrieval_performed = True
        elif binding.mode == SHADOW_MODE:
            # What earlier runs did with stages of this shape. Shadow lookups
            # are measured and never added to the prompt.
            for match in services.prior_stages.lookup(
                    stage, exclude_run=services.run_id):
                if match.found_by == "shape":
                    priors = list(match.observations)
                    break
            retrieval_performed = True
        # Fresh performs no stage-prior query. Zero returned after a query is
        # not the same evidence as proving no query occurred.
        ladder = ladder_from_observations(priors)
        prior_refs = (tuple(item.candidate_ref for item in typed_candidates)
                      if typed_candidates else
                      tuple(item.observation_ref for item in priors))
        if binding.mode == SHADOW_MODE and ladder.observations:
            services.stage_ladders[occurrence] = ladder.to_dict()
        exposure_applied = bool(typed_candidates)
        services.stage_arms[occurrence] = {
            "experiment": CACHE_ASSIST,
            "cognitive_phase": stage.cognitive_phase,
            "assigned_arm": (
                binding.mode if binding.mode != SHADOW_MODE else assigned_arm),
            "exposure_applied": exposure_applied,
            "retrieval_performed": retrieval_performed,
            "retrieved_prior_refs": list(prior_refs),
            "exposed_prior_refs": (
                list(prior_refs) if exposure_applied else []),
            "exposed_material_refs": [
                item.material_ref for item in typed_materials
            ],
            "exposed_material_digests": [
                item.content_digest for item in typed_materials
            ],
            "semantic_signature": stage.digest,
            "experiment_ref": binding.experiment_ref,
            "trial_ref": binding.trial_ref,
            "source_state_digest": binding.source_state_digest,
            "control_manifest_ref": (
                binding.control_manifest.manifest_ref
                if binding.control_manifest is not None else ""),
            "control_manifest_digest": (
                binding.control_manifest.content_digest
                if binding.control_manifest is not None else ""),
            "control_set_digest": (
                binding.control_manifest.control_set_digest
                if binding.control_manifest is not None else ""),
            "control_evidence_class": (
                binding.control_manifest.evidence_class
                if binding.control_manifest is not None else "unrecorded"),
        }
        observation = services.stage_store.add(
            stage, run_id=services.run_id,
            occurrence_id=occurrence,
            semantic_call_id=semantic_call_id,
            owner_loop_id=owner.loop_id,
            pass_number=int(getattr(services, "active_pass_number", 0) or 0))
        _stage_event(
            services, "stage_occurrence_opened", observation,
            stage_fingerprint=stage.to_dict())
        _stage_event(
            services, "stage_retrieval_snapshot", observation,
            experiment=CACHE_ASSIST,
            assigned_arm=services.stage_arms[occurrence]["assigned_arm"],
            experiment_ref=binding.experiment_ref,
            trial_ref=binding.trial_ref,
            source_state_digest=binding.source_state_digest,
            control_manifest_ref=services.stage_arms[occurrence][
                "control_manifest_ref"],
            control_manifest_digest=services.stage_arms[occurrence][
                "control_manifest_digest"],
            control_set_digest=services.stage_arms[occurrence][
                "control_set_digest"],
            control_evidence_class=services.stage_arms[occurrence][
                "control_evidence_class"],
            retrieval_performed=retrieval_performed,
            retrieved_prior_refs=prior_refs,
            prior_not_proof=True)
        return observation
    except Exception as exc:                            # noqa: BLE001
        _stage_degraded(
            services, "open_stage_occurrence", exc,
            semantic_signature=str(getattr(stage, "digest", "")))
    return None


def _grade_stage(services, observation, **signals):
    """Record what this step's own result says about the stage.

    Stage-local, and deliberately separate from the run's fate: whether this
    step's answer satisfied its own contract is known here and now, and a
    run that later fails for unrelated reasons does not make it untrue.

    Swallows its own failures. Grading is instrumentation, and instrumentation
    that can end a run changes the thing it is measuring.
    """
    if observation is None:
        return None
    try:
        updated = services.stage_store.observe(observation, **signals)
        services._graded_stage = updated
        _stage_event(
            services, "stage_local_outcome_observed", updated,
            observed_signals=dict(signals),
            outcome=updated.outcome.to_dict())
        return updated
    except Exception as exc:                            # noqa: BLE001
        _stage_degraded(
            services, "record_stage_outcome", exc,
            stage_occurrence_id=str(
                getattr(observation, "occurrence_id", "")),
            observed_signal_names=sorted(signals))
        return observation


def _record_stage_execution(services, observation, results):
    """Join the real gateway results and attempts to the exact stage."""
    if observation is None:
        return None
    try:
        rows = tuple(results or ())
        foreign = sorted({
            str(getattr(item, "semantic_call_id", "") or "")
            for item in rows
            if str(getattr(item, "semantic_call_id", "") or "")
            != observation.semantic_call_id})
        foreign_owners = sorted({
            str(getattr(item, "owner_loop_id", "") or "")
            for item in rows
            if str(getattr(item, "owner_loop_id", "") or "")
            != observation.owner_loop_id})
        physical = tuple(
            attempt for item in rows
            for attempt in tuple(getattr(item, "attempts", ()) or ())
            if str(getattr(attempt, "loop_id", "") or ""))
        attempt_mismatch = any(
            str(getattr(attempt, "semantic_call_id", "") or "")
            != observation.semantic_call_id
            or str(getattr(attempt, "owner_loop_id", "") or "")
            != observation.owner_loop_id
            for attempt in physical)
        if foreign or foreign_owners or attempt_mismatch:
            raise AdaptivePractitionerError(
                "model execution identity differs from its stage occurrence")
        updated = services.stage_store.record_execution(observation, rows)
        services._graded_stage = updated
        _stage_event(
            services, "stage_model_execution_observed", updated,
            gateway_calls=updated.gateway_calls,
            physical_model_calls=updated.model_calls,
            model_route=updated.model_route,
            model_routes=updated.model_routes,
            model_provider=updated.model_provider,
            model_name=updated.model_name,
            model_attempt_loop_ids=updated.model_attempt_loop_ids,
            elapsed_seconds=updated.elapsed_seconds,
            input_tokens=updated.input_tokens,
            output_tokens=updated.output_tokens,
            usage_complete=(updated.input_tokens is not None
                            and updated.output_tokens is not None))
        return updated
    except Exception as exc:                            # noqa: BLE001
        _stage_degraded(
            services, "join_stage_model_execution", exc,
            stage_occurrence_id=str(
                getattr(observation, "occurrence_id", "")))
        return observation


def _observed_response_shape(value: object) -> str:
    """Describe the returned topology, not the input stage shape."""
    if isinstance(value, dict):
        keys = ",".join(sorted(str(key) for key in value)[:32])
        return f"record[{keys}]"
    if isinstance(value, list):
        return "typed_list"
    if isinstance(value, tuple):
        return "tuple"
    if value is None:
        return "none"
    return type(value).__name__


def _record_stage_packet_exposure(
        services, observation, snapshot: dict, blocks, template_candidates,
        *, packet_digest: str, gateway_result, format_attempt: int,
        transport_attempt: int):
    """Record exposure only after an exact physical provider attempt exists."""
    if observation is None:
        return None
    try:
        facts = services.stage_arms[observation.occurrence_id]
        facts.pop("active_exposure", None)
        exposure = physical_exposure(
            observation, snapshot, packet_digest=packet_digest,
            gateway_result=gateway_result, format_attempt=format_attempt,
            transport_attempt=transport_attempt)
        if exposure is None:
            return None
        _stage_event(
            services, "stage_assistance_exposure", observation,
            experiment=CACHE_ASSIST,
            experiment_ref=facts.get("experiment_ref", ""),
            trial_ref=facts.get("trial_ref", ""),
            control_manifest_ref=facts.get("control_manifest_ref", ""),
            control_manifest_digest=facts.get("control_manifest_digest", ""),
            control_set_digest=facts.get("control_set_digest", ""),
            control_evidence_class=facts.get("control_evidence_class", ""),
            assigned_arm=facts.get("assigned_arm", ""),
            exposure_applied=bool(facts.get("exposure_applied")),
            retrieval_performed=bool(facts.get("retrieval_performed")),
            retrieved_prior_refs=tuple(
                facts.get("retrieved_prior_refs", ())),
            exposed_prior_refs=tuple(facts.get("exposed_prior_refs", ())),
            **exposure,
            context_block_ids=tuple(item.block_id for item in blocks),
            baseline_template_ids=tuple(
                str(item.get("template_id") or "")
                for item in template_candidates
                if item.get("template_id")),
            stage_prior_context_present=bool(
                facts.get("exposed_material_refs")),
            stage_prior_prompt_material_present=bool(
                facts.get("exposed_material_refs")),
            exposed_material_refs=tuple(
                facts.get("exposed_material_refs", ())),
            exposed_material_digests=tuple(
                facts.get("exposed_material_digests", ())),
            prior_not_proof=True)
        facts["active_exposure"] = exposure
        return exposure
    except Exception as exc:                            # noqa: BLE001
        _stage_degraded(
            services, "record_stage_exposure", exc,
            stage_occurrence_id=str(
                getattr(observation, "occurrence_id", "")))
        return None


def _record_stage_assistance_decision(
        services, observation, raw_decision: object, *,
        admitted_response_digest: str, admission_loop_id: str,
        semantic_payload_digest: str):
    """Validate and record the model's use or rejection of exposed priors."""
    if observation is None:
        return
    facts = services.stage_arms.get(observation.occurrence_id, {})
    mode = services.request.stage_assistance.mode
    if mode not in ASSISTANCE_MODES:
        return None
    if raw_decision is None:
        try:
            _stage_event(
                services, "stage_assistance_decision_missing", observation,
                experiment_ref=facts.get("experiment_ref", ""),
                trial_ref=facts.get("trial_ref", ""), assigned_arm=mode,
                reason="the active experiment requested a model decision")
        except Exception as exc:                        # noqa: BLE001
            _stage_degraded(
                services, "record_missing_assistance_decision", exc,
                stage_occurrence_id=observation.occurrence_id)
        raise AdaptivePractitionerError(
            "active stage assistance requires an exact model decision")
    try:
        exposure = facts.get("active_exposure")
        validated = validate_decision(
            raw_decision, mode=mode,
            exposed_refs=facts.get("exposed_prior_refs", ()),
            exposure=exposure)
        disposition = validated["disposition"]
        selected = validated["selected_prior_refs"]
        reason = validated["reason"]
        record = {
            "record_type": "stage_assistance_decision_observed/v1",
            "stage_occurrence_id": observation.occurrence_id,
            "experiment_ref": facts.get("experiment_ref", ""),
            "trial_ref": facts.get("trial_ref", ""),
            "control_manifest_ref": facts.get("control_manifest_ref", ""),
            "control_manifest_digest": facts.get(
                "control_manifest_digest", ""),
            "control_set_digest": facts.get("control_set_digest", ""),
            "control_evidence_class": facts.get(
                "control_evidence_class", ""),
            "assigned_arm": mode,
            "exposure_ref": exposure["exposure_ref"],
            "packet_digest": exposure["packet_digest"],
            "prompt_digest": exposure["prompt_digest"],
            "prompt_assembly_id": exposure["prompt_assembly_id"],
            "gateway_request_digest": exposure["gateway_request_digest"],
            "provider_request_digests": list(
                exposure["provider_request_digests"]),
            "physical_attempt_loop_ids": list(
                exposure["physical_attempt_loop_ids"]),
            "admitted_response_digest": admitted_response_digest,
            "admission_loop_id": admission_loop_id,
            "semantic_payload_digest": semantic_payload_digest,
            "disposition": disposition,
            "selected_prior_refs": list(selected),
            "reason": reason[:500],
        }
        services.stage_assistance_decisions.append(record)
        _stage_event(
            services, "stage_assistance_decision", observation,
            **{key: value for key, value in record.items()
               if key not in ("record_type", "stage_occurrence_id")})
        return record
    except Exception as exc:
        try:
            _stage_event(
                services, "stage_assistance_decision_rejected", observation,
                experiment_ref=facts.get("experiment_ref", ""),
                trial_ref=facts.get("trial_ref", ""),
                assigned_arm=mode,
                error_type=type(exc).__name__, error=str(exc)[:300])
        except Exception as event_exc:                  # noqa: BLE001
            _stage_degraded(
                services, "record_rejected_assistance_decision", event_exc,
                stage_occurrence_id=observation.occurrence_id)
        if isinstance(exc, AdaptivePractitionerError):
            raise
        if isinstance(exc, StageAssistanceRuntimeRecordError):
            raise AdaptivePractitionerError(str(exc)) from exc
        raise AdaptivePractitionerError(
            f"stage assistance decision validation failed: {exc}") from exc
