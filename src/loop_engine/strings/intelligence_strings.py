"""Intelligence as organized strings — the unifying substrate.

Owner insight (2026-08-23): what if ALL the accumulated intelligence is just
organized STRINGS — strings for personas, prompt prefixes, lists, things to
consider, instructions, keywords — and the main loop composes, reorders, and
biases them into prompts?  Then intelligence is DATA, not code: adding a
capability is adding a string (no code); distilling is the model emitting a
string you store; the moat is the accumulated, outcome-weighted string bank.

This module is that substrate.  Every reasoning aid is an ``IntelligenceString``
with a KIND (persona, prompt_prefix, consideration, instruction, keyword,
list_item, analogy, warning, framing, prompt_suffix), a PRECEDENCE (where it
slots into the prompt — aligned with the 13-block ordering), tags + applicability
(so the loop retrieves the relevant ones), a MATURITY (a distilled string earns
trust by evidence), and provenance.  ``compose`` assembles the relevant strings
into a prompt fragment in precedence order; ``distill_string`` turns a model's
open-ended output into a stored, reusable string.

This unifies what were separate concepts — personas, prompt packs, question
prefixes, considerations, keyword packs — under one flexible, searchable,
composable, distillable thing.  Biases become *string hints* the loop can
reorder; the loop itself manages the ordering.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Sequence

# The kinds of intelligence-string, each with a default PRECEDENCE (lower =
# earlier in the prompt) aligned with the standard prompt-block order.
STRING_KINDS_PRECEDENCE = {
    "authority": 1,          # policy / boundaries (pinned top)
    "persona": 2,            # the role / reasoning perspective
    "framing": 3,            # how to frame the objective
    "prompt_prefix": 4,      # text placed before the question
    "consideration": 6,      # "things to consider" (with evidence)
    "warning": 7,            # a failure pattern to avoid
    "analogy": 8,            # a cross-domain lens
    "keyword": 9,            # domain vocabulary to use
    "list_item": 10,         # one item of a checklist / options
    "instruction": 11,       # how to answer / method
    "prompt_suffix": 12,     # text placed after (near the directive)
}
STRING_KINDS = tuple(STRING_KINDS_PRECEDENCE)
MATURITY = ("ephemeral", "candidate", "validated", "preferred")


def _digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


@dataclass
class IntelligenceString:
    """One unit of intelligence, as an organized string."""
    kind: str
    text: str
    tags: tuple = ()
    applicability: str = "any"
    maturity: str = "candidate"
    provenance: str = "hand_seed"
    precedence: int = 0              # 0 => use the kind's default precedence
    uses: int = 0

    def __post_init__(self):
        if self.kind not in STRING_KINDS:
            raise ValueError(f"kind must be one of {STRING_KINDS}")
        if self.maturity not in MATURITY:
            raise ValueError(f"maturity must be one of {MATURITY}")
        if not self.precedence:
            self.precedence = STRING_KINDS_PRECEDENCE[self.kind]

    @property
    def string_id(self) -> str:
        return f"{self.kind}.{_digest(self.text)}"

    def resource(self):
        """Emit the canonical Resource envelope — a string is a resource like any
        other (asset_class=string; maturity → the one lifecycle)."""
        from ..static_architecture.asset_lifecycle import Resource, normalize
        return Resource(asset_id=self.string_id, asset_class="string",
                        role=self.kind, content=self.text,
                        lifecycle=normalize("string_maturity", self.maturity),
                        provenance=self.provenance, tags=tuple(self.tags))

    def envelope(self):
        """The search projection — derived from the one Resource envelope, with
        the legacy record id / body / tags / tier preserved."""
        return self.resource().to_store_record(
            record_id=f"istr.{self.string_id}", kind="context",
            extra_body={"string_kind": self.kind, "text": self.text,
                        "applicability": self.applicability,
                        "precedence": self.precedence},
            extra_tags=("intelligence_string", self.kind),
            tier="core" if self.maturity in ("validated", "preferred")
            else "experimental")


class StringBank:
    """The organized string bank — searchable, composable, distillable.

    Starts EMPTY (the blank-slate experiment) and fills by distillation.  Reads
    are broad; the loop retrieves by tag/applicability match and composes."""

    def __init__(self):
        self._by_id: dict = {}

    def add(self, s: IntelligenceString) -> None:
        self._by_id[s.string_id] = s

    def all(self) -> list:
        return list(self._by_id.values())

    def by_kind(self, kind: str) -> list:
        return [s for s in self._by_id.values() if s.kind == kind]

    def relevant(self, tags: Sequence[str], *,
                 kinds: "Sequence[str] | None" = None) -> list:
        """Strings whose tags/applicability match the task's tags — the loop's
        retrieval.  Ordered by precedence, then maturity (preferred first),
        then more-used first."""
        want = {t.lower() for t in tags}
        hits = []
        for s in self._by_id.values():
            if kinds and s.kind not in kinds:
                continue
            tagset = {t.lower() for t in s.tags}
            if s.applicability == "any" or (tagset & want) \
                    or any(w in s.applicability.lower() for w in want):
                hits.append(s)
        hits.sort(key=lambda s: (s.precedence,
                                 -MATURITY.index(s.maturity), -s.uses))
        return hits

    def __len__(self) -> int:
        return len(self._by_id)


def compose(bank: StringBank, tags: Sequence[str], *,
            max_strings: int = 20, budget_chars: int = 4000) -> dict:
    """Compose the relevant intelligence strings into a prompt fragment, in
    precedence order.  Returns the assembled text plus which strings were used
    (for the record and for outcome attribution) — the loop reorders/biases by
    reordering this list, never by editing code."""
    chosen = bank.relevant(tags)[:max_strings]
    parts, used, chars = [], [], 0
    for s in chosen:
        line = s.text.strip()
        if not line:
            continue
        if chars + len(line) > budget_chars:
            break
        parts.append(line)
        used.append(s.string_id)
        s.uses += 1
        chars += len(line)
    return {"record_type": "composed_intelligence/v1",
            "text": "\n".join(parts), "used_string_ids": used,
            "n_available": len(bank), "n_used": len(used)}


def distill_string(text: str, kind: str, *, tags: Sequence[str] = (),
                   applicability: str = "any",
                   provenance: str = "llm_distilled") -> IntelligenceString:
    """Turn a model's open-ended output into a stored, reusable intelligence
    string.  It enters at 'candidate' maturity and earns trust by outcomes — the
    smart-over-time flywheel expressed as: model reasoning -> organized string."""
    return IntelligenceString(kind=kind, text=text.strip(), tags=tuple(tags),
                              applicability=applicability, maturity="candidate",
                              provenance=provenance)


def promote(s: IntelligenceString, *, accepted_uses: int) -> str:
    """Advance a string's maturity ONE tier on accepted outcomes — never by
    assertion.  candidate needs real accepted use; validated needs many."""
    cur = MATURITY.index(s.maturity)
    nxt = cur
    if s.maturity == "ephemeral" and accepted_uses >= 1:
        nxt = cur + 1
    elif s.maturity == "candidate" and accepted_uses >= 3:
        nxt = cur + 1
    elif s.maturity == "validated" and accepted_uses >= 10:
        nxt = cur + 1
    s.maturity = MATURITY[min(nxt, len(MATURITY) - 1)]
    return s.maturity


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    bank = StringBank()

    # 1. everything is a string with a kind; kinds map to prompt precedence.
    bank.add(IntelligenceString("persona",
             "You are a careful statistician who distrusts leaderboards.",
             tags=("tabular", "stats")))
    bank.add(IntelligenceString("consideration",
             "Consider leakage from post-outcome columns.",
             tags=("tabular", "leakage")))
    bank.add(IntelligenceString("keyword", "collinearity; mutual information",
             tags=("tabular",)))
    bank.add(IntelligenceString("instruction",
             "Answer as a JSON array of moves.", tags=("any",)))
    check("intelligence_is_organized_strings_with_kinds",
          len(bank) == 4 and all(isinstance(s, IntelligenceString)
                                 for s in bank.all())
          and bank.by_kind("persona")[0].precedence == 2,
          "personas / considerations / keywords / instructions are all strings "
          "with a kind + precedence")

    # 2. the loop RETRIEVES relevant strings by tag, ordered by precedence.
    rel = bank.relevant(("tabular", "stats"))
    kinds_in_order = [s.kind for s in rel]
    check("the_loop_retrieves_relevant_strings_in_precedence_order",
          kinds_in_order[0] == "persona"
          and kinds_in_order.index("consideration")
          < kinds_in_order.index("keyword"),
          f"persona (prec 2) before consideration (6) before keyword (9): "
          f"{kinds_in_order}")

    # 3. compose assembles them into a prompt fragment in order.
    out = compose(bank, ("tabular", "stats"))
    check("compose_assembles_strings_into_a_prompt_fragment",
          out["n_used"] >= 3
          and out["text"].index("careful statistician")
          < out["text"].index("leakage"),
          f"composed {out['n_used']} strings; persona text precedes the "
          f"consideration text")

    # 4. an irrelevant string is not retrieved.
    bank.add(IntelligenceString("persona", "You are a cardiologist.",
             tags=("cardiology",), applicability="heart disease"))
    rel2 = bank.relevant(("tabular",))
    check("irrelevant_strings_are_not_composed",
          not any("cardiologist" in s.text for s in rel2),
          "a cardiology persona is not retrieved for a tabular task")

    # 5. DISTILLATION: a model's open-ended output becomes a stored string.
    s = distill_string("Prefer dropping the higher-VIF feature when |r|>0.9.",
                       "consideration", tags=("tabular", "collinearity"))
    bank.add(s)
    check("model_output_distills_into_a_reusable_string",
          s.provenance == "llm_distilled" and s.maturity == "candidate"
          and bank.relevant(("collinearity",)),
          "an LLM answer becomes an organized, retrievable string — the flywheel")

    # 6. maturity promotes only on accepted outcomes, one tier at a time.
    m0 = s.maturity
    stay = promote(s, accepted_uses=1)              # candidate needs >=3
    step = promote(s, accepted_uses=3)
    check("string_maturity_promotes_only_on_outcomes",
          m0 == "candidate" and stay == "candidate"
          and step == "validated",
          "a distilled string earns trust by accepted use, not assertion")

    # 7. strings are searchable resources through the store DAG.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=[x.envelope() for x in bank.all()])
    store.enable_tier("experimental")
    hit = store.search("collinearity higher vif feature", kind="context")
    check("intelligence_strings_are_searchable_resources",
          hit["hits"] and any("istr." in h["record_id"] for h in hit["hits"]),
          "the string bank is findable through the one search DAG")

    # 8. closed vocabularies.
    bad = 0
    for fn in (lambda: IntelligenceString("vibes", "x"),
               lambda: IntelligenceString("persona", "x", maturity="legendary")):
        try:
            fn()
        except ValueError:
            bad += 1
    check("string_kinds_and_maturity_are_closed", bad == 2,
          "the kind and maturity vocabularies are closed")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "intelligence_strings_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
