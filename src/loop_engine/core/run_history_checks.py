"""Executable checks for the append-only Run History authority.

Split out of ``run_history.py`` at the module size cap, the way
``event_vocabulary`` was. The checks exercise ``RunHistory`` end to end:
ordering and digests, the closed event vocabulary and its total
projection, saved-run bundles, product outcome binding, model usage,
and per-run authorship. They fold the focused usage checks so the suite
counts each contract once. The module under test keeps no test code.
"""
from __future__ import annotations

import json
import os

from .event_vocabulary import (
    EVENT_FAMILIES,
    _CANONICAL_EVENT_MAP,
    _EVENT_TYPE_FAMILY,
    canonical_event_coverage,
    family_of,
    to_canonical_events)
from .product_outcome_store import (
    PRODUCT_OUTCOME_FILENAME,
    bind_product_outcome,
    load_saved_run_bundle)
from .run_history import (
    EVENT_TYPES,
    RunHistory,
    as_ledger_events,
    recorded_output_handler,
    verify_saved_run)
from .run_history_paths import RunHistoryIntegrityError, saved_run_ids


def self_test() -> dict:
    import shutil
    import tempfile
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome, default_handler

    def handler(loop, step, context):
        if step == "research":
            return StepOutcome(output="the recorded advice: use hgb",
                               mode="hybrid", confidence=0.7)
        return default_handler(loop, step, context)

    lp = Loop("record this run", LoopConfig(framework="custom",
                                         custom_steps=("orient", "research",
                                                       "act"), power="deep"))
    lp.run(handler=handler)
    usage = [{"model": "test-model", "prompt_tokens": 10, "eval_tokens": 40}]
    ch = RunHistory.from_ledger(lp.ledger.events, run_id="run_test",
                               usage_log=usage)
    head = ch.commit()

    # 1. the projection produces a sequenced, hash-chained canonical history
    # with the model invocation carrying provider tokens.
    calls = [e for e in ch.event_log if e.event_type == "model_invocation"]
    check("ledger_projects_into_a_chained_canonical_history",
          ch.verify_chain()["intact"] and len(head) == 64
          and calls and calls[0].prompt_tokens == 10
          and calls[0].model == "test-model"
          and [e.sequence_number for e in ch.event_log]
          == list(range(len(ch.event_log))),
          f"{len(ch.event_log)} events, chain intact, head {head[:12]}…")

    # 2. committed history is IMMUTABLE; tampering breaks the chain loudly.
    refused = False
    try:
        ch.append("custom")
    except ValueError:
        refused = True
    ch.event_log[2].detail["output"] = "REWRITTEN"
    v = ch.verify_chain()
    check("history_is_immutable_and_tamper_evident",
          refused and not v["intact"] and 2 in v["broken_at"],
          "append-after-commit refused; edit named at its sequence number")

    # 3. save/load round-trips the runs/<run_id>/ layout byte-faithfully.
    ch2 = RunHistory.from_ledger(lp.ledger.events, run_id="run_rt",
                                usage_log=usage)
    ch2.commit()
    tmp = tempfile.mkdtemp(prefix="chron_")
    try:
        unsafe_construct_refused = unsafe_load_refused = False
        try:
            RunHistory("../outside")
        except RunHistoryIntegrityError:
            unsafe_construct_refused = True
        try:
            RunHistory.load(tmp, "%2e%2e/outside")
        except RunHistoryIntegrityError:
            unsafe_load_refused = True
        check("run_ids_are_confined_portable_path_segments",
              unsafe_construct_refused and unsafe_load_refused,
              "construction and load reject traversal before filesystem use")

        ch2.save(tmp)
        back = RunHistory.load(tmp, "run_rt")
        check("runs_layout_round_trips_and_verifies",
              back.verify_chain()["intact"]
              and len(back.event_log) == len(ch2.event_log)
              and back.event_log[-1].event_digest
              == ch2.event_log[-1].event_digest,
              "manifest.json + events.jsonl; chain verifies after reload")
        collision_refused = False
        try:
            ch2.save(tmp)
        except FileExistsError:
            collision_refused = True
        check("saved_run_identity_is_immutable",
              collision_refused,
              "a second save with the same run id is refused")

        artifact_sibling = os.path.join(tmp, "run_rt-artifacts")
        os.makedirs(artifact_sibling)
        with open(os.path.join(artifact_sibling, "artifact.json"), "w") as f:
            json.dump({"artifact": True}, f)
        check("saved_run_listing_excludes_artifact_siblings",
              saved_run_ids(tmp) == ["run_rt"],
              "@last resolves only complete manifest plus event-log folders")

        outcome = {
            "record_type": "solve_outcome/v3", "run_id": "run_rt",
            "terminal_code": "COMPLETED_VERIFIED",
            "status": "COMPLETED_VERIFIED", "solved": True,
            "summary": "Verified fixture.", "failure_code": "",
            "verification": {"passed": True}, "artifacts": [],
            "workspace": "", "limitations": [], "selected_canvas": {},
        }
        outcome_ref = bind_product_outcome(tmp, "run_rt", outcome)
        bound = load_saved_run_bundle(tmp, "run_rt")
        check("product_outcome_is_digest_bound_to_the_saved_run",
              bound.outcome["terminal_code"] == "COMPLETED_VERIFIED"
              and bound.outcome_ref == outcome_ref
              and verify_saved_run(tmp, "run_rt")[
                  "product_outcome_bound"] is True,
              "event chain and product terminal load as one bundle")

        outcome_path = os.path.join(tmp, "run_rt", PRODUCT_OUTCOME_FILENAME)
        original_outcome = json.load(open(outcome_path))
        changed_outcome = {**original_outcome, "summary": "tampered"}
        with open(outcome_path, "w") as stream:
            json.dump(changed_outcome, stream)
        outcome_refused = False
        try:
            load_saved_run_bundle(tmp, "run_rt")
        except RunHistoryIntegrityError:
            outcome_refused = True
        with open(outcome_path, "w") as stream:
            json.dump(original_outcome, stream)
        check("changed_product_outcome_is_refused_on_load",
              outcome_refused,
              "outcome digest must match the run manifest")

        manifest_path = os.path.join(tmp, "run_rt", "manifest.json")
        manifest = json.load(open(manifest_path))
        changed_manifest = {**manifest, "head_digest": "0" * 64}
        with open(manifest_path, "w") as stream:
            json.dump(changed_manifest, stream)
        integrity_refused = False
        try:
            RunHistory.load(tmp, "run_rt")
        except RunHistoryIntegrityError:
            integrity_refused = True
        with open(manifest_path, "w") as stream:
            json.dump(manifest, stream)
        check("changed_saved_history_is_refused_on_load", integrity_refused,
              "the manifest head must match the event-log digest chain")

        projected = as_ledger_events(back.event_log)
        check("persisted_events_project_to_runtime_shape",
              any(e.get("event") == "init" and e.get("goal")
                  for e in projected)
              and any(e.get("event") == "model_invocation"
                      and e.get("prompt_tokens") == 10
                      and e.get("eval_tokens") == 40
                      for e in projected),
              "goal, event kinds, and provider usage survive persistence")
        # 3b. DuckDB can query the projection directly (files stay the truth).
        try:
            import duckdb
            n = duckdb.connect().execute(
                "SELECT count(*) FROM read_json_auto(?)",
                [os.path.join(tmp, "run_rt", "events.jsonl")]).fetchone()[0]
            check("duckdb_queries_the_run_history_files_directly",
                  n == len(ch2.event_log), f"{n} rows")
        except ImportError:
            results.append({
                "test": "duckdb_queries_the_run_history_files_directly",
                "passed": True, "not_tested": True,
                "outcome": "NOT_APPLICABLE",
                "missing_optional_dependencies": ["duckdb"],
                "detail": (
                    "Optional DuckDB projection is not installed; the JSONL "
                    "Run History authority was still verified.")})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 4. recorded-output replay: the semantic step serves the RECORDED answer
    # deterministically — zero model surface — and the run completes.
    replay_handler = recorded_output_handler(ch2, default_handler)
    lp2 = Loop("replay", LoopConfig(framework="custom",
                                    custom_steps=("orient", "research",
                                                  "act"), power="deep"))
    r2 = lp2.run(handler=replay_handler)
    research = [e for e in lp2.ledger.events
                if e.get("event") == "run_step"
                and e.get("step") == "research"]
    check("recorded_output_replay_serves_history_not_models",
          r2.stopped == "done" and research
          and research[0]["mode"] == "deterministic"
          and "recorded advice" in research[0]["output"],
          "orchestration re-ran; the model did not")

    # 5. the OTLP-shaped export nests loops and GenAI spans (a projection).
    spans = ch2.to_otel_spans()
    genai = [s for s in spans if s["kind"] == "model"]
    check("otel_export_projects_loops_and_genai_spans",
          genai and genai[0]["attributes"]["loop_engine.prompt_tokens"] == 10
          and any(s["kind"] == "loop" for s in spans)
          and genai[0]["parent_span_id"],
          f"{len(spans)} spans; model call nested under its loop")

    # REAL-TIME CANARY (superseding charter): one scripted run exercises
    # Context retrieval, a spawned Loop and return, a visible model-backed step
    # (handler-declared mode — event visibility, no provider call), a
    # runtime-memory note written AND read, a solution-canvas update, and
    # terminal closure — then the canonical projection is total, lossless,
    # and carries every required family.
    from ..loop.recursive_loop import LoopLedger
    from .runtime_memory import RunNoteBoard
    _lg = LoopLedger()
    _board = RunNoteBoard("canary-run", ledger=_lg)

    def _h(lp, step, ctx):
        if step == "load":
            return StepOutcome(output="load:string_retrieved:s.leakage",
                               mode="deterministic", confidence=0.9)
        if step == "choose" and lp.depth == 0 and "spawned" not in ctx:
            _board.write("spawned Loop will validate the split",
                         loop_id=lp.loop_id,
                         topic="plan")
            return StepOutcome(output="choose:spawning",
                               mode="deterministic", spawn_goal="validate")
        if step == "act":
            if lp.depth == 0:
                _board.read(topic="plan", loop_id=lp.loop_id)
                lp.ledger.record(loop_id=lp.loop_id,
                                 event="solution.canvas.updated",
                                 candidate="A")
                return StepOutcome(output="act:model_visible",
                                   mode="non_deterministic", confidence=0.7)
            return StepOutcome(output="act:code:n.dedupe",
                               mode="deterministic", confidence=0.95)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    Loop("realtime canary", LoopConfig(framework="five_step", power="deep"),
         ledger=_lg).run(handler=_h, max_steps=12)
    canon = to_canonical_events(_lg.events)
    types = {c["type"] for c in canon}
    need = {"loop.initialized", "loop.iteration.completed",
            "loop.spawned.started", "loop.spawned.returned", "loop.completed",
            "runtime_memory.message_written", "runtime_memory.message_read",
            "solution.canvas.updated"}
    check("realtime_canary_families_present_projection_lossless",
          need <= types and len(canon) == len(_lg.events)
          and any("model_visible" in str(c["source"].get("output", ""))
                  and c["source"].get("mode") == "non_deterministic"
                  for c in canon),
          f"{len(canon)} events, {len(types)} canonical types, "
          "model-backed step visible")

    # ONE VOCABULARY (§3.8).  The canonical families are closed; the stored
    # event_type is a coarser bucket of the SAME vocabulary, not a second
    # semantic model; and nothing this package emits may leak out as an
    # untyped passthrough.
    check("stored_event_types_are_a_projection_of_one_vocabulary",
          set(_EVENT_TYPE_FAMILY) == set(EVENT_TYPES)
          and set(_EVENT_TYPE_FAMILY.values()) <= set(EVENT_FAMILIES)
          and family_of("model_invocation") == "model.invocation.completed",
          f"{len(EVENT_TYPES)} stored buckets over "
          f"{len(EVENT_FAMILIES)} declared families")
    check("no_owned_kind_escapes_as_an_untyped_passthrough",
          not [c for c in canon if c["type"].startswith("x.")],
          "every kind the canary emitted resolved to a declared family")

    # the coverage report is HONEST: it never claims a declared family is
    # live merely because it is declared.
    cov = canonical_event_coverage(_lg.events)
    check("coverage_separates_emitted_from_declared_only",
          cov["declared"] == len(EVENT_FAMILIES)
          and set(cov["emitted_by_some_runtime_kind"]).isdisjoint(
              cov["declared_without_an_emitter"])
          # NOT "> 0": that asserted some family must always lack an
          # emitter, so reaching full coverage failed the test that existed
          # to keep coverage honest.  Fourth instance of assert-the-state in
          # this codebase.  The property is that the two sets are DISJOINT
          # and that nothing observed was undeclared — true at 0% and at
          # 100%.
          and not (set(cov["emitted_by_some_runtime_kind"])
                   & set(cov["declared_without_an_emitter"]))
          and set(cov["observed_in_this_run"])
          <= set(cov["emitted_by_some_runtime_kind"]),
          f"{len(cov['emitted_by_some_runtime_kind'])} families have an "
          f"emitter, {len(cov['declared_without_an_emitter'])} are declared "
          "with none yet")

    # ADVERSARIAL: a resolver that returns an undeclared family must RAISE,
    # not quietly widen the vocabulary; and an unknown intelligence layer is
    # refused rather than silently filed under "string".
    widened = False
    try:
        to_canonical_events([{"event": "intelligence_pull",
                              "layer": "vibes"}])
    except ValueError:
        widened = True
    _saved = _CANONICAL_EVENT_MAP.get("spec")
    _CANONICAL_EVENT_MAP["spec"] = "not.a.declared.family"
    refused = False
    try:
        to_canonical_events([{"event": "spec"}])
    except ValueError:
        refused = True
    finally:
        _CANONICAL_EVENT_MAP["spec"] = _saved
    check("undeclared_families_and_unknown_layers_are_refused",
          widened and refused,
          "an unmapped layer and an undeclared family both raise")

    # D-1: the stored buckets were narrowed, and the narrowing was decided by
    # MEASUREMENT rather than tidiness.  Three kinds moved out of `custom`
    # into buckets nothing counts; the two that would have moved a real
    # counter deliberately stayed coarse.  This test is the guard on that
    # bargain: redistribution is allowed, moving a semantic counter is not.
    _lgn = LoopLedger()

    def _hn(lp, step, ctx):
        lp.ledger.record(loop_id=lp.loop_id, event="intelligence_pull",
                         step=step, pulled=3, required=3)
        lp.ledger.record(loop_id=lp.loop_id, event="infra_call", step=step,
                         surface="resource_search", n_hits=2)
        if step == "act":
            lp.ledger.record(loop_id=lp.loop_id,
                             event="solution.canvas.updated", candidate="A")
            return StepOutcome(output="act:m", mode="non_deterministic",
                               confidence=0.7)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    Loop("narrowing guard", LoopConfig(framework="five_step", power="deep"),
         ledger=_lgn).run(handler=_hn, max_steps=8)
    _usage = [{"model": "m", "prompt_tokens": 5, "eval_tokens": 5}]
    _new = RunHistory.from_ledger(_lgn.events, run_id="n", usage_log=_usage)
    _pre = {"init": "loop_init", "spawn": "loop_spawn", "run_step": "iteration",
            "fallback": "fallback", "terminal": "terminal", "cancel": "cancel",
            "model_boundary_deferred": "model_boundary_deferred",
            "budget_stop": "budget_stop", "spec": "custom", "pause": "custom",
            "resume": "custom"}
    _saved = RunHistory._LEDGER_MAP
    try:
        RunHistory._LEDGER_MAP = _pre
        _old = RunHistory.from_ledger(_lgn.events, run_id="o", usage_log=_usage)
    finally:
        RunHistory._LEDGER_MAP = _saved

    def _c(ch, t):
        return sum(1 for e in ch.event_log if e.event_type == t)

    # The property is that the narrowed kinds MOVED and no semantic counter
    # did — not that `custom` is empty forever.  Asserting == 0 encoded the
    # state of the day: a legitimately-new kind with no accurate bucket
    # (iteration_started) later landed there and failed a guard that was
    # never about it.  Third instance of this smell; assert the direction.
    check("narrowing_redistributed_custom_without_moving_a_counter",
          _c(_old, "custom") > _c(_new, "custom")
          and _c(_new, "context_retrieval") > 0
          and _c(_new, "capability_search") > 0
          and _c(_new, "solution_built") > 0
          # the two that MUST NOT move:
          and _c(_old, "model_invocation") == _c(_new, "model_invocation")
          and _c(_old, "iteration") == _c(_new, "iteration")
          and len(_old.event_log) == len(_new.event_log),
          f"custom {_c(_old, 'custom')}->0; model_invocation and iteration "
          "unchanged; event total unchanged")

    # terminal reason decides completed vs failed — a budget stop never
    # reports as a clean completion.
    fams = [to_canonical_events([{"event": "terminal", "reason": r}])[0]["type"]
            for r in ("done", "budget", "cancelled")]
    check("terminal_projects_by_reason_not_by_optimism",
          fams == ["loop.completed", "loop.failed", "loop.failed"],
          f"done/budget/cancelled -> {fams}")

    from .run_history_usage_checks import self_test as usage_self_test
    for item in usage_self_test()["tests"]:
        check(item["test"], item["passed"], item.get("detail", ""))

    # W1, recorded by three consecutive reviews: the digest chain proves
    # order, not authorship. With a key, a direct append of an event that
    # no facade signed is refused, whatever its type; a facade can emit only
    # the kinds its Loop registered; a history without a key is unchanged
    # and says so.
    from .run_history_authorship import RunAuthorityKey, RunAuthorshipError
    _key = RunAuthorityKey.create("run-authorship-check")
    _keyed = RunHistory("run-authorship-check", authority_key=_key)
    _facade = _keyed.recorder_for("loop-a", {"iteration", "run_started"})
    _signed = _keyed.append(**_facade.record("iteration", step="act", status="ok"))
    _refused = []
    for _forged in ({"event_type": "iteration", "loop_id": "loop-a", "step": "verify",
                     "detail": {"output": "FORGED: independent verification passed"}},
                    {"event_type": "model_invocation", "loop_id": "loop-a", "model": "phantom",
                     "prompt_tokens": 12345, "eval_tokens": 678},
                    {"event_type": "terminal", "loop_id": "loop-phantom",
                     "detail": {"reason": "done"}}):
        try:
            _keyed.append(**_forged); _refused.append(False)
        except RunAuthorshipError:
            _refused.append(True)
    check("keyed_history_refuses_a_forged_verify_model_invocation_and_terminal",
          all(_refused) and len(_refused) == 3 and len(_keyed.event_log) == 1,
          f"refused={_refused}; a handler that reaches append() directly gets nothing in")
    try:
        _facade.record("terminal", detail={"reason": "done"}); _fac_ok = False
    except RunAuthorshipError:
        _fac_ok = True
    check("a_facade_cannot_emit_an_event_kind_its_loop_did_not_register", _fac_ok)
    check("verify_authorship_passes_on_a_clean_keyed_history",
          _keyed.verify_authorship().get("ok") is True and "authorship_tag" in _signed.detail)
    _plain = RunHistory("run-unkeyed-check"); _plain.append("iteration", loop_id="x", step="act")
    check("an_unkeyed_history_is_unchanged_and_labelled_unverified",
          len(_plain.event_log) == 1 and _plain.authorship == "unverified")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
