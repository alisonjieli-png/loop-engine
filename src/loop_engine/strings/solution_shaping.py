"""Solution shaping — decide whether to decompose into sub-models / sub-processes,
and carry the reasoning that pushes the model past a monolithic answer.

Owner ask (2026-08-23): we need DAGs and Context Intelligence on whether to build
out sub-models, sub-prediction models, sub-processes, etc., and prompts/string
intelligence that push the model to think outside the box, break the solution
into individual components, and consider stacking, bagging, and other ensembling.
The ultimate goal is an open-source practitioner harness where ALL the
intelligence lives as Context Intelligence.

So this module is split along exactly that line:

  * The HARNESS (domain-neutral code): ``should_decompose`` — a small decision DAG
    that reads signals and returns decompose / stay-monolithic / abstain-and-ask,
    emitting real practitioner ``CandidateAction`` moves.  It contains NO domain
    knowledge and works with an EMPTY string bank (it just escalates to a model
    ask when it cannot decide deterministically).

  * The INTELLIGENCE (data): ``solution_shaping_pack`` — a seed ``StringBank`` of
    ``IntelligenceString``s that say "think outside the box", "break the solution
    into components", "consider bagging / boosting / stacking / blending",
    "consider per-segment sub-models", "consider a gating/router or a cheap→
    expensive cascade".  These are strings, not code: an open-source consumer
    swaps or grows the pack (or distils new strings from accepted outcomes)
    without touching the loop.

``shape_solution_ask`` is where they meet: the harness composes the relevant
strings (chosen by the task's own signals) into a prompt fragment for the
decide/how node.  The decision node and every string are searchable store
records, so shaping flows through the practitioner like any other capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from ..loop.kernel import CandidateAction
from ..strings.intelligence_strings import (IntelligenceString, StringBank, compose,
                                   distill_string)

# The decomposition moves the harness can propose — a closed, plain-named set.
SHAPING_MOVES = (
    "split_by_target",          # a sub-model per output/target
    "split_by_segment",         # a sub-model per data segment / regime
    "split_by_stage",           # separate preprocessing/feature/model/calibrate
    "split_by_modality",        # a sub-process per input modality
    "ensemble_diverse",         # combine diverse base learners
    "route_gate",               # mixture-of-experts: route input to best sub-model
    "cascade_cheap_to_dear",    # cheap handles easy, escalate the hard residual
    "keep_monolithic",          # one model/process is genuinely right here
)
SHAPING_VERDICTS = ("decompose", "monolithic", "abstain_escalate")


@dataclass
class DecompositionSignals:
    """Domain-neutral signals the DAG reads.  All optional; unknowns stay False/0
    and push the decision toward honest escalation rather than a guess."""
    multi_part_goal: bool = False           # the goal names several deliverables
    heterogeneous_inputs: bool = False      # mixed modalities / sources
    independent_subproblems: bool = False   # parts solvable/verifiable separately
    subtask_count: int = 0                  # explicit sub-tasks detected
    estimated_complexity: float = 0.0       # 0..1 (unknown => 0)
    is_prediction_task: bool = False        # gates the ensembling strings
    signal_confidence: float = 0.0          # 0..1 how sure we are of the above


# Deterministic keyword cues — the cheapest signal reader (no model call).
_MULTIPART_CUES = ("and then", "as well as", "multiple", "several", "each of",
                   "for every", "per ", "both", "pipeline", "end-to-end",
                   "then predict", "and also")
_MODALITY_CUES = ("image", "text", "audio", "video", "tabular", "time series",
                  "graph", "sequence", "signal", "document")
_PREDICTION_CUES = ("predict", "forecast", "classif", "regress", "score",
                    "probability", "rank", "estimate", "detect")


def signals_from_text(objective: str, *, subtask_count: int = 0,
                      estimated_complexity: float = 0.0
                      ) -> DecompositionSignals:
    """Read decomposition signals from the objective text — deterministic cues
    only.  A weak reader on purpose: it should escalate, not overclaim."""
    t = (objective or "").lower()
    modalities = [m for m in _MODALITY_CUES if m in t]
    multipart = any(c in t for c in _MULTIPART_CUES) or len(modalities) >= 2
    is_pred = any(c in t for c in _PREDICTION_CUES)
    # confidence grows with how many independent cues agree.
    cues = sum([multipart, len(modalities) >= 2, subtask_count >= 3,
                estimated_complexity >= 0.6])
    return DecompositionSignals(
        multi_part_goal=multipart,
        heterogeneous_inputs=len(modalities) >= 2,
        independent_subproblems=multipart and is_pred,
        subtask_count=subtask_count,
        estimated_complexity=estimated_complexity,
        is_prediction_task=is_pred,
        signal_confidence=min(1.0, 0.25 * cues))


@dataclass
class ShapingDecision:
    """The DAG's output: a verdict, plain-English reasons, and real moves."""
    verdict: str
    reasons: tuple = ()
    moves: tuple = ()                # CandidateAction rows for the decide node
    escalate: bool = False          # ask a model (with the shaping strings)?

    def __post_init__(self):
        if self.verdict not in SHAPING_VERDICTS:
            raise ValueError(f"verdict must be one of {SHAPING_VERDICTS}")


