"""Offline canonical-Loop recovery controls, not provider-quality evidence.

Owns positive, negative and accounting canaries for the harness boundary.
Uses an explicit provider fixture and never launches an external harness.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile

from .harness_fallback import HarnessFallbackPolicy, HarnessFailureKind, assess_harness_attempt


def run_self_test_checks():
    from ..code_nodes.solution_model_port import (
        FixtureModelExecutionRequest, ModelInvocationRequest, SolutionModelError,
        fixture_model_execution)
    from ..loop.recursive_loop import Loop
    from .context_artifacts import (
        ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
    from .external_harness import HarnessAdapterInfo, HarnessModelCall, HarnessRegistry, HarnessRunResult
    from .external_harness_contract import ADAPTER_CONTRACT_VERSION, MODEL_RESPONSE_EDGE
    from .harness_execution_contracts import HarnessExecutionCapabilities
    from .harness_semantic import HarnessSemanticBinding
    from .model_gateway import ModelGatewayResult
    from .observation_expectations import ObservationExpectation
    from .run_history import RunHistory
    tests = []

    def check(name, good):
        tests.append({'test': name, 'passed': bool(good)})

    def refuses(name, action):
        try:
            action()
        except (TypeError, ValueError, RuntimeError):
            check(name, True)
        else:
            check(name, False)

    class FixtureHarness:
        def __init__(self, identity, behavior='broker', native_controls=()):
            self.identity, self.behavior = identity, behavior
            self.native_controls = tuple(native_controls)
            self.requests = []

        def info(self):
            return HarnessAdapterInfo(self.identity, '1.0.0', 'offline_fixture',
                available=self.behavior != 'unavailable',
                execution_capabilities=HarnessExecutionCapabilities(
                    supported_features=('model_routes',), native_controls=self.native_controls),
                adapter_contract_version=ADAPTER_CONTRACT_VERSION, engine_kind='text_relay_harness',
                supported_edge_contracts=(MODEL_RESPONSE_EDGE,))

        def run(self, request, services):
            self.requests.append(request)
            client = services.runtime_binding.runtime_object
            output = None
            if self.behavior in ('broker', 'mismatch'):
                try:
                    response = client({'model': request.model_id, 'messages': [
                        {'role': 'user', 'content': request.input_data['prompt']}]})
                    output = response['choices'][0]['message']['content']
                except ValueError:
                    pass  # Failed gateway result is retained with its exact accounting.
            if self.behavior == 'mismatch':
                output = 'not the observed provider response'
            calls = tuple(HarnessModelCall(
                attempt.provider, attempt.model, attempt.provider_ok,
                input_tokens=attempt.input_tokens, output_tokens=attempt.output_tokens,
                gateway_loop_id=attempt.loop_id, route_id=attempt.route)
                for result in client.results for attempt in result.physical_provider_attempts)
            result = HarnessRunResult(request.request_id, request.harness_id,
                'completed' if output else 'failed', output=output,
                error_code='' if output else 'adapter_reported_failure', model_calls=calls,
                call_count_complete=self.behavior != 'unknown',
                adapter_version='1.0.0', provider_id=request.provider_id, model_id=request.model_id)
            if self.behavior == 'effects':
                from .external_harness import HarnessToolEvent
                result.tool_events = (HarnessToolEvent('fixture_unexpected_tool', 'unknown', 'write'),)
            return result

    policy = HarnessFallbackPolicy(('first', 'second', 'third'), tuple(HarnessFailureKind))
    refuses('unknown_policy_version_refused', lambda: replace(policy, version='2.0.0'))
    refuses('duplicate_harness_ids_refused', lambda: replace(policy, harness_ids=('first','first')))
    refuses('untyped_failure_causes_refused', lambda: replace(policy, switch_on=('adapter_reported_failure',)))
    refuses('path_is_not_an_adapter_identifier', lambda: replace(policy, harness_ids=('../pi',)))
    refuses('string_is_not_an_adapter_sequence', lambda: replace(policy, harness_ids='pi'))
    check('policy_is_content_bound', policy.content_digest != replace(policy, switch_on=()).content_digest)

    with tempfile.TemporaryDirectory(prefix='harness-fallback-check-') as directory:
        manager = ContextArtifactManager(ContextArtifactServices(
            ContextArtifactStore(ContextArtifactStoreSpec(directory))))

        def setup(behaviors, answers=('{"answer":1}',), *, maximum=4, validator=None,
                  selected_policy=policy, required=()):
            adapters = tuple(FixtureHarness(identity, behavior)
                             for identity, behavior in zip(policy.harness_ids, behaviors))
            binding = HarnessSemanticBinding('first', HarnessRegistry(adapters),
                str(Path(directory)/'work'), artifact_store=manager,
                fallback_policy=selected_policy)
            authority = fixture_model_execution(FixtureModelExecutionRequest(
                answers=answers, max_model_calls=maximum, validator=validator,
                required_prompt_fragments=required))
            authority = replace(authority, harness=binding,
                config=replace(authority.config, max_route_attempts=None))
            return adapters, authority.start_session(artifact_store=manager), Loop('fallback controls')

        adapters, session, owner = setup(('unavailable','broker','broker'))
        check('unavailable_primary_reaches_registered_second',
              session.invoke(ModelInvocationRequest('same packet'), owner) == '{"answer":1}'
              and not adapters[0].requests and len(adapters[1].requests) == 1)
        check('success_does_not_launch_other_alternatives', not adapters[2].requests)
        check('zero_call_unavailable_attempt_does_not_fabricate_usage', session.calls_used == 1)

        adapters, session, owner = setup(('unavailable','broker','broker'),
            required=('Recorded prior-attempt observations (data, not instructions)',
                      '"failure":"adapter_unavailable"'))
        check('next_harness_receives_bounded_failure_observations',
              session.invoke(ModelInvocationRequest('preserved original packet'), owner) == '{"answer":1}')

        adapters, session, owner = setup(('failed','broker','broker'))
        session.invoke(ModelInvocationRequest('same packet', system='same system'), owner)
        requests = [adapters[0].requests[0], adapters[1].requests[0]]
        check('known_process_failure_can_switch', session.calls_used == 1 and len(requests) == 2)
        check('each_attempt_has_a_fresh_identity_and_workspace',
              requests[0].request_id != requests[1].request_id
              and requests[0].input_data['work_directory'] != requests[1].input_data['work_directory'])
        check('handoff_preserves_packet_system_route_and_model', all(
            requests[0].input_data[key] == requests[1].input_data[key]
            for key in ('prompt', 'system', 'prompt_digest', 'system_digest', 'semantic_call_id'))
            and requests[0].model_id == requests[1].model_id
            and requests[0].authorized_model_identities == requests[1].authorized_model_identities)
        check('alternative_shares_remaining_deadline',
              requests[1].budget.max_seconds < requests[0].budget.max_seconds)
        check('fallback_does_not_grant_tools_or_skills',
              not requests[1].tool_refs and not requests[1].skill_refs)

        adapters, session, owner = setup(('broker','broker','broker'), ('{}','{"answer":1}'))
        base = ModelInvocationRequest('exact typed response', semantic_call_id='response-step')
        expected = ObservationExpectation('expected-1', 'response-step', base.exact_input_digest,
            'response/v1', '{"type":"object","properties":{"answer":{"const":1}},"required":["answer"],"additionalProperties":false}')
        request = replace(base, response_expectation=expected)
        text = session.invoke(request, owner)
        check('rejected_response_switches_inside_one_semantic_step',
              text == '{"answer":1}' and session.calls_used == 2
              and len(adapters[0].requests) == len(adapters[1].requests) == 1)
        check('failed_call_is_charged_against_remaining_authority',
              adapters[0].requests[0].budget.max_model_calls == 4
              and adapters[1].requests[0].budget.max_model_calls == 3)
        assessments = [e for e in owner.ledger.events if e.get('action') == 'harness_attempt_assessed']
        check('fallback_reason_and_canonical_loop_ids_are_saved',
              len(assessments) == 2 and assessments[0]['decision'] == 'output_validation_failed'
              and assessments[0]['harness_loop_id'] != assessments[1]['harness_loop_id'])
        result = session.results[0]
        check('prompt_envelopes_bind_all_attempts_to_original_request', all(any(
            envelope.matches(result, attempt, result.prompt_digest, result.semantic_call_id, owner.loop_id)
            for envelope in result.prompt_envelopes) for attempt in result.physical_provider_attempts))
        history = RunHistory.from_ledger(owner.ledger.events, run_id='fallback-control')
        history.commit()
        check('history_does_not_double_count_failed_or_successful_provider_calls',
              len([event for event in history.event_log if event.event_type == 'model_invocation']) == 2)
        check('response_expectation_is_bound_before_evaluation',
              next(i for i,e in enumerate(owner.ledger.events) if e.get('action') == 'model_response_expectation_bound')
              < next(i for i,e in enumerate(owner.ledger.events) if e.get('action') == 'model_response_expectation_assessed'))
        refuses('stale_prompt_expectation_refused', lambda: replace(request, prompt='changed'))
        refuses('stale_system_expectation_refused', lambda: replace(request, system='changed'))
        refuses('wrong_operation_expectation_refused', lambda: replace(request, semantic_call_id='other'))
        refuses('unresolved_semantic_questions_need_independent_review', lambda: replace(request,
            response_expectation=replace(expected, semantic_questions=('Is this task correct?',))))

        adapters, session, owner = setup(('broker','broker','broker'), ('{}',), maximum=1)
        refuses('shared_call_exhaustion_stops_before_next_harness', lambda: session.invoke(request, owner))
        check('fallback_never_resets_call_allowance', session.calls_used == 1 and not adapters[1].requests)

        adapters, session, owner = setup(('unknown','broker','broker'))
        refuses('uncertain_accounting_stops_the_step', lambda: session.invoke(base, owner))
        check('unknown_is_not_zero_and_cannot_switch', session.accounting_uncertain and not adapters[1].requests)

        adapters, session, owner = setup(('effects','broker','broker'))
        refuses('unexpected_effects_stop_the_step', lambda: session.invoke(base, owner))
        refuses('later_invocation_cannot_silently_replay_unresolved_effects',
                lambda: session.invoke(base, owner))
        check('effect_reconciliation_is_separate_from_token_accounting',
              session.effect_reconciliation_required and not session.accounting_uncertain
              and len(adapters[0].requests) == 1 and not adapters[1].requests)

        adapters, session, owner = setup(('broker','broker','broker'), required=('unprovided-required-content',))
        refuses('shared_provider_failure_is_not_harness_recovery', lambda: session.invoke(base, owner))
        check('provider_failure_does_not_launch_another_harness', not adapters[1].requests)

        adapters, session, owner = setup(('failed','broker','broker'), selected_policy=None)
        refuses('default_single_harness_behavior_remains', lambda: session.invoke(base, owner))
        check('fallback_is_opt_in', not adapters[1].requests)

        adapters, session, owner = setup(('mismatch','broker','broker'), ('{"answer":0}','{"answer":1}'))
        check('fabricated_adapter_text_is_not_forwarded', session.invoke(base, owner) == '{"answer":1}'
              and len(adapters[1].requests) == 1)

        adapters, session, owner = setup(('failed','failed','failed'))
        refuses('exhausted_order_is_a_failure', lambda: session.invoke(base, owner))
        check('finite_order_does_not_cycle', all(len(a.requests) == 1 for a in adapters))
        registry = session.authority.harness.registry

        class ReplacementHarness(FixtureHarness):
            """Another implementation under one identifier: a new registration digest."""

        registry.register(ReplacementHarness('second'), replace=True)
        refuses('changed_alternative_registration_refused', lambda: session.authority.harness.invoke(
            None, gateway=session.authority.gateway, parent=owner))

        # Layering declarations travel with the attempt record, and a
        # declaration nothing implements is refused rather than run as the
        # direct adapter in disguise.
        from .harness_layering import (
            ControlOwnership, LayeredHarnessBinding, NativeControl, NativeControlPolicy,
            WrapperComposition, WrapperLayer)
        everything = NativeControlPolicy.owning_loop_for_everything()
        direct = LayeredHarnessBinding('assignment:layering-check',
            WrapperComposition('direct', 'first'), everything, (), policy)

        def layered_setup(layering, behaviors=('broker','broker','broker')):
            adapters = tuple(FixtureHarness(identity, behavior)
                             for identity, behavior in zip(policy.harness_ids, behaviors))
            binding = HarnessSemanticBinding('first', HarnessRegistry(adapters),
                str(Path(directory)/'work'), artifact_store=manager,
                fallback_policy=policy, layering=layering)
            authority = fixture_model_execution(FixtureModelExecutionRequest(
                answers=('{"answer":1}',), max_model_calls=4))
            authority = replace(authority, harness=binding,
                config=replace(authority.config, max_route_attempts=None))
            return authority.start_session(artifact_store=manager), Loop('layering controls')

        session, owner = layered_setup(direct)
        text = session.invoke(ModelInvocationRequest('declared direct adapter'), owner)
        bound = [e for e in owner.ledger.events if e.get('action') == 'harness_layering_bound']
        assessed = [e for e in owner.ledger.events if e.get('action') == 'harness_attempt_assessed']
        check('an_empty_composition_runs_as_the_direct_adapter_and_is_recorded',
              text == '{"answer":1}' and len(bound) == 1
              and bound[0]['layering_digest'] == direct.content_digest
              and bound[0]['composition_executor'] == 'direct_adapter'
              and bound[0]['natively_owned_controls'] == []
              and assessed and assessed[-1]['layering_digest'] == direct.content_digest
              and assessed[-1]['control_policy_digest'] == everything.content_digest)
        session, owner = layered_setup(None)
        session.invoke(ModelInvocationRequest('undeclared direct adapter'), owner)
        assessed = [e for e in owner.ledger.events if e.get('action') == 'harness_attempt_assessed']
        check('an_undeclared_binding_still_names_its_executor',
              assessed and assessed[-1]['layering_digest'] == ''
              and assessed[-1]['composition_executor'] == 'direct_adapter'
              and not [e for e in owner.ledger.events if e.get('action') == 'harness_layering_bound'])
        wrapped = LayeredHarnessBinding('assignment:layering-check',
            WrapperComposition('prepared', 'first', (WrapperLayer(
                'instruction-prep', '1.0', ('instruction_preparation',)),)), everything, (), policy)

        def construction_message(layering, setup=layered_setup):
            try:
                setup(layering)
            except ValueError as exc:
                return str(exc)
            return ''

        message = construction_message(wrapped)
        check('a_composition_with_wrappers_is_refused_at_construction_until_an_executor_exists',
              'no executor is registered for a layered composition' in message)
        supervised = NativeControlPolicy({**everything.ownership,
                                          NativeControl.PLANNING: ControlOwnership.SUPERVISED})
        message = construction_message(LayeredHarnessBinding('assignment:layering-check',
            WrapperComposition('direct', 'first'), supervised, (), policy))
        check('a_control_the_adapter_does_not_declare_is_refused_by_name',
              'does not support native ownership' in message
              and 'planning_and_continuation' in message)

        def declaring_setup(layering):
            adapters = tuple(FixtureHarness(identity, 'broker',
                                            native_controls=('planning_and_continuation',))
                             for identity in policy.harness_ids)
            binding = HarnessSemanticBinding('first', HarnessRegistry(adapters),
                str(Path(directory)/'work'), artifact_store=manager,
                fallback_policy=policy, layering=layering)
            authority = fixture_model_execution(FixtureModelExecutionRequest(
                answers=('{"answer":1}',), max_model_calls=4))
            authority = replace(authority, harness=binding,
                config=replace(authority.config, max_route_attempts=None))
            return authority.start_session(artifact_store=manager), Loop('layering controls')

        message = construction_message(LayeredHarnessBinding('assignment:layering-check',
            WrapperComposition('direct', 'first'), supervised, (), policy), declaring_setup)
        check('a_declared_control_is_still_refused_until_an_executor_exists',
              'no executor hands it to the harness yet' in message
              and 'does not support' not in message)
        session, owner = declaring_setup(direct)
        session.invoke(ModelInvocationRequest('declared adapter controls'), owner)
        bound = [e for e in owner.ledger.events if e.get('action') == 'harness_layering_bound']
        check('the_bound_record_names_the_adapter_native_controls',
              bound and bound[0]['adapter_native_controls'] == ['planning_and_continuation'])
        refuses('an_unknown_native_control_name_is_refused_in_capabilities',
                lambda: HarnessExecutionCapabilities(native_controls=('mind_reading',)))
        check('capabilities_without_native_controls_keep_their_encoding',
              HarnessExecutionCapabilities().to_dict()['record_type'] == 'harness_execution_capabilities/v1'
              and 'native_controls' not in HarnessExecutionCapabilities().to_dict()
              and HarnessExecutionCapabilities(native_controls=('goal_management',)).to_dict()['record_type']
              == 'harness_execution_capabilities/v2')
        other_policy = HarnessFallbackPolicy(('first', 'second'), (HarnessFailureKind.UNAVAILABLE,))
        refuses('a_layered_binding_checked_against_another_outer_policy_is_refused',
                lambda: layered_setup(LayeredHarnessBinding('assignment:layering-check',
                    WrapperComposition('direct', 'first'), everything, (), other_policy)))
        refuses('a_layered_binding_for_another_harness_is_refused',
                lambda: layered_setup(LayeredHarnessBinding('assignment:layering-check',
                    WrapperComposition('direct', 'second'), everything, (),
                    HarnessFallbackPolicy(('second', 'first'), ()))))
        # A host can declare the same binding in a file; the loader reads it
        # under the run's own outer policy and assignment reference.
        import json as _json
        from .harness_configuration import load_layered_binding
        declaration = Path(directory) / 'layering.json'
        declaration.write_text(_json.dumps({
            'schema_version': 1, 'initial': direct.initial.to_dict(),
            'fallbacks': [item.to_dict() for item in direct.fallbacks],
            'control_policy': direct.control_policy.to_dict()}), encoding='utf-8')
        loaded = load_layered_binding(str(declaration),
                                      assignment_ref='assignment:layering-check',
                                      fallback_policy=policy)
        check('a_layering_declaration_file_loads_to_the_same_binding',
              loaded.content_digest == direct.content_digest)
        session, owner = layered_setup(loaded)
        check('a_loaded_declaration_runs_and_is_recorded_like_the_typed_one',
              session.invoke(ModelInvocationRequest('declared in a file'), owner) == '{"answer":1}'
              and [e for e in owner.ledger.events if e.get('action') == 'harness_layering_bound'][0]
              ['layering_digest'] == direct.content_digest)
        declaration.write_text(_json.dumps({
            'schema_version': 1, 'initial': direct.initial.to_dict(),
            'fallbacks': [], 'control_policy': direct.control_policy.to_dict(),
            'fallback_policy': policy.to_dict()}), encoding='utf-8')
        refuses('a_declaration_cannot_carry_its_own_outer_policy',
                lambda: load_layered_binding(str(declaration),
                                             assignment_ref='assignment:layering-check',
                                             fallback_policy=policy))

        result = HarnessRunResult('check', 'first', 'failed', error_code='adapter_reported_failure')
        from .external_harness import HarnessToolEvent
        result.tool_events = (HarnessToolEvent('unexpected', 'unknown', 'write'),)
        decision = assess_harness_attempt(policy, 0, result, ())
        check('possible_effect_is_not_silently_replayed',
              not decision.next_harness_id and decision.reason == 'unexpected_effects_require_reconciliation')
        result.tool_events = ()
        decision = assess_harness_attempt(policy, 0, result,
            (ModelGatewayResult(error_code='unauthorized_route'),))
        check('authority_failure_is_not_a_reason_to_broaden_permissions',
              not decision.next_harness_id and decision.reason == 'provider_or_shared_gateway_failure')
    return {'tests':tests, 'passed':sum(t['passed'] for t in tests), 'total':len(tests),
            'all_passed':all(t['passed'] for t in tests)}
