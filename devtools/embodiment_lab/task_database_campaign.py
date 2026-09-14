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
from loop_engine.core.model_routes import ModelRoute
from loop_engine.core.parameter_resolution import ParameterDefinition, ParameterInput, ParameterSourceKind
from loop_engine.core.provider_failure_classes import (
    ALLOWANCE, CONFIGURATION, CONTRACT, FAIL_CELL, OUTAGE, STOP_ROUTE, UNCLASSIFIED, WAIT_FOR_ALLOWANCE, WAIT_FOR_RECOVERY,
    decide, failure_class)
from loop_engine.core.run_history import load_saved_run_bundle
from loop_engine.core.settings_loader import load_runtime_settings
from loop_engine.generation.space import ConfigurationAxis, ConfigurationSpace
from loop_engine.templates.intake import TaskIntake
from loop_engine.strings.prompt_fragments import TASK_DATABASE_TRIAL_INSTRUCTION_PROMPT

from .systematic_records import CampaignProjection, canonical, digest
from .systematic_runtime import NativeGatewayAdapter, configure_environment
from .campaign_activation import CampaignAccessPolicy, activation_due, probe_gateway, utc_time
from .campaign_sources import (
    TaskSourceAvailability, TaskSourceSnapshot,
    snapshot_available_task_sources,
    verify_available_task_sources, verify_task_sources,
)


# The trial's own lifecycle states, named once.
TRIAL_STARTING, TRIAL_FINISHED, TRIAL_FAILED = 'starting', 'finished', 'failed'
EXECUTION_AND_EVALUATION = 'queued_for_execution_and_evaluation'
BEST_AVAILABLE_RESOLUTION = 'queued_for_best_available_resolution'


def file_digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def optional_file_digest(path):
    path = Path(path)
    return file_digest(path) if path.is_file() else None


def engine_identity(repository):
    """The digests of every Python source in the installed package and of
    every executable a harness manifest launches (the files its
    command_prefix names that exist on this host), folded into one digest,
    so a campaign can refuse to continue on a changed engine. Vendored
    runtime trees are not walked: the launched executable is what the
    manifest binds, and the manifest itself is digested separately."""
    import loop_engine
    package = Path(loop_engine.__file__).resolve().parent
    sources = {str(path.relative_to(package)): file_digest(path) for path in sorted(package.rglob('*.py'))}
    entry_points = {}
    for manifest_path in sorted((Path(repository) / 'embodiments').glob('*/harness.json')):
        for element in json.loads(manifest_path.read_text()).get('command_prefix', ()):
            candidate = Path(str(element))
            if candidate.is_absolute() and candidate.is_file():
                entry_points[str(candidate)] = file_digest(candidate)
    return {'package_root': str(package), 'python_sources': sources, 'harness_entry_points': entry_points,
            'engine_digest': digest({'python_sources': sources, 'harness_entry_points': entry_points})}


def engine_check(frozen_digest, current_digest, allow_engine_change):
    """What a worker does with the engine it finds against the engine the
    campaign was prepared on: continue on a match, record an unfrozen
    prepare, continue on an explicitly allowed change, or refuse."""
    if frozen_digest is None:
        return 'engine_identity_not_frozen_at_prepare', False
    if frozen_digest == current_digest:
        return 'engine_identity_matches_prepare', False
    if allow_engine_change:
        return 'engine_identity_changed_and_explicitly_allowed', False
    return 'engine_identity_changed', True


def public_population_rows(rows):
    """The part of the frozen population a published index can reproduce:
    identities, relative paths, and the instruction digests, never absolute
    directories of this machine."""
    return [{key: row[key] for key in ('id', 'path', 'job_family', 'status', 'admission',
                                        'descriptor_digest', 'brief_digest', 'source_snapshot_digest',
                                        'source_availability_digest',
                                        'source_freeze_state',
                                        'instruction_source_state') if key in row}
            for row in rows]


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


def _work_limit(value):
    if value is not None and (type(value) is not int or value < 1):
        raise ValueError('a declared work limit must be a positive integer or None')
    return value


