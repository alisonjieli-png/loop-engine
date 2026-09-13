#!/usr/bin/env python3
"""Rank refusal messages by what they actually COST, not by a static count.

A static audit of this codebase reports ~159 model-facing refusals that do not
name the legal shape. That number is misleading and I produced it: classifying
them shows about 40 are internal assertions the model never sees ("has no
active Practitioner Loop owner"), and another 50 already state the requirement
in a "X must be Y" form. Fixing all 159 would be work aimed at a number rather
than at a problem.

The refusals worth fixing are the ones that FIRE, and specifically the ones
that fire more than once in a run -- a refusal seen twice is a refusal the
model could not act on, which is the definition of one that failed to say what
was required. That is an empirical question, answered by reading run logs, not
by grepping source.

Measured 2026-09-06 across the day's runs: exactly two messages accounted for
every full-run loss attributable to refusal wording. Both are now fixed. This
tool exists so the next two are found the same way instead of by audit.

Usage:
    python3 tools/refusal_census.py /path/to/run.log [more.log ...]
"""
from __future__ import annotations

import collections
import json
import re
import sys

#: Refusal text as it reaches the model, however the log framed it.
_PATTERNS = (
    re.compile(r'"error"\s*:\s*"([^"]{12,240})"'),
    re.compile(r'"reason"\s*:\s*"([^"]{12,240})"'),
    re.compile(r'"repair_hint"\s*:\s*"([^"]{12,240})"'),
    re.compile(r'(?:Error|error)[: ]+([A-Za-z][^"\\\n]{12,200})'),
)
#: Wording that tells the model what WOULD be accepted.
_NAMES_A_SHAPE = ("admitted", "available", "must be one of", "instead",
                  "for example", "e.g.", "such as", "the shape", "use ",
                  "add a", "declare", "required field")


def census(paths) -> dict:
    seen = collections.Counter()
    for path in paths:
        try:
            text = open(path, errors="ignore").read()
        except OSError:
            continue
        for pattern in _PATTERNS:
            for message in pattern.findall(text):
                cleaned = " ".join(message.split())[:200]
                if cleaned:
                    seen[cleaned] += 1
    return seen


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    seen = census(sys.argv[1:])
    if not seen:
        print("no refusals found in the supplied logs")
        return 0
    repeated = [(m, n) for m, n in seen.most_common() if n > 1]
    print(f"{len(seen)} distinct refusal(s); {len(repeated)} fired more than once\n")
    print("REPEATED -- the model could not act on these, so they are the ones")
    print("that failed to say what was required:\n")
    for message, count in repeated[:12]:
        shaped = any(k in message.lower() for k in _NAMES_A_SHAPE)
        flag = "names a shape" if shaped else "SILENT -> FIX THIS"
        print(f"  x{count:<3} [{flag}]")
        print(f"       {message[:150]}")
    if not repeated:
        print("  (none -- every refusal was acted on first time)")
    print("\nfired once (informational):")
    for message, _ in [(m, n) for m, n in seen.most_common() if n == 1][:5]:
        print(f"       {message[:130]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
