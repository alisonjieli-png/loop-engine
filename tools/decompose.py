#!/usr/bin/env python3
"""Divide one complex goal into small overnight tasks, in dependency order.

The engine's step vocabulary is orient -> route -> how -> act -> verify ->
decide_next.  There is no DIVIDE.  A task arrives whole and is attempted whole,
and today's measurements say that is exactly where it fails: a two-line
function solved clean in 21 seconds, while larger tasks produced zero files
across repeated runs.  Nothing in the loop makes a large task smaller.

This supplies that step, outside the runtime, so it can be used and measured
before anything is wired into the verdict path.

Three things make it more than a prompt:

* **The plan is a dependency graph, so it can be CHECKED.**  A decomposition is
  exactly the shape `core.artifact_constraints.schedule/v1` validates: unknown
  dependencies, self-dependencies and cycles are refused before a single
  provider call is spent on the work.  A plan that cannot be executed is
  rejected while it is still cheap.
* **Order is derived, not asked for.**  The model proposes units and
  dependencies; topological order is computed here.  Ordering is arithmetic,
  and today's evidence is that models are reliable at code and unreliable at
  arithmetic they perform by hand.
* **Each unit is written as a standalone task file.**  A unit that cannot be
  stated without reference to its siblings has not been divided, and the
  overnight queue runs each unit as its own solve, so one failure costs one
  unit rather than the night.

Usage:
    python3 tools/decompose.py --goal "..." --out-dir DIR [--model MODEL]
    python3 tools/decompose.py --plan plan.json --out-dir DIR   # skip the model
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.core.artifact_constraints import verify_constraint  # noqa: E402

PLAN_SCHEMA = {
    "units": [
        {
            "id": "short_slug",
            "duration": 1,
            "depends_on": ["ids of units that must finish first"],
            "title": "one line",
            "task": "a COMPLETE standalone task statement, understandable "
                    "without reading any other unit",
            "verify": "how a machine checks this unit, without a human",
        }
    ]
}

PROMPT = """Divide this goal into the SMALLEST units that can each be solved and
verified independently overnight, with no human present.

GOAL:
{goal}

Rules that matter more than completeness:
- Every unit must be solvable on its own. If a unit cannot be stated without
  referring to another unit's internals, it is not yet divided.
- Prefer more, smaller units. A unit that produces one function and its tests
  is the right size. A unit that produces "the system" is not.
- Every unit needs a machine-checkable verification. If the only way to know it
  worked is for a person to look at it, say so in `verify` and keep the unit
  small enough that the person's job is trivial.
- `depends_on` lists unit ids only. No cycles. A unit depending on nothing runs
  first.
- `duration` is a rough effort in arbitrary units, minimum 1.

