"""Baltor library client: versioned metadata search and exact selected downloads.

Standard library only. No automatic retry, installation, code execution or model call.
Filesystem writes require a new output folder and POSIX descriptor confinement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

VERSION = '0.3.0'
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

class Refusal(ValueError):
    """Only bounded codes and references; never a raw server message or credential."""
    def __init__(self, code, *, status=None, reference=None):
        super().__init__(code)
        self.code, self.status, self.reference = code, status, reference
    def details(self):
        return {'error': self.code, **({'http_status': self.status} if self.status else {}),
                **({'request_reference': self.reference} if self.reference else {})}

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
        require(path in ROUTES and type(limit) is int and 0 <= limit <= JSON_LIMIT, 'exchange_scope_invalid')
        require(authenticated or path == '/api/v1/capabilities', 'authentication_required')
        headers = {'Accept': 'application/octet-stream' if path.endswith('/download') else 'application/json'}
        if authenticated:
            require(bool(self._credential), 'credential_missing_or_invalid')
            headers['Authorization'] = 'Bearer ' + self._credential
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
                    code, reference = 'service_http_' + str(response.status), None
                    try:
                        error = parse_json(raw)
                        self.safe_json(error)
                        if type(error) is dict and error.get('record_type') == 'service_http_error/v1':
                            reason = error.get('error', {})
                            if type(reason) is dict and type(reason.get('code')) is str and re.fullmatch(r'[a-z][a-z0-9_]{0,99}', reason['code']):
                                code = 'service_refused:' + reason['code']
                            ref = error.get('request_reference')
                            if type(ref) is str and re.fullmatch(r'ref_[a-z0-9]{1,64}', ref):
                                reference = ref
                    except Refusal as error:
                        if error.code == 'credential_echo_refused':
                            raise
                    raise Refusal(code, status=response.status, reference=reference)
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
        return {'authority_effects': list(self.config['authority_effects'])}
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
        validate_policy(value, self.config)
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

def validate_policy(value, config):
    effects = value.get('declared_effects')
    require(value.get('library_tier') in {'verified', 'community'} and type(effects) is list
            and all(type(effect) is str for effect in effects) and len(effects) == len(set(effects))
            and set(effects) <= set(config['authority_effects']), 'selection_policy_mismatch')

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
        if config is not None:
            validate_policy(hit, config)
        require(ident not in seen and type(hit.get('body_allowed')) is bool, 'reference_invalid')
        seen.add(ident)

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
    summary = hit['package']
    rows, document = package_entries(summary) if summary is not None else ([], None)
    if summary is not None:
        require((summary['package_digest'] if summary['body_form'] == 'package' else rows[0]['digest']) == digest, 'selection_package_mismatch')
    manifest = client.manifest(selected_identity, digest)
    require(manifest['body_allowed'] is True, 'body_not_allowed')
    if summary is not None:
        expected_size = len(document) if summary['body_form'] == 'package' else rows[0]['size_bytes']
        require(manifest['size_bytes'] == expected_size, 'manifest_package_size_mismatch')
    ceiling = min(FILE_LIMIT, client.capabilities['delivery']['download_bytes'])
    require(manifest['size_bytes'] <= ceiling and all(row['size_bytes'] <= ceiling for row in rows), 'download_exceeds_host_limit')
    receipt = {'record_type': 'baltor_library_fetch_receipt/v1', 'client_version': VERSION, 'origin': client.config['origin'],
               'identity': selected_identity, 'selected_digest': digest, 'request_id': request_id, 'selection_sha256': sha(client.safe_json(selection)),
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

class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal('arguments_invalid')

def main(argv=None):
    try:
        parser = SafeParser(description='Search Baltor and fetch selected exact bytes; never install or execute downloads.')
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
        args = parser.parse_args(argv)
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
