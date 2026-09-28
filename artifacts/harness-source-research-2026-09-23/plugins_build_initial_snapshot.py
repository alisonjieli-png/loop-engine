"""Final research-priority ranking over verified corpus snapshots and bounded primary reads."""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,heapq,json,math,re
from pathlib import Path,PurePosixPath
from urllib.parse import quote
import plugins_rank_research as discovery

HERE=Path(__file__).resolve().parent
SCORING_VERSION='plugin_research_priority/v3'
THEMES={**discovery.THEMES,
 'code_development':r'code|develop|engineer|program|refactor|(?:^|[\W_])(?:git|typescript|python|react|rust|java)(?:$|[\W_])|frontend|backend',
 'data_analytics':r'(?:^|[\W_])(?:data|sql|etl|csv)(?:$|[\W_])|analyt|database|postgres|sqlite|quant'}
METHODS={
 'testing_verification':'Separate draft production from deterministic checks and independent acceptance.',
 'context_memory':'Retrieve compact task-specific context with provenance and explicit freshness.',
 'planning_orchestration':'Represent planning, execution and repair as bounded typed operations with resumable state.',
 'code_development':'Package reusable development procedures behind declared input/output contracts.',
 'data_analytics':'Replace repeated model transformations with bounded deterministic data tools.',
 'browser_automation':'Separate page observation, target selection and authorized browser effects.',
 'security_policy':'Enforce permissions at tool boundaries and record explicit refusal reasons.',
 'operations_observability':'Expose operational checks as swappable engines with auditable results.',
 'design_ui_accessibility':'Turn design/accessibility knowledge into concrete review criteria and examples.',
 'research_documents':'Preserve source citations and uncertainty when compressing research into working context.',
 'business_product':'Represent role-specific decisions as reusable methods with explicit acceptance evidence.',
 'protocol_integration':'Adapt external protocols behind versioned contracts and declared capability requirements.',
 'general_agent_workflow':'Inspect how a small declared package combines reusable agent capabilities.'}


def strict_json(raw):
 def pairs(rows):
  out={}
  for key,value in rows:
   if key in out:raise ValueError('duplicate_json_key')
   out[key]=value
  return out
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite_literal')))

def details(entry):
 if not entry or not entry.get('verified_body'):return {},'not_observed'
 raw=discovery.Quarantine(discovery.CACHE/'quarantine').get(entry['verified_body'])
 try:value=strict_json(raw)
 except (ValueError,UnicodeError):return {},'manifest_bytes_noncanonical_json'
 if not isinstance(value,dict):return {},'manifest_bytes_nonobject_json'
 held={k:value[k] for k in ['name','description','version','$schema','license'] if isinstance(value.get(k),str)}
 held['component_fields']=[k for k in ['skills','agents','hooks','commands','mcpServers','extensions'] if k in value]
 held['keywords']=[x for x in value.get('keywords',[]) if isinstance(x,str)][:30] if isinstance(value.get('keywords'),list) else []
 return held,'primary_manifest_object_observed'

def base_score(item,primary):
 row=item['row'];entry=primary.get(item['research_id'],{});meta,evidence=details(entry)
 # Short keywords have token boundaries; owner names cannot manufacture a task domain.
 text=' '.join([item['repository'].split('/',1)[-1],item['logical_path'],meta.get('name',''),meta.get('description',''),*meta.get('keywords',[])])
 themes=[name for name,pattern in THEMES.items() if re.search(pattern,text,re.I)]
 usefulness=min(24,8+4*len(themes))
 component_count=sum(row.get(key)=='1' for key in ['has_skills_dir','has_agents_dir','has_hooks_dir','has_commands_dir','has_mcp_json','has_dot_mcp_json'])
 format_score=min(16,5+2*component_count+2*discovery.integer(row['has_root_manifest'])+(2 if item['conformance'] and item['conformance']['schema_ok']=='1' else 0))
 try:age=(discovery.ASOF-datetime.fromisoformat(row['repo_pushed_at'].replace('Z','+00:00'))).days
 except (ValueError,TypeError):age=None
 maintenance=0 if row['archived']=='1' else 15 if age is not None and age<=30 else 12 if age is not None and age<=90 else 8 if age is not None and age<=180 else 4 if age is not None and age<=365 else 1
 score={'purpose_keyword_heuristic':usefulness,'reported_component_format_evidence':format_score,
        'primary_manifest_observation':8 if evidence=='primary_manifest_object_observed' else 3 if entry.get('verified_body') else 0,
        'reported_maintenance':maintenance,
        'reported_license':10 if row['license'] in discovery.PERMISSIVE else 5 if row['license'] not in ('','NOASSERTION','NONE') else 0,
        'capped_repository_popularity':round(min(10,2*math.log10(discovery.integer(row['stars'])+1)),4),
        'example_template_penalty':-8 if re.search(r'(^|/)(test|tests|fixture|fixtures|example|examples|template|templates)(/|$)',item['logical_path'],re.I) else 0,
        'observed_missing_manifest_penalty':-12 if entry.get('status')==404 or entry.get('unknown_reason')=='repository_head_unavailable' else 0}
 return {**item,'primary':entry,'details':meta,'evidence':evidence,'themes':themes or ['general_agent_workflow'],
         'score_components':score,'base_score':sum(score.values())}

