"""Exercise the documented solve CLI through a local HTTP provider fixture."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

from loop_engine.core.run_history import load_saved_run_bundle
from loop_engine.code_nodes.loop_report import report_from_run

from run_acceptance import _task_a, _task_b


class _ProviderHandler(BaseHTTPRequestHandler):
    answers: list[str] = []

    def do_POST(self):  # noqa: N802 - standard library protocol
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        if not self.answers:
            self.send_error(500, "fixture answer queue exhausted")
            return
        content = self.answers.pop(0)
        body = json.dumps({
            "model": "fixture-model",
            "choices": [{"message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--installed-package", action="store_true",
                        help="use the interpreter's installed wheel, not src")
    args = parser.parse_args()
    root = args.output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise SystemExit("output root must be empty")
    intake, answers = _task_a()
    fixtures = Path(__file__).resolve().parent / "fixtures"
    dataset_intake, dataset_answers = _task_b(fixtures)
    _ProviderHandler.answers = list(answers)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    settings = {
        "version": 1,
        "models": {
            "default_thinking_power": "medium",
            "allow_local_counted_generation": True,
            "providers": [{
                "id": "acceptance",
                "kind": "custom",
                "endpoint": f"http://127.0.0.1:{port}/v1",
                "model": "fixture-model",
                "wire": "openai", "locality": "local",
                "credential_env": "", "counts_as_evidence": False,
                "maximum_output_tokens": 4096,
                "maximum_output_source": "local acceptance fixture contract",
                "purposes": ["counted_generation", "decide_label"],
            }],
            "tiers": {
                "medium": {"routes": ["custom.acceptance"],
                           "timeout_seconds": 30, "max_attempts": 1}},
            "escalation": {"enabled": False},
        },
        "operating": {
            "access_mode": "offline",
            "construction_and_execution_mode": "sandbox_generate"},
        "history": {"runs_dir": str(root / "runs"),
                    "save_run_history": True},
    }
    settings_path = root / "loop-engine.yaml"
    settings_path.write_text(yaml.safe_dump(settings, sort_keys=False))
    repository = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    if args.installed_package:
        environment.pop("PYTHONPATH", None)
    else:
        environment["PYTHONPATH"] = str(repository / "src")
    command_cwd = root if args.installed_package else repository
    command = [
        sys.executable, "-m", "loop_engine", "solve",
        "--text", intake.text,
        "--settings-file", str(settings_path),
        "--workspace", str(root / "workspace"),
        "--runs-dir", str(root / "runs"),
        "--interaction-mode", "autonomous",
        "--authorize-model-calls", "--max-model-calls", str(len(answers)),
        "--max-total-tokens", "100000",
        "--model-route", "custom.acceptance",
        "--model-id", "fixture-model", "--format", "json",
    ]
    task_file = root / "task.txt"
    task_file.write_text(intake.text + "\n")
    file_command = list(command)
    text_index = file_command.index("--text")
    file_command[text_index:text_index + 2] = ["--file", str(task_file)]
    file_command[file_command.index(str(root / "workspace"))] = str(
        root / "workspace-from-file")
    file_command[file_command.index(str(root / "runs"))] = str(
        root / "runs-from-file")
    dataset_task_file = root / "inventory-task.txt"
    dataset_task_file.write_text(dataset_intake.goal + "\n")
    dataset_command = list(command)
    text_index = dataset_command.index("--text")
    dataset_command[text_index:text_index + 2] = [
        "--file", str(dataset_task_file),
        "--dataset", dataset_intake.dataset,
        "--allow-source-to-model"]
    dataset_command[dataset_command.index(str(root / "workspace"))] = str(
        root / "dataset-workspace")
    dataset_command[dataset_command.index(str(root / "runs"))] = str(
        root / "dataset-runs")
    try:
        completed = subprocess.run(
            command, cwd=command_cwd, env=environment, capture_output=True,
            text=True, timeout=180)
        _ProviderHandler.answers = list(answers)
        completed_file = subprocess.run(
            file_command, cwd=command_cwd, env=environment,
            capture_output=True, text=True, timeout=180)
        _ProviderHandler.answers = list(dataset_answers)
        completed_dataset = subprocess.run(
            dataset_command, cwd=command_cwd, env=environment,
            capture_output=True, text=True, timeout=180)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    if completed.returncode != 0:
        raise SystemExit(
            f"CLI solve failed ({completed.returncode}): {completed.stderr}\n"
            f"{completed.stdout[-2000:]}")
    if completed_file.returncode != 0:
        raise SystemExit(
            f"file CLI solve failed ({completed_file.returncode}): "
            f"{completed_file.stderr}\n{completed_file.stdout[-2000:]}")
    if completed_dataset.returncode != 0:
        raise SystemExit(
            f"dataset task-file CLI solve failed "
            f"({completed_dataset.returncode}): "
            f"{completed_dataset.stderr}\n{completed_dataset.stdout[-2000:]}")
    result = json.loads(completed.stdout)
    file_result = json.loads(completed_file.stdout)
    dataset_result = json.loads(completed_dataset.stdout)
    if result["terminal_code"] != "COMPLETED_VERIFIED":
        raise SystemExit(f"unexpected terminal result: {result['terminal_code']}")
    if not all(Path(item["path"]).is_file() and item["verified"]
               for item in result["artifacts"]):
        raise SystemExit("CLI result references a missing or unverified artifact")
    if result["model_calls"] != len(answers):
        raise SystemExit("CLI model-call count differs from the physical fixture")
    if not all(row["provider"] == "acceptance"
               and row["model"] == "fixture-model"
               for row in result["model_usage"]):
        raise SystemExit("CLI model route identity was not preserved")
    if (file_result["terminal_code"] != "COMPLETED_VERIFIED"
            or not all(Path(item["path"]).is_file() and item["verified"]
                       for item in file_result["artifacts"])):
        raise SystemExit("task-file CLI path did not produce verified artifacts")
    if (dataset_result["terminal_code"] != "COMPLETED_VERIFIED"
            or dataset_result["compiled_task"]["original_input"]
            .strip() != dataset_intake.goal.strip()
            or not all(Path(item["path"]).is_file() and item["verified"]
                       for item in dataset_result["artifacts"])):
        raise SystemExit(
            "task-file plus dataset CLI path did not preserve and solve the task")
    bound_results = (
        (root / "runs", result),
        (root / "runs-from-file", file_result),
        (root / "dataset-runs", dataset_result),
    )
    for run_root, saved_result in bound_results:
        bundle = load_saved_run_bundle(str(run_root), saved_result["run_id"])
        report = report_from_run(str(run_root), saved_result["run_id"])
        if (bundle.outcome["terminal_code"] != "COMPLETED_VERIFIED"
                or report.product_summary()["terminal_code"]
                != "COMPLETED_VERIFIED"
                or len(report.product_summary()["artifacts"])
                != len(saved_result["artifacts"])):
            raise SystemExit(
                "saved CLI bundle or report lost the product result")
    result["acceptance_environment"] = {
        "provider": "local HTTP contract fixture",
        "live_external_provider_proven": False,
        "command": ["loop-engine", *command[4:]],
    }
    evidence = root / "cli-acceptance.json"
    evidence.write_text(json.dumps(result, indent=2) + "\n")
    file_evidence = root / "cli-file-acceptance.json"
    file_evidence.write_text(json.dumps(file_result, indent=2) + "\n")
    dataset_evidence = root / "cli-dataset-task-acceptance.json"
    dataset_evidence.write_text(json.dumps(dataset_result, indent=2) + "\n")
    print(json.dumps({
        "record_type": "product_cli_acceptance/v1",
        "terminal_code": result["terminal_code"],
        "file_terminal_code": file_result["terminal_code"],
        "dataset_file_terminal_code": dataset_result["terminal_code"],
        "run_id": result["run_id"], "artifacts": len(result["artifacts"]),
        "model_calls": result["model_calls"],
        "tool_calls": result["tool_calls"],
        "run_history_chain_intact": result["run_history"]["chain_intact"],
        "saved_product_outcomes_bound": len(bound_results),
        "evidence": str(evidence),
        "file_evidence": str(file_evidence),
        "dataset_evidence": str(dataset_evidence),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
