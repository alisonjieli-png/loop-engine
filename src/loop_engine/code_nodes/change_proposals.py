"""Change proposals — every edit is a versioned proposal; history never mutates.

Architectural role: Code Node system (the intervention lane).

Owns:
    - ChangeProposal: the String envelope for a human or improvement-lane
      suggestion (target, change, rationale, expected effect, evidence,
      risk, diff, test plan, approval status);
    - apply_to_template: applying an APPROVED proposal creates a NEW
      template version (v7 → v8) at CANDIDATE maturity — the prior version
      and every historical run remain untouched; the candidate cannot run
      until admitted (loop_templates' existing gate);
    - the proposal state machine: draft → under_review → approved | rejected
      | deferred (forward-only except reopening a deferral).

Does not own:
    - generating proposals (run_analytics.propose_edits and the improvement
      lane do), admission (loop_templates), promotion (asset_lifecycle),
      or shadow-run execution (the caller runs and compares).

Public entry points:
    - ChangeProposal(...).to_record()
    - advance_status(status, to) -> str (refuses illegal jumps)
    - apply_to_template(template_body, proposal) -> new template body

Key invariants:
    - only an APPROVED proposal may be applied;
    - application NEVER edits the input template in place — it returns a new
      version with lineage back to the proposal and the prior version.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

PROPOSAL_STATUSES = ("draft", "under_review", "approved", "rejected",
                     "deferred")
_LEGAL = {("draft", "under_review"), ("under_review", "approved"),
          ("under_review", "rejected"), ("under_review", "deferred"),
          ("deferred", "under_review")}


class ProposalError(ValueError):
    """An illegal proposal transition or application."""


def record_proposal(proposal, *, ledger=None) -> dict:
    """Put a proposal on the run's timeline as ``change.proposed``.

    A proposal already existed as a record; it was invisible to the event
    vocabulary, so a Studio watching a run could not see that a change had
    been suggested. Opt-in: with no ledger the behaviour is unchanged."""
    rec = proposal.to_record() if hasattr(proposal, "to_record") else dict(proposal)
    if ledger is not None:
        ledger.record(loop_id="", event="change.proposed",
                      target=str(rec.get("target", ""))[:80],
                      status=str(rec.get("status", "draft")))
    return rec


def advance_status(status: str, to: str) -> str:
    if (status, to) not in _LEGAL:
        raise ProposalError(f"illegal proposal transition {status} -> {to}")
    return to


@dataclass
class ChangeProposal:
    """The suggestion as a String — never a direct edit."""
    proposal_id: str
    target_kind: str                    # loop_template | solution_component
    target_id: str
    change: dict                        # field -> new value
    rationale: str
    expected_effect: str = ""
    evidence: tuple = ()
    risk: str = ""
    test_plan: str = "shadow run + matched comparison before any promotion"
    status: str = "draft"

    def to_record(self):
        from ..static_architecture.store_serve import StoreRecord
        from ..static_architecture.facets import string_facets
        return StoreRecord(
            f"proposal.{self.proposal_id}", "strategy",
            f"Change proposal: {self.proposal_id} on {self.target_kind} "
            f"{self.target_id} [{self.status}]",
            body={"role": "change_proposal", "target_kind": self.target_kind,
                  "target_id": self.target_id, "change": dict(self.change),
                  "rationale": self.rationale,
                  "expected_effect": self.expected_effect,
                  "evidence": list(self.evidence), "risk": self.risk,
                  "test_plan": self.test_plan, "status": self.status,
                  "facets": string_facets(category="change_proposal",
                                          subcategory=self.target_kind,
                                          lifecycle=self.status)},
            tags=("change_proposal", self.target_kind, self.status))


_MUTABLE_TEMPLATE_FIELDS = ("steps", "allowed_modes", "description",
                            "stop_condition")


def apply_to_template(template_body: dict, proposal: ChangeProposal) -> dict:
    """APPROVED proposal + template vN -> a NEW template body vN+1 at
    candidate maturity, lineage attached.  The input body is never touched."""
    if proposal.status != "approved":
        raise ProposalError(f"proposal {proposal.proposal_id} is "
                            f"{proposal.status!r} — only approved proposals "
                            "apply")
    if proposal.target_kind != "loop_template":
        raise ProposalError("this applier owns loop templates only")
    illegal = [k for k in proposal.change if k not in
               _MUTABLE_TEMPLATE_FIELDS]
    if illegal:
        raise ProposalError(f"fields {illegal} are not proposal-editable "
                            "(identity/maturity move through their own "
                            "gates, never a proposal)")
    new = copy.deepcopy(template_body)
    version = int(template_body.get("version", 1)) + 1
    for k, v in proposal.change.items():
        new[k] = tuple(v) if isinstance(v, list) else v
    new["version"] = version
    new["maturity"] = "candidate"       # admission decides, never the edit
    new["lineage"] = tuple(template_body.get("lineage", ())) + (
        f"{template_body.get('template_id')}@v"
        f"{template_body.get('version', 1)} via {proposal.proposal_id}",)
    from ..loop.loop_templates import validate_template
    report = validate_template(new)
    if not report["valid"]:
        raise ProposalError("the edited template does not validate: "
                            + "; ".join(report["violations"]))
    return new


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
    base = dict(next(t for t in TEMPLATE_LIBRARY
                     if t["template_id"] == "build_test_repair"))
    base["version"] = 7

    prop = ChangeProposal(
        "trim_repair_loop", "loop_template", "build_test_repair",
        change={"steps": ["understand_minimum", "prototype", "run",
                          "diagnose", "repair", "rerun"]},
        rationale="the research_failure step repeatedly added tokens with no "
                  "quality gain in the mined ledgers",
        evidence=("stuckness_report: escalation_chain on repair loops",),
        risk="loses the research fallback for informational gaps")

    # 1. a draft cannot apply; the state machine refuses illegal jumps.
    refused_draft = refused_jump = False
    try:
        apply_to_template(base, prop)
    except ProposalError:
        refused_draft = True
    try:
        advance_status("draft", "approved")
    except ProposalError:
        refused_jump = True
    check("drafts_cannot_apply_and_jumps_are_refused",
          refused_draft and refused_jump)

    # 2. approval -> a NEW v8 at candidate maturity with lineage; v7 body
    # untouched; the candidate cannot run until admitted.
    prop.status = advance_status(advance_status("draft", "under_review"),
                                 "approved")
    v8 = apply_to_template(base, prop)
    cannot_run = False
    try:
        config_from_template(v8)
    except ValueError:
        cannot_run = True
    check("apply_creates_a_new_candidate_version_history_untouched",
          v8["version"] == 8 and v8["maturity"] == "candidate"
          and len(v8["steps"]) == 6 and len(base["steps"]) == 8
          and "via trim_repair_loop" in v8["lineage"][0]
          and base.get("lineage") is None and cannot_run,
          "v7 -> v8 candidate with lineage; admission still gates running")

    # 3. identity/maturity are not proposal-editable; invalid edits refuse.
    evil = ChangeProposal("evil", "loop_template", "build_test_repair",
                          change={"maturity": "registered"},
                          rationale="promote by edit", status="approved")
    orphan = ChangeProposal("orphan", "loop_template", "build_test_repair",
                            change={"steps": []}, rationale="x",
                            status="approved")
    refused_field = refused_invalid = False
    try:
        apply_to_template(base, evil)
    except ProposalError:
        refused_field = True
    try:
        apply_to_template(base, orphan)
    except ProposalError:
        refused_invalid = True
    check("promotion_by_edit_and_invalid_shapes_are_refused",
          refused_field and refused_invalid,
          "maturity is gate-owned; an orphan template does not validate")

    # 4. the proposal is a searchable String with its status on the card.
    rec = prop.to_record()
    check("proposals_are_searchable_strings",
          rec.body["role"] == "change_proposal"
          and rec.body["facets"]["lifecycle"] == "approved"
          and "approved" in rec.tags)

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
