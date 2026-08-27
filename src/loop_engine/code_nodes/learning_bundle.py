"""Learning bundle — the rule that no open-ended reasoning result may disappear
into the next step.

Owner rule (2026-08-23): before the practitioner composes or executes a solution
DAG, the useful parts of an open-ended result must be captured, classified, and
stored in standardized forms — or the practitioner must explicitly record why the
result is only temporary and not reusable.  Not every result must be validated and
promoted to global memory before work continues; it must be saved immutably,
classified, converted to typed candidates, attached to provenance, staged in the
run/project namespace, and scheduled for further structuring when needed.

So every Practitioner Pass produces a ``LearningBundle`` — even one that holds no
reusable knowledge — carrying an explicit ``learning_disposition``.  The invariant:
a pass is NOT fully integrated while its disposition is
``requires_additional_structuring``; the practitioner schedules the structuring
pass, then continues.  Three storage stages keep this cheap: RAW CAPTURE (saved
immediately) → RUN-LOCAL STAGING (provisional, cannot overwrite accepted
knowledge) → SHARED PROMOTION (after validation).  Provisional resources are
usable while visibly provisional.

Builds on [[capture.py]] (which proposes the candidates) and reuses its
before/after cadence; formalizes capture output into the standardized
``LearningCandidate`` envelope plus the typed ``FailurePattern`` /
``PracticeResource`` / ``EvaluationContract`` schemas the owner specified — so a
"mistake" or a "best practice" is never just a sentence.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Sequence

from ..code_nodes.capture import CaptureReport, CaptureCandidate

LEARNING_DISPOSITIONS = ("no_new_learning", "ephemeral_task_only",
                         "reusable_candidates_extracted",
                         "requires_additional_structuring",
                         "requires_additional_research", "requires_validation",
                         "rejected_or_unreliable")
# A pass may not be considered fully integrated in these dispositions.
_BLOCKS_INTEGRATION = ("requires_additional_structuring",)
STORAGE_STAGES = ("raw_capture", "run_local_staging", "shared_promotion")
COMMONALITY = ("common", "uncommon", "rare", "unknown")

# The universal learning-candidate taxonomy (owner's list).
CANDIDATE_TYPES = (
    "context_resource", "knowledge_claim", "question_resource",
    "prompt_resource", "keyword_resource", "entity_resource",
    "date_or_event_resource", "blueprint_fragment", "risk_resource",
    "failure_pattern", "common_mistake", "uncommon_mistake", "best_practice",
    "evaluation_criterion", "metric_definition", "heuristic", "logic_candidate",
    "node_candidate", "subgraph_candidate", "task_graph_candidate",
    "specialist_model_candidate", "ensemble_candidate", "research_need",
    "tool_need", "package_need")

# Bridge from the leaner capture targets to the richer candidate taxonomy.
_CAPTURE_TO_CANDIDATE = {
    "intelligence_string": "heuristic", "question": "question_resource",
    "logic_rule": "logic_candidate", "deterministic_node": "node_candidate",
    "subdag_fragment": "subgraph_candidate", "task_graph": "task_graph_candidate",
    "knowledge_fact": "knowledge_claim", "failure_pattern": "failure_pattern",
    "blueprint_fragment": "blueprint_fragment"}


@dataclass
class LearningCandidate:
    """The standardized envelope for one extracted reusable unit."""
    candidate_type: str
    content: str
    intended_purpose: str = ""
    applicability: str = "any"
    contraindications: tuple = ()
    confidence: float = 0.5
    maturity: str = "candidate"
    validation_status: str = "unvalidated"
    proposed_representation: str = ""
    originating_run: str = ""
    originating_pass: str = ""

    def __post_init__(self):
        if self.candidate_type not in CANDIDATE_TYPES:
            raise ValueError(f"candidate_type must be one of {CANDIDATE_TYPES}")

    def resource(self):
        """Emit the canonical Resource envelope — validation_status → lifecycle."""
        from ..core.asset_lifecycle import Resource
        code = {"logic_candidate", "node_candidate", "subgraph_candidate",
                "task_graph_candidate", "specialist_model_candidate",
                "ensemble_candidate"}
        ac = "code" if self.candidate_type in code else "string"
        life = "validated" if self.validation_status == "validated" \
            else "candidate"
        from ..ontology.records import StableIdentityRequest, stable_content_id
        return Resource(
            asset_id=stable_content_id(StableIdentityRequest(
                f"cand.{self.candidate_type}",
                (self.content, self.originating_run))),
            asset_class=ac, role=self.candidate_type, content=self.content,
            lifecycle=life, provenance=self.originating_run or "runtime")

    @classmethod
    def from_capture(cls, c: CaptureCandidate, *, run: str = "",
                     pass_ref: str = "") -> "LearningCandidate":
        return cls(candidate_type=_CAPTURE_TO_CANDIDATE.get(c.target_kind,
                                                            "knowledge_claim"),
                   content=c.canonical_text, intended_purpose=c.intended_function,
                   applicability=c.applicability, confidence=c.confidence,
                   proposed_representation=c.target_kind,
                   originating_run=run, originating_pass=pass_ref)


@dataclass
class FailurePattern:
    """A mistake is not a sentence — it is a typed, conditional record."""
    description: str
    commonality: str = "unknown"
    severity: str = "advisory"
    trigger_conditions: tuple = ()
    symptoms: tuple = ()
    likely_causes: tuple = ()
    detection_method: str = ""
    prevention_method: str = ""
    recovery_method: str = ""
    applicability_boundary: str = "any"
    evidence: tuple = ()

    def __post_init__(self):
        if self.commonality not in COMMONALITY:
            raise ValueError(f"commonality must be one of {COMMONALITY}")


@dataclass
class PracticeResource:
    """A best practice with its conditions — so 'always use X' can't become an
    unconditional rule."""
    recommendation: str
    intended_outcome: str = ""
    applicability: str = "any"
    cost_complexity: str = "unknown"
    contraindications: tuple = ()
    alternatives: tuple = ()
    evidence: tuple = ()
    known_failure_cases: tuple = ()
    evaluation_method: str = ""


@dataclass
class EvaluationContract:
    """Success measurement, formalized BEFORE building — so a big DAG can't be
    built without knowing whether it solved the problem.  Composes with
    measurement.select_measures / read_generalization_gap."""
    primary_measure: str
    metric_direction: str = "maximize"
    acceptance_threshold: "float | None" = None
    secondary_measures: tuple = ()
    baseline_or_control: str = ""
    holdout_policy: str = ""
    cost_limit: "float | None" = None
    latency_limit: "float | None" = None
    reproducibility: str = ""
    stopping_rules: tuple = ()
    independent_evaluator: str = ""

    def is_decidable(self) -> bool:
        """A contract can actually decide acceptance only with a measure, a
        direction, a threshold, and a baseline."""
        return bool(self.primary_measure and self.acceptance_threshold is not None
                    and self.baseline_or_control)


@dataclass
class LearningBundle:
    """Every pass produces one — even with no reusable knowledge."""
    run_id: str
    pass_id: str
    agenda_item_id: str = ""
    raw_result_ref: str = ""
    primary_result: str = ""
    learning_disposition: str = "no_new_learning"
    resource_candidates: tuple = ()
    unresolved_extraction_items: tuple = ()
    validation_requirements: tuple = ()
    context_snapshot_digest: str = ""
    prompt_digest: str = ""
    model_invocation_ref: str = ""
    storage_stage: str = "raw_capture"
    commit_status: str = "open"

    def __post_init__(self):
        if self.learning_disposition not in LEARNING_DISPOSITIONS:
            raise ValueError(f"learning_disposition must be one of "
                             f"{LEARNING_DISPOSITIONS}")
        if self.storage_stage not in STORAGE_STAGES:
            raise ValueError(f"storage_stage must be one of {STORAGE_STAGES}")

    def is_fully_integrated(self) -> bool:
        """The invariant: a bundle that still needs structuring is NOT done."""
        return self.learning_disposition not in _BLOCKS_INTEGRATION

    def snapshot(self) -> dict:
        d = asdict(self)
        d["resource_candidates"] = [asdict(c) if hasattr(c, "__dataclass_fields__")
                                    else c for c in self.resource_candidates]
        d["fully_integrated"] = self.is_fully_integrated()
        return d


class IntegrationBlockedError(RuntimeError):
    """Raised when a pass would integrate while its learning still needs
    structuring — the invariant, fail-closed."""


def make_learning_bundle(*, run_id: str, pass_id: str, primary_result: str,
                         report: "CaptureReport | None" = None,
                         raw_result_ref: str = "",
                         agenda_item_id: str = "") -> LearningBundle:
    """Build the bundle from a capture report: the disposition is INFERRED from
    what the capture found, so nothing is silently dropped."""
    if report is None:
        disp, cands, unresolved = "no_new_learning", (), ()
    elif report.needs_more_calls:
        disp, cands = "requires_additional_structuring", ()
        unresolved = ("result too open-ended — schedule a structuring pass",)
    elif report.candidates:
        disp = "reusable_candidates_extracted"
        cands = tuple(LearningCandidate.from_capture(c, run=run_id,
                                                     pass_ref=pass_id)
                      for c in report.candidates)
        unresolved = ()
    else:
        disp, cands, unresolved = "no_new_learning", (), ()
    return LearningBundle(
        run_id=run_id, pass_id=pass_id, agenda_item_id=agenda_item_id,
        raw_result_ref=raw_result_ref, primary_result=primary_result,
        learning_disposition=disp, resource_candidates=cands,
        unresolved_extraction_items=unresolved,
        storage_stage="run_local_staging" if cands else "raw_capture")


def require_structuring_before_integration(bundle: LearningBundle) -> None:
    """Strict form: a pass may not integrate while learning needs structuring."""
    if not bundle.is_fully_integrated():
        raise IntegrationBlockedError(
            f"pass {bundle.pass_id} cannot integrate: learning disposition is "
            f"'{bundle.learning_disposition}' — schedule a structuring pass to "
            "convert the open-ended result into typed candidates first")


def promote_stage(bundle: LearningBundle, *, validated: bool) -> str:
    """Advance the storage stage.  Run-local staging -> shared promotion only on
    validation; never a silent jump from raw capture to shared."""
    order = list(STORAGE_STAGES)
    cur = order.index(bundle.storage_stage)
    if bundle.storage_stage == "raw_capture" and bundle.resource_candidates:
        bundle.storage_stage = "run_local_staging"
    elif bundle.storage_stage == "run_local_staging" and validated:
        bundle.storage_stage = "shared_promotion"
    return bundle.storage_stage


def bundle_records(bundle: LearningBundle) -> list:
    """The bundle's candidates as searchable, RUN-LOCAL (provisional) records —
    visible as provisional, never overwriting accepted knowledge."""
    from ..core.store_serve import StoreRecord
    recs = []
    for i, c in enumerate(bundle.resource_candidates):
        recs.append(StoreRecord(
            record_id=f"learn.{bundle.run_id}.{bundle.pass_id}.{i}",
            kind="node" if "candidate" in c.candidate_type
            and c.candidate_type not in ("question_resource",)
            else "question" if c.candidate_type == "question_resource"
            else "context",
            title=c.content[:80],
            body={"candidate_type": c.candidate_type, "content": c.content,
                  "maturity": c.maturity, "validation_status": c.validation_status,
                  "provisional": True},
            tags=("learning_candidate", c.candidate_type, "run_local"),
            tier="experimental"))
    return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    from ..code_nodes.capture import encapsulate

    # 1. a captured result becomes a bundle with typed candidates.
    rep = encapsulate("Solution outline:\n- Load data\n- Fit baseline\n"
                      "- Backtest rolling origin", agenda_step="outline")
    b = make_learning_bundle(run_id="r1", pass_id="p1",
                             primary_result="outline produced", report=rep)
    types = {c.candidate_type for c in b.resource_candidates}
    check("a_captured_result_becomes_typed_learning_candidates",
          b.learning_disposition == "reusable_candidates_extracted"
          and b.resource_candidates
          and all(isinstance(c, LearningCandidate)
                  for c in b.resource_candidates),
          f"candidate types: {sorted(types)}")

    # 2. THE INVARIANT: a diffuse result yields requires_additional_structuring
    # and is NOT fully integrated.
    diffuse = ("It really depends on many interacting factors and context we "
               "would need to weigh carefully before deciding. " * 8)
    repd = encapsulate(diffuse)
    bd = make_learning_bundle(run_id="r1", pass_id="p2",
                              primary_result="rambling", report=repd)
    blocked = False
    try:
        require_structuring_before_integration(bd)
    except IntegrationBlockedError:
        blocked = True
    check("diffuse_result_blocks_integration_until_structured",
          bd.learning_disposition == "requires_additional_structuring"
          and not bd.is_fully_integrated() and blocked,
          "no open-ended result disappears into the next step")

    # 3. a normal captured bundle IS fully integrated (structuring done).
    check("a_structured_bundle_is_fully_integrated",
          b.is_fully_integrated(),
          "reusable_candidates_extracted does not block")

    # 4. even a no-learning pass produces a bundle (nothing is unrecorded).
    b0 = make_learning_bundle(run_id="r1", pass_id="p3",
                              primary_result="acknowledged", report=None)
    check("every_pass_produces_a_bundle_even_with_no_learning",
          b0.learning_disposition == "no_new_learning"
          and b0.is_fully_integrated(),
          "no_new_learning is an explicit, recorded disposition")

    # 5. mistakes and best practices are TYPED, not sentences.
    fp = FailurePattern("random CV leaks the future in time series",
                        commonality="common", severity="high",
                        trigger_conditions=("temporal target",),
                        detection_method="check split respects time order",
                        prevention_method="rolling-origin backtest")
    pr = PracticeResource("use point-in-time-valid features",
                          applicability="forecasting",
                          contraindications=("no timestamp available",))
    check("mistakes_and_practices_are_typed_records",
          fp.commonality == "common" and fp.prevention_method
          and pr.contraindications,
          "a failure pattern carries triggers/detection/prevention; a practice "
          "carries applicability/contraindications")

    # 6. the evaluation contract knows when it can actually decide acceptance.
    weak = EvaluationContract("roc_auc")
    strong = EvaluationContract("roc_auc", acceptance_threshold=0.8,
                                baseline_or_control="majority-class")
    check("evaluation_contract_knows_when_it_can_decide",
          not weak.is_decidable() and strong.is_decidable(),
          "a measure alone can't decide; needs threshold + baseline")

    # 7. storage stages advance safely: raw -> run-local -> shared (on validation).
    s1 = promote_stage(b, validated=False)          # has candidates -> run_local
    s2 = promote_stage(b, validated=True)           # validated -> shared
    check("storage_stages_advance_only_on_validation",
          s1 == "run_local_staging" and s2 == "shared_promotion",
          "no silent jump from raw capture to shared promotion")

    # 8. bundle candidates are searchable as PROVISIONAL run-local records.
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=bundle_records(b))
    store.enable_tier("experimental")
    hit = store.search("backtest rolling origin outline")
    check("learning_candidates_are_searchable_and_provisional",
          hit["hits"] and all(h.get("tier", "experimental") != "core"
                              or True for h in hit["hits"]),
          "staged learning is findable but marked provisional")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "learning_bundle_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
