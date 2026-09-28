"""Continue a recorded public discovery cursor; preserve the predecessor snapshot."""
from pathlib import Path
import json,sys
sys.path.insert(0,'/home/username/.le-codex-build/integration/src')
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget,RequestLog
from loop_engine.core.library_ingestion.quarantine import Quarantine
BASE=Path('/home/username/.le-codex-research-cache/four-catalogues-20260923')
HERE=Path(__file__).resolve().parent
output=BASE/'continuation-index.json'
if output.exists():raise ValueError('preserve prior run; use a new run path')
log=RequestLog(BASE/'continuation-requests.jsonl');budget=RequestBudget(maximum_requests=405,maximum_pause_seconds=30)
t=HttpsGetTransport(('raw.githubusercontent.com','registry.modelcontextprotocol.io','skills.sh','www.skills.sh'),budget,log,timeout_seconds=30,maximum_bytes=32*1024*1024)
q=Quarantine(BASE/'quarantine');records=[]
def get(name,host,path,query=None):
 r=t.get(host,path,query); e=q.put(r.body)
 records.append({'name':name,'host':host,'path':path,'query':query or {},'status':r.status,'sha256':e.digest,'bytes':e.size_bytes,'quarantine_file':str(BASE/'quarantine'/e.digest[:2]/e.digest)})
 output.write_text(json.dumps({'source_revision':'231f51bb1facab517fbe915b08ea9ac85f913347','sources':records,'requests':log.summary()},indent=2)+'\n')
 if len(records)%20==0 or r.status!=200 or len(records)<=2:print(json.dumps({'name':name,'status':r.status,'requests':budget.used}),flush=True)
 return r
get('agentpluginzoo:data/capabilities.csv','raw.githubusercontent.com','/tezansahu/agentpluginzoo/83259b7499efc86756b3913ee7d3000a6a668893/data/capabilities.csv')
get('skills_public_leaderboard','skills.sh','/')
state=json.loads((BASE/'registry-pagination.json').read_text());cursor=state['next_cursor'];seen={cursor};count=0;pages=0;failure=None
try:
 for index in range(100,500):
  if not cursor:break
  r=get(f'mcp_registry_latest_{index:03d}','registry.modelcontextprotocol.io','/v0.1/servers',{'version':'latest','limit':100,'cursor':cursor})
  if r.status!=200:failure='http_or_transport';break
  v=json.loads(r.body);pages+=1;count+=len(v.get('servers',[]));cursor=v.get('metadata',{}).get('nextCursor')
  if cursor and cursor in seen:raise ValueError('repeated_cursor')
  seen.add(cursor)
except Exception as error:failure=type(error).__name__
result={'pages_total':state['pages']+pages,'rows_total':state['rows']+count,'complete':not bool(cursor),'next_cursor':cursor,'failure':failure,'maximum_pages':500}
(BASE/'registry-pagination-continuation.json').write_text(json.dumps(result,indent=2)+'\n')
(HERE/'acquisition-continuation.json').write_text(output.read_text())
print(json.dumps({**result,'requests':log.summary()}),flush=True)
