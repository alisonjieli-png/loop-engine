"""Local exported-ticket fixture over the public HostRuntimeBinding.

The default invocation only prints a plan. This is a staged fixture pilot,
not an Overnight daemon, Jira integration, publication tool, or paired trial.
Ticket text never defines paths, commands, permissions, or verification code.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from loop_engine import SolveRequest, solve_task
from loop_engine.code_nodes.solution_model_port import ModelExecution
from loop_engine.core.capability_directory import CapabilityDirectory, CapabilityHandshake, Endpoint
from loop_engine.core.host_runtime import HostOperationBinding, HostRuntimeBinding
from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig
from loop_engine.core.workspace_backends import (
    CommandRequest, DockerResourceLimits, DockerWorkspace, DockerWorkspaceDeclaration,
    FileOperation, FileRequest, RestrictedLocalWorkspace, WorkspaceSpec,
)
from loop_engine.loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec
from loop_engine.templates.intake import TaskIntakeRequest, intake_task

BASE = Path(__file__).parent
IMAGE = 'node@sha256:4d676821dff059fd00d277ee4261ef34ea712317fed0737c03941481b5760c96'
FILES = ('clamp.mjs', 'package.json', 'test.mjs')
TICKET_FIELDS = frozenset({'record_type', 'ticket_id', 'source_kind', 'source_ref',
                           'contract_ref', 'title', 'description'})
AUDIT_CASES = (
    {'case_id': 'fractional_below', 'arguments': [-5.5, -2.25, 3.75], 'expected': -2.25, 'error': None},
    {'case_id': 'fractional_above', 'arguments': [9.25, -2.25, 3.75], 'expected': 3.75, 'error': None},
    {'case_id': 'fractional_inside', 'arguments': [0.125, -0.5, 0.5], 'expected': 0.125, 'error': None},
    {'case_id': 'tiny_inside', 'arguments': [5e-324, 0, 1e-323], 'expected': 5e-324, 'error': None},
    {'case_id': 'large_inside', 'arguments': [sys.float_info.max / 2, -sys.float_info.max, sys.float_info.max],
     'expected': sys.float_info.max / 2, 'error': None},
    {'case_id': 'equal_negative', 'arguments': [-9, -3.5, -3.5], 'expected': -3.5, 'error': None},
    {'case_id': 'boolean_value', 'arguments': [True, 0, 1], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'text_bound', 'arguments': [0.5, '0', 1], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'null_value', 'arguments': [None, 0, 1], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'array_value', 'arguments': [[], 0, 1], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'missing_argument', 'arguments': [0.5, 0], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'nan_value', 'arguments': [{'number': 'NaN'}, 0, 1], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'infinite_upper', 'arguments': [0, 0, {'number': 'Infinity'}], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'infinite_lower', 'arguments': [0, {'number': '-Infinity'}, 1], 'expected': None, 'error': 'TypeError'},
    {'case_id': 'reversed', 'arguments': [0, 1, -1], 'expected': None, 'error': 'RangeError'},
    {'case_id': 'exact_lower', 'arguments': [1.25, 1.25, 2.5], 'expected': 1.25, 'error': None},
)


class PilotError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value).encode())


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise PilotError('duplicate JSON field')
        value[key] = item
    return value


def read_json(path):
    return json.loads(read_file(path), object_pairs_hook=_unique,
                      parse_constant=lambda _value: (_ for _ in ()).throw(PilotError('nonfinite JSON')))


def ordinary_path(path):
    path = Path(path).absolute()
    if '..' in path.parts or any(item.is_symlink() for item in (path, *path.parents)):
        raise PilotError('pilot paths must not traverse or follow symlinks')
    return path


def read_file(path, *, maximum_bytes=None):
    path = ordinary_path(path)
    if not path.is_file():
        raise PilotError('required ordinary file is unavailable')
    if maximum_bytes is not None and path.stat().st_size > maximum_bytes:
        raise PilotError('source exceeds its declared byte allowance')
    raw = path.read_bytes()
    if maximum_bytes is not None and len(raw) > maximum_bytes:
        raise PilotError('source exceeds its declared byte allowance')
    return raw


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        handle.write(canonical(value) + '\n')


def load_ticket(path):
    raw = read_file(path)
    ticket = json.loads(raw, object_pairs_hook=_unique)
    if not isinstance(ticket, dict) or set(ticket) != TICKET_FIELDS:
        raise PilotError('ticket fields do not match exported_ticket/v1')
    if any(type(value) is not str or not value.strip() for value in ticket.values()):
        raise PilotError('ticket fields must be nonempty text')
    if ticket['record_type'] != 'exported_ticket/v1' or ticket['contract_ref'] != 'example.clamp_api/v1':
        raise PilotError('this fixture supports only the declared clamp API contract')
    return ticket, raw


def task_text(ticket):
    return ticket['title'] + '\n\n' + ticket['description']


@dataclass(frozen=True)
class PilotGrants:
    workspace_writes: bool = False
    sandbox_commands: bool = False
    source_disclosure: bool = False

    def __post_init__(self):
        if any(type(value) is not bool for value in asdict(self).values()):
            raise PilotError('pilot grants require literal booleans')


def host_configuration():
    return {'record_type': 'ticket_pilot_host_config/v1', 'contract_ref': 'example.clamp_api/v1',
            'editable_files': ['clamp.mjs'], 'protected_files': ['package.json', 'test.mjs'],
            'primary_argv': ['npm', 'test'], 'audit_argv': ['node', 'exported_ticket_audit.mjs'],
            'image': IMAGE, 'network': False, 'verification_workspace_read_only': True,
            'source_byte_allowance': 65536,
            'publication_capabilities': [], 'external_ticket_mutation': False,
            'audit_cases_digest': digest(AUDIT_CASES), 'primary_test_count': 3}


def plan(ticket_path, work_dir=None):
    ticket, raw = load_ticket(ticket_path)
    originals = {name: sha(read_file(BASE / 'project' / name)) for name in FILES}
    originals['exported_ticket_audit.mjs'] = sha(read_file(BASE / 'exported_ticket_audit.mjs'))
    return {'record_type': 'exported_ticket_pilot_plan/v1', 'ticket': ticket,
            'ticket_bytes_digest': sha(raw), 'task_digest': sha(task_text(ticket).encode()),
            'host_configuration': host_configuration(), 'original_file_digests': originals,
            'runner_digest': sha(read_file(__file__)),
            'requested_work_dir': str(ordinary_path(work_dir)) if work_dir else None,
            'scope': 'authored exported-ticket fixture only; no Overnight daemon or Jira integration',
            'model_calls': 0, 'files_written': 0, 'commands_run': 0}


def prepare(ticket_path, work_dir, grants, *, stage_authorized=False):
    if not isinstance(grants, PilotGrants) or stage_authorized is not True:
        raise PilotError('explicit workspace-write authority is required for staging')
    frozen = plan(ticket_path, work_dir)
    root = ordinary_path(work_dir)
    if root.exists():
        raise PilotError('a pilot work directory must be new; existing evidence is preserved')
    ticket, raw = load_ticket(ticket_path)
    if sha(raw) != frozen['ticket_bytes_digest']:
        raise PilotError('ticket changed during staging preflight')
    originals = {name: read_file(BASE / 'project' / name) for name in FILES}
    audit = read_file(BASE / 'exported_ticket_audit.mjs')
    if any(sha(body) != frozen['original_file_digests'][name] for name, body in originals.items()) \
            or sha(audit) != frozen['original_file_digests']['exported_ticket_audit.mjs']:
        raise PilotError('fixture source changed during staging preflight')
    root.mkdir(parents=True)
    for name in ('baseline', 'project', 'gate-records'):
        (root / name).mkdir()
    for name, body in originals.items():
        (root / 'baseline' / name).write_bytes(body)
        (root / 'project' / name).write_bytes(body)
    (root / 'exported_ticket_audit.mjs').write_bytes(audit)
    (root / 'ticket.json').write_bytes(raw)
    manifest = {**frozen, 'record_type': 'exported_ticket_pilot_manifest/v1',
                'grants': asdict(grants), 'work_dir': str(root), 'files_written': None}
    write_json(root / 'manifest.json', manifest)
    return root


def load_manifest(root):
    root = ordinary_path(root)
    manifest = read_json(root / 'manifest.json')
    if (manifest.get('record_type') != 'exported_ticket_pilot_manifest/v1'
            or manifest.get('work_dir') != str(root)
            or manifest.get('host_configuration') != host_configuration()
            or manifest.get('runner_digest') != sha(read_file(__file__))):
        raise PilotError('saved host configuration or implementation identity changed')
    ticket, raw = load_ticket(root / 'ticket.json')
    if sha(raw) != manifest['ticket_bytes_digest'] or ticket != manifest['ticket']:
        raise PilotError('frozen ticket identity changed')
    return manifest


def snapshot(root, manifest):
    if read_json(root / 'manifest.json') != manifest:
        raise PilotError('manifest changed after host binding')
    if sha(read_file(root / 'ticket.json')) != manifest['ticket_bytes_digest']:
        raise PilotError('ticket changed after host binding')
    for name in FILES:
        if sha(read_file(root / 'baseline' / name)) != manifest['original_file_digests'][name]:
            raise PilotError('baseline source identity changed')
    for name in ('package.json', 'test.mjs'):
        if sha(read_file(root / 'project' / name)) != manifest['original_file_digests'][name]:
            raise PilotError('protected primary gate or configuration changed')
    if sha(read_file(root / 'exported_ticket_audit.mjs')) != manifest['original_file_digests']['exported_ticket_audit.mjs']:
        raise PilotError('protected completion verifier changed')
    return digest({'manifest_digest': digest(manifest),
                   'files': {name: sha(read_file(root / 'project' / name,
                        maximum_bytes=manifest['host_configuration']['source_byte_allowance'])) for name in FILES}})


def docker_gate(workspace, argv):
    backend = DockerWorkspace(WorkspaceSpec('exported-ticket-gate', str(workspace), backend_kind='docker',
        execution_enabled=True, allowed_commands=('npm', 'node'), network_access=False),
        DockerWorkspaceDeclaration(IMAGE, workspace_read_only=True,
            limits=DockerResourceLimits(memory='256m', cpus=1, pids=64, temporary_bytes=64 * 1024 * 1024)))
    if not backend.availability().available:
        raise PilotError('the pinned Node image is unavailable; automatic downloads are disabled')
    result = backend.command(CommandRequest(tuple(argv), timeout_seconds=30, max_output_bytes=65536,
                                            execution_authorized=True))
    return {**result.to_dict(), 'backend': 'docker', 'image': IMAGE,
            'workspace_read_only': True, 'network': False}


def audit_comparison(execution):
    if not execution.get('ok') or execution.get('exit_code') != 0 or execution.get('output_truncated'):
        return False, []
    try:
        observed = json.loads(execution['stdout'], object_pairs_hook=_unique,
                              parse_constant=lambda _value: (_ for _ in ()).throw(PilotError('nonfinite observation')))
        if set(observed) != {'cases'} or len(observed['cases']) != len(AUDIT_CASES):
            raise PilotError('audit response shape changed')
        checks = []
        for expected, actual in zip(AUDIT_CASES, observed['cases']):
            passed = (isinstance(actual, dict) and set(actual) == {'case_id', 'value', 'error'}
                      and actual['case_id'] == expected['case_id'] and actual['error'] == expected['error']
                      and canonical(actual['value']) == canonical(expected['expected']))
            checks.append({'case_id': expected['case_id'], 'passed': passed, 'observed': actual})
        return all(item['passed'] for item in checks), checks
    except (ValueError, TypeError, KeyError):
        return False, []


def review_diff(root):
    before = read_file(root / 'baseline' / 'clamp.mjs')
    after = read_file(root / 'project' / 'clamp.mjs')
    return ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                        fromfile='a/clamp.mjs', tofile='b/clamp.mjs'))


def make_host(root, grants, *, runner=None):
    root = ordinary_path(root)
    manifest = load_manifest(root)
    if not isinstance(grants, PilotGrants) or asdict(grants) != manifest['grants']:
        raise PilotError('host grants differ from the staged configuration')
    if not grants.source_disclosure:
        raise PilotError('explicit ticket/source disclosure is required before model-visible binding')
    lock = threading.RLock()
    run_gate = runner or docker_gate
    execution_class = 'injected_fixture' if runner is not None else 'pinned_node_docker'
    backend = RestrictedLocalWorkspace(WorkspaceSpec('exported-ticket-source', str(root / 'project')))

    def current():
        return snapshot(root, manifest)

    def check_request(request):
        if request.state_ref != current():
            raise PilotError('host source identity changed before effect')

    def inspect(request):
        with lock:
            check_request(request)
            body = read_file(root / 'project' / 'clamp.mjs',
                             maximum_bytes=manifest['host_configuration']['source_byte_allowance'])
            return {'kind': 'source_inspection', 'path': 'clamp.mjs', 'content': body.decode(),
                    'digest': sha(body), 'ticket_digest': manifest['ticket_bytes_digest']}

    def replace_source(request):
        with lock:
            check_request(request)
            value = request.arguments
            body = value['content'].encode()
            if len(body) > manifest['host_configuration']['source_byte_allowance']:
                return {'kind': 'source_replacement', 'write_applied': False, 'path': 'clamp.mjs',
                        'error_code': 'source_byte_allowance_exceeded',
                        'digest': sha(read_file(root / 'project/clamp.mjs'))}
            result = backend.file(FileRequest(FileOperation.WRITE, 'clamp.mjs', content=body,
                replace_existing=True, expected_digest=value['expected_digest']))
            return {'kind': 'source_replacement', 'write_applied': result.ok, 'path': 'clamp.mjs',
                    'digest': result.digest, 'error_code': result.error_code}

    def execute_gate(request, kind):
        with lock:
            check_request(request)
            if request.arguments['task'] != task_text(manifest['ticket']):
                raise PilotError('verifier task differs from the frozen export')
            requested = request.arguments['result']['value']
            if requested.get('kind') != 'source_replacement' or requested.get('write_applied') is not True:
                return {'passed': True, 'task_complete': False,
                        'observations': {'kind': 'intermediate_observation'}, 'notes': 'No applied candidate edit to verify.'}
            source_digest = sha(read_file(root / 'project' / 'clamp.mjs'))
            if requested.get('digest') != source_digest:
                raise PilotError('verifier result targets another source revision')
            workspace = root / ('gate-' + kind + '-' + sha(request.invocation_id.encode())[:20])
            workspace.mkdir()
            for name in FILES:
                (workspace / name).write_bytes(read_file(root / 'project' / name))
            if kind == 'audit':
                (workspace / 'exported_ticket_audit.mjs').write_bytes(read_file(root / 'exported_ticket_audit.mjs'))
                write_json(workspace / 'audit-input.json', {'cases': [
                    {key: item[key] for key in ('case_id', 'arguments')} for item in AUDIT_CASES]})
            before = {path.name: sha(read_file(path)) for path in workspace.iterdir()}
            argv = host_configuration()['audit_argv' if kind == 'audit' else 'primary_argv']
            execution = run_gate(workspace, tuple(argv))
            after = {path.name: sha(read_file(path)) for path in workspace.iterdir()}
            if kind == 'audit':
                passed, checks = audit_comparison(execution)
            else:
                counts = {name: int(values[-1]) for name in ('tests', 'pass', 'fail', 'skipped')
                          if (values := re.findall(r'^# ' + name + r' (\d+)\s*$', execution.get('stdout', ''), re.M))}
                passed = (execution.get('ok') is True and execution.get('exit_code') == 0
                          and execution.get('output_truncated') is False
                          and counts == {'tests': 3, 'pass': 3, 'fail': 0, 'skipped': 0})
                checks = [{'case_id': 'primary_repository_tests', 'passed': passed, 'counts': counts}]
            passed = bool(passed and before == after and current() == request.state_ref)
            record = {'record_type': 'exported_ticket_gate_receipt/v1', 'kind': kind,
                'invocation_id': request.invocation_id, 'manifest_digest': digest(manifest),
                'state_ref': request.state_ref, 'source_digest': source_digest,
                'execution_class': execution_class, 'execution': execution, 'checks': checks,
                'passed': passed, 'workspace_unchanged': before == after, 'workspace_hashes': before}
            diff_reference = {}
            if kind == 'audit' and passed:
                body = review_diff(root).encode()
                path = root / ('candidate-' + request.state_ref + '.diff')
                if path.exists():
                    if read_file(path) != body:
                        raise PilotError('existing review diff differs from its source identity')
                else:
                    with path.open('xb') as handle:
                        handle.write(body)
                diff_reference = {'review_diff_ref': str(path), 'review_diff_digest': sha(body)}
                record.update(diff_reference)
            receipt_path = root / 'gate-records' / (sha(request.invocation_id.encode()) + '.json')
            write_json(receipt_path, record)
            return {'passed': passed, 'task_complete': passed,
                    'observations': {'gate': kind, 'checks': checks, 'source_digest': source_digest,
                                     'receipt_ref': str(receipt_path), 'receipt_digest': digest(record),
                                     'execution_class': execution_class, **diff_reference},
                    'notes': 'Declared gate passed.' if passed else 'Declared gate failed; inspect observations.'}

    def primary(request):
        return execute_gate(request, 'primary')

    def completion(request):
        return execute_gate(request, 'audit')

    def schema(properties=None, required=()):
        return {'type': 'object', 'properties': properties or {}, 'required': list(required), 'additionalProperties': False}

    directory = CapabilityDirectory()
    descriptions = (
        ('ticket_inspect', inspect, ('reads_fs',)), ('ticket_replace', replace_source, ('writes_fs',)),
        ('ticket_primary_gate', primary, ('reads_fs', 'writes_fs', 'spawns_process')),
        ('ticket_completion_gate', completion, ('reads_fs', 'writes_fs', 'spawns_process')))
    for surface, callback, effects in descriptions:
        directory.register(CapabilityHandshake(surface, 'static_component', 'Staged exported-ticket fixture operation.',
            ('invoke',), effects=effects, max_response_bytes=1048576), (Endpoint('invoke', callback),))

    def binding(surface, kind, permissions, inputs):
        return HostOperationBinding(surface, 'invoke', inputs, {'type': 'object'},
            lambda request: EffectSpec(kind, surface, 'ticket-pilot:' + str(root),
                (('manifest_digest', digest(manifest)), ('state', request.state_ref))),
            'exported_ticket_pilot.' + surface + '@1.0.0', permission_names=permissions)

    operations = (
        binding('ticket_inspect', EffectClass.LOCAL_READ, ('source_read',), schema()),
        binding('ticket_replace', EffectClass.LOCAL_WRITE, ('workspace_write',), schema({
            'path': {'const': 'clamp.mjs'}, 'content': {'type': 'string', 'maxLength': 65536},
            'expected_digest': {'type': 'string', 'pattern': '^[a-f0-9]{64}$',
                'description': 'Copy the current source digest returned by ticket_inspect, not the new content hash.'}},
            ('path', 'content', 'expected_digest'))))
    primary_binding = binding('ticket_primary_gate', EffectClass.COMMAND_EXECUTION, ('sandbox_command',), {'type': 'object'})
    completion_binding = binding('ticket_completion_gate', EffectClass.COMMAND_EXECUTION, ('sandbox_command',), {'type': 'object'})

    def authorize(request):
        effect = request.effect.effect_class
        permitted = (effect == EffectClass.LOCAL_READ
                     or effect == EffectClass.LOCAL_WRITE and grants.workspace_writes
                     or effect == EffectClass.COMMAND_EXECUTION and grants.sandbox_commands)
        decide = ApprovalDecision.approve if permitted else ApprovalDecision.reject
        return decide(request.request_id, 'staged_ticket_host_policy',
                      reason='Exact effect within the frozen local pilot grants.')

    return HostRuntimeBinding(directory, operations, primary_binding, authorize, current,
        'ticket-pilot:' + str(root), share_outputs_with_model=True, completion_verifiers=(completion_binding,))


def current_gate_receipts(root, manifest, state):
    references, matching = [], []
    current_source = sha(read_file(root / 'project' / 'clamp.mjs'))
    for path in sorted((root / 'gate-records').glob('*.json')):
        record = read_json(path)
        if (record.get('record_type') != 'exported_ticket_gate_receipt/v1'
                or record.get('manifest_digest') != digest(manifest)
                or record.get('kind') not in ('primary', 'audit')
                or path.stem != sha(record['invocation_id'].encode())):
            raise PilotError('gate record contract or identity changed')
        workspace = root / ('gate-' + record['kind'] + '-' + sha(record['invocation_id'].encode())[:20])
        if {item.name: sha(read_file(item)) for item in workspace.iterdir()} != record['workspace_hashes']:
            raise PilotError('retained gate subject changed')
        references.append({'path': str(path), 'file_digest': sha(read_file(path))})
        if record.get('state_ref') == state and record.get('source_digest') == current_source:
            if record.get('review_diff_ref'):
                diff_path = ordinary_path(record['review_diff_ref'])
                if diff_path.parent != root or sha(read_file(diff_path)) != record['review_diff_digest']:
                    raise PilotError('candidate review diff identity changed')
            matching.append(record)
    complete = ({item['kind'] for item in matching} == {'primary', 'audit'}
                and all(item.get('passed') is True and item.get('workspace_unchanged') is True for item in matching))
    return references, complete


def save_review(root, outcome):
    root = ordinary_path(root)
    manifest = load_manifest(root)
    state = snapshot(root, manifest)
    after = read_file(root / 'project' / 'clamp.mjs')
    diff = review_diff(root)
    with (root / 'review.diff').open('x', encoding='utf-8') as handle:
        handle.write(diff)
    records, complete = current_gate_receipts(root, manifest, state)
    evidence_classes = sorted({read_json(item['path'])['execution_class'] for item in records})
    report = {'record_type': 'exported_ticket_review/v1', 'manifest_digest': digest(manifest),
              'ticket_digest': manifest['ticket_bytes_digest'], 'state_ref': state,
              'source_digest': sha(after), 'diff_digest': sha(diff.encode()),
              'review_only': True, 'applied_to_original': False, 'publication_performed': False,
              'external_ticket_updated': False, 'scope': 'staged authored fixture; no live Overnight/Jira integration',
              'gate_receipts': records, 'outcome': outcome.to_dict(),
              'execution_evidence_classes': evidence_classes,
              'current_gates_complete': complete,
              'disposition': 'REVIEW_READY' if outcome.solved and complete else 'UNVERIFIED_REVIEW'}
    report['report_digest'] = digest(report)
    write_json(root / 'review.json', report)
    return report


def inspect_review(root):
    root = ordinary_path(root)
    manifest = load_manifest(root)
    report = read_json(root / 'review.json')
    if (report.get('report_digest') != digest({key: value for key, value in report.items() if key != 'report_digest'})
            or report.get('manifest_digest') != digest(manifest) or report.get('state_ref') != snapshot(root, manifest)
            or report.get('source_digest') != sha(read_file(root / 'project' / 'clamp.mjs'))
            or report.get('diff_digest') != sha(read_file(root / 'review.diff'))):
        raise PilotError('review no longer binds the current source or diff')
    for item in report['gate_receipts']:
        path = ordinary_path(item['path'])
        if path.parent != root / 'gate-records' or sha(read_file(path)) != item['file_digest']:
            raise PilotError('review gate record identity changed')
    references, complete = current_gate_receipts(root, manifest, report['state_ref'])
    if references != report['gate_receipts'] or complete is not report['current_gates_complete']:
        raise PilotError('review gate set changed after report creation')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticket', default=str(BASE / 'exported-ticket.fixture.json'))
    parser.add_argument('--work-dir')
    parser.add_argument('--inspect-report')
    parser.add_argument('--authorize-model-calls', action='store_true')
    parser.add_argument('--allow-source-to-model', action='store_true')
    parser.add_argument('--allow-workspace-writes', action='store_true')
    parser.add_argument('--allow-sandbox-commands', action='store_true')
    parser.add_argument('--model-route', default='cloud.default')
    parser.add_argument('--model-id', default='deepseek-v4-flash:0731')
    args = parser.parse_args(argv)
    if args.inspect_report:
        if args.authorize_model_calls or args.work_dir:
            parser.error('Report inspection cannot also start a run.')
        print(canonical(inspect_review(args.inspect_report)))
        return 0
    if not args.authorize_model_calls:
        print(canonical(plan(args.ticket, args.work_dir)))
        return 0
    if not (args.work_dir and args.allow_source_to_model and args.allow_workspace_writes and args.allow_sandbox_commands):
        parser.error('A live pilot requires a new work dir plus explicit disclosure, write, and command grants.')
    grants = PilotGrants(True, True, True)
    root = prepare(args.ticket, args.work_dir, grants, stage_authorized=args.allow_workspace_writes)
    host = make_host(root, grants)
    gateway = ModelGateway()
    route = gateway.registry.get(args.model_route)
    if route.model != args.model_id:
        parser.error('Configured route must match the exact requested model.')
    model = ModelExecution(gateway, ModelGatewayConfig(route_names=(args.model_route,),
                                                      allowed_models=(args.model_id,), allow_failover=False))
    ticket = load_manifest(root)['ticket']
    outcome = solve_task(SolveRequest(intake_task(TaskIntakeRequest(text=task_text(ticket))),
        host_runtime=host, model_execution=model, runs_dir=str(root / 'runs'), interaction_mode='autonomous',
        quiet_model_io=True, allow_workspace_writes=False, allow_sandbox_commands=False,
        allow_network_reads=False, allow_source_materialization_to_model=False))
    print(canonical(save_review(root, outcome)))
    return 0 if outcome.solved else 1


if __name__ == '__main__':
    raise SystemExit(main())
