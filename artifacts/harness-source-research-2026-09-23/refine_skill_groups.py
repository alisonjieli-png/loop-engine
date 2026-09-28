"""Collapse same-publisher named projections; inspect extra pinned skills without refetching cache."""
from pathlib import Path
import hashlib,json,re,sys
from collections import Counter,defaultdict
from urllib.parse import quote
sys.path.insert(0,'/home/username/.le-codex-build/integration/src')
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget,RequestLog
from loop_engine.core.library_ingestion.quarantine import Quarantine
HERE=Path(__file__).resolve().parent;BASE=Path('/home/username/.le-codex-research-cache/four-catalogues-20260923');RUN=BASE/'skills-primary-v1'
old=HERE/'skills-ranked.jsonl';before=HERE/'skills-ranked-before-logical-dedup.jsonl';assert not before.exists();before.write_bytes(old.read_bytes())
oldsummary=HERE/'skills-summary.json';(HERE/'skills-summary-before-logical-dedup.json').write_bytes(oldsummary.read_bytes())
rows=[json.loads(line) for line in (RUN/'discovered.jsonl').read_text().splitlines()]
cache={r['target']:r for r in (json.loads(line) for line in (RUN/'https-requests.jsonl').read_text().splitlines()) if r['status']==200 and r.get('body_digest')}
sourceidx=json.loads((RUN/'source-index.json').read_text());trees={r['repository']:r for r in sourceidx if '/git/trees/'in r['path'] and r['status']==200}
q=Quarantine(BASE/'quarantine');log=RequestLog(RUN/'logical-refinement-requests.jsonl');t=HttpsGetTransport(('raw.githubusercontent.com',),RequestBudget(550,maximum_pause_seconds=30),log,timeout_seconds=20,maximum_bytes=256*1024)
groups={};variants=defaultdict(list);failures=[];observed=set();scanned=0
for row in sorted(rows,key=lambda r:(-r['priority_score'],r['repository'],r['source_path'])):
 url='https://raw.githubusercontent.com/'+row['repository']+'/'+row['upstream_revision']+'/'+quote(row['source_path'],safe='/')
 try:
  if url in cache:
   digest=cache[url]['body_digest'];raw=q.get(digest)
  else:
   # Additional originals, capped by request authority. Existing cached variants still get recorded.
   if t.budget.used>=550:continue
   response=t.get('raw.githubusercontent.com',url.split('raw.githubusercontent.com',1)[1])
   entry=q.put(response.body)
   if response.status!=200:failures.append({'url':url,'reason':'unavailable','status':response.status});continue
   raw=response.body;digest=entry.digest
  scanned+=1
  if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['upstream_blob_sha']:raise ValueError('blob_mismatch')
  text=raw.decode('utf-8-sig')
  if not text.startswith('---\n') or '\n---' not in text[4:]:raise ValueError('frontmatter_missing')
  front=text[4:text.find('\n---',4)]; name=re.search(r'^name:\s*(.+?)\s*$',front,re.M);description=re.search(r'^description:\s*\S',front,re.M)
  if not name or not description:raise ValueError('required_metadata_missing')
  native_name=name.group(1).strip().strip('\"\'');key=(row['repository'],native_name.casefold())
  variants[key].append({'source_url':row['source_url'],'source_path':row['source_path'],'instruction_sha256':digest})
  if digest in observed:continue
  observed.add(digest)
  if key in groups:continue
  # Root-level SKILL.md owns the repository subtree for this inventory statistic.
  subtree_count=row['supporting_file_count']
  if row['source_path']=='SKILL.md':
   tree=json.loads(Path(trees[row['repository']]['quarantine_file']).read_text());subtree_count=sum(x.get('type')=='blob' and x['path']!='SKILL.md' for x in tree['tree'])
  components={**row['score_components'],'primary_body_and_metadata':15}
  groups[key]={**row,'record_type':'harness_source_research_item/v1','category':'skill','research_id':hashlib.sha256(('skill\0'+key[0]+'\0'+key[1]).encode()).hexdigest(),'license_verified':False,'evidence_level':'primary_instruction_bytes_checked','qualification_status':'unreviewed','compatibility_status':'unverified','instruction_sha256':digest,'instruction_bytes':len(raw),'frontmatter_name':native_name,'required_metadata_observed':True,'supporting_file_count':subtree_count,'inspiration_methods':['Design an original bounded task package from the documented workflow or verification idea.','Keep native adaptation, dependency qualification and task acceptance separate.'],'notes':['Research priority within a declared source population; not a universal quality rank.','Same-repository same-name projections are grouped conservatively; differences remain available for review.','Repository license is reported, not proof of rights for this skill or bundled assets.','Supporting-file count means other files in the directory subtree, not a resolved dependency closure.','No upstream code executed, dependencies loaded or native compatibility qualified.'],'score_components':components,'priority_score':round(sum(components.values()),6),'quarantine_digest':digest}
 except Exception as error:failures.append({'url':url,'reason':str(error) if str(error) in ('blob_mismatch','frontmatter_missing','required_metadata_missing') else type(error).__name__})
 if scanned%250==0:print(json.dumps({'inspected':scanned,'logical_groups':len(groups),'additional_requests':t.budget.used}),flush=True)
selected=[];counts=Counter()
for key,row in sorted(groups.items(),key=lambda kv:(-kv[1]['priority_score'],kv[0])):
 if counts[row['repository']]>=40:continue
 row['native_projection_count']=len(variants[key]);row['native_projections']=variants[key]
 counts[row['repository']]+=1;selected.append(row)
 if len(selected)==1000:break
with old.open('w') as f:
 for rank,row in enumerate(selected,1):row['rank']=rank;f.write(json.dumps(row,sort_keys=True,ensure_ascii=False)+'\n')
summary={'repository_population':87,'discovered_skills':len(rows),'primary_instruction_files_inspected':scanned,'distinct_instruction_byte_digests_inspected':len(observed),'logical_name_groups':len(groups),'selected':len(selected),'distinct_selected_instruction_digests':len({r['instruction_sha256'] for r in selected}),'selected_repositories':len(counts),'per_repository_logical_cap':40,'complete_target':len(selected)==1000,'additional_requests':log.summary(),'failure_count':len(failures),'qualification_status':'unreviewed','native_execution_performed':False,'initial_report':'skills-summary-before-logical-dedup.json','notes':'Conservative same-publisher named grouping, exact-byte duplicate collapse; aliases retained. Seed scope is87 public-leaderboard repositories, not the global skills population.'}
oldsummary.write_text(json.dumps(summary,indent=2)+'\n');(RUN/'logical-refinement-failures.json').write_text(json.dumps(failures,indent=2)+'\n')
print(json.dumps(summary),flush=True)
