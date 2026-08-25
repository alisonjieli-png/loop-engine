"""Competition solver — a Kaggle competition solved BY the practitioner kernel.

Owner directive (2026-08-23): move all code and logic to flow through the
practitioner architecture.  This is that bridge for the competition family: the
tabular executor, the image executor, and (later) the RL/policy vocabulary stop
being scripts called beside the kernel and become NODES the kernel selects, with
``review_mode`` as its verify step and the six-node loop as the only control flow.

One competition = one ``ProblemSpec`` whose success criterion is "a valid,
non-degenerate submission".  The kernel then:

  1. Understand … -> resolve the competition (modality, id/target, metric) from
     its own sample_submission (the file-role contract, never a guessed name).
  2. Select the next action -> produce a submission (or, if the current one is
     degenerate, improve it).
  3. Determine how -> reuse-first (a fitted-model artifact already?), else pick
     the executor node for the detected modality.
  4. Execute -> the executor writes submission.csv and returns its predictions.
  5. Verify -> review_mode interrogates the submission: constant? chance-level?
     A degenerate submission is NOT accepted.
  6. Save/route -> accept a real submission and stop; else improve.

The executors are ordinary functions with one contract
(``execute(comp) -> ExecOutcome``), so a new modality is one registered node.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

from ..loop.kernel import (ProblemSpec, PractitionerState, Situation,
                     CandidateAction, ExecutionPlan, ResultPacket,
                     EvaluationPacket, RouteDecision, PassRecord, run_practitioner)
from ..code_nodes.review_mode import review

MODALITIES = ("tabular", "image", "text")


# ---------------------------------------------------------------------------
# Resolve a downloaded competition into a spec (file-role contract).
# ---------------------------------------------------------------------------


@dataclass
class CompetitionSpec:
    data_dir: str
    id_col: str
    target_cols: list
    problem: str                 # classification | regression | multilabel
    modality: str
    metric: str
    out_path: str = "submission.csv"


def _find(data_dir: str, *names) -> "str | None":
    for n in names:
        p = os.path.join(data_dir, n)
        if os.path.exists(p):
            return p
    return None


def resolve_competition(data_dir: str, *, metric: str = "accuracy"
                        ) -> CompetitionSpec:
    """Resolve id/target/modality/problem from the competition's own files."""
    sample_p = _find(data_dir, "sample_submission.csv", "gender_submission.csv")
    train_p = _find(data_dir, "train.csv")
    if not sample_p or not train_p:
        raise FileNotFoundError(f"need train.csv + sample_submission under "
                                f"{data_dir}")
    sample = pd.read_csv(sample_p)
    train = pd.read_csv(train_p)
    id_col = sample.columns[0]
    target_cols = [c for c in sample.columns if c != id_col]
    y = train[target_cols[0]] if target_cols[0] in train.columns else None
    problem = "classification"
    if len(target_cols) > 1:
        problem = "multilabel"
    elif y is not None and pd.api.types.is_float_dtype(y) and y.nunique() > 20:
        problem = "regression"

    # modality: pixel-named or a wide 0-255 integer matrix -> image.
    feat_cols = [c for c in train.columns if c not in ([id_col] + target_cols)]
    pixelish = sum(1 for c in feat_cols if re.match(r"pixel\d+$", str(c)))
    wide_bytes = (len(feat_cols) >= 200 and
                  all(pd.api.types.is_integer_dtype(train[c])
                      for c in feat_cols[:20]) and
                  int(train[feat_cols[:50]].max().max()) <= 255)
    modality = ("image" if (pixelish >= 0.5 * max(1, len(feat_cols))
                            or wide_bytes) else "tabular")
    return CompetitionSpec(data_dir=data_dir, id_col=id_col,
                           target_cols=target_cols, problem=problem,
                           modality=modality, metric=metric)


# ---------------------------------------------------------------------------
# Executor nodes — one contract: execute(comp) -> ExecOutcome.
# ---------------------------------------------------------------------------


@dataclass
class ExecOutcome:
    submission_path: str
    predictions: list
    local_metric: str
    local_score: float
    majority_prevalence: float
    n_features: int
    estimator: str


