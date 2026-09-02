"""Epistemic state — claims, unknowns, contradictions, and knowledge deltas.

"What do I presently know?" is not a prompt string; it is a structured epistemic
state (v3 Part II).  A fact is a **Claim** carrying its status and provenance, not
a bare string.  What is missing is a first-class **Unknown**.  Incompatible
claims are a preserved **Contradiction**, never a silent overwrite.  And the loop
never edits the state in place — an observation produces an append-only
**KnowledgeDelta**.

This is the substrate the resolvers read: a rule can branch on whether the
"split is leakage-free" claim is VERIFIED versus merely ASSUMED; a decision-need
detector can turn an unresolved Unknown or a material Contradiction into the next
thing to decide.  Confidence and status are kept separate: a high-confidence
INFERRED claim is still inferred, and a DISPUTED official claim is still evidence
with a dispute attached, not deleted data.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# A claim's epistemic status (v3 §4.3).  Distinct from confidence.
CLAIM_STATUSES = ("observed", "inferred", "assumed", "proposed", "supported",
                  "disputed", "refuted", "superseded", "unknown", "verified")

# Statuses that count as knowable ground the reflexes may rely on.
GROUND_STATUSES = frozenset({"observed", "verified", "supported"})


@dataclass(frozen=True)
class Claim:
    """A typed statement with provenance, status, and confidence."""
    id: str
    statement: str
    status: str = "observed"
    confidence: float = 1.0
    source_refs: tuple[str, ...] = ()
    method_ref: str = ""
    supersedes: str = ""

    def __post_init__(self) -> None:
        if self.status not in CLAIM_STATUSES:
            raise ValueError(f"unknown claim status {self.status!r}; expected "
                             f"one of {CLAIM_STATUSES}")

    def is_ground(self) -> bool:
        """True if the claim is settled enough to build on (observed / verified
        / supported).  Assumed, inferred, disputed, proposed are NOT ground."""
        return self.status in GROUND_STATUSES

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in asdict(self).items()}


@dataclass(frozen=True)
class Unknown:
    """A named missing fact or unresolved variable — a first-class object,
    because an expert progresses by naming what is not yet known (v3 §4.4)."""
    id: str
    question: str
    why_it_matters: str = ""
    affected_decisions: tuple[str, ...] = ()
    resolution_methods: tuple[str, ...] = ()
    expected_value: float = 0.0        # value of resolving it, 0..1
    has_conservative_default: bool = False
    ignorable_when: str = ""

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in asdict(self).items()}


@dataclass(frozen=True)
class Contradiction:
    """Incompatible claims kept simultaneously represented, never overwritten
    (v3 §4.5).  A contradiction can itself become the next decision focus."""
    id: str
    claim_ids: tuple[str, ...]
    conflict_type: str = ""
    materiality: float = 0.0           # how much it matters, 0..1
    discriminating_tests: tuple[str, ...] = ()
    resolution_status: str = "open"    # open | resolved | quarantined

    def to_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v)
                for k, v in asdict(self).items()}


@dataclass
class EpistemicState:
    """The structured 'what I know': claims by id, unknowns, contradictions."""
    claims: dict = field(default_factory=dict)          # id -> Claim
    unknowns: dict = field(default_factory=dict)        # id -> Unknown
    contradictions: dict = field(default_factory=dict)  # id -> Contradiction

    def add_claim(self, claim: Claim) -> None:
        # A claim that supersedes another marks the prior superseded, never
        # deletes it — history is preserved.
        if claim.supersedes and claim.supersedes in self.claims:
            prior = self.claims[claim.supersedes]
            self.claims[prior.id] = Claim(
                id=prior.id, statement=prior.statement, status="superseded",
                confidence=prior.confidence, source_refs=prior.source_refs,
                method_ref=prior.method_ref, supersedes=prior.supersedes)
        self.claims[claim.id] = claim

    def add_unknown(self, unknown: Unknown) -> None:
        self.unknowns[unknown.id] = unknown

    def resolve_unknown(self, unknown_id: str) -> None:
        self.unknowns.pop(unknown_id, None)

    def add_contradiction(self, contradiction: Contradiction) -> None:
        self.contradictions[contradiction.id] = contradiction

    def claims_by_status(self, status: str) -> list[Claim]:
        return [c for c in self.claims.values() if c.status == status]

    def open_unknowns(self) -> list[Unknown]:
        return list(self.unknowns.values())

    def open_contradictions(self) -> list[Contradiction]:
        return [c for c in self.contradictions.values()
                if c.resolution_status == "open"]

    def ground_facts(self) -> dict:
        """Project the GROUND claims into a facts dict the reflex regimes can
        read — only observed/verified/supported claims become facts an if-then
        rule may build on.  Assumed/inferred/disputed claims are deliberately
        excluded, so a rule never treats an assumption as established."""
        facts: dict[str, Any] = {}
        for claim in self.claims.values():
            if claim.is_ground():
                # A claim id doubles as a fact key when it is a simple flag.
                facts[claim.id] = True
        return facts

    def to_dict(self) -> dict:
        return {"record_type": "epistemic_state/v1",
                "claims": {k: v.to_dict() for k, v in self.claims.items()},
                "unknowns": {k: v.to_dict() for k, v in self.unknowns.items()},
                "contradictions": {k: v.to_dict()
                                   for k, v in self.contradictions.items()},
                "counts": {"claims": len(self.claims),
                           "unknowns": len(self.unknowns),
                           "open_contradictions": len(self.open_contradictions())}}


@dataclass(frozen=True)
class KnowledgeDelta:
    """The append-only update an observation produces — it never rewrites the
    prior state (v3 §20 KnowledgeDelta)."""
    added_claims: tuple[Claim, ...] = ()
    added_unknowns: tuple[Unknown, ...] = ()
    added_contradictions: tuple[Contradiction, ...] = ()
    resolved_unknowns: tuple[str, ...] = ()
    detail: str = ""

    def apply_to(self, state: EpistemicState) -> EpistemicState:
        """Return a NEW state with the delta applied (the prior state is left
        intact; supersession marks, never deletes)."""
        new = EpistemicState(
            claims=dict(state.claims), unknowns=dict(state.unknowns),
            contradictions=dict(state.contradictions))
        for claim in self.added_claims:
            new.add_claim(claim)
        for unknown in self.added_unknowns:
            new.add_unknown(unknown)
        for contradiction in self.added_contradictions:
            new.add_contradiction(contradiction)
        for uid in self.resolved_unknowns:
            new.resolve_unknown(uid)
        return new
