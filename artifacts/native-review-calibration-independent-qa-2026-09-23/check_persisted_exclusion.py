"""No-provider counterexample: persisted calibration decisions cannot lose exclusions."""
from copy import deepcopy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]
from candidate_review import calibration, review_record
from candidate_review.records import CandidateReviewError
from test_candidate_review_native_calibration import run_fixture, decision
from test_candidate_review_record import APPROVED_RECORD

report, result = run_fixture(lambda prompt, number: decision(prompt, "approve"), reviewer_name="a")
record = deepcopy(APPROVED_RECORD)
record["calibration"] = {**report, "calls": result.calls, "interrupted_dispatches": []}
record["ineligible_reviewers"].append({"installation_id": "a", "reason": calibration.FAILED_CALIBRATION,
                                      "family": "zhipu", "model": "fixture-a", "disabled_reason": ""})

def check(value):
    try:
        review_record.read_panel_review_record(value, allow_fixture=True)
    except CandidateReviewError as error:
        return {"accepted": False, "code": error.code}
    return {"accepted": True}

control = check(record)
changed = deepcopy(record)
changed["calibration"]["excluded"] = {}
changed["ineligible_reviewers"] = [r for r in changed["ineligible_reviewers"]
                                  if r["reason"] not in (calibration.FAILED_CALIBRATION, calibration.CALIBRATION_INCOMPLETE)]
print(json.dumps({"model_calls": 0, "fixture_only": True,
                  "known_wrong_false_approvals_retained": changed["calibration"]["installations"]["a"]["false_approvals"],
                  "persisted_installation_status": changed["calibration"]["installations"]["a"]["status"],
                  "candidate_decisions_from_a": sum(d["reviewer_id"] == "a" for r in changed["rows"] for d in r["decisions"]),
                  "original_consistent_exclusion": control, "exclusion_lists_removed_only": check(changed)}, indent=2))
