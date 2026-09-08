"""Control flow 3: fold a fixed number of units per call.

The loop reads K shards and puts all K in one prompt. Calls fall by a factor
of K and the prompt grows by K observations, so this is the direct trade
between call count and prompt size with one knob on it.

There is no cleverness here on purpose. The next arm adds the cleverness, and
this one exists so the cleverness has something to be measured against.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state
from world import task_text

DEFAULT_BATCH = 8


def run(world, port: Port, max_steps: int = 4000,
        batch: int = DEFAULT_BATCH) -> dict:
    shard_ids = world.shard_ids
    state = empty_state()
    cursor = 0
    for step in range(max_steps):
        chunk = shard_ids[cursor:cursor + batch]
        observations = "\n\n".join(world.read_shard(name) for name in chunk)
        cursor += len(chunk)
        prompt = (
            f"{task_text(world)}\n\n"
            "Fold every shard below into the running state. Reply with one "
            "JSON object carrying an updated `carry`.\n"
            f"CARRIED = {json.dumps(state)}\n"
            f"NEXT = {shard_ids[cursor] if cursor < len(shard_ids) else 'none'}\n"
            f"REMAINING_COUNT = {max(len(shard_ids) - cursor, 0)}\n\n"
            f"{observations}\n"
        )
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": f"batch {batch}: {exc}", "state": state}
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: patch.get(key, state[key]) for key in STATE_KEYS}
        if cursor >= len(shard_ids) and decision.get("action") != "read":
            return {"answer": decision, "stopped": "answered", "state": state,
                    "detail": f"batch {batch}"}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps),
            "state": state}


ARM = {"name": "fixed_batch", "decides_next": "a code-held cursor, K at a time",
       "calls_per_unit": "one over K", "run": run}


def self_check() -> None:
    from world import World, grade
    for batch in (1, 4, 16):
        world = World.build(32, seed=9)
        port = Port(backend="fixture")
        outcome = run(world, port, batch=batch)
        assert grade(world, outcome["answer"])["solved"], (batch, outcome)
        assert world.reads == list(world.shard_ids), batch
    # calls fall as the batch grows, and bytes per prompt rise
    ports = {}
    for batch in (1, 16):
        port = Port(backend="fixture")
        run(World.build(32, seed=9), port, batch=batch)
        ports[batch] = port
    assert ports[16].call_count < ports[1].call_count
    assert ports[16].peak_prompt_bytes > ports[1].peak_prompt_bytes
    print(f"fixed_batch self-check: ok "
          f"({ports[1].call_count} calls at K=1, {ports[16].call_count} at K=16)")


if __name__ == "__main__":
    self_check()
