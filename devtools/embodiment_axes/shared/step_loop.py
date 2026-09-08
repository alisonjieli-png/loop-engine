"""The one loop that families other than context-transport hold constant.

The transport family varies the loop, so each of its arms writes its own. The
placement, verification and memory families vary something else, so they need
the loop to be identical across their arms or the comparison would confound
two changes at once. This is that loop: the bounded-state transport, which the
transport family measured as the one with no horizon in reach.

Nothing here decides anything those families are testing. It renders a prompt,
asks the port, folds the reply and advances a cursor.
"""
from __future__ import annotations

import json

from port import ContextWindowExceeded, Port, extract_json
from world import task_text

STATE_KEYS = ("net", "accounts", "best_shard", "best_abs")


def empty_state() -> dict:
    return {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1}


def render(world, state: dict, next_shard: str, remaining: int,
           observation: str) -> str:
    return (
        f"{task_text(world)}\n\n"
        "You are given the running state, a cursor, and the latest "
        "observation. Answer with one JSON object carrying an updated "
        "`carry`.\n"
        f"CARRIED = {json.dumps(state)}\n"
        f"NEXT = {next_shard}\n"
        f"REMAINING_COUNT = {remaining}\n\n"
        f"{observation}\n"
    )


def solve(world, port: Port, max_steps: int = 4000, state: dict = None,
          cursor: int = 0) -> dict:
    """Read every shard in cursor order and return the final decision.

    `state` and `cursor` are one thing, not two. Resuming from a subtotal
    without the position it was a subtotal of re-reads what the subtotal
    already contains and double counts it. The memory family found exactly
    that, by measuring a resumed run rather than by reading this file, so the
    two now travel together and `folded` is the position the returned state is
    actually true at.
    """
    shard_ids = world.shard_ids
    state = dict(state) if state else empty_state()
    observation = ""
    cursor = max(0, min(int(cursor or 0), len(shard_ids)))
    folded = cursor
    for step in range(max_steps):
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        prompt = render(world, state, next_shard,
                        max(len(shard_ids) - cursor, 0), observation)
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc), "state": state, "steps": step}
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: patch.get(key, state[key]) for key in STATE_KEYS}
            # everything the cursor has passed is now inside the state
            folded = cursor
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if cursor < len(shard_ids) and shard_id == shard_ids[cursor]:
                cursor += 1
            continue
        return {"answer": decision, "stopped": "answered", "state": state,
                "cursor": folded, "steps": step + 1,
                "detail": f"cursor {cursor}"}
    # The last read has not been folded yet, so the honest position to record
    # is the one the state is true at, not the one the cursor reached.
    return {"answer": None, "stopped": "step_ceiling", "state": state,
            "cursor": folded, "steps": max_steps, "detail": str(max_steps)}


def self_check() -> None:
    from world import World, grade

    world = World.build(12, seed=4)
    outcome = solve(world, Port(backend="fixture"))
    assert grade(world, outcome["answer"])["solved"], outcome
    assert world.reads == list(world.shard_ids)
    # a ceiling below the horizon stops rather than answering wrongly
    short = World.build(12, seed=4)
    stopped = solve(short, Port(backend="fixture"), max_steps=3)
    assert stopped["stopped"] == "step_ceiling", stopped

    # and resuming from where it stopped reaches the same answer as one run
    resumed_world = World.build(12, seed=4)
    first = solve(resumed_world, Port(backend="fixture"), max_steps=5)
    assert first["stopped"] == "step_ceiling", first
    second = solve(World.build(12, seed=4), Port(backend="fixture"),
                   state=first["state"], cursor=first["cursor"])
    assert grade(World.build(12, seed=4), second["answer"])["solved"], second
    assert second["steps"] < outcome["steps"], (
        "a resumed run must do less work than a cold one")

    # resuming with the subtotal but not the position double counts, which is
    # the defect this signature exists to make impossible to write by accident
    wrong = solve(World.build(12, seed=4), Port(backend="fixture"),
                  state=first["state"], cursor=0)
    assert not grade(World.build(12, seed=4), wrong["answer"])["solved"], (
        "state without its position must not silently produce a right answer")
    print(f"step_loop self-check: ok "
          f"(cold {outcome['steps']} steps, resumed {second['steps']})")


if __name__ == "__main__":
    self_check()
