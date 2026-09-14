"""Canonical model-session integration checks for harness realizations.

These tests broker real fixture-gateway attempts inside real Loops and check
the resulting history. They do not launch a CLI or call an external provider.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile

from .external_harness import HarnessAdapterInfo, HarnessModelCall, HarnessRegistry, HarnessRunResult
from .harness_execution_contracts import HarnessExecutionCapabilities
from .harness_semantic import HarnessSemanticBinding


def run_checks():
    from ..code_nodes.solution_model_port import (
        FixtureModelExecutionRequest, ModelInvocationRequest, SolutionModelError,
        fixture_model_execution)
    from ..loop.recursive_loop import Loop
    from .context_artifacts import ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec
    from .run_history import RunHistory
    tests = []

    def check(name, good, detail=''):
        tests.append({'test': name, 'passed': bool(good), 'detail': detail})

    class FixtureHarness:
        def __init__(self):
            self.invocations = []
            self.results = []

        def info(self):
            return HarnessAdapterInfo('semantic_fixture', '1.0.0', 'fixture', available=True,
                execution_capabilities=HarnessExecutionCapabilities(supported_features=('model_routes',)))

        def run(self, request, services):
            self.invocations.append(request)
            client = services.runtime_binding.runtime_object
            response = client({'model': request.model_id, 'messages': [
                {'role': 'user', 'content': request.input_data['prompt']}]})
            calls = tuple(HarnessModelCall(
                attempt.provider, attempt.model, attempt.provider_ok,
                input_tokens=attempt.input_tokens, output_tokens=attempt.output_tokens,
                gateway_loop_id=attempt.loop_id, route_id=attempt.route)
                for result in client.results for attempt in result.physical_provider_attempts)
            result = HarnessRunResult(request.request_id, request.harness_id, 'completed',
                output=response['choices'][0]['message']['content'], model_calls=calls,
                adapter_version='1.0.0', provider_id=request.provider_id, model_id=request.model_id)
            self.results.append(result)
            return result

    with tempfile.TemporaryDirectory(prefix='semantic-harness-check-') as directory:
        manager = ContextArtifactManager(ContextArtifactServices(
            ContextArtifactStore(ContextArtifactStoreSpec(directory))))
        adapter = FixtureHarness()
        registry = HarnessRegistry((adapter,))
        binding = HarnessSemanticBinding('semantic_fixture', registry, str(Path(directory) / 'work'))
        authority = fixture_model_execution(FixtureModelExecutionRequest(
            answers=('{"answer":1}', '{"answer":2}'), max_model_calls=2))
        selected = replace(authority, harness=binding)
        refused = False
        try:
            selected.start_session()
        except SolutionModelError as error:
            refused = error.error_code == 'harness_artifacts_required'
        check('missing_artifact_authority_refuses_before_a_session_starts', refused)
        session = selected.start_session(artifact_store=manager)
        owner = Loop('canonical harness session owner')
        first = session.invoke(ModelInvocationRequest('first packet', system='first system'), owner)
        second = session.invoke(ModelInvocationRequest('second packet'), owner)
        check('every_semantic_call_uses_selected_harness', len(adapter.invocations) == 2
              and (first, second) == ('{"answer":1}', '{"answer":2}'))
        check('harness_packet_preserves_original_system_and_prompt',
              adapter.invocations[0].input_data['system'] == 'first system'
              and adapter.invocations[0].input_data['prompt'] == 'first packet')
        policies = [item.input_data.get('outcome_vector_policy')
                    for item in adapter.invocations]
        controls = [item.metadata.get('owning_practitioner_control')
                    for item in adapter.invocations]
        check('every_harness_realization_receives_the_owning_vector_policy',
              all(policy.get('continue_while_safe_authorized_work_remains') is True
                  and policy.get('evaluate_private_reasoning') is False
                  for policy in policies)
              and all(control.get('adapter_may_self_accept') is False
                      and control.get('outcome_vector_policy_digest')
                      for control in controls))
        harness_summaries = [
            item.get('external_harness_result')
            for item in owner.ledger.events
            if isinstance(item.get('external_harness_result'), dict)]
        check('harness_completion_only_sets_the_mechanical_execution_axis',
              len(harness_summaries) == 2
              and all(item['outcome_vector']['execution_succeeded'] is True
                      and item['outcome_vector'][
                          'expected_output_satisfied'] is None
                      and item['outcome_vector']['task_outcome'] is None
                      for item in harness_summaries))
        check('shared_session_charges_actual_gateway_calls', session.calls_used == 2
              and all(result.physical_model_calls == 1 for result in session.results))
        def _self_test_history():
            return RunHistory.from_ledger(owner.ledger.events, run_id='semantic-harness-check')
        history = _self_test_history()
        history.commit()
        invocations = [event for event in history.event_log if event.event_type == 'model_invocation']
        check('brokered_gateway_events_are_not_double_imported', len(invocations) == 2)
        check('semantic_identities_survive_the_harness_boundary',
              len({result.semantic_call_id for result in session.results}) == 2
              and all(result.semantic_call_id for result in session.results))
        from types import SimpleNamespace
        from .stage_assistance_runtime_records import physical_exposure, StageAssistanceRuntimeRecordError
        first_result = session.results[0]
        observation = SimpleNamespace(semantic_call_id=first_result.semantic_call_id,
            owner_loop_id=owner.loop_id, occurrence_id='fixture-stage')
        snapshot = {'prompt_digest': first_result.prompt_digest, 'assembly_id': 'fixture-assembly'}
        exposure = physical_exposure(observation, snapshot, packet_digest='a'*64,
            gateway_result=first_result, format_attempt=1, transport_attempt=1)
        check('stage_exposure_preserves_both_engine_and_actual_prompt_identities',
              exposure['prompt_digest'] == first_result.prompt_digest
              and exposure['physical_prompt_digests'][0] != first_result.prompt_digest
              and len(exposure['prompt_envelopes']) == 1)
        for label, changed_result in (
                ('missing', replace(first_result, prompt_envelopes=())),
                ('wrong_target', replace(first_result, prompt_envelopes=(replace(
                    first_result.prompt_envelopes[0], envelope_prompt_digest='b'*64),))),
                ('untyped', replace(first_result, prompt_envelopes=(
                    first_result.prompt_envelopes[0].summary(),)))):
            denied = False
            try:
                physical_exposure(observation, snapshot, packet_digest='a'*64,
                    gateway_result=changed_result, format_attempt=1, transport_attempt=1)
            except StageAssistanceRuntimeRecordError:
                denied = True
            check('envelope_' + label + '_cannot_bypass_stage_identity', denied)
        exhausted = False
        try:
            session.invoke(ModelInvocationRequest('third packet'), owner)
        except SolutionModelError as error:
            exhausted = error.error_code == 'model_call_budget_exhausted'
        check('whole_run_budget_blocks_before_another_harness_dispatch', exhausted
              and len(adapter.invocations) == 2)
        registry.register(FixtureHarness(), replace=True)
        changed = False
        try:
            binding.invoke(adapter.invocations[0], gateway=authority.gateway, parent=owner,
                           artifact_store=manager)
        except ValueError:
            changed = True
        check('replacement_adapter_requires_a_new_binding', changed)
        from .harness_semantic import HarnessGatewayClient
        from .model_capabilities import ModelOutputCapability
        from .model_gateway import ModelGatewayRequest, ModelGatewayConfig
        fitting = HarnessGatewayClient(
            None, ModelGatewayRequest(
                'fit', config=ModelGatewayConfig(
                    purpose='counted_generation')), None, 'probe-model',
            window_tokens=200000,
            output_capability=ModelOutputCapability(
                1048576, 'probe source',
                endpoint='https://provider.example/v1'),
            route_provider='probe', route_model='probe-model',
            route_name='custom.probe')
        fitted = fitting._fit_window(ModelGatewayRequest(
            'x' * 4000, config=ModelGatewayConfig(purpose='counted_generation'),
            semantic_call_id='semantic-fit-1'))
        allocation = fitted.config.output_allocation
        check('fit_window_allocates_window_minus_measured_input',
              allocation is not None
              and allocation.requested_tokens == 200000 - (4000 + 3) // 4
              and allocation.decision_ref == 'semantic-fit-1'
              and allocation.provider_id == 'probe')
        small = fitting._fit_window(ModelGatewayRequest(
            'y', config=ModelGatewayConfig(
                purpose='counted_generation',
                output_allocation=allocation)))
        check('explicit_allocation_is_never_overwritten',
              small.config.output_allocation is allocation)
        try:
            fitting._fit_window(ModelGatewayRequest(
                'z' * 800004, config=ModelGatewayConfig(
                    purpose='counted_generation')))
            full = False
        except ValueError:
            full = True
        check('prompt_filling_the_window_is_refused_not_truncated', full)

    # A fallback order may name every registered harness on a host that has
    # installed only some of them: an uninstalled alternative registers as
    # unavailable, the failure kind the policy already knows, instead of
    # refusing the whole assignment before any attempt.
    import json as _json
    import os as _os
    from .harness_configuration import (UnavailableHarnessAdapter, load_harness_binding,
                                        load_harness_fallback_binding)
    from .harness_fallback import HarnessFailureKind, HarnessFallbackPolicy
    from .harness_process import HarnessProcessError
    with tempfile.TemporaryDirectory(prefix='harness-availability-') as directory:
        root = Path(directory).resolve()
        software = root / 'software' / 'aider' / 'lib'
        software.mkdir(parents=True)
        executable = root / 'aider-bin'
        executable.write_text('#!/bin/sh\nexit 0\n')
        _os.chmod(executable, 0o755)
        installed = root / 'aider.json'
        installed.write_text(_json.dumps({
            'schema_version': 1, 'harness_id': 'aider', 'package_version': '0.86.2', 'style': 'aider',
            'command_prefix': [str(executable)], 'read_only_paths': [str(software)]}))
        absent = root / 'codex.json'
        absent.write_text(_json.dumps({
            'schema_version': 1, 'harness_id': 'codex', 'package_version': '0.36.0', 'style': 'codex',
            'command_prefix': [str(root / 'absent-codex')], 'read_only_paths': [str(root / 'software' / 'codex' / 'lib')]}))
        malformed = root / 'broken.json'
        malformed.write_text(_json.dumps({'schema_version': 1, 'harness_id': 'kilo'}))
        common = dict(work_root=str(root / 'work'), socket_directory=str(root / 'hs'))
        refused = False
        try:
            load_harness_binding(str(absent), expected_id='codex', **common)
        except HarnessProcessError:
            refused = True
        tolerated = load_harness_binding(str(absent), expected_id='codex', allow_unavailable=True, **common)
        adapter = tolerated.registry.get('codex')
        info = adapter.info()
        check('an_uninstalled_harness_refuses_by_default_and_registers_as_unavailable_when_allowed',
              refused and isinstance(adapter, UnavailableHarnessAdapter) and info.available is False
              and info.availability_reason == 'executable_unavailable'
              and info.adapter_version.startswith('unavailable+') and info.package_version == '0.36.0',
              info.availability_reason)
        still_refused = False
        try:
            load_harness_binding(str(malformed), expected_id='kilo', allow_unavailable=True, **common)
        except (ValueError, HarnessProcessError):
            still_refused = True
        check('a_malformed_declaration_refuses_even_when_unavailability_is_allowed', still_refused)
        policy = HarnessFallbackPolicy(('aider', 'codex'), (HarnessFailureKind.UNAVAILABLE,))
        order = load_harness_fallback_binding((str(installed), str(absent)), policy=policy,
                                              allow_unavailable=True, **common)
        check('a_fallback_order_keeps_an_uninstalled_alternative_as_unavailable',
              order.harness_id == 'aider' and order.registry.get('aider').info().available is True
              and order.registry.get('codex').info().available is False
              and order.fallback_policy is policy)
        order_refused = False
        try:
            load_harness_fallback_binding((str(installed), str(absent)), policy=policy, **common)
        except HarnessProcessError:
            order_refused = True
        check('the_same_order_refuses_without_the_allowance', order_refused)
    return {'tests': tests, 'passed': sum(t['passed'] for t in tests),
            'total': len(tests), 'all_passed': all(t['passed'] for t in tests)}
