"""Pack curation — research new knowledge into the packs, under review.

The packs are what make the system sharp about a field; keeping them current is
itself work a practitioner does — reading papers, scanning new libraries,
comparing to what already exists — and it is work the system should do for
itself.  This module is that loop: research findings become *candidate* pack
items, a council reviews them for quality / stability / fragility, and only the
ones that clear the gate are promoted into a curated pack that layers on top of
the seeded one.  A curated item earns its place; nothing enters the packs by
assertion, and the seeded packs are never mutated — the curated pack grows
append-only beside them.

This is how the system "continuously becomes as smart as the best experts": a
worker researches, proposes, the council reviews, and the accepted knowledge
starts driving future deliberation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from ..strings.packs import Pack, PackItem, PackRegistry
from ..strings.notes import council_review


@dataclass
class PackItemCandidate:
    """A proposed pack item mined from research — candidate until reviewed and
    promoted."""
    item: PackItem
    target_domain: str
    target_kind: str = "question"
    source: str = ""                    # research finding ref
    status: str = "candidate"           # candidate | reviewed | promoted | rejected
    review: dict = field(default_factory=dict)
    weight: float = 0.0

    def to_dict(self) -> dict:
        return {"item": self.item.to_dict(), "target_domain": self.target_domain,
                "target_kind": self.target_kind, "source": self.source,
                "status": self.status, "review": self.review,
                "weight": round(self.weight, 3)}


def curate_from_findings(findings: Sequence[Mapping[str, Any]], *,
                         target_domain: str, target_kind: str = "question"
                         ) -> list[PackItemCandidate]:
    """Turn research findings into candidate pack items.  Each finding supplies
    at least ``text`` (the question / checklist point / context note) and an
    optional ``facet``, ``measures``, and ``source``."""
    out: list[PackItemCandidate] = []
    for i, f in enumerate(findings):
        text = str(f.get("text", "")).strip()
        if not text:
            continue
        item = PackItem(
            id=f.get("id") or f"curated.{target_domain}.{i}", text=text,
            facet=str(f.get("facet", "")),
            measures=tuple(f.get("measures", ())))
        out.append(PackItemCandidate(
            item=item, target_domain=target_domain, target_kind=target_kind,
            source=str(f.get("source", ""))))
    return out


def review_candidate(candidate: PackItemCandidate,
                     reviewer_scores: Sequence[Mapping[str, float]]
                     ) -> PackItemCandidate:
    """Council-review a candidate: quality/stability/fragility → a weight."""
    agg = council_review(reviewer_scores)
    return replace(candidate, status="reviewed", review=agg,
                   weight=agg["weight"])


def promote_candidates(candidates: Sequence[PackItemCandidate],
                       registry: PackRegistry, *, min_quality: float = 0.6,
                       max_fragility: float = 0.4,
                       curated_specificity: int = 5) -> dict:
    """Promote reviewed candidates that clear the quality/fragility gate into a
    curated pack per (kind, domain), layering on top of the seeded packs.  The
    seeded packs are never touched; the curated pack grows append-only."""
    promoted: list[PackItemCandidate] = []
    rejected: list[dict] = []
    # Group passing items by (kind, domain).
    by_target: dict[tuple[str, str], list[PackItem]] = {}
    for cand in candidates:
        if cand.status != "reviewed":
            rejected.append({"item": cand.item.id, "reason": "not reviewed"})
            continue
        r = cand.review
        if r.get("quality", 0.0) < min_quality:
            rejected.append({"item": cand.item.id,
                             "reason": f"quality {r.get('quality')} below "
                             f"{min_quality}"})
            continue
        if r.get("fragility", 1.0) > max_fragility:
            rejected.append({"item": cand.item.id,
                             "reason": f"fragility {r.get('fragility')} above "
                             f"{max_fragility}"})
            continue
        by_target.setdefault((cand.target_kind, cand.target_domain), []).append(
            cand.item)
        promoted.append(cand)

    # Merge promoted items into (or create) the curated pack for each target.
    for (kind, domain), items in by_target.items():
        pack_id = f"pack.{kind}.{domain}.curated"
        existing = registry.get(pack_id)
        merged = (tuple(existing.items) if existing else ()) + tuple(items)
        # De-dup by text.
        seen: set[str] = set()
        deduped = []
        for it in merged:
            key = it.text.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
        version = (f"1.0.{len(deduped)}")
        registry.register(Pack(
            id=pack_id, kind=kind, domain=domain, version=version,
            items=tuple(deduped), keywords=(domain,),
            specificity=curated_specificity, provenance="curated"),
            replace=True)

    return {"record_type": "pack_curation/v1",
            "candidates": len(candidates), "promoted": len(promoted),
            "rejected": len(rejected), "rejected_detail": rejected,
            "curated_packs": [f"pack.{k}.{d}.curated" for (k, d) in by_target],
            "the_rule": ("research proposes, the council reviews, only gated "
                         "items are promoted into a curated pack; seeded packs "
                         "are never mutated and nothing enters by assertion")}


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    findings = [
        {"text": "Does the target exhibit hurdle/zero-inflation structure?",
         "facet": "target", "source": "paper://count-models-2019"},
        {"text": "Would a fold-safe hierarchical encoder reduce cardinality?",
         "facet": "encoding", "source": "pkg://category_encoders"},
        {"text": "Is this metric sensitive to calibration?",
         "facet": "metric", "source": "paper://calibration-2021"}]

    candidates = curate_from_findings(findings, target_domain="ml",
                                      target_kind="question")
    check("research_findings_become_candidate_pack_items",
          len(candidates) == 3
          and all(c.status == "candidate" for c in candidates)
          and candidates[0].item.text.startswith("Does the target"),
          "three research findings become three candidate question items, none "
          "yet in any pack — candidate until reviewed")

    # Review: two strong, one fragile.
    reviewed = [
        review_candidate(candidates[0],
                         [{"quality": 0.9, "stability": 0.9, "fragility": 0.1}]),
        review_candidate(candidates[1],
                         [{"quality": 0.85, "stability": 0.8, "fragility": 0.2}]),
        review_candidate(candidates[2],
                         [{"quality": 0.8, "stability": 0.4, "fragility": 0.7}])]
    check("candidates_are_council_reviewed_for_quality_and_fragility",
          all(c.status == "reviewed" for c in reviewed)
          and reviewed[0].weight > reviewed[2].weight,
          "each candidate is council-reviewed; the stable one earns a higher "
          "weight than the fragile one")

    reg = PackRegistry()
    outcome = promote_candidates(reviewed, reg)
    check("only_gated_items_are_promoted_into_a_curated_pack",
          outcome["promoted"] == 2 and outcome["rejected"] == 1
          and "fragility" in outcome["rejected_detail"][0]["reason"],
          "the two strong items are promoted; the fragile one (0.7 > 0.4 gate) "
          "is rejected — quality alone does not carry a fragile item in")

    # The promoted items now drive deliberation for a matching ML task.
    ml_items = reg.items_for("question",
                             {"task_family": "regression", "domain": "ml"})
    check("promoted_items_immediately_apply_to_matching_tasks",
          any("hurdle" in i.text for i in ml_items)
          and reg.get("pack.question.ml.curated") is not None,
          "the curated pack registers and its promoted questions immediately "
          "apply to a matching ML task — the system just got smarter about the "
          "field, under review")

    # A second curation round appends (never overwrites) to the curated pack.
    more = [review_candidate(
        curate_from_findings([{"text": "Are residuals heteroscedastic?",
                               "facet": "diagnostics"}], target_domain="ml")[0],
        [{"quality": 0.9, "stability": 0.9, "fragility": 0.1}])]
    promote_candidates(more, reg)
    curated = reg.get("pack.question.ml.curated")
    check("curation_appends_to_the_curated_pack",
          len(curated.items) == 3
          and any("heteroscedastic" in i.text for i in curated.items)
          and any("hurdle" in i.text for i in curated.items),
          "a second round appends the new item to the curated pack, keeping the "
          "earlier promoted items — the curated knowledge grows append-only")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "pack_curation_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
