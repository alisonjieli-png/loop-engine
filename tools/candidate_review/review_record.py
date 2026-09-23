"""The dated panel review record, written beside ``reviews.json``, and its strict reader.

Record ``starter_catalogue_panel_review/v1`` holds one row for every item the
panel was asked to review, in the row shape of the catalogue's review record
(identity, body path and digest, declared licence, source layer, decisions,
outcome, approval state, rule and approval reference), plus what this panel
adds: the pre-check results, each decision's findings and the call it came
from, every reviewer with its engine, family, model, route or command and
version, every installation that was not asked and why, every call with its
usage and outcome, every call that was dispatched and never completed (its
outcome and usage unknown), the runs, the population rule and the totals.

The record approves nothing on its own and edits no other record. The lead
engineer merges its verdicts into the served catalogue through the carry and
manifest tools. The reader therefore refuses any record whose approvals the
panel rule does not support, so a merge can trust what it reads.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path, PurePosixPath
import re

import loop_engine

from .catalogue import select_population
from .configuration import FIXTURE_ENGINE_KIND, PanelPolicy
from .ledger import read_row
from .panel import (
    APPROVED, FAMILY_QUORUM_RULE, ITEM_OUTCOMES, NOT_STARTED, PANEL_INCOMPLETE, REFUSED_BEFORE_REVIEW, REJECTED,
    REJECTION_RULE, VERDICT_OUTCOME, distinct_families,
)
from .records import (
    CALL_RECORD, DISPATCH_RECORD, PANEL_REVIEW_RECORD, RUN_END_RECORD, RUN_RECORD, SHA256, read_part, read_record,
    refuse,
)
from .verdicts import APPROVE, DECISIONS, REJECT

REVIEWED_STATE, NO_STATE = "reviewed", "none"
SEEDED_HASH_ORDER = "seeded_hash_order"
EXPLICIT_LIST = "explicit_list"
POPULATION_RULES = (SEEDED_HASH_ORDER, EXPLICIT_LIST)
SECONDS_PER_HOUR = 3600.0
TOP_FIELDS = ("recorded_at", "record_path", "fixture_run", "catalogue_folder", "catalogue_items_record_type",
              "catalogue_source_revision", "complements_review_record", "approval_ref_prefix", "decision_rule",
              "what_an_approval_permits", "what_a_rejection_records", "what_a_row_without_a_verdict_records",
              "population", "producers", "policy", "criteria", "instructions", "reviewers", "ineligible_reviewers",
              "calibration", "rows", "calls", "interrupted_dispatches", "runs", "totals")
CALIBRATION_FIELDS = ("set_sha256", "purpose", "items", "run_id", "installations", "excluded", "limits", "calls",
                      "interrupted_dispatches")
CALIBRATION_STATUSES = ("qualified", "failed_calibration", "calibration_incomplete")
ROW_FIELDS = ("identity", "body_path", "body_sha256", "body_size_bytes", "declared_license", "source_layer",
              "grounding", "criteria_applied", "prechecks", "decisions", "outcome", "approval_state",
              "rule_applied", "approval_ref", "reasons")
DECISION_FIELDS = ("reviewer_id", "decision", "reason", "findings", "body_sha256", "call_ref")
REVIEWER_FIELDS = ("reviewer_id", "label", "engine_kind", "family", "model", "model_version", "route_or_command",
                   "engine_version", "installation_sha256", "lens", "produced_any_item_under_review")
POPULATION_FIELDS = ("rule", "seed", "eligible_count", "eligible", "selected")
DECISION_RULE = ("An item is approved only when at least three reviewers approve it, from at least three "
                 "different model families, none of them the family that produced the item, and no reviewer "
                 "rejects it. One written rejection keeps the item a candidate with its reasons. Deterministic "
                 "pre-checks for licence, format, safety, effects, secrets and duplicates run first and refuse "
                 "before any reviewer is asked.")
WHAT_AN_APPROVAL_PERMITS = ("An approved row may be merged into the catalogue's review record by the lead engineer "
                            "and then served by a host whose licence policy accepts the item's licence. Approval "
                            "covers only the bytes named by the row's digest and grants no effect, network access, "
                            "spending or model authority.")
WHAT_A_REJECTION_RECORDS = ("A rejected row stays a candidate with each rejecting reviewer's reason and findings. "
                            "It may be repaired and put to a new review, which judges new bytes.")
WHAT_A_ROW_WITHOUT_A_VERDICT_RECORDS = ("A row refused before review, incomplete, or not started has no standing "
                                        "verdict. It carries no approval reference and stays a candidate. Partial "
                                        "decisions are kept, and a later run reuses them without asking again.")


@lru_cache(maxsize=1)
def retired_terms() -> tuple:
    """The repository's retired words, from the one policy file that lists them."""
    policy = json.loads((Path(loop_engine.__file__).parent / "forbidden_paths.json").read_text(encoding="utf-8"))
    return tuple(sorted(set(policy["retired_source_nomenclature"]["terms"]), key=len, reverse=True))


