#!/usr/local/bin/python3
"""Prepare a private worker run and invoke the existing public solve command."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import uuid

WORK_ROOT = Path("/work")
HARNESS_ROOT = Path("/tmp")

def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("a positive allocation is required")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--harness", choices=("baltor", "opencode", "gateway"), default="baltor")
    parser.add_argument("--max-model-calls", type=positive, required=True)
    parser.add_argument("--max-passes", type=positive, default=4)
    parser.add_argument("--authorize-project-commands", action="store_true")
    args = parser.parse_args(argv)
    root = WORK_ROOT
    task = args.task.absolute()
    if (not root.is_dir() or root.is_symlink() or not task.is_file() or task.is_symlink()
            or not task.resolve().is_relative_to(root.resolve())):
        parser.error("the task must be a regular file inside the mounted /work project")
    runs = root / "baltor-runs"
    if runs.is_symlink():
        parser.error("the run directory must not be a symlink")
    runs.mkdir(exist_ok=True)
    run = runs / uuid.uuid4().hex
    run.mkdir()
    for name in ("workspace", "history"):
        (run / name).mkdir()
    harness = HARNESS_ROOT / ("baltor-harness-" + run.name)
    harness.mkdir()
    command = ["loop-engine", "solve", "--file", str(task), "--quickstart", "--unattended",
               "--compile-provider", args.provider, "--model-id", args.model,
               "--max-model-calls", str(args.max_model_calls), "--max-passes", str(args.max_passes),
               "--workspace", str(run / "workspace"), "--runs-dir", str(run / "history"),
               "--format", "json", "--quiet-model-io"]
    if args.harness != "gateway":
        command += ["--embodiment", args.harness, "--embodiment-config", "/opt/baltor/" + args.harness + "-harness.json",
                    "--harness-work-dir", str(harness), "--harness-socket-dir", str(HARNESS_ROOT)]
    if args.authorize_project_commands:
        command.append("--allow-local-execution")
    os.execvpe(command[0], command, os.environ)


if __name__ == "__main__":
    main()
