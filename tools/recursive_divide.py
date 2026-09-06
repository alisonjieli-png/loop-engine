#!/usr/bin/env python3
"""Subdivide a goal until every leaf is small enough for the executor.

Decomposition depth is not a property of the task. It is a property of the
RELATIONSHIP between the task and whoever is solving it: what a frontier model
handles in one unit, a medium model needs three for. So there is no fixed size
here, and no fixed depth -- a unit that is still too large is divided again,
recursively, and a unit that already fits is left alone.

The recursion needs a stopping rule that is neither a constant nor a guess.
Three, in priority order:

1. **Atomic by judgement.** The unit is one deliverable with one verification.
   This is the real stopping condition, and it is asked per unit rather than
   assumed by depth.
2. **No progress.** A subdivision that returns a single unit, or units that
   restate the parent, has not divided anything. Recursing further would spend
   calls to produce the same tree, so it stops.
3. **A depth ceiling.** Purely a runaway guard, not a design parameter.
   Reaching it is reported, never silently accepted, because a task that is
   still too big at the ceiling is a task the executor cannot take on.

Splitting is not free. Every split adds a context-passing boundary and another
place to fail, and the measured benefit of decomposition shrinks as the
executor gets stronger (arXiv:2602.04853; and arXiv:2507.03347 found
unstructured reasoning beating imposed structure by up to 18.9%). So the
judgement below is deliberately biased toward STOPPING: a unit is divided only
when it plainly does not fit, not whenever it could be.

Usage:
    python3 tools/recursive_divide.py --goal "..." --out-dir DIR
        [--max-depth 3] [--model M] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from strategies import STRATEGIES, catalogue_text, strategy_prompt  # noqa: E402

from loop_engine.core.artifact_constraints import verify_constraint  # noqa: E402

DIVIDE_PROMPT = """Divide this unit of work into the smallest pieces that can
each be solved and verified independently, by a medium-capability model working
unattended.

UNIT:
{goal}

{strategy}
Rules:
- Each piece must be solvable WITHOUT reading any other piece's internals.
- `depends_on` lists ids from THIS division only. No cycles.
- If this unit is already one coherent deliverable with one verification,
  return exactly one piece: the unit unchanged. That is a correct answer.

Return ONLY:
{{"units":[{{"id":"slug","depends_on":[],"title":"one line",
"task":"complete standalone statement","verify":"machine-checkable check",
"atomic":true}}]}}

Set "atomic" false ONLY if the piece plainly still contains several
deliverables that a medium model could not finish in one go.
"""

SELECT_PROMPT = """Choose ONE decomposition strategy for this unit.

UNIT:
{goal}

EXECUTOR: a medium model working unattended; it solves small self-contained
units reliably and large multi-part tasks poorly.

{catalogue}

"none" is correct whenever this is one coherent deliverable with one
verification. Return ONLY: {{"strategy":"<name>","reason":"<one sentence>"}}
"""


def _ask(prompt: str, model: str) -> tuple:
    from loop_engine.core import ollama_client

    key = ollama_client.load_api_key()
    if not key:
        return None, "no provider key (OLLAMA_API_KEY)"
    result = ollama_client.chat(prompt, model=model, api_key=key, timeout=300)
    if not result.ok:
        return None, f"provider failed: {str(result.error)[:160]}"
    text = (result.text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text[4:] if text.startswith("json") else text
    try:
        return json.loads(text), ""
    except ValueError as exc:
        return None, f"not JSON: {exc}"


def choose_strategy(goal: str, model: str) -> tuple:
    payload, error = _ask(
        SELECT_PROMPT.format(goal=goal, catalogue=catalogue_text()), model)
    if error or not isinstance(payload, dict):
        return "pipeline", f"defaulted ({error or 'unreadable'})"
    name = str(payload.get("strategy") or "").strip()
    if name not in STRATEGIES:
        return "pipeline", f"defaulted (unknown strategy {name!r})"
    return name, str(payload.get("reason") or "")


def divide_once(goal: str, model: str, strategy: str) -> tuple:
    payload, error = _ask(
        DIVIDE_PROMPT.format(goal=goal, strategy=strategy_prompt(strategy)),
        model)
    if error:
        return [], error
    units = payload.get("units") if isinstance(payload, dict) else payload
    if not isinstance(units, list) or not units:
        return [], "no units returned"
    cleaned = []
    seen = set()
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            continue
        uid = str(unit.get("id") or f"u{index}").strip()
        if not uid or uid in seen or not str(unit.get("task") or "").strip():
            continue
        seen.add(uid)
        cleaned.append({
            "id": uid,
            "depends_on": [str(d) for d in (unit.get("depends_on") or [])
                           if str(d) in seen or str(d) != uid],
            "title": str(unit.get("title") or "")[:120],
            "task": str(unit["task"]).strip(),
            "verify": str(unit.get("verify") or "")[:300],
            "atomic": bool(unit.get("atomic", True)),
        })
    if not cleaned:
        return [], "no usable units"
    known = {u["id"] for u in cleaned}
    for unit in cleaned:
        unit["depends_on"] = [d for d in unit["depends_on"] if d in known]
    ok, error = _check_graph(cleaned)
    return (cleaned, "") if ok else ([], error)


def _check_graph(units: list) -> tuple:
    """A division is a dependency graph, so the engine's own checker judges it."""
    probe, start = [], 0
    for unit in units:
        probe.append({"id": unit["id"], "duration": 1, "start": start,
                      "end": start + 1,
                      "depends_on": list(unit["depends_on"])})
        start += 1
    result = verify_constraint("schedule/v1",
                               json.dumps({"tasks": probe}).encode())
    fatal = [v for v in result.violations
             if "cycle" in v or "unknown task" in v or "itself" in v]
    return (not fatal), "; ".join(fatal)


