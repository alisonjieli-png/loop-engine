"""Probe C: does anything model-visible carry expected answers, expected_error, passing-case failure notes, or host-only case arguments?"""
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, '/home/username/loop-engine/examples/25_host_runtime')
import generalization_probe as probe
import counterexample_checks as checks
from test_generalization_probe import SOLUTIONS, fixture_runner, invoke, services
from test_counterexample_checks import FIXED_PRECISION
from loop_engine.core.host_runtime import verify_host_result
from loop_engine.core.adaptive_practitioner_verification import safe_result
from loop_engine.loop.kernel import ResultPacket

def walk(value, path=''):
    if isinstance(value, dict):
        for k, v in value.items():
            yield path + '/' + k, k, v
            yield from walk(v, path + '/' + k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, path + '[%d]' % i)

out = {}
for label, task, solution, policy in (
        ('sales_partial_with_completion', probe.task_population()[1], FIXED_PRECISION, 'policy'),
        ('duration_reference', probe.task_population()[0], SOLUTIONS[0], None),
        ('schedule_html_reference', probe.task_population()[3], SOLUTIONS[3], None)):
    if policy:
        policy = checks.exact_aggregation_policy(task, checks.ExactAggregationProbeConfig(81931, (2, 32, 256)))
    with tempfile.TemporaryDirectory(prefix='probe-c-') as d:
        root = Path(d)
        host = probe.make_host(root, task, runner=fixture_runner, completion_policy=policy)
        state, owner = services(root, host)
        ins = invoke(host, state, owner, 0, {})
        rep = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': solution, 'expected_digest': ins['value']['digest']})
        run = invoke(host, state, owner, 2, {})
        report = verify_host_result(state.request.task, run, state, owner)
        visible = {'inspect': ins, 'replace': rep, 'run': run, 'report': report,
                   'safe_results': [safe_result(ResultPacket('x', result=r))['result'] for r in (ins, rep, run)],
                   'manifest': host.summary(), 'descriptors': list(host.descriptors())}
        text = probe.canonical(visible)
        findings = {}
        findings['keys_expected_or_expected_error'] = [p for p, k, _ in walk(visible) if k in ('expected', 'expected_error')]
        findings['failure_note_on_passing_check'] = [p for p, k, v in walk(visible) if k == 'failure_note' and False]
        for p, k, v in walk(visible):
            if isinstance(v, dict) and 'case_id' in v and 'passed' in v and 'failure_note' in v and v['passed'] is True:
                findings['failure_note_on_passing_check'].append(p)
        findings['arguments_key_inside_observations'] = [p for p, k, _ in walk(visible) if k == 'arguments' and ('observ' in p or 'comparison' in p or 'checks' in p)]
        leaked_args = []
        for case in task.cases:
            for arg in case['arguments']:
                if isinstance(arg, str) and len(arg) >= 12 and probe.canonical(arg)[1:-1] in text:
                    leaked_args.append(case['case_id'])
            if probe.canonical(case['arguments']) in text:
                leaked_args.append(case['case_id'] + ':full_args')
        findings['case_arguments_in_visible_text'] = sorted(set(leaked_args))
        failing = {c['case_id'] for c in run['value']['comparison']['checks'] if not c['passed']}
        leaked_expected = [c['case_id'] for c in task.cases if c['case_id'] in failing and c['expected'] is not None
                           and probe.canonical(c['expected']) in text]
        findings['expected_values_of_failing_cases_in_visible_text'] = leaked_expected
        if policy:
            gen_cases = json.loads(policy.cases_json)
            findings['generated_expected_values_in_visible_text'] = [c['case_id'] for c in gen_cases if probe.canonical(c['expected']) in text]
            findings['generated_arguments_in_visible_text'] = [c['case_id'] for c in gen_cases if probe.canonical(c['arguments'][0])[1:-1] in text]
        findings['host_absolute_root_path_in_visible_text'] = str(root) in text
        findings['paths_carrying_host_root'] = sorted({p for p, k, v in walk(visible) if isinstance(v, str) and str(root) in v})[:8]
        findings['primary_passed'] = run['value']['comparison']['passed']
        findings['report'] = (report['status'], report['task_complete'])
        findings['failing_case_ids_shown_to_model'] = sorted(failing)[:6]
        findings['visible_bytes'] = len(text)
        out[label] = findings
print(json.dumps(out, indent=1))
