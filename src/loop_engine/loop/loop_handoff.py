"""Loop handoff: run one Loop in another process and merge its history back.

Architectural role: the smallest unit of distribution the runtime supports.
A parent Loop exports one typed request (goal, exact definition, ledger
namespace, causal position). A remote process executes that request as an
ordinary canonical ``Loop`` on its own namespaced ledger and returns one
envelope: the remote events, their digest, the terminal result, and an
idempotency key. The parent verifies the digest, refuses a second merge of
the same envelope, appends the remote events to its shared ledger, records
the return as a spawned return, and folds the remote spawn count into its
own result. The envelope and request are passive records; every operation
runs inside a Loop.

What this does not claim: a remote Loop executes under its own effect
authority and provider budget; the parent trusts the envelope's digest, not
its content. Remote outputs remain candidate data for the parent to verify.

Owns:
    - LoopHandoffRequest: the parameter object shipped to the remote process.
    - LoopHandoffEnvelope: the passive result record with digest and
      idempotency key.
    - execute_handoff(): the remote-side operation.
    - merge_handoff(): the parent-side operation.

Does not own: transport (callers choose subprocess, queue, or network), the
Loop runtime (loop.recursive_loop), or Run History projection
(core.run_history).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .loop_definition import LoopDefinition
from .recursive_loop import (Loop, LoopConfig, LoopError, LoopLedger,
                             _default_registered_identity)

HANDOFF_SCHEMA_VERSION = "loop_handoff/v1"


class LoopHandoffError(LoopError):
    """A handoff request or envelope failed its typed contract."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _json_safe(value):
    """Copy ledger events into plain JSON values without changing keys."""
    return json.loads(json.dumps(value, default=str))


@dataclass(frozen=True)
class LoopHandoffRequest:
    """Everything a remote process needs to run one Loop for a parent."""

    goal: str
    definition: dict
    namespace: str
    parent_loop_id: str
    parent_event_index: int
    request_id: str = ""
    schema_version: str = HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != HANDOFF_SCHEMA_VERSION:
            raise LoopHandoffError("unsupported handoff schema version")
        if not self.goal.strip() or not self.parent_loop_id.strip():
            raise LoopHandoffError("a handoff needs a goal and a parent Loop")
        if (not self.namespace.strip() or any(c.isspace() for c in self.namespace)
                or "." in self.namespace):
            raise LoopHandoffError(
                "namespace must be one bounded token without spaces or dots")
        if not isinstance(self.definition, dict) or not self.definition:
            raise LoopHandoffError("definition must be a LoopDefinition mapping")
        LoopDefinition.from_dict(self.definition)  # fail closed early
        if (isinstance(self.parent_event_index, bool)
                or not isinstance(self.parent_event_index, int)
                or self.parent_event_index < 0):
            raise LoopHandoffError("parent_event_index must be a count")
        expected = _digest({
            "goal": self.goal, "definition": self.definition,
            "namespace": self.namespace, "parent_loop_id": self.parent_loop_id,
            "parent_event_index": self.parent_event_index})
        if self.request_id and self.request_id != expected:
            raise LoopHandoffError("request_id does not match the request")
        object.__setattr__(self, "request_id", expected)

    @classmethod
    def create(cls, parent: Loop, goal: str, config: "LoopConfig | None" = None,
               *, namespace: str) -> "LoopHandoffRequest":
        """Compose the remote Loop's exact definition from the parent's side."""
        from .loop_doctrine import baseline_for_practitioner
        selected = config or LoopConfig(
            framework="custom", custom_steps=("act",),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",))
        definition = LoopDefinition.from_runtime(
            identity=_default_registered_identity(selected),
            contract=baseline_for_practitioner(goal, output_roles=("result",)),
            config=selected,
            installed_executor_modes=selected.allowable_modes,
            compatibility=True)
        return cls(goal=goal, definition=definition.to_dict(),
                   namespace=namespace, parent_loop_id=parent.loop_id,
                   parent_event_index=len(parent.ledger.events))

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id, "goal": self.goal,
            "definition": self.definition, "namespace": self.namespace,
            "parent_loop_id": self.parent_loop_id,
            "parent_event_index": self.parent_event_index,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopHandoffRequest":
        return cls(
            goal=str(value["goal"]), definition=dict(value["definition"]),
            namespace=str(value["namespace"]),
            parent_loop_id=str(value["parent_loop_id"]),
            parent_event_index=int(value["parent_event_index"]),
            request_id=str(value.get("request_id", "")),
            schema_version=str(value.get("schema_version", "")))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> "LoopHandoffRequest":
        return cls.from_dict(json.loads(value))


@dataclass(frozen=True)
class LoopHandoffEnvelope:
    """The remote Loop's history and result, digest-bound and idempotent."""

    request_id: str
    namespace: str
    parent_loop_id: str
    parent_event_index: int
    remote_loop_id: str
    terminal_code: str
    stopped: str
    output: str
    steps_run: int
    model_calls: int
    spawned: int
    events: tuple
    events_digest: str
    idempotency_key: str = ""
    schema_version: str = HANDOFF_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != HANDOFF_SCHEMA_VERSION:
            raise LoopHandoffError("unsupported handoff schema version")
        events = tuple(_json_safe(list(self.events)))
        if not events:
            raise LoopHandoffError("a handoff envelope needs remote events")
        prefix = self.namespace + "."
        if any(not str(event.get("loop_id", "")).startswith(prefix)
               for event in events):
            raise LoopHandoffError(
                "every remote event must carry a loop id in the envelope "
                "namespace")
        if not self.remote_loop_id.startswith(prefix):
            raise LoopHandoffError("remote_loop_id must be namespaced")
        digest = _digest(list(events))
        if digest != self.events_digest:
            raise LoopHandoffError(
                "remote events do not match the envelope digest")
        key = _digest({"request_id": self.request_id,
                       "events_digest": self.events_digest})
        if self.idempotency_key and self.idempotency_key != key:
            raise LoopHandoffError("idempotency key does not match")
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "idempotency_key", key)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id, "namespace": self.namespace,
            "parent_loop_id": self.parent_loop_id,
            "parent_event_index": self.parent_event_index,
            "remote_loop_id": self.remote_loop_id,
            "terminal_code": self.terminal_code, "stopped": self.stopped,
            "output": self.output, "steps_run": self.steps_run,
            "model_calls": self.model_calls, "spawned": self.spawned,
            "events": _json_safe(list(self.events)),
            "events_digest": self.events_digest,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopHandoffEnvelope":
        return cls(
            request_id=str(value["request_id"]),
            namespace=str(value["namespace"]),
            parent_loop_id=str(value["parent_loop_id"]),
            parent_event_index=int(value["parent_event_index"]),
            remote_loop_id=str(value["remote_loop_id"]),
            terminal_code=str(value["terminal_code"]),
            stopped=str(value.get("stopped", "")),
            output=str(value.get("output", "")),
            steps_run=int(value.get("steps_run", 0)),
            model_calls=int(value.get("model_calls", 0)),
            spawned=int(value.get("spawned", 0)),
            events=tuple(value["events"]),
            events_digest=str(value["events_digest"]),
            idempotency_key=str(value.get("idempotency_key", "")),
            schema_version=str(value.get("schema_version", "")))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> "LoopHandoffEnvelope":
        return cls.from_dict(json.loads(value))


