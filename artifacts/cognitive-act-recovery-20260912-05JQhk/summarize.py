"""Rebuild this derived report from saved, verified campaign records.

Reads canonical Run History and artifacts without rewriting them. New JSON
projections are generated through DuckDB, including incomplete run states.
"""
from pathlib import Path
import hashlib
import json
import sys

REPOSITORY=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPOSITORY/'devtools'))
from embodiment_lab.systematic_records import CampaignProjection
from loop_engine.core.run_history import verify_saved_run

STUDIES=('cognitive-act-20260912-4dvatL','cognitive-act-20260912-y2dvqH',
         'cognitive-act-20260912-lRaw69')


def summarize():
    output=Path(__file__).resolve().parent
    store=CampaignProjection(output/'review.duckdb')
    cells=[]
    for study in STUDIES:
        root=REPOSITORY/'.loop-engine-dev'/study
        for status in sorted(root.glob('cohorts/*/*/status.json')):
            state=json.loads(status.read_text());cell=status.parent
            summary={'study':study,'cell_id':cell.name,
                **{k:state.get(k) for k in ('harness_id','status','engine_terminal',
                    'development_verified','model_calls','model_call_accounting_complete',
                    'heldout_passed','elapsed_seconds','runtime_source_digest','runtime_source_unchanged')},
                'fallback_policy':state.get('fallback_policy'),
                'provider':'tactical','model_id':'gemma-4-coding-abliterated','cost':None,
                'recovery_rounds':0,'learning_dispositions':[],'reusable_candidates':0}
            outcome=cell/'solve-outcome.json'
            if outcome.is_file():
                value=json.loads(outcome.read_text())
                summary['model_calls_known_subtotal']=value.get('model_calls_known_subtotal')
            for result_path in sorted((cell/'runs').glob('*/adaptive-result.json')):
                result=json.loads(result_path.read_text());run=result_path.parent
                summary['run_id']=run.name
                summary['history_verification']=verify_saved_run(str(run.parent),run.name)
                summary['recovery_rounds']=len(result.get('recovery_directives',()))
                summary['host_operations']=len(result.get('host_results',()))
                for directive in result.get('recovery_directives',()):
                    capture=directive.get('learning_capture',{})
                    if not capture:continue
                    summary['learning_dispositions'].append(capture.get('disposition','unknown'))
                    summary['reusable_candidates']+=capture.get('candidate_count',0)
                    ref=capture.get('artifact_ref')
                    if ref:
                        digest=ref['digest']
                        paths=list((run.parent/(run.name+'-artifacts')).glob(
                            '*/objects/'+digest[:2]+'/'+digest))
                        valid=len(paths)==1 and not paths[0].is_symlink()
                        if valid:
                            body=paths[0].read_bytes()
                            valid=(hashlib.sha256(body).hexdigest()==digest
                                   and len(body)==ref['byte_count'])
                        if not valid:raise ValueError('learning artifact reference did not verify')
            store.record('cell',study+'/'+cell.name,summary);cells.append(summary)
    report={'record_type':'cognitive_act_recovery_review/v1','cells':cells,
        'task_population':'one previously attempted task; fresh sealed query instances per study',
        'active_intelligence_promotion':False,'AGI_demonstrated':False}
    store.record('report','current',report)
    store.refresh_export(output/'summary.json',report)
    store.close()
    for item in cells:
        print(item['study'],item['harness_id'],item['status'],item.get('engine_terminal'),
              'known_calls=',item.get('model_calls_known_subtotal'),
              'recovery_rounds=',item['recovery_rounds'],'learning=',item['learning_dispositions'])


if __name__=='__main__':
    summarize()
