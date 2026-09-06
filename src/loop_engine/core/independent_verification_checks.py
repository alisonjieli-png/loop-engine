"""Offline adversarial checks for independent verifier evidence boundaries.

Injected provider answers and executor observations test local contracts only.
They make no live-model, Docker-isolation, or task-quality claim.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ..code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution,
)
from ..loop.recursive_loop import Loop
from . import independent_verification as verification
from .context_artifacts import (
    ContextArtifactManager, ContextArtifactServices, ContextArtifactStore,
    ContextArtifactStoreSpec,
)
from .generated_project import (
    GeneratedProjectCommand, GeneratedProjectFile, GeneratedProjectFileSpec,
    GeneratedProjectManifest,
)
from .runtime_observer import RuntimeObservationServices


_TASK = "utility.py must expose combine(left, right), returning their sum."
_CRITERIA = (("criterion:0", "combine returns the sum of its two arguments"),)
_BAD_SOURCE = "def combine(left, right):\n    return left - right\n"
_GOOD_SOURCE = "def combine(left, right):\n    return left + right\n"


def _proposal():
    return {
        "status": "ready", "notes": "An offline contract fixture.",
        "files": [{"path": "checks/probe.py", "content": (
            "import json, runpy\n"
            "subject = runpy.run_path('subject/utility.py')\n"
            "print(json.dumps(subject['combine'](7, 5)))\n")}],
        "cases": [{"case_id": "addition", "criterion_refs": ["criterion:0"],
                   "purpose": "Observe the supplied function result.",
                   "argv": ["python", "checks/probe.py"],
                   "timeout_seconds": 5, "comparison": "json_equal",
                   "expected": 12}],
    }


def _observed(stdout="12\n", **changes):
    command = {"argv": ["python", "checks/probe.py"], "ok": True,
               "exit_code": 0, "output_truncated": False,
               "error_code": "", "stdout": stdout, "stderr": ""}
    command.update(changes)
    return {"commands": [command], "deterministic_checks_passed": True,
            "sandbox": {"backend_kind": "offline_fixture"},
            "workspace_path": "offline_observation"}


def _sandbox_observation(request, stdout="12\n"):
    """Inject required sandbox record fields, without starting a container."""
    execution = _observed(stdout)
    execution["sandbox"] = {
        "backend_kind": "docker", "workspace_read_only": True,
        "network_policy": "none", "image": request.image,
        "offline_fixture": True,
    }
    return execution


def _services(root, answers=()):
    owner = Loop("offline independent verification contract owner")
    runtime = RuntimeObservationServices(parent=owner, ledger=owner.ledger)
    manager = ContextArtifactManager(ContextArtifactServices(
        ContextArtifactStore(ContextArtifactStoreSpec(str(root / "artifacts"))),
        runtime))
    session = (fixture_model_execution(FixtureModelExecutionRequest(
        answers=tuple(json.dumps(item) for item in answers),
        max_model_calls=len(answers))).start_session() if answers else None)
    base = root / "workspaces"
    base.mkdir()
    services = SimpleNamespace(
        artifacts=manager, workspace_base=str(base), run_id=owner.loop_id,
        model_session=session, independent_probe_cache={},
        independent_verification_records=[],
        request=SimpleNamespace(allow_workspace_writes=True,
                                allow_sandbox_commands=True))
    return services, owner


def _subject(services, attempt="attempt-1", source=_BAD_SOURCE):
    root = Path(services.workspace_base) / attempt
    root.mkdir(parents=True)
    (root / "utility.py").write_text(source, encoding="utf-8")
    manifest = GeneratedProjectManifest(
        "subject_fixture", "Offline source identity fixture",
        (GeneratedProjectFile("utility.py", source),),
        (GeneratedProjectCommand(("python", "utility.py"), "Verify source", 5,
                                 "verify"),), ())
    project = {
        "record_type": "generated_project_execution/v1",
        "workspace_path": str(root), "manifest": manifest.to_dict(),
        "manifest_digest": manifest.digest, "deterministic_checks_passed": True,
        "writes": [], "artifacts": [],
        "producer_plan": "PRODUCER_PLAN_MUST_NOT_REACH_VERIFIER",
        "history": "PRODUCER_HISTORY_MUST_NOT_REACH_VERIFIER",
    }
    return verification.IndependentVerificationRequest(_TASK, _CRITERIA, project)


def _refused(action):
    try:
        action()
    except (TypeError, ValueError, OSError, RuntimeError):
        return True
    return False


def _comparison_checks(check):
    cases = _proposal()["cases"]
    observed = verification._compare(cases, _observed())
    check("controller_compares_observed_json_outside_candidate_process",
          len(observed) == 1 and observed[0]["passed"])
    invalid = (
        ("missing_command", {"commands": []}),
        ("missing_output", _observed(None)),
        ("empty_output_after_zero_exit", _observed("")),
        ("extra_json_document", _observed("12\n12\n")),
        ("fake_pass_claim", _observed('{"passed":true,"checks":999}')),
        ("nonfinite_constant", _observed("NaN")),
        ("positive_infinity", _observed("Infinity")),
        ("negative_infinity", _observed("-Infinity")),
        ("truncated_output", _observed(output_truncated=True)),
        ("missing_truncation_state", _observed(output_truncated=None)),
        ("timeout", _observed(exit_code=-1, ok=False, error_code="timeout")),
        ("wrong_command", _observed(argv=["python", "subject/utility.py"])),
        ("nonzero_exit_with_correct_stdout", _observed(exit_code=1)),
        ("executor_error_with_correct_stdout", _observed(error_code="unavailable")),
    )
    for name, execution in invalid:
        checks = verification._compare(cases, execution)
        check("independent_comparison_refuses_" + name,
              len(checks) == 1 and checks[0]["passed"] is False)
    for name, expected, stdout in (
        ("duplicate_json_key", {"x": 12}, '{"x":0,"x":12}'),
        ("extra_json_key", {"x": 12}, '{"x":12,"extra":0}'),
        ("missing_json_key", {"x": 12}, '{}'),
        ("boolean_is_not_zero", 0, "false"),
        ("boolean_is_not_one", 1, "true"),
        ("nested_boolean_is_not_zero", {"x": 0}, '{"x":false}'),
        ("missing_is_not_null", {"x": None}, '{}'),
    ):
        changed = deepcopy(cases)
        changed[0]["expected"] = expected
        check("independent_comparison_refuses_" + name,
              not verification._compare(changed, _observed(stdout))[0]["passed"])
    overflow = verification._compare(cases, _observed("1e400"))
    check("overflowed_json_remains_serializable_failed_evidence",
          not overflow[0]["passed"]
          and not _refused(lambda: verification._bytes(overflow)))
    exact_text = deepcopy(cases)
    exact_text[0].update(comparison="text_equal", expected="ready\n")
    check("text_comparison_preserves_exact_trailing_characters",
          verification._compare(exact_text, _observed("ready\n"))[0]["passed"]
          and not verification._compare(exact_text, _observed("ready"))[0]["passed"])


def _proposal_checks(check):
    check("independent_probe_accepts_typed_covered_executable_cases",
          verification._validate_probe(_proposal(), _CRITERIA).commands[0]
          .expected_exit_codes == (0,))
    invalid = []
    for name, key, value in (
        ("unavailable", "status", "unavailable"),
        ("empty_files", "files", []),
        ("empty_cases", "cases", []),
        ("wrong_file_container", "files", {}),
    ):
        proposal = _proposal()
        proposal[key] = value
        invalid.append((name, proposal, _CRITERIA))
    for name, key, value in (
        ("unknown_criterion", "criterion_refs", ["criterion:other"]),
        ("empty_criterion", "criterion_refs", []),
        ("duplicate_criterion", "criterion_refs", ["criterion:0", "criterion:0"]),
        ("empty_case_id", "case_id", ""),
        ("unsupported_comparison", "comparison", "trust_model"),
        ("empty_argv", "argv", []),
        ("inline_command", "argv", ["python", "-c", "print(12)"]),
        ("subject_command", "argv", ["python", "subject/utility.py"]),
        ("shell_command", "argv", ["sh", "checks/probe.py"]),
        ("zero_timeout", "timeout_seconds", 0),
        ("boolean_timeout", "timeout_seconds", True),
        ("nonfinite_timeout", "timeout_seconds", float("inf")),
        ("nonfinite_expectation", "expected", float("nan")),
    ):
        proposal = _proposal()
        proposal["cases"][0][key] = value
        invalid.append((name, proposal, _CRITERIA))
    for name, path in (("traversal", "checks/../probe.py"),
                       ("absolute_path", "/checks/probe.py"),
                       ("outside_checks", "subject/probe.py")):
        proposal = _proposal()
        proposal["files"][0]["path"] = path
        invalid.append((name, proposal, _CRITERIA))
    duplicate = _proposal()
    duplicate["cases"].append(deepcopy(duplicate["cases"][0]))
    invalid.append(("duplicate_case", duplicate, _CRITERIA))
    empty_text = _proposal()
    empty_text["cases"][0].update(comparison="text_equal", expected="")
    invalid.append(("empty_text_expectation", empty_text, _CRITERIA))
    invalid.append(("uncovered_criterion", _proposal(),
                    _CRITERIA + (("criterion:1", "Preserve both inputs."),)))
    for name, proposal, criteria in invalid:
        check("probe_validation_refuses_" + name,
              _refused(lambda: verification._validate_probe(proposal, criteria)))


def _execution_policy_checks(check):
    image = verification.sandbox_image()
    execution = _sandbox_observation(SimpleNamespace(image=image))
    cases = _proposal()["cases"]
    check("execution_policy_accepts_complete_exact_sandbox_fixture",
          verification._valid_execution(execution, cases, image))
    invalid = []
    for name, field, value in (
        ("local_fallback", "backend_kind", "restricted_local"),
        ("writable_mount", "workspace_read_only", False),
        ("network_access", "network_policy", "dependency_setup_only"),
        ("changed_image", "image", image + "-different"),
    ):
        changed = deepcopy(execution)
        changed["sandbox"][field] = value
        invalid.append((name, changed))
    changed = deepcopy(execution)
    changed["commands"].append(deepcopy(changed["commands"][0]))
    invalid.append(("extra_command", changed))
    changed = deepcopy(execution)
    changed["commands"] = []
    invalid.append(("missing_command", changed))
    changed = deepcopy(execution)
    changed["deterministic_checks_passed"] = False
    invalid.append(("failed_mechanical_checks", changed))
    for name, changed in invalid:
        check("execution_policy_refuses_" + name,
              not verification._valid_execution(changed, cases, image))


def _freeze_checks(check):
    with tempfile.TemporaryDirectory(prefix="loop-independent-freeze-") as folder:
        services, _owner = _services(Path(folder))
        request = _subject(services)
        subject, inputs, visible = verification._freeze(request, services)
        check("frozen_subject_has_exact_bytes_and_untrusted_source_labels",
              len(inputs) == 1 and inputs[0].path == "subject/utility.py"
              and inputs[0].content == _BAD_SOURCE.encode()
              and subject["inventory"][0]["digest"]
              == hashlib.sha256(_BAD_SOURCE.encode()).hexdigest()
              and visible[0]["trust"] == "untrusted_candidate_source")
        original = deepcopy(request.project)
        original["manifest_digest"] = "0" * 64
        check("freeze_refuses_manifest_identity_drift", _refused(lambda:
              verification._freeze(verification.IndependentVerificationRequest(
                  _TASK, _CRITERIA, original), services)))
        original = deepcopy(request.project)
        original["deterministic_checks_passed"] = False
        check("freeze_requires_successful_producer_mechanical_checks", _refused(lambda:
              verification._freeze(verification.IndependentVerificationRequest(
                  _TASK, _CRITERIA, original), services)))
        root = Path(request.project["workspace_path"])
        (root / "utility.py").write_text(_GOOD_SOURCE, encoding="utf-8")
        check("freeze_refuses_source_bytes_changed_after_producer_result",
              _refused(lambda: verification._freeze(request, services)))
        for name, kind in (("undeclared_dependency", "file"),
                           ("subject_symlink", "symlink"),
                           ("nonregular_source", "directory")):
            request = _subject(services, attempt=name)
            root = Path(request.project["workspace_path"])
            if kind == "file":
                (root / "dependency.py").write_text("value = 99\n", encoding="utf-8")
            elif kind == "symlink":
                (root / "alias.py").symlink_to(root / "utility.py")
            else:
                (root / "utility.py").unlink()
                (root / "utility.py").mkdir()
            check("freeze_refuses_" + name,
                  _refused(lambda: verification._freeze(request, services)))
        request = _subject(services, attempt="input_case")
        root = Path(request.project["workspace_path"])
        raw = b"private supplied input\n"
        (root / "input.txt").write_bytes(raw)
        project = deepcopy(request.project)
        project["writes"] = [{"path": "input.txt", "input_artifact": True,
                              "digest": hashlib.sha256(raw).hexdigest()}]
        request = verification.IndependentVerificationRequest(_TASK, _CRITERIA, project)
        _, inputs, visible = verification._freeze(request, services)
        check("supplied_input_is_frozen_but_not_sent_as_model_source",
              len(inputs) == 2 and len(visible) == 1
              and visible[0]["path"] == "utility.py")


def _lifecycle_checks(check):
    approved = {"valid": True, "criterion_refs": ["criterion:0"],
                "issues": [], "notes": "Offline oracle review fixture."}
    with tempfile.TemporaryDirectory(prefix="loop-independent-cycle-") as folder:
        services, owner = _services(Path(folder), (_proposal(), approved))
        bad = _subject(services)
        calls = []

        def executor(request, context):
            # Inject deterministic observed stdout. Do not execute fixture source
            # or represent this function as Docker or independent task evidence.
            source = next(item.content for item in request.input_artifacts
                          if item.path == "subject/utility.py")
            calls.append((request, context.parent_loop.loop_id))
            return _sandbox_observation(
                request, "12\n" if source == _GOOD_SOURCE.encode() else "2\n")

        with patch.object(verification, "execute_generated_project", executor):
            failed = verification.run_independent_verification(bad, services, owner)
            good = _subject(services, attempt="attempt-2", source=_GOOD_SOURCE)
            passed = verification.run_independent_verification(good, services, owner)
        check("offline_observed_defect_fails_independent_acceptance",
              failed["status"] == "failed" and failed["checks"][0]["observed"] == 2
              and failed["checks"][0]["expected"] == 12)
        check("repaired_same_path_reuses_exact_frozen_regression_oracle",
              passed["status"] == "passed"
              and failed["probe_ref"] == passed["probe_ref"]
              and failed["subject_digest"] != passed["subject_digest"]
              and passed["model_calls_known_subtotal"] == 0
              and services.model_session.calls_used == 2)
        check("verifier_has_separate_canonical_loop_and_restricted_effect_request",
              calls and all(context_id != owner.loop_id
                            and request.read_only_execution is True
                            and request.authority.allow_local_execution is False
                            and request.authority.allow_network_reads is False
                            for request, context_id in calls)
              and any(event.get("profile_id") == "practitioner.verifier"
                      for event in owner.ledger.events))
        check("issued_pass_validates_against_current_source_and_loop_event",
              not _refused(lambda: verification.validate_independent_verification(
                  passed, good, services, owner)))
        bundle = verification._load(services, passed["probe_ref"])
        design = verification._load(services, bundle["generation"]["prompt_ref"])
        review = verification._load(services, bundle["review_call"]["prompt_ref"])
        check("independent_model_packets_exclude_producer_plan_and_history",
              design["task"] == _TASK and review["task"] == _TASK
              and "producer_plan" not in design and "history" not in design
              and "PRODUCER_PLAN_MUST_NOT_REACH_VERIFIER" not in json.dumps(design)
              and "PRODUCER_HISTORY_MUST_NOT_REACH_VERIFIER" not in json.dumps(review)
              and "interface_source" not in review)
        check("independent_model_calls_use_shared_session_accounting",
              len(services.model_session.results) == 2
              and services.model_session.total_tokens_used is not None)
        check("unissued_fake_pass_is_refused", _refused(lambda:
              verification.validate_independent_verification(
                  {"status": "passed"}, good, services, owner)))
        altered = deepcopy(passed)
        altered["checks"][0]["observed"] = 999
        check("issued_report_mutation_is_refused", _refused(lambda:
              verification.validate_independent_verification(
                  altered, good, services, owner)))
        forged = deepcopy(passed)
        forged["notes"] = "An unissued replacement report."
        forged["report_digest"] = verification._digest({
            key: value for key, value in forged.items() if key != "report_digest"})
        check("rehashed_unissued_report_is_refused", _refused(lambda:
              verification.validate_independent_verification(
                  forged, good, services, owner)))
        check("old_subject_cannot_borrow_a_repaired_subject_pass", _refused(lambda:
              verification.validate_independent_verification(
                  passed, bad, services, owner)))
        check("another_producer_cannot_borrow_issued_pass", _refused(lambda:
              verification.validate_independent_verification(
                  passed, good, services, Loop("unrelated offline owner"))))
        changed_task = verification.IndependentVerificationRequest(
            _TASK + " Preserve both operands.", _CRITERIA, good.project)
        check("changed_task_expires_prior_pass", _refused(lambda:
              verification.validate_independent_verification(
                  passed, changed_task, services, owner)))
        changed_criteria = verification.IndependentVerificationRequest(
            _TASK, (("criterion:0", "Return the product."),), good.project)
        check("changed_criterion_expires_prior_pass", _refused(lambda:
              verification.validate_independent_verification(
                  passed, changed_criteria, services, owner)))
        changed_subject, _inputs, visible = verification._freeze(changed_criteria, services)
        check("criterion_drift_without_remaining_model_authority_is_refused", _refused(lambda:
              verification._probe(changed_criteria, services, owner,
                                  changed_subject, visible)))
        extra = Path(good.project["workspace_path"]) / "additional.txt"
        extra.write_bytes(b"new input\n")
        changed_project = deepcopy(good.project)
        changed_project["writes"] = [{
            "input_artifact": True, "path": "additional.txt",
            "digest": hashlib.sha256(b"new input\n").hexdigest()}]
        changed_inventory = verification.IndependentVerificationRequest(
            _TASK, _CRITERIA, changed_project)
        changed_subject, _inputs, visible = verification._freeze(
            changed_inventory, services)
        check("path_drift_without_remaining_model_authority_is_refused", _refused(lambda:
              verification._probe(changed_inventory, services, owner,
                                  changed_subject, visible)))
        extra.unlink()
        check("exhausted_model_authority_refuses_regression_regeneration_before_dispatch",
              services.model_session.calls_used == 2)
        (Path(good.project["workspace_path"]) / "utility.py").write_text(
            _BAD_SOURCE, encoding="utf-8")
        check("source_mutation_before_acceptance_expires_prior_pass", _refused(lambda:
              verification.validate_independent_verification(
                  passed, good, services, owner)))


def _regression_scope_checks(check):
    approved = {"valid": True, "criterion_refs": ["criterion:0"],
                "issues": [], "notes": "Offline oracle review fixture."}
    for change in ("path", "preserved", "missing_case", "unknown_ref",
                   "incomplete_coverage", "rejected"):
        with tempfile.TemporaryDirectory(prefix="loop-independent-regression-") as folder:
            scope = {"valid": True, "issues": [],
                     "case_criteria": {"addition": ["criterion:sum"]},
                     "notes": "The unchanged case covers the restated sum criterion."}
            if change == "missing_case":
                scope["case_criteria"] = {}
            elif change == "unknown_ref":
                scope["case_criteria"] = {"addition": ["criterion:unknown"]}
            elif change == "rejected":
                scope.update(valid=False, issues=["The unchanged probe is insufficient."])
            services, owner = _services(
                Path(folder), (_proposal(), approved, scope))
            bad = _subject(services)
            good = _subject(services, "attempt-2", _GOOD_SOURCE)
            project = deepcopy(good.project)
            criteria = (("criterion:sum", "The result equals left plus right."),)
            if change == "path":
                raw = b"additional supplied input\n"
                (Path(good.project["workspace_path"]) / "input.txt").write_bytes(raw)
                project["writes"] = [{"path": "input.txt", "input_artifact": True,
                                      "digest": hashlib.sha256(raw).hexdigest()}]
                criteria = _CRITERIA
            elif change == "incomplete_coverage":
                criteria += (("criterion:inputs", "Both arguments remain unchanged."),)
            changed = verification.IndependentVerificationRequest(_TASK, criteria, project)

            def executor(request, _context):
                source = next(item.content for item in request.input_artifacts
                              if item.path == "subject/utility.py")
                return _sandbox_observation(
                    request, "12\n" if source == _GOOD_SOURCE.encode() else "2\n")

            with patch.object(verification, "execute_generated_project", executor):
                failed = verification.run_independent_verification(bad, services, owner)
                result = verification.run_independent_verification(changed, services, owner)
            if change == "preserved":
                bundle = verification._load(services, result["probe_ref"])
                expected = _proposal()
                expected["cases"][0]["criterion_refs"] = ["criterion:sum"]
                check("reviewed_criterion_rebinding_preserves_exact_code_stimulus_and_expectation",
                      result["status"] == "passed"
                      and bundle["previous_probe_ref"] == failed["probe_ref"]
                      and bundle["proposal"] == expected
                      and bundle["criteria"] == dict(criteria)
                      and services.model_session.calls_used == 3
                      and not _refused(lambda: verification.validate_independent_verification(
                          result, changed, services, owner)))
            elif change == "path":
                check("changed_subject_paths_refuse_regeneration_before_model_dispatch",
                      result["status"] == "unavailable"
                      and "regression interface changed" in result["notes"]
                      and services.independent_probe_cache[result["task_digest"]]
                      == failed["probe_ref"]
                      and services.model_session.calls_used == 2)
            else:
                check("criterion_rebinding_refuses_" + change,
                      result["status"] == "unavailable"
                      and services.independent_probe_cache[result["task_digest"]]
                      == failed["probe_ref"]
                      and services.model_session.calls_used == 3)


def _unavailable_checks(check):
    approved = {"valid": True, "criterion_refs": ["criterion:0"],
                "issues": [], "notes": "Offline oracle review fixture."}
    for fault in ("source_changed_during_execution", "extra_command",
                  "empty_output", "executor_unavailable", "rejected_oracle",
                  "model_unavailable", "missing_authority"):
        with tempfile.TemporaryDirectory(prefix="loop-independent-fault-") as folder:
            review = deepcopy(approved)
            if fault == "rejected_oracle":
                review.update(valid=False, issues=["An independently found oracle defect."])
            answers = (() if fault in ("model_unavailable", "missing_authority")
                       else (_proposal(), review))
            services, owner = _services(Path(folder), answers)
            request = _subject(services, source=_GOOD_SOURCE)
            if fault == "missing_authority":
                services.request.allow_sandbox_commands = False
            executions = []

            def executor(execution_request, _context):
                executions.append(execution_request)
                if fault == "executor_unavailable":
                    raise RuntimeError("Offline injected sandbox unavailable.")
                execution = _sandbox_observation(execution_request)
                if fault == "source_changed_during_execution":
                    (Path(request.project["workspace_path"]) / "utility.py").write_text(
                        _BAD_SOURCE, encoding="utf-8")
                elif fault == "extra_command":
                    execution["commands"].append(deepcopy(execution["commands"][0]))
                elif fault == "empty_output":
                    execution["commands"][0]["stdout"] = ""
                return execution

            with patch.object(verification, "execute_generated_project", executor):
                report = verification.run_independent_verification(request, services, owner)
            check("independent_run_refuses_" + fault,
                  report["status"] in ("failed", "unavailable")
                  and len(services.independent_verification_records) == 1
                  and _refused(lambda: verification.validate_independent_verification(
                      report, request, services, owner)))
            if fault in ("rejected_oracle", "model_unavailable", "missing_authority"):
                check("independent_" + fault + "_dispatches_no_project",
                      executions == [])


def _planned_file_checks(check):
    approved = {"valid": True, "criterion_refs": ["criterion:0"],
                "issues": [], "notes": "Offline oracle review fixture."}
    for fault in ("none", "changed_file_path", "duplicate_planned_path"):
        with tempfile.TemporaryDirectory(prefix="loop-independent-files-") as folder:
            plan = _proposal()
            plan["files"] = [
                {"path": "checks/probe.py", "purpose": "Observe the actual function."},
                {"path": "checks/support.py", "purpose": "Hold the probe operands."}]
            bodies = [deepcopy(_proposal()["files"][0]),
                      {"path": "checks/support.py", "content": "OPERANDS = (7, 5)\n"}]
            if fault == "changed_file_path":
                bodies[0]["path"] = "checks/replacement.py"
            elif fault == "duplicate_planned_path":
                plan["files"][1]["path"] = "checks/probe.py"
            services, owner = _services(Path(folder), (plan, *bodies, approved))
            bad = _subject(services)
            executions = []

            def executor(request, _context):
                executions.append(request)
                source = next(item.content for item in request.input_artifacts
                              if item.path == "subject/utility.py")
                return _sandbox_observation(
                    request, "12\n" if source == _GOOD_SOURCE.encode() else "2\n")

            with patch.object(verification, "execute_generated_project", executor):
                first = verification.run_independent_verification(bad, services, owner)
                if fault == "none":
                    good = _subject(services, "attempt-2", _GOOD_SOURCE)
                    second = verification.run_independent_verification(good, services, owner)
            if fault != "none":
                check("planned_probe_refuses_" + fault,
                      first["status"] == "unavailable" and executions == []
                      and services.model_session.calls_used == 2
                      and services.independent_probe_cache == {})
                continue
            bundle = verification._load(services, first["probe_ref"])
            packets = [verification._load(services, call["prompt_ref"])
                       for call in bundle["file_calls"]]
            check("planned_probe_generates_each_file_through_shared_accounted_session",
                  len(bundle["file_calls"]) == 2
                  and services.model_session.calls_used == 4
                  and bundle["proposal"]["files"] == bodies
                  and all(item["record_type"] == "independent_probe_file/v1"
                          and item["task"] == _TASK for item in packets))
            check("planned_files_receive_prior_file_without_producer_plan_history",
                  packets[0]["other_files"] == []
                  and packets[1]["other_files"] == [bodies[0]]
                  and "PRODUCER_PLAN_MUST_NOT_REACH_VERIFIER" not in json.dumps(packets))
            check("planned_probe_is_retained_byte_exact_after_observed_failure",
                  first["status"] == "failed" and second["status"] == "passed"
                  and first["probe_ref"] == second["probe_ref"]
                  and second["model_calls_known_subtotal"] == 0
                  and len(executions) == 2)


def _reasoned_retry_checks(check):
    from .model_capabilities import ModelOutputAllocation, ModelOutputCapability
    from .recovery import RecoveryOutcome

    packet = {"record_type": "offline_independent_retry/v1",
              "responsibility": "Return the fixture value.",
              "response_contract": {"value": "integer"}}
    for choice in ("retry", "several_retries", "abandon", "unreasoned", "budget"):
        with tempfile.TemporaryDirectory(prefix="loop-independent-retry-") as folder:
            services, owner = _services(Path(folder))
            failures = 3 if choice == "several_retries" else 1
            authority = fixture_model_execution(FixtureModelExecutionRequest(
                answers=("FAIL",) * failures + ('{"value":12}',),
                max_model_calls=failures + 1, validator=lambda raw: raw != "FAIL"))
            services.model_session = replace(
                authority, max_model_calls=1 if choice == "budget" else None).start_session()
            events, decisions = [], []
            services.publish = lambda kind, **values: events.append((kind, values))
            allocation = ModelOutputAllocation(
                ModelOutputCapability(64, "offline fixture contract"),
                "fixture", "fixture-model", "fixture.route", 32,
                "recovery:offline-fixture", "Offline explicitly selected response allowance.")

            def recovery(request, error_code, attempt, *, provider_responded):
                decisions.append((request, error_code, attempt, provider_responded))
                selected = ("abandon",) if (choice == "abandon"
                    or choice == "budget" and attempt > 1) else ("retry_same_route",)
                return RecoveryOutcome(
                    selected=selected,
                    chosen_by="deterministic" if choice == "unreasoned" else "llm",
                    reason="Offline recovery decision fixture.", output_allocation=allocation)

            services._reasoned_recovery = recovery
            value, error = None, None
            try:
                value, _references = verification._call(
                    services, owner, "fixture", packet)
            except Exception as exc:
                error = exc
            if choice in ("retry", "several_retries"):
                check("independent_" + choice + "_uses_reasoned_allocation_and_shared_accounting",
                      error is None and value == {"value": 12}
                      and services.model_session.calls_used == failures + 1
                      and services.model_session.authority.max_model_calls is None
                      and [item[2] for item in decisions] == list(range(1, failures + 1))
                      and [result.attempts[0].maximum_output_tokens
                           for result in services.model_session.results]
                      == [64] + [32] * failures)
                check("independent_" + choice + "_publishes_each_failed_and_completed_attempt",
                      len([item for item in events if item[0].endswith(".failed")]) == failures
                      and len([item for item in events if item[0].endswith(".started")])
                      == failures + 1
                      and len([item for item in events if item[0].endswith(".completed")]) == 1)
            else:
                check("independent_reasoned_recovery_refuses_" + choice,
                      error is not None and value is None
                      and services.model_session.calls_used == 1
                      and len(decisions) == (2 if choice == "budget" else 1))
            check("independent_" + choice + "_passes_typed_failure_responsibility_to_recovery",
                  decisions and decisions[0][0].step_id == "independent_fixture"
                  and decisions[0][0].objective == packet["responsibility"]
                  and decisions[0][2] == 1 and decisions[0][3] is True)


def _file_envelope_checks(check):
    body = ("# Untrusted suggested path: subject/ignored.py\n"
            "raise RuntimeError('the source must not execute during admission')\n")
    raw = "```python\n" + body + "```"
    packet = {"responsibility": "Return the one predeclared source file.",
              "response_contract": {"path": "checks/probe.py", "content": "Python source"}}
    variants = (
        ("exact_python_fence", raw, GeneratedProjectFileSpec("checks/probe.py", "Probe")),
        ("no_declared_file", raw, None),
        ("wrong_language", raw.replace("```python", "```javascript"),
         GeneratedProjectFileSpec("checks/probe.py", "Probe")),
        ("prose_wrapper", "Here is the implementation:\n" + raw,
         GeneratedProjectFileSpec("checks/probe.py", "Probe")),
        ("invalid_syntax", "```python\ndef broken(:\n```",
         GeneratedProjectFileSpec("checks/probe.py", "Probe")),
        ("wrong_file_suffix", raw, GeneratedProjectFileSpec("checks/probe.txt", "Probe")),
        ("untyped_file_spec", raw, {"path": "checks/probe.py", "purpose": "Probe"}),
    )
    for name, response, file_spec in variants:
        with tempfile.TemporaryDirectory(prefix="loop-independent-envelope-") as folder:
            services, owner = _services(Path(folder))
            services.model_session = fixture_model_execution(FixtureModelExecutionRequest(
                answers=(response,), max_model_calls=1)).start_session()
            value, references, refused = None, None, False
            try:
                value, references = verification._call(
                    services, owner, "file.fixture", packet, file_spec=file_spec)
            except (TypeError, ValueError, SyntaxError):
                refused = True
            if name != "exact_python_fence":
                check("predeclared_file_fence_refuses_" + name,
                      refused and value is None
                      and not any(event.get("custom_kind") == "independent_file_representation"
                                  for event in owner.ledger.events))
                continue
            representation = references["representation"]
            check("predeclared_python_fence_preserves_exact_body_and_frozen_path",
                  not refused and value == {"path": "checks/probe.py", "content": body}
                  and representation["source_digest"] == hashlib.sha256(body.encode()).hexdigest()
                  and representation["raw_digest"] == hashlib.sha256(raw.encode()).hexdigest()
                  and references["response_ref"]["digest"] == representation["raw_digest"])
            check("file_envelope_records_representation_without_execution_or_approval",
                  len([event for event in owner.ledger.events
                       if event.get("custom_kind") == "independent_file_representation"]) == 1
                  and services.independent_verification_records == []
                  and services.independent_probe_cache == {}
                  and services.model_session.calls_used == 1)
    with tempfile.TemporaryDirectory(prefix="loop-independent-wrong-path-") as folder:
        services, owner = _services(Path(folder), (
            {"path": "checks/replacement.py", "content": body},))
        request = _subject(services)
        subject, _inputs, visible = verification._freeze(request, services)
        plan = _proposal()
        plan["files"] = [{"path": "checks/probe.py", "purpose": "Observe the subject."}]
        check("valid_json_with_wrong_file_path_is_not_rescued_by_fence_alternative",
              _refused(lambda: verification._materialize_probe_files(
                  request, services, owner, plan, subject, visible))
              and not any(event.get("custom_kind") == "independent_file_representation"
                          for event in owner.ledger.events))


def run_checks() -> dict:
    """Exercise oracle admission, artifact identity and retained observations."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    for label, group in (("comparison", _comparison_checks),
                         ("proposal", _proposal_checks),
                         ("execution_policy", _execution_policy_checks),
                         ("freeze", _freeze_checks),
                         ("lifecycle", _lifecycle_checks),
                         ("regression_scope", _regression_scope_checks),
                         ("unavailable", _unavailable_checks),
                         ("planned_files", _planned_file_checks),
                         ("reasoned_retry", _reasoned_retry_checks),
                         ("file_envelope", _file_envelope_checks)):
        try:
            group(check)
        except Exception as exc:
            check("independent_" + label + "_fixture_completed", False,
                  type(exc).__name__ + ": " + str(exc))
    passed = sum(item["passed"] for item in tests)
    return {"component": "independent_verification", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests), "provider_calls_made": 0,
            "scope": "Offline injected provider/executor contract checks only."}
