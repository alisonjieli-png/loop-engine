"""Freeze the finite experimental space and inventory actual task folders.

Catalog presence does not qualify an implementation or authorize a model call.
The Cartesian space is a DuckDB view, so millions of planned combinations do
not require millions of handwritten files or a parallel runtime queue.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import zipfile

from .systematic_records import CampaignProjection, canonical, digest


ROOT = Path(__file__).resolve().parents[2]
#: The task folders and the earlier campaign cells live outside the
#: repository. Both locations are machine facts, so they come from the
#: environment; the defaults name the owner's layout under the home
#: directory rather than one account's absolute path.
TASK_ROOT = Path(os.environ.get(
    'LOOP_ENGINE_TASK_DATABASE',
    str(Path.home() / 'task_database' / 'kaggle_tasks')))
PRIOR_CAMPAIGN_RUNS_GLOB = os.environ.get(
    'LOOP_ENGINE_PRIOR_CAMPAIGN_RUNS_GLOB',
    str(Path.home() / 'task-campaign-runs' / '*' / 'cells' / '*' / 'cell.json'))


@dataclass(frozen=True)
class FactorLevel:
    factor: str
    level_id: str
    parameters_json: str
    implementation: str
    maturity: str


def level(factor, name, parameters, implementation, maturity='planned'):
    return FactorLevel(factor, name, canonical(parameters), implementation, maturity)


def levels():
    result = [level('harness', 'native_gateway', {'harness_id': 'native_gateway'},
                    'systematic_runtime.NativeGatewayAdapter', 'needs_qualification')]
    for p in sorted((ROOT / 'embodiments').glob('*/harness.json')):
        value = json.loads(p.read_text())
        result.append(level('harness', value['harness_id'],
            {'harness_id': value['harness_id'], 'configuration_path': str(p),
             'configuration_digest': hashlib.sha256(p.read_bytes()).hexdigest(),
             'package_version': value['package_version'], 'style': value['style']},
            'core.harness_configuration.load_harness_binding', 'installed_configuration_not_qualification'))
    result += [
        level('context', 'bounded_inline', {'projection': 'bounded', 'delivery': 'inline'}, 'systematic_runtime.compose_packet'),
        level('context', 'full_history', {'projection': 'full_history', 'delivery': 'inline'}, 'systematic_runtime.compose_packet'),
        level('context', 'selected_references', {'projection': 'bounded', 'delivery': 'references'}, 'core.information_access.InformationResolver'),
        level('skills', 'none', {'skill_refs': []}, 'systematic_runtime.compose_packet'),
        level('skills', 'admitted_core', {'selection': 'exact_admitted_core_refs'}, 'core.skill_registry.SkillRegistry'),
        level('tools', 'proposal_only', {'worker_tool_policy': 'none'}, 'systematic_runtime.action_dispatch'),
        level('tools', 'read_context', {'worker_tool_policy': 'context_read'}, 'systematic_runtime.action_dispatch'),
        level('tools', 'execute_validate', {'worker_tool_policy': 'context_read_and_sandbox_validation'}, 'core.workspace_operations.WorkspaceOperationService'),
        level('intelligence', 'none', {'layers': [], 'prior_snapshot': None}, 'systematic_runtime.compose_packet'),
        level('intelligence', 'core_context', {'layers': ['context'], 'prior_snapshot': 'frozen_core'}, 'core.practitioner_context'),
        level('intelligence', 'approved_prior', {'layers': ['context', 'code', 'runtime_history_solution', 'user_feedback'], 'prior_snapshot': 'pre_campaign_approved_only'}, 'core.intelligence_layers'),
        level('first_steps', 'orient_first', {'initial_steps': ['orient', 'propose']}, 'systematic_runtime.run_steps'),
        level('first_steps', 'inspect_first', {'initial_steps': ['inspect', 'orient', 'propose']}, 'systematic_runtime.run_steps'),
        level('first_steps', 'model_selected', {'initial_steps': ['select_next_step']}, 'systematic_runtime.run_steps'),
        level('initialization', 'fresh_minimal', {'process_lifetime': 'fresh', 'seed_files': []}, 'core.harness_process'),
        level('initialization', 'fresh_core_files', {'process_lifetime': 'fresh', 'seed_bundle': 'exact_core_resources'}, 'systematic_runtime.SeededHarnessAdapter'),
        level('outputs', 'single', {'production_policy': 'one_verified_candidate'}, 'systematic_runtime.produce_candidates'),
        level('outputs', 'continued', {'production_policy': 'first_candidate_then_alternatives'}, 'loop.reactive_outputs'),
        level('temperature', 'zero', {'temperature': 0.0}, 'code_nodes.solution_model_port.ModelInvocationRequest'),
        level('temperature', 'exploratory', {'temperature': 0.7}, 'code_nodes.solution_model_port.ModelInvocationRequest'),
        level('expectations', 'contracts_only', {'semantic_reviews': False, 'structural_checks': True}, 'core.observation_expectations'),
        level('expectations', 'before_after_actions', {'semantic_reviews': True, 'structural_checks': True}, 'systematic_runtime.review_expectation'),
        # The two layering dimensions from the 2026-09-13 proposal. The direct
        # adapter and the owning-Loop policy are what every current recipe runs
        # and are recorded as installed configuration; the other levels are
        # declarations the binding refuses to execute until an executor exists,
        # so they stay planned. Records: core.harness_layering.
        level('wrapper_composition', 'direct', {'layers': [], 'record_type': 'harness_wrapper_composition/v1'},
              'core.harness_layering.WrapperComposition', 'installed_configuration_not_qualification'),
        level('wrapper_composition', 'instruction_preparation_then_direct',
              {'layers': [{'wrapper_id': 'instruction-preparation', 'responsibilities': ['instruction_preparation']}],
               'record_type': 'harness_wrapper_composition/v1'},
              'core.harness_layering.WrapperComposition', 'planned'),
        level('native_control', 'owning_loop', {'ownership': 'owning_loop_for_every_control',
                                                'record_type': 'harness_native_control_policy/v1'},
              'core.harness_layering.NativeControlPolicy', 'installed_configuration_not_qualification'),
        level('native_control', 'supervised_planning',
              {'ownership': 'owning_loop_except_planning_supervised', 'requires_adapter_native_controls': ['planning_and_continuation'],
               'record_type': 'harness_native_control_policy/v1'},
              'core.harness_layering.NativeControlPolicy', 'planned'),
    ]
    return result


def prepare(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    store = CampaignProjection(root / 'campaign.duckdb')
    c = store.connection
    c.execute('CREATE TABLE IF NOT EXISTS factor_levels(factor VARCHAR, level_id VARCHAR, parameters JSON, implementation VARCHAR, maturity VARCHAR, PRIMARY KEY(factor,level_id))')
    frozen_levels = levels()
    existing = c.execute('SELECT factor,level_id,parameters,implementation,maturity FROM factor_levels').fetchall()
    expected_levels = {(v.factor,v.level_id): (v.parameters_json,v.implementation,v.maturity) for v in frozen_levels}
    if any(expected_levels.get((row[0],row[1])) != tuple(row[2:]) for row in existing):
        raise ValueError('factor catalog changed; use a new experiment version')
    c.executemany('INSERT INTO factor_levels VALUES (?,?,?::JSON,?,?) ON CONFLICT DO NOTHING',
                  [(v.factor, v.level_id, v.parameters_json, v.implementation, v.maturity) for v in frozen_levels])
    c.execute('CREATE TABLE IF NOT EXISTS task_catalog(task_id VARCHAR PRIMARY KEY, source_directory VARCHAR, descriptor_digest VARCHAR, previously_attempted BOOLEAN, archive_count INTEGER, declared_uncompressed_bytes BIGINT, admission_status VARCHAR, descriptor JSON)')
    prior = {row[0] for row in c.execute(
        "SELECT DISTINCT task FROM read_json_auto(?, union_by_name=true)",
        [PRIOR_CAMPAIGN_RUNS_GLOB]).fetchall()}
    for folder in sorted(TASK_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        if c.execute('SELECT 1 FROM task_catalog WHERE task_id=?',[folder.name]).fetchone():
            continue
        description = folder / 'description.json'
        raw = description.read_bytes() if description.is_file() else b'[]'
        metadata_error = None
        try:
            descriptions = json.loads(raw)
        except ValueError:
            descriptions = []
            metadata_error = 'descriptor_is_not_valid_json'
        sections = [v for v in descriptions if isinstance(v, dict)] if isinstance(descriptions, list) else []
        archives = []
        for archive in sorted((folder / 'data').glob('*.zip')):
            try:
                with zipfile.ZipFile(archive) as z:
                    members = [{'name': v.filename, 'bytes': v.file_size, 'crc32': v.CRC}
                               for v in z.infolist() if not v.is_dir()]
                unsafe = [v['name'] for v in members if Path(v['name']).is_absolute() or '..' in Path(v['name']).parts]
                archives.append({'path': str(archive), 'bytes': archive.stat().st_size,
                                 'members': members, 'unsafe_paths': unsafe,
                                 'content_digest_state': 'not_yet_admitted'})
            except (OSError, zipfile.BadZipFile) as exc:
                archives.append({'path': str(archive), 'error': type(exc).__name__, 'members': []})
        status = ('previously_attempted_excluded_from_fresh_tasks' if folder.name in prior else
                  'requires_metadata_recovery' if metadata_error else
                  'missing_data' if not archives else 'requires_task_and_evaluator_admission')
        descriptor = {'record_type': 'systematic_task_candidate/v1', 'task_id': folder.name,
                      'sections': sections, 'archives': archives, 'metadata_error': metadata_error,
                      'raw_descriptor_sha256': hashlib.sha256(raw).hexdigest(),
                      'license_state': 'source_terms_retained_not_redistribution_authority',
                      'unseen_scope': 'absent_from_surviving_task_campaign_cell_ids' if folder.name not in prior else 'previously_attempted',
                      'pretraining_unseen_claim': False}
        c.execute('INSERT INTO task_catalog VALUES (?,?,?,?,?,?,?,?::JSON)',
                  [folder.name, str(folder), digest(descriptor), folder.name in prior,
                   len(archives), sum(v['bytes'] for a in archives for v in a['members']), status, canonical(descriptor)])
    factors = sorted({v.factor for v in frozen_levels})
    aliases = ['f' + str(i) for i in range(len(factors))]
    selections = ', '.join(a + '.level_id AS ' + factor for a, factor in zip(aliases, factors))
    sources = ' CROSS JOIN '.join("(SELECT level_id FROM factor_levels WHERE factor='" + factor + "') " + a
                                  for a, factor in zip(aliases, factors))
    c.execute('CREATE VIEW IF NOT EXISTS configurations AS SELECT ' + selections + ' FROM ' + sources)
    count = c.execute('SELECT count(*) FROM configurations').fetchone()[0]
    fresh = c.execute('SELECT count(*) FROM task_catalog WHERE NOT previously_attempted').fetchone()[0]
    spec = {'record_type': 'systematic_campaign/v1', 'campaign_id': root.name,
            'task_root': str(TASK_ROOT), 'model_id': 'gemma-4-coding-abliterated',
            'provider_id': 'tactical', 'route_name': 'custom.tactical',
            'termination_preference': 'complete_registered_matrix',
            'per_task_model_call_limit': None, 'per_task_pass_limit': None,
            'automatic_provider_failover': False,
            'configurations_per_task': count, 'fresh_task_candidates': fresh,
            'theoretical_cells_before_admission': count * fresh,
            'factor_order': factors,
            'factor_catalog_digest': digest([v.__dict__ for v in frozen_levels]),
            'evaluation': 'development_feedback_and_sealed_final_evaluation_separate',
            'status': 'cataloged_not_run',
            'coverage_rule': 'Only exact implemented and qualified configurations may dispatch; others remain explicit gaps.'}
    store.record('campaign', root.name, spec)
    store.export_object(root / 'campaign-manifest.json', spec)
    print(c.execute('SELECT factor,count(*) FROM factor_levels GROUP BY factor ORDER BY factor').fetchall())
    print(c.execute('SELECT admission_status,count(*) FROM task_catalog GROUP BY admission_status ORDER BY admission_status').fetchall())
    print('Configurations per task:', count, 'Theoretical cells before admission:', count * fresh)
    store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    prepare(parser.parse_args().root)
