#!/usr/bin/env python3
"""Hamilton-method integer quota apportionment as a bounded JSON CLI.

This module is the single executable tool for the
``apportion_integer_quotas`` method. It:

* reads one UTF-8 JSON object from stdin (capped at 1 MiB),
* validates it against the rules documented in ``AGENTS.md``,
* allocates ``target`` integer sample slots across the weighted groups using
  Hamilton's largest-remainders method with exact ``Fraction`` arithmetic,
* prints exactly one JSON object on stdout and exits.

It deliberately avoids file I/O, network use, subprocesses, and
``eval``/``exec``. It only writes to stdout. The host owns the effect
authority; this module grants itself nothing.

Run it directly::

    python3 tools/apportion_integer_quotas.py < input.json

The output schema is documented in ``contracts/output.schema.json``.
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from typing import Any

# --------------------------------------------------------------------------- #
# Public, stable constants.
# --------------------------------------------------------------------------- #

MAX_INPUT_BYTES: int = 1 << 20  # 1 MiB
MAX_PORTABLE_INT: int = (1 << 53) - 1  # JSON-safe integer range

# Error codes returned in the structured ``refused`` status. The host can
# branch on these exactly; messages are human-readable only.
E_INPUT_BYTES = "E_INPUT_BYTES"
E_INPUT_SHAPE = "E_INPUT_SHAPE"
E_TARGET = "E_TARGET"
E_WEIGHTS = "E_WEIGHTS"
E_WEIGHT_VALUE = "E_WEIGHT_VALUE"
E_WEIGHT_ID = "E_WEIGHT_ID"
E_WEIGHTS_ALL_ZERO = "E_WEIGHTS_ALL_ZERO"
E_INTERNAL = "E_INTERNAL"

PROG = "apportion_integer_quotas"
VERSION = "1.0.0"


# --------------------------------------------------------------------------- #
# Output helpers.
# --------------------------------------------------------------------------- #


def _emit(obj: dict[str, Any]) -> None:
    """Write one JSON object to stdout and flush.

    No trailing newline is added. The caller still controls the final exit
    status. ``ensure_ascii=False`` keeps IDs readable; ``sort_keys=False``
    preserves the order computed by the algorithm.
    """
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, sort_keys=False))
    sys.stdout.flush()


def _refuse(code: str, message: str) -> dict[str, Any]:
    """Build a structured refused payload.

    Refusal messages are deliberately generic and never echo input values or
    IDs. The caller writes this object to stdout and exits non-zero.
    """
    return {"status": "refused", "error": {"code": code, "message": message}}


# --------------------------------------------------------------------------- #
# Input validation. Every step raises ``ValueError`` with the public error
# code so the main entry point can convert it to a refused payload without
# echoing private values.
# --------------------------------------------------------------------------- #


def _ensure_portable_int(value: Any, code: str) -> int:
    """Coerce ``value`` to an int in the portable JSON range.

    Booleans are rejected; they are not numbers in this protocol.
    """
    if isinstance(value, bool) or value is None:
        raise ValueError(code)
    if isinstance(value, int):
        n = value
    elif isinstance(value, float):
        # Reject NaN, +inf, -inf explicitly before converting.
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(code)
        if not value.is_integer():
            raise ValueError(code)
        n = int(value)
    else:
        raise ValueError(code)
    if n < 0 or n > MAX_PORTABLE_INT:
        raise ValueError(code)
    return n


def _load_input(raw: bytes) -> dict[str, Any]:
    """Parse and validate the single stdin object.

    * Enforces the 1 MiB ceiling.
    * Requires exactly one outer JSON value (the object) with no trailing
      garbage.
    * Rejects duplicate JSON keys by routing through ``object_pairs_hook``.
    * Rejects non-finite numbers (``NaN``, ``Infinity``, ``-Infinity``).
    """
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(E_INPUT_BYTES)

    text = raw.decode("utf-8")

    def _hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: dict[str, None] = {}
        for key, _ in pairs:
            if key in seen:
                raise ValueError(E_INPUT_SHAPE)
            seen[key] = None
        return dict(pairs)

    decoder = json.JSONDecoder(object_pairs_hook=_hook)
    try:
        obj = decoder.decode(text)
    except json.JSONDecodeError as exc:
        raise ValueError(E_INPUT_SHAPE) from exc
    if obj is None or not isinstance(obj, dict):
        raise ValueError(E_INPUT_SHAPE)

    # Re-check JSON duplicate keys against the reconstructed dict. ``_hook``
    # already enforces uniqueness, but a more subtle duplicate (same pair
    # preserved by ``decode``) is still caught here.
    raw_obj = obj

    # Reject non-finite floats inside the object. ``json.loads`` rejects
    # ``NaN`` by default; ``allow_nan=True`` would not, but we use the default
    # decoder above, so any literal non-finite tokens raise ``ValueError``.
    # The walk below catches numeric values that round-tripped from user data
    # in other containers (lists, nested objects).
    def _walk(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, (int,)):
            return
        if isinstance(node, float):
            if node != node or node in (float("inf"), float("-inf")):
                raise ValueError(E_INPUT_SHAPE)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if not isinstance(k, str):
                    raise ValueError(E_INPUT_SHAPE)
                _walk(v)
            return

    _walk(raw_obj)
    return raw_obj


def _validate(data: dict[str, Any]) -> tuple[int, dict[str, int]]:
    """Return ``(target, weights)`` after full validation."""
    if "target" not in data:
        raise ValueError(E_TARGET)
    target = _ensure_portable_int(data["target"], E_TARGET)

    if "weights" not in data or not isinstance(data["weights"], dict):
        raise ValueError(E_WEIGHTS)

    raw_weights: dict[str, Any] = data["weights"]
    if not raw_weights:
        raise ValueError(E_WEIGHTS)

    weights: dict[str, int] = {}
    for key in raw_weights:
        if not isinstance(key, str) or key == "":
            raise ValueError(E_WEIGHT_ID)
        weights[key] = _ensure_portable_int(raw_weights[key], E_WEIGHT_VALUE)

    if target > 0 and all(v == 0 for v in weights.values()):
        raise ValueError(E_WEIGHTS_ALL_ZERO)

    return target, weights


# --------------------------------------------------------------------------- #
# Algorithm. Pure and easily testable.
# --------------------------------------------------------------------------- #


def apportion(target: int, weights: dict[str, int]) -> dict[str, int]:
    """Hamilton's largest-remainders method with exact ``Fraction`` math.

    Pre-conditions are checked by :func:`_validate`; this function assumes
    them. ``target`` is a non-negative int and ``weights`` maps unique
    nonempty strings to non-negative ints with at least one positive value
    when ``target`` is positive.
    """
    allocations: dict[str, int] = {key: 0 for key in weights}

    if target == 0:
        return allocations

    sum_w = sum(weights.values())
    # ``sum_w`` is always > 0 here, otherwise _validate refused.

    # Compute floor + remainder for each group.
    fractions: dict[str, Fraction] = {}
    for key, w in weights.items():
        ideal = Fraction(target) * Fraction(w) / Fraction(sum_w)
        floor = ideal.numerator // ideal.denominator  # exact floor
        allocations[key] = floor
        fractions[key] = ideal - floor

    remaining = target - sum(allocations.values())
    if remaining <= 0:
        return allocations

    # Award the remaining slots, breaking ties by ascending ID.
    order = sorted(weights.keys(), key=lambda k: (-fractions[k], k))
    for i in range(remaining):
        allocations[order[i]] += 1
    return allocations


# --------------------------------------------------------------------------- #
# Entry point.
# --------------------------------------------------------------------------- #


def main(argv: list[str]) -> int:
    """Run the CLI. Returns a process exit status."""
    try:
        raw = sys.stdin.buffer.read()
        data = _load_input(raw)
        target, weights = _validate(data)
        allocations = apportion(target, weights)
    except ValueError as exc:
        code = str(exc)
        messages = {
            E_INPUT_BYTES: "input exceeded the 1 MiB byte ceiling",
            E_INPUT_SHAPE: "input is not a single JSON object",
            E_TARGET: "target must be a non-negative integer",
            E_WEIGHTS: "weights must be a non-empty object of integers",
            E_WEIGHT_VALUE: "each weight must be a non-negative integer",
            E_WEIGHT_ID: "each group id must be a non-empty string",
            E_WEIGHTS_ALL_ZERO: "weights are all zero but target is positive",
            E_INTERNAL: "internal failure",
        }
        message = messages.get(code, "invalid input")
        _emit(_refuse(code, message))
        return 2
    except Exception:  # pragma: no cover - defensive
        _emit(_refuse(E_INTERNAL, "internal failure"))
        return 2

    _emit(
        {
            "status": "ok",
            "sum": sum(allocations.values()),
            "allocations": allocations,
        }
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
