"""One-shot feedback client over existing authenticated HTTP contracts, using only the standard library.

Customer fields arrive on stdin. The credential is read only from a named
environment variable. No token argument, redirect, body log or automatic retry.
The review operation calls the staff-only counts endpoint, never the raw view.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

VERSION = "baltor_feedback_cli_result/v1"
REQUEST_VERSION = "service_provisioning_request/v2"
RESULT_VERSION = "service_http_result/v1"
SUMMARY_PATH = "/api/v1/admin/feedback/summary"
INPUT_LIMIT, RESPONSE_LIMIT = 16_384, 65_536
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_CODES = {"unauthorized", "scope_required", "insufficient_scope", "invalid_request", "unsupported_version",
              "account_administration_forbidden", "staff_role_required", "rating_requires_download",
              "rating_value_invalid", "feedback_note_too_long", "material_request_description_invalid",
              "material_request_identity_conflict", "store_busy", "commit_unknown", "deadline_exceeded",
              "response_limit_exceeded", "tenant_concurrency_limit_reached", "service_busy"}


class Refusal(ValueError):
    pass


class SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        # argparse's ordinary message can echo an accidental --token argument.
        raise Refusal("invalid_arguments")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Refusal("redirect_refused")


def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Refusal("invalid_json")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _value: (_ for _ in ()).throw(Refusal("invalid_json")))
    except (ValueError, UnicodeError, RecursionError):
        raise Refusal("invalid_json") from None


def origin(value, allow_loopback):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise Refusal("invalid_origin") from None
    if (not isinstance(value, str) or not value.isascii() or len(value) > 2048
            or any(ord(char) < 33 for char in value) or any(char in value for char in "\\?#")
            or parsed.username is not None or parsed.password is not None or not parsed.hostname or parsed.path
            or '%' in parsed.netloc or (parsed.scheme != 'https' and not (
                allow_loopback and parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1', '::1')))
            or (parsed.scheme == 'https' and port not in (None, 443))):
        raise Refusal("invalid_origin")
    return value


def fields_for(operation, raw):
    if len(raw) > INPUT_LIMIT:
        raise Refusal("input_too_large")
    value = parse_json(raw)
    required = {'identity', 'expected_digest', 'value'} if operation == 'rate' else {'request_id', 'description'}
    allowed = required | {'note'} if operation == 'rate' else required
    if not isinstance(value, dict) or not required <= set(value) or set(value) - allowed:
        raise Refusal("invalid_fields")
    named = value.get('identity') if operation == 'rate' else value.get('request_id')
    if type(named) is not str or IDENTITY.fullmatch(named) is None:
        raise Refusal("invalid_fields")
    if operation == 'rate':
        if type(value['expected_digest']) is not str or not SHA256.fullmatch(value['expected_digest']) or value['value'] not in ('useful', 'not_useful'):
            raise Refusal("invalid_fields")
        text, limit = value.get('note', ''), 500
    else:
        text, limit = value['description'], 2000
    if type(text) is not str or len(text) > limit or any(ord(char) < 32 and char not in '\n\t' for char in text):
        raise Refusal("invalid_fields")
    if operation != 'rate' and not text.strip():
        raise Refusal("invalid_fields")
    return value


def checked_result(operation, value):
    """Only exact known result fields can reach stdout; raw staff rows cannot."""
    if not isinstance(value, dict) or value.get('record_type') != RESULT_VERSION or type(value.get('result')) is not dict:
        raise Refusal("invalid_response")
    result = value['result']
    if operation == 'review':
        if set(result) != {'record_type', 'ratings', 'material_requests', 'search_gaps'} or result['record_type'] != 'service_feedback_summary/v1':
            raise Refusal("invalid_response")
        shapes = {'ratings': {'useful', 'not_useful', 'items_rated'}, 'material_requests': {'total', 'open'},
                  'search_gaps': {'groups', 'searches'}}
        for key, fields in shapes.items():
            if (type(result[key]) is not dict or set(result[key]) != fields
                    or any(type(number) is not int or number < 0 for number in result[key].values())):
                raise Refusal("invalid_response")
    elif operation == 'rate':
        if (set(result) != {'record_type', 'committed', 'item_identity', 'body_digest', 'value', 'replaced', 'revision'}
                or result['record_type'] != 'catalogue_item_rating_result/v1' or result['committed'] is not True
                or type(result['item_identity']) is not str or not IDENTITY.fullmatch(result['item_identity'])
                or type(result['body_digest']) is not str or not SHA256.fullmatch(result['body_digest'])
                or result['value'] not in ('useful', 'not_useful') or type(result['replaced']) is not bool
                or type(result['revision']) is not int or result['revision'] < 1):
            raise Refusal("invalid_response")
    elif (set(result) != {'record_type', 'committed', 'repeated', 'request_id_digest', 'state'}
            or result['record_type'] != 'material_request_result/v1' or result['committed'] is not True
            or type(result['repeated']) is not bool or type(result['request_id_digest']) is not str
            or not SHA256.fullmatch(result['request_id_digest']) or result['state'] != 'open'):
        raise Refusal("invalid_response")
    return result


def contains_credential(value, credential):
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str) and credential in item:
            return True
        if isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return False


def exchange(base, operation, fields, credential, timeout, *, opener=None):
    encoded = None if operation == 'review' else json.dumps({'record_type': REQUEST_VERSION, 'operation': operation, **fields}).encode()
    if contains_credential(fields, credential):
        raise Refusal("credential_in_feedback")
    path = SUMMARY_PATH if operation == 'review' else '/api/v1/provisioning'
    request = urllib.request.Request(base+path, data=encoded,
        headers={'Authorization': 'Bearer '+credential, 'Accept': 'application/json', 'Content-Type': 'application/json'})
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler(), NoRedirect())
    deadline = time.monotonic()+timeout
    try:
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            if response.geturl() != request.full_url:
                raise Refusal("redirect_refused")
            parts, count = [], 0
            while count <= RESPONSE_LIMIT:
                if time.monotonic() > deadline:
                    raise Refusal("transport_failed")
                part = response.read1(min(8192, RESPONSE_LIMIT+1-count))
                if not part:
                    break
                parts.append(part)
                count += len(part)
            raw = b''.join(parts)
            if count > RESPONSE_LIMIT:
                raise Refusal("response_too_large")
            if credential.encode() in raw:
                raise Refusal("credential_echo_refused")
            value = parse_json(raw)
            if contains_credential(value, credential):
                raise Refusal("credential_echo_refused")
            if response.status != 200:
                code = value.get('error', {}).get('code') if type(value) is dict and type(value.get('error')) is dict else None
                raise Refusal(code if code in SAFE_CODES else "service_refused")
            return checked_result(operation, value)
    except Refusal:
        raise
    except Exception:
        raise Refusal("transport_failed") from None


def main(argv=None):
    attempted = False
    try:
        parser = SafeParser(prog='baltor-feedback', description=__doc__)
        parser.add_argument('operation', choices=('rate', 'request_material', 'review'))
        parser.add_argument('--origin', default='https://baltor.ai')
        parser.add_argument('--credential-environment', default='BALTOR_SERVICE_TOKEN')
        parser.add_argument('--allow-loopback-http', action='store_true', help='Local synthetic testing only.')
        parser.add_argument('--timeout', type=float, default=15)
        options = parser.parse_args(argv)
        base = origin(options.origin, options.allow_loopback_http)
        if not math.isfinite(options.timeout) or not 1 <= options.timeout <= 30:
            raise Refusal("invalid_timeout")
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', options.credential_environment):
            raise Refusal("invalid_credential_reference")
        credential = os.environ.get(options.credential_environment, '')
        if not re.fullmatch(r'[\x21-\x7e]{1,4096}', credential):
            raise Refusal("credential_missing_or_invalid")
        fields = {} if options.operation == 'review' else fields_for(options.operation, sys.stdin.buffer.read(INPUT_LIMIT+1))
        if contains_credential(fields, credential):
            raise Refusal("credential_in_feedback")
        attempted = True
        result = exchange(base, options.operation, fields, credential, options.timeout)
        print(json.dumps({'record_type': VERSION, 'ok': True, 'operation': options.operation, 'result': result}))
        return 0
    except Refusal as error:
        print(json.dumps({'record_type': VERSION, 'ok': False, 'error': str(error),
                          'effect_commitment': 'not_asserted' if attempted else 'not_attempted', 'automatic_retry': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