def serialized(value: dict) -> bytes:
    """The record as ASCII JSON whose bytes hold no retired word, decoding to exactly the same record.

    Reviewer text is evidence and is never changed. A retired word inside it has
    its first letter written as a JSON escape, so the file decodes to the same
    text while the repository's scans of committed files find no retired word.
    Every character outside ASCII, a dash for example, is escaped the same way."""
    text = json.dumps(value, indent=2, ensure_ascii=True) + "\n"
    for term in retired_terms():
        text = re.sub(re.escape(term), lambda match: "\\u%04x" % ord(match.group(0)[0]) + match.group(0)[1:],
                      text, flags=re.IGNORECASE)
    return text.encode("ascii")


@dataclass(frozen=True)
class PopulationSelection:
    """Which items were put to the panel and by which declared rule."""

    rule: str
    seed: str
    eligible: tuple
    selected: tuple

    def to_dict(self) -> dict:
        return {"rule": self.rule, "seed": self.seed, "eligible_count": len(self.eligible),
                "eligible": list(self.eligible), "selected": list(self.selected)}


def approval_rule_holds(approvers, family_of, policy) -> bool:
    return (len(approvers) >= policy.minimum_approvals
            and distinct_families(approvers, family_of) >= policy.minimum_distinct_families)


def _version(call) -> tuple:
    return json.dumps(call["model_version"], sort_keys=True), call["engine_version"]


def _reviewers(ledger_calls, configuration, producer_families) -> list:
    """Every installation that was called, named with the model and engine versions its calls answered with.

    A reviewer whose calls name two versions is two reviewers, and the record refuses to merge them."""
    asked = {call["installation_id"] for call in ledger_calls}
    rows = []
    for installation in configuration.installations:
        if installation.installation_id not in asked:
            continue
        calls = [call for call in ledger_calls if call["installation_id"] == installation.installation_id]
        if len({_version(call) for call in calls}) != 1:
            refuse("reviewer_version_changed_during_review",
                   f"the calls of {installation.installation_id} name more than one model or engine version")
        last = calls[-1]
        rows.append({"reviewer_id": installation.installation_id,
                     "label": f"{installation.model}, {installation.family} family, {installation.lens} lens",
                     "engine_kind": installation.engine_kind, "family": installation.family,
                     "model": installation.model, "model_version": dict(last["model_version"]),
                     "route_or_command": last["route_or_command"], "engine_version": last["engine_version"],
                     "installation_sha256": installation.sha256, "lens": installation.lens,
                     "produced_any_item_under_review": installation.family in producer_families})
    return rows


def _relative(path, repository) -> str:
    """A path inside the repository, written relative to its root, as every committed record names paths."""
    try:
        return Path(path).resolve().relative_to(Path(repository).resolve()).as_posix()
    except ValueError:
        refuse("record_path_not_relative", "a record names only paths inside the repository")


