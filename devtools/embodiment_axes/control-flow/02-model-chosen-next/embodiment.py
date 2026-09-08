"""Control flow 2: the model picks what to do next from what is left.

Instead of a cursor, the prompt carries the list of unread shards and the
reply names one. This is the shape people reach for when order matters or when
the next unit depends on what was just seen.

It buys real flexibility and it costs a list. That list has one entry per
remaining unit, so the prompt is proportional to the horizon and the arm
inherits a wall it did not have to have. The transport family measured the
same field as the dominant cost in the state arm.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state
from world import task_text


def run(world, port: Port, max_steps: int = 4000) -> dict:
    state = empty_state()
    unread = list(world.shard_ids)
    observation = ""
    for step in range(max_steps):
        prompt = (
            f"{task_text(world)}\n\n"
            "Choose which shard to read next from REMAINING, or answer. "
            "Reply with one JSON object carrying an updated `carry`.\n"
            f"CARRIED = {json.dumps(state)}\n"
            f"REMAINING = {json.dumps(unread)}\n\n"
            f"{observation}\n"
        )
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc), "state": state}
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: patch.get(key, state[key]) for key in STATE_KEYS}
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if shard_id in unread:
                unread.remove(shard_id)
            else:
                return {"answer": None, "stopped": "repeat_read",
                        "detail": f"asked again for {shard_id}", "state": state}
            continue
        return {"answer": decision, "stopped": "answered", "state": state,
                "detail": f"{len(unread)} left unread"}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps),
            "state": state}


ARM = {"name": "model_chosen_next", "decides_next": "the reply, from a list",
       "calls_per_unit": "one", "run": run}


def self_check() -> None:
    from world import World, grade
    world = World.build(12, seed=9)
    port = Port(backend="fixture")
    outcome = run(world, port)
    assert grade(world, outcome["answer"])["solved"], outcome
    # the list is the cost, and it is visible against the cursor arm
    small = Port(backend="fixture")
    run(World.build(4, seed=9), small)
    assert port.peak_prompt_bytes > small.peak_prompt_bytes, (
        "the remaining list must grow with the horizon; that is the finding")
    print(f"model_chosen_next self-check: ok "
          f"(peak {small.peak_prompt_bytes} at 4, {port.peak_prompt_bytes} at 12)")


if __name__ == "__main__":
    self_check()
