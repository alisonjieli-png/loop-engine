"""Optional one-shot Python transport for registered trusted pure operations.

Both placements execute canonical Loops and the same operation contract. The
worker receives finite JSON over stdin. It cannot select imports or commands.
This is process isolation, NOT a sandbox for generated or untrusted code.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import sys
import time
import uuid

if __name__ == '__main__':
    # Exact repository-owned bootstrap. No request-controlled import paths.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from jsonschema import Draft202012Validator
from loop_engine.core.record_operations_records import canonical_json, content_digest, parse_json
from loop_engine.core.runtime_observer import RuntimeObservationServices
from loop_engine.core.workspace_contracts import CommandRequest, WorkspaceSpec
from loop_engine.core.workspace_local import RestrictedLocalWorkspace
from loop_engine.core.workspace_operations import WorkspaceOperationService
from loop_engine.loop.effect_approval import EffectApprovalService
from loop_engine.loop.encapsulate import as_loop
from loop_engine.loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from loop_engine.loop.recursive_loop import LoopLedger

SEARCH_SCHEMA = {'type': 'object', 'required': ['snapshot_json', 'need', 'limit'],
    'additionalProperties': False, 'properties': {
        'snapshot_json': {'type': 'string', 'maxLength': 900000},
        'need': {'type': 'string', 'minLength': 1, 'maxLength': 4000},
        'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}}}


def implementation_manifest():
    """Compute the trusted installed source closure, not a model-selected file."""
    import loop_engine
    root = Path(loop_engine.__file__).resolve().parent
    sources = [(str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest())
               for path in sorted(root.rglob('*')) if path.is_file()
               and path.suffix in ('.py', '.yaml', '.json', '.jsonl')
               and path.name != 'architecture_conformance.json']
    local = [Path(__file__).resolve(), Path(__file__).with_name('intelligence_resource_catalog.py').resolve()]
    return {'operation_id': 'intelligence.resource_search@1', 'entrypoint': 'intelligence_resource_catalog:search_snapshot',
        'effect_class': 'pure', 'input_schema_digest': content_digest(SEARCH_SCHEMA),
        'runtime_source_digest': content_digest(sources),
        'worker_sources': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in local},
        'interpreter_version': sys.version, 'interpreter_digest': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()}


@dataclass(frozen=True)
class StepPlacement:
    backend: str = 'in_process'
    timeout_seconds: float = 30.0
    maximum_message_bytes: int = 1000000

    def __post_init__(self):
        if (self.backend not in ('in_process', 'python_process')
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0
                or type(self.maximum_message_bytes) is not int or not 1 <= self.maximum_message_bytes <= 2000000):
            raise ValueError('invalid explicit step placement')


def _execute(envelope):
    if set(envelope) != {'record_type', 'invocation_id', 'upstream_loop_ref', 'implementation', 'payload'}:
        raise ValueError('invalid worker envelope fields')
    if envelope['record_type'] != 'loop_step_invocation/v1' or envelope['implementation'] != implementation_manifest():
        raise ValueError('unknown operation or changed implementation')
    if not isinstance(envelope['invocation_id'], str) or not envelope['invocation_id']:
        raise ValueError('invocation identity required')
    Draft202012Validator(SEARCH_SCHEMA).validate(envelope['payload'])
    from intelligence_resource_catalog import search_snapshot
    ledger = LoopLedger(id_namespace=envelope['invocation_id'])
    result = as_loop('search exact granted intelligence descriptor cards', lambda value: search_snapshot(value, ledger=ledger),
        inputs=envelope['payload'], ledger=ledger,
        identity=LoopRoleIdentity(LoopRole.INTELLIGENCE, 'intelligence.search'),
        relationship=LoopRelationship.queried_by(envelope['upstream_loop_ref']))
    if result['error'] is not None or not result['accepted']:
        raise ValueError('worker operation did not complete')
    return {'record_type': 'loop_step_result/v1', 'invocation_id': envelope['invocation_id'],
        'input_digest': content_digest(envelope), 'implementation_digest': content_digest(envelope['implementation']),
        'value': result['value'], 'value_digest': content_digest(result['value']),
        'worker_pid': os.getpid(), 'worker_loop_id': result['loop_id'],
        'worker_run_id': envelope['invocation_id'], 'worker_events': ledger.events,
        'terminal_code': 'ACCEPTED', 'physical_model_calls': 0}


def run_search_step(payload, placement=StepPlacement(), *, authorize=None, runtime=None,
                    upstream_loop_ref='host.resource-discovery'):
    """One request, one execution, no retry or backend fallback on failure."""
    if type(placement) is not StepPlacement or not isinstance(upstream_loop_ref, str) or not upstream_loop_ref:
        raise TypeError('typed placement and upstream Loop identity required')
    Draft202012Validator(SEARCH_SCHEMA).validate(payload)
    envelope = {'record_type': 'loop_step_invocation/v1', 'invocation_id': 'step-' + uuid.uuid4().hex,
        'upstream_loop_ref': upstream_loop_ref, 'implementation': implementation_manifest(),
        'payload': parse_json(canonical_json(payload))}
    raw = canonical_json(envelope)
    if len(raw.encode()) > placement.maximum_message_bytes:
        raise ValueError('step message exceeds its explicit bound; use a selected reference')
    runtime = runtime or RuntimeObservationServices(ledger=LoopLedger())
    start = time.monotonic()
    if placement.backend == 'in_process':
        result = _execute(envelope)
    else:
        if authorize is None:
            raise PermissionError('process launch requires exact host approval')
        approvals = EffectApprovalService(runtime)
        workspace = RestrictedLocalWorkspace(WorkspaceSpec('trusted-step-worker', str(Path(__file__).resolve().parent),
            execution_enabled=True, allowed_commands=(sys.executable,), network_access=False))
        operations = WorkspaceOperationService(workspace, approvals=approvals, runtime=runtime)
        request = CommandRequest((sys.executable, '-I', '-B', str(Path(__file__).resolve())),
            stdin_text=raw, execution_authorized=True, timeout_seconds=placement.timeout_seconds,
            max_output_bytes=placement.maximum_message_bytes)
        plan = operations.plan_command(request, loop_id=upstream_loop_ref,
            reason='Execute this exact pure operation and finite JSON input in a fresh trusted Python process.')
        pending = approvals.create(plan.approval)
        approvals.resume(pending.pending, pending.resume_token, authorize(plan.approval))
        completed = operations.command(request, approval_id=plan.approval.request_id)
        if not completed.ok or completed.output_truncated:
            raise RuntimeError('worker failed without retry: ' + (completed.error_code or 'output_truncated'))
        result = parse_json(completed.stdout)
    if (result.get('record_type') != 'loop_step_result/v1'
            or result.get('invocation_id') != envelope['invocation_id']
            or result.get('input_digest') != content_digest(envelope)
            or result.get('implementation_digest') != content_digest(envelope['implementation'])
            or result.get('value_digest') != content_digest(result.get('value'))
            or result.get('terminal_code') != 'ACCEPTED'):
        raise ValueError('worker result identity or completion mismatch')
    runtime.ledger.record(loop_id=upstream_loop_ref, event='custom',
        step_process_result={key: result[key] for key in ('invocation_id', 'worker_run_id', 'worker_loop_id',
            'input_digest', 'implementation_digest', 'value_digest', 'terminal_code')},
        placement=placement.backend)
    return {**result, 'placement': placement.backend, 'elapsed_seconds': time.monotonic() - start}


if __name__ == '__main__':
    try:
        incoming = sys.stdin.buffer.read(2000001)
        if len(incoming) > 2000000:
            raise ValueError('worker input too large')
        print(canonical_json(_execute(parse_json(incoming.decode('utf-8')))))
    except Exception as error:
        print(canonical_json({'record_type': 'loop_step_failure/v1', 'error_class': type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
