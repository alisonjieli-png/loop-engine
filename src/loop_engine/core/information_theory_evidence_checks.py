"""Offline checks for passive information and state-policy evidence.
Fixtures use declared observations without model, tool, or storage operations.
They exercise exact quantities, provenance, exclusions, and refusal paths."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from .information_evidence_contracts import (
    EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST,
    PAIRED_COMPRESSION_DISTORTION_ESTIMATOR_CONTRACT_DIGEST,
    InfrastructureValidityRecord,
)
from .information_theory_evidence import (
    DETERMINISTIC_PROJECTION,
    INSUFFICIENT_VALID_EVIDENCE,
    NOT_SUPPORTED_WITHIN_TOLERANCE,
    STOCHASTIC_PROJECTION,
    SUPPORTED_WITHIN_TOLERANCE,
    CategoricalDistribution,
    InformationMeasurementSpec,
    InformationTheoryEvidenceError,
    InformationUpdateEvidence,
    PredictiveStateSample,
    estimate_predictive_information,
)
from .state_policy_evidence import (
    PairedStatePolicyTrial,
    StatePolicyTolerance,
    assess_state_policy,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _payload_digest(value: object) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))


def self_test() -> dict[str, object]:
    tests: list[dict[str, object]] = []
    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})
    predictive = CategoricalDistribution(
        "predict.next-observation",
        "observation-class/v1",
        (("failure", 0.75), ("success", 0.25)),
    )
    prior = CategoricalDistribution(
        "belief.prior",
        "cause/v1",
        (("cause-a", 0.5), ("cause-b", 0.5)),
    )
    posterior = CategoricalDistribution(
        "belief.posterior",
        "cause/v1",
        (("cause-a", 0.8), ("cause-b", 0.2)),
    )
    update = InformationUpdateEvidence(
        "update.1",
        "observation.1",
        "evidence.1",
        "success",
        predictive,
        prior,
        posterior,
    )
    check(
        "shannon_surprisal_and_bayesian_surprise_are_distinct_quantities",
        abs((update.shannon_surprisal_bits or 0.0) - 2.0) < 1e-12
        and abs((update.bayesian_surprise[0] or 0.0) - 0.2780719051) < 1e-9
        and not update.bayesian_surprise[1],
    )
    check(
        "distribution_entropy_is_base_two_and_source_order_independent",
        abs(predictive.entropy_bits - 0.8112781245) < 1e-9
        and predictive.probabilities[0][0] == "failure",
    )
    impossible_prediction = replace(
        update,
        predictive_distribution=CategoricalDistribution(
            "predict.impossible",
            "observation-class/v1",
            (("failure", 1.0), ("success", 0.0)),
        ),
    )
    impossible_prior = replace(
        update,
        prior_beliefs=CategoricalDistribution(
            "belief.zero-prior",
            "cause/v1",
            (("cause-a", 0.0), ("cause-b", 1.0)),
        ),
    )
    check(
        "infinite_information_quantities_use_flags_not_non_json_numbers",
        impossible_prediction.shannon_surprisal_bits is None
        and impossible_prediction.shannon_surprisal_infinite
        and impossible_prior.bayesian_surprise == (None, True)
        and "Infinity" not in json.dumps(impossible_prediction.to_dict()),
    )
    distribution_refused = belief_support_refused = False
    try:
        CategoricalDistribution("bad", "v", (("a", 0.8), ("b", 0.8)))
    except InformationTheoryEvidenceError:
        distribution_refused = True
    try:
        replace(
            update,
            posterior_beliefs=CategoricalDistribution(
                "different",
                "other-variable/v1",
                (("cause-a", 0.5), ("cause-b", 0.5)),
            ),
        )
    except InformationTheoryEvidenceError:
        belief_support_refused = True
    check(
        "invalid_probability_mass_and_belief_variable_mismatch_fail_closed",
        distribution_refused and belief_support_refused,
    )
    check(
        "information_update_is_measurement_only",
        update.to_dict()["grants_authority"] is False
        and update.to_dict()["gradient_surprise_measured"] is False
        and update.to_dict()["measurement_specification_bound"] is False
        and update.to_dict()["issued_measurement"] is False,
    )
    target_digest = _sha("outcome-contract/v1")
    population_digest = _sha("population.fixed/v1")
    evaluator_digest = _sha("evaluator/v1")
    measurement = InformationMeasurementSpec(
        measurement_id="measurement.predictive-state.1",
        measure_kind="predictive_state_information",
        random_variable_refs=("history-class/v1", "state-class/v1", "outcome/v1"),
        target_ref="outcome-contract/v1",
        target_digest=target_digest,
        target_horizon="next verified observation",
        conditioning_refs=("task-region.tabular", "environment.fixture.v1"),
        namespace_ref="namespace.campaign-a.tenant-a",
        privacy_class="run_private",
        task_region_ref="task-region.tabular",
        population_ref="population.fixed/v1",
        population_digest=population_digest,
        evaluator_ref="evaluator.fixture/v1",
        evaluator_digest=evaluator_digest,
        exclusion_policy_ref="exclusion.infrastructure-only/v1",
        exclusion_policy_digest=_sha("exclusion.infrastructure-only/v1"),
        minimum_valid_population_coverage=0.6,
        selection_rule_ref="selection.frozen-alternating/v1",
        selection_rule_digest=_sha("selection.frozen-alternating/v1"),
        probability_model_ref="empirical-counts/v1",
        probability_model_digest=_sha("empirical-counts/v1"),
        estimator_ref="empirical_plugin_base2/v1",
        estimator_contract_digest=EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST,
        holdout_design_ref="holdout.fixture-only-no-generalization/v1",
        holdout_design_digest=_sha("holdout.fixture-only-no-generalization/v1"),
        bias_correction="none",
        confidence_interval_method="not_estimated",
        reference_manifest_ref="manifest.predictive-state.fixture/v1",
        reference_manifest_digest=_sha("manifest.predictive-state.fixture/v1"),
        evidence_refs=("fixture:predictive-state",),
    )
    def sample(
        index: int,
        history_class: str,
        state_class: str,
        outcome_class: str,
        *,
        mode: str = DETERMINISTIC_PROJECTION,
        valid: bool = True,
    ) -> PredictiveStateSample:
        source_occurrence_ref = f"source-occurrence.{index}"
        history_ref = f"history.{index}"
        history_digest = _sha(history_ref)
        state_ref = f"state.{index}"
        state_digest = _sha(f"state.{index}:{state_class}")
        outcome_ref = f"outcome.{index}" if valid else ""
        admitted_outcome_class = outcome_class if valid else ""
        temporal_ref = f"temporal-order.{index}"
        temporal_digest = _sha(temporal_ref)
        subject_digest = _payload_digest(
            {
                "namespace_ref": "namespace.campaign-a.tenant-a",
                "privacy_class": "run_private",
                "task_region_ref": "task-region.tabular",
                "population_ref": "population.fixed/v1",
                "population_digest": population_digest,
                "source_occurrence_ref": source_occurrence_ref,
                "projection_policy_ref": "state-policy.compact/v1",
                "projection_policy_digest": _sha("state-policy.compact/v1"),
                "projection_mode": mode,
                "history_representation_ref": history_ref,
                "history_representation_digest": history_digest,
                "history_class": history_class,
                "state_ref": state_ref,
                "state_digest": state_digest,
                "state_class": state_class,
                "outcome_contract_ref": "outcome-contract/v1",
                "outcome_contract_digest": target_digest,
                "outcome_ref": outcome_ref,
                "outcome_class": admitted_outcome_class,
                "evaluator_ref": "evaluator.fixture/v1",
                "evaluator_digest": evaluator_digest,
                "temporal_order_evidence_ref": temporal_ref,
                "temporal_order_evidence_digest": temporal_digest,
            }
        )
        validity = InfrastructureValidityRecord(
            record_id=f"validity:{index}",
            subject_ref=source_occurrence_ref,
            subject_digest=subject_digest,
            evaluator_ref="evaluator.fixture/v1",
            evaluator_digest=evaluator_digest,
            status="valid" if valid else "invalid",
            reason_code="" if valid else "provider_transport_invalid",
            evidence_refs=(f"validity-evidence:{index}",),
        )
        return PredictiveStateSample(
            sample_id=f"sample.{index}",
            namespace_ref="namespace.campaign-a.tenant-a",
            privacy_class="run_private",
            task_region_ref="task-region.tabular",
            population_ref="population.fixed/v1",
            population_digest=population_digest,
            source_occurrence_ref=source_occurrence_ref,
            projection_policy_ref="state-policy.compact/v1",
            projection_policy_digest=_sha("state-policy.compact/v1"),
            projection_mode=mode,
            history_representation_ref=history_ref,
            history_representation_digest=history_digest,
            history_class=history_class,
            state_ref=state_ref,
            state_digest=state_digest,
            state_class=state_class,
            outcome_contract_ref="outcome-contract/v1",
            outcome_contract_digest=target_digest,
            outcome_ref=outcome_ref,
            evaluator_ref="evaluator.fixture/v1",
            evaluator_digest=evaluator_digest,
            temporal_order_evidence_ref=temporal_ref,
            temporal_order_evidence_digest=temporal_digest,
            validity_record=validity,
            evidence_refs=(f"evidence:{index}",),
            outcome_class=admitted_outcome_class,
        )
    lossy_samples = (
        sample(0, "history-a", "state-shared", "outcome-a"),
        sample(1, "history-b", "state-shared", "outcome-b"),
        sample(2, "history-a", "state-shared", "outcome-a"),
        sample(3, "history-b", "state-shared", "outcome-b"),
        sample(4, "history-a", "state-shared", "outcome-a", valid=False),
    )
    lossy = estimate_predictive_information(lossy_samples, measurement)
    check(
        "lossy_state_has_one_bit_of_empirical_residual_predictive_information",
        lossy.sample_count == 4
        and lossy.excluded_sample_refs == ("sample.4",)
        and abs(lossy.outcome_entropy_bits - 1.0) < 1e-12
        and abs(lossy.mutual_information_history_outcome_bits - 1.0) < 1e-12
        and abs(lossy.mutual_information_state_outcome_bits) < 1e-12
        and abs(lossy.residual_predictive_information_bits - 1.0) < 1e-12
        and lossy.state_information_retention == 0.0,
    )
    check(
        "empirical_information_binds_measurement_population_and_exact_samples",
        lossy.measurement_spec_digest == measurement.digest
        and lossy.source_population_digest == population_digest
        and lossy.sample_population_digest
        == _payload_digest(
            [
                row.identity_dict()
                for row in sorted(lossy_samples, key=lambda item: item.sample_id)
            ]
        )
        and lossy.data_processing_inequality_holds is True,
    )
    perfect_samples = tuple(
        sample(
            index,
            row.history_class,
            "state-a" if row.history_class == "history-a" else "state-b",
            row.outcome_class,
        )
        for index, row in enumerate(lossy_samples[:4])
    )
    perfect = estimate_predictive_information(perfect_samples, measurement)
    check(
        "predictively_complete_state_has_zero_empirical_residual",
        abs(perfect.residual_predictive_information_bits) < 1e-12
        and perfect.state_information_retention == 1.0,
    )
    stochastic = estimate_predictive_information(
        tuple(
            sample(
                index,
                row.history_class,
                row.state_class,
                row.outcome_class,
                mode=STOCHASTIC_PROJECTION,
            )
            for index, row in enumerate(lossy_samples[:4])
        ),
        measurement,
    )
    check(
        "stochastic_projection_does_not_claim_a_data_processing_check",
        not stochastic.data_processing_check_applicable
        and stochastic.data_processing_inequality_holds is None
        and not stochastic.residual_predictive_information_interpretation_applicable,
    )
    deterministic_conflict_refused = False
    try:
        estimate_predictive_information(
            (
                sample(20, "same-history", "state-a", "outcome-a"),
                sample(21, "same-history", "state-b", "outcome-b"),
            ),
            measurement,
        )
    except InformationTheoryEvidenceError:
        deterministic_conflict_refused = True
    check(
        "claimed_deterministic_projection_cannot_map_one_history_class_twice",
        deterministic_conflict_refused,
    )
    duplicate_refused = mismatch_refused = no_valid_refused = False
    try:
        estimate_predictive_information(
            (lossy_samples[0], lossy_samples[0]), measurement
        )
    except InformationTheoryEvidenceError:
        duplicate_refused = True
    try:
        estimate_predictive_information(
            (lossy_samples[0], replace(lossy_samples[1], evaluator_ref="other")),
            measurement,
        )
    except InformationTheoryEvidenceError:
        mismatch_refused = True
    try:
        estimate_predictive_information((lossy_samples[4],), measurement)
    except InformationTheoryEvidenceError:
        no_valid_refused = True
    check(
        "duplicate_mixed_evaluator_and_no_valid_samples_fail_closed",
        duplicate_refused and mismatch_refused and no_valid_refused,
    )
    wrong_measurement_refused = False
    try:
        estimate_predictive_information(
            lossy_samples,
            replace(measurement, target_ref="another-target/v1"),
        )
    except InformationTheoryEvidenceError:
        wrong_measurement_refused = True
    check(
        "measurement_specification_must_match_target_and_task_region",
        wrong_measurement_refused,
    )
    check(
        "empirical_information_serializes_without_a_generalization_claim",
        json.loads(json.dumps(lossy.to_dict()))["generalization_claimed"] is False
        and lossy.to_dict()["estimator_bias_warning"]
        and measurement.to_dict()["grants_authority"] is False,
    )
    forged_information_refused = forged_count_refused = False
    try:
        replace(lossy, mutual_information_state_outcome_bits=0.5)
    except (InformationTheoryEvidenceError, TypeError):
        forged_information_refused = True
    try:
        replace(lossy, sample_count=99)
    except (InformationTheoryEvidenceError, TypeError):
        forged_count_refused = True
    check(
        "predictive_information_aggregate_cannot_be_publicly_reconstructed",
        forged_information_refused and forged_count_refused,
    )
    invalid_outcome_refused = excluded_scope_refused = evaluator_refused = False
    try:
        replace(lossy_samples[4], outcome_class="outcome-a")
    except InformationTheoryEvidenceError:
        invalid_outcome_refused = True
    try:
        estimate_predictive_information(
            (*lossy_samples[:4], replace(lossy_samples[4], namespace_ref="other")),
            measurement,
        )
    except InformationTheoryEvidenceError:
        excluded_scope_refused = True
    try:
        estimate_predictive_information(
            lossy_samples,
            replace(measurement, evaluator_ref="evaluator.other/v1"),
        )
    except InformationTheoryEvidenceError:
        evaluator_refused = True
    check(
        "invalid_samples_cannot_hide_outcomes_or_cross_declared_scope",
        invalid_outcome_refused and excluded_scope_refused and evaluator_refused,
    )
    impossible_entropy_refused = deterministic_dpi_refused = wrong_kind_refused = False
    try:
        replace(
            lossy,
            outcome_entropy_bits=0.5,
            conditional_entropy_outcome_given_state_bits=1.0,
            mutual_information_history_outcome_bits=0.5,
        )
    except (InformationTheoryEvidenceError, TypeError):
        impossible_entropy_refused = True
    try:
        replace(
            lossy,
            history_class_count=2,
            state_class_count=2,
            conditional_entropy_outcome_given_history_bits=1.0,
            conditional_entropy_outcome_given_state_bits=0.0,
            mutual_information_history_outcome_bits=0.0,
            mutual_information_state_outcome_bits=1.0,
            residual_predictive_information_bits=0.0,
            state_information_retention=None,
            data_processing_inequality_holds=False,
        )
    except (InformationTheoryEvidenceError, TypeError):
        deterministic_dpi_refused = True
    try:
        estimate_predictive_information(
            lossy_samples,
            replace(measurement, measure_kind="paired_state_compression_distortion"),
        )
    except InformationTheoryEvidenceError:
        wrong_kind_refused = True
    check(
        "impossible_entropy_deterministic_dpi_and_wrong_measure_kind_fail_closed",
        impossible_entropy_refused and deterministic_dpi_refused and wrong_kind_refused,
    )
    reordered = estimate_predictive_information(tuple(reversed(lossy_samples)), measurement)
    check(
        "predictive_sample_population_identity_is_order_independent",
        reordered.sample_population_digest == lossy.sample_population_digest
        and reordered.included_sample_refs == lossy.included_sample_refs
        and reordered.excluded_sample_refs == lossy.excluded_sample_refs,
    )
    def paired_trial(
        index: int,
        control_bytes: int,
        state_bytes: int,
        control_loss: float,
        state_loss: float,
        *,
        control_false_acceptance: bool = False,
        state_false_acceptance: bool = False,
        valid: bool = True,
        costs_known: bool = True,
    ) -> PairedStatePolicyTrial:
        control_outcome_ref = f"outcome.control.{index}" if valid else ""
        treatment_outcome_ref = f"outcome.state.{index}" if valid else ""
        pair_source_ref = f"pair-source.{index}"
        source_state_digest = _sha(f"frozen-state:{index}")
        control_occurrence_ref = f"occurrence.control.{index}"
        treatment_occurrence_ref = f"occurrence.state.{index}"
        control_cost = 0.10 if costs_known else None
        treatment_cost = 0.05 if costs_known else None
        subject_digest = _payload_digest(
            {
                "namespace_ref": "namespace.campaign-a.tenant-a",
                "privacy_class": "run_private",
                "task_region_ref": "task-region.tabular",
                "population_ref": "population.fixed/v1",
                "population_digest": population_digest,
                "pair_source_ref": pair_source_ref,
                "source_state_digest": source_state_digest,
                "full_history_policy_ref": "context.full-history/v1",
                "state_policy_ref": "context.structured-state/v1",
                "model_profile_ref": "model.fixture/v1",
                "model_profile_digest": _sha("model.fixture/v1"),
                "evaluator_ref": "evaluator.fixture/v1",
                "evaluator_digest": evaluator_digest,
                "outcome_contract_ref": "outcome-contract/v1",
                "outcome_contract_digest": target_digest,
                "control_occurrence_ref": control_occurrence_ref,
                "treatment_occurrence_ref": treatment_occurrence_ref,
                "control_outcome_ref": control_outcome_ref,
                "treatment_outcome_ref": treatment_outcome_ref,
                "control_context_bytes": control_bytes,
                "treatment_context_bytes": state_bytes,
                "control_loss": control_loss,
                "treatment_loss": state_loss,
                "control_false_acceptance": control_false_acceptance,
                "treatment_false_acceptance": state_false_acceptance,
                "control_cost_usd": control_cost,
                "treatment_cost_usd": treatment_cost,
                "control_latency_seconds": 2.0,
                "treatment_latency_seconds": 1.5,
            }
        )
        validity = InfrastructureValidityRecord(
            record_id=f"paired-validity:{index}",
            subject_ref=pair_source_ref,
            subject_digest=subject_digest,
            evaluator_ref="evaluator.fixture/v1",
            evaluator_digest=evaluator_digest,
            status="valid" if valid else "invalid",
            reason_code="" if valid else "provider_transport_invalid",
            evidence_refs=(f"paired-validity-evidence:{index}",),
        )
        return PairedStatePolicyTrial(
            trial_id=f"paired.{index}",
            namespace_ref="namespace.campaign-a.tenant-a",
            privacy_class="run_private",
            task_region_ref="task-region.tabular",
            population_ref="population.fixed/v1",
            population_digest=population_digest,
            pair_source_ref=pair_source_ref,
            source_state_digest=source_state_digest,
            full_history_policy_ref="context.full-history/v1",
            state_policy_ref="context.structured-state/v1",
            model_profile_ref="model.fixture/v1",
            model_profile_digest=_sha("model.fixture/v1"),
            evaluator_ref="evaluator.fixture/v1",
            evaluator_digest=evaluator_digest,
            outcome_contract_ref="outcome-contract/v1",
            outcome_contract_digest=target_digest,
            control_occurrence_ref=control_occurrence_ref,
            treatment_occurrence_ref=treatment_occurrence_ref,
            control_outcome_ref=control_outcome_ref,
            treatment_outcome_ref=treatment_outcome_ref,
            control_context_bytes=control_bytes,
            treatment_context_bytes=state_bytes,
            control_loss=control_loss,
            treatment_loss=state_loss,
            control_false_acceptance=control_false_acceptance,
            treatment_false_acceptance=state_false_acceptance,
            validity_record=validity,
            evidence_refs=(f"evidence:paired:{index}",),
            control_cost_usd=control_cost,
            treatment_cost_usd=treatment_cost,
            control_latency_seconds=2.0,
            treatment_latency_seconds=1.5,
        )
    paired = (
        paired_trial(0, 1000, 250, 0.0, 0.05),
        paired_trial(1, 800, 200, 0.1, 0.15, costs_known=False),
        paired_trial(2, 900, 225, 0.0, 0.0, valid=False),
    )
    tolerance = StatePolicyTolerance(
        "tolerance.state-context",
        "1.0.0",
        minimum_valid_pairs=2,
        maximum_mean_excess_loss=0.05,
        maximum_treatment_loss=0.2,
        maximum_false_acceptance_delta=0.0,
        maximum_treatment_false_acceptance_rate=0.0,
        minimum_aggregate_compression_ratio=3.5,
    )
    state_measurement = replace(
        measurement,
        measurement_id="measurement.state-policy.1",
        measure_kind="paired_state_compression_distortion",
        random_variable_refs=("context-policy/v1", "verified-loss/v1"),
        estimator_ref="paired_empirical_compression_distortion/v1",
        estimator_contract_digest=PAIRED_COMPRESSION_DISTORTION_ESTIMATOR_CONTRACT_DIGEST,
        log_base=None,
        units="bytes_and_declared_loss",
    )
    assessment = assess_state_policy(
        paired,
        tolerance,
        state_measurement,
        assessment_id="assessment.state-context.1",
    )
    check(
        "paired_compression_loss_proxy_can_meet_one_declared_tolerance",
        assessment.status == SUPPORTED_WITHIN_TOLERANCE
        and assessment.valid_pairs == 2
        and assessment.excluded_trial_refs == ("paired.2",)
        and abs((assessment.aggregate_context_compression_ratio or 0.0) - 4.0) < 1e-12
        and abs(assessment.mean_excess_loss - 0.05) < 1e-12,
    )
    check(
        "unknown_cost_does_not_become_a_partial_or_zero_aggregate",
        assessment.mean_cost_delta_usd is None
        and not assessment.economics_complete
        and not assessment.economic_claim_supported
        and abs((assessment.mean_latency_delta_seconds or 0.0) + 0.5) < 1e-12,
    )
    insufficient = assess_state_policy(
        paired,
        replace(tolerance, minimum_valid_pairs=3),
        state_measurement,
        assessment_id="assessment.insufficient",
    )
    harmful = assess_state_policy(
        (
            paired[0],
            paired_trial(
                1,
                800,
                200,
                0.1,
                0.15,
                state_false_acceptance=True,
                costs_known=False,
            ),
        ),
        tolerance,
        state_measurement,
        assessment_id="assessment.harmful",
    )
    check(
        "insufficient_and_false_acceptance_results_do_not_pass",
        insufficient.status == INSUFFICIENT_VALID_EVIDENCE
        and harmful.status == NOT_SUPPORTED_WITHIN_TOLERANCE
        and harmful.false_acceptance_delta == 0.5,
    )
    bad_pair_refused = bad_number_refused = mixed_population_refused = False
    try:
        replace(paired[0], treatment_occurrence_ref=paired[0].control_occurrence_ref)
    except InformationTheoryEvidenceError:
        bad_pair_refused = True
    try:
        replace(paired[0], treatment_loss=float("nan"))
    except InformationTheoryEvidenceError:
        bad_number_refused = True
    try:
        assess_state_policy(
            (paired[0], replace(paired[1], population_ref="population.other")),
            tolerance,
            state_measurement,
            assessment_id="assessment.mixed",
        )
    except InformationTheoryEvidenceError:
        mixed_population_refused = True
    check(
        "same_occurrence_nonfinite_and_mixed_population_pairs_fail_closed",
        bad_pair_refused and bad_number_refused and mixed_population_refused,
    )
    zero_context_refused = wrong_spec_refused = False
    try:
        replace(paired[0], treatment_context_bytes=0)
    except InformationTheoryEvidenceError:
        zero_context_refused = True
    try:
        assess_state_policy(
            paired,
            tolerance,
            replace(state_measurement, population_ref="population.other"),
            assessment_id="assessment.wrong-spec",
        )
    except InformationTheoryEvidenceError:
        wrong_spec_refused = True
    check(
        "zero_context_and_wrong_measurement_binding_fail_closed",
        zero_context_refused and wrong_spec_refused,
    )
    forged_assessment_refused = False
    try:
        replace(assessment, valid_pairs=99)
    except (InformationTheoryEvidenceError, TypeError):
        forged_assessment_refused = True
    check(
        "assessment_aggregate_cannot_be_publicly_reconstructed",
        forged_assessment_refused,
    )
    same_outcome_refused = duplicate_comparison_refused = reused_occurrence_refused = False
    try:
        replace(
            paired[0],
            treatment_outcome_ref=paired[0].control_outcome_ref,
        )
    except InformationTheoryEvidenceError:
        same_outcome_refused = True
    try:
        assess_state_policy(
            (paired[0], replace(paired[0], trial_id="paired.relabel")),
            tolerance,
            state_measurement,
            assessment_id="assessment.duplicate-comparison",
        )
    except InformationTheoryEvidenceError:
        duplicate_comparison_refused = True
    try:
        assess_state_policy(
            (
                paired[0],
                replace(
                    paired[1],
                    control_occurrence_ref=paired[0].control_occurrence_ref,
                ),
            ),
            tolerance,
            state_measurement,
            assessment_id="assessment.reused-occurrence",
        )
    except InformationTheoryEvidenceError:
        reused_occurrence_refused = True
    check(
        "paired_evidence_cannot_reuse_outcomes_comparisons_or_occurrences",
        same_outcome_refused
        and duplicate_comparison_refused
        and reused_occurrence_refused,
    )
    invalid_semantics_refused = invalid_reason_refused = False
    try:
        replace(paired[2], control_loss=0.1)
    except InformationTheoryEvidenceError:
        invalid_semantics_refused = True
    try:
        replace(paired[2], invalid_reason="semantic_failure")
    except (InformationTheoryEvidenceError, TypeError):
        invalid_reason_refused = True
    check(
        "infrastructure_exclusions_are_typed_and_carry_no_semantic_outcome",
        invalid_semantics_refused and invalid_reason_refused,
    )
    both_arms_false = assess_state_policy(
        (
            paired_trial(
                0,
                1000,
                250,
                0.0,
                0.05,
                control_false_acceptance=True,
                state_false_acceptance=True,
            ),
            paired[1],
        ),
        tolerance,
        state_measurement,
        assessment_id="assessment.absolute-false-acceptance",
    )
    check(
        "absolute_false_acceptance_prevents_a_zero_delta_from_passing",
        both_arms_false.status == NOT_SUPPORTED_WITHIN_TOLERANCE
        and both_arms_false.false_acceptance_delta == 0.0
        and both_arms_false.treatment_false_acceptance_rate == 0.5,
    )
    wrong_kind_assessment_refused = wrong_evaluator_assessment_refused = False
    try:
        assess_state_policy(
            paired,
            tolerance,
            measurement,
            assessment_id="assessment.wrong-kind",
        )
    except InformationTheoryEvidenceError:
        wrong_kind_assessment_refused = True
    try:
        assess_state_policy(
            paired,
            tolerance,
            replace(state_measurement, evaluator_digest=_sha("another-evaluator")),
            assessment_id="assessment.wrong-evaluator",
        )
    except InformationTheoryEvidenceError:
        wrong_evaluator_assessment_refused = True
    check(
        "state_assessment_binds_measure_kind_and_evaluator",
        wrong_kind_assessment_refused and wrong_evaluator_assessment_refused,
    )
    reordered_assessment = assess_state_policy(
        tuple(reversed(paired)),
        tolerance,
        state_measurement,
        assessment_id="assessment.reordered",
    )
    check(
        "paired_population_identity_is_order_independent",
        reordered_assessment.source_trial_population_digest
        == assessment.source_trial_population_digest
        and reordered_assessment.included_trial_refs == assessment.included_trial_refs
        and reordered_assessment.excluded_trial_refs == assessment.excluded_trial_refs,
    )
    check(
        "state_policy_assessment_is_measurement_not_promotion",
        assessment.to_dict()["measurement_only"] is True
        and assessment.to_dict()["promotion_authorized"] is False
        and assessment.to_dict()["rate_distortion_function_estimated"] is False
        and assessment.measurement_spec_digest == state_measurement.digest,
    )
    passed = sum(1 for item in tests if item["passed"])
    return {
        "record_type": "information_theory_evidence_checks/v1",
        "scope": "offline_passive_measurement_only",
        "provider_calls": 0, "tool_calls": 0, "storage_writes": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = ("self_test",)
