"""Measurement — how to judge models, task success, and the train-CV gap, as
Context Intelligence plus a deterministic reuse node.

Owner ask (2026-08-23): we need Context Intelligence for measuring models, task
success, the train-CV gap, etc. — every industry has its own ways of measuring,
and that belongs in strings.  This module serves the two moat asset classes at
once (see [[harness-commodity-intelligence-is-the-moat]]):

  * CONTEXT INTELLIGENCE (data): ``measurement_pack`` contains the conventions as
    IntelligenceStrings, step-tagged (mostly ``step:verify``): metric definitions
    and when-to-use, industry conventions (clinical, finance, search/ranking,
    NLP/generation, forecasting, fraud, manufacturing, experiment), the
    overfitting/generalization-gap warnings, and the task-success framing
    (freeze the metric+threshold+population BEFORE measuring).  Swappable and
    distillable — better measurement strings ⇒ a better reading of every result.

  * A DETERMINISTIC REUSE-NODE (fast, inherited by everyone):
    ``read_generalization_gap`` — the train-vs-CV gap is a NUMBER, not prose, so
    it is computed here, direction- and scale-aware, returning a plain verdict
    (healthy / overfitting / cv_beats_train_suspect_leakage /
    too_perfect_suspect_leakage / high_variance_cv / no_better_than_baseline /
    insufficient_evidence).  It complements review_mode's output-side degeneracy
    detectors (constant / chance-level / too-perfect); this one reads the
    train↔honest-estimate relationship.

The HARNESS is domain-neutral: ``select_measures`` reads a task's signals and
returns which metrics apply and which are misleading here — the industry
knowledge lives in the strings, not in this code.  Everything is a searchable
store record, so measurement flows through the practitioner like any capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from ..strings.intelligence_strings import IntelligenceString, StringBank, compose

TASK_TYPES = ("classification", "regression", "ranking", "forecasting",
              "generation", "detection", "clustering", "unknown")
TARGET_SHAPES = ("binary", "multiclass", "continuous", "probability",
                 "ranking", "sequence", "unknown")
CLASS_BALANCE = ("balanced", "imbalanced", "unknown")
GAP_VERDICTS = ("healthy", "overfitting", "cv_beats_train_suspect_leakage",
                "too_perfect_suspect_leakage", "high_variance_cv",
                "no_better_than_baseline", "insufficient_evidence")


# ---------------------------------------------------------------------------
# The deterministic reuse-node: read the generalization gap.
# ---------------------------------------------------------------------------


@dataclass
class GapReading:
    """The computed reading of a train-vs-CV gap — numbers AND a plain verdict."""
    verdict: str
    train: "float | None"
    cv: "float | None"
    gap: float                     # directional: how much train BEATS cv
    relative_gap: float            # gap / |cv| (scale-robust across metrics)
    reason: str
    threshold_used: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.verdict not in GAP_VERDICTS:
            raise ValueError(f"verdict must be one of {GAP_VERDICTS}")


def read_generalization_gap(train, cv, *, metric_direction: str = "maximize",
                            cv_std=None, n_folds=None, bounded_01: bool = False,
                            baseline=None, overfit_rel: float = 0.10,
                            suspicious_rel: float = 0.05, perfect: float = 1.0,
                            perfect_eps: float = 0.005) -> GapReading:
    """Read the train-CV gap deterministically.

    ``metric_direction`` is 'maximize' (accuracy, AUC, F1, R²…) or 'minimize'
    (RMSE, MAE, log-loss…).  The gap is computed in the DIRECTION of overfitting —
    how much better the model looks on train than on the honest cross-validated
    estimate — and scaled by |cv| so the same thresholds work for a 0.85 AUC and
    an 8.0 RMSE.  Thresholds are parameters (never fixed constants), and the
    computed numbers are returned so a caller can apply its own policy."""
    thr = {"overfit_rel": overfit_rel, "suspicious_rel": suspicious_rel,
           "perfect_eps": perfect_eps}
    if metric_direction not in ("maximize", "minimize"):
        raise ValueError("metric_direction must be 'maximize' or 'minimize'")
    if cv is None or train is None or (n_folds is not None and n_folds < 2):
        return GapReading("insufficient_evidence", train, cv, 0.0, 0.0,
                          "no cross-validated estimate (or <2 folds): the honest "
                          "number is unknown, so no gap can be read", thr)
    # directional gap: positive => train looks better than cv => overfit side.
    gap = (train - cv) if metric_direction == "maximize" else (cv - train)
    rel = gap / (abs(cv) + 1e-9)

    # 1. suspiciously perfect honest estimate — leakage review before applause.
    if bounded_01 and metric_direction == "maximize" \
            and cv >= perfect - perfect_eps:
        return GapReading("too_perfect_suspect_leakage", train, cv, gap, rel,
                          f"cross-validated score {cv:.4f} is at the metric "
                          f"ceiling ({perfect}); check leakage, target proxies, "
                          "answer exposure, and duplicated rows before trusting "
                          "it", thr)
    # 2. cv better than train — usually leakage in the folds or a metric bug.
    if gap < 0 and abs(rel) >= suspicious_rel:
        return GapReading("cv_beats_train_suspect_leakage", train, cv, gap, rel,
                          f"the cross-validated score beats the training score "
                          f"(relative {rel:+.1%}) — a red flag for CV-fold "
                          "leakage, a target proxy, or a metric bug", thr)
    # 3. no better than a provided baseline — useless regardless of the gap.
    if baseline is not None:
        useless = (cv <= baseline) if metric_direction == "maximize" \
            else (cv >= baseline)
        if useless:
            return GapReading("no_better_than_baseline", train, cv, gap, rel,
                              f"cross-validated score {cv} is no better than the "
                              f"baseline {baseline}: not evidence of skill", thr)
    # 4. is the gap within fold noise?  then we can't trust it.
    if cv_std is not None and cv_std > 0 and cv_std >= abs(gap):
        return GapReading("high_variance_cv", train, cv, gap, rel,
                          f"the fold-to-fold spread (±{cv_std}) exceeds the gap "
                          f"({gap:+.4f}); the estimate itself is unreliable — "
                          "report the confidence interval, don't trust the mean",
                          thr)
    # 5. strong gap in the overfit direction.
    if rel >= overfit_rel:
        return GapReading("overfitting", train, cv, gap, rel,
                          f"training score beats the cross-validated score by "
                          f"{rel:.1%} (>{overfit_rel:.0%}): the model memorized "
                          "rather than generalized — decide on the CV number",
                          thr)
    return GapReading("healthy", train, cv, gap, rel,
                      f"train and cross-validated scores agree within {rel:.1%}: "
                      "no strong overfitting signal (still verify leakage)", thr)


# ---------------------------------------------------------------------------
# The harness: which measures apply to this task (domain-neutral selection).
# ---------------------------------------------------------------------------


@dataclass
class MeasurementSignals:
    task_type: str = "unknown"
    target_shape: str = "unknown"
    class_balance: str = "unknown"
    industry: str = ""
    has_holdout: bool = False

    def __post_init__(self):
        if self.task_type not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {TASK_TYPES}")
        if self.target_shape not in TARGET_SHAPES:
            raise ValueError(f"target_shape must be one of {TARGET_SHAPES}")
        if self.class_balance not in CLASS_BALANCE:
            raise ValueError(f"class_balance must be one of {CLASS_BALANCE}")


@dataclass
class MeasurementPlan:
    recommended_metrics: tuple = ()
    misleading_metrics: tuple = ()
    health_checks: tuple = ()
    reasons: tuple = ()


# Deterministic, domain-neutral: maps task shape -> which metrics apply.  The
# WHY (definitions, industry conventions) lives in the strings, not here.
def select_measures(signals: MeasurementSignals) -> MeasurementPlan:
    rec, mis, reasons = [], [], []
    tt, bal = signals.task_type, signals.class_balance
    if tt == "classification":
        rec += ["roc_auc"]
        if signals.target_shape == "probability":
            rec += ["log_loss", "brier_calibration"]
        if bal == "imbalanced":
            rec += ["pr_auc", "balanced_accuracy", "f1", "mcc"]
            mis += ["accuracy"]
            reasons.append("accuracy is misleading under class imbalance; "
                           "precision/recall, PR-AUC, balanced accuracy, and MCC "
                           "read the minority class honestly")
        else:
            rec += ["accuracy", "f1"]
    elif tt == "regression":
        rec += ["rmse", "mae", "r2"]
        reasons.append("RMSE penalizes large errors, MAE is robust to outliers, "
                       "R² is variance explained (can go negative); MAPE blows up "
                       "near zero targets")
    elif tt == "ranking":
        rec += ["ndcg", "map", "mrr", "precision_at_k"]
    elif tt == "forecasting":
        rec += ["mase", "smape", "rmse"]
        reasons.append("use a rolling-origin backtest and MASE (scaled against a "
                       "naive forecast); never random-split a time series")
    elif tt == "generation":
        rec += ["reference_and_human_eval"]
        mis += ["bleu", "rouge"]
        reasons.append("n-gram metrics (BLEU/ROUGE) correlate weakly with quality;"
                       " pair them with reference-based and human evaluation")
    elif tt == "detection":
        rec += ["pr_auc", "precision_at_low_fpr", "recall"]
    # always-on health checks (computable, cheap) — the reuse-node battery.
    checks = ["train_cv_gap (read_generalization_gap)",
              "leakage / too-perfect (detect_too_perfect)",
              "chance-level baseline (detect_chance_level)",
              "constant / degenerate output (detect_constant_output)"]
    if not signals.has_holdout:
        reasons.append("no holdout declared: the honest estimate is unverified — "
                       "reserve a sealed split before trusting any score")
    return MeasurementPlan(tuple(rec), tuple(mis), tuple(checks), tuple(reasons))


# ---------------------------------------------------------------------------
# Context Intelligence data, step-tagged and reusable.
# ---------------------------------------------------------------------------

_ANY = "any"


def _s(kind, text, tags, appl=_ANY):
    return IntelligenceString(kind, text, tags=tuple(tags), applicability=appl,
                              provenance="hand_seed")


def measurement_pack() -> StringBank:
    """The measurement conventions as Context Intelligence. Step-tagged
    (``step:verify`` mostly; success-framing also ``step:decide_next``).  A seed
    starter — grow or distil it per user/industry."""
    bank = StringBank()
    seed = [
        # --- the generalization gap (the owner's explicit example) ----------
        _s("consideration",
           "The train-CV gap is the primary overfitting signal: a large gap "
           "between the training score and the cross-validated score means the "
           "model memorized rather than generalized.",
           ("measurement", "gap", "overfitting", "step:verify")),
        _s("instruction",
           "The cross-validated (or holdout) score is the honest estimate; the "
           "training score is optimistic. Report and decide on the CV/holdout "
           "number, never the training number.",
           ("measurement", "gap", "step:verify")),
        _s("warning",
           "A CV score that beats the training score is a red flag — usually "
           "leakage in the CV folds, a target proxy, or a metric bug.",
           ("measurement", "gap", "leakage", "step:verify")),
        _s("warning",
           "A near-perfect score is suspicious before it is impressive: check "
           "leakage, target proxies, answer exposure, and duplicated rows.",
           ("measurement", "leakage", "step:verify")),
        _s("consideration",
           "High variance across CV folds means the estimate itself is "
           "unreliable; widen the folds or report the confidence interval — "
           "don't trust the mean.",
           ("measurement", "gap", "variance", "step:verify")),
        # --- task success framing (also decide, before you start) -----------
        _s("instruction",
           "Define the acceptance metric, its direction, threshold, and the "
           "population BEFORE measuring. A score without a frozen "
           "metric+population+provenance is not success.",
           ("measurement", "success", "step:decide_next", "step:verify")),
        _s("instruction",
           "Compare against a real baseline — a simple/majority/naive model AND "
           "the incumbent. Beating nothing is not evidence.",
           ("measurement", "success", "baseline", "step:verify")),
        _s("warning",
           "A best-of-many score compared to a one-shot baseline overstates "
           "skill; correct for selection breadth and report failure-inclusive "
           "outcomes.", ("measurement", "success", "step:verify")),
        # --- metric definitions / when-to-use (task-tagged) -----------------
        _s("consideration",
           "Under class imbalance, accuracy is misleading; use precision, "
           "recall, F1, PR-AUC (area under precision-recall), balanced accuracy, "
           "or MCC (Matthews correlation).",
           ("measurement", "classification", "imbalanced", "step:verify"),
           appl="classification imbalanced"),
        _s("consideration",
           "A probability model needs calibration (Brier score, reliability "
           "diagram), not just ranking quality (ROC-AUC) — a well-ranked model "
           "can still be badly calibrated.",
           ("measurement", "classification", "calibration", "step:verify"),
           appl="classification probability"),
        _s("consideration",
           "Regression: RMSE penalizes large errors, MAE is robust to outliers, "
           "R² is variance explained (can be negative); avoid MAPE when targets "
           "approach zero.",
           ("measurement", "regression", "step:verify"), appl="regression"),
        _s("consideration",
           "Ranking/search: use NDCG, MAP, MRR, or precision@k — position "
           "matters, so a flat accuracy is the wrong lens.",
           ("measurement", "ranking", "step:verify"), appl="ranking search"),
        _s("consideration",
           "Forecasting: score with a rolling-origin backtest and MASE (scaled "
           "against a naive forecast); a random train/test split leaks the "
           "future.", ("measurement", "forecasting", "step:verify"),
           appl="forecasting time series"),
        # --- industry conventions (industry-tagged) -------------------------
        _s("consideration",
           "Clinical: report sensitivity and specificity, PPV/NPV at the "
           "operating threshold, and AUC with a confidence interval; the cost of "
           "a false negative usually dominates.",
           ("measurement", "industry", "clinical", "step:verify"),
           appl="clinical medical health"),
        _s("consideration",
           "Finance/trading: judge a strategy by risk-adjusted return (Sharpe), "
           "maximum drawdown, and an out-of-sample walk-forward backtest — never "
           "in-sample fit.",
           ("measurement", "industry", "finance", "step:verify"),
           appl="finance trading investment"),
        _s("consideration",
           "Fraud/security: precision at a low false-positive rate (or "
           "recall@fixed-alarm-budget) matters far more than accuracy or raw "
           "AUC — the base rate is tiny.",
           ("measurement", "industry", "fraud", "step:verify"),
           appl="fraud security anomaly"),
        _s("consideration",
           "Manufacturing/quality: track defect/escape rate, yield, and "
           "false-reject vs false-accept; a controlled process is judged by "
           "capability, not a single accuracy number.",
           ("measurement", "industry", "manufacturing", "step:verify"),
           appl="manufacturing quality"),
        _s("consideration",
           "Marketing/experiment: measure lift versus a control with a "
           "confidence interval; a metric that moves without a control arm is "
           "not causal evidence.",
           ("measurement", "industry", "experiment", "step:verify"),
           appl="marketing experiment ab test"),
    ]
    for s in seed:
        bank.add(s)
    return bank


def _tags_for(signals: MeasurementSignals) -> tuple:
    tags = ["measurement", "gap", "success", "step:verify"]
    if signals.task_type in TASK_TYPES and signals.task_type != "unknown":
        tags.append(signals.task_type)
    if signals.class_balance == "imbalanced":
        tags += ["imbalanced"]
    if signals.industry:
        tags += ["industry", signals.industry.lower()]
    return tuple(tags)


def interpret_measurement(signals: MeasurementSignals, *,
                          train=None, cv=None,
                          metric_direction: str = "maximize",
                          bank: "StringBank | None" = None,
                          **gap_kwargs) -> dict:
    """The verify-node reading: which measures apply (harness), the relevant
    measurement strings (intelligence), and — when train/cv are given — the
    deterministic gap verdict (reuse-node)."""
    b = bank if bank is not None else measurement_pack()
    plan = select_measures(signals)
    composed = compose(b, _tags_for(signals))
    out = {"record_type": "measurement_reading/v1",
           "recommended_metrics": list(plan.recommended_metrics),
           "misleading_metrics": list(plan.misleading_metrics),
           "health_checks": list(plan.health_checks),
           "reasons": list(plan.reasons),
           "prompt_fragment": composed["text"],
           "used_string_ids": composed["used_string_ids"],
           "n_strings": composed["n_used"]}
    if train is not None or cv is not None:
        g = read_generalization_gap(train, cv, metric_direction=metric_direction,
                                    **gap_kwargs)
        out["gap"] = {"verdict": g.verdict, "reason": g.reason,
                      "train": g.train, "cv": g.cv,
                      "relative_gap": round(g.relative_gap, 4)}
    return out


# ---------------------------------------------------------------------------
# Searchable records — measurement flows through the practitioner.
# ---------------------------------------------------------------------------


def measurement_nodes() -> list:
    """The selection DAG and the gap-reader as searchable node records."""
    from ..core.store_serve import StoreRecord
    return [
        StoreRecord(
            record_id="node.measurement.select_measures", kind="node",
            title="Select the metrics and health checks for a task",
            body={"input": "MeasurementSignals",
                  "output": "MeasurementPlan (recommended/misleading metrics + "
                  "health checks)",
                  "task_types": list(TASK_TYPES)},
            tags=("measurement", "metrics", "step:verify"), tier="core"),
        StoreRecord(
            record_id="node.measurement.read_generalization_gap", kind="node",
            title="Read the train-CV generalization gap (deterministic)",
            body={"input": "train score, cv score, metric_direction, cv_std, "
                  "baseline",
                  "output": "GapReading verdict: " + " / ".join(GAP_VERDICTS),
                  "note": "a computable reuse-node; complements review_mode "
                  "output-side degeneracy detectors"},
            tags=("measurement", "gap", "overfitting", "deterministic_node",
                  "step:verify"), tier="core"),
    ]


def pack_records(bank: "StringBank | None" = None) -> list:
    b = bank if bank is not None else measurement_pack()
    return [s.envelope() for s in b.all()]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. the gap reader catches overfitting (train >> cv, maximize).
    g = read_generalization_gap(0.99, 0.80, metric_direction="maximize")
    check("gap_reader_flags_overfitting",
          g.verdict == "overfitting" and g.gap > 0,
          f"{g.verdict}: {g.reason[:60]}")

    # 2. it calls agreement healthy.
    g2 = read_generalization_gap(0.86, 0.84)
    check("gap_reader_calls_agreement_healthy", g2.verdict == "healthy",
          f"{g2.verdict}")

    # 3. cv beating train is a leakage red flag.
    g3 = read_generalization_gap(0.80, 0.88)
    check("gap_reader_flags_cv_beating_train_as_leakage",
          g3.verdict == "cv_beats_train_suspect_leakage",
          f"{g3.verdict}")

    # 4. a near-perfect bounded CV score → leakage review, not applause.
    g4 = read_generalization_gap(1.0, 0.9995, bounded_01=True)
    check("gap_reader_flags_too_perfect_as_suspect_leakage",
          g4.verdict == "too_perfect_suspect_leakage", f"{g4.verdict}")

    # 5. a gap within fold noise → high variance, not overfitting.
    g5 = read_generalization_gap(0.85, 0.80, cv_std=0.12)
    check("gap_reader_downgrades_to_high_variance_when_gap_is_within_noise",
          g5.verdict == "high_variance_cv", f"{g5.verdict}")

    # 6. it is direction-aware: minimize metric (RMSE) overfits when train<cv.
    g6 = read_generalization_gap(8.0, 12.0, metric_direction="minimize")
    check("gap_reader_is_direction_aware_for_minimize_metrics",
          g6.verdict == "overfitting",
          "lower RMSE on train than cv is the overfit direction")

    # 7. no cv => insufficient evidence, never a guess.
    g7 = read_generalization_gap(0.9, None)
    check("gap_reader_abstains_without_a_cv_estimate",
          g7.verdict == "insufficient_evidence", f"{g7.verdict}")

    # 8. select_measures marks accuracy MISLEADING under imbalance.
    plan = select_measures(MeasurementSignals(
        task_type="classification", target_shape="binary",
        class_balance="imbalanced"))
    check("select_measures_marks_accuracy_misleading_under_imbalance",
          "accuracy" in plan.misleading_metrics
          and "pr_auc" in plan.recommended_metrics,
          f"recommended={plan.recommended_metrics}")

    # 9. Context Intelligence carries the industry and gap language the owner
    # asked for.
    bank = measurement_pack()
    txt = " ".join(s.text.lower() for s in bank.all())
    check("context_intelligence_carries_gap_and_industry_measures",
          "train-cv gap" in txt and "sensitivity and specificity" in txt
          and "sharpe" in txt and "mase" in txt and "calibration" in txt,
          f"{len(bank)} measurement strings across metrics + industries")

    # 10. interpret composes verify strings AND the computed gap verdict.
    reading = interpret_measurement(
        MeasurementSignals(task_type="classification", class_balance="imbalanced",
                           industry="clinical"),
        train=0.99, cv=0.80)
    check("interpret_composes_strings_and_the_computed_gap",
          reading["gap"]["verdict"] == "overfitting"
          and "accuracy" in reading["misleading_metrics"]
          and reading["n_strings"] >= 3,
          "the verify node gets metrics + strings + a numeric gap verdict")

    # 11. measurement is searchable through the one store DAG.
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=measurement_nodes() + pack_records(bank))
    hit = store.search("is my model overfitting train vs cross validation",
                       kind="node")
    check("measurement_flows_through_the_practitioner_as_searchable_records",
          hit["hits"] and any("read_generalization_gap" in h["record_id"]
                              for h in hit["hits"]),
          "the gap-reader node is findable through the one search DAG")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "measurement_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
