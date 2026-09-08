"""Placement 1: the step runs inside the calling process.

The default, and the baseline every other placement is priced against. There
is no boundary, so there is nothing to cross and nothing to pay for. There is
also nothing to contain: a step that reads a file, exhausts memory or calls
exit takes the run with it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

from port import fixture_reply


def make_evaluator():
    """Return the callable the port will use for every step of a run."""
    return fixture_reply


def available() -> tuple:
    return True, ""


ARM = {
    "name": "in_process",
    "placement": "the calling process",
    "isolation": "none",
    "make_evaluator": make_evaluator,
    "available": available,
}


def self_check() -> None:
    reply = make_evaluator()("REMAINING = []\nshard s000\naccount,side,amount\n"
                             "cash,DR,5\n")
    assert '"net": 5' in reply, reply
    print("in_process self-check: ok")


if __name__ == "__main__":
    self_check()
