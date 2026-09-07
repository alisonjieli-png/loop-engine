"""Live unseen-task campaign runner over the sealed novel population.

This runner reuses the frozen generalization-probe host machinery exactly:
same manifest-driven operation surface, same Docker sandbox, same oracle
discipline. Only the population differs, and it has never been run through
the engine before this campaign. No repair or continuation against these
tasks is permitted inside the campaign; a failed task is recorded as failed.

Default invocation prints the frozen plan with zero model calls. Live
execution requires both explicit grant flags and a new work root, mirroring
the generalization probe.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generalization_probe as probe
from generalization_probe import (
    SolveRequest, TaskIntakeRequest, ModelExecution, ModelGateway, ModelGatewayConfig,
    HOST_INSTRUCTIONS, canonical, digest, docker_workspace, make_host, model_usage_summary,
    population_manifest, require_file_bindings, solve_task, intake_task, write_json)
from novel_task_population import task_population

RUNNER_DIGEST_NOTE = 'novel campaign runner reuses the frozen probe host machinery'


def campaign_manifest(tasks, *, model_route, model_id):
    manifest = population_manifest(tasks, model_route=model_route, model_id=model_id)
    manifest['record_type'] = 'novel_task_campaign_population/v1'
    manifest['selection_reason'] = ('All ten sealed novel tasks; authored for this campaign and never '
                                     'previously executed through the engine.')
    manifest['limitations'] = [
        'novel by construction for this repository, not proven outside model pretraining',
        'one attempt per task; no repair or continuation against this population',
        'operator runs the batch but does not direct individual task outcomes',
        'post-campaign independent audit may invalidate accepted solutions',
        'nonfinite arguments use a fixed trusted constant codec, never model-supplied Python expressions']
    return manifest


def main(argv=None):
    all_tasks = task_population()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir')
    parser.add_argument('--authorize-model-calls', action='store_true')
    parser.add_argument('--allow-source-to-model', action='store_true')
    parser.add_argument('--model-route', default='cloud.default')
    parser.add_argument('--model-id', default='deepseek-v4-flash:0731')
    parser.add_argument('--task', action='append', choices=[task.task_id for task in all_tasks])
    args = parser.parse_args(argv)
    if args.task and len(args.task) != len(set(args.task)):
        parser.error('--task entries must be unique.')
    tasks = tuple(task for task in all_tasks if not args.task or task.task_id in args.task)
    manifest = campaign_manifest(tasks, model_route=args.model_route, model_id=args.model_id)
    manifest['requested_task_ids'] = args.task or [task.task_id for task in all_tasks]
    if not args.authorize_model_calls:
        print(canonical({'plan': manifest, 'model_calls': 0, 'files_written': 0}))
        return 0
    if not args.allow_source_to_model or not args.work_dir:
        parser.error('Live execution requires --allow-source-to-model and a new --work-dir.')
    root = Path(args.work_dir).absolute()
    if root.exists() or any(path.is_symlink() for path in (root, *root.parents)):
        parser.error('--work-dir must not already exist.')
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
        calls_complete = all(item['model_call_accounting_complete'] is True for item in outcomes)
        tokens_complete = all(item['model_usage']['token_accounting_complete'] is True for item in outcomes)
        known_input = sum(item['model_usage'].get('known_input_tokens_subtotal', 0) for item in outcomes)
        known_output = sum(item['model_usage'].get('known_output_tokens_subtotal', 0) for item in outcomes)
        return {'record_type': 'novel_task_campaign_report/v1', 'population_digest': digest(manifest),
                'selected': len(tasks), 'attempted': len(outcomes),
                'verified_completed': sum(item['solved'] for item in outcomes),
                'not_started': [task.task_id for task in tasks if task.task_id not in {item['task_id'] for item in outcomes}],
                'usage_scope': 'attempted_tasks',
                'model_calls': sum(item['model_calls'] for item in outcomes) if calls_complete else None,
                'model_calls_known_subtotal': sum(item['model_calls_known_subtotal'] for item in outcomes),
                'model_call_accounting_complete': calls_complete,
                'input_tokens': known_input if tokens_complete else None,
                'output_tokens': known_output if tokens_complete else None,
                'known_input_tokens_subtotal': known_input, 'known_output_tokens_subtotal': known_output,
                'token_accounting_complete': tokens_complete, 'cost_usd': None, 'cost_state': 'unknown',
                'outcomes': outcomes, 'limitations': manifest['limitations']}

    for task in tasks:
        task_root = root / task.task_id
        task_root.mkdir()
        started = False
        phase = 'host_preparation'
        try:
            host = make_host(task_root, task)
            if not docker_workspace(task_root / 'source', probe.IMAGE).availability().available:
                raise RuntimeError('pinned sandbox unavailable before model dispatch')
            model = ModelExecution(gateway, ModelGatewayConfig(
                route_names=(args.model_route,), allowed_models=(args.model_id,), allow_failover=False))
            prompt = task.manifest()['effective_prompt']

            def progress(value):
                if value.get('event_type') in ('model.step.started', 'model.step.completed', 'practitioner.diagnostic'):
                    print(canonical({'task_id': task.task_id, **{key: value.get(key) for key in (
                        'event_type', 'run_id', 'step', 'model_calls_completed', 'elapsed_seconds', 'diagnostic_code')}}), flush=True)

            started = True
            phase = 'solve'
            outcome = solve_task(SolveRequest(intake_task(TaskIntakeRequest(text=prompt)), model_execution=model,
                host_runtime=host, runs_dir=str(task_root / 'runs'), interaction_mode='autonomous', quiet_model_io=True,
                progress=progress))
            phase = 'save_outcome'
            write_json(task_root / 'outcome.json', outcome.to_dict())
            entry = {'task_id': task.task_id, 'shape': task.shape, 'task_digest': task.content_digest,
                     'terminal_code': outcome.status, 'solved': outcome.solved, 'run_id': outcome.run_id,
                     'model_calls': outcome.model_calls, 'model_calls_known_subtotal': outcome.model_calls_known_subtotal,
                     'model_call_accounting_complete': outcome.model_call_accounting_complete,
                     'model_usage': model_usage_summary(outcome),
                     'elapsed_seconds': outcome.elapsed_seconds, 'outcome_path': str(task_root / 'outcome.json')}
        except BaseException as exc:
            entry = {'task_id': task.task_id, 'shape': task.shape, 'task_digest': task.content_digest,
                     'terminal_code': 'RUNNER_EXCEPTION', 'solved': False, 'error_type': type(exc).__name__,
                     'phase': phase,
                     'model_calls': None if started else 0, 'model_call_accounting_complete': not started,
                     'model_usage': {'input_tokens': None if started else 0, 'output_tokens': None if started else 0,
                                     'token_accounting_complete': not started, 'cost_usd': None, 'cost_state': 'unknown'},
                     'model_calls_known_subtotal': 0, 'run_id': None}
            write_json(task_root / 'runner-failure.json', entry)
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                outcomes.append(entry)
                write_json(root / 'report.json', report())
                raise
        outcomes.append(entry)
        write_json(root / f'progress-{len(outcomes):04d}.json', report())
        print(canonical(entry), flush=True)
    write_json(root / 'report.json', report())
    print(canonical(report()))
    return 0 if all(item['solved'] for item in outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())