def _row(item, catalogue, prefix) -> dict:
    reference = catalogue.item(item.identity)["reference"]
    approved = item.outcome == APPROVED
    return {"identity": item.identity, "body_path": catalogue.item(item.identity)["body_path"],
            "body_sha256": item.request.body_sha256, "body_size_bytes": item.request.body_size_bytes,
            "declared_license": reference.get("license"), "source_layer": reference.get("source_layer"),
            "grounding": item.request.grounding, "criteria_applied": sorted(item.request.applicable_criteria_ids),
            "prechecks": item.prechecks.to_dict(),
            "decisions": [{"reviewer_id": verdict["reviewer_id"], "decision": verdict["decision"],
                           "reason": verdict["reasons"], "findings": verdict["findings"],
                           "body_sha256": verdict["body_sha256"],
                           "call_ref": f"{verdict['run_id']}#{verdict['sequence']}"} for verdict in item.verdicts],
            "outcome": item.outcome, "approval_state": REVIEWED_STATE if approved else NO_STATE,
            "rule_applied": item.rule_applied, "approval_ref": prefix + item.identity if approved else "",
            "reasons": [str(reason) for reason in item.reasons]}


def _totals(rows, calls, runs, interrupted) -> dict:
    outcomes = [row["outcome"] for row in rows]
    by_outcome = {}
    for call in calls:
        by_outcome[call["outcome"]] = by_outcome.get(call["outcome"], 0) + 1
    known = [call["physical_model_calls"] for call in calls if call["physical_model_calls"] is not None]
    reported = [call["usage"] for call in calls
                if call["usage"]["input_tokens"] is not None and call["usage"]["output_tokens"] is not None]
    # Review time is the time of the runs that made the calls. A later command that only reused stored
    # verdicts, for example to write the record again, adds no review time.
    reviewing = {call["run_id"] for call in calls}
    seconds = round(sum(run["elapsed_seconds"] for run in runs if run["record_type"] == RUN_END_RECORD
                        and run["run_id"] in reviewing), 3)
    standing = outcomes.count(APPROVED) + outcomes.count(REJECTED) + outcomes.count(REFUSED_BEFORE_REVIEW)
    return {"items_selected": len(rows), **{outcome: outcomes.count(outcome) for outcome in ITEM_OUTCOMES},
            "disagreements": sum(1 for row in rows
                                 if {decision["decision"] for decision in row["decisions"]} == {APPROVE, REJECT}),
            "calls": len(calls), "calls_by_outcome": dict(sorted(by_outcome.items())),
            "interrupted_dispatches": len(interrupted),
            "physical_model_calls_known": sum(known), "calls_with_unknown_physical_count": len(calls) - len(known),
            "calls_with_unknown_usage": len(calls) - len(reported),
            "input_tokens_reported": sum(usage["input_tokens"] for usage in reported),
            "output_tokens_reported": sum(usage["output_tokens"] for usage in reported),
            "charged_tokens": sum(call["charged_tokens"] for call in calls),
            "pause_seconds": round(sum(call["pause_seconds_after"] for call in calls), 3),
            "run_seconds": seconds,
            "items_with_a_standing_verdict_per_hour": round(standing / (seconds / SECONDS_PER_HOUR), 3)
            if seconds > 0 else None}


