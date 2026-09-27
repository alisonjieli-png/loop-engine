"""Small recurring source-discovery job; never installs, calls models or publishes.

Network effects use the existing bounded, credential-free ingestion transport.
Snapshots are research artifacts. The queue is a rebuildable review projection,
not an approved component catalogue.
"""
import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET

VENDOR = os.environ.get('BALTOR_RADAR_VENDOR_ROOT')
if VENDOR:
    # Explicit durable deployment binding: exact copied transport modules and
    # pattern data, with upstream paths/digests in the installation manifest.
    sys.path.insert(0, VENDOR)
    from radar_ingestion.https_transport import HttpsGetTransport, split_address
    from radar_ingestion.request_log import RequestBudget, RequestLog
    _PATTERNS = tuple(json.loads((Path(VENDOR) / 'secret-patterns.json').read_bytes()))
    def default_secret_patterns():
        return _PATTERNS
else:
    RUNTIME = Path(os.environ.get('BALTOR_RADAR_RUNTIME_ROOT', Path(__file__).resolve().parents[2])).resolve()
    sys.path.insert(0, str(RUNTIME / 'src'))
    from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport, split_address
    from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog
    from loop_engine.core.model_call_records import default_secret_patterns

CONFIG_TYPE = 'source_discovery_configuration/v1'
RUN_TYPE = 'source_discovery_run/v1'
ATOM = '{http://www.w3.org/2005/Atom}'


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def clean(value, maximum=500):
    value = html.unescape(re.sub(r'<[^>]*>', ' ', str(value or '')[:8000]))
    value = ' '.join(value.split())
    for pattern in default_secret_patterns():
        value = re.sub(pattern, '[redacted]', value)
    return value[:maximum]


def public_url(value):
    if type(value) is not str or len(value) > 2000:
        raise ValueError('invalid_public_url')
    parsed = split_address(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('invalid_public_url')
    return value


def timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        try:
            parsed = parsedate_to_datetime(value)
        except (ValueError, TypeError, IndexError):
            return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def repository(row, source_id):
    identity, name = row.get('id'), row.get('full_name')
    if type(identity) is not int or identity <= 0 or type(name) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name):
        raise ValueError('invalid_repository_identity')
    url = public_url(row.get('html_url'))
    if url.rstrip('/').lower() != ('https://github.com/' + name).lower():
        raise ValueError('repository_url_mismatch')
    metrics = {}
    for key in ['stargazers_count', 'forks_count']:
        value = row.get(key)
        metrics[key] = value if type(value) is int and value >= 0 else None
    return {'key': 'github-repository:' + str(identity), 'kind': 'repository', 'title': name, 'url': url,
            'summary': clean(row.get('description')), 'created_at': timestamp(row.get('created_at')),
            'updated_at': timestamp(row.get('pushed_at')), 'metrics': metrics,
            'topics': [clean(x, 80) for x in row.get('topics', []) if isinstance(x, str)][:30],
            'archived': row.get('archived') is True,
            'declared_licence': (row.get('license') or {}).get('spdx_id'),
            'source_id': source_id, 'source_commit': None, 'verification': 'discovery_only'}


def parse_feed(raw, source_id, maximum=20):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('xml_entity_declaration_refused')
    root = ET.fromstring(raw)
    if root.tag not in (ATOM + 'feed', 'rss'):
        raise ValueError('unsupported_feed_format')
    entries = root.findall(ATOM + 'entry') if root.tag == ATOM + 'feed' else root.findall('./channel/item')
    result = []
    for entry in entries[:maximum]:
        if root.tag == ATOM + 'feed':
            title = entry.findtext(ATOM + 'title')
            links = entry.findall(ATOM + 'link')
            url = next((link.get('href') for link in links if link.get('rel', 'alternate') == 'alternate'), None)
            date = entry.findtext(ATOM + 'published') or entry.findtext(ATOM + 'updated')
            description = entry.findtext(ATOM + 'summary') or entry.findtext(ATOM + 'content')
        else:
            title, url, date, description = (entry.findtext(key) for key in ['title', 'link', 'pubDate', 'description'])
        if not title or not url:
            continue
        try:
            public_url(url)
        except ValueError:
            continue
        result.append({'key': 'web-observation:' + sha(url.encode()), 'kind': 'news_or_release',
                       'title': clean(title, 200), 'url': url, 'summary': clean(description),
                       'created_at': timestamp(date), 'updated_at': timestamp(date), 'metrics': {}, 'topics': [],
                       'archived': False, 'declared_licence': None, 'source_id': source_id,
                       'source_commit': None, 'verification': 'discovery_only'})
    return result


