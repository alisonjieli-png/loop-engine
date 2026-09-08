"""Decomposition 4: split by approach, not by work. Run several, publish one.

Every other arm here divides the units. This one divides the *design*: it runs
the same whole task through several different transports, verifies each result
independently, and publishes the first one that passes. Nothing is merged,
because each candidate already answers the whole question.

It is the only arm in the catalogue that survives one of its designs being
wrong for the input. The transports have different horizons, so at a size
where two of them hit their wall the third still answers and the portfolio
still returns. What it costs is running all of them.

This arm is also the catalogue's own claim under test. It builds nothing of
its own: the candidates are the context-transport embodiments and the checker
is the verification embodiment, both loaded from their folders. If the axes
really are independent and composable, this should work without either of
them knowing it exists.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from port import Port
from world import World

#: Deliberately mixed: two with a horizon they cannot pass, one without. A
#: portfolio of identical designs buys nothing but cost.
DEFAULT_CANDIDATES = (
    "context-transport/01-monolith",
    "context-transport/02-full-history",
    "context-transport/06-bounded-state",
)
VERIFIER = "verification/03-independent-recompute"


def _load(relative: str):
    name = "portfolio_" + relative.replace("/", "_").replace("-", "_")
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, ROOT / relative / "embodiment.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(world, port: Port, max_steps: int = 6000,
        candidates=DEFAULT_CANDIDATES, seed: int = 11) -> dict:
    verifier = _load(VERIFIER).ARM["verify"]
    shard_count = len(world.shard_ids)
    attempted, accepted = [], None
    verifier_reads = 0
    for relative in candidates:
        arm = _load(relative).ARM
        # Its own world, so one candidate's reads cannot help another's.
        own = World.build(shard_count, seed=seed)
        try:
            outcome = (arm["run"](own, port) if arm["name"] == "monolith"
                       else arm["run"](own, port, max_steps=max_steps))
            error = ""
        except Exception as exc:
            outcome = {"answer": None, "stopped": "raised"}
            error = f"{type(exc).__name__}: {exc}"[:100]
        result = verifier(own, outcome)
        verifier_reads += result.get("reads", 0)
        attempted.append({"candidate": arm["name"],
                          "stopped": outcome.get("stopped"),
                          "accepted": result["accepted"],
                          "reason": result["reason"][:60] or error})
        if result["accepted"] and accepted is None:
            accepted = {"candidate": arm["name"], "answer": outcome["answer"]}
            # Everything after this point would be paid for nothing. A real
            # portfolio runs them at the same time and stops the rest here.
            break
    if accepted is None:
        return {"answer": None, "stopped": "no_candidate_verified",
                "groups": 1, "candidates": len(attempted),
                "longest_group_calls": port.call_count,
                "attempted": attempted, "verifier_reads": verifier_reads,
                "detail": f"{len(attempted)} candidates, none verified"}
    return {"answer": accepted["answer"], "stopped": "answered",
            "groups": 1, "candidates": len(attempted),
            "longest_group_calls": port.call_count,
            "published": accepted["candidate"], "attempted": attempted,
            "verifier_reads": verifier_reads,
            "detail": f"published {accepted['candidate']} after "
                      f"{len(attempted)} candidate(s)"}


ARM = {"name": "portfolio", "splits_into": "several whole approaches",
       "parallelism": "one candidate per worker", "run": run}


def self_check() -> None:
    from world import grade

    # small enough that the first candidate works, so nothing else is run
    world = World.build(16, seed=11)
    cheap = run(world, Port(backend="fixture"), seed=11)
    assert grade(world, cheap["answer"])["solved"], cheap
    assert cheap["published"] == "monolith", cheap
    assert cheap["candidates"] == 1, "a verified first candidate stops the rest"

    # past two candidates' horizons, and the portfolio still answers
    big = World.build(256, seed=11)
    survived = run(big, Port(backend="fixture"), seed=11)
    assert grade(big, survived["answer"])["solved"], survived
    assert survived["published"] == "bounded_state", survived
    assert survived["candidates"] == 3, survived
    assert [entry["accepted"] for entry in survived["attempted"]] == [
        False, False, True], survived["attempted"]

    # a portfolio whose every candidate fails must refuse, not pick one
    doomed = run(World.build(256, seed=11), Port(backend="fixture"), seed=11,
                 candidates=("context-transport/01-monolith",
                             "context-transport/02-full-history"))
    assert doomed["stopped"] == "no_candidate_verified", doomed
    assert doomed["answer"] is None
    print(f"portfolio self-check: ok (1 candidate at 16 units, "
          f"{survived['candidates']} at 256 where two hit their wall)")


if __name__ == "__main__":
    self_check()
