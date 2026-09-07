"""Probe F: a binding without completion_verifiers must behave identically to the pre-merge module (1ea1335)."""
import importlib.util, sys, json, tempfile, hashlib, copy
from types import SimpleNamespace
from pathlib import Path
S = Path('/tmp/claude-1000/-home-username-loop-engine/6d8b36e1-c0bf-4f98-a765-7be966b7d9c2/scratchpad/agent_host')
spec = importlib.util.spec_from_file_location('loop_engine.core.host_runtime_v0', S / 'host_runtime_v0.py')
v0 = importlib.util.module_from_spec(spec); sys.modules['loop_engine.core.host_runtime_v0'] = v0; spec.loader.exec_module(v0)
from loop_engine.core import host_runtime as v1
from loop_engine.core.adaptive_host_runtime_checks import _services
from loop_engine.loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec
from loop_engine.core.capability_directory import CapabilityDirectory, CapabilityHandshake, Endpoint

def build(m):
    state = {'revision': 1, 'answer': 42}
    calls, approvals = [], []
    def snapshot():
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    def operation(*, request):
        calls.append(('operation', request)); return {'answer': state['answer']}
    def verifier(*, request):
        calls.append(('verifier', request)); return {'passed': True, 'task_complete': True, 'observations': {'answer': 42}, 'notes': 'Fixture checks the host-owned answer.'}
    def effect(request):
        return EffectSpec(EffectClass.LOCAL_READ, 'read_fixture_state', request.scope_ref)
    def authorize(request):
        approvals.append(request); return ApprovalDecision.approve(request.request_id, 'fixture_host_authority')
    directory = CapabilityDirectory()
    for surface, name, cb in (('fixture_ops', 'run', operation), ('fixture_checks', 'validate', verifier)):
        directory.register(CapabilityHandshake(surface, 'static_component', 'Read the host-owned fixture answer.', (name,), effects=('pure',), max_response_bytes=8192), (Endpoint(name, cb),))
    action = m.HostOperationBinding('fixture_ops', 'run', {'type': 'object'}, {'type': 'object'}, effect, 'fixture.operation/v1')
    check = m.HostOperationBinding('fixture_checks', 'validate', {'type': 'object'}, {'type': 'object'}, effect, 'fixture.verifier/v1')
    binding = m.HostRuntimeBinding(directory, (action,), check, authorize, snapshot, 'fixture:host-owned-answer', share_outputs_with_model=True)
    return SimpleNamespace(binding=binding, action=action, calls=calls, approvals=approvals)

RANDOM = {'invocation_id', 'approval_ref', 'effect_digest', 'capability_loop_id', 'result_digest', 'subject_digest',
          'verifier_loop_id', 'producer_loop_id', 'report_digest'}
def mask(d):
    return {k: ('<random>' if k in RANDOM else mask(v) if isinstance(v, dict) else v) for k, v in d.items()}

runs = {}
for name, m in (('v0', v0), ('v1', v1)):
    fx = build(m)
    with tempfile.TemporaryDirectory(prefix='probe-f-') as d:
        services, owner = _services(d, fx)
        result = m.invoke_host_operation(m.HostOperationRequest(fx.action.capability_ref, {}), services, owner)
        report = m.verify_host_result(services.request.task, result, services, owner)
        m.validate_host_verification(report, services.request.task, result, services, owner)
        kinds = [e.get('custom_kind') or e.get('event') for e in owner.ledger.events]
        runs[name] = {'summary': fx.binding.summary(), 'descriptors': list(fx.binding.descriptors()),
                      'result': mask(result), 'report': mask(report), 'ledger_kinds': kinds,
                      'callbacks': [k for k, _ in fx.calls], 'approvals': len(fx.approvals),
                      'port_caps': list(owner.runtime_context.custom_plugins.capabilities) if getattr(owner, 'runtime_context', None) and owner.runtime_context.custom_plugins else None,
                      'invocation_record_keys': sorted(fx.calls[1][1].to_dict().keys()),
                      'verifier_arguments_keys': sorted(fx.calls[1][1].arguments.keys())}
out = {}
for key in runs['v0']:
    same = json.dumps(runs['v0'][key], sort_keys=True, default=str) == json.dumps(runs['v1'][key], sort_keys=True, default=str)
    out[key] = 'identical' if same else {'v0': runs['v0'][key], 'v1': runs['v1'][key]}
out['result_keys_v1'] = sorted(runs['v1']['result'].keys())
out['report_keys_v1'] = sorted(runs['v1']['report'].keys())
print(json.dumps(out, indent=1, default=str)[:6000])