def choose(population,primary,count=1000):
 rows=[base_score(item,primary) for item in population]
 heap=[(-(r['base_score']+15),r['research_id'],i) for i,r in enumerate(rows)];heapq.heapify(heap)
 repos=Counter();owners=Counter();selected=[];fresh=set();fresh_names=set();skipped_same_manifest=0;skipped_same_name=0
 while heap and len(selected)<count:
  _,identity,index=heapq.heappop(heap);row=rows[index];repo=row['repository'].lower();owner=repo.split('/')[0]
  if repos[repo]>=8 or owners[owner]>=20:continue
  blob=row['primary'].get('verified_body');key=(repo,blob) if blob else None
  if key and key in fresh:skipped_same_manifest+=1;continue
  name=row['details'].get('name','').strip().casefold()
  name_key=(repo,name) if name else None
  if name_key and name_key in fresh_names:skipped_same_name+=1;continue
  diversity=round(10/(1+repos[repo])+5/(1+owners[owner]),4)
  components={**row['score_components'],'selection_diversity':diversity}
  score=float(sum(Decimal(str(v)) for v in components.values()))
  if heap and -heap[0][0]>score:
   heapq.heappush(heap,(-score,identity,index));continue
  selected.append({**row,'score_components':components,'priority_score':score})
  repos[repo]+=1;owners[owner]+=1
  if key:fresh.add(key)
  if name_key:fresh_names.add(name_key)
 return selected,{'fresh_same_repository_manifest_candidates_skipped':skipped_same_manifest,'fresh_same_repository_manifest_name_candidates_skipped':skipped_same_name}

def public_record(row,rank,stats):
 original=row['row'];entry=row['primary'];meta=row['details'];revision=entry.get('revision')
 path=original['manifest_source'];name=meta.get('name') or PurePosixPath(row['logical_path']).name or row['repository'].split('/')[-1]
 name=' '.join(name.split())[:256]
 source='https://github.com/'+row['repository']+'/blob/'+(revision or 'HEAD')+'/'+quote(path,safe='/')
 notes=['Research priority only; no source code was executed, imported or installed.',
        'Repository popularity, push date and license are reported snapshot metadata, not package quality or license clearance.',
        'Component presence and manifest parsing do not prove client compatibility, safety or usefulness.']
 if len(row['members'])>1:notes.append('Native projections and/or same-repository truncated manifest fingerprints were conservatively grouped; other package files were not compared.')
 if not entry.get('verified_body'):notes.append('Current manifest bytes were not confirmed; discovery remains backed by the pinned corpus export.')
 if entry.get('unknown_reason'):notes.append('Primary read observation: '+entry['unknown_reason']+'.')
 if revision is None:notes.append('Original upstream commit is absent from the exported corpus; the source location uses mutable HEAD.')
 return {'record_type':'harness_source_research_item/v1','category':'plugin','research_id':row['research_id'],
  'name':name,'repository':row['repository'],'source_url':source,'source_path':path,
  'source_snapshot_digest':entry.get('verified_body') or stats['artifact_snapshot_digest'],
  'source_snapshot_kind':'primary_manifest_bytes' if entry.get('verified_body') else 'agentpluginzoo_artifacts_csv',
  'upstream_revision':revision,'upstream_blob_sha':entry.get('blob_sha'),
  'license_reported':original['license'] if original['license'] not in ('','NOASSERTION','NONE') else None,
  'manifest_license_reported':meta.get('license'),'license_verified':False,
  'rank':rank,'priority_score':row['priority_score'],'score_components':row['score_components'],
  'scoring_recipe':SCORING_VERSION,'evidence_level':row['evidence'] if entry.get('verified_body') else 'pinned_research_metadata',
  'qualification_status':'unreviewed','compatibility_status':'unverified',
  'inspiration_methods':[METHODS[t] for t in row['themes'][:4]],'research_topics':row['themes'],
  'notes':notes,'logical_package_path':row['logical_path'],
  'reported_metadata':{'stars':discovery.integer(original['stars']),'repo_pushed_at':original['repo_pushed_at'] or None,
    'archived':original['archived']=='1','is_fork':original['is_fork']=='1','language':original['language'] or None,
    'component_directories':{k:original.get(k)=='1' for k in ['has_skills_dir','has_agents_dir','has_hooks_dir','has_commands_dir','has_mcp_json','has_dot_mcp_json']},
    'study_manifest_schema_ok':row['conformance']['schema_ok']=='1' if row['conformance'] else None,
    'manifest_fingerprint_24':original['content_hash'] or None},
  'primary_observation':{'status':entry.get('status'),'json_shape':row['evidence'],
    'api_response_digest':entry.get('response_digest'),'manifest_size_bytes':entry.get('size_bytes'),
    'declared_name':meta.get('name'),'declared_version':meta.get('version'),'declared_schema':meta.get('$schema'),
    'manifest_component_fields':meta.get('component_fields',[]),
    'matches_reported_manifest_fingerprint':entry['verified_body'][:24]==original['content_hash'] if entry.get('verified_body') else None},
  'corpus_provenance':{'repository':'tezansahu/agentpluginzoo','revision':discovery.CORPUS_REV,
    'artifact_csv_sha256':stats['artifact_snapshot_digest'],'artifact_id':original['artifact_id'],
    'artifact_row_sha256':discovery.sha(discovery.canonical(original)),
    'source_ids':original['source_ids'].split('|') if original['source_ids'] else [],
    'grouped_artifact_ids':sorted(x['artifact_id'] for x in row['members']),
    'grouped_bundle_paths':sorted(set(x['bundle_path'] for x in row['members'])),
    'reported_manifest_paths':sorted(set(path for x in row['members'] for path in json.loads(x['manifest_paths'] or '[]')))}}

