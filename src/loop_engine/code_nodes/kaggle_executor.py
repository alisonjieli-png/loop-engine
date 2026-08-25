"""Kaggle executor — turn the loop's proposed moves into a real, submittable file.

The what-is-next loop *proposes* moves ("establish a baseline", "encode the
categoricals", "estimator=lightgbm").  Proposing is not solving: to learn how a
proposal actually performs, something has to EXECUTE it on real data and produce
a real prediction file.  This module is that bridge for the tabular-competition
family.  It is deliberately general — it reads the competition's own sample
submission to discover the identifier column, the target column, and the output
shape, so nothing here is hard-coded to one competition (the file-role-resolution
rule: the submission template is the authority on output fields, never a guessed
column name).

Flow::

    resolve roles from sample_submission  ->  run the what-is-next loop to get a
    PLAN (which estimator, whether to encode / impute)  ->  execute that plan with
    a real scikit-learn / LightGBM pipeline  ->  cross-validate for an honest local
    score  ->  write submission.csv in the template's exact shape.

The estimator is chosen by the loop's proposals when they name one, else by a
deterministic default (histogram gradient boosting — a strong tabular default;
the memory records it beating a heavier stacking zoo).  The caller submits the
file with the Kaggle command-line tool; this module never makes an external call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Role resolution — the sample submission is the authority on output shape.
# ---------------------------------------------------------------------------


@dataclass
class TaskRoles:
    """What the competition's own files say the output must look like."""
    id_col: str
    target_col: str
    problem: str                       # "classification" | "regression"
    proba: bool                        # target is a probability column?
    classes: list = field(default_factory=list)
    sample_shape: tuple = (0, 0)


def resolve_roles(train: pd.DataFrame, sample: pd.DataFrame) -> TaskRoles:
    """Derive id/target/problem-type from the sample submission + train frame.

    The sample submission's first column is the row identifier and its remaining
    column(s) are what must be predicted — this is the template contract, not a
    name guess.  Whether the target is a class label or a probability is read
    from the training target's own values, never assumed."""
    id_col = sample.columns[0]
    target_col = sample.columns[1] if len(sample.columns) > 1 else sample.columns[0]
    # The training frame carries the real target values under the same name.
    if target_col not in train.columns:
        # Some competitions name the sample column differently from train; fall
        # back to "the train column absent from the sample id" heuristic.
        cand = [c for c in train.columns if c != id_col
                and c not in sample.columns]
        target_col = cand[-1] if cand else target_col
    y = train[target_col] if target_col in train.columns else None
    proba = False
    problem = "classification"
    classes: list = []
    if y is not None:
        nun = y.nunique(dropna=True)
        is_float = pd.api.types.is_float_dtype(y)
        # A probability-style submission: sample values strictly inside (0,1).
        samp_target = sample[sample.columns[-1]]
        if pd.api.types.is_float_dtype(samp_target) and \
                ((samp_target > 0) & (samp_target < 1)).mean() > 0.3:
            proba, problem = True, "classification"
            classes = sorted(y.dropna().unique().tolist())
        elif is_float and nun > 20:
            problem = "regression"
        else:
            problem = "classification"
            classes = sorted(y.dropna().unique().tolist())
    return TaskRoles(id_col=id_col, target_col=target_col, problem=problem,
                     proba=proba, classes=classes, sample_shape=sample.shape)


# ---------------------------------------------------------------------------
# Estimator selection — the loop's proposals choose; a default catches the rest.
# ---------------------------------------------------------------------------

_ESTIMATOR_WORDS = {
    "lightgbm": "lightgbm", "lgbm": "lightgbm", "gbm": "lightgbm",
    "xgboost": "xgboost", "xgb": "xgboost",
    "histgradientboosting": "hgb", "hgb": "hgb", "gradient": "hgb",
    "randomforest": "rf", "random_forest": "rf", "forest": "rf",
    "logistic": "logreg", "logreg": "logreg", "linear": "linear",
    "ridge": "ridge",
}


