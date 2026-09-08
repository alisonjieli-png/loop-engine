"""Failure 1: the first failed step ends the run.

No retry, no escalation, no skipping. The run stops and says which unit it
stopped on. This is the strictest policy and the only one that never spends
anything on a failure it cannot fix.

It treats an unparseable reply as a failure too, which matters more than it
sounds: a step that raises is easy to see, and a step that returns confident
prose looks like success to anything checking only for exceptions.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state, render


def run(world, port: Port, max_steps: int = 4000) -> dict:
    shard_ids = world.shard_ids
    state = empty_state()
    observation = ""
    cursor = 0
    for step in range(max_steps):
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        prompt = render(world, state, next_shard,
                        max(len(shard_ids) - cursor, 0), observation)
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc), "failures": 1, "units_lost": 0}
        except Exception as exc:
            return {"answer": None, "stopped": "failed",
                    "detail": f"{type(exc).__name__}: {exc}"[:120],
                    "failures": 1, "units_lost": 0}
        decision = extract_json(reply)
        if not isinstance(decision, dict):
            return {"answer": None, "stopped": "failed",
                    "detail": "reply did not parse", "failures": 1,
                    "units_lost": 0}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: patch.get(key, state[key]) for key in STATE_KEYS}
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if cursor < len(shard_ids) and shard_id == shard_ids[cursor]:
                cursor += 1
            continue
        return {"answer": decision, "stopped": "answered", "failures": 0,
                "units_lost": 0, "detail": f"cursor {cursor}"}
    return {"answer": None, "stopped": "step_ceiling", "failures": 0,
            "units_lost": 0, "detail": str(max_steps)}


ARM = {"name": "stop_on_first", "on_failure": "stop the run",
       "budget": "none", "run": run}


def self_check() -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fh_faults", Path(__file__).resolve().parents[1] / "faults.py")
    faults = importlib.util.module_from_spec(spec)
    sys.modules["fh_faults"] = faults
    spec.loader.exec_module(faults)
    from world import World, grade

    clean = World.build(12, seed=3)
    good = run(clean, Port(backend="fixture"))
    assert grade(clean, good["answer"])["solved"], good

    broken = run(World.build(12, seed=3),
                 Port(evaluator=faults.transient(clears_after=1)))
    assert broken["stopped"] == "failed", broken
    quiet = run(World.build(12, seed=3),
                Port(evaluator=faults.unparseable(at_unit=8)))
    assert quiet["stopped"] == "failed", (
        "prose must be treated as a failure, not as a completed step")
    print("stop_on_first self-check: ok")


if __name__ == "__main__":
    self_check()
