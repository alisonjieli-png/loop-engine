"""Unseen-task campaign runner, version 2: provenance-bound, with a shared
learning store, repeated passes, and durable evidence.

Version 1 reused the frozen probe host machinery and is the record of the
2026-09-06 run. Version 2 keeps that machinery and the same grant flags, and
adds what the 2026-09-07 review found missing:

- Provenance. The manifest records the SHA-256 of this runner, the population
  module, the offline check, and the probe module, and every one of them is
  rechecked before each dispatch, as the five-shape probe does for itself.
- A learning arm. ``--shared-runs-dir`` gives every task one Run History root,
  so the stage store and region evidence one task records are visible to the
  next. Version 1 gave each task its own root, which made cross-task learning
  impossible by construction.
- Repeated passes. ``--passes N`` runs the whole population N times in
  sequence; pass two runs inside the regions pass one populated. The report
  groups calls, tokens, observations, and the region evidence each run saw
  per pass, so learning is measured instead of assumed.
- Durable evidence. ``--evidence-out DIR`` copies each task's frozen task,
  observations, outcome, and final source out of the work root, which on this
  machine is tmpfs.

Default invocation prints the frozen plan with zero model calls and zero
file writes. Live execution requires both grant flags and a new work root.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generalization_probe as probe
from generalization_probe import (
    SolveRequest, TaskIntakeRequest, ModelExecution, ModelGateway, ModelGatewayConfig,
    canonical, digest, docker_workspace, make_host, model_usage_summary,
    population_manifest, solve_task, intake_task, write_json)
import novel_task_offline_check_v2 as offline_check
import novel_task_population_v2 as population_module
from novel_task_population_v2 import POPULATION_RECORD_TYPE, task_population

REPORT_RECORD_TYPE = 'novel_task_campaign_report/v2'
REGION_EVIDENCE_VISIBLE_BYTES = 4096
EVIDENCE_FILES = ('frozen-task.json', 'outcome.json', 'runner-failure.json')


def module_digests():
    """SHA-256 of every source file whose behavior the campaign depends on."""
    return {name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name, module in (('runner', sys.modules[__name__]),
                                 ('population', population_module),
                                 ('offline_check', offline_check),
                                 ('probe', probe))}


def require_module_digests(expected):
    """Refuse dispatch when any frozen source changed after the plan was written."""
    current = module_digests()
    changed = sorted(name for name in expected if current.get(name) != expected[name])
    if changed:
        raise ValueError('frozen campaign source changed: ' + ', '.join(changed))


def campaign_manifest(tasks, *, model_route, model_id, shared_runs_dir=False, passes=1,
                      evidence_out=None):
    manifest = population_manifest(tasks, model_route=model_route, model_id=model_id)
    manifest['record_type'] = POPULATION_RECORD_TYPE
    manifest['module_digests'] = module_digests()
    manifest['selection_reason'] = ('Population version 2: the ten tasks with prompts and oracles that '
                                    'agree, one attempt per task per pass.')
    manifest['learning'] = {'shared_runs_dir': bool(shared_runs_dir), 'passes': int(passes),
                            'evidence_out': str(evidence_out) if evidence_out else None,
                            'region_evidence_source': 'outcome.intelligence.region_evidence'}
    manifest['limitations'] = [
        'textbook problems with contract twists; novel to this repository, not to any model',
        'one attempt per task per pass; no operator repair inside a pass',
        'a later pass may reuse stages the earlier pass recorded only under --shared-runs-dir',
        'post-campaign independent audit (novel_task_audit_v2) may invalidate accepted solutions',
        'nonfinite arguments use a fixed trusted constant codec, never model-supplied Python expressions']
    return manifest


def region_summary(outcome_record):
    """The region evidence a run saw, bounded so the report stays readable."""
    evidence = (outcome_record.get('intelligence') or {}).get('region_evidence') or {}
    summary = {key: evidence.get(key) for key in ('region_ref', 'advisory', 'shortcut_decision',
                                                  'tuning_decision', 'region_statistics')
               if key in evidence}
    text = canonical(summary)
    if len(text.encode('utf-8')) > REGION_EVIDENCE_VISIBLE_BYTES:
        return {'region_ref': evidence.get('region_ref'), 'advisory': evidence.get('advisory'),
                'region_evidence_digest': digest(evidence),
                'summary': 'Region evidence retained in outcome.json; too large for the report.'}
    return summary


def copy_evidence(task_root, destination):
    """Copy the durable subset of one task's work root; the Run History stays in place."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    copied = []
    for name in EVIDENCE_FILES:
        source = task_root / name
        if source.is_file():
            shutil.copy2(source, destination / name)
            copied.append(name)
    for observation in sorted(task_root.glob('observation-*.json')):
        shutil.copy2(observation, destination / observation.name)
        copied.append(observation.name)
    final_source = task_root / 'source' / 'solution.py'
    if final_source.is_file():
        (destination / 'source').mkdir()
        shutil.copy2(final_source, destination / 'source' / 'solution.py')
        copied.append('source/solution.py')
    return copied


