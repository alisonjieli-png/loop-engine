"""Verification 1: the run is finished when the run says it is finished.

No independent check at all. This is the baseline, and it is also what a
system does by default when nobody chose a verification policy, so it is worth
measuring rather than assuming.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))


def verify(world, outcome: dict) -> dict:
    answer = outcome.get("answer")
    if not isinstance(answer, dict):
        return {"accepted": False, "reason": "no answer object", "reads": 0}
    if outcome.get("stopped") != "answered":
        return {"accepted": False,
                "reason": f"stopped {outcome.get('stopped')}", "reads": 0}
    return {"accepted": True, "reason": "", "reads": 0}


ARM = {
    "name": "self_report",
    "checks": "that a reply claiming to be an answer arrived",
    "verify": verify,
}


def self_check() -> None:
    assert verify(None, {"answer": {"net": 1}, "stopped": "answered"})["accepted"]
    assert not verify(None, {"answer": None, "stopped": "answered"})["accepted"]
    assert not verify(None, {"answer": {}, "stopped": "step_ceiling"})["accepted"]
    print("self_report self-check: ok")


if __name__ == "__main__":
    self_check()
