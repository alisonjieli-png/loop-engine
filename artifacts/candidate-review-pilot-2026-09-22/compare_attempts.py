"""Compare the two pilot attempts of the independent review panel, from their ledgers only.

Attempt one sent every written criterion for every body. Attempt two tells each
reviewer the kind of body the item declares, in the review sheet's own words,
and sends only the criteria for that kind. This script measures what changed,
on the pairs of one reviewer and one item that both attempts asked about, and
on the calibration items both attempts asked every reviewer about.

It reads the two ledgers with the panel's strict ledger reader and the
catalogue's item file for each item's declared kind. It calls no model, reaches
no network and writes one JSON report:

    PYTHONPATH=src:tools python \\
        artifacts/candidate-review-pilot-2026-09-22/compare_attempts.py \\
        --write artifacts/candidate-review-pilot-2026-09-22/comparison.json

A difference between the attempts is an observation about two prompts on a
small sample. It is not a measured error rate of any reviewer.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from candidate_review.ledger import ReviewLedger  # noqa: E402

RECORD_TYPE = "candidate_review_attempt_comparison/v1"
ITEMS = ROOT / "examples/29_intelligence_service/starter-catalogue/items.json"
CALIBRATION_SET = ROOT / "tools/candidate_review/resources/calibration-set.json"
LEDGERS = {"attempt_1": HERE / "attempt-1" / "ledger.jsonl", "attempt_2": HERE / "attempt-2" / "ledger.jsonl"}
#: The grounding criterion each kind of body is judged by. Citing the other one misapplies the review sheet.
OWN_GROUNDING_CRITERION = {"restates_cited_source": "restated_source_grounding",
                           "general_practice_beside_cited_source": "general_practice_grounding"}
GROUNDING_CRITERIA = frozenset(OWN_GROUNDING_CRITERION.values())
EFFECT_CRITERIA = frozenset({"effects_rule", "licence_and_effects"})
LIMITS = ("Two prompts compared on the pairs of one reviewer and one item that both attempts asked about, with "
          "the same body bytes and the same reviewer installations. Model answers vary between calls, so a changed "
          "decision is not attributed to the prompt alone. The sample is small and was not chosen at random for "
          "this comparison: attempt one stopped when the session that ran it reached its limit.")


def _groundings() -> dict:
    items = json.loads(ITEMS.read_text(encoding="utf-8"))["items"]
    return {row["reference"]["identity"]: row["provenance"]["grounding"] for row in items}


def _calibration() -> dict:
    value = json.loads(CALIBRATION_SET.read_text(encoding="utf-8"))
    return {row["identity"]: row for row in value["items"]}


def _kind(identity: str, groundings: dict, calibration: dict) -> str:
    if identity in calibration:
        return groundings[calibration[identity]["base_identity"]]
    return groundings[identity]


def _misapplied(finding: dict, kind: str) -> bool:
    return finding["criterion_id"] in GROUNDING_CRITERIA and finding["criterion_id"] != OWN_GROUNDING_CRITERION[kind]


def _summary(name: str, ledger: ReviewLedger, groundings: dict, calibration: dict) -> dict:
    calls, verdicts = ledger.calls(), ledger.verdicts()
    reported = [call["usage"] for call in calls if call["usage"]["input_tokens"] is not None
                and call["usage"]["output_tokens"] is not None]
    decisions = defaultdict(Counter)
    rejections = Counter()
    for verdict in verdicts:
        section = "calibration" if verdict["identity"] in calibration else "candidates"
        decisions[f"{section}:{verdict['installation_id']}"][verdict["decision"]] += 1
        if verdict["decision"] != "reject" or section != "candidates":
            continue
        kind = _kind(verdict["identity"], groundings, calibration)
        blocking = [finding for finding in verdict["findings"] if finding["blocking"]]
        rejections["rejections"] += 1
        if any(_misapplied(finding, kind) for finding in blocking):
            rejections["citing_the_other_kind_grounding_criterion"] += 1
        if blocking and all(_misapplied(finding, kind) for finding in blocking):
            rejections["resting_only_on_the_other_kind_grounding_criterion"] += 1
        if any(finding["criterion_id"] in EFFECT_CRITERIA for finding in blocking):
            rejections["citing_an_effects_criterion"] += 1
        if blocking and all(finding["criterion_id"] in EFFECT_CRITERIA for finding in blocking):
            rejections["resting_only_on_an_effects_criterion"] += 1
    return {"attempt": name, "runs": [row["run_id"] for row in ledger.runs()],
            "run_ends": [{"run_id": row["run_id"], "stop_reason": row["stop_reason"],
                          "elapsed_seconds": row["elapsed_seconds"], "calls": row["calls"]}
                         for row in ledger.run_ends()],
            "dispatches": len(ledger.dispatches()), "calls": len(calls),
            "interrupted_dispatches": [{"run_id": row["run_id"], "sequence": row["sequence"],
                                        "installation_id": row["installation_id"], "identity": row["identity"]}
                                       for row in ledger.interrupted_dispatches()],
            "calls_by_outcome": dict(sorted(Counter(call["outcome"] for call in calls).items())),
            "calls_with_unknown_usage": len(calls) - len(reported),
            "input_tokens_reported": sum(usage["input_tokens"] for usage in reported),
            "output_tokens_reported": sum(usage["output_tokens"] for usage in reported),
            "verdicts": len(verdicts),
            "decisions_by_installation": {key: dict(sorted(value.items()))
                                          for key, value in sorted(decisions.items())},
            "candidate_rejections": dict(sorted(rejections.items()))}


def _pairs(first: ReviewLedger, second: ReviewLedger, groundings: dict, calibration: dict) -> dict:
    """Pairs of one installation and one item that both attempts decided on the same body bytes."""
    def index(ledger):
        return {(row["installation_id"], row["identity"], row["body_sha256"]): row for row in ledger.verdicts()}
    before, after = index(first), index(second)
    shared = sorted(set(before) & set(after))
    changes, rows = Counter(), []
    for key in shared:
        old, new = before[key], after[key]
        kind = _kind(key[1], groundings, calibration)
        changes[f"{old['decision']}_to_{new['decision']}"] += 1
        rows.append({"installation_id": key[0], "identity": key[1], "calibration_item": key[1] in calibration,
                     "attempt_1": old["decision"], "attempt_2": new["decision"],
                     "attempt_1_misapplied_grounding": any(_misapplied(finding, kind) for finding in old["findings"]
                                                           if finding["blocking"]),
                     "attempt_1_blocking_criteria": sorted({finding["criterion_id"] for finding in old["findings"]
                                                            if finding["blocking"]}),
                     "attempt_2_blocking_criteria": sorted({finding["criterion_id"] for finding in new["findings"]
                                                            if finding["blocking"]})})
    return {"pairs": len(shared), "decision_changes": dict(sorted(changes.items())), "rows": rows}


def compare() -> dict:
    groundings, calibration = _groundings(), _calibration()
    ledgers = {name: ReviewLedger(path) for name, path in LEDGERS.items()}
    return {"record_type": RECORD_TYPE,
            "ledgers": {name: str(path.relative_to(ROOT)) for name, path in LEDGERS.items()},
            "attempts": [_summary(name, ledger, groundings, calibration) for name, ledger in ledgers.items()],
            "shared_pairs": _pairs(ledgers["attempt_1"], ledgers["attempt_2"], groundings, calibration),
            "limits": LIMITS}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", type=Path, help="Write the report here instead of printing it.")
    options = parser.parse_args(argv)
    payload = json.dumps(compare(), indent=2, ensure_ascii=True) + "\n"
    if options.write:
        options.write.write_text(payload, encoding="ascii")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
