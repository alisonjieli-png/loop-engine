"""Embodiment 4: the same fields, labelled by horizon.

Carries exactly what embodiment 3 carries and adds nothing. The only change is
presentation: the state is split into three labelled blocks so a reader can
tell what is constitutional, what the run has accumulated, and what is true
only at this instant.

That makes this arm the honest control for a claim worth testing separately:
labelling changes bytes a little and may change how well a real model uses
them. Against a perfect player it should be indistinguishable from
embodiment 3 in correctness, and the byte difference is the cost of the
labels. Any other result would mean one of the two arms is not carrying what
it claims.

Independent by construction: its own loop and its own rendering.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

import json

from port import ContextWindowExceeded, Port, extract_json
from world import task_text

STATE_KEYS = ("net", "accounts", "best_shard", "best_abs", "shards_folded")


def _render(task: str, state: dict, unread: list, observation: str) -> str:
    """Three labelled blocks over one state, not three states."""
    long_horizon = f"## LONG: why this run exists\n{task}"
    medium = ("## MEDIUM: what the run has accumulated\n"
              f"CARRIED = {json.dumps(state)}\n"
              f"folded {len(state.get('shards_folded') or [])} shards so far")
    short = ("## SHORT: this step's working set\n"
             f"REMAINING = {unread}\n\n{observation}")
    return "\n\n".join((long_horizon, medium, short,
                        "Answer with one JSON object carrying an updated "
                        "`carry`."))


def run(world, port: Port, max_steps: int = 400) -> dict:
    state = {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1,
             "shards_folded": []}
    observation = ""
    unread = list(world.shard_ids)
    for step in range(max_steps):
        prompt = _render(task_text(world), state, unread, observation)
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc)}
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            state = {key: value for key, value in patch.items()
                     if key in STATE_KEYS}
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            observation = world.read_shard(shard_id)
            if shard_id in unread:
                unread.remove(shard_id)
            continue
        return {"answer": decision, "stopped": "answered", "detail": ""}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps)}


ARM = {
    "name": "horizon_state",
    "idea": "the same state, labelled long, medium and short",
    "carries": "one accumulator, presented in three blocks",
    "run": run,
}