def _parse_work_limit(value):
    try:
        return _work_limit(None if value == 'unbounded' else int(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def campaign_space(harnesses, *, route=None, model_call_limits=(None,), pass_limits=(None,)):
    route = route or ModelRoute('custom.tactical', 'tactical', 'gemma-4-coding-abliterated', 'cloud')
    if not isinstance(route, ModelRoute):
        raise TypeError('a campaign route must use the existing ModelRoute contract')
    def axis(name, values):
        return ConfigurationAxis(name, 'categorical', tuple(canonical(value) for value in values))
    axes = [
        axis('harness', harnesses), axis('temperature', (0.0, 0.7)),
        axis('output_allocation_tokens', (16384, 65536)),
        axis('context_delivery', ('bounded_inline', 'selected_references')),
        axis('harness_fallback', ('none', 'registered_alternatives'))]
    fixed = {'mode': 'non_deterministic', 'provider': route.provider,
            'model': route.model, 'route': route.name,
            'provider_failover': False, 'max_model_calls': None, 'max_passes': None}
    for name, values in (('max_model_calls', model_call_limits), ('max_passes', pass_limits)):
        if not isinstance(values, tuple) or not values:
            raise ValueError('work-limit levels must be a nonempty explicit tuple')
        values = tuple(_work_limit(value) for value in values)
        if values != (None,):
            axes.append(axis(name, values))
            del fixed[name]
    return ConfigurationSpace('task-database-executable-grid', '1.0.0', tuple(axes), canonical(fixed))


def prepare(root, task_root, provider_file, repository, *, route_name='', not_before='',
            access_policy=CampaignAccessPolicy(), model_call_limits=(None,), pass_limits=(None,)):
    os.umask(0o077)
    root, task_root, repository = Path(root).resolve(), Path(task_root).resolve(), Path(repository).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / 'campaign.json').exists():
        raise ValueError('this campaign is already frozen')
    if not isinstance(access_policy, CampaignAccessPolicy):
        raise TypeError('campaign access policy must be typed')
    catalog_path = task_root / 'catalog.json'
    catalog = json.loads(catalog_path.read_text())
    if len({row['id'] for row in catalog['tasks']}) != len(catalog['tasks']):
        raise ValueError('the frozen catalog contains duplicate task identities')
    harness_files = sorted((repository / 'embodiments').glob('*/harness.json'))
    harnesses = ['native_gateway'] + [json.loads(path.read_text())['harness_id'] for path in harness_files]
    settings = load_runtime_settings(str(provider_file)).settings
    gateway = settings.build_gateway()
    if not route_name:
        custom = [provider.route_name for provider in settings.models.providers if provider.kind == 'custom']
        if len(custom) != 1:
            raise ValueError('prepare requires an explicit route name when no single custom route is declared')
        route_name = custom[0]
    route = gateway.registry.get(route_name)
    if route.provider not in gateway.providers:
        raise ValueError('the selected route has no configured provider')
    if not_before:
        not_before = utc_time(not_before).isoformat()
    space = campaign_space(harnesses, route=route, model_call_limits=model_call_limits,
                           pass_limits=pass_limits)
    records = CampaignProjection(root / 'campaign.duckdb')
    rows = []
    source_cache = {}
    try:
        for item in fair_order(catalog['tasks']):
            confined_name(item['id'])
            directory = (task_root / item['path']).resolve(strict=False)
            if not directory.is_relative_to(task_root):
                raise ValueError('task directory leaves the admitted database')
            descriptor, brief = directory / 'task.json', directory / 'task.md'
            row = {**item, 'task_directory': str(directory), 'task_root': str(task_root),
                'descriptor_digest': optional_file_digest(descriptor),
                'brief_digest': optional_file_digest(brief),
                'instruction_source_state': (
                    'complete' if descriptor.is_file() and brief.is_file()
                    else 'partial' if descriptor.is_file() or brief.is_file()
                    else 'missing'),
                'admission': (EXECUTION_AND_EVALUATION
                              if item['status'] == 'ready'
                              else BEST_AVAILABLE_RESOLUTION),
                'evaluator_qualification': 'task_specific_campaign_qualification_pending'}
            if row['instruction_source_state'] != 'complete':
                row['admission'] = BEST_AVAILABLE_RESOLUTION
            row['source_freeze_state'] = 'not_admitted'
            try:
                availability = snapshot_available_task_sources(
                    directory, task_root, cache=source_cache)
                snapshot = availability.available
                if row['admission'] == EXECUTION_AND_EVALUATION \
                        and not availability.complete:
                    row['admission'] = BEST_AVAILABLE_RESOLUTION
                row.update(
                    source_snapshot=snapshot.to_dict(),
                    source_snapshot_digest=snapshot.content_digest,
                    source_availability=availability.to_dict(),
                    source_availability_digest=availability.content_digest,
                    source_freeze_state=(
                        'frozen' if availability.complete
                        else 'available_sources_frozen_with_missing_items'))
            except (OSError, ValueError, TypeError) as exc:
                row.update(
                    admission=BEST_AVAILABLE_RESOLUTION,
                    source_freeze_state='unavailable',
                    source_freeze_error=type(exc).__name__)
            rows.append(row)
            records.record('task_population', item['id'], row)
        identity = engine_identity(repository)
        manifest = {'record_type': 'task_database_campaign/v1', 'campaign_id': root.name,
            'task_root': str(task_root), 'catalog_digest': file_digest(catalog_path),
            'task_count': len(rows), 'ready_source_count': sum(r['status'] == 'ready' for r in rows),
            'job_families': sorted({r['job_family'] for r in rows}),
            'population_digest': digest(rows), 'public_population_digest': digest(public_population_rows(rows)),
            'engine_digest': identity['engine_digest'],
            'selection_rule': 'family_round_robin_then_declared_criteria_then_identity',
            'provider_file': str(Path(provider_file).resolve()), 'provider_file_digest': file_digest(provider_file),
            'selected_route_name': route.name, 'not_before_utc': not_before,
            'readiness_method': 'gateway_generation_probe',
            'access_probe_policy': access_policy.to_dict(),
            'source_freeze_policy': 'declared_input_contents/v1',
            'source_frozen_count': sum(
                row['admission'] == EXECUTION_AND_EVALUATION
                and row['source_freeze_state'] == 'frozen' for row in rows),
            'best_available_resolution_count': sum(
                row['admission'] == BEST_AVAILABLE_RESOLUTION for row in rows),
            'available_source_snapshot_count': sum(
                bool(row.get('source_snapshot')) for row in rows),
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
        records.record('controller', 'engine_identity_at_prepare', identity)
        records.export_object(root / 'campaign.json', manifest)
        records.export_object(root / 'task-population.json', {'tasks': rows})
        records.export_object(root / 'population-index.json', {'record_type': 'task_population_index/v1',
            'public_population_digest': manifest['public_population_digest'],
            'tasks': public_population_rows(rows)})
        records.record('controller', 'cursor', {'round': 0, 'task_position': 0, 'completed_trials': 0})
        records.refresh_export(root / 'status.json', {'status': 'prepared', 'task_count': len(rows),
            'ready_source_count': manifest['ready_source_count'], 'raw_configurations_per_task': space.cardinality})
        return manifest
    finally:
        records.close()


def task_intake(row, delivery):
    directory = Path(row['task_directory'])
    descriptor_path, brief_path = directory / 'task.json', directory / 'task.md'
    if (optional_file_digest(descriptor_path) != row.get('descriptor_digest')
            or optional_file_digest(brief_path) != row.get('brief_digest')):
        raise ValueError('frozen task instructions changed')
    descriptor = (
        json.loads(descriptor_path.read_text()) if descriptor_path.is_file()
        else {
            'attachments': list(row.get('attachments') or ()),
            'data_path': row.get('data_path'),
        })
    instruction_gaps = []
    if not descriptor_path.is_file():
        instruction_gaps.append('The task descriptor file is missing.')
    if not brief_path.is_file():
        instruction_gaps.append('The task brief file is missing.')
    availability = None
    if row.get('source_availability') is not None:
        availability = TaskSourceAvailability.from_dict(
            row['source_availability'])
        verify_available_task_sources(
            directory, row['task_root'], availability)
    elif row.get('source_snapshot') is not None:
        verify_task_sources(
            directory, row['task_root'],
            TaskSourceSnapshot.from_dict(row['source_snapshot']))
    missing_paths = {
        path for path, _reason in (availability.missing if availability else ())}
    missing_items = [{"path": path, "reason": reason}
                     for path, reason in (
                         availability.missing if availability else ())]
    attachments, references, sources = [], [], {}

    def admitted_path(relative, *, boundary):
        supplied = Path(str(relative))
        if supplied.is_absolute():
            raise ValueError('declared task source path is not confined')
        candidate = directory / supplied
        unresolved = candidate.resolve(strict=False)
        if not unresolved.is_relative_to(boundary):
            raise ValueError('declared task source escapes its admitted boundary')
        relative_path = unresolved.relative_to(
            Path(row['task_root']).resolve()).as_posix()
        if not candidate.exists():
            if (relative_path in missing_paths
                    or row.get('admission') == BEST_AVAILABLE_RESOLUTION):
                if relative_path not in missing_paths:
                    missing_paths.add(relative_path)
                    missing_items.append({
                        'path': relative_path, 'reason': 'not_found'})
                return None
        path = candidate.resolve(strict=True)
        if not path.is_relative_to(boundary):
            raise ValueError('declared task source escapes its admitted boundary')
        return path

    for relative in descriptor.get('attachments', ()):
        path = admitted_path(relative, boundary=directory)
        if path is None:
            continue
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
        database = Path(row['task_root']) if row.get('task_root') else Path(row['task_directory']).parents[3]
        path = admitted_path(data_path, boundary=database.resolve())
        if path is not None:
            references.append(str(path))
    semantic_gaps = []
    if row.get('status') == 'awaiting_data':
        semantic_gaps.append(
            'The task data is not available as an admitted task source.')
    if row.get('status') == 'needs_metadata':
        semantic_gaps.append(
            'Task metadata or acceptance criteria remain incomplete.')
    semantic_gaps.extend(instruction_gaps)
    source_condition = {
        'admission': row.get('admission'),
        'catalog_status': row.get('status'),
        'available_source_references': references,
        'missing_declared_sources': missing_items,
        'semantic_source_gaps': semantic_gaps,
        'original_task_evaluation_eligible': (
            row.get('admission') == EXECUTION_AND_EVALUATION),
        'required_behavior': (
            'Use every available source. Complete safe reversible work. '
            'When literal task execution is unavailable, produce a complete '
            'best-available resolution with explicit evidence, assumptions, '
            'scenario or pro forma analysis, labeled synthetic material when '
            'useful, estimates, analogous and first-principles solutions, '
            'supplemental items, missing pieces, and next actions.'),
    }
    prompt = (TASK_DATABASE_TRIAL_INSTRUCTION_PROMPT
        + (brief_path.read_text() if brief_path.is_file() else canonical({
            'title': row.get('title') or row.get('id'),
            'job_family': row.get('job_family'),
            'source': row.get('source'),
            'known_acceptance_criteria': row.get('acceptance_criteria'),
            'instruction_limitation': (
                'The original task brief is unavailable. Analyze only the '
                'catalog facts and available admitted material.'),
        })) + '\n\n'
        + canonical({'provided_attachments': attachments,
                     'task_source_condition': source_condition}))
    return TaskIntake('task_pack', prompt, tuple(references)), sources


class RecordedSettingSession:
    """Record each applied setting while retaining one existing budget owner."""

    def __init__(self, authority, artifacts, configuration, records, *, checkpoint_retention=None):
        self._session = ModelExecutionSession(replace(authority, session_factory=None), artifact_store=artifacts)
        self.configuration, self.records = configuration, records
        if checkpoint_retention is not None:
            raise ValueError('automatic deletion of referenced Run History is not a checkpoint retention policy')
        # One Run History per trial, grown with the owner's ledger and
        # checkpointed after every invocation into an append-only store, so
        # N checkpoints of an n-event trial store n events once rather than
        # N full copies; every checkpoint stays referenced and re-loadable.
        self._trial_history = None
        self._projected_events = 0
        self._invocation_sequence = 0

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
        self._invocation_sequence += 1
        operation = (request.semantic_call_id or parent_loop.loop_id) + ':' + str(self._invocation_sequence)
        self.records.record('applied_configuration', operation, {'setting_report': result.report,
            'setting_loop_id': run['loop_id'], 'semantic_call_id': request.semantic_call_id,
            'owner_loop_id': parent_loop.loop_id, 'configuration': self.configuration,
            'input_digest': request.exact_input_digest})
        if result.report['status'] not in ('applied_in_memory', 'unchanged'):
            raise ValueError('requested experiment setting was refused')
        result_start = len(self._session.results)
        event_start = len(parent_loop.ledger.events)
        selected_allocation = result.configuration.output_allocation or self.authority.config.output_allocation
        try:
            return self._session.invoke(result.configuration, parent_loop)
        finally:
            provider_attempts = []
            for gateway_result in self._session.results[result_start:]:
                for attempt in gateway_result.to_dict().get('attempts', ()):
                    provider_attempts.append({key: attempt.get(key) for key in (
                        'provider', 'model', 'route', 'maximum_output_tokens', 'maximum_output_source',
                        'output_capacity_digest', 'provider_ok', 'error_code', 'input_tokens', 'output_tokens',
                        'loop_id', 'semantic_call_id', 'provider_physical_requests')})
            harness_attempts = [{key: event.get(key) for key in ('harness_id', 'adapter_version', 'status', 'attempt_index')}
                for event in parent_loop.ledger.events[event_start:]
                if event.get('action') == 'external_harness_result']
            self.records.record('effective_configuration', operation, {
                'semantic_call_id': request.semantic_call_id, 'owner_loop_id': parent_loop.loop_id,
                'temperature': result.configuration.temperature,
                'requested_output_allocation': selected_allocation.summary() if selected_allocation is not None else None,
                'provider_attempts': provider_attempts, 'harness_attempts': harness_attempts,
                'in_process_gateway': self.authority.harness is None,
                'call_accounting_complete': not self.accounting_uncertain})
            # Persist a current checkpoint after every completed or failed
            # semantic invocation, not just at the task's terminal state.
            from loop_engine.core.run_history import RunHistory
            ledger_events = list(parent_loop.ledger.events)
            root = Path(self.records.path).parent / 'step-history'
            run_id = 'checkpoint-' + digest(str(Path(self.records.path).parent))[:24]
            if self._trial_history is None or self._trial_history.run_id != run_id:
                self._trial_history = RunHistory.from_ledger(ledger_events, run_id=run_id)
            else:
                self._trial_history.extend_from_ledger(ledger_events[self._projected_events:])
            self._projected_events = len(ledger_events)
            checkpoint = self._trial_history.append_checkpoint(str(root))
            self.records.record('step_history', operation, {'history': str(root / run_id),
                'layout': 'append_only_checkpoint_store', 'checkpoint': checkpoint,
                'integrity': self._trial_history.verify_chain(), 'known_calls': self.calls_used,
                'call_accounting_complete': not self.accounting_uncertain,
                'revision': checkpoint['revision'], 'retention': 'immutable_history_preserved',
                'events': len(ledger_events)})


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
        # An interrupted occurrence keeps its evidence. A new directory name
        # does not authorize replay of unresolved effects.
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
        model_call_limit = _work_limit(configuration.get('max_model_calls'))
        pass_limit = _work_limit(configuration.get('max_passes'))
        intake, source_digests = task_intake(row, configuration['context_delivery'])
        records.record('task_sources', 'selected', {'source_digests': source_digests,
                       'input_digest': intake.content_digest, 'source_refs': list(intake.source_refs),
                       'source_snapshot_digest': row.get('source_snapshot_digest'),
                       'source_availability_digest': row.get('source_availability_digest'),
                       'source_freeze_state': row.get('source_freeze_state', 'legacy_not_population_frozen'),
                       'admission': row.get('admission'),
                       'original_task_evaluation_eligible': (
                           row.get('admission') == EXECUTION_AND_EVALUATION)})
        records.record('source_verification', 'before', {
            'state': ('available_sources_verified'
                      if row.get('source_availability')
                      else 'verified' if row.get('source_snapshot')
                      else 'legacy_not_population_frozen'),
            'source_snapshot_digest': row.get('source_snapshot_digest')})
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
                    artifact_store=artifacts, expected_id=name, allow_unavailable=True)
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
            reason='Explicit experimental response allocation; per-cell call and pass authority are separate configuration fields.')
        authority = ModelExecution(gateway, ModelGatewayConfig(route_names=(configuration['route'],),
            allowed_models=(configuration['model'],), allow_failover=False,
            max_route_attempts=None, timeout_seconds=1200, max_total_tokens=None, output_allocation=allocation),
            max_model_calls=model_call_limit, harness=binding,
            session_factory=lambda authority: RecordedSettingSession(authority, artifacts, configuration, records))
        def progress(event):
            safe = {key: event.get(key) for key in ('event_type', 'step', 'model_calls_completed',
                    'elapsed_seconds', 'diagnostic_code', 'failure_code')}
            records.record('progress', 'latest', safe)
            records.refresh_export(cell / 'status.json', {**state, 'status': 'running', 'latest_progress': safe})
            print(canonical({'task': row['id'], **safe}), flush=True)
        outcome = solve_task(SolveRequest(intake, model_execution=authority, runs_dir=str(cell / 'runs'),
            interaction_mode='autonomous', practitioner_mode='non_deterministic', max_passes=pass_limit,
            allow_network_reads=False, allow_workspace_writes=True, allow_sandbox_commands=True,
            workspace_root=str(cell / 'workspace'), allow_source_materialization_to_model=True,
            allow_local_execution=False, quiet_model_io=True, progress=progress))
        value = outcome.to_dict()
        records.record('outcome', 'terminal', value)
        records.export_object(cell / 'outcome.json', value)
        if row.get('source_availability') is not None:
            try:
                verify_available_task_sources(
                    row['task_directory'], row['task_root'],
                    TaskSourceAvailability.from_dict(row['source_availability']))
            except (OSError, ValueError, TypeError):
                records.record('source_verification', 'after', {'state': 'changed_or_unreadable',
                    'source_snapshot_digest': row.get('source_snapshot_digest')})
                raise
            records.record('source_verification', 'after', {'state': 'available_sources_verified',
                'source_snapshot_digest': row.get('source_snapshot_digest')})
        elif row.get('source_snapshot') is not None:
            try:
                verify_task_sources(row['task_directory'], row['task_root'],
                                    TaskSourceSnapshot.from_dict(row['source_snapshot']))
            except (OSError, ValueError, TypeError):
                records.record('source_verification', 'after', {
                    'state': 'changed_or_unreadable',
                    'source_snapshot_digest': row.get('source_snapshot_digest')})
                raise
            records.record('source_verification', 'after', {'state': 'verified',
                'source_snapshot_digest': row.get('source_snapshot_digest')})
        integrity = load_saved_run_bundle(str(cell / 'runs'), value['run_id']).history.verify_chain()
        state.update(status=TRIAL_FINISHED, engine_terminal=value['terminal_code'], engine_solved=value['solved'],
            failure_code=value.get('failure_code', ''),
            provider_failure_codes=terminal_provider_codes(value),
            model_calls=value['model_calls'], model_call_accounting_complete=value['model_call_accounting_complete'],
            model_calls_known_subtotal=value['model_calls_known_subtotal'], history_integrity=integrity,
            delivered_artifacts=len(value['artifacts']),
            resolution_status=(value.get('result') or {}).get('resolution_status'),
            original_task_evaluation_eligible=(
                row.get('admission') == EXECUTION_AND_EVALUATION),
            campaign_acceptance=(
                'independent_task_specific_review_required'
                if row.get('admission') == EXECUTION_AND_EVALUATION
                else 'best_available_resolution_review_required_not_task_acceptance'))
    except Exception as exc:
        state.update(status=TRIAL_FAILED, error_type=type(exc).__name__,
                     error_message='trial boundary failed; private exception text is not exported',
                     model_call_accounting_complete=False)
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