#: Words that NAME a family outright ("lightgbm") outrank words that merely
#: describe a family of families ("gradient", "forest", "linear"). Measured
#: 2026-08-24: a live model answered "Use **LightGBM** (gradient-boosted
#: trees)", the distiller collected words in text order as
#: ['gradient boosting', 'lightgbm', ...], and first-match-wins returned hgb —
#: the model's explicit recommendation was overridden by an incidental word
#: INSIDE its own explanation of that recommendation. Specificity, not
#: position, decides.
_GENERIC_ESTIMATOR_WORDS = frozenset(
    {"gradient", "forest", "linear", "gbm"})


def estimator_from_moves(proposed_keys: Sequence[str], problem: str) -> str:
    """Read an estimator choice out of the loop's proposed move keys.

    Move keys look like ``estimator=lightgbm`` or ``model=random_forest``. The
    MOST SPECIFIC recognised family wins, not the first one seen: an explicit
    family name beats a generic descriptor, and among equals the earlier key
    wins. With no recognised proposal we return the deterministic default so
    the executor always has a real model to run."""
    best = None                       # (specific?, -position, family)
    for pos, key in enumerate(proposed_keys):
        low = key.lower()
        for word, fam in _ESTIMATOR_WORDS.items():
            if word not in low:
                continue
            rank = (word not in _GENERIC_ESTIMATOR_WORDS, -pos)
            if best is None or rank > best[0]:
                best = (rank, fam)
    return best[1] if best else "hgb"               # strong tabular default


def _build_estimator(family: str, problem: str, *, conservative: bool = False):
    """Construct a real fitted-capable estimator for the chosen family.

    ``conservative`` dials capacity DOWN — fewer trees, shallower, stronger
    regularisation, larger leaf minimums.  It is set when the data is small or
    when the council explicitly asked for a "regularized" / "conservative" model;
    on a ~900-row set an unregularised 400-tree booster overfits and loses to a
    simpler model, so honouring that guidance is executing the council's advice,
    not ignoring it."""
    clf = problem == "classification"
    n_est = 200 if conservative else 400
    lr = 0.05 if conservative else 0.03
    if family == "lightgbm":
        import lightgbm as lgb
        kw = dict(n_estimators=n_est, learning_rate=lr, verbose=-1)
        if conservative:
            kw.update(num_leaves=15, min_child_samples=30, subsample=0.8,
                      colsample_bytree=0.8, reg_lambda=1.0, subsample_freq=1)
        else:
            kw.update(num_leaves=31, subsample=0.8, colsample_bytree=0.8)
        return lgb.LGBMClassifier(**kw) if clf else lgb.LGBMRegressor(**kw)
    if family == "xgboost":
        import xgboost as xgb
        kw = dict(n_estimators=n_est, learning_rate=lr,
                  max_depth=3 if conservative else 5, subsample=0.8,
                  colsample_bytree=0.8,
                  reg_lambda=2.0 if conservative else 1.0)
        if clf:
            kw["eval_metric"] = "logloss"
        return xgb.XGBClassifier(**kw) if clf else xgb.XGBRegressor(**kw)
    if family == "rf":
        from sklearn.ensemble import (RandomForestClassifier,
                                      RandomForestRegressor)
        kw = dict(n_estimators=n_est, n_jobs=-1, random_state=0,
                  min_samples_leaf=5 if conservative else 1)
        return (RandomForestClassifier(**kw) if clf
                else RandomForestRegressor(**kw))
    if family in ("logreg", "linear", "ridge"):
        from sklearn.linear_model import (LogisticRegression, Ridge)
        return (LogisticRegression(max_iter=2000)
                if clf else Ridge())
    # default: histogram gradient boosting
    from sklearn.ensemble import (HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor)
    kw = dict(random_state=0)
    if conservative:
        kw.update(max_leaf_nodes=15, min_samples_leaf=30, l2_regularization=1.0)
    return (HistGradientBoostingClassifier(**kw) if clf
            else HistGradientBoostingRegressor(**kw))


