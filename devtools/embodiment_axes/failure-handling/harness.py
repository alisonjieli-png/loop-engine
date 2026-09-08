"""Show every recovery policy the same failures and record what survived.

Five failure shapes plus a clean control, identical for every arm. Four of the
five are recoverable by something; one is recoverable by nothing, and what
separates the policies there is whether they say so and what they spent
finding out.

The columns to read together are `solved` and `calls`. A policy that recovers
is worth what it costs only if the recovery was possible, and the permanent
shape is in the set precisely so the cost of a futile recovery is visible.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "shared"))

_spec = importlib.util.spec_from_file_location("fh_faults_harness",
                                               HERE / "faults.py")
faults = importlib.util.module_from_spec(_spec)
sys.modules["fh_faults_harness"] = faults
_spec.loader.exec_module(faults)

from port import DEFAULT_CONTEXT_LIMIT, Port, fixture_reply
from world import World, grade

#: Every arm that can retry is given the same total attempt budget, so what
#: varies between them is the policy and not how many tries it was handed.
#: The first arm's policy is to have no budget at all, which is why it is the
#: one arm this cannot equalise.
DEFAULTS = {"horizons": [12], "seed": 3,
            "context_limit": DEFAULT_CONTEXT_LIMIT, "max_steps": 4000,
            "broken_unit": 8, "attempt_budget": 4}


def _budgeted(run, budget: int) -> dict:
    """The budget arguments this particular arm understands."""
    import inspect
    names = set(inspect.signature(run).parameters)
    if {"plain", "escalated"} <= names:
        return {"plain": budget // 2, "escalated": budget - budget // 2}
    if "attempts" in names:
        return {"attempts": budget}
    return {}

#: Built the same way for every arm, so no arm meets an easier failure.
def _shapes(options):
    unit = options["broken_unit"]
    return {
        "none": lambda: fixture_reply,
        "transient": lambda: faults.transient(clears_after=2),
        "flaky": lambda: faults.flaky(rate=0.25, seed=options["seed"]),
        "unparseable": lambda: faults.unparseable(at_unit=unit,
                                                  clears_after=2),
        "needs_escalation": lambda: faults.needs_escalation(at_unit=unit),
        "permanent": lambda: faults.permanent(at_unit=unit),
    }


def run_family(arms, spec) -> list:
    options = {**DEFAULTS, **(spec or {})}
    rows = []
    for horizon in options["horizons"]:
        shapes = _shapes(options)
        for arm in arms:
            body = arm["module"].ARM
            survived, per_shape = [], {}
            total_calls = 0
            for name, make in shapes.items():
                world = World.build(horizon, seed=options["seed"])
                port = Port(context_limit=options["context_limit"],
                            evaluator=make())
                try:
                    outcome = body["run"](
                        world, port, max_steps=options["max_steps"],
                        **_budgeted(body["run"], options["attempt_budget"]))
                    error = ""
                except Exception as exc:
                    outcome = {"answer": None, "stopped": "raised",
                               "failures": 0, "units_lost": 0}
                    error = f"{type(exc).__name__}: {exc}"[:120]
                solved = grade(world, outcome.get("answer"))["solved"]
                total_calls += port.call_count
                if solved and name != "none":
                    survived.append(name)
                per_shape[name] = {
                    "solved": solved, "stopped": outcome["stopped"],
                    "calls": port.call_count,
                    "failures": outcome.get("failures", 0),
                    "units_lost": outcome.get("units_lost", 0),
                    "error": error,
                    "detail": str(outcome.get("detail", ""))[:80]}
            recoverable = [name for name in faults.RECOVERABLE
                           if name in shapes]
            rows.append({
                "family": "failure-handling", "id": arm["id"],
                "arm": body["name"], "horizon": horizon,
                "on_failure": body["on_failure"],
                "budget": body["budget"],
                "attempt_budget": options["attempt_budget"],
                "clean_solved": per_shape["none"]["solved"],
                "clean_calls": per_shape["none"]["calls"],
                "survived": sorted(survived),
                "survived_count": len(survived),
                "recoverable_count": len(recoverable),
                "permanent_stopped": per_shape["permanent"]["stopped"],
                "permanent_calls": per_shape["permanent"]["calls"],
                "permanent_units_lost": per_shape["permanent"]["units_lost"],
                "permanent_answered_wrongly": (
                    per_shape["permanent"]["stopped"] == "answered"
                    and not per_shape["permanent"]["solved"]),
                "total_calls": total_calls,
                "per_shape": per_shape,
            })
    return rows


def summarise(rows) -> list:
    lines = []
    for row in rows:
        lines.append(
            f"  {row['arm']:24s} survived {row['survived_count']}/"
            f"{row['recoverable_count']}  clean={row['clean_calls']:3d} calls  "
            f"permanent: {row['permanent_stopped']:20s} "
            f"{row['permanent_calls']:3d} calls"
            + ("  ANSWERED WRONGLY"
               if row["permanent_answered_wrongly"] else ""))
        missed = [name for name in ("transient", "flaky", "unparseable",
                                    "needs_escalation")
                  if name not in row["survived"]]
        if missed:
            lines.append(f"  {'':24s} lost to: {', '.join(missed)}")
    return lines
