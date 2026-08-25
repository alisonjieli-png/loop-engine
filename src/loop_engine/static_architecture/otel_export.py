"""OpenTelemetry projection of saved run history.

Saved events are projected into bounded span records. Raw prompts, tool
outputs, secrets, and intelligence bodies are excluded. Export can target an
in-memory verifier or an installed OpenTelemetry tracer without changing the
stored run history.

The projection itself runs as a deterministic Loop. Export success does not
change run acceptance or saved-history integrity.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence


SPAN_KINDS = ("loop", "model", "tool", "search", "approval", "custom")
_SAFE_KEYS = (
    "loop_id", "spawning_loop_id", "relationship_kind",
    "spawned_by_loop_id", "queried_by_loop_id", "retrieved_by_loop_id",
    "connected_from_loop_ids", "depth", "event", "step", "mode", "provider",
    "model", "operation", "surface", "status", "reason", "error_code",
    "thinking_power", "llm_thinking_power", "accepted", "attempts",
    "prompt_tokens", "eval_tokens", "usage_known")


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


def run_history_to_spans(events: Sequence[Mapping[str, object]], *,
                       run_id: str) -> tuple[OtelSpanRecord, ...]:
    """Project one event history into deterministic, content-safe spans."""
    from .run_history import as_ledger_events
    events = as_ledger_events(events)
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
            spawning_loops[loop_id] = str(
                event.get("spawning_loop_id", ""))

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
            status, _safe_attributes({**start, **end})))

    event_kinds = {
        "model_led": "model", "model_invocation": "model",
        "model_invocation_failed": "model",
        "capability_call": "tool", "user_guidance": "approval",
        "search": "search", "intelligence.context.retrieved": "search",
        "intelligence.code.retrieved": "search",
    }
    for index, event in enumerate(events):
        kind = event_kinds.get(str(event.get("event", "")))
        if kind is None:
            continue
        loop_id = str(event.get("loop_id", ""))
        ts = float(event.get("ts", 0.0) or 0.0)
        failed = ("failed" in str(event.get("event", ""))
                  or event.get("ok") is False)
        spans.append(OtelSpanRecord(
            trace_id, _id("span_", run_id, loop_id, index),
            loop_span_ids.get(loop_id, ""),
            ("gen_ai.request" if kind == "model"
             else f"loop_engine.{kind}"), kind,
            ts, ts, "error" if failed else "ok", _safe_attributes(event)))
    return tuple(sorted(spans, key=lambda span: (
        span.start_time, span.parent_span_id, span.span_id)))


@dataclass(frozen=True)
class OtelExportResult:
    run_id: str
    spans_projected: int
    spans_exported: int
    loop_id: str


def export_run_history_as_loop(events, *, run_id: str,
                             exporter: SpanExporter) -> OtelExportResult:
    """Project and export spans through a deterministic Loop."""
    from ..loop.encapsulate import as_practitioner_loop

    def project_and_export():
        spans = run_history_to_spans(events, run_id=run_id)
        count = exporter.export(spans)
        return len(spans), int(count or 0)

    wrapped = as_practitioner_loop(
        f"export OpenTelemetry spans for {run_id}", project_and_export)
    projected, exported = wrapped["value"]
    return OtelExportResult(
        run_id, projected, exported, wrapped["loop_id"])


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
    spans = run_history_to_spans(events, run_id="run-1")
    loop_spans = [span for span in spans if span.kind == "loop"]
    spawned = next(span for span in loop_spans if span.name == "loop:loop2")
    starting = next(span for span in loop_spans if span.name == "loop:loop1")
    check("loop_tree_preserves_spawning_span_relationships",
          spawned.parent_span_id == starting.span_id and len(spans) == 3)
    check("raw_prompts_and_secret_fields_are_not_exported",
          "private" not in str(spans) and "must-not-export" not in str(spans))
    exporter = InMemorySpanExporter()
    result = export_run_history_as_loop(
        events, run_id="run-1", exporter=exporter)
    check("export_itself_is_a_loop_and_run_history_remains_authoritative",
          result.loop_id.startswith("loop") and result.spans_exported == 3
          and len(exporter.spans) == 3)

    sdk_relationships_ok = False
    sdk_detail = "OpenTelemetry SDK is not installed"
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
        actual.export(spans)
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
                    == spans[0].trace_id for span in finished))
        sdk_detail = "actual SDK spans share one trace and spawning chain"
        provider.shutdown()
    except ImportError as exc:
        sdk_relationships_ok = False
        sdk_detail = (
            "OpenTelemetry SDK dependency is missing: "
            f"{type(exc).__name__}: {exc}")
    check("installed_OpenTelemetry_export_preserves_the_spawning_chain",
          sdk_relationships_ok, sdk_detail)

    dangling_failed = False
    try:
        OpenTelemetrySpanExporter(
            tracer=(provider.get_tracer("loop_engine.dangling")
                    if "provider" in locals() else None)).export((
                        OtelSpanRecord(
                            "trace_missing", "span_spawned", "span_missing",
                            "orphan", "loop", 1.0, 2.0),))
    except ValueError:
        dangling_failed = True
    except ImportError:
        dangling_failed = True
    check("missing_spawning_span_references_fail_closed", dangling_failed)

    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
