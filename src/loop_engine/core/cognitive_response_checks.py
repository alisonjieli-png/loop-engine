"""Response-boundary checks for cognitive work in the real Practitioner path.

Exercises deterministic admission, explicit normalization and format repair
using canonical Loops and an offline provider fixture, never live quality claims.
"""
from __future__ import annotations

from dataclasses import replace
import json
import tempfile
from unittest.mock import patch


def self_test():
    from .model_response_admission import (
        ModelResponseAdmissionPolicy, ModelResponseContract, ModelResponseAdmissionRequest,
        admit_model_response_as_loop)
    from .adaptive_practitioner_records import NextActionDecision, ModelStepRequest
    from .observation_expectations import ObservationBinding, ObservationExpectation
    from ..code_nodes.solution_model_port import (
        ModelInvocationRequest, FixtureModelExecutionRequest, fixture_model_execution, SolutionModelError)
    from ..loop.recursive_loop import Loop
    tests=[]
    def check(name, passed):
        tests.append({'test':name,'passed':bool(passed)})
    def refuses(name, fn):
        try: fn()
        except (ValueError, TypeError):check(name,True)
        else:check(name,False)
    contract = NextActionDecision.response_contract(('example.inspect',))
    from typing import get_type_hints
    check('public_invocation_types_resolve_for_schema_consumers',
          'response_admission_policy' in get_type_hints(ModelInvocationRequest))
    from .adaptive_practitioner_acceptance_checks import _run, _success_answers
    answers = list(_success_answers())
    valid = json.loads(answers[1])
    shape = NextActionDecision.response_contract(tuple(valid['actions'][0]['required_capabilities']))
    def admit(value, expected=shape):
        return admit_model_response_as_loop(ModelResponseAdmissionRequest(
            json.dumps(value),expected.contract_ref,expected.content_digest,
            schema=json.loads(expected.schema_json),policy=expected.policy))
    check('complete_action_response_is_admitted',admit(valid).admitted)
    incomplete=json.loads(answers[1]);del incomplete['actions'][0]['budget']
    incomplete['actions'][0]['private_extra_value']='PRIVATE_RESPONSE_CONTROL'
    refused=admit(incomplete)
    check('missing_fields_are_detected_before_the_consumer',not refused.admitted
          and 'schema_required_field_missing:budget' in refused.schema_errors)
    check('feedback_does_not_copy_rejected_values', 'PRIVATE_RESPONSE_CONTROL' not in json.dumps(refused.to_dict()))
    surplus=json.loads(answers[1]);surplus['additional_observation']='compatible extra information'
    check('permitted_extra_information_is_not_discarded',admit(surplus).admitted)
    wrong=json.loads(answers[1]);wrong['actions'][0]['required_capabilities']=['not.registered']
    check('unknown_capability_is_rejected',not admit(wrong).admitted)
    wrong=json.loads(answers[1]);wrong['actions'][0]['confidence']=True
    check('boolean_is_not_a_confidence_number',not admit(wrong).admitted)
    impossible=json.loads(answers[1]);impossible['actions'][0].update(
        action_kind='COMPOSE_SOLUTION',required_capabilities=[])
    check('composition_cannot_request_an_impossible_capability_free_method',not admit(impossible).admitted)
    terminal=json.loads(answers[1]);terminal['actions'][0].update(action_kind='ABSTAIN',required_capabilities=[])
    check('dedicated_control_actions_remain_capability_free',admit(terminal).admitted)
    many={'actions':[valid['actions'][0],valid['actions'][0]]}
    check('multiple_candidates_need_explicit_selection',not admit(many).admitted)
    check('selection_is_not_a_new_runtime_type',admit({**many,'selected_action_index':1}).admitted)
    from .adaptive_practitioner_planning import _planning_response_contract
    method=NextActionDecision.from_mapping(valid['actions'][0])
    expected_method=_planning_response_contract('selected-action',method)
    method_value={'action_id':'selected-action','how_mode':'custom method',
        'act_mode':'run_dag','capability_ref':method.required_capabilities[0],
        'arguments':{},'steps':[],'spawned_tasks':[],'rationale':'Execute the selected method'}
    check('method_accepts_the_selected_action_contract',admit(method_value,expected_method).admitted)
    check('method_cannot_retarget_another_action',not admit({**method_value,'action_id':'other'},expected_method).admitted)
    check('method_cannot_switch_to_an_unselected_capability',not admit({**method_value,'capability_ref':'outside'},expected_method).admitted)
    check('method_telemetry_does_not_change_admission',admit({**method_value,
        'selection_report':{'wanted_but_absent':'an observation'},'operator_gap':None},expected_method).admitted)
    refuses('remote_schema_references_are_refused_before_execution',lambda:ModelResponseContract(
        'bad/v1','{"$ref":"https://example.invalid/schema"}'))
    refuses('duplicate_schema_keys_are_refused',lambda:ModelResponseContract('bad/v1','{"type":"object","type":"string"}'))
    refuses('duplicate_observation_keys_are_refused',lambda:ObservationBinding('operation','a'*64,'{"a":1,"a":2}'))
    check('policy_change_changes_the_contract_identity',shape.content_digest != replace(shape,
        policy=ModelResponseAdmissionPolicy(allowed_strategies=('strict_json',))).content_digest)
    request=ModelStepRequest('decide_next','Choose a bounded action',{},'example',shape)
    check('step_schema_digest_binds_the_enforced_contract',request.output_contract_digest==shape.content_digest)
    base=ModelInvocationRequest('Return an object',semantic_call_id='normalization-control')
    expected=ObservationExpectation('expected',base.semantic_call_id,base.exact_input_digest,
        'response/v1','{"type":"object","required":["answer"]}')
    session=fixture_model_execution(FixtureModelExecutionRequest(
        answers=('```json\n{"answer":1}\n```',),max_model_calls=1)).start_session()
    normalized=replace(base,response_expectation=expected,response_admission_policy=ModelResponseAdmissionPolicy())
    raw=session.invoke(normalized,Loop('explicit normalization control'))
    check('approved_envelope_is_repaired_without_another_model_call',raw.startswith('```json')
          and session.calls_used==1 and session.results[0].response_admissions[0].admitted
          and session.results[0].response_admissions[0].strategy=='json_markdown_fence_removed')
    strict=fixture_model_execution(FixtureModelExecutionRequest(
        answers=('```json\n{"answer":1}\n```',),max_model_calls=1)).start_session()
    try:strict.invoke(replace(base,response_expectation=expected),Loop('strict JSON control'))
    except SolutionModelError:check('normalization_is_not_enabled_implicitly',True)
    else:check('normalization_is_not_enabled_implicitly',False)
    # Exercise the actual adaptive packet assembly, not a standalone validator.
    from . import adaptive_practitioner_records as records
    assembled=[];original=records.assemble_work_packet
    def capture(request, owner):
        result=original(request,owner);assembled.append((request.packet,result));return result
    with tempfile.TemporaryDirectory(prefix='cognitive-response-') as directory, patch(
            'loop_engine.core.adaptive_practitioner_records.assemble_work_packet',side_effect=capture):
        outcome=_run('Create a verified result.',(answers[0],json.dumps(incomplete),*answers[1:]),directory)
    decisions=[(p,a) for p,a in assembled if p.phase=='decide_next']
    check('real_practitioner_repairs_shape_before_planning',outcome.get('solved') is True
          and outcome.get('model_calls')==8 and len(decisions)==2)
    feedback=decisions[1][0].attempt_history.get('response_syntax_failure',{}) if len(decisions)>1 else {}
    check('repair_receives_exact_contract_failure_feedback',
          'schema_required_field_missing:budget' in feedback.get('schema_errors',())
          and all('PRIVATE_RESPONSE_CONTROL' not in item.prompt for _,item in assembled))
    from types import SimpleNamespace
    from .adaptive_practitioner_recovery import recover_step_contract_failure
    from .model_response_admission import ModelResponseRepairStalled
    failure=ModelResponseRepairStalled('response stalled',step_id='how',attempts=4,
        failure_code='schema_validation_failed',rejected_digests=('a'*64,))
    events=[]
    service=SimpleNamespace(request=SimpleNamespace(diagnose_unchanged_evidence=True),
        model_session=SimpleNamespace(results=[]),supervision_findings=[],active_pass_number=1,
        diagnostic=lambda code,payload:events.append((code,payload)))
    with patch('loop_engine.core.adaptive_practitioner_recovery.resolve_stall_with_panel',
               return_value={'route':'reframe'}) as panel:
        result=recover_step_contract_failure(failure,{'selected_action_id':'selected'},service)
    check('enabled_contract_stall_enters_the_existing_recovery_panel',
          panel.call_count==1 and result['route']=='reframe'
          and service.supervision_findings[-1]['current_action_executed'] is False)
    with patch('loop_engine.core.adaptive_practitioner_recovery.resolve_stall_with_panel',
               side_effect=failure) as panel:
        result=recover_step_contract_failure(failure,{},service)
    check('a_failed_recovery_panel_does_not_recursively_recover_itself',
          panel.call_count==1 and result is None and events[-1][0]=='step_contract_reorientation_unavailable')
    service.request.diagnose_unchanged_evidence=False
    try:recover_step_contract_failure(failure,{},service)
    except ModelResponseRepairStalled:check('disabled_pre_action_recovery_preserves_original_failure',True)
    else:check('disabled_pre_action_recovery_preserves_original_failure',False)
    return {'tests':tests,'passed':sum(t['passed'] for t in tests),'total':len(tests),
            'all_passed':all(t['passed'] for t in tests)}
