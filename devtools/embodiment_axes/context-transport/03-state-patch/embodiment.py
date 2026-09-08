"""Embodiment 3: procedure, closed state, latest observation, and nothing else.

Step k receives the fixed procedure, one closed-schema state record, and only
the observation that just arrived. The state is the accumulator, so it is the
same size whether the horizon is five shards or five hundred. History is not
sent because the state is a sufficient statistic for this task.

The arm accepts a state patch from the reply and refuses fields outside the
schema, so a reply cannot widen what travels forward.

Independent by construction: its own loop, its own state and patch handling.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

import json

from port import ContextWindowExceeded, Port, extract_json
from world import task_text

#: The closed schema. A key outside this set is refused, never merged.
STATE_KEYS = ("net", "accounts", "best_shard", "best_abs", "shards_folded")


def _admit(patch) -> dict:
    """Keep the fields the schema names and report the ones it refuses."""
    if not isinstance(patch, dict):
        return {}, ["patch was not an object"]
    kept = {key: value for key, value in patch.items() if key in STATE_KEYS}
    refused = sorted(set(patch) - set(STATE_KEYS))
    return kept, refused


def run(world, port: Port, max_steps: int = 400) -> dict:
    state = {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1,
             "shards_folded": []}
    observation = ""
    unread = list(world.shard_ids)
    refused_fields: list = []
    for step in range(max_steps):
        prompt = (
            f"{task_text(world)}\n\n"
            "You are given the running state and the latest observation only. "
            "Answer with one JSON object carrying an updated `carry`.\n"
            f"CARRIED = {json.dumps(state)}\n"
            f"REMAINING = {unread}\n\n"
            f"{observation}\n"
        )
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc)}
        decision = extract_json(reply) or {}
        kept, refused = _admit(decision.get("carry"))
        refused_fields.extend(refused)
        if kept:
            state = kept
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if shard_id in unread:
                unread.remove(shard_id)
            continue
        return {"answer": decision, "stopped": "answered",
                "detail": f"refused fields: {sorted(set(refused_fields))}"
                if refused_fields else ""}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps)}


ARM = {
    "name": "state_patch",
    "idea": "procedure plus a closed state record plus the latest observation",
    "carries": "one accumulator, the same size at any horizon",
    "run": run,
}
