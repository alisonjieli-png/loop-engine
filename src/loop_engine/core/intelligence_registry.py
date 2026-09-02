"""Intelligence registry — one standardized way to serve, version, track, and
manage every piece of intelligence, across a single Database/Runtime boundary.

Owner direction (2026-08-23): standardize intelligence into DATABASE intelligence
(standardized enough to live in the database) vs RUNTIME-generated intelligence
(real intel a run produced, but not yet standardized enough for the database).
Give one standardized way of serving, versioning, tracking, and managing string
and logic-node intelligence; everything else is processed via the standardized
loop.

Today the "how promoted / how trusted" idea is smeared across three vocabularies:
store_serve tier (core/experimental), intelligence_strings maturity
(ephemeral..preferred), and learning_bundle storage-stage + validation-status.
This module collapses them into ONE canonical boundary and a single managed
envelope:

  * DATABASE tier — standardized, versioned (semver + content digest), served,
    tracked, durable, cross-run.  Cannot be overwritten by a run.
  * RUNTIME tier — provisional, run/project-scoped, usable while visibly
    provisional, NOT served as database truth.

Promotion RUNTIME -> DATABASE is the candidate->truth boundary: evidence-gated,
never by assertion.  This is a management layer OVER store_serve (database ==
served core tier; runtime == experimental), not a fourth store — it standardizes
the vocabulary the loop already produces.  See [[intelligence_strings.py]],
[[learning_bundle.py]], [[harness-commodity-intelligence-is-the-moat]].
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Sequence

INTELLIGENCE_TIERS = ("runtime", "database")
# The kinds of intelligence the registry manages uniformly.
INTELLIGENCE_KINDS = ("string", "logic_node", "schema", "policy", "node",
                      "question", "practice", "failure_pattern", "metric",
                      "blueprint_fragment", "shortcut")
# The managed lifecycle — orthogonal to tier (a runtime item can be validated
# in-run but still not promoted to the database).
LIFECYCLE = ("generated", "staged", "validated", "served", "superseded",
             "retired")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def content_digest(kind: str, content: str, version: str) -> str:
    """The version fingerprint — changes if kind, content, or version changes."""
    return hashlib.sha256(f"{kind}\x00{content}\x00{version}"
                          .encode("utf-8")).hexdigest()[:16]


class PromotionRefused(RuntimeError):
    """Raised when runtime intelligence is promoted to the database without the
    evidence the boundary requires."""


@dataclass
class ManagedIntelligence:
    """The one standardized envelope for a piece of intelligence."""
    intel_id: str
    kind: str
    content: str
    tier: str = "runtime"
    version: str = "0.1.0"
    maturity: str = "candidate"
    lifecycle: str = "generated"
    provenance: str = "runtime"
    scope: str = "run"                 # run | project | org | core (widens on promote)
    lineage: tuple = ()
    supersedes: str = ""
    uses: int = 0
    digest: str = ""

    def __post_init__(self):
        if self.kind not in INTELLIGENCE_KINDS:
            raise ValueError(f"kind must be one of {INTELLIGENCE_KINDS}")
        if self.tier not in INTELLIGENCE_TIERS:
            raise ValueError(f"tier must be one of {INTELLIGENCE_TIERS}")
        if self.lifecycle not in LIFECYCLE:
            raise ValueError(f"lifecycle must be one of {LIFECYCLE}")
        if not _SEMVER.match(self.version):
            raise ValueError(f"version must be semver x.y.z, got {self.version!r}")
        self.digest = content_digest(self.kind, self.content, self.version)

    @property
    def served(self) -> bool:
        """Only database intelligence is served as durable truth."""
        return self.tier == "database" and self.lifecycle in ("validated",
                                                              "served")

    def bump(self, new_content: str, *, level: str = "patch") -> None:
        """Standardized versioning: new content -> new semver + new digest."""
        major, minor, patch = (int(x) for x in self.version.split("."))
        if level == "major":
            major, minor, patch = major + 1, 0, 0
        elif level == "minor":
            minor, patch = minor + 1, 0
        else:
            patch += 1
        self.content = new_content
        self.version = f"{major}.{minor}.{patch}"
        self.digest = content_digest(self.kind, self.content, self.version)


class IntelligenceRegistry:
    """Standardized serve / version / track / manage over the two tiers."""

    def __init__(self, items: "Sequence[ManagedIntelligence] | None" = None):
        self._by_id: dict = {}
        for it in (items or ()):
            self._by_id[it.intel_id] = it

    # --- register / track ---------------------------------------------------

    def register(self, item: ManagedIntelligence) -> ManagedIntelligence:
        self._by_id[item.intel_id] = item
        return item

    def track_use(self, intel_id: str) -> int:
        it = self._by_id[intel_id]
        it.uses += 1
        return it.uses

    def all(self) -> list:
        return list(self._by_id.values())

    def by_tier(self, tier: str) -> list:
        return [it for it in self._by_id.values() if it.tier == tier]

    # --- serve --------------------------------------------------------------

    def serve_set(self, *, include_runtime: bool = False) -> list:
        """What is served.  Database intelligence always; runtime only when a
        caller explicitly opts in (and it is served run-locally, provisional)."""
        out = [it for it in self._by_id.values() if it.served]
        if include_runtime:
            out += [it for it in self._by_id.values()
                    if it.tier == "runtime"]
        return out

    # --- the promotion boundary (evidence-gated) ---------------------------

    def promote(self, intel_id: str, *, evidence: Sequence,
                scope: str = "org", level: str = "minor") -> ManagedIntelligence:
        """Move runtime intelligence across the boundary into the database.
        Refused without evidence — the candidate->truth boundary is never crossed
        by assertion.  Promotion bumps the version (a new served version) and
        widens scope."""
        it = self._by_id[intel_id]
        if it.tier == "database":
            return it
        if not evidence:
            raise PromotionRefused(
                f"cannot promote {intel_id!r} to the database without evidence — "
                "runtime intelligence crosses to database truth only on accepted "
                "outcomes, never by assertion")
        it.tier = "database"
        it.lifecycle = "served"
        it.maturity = "validated" if it.maturity in ("ephemeral",
                                                      "candidate") else it.maturity
        it.scope = scope
        it.provenance = f"promoted; evidence={list(evidence)[:3]}"
        it.bump(it.content, level=level)
        return it

    def supersede(self, old_id: str, new_item: ManagedIntelligence
                  ) -> ManagedIntelligence:
        """Retire an item in favor of a new version — lineage preserved, never a
        silent overwrite."""
        old = self._by_id.get(old_id)
        if old is not None:
            old.lifecycle = "superseded"
        new_item.supersedes = old_id
        new_item.lineage = tuple(new_item.lineage) + ((old_id,) if old else ())
        return self.register(new_item)

    def retire(self, intel_id: str) -> None:
        self._by_id[intel_id].lifecycle = "retired"

    # --- serving via the one search DAG ------------------------------------

    def store_records(self, *, include_runtime: bool = True) -> list:
        """Project managed intelligence into store records: database -> core
        tier (served truth), runtime -> experimental (provisional)."""
        from ..core.store_serve import StoreRecord
        recs = []
        _kind_map = {"string": "context", "question": "question",
                     "schema": "strategy", "policy": "strategy",
                     "practice": "context", "failure_pattern": "context",
                     "metric": "context", "blueprint_fragment": "context"}
        for it in self._by_id.values():
            if it.tier == "runtime" and not include_runtime:
                continue
            if it.lifecycle in ("superseded", "retired"):
                continue
            recs.append(StoreRecord(
                record_id=f"intel.{it.intel_id}",
                kind=_kind_map.get(it.kind, "node"),
                title=it.content[:80],
                body={"kind": it.kind, "tier": it.tier, "version": it.version,
                      "digest": it.digest, "maturity": it.maturity,
                      "served": it.served, "provisional": it.tier == "runtime"},
                tags=("managed_intelligence", it.kind, it.tier),
                tier="core" if it.tier == "database" else "experimental"))
        return recs


# ---------------------------------------------------------------------------
# Standardizing bridges — classify existing intelligence into the two tiers,
# so this LAYERS over what the loop already produces rather than forking it.
# ---------------------------------------------------------------------------


def from_string(s, *, intel_id: str = "") -> ManagedIntelligence:
    """Standardize an IntelligenceString: its maturity decides the tier."""
    tier = "database" if s.maturity in ("validated", "preferred") else "runtime"
    return ManagedIntelligence(
        intel_id=intel_id or f"str.{s.string_id}", kind="string", content=s.text,
        tier=tier, maturity=s.maturity, provenance=s.provenance,
        lifecycle="validated" if tier == "database" else "generated",
        scope="core" if tier == "database" else "run")


def from_learning_candidate(c, *, intel_id: str = "") -> ManagedIntelligence:
    """Standardize a LearningCandidate: validation_status decides the tier.  A
    freshly captured candidate is runtime until validated."""
    kind_map = {"logic_candidate": "logic_node", "node_candidate": "node",
                "question_resource": "question", "best_practice": "practice",
                "failure_pattern": "failure_pattern",
                "metric_definition": "metric", "heuristic": "string",
                "blueprint_fragment": "blueprint_fragment"}
    tier = "database" if c.validation_status == "validated" else "runtime"
    from ..ontology.records import StableIdentityRequest, stable_content_id
    return ManagedIntelligence(
        intel_id=intel_id or stable_content_id(StableIdentityRequest(
            f"cand.{c.candidate_type}",
            (c.content, c.originating_run))),
        kind=kind_map.get(c.candidate_type, "string"), content=c.content,
        tier=tier, maturity=c.maturity, provenance=c.originating_run or "runtime",
        scope="run")


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    reg = IntelligenceRegistry()

    # 1. one standardized envelope; the two tiers are canonical.
    rt = reg.register(ManagedIntelligence(
        "h1", "string", "Prefer point-in-time features.", tier="runtime"))
    db = reg.register(ManagedIntelligence(
        "h2", "logic_node", "IF temporal THEN no random split.", tier="database",
        lifecycle="served", maturity="validated"))
    check("two_canonical_tiers_one_envelope",
          rt.tier == "runtime" and db.tier == "database"
          and set(INTELLIGENCE_TIERS) == {"runtime", "database"},
          "runtime vs database, one ManagedIntelligence envelope")

    # 2. only DATABASE intelligence is served as truth; runtime is provisional.
    served = reg.serve_set()
    check("only_database_intelligence_is_served",
          [it.intel_id for it in served] == ["h2"]
          and rt.served is False and db.served is True,
          "runtime intel is not served as database truth")
    check("runtime_can_be_served_run_locally_when_opted_in",
          len(reg.serve_set(include_runtime=True)) == 2,
          "opting in serves runtime provisionally, run-locally")

    # 3. standardized versioning: content change -> new semver + new digest.
    d0, v0 = rt.digest, rt.version
    rt.bump("Prefer point-in-time features; test for leakage.", level="minor")
    check("versioning_bumps_semver_and_digest",
          rt.version == "0.2.0" and rt.digest != d0 and v0 == "0.1.0",
          f"{v0}->{rt.version}, digest changed")

    # 4. THE BOUNDARY: promotion runtime->database is evidence-gated.
    refused = False
    try:
        reg.promote("h1", evidence=())
    except PromotionRefused:
        refused = True
    promoted = reg.promote("h1", evidence=["paired-trial: reuse arm accepted"])
    check("promotion_to_database_is_evidence_gated",
          refused and promoted.tier == "database" and promoted.served
          and promoted.scope == "org",
          "no evidence -> refused; with evidence -> crosses to database truth")

    # 5. tracking: uses accumulate.
    reg.track_use("h2")
    reg.track_use("h2")
    check("use_is_tracked", reg._by_id["h2"].uses == 2, "usage counted")

    # 6. supersede preserves lineage, never a silent overwrite.
    newv = ManagedIntelligence("h2b", "logic_node",
                               "IF temporal THEN time-ordered split only.",
                               tier="database", lifecycle="served",
                               maturity="validated")
    reg.supersede("h2", newv)
    check("supersede_preserves_lineage",
          reg._by_id["h2"].lifecycle == "superseded"
          and "h2" in newv.lineage,
          "the old version is retired with lineage, not overwritten")

    # 7. standardizing bridges: existing intelligence classifies into tiers by
    # its OWN evidence fields (this LAYERS over the loop, no fork).
    from ..strings.intelligence_strings import IntelligenceString
    from ..code_nodes.learning_bundle import LearningCandidate
    m_str = from_string(IntelligenceString("consideration", "x",
                                           maturity="preferred"))
    m_cand = from_learning_candidate(LearningCandidate(
        "logic_candidate", "IF a THEN b", validation_status="unvalidated"))
    check("bridges_standardize_existing_intelligence_by_evidence",
          m_str.tier == "database" and m_str.kind == "string"
          and m_cand.tier == "runtime" and m_cand.kind == "logic_node",
          "a preferred string -> database; an unvalidated candidate -> runtime")

    # 8. served through the one search DAG, tiers mapped to core/experimental.
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=reg.store_records())
    store.enable_tier("experimental")
    hit = store.search("time ordered split temporal no random")
    check("managed_intelligence_serves_through_the_one_search_dag",
          hit["hits"] and any("intel." in h["record_id"] for h in hit["hits"]),
          "database->core, runtime->experimental, one search over both")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "intelligence_registry_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
