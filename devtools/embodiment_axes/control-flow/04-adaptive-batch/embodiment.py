"""Control flow 4: grow the batch until the window pushes back, then hold.

The fixed batch needs someone to choose K, and the right K depends on the
window, the observation size and the state size, none of which the author of
the loop knows. This arm discovers it: it doubles the batch while the last
prompt used less than a target share of the window, and halves it on a refusal,
retrying the same work at the smaller size.

A refusal is therefore recoverable rather than fatal, which is the property
that separates this from every other arm in the family. It is also the only
arm here that adapts to a window it was not told about.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from step_loop import STATE_KEYS, empty_state
from world import task_text

#: Grow while the last prompt sat under this share of the window.
TARGET_SHARE = 0.5
MAX_BATCH = 4096


def run(world, port: Port, max_steps: int = 4000, batch: int = 1,
        target_share: float = TARGET_SHARE) -> dict:
    shard_ids = world.shard_ids
    state = empty_state()
    cursor = 0
    history: list = []
    refusals = 0
    for step in range(max_steps):
        if cursor >= len(shard_ids) and history:
            break
        chunk = shard_ids[cursor:cursor + batch]
        observations = "\n\n".join(world.read_shard(name) for name in chunk)
        ahead = cursor + len(chunk)
        prompt = (
            f"{task_text(world)}\n\n"
            "Fold every shard below into the running state. Reply with one "
            "JSON object carrying an updated `carry`.\n"
            f"CARRIED = {json.dumps(state)}\n"
            f"NEXT = {shard_ids[ahead] if ahead < len(shard_ids) else 'none'}\n"
            f"REMAINING_COUNT = {max(len(shard_ids) - ahead, 0)}\n\n"
            f"{observations}\n"
        )
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded:
            refusals += 1
            if batch <= 1:
                return {"answer": None, "stopped": "context_window_exceeded",
                        "detail": "one unit does not fit the window",
                        "state": state}
            batch = max(1, batch // 2)
            continue                      # the same units, at a smaller size
        cursor = ahead
        history.append(batch)
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: patch.get(key, state[key]) for key in STATE_KEYS}
        used = port.calls[-1].prompt_bytes / max(port.context_limit, 1)
        if used < target_share and batch < MAX_BATCH:
            batch = min(MAX_BATCH, batch * 2)
        if cursor >= len(shard_ids) and decision.get("action") != "read":
            return {"answer": decision, "stopped": "answered", "state": state,
                    "detail": f"batch reached {max(history)}, "
                              f"{refusals} refusals absorbed"}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps),
            "state": state}


ARM = {"name": "adaptive_batch",
       "decides_next": "a cursor with a batch size the window sets",
       "calls_per_unit": "falls as the batch grows", "run": run}


def self_check() -> None:
    from world import World, grade

    world = World.build(256, seed=9)
    port = Port(backend="fixture")
    outcome = run(world, port)
    assert grade(world, outcome["answer"])["solved"], outcome
    assert world.reads[:len(world.shard_ids)] == list(world.shard_ids)
    assert port.call_count < 40, (
        f"adaptation should collapse 256 units into far fewer calls, "
        f"got {port.call_count}")

    # a window too small for a single unit is refused, not looped forever
    tiny = World.build(8, seed=9)
    refused = run(tiny, Port(backend="fixture", context_limit=200))
    assert refused["stopped"] == "context_window_exceeded", refused

    # A narrow window still solves. Note what does not happen: at the default
    # target share the arm stops growing before it ever overshoots, so a
    # careful share buys a run with no refusals at all.
    narrow_world = World.build(64, seed=9)
    narrow = Port(backend="fixture", context_limit=2000)
    tight = run(narrow_world, narrow)
    assert grade(narrow_world, tight["answer"])["solved"], tight
    assert narrow.refusals == 0, (
        "a half-window target should not overshoot", narrow.refusals)

    # Push the target to the edge and the recovery path is exercised for real:
    # the arm overshoots, is refused, halves, and still finishes correctly.
    greedy_world = World.build(64, seed=9)
    greedy = Port(backend="fixture", context_limit=2000)
    result = run(greedy_world, greedy, target_share=0.99)
    assert grade(greedy_world, result["answer"])["solved"], result
    assert greedy.refusals >= 1, "a greedy target must hit the window"
    assert "refusals absorbed" in result["detail"], result
    print(f"adaptive_batch self-check: ok "
          f"({port.call_count} calls for 256 units; "
          f"{narrow.refusals} refusals at a half-window target, "
          f"{greedy.refusals} absorbed at a 0.99 target)")


if __name__ == "__main__":
    self_check()
