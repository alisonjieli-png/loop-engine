"""Separately budgeted continuation: inspect every selected plugin path when available."""
from __future__ import annotations
import base64,json,re
from collections import Counter
from urllib.parse import quote
import plugins_rank_research as source
import plugins_build_ranked as ranking
from loop_engine.core.library_ingestion.request_log import RequestBudget,RequestLog,PauseExceedsBound,RequestCeilingReached
from loop_engine.core.library_ingestion.github_reader import GhCliReader,ReadOnlyRequestRefused


def main():
 state=source.state_load();initial=json.loads((source.CACHE/'initial-state-completed.json').read_text())
 path=source.CACHE/'continuation-requests.jsonl';log=RequestLog(path)
 if path.exists():log.records=[json.loads(line) for line in path.read_text().splitlines() if line]
 previous=state.get('continuation_budget',{})
 budget=RequestBudget(maximum_requests=1200,maximum_pause_seconds=30,reserve=500,used=len(log.records),
  paused_seconds=sum(row['seconds'] for row in previous.get('pauses',[]) if row['taken']),pauses=list(previous.get('pauses',[])))
 reader=GhCliReader(budget,log,timeout_seconds=30,maximum_bytes=4*1024*1024)
 quarantine=source.Quarantine(source.CACHE/'quarantine')
 def get(target,force=False):
  if not force and target in state['responses']:
   saved=state['responses'][target];raw=quarantine.get(saved['body_digest'])
   try:value=json.loads(raw) if saved['status']==200 else None
   except ValueError:value=None
   return saved,value
  response=reader.get(target);held=quarantine.put(response.body)
  saved={'target':target,'status':response.status,'body_digest':held.digest,'bytes':held.size_bytes,'campaign':'continuation'}
  state['responses'][target]=saved;source.state_save(state)
  try:value=json.loads(response.body) if response.status==200 else None
  except ValueError:value=None
  return saved,value
 def inspect(row):
  key=row['research_id'];repo=row['repository'];entry={'repository':repo,'path':row['row']['manifest_source'],'revision':None,'status':None,'campaign':'continuation'}
  try:
   if repo not in state['heads']:
    saved,value=get('repos/'+repo+'/commits/HEAD');revision=value.get('sha') if isinstance(value,dict) else None
    state['heads'][repo]={'revision':revision if isinstance(revision,str) and re.fullmatch('[0-9a-f]{40}',revision) else None,'response_digest':saved['body_digest'],'status':saved['status']};source.state_save(state)
   entry['revision']=state['heads'][repo]['revision']
   if not entry['revision']:entry['unknown_reason']='repository_head_unavailable'
   else:
    target='repos/'+repo+'/contents/'+quote(entry['path'],safe='/')+'?ref='+entry['revision']
    saved,value=get(target);entry.update(status=saved['status'],response_digest=saved['body_digest'])
    if isinstance(value,dict) and value.get('type')=='file' and value.get('encoding')=='base64' and value.get('path')==entry['path']:
     try:
      raw=base64.b64decode(''.join(value['content'].split()),validate=True)
      blob=source.hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
      if blob!=value.get('sha') or len(raw)!=value.get('size'):raise ValueError('blob_mismatch')
      held=quarantine.put(raw);entry.update(verified_body=held.digest,blob_sha=blob,size_bytes=held.size_bytes)
     except (ValueError,KeyError,TypeError):entry['unknown_reason']='file_content_integrity_unavailable'
    else:entry['unknown_reason']='manifest_file_unavailable_or_unsupported'
  except ReadOnlyRequestRefused:entry['unknown_reason']='read_only_transport_path_not_supported'
  state['primary'][key]=entry;source.state_save(state)
 population,stats=source.load_population()
 state['stopped_reason']=None
 try:
  _,value=get('rate_limit',force=True)
  if value:
   core=value['resources']['core'];budget.respect_allowance(core['remaining'],core['reset'],'GitHub')
  while True:
   selected,_=ranking.choose(population,state['primary'])
   pending=[row for row in selected if row['research_id'] not in state['primary']]
   if not pending:
    state['stopped_reason']='all_selected_manifest_paths_attempted';break
   for row in pending[:50]:
    inspect(row)
    if len(state['primary'])%25==0:
     print(json.dumps({'all_manifest_attempts':len(state['primary']),'continuation_requests':budget.used,'pending_at_batch_start':len(pending)}),flush=True)
 except (PauseExceedsBound,RequestCeilingReached) as error:
  state['stopped_reason']=type(error).__name__
 finally:
  state['continuation_request_summary']=log.summary()
  state['continuation_budget']={'ceiling':1200,'used':budget.used,'remaining_reserve':500,'maximum_pause_seconds':30,'pauses':budget.pauses}
  counts=Counter(initial['request_summary']['by_outcome']);counts.update(log.summary()['by_outcome'])
  state['request_summary']={'requests':initial['request_summary']['requests']+len(log.records),'by_outcome':dict(counts),'bytes':initial['request_summary']['bytes']+log.summary()['bytes']}
  state['request_budget']={'maximum_campaign_requests':initial['request_summary']['requests']+1200,'used':state['request_summary']['requests'],
    'initial':initial['request_budget'],'continuation':state['continuation_budget']}
  state['source_tooling_revision']='231f51bb1facab517fbe915b08ea9ac85f913347'
  source.state_save(state)
  print(json.dumps({'stopped_reason':state['stopped_reason'],'requests':state['request_summary'],'all_manifest_attempts':len(state['primary'])}),flush=True)

if __name__=='__main__':main()
