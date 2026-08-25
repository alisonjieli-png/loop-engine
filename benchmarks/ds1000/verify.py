"""Offline independent verifier for the tracked DS-1000 evidence.

The verifier uses only the Python standard library. It reads saved evidence,
recomputes hashes and accounting, and never executes candidate code, fits or
trains a model, imports a data-science package, or contacts a provider.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
EXPECTED_TASKS = {
    72: "Pandas",
    218: "Pandas",
    838: "Sklearn",
    896: "Sklearn",
}
EXPECTED_ROOT_STEPS = [
    "orient",
    "reconcile_horizon",
    "assess_prepare",
    "decide_next",
    "how",
    "act",
    "verify",
    "integrate_commit",
    "route",
]
MODEL = "deepseek-v4-flash:0731"
PROVIDER = "ollama_cloud"
ROUTE = "benchmark.ds1000.deepseek-v4-flash-0731"
MAXIMUM_OUTPUT_TOKENS = 65536
SOURCE_COMMIT = "b39aab71da6d23ef8d3cac59a7c5f834516ab334"


class VerificationFailure(RuntimeError):
    """A required saved-evidence invariant failed."""


class Checks:
    def __init__(self):
        self.rows: list[dict] = []

    def check(self, name: str, condition, detail="") -> None:
        passed = bool(condition)
        self.rows.append({
            "name": name,
            "passed": passed,
            "detail": detail,
        })

    @property
    def passed(self) -> int:
        return sum(row["passed"] for row in self.rows)

    @property
    def all_passed(self) -> bool:
        return self.passed == len(self.rows)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_digest(value) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(character in "0123456789abcdef" for character in value))


def verify_artifact_manifest(root: Path, checks: Checks) -> dict:
    manifest_path = root / "manifest.json"
    manifest = load_json(manifest_path)
    expected_entries = {row["path"]: row for row in manifest["files"]}
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    checks.check(
        "artifact_manifest_file_set",
        actual_paths == set(expected_entries),
        f"{len(actual_paths)} tracked evidence files")
    for relative, row in sorted(expected_entries.items()):
        path = root / relative
        checks.check(
            f"artifact_bytes:{relative}",
            path.is_file() and path.stat().st_size == row["bytes"],
            row["bytes"])
        checks.check(
            f"artifact_sha256:{relative}",
            path.is_file() and sha256_file(path) == row["sha256"],
            row["sha256"])
    entries_digest = sha256_bytes(json.dumps(
        manifest["files"], sort_keys=True,
        separators=(",", ":")).encode())
    checks.check(
        "artifact_manifest_entries_digest",
        entries_digest == manifest["files_digest"],
        entries_digest)
    checks.check(
        "artifact_package_excludes_hidden_upstream_bodies",
        manifest.get("contains_task_reference_solutions") is False
        and manifest.get("contains_evaluator_bodies") is False)
    forbidden = ("\"reference_code\"", "\"code_context\"",
                 "def test_execution(", "def test_string(")
    leaks = []
    for relative in actual_paths:
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(marker in text for marker in forbidden):
            leaks.append(relative)
    checks.check(
        "artifact_package_has_no_reference_or_evaluator_body",
        not leaks,
        leaks)
    return manifest


def verify_compact_chain(chain: dict, checks: Checks) -> None:
    run_id = chain["run_id"]
    event_digests = chain["event_digests"]
    previous_digests = chain["previous_digests"]
    manifest = chain["manifest"]
    count = manifest["events"]
    checks.check(
        f"run_history_count:{run_id}",
        len(event_digests) == len(previous_digests) == count,
        count)
    linkage = bool(event_digests) and previous_digests[0] == ""
    linkage = linkage and all(
        previous_digests[index] == event_digests[index - 1]
        for index in range(1, len(event_digests)))
    checks.check(f"run_history_linkage:{run_id}", linkage)
    checks.check(
        f"run_history_digest_shapes:{run_id}",
        all(is_digest(value) for value in event_digests)
        and all(value == "" or is_digest(value)
                for value in previous_digests))
    checks.check(
        f"run_history_head:{run_id}",
        bool(event_digests)
        and event_digests[-1] == manifest["head_digest"]
        and manifest.get("committed") is True)
    sequence_sha = sha256_bytes(json.dumps({
        "event_digests": event_digests,
        "previous_digests": previous_digests,
    }, sort_keys=True, separators=(",", ":")).encode())
    checks.check(
        f"run_history_compact_sequence:{run_id}",
        sequence_sha == chain["sequence_sha256"],
        sequence_sha)
    checks.check(
        f"run_history_event_families_sum:{run_id}",
        sum(chain["event_type_counts"].values()) == count)
    checks.check(
        f"run_history_source_was_body_verified:{run_id}",
        chain.get("source_body_and_links_verified") is True)


def verify_local_chain_if_present(chain: dict, checks: Checks) -> str:
    source_kind = chain["source_kind"]
    campaign_id = (
        chain["run_id"].split(".problem-", 1)[0])
    run_dir = HERE / "results" / campaign_id / "run-histories" / chain["run_id"]
    events_path = run_dir / "events.jsonl"
    manifest_path = run_dir / "manifest.json"
    if not events_path.is_file() or not manifest_path.is_file():
        return "not_present_in_clean_checkout"
    event_digests = []
    previous_digests = []
    previous = ""
    valid = True
    with events_path.open(encoding="utf-8") as stream:
        for expected_sequence, line in enumerate(stream):
            row = json.loads(line)
            body = dict(row)
            event_digest = body.pop("event_digest")
            recomputed = sha256_bytes(
                json.dumps(body, sort_keys=True, default=str).encode())
            valid = valid and row["sequence_number"] == expected_sequence
            valid = valid and row["prev_digest"] == previous
            valid = valid and event_digest == recomputed
            previous_digests.append(row["prev_digest"])
            event_digests.append(event_digest)
            previous = event_digest
    valid = valid and event_digests == chain["event_digests"]
    valid = valid and previous_digests == chain["previous_digests"]
    valid = valid and sha256_file(events_path) == chain["events_jsonl_sha256"]
    valid = valid and sha256_file(manifest_path) == chain[
        "manifest_json_sha256"]
    checks.check(
        f"local_detailed_run_history_cross_check:{source_kind}:"
        f"{chain['problem_id']}",
        valid,
        str(events_path))
    return "verified"


def verify_canvas(path: Path, expected_role: str, checks: Checks) -> dict:
    canvas = load_json(path)
    label = path.relative_to(path.parents[3]).as_posix()
    plan = canvas["plan"]
    digest = canvas["plan_digest"]
    checks.check(
        f"canvas_record:{label}",
        canvas["record_type"] == "ds1000_canvas_evidence/v1"
        and canvas["role"] == expected_role)
    checks.check(
        f"canvas_digest:{label}",
        is_digest(digest)
        and plan["digest"] == digest
        and canvas["canonical"]["digest"] == digest
        and json.loads(canvas["json"])["digest"] == digest,
        digest)
    checks.check(
        f"canvas_rendering:{label}",
        canvas["mermaid"].startswith("flowchart TD")
        and canvas["canonical"]["record_type"] == "solution_plan/v1")
    evaluation = canvas["evaluation"]
    checks.check(
        f"canvas_evaluation:{label}",
        evaluation["status"] == "completed"
        and is_digest(evaluation["candidate_sha256"]))
    return canvas


def verify_report_and_playback(root: Path, task: dict, chain: dict,
                               selected: bool, checks: Checks) -> None:
    report_path = root / task["report_path"]
    playback_path = root / task["playback_path"]
    report = load_json(report_path)["report"]
    playback = playback_path.read_text(encoding="utf-8")
    label = f"{'selected' if selected else 'correction'}:{task['problem_id']}"
    checks.check(
        f"report_identity:{label}",
        report["record_type"] == "loop_report/v1"
        and report["run_id"] == task["run_id"]
        and report["events"] == chain["manifest"]["events"]
        and report["chain_intact"] is True)
    expected_calls = task["physical_model_calls"] if selected else 0
    checks.check(
        f"report_model_calls:{label}",
        report["model_calls"] == expected_calls,
        report["model_calls"])
    checks.check(
        f"playback_hash:{label}",
        sha256_file(playback_path) == task["playback_sha256"]
        and len(playback.splitlines()) == task["playback_lines"])
    checks.check(
        f"playback_content:{label}",
        "INIT" in playback and "TERMINAL" in playback)


def verify_selected(selected: dict, compact: dict, population: dict,
                    task_evidence: dict, artifact_root: Path,
                    chains_by_run: dict, checks: Checks) -> dict[int, dict]:
    checks.check(
        "selected_summary_identity",
        selected["record_type"] == "ds1000_full_practitioner_campaign/v1"
        and selected["campaign_id"] == compact["selected_campaign_id"]
        and selected["population_id"] == population["population_id"])
    checks.check(
        "selected_population_accounting",
        selected["population_size"] == selected["attempted"] == 4
        and selected["passed"] == 2
        and selected["execution_accuracy"] == 0.5
        and selected["full_path_eligible"] == 4)
    checks.check(
        "selected_exact_model_route",
        selected["model"] == MODEL
        and selected["provider"] == PROVIDER
        and selected["maximum_output_tokens"] == MAXIMUM_OUTPUT_TOKENS
        and selected["failover"] is False
        and selected["selected_mode"] == "non_deterministic")

    budget = selected["budget"]
    attempts = budget["attempts"]
    input_tokens = sum(int(row["input_tokens"]) for row in attempts)
    output_tokens = sum(int(row["output_tokens"]) for row in attempts)
    physical_by_task = Counter(str(row["problem_id"]) for row in attempts)
    checks.check(
        "selected_call_accounting",
        len(attempts) == budget["physical_population"] == 14
        and budget["excluded_diagnostic_physical_calls"] == 1
        and budget["packet_total_physical_calls"]
        == selected["packet_total_physical_calls"] == 15
        and selected["packet_physical_call_ceiling"] == 16
        and budget["repair_requests"] == 2)
    checks.check(
        "selected_token_accounting",
        input_tokens == selected["input_tokens"] == 11577
        and output_tokens == selected["output_tokens"] == 25301
        and input_tokens + output_tokens == selected["total_tokens"] == 36878)
    checks.check(
        "selected_per_task_call_accounting",
        dict(physical_by_task) == budget["physical_by_task"]
        == {"72": 4, "218": 3, "838": 3, "896": 4})
    checks.check(
        "selected_attempt_contracts",
        all(row["provider"] == PROVIDER
            and row["model"] == MODEL
            and row["route"] == ROUTE
            and row["maximum_output_tokens"] == MAXIMUM_OUTPUT_TOKENS
            and row["loop_id"]
            and row["ok"] is True
            for row in attempts))

    task_rows = {int(row["problem_id"]): row
                 for row in task_evidence["selected"]}
    summary_rows = {int(row["problem_id"]): row for row in selected["tasks"]}
    expected_pass = {72: False, 218: True, 838: True, 896: False}
    for problem_id, library in EXPECTED_TASKS.items():
        task = task_rows[problem_id]
        summary = summary_rows[problem_id]
        label = f"selected:{problem_id}"
        checks.check(
            f"task_identity:{label}",
            task["library"] == library
            and task["run_id"] == summary["run_id"]
            and task["source_commit"] == SOURCE_COMMIT)
        checks.check(
            f"task_original_result:{label}",
            task["passed"] is expected_pass[problem_id]
            and summary["passed"] is expected_pass[problem_id])
        checks.check(
            f"task_usage:{label}",
            task["physical_model_calls"] == summary["physical_model_calls"]
            and task["input_tokens"] == summary["input_tokens"]
            and task["output_tokens"] == summary["output_tokens"]
            and task["total_tokens"]
            == task["input_tokens"] + task["output_tokens"])
        path = task["full_path"]
        checks.check(
            f"task_full_path:{label}",
            path["eligible"] is True
            and all(path["checks"].values())
            and path["root_steps"] == EXPECTED_ROOT_STEPS)
        checks.check(
            f"task_failure_visibility:{label}",
            task["failures_preserved"] is True and task["error"] == "")
        calls = task["model_spawned_loops"]
        by_role = {row["role"]: row for row in calls}
        required_roles = {"candidate_a", "candidate_b", "synthesis"}
        checks.check(
            f"task_required_model_spawned_loops:{label}",
            required_roles <= set(by_role)
            and set(by_role["candidate_a"]["consumption"]["consumed_refs"])
            != set(by_role["candidate_b"]["consumption"]["consumed_refs"]))
        checks.check(
            f"task_spawned_loop_intelligence:{label}",
            all(row["consumption"]["mode"] == "non_deterministic"
                and len(row["consumption"]["consumed_refs"]) == 7
                and is_digest(row["consumption"]["record_digest"])
                and any("user_feedback_intelligence" in ref
                        for ref in row["consumption"]["consumed_refs"])
                and any("runtime_history_solution_intelligence" in ref
                        for ref in row["consumption"]["consumed_refs"])
                for row in calls))
        attempt_rows = [attempt for row in calls
                        for attempt in row["gateway_attempts"]]
        checks.check(
            f"task_call_rows:{label}",
            len(attempt_rows) == task["physical_model_calls"]
            and sum(int(row["input_tokens"]) for row in attempt_rows)
            == task["input_tokens"]
            and sum(int(row["output_tokens"]) for row in attempt_rows)
            == task["output_tokens"])
        checks.check(
            f"task_evaluations:{label}",
            bool(task["evaluations"])
            and all(row["status"] == "completed"
                    and is_digest(row["candidate_sha256"])
                    for row in task["evaluations"]))
        for evaluation, canvas_relative in zip(
                task["evaluations"], task["canvas_paths"]):
            canvas = verify_canvas(
                artifact_root / canvas_relative,
                evaluation["role"], checks)
            checks.check(
                f"task_canvas_result:{label}:{evaluation['role']}",
                canvas["evaluation"]["passed"] == evaluation["passed"]
                and canvas["evaluation"]["candidate_sha256"]
                == evaluation["candidate_sha256"])
        chain = chains_by_run[task["run_id"]]
        verify_report_and_playback(
            artifact_root, task, chain, True, checks)
    return task_rows


def verify_correction(correction: dict, compact: dict,
                      selected_tasks: dict[int, dict], task_evidence: dict,
                      artifact_root: Path, chains_by_run: dict,
                      checks: Checks) -> None:
    checks.check(
        "correction_summary_identity",
        correction["record_type"]
        == "ds1000_recorded_output_regrade_campaign/v1"
        and correction["correction_id"]
        == compact["corrected_recorded_output_evaluation"]["correction_id"]
        and correction["parent_campaign_id"] == compact["selected_campaign_id"])
    checks.check(
        "invalidated_result_is_prominent",
        correction["parent_reported_execution_accuracy"] == 0.5
        and correction["parent_score_status"].startswith("invalidated")
        and compact["original_evaluation"]["reported_execution_accuracy"] == 0.5
        and compact["original_evaluation"]["status"] == "invalidated")
    checks.check(
        "corrected_campaign_result",
        correction["corrected_passed"] == correction["population_size"] == 4
        and correction["corrected_execution_accuracy"] == 1.0
        and correction["full_regrade_path_eligible"] == 4
        and correction["physical_model_calls"] == 0
        and correction["packet_total_physical_calls_unchanged"] == 15)
    checks.check(
        "exact_recorded_outputs_not_new_provider_run",
        "exact recorded provider responses" in correction["interpretation"]
        and "not a new model run" in correction["interpretation"])

    task_rows = {int(row["problem_id"]): row
                 for row in task_evidence["correction"]}
    changed = []
    for problem_id, library in EXPECTED_TASKS.items():
        task = task_rows[problem_id]
        selected = selected_tasks[problem_id]
        label = f"correction:{problem_id}"
        checks.check(
            f"task_identity:{label}",
            task["library"] == library
            and task["parent_run_id"] == selected["run_id"]
            and task["parent_campaign_id"] == correction["parent_campaign_id"])
        checks.check(
            f"task_corrected_result:{label}",
            task["corrected_passed"] is True
            and task["corrected_upstream_result"] == "passed"
            and task["physical_model_calls"] == 0
            and task["provider_outputs_reused"] is True)
        path = task["full_regrade_path"]
        checks.check(
            f"task_full_regrade_path:{label}",
            path["eligible"] is True
            and all(path["checks"].values())
            and path["root_steps"] == EXPECTED_ROOT_STEPS)
        selected_call = next(
            row for row in selected["model_spawned_loops"]
            if row["role"] == task["selected_role"])
        checks.check(
            f"task_original_candidate_binding:{label}",
            task["original_candidate_sha256"]
            == selected_call["candidate_code_sha256"])
        selected_raw_by_role = {
            row["role"]: row["raw_response_sha256"]
            for row in selected["model_spawned_loops"]}
        replay_raw_by_role = {
            row["role"]: row["raw_response_sha256"]
            for row in task["recorded_spawned_loops"]}
        checks.check(
            f"task_exact_recorded_output_binding:{label}",
            selected_raw_by_role == replay_raw_by_role
            and all(row["physical_model_calls"] == 0
                    for row in task["recorded_spawned_loops"]))
        canvas = verify_canvas(
            artifact_root / task["canvas_path"],
            task["selected_role"], checks)
        checks.check(
            f"task_corrected_canvas_result:{label}",
            canvas["evaluation"]["passed"] is True
            and canvas["evaluation"]["candidate_sha256"]
            == task["corrected_candidate_sha256"])
        if task["original_candidate_sha256"] \
                != task["corrected_candidate_sha256"]:
            changed.append(problem_id)
        chain = chains_by_run[task["run_id"]]
        verify_report_and_playback(
            artifact_root, task, chain, False, checks)
    checks.check(
        "whitespace_correction_changed_only_affected_selected_candidates",
        changed == [72, 896],
        changed)


def verify_population(population: dict, compact: dict,
                      checks: Checks) -> None:
    observed = {int(row["problem_id"]): row["library"]
                for row in population["tasks"]}
    checks.check(
        "population_frozen_before_outcomes",
        population["record_type"] == "ds1000_population/v1"
        and population["frozen_before_outcomes"] is True)
    checks.check(
        "population_exact_four_tasks",
        observed == EXPECTED_TASKS,
        observed)
    checks.check(
        "population_source_commit",
        population["source"]["commit"] == SOURCE_COMMIT
        == compact["source_commit"])
    data = next(row for row in population["source"]["artifacts"]
                if row["path"] == "data/ds1000.jsonl.gz")
    checks.check(
        "population_data_digest",
        data["sha256"]
        == "e8c6daa9d7223976bce0296644f3933f78d7f47830669ff05cd61da62c6ba9b3"
        and data["bytes"] == 418089)


def verify_self_is_offline(checks: Checks) -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    forbidden_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0]
                                  for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            if name in {"fit", "fit_transform", "partial_fit", "train"}:
                forbidden_calls.append((name, node.lineno))
    allowed = {
        "__future__", "argparse", "ast", "hashlib", "json", "sys",
        "collections", "pathlib",
    }
    checks.check(
        "verifier_imports_standard_library_only",
        imported_roots <= allowed,
        sorted(imported_roots))
    checks.check(
        "verifier_fits_or_trains_nothing",
        not forbidden_calls,
        forbidden_calls)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=HERE / "artifacts",
        help="tracked compact evidence directory")
    args = parser.parse_args(argv)
    root = args.artifacts.resolve()
    checks = Checks()
    try:
        verify_artifact_manifest(root, checks)
        compact = load_json(HERE / "verified-result.json")
        expected_evidence_paths = {
            "artifact_manifest": "artifacts/manifest.json",
            "selected_summary": "artifacts/selected-summary.json",
            "corrected_summary": "artifacts/correction-summary.json",
            "task_evidence": "artifacts/task-evidence.json",
            "run_history_chains": "artifacts/run-history-chains.json",
            "population_manifest": "population-v1.json",
            "offline_verifier": "verify.py",
        }
        checks.check(
            "compact_result_uses_tracked_clean_checkout_evidence",
            compact["evidence"] == expected_evidence_paths
            and all((HERE / relative).is_file()
                    for relative in expected_evidence_paths.values()),
            compact["evidence"])
        population = load_json(HERE / "population-v1.json")
        selected = load_json(root / "selected-summary.json")
        correction = load_json(root / "correction-summary.json")
        task_evidence = load_json(root / "task-evidence.json")
        chain_file = load_json(root / "run-history-chains.json")
        chains_by_run = {row["run_id"]: row for row in chain_file["chains"]}
        checks.check(
            "all_eight_run_histories_materialized",
            len(chains_by_run) == 8
            and Counter(row["source_kind"] for row in chain_file["chains"])
            == {"selected": 4, "correction": 4})
        local_detail_states = Counter()
        for chain in chain_file["chains"]:
            verify_compact_chain(chain, checks)
            local_detail_states[verify_local_chain_if_present(
                chain, checks)] += 1
        verify_population(population, compact, checks)
        selected_tasks = verify_selected(
            selected, compact, population, task_evidence, root,
            chains_by_run, checks)
        verify_correction(
            correction, compact, selected_tasks, task_evidence, root,
            chains_by_run, checks)
        checks.check(
            "compact_result_matches_selected_summary",
            compact["full_selected_run"]["new_physical_model_calls"]
            == selected["budget"]["physical_population"]
            and compact["full_selected_run"]["input_tokens"]
            == selected["input_tokens"]
            and compact["full_selected_run"]["output_tokens"]
            == selected["output_tokens"]
            and compact["full_selected_run"]["total_tokens"]
            == selected["total_tokens"])
        checks.check(
            "compact_result_matches_correction_summary",
            compact["corrected_recorded_output_evaluation"]["passed"]
            == correction["corrected_passed"] == 4
            and compact["corrected_recorded_output_evaluation"][
                "execution_accuracy"]
            == correction["corrected_execution_accuracy"] == 1.0
            and correction["physical_model_calls"] == 0)
        verify_self_is_offline(checks)
        output = {
            "record_type": "ds1000_offline_verification/v1",
            "all_passed": checks.all_passed,
            "passed": checks.passed,
            "total": len(checks.rows),
            "fit_or_train_calls": 0,
            "provider_calls": 0,
            "original_result": {
                "reported_passed": 2,
                "population": 4,
                "reported_accuracy": 0.5,
                "status": "INVALIDATED",
                "reason": compact["original_evaluation"]["reason"],
            },
            "corrected_recorded_output_result": {
                "passed": 4,
                "population": 4,
                "accuracy": 1.0,
                "new_model_calls": 0,
                "exact_recorded_provider_outputs": True,
            },
            "packet": {
                "selected_calls": 14,
                "excluded_diagnostic_calls": 1,
                "total_calls": 15,
                "ceiling": 16,
                "input_tokens": 11577,
                "output_tokens": 25301,
            },
            "run_histories": {
                "compact_chains_verified": 8,
                "local_detail_cross_check": dict(local_detail_states),
            },
            "checks": checks.rows,
        }
    except Exception as exc:
        output = {
            "record_type": "ds1000_offline_verification/v1",
            "all_passed": False,
            "fatal_error": f"{type(exc).__name__}: {exc}",
            "passed": checks.passed,
            "total": len(checks.rows),
            "fit_or_train_calls": 0,
            "provider_calls": 0,
            "checks": checks.rows,
        }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
