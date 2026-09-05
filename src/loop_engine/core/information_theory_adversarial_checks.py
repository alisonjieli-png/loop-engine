"""Adversarial checks for passive information and state-policy evidence.

These fixtures target provenance relabeling, exclusion manipulation, aggregate
forgery, attrition, unsafe loss, and numeric edge cases. They perform no model
call, storage write, policy selection, or promotion.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from .information_evidence_contracts import (
    EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST,
    PAIRED_COMPRESSION_DISTORTION_ESTIMATOR_CONTRACT_DIGEST,
    InformationMeasurementSpec,
    InformationTheoryEvidenceError,
    InfrastructureValidityRecord,
)
from .information_theory_evidence import (
    DETERMINISTIC_PROJECTION,
    STOCHASTIC_PROJECTION,
    CategoricalDistribution,
    EmpiricalPredictiveInformation,
    InformationUpdateEvidence,
    PredictiveStateSample,
    estimate_predictive_information,
)
from .information_update_evidence import (
    CategoricalForecastScore,
    score_categorical_forecast,
)
from .state_policy_evidence import (
    INSUFFICIENT_VALID_EVIDENCE,
    NOT_SUPPORTED_WITHIN_TOLERANCE,
    PairedStatePolicyTrial,
    StatePolicyAssessment,
    StatePolicyTolerance,
    assess_state_policy,
)


def _forecast_score_checks() -> list[dict]:
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})

    predictive = CategoricalDistribution(
        "prediction", "observation", (("failure", 0.75), ("success", 0.25)))
    prior = CategoricalDistribution("prior", "cause", (("a", 0.5), ("b", 0.5)))
    posterior = CategoricalDistribution("posterior", "cause", (("a", 0.8), ("b", 0.2)))
    update = InformationUpdateEvidence("update", "observation", "evidence", "success",
                                       predictive, prior, posterior)
    score = score_categorical_forecast(update)
    check("proper_scores_distinguish_prediction_error_from_belief_surprise",
          score.multiclass_brier_loss == 1.125
          and score.normalized_brier_loss == 0.5625
          and score.log_loss_bits == 2.0
          and abs(score.normalized_brier_loss - (update.bayesian_surprise[0] or 0.0)) > 0.1)
    reordered = replace(update, predictive_distribution=replace(
        predictive, probabilities=tuple(reversed(predictive.probabilities))))
    check("proper_score_and_forecast_digest_are_label_order_invariant",
          score_categorical_forecast(reordered) == score)
    zero_score = score_categorical_forecast(replace(update, predictive_distribution=replace(
        predictive, probabilities=(("failure", 1.0), ("success", 0.0)))))
    check("zero_probability_realized_class_has_max_brier_and_infinite_log_loss",
          zero_score.multiclass_brier_loss == 2.0
          and zero_score.normalized_brier_loss == 1.0
          and zero_score.log_loss_bits is None and zero_score.log_loss_infinite
          and "Infinity" not in json.dumps(zero_score.to_dict(), allow_nan=False))
    perfect = score_categorical_forecast(replace(update, predictive_distribution=replace(
        predictive, probabilities=(("failure", 0.0), ("success", 1.0)))))
    check("perfect_point_forecast_has_zero_proper_loss",
          perfect.multiclass_brier_loss == 0.0 and perfect.log_loss_bits == 0.0)
    multi = score_categorical_forecast(replace(update, observed_outcome="b",
        predictive_distribution=CategoricalDistribution(
            "multi", "class", (("a", 0.2), ("b", 0.5), ("c", 0.3)))))
    check("multiclass_brier_is_scored_over_full_support",
          abs(multi.multiclass_brier_loss - 0.38) < 1e-12
          and multi.log_loss_bits == 1.0 and multi.support_size == 3)
    refused_foreign = refused_forgery = False
    try:
        score_categorical_forecast(replace(update, observed_outcome="outside"))
    except InformationTheoryEvidenceError:
        refused_foreign = True
    try:
        CategoricalForecastScore(multiclass_brier_loss=0.0)
    except TypeError:
        refused_forgery = True
    check("forecast_score_refuses_unknown_support_and_direct_score_forgery",
          refused_foreign and refused_forgery)
    score_record = score.to_dict()
    class MisreportedSurprise(InformationUpdateEvidence):
        @property
        def shannon_surprisal_bits(self):
            return 0.0

    spoofed = MisreportedSurprise("spoof", "observation", "evidence", "success",
                                 predictive, prior, posterior)
    check("forecast_score_recomputes_instead_of_trusting_overridden_summary",
          score_categorical_forecast(spoofed).log_loss_bits == 2.0)
    class UnvalidatedDistribution(CategoricalDistribution):
        def __post_init__(self):
            pass

    invalid_forecast_refused = False
    try:
        score_categorical_forecast(replace(update, predictive_distribution=
            UnvalidatedDistribution("bad", "observation", (("failure", -2.0), ("success", 3.0)))))
    except InformationTheoryEvidenceError:
        invalid_forecast_refused = True
    check("forecast_score_revalidates_subclass_probability_mass", invalid_forecast_refused)
    check("proper_score_is_not_calibration_temporal_or_population_proof",
          all(score_record[name] is False for name in (
              "measurement_specification_bound", "population_and_evaluator_bound",
              "forecast_precedes_outcome_verified", "calibration_established",
              "issued_measurement", "grants_authority")))
    return tests


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _content_digest(value: object) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return _sha(body)


def _measurement(
    measure_kind: str,
    *,
    minimum_valid_population_coverage: float = 0.75,
) -> InformationMeasurementSpec:
    target = _sha("outcome-contract/v1")
    population = _sha("population.fixed/v1")
    evaluator = _sha("evaluator.fixture/v1")
    paired = measure_kind == "paired_state_compression_distortion"
    return InformationMeasurementSpec(
        measurement_id=f"measurement.{measure_kind}",
        measure_kind=measure_kind,
        random_variable_refs=("history/v1", "state/v1", "outcome/v1"),
        target_ref="outcome-contract/v1",
        target_digest=target,
        target_horizon="next verified observation",
        conditioning_refs=("task-region.fixture",),
        namespace_ref="namespace.fixture",
        privacy_class="run_private",
        task_region_ref="task-region.fixture",
        population_ref="population.fixed/v1",
        population_digest=population,
        evaluator_ref="evaluator.fixture/v1",
        evaluator_digest=evaluator,
        exclusion_policy_ref="exclusion.infrastructure-only/v1",
        exclusion_policy_digest=_sha("exclusion.infrastructure-only/v1"),
        minimum_valid_population_coverage=minimum_valid_population_coverage,
        selection_rule_ref="selection.frozen/v1",
        selection_rule_digest=_sha("selection.frozen/v1"),
        probability_model_ref="empirical-counts/v1",
        probability_model_digest=_sha("empirical-counts/v1"),
        estimator_ref=(
            "paired_empirical_compression_distortion/v1"
            if paired
            else "empirical_plugin_base2/v1"
        ),
        estimator_contract_digest=(
            PAIRED_COMPRESSION_DISTORTION_ESTIMATOR_CONTRACT_DIGEST
            if paired
            else EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST
        ),
        holdout_design_ref="holdout.source-task-lineage/v1",
        holdout_design_digest=_sha("holdout.source-task-lineage/v1"),
        bias_correction="none",
        confidence_interval_method="not_estimated",
        reference_manifest_ref="manifest.fixture/v1",
        reference_manifest_digest=_sha("manifest.fixture/v1"),
        evidence_refs=("evidence:measurement",),
        log_base=None if paired else 2.0,
        units="bytes_and_declared_loss" if paired else "bits",
    )


def _sample_subject(values: dict[str, object]) -> dict[str, object]:
    names = (
        "namespace_ref",
        "privacy_class",
        "task_region_ref",
        "population_ref",
        "population_digest",
        "source_occurrence_ref",
        "projection_policy_ref",
        "projection_policy_digest",
        "projection_mode",
        "history_representation_ref",
        "history_representation_digest",
        "history_class",
        "state_ref",
        "state_digest",
        "state_class",
        "outcome_contract_ref",
        "outcome_contract_digest",
        "outcome_ref",
        "outcome_class",
        "evaluator_ref",
        "evaluator_digest",
        "temporal_order_evidence_ref",
        "temporal_order_evidence_digest",
    )
    return {name: values[name] for name in names}


def _sample(
    index: int,
    history_class: str,
    state_class: str,
    outcome_class: str,
    *,
    valid: bool = True,
    history_ref: str = "",
    history_digest: str = "",
    mode: str = DETERMINISTIC_PROJECTION,
) -> PredictiveStateSample:
    history_ref = history_ref or f"history.{index}"
    history_digest = history_digest or _sha(history_ref)
    values: dict[str, object] = {
        "sample_id": f"sample.{index}",
        "namespace_ref": "namespace.fixture",
        "privacy_class": "run_private",
        "task_region_ref": "task-region.fixture",
        "population_ref": "population.fixed/v1",
        "population_digest": _sha("population.fixed/v1"),
        "source_occurrence_ref": f"source-occurrence.{index}",
        "projection_policy_ref": "state-policy.fixture/v1",
        "projection_policy_digest": _sha("state-policy.fixture/v1"),
        "projection_mode": mode,
        "history_representation_ref": history_ref,
        "history_representation_digest": history_digest,
        "history_class": history_class,
        "state_ref": f"state.{index}",
        "state_digest": _sha(f"state.{index}:{state_class}"),
        "state_class": state_class,
        "outcome_contract_ref": "outcome-contract/v1",
        "outcome_contract_digest": _sha("outcome-contract/v1"),
        "outcome_ref": f"outcome.{index}" if valid else "",
        "outcome_class": outcome_class if valid else "",
        "evaluator_ref": "evaluator.fixture/v1",
        "evaluator_digest": _sha("evaluator.fixture/v1"),
        "temporal_order_evidence_ref": f"temporal.{index}",
        "temporal_order_evidence_digest": _sha(f"temporal.{index}"),
        "evidence_refs": (f"evidence:sample:{index}",),
    }
    validity_record = InfrastructureValidityRecord(
        record_id=f"validity.sample.{index}",
        subject_ref=str(values["source_occurrence_ref"]),
        subject_digest=_content_digest(_sample_subject(values)),
        evaluator_ref=str(values["evaluator_ref"]),
        evaluator_digest=str(values["evaluator_digest"]),
        status="valid" if valid else "invalid",
        reason_code="" if valid else "provider_transport_invalid",
        evidence_refs=(f"evidence:validity:{index}",),
    )
    values["validity_record"] = validity_record
    return PredictiveStateSample(**values)


def _trial_subject(values: dict[str, object]) -> dict[str, object]:
    names = (
        "namespace_ref",
        "privacy_class",
        "task_region_ref",
        "population_ref",
        "population_digest",
        "pair_source_ref",
        "source_state_digest",
        "full_history_policy_ref",
        "state_policy_ref",
        "model_profile_ref",
        "model_profile_digest",
        "evaluator_ref",
        "evaluator_digest",
        "outcome_contract_ref",
        "outcome_contract_digest",
        "control_occurrence_ref",
        "treatment_occurrence_ref",
        "control_outcome_ref",
        "treatment_outcome_ref",
        "control_context_bytes",
        "treatment_context_bytes",
        "control_loss",
        "treatment_loss",
        "control_false_acceptance",
        "treatment_false_acceptance",
        "control_cost_usd",
        "treatment_cost_usd",
        "control_latency_seconds",
        "treatment_latency_seconds",
    )
    return {name: values[name] for name in names}


def _trial(
    index: int,
    control_loss: float,
    treatment_loss: float,
    *,
    valid: bool = True,
    context_bytes: tuple[int, int] = (1000, 250),
) -> PairedStatePolicyTrial:
    values: dict[str, object] = {
        "trial_id": f"trial.{index}",
        "namespace_ref": "namespace.fixture",
        "privacy_class": "run_private",
        "task_region_ref": "task-region.fixture",
        "population_ref": "population.fixed/v1",
        "population_digest": _sha("population.fixed/v1"),
        "pair_source_ref": f"pair-source.{index}",
        "source_state_digest": _sha(f"source-state.{index}"),
        "full_history_policy_ref": "context.full/v1",
        "state_policy_ref": "context.state/v1",
        "model_profile_ref": "model.fixture/v1",
        "model_profile_digest": _sha("model.fixture/v1"),
        "evaluator_ref": "evaluator.fixture/v1",
        "evaluator_digest": _sha("evaluator.fixture/v1"),
        "outcome_contract_ref": "outcome-contract/v1",
        "outcome_contract_digest": _sha("outcome-contract/v1"),
        "control_occurrence_ref": f"occurrence.control.{index}",
        "treatment_occurrence_ref": f"occurrence.treatment.{index}",
        "control_outcome_ref": f"outcome.control.{index}" if valid else "",
        "treatment_outcome_ref": f"outcome.treatment.{index}" if valid else "",
        "control_context_bytes": context_bytes[0],
        "treatment_context_bytes": context_bytes[1],
        "control_loss": control_loss if valid else 0.0,
        "treatment_loss": treatment_loss if valid else 0.0,
        "control_false_acceptance": False,
        "treatment_false_acceptance": False,
        "evidence_refs": (f"evidence:trial:{index}",),
        "control_cost_usd": None,
        "treatment_cost_usd": None,
        "control_latency_seconds": None,
        "treatment_latency_seconds": None,
    }
    validity_record = InfrastructureValidityRecord(
        record_id=f"validity.trial.{index}",
        subject_ref=str(values["pair_source_ref"]),
        subject_digest=_content_digest(_trial_subject(values)),
        evaluator_ref=str(values["evaluator_ref"]),
        evaluator_digest=str(values["evaluator_digest"]),
        status="valid" if valid else "invalid",
        reason_code="" if valid else "provider_transport_invalid",
        evidence_refs=(f"evidence:trial-validity:{index}",),
    )
    values["validity_record"] = validity_record
    return PairedStatePolicyTrial(**values)


def _tolerance(*, maximum_treatment_loss: float = 0.25) -> StatePolicyTolerance:
    return StatePolicyTolerance(
        policy_id="tolerance.fixture",
        version="1.0.0",
        minimum_valid_pairs=2,
        maximum_mean_excess_loss=0.05,
        maximum_treatment_loss=maximum_treatment_loss,
        maximum_false_acceptance_delta=0.0,
        maximum_treatment_false_acceptance_rate=0.0,
        minimum_aggregate_compression_ratio=3.0,
    )


def _refused(operation) -> bool:
    try:
        operation()
    except (InformationTheoryEvidenceError, OverflowError, TypeError, ValueError):
        return True
    return False


def self_test() -> dict[str, object]:
    tests: list[dict[str, object]] = []

    def check(name: str, passed: object) -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": ""})

    predictive_spec = _measurement("predictive_state_information")
    samples = (
        _sample(0, "history-a", "state-a", "outcome-a"),
        _sample(1, "history-b", "state-b", "outcome-b"),
        _sample(2, "history-a", "state-a", "outcome-a"),
        _sample(3, "history-b", "state-b", "outcome-b"),
    )
    result = estimate_predictive_information(samples, predictive_spec)
    check(
        "validity_is_derived_from_a_digest_bound_typed_record",
        all(item.infrastructure_valid for item in samples)
        and all(
            item.validity_record.subject_digest == item.validity_subject_digest
            for item in samples
        ),
    )
    check(
        "renaming_a_duplicate_physical_sample_does_not_count_it_twice",
        _refused(
            lambda: estimate_predictive_information(
                (*samples, replace(samples[0], sample_id="sample.relabel")),
                predictive_spec,
            )
        ),
    )
    shared_history_ref = "history.shared"
    shared_history_digest = _sha(shared_history_ref)
    conflicting_history = (
        _sample(
            10,
            "history-label-a",
            "state-a",
            "outcome-a",
            history_ref=shared_history_ref,
            history_digest=shared_history_digest,
        ),
        _sample(
            11,
            "history-label-b",
            "state-b",
            "outcome-b",
            history_ref=shared_history_ref,
            history_digest=shared_history_digest,
        ),
    )
    check(
        "one_exact_history_cannot_be_relabelled_into_conflicting_projections",
        _refused(
            lambda: estimate_predictive_information(
                conflicting_history,
                replace(predictive_spec, minimum_valid_population_coverage=1.0),
            )
        ),
    )
    check(
        "a_changed_validity_status_cannot_reuse_the_old_subject_record",
        _refused(
            lambda: replace(
                samples[0],
                outcome_ref="",
                outcome_class="",
                validity_record=replace(
                    samples[0].validity_record,
                    status="invalid",
                    reason_code="provider_transport_invalid",
                ),
            )
        ),
    )
    check(
        "sample_validity_record_binds_semantic_labels_and_projection_values",
        _refused(lambda: replace(samples[0], outcome_class="outcome-changed"))
        and _refused(lambda: replace(samples[0], state_class="state-changed"))
        and _refused(
            lambda: replace(samples[0], projection_policy_ref="policy.changed/v1")
        ),
    )
    check(
        "optional_validity_and_outcome_text_fields_remain_typed",
        _refused(
            lambda: replace(samples[0].validity_record, reason_code=None)
        )
        and _refused(lambda: replace(samples[0], outcome_ref=None)),
    )
    low_coverage = (
        samples[0],
        samples[1],
        _sample(20, "h", "s", "o", valid=False),
        _sample(21, "h", "s", "o", valid=False),
        _sample(22, "h", "s", "o", valid=False),
        _sample(23, "h", "s", "o", valid=False),
    )
    check(
        "predeclared_predictive_population_coverage_blocks_high_attrition",
        _refused(
            lambda: estimate_predictive_information(low_coverage, predictive_spec)
        ),
    )
    check(
        "an_arbitrary_estimator_contract_digest_is_refused",
        _refused(
            lambda: replace(
                predictive_spec,
                estimator_contract_digest=_sha("arbitrary-estimator"),
            )
        ),
    )
    stochastic = estimate_predictive_information(
        tuple(
            _sample(
                index,
                item.history_class,
                item.state_class,
                item.outcome_class,
                mode=STOCHASTIC_PROJECTION,
            )
            for index, item in enumerate(samples)
        ),
        predictive_spec,
    )
    check(
        "stochastic_projection_does_not_emit_a_deterministic_residual",
        stochastic.residual_predictive_information_bits is None
        and not stochastic.residual_predictive_information_interpretation_applicable
        and stochastic.data_processing_inequality_holds is None,
    )
    stochastic_shared_history = (
        _sample(
            24,
            "history-shared",
            "state-a",
            "outcome-a",
            history_ref="history.stochastic-shared",
            history_digest=_sha("history.stochastic-shared"),
            mode=STOCHASTIC_PROJECTION,
        ),
        _sample(
            25,
            "history-shared",
            "state-b",
            "outcome-b",
            history_ref="history.stochastic-shared",
            history_digest=_sha("history.stochastic-shared"),
            mode=STOCHASTIC_PROJECTION,
        ),
    )
    stochastic_shared_result = estimate_predictive_information(
        stochastic_shared_history,
        replace(predictive_spec, minimum_valid_population_coverage=1.0),
    )
    check(
        "stochastic_projection_may_map_one_exact_history_to_several_states",
        stochastic_shared_result.sample_count == 2
        and stochastic_shared_result.data_processing_inequality_holds is None,
    )
    check(
        "derived_predictive_aggregate_is_not_publicly_replaceable",
        _refused(lambda: replace(result, sample_count=999))
        and result.to_dict()["issued_measurement"] is False
        and result.to_dict()["source_references_resolved_by_this_record"] is False,
    )

    subnormal_prior = CategoricalDistribution(
        "prior.subnormal",
        "belief/v1",
        (("rare", 5e-324), ("other", 1.0)),
    )
    concentrated = CategoricalDistribution(
        "posterior.concentrated",
        "belief/v1",
        (("rare", 1.0), ("other", 0.0)),
    )
    subnormal_update = InformationUpdateEvidence(
        "update.subnormal",
        "observation.subnormal",
        "evidence.subnormal",
        "rare",
        concentrated,
        subnormal_prior,
        concentrated,
    )
    check(
        "subnormal_prior_produces_finite_strict_json_bayesian_surprise",
        subnormal_update.bayesian_surprise == (1074.0, False)
        and "Infinity" not in json.dumps(subnormal_update.to_dict()),
    )
    near_normalized = CategoricalDistribution(
        "near-normalized",
        "singleton/v1",
        (("only", 0.9999999995),),
    )
    check(
        "accepted_probability_tolerance_is_canonically_normalized",
        near_normalized.probabilities == (("only", 1.0),)
        and near_normalized.entropy_bits == 0.0,
    )

    state_spec = _measurement(
        "paired_state_compression_distortion",
        minimum_valid_population_coverage=0.75,
    )
    check(
        "paired_measurement_uses_its_byte_and_declared_loss_contract",
        state_spec.estimator_ref == "paired_empirical_compression_distortion/v1"
        and state_spec.log_base is None
        and state_spec.units == "bytes_and_declared_loss"
        and _refused(
            lambda: replace(
                state_spec,
                estimator_ref="empirical_plugin_base2/v1",
                estimator_contract_digest=EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST,
                log_base=2.0,
                units="bits",
            )
        ),
    )
    valid_trials = (_trial(0, 0.05, 0.08), _trial(1, 0.10, 0.12))
    assessment = assess_state_policy(
        valid_trials,
        _tolerance(),
        state_spec,
        assessment_id="assessment.valid",
    )
    integer_trial = _trial(2, 100, 100)
    check(
        "integer_measurements_preserve_their_validity_bound_representation",
        integer_trial.control_loss == 100
        and integer_trial.treatment_loss == 100
        and integer_trial.validity_record.subject_digest
        == integer_trial.validity_subject_digest,
    )
    check(
        "paired_assessment_reconciles_aggregate_context_compression",
        assessment.aggregate_context_compression_ratio == 4.0
        and assessment.mean_control_context_bytes
        / assessment.mean_treatment_context_bytes
        == assessment.aggregate_context_compression_ratio,
    )
    check(
        "derived_state_policy_aggregate_is_not_publicly_replaceable",
        _refused(
            lambda: replace(
                assessment,
                mean_control_context_bytes=1.0,
                mean_treatment_context_bytes=1000.0,
                aggregate_context_compression_ratio=10.0,
            )
        )
        and assessment.to_dict()["issued_assessment"] is False,
    )
    high_loss = assess_state_policy(
        (_trial(30, 100.0, 100.0), _trial(31, 100.0, 100.0)),
        _tolerance(maximum_treatment_loss=0.25),
        state_spec,
        assessment_id="assessment.high-absolute-loss",
    )
    check(
        "zero_relative_regret_cannot_hide_unacceptable_absolute_loss",
        high_loss.mean_excess_loss == 0.0
        and high_loss.status == NOT_SUPPORTED_WITHIN_TOLERANCE,
    )
    attrited_trials = (
        *valid_trials,
        *tuple(_trial(index, 0.0, 0.0, valid=False) for index in range(40, 60)),
    )
    attrited = assess_state_policy(
        attrited_trials,
        _tolerance(),
        state_spec,
        assessment_id="assessment.high-attrition",
    )
    check(
        "minimum_pair_count_cannot_hide_high_population_attrition",
        attrited.valid_pairs == 2
        and attrited.valid_population_coverage < 0.1
        and attrited.status == INSUFFICIENT_VALID_EVIDENCE,
    )
    check(
        "unbounded_context_byte_integer_is_refused_before_division",
        _refused(
            lambda: _trial(
                70,
                0.0,
                0.0,
                context_bytes=(10**400, 1),
            )
        ),
    )
    check(
        "paired_validity_record_cannot_bind_a_different_source_subject",
        _refused(
            lambda: replace(
                valid_trials[0],
                pair_source_ref="pair-source.changed",
            )
        ),
    )
    check(
        "paired_validity_record_binds_losses_context_and_false_acceptance",
        _refused(lambda: replace(valid_trials[0], treatment_loss=0.2))
        and _refused(lambda: replace(valid_trials[0], treatment_context_bytes=200))
        and _refused(
            lambda: replace(valid_trials[0], treatment_false_acceptance=True)
        ),
    )
    check(
        "invalid_paired_outcome_references_cannot_use_null_as_empty",
        _refused(
            lambda: replace(
                _trial(71, 0.0, 0.0, valid=False),
                control_outcome_ref=None,
            )
        ),
    )
    check(
        "aggregate_result_types_refuse_public_scalar_construction",
        _refused(lambda: EmpiricalPredictiveInformation())
        and _refused(lambda: StatePolicyAssessment())
        and not hasattr(EmpiricalPredictiveInformation, "_from_calculation")
        and not hasattr(StatePolicyAssessment, "_from_calculation"),
    )

    tests.extend(_forecast_score_checks())
    passed = sum(1 for item in tests if item["passed"])
    return {
        "record_type": "information_theory_adversarial_checks/v1",
        "scope": "offline_passive_evidence_only",
        "provider_calls": 0,
        "tool_calls": 0,
        "storage_writes": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = ("self_test",)