def _move(name: str, rationale: str, *, cost: float, value: float,
          parallel: bool = True) -> CandidateAction:
    return CandidateAction(action=f"shape::{name}", kind="decompose",
                           rationale=rationale, estimated_cost=cost,
                           expected_value=value, parallelizable=parallel,
                           information_gain=0.3)


def should_decompose(signals: DecompositionSignals) -> ShapingDecision:
    """The decision DAG — domain-neutral, no strings baked in.

    decompose        when the task shows independent parts / multiple deliverables
                     / heterogeneous inputs / real complexity;
    monolithic       when it is clearly one small, single-part task;
    abstain_escalate when the signals are too weak to decide — hand the question
                     to a model, carrying the outside-the-box strings.
    """
    reasons: list = []
    moves: list = []

    # --- strong decompose signals -----------------------------------------
    if signals.independent_subproblems:
        reasons.append("the goal has parts that can be solved and verified "
                       "separately")
    if signals.multi_part_goal:
        reasons.append("the goal names several deliverables")
    if signals.heterogeneous_inputs:
        reasons.append("inputs are heterogeneous (mixed modalities/sources)")
    if signals.subtask_count >= 3:
        reasons.append(f"{signals.subtask_count} sub-tasks were detected")
    if signals.estimated_complexity >= 0.6:
        reasons.append(f"estimated complexity is high "
                       f"({signals.estimated_complexity:.2f})")

    strong = len(reasons)

    # --- clearly monolithic ------------------------------------------------
    if strong == 0 and signals.signal_confidence >= 0.5 \
            and signals.estimated_complexity <= 0.3:
        return ShapingDecision(
            "monolithic",
            reasons=("single-part, low-complexity task; one model/process is "
                     "the right hypothesis — but verify it, don't assume it",),
            moves=(_move("keep_monolithic",
                         "no independent parts detected; solve directly then "
                         "review for hidden structure", cost=1.0, value=0.5),))

    # --- too weak to decide: escalate to a model with the strings ----------
    if strong == 0:
        return ShapingDecision(
            "abstain_escalate",
            reasons=("decomposition signals are too weak to decide "
                     "deterministically; ask a model, carrying the "
                     "outside-the-box / decompose strings",),
            escalate=True,
            moves=(_move("keep_monolithic",
                         "provisional: proceed monolithic unless the model "
                         "identifies separable parts", cost=1.0, value=0.4),))

    # --- decompose: propose concrete, plain-named moves --------------------
    if signals.multi_part_goal or signals.subtask_count >= 3:
        moves.append(_move("split_by_stage",
                           "make preprocessing, representation, modeling, and "
                           "calibration separate reusable nodes", cost=2.0,
                           value=0.6))
    if signals.heterogeneous_inputs:
        moves.append(_move("split_by_modality",
                           "one sub-process per input modality, joined by a "
                           "typed edge", cost=2.0, value=0.6))
    if signals.independent_subproblems:
        moves.append(_move("split_by_segment",
                           "a sub-model per segment/regime may beat one global "
                           "model — trial it", cost=2.5, value=0.55))
    if signals.is_prediction_task:
        moves.append(_move("ensemble_diverse",
                           "combine diverse base learners (bagging/boosting/"
                           "stacking/blending); compare against the strongest "
                           "single member", cost=2.5, value=0.6))
        moves.append(_move("cascade_cheap_to_dear",
                           "cheap model handles easy cases, escalate only the "
                           "hard residual", cost=1.5, value=0.5))
    if not moves:                       # complex but shape unclear
        moves.append(_move("split_by_stage",
                           "high complexity with unclear structure: split into "
                           "stages to expose the shape", cost=2.0, value=0.5))
    return ShapingDecision("decompose", reasons=tuple(reasons),
                           moves=tuple(moves),
                           escalate=signals.signal_confidence < 0.5)


