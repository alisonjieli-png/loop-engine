"""Execute a finite live comparison of context, resources, and repair settings.

Every cell retains exact settings, inputs, source identities, materialized
references, provider accounting, applied changes, and independent evaluation.
This is component qualification on disclosed cases, not a full-system benchmark.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import uuid

from loop_engine.core.context_artifacts import ContextArtifactManager, ContextArtifactServices
from loop_engine.core.model_response_admission import ModelResponseAdmissionPolicy
from loop_engine.core.practitioner_context import load_practitioner_context_with_record
from loop_engine.core.skill_registry import SkillAdmissionRecord, SkillLoadPurpose, SkillRegistry
from loop_engine.core.runtime_observer import RuntimeObservationServices

from .configuration_resources import (
    StudyInformation, apply_repairs, arithmetic_plugin, decision_schema,
    deterministic_assignment, evaluate_repairs, save_history, task_population)
from .configuration_study import freeze_sources, source_changes
from .systematic_records import CampaignProjection, canonical, digest
from .systematic_runtime import ROOT, SemanticStepSession, configure_environment


@dataclass(frozen=True)
class ResourceConfiguration:
    harness_id: str
    context_delivery: str = 'relevant_inline'
    intelligence: str = 'none'
    initialization: str = 'none'
    first_step: str = 'repair_selection'
    temperature: float = 0.0
    counterfactual_input: bool = False
    version: str = '1.0.0'

    def __post_init__(self):
        if self.harness_id not in ('native_gateway','pi','opencode','codex'):
            raise ValueError('unknown harness')
        if self.context_delivery not in ('relevant_inline','full_history','selected_references'):
            raise ValueError('unknown context delivery')
        if self.intelligence not in ('none','core_context'):
            raise ValueError('unknown intelligence policy')
        if self.initialization not in ('none','controller_markdown','admitted_skill','tool_manifest'):
            raise ValueError('unknown resource initialization')
        if self.first_step not in ('repair_selection','orient_then_repair'):
            raise ValueError('unknown first step')
        if self.temperature not in (0.0,0.7) or type(self.counterfactual_input) is not bool or self.version!='1.0.0':
            raise ValueError('invalid version, temperature, or input setting')


def configurations():
    variants=(('baseline',{}),('full_history',{'context_delivery':'full_history'}),
        ('selected_references',{'context_delivery':'selected_references'}),
        ('core_context',{'intelligence':'core_context'}),
        ('markdown',{'initialization':'controller_markdown'}),
        ('skill',{'initialization':'admitted_skill'}),
        ('tools',{'initialization':'tool_manifest'}),
        ('practitioner_steps',{'first_step':'orient_then_repair'}),
        ('temperature',{'temperature':0.7}),('changed_input',{'counterfactual_input':True}))
    result=[(name,ResourceConfiguration(harness,**fields))
            for harness in ('native_gateway','pi','opencode','codex') for name,fields in variants]
    random.Random(9122603).shuffle(result)
    return result


def exact_skill_review(root,phase,projection):
    """Review an existing authored skill independently before run-local admission."""
    registry=SkillRegistry()
    candidate=registry.discover((str(ROOT/'src/loop_engine/skills/software-tdd-red-green-refactor'),))[0]
    loaded=registry.load(candidate.skill_id,purpose=SkillLoadPurpose.CANDIDATE_REVIEW)
    session=SemanticStepSession(root,'native_gateway',phase/'skill-independent-review')
    fields=('requires_exact_requirement','requires_confined_authority','requires_observed_failure',
            'requires_post_change_verification','forbids_unapproved_publication')
    schema={'type':'object','properties':{'decision':{'enum':['admit','reject']},
        'manifest_digest':{'const':candidate.manifest_digest},
        'checks':{'type':'object','properties':{name:{'type':'boolean'} for name in fields},
            'required':list(fields),'additionalProperties':False},
        'supporting_quotes':{'type':'array','minItems':3,'items':{'type':'string','minLength':12}},
        'reason':{'type':'string','minLength':1}},
        'required':['decision','manifest_digest','checks','supporting_quotes','reason'],
        'additionalProperties':False}
    result=session.invoke('Independently review an existing skill for this confined repair study',
        {'candidate':{'id':candidate.skill_id,'version':candidate.version,
            'manifest_digest':candidate.manifest_digest,'instructions':loaded.instructions},
         'review_scope':'Only repair typed local execution requests against an exact schema, invoke registered pure tools, and verify the resulting values. No source publication or broader permissions.',
         'decision_rule':'Admit only if every named condition is supported by the actual skill. Quote exact text supporting the decision. You are separate from the later repair producers; no repair outputs are supplied.'},
        schema,temperature=0.0,output_allocation_tokens=4096,
        response_policy=ModelResponseAdmissionPolicy(),profile_id='practitioner.verifier')
    projection.record('skill_review',candidate.skill_id,result)
    projection.export_object(phase/'skill-review.json',result)
    value=result.get('value') or {}
    quotes=value.get('supporting_quotes',[])
    actual=' '.join(loaded.instructions.split())
    qualified=(result['accepted_response'] and value.get('decision')=='admit'
               and all(value.get('checks',{}).get(name) is True for name in fields)
               and len(quotes)>=3 and all(' '.join(q.split()) in actual for q in quotes))
    if not qualified:return registry,None,result
    admission=SkillAdmissionRecord('study-skill-'+uuid.uuid4().hex,candidate.skill_id,candidate.version,
        candidate.manifest_digest,'independent-verifier:'+result['operation_id'],
        ('run-history:'+result['run_history'],),digest(result))
    registry.admit(admission)
    projection.record('skill_admission',candidate.skill_id,admission.to_dict())
    projection.export_object(phase/'skill-admission.json',admission.to_dict())
    return registry,admission,result


def input_population(counterfactual):
    cases,documents=task_population()
    if not counterfactual:return cases,documents
    cases=tuple(replace(case,expected_value=27) if case.case_id=='stock' else case for case in cases)
    documents=tuple({**doc,'content':'The initial stock is 47 units. Shipments remove 20 units.'}
                    if doc['resource_id']=='stock-requirement' else doc for doc in documents)
    return cases,documents


def reference_consumer(packet):
    information=StudyInformation.restore(packet['handoff'])
    material,owner=deterministic_assignment('Resolve exact selected context in a new process',
        lambda owner:information.load(packet['resource_ids'],owner),profile='intelligence.context.serve')
    return {'record_type':'configuration_reference_materialization/v1','material':material,
        'process_id':os.getpid(),'bytes_loaded':len(canonical(material).encode()),
        'provider_credential_present':bool(os.environ.get('TACTICAL_API_KEY')),
        'history':save_history(owner,Path(packet['history_directory']),'reference-consumer-'+uuid.uuid4().hex)}


def run_cell(root,phase,cell_id,config,skill_registry,admission,projection):
    cell=phase/cell_id;cell.mkdir()
    cases,documents=input_population(config.counterfactual_input)
    information=StudyInformation(cell,cell_id)
    manifest,publisher=deterministic_assignment('Publish exact experimental resource references',
        lambda owner:information.publish(documents,owner),profile='intelligence.context.serve')
    preparation={'publication':save_history(publisher,cell/'mechanics-runs','publication-'+cell_id),
        'reference_manifest':manifest,'native_harness_tools_enabled':False,
        'native_harness_auto_loading_enabled':False}
    semantic=SemanticStepSession(root,config.harness_id,cell/'semantic')
    policy=ModelResponseAdmissionPolicy(report_required_field_names=True)
    observations=[]
    def remember(observation):
        observations.append(observation)
        payload={'record_type':'configuration_semantic_observations/v1','items':observations}
        projection.record('semantic_observations',cell_id,payload)
        projection.refresh_export(cell/'semantic-observations.json',payload)
    packet={'record_type':'configuration_repair_assignment/v1',
        'objective':'Choose one offered replacement call per case. Each replacement must satisfy the tool argument schema and the current requirement. The controller will apply and execute your exact selection, then independently check the result.',
        'cases':[case.public() for case in cases],
        'effect_policy':'Only the three registered pure arithmetic tools are permitted. No new code, shell, network, publication, permission changes, or self-promotion.',
        'resources':[]}
    if config.context_delivery=='selected_references':
        selected=semantic.invoke('Select the exact references needed to repair the four requests',
            {'cases':packet['cases'],'available_resources':manifest,
             'instruction':'Select the requirement for every case and the tool contract. Omit unrelated material.'},
            {'type':'object','properties':{'resource_ids':{'type':'array','uniqueItems':True,
              'minItems':1,'maxItems':len(documents),'items':{'enum':[d['resource_id'] for d in documents]}}},
             'required':['resource_ids'],'additionalProperties':False},temperature=config.temperature,
            output_allocation_tokens=4096,response_policy=policy)
        remember(selected)
        if not selected['accepted_response']:return {'status':'reference_selection_failed','semantic_observations':observations,'preparation':preparation}
        transfer={'handoff':information.transfer(),'resource_ids':selected['value']['resource_ids'],
                  'history_directory':str(cell/'mechanics-runs')}
        # The consumer gets only exact binding metadata and approved local reads.
        # Credentials and the calling process environment are not inherited.
        completed=subprocess.run([sys.executable,'-m','embodiment_lab.configuration_matrix','--resolve-references'],
            input=canonical(transfer),text=True,capture_output=True,check=True,timeout=60,
            cwd=ROOT,env={'PATH':'/usr/bin:/bin','PYTHONPATH':str(ROOT/'src')+':'+str(ROOT/'devtools'),
                         'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8','TMPDIR':'/var/tmp'})
        handoff=json.loads(completed.stdout)
        packet['resources']=handoff.pop('material')
        preparation['reference_consumer']=handoff
        preparation['selected_resource_ids']=selected['value']['resource_ids']
    else:
        chosen=[doc['resource_id'] for doc in documents
                if config.context_delivery=='full_history' or doc['purpose']!='historical_unrelated_material']
        material,loader=deterministic_assignment('Materialize the configured context',
            lambda owner:information.load(chosen,owner),profile='intelligence.context.serve')
        packet['resources']=material
        preparation['context_load']=save_history(loader,cell/'mechanics-runs','context-'+cell_id)
        preparation['selected_resource_ids']=chosen
    preparation['materialized_context_bytes']=len(canonical(packet['resources']).encode())
    if config.intelligence=='core_context':
        loaded,owner=deterministic_assignment('Load the existing Context Intelligence portfolio',
            lambda owner:(lambda record:{'record':record.to_dict(),
                'questions':record.portfolio.question_candidates('adjudicate_recovery'),
                'guidance':record.portfolio.guidance_candidates('adjudicate_recovery')})(load_practitioner_context_with_record()),
            profile='intelligence.context.serve')
        packet['context_intelligence']=loaded
        preparation['intelligence_load']=save_history(owner,cell/'mechanics-runs','intelligence-'+cell_id)
    if config.initialization=='controller_markdown':
        path=Path(__file__).parent/'resources/configuration-instructions.md'
        material,owner=deterministic_assignment('Load explicitly selected Markdown instructions',
            lambda owner:{'source_path':str(path.relative_to(ROOT)),
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'content':path.read_text()},
            profile='intelligence.context.serve')
        packet['selected_instructions']=material
        preparation['markdown_load']=save_history(owner,cell/'mechanics-runs','markdown-'+cell_id)
        preparation['markdown_mechanism']='controller_loads_exact_file_into_assignment; not native auto-discovery'
    if config.initialization=='admitted_skill':
        if admission is None:return {'status':'skill_review_not_admitted','semantic_observations':observations,'preparation':preparation}
        loaded=skill_registry.load(admission.skill_id,admission.version,purpose=SkillLoadPurpose.TASK_USE)
        packet['selected_skill']={'skill_id':admission.skill_id,'version':admission.version,
            'manifest_digest':admission.manifest_digest,'admission_digest':admission.digest,
            'instructions':loaded.instructions}
        preparation['skill_loading']='actual SkillRegistry task use after independent run-local admission'
    if config.initialization=='tool_manifest':
        def discover(owner):
            artifacts=ContextArtifactManager(ContextArtifactServices(information.store))
            registry,services,transport=arithmetic_plugin(artifacts,owner)
            return [{'server_id':tool.server_id,'name':tool.name,'description':tool.description,
                'input_schema':dict(tool.input_schema),'effect':tool.effect} for tool in registry.tools('study-arithmetic')]
        tools,owner=deterministic_assignment('Discover the explicitly registered default tools',discover,
            profile='intelligence.code.resolve')
        packet['default_tools']=tools
        preparation['tool_discovery']=save_history(owner,cell/'mechanics-runs','tools-'+cell_id)
    if config.first_step=='orient_then_repair':
        orientation=semantic.invoke('Orient the repair assignment before selecting changes',packet,
            {'type':'object','properties':{'required_checks':{'type':'array','minItems':1,'items':{'type':'string'}},
                'information_gaps':{'type':'array','items':{'type':'string'}},'plan':{'type':'string'}},
             'required':['required_checks','information_gaps','plan'],'additionalProperties':False},
            temperature=config.temperature,output_allocation_tokens=4096,response_policy=policy)
        remember(orientation)
        if not orientation['accepted_response']:return {'status':'orientation_failed','semantic_observations':observations,'preparation':preparation}
        packet['preceding_orientation']=orientation['value']
    preparation['final_packet_bytes']=len(canonical(packet).encode())
    projection.export_object(cell/'input-packet.json',packet)
    answer=semantic.invoke('Select repairs that satisfy the exact request contracts',packet,
        decision_schema(cases),temperature=config.temperature,output_allocation_tokens=4096,response_policy=policy)
    remember(answer)
    if not answer['accepted_response']:return {'status':'response_rejected','semantic_observations':observations,'preparation':preparation}
    artifacts=ContextArtifactManager(ContextArtifactServices(information.store))
    application,executor=deterministic_assignment('Apply selected changes and invoke registered tools',
        lambda owner:apply_repairs(cases,answer['value']['decisions'],artifacts,owner))
    evaluation,verifier=deterministic_assignment('Independently evaluate the changed results',
        lambda owner:evaluate_repairs(cases,application),profile='practitioner.verifier')
    return {'status':'evaluated','semantic_observations':observations,'preparation':preparation,
        'application':application,'evaluation':evaluation,
        'application_history':save_history(executor,cell/'mechanics-runs','application-'+cell_id),
        'evaluation_history':save_history(verifier,cell/'mechanics-runs','evaluation-'+cell_id)}


def run_matrix(study_root):
    root=Path(study_root).resolve();phase=root/('resource-matrix-'+uuid.uuid4().hex[:12]);phase.mkdir()
    projection=CampaignProjection(phase/'projection.duckdb')
    configure_environment()
    skill_registry,admission,review=exact_skill_review(root,phase,projection)
    if not review['model_call_accounting_complete']:
        projection.close();raise RuntimeError('unknown review accounting requires reconciliation')
    selected=configurations();sources=freeze_sources(phase/'source-files.zip')
    manifest={'record_type':'resource_configuration_matrix/v1','phase_id':phase.name,
        'selection_rule':'all four named harnesses crossed with ten explicitly configured variants, one attempt per cell',
        'population':'four disclosed synthetic repair cases; changed_input alters one requirement',
        'planned_cells':len(selected),'cases_per_cell':4,'configs':[{'variant':name,**asdict(c)} for name,c in selected],
        'sources':sources,'skill_admission':admission.to_dict() if admission else None,
        'provider_configuration_digest':hashlib.sha256((root/'provider.yaml').read_bytes()).hexdigest(),
        'automatic_provider_failover':False,'total_model_call_limit':None,'total_token_limit':None,
        'per_response_allocation_tokens':4096,'harness_process_lifetime':'fresh_per_semantic_attempt',
        'native_harness_tool_skill_plugin_loading':'not enabled by these recipes; measured engine-mediated alternatives',
        'private_or_external_task_data':False,'full_system_benchmark':False,'hypothesis':'material delivery and setup may affect repair choice, admission, effort, and independently checked outcomes'}
    projection.record('manifest',phase.name,manifest);projection.export_object(phase/'manifest.json',manifest)
    results=[]
    try:
        for index,(variant,configuration) in enumerate(selected):
            cell_id=f'{index:02d}-{configuration.harness_id}-{variant}-{uuid.uuid4().hex[:8]}'
            record={'cell_id':cell_id,'variant':variant,'configuration':asdict(configuration),'status':'started'}
            projection.record('cell',cell_id,record);print('START',cell_id,flush=True)
            try:record.update(run_cell(root,phase,cell_id,configuration,skill_registry,admission,projection))
            except Exception as error:
                observed=projection.latest('semantic_observations',cell_id) or {}
                record.update(status='application_failed',error_type=type(error).__name__,error=str(error)[:240],
                              semantic_observations=observed.get('items',[]))
            record['source_changes']=source_changes(sources)
            results.append(record);projection.record('cell',cell_id,record)
            projection.export_object(phase/(cell_id+'.json'),record)
            projection.refresh_export(phase/'summary.json',{'record_type':'resource_configuration_summary/v1',
                'manifest_digest':digest(manifest),'planned':len(selected),'finished':len(results),
                'skill_review':review,'results':results,'live_provider':True,'full_system_benchmark':False})
            calls=(sum(x['model_calls_known_subtotal'] for x in record['semantic_observations'])
                   if record.get('semantic_observations') else None)
            print('RESULT',cell_id,record['status'],'passed',record.get('evaluation',{}).get('passed'),
                  'known_calls',calls,'error',record.get('error'),flush=True)
            if record['source_changes']:raise RuntimeError('source changed during frozen comparison')
            if record['status']=='application_failed':raise RuntimeError('application failure requires diagnosis before continuing the matrix')
            if any(not x['model_call_accounting_complete'] for x in record.get('semantic_observations',[])):
                raise RuntimeError('unknown provider accounting requires reconciliation')
    finally:projection.close()
    print('MATRIX_COMPLETE',phase,flush=True)
    return phase


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root');parser.add_argument('--resolve-references',action='store_true')
    args=parser.parse_args()
    if args.resolve_references:
        # JSON is a process message here, not a generated file or managed record.
        print(canonical(reference_consumer(json.load(sys.stdin))))
    elif args.root:run_matrix(args.root)
    else:parser.error('--root is required for a live comparison')
