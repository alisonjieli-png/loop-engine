"""Translate one public solve request into the canonical Practitioner request.

This deterministic adapter owns no task semantics and performs no execution.
It keeps active stage experiments free of prior-derived region tuning and
projects inspectable stage evidence back into the public outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.adaptive_practitioner_records import AdaptivePractitionerRequest
from ..core.product_outcome_store import ProductModelCallAccounting


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
        source_refs=request.intake.external_source_refs,
        instruction_provenance=request.intake.instruction_provenance,
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


def model_call_accounting(adaptive: dict) -> ProductModelCallAccounting:
    """Preserve unknown totals; never convert interrupted accounting to zero."""
    if not isinstance(adaptive, dict):
        raise TypeError("model call projection requires an adaptive result mapping")
    total = adaptive.get("model_calls")
    subtotal = adaptive.get("model_calls_known_subtotal")
    if "model_call_accounting_complete" in adaptive:
        complete = adaptive["model_call_accounting_complete"]
    else:
        # Older cancellation records cannot attest that no call was in flight.
        # Retain their declared count only as a subtotal, not a complete total.
        cancelled = any(adaptive.get(name) == "CANCELLED" for name in (
            "failure_code", "terminal_code", "status"))
        complete = total is not None and not cancelled
        if not complete and total is not None:
            if subtotal is not None and subtotal != total:
                raise ValueError("legacy cancelled model call counts contradict their subtotal")
            subtotal, total = total, None
    if complete is True and subtotal is None:
        subtotal = total
    return ProductModelCallAccounting(total, complete, subtotal)


def outcome_model_call_accounting(outcome) -> ProductModelCallAccounting:
    """Normalize constructor defaults, not explicit v5 serialized evidence."""
    from .solve_runtime import SolveError

    complete = (outcome.model_calls is not None
                if outcome.model_call_accounting_complete is None
                else outcome.model_call_accounting_complete)
    subtotal = (outcome.model_calls if complete is True
                and outcome.model_calls_known_subtotal is None
                else outcome.model_calls_known_subtotal)
    try:
        return ProductModelCallAccounting(outcome.model_calls, complete, subtotal)
    except ValueError as exc:
        raise SolveError(str(exc)) from exc


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
    tests.extend(_instruction_adaptation_checks())
    tests.extend(_public_call_accounting_checks())
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "stage_assistance_public_solve_checks/v1",
        "provider_calls": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


def _instruction_adaptation_checks() -> list[dict]:
    """Captured instructions remain model-visible without data-read authority."""
    import hashlib
    import tempfile
    from dataclasses import replace
    from pathlib import Path
    from types import SimpleNamespace

    from ..cli_operations import task_intake_from_args
    from ..core.action_fence import ActionFenceLedger
    from ..core.adaptive_practitioner_prompting import (
        AdaptivePromptAssemblyRequest,
        assemble_work_packet,
    )
    from ..core.adaptive_practitioner_records import AdaptiveRunServices
    from ..core.llm_work_packet import LLMWorkPacket, WorkDirective
    from ..core.practitioner_runtime_facts import runtime_facts
    from ..loop.recursive_loop import Loop
    from ..templates.intake import TaskIntakeRequest, intake_task
    from .solve_runtime import SolveRequest

    with tempfile.TemporaryDirectory(prefix="instruction-adaptation-") as directory:
        path = Path(directory) / "task.txt"
        original_text = "Preserve this captured instruction exactly."
        path.write_text(original_text, encoding="utf-8")
        intake = task_intake_from_args(SimpleNamespace(
            file=str(path), text="", dataset="", repository="", url="", task_pack=""))
        public = SolveRequest(intake)
        request = build_adaptive_request(SolveAdaptationRequest(
            public, "non_deterministic", {}, None))
        original_digest = request.source_state_digest
        path.write_text("different filesystem text", encoding="utf-8")
        services = SimpleNamespace(
            request=request, workspace_base=Path(directory) / "workspace",
            action_fence=ActionFenceLedger(), source_inspections=[])
        facts = runtime_facts(services)
        unchanged_request = build_adaptive_request(SolveAdaptationRequest(
            public, "non_deterministic", {}, None))
        data = SolveRequest(intake_task(TaskIntakeRequest(
            dataset=str(path), goal="Use explicitly supplied data.")))
        data_request = build_adaptive_request(SolveAdaptationRequest(
            data, "non_deterministic", {}, None))
        data_services = SimpleNamespace(request=data_request)
        data_without_grant = not any(item["capability_ref"] == "core.source.inspect"
            for item in AdaptiveRunServices.available_capabilities(data_services))
        data_services.request = replace(data_request, allow_source_materialization_to_model=True)
        data_with_grant = any(item["capability_ref"] == "core.source.inspect"
            for item in AdaptiveRunServices.available_capabilities(data_services))
        owner = Loop("render captured instruction evidence")
        packet = LLMWorkPacket(
            packet_id="packet.instruction", packet_version="1.0.0",
            purpose="inspect_instruction_context", phase="orient_task",
            persona_context={}, task_context={
                "original_input": request.task,
                "source_refs": list(request.source_refs),
                "instruction_provenance": request.instruction_provenance.to_dict()},
            loop_context={"run_id": "instruction-fixture", "loop_id": owner.loop_id},
            context_intelligence=(), question_portfolio={},
            capability_context={"runtime_facts": facts}, attempt_history={},
            work_directive=WorkDirective(
                "orient", "Read the supplied instruction", True, (), (),
                "return a typed observation", "invalid output", "fixture:v1", "return"),
            output_contract={"type": "object"}, policy_context={"permissions": []},
            token_budget={}, source_refs=request.source_refs, context_blocks=())
        prompt = assemble_work_packet(AdaptivePromptAssemblyRequest(
            packet, "fixture.instruction", "canonical"), owner).prompt

    return [{
        "test": "file_adaptation_preserves_text_and_origin_without_unread_data_refs",
        "passed": (request.task == original_text and not request.source_refs
                   and request.instruction_provenance.source_refs == intake.source_refs
                   and request.instruction_provenance.content_digest
                   == hashlib.sha256(original_text.encode()).hexdigest()
                   and not request.allow_source_materialization_to_model
                   and not services.source_inspections
                   and not any(item["capability_ref"] == "core.source.inspect"
                       for item in AdaptiveRunServices.available_capabilities(services))),
    }, {
        "test": "file_mutation_after_intake_does_not_rebind_adaptive_instruction",
        "passed": (unchanged_request.task == original_text
                   and unchanged_request.source_state_digest == original_digest
                   and unchanged_request.instruction_provenance == request.instruction_provenance),
    }, {
        "test": "dataset_references_still_require_the_separate_source_grant",
        "passed": (data_request.source_refs == data.intake.source_refs
                   and data_request.instruction_provenance is None
                   and data_without_grant and data_with_grant),
    }, {
        "test": "rendered_semantic_prompt_states_instruction_capture_not_unread_source",
        "passed": (original_text in prompt
                   and '"text_in_original_input":true' in prompt
                   and '"inspection_required_for_instruction_text":false' in prompt
                   and '"source_refs":[]' in prompt
                   and '"reference_role":"instruction_provenance_not_external_data"' in prompt
                   and '"permissions":[]' in prompt),
    }]


def _public_call_accounting_checks() -> list[dict]:
    """Unknown cancellation totals survive the public path and saved v5 bundle."""
    import tempfile
    from dataclasses import replace
    from pathlib import Path
    from unittest.mock import patch

    from ..core.product_outcome_store import (
        ProductModelCallAccounting,
        _validate_product_outcome,
        load_saved_run_bundle,
    )
    from ..loop.recursive_loop import Loop
    from ..templates.intake import TaskIntakeRequest, intake_task
    from .solution_model_port import (
        FixtureModelExecutionRequest,
        fixture_model_execution,
    )
    from .solve_runtime import SolveOutcome, SolveRequest, solve_task
    from .solve_terminal import SolveTerminalCode, failure_code_for

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    def refused(operation):
        try:
            operation()
        except ValueError:
            return True
        return False

    interrupted = {
        "model_calls": None, "model_call_accounting_complete": False,
        "model_calls_known_subtotal": 44,
    }
    check("an_explicit_failure_code_still_wins_over_layer_inference",
          failure_code_for({"failure_code": "timeout"})
          == SolveTerminalCode.PROVIDER_UNAVAILABLE.value
          and failure_code_for({"failure_code": "CANCELLED"})
          == SolveTerminalCode.CANCELLED.value)
    check("interrupted_accounting_preserves_unknown_total_and_known_44_subtotal",
          model_call_accounting(interrupted).to_dict() == interrupted)
    check("complete_zero_and_positive_call_totals_remain_exact",
          all(model_call_accounting({"model_calls": count}).to_dict() == {
              "model_calls": count, "model_call_accounting_complete": True,
              "model_calls_known_subtotal": count} for count in (0, 44)))
    check("missing_and_legacy_cancelled_accounting_cannot_become_complete_zero",
          model_call_accounting({}).to_dict() == {
              "model_calls": None, "model_call_accounting_complete": False,
              "model_calls_known_subtotal": None}
          and model_call_accounting({"failure_code": "CANCELLED",
                                     "model_calls": 44}).to_dict() == interrupted)
    check("explicit_complete_accounting_is_preserved_on_between_call_cancellation",
          model_call_accounting({
              "failure_code": "CANCELLED", "model_calls": 44,
              "model_call_accounting_complete": True,
              "model_calls_known_subtotal": 44}).model_calls == 44)
    invalid = (
        {"model_calls": True}, {"model_calls": -1}, {"model_calls": "44"},
        {"model_calls": 1.5}, {**interrupted, "model_calls_known_subtotal": True},
        {**interrupted, "model_calls_known_subtotal": -1},
        {**interrupted, "model_call_accounting_complete": "false"},
        {**interrupted, "model_call_accounting_complete": True},
        {**interrupted, "model_calls": 0},
        {"model_calls": 44, "model_call_accounting_complete": True,
         "model_calls_known_subtotal": 43},
    )
    check("invalid_types_negative_counts_and_contradictory_completeness_refuse",
          all(refused(lambda value=value: model_call_accounting(value)) for value in invalid))

    with tempfile.TemporaryDirectory(prefix="public-cancelled-accounting-") as directory:
        run_id = "cancelled-accounting-fixture"
        owner = Loop("offline saved cancellation projection")
        owner.enable_run_history(run_id, root_dir=directory)
        owner.run()
        history_path = str(Path(directory) / run_id)
        adaptive = {
            "run_id": run_id, "solved": False, "failure_code": "CANCELLED",
            "failure": "operator cancellation fixture",
            "deterministic_attempt": {"status": "SKIPPED_LLM_LED"},
            "run_history": {"path": history_path}, "loop_details": [],
            **interrupted,
        }
        model = fixture_model_execution(FixtureModelExecutionRequest(
            answers=("never dispatched",), max_model_calls=1))
        request = SolveRequest(
            intake_task(TaskIntakeRequest(text="Return a typed cancellation.")),
            model_execution=model, runs_dir=directory)
        with patch("loop_engine.code_nodes.solve_runtime.run_adaptive_practitioner",
                   return_value=adaptive):
            outcome = solve_task(request)
        value = outcome.to_dict()
        saved = load_saved_run_bundle(directory, run_id)
        check("public_solve_cancelled_v5_never_coerces_unknown_calls_to_zero",
              value["record_type"] == "solve_outcome/v5"
              and value["terminal_code"] == "CANCELLED"
              and value["model_calls"] is None
              and value["model_call_accounting_complete"] is False
              and value["model_calls_known_subtotal"] == 44)
        check("v5_unknown_accounting_round_trips_in_digest_bound_saved_outcome",
              saved.history.verify_chain()["intact"]
              and saved.outcome_ref.record_type == "solve_outcome/v5"
              and all(saved.outcome[name] == expected
                      for name, expected in interrupted.items()))
        legacy = {**value, "model_calls": 0}
        legacy.pop("model_call_accounting_complete")
        legacy.pop("model_calls_known_subtotal")
        check("legacy_v3_v4_records_remain_readable_without_accounting_rewrite",
              all(_validate_product_outcome({**legacy, "record_type": version}, run_id)
                  == {**legacy, "record_type": version}
                  for version in ("solve_outcome/v3", "solve_outcome/v4")))
        malformed_v5 = [
            {key: item for key, item in value.items() if key != missing}
            for missing in interrupted]
        malformed_v5.extend({**value, **item} for item in invalid)
        check("saved_v5_requires_complete_typed_accounting_fields",
              all(refused(lambda item=item: _validate_product_outcome(item, run_id))
                  for item in malformed_v5))
        check("public_constructor_rejects_inconsistent_accounting_and_defaults_unknown",
              refused(lambda: replace(outcome, model_calls=0))
              and SolveOutcome("unknown", "CANCELLED", False).model_calls is None
              and ProductModelCallAccounting(None, False, 0).model_calls is None)
    return tests


__all__ = (
    "SolveAdaptationRequest",
    "build_adaptive_request",
    "model_call_accounting",
    "outcome_model_call_accounting",
    "stage_assistance_summary",
    "self_test",
)
