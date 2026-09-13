"""Probe D: approval binding to the exact effect, stale/edited decisions, and model reach of verifier endpoints."""
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, '/home/username/loop-engine/examples/25_host_runtime')
import generalization_probe as probe
from test_generalization_probe import SOLUTIONS, fixture_runner, invoke, services
from loop_engine.core import host_runtime as hr
from loop_engine.core.adaptive_host_runtime_checks import _fixture, _services
from loop_engine.core.host_completion_checks import _add
from loop_engine.loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec

out = {}
# D1: what the host's authorize() sees, on the real generalization host
seen = []
task = probe.task_population()[0]
with tempfile.TemporaryDirectory(prefix='probe-d-') as d:
    root = Path(d)
    host = probe.make_host(root, task, runner=fixture_runner)
    from dataclasses import replace as dc_replace
    original = host.authorize
    def recording_authorize(request):
        seen.append(request); return original(request)
    host = dc_replace(host, authorize=recording_authorize)
    state, owner = services(root, host)
    ins = invoke(host, state, owner, 0, {})
    rep = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0], 'expected_digest': ins['value']['digest']})
    rep_b = invoke(host, state, owner, 1, {'path': 'solution.py', 'content': SOLUTIONS[0] + '\n', 'expected_digest': rep['value']['digest']})
    out['D1_effects_presented_to_authorize'] = [{'operation': r.effect.operation, 'effect_class': r.effect.effect_class.value, 'target': r.effect.target[:40],
        'parameter_keys': sorted(dict(r.effect.parameters)), 'state': dict(r.effect.parameters)['state'][:10],
        'host_invocation_digest': dict(r.effect.parameters)['host_invocation_digest'][:10], 'request_id': r.request_id[:14]} for r in seen]
    out['D1_all_request_ids_and_invocation_digests_distinct'] = (len({r.request_id for r in seen}) == len(seen)
        and len({dict(r.effect.parameters)['host_invocation_digest'] for r in seen}) == len(seen))
    # direct call of verifier through the model-facing entry point
    for label, ref in (('D4_verifier_direct', host.verifier.capability_ref), ('D4b_unknown_ref', 'host:workspace_completion:invoke')):
        try:
            hr.invoke_host_operation(hr.HostOperationRequest(ref, {'task': state.request.task, 'result': rep, 'state_ref': rep['state_after']}), state, owner)
            out[label] = 'INVOKED'
        except Exception as e:
            out[label] = 'refused:%s:%s' % (type(e).__name__, str(e)[:90])
    from loop_engine.loop.runtime_context import LoopRuntimeContext
    out['D7_plugin_port_lists'] = list(owner.runtime_context.custom_plugins.capabilities) if getattr(owner, 'runtime_context', None) else 'n/a'
    out['D7_supports'] = {ref: host.supports(ref) for ref in (host.operations[0].capability_ref, host.verifier.capability_ref)}

# D2/D3: stale or edited decisions on the fixture host
for label, mode in (('D2_stale_request_id_decision', 'stale'), ('D3_edit_decision', 'edit'), ('D3b_wrong_action_reject_object', 'reject')):
    box = {'previous': None}
    def hook(request, state, mode=mode, box=box):
        pass
    fx = _fixture()
    with tempfile.TemporaryDirectory(prefix='probe-d2-') as d:
        svc, owner = _services(d, fx)
        first = hr.invoke_host_operation(hr.HostOperationRequest(fx.action.capability_ref, {}), svc, owner)
        prev_id = fx.approvals[-1].request_id
        def authorize(request, mode=mode, prev_id=prev_id):
            fx.approvals.append(request)
            if mode == 'stale':
                return ApprovalDecision.approve(prev_id, 'fixture_host_authority')
            if mode == 'edit':
                return ApprovalDecision.edit(request.request_id, 'fixture_host_authority', EffectSpec(EffectClass.LOCAL_READ, 'read_fixture_state', request.effect.target))
            return ApprovalDecision.reject(request.request_id, 'fixture_host_authority', reason='probe refusal')
        from dataclasses import replace
        fx.binding = replace(fx.binding, authorize=authorize)
        svc.dependencies.host_runtime = fx.binding
        calls_before = len(fx.calls)
        try:
            hr.invoke_host_operation(hr.HostOperationRequest(fx.action.capability_ref, {}), svc, owner)
            res = 'INVOKED'
        except Exception as e:
            res = 'refused:%s:%s' % (type(e).__name__, str(e)[:80])
        started = [e for e in owner.ledger.events if e.get('custom_kind') == 'host_invocation_started']
        out[label] = {'result': res, 'host_callback_ran': len(fx.calls) > calls_before, 'invocation_started_events': len(started)}

# D4c: completion verifier direct call on the completion fixture
fx = _add(_fixture(), ({'passed': True, 'task_complete': True, 'observations': {}, 'notes': 'x'},))
with tempfile.TemporaryDirectory(prefix='probe-d4-') as d:
    svc, owner = _services(d, fx)
    ref = fx.binding.completion_verifiers[0].capability_ref
    try:
        hr.invoke_host_operation(hr.HostOperationRequest(ref, {}), svc, owner); out['D4c_completion_gate_direct'] = 'INVOKED'
    except Exception as e:
        out['D4c_completion_gate_direct'] = 'refused:%s:%s' % (type(e).__name__, str(e)[:80])
    # D5: through the real adaptive dispatch
    try:
        from loop_engine.core.adaptive_practitioner_capabilities import AdaptiveCapabilityExecutionRequest, execute_adaptive_capability
        from loop_engine.loop.kernel import ExecutionPlan, PractitionerState, ProblemSpec
        plan = ExecutionPlan('generate', 'run_dag', handle=ref, experiment={'arguments': {}}, rationale='model wants the gate')
        packet = execute_adaptive_capability(AdaptiveCapabilityExecutionRequest(PractitionerState(ProblemSpec('t')), plan, owner), svc)
        out['D5_adaptive_dispatch_to_gate'] = {'errors': list(packet.errors), 'result': packet.result, 'gate_callback_ran': any(k.startswith('fixture_completion') for k, _ in fx.calls)}
    except Exception as e:
        out['D5_adaptive_dispatch_to_gate'] = 'exception:%s:%s' % (type(e).__name__, str(e)[:120])
print(json.dumps(out, indent=1, default=str))
