#!/usr/bin/env python3
"""Run a queue of tasks overnight, bounded, resumable, and never blocking.

Loop Engine solves one task per invocation.  "Solve tasks overnight" needs
several, a spend bound that holds across all of them, and the property that one
task's failure does not end the night.  This driver supplies that without
touching the engine: each task is a separate `loop-engine solve`, so a crash,
a hang, or a provider outage costs one task rather than the queue.

It lives outside ``src/loop_engine`` deliberately -- it is an operator tool,
not a runtime capability, and it adds no conformance surface.

Design notes worth stating, because each is a decision rather than an oversight:

* **Per-task wall clock.** The engine has no deadline of its own
  (``DEADLINE_EXHAUSTED`` exists in solve_terminal.py and nothing raises it),
  so a task that hangs would otherwise hold the night.  Here a timeout kills
  the task and the queue moves on.
* **A queue-wide call ceiling.** ``--max-total-tokens`` is unusable on the
  Ollama route (model_token_preflight.py:196 raises token_bound_unavailable
  when no resolver exists), so model CALLS are the honest spend bound.
* **Resume by skipping completed work**, not by replaying reasoning.  Provider
  state was never captured, so a resumed task starts over; what resume buys is
  not repeating tasks that already finished.
* **Never blocks.** ``--unattended`` is passed always: there is nobody to ask.

Usage:
    python3 tools/overnight_queue.py tasks.txt --runs-dir DIR --workspace-root DIR
    (tasks.txt: one task file path per line, blank lines and # comments ignored)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

STATE_FILENAME = "overnight-queue.json"


def load_tasks(manifest: Path) -> list[Path]:
    """Read the task list, ignoring blanks and comments."""
    tasks = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        path = Path(text).expanduser()
        if not path.is_file():
            print(f"  ! skipping missing task file: {path}", flush=True)
            continue
        tasks.append(path)
    return tasks


def load_state(state_path: Path) -> dict:
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"completed": {}, "calls_used": 0}


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=1, sort_keys=True),
                         encoding="utf-8")
    os.replace(temporary, state_path)


def summarise(workspace: Path, runs_dir: Path) -> dict:
    """Report what a finished task left behind, ranked if it can be."""
    # The engine nests history under a per-run directory, so the checkpoint is
    # at runs_dir/<run_id>/checkpoint.json rather than directly in runs_dir.
    # Take the newest, since a runs_dir may accumulate several.
    candidates = sorted(runs_dir.glob("*/checkpoint.json"),
                        key=lambda p: p.stat().st_mtime if p.exists() else 0)
    data = {}
    if candidates:
        try:
            data = json.loads(candidates[-1].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    return {
        "attempts": len(data.get("attempts") or ()),
        "retained": data.get("retained", ""),
        "ranked": bool(data.get("retained_is_ranked")),
        "files": len(list(workspace.rglob("*.py"))) if workspace.is_dir() else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="file listing one task file per line")
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--task-timeout", type=int, default=1800,
                        help="seconds before a hung task is abandoned")
    parser.add_argument("--max-calls-per-task", type=int, default=120)
    parser.add_argument("--queue-call-budget", type=int, default=1200,
                        help="ceiling across the whole night")
    parser.add_argument("--max-passes", type=int, default=6)
    parser.add_argument("--fresh", action="store_true",
                        help="ignore prior state and rerun every task")
    args = parser.parse_args()

    manifest = Path(args.manifest).expanduser()
    runs_root = Path(args.runs_dir).expanduser()
    workspace_root = Path(args.workspace_root).expanduser()
    state_path = runs_root / STATE_FILENAME
    state = {"completed": {}, "calls_used": 0} if args.fresh else load_state(state_path)

    tasks = load_tasks(manifest)
    if not tasks:
        print("no runnable tasks in the manifest")
        return 1

    print(f"queue: {len(tasks)} task(s), "
          f"{len(state.get('completed') or {})} already completed, "
          f"budget {args.queue_call_budget} calls")
    started = time.time()
    for index, task in enumerate(tasks, 1):
        key = str(task.resolve())
        if key in (state.get("completed") or {}):
            print(f"[{index}/{len(tasks)}] skip (done): {task.name}", flush=True)
            continue
        if state.get("calls_used", 0) >= args.queue_call_budget:
            print(f"[{index}/{len(tasks)}] STOP: queue call budget exhausted "
                  f"({state['calls_used']}/{args.queue_call_budget})", flush=True)
            break

        workspace = workspace_root / f"task-{index:03d}"
        task_runs = runs_root / f"task-{index:03d}"
        print(f"[{index}/{len(tasks)}] {task.name} -> {workspace}", flush=True)
        command = [
            args.python, "-m", "loop_engine", "solve", "--file", str(task),
            "--quickstart", "--unattended", "--authorize-model-calls",
            "--workspace", str(workspace), "--runs-dir", str(task_runs),
            "--max-passes", str(args.max_passes),
            "--max-model-calls", str(args.max_calls_per_task),
            "--quiet-model-io",
        ]
        began = time.time()
        try:
            finished = subprocess.run(
                command, capture_output=True, text=True,
                timeout=args.task_timeout, shell=False)
            code, tail = finished.returncode, (finished.stdout or "")[-400:]
        except subprocess.TimeoutExpired:
            code, tail = 124, f"abandoned after {args.task_timeout}s"
        elapsed = round(time.time() - began, 1)

        result = summarise(workspace, task_runs)
        state.setdefault("completed", {})[key] = {
            "exit": code, "seconds": elapsed,
            # Record where this ran. Downstream tooling should never have to
            # infer the mapping from a naming convention.
            "workspace": str(workspace), "runs_dir": str(task_runs),
            "task_file": key, "index": index,
            **result,
        }
        # A task's call count is not reported back, so charge the ceiling: the
        # budget must never under-count, or the night can overrun it.
        state["calls_used"] = state.get("calls_used", 0) + args.max_calls_per_task
        save_state(state_path, state)
        mark = "ok" if code == 0 else f"exit {code}"
        retained = (result["retained"] or "").rsplit("/", 1)[-1] or "none"
        print(f"    {mark} in {elapsed}s | files {result['files']} | "
              f"attempts {result['attempts']} | retained {retained}"
              f"{'' if result['ranked'] else ' (unranked)'}", flush=True)
        if tail.strip() and code != 0:
            print(f"    last output: {tail.strip().splitlines()[-1][:120]}", flush=True)

    total = round(time.time() - started, 1)
    done = state.get("completed") or {}
    solved = sum(1 for v in done.values() if v.get("exit") == 0)
    with_work = sum(1 for v in done.values() if v.get("files"))
    print(f"\nnight finished in {total}s: {len(done)} task(s) run, "
          f"{solved} exited clean, {with_work} produced files")
    print(f"state: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
