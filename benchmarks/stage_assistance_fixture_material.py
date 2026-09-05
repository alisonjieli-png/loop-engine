"""Hydrated prior material used by the offline stage-assistance fixture.

The body is deliberately generic and cross-task. It supplies a response
program, a context plan, and a verified local outcome without granting
authority or acting as an instruction.
"""

from __future__ import annotations

from loop_engine.core.solve_control_manifest import (
    CONTROL_COMPONENT_IDS,
    ControlComponentRecord,
    PublicSolveControlManifest,
)
from loop_engine.core.stage_assistance_material import (
    StageAssistanceMaterial,
    StageAssistanceMaterialDraft,
)
from loop_engine.core.stage_evidence_records import StageRetrievalCandidate

CONTROL_HISTORY_PROBE = "CONTROL_MANIFEST_PRIOR_TEXT_MUST_NOT_ENTER_PROMPT"


def fixture_control_manifest(
    source_state_digest: str,
) -> PublicSolveControlManifest:
    """Describe why this injected-provider comparison is mechanism-only."""
    unresolved = {
        "runtime_definition": ("dirty_runtime_build_digest",),
        "model_execution": ("arm_specific_injected_response_queue",),
        "execution_environment": ("project_executor_implementation_digest",),
        "evaluation": ("independent_evaluator_identity",),
        "workspace_isolation": ("initial_workspace_content_digest",),
        "observer_sinks": ("progress_callback_implementation_digest",),
    }
    components = tuple(ControlComponentRecord.create(
        name, "unknown" if name in unresolved else "exact",
        {"fixture": "stage_assistance_public_solve/v2", "component": name,
         **({"source_state_digest": source_state_digest}
            if name == "task_and_source" else {}),
         **({"contamination_probe": CONTROL_HISTORY_PROBE}
            if name == "runtime_definition" else {})},
        unresolved.get(name, ())) for name in CONTROL_COMPONENT_IDS)
    blocking = tuple(field for name in CONTROL_COMPONENT_IDS
                     for field in unresolved.get(name, ()))
    return PublicSolveControlManifest(
        "stage-assistance-offline-fixture", "mechanism_only",
        components, blocking)


def fixture_material(
    candidate: StageRetrievalCandidate,
    index: int,
) -> StageAssistanceMaterial:
    return StageAssistanceMaterial.create(
        StageAssistanceMaterialDraft(
            material_ref=f"stage-material:fixture:{index}",
            candidate_ref=candidate.candidate_ref,
            source_occurrence_ref=candidate.source_occurrence_ref,
            semantic_signature=candidate.semantic_signature,
            hydration_level="L2",
            material_kind="response_program_and_context_plan",
            content={
                "source_candidate_ref": candidate.candidate_ref,
                "semantic_stage_signature": candidate.semantic_signature,
                "prior_stage_summary": (
                    "A bounded artifact stage succeeded after preserving an exact "
                    "output contract and independent file verification."
                ),
                "response_program_candidate": {
                    "required_sections": [
                        "candidate action",
                        "expected observation",
                        "verification",
                    ]
                },
                "context_plan_candidate": {
                    "include": ["task contract", "latest state", "artifact checks"],
                    "exclude": ["unrelated parent-task details"],
                },
                "known_local_outcome": "verified",
            },
            source_evidence_refs=(
                "run-history:fixture:prior",
                "stage-outcome:fixture:locally-verified",
            ),
        )
    )


def fixture_lineage_summary(result: dict) -> dict:
    action_links = tuple(result.get("stage_action_links", ()))
    execution_links = tuple(result.get("stage_execution_links", ()))
    outcome_links = tuple(result.get("stage_outcome_links", ()))
    assistance = result.get("intelligence", {}).get("stage_assistance", {})
    exact_chain = bool(
        len(action_links) == len(execution_links) == len(outcome_links) == 1
        and action_links[0].get("action_occurrence_ref")
        == execution_links[0].get("action_occurrence_ref")
        == outcome_links[0].get("action_occurrence_ref")
        and execution_links[0].get("execution_ref")
        == outcome_links[0].get("execution_ref")
        and action_links[0].get("stage_occurrence_id")
        == execution_links[0].get("stage_occurrence_id")
        == outcome_links[0].get("stage_occurrence_id")
        and outcome_links[0].get("verifier_stage_occurrence_id")
        and outcome_links[0].get("verifier_semantic_call_id")
        and outcome_links[0].get("verifier_stage_occurrence_id")
        != outcome_links[0].get("stage_occurrence_id"))
    return {
        "selected_action_link_records": len(action_links),
        "action_execution_link_records": len(execution_links),
        "action_outcome_link_records": len(outcome_links),
        "linked_action_ids": sorted({
            str(item.get("action_id") or "")
            for item in (*action_links, *execution_links, *outcome_links)
            if item.get("action_id")
        }),
        "linked_stage_occurrence_ids": sorted({
            str(item.get("stage_occurrence_id") or "")
            for item in (*action_links, *execution_links, *outcome_links)
            if item.get("stage_occurrence_id")
        }),
        "direct_local_verification_passed": bool(outcome_links)
        and all(item.get("local_verification") is True for item in outcome_links),
        "outcome_attribution_methods": sorted({
            str(item.get("attribution_method") or "")
            for item in outcome_links
            if item.get("attribution_method")
        }),
        "exact_occurrence_chain_complete": exact_chain,
        "attribution_confidence_unknown": bool(outcome_links)
        and all(item.get("attribution_confidence") is None
                for item in outcome_links),
        "control_manifest_ref": assistance.get("control_manifest_ref", ""),
        "control_manifest_digest": assistance.get(
            "control_manifest_digest", ""),
        "control_set_digest": assistance.get("control_set_digest", ""),
        "control_evidence_class": assistance.get(
            "control_evidence_class", "unrecorded"),
        "control_blocking_unknowns": assistance.get(
            "control_blocking_unknowns", []),
    }


def fixture_lineage_is_complete(arm: dict) -> bool:
    return bool(
        arm.get("stage_credit_known") == 1
        and arm.get("selected_action_link_records") == 1
        and arm.get("action_execution_link_records") == 1
        and arm.get("action_outcome_link_records") == 1
        and arm.get("direct_local_verification_passed")
        and arm.get("exact_occurrence_chain_complete")
        and arm.get("attribution_confidence_unknown")
        and arm.get("outcome_attribution_methods")
        == ["DIRECT_LOCAL_VERIFIER"]
    )


__all__ = (
    "CONTROL_HISTORY_PROBE",
    "fixture_control_manifest",
    "fixture_lineage_is_complete",
    "fixture_lineage_summary",
    "fixture_material",
)
