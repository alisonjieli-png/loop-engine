"""Loop Engine saved run history.

This internal service owns the append-only, hash-chained event record, its
ledger projection, persistence, integrity check, replay output, and telemetry
projection. It also re-exports the established saved-run path and bound product
outcome contracts for compatible callers.

Playback and analytics remain separate projections. A committed history is
never edited; replay or a fork creates new work. Provider usage preserves
positive, missing, partial, and real-zero observations.

Verification lives in ``run_history_checks.self_test()`` and the focused
usage checks.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field

from .run_history_paths import (
    RUNS_DIR_ENV as RUNS_DIR_ENV,
)
from .run_history_paths import (
    RunHistoryIntegrityError,
    saved_run_ids,
    validated_run_id,
)
from .run_history_paths import (
    default_runs_dir as default_runs_dir,
)
from .run_history_usage import apply_model_usage, prepare_model_event

EVENT_TYPES = ("run_started", "loop_init", "loop_spawn", "iteration",
               "capability_search", "context_retrieval", "code_execution",
               "model_invocation", "fallback", "model_boundary_deferred",
               "budget_stop", "evaluation", "terminal", "cancel",
               "solution_built", "solution_run", "learning", "custom")

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
        if (key not in out and event_type == "model_invocation"
                and key in ("prompt_tokens", "eval_tokens")):
            out[key] = value
        elif key not in out and value not in (None, "", 0):
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
    prompt_tokens: "int | None" = 0
    eval_tokens: "int | None" = 0
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

    def __init__(self, run_id: str, *, parent_run_id: str = "",
                 authority_key=None):
        self.run_id = validated_run_id(run_id)
        self.parent_run_id = (
            validated_run_id(parent_run_id) if parent_run_id else "")
        self.event_log: list[RunHistoryEvent] = []
        self._committed = False
        # Authorship. With a key, every append must carry a tag that
        # verifies under it, so a handler that reaches append() directly
        # cannot forge a verify, a model_invocation, or a terminal for a
        # Loop it does not own. Without a key nothing changes, and the
        # manifest says so: "unverified" is a statement, not an omission.
        self._authority_key = authority_key

    @property
    def authorship(self) -> str:
        """Which of three states this history is in, honestly.

        ``verified``   a key is held and every append was checked against it.
        ``signed``     authorship tags are present but no key is held, which
                       is what a saved history looks like when it is loaded
                       back: the evidence is on disk and this process cannot
                       check it. Reporting ``unverified`` here (the earlier
                       behaviour) told a reader the run was unsigned when it
                       was signed, which is the wrong direction to be wrong.
        ``unverified`` no key and no tags.
        """
        if self._authority_key is not None:
            return "verified"
        if any("authorship_tag" in (event.detail or {})
               for event in self.event_log):
            return "signed"
        return "unverified"

    def _envelope_shape(self, body: dict) -> dict:
        """What a facade's fields look like once the ledger has stored them."""
        fields = dict(body)
        event_type = fields.pop("event_type")
        if event_type == "model_invocation":
            prepare_model_event(fields)
        fields.pop("ts", None)
        return RunHistoryEvent(event_type=event_type, run_id=self.run_id,
                               sequence_number=0, ts=0.0, prev_digest="",
                               **fields).body()

    def recorder_for(self, loop_id: str, allowed_event_types):
        """The only thing a handler should be handed. See run_history_authorship."""
        from .run_history_authorship import RecorderFacade, RunAuthorshipError
        if self._authority_key is None:
            raise RunAuthorshipError(
                "this history has no authority key, so it cannot issue a "
                "recorder facade; build it with authority_key=")
        return RecorderFacade(self._authority_key, loop_id,
                              frozenset(allowed_event_types),
                              normalize=self._envelope_shape)

    # --- append / commit ---------------------------------------------------

    def append(self, event_type: str, **kw) -> RunHistoryEvent:
        if self._committed:
            raise ValueError("run_history committed — history is immutable; "
                             "start a NEW run (fork) instead")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type {event_type!r}")
        if event_type == "model_invocation":
            prepare_model_event(kw)
        from .run_history_authorship import AUTHORSHIP_TAG_FIELD, RunAuthorshipError
        tag = kw.pop(AUTHORSHIP_TAG_FIELD, None)
        prev = self.event_log[-1].event_digest if self.event_log else ""
        ev = RunHistoryEvent(event_type=event_type, run_id=self.run_id,
                            sequence_number=len(self.event_log),
                            ts=kw.pop("ts", time.time()),
                            prev_digest=prev, **kw)
        if self._authority_key is not None:
            if tag is None:
                raise RunAuthorshipError(
                    f"{event_type!r} for loop {ev.loop_id!r} carries no "
                    "authorship tag; on a keyed history every event is "
                    "recorded through a RecorderFacade, never appended directly")
            if not self._authority_key.verify(ev.body(), tag):
                raise RunAuthorshipError(
                    f"{event_type!r} for loop {ev.loop_id!r} carries an "
                    "authorship tag that does not verify under this run's key")
        if tag is not None:
            ev.detail = {**ev.detail, AUTHORSHIP_TAG_FIELD: tag}
        ev.event_digest = _digest(ev.body())
        self.event_log.append(ev)
        return ev

    def verify_authorship(self) -> dict:
        """Every event's tag checked under this history's key."""
        from .run_history_authorship import verify_authorship
        if self._authority_key is None:
            return {"ok": False, "authorship": "unverified",
                    "reason": "no authority key on this history"}
        return {"authorship": "verified", **verify_authorship(
            self.event_log, self._authority_key)}

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
            if (et == "custom"
                    and e.get("custom_kind") == "terminal_handler_return"
                    and e.get("reported_model_calls")):
                # Work a handler reports after cancellation is never admitted
                # as output, but the model calls it made were real; the
                # canonical history counts them instead of showing zero.
                et = "model_invocation"
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
                apply_model_usage(kw, e)
                kw["status"] = ("failed" if e.get("event")
                                == "model_invocation_failed" else "ok")
            if (not explicit_model_events and et == "iteration"
                    and e.get("mode") in (
                        "hybrid", "non_deterministic")):
                apply_model_usage(kw, {})
                if ui < len(usage):
                    u = usage[ui]
                    ui += 1
                    kw["model"] = str(u.get("model", ""))
                    apply_model_usage(kw, u)
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
        run_id = validated_run_id(run_id)
        d = os.path.join(root, run_id)
        with open(os.path.join(d, "manifest.json"), encoding="utf-8") as stream:
            man = json.load(stream)
        if man.get("record_type") != "run_history_manifest/v1":
            raise RunHistoryIntegrityError(
                "manifest is not a run_history_manifest/v1 record")
        if man.get("run_id") != run_id:
            raise RunHistoryIntegrityError(
                "manifest run_id does not match the requested run")
        ch = cls(run_id, parent_run_id=man.get("parent_run_id", ""))
        with open(os.path.join(d, "events.jsonl"), encoding="utf-8") as stream:
            for line in stream:
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


