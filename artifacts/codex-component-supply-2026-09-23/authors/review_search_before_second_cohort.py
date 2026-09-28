"""Read-only candidate retrieval using existing catalogue/search contracts."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=Path('/home/username/.le-codex-build/integration')
sys.path[:0]=[str(REPO),str(REPO/'src')]
from tools.stage_intelligence_candidates import LAYERS,CATALOG_LAYERS,StoreRecord,IntelligenceSearchRequest,query_intelligence
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.catalog.query import IntelligenceQuery
DATABASE=Path('/home/username/.le-codex-research-cache/component-supply-20260923/candidates.db')
NAMESPACE='codex.component.supply.20260923'
PAIRS=[
('render_focused_task_context','Turn this assignment into a compact brief with clear first actions and completion checks.'),
('evaluate_capability_requirements','Which required features still lack sufficiently strong supporting evidence?'),
('select_context_blocks','Fit useful background into a fixed allowance while retaining mandatory prerequisites.'),
('paired_sign_test','Compare paired baseline and candidate measurements without treating ties as wins.'),
('profile_csv_structure','Inspect this quoted delimited extract for ragged rows and empty columns.'),
('reconcile_multiset_rows','Find extra repeated records on either side of these two collections.'),
('compute_weighted_quantiles','Return exact weighted percentile cutoffs without interpolating between observed values.'),
('audit_half_open_interval_overlaps','Identify overlapping reservations, total covered time and peak simultaneous occupancy.'),
('apply_flat_record_changes','Apply all these object edits only if every expected old value still matches.'),
('reconcile_keyed_tables','Match two tables by unique typed identifiers and report field-level changes.'),
('compare_file_inventories','Compare two supplied file manifests and separate additions, removals and metadata changes.'),
('resolve_selected_dependency_closure','Find everything needed by the selected packages and report reachable dependency cycles.'),
('assign_digest_shards','Assign identifiers reproducibly to a fixed number of buckets from their complete content hashes.'),
('validate_event_precedence','Check whether required events occurred in the prescribed relative order.'),
('apply_nonoverlapping_text_edits','Apply several string replacements using positions from the original Unicode text.'),
('detect_portable_path_collisions','Detect names that collide after Unicode normalization or make one file the parent of another.')]
def layers():
 store=SQLiteRecordStore(DATABASE)
 try:records=list(store.query(IntelligenceQuery(namespaces=(NAMESPACE,),lifecycle=('candidate',))))
 finally:store.close()
 result={key:[] for key in LAYERS}
 for row in records:
  body=row['payload']
  result[CATALOG_LAYERS[row['intelligence_layer']]].append(StoreRecord(row['record_id'],'context',body['title'],body={'text':body['text'],'lifecycle':'candidate','category':body['family'],'symbols':body.get('symbols',[]),'source_identities':body['sources']},tags=tuple(row['attributes']['tags']),tier='experimental',source='candidate_review_catalogue'))
 return result

def search(query,top_n=3):return query_intelligence(IntelligenceSearchRequest(query,layers(),top_n=top_n,include_candidates=True))
def main():
 p=argparse.ArgumentParser();p.add_argument('--query');p.add_argument('--evaluate',type=Path);args=p.parse_args()
 if args.query:
  r=search(args.query);print(json.dumps({'candidate_only':True,'hits':r['hits'],'model_calls':r['query_loop']['model_calls']},indent=2));return
 if not args.evaluate:p.error('--query or --evaluate required')
 if args.evaluate.exists():raise ValueError('use a new report path')
 rows=[]
 for identity,query in PAIRS:
  r=search(query);hits=[h['record_id'] for h in r['hits']];wanted=NAMESPACE+'.'+identity
  rows.append({'identity':identity,'query':query,'hits':hits,'rank':hits.index(wanted)+1 if wanted in hits else None,'model_calls':r['query_loop']['model_calls']})
 negative=[]
 for query in ['Bake sourdough bread at high altitude','Select a hiking tent for winter camping','Diagnose severe chest pain','Send a message to a customer']:
  r=search(query);negative.append({'query':query,'hits':[h['record_id'] for h in r['hits']]})
 report={'record_type':'candidate_supply_retrieval_probe/v1','scope':'Independent task paraphrases fixed before results; one small candidate cohort, not a held-out full-system benchmark.','candidates':16,'probes':rows,'rank_one':sum(x['rank']==1 for x in rows),'within_three':sum(x['rank']is not None for x in rows),'unrelated_probes':negative,'physical_model_calls':0,'normal_serving_excludes_candidates':True}
 args.evaluate.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['candidates','rank_one','within_three','physical_model_calls']}))
if __name__=='__main__':main()