# ---------------------------------------------------------------------------
# Feature preparation — the deterministic tabular reflexes, executed.
# ---------------------------------------------------------------------------


_TITLE_RE = re.compile(r",\s*([A-Za-z][A-Za-z /]+?)\.")
_TITLE_HAS = re.compile(r",\s*[A-Za-z][A-Za-z /]+?\.")     # group-free detector
_DECK_RE = re.compile(r"^([A-Za-z])\s*\d")
_DECK_HAS = re.compile(r"^[A-Za-z]\s*\d")                  # group-free detector


def _engineer_features(train: pd.DataFrame, test: pd.DataFrame, roles: TaskRoles,
                       proposed_keys: Sequence[str]) -> tuple:
    """Execute the feature-engineering the council PROPOSED — generically.

    The council proposes patterns by name ("title", "family", "missingness",
    "deck"); this executes each *only when the pattern is actually detectable* in
    the data, never by a hard-coded column name (the reusable-architecture gate:
    no convenient-column-name dispatch).  A title is extracted from whatever
    object column carries a ``", Xxx."`` honorific; a deck from whatever object
    column carries a ``letter+digits`` cabin code; missingness indicators from
    whatever columns actually have missing values.  Returns the augmented frames
    and the list of engineered columns (for the receipt)."""
    kt = " ".join(proposed_keys).lower()
    tr, te = train.copy(), test.copy()
    added: list[str] = []
    obj_cols = [c for c in tr.columns
                if c not in (roles.id_col, roles.target_col)
                and tr[c].dtype == object]

    # Title: the single highest-value Titanic feature, detected by honorific.
    if any(w in kt for w in ("title", "honorif", "name")):
        for c in obj_cols:
            frac = tr[c].dropna().astype(str).str.contains(_TITLE_HAS).mean()
            if frac > 0.6:                       # this column carries honorifics
                def _title(s):
                    m = _TITLE_RE.search(str(s))
                    t = m.group(1).strip() if m else "None"
                    # coarse-grain the long tail to the well-known buckets
                    if t in ("Mr", "Mrs", "Miss", "Master"):
                        return t
                    if t in ("Mme", "Ms", "Lady", "Mlle", "Countess", "Dona"):
                        return "Miss" if t in ("Mlle", "Ms") else "Mrs"
                    return "Rare"
                tr["title__" + c] = tr[c].map(_title)
                te["title__" + c] = te[c].map(_title)
                added.append("title__" + c)
                break

    # Deck: first letter of a cabin-like alphanumeric code.
    if any(w in kt for w in ("deck", "cabin")):
        for c in obj_cols:
            frac = tr[c].dropna().astype(str).str.contains(_DECK_HAS).mean()
            if frac > 0.4:
                tr["deck__" + c] = tr[c].astype(str).str.extract(
                    _DECK_RE, expand=False).fillna("U")
                te["deck__" + c] = te[c].astype(str).str.extract(
                    _DECK_RE, expand=False).fillna("U")
                added.append("deck__" + c)
                break

    # Family size: sum of the small non-negative integer "count" columns.
    if any(w in kt for w in ("family", "sibsp", "parch", "household")):
        count_cols = [c for c in tr.columns
                      if c not in (roles.id_col, roles.target_col)
                      and pd.api.types.is_integer_dtype(tr[c])
                      and tr[c].min() >= 0 and tr[c].max() <= 12
                      and tr[c].nunique() > 1]
        if len(count_cols) >= 2:
            tr["family_size"] = tr[count_cols].sum(axis=1) + 1
            te["family_size"] = te[count_cols].sum(axis=1) + 1
            tr["is_alone"] = (tr["family_size"] == 1).astype(int)
            te["is_alone"] = (te["family_size"] == 1).astype(int)
            added.extend(["family_size", "is_alone"])

    # Numeric interactions: ratios and products between columns the advice
    # actually NAMES.
    #
    # Added 2026-08-24 from a measured gap. A live model answered with
    # "usage_ratio = total_usage_hours / (days_since_first_use + 1)" — concrete,
    # correct, and naming real columns — and the executor engineered NOTHING,
    # because every pattern it knew (title, deck, family, missingness) was
    # shaped by one Titanic-like dataset. The vocabulary, not the advice, was
    # the limit: a closed list returns "nothing" for whatever it was not told
    # about, which reads as "the model had no useful ideas".
    #
    # Detection stays generic: a column participates because the advice names
    # it AND it is numeric in the data — never because of a hard-coded name.
    if any(w in kt for w in ("ratio", "per ", "/", "*", "product", "divide",
                             "interact", "rate", "times")):
        num_cols = [c for c in tr.columns
                    if c not in (roles.id_col, roles.target_col)
                    and pd.api.types.is_numeric_dtype(tr[c])
                    and c in te.columns]
        named = [c for c in num_cols if c.lower() in kt]
        # Pair the named columns in the order the advice mentions them, so
        # "A / B" builds A/B rather than an arbitrary pairing. Capped at three
        # engineered pairs: an unbounded interaction sweep is a different
        # (and much more expensive) technique than executing stated advice.
        named.sort(key=lambda c: kt.index(c.lower()))
        for a, b in zip(named, named[1:]):
            if len(added) >= 12:
                break
            denom_tr, denom_te = tr[b].astype(float), te[b].astype(float)
            # +1 shift only when the denominator actually reaches zero, so a
            # column that never does keeps its natural scale
            if (denom_tr == 0).any() or (denom_te == 0).any():
                denom_tr, denom_te = denom_tr + 1.0, denom_te + 1.0
            name = f"ratio__{a}__{b}"
            tr[name] = tr[a].astype(float) / denom_tr
            te[name] = te[a].astype(float) / denom_te
            added.append(name)
            if any(w in kt for w in ("product", "*", "times", "interact")):
                pname = f"product__{a}__{b}"
                tr[pname] = tr[a].astype(float) * tr[b].astype(float)
                te[pname] = te[a].astype(float) * te[b].astype(float)
                added.append(pname)

    # Missingness indicators: fully general, for any column with real gaps.
    if any(w in kt for w in ("missing", "indicator", "nan", "impute")):
        for c in list(tr.columns):
            if c in (roles.id_col, roles.target_col) or c.startswith(
                    ("title__", "deck__")):
                continue
            if tr[c].isna().mean() > 0.05:
                tr[c + "__isna"] = tr[c].isna().astype(int)
                te[c + "__isna"] = (te[c].isna().astype(int)
                                    if c in te.columns else 0)
                added.append(c + "__isna")

    return tr, te, added


