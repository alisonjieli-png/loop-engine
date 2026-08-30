"""Verify the non-secret README journey against the public CLI."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


PINNED_IMAGE = (
    "python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3")


def _run(command: list[str], repository: Path) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repository / "src")
    return subprocess.run(
        command, cwd=repository, env=environment,
        capture_output=True, text=True, timeout=180)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repository = args.repository.resolve()
    readme = (repository / "README.md").read_text(encoding="utf-8")
    required = (
        "loop-engine doctor", "loop-engine models probe ollama_cloud",
        "loop-engine solve", "--workspace", "--runs-dir",
        "COMPLETED_VERIFIED", "CAPABILITY_GAP",
        "loop-engine --report @last", "Task build is not solve",
        "download ready-to-run task files",
    )
    missing = [value for value in required if value not in readme]
    help_result = _run(
        [sys.executable, "-m", "loop_engine", "--help"], repository)
    doctor_result = _run(
        [sys.executable, "-m", "loop_engine", "doctor", "--format", "json"],
        repository)
    doctor = json.loads(doctor_result.stdout) if doctor_result.returncode == 0 else {}
    with tempfile.TemporaryDirectory(prefix="loop-engine-readme-check-") as root:
        runs = Path(root) / "runs"
        no_key = _run([
            sys.executable, "-m", "loop_engine", "solve",
            "--text", "Create a verified artifact requiring an unavailable executor.",
            "--interaction-mode", "autonomous", "--runs-dir", str(runs),
            "--format", "json"], repository)
        no_key_value = json.loads(no_key.stdout)
        history_path = Path(no_key_value["run_history"]["path"])
        history_exists = history_path.is_dir()
    image = _run(
        ["docker", "image", "inspect", PINNED_IMAGE], repository)
    checks = {
        "readme_fragments_present": not missing,
        "cli_help_runs": help_result.returncode == 0
        and "solve a task" in help_result.stdout,
        "doctor_runs_without_provider_calls": doctor_result.returncode == 0
        and doctor.get("provider_calls_made") == 0,
        "no_key_solve_is_honest": no_key.returncode == 1
        and no_key_value.get("terminal_code") == "CAPABILITY_GAP"
        and not no_key_value.get("solved"),
        "no_key_run_history_exists": history_exists
        and no_key_value["run_history"].get("chain_intact"),
        "pinned_docker_image_present": image.returncode == 0,
    }
    report = {
        "record_type": "readme_quickstart_check/v1",
        "checks": checks, "missing_fragments": missing,
        "provider_calls": 0, "all_passed": all(checks.values()),
        "limitations": [
            "The external-provider step requires a separately authorized live run."],
    }
    print(json.dumps(report, indent=2))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