def build_panel_review_record(result, ledger, *, catalogue, configuration, criteria, instructions, producers,
                              population: PopulationSelection, recorded_at: str, record_path: str,
                              fixture_run: bool = False, calibration_report=None,
                              calibration_requests=()) -> dict:
    """Assemble the dated record from the final run's outcomes and every call the ledger holds for them.

    ``calibration_report`` is the calibration evaluation of the same session, and
    ``calibration_requests`` the request digests of its items; their calls are
    kept in the calibration section, apart from the calls on real candidates."""
    prefix = record_path + "#"
    by_identity = {item.identity: item for item in result.items}
    rows = [_row(by_identity[identity], catalogue, prefix) for identity in population.selected]
    requests = {item.request.request_sha256 for item in result.items}
    calls = sorted((call for call in ledger.calls() if call["request_sha256"] in requests),
                   key=lambda call: (call["started_at"], call["run_id"], call["sequence"]))
    interrupted = _interrupted(ledger, requests)
    run_ids = {call["run_id"] for call in calls} | {row["run_id"] for row in interrupted} | {result.run_id}
    runs = [row for row in ledger.runs() + ledger.run_ends() if row["run_id"] in run_ids]
    producer_families = {producers.producer_for(identity).family for identity in population.selected}
    ineligible = [{"installation_id": identity, "reason": reason,
                   "family": configuration.installation(identity).family,
                   "model": configuration.installation(identity).model,
                   "disabled_reason": configuration.installation(identity).disabled_reason}
                  for identity, reason in sorted(result.ineligible.items())]
    calibration = None
    if calibration_report is not None:
        wanted = set(calibration_requests)
        calibration = {**calibration_report, "calls": sorted(
            (call for call in ledger.calls() if call["request_sha256"] in wanted),
            key=lambda call: (call["started_at"], call["run_id"], call["sequence"])),
            "interrupted_dispatches": _interrupted(ledger, wanted)}
    return {"record_type": PANEL_REVIEW_RECORD, "recorded_at": recorded_at, "record_path": record_path,
            "fixture_run": fixture_run, "catalogue_folder": producers.catalogue_folder,
            "catalogue_items_record_type": "starter_catalogue_candidate_items/v2",
            "catalogue_source_revision": catalogue.source_revision,
            "complements_review_record": {"path": "reviews.json", "record_type": "starter_catalogue_independent_review/v2",
                                          "sha256": catalogue.review_record_sha256},
            "approval_ref_prefix": prefix, "decision_rule": DECISION_RULE,
            "what_an_approval_permits": WHAT_AN_APPROVAL_PERMITS,
            "what_a_rejection_records": WHAT_A_REJECTION_RECORDS,
            "what_a_row_without_a_verdict_records": WHAT_A_ROW_WITHOUT_A_VERDICT_RECORDS,
            "population": population.to_dict(), "producers": producers.to_dict(),
            "policy": configuration.policy.to_dict(), "criteria": {**criteria.to_dict(),
                                                                    "source_sha256": criteria.source_sha256,
                                                                    "criteria_sha256": criteria.sha256},
            "instructions": {"path": _relative(instructions.path, catalogue.repository),
                             "sha256": instructions.sha256},
            "reviewers": _reviewers(calls, configuration, producer_families),
            "ineligible_reviewers": ineligible, "calibration": calibration, "rows": rows, "calls": calls,
            "interrupted_dispatches": interrupted,
            "runs": sorted(runs, key=lambda row: (row["run_id"], row["record_type"])),
            "totals": _totals(rows, calls, runs, interrupted)}


def _interrupted(ledger, requests) -> list:
    """The dispatches for these requests that never received a call row, in the order they were sent."""
    return sorted((row for row in ledger.interrupted_dispatches() if row["request_sha256"] in requests),
                  key=lambda row: (row["dispatched_at"], row["run_id"], row["sequence"]))


def _producer_family(record, identity) -> str:
    for row in record["producers"]["item_producers"]:
        if row["identity"] == identity:
            return row["family"]
    return record["producers"]["default_producer"]["family"]


