"""Baltor library client: versioned metadata search, exact selected downloads and exact placement.

Standard library only. No code execution or model call. The only automatic retry repeats a request the service
refused without recording anything, after the wait the service names. Fetching writes a new staging folder; installing
copies a verified skill package into one client's native skill folder. Filesystem writes use POSIX descriptor
confinement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

VERSION = '0.4.1'
JSON_LIMIT = 16 * 1024 * 1024
FILE_LIMIT = 8 * 1024 * 1024
PACKAGE_LIMIT = 32 * 1024 * 1024
DIGEST = re.compile(r'[a-f0-9]{64}\Z')
MEDIA = re.compile(r'[a-z0-9][a-z0-9!#$&^_.+-]{0,62}/[a-z0-9][a-z0-9!#$&^_.+-]{0,126}\Z')
EFFECTS = {'reads_fs', 'writes_fs', 'reads_secret', 'network', 'spawns_process'}
PACKAGE_ROLES = {'instruction_file', 'skill_definition', 'skill_script', 'skill_reference', 'skill_asset',
                 'subagent_definition', 'command', 'hook', 'protocol_server_configuration', 'plugin_manifest',
                 'executable_tool', 'configuration', 'other'}
SOURCE_LAYERS = {'context_intelligence', 'code_intelligence', 'runtime_history_solution_intelligence',
                 'user_feedback_intelligence', 'harness_local'}
ROUTES = {'/api/v1/capabilities', '/api/v1/retrieval', '/api/v1/provisioning', '/api/v1/download'}
# The configured effects travel in this header: what the consuming step may do. The service shows every item with the
# effects a step would still have to declare, and refuses a download of an item whose effects the header leaves out.
STEP_EFFECTS_HEADER = 'Baltor-Step-Effects'
# Refusals that recorded nothing and name a short wait. A download counts once per item version and month, so sending
# the same request again after the wait can never count twice.
RETRYABLE = {'tenant_concurrency_limit_reached', 'usage_store_busy', 'store_busy', 'service_busy'}
RETRY_BUDGET_SECONDS, LONGEST_RETRY_WAIT_SECONDS = 15, 5
RECEIPT_VERSION = 'baltor_library_fetch_receipt/v2'
READABLE_RECEIPTS = ('baltor_library_fetch_receipt/v1', RECEIPT_VERSION)
INSTALL_RECORD = 'baltor_library_install/v1'
# Where each client reads skills, as release.json names them. A skill folder is <root>/<name>/SKILL.md.
NATIVE_SKILL_ROOTS = {'claude-code': {'project': '.claude/skills', 'user': '~/.claude/skills'},
                      'codex': {'project': '.agents/skills', 'user': '~/.agents/skills'},
                      'opencode': {'project': '.opencode/skills', 'user': '~/.config/opencode/skills'},
                      'pi': {'project': '.pi/skills', 'user': '~/.pi/agent/skills'}}
SKILL_FILE = 'SKILL.md'
SKILL_NAME = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
STAGING_PREFIX = '.baltor-staging-'

class Refusal(ValueError):
    """Only bounded codes and references; never a raw server message or credential."""
    def __init__(self, code, *, status=None, reference=None, effects=None, retry_after=None):
        super().__init__(code)
        self.code, self.status, self.reference = code, status, reference
        self.effects, self.retry_after = effects, retry_after
    def details(self):
        return {'error': self.code, **({'http_status': self.status} if self.status else {}),
                **({'request_reference': self.reference} if self.reference else {}),
                **({'effects_to_declare': list(self.effects)} if self.effects else {})}

def require(condition, code):
    if not condition:
        raise Refusal(code)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode()

def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def nonfinite(_value):
        raise Refusal('nonfinite_json')
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    except Refusal:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise Refusal('invalid_json') from None

def exact_digest(value):
    require(type(value) is str and DIGEST.fullmatch(value), 'invalid_digest')
    return value

def identity(value):
    require(type(value) is str and 1 <= len(value) <= 512 and not any(ord(c) < 32 or ord(c) == 127 for c in value), 'identity_invalid')
    return value

@contextmanager
def directory_fd(path):
    require(hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY') and os.open in os.supports_dir_fd,
            'confined_filesystem_unavailable')
    absolute = Path(path).absolute()
    require('..' not in absolute.parts, 'directory_path_invalid')
    fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        yield fd
    except OSError:
        raise Refusal('directory_not_plain') from None
    finally:
        os.close(fd)

def plain_file(path, limit):
    path = Path(path).absolute()
    try:
        with directory_fd(path.parent) as parent:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0), dir_fd=parent)
            with os.fdopen(fd, 'rb') as stream:
                require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'source_not_regular')
                raw = stream.read(limit + 1)
    except OSError:
        raise Refusal('source_unavailable') from None
    require(len(raw) <= limit, 'source_too_large')
    return raw

def validate_configuration(value):
    fields = {'record_type', 'origin', 'credential_environment', 'authority_effects'}
    require(type(value) is dict and set(value) == fields, 'configuration_shape')
    require(value['record_type'] == 'baltor_library_client_configuration/v2', 'configuration_version')
    origin = value['origin']
    require(type(origin) is str and len(origin) <= 2048 and origin.isascii() and '\\' not in origin
            and not any(c.isspace() or ord(c) < 32 for c in origin), 'https_origin_required')
    try:
        parts = urlsplit(origin)
        valid = parts.scheme == 'https' and parts.hostname and parts.port in (None, 443) and not (parts.username or parts.password or parts.query or parts.fragment or parts.path)
    except ValueError:
        valid = False
    require(valid, 'https_origin_required')
    require(type(value['credential_environment']) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', value['credential_environment']), 'credential_reference_invalid')
    for name, allowed in [('authority_effects', EFFECTS)]:
        values = value[name]
        require(type(values) is list and all(type(x) is str for x in values) and len(set(values)) == len(values)
                and set(values) <= allowed, 'selection_invalid')
    return json.loads(json.dumps(value))

def configuration(path):
    return validate_configuration(parse_json(plain_file(path, 32768)))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Refusal('redirect_refused')

class Client:
    def __init__(self, config, credential, opener=None):
        self.config = validate_configuration(config)
        require(type(credential) is str and (not credential or re.fullmatch(r'[\x21-\x7e]{1,4096}', credential)), 'credential_missing_or_invalid')
        self._credential = credential
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.capabilities, self.calls = None, 0
    def safe_json(self, value):
        encoded = json_bytes(value)
        pending = [value]
        while pending:
            part = pending.pop()
            if isinstance(part, str):
                require(not self._credential or self._credential not in part, 'credential_echo_refused')
            elif isinstance(part, dict):
                pending.extend(part.keys()); pending.extend(part.values())
            elif isinstance(part, (list, tuple)):
                pending.extend(part)
        return encoded
    def exchange(self, path, payload=None, *, authenticated=True, limit=JSON_LIMIT):
        """One request, sent again only after a refusal that recorded nothing, while the retry budget lasts."""
        started = time.monotonic()
        while True:
            try:
                return self.exchange_once(path, payload, authenticated=authenticated, limit=limit)
            except Refusal as refusal:
                wait = refusal.retry_after
                if wait is None or time.monotonic() - started + wait > RETRY_BUDGET_SECONDS:
                    raise
            time.sleep(wait)
    def exchange_once(self, path, payload=None, *, authenticated=True, limit=JSON_LIMIT):
        require(path in ROUTES and type(limit) is int and 0 <= limit <= JSON_LIMIT, 'exchange_scope_invalid')
        require(authenticated or path == '/api/v1/capabilities', 'authentication_required')
        headers = {'Accept': 'application/octet-stream' if path.endswith('/download') else 'application/json'}
        if authenticated:
            require(bool(self._credential), 'credential_missing_or_invalid')
            headers['Authorization'] = 'Bearer ' + self._credential
            if self.config['authority_effects']:
                headers[STEP_EFFECTS_HEADER] = ', '.join(self.config['authority_effects'])
        data = self.safe_json(payload) if payload is not None else None
        if data is not None:
            if self.capabilities:
                require(len(data) <= self.capabilities['limits']['request_bytes'], 'request_too_large')
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(self.config['origin'] + path, data=data, headers=headers)
        self.calls += 1
        deadline = time.monotonic() + 60
        try:
            try:
                response = self.opener.open(request, timeout=15)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                require(response.geturl() == request.full_url, 'redirect_refused')
                require(type(response.status) is int and 100 <= response.status <= 599, 'http_status_invalid')
                ceiling = limit if response.status == 200 else min(JSON_LIMIT, 65536)
                chunks, remaining = [], ceiling + 1
                while remaining:
                    require(time.monotonic() < deadline, 'response_deadline')
                    chunk = response.read1(min(65536, remaining))
                    require(time.monotonic() < deadline, 'response_deadline')
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                raw = b''.join(chunks)
                require(len(raw) <= ceiling, 'response_too_large')
                require(not self._credential or self._credential.encode() not in raw, 'credential_echo_refused')
                if response.status != 200:
                    code, reference, effects, retry_after = 'service_http_' + str(response.status), None, None, None
                    try:
                        error = parse_json(raw)
                        self.safe_json(error)
                        if type(error) is dict and error.get('record_type') == 'service_http_error/v1':
                            reason = error.get('error', {})
                            if type(reason) is dict and type(reason.get('code')) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,99}', reason['code']):
                                code = 'service_refused:' + reason['code']
                                details = reason.get('details')
                                wanted = details.get('effects_to_declare') if type(details) is dict else None
                                if type(wanted) is list and wanted and all(type(e) is str and e in EFFECTS for e in wanted):
                                    effects = wanted
                                waits = response.headers.get_all('Retry-After') or []
                                if (response.status in (429, 503) and reason['code'] in RETRYABLE and len(waits) == 1
                                        and waits[0].isdigit() and int(waits[0]) <= LONGEST_RETRY_WAIT_SECONDS):
                                    retry_after = max(1, int(waits[0]))
                            ref = error.get('request_reference')
                            if type(ref) is str and re.fullmatch(r'ref_[a-z0-9]{1,64}', ref):
                                reference = ref
                    except Refusal as error:
                        if error.code == 'credential_echo_refused':
                            raise
                    raise Refusal(code, status=response.status, reference=reference, effects=effects,
                                  retry_after=retry_after)
                return raw, response.headers
        except Refusal:
            raise
        except Exception:
            raise Refusal('transport_failed') from None
    def result(self, path, payload=None, *, authenticated=True):
        limit = min(JSON_LIMIT, self.capabilities['limits']['response_bytes']) if self.capabilities else JSON_LIMIT
        raw, headers = self.exchange(path, payload, authenticated=authenticated, limit=limit)
        media = headers.get_all('Content-Type') or []
        require(len(media) == 1 and media[0].split(';', 1)[0].strip().lower() == 'application/json', 'json_media_type_required')
        value = parse_json(raw)
        self.safe_json(value)
        operation = payload['operation'] if path.endswith('/provisioning') else path.rsplit('/', 1)[-1]
        require(type(value) is dict and value.get('record_type') == 'service_http_result/v1'
                and value.get('operation') == operation and type(value.get('result')) is dict, 'service_envelope_unsupported')
        return value['result']
    def handshake(self):
        c = self.result('/api/v1/capabilities', authenticated=False)
        require(c.get('record_type') == 'service_capabilities/v1' and c.get('api_version') == 'v1', 'capabilities_version')
        require(all(type(c.get(k)) is dict for k in ['retrieval', 'library', 'delivery', 'limits']), 'capabilities_shape')
        require(c['retrieval'].get('request_record_type') == 'service_retrieval_request/v2'
                and 'lexical' in c['retrieval'].get('modes', []) and c['retrieval'].get('returns_bodies') is False, 'retrieval_version')
        require('service_provisioning_request/v2' in c['library'].get('provisioning_request_record_types', []), 'provisioning_version')
        d = c['delivery']
        require(d.get('download_endpoint') == '/api/v1/download' and d.get('package_files') == 'download_by_path'
                and d.get('body_format') == 'utf8_text', 'delivery_unsupported')
        require(type(d.get('download_bytes')) is int and d['download_bytes'] > 0, 'download_limit_invalid')
        require(all(type(c['limits'].get(k)) is int and c['limits'][k] > 0 for k in ['request_bytes', 'response_bytes', 'search_results']), 'limits_invalid')
        require(type(c['library'].get('step_effects')) is list and all(type(e) is str for e in c['library']['step_effects'])
                and set(self.config['authority_effects']) <= set(c['library']['step_effects']), 'effects_unsupported')
        self.capabilities = c
        return c
    def selection(self):
        # Configured effects travel in the Baltor-Step-Effects header, so the service shows every item marked with
        # the effects still to declare. An explicit empty list means a step with no effects: it is sent as the
        # request's own narrowing, so only items that declare none are shown.
        return {} if self.config['authority_effects'] else {'authority_effects': []}
    def search(self, query, limit):
        require(self.capabilities is not None, 'handshake_required')
        require(type(query) is str and query.strip() and len(query.encode('utf-8')) <= 4096, 'query_invalid')
        require(type(limit) is int and 1 <= limit <= self.capabilities['limits']['search_results'], 'search_limit_invalid')
        value = self.result('/api/v1/retrieval', {'record_type': 'service_retrieval_request/v2', 'query': query,
                           'mode': 'lexical', 'top_n': limit, **self.selection()})
        validate_search(value, self.config)
        require(len(value['hits']) <= limit, 'search_limit_exceeded')
        return value
    def manifest(self, selected_identity, digest):
        require(self.capabilities is not None, 'handshake_required')
        identity(selected_identity); exact_digest(digest)
        value = self.result('/api/v1/provisioning', {'record_type': 'service_provisioning_request/v2', 'operation': 'manifest',
                            'identity': selected_identity, 'expected_digest': digest, **self.selection()})
        require(value.get('record_type') == 'provisioning_manifest/v3' and value.get('identity') == selected_identity
                and value.get('digest') == digest, 'manifest_binding_mismatch')
        require(type(value.get('size_bytes')) is int and 0 <= value['size_bytes'] <= FILE_LIMIT
                and type(value.get('body_allowed')) is bool, 'manifest_shape')
        validate_shape(value)
        return value
    def download(self, selected_identity, selected_digest, request_id, expected_digest, size, path=None):
        require(self.capabilities is not None, 'handshake_required')
        identity(selected_identity); exact_digest(selected_digest); exact_digest(expected_digest)
        require(type(size) is int and 0 <= size <= min(FILE_LIMIT, self.capabilities['delivery']['download_bytes']), 'download_exceeds_host_limit')
        payload = {'record_type': 'service_provisioning_request/v2', 'operation': 'read', 'identity': selected_identity,
                   'expected_digest': selected_digest, 'request_id': request_id, **self.selection()}
        if path is not None:
            payload['path'] = path
        raw, headers = self.exchange('/api/v1/download', payload, limit=size)
        require(headers.get_all('X-Loop-Engine-Record-Type') == ['service_download/v1'], 'download_version')
        require(headers.get_all('X-Content-SHA256') == [expected_digest] and sha(raw) == expected_digest and len(raw) == size, 'download_integrity')
        return raw

def validate_shape(value):
    """A hit or manifest names a known tier, a distinct list of declared effects and, when present, the effects its
    step would still have to declare."""
    effects, marks = value.get('declared_effects'), value.get('effects_to_declare', [])
    require(value.get('library_tier') in {'verified', 'community'} and type(effects) is list
            and all(type(effect) is str for effect in effects) and len(effects) == len(set(effects))
            and type(marks) is list and all(type(effect) is str and effect in EFFECTS for effect in marks),
            'selection_shape_invalid')

def validate_policy(value, config):
    """The selected item's declared effects are all effects the configuration lets the consuming step perform."""
    validate_shape(value)
    beyond = [effect for effect in value['declared_effects'] if effect != 'pure' and effect not in config['authority_effects']]
    if beyond:
        raise Refusal('step_effects_not_configured', effects=beyond)