def _prep_xy(comp: CompetitionSpec):
    train = pd.read_csv(_find(comp.data_dir, "train.csv"))
    test = pd.read_csv(_find(comp.data_dir, "test.csv"))
    sample = pd.read_csv(_find(comp.data_dir, "sample_submission.csv",
                               "gender_submission.csv"))
    feat = [c for c in train.columns
            if c not in ([comp.id_col] + comp.target_cols)]
    feat = [c for c in feat if c in test.columns]
    return train, test, sample, feat


def execute_image(comp: CompetitionSpec) -> ExecOutcome:
    """Image executor: normalise pixel matrices and classify.  For the
    pixel-CSV image competitions (MNIST-family) a calibrated gradient-boosting
    classifier on normalised pixels is a fast, honest node; a conv net can be a
    stronger registered alternative later."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    train, test, sample, feat = _prep_xy(comp)
    tgt = comp.target_cols[0]
    X = train[feat].values.astype(np.float32) / 255.0
    y = train[tgt].values
    Xte = test[feat].reindex(columns=feat, fill_value=0).values.astype(
        np.float32) / 255.0
    est = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.1,
                                         random_state=0)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=0)
    score = float(cross_val_score(est, X, y, cv=cv, scoring="accuracy").mean())
    est.fit(X, y)
    preds = est.predict(Xte)
    sub = sample.copy()
    sub[comp.target_cols[0]] = preds.astype(train[tgt].dtype)
    sub = sub[sample.columns]
    out = os.path.join(comp.data_dir, comp.out_path)
    sub.to_csv(out, index=False)
    maj = float(pd.Series(y).value_counts(normalize=True).max())
    return ExecOutcome(out, preds.tolist(), "accuracy", score, maj,
                       len(feat), "hist_gradient_boosting")


def execute_tabular(comp: CompetitionSpec) -> ExecOutcome:
    """Tabular executor: delegates to the tested kaggle_executor."""
    from ..code_nodes.kaggle_executor import execute_tabular as _exec
    train_p = _find(comp.data_dir, "train.csv")
    test_p = _find(comp.data_dir, "test.csv")
    samp_p = _find(comp.data_dir, "sample_submission.csv",
                   "gender_submission.csv")
    out = os.path.join(comp.data_dir, comp.out_path)
    res = _exec(train_p, test_p, samp_p, out)
    sub = pd.read_csv(out)
    train = pd.read_csv(train_p)
    tgt = comp.target_cols[0]
    maj = (float(pd.Series(train[tgt]).value_counts(normalize=True).max())
           if tgt in train.columns and comp.problem != "regression" else 0.0)
    return ExecOutcome(out, sub[comp.target_cols[0]].tolist(),
                       res.local_metric, res.local_score, maj,
                       res.n_features, res.family)


EXECUTORS = {"image": execute_image, "tabular": execute_tabular}


# ---------------------------------------------------------------------------
# The executors as SEARCHABLE, FINDABLE resources — the practitioner discovers
# them through the strict search/serve DAG, never a hardcoded dispatch.
# ---------------------------------------------------------------------------


def executor_node_records() -> list:
    """Each executor as a store record (kind=node) with a capability
    description + typed handle, so 'find me a node that classifies images'
    resolves through the same search DAG as every other resource."""
    from ..static_architecture.store_serve import StoreRecord
    return [
        StoreRecord(
            "node.executor.image", "node",
            "image classification executor for pixel-matrix competitions",
            body={"handle": "executor:image",
                  "capability": "classify images (pixel matrices) into labels",
                  "inputs": "pixel matrix per row", "outputs": "label per row"},
            tags=("executor", "image", "classification", "vision", "pixels")),
        StoreRecord(
            "node.executor.tabular", "node",
            "tabular classification and regression executor",
            body={"handle": "executor:tabular",
                  "capability": "fit a model on tabular features and predict",
                  "inputs": "tabular feature rows",
                  "outputs": "prediction per row"},
            tags=("executor", "tabular", "classification", "regression")),
    ]


def build_competition_store(extra=()):
    """The resource store the practitioner searches — core seed + executor
    nodes + any organisation-supplied extras."""
    from ..static_architecture.store_serve import SolverStore, core_seed
    return SolverStore(core_records=list(core_seed())
                       + executor_node_records() + list(extra))


def find_executor(store, modality: str):
    """Search the store for a compatible executor node; return (record, handle)
    or (None, "").  This is the 'do we already have a node for this?' step —
    answered by capability search, not a dict lookup."""
    from ..loop.intelligence_loops import search_as_loop, serve_record_as_loop
    hits = search_as_loop(store, f"{modality} classification executor",
                          pillar="code_intelligence", kind="node",
                          top_n=5)["value"]["hits"]
    for h in hits:
        rec = serve_record_as_loop(store, h["record_id"],
                                   pillar="code_intelligence")["value"]
        if rec and (modality in rec.title.lower()
                    or modality in " ".join(rec.tags).lower()):
            return rec, rec.body.get("handle", "")
    return None, ""


# ---------------------------------------------------------------------------
# Kernel node implementations — the competition solved through the six nodes.
# ---------------------------------------------------------------------------


def make_competition_impls(comp: CompetitionSpec, store=None) -> dict:
    """Six-node kernel implementations that solve ``comp``.

    ``store`` is the resource store the practitioner SEARCHES to find its
    executor node; a default store with the executors registered is built when
    none is given, so the discovery path is exercised either way."""
    store = store if store is not None else build_competition_store()

    def orient(state: PractitionerState) -> Situation:
        have_sub = bool(state.artifacts.get("submission"))
        degenerate = bool(state.facts.get("submission_degenerate"))
        unmet = () if (have_sub and not degenerate) else ("valid_submission",)
        signals = ["submission_degenerate"] if degenerate else []
        return Situation(
            summary=f"{comp.modality} {comp.problem}; submission="
            f"{'yes' if have_sub else 'no'} degenerate={degenerate}",
            knowns=dict(state.facts), unknowns=unmet, signals=tuple(signals))

    def select_next_action(state: PractitionerState,
                           situation: Situation) -> list:
        if not situation.unknowns:
            return [CandidateAction("deliver", kind="deliver",
                                    rationale="a valid, non-degenerate "
                                    "submission exists", expected_value=1.0,
                                    confidence=0.95)]
        if "submission_degenerate" in situation.signals:
            return [CandidateAction(
                "improve_submission", kind="task",
                rationale="the current submission is degenerate — a stronger "
                "estimator/features are next", expected_value=0.95,
                confidence=0.7)]
        return [CandidateAction(
            f"produce_submission:{comp.modality}", kind="task",
            rationale=f"run the {comp.modality} executor to a submission",
            expected_value=0.9, confidence=0.8)]

    def how(state: PractitionerState, situation: Situation,
            chosen: CandidateAction) -> ExecutionPlan:
        if chosen.kind == "deliver":
            return ExecutionPlan("use", "run_direct", handle="deliver")
        # reuse-first via SEARCH: find a node whose capability matches the
        # modality (the practitioner discovers it, it is not hardcoded).
        rec, handle = find_executor(store, comp.modality)
        if rec is None or handle not in (f"executor:{m}" for m in EXECUTORS):
            return ExecutionPlan("generate", "run_dag",
                                 handle=f"author_executor:{comp.modality}",
                                 rationale="no executor node found in the store "
                                 "for this modality — author one")
        return ExecutionPlan("use", "run_direct", handle=handle,
                             rationale=f"found node {rec.record_id} via "
                             f"capability search")

    def act(state: PractitionerState, plan: ExecutionPlan) -> list:
        if not plan.handle.startswith("executor:"):
            return [ResultPacket(objective=plan.handle,
                                 result={"delivered": True}, confidence=0.9)]
        modality = plan.handle.split(":", 1)[1]
        outcome = EXECUTORS[modality](comp)
        return [ResultPacket(
            objective="submission", result=outcome,
            artifact_refs=(outcome.submission_path,),
            metrics={"local_metric": outcome.local_metric,
                     "local_score": outcome.local_score},
            confidence=0.8, cost=1.0,
            claims=(f"estimator:{outcome.estimator}",))]

    def verify(state: PractitionerState, plan: ExecutionPlan,
               results: list) -> EvaluationPacket:
        if not results or not isinstance(results[0].result, ExecOutcome):
            return EvaluationPacket("accept", notes="delivered")
        oc: ExecOutcome = results[0].result
        rep = review(objective=f"win {comp.modality} competition",
                     input_summary=f"{comp.modality} {comp.problem}",
                     output_values=oc.predictions,
                     output_contract="submission.csv per the sample",
                     metric=oc.local_metric, score=oc.local_score,
                     majority_prevalence=oc.majority_prevalence)
        state.blackboard = getattr(state, "blackboard", {})
        if rep.verdict in ("degenerate", "fail"):
            return EvaluationPacket("repair", notes=f"review: {rep.verdict} — "
                                    f"{rep.plain_summary}")
        return EvaluationPacket("accept", notes=f"review: {rep.verdict} "
                                f"({oc.local_metric}={oc.local_score:.4f})")

    def learn_route(state: PractitionerState, rec: PassRecord) -> tuple:
        ev = rec.evaluation
        facts = dict(state.facts)
        artifacts = dict(state.artifacts)
        if ev and ev.verdict == "accept" and rec.results \
                and isinstance(rec.results[0].result, ExecOutcome):
            oc = rec.results[0].result
            artifacts["submission"] = oc.submission_path
            facts["met:valid_submission"] = True
            facts["local_score"] = oc.local_score
            facts.pop("submission_degenerate", None)
            return (RouteDecision("continue", "submission accepted"),
                    state.derive(facts=facts, artifacts=artifacts,
                                 last_route="continue"))
        if ev and ev.verdict == "accept" and rec.chosen \
                and rec.chosen.kind == "deliver":
            return (RouteDecision("stop_success", "delivered"),
                    state.derive(last_route="stop_success"))
        if ev and ev.verdict == "repair":
            facts["submission_degenerate"] = True
            failures = state.failures + (f"pass {rec.pass_number}: "
                                         f"{ev.notes}",)
            # a second degenerate result -> stop honestly rather than spin
            if state.last_route == "repair":
                return (RouteDecision("stop_unprofitable",
                                      "submission remained degenerate"),
                        state.derive(facts=facts, failures=failures,
                                     last_route="stop_unprofitable"))
            return (RouteDecision("repair", ev.notes),
                    state.derive(facts=facts, failures=failures,
                                 last_route="repair"))
        return (RouteDecision("stop_unprofitable", "no progress"),
                state.derive(last_route="stop_unprofitable"))

    return {"orient": orient, "decide_next": select_next_action, "how": how,
            "act": act, "verify": verify, "route": learn_route}


@dataclass
class CompetitionResult:
    slug: str
    submission_path: str
    local_metric: str
    local_score: float
    review_verdict: str
    passes: int
    final_route: str


def solve_competition(data_dir: str, *, slug: str = "", metric: str = "accuracy",
                      max_passes: int = 6) -> CompetitionResult:
    """Solve a downloaded competition THROUGH the practitioner kernel."""
    comp = resolve_competition(data_dir, metric=metric)
    spec = ProblemSpec(objective=f"win competition {slug or comp.modality}",
                       success_criteria=("valid_submission",),
                       budget_passes=max_passes)
    store = build_competition_store()
    out = run_practitioner(spec, make_competition_impls(comp, store=store),
                           max_passes=max_passes)
    sub = out["artifacts"].get("submission", "")
    score = float(out["facts"].get("local_score", 0.0))
    # one final review verdict for the record
    verdict = "pass" if out["facts"].get("met:valid_submission") else "unmet"
    return CompetitionResult(slug=slug or comp.modality, submission_path=sub,
                             local_metric=comp.metric, local_score=score,
                             review_verdict=verdict, passes=out["passes"],
                             final_route=out["final_route"])


# ---------------------------------------------------------------------------
# Self-test — offline, a tiny synthetic competition dir, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    import tempfile
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    rng = np.random.default_rng(0)

    with tempfile.TemporaryDirectory() as d:
        # a tiny TABULAR competition with real signal
        n = 240
        num = rng.normal(size=n)
        y = (num + rng.normal(scale=0.5, size=n) > 0).astype(int)
        tr = pd.DataFrame({"id": range(n), "f1": num,
                           "f2": rng.normal(size=n), "y": y})
        te = pd.DataFrame({"id": range(n, n + 60), "f1": rng.normal(size=60),
                           "f2": rng.normal(size=60)})
        pd.DataFrame(tr).to_csv(f"{d}/train.csv", index=False)
        pd.DataFrame(te).to_csv(f"{d}/test.csv", index=False)
        pd.DataFrame({"id": te["id"], "y": 0}).to_csv(
            f"{d}/sample_submission.csv", index=False)

        comp = resolve_competition(f"{d}")
        check("resolve_reads_id_target_modality_from_the_sample",
              comp.id_col == "id" and comp.target_cols == ["y"]
              and comp.modality == "tabular",
              f"id={comp.id_col} target={comp.target_cols} "
              f"modality={comp.modality}")

        res = solve_competition(f"{d}", slug="toy-tabular")
        sub = pd.read_csv(res.submission_path)
        check("the_kernel_solves_a_tabular_competition_end_to_end",
              res.final_route == "stop_success"
              and os.path.exists(res.submission_path)
              and list(sub.columns) == ["id", "y"] and len(sub) == 60,
              f"{res.passes} passes -> {res.final_route}; submission written")

        check("a_real_submission_passes_review_not_degenerate",
              res.review_verdict == "pass" and sub["y"].nunique() > 1
              and res.local_score > 0.6,
              f"review={res.review_verdict}, local acc={res.local_score:.3f}, "
              f"{sub['y'].nunique()} distinct predictions")

    # image modality detection on a pixel-named frame (a learnable signal:
    # the class is set by a small, clear region so HGB actually learns it).
    with tempfile.TemporaryDirectory() as d:
        m = 300
        px = rng.integers(0, 256, size=(m, 100))
        lab = (px[:, :10].mean(axis=1) > 128).astype(int)   # clear, learnable
        cols = {f"pixel{i}": px[:, i] for i in range(100)}
        cols["label"] = lab
        tr = pd.DataFrame(cols); tr.insert(0, "ImageId", range(m))
        te_px = rng.integers(0, 256, size=(60, 100))
        te = pd.DataFrame({f"pixel{i}": te_px[:, i] for i in range(100)})
        te.insert(0, "ImageId", range(m, m + 60))
        tr.to_csv(f"{d}/train.csv", index=False)
        te.to_csv(f"{d}/test.csv", index=False)
        pd.DataFrame({"ImageId": te["ImageId"], "label": 0}).to_csv(
            f"{d}/sample_submission.csv", index=False)
        comp2 = resolve_competition(f"{d}")
        check("pixel_named_wide_matrices_are_detected_as_image_modality",
              comp2.modality == "image",
              f"300 pixel columns -> modality {comp2.modality}")
        res2 = solve_competition(f"{d}", slug="toy-image")
        check("the_kernel_solves_an_image_competition_via_the_image_executor",
              res2.final_route == "stop_success"
              and os.path.exists(res2.submission_path)
              and res2.local_score > 0.6,
              f"image executor -> acc {res2.local_score:.3f} in {res2.passes} "
              f"passes")

    # a degenerate submission is caught by verify (review_mode) and NOT accepted
    with tempfile.TemporaryDirectory() as d:
        n = 120
        tr = pd.DataFrame({"id": range(n), "f1": rng.normal(size=n),
                           "y": rng.integers(0, 2, size=n)})   # pure noise
        te = pd.DataFrame({"id": range(n, n + 40),
                           "f1": rng.normal(size=40)})
        tr.to_csv(f"{d}/train.csv", index=False)
        te.to_csv(f"{d}/test.csv", index=False)
        pd.DataFrame({"id": te["id"], "y": 0}).to_csv(
            f"{d}/sample_submission.csv", index=False)
        comp3 = resolve_competition(f"{d}")
        impls = make_competition_impls(comp3)
        # force a constant prediction and confirm verify says repair
        oc = ExecOutcome("x", [1] * 40, "accuracy", 0.50, 0.5, 1, "e")
        ev = impls["verify"](PractitionerState(spec=ProblemSpec(objective="x")),
                             ExecutionPlan("use", "run_direct",
                                           handle="executor:tabular"),
                             [ResultPacket(objective="s", result=oc)])
        check("verify_uses_review_mode_to_reject_a_degenerate_submission",
              ev.verdict == "repair" and "degenerate" in ev.notes.lower(),
              "a constant chance-level submission is caught at verify, not "
              "shipped")

    # the executor node is FINDABLE via capability search — not hardcoded.
    store = build_competition_store()
    rec, handle = find_executor(store, "image")
    hit = store.search("classify images into labels", kind="node")
    check("executors_are_searchable_and_findable_resources",
          rec is not None and handle == "executor:image"
          and hit["hits"] and hit["hits"][0]["record_id"] == "node.executor.image",
          "the practitioner discovers the image executor by capability search, "
          "then incorporates it — never a hardcoded dispatch")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "competition_solver_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