def terminal_provider_codes(outcome):
    """Use the final gateway result, not a folded public solve terminal.

    Earlier recovered failures are not the cause of a later terminal. No
    private provider diagnostic or exception body enters this projection.
    """
    usage = outcome.get('model_usage') or []
    if not usage or not isinstance(usage[-1], dict) or usage[-1].get('ok') is not False:
        return []
    final = usage[-1]
    codes = [attempt.get('error_code') for attempt in final.get('attempts', ()) if isinstance(attempt, dict)]
    codes = [code for code in codes if type(code) is str and code and len(code) <= 128
             and all(c.isalnum() or c == '_' for c in code)]
    if not codes:
        code = final.get('error_code')
        if type(code) is str and code and len(code) <= 128 and all(c.isalnum() or c == '_' for c in code):
            codes.append(code)
    return list(dict.fromkeys(codes))


def outage_decision(result, attempts_so_far, attempt_ceiling):
    """Classify actual terminal errors without inventing an outage."""
    if result.get('engine_terminal') != SolveTerminalCode.PROVIDER_UNAVAILABLE.value:
        return None
    codes = result.get('provider_failure_codes')
    if codes is None:
        code = result.get('failure_code') or ''
        codes = [code] if code else []
    return decide(codes, attempts_so_far=attempts_so_far, attempt_ceiling=attempt_ceiling)


