"""Reproducible plugin research discovery/ranking; never executes upstream content."""
from __future__ import annotations
import argparse,base64,csv,hashlib,io,json,math,re,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from urllib.parse import quote

sys.dont_write_bytecode=True
OWNER=Path('/home/username/.le-codex-build/integration')
sys.path.insert(0,str(OWNER/'src'))
from loop_engine.core.library_ingestion.github_reader import GhCliReader
from loop_engine.core.library_ingestion.request_log import RequestBudget,RequestLog,PauseExceedsBound,RequestCeilingReached
from loop_engine.core.library_ingestion.quarantine import Quarantine
HERE=Path(__file__).resolve().parent
CACHE=Path('/home/username/.le-codex-research-cache/plugin-research-20260923')
INDEX=Path('/home/username/.le-codex-research-cache/four-catalogues-20260923/initial-index.json')
CORPUS_REV='83259b7499efc86756b3913ee7d3000a6a668893'
ASOF=datetime(2026,9,23,tzinfo=timezone.utc)
NATIVE=re.compile(r'^\.[a-z0-9-]+-plugin$')
PERMISSIVE={'MIT','Apache-2.0','BSD-2-Clause','BSD-3-Clause','ISC','0BSD','Unlicense','CC0-1.0','Zlib'}
THEMES={
 'testing_verification':r'test|evaluat|benchmark|review|debug|quality|validat',
 'context_memory':r'context|memory|rag|retriev|knowledge|recall',
 'planning_orchestration':r'plan|workflow|agentic|orchestrat|coordinat|spec.?driven|architect|sdd|brainstorm',
 'code_development':r'code|develop|engineer|program|refactor|git|typescript|python|react|rust|java|frontend|backend',
 'data_analytics':r'data|sql|analyt|database|postgres|sqlite|csv|etl|quant',
 'browser_automation':r'browser|playwright|web.?automat|selenium|scrap|crawl',
 'security_policy':r'secur|audit|policy|compliance|auth|credential|threat|pentest',
 'operations_observability':r'devops|deploy|docker|kubernetes|infra|monitor|observ|sre|incident|cloud|telemetry',
 'design_ui_accessibility':r'design|ui.?ux|accessib|figma|web.?design|design.?system',
 'research_documents':r'research|document|paper|pdf|citation|writing|markdown|obsidian',
 'business_product':r'product|business|marketing|finance|sales|customer|support|commerce|startup',
 'protocol_integration':r'\bmcp\b|protocol|integration|connector|openapi|schema|plugin.?sdk|tool.?registry',
}

def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def integer(value):
 try:return int(value)
 except (ValueError,TypeError):return 0

def sources():
 index=json.loads(INDEX.read_text());answer={}
 for row in index['sources']:
  if not row['name'].startswith('agentpluginzoo:'):continue
  raw=Path(row['quarantine_file']).read_bytes()
  if sha(raw)!=row['sha256'] or len(raw)!=row['bytes']:raise ValueError('cached_source_integrity_mismatch')
  answer[row['name'].split(':',1)[1]]=(row,raw)
 return answer

def tables():
 held=sources()
 answer={name:list(csv.DictReader(io.StringIO(held['data/'+name+'.csv'][1].decode('utf-8')))) for name in ['artifacts','repos','conformance','source_ledger']}
 answer['sources']={key:value[0] for key,value in held.items()}
 return answer

def logical_path(path):
 parts=list(PurePosixPath(path).parts) if path else []
 while parts and NATIVE.fullmatch(parts[-1]):parts.pop()
 return '/'.join(parts)

