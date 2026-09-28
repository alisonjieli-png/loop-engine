"""Pinned primary-source skill discovery and a reproducible research-priority list."""
from pathlib import Path
import concurrent.futures,hashlib,json,math,re,sys,threading
from datetime import datetime,timezone
from urllib.parse import quote
sys.path.insert(0,'/home/username/.le-codex-build/integration/src')
from loop_engine.core.library_ingestion.github_reader import GhCliReader
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget,RequestLog
from loop_engine.core.library_ingestion.quarantine import Quarantine
HERE=Path(__file__).resolve().parent
BASE=Path('/home/username/.le-codex-research-cache/four-catalogues-20260923')
RUN=BASE/'skills-primary-v1';RUN.mkdir(exist_ok=False)
q=Quarantine(BASE/'quarantine')
gh=GhCliReader(RequestBudget(400,maximum_pause_seconds=30,reserve=500),RequestLog(RUN/'github-requests.jsonl'),timeout_seconds=30,maximum_bytes=16*1024*1024)
http=HttpsGetTransport(('raw.githubusercontent.com',),RequestBudget(1800,maximum_pause_seconds=30),RequestLog(RUN/'https-requests.jsonl'),timeout_seconds=20,maximum_bytes=256*1024)
public=json.loads((BASE/'skills-public-extracted.json').read_text())
leader={}
for item in public['skills']:
 if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}',item['source']):leader[(item['source'].lower(),item['skillId'].lower())]=item
repositories=sorted({x[0] for x in leader},key=lambda repo:-max(int(v.get('installs',0)) for (r,_),v in leader.items() if r==repo))
raw_sources=[];discovered=[];failures=[]
def api(repo,route):
 response=gh.get(route);entry=q.put(response.body)
 raw_sources.append({'repository':repo,'path':route,'status':response.status,'sha256':entry.digest,'quarantine_file':str(BASE/'quarantine'/entry.digest[:2]/entry.digest)})
 (RUN/'source-index.json').write_text(json.dumps(raw_sources,indent=2)+'\n')
 return json.loads(response.body) if response.status==200 else None
for index,repo in enumerate(repositories):
 try:
  meta=api(repo,'repos/'+repo)
  if not meta or meta.get('archived'):failures.append({'repository':repo,'reason':'unavailable_or_archived'});continue
  commit=api(repo,'repos/'+repo+'/commits/'+quote(meta['default_branch'],safe=''))
  if not commit:continue
  revision=commit['sha'];tree=api(repo,f'repos/{repo}/git/trees/{revision}?recursive=1')
  if not tree or tree.get('truncated'):failures.append({'repository':repo,'reason':'tree_missing_or_truncated'});continue
  entries=tree['tree'];seen=set()
  for item in entries:
   path=item.get('path','');parts=path.split('/')
   if item.get('type')!='blob' or parts[-1]!='SKILL.md':continue
   if any(p.lower() in ('node_modules','.venv','venv','.git','fixtures','__fixtures__','testdata','tests','test','__tests__') for p in parts[:-1]):continue
   if item.get('size',0)>256*1024 or item['sha'] in seen:continue
   seen.add(item['sha']);folder='/'.join(parts[:-1]);name=parts[-2] if len(parts)>1 else repo.split('/')[-1]
   advertised=leader.get((repo,name.lower()),{})
   terms=(name+' '+folder).lower();terms=re.sub(r'[^a-z0-9]+',' ',terms).split()
   categories={k for k,words in {'software':['code','coding','test','testing','debug','git','review','repo','agent','skill','tool','plugin','mcp','context'], 'data':['data','csv','sql','schema','analytics','database','search','embedding'], 'operations':['deploy','deployment','security','cloud','incident','workflow','automation'], 'product':['design','ui','ux','marketing','copy','accessibility','customer','sales'], 'research':['research','paper','benchmark','evaluation','analysis']}.items() if set(terms)&set(words)}
   license_=(meta.get('license')or{}).get('spdx_id') or 'unknown'
   reported_installs=advertised.get('installs')
   components={'task_relevance':min(20,6+7*len(categories)), 'reported_license_clarity':12 if license_ in ('MIT','Apache-2.0','BSD-2-Clause','BSD-3-Clause','ISC','CC0-1.0') else 0,'primary_source_pin':15,'public_usage_signal':min(20,3*math.log10(1+reported_installs)) if reported_installs is not None else 0,'repository_popularity':min(10,2*math.log10(1+meta.get('stargazers_count',0))),'not_archived':5}
   discovered.append({'repository':repo,'source_path':path,'upstream_revision':revision,'upstream_blob_sha':item['sha'],'name':name,'source_url':f'https://github.com/{repo}/blob/{revision}/'+quote(path,safe='/'),'license_reported':license_,'source_snapshot_digest':raw_sources[-1]['sha256'],'reported_installs':reported_installs,'repository_stars':meta.get('stargazers_count'),'repository_pushed_at':meta.get('pushed_at'),'relevance_classes':sorted(categories),'score_components':components,'priority_score':round(sum(components.values()),6),'supporting_file_count':sum(1 for e in entries if e.get('type')=='blob' and e['path'].startswith(folder+'/') and e['path']!=path),'leaderboard_page_sha256':public['page_sha256']})
 except Exception as error:failures.append({'repository':repo,'reason':type(error).__name__})
 if (index+1)%10==0:print(json.dumps({'repositories_visited':index+1,'discovered_skills':len(discovered),'failures':len(failures)}),flush=True)
