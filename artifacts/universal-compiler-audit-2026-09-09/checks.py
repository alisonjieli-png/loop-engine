"""Capture this audit's existing offline checks without altering their gates."""
from __future__ import annotations
import argparse
import contextlib
import importlib
import json
from pathlib import Path
import sys
import time

ROOT = Path('/home/username/loop-engine')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['focused', 'full', 'conformance', 'reachability'])
    parser.add_argument('--label', choices=['workspace-tmp'], default=None)
    args = parser.parse_args()
    prefix = args.kind + ('-' + args.label if args.label else '')
    target = HERE / f'{prefix}-checks.json'
    if target.exists():
        raise SystemExit('Refusing to overwrite previous check evidence')
    start = time.monotonic()
    with (HERE / f'{prefix}-checks.log').open('x') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        if args.kind == 'full':
            from loop_engine._self_test import self_test
            result = self_test()
        elif args.kind == 'focused':
            tests = []
            for name in ('core.information_access_checks', 'core.task_fingerprint',
                         'core.reusable_capability_checks', 'core.semantic_runtime_checks',
                         'code_nodes.solution_graph_checks', 'core.stage_assistance_checks',
                         'core.model_token_preflight', 'core.skill_state_context_checks',
                         'core.external_harness', 'core.harness_intelligence_bridge'):
                part = importlib.import_module('loop_engine.' + name).self_test()
                tests.extend(dict(t, owning_module=name) for t in part['tests'])
            result = {'tests': tests, 'passed': sum(bool(t['passed']) for t in tests),
                      'total': len(tests), 'all_passed': all(t['passed'] for t in tests)}
        elif args.kind == 'conformance':
            from loop_engine.conformance_report import run_conformance
            from loop_engine.repository_conformance import run_repository_conformance
            result = {'conformance': run_conformance(), 'repository': run_repository_conformance()}
        else:
            from loop_engine.reachability_report import reachability_report, reachable_from, LIVE_ENTRY_POINTS, shipped_modules
            result = {'summaries': [reachability_report(x) for x in LIVE_ENTRY_POINTS],
                      'static_import_closures': {x: sorted(reachable_from(m)) for x, m in LIVE_ENTRY_POINTS.items()},
                      'scope_warning': 'Static import closure is not invocation, dynamic import completeness, or verified effect.'}
    report = {'record_type': 'audit_check_execution/v1', 'kind': args.kind,
              'elapsed_seconds': time.monotonic() - start, 'python': sys.version,
              'provider_credentials_inherited': False,
              'provider_calls_authorized': False, 'network_policy': 'offline checks; enforcement belongs to launcher',
              'result': result}
    with target.open('x') as out:
        json.dump(report, out, indent=2, default=str)
        out.write('\n')
    print(json.dumps({'report': str(target), 'elapsed_seconds': report['elapsed_seconds'],
                      **{k: result[k] for k in ('passed', 'total', 'all_passed') if k in result}}), flush=True)
