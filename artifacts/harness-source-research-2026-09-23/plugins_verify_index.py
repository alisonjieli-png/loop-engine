"""Independent final-index integrity checks; reads only frozen files, never the network."""
from __future__ import annotations
import base64,csv,hashlib,io,json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote
HERE=Path(__file__).resolve().parent
CACHE=Path('/home/username/.le-codex-research-cache/plugin-research-20260923')

def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def held(digest):
 path=CACHE/'quarantine'/digest[:2]/digest
 if path.is_symlink():raise ValueError('symlink_cache')
 raw=path.read_bytes()
 if sha(raw)!=digest:raise ValueError('quarantine_digest_mismatch')
 return raw

def load_records():return [json.loads(line) for line in (HERE/'plugins-ranked.jsonl').read_text().splitlines()]
def structural(rows):
 return {
 'exactly_1000':len(rows)==1000,
 'unique_research_ids':len({r['research_id'] for r in rows})==len(rows),
 'unique_logical_locations':len({(r['repository'].lower(),r['logical_package_path']) for r in rows})==len(rows),
 'rank_sequence':[r['rank'] for r in rows]==list(range(1,len(rows)+1)),
 'descending_priority':all(a['priority_score']>=b['priority_score'] for a,b in zip(rows,rows[1:])),
 'component_sum':all(Decimal(str(r['priority_score']))==sum(Decimal(str(v)) for v in r['score_components'].values()) for r in rows),
 'unreviewed_and_unverified':all(r['record_type']=='harness_source_research_item/v1' and r['category']=='plugin' and r['qualification_status']=='unreviewed' and r['compatibility_status']=='unverified' and r['license_verified'] is False for r in rows),
 'repository_diversity_bound':max(Counter(r['repository'].lower() for r in rows).values())<=8,
 'owner_diversity_bound':max(Counter(r['repository'].split('/')[0].lower() for r in rows).values())<=20,
 }

def main():
 rows=load_records();checks=structural(rows)
 initial=json.loads(Path('/home/username/.le-codex-research-cache/four-catalogues-20260923/initial-index.json').read_text())
 source=next(r for r in initial['sources'] if r['name']=='agentpluginzoo:data/artifacts.csv')
 data=Path(source['quarantine_file']).read_bytes()
 if sha(data)!=source['sha256']:raise ValueError('corpus_source_changed')
 original={r['artifact_id']:r for r in csv.DictReader(io.StringIO(data.decode()))}
 proof=json.loads((CACHE/'public-state.json').read_text())['observations']
 failures=[];seen_hashes=set();seen_names=set();fresh=0
 for row in rows:
  problems=[];provenance=row['corpus_provenance'];item=original[provenance['artifact_id']]
  if item['stratum']!='A_plugin' or item['full_name']!=row['repository'] or item['manifest_source']!=row['source_path']:problems.append('corpus_identity')
  if sha(canonical(item))!=provenance['artifact_row_sha256'] or provenance['artifact_csv_sha256']!=source['sha256']:problems.append('corpus_digest')
  if any(member not in original or original[member]['full_name'].lower()!=row['repository'].lower() for member in provenance['grouped_artifact_ids']):problems.append('alias_scope')
  if row['source_snapshot_kind']=='primary_manifest_bytes':
   fresh+=1;raw=held(row['source_snapshot_digest']);revision=row['upstream_revision']
   if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['upstream_blob_sha']:problems.append('git_blob_digest')
   api=json.loads(held(row['primary_observation']['api_response_digest']))
   if api.get('type')!='file' or api.get('encoding')!='base64' or api.get('path')!=row['source_path'] or api.get('sha')!=row['upstream_blob_sha']:problems.append('api_file_binding')
   if base64.b64decode(''.join(api.get('content','').split()),validate=True)!=raw:problems.append('api_bytes')
   p=proof.get(row['research_id'],{});url='https://raw.githubusercontent.com/'+row['repository']+'/'+revision+'/'+quote(row['source_path'],safe='/')
   if not(row['primary_observation']['anonymous_public_verified'] is True and p.get('same_bytes_anonymously_available') is True and p.get('status')==200 and p.get('body_digest')==row['source_snapshot_digest']==p.get('expected_digest') and p.get('source_url')==url):problems.append('anonymous_public_bytes')
   expected_url='https://github.com/'+row['repository']+'/blob/'+revision+'/'+quote(row['source_path'],safe='/')
   if row['source_url']!=expected_url:problems.append('immutable_source_url')
   key=(row['repository'].lower(),row['source_snapshot_digest'])
   if key in seen_hashes:problems.append('duplicate_current_manifest')
   seen_hashes.add(key)
   name=(row['primary_observation']['declared_name'] or '').strip().casefold()
   key=(row['repository'].lower(),name)
   if name and key in seen_names:problems.append('duplicate_current_manifest_name')
   if name:seen_names.add(key)
  else:
   if row['source_snapshot_digest']!=source['sha256'] or row['upstream_blob_sha'] is not None:problems.append('metadata_only_scope')
  if problems:failures.append({'research_id':row['research_id'],'problems':problems})
 checks['all_source_rows_and_primary_bytes_bind']=not failures
 checks['all_selected_have_primary_public_bytes']=fresh==1000
 # Mutated in-memory records, never edits to the exported list.
 bad=[dict(row) for row in rows];bad[0]['qualification_status']='approved'
 checks['approval_flag_mutation_detected']=not structural(bad)['unreviewed_and_unverified']
 bad=[dict(row) for row in rows];bad[1]['research_id']=bad[0]['research_id']
 checks['duplicate_identity_mutation_detected']=not structural(bad)['unique_research_ids']
 result={'record_type':'plugin_research_index_verification/v1','checks':checks,'passed':all(checks.values()),
  'records':len(rows),'public_primary_bytes_verified':fresh,'failures':failures,
  'ranked_file_sha256':sha((HERE/'plugins-ranked.jsonl').read_bytes()),
  'source_artifact_csv_sha256':source['sha256'],'network_calls':0,'upstream_code_executed':False}
 with (HERE/'plugins-index-verification.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
 print(json.dumps({'passed':result['passed'],'checks':len(checks),'records':len(rows),'public_primary_bytes_verified':fresh,'failures':len(failures)}))
 if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