def validate_search(value, config=None):
    require(type(value) is dict and value.get('record_type') == 'service_retrieval_result/v1'
            and value.get('bodies_loaded') is False and type(value.get('hits')) is list, 'retrieval_result_invalid')
    seen = set()
    for hit in value['hits']:
        require(type(hit) is dict and type(hit.get('reference')) is dict and 'package' in hit, 'reference_invalid')
        reference = hit['reference']
        require(set(reference) == {'record_type', 'identity', 'source_layer', 'source_ref', 'body_digest', 'descriptor_digest'}
                and reference.get('record_type') == 'provisioning_item_binding/v1', 'reference_binding_unsupported')
        require(reference.get('source_layer') in SOURCE_LAYERS and type(reference.get('source_ref')) is str
                and reference['source_ref'].strip() and len(reference['source_ref']) <= 4096, 'reference_source_invalid')
        ident = identity(reference['identity']); exact_digest(reference['body_digest']); exact_digest(reference['descriptor_digest'])
        # Every item is shown, marked with the effects still to declare; fetch checks the selected one's effects.
        validate_shape(hit)
        require(ident not in seen and type(hit.get('body_allowed')) is bool, 'reference_invalid')
        seen.add(ident)

def bounded_text(value, limit):
    """Metadata text on one line: every character that does not print becomes a space, at most `limit` characters."""
    if type(value) is not str:
        return ''
    return ' '.join(''.join(ch if ch.isprintable() else ' ' for ch in value).split())[:limit]

