"""Domain Support Packs — swappable domain bundles that never touch the kernel.

Owner spec (2026-08-23): a Domain Support Pack bundles everything a domain needs
so it can grow over time without changing the Practitioner Kernel — a cardiology
pack, an oil-and-gas pack, an insurance pack, a legal pack, or a proprietary
organizational pack.  It contains, per the spec:

  glossary/key phrases · accepted knowledge & evidence refs · preferred and
  prohibited SOURCE POLICIES · Question Definitions & Patterns · reasoning
  perspectives · context policies · prompt components & layout policies ·
  research recipes · evaluators & hard checks · relevant nodes/tools/graphs/
  packages · known failure patterns · utility & applicability history.

A pack is INSTALLED by contributing all of its parts to the resource store (as
standard records) and its questions to the QuestionBank — so the practitioner
finds them through the same strict search/serve DAG as everything else.  Packs
are tiered (core / experimental / gated) so a proprietary or trade-secret pack is
off by default and needs an explicit grant.  Installing or uninstalling a pack
changes only the resource banks, never the kernel — the whole point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from ..static_architecture.store_serve import StoreRecord, SolverStore, TIERS
from ..strings.question_bank import QuestionBank, QuestionDefinition, QuestionPattern

# The parts a pack may carry (each becomes searchable resources).
PACK_PARTS = ("glossary", "knowledge", "source_policies", "question_definitions",
              "question_patterns", "perspectives", "context_policies",
              "prompt_components", "layout_policies", "research_recipes",
              "evaluators", "nodes_tools_graphs", "failure_patterns")


@dataclass
class DomainSupportPack:
    """A swappable domain bundle.  Every field is a list of dicts/records; empty
    fields are fine — a pack grows over time."""
    domain: str
    version: int = 1
    tier: str = "core"
    glossary: list = field(default_factory=list)         # {term, definition}
    knowledge: list = field(default_factory=list)        # {claim, evidence_ref}
    source_policies: dict = field(default_factory=dict)  # {preferred, prohibited}
    question_definitions: list = field(default_factory=list)  # QuestionDefinition
    question_patterns: list = field(default_factory=list)     # QuestionPattern
    perspectives: list = field(default_factory=list)     # {name, description}
    context_policies: list = field(default_factory=list)
    prompt_components: list = field(default_factory=list)
    layout_policies: list = field(default_factory=list)
    research_recipes: list = field(default_factory=list)
    evaluators: list = field(default_factory=list)
    nodes_tools_graphs: list = field(default_factory=list)
    failure_patterns: list = field(default_factory=list)

    def __post_init__(self):
        if self.tier not in TIERS:
            raise ValueError(f"tier must be one of {TIERS}")

    def records(self) -> list:
        """Every part rendered as a standard searchable store record, carrying
        the pack's tier so a gated pack stays gated."""
        recs: list = []
        dom = self.domain

        def rec(rid, kind, title, body, tags):
            return StoreRecord(record_id=f"pack.{dom}.{rid}", kind=kind,
                               title=str(title)[:80], body=body,
                               tags=("domain_pack", dom) + tuple(tags),
                               tier=self.tier)
        for i, g in enumerate(self.glossary):
            recs.append(rec(f"glossary.{i}", "context", g.get("term", ""),
                            g, ("glossary", "key_phrase")))
        for i, k in enumerate(self.knowledge):
            recs.append(rec(f"knowledge.{i}", "knowledge",
                            k.get("claim", ""), k, ("knowledge",)))
        if self.source_policies:
            recs.append(rec("source_policies", "context", "source policies",
                            self.source_policies, ("source_policy",)))
        for i, p in enumerate(self.perspectives):
            recs.append(rec(f"perspective.{i}", "persona", p.get("name", ""),
                            p, ("perspective",)))
        for i, c in enumerate(self.context_policies):
            recs.append(rec(f"context_policy.{i}", "context",
                            c.get("name", ""), c, ("context_policy",)))
        for i, r in enumerate(self.research_recipes):
            recs.append(rec(f"research_recipe.{i}", "strategy",
                            r.get("name", ""), r, ("research_recipe",)))
        for i, e in enumerate(self.evaluators):
            recs.append(rec(f"evaluator.{i}", "node", e.get("name", ""), e,
                            ("evaluator", "hard_check")))
        for i, n in enumerate(self.nodes_tools_graphs):
            recs.append(rec(f"node.{i}", "node", n.get("name", ""), n,
                            ("node", "tool")))
        for i, f in enumerate(self.failure_patterns):
            recs.append(rec(f"failure.{i}", "context", f.get("name", ""), f,
                            ("failure_pattern",)))
        # question patterns/definitions are also records (via the bank envelopes)
        for qd in self.question_definitions:
            r = qd.envelope(); r.tier = self.tier
            r.tags = r.tags + ("domain_pack", dom); recs.append(r)
        for qp in self.question_patterns:
            r = qp.envelope()
            if self.tier != "core":
                r.tier = self.tier
            r.tags = r.tags + ("domain_pack", dom); recs.append(r)
        return recs

    def part_counts(self) -> dict:
        return {part: len(getattr(self, part))
                for part in PACK_PARTS if isinstance(getattr(self, part), list)}


