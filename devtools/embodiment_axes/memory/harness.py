"""Score each memory design on savings, on resume, and on being lied to.

Four scenarios, identical for every arm:

cold    a first run over a fresh world; the baseline call count.
warm    a second run over the same world after the first committed; the
        saving is whatever the arm can serve without calls.
resume  a run stopped by a ceiling below the horizon, then a second run; the
        question is whether the second one continues or starts over.
poison  an outsider stages a wrong answer before the second run; the questions
        are whether the arm serves it and whether the run then answers wrongly.

The poison scenario is the reason this family exists. Savings and blast radius
move together, and only a measurement shows by how much.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from port import DEFAULT_CONTEXT_LIMIT, Port
from step_loop import solve
from world import World, grade, oracle

DEFAULTS = {"horizons": [16], "seed": 11,
            "context_limit": DEFAULT_CONTEXT_LIMIT, "max_steps": 4000,
            "resume_ceiling": 6}

POISON = {"net": -999999, "unbalanced": 0, "largest": "s000"}


def _reviewer(world, answer):
    """The independent gate the governed arm is given. Others ignore it."""
    truth = oracle(world)
    wrong = [key for key in truth if answer.get(key) != truth[key]]
    return (not wrong), ("" if not wrong else f"disagrees on {wrong}")


def _make(arm, options):
    Store = arm["module"].ARM["Store"]
    try:
        return Store(reviewer=_reviewer)
    except TypeError:
        return Store()


def _run(world, store, options, max_steps=None):
    """Recall first, then solve, then commit. Identical for every arm."""
    recalled = store.recall(world)
    if recalled is not None:
        return {"answer": recalled, "stopped": "recalled", "calls": 0,
                "state": {}, "recalled": True}
    saved = store.checkpoint(world) or {}
    port = Port(context_limit=options["context_limit"])
    outcome = solve(world, port,
                    max_steps=max_steps or options["max_steps"],
                    state=saved.get("state"), cursor=saved.get("cursor", 0))
    store.commit(world, outcome, accepted=False)
    return {**outcome, "calls": port.call_count, "recalled": False}


def run_family(arms, spec) -> list:
    options = {**DEFAULTS, **(spec or {})}
    rows = []
    for horizon in options["horizons"]:
        for arm in arms:
            body = arm["module"].ARM

            store = _make(arm, options)
            cold = _run(World.build(horizon, seed=options["seed"]), store,
                        options)
            warm = _run(World.build(horizon, seed=options["seed"]), store,
                        options)

            resume_store = _make(arm, options)
            first = _run(World.build(horizon, seed=options["seed"]),
                         resume_store, options,
                         max_steps=options["resume_ceiling"])
            second_world = World.build(horizon, seed=options["seed"])
            second = _run(second_world, resume_store, options)
            resumed = (second["calls"] < cold["calls"]
                       and not second.get("recalled"))
            resume_correct = grade(second_world,
                                   second.get("answer"))["solved"]

            poison_store = _make(arm, options)
            _run(World.build(horizon, seed=options["seed"]), poison_store,
                 options)
            poison_world = World.build(horizon, seed=options["seed"])
            offered = poison_store.offer(poison_world, dict(POISON),
                                         by="outsider")
            after = _run(poison_world, poison_store, options)
            served = after.get("answer") == POISON
            wrong = not grade(poison_world, after.get("answer"))["solved"]

            rows.append({
                "family": "memory", "id": arm["id"], "arm": body["name"],
                "horizon": horizon, "keeps": body["keeps"],
                "cold_calls": cold["calls"], "warm_calls": warm["calls"],
                "warm_recalled": bool(warm.get("recalled")),
                "cold_solved": grade(World.build(horizon,
                                                 seed=options["seed"]),
                                     cold.get("answer"))["solved"],
                "resume_first_stopped": first["stopped"],
                "resume_second_calls": second["calls"],
                "resumed": bool(resumed),
                "resume_correct": bool(resume_correct),
                "poison_response": str(offered)[:60],
                "poison_served": bool(served),
                "poison_answer_wrong": bool(wrong),
            })
    return rows


def summarise(rows) -> list:
    lines = []
    for row in rows:
        lines.append(
            f"  {row['arm']:22s} cold={row['cold_calls']:4d} "
            f"warm={row['warm_calls']:4d} "
            f"resume={'yes' if row['resumed'] else 'no ':3s} "
            f"resume_ok={'yes' if row['resume_correct'] else 'NO ':3s} "
            f"poison_served={'YES' if row['poison_served'] else 'no ':3s} "
            f"answer_wrong={'YES' if row['poison_answer_wrong'] else 'no'}")
    return lines