with (RUN/'discovered.jsonl').open('x') as f:
 for row in discovered:f.write(json.dumps(row,sort_keys=True)+'\n')
# Select a bounded comparison population with a per-repository cap, retaining exclusions.
ordered=sorted(discovered,key=lambda r:(-r['priority_score'],r['repository'],r['source_path']))
counts={};population=[]
for row in ordered:
 if counts.get(row['repository'],0)>=40:continue
 counts[row['repository']]=counts.get(row['repository'],0)+1;population.append(row)
 if len(population)>=1600:break
observed=[];body_seen={}
for index,row in enumerate(population):
 try:
  response=http.get('raw.githubusercontent.com','/'+row['repository']+'/'+row['upstream_revision']+'/'+quote(row['source_path'],safe='/'))
  entry=q.put(response.body)
  if response.status!=200:failures.append({'source_url':row['source_url'],'reason':'body_unavailable','status':response.status});continue
  git_hash=hashlib.sha1(b'blob '+str(len(response.body)).encode()+b'\0'+response.body).hexdigest()
  if git_hash!=row['upstream_blob_sha']:failures.append({'source_url':row['source_url'],'reason':'git_blob_mismatch'});continue
  text=response.body.decode('utf-8-sig')
  if not text.startswith('---\n') or '\n---' not in text[4:]:failures.append({'source_url':row['source_url'],'reason':'frontmatter_not_observed'});continue
  front=text[4:text.find('\n---',4)]
  name_match=re.search(r'^name:\s*(.+?)\s*$',front,re.M);description_match=re.search(r'^description:\s*\S',front,re.M)
  if not name_match or not description_match:failures.append({'source_url':row['source_url'],'reason':'required_metadata_not_observed'});continue
  if entry.digest in body_seen:failures.append({'source_url':row['source_url'],'reason':'duplicate_instruction_bytes','duplicate_of':body_seen[entry.digest]});continue
  body_seen[entry.digest]=row['source_url']
  record={**row,'record_type':'harness_source_research_item/v1','category':'skill','research_id':hashlib.sha256(('skill\0'+row['repository']+'\0'+row['source_path']).encode()).hexdigest(),'license_verified':False,'evidence_level':'primary_instruction_bytes_checked','qualification_status':'unreviewed','compatibility_status':'unverified','instruction_sha256':entry.digest,'instruction_bytes':entry.size_bytes,'frontmatter_name':name_match.group(1).strip().strip('\"\''),'required_metadata_observed':True,'inspiration_methods':['Use the task decomposition or verification idea to design an original bounded package.','Qualify dependencies, native loading and exact output independently before serving.'],'notes':['Research priority within a documented source population; not a universal quality rank.','Reported repository license may not cover every bundled skill or asset.','Only SKILL.md bytes were read; supporting files were inventoried, not executed or qualified.','Popularity and installs are reported signals, not unique users or task success.'],'quarantine_digest':entry.digest}
  record['score_components']={**record['score_components'],'primary_body_and_metadata':15}
  record['priority_score']=round(sum(record['score_components'].values()),6);observed.append(record)
 except Exception as error:failures.append({'source_url':row['source_url'],'reason':type(error).__name__})
 if (index+1)%100==0:print(json.dumps({'primary_files_attempted':index+1,'unique_inspected_skills':len(observed)}),flush=True)
 # Inspect a buffer beyond 1,000, so final ranking incorporates the same byte checks.
 if len(observed)>=1200:break
observed.sort(key=lambda r:(-r['priority_score'],r['repository'],r['source_path']))
selected=observed[:1000]
with (HERE/'skills-ranked.jsonl').open('x') as f:
 for rank,row in enumerate(selected,1):row['rank']=rank;f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+'\n')
summary={'repository_population':len(repositories),'discovered_skills':len(discovered),'comparison_population':len(population),'unique_primary_skills_checked':len(observed),'selected':len(selected),'unique_instruction_digests':len({r['instruction_sha256'] for r in selected}),'per_repository_population_cap':40,'complete_target':len(selected)==1000,'github_requests':gh.log.summary(),'https_requests':http.log.summary(),'failure_or_exclusion_count':len(failures),'limits':'Public leaderboard seed scope only; not all global skills. No upstream code executed, no skill approved or installed; license scope and complete dependencies remain unqualified.'}
(HERE/'skills-summary.json').write_text(json.dumps(summary,indent=2)+'\n');(RUN/'failures-and-exclusions.json').write_text(json.dumps(failures,indent=2)+'\n')
print(json.dumps(summary),flush=True)
