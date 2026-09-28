"""Research acquisition through the existing bounded source transport; never import fetched code."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,'/home/username/.le-codex-build/integration/src')
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget,RequestLog
from loop_engine.core.library_ingestion.quarantine import Quarantine
BASE=Path('/home/username/.le-codex-research-cache/four-catalogues-20260923')
BASE.mkdir(parents=True,exist_ok=True)
HERE=Path(__file__).resolve().parent
log=RequestLog(BASE/'initial-requests.jsonl')
budget=RequestBudget(maximum_requests=120,maximum_pause_seconds=30)
transport=HttpsGetTransport(('raw.githubusercontent.com','www.schemastore.org','api.apis.guru','registry.modelcontextprotocol.io','skills.sh'),budget,log,timeout_seconds=30,maximum_bytes=32*1024*1024)
quarantine=Quarantine(BASE/'quarantine')
records=[]
def get(name,host,path,query=None):
 response=transport.get(host,path,query)
 entry=quarantine.put(response.body)
 record={'name':name,'host':host,'path':path,'query':query or {},'status':response.status,'sha256':entry.digest,'bytes':entry.size_bytes,'quarantine_file':str(BASE/'quarantine'/entry.digest[:2]/entry.digest)}
 records.append(record)
 (BASE/'initial-index.json').write_text(json.dumps({'source_revision':'231f51bb1facab517fbe915b08ea9ac85f913347','sources':records,'requests':log.summary()},indent=2)+'\n')
 print(json.dumps({k:record[k] for k in ('name','status','bytes','sha256')}),flush=True)
 return response
pin='83259b7499efc86756b3913ee7d3000a6a668893'
for name in ('README.md','LICENSE','data/README.md','data/source_ledger.csv','data/repos.csv','data/artifacts.csv','data/conformance.csv'):
 get('agentpluginzoo:'+name,'raw.githubusercontent.com',f'/tezansahu/agentpluginzoo/{pin}/{name}')
get('schemastore_catalog','www.schemastore.org','/api/json/catalog.json')
get('apis_guru_list','api.apis.guru','/v2/list.json')
# This public documentation describes authentication. An HTTP401 is recorded; no bypass.
get('skills_leaderboard','skills.sh','/api/v1/skills',{'view':'all-time','per_page':500,'page':0})
count=0;cursor=None;seen=set();pages=[]
for index in range(100):
 query={'version':'latest','limit':100}
 if cursor:query['cursor']=cursor
 r=get(f'mcp_registry_latest_{index:03d}','registry.modelcontextprotocol.io','/v0.1/servers',query)
 if r.status!=200:break
 value=json.loads(r.body); pages.append(value);count+=len(value.get('servers',[]))
 cursor=value.get('metadata',{}).get('nextCursor')
 if not cursor:break
 if cursor in seen:raise ValueError('registry_cursor_repeated')
 seen.add(cursor)
(BASE/'registry-pagination.json').write_text(json.dumps({'pages':len(pages),'rows':count,'complete':not bool(cursor),'next_cursor':cursor,'request_ceiling':120,'maximum_pages':100},indent=2)+'\n')
(HERE/'acquisition.json').write_text((BASE/'initial-index.json').read_text())
print(json.dumps({'registry_pages':len(pages),'registry_rows':count,'registry_complete':not bool(cursor),'requests':log.summary()}),flush=True)
