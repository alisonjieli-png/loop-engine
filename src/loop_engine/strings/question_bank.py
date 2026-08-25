"""Question storage tiers — Definition / Pattern / Instance / Outcome + maturity.

Owner spec (2026-08-23): the question bank is not a pile of prompt strings.  It is
four tiers, each answering a different thing, plus a maturity lifecycle so a
generated question earns trust by evidence rather than assertion:

  * **QuestionDefinition** — the SEMANTIC question we are answering
    ("what is the single most valuable next action?").  Stable, reusable.
  * **QuestionPattern** — HOW we ask/investigate it (a template with slots +
    the answer shape + which context policies / personas it suits).  A
    definition may have many patterns.
  * **QuestionInstance** — the EXACT task-specific rendered question (a pattern
    filled for one problem), addressed by a canonical payload digest.
  * **QuestionOutcomeRecord** — how USEFUL an instance was, under what
    conditions, at what cost — the utility/failure history the moat is built on.

Maturity: ``ephemeral`` -> ``candidate`` -> ``experimentally_validated`` ->
``preferred`` (within an applicability boundary).  ``promote`` moves a resource
up ONLY on recorded outcomes; it never skips tiers or promotes by assertion.

Everything is a resource with the standard envelope and is searchable through the
strict search/serve DAG.  This tiers the flat ``question_engine`` forms (a form
becomes a Pattern under a Definition) without discarding them.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Sequence

from ..strings.question_engine import ANSWER_SHAPES
from ..static_architecture.store_serve import StoreRecord, TIERS

MATURITY = ("ephemeral", "candidate", "experimentally_validated", "preferred")


def _digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


@dataclass
class QuestionDefinition:
    """The semantic question — WHAT we are answering."""
    definition_id: str
    intent: str
    domain: str = "general"
    keywords: tuple = ()

    def envelope(self) -> StoreRecord:
        return StoreRecord(
            record_id=f"qdef.{self.definition_id}", kind="question",
            title=self.intent[:80],
            body={"tier_type": "definition", "intent": self.intent,
                  "domain": self.domain},
            tags=("question_definition", self.domain) + tuple(self.keywords))


@dataclass
class QuestionPattern:
    """HOW we ask/investigate a definition — a template + answer shape."""
    pattern_id: str
    definition_id: str
    template: str                     # with {slot} placeholders
    answer_shape: str
    suits_context_policies: tuple = ()
    suits_personas: tuple = ()
    maturity: str = "candidate"
    provenance: str = "hand_authored"

    def __post_init__(self):
        if self.answer_shape not in ANSWER_SHAPES:
            raise ValueError(f"answer_shape must be one of {ANSWER_SHAPES}")
        if self.maturity not in MATURITY:
            raise ValueError(f"maturity must be one of {MATURITY}")
        self.slots = tuple(sorted(set(re.findall(r"{(\w+)}", self.template))))

    def render(self, **values) -> "QuestionInstance":
        missing = [s for s in self.slots if s not in values]
        if missing:
            raise ValueError(f"pattern {self.pattern_id!r} missing slots "
                             f"{missing}")
        text = self.template.format(**{k: values[k] for k in self.slots})
        return QuestionInstance(
            instance_id=_digest(self.pattern_id + "::" + text),
            pattern_id=self.pattern_id, definition_id=self.definition_id,
            text=text, answer_shape=self.answer_shape)

    def envelope(self) -> StoreRecord:
        return StoreRecord(
            record_id=f"qpat.{self.pattern_id}", kind="question",
            title=self.template[:80],
            body={"tier_type": "pattern", "definition_id": self.definition_id,
                  "template": self.template, "answer_shape": self.answer_shape,
                  "slots": list(self.slots), "provenance": self.provenance},
            tags=("question_pattern", self.answer_shape),
            tier="experimental" if self.maturity in ("ephemeral", "candidate")
            else "core")


@dataclass
class QuestionInstance:
    """The EXACT task-specific question, addressed by its payload digest."""
    instance_id: str
    pattern_id: str
    definition_id: str
    text: str
    answer_shape: str

    @property
    def payload_digest(self) -> str:
        return _digest(self.text)


@dataclass
class QuestionOutcomeRecord:
    """How useful an instance was — the utility/failure history."""
    instance_id: str
    pattern_id: str
    accepted: bool
    quality: float = 0.0             # 0..1, from the independent evaluator
    cost_tokens: int = 0
    conditions: dict = field(default_factory=dict)
    note: str = ""


class QuestionBank:
    """The four tiers + the maturity engine, over the standard store."""

    def __init__(self):
        self.definitions: dict = {}
        self.patterns: dict = {}
        self.outcomes: dict = {}        # pattern_id -> [QuestionOutcomeRecord]

    def add_definition(self, d: QuestionDefinition) -> None:
        self.definitions[d.definition_id] = d

    def add_pattern(self, p: QuestionPattern) -> None:
        if p.definition_id not in self.definitions:
            raise ValueError(f"pattern references unknown definition "
                             f"{p.definition_id!r}")
        self.patterns[p.pattern_id] = p

    def record_outcome(self, o: QuestionOutcomeRecord) -> None:
        self.outcomes.setdefault(o.pattern_id, []).append(o)

    def pattern_stats(self, pattern_id: str) -> dict:
        recs = self.outcomes.get(pattern_id, [])
        n = len(recs)
        acc = sum(1 for r in recs if r.accepted)
        mean_q = (sum(r.quality for r in recs) / n) if n else 0.0
        return {"trials": n, "accepted": acc,
                "acceptance_rate": (acc / n) if n else 0.0,
                "mean_quality": mean_q}

    def promote(self, pattern_id: str, *, min_trials: int = 5,
                good_quality: float = 0.6) -> str:
        """Advance a pattern's maturity ONE tier when the OUTCOMES justify it —
        never by assertion, never skipping a tier.  ephemeral needs a first
        accepted use; candidate needs enough good trials to be experimentally
        validated; experimentally_validated needs a strong, stable record to be
        preferred.  Returns the (possibly unchanged) maturity."""
        p = self.patterns[pattern_id]
        st = self.pattern_stats(pattern_id)
        cur = MATURITY.index(p.maturity)
        nxt = cur
        if p.maturity == "ephemeral" and st["accepted"] >= 1:
            nxt = cur + 1
        elif (p.maturity == "candidate" and st["trials"] >= min_trials
              and st["mean_quality"] >= good_quality
              and st["acceptance_rate"] >= 0.5):
            nxt = cur + 1
        elif (p.maturity == "experimentally_validated"
              and st["trials"] >= min_trials * 2
              and st["mean_quality"] >= good_quality + 0.1
              and st["acceptance_rate"] >= 0.7):
            nxt = cur + 1
        p.maturity = MATURITY[min(nxt, len(MATURITY) - 1)]
        return p.maturity

    def envelopes(self) -> list:
        """All tiers as searchable store records (definitions + patterns)."""
        return ([d.envelope() for d in self.definitions.values()]
                + [p.envelope() for p in self.patterns.values()])


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    bank = QuestionBank()
    d = QuestionDefinition("next_action",
                           "what is the single most valuable next action?",
                           domain="general", keywords=("what_is_next",))
    bank.add_definition(d)
    p = QuestionPattern("next_action.blueprint", "next_action",
                        "For {task}, outline every step, then name the most "
                        "discrete immediate action.", "decomposition")

    # 1. the four tiers are distinct and a pattern references its definition.
    bank.add_pattern(p)
    check("definition_pattern_instance_are_distinct_tiers",
          p.definition_id == d.definition_id and p.slots == ("task",)
          and "blueprint" in p.pattern_id,
          "a Pattern (how) references a Definition (what); slots parsed")

    # 2. rendering a pattern yields an Instance with a payload digest.
    inst = p.render(task="win the RSNA competition")
    check("rendering_yields_an_instance_with_a_payload_digest",
          isinstance(inst, QuestionInstance)
          and "win the RSNA" in inst.text and len(inst.payload_digest) == 16,
          "the exact task-specific question is addressed by its digest")

    # 3. a pattern references to an unknown definition are refused.
    bad = False
    try:
        bank.add_pattern(QuestionPattern("orphan", "nope", "{x}?", "verdict"))
    except ValueError:
        bad = True
    check("a_pattern_for_an_unknown_definition_is_refused", bad,
          "tiers are linked, not free-floating")

    # 4. MATURITY promotes only on outcomes, one tier at a time, never skipping.
    m0 = p.maturity                       # candidate
    # not enough trials yet -> stays candidate
    bank.record_outcome(QuestionOutcomeRecord(inst.instance_id, p.pattern_id,
                                              accepted=True, quality=0.8))
    stay = bank.promote(p.pattern_id)
    # add strong trials -> candidate -> experimentally_validated (one step)
    for _ in range(5):
        bank.record_outcome(QuestionOutcomeRecord(
            inst.instance_id, p.pattern_id, accepted=True, quality=0.8))
    step1 = bank.promote(p.pattern_id)
    check("maturity_promotes_only_on_outcomes_one_tier_at_a_time",
          m0 == "candidate" and stay == "candidate"
          and step1 == "experimentally_validated",
          "a thin record stays candidate; a strong record advances exactly one "
          "tier — never by assertion, never skipping")

    # 5. a weak record never promotes.
    bank2 = QuestionBank(); bank2.add_definition(d)
    pw = QuestionPattern("weak", "next_action", "{task}?", "verdict")
    bank2.add_pattern(pw)
    for _ in range(6):
        bank2.record_outcome(QuestionOutcomeRecord("i", "weak", accepted=False,
                                                   quality=0.2))
    check("a_weak_pattern_never_promotes",
          bank2.promote("weak") == "candidate",
          "rejected, low-quality outcomes keep a pattern where it is")

    # 6. tiers are searchable resources through the strict search DAG.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=bank.envelopes())
    store.enable_tier("experimental")
    hit = store.search("outline every step most discrete action",
                       kind="question")
    check("question_tiers_are_searchable_resources",
          hit["hits"] and any("qpat.next_action.blueprint" == h["record_id"]
                              for h in hit["hits"]),
          "definitions and patterns are findable via the one search DAG")

    # 7. closed vocabularies.
    bad2 = 0
    for fn in (lambda: QuestionPattern("x", "next_action", "{a}?", "vibes"),
               lambda: QuestionPattern("x", "next_action", "{a}?", "verdict",
                                       maturity="legendary")):
        try:
            fn()
        except ValueError:
            bad2 += 1
    check("answer_shape_and_maturity_are_closed", bad2 == 2,
          "the tier vocabularies are closed")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "question_bank_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
