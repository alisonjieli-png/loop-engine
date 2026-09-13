"""Probe G: a host-refused write (no effect performed) is recorded as an unknown-outcome mutating effect and blocks all later writes/runs/gates."""
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, '/home/username/loop-engine/examples/25_host_runtime')
import generalization_probe as probe
import counterexample_checks as checks
from test_generalization_probe import SOLUTIONS, fixture_runner, invoke, services
from loop_engine.core.host_runtime import verify_host_result

out = {}
task = probe.task_population()[1]  # sales_aggregation (completion policy available)
policy = checks.exact_aggregation_policy(task, checks.ExactAggregationProbeConfig(7, (2, 32)))
with tempfile.TemporaryDirectory(prefix='probe-g-') as d:
    root = Path(d)
    host = probe.make_host(root, task, runner=fixture_runner, completion_policy=policy)
    state, owner = services(root, host)
    ins = invoke(host, state, owner, 0, {})
    before_bytes = (root / 'source' / 'solution.py').read_bytes()
    # 65536 characters (passes JSON-schema maxLength) but 131072 bytes (host refuses by raising)
    oversized = 'é' * 65536
    try:
        r = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': oversized, 'expected_digest': ins['value']['digest']})
        out['oversized_replace'] = {'ok': r['ok'], 'value': r['value']}
    except Exception as e:
        out['oversized_replace'] = {'raised': type(e).__name__ + ': ' + str(e)[:120]}
    out['solution_unchanged_on_disk'] = (root / 'source' / 'solution.py').read_bytes() == before_bytes
    kinds = [(e.get('custom_kind'), e.get('mutating'), e.get('outcome_known')) for e in owner.ledger.events if e.get('custom_kind') in ('host_invocation_started', 'host_invocation_finished')]
    out['ledger_tail'] = kinds[-2:]
    for label, index, args in (
            ('subsequent_valid_replace', 1, {'path': 'solution.py', 'content': SOLUTIONS[1], 'expected_digest': ins['value']['digest']}),
            ('subsequent_run', 2, {}),
            ('subsequent_inspect_read_only', 0, {})):
        try:
            r = invoke(host, state, owner, index, args)
            out[label] = {'ok': r['ok'], 'kind': r['value'].get('kind')}
        except Exception as e:
            out[label] = {'raised': type(e).__name__ + ': ' + str(e)[:120]}
    out['note'] = 'after one host-refused oversized write the run can never write, run, or complete again; no reconciliation API exists'
    # Control: with the digest-mismatch refusal path (typed refusal dict) the run continues
with tempfile.TemporaryDirectory(prefix='probe-g2-') as d:
    root = Path(d)
    host = probe.make_host(root, task, runner=fixture_runner)
    state, owner = services(root, host)
    ins = invoke(host, state, owner, 0, {})
    r = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[1], 'expected_digest': 'a' * 64})
    out['control_digest_mismatch_refusal'] = {'ok': r['ok'], 'kind': r['value'].get('kind')}
    r = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[1], 'expected_digest': ins['value']['digest']})
    out['control_subsequent_valid_replace'] = {'ok': r['ok'], 'kind': r['value'].get('kind')}
print(json.dumps(out, indent=1, default=str))
