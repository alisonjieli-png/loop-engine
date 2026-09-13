"""Probe B: completion gate sequencing, malformed gate replies, and state drift between primary verify and gate."""
import json, tempfile, hashlib, copy
from types import SimpleNamespace
from loop_engine.core import host_runtime as hr
from loop_engine.core.adaptive_host_runtime_checks import _services
from loop_engine.core.adaptive_host_verification import require_host_checks
from loop_engine.loop.kernel import ResultPacket
from loop_engine.loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec
from loop_engine.core.capability_directory import CapabilityDirectory, CapabilityHandshake, Endpoint

def build(gates, *, snapshot_hook=None, gate_effect_hooks=None):
    state = {'revision': 1, 'answer': 42}
    calls, approvals, snaps = [], [], []
    def snapshot():
        snaps.append(len(snaps) + 1)
        if snapshot_hook:
            snapshot_hook(len(snaps), state, calls)
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    def operation(*, request):
        calls.append(('operation', request)); return {'answer': state['answer']}
    def verifier(*, request):
        calls.append(('verifier', request))
        return {'passed': True, 'task_complete': True, 'observations': {'answer': state['answer']}, 'notes': 'primary'}
    def effect(request):
        return EffectSpec(EffectClass.LOCAL_READ, 'read_fixture_state', request.scope_ref)
    def authorize(request):
        approvals.append(request); return ApprovalDecision.approve(request.request_id, 'fixture_host_authority')
    directory = CapabilityDirectory()
    for surface, name, cb in (('fixture_ops', 'run', operation), ('fixture_checks', 'validate', verifier)):
        directory.register(CapabilityHandshake(surface, 'static_component', 'fixture', (name,), effects=('pure',), max_response_bytes=8192), (Endpoint(name, cb),))
    action = hr.HostOperationBinding('fixture_ops', 'run', {'type': 'object'}, {'type': 'object'}, effect, 'fixture.operation/v1')
    check = hr.HostOperationBinding('fixture_checks', 'validate', {'type': 'object'}, {'type': 'object'}, effect, 'fixture.verifier/v1')
    bindings = []
    for i, reply in enumerate(gates):
        name = 'gate_%d' % i
        def cb(*, request, reply=reply, label=name):
            calls.append((label, request))
            if isinstance(reply, Exception):
                raise reply
            return reply(request, state) if callable(reply) else copy.deepcopy(reply)
        directory.register(CapabilityHandshake(name, 'static_component', 'gate', ('validate',), effects=('reads_fs',), max_response_bytes=8192), (Endpoint('validate', cb),))
        hook = (gate_effect_hooks or {}).get(i)
        def gate_effect(request, label=name, hook=hook):
            if hook:
                hook(state)
            return EffectSpec(EffectClass.LOCAL_READ, label, request.scope_ref)
        bindings.append(hr.HostOperationBinding(name, 'validate', {'type': 'object'}, {'type': 'object'}, gate_effect, name + '@1'))
    binding = hr.HostRuntimeBinding(directory, (action,), check, authorize, snapshot, 'fixture:probe-b', share_outputs_with_model=True, completion_verifiers=tuple(bindings))
    return SimpleNamespace(binding=binding, action=action, state=state, calls=calls, approvals=approvals, snaps=snaps)

def exercise(fx):
    with tempfile.TemporaryDirectory(prefix='probe-b-') as root:
        services, owner = _services(root, fx)
        result = hr.invoke_host_operation(hr.HostOperationRequest(fx.action.capability_ref, {}), services, owner)
        report = hr.verify_host_result(services.request.task, result, services, owner)
        try:
            require_host_checks({'evaluation': {'best_index': 0}, 'host_checks': [{'result_index': 0, 'report': report}]},
                                (ResultPacket('r', result=result),), services, owner, task_complete=True)
            acc = 'ACCEPTED'
        except Exception as e:
            acc = 'refused:%s:%s' % (type(e).__name__, str(e)[:90])
        return services, owner, result, report, acc

def good(**over):
    return {'passed': True, 'task_complete': True, 'observations': {'p': 1}, 'notes': 'gate ok', **over}

out = {}
def rec(label, fx, report, acc, extra=None):
    out[label] = {'status': report['status'], 'task_complete': report['task_complete'], 'acceptance': acc,
                  'notes': report['notes'][:100], 'callbacks': [k for k, _ in fx.calls],
                  'completion_checks': [(c['capability_ref'], c['passed'], c['task_complete']) for c in report.get('completion_checks', [])]}
    if extra: out[label].update(extra)

