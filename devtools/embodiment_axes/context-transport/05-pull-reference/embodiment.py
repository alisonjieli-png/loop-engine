"""Embodiment 5: a small seed and an identifier, with everything else pulled.

Step k is launched with almost nothing: who it is, what it must produce, and a
context identifier plus the list of keys it may ask for. If it needs the
accumulator it asks, the store serves that key, and the step is asked again
with what it requested. Every pull is logged, so the question this arm exists
to answer has an answer in the record: what did the step ask for that the push
would have had to guess.

The cost shape is the opposite of the transcript arm. Per-step bytes are the
smallest of any arm, and each pull is another round trip. Whether that trade
is worth making is exactly what the numbers should decide.

The store serves only keys the engine named, never a query the step composed,
so a step cannot widen its own grant by asking differently.

Independent by construction: its own loop, its own store, its own pull log.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

import json

from port import ContextWindowExceeded, Port, extract_json
from world import task_text

STATE_KEYS = ("net", "accounts", "best_shard", "best_abs", "shards_folded")

#: The closed pull vocabulary. A step names a key; it never writes a query.
PULLABLE = ("carried", "remaining", "task")


class ContextStore:
    """What a step may fetch by identifier, and a log of what it fetched."""

    def __init__(self, context_id: str):
        self.context_id = context_id
        self.values: dict = {}
        self.pulls: list = []

    def put(self, key: str, value) -> None:
        if key not in PULLABLE:
            raise KeyError(f"{key} is not in the closed pull vocabulary")
        self.values[key] = value

    def pull(self, context_id: str, keys) -> dict:
        """Serve named keys for one identifier. An unknown key is refused."""
        if context_id != self.context_id:
            raise PermissionError("an identifier is not authority for another")
        served = {}
        for key in keys:
            if key not in PULLABLE:
                self.pulls.append({"key": key, "served": False})
                continue
            served[key] = self.values.get(key)
            self.pulls.append({"key": key, "served": True})
        return served


def run(world, port: Port, max_steps: int = 400) -> dict:
    context_id = "ctx-" + world.shard_ids[0] if world.shard_ids else "ctx-empty"
    store = ContextStore(context_id)
    state = {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1,
             "shards_folded": []}
    observation = ""
    unread = list(world.shard_ids)
    steps = 0
    while steps < max_steps:
        store.put("carried", state)
        store.put("remaining", unread)
        store.put("task", task_text(world))
        # The seed: identity, the contract, the keys available, and the one
        # observation that just arrived. No accumulator unless it is asked for.
        seed = (
            "You are one step of a ledger reconciliation run.\n"
            f"CONTEXT_ID = {context_id}\n"
            f"PULLABLE = {json.dumps(list(PULLABLE))}\n"
            "Answer with one JSON object: a pull action naming keys, a read "
            "action, or the final answer with an updated `carry`.\n\n"
            f"{observation}\n"
        )
        served: dict = {}
        for _ in range(3):  # bounded pull rounds per step
            prompt = seed + (
                "" if not served else
                f"\nCARRIED = {json.dumps(served.get('carried'))}\n"
                f"REMAINING = {json.dumps(served.get('remaining'))}\n"
                f"{served.get('task', '')}\n")
            try:
                reply = port.ask(f"step{steps}", prompt)
            except ContextWindowExceeded as exc:
                return {"answer": None, "stopped": "context_window_exceeded",
                        "detail": str(exc), "pulls": store.pulls}
            steps += 1
            decision = extract_json(reply) or {}
            if decision.get("action") == "pull":
                served = store.pull(context_id, decision.get("keys") or [])
                continue
            break
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
        return {"answer": decision, "stopped": "answered",
                "detail": f"{len(store.pulls)} pulls", "pulls": store.pulls}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps),
            "pulls": store.pulls}


ARM = {
    "name": "pull_reference",
    "idea": "a seed with an identifier; everything else is fetched by name",
    "carries": "an identifier, and whatever the step asked for",
    "run": run,
}
