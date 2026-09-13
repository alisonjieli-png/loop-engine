"""Contract checks for stalled repair: shapes ride with the exception.

The repair loop refuses repeated invalid outputs; when it gives up, the
raised ModelResponseRepairStalled must carry the rejected shapes so a
recovery panel can forbid them instead of re-deriving the failure.
"""
from __future__ import annotations

from .model_response_admission import ModelResponseRepairStalled


def self_test() -> dict:
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    stalled = ModelResponseRepairStalled(
        "cycle stalled", step_id="orient", attempts=3,
        failure_code="repeated_invalid_output",
        rejected_digests=("aaa", "bbb"))
    check("repair_stall_carries_shapes_for_recovery",
          isinstance(stalled, RuntimeError)
          and stalled.step_id == "orient" and stalled.attempts == 3
          and stalled.failure_code == "repeated_invalid_output"
          and stalled.rejected_digests == ("aaa", "bbb")
          and str(stalled) == "cycle stalled",
          "message unchanged; shapes ride as attributes for the "
          "recovery panel")
    bare = ModelResponseRepairStalled("stalled")
    check("stall_defaults_stay_empty_not_none",
          bare.step_id == "" and bare.attempts == 0
          and bare.failure_code == "" and bare.rejected_digests == (),
          "old raise sites without keywords keep working")

    passed = sum(1 for item in results if item["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