# ---------------------------------------------------------------------------
# Context Intelligence data in a reusable seed pack.
# ---------------------------------------------------------------------------

_ANY = "any"
_PRED = "prediction modeling"


def solution_shaping_pack() -> StringBank:
    """A seed bank of shaping strings.  This is the INTELLIGENCE — data, not
    code.  Open-source consumers replace or grow it; the harness composes
    whatever is in the bank.  Provenance 'hand_seed' marks these as a starter
    that accepted outcomes can supersede via distillation."""
    bank = StringBank()
    seed = [
        IntelligenceString("persona",
            "You are a solution architect who decomposes a hard problem into "
            "small, independently testable components before building anything.",
            tags=("shaping",), applicability=_ANY, provenance="hand_seed"),
        IntelligenceString("framing",
            "Frame the task as a graph of smaller sub-problems, not one "
            "monolithic answer. Which parts can be solved, verified, and reused "
            "separately?", tags=("shaping", "decompose"), applicability=_ANY,
            provenance="hand_seed"),
        IntelligenceString("instruction",
            "Think outside the box: list at least three structurally different "
            "approaches before committing to one. Do not default to the first "
            "solution.", tags=("shaping", "diversity"), applicability=_ANY,
            provenance="hand_seed"),
        IntelligenceString("instruction",
            "Break the solution into individual components. For each component "
            "decide: reuse an existing capability, compose from parts, or build "
            "a small dedicated sub-model or sub-process.",
            tags=("shaping", "decompose"), applicability=_ANY,
            provenance="hand_seed"),
        IntelligenceString("consideration",
            "Consider separate sub-prediction models per target, segment, or "
            "regime instead of one global model — trial it against the global "
            "baseline.", tags=("submodel",), applicability=_PRED,
            provenance="hand_seed"),
        IntelligenceString("consideration",
            "Consider sub-processes as separate reusable nodes: a preprocessing "
            "stage, a feature/representation stage, a modeling stage, and a "
            "post-processing/calibration stage.",
            tags=("shaping", "subprocess"), applicability=_ANY,
            provenance="hand_seed"),
        IntelligenceString("consideration",
            "Consider ensembling: bagging (variance reduction via bootstrap "
            "replicas), boosting (bias reduction via sequential residual "
            "fitting), stacking (a meta-model over diverse base learners), and "
            "simple blending/averaging. Compare each against its strongest "
            "single member — more members is not automatically better.",
            tags=("ensemble", "stacking", "bagging", "boosting"),
            applicability=_PRED, provenance="hand_seed"),
        IntelligenceString("consideration",
            "Consider a gating/router model (mixture-of-experts) that sends each "
            "input to the sub-model best suited to it, rather than one model for "
            "all inputs.", tags=("router", "ensemble"),
            applicability=_PRED, provenance="hand_seed"),
        IntelligenceString("consideration",
            "Consider a cascade: a cheap model handles easy cases and abstains "
            "to an expensive model only on the hard residual.",
            tags=("shaping", "cascade"), applicability=_ANY,
            provenance="hand_seed"),
        IntelligenceString("warning",
            "A single monolithic model or prompt is a hypothesis, not a "
            "default. Justify NOT decomposing when the task has independent "
            "parts.", tags=("shaping", "decompose"), applicability=_ANY,
            provenance="hand_seed"),
        IntelligenceString("list_item",
            "Decomposition moves to weigh: split by target · split by data "
            "segment/regime · split by pipeline stage · split by modality · "
            "per-component sub-model · ensemble of diverse learners · "
            "router/gating · cheap-to-expensive cascade.",
            tags=("shaping", "checklist"), applicability=_ANY,
            provenance="hand_seed"),
    ]
    for s in seed:
        bank.add(s)
    return bank


