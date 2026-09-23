"""Realize canonical semantic steps through explicitly registered harnesses.

Owns: a passive realization binding and its run-scoped gateway client.
Belongs to: the existing external-harness/model-gateway boundary.
Does not own: task planning, effects, intelligence admission, verification,
promotion, model routes, or another operational runtime. Those remain Loops.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path

from .external_harness import (
    HarnessAdapterInfo, HarnessBudget, HarnessModelCall, HarnessModelIdentity,
    HarnessRegistry, HarnessRunRequest, HarnessRunResult, HarnessRuntimeBinding,
    HarnessServices, ModelOutputLimit, run_external_harness,
)
from .external_harness_contract import ADAPTER_CONTRACT_VERSION, MODEL_RESPONSE_EDGE
from .harness_execution_contracts import HarnessExecutionCapabilities
from .instance_instructions import InstanceInstructionWriter
from .harness_fallback import (
    ALTERNATIVES_EXHAUSTED, FAILURE_NOT_PERMITTED_BY_POLICY, RESPONSE_EVALUATION_INCONCLUSIVE,
    UNEXPECTED_EFFECTS_REQUIRE_RECONCILIATION,
    HarnessFallbackPolicy, HarnessFailureKind, HarnessRecoveryObservation, assess_harness_attempt,
)
from .harness_response_evaluation import PASSED, REJECTED

#: A semantic harness instance is confined to the step folder the engine makes
#: for it. It reads and writes there, and every model call leaves through the
#: relay the engine owns rather than through the instance. Those are the only
#: effects its instruction file may name.
SEMANTIC_INSTANCE_EFFECTS = ("reads_fs", "writes_fs")
#: What the instance is told about reporting. Completion is not acceptance.
SEMANTIC_INSTANCE_REPORTING = (
    "Return the response the packet's contract names. Finishing a response is not "
    "acceptance: the owning Loop checks the work and decides whether the assignment "
    "is done.")

from .model_gateway import (
    EVALUATOR_VERDICT_ERRORS, ModelGateway, ModelGatewayRequest, ModelGatewayResult,
)
from .model_gateway_accounting import complete_attempt_sum
from .model_prompt_envelope import ModelPromptEnvelopeBinding
from .harness_selection_records import HarnessSelectionPolicy, HarnessSelectionScope
from .outcome_vector import DEFAULT_OUTCOME_VECTOR_POLICY


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _record_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class _HarnessSemanticAttempt:
    response: ModelGatewayResult
    harness_result: HarnessRunResult | None = None
    gateway_results: tuple[ModelGatewayResult, ...] = ()
    accounting_uncertain: bool = False


@dataclass(frozen=True)
class HarnessSemanticBinding:
    """One explicit adapter selection; no discovery-time execution or grants."""

    harness_id: str
    registry: HarnessRegistry = field(repr=False, compare=False)
    work_root: str
    artifact_store: object = field(default=None, repr=False, compare=False)
    socket_directory: str = ''
    fallback_policy: HarnessFallbackPolicy | None = None
    selection_policy: HarnessSelectionPolicy | None = None
    #: Optional declaration of the wrapper composition and native control
    #: ownership this binding runs under (core.harness_layering). Absent, the
    #: direct adapter runs, which is also what an empty composition with
    #: every control owned by the Loop declares. A composition with wrapper
    #: layers, or a natively owned control, is recorded but refused at
    #: invocation until an executor for it is registered, so a declaration
    #: can never be silently run as something else.
    layering: object = field(default=None, repr=False, compare=False)
    _registration: HarnessAdapterInfo = field(init=False, repr=False)
    _adapter: object = field(init=False, repr=False, compare=False)
    _alternatives: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.registry, HarnessRegistry):
            raise TypeError('a harness realization requires HarnessRegistry')
        adapter = self.registry.get(self.harness_id)
        info = adapter.info()
        root = Path(self.work_root)
        if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
            raise ValueError('harness working storage requires an absolute non-symlink path')
        if self.artifact_store is not None:
            from .context_artifacts import ContextArtifactManager
            if not isinstance(self.artifact_store, ContextArtifactManager):
                raise TypeError('harness artifacts require ContextArtifactManager')
        object.__setattr__(self, '_registration', info)
        object.__setattr__(self, '_adapter', adapter)
        policy = self.fallback_policy
        if self.selection_policy is not None and not isinstance(self.selection_policy, HarnessSelectionPolicy):
            raise TypeError('harness selection requires a typed reviewed-evidence policy')
        if policy is not None and not isinstance(policy, HarnessFallbackPolicy):
            raise TypeError('harness fallback requires a typed policy')
        ids = policy.harness_ids if policy is not None else (self.harness_id,)
        if ids[0] != self.harness_id:
            raise ValueError('fallback order must start with the selected harness')
        object.__setattr__(self, '_alternatives', tuple(
            (item, self.registry.get(item), self.registry.get(item).info()) for item in ids))
        if any(MODEL_RESPONSE_EDGE not in info.supported_edge_contracts
               for _item, _adapter, info in self._alternatives):
            # A step engine in the same registry never answers a semantic call.
            raise ValueError('a harness realization alternative must serve the model response edge')
        if self.layering is not None:
            from .harness_layering import LayeredHarnessBinding
            layering = self.layering
            if not isinstance(layering, LayeredHarnessBinding):
                raise TypeError('harness layering requires a typed LayeredHarnessBinding')
            if layering.initial.harness_id != self.harness_id:
                raise ValueError('the layered binding must wrap the selected harness')
            outer = layering.fallback_policy
            if (outer is None) != (policy is None) or (
                    outer is not None and outer.content_digest != policy.content_digest):
                raise ValueError('the layered binding must be checked against this binding\'s '
                                 'own fallback policy')
            for item in layering.fallbacks:
                if item.harness_id and item.harness_id not in ids:
                    raise ValueError('a layered fallback names a harness outside the registered order')
            # Refuse here, at construction, so the exact reason reaches the
            # caller instead of being folded into a session's fail-closed
            # accounting failure at invocation.
            self._refuse_undeclared_executor()

    def _refuse_undeclared_executor(self):
        """A declaration is not an implementation: refuse to run wrappers or
        native controls that no registered executor implements."""
        if self.layering is None:
            return
        from .harness_layering_availability import EXECUTABLE_NOW, executor_refusal
        state, reason = executor_refusal(self.layering, self.harness_id,
                                         self._adapter_native_controls())
        if state != EXECUTABLE_NOW:
            raise ValueError(reason)

    def _adapter_native_controls(self):
        capabilities = self._registration.execution_capabilities
        return tuple(capabilities.native_controls) if capabilities is not None else ()

    def _layering_fields(self):
        if self.layering is None:
            return {'layering_digest': '', 'composition_id': '', 'control_policy_digest': '',
                    'composition_executor': 'direct_adapter'}
        return {'layering_digest': self.layering.content_digest,
                'composition_id': self.layering.initial.composition_id,
                'control_policy_digest': self.layering.control_policy.content_digest,
                'composition_executor': 'direct_adapter'}

    def invoke(self, request: ModelGatewayRequest, *, gateway: ModelGateway,
               parent, artifact_store=None, validate=None, selection_scope=None,
               evaluation_state=None) -> ModelGatewayResult:
        """Try explicit alternatives within one semantic call's shared authority.

        Each adapter attempt gets a fresh work directory and canonical Spawned
        Loop. Only a semantic proposal is retried, never a host tool effect.
        """
        started = time.monotonic()
        for item, registered, info in self._alternatives:
            adapter = self.registry.get(item)
            if adapter is not registered or adapter.info() != info:
                raise ValueError('harness realization registration changed')
        if not request.semantic_call_id:
            request = replace(request, semantic_call_id='semantic-harness-' + uuid.uuid4().hex)
        policy = self.fallback_policy or HarnessFallbackPolicy((self.harness_id,), ())
        self._refuse_undeclared_executor()
        if self.layering is not None:
            parent.ledger.record(loop_id=parent.loop_id, event='custom',
                action='harness_layering_bound', record_type='harness_layering_bound/v1',
                semantic_call_id=request.semantic_call_id,
                assignment_ref=self.layering.assignment_ref,
                natively_owned_controls=[item.value for item in self.layering.control_policy.natively_owned()],
                adapter_native_controls=list(self._adapter_native_controls()),
                fallback_actions=[item.action for item in self.layering.fallbacks],
                **self._layering_fields())
        if self.selection_policy is not None:
            from .harness_selection import select_harness_as_loop
            routes = gateway._routes(request.config)
            if selection_scope is not None and routes:
                if not isinstance(selection_scope,HarnessSelectionScope):
                    raise TypeError('assignment harness selection scope must be typed')
                primary=routes[0][0]
                selection=select_harness_as_loop(self.selection_policy,selection_scope,
                    tuple(item[2] for item in self._alternatives),provider_id=primary.provider,
                    model_id=primary.model,parent=parent)
                parent.ledger.record(loop_id=parent.loop_id,event='custom',action='harness_selection_bound',
                    semantic_call_id=request.semantic_call_id,request_digest=request.request_digest,
                    scope_digest=selection.scope_digest,policy_digest=selection.policy_digest,
                    selection_loop_id=selection.selection_loop_id)
                if not selection.ordered_harness_ids:
                    return ModelGatewayResult(error_code='harness_capability_requirement_unsatisfied',
                        error='No authorized harness satisfies the assignment requirements')
                policy=replace(policy,harness_ids=selection.ordered_harness_ids)
            else:
                parent.ledger.record(loop_id=parent.loop_id,event='custom',action='harness_selection_unavailable',
                    semantic_call_id=request.semantic_call_id,reason='bound_contract_or_route_unavailable',
                    configured_order=list(policy.harness_ids))
        registrations={item[0]:(item[1],item[2]) for item in self._alternatives}
        responses = []
        recovery = []
        for index, harness_id in enumerate(policy.harness_ids):
            # Recheck exact registrations after prior execution, not just at
            # discovery. Adapter code cannot replace a later alternative.
            registered, info = registrations[harness_id]
            if self.registry.get(harness_id) is not registered or registered.info() != info:
                raise ValueError('harness realization registration changed')
            config = request.config
            calls = sum(item.physical_model_calls for item in responses)
            stop_code = ''
            if config.max_route_attempts is not None:
                remaining = config.max_route_attempts - calls
                if remaining <= 0:
                    stop_code = 'model_call_budget_exhausted'
                else:
                    config = replace(config, max_route_attempts=remaining)
            if config.max_total_tokens is not None:
                if any(item.physical_model_calls and item.total_tokens is None for item in responses):
                    stop_code = 'token_accounting_unavailable'
                else:
                    remaining = config.max_total_tokens - sum(item.total_tokens or 0 for item in responses)
                    if remaining <= 0:
                        stop_code = 'token_budget_exhausted'
                    else:
                        config = replace(config, max_total_tokens=remaining)
            seconds = config.timeout_seconds - (time.monotonic() - started)
            if seconds <= 0:
                stop_code = 'time_budget_exhausted'
            if stop_code:
                parent.ledger.record(loop_id=parent.loop_id, event='custom',
                    action='harness_fallback_stopped', semantic_call_id=request.semantic_call_id,
                    policy_digest=policy.content_digest, error_code=stop_code)
                responses.append(ModelGatewayResult(error_code=stop_code))
                break
            current = replace(request, config=replace(config, timeout_seconds=seconds))
            if evaluation_state is not None:
                evaluation_state.begin_attempt()
            attempt = self._invoke_one(current, gateway=gateway, parent=parent,
                artifact_store=artifact_store, validate=validate, harness_id=harness_id,
                source_request=request, recovery=tuple(recovery), adapter=registered)
            response = attempt.response
            responses.append(response)
            if attempt.harness_result is None:
                break  # Shared configuration failed before any adapter launch.
            decision = assess_harness_attempt(policy, index, attempt.harness_result,
                attempt.gateway_results, accounting_uncertain=attempt.accounting_uncertain,
                response_evaluation=evaluation_state.latest if evaluation_state is not None else None)
            if decision.accounting_uncertain:
                response.ok, response.text = False, ''
                response.error_code = 'provider_attempt_contract_violated'
            elif decision.reason == UNEXPECTED_EFFECTS_REQUIRE_RECONCILIATION:
                response.ok, response.text = False, ''
                response.error_code = decision.reason
            elif (evaluation_state is not None and evaluation_state.latest is not None
                  and decision.reason in (HarnessFailureKind.SEMANTIC_REJECTED.value,
                                          FAILURE_NOT_PERMITTED_BY_POLICY, ALTERNATIVES_EXHAUSTED,
                                          RESPONSE_EVALUATION_INCONCLUSIVE)
                  and all(item.error_code in ('output_validation_failed', *EVALUATOR_VERDICT_ERRORS)
                          for item in attempt.gateway_results if not item.ok)):
                if evaluation_state.latest.status != PASSED:
                    response.ok, response.text = False, ''
                    response.error_code = ('semantic_response_rejected' if evaluation_state.latest.status == REJECTED
                                           else 'response_evaluation_inconclusive')
            parent.ledger.record(loop_id=parent.loop_id, event='custom',
                action='harness_attempt_assessed', record_type='harness_attempt_assessment/v1',
                semantic_call_id=request.semantic_call_id, policy_digest=policy.content_digest,
                attempt_index=index, harness_id=harness_id,
                harness_loop_id=attempt.harness_result.loop_id,
                prompt_digest=request.prompt_digest, system_digest=request.system_digest,
                request_digest=request.request_digest, status=attempt.harness_result.status,
                decision=decision.reason, next_harness_id=decision.next_harness_id,
                model_calls_known_subtotal=response.physical_model_calls,
                model_call_accounting_complete=not decision.accounting_uncertain,
                outcome_vector_policy_digest=_record_digest(
                    DEFAULT_OUTCOME_VECTOR_POLICY.to_dict()),
                task_accepted=False, **self._layering_fields())
            if not decision.next_harness_id:
                break
            recovery.append(HarnessRecoveryObservation(harness_id,
                attempt.harness_result.loop_id, request.semantic_call_id,
                HarnessFailureKind(decision.reason),
                evaluation_state.latest.contract_ref if evaluation_state is not None and evaluation_state.latest is not None
                    and decision.reason == HarnessFailureKind.SEMANTIC_REJECTED.value else '',
                evaluation_state.latest.finding_codes if evaluation_state is not None and evaluation_state.latest is not None
                    and decision.reason == HarnessFailureKind.SEMANTIC_REJECTED.value else ()))
        latest = responses[-1]
        attempts = [attempt for item in responses for attempt in item.attempts]
        physical = [attempt for attempt in attempts if attempt.loop_id]
        return replace(latest, attempts=attempts,
            input_tokens=complete_attempt_sum(physical, 'input_tokens') if physical else None,
            output_tokens=complete_attempt_sum(physical, 'output_tokens') if physical else None,
            semantic_call_id=request.semantic_call_id, owner_loop_id=parent.loop_id,
            prompt_digest=request.prompt_digest, system_digest=request.system_digest,
            request_digest=request.request_digest,
            prompt_envelopes=tuple(envelope for item in responses for envelope in item.prompt_envelopes))

    def _invoke_one(self, request, *, gateway, parent, artifact_store, validate,
                    harness_id, source_request, recovery, adapter) -> _HarnessSemanticAttempt:
        """Keep one adapter attempt and its accounting inside one harness Loop."""
        from ..loop.loop_contract import LoopContract
        manager = artifact_store or self.artifact_store
        if manager is None:
            raise ValueError('a harness realization needs the owning run artifact manager')
        routes = gateway._routes(request.config)
        if not routes:
            return _HarnessSemanticAttempt(ModelGatewayResult(error_code='no_eligible_route',
                                      error='no eligible model route'))
        primary = routes[0][0]
        provider = gateway.providers.get(primary.provider)
        if provider is None:
            return _HarnessSemanticAttempt(ModelGatewayResult(error_code='provider_not_configured'))
        capability = provider.output_capability_for(primary.model)
        if capability.declared_maximum is None:
            return _HarnessSemanticAttempt(ModelGatewayResult(error_code='unknown_model_output_limit'))
        allocation = request.config.output_allocation
        limit = ModelOutputLimit(
            capability.declared_maximum, 'provider_declared', capability.source,
            primary.provider, primary.model, primary.name)
        client = HarnessGatewayClient(
            gateway, request, parent, primary.model, validator=validate,
            window_tokens=int(
                getattr(primary.capabilities, 'max_context', 0) or 0),
            output_capability=capability, route_provider=primary.provider,
            route_model=primary.model, route_name=primary.name,
            source_request=source_request, recovery_observations=recovery)
        work = Path(self.work_root) / ('step-' + uuid.uuid4().hex)
        work.mkdir(parents=True, mode=0o700, exist_ok=False)
        context_capacity = int(getattr(primary.capabilities, 'max_context', 0) or 0)
        vector_policy = DEFAULT_OUTCOME_VECTOR_POLICY.to_dict()
        vector_policy_digest = _record_digest(vector_policy)
        harness_request = HarnessRunRequest(
            request_id='semantic-' + uuid.uuid4().hex,
            harness_id=harness_id,
            goal='Resolve one canonical semantic step',
            contract=LoopContract(
                name='canonical semantic proposal', execution_mode='model_led',
                input_roles=('semantic_packet',), output_roles=('semantic_proposal',),
                role='practitioner'),
            budget=HarnessBudget(
                max_model_calls=request.config.max_route_attempts,
                max_total_tokens=request.config.max_total_tokens,
                max_seconds=request.config.timeout_seconds,
                output_limit=limit, output_allocation=allocation),
            input_data={
                'prompt': request.prompt, 'system': request.system,
                'prompt_digest': request.prompt_digest,
                'system_digest': request.system_digest,
                'semantic_call_id': request.semantic_call_id,
                'work_directory': str(work), 'context_capacity': context_capacity,
                'socket_directory': self.socket_directory,
                'outcome_vector_policy': vector_policy,
            },
            provider_id=primary.provider, model_id=primary.model,
            model_routes=tuple(dict.fromkeys(route.name for route, _ in routes)),
            authorized_model_identities=tuple(dict.fromkeys(
                HarnessModelIdentity(route.provider, route.model, route.name)
                for route, _ in routes)),
            authorize_model_calls=True,
            outcome_vector_policy=DEFAULT_OUTCOME_VECTOR_POLICY,
            metadata={
                'owning_practitioner_control': {
                    'outcome_vector_policy_id': vector_policy['policy_id'],
                    'outcome_vector_policy_version': vector_policy['version'],
                    'outcome_vector_policy_digest': vector_policy_digest,
                    'adapter_may_self_accept': False,
                }},
        )
        result = run_external_harness(
            adapter, harness_request, parent=parent,
            services=HarnessServices(
                artifact_store=manager,
                instruction_writer=InstanceInstructionWriter(
                    str(work), SEMANTIC_INSTANCE_EFFECTS,
                    reporting=SEMANTIC_INSTANCE_REPORTING, visible_root="/work"),
                runtime_binding=HarnessRuntimeBinding(
                    primary.provider, primary.model, 'client', client,
                    'gateway-request:' + request.request_digest, limit)))
        attempts = [attempt for item in client.results for attempt in item.attempts]
        physical = [attempt for attempt in attempts if attempt.loop_id]
        latest = client.results[-1] if client.results else ModelGatewayResult()
        if result.completed and (not client.final_text or result.output != client.final_text):
            result.status, result.output = 'failed', None
            result.error_code = 'adapter_reported_failure'
        output = client.final_text if result.completed else ''
        response = ModelGatewayResult(
            ok=result.completed and bool(output), text=output,
            provider=latest.provider or primary.provider,
            model=(physical[-1].model if physical else ''), route=latest.route or primary.name,
            thinking_power=latest.thinking_power,
            input_tokens=complete_attempt_sum(physical, 'input_tokens') if physical else None,
            output_tokens=complete_attempt_sum(physical, 'output_tokens') if physical else None,
            attempts=attempts, gateway_loop_id=latest.gateway_loop_id,
            error_code=('provider_attempt_contract_violated' if client.accounting_uncertain else
                        '' if result.completed else
                        latest.error_code or result.error_code or 'adapter_reported_failure'),
            error=('' if result.completed else 'semantic harness did not produce an admitted response'),
            semantic_call_id=request.semantic_call_id,
            owner_loop_id=parent.loop_id,
            prompt_digest=request.prompt_digest, system_digest=request.system_digest,
            request_digest=request.request_digest,
            transport_succeeded=latest.transport_succeeded,
            transport_error_code=latest.transport_error_code,
            prompt_envelopes=tuple(client.prompt_envelopes),
        )
        return _HarnessSemanticAttempt(response, result, tuple(client.results), client.accounting_uncertain)


@dataclass
class HarnessGatewayClient:
    """Credential-free harness requests enter the original authorized gateway."""

    gateway: ModelGateway
    request: ModelGatewayRequest
    parent: object
    proxy_model: str
    validator: object = field(default=None, repr=False)
    results: list[ModelGatewayResult] = field(default_factory=list)
    prompt_envelopes: list[ModelPromptEnvelopeBinding] = field(default_factory=list)
    final_text: str = ''
    accounting_uncertain: bool = False
    started: float = field(default_factory=time.monotonic)
    #: Measured route context window and output capability, bound at invoke
    #: time so per-attempt allocations derive from evidence, never defaults.
    window_tokens: int = 0
    output_capability: object = field(default=None, repr=False)
    route_provider: str = ''
    route_model: str = ''
    route_name: str = ''
    source_request: ModelGatewayRequest | None = field(default=None, repr=False)
    recovery_observations: tuple[HarnessRecoveryObservation, ...] = ()

    def _fit_window(self, actual):
        """Attach an explicit output allocation when the declared capacity
        cannot fit the route window.

        The declared maximum is the provider's accepted ceiling; the usable
        ceiling for THIS attempt is window minus measured input. The
        allocation records that derivation with the semantic call as
        decision provenance, so nothing is silently defaulted: a prompt
        that already fills the window is refused, not truncated.
        """
        from .context_budget import estimate_tokens
        from .model_capabilities import ModelOutputAllocation
        if actual.config.output_allocation is not None:
            return actual
        capability = self.output_capability
        maximum = getattr(capability, 'declared_maximum', None)
        if maximum is None or self.window_tokens <= 0:
            return actual
        estimated_input = estimate_tokens(actual.prompt, actual.system)
        requested = self.window_tokens - estimated_input
        if requested < 1:
            raise ValueError(
                'harness prompt already fills the route context window')
        if requested >= maximum:
            return actual
        return replace(actual, config=replace(
            actual.config, output_allocation=ModelOutputAllocation(
                capability=capability, provider_id=self.route_provider,
                model_id=self.route_model, route_name=self.route_name,
                requested_tokens=requested,
                decision_ref=actual.semantic_call_id or 'harness-fit-window',
                reason=(f'fit declared {maximum} into measured window '
                        f'{self.window_tokens} after {estimated_input} '
                        f'estimated input tokens'))))

    def __call__(self, payload: dict) -> dict:
        """Record bounded contract refusals without copying a private request."""
        try:
            return self._call_admitted(payload)
        except ValueError as exc:
            known = {
                'harness requested an unauthorized model': 'unauthorized_model',
                'previous provider attempt has unresolved accounting': 'unresolved_accounting',
                'harness needs bounded messages': 'invalid_messages',
                'semantic harness cannot grant native tool execution': 'native_tools_not_authorized',
                'harness message role is not supported': 'unsupported_message_role',
                'semantic harness messages must be text': 'nontext_message',
                'harness omitted or changed the original semantic packet': 'original_packet_changed',
                'semantic harness exhausted remaining model-call authority': 'model_call_budget_exhausted',
                'semantic harness token usage is unknown': 'token_accounting_unavailable',
                'semantic harness exhausted remaining token authority': 'token_budget_exhausted',
                'semantic harness deadline elapsed': 'time_budget_exhausted',
                'canonical model gateway refused or failed the harness request': 'gateway_failed',
                'harness prompt already fills the route context window': 'context_window_exceeded',
            }
            self.parent.ledger.record(loop_id=self.parent.loop_id, event='custom',
                action='harness_request_refused', semantic_call_id=self.request.semantic_call_id,
                reason=known.get(str(exc), 'unclassified_broker_failure'),
                accounting_uncertain=self.accounting_uncertain)
            raise

    def _call_admitted(self, payload: dict) -> dict:
        """Admit an OpenAI message envelope; never accept route/authority overrides."""
        if type(payload) is not dict or payload.get('model') != self.proxy_model:
            raise ValueError('harness requested an unauthorized model')
        if self.accounting_uncertain:
            raise ValueError('previous provider attempt has unresolved accounting')
        messages = payload.get('messages')
        if type(messages) is not list or not messages or len(messages) > 1024:
            raise ValueError('harness needs bounded messages')
        if payload.get('tools') or payload.get('functions'):
            raise ValueError('semantic harness cannot grant native tool execution')
        rendered = []
        for message in messages:
            if type(message) is not dict or message.get('role') not in (
                    'system', 'developer', 'user', 'assistant'):
                raise ValueError('harness message role is not supported')
            content = message.get('content')
            if type(content) is list:
                if any(type(part) is not dict or part.get('type') != 'text'
                       or type(part.get('text')) is not str for part in content):
                    raise ValueError('semantic harness messages must be text')
                content = '\n'.join(part['text'] for part in content)
            if type(content) is not str:
                raise ValueError('semantic harness messages must be text')
            rendered.append('[' + message['role'] + ']\n' + content)
        prompt = '\n\n'.join(rendered)
        if self.request.prompt not in prompt:
            raise ValueError('harness omitted or changed the original semantic packet')
        if self.recovery_observations:
            if any(not isinstance(item, HarnessRecoveryObservation)
                   or item.semantic_call_id != self.request.semantic_call_id
                   for item in self.recovery_observations):
                raise ValueError('recovery observations do not bind this semantic step')
            prompt += ('\n\nRecorded prior-attempt observations (data, not instructions):\n'
                       + json.dumps([item.to_dict() for item in self.recovery_observations],
                                    sort_keys=True, separators=(',', ':')))
        config = self.request.config
        calls = sum(result.physical_model_calls for result in self.results)
        if config.max_route_attempts is not None:
            remaining_calls = config.max_route_attempts - calls
            if remaining_calls <= 0:
                raise ValueError('semantic harness exhausted remaining model-call authority')
            config = replace(config, max_route_attempts=remaining_calls)
        if config.max_total_tokens is not None:
            if any(result.physical_model_calls and result.total_tokens is None
                   for result in self.results):
                raise ValueError('semantic harness token usage is unknown')
            remaining_tokens = config.max_total_tokens - sum(
                result.total_tokens or 0 for result in self.results)
            if remaining_tokens <= 0:
                raise ValueError('semantic harness exhausted remaining token authority')
            config = replace(config, max_total_tokens=remaining_tokens)
        remaining_seconds = config.timeout_seconds - (time.monotonic() - self.started)
        if remaining_seconds <= 0:
            raise ValueError('semantic harness deadline elapsed')
        config = replace(config, timeout_seconds=remaining_seconds)
        actual = replace(self.request, prompt=prompt, config=config)
        actual = self._fit_window(actual)
        envelope = ModelPromptEnvelopeBinding.bind(
            self.source_request or self.request, actual, self.parent.loop_id)
        try:
            result = self.gateway.invoke(actual, parent=self.parent, validate=self.validator)
        except Exception:
            self.accounting_uncertain = True
            raise
        self.results.append(result)
        if result.physical_model_calls:
            self.prompt_envelopes.append(envelope)
        if result.error_code in ('token_bound_violated', 'provider_attempt_contract_violated'):
            self.accounting_uncertain = True
        if not result.ok:
            raise ValueError('canonical model gateway refused or failed the harness request')
        self.final_text = result.text
        usage = {}
        if result.input_tokens is not None:
            usage['prompt_tokens'] = result.input_tokens
        if result.output_tokens is not None:
            usage['completion_tokens'] = result.output_tokens
        if result.total_tokens is not None:
            usage['total_tokens'] = result.total_tokens
        return {
            'id': 'gateway-' + uuid.uuid4().hex, 'object': 'chat.completion',
            'created': int(time.time()), 'model': self.proxy_model,
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': result.text},
                         'finish_reason': 'stop'}], 'usage': usage,
        }


@dataclass(frozen=True)
class GatewayHarnessProcessAdapter:
    """Registered process mechanics; every physical model request is brokered."""

    spec: object

    def __post_init__(self):
        from .harness_process import HarnessProcessSpec
        if not isinstance(self.spec, HarnessProcessSpec):
            raise TypeError('a process harness requires a pinned HarnessProcessSpec')

    def info(self):
        return HarnessAdapterInfo(
            harness_id=self.spec.harness_id, adapter_version='1.0.0+' + self.spec.digest,
            package_name=self.spec.harness_id, package_version=self.spec.package_version,
            available=True, features=('canonical_semantic_steps', 'gateway_broker'),
            limitations=('native harness tools are disabled; the owning Loop executes engine capabilities',),
            execution_capabilities=HarnessExecutionCapabilities(
                supported_features=('configuration_isolation', 'credential_isolation',
                                    'private_prompt_channel', 'private_raw_events',
                                    'process_tree_cancellation', 'model_routes'),
                enforced_limits=('model_calls', 'total_tokens', 'maximum_output', 'wall_time'),
                isolation='os_sandbox', evidence_refs=('harness_process_checks',)),
            adapter_contract_version=ADAPTER_CONTRACT_VERSION, engine_kind='text_relay_harness',
            supported_edge_contracts=(MODEL_RESPONSE_EDGE,))

    def run(self, request: HarnessRunRequest, services: HarnessServices):
        from .harness_process import HarnessProcessRequest, run_harness_process
        binding = services.runtime_binding
        if binding is None or not isinstance(binding.runtime_object, HarnessGatewayClient):
            raise TypeError('process harness requires the canonical gateway client')
        binding.validate_for(request, runtime_kind='client', preconfigured_output_limit=True)
        client = binding.runtime_object
        process_request = HarnessProcessRequest(
            spec=self.spec, prompt=request.input_data['prompt'], model=request.model_id,
            output_capacity=request.budget.max_output_tokens,
            output_allowance=request.budget.requested_output_tokens,
            timeout_seconds=request.budget.max_seconds,
            work_dir=request.input_data['work_directory'],
            socket_directory=request.input_data['socket_directory'] or None,
            context_capacity=request.input_data['context_capacity'] or None,
            instruction_material=(services.instruction_writer.material_for(request)
                                  if services.instruction_writer is not None else ()))
        observed = run_harness_process(process_request, client)
        calls = tuple(HarnessModelCall(
            provider=attempt.provider, model=attempt.model, ok=attempt.provider_ok,
            input_tokens=attempt.input_tokens, output_tokens=attempt.output_tokens,
            error_code=attempt.error_code, elapsed_seconds=attempt.elapsed_seconds,
            route_id=attempt.route, gateway_loop_id=attempt.loop_id)
            for result in client.results for attempt in result.physical_provider_attempts)
        completed = (observed.ok and observed.output == client.final_text
                     and not client.accounting_uncertain)
        artifact = services.artifact_store.store.put_text(
            json.dumps({'harness_id': request.harness_id,
                        'package_version': self.spec.package_version,
                        'exit_code': observed.exit_code, 'timed_out': observed.timed_out,
                        'errors': observed.errors, 'process_identity': observed.process_identity,
                        'broker_requests': observed.broker_request_count,
                        'received_requests': observed.received_request_count,
                        'instruction_manifest': list(observed.instruction_manifest),
                        'instruction_loading_observed': False,
                        'stdout_digest': _digest(observed.stdout),
                        'stderr_digest': _digest(observed.stderr)}, sort_keys=True),
            media_type='application/json', artifact_kind='harness_execution')
        return HarnessRunResult(
            request.request_id, request.harness_id, 'completed' if completed else 'failed',
            output=observed.output if completed else None,
            error_code='' if completed else 'adapter_reported_failure',
            error='' if completed else 'harness execution failed',
            model_calls=calls, call_count_complete=not client.accounting_uncertain,
            reported_model_call_count=len(calls) if not client.accounting_uncertain else None,
            adapter_version=self.info().adapter_version,
            provider_id=request.provider_id, model_id=request.model_id,
            trace_ref=artifact.object_key,
            max_output_tokens_used=request.budget.requested_output_tokens,
            model_output_limit_source=request.budget.output_limit.source,
            model_output_limit_reference=request.budget.output_limit.reference)


def self_test():
    """Offline integration checks are maintained beside this boundary."""
    from .harness_semantic_checks import run_checks as checks
    return checks()
