"""Materialize the smallest tracked DS-1000 evidence package.

This reads the preserved local results and writes non-secret compact evidence.
It never imports a model or data-science library, executes benchmark code,
fits a model, trains a model, or contacts a provider.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ARTIFACTS = HERE / "artifacts"
SELECTED_ID = "ds1000-full-v1-20260825T150857Z"
CORRECTION_ID = SELECTED_ID + "-extractor-whitespace-correction-v1"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")


def _digest_body(row: dict) -> str:
    body = dict(row)
    body.pop("event_digest", None)
    return _sha256_bytes(
        json.dumps(body, sort_keys=True, default=str).encode())


def _compact_chain(run_dir: Path, source_kind: str,
                   problem_id: int) -> dict:
    manifest_path = run_dir / "manifest.json"
    events_path = run_dir / "events.jsonl"
    manifest = _load(manifest_path)
    event_digests = []
    previous_digests = []
    event_types = Counter()
    previous = ""
    rows = 0
    with events_path.open(encoding="utf-8") as stream:
        for expected_sequence, line in enumerate(stream):
            row = json.loads(line)
            if row["sequence_number"] != expected_sequence:
                raise ValueError(
                    f"{manifest['run_id']} has a sequence discontinuity")
            if row["prev_digest"] != previous:
                raise ValueError(
                    f"{manifest['run_id']} has a broken previous digest")
            if row["event_digest"] != _digest_body(row):
                raise ValueError(
                    f"{manifest['run_id']} has a body digest mismatch")
            previous_digests.append(row["prev_digest"])
            event_digests.append(row["event_digest"])
            event_types[row["event_type"]] += 1
            previous = row["event_digest"]
            rows += 1
    if (rows != manifest["events"]
            or previous != manifest["head_digest"]
            or manifest.get("committed") is not True):
        raise ValueError(f"{manifest['run_id']} manifest does not match events")
    sequence_body = {
        "event_digests": event_digests,
        "previous_digests": previous_digests,
    }
    return {
        "record_type": "run_history_compact_chain/v1",
        "source_kind": source_kind,
        "problem_id": problem_id,
        "run_id": manifest["run_id"],
        "manifest": manifest,
        "event_digests": event_digests,
        "previous_digests": previous_digests,
        "sequence_sha256": _sha256_bytes(json.dumps(
            sequence_body, sort_keys=True,
            separators=(",", ":")).encode()),
        "event_type_counts": dict(sorted(event_types.items())),
        "events_jsonl_sha256": _sha256_file(events_path),
        "manifest_json_sha256": _sha256_file(manifest_path),
        "source_body_and_links_verified": True,
    }


def _canvas_evidence(canvas: dict, role: str) -> dict:
    canvas_view = canvas["canvas"]
    return {
        "record_type": "ds1000_canvas_evidence/v1",
        "role": role,
        "plan_digest": canvas["plan_digest"],
        "plan": canvas["plan"],
        "canonical": canvas_view["canonical"],
        "json": canvas_view["json"],
        "mermaid": canvas_view["mermaid"],
        "trace": canvas["trace"],
        "evaluation": canvas["evaluation"],
    }


def _report_evidence(report_path: Path) -> dict:
    report = _load(report_path)
    summary_keys = (
        "record_type", "run_id", "loops", "events", "max_depth",
        "model_calls", "total_tokens", "tokens_by_provider",
        "event_families", "chain_intact",
    )
    return {
        "record_type": "ds1000_compact_loop_report/v1",
        "report": {key: report.get(key) for key in summary_keys},
        "source_report_sha256": _sha256_file(report_path),
        "source_report_bytes": report_path.stat().st_size,
    }


def _selected_task_evidence(source_dir: Path, artifact_root: Path,
                            task_summary: dict) -> tuple[dict, dict]:
    problem_id = int(task_summary["problem_id"])
    task_dir = source_dir / "tasks" / f"problem-{problem_id}"
    outcome = _load(task_dir / "outcome.json")
    playback_source = task_dir / "playback.txt"
    playback_relative = Path("selected/playback") / f"problem-{problem_id}.txt"
    playback_target = artifact_root / playback_relative
    playback_target.parent.mkdir(parents=True, exist_ok=True)
    playback_target.write_bytes(playback_source.read_bytes())
    report_relative = Path("selected/reports") / f"problem-{problem_id}.json"
    _write_json(
        artifact_root / report_relative,
        _report_evidence(task_dir / "loop-report.json"))

    canvas_paths = []
    evaluation_rows = []
    for evaluation in outcome["evaluations"]:
        role = evaluation["role"]
        canvas_relative = (
            Path("selected/canvas")
            / f"problem-{problem_id}-{role}.json")
        _write_json(
            artifact_root / canvas_relative,
            _canvas_evidence(evaluation["canvas"], role))
        canvas_paths.append(canvas_relative.as_posix())
        evaluation_rows.append({
            "role": role,
            "error": evaluation["error"],
            "stopped": evaluation["stopped"],
            "passed": evaluation["canvas"]["evaluation"]["passed"],
            "status": evaluation["canvas"]["evaluation"]["status"],
            "result": evaluation["canvas"]["evaluation"][
                "upstream_result"],
            "candidate_sha256": evaluation["canvas"]["evaluation"][
                "candidate_sha256"],
        })

    model_spawned_loops = []
    for role, call in outcome["model_spawned_loops"].items():
        candidate = call.get("candidate") or {}
        raw_response = str(candidate.get("raw_response", ""))
        model_spawned_loops.append({
            "role": role,
            "spawned_loop_id": call["spawned_loop_id"],
            "physical_calls": call["physical_calls"],
            "prompt_sha256": call["prompt_sha256"],
            "candidate_code_sha256": candidate.get("code_sha256", ""),
            "raw_response_sha256": _sha256_bytes(raw_response.encode()),
            "consumed_candidate_refs": call["consumed_candidate_refs"],
            "consumption": call["spawned_loop_intelligence"]["consumption"],
            "gateway_attempts": call["gateway_result"]["attempts"],
        })

    evidence = {
        "record_type": "ds1000_selected_task_evidence/v1",
        "problem_id": problem_id,
        "library": outcome["library"],
        "run_id": outcome["run_id"],
        "passed": outcome["passed"],
        "selected_role": outcome["selected_role"],
        "selected_candidate_sha256": outcome["selected_candidate_sha256"],
        "physical_model_calls": outcome["physical_model_calls"],
        "input_tokens": outcome["input_tokens"],
        "output_tokens": outcome["output_tokens"],
        "total_tokens": outcome["total_tokens"],
        "accounting_complete": outcome["accounting_complete"],
        "failover": outcome["failover"],
        "maximum_output_tokens": outcome["maximum_output_tokens"],
        "model": outcome["model"],
        "provider": outcome["provider"],
        "source_commit": outcome["source_commit"],
        "runtime": outcome["runtime"],
        "error": outcome["error"],
        "failures_preserved": outcome["failures_preserved"],
        "full_path": outcome["full_path"],
        "model_spawned_loops": model_spawned_loops,
        "evaluations": evaluation_rows,
        "canvas_paths": canvas_paths,
        "report_path": report_relative.as_posix(),
        "playback_path": playback_relative.as_posix(),
        "playback_sha256": _sha256_file(playback_source),
        "playback_lines": len(playback_source.read_text(
            encoding="utf-8").splitlines()),
        "loop_tree_sha256": _sha256_file(task_dir / "loop-tree.mmd"),
        "html_report_sha256": _sha256_file(task_dir / "report.html"),
    }
    run_history_dir = source_dir / "run-histories" / outcome["run_id"]
    return evidence, _compact_chain(
        run_history_dir, "selected", problem_id)


def _correction_task_evidence(source_dir: Path, artifact_root: Path,
                              task_summary: dict) -> tuple[dict, dict]:
    problem_id = int(task_summary["problem_id"])
    task_dir = source_dir / "tasks" / f"problem-{problem_id}"
    outcome = _load(task_dir / "outcome.json")
    playback_source = task_dir / "playback.txt"
    playback_relative = (
        Path("correction/playback") / f"problem-{problem_id}.txt")
    playback_target = artifact_root / playback_relative
    playback_target.parent.mkdir(parents=True, exist_ok=True)
    playback_target.write_bytes(playback_source.read_bytes())
    report_relative = (
        Path("correction/reports") / f"problem-{problem_id}.json")
    _write_json(
        artifact_root / report_relative,
        _report_evidence(task_dir / "loop-report.json"))
    canvas_relative = (
        Path("correction/canvas") / f"problem-{problem_id}.json")
    _write_json(
        artifact_root / canvas_relative,
        _canvas_evidence(outcome["canvas"], outcome["selected_role"]))

    evidence = {
        "record_type": "ds1000_correction_task_evidence/v1",
        "problem_id": problem_id,
        "library": outcome["library"],
        "run_id": outcome["run_id"],
        "parent_run_id": outcome["parent_run_id"],
        "parent_campaign_id": outcome["parent_campaign_id"],
        "selected_role": outcome["selected_role"],
        "original_reported_passed": outcome["original_reported_passed"],
        "corrected_passed": outcome["corrected_passed"],
        "original_candidate_sha256": outcome["original_candidate_sha256"],
        "corrected_candidate_sha256": outcome["corrected_candidate_sha256"],
        "corrected_upstream_result": outcome["corrected_upstream_result"],
        "correction": outcome["correction"],
        "physical_model_calls": outcome["physical_model_calls"],
        "provider_outputs_reused": outcome["provider_outputs_reused"],
        "runtime": outcome["runtime"],
        "recorded_spawned_loops": outcome["recorded_spawned_loops"],
        "full_regrade_path": outcome["full_regrade_path"],
        "canvas_path": canvas_relative.as_posix(),
        "report_path": report_relative.as_posix(),
        "playback_path": playback_relative.as_posix(),
        "playback_sha256": _sha256_file(playback_source),
        "playback_lines": len(playback_source.read_text(
            encoding="utf-8").splitlines()),
        "html_report_sha256": _sha256_file(task_dir / "report.html"),
    }
    run_history_dir = source_dir / "run-histories" / outcome["run_id"]
    return evidence, _compact_chain(
        run_history_dir, "correction", problem_id)


def main() -> int:
    if ARTIFACTS.exists():
        raise FileExistsError(
            f"tracked artifact directory already exists: {ARTIFACTS}")
    selected_dir = RESULTS / SELECTED_ID
    correction_dir = RESULTS / CORRECTION_ID
    selected_summary = _load(selected_dir / "summary.json")
    correction_summary = _load(correction_dir / "summary.json")

    with tempfile.TemporaryDirectory(
            prefix="ds1000-artifacts-", dir=HERE) as temporary:
        root = Path(temporary)
        _write_json(root / "selected-summary.json", selected_summary)
        _write_json(root / "correction-summary.json", correction_summary)
        task_evidence = {"record_type": "ds1000_task_evidence/v1",
                         "selected": [], "correction": []}
        chains = {"record_type": "run_history_compact_chains/v1",
                  "chains": []}
        for task_summary in selected_summary["tasks"]:
            task, chain = _selected_task_evidence(
                selected_dir, root, task_summary)
            task_evidence["selected"].append(task)
            chains["chains"].append(chain)
        for task_summary in correction_summary["tasks"]:
            task, chain = _correction_task_evidence(
                correction_dir, root, task_summary)
            task_evidence["correction"].append(task)
            chains["chains"].append(chain)
        _write_json(root / "task-evidence.json", task_evidence)
        _write_json(root / "run-history-chains.json", chains)

        entries = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == "manifest.json":
                continue
            entries.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            })
        manifest_body = {
            "record_type": "ds1000_tracked_artifact_manifest/v1",
            "selected_campaign_id": SELECTED_ID,
            "correction_id": CORRECTION_ID,
            "contains_task_reference_solutions": False,
            "contains_evaluator_bodies": False,
            "files": entries,
        }
        manifest_body["files_digest"] = _sha256_bytes(json.dumps(
            entries, sort_keys=True, separators=(",", ":")).encode())
        _write_json(root / "manifest.json", manifest_body)
        os.replace(root, ARTIFACTS)
    print(json.dumps({
        "record_type": "ds1000_evidence_materialization/v1",
        "artifact_root": str(ARTIFACTS),
        "files": len(list(ARTIFACTS.rglob("*"))),
        "model_calls": 0,
        "fit_or_train_calls": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

