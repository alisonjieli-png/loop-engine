"""Offline tests for the version 2 novel-task campaign variation.

No model call, no Docker. Candidate code in these tests is fixture code the
test wrote itself, executed through the probe WORKER by a host-Python runner.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generalization_probe as probe
import novel_task_audit_v2 as audit
import novel_task_campaign_v2 as campaign
import novel_task_offline_check_v2 as offline
from novel_task_population_v2 import POPULATION_RECORD_TYPE, task_population

RIGHT_SPIRAL = '''def spiral_weighted_sum(matrix):
    if not isinstance(matrix, list):
        raise ValueError
    if not matrix:
        return 0
    if any(not isinstance(row, list) for row in matrix):
        raise ValueError
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError
    for row in matrix:
        for value in row:
            if type(value) is not int:
                raise ValueError
    order = []
    top, bottom, left, right = 0, len(matrix) - 1, 0, width - 1
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            order.append(matrix[top][c])
        for r in range(top + 1, bottom + 1):
            order.append(matrix[r][right])
        if top < bottom:
            for c in range(right - 1, left - 1, -1):
                order.append(matrix[bottom][c])
        if left < right:
            for r in range(bottom - 1, top, -1):
                order.append(matrix[r][left])
        top, bottom, left, right = top + 1, bottom - 1, left + 1, right - 1
    return sum(v * i for i, v in enumerate(order, start=1))
'''


def campaign_fixture(root, task, source, *, solved=True, digest_override=None):
    """A minimal accepted-task work root as the campaign writes it."""
    task_root = root / task.task_id
    (task_root / 'source').mkdir(parents=True)
    (task_root / 'source' / 'solution.py').write_text(source, encoding='utf-8')
    import hashlib
    source_digest = digest_override or hashlib.sha256(source.encode('utf-8')).hexdigest()
    probe.write_json(task_root / 'frozen-task.json', task.manifest())
    probe.write_json(task_root / 'observation-0001.json', {'record_type': 'fixture', 'passed': solved})
    probe.write_json(task_root / 'outcome.json', {
        'status': 'COMPLETED_VERIFIED' if solved else 'FAILED', 'solved': solved,
        'result': {'value': {'kind': 'execution_observation', 'source_digest': source_digest}},
        'intelligence': {'region_evidence': {'region_ref': 'region.fixture', 'advisory': True,
                                             'region_statistics': {'runs': 1}}}})
    return task_root


class PopulationChecks(unittest.TestCase):
    def test_population_names_its_entrypoints_and_record_type(self):
        population = task_population()
        self.assertEqual(len(population), 10)
        for task in population:
            self.assertIn(f'Implement {task.entrypoint}(', task.prompt)
            self.assertGreaterEqual(sum(1 for item in task.cases if item['error'] is None), 2)
            self.assertGreaterEqual(sum(1 for item in task.cases if item['error'] == 'ValueError'), 1)
        self.assertEqual(POPULATION_RECORD_TYPE, 'novel_task_campaign_population/v2')

    def test_offline_check_passes_and_every_control_fails_its_wrong_solution(self):
        results = offline.check_population(runner=offline.host_python_runner)
        self.assertTrue(results['passed'], results)
        self.assertEqual(results['reference_mismatches'], [])
        self.assertEqual(results['evaluator_control_failures'], [])
        self.assertEqual(results['cases_checked'], sum(len(task.cases) for task in task_population()))

    def test_spiral_evaluator_distinguishes_a_plain_sum_from_a_spiral_walk(self):
        task = next(item for item in task_population() if item.task_id == 'matrix_spiral')
        right = offline.evaluate_solution(task, RIGHT_SPIRAL)
        wrong = offline.evaluate_solution(task, offline.WRONG_SOLUTIONS['matrix_spiral'])
        self.assertTrue(right['passed'], [c['case_id'] for c in right['checks'] if not c['passed']])
        self.assertFalse(wrong['passed'])

    def test_non_ascii_code_point_is_a_real_code_point(self):
        task = next(item for item in task_population() if item.task_id == 'poly_hash')
        argument = next(item for item in task.cases if item['case_id'] == 'non_ascii_code_point')['arguments'][0]
        self.assertEqual(len(argument), 1)
        self.assertEqual(ord(argument), 233)


class CampaignRunnerChecks(unittest.TestCase):
    def run_plan(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = campaign.main(argv)
        return code, json.loads(buffer.getvalue())

    def test_plan_mode_prints_provenance_and_learning_flags_without_writes(self):
        with tempfile.TemporaryDirectory(prefix='novel-v2-plan-') as directory:
            code, plan = self.run_plan(['--shared-runs-dir', '--passes', '2',
                                        '--evidence-out', str(Path(directory) / 'evidence')])
            self.assertEqual(code, 0)
            self.assertEqual(plan['model_calls'], 0)
            self.assertEqual(plan['files_written'], 0)
            self.assertEqual(set(plan['plan']['module_digests']), {'runner', 'population', 'offline_check', 'probe'})
            self.assertTrue(all(len(value) == 64 for value in plan['plan']['module_digests'].values()))
            self.assertEqual(plan['plan']['learning']['shared_runs_dir'], True)
            self.assertEqual(plan['plan']['learning']['passes'], 2)
            self.assertEqual(plan['plan']['record_type'], POPULATION_RECORD_TYPE)
            self.assertEqual(sorted(Path(directory).iterdir()), [])
        code, default_plan = self.run_plan([])
        self.assertEqual(default_plan['plan']['learning'], {
            'shared_runs_dir': False, 'passes': 1, 'evidence_out': None,
            'region_evidence_source': 'outcome.intelligence.region_evidence'})

    def test_changed_frozen_source_refuses_dispatch(self):
        expected = campaign.module_digests()
        campaign.require_module_digests(expected)
        changed = dict(expected, population='0' * 64)
        with self.assertRaisesRegex(ValueError, 'population'):
            campaign.require_module_digests(changed)

    def test_report_groups_per_pass_and_names_unstarted_work(self):
        tasks = task_population()[:2]
        manifest = campaign.campaign_manifest(tasks, model_route='cloud.default', model_id='m',
                                              shared_runs_dir=True, passes=2)

        def entry(pass_index, task, calls, solved=True):
            return {'pass_index': pass_index, 'task_id': task.task_id, 'terminal_code': 'COMPLETED_VERIFIED',
                    'solved': solved, 'model_calls': calls, 'model_calls_known_subtotal': calls,
                    'model_call_accounting_complete': True, 'observations': 1, 'elapsed_seconds': 1.0,
                    'region_evidence': {'region_ref': 'region.x'},
                    'model_usage': {'token_accounting_complete': True, 'known_input_tokens_subtotal': 10 * calls,
                                    'known_output_tokens_subtotal': calls}}

        outcomes = [entry(1, tasks[0], 20), entry(1, tasks[1], 15), entry(2, tasks[0], 12)]
        report = campaign.campaign_report(manifest, tasks, outcomes, 2)
        self.assertEqual(report['record_type'], 'novel_task_campaign_report/v2')
        self.assertEqual(report['selected'], 4)
        self.assertEqual(report['attempted'], 3)
        self.assertEqual(report['not_started'], ['pass-02/' + tasks[1].task_id])
        self.assertEqual([item['model_calls'] for item in report['per_pass']], [35, 12])
        self.assertEqual(report['per_pass'][1]['per_task'][0]['region_evidence'], {'region_ref': 'region.x'})
        self.assertEqual(report['model_calls'], 47)
        self.assertEqual(report['input_tokens'], 470)

    def test_evidence_copy_takes_the_durable_subset(self):
        task = task_population()[0]
        with tempfile.TemporaryDirectory(prefix='novel-v2-evidence-') as directory:
            root = Path(directory)
            task_root = campaign_fixture(root / 'work', task, 'def path_cost(text):\n    return 0\n')
            (task_root / 'runs').mkdir()
            (task_root / 'runs' / 'stages.jsonl').write_text('{}\n')
            copied = campaign.copy_evidence(task_root, root / 'evidence' / 'pass-01' / task.task_id)
            self.assertEqual(sorted(copied), ['frozen-task.json', 'observation-0001.json', 'outcome.json',
                                              'source/solution.py'])
            self.assertFalse((root / 'evidence' / 'pass-01' / task.task_id / 'runs').exists())
            with self.assertRaises(FileExistsError):
                campaign.copy_evidence(task_root, root / 'evidence' / 'pass-01' / task.task_id)

    def test_region_summary_is_bounded(self):
        small = campaign.region_summary({'intelligence': {'region_evidence': {
            'region_ref': 'region.a', 'advisory': True, 'region_statistics': {'runs': 3}}}})
        self.assertEqual(small, {'region_ref': 'region.a', 'advisory': True, 'region_statistics': {'runs': 3}})
        large = campaign.region_summary({'intelligence': {'region_evidence': {
            'region_ref': 'region.b', 'advisory': True, 'region_statistics': {'blob': 'x' * 5000}}}})
        self.assertEqual(large['region_ref'], 'region.b')
        self.assertIn('region_evidence_digest', large)
        self.assertNotIn('region_statistics', large)


class AuditChecks(unittest.TestCase):
    def test_audit_passes_a_right_solution_and_invalidates_a_wrong_one(self):
        task = next(item for item in task_population() if item.task_id == 'matrix_spiral')
        with tempfile.TemporaryDirectory(prefix='novel-v2-audit-') as directory:
            root = Path(directory)
            campaign_fixture(root / 'right', task, RIGHT_SPIRAL)
            campaign_fixture(root / 'wrong', task, offline.WRONG_SOLUTIONS['matrix_spiral'])
            right = audit.audit_campaign(root / 'right', count=24, runner=offline.host_python_runner,
                                         scratch=root / 'scratch-right')
            wrong = audit.audit_campaign(root / 'wrong', count=24, runner=offline.host_python_runner,
                                         scratch=root / 'scratch-wrong')
        self.assertEqual(right['tasks_audited'], 1)
        self.assertEqual(right['tasks_invalidated'], 0, right['results'][0].get('failures'))
        self.assertEqual(wrong['tasks_invalidated'], 1)
        self.assertTrue(wrong['results'][0]['failures'])
        self.assertGreater(right['results'][0]['invalid_inputs'], 0)
        self.assertEqual(right['record_type'], 'novel_task_campaign_audit/v2')

    def test_audit_refuses_a_source_that_is_not_the_accepted_one(self):
        task = next(item for item in task_population() if item.task_id == 'matrix_spiral')
        with tempfile.TemporaryDirectory(prefix='novel-v2-audit-drift-') as directory:
            root = Path(directory)
            campaign_fixture(root / 'drift', task, RIGHT_SPIRAL, digest_override='0' * 64)
            campaign_fixture(root / 'unsolved', task, RIGHT_SPIRAL, solved=False)
            drift = audit.audit_campaign(root / 'drift', count=5, runner=offline.host_python_runner,
                                         scratch=root / 'scratch-drift')
            unsolved = audit.audit_campaign(root / 'unsolved', count=5, runner=offline.host_python_runner,
                                            scratch=root / 'scratch-unsolved')
        self.assertIn('accepted source digest', drift['results'][0]['refused'])
        self.assertIn('did not accept', unsolved['results'][0]['refused'])
        self.assertEqual(drift['tasks_invalidated'], 1)

    def test_audit_finds_tasks_under_pass_directories(self):
        task = next(item for item in task_population() if item.task_id == 'matrix_spiral')
        with tempfile.TemporaryDirectory(prefix='novel-v2-audit-passes-') as directory:
            root = Path(directory)
            campaign_fixture(root / 'pass-01', task, RIGHT_SPIRAL)
            campaign_fixture(root / 'pass-02', task, RIGHT_SPIRAL)
            found = audit.task_roots(root)
            self.assertEqual([name for name, _ in found], ['pass-01', 'pass-02'])


if __name__ == '__main__':
    unittest.main()
