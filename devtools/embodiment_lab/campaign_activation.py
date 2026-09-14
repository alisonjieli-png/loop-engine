"""Time gating and gateway access checks for any configured campaign route.

Location does not select a runtime or protocol. The existing gateway owns
provider dispatch and accounting; this application records a separate probe
history and never treats a probe as task completion or model quality.
"""
from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib
from pathlib import Path
import uuid

from loop_engine.code_nodes.solution_model_port import ModelExecution, ModelInvocationRequest
from loop_engine.core.model_gateway import ModelGatewayConfig, _error_code
from loop_engine.core.run_history import RunHistory
from loop_engine.loop.loop_role import LoopRole, LoopRoleIdentity
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome


@dataclass(frozen=True)
class CampaignAccessPolicy:
    """When to spend a separate provider-access call in one worker activation."""

    frequency: str = "per_worker_activation"
    version: str = "1.0.0"

    def __post_init__(self):
        if self.frequency not in ("per_worker_activation", "per_trial") or self.version != "1.0.0":
            raise ValueError("unsupported campaign access policy")

    def requires_probe(self, verified_in_activation):
        if type(verified_in_activation) is not bool:
            raise TypeError("access verification state must be explicit")
        return self.frequency == "per_trial" or not verified_in_activation

    def to_dict(self):
        return {"record_type": "campaign_access_policy/v1", "frequency": self.frequency,
                "version": self.version}

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != {"record_type", "frequency", "version"}
                or value["record_type"] != "campaign_access_policy/v1"):
            raise ValueError("invalid campaign access policy record")
        return cls(value["frequency"], value["version"])


def utc_time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('activation time requires an explicit timezone')
    return parsed.astimezone(timezone.utc)


def activation_due(not_before, now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('current time requires an explicit timezone')
    if not_before is None or not_before == '':
        # No gate was declared: the campaign may start. Anything else that
        # is not text (a null written by hand, a number) is not a declared
        # time and must not open the gate by reading as false.
        return True
    if not isinstance(not_before, str):
        raise ValueError('activation time must be text or absent')
    return now >= utc_time(not_before)


def probe_gateway(gateway, route, records):
    """One physical-attempt allowance, full sourced capacity, no failover."""
    authority = ModelExecution(gateway, ModelGatewayConfig(route_names=(route.name,),
        allowed_models=(route.model,), allow_failover=False, max_route_attempts=1,
        timeout_seconds=1200), max_model_calls=1)
    session = authority.start_session()
    config = LoopConfig(framework='custom', custom_steps=('probe',),
        allowable_modes=('non_deterministic',), preferred_modes=('non_deterministic',),
        max_model_calls=1, exit_condition='steps_complete')
    owner = Loop('check the exact configured model route', config,
                 identity=LoopRoleIdentity(LoopRole.PRACTITIONER, 'practitioner.solver'))
    observation = {'reachable': False, 'kind': 'gateway_generation_probe', 'failure_code': '',
        'provider': route.provider, 'model': route.model, 'route': route.name,
        'task_accepted': False, 'model_quality_verified': False}
    def handle(active, step, context):
        try:
            text = session.invoke(ModelInvocationRequest('Reply with READY.',
                semantic_call_id='campaign-access-' + uuid.uuid4().hex), active)
            observation['reachable'] = bool(text) and not session.accounting_uncertain
            observation['response_digest'] = hashlib.sha256(text.encode()).hexdigest()
        except Exception as exc:
            observation['failure_code'] = _error_code(str(exc))
        return StepOutcome('access response observed' if observation['reachable'] else 'access unavailable',
            mode='non_deterministic', confidence=1.0 if observation['reachable'] else 0.0,
            failed=not observation['reachable'], model_calls=0)
    owner.run(handler=handle, max_steps=1)
    results = [result.to_dict() for result in session.results]
    if results and not observation['reachable']:
        observation['failure_code'] = results[-1].get('error_code') or observation['failure_code']
    history = RunHistory.from_ledger(owner.ledger.events, run_id='campaign-access-' + uuid.uuid4().hex)
    history.commit()
    observation.update(model_calls=None if session.accounting_uncertain else session.calls_used,
        model_calls_known_subtotal=session.calls_used, gateway_results=results,
        history=history.save(str(Path(records.path).parent / 'provider-access')),
        history_integrity=history.verify_chain())
    records.record('provider_access', route.name, observation)
    return observation
