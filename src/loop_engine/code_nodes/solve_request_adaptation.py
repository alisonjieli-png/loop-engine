"""Translate one public solve request into the canonical Practitioner request.

This deterministic adapter owns no task semantics and performs no execution.
It keeps active stage experiments free of prior-derived region tuning and
projects inspectable stage evidence back into the public outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.adaptive_practitioner_records import AdaptivePractitionerRequest


@dataclass(frozen=True)
class SolveAdaptationRequest:
    solve_request: object
    mode: str
    region_evidence: dict
    tuned_budget: object | None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, str) or not self.mode:
            raise ValueError("solve adaptation mode must be non-empty text")
        if not isinstance(self.region_evidence, dict):
            raise ValueError("solve adaptation region evidence must be a mapping")


def build_adaptive_request(
    specification: SolveAdaptationRequest,
) -> AdaptivePractitionerRequest:
    """Build the exact internal request used by the public solve path."""
    if not isinstance(specification, SolveAdaptationRequest):
        raise ValueError("build_adaptive_request needs SolveAdaptationRequest")
    request = specification.solve_request
    budget = (
        {"context_budget": request.context_budget}
        if request.context_budget is not None
        else {"context_budget": specification.tuned_budget}
        if specification.tuned_budget is not None
        else {}
    )
    return AdaptivePractitionerRequest(
        request.intake.original_input,
        mode=specification.mode,
        runs_dir=request.runs_dir,
        max_passes=request.max_passes,
        interaction_mode=request.interaction_mode.value,
        allow_network_reads=request.allow_network_reads,
        allow_workspace_writes=request.allow_workspace_writes,
        allow_sandbox_commands=request.allow_sandbox_commands,
        source_kind=request.intake.kind,
        source_refs=request.intake.source_refs,
        feedback=request.feedback,
        workspace_root=request.workspace_root,
        allow_source_materialization_to_model=(
            request.allow_source_materialization_to_model
        ),
        persist_run_history=request.save_run_history,
        quiet_model_io=request.quiet_model_io,
        allow_local_execution=request.allow_local_execution,
        prior_region_evidence=specification.region_evidence,
        stage_assistance=request.stage_assistance,
        **budget,
    )


def stage_assistance_summary(solve_request: object, adaptive: dict) -> dict:
    """Project passive stage-assistance evidence into a public result."""
    binding = solve_request.stage_assistance
    control = binding.control_manifest
    recorded = adaptive.get("control_manifest_evidence", {})
    control_recorded = bool(
        control is not None and recorded.get("recorded") is True
        and recorded.get("control_manifest_ref") == control.manifest_ref
        and recorded.get("control_manifest_digest") == control.content_digest
        and recorded.get("control_set_digest") == control.control_set_digest
        and recorded.get("control_evidence_class") == control.evidence_class)
    return {
        "mode": binding.mode,
        "experiment_ref": binding.experiment_ref,
        "trial_ref": binding.trial_ref,
        "source_state_digest": binding.source_state_digest,
        "control_manifest_recorded": control_recorded,
        "control_manifest_ref": (
            control.manifest_ref if control_recorded else ""),
        "control_manifest_digest": (
            control.content_digest if control_recorded else ""),
        "control_set_digest": (
            control.control_set_digest if control_recorded else ""),
        "control_evidence_class": (
            control.evidence_class if control_recorded else "unrecorded"),
        "control_blocking_unknowns": (
            list(control.blocking_unknowns) if control_recorded else []),
        "stage_arms": adaptive.get("stage_arms", {}),
        "decisions": adaptive.get("stage_assistance_decisions", []),
        "action_links": adaptive.get("stage_action_links", []),
        "execution_links": adaptive.get("stage_execution_links", []),
        "outcome_links": adaptive.get("stage_outcome_links", []),
        "stages": adaptive.get("stages", {}),
        "prior_stages_loaded": adaptive.get("prior_stages_loaded", 0),
        "attribution_boundaries": adaptive.get("stage_attribution_events", []),
        "degradations": adaptive.get("stage_evidence_degradations", []),
    }


def self_test() -> dict[str, object]:
    """Prove active experiments cross the public solve boundary fail closed."""
    import tempfile
    from dataclasses import replace
    from unittest.mock import patch

    from ..core.adaptive_practitioner_records import StageAssistanceRuntimeBinding
    from ..core.solve_control_manifest import (
        CONTROL_COMPONENT_IDS,
        ControlComponentRecord,
        PublicSolveControlManifest,
    )
    from ..templates.intake import TaskIntakeRequest, intake_task
    from .solution_model_port import (
        FixtureModelExecutionRequest,
        fixture_model_execution,
    )
    from .solve_runtime import (
        SolveRequest,
        solve_task,
        stage_assistance_source_state_digest,
    )

    model = fixture_model_execution(
        FixtureModelExecutionRequest(answers=("unused",), max_model_calls=1)
    )
    captured = []

    def fake_adaptive(request, _dependencies):
        captured.append(request)
        return {
            "run_id": "public-stage-assistance-fixture",
            "solved": False,
            "failure_code": "NO_VERIFIED_CAPABILITY",
            "deterministic_attempt": {"status": "NO_VERIFIED_CAPABILITY"},
            "run_history": {},
            "loop_details": [],
            "stage_arms": {"occurrence.fixture": {"assigned_arm": "fresh"}},
            "stage_assistance_decisions": [{"disposition": "START_FRESH"}],
            "stages": {"record_type": "stage_store/v1"},
            "prior_stages_loaded": 0,
            "stage_attribution_events": [],
            "stage_evidence_degradations": [],
        }

    def forbidden_region_lookup(_request):
        raise AssertionError("active experiment consulted prior region evidence")

    with tempfile.TemporaryDirectory() as root:
        base = SolveRequest(
            intake_task(TaskIntakeRequest(text="Inspect one bounded task.")),
            model_execution=model,
            runs_dir=root,
        )
        source_digest = stage_assistance_source_state_digest(base)
        def control_manifest(digest):
            return PublicSolveControlManifest(
                "public-solve-adaptation-fixture", "mechanism_only",
                tuple(ControlComponentRecord.create(
                    name, "exact", {"component": name, **({
                        "source_state_digest": digest}
                        if name == "task_and_source" else {})})
                      for name in CONTROL_COMPONENT_IDS))
        fresh = replace(
            base,
            stage_assistance=StageAssistanceRuntimeBinding(
                "fresh",
                "experiment.fixture",
                "trial.fixture",
                source_digest,
                control_manifest=control_manifest(source_digest),
            ),
        )
        with patch(
            "loop_engine.code_nodes.solve_runtime.region_evidence_for_solve",
            side_effect=forbidden_region_lookup,
        ), patch(
            "loop_engine.code_nodes.solve_runtime.run_adaptive_practitioner",
            side_effect=fake_adaptive,
        ):
            outcome = solve_task(fresh)

    def refused(operation) -> bool:
        try:
            operation()
        except (TypeError, ValueError):
            return True
        return False

    tests = [
        {
            "test": "public_solve_passes_the_exact_active_binding",
            "passed": len(captured) == 1
            and captured[0].stage_assistance == fresh.stage_assistance
            and captured[0].prior_region_evidence == {},
        },
        {
            "test": "public_outcome_projects_inspectable_stage_evidence",
            "passed": outcome.intelligence["stage_assistance"]["mode"] == "fresh"
            and outcome.intelligence["stage_assistance"]["decisions"]
            == [{"disposition": "START_FRESH"}]
            and not outcome.intelligence["stage_assistance"][
                "control_manifest_recorded"]
            and outcome.intelligence["stage_assistance"][
                "control_evidence_class"] == "unrecorded"
            and outcome.intelligence["region_evidence"] == {},
        },
        {
            "test": "source_state_digest_is_stable_and_treatment_neutral",
            "passed": source_digest == stage_assistance_source_state_digest(base)
            and source_digest
            == build_adaptive_request(
                SolveAdaptationRequest(fresh, fresh.practitioner_mode, {}, None)
            ).source_state_digest,
        },
        {
            "test": "active_experiment_requires_model_reasoning_and_history",
            "passed": refused(
                lambda: replace(fresh, model_execution=None)
            )
            and refused(lambda: replace(fresh, practitioner_mode="deterministic"))
            and refused(lambda: replace(fresh, save_run_history=False))
            and refused(lambda: replace(
                fresh, stage_assistance=replace(
                    fresh.stage_assistance, control_manifest=None))),
        },
        {
            "test": "wrong_frozen_source_state_is_refused_before_execution",
            "passed": refused(
                lambda: build_adaptive_request(
                    SolveAdaptationRequest(
                        replace(
                            fresh,
                            stage_assistance=StageAssistanceRuntimeBinding(
                                "fresh",
                                "experiment.fixture",
                                "trial.fixture",
                                "f" * 64,
                                control_manifest=control_manifest("f" * 64),
                            ),
                        ),
                        fresh.practitioner_mode,
                        {},
                        None,
                    )
                )
            ),
        },
    ]
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "stage_assistance_public_solve_checks/v1",
        "provider_calls": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = (
    "SolveAdaptationRequest",
    "build_adaptive_request",
    "stage_assistance_summary",
    "self_test",
)