Return ONLY this JSON:
{schema}
"""


def order_units(units: list) -> tuple:
    """Topologically order units, returning (ordered, error)."""
    by_id = {u["id"]: u for u in units}
    state: dict = {}
    ordered: list = []

    def visit(uid: str, trail: tuple) -> str:
        if state.get(uid) == "done":
            return ""
        if state.get(uid) == "open":
            return f"cycle: {' -> '.join(trail + (uid,))}"
        state[uid] = "open"
        for dep in by_id[uid].get("depends_on") or ():
            if dep not in by_id:
                return f"{uid} depends on unknown unit {dep!r}"
            error = visit(dep, trail + (uid,))
            if error:
                return error
        state[uid] = "done"
        ordered.append(by_id[uid])
        return ""

    for unit in units:
        error = visit(unit["id"], ())
        if error:
            return (), error
    return tuple(ordered), ""


def validate_plan(units: list) -> tuple:
    """Refuse an unexecutable plan before any work is spent on it."""
    if not units:
        return False, "plan contains no units"
    seen = set()
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            return False, f"unit #{index} is not an object"
        for field in ("id", "task"):
            if not str(unit.get(field) or "").strip():
                return False, f"unit #{index} has no {field}"
        if unit["id"] in seen:
            return False, f"duplicate unit id {unit['id']!r}"
        seen.add(unit["id"])
    # Reuse the engine-owned schedule checker: a plan IS a dependency graph,
    # and the same predicate that rejects an impossible project schedule
    # rejects an impossible decomposition.
    probe = [{"id": u["id"], "duration": max(1, int(u.get("duration") or 1)),
              "depends_on": list(u.get("depends_on") or [])} for u in units]
    start = 0
    for item in probe:                       # give the checker concrete dates
        item["start"] = start
        item["end"] = start + item["duration"]
        start = item["end"]
    result = verify_constraint(
        "schedule/v1", json.dumps({"tasks": probe}).encode())
    cycle_or_unknown = [v for v in result.violations
                        if "cycle" in v or "unknown task" in v
                        or "itself" in v]
    if cycle_or_unknown:
        return False, "; ".join(cycle_or_unknown)
    return True, ""


def request_plan(goal: str, model: str) -> tuple:
    """Ask the configured provider for a decomposition."""
    from loop_engine.core import ollama_client

    key = ollama_client.load_api_key()
    if not key:
        return [], "no provider key found (OLLAMA_API_KEY)"
    prompt = PROMPT.format(
        goal=goal, schema=json.dumps(PLAN_SCHEMA, indent=1))
    result = ollama_client.chat(prompt, model=model, api_key=key, timeout=300)
    if not result.ok:
        return [], f"provider call failed: {result.error[:200]}"
    text = (result.text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    try:
        payload = json.loads(text)
    except ValueError as exc:
        return [], f"plan was not valid JSON: {exc}"
    units = payload.get("units") if isinstance(payload, dict) else payload
    if not isinstance(units, list):
        return [], "plan contained no unit list"
    return units, ""


def write_tasks(units: tuple, out_dir: Path, goal: str) -> list:
    """Write one standalone task file per unit, plus a queue manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, unit in enumerate(units, 1):
        path = out_dir / f"{index:02d}-{unit['id']}.txt"
        depends = ", ".join(unit.get("depends_on") or ()) or "nothing"
        body = [
            unit["task"].strip(),
            "",
            f"# Unit {index} of {len(units)} from a larger goal.",
            f"# Overall goal (context only, do NOT solve it here): {goal}",
            f"# This unit depends on: {depends}",
        ]
        if unit.get("verify"):
            body.append(f"# Verification for this unit: {unit['verify']}")
        body.append(
        "# ENVIRONMENT: the sandbox runs a bare Python interpreter with "
        "the standard library ONLY. Write tests with unittest and run "
        "them via `python3 -m unittest`. pytest is NOT installed, so a "
        "pytest test file cannot execute and the unit is reported as "
        "failed even when its code is correct (measured 2026-09-05). "
        "Do not import any third-party package.")
        body.append("# Solve ONLY this unit. Keep it self-contained.")
        path.write_text("\n".join(body) + "\n", encoding="utf-8")
        paths.append(str(path))
    manifest = out_dir / "queue.txt"
    manifest.write_text("\n".join(paths) + "\n", encoding="utf-8")
    (out_dir / "plan.json").write_text(
        json.dumps({"record_type": "decomposition/v1", "goal": goal,
                    "units": list(units)}, indent=1), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal")
    parser.add_argument("--plan", help="a plan.json to use instead of a model")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default="deepseek-v4-flash:0731")
    args = parser.parse_args()

    if args.plan:
        payload = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        units = payload.get("units", payload)
        goal = payload.get("goal", args.goal or "(from plan)")
    elif args.goal:
        goal = args.goal
        units, error = request_plan(goal, args.model)
        if error:
            print(f"decomposition failed: {error}")
            return 1
    else:
        print("need --goal or --plan")
        return 2

    ok, error = validate_plan(units)
    if not ok:
        print(f"plan REFUSED before any work was spent: {error}")
        return 1
    ordered, error = order_units(units)
    if error:
        print(f"plan REFUSED: {error}")
        return 1

    paths = write_tasks(ordered, Path(args.out_dir), goal)
    print(f"divided into {len(paths)} unit(s), dependency-ordered:")
    for index, unit in enumerate(ordered, 1):
        deps = ",".join(unit.get("depends_on") or ()) or "-"
        print(f"  {index:2}. {unit['id']:24} deps={deps:18} "
              f"{str(unit.get('title') or '')[:44]}")
    print(f"\nqueue manifest: {Path(args.out_dir) / 'queue.txt'}")
    print(f"run it: python3 tools/overnight_queue.py "
          f"{Path(args.out_dir) / 'queue.txt'} --runs-dir RUNS "
          f"--workspace-root WS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
