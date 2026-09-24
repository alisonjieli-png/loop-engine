"""Put the served item normalize_phone_numbers to the independent panel again, with the measured evidence.

The request is the ordinary starter-catalogue review request for the item's
current bytes, with one more cited source: the evidence file beside this
script, which quotes the data-cleanup study that measured a lower score with
the item. The request digest covers that source, so this is its own review
subject. The item's producer family (anthropic, Claude Code) is never asked,
as for any review. Every other reachable family is asked once; the families
out of reach are excluded with their written reasons.

The decision rule is written here before any call:

- any independent written rejection withdraws the standing approval of these
  bytes, and of every earlier digest of the item that differs from them only in
  the anchor line, because the same procedure is judged;
- the rejecting reviewers' reasons say whether a narrowed version (the same
  method with its limits stated) or a replacement is the repair; either is new
  bytes that need a new review and a new measurement before serving;
- if every eligible reviewer approves, the standing approval is left as it is
  and the record says so; one family cannot grant a new approval.

    PYTHONPATH=src:tools python artifacts/review-throughput-2026-09-24/adjudication/adjudicate_phone_item.py \\
        --ledger artifacts/review-throughput-2026-09-24/adjudication/ledger.jsonl \\
        --output artifacts/review-throughput-2026-09-24/adjudication/phone-item-adjudication.json --authorize-model-calls
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src"), str(ROOT)]

from candidate_review import configuration as config  # noqa: E402
from candidate_review import engines  # noqa: E402
from candidate_review.catalogue import CitedSource, StarterCatalogue  # noqa: E402
from candidate_review.ledger import ReviewLedger  # noqa: E402
from candidate_review.panel import PanelRunRequest, ReviewPanel  # noqa: E402
from candidate_review.records import sha256_hex  # noqa: E402
from candidate_review.reviewers import ReviewerContext  # noqa: E402

RECORD_TYPE = "catalogue_item_adjudication/v1"
IDENTITY = "normalize_phone_numbers"
CATALOGUE = ROOT / "examples/29_intelligence_service/starter-catalogue"
RESOURCES = ROOT / "tools/candidate_review/resources"
EVIDENCE = "artifacts/review-throughput-2026-09-24/adjudication/phone-item-evidence.md"
#: The digest the coordinator named as served, and the revision whose body has it.
SERVED_DIGEST = "8f0ab269db267078c2f9b3f4671d8785a9e8a3dcce0fbdac578f6b2dacf255ef"
SERVED_REVISION = "bb4c6c5b"
BODY = "examples/29_intelligence_service/starter-catalogue/bodies/normalize_phone_numbers.md"
DECISION_RULE = ("Any independent written rejection withdraws the standing approval of the judged bytes and of "
                 "every earlier digest of the item that differs only in its anchor line. The rejecting reasons "
                 "name the repair (narrow or replace); a repair is new bytes that need a new review and a new "
                 "measurement. If every eligible reviewer approves, the standing approval is left unchanged; one "
                 "family cannot grant a new approval.")


def _git(*arguments) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *arguments], capture_output=True, check=True).stdout


def anchor_line_only(old: bytes, new: bytes) -> dict:
    """Whether two bodies differ only in the one line that names the compile revision."""
    before, after = old.decode("utf-8").splitlines(), new.decode("utf-8").splitlines()
    different = [index for index, (a, b) in enumerate(zip(before, after)) if a != b]
    return {"lines": len(after), "same_length": len(before) == len(after), "different_lines": different,
            "anchor_line_only": len(before) == len(after) and len(different) == 1
            and "Compiled from revision" in before[different[0]] and "Compiled from revision" in after[different[0]]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclude-installation", action="append", default=[])
    parser.add_argument("--authorize-model-calls", action="store_true")
    options = parser.parse_args(argv)
    revision = _git("rev-parse", "HEAD").decode().strip()
    configuration = config.PanelConfiguration.from_dict(json.loads((RESOURCES / "panel.json").read_text()))
    criteria_record = json.loads((RESOURCES / "criteria.json").read_text())
    criteria = config.compile_criteria(criteria_record, (ROOT / criteria_record["source_path"]).read_text())
    producer_record = json.loads((RESOURCES / "producer-starter-catalogue.json").read_text())
    producers = config.ProducerDeclaration.from_dict(
        producer_record, (ROOT / producer_record["evidence"]["path"]).read_text(), configuration.families)
    instructions = config.load_instructions(RESOURCES / "REVIEWER-INSTRUCTIONS.md")
    catalogue = StarterCatalogue.load(CATALOGUE, ROOT)
    request = catalogue.request(IDENTITY, producers.producer_for(IDENTITY), criteria, instructions.sha256)
    evidence = _git("show", f"{revision}:{EVIDENCE}")
    if evidence != (ROOT / EVIDENCE).read_bytes():
        raise SystemExit("the evidence file must be committed unchanged before the adjudication")
    request = replace(request, cited_sources=request.cited_sources + (
        CitedSource(EVIDENCE, revision, sha256_hex(evidence), evidence.decode("utf-8")),))
    served = _git("show", f"{SERVED_REVISION}:{BODY}")
    exclusions = dict(value.split("=", 1) for value in options.exclude_installation)
    context = ReviewerContext(repository=ROOT, credential_resolver=__import__(
        "tools.operator_credentials", fromlist=["resolve"]).resolve if options.authorize_model_calls else None)
    reviewers = {item.installation_id: engines.build_reviewer(item, configuration.policy, context)
                 for item in configuration.installations}
    panel = ReviewPanel(configuration, criteria, instructions, reviewers,
                        engines.build_precheck_engines(configuration), ReviewLedger(options.ledger))
    run_id = "phone-adjudication-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = panel.run(PanelRunRequest(
        run_id=run_id, requests=(request,), population=catalogue.population_bodies(), call_ceiling=3,
        token_ceiling=400_000, model_calls_authorized=options.authorize_model_calls,
        excluded_installations=exclusions, quota_group_call_ceilings={"claude_subscription": 0},
        repeated_failure_limit=2,
        collect_below_quorum_reason="An adjudication of a served item: every reachable family other than the "
                                    "producer's is asked once, and one written rejection withdraws."))
    item = result.items[0]
    rejections = [verdict for verdict in item.verdicts if verdict["decision"] == "reject"]
    decision = ("withdraw" if rejections else ("approval_unchanged" if item.verdicts else "no_verdict"))
    record = {
        "record_type": RECORD_TYPE, "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "identity": IDENTITY, "reviewed_revision": revision, "reviewed_body_digest": request.body_sha256,
        "reviewed_body_size_bytes": request.body_size_bytes, "request_sha256": request.request_sha256,
        "evidence": {"path": EVIDENCE, "sha256": sha256_hex(evidence)},
        "served_digest_named_by_the_coordinator": SERVED_DIGEST, "served_body_revision": SERVED_REVISION,
        "served_body_digest_measured": sha256_hex(served),
        "served_body_relation": anchor_line_only(served, request.body),
        "producer": request.producer.to_dict(), "decision_rule": DECISION_RULE,
        "prechecks": item.prechecks.to_dict(), "verdicts": item.verdicts, "panel_outcome": item.outcome,
        "panel_rule": item.rule_applied, "reasons": item.reasons, "decision": decision,
        "repair": [verdict["reasons"] for verdict in rejections],
        "calls": result.calls, "ineligible": result.ineligible, "run_id": run_id,
        "ledger": str(options.ledger), "stop_reason": result.stop_reason}
    options.output.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=True) + "\n")
    print(json.dumps({"decision": decision, "outcome": item.outcome, "verdicts": len(item.verdicts),
                      "calls": len(result.calls), "stop_reason": result.stop_reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