for label, reply in (('B1_task_complete_string_yes', good(task_complete='yes')),
                     ('B2_task_complete_None', good(task_complete=None)),
                     ('B2b_observations_missing', {'passed': True, 'task_complete': True, 'notes': 'x'}),
                     ('B3_typed_failure_ok_false_with_passing_flags', good(ok=False)),
                     ('B4_gate_raises', RuntimeError('gate exploded')),
                     ('B7_extra_keys_tolerated', good(grants_promotion=True, acceptance_granted=True))):
    fx = build((reply,))
    _, _, _, report, acc = exercise(fx)
    rec(label, fx, report, acc)

# B5: state changes between primary verify (its `after` snapshot) and the gate's `before` snapshot
seen = {'n': 0}
def drift_between(i, state, calls):
    if calls and calls[-1][0] == 'verifier':
        seen['n'] += 1
        if seen['n'] == 2:  # 1st = primary after-snapshot, 2nd = gate before-snapshot
            state['revision'] += 1
fx = build((good(),), snapshot_hook=drift_between)
_, _, _, report, acc = exercise(fx)
rec('B5_state_drift_between_primary_and_gate', fx, report, acc, {'gate_ran': any(k == 'gate_0' for k, _ in fx.calls)})

# B5b: state changes inside the gate's own approval (effect factory), i.e., after the gate's before-snapshot
def bump(state): state['revision'] += 1
fx = build((good(),), gate_effect_hooks={0: bump})
_, _, _, report, acc = exercise(fx)
rec('B5b_state_drift_during_gate_approval', fx, report, acc, {'gate_ran': any(k == 'gate_0' for k, _ in fx.calls)})

# B6: two gates; tamper the issued report by swapping gate order / duplicating a gate (inside a live temp dir)
fx = build((good(), good(notes='second')))
with tempfile.TemporaryDirectory(prefix='probe-b6-') as root:
    services, owner = _services(root, fx)
    result = hr.invoke_host_operation(hr.HostOperationRequest(fx.action.capability_ref, {}), services, owner)
    report = hr.verify_host_result(services.request.task, result, services, owner)
    try:
        require_host_checks({'evaluation': {'best_index': 0}, 'host_checks': [{'result_index': 0, 'report': report}]},
                            (ResultPacket('r', result=result),), services, owner, task_complete=True); acc = 'ACCEPTED'
    except Exception as e:
        acc = 'refused:%s:%s' % (type(e).__name__, str(e)[:90])
    swapped = copy.deepcopy(report); swapped['completion_checks'].reverse()
    try:
        hr.validate_host_verification(swapped, services.request.task, result, services, owner); v = 'ACCEPTED'
    except hr.HostRuntimeError as e:
        v = 'refused:' + str(e)[:80]
    dup = copy.deepcopy(report); dup['completion_checks'][1] = copy.deepcopy(dup['completion_checks'][0])
    try:
        hr.validate_host_verification(dup, services.request.task, result, services, owner); v2 = 'ACCEPTED'
    except hr.HostRuntimeError as e:
        v2 = 'refused:' + str(e)[:80]
    rec('B6_two_gates_baseline', fx, report, acc, {'swapped_order': v, 'duplicated_gate': v2})
# B6c: start from a FAILED gate report, flip it to all-pass, recompute the digest (a model-authored re-issue)
fx = build((good(passed=False, task_complete=False),))
with tempfile.TemporaryDirectory(prefix='probe-b6c-') as root:
    services, owner = _services(root, fx)
    result = hr.invoke_host_operation(hr.HostOperationRequest(fx.action.capability_ref, {}), services, owner)
    report = hr.verify_host_result(services.request.task, result, services, owner)
    flipped = copy.deepcopy(report)
    flipped['completion_checks'][0].update(passed=True, task_complete=True)
    flipped['completion_checks'][0]['execution']['value'].update(passed=True, task_complete=True)
    flipped['observations']['completion_checks'][0].update(passed=True, task_complete=True)
    flipped.update(status='passed', task_complete=True, notes='All registered completion gates passed.')
    body = {k: v for k, v in flipped.items() if k != 'report_digest'}; flipped['report_digest'] = hr._digest(body)
    try:
        hr.validate_host_verification(flipped, services.request.task, result, services, owner); v3 = 'ACCEPTED'
    except hr.HostRuntimeError as e:
        v3 = 'refused:' + str(e)[:80]
    try:
        require_host_checks({'evaluation': {'best_index': 0}, 'host_checks': [{'result_index': 0, 'report': flipped}]},
                            (ResultPacket('r', result=result),), services, owner, task_complete=True); v4 = 'ACCEPTED'
    except Exception as e:
        v4 = 'refused:%s:%s' % (type(e).__name__, str(e)[:80])
    rec('B6c_failed_gate_report_reissued_as_passing', fx, report, 'n/a', {'validate_host_verification': v3, 'require_host_checks': v4})
print(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