def execute_handoff(request: LoopHandoffRequest, *,
                    handler) -> LoopHandoffEnvelope:
    """Remote side: run the requested Loop on a namespaced ledger."""
    if not isinstance(request, LoopHandoffRequest):
        raise LoopHandoffError("execute_handoff needs a LoopHandoffRequest")
    definition = LoopDefinition.from_dict(request.definition)
    ledger = LoopLedger(id_namespace=request.namespace)
    loop = Loop(request.goal, definition.to_loop_config(),
                identity=definition.identity, ledger=ledger)
    result = loop.run(handler=handler)
    events = _json_safe(list(ledger.events))
    return LoopHandoffEnvelope(
        request_id=request.request_id, namespace=request.namespace,
        parent_loop_id=request.parent_loop_id,
        parent_event_index=request.parent_event_index,
        remote_loop_id=loop.loop_id, terminal_code=result.terminal_code,
        stopped=result.stopped, output=str(result.output),
        steps_run=result.steps_run, model_calls=result.model_calls,
        spawned=result.spawned, events=tuple(events),
        events_digest=_digest(events))


def merged_handoff_keys(parent: Loop) -> set:
    return {str(event.get("idempotency_key")) for event in parent.ledger.events
            if event.get("event") == "custom"
            and event.get("custom_kind") == "handoff_merged"}


def merge_handoff(parent: Loop, envelope: LoopHandoffEnvelope) -> dict:
    """Parent side: verify, refuse duplicates, append, and record the return."""
    if not isinstance(envelope, LoopHandoffEnvelope):
        raise LoopHandoffError("merge_handoff needs a LoopHandoffEnvelope")
    if envelope.parent_loop_id != parent.loop_id:
        raise LoopHandoffError(
            f"envelope addresses {envelope.parent_loop_id!r}, not "
            f"{parent.loop_id!r}")
    if envelope.parent_event_index > len(parent.ledger.events):
        raise LoopHandoffError(
            "envelope claims a causal position the parent ledger never reached")
    if envelope.idempotency_key in merged_handoff_keys(parent):
        raise LoopHandoffError(
            "this handoff envelope was already merged; a second merge would "
            "replay its history")
    local_ids = parent.ledger.loops()
    remote_ids = {str(event.get("loop_id")) for event in envelope.events}
    if local_ids & remote_ids:
        raise LoopHandoffError("remote loop ids collide with the parent ledger")
    for event in envelope.events:
        parent.ledger.events.append(
            {**event, "handoff_request_id": envelope.request_id})
    parent.ledger.record(
        loop_id=parent.loop_id, event="spawned_return",
        spawned_loop_id=envelope.remote_loop_id, depth=parent.depth + 1,
        reason=envelope.stopped or envelope.terminal_code,
        steps_run=envelope.steps_run, handoff=True)
    parent.ledger.record(
        loop_id=parent.loop_id, event="custom", custom_kind="handoff_merged",
        idempotency_key=envelope.idempotency_key,
        request_id=envelope.request_id, namespace=envelope.namespace,
        remote_loop_id=envelope.remote_loop_id,
        remote_events=len(envelope.events),
        events_digest=envelope.events_digest,
        terminal_code=envelope.terminal_code,
        remote_model_calls=envelope.model_calls)
    parent._note_spawned(1 + envelope.spawned)
    return {
        "merged_events": len(envelope.events),
        "remote_loop_id": envelope.remote_loop_id,
        "idempotency_key": envelope.idempotency_key,
        "terminal_code": envelope.terminal_code,
    }


