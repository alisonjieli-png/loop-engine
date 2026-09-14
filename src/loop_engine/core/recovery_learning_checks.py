"""Offline checks for candidate-only learning inside a self-improvement Loop.

The provider is explicitly a fixture. These checks establish governed capture,
not the correctness of a lesson or cross-task improvement.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace


def run_self_test_checks():
    from .recovery_learning import capture_recovery_learning
    from .context_artifacts import (ContextArtifactManager,ContextArtifactServices,
        ContextArtifactStore,ContextArtifactStoreSpec,ContextArtifactRef)
    from .semantic_decision import SemanticAutonomyTally
    from ..code_nodes.solution_model_port import FixtureModelExecutionRequest,fixture_model_execution
    from ..loop.recursive_loop import Loop
    tests=[]
    def check(name,passed):tests.append({'test':name,'passed':bool(passed)})
    directive={'record_type':'practitioner_recovery_directive/v1','recovery_round':1,
        'stall_signal':{'code':'RECOVERY_DIAGNOSIS_REQUIRED'},'diagnosis':{'root_causes':[]},
        'selected_proposal_id':'repair-1','route':'repair','reason':'Test the proposed correction',
        'directive':'Use the exact response contract','expected_progress':'A schema-valid proposal'}
    candidate={'disposition':'requires_validation','reason':'A conditional hypothesis needs review',
        'candidate':{'candidate_type':'failure_pattern','content':'Check required fields before a handoff.',
            'applicability':'Responses bound to this schema','contraindications':['Does not establish task correctness'],
            'maturity':'registered','validation_status':'validated'}}
    with tempfile.TemporaryDirectory(prefix='recovery-learning-') as directory:
        manager=ContextArtifactManager(ContextArtifactServices(
            ContextArtifactStore(ContextArtifactStoreSpec(directory))))
        def services(answer,enabled=True):
            session=fixture_model_execution(FixtureModelExecutionRequest(
                answers=(json.dumps(answer),),max_model_calls=1)).start_session(artifact_store=manager)
            return SimpleNamespace(model_session=session,artifacts=manager,run_id='learning-control',
                request=SimpleNamespace(mode='non_deterministic',capture_recovery_learning=enabled),
                semantic_decisions=SemanticAutonomyTally(),selected_intelligence_refs=[])
        s=services(candidate);owner=Loop('learning capture owner')
        result=capture_recovery_learning(directive,s,parent=owner)
        bundle=json.loads(manager.store.get_text(ContextArtifactRef.from_dict(result['artifact_ref'])))
        item=bundle['resource_candidates'][0]
        check('candidate_is_retained_through_the_existing_artifact_store',result['candidate_count']==1
              and bundle['storage_stage']=='run_local_staging')
        check('model_cannot_self_validate_or_promote',item['maturity']=='candidate'
              and item['validation_status']=='unvalidated' and result['active_intelligence_updated'] is False)
        check('capture_is_owned_by_a_classified_self_improvement_loop',
              result['producer_profile']=='practitioner.self_improvement'
              and result['producer_loop_id']!=owner.loop_id)
        check('capture_uses_existing_shared_model_accounting',s.model_session.calls_used==1
              and sum(e.get('event')=='model_led' for e in owner.ledger.events)==1)
        check('candidate_content_is_not_injected_into_active_intelligence',not s.selected_intelligence_refs
              and 'content' not in result and result['improvement_demonstrated'] is False)
        reopened=ContextArtifactStore(ContextArtifactStoreSpec(directory))
        check('candidate_survives_store_reopen',json.loads(reopened.get_text(
            ContextArtifactRef.from_dict(result['artifact_ref'])))==bundle)
        s=services({'disposition':'ephemeral_task_only','reason':'Insufficient evidence to generalize'})
        result=capture_recovery_learning(directive,s,parent=Loop('ephemeral control'))
        check('no_learning_is_an_explicit_valid_outcome',result['candidate_count']==0
              and result['disposition']=='ephemeral_task_only')
        s=services(candidate,False)
        try:capture_recovery_learning(directive,s,parent=Loop('disabled capture control'))
        except ValueError:check('disabled_capture_spends_no_model_call',s.model_session.calls_used==0)
        else:check('disabled_capture_spends_no_model_call',False)
        # A campaign session wraps the in-process one; the contract, not the class, admits it.
        class DelegatingSession:
            def __init__(self,inner):self._inner=inner
            def __getattr__(self,name):return getattr(self._inner,name)
            def invoke(self,request,parent_loop):return self._inner.invoke(request,parent_loop)
        s=services(candidate);s.model_session=DelegatingSession(s.model_session)
        try:wrapped=capture_recovery_learning(directive,s,parent=Loop('wrapped session capture'))
        except TypeError:wrapped={'candidate_count':0}
        check('a_session_from_a_session_factory_can_capture_learning',wrapped['candidate_count']==1
              and s.model_session.calls_used==1)
        s=services(candidate);s.model_session=SimpleNamespace(invoke=s.model_session.invoke,results=[])
        try:capture_recovery_learning(directive,s,parent=Loop('incomplete session capture'))
        except TypeError:check('a_value_without_the_model_session_contract_cannot_capture',True)
        else:check('a_value_without_the_model_session_contract_cannot_capture',False)
    return {'tests':tests,'passed':sum(t['passed'] for t in tests),'total':len(tests),
            'all_passed':all(t['passed'] for t in tests)}
