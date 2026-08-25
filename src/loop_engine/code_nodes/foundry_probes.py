"""Foundry probes — interrogation questions promoted to executable Code Nodes.

Architectural role: Code Node system (§13.6 question-to-Code promotions).

Owns:
    - residual_predictability_probe: "Can an out-of-fold secondary model
      predict where the primary model errs?" — cross-fitted, seeded; a high
      probe AUC means exploitable structure remains (features to add, or a
      subgroup the model misses);
    - train_test_distinguishability_probe: "Can a classifier tell train
      rows from test rows?" — the domain-classifier shift/leak detector; AUC
      near 0.5 means same distribution, high AUC names the drifting columns.

Does not own:
    - acting on findings (the loop decides; these emit finding Strings),
      question TEXT (strings/interrogation owns the bank), or any model call
      (both probes are seeded sklearn — code_only, local_machine, pure).

Public entry points:
    - residual_predictability_probe(X, y, predictions) -> finding dict
    - train_test_distinguishability_probe(train_X, test_X) -> finding dict

Key invariants:
    - both probes are SEEDED (repeatable) and abstain on degenerate input
      (too few rows / one class) instead of fabricating a verdict;
    - verdicts carry thresholds openly; a probe finding is an observation
      for the loop, never an accepted claim.

Verification: self_test() — canary-style: planted structure must FIRE,
clean noise must NOT (a probe without a failing canary is not proven).
"""
from __future__ import annotations

_MIN_ROWS = 60


def _abstain(probe: str, why: str) -> dict:
    return {"record_type": f"{probe}/v1", "verdict": "abstain",
            "reason": why,
            "note": "abstention is a real state — no fabricated verdict"}


def residual_predictability_probe(X, y, predictions, *, folds: int = 5,
                                  seed: int = 0) -> dict:
    """Cross-fitted probe: fit a secondary model to predict WHERE the primary
    erred (residual sign for classification-style 0/1 targets).  Probe AUC
    well above 0.5 = the errors have learnable structure the primary missed."""
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    X = np.asarray(X, dtype=float)
    y = np.asarray(y).ravel()
    pred = np.asarray(predictions).ravel()
    err = (np.round(pred) != y).astype(int)
    if len(y) < _MIN_ROWS:
        return _abstain("residual_predictability", f"{len(y)} rows < "
                        f"{_MIN_ROWS}")
    if err.sum() < 10 or err.sum() > len(err) - 10:
        return _abstain("residual_predictability",
                        "too few errors (or almost all errors) to probe")
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    proba = cross_val_predict(
        HistGradientBoostingClassifier(max_iter=120, random_state=seed),
        X, err, cv=cv, method="predict_proba")[:, 1]
    auc = float(roc_auc_score(err, proba))
    threshold = 0.62
    return {"record_type": "residual_predictability/v1",
            "probe_auc": round(auc, 4), "error_rate": round(float(err.mean()), 4),
            "threshold": threshold,
            "verdict": ("errors_have_learnable_structure" if auc >= threshold
                        else "no_exploitable_residual_structure_found"),
            "recommendation": ("the primary model is missing signal — add "
                               "features/subgroup handling where the probe "
                               "scores high" if auc >= threshold else
                               "residuals look unstructured at this probe's "
                               "capacity — spend elsewhere"),
            "seeded": seed, "attribution": "observation, not accepted claim"}