def _tags_for(signals: DecompositionSignals) -> tuple:
    """Which string tags this task should retrieve — the harness choosing, from
    signals, which intelligence is relevant."""
    tags = ["shaping", "decompose", "diversity"]
    if signals.is_prediction_task:
        tags += ["prediction", "modeling", "ensemble", "stacking", "bagging",
                 "boosting", "router", "submodel"]
    if signals.heterogeneous_inputs:
        tags += ["subprocess"]
    return tuple(tags)


def shape_solution_ask(signals: DecompositionSignals, *,
                       bank: "StringBank | None" = None,
                       decision: "ShapingDecision | None" = None) -> dict:
    """Compose the shaping prompt fragment for the decide/how node: the relevant
    Context Intelligence (chosen by the task's signals) plus the DAG's verdict and
    proposed moves.  Works with an empty/None bank (harness still returns the
    decision) — the strings enrich, they are not required."""
    b = bank if bank is not None else solution_shaping_pack()
    dec = decision or should_decompose(signals)
    composed = compose(b, _tags_for(signals))
    move_lines = [f"- {m.action.split('::',1)[-1]}: {m.rationale}"
                  for m in dec.moves]
    text = composed["text"]
    if dec.escalate:
        text += ("\n\nThe decomposition signals were weak — decide the solution "
                 "shape yourself using the guidance above, and say which "
                 "components (if any) deserve their own sub-model or "
                 "sub-process.")
    return {"record_type": "solution_shaping_ask/v1",
            "verdict": dec.verdict, "escalate": dec.escalate,
            "reasons": list(dec.reasons),
            "prompt_fragment": text,
            "proposed_moves": move_lines,
            "used_string_ids": composed["used_string_ids"],
            "n_strings": composed["n_used"]}


# ---------------------------------------------------------------------------
# Searchable records — shaping flows through the practitioner like any node.
# ---------------------------------------------------------------------------


def shaping_decision_node():
    """The decision DAG as a searchable node record (kind='node')."""
    from ..static_architecture.store_serve import StoreRecord
    return StoreRecord(
        record_id="node.solution_shaping.should_decompose", kind="node",
        title="Decide whether to decompose into sub-models / sub-processes",
        body={"verdicts": list(SHAPING_VERDICTS), "moves": list(SHAPING_MOVES),
              "input": "DecompositionSignals",
              "output": "ShapingDecision (verdict + reasons + CandidateActions)",
              "escalates": "asks a model with the shaping strings when signals "
              "are too weak"},
        tags=("solution_shaping", "decompose", "ensemble", "sub_model",
              "sub_process", "step:decide_next", "step:how"),
        tier="core")


