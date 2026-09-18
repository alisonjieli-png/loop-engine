"""Offline checks for reviewing a failed independent check before repair.

Injected model answers and executor observations exercise the local contract:
grounded classification and confirmation, discrimination against an emptied
subject, check revision, revision validation, and the parent verification
hooks. They make no live-model, Docker-isolation, or task-quality claim.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from . import independent_failure_review as review
from . import independent_verification as verification
from .generated_project import GeneratedProjectInputArtifact
from .independent_judgment import JUDGMENT_COMPARISON
from .independent_verification_checks import (
    _BAD_SOURCE, _GOOD_SOURCE, _proposal, _refused, _sandbox_observation, _services, _subject,
)


def _plan(expected):
    return {"status": "ready", "notes": "An offline failure review fixture.",
            "files": [{"path": "checks/probe.py", "purpose": "Observe the frozen combine function."}],
            "cases": [{"case_id": "addition", "criterion_refs": ["criterion:0"],
                       "purpose": "Observe the supplied function result.",
                       "argv": ["python", "checks/probe.py"], "timeout_seconds": 5,
                       "comparison": "json_equal", "expected": expected}]}


_SOURCE = _proposal()["files"][0]
_APPROVAL = {"valid": True, "criterion_refs": ["criterion:0"], "issues": [],
             "notes": "The probe runs the supplied combine function."}


def _classification(name, evidence, reason):
    return {"classification": name,
            "repair_target": "implementation" if name == "correct_failure" else "none",
            "findings": [{"case_id": "addition", "classification": name,
                          "evidence": evidence, "reason": reason}], "notes": ""}


_WRONG_EXPECTATION = _classification(
    "wrong_expectation", ["subject['combine'](7, 5)", "return left + right"],
    "Seven plus five is twelve, and the case expects thirteen.")
_CORRECT_FAILURE = _classification(
    "correct_failure", ["return left - right"],
    "combine subtracts, so seven and five give two instead of their sum.")
_UNGROUNDED = _classification(
    "wrong_expectation", ["the function obviously returns twelve"], "The case is wrong.")
_CONFIRMED = {"confirmed": True, "evidence": ["return left + right"],
              "reason": "combine adds its arguments, so twelve is their sum."}
_NOT_CONFIRMED = {"confirmed": False, "evidence": ["return left + right"],
                  "reason": "The evidence does not settle the expectation."}


def _executor(executions, *, tautological=False):
    """Observe the subject as the sandbox would; an emptied subject has no combine."""
    def execute(active_request, _context):
        executions.append(active_request)
        source = next((item.content for item in active_request.input_artifacts
                       if item.path == "subject/utility.py"), b"")
        if not source and not tautological:
            observed = _sandbox_observation(active_request, "")
            observed["commands"][0].update(exit_code=1, ok=False, stderr="KeyError: 'combine'")
            return observed
        return _sandbox_observation(
            active_request, "12\n" if tautological or b"left + right" in source else "2\n")
    return execute


def _run(root, source, answers, *, tautological=False):
    services, owner = _services(root, answers)
    request = _subject(services, source=source)
    executions = []
    with patch.object(verification, "execute_generated_project",
                      _executor(executions, tautological=tautological)):
        first = verification.run_independent_verification(request, services, owner)
        result = review.review_failed_independent_check(request, services, owner, first)
        again = review.review_failed_independent_check(request, services, owner, first)
    return services, owner, request, first, result, again, executions


def _revision_checks(check):
    with tempfile.TemporaryDirectory(prefix="loop-failure-review-revise-") as folder:
        services, owner, request, first, result, again, executions = _run(
            Path(folder), _GOOD_SOURCE,
            (_plan(13), _SOURCE, _APPROVAL, _WRONG_EXPECTATION, _CONFIRMED,
             _plan(12), _SOURCE, _APPROVAL))
        summary = result.get("failure_review", {})
        revision, revised = result.get("revision", {}), result.get("report", {})
        check("confirmed_wrong_expectation_is_revised_and_the_revised_check_passes_correct_work",
              first["status"] == "failed" and summary.get("decision") == "revise_check"
              and summary.get("classification") == "wrong_expectation"
              and summary.get("confirmed") is True and revision.get("admitted") is True
              and revised.get("status") == "passed" and services.model_session.calls_used == 8
              and len(executions) == 3, str(result)[:600])
        record = (verification._load(services, revision["revision_ref"])
                  if revision.get("revision_ref") else {})
        design = (verification._load(services, record["plan_attempts"][0]["generation"]["prompt_ref"])
                  if record.get("plan_attempts") else {})
        feedback = design.get("prior_rejected_oracle") or {}
        check("revised_check_design_receives_the_disputed_check_and_its_confirmed_review",
              feedback.get("previous_review", {}).get("source") == "confirmed_failure_review"
              and feedback.get("previous_proposal", {}).get("cases", [{}])[0].get("expected") == 13
              and record.get("known_wrong_subject") == review.KNOWN_WRONG_SUBJECT
              and record.get("admitted") is True, str(feedback)[:400])
        check("original_failed_report_stays_recorded_and_the_revised_report_validates",
              any(item.get("report_digest") == first["report_digest"]
                  for item in services.independent_verification_records)
              and bool(revised)
              and not _refused(lambda: verification.validate_independent_verification(
                  revised, request, services, owner))
              and not _refused(lambda: review.validate_check_revision(revised, services, owner)))
        check("a_failed_report_is_reviewed_once",
              again.get("failure_review", {}).get("decision") == "revise_check"
              and "revision" not in again and services.model_session.calls_used == 8
              and len(services.independent_failure_reviews) == 1, str(again)[:300])
        if revised.get("probe_ref"):
            passing = verification._load(services, revised["execution_ref"])
            forged = {**record, "execution_ref": revised["execution_ref"],
                      "checks": verification._compare(verification._load(
                          services, revised["probe_ref"])["proposal"]["cases"], passing)}
            owner.ledger.record(
                loop_id=owner.loop_id, event="custom", custom_kind="independent_check_revision",
                revision_ref=verification._store(services, forged, "independent_check_revision"),
                admitted=True, revised_probe_digest=revised["probe_ref"]["digest"],
                disputed_probe_digest="forged")
        check("revision_whose_known_wrong_execution_passed_is_refused_at_validation",
              bool(revised) and _refused(lambda: review.validate_check_revision(revised, services, owner)))


def _decision_checks(check):
    for name, source, answers, tautological in (
            ("correct_failure", _BAD_SOURCE, (_plan(12), _SOURCE, _APPROVAL, _CORRECT_FAILURE), False),
            ("not_confirmed", _GOOD_SOURCE,
             (_plan(13), _SOURCE, _APPROVAL, _WRONG_EXPECTATION, _NOT_CONFIRMED), False),
            ("ungrounded", _GOOD_SOURCE, (_plan(13), _SOURCE, _APPROVAL, _UNGROUNDED), False),
            ("non_discriminating", _GOOD_SOURCE,
             (_plan(13), _SOURCE, _APPROVAL, _WRONG_EXPECTATION, _CONFIRMED,
              _plan(12), _SOURCE, _APPROVAL), True),
            ("unavailable", _GOOD_SOURCE, (_plan(13), _SOURCE, _APPROVAL), False)):
        with tempfile.TemporaryDirectory(prefix="loop-failure-review-" + name + "-") as folder:
            services, owner, _request, first, result, _again, executions = _run(
                Path(folder), source, answers, tautological=tautological)
            summary = result.get("failure_review", {})
            cached = services.independent_probe_cache.get(first.get("task_digest"))
            calls = services.model_session.calls_used
            if name == "correct_failure":
                check("correct_failure_names_the_repair_and_keeps_the_check",
                      summary.get("decision") == "repair_work"
                      and summary.get("repair_target") == "implementation"
                      and "revision" not in result and "report" not in result
                      and cached == first["probe_ref"] and calls == 4, str(summary))
            elif name == "not_confirmed":
                check("unconfirmed_check_defect_changes_nothing",
                      summary.get("decision") == "keep_failure" and summary.get("confirmed") is False
                      and "revision" not in result and cached == first["probe_ref"]
                      and calls == 5, str(summary))
            elif name == "ungrounded":
                check("ungrounded_finding_is_neither_confirmed_nor_acted_on",
                      summary.get("decision") == "keep_failure"
                      and summary.get("failure") == "ungrounded_finding"
                      and summary.get("confirmed") is None and calls == 4, str(summary))
            elif name == "non_discriminating":
                events = [event.get("admitted") for event in owner.ledger.events
                          if event.get("custom_kind") == "independent_check_revision"]
                check("revision_that_passes_the_emptied_subject_is_refused_and_the_old_check_returns",
                      result.get("revision", {}).get("admitted") is False and "report" not in result
                      and cached == first["probe_ref"] and len(executions) == 2
                      and events == [False], str(result)[:500])
            else:
                check("unavailable_review_keeps_the_failure_without_raising",
                      summary.get("status") == "unavailable" and summary.get("decision") == "keep_failure"
                      and "unavailable" in summary.get("notes", "") and calls == 3, str(summary))


def _authority_checks(check):
    with tempfile.TemporaryDirectory(prefix="loop-failure-review-authority-") as folder:
        services, owner = _services(Path(folder), (
            _plan(13), _SOURCE, _APPROVAL, _WRONG_EXPECTATION, _CONFIRMED))
        request = _subject(services, source=_GOOD_SOURCE)
        executions = []
        with patch.object(verification, "execute_generated_project", _executor(executions)):
            first = verification.run_independent_verification(request, services, owner)
            services.request.allow_sandbox_commands = False
            result = review.review_failed_independent_check(request, services, owner, first)
        revision = result.get("revision", {})
        check("check_revision_needs_existing_sandbox_authority",
              first["status"] == "failed" and revision.get("admitted") is False
              and "needs existing workspace and sandbox authority" in revision.get("notes", "")
              and len(executions) == 1 and services.model_session.calls_used == 5
              and services.independent_probe_cache.get(first["task_digest"]) == first["probe_ref"],
              str(result)[:400])


def _rule_checks(check):
    from ..strings.verification_prompts import (
        INDEPENDENT_FAILURE_CONFIRMATION_PROMPT, INDEPENDENT_FAILURE_REVIEW_PROMPT)
    exact = {"case_id": "a", "comparison": "json_equal"}
    judged = {"case_id": "b", "comparison": JUDGMENT_COMPARISON}
    printed = {"completed": True, "observed": "A long printed passage."}
    check("known_wrong_rule_counts_a_failed_exact_case_or_an_unquotable_judged_case",
          review.rejects_known_wrong([exact, judged], [{"passed": False}, printed])
          and review.rejects_known_wrong([exact, judged], [{"passed": True},
                                                           {"completed": True, "observed": "  short "}])
          and not review.rejects_known_wrong([exact, judged], [{"passed": True}, printed]))
    failed = [{"case_id": "addition"}]
    texts = ["print(json.dumps(subject['combine'](7, 5)))", "return left + right"]
    other = {**_WRONG_EXPECTATION, "findings": [{**_WRONG_EXPECTATION["findings"][0], "case_id": "other"}]}
    check("classification_needs_one_grounded_finding_for_each_failed_case",
          review.ground_classification({**_WRONG_EXPECTATION, "findings": []}, failed, texts)["failure"]
          == "finding_missing"
          and review.ground_classification(other, failed, texts)["failure"] == "invalid_finding"
          and review.ground_classification(_WRONG_EXPECTATION, failed, texts)["grounded"] is True)
    check("confirmation_must_agree_and_quote_the_reviewed_material",
          review.ground_confirmation(_CONFIRMED, texts)["grounded"] is True
          and review.ground_confirmation(_NOT_CONFIRMED, texts)["failure"] == "not_confirmed"
          and review.ground_confirmation({**_CONFIRMED, "evidence": ["combine adds its arguments"]},
                                         texts)["failure"] == "ungrounded_confirmation"
          and review.ground_confirmation({**_CONFIRMED, "notes": "extra"}, texts)["grounded"] is True)
    with tempfile.TemporaryDirectory(prefix="loop-failure-review-inputs-") as folder:
        services, _owner = _services(Path(folder))
        bodies = {"inputs/data.csv": b"region,amount\nEast,40\n", "report.md": b"The total is 40."}
        refs = {path: services.artifacts.store.put(body, artifact_kind="verification_subject").to_dict()
                for path, body in bodies.items()}
        request = SimpleNamespace(project={"writes": [{"input_artifact": True, "path": "inputs/data.csv"}]})
        report = {"subject": {"inventory": [{"path": path, "authored": False, "artifact_ref": ref}
                                            for path, ref in refs.items()]}}
        excerpts, excluded = review._subject_excerpts(services, request, report)
        emptied = review._known_wrong_inputs(tuple(
            GeneratedProjectInputArtifact("subject/" + path, body) for path, body in bodies.items()), request)
        check("supplied_inputs_are_never_sent_to_a_review_or_emptied",
              [item["path"] for item in excerpts] == ["report.md"]
              and excluded == [{"path": "inputs/data.csv", "reason": "supplied_input"}]
              and [item.content for item in emptied] == [bodies["inputs/data.csv"], b""])
    check("failure_review_prompts_demand_quoted_evidence_and_refuse_the_claim_as_evidence",
          "Give one finding for each failed case" in INDEPENDENT_FAILURE_REVIEW_PROMPT
          and "check_stricter_than_task" in INDEPENDENT_FAILURE_REVIEW_PROMPT
          and "Do not add requirements" in INDEPENDENT_FAILURE_REVIEW_PROMPT
          and "the claim itself is not evidence" in INDEPENDENT_FAILURE_CONFIRMATION_PROMPT)


def _separation_checks(check):
    """A declared route separation confirms a claimed check defect on another route."""
    import json
    from .independent_verification_checks import ModelInvocationRequest
    from .route_separation_checks import _two_route_execution
    with tempfile.TemporaryDirectory(prefix="loop-failure-review-routes-") as folder:
        services, owner = _services(Path(folder))
        services.model_session = _two_route_execution(
            ("producer answer", _plan(13), _SOURCE, _APPROVAL, _WRONG_EXPECTATION, _CONFIRMED,
             _plan(12), _SOURCE, _APPROVAL), max_model_calls=9).start_session()
        services.request.independent_verification_policy = (
            verification.IndependentVerificationPolicy(separate_route=True))
        services.model_session.invoke(ModelInvocationRequest("the producer's own call"), owner)
        request = _subject(services, source=_GOOD_SOURCE)
        executions = []
        with patch.object(verification, "execute_generated_project", _executor(executions)):
            first = verification.run_independent_verification(request, services, owner)
            result = review.review_failed_independent_check(request, services, owner, first)
        record = services.independent_failure_reviews[-1]
        separation = (record.get("confirmation") or {}).get("route_separation") or {}
        routes = [item.route for item in services.model_session.results]
        revised = result.get("report") or {}
        # Calls: 0 producer; 1 to 3 the separated verification; 4 the classification
        # (the review itself is not separated from the producer); 5 the confirmation,
        # separated from the classification's route; 6 to 8 the revision design.
        check("a_declared_separation_confirms_a_claimed_check_defect_on_another_route",
              first["status"] == "failed"
              and (first.get("route_separation") or {}).get("achieved") is True
              and routes[0] == "fixture.producer"
              and routes[1:4] == ["fixture.verifier"] * 3
              and routes[4] == "fixture.producer" and routes[5] == "fixture.verifier"
              and separation.get("required") is True and separation.get("achieved") is True
              and separation.get("producer_routes") == ["fixture.producer"]
              and separation.get("verifier_routes") == ["fixture.verifier"]
              and result.get("failure_review", {}).get("decision") == "revise_check",
              json.dumps({"routes": routes, "separation": separation}))
        # The revised verification reuses the admitted revision without a model
        # call; its producer routes name only the producer's route, never the
        # routes the verifier and the review used on the same session.
        check("a_nested_revision_still_separates_from_the_producer_not_from_the_verifier",
              revised.get("status") == "passed"
              and (revised.get("route_separation") or {}).get("producer_routes") == ["fixture.producer"]
              and (revised.get("route_separation") or {}).get("verifier_routes") == []
              and (revised.get("route_separation") or {}).get("achieved") is True
              and services.model_session.calls_used == 9,
              json.dumps(revised.get("route_separation")))


def _hook_checks(check):
    from ..loop.recursive_loop import Loop
    from . import adaptive_practitioner_verification as adaptive
    owner = Loop("offline failure review hook owner")
    failed, passed, reviewed = {"status": "failed"}, {"status": "passed"}, []
    services = SimpleNamespace(
        request=SimpleNamespace(task="Add two numbers.",
                                independent_verification_policy=verification.IndependentVerificationPolicy()),
        diagnostic=lambda *_args, **_kwargs: None)
    results = [SimpleNamespace(result={"record_type": "generated_project_execution/v1",
                                       "deterministic_checks_passed": True})]
    criteria = [{"criterion_ref": "criterion:0", "text": "combine returns the sum of its two arguments"}]

    def fake_review(_request, _services, _owner, report):
        reviewed.append(report)
        return {"failure_review": {"decision": "revise_check"}, "report": passed}

    with patch.object(adaptive, "run_independent_verification", lambda *_args: failed), \
            patch.object(adaptive, "review_failed_independent_check", fake_review):
        entries = adaptive._run_independent_checks(services, results, criteria, owner)
    check("parent_verification_reviews_a_failed_report_and_uses_the_revised_report",
          reviewed == [failed] and entries[0]["report"] is passed
          and entries[0]["failure_review"]["decision"] == "revise_check", str(entries)[:300])
    record = {"independent_verification_policy": verification.IndependentVerificationPolicy().to_dict(),
              "independent_checks": [{"result_index": 0, "report": passed}],
              "registered_acceptance_criteria": criteria}

    def refuse(*_args):
        raise ValueError("revision refused")

    with patch.object(adaptive, "validate_independent_verification", lambda *_args: None), \
            patch.object(adaptive, "validate_check_revision", refuse):
        refused = _refused(lambda: adaptive._require_independent_checks(record, results, services, owner))
    check("acceptance_validates_a_revised_check_before_it_counts", refused)


def run_checks() -> dict:
    """Exercise the review decisions, the revision, and the parent hooks."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    for label, group in (("revision", _revision_checks), ("decisions", _decision_checks),
                         ("authority", _authority_checks), ("rules", _rule_checks),
                         ("separation", _separation_checks), ("hooks", _hook_checks)):
        try:
            group(check)
        except Exception as exc:
            check("failure_review_" + label + "_fixture_completed", False,
                  type(exc).__name__ + ": " + str(exc))
    passed = sum(item["passed"] for item in tests)
    return {"component": "independent_failure_review", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests), "provider_calls_made": 0,
            "scope": "Offline injected provider and executor contract checks only."}
