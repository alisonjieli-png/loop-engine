"""Export one exact managed-record revision through approved workspace writes.

The record service owns CRUD and immutable revisions. This tool produces a
non-authoritative JSON view; it never updates catalog rows or revision bodies.
Host arguments select storage, scope, revision, and destination. No raw SQL.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.record_operations import (
    RecordOperationService, RecordOperationServices, RecordStorageBinding, effect_digest)
from loop_engine.core.record_operations_records import (
    RecordOperationPolicy, RecordOperationRequest, canonical_json, content_digest, parse_json)
from loop_engine.core.runtime_observer import RuntimeObservationServices
from loop_engine.core.workspace_contracts import FileOperation, FileRequest, WorkspaceSpec
from loop_engine.core.workspace_local import RestrictedLocalWorkspace
from loop_engine.core.workspace_operations import WorkspaceOperationService
from loop_engine.loop.effect_approval import ApprovalDecision, EffectApprovalService
from loop_engine.loop.recursive_loop import LoopLedger

RENDERER_VERSION = 'managed_record_json_export/v1'


@dataclass(frozen=True)
class ExportRequest:
    record_id: str
    record_version: str
    output_path: str
    generated_at: str
    expected_output_digest: str = ''

    def __post_init__(self):
        parsed = datetime.fromisoformat(self.generated_at.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('generated_at needs an explicit timezone')
        if not self.record_version:
            raise ValueError('export requires an exact record version')


def export_record(service, workspace, request, *, approved_effect_digest=''):
    """Read through the record service; plan or execute one exact file effect."""
    result = service.execute(RecordOperationRequest(
        'get', record_id=request.record_id, record_version=request.record_version,
        materialize=True, maximum_history_depth=service.policy.maximum_history_depth))
    if (result.status not in ('found', 'retired') or len(result.records) != 1
            or not result.document_json or result.records[0].get('managed') is not True
            or result.records[0]['record_version'] != request.record_version):
        raise ValueError('an exact materialized managed revision is required')
    document = parse_json(result.document_json)
    view = {'record_type': 'managed_record_export/v1', 'generated_view': True,
            'edit_policy': 'Update through loop-engine records and regenerate this export.',
            'generated_at': request.generated_at, 'renderer_version': RENDERER_VERSION,
            'renderer_source_digest': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_policy_digest': service.policy.digest, 'source_record': result.records[0],
            'document_digest': content_digest(document), 'document': document,
            'grants_authority': False, 'promotes_intelligence': False}
    view['view_digest'] = content_digest(view)
    body = (json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    write = FileRequest(FileOperation.WRITE, request.output_path, content=body,
        replace_existing=bool(request.expected_output_digest),
        expected_digest=request.expected_output_digest)
    runtime = RuntimeObservationServices(ledger=LoopLedger())
    approvals = EffectApprovalService(runtime)
    operations = WorkspaceOperationService(workspace, approvals=approvals, runtime=runtime)
    plan = operations.plan_file_write(write, loop_id='managed-record-export',
        reason='Export this exact selected record revision to the approved review file.')
    digest = effect_digest(plan.effect)
    summary = {'record_type': 'managed_record_export_plan/v1', 'effect_digest': digest,
               'effect': plan.effect.to_dict(), 'record_id': request.record_id,
               'record_version': request.record_version, 'document_digest': content_digest(document),
               'output_digest': hashlib.sha256(body).hexdigest(), 'bytes': len(body),
               'effects_executed': False, 'record_mutated': False}
    if not approved_effect_digest:
        return summary
    if approved_effect_digest != digest:
        raise ValueError('approved export effect does not match the selected revision and bytes')
    pending = approvals.create(plan.approval)
    approvals.resume(pending.pending, pending.resume_token,
        ApprovalDecision.approve(plan.approval.request_id, 'host.export_cli',
            reason='Host supplied the exact previously reviewed export effect digest.'))
    written = operations.file(write, approval_id=plan.approval.request_id)
    if not written.ok:
        raise ValueError('record export refused: ' + written.error_code)
    observed = operations.file(FileRequest(FileOperation.READ, request.output_path))
    if not observed.ok or observed.content != body:
        raise RuntimeError('export outcome unknown: exact readback did not match')
    return {**summary, 'record_type': 'managed_record_export_result/v1',
            'effects_executed': True, 'output_verified': True,
            'loop_events': len(runtime.ledger.events)}


def plain_path(value, *, must_exist=True):
    path = Path(value).absolute()
    if '..' in path.parts or any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError('host paths cannot cross traversal or symlinks')
    if must_exist and not path.exists():
        raise FileNotFoundError(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('policy', 'database', 'artifact-root', 'record-id', 'record-version',
                 'output-root', 'output-path', 'generated-at'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--expected-output-digest', default='')
    parser.add_argument('--approve-effect-digest', default='')
    args = parser.parse_args()
    policy = RecordOperationPolicy.from_mapping(parse_json(
        plain_path(args.policy).read_text(encoding='utf-8')))
    database, artifacts = plain_path(args.database), plain_path(args.artifact_root)
    def open_read_only(write):
        if write:
            raise PermissionError('the exporter cannot mutate records')
        return SQLiteRecordStore(str(plain_path(database)), read_only=True)
    service = RecordOperationService(policy, RecordOperationServices(RecordStorageBinding(
        'sqlite:' + str(database), str(artifacts), open_read_only)))
    workspace = RestrictedLocalWorkspace(WorkspaceSpec('managed-record-publication',
        str(plain_path(args.output_root)), max_file_bytes=policy.maximum_document_bytes + 16384))
    result = export_record(service, workspace, ExportRequest(
        args.record_id, args.record_version, args.output_path, args.generated_at,
        args.expected_output_digest), approved_effect_digest=args.approve_effect_digest)
    print(canonical_json(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
