"""Failure 2: retry the same request, up to a budget.

The simplest recovery there is, and the one that handles the most common real
failure: something that goes away on its own. A rate limit, a dropped
connection, a decode that happened to come out wrong.

It cannot fix a failure whose cause is the request itself. Against that shape
it spends its entire budget discovering that nothing changed, which is the
cost this arm exists to make visible.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state, render

DEFAULT_ATTEMPTS = 4


def run(world, port: Port, max_steps: int = 4000,
        attempts: int = DEFAULT_ATTEMPTS) -> dict:
    shard_ids = world.shard_ids
    state = empty_state()
    observation = ""
    cursor = 0
    failures = 0
    for step in range(max_steps):
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        prompt = render(world, state, next_shard,
                        max(len(shard_ids) - cursor, 0), observation)
        decision = None
        last = ""
        for attempt in range(attempts):
            try:
                reply = port.ask(f"step{step}.{attempt}", prompt)
            except ContextWindowExceeded as exc:
                return {"answer": None, "stopped": "context_window_exceeded",
                        "detail": str(exc), "failures": failures,
                        "units_lost": 0}
            except Exception as exc:
                failures += 1
                last = f"{type(exc).__name__}: {exc}"[:100]
                continue
            parsed = extract_json(reply)
            if isinstance(parsed, dict):
                decision = parsed
                break
            failures += 1
            last = "reply did not parse"
        if decision is None:
            return {"answer": None, "stopped": "attempts_exhausted",
                    "detail": f"{attempts} attempts on unit {cursor}: {last}",
                    "failures": failures, "units_lost": 0}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: patch.get(key, state[key]) for key in STATE_KEYS}
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if cursor < len(shard_ids) and shard_id == shard_ids[cursor]:
                cursor += 1
            continue
        return {"answer": decision, "stopped": "answered",
                "failures": failures, "units_lost": 0,
                "detail": f"{failures} failures absorbed"}
    return {"answer": None, "stopped": "step_ceiling", "failures": failures,
            "units_lost": 0, "detail": str(max_steps)}


ARM = {"name": "retry_same", "on_failure": "send the same request again",
       "budget": f"{DEFAULT_ATTEMPTS} attempts per unit", "run": run}


def self_check() -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fh_faults2", Path(__file__).resolve().parents[1] / "faults.py")
    faults = importlib.util.module_from_spec(spec)
    sys.modules["fh_faults2"] = faults
    spec.loader.exec_module(faults)
    from world import World, grade

    world = World.build(12, seed=3)
    healed = run(world, Port(evaluator=faults.transient(clears_after=2)))
    assert grade(world, healed["answer"])["solved"], healed
    assert healed["failures"] > 0, "it must actually have failed and recovered"

    # the shape retrying cannot fix: the request itself is the problem
    stuck = run(World.build(12, seed=3),
                Port(evaluator=faults.needs_escalation(at_unit=8)))
    assert stuck["stopped"] == "attempts_exhausted", stuck
    print(f"retry_same self-check: ok "
          f"({healed['failures']} transient failures absorbed)")


if __name__ == "__main__":
    self_check()
