"""Derived local research metadata index over immutable ranked JSONL snapshots.

Uses the existing CatalogStore and candidate-aware intelligence query contracts.
Never fetches upstream bodies, launches a source, or promotes research records.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import parse_qsl, unquote, urlsplit

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/username/.le-codex-research-cache/four-catalogues-20260923')
CANONICAL = Path('/home/username/.le-codex-build/integration')
SOURCE_REVISION = '231f51bb1facab517fbe915b08ea9ac85f913347'
CATEGORIES = ('skill', 'plugin', 'contract', 'tool')
SOURCE_FILES = {category: HERE/f'{category}s-ranked.jsonl' for category in CATEGORIES}
QUARANTINES = (CACHE/'quarantine', Path('/home/username/.le-codex-research-cache/plugin-research-20260923/quarantine'))
DEFAULT_DB = CACHE/'research-index.db'
DEFAULT_MANIFEST = HERE/'research-index-manifest.json'
NAMESPACE = 'research:local:four-catalogues-20260923'
COLLECTION = 'codex_research_metadata_20260923'
LAYER = 'context_intelligence'
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
ITEM_TYPE = 'harness_source_research_item/v1'
MANIFEST_TYPE = 'local_research_index_manifest/v1'


class ResearchIndexError(ValueError):
    """A bounded validation or source-integrity refusal; no untrusted value is echoed."""


def need(value, code):
    if not value:
        raise ResearchIndexError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    out = {}
    for key, value in pairs:
        need(key not in out, 'duplicate_json_key')
        out[key] = value
    return out


def strict_json(raw):
    def nonfinite(_value):
        raise ResearchIndexError('nonfinite_json')
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, str):
                item.encode('utf-8')
            elif type(item) is float:
                need(math.isfinite(item), 'nonfinite_json')
            elif isinstance(item, dict):
                pending.extend(item.keys()); pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        return value
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ResearchIndexError('invalid_json') from exc


def public_source_url(value):
    """Validate navigation URLs without DNS lookup or network access."""
    need(isinstance(value, str) and 0 < len(value) <= 8192, 'unsafe_source_url')
    decoded = unquote(value)
    need(not any(ord(c) <= 32 or ord(c) == 127 for c in value), 'unsafe_source_url')
    need(not any(ord(c) < 32 or ord(c) == 127 for c in decoded) and '\\' not in decoded, 'unsafe_source_url')
    need(not re.search(r'%(?![0-9a-fA-F]{2})',value),'unsafe_source_url')
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        need(parsed.scheme == 'https' and not parsed.username and not parsed.password and parsed.port in (None,443), 'unsafe_source_url')
        need(host and host == host.lower() and not host.endswith(('.localhost','.local','.internal','.lan','.home','.test','.invalid')), 'unsafe_source_url')
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            need(bool(re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z][a-z0-9-]*', host)), 'unsafe_source_url')
        else:
            need(address.is_global, 'unsafe_source_url')
        private_keys = {'token','access_token','api_key','apikey','key','secret','password','credential','authorization','auth','signature','sig'}
        need(not any(k.lower() in private_keys or k.lower().startswith('x-amz-') for k,_v in parse_qsl(parsed.query,keep_blank_values=True)), 'unsafe_source_url')
    except ValueError as exc:
        if isinstance(exc, ResearchIndexError):
            raise
        raise ResearchIndexError('unsafe_source_url') from exc
    return value


def validate_rows(rows, category):
    need(category in CATEGORIES and isinstance(rows,list) and len(rows)==1000, 'population_count_invalid')
    ids = set()
    for row in rows:
        need(isinstance(row,dict) and row.get('record_type')==ITEM_TYPE and row.get('category')==category, 'source_record_invalid')
        identity = row.get('research_id')
        need(isinstance(identity,str) and bool(re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',identity)), 'research_id_invalid')
        need(identity not in ids,'duplicate_research_id'); ids.add(identity)
        need(isinstance(row.get('name'),str) and 0 < len(row['name']) <= 1024, 'source_name_invalid')
        need(row.get('qualification_status')=='unreviewed' and row.get('compatibility_status')=='unverified'
             and row.get('license_verified') is False and row.get('execution_available',False) is False
             and row.get('approved',False) is False and row.get('lifecycle','candidate')=='candidate', 'candidate_status_required')
        need(isinstance(row.get('source_snapshot_digest'),str) and bool(HEX64.fullmatch(row['source_snapshot_digest'])), 'source_digest_invalid')
        public_source_url(row.get('source_url'))
        repository = row.get('repository')
        if isinstance(repository,str) and '://' in repository:
            public_source_url(repository)
        licence=row.get('license_reported')
        need(licence is None or isinstance(licence,str) or
             (isinstance(licence,dict) and set(licence)<= {'name','url'} and isinstance(licence.get('name'),str)
              and ('url' not in licence or isinstance(licence['url'],str))), 'rights_metadata_invalid')
        need(isinstance(row.get('evidence_level'),str) and bool(row['evidence_level']),'source_evidence_invalid')
        number = row.get('priority_score')
        components = row.get('score_components')
        need(type(number) in (int,float) and math.isfinite(number) and isinstance(components,dict)
             and all(type(x) in (int,float) and math.isfinite(x) for x in components.values())
             and math.isclose(sum(components.values()),number,abs_tol=0.00001), 'priority_score_invalid')
    need(all(type(row.get('rank')) is int for row in rows) and [row['rank'] for row in rows]==list(range(1,1001)), 'rank_sequence_invalid')
    return rows


def runtime_fingerprint():
    """Require the explicitly pinned first-party source, including package data."""
    command = ['git','-C',str(CANONICAL)]
    checked = subprocess.run(command+['diff','--quiet',SOURCE_REVISION,'--','src/loop_engine'],capture_output=True,timeout=15)
    need(checked.returncode==0,'canonical_source_changed')
    extra = subprocess.run(command+['ls-files','--others','--exclude-standard','src/loop_engine'],capture_output=True,timeout=15,check=True)
    need(not extra.stdout.strip(),'canonical_source_untracked')
    listing = subprocess.run(command+['ls-files','-z','src/loop_engine'],capture_output=True,timeout=15,check=True)
    paths = [p.decode() for p in listing.stdout.split(b'\0') if p]
    fingerprint = sha(json.dumps([(p,sha((CANONICAL/p).read_bytes())) for p in paths],separators=(',',':')).encode())
    return {'revision': SOURCE_REVISION, 'classpath': str(CANONICAL/'src'),
            'tracked_source_files': len(paths), 'source_tree_sha256': fingerprint,
            'local_helper_sha256':sha(Path(__file__).read_bytes())}


def api():
    sys.path.insert(0,str(CANONICAL/'src'))
    from loop_engine.catalog.protocol import CatalogRecordPrecondition, CatalogWriteBatch, require_atomic_batch
    from loop_engine.catalog.query import IntelligenceQuery
    from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
    from loop_engine.core.intelligence_layers import IntelligenceSearchRequest, query_intelligence
    from loop_engine.core.store_serve import StoreRecord
    return SQLiteRecordStore, CatalogWriteBatch, CatalogRecordPrecondition, require_atomic_batch, IntelligenceQuery, StoreRecord, IntelligenceSearchRequest, query_intelligence


def load_sources(source_files, quarantine_roots):
    need(set(source_files)==set(CATEGORIES),'source_set_invalid')
    sources, records, identities, required_digests = {}, [], set(), set()
    for category in CATEGORIES:
        path = Path(source_files[category])
        need(path.is_file() and not path.is_symlink(),'source_file_invalid')
        raw = path.read_bytes()
        need(0 < len(raw) <= 32*1024*1024 and raw.endswith(b'\n'),'source_file_bounds')
        lines = [line+b'\n' for line in raw.split(b'\n')[:-1]]
        need(all(0 < len(line) <= 256*1024 for line in lines),'source_line_bounds')
        rows = validate_rows([strict_json(line) for line in lines],category)
        sources[category] = {'path':str(path.resolve()),'filename':path.name,'sha256':sha(raw),'bytes':len(raw),'rows':len(rows)}
        for line_number,(line,row) in enumerate(zip(lines,rows),1):
            need(row['research_id'] not in identities,'duplicate_research_id')
            identities.add(row['research_id']); required_digests.add(row['source_snapshot_digest'])
            records.append({'record_id':row['research_id'],'record_version':sha(line),'intelligence_layer':LAYER,
                            'source_collection':COLLECTION,'artifact_kind':'research_source_metadata','lifecycle':'candidate',
                            'namespace':NAMESPACE,'attributes':{'category':category,'execution_available':False},
                            'payload':{'record_type':'local_research_source_payload/v1','source_line':line.decode('utf-8'),
                                       'source_line_sha256':sha(line),'source_filename':path.name,'source_line_number':line_number}})
    snapshots=[]
    for digest in sorted(required_digests):
        candidates=[Path(root)/digest[:2]/digest for root in quarantine_roots]
        held=next((p for p in candidates if p.is_file() and not p.is_symlink()),None)
        need(held is not None,'source_snapshot_missing')
        need(sha(held.read_bytes())==digest,'source_snapshot_digest_mismatch')
        snapshots.append({'sha256':digest,'local_path':str(held)})
    return records,sources,snapshots


def search_record(record, StoreRecord):
    row = strict_json(record['payload']['source_line'])
    pieces = [row['name'],str(row.get('repository') or '')]
    for field in ('inspiration_methods','declared_families','research_topics','relevance_classes','native_file_patterns','contract_kind'):
        value=row.get(field)
        if isinstance(value,list): pieces.extend(str(x) for x in value)
        elif isinstance(value,str): pieces.append(value)
    return StoreRecord(row['research_id'],'context',row['name'],
                       body={'text':' '.join(pieces),'lifecycle':'candidate','maturity':'candidate','execution_available':False,
                             'facets':{'category':row['category'],'scope':'local_research','lifecycle':'candidate'}},
                       tags=(row['category'],'research_metadata'),tier='experimental',source='local_research_snapshot')


def assert_sources_current(source_files, sources):
    need(set(source_files)==set(sources),'source_file_drift')
    for category, expected in sources.items():
        path=Path(source_files[category])
        need(path.is_file() and not path.is_symlink() and sha(path.read_bytes())==expected['sha256'],'source_file_drift')


def build_index(source_files, database, manifest_path, *, authorize=False, isolated_root=CACHE, quarantine_roots=QUARANTINES):
    need(authorize is True,'authorization_required')
    database,manifest_path=Path(database),Path(manifest_path)
    need(database.parent.resolve()==Path(isolated_root).resolve() and database.suffix=='.db','index_not_isolated')
    need(not database.exists() and not database.is_symlink() and not manifest_path.exists() and not manifest_path.is_symlink(),'existing_index_refused')
    runtime=runtime_fingerprint()
    records,sources,snapshots=load_sources(source_files,quarantine_roots)
    Store,Batch,Precondition,require_atomic,Query,Record,Search,query=api()
    descriptor=os.open(database,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(descriptor)
    store=Store(str(database))
    try:
        require_atomic(store)
        batch=Batch.from_records(records,tuple(Precondition(r['record_id'],must_not_exist=True) for r in records))
        acknowledgment=store.apply_batch(batch)
        need(acknowledgment.committed is True and acknowledgment.batch_digest==batch.digest,'write_acknowledgment_mismatch')
        readback=0
        for record in records:
            need(store.get(record['record_id'],record['record_version'])==record,'readback_payload_mismatch')
            readback+=1
        need(store.health()['record_count']==len(records),'readback_count_mismatch')
        active=store.query(Query(namespaces=(NAMESPACE,),lifecycle=('active',)))
        need(not active,'active_record_leak')
        default=query(Search('research metadata', {LAYER:[search_record(r,Record) for r in records]},mode='lexical',include_candidates=False,top_n=1))
        need(not default['hits'] and len(default['excluded'])==len(records),'default_query_candidate_leak')
        health=store.health()
    finally:
        store.close()
    assert_sources_current(source_files,sources)
    manifest={'record_type':MANIFEST_TYPE,'authoritative_input':'ranked_jsonl_files','derived_index':True,'runtime':runtime,
              'sources':sources,'source_snapshot_count':len(snapshots),'verified_source_snapshots':snapshots,
              'database_path':str(database.resolve()),'database_sha256':sha(database.read_bytes()),
              'records':len(records),'readback_exact_payloads':readback,'batch_digest':batch.digest,
              'batch_acknowledged':True,'active_store_rows':0,'default_active_search_hits':0,
              'default_active_search_excluded':len(default['excluded']),'lifecycle':'candidate','execution_available':False,
              'store_health':health,'network_requests':0,'model_calls':0,'upstream_programs_executed':0}
    with manifest_path.open('x',encoding='utf-8') as stream:
        json.dump(manifest,stream,indent=2);stream.write('\n')
    return manifest


def metadata_hit(record, query_score=None):
    need(record['lifecycle']=='candidate' and record['attributes'].get('execution_available') is False,'candidate_index_drift')
    payload=record['payload'];line=payload['source_line'].encode('utf-8')
    need(sha(line)==payload['source_line_sha256']==record['record_version'],'candidate_index_drift')
    row=strict_json(line)
    public_source_url(row['source_url'])
    return {'research_id':row['research_id'],'category':row['category'],'name':row['name'],'repository':row.get('repository'),
            'source_url':row['source_url'],'source_path':row.get('source_path'),'source_snapshot_digest':row['source_snapshot_digest'],
            'rank':row['rank'],'priority_score':row['priority_score'],'query_score':query_score,
            'evidence_level':row['evidence_level'],'qualification_status':'unreviewed','compatibility_status':'unverified',
            'rights_state':{'license_reported':row.get('license_reported'),'license_verified':False,'clearance':'not_established'},
            'lifecycle':'candidate','execution_available':False}


def query_index(source_files, database, manifest_path, *, query=None, lookup=None, category=None, limit=10):
    need((query is None)!=(lookup is None),'query_or_lookup_required')
    need(category is None or category in CATEGORIES,'category_invalid')
    need(type(limit) is int and 1<=limit<=100,'limit_invalid')
    need(query is None or isinstance(query,str) and 0<len(query.strip())<=512,'query_invalid')
    need(lookup is None or isinstance(lookup,str) and 0<len(lookup)<=128,'lookup_invalid')
    runtime=runtime_fingerprint()
    manifest=strict_json(Path(manifest_path).read_bytes())
    need(manifest.get('record_type')==MANIFEST_TYPE and manifest.get('runtime')==runtime,'index_manifest_or_runtime_drift')
    assert_sources_current(source_files,manifest['sources'])
    database=Path(database)
    need(database.is_file() and not database.is_symlink() and sha(database.read_bytes())==manifest['database_sha256'],'index_database_drift')
    Store,_Batch,_Precondition,_require_atomic,Query,Record,Search,search=api()
    store=Store(str(database),read_only=True)
    try:
        if lookup is not None:
            record=store.get(lookup)
            hits=[metadata_hit(record)] if record and record['namespace']==NAMESPACE and (category is None or record['attributes']['category']==category) else []
        else:
            pool=store.query(Query(namespaces=(NAMESPACE,),lifecycle=('candidate',),
                                   attributes={'category':{'equals':category}} if category else {}))
            result=search(Search(query,{LAYER:[search_record(r,Record) for r in pool]},mode='lexical',include_candidates=True,top_n=limit))
            by_id={r['record_id']:r for r in pool}
            hits=[metadata_hit(by_id[hit['record_id']],hit['score']) for hit in result['hits']]
    finally:
        store.close()
    assert_sources_current(source_files,manifest['sources'])
    need(sha(database.read_bytes())==manifest['database_sha256'],'index_database_drift')
    return {'record_type':'local_research_metadata_results/v1','mode':'exact_id' if lookup else 'lexical',
            'category':category,'query':query,'lookup':lookup,'candidate_selection_explicit':True,'execution_available':False,
            'source_integrity':'current_hashes_match_manifest','query_scoring':'existing lexical FTS5/BM25 order with reciprocal-rank score; separate from research priority',
            'hits':hits,'network_requests':0,'model_calls':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    build=commands.add_parser('build')
    build.add_argument('--authorize-isolated-index',action='store_true')
    search=commands.add_parser('search')
    search.add_argument('--category',choices=CATEGORIES)
    match=search.add_mutually_exclusive_group(required=True)
    match.add_argument('--query');match.add_argument('--lookup')
    search.add_argument('--limit',type=int,default=10)
    for command in (build,search):
        command.add_argument('--database',type=Path,default=DEFAULT_DB)
        command.add_argument('--manifest',type=Path,default=DEFAULT_MANIFEST)
    args=parser.parse_args()
    try:
        if args.command=='build':
            value=build_index(SOURCE_FILES,args.database,args.manifest,authorize=args.authorize_isolated_index)
            value={k:v for k,v in value.items() if k!='verified_source_snapshots'}
        else:
            need(args.database.parent.resolve()==CACHE.resolve(),'index_not_isolated')
            value=query_index(SOURCE_FILES,args.database,args.manifest,query=args.query,lookup=args.lookup,category=args.category,limit=args.limit)
        print(json.dumps(value,ensure_ascii=False,indent=2))
        return 0
    except (ResearchIndexError,OSError,ValueError,subprocess.SubprocessError) as error:
        print(json.dumps({'record_type':'local_research_index_refusal/v1','error':str(error) if isinstance(error,ResearchIndexError) else type(error).__name__}),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
