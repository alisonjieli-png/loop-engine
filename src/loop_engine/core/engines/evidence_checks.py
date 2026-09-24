"""Offline checks for the engine evidence records and the matched evidence ranking.

Each check names its known-wrong case and passes only when that case is
refused; each removed-guard control deletes one guard and passes only when
its check would then fail. The ranking is compared with the harness selector
it generalizes on the same evidence. No engine, model or network is touched.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import patch

from . import evidence as evidence_module
from ..configuration_capabilities import digest
from ..configuration_preferences import InsufficientEvidence, PreferenceCandidate, PreferenceSnapshot
from .evidence import (
    EngineEvidenceReview, EngineEvidenceRule, EngineEvidenceSnapshot, EngineTrialEvidence, MatchedEvidenceRanking,
    RankedCandidate)
from .records import EngineRecordError

NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)
SCOPE = digest("one exact step scope")
RULE = EngineEvidenceRule("matched_quality_then_efficiency", "tokens", 10, "fixture.evaluator@1.0.0",
                          digest("fixture evaluator"), 30, 200)
ENGINES = (RankedCandidate("alpha", "alpha@1.0.0", digest("alpha installation")),
           RankedCandidate("beta", "beta@1.0.0", digest("beta installation")))


def trial(engine, number, successes, *, tokens=100, population="population-a", scope=SCOPE,
          recorded_at="2026-09-21T12:00:00Z", **changes):
    base = EngineTrialEvidence(
        f"{engine.engine_ref}#{number}", "step_executor", engine.engine_ref, engine.installation_digest, scope,
        digest(population), RULE.evaluator_ref, RULE.evaluator_digest, digest(f"subject {number}"),
        f"history/{engine.installation_id}/{number}", digest(f"history {engine.engine_ref} {number}"),
        "comparison_arm", successes, 2, None if tokens is None else tokens // 2,
        None if tokens is None else tokens - tokens // 2, 3.0, None, recorded_at)
    return replace(base, **changes)


def review(item, **changes):
    base = EngineEvidenceReview(item.content_digest, "independent-reviewer@fixture", "reviews/" + item.trial_id,
                                digest("review " + item.trial_id), "approved")
    return replace(base, **changes)


def snapshot(trials, rule=RULE):
    return EngineEvidenceSnapshot("step_executor", SCOPE, rule, tuple((item, review(item)) for item in trials),
                                  "2026-09-22T00:00:00Z")


def ranked(trials, rule=RULE, objective=""):
    ranking = MatchedEvidenceRanking(snapshot(trials, rule), ENGINES, scope_digest=SCOPE, as_of=NOW,
                                     objective=objective)
    preference = PreferenceSnapshot("engine_installation", SCOPE,
                                    tuple(PreferenceCandidate(item.installation_id) for item in ENGINES))
    try:
        return ranking.rank(preference).ordered_ids
    except InsufficientEvidence:
        return None


def population(alpha_successes, beta_successes, count=10, *, alpha_tokens=100, beta_tokens=100, **changes):
    return ([trial(ENGINES[0], number, alpha_successes, tokens=alpha_tokens, **changes) for number in range(count)]
            + [trial(ENGINES[1], number, beta_successes, tokens=beta_tokens) for number in range(count)])


def _refused(action, code=None) -> bool:
    try:
        action()
    except EngineRecordError as exc:
        return code is None or exc.code == code
    except Exception:
        return False
    return False


def an_evidence_rule_declares_every_threshold() -> bool:
    """Known wrong: a rule relying on a default; a minimum below the lowest floor; the
    paired method declared before it is built; a window that holds fewer records than
    the minimum."""
    record = RULE.to_dict()
    missing = {key: value for key, value in record.items() if key != "maximum_age_days"}
    return (_refused(lambda: EngineEvidenceRule.from_dict(missing), "missing_record_fields")
            and _refused(lambda: replace(RULE, minimum_matched_records=9))
            and _refused(lambda: replace(RULE, method="paired_efficiency_within_loss_margin"),
                         "evidence_method_not_built")
            and _refused(lambda: replace(RULE, maximum_records=9))
            and EngineEvidenceRule.from_dict(record) == RULE)


def a_trial_keeps_unknown_apart_from_zero_and_its_denominator_honest() -> bool:
    """Known wrong: more successes than observations; a first-choice attempt counted as
    ranking evidence; an unknown token count read as zero."""
    unknown = trial(ENGINES[0], 0, 1, tokens=None)
    return (_refused(lambda: trial(ENGINES[0], 0, 3))
            and _refused(lambda: trial(ENGINES[0], 0, 1, selection_path="first_choice"), "invalid_vocabulary")
            and unknown.metric("tokens") is None
            and EngineTrialEvidence.from_dict(unknown.to_dict()) == unknown)


def a_producer_never_reviews_its_own_trial() -> bool:
    """Known wrong: an engine reviewing its own trial; a review bound to another trial; one
    Run History reference counted as two trials."""
    item = trial(ENGINES[0], 0, 1)
    other = trial(ENGINES[0], 1, 1)
    twice = replace(other, history_ref=item.history_ref)
    return (_refused(lambda: EngineEvidenceSnapshot("step_executor", SCOPE, RULE, (
                (item, review(item, reviewer_ref="alpha@1.0.0")),), "2026-09-22T00:00:00Z"), "self_review")
            and _refused(lambda: EngineEvidenceSnapshot("step_executor", SCOPE, RULE, (
                (item, review(other)),), "2026-09-22T00:00:00Z"), "review_binds_another_trial")
            and _refused(lambda: snapshot([item, twice]), "repeated_value")
            and EngineEvidenceSnapshot.from_dict(snapshot([item, other]).to_dict()).content_digest
            == snapshot([item, other]).content_digest)


def below_the_minimum_the_ranking_declines() -> bool:
    """Known wrong: nine matched records per engine order a slot whose rule asks for ten."""
    return ranked(population(1, 2, count=9)) is None and ranked(population(1, 2)) == ("beta", "alpha")


def lower_verified_outcome_never_outranks_on_efficiency() -> bool:
    """Known wrong: a cheaper engine with a lower verified outcome moved first; an engine whose
    token use is unknown winning over a known one."""
    cheaper_worse = ranked(population(2, 1, alpha_tokens=900, beta_tokens=100))
    tie_cheaper = ranked(population(2, 2, alpha_tokens=900, beta_tokens=100))
    unknown_metric = ranked(population(2, 2, alpha_tokens=None, beta_tokens=900))
    return cheaper_worse == ("alpha", "beta") and tie_cheaper == ("beta", "alpha") and unknown_metric == (
        "beta", "alpha")


def evidence_from_another_scope_population_or_window_cannot_rank() -> bool:
    """Known wrong: trials of another scope, a population the other engine never ran, a
    rejected review or trials older than the window counted toward the minimum."""
    foreign_scope = population(1, 2, scope=digest("another scope"))
    split_population = population(1, 2, population="population-b")
    stale = population(1, 2, recorded_at="2026-07-01T00:00:00Z")
    trials = population(1, 2)
    rejected = EngineEvidenceSnapshot("step_executor", SCOPE, RULE, tuple(
        (item, review(item, decision="rejected")) for item in trials), "2026-09-22T00:00:00Z")
    ranking = MatchedEvidenceRanking(rejected, ENGINES, scope_digest=SCOPE, as_of=NOW)
    preference = PreferenceSnapshot("engine_installation", SCOPE,
                                    tuple(PreferenceCandidate(item.installation_id) for item in ENGINES))
    try:
        ranking.rank(preference)
        rejected_ranks = True
    except InsufficientEvidence:
        rejected_ranks = False
    return (ranked(foreign_scope) is None and ranked(split_population) is None and ranked(stale) is None
            and not rejected_ranks)


def the_general_rule_and_select_harness_agree_on_the_same_evidence() -> bool:
    """Known wrong: the lifted rule ordering two harnesses differently from core.harness_selection
    on the same approved, matched evidence."""
    from ..external_harness import HarnessAdapterInfo
    from ..harness_selection import select_harness
    from ..harness_selection_records import (
        HarnessEvidenceReview, HarnessSelectionPolicy, HarnessSelectionScope, HarnessTrialEvidence,
        ReviewedHarnessEvidence)
    scope = HarnessSelectionScope("step_run_request/v1", digest("response"), "practitioner.code_execution@1.0.0",
                                  digest("resources"), digest("settings"), digest("definition"))
    evidence = []
    for name, successes, tokens in (("alpha", 1, 100), ("beta", 2, 300)):
        for number in range(10):
            measured = HarnessTrialEvidence(
                f"{name}#{number}", name, "1.0.0", "fixture.provider", "fixture-model", scope.digest,
                digest("population-a"), RULE.evaluator_ref, RULE.evaluator_digest, digest(f"subject {number}"),
                f"history/{name}/{number}", digest(f"history {name} {number}"), successes, 2, 1,
                tokens // 2, tokens - tokens // 2, 3.0, None)
            evidence.append(ReviewedHarnessEvidence(measured, HarnessEvidenceReview(
                measured.digest, "independent-reviewer@fixture", "reviews/" + name, digest("review"))))
    rules = HarnessSelectionPolicy(digest("resources"), tuple(evidence), 10,
                                   evaluation_contract_ref="response_admission/v1")
    registrations = tuple(HarnessAdapterInfo(name, "1.0.0", "fixture", available=True,
                                             adapter_contract_version="external_harness_adapter/v2",
                                             engine_kind="text_relay_harness",
                                             supported_edge_contracts=("step_run_request/v1",))
                          for name in ("alpha", "beta"))
    harness_order = select_harness(rules, scope, registrations, provider_id="fixture.provider",
                                   model_id="fixture-model").ordered_harness_ids
    general_order = ranked(population(1, 2, alpha_tokens=100, beta_tokens=300))
    return harness_order == general_order == ("beta", "alpha")


CHECKS = (
    ("an_evidence_rule_with_any_missing_threshold_is_refused", an_evidence_rule_declares_every_threshold, ()),
    ("a_trial_keeps_unknown_apart_from_zero_and_its_denominator_honest",
     a_trial_keeps_unknown_apart_from_zero_and_its_denominator_honest, ()),
    ("rejected_review_or_self_review_cannot_rank_an_engine", a_producer_never_reviews_its_own_trial,
     (("removed_self_review_refusal_is_detected", ((evidence_module, "_refuse_self_review"),)),)),
    ("below_the_minimum_the_evidence_ranking_declines", below_the_minimum_the_ranking_declines,
     (("removed_minimum_rule_is_detected", ((evidence_module, "_require_minimum"),)),)),
    ("lower_verified_outcome_never_outranks_on_efficiency", lower_verified_outcome_never_outranks_on_efficiency, ()),
    ("evidence_from_another_scope_cannot_rank", evidence_from_another_scope_population_or_window_cannot_rank,
     (("removed_scope_match_rule_is_detected", ((evidence_module, "_matches", lambda *a, **k: True),)),)),
    ("the_general_rule_and_select_harness_agree_on_the_same_evidence",
     the_general_rule_and_select_harness_agree_on_the_same_evidence, ()),
)


def run_checks() -> dict:
    tests = []
    for name, scenario, controls in CHECKS:
        tests.append({"name": name, "passed": _observe(scenario)})
        for control, removed in controls:
            patches = [patch.object(module, item[1], item[2] if len(item) > 2 else _removed) for item in removed
                       for module in (item[0],)]
            for item in patches:
                item.start()
            try:
                tests.append({"name": control, "passed": _observe(scenario) is False})
            finally:
                for item in patches:
                    item.stop()
    return {"tests": tests, "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def _removed(*_args, **_kwargs):
    return None


def _observe(scenario) -> bool:
    try:
        return bool(scenario())
    except Exception:
        return False


def self_test() -> dict:
    return run_checks()