def build(prefix="plugins"):
 population,stats=discovery.load_population();state=discovery.state_load()
 selected,extra=choose(population,state['primary']);records=[public_record(row,i+1,stats) for i,row in enumerate(selected)]
 if len(records)!=1000:raise ValueError('insufficient_eligible_discovery_population')
 aliases=defaultdict(list)
 for research_id,entry in state['primary'].items():
  meta,_=details(entry);name=meta.get('name','').strip().casefold()
  if name:aliases[(entry['repository'].lower(),name)].append({'research_id':research_id,'path':entry['path'],'revision':entry.get('revision'),'body_digest':entry.get('verified_body')})
 for record in records:
  name=(record['primary_observation']['declared_name'] or '').strip().casefold()
  record['primary_name_aliases']=sorted(aliases.get((record['repository'].lower(),name),[]),key=lambda x:x['path'])
  if len(record['primary_name_aliases'])>1:record['notes'].append('Same-repository observed manifest names are grouped conservatively; related native variants remain linked for review.')
 path=HERE/(prefix+'-ranked.jsonl')
 with path.open('x') as stream:
  for record in records:stream.write(json.dumps(record,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')
 evidence=Counter(r['evidence_level'] for r in records);topics=Counter(t for r in records for t in r['research_topics'])
 all_body=[v for v in state['primary'].values() if v.get('verified_body')]
 stats.update(extra)
 stats.update({'record_type':'plugin_research_population/v1','ranked_items':len(records),
  'distinct_ranked_repositories':len({r['repository'].lower() for r in records}),
  'distinct_ranked_owners':len({r['repository'].split('/')[0].lower() for r in records}),
  'maximum_items_one_repository':max(Counter(r['repository'].lower() for r in records).values()),
  'maximum_items_one_owner':max(Counter(r['repository'].split('/')[0].lower() for r in records).values()),
  'evidence_levels':dict(evidence),'topics':dict(topics),'license_verified_count':0,
  'reported_license_counts':dict(Counter(r['license_reported'] or 'unknown' for r in records)),
  'primary_manifest_attempts':len(state['primary']),'primary_manifest_verified_byte_reads':len(all_body),
  'primary_status_counts':dict(Counter(str(r.get('status')) for r in state['primary'].values())),
  'network_request_summary':state.get('request_summary'),'network_request_budget':state.get('request_budget'),
  'stopped_reason':state.get('stopped_reason'),'ranked_file_sha256':discovery.sha(path.read_bytes()),
  'scoring_recipe':SCORING_VERSION,'source_files':{name:discovery.sha((HERE/name).read_bytes()) for name in ['plugins_rank_research.py','plugins_build_ranked.py']},
  'raw_body_location':'outside_repository_content_addressed_quarantine',
  'upstream_code_executed':False,'qualification_or_approval_performed':False})
 with (HERE/(prefix+'-population.json')).open('x') as stream:json.dump(stats,stream,indent=2);stream.write('\n')
 with (HERE/(prefix+'-primary-observations.json')).open('x') as stream:
  json.dump({'record_type':'plugin_primary_observations/v1','observations':state['primary'],'heads':state['heads']},stream,indent=2);stream.write('\n')
 print(json.dumps({k:stats[k] for k in ['ranked_items','distinct_ranked_repositories','evidence_levels','primary_manifest_attempts','ranked_file_sha256']}))

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--prefix',choices=['plugins','plugins-initial'],default='plugins');args=parser.parse_args();build(args.prefix)
