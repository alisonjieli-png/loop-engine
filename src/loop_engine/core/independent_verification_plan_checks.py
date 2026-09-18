"""Invalid-plan feedback, response format repair, criterion judgment, and a Docker verifier probe.

The folded checks use declared fixtures. The separate opt-in qualification
executes the existing verifier in Docker without a real model call.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ..code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution)
from . import independent_verification as verification
from .generated_project import GeneratedProjectCommand, GeneratedProjectFile, GeneratedProjectManifest
from .independent_judgment import JUDGMENT_COMPARISON, JUDGMENT_RECORD_TYPE
from .independent_probe_planning import InvalidProbePlan, validate_probe_plan
from .independent_verification_checks import (
    _CRITERIA, _GOOD_SOURCE, _proposal, _refused, _sandbox_observation, _services, _subject,
)


def _plans():
    criteria = _CRITERIA + (("criterion:1", "The returned value is numeric."),)
    missing = _proposal()
    missing["files"] = [{"path": "checks/probe.py", "purpose": "Observe the frozen combine function."}]
    corrected = deepcopy(missing)
    corrected["cases"].append({**corrected["cases"][0], "case_id": "numeric",
                               "criterion_refs": ["criterion:1"], "purpose": "Observe its numeric result."})
    source = _proposal()["files"][0]
    review = {"valid": True, "criterion_refs": ["criterion:0", "criterion:1"], "issues": [],
              "notes": "Both observations exercise the actual function and compare a numeric sum."}
    return criteria, missing, corrected, source, review


def run_plan_checks(check):
    criteria, missing, corrected, source, review = _plans()
    diagnostic = None
    try:
        validate_probe_plan(missing, criteria)
    except InvalidProbePlan as exc:
        diagnostic = exc.diagnostic.to_dict()
    check("invalid_plan_diagnostic_names_missing_criteria_without_padding",
          diagnostic is not None and diagnostic["missing_criteria"] == ["criterion:1"]
          and diagnostic["unknown_criteria"] == []
          and missing["cases"][0]["criterion_refs"] == ["criterion:0"])
    unknown = deepcopy(missing)
    unknown["cases"][0]["criterion_refs"] = ["criterion:foreign"]
    try:
        validate_probe_plan(unknown, criteria)
        unknown_diagnostic = None
    except InvalidProbePlan as exc:
        unknown_diagnostic = exc.diagnostic
    check("invalid_plan_diagnostic_names_unknown_and_missing_criteria",
          unknown_diagnostic is not None and unknown_diagnostic.unknown_criteria == ("criterion:foreign",)
          and unknown_diagnostic.missing_criteria == ("criterion:0", "criterion:1"))
    textual_timeout = deepcopy(corrected)
    textual_timeout["cases"][0]["timeout_seconds"] = "10"
    try:
        validate_probe_plan(textual_timeout, criteria)
        timeout_diagnostic = None
    except InvalidProbePlan as exc:
        timeout_diagnostic = exc.diagnostic
    check("invalid_case_diagnostic_names_the_case_and_the_field_to_repair",
          timeout_diagnostic is not None and timeout_diagnostic.code == "invalid_case_execution"
          and repr(textual_timeout["cases"][0]["case_id"]) in timeout_diagnostic.detail
          and "timeout_seconds must be a positive JSON number" in timeout_diagnostic.detail
          and '"10"' in timeout_diagnostic.detail and timeout_diagnostic.repairable
          and validate_probe_plan(corrected, criteria) is not None)
    check("plan_attempt_policy_is_explicit_positive_and_versioned",
          verification.IndependentVerificationPolicy().maximum_plan_attempts == 2
          and verification.IndependentVerificationPolicy(maximum_plan_attempts=5).to_dict()["record_type"]
          == "independent_verification_policy/v2"
          and all(_refused(lambda value=value: verification.IndependentVerificationPolicy(maximum_plan_attempts=value))
                  for value in (None, 0, -1, True, 1.5, "2")))

    for mode in ("repaired", "repeated_invalid", "budget_exhausted", "one_attempt",
                 "explicit_unavailable", "review_rejected", "observation_failed"):
        with tempfile.TemporaryDirectory(prefix="independent-plan-feedback-") as directory:
            responses = (missing, corrected, source, review)
            if mode == "repeated_invalid": responses = (missing, missing)
            elif mode in ("budget_exhausted", "one_attempt"): responses = (missing,)
            elif mode == "explicit_unavailable": responses = ({"status": "unavailable", "notes": "No executable plan."}, corrected)
            elif mode == "review_rejected": responses = (missing, corrected, source, {**review, "valid": False, "issues": ["oracle rejected"]})
            services, owner = _services(Path(directory), responses)
            services.request.independent_verification_policy = verification.IndependentVerificationPolicy(
                maximum_plan_attempts=1 if mode == "one_attempt" else 2)
            request = replace(_subject(services, source=_GOOD_SOURCE), criteria=criteria)
            executions = []

            def execute(active_request, _context):
                executions.append(active_request)
                observed = _sandbox_observation(active_request, "2\n" if mode == "observation_failed" else "12\n")
                observed["commands"] = [dict(observed["commands"][0]) for _ in active_request.manifest.commands]
                return observed

            with patch.object(verification, "execute_generated_project", execute):
                result = verification.run_independent_verification(request, services, owner)
            attempts = result["plan_attempts"]
            original = verification._load(services, attempts[0]["proposal_ref"])
            check("plan_feedback_" + mode + "_retains_original_model_proposal",
                  original == responses[0] and all(verification._load(services, item["attempt_ref"])["proposal_ref"]
                      == item["proposal_ref"] for item in attempts))
            if mode == "repaired":
                from ..strings.prompt_fragments import INDEPENDENT_PROBE_REVIEW_PROMPT
                bundle = verification._load(services, result["probe_ref"])
                feedback = verification._load(services, attempts[1]["generation"]["prompt_ref"])
                review_packet = verification._load(services, bundle["review_call"]["prompt_ref"])
                check("oracle_review_contract_shows_every_registered_criterion_once",
                      review_packet["response_contract"]["criterion_refs"]
                      == [ref for ref, _text in criteria])
                check("oracle_review_uses_the_governed_prompt_and_keeps_every_refusal_class",
                      review_packet["responsibility"] == INDEPENDENT_PROBE_REVIEW_PROMPT
                      and all(phrase in INDEPENDENT_PROBE_REVIEW_PROMPT for phrase in (
                          "Refuse tautological/hardcoded observations",
                          "does not execute/read the subject", "invented requirements",
                          "missed criteria", "wrong expectations",
                          "looser than the task justifies", "Return exact covered criterion refs")))
                check("invalid_plan_is_revised_before_code_generation_and_independent_review",
                      result["status"] == "passed" and services.model_session.calls_used == 4
                      and len(executions) == 1 and [item["valid"] for item in attempts] == [False, True]
                      and len(bundle["file_calls"]) == 1 and bundle["review"]["valid"]
                      and feedback["record_type"] == "independent_probe_design_repair/v1"
                      and feedback["repair_feedback"]["diagnostic"]["missing_criteria"] == ["criterion:1"]
                      and feedback["repair_feedback"]["previous_proposal"] == missing)
            elif mode == "observation_failed":
                check("plan_repair_does_not_convert_failing_execution_into_acceptance",
                      result["status"] == "failed" and services.model_session.calls_used == 4
                      and len(executions) == 1 and all(item["passed"] is False for item in result["checks"]))
            else:
                expected_calls = (2 if mode == "repeated_invalid" else 4 if mode == "review_rejected" else 1)
                check("plan_feedback_" + mode + "_refuses_without_executing_a_probe",
                      result["status"] == "unavailable" and not executions
                      and services.model_session.calls_used == expected_calls
                      and not services.independent_probe_cache)


def run_format_repair_checks(check):
    """An inadmissible verifier response is repaired, never beyond authority."""
    packet = {"record_type": "offline_independent_format_repair/v1",
              "responsibility": "Return the fixture value.",
              "response_contract": {"value": "integer"}}
    prose = "The value is twelve."
    for name, answers, calls in (
            ("repaired", (prose, '{"value":12}'), 3),
            ("repeated", (prose, prose, '{"value":12}'), 3),
            ("spent_authority", (prose, '{"value":12}'), 1)):
        with tempfile.TemporaryDirectory(prefix="loop-independent-format-") as folder:
            services, owner = _services(Path(folder))
            services.model_session = fixture_model_execution(FixtureModelExecutionRequest(
                answers=answers, max_model_calls=calls)).start_session()
            value, references, error = None, None, None
            try:
                value, references = verification._call(
                    services, owner, "fixture", packet)
            except ValueError as exc:
                error = exc
            repairs = [event for event in owner.ledger.events
                       if event.get("custom_kind")
                       == "independent_verification_format_repair"]
            if name == "repaired":
                prompt = (verification._load(services, references["prompt_ref"])
                          if references else {})
                check("inadmissible_verifier_response_is_repaired_within_authority",
                      error is None and value == {"value": 12}
                      and services.model_session.calls_used == 2
                      and len(repairs) == 1
                      and prompt.get("format_repair", {}).get(
                          "format_repair_required") is True,
                      str(error))
            elif name == "repeated":
                check("repeated_inadmissible_verifier_response_ends_format_repair",
                      error is not None and value is None
                      and services.model_session.calls_used == 2
                      and len(repairs) == 1, str(error))
            else:
                check("verifier_format_repair_never_exceeds_declared_calls",
                      error is not None and value is None
                      and services.model_session.calls_used == 1
                      and repairs == [], str(error))


def run_file_identity_checks(check):
    """A planned file keeps its declared path; a conflicting path is asked again."""
    from .generated_project import GeneratedProjectFileSpec
    spec = GeneratedProjectFileSpec("checks/probe.py", "Observe the frozen combine function.")
    body = _proposal()["files"][0]["content"]
    packet = {"record_type": "offline_independent_file_identity/v1",
              "responsibility": "Return the planned probe file.",
              "response_contract": {"path": spec.path, "content": "complete Python source"}}
    exact = {"path": spec.path, "content": body}
    moved = {"path": "checks/replacement.py", "content": body}
    for name, answers in (
            ("omitted", ({"content": body},)),
            ("conflict_repaired", (moved, exact)),
            ("conflict_repeated", (moved, moved)),
            ("extra_field_repaired", ({**exact, "notes": "extra"}, exact))):
        with tempfile.TemporaryDirectory(prefix="loop-independent-file-identity-") as folder:
            services, owner = _services(Path(folder), answers)
            value, references, error = None, None, None
            try:
                value, references = verification._call(
                    services, owner, "file.fixture", packet, file_spec=spec)
            except ValueError as exc:
                error = exc
            repairs = [event.get("failure_code") for event in owner.ledger.events
                       if event.get("custom_kind") == "independent_verification_format_repair"]
            bound = [event for event in owner.ledger.events
                     if event.get("custom_kind") == "independent_file_representation"]
            calls = services.model_session.calls_used
            if name == "omitted":
                check("file_response_without_a_path_receives_the_declared_path",
                      error is None and value == exact and repairs == [] and calls == 1
                      and len(bound) == 1 and bound[0].get("strategy") == "predeclared_path_binding"
                      and references["representation"]["path"] == spec.path, str(error))
            elif name == "conflict_repaired":
                check("file_response_with_a_different_path_is_asked_again_not_rebound",
                      error is None and value == exact and bound == [] and calls == 2
                      and repairs == ["file_identity_changed"], str(error))
            elif name == "conflict_repeated":
                check("repeated_different_file_path_is_still_refused",
                      error is not None and value is None and bound == [] and calls == 2
                      and repairs == ["file_identity_changed"], str(error))
            else:
                check("file_response_with_extra_fields_is_asked_again",
                      error is None and value == exact and bound == [] and calls == 2
                      and repairs == ["file_response_shape_invalid"], str(error))


def run_recovery_record_checks(check):
    """A declined recovery keeps its decision on record before the refusal."""
    from .recovery import RecoveryOutcome

    packet = {"record_type": "offline_independent_recovery_record/v1",
              "responsibility": "Return the fixture value.",
              "response_contract": {"value": "integer"}}
    for choice, chosen_by, selected in (
            ("abandoned", "llm", ("abandon",)),
            ("unreasoned", "deterministic", ("retry_same_route",))):
        with tempfile.TemporaryDirectory(prefix="loop-independent-recovery-record-") as folder:
            services, owner = _services(Path(folder))
            services.model_session = fixture_model_execution(FixtureModelExecutionRequest(
                answers=("FAIL",), max_model_calls=1,
                validator=lambda raw: raw != "FAIL")).start_session()

            def recovery(request, error_code, attempt, *, provider_responded,
                         chosen_by=chosen_by, selected=selected):
                return RecoveryOutcome(selected=selected, chosen_by=chosen_by,
                                       reason="Offline recovery decision fixture.")

            services._reasoned_recovery = recovery
            error = None
            try:
                verification._call(services, owner, "fixture", packet)
            except Exception as exc:
                error = exc
            declined = [event for event in owner.ledger.events
                        if event.get("custom_kind")
                        == "independent_verification_recovery_declined"]
            check("independent_" + choice + "_recovery_is_recorded_before_the_refusal",
                  error is not None and len(declined) == 1
                  and declined[0].get("phase") == "fixture"
                  and declined[0].get("reasoned") is (chosen_by == "llm")
                  and declined[0].get("selected") == list(selected)
                  and declined[0].get("reason") == "Offline recovery decision fixture.",
                  str(declined)[:300])


def run_prompt_evidence_checks(check):
    """Probes run the subject itself, and expectations stated by the task are independent."""
    from ..strings.prompt_fragments import (
        INDEPENDENT_PROBE_DESIGN_PROMPT, INDEPENDENT_PROBE_REVIEW_PROMPT)
    check("probe_design_runs_the_subject_instead_of_reimplementing_it",
          "Probe code must exercise the actual subject" in INDEPENDENT_PROBE_DESIGN_PROMPT
          and "instead of reimplementing their logic" in INDEPENDENT_PROBE_DESIGN_PROMPT)
    check("oracle_review_accepts_expectations_stated_by_the_task",
          "An expected value stated by the task or its criteria is independent evidence"
          in INDEPENDENT_PROBE_REVIEW_PROMPT
          and "one copied from the subject code or its output is not" in INDEPENDENT_PROBE_REVIEW_PROMPT
          and "Refuse tautological/hardcoded observations" in INDEPENDENT_PROBE_REVIEW_PROMPT)
    # A live cell authored a probe that inferred the subject location from
    # its own file path and failed at execution with a missing source file,
    # after the subject work had already passed its own checks. Both prompts
    # now state the exact container binding and refuse location inference.
    check("probe_prompts_state_the_exact_subject_binding",
          "/workspace/subject/<name>" in INDEPENDENT_PROBE_DESIGN_PROMPT
          and "never infer their location from this probe file"
          in INDEPENDENT_PROBE_DESIGN_PROMPT)
    check("oracle_review_refuses_subject_location_inference",
          "resolves subject files by inferring their location"
          in INDEPENDENT_PROBE_REVIEW_PROMPT
          and "declared subject/ binding" in INDEPENDENT_PROBE_REVIEW_PROMPT)


def run_subject_binding_checks(check):
    """A probe that infers the subject location is refused at plan time.

    The September 15 flash cell SCM-001 authored a probe that resolved the
    subject directory from its own file location and then joined subject
    file names to that parent, so execution failed with a missing source
    file after the subject report had already satisfied every criterion.
    The plan validation refuses that shape before any execution spends a
    sandbox run, and the diagnostic names the declared binding to repair.
    """
    misbound = _proposal()
    misbound["files"][0]["content"] = (
        "import sys\n"
        "from pathlib import Path\n"
        "subject_dir = Path(__file__).resolve().parent.parent\n"
        "src = subject_dir / 'generate_report.py'\n"
        "print(open(src).read())\n")
    bound = deepcopy(misbound)
    bound["files"][0]["content"] = (
        "import json\n"
        "print(open('subject/generate_report.py').read())\n")
    repaired = deepcopy(misbound)
    repaired["files"][0]["content"] = (
        "import sys\n"
        "sys.path.insert(0, 'subject')\n"
        "import generate_report\n"
        "print(generate_report.__file__)\n")
    criteria = {"criterion:0": "The subject script text is observable."}
    for name, plan in (("misbound", misbound), ("declared", bound), ("repaired", repaired)):
        error, diagnostic = None, None
        try:
            validate_probe_plan(plan, criteria, materialized=True)
        except InvalidProbePlan as exc:
            error, diagnostic = exc, exc.diagnostic.to_dict()
        if name == "misbound":
            check("probe_inferring_the_subject_location_is_refused",
                  error is not None
                  and diagnostic.get("code") == "subject_location_inferred"
                  and diagnostic.get("repairable") is True
                  and "subject/<name>" in diagnostic.get("detail", ""),
                  str(diagnostic)[:250])
        elif name == "declared":
            check("probe_using_the_declared_subject_binding_is_accepted",
                  error is None, str(error)[:200])
        else:
            check("probe_resolving_through_the_subject_directory_is_accepted",
                  error is None, str(error)[:200])


def run_undeclared_output_checks(check):
    """An undeclared subject file is named, so the producer can declare it."""
    body = "An output the project's commands wrote.\n"
    for name, extra in (("one_output", ("analysis.md",)),
                        ("two_outputs", ("reports/summary.txt", "analysis.md"))):
        with tempfile.TemporaryDirectory(prefix="loop-independent-undeclared-") as folder:
            services, owner = _services(Path(folder))
            request = _subject(services, source=_GOOD_SOURCE)
            root = Path(request.project["workspace_path"])
            for relative in extra:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(body, encoding="utf-8")
            error = ""
            try:
                verification._freeze(request, services)
            except ValueError as exc:
                error = str(exc)
            report = verification.run_independent_verification(request, services, owner)
            if name == "one_output":
                check("undeclared_subject_file_is_named_with_the_repair_to_make",
                      "undeclared dependency files: analysis.md;" in error
                      and "declare each file the project's commands write as an expected artifact" in error
                      and report["status"] == "unavailable" and "analysis.md" in report["notes"]
                      and report["model_calls_known_subtotal"] == 0, error)
                continue
            declared = deepcopy(request.project)
            declared["artifacts"] = [{"path": relative, "digest": hashlib.sha256(body.encode()).hexdigest()}
                                     for relative in extra]
            subject, _inputs, _visible = verification._freeze(replace(request, project=declared), services)
            check("every_undeclared_subject_file_is_named_and_a_declared_output_is_frozen",
                  "undeclared dependency files: analysis.md, reports/summary.txt;" in error
                  and {item["path"]: item["authored"] for item in subject["inventory"]}
                  == {"utility.py": True, "analysis.md": False, "reports/summary.txt": False}, error)


_NOTICE = ("Dear patrons,\n\nThe library will close at 6 pm on Friday for scheduled "
           "maintenance.\nWe will reopen at 9 am on Monday with the usual hours.\n")
_NOTICE_TASK = "Write notice.md telling patrons when the library closes, why, and when it reopens."
_NOTICE_CRITERIA = (("criterion:0", "The notice states when the library closes and why."),
                    ("criterion:1", "The notice states when the library reopens."))


def _notice_request(services):
    """A natural-language deliverable that no exact expected value can check."""
    root = Path(services.workspace_base) / "attempt-notice"
    root.mkdir(parents=True)
    show = "print(open('notice.md', encoding='utf-8').read())\n"
    files = (GeneratedProjectFile("notice.md", _NOTICE), GeneratedProjectFile("show_notice.py", show))
    for file in files:
        (root / file.path).write_text(file.content, encoding="utf-8")
    manifest = GeneratedProjectManifest(
        "notice_fixture", "Offline natural-language deliverable fixture", files,
        (GeneratedProjectCommand(("python", "show_notice.py"), "Show the notice", 5, "verify"),), ())
    project = {"record_type": "generated_project_execution/v1", "workspace_path": str(root),
               "manifest": manifest.to_dict(), "manifest_digest": manifest.digest,
               "deterministic_checks_passed": True, "writes": [], "artifacts": [],
               "producer_plan": "PRODUCER_PLAN_MUST_NOT_REACH_VERIFIER"}
    return verification.IndependentVerificationRequest(_NOTICE_TASK, _NOTICE_CRITERIA, project)


def _judged_plan():
    return {"status": "ready", "notes": "Each criterion is judged against the printed notice.",
            "files": [{"path": "checks/read_notice.py", "purpose": "Print the notice exactly as written."}],
            "cases": [{"case_id": f"notice-{index}", "criterion_refs": [ref],
                       "purpose": "Show the notice to an independent judge.",
                       "argv": ["python", "checks/read_notice.py"], "timeout_seconds": 5,
                       "comparison": JUDGMENT_COMPARISON,
                       "expected": {"criterion_ref": ref, "requirement": text}}
                      for index, (ref, text) in enumerate(_NOTICE_CRITERIA)]}


def run_judgment_checks(check):
    """A natural-language deliverable passes only on grounded criterion judgments."""
    from ..strings.prompt_fragments import (
        INDEPENDENT_PROBE_DESIGN_PROMPT, INDEPENDENT_PROBE_REVIEW_PROMPT)
    plan = _judged_plan()
    refusals = {}
    for label, change in (
            ("added_requirement", lambda case: case["expected"].update(
                requirement=case["expected"]["requirement"] + " It names the branch manager.")),
            ("other_criterion", lambda case: case["expected"].update(criterion_ref="criterion:1")),
            ("tolerance", lambda case: case.update(tolerance={"absolute": 1}))):
        changed = deepcopy(plan)
        change(changed["cases"][0])
        try:
            validate_probe_plan(changed, _NOTICE_CRITERIA)
            refusals[label] = None
        except InvalidProbePlan as exc:
            refusals[label] = exc.diagnostic.code
    check("criterion_judgment_rubric_must_restate_its_one_registered_criterion",
          validate_probe_plan(plan, _NOTICE_CRITERIA) is not None
          and refusals == {"added_requirement": "invalid_expectation",
                           "other_criterion": "invalid_expectation", "tolerance": "invalid_tolerance"},
          str(refusals))
    check("verifier_prompts_offer_criterion_judgment_only_where_exact_checks_cannot_apply",
          "use criterion_judgment" in INDEPENDENT_PROBE_DESIGN_PROMPT
          and "copied word for word" in INDEPENDENT_PROBE_DESIGN_PROMPT
          and "A criterion_judgment case states no exact value" in INDEPENDENT_PROBE_REVIEW_PROMPT
          and "refuse it when an exact comparison could check" in INDEPENDENT_PROBE_REVIEW_PROMPT)
    source = {"path": "checks/read_notice.py", "content": (
        "from pathlib import Path\n"
        "print(Path('subject/notice.md').read_text(encoding='utf-8'), end='')\n")}
    review = {"valid": True, "criterion_refs": [ref for ref, _text in _NOTICE_CRITERIA],
              "issues": [], "notes": "The probe prints the notice read from the subject."}
    closing = {"satisfied": True, "reason": "The closing time and its reason are stated.",
               "evidence": ["The library will close at 6 pm on Friday for scheduled maintenance."]}
    reopening = {"satisfied": True, "reason": "The reopening time is stated.",
                 "evidence": ["We will reopen at 9 am on Monday"]}
    invented = "The library stays open through the weekend."

    def forged(_task, _cases, observations, _call):
        response = {"satisfied": True, "evidence": [invented], "reason": "Forged."}
        return [{**item, "passed": True, "judgment": {
            "record_type": JUDGMENT_RECORD_TYPE, "satisfied": True, "evidence": [invented],
            "missing_quotes": [], "reason": "Forged.", "grounded": True, "failure": "",
            "response": response, "call": {}}} for item in observations]

    for mode, judgments in (
            ("grounded", (closing, reopening)),
            ("not_satisfied", (closing, {**reopening, "satisfied": False,
                                         "reason": "No reopening time is given."})),
            ("invented_quote", ({**closing, "evidence": [invented]}, reopening)),
            ("probe_failed", ()), ("judge_unavailable", ()), ("forged", ())):
        with tempfile.TemporaryDirectory(prefix="independent-criterion-judgment-") as directory:
            services, owner = _services(Path(directory), (plan, source, review, *judgments))
            request = _notice_request(services)

            def execute(active_request, _context, mode=mode):
                observed = _sandbox_observation(active_request, _NOTICE)
                failed = {"exit_code": 1, "ok": False} if mode == "probe_failed" else {}
                observed["commands"] = [{**observed["commands"][0], "argv": list(command.argv), **failed}
                                        for command in active_request.manifest.commands]
                return observed

            with patch.object(verification, "execute_generated_project", execute):
                if mode == "forged":
                    with patch.object(verification, "judge_observations", forged):
                        result = verification.run_independent_verification(request, services, owner)
                else:
                    result = verification.run_independent_verification(request, services, owner)
            judged = [item.get("judgment") or {} for item in result["checks"]]
            calls = services.model_session.calls_used
            if mode == "grounded":
                bundle = verification._load(services, result["probe_ref"])
                design = verification._load(services, bundle["generation"]["prompt_ref"])
                file_packet = verification._load(services, bundle["file_calls"][0]["prompt_ref"])
                prompts = [verification._load(services, item["call"]["prompt_ref"])
                           for item in judged if item.get("call")]
                check("natural_language_deliverable_passes_on_grounded_criterion_judgments",
                      result["status"] == "passed" and calls == 5
                      and all(item.get("grounded") is True for item in judged)
                      and not _refused(lambda: verification.validate_independent_verification(
                          result, request, services, owner)), str(result.get("notes")))
                contract = design["response_contract"]["cases"][0]
                check("judge_sees_only_the_task_one_criterion_and_the_printed_text",
                      [item["criterion_ref"] for item in prompts] == ["criterion:0", "criterion:1"]
                      and all(item["observed_deliverable"] == _NOTICE and item["task"] == _NOTICE_TASK
                              and "PRODUCER_PLAN" not in json.dumps(item) for item in prompts)
                      and JUDGMENT_COMPARISON in contract["comparison"]
                      and "criterion_ref and requirement" in contract["expected"]
                      and "print the deliverable text exactly as read" in file_packet["responsibility"])
            elif mode in ("not_satisfied", "invented_quote"):
                index, failure = (1, "not_satisfied") if mode == "not_satisfied" else (0, "ungrounded_quote")
                check("criterion_judgment_" + mode + "_fails_the_report",
                      result["status"] == "failed" and calls == 5
                      and judged[index].get("failure") == failure
                      and result["checks"][index]["passed"] is False
                      and result["checks"][1 - index]["passed"] is True, str(judged)[:400])
            elif mode == "probe_failed":
                check("judged_case_whose_probe_did_not_complete_gets_no_judge_call",
                      result["status"] == "failed" and calls == 3 and judged == [{}, {}],
                      str(result.get("notes")))
            elif mode == "judge_unavailable":
                check("unanswered_judge_call_leaves_the_report_unavailable",
                      result["status"] == "unavailable" and calls == 3 and result["checks"] == [],
                      str(result.get("notes")))
            else:
                check("stored_judgment_is_grounded_again_when_the_report_is_validated",
                      result["status"] == "passed" and calls == 3
                      and _refused(lambda: verification.validate_independent_verification(
                          result, request, services, owner)), str(result.get("notes")))


def qualify_plan_repair(output_root: str) -> dict:
    """Explicit Docker execution; model replies are local contract fixtures."""
    root = Path(output_root)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink() or any(root.iterdir()):
        raise ValueError("qualification requires an existing empty absolute directory")
    criteria, missing, corrected, source, review = _plans()
    services, owner = _services(root, (missing, corrected, source, review))
    request = replace(_subject(services, source=_GOOD_SOURCE), criteria=criteria)
    result = verification.run_independent_verification(request, services, owner)
    result["qualification_scope"] = "real Docker probe execution with fixture model replies; no live provider"
    (root / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
