"""Injected faults, so the verification family has something to catch.

A verification design that is never shown a wrong answer cannot be compared
with any other. So this file produces wrong answers on purpose, in the shapes
a real run actually produces them: an arithmetic slip that is internally
consistent, a claim about something never seen, a missing field, and a run
that stops early and answers anyway.

Every fault is deterministic and every one is labelled, so a verifier's score
is the fraction of labelled faults it refused, and its false positive rate is
whether it refused the clean run.
"""
from __future__ import annotations

import json
import re

from port import extract_json, fixture_reply

REMAINING = re.compile(r"REMAINING_COUNT\s*=\s*(\d+)")


def _wrap(corrupt):
    def evaluate(prompt: str) -> str:
        reply = fixture_reply(prompt)
        decision = extract_json(reply)
        if not isinstance(decision, dict):
            return reply
        changed = corrupt(prompt, decision)
        return json.dumps(changed) if changed is not None else reply
    return evaluate


def _none(prompt, decision):
    return None


def _net_off_by_one(prompt, decision):
    """Wrong in the total, and left contradicting its own account breakdown.

    This was written as the hard case and turned out to be the easy one: the
    engine gate caught it immediately, because bumping the total without
    bumping any account makes the answer disagree with itself. That result is
    worth keeping, and `consistent_drift` below is the fault it was meant to
    be.
    """
    if decision.get("action") != "answer":
        return None
    decision = dict(decision)
    decision["net"] = decision.get("net", 0) + 1
    carry = dict(decision.get("carry") or {})
    if carry:
        carry["net"] = carry.get("net", 0) + 1
        decision["carry"] = carry
    return decision


def _consistent_drift(prompt, decision):
    """Wrong, and in agreement with itself at every level a gate can check.

    The total moves, the carried total moves with it, and one account that was
    already non-zero absorbs the difference, so the breakdown still sums to
    the total and the unbalanced count is unchanged. Every structural check
    passes. Only redoing the arithmetic from the world finds it, which is what
    separates the two verification arms that both score four out of four
    against weaker faults.
    """
    if decision.get("action") != "answer":
        return None
    carry = dict(decision.get("carry") or {})
    accounts = dict(carry.get("accounts") or {})
    movable = [name for name, value in accounts.items() if value not in (0, -1)]
    if not movable:
        return None
    target = max(movable, key=lambda name: abs(accounts[name]))
    accounts[target] += 1
    carry["accounts"] = accounts
    carry["net"] = carry.get("net", 0) + 1
    decision = dict(decision)
    decision["carry"] = carry
    decision["net"] = decision.get("net", 0) + 1
    decision["unbalanced"] = sum(1 for value in accounts.values() if value != 0)
    return decision


def _phantom_largest(prompt, decision):
    """Claims a shard that was never read and does not exist."""
    if decision.get("action") != "answer":
        return None
    decision = dict(decision)
    decision["largest"] = "s999999"
    return decision


def _missing_key(prompt, decision):
    if decision.get("action") != "answer":
        return None
    decision = dict(decision)
    decision.pop("unbalanced", None)
    return decision


def _stops_early(prompt, decision):
    """Answers with three shards still unread, using the carry it has."""
    match = REMAINING.search(prompt)
    if not match or int(match.group(1)) != 3:
        return None
    if decision.get("action") != "read":
        return None
    carry = decision.get("carry") or {}
    accounts = carry.get("accounts") or {}
    return {"action": "answer",
            "net": carry.get("net", 0),
            "unbalanced": sum(1 for value in accounts.values() if value != 0),
            "largest": carry.get("best_shard", ""),
            "carry": carry}


FAULTS = {
    "none": _none,
    "net_off_by_one": _net_off_by_one,
    "consistent_drift": _consistent_drift,
    "phantom_largest": _phantom_largest,
    "missing_key": _missing_key,
    "stops_early": _stops_early,
}

#: Everything except the clean control. A verifier's score is over these.
INJECTED = tuple(name for name in FAULTS if name != "none")


def evaluator(fault: str):
    if fault not in FAULTS:
        raise KeyError(f"unknown fault {fault!r}; have {sorted(FAULTS)}")
    return _wrap(FAULTS[fault])


def self_check() -> None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))
    from step_loop import solve
    from port import Port
    from world import World, grade

    for name in FAULTS:
        world = World.build(10, seed=6)
        outcome = solve(world, Port(evaluator=evaluator(name)))
        solved = grade(world, outcome["answer"])["solved"]
        if name == "none":
            assert solved, "the control must be a correct run"
        else:
            assert not solved, f"fault {name} produced a correct answer"
    print(f"faults self-check: ok ({len(INJECTED)} faults all land)")


if __name__ == "__main__":
    self_check()