def install_pack(pack: DomainSupportPack, store: SolverStore,
                 bank: "QuestionBank | None" = None) -> dict:
    """Install a pack by contributing its parts to the resource store (and its
    questions to the bank).  Changes ONLY the banks — never the kernel."""
    recs = pack.records()
    for r in recs:
        store.add(r)
    installed_q = 0
    if bank is not None:
        for qd in pack.question_definitions:
            bank.add_definition(qd)
        for qp in pack.question_patterns:
            try:
                bank.add_pattern(qp)
                installed_q += 1
            except ValueError:
                continue
    return {"record_type": "pack_install/v1", "domain": pack.domain,
            "tier": pack.tier, "records_installed": len(recs),
            "questions_installed": installed_q,
            "part_counts": pack.part_counts()}


def cardiology_pack() -> DomainSupportPack:
    """A worked example pack (the spec's heart-disease case) — small but real."""
    d = QuestionDefinition("cardio.risk_stratify",
                           "how should the cardiac risk factors be stratified?",
                           domain="cardiology",
                           keywords=("risk", "cardiac", "stratify"))
    p = QuestionPattern("cardio.risk_stratify.modifiable",
                        "cardio.risk_stratify",
                        "For {task}, stratify the risk factors by modifiability "
                        "and expected effect size.", "ranking")
    return DomainSupportPack(
        domain="cardiology", tier="core",
        glossary=[{"term": "ejection fraction",
                   "definition": "fraction of blood pumped per beat"},
                  {"term": "ST elevation",
                   "definition": "ECG sign of acute injury"}],
        source_policies={"preferred": ["peer-reviewed cardiology journals"],
                         "prohibited": ["unverified social media"]},
        question_definitions=[d], question_patterns=[p],
        perspectives=[{"name": "an interventional cardiologist",
                       "description": "cath-lab outcomes focus"},
                      {"name": "a bridge fatigue engineer",
                       "description": "diametric: load-cycle failure lens"}],
        evaluators=[{"name": "leakage_check",
                     "description": "labels must not leak from the report"}],
        failure_patterns=[{"name": "over-trusting a single imaging view"}])


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    pack = cardiology_pack()

    # 1. a pack bundles the spec's parts.
    counts = pack.part_counts()
    check("a_pack_bundles_the_domain_parts",
          counts["glossary"] == 2 and counts["question_patterns"] == 1
          and counts["perspectives"] == 2 and counts["evaluators"] == 1,
          f"parts: {[k for k,v in counts.items() if v]}")

    # 2. installing a pack contributes searchable records + bank questions,
    # and changes ONLY the banks.
    store = SolverStore()
    bank = QuestionBank()
    report = install_pack(pack, store, bank)
    check("installing_a_pack_contributes_records_and_questions",
          report["records_installed"] >= 6 and report["questions_installed"] == 1
          and len(store) == report["records_installed"],
          f"{report['records_installed']} records, "
          f"{report['questions_installed']} question(s) installed")

    # 3. the pack's resources are FOUND via the strict search DAG.
    hit = store.search("ejection fraction cardiac", kind="context")
    persona_hit = store.search("interventional cardiologist", kind="persona")
    check("pack_resources_are_findable_by_capability_search",
          hit["hits"] and persona_hit["hits"],
          "glossary + personas discovered like any other resource")

    # 4. a GATED (proprietary/trade-secret) pack is off by default and needs a
    # grant — installing it does not make it servable until enabled.
    secret = DomainSupportPack(domain="oil_gas", tier="gated",
                               glossary=[{"term": "mud weight",
                                          "definition": "drilling fluid density"}])
    store2 = SolverStore()
    install_pack(secret, store2)
    off = store2.search("mud weight drilling", kind="context")
    store2.enable_tier("gated", grant="org-license")
    on = store2.search("mud weight drilling", kind="context")
    check("a_gated_pack_is_off_by_default_and_needs_a_grant",
          not off["hits"] and on["hits"],
          "a trade-secret pack stays dark until an explicit grant enables it")

    # 5. the kernel is untouched — install/uninstall only changes the store.
    from ..loop.kernel import KERNEL_NODES
    before = tuple(KERNEL_NODES)
    install_pack(cardiology_pack(), SolverStore(), QuestionBank())
    check("installing_a_pack_never_changes_the_kernel",
          tuple(KERNEL_NODES) == before,
          "packs grow the banks; the kernel node set is invariant under install")

    # 6. an unknown tier is refused.
    bad = False
    try:
        DomainSupportPack(domain="x", tier="platinum")
    except ValueError:
        bad = True
    check("an_unknown_pack_tier_is_refused", bad, "tiers are closed")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "domain_pack_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
