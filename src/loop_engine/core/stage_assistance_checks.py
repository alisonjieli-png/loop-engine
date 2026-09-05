"""Adversarial offline checks for stage-assistance evidence.

The fixture uses canonical Run History events and no provider. It proves record
and projection integrity only; it does not claim that an LLM used assistance.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace

from .run_history import RunHistory
from .stage_assistance_experiment import (
    ADVISORY,
    FRESH,
    PairedStageAssistanceTrial,
    StageAssistanceExperimentError,
    StageAssistanceExperimentSpec,
    StageExperimentAssignment,
    StagePacketEvidence,
    assign_paired_trial,
    build_exposure_manifest,
    packet_event_detail,
)
from .stage_evidence_projection import (
    PROJECTION_AUTHORITY,
    SQLiteStageEvidenceProjection,
    StageEvidenceProjectionError,
    projection_event_detail,
)
from .stage_evidence_records import (
    COMBINE,
    STAGE_ASSISTANCE_DISPOSITIONS,
    START_FRESH,
    USE,
    EvidenceNamespace,
    StageAssistanceDecision,
    StageEvidenceContractError,
    StageOccurrenceIdentity,
    StageRetrievalCandidate,
    StageRetrievalSnapshot,
    StageTrialOutcome,
    record_from_dict,
    validate_decision_against_exposure,
)


def _occurrence(namespace: EvidenceNamespace, suffix: str, *, run_id: str,
                state_digest: str = "a" * 64,
                signature: str = "semantic.clean-and-validate/v1",
                shape: str = "shape.tabular-transform/v1",
                call_id: str = "") -> StageOccurrenceIdentity:
    loop_id = f"loop-{suffix}"
    return StageOccurrenceIdentity(
        namespace=namespace, run_id=run_id, loop_id=loop_id,
        activation_id=loop_id,
        semantic_call_id=call_id or f"semantic-call-{suffix}",
        branch_id=f"branch-{suffix}", graph_version="1.0.0",
        source_state_revision=7, source_state_digest=state_digest,
        semantic_signature=signature, shape_signature=shape,
        motif_signatures=("motif.clean-then-verify/v1",))


def _init(history: RunHistory, loop_id: str) -> None:
    history.append("loop_init", loop_id=loop_id,
                   detail={"activation_id": loop_id})


def _model_event(history: RunHistory, occurrence: StageOccurrenceIdentity) -> None:
    model_loop = f"model-{occurrence.semantic_call_id}"
    _init(history, model_loop)
    history.append(
        "model_invocation", loop_id=model_loop,
        spawning_loop_id=occurrence.loop_id,
        detail={"semantic_call_id": occurrence.semantic_call_id,
                "owner_loop_id": occurrence.loop_id})


def _record_event(history: RunHistory, record, loop_id: str):
    return history.append(
        "custom", loop_id=loop_id, detail=projection_event_detail(record))


def _refused(action, error_types=(ValueError,)) -> bool:
    try:
        action()
    except error_types:
        return True
    return False


def self_test() -> dict:
    """Prove source binding, paired isolation, links, and durability."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    run_id = "stage-proof-main"
    namespace = EvidenceNamespace(
        "campaign-proof", "deployment-local", "tenant-a", "workspace-a")
    other_namespace = EvidenceNamespace(
        "campaign-proof", "deployment-local", "tenant-b", "workspace-a")
    first = _occurrence(namespace, "advisory", run_id=run_id)
    second = _occurrence(namespace, "fresh", run_id=run_id)
    repeated = _occurrence(namespace, "advisory", run_id=run_id)

    check("exact_occurrence_identity_is_stable_and_round_trips",
          first == repeated and first.occurrence_ref == repeated.occurrence_ref
          and record_from_dict(first.to_dict()) == first)
    changed_projection = replace(
        first, semantic_signature="semantic.rebuilt/v2",
        shape_signature="shape.rebuilt/v2",
        motif_signatures=("motif.rebuilt/v2",))
    check("similarity_projections_do_not_change_occurrence_identity",
          changed_projection.loop_activation_ref == first.loop_activation_ref
          and changed_projection.semantic_call_ref == first.semantic_call_ref
          and changed_projection.occurrence_ref == first.occurrence_ref
          and changed_projection.content_digest != first.content_digest)
    another_call = replace(first, semantic_call_id="semantic-call-second")
    check("activation_and_semantic_call_identities_are_distinct_scales",
          another_call.loop_activation_ref == first.loop_activation_ref
          and another_call.semantic_call_ref != first.semantic_call_ref
          and first.occurrence_ref == first.semantic_call_ref)
    check("two_branches_share_semantics_but_not_occurrence_identity",
          first.occurrence_ref != second.occurrence_ref
          and first.semantic_signature == second.semantic_signature)
    check("namespace_is_part_of_exact_activation_identity",
          _occurrence(other_namespace, "advisory", run_id=run_id).
          loop_activation_ref != first.loop_activation_ref)
    check("strict_record_reader_rejects_unknown_fields",
          _refused(lambda: record_from_dict(
              {**first.to_dict(), "ambient_authority": True}),
                   (StageEvidenceContractError,)))

    experiment = StageAssistanceExperimentSpec(
        "stage-prior-assistance", "1.0.0", "campaign-seed-17",
        "verification.stage-result/v1")
    trial = PairedStageAssistanceTrial(
        "paired-trial-1", experiment.experiment_ref,
        first.semantic_signature, "a" * 64, (first, second))
    assignments = assign_paired_trial(experiment, trial)
    by_arm = {item.arm: item for item in assignments}
    check("spec_and_trial_have_content_addressed_persistence_refs",
          experiment.record_ref == experiment.experiment_ref
          and trial.record_ref == trial.trial_ref
          and projection_event_detail(experiment)["stage_evidence_record_ref"]
          == experiment.experiment_ref
          and projection_event_detail(trial)["stage_evidence_record_ref"]
          == trial.trial_ref)
    check("paired_assignment_has_one_retry_stable_occurrence_per_arm",
          set(by_arm) == {ADVISORY, FRESH} and len(assignments) == 2
          and assignments == assign_paired_trial(experiment, trial))
    check("paired_trial_rejects_different_source_state_or_shape",
          _refused(lambda: PairedStageAssistanceTrial(
              "bad-state", experiment.experiment_ref,
              first.semantic_signature, "a" * 64,
              (first, _occurrence(namespace, "other", run_id=run_id,
                                  state_digest="b" * 64))))
          and _refused(lambda: PairedStageAssistanceTrial(
              "bad-shape", experiment.experiment_ref,
              first.semantic_signature, "a" * 64,
              (first, replace(second, shape_signature="shape.other/v1")))))
    same_activation = replace(first, semantic_call_id="another-semantic-call")
    check("paired_trial_requires_two_distinct_loop_activations",
          _refused(lambda: PairedStageAssistanceTrial(
              "same-activation", experiment.experiment_ref,
              first.semantic_signature, "a" * 64,
              (first, same_activation))))
    check("paired_trial_requires_one_source_state_revision",
          _refused(lambda: PairedStageAssistanceTrial(
              "different-revision", experiment.experiment_ref,
              first.semantic_signature, "a" * 64,
              (first, replace(second, source_state_revision=8)))))

    advisory_occurrence = next(item for item in (first, second)
                               if item.occurrence_ref
                               == by_arm[ADVISORY].occurrence_ref)
    fresh_occurrence = next(item for item in (first, second)
                            if item.occurrence_ref
                            == by_arm[FRESH].occurrence_ref)
    priors = tuple(_occurrence(namespace, name, run_id=run_id)
                   for name in ("prior-one", "prior-two", "prior-private"))
    candidates = (
        StageRetrievalCandidate(
            "prior-stage.one", priors[0].occurrence_ref,
            first.semantic_signature, "semantic_signature",
            evidence_refs=("run-history:prior-one",),
            material_differences=("different column names",),
            contract_compatible=True, effect_compatible=True,
            authority_compatible=True, privacy_compatible=True,
            outcome_refs=("stage-outcome:prior-one",)),
        StageRetrievalCandidate(
            "prior-stage.two", priors[1].occurrence_ref,
            first.semantic_signature, "motif",
            material_differences=("different storage engine",),
            contract_compatible=True, effect_compatible=None,
            authority_compatible=True, privacy_compatible=True),
        StageRetrievalCandidate(
            "prior-stage.private", priors[2].occurrence_ref,
            first.semantic_signature, "semantic_signature",
            contract_compatible=True, effect_compatible=True,
            authority_compatible=True, privacy_compatible=False),
    )
    snapshot = StageRetrievalSnapshot(
        "snapshot-advisory", advisory_occurrence.occurrence_ref,
        first.semantic_signature, candidates)
    check("snapshot_refuses_a_candidate_from_another_semantic_signature",
          _refused(lambda: StageRetrievalSnapshot(
              "snapshot-mismatch", advisory_occurrence.occurrence_ref,
              first.semantic_signature,
              (replace(candidates[0], candidate_ref="prior-stage.mismatch",
                       semantic_signature="semantic.other/v1"),)),
                   (StageEvidenceContractError,)))
    malformed_sequence = candidates[0].to_dict()
    malformed_sequence["evidence_refs"] = "one-reference"
    check("serialized_string_cannot_become_a_sequence_of_character_refs",
          _refused(lambda: StageRetrievalCandidate.from_dict(
              malformed_sequence), (StageEvidenceContractError,)))

    history = RunHistory(run_id)
    coordinator = "loop-experiment-coordinator"
    evaluator_advisory, evaluator_fresh = "loop-eval-advisory", "loop-eval-fresh"
    occurrences = (*priors, first, second)
    for loop_id in (coordinator, *(item.loop_id for item in occurrences),
                    evaluator_advisory, evaluator_fresh):
        _init(history, loop_id)
    for occurrence in occurrences:
        _model_event(history, occurrence)
    evidence_records = []

    def add(record, loop_id):
        evidence_records.append(record)
        return _record_event(history, record, loop_id)

    add(experiment, coordinator)
    for occurrence in occurrences:
        add(occurrence, occurrence.loop_id)
    add(trial, coordinator)
    add(by_arm[ADVISORY], advisory_occurrence.loop_id)
    add(by_arm[FRESH], fresh_occurrence.loop_id)
    add(snapshot, advisory_occurrence.loop_id)

    exposed = (candidates[0].candidate_ref,)
    advisory_packet_event = history.append(
        "custom", loop_id=advisory_occurrence.loop_id,
        detail=packet_event_detail(
            packet_digest="b" * 64,
            assignment_ref=by_arm[ADVISORY].assignment_ref,
            retrieval_snapshot_ref=snapshot.snapshot_ref,
            exposed_prior_refs=exposed,
            context_block_ids=("task", "stage-prior-assistance")))
    fresh_packet_event = history.append(
        "custom", loop_id=fresh_occurrence.loop_id,
        detail=packet_event_detail(
            packet_digest="c" * 64,
            assignment_ref=by_arm[FRESH].assignment_ref,
            context_block_ids=("task",)))
    advisory_packet = StagePacketEvidence.from_event(advisory_packet_event)
    fresh_packet = StagePacketEvidence.from_event(fresh_packet_event)
    advisory_exposure = build_exposure_manifest(
        by_arm[ADVISORY], snapshot, packet_evidence=advisory_packet)
    fresh_exposure = build_exposure_manifest(
        by_arm[FRESH], packet_evidence=fresh_packet)
    check("default_exposure_includes_only_proven_hard_compatible_priors",
          advisory_exposure.retrieved_prior_refs
          == tuple(item.candidate_ref for item in candidates)
          and advisory_exposure.exposed_prior_refs == exposed)
    check("unknown_or_failed_privacy_cannot_be_explicitly_exposed",
          _refused(lambda: build_exposure_manifest(
              by_arm[ADVISORY], snapshot, packet_evidence=advisory_packet,
              exposed_prior_refs=(candidates[1].candidate_ref,)))
          and _refused(lambda: build_exposure_manifest(
              by_arm[ADVISORY], snapshot, packet_evidence=advisory_packet,
              exposed_prior_refs=(candidates[2].candidate_ref,))))
    check("fresh_exposure_is_bound_to_a_recorded_zero_prior_packet_event",
          fresh_exposure.arm == FRESH
          and not fresh_exposure.retrieval_snapshot_ref
          and not fresh_exposure.exposed_prior_refs
          and fresh_exposure.packet_event_ref == fresh_packet_event.event_digest)
    check("packet_evidence_is_required_and_cannot_be_fabricated_by_builder",
          _refused(lambda: build_exposure_manifest(by_arm[FRESH]), (TypeError,)))
    wrong_policy_event = history.append(
        "custom", loop_id=fresh_occurrence.loop_id,
        detail=packet_event_detail(
            packet_digest="f" * 64,
            assignment_ref=by_arm[FRESH].assignment_ref,
            fresh_policy_id="ambient-history/v1"))
    check("fresh_packet_policy_is_machine_checked_before_manifest_creation",
          _refused(lambda: build_exposure_manifest(
              by_arm[FRESH],
              packet_evidence=StagePacketEvidence.from_event(
                  wrong_policy_event)), (StageAssistanceExperimentError,)))
    add(advisory_exposure, advisory_occurrence.loop_id)
    add(fresh_exposure, fresh_occurrence.loop_id)

    selected = advisory_exposure.exposed_prior_refs
    advisory_decision = StageAssistanceDecision(
        "decision-use", advisory_occurrence.occurrence_ref,
        advisory_exposure.manifest_ref, USE, selected,
        "solver-owned choice")
    validate_decision_against_exposure(advisory_decision, advisory_exposure)
    fresh_decision = StageAssistanceDecision(
        "decision-fresh", fresh_occurrence.occurrence_ref,
        fresh_exposure.manifest_ref, START_FRESH,
        reason="fresh control receives no prior")
    check("decisions_are_explicit_and_exposure_checked",
          validate_decision_against_exposure(
              fresh_decision, fresh_exposure)
          and _refused(lambda: validate_decision_against_exposure(
              StageAssistanceDecision(
                  "bad", advisory_occurrence.occurrence_ref,
                  advisory_exposure.manifest_ref, COMBINE, selected),
              advisory_exposure)))
    check("the_assistance_disposition_vocabulary_is_complete",
          STAGE_ASSISTANCE_DISPOSITIONS == (
              "USE", "MODIFY", "COMBINE", "IGNORE", "RETRIEVE_DEEPER",
              "START_FRESH", "SPAWN_CHALLENGER"))
    check("an_assistance_decision_requires_a_reason",
          _refused(lambda: StageAssistanceDecision(
              "decision-without-reason", advisory_occurrence.occurrence_ref,
              advisory_exposure.manifest_ref, USE, selected)))
    add(advisory_decision, advisory_occurrence.loop_id)
    add(fresh_decision, fresh_occurrence.loop_id)

    metric_ref = "metric.stage-quality@1.0.0#sha256:" + "d" * 64
    def evaluation_detail(quality):
        return {
            "verification_contract_ref": experiment.verification_contract_ref,
            "metric_ref": metric_ref, "metric_direction": "maximize",
            "run_validity": "SEMANTICALLY_ANALYZABLE",
            "verification_passed": True, "quality": quality,
            "cost": 0.2, "latency_seconds": 1.5,
            "input_tokens": 120, "output_tokens": 40}
    advisory_evaluation = history.append(
        "evaluation", loop_id=evaluator_advisory,
        detail=evaluation_detail(0.9))
    fresh_evaluation = history.append(
        "evaluation", loop_id=evaluator_fresh,
        detail=evaluation_detail(0.8))

    def outcome(arm, occurrence, assignment, exposure, decision, evaluation,
                evaluator, quality):
        return StageTrialOutcome(
            outcome_id=f"outcome-{arm}", occurrence_ref=occurrence.occurrence_ref,
            experiment_ref=experiment.experiment_ref, trial_ref=trial.trial_ref,
            assignment_ref=assignment.assignment_ref,
            exposure_manifest_ref=exposure.manifest_ref,
            decision_ref=decision.decision_ref,
            verification_ref=evaluation.event_digest, arm=arm,
            evaluator_id=evaluator, metric_ref=metric_ref,
            metric_direction="maximize", run_validity="SEMANTICALLY_ANALYZABLE",
            verification_passed=True, quality=quality, cost=0.2,
            latency_seconds=1.5, input_tokens=120, output_tokens=40)

    advisory_outcome = outcome(
        ADVISORY, advisory_occurrence, by_arm[ADVISORY], advisory_exposure,
        advisory_decision, advisory_evaluation, evaluator_advisory, 0.9)
    fresh_outcome = outcome(
        FRESH, fresh_occurrence, by_arm[FRESH], fresh_exposure,
        fresh_decision, fresh_evaluation, evaluator_fresh, 0.8)
    add(advisory_outcome, evaluator_advisory)
    add(fresh_outcome, evaluator_fresh)
    history.commit()

    with tempfile.TemporaryDirectory(
            prefix="loop-engine-stage-evidence-") as root:
        database = os.path.join(root, "stage-evidence.sqlite")
        projection = SQLiteStageEvidenceProjection(database)
        first_write = projection.ingest_run_history(history, namespace)
        before_replay = projection.health()["record_count"]
        replay = projection.ingest_run_history(history, namespace)
        check("exact_history_replay_is_idempotent",
              first_write and all(item.stored for item in first_write)
              and replay and all(item.replayed for item in replay)
              and before_replay == projection.health()["record_count"]
              == len(evidence_records))
        check("projection_is_file_backed_wal_and_non_authoritative",
              projection.health()["journal_mode"] == "wal"
              and projection.health()["authority"] == PROJECTION_AUTHORITY
              and projection.query(namespace)["authoritative"] is False)
        check("spec_trial_assignments_manifests_decisions_outcomes_are_linked",
              len(projection.query(namespace)["records"])
              == len(evidence_records)
              and len(projection.query(
                  namespace, record_type="stage_assistance_experiment/v1")[
                      "records"]) == 1
              and len(projection.query(
                  namespace, record_type="paired_stage_assistance_trial/v1")[
                      "records"]) == 1)

        conflicting = StageExperimentAssignment(
            "conflicting-arm", trial.trial_ref, experiment.experiment_ref,
            advisory_occurrence.occurrence_ref, first.semantic_signature,
            FRESH, experiment.campaign_seed)
        bad_assignment_history = RunHistory("bad-assignment-run")
        _init(bad_assignment_history, coordinator)
        _record_event(bad_assignment_history, conflicting, coordinator)
        bad_assignment_history.commit()
        check("projection_refuses_a_second_arm_for_one_trial_occurrence",
              _refused(lambda: projection.ingest_run_history(
                  bad_assignment_history, namespace),
                       (StageEvidenceProjectionError,)))

        def invalid_assignment_history(changed, run_suffix):
            invalid = RunHistory(f"bad-assignment-{run_suffix}")
            _init(invalid, coordinator)
            _record_event(invalid, changed, coordinator)
            invalid.commit()
            return invalid

        wrong_signature = replace(
            by_arm[ADVISORY], assignment_id="wrong-signature",
            semantic_signature="semantic.wrong/v1")
        wrong_seed = replace(
            by_arm[FRESH], assignment_id="wrong-seed",
            campaign_seed="another-campaign-seed")
        check("assignment_must_match_signature_seed_spec_and_trial",
              _refused(lambda: projection.ingest_run_history(
                  invalid_assignment_history(wrong_signature, "signature"),
                  namespace), (StageEvidenceProjectionError,))
              and _refused(lambda: projection.ingest_run_history(
                  invalid_assignment_history(wrong_seed, "seed"), namespace),
                           (StageEvidenceProjectionError,)))

        missing_evaluation = replace(
            advisory_outcome, outcome_id="missing-evaluation",
            verification_ref="e" * 64)
        bad_outcome_history = RunHistory("bad-outcome-run")
        _init(bad_outcome_history, evaluator_advisory)
        _record_event(bad_outcome_history, missing_evaluation,
                      evaluator_advisory)
        bad_outcome_history.commit()
        check("outcome_requires_the_exact_evaluation_event",
              _refused(lambda: projection.ingest_run_history(
                  bad_outcome_history, namespace),
                       (StageEvidenceProjectionError,)))

        wrong_arm = replace(
            advisory_outcome, outcome_id="wrong-outcome-arm", arm=FRESH)
        wrong_arm_history = RunHistory("bad-outcome-arm")
        _init(wrong_arm_history, evaluator_advisory)
        _record_event(wrong_arm_history, wrong_arm, evaluator_advisory)
        wrong_arm_history.commit()
        check("outcome_arm_must_match_assignment_trial_spec_and_manifest",
              _refused(lambda: projection.ingest_run_history(
                  wrong_arm_history, namespace),
                       (StageEvidenceProjectionError,)))

        bad_accounting_history = RunHistory("bad-outcome-accounting")
        _init(bad_accounting_history, evaluator_advisory)
        accounting_evaluation = bad_accounting_history.append(
            "evaluation", loop_id=evaluator_advisory,
            detail=evaluation_detail(0.9))
        changed_accounting = replace(
            advisory_outcome, outcome_id="changed-accounting",
            verification_ref=accounting_evaluation.event_digest,
            cost=999.0, input_tokens=999)
        _record_event(bad_accounting_history, changed_accounting,
                      evaluator_advisory)
        bad_accounting_history.commit()
        check("outcome_accounting_must_match_its_evaluation_event",
              _refused(lambda: projection.ingest_run_history(
                  bad_accounting_history, namespace),
                       (StageEvidenceProjectionError,)))

        invented_manifest = replace(
            advisory_exposure, manifest_id="invented-snapshot",
            retrieval_snapshot_ref="stage-retrieval-snapshot:sha256:" + "f" * 64)
        bad_manifest_history = RunHistory("bad-manifest-run")
        _init(bad_manifest_history, advisory_occurrence.loop_id)
        _record_event(bad_manifest_history, invented_manifest,
                      advisory_occurrence.loop_id)
        bad_manifest_history.commit()
        check("manifest_requires_its_exact_retrieval_snapshot",
              _refused(lambda: projection.ingest_run_history(
                  bad_manifest_history, namespace),
                       (StageEvidenceProjectionError,)))

        mismatched_occurrence = replace(first, run_id="not-source-history")
        bad_occurrence_history = RunHistory("bad-occurrence-run")
        _init(bad_occurrence_history, mismatched_occurrence.loop_id)
        _model_event(bad_occurrence_history, mismatched_occurrence)
        _record_event(bad_occurrence_history, mismatched_occurrence,
                      mismatched_occurrence.loop_id)
        bad_occurrence_history.commit()
        check("occurrence_matches_actual_run_loop_activation_and_model_call",
              _refused(lambda: projection.ingest_run_history(
                  bad_occurrence_history, namespace),
                       (StageEvidenceProjectionError,)))

        no_call = _occurrence(
            namespace, "missing-call", run_id="bad-missing-call-run")
        missing_call_history = RunHistory(no_call.run_id)
        _init(missing_call_history, no_call.loop_id)
        _record_event(missing_call_history, no_call, no_call.loop_id)
        missing_call_history.commit()
        check("occurrence_without_a_model_call_event_is_refused",
              _refused(lambda: projection.ingest_run_history(
                  missing_call_history, namespace),
                       (StageEvidenceProjectionError,)))

        rebuilt = projection.rebuild((history,), namespace)
        check("namespace_projection_rebuilds_from_canonical_history_only",
              len(rebuilt) == len(evidence_records)
              and len(projection.query(namespace)["records"])
              == len(evidence_records))

        future_history = RunHistory("future-retrieval-run")
        future_source = _occurrence(
            namespace, "future-source", run_id=future_history.run_id)
        future_target = _occurrence(
            namespace, "future-target", run_id=future_history.run_id)
        future_candidate = StageRetrievalCandidate(
            "prior-stage.future", future_source.occurrence_ref,
            future_target.semantic_signature, "semantic_signature",
            contract_compatible=True, effect_compatible=True,
            authority_compatible=True, privacy_compatible=True)
        future_snapshot = StageRetrievalSnapshot(
            "snapshot-before-source", future_target.occurrence_ref,
            future_target.semantic_signature, (future_candidate,))
        for loop_id in (future_source.loop_id, future_target.loop_id,
                        f"model-{future_source.semantic_call_id}",
                        f"model-{future_target.semantic_call_id}"):
            _init(future_history, loop_id)
        _record_event(future_history, future_snapshot, future_target.loop_id)
        _model_event(future_history, future_source)
        _model_event(future_history, future_target)
        _record_event(future_history, future_source, future_source.loop_id)
        _record_event(future_history, future_target, future_target.loop_id)
        future_history.commit()
        check("rebuild_refuses_retrieval_evidence_from_a_future_source_event",
              _refused(lambda: projection.rebuild(
                  (future_history,), namespace),
                       (StageEvidenceProjectionError,)))
        projection.close()
        reopened = SQLiteStageEvidenceProjection(database)
        check("projection_survives_a_fresh_database_connection",
              len(reopened.query(namespace)["records"])
              == len(evidence_records))
        reopened.close()

        degraded = SQLiteStageEvidenceProjection(
            os.path.join(root, "degraded.sqlite"))
        degraded.close()
        degraded_results = degraded.safe_ingest_run_history(history, namespace)
        health = degraded.health()
        check("storage_degradation_is_nonfatal_and_visible",
              len(degraded_results) == 1 and degraded_results[0].degraded
              and health["degraded"] and health["write_failures"] == 1
              and health["last_error"] and health["rebuild_required"])

    uncommitted = RunHistory("stage-proof-uncommitted")
    uncommitted_occurrence = _occurrence(
        namespace, "uncommitted", run_id=uncommitted.run_id)
    _init(uncommitted, uncommitted_occurrence.loop_id)
    _model_event(uncommitted, uncommitted_occurrence)
    _record_event(uncommitted, uncommitted_occurrence,
                  uncommitted_occurrence.loop_id)
    with tempfile.TemporaryDirectory(
            prefix="loop-engine-stage-uncommitted-") as root:
        projection = SQLiteStageEvidenceProjection(
            os.path.join(root, "projection.sqlite"))
        check("uncommitted_history_cannot_feed_the_projection",
              _refused(lambda: projection.ingest_run_history(
                  uncommitted, namespace), (StageEvidenceProjectionError,)))
        projection.close()

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "stage_assistance_foundation_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests), "provider_calls": 0}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2, sort_keys=True))