def subdivide(goal: str, model: str, depth: int, max_depth: int,
              path: str, log: list) -> list:
    """Return leaf units, dividing recursively only where it plainly helps."""
    strategy, reason = choose_strategy(goal, model)
    log.append(f"{'  ' * depth}[{path or 'root'}] strategy={strategy} "
               f"({reason[:70]})")
    if strategy == "none":
        return [{"id": path or "root", "task": goal, "depends_on": [],
                 "title": "single unit", "verify": "", "atomic": True,
                 "depth": depth}]
    units, error = divide_once(goal, model, strategy)
    if error:
        log.append(f"{'  ' * depth}  division failed ({error}); keeping whole")
        return [{"id": path or "root", "task": goal, "depends_on": [],
                 "title": "undivided", "verify": "", "atomic": True,
                 "depth": depth}]
    if len(units) == 1:
        # Stopping rule 2: a division that returns one piece divided nothing.
        log.append(f"{'  ' * depth}  returned one unit; treating as atomic")
        units[0]["atomic"] = True

    leaves = []
    for unit in units:
        child_path = f"{path}.{unit['id']}" if path else unit["id"]
        needs_more = (not unit["atomic"]) and depth + 1 <= max_depth
        if not unit["atomic"] and depth + 1 > max_depth:
            log.append(f"{'  ' * depth}  ! {child_path} still non-atomic at "
                       f"the depth ceiling -- kept whole and REPORTED")
            unit["ceiling_reached"] = True
        if needs_more:
            children = subdivide(unit["task"], model, depth + 1, max_depth,
                                 child_path, log)
            # The parent's dependencies attach to the first child; siblings
            # inside the subtree keep their own order.
            if children:
                children[0]["depends_on"] = list(
                    dict.fromkeys(children[0].get("depends_on", [])
                                  + [f"{path}.{d}" if path else d
                                     for d in unit["depends_on"]]))
            leaves.extend(children)
        else:
            leaves.append({**unit, "id": child_path, "depth": depth,
                           "depends_on": [f"{path}.{d}" if path else d
                                          for d in unit["depends_on"]]})
    return leaves


def order(units: list) -> tuple:
    by_id = {u["id"]: u for u in units}
    state, ordered = {}, []

    def visit(uid, trail):
        if state.get(uid) == "done":
            return ""
        if state.get(uid) == "open":
            return f"cycle: {' -> '.join(trail + (uid,))}"
        state[uid] = "open"
        for dep in by_id[uid].get("depends_on") or ():
            if dep in by_id:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--model", default="deepseek-v4-flash:0731")
    args = parser.parse_args()

    log: list = []
    leaves = subdivide(args.goal, args.model, 0, args.max_depth, "", log)
    print("\n".join(log))
    ordered, error = order(leaves)
    if error:
        print(f"\nREFUSED: {error}")
        return 1

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, unit in enumerate(ordered, 1):
        path = out / f"{index:02d}-{unit['id'].replace('.', '_')}.txt"
        body = [unit["task"], "",
                f"# Leaf unit {index}/{len(ordered)} at depth {unit.get('depth', 0)}",
                f"# Overall goal (context only): {args.goal}",
                "# ENVIRONMENT: the sandbox runs a bare Python interpreter with the "
                "standard library ONLY. Write tests with unittest and run them "
                "with `python3 -m unittest`. pytest is NOT installed -- a pytest "
                "test file cannot execute, so the unit will be reported as failed "
                "even when its code is correct (measured 2026-09-05). Do not "
                "import any third-party package.",
                "# ENVIRONMENT: bare Python interpreter, standard "
                "library ONLY. Use unittest and `python3 -m unittest`; "
                "pytest is NOT installed and a pytest file cannot run, "
                "so the unit is reported failed even when correct. No "
                "third-party imports.",
                "# Solve ONLY this unit. Keep it self-contained."]
        if unit.get("verify"):
            body.insert(2, f"# Verification: {unit['verify']}")
        path.write_text("\n".join(body) + "\n", encoding="utf-8")
        paths.append(str(path))
    (out / "queue.txt").write_text("\n".join(paths) + "\n", encoding="utf-8")
    (out / "tree.json").write_text(json.dumps(
        {"record_type": "recursive_decomposition/v1", "goal": args.goal,
         "max_depth": args.max_depth, "leaves": list(ordered),
         "log": log}, indent=1), encoding="utf-8")

    ceilings = [u["id"] for u in ordered if u.get("ceiling_reached")]
    print(f"\n{len(ordered)} leaf unit(s), max depth reached "
          f"{max((u.get('depth', 0) for u in ordered), default=0)}:")
    for index, unit in enumerate(ordered, 1):
        deps = ",".join(unit.get("depends_on") or ()) or "-"
        print(f"  {index:2}. d{unit.get('depth', 0)} {unit['id']:34} "
              f"deps={deps[:26]:26} {str(unit.get('title') or '')[:34]}")
    if ceilings:
        print(f"\n! {len(ceilings)} unit(s) hit the depth ceiling and were "
              f"kept whole: {ceilings}")
    print(f"\nqueue: {out / 'queue.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