from .product_outcome_store import (  # noqa: E402
    PRODUCT_OUTCOME_FILENAME,
    bind_product_outcome,
    load_saved_run_bundle,
)
from .product_outcome_store import (  # noqa: E402
    ProductOutcomeRef as ProductOutcomeRef,
)
from .product_outcome_store import (  # noqa: E402
    SavedRunBundle as SavedRunBundle,
)


def verify_saved_run(root: str, run_id: str) -> dict:
    """Read back one saved run at the owning storage boundary and verify it."""
    bundle = load_saved_run_bundle(root, run_id)
    history = bundle.history
    chain = history.verify_chain()
    return {
        "run_id": run_id, "events": len(history.event_log),
        "head_digest": (history.event_log[-1].event_digest
                        if history.event_log else ""),
        "chain_intact": chain["intact"],
        "broken_at": chain["broken_at"],
        "path": os.path.join(root, run_id),
        "product_outcome_bound": bundle.outcome is not None,
        "product_outcome_digest": (
            bundle.outcome_ref.content_digest if bundle.outcome_ref else ""),
        "terminal_code": (
            str(bundle.outcome.get("terminal_code") or "")
            if bundle.outcome else ""),
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
from .event_vocabulary import (  # noqa: E402
    _CANONICAL_EVENT_MAP,
    _EVENT_TYPE_FAMILY,
    EVENT_FAMILIES,
    canonical_event_coverage,
    family_of,
    to_canonical_events,
)

