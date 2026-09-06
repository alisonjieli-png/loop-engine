"""Offline public-solve checks for autonomous executable feedback.

Model answers are fixture data; authored Python programs execute in temporary
directories. These checks prove repair wiring and accounting, not model quality
or production sandbox isolation.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from ..code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution)
from .adaptive_practitioner_acceptance_checks import (
    _decision, _orientation, _success_answers)


def run_checks() -> list[dict]:
    """Exercise repair and verification-only continuation through public solve."""
    return [*_feedback_scenario(), *_feedback_scenario(verification_retry=True)]


def _feedback_scenario(*, verification_retry=False) -> list[dict]:
    """Public solve repairs a real counterexample with no supplied feedback.

    Models use the canonical offline fixture transport. The narrow injected
    executor runs only these authored fixture programs in temporary directories;
    it supplies no evidence about Docker isolation or live model quality.
    """
    import sys

    from ..code_nodes.solve_runtime import SolveRequest, solve_task
    from ..templates.intake import TaskIntakeRequest, intake_task
    from .adaptive_practitioner_records import AdaptiveRunServices
    from .workspace_contracts import CommandRequest, WorkspaceSpec
    from .workspace_backends import RestrictedLocalWorkspace

    task = (
        "Create main.py with double(value) returning twice an integer, including "
        "zero and negative integers. Include an executable check.")
    orientation = _orientation(
        task_summary=task,
        verification_obligations=[
            "double(value) returns twice the input integer, including zero and negatives."])
    bad = "def double(value):\n    return value\n\nif __name__ == '__main__':\n    assert double(0) == 0\n"
    good = bad.replace("return value", "return 2 * value")
    candidate = {
        "record_type": "generated_project_candidate/v1", "project_id": "doubling",
        "summary": "Return the requested integer transformation.",
        "files": [{"path": "main.py", "purpose": "Implement integer doubling.",
                   "acceptance": ["The executable zero check passes."]}],
        "commands": [{"argv": ["python", "main.py"], "purpose": "Check zero.",
                      "timeout_seconds": 10, "command_kind": "verify"}],
        "expected_artifacts": [],
    }
    first = list(_success_answers(orientation=orientation))
    first[3] = json.dumps(candidate)
    first[4] = json.dumps({"path": "main.py", "content": bad})
    if verification_retry:
        first[4] = json.dumps({"path": "main.py", "content": good})
    proposal = {
        "status": "ready", "notes": "Observe actual outputs on distinct integers.",
        "files": [{"path": "checks/probe.py", "content": (
            "import json, sys\nfrom pathlib import Path\n"
            "sys.path.insert(0, str(Path('subject').resolve()))\n"
            "from main import double\n"
            "print(json.dumps([double(value) for value in (0, 3, -2)]))\n")}],
        "cases": [{"case_id": "integers", "criterion_refs": ["criterion:0"],
                   "purpose": "Observe zero, positive, and negative outputs.",
                   "argv": ["python", "checks/probe.py"], "timeout_seconds": 10,
                   "comparison": "json_equal", "expected": [0, 6, -4]}],
    }
    review = {"valid": True, "criterion_refs": ["criterion:0"], "issues": [],
              "notes": "The expected values follow directly from integer doubling."}
    second = list(_success_answers(
        orientation=orientation,
        decision=_decision("REPAIR", reason="Repair the independent integer counterexamples.")))
    repaired_candidate = json.loads(json.dumps(candidate))
    repaired_candidate["files"][0]["acceptance"].append(
        "Correct the observed positive and negative counterexamples.")
    second[3] = json.dumps(repaired_candidate)
    second[4] = json.dumps({"path": "main.py", "content": good})
    if verification_retry:
        second = [json.dumps(orientation), json.dumps({"actions": [_decision(
            "RETURN_RESULT", reason="Retry incomplete checking of the existing project.")]}),
            *first[5:]]
    answers = (*first[:5], json.dumps(proposal), json.dumps(review),
               *first[5:], *second)
    observed_repair_state = []
    execution_records = []
    original_model = AdaptiveRunServices.model
    unavailable_checker = []

    def capture_model(services, request):
        if request.step_id == "orient" and services.active_pass_number == 2:
            observed_repair_state.append(request.state)
        return original_model(services, request)

    def fixture_executor(request, context):
        del context
        if verification_retry and request.read_only_execution and not unavailable_checker:
            unavailable_checker.append(True)
            raise OSError("offline fixture checker was temporarily unavailable")
        root = Path(request.workspace_root)
        root.mkdir(parents=True)
        for item in request.input_artifacts:
            path = root / item.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(item.content)
        for item in request.manifest.files:
            path = root / item.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item.content, encoding="utf-8")
        commands = []
        workspace = RestrictedLocalWorkspace(WorkspaceSpec(
            "trusted_feedback_fixture", str(root), execution_enabled=True,
            allowed_commands=(sys.executable,)))
        for command in request.manifest.commands:
            result = workspace.command(CommandRequest(
                (sys.executable, *command.argv[1:]),
                timeout_seconds=command.timeout_seconds, execution_authorized=True))
            commands.append({"argv": list(command.argv), "purpose": command.purpose,
                             "ok": result.ok, "exit_code": result.exit_code,
                             "stdout": result.stdout, "stderr": result.stderr,
                             "output_truncated": result.output_truncated,
                             "error_code": result.error_code})
        artifacts = [{"path": item.path, "media_type": "text/x-python",
                      "verified": True, "present": True,
                      "byte_count": len(item.content.encode()),
                      "digest": hashlib.sha256(item.content.encode()).hexdigest()}
                     for item in request.manifest.files]
        record = {
            "record_type": "generated_project_execution/v1", "commands": commands,
            "workspace_path": str(root), "artifacts": artifacts, "writes": [],
            "sandbox": {
                "backend_kind": "docker",
                "workspace_read_only": request.read_only_execution,
                "network_policy": "none", "image": request.image,
                "execution_evidence_state": "INJECTED_CONTRACT_FIXTURE_ONLY",
            },
            "deterministic_checks_passed": all(item["ok"] for item in commands),
        }
        execution_records.append({"independent": request.read_only_execution, **record})
        return record

    with tempfile.TemporaryDirectory(prefix="independent-feedback-") as root:
        execution = fixture_model_execution(FixtureModelExecutionRequest(
            answers=answers, max_model_calls=len(answers)))
        request = SolveRequest(
            intake_task(TaskIntakeRequest(text=task)), model_execution=execution,
            runs_dir=root, max_passes=2, interaction_mode="autonomous", feedback=(),
            allow_workspace_writes=True, allow_sandbox_commands=True,
            project_executor=fixture_executor)
        with patch.object(AdaptiveRunServices, "model", capture_model), patch(
                "loop_engine.core.independent_verification.execute_generated_project",
                side_effect=fixture_executor):
            outcome = solve_task(request)
        reports = outcome.verification["independent_verification_records"]
        details = {
            "solved": outcome.solved, "failure_code": outcome.failure_code,
            "model_calls": outcome.model_calls,
            "reports": [{"status": item.get("status"), "notes": item.get("notes")}
                        for item in reports],
        }
        producer = [item for item in execution_records if not item["independent"]]
        feedback = ((observed_repair_state[0].get("facts", {}).get("last_verification", {})
                     .get("independent_checks", [])) if observed_repair_state else [])
        details["feedback_errors"] = [item.get("error") for item in feedback]
        prior_report = (feedback[0].get("report") or {}) if feedback else {}
        prior_checks = prior_report.get("checks") or []
        if verification_retry:
            last_verification = observed_repair_state[0]["facts"]["last_verification"]
            return [{
                "test": "public_return_result_rechecks_existing_project_without_regeneration",
                "passed": bool(outcome.solved and request.feedback == ()
                                and [item["status"] for item in reports] == ["unavailable", "passed"]
                                and len(producer) == 1
                                and producer[0]["deterministic_checks_passed"]
                                and outcome.model_calls == len(answers)
                                and reports[0]["probe_ref"] == reports[1]["probe_ref"]
                                and Path(outcome.workspace, "main.py").read_text() == good),
                "detail": json.dumps(details),
            }, {
                "test": "checker_outage_is_operational_feedback_without_invented_task_gap",
                "passed": bool(last_verification["operational_failures"]
                                and not last_verification["remaining_gaps"]
                                and not last_verification["gap_assessments"]
                                and last_verification["registered_acceptance_criteria"]
                                == outcome.verification["registered_acceptance_criteria"]),
                "detail": json.dumps(details),
            }]
        return [{
            "test": "public_solve_repairs_independent_counterexample_without_task_feedback",
            "passed": bool(outcome.solved and request.feedback == ()
                            and [item["status"] for item in reports] == ["failed", "passed"]
                            and len(producer) == 2
                            and all(item["deterministic_checks_passed"] for item in producer)
                            and prior_checks and prior_checks[0]["observed"] == [0, 3, -2]
                            and Path(outcome.workspace, "main.py").read_text() == good),
            "detail": json.dumps(details),
        }, {
            "test": "independent_failing_probe_is_replayed_under_shared_model_accounting",
            "passed": bool(len(reports) == 2
                            and reports[0]["probe_ref"] == reports[1]["probe_ref"]
                            and [item["model_calls_known_subtotal"] for item in reports] == [2, 0]
                            and outcome.model_calls == len(answers)
                            and outcome.run_history.get("chain_intact")),
            "detail": json.dumps(details),
        }]


def request_policy_checks() -> list[dict]:
    """Keep public adaptation and verification controls independently observable."""
    from dataclasses import replace
    from ..code_nodes.solve_runtime import SolveRequest, solve_task
    from ..templates.intake import TaskIntakeRequest, intake_task
    from .independent_verification import IndependentVerificationPolicy

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    class NonMatchingResolver:
        """Registered exact resolver that correctly declines this task."""

        resolver_id = "fixture.non_matching@1"

        def supports(self, _task):
            return False

        def execute(self, _task):
            raise AssertionError("a non-matching resolver must not execute")

    observed_pass_limits = []
    observed_verification_policies = []

    def capture_adaptive_request(adaptive_request, _dependencies):
        observed_pass_limits.append(adaptive_request.max_passes)
        observed_verification_policies.append(
            adaptive_request.independent_verification_policy)
        return {
            "run_id": "fixture-no-injected-pass-ceiling",
            "solved": False,
            "failure_code": "NO_VERIFIED_CAPABILITY",
            "deterministic_attempt": {
                "status": "NO_VERIFIED_CAPABILITY",
                "diagnostics": ["fixture stopped before semantic work"],
            },
            "run_history": {},
            "loop_details": [],
        }

    with patch(
            "loop_engine.code_nodes.solve_runtime.run_adaptive_practitioner",
            side_effect=capture_adaptive_request):
        solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                text="Solve work not covered by the exact resolver.")),
            deterministic_resolvers=(NonMatchingResolver(),),
            save_run_history=False))
    check(
        "registered_resolver_does_not_inject_a_practitioner_pass_ceiling",
        observed_pass_limits == [None],
        "resolver presence changes eligibility, not semantic stopping")
    check(
        "public_solve_requires_independent_verification_by_default",
        observed_verification_policies == [IndependentVerificationPolicy()],
        "verification policy reaches the canonical Practitioner request")
    from .adaptive_practitioner_records import AdaptivePractitionerRequest
    required = AdaptivePractitionerRequest("Produce the requested result.")
    legacy = replace(required, independent_verification_policy=
                     IndependentVerificationPolicy(required=False))
    check("verification_policy_changes_the_source_state_digest",
          required.source_state_digest != legacy.source_state_digest)
    return results


def verification_operational_checks() -> list[dict]:
    """Challenge failures remain binding even when the producer says accept."""
    from copy import deepcopy
    from types import SimpleNamespace
    from unittest.mock import patch

    from ..loop.kernel import ExecutionPlan, PractitionerState, ProblemSpec, ResultPacket
    from .independent_verification import IndependentVerificationPolicy
    from .adaptive_practitioner_verification import (
        AdaptiveVerificationRequest, _require_independent_checks, verify_adaptive_results)
    from .stage_store import StageStore

    tests = []
    project = {"record_type": "generated_project_execution/v1",
               "deterministic_checks_passed": True}
    proposed = {"verdict": "accept", "best_index": 0, "scores": [1.0],
                "notes": "The producer considers this finished.",
                "remaining_gaps": [], "advisory_findings": [],
                "new_requirement_proposals": []}
    for status in ("failed", "unavailable"):
        seen = []

        def model(request):
            seen.append(request.state)
            return deepcopy(proposed)

        services = SimpleNamespace(
            orientation_by_version={},
            request=SimpleNamespace(
                task="Return the requested result.",
                independent_verification_policy=IndependentVerificationPolicy()),
            model=model, diagnostic=lambda *_args: None,
            verification_records=[], active_pass_number=1,
            stage_store=StageStore(), stage_attribution_events=[])
        report = {"status": status,
                  "notes": "The independent check did not establish acceptance."}
        with patch("loop_engine.core.adaptive_practitioner_verification.run_independent_verification", return_value=report):
            evaluation = verify_adaptive_results(AdaptiveVerificationRequest(
                PractitionerState(ProblemSpec(services.request.task)),
                ExecutionPlan("generate", "run_dag"),
                (ResultPacket("candidate", result=project),), {}), services)
        tests.append({
            "test": f"independent_{status}_overrides_producer_acceptance",
            "passed": bool(evaluation.verdict == "repair"
            and seen[0]["independent_checks"][0]["report"] == report
            and services.verification_records[-1]["operational_failures"]
            and not services.verification_records[-1]["remaining_gaps"]
            and not services.verification_records[-1]["gap_assessments"]
            and services.verification_records[-1]["semantic_verification_observed"])})

    criteria = [{"criterion_ref": "criterion:0", "text": services.request.task}]
    binding = {
        "independent_verification_policy":
            services.request.independent_verification_policy.to_dict(),
        "registered_acceptance_criteria": criteria,
        "independent_checks": [{"result_index": 0, "report": {"status": "passed"}}],
    }
    refused = False
    with patch("loop_engine.core.adaptive_practitioner_verification.validate_independent_verification",
               side_effect=ValueError("artifact bytes changed")) as validator:
        try:
            _require_independent_checks(
                binding, (ResultPacket("candidate", result=project),), services, None)
        except ValueError:
            refused = True
    tests.append({"test": "independent_acceptance_rechecks_exact_source_binding",
                  "passed": refused and validator.call_count == 1})
    return tests
