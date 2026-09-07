"""Offline tests for generated checks and mandatory host completion acceptance."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import counterexample_checks as checks
import generalization_probe as probe
from test_generalization_probe import SOLUTIONS, fixture_runner, invoke, services


FIXED_PRECISION = '''import csv, io
from decimal import Decimal, localcontext
def summarize_sales(text):
    totals = {}
    with localcontext() as context:
        context.prec = 100
        for row in csv.DictReader(io.StringIO(text)):
            count, total = totals.get(row['department'], (Decimal(0), Decimal(0)))
            quantity = Decimal(row['quantity'])
            totals[row['department']] = count + quantity, total + quantity * Decimal(row['unit_price'])
        return [{'department': key, 'quantity': int(value[0]), 'total': format(value[1], '.2f')}
                for key, value in sorted(totals.items())]
'''


class CounterexampleChecks(unittest.TestCase):
    def setUp(self):
        self.task = probe.task_population()[1]
        self.config = checks.ExactAggregationProbeConfig(81931, (2, 32, 256))

    def exercise(self, directory, content, *, primary_task=None):
        from loop_engine.core.host_runtime import verify_host_result
        root = Path(directory)
        task = primary_task or self.task
        policy = checks.exact_aggregation_policy(task, self.config)
        host = probe.make_host(root, task, runner=fixture_runner, completion_policy=policy)
        state, owner = services(root, host)
        observed = invoke(host, state, owner, 0, {})
        invoke(host, state, owner, 1, {'path': 'solution.py', 'content': content,
            'expected_digest': observed['value']['digest']})
        result = invoke(host, state, owner, 2, {})
        report = verify_host_result(state.request.task, result, state, owner)
        return policy, host, state, owner, result, report

    def test_generated_plan_is_reproducible_source_independent_and_scope_bound(self):
        first = checks.exact_aggregation_policy(self.task, self.config)
        second = checks.exact_aggregation_policy(self.task, self.config)
        third = checks.exact_aggregation_policy(self.task, replace(self.config, seed=81932))
        self.assertEqual(first.content_digest, second.content_digest)
        self.assertNotEqual(first.content_digest, third.content_digest)
        self.assertFalse(first.describe()['generator']['candidate_source_used_for_generation'])
        self.assertEqual(first.validate_for(self.task).cases, json.loads(first.cases_json))
        self.assertNotIn('cases', first.describe())
        with self.assertRaises(ValueError):
            first.validate_for(replace(self.task, prompt=self.task.prompt + ' Changed task.'))

    def test_corrupt_expected_answer_cannot_qualify_or_create_a_host(self):
        policy = checks.exact_aggregation_policy(self.task, self.config)
        cases = json.loads(policy.cases_json)
        cases[0]['expected'][0]['total'] = '999.00'
        corrupted = replace(policy, cases_json=probe.canonical(cases))
        with tempfile.TemporaryDirectory(prefix='wrong-completion-oracle-') as directory:
            with self.assertRaises(ValueError):
                probe.make_host(directory, self.task, completion_policy=corrupted)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_disagreeing_oracle_is_not_hidden_by_proposed_success(self):
        with patch.object(checks, 'decimal_oracle', return_value=[]), self.assertRaises(ValueError):
            checks.exact_aggregation_policy(self.task, self.config)

    def test_reference_passes_required_extra_gates_and_reuses_exact_receipt(self):
        from loop_engine.core.host_runtime import verify_host_result
        with tempfile.TemporaryDirectory(prefix='completion-reference-') as directory:
            policy, host, state, owner, result, report = self.exercise(directory, SOLUTIONS[1])
            self.assertEqual(report['status'], 'passed', report)
            self.assertTrue(report['task_complete'])
            extra = report['completion_checks'][0]['observations']
            self.assertEqual(extra['case_count'], 9)
            self.assertEqual(extra['passed_cases'], 9)
            before = sorted(path.name for path in Path(directory).glob('completion-*.json'))
            again = verify_host_result(state.request.task, result, state, owner)
            self.assertTrue(again['task_complete'])
            self.assertEqual(again['completion_checks'][0]['observations']['receipt_digest'], extra['receipt_digest'])
            self.assertEqual(before, sorted(path.name for path in Path(directory).glob('completion-*.json')))
            visible = probe.canonical(extra)
            self.assertNotIn('"expected"', visible)
            self.assertNotIn('"arguments"', visible)

    def test_primary_pass_cannot_hide_fixed_precision_counterexample(self):
        from loop_engine.core.adaptive_host_verification import require_host_checks
        from loop_engine.loop.kernel import ResultPacket
        small = replace(self.task, cases_json=probe.canonical(self.task.cases[:3]))
        with tempfile.TemporaryDirectory(prefix='completion-reject-fixed-cap-') as directory:
            _, _, state, owner, result, report = self.exercise(directory, FIXED_PRECISION, primary_task=small)
            self.assertTrue(result['value']['comparison']['passed'])
            self.assertEqual(report['status'], 'failed')
            self.assertFalse(report['task_complete'])
            extra = report['completion_checks'][0]['observations']
            self.assertLess(extra['passed_cases'], extra['case_count'])
            self.assertTrue(any(item['passed'] is False for item in extra['checks']))
            with self.assertRaises(ValueError):
                require_host_checks({'evaluation': {'best_index': 0},
                    'host_checks': [{'result_index': 0, 'report': report}]},
                    (ResultPacket('candidate', result=result),), state, owner, task_complete=True)

    def test_frozen_policy_and_receipts_cannot_be_rewritten(self):
        from loop_engine.core.host_runtime import verify_host_result
        with tempfile.TemporaryDirectory(prefix='completion-drift-') as directory:
            _, host, state, owner, result, report = self.exercise(directory, SOLUTIONS[1])
            record = Path(directory) / report['completion_checks'][0]['observations']['receipt_ref']
            self.assertFalse(Path(report['completion_checks'][0]['observations']['receipt_ref']).is_absolute())
            record.write_text('{}')
            failed = verify_host_result(state.request.task, result, state, owner)
            self.assertEqual(failed['status'], 'unavailable')
            self.assertFalse(failed['task_complete'])
            policy_file = Path(directory) / 'completion-policy.json'
            policy_file.chmod(0o600)
            policy_file.write_text('{}')
            with self.assertRaises(ValueError):
                host.snapshot()

    def test_changed_task_cannot_borrow_correct_results(self):
        from loop_engine.core.host_runtime import verify_host_result
        with tempfile.TemporaryDirectory(prefix='completion-other-task-') as directory:
            _, _, state, owner, result, report = self.exercise(directory, SOLUTIONS[1])
            self.assertTrue(report['task_complete'])
            different = verify_host_result('Solve an unrelated task.', result, state, owner)
            self.assertEqual(different['status'], 'unavailable')
            self.assertFalse(different['task_complete'])


if __name__ == '__main__':
    unittest.main()
