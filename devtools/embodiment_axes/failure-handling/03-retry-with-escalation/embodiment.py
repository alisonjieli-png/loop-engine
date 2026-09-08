"""Failure 3: retry, and when retrying stops helping, change the request.

Plain retries first, because most failures clear on their own and escalation
costs more. When the budget for plain retries runs out, the request itself is
marked escalated and tried again. Something about the ask has changed, which
is the only thing that can fix a failure the request caused.

The ladder is a field, not a subclass, and it is the same shape as the
engine's own escalation ladder on its supervision policy.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state, render

DEFAULT_PLAIN = 2
DEFAULT_ESCALATED = 2

#: What escalating actually adds to the request. Kept explicit and small, so
#: the cost of the ladder is a number rather than a feeling.
ESCALATION_BLOCK = (
    "ESCALATED = true\n"
    "The previous attempts at this step did not produce a usable reply. "
    "Answer with one JSON object and nothing else.\n"
)


def run(world, port: Port, max_steps: int = 4000,
        plain: int = DEFAULT_PLAIN, escalated: int = DEFAULT_ESCALATED) -> dict:
    shard_ids = world.shard_ids
    state = empty_state()
    observation = ""
    cursor = 0
    failures = 0
    escalations = 0
    for step in range(max_steps):
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        base = render(world, state, next_shard,
                      max(len(shard_ids) - cursor, 0), observation)
        decision = None
        last = ""
        did_escalate = False
        for attempt in range(plain + escalated):
            if attempt >= plain and not did_escalate:
                did_escalate = True
                escalations += 1
            prompt = (base if attempt < plain else ESCALATION_BLOCK + base)
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
            return {"answer": None, "stopped": "ladder_exhausted",
                    "detail": f"{plain}+{escalated} attempts on unit "
                              f"{cursor}: {last}",
                    "failures": failures, "units_lost": 0,
                    "escalations": escalations}
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
                "escalations": escalations,
                "detail": f"{failures} failures, {escalations} escalations"}
    return {"answer": None, "stopped": "step_ceiling", "failures": failures,
            "units_lost": 0, "escalations": escalations,
            "detail": str(max_steps)}


ARM = {"name": "retry_with_escalation",
       "on_failure": "retry, then change the request and retry again",
       "budget": f"{DEFAULT_PLAIN} plain then {DEFAULT_ESCALATED} escalated",
       "run": run}


def self_check() -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fh_faults3", Path(__file__).resolve().parents[1] / "faults.py")
    faults = importlib.util.module_from_spec(spec)
    sys.modules["fh_faults3"] = faults
    spec.loader.exec_module(faults)
    from world import World, grade

    # the shape only escalation fixes
    world = World.build(12, seed=3)
    fixed = run(world, Port(evaluator=faults.needs_escalation(at_unit=8)))
    assert grade(world, fixed["answer"])["solved"], fixed
    assert fixed["escalations"] >= 1, fixed

    # and it still handles the ordinary one, without escalating for it
    transient_world = World.build(12, seed=3)
    healed = run(transient_world,
                 Port(evaluator=faults.transient(clears_after=1)))
    assert grade(transient_world, healed["answer"])["solved"], healed
    assert healed["escalations"] == 0, (
        "a failure that clears on a plain retry must not cost an escalation")

    # nothing fixes a permanently broken unit; the ladder must say so
    stuck = run(World.build(12, seed=3),
                Port(evaluator=faults.permanent(at_unit=8)))
    assert stuck["stopped"] == "ladder_exhausted", stuck
    print(f"retry_with_escalation self-check: ok "
          f"({fixed['escalations']} escalations to fix the request-shaped "
          f"failure, 0 for the transient one)")


if __name__ == "__main__":
    self_check()
