"""Dated research adapter over existing bounded ingestion; no schema/code execution.

Ranks catalogue metadata, retrieves at most 1 MiB per allowed public document,
and records parse observations. It never resolves references, installs a package,
calls a described API, or qualifies a document for redistribution or admission.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

SOURCE = Path('/home/username/.le-codex-build/integration')
sys.path.insert(0, str(SOURCE / 'src'))
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog
from loop_engine.core.library_ingestion.quarantine import Quarantine

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/username/.le-codex-research-cache/four-catalogues-20260923')
HOSTS = ('raw.githubusercontent.com', 'www.schemastore.org', 'api.apis.guru')
LIMIT = 1024 * 1024
SOURCE_NAMES = ('schemastore_catalog', 'apis_guru_list')
RULES = {
    'direct_agent_or_protocol': (44, ('claude code', 'gemini cli', 'opencode', 'mcp', 'ai agent', 'ai coding', 'ai harness', 'aiconfig', 'agent run metrics', 'context passport', 'arazzo', 'asyncapi', 'openapi', 'json schema', 'pactspec')),
    'developer_build_test_and_config': (32, ('github', 'gitlab', 'package', 'typescript', 'tsconfig', 'compiler', 'linter', 'lint', 'formatter', 'test', 'build', 'dependency', 'dependencies', 'ci/cd', 'workflow', 'deployment', 'container', 'docker', 'kubernetes', 'cargo', 'pyproject', 'python', 'javascript', 'eslint', 'prettier', 'renovate', 'release', 'code generation', 'codegen', 'api gateway')),
    'data_and_observability': (30, ('schema', 'database', 'sql', 'table', 'dataset', 'data pipeline', 'data quality', 'telemetry', 'observability', 'metrics', 'logging', 'monitoring', 'parquet', 'avro', 'csv', 'etl')),
    'security_and_policy': (29, ('security', 'permission', 'policy', 'audit', 'vulnerab', 'authentication', 'authorization', 'certificate', 'secret', 'supply chain')),
    'product_and_business': (16, ('documentation', 'website', 'content', 'project', 'application', 'config', 'manifest', 'configuration', 'customer', 'commerce', 'payment')),
}
API_CATEGORIES = {'machine_learning': 44, 'developer_tools': 35, 'security': 34,
    'analytics': 32, 'text': 31, 'open_data': 30, 'search': 30, 'monitoring': 30,
    'storage': 29, 'collaboration': 28, 'messaging': 27, 'cloud': 26, 'tools': 26,
    'email': 25, 'project_management': 25, 'time_management': 25, 'ecommerce': 23,
    'customer_relation': 23, 'financial': 22, 'payment': 22, 'location': 21,
    'enterprise': 21, 'hosting': 21, 'backend': 21, 'education': 20, 'forms': 20,
    'support': 20, 'transport': 18, 'media': 17, 'marketing': 17, 'iot': 16,
    'social': 16, 'telecom': 15, 'entertainment': 12}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def duplicate_safe(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def parse(data):
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=duplicate_safe,
        parse_float=Decimal, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))


def safe_address(url):
    try:
        if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
            return None
        value = urlsplit(url)
        if value.scheme != 'https' or value.hostname not in HOSTS or value.netloc != value.hostname:
            return None
        if value.username or value.password or value.query or value.fragment or not value.path.startswith('/'):
            return None
        if any(x in value.path for x in ('\\', '\r', '\n', '\0')) or '..' in value.path.split('/'):
            return None
        return value.hostname, value.path
    except (TypeError, ValueError):
        return None


def navigation_address(url):
    """Metadata links may name unqualified fetch hosts, but must still be valid URLs."""
    try:
        if not isinstance(url, str) or any(ord(char) <= 32 or ord(char) == 127 for char in url):
            return False
        value = urlsplit(url)
        return value.scheme in ('https', 'http') and bool(value.hostname) and not value.username and not value.password
    except ValueError:
        return False


def repository_parts(url):
    value = urlsplit(url)
    if value.hostname == 'raw.githubusercontent.com':
        parts = value.path.strip('/').split('/')
        if len(parts) >= 4:
            # Branch/tag names are observations, never fabricated immutable revisions.
            ref = parts[2]
            return '/'.join(parts[:2]), '/'.join(parts[3:]), ref if re.fullmatch('[0-9a-f]{40}', ref) else None
    return None, None, None


def common(kind, key, name, url, snapshot):
    repository, source_path, revision = repository_parts(url)
    return {'record_type': 'harness_source_research_item/v1', 'category': 'contract',
        'research_id': 'contract-' + digest((kind + '\0' + key).encode())[:24],
        'logical_contract_key': kind + ':' + key, 'contract_kind': kind,
        'name': name, 'repository': repository, 'source_url': url,
        'source_path': source_path, 'source_snapshot_digest': snapshot,
        'upstream_revision': revision, 'upstream_blob_sha': None,
        'license_reported': None, 'license_verified': False,
        'qualification_status': 'unreviewed', 'compatibility_status': 'unverified',
        'evidence_level': 'catalogue_metadata', 'body_snapshot_digest': None,
        'inspiration_methods': [], 'notes': [], 'score_components': {},
        'fetch_observation': {'status': 'not_attempted'}}


def catalogue_rows():
    index = json.loads((CACHE / 'initial-index.json').read_text())
    sources = {r['name']: r for r in index['sources'] if r['name'] in SOURCE_NAMES}
    docs = {}
    for name, row in sources.items():
        raw = Path(row['quarantine_file']).read_bytes()
        if digest(raw) != row['sha256'] or len(raw) != row['bytes']:
            raise ValueError('catalogue_snapshot_mismatch:' + name)
        docs[name] = parse(raw)
    rows, collapsed = [], []
    groups = defaultdict(list)
    for item in docs['schemastore_catalog']['schemas']:
        # A version map is one family; explicit meta-schema drafts also share one family.
        name = item['name']
        family = re.sub(r'(?i)(?:[ -]v?\d+(?:\.\d+)+(?:[ .-]manifest)?| draft .*|\s+v\d+)$', '', name).casefold()
        if name.lower().startswith('json schema draft'):
            family = 'json-schema-metaschema'
        key = 'family:' + family
        groups[key].append(item)
    seen_urls = set()
    for key, members in sorted(groups.items()):
        item = sorted(members, key=lambda r: (not bool(safe_address(r['url'])), r['url']))[0]
        if item['url'] in seen_urls:
            collapsed.append({'kind': 'schema_url_alias', 'names': [x['name'] for x in members], 'url': item['url']})
            continue
        seen_urls.add(item['url'])
        row = common('document_schema', key, item['name'], item['url'], sources['schemastore_catalog']['sha256'])
        text = (item['name'] + ' ' + item['description']).lower()
        matches = [(score, group, sorted(t for t in terms if t in text)) for group, (score, terms) in RULES.items() if any(t in text for t in terms)]
        score, group, terms = max(matches, default=(8, 'general_document_format', []))
        fragment = any(t in item['name'].lower() for t in ('partial-', 'snippet definition', 'structure value'))
        row.update(relevance_class=group, provider=repository_parts(item['url'])[0] or urlsplit(item['url']).hostname,
            native_file_patterns=item.get('fileMatch', []), catalog_member_names=[x['name'] for x in members],
            version_links_not_counted=sum(len(x.get('versions', {})) for x in members),
            relevance_evidence={'matched_metadata_terms': terms, 'description_digest': digest(item['description'].encode())})
        row['score_components'] = {'task_relevance': score, 'filename_association': 3 if item.get('fileMatch') else 0,
            'qualified_acquisition_host': 2 if safe_address(item['url']) else 0, 'fragment_penalty': -30 if fragment else 0}
        row['inspiration_methods'] = ['validate a task-produced document offline', 'provide bounded valid and invalid examples', 'explain version-specific fields from pinned sources']
        row['notes'] = ['SchemaStore membership is discovery evidence; filename associations grant no permissions.',
            'SchemaStore repository reports Apache-2.0; external linked documents and per-file notices need separate rights review.',
            'Alias and version links are not additional logical contracts.']
        rows.append(row)
        if len(members) > 1:
            collapsed.append({'kind': 'schema_family', 'key': key, 'names': row['catalog_member_names']})
    groups = defaultdict(list)
    for key, item in docs['apis_guru_list'].items():
        preferred = item['preferred']
        version = item['versions'].get(preferred)
        if not version or not isinstance(version.get('info'), dict):
            collapsed.append({'kind': 'missing_preferred_metadata', 'key': key})
            continue
        info = version['info']
        provider = info.get('x-providerName', key.split(':', 1)[0])
        title = re.sub(r'\s+', ' ', info.get('title', key)).strip()
        # Conservative consolidation of provider fragments carrying the same API title.
        logical = provider.casefold() + ':' + title.casefold()
        groups[logical].append((key, item, version))
    for key, members in sorted(groups.items()):
        member, item, version = sorted(members, key=lambda x: (x[2].get('updated', ''), x[0]), reverse=True)[0]
        info = version['info']; url = version.get('swaggerUrl', '')
        row = common('service_api', key, info.get('title', member), url, sources['apis_guru_list']['sha256'])
        cats = info.get('x-apisguru-categories', [])
        cats = cats if isinstance(cats, list) and all(isinstance(x, str) for x in cats) else []
        known = sorted(set(c for c in cats if c in API_CATEGORIES))
        category_score = max((API_CATEGORIES[c] for c in known), default=8)
        updated = version.get('updated')
        row.update(provider=info.get('x-providerName', member.split(':', 1)[0]),
            catalog_api_ids=[x[0] for x in members], selected_catalog_api_id=member,
            selected_preferred_version=item['preferred'], version_count_not_counted=sum(len(x[1]['versions']) for x in members),
            declared_openapi_version=version.get('openapiVer'), catalogue_updated_at=updated,
            relevance_class='service_api_' + (max(known, key=lambda c: API_CATEGORIES[c]) if known else 'uncategorized'),
            relevance_evidence={'categories': known, 'unrecognized_categories': [c for c in cats if c not in API_CATEGORIES]},
            license_reported=info.get('license'), upstream_origins=info.get('x-origin', []))
        row['score_components'] = {'task_relevance': category_score, 'origin_metadata': 3 if info.get('x-origin') else 0,
            'reported_license_metadata': 2 if info.get('license') else 0,
            'qualified_acquisition_host': 2 if safe_address(url) else 0,
            'stale_metadata_penalty': -6 if not updated or updated[:4] < '2025' else 0}
        row['inspiration_methods'] = ['derive offline request and response fixtures', 'identify read-only task operations', 'design a typed adapter with separate credential and effect authority']
        row['notes'] = ['Directory preferred version is used; current upstream operation has not been verified.',
            'info.license is reported API metadata, not verified redistribution permission for all definition bytes.',
            'A valid API description does not supply authentication, execution authority, idempotency or endpoint availability.']
        rows.append(row)
        if len(members) > 1:
            collapsed.append({'kind': 'provider_title_family', 'key': key, 'api_ids': row['catalog_api_ids']})
    for row in rows:
        row['priority_score'] = sum(row['score_components'].values())
    invalid = [row for row in rows if not navigation_address(row['source_url'])]
    for row in invalid:
        collapsed.append({'kind': 'invalid_navigation_url_excluded', 'research_id': row['research_id'],
            'source_url_sha256': digest(row['source_url'].encode()),
            'reason': 'Raw catalogue provenance remains in the input snapshot; no URL normalization was assumed.'})
    rows = [row for row in rows if navigation_address(row['source_url'])]
    rows.sort(key=lambda r: (-r['priority_score'], r['logical_contract_key']))
    return rows, collapsed, sources


def select(rows, counts=None):
    counts = counts or {'document_schema': 600, 'service_api': 400}
    totals = Counter(); providers = Counter(); result = []
    for row in rows:
        kind = row['contract_kind']; provider = row['provider']
        if totals[kind] >= counts[kind]:
            continue
        # Do not turn an API operation/subservice catalogue into one-provider dominance.
        cap = 12 if provider in ('azure.com', 'amazonaws.com', 'googleapis.com') else 20
        if kind == 'service_api' and providers[provider] >= cap:
            continue
        result.append(row); totals[kind] += 1
        if kind == 'service_api':
            providers[provider] += 1
    if totals != Counter(counts):
        raise ValueError('insufficient_distinct_metadata_candidates:' + str(totals))
    for rank, row in enumerate(result, 1):
        row['rank'] = rank
    return result


def inspect_body(raw, kind):
    value = parse(raw)
    if kind == 'service_api' and (not isinstance(value, dict) or not any(k in value for k in ('swagger', 'openapi'))):
        raise ValueError('api_root_marker_missing')
    if kind == 'document_schema' and not isinstance(value, (dict, bool)):
        raise ValueError('schema_root_type')
    refs = []; count = 0; stack = [(value, 0)]
    while stack:
        entry, depth = stack.pop(); count += 1
        if depth > 128 or count > 100000:
            raise ValueError('document_structure_budget')
        if isinstance(entry, dict):
            for key, val in entry.items():
                if key in ('$ref', '$dynamicRef') and isinstance(val, str):
                    refs.append(val)
                stack.append((val, depth + 1))
        elif isinstance(entry, list):
            stack.extend((val, depth + 1) for val in entry)
    root = value if isinstance(value, dict) else {}
    return {'json_parsed': True, 'root_kind': 'boolean' if isinstance(value, bool) else 'object',
        'declared_dialect': root.get('$schema'), 'declared_id': root.get('$id'),
        'openapi_marker': root.get('openapi', root.get('swagger')),
        'reference_count': len(refs), 'external_reference_count': sum(not r.startswith('#') for r in refs),
        'remote_references_resolved': False, 'structural_values_visited': count,
        'metaschema_validated': False, 'semantic_behavior_verified': False}


def fetch_lane(lane, rows, run):
    log = RequestLog(run / f'requests-{lane}.jsonl')
    budget = RequestBudget(maximum_requests=150, maximum_pause_seconds=10)
    transport = HttpsGetTransport(HOSTS, budget, log, timeout_seconds=12, maximum_bytes=LIMIT)
    answers = []
    for row in rows:
        address = safe_address(row['source_url'])
        if address is None:
            answers.append((row['research_id'], {'status': 'host_or_url_not_qualified'}, None)); continue
        try:
            answer = transport.get(*address)
            observation = {'status': 'fetched' if answer.status == 200 else 'fetch_failed', 'http_status': answer.status}
            if log.records:
                observation['request_digest'] = log.records[-1]['request_digest']
                observation['transport_error_class'] = log.records[-1]['error_class'] or None
            if answer.status == 200:
                try:
                    observation.update(inspect_body(answer.body, row['contract_kind']))
                except (ValueError, UnicodeError, RecursionError, ArithmeticError) as error:
                    observation.update(status='parse_or_shape_refused', error_class=type(error).__name__, error=str(error)[:100])
            # status=None includes over-limit responses whose body was discarded;
            # the empty return buffer is not an observed source document.
            answers.append((row['research_id'], observation, answer.body if answer.status is not None else None))
        except Exception as error:
            answers.append((row['research_id'], {'status': 'request_refused', 'error_class': type(error).__name__}, None))
    return answers, log.summary(), budget.used


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--run-name', default='contracts-20260923-1')
    parser.add_argument('--output-dir', type=Path, default=HERE)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9-]+', args.run_name):
        raise ValueError('safe_run_name_required')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if any((args.output_dir / name).exists() for name in ('contracts-ranked.jsonl', 'contracts-counts.json')):
        raise ValueError('preserve prior outputs; select a new output directory before requests')
    run = CACHE / args.run_name
    run.mkdir(exist_ok=False)
    rows, collapsed, sources = catalogue_rows(); selected = select(rows)
    q = Quarantine(run / 'quarantine'); by_id = {r['research_id']: r for r in selected}
    logs = []; used = 0
    if args.fetch:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(fetch_lane, lane, selected[lane::8], run) for lane in range(8)]
            for future in as_completed(futures):
                answers, summary, count = future.result(); used += count; logs.append(summary)
                for identity, observation, raw in answers:
                    row = by_id[identity]; row['fetch_observation'] = observation
                    if raw is not None:
                        entry = q.put(raw); row['body_snapshot_digest'] = entry.digest
                        row['body_bytes'] = entry.size_bytes
                    if observation.get('json_parsed'):
                        row['evidence_level'] = 'catalogue_and_exact_document_parse'
                print(json.dumps({'lanes_done': len(logs), 'requests': used, 'rows_observed': sum(r['fetch_observation']['status'] != 'not_attempted' for r in selected)}), flush=True)
                (run / 'partial-index.json').write_text(json.dumps(selected, indent=2) + '\n')
    assert used <= 1200
    body_groups = defaultdict(list)
    for row in selected:
        if row['fetch_observation'].get('json_parsed'):
            body_groups[row['body_snapshot_digest']].append(row['research_id'])
    duplicate_bodies = {h: ids for h, ids in body_groups.items() if len(ids) > 1}
    # Exact body aliases are one candidate. Replacements remain explicit metadata-only.
    duplicate_ids = {identity for ids in duplicate_bodies.values() for identity in ids[1:]}
    for row in selected:
        if row['research_id'] in duplicate_ids:
            collapsed.append({'kind': 'fetched_exact_body_alias', 'research_id': row['research_id'], 'digest': row['body_snapshot_digest']})
    excluded = {r['research_id'] for r in selected}
    kept = [r for r in selected if r['research_id'] not in duplicate_ids]
    missing = Counter(r['contract_kind'] for r in selected if r['research_id'] in duplicate_ids)
    for row in rows:
        if row['research_id'] not in excluded and missing[row['contract_kind']]:
            kept.append(row); missing[row['contract_kind']] -= 1
            row['notes'].append('Metadata-only replacement for an exact-body alias; body not fetched in this run.')
    assert len(kept) == 1000 and len({r['logical_contract_key'] for r in kept}) == 1000
    kept.sort(key=lambda r: (-r['priority_score'], r['logical_contract_key']))
    for rank, row in enumerate(kept, 1): row['rank'] = rank
    output = args.output_dir / 'contracts-ranked.jsonl'
    with output.open('x') as file:
        for row in kept: file.write(json.dumps(row, sort_keys=True) + '\n')
    report = {'record_type': 'contract_source_research_counts/v1', 'run': str(run),
        'source_revision': json.loads((CACHE / 'initial-index.json').read_text())['source_revision'],
        'script_sha256': digest(Path(__file__).read_bytes()),
        'sources': sources, 'raw_catalogue_entries': 4003, 'logical_metadata_families': len(rows),
        'ranked_candidates': len(kept), 'kinds': dict(Counter(r['contract_kind'] for r in kept)),
        'relevance': dict(Counter(r['relevance_class'] for r in kept)),
        'fetch_observations': dict(Counter(r['fetch_observation']['status'] for r in kept)),
        'http_statuses': dict(Counter(str(r['fetch_observation'].get('http_status')) for r in kept)),
        'acquisition_lanes': logs, 'admitted_attempts': used,
        'recorded_requests': sum(log['requests'] for log in logs), 'request_ceiling': 1200,
        'maximum_document_bytes': LIMIT, 'remote_references_resolved': 0,
        'exact_body_duplicate_groups': duplicate_bodies, 'collapsed': collapsed,
        'license_verified': 0, 'approved_packages': 0, 'loaded_packages': 0,
        'ranked_output_sha256': digest(output.read_bytes())}
    (args.output_dir / 'contracts-counts.json').write_text(json.dumps(report, indent=2) + '\n')
    (run / 'final-index.json').write_text(json.dumps(kept, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('ranked_candidates', 'kinds', 'fetch_observations', 'recorded_requests', 'license_verified', 'approved_packages')}, indent=2))


if __name__ == '__main__':
    main()