def pass_report(outcomes, pass_index):
    selected = [item for item in outcomes if item['pass_index'] == pass_index]
    calls_complete = all(item['model_call_accounting_complete'] is True for item in selected)
    tokens_complete = all(item['model_usage']['token_accounting_complete'] is True for item in selected)
    return {'pass_index': pass_index, 'attempted': len(selected),
            'verified_completed': sum(1 for item in selected if item['solved']),
            'model_calls': sum(item['model_calls'] for item in selected) if calls_complete else None,
            'model_calls_known_subtotal': sum(item['model_calls_known_subtotal'] for item in selected),
            'input_tokens': (sum(item['model_usage']['known_input_tokens_subtotal'] for item in selected)
                             if tokens_complete else None),
            'output_tokens': (sum(item['model_usage']['known_output_tokens_subtotal'] for item in selected)
                              if tokens_complete else None),
            'per_task': [{key: item.get(key) for key in (
                'task_id', 'terminal_code', 'solved', 'model_calls', 'observations', 'elapsed_seconds',
                'region_evidence')} for item in selected]}


def campaign_report(manifest, tasks, outcomes, passes):
    calls_complete = all(item['model_call_accounting_complete'] is True for item in outcomes)
    tokens_complete = all(item['model_usage']['token_accounting_complete'] is True for item in outcomes)
    known_input = sum(item['model_usage'].get('known_input_tokens_subtotal', 0) for item in outcomes)
    known_output = sum(item['model_usage'].get('known_output_tokens_subtotal', 0) for item in outcomes)
    attempted = {(item['pass_index'], item['task_id']) for item in outcomes}
    return {'record_type': REPORT_RECORD_TYPE, 'population_digest': digest(manifest),
            'module_digests': manifest['module_digests'], 'learning': manifest['learning'],
            'selected': len(tasks) * passes, 'attempted': len(outcomes),
            'verified_completed': sum(1 for item in outcomes if item['solved']),
            'not_started': [f'pass-{index:02d}/{task.task_id}' for index in range(1, passes + 1)
                            for task in tasks if (index, task.task_id) not in attempted],
            'usage_scope': 'attempted_tasks',
            'model_calls': sum(item['model_calls'] for item in outcomes) if calls_complete else None,
            'model_calls_known_subtotal': sum(item['model_calls_known_subtotal'] for item in outcomes),
            'model_call_accounting_complete': calls_complete,
            'input_tokens': known_input if tokens_complete else None,
            'output_tokens': known_output if tokens_complete else None,
            'known_input_tokens_subtotal': known_input, 'known_output_tokens_subtotal': known_output,
            'token_accounting_complete': tokens_complete, 'cost_usd': None, 'cost_state': 'unknown',
            'per_pass': [pass_report(outcomes, index) for index in range(1, passes + 1)],
            'outcomes': outcomes, 'limitations': manifest['limitations']}


def build_parser(all_tasks):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir')
    parser.add_argument('--authorize-model-calls', action='store_true')
    parser.add_argument('--allow-source-to-model', action='store_true')
    parser.add_argument('--model-route', default='cloud.default')
    parser.add_argument('--model-id', default='deepseek-v4-flash:0731')
    parser.add_argument('--task', action='append', choices=[task.task_id for task in all_tasks])
    parser.add_argument('--shared-runs-dir', action='store_true',
                        help='one Run History root for every task, so stages and region evidence are shared')
    parser.add_argument('--passes', type=int, default=1,
                        help='run the whole population this many times in sequence')
    parser.add_argument('--evidence-out',
                        help='durable directory receiving each task\'s frozen task, observations, outcome, and source')
    return parser


