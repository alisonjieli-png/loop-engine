"""Independent read-only review of the final skill index and cached source bindings."""
from __future__ import annotations
import hashlib,json,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
HERE=Path(__file__).resolve().parent
BASE=Path('/home/username/.le-codex-research-cache/four-catalogues-20260923')
RUN=BASE/'skills-primary-v1'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def held(digest):
 path=BASE/'quarantine'/digest[:2]/digest
 if path.is_symlink():raise ValueError('unexpected_cache_symlink')
 raw=path.read_bytes()
 if sha(raw)!=digest:raise ValueError('cached_source_digest_mismatch')
 return raw

def main():
 index_path=HERE/'skills-ranked.jsonl';before=index_path.read_bytes()
 rows=[json.loads(line) for line in before.decode().splitlines()]
 sources=json.loads((RUN/'source-index.json').read_text())
 metadata={row['repository'].lower():row for row in sources if row['path']=='repos/'+row['repository'] and row['status']==200}
 trees_by_digest=defaultdict(list)
 for source_row in sources:
  if '/git/trees/' in source_row['path'] and source_row['status']==200:trees_by_digest[source_row['sha256']].append(source_row)
 public={}
 for name in ['https-requests.jsonl','logical-refinement-requests.jsonl']:
  for line in (RUN/name).read_text().splitlines():
   row=json.loads(line)
   if row['status']==200 and row['transport']=='https_get' and row['host']=='raw.githubusercontent.com':
    public.setdefault(row['target'],set()).add(row['body_digest'])
 checks={
  'exactly_1000_records':len(rows)==1000,
  'unique_research_ids':len({r['research_id'] for r in rows})==1000,
  'unique_same_publisher_names':len({(r['repository'].lower(),r['frontmatter_name'].casefold()) for r in rows})==1000,
  'unique_instruction_sha256':len({r['instruction_sha256'] for r in rows})==1000,
  'continuous_rank':[r['rank'] for r in rows]==list(range(1,1001)),
  'descending_priority':all(a['priority_score']>=b['priority_score'] for a,b in zip(rows,rows[1:])),
  'score_sum_rounded_six_places':all(round(sum(r['score_components'].values()),6)==r['priority_score'] for r in rows),
  'research_only_status_flags':all(r['record_type']=='harness_source_research_item/v1' and r['category']=='skill' and r['qualification_status']=='unreviewed' and r['compatibility_status']=='unverified' and r['license_verified'] is False for r in rows),
  'per_repository_cap_40':max(Counter(r['repository'].lower() for r in rows).values())<=40,
 }
 cached_trees={};cached_meta={};failures=[];alias_count=0;alias_bytes_checked=0
 for row in rows:
  issues=[];repo=row['repository'];revision=row['upstream_revision'];path=row['source_path']
  raw=held(row['instruction_sha256'])
  if row['quarantine_digest']!=row['instruction_sha256'] or len(raw)!=row['instruction_bytes']:issues.append('instruction_sha_size')
  if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['upstream_blob_sha']:issues.append('git_blob_binding')
  tree_digest=row['source_snapshot_digest']
  if tree_digest not in cached_trees:cached_trees[tree_digest]=json.loads(held(tree_digest))
  tree=cached_trees[tree_digest]
  matching=trees_by_digest.get(tree_digest,[])
  if not any(source['path']=='repos/'+repo+'/git/trees/'+revision+'?recursive=1' for source in matching) or tree.get('truncated') is not False:issues.append('complete_tree_request_binding')
  entries={entry['path']:entry for entry in tree['tree']}
  if entries.get(path,{}).get('sha')!=row['upstream_blob_sha'] or entries.get(path,{}).get('type')!='blob':issues.append('tree_entry')
  if row['source_url']!='https://github.com/'+repo+'/blob/'+revision+'/'+quote(path,safe='/'):issues.append('pinned_source_url')
  raw_url='https://raw.githubusercontent.com/'+repo+'/'+revision+'/'+quote(path,safe='/')
  if row['instruction_sha256'] not in public.get(raw_url,set()):issues.append('anonymous_primary_read')
  if repo.lower() not in cached_meta:
   meta_source=metadata.get(repo.lower());cached_meta[repo.lower()]=json.loads(held(meta_source['sha256'])) if meta_source else {}
  meta=cached_meta[repo.lower()]
  if meta.get('private') is not False or meta.get('archived') is not False:issues.append('public_active_repository_metadata')
  if row.get('repository_id')!=meta.get('id') or row.get('canonical_repository')!=meta.get('full_name'):issues.append('canonical_repository_metadata_binding')
  expected_license=(meta.get('license') or {}).get('spdx_id') or 'unknown'
  if row['license_reported']!=expected_license:issues.append('reported_license_source')
  expected_id=sha(('skill\0'+repo+'\0'+row['frontmatter_name'].casefold()).encode())
  if row['research_id']!=expected_id:issues.append('stable_named_group_id')
  folder=path.rsplit('/',1)[0] if '/' in path else ''
  supporting=sum(entry.get('type')=='blob' and entry['path']!=path and (not folder or entry['path'].startswith(folder+'/')) for entry in tree['tree'])
  if row['supporting_file_count']!=supporting:issues.append('supporting_subtree_count')
  variants=row['native_projections'];alias_count+=len(variants)
  if row['native_projection_count']!=len(variants) or not variants:issues.append('alias_count')
  if len({v['source_path'] for v in variants})!=len(variants):issues.append('duplicate_alias_path')
  representative=False
  for variant in variants:
   vp=variant['source_path'];vraw=held(variant['instruction_sha256']);alias_bytes_checked+=1
   blob=hashlib.sha1(b'blob '+str(len(vraw)).encode()+b'\0'+vraw).hexdigest()
   if entries.get(vp,{}).get('sha')!=blob:issues.append('alias_git_blob')
   if variant['source_url']!='https://github.com/'+repo+'/blob/'+revision+'/'+quote(vp,safe='/'):issues.append('alias_revision_scope')
   url='https://raw.githubusercontent.com/'+repo+'/'+revision+'/'+quote(vp,safe='/')
   if variant['instruction_sha256'] not in public.get(url,set()):issues.append('alias_anonymous_read')
   text=vraw.decode('utf-8-sig');front=text[4:text.find('\n---',4)] if text.startswith('---\n') else ''
   observed=re.search(r'^name:\s*(.+?)\s*$',front,re.M)
   if not observed or observed.group(1).strip().strip('\"\'').casefold()!=row['frontmatter_name'].casefold():issues.append('alias_named_group')
   if vp==path and variant['instruction_sha256']==row['instruction_sha256']:representative=True
  if not representative:issues.append('representative_in_alias_group')
  held(row['leaderboard_page_sha256'])
  if issues:failures.append({'research_id':row['research_id'],'issues':sorted(set(issues))})
 canonical_keys={(cached_meta[row['repository'].lower()].get('id'),row['frontmatter_name'].casefold()) for row in rows}
 checks['canonical_repository_ids_present']=all(type(meta.get('id')) is int for meta in cached_meta.values())
 checks['unique_canonical_repository_id_and_skill_name']=len(canonical_keys)==1000
 checks['all_cached_bytes_tree_blob_alias_and_public_bindings']=not failures
 checks['source_index_unchanged_during_review']=index_path.read_bytes()==before
 summary={'record_type':'skills_independent_integrity_review/v1','at':datetime.now(timezone.utc).isoformat(),
  'checks':checks,'passed':all(checks.values()),'records':len(rows),'repository_addresses':len(cached_meta),'canonical_repository_ids':len({meta['id'] for meta in cached_meta.values()}),
  'distinct_instruction_digests':len({r['instruction_sha256'] for r in rows}),
  'aliases_checked':alias_count,'alias_bodies_checked':alias_bytes_checked,
  'failures':failures,'source_index_sha256':sha(before),'review_script_sha256':sha(Path(__file__).read_bytes()),
  'network_calls':0,'upstream_code_executed':False,
  'scope':'Counts, score arithmetic, cached bytes, Git/tree/projection bindings, anonymous fetch records, public repository metadata and research-only flags; no compatibility, license clearance or semantic task qualification.'}
 output=HERE/'skills-independent-integrity-review-final.json'
 with output.open('x') as stream:json.dump(summary,stream,indent=2);stream.write('\n')
 print(json.dumps({key:summary[key] for key in ['passed','records','repository_addresses','canonical_repository_ids','distinct_instruction_digests','aliases_checked','source_index_sha256']}))
 if failures:print(json.dumps(failures[:8]))
 if not summary['passed']:raise SystemExit(1)
if __name__=='__main__':main()
