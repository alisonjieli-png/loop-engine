"""Offline controls for governed selection and independent response obligations.

Uses explicit fixture providers and adapters to test canonical runtime paths.
These controls do not establish real provider integration or learned task quality.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile

from .harness_selection_records import (
    HarnessEvidenceReview,HarnessSelectionPolicy,HarnessSelectionScope,
    HarnessTrialEvidence,ReviewedHarnessEvidence,content_digest,response_contract_digest)
from .harness_response_evaluation import HarnessResponseEvaluator,ResponseEvaluationVerdict


def _checks():
    tests=[]
    def check(name,good):tests.append({'test':name,'passed':bool(good)})
    def refuses(name,action):
        try:action()
        except (ValueError,TypeError,RuntimeError):check(name,True)
        else:check(name,False)
    return tests,check,refuses


def _summary(tests):
    return {'tests':tests,'passed':sum(x['passed'] for x in tests),'total':len(tests),
            'all_passed':all(x['passed'] for x in tests)}


def _scope():
    return HarnessSelectionScope(operation_contract_ref='fixture.answer/v1',
        response_contract_digest='a'*64,profile_ref='practitioner.solver@1.0.0',
        resource_profile_digest='b'*64,execution_settings_digest='c'*64,owning_definition_digest='d'*64)


def _reviewed(identity,scope,successes,tokens,*,version='1.0.0',population='e'*64,
              provider='fixture',model='fixture-model',suffix=''):
    trial=HarnessTrialEvidence(trial_id='fixture-trial-'+identity+suffix,
        harness_id=identity,adapter_version=version,provider_id=provider,model_id=model,
        scope_digest=scope.digest,population_digest=population,evaluator_ref='fixture.evaluator/v1',
        evaluator_digest='f'*64,subject_digest=content_digest(identity+suffix),
        history_ref='fixture-history:'+identity+suffix,history_digest=content_digest('history:'+identity+suffix),
        successes=successes,observations=4,physical_model_calls=1,
        input_tokens=tokens,output_tokens=0 if tokens is not None else None,elapsed_seconds=None)
    review=HarnessEvidenceReview(trial.digest,'independent-fixture-reviewer',
        'fixture-review:'+identity+suffix,content_digest(trial.to_dict()))
    return ReviewedHarnessEvidence(trial,review)


def run_self_test_checks():
    from .external_harness import HarnessAdapterInfo
    from .harness_execution_contracts import HarnessExecutionCapabilities,HarnessExecutionRequirements
    from .harness_selection import select_harness
    tests,check,refuses=_checks();scope=_scope()
    infos=tuple(HarnessAdapterInfo(name,'1.0.0','explicit-offline-fixture',available=True,
        execution_capabilities=HarnessExecutionCapabilities(supported_features=('model_routes',)))
        for name in ('first','second','third'))
    evidence=tuple(_reviewed(name,scope,quality,tokens)
        for name,quality,tokens in (('first',2,5),('second',4,30),('third',4,None)))
    policy=HarnessSelectionPolicy(scope.resource_profile_digest,evidence,1)
    restored=HarnessSelectionPolicy.from_dict(json.loads(json.dumps(policy.to_dict())))
    check('reviewed_policy_roundtrip_preserves_exact_identity',restored.digest==policy.digest)
    changed_policy=policy.to_dict();changed_policy['minimum_records']=2
    refuses('changed_serialized_policy_is_refused',lambda:HarnessSelectionPolicy.from_dict(changed_policy))
    def select(p=policy,s=scope,i=infos):
        return select_harness(p,s,i,provider_id='fixture',model_id='fixture-model')
    decision=select()
    check('verified_outcomes_rank_before_token_cost',decision.ordered_harness_ids==('second','third','first'))
    assessments=json.loads(decision.assessments_json)
    check('unknown_tokens_are_not_zero',assessments[2]['mean_tokens_per_trial'] is None)
    check('selection_preserves_exact_evidence_references',len(decision.evidence_refs)==3 and decision.scope_digest==scope.digest)
    check('selection_does_not_claim_task_acceptance',decision.to_dict()['task_accepted'] is False)
    missing=select(replace(policy,evidence=evidence[:1]))
    check('missing_arms_preserve_the_configured_order',missing.ordered_harness_ids==('first','second','third')
          and missing.reason=='insufficient_matched_reviewed_evidence')
    check('unavailable_best_harness_is_excluded',select(i=(infos[0],replace(infos[1],available=False),infos[2])).ordered_harness_ids[0]=='third')
    requirement=replace(scope,requirements=HarnessExecutionRequirements(required_features=('tool_refs',)))
    check('unsupported_mechanics_refuse_before_execution',select(s=requirement).ordered_harness_ids==())
    for name,changed in (
        ('different_resources',replace(scope,resource_profile_digest='1'*64)),
        ('different_schema',replace(scope,response_contract_digest='2'*64)),
        ('different_settings',replace(scope,execution_settings_digest='3'*64)),
        ('different_definition',replace(scope,owning_definition_digest='4'*64))):
        check(name+'_cannot_reuse_evidence',select(s=changed).reason=='insufficient_matched_reviewed_evidence')
    changed_version=(replace(infos[0],adapter_version='2.0.0'),*infos[1:])
    check('changed_adapter_version_invalidates_the_comparison',select(i=changed_version).reason=='insufficient_matched_reviewed_evidence')
    unrelated=_reviewed('first',scope,4,1,population='5'*64)
    check('unmatched_populations_are_not_pooled',select(replace(policy,evidence=(unrelated,*evidence[1:]))).reason=='insufficient_matched_reviewed_evidence')
    rejected=replace(evidence[1],review=replace(evidence[1].review,decision='rejected'))
    check('rejected_review_cannot_rank_a_harness',select(replace(policy,evidence=(evidence[0],rejected,evidence[2]))).reason=='insufficient_matched_reviewed_evidence')
    wrong_provider=_reviewed('first',scope,4,1,provider='other')
    check('different_provider_evidence_is_excluded',select(replace(policy,evidence=(wrong_provider,*evidence[1:]))).reason=='insufficient_matched_reviewed_evidence')
    wrong_model=_reviewed('first',scope,4,1,model='other-model')
    check('different_model_evidence_is_excluded',select(replace(policy,evidence=(wrong_model,*evidence[1:]))).reason=='insufficient_matched_reviewed_evidence')
    refuses('changed_trial_cannot_reuse_an_approval',lambda:replace(evidence[0],trial=replace(evidence[0].trial,successes=4)))
    refuses('duplicates_cannot_inflate_trial_count',lambda:replace(policy,evidence=(evidence[0],evidence[0])))
    def reissued(reviewed,trial_id,**changes):
        trial=replace(reviewed.trial,trial_id=trial_id,**changes)
        return ReviewedHarnessEvidence(trial,HarnessEvidenceReview(trial.digest,'independent-fixture-reviewer',
            'fixture-review:'+trial_id,content_digest(trial.to_dict())))
    refuses('one_history_reference_cannot_count_as_several_trials',
            lambda:replace(policy,evidence=(*evidence,reissued(evidence[0],'fixture-trial-first-copy'))))
    repeated=reissued(evidence[0],'fixture-trial-first-again',history_ref='fixture-history:first-again',
                      history_digest=content_digest('history:first-again'),successes=4)
    again=select(replace(policy,evidence=(*evidence,repeated)))
    check('distinct_repeated_trials_of_one_subject_still_count',again.reason=='ranked_matched_reviewed_evidence'
          and json.loads(again.assessments_json)[0]['matching_reviewed_records']==2)
    refuses('booleans_are_not_measurement_counts',lambda:replace(evidence[0].trial,observations=True))
    refuses('negative_usage_is_not_admitted',lambda:replace(evidence[0].trial,input_tokens=-1))
    refuses('nonfinite_elapsed_is_not_admitted',lambda:replace(evidence[0].trial,elapsed_seconds=float('nan')))
    refuses('unknown_selection_objective_is_refused',lambda:replace(policy,objective='model_confidence'))
    refuses('unversioned_operation_contract_is_refused',lambda:replace(scope,operation_contract_ref='an arbitrary label'))
    second_scope=replace(scope,resource_profile_digest='6'*64)
    more=tuple(_reviewed(name,second_scope,quality,tokens,suffix='-other')
               for name,quality,tokens in (('first',4,10),('second',1,30),('third',1,50)))
    mixed=replace(policy,evidence=(*evidence,*more))
    check('different_assignments_can_select_different_harnesses',select(mixed,scope).ordered_harness_ids[0]=='second'
          and select(mixed,second_scope).ordered_harness_ids[0]=='first')
    _integration_selection_checks(tests)
    return _summary(tests)


class _FixtureHarness:
    """Offline brokered adapter: one broker call per attempt, no native tools."""
    def __init__(self,name):self.name=name;self.requests=[]
    def info(self):
        from .external_harness import HarnessAdapterInfo
        from .harness_execution_contracts import HarnessExecutionCapabilities
        return HarnessAdapterInfo(self.name,'1.0.0','explicit-offline-fixture',available=True,
            execution_capabilities=HarnessExecutionCapabilities(supported_features=('model_routes',)))
    def run(self,request,services):
        from .external_harness import HarnessModelCall,HarnessRunResult
        self.requests.append(request);client=services.runtime_binding.runtime_object;output=None
        try:output=client({'model':request.model_id,'messages':[{'role':'user','content':request.input_data['prompt']}]})['choices'][0]['message']['content']
        except ValueError:pass
        calls=tuple(HarnessModelCall(a.provider,a.model,a.provider_ok,input_tokens=a.input_tokens,
            output_tokens=a.output_tokens,error_code=a.error_code,gateway_loop_id=a.loop_id,route_id=a.route)
            for r in client.results for a in r.physical_provider_attempts)
        return HarnessRunResult(request.request_id,self.name,'completed' if output else 'failed',
            output=output,error_code='' if output else 'adapter_reported_failure',model_calls=calls,
            adapter_version='1.0.0',provider_id=request.provider_id,model_id=request.model_id)


def _two_route_authority(*,evaluators=(),harness=None,allow_evaluator_route_failover=False):
    """Two providers on two routes: alpha answers 41, beta answers 42."""
    from ..code_nodes.solution_model_port import ModelExecution
    from .model_capabilities import ModelOutputCapability
    from .model_gateway import ModelGateway,ModelGatewayConfig,ProviderSpec
    from .model_routes import ModelRoute,RoutePolicy
    from .ollama_client import ChatResult
    def adapter(name,answer):
        class Adapter:
            DEFAULT_MODEL=name+'-model'
            @staticmethod
            def output_capability_for(model=''):return ModelOutputCapability(64,'offline fixture contract')
            @staticmethod
            def chat_maxout(prompt,**kwargs):return ChatResult(answer,name+'-model',prompt_tokens=2,eval_tokens=3,ok=True)
            @staticmethod
            def verify(model=''):return {'ok':True}
            @staticmethod
            def live_models():return [name+'-model']
        return Adapter
    gateway=ModelGateway(providers=(
            ProviderSpec('alpha',adapter('alpha','{"answer":41}'),'offline_fixture','not_required',locality='local'),
            ProviderSpec('beta',adapter('beta','{"answer":42}'),'offline_fixture','not_required',locality='local')),
        routes=(ModelRoute('fx.alpha','alpha','alpha-model','local',purposes=('counted_generation',)),
                ModelRoute('fx.beta','beta','beta-model','local',purposes=('counted_generation',))),
        policy=RoutePolicy(allow_local_counted_generation=True))
    config=ModelGatewayConfig(route_names=('fx.alpha','fx.beta'),allowed_localities=('local',),
                              allow_failover=True,
                              allow_evaluator_route_failover=allow_evaluator_route_failover)
    return ModelExecution(gateway,config,max_model_calls=4,response_evaluators=tuple(evaluators),harness=harness)


def _fixture_runtime(directory,answers,*,switch_on=(),evaluators=(),policy=None):
    from ..code_nodes.solution_model_port import FixtureModelExecutionRequest,fixture_model_execution
    from .external_harness import HarnessRegistry
    from .harness_fallback import HarnessFallbackPolicy
    from .harness_semantic import HarnessSemanticBinding
    from .context_artifacts import ContextArtifactManager,ContextArtifactServices,ContextArtifactStore,ContextArtifactStoreSpec
    from ..loop.recursive_loop import Loop
    manager=ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(ContextArtifactStoreSpec(directory))))
    adapters=(_FixtureHarness('first'),_FixtureHarness('second'))
    binding=HarnessSemanticBinding('first',HarnessRegistry(adapters),str(Path(directory)/'work'),artifact_store=manager,
        fallback_policy=HarnessFallbackPolicy(('first','second'),tuple(switch_on)),selection_policy=policy)
    authority=fixture_model_execution(FixtureModelExecutionRequest(answers=tuple(answers),max_model_calls=8))
    authority=replace(authority,harness=binding,response_evaluators=tuple(evaluators),config=replace(authority.config,max_route_attempts=None))
    return adapters,authority,manager,Loop('governed selection fixture')


def _request(owner,*,evaluation_ref='',policy=None):
    from ..code_nodes.solution_model_port import ModelInvocationRequest
    from .observation_expectations import ObservationExpectation
    base=ModelInvocationRequest('Compute the requested value without changing authority.',semantic_call_id='fixture-assignment')
    expected=ObservationExpectation('fixture-expectation',base.semantic_call_id,base.exact_input_digest,
        'fixture.answer/v1','{"type":"object","properties":{"answer":{"type":"integer"}},"required":["answer"]}')
    return replace(base,response_expectation=expected,response_admission_policy=policy,response_evaluation_ref=evaluation_ref)


def _integration_selection_checks(tests):
    from .harness_fallback import HarnessFailureKind
    from ..code_nodes.solution_model_port import SolutionModelError
    with tempfile.TemporaryDirectory(prefix='harness-selection-check-') as directory:
        adapters,authority,manager,owner=_fixture_runtime(directory,('{"answer":42}',),switch_on=tuple(HarnessFailureKind))
        request=_request(owner)
        scope=HarnessSelectionScope(operation_contract_ref='fixture.answer/v1',
            response_contract_digest=response_contract_digest(request.response_expectation,None),
            profile_ref=owner.definition.role_profile_id+'@'+owner.definition.role_profile_version,
            resource_profile_digest='7'*64,
            execution_settings_digest=content_digest({'temperature':request.temperature,'output_allowance':None,
                'gateway_thinking_power':authority.config.thinking_power,'loop_thinking_power':authority.llm_thinking_power,
                'evaluation_implementation':None,'evaluation_qualification':None}),
            owning_definition_digest=owner.definition.content_digest)
        route=authority.gateway._routes(authority.config)[0][0]
        evidence=tuple(_reviewed(name,scope,quality,tokens,provider=route.provider,model=route.model)
                       for name,quality,tokens in (('first',1,2),('second',4,10)))
        binding=replace(authority.harness,selection_policy=HarnessSelectionPolicy(scope.resource_profile_digest,evidence,1))
        session=replace(authority,harness=binding).start_session(artifact_store=manager)
        text=session.invoke(request,owner)
        tests.append({'test':'actual_model_session_uses_the_ranked_harness','passed':text=='{"answer":42}'
            and not adapters[0].requests and len(adapters[1].requests)==1 and session.calls_used==1})
        tests.append({'test':'selection_is_a_classified_loop_in_history','passed':any(
            e.get('action')=='harness_selection_assessed' and e.get('selection_loop_id')
            for e in owner.ledger.events)})
        try:session.invoke(replace(request,temperature=0.0,harness_selection_scope=scope),owner)
        except SolutionModelError as error:refused=error.error_code=='harness_selection_scope_mismatch'
        else:refused=False
        tests.append({'test':'stale_settings_scope_refuses_without_another_model_call','passed':refused and session.calls_used==1})


def run_response_evaluation_checks():
    from ..code_nodes.solution_model_port import SolutionModelError
    from .harness_fallback import HarnessFailureKind
    tests,check,refuses=_checks()
    with tempfile.TemporaryDirectory(prefix='response-evaluation-check-') as directory:
        adapters,authority,manager,owner=_fixture_runtime(directory,('{"answer":41}','{"answer":42}'),
            switch_on=(HarnessFailureKind.SEMANTIC_REJECTED,))
        request=_request(owner,evaluation_ref='fixture.arithmetic/v1')
        def evaluate(text):
            return (ResponseEvaluationVerdict('passed') if json.loads(text)['answer']==42
                    else ResponseEvaluationVerdict('rejected',('answer_incorrect',)))
        evaluator=HarnessResponseEvaluator(contract_ref='fixture.arithmetic/v1',implementation_digest='a'*64,
            qualification_ref='fixture-negative-and-positive-controls',qualification_digest='b'*64,
            subject_contract_ref=request.response_expectation.output_contract_ref,
            subject_contract_digest=response_contract_digest(request.response_expectation,None),evaluate=evaluate)
        session=replace(authority,response_evaluators=(evaluator,)).start_session(artifact_store=manager)
        result=session.invoke(request,owner)
        check('valid_but_wrong_response_reaches_the_next_permitted_harness',result=='{"answer":42}' and session.calls_used==2)
        check('semantic_rejection_and_success_are_both_retained',
            [e.status for e in session.results[-1].response_evaluations]==['rejected','passed'])
        check('semantic_recovery_is_distinct_from_structural_repair',any(e.get('action')=='harness_attempt_assessed'
            and e.get('decision')=='semantic_response_rejected' for e in owner.ledger.events))
        check('verifier_uses_a_separate_loop',all(e.verifier_loop_id!=owner.loop_id for e in session.results[-1].response_evaluations))
        check('evaluated_results_have_a_versioned_encoding',session.results[-1].to_dict()['record_type']=='model_gateway_result/v2')
        check('response_evaluation_does_not_accept_the_whole_task',all(e.to_dict()['task_accepted'] is False for e in session.results[-1].response_evaluations))
        check('no_tool_or_skill_authority_is_added',all(not a.requests[0].tool_refs and not a.requests[0].skill_refs for a in adapters))
    for label,callback,expected_code,allowed in (
        ('unpermitted_semantic_failure',evaluate,'semantic_response_rejected',()),
        ('inconclusive_verification',lambda text:ResponseEvaluationVerdict('inconclusive',('missing_evidence',)),
         'response_evaluation_inconclusive',(HarnessFailureKind.SEMANTIC_REJECTED,)),
        ('malformed_verifier_result',lambda text:True,'response_evaluation_inconclusive',(HarnessFailureKind.SEMANTIC_REJECTED,))):
        with tempfile.TemporaryDirectory(prefix='response-refusal-check-') as directory:
            adapters,authority,manager,owner=_fixture_runtime(directory,('{"answer":41}','{"answer":42}'),switch_on=allowed)
            bound=replace(evaluator,evaluate=callback)
            session=replace(authority,response_evaluators=(bound,)).start_session(artifact_store=manager)
            request=_request(owner,evaluation_ref=bound.contract_ref)
            try:session.invoke(request,owner)
            except SolutionModelError as error:refused=error.error_code==expected_code
            else:refused=False
            check(label+'_stops_after_the_observed_call',refused and session.calls_used==1 and not adapters[1].requests)
            check(label+'_retains_known_accounting',not session.accounting_uncertain)
    refuses('finding_codes_cannot_copy_response_bodies',lambda:ResponseEvaluationVerdict('rejected',('private text with spaces',)))
    refuses('unversioned_evaluator_is_refused',lambda:replace(evaluator,contract_ref='a confidence label'))
    with tempfile.TemporaryDirectory(prefix='missing-evaluator-check-') as directory:
        adapters,authority,manager,owner=_fixture_runtime(directory,('{"answer":42}',))
        session=authority.start_session(artifact_store=manager)
        try:session.invoke(_request(owner,evaluation_ref='not.installed/v1'),owner)
        except SolutionModelError as error:refused=error.error_code=='response_evaluator_unavailable'
        else:refused=False
        check('missing_evaluator_refuses_before_provider_dispatch',refused and session.calls_used==0 and not adapters[0].requests)
    _two_route_evaluation_checks(tests,check)
    return _summary(tests)


def _two_route_evaluation_checks(tests,check):
    """An evaluator's verdict never spends a call on another route by itself."""
    from ..code_nodes.solution_model_port import ModelInvocationRequest,SolutionModelError
    from ..loop.recursive_loop import Loop
    from .observation_expectations import ObservationExpectation
    def two_route_request(call_id):
        base=ModelInvocationRequest('Compute the requested value.',semantic_call_id=call_id)
        expected=ObservationExpectation('exp-'+call_id,call_id,base.exact_input_digest,'fixture.answer/v1',
            '{"type":"object","properties":{"answer":{"type":"integer"}},"required":["answer"]}')
        return replace(base,response_expectation=expected,response_evaluation_ref='fixture.arithmetic/v1'),expected
    def bound_evaluator(expected,callback):
        return HarnessResponseEvaluator(contract_ref='fixture.arithmetic/v1',implementation_digest='a'*64,
            qualification_ref='fixture-negative-and-positive-controls',qualification_digest='b'*64,
            subject_contract_ref=expected.output_contract_ref,
            subject_contract_digest=response_contract_digest(expected,None),evaluate=callback)
    def rejecting(text):
        return (ResponseEvaluationVerdict('passed') if json.loads(text)['answer']==42
                else ResponseEvaluationVerdict('rejected',('answer_incorrect',)))
    def inconclusive(text):
        return (ResponseEvaluationVerdict('passed') if json.loads(text)['answer']==42
                else ResponseEvaluationVerdict('inconclusive',('missing_evidence',)))
    for label,callback,expected_code in (('rejected',rejecting,'semantic_response_rejected'),
                                         ('inconclusive',inconclusive,'response_evaluation_inconclusive')):
        request,expected=two_route_request('two-route-'+label)
        session=_two_route_authority(evaluators=(bound_evaluator(expected,callback),)).start_session()
        owner=Loop('two route '+label)
        try:session.invoke(request,owner);code=''
        except SolutionModelError as error:code=error.error_code
        result=session.results[-1]
        check('evaluator_'+label+'_verdict_does_not_fail_over_to_another_route',
              code==expected_code and session.calls_used==1
              and [a.provider for a in result.physical_provider_attempts]==['alpha']
              and result.attempts[0].error_code==expected_code
              and any(e.get('action')=='evaluator_verdict_stops_route_failover' for e in owner.ledger.events))
    request,expected=two_route_request('two-route-permitted')
    session=_two_route_authority(evaluators=(bound_evaluator(expected,rejecting),),
                                 allow_evaluator_route_failover=True).start_session()
    owner=Loop('two route permitted')
    text=session.invoke(request,owner)
    check('explicit_permission_allows_evaluator_triggered_route_change',text=='{"answer":42}' and session.calls_used==2
          and [e.status for e in session.results[-1].response_evaluations]==['rejected','passed'])
    check('evaluation_record_binds_the_subject_contract',all(
        e.to_dict()['record_type']=='harness_response_evaluation/v2'
        and e.subject_contract_ref==expected.output_contract_ref
        and e.subject_contract_digest==response_contract_digest(expected,None)
        for e in session.results[-1].response_evaluations))
    seen={}
    def aware(text,context):
        seen['context']=context
        return ResponseEvaluationVerdict('passed')
    request,expected=two_route_request('context-aware')
    session=_two_route_authority(evaluators=(bound_evaluator(expected,aware),)).start_session()
    session.invoke(request,Loop('context aware'))
    context=seen.get('context')
    check('context_aware_evaluator_receives_the_exact_occurrence',context is not None
          and context.input_digest==request.exact_input_digest and context.semantic_call_id=='context-aware'
          and context.subject_contract_ref=='fixture.answer/v1'
          and session.results[-1].response_evaluations[0].context_aware is True)
    with tempfile.TemporaryDirectory(prefix='two-route-harness-check-') as directory:
        from .context_artifacts import ContextArtifactManager,ContextArtifactServices,ContextArtifactStore,ContextArtifactStoreSpec
        from .external_harness import HarnessRegistry
        from .harness_fallback import HarnessFallbackPolicy
        from .harness_semantic import HarnessSemanticBinding
        manager=ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(ContextArtifactStoreSpec(directory))))
        adapters=(_FixtureHarness('first'),_FixtureHarness('second'))
        binding=HarnessSemanticBinding('first',HarnessRegistry(adapters),str(Path(directory)/'work'),artifact_store=manager,
            fallback_policy=HarnessFallbackPolicy(('first','second'),()))
        request,expected=two_route_request('two-route-harness')
        session=_two_route_authority(evaluators=(bound_evaluator(expected,rejecting),),harness=binding).start_session(artifact_store=manager)
        owner=Loop('two route harness')
        try:session.invoke(request,owner);code=''
        except SolutionModelError as error:code=error.error_code
        decisions=[e.get('decision') for e in owner.ledger.events if e.get('action')=='harness_attempt_assessed']
        check('harness_attempt_cannot_change_provider_after_semantic_rejection',
              code=='semantic_response_rejected' and session.calls_used==1 and not adapters[1].requests
              and decisions==['failure_not_permitted_by_policy']
              and [a.provider for a in session.results[-1].physical_provider_attempts]==['alpha'])