def selected_hit(search_record, selected_identity, selected_digest):
    validate_search(search_record)
    matches = [hit for hit in search_record['hits'] if hit['reference']['identity'] == selected_identity
               and hit['reference']['body_digest'] == selected_digest]
    require(len(matches) == 1, 'selection_binding_mismatch')
    return matches[0]

def package_entries(value):
    require(type(value) is dict and set(value) == {'body_form', 'package_digest', 'files'}, 'package_summary_shape')
    require(value['body_form'] in ('file', 'package'), 'package_body_form')
    exact_digest(value['package_digest'])
    rows = value['files']
    require(type(rows) is list and 1 <= len(rows) <= 64, 'package_file_count')
    paths, total = set(), 0
    for row in rows:
        require(type(row) is dict and set(row) == {'path', 'digest', 'size_bytes', 'media_type', 'role'}, 'package_entry_shape')
        path = row['path']
        require(type(path) is str and len(path) <= 200 and 1 <= len(path.split('/')) <= 8, 'package_path')
        require(all(re.fullmatch(r'[A-Za-z0-9._@+-]{1,100}', p) and p not in ('.', '..') and p.casefold() != '.git'
                    for p in path.split('/')), 'package_path')
        folded = path.casefold()
        require(folded not in paths and not any(folded.startswith(p + '/') or p.startswith(folded + '/') for p in paths), 'package_path_collision')
        paths.add(folded); exact_digest(row['digest'])
        require(type(row['size_bytes']) is int and 0 <= row['size_bytes'] <= FILE_LIMIT, 'package_size')
        require(type(row['role']) is str and row['role'] in PACKAGE_ROLES and type(row['media_type']) is str
                and MEDIA.fullmatch(row['media_type']), 'package_role')
        total += row['size_bytes']
    require(total <= PACKAGE_LIMIT and rows == sorted(rows, key=lambda row: row['path']), 'package_total_or_order')
    require(value['body_form'] != 'file' or len(rows) == 1, 'package_body_form')
    document = json.dumps({'record_type': 'catalogue_package/v1', 'files': rows}, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    require(sha(document) == value['package_digest'], 'package_summary_digest')
    return rows, document

class Output:
    def __init__(self, fd):
        self.fd = fd
    def write(self, relative, data):
        require(type(relative) is str and not relative.startswith('/') and all(
            re.fullmatch(r'[A-Za-z0-9._@+-]{1,100}', part) and part not in ('.', '..') and part.casefold() != '.git'
            for part in relative.split('/')), 'output_path_invalid')
        parts = relative.split('/')
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd); fd = nxt
            target = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            with os.fdopen(target, 'wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.fsync(fd)
        except OSError:
            raise Refusal('output_write_failed') from None
        finally:
            os.close(fd)

@contextmanager
def new_output(path):
    path = Path(path).absolute()
    with directory_fd(path.parent) as parent:
        try:
            os.mkdir(path.name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            raise Refusal('output_exists') from None
        fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        os.fsync(parent)
        try:
            yield Output(fd)
        finally:
            os.close(fd)

def fetch(client, selected_identity, digest, request_id, output, selection):
    require(type(request_id) is str and re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', request_id), 'request_id_invalid')
    identity(selected_identity); exact_digest(digest)
    client.safe_json(selection)
    validate_search(selection, client.config)
    hit = selected_hit(selection, selected_identity, digest)
    require(hit['body_allowed'] is True, 'selected_body_not_allowed')
    validate_policy(hit, client.config)
    summary = hit['package']
    rows, document = package_entries(summary) if summary is not None else ([], None)
    if summary is not None:
        require((summary['package_digest'] if summary['body_form'] == 'package' else rows[0]['digest']) == digest, 'selection_package_mismatch')
    manifest = client.manifest(selected_identity, digest)
    require(manifest['body_allowed'] is True, 'body_not_allowed')
    validate_policy(manifest, client.config)
    if summary is not None:
        expected_size = len(document) if summary['body_form'] == 'package' else rows[0]['size_bytes']
        require(manifest['size_bytes'] == expected_size, 'manifest_package_size_mismatch')
    ceiling = min(FILE_LIMIT, client.capabilities['delivery']['download_bytes'])
    require(manifest['size_bytes'] <= ceiling and all(row['size_bytes'] <= ceiling for row in rows), 'download_exceeds_host_limit')
    receipt = {'record_type': RECEIPT_VERSION, 'client_version': VERSION, 'origin': client.config['origin'],
               'identity': selected_identity, 'selected_digest': digest, 'request_id': request_id, 'selection_sha256': sha(client.safe_json(selection)),
               'kind': bounded_text(hit.get('kind'), 64), 'purpose': bounded_text(hit.get('purpose'), 1024),
               'declared_effects': list(hit['declared_effects']),
               'complete': False, 'files': [], 'installed': False, 'executed': False,
               'package_metadata_source': 'selected_search_result', 'usage_commitment': 'not_asserted'}
    with new_output(output) as destination:
        destination.write('request.json', client.safe_json(receipt))
        try:
            raw = client.download(selected_identity, digest, request_id, digest, manifest['size_bytes'])
            destination.write('body', raw)
            if summary is None:
                receipt['files'].append({'path': 'body', 'digest': digest, 'size_bytes': len(raw), 'role': 'unassigned'})
            else:
                if summary['body_form'] == 'package':
                    require(raw == document, 'package_document_binding')
                for row in rows:
                    data = raw if summary['body_form'] == 'file' else client.download(selected_identity, digest, request_id, row['digest'], row['size_bytes'], row['path'])
                    destination.write('payload/' + row['path'], data)
                    receipt['files'].append({key: row[key] for key in ('path', 'digest', 'size_bytes', 'role', 'media_type')})
            receipt['complete'] = True
            destination.write('receipt.json', client.safe_json(receipt))
            return receipt
        except Exception as error:
            receipt['failure'] = error.details() if isinstance(error, Refusal) else {'error': 'local_fetch_failed'}
            try:
                destination.write('failure.json', client.safe_json(receipt))
            except Exception:
                pass  # The initial request identity remains when the filesystem cannot save more.
            if isinstance(error, Refusal):
                raise
            raise Refusal('local_fetch_failed') from None

def ensure_directory(path):
    """Open each parent without following links before creating its descendants."""
    path = Path(path).absolute()
    require('..' not in path.parts, 'directory_path_invalid')
    require(os.mkdir in os.supports_dir_fd, 'confined_filesystem_unavailable')
    with directory_fd(path.anchor) as anchor:
        fd = os.dup(anchor)
        try:
            for part in path.parts[1:]:
                try:
                    os.mkdir(part, 0o755, dir_fd=fd)
                except FileExistsError:
                    pass
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
        except OSError:
            raise Refusal('directory_not_plain') from None
        finally:
            os.close(fd)
    return path

def exists(path):
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False

def skill_front_matter(data):
    """The fields a SKILL.md states in its YAML front matter, read line by line, or {} without front matter."""
    try:
        lines = data.decode('utf-8').splitlines()
    except UnicodeDecodeError:
        return {}
    if not lines or lines[0].strip() != '---':
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == '---':
            return fields
        match = re.match(r'([A-Za-z_][A-Za-z0-9_-]*):[ \t]*(.*)\Z', line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                value = value[1:-1]
            fields[match.group(1)] = value
    return {}

def native_name(value):
    """A skill folder name every client accepts, from an item identity: lower case, '.' and '_' become '-'."""
    name = re.sub(r'[._]+', '-', identity(value).lower()).strip('-')
    require(len(name) <= 64 and SKILL_NAME.match(name), 'identity_has_no_skill_name')
    return name

def skill_header(name, description):
    """The front matter the clients need, written as JSON strings, which are YAML scalars too."""
    return ('---\nname: ' + json.dumps(name) + '\ndescription: ' + json.dumps(description) + '\n---\n').encode()

def skill_roots(client_name, scope, project):
    """The client's skill folder for the scope, and the folder that keeps this client's install records beside it.

    A folder the table writes from the home folder (`~/...`) is the user's; any other is inside the project."""
    require(client_name in NATIVE_SKILL_ROOTS, 'client_unknown')
    require(scope in NATIVE_SKILL_ROOTS[client_name], 'scope_unknown')
    declared = NATIVE_SKILL_ROOTS[client_name][scope]
    root = Path(declared).expanduser() if declared.startswith('~') else Path(project).absolute() / declared
    return root, root.parent / 'baltor-library' / 'installed'

def staged_files(staged):
    """The verified bytes of every file a completed fetch staged, read again from its folder, with its receipt."""
    receipt_path = Path(staged).absolute() / 'receipt.json'
    raw = plain_file(receipt_path, JSON_LIMIT)
    receipt = parse_json(raw)
    require(type(receipt) is dict and receipt.get('record_type') in READABLE_RECEIPTS and receipt.get('complete') is True
            and type(receipt.get('files')) is list and receipt['files'], 'receipt_incomplete')
    identity(receipt.get('identity')); exact_digest(receipt.get('selected_digest'))
    require(all(type(row) is dict and row.get('path') != 'body' for row in receipt['files']), 'install_needs_package_metadata')
    files = {}
    for row in receipt['files']:
        path = row.get('path')
        require(type(path) is str and len(path) <= 200 and all(
            re.fullmatch(r'[A-Za-z0-9._@+-]{1,100}', part) and part not in ('.', '..') and part.casefold() != '.git'
            for part in path.split('/')) and path not in files, 'package_path')
        exact_digest(row.get('digest'))
        data = plain_file(receipt_path.parent / 'payload' / path, FILE_LIMIT)
        require(sha(data) == row['digest'] and len(data) == row.get('size_bytes'), 'staged_file_changed')
        files[path] = (data, row)
    return receipt, raw, files

def installed_problems(target, record):
    """What no longer matches in an installed skill folder, file by file."""
    problems = []
    for row in record['files']:
        try:
            data = plain_file(target / row['path'], FILE_LIMIT + 4096)
        except Refusal:
            problems.append(row['path'] + ' is missing')
            continue
        if sha(data) != row['file_sha256']:
            problems.append(row['path'] + ' changed since it was installed')
        elif sha(data[row['header_bytes']:]) != row['published_digest']:
            problems.append(row['path'] + ' does not hold the published bytes')
    return problems

def read_install_record(records, name):
    record = parse_json(plain_file(records / (name + '.json'), JSON_LIMIT))
    require(type(record) is dict and record.get('record_type') == INSTALL_RECORD and record.get('native_name') == name
            and type(record.get('files')) is list and all(
                type(row) is dict and type(row.get('path')) is str and type(row.get('header_bytes')) is int
                and row['header_bytes'] >= 0 for row in record['files']), 'install_record_invalid')
    return record

def write_record(records, name, record):
    """Write one install record in place of an older one, through a new file and one rename."""
    ensure_directory(records)
    temporary = '.' + name + '.' + os.urandom(6).hex() + '.tmp'
    with directory_fd(records) as folder:
        try:
            handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
            with os.fdopen(handle, 'wb') as stream:
                stream.write(json_bytes(record)); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, name + '.json', src_dir_fd=folder, dst_dir_fd=folder)
            os.fsync(folder)
        except OSError:
            raise Refusal('install_record_write_failed') from None

def install(staged, client_name, scope='project', project='.'):
    """Place one fetched, verified skill package in a client's native skill folder, byte for byte.

    The files are read again from the staging folder and checked against the fetch receipt, written into a new
    folder beside the target, checked again, and moved into place with one rename. A folder that already holds
    something else is never replaced. A SKILL.md whose front matter lacks a usable name and description gets a
    generated header followed by the published bytes, and the install record says so. Only skill packages have a
    native place here; every other kind stays in its staging folder."""
    receipt, raw, files = staged_files(staged)
    require(SKILL_FILE in files and files[SKILL_FILE][1].get('role') == 'skill_definition', 'install_kind_unsupported')
    fields = skill_front_matter(files[SKILL_FILE][0])
    served, described = fields.get('name', ''), fields.get('description', '')
    header = b''
    if SKILL_NAME.match(served) and len(served) <= 64 and described:
        name = served
    else:
        name = native_name(receipt['identity'])
        text = described if described not in ('', '>', '|', '>-', '|-') else receipt.get('purpose', '')
        require(bounded_text(text, 1024), 'skill_description_missing')
        header = skill_header(name, bounded_text(text, 1024))
    root, records = skill_roots(client_name, scope, project)
    target = root / name
    if exists(target):
        try:
            record = read_install_record(records, name)
        except Refusal:
            raise Refusal('placement_conflict') from None
        require(record.get('identity') == receipt['identity'] and record.get('published_digest') == receipt['selected_digest']
                and not installed_problems(target, record), 'placement_conflict')
        return {**record, 'already_installed': True}
    ensure_directory(root)
    staging = root / (STAGING_PREFIX + os.urandom(8).hex())
    written = []
    try:
        with new_output(staging) as out:
            for path, (data, row) in sorted(files.items()):
                content = header + data if path == SKILL_FILE else data
                out.write(path, content)
                written.append({'path': path, 'published_digest': row['digest'], 'size_bytes': len(data),
                                'header_bytes': len(header) if path == SKILL_FILE else 0, 'file_sha256': sha(content)})
        require(not installed_problems(staging, {'files': written}), 'placement_verification_failed')
        require(not exists(target), 'placement_conflict')
        os.rename(staging, target)
    except OSError:
        raise Refusal('placement_failed') from None
    finally:
        if exists(staging):
            shutil.rmtree(staging, ignore_errors=True)
    record = {'record_type': INSTALL_RECORD, 'client_version': VERSION, 'client': client_name, 'scope': scope,
              'identity': receipt['identity'], 'native_name': name, 'target': str(target),
              'published_digest': receipt['selected_digest'], 'receipt_sha256': sha(raw),
              'rendering': 'generated_front_matter_then_served_bytes' if header else 'served_bytes_unchanged',
              'files': written, 'installed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'loaded': 'not_asserted'}
    write_record(records, name, record)
    return record

def verify(client_name, name, scope='project', project='.'):
    """Check an installed skill folder against its install record: each file's bytes and its published digest."""
    require(type(name) is str and SKILL_NAME.match(name) and len(name) <= 64, 'skill_name_invalid')
    root, records = skill_roots(client_name, scope, project)
    record = read_install_record(records, name)
    problems = installed_problems(root / name, record)
    return {'record_type': 'baltor_library_install_check/v1', 'client_version': VERSION, 'native_name': name,
            'identity': record.get('identity'), 'published_digest': record.get('published_digest'),
            'target': str(root / name), 'verified': not problems, 'problems': problems}

class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal('arguments_invalid')

def main(argv=None):
    try:
        parser = SafeParser(description='Search Baltor, fetch selected exact bytes and place a verified skill; never execute downloads.')
        parser.add_argument('--config', type=Path, default=Path.home()/'.config/baltor/client.json')
        parser.add_argument('--version', action='version', version=VERSION)
        commands = parser.add_subparsers(dest='command', required=True)
        commands.add_parser('capabilities')
        search = commands.add_parser('search'); search.add_argument('query'); search.add_argument('--limit', type=int, default=5)
        for name in ('manifest', 'fetch'):
            p = commands.add_parser(name); p.add_argument('--identity', required=True); p.add_argument('--digest', required=True)
            if name == 'fetch':
                p.add_argument('--selection', type=Path, required=True); p.add_argument('--request-id', required=True)
                p.add_argument('--output', type=Path, required=True); p.add_argument('--authorize-download', action='store_true')
        placing = commands.add_parser('install')
        placing.add_argument('--staged', type=Path, required=True)
        placing.add_argument('--client', required=True, choices=sorted(NATIVE_SKILL_ROOTS))
        placing.add_argument('--scope', default='project', choices=('project', 'user'))
        placing.add_argument('--project', type=Path, default=Path('.'))
        placing.add_argument('--authorize-install', action='store_true')
        checking = commands.add_parser('verify')
        checking.add_argument('--client', required=True, choices=sorted(NATIVE_SKILL_ROOTS))
        checking.add_argument('--name', required=True)
        checking.add_argument('--scope', default='project', choices=('project', 'user'))
        checking.add_argument('--project', type=Path, default=Path('.'))
        args = parser.parse_args(argv)
        if args.command in ('install', 'verify'):
            # Placement reads the staged files and writes the client's folder; it needs no network and no token.
            if args.command == 'install':
                require(args.authorize_install, 'install_authority_required')
                value = install(args.staged, args.client, args.scope, args.project)
            else:
                value = verify(args.client, args.name, args.scope, args.project)
            sys.stdout.buffer.write(json_bytes(value))
            return 0 if value.get('verified', True) else 1
        config = configuration(args.config); key = os.environ.get(config['credential_environment'], '')
        require(not key or all(key not in arg for arg in (argv if argv is not None else sys.argv[1:])), 'credential_in_arguments')
        if args.command != 'capabilities':
            require(bool(key), 'credential_missing_or_invalid')
        if args.command == 'fetch':
            require(args.authorize_download, 'download_authority_required')
            selection = parse_json(plain_file(args.selection, JSON_LIMIT))
        c = Client(config, key); caps = c.handshake()
        if args.command == 'capabilities':
            value = caps
        elif args.command == 'search':
            value = c.search(args.query, args.limit)
        elif args.command == 'manifest':
            value = c.manifest(args.identity, args.digest)
        else:
            value = fetch(c, args.identity, args.digest, args.request_id, args.output, selection)
        sys.stdout.buffer.write(c.safe_json(value))
        return 0
    except Exception as error:
        value = error.details() if isinstance(error, Refusal) else {'error': 'client_failed'}
        print(json.dumps(value, sort_keys=True), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
