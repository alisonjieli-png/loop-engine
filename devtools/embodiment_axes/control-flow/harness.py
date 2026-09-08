"""Run the control-flow arms over the same worlds and record the trade.

Every arm carries the same state schema and faces the same window. What
changes is who picks the next unit and how many units one call carries, so
the calls column and the peak bytes column are the two ends of one trade.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from port import DEFAULT_CONTEXT_LIMIT, Port
from world import World, grade

DEFAULTS = {"horizons": [16, 64, 256], "seed": 11,
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
                outcome = body["run"](world, port,
                                      max_steps=options["max_steps"])
                error = ""
            except Exception as exc:
                outcome = {"answer": None, "stopped": "raised", "detail": ""}
                error = f"{type(exc).__name__}: {exc}"[:160]
            verdict = grade(world, outcome.get("answer"))
            rows.append({
                "family": "control-flow", "id": arm["id"], "arm": body["name"],
                "horizon": horizon, "solved": verdict["solved"],
                "why_not": verdict["reason"], "stopped": outcome["stopped"],
                "decides_next": body["decides_next"],
                "calls": port.call_count, "refused_calls": port.refusals,
                "prompt_bytes_total": port.prompt_bytes_total,
                "peak_prompt_bytes": port.peak_prompt_bytes,
                "tool_reads": len(world.reads),
                "repeat_reads": len(world.reads) - len(set(world.reads)),
                "seconds": round(time.monotonic() - started, 3),
                "error": error,
                "detail": str(outcome.get("detail", ""))[:100],
            })
    return rows


def summarise(rows) -> list:
    lines = []
    for row in rows:
        mark = "solved " if row["solved"] else "FAILED "
        lines.append(
            f"  {mark}{row['arm']:20s} h={row['horizon']:<5d} "
            f"calls={row['calls']:5d} peak={row['peak_prompt_bytes']:7,d} "
            f"refused={row['refused_calls']:2d} "
            + (f"| {row['why_not'] or row['stopped']}"
               if not row["solved"] else f"| {row['detail'][:44]}"))
    return lines
