"""Embed Loop Engine over a populated, host-owned JavaScript project.

Only --authorize-model-calls performs a solve. The host's immutable gate uses
Node in a pinned Docker image. This example has no Git publication capability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from loop_engine import SolveRequest, solve_task
from loop_engine.code_nodes.solution_model_port import ModelExecution
from loop_engine.core.capability_directory import CapabilityDirectory, CapabilityHandshake, Endpoint
from loop_engine.core.host_runtime import HostOperationBinding, HostRuntimeBinding
from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig
from loop_engine.core.workspace_backends import (
    CommandRequest, DockerResourceLimits, DockerWorkspace, DockerWorkspaceDeclaration,
    FileOperation, FileRequest, WorkspaceSpec,
)
from loop_engine.loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec
from loop_engine.templates.intake import TaskIntakeRequest, intake_task


IMAGE = 'node@sha256:4d676821dff059fd00d277ee4261ef34ea712317fed0737c03941481b5760c96'
TASK = (
    'Repair the existing clamp.mjs implementation without changing its public API. '
    'clamp(value, minimum, maximum) must return the value when inside inclusive bounds, '
    'the nearest boundary outside them, and the boundary when both bounds are equal. '
    'Preserve TypeError for nonfinite numbers and RangeError for reversed bounds. '
    'Use the host inspection and replacement capabilities; the host owns the tests '
    'and verification environment. Return the repaired repository state when verified.')


def schema(properties=None, required=()):
    return {'type': 'object', 'properties': properties or {},
            'required': list(required), 'additionalProperties': False}


def make_host(project: Path):
    """Trusted adapter code; its file scope and gates are not model parameters."""
    project = project.resolve()
    gate_paths = ('test.mjs', 'package.json')
    gate_hashes = {name: hashlib.sha256((project / name).read_bytes()).hexdigest()
                   for name in gate_paths}
    files = ('clamp.mjs', *gate_paths)

    def snapshot():
        return hashlib.sha256(json.dumps({name: hashlib.sha256(
            (project / name).read_bytes()).hexdigest() for name in files},
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    declaration = DockerWorkspaceDeclaration(
        IMAGE, workspace_read_only=True,
        limits=DockerResourceLimits(memory='256m', cpus=1.0, pids=64,
                                    temporary_bytes=64 * 1024 * 1024))
    backend = DockerWorkspace(WorkspaceSpec(
        'host-javascript-project', str(project), backend_kind='docker',
        execution_enabled=True, allowed_commands=('npm',), network_access=False), declaration)
    if not backend.availability().available:
        raise RuntimeError('The pinned Node Docker image must be installed before this example.')

    def inspect(request):
        if request.state_ref != snapshot():
            raise ValueError('host state changed before inspection')
        raw = backend.file(FileRequest(FileOperation.READ, 'clamp.mjs'))
        if not raw.ok:
            raise ValueError(raw.error_code)
        return {'ok': True, 'path': 'clamp.mjs', 'content': raw.content.decode(),
                'digest': raw.digest}

    def replace(request):
        if request.state_ref != snapshot():
            raise ValueError('host state changed before replacement')
        value = request.arguments
        result = backend.file(FileRequest(
            FileOperation.WRITE, value['path'], content=value['content'].encode(),
            replace_existing=True, expected_digest=value['expected_digest']))
        return {'ok': result.ok, 'path': value['path'], 'digest': result.digest,
                'error_code': result.error_code}

    def verify(request):
        if request.state_ref != snapshot():
            raise ValueError('host verification snapshot changed')
        if any(hashlib.sha256((project / name).read_bytes()).hexdigest() != digest
               for name, digest in gate_hashes.items()):
            return {'passed': False, 'task_complete': False,
                    'observations': {'error': 'host gate files changed'},
                    'notes': 'The fixed host verification contract was altered.'}
        result = backend.command(CommandRequest(
            ('npm', 'test'), timeout_seconds=30, execution_authorized=True))
        counts = {name: int(values[-1]) for name in ('tests', 'pass', 'fail', 'skipped')
                  if (values := re.findall(r'^# ' + name + r' (\d+)\s*$',
                                           result.stdout, flags=re.MULTILINE))}
        passed = (result.ok and result.exit_code == 0 and not result.output_truncated
                  and counts == {'tests': 3, 'pass': 3, 'fail': 0, 'skipped': 0})
        return {'passed': passed, 'task_complete': passed,
                'observations': {'gate': ['npm', 'test'], 'exit_code': result.exit_code,
                                 'stdout': result.stdout, 'stderr': result.stderr,
                                 'gate_hashes': gate_hashes, 'test_counts': counts, 'image': IMAGE,
                                 'workspace_read_only': True, 'network': False},
                'notes': 'Host-owned Node tests passed.' if passed else
                         'Host-owned Node tests failed; use their observations to repair the source.'}

    def effect(kind, operation):
        def build(request):
            return EffectSpec(kind, operation, 'host-project:' + str(project),
                              (('snapshot', request.state_ref),))
        return build

    directory = CapabilityDirectory()
    registrations = (
        ('project_inspection', 'invoke', inspect,
         'Read the editable JavaScript source and its exact current digest.', ('reads_fs',)),
        ('project_replacement', 'invoke', replace,
         'Replace the editable source using its expected digest; protected tests cannot be edited.',
         ('writes_fs',)),
        ('project_verifier', 'validate', verify,
         'Run immutable host-owned repository tests in the declared Node sandbox.',
         ('reads_fs', 'spawns_process')),
    )
    for surface, operation, callback, purpose, effects in registrations:
        directory.register(CapabilityHandshake(
            surface, 'static_component', purpose, (operation,), effects=effects,
            input_schema='host_arguments/v1', output_schema='host_observation/v1',
            max_response_bytes=1024 * 1024), [Endpoint(operation, callback)])
    output = {'type': 'object'}
    inspect_binding = HostOperationBinding(
        'project_inspection', 'invoke', schema(), output,
        effect(EffectClass.LOCAL_READ, 'inspect_source'), 'example.inspect@1.0.0',
        permission_names=('source_read',))
    replace_binding = HostOperationBinding(
        'project_replacement', 'invoke', schema({
            'path': {'const': 'clamp.mjs'}, 'content': {'type': 'string'},
            'expected_digest': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}},
            ('path', 'content', 'expected_digest')), output,
        effect(EffectClass.LOCAL_WRITE, 'replace_source'), 'example.replace@1.0.0',
        permission_names=('workspace_write',))
    verifier = HostOperationBinding(
        'project_verifier', 'validate', {'type': 'object'}, output,
        effect(EffectClass.COMMAND_EXECUTION, 'verify_repository'), 'example.host_gates@1.0.0',
        permission_names=('sandbox_command',))

    def authorize(request):
        return ApprovalDecision.approve(request.request_id, 'example_host_policy',
                                        reason='Exact invocation inside the predeclared example project.')

    return HostRuntimeBinding(directory, (inspect_binding, replace_binding), verifier,
                              authorize, snapshot, 'example-javascript-project',
                              share_outputs_with_model=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--authorize-model-calls', action='store_true')
    parser.add_argument('--allow-source-to-model', action='store_true')
    parser.add_argument('--model-route', default='cloud.default')
    parser.add_argument('--model-id', default='deepseek-v4-flash:0731')
    args = parser.parse_args()
    if not args.authorize_model_calls:
        parser.error('Use --authorize-model-calls to grant the example a live model session.')
    if not args.allow_source_to_model:
        parser.error('Use --allow-source-to-model to share the fixture source and test observations.')
    root = Path(args.work_dir).resolve()
    if root.exists():
        parser.error('--work-dir must not already exist; previous evidence is never overwritten.')
    root.mkdir(parents=True)
    project = root / 'project'
    shutil.copytree(Path(__file__).parent / 'project', project)
    host = make_host(project)
    model = ModelExecution(ModelGateway(), ModelGatewayConfig(
        route_names=(args.model_route,), allowed_models=(args.model_id,),
        allow_failover=False))

    def progress(value):
        if value.get('event_type') in ('model.step.started', 'model.step.completed',
                                     'practitioner.diagnostic'):
            print(json.dumps({key: value.get(key) for key in (
                'event_type', 'run_id', 'step', 'model_calls_completed',
                'elapsed_seconds', 'diagnostic_code')}), flush=True)

    outcome = solve_task(SolveRequest(
        intake_task(TaskIntakeRequest(text=TASK)), model_execution=model,
        host_runtime=host, runs_dir=str(root / 'runs'), interaction_mode='autonomous',
        quiet_model_io=True, progress=progress))
    print(json.dumps(outcome.to_dict(), indent=2))
    return 0 if outcome.solved else 1


if __name__ == '__main__':
    raise SystemExit(main())
