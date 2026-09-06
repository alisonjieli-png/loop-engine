#!/usr/bin/env python3
"""Subdivide on FAILURE, because models cannot tell you a unit is too big.

The obvious design asks the model whether a unit is atomic and recurses when it
says no. Measured 2026-09-05, that design does not work: asked to divide "a
complete relational database engine -- SQL parser with joins and subqueries,
cost-based query planner, B-tree storage with page management, write-ahead log
with crash recovery, MVCC isolation, and a wire protocol server", the model
returned seven units and marked every one of them ATOMIC, including "B-tree
storage layer with page management". Nine units for a project-planning toolkit:
same, all atomic.

That is the session's recurring failure at one more level. A model cannot
reliably grade its own output, and it cannot reliably grade its own workload
either. Self-report is not evidence.

So size is decided the only way that carries evidence: by ATTEMPTING the unit.
A unit that solves was small enough. A unit that fails is subdivided and its
children attempted, recursively, until they solve or the depth ceiling is hit.
This is ADaPT's as-needed decomposition (arXiv:2311.05772) -- decompose when
the executor actually fails, not when it predicts it might -- and it is
self-calibrating: the same goal divides further for a weak model than a strong
one, with nobody having to know in advance which they have.

The cost is real: a failed attempt is spent before its subdivision begins. That
is the price of evidence over prediction, and it is bounded by the call budget
and the depth ceiling.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from recursive_divide import _check_graph, choose_strategy, divide_once  # noqa: E402


def attempt(task_text: str, work: Path, runs: Path, python: str,
            calls: int, passes: int, timeout: int) -> tuple:
    """Run one unit through the engine. Returns (solved, files, seconds)."""
    work.mkdir(parents=True, exist_ok=True)
    task_file = work / "task.txt"
    task_file.write_text(task_text, encoding="utf-8")
    began = time.time()
    try:
        done = subprocess.run(
            [python, "-m", "loop_engine", "solve", "--file", str(task_file),
             "--quickstart", "--unattended", "--authorize-model-calls",
             "--workspace", str(work / "ws"), "--runs-dir", str(runs),
             "--max-passes", str(passes), "--max-model-calls", str(calls),
             "--quiet-model-io"],
            capture_output=True, text=True, timeout=timeout, shell=False)
        code = done.returncode
    except subprocess.TimeoutExpired:
        code = 124
    produced = len(list((work / "ws").rglob("*.py"))) if (work / "ws").is_dir() else 0
    return code == 0, produced, round(time.time() - began, 1)


def solve_adaptively(task_text: str, node: str, depth: int, args,
                     budget: dict, report: list) -> bool:
    """Attempt; on failure subdivide and attempt the children."""
    pad = "  " * depth
    if budget["calls"] <= 0:
        report.append(f"{pad}[{node}] SKIPPED - call budget exhausted")
        return False
    work = Path(args.work_root) / node.replace(".", "_")
    runs = Path(args.runs_root) / node.replace(".", "_")
    solved, files, seconds = attempt(
        task_text, work, runs, args.python, args.max_calls_per_unit,
        args.max_passes, args.task_timeout)
    budget["calls"] -= args.max_calls_per_unit
    report.append(f"{pad}[{node}] {'SOLVED' if solved else 'failed'} "
                  f"in {seconds}s, {files} file(s)")
    if solved:
        budget["solved"].append({"node": node, "depth": depth,
                                 "workspace": str(work / "ws")})
        return True
    if depth >= args.max_depth:
        report.append(f"{pad}  ! depth ceiling reached; not dividing further")
        budget["unsolved"].append({"node": node, "reason": "depth ceiling"})
        return False

    strategy, reason = choose_strategy(task_text, args.model)
    if strategy == "none":
        # It failed, and the model still says it is one unit. Divide anyway --
        # the failure is the evidence, and its opinion has already been wrong.
        strategy = "pipeline"
        reason = "forced: unit failed, so 'none' is contradicted by evidence"
    report.append(f"{pad}  dividing ({strategy}: {reason[:60]})")
    units, error = divide_once(task_text, args.model, strategy)
    if error or len(units) < 2:
        report.append(f"{pad}  ! cannot divide ({error or 'returned one unit'})")
        budget["unsolved"].append({"node": node, "reason": error or "indivisible"})
        return False

    ordered = _dependency_order(units)
    any_solved = False
    for unit in ordered:
        child_text = unit["task"]
        if unit.get("verify"):
            child_text += f"\n\n# Verification: {unit['verify']}"
        if solve_adaptively(child_text, f"{node}.{unit['id']}", depth + 1,
                            args, budget, report):
            any_solved = True
    return any_solved


def _dependency_order(units: list) -> list:
    by_id = {u["id"]: u for u in units}
    state, ordered = {}, []

    def visit(uid):
        if state.get(uid) == "done" or uid not in by_id:
            return
        state[uid] = "open"
        for dep in by_id[uid].get("depends_on") or ():
            if state.get(dep) != "open":
                visit(dep)
        state[uid] = "done"
        ordered.append(by_id[uid])

    for unit in units:
        visit(unit["id"])
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--model", default="deepseek-v4-flash:0731")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-calls-per-unit", type=int, default=50)
    parser.add_argument("--max-passes", type=int, default=3)
    parser.add_argument("--task-timeout", type=int, default=400)
    parser.add_argument("--call-budget", type=int, default=600)
    args = parser.parse_args()

    budget = {"calls": args.call_budget, "solved": [], "unsolved": []}
    report: list = []
    print(f"adaptive divide: budget {args.call_budget} calls, "
          f"depth ceiling {args.max_depth}\n")
    solve_adaptively(args.goal, "root", 0, args, budget, report)
    print("\n".join(report))
    print(f"\nsolved {len(budget['solved'])} unit(s); "
          f"{len(budget['unsolved'])} unsolved; "
          f"{max(0, budget['calls'])} calls left")
    out = Path(args.work_root) / "adaptive-report.json"
    out.write_text(json.dumps(
        {"record_type": "adaptive_division/v1", "goal": args.goal,
         "solved": budget["solved"], "unsolved": budget["unsolved"],
         "report": report}, indent=1), encoding="utf-8")
    print(f"report: {out}")
    return 0 if budget["solved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
