"""Loop Engine Chronicle — the canonical append-only event history (system of record).

Architectural role: Static Architecture service (evidence/history).

Owns:
    - ChronicleEvent: the one canonical event envelope (identity, ordering,
      lineage refs, tokens/cost, status, digest);
    - Chronicle: append-only, monotonically sequenced, HASH-CHAINED history —
      immutable after commit, tamper-evident, persistable to the standard
      ``runs/<run_id>/`` layout (manifest.json + events.jsonl), replayable;
    - from_ledger: the projection from the runtime's lightweight LoopLedger
      into canonical events (the ledger records; the Chronicle is the record);
    - to_otel_spans: the OpenTelemetry-shaped export projection (runs→traces,
      loops/iterations→spans, model calls→GenAI spans) — an EXPORT view,
      never the authoritative store;
    - recorded_output_handler: recorded-output REPLAY — re-run orchestration
      substituting the originally recorded semantic outputs (no model calls).

Does not own:
    - playback rendering (run_playback), metrics (run_analytics/run_quality),
      or any mutation of history — an edit is a NEW proposal + a NEW run.

Public entry points:
    - Chronicle(run_id).append(...) / commit() / verify_chain()
    - Chronicle.from_ledger(events, run_id=...)
    - chronicle.save(root) / Chronicle.load(root, run_id)
    - chronicle.to_otel_spans()
    - recorded_output_handler(chronicle, base_handler, semantic_steps)

Key invariants:
    - append-only: committed events can never be altered (the digest chain
      breaks loudly on tamper — verify_chain refuses);
    - playback reads history; replay re-executes; a fork is a NEW run linked
      by parent_run_id — history is never mutated.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field

EVENT_TYPES = ("run_started", "loop_init", "loop_spawn", "iteration",
               "capability_search", "string_retrieval", "code_execution",
               "model_invocation", "fallback", "model_boundary_deferred",
               "budget_stop", "evaluation", "terminal", "cancel",
               "solution_built", "solution_run", "learning", "custom")


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class ChronicleEvent:
    """The one canonical event envelope."""
    event_type: str
    run_id: str
    sequence_number: int
    ts: float
    loop_id: str = ""
    parent_loop_id: str = ""
    iteration: "int | None" = None
    step: str = ""
    mode: str = ""
    consumed_refs: tuple = ()
    produced_refs: tuple = ()
    model: str = ""
    prompt_tokens: int = 0
    eval_tokens: int = 0
    status: str = "ok"
    detail: dict = field(default_factory=dict)
    prev_digest: str = ""
    event_digest: str = ""

    def body(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()
             if k not in ("event_digest",)}
        d["consumed_refs"] = list(self.consumed_refs)
        d["produced_refs"] = list(self.produced_refs)
        return d


class Chronicle:
    """Append-only, hash-chained, persistable event history for one run."""

    def __init__(self, run_id: str, *, parent_run_id: str = ""):
        self.run_id = run_id
        self.parent_run_id = parent_run_id
        self.events: list = []
        self._committed = False

    # --- append / commit ---------------------------------------------------

    def append(self, event_type: str, **kw) -> ChronicleEvent:
        if self._committed:
            raise ValueError("chronicle committed — history is immutable; "
                             "start a NEW run (fork) instead")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type {event_type!r}")
        prev = self.events[-1].event_digest if self.events else ""
        ev = ChronicleEvent(event_type=event_type, run_id=self.run_id,
                            sequence_number=len(self.events),
                            ts=kw.pop("ts", time.time()),
                            prev_digest=prev, **kw)
        ev.event_digest = _digest(ev.body())
        self.events.append(ev)
        return ev

    def commit(self) -> str:
        self._committed = True
        return self.events[-1].event_digest if self.events else ""

    def verify_chain(self) -> dict:
        """Recompute every digest; a broken link is named, never silent."""
        broken = []
        prev = ""
        for e in self.events:
            if e.prev_digest != prev or e.event_digest != _digest(e.body()):
                broken.append(e.sequence_number)
            prev = e.event_digest
        return {"intact": not broken, "broken_at": broken,
                "events": len(self.events)}

    # --- the ledger projection --------------------------------------------

    #: raw ledger kind -> stored bucket.  Narrowed 2026-08-23 (drift D-1),
    #: but only where nothing counts the target bucket — the measurement, not
    #: the tidiness, decided which kinds moved:
    #:   * intelligence_pull -> string_retrieval, infra_call ->
    #:     capability_search, solution.canvas.updated -> solution_built.
    #:     Nothing in the tree counts those three buckets, so redistributing
    #:     into them moves no consumer's number.
    #:   * model_led / model_escalation deliberately STAY custom.  Mapping
    #:     them to model_invocation would double-count: from_ledger already
    #:     synthesizes a model_invocation for each hybrid/non-deterministic
    #:     iteration, and run_quality pairs quality observations off exactly
    #:     that bucket.  Their canonical family is precise either way, so the
    #:     coarse bucket costs nothing that the family does not already give.
    #:   * kernel_run STAYS custom for the same reason: run_quality counts
    #:     `iteration` as per-loop steps, and a delegated kernel run is one
    #:     unit of work, not N steps of this loop.
    #:   * runtime_memory.* and child_return have no accurate bucket in
    #:     EVENT_TYPES; inventing one to look complete would be worse than
    #:     the honest `custom`.
    _LEDGER_MAP = {"init": "loop_init", "spawn": "loop_spawn",
                   "run_step": "iteration", "fallback": "fallback",
                   "model_boundary_deferred": "model_boundary_deferred",
                   "budget_stop": "budget_stop", "terminal": "terminal",
                   "cancel": "cancel", "spec": "custom",
                   "pause": "custom", "resume": "custom",
                   "loop.started": "loop_init",
                   "intelligence_pull": "string_retrieval",
                   "infra_call": "capability_search",
                   "solution.canvas.updated": "solution_built"}

    @classmethod
    def from_ledger(cls, ledger_events, *, run_id: str,
                    usage_log=()) -> "Chronicle":
        """Project the runtime LoopLedger into canonical Chronicle events.
        Semantic iterations absorb provider usage in order (the usage log is
        positional: nth semantic step ↔ nth usage row)."""
        ch = cls(run_id)
        ch.append("run_started", detail={"source": "loop_ledger"})
        usage = list(usage_log or ())
        ui = 0
        for e in ledger_events:
            et = cls._LEDGER_MAP.get(e.get("event", ""), "custom")
            kw = {"loop_id": str(e.get("loop_id", "")),
                  "parent_loop_id": str(e.get("parent", "")),
                  "step": str(e.get("step", "")),
                  "mode": str(e.get("mode", "")),
                  "ts": e.get("ts", 0.0) or 0.0,
                  "detail": {k: v for k, v in e.items()
                             if k not in ("event", "loop_id", "parent",
                                          "step", "mode", "ts")}}
            if et == "iteration" and e.get("mode") in ("hybrid",
                                                       "non_deterministic"):
                if ui < len(usage):
                    u = usage[ui]; ui += 1
                    kw["model"] = str(u.get("model", ""))
                    kw["prompt_tokens"] = int(u.get("prompt_tokens", 0) or 0)
                    kw["eval_tokens"] = int(u.get("eval_tokens", 0) or 0)
                ch.append("model_invocation", **dict(kw))
            ch.append(et, **kw)
        return ch

    # --- persistence: the runs/<run_id>/ layout ----------------------------

    def save(self, root: str) -> str:
        d = os.path.join(root, self.run_id)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "events.jsonl"), "w") as f:
            for e in self.events:
                f.write(json.dumps({**e.body(),
                                    "event_digest": e.event_digest},
                                   default=str) + "\n")
        manifest = {"record_type": "chronicle_manifest/v1",
                    "run_id": self.run_id,
                    "parent_run_id": self.parent_run_id,
                    "events": len(self.events),
                    "head_digest": (self.events[-1].event_digest
                                    if self.events else ""),
                    "committed": self._committed}
        with open(os.path.join(d, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=1)
        return d

    @classmethod
    def load(cls, root: str, run_id: str) -> "Chronicle":
        d = os.path.join(root, run_id)
        man = json.load(open(os.path.join(d, "manifest.json")))
        ch = cls(run_id, parent_run_id=man.get("parent_run_id", ""))
        for line in open(os.path.join(d, "events.jsonl")):
            row = json.loads(line)
            dig = row.pop("event_digest")
            row["consumed_refs"] = tuple(row.get("consumed_refs", ()))
            row["produced_refs"] = tuple(row.get("produced_refs", ()))
            ev = ChronicleEvent(**row)
            ev.event_digest = dig
            ch.events.append(ev)
        ch._committed = man.get("committed", False)
        return ch

    # --- OTLP-shaped export (a projection, never the store) ----------------

    def to_otel_spans(self) -> list:
        spans = []
        loop_spans: dict = {}
        for e in self.events:
            if e.event_type == "loop_init":
                loop_spans[e.loop_id] = f"span-{e.loop_id}"
                spans.append({"name": "loop_engine.loop", "trace_id": self.run_id,
                              "span_id": f"span-{e.loop_id}",
                              "parent_span_id": loop_spans.get(
                                  e.parent_loop_id, ""),
                              "attributes": {"loop_engine.loop.id": e.loop_id,
                                             "loop_engine.loop.depth":
                                                 e.detail.get("depth", 0)}})
            elif e.event_type == "model_invocation":
                spans.append({"name": "gen_ai.request",
                              "trace_id": self.run_id,
                              "span_id": f"span-call-{e.sequence_number}",
                              "parent_span_id": loop_spans.get(e.loop_id, ""),
                              "attributes": {
                                  "gen_ai.request.model": e.model,
                                  "gen_ai.usage.input_tokens":
                                      e.prompt_tokens,
                                  "gen_ai.usage.output_tokens": e.eval_tokens,
                                  "loop_engine.loop.id": e.loop_id,
                                  "loop_engine.loop.mode": e.mode}})
        return spans


def recorded_output_handler(chronicle: Chronicle, base_handler,
                            semantic_steps=("research",)):
    """Recorded-output REPLAY: a handler wrapper that serves the originally
    recorded outputs for semantic steps (no model is called), and delegates
    everything else to ``base_handler`` — test orchestration changes without
    paying for the calls again."""
    from ..loop.recursive_loop import StepOutcome
    recorded = {}
    for e in chronicle.events:
        if e.event_type == "iteration" and e.step in semantic_steps \
                and e.mode in ("hybrid", "non_deterministic"):
            recorded.setdefault(e.step, str(e.detail.get("output", "")))

    def handler(loop, step, context):
        if step in recorded:
            return StepOutcome(output=recorded[step], mode="deterministic",
                               confidence=0.8)
        return base_handler(loop, step, context)
    return handler


#: superseding charter (2026-08-24): one canonical live event vocabulary
#: across every transport.  Ledger kinds map to the charter families;
#: (refined 2026-08-24 to the live-runtime directive's spelling:
#: loop.child.started, model.invocation.*, user_intelligence.*); kinds
#: neither vocabulary names pass through under "x." so the projection is
#: TOTAL and LOSSLESS, never silently dropping events.
# The canonical vocabulary lives in `event_vocabulary` (split out when this
# module crossed the size cap).  Re-exported here so every existing import
# site keeps working and the vocabulary keeps one home.
from .event_vocabulary import (                                # noqa: E402
    EVENT_FAMILIES, _CANONICAL_EVENT_MAP, _EVENT_TYPE_FAMILY,
    _INTELLIGENCE_LAYER_FAMILY, _ACCEPTED_TERMINAL_REASONS, family_of,
    to_canonical_events, canonical_event_coverage)


def self_test() -> dict:
    import shutil
    import tempfile
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome, \
        default_handler

    def handler(loop, step, context):
        if step == "research":
            return StepOutcome(output="the recorded advice: use hgb",
                               mode="hybrid", confidence=0.7)
        return default_handler(loop, step, context)

    lp = Loop("chronicle me", LoopConfig(framework="custom",
                                         custom_steps=("orient", "research",
                                                       "act"), power="deep"))
    lp.run(handler=handler)
    usage = [{"model": "test-model", "prompt_tokens": 10, "eval_tokens": 40}]
    ch = Chronicle.from_ledger(lp.ledger.events, run_id="run_test",
                               usage_log=usage)
    head = ch.commit()

    # 1. the projection produces a sequenced, hash-chained canonical history
    # with the model invocation carrying provider tokens.
    calls = [e for e in ch.events if e.event_type == "model_invocation"]
    check("ledger_projects_into_a_chained_canonical_history",
          ch.verify_chain()["intact"] and len(head) == 64
          and calls and calls[0].prompt_tokens == 10
          and calls[0].model == "test-model"
          and [e.sequence_number for e in ch.events]
          == list(range(len(ch.events))),
          f"{len(ch.events)} events, chain intact, head {head[:12]}…")

    # 2. committed history is IMMUTABLE; tampering breaks the chain loudly.
    refused = False
    try:
        ch.append("custom")
    except ValueError:
        refused = True
    ch.events[2].detail["output"] = "REWRITTEN"
    v = ch.verify_chain()
    check("history_is_immutable_and_tamper_evident",
          refused and not v["intact"] and 2 in v["broken_at"],
          "append-after-commit refused; edit named at its sequence number")

    # 3. save/load round-trips the runs/<run_id>/ layout byte-faithfully.
    ch2 = Chronicle.from_ledger(lp.ledger.events, run_id="run_rt",
                                usage_log=usage)
    ch2.commit()
    tmp = tempfile.mkdtemp(prefix="chron_")
    try:
        ch2.save(tmp)
        back = Chronicle.load(tmp, "run_rt")
        check("runs_layout_round_trips_and_verifies",
              back.verify_chain()["intact"]
              and len(back.events) == len(ch2.events)
              and back.events[-1].event_digest
              == ch2.events[-1].event_digest,
              "manifest.json + events.jsonl; chain verifies after reload")
        # 3b. DuckDB can query the projection directly (files stay the truth).
        try:
            import duckdb
            n = duckdb.connect().execute(
                "SELECT count(*) FROM read_json_auto(?)",
                [os.path.join(tmp, "run_rt", "events.jsonl")]).fetchone()[0]
            check("duckdb_queries_the_chronicle_files_directly",
                  n == len(ch2.events), f"{n} rows")
        except ImportError:
            results.append({
                "test": "duckdb_queries_the_chronicle_files_directly",
                "passed": False, "missing_dependency": "duckdb",
                "detail": "FAILED: missing duckdb. Reinstall Loop Engine."})
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
    genai = [s for s in spans if s["name"] == "gen_ai.request"]
    check("otel_export_projects_loops_and_genai_spans",
          genai and genai[0]["attributes"]["gen_ai.usage.input_tokens"] == 10
          and any(s["name"] == "loop_engine.loop" for s in spans)
          and genai[0]["parent_span_id"],
          f"{len(spans)} spans; model call nested under its loop")

    # REAL-TIME CANARY (superseding charter): one scripted run exercises
    # string retrieval, a child spawn+return, a VISIBLE model-backed step
    # (handler-declared mode — event visibility, no provider call), a
    # runtime-memory note written AND read, a solution-canvas update, and
    # terminal closure — then the canonical projection is total, lossless,
    # and carries every required family.
    from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
    from .runtime_memory import RunNoteBoard
    _lg = LoopLedger()
    _board = RunNoteBoard("canary-run", ledger=_lg)

    def _h(lp, step, ctx):
        if step == "load":
            return StepOutcome(output="load:string_retrieved:s.leakage",
                               mode="deterministic", confidence=0.9)
        if step == "choose" and lp.depth == 0 and "child" not in ctx:
            _board.write("child will validate the split", loop_id=lp.loop_id,
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
            "loop.child.started", "loop.child.returned", "loop.completed",
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
    _new = Chronicle.from_ledger(_lgn.events, run_id="n", usage_log=_usage)
    _pre = {"init": "loop_init", "spawn": "loop_spawn", "run_step": "iteration",
            "fallback": "fallback", "terminal": "terminal", "cancel": "cancel",
            "model_boundary_deferred": "model_boundary_deferred",
            "budget_stop": "budget_stop", "spec": "custom", "pause": "custom",
            "resume": "custom"}
    _saved = Chronicle._LEDGER_MAP
    try:
        Chronicle._LEDGER_MAP = _pre
        _old = Chronicle.from_ledger(_lgn.events, run_id="o", usage_log=_usage)
    finally:
        Chronicle._LEDGER_MAP = _saved

    def _c(ch, t):
        return sum(1 for e in ch.events if e.event_type == t)

    # The property is that the narrowed kinds MOVED and no semantic counter
    # did — not that `custom` is empty forever.  Asserting == 0 encoded the
    # state of the day: a legitimately-new kind with no accurate bucket
    # (iteration_started) later landed there and failed a guard that was
    # never about it.  Third instance of this smell; assert the direction.
    check("narrowing_redistributed_custom_without_moving_a_counter",
          _c(_old, "custom") > _c(_new, "custom")
          and _c(_new, "string_retrieval") > 0
          and _c(_new, "capability_search") > 0
          and _c(_new, "solution_built") > 0
          # the two that MUST NOT move:
          and _c(_old, "model_invocation") == _c(_new, "model_invocation")
          and _c(_old, "iteration") == _c(_new, "iteration")
          and len(_old.events) == len(_new.events),
          f"custom {_c(_old, 'custom')}->0; model_invocation and iteration "
          "unchanged; event total unchanged")

    # terminal reason decides completed vs failed — a budget stop never
    # reports as a clean completion.
    fams = [to_canonical_events([{"event": "terminal", "reason": r}])[0]["type"]
            for r in ("done", "budget", "cancelled")]
    check("terminal_projects_by_reason_not_by_optimism",
          fams == ["loop.completed", "loop.failed", "loop.failed"],
          f"done/budget/cancelled -> {fams}")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
