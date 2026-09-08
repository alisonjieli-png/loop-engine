"""Embodiment 2: the naive agent loop, with the whole transcript each step.

Step k receives every earlier prompt fragment and every earlier observation.
Nothing is summarised and nothing is dropped, so correctness is easy and the
cost grows with the square of the horizon. This is the shape most agent loops
start as, and the one the constant-context literature is a reaction to.

Independent by construction: its own loop, its own transcript handling.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import ContextWindowExceeded, Port, extract_json
from world import task_text


def run(world, port: Port, max_steps: int = 400) -> dict:
    """Append every observation to a growing transcript and re-send it all."""
    transcript: list = []
    unread = list(world.shard_ids)
    for step in range(max_steps):
        prompt = (
            f"{task_text(world)}\n\n"
            "The complete history of this run follows. Answer with one JSON "
            "object: either a read action or the final answer.\n"
            f"REMAINING = {unread}\n\n"
            + "\n\n".join(transcript)
        )
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc)}
        decision = extract_json(reply) or {}
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            transcript.append(world.read_shard(shard_id))
            if shard_id in unread:
                unread.remove(shard_id)
            continue
        return {"answer": decision, "stopped": "answered", "detail": ""}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps)}


ARM = {
    "name": "full_history",
    "idea": "every step re-sends the entire transcript",
    "carries": "all raw observations, forever",
    "run": run,
}
