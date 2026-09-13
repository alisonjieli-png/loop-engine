"""Run the public solver on a newly admitted real task, with a sealed final set.

This first cohort uses the implemented baseline configuration. It does not
claim that planned factor combinations are implemented or tested. All source
attempts and failed runs remain in independent, non-overwriting directories.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

from .systematic_records import CampaignProjection, canonical, digest
from .systematic_runtime import SemanticStepSession, configure_environment
from .systematic_tasks import TASK_ID


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / 'examples/25_host_runtime'
if str(EXAMPLES) not in sys.path:
    sys.path.insert(0, str(EXAMPLES))
import generalization_probe as probe

from loop_engine import SolveRequest, solve_task
from loop_engine.core.model_capabilities import ModelOutputAllocation
from loop_engine.core.harness_fallback import HarnessFallbackPolicy, HarnessFailureKind
from loop_engine.core.observation_expectations import ObservationExpectation, ObservationBinding, assess_observation
from loop_engine.templates.intake import TaskIntakeRequest, intake_task

IMAGE = 'loop-engine-ds1000-runtime@sha256:d29a0fedd17671510b759b15f276b73ee9ba813868653d8923c7365482ee328d'


def task_value(record, queries, expected):
    return probe.ProbeTask(TASK_ID, 'density_normalized_neighbor_retrieval', record['prompt'],
        'solve', 'def solve(training_points, query_points):\n    raise NotImplementedError("No implementation has been generated yet")\n',
        canonical([probe.case('independent_queries', [record['training_points'], queries], expected)]))


def evaluate_source(root, source, task, store):
    root.mkdir(parents=True, exist_ok=False)
    (root/'solution.py').write_bytes(source)
    (root/'probe.py').write_text(probe.WORKER, encoding='utf8')
    store.export_object(root/'probe-input.json', {'entrypoint': task.entrypoint,
        'cases': [{k:c[k] for k in ('case_id','arguments','python_constants') if k in c} for c in task.cases]})
    before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
    execution = probe.docker_probe(root, IMAGE)
    after = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
    if before != after:
        raise ValueError('candidate changed frozen execution inputs')
    result = probe.evaluate(task, execution)
    return {'comparison': result, 'execution': execution, 'source_digest': hashlib.sha256(source).hexdigest()}


def qualify_evaluator(study_root):
    study_root = Path(study_root)
    source_store = CampaignProjection(study_root/'campaign.duckdb')
    admitted = source_store.latest('admitted_task', TASK_ID)
    source_store.close()
    if admitted is None:
        raise ValueError('task has not been admitted')
    # Use a small actual-data subset so control qualification is inexpensive;
    # the full source population remains in the real campaign cases.
    from .systematic_tasks import reference_neighbors
    import inspect
    training = admitted['training_points'][:43]
    queries = admitted['development_queries'][:3]
    expected = reference_neighbors(training, queries)
    control_record = {**admitted, 'training_points': training}
    task = task_value(control_record, queries, expected)
    root = study_root/'evaluator-qualification'/uuid.uuid4().hex
    store = CampaignProjection(root/'projection.duckdb')
    positive = ('import numpy as np\n' + inspect.getsource(reference_neighbors) +
                '\ndef solve(training_points, query_points):\n    return reference_neighbors(training_points, query_points)\n').encode()
    negative = b'def solve(training_points, query_points):\n    return [[training_points[0][0]]*5 for query in query_points]\n'
    good = evaluate_source(root/'correct_control', positive, task, store)
    bad = evaluate_source(root/'wrong_control', negative, task, store)
    result = {'record_type':'systematic_evaluator_qualification/v1',
              'positive_passed': good['comparison']['passed'],
              'negative_rejected': not bad['comparison']['passed'],
              'candidate_has_expected_outputs':False,
              'image':IMAGE,'positive':good,'negative':bad}
    result['qualified'] = result['positive_passed'] and result['negative_rejected']
    store.record('qualification', TASK_ID, result)
    store.export_object(root/'qualification.json', result)
    store.close()
    source_store = CampaignProjection(study_root/'campaign.duckdb')
    source_store.record('evaluator_qualification',TASK_ID,{'qualified':result['qualified'],'evidence':str(root/'qualification.json')})
    source_store.close()
    print('EVALUATOR', 'qualified' if result['qualified'] else 'failed', str(root),flush=True)
    return result['qualified']


def run_cohort(study_root, harnesses, *, fallback_policy=None, capture_recovery_learning=False,
               diagnose_unchanged_evidence=False):
    configure_environment()
    study_root=Path(study_root)
    source_store=CampaignProjection(study_root/'campaign.duckdb')
    admitted=source_store.latest('admitted_task',TASK_ID)
    qualification=source_store.latest('evaluator_qualification',TASK_ID)
    source_store.close()
    if not admitted or not qualification or not qualification['qualified']:
        raise ValueError('an admitted task and qualified evaluator are required')
    tasks=[]
    cohort='baseline-'+uuid.uuid4().hex[:12]
    for harness in harnesses:
        case_id=harness+'-'+uuid.uuid4().hex[:12]
        root=study_root/'cohorts'/cohort/case_id
        store=CampaignProjection(root/'projection.duckdb')
        selected_fallback = (fallback_policy if fallback_policy is not None
                             and fallback_policy.harness_ids[0] == harness else None)
        import loop_engine
        package=Path(loop_engine.__file__).resolve().parent
        source_identities={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(package.rglob('*.py'))}
        state={'record_type':'systematic_baseline_cell/v1','case_id':case_id,'cohort_id':cohort,
               'harness_id':harness,'origin_task_id':admitted['origin_task_id'],
               'task_id':TASK_ID,'task_digest':digest(admitted),'status':'starting',
               'per_task_model_call_limit':None,'per_task_pass_limit':None,
               'test_feedback_exposed':False,
               'runtime_source_digest':digest(source_identities),'runtime_source_root':str(package),
               'fallback_policy':selected_fallback.to_dict() if selected_fallback else None,
               'capture_recovery_learning':capture_recovery_learning,
               'diagnose_unchanged_evidence':diagnose_unchanged_evidence,
               'population_scope':'Previously attempted task with fresh sealed query instances; diagnostic, not an unseen-task claim',
               'configuration':{'context':'bounded_inline','skills':'none','tools':'execute_validate',
                                'intelligence':'core_context','first_steps':'orient_first',
                                'initialization':'fresh_minimal','outputs':'single',
                                'temperature':'exploratory','expectations':'typed_response_and_observable_progress'}}
        store.record('source_snapshot',case_id,source_identities)
        store.record('cell',case_id,state);store.refresh_export(root/'status.json',state)
        print('CELL START',cohort,harness,flush=True)
        started=time.monotonic()
        previous_writer=probe.write_json
        try:
            task=task_value(admitted,admitted['development_queries'],admitted['development_expected'])
            # The existing host's JSON writer is a configurable module seam.
            # It now materializes its exact object records through DuckDB.
            probe.write_json=store.export_object
            (root/'host').mkdir(mode=0o700)
            host=probe.make_host(root/'host',task,image=IMAGE)
            session=SemanticStepSession(study_root,harness,root/'semantic',fallback_policy=selected_fallback)
            authority=session.session.authority
            capability=authority.gateway.providers['tactical'].output_capability_for('gemma-4-coding-abliterated')
            allocation=ModelOutputAllocation(capability=capability,provider_id='tactical',
                model_id='gemma-4-coding-abliterated',route_name='custom.tactical',requested_tokens=65536,
                decision_ref=case_id+'-source-response-allocation',
                reason='Explicit per-call allowance for generating and reviewing a source artifact bounded at 64 KiB; total task calls and passes remain uncapped.')
            authority=replace(authority,config=replace(authority.config,output_allocation=allocation),max_model_calls=None)

            def progress(event):
                safe={k:event.get(k) for k in ('event_type','step','model_calls_completed','elapsed_seconds',
                    'diagnostic_code','diagnostic_detail','failure_code','format_attempt','transport_attempt')}
                store.record('progress',case_id,safe)
                store.refresh_export(root/'status.json',{**state,'status':'running','latest_progress':safe})
                if event.get('event_type') in ('model.step.started','model.step.completed','practitioner.diagnostic'):
                    print('PROGRESS',harness,safe,flush=True)

            outcome=solve_task(SolveRequest(intake_task(TaskIntakeRequest(text=task.prompt+probe.HOST_INSTRUCTIONS)),
                model_execution=authority,host_runtime=host,runs_dir=str(root/'runs'),
                interaction_mode='autonomous',quiet_model_io=True,max_passes=None,
                capture_recovery_learning=capture_recovery_learning,
                diagnose_unchanged_evidence=diagnose_unchanged_evidence,
                progress=progress))
            value=outcome.to_dict()
            store.record('solve_outcome',case_id,value)
            store.export_object(root/'solve-outcome.json',value)
            source=(root/'host/source/solution.py').read_bytes()
            state.update(status='candidate_frozen',engine_terminal=value['terminal_code'],
                         development_verified=value['solved'],model_calls=value['model_calls'],
                         model_call_accounting_complete=value.get('model_call_accounting_complete'),
                         frozen_source_digest=hashlib.sha256(source).hexdigest(),
                         elapsed_seconds=round(time.monotonic()-started,3))
            tasks.append((root,source,state))
        except Exception as exc:
            state.update(status='failed',error={'type':type(exc).__name__,'message':str(exc)[:500]},
                         elapsed_seconds=round(time.monotonic()-started,3))
        finally:
            probe.write_json=previous_writer
            current={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(package.rglob('*.py'))}
            state['runtime_source_unchanged']=current==source_identities
            store.record('cell',case_id,state);store.refresh_export(root/'status.json',state);store.close()
        print('CELL END',harness,state['status'],state.get('engine_terminal'),flush=True)
    # Holdout scores are released only after every surviving candidate in this
    # predeclared cohort is frozen. They never enter the current solver context.
    source_store=CampaignProjection(study_root/'campaign.duckdb')
    secret=source_store.latest('sealed_cases',TASK_ID);source_store.close()
    held=task_value(admitted,secret['queries'],secret['expected'])
    for root,source,state in tasks:
        store=CampaignProjection(root/'projection.duckdb')
        result=evaluate_source(root/'sealed-evaluation',source,held,store)
        store.record('sealed_evaluation',state['case_id'],result)
        store.export_object(root/'heldout-evaluation.json',result)
        state.update(status='evaluated',heldout_passed=result['comparison']['passed'])
        store.record('cell',state['case_id'],state);store.refresh_export(root/'status.json',state);store.close()
        print('HELDOUT',state['harness_id'],result['comparison']['passed'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True)
    p.add_argument('--qualify-evaluator',action='store_true')
    p.add_argument('--harnesses',default='native_gateway,pi,opencode,codex')
    p.add_argument('--fallback-order')
    p.add_argument('--capture-recovery-learning',action='store_true')
    p.add_argument('--diagnose-unchanged-evidence',action='store_true')
    a=p.parse_args()
    if a.qualify_evaluator:raise SystemExit(0 if qualify_evaluator(a.root) else 1)
    policy=(HarnessFallbackPolicy(tuple(a.fallback_order.split(',')),tuple(HarnessFailureKind))
            if a.fallback_order else None)
    run_cohort(a.root,a.harnesses.split(','),fallback_policy=policy,
               capture_recovery_learning=a.capture_recovery_learning,
               diagnose_unchanged_evidence=a.diagnose_unchanged_evidence)
