"""The Kaggle smoke-test ladder (§24) — the Loop proving ground.

Stage 0 runs a deterministic local fixture (synthetic tabular task) through a
REAL ``Loop`` end to end: data loading, baseline, validation, records — zero
model calls.  The Titanic stage runs the same loop shape with ONE visible
semantic model call (cloud-only, ``chat_maxout``, provider-reported tokens)
and can really submit.  The warm run replays the task family with the mined
advice served from the store — the growth gate: fewer model calls, more
code-served steps, same-or-better local score.

SMOKE ONLY: these runs prove the plumbing.  Playground/beginner tasks are
never presented as benchmark evidence; real active competitions remain the
evidence bar.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile

from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome

SMOKE_STEPS = ("orient", "research", "decide", "act", "verify", "commit")

#: estimator words the decide step can distill from advice text
_FAMILY_WORDS = ("hist_gradient_boosting", "gradient boosting", "hgb",
                 "random forest", "logistic", "lightgbm", "xgboost")


def _fixture(workdir: str) -> tuple:
    """A tiny DETERMINISTIC binary-classification task (seeded, no download):
    two informative numeric features + one categorical + noise."""
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(7)
    n, m = 240, 60
    def make(k, offset):
        x1 = rng.normal(0, 1, k)
        x2 = rng.normal(0, 1, k)
        cat = rng.choice(["a", "b", "c"], k)
        noise = rng.normal(0, 1, k)
        y = ((x1 + 0.8 * x2 + (cat == "a") * 0.9 + 0.35 * noise) > 0).astype(int)
        return pd.DataFrame({"row_id": np.arange(offset, offset + k),
                             "x1": x1, "x2": x2, "cat": cat, "noise": noise,
                             "target": y})
    train, test_full = make(n, 0), make(m, n)
    test = test_full.drop(columns=["target"])
    sample = test[["row_id"]].copy(); sample["target"] = 0
    paths = tuple(os.path.join(workdir, f) for f in
                  ("train.csv", "test.csv", "sample.csv", "out.csv"))
    train.to_csv(paths[0], index=False)
    test.to_csv(paths[1], index=False)
    sample.to_csv(paths[2], index=False)
    return paths


def _distill_keys(advice: str) -> tuple:
    """Deterministically distill estimator/feature keys from advice text."""
    low = advice.lower()
    keys = [w for w in _FAMILY_WORDS if w in low]
    for feat in re.findall(r"(?:feature|engineer|derive|extract)[^.\n]{0,80}",
                           low)[:3]:
        keys.append(feat.strip())
    return tuple(keys) or ("hist_gradient_boosting",)


#: the research-probe ranking backend — config, never code. "store" is the
#: behavior-identical baseline (the same idf ranking the lane always had);
#: "fts5"/"lancedb" are one flip away and change ONLY by winning a frozen-
#: query tournament on real smoke queries (the evidence-gated-adoption law).
RESEARCH_BACKEND = "store"


def _research_probe(store, query: str) -> list:
    """Research retrieval through the ONE Retriever plug, so the live
    lane fronts the same swappable contract as everything else. Bodies
    stay behind store.serve() — reference, not body."""
    from ..core.retrieval import Retriever
    from ..loop.intelligence_loops import records_as_loop
    return Retriever(records_as_loop(store)["value"],
                     lexical_backend=RESEARCH_BACKEND).search(
        query, mode="lexical")["hits"]


def _consult_pillars(loop, step: str, advice_store=None,
                     code_store=None, history_store=None) -> dict:
    """Consult the intelligence plane for this step, on the loop's ledger.

    All FOUR pillars, plus a capability search — the plane exists to be used
    while solving, and D-9 found a real solve touching none of it.

    Failures are swallowed deliberately: consulting intelligence must never
    be able to break a solve.  An unavailable pillar degrades the run's
    EVIDENCE, never its result — intelligence is meant to help solving, not
    to become a new way for solving to fail.  Returns what was consulted, so
    a caller can measure cold-versus-warm rather than assert it."""
    from ..loop.intelligence_loops import (serve_pillar, guidance_for_as_loop,
                                           search_as_loop_refs)
    got = {"string": 0, "code": 0, "history": 0, "guidance": 0, "refs": 0}
    try:
        serve_pillar("context_intelligence", f"step:{step}",
                     lambda: f"considerations for {step}",
                     ledger=loop.ledger, parent=loop)
        got["string"] = 1
    except Exception:                                       # noqa: BLE001
        pass
    # CODE intelligence: does a capability already serve this step?  This is
    # also the capability search the solve path never performed.
    if code_store is not None:
        try:
            refs = search_as_loop_refs(code_store, step,
                                       pillar="code_intelligence",
                                       ledger=loop.ledger, parent=loop)
            got["code"], got["refs"] = 1, len(refs)
        except Exception:                                   # noqa: BLE001
            pass
    # HISTORY: has a prior run solved something like this step before?
    if history_store is not None:
        try:
            serve_pillar("runtime_history_solution_intelligence", f"prior:{step}",
                         lambda: f"prior runs touching {step}",
                         ledger=loop.ledger, parent=loop)
            got["history"] = 1
        except Exception:                                   # noqa: BLE001
            pass
    if advice_store is not None:
        try:
            guidance_for_as_loop(advice_store, "task", "smoke",
                                 ledger=loop.ledger, parent=loop)
            got["guidance"] = 1
        except Exception:                                   # noqa: BLE001
            pass
    return got


def make_smoke_handler(*, train_csv: str, test_csv: str, sample_csv: str,
                       out_csv: str, advice_fn=None, advice_store=None,
                       output_probabilities: "bool | None" = None,
                       trace: "dict | None" = None):
    """The one smoke handler for every stage.

    ``advice_fn(prompt) -> (text, usage_dict)`` is the ONLY semantic surface —
    None means fully deterministic (stage 0).  ``advice_store`` is probed FIRST
    (a real store search): a hit serves the research step from code, so the
    warm run makes zero model calls.  ``trace`` collects record facts.
    """
    from .kaggle_executor import execute_tabular, resolve_roles
    import pandas as pd
    tr = trace if trace is not None else {}
    tr.setdefault("model_calls", [])
    tr.setdefault("code_served_steps", [])

    def handler(loop: Loop, step: str, context: dict) -> StepOutcome:
        # D-9: the solve consults the intelligence plane BEFORE each step.
        # Until this, a real solve produced four canonical families and
        # touched no pillar — the architecture was conformant and unused on
        # the one path that does real work.  Deterministic, zero semantic
        # calls, and every retrieval labelled on the run's own ledger.
        tr.setdefault("consulted", []).append(
            _consult_pillars(loop, step, advice_store,
                             code_store=advice_store,
                             history_store=advice_store))
        if step == "orient":
            train = pd.read_csv(train_csv)
            sample = pd.read_csv(sample_csv)
            roles = resolve_roles(train, sample)
            tr["target_col"] = roles.target_col
            tr["id_col"] = roles.id_col
            out = (f"rows={len(train)} target={roles.target_col} "
                   f"problem={roles.problem} id={roles.id_col}")
            # PRIOR-SOLUTIONS AWARENESS: previously solved solutions are a
            # first-class String role (SolutionSpec records), probed at
            # orient — not a third primitive.  A hit changes what the loop
            # knows before it decides anything.
            if advice_store is not None:
                ps = advice_store.search(
                    f"solution_spec {roles.problem} {roles.target_col} "
                    "tabular")
                prior = [h["record_id"] for h in ps.get("hits", ())
                         if (h.get("facets") or {}).get("category")
                         == "solution_spec"][:3]
                if prior:
                    tr["prior_solutions"] = prior
                    out += " prior_solutions=" + ",".join(prior)
            tr["code_served_steps"].append(step)
            return StepOutcome(output=out, mode="deterministic",
                               confidence=0.95)
        if step == "research":
            if advice_store is not None:
                # any kind can serve the need — a strategy String or a
                # registered advice-serving code node.  Ranking runs
                # through the ONE Retriever (backend = RESEARCH_BACKEND).
                hits = _research_probe(
                    advice_store,
                    "estimator feature advice " + context.get("orient", ""))
                if hits:
                    rec = advice_store.serve(hits[0]["record_id"])
                    tr["code_served_steps"].append(step)
                    tr["warm_advice_id"] = rec.record_id
                    tr["research_backend"] = RESEARCH_BACKEND
                    return StepOutcome(
                        output=str(rec.body.get("advice", "")),
                        mode="deterministic", confidence=0.85)
            # the LOOP'S mode discipline decides whether research may ask the
            # model: a deterministic-only loop stays on the code rail even
            # when an advice surface exists (permissions, not preference).
            mode = loop.choose_mode(needs_judgement=True)
            if advice_fn is None or mode == "deterministic":
                tr["code_served_steps"].append(step)
                return StepOutcome(
                    output="baseline advice: hist_gradient_boosting with "
                           "default features (code-rail research)",
                    mode="deterministic", confidence=0.7)
            prompt = ("You advise a tabular ML loop. Task facts: "
                      + context.get("orient", "")
                      + ". In <=8 lines: which estimator family and which 2-3 "
                        "engineered features? Name concrete columns/ops.")
            text, usage = advice_fn(prompt)
            tr["model_calls"].append(usage)
            return StepOutcome(output=text[:2000] or "(empty)", mode=mode,
                               confidence=0.75, failed=not text,
                               model_calls=1)
        if step == "decide":
            keys = _distill_keys(context.get("research", ""))
            tr["proposed_keys"] = list(keys)
            tr["code_served_steps"].append(step)
            return StepOutcome(output="keys=" + "|".join(keys),
                               mode="deterministic", confidence=0.85)
        if step == "act":
            res = execute_tabular(train_csv, test_csv, sample_csv, out_csv,
                                  proposed_keys=tuple(
                                      tr.get("proposed_keys", ())),
                                  output_probabilities=output_probabilities)
            tr["cv_score"] = res.local_score
            tr["metric"] = res.local_metric
            tr["estimator"] = res.family
            tr["engineered"] = list(res.engineered)
            tr["out_csv"] = res.submission_path
            tr["code_served_steps"].append(step)
            # the run's ARTIFACT, first-class: the shipped pipeline as a
            # SolutionSpec (deterministic — seeded sklearn — regardless of
            # how the LOOP researched; the loop's mode is not the solution's).
            from .solution_canvas import SolutionLoopSpec, SolutionSpec
            spec = SolutionSpec(
                f"tabular_{res.family}",
                permitted_loop_modes=("deterministic",),
                loops=(SolutionLoopSpec("load", "load_csv"),
                       SolutionLoopSpec("features", "engineer",
                                    params={"engineered":
                                            list(res.engineered)}),
                       SolutionLoopSpec("model", "fit_predict",
                                    params={"family": res.family,
                                            "output":
                                                ("probabilities"
                                                 if output_probabilities
                                                 else "labels")},
                                    fallback_operations=(
                                        "fit_predict_conservative",))))
            tr["solution_spec"] = {"valid": spec.validate()["valid"],
                                   "record_id": spec.to_record().record_id,
                                   "ensemble": spec.ensemble,
                                   "permitted_loop_modes": list(
                                       spec.permitted_loop_modes)}
            return StepOutcome(output=f"cv_{res.local_metric}="
                                      f"{res.local_score:.5f} "
                                      f"est={res.family}",
                               mode="deterministic", confidence=0.9)
        if step == "verify":
            sub = pd.read_csv(out_csv)
            sample = pd.read_csv(sample_csv)
            shape_ok = (len(sub) == len(sample)
                        and list(sub.columns) == list(sample.columns))
            train = pd.read_csv(train_csv)
            tcol = tr.get("target_col") or train.columns[-1]
            rate = float(train[tcol].mean()) if tcol in train else 0.5
            majority = max(rate, 1 - rate)
            beats = tr.get("cv_score", 0) > majority
            tr["verify"] = {"shape_ok": shape_ok, "majority": round(majority, 5),
                            "beats_majority": bool(beats)}
            tr["code_served_steps"].append(step)
            return StepOutcome(
                output=f"shape_ok={shape_ok} beats_majority={beats}",
                mode="deterministic", confidence=0.9, failed=not shape_ok)
        # commit
        tr["code_served_steps"].append(step)
        return StepOutcome(output="committed", mode="deterministic",
                           confidence=0.9)

    return handler


def run_smoke_loop(goal: str, *, train_csv: str, test_csv: str,
                   sample_csv: str, out_csv: str, advice_fn=None,
                   advice_store=None, output_probabilities: "bool | None" = None,
                   config: "LoopConfig | None" = None, ledger=None,
                   run_history_run_id: str = "", runs_dir: str = "",
                   usage_log: "list | None" = None) -> dict:
    """One end-to-end smoke run through the canonical Loop; returns the
    record (ledger, modes, trace, §12 accounting).  ``config`` sets the
    loop's mode discipline — a deterministic-only config keeps research on
    the code rail even when a live advice surface is wired."""
    trace: dict = {}
    handler = make_smoke_handler(train_csv=train_csv, test_csv=test_csv,
                                 sample_csv=sample_csv, out_csv=out_csv,
                                 advice_fn=advice_fn, advice_store=advice_store,
                                 output_probabilities=output_probabilities,
                                 trace=trace)
    if config is None:
        from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
        tmpl = next(b for b in TEMPLATE_LIBRARY
                    if b["template_id"] == "smoke_solve_six_beat")
        config = config_from_template(tmpl, power="deep")
    loop = Loop(goal, config, ledger=ledger)
    if run_history_run_id:
        from ..core.run_history import default_runs_dir
        loop.enable_run_history(run_history_run_id,
                              root_dir=default_runs_dir(runs_dir),
                              usage_log=usage_log)
    recs = []
    while not loop.is_terminal:
        recs.append(loop.run_next_iteration(handler=handler))
    res = loop.result()
    return {"record_type": "smoke_loop_record/v1", "goal": goal,
            "loop_id": res.loop_id, "steps_run": res.steps_run,
            "stopped": res.stopped, "mode_counts": res.mode_counts,
            "model_calls_budgeted": res.model_calls,
            "semantic_calls_per_iteration_max":
                max((r.get("semantic_calls", 0) for r in recs), default=0),
            "trace": trace,
            "ledger_events": len(loop.ledger.events),
            "ledger": loop.ledger.events}


def stage0(workdir: "str | None" = None) -> dict:
    """Stage 0: the deterministic local fixture through the real Loop —
    proves loop init, data loading, baseline, validation, records, with
    ZERO model calls."""
    workdir = workdir or tempfile.mkdtemp(prefix="smoke0_")
    train, test, sample, out = _fixture(workdir)
    record = run_smoke_loop("stage0: solve the deterministic fixture",
                             train_csv=train, test_csv=test,
                             sample_csv=sample, out_csv=out)
    record["stage"] = "stage0_deterministic_fixture"
    record["honesty"] = ("synthetic seeded fixture; proves plumbing only — "
                          "never benchmark evidence")
    return record


def submission_as_loop(competition: str, csv_path: str, message: str, *,
                       authorized: bool = False, submit_fn=None,
                       ledger=None) -> dict:
    """Loop-standardization item #2: the external submission runs AS a
    PractitionerLoop on the registered guarded_irreversible_effect
    template — an explicit AUTHORIZE beat FAILS CLOSED before the
    irreversible act. Unauthorized: the submit function is never called
    and the refusal is loop evidence. Authorized: exactly one submit,
    then verify inspects the effect's own return."""
    from ..loop.recursive_loop import Loop, StepOutcome
    from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
    tmpl = next(b for b in TEMPLATE_LIBRARY
                if b["template_id"] == "guarded_irreversible_effect")
    fn = submit_fn or submit_to_kaggle
    state: dict = {"submitted": False, "refused": False}

    def handler(lp, step, ctx):
        if step == "authorize":
            if not authorized:
                state["refused"] = True
                return StepOutcome(output="authorize:REFUSED — no explicit "
                                          "authorization for an external "
                                          "submission", mode="deterministic",
                                   confidence=0.99)
            return StepOutcome(output="authorize:granted",
                               mode="deterministic", confidence=0.99)
        if step == "act":
            if state["refused"]:
                return StepOutcome(output="act:skipped (refused upstream)",
                                   mode="deterministic", confidence=0.99)
            state["result"] = fn(competition, csv_path, message)
            state["submitted"] = True
            return StepOutcome(output="act:submitted",
                               mode="deterministic", confidence=0.9)
        if step == "verify":
            ok = (not state["refused"]
                  and state.get("result", {}).get("returncode") == 0)
            return StepOutcome(
                output=f"verify:{'effect confirmed' if ok else 'no effect'}",
                mode="deterministic", confidence=0.9 if ok else 0.6)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    loop = Loop(f"guarded submission: {competition}",
                config_from_template(tmpl, power="standard"), ledger=ledger)
    res = loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    return {"loop_id": res.loop_id, "refused": state["refused"],
            "submitted": state["submitted"],
            "result": state.get("result"), "model_calls": res.model_calls,
            "stopped": res.stopped}


