"""Offline adversarial checks for passive procedural-control evidence.

The fixtures exercise record identity, scope, behavioral probes, and refusal.
They perform no provider call, storage write, procedure execution, or promotion.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import replace

from ...loop.loop_definition import LoopDefinitionRef
from ..model.memory_type import MemoryIdentity, MemoryType
from .control_assessment import (
    ProceduralControlAssessment,
    ProceduralControlStatus,
    ProceduralProbeEvidence,
    ProceduralProbeKind,
    ProceduralProbeVerdict,
)

_D = {
    "procedure": "a" * 64,
    "positive": "b" * 64,
    "negative": "c" * 64,
    "transfer": "d" * 64,
    "state": "e" * 64,
    "event": "f" * 64,
    "policy": "1" * 64,
    "graph": "2" * 64,
    "definition": "3" * 64,
    "fallback": "4" * 64,
}


def _identity(name: str, digest: str, kind: MemoryType) -> MemoryIdentity:
    return MemoryIdentity(f"memory.{name}", "1.0.0", digest, kind)


def _probe(
    kind: ProceduralProbeKind,
    verdict: ProceduralProbeVerdict = ProceduralProbeVerdict.PASSED,
    *,
    suffix: str = "",
    infrastructure_valid: bool = True,
    invalid_reason: str = "",
    contamination_refs: tuple[str, ...] = (),
) -> ProceduralProbeEvidence:
    name = f"{kind.value}{suffix}"
    common = {
        "probe_id": f"probe.{name}",
        "probe_kind": kind,
        "task_region_ref": "task-region.fixture",
        "source_state_digest": _D["state"],
        "expected_behavior_ref": f"expected.{name}",
        "occurrence_refs": (f"occurrence.{name}",),
        "outcome_refs": (f"outcome.{name}",),
        "run_history_event_digests": (
            hashlib.sha256(f"event.{name}".encode()).hexdigest(),
        ),
        "evaluator_loop_ref": "loop.independent-assessor",
        "evaluator_policy_ref": "policy.procedural-control@1.0.0",
        "evaluator_policy_digest": _D["policy"],
        "verdict": verdict,
        "evidence_refs": (f"evidence.{name}",),
        "infrastructure_valid": infrastructure_valid,
        "invalid_reason": invalid_reason,
        "contamination_refs": contamination_refs,
    }
    if kind is ProceduralProbeKind.FRESH_CONTROL:
        common.update(
            {
                "occurrence_refs": (
                    f"occurrence.{name}.control",
                    f"occurrence.{name}.treatment",
                ),
                "outcome_refs": (
                    f"outcome.{name}.control",
                    f"outcome.{name}.treatment",
                ),
                "experiment_ref": f"experiment.{name}",
                "experiment_digest": "7" * 64,
                "control_occurrence_ref": f"occurrence.{name}.control",
                "treatment_occurrence_ref": f"occurrence.{name}.treatment",
                "control_outcome_ref": f"outcome.{name}.control",
                "treatment_outcome_ref": f"outcome.{name}.treatment",
            }
        )
    if not infrastructure_valid:
        common["outcome_refs"] = ()
        if kind is ProceduralProbeKind.FRESH_CONTROL:
            common["control_outcome_ref"] = ""
            common["treatment_outcome_ref"] = ""
    return ProceduralProbeEvidence(**common)


def _probes() -> tuple[ProceduralProbeEvidence, ...]:
    return tuple(_probe(kind) for kind in ProceduralProbeKind)


def _assessment(**changes) -> ProceduralControlAssessment:
    positive = _identity("positive", _D["positive"], MemoryType.EPISODIC)
    negative = _identity("negative", _D["negative"], MemoryType.EPISODIC)
    transfer = _identity("transfer", _D["transfer"], MemoryType.EPISODIC)
    values = {
        "assessment_id": "assessment.fixture",
        "version": "1.0.0",
        "procedure_identity": _identity(
            "procedure", _D["procedure"], MemoryType.PROCEDURAL
        ),
        "procedure_loop_definition_ref": LoopDefinitionRef(
            "solution.procedure.fixture", "1.0.0", _D["definition"]
        ),
        "producer_loop_ref": "loop.producer",
        "assessor_loop_refs": ("loop.independent-assessor",),
        "assessment_policy_ref": "policy.procedural-control@1.0.0",
        "assessment_policy_digest": _D["policy"],
        "task_region_scope": ("task-region.fixture",),
        "cognitive_phase_scope": ("execution", "verification"),
        "semantic_signature_scope": ("semantic.fixture",),
        "shape_signature_scope": ("shape.fixture",),
        "motif_signature_scope": ("execution/knowns",),
        "segment_signature_scope": ("segment:sha256:0123456789abcdef",),
        "graph_definition_digests": (_D["graph"],),
        "positive_episode_identities": (positive,),
        "negative_episode_identities": (negative, transfer),
        "negative_transfer_episode_identities": (transfer,),
        "probes": _probes(),
        "deliberative_fallback_ref": LoopDefinitionRef(
            "practitioner.deliberative.fallback", "1.0.0", _D["fallback"]
        ),
        "evidence_refs": ("run-history.fixture", "experiment.fixture"),
        "limitations": ("offline fixture only",),
        "confidence": 0.75,
    }
    values.update(changes)
    return ProceduralControlAssessment(**values)


def _refused(operation) -> bool:
    try:
        operation()
    except (TypeError, ValueError):
        return True
    return False


def self_test() -> dict[str, object]:
    """Exercise successful, incomplete, failed, and adversarial evidence."""
    tests: list[dict[str, object]] = []

    def check(name: str, passed: object, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    assessment = _assessment()
    serialized = assessment.to_dict()
    check(
        "all_seven_behavioral_boundaries_are_represented",
        {item.probe_kind for item in assessment.probes}
        == set(ProceduralProbeKind),
    )
    check(
        "complete_valid_evidence_remains_pending_reference_resolution",
        assessment.status
        is ProceduralControlStatus.CANDIDATE_SUPPORT_PENDING_RESOLUTION,
    )
    relabeled_candidate = _assessment(
        procedure_identity=_identity(
            "unresolved-procedure", "8" * 64, MemoryType.PROCEDURAL
        ),
        task_region_scope=("task-region.unresolved", "task-region.fixture"),
    )
    check(
        "caller_authored_scope_and_procedure_can_never_produce_resolved_support",
        relabeled_candidate.status
        is ProceduralControlStatus.CANDIDATE_SUPPORT_PENDING_RESOLUTION
        and relabeled_candidate.to_dict()["promotion_authorized"] is False
        and relabeled_candidate.to_dict()["generalization_claimed"] is False,
    )
    check(
        "procedure_and_fallback_bind_exact_existing_reference_types",
        assessment.procedure_identity.memory_type is MemoryType.PROCEDURAL
        and isinstance(assessment.procedure_loop_definition_ref, LoopDefinitionRef)
        and isinstance(assessment.deliberative_fallback_ref, LoopDefinitionRef),
    )
    check(
        "assessment_serialization_explicitly_grants_no_authority",
        serialized["grants_authority"] is False
        and serialized["promotion_authorized"] is False
        and serialized["generalization_claimed"] is False,
    )
    check(
        "strict_round_trip_preserves_identity_status_and_digest",
        ProceduralControlAssessment.from_dict(serialized) == assessment
        and ProceduralControlAssessment.from_dict(serialized).content_digest
        == assessment.content_digest,
    )
    first_probe = assessment.probes[0]
    check(
        "probe_round_trip_is_strict_and_digest_bound",
        ProceduralProbeEvidence.from_dict(first_probe.to_dict()) == first_probe,
    )
    check(
        "positive_negative_and_transfer_evidence_remain_distinct",
        set(assessment.positive_episode_identities).isdisjoint(
            assessment.negative_episode_identities
        )
        and set(assessment.negative_transfer_episode_identities)
        <= set(assessment.negative_episode_identities),
    )

    check(
        "non_procedural_procedure_identity_is_refused",
        _refused(
            lambda: _assessment(
                procedure_identity=_identity(
                    "wrong", _D["procedure"], MemoryType.SEMANTIC
                )
            )
        ),
    )
    check(
        "non_episodic_episode_identity_is_refused",
        _refused(
            lambda: _assessment(
                positive_episode_identities=(
                    _identity("wrong", _D["positive"], MemoryType.PROCEDURAL),
                )
            )
        ),
    )
    shared = _identity("shared", "5" * 64, MemoryType.EPISODIC)
    check(
        "positive_and_negative_episode_overlap_is_refused",
        _refused(
            lambda: _assessment(
                positive_episode_identities=(shared,),
                negative_episode_identities=(shared,),
                negative_transfer_episode_identities=(),
            )
        ),
    )
    aliased_positive = _identity("positive-alias", _D["negative"], MemoryType.EPISODIC)
    check(
        "one_episode_digest_cannot_be_aliased_across_outcome_classes",
        _refused(
            lambda: _assessment(
                positive_episode_identities=(aliased_positive,)
            )
        ),
    )
    outsider = _identity("outsider", "6" * 64, MemoryType.EPISODIC)
    check(
        "negative_transfer_must_be_part_of_negative_evidence",
        _refused(
            lambda: _assessment(negative_transfer_episode_identities=(outsider,))
        ),
    )
    check(
        "procedure_producer_cannot_assess_itself",
        _refused(lambda: _assessment(assessor_loop_refs=("loop.producer",))),
    )
    check(
        "duplicate_assessors_are_refused",
        _refused(
            lambda: _assessment(
                assessor_loop_refs=(
                    "loop.independent-assessor",
                    "loop.independent-assessor",
                )
            )
        ),
    )
    check(
        "procedure_cannot_be_its_own_deliberative_fallback",
        _refused(
            lambda: _assessment(
                deliberative_fallback_ref=assessment.procedure_loop_definition_ref
            )
        ),
    )
    check(
        "undeclared_probe_evaluator_is_refused",
        _refused(
            lambda: _assessment(
                probes=(
                    replace(first_probe, evaluator_loop_ref="loop.undeclared"),
                    *assessment.probes[1:],
                )
            )
        ),
    )
    check(
        "probe_outside_declared_task_region_is_refused",
        _refused(
            lambda: _assessment(
                probes=(
                    replace(first_probe, task_region_ref="task-region.other"),
                    *assessment.probes[1:],
                )
            )
        ),
    )
    check(
        "probe_with_different_evaluator_policy_is_refused",
        _refused(
            lambda: _assessment(
                probes=(
                    replace(first_probe, evaluator_policy_digest="8" * 64),
                    *assessment.probes[1:],
                )
            )
        ),
    )

    missing_termination = tuple(
        item
        for item in assessment.probes
        if item.probe_kind is not ProceduralProbeKind.TERMINATION
    )
    check(
        "missing_required_probe_is_insufficient_not_supported",
        _assessment(probes=missing_termination).status
        is ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE,
    )
    for kind in (
        ProceduralProbeKind.INTERRUPTION,
        ProceduralProbeKind.OUTCOME_DEVALUATION,
        ProceduralProbeKind.NEGATIVE_TRANSFER,
        ProceduralProbeKind.FRESH_CONTROL,
        ProceduralProbeKind.DELIBERATIVE_FALLBACK,
    ):
        failed = tuple(
            _probe(kind, ProceduralProbeVerdict.FAILED, suffix=".failed")
            if item.probe_kind is kind
            else item
            for item in assessment.probes
        )
        check(
            f"failed_{kind.value}_gate_prevents_support",
            _assessment(probes=failed).status
            is ProceduralControlStatus.NOT_SUPPORTED_WITHIN_DECLARED_SCOPE,
        )
    contradicted = (
        *assessment.probes,
        _probe(
            ProceduralProbeKind.OUTCOME_DEVALUATION,
            ProceduralProbeVerdict.FAILED,
            suffix=".contradiction",
        ),
    )
    check(
        "passing_and_failed_evidence_for_one_boundary_is_contradicted",
        _assessment(probes=contradicted).status
        is ProceduralControlStatus.CONTRADICTED,
    )
    inconclusive = tuple(
        _probe(
            ProceduralProbeKind.TERMINATION,
            ProceduralProbeVerdict.INCONCLUSIVE,
            suffix=".unknown",
        )
        if item.probe_kind is ProceduralProbeKind.TERMINATION
        else item
        for item in assessment.probes
    )
    check(
        "inconclusive_is_unknown_not_failed",
        _assessment(probes=inconclusive).status
        is ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE,
    )
    invalid = tuple(
        _probe(
            ProceduralProbeKind.INITIATION,
            ProceduralProbeVerdict.INFRASTRUCTURE_INVALID,
            suffix=".invalid",
            infrastructure_valid=False,
            invalid_reason="provider request did not execute",
        )
        if item.probe_kind is ProceduralProbeKind.INITIATION
        else item
        for item in assessment.probes
    )
    check(
        "infrastructure_invalid_probe_does_not_count_as_failure_or_coverage",
        _assessment(probes=invalid).status
        is ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE,
    )
    check(
        "invalid_reason_and_infrastructure_verdict_must_agree",
        _refused(
            lambda: _probe(
                ProceduralProbeKind.INITIATION,
                ProceduralProbeVerdict.INFRASTRUCTURE_INVALID,
            )
        )
        and _refused(
            lambda: _probe(
                ProceduralProbeKind.INITIATION,
                ProceduralProbeVerdict.PASSED,
                infrastructure_valid=False,
                invalid_reason="transport invalid",
            )
        ),
    )
    failed_probe = _probe(
        ProceduralProbeKind.INITIATION,
        ProceduralProbeVerdict.FAILED,
        suffix=".laundering",
    )
    check(
        "failed_semantic_outcome_cannot_be_laundered_as_infrastructure_invalid",
        _refused(
            lambda: replace(
                failed_probe,
                verdict=ProceduralProbeVerdict.INFRASTRUCTURE_INVALID,
                infrastructure_valid=False,
                invalid_reason="provider request did not execute",
            )
        ),
    )

    contaminated = tuple(
        _probe(
            ProceduralProbeKind.FRESH_CONTROL,
            ProceduralProbeVerdict.INFRASTRUCTURE_INVALID,
            suffix=".contaminated",
            infrastructure_valid=False,
            invalid_reason="fresh control contained prior-derived context",
            contamination_refs=("context.prior-derived-template",),
        )
        if item.probe_kind is ProceduralProbeKind.FRESH_CONTROL
        else item
        for item in assessment.probes
    )
    check(
        "contaminated_fresh_control_is_excluded_as_infrastructure_invalid",
        _assessment(probes=contaminated).status
        is ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE,
    )
    check(
        "contaminated_fresh_control_cannot_claim_passed",
        _refused(
            lambda: _probe(
                ProceduralProbeKind.FRESH_CONTROL,
                contamination_refs=("context.prior-derived-template",),
            )
        ),
    )
    fresh = next(
        item
        for item in assessment.probes
        if item.probe_kind is ProceduralProbeKind.FRESH_CONTROL
    )
    check(
        "fresh_control_requires_distinct_occurrences",
        _refused(
            lambda: replace(
                fresh,
                occurrence_refs=("occurrence.same",),
                control_occurrence_ref="occurrence.same",
                treatment_occurrence_ref="occurrence.same",
            )
        ),
    )
    check(
        "fresh_control_requires_experiment_identity",
        _refused(lambda: replace(fresh, experiment_ref="")),
    )
    check(
        "fresh_control_pair_must_match_occurrence_refs",
        _refused(
            lambda: replace(fresh, occurrence_refs=("occurrence.unrelated",))
        ),
    )
    check(
        "fresh_control_pair_must_match_independent_outcome_refs",
        _refused(
            lambda: replace(fresh, outcome_refs=("outcome.unrelated",))
        )
        and _refused(
            lambda: replace(
                fresh,
                outcome_refs=("outcome.same",),
                control_outcome_ref="outcome.same",
                treatment_outcome_ref="outcome.same",
            )
        ),
    )
    check(
        "non_fresh_probe_cannot_smuggle_control_fields",
        _refused(
            lambda: replace(
                first_probe,
                experiment_ref="experiment.hidden",
                control_occurrence_ref="occurrence.control",
                treatment_occurrence_ref="occurrence.treatment",
            )
        )
        and _refused(lambda: replace(first_probe, experiment_ref=None)),
    )

    check(
        "missing_positive_negative_or_transfer_population_is_insufficient",
        _assessment(positive_episode_identities=()).status
        is ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE
        and _assessment(
            negative_episode_identities=(),
            negative_transfer_episode_identities=(),
        ).status
        is ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE
        and _assessment(negative_transfer_episode_identities=()).status
        is ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE,
    )
    check(
        "string_as_sequence_is_refused",
        _refused(lambda: _assessment(assessor_loop_refs="loop.assessor"))
        and _refused(lambda: _assessment(evidence_refs="evidence.one"))
        and _refused(lambda: replace(first_probe, occurrence_refs="occurrence.one")),
    )
    check(
        "mapping_as_sequence_is_refused",
        _refused(lambda: _assessment(assessor_loop_refs={"loop": "assessor"}))
        and _refused(
            lambda: replace(first_probe, occurrence_refs={"occurrence": "one"})
        ),
    )
    check(
        "unordered_sets_are_refused_before_digest_construction",
        _refused(
            lambda: _assessment(
                semantic_signature_scope={"semantic.a", "semantic.b"}
            )
        )
        and _refused(lambda: replace(first_probe, evidence_refs={"a", "b"})),
    )
    check(
        "nonfinite_and_out_of_range_confidence_are_refused",
        _refused(lambda: _assessment(confidence=float("nan")))
        and _refused(lambda: _assessment(confidence=float("inf")))
        and _refused(lambda: _assessment(confidence=1.1)),
    )
    check(
        "control_characters_are_refused",
        _refused(lambda: _assessment(assessment_id="assessment\nforged"))
        and _refused(
            lambda: replace(first_probe, evidence_refs=("evidence\tforged",))
        ),
    )
    check(
        "malformed_exact_digests_are_refused",
        _refused(lambda: _assessment(graph_definition_digests=("ABC",)))
        and _refused(
            lambda: _assessment(
                procedure_identity=_identity(
                    "procedure", "not-a-digest", MemoryType.PROCEDURAL
                )
            )
        ),
    )
    check(
        "unknown_probe_kind_and_verdict_are_refused",
        _refused(lambda: replace(first_probe, probe_kind="habit"))
        and _refused(lambda: replace(first_probe, verdict="unknown")),
    )
    check(
        "duplicate_probe_identity_is_refused",
        _refused(lambda: _assessment(probes=(first_probe, first_probe))),
    )
    reused = replace(
        _probe(ProceduralProbeKind.TERMINATION),
        occurrence_refs=first_probe.occurrence_refs,
    )
    check(
        "one_observation_cannot_be_relabelled_across_probe_kinds",
        _refused(lambda: _assessment(probes=(first_probe, reused))),
    )
    check(
        "fresh_control_reference_order_is_canonical",
        _refused(
            lambda: replace(
                fresh,
                occurrence_refs=tuple(reversed(fresh.occurrence_refs)),
                outcome_refs=tuple(reversed(fresh.outcome_refs)),
            )
        ),
    )
    check(
        "bad_assessment_version_is_refused",
        _refused(lambda: _assessment(version="latest")),
    )

    forged_status = copy.deepcopy(serialized)
    forged_status["status"] = "not_supported_within_declared_scope"
    check(
        "caller_cannot_assert_status_that_contradicts_evidence",
        _refused(lambda: ProceduralControlAssessment.from_dict(forged_status)),
    )
    forged_authority = copy.deepcopy(serialized)
    forged_authority["promotion_authorized"] = True
    check(
        "serialized_assessment_cannot_grant_promotion",
        _refused(lambda: ProceduralControlAssessment.from_dict(forged_authority)),
    )
    changed_identity = copy.deepcopy(serialized)
    changed_identity["procedure_identity"]["content_digest"] = "9" * 64
    check(
        "changed_procedure_identity_without_resigning_is_refused",
        _refused(lambda: ProceduralControlAssessment.from_dict(changed_identity)),
    )
    changed_definition = copy.deepcopy(serialized)
    changed_definition["procedure_loop_definition_ref"]["content_digest"] = "8" * 64
    check(
        "changed_loop_definition_without_resigning_is_refused",
        _refused(lambda: ProceduralControlAssessment.from_dict(changed_definition)),
    )
    changed_probe = copy.deepcopy(serialized)
    changed_probe["probes"][0]["verdict"] = "failed"
    check(
        "changed_nested_probe_without_resigning_is_refused",
        _refused(lambda: ProceduralControlAssessment.from_dict(changed_probe)),
    )
    extra = copy.deepcopy(serialized)
    extra["hidden_route"] = "execute"
    check(
        "unknown_serialized_field_is_refused",
        _refused(lambda: ProceduralControlAssessment.from_dict(extra)),
    )
    missing = copy.deepcopy(serialized)
    missing.pop("evidence_refs")
    check(
        "missing_serialized_field_is_refused",
        _refused(lambda: ProceduralControlAssessment.from_dict(missing)),
    )
    bad_probe = first_probe.to_dict()
    bad_probe["grants_authority"] = True
    check(
        "serialized_probe_cannot_grant_authority",
        _refused(lambda: ProceduralProbeEvidence.from_dict(bad_probe)),
    )

    passed = sum(1 for item in tests if item["passed"])
    return {
        "record_type": "procedural_control_assessment_checks/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
        "provider_calls": 0,
        "storage_writes": 0,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(self_test(), indent=2))


__all__ = ("self_test",)