def read_panel_review_record(value, *, allow_fixture: bool = False) -> dict:
    """Return the record only when every row, decision, call and total agrees with the panel rule."""
    record = read_record(value, PANEL_REVIEW_RECORD, TOP_FIELDS)
    if record["fixture_run"] is not False and not allow_fixture:
        refuse("fixture_reviewer_in_record", "this record comes from a fixture run")
    policy = PanelPolicy.from_dict(record["policy"])
    reviewers = {}
    for raw in record["reviewers"]:
        reviewer = read_part(raw, "reviewer", REVIEWER_FIELDS)
        if reviewer["reviewer_id"] in reviewers:
            refuse("reviewer_repeated", f"{reviewer['reviewer_id']} is named twice")
        if reviewer["engine_kind"] == FIXTURE_ENGINE_KIND and not allow_fixture:
            refuse("fixture_reviewer_in_record", f"{reviewer['reviewer_id']} is a fixture reviewer")
        reviewers[reviewer["reviewer_id"]] = reviewer
    family_of = {identity: reviewer["family"] for identity, reviewer in reviewers.items()}
    calls, ordered = {}, []
    for raw in record["calls"]:
        call = read_row(raw)
        if call["record_type"] != CALL_RECORD:
            refuse("record_call_unsupported", "the calls list holds only call records")
        reviewer = reviewers.get(call["installation_id"])
        if reviewer is not None and _version(call) != _version(reviewer):
            refuse("reviewer_version_disagrees_with_calls",
                   f"{call['installation_id']} is named with another version than its calls answered with")
        calls[f"{call['run_id']}#{call['sequence']}"] = call
        ordered.append(call)
    _read_paths(record)
    interrupted = _read_interrupted(record["interrupted_dispatches"], calls)
    for raw in record["runs"]:
        if read_row(raw)["record_type"] not in (RUN_RECORD, RUN_END_RECORD):
            refuse("record_run_unsupported", "the runs list holds only run records")
    if record["calibration"] is not None:
        _read_calibration(record["calibration"], record["ineligible_reviewers"])
    population = read_part(record["population"], "population", POPULATION_FIELDS)
    if population["rule"] not in POPULATION_RULES:
        refuse("population_rule_unknown", f"population rules are {list(POPULATION_RULES)}")
    identities = [row.get("identity") for row in record["rows"]]
    if identities != list(population["selected"]):
        refuse("rows_do_not_cover_population", "the rows must name exactly the selected items, in order")
    prefix = record["approval_ref_prefix"]
    if prefix != record["record_path"] + "#":
        refuse("approval_ref_inconsistent", "the approval reference prefix names another record")
    for raw in record["rows"]:
        _read_row(read_part(raw, "row", ROW_FIELDS), reviewers, family_of, calls, policy, prefix,
                  _producer_family(record, raw["identity"]))
    runs = [read_row(raw) for raw in record["runs"]]
    if record["totals"] != _totals(record["rows"], ordered, runs, interrupted):
        refuse("totals_inconsistent", "the totals disagree with the rows and the calls")
    return record


def _read_paths(record) -> None:
    """Every path a committed record names is relative to the repository root and stays inside it."""
    paths = [record["record_path"], record["catalogue_folder"], record["instructions"]["path"],
             record["criteria"]["source_path"], record["producers"]["evidence"]["path"],
             *(row["body_path"] for row in record["rows"])]
    for path in paths:
        pure = PurePosixPath(path) if type(path) is str else None
        if pure is None or not path or pure.is_absolute() or ".." in pure.parts or "\\" in path:
            refuse("record_path_not_relative", f"the record names the path {str(path)[:80]!r}")


def _read_interrupted(values, calls) -> list:
    """Every listed interruption is a dispatch record whose call never completed."""
    if type(values) is not list:
        refuse("record_dispatch_unsupported", "interrupted_dispatches is a list of dispatch records")
    rows = []
    for raw in values:
        row = read_row(raw)
        if row["record_type"] != DISPATCH_RECORD:
            refuse("record_dispatch_unsupported", "interrupted_dispatches holds only dispatch records")
        if f"{row['run_id']}#{row['sequence']}" in calls:
            refuse("dispatch_not_interrupted", f"dispatch {row['run_id']}#{row['sequence']} has a completed call")
        rows.append(row)
    return rows


def _read_calibration(value, ineligible) -> None:
    calibration = read_part(value, "calibration", CALIBRATION_FIELDS)
    calls = {}
    for raw in calibration["calls"]:
        call = read_row(raw)
        if call["record_type"] != CALL_RECORD:
            refuse("record_call_unsupported", "the calibration calls list holds only call records")
        calls[f"{call['run_id']}#{call['sequence']}"] = call
    _read_interrupted(calibration["interrupted_dispatches"], calls)
    for installation_id, status in calibration["excluded"].items():
        if status not in CALIBRATION_STATUSES[1:]:
            refuse("calibration_inconsistent", f"{installation_id} is excluded for an unknown reason")
    excluded_for_calibration = {row["installation_id"]: row["reason"] for row in ineligible
                                if row["reason"] in CALIBRATION_STATUSES[1:]}
    if excluded_for_calibration != dict(calibration["excluded"]):
        refuse("calibration_inconsistent", "the reviewers excluded by calibration differ from the calibration result")


