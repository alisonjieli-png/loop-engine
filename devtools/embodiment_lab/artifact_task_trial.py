"""A configurable compact Practitioner experiment for full task deliverables.

The same composition accepts any admitted task pack. It uses the existing
model authority, harness binding, project executor, and Run History. Generated
tests establish mechanical checks, not independent task acceptance.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time

from loop_engine.code_nodes.solution_model_port import ModelExecution, ModelInvocationRequest
from loop_engine.core.context_artifacts import (
    ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
from loop_engine.core.adaptive_practitioner_source import _open_source
from loop_engine.core.generated_project import (
    GENERATED_PROJECT_RECORD_TYPE, GeneratedProjectManifest, GeneratedProjectAuthority,
    GeneratedProjectExecutionContext, GeneratedProjectExecutionRequest,
    GeneratedProjectInputArtifact, execute_generated_project)
from loop_engine.core.harness_configuration import load_harness_binding
from loop_engine.core.model_capabilities import ModelOutputAllocation
from loop_engine.core.model_gateway import ModelGatewayConfig
from loop_engine.core.model_response_admission import ModelResponseAdmissionRequest, admit_model_response_as_loop
from loop_engine.core.run_history import RunHistory
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.strings.prompt_fragments import (
    ARTIFACT_TRIAL_ASSIGNMENT_PROMPT, ARTIFACT_TRIAL_CONTRACT_NOTES_PROMPT,
    ARTIFACT_TRIAL_FEEDBACK_POLICY_PROMPT, ARTIFACT_TRIAL_PROMPT_RESOURCE)
from loop_engine.loop.loop_role import LoopRole, LoopRoleIdentity

from .campaign_sources import TaskSourceSnapshot, verify_task_sources
from .systematic_records import CampaignProjection, canonical, digest
from .task_database_campaign import RecordedSettingSession, engine_identity, task_intake


class ArtifactTrialUnavailable(ValueError):
    """This composition cannot honor a declared input or configuration."""

    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class TrialFeedback:
    source_snapshot_digest: str
    subject_digest: str
    evaluation_ref: str
    evaluation_digest: str
    summary: str

    def __post_init__(self):
        for value in (self.source_snapshot_digest, self.subject_digest, self.evaluation_digest):
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('trial feedback needs exact source and evidence identities')
        if not self.evaluation_ref or not self.summary:
            raise ValueError('trial feedback requires its source and scoped observation')


@dataclass(frozen=True)
class ArtifactTrialRequest:
    root: str
    task: dict
    configuration: dict
    repository: str
    sandbox_image: str
    feedback: tuple[TrialFeedback, ...] = ()

    def __post_init__(self):
        if type(self.task) is not dict or type(self.configuration) is not dict:
            raise TypeError('task and configuration must be explicit records')
        for value in (self.root, self.repository, self.sandbox_image):
            if not isinstance(value, str) or not value:
                raise ValueError('artifact trial needs exact workspace, repository and image')
        if not isinstance(self.feedback, tuple) or any(not isinstance(item, TrialFeedback) for item in self.feedback):
            raise TypeError('artifact trial feedback must be a tuple of typed observations')


def _read_input(path):
    with os.fdopen(_open_source(Path(path).absolute()), 'rb') as stream:
        return stream.read()


def _validate_feedback(feedback, expected):
    for item in feedback:
        if not isinstance(item, TrialFeedback) or item.source_snapshot_digest != expected.content_digest:
            raise ValueError('feedback belongs to a different task source snapshot')
        if hashlib.sha256(_read_input(item.evaluation_ref)).hexdigest() != item.evaluation_digest:
            raise ValueError('feedback evidence changed or does not match its identity')


def _inputs_for_composition(task):
    directory = Path(task['task_directory']).absolute()
    declaration = json.loads(_read_input(directory / 'task.json'))
    if declaration.get('data_path'):
        # Dataset materialization belongs to the full Practitioner source
        # resolver. This narrower experimental composition cannot omit it.
        raise ArtifactTrialUnavailable('dataset_materializer_not_bound')
    inputs = []
    for name in declaration.get('attachments', ()):
        path = directory / name
        if not path.resolve(strict=True).is_relative_to(directory.resolve()):
            raise ValueError('source input escapes task directory')
        if not path.is_file():
            raise ArtifactTrialUnavailable('directory_materializer_not_bound')
        inputs.append(GeneratedProjectInputArtifact('inputs/' + name, _read_input(path)))
    return tuple(inputs)


# The harness level that binds no external harness: the trial calls the
# configured route through the model gateway directly.
NATIVE_GATEWAY_HARNESS = 'native_gateway'


def _compose_prompt(task_input, shape, inputs, feedback):
    """Keep task deliverable formats separate from the outer response format.

    The instruction texts are the governed prompt resource named by
    ``ARTIFACT_TRIAL_PROMPT_RESOURCE``; the trial state records that identity.
    """
    return canonical({
        'assignment': ARTIFACT_TRIAL_ASSIGNMENT_PROMPT,
        'original_task': task_input,
        'response_contract': shape,
        'contract_notes': ARTIFACT_TRIAL_CONTRACT_NOTES_PROMPT,
        'provided_inputs': [value.to_dict() for value in inputs],
        'prior_trial_feedback': feedback,
        'feedback_policy': ARTIFACT_TRIAL_FEEDBACK_POLICY_PROMPT})


def run_artifact_trial(request: ArtifactTrialRequest, gateway):
    """Compose a project, execute it in the declared sandbox, and save evidence."""
    if not isinstance(request, ArtifactTrialRequest):
        raise TypeError('artifact trial request must be typed')
    root = Path(request.root)
    root.mkdir(parents=True, exist_ok=False)
    records = CampaignProjection(root / 'projection.duckdb')
    try:
        return _run_artifact_trial(request, gateway, records)
    finally:
        records.close()


def _run_artifact_trial(request, gateway, records):
    root = Path(request.root)
    artifacts = ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(
        ContextArtifactStoreSpec(str(root / 'artifacts')))))
    configuration = json.loads(canonical(request.configuration))
    session, expected, intake = None, None, None
    owner = Loop('produce task deliverables through a compact configured composition',
        LoopConfig(framework='custom', custom_steps=('compose', 'execute'),
                   allowable_modes=('non_deterministic', 'deterministic'),
                   preferred_modes=('non_deterministic', 'deterministic'),
                   exit_condition='steps_complete', max_model_calls=None),
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, 'practitioner.solver'))
    state = {'record_type': 'artifact_task_trial/v1', 'task_id': request.task['id'],
             'configuration': configuration, 'composition': ['compose', 'execute'],
             'task_accepted': False, 'independent_evaluation_qualified': False,
             'composition_qualified': False, 'full_system_benchmark': False,
             'harness_composition': 'direct_model_gateway' if configuration.get('harness') == NATIVE_GATEWAY_HARNESS else 'external_harness_binding',
             'prompt_resource': {'resource_id': ARTIFACT_TRIAL_PROMPT_RESOURCE[0],
                                 'version': ARTIFACT_TRIAL_PROMPT_RESOURCE[1]},
             'sandbox_image': request.sandbox_image,
             'status': 'starting', 'model_calls': None}
    inputs = ()
    started = time.monotonic()
    candidate = None

    def publish(status):
        state.update(status=status, known_model_calls=session.calls_used if session else 0,
                     elapsed_seconds=round(time.monotonic() - started, 3))
        records.record('trial', 'state', state)
        records.refresh_export(root / 'status.json', state)
        print(canonical({k: state[k] for k in ('task_id', 'status', 'known_model_calls', 'elapsed_seconds')}), flush=True)

    def handle(active, step, context):
        nonlocal candidate
        if step == 'compose':
            publish('composing_real_task_deliverables')
            shape = {'record_type': GENERATED_PROJECT_RECORD_TYPE, 'project_id': 'task-deliverables',
                'summary': 'Describe the proposed deliverables.',
                'files': [{'path': 'run.py', 'content': 'Complete source code goes here.'}],
                'commands': [{'argv': ['python3', 'run.py'], 'purpose': 'Produce and test the deliverables.',
                    'timeout_seconds': 300, 'command_kind': 'execute', 'network_access': False,
                    'expected_exit_codes': [0]}],
                'expected_artifacts': [{'path': 'output/report.md', 'media_type': 'text/markdown',
                                        'minimum_bytes': 1, 'constraint': ''}]}
            prompt = _compose_prompt(intake.original_input, shape, inputs, state['feedback'])
            raw = session.invoke(ModelInvocationRequest(prompt,
                system='Produce an executable candidate for the original task under the supplied typed project contract.',
                semantic_call_id='compose:' + active.loop_id), active)
            response_ref = artifacts.capture(raw, artifact_kind='candidate_project_response').raw
            records.record('candidate', 'response', {'artifact_ref': response_ref.to_dict()})
            admission = admit_model_response_as_loop(ModelResponseAdmissionRequest(
                raw, GENERATED_PROJECT_RECORD_TYPE, digest(shape)), parent=active)
            if not admission.admitted:
                raise ValueError('project response was not admitted: ' + admission.failure_code)
            candidate = GeneratedProjectManifest.from_mapping(admission.value)
            reference = artifacts.capture(canonical(candidate.to_dict()), artifact_kind='candidate_project').raw
            records.record('candidate', 'project', {'manifest_digest': candidate.digest, 'artifact_ref': reference.to_dict()})
            publish('candidate_composed')
            return StepOutcome('candidate project composed', mode='non_deterministic', model_calls=0)
        publish('executing_in_declared_sandbox')
        execution = execute_generated_project(GeneratedProjectExecutionRequest(candidate,
            str(root / 'workspace'), GeneratedProjectAuthority(actor_id=active.loop_id,
                allow_workspace_writes=True, allow_sandbox_commands=True,
                allow_network_reads=False, allow_local_execution=False),
            image=request.sandbox_image, input_artifacts=tuple(inputs)), GeneratedProjectExecutionContext(active))
        records.record('execution', 'project', execution)
        records.export_object(root / 'execution.json', execution)
        state['execution_succeeded'] = execution.get('deterministic_checks_passed', False)
        state['execution_workspace'] = execution.get('workspace')
        state['delivered_artifacts'] = execution.get('artifacts', [])
        publish('candidate_execution_recorded')
        return StepOutcome('candidate execution recorded; independent task evaluation still required',
                           mode='deterministic')

    try:
        publish('validating_composition_eligibility')
        supported = {'provider', 'route', 'model', 'harness', 'temperature', 'output_allocation_tokens',
                     'context_delivery', 'harness_fallback', 'provider_failover', 'mode',
                     'max_model_calls', 'max_passes'}
        if set(configuration) - supported:
            raise ArtifactTrialUnavailable('configuration_dimension_not_supported')
        if (configuration.get('harness_fallback', 'none') != 'none'
                or configuration.get('provider_failover', False) is not False
                or configuration.get('mode', 'non_deterministic') != 'non_deterministic'
                or configuration.get('max_passes') is not None):
            raise ArtifactTrialUnavailable('configuration_policy_not_supported')
        expected = TaskSourceSnapshot.from_dict(request.task['source_snapshot'])
        verify_task_sources(request.task['task_directory'], request.task['task_root'], expected)
        state['source_snapshot_digest'] = expected.content_digest
        records.record('source_verification', 'before', {'state': 'verified',
                       'source_snapshot_digest': expected.content_digest})
        _validate_feedback(request.feedback, expected)
        state['feedback'] = [dict(item.__dict__) for item in request.feedback]
        inputs = _inputs_for_composition(request.task)
        intake, _ = task_intake(request.task, configuration['context_delivery'])
        records.record('source', 'runtime', {
            'engine': engine_identity(Path(__file__).resolve().parents[2]),
            'composition_source_digest': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'sandbox_image': request.sandbox_image})
        capability = gateway.providers[configuration['provider']].output_capability_for(configuration['model'])
        allocation = ModelOutputAllocation(capability=capability, provider_id=configuration['provider'],
            model_id=configuration['model'], route_name=configuration['route'],
            requested_tokens=configuration['output_allocation_tokens'],
            decision_ref='artifact-trial:' + digest(configuration),
            reason='Declared grid output allowance for this experiment.')
        harness = None
        if configuration['harness'] != NATIVE_GATEWAY_HARNESS:
            harness = load_harness_binding(str(Path(request.repository) / 'embodiments' /
                configuration['harness'] / 'harness.json'), work_root=str(root / 'processes'),
                socket_directory=str(Path(request.repository) / '.loop-engine-dev/hs'),
                artifact_store=artifacts, expected_id=configuration['harness'], allow_unavailable=True)
        authority = ModelExecution(gateway, ModelGatewayConfig(route_names=(configuration['route'],),
            allowed_models=(configuration['model'],), allow_failover=False, output_allocation=allocation,
            max_route_attempts=None, timeout_seconds=1200),
            max_model_calls=configuration.get('max_model_calls'), harness=harness)
        session = RecordedSettingSession(authority, artifacts, configuration, records)
        owner.run(handler=handle)
        state['model_calls'] = None if session.accounting_uncertain else session.calls_used
        publish('finished_candidate_not_independently_accepted')
    except Exception as exc:
        diagnostic = artifacts.capture(canonical({'error_type': type(exc).__name__, 'detail': str(exc)}),
                                       artifact_kind='private_trial_diagnostic').raw
        state.update(error_type=type(exc).__name__, model_calls=(
            None if session and session.accounting_uncertain else session.calls_used if session else 0))
        state['diagnostic_ref'] = diagnostic.to_dict()
        state['ineligibility_reason'] = exc.reason_code if isinstance(exc, ArtifactTrialUnavailable) else None
        publish('ineligible_configuration' if isinstance(exc, ArtifactTrialUnavailable) else 'failed')
    finally:
        if expected is not None:
            try:
                verify_task_sources(request.task['task_directory'], request.task['task_root'], expected)
                records.record('source_verification', 'after', {'state': 'verified',
                    'source_snapshot_digest': expected.content_digest})
            except Exception as exc:
                records.record('source_verification', 'after', {'state': 'failed',
                    'source_snapshot_digest': expected.content_digest, 'error_type': type(exc).__name__})
                state.update(status='failed', source_verification_failed=True)
        state['model_usage'] = [{key: value for key, value in result.to_dict().items() if key != 'text'}
                                for result in session.results] if session else []
        history = RunHistory.from_ledger(owner.ledger.events, run_id='artifact-trial-' + digest(str(root))[:20])
        history.commit()
        state['history'] = history.save(str(root / 'runs'))
        state['history_integrity'] = history.verify_chain()
        records.record('trial', 'state', state)
        records.refresh_export(root / 'status.json', state)
    return state