def reconcile_interrupted(records, cursor):
    """Record the interruption without asserting that its effects are resolved.

    Restart requires separate effect reconciliation. Clearing the active
    marker or changing occurrence identity is not proof that replay is safe.
    """
    active = records.latest('controller', 'active_trial')
    if not active:
        return None
    occurrence = str(cursor['round']) + '-attempt-' + str(cursor.get('trial_attempt', 0))
    row = {**active, 'status': 'interrupted_requires_reconciliation', 'occurrence': occurrence,
           'observed_at': datetime.now(timezone.utc).isoformat(),
           'effects_reconciled': False, 'replay_authorized': False}
    records.record('trial_projection', str(active.get('task_id')) + ':' + occurrence, row)
    return row


def _terminate(signum, frame):
    # A termination signal must unwind through every finally block so the
    # trial's records close and the active-trial marker stays for
    # reconciliation, instead of the default handler ending the process.
    raise SystemExit(128 + signum)


def worker(root, *, probe_interval=60, wait_attempt_ceiling=3, refuse_interrupted=False,
           allow_engine_change=False):
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
            gateway = load_runtime_settings(manifest['provider_file']).settings.build_gateway()
            route_name = manifest.get('selected_route_name') or manifest['configuration_space']['fixed_context']['route']
            route = gateway.registry.get(route_name)
            # The frozen typed space is authoritative. Rebuilding from today's
            # defaults would erase declared budget levels or change old trials.
            space = ConfigurationSpace.from_dict(manifest['configuration_space'])
            if space.digest != manifest['configuration_space_digest']:
                raise ValueError('configuration space changed')
            cursor = records.latest('controller', 'cursor')
            if refuse_interrupted and records.latest('controller', 'active_trial'):
                raise ValueError('an interrupted trial requires explicit reconciliation before resume')
            reconciled = reconcile_interrupted(records, cursor)
            if reconciled:
                records.refresh_export(root / 'status.json', reconciled)
                print(canonical(reconciled), flush=True)
                return
            # This exact legacy reader preserves the original Tactical
            # preparation contract. New campaigns receive credentials through
            # their configured gateway or its existing adapter.
            if 'selected_route_name' not in manifest:
                configure_environment()
                gateway = load_runtime_settings(manifest['provider_file']).settings.build_gateway()
            os.environ['LOOP_ENGINE_SANDBOX_IMAGE'] = 'loop-engine-ds1000-runtime@sha256:d29a0fedd17671510b759b15f276b73ee9ba813868653d8923c7365482ee328d'
            endpoint = getattr(gateway.providers[route.provider].adapter, 'endpoint', None)
            identity = engine_identity(manifest['repository'])
            frozen = manifest.get('engine_digest')
            engine_status, refuse = engine_check(frozen, identity['engine_digest'], allow_engine_change)
            if refuse:
                raise ValueError('the engine changed since this campaign was prepared; '
                                 'pass --allow-engine-change to record and continue')
            records.record('controller', 'runtime_identity', {**identity, 'engine_status': engine_status,
                'frozen_engine_digest': frozen, 'controller_file': str(Path(__file__).resolve()),
                'controller_digest': file_digest(__file__), 'worker_pid': os.getpid(),
                'started_at': datetime.now(timezone.utc).isoformat()})
            # Old frozen manifests retain their declared per-trial behavior.
            access_policy = (CampaignAccessPolicy.from_dict(manifest['access_probe_policy'])
                             if 'access_probe_policy' in manifest else CampaignAccessPolicy('per_trial'))
            access_verified = False
            probe = None
            while cursor['round'] < space.cardinality:
                row = rows[cursor['task_position']]
                base = {'worker_pid': os.getpid(), 'task_count': len(rows), 'cursor': cursor,
                        'updated_at': datetime.now(timezone.utc).isoformat()}
                if not activation_due(manifest.get('not_before_utc', ''), datetime.now(timezone.utc)):
                    records.refresh_export(root / 'status.json', {**base, 'status': 'waiting_for_activation_window',
                        'not_before_utc': manifest['not_before_utc'], 'provider': route.provider})
                    time.sleep(probe_interval)
                    continue
                if row['admission'] not in (
                        EXECUTION_AND_EVALUATION, BEST_AVAILABLE_RESOLUTION):
                    # A legacy or unknown admission is recorded once. New
                    # incomplete-source rows enter the separate best-available
                    # resolution lane instead of disappearing before a
                    # Practitioner can inspect what remains.
                    if cursor['round'] == 0:
                        records.record('trial_projection', row['id'] + ':' + str(cursor['round']),
                                       {'status': 'requires_source_admission', 'task_id': row['id'], 'attempted': False})
                    cursor['task_position'] += 1
                    if cursor['task_position'] == len(rows):
                        cursor['task_position'] = 0
                        cursor['round'] += 1
                    records.record('controller', 'cursor', cursor)
                    continue
                else:
                    if manifest.get('readiness_method') == 'gateway_generation_probe':
                        if access_policy.requires_probe(access_verified):
                            probe = probe_gateway(gateway, route, records)
                            access_verified = bool(probe['reachable'])
                        if not probe['reachable']:
                            # A catalog entry or elapsed reset estimate cannot
                            # authorize an endless sequence of failed calls.
                            records.refresh_export(root / 'status.json', {**base,
                                'status': 'provider_access_not_verified', 'provider_observation': probe})
                            return
                    elif endpoint is not None:
                        probe = provider_available(endpoint)
                    else:
                        raise ValueError('this legacy campaign has no compatible metadata probe')
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
                    result = run_trial(root, row, space.configuration_at(index), manifest, occurrence,
                                       services=CampaignTrialServices(gateway))
                    records.record('controller', 'active_trial', {})
                    decision = outage_decision(result, cursor.get('trial_attempt', 0), wait_attempt_ceiling)
                    if decision is not None:
                        if any(code in (OUTAGE, ALLOWANCE) for code in decision['classes']):
                            access_verified = False
                        result = {**result, 'decision': decision}
                        records.record('trial_projection', row['id'] + ':' + occurrence, result)
                        if decision['decision'] in (WAIT_FOR_RECOVERY, WAIT_FOR_ALLOWANCE):
                            cursor['trial_attempt'] = cursor.get('trial_attempt', 0) + 1
                            counter = 'allowance_attempts' if ALLOWANCE in decision['classes'] else 'outage_attempts'
                            cursor[counter] = cursor.get(counter, 0) + 1
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
                        if decision['classes'] and set(decision['classes']) <= {OUTAGE, ALLOWANCE}:
                            # A shared provider wait does not make this task
                            # fail and must not drain the rest of the queue.
                            # The suspension records how many waits were
                            # spent and resets the per-cell counter, so a
                            # restarted worker waits its full ceiling again
                            # instead of suspending after one attempt.
                            cursor['suspended_after_attempts'] = cursor.get('trial_attempt', 0) + 1
                            cursor['suspensions'] = cursor.get('suspensions', 0) + 1
                            cursor['trial_attempt'] = 0
                            records.record('controller', 'cursor', cursor)
                            records.refresh_export(root / 'status.json', {**base, 'cursor': cursor,
                                'status': 'provider_wait_suspended', 'latest_trial': result})
                            return
                        result['status'] = 'failed_with_classified_provider_result'
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
    parser.add_argument('--task-root', default=str(Path(__file__).resolve().parents[2] / 'task_database'))
    parser.add_argument('--provider-file')
    parser.add_argument('--route-name', default='')
    parser.add_argument('--not-before', default='')
    parser.add_argument('--model-call-limit', action='append', type=_parse_work_limit,
                        help='repeat to declare per-cell call-budget grid levels; use unbounded explicitly for no ceiling')
    parser.add_argument('--pass-limit', action='append', type=_parse_work_limit,
                        help='repeat to declare per-cell pass-budget grid levels; no new ceiling is assumed when omitted')
    parser.add_argument('--repository', default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument('--probe-interval', type=int, default=60)
    parser.add_argument('--wait-attempt-ceiling', type=int, default=3,
                        help='bounded waits per cell after a provider-unavailable trial')
    parser.add_argument('--refuse-interrupted', action='store_true',
                        help='raise immediately instead of recording the unresolved interruption')
    parser.add_argument('--allow-engine-change', action='store_true',
                        help='continue a campaign on a changed engine, recording the change')
    parser.add_argument('--wait-for-launch-signal', action='store_true')
    args = parser.parse_args()
    if args.operation != 'prepare' and (args.model_call_limit or args.pass_limit):
        parser.error('work-limit levels belong to prepare; a worker must use its frozen configuration space')
    if args.operation == 'prepare':
        if not args.provider_file:
            parser.error('prepare requires an explicit provider file')
        print(canonical(prepare(args.root, args.task_root, args.provider_file, args.repository,
                               route_name=args.route_name, not_before=args.not_before,
                               model_call_limits=tuple(args.model_call_limit) if args.model_call_limit else (None,),
                               pass_limits=tuple(args.pass_limit) if args.pass_limit else (None,))), flush=True)
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
               refuse_interrupted=args.refuse_interrupted, allow_engine_change=args.allow_engine_change)


if __name__ == '__main__':
    main()