def priority(item, keywords):
    terms = (item['title'] + ' ' + item['summary'] + ' ' + ' '.join(item['topics'])).lower()
    matched = sorted({word for word in keywords if word.lower() in terms})
    score = min(60, len(matched) * 10)
    reasons = ['topic:' + word for word in matched]
    if item['source_id'].startswith('watch-'):
        score += 25
        reasons.append('explicit_watchlist')
    stars = item['metrics'].get('stargazers_count')
    if stars is not None and stars >= 100:
        score += 5
        reasons.append('public_attention_signal_not_quality')
    if item['archived']:
        score -= 20
        reasons.append('archived_repository')
    return max(0, score), reasons


def merge(previous, observations, observed_at, keywords):
    records = dict(previous)
    new, changed, substantive_changes = 0, 0, 0
    for item in observations:
        identity = item['key']
        old = records.get(identity)
        fingerprint = sha(canonical({key: value for key, value in item.items() if key != 'source_id'}))
        substantive = sha(canonical({key: value for key, value in item.items() if key not in ('source_id', 'metrics')}))
        new += old is None
        changed += old is not None and old['fingerprint'] != fingerprint
        score, reasons = priority(item, keywords)
        sources = sorted(set((old or {}).get('seen_via', [])) | {item['source_id']})
        if any(source.startswith('watch-') for source in sources) and 'explicit_watchlist' not in reasons:
            score += 25
            reasons.append('explicit_watchlist')
        substantive_changed = old is not None and old['substantive_fingerprint'] != substantive
        substantive_changes += substantive_changed
        state = 'changed_needs_review' if substantive_changed else (old or {}).get('review_state', 'unreviewed')
        records[identity] = {**item, 'fingerprint': fingerprint, 'review_priority': score, 'priority_reasons': reasons,
                             'first_seen': old['first_seen'] if old else observed_at, 'last_seen': observed_at,
                             'substantive_fingerprint': substantive, 'seen_via': sources, 'review_state': state}
    return records, {'new': new, 'changed': changed, 'substantive_changes': substantive_changes}


def write_json(path, value):
    raw = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    temporary = path.with_name(path.name + '.partial')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def validate_config(value):
    fields = {'record_type', 'sources', 'keywords', 'maximum_requests', 'timeout_seconds', 'queue_size'}
    if type(value) is not dict or set(value) != fields or value['record_type'] != CONFIG_TYPE:
        raise ValueError('unsupported_configuration')
    if any(type(value[key]) is not int for key in ('maximum_requests','timeout_seconds','queue_size')):
        raise ValueError('invalid_budget')
    if not 1 <= value['maximum_requests'] <= 20 or not 1 <= value['timeout_seconds'] <= 20 or not 1 <= value['queue_size'] <= 1000:
        raise ValueError('invalid_budget')
    if not isinstance(value['sources'], list) or len(value['sources']) > value['maximum_requests']:
        raise ValueError('source_budget_mismatch')
    ids = set()
    for source in value['sources']:
        if set(source) != {'id', 'kind', 'host', 'path', 'query'} or source['kind'] not in ('github_search', 'github_repository', 'feed'):
            raise ValueError('invalid_source')
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,60}', source['id']) or source['id'] in ids:
            raise ValueError('duplicate_source')
        ids.add(source['id'])
        if not re.fullmatch(r'[a-z0-9.-]+', source['host']) or not source['path'].startswith('/') or '..' in source['path'].split('/'):
            raise ValueError('invalid_source_address')
        if not isinstance(source['query'], dict) or any(not isinstance(k, str) or not isinstance(v, (str, int)) for k,v in source['query'].items()):
            raise ValueError('invalid_query')
        if source['kind'] == 'github_search':
            if source['host'] != 'api.github.com' or source['path'] != '/search/repositories' or set(source['query']) != {'q','sort','order','per_page'}:
                raise ValueError('invalid_repository_search')
            if type(source['query']['per_page']) is not int or not 1 <= source['query']['per_page'] <= 20:
                raise ValueError('invalid_page_bound')
        elif source['query']:
            raise ValueError('unexpected_query_parameters')
        if any(re.search(pattern, json.dumps(source)) for pattern in default_secret_patterns()):
            raise ValueError('secret_shaped_configuration')
    if not isinstance(value['keywords'], list) or not all(isinstance(k, str) and 1 <= len(k) <= 80 for k in value['keywords']):
        raise ValueError('invalid_keywords')
    return value


