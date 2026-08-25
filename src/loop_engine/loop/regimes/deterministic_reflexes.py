"""Deterministic reflexes — the if-then moves an expert makes without thinking.

These are the ``deterministic_rule`` regimes: they read the data/task facts on the
Knowledge and answer with no model call.  They are ordered by *cost as priority*
(lower cost fires first among the free rules), and the two safety reflexes are
cheapest of all so they win before any build step:

- **near-perfect → audit for leakage** (a saturated score is guilty until proven
  innocent), and
- **verify the split before any label-aware transform** (never target-encode
  before the split is proven leakage-free).

Each build reflex encodes its own precondition, so they compose safely: the
high-cardinality encoder simply refuses to fire until the split is verified, and
the split-verify reflex fills that gap — no external ordering needed.  When
several genuinely apply, the loop takes the highest-priority one, applies it, and
asks again; the rest fire on later turns.

Every regime here is a ``(Knowledge) -> NextActionProposal | None`` function; a
spec list at the bottom is what the registry consumes.
"""

from __future__ import annotations

from ...strings.knowledge import Knowledge
from ...loop.moves import answer, move


def near_perfect_leakage_audit(k: Knowledge):
    if k.fact("near_perfect"):
        return answer("near_perfect_leakage_audit", "deterministic_rule",
                      [move("run_tests", "leakage_audit",
                            mechanism="a near-perfect score is guilty until a "
                            "leakage/identity audit clears it", confidence=0.95)],
                      0.95)
    return None


def verify_split_first(k: Knowledge):
    wants_label_aware = (k.fact("high_cardinality_cols")
                         or k.fact("wants_target_encoding"))
    if wants_label_aware and not k.fact("split_verified"):
        return answer("verify_split_first", "deterministic_rule",
                      [move("run_tests", "verify_split_leakage_free",
                            mechanism="a label-aware transform is wanted but the "
                            "split is not proven leakage-free — verify it first",
                            confidence=0.92)], 0.92)
    return None


def establish_baseline(k: Knowledge):
    if not k.fact("has_baseline"):
        return answer("establish_baseline", "deterministic_rule",
                      [move("add_node", "baseline=deterministic_default",
                            mechanism="no baseline yet — establish a control "
                            "before anything expensive", confidence=0.9)], 0.9)
    return None


def add_missing_model(k: Knowledge):
    if k.fact("has_baseline") and not k.fact("has_model"):
        est = ("hgb" if k.fact("target_kind") in ("categorical", "continuous")
               else "hgb")
        return answer("add_missing_model", "deterministic_rule",
                      [move("add_node", f"estimator={est}",
                            mechanism="baseline exists, no model node — add a "
                            "strong tabular estimator", confidence=0.9)], 0.9)
    return None


def impute_missing(k: Knowledge):
    cols = k.fact("missing_cols")
    if cols:
        return answer("impute_missing", "deterministic_rule",
                      [move("add_node", "imputer=simple",
                            mechanism=f"{len(cols)} column(s) have missing "
                            "values — add an imputer", confidence=0.85)], 0.85)
    return None


def featurize_text(k: Knowledge):
    cols = k.fact("text_cols")
    if cols:
        return answer("featurize_text", "deterministic_rule",
                      [move("add_node", "text_featurizer=hashing",
                            mechanism=f"{len(cols)} text column(s) — add a "
                            "keyless text featurizer", confidence=0.85)], 0.85)
    return None


def handle_imbalance(k: Knowledge):
    if k.fact("imbalanced") and k.fact("target_kind") == "categorical":
        return answer("handle_imbalance", "deterministic_rule",
                      [move("add_node", "class_weight=balanced",
                            mechanism="imbalanced classification target — weight "
                            "classes (cheaper and safer than resampling)",
                            confidence=0.82)], 0.82)
    return None


def encode_high_cardinality(k: Knowledge):
    # Precondition: the split must be proven leakage-free (verify_split_first
    # handles the not-yet-verified case).  This is the reflex's own safety gate.
    if k.fact("high_cardinality_cols") and k.fact("split_verified"):
        return answer("encode_high_cardinality", "deterministic_rule",
                      [move("add_node", "target_encoder=out_of_fold",
                            mechanism="high-cardinality categoricals with a "
                            "verified split — out-of-fold target encoding",
                            confidence=0.83)], 0.83)
    return None


def set_temporal_split(k: Knowledge):
    if k.fact("time_axis") and k.fact("split_strategy") != "temporal_forward":
        return answer("set_temporal_split", "deterministic_rule",
                      [move("mutate", "split_strategy=temporal_forward",
                            mechanism="a time axis exists — a random split leaks "
                            "the future; switch to a forward temporal split",
                            confidence=0.9)], 0.9)
    return None


def add_cross_validation(k: Knowledge):
    if k.fact("has_model") and not k.fact("has_cv"):
        return answer("add_cross_validation", "deterministic_rule",
                      [move("add_node", "cross_validation=grouped_or_kfold",
                            mechanism="a model exists but no cross-validation — "
                            "add out-of-fold evaluation", confidence=0.8)], 0.8)
    return None


# (name, category, fn, kwargs) — cost is priority: lower fires first.
SPECS = [
    ("near_perfect_leakage_audit", "deterministic_rule",
     near_perfect_leakage_audit, {"cost": 0.0}),
    ("verify_split_first", "deterministic_rule", verify_split_first,
     {"cost": 0.05}),
    ("establish_baseline", "deterministic_rule", establish_baseline,
     {"cost": 0.1}),
    ("add_missing_model", "deterministic_rule", add_missing_model,
     {"cost": 0.2}),
    ("impute_missing", "deterministic_rule", impute_missing, {"cost": 0.3}),
    ("featurize_text", "deterministic_rule", featurize_text, {"cost": 0.4}),
    ("handle_imbalance", "deterministic_rule", handle_imbalance, {"cost": 0.5}),
    ("encode_high_cardinality", "deterministic_rule", encode_high_cardinality,
     {"cost": 0.6}),
    ("set_temporal_split", "deterministic_rule", set_temporal_split,
     {"cost": 0.7}),
    ("add_cross_validation", "deterministic_rule", add_cross_validation,
     {"cost": 0.8}),
]
