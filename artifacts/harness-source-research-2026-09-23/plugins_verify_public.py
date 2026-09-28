"""Verify anonymous access to the exact inspected manifest bytes, with no credential."""
from __future__ import annotations
import json,time
from urllib.parse import quote
import plugins_rank_research as source
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget,RequestLog,PauseExceedsBound,RequestCeilingReached


def main():
 path=source.CACHE/'public-state.json'
 held=json.loads(path.read_text()) if path.exists() else {'observations':{}}
 log=RequestLog(source.CACHE/'anonymous-requests.jsonl')
 if log.path.exists():log.records=[json.loads(line) for line in log.path.read_text().splitlines() if line]
 budget=RequestBudget(maximum_requests=1100,maximum_pause_seconds=30,used=len(log.records),
   paused_seconds=sum(row['seconds'] for row in held.get('budget',{}).get('pauses',[]) if row['taken']),
   pauses=list(held.get('budget',{}).get('pauses',[])))
 transport=HttpsGetTransport(('raw.githubusercontent.com',),budget,log,timeout_seconds=30,maximum_bytes=4*1024*1024)
 quarantine=source.Quarantine(source.CACHE/'quarantine')
 def save():
  temporary=path.with_suffix('.partial');temporary.write_text(json.dumps(held,indent=2)+'\n');temporary.replace(path)
 try:
  while True:
   state=source.state_load()
   pending=[(key,entry) for key,entry in state['primary'].items() if entry.get('verified_body') and key not in held['observations']]
   if not pending:
    if state.get('stopped_reason') is not None:held['stopped_reason']='all_available_primary_bytes_checked';break
    time.sleep(3);continue
   for key,entry in pending:
    target='/'+entry['repository']+'/'+entry['revision']+'/'+quote(entry['path'],safe='/')
    response=transport.get('raw.githubusercontent.com',target)
    raw=quarantine.put(response.body)
    matched=response.status==200 and raw.digest==entry['verified_body']
    held['observations'][key]={'status':response.status,'same_bytes_anonymously_available':matched,
      'body_digest':raw.digest,'expected_digest':entry['verified_body'],'revision':entry['revision'],
      'source_path':entry['path'],'source_url':'https://raw.githubusercontent.com'+target,
      'outcome':'public_exact_bytes_observed' if matched else 'anonymous_source_unavailable' if response.status!=200 else 'anonymous_bytes_differ'}
    save()
    if len(held['observations'])%50==0:print(json.dumps({'anonymous_checks':len(held['observations']),'confirmed':sum(x['same_bytes_anonymously_available'] for x in held['observations'].values()),'requests':budget.used}),flush=True)
 except (PauseExceedsBound,RequestCeilingReached) as error:held['stopped_reason']=type(error).__name__
 finally:
  held['requests']=log.summary();held['budget']={'maximum_requests':1100,'used':budget.used,'maximum_pause_seconds':30,'pauses':budget.pauses};save()
  print(json.dumps({'checks':len(held['observations']),'confirmed':sum(x['same_bytes_anonymously_available'] for x in held['observations'].values()),'stopped_reason':held.get('stopped_reason')}),flush=True)
if __name__=='__main__':main()
