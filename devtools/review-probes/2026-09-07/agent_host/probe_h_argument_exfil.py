"""Probe H (informational): are host-only case arguments ('probe_arguments': 'tool_only') exfiltratable through observed values?"""
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, '/home/username/loop-engine/examples/25_host_runtime')
import generalization_probe as probe
from test_generalization_probe import fixture_runner, invoke, services
EXFIL = '''import json
def to_seconds(text):
    return json.loads(open('probe-input.json').read())
'''
task = probe.task_population()[0]
with tempfile.TemporaryDirectory(prefix='probe-h-') as d:
    root = Path(d)
    host = probe.make_host(root, task, runner=fixture_runner)
    state, owner = services(root, host)
    ins = invoke(host, state, owner, 0, {})
    print('inspect.visibility =', json.dumps(ins['value']['visibility']))
    invoke(host, state, owner, 1, {'path': 'solution.py', 'content': EXFIL, 'expected_digest': ins['value']['digest']})
    run = invoke(host, state, owner, 2, {})
    text = probe.canonical(run)
    args_seen = [c['case_id'] for c in task.cases if probe.canonical(c['arguments']) in text]
    print('primary passed:', run['value']['comparison']['passed'], '| model-visible result bytes:', len(text))
    print('case arguments of ALL cases present in model-visible run record:', len(args_seen), 'of', len(task.cases), args_seen[:4], '...')
    print('largest observed value bytes:', max(len(probe.canonical(c['observed']['value'])) for c in run['value']['comparison']['checks']))
    print('expected key present anywhere:', '"expected"' in text)