def run(configuration, output):
    configuration = validate_config(configuration)
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.resolve() != output:
        raise ValueError('output_root_not_plain')
    lock = os.open(output / 'collector.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock)
        return {'status': 'already_running'}
    try:
        observed_at = now()
        state_path = output / 'projection.json'
        previous = {}
        if state_path.exists():
            if state_path.is_symlink():
                raise ValueError('projection_not_plain')
            saved = json.loads(state_path.read_bytes())
            if saved.get('record_type') != 'source_discovery_projection/v1' or type(saved.get('records')) is not dict:
                raise ValueError('unsupported_projection')
            previous = saved['records']
            for key, row in previous.items():
                if not isinstance(row, dict) or row.get('key') != key or 'substantive_fingerprint' not in row:
                    raise ValueError('invalid_projection')
        run_id = observed_at.replace(':', '').replace('-', '') + '-' + str(os.getpid())
        folder = output / 'runs' / run_id
        folder.mkdir(parents=True, exist_ok=False)
        log = RequestLog(folder / 'requests.jsonl')
        budget = RequestBudget(configuration['maximum_requests'], maximum_pause_seconds=0, reserve=0)
        transport = HttpsGetTransport({s['host'] for s in configuration['sources']}, budget, log,
                                     timeout_seconds=configuration['timeout_seconds'], maximum_bytes=2 * 1024 * 1024)
        observations, outcomes = [], []
        since = (datetime.now(timezone.utc) - timedelta(days=14)).strftime('%Y-%m-%d')
        for source in configuration['sources']:
            query = {key: value.replace('{since_14d}', since) if isinstance(value, str) else value for key, value in source['query'].items()}
            result = {'source_id': source['id'], 'outcome': 'failed', 'observations': 0}
            try:
                response = transport.get(source['host'], source['path'], query)
                result['http_status'] = response.status
                if response.status != 200:
                    raise ValueError('source_http_failure')
                if source['kind'] == 'feed':
                    rows = parse_feed(response.body, source['id'])
                else:
                    data = json.loads(response.body)
                    if source['kind'] == 'github_search':
                        rows = [repository(item, source['id']) for item in data['items'][:20]]
                        result.update(total_count=data.get('total_count'), incomplete_results=data.get('incomplete_results'), coverage='first_page_only')
                    else:
                        rows = [repository(data, source['id'])]
                observations.extend(rows)
                result.update(outcome='ok', observations=len(rows))
            except Exception as error:
                result['error_type'] = type(error).__name__
            outcomes.append(result)
        records, changes = merge(previous, observations, observed_at, configuration['keywords'])
        ordered = sorted(records.values(), key=lambda row: (-row['review_priority'], -datetime.fromisoformat(row['last_seen'].replace('Z','+00:00')).timestamp(), row['key']))
        queue = ordered[:configuration['queue_size']]
        report = {'record_type': RUN_TYPE, 'run_id': run_id, 'observed_at': observed_at, 'finished_at': now(),
                  'configuration_sha256': sha(canonical(configuration)), 'collector_sha256': sha(Path(__file__).read_bytes()),
                  'sources': outcomes, 'requests': budget.used, 'observations': observations, 'changes': changes,
                  'cumulative_source_identities': len(records), 'model_calls': 0, 'installs': 0, 'published_components': 0,
                  'scope': 'discovery observations and triage; no source code executed, no component approval',
                  'status': 'complete' if all(r['outcome']=='ok' for r in outcomes) else 'partial'}
        write_json(folder / 'report.json', report)
        write_json(output / 'projection.json', {'record_type': 'source_discovery_projection/v1', 'records': records})
        write_json(output / 'review-queue.json', {'record_type': 'source_discovery_review_queue/v1', 'source_run': run_id,
                   'meaning': 'priority to inspect; not quality, permission or approval', 'items': queue})
        write_json(output / 'latest.json', {'record_type': RUN_TYPE, 'run_id': run_id, 'report': str(folder / 'report.json'),
                                          'status': report['status'], 'finished_at': report['finished_at']})
        return {key: report[key] for key in ['run_id','status','requests','changes','cumulative_source_identities','model_calls']}
    finally:
        os.close(lock)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--configuration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--authorize-network-reads', action='store_true')
    parser.add_argument('--authorize-local-writes', action='store_true')
    args = parser.parse_args()
    configuration = validate_config(json.loads(args.configuration.read_bytes()))
    if not args.authorize_network_reads or not args.authorize_local_writes:
        print(json.dumps({'mode':'preview','sources':len(configuration['sources']),'maximum_requests':configuration['maximum_requests'],'model_calls':0}))
        return
    print(json.dumps(run(configuration, args.output)))


if __name__ == '__main__':
    main()
