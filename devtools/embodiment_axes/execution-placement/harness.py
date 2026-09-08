"""Time the same loop in each placement, and record what each one contains.

The loop, the transport and the reader are identical across arms. Only the
boundary the step body runs behind changes, so the seconds column is the price
of the boundary and nothing else.

An unavailable placement is recorded as a skip with its reason. It is never
quietly replaced by a weaker one, because a placement that downgrades in
silence is worse than one that refuses.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from port import DEFAULT_CONTEXT_LIMIT, Port
from step_loop import solve
from world import World, grade

#: Small on purpose. A container start is hundreds of milliseconds, so a large
#: horizon here measures patience rather than placement.
DEFAULTS = {"horizons": [12], "seed": 11,
            "context_limit": DEFAULT_CONTEXT_LIMIT, "max_steps": 4000}


def run_family(arms, spec) -> list:
    options = {**DEFAULTS, **(spec or {})}
    rows = []
    for horizon in options["horizons"]:
        for arm in arms:
            body = arm["module"].ARM
            ok, detail = body["available"]()
            base = {"family": "execution-placement", "id": arm["id"],
                    "arm": body["name"], "horizon": horizon,
                    "placement": body["placement"],
                    "isolation": body["isolation"], "available": ok,
                    "availability_detail": detail}
            if not ok:
                rows.append({**base, "solved": None, "calls": 0,
                             "seconds": 0.0, "seconds_per_call": 0.0,
                             "stopped": "skipped", "error": ""})
                continue
            world = World.build(horizon, seed=options["seed"])
            port = Port(context_limit=options["context_limit"],
                        evaluator=body["make_evaluator"]())
            started = time.monotonic()
            try:
                outcome = solve(world, port, max_steps=options["max_steps"])
                error = ""
            except Exception as exc:
                outcome = {"answer": None, "stopped": "raised"}
                error = f"{type(exc).__name__}: {exc}"[:160]
            elapsed = time.monotonic() - started
            rows.append({**base,
                         "solved": grade(world, outcome.get("answer"))["solved"],
                         "stopped": outcome["stopped"],
                         "calls": port.call_count,
                         "seconds": round(elapsed, 3),
                         "seconds_per_call": round(
                             elapsed / max(port.call_count, 1), 4),
                         "error": error})
    return rows


def summarise(rows) -> list:
    lines = []
    for row in rows:
        if not row["available"]:
            lines.append(f"  skipped {row['arm']:22s} "
                         f"{row['availability_detail']}")
            continue
        mark = "solved " if row["solved"] else "FAILED "
        lines.append(f"  {mark}{row['arm']:22s} calls={row['calls']:4d} "
                     f"{row['seconds']:7.3f}s  "
                     f"{row['seconds_per_call'] * 1000:8.2f} ms/call  "
                     f"{row['isolation'][:44]}")
    return lines
