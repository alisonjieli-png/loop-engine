"""Run each decomposition over the same worlds and record both cost columns.

Total calls and the longest single chain point in opposite directions, and
that is the whole point of this family. Splitting adds calls and removes
serial time; the two columns have to be read together or the comparison says
whatever the reader already believed.

`longest_group_calls` is the serial depth: what the run would still cost if
every group had its own worker. It is a lower bound on wall time, not a
measurement of it, and it is labelled that way rather than dressed up as a
speedup.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from port import DEFAULT_CONTEXT_LIMIT, Port
from world import World, grade

DEFAULTS = {"horizons": [24, 256], "seed": 11,
            "context_limit": DEFAULT_CONTEXT_LIMIT, "max_steps": 6000}


def run_family(arms, spec) -> list:
    options = {**DEFAULTS, **(spec or {})}
    rows = []
    for horizon in options["horizons"]:
        for arm in arms:
            body = arm["module"].ARM
            world = World.build(horizon, seed=options["seed"])
            port = Port(context_limit=options["context_limit"])
            started = time.monotonic()
            try:
                kwargs = ({"seed": options["seed"]}
                          if body["name"] == "portfolio" else {})
                outcome = body["run"](world, port,
                                      max_steps=options["max_steps"], **kwargs)
                error = ""
            except Exception as exc:
                outcome = {"answer": None, "stopped": "raised", "groups": 0,
                           "candidates": 0, "longest_group_calls": 0}
                error = f"{type(exc).__name__}: {exc}"[:160]
            verdict = grade(world, outcome.get("answer"))
            longest = outcome.get("longest_group_calls", port.call_count)
            rows.append({
                "family": "decomposition", "id": arm["id"],
                "arm": body["name"], "horizon": horizon,
                "splits_into": body["splits_into"],
                "solved": verdict["solved"], "why_not": verdict["reason"],
                "stopped": outcome["stopped"],
                "calls": port.call_count,
                "groups": outcome.get("groups", 1),
                "candidates": outcome.get("candidates", 1),
                "longest_chain_calls": longest,
                "serial_depth_ratio": round(
                    port.call_count / max(longest, 1), 2),
                "peak_prompt_bytes": port.peak_prompt_bytes,
                "prompt_bytes_total": port.prompt_bytes_total,
                "tree_depth": outcome.get("tree_depth", 0),
                "published": outcome.get("published", ""),
                "seconds": round(time.monotonic() - started, 3),
                "error": error,
                "detail": str(outcome.get("detail", ""))[:90],
            })
    return rows


def summarise(rows) -> list:
    lines = []
    for row in rows:
        mark = "solved " if row["solved"] else "FAILED "
        lines.append(
            f"  {mark}{row['arm']:18s} h={row['horizon']:<5d} "
            f"calls={row['calls']:5d} longest_chain={row['longest_chain_calls']:5d} "
            f"({row['serial_depth_ratio']:5.2f}x if parallel)  "
            f"{row['detail'][:52]}")
    return lines
