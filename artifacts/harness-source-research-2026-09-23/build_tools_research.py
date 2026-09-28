"""Build a reproducible research list from pinned local snapshots; never run a server."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

HERE = Path(__file__).resolve().parent
CACHE = Path('/home/username/.le-codex-research-cache/four-catalogues-20260923')
OFFICIAL = 'io.modelcontextprotocol.registry/official'
FAMILIES = {
    'structured_data': ('json', 'csv', 'sql', 'sqlite', 'postgres', 'database', 'schema', 'dataframe'),
    'developer_work': ('git', 'github', 'repository', 'code', 'test', 'debug', 'package', 'build'),
    'research_retrieval': ('search', 'research', 'documentation', 'knowledge', 'retrieve', 'papers', 'citation'),
    'documents': ('pdf', 'document', 'markdown', 'text', 'spreadsheet', 'excel', 'slides'),
    'browser': ('browser', 'playwright', 'accessibility', 'webpage', 'crawl'),
    'operations': ('monitor', 'metrics', 'logs', 'observability', 'incident', 'cloud'),
    'workflow': ('task', 'calendar', 'issue', 'project', 'workflow', 'schedule'),
    'media': ('image', 'video', 'audio', 'metadata', 'media'),
}
METHODS = {
    'structured_data': 'Investigate a bounded schema/table inspection or supplied-data transformation contract.',
    'developer_work': 'Investigate exact-revision repository inspection with explicit file and command scope.',
    'research_retrieval': 'Investigate source retrieval with provenance, query limits and citation receipts.',
    'documents': 'Investigate format-specific inspection or transformation with parser and output bounds.',
    'browser': 'Investigate a session-bound browser step with explicit targets, state and allowed effects.',
    'operations': 'Investigate bounded telemetry retrieval with tenant scope and redacted output.',
    'workflow': 'Investigate explicit task-state reads or a separately authorized mutation contract.',
    'media': 'Investigate bounded media metadata or transformation with declared file and codec limits.',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def repo_url(server):
    value = server.get('repository', {}).get('url')
    if not isinstance(value, str):
        return None
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.query or p.fragment:
        return None
    return value.rstrip('/').removesuffix('.git')


def clean_surface(value):
    if isinstance(value, dict):
        return {k: clean_surface(v) for k, v in value.items() if k not in ('description', 'title')}
    if isinstance(value, list):
        return [clean_surface(v) for v in value]
    return value


def select_population(observations):
    groups = defaultdict(list)
    excluded = []
    for row in observations:
        groups[row['server']['name']].append(row)
    eligible = []
    for name, values in sorted(groups.items()):
        fingerprints = {digest({'server': x['server'], 'status': x.get('_meta', {}).get(OFFICIAL, {})}) for x in values}
        if len(fingerprints) != 1:
            excluded.append({'name': name, 'reason': 'conflicting_name_observations', 'observations': len(values)})
            continue
        row = values[0]
        official = row.get('_meta', {}).get(OFFICIAL, {})
        if official.get('status') != 'active' or official.get('isLatest') is not True:
            excluded.append({'name': name, 'reason': 'inactive_or_not_latest', 'status': official.get('status')})
            continue
        eligible.append(row)
    surfaces = {}
    selected = []
    for row in eligible:
        server = row['server']
        parts = {'packages': clean_surface(server.get('packages', [])),
                 'remotes': clean_surface(server.get('remotes', []))}
        # A shared monorepo is insufficient to merge distinct installations.
        # Unknown repositories never establish a shared project identity.
        surface = digest({'repository': repo_url(server), **parts}) if repo_url(server) and any(parts.values()) else None
        if surface and surface in surfaces:
            excluded.append({'name': server['name'], 'reason': 'duplicate_installation_surface',
                             'retained_name': surfaces[surface]})
            continue
        if surface:
            surfaces[surface] = server['name']
        selected.append(row)
    return selected, excluded


def score(server, check):
    description = server.get('description', '')
    words = set(re.findall(r'[a-z][a-z0-9]+', (server['name'] + ' ' + description).lower()))
    families = [name for name, terms in FAMILIES.items() if words.intersection(terms)]
    packages = server.get('packages', [])
    remotes = server.get('remotes', [])
    versioned = any(p.get('version') and not any(c in str(p['version']) for c in ('*', '^', '~', '>', '<')) for p in packages)
    transport = any(p.get('transport', {}).get('type') in ('stdio', 'streamable-http', 'sse') for p in packages)
    transport |= any(p.get('type') in ('streamable-http', 'sse') for p in remotes)
    variable_records = [v for p in packages for v in p.get('environmentVariables', [])]
    variable_records += [v for p in remotes for v in p.get('headers', [])]
    env_clarity = bool(variable_records) and all(v.get('name') and ('description' in v or 'value' in v) for v in variable_records)
    components = {
        'descriptor_completeness': min(10, len(description.split())) + 4 * bool(server.get('title')) + 3 * bool(server.get('version')) + 3 * bool(server.get('websiteUrl')),
        'declared_task_relevance': min(15, 5 * len(families)) + 5 * bool(words.intersection(('inspect', 'validate', 'search', 'query', 'analyze', 'convert', 'read', 'retrieve', 'compare', 'manage'))),
        'dependency_clarity': 7 * bool(packages) + 5 * versioned + 3 * env_clarity + 5 * bool(check.get('identity_matches')),
        'declared_runtime_surface': 8 * transport + 4 * bool(packages or remotes) + 3 * any(p.get('registryType') in ('npm', 'pypi', 'oci', 'mcpb', 'nuget', 'cargo') for p in packages),
        'primary_surface_evidence': 8 * bool(repo_url(server)) + 4 * bool(server.get('websiteUrl')) + 3 * bool(packages) + 3 * bool(remotes) + 7 * bool(check.get('identity_matches')),
    }
    # The word 'test' can describe a useful testing tool; only an explicit
    # registration label is penalized. This is editorial scope, not a safety decision.
    if re.match(r'\s*\[(?:test|demo|staging)\]', description, re.I):
        components['explicit_nonproduction_label_penalty'] = -min(20, sum(components.values()))
    return components, families


def make_item(row, rank, checks):
    server = row['server']
    name = server['name']
    check = checks.get(name, {})
    components, families = score(server, check)
    source = row['_source']
    return {
        'record_type': 'harness_source_research_item/v1', 'category': 'tool',
        'research_id': 'tool-' + hashlib.sha256(('mcp_server_package\0' + name).encode()).hexdigest()[:24],
        'name': name, 'repository': repo_url(server), 'source_url': source['url'],
        'source_path': source['path'], 'source_snapshot_digest': source['digest'],
        'upstream_revision': None, 'upstream_blob_sha': None,
        'license_reported': check.get('license_reported') or 'unknown', 'license_verified': False,
        'rank': rank, 'priority_score': sum(components.values()), 'score_components': components,
        'evidence_level': 'official_registry_and_matching_package_metadata' if check.get('identity_matches') else 'official_registry_metadata',
        'qualification_status': 'unreviewed', 'compatibility_status': 'unverified',
        'inspiration_methods': [METHODS[x] for x in families] or ['Investigate the declared task and establish a bounded operation contract before packaging.'],
        'notes': ['Editorial metadata priority; not a benchmark or correctness ranking.',
                  'Server installation is the counted unit. Tool schemas were not discovered or invoked.',
                  'Reported version is mutable metadata, not an immutable source or executable pin.',
                  'Effects, dependency closure, licence rights and client compatibility require independent review.'],
        'tool_unit': 'tool_provider/mcp_server_package', 'tools_list_observed': False,
        'reported_version': server.get('version'), 'registry_status': row['_meta'][OFFICIAL]['status'],
        'declared_families': families, 'package_metadata_check': check or None,
    }


def load_observations():
    observations, pages, seen = [], [], set()
    for index_name in ('initial-index.json', 'continuation-index.json'):
        index = json.loads((CACHE / index_name).read_text())
        for page in index['sources']:
            if not page['name'].startswith('mcp_registry_latest_'):
                continue
            if page['name'] in seen:
                raise ValueError('duplicate_page_name')
            seen.add(page['name'])
            raw = Path(page['quarantine_file']).read_bytes()
            if page['status'] != 200 or hashlib.sha256(raw).hexdigest() != page['sha256']:
                raise ValueError('invalid_source_snapshot')
            body = json.loads(raw)
            pages.append({'name': page['name'], 'digest': page['sha256'], 'rows': len(body['servers'])})
            for offset, value in enumerate(body['servers']):
                observations.append({**value, '_source': {
                    'digest': page['sha256'], 'path': f'servers/{offset}/server',
                    'url': 'https://' + page['host'] + page['path'] + '?' + urlencode(page['query'])}})
    completion = json.loads((CACHE / 'registry-pagination-continuation.json').read_text())
    if completion.get('complete') is not True:
        raise ValueError('registry_population_incomplete')
    return observations, pages


def rank_population(selected, checks):
    return sorted(selected, key=lambda r: (-sum(score(r['server'], checks.get(r['server']['name'], {}))[0].values()), r['server']['name']))


def build():
    observations, pages = load_observations()
    selected, excluded = select_population(observations)
    check_path = CACHE / 'tools-package-metadata-summary.json'
    checks = json.loads(check_path.read_text())['checks'] if check_path.exists() else {}
    ranked = rank_population(selected, checks)
    # Preserve a breadth-oriented sample; a prolific publisher must not fill the research list.
    counts = Counter()
    chosen = []
    deferred = []
    for row in ranked:
        publisher = row['server']['name'].split('/', 1)[0].lower()
        if counts[publisher] >= 20:
            deferred.append(row['server']['name'])
            continue
        chosen.append(row)
        counts[publisher] += 1
        if len(chosen) == 1000:
            break
    if len(chosen) != 1000:
        raise ValueError('insufficient_distinct_population')
    items = [make_item(row, rank, checks) for rank, row in enumerate(chosen, 1)]
    output = HERE / 'tools-ranked.jsonl'
    output.write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True) + '\n' for x in items))
    report = {
        'record_type': 'tool_source_research_population/v1', 'source_date': '2026-09-23',
        'unit': 'tool_provider/mcp_server_package', 'source_pages': len(pages), 'source_rows': len(observations),
        'unique_registry_names': len({x['server']['name'] for x in observations}),
        'status_counts': dict(Counter(x['_meta'][OFFICIAL].get('status') for x in observations)),
        'eligible_distinct_installations': len(selected), 'excluded': excluded,
        'exclusion_counts': dict(Counter(x['reason'] for x in excluded)),
        'selected': len(items), 'publisher_cap': 20, 'publisher_cap_deferred': deferred,
        'selected_publishers': len(counts), 'selected_metadata_matches': sum(bool(x['package_metadata_check'] and x['package_metadata_check'].get('identity_matches')) for x in items),
        'selected_license_unknown': sum(x['license_reported'] == 'unknown' for x in items),
        'source_snapshots': pages, 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'score_range': [min(x['priority_score'] for x in items), max(x['priority_score'] for x in items)],
        'tools_list_discoveries': 0, 'servers_started': 0, 'approved_packages': 0,
    }
    (HERE / 'tools-population.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('excluded', 'source_snapshots', 'publisher_cap_deferred')}, indent=2))
    print('Top20:', json.dumps([(x['name'], x['priority_score']) for x in items[:20]]))


def metadata_checks():
    sys.path.insert(0, '/home/username/.le-codex-build/integration/src')
    from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
    from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog
    from loop_engine.core.library_ingestion.quarantine import Quarantine
    destination = CACHE / 'tools-package-metadata-summary.json'
    if destination.exists():
        raise ValueError('preserve_existing_acquisition')
    observations, _ = load_observations()
    selected, _ = select_population(observations)
    log = RequestLog(CACHE / 'tools-package-requests.jsonl')
    transport = HttpsGetTransport(('registry.npmjs.org', 'pypi.org'), RequestBudget(150, maximum_pause_seconds=20), log,
                                 timeout_seconds=10, maximum_bytes=4 * 1024 * 1024)
    quarantine = Quarantine(CACHE / 'quarantine')
    checks = {}
    publishers = Counter()
    for row in rank_population(selected, {}):
        server = row['server']
        publisher = server['name'].split('/', 1)[0].lower()
        if publishers[publisher] >= 4:
            continue
        package = next((p for p in server.get('packages', []) if p.get('registryType') in ('npm', 'pypi') and p.get('version') and not any(c in p['version'] for c in '*^~<>')), None)
        if package is None:
            continue
        registry, identifier, version = package['registryType'], package['identifier'], package['version']
        host = 'registry.npmjs.org' if registry == 'npm' else 'pypi.org'
        path = '/' + quote(identifier, safe='') + '/' + quote(version, safe='') if registry == 'npm' else '/pypi/' + quote(identifier, safe='') + '/' + quote(version, safe='') + '/json'
        response = transport.get(host, path)
        entry = quarantine.put(response.body)
        result = {'status': response.status, 'sha256': entry.digest, 'source_url': 'https://' + host + path,
                  'registry': registry, 'identifier': identifier, 'version': version, 'identity_matches': False,
                  'license_reported': 'unknown', 'license_verified': False}
        if response.status == 200:
            try:
                value = json.loads(response.body)
                info = value if registry == 'npm' else value.get('info', {})
                normalized = lambda x: re.sub(r'[-_.]+', '-', str(x)).lower() if registry == 'pypi' else x
                result['identity_matches'] = normalized(info.get('name')) == normalized(identifier) and info.get('version') == version
                licence = info.get('license_expression') or info.get('license')
                if isinstance(licence, dict):
                    licence = licence.get('type')
                if result['identity_matches'] and isinstance(licence, str) and 0 < len(licence.strip()) <= 160:
                    result['license_reported'] = licence.strip()
            except (ValueError, TypeError):
                result['parse_error'] = True
        checks[server['name']] = result
        publishers[publisher] += 1
        destination.write_text(json.dumps({'request_ceiling': 150, 'selected_check_ceiling': 120,
                                          'requests': log.summary(), 'checks': checks}, indent=2) + '\n')
        if len(checks) % 20 == 0:
            print(json.dumps({'checks': len(checks), 'requests': log.summary()}), flush=True)
        if len(checks) >= 120:
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-package-metadata', action='store_true')
    args = parser.parse_args()
    metadata_checks() if args.check_package_metadata else build()