def main(argv=None):
    all_tasks = task_population()
    parser = build_parser(all_tasks)
    args = parser.parse_args(argv)
    if args.task and len(args.task) != len(set(args.task)):
        parser.error('--task entries must be unique.')
    if args.passes < 1:
        parser.error('--passes must be at least 1.')
    tasks = tuple(task for task in all_tasks if not args.task or task.task_id in args.task)
    evidence_out = Path(args.evidence_out).absolute() if args.evidence_out else None
    manifest = campaign_manifest(tasks, model_route=args.model_route, model_id=args.model_id,
                                 shared_runs_dir=args.shared_runs_dir, passes=args.passes,
                                 evidence_out=evidence_out)
    manifest['requested_task_ids'] = args.task or [task.task_id for task in all_tasks]
    if not args.authorize_model_calls:
        print(canonical({'plan': manifest, 'model_calls': 0, 'files_written': 0}))
        return 0
    if not args.allow_source_to_model or not args.work_dir:
        parser.error('Live execution requires --allow-source-to-model and a new --work-dir.')
    root = Path(args.work_dir).absolute()
    if root.exists() or any(path.is_symlink() for path in (root, *root.parents)):
        parser.error('--work-dir must not already exist.')
    if evidence_out is not None and evidence_out.exists():
        parser.error('--evidence-out must not already exist.')
    gateway = ModelGateway()
    route = gateway.registry.get(args.model_route)
    if route.model != args.model_id or route.provider != 'ollama_cloud':
        parser.error('Use the exact configured Ollama Cloud route and model for this campaign.')
    capability = gateway.providers[route.provider].output_capability_for(args.model_id)
    if capability.declared_maximum is None:
        parser.error('The exact route lacks known source-backed output capacity.')
    manifest['output_capacity'] = capability.summary()
    root.mkdir(parents=True)
    write_json(root / 'population.json', manifest)
    outcomes = []

    def report():
        return campaign_report(manifest, tasks, outcomes, args.passes)

    for pass_index in range(1, args.passes + 1):
        pass_root = root / f'pass-{pass_index:02d}' if args.passes > 1 else root
        pass_root.mkdir(exist_ok=True)
        for task in tasks:
            task_root = pass_root / task.task_id
            task_root.mkdir()
            runs_dir = (root / 'runs') if args.shared_runs_dir else (task_root / 'runs')
            started = False
            phase = 'host_preparation'
            try:
                require_module_digests(manifest['module_digests'])
                host = make_host(task_root, task)
                if not docker_workspace(task_root / 'source', probe.IMAGE).availability().available:
                    raise RuntimeError('pinned sandbox unavailable before model dispatch')
                model = ModelExecution(gateway, ModelGatewayConfig(
                    route_names=(args.model_route,), allowed_models=(args.model_id,), allow_failover=False))
                prompt = task.manifest()['effective_prompt']

                def progress(value):
                    if value.get('event_type') in ('model.step.started', 'model.step.completed',
                                                   'practitioner.diagnostic'):
                        print(canonical({'pass_index': pass_index, 'task_id': task.task_id, **{
                            key: value.get(key) for key in (
                                'event_type', 'run_id', 'step', 'model_calls_completed',
                                'elapsed_seconds', 'diagnostic_code')}}), flush=True)

                started = True
                phase = 'solve'
                outcome = solve_task(SolveRequest(
                    intake_task(TaskIntakeRequest(text=prompt)), model_execution=model,
                    host_runtime=host, runs_dir=str(runs_dir), interaction_mode='autonomous',
                    quiet_model_io=True, progress=progress))
                phase = 'save_outcome'
                record = outcome.to_dict()
                write_json(task_root / 'outcome.json', record)
                entry = {'pass_index': pass_index, 'task_id': task.task_id, 'shape': task.shape,
                         'task_digest': task.content_digest, 'terminal_code': outcome.status,
                         'solved': outcome.solved, 'run_id': outcome.run_id,
                         'model_calls': outcome.model_calls,
                         'model_calls_known_subtotal': outcome.model_calls_known_subtotal,
                         'model_call_accounting_complete': outcome.model_call_accounting_complete,
                         'model_usage': model_usage_summary(outcome),
                         'elapsed_seconds': outcome.elapsed_seconds,
                         'observations': len(list(task_root.glob('observation-*.json'))),
                         'runs_dir': str(runs_dir), 'region_evidence': region_summary(record),
                         'outcome_path': str(task_root / 'outcome.json')}
            except BaseException as exc:
                entry = {'pass_index': pass_index, 'task_id': task.task_id, 'shape': task.shape,
                         'task_digest': task.content_digest, 'terminal_code': 'RUNNER_EXCEPTION',
                         'solved': False, 'error_type': type(exc).__name__, 'phase': phase,
                         'model_calls': None if started else 0,
                         'model_call_accounting_complete': not started,
                         'model_usage': {'input_tokens': None if started else 0,
                                         'output_tokens': None if started else 0,
                                         'token_accounting_complete': not started,
                                         'cost_usd': None, 'cost_state': 'unknown'},
                         'model_calls_known_subtotal': 0, 'run_id': None,
                         'observations': len(list(task_root.glob('observation-*.json'))),
                         'runs_dir': str(runs_dir), 'region_evidence': {}}
                write_json(task_root / 'runner-failure.json', entry)
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    outcomes.append(entry)
                    write_json(root / 'report.json', report())
                    raise
            if evidence_out is not None:
                entry['evidence_copied'] = copy_evidence(
                    task_root, evidence_out / f'pass-{pass_index:02d}' / task.task_id)
            outcomes.append(entry)
            write_json(root / f'progress-{len(outcomes):04d}.json', report())
            print(canonical(entry), flush=True)
    write_json(root / 'report.json', report())
    print(canonical(report()))
    return 0 if all(item['solved'] for item in outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
