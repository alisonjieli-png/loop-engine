"""Qualify an installed snapshot and export derived reports through DuckDB.

This application changes no source checkout and calls no model. The existing
conformance generator's JSON stream is materialized by the database writer.
Canonical test fixtures and Run History keep their existing storage contracts.
"""
from __future__ import annotations

import argparse
import builtins
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from unittest.mock import patch

from .systematic_records import CampaignProjection


def summarize_tests(report):
    """Keep malformed results separate from both Boolean passes and failures."""
    tests = report['tests']
    return {'strict_boolean_passed': sum(t.get('passed') is True for t in tests),
            'total': len(tests),
            'failures': [t for t in tests if t.get('passed') is False],
            'malformed_test_results': [t for t in tests if type(t.get('passed')) is not bool]}


def qualify(root: Path, full: bool):
    from loop_engine import conformance_report
    from loop_engine import _self_test
    from loop_engine.core import harness_fallback, harness_semantic, observation_expectations
    from loop_engine.code_nodes import solution_model_port
    package = Path(conformance_report.__file__).resolve().parent
    if not package.is_relative_to(root.resolve()):
        raise ValueError('qualification requires an isolated package under its owned report root')
    store = CampaignProjection(root/'qualification.duckdb')

    class DatabaseStream(io.StringIO):
        def __init__(self, path):
            super().__init__()
            self.path = Path(path)

        def __exit__(self, kind, value, tb):
            if kind is None:
                store.refresh_export(self.path, json.loads(self.getvalue()))
            self.close()
            return False

    def scoped_open(path, mode='r', *args, **kwargs):
        if str(path) == str(package/'architecture_conformance.json') and mode == 'w':
            return DatabaseStream(path)
        return builtins.open(path, mode, *args, **kwargs)

    good = True
    with patch.object(conformance_report, 'open', scoped_open, create=True):
        report = conformance_report.run_conformance()
        store.record('qualification','conformance',report)
        store.refresh_export(root/'conformance.json',report)
        print(report['human_summary'],flush=True)
        good = good and report['all_gates_pass']
        for module in (harness_fallback, harness_semantic, observation_expectations, solution_model_port):
            report = module.self_test()
            store.record('qualification',module.__name__,report)
            tests=report['tests']
            print(module.__name__,sum(t['passed'] for t in tests),len(tests),flush=True)
            good = good and all(t['passed'] for t in tests)
        if full:
            store.record('qualification','full_suite',{'status':'started'})
            print('FULL SUITE START',flush=True)
            try:
                captured=io.StringIO()
                with redirect_stdout(captured):
                    report = _self_test.self_test()
                report['captured_output_lines']=len(captured.getvalue().splitlines())
                strict = summarize_tests(report)
                report['strict_summary'] = strict
                store.record('qualification','full_suite',report)
                store.refresh_export(root/'self-test.json',report)
                print('FULL SUITE',strict['strict_boolean_passed'],strict['total'],
                      'failures=',strict['failures'], 'malformed=',strict['malformed_test_results'],
                      'missing_dependencies=',report.get('missing_dependencies'),flush=True)
                good = good and not strict['failures'] and not strict['malformed_test_results']
            except Exception as exc:
                store.record('qualification','full_suite',{'status':'interrupted_by_error',
                    'error_type':type(exc).__name__,'error':str(exc)[:800]})
                print('FULL SUITE ERROR',type(exc).__name__,str(exc)[:800],flush=True)
                good=False
    store.close()
    return good


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--full',action='store_true')
    args=parser.parse_args()
    raise SystemExit(0 if qualify(args.root,args.full) else 1)
