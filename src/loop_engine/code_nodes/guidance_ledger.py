"""Guidance Ledger — due considerations with honest states, never a done-flag.

Architectural role: Code Node system (guidance state machinery; the guidance
items themselves are Strings).

Owns:
    - the eleven guidance states (§7.4 of the master specification) with a
      fail-closed legal-transition machine;
    - the default bootstrap guidance for nontrivial work (§7.2) with its
      before/after pairings (§7.3);
    - skip/defer RECEIPTS carrying the full record (reason, evidence, risk,
      alternative, revisit condition, expiration) — a skip without a reason
      is refused;
    - Guidance Debt: deferred/skipped items stay visible until satisfied,
      accepted as risk, or marked not applicable.

Does not own:
    - deciding WHEN an item is satisfied (the loop's verify/evaluate steps
      do), promotion, or any bias evidence accounting (bias_checklist and
      the improvement lane own their pieces).

Public entry points:
    - GuidanceLedger(items=BOOTSTRAP_GUIDANCE).advance(key, to, **receipt)
    - ledger.debt() / ledger.render_for_prompt()

Key invariants:
    - illegal transitions raise (e.g. not_considered -> satisfied_validated
      without passing through work);
    - skipped_with_reason and deferred REQUIRE reason + revisit_condition;
    - reopening is always legal from deferred/skipped/superseded (debt can
      come back due); history of every transition is append-only.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

from dataclasses import dataclass, field

GUIDANCE_STATES = ("not_considered", "due", "in_progress",
                   "satisfied_provisional", "satisfied_validated",
                   "deferred", "blocked", "not_applicable",
                   "skipped_with_reason", "superseded", "reopened")

_LEGAL = {
    ("not_considered", "due"), ("not_considered", "not_applicable"),
    ("due", "in_progress"), ("due", "deferred"), ("due", "blocked"),
    ("due", "skipped_with_reason"), ("due", "not_applicable"),
    ("in_progress", "satisfied_provisional"), ("in_progress", "blocked"),
    ("in_progress", "deferred"),
    ("satisfied_provisional", "satisfied_validated"),
    ("satisfied_provisional", "reopened"),
    ("satisfied_validated", "reopened"), ("satisfied_validated",
                                          "superseded"),
    ("deferred", "reopened"), ("skipped_with_reason", "reopened"),
    ("superseded", "reopened"), ("blocked", "due"), ("blocked", "deferred"),
    ("reopened", "due"), ("reopened", "in_progress"),
}

#: §7.2 — the default bootstrap considerations, each paired with its AFTER
#: obligation (§7.3): the after-item becomes due when the before-item is
#: satisfied.
BOOTSTRAP_GUIDANCE = (
    {"key": "define_goal", "text": "Define the ultimate goal, outputs, "
     "constraints, non-goals, and completion criteria.",
     "after": "evaluate_actual_result"},
    {"key": "assess_context_sufficiency", "text": "Assess whether relevant "
     "context and evidence are sufficient.",
     "after": "identify_new_gaps"},
    {"key": "retrieve_or_research_context", "text": "Retrieve, generate, or "
     "research missing context, terminology, entities, and history.",
     "after": "identify_new_gaps"},
    {"key": "create_blueprint", "text": "Create or retrieve a high-level "
     "Outcome Blueprint.", "after": "reconcile_with_blueprint"},
    {"key": "predict_risks", "text": "Identify common and uncommon mistakes, "
     "hidden assumptions, risks, and failure modes.",
     "after": "record_realized_failures"},
    {"key": "identify_best_practices", "text": "Identify best practices, "
     "alternatives, simplifications, and ensemble opportunities.",
     "after": "measure_practice_effect"},
    {"key": "define_success_measures", "text": "Define how success, failure, "
     "quality, cost, and completion will be measured.",
     "after": "evaluate_actual_result"},
    {"key": "search_reusable_capability", "text": "Search reusable Strings, "
     "Code Nodes, loops, Solutions, and prior outcomes.",
     "after": "store_new_reusable_capability"},
    {"key": "capture_learning", "text": "Capture what was learned as "
     "standardized resource candidates.", "after": ""},
    {"key": "confirm_readiness", "text": "Confirm readiness before composing "
     "or running a major Solution.", "after": ""},
)

_SKIP_REQUIRED = ("reason", "revisit_condition")


class GuidanceError(ValueError):
    """An illegal guidance transition or an incomplete skip receipt."""


@dataclass
class GuidanceItem:
    key: str
    text: str
    after: str = ""
    state: str = "due"
    history: list = field(default_factory=list)


class GuidanceLedger:
    """The semi-persistent ledger for one run/loop scope."""

    def __init__(self, items=BOOTSTRAP_GUIDANCE):
        self.items = {i["key"]: GuidanceItem(i["key"], i["text"],
                                             i.get("after", ""))
                      for i in items}
        # after-obligations start unconsidered; they become due on
        # satisfaction of their before-item.
        for i in items:
            a = i.get("after", "")
            if a and a not in self.items:
                self.items[a] = GuidanceItem(
                    a, f"AFTER obligation paired with '{i['key']}'.",
                    state="not_considered")

    def advance(self, key: str, to: str, ledger=None, **receipt) -> GuidanceItem:
        item = self.items[key]
        if to not in GUIDANCE_STATES:
            raise GuidanceError(f"unknown guidance state {to!r}")
        if (item.state, to) not in _LEGAL:
            raise GuidanceError(f"illegal guidance transition "
                                f"{item.state} -> {to} for {key!r}")
        if to in ("skipped_with_reason", "deferred"):
            missing = [f for f in _SKIP_REQUIRED if not receipt.get(f)]
            if missing:
                raise GuidanceError(
                    f"a {to} needs {missing} — a skip without its receipt "
                    "is refused (why, when to revisit, at minimum)")
        item.history.append({"from": item.state, "to": to, **receipt})
        item.state = to
        # satisfying a before-item makes its after-obligation DUE.
        if to in ("satisfied_provisional", "satisfied_validated") \
                and item.after and item.after in self.items:
            paired = self.items[item.after]
            if paired.state == "not_considered":
                paired.history.append({"from": "not_considered", "to": "due",
                                       "because": f"{key} satisfied"})
                paired.state = "due"
        return item

    def debt(self) -> list:
        """Deferred/skipped/blocked items stay VISIBLE until resolved."""
        return [{"key": i.key, "state": i.state,
                 "receipt": i.history[-1] if i.history else {}}
                for i in self.items.values()
                if i.state in ("deferred", "skipped_with_reason", "blocked")]

    def render_for_prompt(self, *, max_items: int = 8) -> str:
        due = [i for i in self.items.values()
               if i.state in ("due", "in_progress", "reopened")]
        lines = ["GUIDANCE (due considerations — satisfy, defer with a "
                 "receipt, or mark not applicable):"]
        lines += [f"- [{i.state}] {i.text}" for i in due[:max_items]]
        d = self.debt()
        if d:
            lines.append(f"GUIDANCE DEBT ({len(d)} item(s) deferred/skipped "
                         "— still owed):")
            lines += [f"- [{x['state']}] {x['key']}: "
                      f"{x['receipt'].get('reason', '?')}" for x in d[:4]]
        return "\n".join(lines)


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    g = GuidanceLedger()

    # 1. bootstrap items are due; after-obligations wait unconsidered.
    check("bootstrap_items_due_and_after_obligations_wait",
          g.items["define_goal"].state == "due"
          and g.items["evaluate_actual_result"].state == "not_considered"
          and len(g.items) >= 14)

    # 2. a skip WITHOUT its receipt is refused; with it, recorded fully.
    refused = False
    try:
        g.advance("create_blueprint", "skipped_with_reason")
    except GuidanceError:
        refused = True
    g.advance("create_blueprint", "skipped_with_reason",
              reason="tiny bounded task; blueprint adds no information",
              evidence="6-step smoke shape, one deliverable",
              risk="low — single-artifact output",
              alternative="direct execution",
              revisit_condition="if the task grows a second deliverable")
    check("skip_needs_its_full_receipt",
          refused and g.items["create_blueprint"].state
          == "skipped_with_reason"
          and g.items["create_blueprint"].history[-1]["revisit_condition"])

    # 3. illegal jumps refuse (no teleporting to satisfied_validated).
    refused2 = False
    try:
        g.advance("define_goal", "satisfied_validated")
    except GuidanceError:
        refused2 = True
    check("illegal_transitions_refused", refused2,
          "due -> satisfied_validated must pass through work")

    # 4. satisfying a BEFORE item makes its AFTER obligation due (§7.3).
    g.advance("define_goal", "in_progress")
    g.advance("define_goal", "satisfied_provisional")
    check("before_after_pairing_fires",
          g.items["evaluate_actual_result"].state == "due")

    # 5. debt stays visible and is reopenable.
    g.advance("predict_risks", "deferred",
              reason="risk scan queued behind data access",
              revisit_condition="when the dataset lands")
    debt = g.debt()
    g.advance("predict_risks", "reopened")
    g.advance("predict_risks", "due")
    check("debt_visible_and_reopenable",
          any(d["key"] == "predict_risks" for d in debt)
          and any(d["key"] == "create_blueprint" for d in debt)
          and g.items["predict_risks"].state == "due")

    # 6. the prompt rendering carries due items AND the debt.
    txt = g.render_for_prompt()
    check("prompt_rendering_carries_due_and_debt",
          "GUIDANCE" in txt and "GUIDANCE DEBT" in txt
          and "blueprint adds no information" in txt)

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
