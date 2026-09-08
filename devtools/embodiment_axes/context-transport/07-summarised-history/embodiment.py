"""Embodiment 7: keep the transcript, compact the oldest part on a threshold.

The transcript arm has a wall because history only grows. This arm keeps the
transcript idea and adds one rule: when the raw tail crosses a byte threshold,
the oldest entries are folded into the carried summary and their raw text is
dropped. Recent observations stay verbatim.

There is a second, less obvious rule here, and it is the one worth stealing.
The de-duplication list only has to name what is currently in the prompt. A
shard that has been folded into the summary and dropped from the tail cannot
be folded twice, because it is not there to fold. So the list is bounded by
the tail, not by the horizon, and the arm keeps a flat prompt without giving
up raw recent detail.

The fold here is arithmetic, so it loses nothing. A model-written summary is
not arithmetic, and the difference is where this design gets dangerous.

Independent by construction: its own loop, its own tail and its own compaction.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

import json

from port import ContextWindowExceeded, Port, extract_json
from world import task_text

#: Raw tail budget in bytes. The only knob. Peak prompt tracks it directly.
DEFAULT_TAIL_BYTES = 600

SUMMARY_KEYS = ("net", "accounts", "best_shard", "best_abs")


def _tail_bytes(tail) -> int:
    return sum(len(text.encode("utf-8")) + 2 for _, text in tail)


def _compact(tail, tail_bytes: int, folded):
    """Drop oldest raw entries until the tail fits, and never drop unfolded.

    The first version of this dropped by age alone. At a tail budget smaller
    than one observation it discarded the observation that had just arrived,
    before anything had folded it, and the run answered confidently with a
    missing shard. Dropping is only safe for an entry whose value is already
    in the summary, so that is now the condition, and the budget is advisory
    against it: a tail always keeps at least the entries nothing has read yet.
    """
    dropped = 0
    while tail and _tail_bytes(tail) > tail_bytes and tail[0][0] in folded:
        tail.pop(0)
        dropped += 1
    return dropped


def run(world, port: Port, max_steps: int = 4000,
        tail_bytes: int = DEFAULT_TAIL_BYTES) -> dict:
    shard_ids = world.shard_ids
    summary = {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1}
    tail: list = []              # [(shard_id, rendered_text)]
    in_prompt: list = []         # ids present in the tail and already folded
    cursor = 0
    compactions = 0
    for step in range(max_steps):
        next_shard = shard_ids[cursor] if cursor < len(shard_ids) else "none"
        carried = dict(summary)
        # The list names only what this prompt actually contains. That is what
        # keeps it bounded, and it is enough to stop a double count.
        carried["shards_folded"] = list(in_prompt)
        prompt = (
            f"{task_text(world)}\n\n"
            "A summary of everything folded so far, then the most recent "
            "observations in full. Answer with one JSON object carrying an "
            "updated `carry`.\n"
            f"CARRIED = {json.dumps(carried)}\n"
            f"NEXT = {next_shard}\n\n"
            + "\n\n".join(text for _, text in tail) + "\n"
        )
        try:
            reply = port.ask(f"step{step}", prompt)
        except ContextWindowExceeded as exc:
            return {"answer": None, "stopped": "context_window_exceeded",
                    "detail": str(exc)}
        decision = extract_json(reply) or {}
        patch = decision.get("carry")
        if isinstance(patch, dict):
            summary = {key: patch.get(key, summary[key])
                       for key in SUMMARY_KEYS}
            # everything sitting in the tail has now been folded into summary
            in_prompt = [shard_id for shard_id, _ in tail]
        if decision.get("action") == "read":
            shard_id = decision.get("shard")
            tail.append((shard_id, world.read_shard(shard_id)))
            if cursor < len(shard_ids) and shard_id == shard_ids[cursor]:
                cursor += 1
            dropped = _compact(tail, tail_bytes, set(in_prompt))
            if dropped:
                compactions += 1
                keep = {shard_id for shard_id, _ in tail}
                in_prompt = [name for name in in_prompt if name in keep]
            continue
        return {"answer": decision, "stopped": "answered",
                "detail": f"{compactions} compactions, tail {len(tail)}"}
    return {"answer": None, "stopped": "step_ceiling", "detail": str(max_steps)}


ARM = {
    "name": "summarised_history",
    "idea": "raw recent observations over a folded summary of the rest",
    "carries": "one summary plus a byte-capped tail of raw text",
    "run": run,
}


def self_check() -> None:
    from world import World, grade

    world = World.build(40, seed=5)
    outcome = run(world, Port(backend="fixture"))
    verdict = grade(world, outcome["answer"])
    assert verdict["solved"], verdict
    assert "compactions" in outcome["detail"]
    assert world.reads == list(world.shard_ids), "each shard read once, in order"
    # a smaller tail must not change the answer, only the bytes
    tight = World.build(40, seed=5)
    port = Port(backend="fixture")
    tiny = run(tight, port, tail_bytes=120)
    assert grade(tight, tiny["answer"])["solved"], tiny
    wide = Port(backend="fixture")
    run(World.build(40, seed=5), wide, tail_bytes=4000)
    assert port.peak_prompt_bytes < wide.peak_prompt_bytes, (
        "the tail budget must actually control the peak")
    # the guard that the first version of this file did not have
    starved = World.build(6, seed=5)
    answer = run(starved, Port(backend="fixture"), tail_bytes=1)
    assert grade(starved, answer["answer"])["solved"], (
        "a tail budget under one observation must not silently lose it")
    print(f"summarised_history self-check: ok "
          f"(peak {port.peak_prompt_bytes} at 120, "
          f"{wide.peak_prompt_bytes} at 4000)")


if __name__ == "__main__":
    self_check()
