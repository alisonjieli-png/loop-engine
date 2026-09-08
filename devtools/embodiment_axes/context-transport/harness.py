"""Run the context-transport arms over the same worlds and score them.

Each arm gets its own World built from the same seed, so no arm can see
another's reads and no arm is helped or hurt by another's tool use. The oracle
grades every answer identically and is never handed to an arm.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from port import DEFAULT_CONTEXT_LIMIT, Port
from world import World, grade, oracle, world_digest

DEFAULTS = {"horizons": [4, 16, 64, 256], "seed": 11, "backend": "fixture",
            "model": "glm-5.3-flash:cloud",
            "context_limit": DEFAULT_CONTEXT_LIMIT, "max_steps": 6000}


def run_family(arms, spec) -> list:
    options = {**DEFAULTS, **(spec or {})}
    rows = []
    for horizon in options["horizons"]:
        reference = World.build(horizon, seed=options["seed"])
        truth = oracle(reference)
        for arm in arms:
            body = arm["module"].ARM
            world = World.build(horizon, seed=options["seed"])
            port = Port(backend=options["backend"], model=options["model"],
                        context_limit=options["context_limit"])
            started = time.monotonic()
            try:
                if body["name"] == "monolith":
                    outcome = body["run"](world, port)
                else:
                    outcome = body["run"](world, port,
                                          max_steps=options["max_steps"])
                error = ""
            except Exception as exc:            # an arm that breaks is a result
                outcome = {"answer": None, "stopped": "raised", "detail": ""}
                error = f"{type(exc).__name__}: {exc}"[:160]
            verdict = grade(world, outcome.get("answer"))
            rows.append({
                "family": "context-transport", "id": arm["id"],
                "arm": body["name"], "horizon": horizon,
                "seed": options["seed"], "solved": verdict["solved"],
                "why_not": verdict["reason"], "stopped": outcome["stopped"],
                "calls": port.call_count, "refused_calls": port.refusals,
                "prompt_bytes_total": port.prompt_bytes_total,
                "peak_prompt_bytes": port.peak_prompt_bytes,
                "tool_reads": len(world.reads),
                "repeat_reads": len(world.reads) - len(set(world.reads)),
                "pulls": len(outcome.get("pulls") or []),
                "seconds": round(time.monotonic() - started, 3),
                "error": error,
                "detail": str(outcome.get("detail", ""))[:100],
                "world": world_digest(reference), "truth": truth,
            })
    return rows


def summarise(rows) -> list:
    """One line per arm per horizon, for a person reading a terminal."""
    lines = []
    for row in rows:
        mark = "solved " if row["solved"] else "FAILED "
        lines.append(
            f"  {mark}{row['arm']:20s} h={row['horizon']:<5d} "
            f"calls={row['calls']:5d} bytes={row['prompt_bytes_total']:10,d} "
            f"peak={row['peak_prompt_bytes']:7,d} "
            + (f"| {row['why_not'] or row['stopped']}"
               if not row["solved"] else ""))
    return lines
