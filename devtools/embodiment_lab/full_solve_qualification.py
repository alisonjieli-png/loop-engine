"""Run a real installed harness on the complete public solve fixture workflow.

Model replies are explicit fixtures. Source generation, Docker commands,
independent verification, harness processes and saved Run History are real.
This qualifies integration, not live model reasoning quality.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples/22_product_quickstart'
sys.path.insert(0, str(EXAMPLE))
import acceptance_oracles
import run_acceptance
from loop_engine.code_nodes.solve_runtime import SolveRequest, solve_task
from loop_engine.core.harness_configuration import load_harness_binding
from loop_engine.core.model_gateway import ModelGateway
from loop_engine.core.model_routes import ModelProviderCapabilities
from loop_engine.core.run_history import load_saved_run_bundle
from loop_engine.templates.intake import intake_task


def bind_enveloped_fixture(answer, prompt):
    """Resolve one unique fixture-phase packet inside the observed CLI envelope."""
    value = json.loads(answer)
    if not isinstance(value, dict) or 'acceptance_fixture_for' not in value:
        return answer
    decoder = json.JSONDecoder()
    found = []
    for index, character in enumerate(prompt):
        if character != '{':
            continue
        try:
            candidate, end = decoder.raw_decode(prompt[index:])
        except ValueError:
            continue
        if (isinstance(candidate, dict)
                and candidate.get('record_type') == value['acceptance_fixture_for']
                and isinstance(candidate.get('registered_acceptance_criteria'), dict)):
            found.append(prompt[index:index+end])
    if len(found) != 1:
        raise ValueError('fixture needs exactly one complete verifier packet in the harness envelope')
    return ORIGINAL_BIND(answer, found[0])


ORIGINAL_BIND = acceptance_oracles.bind_response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--harness', required=True)
    parser.add_argument('--case', choices=('a', 'b', 'c', 'd'), default='a')
    parser.add_argument('--control', choices=('wrong_math', 'undeclared_dependency'), default='')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    out = args.out.resolve()
    if not out.is_relative_to(ROOT):
        raise SystemExit('qualification outputs must remain inside loop-engine')
    out.mkdir(parents=True, exist_ok=False)
    fixtures = EXAMPLE / 'fixtures'
    intake_request, answers = (run_acceptance._task_a() if args.case == 'a' else
        getattr(run_acceptance, '_task_' + args.case)(fixtures))
    if args.control:
        if args.case != 'a':
            raise SystemExit('the negative controls apply to the expense task')
        answers = acceptance_oracles.negative_answers(answers, args.control)
    manifest = {'harness': args.harness, 'case': args.case, 'control': args.control,
                'model_semantics': 'explicit_fixture_not_live_model', 'fixture_replies': len(answers),
                'answer_digest': hashlib.sha256(json.dumps(answers).encode()).hexdigest(),
                'task': intake_request.text or intake_request.goal,
                'source_identities': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (Path(__file__), EXAMPLE / 'run_acceptance.py',
                                 EXAMPLE / 'acceptance_oracles.py')}}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    acceptance_oracles.bind_response = bind_enveloped_fixture
    authority = acceptance_oracles.model_execution(answers)
    old_route = authority.gateway.registry.get('fixture.route')
    route = replace(old_route, capabilities=ModelProviderCapabilities(
        'fixture', 'local', True, max_context=131072))
    gateway = ModelGateway(providers=tuple(authority.gateway.providers.values()), routes=(route,),
                           policy=authority.gateway.policy)
    binding = load_harness_binding(str(ROOT / 'embodiments' / args.harness / 'harness.json'),
        work_root=str(out / 'processes'), socket_directory=str(ROOT / '.loop-engine-dev/hs'),
        expected_id=args.harness)
    authority = replace(authority, gateway=gateway, harness=binding)
    result = solve_task(SolveRequest(
        intake_task(intake_request), model_execution=authority, runs_dir=str(out / 'runs'),
        interaction_mode='autonomous', max_passes=1 if args.case == 'a' else 2,
        allow_workspace_writes=True, allow_sandbox_commands=True,
        workspace_root=str(out / 'workspace'), allow_source_materialization_to_model=args.case != 'a',
        quiet_model_io=True))
    value = result.to_dict()
    (out / 'outcome.json').write_text(json.dumps(value, indent=2) + '\n')
    bundle = load_saved_run_bundle(str(out / 'runs'), value['run_id'])
    model_events = [event for event in bundle.history.event_log if event.event_type == 'model_invocation']
    harness_events = [event for event in bundle.history.event_log
                      if 'external_harness_result' in str(event.detail)]
    checks = {
        'terminal_matches_expected_acceptance': (value['terminal_code'] == 'COMPLETED_VERIFIED'
                                               if not args.control else not value['solved']),
        'history_chain_intact': bundle.history.verify_chain()['intact'],
        'physical_calls_match_history': value['model_calls'] == len(model_events),
        'harness_was_actually_invoked': bool(harness_events),
        'independent_verification_required': value.get('verification', {}).get(
            'independent_verification_policy', {}).get('required') is True,
    }
    report = {'harness': args.harness, 'terminal_code': value['terminal_code'],
        'checks': checks, 'all_passed': all(checks.values()), 'fixture_model_calls': value['model_calls'],
        'live_provider_calls': 0, 'harness_events': len(harness_events),
        'independent_verification': value.get('verification', {}).get('independent_checks', []),
        'output': str(out)}
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