def train_test_distinguishability_probe(train_X, test_X, *, folds: int = 5,
                                        seed: int = 0, top_k: int = 5) -> dict:
    """The domain classifier: label train rows 0 and test rows 1, cross-fit a
    classifier.  AUC ≈ 0.5 = same distribution; high AUC = shift or leakage,
    and the top importances NAME the drifting columns."""
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.model_selection import train_test_split

    A = np.asarray(train_X, dtype=float)
    B = np.asarray(test_X, dtype=float)
    if len(A) < _MIN_ROWS or len(B) < _MIN_ROWS:
        return _abstain("train_test_distinguishability", "too few rows")
    X = np.vstack([A, B])
    d = np.r_[np.zeros(len(A)), np.ones(len(B))]
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    proba = cross_val_predict(
        HistGradientBoostingClassifier(max_iter=120, random_state=seed),
        X, d, cv=cv, method="predict_proba")[:, 1]
    auc = float(roc_auc_score(d, proba))
    threshold = 0.60
    drifting = []
    if auc >= threshold:
        Xf, Xh, df, dh = train_test_split(X, d, test_size=0.3,
                                          random_state=seed, stratify=d)
        clf = HistGradientBoostingClassifier(max_iter=120,
                                             random_state=seed).fit(Xf, df)
        imp = permutation_importance(clf, Xh, dh, n_repeats=3,
                                     random_state=seed)
        order = imp.importances_mean.argsort()[::-1][:top_k]
        drifting = [{"column_index": int(i),
                     "importance": round(float(imp.importances_mean[i]), 4)}
                    for i in order if imp.importances_mean[i] > 0]
    return {"record_type": "train_test_distinguishability/v1",
            "domain_auc": round(auc, 4), "threshold": threshold,
            "verdict": ("distributions_differ" if auc >= threshold
                        else "no_material_shift_detected"),
            "drifting_columns": drifting,
            "recommendation": ("investigate the named columns for shift or "
                               "leakage before trusting validation" if
                               drifting else "train and test look exchangeable "
                               "at this probe's capacity"),
            "seeded": seed, "attribution": "observation, not accepted claim"}


def self_test() -> dict:
    import numpy as np
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    rng = np.random.default_rng(3)
    n = 600
    X = rng.normal(0, 1, (n, 4))

    # --- residual probe canaries ------------------------------------------
    # planted structure: the primary "model" ignores column 2, and errors are
    # exactly where column 2 is large — the probe MUST fire.
    y = ((X[:, 0] + X[:, 1] + 1.5 * X[:, 2]) > 0).astype(int)
    weak_pred = ((X[:, 0] + X[:, 1]) > 0).astype(float)   # blind to col 2
    fired = residual_predictability_probe(X, y, weak_pred)
    # clean noise: errors are coin flips — the probe must NOT fire.
    y2 = rng.integers(0, 2, n)
    coin_pred = rng.integers(0, 2, n).astype(float)
    quiet = residual_predictability_probe(X, y2, coin_pred)
    check("residual_probe_fires_on_planted_structure_only",
          fired["verdict"] == "errors_have_learnable_structure"
          and fired["probe_auc"] > 0.7
          and quiet["verdict"] == "no_exploitable_residual_structure_found",
          f"planted auc {fired['probe_auc']} vs noise "
          f"{quiet['probe_auc']}")

    # --- domain-classifier canaries ---------------------------------------
    # planted shift: test's column 1 is displaced — must fire AND name it.
    B = rng.normal(0, 1, (300, 4)); B[:, 1] += 2.0
    shifted = train_test_distinguishability_probe(X, B)
    same = train_test_distinguishability_probe(X[:300], X[300:])
    check("domain_probe_fires_on_shift_and_names_the_column",
          shifted["verdict"] == "distributions_differ"
          and shifted["domain_auc"] > 0.8
          and shifted["drifting_columns"]
          and shifted["drifting_columns"][0]["column_index"] == 1
          and same["verdict"] == "no_material_shift_detected",
          f"shift auc {shifted['domain_auc']} names column 1; "
          f"same-dist auc {same['domain_auc']}")

    # --- abstention is a real state ---------------------------------------
    tiny = residual_predictability_probe(X[:20], y[:20], weak_pred[:20])
    check("probes_abstain_on_degenerate_input_never_fabricate",
          tiny["verdict"] == "abstain" and "rows" in tiny["reason"])

    # --- probes are seeded: identical reruns, identical verdicts ----------
    again = residual_predictability_probe(X, y, weak_pred)
    check("probes_are_seeded_and_repeatable",
          again["probe_auc"] == fired["probe_auc"])

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
