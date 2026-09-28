"""One explicit, same-origin catalogue URL encoding correction; preserve predecessors."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('contract_research', HERE / 'collect_contract_candidates.py')
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
OLD = 'https://api.apis.guru/v2/specs/europeana.eu/version unknown/swagger.json'
NEW = 'https://api.apis.guru/v2/specs/europeana.eu/version%20unknown/swagger.json'
IDENTITY = 'contract-63260b9344771c11b37329e7'
RUN = owner.CACHE / 'contracts-url-repair-20260923-2'


def main():
    ranked = HERE / 'contracts-ranked.jsonl'
    raw = ranked.read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    row = next(value for value in rows if value['research_id'] == IDENTITY)
    if row['source_url'] != OLD or RUN.exists():
        raise ValueError('preserve_previous_state_and_do_not_repeat_repair')
    old, new = urlsplit(OLD), urlsplit(NEW)
    assert old.scheme == new.scheme == 'https' and old.netloc == new.netloc == 'api.apis.guru'
    assert not any((old.query, new.query, old.fragment, new.fragment, new.username, new.password))
    assert old.path.split('/') == unquote(new.path).split('/')
    assert owner.safe_address(OLD) is None and owner.safe_address(NEW) == (new.hostname, new.path)
    for name in ('contracts-ranked.jsonl', 'contracts-counts.json', 'contracts-integrity-checks.json'):
        suffix = Path(name).suffix
        backup = HERE / (Path(name).stem + '-before-url-repair-2' + suffix)
        if backup.exists(): raise ValueError('preserve_predecessor')
        shutil.copyfile(HERE / name, backup)
    RUN.mkdir()
    log = owner.RequestLog(RUN / 'requests.jsonl')
    budget = owner.RequestBudget(maximum_requests=1, maximum_pause_seconds=0)
    transport = owner.HttpsGetTransport(('api.apis.guru',), budget, log,
        timeout_seconds=12, maximum_bytes=owner.LIMIT)
    answer = transport.get(new.hostname, new.path)
    observation = {'status': 'fetched' if answer.status == 200 else 'fetch_failed',
        'http_status': answer.status, 'request_digest': log.records[-1]['request_digest'],
        'transport_error_class': log.records[-1]['error_class'] or None}
    body_digest = None
    if answer.status is not None:
        entry = owner.Quarantine(RUN / 'quarantine').put(answer.body)
        body_digest = entry.digest
    if answer.status == 200:
        try:
            observation.update(owner.inspect_body(answer.body, 'service_api'))
        except (ValueError, UnicodeError, RecursionError, ArithmeticError) as error:
            observation.update(status='parse_or_shape_refused', error_class=type(error).__name__)
    row['source_url_original'] = OLD
    row['source_url'] = NEW
    row['source_url_normalization'] = {'operation': 'percent_encode_literal_space_in_path',
        'same_origin': True, 'decoded_path_segments_unchanged': True,
        'original_catalogue_snapshot_digest': row['source_snapshot_digest'],
        'request_digest': log.records[-1]['request_digest']}
    row['prior_fetch_observation'] = row['fetch_observation']
    row['fetch_observation'] = observation
    row['body_snapshot_digest'] = body_digest
    if body_digest:
        row['body_bytes'] = len(answer.body)
        row['body_quarantine_run'] = str(RUN)
    if observation.get('json_parsed'):
        row['evidence_level'] = 'catalogue_and_exact_document_parse'
    row['notes'].append('Original catalogue URL had a literal space; this same-origin percent-encoded path was explicitly checked in the dated URL repair. The original URL remains in provenance.')
    updated = ''.join(json.dumps(value, sort_keys=True) + '\n' for value in rows).encode()
    assert len(rows) == 1000 and len({r['research_id'] for r in rows}) == 1000
    for value in rows:
        url = value['source_url']; parsed = urlsplit(url)
        assert parsed.scheme in ('http','https') and parsed.hostname and not parsed.username and not parsed.password
        assert all(ord(char) > 32 and ord(char) != 127 for char in url)
    ranked.write_bytes(updated)
    report = {'record_type': 'contract_source_url_repair/v1', 'research_id': IDENTITY,
        'raw_catalogue_url': OLD, 'normalized_source_url': NEW,
        'previous_ranked_sha256': hashlib.sha256(raw).hexdigest(),
        'ranked_sha256': hashlib.sha256(updated).hexdigest(),
        'normalization': row['source_url_normalization'], 'fetch_observation': observation,
        'body_sha256': body_digest, 'run': str(RUN), 'requests': log.summary(),
        'logical_candidate_count': 1000, 'rows_changed': 1,
        'licence_object_preserved': row['license_reported'] == {'name':'API terms of use','url':'https://www.europeana.eu/en/rights/api-terms-of-use'},
        'all_rows_remain_unreviewed': all(r['qualification_status']=='unreviewed' and not r['license_verified'] for r in rows),
        'navigation_urls_valid': True, 'approval': 'not_performed'}
    (HERE / 'contracts-url-repair-2.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
