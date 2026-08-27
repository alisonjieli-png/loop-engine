"""Housekeeping — the continuous-improvement practitioner, separate from solving.

Owner concept (2026-08-23): a housekeeping / continuous-improvement layer that is
SEPARATE from direct solutioning.  It runs on a trigger or a cron, reviews all our
runtimes, logs, and evidence, organizes and classifies them (Context Intelligence
vs code intelligence), mines them, and determines new code nodes, new text
intelligence, new logic, and new biases worth including.  It can also review a
customer's LEGACY codebases (e.g. a list of GitHub URLs) and either propose how
they can be improved / replaced with Loop Engine solutioning, or use them to generate
Loop Engine-first nodes and intelligence from code that already exists.

This is the **Continuous Improvement Plane** — one of two lanes of the SAME
practitioner loop (the other is direct solutioning).  Four JOB FAMILIES (families,
not primitives): ``runtime_housekeeping`` (clean/validate/organize/index — the
cheap deterministic layer), ``capability_mining`` (find repeated reasoning /
failures / searches worth reusing), ``capability_engineering`` (generate / test /
compare / promote / retire), and ``legacy_assimilation`` (customer repos → wrap /
adapt / compose / reimplement / replace / extract / retire).  Three COST TIERS keep
the LLM out of the cheap layer (housekeeping_scan → opportunity_mining →
capability_engineering), so a few SCORED opportunities reach an LLM, never millions
of raw records.  Runs start from one of four TRIGGER CLASSES (scheduled / event /
threshold / manual).

Discipline (non-negotiable, from the doctrine):

  * It PROPOSES, never promotes.  Everything it produces is a candidate at the
    RUNTIME tier; crossing to the database is the evidence-gated candidate→truth
    boundary owned by [[intelligence_registry.py]] — housekeeping cannot flip it.
  * It EXTRACTS legacy code body-free and proposes wrappers; it never executes
    unverified legacy code, and a generated node is candidate-until-verified.
  * A mined pattern is an OBSERVATION, not an accepted claim.  Recurrence and
    evidence are recorded; nothing is asserted as true.
  * It is a distinct PURPOSE, not a separate engine: it runs THROUGH the same
    ``run_kernel_passes`` loop, given a self-improvement objective + instructions,
    with the mining as the code node its act node calls (``self_improve`` is the
    same idea per cycle).  It improves the library the solving practitioner draws
    on — more code nodes (zero-token), better strings, sharper biases — it does not
    answer the customer's task itself.

Every candidate is classified STRING or CODE ([[asset_class.py]]) so the report
says exactly what text intelligence vs code intelligence it wants to add, and each
is a searchable runtime record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from ..core.asset_class import classify
from ..loop.kernel import (KernelRunRequest, ProblemSpec, ResultPacket,
                           default_impls, run_kernel_passes)

# What housekeeping can propose adding.
IMPROVEMENT_KINDS = ("code_node", "logic_rule", "intelligence_string", "bias",
                     "question", "failure_pattern", "research_pipeline")
# The asset kind each improvement maps to (for the String/Code classification).
_IMP_ASSET_KIND = {
    "code_node": "node", "logic_rule": "logic_rule",
    "research_pipeline": "task_graph",              # code
    "intelligence_string": "consideration", "bias": "consideration",
    "question": "question", "failure_pattern": "failure_pattern",  # strings
}
LEGACY_SOURCE_KINDS = ("github_url", "local_path", "package")

# The four JOB FAMILIES of the Continuous Improvement Plane (job families, not
# primitives) and the COST TIER each runs at (cheap-deterministic-first, so a few
# high-value opportunities reach an LLM, never millions of raw records).
JOB_FAMILIES = ("runtime_housekeeping", "capability_mining",
                "capability_engineering", "legacy_assimilation")
COST_TIERS = ("housekeeping_scan", "opportunity_mining",
              "capability_engineering")
JOB_TIER = {"runtime_housekeeping": "housekeeping_scan",
            "capability_mining": "opportunity_mining",
            "legacy_assimilation": "opportunity_mining",
            "capability_engineering": "capability_engineering"}

# The four trigger CLASSES (each is a String routed into a normal practitioner run).
TRIGGER_CLASSES = ("scheduled", "event", "threshold", "manual")

# For each legacy capability, one explicit modernization decision.
MODERNIZATION_DECISIONS = ("wrap", "adapt", "compose", "reimplement", "replace",
                           "extract_intelligence_only", "quarantine", "retire")

# Non-negotiable safeguards: what the improvement practitioner MAY and MUST NOT do.
IMPROVEMENT_MAY = ("observe", "analyze", "recommend", "generate_candidate",
                   "stage_candidate", "run_quarantined_test", "compare")
IMPROVEMENT_MUST_NOT = ("promote", "overwrite_accepted", "delete_evidence",
                        "modify_production", "execute_untrusted",
                        "infer_authorization", "count_duplicates_as_independent",
                        "rewrite_history")


class SafeguardError(RuntimeError):
    """Raised when the improvement practitioner attempts a forbidden action."""


def guard_improvement_action(action: str, *, logical_kind: str = "") -> None:
    """The safeguard gate: the improvement practitioner may observe, analyze,
    recommend, and stage — it may NOT promote its own candidate, overwrite
    accepted resources, delete evidence, or touch production.  A separate
    promotion authority owns consequential change.

    ``logical_kind`` binds the gate to Constitution Article 11: a loop
    declaring itself ``search_improvement`` is refused a consequential action
    on the strength of its OWN kind, not on the caller remembering to ask.
    Before this, the rule "a search loop may never accept its own candidate"
    was true only while every caller was careful."""
    from ..loop.recursive_loop import SELF_PROMOTION_FORBIDDEN
    if logical_kind in SELF_PROMOTION_FORBIDDEN and \
            action in IMPROVEMENT_MUST_NOT:
        raise SafeguardError(
            f"a {logical_kind!r} loop may not '{action}' — Article 11: it "
            "proposes, stages and compares, and never accepts its own "
            "candidate")
    if action in IMPROVEMENT_MUST_NOT:
        raise SafeguardError(
            f"the improvement practitioner may not '{action}' — it stages "
            "candidates; a separate promotion authority decides (evidence-gated)")
    if action not in IMPROVEMENT_MAY:
        raise SafeguardError(f"unknown improvement action {action!r}")


@dataclass(frozen=True)
class Schedule:
    """When an improvement run starts — one of the four trigger classes; ``spec``
    holds the cron expression / threshold.  Separate from any solving run."""
    trigger_class: str
    spec: str = ""

    def __post_init__(self):
        if self.trigger_class not in TRIGGER_CLASSES:
            raise ValueError(f"trigger_class must be one of {TRIGGER_CLASSES}")


@dataclass
class ImprovementCandidate:
    """One thing the improvement practitioner proposes — a candidate only, at the
    bottom of the maturity ladder (runtime_raw)."""
    kind: str
    proposal: str
    evidence: tuple = ()
    source: str = "runtime_mining"      # runtime_mining | legacy:<ref>
    frequency: int = 1
    confidence: float = 0.4
    job_family: str = "capability_mining"
    decision: str = ""                  # a MODERNIZATION_DECISION (legacy only)
    maturity: str = "runtime_raw"       # runtime_raw -> normalized_candidate -> …
    score: float = 0.0                  # opportunity score (set by rank)

    def __post_init__(self):
        if self.kind not in IMPROVEMENT_KINDS:
            raise ValueError(f"kind must be one of {IMPROVEMENT_KINDS}")
        if self.job_family not in JOB_FAMILIES:
            raise ValueError(f"job_family must be one of {JOB_FAMILIES}")
        if self.decision and self.decision not in MODERNIZATION_DECISIONS:
            raise ValueError(f"decision must be one of {MODERNIZATION_DECISIONS}")

    @property
    def cost_tier(self) -> str:
        return JOB_TIER[self.job_family]

    def resource(self):
        """Emit the canonical Resource — maturity → the one lifecycle."""
        from ..core.asset_lifecycle import Resource, normalize
        from ..ontology.records import StableIdentityRequest, stable_content_id
        return Resource(
            asset_id=stable_content_id(StableIdentityRequest(
                f"imp.{self.kind}", (self.proposal, self.source))),
            asset_class=self.asset_class, role=self.kind, content=self.proposal,
            lifecycle=normalize("housekeeping_maturity", self.maturity),
            provenance=self.source)

    @property
    def asset_class(self) -> str:
        """STRING intelligence or CODE intelligence — the binary."""
        return classify(_IMP_ASSET_KIND[self.kind])


@dataclass
class HousekeepingReport:
    trigger: str
    n_runs_reviewed: int
    candidates: tuple
    classification: dict                # {"string": [...], "code": [...]}
    through_loop: bool = False          # did it run through the practitioner loop?
    run: "dict | None" = None           # the practitioner run record
    note: str = ("all proposals are RUNTIME candidates; promotion to the database "
                 "is evidence-gated and not performed here")


# ---------------------------------------------------------------------------
# Mine our own runtimes / logs.
# ---------------------------------------------------------------------------


def trace_from_loop_ledger(events: "Sequence[dict]") -> dict:
    """Bridge a LOOP LEDGER (recursive_loop events) into the miner's trace
    vocabulary, so the improvement lane can mine real loop runs:

      * a ``run_step`` in hybrid / non_deterministic mode is BOTH a recurring
        model decision (distill it) and an LLM fallback for that step (no code
        node served it → build one);
      * ``fallback``, ``model_boundary_deferred``, and ``budget_stop`` events
        are failure signatures (the loop hit a wall worth remembering).
    """
    model_decisions, llm_fallbacks, failures = [], [], []
    for e in events:
        ev = e.get("event", "")
        if ev == "run_step" and e.get("mode") in ("hybrid",
                                                  "non_deterministic"):
            step = e.get("step", "?")
            model_decisions.append(f"model resolved step '{step}'")
            llm_fallbacks.append(f"no code node served step '{step}'")
        elif ev in ("fallback", "model_boundary_deferred"):
            failures.append(f"step '{e.get('step', '?')}' failed in "
                            f"{e.get('from_mode', '?')} mode")
        elif ev == "budget_stop":
            failures.append("model-call budget exhausted before completion")
    return {"failures": failures, "model_decisions": model_decisions,
            "llm_fallbacks": llm_fallbacks}


def mine_runtime(runs: "Sequence[dict]", *,
                 min_frequency: int = 2) -> list:
    """Review run traces and propose improvements from RECURRING patterns.

    Each trace may carry: ``failures`` (signatures), ``model_decisions`` (bounded
    decisions the model kept making → distill to code), ``llm_fallbacks`` (needs
    that fell back to the LLM because no code node served them → build one).  A
    pattern must recur at least ``min_frequency`` times to be proposed."""
    from collections import Counter
    fails, decisions, fallbacks = Counter(), Counter(), Counter()
    for r in runs:
        for f in r.get("failures", ()):
            fails[_sig(f)] += 1
        for dcn in r.get("model_decisions", ()):
            decisions[_sig(dcn)] += 1
        for nb in r.get("llm_fallbacks", ()):
            fallbacks[_sig(nb)] += 1

    out: list = []
    for sig, n in fails.items():
        if n >= min_frequency:
            out.append(ImprovementCandidate(
                "failure_pattern", f"recurring failure: {sig}",
                evidence=(f"seen {n} runs",), frequency=n,
                confidence=min(0.9, 0.4 + 0.1 * n)))
            out.append(ImprovementCandidate(
                "bias", f"bias to avoid the method that causes: {sig}",
                evidence=(f"seen {n} runs",), frequency=n, confidence=0.5))
    for sig, n in decisions.items():
        if n >= min_frequency:
            out.append(ImprovementCandidate(
                "logic_rule", f"distill the recurring decision '{sig}' into a "
                "deterministic rule (zero-token)", evidence=(f"seen {n} runs",),
                frequency=n, confidence=min(0.85, 0.4 + 0.12 * n)))
    for sig, n in fallbacks.items():
        if n >= min_frequency:
            out.append(ImprovementCandidate(
                "code_node", f"build a code node for '{sig}' — it repeatedly fell "
                "back to the LLM (tokens spent on a solved problem)",
                evidence=(f"{n} LLM fallbacks",), frequency=n,
                confidence=min(0.85, 0.4 + 0.12 * n)))
    return out


def _sig(x) -> str:
    """A coarse signature so near-identical entries group together (dropping the
    volatile 'pass N:' / 'error:' prefixes so the same failure across runs
    matches)."""
    import re
    s = str(x).strip().lower()
    s = re.sub(r"^pass\s+\d+\s*:\s*", "", s)
    s = re.sub(r"^(error|onfail::?)\s*:?\s*", "", s)
    return " ".join(s.split()[:8])


def classify_intelligence(candidates: "Sequence[ImprovementCandidate]") -> dict:
    """Split proposals into STRING intelligence vs CODE intelligence — the report
    says exactly what text vs code it wants to add."""
    string_, code = [], []
    for c in candidates:
        (string_ if c.asset_class == "string" else code).append(c)
    return {"string": string_, "code": code,
            "n_string": len(string_), "n_code": len(code)}


# How much a kind of improvement is worth per unit of frequency×confidence
# (a code node / logic rule saves the most because it removes token spend).
_KIND_WEIGHT = {"code_node": 1.5, "logic_rule": 1.4, "research_pipeline": 1.2,
                "failure_pattern": 1.1, "bias": 1.0, "question": 0.9,
                "intelligence_string": 0.9}


def score_opportunity(c: ImprovementCandidate) -> float:
    """Rank an opportunity by frequency × confidence × (worth of the kind) — the
    cheap deterministic filter that surfaces a few high-value opportunities before
    any expensive engineering."""
    return round(c.frequency * c.confidence * _KIND_WEIGHT.get(c.kind, 1.0), 3)


def rank_opportunities(cands: "Sequence[ImprovementCandidate]") -> list:
    """Score and sort candidates, highest opportunity first."""
    for c in cands:
        c.score = score_opportunity(c)
    return sorted(cands, key=lambda c: c.score, reverse=True)


@dataclass
class ModernizationBlueprint:
    """How one legacy capability should be brought into Loop Engine — one explicit
    decision, never a silent rewrite."""
    source_ref: str
    capability: str
    decision: str
    rationale: str = ""

    def __post_init__(self):
        if self.decision not in MODERNIZATION_DECISIONS:
            raise ValueError(f"decision must be one of {MODERNIZATION_DECISIONS}")


# ---------------------------------------------------------------------------
# Mine a customer's legacy codebase (GitHub URLs etc.) — body-free proposals.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegacyFunction:
    name: str
    purpose: str
    inputs: tuple = ()
    outputs: tuple = ()


def mine_legacy(source_ref: str, functions: "Sequence[LegacyFunction]", *,
                source_kind: str = "github_url",
                decision: str = "wrap") -> list:
    """Propose Loop Engine-first CODE NODE candidates from functions that already exist
    in a legacy codebase — body-free (a wrapper proposal), candidate-until-verified,
    never executed here.  Each carries one explicit modernization decision
    (default 'wrap'); a customer's GitHub URL becomes candidate nodes, not a
    silent rewrite."""
    if source_kind not in LEGACY_SOURCE_KINDS:
        raise ValueError(f"source_kind must be one of {LEGACY_SOURCE_KINDS}")
    if decision not in MODERNIZATION_DECISIONS:
        raise ValueError(f"decision must be one of {MODERNIZATION_DECISIONS}")
    out = []
    for fn in functions:
        out.append(ImprovementCandidate(
            "code_node",
            f"{decision} legacy '{fn.name}' ({fn.purpose}) as a Loop Engine code node: "
            f"inputs {list(fn.inputs)} → outputs {list(fn.outputs)}",
            evidence=(f"exists in {source_ref}",),
            source=f"legacy:{source_ref}", confidence=0.45,
            job_family="legacy_assimilation", decision=decision))
    return out


def modernization_blueprint(source_ref: str, fn: "LegacyFunction", *,
                            decision: str = "wrap",
                            rationale: str = "") -> ModernizationBlueprint:
    """The explicit per-capability plan (wrap / adapt / reimplement / replace /
    extract_intelligence_only / retire …) for a legacy capability."""
    return ModernizationBlueprint(source_ref, fn.name, decision,
                                  rationale or f"{decision} the existing "
                                  f"implementation of {fn.purpose}")


# ---------------------------------------------------------------------------
# The housekeeping run — a scheduled meta-practitioner.
# ---------------------------------------------------------------------------


def housekeeping_spec(runs: "Sequence[dict]", legacy: "Sequence[tuple]", *,
                      trigger_class: str = "scheduled",
                      min_frequency: int = 2) -> ProblemSpec:
    """The self-improvement OBJECTIVE + instructions the practitioner loop runs on
    — the same loop that solves, pointed at improving the library, not at a
    customer task.  The runs/legacy to mine and the discipline ride in the spec."""
    return ProblemSpec(
        objective="Continuous improvement: review our runtimes, logs, and legacy "
                  "code and propose reusable code nodes, strings, logic, and "
                  "biases worth adding to the library.",
        constraints=("propose candidates only — never promote to the database",
                     "classify each proposal as string or code intelligence",
                     "extract legacy code body-free; never execute it"),
        success_criteria=("improvements_proposed",),
        seed_facts={"_mode": "self_improvement", "_runs": list(runs),
                    "_legacy": list(legacy), "_trigger": trigger_class,
                    "_min_frequency": min_frequency})


def housekeeping_impls() -> dict:
    """Kernel impls for a self-improvement run: the loop stays the SAME; only the
    act node changes — it runs the mining code nodes over the runtimes + legacy
    carried in the spec and returns the improvement candidates."""
    base = default_impls()

    def act(state, plan):
        runs = state.facts.get("_runs", ())
        legacy = state.facts.get("_legacy", ())
        mf = state.facts.get("_min_frequency", 2)
        cands = list(mine_runtime(runs, min_frequency=mf))
        for entry in legacy:
            ref, fns = entry[0], entry[1]
            kind = entry[2] if len(entry) > 2 else "github_url"
            cands += mine_legacy(ref, fns, source_kind=kind)
        return [ResultPacket(objective=state.spec.objective, result=cands,
                             claims=("improvements_proposed",), confidence=0.85)]

    return {**base, "act": act}


def run_housekeeping(*, runs: "Sequence[dict]" = (),
                     legacy: "Sequence[tuple]" = (),
                     trigger_class: str = "scheduled",
                     min_frequency: int = 2) -> HousekeepingReport:
    """Run continuous improvement THROUGH the practitioner loop (not a separate
    engine): the same run_kernel_passes, given a self-improvement objective +
    instructions, with the mining as the code node its act node calls.  Ranks the
    opportunities and promotes nothing — every proposal is a runtime candidate."""
    if trigger_class not in TRIGGER_CLASSES:
        raise ValueError(f"trigger_class must be one of {TRIGGER_CLASSES}")
    spec = housekeeping_spec(runs, legacy, trigger_class=trigger_class,
                             min_frequency=min_frequency)
    run = run_kernel_passes(KernelRunRequest(
        spec, housekeeping_impls(), max_passes=6))
    seen, cands = set(), []
    for rec in run["records"]:
        for res in (rec.results or ()):
            if isinstance(getattr(res, "result", None), list):
                for c in res.result:
                    if isinstance(c, ImprovementCandidate) \
                            and (c.kind, c.proposal) not in seen:
                        seen.add((c.kind, c.proposal))
                        cands.append(c)
    cands = rank_opportunities(cands)          # highest-value opportunity first
    return HousekeepingReport(
        trigger=trigger_class, n_runs_reviewed=len(runs), candidates=tuple(cands),
        classification=classify_intelligence(cands), through_loop=True, run=run)


def candidate_records(report: HousekeepingReport) -> list:
    """Every proposal as a searchable RUNTIME (provisional) record — findable by
    the solving practitioner, never serving as truth until promoted."""
    from ..core.store_serve import StoreRecord
    recs = []
    for i, c in enumerate(report.candidates):
        recs.append(StoreRecord(
            record_id=f"improve.{i}",
            kind="node" if c.asset_class == "code" else "context",
            title=c.proposal[:80],
            body={"improvement_kind": c.kind, "asset_class": c.asset_class,
                  "proposal": c.proposal, "source": c.source,
                  "frequency": c.frequency, "confidence": c.confidence,
                  "provisional": True, "promotion": "evidence-gated, not here"},
            tags=("improvement_candidate", c.kind, c.asset_class, "housekeeping"),
            tier="experimental"))
    return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    runs = [
        {"failures": ["pass 3: random CV leaked the future"],
         "model_decisions": ["classify churn task type"],
         "llm_fallbacks": ["is this dataset imbalanced?"]},
        {"failures": ["pass 5: random CV leaked the future"],
         "model_decisions": ["classify churn task type"],
         "llm_fallbacks": ["is this dataset imbalanced?"]},
        {"failures": ["pass 2: out of memory"], "model_decisions": [],
         "llm_fallbacks": ["is this dataset imbalanced?"]},
    ]

    # 1. mining a recurring FAILURE proposes a failure_pattern + an avoid bias.
    mined = mine_runtime(runs)
    kinds = [c.kind for c in mined]
    check("recurring_failure_proposes_pattern_and_bias",
          "failure_pattern" in kinds and "bias" in kinds,
          f"proposed kinds: {sorted(set(kinds))}")

    # 2. a recurring MODEL DECISION proposes a logic rule (distill to zero-token).
    check("recurring_decision_proposes_a_logic_rule_to_distill",
          any(c.kind == "logic_rule" and "distill" in c.proposal for c in mined),
          "a decision the model kept making becomes a deterministic rule")

    # 3. a recurring LLM FALLBACK proposes building a CODE NODE (save tokens).
    check("recurring_llm_fallback_proposes_a_code_node",
          any(c.kind == "code_node" and "fell back to the LLM" in c.proposal
              for c in mined),
          "a solved problem repeatedly re-asked the LLM → build the node")

    # 4. classification splits STRING intelligence vs CODE intelligence.
    cls = classify_intelligence(mined)
    check("proposals_are_classified_string_vs_code",
          cls["n_string"] >= 1 and cls["n_code"] >= 1
          and all(c.asset_class == "code" for c in cls["code"])
          and all(c.asset_class == "string" for c in cls["string"]),
          f"{cls['n_string']} string / {cls['n_code']} code proposals")

    # 5. LEGACY mining proposes Loop Engine-first CODE NODE candidates (body-free).
    leg = mine_legacy("github.com/acme/etl",
                      [LegacyFunction("clean_dates", "normalize date columns",
                                      ("df",), ("df",)),
                       LegacyFunction("dedupe", "drop duplicate rows",
                                      ("df",), ("df",))])
    check("legacy_code_becomes_loop_first_node_candidates",
          len(leg) == 2 and all(c.kind == "code_node"
                                and c.source.startswith("legacy:") for c in leg),
          "existing functions → wrapped Loop Engine code-node proposals, body-free")

    # 6. it runs THROUGH the practitioner loop (not a separate engine) with a
    # self-improvement objective, and everything it produces is a CANDIDATE.
    report = run_housekeeping(
        runs=runs, legacy=[("github.com/acme/etl",
                            [LegacyFunction("clean_dates", "normalize dates")])],
        trigger_class="scheduled")
    check("housekeeping_runs_through_the_practitioner_loop",
          report.through_loop and report.run is not None
          and report.run["passes"] >= 1
          and report.run["facts"].get("_mode") == "self_improvement",
          "same run_kernel_passes, self-improvement objective + instructions")
    check("housekeeping_promotes_nothing",
          report.candidates and "evidence-gated" in report.note
          and all(isinstance(c, ImprovementCandidate)
                  for c in report.candidates),
          "runtime candidates only; promotion is the evidence-gated boundary")

    # 7. one of the four trigger CLASSES (scheduled/event/threshold/manual),
    # separate from solving.
    sch = Schedule("scheduled", spec="0 3 * * *")
    bad = False
    try:
        Schedule("whenever")
    except ValueError:
        bad = True
    check("improvement_runs_on_one_of_four_trigger_classes",
          sch.trigger_class == "scheduled" and report.trigger == "scheduled"
          and set(TRIGGER_CLASSES) == {"scheduled", "event", "threshold", "manual"}
          and bad,
          "scheduled / event / threshold / manual; a distinct purpose from solving")

    # 8. proposals are searchable RUNTIME records (findable, provisional).
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=candidate_records(report))
    store.enable_tier("experimental")
    hit = store.search("build a code node imbalanced dataset fell back to llm")
    check("improvement_candidates_are_searchable_and_provisional",
          hit["hits"] and any("improve." in h["record_id"] for h in hit["hits"]),
          "the solving practitioner can find them; they never serve as truth")

    # 9. OPPORTUNITY SCORING ranks high-frequency code-node builds above a
    # low-value string tweak (cheap deterministic filter before engineering).
    ranked = rank_opportunities(list(mined))
    top = ranked[0]
    check("opportunities_are_scored_and_ranked",
          top.score > 0 and ranked == sorted(ranked, key=lambda c: -c.score)
          and top.kind in ("code_node", "logic_rule", "failure_pattern"),
          f"top opportunity: {top.kind} (score {top.score})")

    # 10. LEGACY carries an explicit MODERNIZATION DECISION + a blueprint; the
    # job family and cost tier are set.
    leg2 = mine_legacy("github.com/acme/etl",
                       [LegacyFunction("score_risk", "score credit risk")],
                       decision="reimplement")
    bp = modernization_blueprint("github.com/acme/etl",
                                 LegacyFunction("score_risk", "score credit risk"),
                                 decision="reimplement")
    check("legacy_carries_an_explicit_modernization_decision",
          leg2[0].decision == "reimplement"
          and leg2[0].job_family == "legacy_assimilation"
          and leg2[0].cost_tier == "opportunity_mining"
          and bp.decision == "reimplement",
          "wrap / adapt / reimplement / replace / … — never a silent rewrite")

    # 11. cost tiers keep the LLM out of the cheap layer: housekeeping mining is
    # opportunity_mining; engineering is capability_engineering.
    check("cost_tiers_gate_expensive_work",
          JOB_TIER["capability_mining"] == "opportunity_mining"
          and JOB_TIER["capability_engineering"] == "capability_engineering"
          and JOB_TIER["runtime_housekeeping"] == "housekeeping_scan",
          "cheap deterministic scan first; the LLM only for high-value candidates")

    # 12. THE SAFEGUARD: the improvement practitioner may stage, never promote.
    may = True
    try:
        guard_improvement_action("stage_candidate")
    except SafeguardError:
        may = False
    forbidden = False
    try:
        guard_improvement_action("promote")
    except SafeguardError:
        forbidden = True
    check("safeguard_forbids_self_promotion",
          may and forbidden,
          "may observe/analyze/stage; must NOT promote/overwrite/delete evidence")

    # 13. the LOOP-LEDGER BRIDGE: real recursive_loop ledgers become minable
    # traces — a step that repeatedly escalated to the model across runs
    # yields a code-node build proposal (the distillation flywheel's intake).
    ledger_a = [{"event": "run_step", "step": "research", "mode": "hybrid",
                 "loop_id": "loop1"},
                {"event": "run_step", "step": "act", "mode": "deterministic",
                 "loop_id": "loop1"}]
    ledger_b = [{"event": "run_step", "step": "research",
                 "mode": "non_deterministic", "loop_id": "loop2"},
                {"event": "model_boundary_deferred", "step": "act",
                 "from_mode": "hybrid", "to_mode": "non_deterministic"}]
    mined13 = mine_runtime([trace_from_loop_ledger(ledger_a),
                            trace_from_loop_ledger(ledger_b)])
    kinds13 = {(c.kind, c.proposal.split("'")[1] if "'" in c.proposal else "")
               for c in mined13}
    check("loop_ledgers_are_minable_and_yield_code_node_proposals",
          any(c.kind == "code_node" and "research" in c.proposal
              for c in mined13)
          and any(c.kind == "logic_rule" for c in mined13),
          f"{len(mined13)} candidates from 2 real-shaped ledgers: {kinds13}")

    # ARTICLE 11 BOUND TO THE GATE: a loop declaring itself
    # search_improvement is refused a consequential action on the strength of
    # its OWN kind.  Before this, "a search loop may never accept its own
    # candidate" held only while every caller remembered to check.
    from ..loop.recursive_loop import LoopConfig, SELF_PROMOTION_FORBIDDEN
    kind_refused = generic_refused = staging_allowed = False
    try:
        guard_improvement_action("promote", logical_kind="search_improvement")
    except SafeguardError as e:
        kind_refused = "Article 11" in str(e)
    try:
        guard_improvement_action("promote")
    except SafeguardError:
        generic_refused = True
    try:                                  # it may still do its actual job
        guard_improvement_action("stage_candidate",
                                 logical_kind="search_improvement")
        staging_allowed = True
    except SafeguardError:
        pass
    check("a_search_improvement_loop_cannot_promote_its_own_candidate",
          kind_refused and generic_refused and staging_allowed
          and SELF_PROMOTION_FORBIDDEN == ("search_improvement",)
          and LoopConfig(logical_kind="search_improvement").logical_kind
          == "search_improvement",
          "kind-specific refusal on promote; staging still permitted")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "housekeeping_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
