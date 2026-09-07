"""Offline host/verification regressions; all executed Python is authored fixture code."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import generalization_probe as probe

SOLUTIONS = (
    '''import re
def decimal_integer(digits):
    value = 0
    for character in digits:
        value = value * 10 + ord(character) - ord('0')
    return value
def to_seconds(text):
    if not isinstance(text, str) or not re.fullmatch(r'[0-9]+:[0-9]+(?::[0-9]+)?', text.strip()):
        raise ValueError('duration')
    values = [decimal_integer(part) for part in text.strip().split(':')]
    if any(value >= 60 for value in values[-2:]):
        raise ValueError('component')
    return sum(value * factor for value, factor in zip(reversed(values), (1, 60, 3600)))
''',
    '''import csv, io, re
def decimal_integer(digits):
    sign = -1 if digits.startswith('-') else 1
    value = 0
    for character in digits.lstrip('+-'):
        value = value * 10 + ord(character) - ord('0')
    return sign * value
def decimal_text(value):
    if value == 0:
        return '0'
    parts = []
    while value:
        value, part = divmod(value, 1000000000)
        parts.append(str(part).zfill(9))
    return ''.join(reversed(parts)).lstrip('0')
def summarize_sales(text):
    if not isinstance(text, str): raise ValueError('text')
    rows = csv.DictReader(io.StringIO(text))
    if not {'department', 'quantity', 'unit_price'} <= set(rows.fieldnames or []):
        raise ValueError('columns')
    groups = {}
    for row in rows:
        name, quantity, price = row['department'], row['quantity'], row['unit_price']
        if not name or not re.fullmatch(r'[+-]?[0-9]+', quantity or '') or not re.fullmatch(r'[0-9]+\\.[0-9]{2}', price or ''):
            raise ValueError('row')
        whole, fraction = price.split('.')
        cents = decimal_integer(whole) * 100 + decimal_integer(fraction)
        count, total = groups.get(name, (0, 0))
        groups[name] = count + decimal_integer(quantity), total + decimal_integer(quantity) * cents
    return [{'department': name, 'quantity': values[0],
             'total': ('-' if values[1] < 0 else '') + decimal_text(abs(values[1]) // 100) + '.' + str(abs(values[1]) % 100).zfill(2)}
            for name, values in sorted(groups.items())]
''',
    '''def schedule(tasks):
    if not isinstance(tasks, list): raise ValueError('tasks')
    entries = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {'id', 'duration', 'dependencies'}:
            raise ValueError('task')
        key, length, deps = task['id'], task['duration'], task['dependencies']
        if not isinstance(key, str) or not key or key in entries or type(length) is not int or length <= 0:
            raise ValueError('identity')
        if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps) or len(set(deps)) != len(deps):
            raise ValueError('dependencies')
        entries[key] = task
    done, active = {}, set()
    def visit(key):
        if key in done: return done[key]
        if key in active or key not in entries: raise ValueError('cycle or missing')
        active.add(key)
        start = max([visit(dep)[1] for dep in entries[key]['dependencies']], default=0)
        done[key] = [start, start + entries[key]['duration']]
        active.remove(key)
        return done[key]
    for key in entries: visit(key)
    return done
''',
    '''from html import escape
def render_schedule(schedule, title):
    if not isinstance(schedule, dict) or not isinstance(title, str): raise ValueError('input')
    for name, times in schedule.items():
        if not isinstance(name, str) or not name or not isinstance(times, list) or len(times) != 2 or any(type(x) is not int for x in times) or not 0 <= times[0] <= times[1]:
            raise ValueError('times')
    parts = ['<!DOCTYPE html><html><body><h1>' + escape(title) + '</h1>']
    for name, times in sorted(schedule.items(), key=lambda item: (item[1][0], item[0])):
        parts.append('<div data-task="' + escape(name, quote=True) + '" data-start="' + str(times[0]) + '" data-end="' + str(times[1]) + '">' + escape(name) + '</div>')
    return ''.join(parts) + '</body></html>'
''',
    '''import math
def merge_intervals(intervals):
    if not isinstance(intervals, list): raise ValueError('outer')
    for item in intervals:
        if not isinstance(item, list) or len(item) != 2 or any(type(x) not in (int, float) or (type(x) is float and not math.isfinite(x)) for x in item) or item[0] > item[1]:
            raise ValueError('interval')
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]: result[-1][1] = max(result[-1][1], end)
        else: result.append([start, end])
    return result
''',
)


def fixture_runner(workspace, image):
    from loop_engine.core.workspace_backends import CommandRequest, RestrictedLocalWorkspace, WorkspaceSpec
    backend = RestrictedLocalWorkspace(WorkspaceSpec('authored_probe_fixture', str(workspace),
        execution_enabled=True, allowed_commands=(sys.executable,)))
    result = backend.command(CommandRequest((sys.executable, '-B', 'probe.py'), execution_authorized=True,
                                            timeout_seconds=10))
    return {'ok': result.ok, 'exit_code': result.exit_code, 'stdout': result.stdout,
            'stderr': result.stderr, 'output_truncated': result.output_truncated, 'error_code': result.error_code,
            'backend': 'LOCAL_AUTHORED_FIXTURE_ONLY', 'image': image}


def services(root, host):
    from loop_engine.core.adaptive_host_runtime_checks import _services
    state, owner = _services(root / 'evidence', SimpleNamespace(binding=host))
    state.request.task = host.verifier.input_schema['properties']['task']['enum'][0]
    return state, owner


def invoke(host, state, owner, index, arguments):
    from loop_engine.core.host_runtime import HostOperationRequest, invoke_host_operation
    return invoke_host_operation(HostOperationRequest(host.operations[index].capability_ref, arguments), state, owner)


def prior_run(root, task, source, *, manifest=None, source_binding=True):
    """Author an exact local prior-run fixture, never a provider result."""
    old = task.manifest() if manifest is None else manifest
    population = probe.population_manifest((task,))
    population['tasks'] = [old]
    probe.write_json(root / 'population.json', population)
    task_root = root / task.task_id
    (task_root / 'source').mkdir(parents=True)
    (task_root / 'source/solution.py').write_text(source, encoding='utf-8')
    probe.write_json(task_root / 'frozen-task.json', old)
    value = ({'kind': 'execution_observation', 'source_digest': hashlib.sha256(source.encode()).hexdigest()}
             if source_binding else {'kind': 'unverified_partial_candidate'})
    probe.write_json(task_root / 'outcome.json', {
        'record_type': 'solve_outcome/v5', 'status': 'COMPLETED_VERIFIED',
        'run_id': 'authored-prior-fixture', 'result': {'value': value}})
    report = {'record_type': 'generalization_probe_report/v1',
              'population_digest': probe.digest(population),
              'outcomes': [{'task_id': task.task_id, 'task_digest': probe.digest(old),
                            'terminal_code': 'COMPLETED_VERIFIED', 'run_id': 'authored-prior-fixture'}]}
    probe.write_json(root / 'report.json', report)
    return root / 'report.json'


class ProbeChecks(unittest.TestCase):
    def test_followup_selection_preserves_exact_task_contracts_and_parent_failure(self):
        population = probe.task_population()
        selected = (population[0], population[3])
        with tempfile.TemporaryDirectory(prefix='probe-followup-') as directory:
            report = Path(directory) / 'report.json'
            body = {'record_type': 'generalization_probe_report/v1',
                    'population_digest': 'a' * 64,
                    'outcomes': [{'task_id': task.task_id, 'task_digest': task.content_digest,
                                  'terminal_code': 'CANCELLED'} for task in selected]}
            report.write_text(probe.canonical(body))
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                self.assertEqual(probe.main(['--task', 'schedule_html', '--task', 'duration_utility',
                    '--parent-report', str(report), '--selection-reason', 'Repair the two unverified tasks.']), 0)
            plan = json.loads(captured.getvalue())['plan']
            self.assertEqual([task['task_id'] for task in plan['tasks']],
                             ['duration_utility', 'schedule_html'])
            self.assertEqual(plan['parent_report']['sha256'], hashlib.sha256(report.read_bytes()).hexdigest())
            self.assertEqual(set(plan['parent_report']['previous_statuses'].values()), {'CANCELLED'})
            self.assertEqual(plan['selection_reason'], 'Repair the two unverified tasks.')
            self.assertEqual(sorted(Path(directory).iterdir()), [report])
            body['outcomes'][0]['task_digest'] = '0' * 64
            report.write_text(probe.canonical(body))
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                probe.main(['--task', 'duration_utility', '--parent-report', str(report)])

    def test_repeated_task_selection_is_not_silently_deduplicated(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            probe.main(['--task', 'duration_utility', '--task', 'duration_utility'])

    def test_default_plan_is_effect_free_and_no_loop_ceilings_are_invented(self):
        with patch.object(probe, 'ModelGateway', side_effect=AssertionError('provider discovery not needed')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(probe.main([]), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual((plan['model_calls'], plan['files_written']), (0, 0))
        self.assertEqual(len(plan['plan']['tasks']), 5)
        self.assertEqual(len({task['shape'] for task in plan['plan']['tasks']}), 5)
        for key in ('max_model_calls', 'max_passes', 'max_total_tokens'):
            self.assertIsNone(plan['plan']['authority'][key])

    def test_all_five_shapes_pass_same_host_operations_with_independent_verification(self):
        from loop_engine.core.host_runtime import verify_host_result
        for task, solution in zip(probe.task_population(), SOLUTIONS):
            with self.subTest(shape=task.shape), tempfile.TemporaryDirectory(prefix='probe-shape-') as directory:
                root = Path(directory)
                host = probe.make_host(root, task, runner=fixture_runner)
                state, owner = services(root, host)
                self.assertEqual(tuple(item.surface for item in host.operations), probe.OPERATIONS)
                initial = invoke(host, state, owner, 0, {})
                self.assertNotIn('cases', initial['value'])
                self.assertEqual(initial['value']['visibility']['oracle_definition'], 'host_only')
                intermediate = verify_host_result(task.prompt, initial, state, owner)
                self.assertFalse(intermediate['task_complete'])
                invoke(host, state, owner, 1, {'path': 'solution.py', 'content': solution,
                                             'expected_digest': initial['value']['digest']})
                result = invoke(host, state, owner, 2, {})
                verified = verify_host_result(task.prompt, result, state, owner)
                self.assertEqual(verified['status'], 'passed', verified)
                self.assertTrue(verified['task_complete'])
                for comparison in (result['value']['comparison'], verified['observations']):
                    self.assertTrue(all('expected' not in item and 'expected_error' not in item
                                        for item in comparison['checks']))
                execution_input = json.loads((root / 'observation-0001/probe-input.json').read_text())
                self.assertTrue(all({'case_id', 'arguments'} <= set(item)
                                    and set(item) <= {'case_id', 'arguments', 'python_constants'}
                                    for item in execution_input['cases']))
                if task.shape == 'structured_data_to_safe_document':
                    self.assertEqual(len(result['value']['artifacts']), 1)
                    self.assertFalse(Path(result['value']['artifacts'][0]['path']).is_absolute())
                    self.assertTrue((root / result['value']['artifacts'][0]['path']).is_file())
                    self.assertNotIn(str(root), json.dumps(result))

    def test_delivered_artifact_mutation_invalidates_snapshot_and_verification(self):
        from loop_engine.core.host_runtime import verify_host_result
        task = probe.task_population()[3]
        with tempfile.TemporaryDirectory(prefix='probe-artifact-') as directory:
            root = Path(directory)
            host = probe.make_host(root, task, runner=fixture_runner)
            state, owner = services(root, host)
            initial = invoke(host, state, owner, 0, {})
            invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[3],
                                         'expected_digest': initial['value']['digest']})
            result = invoke(host, state, owner, 2, {})
            artifact = root / result['value']['artifacts'][0]['path']
            original = artifact.read_bytes()
            self.assertIn(b'Review', original)
            artifact.write_bytes(original.replace(b'Review', b'Change'))
            self.assertEqual(artifact.stat().st_size, len(original))
            with self.assertRaisesRegex(ValueError, 'delivered artifact'):
                host.snapshot()
            verified = verify_host_result(task.prompt, result, state, owner)
            self.assertFalse(verified['task_complete'])
            self.assertNotEqual(verified['status'], 'passed')

    def test_usage_preserves_unknown_tokens_and_cost(self):
        outcome = SimpleNamespace(model_usage=({'input_tokens': 7, 'output_tokens': None,
            'physical_model_calls': 1, 'accounting_complete': False},),
            model_call_accounting_complete=True, model_calls=1)
        usage = probe.model_usage_summary(outcome)
        self.assertIsNone(usage['input_tokens'])
        self.assertIsNone(usage['output_tokens'])
        self.assertEqual(usage['known_input_tokens_subtotal'], 7)
        self.assertIsNone(usage['cost_usd'])

    def test_seeded_repair_failure_is_not_a_completed_task(self):
        from loop_engine.core.host_runtime import verify_host_result
        task = probe.task_population()[-1]
        with tempfile.TemporaryDirectory(prefix='probe-negative-') as directory:
            root = Path(directory)
            host = probe.make_host(root, task, runner=fixture_runner)
            state, owner = services(root, host)
            result = invoke(host, state, owner, 2, {})
            verified = verify_host_result(task.prompt, result, state, owner)
            self.assertEqual(verified['status'], 'failed')
            self.assertFalse(verified['task_complete'])
            self.assertTrue(any(not item['passed'] for item in verified['observations']['checks']))

    def test_host_schema_refuses_test_and_traversal_paths_before_mutation(self):
        for name in ('../frozen-task.json', 'probe.py', '/tmp/arbitrary.py'):
            with self.subTest(path=name), tempfile.TemporaryDirectory(prefix='probe-path-') as directory:
                root = Path(directory)
                host = probe.make_host(root, probe.task_population()[0], runner=fixture_runner)
                state, owner = services(root, host)
                before = host.snapshot()
                with self.assertRaises(ValueError):
                    invoke(host, state, owner, 1, {'path': name, 'content': 'changed', 'expected_digest': '0' * 64})
                self.assertEqual(host.snapshot(), before)

    def test_digest_semantics_are_exposed_and_new_content_hash_cannot_authorize_overwrite(self):
        from loop_engine.core.host_runtime import verify_host_result
        with tempfile.TemporaryDirectory(prefix='probe-digest-contract-') as directory:
            root = Path(directory)
            task = probe.task_population()[0]
            host = probe.make_host(root, task, runner=fixture_runner)
            state, owner = services(root, host)
            initial = invoke(host, state, owner, 0, {})
            field = host.operations[1].input_schema['properties']['expected_digest']
            self.assertIn('current source digest', field['description'])
            self.assertIn('workspace_inspect', field['description'])
            self.assertIn('not the proposed new content hash', field['description'])
            self.assertEqual(initial['value']['digest_purpose'], field['description'])
            new_digest = hashlib.sha256(SOLUTIONS[0].encode()).hexdigest()
            self.assertNotEqual(initial['value']['digest'], new_digest)
            refused = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0],
                                                    'expected_digest': new_digest})
            self.assertTrue(refused['ok'])
            self.assertFalse(refused['value']['write_applied'])
            self.assertEqual(refused['value']['error_code'], 'source_digest_mismatch')
            self.assertIn('workspace_inspect', refused['value']['reason'])
            self.assertEqual((root / 'source/solution.py').read_text(), task.initial_source)
            verification = verify_host_result(task.prompt, refused, state, owner)
            self.assertEqual(verification['status'], 'failed')
            self.assertFalse(verification['task_complete'])
            accepted = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0],
                                                     'expected_digest': initial['value']['digest']})
            self.assertTrue(accepted['ok'])
            self.assertEqual((root / 'source/solution.py').read_text(), SOLUTIONS[0])

    def test_public_host_refusal_cannot_be_self_certified_by_model(self):
        from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
        from loop_engine.core.adaptive_host_runtime_checks import _answers
        from loop_engine.core.run_history import RunHistory
        with tempfile.TemporaryDirectory(prefix='probe-public-refusal-') as directory:
            root = Path(directory)
            task = probe.task_population()[0]
            host = probe.make_host(root, task, runner=fixture_runner)
            replies = [json.loads(value) for value in _answers(SimpleNamespace(action=host.operations[1]))]
            replies[2]['arguments'] = {'path': 'solution.py', 'content': SOLUTIONS[0],
                                      'expected_digest': hashlib.sha256(SOLUTIONS[0].encode()).hexdigest()}
            self.assertEqual(replies[3]['verdict'], 'accept')
            self.assertEqual(replies[4]['route'], 'stop_success')
            outcome = probe.solve_task(probe.SolveRequest(
                probe.intake_task(probe.TaskIntakeRequest(text=task.prompt)),
                host_runtime=host, runs_dir=str(root / 'runs'), max_passes=1, quiet_model_io=True,
                model_execution=fixture_model_execution(FixtureModelExecutionRequest(
                    answers=tuple(json.dumps(value) for value in replies), max_model_calls=5))))
            self.assertFalse(outcome.solved)
            self.assertFalse(outcome.verification['passed'])
            self.assertEqual(outcome.model_calls, 5)
            report = outcome.verification['host_checks'][0]['report']
            self.assertEqual(report['status'], 'failed')
            self.assertFalse(report['task_complete'])
            self.assertEqual(report['observations']['error_code'], 'source_digest_mismatch')
            self.assertEqual((root / 'source/solution.py').read_text(), task.initial_source)
            self.assertFalse((root / 'observation-0001').exists())
            history = RunHistory.load(str(root / 'runs'), outcome.run_id)
            completions = [event.detail for event in history.event_log
                           if event.detail.get('custom_kind') == 'host_invocation_finished']
            self.assertEqual(len(completions), 2)
            self.assertTrue(all(item['outcome_known'] is True for item in completions))

    def test_stale_digest_and_changed_oracle_are_refused(self):
        with tempfile.TemporaryDirectory(prefix='probe-stale-') as directory:
            root = Path(directory)
            host = probe.make_host(root, probe.task_population()[0], runner=fixture_runner)
            state, owner = services(root, host)
            initial = invoke(host, state, owner, 0, {})
            (root / 'source/solution.py').write_text('# another writer\n')
            stale = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0],
                                                 'expected_digest': initial['value']['digest']})
            self.assertTrue(stale['ok'])  # A known precondition refusal is a completed observation.
            self.assertFalse(stale['value']['write_applied'])
            self.assertEqual(stale['value']['error_code'], 'source_digest_mismatch')
            self.assertEqual((root / 'source/solution.py').read_text(), '# another writer\n')
            (root / 'frozen-task.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'frozen task'):
                host.snapshot()

    def test_forged_duplicate_nonfinite_and_incomplete_observations_cannot_pass(self):
        task = probe.task_population()[0]
        rows = [{'case_id': case['case_id'], 'value': case['expected'], 'error': case['error'],
                 'input_unchanged': True, 'stdout': ''} for case in task.cases]
        valid = probe.canonical({'cases': rows})
        malformed = ('{"cases":[],"cases":' + probe.canonical(rows) + '}',
                     valid.replace('123', 'NaN', 1), probe.canonical({'cases': rows[:-1]}))
        for stdout in malformed:
            self.assertFalse(probe.evaluate(task, {'ok': True, 'exit_code': 0,
                                                  'output_truncated': False, 'stdout': stdout})['passed'])
        self.assertFalse(probe.evaluate(task, {'ok': True, 'exit_code': None,
                                              'output_truncated': False, 'stdout': valid})['passed'])

    def test_html_oracle_rejects_injection_and_generator_shape(self):
        expected = {'schedule': {}, 'title': 'Empty'}
        for value in ('print("<html>...</html>")',
                      '<!DOCTYPE html><html><h1>Empty</h1><script>alert(1)</script></html>',
                      '<!DOCTYPE html><html><h1>Empty</h1><style>@import "https://remote";</style></html>'):
            self.assertFalse(probe.compare_html(value, expected))

    def test_trusted_nonfinite_codec_rejects_expressions_and_unbound_paths(self):
        valid = probe.case('nonfinite', [[[None, 1.0]]], error='ValueError',
                           python_constants=({'name': 'nan', 'path': [0, 0, 0]},))
        self.assertEqual(valid['python_constants'][0]['name'], 'nan')
        for binding in ({'name': '__import__("os").getcwd()', 'path': [0, 0, 0]},
                        {'name': 'nan', 'path': [0, 0, 9]},
                        {'name': 'nan', 'path': [0, 0, False]},
                        {'name': 'nan', 'path': [0, 0, 1]},
                        {'name': 'nan', 'path': []}):
            with self.subTest(binding=binding), self.assertRaises(ValueError):
                probe.case('invalid', [[[None, 1.0]]], error='ValueError', python_constants=(binding,))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            probe.case('duplicate', [[[None, 1.0]]], error='ValueError',
                       python_constants=tuple(valid['python_constants'] * 2))

    def test_real_reference_execution_covers_precision_and_nonfinite_cases(self):
        precision_cases = {f'{kind}_{digits}_digits' for digits in (231, 517, 1021)
                           for kind in ('exact_magnitude_price', 'exact_price_cancellation', 'exact_quantity_cancellation')}
        targets = {'sales_aggregation': (1, {'exact_large_integer_cancellation', 'exact_long_decimal_price', *precision_cases}),
                   'interval_repair': (4, {'large_finite_integer_endpoints', *(
                       f'{name}_endpoint_{position}' for name in probe.PYTHON_CONSTANT_NAMES for position in (0, 1))})}
        for task in probe.task_population():
            if task.task_id not in targets:
                continue
            index, required = targets[task.task_id]
            with self.subTest(task=task.task_id), tempfile.TemporaryDirectory(prefix='probe-numeric-reference-') as directory:
                root = Path(directory)
                host = probe.make_host(root, task, runner=fixture_runner)
                state, owner = services(root, host)
                initial = invoke(host, state, owner, 0, {})
                invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[index],
                                             'expected_digest': initial['value']['digest']})
                result = invoke(host, state, owner, 2, {})
                checks = {item['case_id']: item for item in result['value']['comparison']['checks']}
                self.assertTrue(required <= set(checks))
                self.assertTrue(all(checks[key]['passed'] for key in required))
                if index == 4:
                    self.assertEqual(checks['large_finite_integer_endpoints']['observed']['value'],
                                     [[10 ** 400, 10 ** 400 + 2]])
                else:
                    self.assertEqual(checks['exact_large_integer_cancellation']['observed']['value'][0]['total'], '0.01')
                    self.assertTrue(all('failure_note' not in checks[key] for key in precision_cases))

    def test_fixed_decimal_precision_is_rejected_with_requirement_feedback(self):
        limited_source = '''import csv, io
from decimal import Decimal, localcontext
def summarize_sales(text):
    totals = {}
    with localcontext() as context:
        context.prec = 200
        for row in csv.DictReader(io.StringIO(text)):
            quantity = int(row['quantity'])
            count, total = totals.get(row['department'], (0, Decimal(0)))
            totals[row['department']] = count + quantity, total + quantity * Decimal(row['unit_price'])
        return [{'department': name, 'quantity': count, 'total': str(total.quantize(Decimal('0.01')))}
                for name, (count, total) in sorted(totals.items())]
'''
        with tempfile.TemporaryDirectory(prefix='probe-fixed-precision-') as directory:
            root = Path(directory)
            task = probe.task_population()[1]
            host = probe.make_host(root, task, runner=fixture_runner)
            state, owner = services(root, host)
            initial = invoke(host, state, owner, 0, {})
            invoke(host, state, owner, 1, {'path': 'solution.py', 'content': limited_source,
                                         'expected_digest': initial['value']['digest']})
            result = invoke(host, state, owner, 2, {})
            comparisons = result['value']['comparison']['checks']
            selected = [item for item in comparisons if item['case_id'].startswith(
                ('exact_magnitude_price_', 'exact_price_cancellation_', 'exact_quantity_cancellation_'))]
            self.assertEqual(len(selected), 9)
            self.assertTrue(all(not item['passed'] for item in selected))
            self.assertTrue(all('fixed precision cap merely moves the failure boundary' in item['failure_note']
                                for item in selected))
            self.assertTrue(all('expected' not in item and 'expected_error' not in item for item in comparisons))

    def test_zero_padded_valid_values_keep_small_exact_results_and_failure_only_feedback(self):
        cases = (
            (0, {'zero_padded_hours_5001_digits'}, SOLUTIONS[0].replace(
                '[decimal_integer(part) for part in text.strip().split(\':\')]',
                '[int(part) for part in text.strip().split(\':\')]')),
            (1, {'zero_padded_integer_quantity_5001_digits', 'zero_padded_decimal_whole_5001_digits',
                 'significant_quantity_cancellation_5001_digits'},
             SOLUTIONS[1].replace('decimal_integer(whole)', 'int(whole)').replace(
                 'decimal_integer(quantity)', 'int(quantity)')),
        )
        for index, selected, limited_source in cases:
            self.assertNotEqual(limited_source, SOLUTIONS[index])
            task = probe.task_population()[index]
            definitions = {item['case_id']: item for item in task.cases}
            self.assertTrue(selected <= set(definitions))
            for name in selected:
                self.assertLess(len(probe.canonical(definitions[name]['expected'])), 100)
                self.assertIn('no ', definitions[name]['failure_note'])
            for source, should_pass in ((limited_source, False), (SOLUTIONS[index], True)):
                with self.subTest(task=task.task_id, reference=should_pass), tempfile.TemporaryDirectory(
                        prefix='probe-zero-padding-') as directory:
                    root = Path(directory)
                    host = probe.make_host(root, task, runner=fixture_runner)
                    state, owner = services(root, host)
                    initial = invoke(host, state, owner, 0, {})
                    invoke(host, state, owner, 1, {'path': 'solution.py', 'content': source,
                                                 'expected_digest': initial['value']['digest']})
                    result = invoke(host, state, owner, 2, {})
                    checks = {item['case_id']: item for item in result['value']['comparison']['checks']}
                    for name in selected:
                        self.assertEqual(checks[name]['passed'], should_pass)
                        self.assertEqual('failure_note' in checks[name], not should_pass)
                        self.assertNotIn('expected', checks[name])
                        self.assertNotIn('expected_error', checks[name])
                        if not should_pass:
                            self.assertEqual(checks[name]['observed']['error'], 'ValueError')

    def test_significant_price_and_large_product_are_transport_safe_contract_checks(self):
        task = probe.task_population()[1]
        definitions = {item['case_id']: item for item in task.cases}
        price_case = 'significant_price_cancellation_4301_digits'
        product_case = 'large_product_decimal_formatting_2600_digits'
        expected_product = definitions[product_case]['expected'][0]
        self.assertEqual(expected_product['quantity'], 10 ** 2599 + 83)
        self.assertEqual(len(expected_product['total']), 5202)
        computed_cents = 0
        for character in expected_product['total'].replace('.', ''):
            computed_cents = computed_cents * 10 + ord(character) - ord('0')
        self.assertEqual(computed_cents, (10 ** 2599 + 83) ** 2 * 100)
        self.assertEqual(definitions[price_case]['expected'],
                         [{'department': 'A', 'quantity': 0, 'total': '0.01'}])
        stripped = SOLUTIONS[1].replace('decimal_integer(whole)', "int(whole.lstrip('0') or '0')").replace(
            'decimal_integer(quantity)', "int(quantity.lstrip('0') or '0')")
        format_limited = SOLUTIONS[1].replace('decimal_text(abs(values[1]) // 100)',
                                              'str(abs(values[1]) // 100)')
        for source, expected_checks in (
                (SOLUTIONS[1], {price_case: True, product_case: True}),
                (format_limited, {price_case: True, product_case: False}),
                (stripped, {price_case: False, product_case: True,
                    'zero_padded_integer_quantity_5001_digits': True,
                    'zero_padded_decimal_whole_5001_digits': True,
                    'significant_quantity_cancellation_5001_digits': False})):
            with self.subTest(checks=expected_checks), tempfile.TemporaryDirectory(
                    prefix='probe-numeric-boundaries-') as directory:
                root = Path(directory)
                host = probe.make_host(root, task, runner=fixture_runner)
                state, owner = services(root, host)
                initial = invoke(host, state, owner, 0, {})
                invoke(host, state, owner, 1, {'path': 'solution.py', 'content': source,
                                             'expected_digest': initial['value']['digest']})
                result = invoke(host, state, owner, 2, {})
                checks = {item['case_id']: item for item in result['value']['comparison']['checks']}
                for name, passed in expected_checks.items():
                    self.assertEqual(checks[name]['passed'], passed)
                    self.assertEqual('failure_note' in checks[name], not passed)
                    if not passed:
                        self.assertEqual(checks[name]['observed']['error'], 'ValueError')

    def test_optional_failure_note_is_generic_validated_and_failure_only(self):
        note = 'Preserve the already declared exact result requirement.'
        case = probe.case('bounded_value', [1], 2, failure_note=note)
        task = probe.ProbeTask('note_contract', 'scalar', 'Return twice the input.', 'double', '',
                              probe.canonical([case]))
        def outcome(value):
            return {'ok': True, 'exit_code': 0, 'output_truncated': False,
                    'stdout': probe.canonical({'cases': [{'case_id': case['case_id'], 'value': value,
                        'error': None, 'input_unchanged': True, 'stdout': ''}]})}
        failed = probe.feedback(probe.evaluate(task, outcome(3)))['checks'][0]
        self.assertEqual(failed['failure_note'], note)
        passed = probe.feedback(probe.evaluate(task, outcome(2)))['checks'][0]
        self.assertNotIn('failure_note', passed)
        self.assertNotIn('failure_note', probe.case('without_note', [], None))
        for invalid in ('', ' ' * 2, 7, ['text'], 'x' * 1025):
            with self.subTest(note=invalid), self.assertRaises(ValueError):
                probe.case('invalid_note', [], failure_note=invalid)
        with self.assertRaises(ValueError):
            probe.ProbeTask('invalid_note', 'scalar', 'Task', 'double', '',
                            probe.canonical([{**case, 'failure_note': None}]))

    def test_unhashable_dependency_and_large_integer_defects_are_rejected(self):
        altered = (
            (2, SOLUTIONS[2].replace(
                "any(not isinstance(dep, str) for dep in deps) or len(set(deps)) != len(deps)",
                "len(set(deps)) != len(deps) or any(not isinstance(dep, str) for dep in deps)"),
             'unhashable_list_dependency', 'TypeError'),
            (4, SOLUTIONS[4].replace("(type(x) is float and not math.isfinite(x))", "not math.isfinite(x)"),
             'large_finite_integer_endpoints', 'OverflowError'),
        )
        for index, source, failed_case, expected_error in altered:
            with self.subTest(case=failed_case), tempfile.TemporaryDirectory(prefix='probe-counterexample-') as directory:
                root = Path(directory)
                host = probe.make_host(root, probe.task_population()[index], runner=fixture_runner)
                state, owner = services(root, host)
                initial = invoke(host, state, owner, 0, {})
                invoke(host, state, owner, 1, {'path': 'solution.py', 'content': source,
                                             'expected_digest': initial['value']['digest']})
                result = invoke(host, state, owner, 2, {})
                checks = {item['case_id']: item for item in result['value']['comparison']['checks']}
                self.assertFalse(result['value']['comparison']['passed'])
                self.assertFalse(checks[failed_case]['passed'])
                self.assertEqual(checks[failed_case]['observed']['error'], expected_error)

    def test_evaluator_revision_is_explicit_and_records_exact_old_new_contracts(self):
        task = probe.task_population()[1]
        old = {**task.manifest(), 'cases': task.cases[:10], 'evaluator': 'host_fixed_comparisons/v1',
               'worker_digest': 'a' * 64}
        old.pop('argument_codec')
        with tempfile.TemporaryDirectory(prefix='probe-evaluator-revision-') as directory:
            root = Path(directory)
            report = prior_run(root, task, SOLUTIONS[1], manifest=old)
            before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in root.rglob('*') if path.is_file()}
            with self.assertRaisesRegex(ValueError, 'selected task changed'):
                probe.bind_parent_followup(report, (task,))
            with self.assertRaisesRegex(ValueError, 'rationale'):
                probe.bind_parent_followup(report, (task,), allow_evaluator_revision=True)
            metadata, seeds = probe.bind_parent_followup(report, (task,), allow_evaluator_revision=True,
                revision_reason='Add independent counterexamples to the unchanged task.')
            self.assertFalse(seeds)
            revision = metadata['evaluation_revisions'][0]
            self.assertEqual(revision['old_task_digest'], probe.digest(old))
            self.assertEqual(revision['new_task_digest'], task.content_digest)
            self.assertEqual(revision['old_evaluator_digest'], probe.evaluator_digest(old))
            self.assertEqual(revision['new_evaluator_digest'], probe.evaluator_digest(task.manifest()))
            self.assertEqual((revision['old_case_count'], revision['new_case_count']), (10, len(task.cases)))
            self.assertEqual(revision['unchanged_semantic_digest'], probe.digest(probe.task_semantics(old)))
            self.assertEqual(before, {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in root.rglob('*') if path.is_file()})

    def test_evaluator_revision_cannot_amend_prompt_entrypoint_or_editable_contract(self):
        task = probe.task_population()[1]
        changes = ({'prompt': task.prompt + ' Change the objective.'},
                   {'effective_prompt': 'different host authority'}, {'entrypoint': 'other_function'},
                   {'editable_files': ['solution.py', 'tests.py']}, {'initial_source': '# a different starting task'})
        for change in changes:
            with self.subTest(change=list(change)), tempfile.TemporaryDirectory(prefix='probe-semantics-') as directory:
                report = prior_run(Path(directory), task, SOLUTIONS[1], manifest={**task.manifest(), **change})
                with self.assertRaisesRegex(ValueError, 'cannot change'):
                    probe.bind_parent_followup(report, (task,), allow_evaluator_revision=True,
                                               revision_reason='Cases only', reuse_source=True)

    def test_cli_revision_and_reuse_require_parent_and_do_not_call_a_provider_for_plan(self):
        for arguments in (['--reuse-parent-source'], ['--allow-evaluator-revision'],
                          ['--evaluation-revision-reason', 'unbound reason']):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                probe.main(arguments)
        task = probe.task_population()[1]
        old = {**task.manifest(), 'cases': task.cases[:10]}
        with tempfile.TemporaryDirectory(prefix='probe-plan-preservation-') as directory:
            root = Path(directory)
            report = prior_run(root, task, SOLUTIONS[1], manifest=old)
            before = sorted(str(path) for path in root.rglob('*'))
            with patch.object(probe, 'ModelGateway', side_effect=AssertionError('no provider work')):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(probe.main(['--task', task.task_id, '--parent-report', str(report),
                        '--allow-evaluator-revision', '--evaluation-revision-reason', 'Audit counterexamples',
                        '--reuse-parent-source']), 0)
            plan = json.loads(output.getvalue())
            self.assertEqual((plan['model_calls'], plan['files_written']), (0, 0))
            self.assertEqual(plan['plan']['source_reuse'][task.task_id]['status'], 'UNVERIFIED')
            self.assertFalse(plan['plan']['source_reuse'][task.task_id]['acceptance_inherited'])
            self.assertEqual(before, sorted(str(path) for path in root.rglob('*')))

    def test_prior_candidate_is_snapshotted_before_working_copy_without_inherited_acceptance(self):
        from loop_engine.core.host_runtime import verify_host_result
        task = probe.task_population()[1]
        initial = 'def summarize_sales(text):\n    raise ValueError("unfinished")\n'
        with tempfile.TemporaryDirectory(prefix='probe-seed-parent-') as prior, \
                tempfile.TemporaryDirectory(prefix='probe-seed-spawned-') as current:
            prior_root, root = Path(prior), Path(current)
            report = prior_run(prior_root, task, initial)
            metadata, seeds = probe.bind_parent_followup(report, (task,), reuse_source=True)
            original_hashes = dict(metadata['file_hashes'])
            seed = seeds[task.task_id]
            host = probe.make_host(root, task, runner=fixture_runner, seed_source=seed)
            self.assertEqual((root / 'seed-source.py').read_bytes(), initial.encode())
            self.assertEqual((root / 'source/solution.py').read_bytes(), initial.encode())
            record = json.loads((root / 'seed-source.json').read_text())
            self.assertEqual(record['status'], 'UNVERIFIED')
            self.assertFalse(record['acceptance_inherited'])
            self.assertEqual(record['snapshot_digest'], seed.source_digest)
            self.assertEqual(json.loads((root / 'frozen-task.json').read_text()), task.manifest())
            self.assertEqual(task.manifest()['initial_source'], task.initial_source)
            state, owner = services(root, host)
            inspected = invoke(host, state, owner, 0, {})
            self.assertEqual(inspected['value']['seed_material']['status'], 'UNVERIFIED')
            self.assertFalse(verify_host_result(task.prompt, inspected, state, owner)['task_complete'])
            failed = invoke(host, state, owner, 2, {})
            self.assertFalse(verify_host_result(task.prompt, failed, state, owner)['task_complete'])
            invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[1],
                                         'expected_digest': inspected['value']['digest']})
            passed = invoke(host, state, owner, 2, {})
            self.assertTrue(verify_host_result(task.prompt, passed, state, owner)['task_complete'])
            self.assertEqual((root / 'seed-source.py').read_bytes(), initial.encode())
            probe.require_file_bindings(original_hashes)

    def test_changed_prior_source_or_frozen_task_is_refused_before_seed_writes(self):
        task = probe.task_population()[1]
        for changed in ('source/solution.py', 'frozen-task.json'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory(prefix='probe-seed-drift-') as directory, \
                    tempfile.TemporaryDirectory(prefix='probe-seed-drift-target-') as destination:
                root = Path(directory)
                report = prior_run(root, task, SOLUTIONS[1])
                _, seeds = probe.bind_parent_followup(report, (task,), reuse_source=True)
                (root / task.task_id / changed).write_text('changed after capture')
                with self.assertRaisesRegex(ValueError, 'changed after capture'):
                    probe.make_host(Path(destination), task, runner=fixture_runner,
                                    seed_source=seeds[task.task_id])
                self.assertEqual(list(Path(destination).iterdir()), [])

    def test_source_must_match_prior_outcome_when_an_identity_is_recorded(self):
        task = probe.task_population()[1]
        with tempfile.TemporaryDirectory(prefix='probe-prior-source-binding-') as directory:
            root = Path(directory)
            report = prior_run(root, task, SOLUTIONS[1])
            (root / task.task_id / 'source/solution.py').write_text('different = True\n')
            with self.assertRaisesRegex(ValueError, 'previous source differs'):
                probe.bind_parent_followup(report, (task,), reuse_source=True)

    def test_unbound_partial_source_stays_explicitly_unverified(self):
        task = probe.task_population()[1]
        with tempfile.TemporaryDirectory(prefix='probe-partial-seed-') as directory:
            report = prior_run(Path(directory), task, '# incomplete candidate\n', source_binding=False)
            _, seeds = probe.bind_parent_followup(report, (task,), reuse_source=True)
            record = seeds[task.task_id].record()
            self.assertEqual(record['status'], 'UNVERIFIED')
            self.assertEqual(record['provenance']['source_identity'], 'CAPTURED_UNVERIFIED_WORKING_SOURCE')

    def test_parent_population_and_frozen_record_must_match_their_digests(self):
        task = probe.task_population()[1]
        for name in ('population.json', task.task_id + '/frozen-task.json'):
            with self.subTest(file=name), tempfile.TemporaryDirectory(prefix='probe-parent-tamper-') as directory:
                root = Path(directory)
                report = prior_run(root, task, SOLUTIONS[1])
                value = json.loads((root / name).read_text())
                value['unexpected_change'] = True
                (root / name).write_text(probe.canonical(value))
                with self.assertRaises(ValueError):
                    probe.bind_parent_followup(report, (task,), reuse_source=True)

    def test_seed_symlink_and_snapshot_mutation_are_refused(self):
        task = probe.task_population()[1]
        with tempfile.TemporaryDirectory(prefix='probe-seed-link-') as directory:
            root = Path(directory)
            report = prior_run(root, task, SOLUTIONS[1])
            source = root / task.task_id / 'source/solution.py'
            original = root / 'saved-source.py'
            source.rename(original)
            source.symlink_to(original)
            with self.assertRaisesRegex(ValueError, 'ordinary file'):
                probe.bind_parent_followup(report, (task,), reuse_source=True)
        with tempfile.TemporaryDirectory(prefix='probe-seed-snapshot-parent-') as prior, \
                tempfile.TemporaryDirectory(prefix='probe-seed-snapshot-spawned-') as current:
            root = Path(current)
            report = prior_run(Path(prior), task, SOLUTIONS[1])
            _, seeds = probe.bind_parent_followup(report, (task,), reuse_source=True)
            host = probe.make_host(root, task, runner=fixture_runner, seed_source=seeds[task.task_id])
            snapshot = root / 'seed-source.py'
            snapshot.chmod(0o644)
            snapshot.write_text('# altered retained seed\n')
            with self.assertRaisesRegex(ValueError, 'changed after capture'):
                host.snapshot()


if __name__ == '__main__':
    unittest.main()