def _prepare_features(train: pd.DataFrame, test: pd.DataFrame, roles: TaskRoles):
    """Impute + encode into numeric matrices — the tabular reflexes the loop
    proposes ("handle missing", "encode categoricals"), actually carried out.

    High-cardinality free-text columns (names, tickets) are dropped rather than
    exploded; low-cardinality object columns are one-hot encoded; numbers are
    median-imputed.  Deterministic and leakage-safe: encoders are fit on train
    and applied to test, and the target/id never enter the feature matrix."""
    drop = {roles.id_col, roles.target_col}
    feat_cols = [c for c in train.columns if c not in drop]
    Xtr, Xte = train[feat_cols].copy(), test[feat_cols].copy() if \
        all(c in test.columns for c in feat_cols) else \
        test.reindex(columns=feat_cols).copy()
    used: list[str] = []
    frames_tr, frames_te = [], []
    for c in feat_cols:
        s_tr = Xtr[c]
        if pd.api.types.is_numeric_dtype(s_tr):
            med = s_tr.median()
            frames_tr.append(s_tr.fillna(med).rename(c))
            frames_te.append(Xte[c].fillna(med).rename(c))
            used.append(c)
        else:
            nun = s_tr.nunique(dropna=True)
            if nun > 20:                       # high-cardinality free text: drop
                continue
            dummies_tr = pd.get_dummies(s_tr.astype("string").fillna("NA"),
                                        prefix=c)
            dummies_te = pd.get_dummies(Xte[c].astype("string").fillna("NA"),
                                        prefix=c)
            dummies_te = dummies_te.reindex(columns=dummies_tr.columns,
                                            fill_value=0)
            frames_tr.append(dummies_tr)
            frames_te.append(dummies_te)
            used.extend(dummies_tr.columns.tolist())
    Mtr = pd.concat(frames_tr, axis=1).astype(float) if frames_tr else \
        pd.DataFrame(index=train.index)
    Mte = pd.concat(frames_te, axis=1).astype(float) if frames_te else \
        pd.DataFrame(index=test.index)
    Mte = Mte.reindex(columns=Mtr.columns, fill_value=0.0)
    return Mtr.values, Mte.values, list(Mtr.columns)


