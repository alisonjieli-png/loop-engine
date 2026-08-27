"""Loop Engine saved run history.

Architectural role: internal saved-run event log service.

Owns:
    - RunHistoryEvent: the one canonical event envelope (identity, ordering,
      lineage refs, tokens/cost, status, digest);
    - RunHistory: append-only, monotonically sequenced, HASH-CHAINED history —
      immutable after commit, tamper-evident, persistable to the standard
      ``runs/<run_id>/`` layout (manifest.json + events.jsonl), replayable;
    - from_ledger: the projection from the runtime's lightweight LoopLedger
      into canonical events (the ledger records; the RunHistory is the record);
    - to_otel_spans: the OpenTelemetry-shaped export projection (runs→traces,
      loops/iterations→spans, model calls→GenAI spans) — an EXPORT view,
      never the authoritative store;
    - recorded_output_handler: recorded-output REPLAY — re-run orchestration
      substituting the originally recorded semantic outputs (no model calls).

Does not own:
    - playback rendering (run_playback), metrics (run_analytics/run_quality),
      or any mutation of history — an edit is a NEW proposal + a NEW run.

Public entry points:
    - RunHistory(run_id).append(...) / commit() / verify_chain()
    - RunHistory.from_ledger(events, run_id=...)
    - run_history.save(root) / RunHistory.load(root, run_id)
    - run_history.to_otel_spans()
    - recorded_output_handler(run_history, base_handler, semantic_steps)

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
               "capability_search", "context_retrieval", "code_execution",
               "model_invocation", "fallback", "model_boundary_deferred",
               "budget_stop", "evaluation", "terminal", "cancel",
               "solution_built", "solution_run", "learning", "custom")

RUNS_DIR_ENV = "LOOP_ENGINE_RUNS_DIR"


def default_runs_dir(path: str = "") -> str:
    """One shared run directory for live runs, reports, playback, and Studio."""
    selected = path or os.environ.get(RUNS_DIR_ENV, "")
    if selected:
        return os.path.abspath(os.path.expanduser(selected))
    return os.path.join(os.path.expanduser("~"), ".loop-engine", "runs")


_RUN_HISTORY_TO_LEDGER = {
    "run_started": "run_started",
    "loop_init": "init",
    "loop_spawn": "spawn",
    "iteration": "run_step",
    "capability_search": "infra_call",
    "context_retrieval": "intelligence_pull",
    "code_execution": "code_execution",
    "model_invocation": "model_invocation",
    "fallback": "fallback",
    "model_boundary_deferred": "model_boundary_deferred",
    "budget_stop": "budget_stop",
    "evaluation": "evaluation",
    "terminal": "terminal",
    "cancel": "cancel",
    "solution_built": "solution.canvas.updated",
    "solution_run": "solution_run",
    "learning": "learning",
    "custom": "custom",
}


def as_ledger_event(event) -> dict:
    """Project a RunHistory event into the runtime event shape consumers use.

    Raw ledger dictionaries pass through unchanged. RunHistoryEvent objects and
    persisted event dictionaries use one explicit adapter, so reporting,
    analytics, and playback cannot disagree about field names.
    """
    if isinstance(event, dict) and "event" in event:
        return _normalize_runtime_relationship(dict(event))
    row = event.body() if hasattr(event, "body") else dict(event)
    detail = dict(row.get("detail") or {})
    event_type = str(row.get("event_type", "custom"))
    kind = str(detail.pop("_ledger_event", "")
               or _RUN_HISTORY_TO_LEDGER.get(event_type, "custom"))
    out = _normalize_runtime_relationship({**detail,
           "event": kind,
           "loop_id": str(row.get("loop_id", "") or ""),
           "ts": row.get("ts"),
           "step": str(row.get("step", "") or ""),
           "mode": str(row.get("mode", "") or ""),
           "spawning_loop_id": str(
               row.get("spawning_loop_id", "") or "")})
    for key in ("model", "prompt_tokens", "eval_tokens", "status"):
        value = row.get(key)
        if key not in out and value not in (None, "", 0):
            out[key] = value
    return out


def _normalize_runtime_relationship(row: dict) -> dict:
    """Copy one current runtime event without changing relationship fields."""
    return row


def as_ledger_events(events) -> list:
    """Normalize raw or persisted events for report and playback consumers."""
    return [as_ledger_event(event) for event in events]


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


class RunHistoryIntegrityError(ValueError):
    """Saved run history is incomplete, inconsistent, or has been changed."""


@dataclass
class RunHistoryEvent:
    """The one canonical event envelope."""
    event_type: str
    run_id: str
    sequence_number: int
    ts: float
    loop_id: str = ""
    spawning_loop_id: str = ""
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
             if k != "event_digest"}
        d["consumed_refs"] = list(self.consumed_refs)
        d["produced_refs"] = list(self.produced_refs)
        return d


class RunHistory:
    """Append-only, hash-chained, persistable event history for one run."""

    def __init__(self, run_id: str, *, parent_run_id: str = ""):
        self.run_id = run_id
        self.parent_run_id = parent_run_id
        self.event_log: list[RunHistoryEvent] = []
        self._committed = False

    # --- append / commit ---------------------------------------------------

    def append(self, event_type: str, **kw) -> RunHistoryEvent:
        if self._committed:
            raise ValueError("run_history committed — history is immutable; "
                             "start a NEW run (fork) instead")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type {event_type!r}")
        prev = self.event_log[-1].event_digest if self.event_log else ""
        ev = RunHistoryEvent(event_type=event_type, run_id=self.run_id,
                            sequence_number=len(self.event_log),
                            ts=kw.pop("ts", time.time()),
                            prev_digest=prev, **kw)
        ev.event_digest = _digest(ev.body())
        self.event_log.append(ev)
        return ev

    def commit(self) -> str:
        self._committed = True
        return self.event_log[-1].event_digest if self.event_log else ""

    def verify_chain(self) -> dict:
        """Recompute every digest; a broken link is named, never silent."""
        broken = []
        prev = ""
        for e in self.event_log:
            if e.prev_digest != prev or e.event_digest != _digest(e.body()):
                broken.append(e.sequence_number)
            prev = e.event_digest
        return {"intact": not broken, "broken_at": broken,
                "events": len(self.event_log)}

    # --- the ledger projection --------------------------------------------

    #: raw ledger kind -> stored bucket.  Narrowed 2026-08-23 (drift D-1),
    #: but only where nothing counts the target bucket — the measurement, not
    #: the tidiness, decided which kinds moved:
    #:   * intelligence_pull -> context_retrieval, infra_call ->
    #:     capability_search, solution.canvas.updated -> solution_built.
    #:     Nothing in the tree counts those three buckets, so redistributing
    #:     into them moves no consumer's number.
    #:   * explicit provider events map to model_invocation. Mode labels alone
    #:     are not physical-call evidence. Legacy histories with no explicit
    #:     provider events retain the older synthesis path for compatibility.
    #:   * kernel_run STAYS custom for the same reason: run_quality counts
    #:     `iteration` as per-loop steps, and a delegated kernel run is one
    #:     unit of work, not N steps of this loop.
    #:   * runtime_memory.* and spawned_return have no accurate bucket in
    #:     EVENT_TYPES; inventing one to look complete would be worse than
    #:     the honest `custom`.
    _LEDGER_MAP = {"init": "loop_init", "spawn": "loop_spawn",
                   "run_step": "iteration", "fallback": "fallback",
                   "model_boundary_deferred": "model_boundary_deferred",
                   "budget_stop": "budget_stop", "terminal": "terminal",
                   "cancel": "cancel", "spec": "custom",
                   "pause": "custom", "resume": "custom",
                   "loop.started": "loop_init",
                   "model_led": "model_invocation",
                   "model_escalation": "model_invocation",
                   "model_invocation_failed": "model_invocation",
                   "model.invocation.started": "model_invocation",
                   "model.invocation.completed": "model_invocation",
                   "model.invocation.failed": "model_invocation",
                   "model.selection.requested": "capability_search",
                   "model.selection.completed": "capability_search",
                   "model.route.rejected": "fallback",
                   "model.route.selected": "capability_search",
                   "model.no_model_required": "capability_search",
                   "model.outcome.recorded": "model_invocation",
                   "model.routing.candidate.staged": "learning",
                   "intelligence_pull": "context_retrieval",
                   "infra_call": "capability_search",
                   "solution.canvas.updated": "solution_built"}

    @classmethod
    def from_ledger(cls, ledger_events, *, run_id: str,
                    usage_log=()) -> "RunHistory":
        """Project the runtime LoopLedger into canonical RunHistory events.
        Explicit provider events are authoritative. Legacy ledgers without
        them may absorb the positional usage log for compatibility."""
        ledger_events = list(ledger_events)
        ch = cls(run_id)
        ch.append("run_started", detail={"source": "loop_ledger"})
        usage = list(usage_log or ())
        ui = 0
        explicit_model_events = any(
            event.get("event") in (
                "model_led", "model_escalation", "model_invocation_failed",
                "model.invocation.started", "model.invocation.completed",
                "model.invocation.failed")
            for event in ledger_events)
        for e in ledger_events:
            et = cls._LEDGER_MAP.get(e.get("event", ""), "custom")
            e = _normalize_runtime_relationship(dict(e))
            kw = {"loop_id": str(e.get("loop_id", "")),
                  "spawning_loop_id": str(
                      e.get("spawning_loop_id", "")),
                  "step": str(e.get("step", "")),
                  "mode": str(e.get("mode", "")),
                  "ts": e.get("ts", 0.0) or 0.0,
                  "detail": {"_ledger_event": str(e.get("event", "")),
                             **{k: v for k, v in e.items()
                                if k not in ("event", "loop_id",
                                             "spawning_loop_id", "step",
                                             "mode", "ts")}}}
            if et == "model_invocation":
                kw["model"] = str(e.get("model", ""))
                kw["prompt_tokens"] = int(e.get("prompt_tokens", 0) or 0)
                kw["eval_tokens"] = int(e.get("eval_tokens", 0) or 0)
                kw["status"] = ("failed" if e.get("event")
                                == "model_invocation_failed" else "ok")
            if (not explicit_model_events and et == "iteration"
                    and e.get("mode") in (
                        "hybrid", "non_deterministic")):
                if ui < len(usage):
                    u = usage[ui]; ui += 1
                    kw["model"] = str(u.get("model", ""))
                    kw["prompt_tokens"] = int(u.get("prompt_tokens", 0) or 0)
                    kw["eval_tokens"] = int(u.get("eval_tokens", 0) or 0)
                invocation = dict(kw)
                invocation["detail"] = {
                    **dict(kw["detail"]), "_ledger_event": "model_invocation"}
                ch.append("model_invocation", **invocation)
            ch.append(et, **kw)
        return ch

    # --- persistence: the runs/<run_id>/ layout ----------------------------

    def save(self, root: str) -> str:
        d = os.path.join(root, self.run_id)
        if os.path.exists(d):
            raise FileExistsError(
                f"run {self.run_id!r} already exists at {d}; "
                "saved run history is immutable")
        os.makedirs(d, exist_ok=False)
        with open(os.path.join(d, "events.jsonl"), "w") as f:
            for e in self.event_log:
                f.write(json.dumps({**e.body(),
                                    "event_digest": e.event_digest},
                                   default=str) + "\n")
        manifest = {"record_type": "run_history_manifest/v1",
                    "run_id": self.run_id,
                    "parent_run_id": self.parent_run_id,
                    "events": len(self.event_log),
                    "head_digest": (self.event_log[-1].event_digest
                                    if self.event_log else ""),
                    "committed": self._committed}
        with open(os.path.join(d, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=1)
        return d

    @classmethod
    def load(cls, root: str, run_id: str) -> "RunHistory":
        d = os.path.join(root, run_id)
        man = json.load(open(os.path.join(d, "manifest.json")))
        if man.get("record_type") != "run_history_manifest/v1":
            raise RunHistoryIntegrityError(
                "manifest is not a run_history_manifest/v1 record")
        if man.get("run_id") != run_id:
            raise RunHistoryIntegrityError(
                "manifest run_id does not match the requested run")
        ch = cls(run_id, parent_run_id=man.get("parent_run_id", ""))
        for line in open(os.path.join(d, "events.jsonl")):
            row = json.loads(line)
            dig = row.pop("event_digest")
            row["consumed_refs"] = tuple(row.get("consumed_refs", ()))
            row["produced_refs"] = tuple(row.get("produced_refs", ()))
            ev = RunHistoryEvent(**row)
            ev.event_digest = dig
            ch.event_log.append(ev)
        ch._committed = man.get("committed", False)
        verification = ch.verify_chain()
        expected_head = str(man.get("head_digest", ""))
        observed_head = (ch.event_log[-1].event_digest
                         if ch.event_log else "")
        if (not verification["intact"]
                or int(man.get("events", -1)) != len(ch.event_log)
                or expected_head != observed_head):
            raise RunHistoryIntegrityError(
                "saved event log does not match its manifest or digest chain")
        return ch
    # --- OTLP-shaped export (a projection, never the store) ----------------

    def to_otel_spans(self) -> list:
        """Return the one canonical safe OpenTelemetry projection as dicts."""
        from dataclasses import asdict
        from .otel_export import run_history_to_spans

        records = run_history_to_spans(self, run_id=self.run_id)
        return [asdict(record) for record in records]


def verify_saved_run(root: str, run_id: str) -> dict:
    """Read back one saved run at the owning storage boundary and verify it."""
    history = RunHistory.load(root, run_id)
    chain = history.verify_chain()
    return {
        "run_id": run_id, "events": len(history.event_log),
        "head_digest": (history.event_log[-1].event_digest
                        if history.event_log else ""),
        "chain_intact": chain["intact"],
        "broken_at": chain["broken_at"],
        "path": os.path.join(root, run_id),
    }


def recorded_output_handler(run_history: RunHistory, base_handler,
                            semantic_steps=("research",)):
    """Recorded-output REPLAY: a handler wrapper that serves the originally
    recorded outputs for semantic steps (no model is called), and delegates
    everything else to ``base_handler`` — test orchestration changes without
    paying for the calls again."""
    from ..loop.recursive_loop import StepOutcome
    recorded = {}
    for e in run_history.event_log:
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
#: loop.spawned.started, model.invocation.*, user_feedback_intelligence.*); kinds
#: neither vocabulary names pass through under "x." so the projection is
#: TOTAL and LOSSLESS, never silently dropping events.
# The canonical vocabulary lives in `event_vocabulary` (split out when this
# module crossed the size cap).  Re-exported here so every existing import
# site keeps working and the vocabulary keeps one home.
from .event_vocabulary import (                                # noqa: E402
    EVENT_FAMILIES, _CANONICAL_EVENT_MAP, _EVENT_TYPE_FAMILY,
    family_of, to_canonical_events, canonical_event_coverage)


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
                "passed": False, "missing_dependency": "duckdb",
                "detail": "FAILED: missing duckdb. Reinstall with: python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git"})
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

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
