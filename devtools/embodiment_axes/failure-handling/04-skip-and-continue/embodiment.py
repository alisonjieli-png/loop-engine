"""Failure 4: record the failure, skip the unit, keep going.

The only policy here that finishes a run containing a failure it could not
fix. It is also the only one that can return an answer that is quietly wrong,
because the answer is computed over the units that worked and says nothing
about the ones that did not unless someone reads the detail.

That is not a reason to reject it. Partial results are the right answer for
plenty of work. It is a reason to pair it with verification: this arm and the
independent recompute verifier together give you a finished run and an honest
refusal, where either alone gives you one or the other.

So the units it lost are returned as a field, not buried in a log.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state, render

DEFAULT_ATTEMPTS = 2


def run(world, port: Port, max_steps: int = 4000,
        attempts: int = DEFAULT_ATTEMPTS) -> dict:
    shard_ids = world.shard_ids
    state = empty_state()
    observation = ""
    cursor = 0
    failures = 0
    lost: list = []
    for step in range(max_steps):
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        prompt = render(world, state, next_shard,
                        max(len(shard_ids) - cursor, 0), observation)
        decision = None
        for attempt in range(attempts):
            try:
                reply = port.ask(f"step{step}.{attempt}", prompt)
            except ContextWindowExceeded as exc:
                return {"answer": None, "stopped": "context_window_exceeded",
                        "detail": str(exc), "failures": failures,
                        "units_lost": len(lost), "lost": lost}
            except Exception:
                failures += 1
                continue
            parsed = extract_json(reply)
            if isinstance(parsed, dict):
                decision = parsed
                break
            failures += 1
        if decision is None:
            # Give up on this unit and move past it. The observation is
            # dropped, so its contribution never reaches the state.
            if cursor < len(shard_ids):
                lost.append(shard_ids[cursor])
                cursor += 1
                observation = ""
                continue
            return {"answer": None, "stopped": "failed_at_answer",
                    "detail": f"{len(lost)} units skipped",
                    "failures": failures, "units_lost": len(lost),
                    "lost": lost}
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
                "failures": failures, "units_lost": len(lost), "lost": lost,
                "detail": (f"{failures} failures, {len(lost)} units skipped: "
                           f"{lost[:5]}") if lost else f"{failures} failures"}
    return {"answer": None, "stopped": "step_ceiling", "failures": failures,
            "units_lost": len(lost), "lost": lost, "detail": str(max_steps)}


ARM = {"name": "skip_and_continue",
       "on_failure": "record it, skip the unit, finish the run",
       "budget": f"{DEFAULT_ATTEMPTS} attempts per unit", "run": run}


def self_check() -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fh_faults4", Path(__file__).resolve().parents[1] / "faults.py")
    faults = importlib.util.module_from_spec(spec)
    sys.modules["fh_faults4"] = faults
    spec.loader.exec_module(faults)
    from world import World, grade

    clean = World.build(12, seed=3)
    good = run(clean, Port(backend="fixture"))
    assert grade(clean, good["answer"])["solved"] and good["units_lost"] == 0

    # it finishes where every other policy stops, and the answer is wrong
    world = World.build(12, seed=3)
    partial = run(world, Port(evaluator=faults.permanent(at_unit=8)))
    assert partial["stopped"] == "answered", partial
    assert partial["units_lost"] >= 1, partial
    assert not grade(world, partial["answer"])["solved"], (
        "a run missing a unit must not be graded as correct")
    # and it says which ones, in a field rather than a log
    assert partial["lost"] and all(name in world.shard_ids
                                   for name in partial["lost"])
    print(f"skip_and_continue self-check: ok "
          f"(finished with {partial['units_lost']} unit(s) lost: "
          f"{partial['lost']})")


if __name__ == "__main__":
    self_check()
