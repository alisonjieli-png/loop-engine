"""Embodiment 8: push what fits a budget, pull the rest by name.

The pure pull arm pays a fetch round on every step, including the steps where
the node wanted exactly what a push would have sent anyway. The pure push arms
cannot express a step that needs something rare and large. This arm makes the
choice per step against a byte budget: if the state fits the budget it is
pushed and the step costs one call; if it does not, the step gets an
identifier and a key list instead, and pays a fetch.

So the budget is the whole design. Set it above the state size and this is the
bounded arm. Set it below and this is the pull arm. The interesting question a
measurement can answer is what it costs in the middle, and whether any real
task sits there.

The ledger records every served key, so what a node asked for is auditable
even though most steps never ask.

Independent by construction: its own loop, its own ledger, its own budget rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

import json

from port import ContextWindowExceeded, Port, extract_json
from world import task_text

#: Bytes of state the seed will carry inline. Above this, the step fetches.
DEFAULT_PUSH_BUDGET = 512

STATE_KEYS = ("net", "accounts", "best_shard", "best_abs")
PULLABLE = ("carried",)


class Ledger:
    """Holds context by identifier and records every key it serves."""

    def __init__(self, context_id: str):
        self.context_id = context_id
        self.entries: dict = {}
        self.pulls: list = []

    def put(self, key: str, value) -> None:
        self.entries[key] = value

    def pull(self, context_id: str, keys) -> dict:
        if context_id != self.context_id:
            return {}
        served = {}
        for key in keys:
            if key in self.entries:
                served[key] = self.entries[key]
                self.pulls.append(key)
        return served


def run(world, port: Port, max_steps: int = 4000,
        push_budget: int = DEFAULT_PUSH_BUDGET) -> dict:
    shard_ids = world.shard_ids
    ledger = Ledger("ctx-hybrid")
    state = {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1}
    observation = ""
    cursor = 0
    pushed_steps = 0
    pulled_steps = 0
    steps = 0
    while steps < max_steps:
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        rendered = json.dumps(state)
        fits = len(rendered.encode("utf-8")) <= push_budget
        ledger.put("carried", state)
        head = (
            f"{task_text(world)}\n\n"
            "Answer with one JSON object: a pull action naming keys, a read "
            "action, or the final answer with an updated `carry`.\n"
            f"CONTEXT_ID = {ledger.context_id}\n"
            f"NEXT = {next_shard}\n"
        )
        if fits:
            prompt = head + f"CARRIED = {rendered}\n\n{observation}\n"
            pushed_steps += 1
        else:
            prompt = (head + f"PULLABLE = {json.dumps(list(PULLABLE))}\n\n"
                      f"{observation}\n")
            pulled_steps += 1
        served: dict = {}
        for _ in range(3):          # bounded fetch rounds per step
            try:
                reply = port.ask(f"step{steps}", prompt)
            except ContextWindowExceeded as exc:
                return {"answer": None, "stopped": "context_window_exceeded",
                        "detail": str(exc), "pulls": ledger.pulls}
            steps += 1
            decision = extract_json(reply) or {}
            if decision.get("action") != "pull":
                break
            served = ledger.pull(decision.get("context_id",
                                              ledger.context_id),
                                 decision.get("keys") or [])
            prompt = (head + "CARRIED = "
                      + json.dumps(served.get("carried", state))
                      + f"\n\n{observation}\n")
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
                "pulls": ledger.pulls,
                "detail": f"{pushed_steps} pushed, {pulled_steps} fetched, "
                          f"{len(ledger.pulls)} keys served"}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps),
            "pulls": ledger.pulls}


ARM = {
    "name": "hybrid_push_pull",
    "idea": "push the state while it fits a budget, otherwise fetch it by name",
    "carries": "a bounded state, or an identifier and a key list",
    "run": run,
}


def self_check() -> None:
    from world import World, grade

    # above the budget threshold this is a push arm and never fetches
    world = World.build(24, seed=5)
    port = Port(backend="fixture")
    outcome = run(world, port, push_budget=4096)
    assert grade(world, outcome["answer"])["solved"], outcome
    assert outcome["pulls"] == [], "nothing should be fetched when state fits"
    push_calls = port.call_count

    # below it the same arm degrades to fetch-per-step and still solves
    tight_world = World.build(24, seed=5)
    tight = Port(backend="fixture")
    fetched = run(tight_world, tight, push_budget=1)
    assert grade(tight_world, fetched["answer"])["solved"], fetched
    assert len(fetched["pulls"]) >= 24, fetched["pulls"]
    assert tight.call_count > push_calls, (
        "fetching must cost calls, or the budget is not doing anything")
    # a fetch for an identifier the ledger does not hold serves nothing
    ledger = Ledger("ctx-a")
    ledger.put("carried", {"net": 1})
    assert ledger.pull("ctx-b", ["carried"]) == {}
    assert ledger.pull("ctx-a", ["nope"]) == {}
    print(f"hybrid_push_pull self-check: ok "
          f"({push_calls} calls pushing, {tight.call_count} fetching)")


if __name__ == "__main__":
    self_check()
