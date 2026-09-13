"""Task data, immutable references, and actual tools for configuration trials.

The arithmetic tools are trusted deterministic application implementations.
They are not provider fixtures. Model-selected changes pass exact contracts
before a registered tool executes; independent expected outcomes stay outside
the model packet. Resource access uses the existing InformationResolver.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import random

from loop_engine.core.context_artifacts import (
    ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
from loop_engine.core.information_access import (
    ContextArtifactInformationAdapter, InformationAccessRequest,
    InformationPublicationRequest, InformationResolver, InformationStorageBinding)
from loop_engine.core.mcp_adapter import (
    InjectedMcpTransport, McpCallRequest, McpInvocationServices, McpRegistry,
    McpServerSpec, McpToolSpec)
from loop_engine.core.run_history import RunHistory
from loop_engine.core.runtime_observer import RuntimeObservationServices
from loop_engine.loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.loop_role import LoopRoleIdentity
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome

from .systematic_records import canonical, digest


ARGUMENT_SCHEMA = {'type':'object','properties':{'left':{'type':'integer'},
    'right':{'type':'integer'}},'required':['left','right'],'additionalProperties':False}
TOOL_DESCRIPTIONS = {'difference':'Subtract right from left.',
    'sum':'Add left and right.', 'product':'Multiply left by right.'}


@dataclass(frozen=True)
class RepairCase:
    case_id: str
    goal: str
    broken_call_json: str
    choices_json: str
    requirement_document: str
    expected_value: int

    def public(self):
        return {'case_id':self.case_id,'goal':self.goal,
                'broken_call':json.loads(self.broken_call_json),
                'repair_choices':json.loads(self.choices_json),
                'requirement_document':self.requirement_document}


def task_population():
    """Four disclosed component cases; no unseen or training-independence claim."""
    generator=random.Random(9122602)
    facts=(('stock','Compute stock remaining after shipments.','difference',47,19,
            'The initial stock is 47 units. Shipments remove 19 units.'),
           ('hours','Compute combined hours from two work periods.','sum',6,9,
            'The first work period is 6 hours. The second is 9 hours.'),
           ('packages','Compute the total units in equal packages.','product',8,7,
            'There are 8 packages with 7 units in each package.'),
           ('balance','Compute the remaining balance, permitting a negative result.','difference',73,91,
            'The initial balance is 73 units. A debit removes 91 units.'))
    cases=[];documents=[]
    for name,goal,tool,left,right,description in facts:
        patches=[{'tool_name':tool,'arguments':{'left':left,'right':right}},
                 {'tool_name':tool,'arguments':{'left':left,'right':right+1}},
                 {'tool_name':'product' if tool!='product' else 'sum',
                  'arguments':{'left':left,'right':right}},
                 {'tool_name':tool,'arguments':{'left':left,'right':str(right)}}]
        generator.shuffle(patches)
        choices=[{'repair_id':name+'-choice-'+str(index),
                  'replacement_call':value} for index,value in enumerate(patches)]
        # Expected results use separate simple expressions, not the tool handler.
        expected={'stock':28,'hours':15,'packages':56,'balance':-18}[name]
        cases.append(RepairCase(name,goal,canonical({'tool_name':tool,
            'arguments':{'left':str(left),'right':right}}),canonical(choices),
            name+'-requirement',expected))
        documents.append({'resource_id':name+'-requirement','title':goal,
            'version':'1.0.0','record_type':'configuration_resource/v1',
            'content':description,'purpose':'task_requirement'})
    documents.append({'resource_id':'tool-contracts','title':'Permitted arithmetic tool contracts',
        'version':'1.0.0','record_type':'configuration_resource/v1',
        'content':{'tools':TOOL_DESCRIPTIONS,'argument_schema':ARGUMENT_SCHEMA},
        'purpose':'tool_contract'})
    for index in range(12):
        documents.append({'resource_id':'unrelated-'+str(index),
            'title':'Historical unrelated configuration note '+str(index),
            'version':'1.0.0','record_type':'configuration_resource/v1',
            'content':('This note concerns another task and supplies no authority or current values. '
                'Historical quantities and earlier choices do not change the current requirement. ')*4,
            'purpose':'historical_unrelated_material'})
    return tuple(cases),tuple(documents)


def decision_schema(cases):
    return {'type':'object','properties':{'decisions':{'type':'array',
        'minItems':len(cases),'maxItems':len(cases),'items':{'oneOf':[
            {'type':'object','properties':{'case_id':{'const':case.case_id},
                'repair_id':{'enum':[c['repair_id'] for c in json.loads(case.choices_json)]}},
             'required':['case_id','repair_id'],'additionalProperties':False} for case in cases]}}},
        'required':['decisions'],'additionalProperties':False}


def deterministic_assignment(goal, callback, *, profile='practitioner.code_execution'):
    role=profile.split('.')[0]
    config=LoopConfig(framework='custom',custom_steps=('execute',),
        allowable_modes=('deterministic',),preferred_modes=('deterministic',),
        delegated_modes=('deterministic',),exit_condition='steps_complete')
    owner=Loop(goal,config,identity=LoopRoleIdentity(role,profile),
        contract=LoopContract('configuration operation','code_only',
            input_roles=('configuration_request/v1',),output_roles=('configuration_result/v1',),role=role))
    holder={}
    def handler(active,step,context):
        holder['value']=callback(active)
        return StepOutcome(output=canonical(holder['value']),mode='deterministic',confidence=1.0)
    owner.run(handler=handler,max_steps=1)
    if 'value' not in holder:raise RuntimeError('deterministic assignment did not return a value')
    return holder['value'],owner


def save_history(owner, directory, run_id):
    history=RunHistory.from_ledger(owner.ledger.events,run_id=run_id)
    history.commit()
    path=history.save(str(directory))
    return {'path':path,'verification':history.verify_chain(),
            'loop_definition':owner.definition.to_dict()}


class StudyInformation:
    """Application binding to the existing artifact store and information resolver."""
    def __init__(self, root, run_id):
        self.root=Path(root).resolve();self.run_id=run_id
        self.store=ContextArtifactStore(ContextArtifactStoreSpec(str(self.root/'artifacts')))
        self.resolver=InformationResolver()
        self.resolver.register(ContextArtifactInformationAdapter(self.store))
        self.bindings={}

    def publish(self, documents, owner):
        for item in documents:
            value=LoopValue.create(item,LoopValueCreateRequest('configuration_resource/v1',
                'selected_task_material',owner.loop_id,owner.definition.content_digest,
                source_refs=('synthetic_component_population:configuration_resources:v1',)))
            binding=self.resolver.publish(InformationPublicationRequest(value,
                'local.context_artifact','run','run_shared',run_id=self.run_id,
                required_permissions=('study.context.read',)))
            self.bindings[item['resource_id']]=binding
        return [{'resource_id':item['resource_id'],'title':item['title'],
            'version':item['version'],'purpose':item['purpose'],
            'reference':self.bindings[item['resource_id']].value_ref.to_dict(),
            'bytes':self.bindings[item['resource_id']].size_bytes} for item in documents]

    def load(self, ids, owner, *, grant=True):
        if not isinstance(ids,(list,tuple)) or len(set(ids))!=len(ids):
            raise ValueError('selected resource IDs must be a unique sequence')
        material=[]
        for resource_id in ids:
            binding=self.bindings[resource_id]
            material.append(self.resolver.materialize(InformationAccessRequest(
                owner.loop_id,binding.value_ref,'resolve selected experimental context',
                requester_run_id=self.run_id,granted_permissions=('study.context.read',) if grant else (),
                maximum_bytes=32768)).value)
        return material

    def transfer(self):
        return {'record_type':'configuration_reference_handoff/v1',
            'artifact_root':str(self.root/'artifacts'),'run_id':self.run_id,
            'bindings':{key:value.to_storage_dict() for key,value in self.bindings.items()}}

    @classmethod
    def restore(cls, packet):
        if packet['record_type']!='configuration_reference_handoff/v1':raise ValueError('unsupported handoff')
        obj=cls(Path(packet['artifact_root']).parent,packet['run_id'])
        for key,value in packet['bindings'].items():
            binding=InformationStorageBinding.from_storage_dict(value)
            obj.resolver.attach(binding);obj.bindings[key]=binding
        return obj


def arithmetic_plugin(artifacts, owner):
    tools=tuple(McpToolSpec('study-arithmetic',name,description,ARGUMENT_SCHEMA,'pure')
                for name,description in TOOL_DESCRIPTIONS.items())
    async def execute(request):
        values=request.transport_arguments();left,right=values['left'],values['right']
        if request.tool_name=='difference':answer=left-right
        elif request.tool_name=='sum':answer=left+right
        elif request.tool_name=='product':answer=left*right
        else:raise ValueError('unknown arithmetic operation')
        return {'value':answer}
    transport=InjectedMcpTransport(tools,execute)
    registry=McpRegistry()
    registry.register(McpServerSpec('study-arithmetic','in_process',tool_allowlist=tuple(TOOL_DESCRIPTIONS)),transport)
    runtime=RuntimeObservationServices(parent=owner)
    registry.discover('study-arithmetic',runtime=runtime)
    services=McpInvocationServices(runtime=runtime,artifact_manager=artifacts)
    return registry,services,transport


def apply_repairs(cases, decisions, artifacts, owner):
    if not isinstance(decisions,list) or len(decisions)!=len(cases):
        raise ValueError('every case needs exactly one selected repair')
    selected={d['case_id']:d['repair_id'] for d in decisions}
    if len(selected)!=len(cases) or set(selected)!={c.case_id for c in cases}:
        raise ValueError('duplicate or unrelated case selection')
    registry,services,transport=arithmetic_plugin(artifacts,owner)
    observations=[]
    for case in cases:
        choices={c['repair_id']:c['replacement_call'] for c in json.loads(case.choices_json)}
        call=choices[selected[case.case_id]]
        before=json.loads(case.broken_call_json)
        baseline=registry.invoke(McpCallRequest('study-arithmetic',before['tool_name'],before['arguments']),services=services)
        result=registry.invoke(McpCallRequest('study-arithmetic',call['tool_name'],call['arguments']),services=services)
        observations.append({'case_id':case.case_id,'repair_id':selected[case.case_id],
            'before_call_digest':digest(before),'applied_call_digest':digest(call),
            'changed':before!=call,'before_status':baseline.status,
            'before_error_code':baseline.error_code,'after_status':result.status,
            'after_error_code':result.error_code,'output':result.output,
            'output_ref':result.output_ref,'tool_loop_id':result.loop_id})
    return {'observations':observations,'physical_tool_calls':len(transport.calls),
            'plugin_transport':'real_in_process_application','native_harness_tools':False}


def evaluate_repairs(cases, application):
    expected={case.case_id:case.expected_value for case in cases}
    judgments=[]
    for item in application['observations']:
        actual=(item.get('output') or {}).get('value')
        passed=(item['changed'] and item['before_status']=='refused'
                and item['after_status']=='completed' and type(actual) is int
                and actual==expected[item['case_id']])
        judgments.append({'case_id':item['case_id'],'passed':passed,
                          'observed':actual,'expected':expected[item['case_id']]})
    return {'record_type':'configuration_repair_evaluation/v1','cases':judgments,
            'passed':sum(x['passed'] for x in judgments),'total':len(cases),
            'all_passed':len(judgments)==len(cases) and all(x['passed'] for x in judgments),
            'evaluator':'independent_controller_expected_values/v1',
            'metric_direction':'higher_is_better','full_system_benchmark':False}
