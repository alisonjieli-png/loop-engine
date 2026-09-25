"""Measure review calibration, throughput, rates and disagreement from review ledgers only.

Every number comes from ledger rows the review panel wrote: call rows (single
and batch), their elapsed seconds and reported usage, and verdict rows. Nothing
is estimated from a model's own statement. A number the ledgers cannot give is
written as null with the reason.

    PYTHONPATH=src:tools python artifacts/review-throughput-2026-09-24/measure_review_throughput.py \\
        --calibration-ledger PATH --calibration-set PATH ... --panel-ledger PATH --output PATH
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src"), str(ROOT)]

from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.records import BATCH_CALL_RECORD  # noqa: E402

RECORD_TYPE = "review_throughput_measurement/v1"
SECONDS_PER_HOUR = 3600.0


def _labels(paths) -> dict:
    labels = {}
    for path in paths:
        value = json.loads(Path(path).read_text())
        for item in value["items"]:
            labels[item["identity"]] = item["expected_decision"]
    return labels


def _calls(ledger) -> list:
    """Every call row, single or batch, with the items it asked about."""
    rows = []
    for call in ledger.calls():
        rows.append({**call, "items": [call["identity"]], "batch": False})
    for call in ledger.batch_calls():
        rows.append({**call, "items": [member["identity"] for member in call["members"]], "batch": True})
    return rows


def _verdicts(ledger) -> list:
    """Every verdict with the mode of the call that produced it."""
    calls = {(call["run_id"], call["sequence"]): call for call in _calls(ledger)}
    rows = []
    for verdict in ledger.verdicts():
        call = calls[(verdict["run_id"], verdict["sequence"])]
        rows.append({**verdict, "batch": call["record_type"] == BATCH_CALL_RECORD,
                     "batch_size": len(call["items"])})
    return rows


def calibration(ledgers: dict, labels: dict) -> dict:
    """Per installation and mode: decisions on every control, errors against the labels, and agreement."""
    by_key = defaultdict(dict)  # (installation, run label, mode) -> identity -> decision
    invalid = Counter()
    calls = Counter()
    for name, path in ledgers.items():
        ledger = ReviewLedger(Path(path))
        for verdict in _verdicts(ledger):
            if verdict["identity"] in labels:
                mode = "batched" if verdict["batch"] else "single"
                by_key[(verdict["installation_id"], name, mode)][verdict["identity"]] = verdict["decision"]
        for call in _calls(ledger):
            if not set(call["items"]) & set(labels):
                continue
            mode = "batched" if call["batch"] else "single"
            calls[(call["installation_id"], name, mode)] += 1
            if call["batch"]:
                invalid[(call["installation_id"], name, mode)] += sum(
                    1 for member in call["members"] if member["outcome"] != "verdict")
            elif call["outcome"] != "verdict":
                invalid[(call["installation_id"], name, mode)] += 1
    runs = []
    for key, decisions in sorted(by_key.items()):
        installation, name, mode = key
        wrong = [identity for identity, label in labels.items() if label == "reject" and identity in decisions]
        good = [identity for identity, label in labels.items() if label == "approve" and identity in decisions]
        runs.append({
            "installation_id": installation, "ledger": name, "mode": mode, "calls": calls[key],
            "controls_answered": len(decisions), "controls_without_a_valid_verdict": invalid[key],
            "false_approvals": sorted(identity for identity in wrong if decisions[identity] == "approve"),
            "known_wrong_rejected": sum(1 for identity in wrong if decisions[identity] == "reject"),
            "known_wrong_answered": len(wrong),
            "label_refusals": sorted(identity for identity in good if decisions[identity] == "reject"),
            "decisions": dict(sorted(decisions.items()))})
    agreement = []
    installations = sorted({run["installation_id"] for run in runs})
    for installation in installations:
        mine = [run for run in runs if run["installation_id"] == installation]
        for index, first in enumerate(mine):
            for second in mine[index + 1:]:
                shared = sorted(set(first["decisions"]) & set(second["decisions"]))
                same = sum(1 for identity in shared if first["decisions"][identity] == second["decisions"][identity])
                agreement.append({"installation_id": installation,
                                  "first": f"{first['ledger']}/{first['mode']}",
                                  "second": f"{second['ledger']}/{second['mode']}",
                                  "controls_compared": len(shared), "same_decision": same,
                                  "different": sorted(identity for identity in shared
                                                      if first["decisions"][identity] != second["decisions"][identity])})
    return {"runs": runs, "agreement": agreement}


def panel(ledger_path: Path, controls: set) -> dict:
    """Throughput per installation, decision rates, disagreement between families and calls per decision."""
    ledger = ReviewLedger(ledger_path)
    calls = [call for call in _calls(ledger) if not set(call["items"]) & controls]
    verdicts = [verdict for verdict in _verdicts(ledger) if verdict["identity"] not in controls]
    per = {}
    for installation in sorted({call["installation_id"] for call in calls}):
        mine = [call for call in calls if call["installation_id"] == installation]
        judged = [verdict for verdict in verdicts if verdict["installation_id"] == installation]
        elapsed = sum(call["elapsed_seconds"] for call in mine)
        known = [call for call in mine if call["usage"]["input_tokens"] is not None
                 and call["usage"]["output_tokens"] is not None]
        decisions = Counter(verdict["decision"] for verdict in judged)
        per[installation] = {
            "family": mine[0]["family"], "model": mine[0]["model"],
            "calls": len(mine), "calls_by_outcome": dict(Counter(call["outcome"] for call in mine)),
            "batch_calls": sum(1 for call in mine if call["batch"]),
            "items_asked": sum(len(call["items"]) for call in mine),
            "verdicts": len(judged), "approve": decisions.get("approve", 0), "reject": decisions.get("reject", 0),
            "approval_rate": round(decisions.get("approve", 0) / len(judged), 4) if judged else None,
            "call_seconds_total": round(elapsed, 3),
            "seconds_per_call": round(elapsed / len(mine), 1) if mine else None,
            "verdicts_per_hour_of_call_time": round(len(judged) / (elapsed / SECONDS_PER_HOUR), 1) if elapsed else None,
            "calls_per_verdict": round(len(mine) / len(judged), 3) if judged else None,
            "input_tokens_reported": sum(call["usage"]["input_tokens"] for call in known),
            "output_tokens_reported": sum(call["usage"]["output_tokens"] for call in known),
            "calls_with_unknown_usage": len(mine) - len(known)}
    by_item = defaultdict(dict)
    for verdict in verdicts:
        by_item[verdict["identity"]][verdict["family"]] = verdict["decision"]
    families = sorted({verdict["family"] for verdict in verdicts})
    pairs = []
    for index, first in enumerate(families):
        for second in families[index + 1:]:
            both = [decisions for decisions in by_item.values() if first in decisions and second in decisions]
            table = Counter((decisions[first], decisions[second]) for decisions in both)
            agree = table[("approve", "approve")] + table[("reject", "reject")]
            count = len(both)
            observed = agree / count if count else None
            first_yes = sum(1 for decisions in both if decisions[first] == "approve") / count if count else None
            second_yes = sum(1 for decisions in both if decisions[second] == "approve") / count if count else None
            expected = (first_yes * second_yes + (1 - first_yes) * (1 - second_yes)) if count else None
            kappa = ((observed - expected) / (1 - expected)) if count and expected is not None and expected < 1 \
                else None
            pairs.append({"families": [first, second], "items_judged_by_both": count,
                          "both_approve": table[("approve", "approve")], "both_reject": table[("reject", "reject")],
                          f"{first}_approves_{second}_rejects": table[("approve", "reject")],
                          f"{first}_rejects_{second}_approves": table[("reject", "approve")],
                          "disagreement_rate": round(1 - observed, 4) if observed is not None else None,
                          "cohen_kappa": round(kappa, 4) if kappa is not None else None})
    runs = ledger.runs()
    ends = {row["run_id"]: row for row in ledger.run_ends()}
    wall = sum(ends[row["run_id"]]["elapsed_seconds"] for row in runs if row["run_id"] in ends)
    return {"installations": per, "family_pairs": pairs, "items_with_a_verdict": len(by_item),
            "wall_seconds_of_runs": round(wall, 3), "runs": [row["run_id"] for row in runs]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--calibration-ledger", action="append", default=[],
                        help="NAME=PATH of one calibration ledger.")
    parser.add_argument("--calibration-set", action="append", default=[], help="A calibration set with labels.")
    parser.add_argument("--panel-ledger", type=Path, help="The ledger of the run on real candidates.")
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    labels = _labels(options.calibration_set)
    ledgers = dict(value.split("=", 1) for value in options.calibration_ledger)
    record = {"record_type": RECORD_TYPE, "calibration": calibration(ledgers, labels) if ledgers else None,
              "panel": panel(options.panel_ledger, set(labels)) if options.panel_ledger else None,
              "limits": "Calibration measures known defect classes on nine fixed controls; it does not estimate "
                        "error rates on real candidates. Items per hour are verdicts over the summed call time of "
                        "one installation; concurrent calls of other installations are not subtracted."}
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"written": str(options.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