def load_population():
 data=tables();artifacts=[row for row in data['artifacts'] if row['stratum']=='A_plugin']
 conform={row['artifact_id']:row for row in data['conformance']}
 parent=list(range(len(artifacts)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def union(a,b):
  a,b=find(a),find(b)
  if a!=b:parent[b]=a
 paths,hashes={},{}
 for i,row in enumerate(artifacts):
  repo=row['full_name'].lower();key=(repo,logical_path(row['bundle_path']))
  if key in paths:union(i,paths[key])
  else:paths[key]=i
  if row['content_hash']:
   key=(repo,row['content_hash'])
   if key in hashes:union(i,hashes[key])
   else:hashes[key]=i
 groups=defaultdict(list)
 for i,row in enumerate(artifacts):groups[find(i)].append(row)
 population=[]
 for members in groups.values():
  eligible=[r for r in members if r['fetch_state']=='done' and r['manifest_source'].endswith('plugin.json')]
  if not eligible:continue
  def preferred(r):
   path=r['manifest_source'];root=logical_path(r['bundle_path'])
   return (0 if path==((root+'/') if root else '')+'plugin.json' else 1 if '/.claude-plugin/' in '/'+path else 2,
           len(PurePosixPath(root).parts),len(path),r['artifact_id'])
  row=min(eligible,key=preferred)
  logical=min((logical_path(r['bundle_path']) for r in members),key=lambda x:(len(PurePosixPath(x).parts),len(x),x))
  identity=sha(canonical({'repository':row['full_name'].lower(),'logical_path':logical}))
  population.append({'research_id':'plugin-'+identity[:24],'repository':row['full_name'], 'logical_path':logical,
    'row':row,'members':members,'conformance':conform.get(row['artifact_id'])})
 stats={'artifact_rows':len(data['artifacts']),'strata':dict(Counter(r['stratum'] for r in data['artifacts'])),
        'repo_rows':len(data['repos']),'conformance_rows':len(data['conformance']),
        'plugin_artifact_ids_joined_to_conformance':sum(r['artifact_id'] in conform for r in artifacts),
        'plugin_rows':len(artifacts),'logical_groups':len(groups),'eligible_logical_groups':len(population),
        'native_projection_or_same_repo_fingerprint_rows_collapsed':len(artifacts)-len(groups),
        'source_ledger_rows':len(data['source_ledger']),
        'unexhausted_source_routes':sum(r['exhausted']!='1' for r in data['source_ledger']),
        'artifact_snapshot_digest':data['sources']['data/artifacts.csv']['sha256'],
        'source_snapshots':{key:{k:v for k,v in value.items() if k!='quarantine_file'} for key,value in data['sources'].items()}}
 return population,stats

def manifest_details(entry):
 if not entry or entry.get('status')!=200 or not entry.get('verified_body'):return {}
 raw=Quarantine(CACHE/'quarantine').get(entry['verified_body'])
 try:
  value=json.loads(raw)
  if not isinstance(value,dict):return {}
  details={key:value[key] for key in ['name','description','version','$schema','license'] if isinstance(value.get(key),str)}
  details['component_fields']=[key for key in ('skills','agents','hooks','commands','mcpServers','extensions') if key in value]
  details['keywords']=[x for x in value.get('keywords',[]) if isinstance(x,str)][:30] if isinstance(value.get('keywords'),list) else []
  details['json_object_observed']=True
  return details
 except (ValueError,UnicodeError):return {}

def scored(item,primary):
 row=item['row'];entry=primary.get(item['research_id'],{});details=manifest_details(entry)
 text=' '.join([item['repository'],item['logical_path'],details.get('name',''),details.get('description',''),*details.get('keywords',[])])
 themes=[name for name,pattern in THEMES.items() if re.search(pattern,text,re.I)]
 useful=min(24,8+4*len(themes))
 components=sum(row.get(key)=='1' for key in ['has_skills_dir','has_agents_dir','has_hooks_dir','has_commands_dir','has_mcp_json','has_dot_mcp_json'])
 format_points=min(16,5+2*components+2*integer(row['has_root_manifest']))
 if item['conformance'] and item['conformance']['schema_ok']=='1':format_points=min(16,format_points+2)
 evidence=8 if details.get('json_object_observed') else 0
 try:age=(ASOF-datetime.fromisoformat(row['repo_pushed_at'].replace('Z','+00:00'))).days
 except (ValueError,TypeError):age=None
 maintenance=0 if row['archived']=='1' else 15 if age is not None and age<=30 else 12 if age is not None and age<=90 else 8 if age is not None and age<=180 else 4 if age is not None and age<=365 else 1
 license_score=10 if row['license'] in PERMISSIVE else 5 if row['license'] not in ('','NOASSERTION','NONE') else 0
 popularity=round(min(10,2*math.log10(integer(row['stars'])+1)),4)
 noise=-8 if re.search(r'(^|/)(test|tests|fixture|fixtures|example|examples|template|templates)(/|$)',item['logical_path'],re.I) else 0
 scores={'purpose_usefulness':useful,'reported_format_evidence':format_points,'fresh_manifest_evidence':evidence,
         'reported_maintenance':maintenance,'reported_license':license_score,'capped_popularity':popularity,
         'example_template_penalty':noise}
 return {**item,'details':details,'primary':entry,'themes':themes or ['general_agent_workflow'],'base_components':scores,'base_score':sum(scores.values())}

def rank(population,primary,count=1000):
 import heapq
 candidates=[scored(item,primary) for item in population]
 heap=[(-(row['base_score']+15),row['research_id'],index) for index,row in enumerate(candidates)];heapq.heapify(heap)
 repos=Counter();owners=Counter();selected=[]
 while heap and len(selected)<count:
  neg,identity,index=heapq.heappop(heap);row=candidates[index];repo=row['repository'].lower();owner=repo.split('/')[0]
  if repos[repo]>=8 or owners[owner]>=20:continue
  diversity=10/(1+repos[repo])+5/(1+owners[owner]);score=round(row['base_score']+diversity,4)
  if heap and -heap[0][0]>score:
   heapq.heappush(heap,(-score,identity,index));continue
  row['score_components']={**row['base_components'],'selection_diversity':round(diversity,4)}
  row['priority_score']=round(sum(row['score_components'].values()),4);selected.append(row);repos[repo]+=1;owners[owner]+=1
 return selected

def state_load():
 p=CACHE/'state.json'
 return json.loads(p.read_text()) if p.exists() else {'responses':{},'primary':{},'heads':{},'stopped_reason':None}

def state_save(state):
 temporary=CACHE/'state.partial';temporary.write_text(json.dumps(state,indent=2)+'\n');temporary.replace(CACHE/'state.json')

def collect(limit=1160):
 CACHE.mkdir(parents=True,exist_ok=True);state=state_load();log=RequestLog(CACHE/'requests.jsonl')
 if log.path.exists():log.records=[json.loads(line) for line in log.path.read_text().splitlines() if line]
 budget=RequestBudget(maximum_requests=1200,maximum_pause_seconds=30,reserve=500,used=len(log.records))
 reader=GhCliReader(budget,log,timeout_seconds=30,maximum_bytes=4*1024*1024);quarantine=Quarantine(CACHE/'quarantine')
 def get(target):
  if target in state['responses']:
   saved=state['responses'][target];return saved,json.loads(quarantine.get(saved['body_digest'])) if saved['status']==200 else None
  response=reader.get(target);entry=quarantine.put(response.body)
  saved={'target':target,'status':response.status,'body_digest':entry.digest,'bytes':entry.size_bytes}
  state['responses'][target]=saved;state_save(state)
  try:value=json.loads(response.body) if response.status==200 else None
  except ValueError:value=None
  return saved,value
 population,stats=load_population();initial=rank(population,{},1000)
 if not (HERE/'plugins-initial-discovery-order.json').exists():
  (HERE/'plugins-initial-discovery-order.json').write_text(json.dumps({'source_snapshot_digest':stats['artifact_snapshot_digest'],'research_ids':[r['research_id'] for r in initial]},indent=2)+'\n')
 try:
  saved,value=get('rate_limit')
  if value:
   core=value['resources']['core'];budget.respect_allowance(core['remaining'],core['reset'],'GitHub')
  # Data licensing and the study's fingerprint implementation are primary source reads.
  get('repos/tezansahu/agentpluginzoo/contents/LICENSE-DATA?ref='+CORPUS_REV)
  saved,tree=get('repos/tezansahu/agentpluginzoo/git/trees/'+CORPUS_REV+'?recursive=1')
  if isinstance(tree,dict):
   state['study_collector_paths']=[entry['path'] for entry in tree.get('tree',[]) if entry.get('type')=='blob' and entry.get('path','').startswith('collector/') and entry['path'].endswith('.py')]
   state_save(state)
  for row in initial:
   key=row['research_id']
   if key in state['primary']:continue
   if budget.used>=limit:state['stopped_reason']='declared_collection_ceiling';break
   repo=row['repository']
   if repo not in state['heads']:
    saved,value=get('repos/'+repo+'/commits/HEAD')
    revision=value.get('sha') if isinstance(value,dict) else None
    state['heads'][repo]={'revision':revision if isinstance(revision,str) and re.fullmatch('[0-9a-f]{40}',revision) else None,'response_digest':saved['body_digest'],'status':saved['status']};state_save(state)
   head=state['heads'][repo]
   entry={'repository':repo,'path':row['row']['manifest_source'],'revision':head['revision'],'status':None}
   if not head['revision']:
    entry['unknown_reason']='repository_head_unavailable';state['primary'][key]=entry;state_save(state);continue
   if budget.used>=limit:state['stopped_reason']='declared_collection_ceiling';break
   target='repos/'+repo+'/contents/'+quote(entry['path'],safe='/')+'?ref='+head['revision']
   saved,value=get(target);entry.update(status=saved['status'],response_digest=saved['body_digest'])
   if isinstance(value,dict) and value.get('type')=='file' and value.get('encoding')=='base64' and value.get('path')==entry['path']:
    try:
     raw=base64.b64decode(''.join(value['content'].split()),validate=True)
     blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
     if blob!=value.get('sha') or len(raw)!=value.get('size'):raise ValueError('blob_mismatch')
     held=quarantine.put(raw);entry.update(verified_body=held.digest,blob_sha=blob,size_bytes=held.size_bytes)
    except (ValueError,KeyError,TypeError):entry['unknown_reason']='file_content_integrity_unavailable'
   else:entry['unknown_reason']='manifest_file_unavailable_or_unsupported'
   state['primary'][key]=entry;state_save(state)
   if len(state['primary'])%25==0:print(json.dumps({'manifests_attempted':len(state['primary']),'requests_used':budget.used,'last_status':entry['status']}),flush=True)
 except (PauseExceedsBound,RequestCeilingReached) as error:
  state['stopped_reason']=type(error).__name__;state_save(state)
 finally:
  state['request_summary']=log.summary();state['request_budget']={'ceiling':1200,'used':budget.used,'remaining_reserve':500,'maximum_pause_seconds':30,'pauses':budget.pauses};state_save(state)
 print(json.dumps({'requests':state['request_summary'],'manifests_attempted':len(state['primary']),'stopped_reason':state['stopped_reason']}),flush=True)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['inspect','collect']);parser.add_argument('--ceiling',type=int,default=1160);args=parser.parse_args()
 if args.operation=='collect':collect(min(args.ceiling,1160));return
 population,stats=load_population();print(json.dumps(stats,indent=2));print('\nINITIAL PRIORITIES')
 for row in rank(population,{},25):print(row['repository'],row['logical_path'],row['priority_score'],row['themes'])
if __name__=='__main__':main()