def pack_records(bank: "StringBank | None" = None) -> list:
    """Every shaping string as a searchable store record — the string
    intelligence, findable through the one search DAG."""
    b = bank if bank is not None else solution_shaping_pack()
    return [s.envelope() for s in b.all()]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. the DAG decomposes a multi-part prediction task and proposes real moves.
    sig = signals_from_text(
        "Clean the tabular data and the text notes, then predict churn per "
        "customer segment as well as overall.", subtask_count=4,
        estimated_complexity=0.7)
    dec = should_decompose(sig)
    move_names = {m.action.split("::", 1)[-1] for m in dec.moves}
    check("dag_decomposes_a_multi_part_prediction_task",
          dec.verdict == "decompose"
          and isinstance(dec.moves[0], CandidateAction)
          and ("ensemble_diverse" in move_names
               or "split_by_segment" in move_names),
          f"verdict={dec.verdict}, moves={sorted(move_names)}")

    # 2. a clearly single small task stays monolithic (but is told to verify).
    sig2 = DecompositionSignals(estimated_complexity=0.1, signal_confidence=0.8)
    dec2 = should_decompose(sig2)
    check("dag_keeps_a_single_small_task_monolithic",
          dec2.verdict == "monolithic"
          and "keep_monolithic" in dec2.moves[0].action,
          f"verdict={dec2.verdict}")

    # 3. weak signals ESCALATE to a model rather than guessing.
    sig3 = DecompositionSignals()          # nothing known
    dec3 = should_decompose(sig3)
    check("weak_signals_escalate_to_a_model_not_a_guess",
          dec3.verdict == "abstain_escalate" and dec3.escalate is True,
          "the honest default when the DAG cannot decide")

    # 4. the intelligence is STRINGS: the pack carries the words the owner asked
    # for — outside the box, decompose, stacking/bagging/boosting.
    bank = solution_shaping_pack()
    alltext = " ".join(s.text.lower() for s in bank.all())
    check("string_intelligence_carries_decompose_and_ensemble_language",
          "outside the box" in alltext and "break the solution" in alltext
          and "bagging" in alltext and "boosting" in alltext
          and "stacking" in alltext and "sub-process" in alltext
          and "sub-prediction models" in alltext,
          f"{len(bank)} shaping strings seeded")

    # 5. shape_solution_ask COMPOSES the right strings for the task: ensembling
    # strings appear for a prediction task and not for a non-prediction one.
    ask_pred = shape_solution_ask(sig)
    ask_plain = shape_solution_ask(
        signals_from_text("Write a project README from these notes."))
    check("harness_composes_prediction_strings_only_when_relevant",
          "bagging" in ask_pred["prompt_fragment"].lower()
          and "bagging" not in ask_plain["prompt_fragment"].lower()
          and "outside the box" in ask_plain["prompt_fragment"].lower(),
          "ensembling strings fire for prediction; outside-the-box fires for all")

    # 6. the harness works with an EMPTY bank (code needs no strings to decide).
    empty = StringBank()
    ask_empty = shape_solution_ask(sig, bank=empty)
    check("harness_decides_even_with_an_empty_string_bank",
          ask_empty["verdict"] == "decompose" and ask_empty["n_strings"] == 0
          and ask_empty["proposed_moves"],
          "blank-slate: the DAG still returns a decision and moves")

    # 7. distillation grows the pack: a model's shaping insight becomes a string.
    grown = solution_shaping_pack()
    grown.add(distill_string(
        "For imbalanced churn, a boosted tree on the minority residual beat "
        "the global model.", "consideration",
        tags=("shaping", "ensemble", "boosting"), applicability=_PRED))
    check("distillation_grows_the_string_intelligence",
          len(grown) == len(bank) + 1
          and any(s.provenance == "llm_distilled" for s in grown.all()),
          "accepted model reasoning becomes a new, retrievable shaping string")

    # 8. shaping is searchable: the decision node and strings register.
    from ..static_architecture.store_serve import SolverStore
    recs = [shaping_decision_node()] + pack_records(bank)
    store = SolverStore(core_records=recs)
    hit = store.search("should we build separate sub-models or an ensemble",
                       kind="node")
    check("shaping_flows_through_the_practitioner_as_searchable_records",
          hit["hits"]
          and hit["hits"][0]["record_id"]
          == "node.solution_shaping.should_decompose",
          "the decompose decision is findable through the one search DAG")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "solution_shaping_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
