"""One model port, three backends, and the accounting every arm shares.

The comparison isolates transport, so the thing that reads a prompt must be
identical across arms. The fixture backend is that: a pure function of the
prompt text that plays perfectly on whatever the prompt actually contains. An
arm whose transport carries what the step needs succeeds. An arm whose
transport loses it fails, or pays calls to recover it. Nothing about the arms'
relative standing depends on a model's mood, and that is the point.

The fixture is a perfect player, so this measures transport, not reasoning.
Whether a real model uses a given transport well is a separate question, and
the same arms answer it against a live backend.

The context limit is enforced here rather than in the arms, so every arm faces
the same window, and a prompt over it is refused with a typed error instead of
being silently truncated. A silent truncation would hide the wall this
experiment exists to find.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass, field

#: Bytes, not tokens. Tokens are model specific; bytes are comparable across
#: arms and are what a transport actually moves.
DEFAULT_CONTEXT_LIMIT = 16_000

SHARD_HEADER = re.compile(r"^shard (s\d+)$", re.M)
ROW = re.compile(r"^([a-z]+),(DR|CR),(\d+)$", re.M)


class ContextWindowExceeded(RuntimeError):
    """A prompt did not fit. The arm hit its wall; that is a result."""


@dataclass
class Call:
    step: str
    prompt_bytes: int
    reply_bytes: int
    refused: bool = False


@dataclass
class Port:
    """Accounting plus one backend. An arm holds a Port and nothing else."""

    backend: str = "fixture"
    model: str = "glm-5.3-flash:cloud"
    context_limit: int = DEFAULT_CONTEXT_LIMIT
    calls: list = field(default_factory=list)
    #: Optional. When set it replaces the backend dispatch and receives the
    #: prompt. The execution-placement family uses this to move the same
    #: reader into a subprocess or a container without changing any arm, so
    #: what that family measures is placement and not the reader. Unset
    #: leaves every existing arm on exactly the path it had before.
    evaluator: object = None

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def prompt_bytes_total(self) -> int:
        return sum(call.prompt_bytes for call in self.calls)

    @property
    def peak_prompt_bytes(self) -> int:
        return max((call.prompt_bytes for call in self.calls), default=0)

    @property
    def refusals(self) -> int:
        return sum(1 for call in self.calls if call.refused)

    def ask(self, step: str, prompt: str) -> str:
        """One model call. Raises when the prompt does not fit the window."""
        prompt_bytes = len(prompt.encode("utf-8"))
        if prompt_bytes > self.context_limit:
            self.calls.append(Call(step, prompt_bytes, 0, refused=True))
            raise ContextWindowExceeded(
                f"{step}: prompt is {prompt_bytes} bytes, "
                f"window is {self.context_limit}")
        if self.evaluator is not None:
            reply = self.evaluator(prompt)
        else:
            reply = (fixture_reply(prompt) if self.backend == "fixture"
                     else _ollama(prompt, self.model))
        self.calls.append(Call(step, prompt_bytes, len(reply.encode("utf-8"))))
        return reply


def _ollama(prompt: str, model: str) -> str:
    """The one live path, used only when a caller asks for a live backend."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("OLLAMA_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        "http://localhost:11434/api/chat", data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = json.loads(response.read())
    return payload.get("message", {}).get("content", "")


def extract_json(text: str):
    """The one reply reader. Every arm parses replies the same way."""
    if not isinstance(text, str):
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start, end = text.find("{"), text.rfind("}")
        candidate = text[start:end + 1] if 0 <= start < end else None
    if candidate is None:
        return None
    try:
        return json.loads(candidate)
    except ValueError:
        return None


# --- the constant held across arms ---------------------------------------

def empty_carry() -> dict:
    """The closed accumulator shape. It is O(1) in the number of shards."""
    return {"net": 0, "accounts": {}, "best_shard": "", "best_abs": -1,
            "shards_folded": []}


def fold_prompt(prompt: str, carry: dict) -> dict:
    """Fold every shard block present in this prompt into the accumulator.

    A shard already folded is not folded twice, which is what makes a
    transport that repeats history cost bytes without buying correctness.
    """
    carry = {**empty_carry(), **(carry or {})}
    carry["accounts"] = dict(carry.get("accounts") or {})
    folded = list(carry.get("shards_folded") or [])
    positions = [(m.start(), m.group(1)) for m in SHARD_HEADER.finditer(prompt)]
    for index, (start, shard_id) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(prompt)
        if shard_id in folded:
            continue
        shard_net = 0
        for account, side, amount in ROW.findall(prompt[start:end]):
            signed = int(amount) if side == "DR" else -int(amount)
            shard_net += signed
            carry["net"] += signed
            carry["accounts"][account] = carry["accounts"].get(account, 0) + signed
        if (abs(shard_net) > carry["best_abs"]
                or (abs(shard_net) == carry["best_abs"]
                    and shard_id < carry["best_shard"])):
            carry["best_abs"], carry["best_shard"] = abs(shard_net), shard_id
        folded.append(shard_id)
    carry["shards_folded"] = folded
    return carry


