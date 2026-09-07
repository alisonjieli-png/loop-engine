"""Read scoped repair observations from existing Run History and artifact records.

No new memory store or promotion authority is created. A selected historical
failure is advisory input; it never carries acceptance into another run.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from loop_engine.core.context_artifacts import ContextArtifactRef, ContextArtifactStore, ContextArtifactStoreSpec
from loop_engine.core.run_history import RunHistory
from loop_engine.loop.intelligence_loops import serve_historical_intelligence


@dataclass(frozen=True)
class ProbeRepairRequest:
    """Explicit permitted prior run, artifact namespace, subject scope, and record."""

    history_root: str
    run_id: str
    artifact_store: ContextArtifactStoreSpec
    scope_ref: str
    receipt_path: str
    receipt_digest: str
    maximum_bytes: int = 32 * 1024 * 1024


@dataclass(frozen=True)
class ProbeRepairEvidence:
    """Immutable selected view; references and source checks remain attached."""

    task_semantic_digest: str
    view_json: str
    source_bindings_json: str

    def validate_for(self, task):
        from generalization_probe import digest, require_file_bindings, task_semantics
        if self.task_semantic_digest != digest(task_semantics(task.manifest())):
            raise ValueError('repair evidence belongs to different task semantics')
        view = json.loads(self.view_json)
        if (view.get('record_type') != 'probe_repair_evidence/v1'
                or view.get('trust') != 'observed_historical_failure_advisory'
                or view.get('task_semantic_digest') != self.task_semantic_digest
                or view.get('acceptance_inherited') is not False
                or view.get('grants_promotion') is not False
                or view.get('current_source_verdict') != 'not_evaluated_by_this_historical_record'
                or not isinstance(view.get('failures'), list) or not 1 <= len(view['failures']) <= 8
                or len(self.view_json.encode()) > 32768):
            raise ValueError('repair context must remain bounded historical advice, without acceptance')
        for item in view['failures']:
            if (not isinstance(item, dict) or item.get('passed') is not False
                    or set(item) - {'case_id', 'passed', 'observed_digest', 'observed',
                                   'observed_summary', 'failure_note'}
                    or len(str(item.get('failure_note', '')).encode()) > 4096):
                raise ValueError('repair context contains unsupported disclosure or status')
        require_file_bindings(json.loads(self.source_bindings_json))
        return view

    @property
    def content_digest(self):
        return hashlib.sha256(self.view_json.encode()).hexdigest()


def load_repair_evidence(task, request):
    """Select one observed failure through Runtime History and Solution Intelligence."""
    from generalization_probe import canonical, digest, ordinary_file, task_semantics

    if not isinstance(request, ProbeRepairRequest) or not isinstance(request.artifact_store, ContextArtifactStoreSpec):
        raise TypeError('repair retrieval requires an explicit typed history and artifact scope')
    if type(request.maximum_bytes) is not int or request.maximum_bytes <= 0:
        raise ValueError('repair retrieval requires a positive byte budget')
    if not request.scope_ref or not request.run_id:
        raise ValueError('repair retrieval requires exact scope and run identities')
    if request.artifact_store.namespace in ('.', '..'):
        raise ValueError('repair artifact namespace cannot traverse its authorized root')
    bindings = {}
    consumed_bytes = 0

    def read(path):
        nonlocal consumed_bytes
        path = Path(path).absolute()
        if not path.is_file() or path.stat().st_size + consumed_bytes > request.maximum_bytes:
            raise ValueError('repair evidence unavailable or outside its read budget')
        path, raw, sha = ordinary_file(path)
        consumed_bytes += len(raw)
        bindings[str(path)] = sha
        return raw, sha

    def load():
        from loop_engine.core.run_history_paths import validated_run_id
        run_id = validated_run_id(request.run_id)
        history_root = Path(request.history_root).absolute()
        read(history_root / run_id / 'manifest.json')
        read(history_root / run_id / 'events.jsonl')
        history = RunHistory.load(str(history_root), run_id)
        if not history._committed:
            raise ValueError('repair history must be committed before reuse')
        objects = Path(request.artifact_store.root).absolute() / request.artifact_store.namespace / 'objects'
        if not objects.is_dir() or any(path.is_symlink() for path in (objects, *objects.parents)):
            raise ValueError('repair artifact namespace must already exist without symlinks')
        store = ContextArtifactStore(request.artifact_store)

        def artifact(reference):
            ref = ContextArtifactRef.from_dict(reference)
            raw, sha = read(objects / ref.digest[:2] / ref.digest)
            if sha != ref.digest or len(raw) != ref.byte_count or store.get(ref) != raw:
                raise ValueError('repair artifact identity mismatch')
            return json.loads(raw)

        receipt_raw, receipt_sha = read(request.receipt_path)
        record = json.loads(receipt_raw)
        if (receipt_sha != request.receipt_digest
                or record.get('record_type') != 'generalization_completion_observation/v1'
                or record.get('task_semantic_digest') != digest(task_semantics(task.manifest()))
                or record.get('comparison', {}).get('passed') is not False):
            raise ValueError('repair record is not the exact selected failure for this task')
        events = history.event_log
        selected = []
        for event in events:
            if event.detail.get('custom_kind') != 'host_verification_recorded':
                continue
            report = artifact(event.detail['artifact_ref'])
            if (report.get('report_digest') != event.detail.get('record_digest')
                    or digest({key: value for key, value in report.items() if key != 'report_digest'})
                    != report.get('report_digest')
                    or report.get('verifier_loop_id') != event.loop_id
                    or report.get('producer_loop_id') == event.loop_id):
                raise ValueError('historical host report lacks its issued verifier binding')
            if report.get('status') != 'failed':
                continue
            matching = [item for item in report.get('completion_checks', ())
                        if item.get('passed') is False
                        and item.get('observations', {}).get('receipt_ref') == str(Path(request.receipt_path).absolute())
                        and item.get('observations', {}).get('receipt_digest') == receipt_sha]
            if not matching:
                continue
            sources = [item for item in events if item.detail.get('custom_kind') == 'host_operation_recorded'
                       and item.detail.get('record_digest') == report.get('subject_digest')]
            if len(sources) != 1:
                raise ValueError('repair report has no exact original operation')
            original = artifact(sources[0].detail['artifact_ref'])
            if (original.get('scope_ref') != request.scope_ref
                    or original.get('binding_digest') != report.get('binding_digest')
                    or original.get('value', {}).get('source_digest') != record.get('source_digest')
                    or original.get('value', {}).get('kind') != 'execution_observation'):
                raise ValueError('repair observation crosses its allowed source or scope')
            selected.append((event, report, matching[0]))
        if not selected:
            raise ValueError('repair record is not linked to a committed failed host verification')
        event, report, check = selected[-1]
        failures = [{key: value for key, value in item.items() if key in (
            'case_id', 'passed', 'observed_digest', 'observed', 'observed_summary', 'failure_note')}
            for item in check['observations'].get('checks', ()) if item.get('passed') is False][:8]
        if not failures:
            raise ValueError('repair evidence contains no actual counterexample observation')
        view = {'record_type': 'probe_repair_evidence/v1',
                'trust': 'observed_historical_failure_advisory',
                'task_semantic_digest': record['task_semantic_digest'],
                'historical_source_digest': record['source_digest'],
                'policy_digest': record['policy_digest'],
                'receipt_ref': str(Path(request.receipt_path).absolute()), 'receipt_digest': receipt_sha,
                'history_ref': {'run_id': run_id, 'event_digest': event.event_digest,
                                'head_digest': events[-1].event_digest, 'report_digest': report['report_digest']},
                'failures': failures, 'acceptance_inherited': False, 'grants_promotion': False,
                'current_source_verdict': 'not_evaluated_by_this_historical_record'}
        return ProbeRepairEvidence(record['task_semantic_digest'], canonical(view), canonical(bindings))

    result = serve_historical_intelligence('Selected host counterexample evidence', load)['value']
    if not isinstance(result, ProbeRepairEvidence):
        raise ValueError('selected repair evidence could not be verified and materialized')
    result.validate_for(task)
    return result


def load_repair_bundle(task, path):
    """Load an explicit host request, never discover or follow arbitrary histories."""
    from generalization_probe import canonical, ordinary_file
    from dataclasses import replace
    path, raw, sha = ordinary_file(path)
    body = json.loads(raw)
    fields = {'record_type', 'history_root', 'run_id', 'artifact_root', 'artifact_namespace',
              'scope_ref', 'receipt_path', 'receipt_digest'}
    if (set(body) != fields or body['record_type'] != 'probe_repair_request/v1'
            or any(type(body[key]) is not str or not body[key] for key in fields)):
        raise ValueError('repair bundle must declare the exact supported request fields')
    value = load_repair_evidence(task, ProbeRepairRequest(
        history_root=body['history_root'], run_id=body['run_id'],
        artifact_store=ContextArtifactStoreSpec(body['artifact_root'], body['artifact_namespace']),
        scope_ref=body['scope_ref'], receipt_path=body['receipt_path'], receipt_digest=body['receipt_digest']))
    bindings = json.loads(value.source_bindings_json)
    bindings[str(path)] = sha
    return replace(value, source_bindings_json=canonical(bindings))