# ---------------------------------------------------------------------------
# The executor — plan in, real submission file + honest local score out.
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    family: str
    problem: str
    local_metric: str
    local_score: float
    n_features: int
    n_train: int
    n_test: int
    submission_path: str
    id_col: str
    target_col: str
    engineered: list = field(default_factory=list)


def execute_tabular(train_csv: str, test_csv: str, sample_csv: str,
                    out_csv: str, *, proposed_keys: Sequence[str] = (),
                    folds: int = 5,
                    output_probabilities: "bool | None" = None
                    ) -> ExecutionResult:
    """Execute a tabular plan end to end and write a submittable file.

    ``proposed_keys`` are the loop's proposed move keys; they steer the estimator
    choice.  Returns an honest cross-validated local score alongside the written
    path — the local score is what we know before Kaggle grades the hidden half.

    ``output_probabilities`` overrides the sample-derived shape: pass True when
    the OFFICIAL metric is a ranking metric (ROC-AUC) even though the sample
    shows hard labels — probabilities score strictly better under AUC.  The
    local metric then switches to out-of-fold ROC-AUC so the number we quote is
    the number the leaderboard grades (the metric-confirmation rule)."""
    from sklearn.model_selection import (StratifiedKFold, KFold,
                                         cross_val_predict, cross_val_score)
    from sklearn.metrics import accuracy_score, roc_auc_score

    train = pd.read_csv(train_csv)
    test = pd.read_csv(test_csv)
    sample = pd.read_csv(sample_csv)
    roles = resolve_roles(train, sample)
    family = estimator_from_moves(proposed_keys, roles.problem)

    # Execute the council's proposed feature engineering (generically detected),
    # then impute + encode the augmented frames.
    train, test, engineered = _engineer_features(train, test, roles,
                                                 proposed_keys)
    y = train[roles.target_col].values
    Xtr, Xte, cols = _prepare_features(train, test, roles)
    # Conservative capacity when the data is small OR the council asked for a
    # regularized/conservative/robust model — small tabular sets overfit big
    # boosters, and the council flagged exactly this risk on Titanic.
    kt = " ".join(proposed_keys).lower()
    conservative = (len(train) < 5000
                    or any(w in kt for w in ("regular", "conservativ", "robust",
                                             "shrink", "penal")))
    est = _build_estimator(family, roles.problem, conservative=conservative)

    # Honest local score by cross-validation (no leakage: folds are internal).
    # For a hard-label submission we report ACCURACY — the metric the leaderboard
    # actually grades — because a healthy roc_auc (a ranking metric) can hide a
    # poor accuracy, which is exactly how the first Titanic run misled us.
    # When probabilities are the shipped artifact, the honest local metric is
    # out-of-fold ROC-AUC: quote what the leaderboard grades, never a proxy.
    force_proba = (roles.proba if output_probabilities is None
                   else bool(output_probabilities))
    if roles.problem == "classification" and force_proba:
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
        oof = cross_val_predict(est, Xtr, y, cv=cv, method="predict_proba")
        local_metric = "roc_auc"
        local_score = float(roc_auc_score(
            y, oof[:, 1] if oof.shape[1] == 2 else oof, multi_class="ovr"))
    elif roles.problem == "classification":
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=0)
        pred = cross_val_predict(est, Xtr, y, cv=cv)
        local_metric, local_score = "accuracy", float(accuracy_score(y, pred))
    else:
        cv = KFold(n_splits=folds, shuffle=True, random_state=0)
        scores = cross_val_score(est, Xtr, y, cv=cv,
                                 scoring="neg_root_mean_squared_error")
        local_metric, local_score = "rmse", float(-scores.mean())

    # Fit on all of train, predict test, write in the template's exact shape.
    est.fit(Xtr, y)
    sub = sample.copy()
    if force_proba and hasattr(est, "predict_proba"):
        p = est.predict_proba(Xte)
        sub[sub.columns[-1]] = p[:, 1] if p.shape[1] == 2 else p.max(1)
    else:
        preds = est.predict(Xte)
        if roles.problem == "classification":
            preds = preds.astype(train[roles.target_col].dtype)
        sub[sub.columns[-1]] = preds
    sub.to_csv(out_csv, index=False)

    return ExecutionResult(
        family=family, problem=roles.problem, local_metric=local_metric,
        local_score=local_score, n_features=len(cols), n_train=len(train),
        n_test=len(test), submission_path=out_csv, id_col=roles.id_col,
        target_col=roles.target_col, engineered=engineered)


