"""Embodiment 1: one call, everything inlined.

No decomposition, no state, no transport question. The whole world is pasted
into a single prompt and the answer is expected in the reply. This is the
control every other arm is measured against, and it is the arm whose wall is
easiest to predict: it fails the moment the world stops fitting in the window.

Independent by construction: this file holds its own loop and shares nothing
with the other arms but the world, the port, and the measurement record.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from world import task_text


def run(world, port: Port) -> dict:
    """Read everything, ask once, return whatever came back."""
    prompt = (
        f"{task_text(world)}\n\n"
        "Every shard is below. Answer with one JSON object.\n"
        "REMAINING = []\n\n"
        f"{world.all_shards_rendered()}\n"
    )
    try:
        reply = port.ask("only", prompt)
    except ContextWindowExceeded as exc:
        return {"answer": None, "stopped": "context_window_exceeded",
                "detail": str(exc)}
    return {"answer": extract_json(reply), "stopped": "answered", "detail": ""}


ARM = {
    "name": "monolith",
    "idea": "one call with the whole world inlined",
    "carries": "nothing between steps, because there are no steps",
    "run": run,
}
