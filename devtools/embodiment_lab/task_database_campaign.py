"""Persistent real task-database trials through the existing public solver.

The whole catalog is frozen before dispatch. Readiness exclusions, transport
outages, applied settings, failures, and saved Run History remain distinct.
The experiment projection is not an execution history or acceptance authority.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sys
import time
from urllib.parse import urlsplit

from loop_engine import SolveRequest, solve_task
from loop_engine.code_nodes.solve_terminal import SolveTerminalCode
from loop_engine.code_nodes.solution_model_port import ModelExecution, ModelExecutionSession
from loop_engine.core.configuration_capabilities import (
    ConfigurationFact, ConfigurationSettingSpec, ConfigurationTargetSpec, describe_configuration)
from loop_engine.core.configuration_setters import (
    ConfigurationSetterContext, ConfigurationSettingChange, ConfigurationUpdateRequest,
    ConfigurationValueCandidate, ConfigurationWriteAuthority, apply_configuration_as_loop)
from loop_engine.core.context_artifacts import (
    ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
from loop_engine.core.external_harness import HarnessRegistry
from loop_engine.core.harness_configuration import load_harness_binding
from loop_engine.core.harness_fallback import HarnessFallbackPolicy, HarnessFailureKind
from loop_engine.core.harness_semantic import HarnessSemanticBinding
from loop_engine.core.model_capabilities import ModelOutputAllocation
from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig
from loop_engine.core.parameter_resolution import ParameterDefinition, ParameterInput, ParameterSourceKind
from loop_engine.core.provider_failure_classes import (
    CONFIGURATION, CONTRACT, FAIL_CELL, STOP_ROUTE, UNCLASSIFIED, WAIT_FOR_ALLOWANCE, WAIT_FOR_RECOVERY,
    decide, failure_class)
from loop_engine.core.run_history import load_saved_run_bundle
from loop_engine.core.settings_loader import load_runtime_settings
from loop_engine.generation.space import ConfigurationAxis, ConfigurationSpace
from loop_engine.templates.intake import TaskIntake

from .systematic_records import CampaignProjection, canonical, digest
from .systematic_runtime import NativeGatewayAdapter, configure_environment


# The trial's own lifecycle states, named once.
TRIAL_STARTING, TRIAL_FINISHED, TRIAL_FAILED = 'starting', 'finished', 'failed'


def file_digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def confined_name(value):
    if (type(value) is not str or not value or value in ('.', '..')
            or '/' in value or '\\' in value or any(ord(c) < 32 for c in value)):
        raise ValueError('task and occurrence identities must be single safe path components')
    return value


def fair_order(tasks):
    """Round-robin families, with explicit-checklist tasks first within each."""
    groups = defaultdict(list)
    for task in tasks:
        groups[task['job_family']].append(task)
    groups = {key: deque(sorted(rows, key=lambda row: (not row.get('has_acceptance_criteria'), row['id'])))
              for key, rows in groups.items()}
    output = []
    while any(groups.values()):
        for family in sorted(groups):
            if groups[family]:
                output.append(groups[family].popleft())
    return output


def campaign_space(harnesses):
    def axis(name, values):
        return ConfigurationAxis(name, 'categorical', tuple(canonical(value) for value in values))
    return ConfigurationSpace('task-database-executable-grid', '1.0.0', (
        axis('harness', harnesses), axis('temperature', (0.0, 0.7)),
        axis('output_allocation_tokens', (16384, 65536)),
        axis('context_delivery', ('bounded_inline', 'selected_references')),
        axis('harness_fallback', ('none', 'registered_alternatives'))),
        canonical({'mode': 'non_deterministic', 'provider': 'tactical',
            'model': 'gemma-4-coding-abliterated', 'route': 'custom.tactical',
            'provider_failover': False, 'max_model_calls': None, 'max_passes': None}))


def prepare(root, task_root, provider_file, repository):
    os.umask(0o077)
    root, task_root, repository = Path(root).resolve(), Path(task_root).resolve(), Path(repository).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / 'campaign.json').exists():
        raise ValueError('this campaign is already frozen')
    catalog_path = task_root / 'catalog.json'
    catalog = json.loads(catalog_path.read_text())
    if len({row['id'] for row in catalog['tasks']}) != len(catalog['tasks']):
        raise ValueError('the frozen catalog contains duplicate task identities')
    harness_files = sorted((repository / 'embodiments').glob('*/harness.json'))
    harnesses = ['native_gateway'] + [json.loads(path.read_text())['harness_id'] for path in harness_files]
    space = campaign_space(harnesses)
    records = CampaignProjection(root / 'campaign.duckdb')
    rows = []
    try:
        for item in fair_order(catalog['tasks']):
            confined_name(item['id'])
            directory = (task_root / item['path']).resolve(strict=True)
            if not directory.is_relative_to(task_root):
                raise ValueError('task directory leaves the admitted database')
            descriptor, brief = directory / 'task.json', directory / 'task.md'
            row = {**item, 'task_directory': str(directory),
                'descriptor_digest': file_digest(descriptor), 'brief_digest': file_digest(brief),
                'admission': 'queued_for_execution_and_evaluation' if item['status'] == 'ready'
                             else 'requires_source_admission',
                'evaluator_qualification': 'task_specific_campaign_qualification_pending'}
            rows.append(row)
            records.record('task_population', item['id'], row)
        manifest = {'record_type': 'task_database_campaign/v1', 'campaign_id': root.name,
            'task_root': str(task_root), 'catalog_digest': file_digest(catalog_path),
            'task_count': len(rows), 'ready_source_count': sum(r['status'] == 'ready' for r in rows),
            'job_families': sorted({r['job_family'] for r in rows}),
            'population_digest': digest(rows), 'selection_rule': 'family_round_robin_then_declared_criteria_then_identity',
            'provider_file': str(Path(provider_file).resolve()), 'provider_file_digest': file_digest(provider_file),
            'repository': str(repository), 'harnesses': harnesses,
            'harness_file_digests': {str(path): file_digest(path) for path in harness_files},
            'configuration_space': space.to_dict(), 'configuration_space_digest': space.digest,
            'raw_configurations_per_task': space.cardinality,
            'raw_task_configuration_cells': len(rows) * space.cardinality,
            'valid_task_configuration_cells': None,
            'search_policy': 'diagonal_exact_enumeration_with_per_task_coverage',
            'optimizer_policy': 'exact_grid_initial_campaign_other_search_methods_separately_qualified',
            'external_business_effects_authorized': False, 'provider_failover': False,
            'source_readiness_is_evaluator_qualification': False,
            'task_acceptance_requires_independent_campaign_review': True,
            'status': 'prepared', 'created_at': datetime.now(timezone.utc).isoformat()}
        records.record('campaign', 'manifest', manifest)
        records.export_object(root / 'campaign.json', manifest)
        records.export_object(root / 'task-population.json', {'tasks': rows})
        records.record('controller', 'cursor', {'round': 0, 'task_position': 0, 'completed_trials': 0})
        records.refresh_export(root / 'status.json', {'status': 'prepared', 'task_count': len(rows),
            'ready_source_count': manifest['ready_source_count'], 'raw_configurations_per_task': space.cardinality})
        return manifest
    finally:
        records.close()


def task_intake(row, delivery):
    directory = Path(row['task_directory'])
    if (file_digest(directory / 'task.json') != row['descriptor_digest']
            or file_digest(directory / 'task.md') != row['brief_digest']):
        raise ValueError('frozen task instructions changed')
    descriptor = json.loads((directory / 'task.json').read_text())
    attachments, references, sources = [], [], {}
    for relative in descriptor.get('attachments', ()):
        candidate = directory / relative
        path = candidate.resolve(strict=True)
        if not path.is_relative_to(directory):
            raise ValueError('an attachment escapes its admitted task directory')
        sources[str(path)] = file_digest(path)
        if delivery == 'bounded_inline' and path.stat().st_size <= 65536:
            try:
                attachments.append({'name': relative, 'text': path.read_text(encoding='utf-8')})
                continue
            except UnicodeError:
                pass
        references.append(str(path))
    data_path = descriptor.get('data_path')
    if data_path:
        path = (directory / data_path).resolve(strict=True)
        database = Path(row['task_directory']).parents[3]
        if not path.is_relative_to(database):
            raise ValueError('dataset link escapes the admitted task database')
        references.append(str(path))
    prompt = ('Perform this task and produce its actual deliverables. Preserve all original requirements. '
        'This run authorizes local sandbox work and provider reasoning, not real business-system mutations, '
        'messages, submissions, purchases, or deployment. Use simulated services where the task needs effect tests. '
        'Ask a precise material question when required information is absent.\n\n'
        + (directory / 'task.md').read_text() + '\n\n'
        + canonical({'provided_attachments': attachments, 'available_source_references': references}))
    return TaskIntake('task_pack', prompt, tuple(references)), sources


class RecordedSettingSession:
    """Record each applied setting while retaining one existing budget owner."""

    def __init__(self, authority, artifacts, configuration, records, *, checkpoint_retention=2):
        self._session = ModelExecutionSession(replace(authority, session_factory=None), artifact_store=artifacts)
        self.configuration, self.records = configuration, records
        if type(checkpoint_retention) is not int or checkpoint_retention < 1:
            raise ValueError('checkpoint retention must keep at least the latest revision')
        # The ledger is append-only, so every earlier checkpoint is a prefix of
        # the latest one; keeping all of them grows the cell quadratically.
        self.checkpoint_retention = checkpoint_retention

    def __getattr__(self, name):
        return getattr(self._session, name)

    def invoke(self, request, parent_loop):
        source = digest('ModelInvocationRequest.temperature:explicit-campaign-setting@1.0.0')
        def fact(state):
            return ConfigurationFact(state, 'campaign-temperature-binding@1.0.0', source)
        setting = ConfigurationSettingSpec.from_parameter(ParameterDefinition('temperature', 'temperature',
            'Explicit temperature treatment for this real campaign', 'number', 'campaign@1.0.0', 'invocation',
            constraints={'minimum': 0, 'maximum': 2}), 'temperature', support=fact('supported'),
            availability=fact('available'), qualification=ConfigurationFact(), writable=True,
            phases=('per_request',), run_modes=('non_deterministic', 'hybrid'))
        target = ConfigurationTargetSpec('campaign-model-request@1.0.0', (setting,),
                                         'campaign-temperature-binding@1.0.0', source)
        now = datetime.now(timezone.utc)
        before = describe_configuration(target, request, at=now)
        update = ConfigurationUpdateRequest(before['target_digest'], before['values_digest'],
            (ConfigurationSettingChange('temperature', (ConfigurationValueCandidate(
                ParameterInput.from_value(self.configuration['temperature'])),)),), 'per_request', 'non_deterministic')
        authority = ConfigurationWriteAuthority(target.target_ref, ('temperature',),
            ParameterSourceKind.EXPLICIT_INVOCATION, 'campaign-treatment@1.0.0', '1.0.0', allow_unqualified=True)
        result, run = apply_configuration_as_loop(update,
            ConfigurationSetterContext(target, request, authority, now), parent=parent_loop)
        operation = request.semantic_call_id or parent_loop.loop_id
        self.records.record('applied_configuration', operation, {'setting_report': result.report,
            'setting_loop_id': run['loop_id'], 'semantic_call_id': request.semantic_call_id,
            'owner_loop_id': parent_loop.loop_id, 'configuration': self.configuration,
            'input_digest': request.exact_input_digest})
        if result.report['status'] not in ('applied_in_memory', 'unchanged'):
            raise ValueError('requested experiment setting was refused')
        try:
            return self._session.invoke(result.configuration, parent_loop)
        finally:
            # Persist a current checkpoint after every completed or failed
            # semantic invocation, not just at the task's terminal state.
            from loop_engine.core.run_history import RunHistory
            history = RunHistory.from_ledger(parent_loop.ledger.events,
                run_id='checkpoint-' + digest(operation)[:24])
            history.commit()
            root = Path(self.records.path).parent / 'step-history' / digest(operation)[:24]
            revisions = sorted((int(p.name) for p in root.iterdir() if p.name.isdigit()), reverse=True) \
                if root.exists() else []
            revision = (revisions[0] + 1) if revisions else 0
            location = history.save(str(root / str(revision)))
            for stale in revisions[self.checkpoint_retention - 1:]:
                shutil.rmtree(root / str(stale), ignore_errors=True)
            self.records.record('step_history', operation, {'history': location,
                'integrity': history.verify_chain(), 'known_calls': self.calls_used,
                'call_accounting_complete': not self.accounting_uncertain,
                'revision': revision, 'retained_revisions': self.checkpoint_retention,
                'events': len(parent_loop.ledger.events)})


@dataclass(frozen=True)
class CampaignTrialServices:
    """Optional exact gateway; route and model authority still come from the trial."""

    gateway: ModelGateway | None = None

    def __post_init__(self):
        if self.gateway is not None and not isinstance(self.gateway, ModelGateway):
            raise TypeError('campaign gateway must use the existing typed boundary')


def run_trial(root, row, configuration, manifest, ordinal, *, services=CampaignTrialServices()):
    root = Path(root)
    confined_name(row['id'])
    confined_name(str(ordinal))
    cell = root / 'trials' / (row['id'] + '-' + digest(row['task_directory'])[:8]) / str(ordinal)
    if cell.exists():
        # An interrupted occurrence keeps its evidence; the worker reconciles
        # it and advances the attempt number instead of writing over it.
        return {'record_type': 'task_database_trial/v1', 'task_id': row['id'], 'configuration': configuration,
                'status': TRIAL_FAILED, 'error_type': 'FileExistsError',
                'error_message': 'trial cell already exists; reconcile the interrupted occurrence',
                'task_accepted': False, 'model_calls': None, 'path': str(cell)}
    cell.mkdir(parents=True, exist_ok=False)
    records = CampaignProjection(cell / 'projection.duckdb')
    state = {'record_type': 'task_database_trial/v1', 'task_id': row['id'], 'configuration': configuration,
             'status': TRIAL_STARTING, 'task_accepted': False, 'model_calls': None}
    records.record('trial', 'state', state)
    records.refresh_export(cell / 'status.json', state)
    started = time.monotonic()
    try:
        intake, source_digests = task_intake(row, configuration['context_delivery'])
        records.record('task_sources', 'selected', {'source_digests': source_digests,
                       'input_digest': intake.content_digest, 'source_refs': list(intake.source_refs)})
        artifacts = ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(
            ContextArtifactStoreSpec(str(cell / 'artifacts')))))
        if not isinstance(services, CampaignTrialServices):
            raise TypeError('trial services must be typed')
        gateway = services.gateway or load_runtime_settings(manifest['provider_file']).settings.build_gateway()
        provider = gateway.providers[configuration['provider']]
        names = ([configuration['harness']] if configuration['harness_fallback'] == 'none' else
                 [configuration['harness']] + [n for n in manifest['harnesses'] if n != configuration['harness']])
        adapters = []
        for name in names:
            if name == 'native_gateway':
                adapters.append(NativeGatewayAdapter())
            else:
                path = str(Path(manifest['repository']) / 'embodiments' / name / 'harness.json')
                if file_digest(path) != manifest['harness_file_digests'][path]:
                    raise ValueError('harness configuration changed after freeze')
                bound = load_harness_binding(path, work_root=str(cell / 'processes'),
                    socket_directory=str(Path(manifest['repository']) / '.loop-engine-dev/hs'),
                    artifact_store=artifacts, expected_id=name)
                adapters.append(bound.registry.get(name))
        policy = HarnessFallbackPolicy(tuple(names), tuple(HarnessFailureKind) if len(names) > 1 else ())
        binding = HarnessSemanticBinding(names[0], HarnessRegistry(tuple(adapters)), str(cell / 'processes'),
            artifact_store=artifacts, fallback_policy=policy,
            socket_directory=str(Path(manifest['repository']) / '.loop-engine-dev/hs'))
        capability = provider.output_capability_for(configuration['model'])
        allocation = ModelOutputAllocation(capability=capability, provider_id=configuration['provider'],
            model_id=configuration['model'], route_name=configuration['route'],
            requested_tokens=configuration['output_allocation_tokens'],
            decision_ref='campaign-configuration:' + digest(configuration),
            reason='Explicit experimental response allocation; total task calls and passes remain uncapped.')
        authority = ModelExecution(gateway, ModelGatewayConfig(route_names=(configuration['route'],),
            allowed_models=(configuration['model'],), allow_failover=False,
            max_route_attempts=None, timeout_seconds=1200, max_total_tokens=None, output_allocation=allocation),
            max_model_calls=None, harness=binding,
            session_factory=lambda authority: RecordedSettingSession(authority, artifacts, configuration, records))
        def progress(event):
            safe = {key: event.get(key) for key in ('event_type', 'step', 'model_calls_completed',
                    'elapsed_seconds', 'diagnostic_code', 'failure_code')}
            records.record('progress', 'latest', safe)
            records.refresh_export(cell / 'status.json', {**state, 'status': 'running', 'latest_progress': safe})
            print(canonical({'task': row['id'], **safe}), flush=True)
        outcome = solve_task(SolveRequest(intake, model_execution=authority, runs_dir=str(cell / 'runs'),
            interaction_mode='autonomous', practitioner_mode='non_deterministic', max_passes=None,
            allow_network_reads=False, allow_workspace_writes=True, allow_sandbox_commands=True,
            workspace_root=str(cell / 'workspace'), allow_source_materialization_to_model=True,
            allow_local_execution=False, quiet_model_io=True, progress=progress))
        value = outcome.to_dict()
        records.record('outcome', 'terminal', value)
        records.export_object(cell / 'outcome.json', value)
        integrity = load_saved_run_bundle(str(cell / 'runs'), value['run_id']).history.verify_chain()
        state.update(status=TRIAL_FINISHED, engine_terminal=value['terminal_code'], engine_solved=value['solved'],
            failure_code=value.get('failure_code', ''),
            model_calls=value['model_calls'], model_call_accounting_complete=value['model_call_accounting_complete'],
            model_calls_known_subtotal=value['model_calls_known_subtotal'], history_integrity=integrity,
            delivered_artifacts=len(value['artifacts']),
            campaign_acceptance='independent_task_specific_review_required')
    except Exception as exc:
        state.update(status=TRIAL_FAILED, error_type=type(exc).__name__,
                     error_message=str(exc)[:300], model_call_accounting_complete=False)
    finally:
        state['elapsed_seconds'] = time.monotonic() - started
        records.record('trial', 'state', state)
        records.refresh_export(cell / 'status.json', state)
        records.close()
    return {**state, 'path': str(cell)}


def listed_model_names(body):
    """The names a listing carries, from either the OpenAI or the Ollama shape."""
    rows = body.get('data') or body.get('models') or [] if isinstance(body, dict) else []
    return {str(row.get('id') or row.get('name') or '') for row in rows if isinstance(row, dict)} - {''}


def model_is_listed(names, model):
    """Exact identity, or the same identity with the implicit latest tag."""
    return model in names or model + ':latest' in names or (model.endswith(':latest') and model[:-7] in names)


def endpoint_reachable(url):
    """Transport-only observation: no credentials, model, or success claim."""
    parsed = urlsplit(url)
    port = parsed.port or (80 if parsed.scheme == 'http' else 443)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=10):
            return {'reachable': True, 'kind': 'tcp_connection_only', 'provider_verified': False}
    except OSError as exc:
        return {'reachable': False, 'kind': 'tcp_connection_only', 'error_type': type(exc).__name__,
                'errno': exc.errno, 'provider_verified': False}


def provider_available(endpoint):
    """Observe the configured model listing without generating a response."""
    from urllib.error import HTTPError, URLError
    from urllib.request import Request
    from loop_engine.core.custom_endpoint import _endpoint_opener, _request_headers
    from loop_engine.core.model_gateway import _error_code
    transport = endpoint_reachable(endpoint.base_url)
    if not transport['reachable']:
        return transport
    # The same listing path the product adapter reads for this wire.
    listing = endpoint.base_url.rstrip('/') + ('/api/tags' if getattr(endpoint, 'wire', 'openai') == 'ollama'
                                              else '/models')
    try:
        with _endpoint_opener(endpoint).open(Request(listing, headers=_request_headers(endpoint)),
                                             timeout=30) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                return {'reachable': False, 'kind': 'model_listing', 'reason': 'listing_exceeds_probe_contract'}
            names = listed_model_names(json.loads(raw))
            present = model_is_listed(names, endpoint.model)
            # An empty listing is a provider still coming up (an outage); a
            # listing that names other models but not this one is a
            # configuration fault the worker must not wait on.
            code = '' if present else ('model_not_found' if names else 'provider_unavailable')
            return {'reachable': present, 'kind': 'model_listing', 'model_listed': present,
                    'listed_count': len(names), 'listing_url': listing, 'failure_code': code,
                    'failure_class': failure_class(code) if code else '',
                    'provider_verified': False, 'model_calls': 0}
    except HTTPError as exc:
        # An HTTP refusal is classified by the gateway's own rule so a wrong
        # credential or a missing route stops the worker instead of reading
        # as an outage that never ends.
        code = _error_code(f'HTTP Error {exc.code}: {exc.reason}')
        return {'reachable': False, 'kind': 'model_listing', 'http_status': exc.code,
                'failure_code': code, 'failure_class': failure_class(code), 'listing_url': listing,
                'model_calls': 0}
    except (URLError, OSError, ValueError, TypeError, AttributeError) as exc:
        return {'reachable': False, 'kind': 'model_listing', 'error_type': type(exc).__name__, 'model_calls': 0}


def outage_decision(result, attempts_so_far, attempt_ceiling):
    """The worker's one decision after a trial the engine ended as provider
    unavailable, from the failure code the run reported. A configuration or
    contract fault stops the route; an allowance waits for its reset; an
    outage waits for recovery; both waits are bounded by the ceiling, after
    which the cell fails and the campaign advances. A code the vocabulary
    does not know is read as an outage, the conservative reading under this
    terminal, still bounded. Any other terminal needs no decision."""
    if result.get('engine_terminal') != SolveTerminalCode.PROVIDER_UNAVAILABLE.value:
        return None
    code = result.get('failure_code') or ''
    codes = [code] if failure_class(code) != UNCLASSIFIED else ['provider_unavailable']
    return decide(codes, attempts_so_far=attempts_so_far, attempt_ceiling=attempt_ceiling)


def reconcile_interrupted(records, cursor):
    """Record an interrupted trial as interrupted, keep its evidence where it
    is, and move the attempt number on so the next occurrence never writes
    over it. Returns the reconciled row, or None when nothing was active."""
    active = records.latest('controller', 'active_trial')
    if not active:
        return None
    occurrence = str(cursor['round']) + '-attempt-' + str(cursor.get('trial_attempt', 0))
    row = {**active, 'status': 'interrupted', 'occurrence': occurrence,
           'reconciled_at': datetime.now(timezone.utc).isoformat()}
    records.record('trial_projection', str(active.get('task_id')) + ':' + occurrence, row)
    cursor['trial_attempt'] = cursor.get('trial_attempt', 0) + 1
    cursor['interrupted_trials'] = cursor.get('interrupted_trials', 0) + 1
    records.record('controller', 'active_trial', {})
    records.record('controller', 'cursor', cursor)
    return row


def _terminate(signum, frame):
    # A termination signal must unwind through every finally block so the
    # trial's records close and the active-trial marker stays for
    # reconciliation, instead of the default handler ending the process.
    raise SystemExit(128 + signum)


def worker(root, *, probe_interval=60, wait_attempt_ceiling=3, refuse_interrupted=False):
    if type(probe_interval) is not int or probe_interval < 1:
        raise ValueError('probe interval must be positive')
    if type(wait_attempt_ceiling) is not int or wait_attempt_ceiling < 1:
        raise ValueError('wait attempt ceiling must be positive')
    signal.signal(signal.SIGTERM, _terminate)
    root = Path(root).resolve()
    os.umask(0o077)
    with (root / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        records = CampaignProjection(root / 'campaign.duckdb')
        try:
            manifest = records.latest('campaign', 'manifest')
            rows = json.loads((root / 'task-population.json').read_text())['tasks']
            if digest(rows) != manifest['population_digest'] or file_digest(manifest['provider_file']) != manifest['provider_file_digest']:
                raise ValueError('frozen campaign inputs changed')
            space = campaign_space(manifest['harnesses'])
            if space.digest != manifest['configuration_space_digest']:
                raise ValueError('configuration space changed')
            cursor = records.latest('controller', 'cursor')
            if refuse_interrupted and records.latest('controller', 'active_trial'):
                raise ValueError('an interrupted trial requires explicit reconciliation before resume')
            reconciled = reconcile_interrupted(records, cursor)
            if reconciled:
                print(canonical({'status': 'reconciled_interrupted_trial', **reconciled}), flush=True)
            configure_environment()
            os.environ['LOOP_ENGINE_SANDBOX_IMAGE'] = 'loop-engine-ds1000-runtime@sha256:d29a0fedd17671510b759b15f276b73ee9ba813868653d8923c7365482ee328d'
            endpoint = load_runtime_settings(manifest['provider_file']).settings.build_gateway().providers['tactical'].adapter.endpoint
            import loop_engine
            package = Path(loop_engine.__file__).resolve().parent
            records.record('controller', 'runtime_identity', {'package_root': str(package),
                'python_sources': {str(path.relative_to(package)): file_digest(path) for path in package.rglob('*.py')},
                'controller_file': str(Path(__file__).resolve()), 'controller_digest': file_digest(__file__),
                'worker_pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()})
            while cursor['round'] < space.cardinality:
                row = rows[cursor['task_position']]
                base = {'worker_pid': os.getpid(), 'task_count': len(rows), 'cursor': cursor,
                        'updated_at': datetime.now(timezone.utc).isoformat()}
                if row['admission'] != 'queued_for_execution_and_evaluation':
                    result = {'status': 'requires_source_admission', 'task_id': row['id'], 'attempted': False}
                else:
                    probe = provider_available(endpoint)
                    records.record('provider_availability', 'latest', probe)
                    if failure_class(probe.get('failure_code', '')) in (CONFIGURATION, CONTRACT):
                        cursor['stopped_routes'] = cursor.get('stopped_routes', 0) + 1
                        records.record('controller', 'cursor', cursor)
                        state = {**base, 'cursor': cursor, 'status': 'route_stopped', 'provider_observation': probe}
                        records.refresh_export(root / 'status.json', state)
                        print(canonical(state), flush=True)
                        return
                    if not probe['reachable']:
                        state = {**base, 'status': 'waiting_for_provider', 'provider_observation': probe,
                                 'next_probe_seconds': probe_interval, 'next_task': row['id']}
                        records.record('controller_status', 'latest', state)
                        records.refresh_export(root / 'status.json', state)
                        print(canonical(state), flush=True)
                        time.sleep(probe_interval)
                        continue
                    # Diagonal ordering varies configurations across the first
                    # population pass; every task still visits every address.
                    index = (cursor['round'] + cursor['task_position']) % space.cardinality
                    active = {**base, 'status': 'running', 'task_id': row['id'], 'configuration_index': index}
                    records.record('controller', 'active_trial', active)
                    records.refresh_export(root / 'status.json', active)
                    occurrence = str(cursor['round']) + '-attempt-' + str(cursor.get('trial_attempt', 0))
                    result = run_trial(root, row, space.configuration_at(index), manifest, occurrence)
                    records.record('controller', 'active_trial', {})
                    decision = outage_decision(result, cursor.get('trial_attempt', 0), wait_attempt_ceiling)
                    if decision is not None:
                        result = {**result, 'decision': decision}
                        records.record('trial_projection', row['id'] + ':' + occurrence, result)
                        if decision['decision'] in (WAIT_FOR_RECOVERY, WAIT_FOR_ALLOWANCE):
                            cursor['trial_attempt'] = cursor.get('trial_attempt', 0) + 1
                            cursor['outage_attempts'] = cursor.get('outage_attempts', 0) + 1
                            records.record('controller', 'cursor', cursor)
                            records.refresh_export(root / 'status.json', {**base, 'cursor': cursor,
                                'status': 'waiting_for_provider', 'latest_trial': result,
                                'next_probe_seconds': probe_interval})
                            time.sleep(probe_interval)
                            continue
                        if decision['decision'] == STOP_ROUTE:
                            # A wrong credential, a missing model, or a broken
                            # contract cannot pass on retry; the worker stops
                            # with a distinct status rather than spending calls.
                            cursor['stopped_routes'] = cursor.get('stopped_routes', 0) + 1
                            records.record('controller', 'cursor', cursor)
                            records.refresh_export(root / 'status.json', {**base, 'cursor': cursor,
                                'status': 'route_stopped', 'latest_trial': result})
                            print(canonical({'status': 'route_stopped', 'task': row['id'], 'decision': decision}), flush=True)
                            return
                        result['status'] = 'failed_after_bounded_wait'
                    if result.get('status') == TRIAL_FINISHED:
                        cursor['completed_trials'] += 1
                    else:
                        cursor['failed_cells'] = cursor.get('failed_cells', 0) + 1
                records.record('trial_projection', row['id'] + ':' + str(cursor['round']), result)
                cursor['trial_attempt'] = 0
                cursor['task_position'] += 1
                if cursor['task_position'] == len(rows):
                    cursor['task_position'] = 0
                    cursor['round'] += 1
                records.record('controller', 'cursor', cursor)
                records.refresh_export(root / 'status.json', {**base, 'cursor': cursor, 'status': 'advancing', 'latest_trial': result})
            records.refresh_export(root / 'status.json', {'status': 'declared_grid_traversal_finished', 'cursor': cursor,
                'task_acceptance': 'independent_review_required', 'all_possible_product_configurations_tested': False})
        finally:
            records.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('prepare', 'worker', 'reconcile'))
    parser.add_argument('--root', required=True)
    parser.add_argument('--task-root', default='/home/username/task_database')
    parser.add_argument('--provider-file')
    parser.add_argument('--repository', default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument('--probe-interval', type=int, default=60)
    parser.add_argument('--wait-attempt-ceiling', type=int, default=3,
                        help='bounded waits per cell after a provider-unavailable trial')
    parser.add_argument('--refuse-interrupted', action='store_true',
                        help='refuse to start over an interrupted trial instead of reconciling it')
    parser.add_argument('--wait-for-launch-signal', action='store_true')
    args = parser.parse_args()
    if args.operation == 'prepare':
        if not args.provider_file:
            parser.error('prepare requires an explicit provider file')
        print(canonical(prepare(args.root, args.task_root, args.provider_file, args.repository)), flush=True)
    elif args.operation == 'reconcile':
        records = CampaignProjection(Path(args.root).resolve() / 'campaign.duckdb')
        try:
            cursor = records.latest('controller', 'cursor')
            print(canonical(reconcile_interrupted(records, cursor) or {'status': 'nothing_to_reconcile'}), flush=True)
        finally:
            records.close()
    else:
        if args.wait_for_launch_signal and sys.stdin.readline().strip() != 'start':
            raise ValueError('detached worker did not receive its launch signal')
        worker(args.root, probe_interval=args.probe_interval, wait_attempt_ceiling=args.wait_attempt_ceiling,
               refuse_interrupted=args.refuse_interrupted)


if __name__ == '__main__':
    main()