# ---------------------------------------------------------------------------
# Self-test — offline, synthetic tabular data, no network and no real files.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    import tempfile, os
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # --- both of these lock in defects MEASURED on a live model answer
    # (2026-08-24, playground-series-s6e8). Each made the model's advice
    # unable to change the prediction, so a model arm produced a submission
    # byte-identical to the zero-model arm while still billing tokens.

    # 1. SPECIFICITY BEATS POSITION. The live answer was "Use **LightGBM**
    # (gradient-boosted trees)"; keys distilled in text order as
    # ['gradient boosting', 'lightgbm', ...] and first-match-wins returned hgb
    # — the recommendation overridden by a word inside its own explanation.
    check("an_explicit_family_beats_a_generic_word_seen_earlier",
          estimator_from_moves(("gradient boosting", "lightgbm", "xgboost"),
                               "classification") == "lightgbm"
          and estimator_from_moves(("gradient boosting",),
                                   "classification") == "hgb"
          and estimator_from_moves(("hist_gradient_boosting",),
                                   "classification") == "hgb"
          and estimator_from_moves((), "classification") == "hgb",
          "'lightgbm' outranks the 'gradient' inside its own explanation; "
          "generic-only and empty still fall back to the default")

    # 2. THE FEATURE VOCABULARY IS NOT ONE DATASET'S SHAPE. The live answer
    # proposed "usage_ratio = total_usage_hours / (days_since_first_use + 1)"
    # and the executor engineered nothing, because every pattern it knew came
    # from a Titanic-like set. A closed list answers "nothing" for whatever it
    # was never told about, which reads as the model having had no ideas.
    _ftr = pd.DataFrame({"id": range(20), "hours": np.arange(20.) + 1.0,
                         "days": np.arange(20.), "y": [0, 1] * 10})
    _fte = _ftr.drop(columns="y").copy()
    _fsa = pd.DataFrame({"id": range(20), "y": [0] * 20})
    _froles = resolve_roles(_ftr, _fsa)
    _, _, _named = _engineer_features(
        _ftr, _fte, _froles, ("ratio = hours / (days + 1)",))
    _, _, _unnamed = _engineer_features(
        _ftr, _fte, _froles, ("hist_gradient_boosting", "default features"))
    check("advice_that_names_real_numeric_columns_engineers_a_feature",
          _named == ["ratio__hours__days"] and _unnamed == [],
          "a ratio between named numeric columns is built; advice naming "
          "nothing engineers nothing")

    rng = np.random.default_rng(0)
    n = 300
    df = pd.DataFrame({
        "id": np.arange(n),
        "num": rng.normal(size=n),
        "cat": rng.choice(["a", "b", "c"], size=n),
        "text": [f"free text {i}" for i in range(n)],   # high-cardinality: drop
    })
    df["y"] = ((df["num"] + (df["cat"] == "a") * 1.5
                + rng.normal(scale=0.5, size=n)) > 0).astype(int)
    tr = df.iloc[:200].copy()
    te = df.iloc[200:].drop(columns=["y"]).copy()
    samp = pd.DataFrame({"id": te["id"], "y": 0})

    with tempfile.TemporaryDirectory() as d:
        p_tr = os.path.join(d, "train.csv"); tr.to_csv(p_tr, index=False)
        p_te = os.path.join(d, "test.csv"); te.to_csv(p_te, index=False)
        p_sa = os.path.join(d, "samp.csv"); samp.to_csv(p_sa, index=False)
        p_out = os.path.join(d, "sub.csv")

        roles = resolve_roles(tr, samp)
        check("roles_resolve_id_and_target_from_the_sample_submission",
              roles.id_col == "id" and roles.target_col == "y"
              and roles.problem == "classification",
              f"id={roles.id_col} target={roles.target_col} "
              f"problem={roles.problem}")

        fam = estimator_from_moves(["estimator=lightgbm"], "classification")
        check("an_estimator_proposal_is_read_from_the_moves",
              fam == "lightgbm",
              "a move key of estimator=lightgbm selects the lightgbm family")

        check("no_proposal_falls_back_to_a_real_default_estimator",
              estimator_from_moves([], "classification") == "hgb",
              "with no estimator proposed the executor still has a real default")

        res = execute_tabular(p_tr, p_te, p_sa, p_out,
                              proposed_keys=["estimator=random_forest"], folds=3)
        out = pd.read_csv(p_out)
        check("the_executor_writes_a_file_in_the_templates_exact_shape",
              list(out.columns) == ["id", "y"] and len(out) == len(te),
              f"submission has columns {list(out.columns)} and {len(out)} rows")

        check("the_high_cardinality_text_column_was_dropped_not_exploded",
              res.n_features <= 6,
              f"{res.n_features} features — the free-text column did not explode "
              f"into 200 one-hot columns")

        check("the_local_score_is_a_real_cross_validated_number",
              0.6 <= res.local_score <= 1.0 and res.local_metric in
              ("roc_auc", "accuracy"),
              f"local {res.local_metric}={res.local_score:.4f} on a learnable "
              f"synthetic signal")


        # the probability override: forced proba writes floats in (0,1) and the
        # local metric becomes out-of-fold ROC-AUC — quote what an AUC
        # leaderboard grades, never a proxy (the metric-confirmation rule).
        p_out2 = p_out.replace(".csv", "_proba.csv")
        res_p = execute_tabular(p_tr, p_te, p_sa, p_out2,
                                output_probabilities=True)
        import pandas as _pd
        sub_p = _pd.read_csv(p_out2)
        vals = sub_p[sub_p.columns[-1]]
        check("probability_override_ships_floats_and_scores_roc_auc",
              res_p.local_metric == "roc_auc" and 0.5 < res_p.local_score <= 1.0
              and vals.dtype.kind == "f"
              and float(vals.min()) >= 0.0 and float(vals.max()) <= 1.0
              and vals.nunique() > 2,
              f"oof roc_auc={res_p.local_score:.4f}; submission column is "
              "continuous probabilities")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "kaggle_executor_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