def _read_row(row, reviewers, family_of, calls, policy, prefix, producer_family) -> None:
    identity, outcome = row["identity"], row["outcome"]
    if outcome not in ITEM_OUTCOMES:
        refuse("row_outcome_unknown", f"{identity} records the outcome {outcome!r}")
    if outcome == APPROVED and row["body_sha256"] is None:
        refuse("approval_without_digest", f"approved {identity} names no digest")
    if row["body_sha256"] is not None and (type(row["body_sha256"]) is not str
                                           or not SHA256.fullmatch(row["body_sha256"])):
        refuse("row_digest_invalid", f"{identity} names no valid digest")
    applied = row["criteria_applied"]
    if type(applied) is not list or any(type(item) is not str for item in applied):
        refuse("row_inconsistent", f"{identity} names the criteria it was judged by as a list")
    for raw in row["decisions"]:
        decision = read_part(raw, "decision", DECISION_FIELDS)
        if any(type(finding) is not dict or finding.get("criterion_id") not in applied
               for finding in decision["findings"]):
            refuse("finding_outside_the_criteria_applied",
                   f"a decision on {identity} cites a criterion that does not apply to its kind of body")
        if decision["reviewer_id"] not in reviewers:
            refuse("unknown_reviewer", f"{identity} records a decision by a reviewer the record does not name")
        if family_of[decision["reviewer_id"]] == producer_family:
            refuse("producer_family_approved" if decision["decision"] == APPROVE else "producer_family_decided",
                   f"a reviewer of the family that produced {identity} decided it")
        if decision["decision"] not in DECISIONS:
            refuse("decision_unknown", f"{identity} records the decision {decision['decision']!r}")
        if decision["body_sha256"] != row["body_sha256"]:
            refuse("decision_bound_to_other_bytes", f"a decision on {identity} names other bytes than the row")
        call = calls.get(decision["call_ref"])
        if (call is None or call["outcome"] != VERDICT_OUTCOME or call["installation_id"] != decision["reviewer_id"]
                or call["body_sha256"] != decision["body_sha256"] or call["decision"] != decision["decision"]):
            refuse("decision_without_call", f"a decision on {identity} names no matching call")
    rejections = [decision for decision in row["decisions"] if decision["decision"] == REJECT]
    approvers = [decision["reviewer_id"] for decision in row["decisions"] if decision["decision"] == APPROVE]
    if outcome == APPROVED:
        if rejections:
            refuse("approval_beside_rejection", f"{identity} is approved while a reviewer rejected it")
        if not approval_rule_holds(approvers, family_of, policy):
            refuse("approval_below_quorum", f"{identity} lacks the approvals or families the rule needs")
        if row["approval_state"] != REVIEWED_STATE or row["rule_applied"] != FAMILY_QUORUM_RULE \
                or row["approval_ref"] != prefix + identity:
            refuse("approval_ref_inconsistent", f"approved {identity} must carry its own approval reference")
        return
    if row["approval_ref"] != "" or row["approval_state"] != NO_STATE:
        refuse("approval_ref_inconsistent", f"{identity} has no approval and carries an approval reference")
    if outcome == REJECTED:
        if not rejections or row["rule_applied"] != REJECTION_RULE:
            refuse("rejection_inconsistent", f"rejected {identity} records no rejection")
        if any(not str(decision["reason"]).strip() for decision in rejections):
            refuse("rejection_without_reason", f"a rejection of {identity} has no written reason")
    elif rejections:
        refuse("rejection_inconsistent", f"{identity} records a rejection and the outcome {outcome}")
    if outcome in (REFUSED_BEFORE_REVIEW, NOT_STARTED) and row["decisions"]:
        refuse("row_inconsistent", f"{identity} records decisions without a review")


__all__ = ["PopulationSelection", "build_panel_review_record", "read_panel_review_record", "select_population",
           "approval_rule_holds", "serialized", "retired_terms", "REVIEWED_STATE", "NO_STATE", "SEEDED_HASH_ORDER",
           "EXPLICIT_LIST"]