def finalize(carry: dict) -> dict:
    return {"net": carry.get("net", 0),
            "unbalanced": sum(1 for value in (carry.get("accounts") or {}).values()
                              if value != 0),
            "largest": carry.get("best_shard", "")}


def fixture_reply(prompt: str) -> str:
    """Perfect play on exactly what the prompt contains, and nothing else.

    The function has no memory between calls and never touches the world. An
    arm that does not carry the accumulator forward, and does not repeat the
    rows, genuinely loses the work, which is the behavior under test.
    """
    carried = _block(prompt, "CARRIED")
    # A player offered a way to fetch what it was not given uses it. This is
    # the pull architecture's whole premise, so refusing to model it would
    # decide the comparison in advance.
    pullable = re.findall(r'"([a-z_]+)"', _raw_block(prompt, "PULLABLE") or "")
    if pullable and carried is None:
        return json.dumps({"action": "pull", "keys": pullable})
    carry = fold_prompt(prompt, carried or {})
    # Two ways a transport can say what is left: the whole list, which grows
    # with the horizon, or a cursor, which does not. A perfect player uses
    # whichever the prompt offers, so the choice is the arm's, not the
    # player's.
    cursor = re.search(r"NEXT\s*=\s*(s\d+|none)", prompt)
    if cursor:
        if cursor.group(1) != "none":
            return json.dumps({"action": "read", "shard": cursor.group(1),
                               "carry": carry})
    else:
        remaining = re.findall(r"s\d+", _raw_block(prompt, "REMAINING") or "")
        if remaining:
            return json.dumps({"action": "read", "shard": remaining[0],
                               "carry": carry})
    return json.dumps({"action": "answer", **finalize(carry), "carry": carry})


def _raw_block(prompt: str, name: str):
    match = re.search(rf"{name}\s*=\s*(\[.*?\]|\{{.*?\}})\s*(?:\n|$)",
                      prompt, re.S)
    return match.group(1) if match else None


def _block(prompt: str, name: str):
    raw = _raw_block(prompt, name)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def self_check() -> None:
    from world import World, oracle

    port = Port(backend="fixture")
    assert port.ask("a", "REMAINING = []\n") is not None
    assert port.call_count == 1
    try:
        port.ask("b", "x" * (DEFAULT_CONTEXT_LIMIT + 1))
        raise AssertionError("an oversize prompt must be refused")
    except ContextWindowExceeded:
        pass
    assert port.refusals == 1, "a refusal is recorded, not hidden"

    assert extract_json('text {"a": 1} tail') == {"a": 1}
    assert extract_json('```json\n{"b": 2}\n```') == {"b": 2}
    assert extract_json("no json here") is None

    # The fixture is perfect on complete information, by either route.
    world = World.build(4, seed=3)
    truth = oracle(world)
    everything = "REMAINING = []\n" + "\n\n".join(
        shard.rendered() for shard in world.shards)
    by_rows = extract_json(fixture_reply(everything))
    assert {k: by_rows[k] for k in truth} == truth, (by_rows, truth)

    carry = empty_carry()
    for shard in world.shards:
        carry = fold_prompt(shard.rendered(), carry)
    by_carry = extract_json(fixture_reply(
        "REMAINING = []\nCARRIED = " + json.dumps(carry) + "\n"))
    assert {k: by_carry[k] for k in truth} == truth, (by_carry, truth)

    # And it is wrong when the transport loses the work, which is the point.
    starved = extract_json(fixture_reply(
        "REMAINING = []\n" + world.shards[0].rendered()))
    assert starved["net"] != truth["net"] or len(world.shards) == 1
    # Folding the same shard twice does not double count.
    twice = fold_prompt(world.shards[0].rendered(),
                        fold_prompt(world.shards[0].rendered(), empty_carry()))
    once = fold_prompt(world.shards[0].rendered(), empty_carry())
    assert twice["net"] == once["net"], "a repeated shard must not double count"
    # an injected evaluator replaces the backend and is still accounted for
    seen = []
    injected = Port(evaluator=lambda text: seen.append(text) or '{"a": 1}')
    assert extract_json(injected.ask("c", "hello")) == {"a": 1}
    assert seen == ["hello"] and injected.call_count == 1
    assert Port().evaluator is None, "the default path must be untouched"
    print("port self-check: ok")


if __name__ == "__main__":
    self_check()
