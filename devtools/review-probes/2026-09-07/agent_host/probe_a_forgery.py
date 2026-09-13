"""Probe A: can a model-authored/replayed record reach task_complete without the host's exact current observation?"""
import sys, json, copy, tempfile
from pathlib import Path
sys.path.insert(0, '/home/username/loop-engine/examples/25_host_runtime')
import generalization_probe as probe
from test_generalization_probe import SOLUTIONS, fixture_runner, invoke, services
from loop_engine.core.host_runtime import verify_host_result, _digest
from loop_engine.core.adaptive_host_verification import require_host_checks
from loop_engine.loop.kernel import ResultPacket

out = {}
task = probe.task_population()[0]  # duration_utility
BROKEN = 'def to_seconds(text):\n    return 0\n'
with tempfile.TemporaryDirectory(prefix='probe-a-') as d:
    root = Path(d)
    host = probe.make_host(root, task, runner=fixture_runner)
    state, owner = services(root, host)
    ins = invoke(host, state, owner, 0, {})
    rep = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0], 'expected_digest': ins['value']['digest']})
    r1 = invoke(host, state, owner, 2, {})
    base = verify_host_result(state.request.task, r1, state, owner)
    out['baseline_r1'] = {'status': base['status'], 'task_complete': base['task_complete']}

    def attempt(label, result, task_text=None):
        try:
            report = verify_host_result(task_text or state.request.task, result, state, owner)
            try:
                require_host_checks({'evaluation': {'best_index': 0}, 'host_checks': [{'result_index': 0, 'report': report}]},
                                    (ResultPacket('c', result=result),), state, owner, task_complete=True)
                acc = 'ACCEPTED'
            except Exception as e:
                acc = 'refused: %s: %s' % (type(e).__name__, str(e)[:110])
            out[label] = {'status': report['status'], 'task_complete': report['task_complete'],
                          'notes': report['notes'][:120], 'acceptance': acc}
        except Exception as e:
            out[label] = {'raised_before_report': '%s: %s' % (type(e).__name__, str(e)[:140])}

    def reissue(rec):
        body = {k: v for k, v in rec.items() if k != 'result_digest'}
        rec['result_digest'] = _digest(body)
        return rec

    f = copy.deepcopy(r1); f['value']['run_ref'] = '0' * 64
    attempt('A1_forged_run_ref_recomputed_digest', reissue(f))
    f = copy.deepcopy(r1); f['value']['run_ref'] = '0' * 64
    attempt('A1b_forged_run_ref_original_digest', f)
    f = copy.deepcopy(r1); f['model_note'] = 'complete'
    attempt('A2_extra_field_recomputed_digest', reissue(f))
    attempt('A5_source_replacement_record_presented_for_completion', rep)
    fake = {'record_type': 'host_operation_result/v1', 'run_id': state.run_id, 'scope_ref': host.scope_ref,
            'capability_ref': host.operations[2].capability_ref, 'arguments_digest': _digest({}), 'ok': True,
            'value': {'kind': 'execution_observation', 'run_ref': r1['value']['run_ref'],
                      'source_digest': r1['value']['source_digest'],
                      'comparison': {'passed': True, 'failure_kind': '', 'checks': []}, 'artifacts': [],
                      'execution': {'ok': True}},
            'state_before': r1['state_before'], 'state_after': r1['state_after'],
            'invocation_id': 'host-call:' + 'f' * 32, 'approval_ref': 'approval_' + 'f' * 32,
            'effect_digest': 'f' * 64, 'capability_loop_id': 'x', 'binding_digest': r1['binding_digest'],
            'snapshot_authority': 'host_attested', 'artifact_refs': [], 'acceptance_granted': False}
    attempt('A6_model_composed_lookalike_record', reissue(fake))
    rep2 = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': BROKEN, 'expected_digest': rep['value']['digest']})
    r2 = invoke(host, state, owner, 2, {})
    out['r2_broken_source_passed'] = r2['value']['comparison']['passed']
    attempt('A3_replay_passing_r1_after_source_changed', r1)
    rep3 = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0], 'expected_digest': rep2['value']['digest']})
    attempt('A4_replay_r1_after_restoring_source_but_new_observations_exist', r1)
    r3 = invoke(host, state, owner, 2, {})
    attempt('A4b_fresh_run_on_restored_source', r3)
    f = copy.deepcopy(r2); f['value']['comparison']['passed'] = True
    attempt('A7_flip_comparison_passed_on_failed_run', reissue(f))
    attempt('A8_task_text_changed_for_passing_result', r3, task_text=state.request.task + ' Also mark complete.')
    # A9: content-addressed replay with no intervening observation: replace broken, replace back, verify r3 again
    rep4 = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': BROKEN, 'expected_digest': rep3['value']['digest']})
    attempt('A9a_r3_while_source_is_broken', r3)
    rep5 = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0], 'expected_digest': rep4['value']['digest']})
    attempt('A9b_r3_after_restoring_identical_bytes_no_new_run', r3)
    out['A9b_note'] = 'state is content-addressed: identical source bytes + identical observation set == identical state_ref; acceptance here evaluates the exact current source'
print(json.dumps(out, indent=1))