_REMOTE_SCRIPT = """
import json, sys
from loop_engine.loop.loop_handoff import LoopHandoffRequest, execute_handoff
from loop_engine.loop.recursive_loop import StepOutcome
request = LoopHandoffRequest.from_json(sys.stdin.read())
envelope = execute_handoff(request, handler=lambda loop, step, context:
    StepOutcome(output=f"remote:{step}", mode="deterministic"))
sys.stdout.write(envelope.to_json())
"""


def self_test() -> dict:
    """Prove a real two-process handoff with digest, idempotency, and chain."""
    import os
    import subprocess
    import sys
    from pathlib import Path
    from ..core.run_history import RunHistory
    from .recursive_loop import StepOutcome

    parent = Loop("coordinate remote work", LoopConfig(
        framework="custom", custom_steps=("act",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",)))
    request = LoopHandoffRequest.create(
        parent, "count the rows of one table", namespace="worker_a")
    src_root = str(Path(__file__).resolve().parents[2])
    env = dict(os.environ)
    env["PYTHONPATH"] = src_root + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    completed = subprocess.run(
        [sys.executable, "-c", _REMOTE_SCRIPT], input=request.to_json(),
        capture_output=True, text=True, env=env, timeout=120)
    remote_ok = completed.returncode == 0
    envelope = None
    if remote_ok:
        envelope = LoopHandoffEnvelope.from_json(completed.stdout)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"test": name, "passed": bool(passed),
                       "detail": str(detail)[:240]})

    check("remote_process_executes_the_request_as_a_canonical_loop",
          remote_ok and envelope is not None
          and envelope.remote_loop_id.startswith("worker_a.")
          and envelope.terminal_code == "ACCEPTED"
          and envelope.output == "remote:act"
          and envelope.request_id == request.request_id,
          completed.stderr[-200:] if not remote_ok else envelope.remote_loop_id)
    if envelope is None:
        return {"module": "loop.loop_handoff", "passed": False,
                "tests": checks}

    def parent_handler(loop, step, context):
        summary = merge_handoff(loop, envelope)
        return StepOutcome(output=f"merged:{summary['remote_loop_id']}",
                           mode="deterministic")

    result = parent.run(handler=parent_handler)
    merged_ids = {str(e.get("loop_id")) for e in parent.ledger.events
                  if str(e.get("loop_id", "")).startswith("worker_a.")}
    history = RunHistory.from_ledger(parent.ledger.events,
                                     run_id="handoff-proof")
    history.commit()
    chain = history.verify_chain()
    check("merged_history_keeps_one_intact_chain_and_a_recorded_return",
          result.terminal_code == "ACCEPTED" and merged_ids
          and chain.get("intact") is True
          and any(e.get("event") == "spawned_return" and e.get("handoff")
                  for e in parent.ledger.events)
          and result.spawned == 1,
          f"remote loops={sorted(merged_ids)} spawned={result.spawned}")
    duplicate_refused = False
    try:
        merge_handoff(parent, envelope)
    except LoopHandoffError as exc:
        duplicate_refused = "already merged" in str(exc)
    tampered = envelope.to_dict()  # to_dict copies; the envelope is untouched
    tampered["events"][0]["goal"] = "something else"
    tampered_refused = False
    try:
        LoopHandoffEnvelope.from_dict(tampered)
    except LoopHandoffError:
        tampered_refused = True
    misaddressed = LoopHandoffEnvelope.from_dict(
        {**envelope.to_dict(), "parent_loop_id": "loop999"})
    misaddressed_refused = False
    try:
        merge_handoff(parent, misaddressed)
    except LoopHandoffError:
        misaddressed_refused = True
    check("duplicate_tampered_and_misaddressed_envelopes_are_refused",
          duplicate_refused and tampered_refused and misaddressed_refused,
          f"{duplicate_refused} {tampered_refused} {misaddressed_refused}")
    bad_namespace = False
    try:
        LoopHandoffRequest.create(parent, "x", namespace="a.b")
    except LoopHandoffError:
        bad_namespace = True
    check("request_identity_is_content_addressed_and_namespaces_are_bounded",
          bad_namespace and len(request.request_id) == 64
          and LoopHandoffRequest.from_json(request.to_json()) == request,
          request.request_id[:16])
    return {"module": "loop.loop_handoff",
            "passed": all(item["passed"] for item in checks),
            "tests": checks}
