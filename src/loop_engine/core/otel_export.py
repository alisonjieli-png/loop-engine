"""OpenTelemetry projection of saved run history.

Verified Run History is projected into bounded span records. Explicitly raw
ledger events remain compatible through ``RawLedgerEvents`` and are marked
unverified. Raw prompts, tool outputs, secrets, and intelligence bodies are
excluded. Export can target an in-memory verifier or an installed recording
OpenTelemetry tracer without changing the stored run history.

The projection itself runs as a deterministic Loop. Export success does not
change run acceptance or saved-history integrity.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence


SPAN_KINDS = (
    "loop", "model", "tool", "search", "approval", "skill", "context",
    "custom")
_SAFE_KEYS = (
    "loop_id", "spawning_loop_id", "relationship_kind",
    "spawned_by_loop_id", "queried_by_loop_id", "retrieved_by_loop_id",
    "connected_from_loop_ids", "depth", "event", "step", "mode", "provider",
    "model", "operation", "surface", "status", "reason", "error_code",
    "thinking_power", "llm_thinking_power", "accepted", "attempts",
    "prompt_tokens", "eval_tokens", "usage_known",
    "server_id", "tool_name", "effect", "request_digest",
    "has_output_ref", "has_approval", "skill_id", "version", "lifecycle",
    "manifest_digest", "file_count", "raw_digest", "compacted_digest",
    "compacted_bytes", "omitted_bytes", "strategy", "loop_profile",
    "effect_class", "target_digest", "state_revision", "schema_version",
    "action", "artifact_kind", "byte_count", "media_type",
    "estimated_tokens", "token_counter_id", "offloaded")


@dataclass(frozen=True)
class RawLedgerEvents:
    """Explicitly unverified compatibility input for raw runtime events.

    Bare event sequences are refused because they can be mistaken for a
    verified ``RunHistory``. This wrapper keeps live-ledger compatibility and
    marks every projected span and result as unverified.
    """

    events: tuple[Mapping[str, object], ...]
    source_label: str = "raw_ledger_unverified"

    def __post_init__(self) -> None:
        if self.source_label != "raw_ledger_unverified":
            raise ValueError(
                "raw ledger source_label must be raw_ledger_unverified")
        try:
            snapshot = tuple(dict(event) for event in self.events)
        except (TypeError, ValueError) as exc:
            raise TypeError("RawLedgerEvents needs mapping events") from exc
        object.__setattr__(self, "events", snapshot)


@dataclass(frozen=True)
class OtelSpanRecord:
    trace_id: str
    span_id: str
    parent_span_id: str
    name: str
    kind: str
    start_time: float
    end_time: float
    status: str = "unset"
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in SPAN_KINDS:
            raise ValueError(f"kind must be one of {SPAN_KINDS}")
        if self.end_time < self.start_time:
            raise ValueError("span end cannot precede start")


class SpanExporter(Protocol):
    def export(self, spans: Sequence[OtelSpanRecord]) -> object: ...


class InMemorySpanExporter:
    def __init__(self):
        self.spans: list[OtelSpanRecord] = []

    def export(self, spans: Sequence[OtelSpanRecord]) -> int:
        self.spans.extend(spans)
        return len(spans)


class OpenTelemetrySpanExporter:
    """Export records through an installed OpenTelemetry tracer."""

    def __init__(self, tracer_name: str = "loop_engine", *, tracer=None):
        if tracer is None:
            from opentelemetry import trace
            tracer = trace.get_tracer(tracer_name)
        self.tracer = tracer

    def export(self, spans: Sequence[OtelSpanRecord]) -> int:
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode
        pending = list(spans)
        exported_contexts = {}
        exported = 0
        while pending:
            progressed = False
            for record in tuple(pending):
                if (record.parent_span_id
                        and record.parent_span_id not in exported_contexts):
                    continue
                parent_context = None
                if record.parent_span_id:
                    parent = trace.NonRecordingSpan(
                        exported_contexts[record.parent_span_id])
                    parent_context = trace.set_span_in_context(parent)
                attributes = dict(record.attributes)
                attributes["loop_engine.logical_trace_id"] = record.trace_id
                attributes["loop_engine.logical_span_id"] = record.span_id
                if record.parent_span_id:
                    attributes["loop_engine.logical_parent_span_id"] = (
                        record.parent_span_id)
                span = self.tracer.start_span(
                    record.name, context=parent_context,
                    start_time=int(record.start_time * 1_000_000_000),
                    attributes=attributes)
                if not span.is_recording():
                    span.end(end_time=int(record.end_time * 1_000_000_000))
                    raise RuntimeError(
                        "OpenTelemetry tracer returned a non-recording span; "
                        "configure an SDK TracerProvider and span processor")
                exported_contexts[record.span_id] = span.get_span_context()
                if record.status == "error":
                    span.set_status(Status(StatusCode.ERROR))
                elif record.status == "ok":
                    span.set_status(Status(StatusCode.OK))
                span.end(end_time=int(record.end_time * 1_000_000_000))
                pending.remove(record)
                exported += 1
                progressed = True
            if not progressed:
                dangling = sorted({record.parent_span_id for record in pending
                                   if record.parent_span_id})
                raise ValueError(
                    "OpenTelemetry records contain a missing or cyclic "
                    f"parent span reference: {dangling!r}")
        return exported


def _id(prefix: str, *parts) -> str:
    digest = hashlib.sha256("|".join(
        str(part) for part in parts).encode()).hexdigest()
    return f"{prefix}{digest[:24]}"


def _safe_attributes(event: Mapping[str, object]) -> dict:
    values = {}
    for key in _SAFE_KEYS:
        if key not in event:
            continue
        value = event[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            values[f"loop_engine.{key}"] = (
                value[:200] if isinstance(value, str) else value)
        elif (key == "connected_from_loop_ids"
              and isinstance(value, (list, tuple))
              and all(isinstance(item, str) for item in value)):
            values[f"loop_engine.{key}"] = tuple(
                item[:200] for item in value)
    return values


@dataclass(frozen=True)
class _SpanSource:
    events: tuple[Mapping[str, object], ...]
    source_kind: str
    chain_verified: bool


def _normalize_source(source, run_id: str) -> _SpanSource:
    from .run_history import (RunHistory, RunHistoryIntegrityError,
                              as_ledger_events)
    if isinstance(source, RunHistory):
        if source.run_id != run_id:
            raise RunHistoryIntegrityError(
                "OpenTelemetry run_id does not match the RunHistory")
        if not source.verify_chain()["intact"]:
            raise RunHistoryIntegrityError(
                "OpenTelemetry export refused a changed RunHistory chain")
        return _SpanSource(
            tuple(as_ledger_events(source.event_log)),
            "verified_run_history", True)
    if isinstance(source, RawLedgerEvents):
        return _SpanSource(
            tuple(as_ledger_events(source.events)),
            source.source_label, False)
    raise TypeError(
        "OpenTelemetry source must be RunHistory or explicit "
        "RawLedgerEvents")


def _record_parent(parents: dict[str, str], loop_id: str,
                   parent_id: str, source: str) -> None:
    if not parent_id:
        raise ValueError(
            f"spawned Loop {loop_id!r} has no declared parent in {source}")
    existing = parents.get(loop_id)
    if existing and existing != parent_id:
        raise ValueError(
            f"spawned Loop {loop_id!r} has conflicting parents "
            f"{existing!r} and {parent_id!r}")
    parents[loop_id] = parent_id


def _validate_parent_graph(parents: Mapping[str, str],
                           loop_ids: set[str]) -> None:
    for loop_id, parent_id in parents.items():
        if loop_id not in loop_ids:
            raise ValueError(f"spawned Loop {loop_id!r} has no init event")
        if parent_id not in loop_ids:
            raise ValueError(
                f"spawned Loop {loop_id!r} refers to absent parent "
                f"{parent_id!r}")
    for origin in parents:
        seen = set()
        current = origin
        while current in parents:
            if current in seen:
                raise ValueError(
                    "spawned Loop parent relationships contain a cycle")
            seen.add(current)
            current = parents[current]


def run_history_to_spans(source, *, run_id: str
                         ) -> tuple[OtelSpanRecord, ...]:
    """Project verified history or explicit raw events into safe spans."""
    normalized = _normalize_source(source, run_id)
    events = normalized.events
    trace_id = _id("trace_", run_id)
    loop_starts: dict[str, Mapping[str, object]] = {}
    loop_ends: dict[str, Mapping[str, object]] = {}
    spawning_loops: dict[str, str] = {}
    for event in events:
        loop_id = str(event.get("loop_id", ""))
        if not loop_id:
            continue
        if event.get("event") == "init":
            loop_starts.setdefault(loop_id, event)
        elif event.get("event") == "terminal":
            loop_ends[loop_id] = event
        elif event.get("event") == "spawn":
            _record_parent(
                spawning_loops, loop_id,
                str(event.get("spawning_loop_id", "")
                    or event.get("spawned_by_loop_id", "")),
                "spawn event")

    for loop_id, start in loop_starts.items():
        if str(start.get("relationship_kind", "")) == "spawned_by":
            _record_parent(
                spawning_loops, loop_id,
                str(start.get("spawned_by_loop_id", "")),
                "init event")
    _validate_parent_graph(spawning_loops, set(loop_starts))

    source_attributes = {
        "loop_engine.source_kind": normalized.source_kind,
        "loop_engine.chain_verified": normalized.chain_verified,
    }

    spans = []
    loop_span_ids = {loop_id: _id("span_", run_id, loop_id)
                     for loop_id in loop_starts}
    for loop_id, start in loop_starts.items():
        end = loop_ends.get(loop_id, start)
        spawning_loop = spawning_loops.get(loop_id, "")
        status = "ok" if end.get("reason") in ("done", "success_once") \
            else "error" if end.get("reason") else "unset"
        spans.append(OtelSpanRecord(
            trace_id, loop_span_ids[loop_id],
            loop_span_ids.get(spawning_loop, ""),
            f"loop:{loop_id}", "loop",
            float(start.get("ts", 0.0) or 0.0),
            float(end.get("ts", start.get("ts", 0.0)) or 0.0),
            status, {**_safe_attributes({**start, **end}),
                     **source_attributes}))

    event_kinds = {
        "model_led": "model", "model_invocation": "model",
        "model_invocation_failed": "model",
        "capability_call": "tool", "user_guidance": "approval",
        "search": "search", "intelligence.context.retrieved": "search",
        "intelligence.code.retrieved": "search",
        "mcp_call_terminal": "tool",
        "skill_load_terminal": "skill",
        "context_artifact_stored": "context",
        "context_compaction_completed": "context",
        "effect_approval_requested": "approval",
        "effect_approval_decided": "approval",
    }
    for index, event in enumerate(events):
        kind = event_kinds.get(str(event.get("event", "")))
        if kind is None:
            continue
        loop_id = str(event.get("loop_id", ""))
        ts = float(event.get("ts", 0.0) or 0.0)
        failed = ("failed" in str(event.get("event", ""))
                  or event.get("ok") is False
                  or event.get("status") in (
                      "failed", "refused", "unavailable"))
        spans.append(OtelSpanRecord(
            trace_id, _id("span_", run_id, loop_id, index),
            loop_span_ids.get(loop_id, ""),
            ("gen_ai.request" if kind == "model"
             else f"loop_engine.{kind}"), kind,
            ts, ts, "error" if failed else "ok",
            {**_safe_attributes(event), **source_attributes}))
    return tuple(sorted(spans, key=lambda span: (
        span.start_time, span.parent_span_id, span.span_id)))


@dataclass(frozen=True)
class OtelExportResult:
    run_id: str
    spans_projected: int
    spans_exported: int
    loop_id: str
    source_kind: str
    chain_verified: bool


def export_run_history_as_loop(source, *, run_id: str,
                             exporter: SpanExporter) -> OtelExportResult:
    """Project and export spans through a deterministic Loop."""
    from ..loop.encapsulate import as_practitioner_loop

    def project_and_export():
        spans = run_history_to_spans(source, run_id=run_id)
        count = exporter.export(spans)
        return len(spans), int(count or 0)

    wrapped = as_practitioner_loop(
        f"export OpenTelemetry spans for {run_id}", project_and_export)
    projected, exported = wrapped["value"]
    normalized = _normalize_source(source, run_id)
    return OtelExportResult(
        run_id, projected, exported, wrapped["loop_id"],
        normalized.source_kind, normalized.chain_verified)


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    events = [
        {"ts": 1.0, "event": "init", "loop_id": "loop1",
         "goal": "starting", "relationship_kind": "starting",
         "mode": "hybrid", "secret": "must-not-export"},
        {"ts": 2.0, "event": "spawn", "loop_id": "loop2",
         "spawning_loop_id": "loop1"},
        {"ts": 2.1, "event": "init", "loop_id": "loop2",
         "goal": "spawned", "relationship_kind": "spawned_by",
         "spawned_by_loop_id": "loop1"},
        {"ts": 2.2, "event": "model_led", "loop_id": "loop2",
         "provider": "fixture", "model": "m", "prompt_tokens": 4,
         "eval_tokens": 2, "raw_prompt": "private"},
        {"ts": 3.0, "event": "terminal", "loop_id": "loop2",
         "reason": "success_once"},
        {"ts": 4.0, "event": "terminal", "loop_id": "loop1",
         "reason": "done"},
    ]
    from .run_history import RunHistory, RunHistoryIntegrityError
    raw_source = RawLedgerEvents(tuple(events))
    spans = run_history_to_spans(raw_source, run_id="run-1")
    loop_spans = [span for span in spans if span.kind == "loop"]
    spawned = next(span for span in loop_spans if span.name == "loop:loop2")
    starting = next(span for span in loop_spans if span.name == "loop:loop1")
    check("loop_tree_preserves_spawning_span_relationships",
          spawned.parent_span_id == starting.span_id and len(spans) == 3)
    check("raw_prompts_and_secret_fields_are_not_exported",
          "private" not in str(spans) and "must-not-export" not in str(spans))
    service_events = events + [
        {"ts": 2.3, "event": "mcp_call_terminal", "loop_id": "loop2",
         "server_id": "catalog", "tool_name": "lookup",
         "status": "completed", "effect": "pure",
         "request_digest": "a" * 64, "has_output_ref": True,
         "has_approval": False, "error_code": ""},
        {"ts": 2.4, "event": "skill_load_terminal", "loop_id": "loop2",
         "skill_id": "release-review", "version": "2.0.0",
         "lifecycle": "registered", "manifest_digest": "b" * 64,
         "file_count": 2, "status": "completed", "error_code": ""},
        {"ts": 2.5, "event": "context_compaction_completed",
         "loop_id": "loop2", "raw_digest": "c" * 64,
         "compacted_digest": "d" * 64, "compacted_bytes": 80,
         "omitted_bytes": 120, "strategy": "head_tail",
         "loop_profile": "context.compaction.deterministic.v1"},
        {"ts": 2.6, "event": "effect_approval_requested",
         "loop_id": "loop2", "request_id": "approval-1",
         "effect_class": "network_write", "operation": "submit",
         "target_digest": "e" * 64, "status": "pending",
         "state_revision": 1, "schema_version": "approval_state/v1"},
    ]
    service_spans = run_history_to_spans(
        RawLedgerEvents(tuple(service_events)), run_id="run-services")
    by_kind = {span.kind for span in service_spans}
    check("MCP_skill_compaction_and_approval_events_become_safe_spans",
          {"tool", "skill", "context", "approval"} <= by_kind
          and "release-review" in str(service_spans)
          and "raw_prompt" not in str(service_spans))
    check("raw_ledger_compatibility_is_explicitly_marked_unverified",
          all(span.attributes.get("loop_engine.source_kind")
              == "raw_ledger_unverified" for span in spans)
          and all(span.attributes.get("loop_engine.chain_verified") is False
                  for span in spans))
    raw_relabel_refused = False
    try:
        RawLedgerEvents(tuple(events), source_label="verified_run_history")
    except ValueError:
        raw_relabel_refused = True
    check("raw_ledger_source_cannot_claim_a_verified_label",
          raw_relabel_refused)
    bare_events_refused = False
    try:
        run_history_to_spans(events, run_id="run-1")
    except TypeError:
        bare_events_refused = True
    check("bare_event_sequences_cannot_impersonate_verified_run_history",
          bare_events_refused)

    history = RunHistory.from_ledger(events, run_id="run-1")
    history.commit()
    verified_spans = run_history_to_spans(history, run_id="run-1")
    check("verified_run_history_marks_every_span_chain_verified",
          len(verified_spans) == 3
          and all(span.attributes.get("loop_engine.source_kind")
                  == "verified_run_history" for span in verified_spans)
          and all(span.attributes.get("loop_engine.chain_verified") is True
                  for span in verified_spans))
    exporter = InMemorySpanExporter()
    result = export_run_history_as_loop(
        history, run_id="run-1", exporter=exporter)
    check("export_itself_is_a_loop_and_run_history_remains_authoritative",
          result.loop_id.startswith("loop") and result.spans_exported == 3
          and len(exporter.spans) == 3 and result.chain_verified
          and result.source_kind == "verified_run_history")

    tampered = RunHistory.from_ledger(events, run_id="tampered-run")
    tampered.commit()
    tampered.event_log[0].detail["changed_after_commit"] = True
    tampered_refused = False
    try:
        run_history_to_spans(tampered, run_id="tampered-run")
    except RunHistoryIntegrityError:
        tampered_refused = True
    check("changed_run_history_chain_is_refused_before_projection",
          not tampered.verify_chain()["intact"] and tampered_refused)

    absent_parent_refused = False
    try:
        run_history_to_spans(RawLedgerEvents((
            {"ts": 1.0, "event": "spawn", "loop_id": "loop2",
             "spawning_loop_id": "missing-loop"},
            {"ts": 1.1, "event": "init", "loop_id": "loop2",
             "relationship_kind": "spawned_by",
             "spawned_by_loop_id": "missing-loop"},
        )), run_id="missing-parent")
    except ValueError:
        absent_parent_refused = True
    check("declared_spawned_relationship_with_absent_parent_is_refused",
          absent_parent_refused)

    sdk_relationships_ok = False
    sdk_detail = "OpenTelemetry SDK is not installed"
    dangling_failed = False
    non_recording_failed = False
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter as SdkInMemorySpanExporter)
        sdk_exporter = SdkInMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(sdk_exporter))
        actual = OpenTelemetrySpanExporter(
            tracer=provider.get_tracer("loop_engine.self_test"))
        actual.export(verified_spans)
        finished = sdk_exporter.get_finished_spans()
        by_name = {span.name: span for span in finished}
        actual_starting = by_name["loop:loop1"]
        actual_spawned = by_name["loop:loop2"]
        actual_model = by_name["gen_ai.request"]
        sdk_relationships_ok = (
            actual_spawned.parent.span_id == actual_starting.context.span_id
            and actual_model.parent.span_id == actual_spawned.context.span_id
            and len({span.context.trace_id for span in finished}) == 1
            and all(span.attributes.get("loop_engine.logical_trace_id")
                    == verified_spans[0].trace_id for span in finished))
        sdk_detail = "actual SDK spans share one trace and spawning chain"
        try:
            actual.export((OtelSpanRecord(
                "trace_missing", "span_spawned", "span_missing",
                "orphan", "loop", 1.0, 2.0),))
        except ValueError:
            dangling_failed = True
        from opentelemetry import trace
        try:
            OpenTelemetrySpanExporter(
                tracer=trace.NoOpTracerProvider().get_tracer(
                    "loop_engine.non_recording")).export((
                        OtelSpanRecord(
                            "trace_noop", "span_noop", "", "noop",
                            "custom", 1.0, 1.0),))
        except RuntimeError:
            non_recording_failed = True
        provider.shutdown()
    except ImportError as exc:
        sdk_relationships_ok = False
        sdk_detail = (
            "OpenTelemetry SDK dependency is missing: "
            f"{type(exc).__name__}: {exc}")
    check("installed_OpenTelemetry_export_preserves_the_spawning_chain",
          sdk_relationships_ok, sdk_detail)
    check("missing_spawning_span_references_fail_closed", dangling_failed)
    check("non_recording_SDK_tracer_cannot_report_export_success",
          non_recording_failed)

    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
