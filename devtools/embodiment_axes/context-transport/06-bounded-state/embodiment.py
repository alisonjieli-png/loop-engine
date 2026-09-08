"""Embodiment 6: the state arm with a schema that is actually bounded.

Embodiment 3 was written to carry a constant amount per step, and the
measurement said otherwise: at 1,024 shards its prompt had grown to about ten
kilobytes. Two fields were the cause. It sent the whole remaining list, which
is one entry per unread shard, and it sent every folded shard id, which is one
entry per read shard. Together they are the horizon written out twice.

Neither is needed. Reading in order means a cursor says everything the list
said, and a count says everything the folded list said. This arm carries the
same information with five scalars and one small mapping, so its prompt is the
same size at four shards and at four thousand.

This is the arm to copy if you want a constant-context step. Embodiment 3 is
the arm that shows how easily a schema stops being constant without anyone
noticing.

Independent by construction: its own loop, its own schema, its own rendering.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

import json

from port import ContextWindowExceeded, Port, extract_json
from world import task_text

#: Five scalars and one mapping over a fixed account vocabulary. Nothing in
#: this schema is proportional to the number of shards.
STATE_KEYS = ("net", "accounts", "best_shard", "best_abs", "folded_count")


def run(world, port: Port, max_steps: int = 4000) -> dict:
    shard_ids = world.shard_ids
    state = {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1,
             "folded_count": 0}
    observation = ""
    cursor = 0
    for step in range(max_steps):
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        prompt = (
            f"{task_text(world)}\n\n"
            "You are given the running state, a cursor, and the latest "
            "observation. Answer with one JSON object carrying an updated "
            "`carry`.\n"
            f"CARRIED = {json.dumps(state)}\n"
            f"NEXT = {next_shard}\n"
            f"REMAINING_COUNT = {max(len(shard_ids) - cursor, 0)}\n\n"
            f"{observation}\n"
        )
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc)}
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            # The player returns the folded list because the shared schema has
            # one; this arm keeps only its count, which is all it needs to
            # know that a shard was already folded once reading is in order.
            folded = patch.get("shards_folded")
            state = {key: value for key, value in patch.items()
                     if key in STATE_KEYS}
            state["folded_count"] = (len(folded) if isinstance(folded, list)
                                     else patch.get("folded_count", 0))
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if cursor < len(shard_ids) and shard_id == shard_ids[cursor]:
                cursor += 1
            continue
        return {"answer": decision, "stopped": "answered",
                "detail": f"cursor {cursor} of {len(shard_ids)}"}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps)}


ARM = {
    "name": "bounded_state",
    "idea": "a state schema with nothing proportional to the horizon",
    "carries": "five scalars, a fixed account mapping, and a cursor",
    "run": run,
}