def submit_to_kaggle(competition: str, csv_path: str, message: str) -> dict:
    """REAL external submission via the kaggle CLI (explicit call sites only)."""
    p = subprocess.run(["kaggle", "competitions", "submit", "-c", competition,
                        "-f", csv_path, "-m", message],
                       capture_output=True, text=True, timeout=300)
    return {"returncode": p.returncode, "stdout": p.stdout.strip()[-500:],
            "stderr": p.stderr.strip()[-500:]}


def self_test() -> dict:
    """Offline-only: stage 0 end to end + the warm-run growth-gate MECHANISM
    with a stubbed advice surface (no network, no model)."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    r0 = stage0()
    check("stage0_fixture_runs_end_to_end_through_the_loop",
          r0["steps_run"] == 6 and r0["stopped"] == "done"
          and r0["trace"]["verify"]["shape_ok"]
          and r0["trace"]["verify"]["beats_majority"]
          and r0["model_calls_budgeted"] == 0,
          f"cv={r0['trace'].get('cv_score')} vs majority "
          f"{r0['trace']['verify']['majority']}; zero model calls")

    check("stage0_record_is_complete",
          r0["semantic_calls_per_iteration_max"] == 0
          and r0["ledger_events"] >= 7          # init + six recorded steps
          and len(r0["trace"]["code_served_steps"]) == 6,
          "every step recorded; all six served by code")

    # the growth-gate mechanism, offline: cold run pays one (stubbed) semantic
    # call; the mined advice is stored; the warm run serves it from the store
    # and pays ZERO.
    workdir = tempfile.mkdtemp(prefix="smoke_warm_")
    train, test, sample, out = _fixture(workdir)

    def stub_advice(prompt):
        return ("Use gradient boosting (hgb). Engineer: x1*x2 interaction, "
                "cat frequency encoding.", {"stub": True, "eval_count": 0})

    cold = run_smoke_loop("cold", train_csv=train, test_csv=test,
                          sample_csv=sample, out_csv=out,
                          advice_fn=stub_advice)
    from ..core.store_serve import SolverStore, StoreRecord
    store = SolverStore(core_records=[StoreRecord(
        "advice.fixture", "strategy",
        "estimator feature advice for tabular fixture (mined, CANDIDATE)",
        body={"advice": cold["trace"]["research_advice"]
              if "research_advice" in cold["trace"]
              else "hgb with interaction features",
              "maturity": "candidate",
              "provenance": "mined from cold-run ledger"},
        tags=("advice", "estimator", "candidate"))])
    warm = run_smoke_loop("warm", train_csv=train, test_csv=test,
                          sample_csv=sample, out_csv=out,
                          advice_fn=stub_advice, advice_store=store)
    check("growth_gate_mechanism_warm_run_serves_advice_from_code",
          len(cold["trace"]["model_calls"]) == 1
          and len(warm["trace"]["model_calls"]) == 0
          and warm["trace"].get("warm_advice_id") == "advice.fixture"
          and len(warm["trace"]["code_served_steps"]) == 6,
          "cold paid 1 semantic call; warm served the mined advice from the "
          "store and paid 0 — the flywheel mechanism, offline")

    # §12 holds on the smoke shape: never >1 semantic call in an iteration.
    check("smoke_runs_respect_one_semantic_call_per_iteration",
          cold["semantic_calls_per_iteration_max"] <= 1
          and warm["semantic_calls_per_iteration_max"] == 0)

    # prior-solutions awareness: a SolutionSpec record in the store is
    # surfaced at ORIENT (a String role, not a third primitive) — the loop
    # knows similar solved solutions before deciding anything.
    from .solution_canvas import SolutionLoopSpec, SolutionSpec
    sol_store = SolverStore(core_records=[
        SolutionSpec("tabular_hgb_prior",
                     loops=(SolutionLoopSpec("m", "fit_predict"),)).to_record()])
    aware = run_smoke_loop("aware", train_csv=train, test_csv=test,
                           sample_csv=sample, out_csv=out,
                           advice_fn=stub_advice, advice_store=sol_store)
    check("prior_solutions_surface_at_orient_as_a_string_role",
          aware["trace"].get("prior_solutions")
          == ["solution.tabular_hgb_prior"]
          # search the WHOLE ledger, not its first six events: the assertion
          # used to encode a POSITION, and adding the intelligence consult
          # before each step pushed the event past the window.  The property
          # is that orient recorded it, not where it landed.
          and any("prior_solutions=" in str(e) for e in aware["ledger"]),
          "previously solved solutions are searchable Strings the loop "
          "reads at orient")

    # LOOP-STANDARDIZATION #2: the submission lane is a guarded loop —
    # unauthorized NEVER calls the submit function (fail closed, loop
    # evidence); authorized calls it exactly once with a stub.
    from ..loop.recursive_loop import LoopLedger as _LL
    calls = []
    _stub = lambda c, f, m: (calls.append((c, f, m))
                             or {"returncode": 0, "stdout": "ok",
                                 "stderr": ""})
    _lgA = _LL()
    ref = submission_as_loop("comp-x", "sub.csv", "msg", authorized=False,
                             submit_fn=_stub, ledger=_lgA)
    ok = submission_as_loop("comp-x", "sub.csv", "msg", authorized=True,
                            submit_fn=_stub)
    refused_evidence = any("authorize:REFUSED" in str(e.get("output", ""))
                           for e in _lgA.events)
    check("submission_is_a_guarded_loop_fail_closed",
          ref["refused"] and not ref["submitted"] and len(calls) == 1
          and ok["submitted"] and not ok["refused"]
          and ok["model_calls"] == 0 and refused_evidence,
          "unauthorized: 0 submits + refusal on the ledger; "
          "authorized: exactly 1")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
