"""Real loopback Public Good checks with synthetic accounts and private catalogue bytes."""
from __future__ import annotations

import asyncio
import base64
from concurrent.futures import wait
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
from unittest import mock

import httpx

from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.core.service_runtime.access import ServiceAccessAdministration, ServiceAccessRequest, ServiceAccessSession, ServiceClientAccessPolicy
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture, bundle_line
from loop_engine.core.service_runtime.catalogue_serving_checks import _Served, _application
from loop_engine.core.service_runtime.http import TIERED_PROVISIONING_REQUEST_VERSION, RETRIEVAL_REQUEST_VERSION
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.protocol_checks import _protocol_client
from loop_engine.core.service_runtime.public_good import DELIVERY_KIND, HOST_WINDOW_KIND, WINDOW_KIND, PublicGoodGrant, PublicGoodLimits
from loop_engine.core.service_runtime.records import DEFAULT_SCOPES, SubjectTenantRegistration
from loop_engine.core.service_runtime.runtime import ENTITLEMENT

EVENTS = []
BODY = b'SYNTHETIC_PUBLIC_ONE\n'
BINARY = bytes(range(256)) * 4
BUNDLE = [('SKILL.md', b'# Synthetic public package\n', 'text/markdown', 'skill_definition'),
          ('assets/payload.bin', BINARY, 'application/octet-stream', 'skill_asset'),
          ('references/note.md', b'Synthetic note.\n' * 20, 'text/markdown', 'skill_reference')]



def error_code(response):
    try:
        error = response.json().get('error')
        code = error.get('code') if isinstance(error, dict) else error
        return code if isinstance(code, str) and re.fullmatch(r'[a-z_]{1,80}', code) else None
    except (ValueError, AttributeError):
        return None


class Credentials:
    def __init__(self, raw):
        self.raw = raw

    def headers(self, _tenant='alpha'):
        return {'Authorization': 'Bearer ' + self.raw}


class PublicGoodHttp(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='pg-http-')))
        self.case = Fixture(root / 'service')
        self.case._bytes = {'public_one': (BODY,), 'public_bundle': tuple(row[1] for row in BUNDLE),
                            'paid_only': (b'SYNTHETIC_PAID_ONLY\n',)}
        self.case.publish([
            bundle_line('public_one', [('SKILL.md', BODY, 'text/markdown', 'skill_definition')], purpose='Synthetic public numeracy method'),
            bundle_line('public_bundle', BUNDLE, purpose='Synthetic public learning package'),
            bundle_line('paid_only', [('SKILL.md', b'SYNTHETIC_PAID_ONLY\n', 'text/markdown', 'skill_definition')], purpose='Synthetic ordinary paid method')])
        self.runtime = self.case.runtime
        self.now = [int(time.time())]
        self.runtime._clock = lambda: self.now[0]
        self.served = _Served(self.case)
        self.binding = self.served.provisioning
        self.access = self.binding.public_good
        self.view = self.binding.current_view()
        self.principal, self.raw = self.customer('unpaid-one')
        self.headers = {'Authorization': 'Bearer ' + self.raw}
        self.grants = []
        for identity in ('public_one', 'public_bundle'):
            item = self.view.catalogue.items[identity]
            from loop_engine.core.provisioning_server import ProvisioningItemBinding
            binding = ProvisioningItemBinding.from_item(item)
            self.grants.append(PublicGoodGrant(binding, self.view.item_versions[identity],
                self.view.qualification_resolver.resolve(binding).approval_ref, 'synthetic-rights-record', (4,),
                'Synthetic learning check only', self.now[0] + 120))
        self.access.configure(self.view, self.grants)
        self.base, self.app = self.stack.enter_context(running_http(self.served, application_factory=_application(self.served, 60)))
        self.client = self.stack.enter_context(httpx.Client(base_url=self.base, headers=self.headers, trust_env=False, timeout=15))
        self.meter = self.stack.enter_context(mock.patch.object(self.runtime, 'record_usage', side_effect=AssertionError('free path attempted paid metering')))

    def customer(self, subject, scopes=DEFAULT_SCOPES):
        issuer = 'https://synthetic-identity.example.test/auth/v1'
        self.runtime.ensure_subject_tenant(SubjectTenantRegistration(issuer, subject, 'customer', follows_active_release=True))
        principal = self.runtime.authenticate_subject(issuer, subject)
        session = ServiceAccessSession(principal.authentication_record_id, hashlib.sha256(subject.encode()).hexdigest(),
                                       self.now[0] + 86400, DEFAULT_SCOPES)
        manager = ServiceAccessAdministration(self.runtime, ServiceClientAccessPolicy(writes_authorized=True))
        result = manager.apply(principal, ServiceAccessRequest('issue', 'synthetic-key-' + subject, principal.tenant_id,
            label='Synthetic customer', scopes=scopes, lifetime_seconds=86400), session=session)
        return principal, result['token']

    def record(self, label, passed, **facts):
        row = {'case': self.id().rsplit('.', 1)[-1], 'step': label, 'passed': passed, **facts}
        EVENTS.append(row)
        if not passed:
            print(json.dumps({'concrete_failure': row}), flush=True)
        self.assertTrue(passed, label)

    def expect(self, response, status, label):
        self.record(label, response.status_code == status, status=response.status_code, expected_status=status,
                    error_code=error_code(response))
        return response

    def payload(self, operation, identity=None, **fields):
        return {'record_type': TIERED_PROVISIONING_REQUEST_VERSION, 'operation': operation,
                **({'identity': identity} if identity else {}), **fields}

    def post(self, operation, identity=None, **fields):
        return self.client.post('/api/v1/provisioning', json=self.payload(operation, identity, **fields))

    def download(self, identity='public_one', **fields):
        return self.client.post('/api/v1/download', json=self.payload('read', identity,
            expected_digest=self.view.catalogue.items[identity].digest, request_id='synthetic-download', **fields))

    def configure(self, grants=None, limits=None):
        before = self.access.snapshot(self.binding.current_view())
        return self.access.configure(self.binding.current_view(), self.grants if grants is None else grants,
            limits=limits or before.limits, expected_version=before.version)

    def rows(self, kind, tenant=None):
        with self.runtime._catalog.store() as store:
            return self.runtime._catalog.rows(store, kind, tenant or self.principal.tenant_id)

    def no_billing(self):
        self.assertEqual(self.runtime.revalidate(self.principal).entitlement, 'metadata')
        self.assertEqual(self.runtime.usage_for(self.principal)['records'], 0)
        self.assertEqual(self.meter.call_count, 0)
        with self.runtime._catalog.store() as store:
            self.assertIsNone(self.runtime._catalog.read(store, ENTITLEMENT, self.principal.tenant_id))

    def test_unpaid_metadata_manifest_direct_body_bundle_and_file_bytes(self):
        session = self.expect(self.client.get('/api/v1/session'), 200, 'normal_unpaid_session').json()['result']
        self.assertEqual(session['access_source'], 'none')
        collection = self.expect(self.client.get('/api/v1/public-good'), 200, 'public_good_metadata').json()['result']
        self.assertEqual({row['identity'] for row in collection['items']}, {'public_one', 'public_bundle'})
        manifest = self.expect(self.post('manifest', 'public_one', expected_digest=self.view.catalogue.items['public_one'].digest),
                               200, 'exact_manifest').json()['result']
        self.assertTrue(manifest['body_allowed'])
        self.assertEqual(manifest['digest'], hashlib.sha256(BODY).hexdigest())
        body = self.expect(self.download(), 200, 'unpaid_exact_body')
        self.assertEqual(body.content, BODY)
        self.assertEqual(body.headers['x-content-sha256'], hashlib.sha256(BODY).hexdigest())
        package = self.expect(self.download('public_bundle'), 200, 'package_document')
        self.assertEqual(package.content, self.view.packages['public_bundle'].document())
        binary = self.expect(self.download('public_bundle', path='assets/payload.bin'), 200, 'binary_file')
        self.assertEqual(binary.content, BINARY)
        self.assertEqual(binary.headers['x-content-sha256'], hashlib.sha256(BINARY).hexdigest())
        self.no_billing()

    def file_collection_grants(self):
        self.grants = [replace(grant, useful_paths=('SKILL.md',), display_name='Synthetic public method',
                               initiatives=('accessible-learning',)) for grant in self.grants]
        self.configure()

    def test_public_file_metadata_filters_and_pagination_do_not_read_bodies(self):
        self.file_collection_grants()
        from loop_engine.core.service_runtime.catalogue_serving import CatalogueView
        with mock.patch.object(CatalogueView, 'read_package_file', side_effect=AssertionError('metadata read file bytes')):
            with httpx.Client(base_url=self.base, trust_env=False, timeout=10) as anonymous:
                first = self.expect(anonymous.get('/api/v1/public-good/files?page_size=1'), 200, 'anonymous_file_metadata').json()['result']
                second = self.expect(anonymous.get('/api/v1/public-good/files?page_size=1&page=2'), 200, 'next_metadata_page').json()['result']
                filtered = self.expect(anonymous.get('/api/v1/public-good/files', params={
                    'goal': '4', 'media_type': 'text/markdown', 'initiative': 'accessible-learning',
                    'package': 'public_bundle', 'query': 'SKILL.md'}), 200, 'conjunctive_file_filters').json()['result']
        self.assertEqual(first['record_type'], 'public_good_file_collection/v1')
        self.assertEqual((first['packages'], first['distinct_useful_files'], first['file_placements']), (2, 2, 4))
        self.assertTrue(first['authentication_required'])
        self.assertFalse(first['subscription_required'])
        self.assertTrue(first['has_next'])
        self.assertFalse(second['has_next'])
        self.assertNotEqual(first['items'][0]['file_sha256'], second['items'][0]['file_sha256'])
        self.assertEqual(filtered['matches'], 1)
        placement = filtered['items'][0]['placements'][0]
        self.assertEqual((placement['identity'], placement['path']), ('public_bundle', 'SKILL.md'))
        self.assertEqual(placement['body_digest'], self.view.catalogue.items['public_bundle'].digest)
        self.assertNotIn(BODY.decode(), json.dumps(first))
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.no_billing()

    def test_public_file_query_validation_and_envelope_limit(self):
        self.file_collection_grants()
        invalid = ('page=0', 'page=10001', 'page=1&page=2', 'page_size=0', 'page_size=51',
                   'page_size=100', 'page_size=true', 'goal=18', 'media_type=text',
                   'initiative=Bad%20Value', 'unrecognized=1', 'query=%00')
        for query in invalid:
            with self.subTest(query=query):
                self.expect(self.client.get('/api/v1/public-good/files?' + query), 400, 'invalid_file_query_refused')
        self.expect(self.client.get('/api/v1/public-good?page_size=1'), 400, 'package_query_contract_unchanged')
        self.app.configuration = replace(self.app.configuration, maximum_response_bytes=256)
        self.expect(self.client.get('/api/v1/public-good/files'), 413, 'file_metadata_envelope_refused')
        self.no_billing()

    def test_public_file_projection_rechecks_policy_and_expiry(self):
        self.file_collection_grants()
        from loop_engine.core.service_runtime import public_good_files
        original = public_good_files.collection
        def withdraw(view, snapshot, **fields):
            result = original(view, snapshot, **fields)
            self.configure(grants=[])
            return result
        with mock.patch.object(public_good_files, 'collection', withdraw):
            response = self.expect(self.client.get('/api/v1/public-good/files'), 409, 'file_metadata_policy_changed')
            self.assertNotIn('placements', response.text)
        self.configure()
        self.now[0] += 121
        expired = self.expect(self.client.get('/api/v1/public-good/files'), 200, 'expired_file_inventory').json()['result']
        self.assertEqual((expired['packages'], expired['distinct_useful_files'], expired['items']), (0, 0, []))
        self.no_billing()

    def test_real_mcp_package_and_file_delivery_without_billing(self):
        async def run():
            async with _protocol_client(self.base, Credentials(self.raw), 'legacy') as protocol:
                manifest = await protocol.call_tool('provisioning_manifest', {'identity': 'public_bundle'})
                package = await protocol.call_tool('provisioning_read', {'identity': 'public_bundle',
                    'expected_digest': self.view.catalogue.items['public_bundle'].digest, 'request_id': 'mcp-package'})
                selected = await protocol.call_tool('provisioning_read', {'identity': 'public_bundle', 'path': 'assets/payload.bin',
                    'expected_digest': self.view.catalogue.items['public_bundle'].digest, 'request_id': 'mcp-file'})
                single = await protocol.call_tool('provisioning_read', {'identity': 'public_one', 'request_id': 'mcp-body'})
                return manifest, package, selected, single
        manifest, package, selected, single = asyncio.run(run())
        for label, answer in (('mcp_manifest', manifest), ('mcp_package', package), ('mcp_file', selected), ('mcp_body', single)):
            error = answer.structured_content.get('error', {}) if answer.structured_content else {}
            self.record(label, not answer.is_error, error_code=error.get('code'))
        values = {row['path']: base64.b64decode(row['content']) if row['encoding'] == 'base64' else row['content'].encode()
                  for row in package.structured_content['result']['files']}
        self.assertEqual(values, {path: data for path, data, _media, _role in BUNDLE})
        self.assertEqual(len(selected.structured_content['result']['files']), 1)
        self.assertEqual(single.structured_content['result']['body'].encode(), BODY)
        self.no_billing()

    def test_protocol_public_good_files_matches_web_and_reads_exact_selection(self):
        self.file_collection_grants()
        fields = {'goal': '4', 'query': 'SKILL.md', 'package': 'public_bundle', 'page_size': 1}
        expected = self.client.get('/api/v1/public-good/files', params=fields).json()['result']
        async def run(mode):
            async with _protocol_client(self.base, Credentials(self.raw), mode) as protocol:
                listed = await protocol.list_tools()
                tool = next(row for row in listed.tools if row.name == 'public_good_files')
                self.assertTrue(tool.annotations.read_only_hint)
                answer = await protocol.call_tool('public_good_files', fields)
                self.assertFalse(answer.is_error, answer.structured_content)
                self.assertEqual(answer.structured_content['result'], expected)
                placement = answer.structured_content['result']['items'][0]['placements'][0]
                selected = await protocol.call_tool('provisioning_read', {
                    'identity': placement['identity'], 'expected_digest': placement['body_digest'],
                    'path': placement['path'], 'request_id': 'selected-free-' + mode})
                self.assertFalse(selected.is_error, selected.structured_content)
                delivered = selected.structured_content['result']['files'][0]
                self.assertEqual(hashlib.sha256(delivered['content'].encode()).hexdigest(),
                    answer.structured_content['result']['items'][0]['file_sha256'])
        for mode in ('legacy', '2026-07-28'):
            with self.subTest(mode=mode):
                asyncio.run(run(mode))
        self.no_billing()

    def test_protocol_public_good_media_type_uses_the_same_domain_as_http(self):
        self.file_collection_grants()
        media_type = 'a' * 63 + '/' + 'b' * 127
        expected = self.client.get('/api/v1/public-good/files', params={'media_type': media_type}).json()['result']
        async def read():
            async with _protocol_client(self.base, Credentials(self.raw), 'legacy') as protocol:
                return await protocol.call_tool('public_good_files', {'media_type': media_type})
        answer = asyncio.run(read())
        self.assertFalse(answer.is_error, answer.structured_content)
        self.assertEqual(answer.structured_content['result'], expected)
        self.assertEqual(expected['matches'], 0)
        self.no_billing()

    def test_protocol_public_good_files_refuses_invalid_scope_policy_and_envelope(self):
        self.file_collection_grants()
        async def read(fields=None, key=None):
            async with _protocol_client(self.base, Credentials(key or self.raw), 'legacy') as protocol:
                return await protocol.call_tool('public_good_files', fields or {})
        for fields in ({'goal': '18'}, {'page_size': 51}, {'page': True}, {'page': 0},
                       {'identity': 'paid_only'}, {'query': '\x00'}):
            with self.subTest(fields=fields):
                answer = asyncio.run(read(fields))
                self.assertTrue(answer.is_error)
        _, usage_key = self.customer('usage-only', scopes=('usage:read',))
        denied = asyncio.run(read(key=usage_key))
        self.assertTrue(denied.is_error)
        self.assertIn(denied.structured_content['error']['code'], ('scope_required', 'insufficient_scope'))
        from loop_engine.core.service_runtime import public_good_files
        original = public_good_files.collection
        def withdraw(view, snapshot, **fields):
            result = original(view, snapshot, **fields)
            self.configure(grants=[])
            return result
        with mock.patch.object(public_good_files, 'collection', withdraw):
            changed = asyncio.run(read())
        self.assertTrue(changed.is_error)
        self.assertEqual(changed.structured_content['error']['code'], 'public_good_authority_changed')
        self.assertNotIn('placements', json.dumps(changed.structured_content))
        self.configure()
        self.app.configuration = replace(self.app.configuration, maximum_response_bytes=256)
        oversized = asyncio.run(read())
        self.assertTrue(oversized.is_error)
        self.assertEqual(oversized.structured_content['error']['code'], 'response_limit_exceeded')
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.no_billing()

    def test_protocol_public_good_files_rechecks_account_and_known_wrong_scope_control(self):
        self.file_collection_grants()
        async def read(key):
            async with _protocol_client(self.base, Credentials(key), 'legacy') as protocol:
                return await protocol.call_tool('public_good_files', {})
        _, usage_key = self.customer('control-usage-only', scopes=('usage:read',))
        self.assertTrue(asyncio.run(read(usage_key)).is_error)
        with mock.patch.object(self.app, '_require_scope', return_value=None):
            self.assertFalse(asyncio.run(read(usage_key)).is_error,
                             'known-wrong missing scope guard must admit the otherwise refused query')
        from loop_engine.core.service_runtime import public_good_files
        original = public_good_files.collection
        def disable(view, snapshot, **fields):
            result = original(view, snapshot, **fields)
            self.runtime.set_tenant_enabled(self.principal.tenant_id, False)
            return result
        with mock.patch.object(public_good_files, 'collection', disable):
            answer = asyncio.run(read(self.raw))
        self.assertTrue(answer.is_error)
        self.assertNotIn('placements', json.dumps(answer.structured_content))
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.assertEqual(self.meter.call_count, 0)

    def test_anonymous_disabled_ungranted_and_wrong_digest_body_refusals(self):
        with httpx.Client(base_url=self.base, trust_env=False, timeout=10) as anonymous:
            shown = self.expect(anonymous.get('/api/v1/public-good'), 200, 'anonymous_metadata_only')
            self.assertNotIn(BODY.decode(), shown.text)
            self.expect(anonymous.post('/api/v1/download', json=self.payload('read', 'public_one', request_id='anonymous')),
                        401, 'anonymous_body_refused')
        self.expect(self.download('paid_only'), 403, 'ungranted_requires_normal_plan')
        wrong = self.client.post('/api/v1/download', json=self.payload('read', 'public_one', expected_digest='0' * 64, request_id='wrong-digest'))
        self.record('wrong_digest_refused', wrong.status_code in (400, 403, 404), status=wrong.status_code, error_code=error_code(wrong))
        self.assertNotIn(BODY, wrong.content)
        self.runtime.set_tenant_enabled(self.principal.tenant_id, False)
        self.expect(self.download(), 401, 'disabled_account_refused')
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.assertEqual(self.meter.call_count, 0)

    def test_rate_and_byte_caps_are_atomic_and_nonbillable(self):
        length = len(BODY)
        self.configure(limits=PublicGoodLimits(requests_per_window=3, bytes_per_window=2 * length - 1,
                                             maximum_response_bytes=length))
        self.expect(self.download(), 200, 'first_bounded_body')
        refused = self.expect(self.download(), 429, 'byte_budget_exhausted')
        self.assertEqual(error_code(refused), 'public_good_rate_limited')
        self.assertGreater(int(refused.headers['retry-after']), 0)
        window = self.rows(WINDOW_KIND)[0]['payload']
        self.assertEqual((window['requests'], window['bytes_reserved']), (1, length))
        self.no_billing()

    def test_host_rate_and_byte_caps_cover_distinct_unpaid_accounts(self):
        other, raw = self.customer('host-limit-second')
        length = len(BODY)
        policies = (PublicGoodLimits(host_requests_per_window=1),
                    PublicGoodLimits(host_bytes_per_window=2 * length - 1, maximum_response_bytes=length))
        for index, limits in enumerate(policies):
            if index:
                self.now[0] += 3601
                self.grants = [replace(grant, expires_at=self.now[0] + 120) for grant in self.grants]
            self.configure(limits=limits)
            self.expect(self.download(), 200, 'first_account_uses_host_allowance')
            response = self.client.post('/api/v1/download', headers={'Authorization': 'Bearer ' + raw},
                json=self.payload('read', 'public_one', expected_digest=self.view.catalogue.items['public_one'].digest,
                                  request_id='second-account-host-limit'))
            self.expect(response, 429, 'shared_host_' + ('request_cap' if index == 0 else 'byte_cap'))
            self.assertEqual(error_code(response), 'public_good_rate_limited')
            self.assertEqual(len(self.rows(DELIVERY_KIND, other.tenant_id)), 0)
        self.no_billing()

    def test_response_cap_refuses_before_delivery_and_read_error_consumes_attempt(self):
        self.configure(limits=PublicGoodLimits(maximum_response_bytes=len(BODY) - 1))
        response = self.download()
        self.record('response_cap_refused', response.status_code != 200, status=response.status_code, error_code=error_code(response))
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.assertEqual(len(self.rows(WINDOW_KIND)), 0)
        self.configure(limits=PublicGoodLimits(requests_per_window=2))
        original = self.binding.body_reader
        attempts = []
        def fail_once(item):
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError('synthetic body read failure')
            return original(item)
        self.binding.body_reader = fail_once
        failed = self.download()
        self.record('failed_body_not_delivered', failed.status_code != 200, status=failed.status_code, error_code=error_code(failed))
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.expect(self.download(), 200, 'retry_is_a_second_attempt')
        self.assertEqual(self.rows(WINDOW_KIND)[0]['payload']['requests'], 2)
        self.no_billing()

    def test_withdrawal_during_body_or_file_read_returns_no_bytes(self):
        original = self.binding.body_reader
        def withdraw(item):
            self.configure(grants=[])
            return original(item)
        self.binding.body_reader = withdraw
        response = self.download()
        self.record('withdrawal_during_body_read', response.status_code != 200, status=response.status_code, error_code=error_code(response))
        self.assertNotIn(BODY, response.content)
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.binding.body_reader = original
        self.configure()
        view_type = type(self.binding.current_view())
        original_file = view_type.read_package_file
        def withdraw_file(view, identity, path):
            result = original_file(view, identity, path)
            self.configure(grants=[])
            return result
        with mock.patch.object(view_type, 'read_package_file', withdraw_file):
            response = self.download('public_bundle', path='assets/payload.bin')
        self.record('withdrawal_during_native_file_read', response.status_code != 200, status=response.status_code, error_code=error_code(response))
        self.assertNotIn(BINARY, response.content)
        self.assertEqual(len(self.rows(DELIVERY_KIND)), 0)
        self.no_billing()

    def test_withdrawn_or_expired_policy_invalidates_cursor_and_cached_permissions(self):
        first = self.expect(self.post('list', page_size=1), 200, 'initial_paged_list').json()['result']
        self.assertIsNotNone(first['next_cursor'])
        self.configure(grants=[])
        changed = self.post('list', page_size=1, cursor=first['next_cursor'])
        self.expect(changed, 409, 'withdrawal_invalidates_cursor')
        fresh = self.expect(self.post('list', page_size=50), 200, 'fresh_unpaid_permissions').json()['result']
        self.assertTrue(all(not row['body_allowed'] for row in fresh['items']))
        search = self.client.post('/api/v1/retrieval', json={'record_type': RETRIEVAL_REQUEST_VERSION, 'query': 'public', 'mode': 'lexical'})
        self.expect(search, 200, 'fresh_search_after_withdrawal')
        self.assertTrue(all(not row['body_allowed'] for row in search.json()['result']['hits']))
        self.configure()
        first = self.expect(self.post('list', page_size=1), 200, 'new_grant_cursor').json()['result']
        self.now[0] += 121
        self.expect(self.post('list', page_size=1, cursor=first['next_cursor']), 409, 'expiry_invalidates_cursor')
        self.expect(self.download(), 403, 'expired_grant_cannot_deliver')
        self.no_billing()

    def test_report_eligibility_follows_successful_exact_free_response(self):
        fields = {'expected_digest': self.view.catalogue.items['public_one'].digest, 'reason': 'Synthetic QA report'}
        self.expect(self.post('report', 'public_one', **fields), 409, 'report_before_download_refused')
        self.expect(self.download(), 200, 'free_response_before_report')
        self.expect(self.post('report', 'public_one', **fields), 200, 'report_after_free_download')
        self.no_billing()

    def test_rating_eligibility_follows_successful_exact_free_response(self):
        fields = {'expected_digest': self.view.catalogue.items['public_one'].digest, 'value': 'useful'}
        self.expect(self.post('rate', 'public_one', **fields), 409, 'rating_before_download_refused')
        self.expect(self.download(), 200, 'free_response_before_rating')
        self.expect(self.post('rate', 'public_one', **fields), 200, 'rating_after_free_download')
        self.no_billing()

    def test_transport_serialization_failure_does_not_create_download_eligibility(self):
        result = self.expect(self.post('read', 'public_one', request_id='baseline-json'), 200, 'baseline_json_response')
        record_bytes = len(json.dumps(result.json()['result'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
        actual_bytes = len(result.content)
        self.assertGreater(actual_bytes, record_bytes)
        self.app.configuration = replace(self.app.configuration, maximum_response_bytes=(record_bytes + actual_bytes) // 2)
        other, raw = self.customer('unpaid-second')
        rejected = self.client.post('/api/v1/provisioning', headers={'Authorization': 'Bearer ' + raw},
            json=self.payload('read', 'public_one', request_id='over-envelope-cap'))
        self.expect(rejected, 413, 'outer_response_cap_refused')
        deliveries = self.rows(DELIVERY_KIND, other.tenant_id)
        self.record('no_delivery_on_serialization_refusal', len(deliveries) == 0, delivery_records=len(deliveries),
                    reserved_response_cap=self.app.configuration.maximum_response_bytes,
                    recorded_payload_bytes=record_bytes, complete_baseline_response_bytes=actual_bytes)
        self.no_billing()

    def mcp_envelope_refusal(self, *, restore_early_completion=False):
        async def read(raw, request_id):
            async with _protocol_client(self.base, Credentials(raw), 'legacy') as protocol:
                return await protocol.call_tool('provisioning_read', {'identity': 'public_one', 'request_id': request_id})
        baseline = asyncio.run(read(self.raw, 'baseline-mcp'))
        self.assertFalse(baseline.is_error)
        full_size = len(baseline.model_dump_json(by_alias=True).encode())
        self.app.configuration = replace(self.app.configuration, maximum_response_bytes=full_size - 1)
        other, raw = self.customer('unpaid-mcp-second')
        if restore_early_completion:
            original = self.app._protocol_read
            def early(authentication, fields, step=None, completions=None):
                return original(authentication, fields, step, completions=None)
            with mock.patch.object(self.app, '_protocol_read', early):
                refused = asyncio.run(read(raw, 'mcp-over-envelope-cap'))
        else:
            refused = asyncio.run(read(raw, 'mcp-over-envelope-cap'))
        code = refused.structured_content.get('error', {}).get('code') if refused.structured_content else None
        self.record('mcp_final_envelope_refused', refused.is_error, error_code=code,
                    maximum_response_bytes=self.app.configuration.maximum_response_bytes)
        self.assertEqual(code, 'response_limit_exceeded')
        return self.rows(DELIVERY_KIND, other.tenant_id)

    def test_final_mcp_envelope_cap_cannot_create_download_eligibility(self):
        deliveries = self.mcp_envelope_refusal()
        self.record('no_delivery_on_mcp_envelope_refusal', len(deliveries) == 0, delivery_records=len(deliveries))
        self.no_billing()

    def test_known_wrong_early_mcp_completion_is_detected(self):
        deliveries = self.mcp_envelope_refusal(restore_early_completion=True)
        self.record('known_wrong_early_mcp_completion_detected', len(deliveries) == 1, delivery_records=len(deliveries))
        self.no_billing()

    def delayed_first_body(self):
        entered, release, attempts, futures = threading.Event(), threading.Event(), [], []
        original = self.binding.body_reader
        original_submit = self.app._workers.submit
        def reader(item):
            attempts.append(1)
            if len(attempts) == 1:
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('synthetic test did not release reader')
            return original(item)
        def submit(*args, **kwargs):
            future = original_submit(*args, **kwargs)
            futures.append(future)
            return future
        self.stack.callback(release.set)
        self.stack.enter_context(mock.patch.object(self.app._workers, 'submit', submit))
        self.binding.body_reader = reader
        # The deadline covers the whole worker, so the stages before the body read count against it. It must expire
        # while the reader is held, not before the worker reaches it: at 0.2 s it expired first once on October 5,
        # 2026, in a CI shard run on a machine at load average 28. The reader is held for up to 5 seconds.
        self.app.configuration = replace(self.app.configuration, request_timeout_seconds=1.0)
        return entered, release, attempts, futures

    def assert_late_worker_finished_without_delivery(self, entered, release, futures, label):
        self.assertTrue(entered.is_set(), 'timeout control did not reach the body reader')
        release.set()
        _done, pending = wait(futures, timeout=5)
        self.assertFalse(pending, 'synthetic worker did not finish')
        deliveries = self.rows(DELIVERY_KIND)
        self.record(label, len(deliveries) == 0, delivery_records=len(deliveries))

    def test_late_http_completion_is_not_finalized_by_same_identity_retry(self):
        entered, release, attempts, futures = self.delayed_first_body()
        timed_out = self.post('read', 'public_one', request_id='same-logical-http')
        self.expect(timed_out, 504, 'http_body_deadline')
        self.assert_late_worker_finished_without_delivery(entered, release, futures, 'late_http_tuple_not_finalized')
        self.expect(self.post('read', 'public_one', request_id='same-logical-http'), 200, 'http_retry_separate_completion')
        states = sorted(value['state'] for value in self.rows(WINDOW_KIND)[0]['payload']['reservations'].values())
        self.assertEqual(states, ['complete', 'reserved'])
        self.assertEqual(len(attempts), 2)
        self.no_billing()

    def test_late_mcp_completion_is_not_finalized_by_same_identity_retry(self):
        entered, release, attempts, futures = self.delayed_first_body()
        async def read():
            async with _protocol_client(self.base, Credentials(self.raw), 'legacy') as protocol:
                return await protocol.call_tool('provisioning_read', {'identity': 'public_one', 'request_id': 'same-logical-mcp'})
        timed_out = asyncio.run(read())
        code = timed_out.structured_content.get('error', {}).get('code') if timed_out.structured_content else None
        self.record('mcp_body_deadline', timed_out.is_error and code == 'deadline_exceeded', error_code=code)
        self.assert_late_worker_finished_without_delivery(entered, release, futures, 'late_mcp_tuple_not_finalized')
        self.assertFalse(asyncio.run(read()).is_error)
        states = sorted(value['state'] for value in self.rows(WINDOW_KIND)[0]['payload']['reservations'].values())
        self.assertEqual(states, ['complete', 'reserved'])
        self.assertEqual(len(attempts), 2)
        self.no_billing()

    def test_download_timeout_does_not_finalize_after_request_ended(self):
        entered, release, attempts, futures = self.delayed_first_body()
        self.expect(self.download(), 504, 'download_body_deadline')
        self.assert_late_worker_finished_without_delivery(entered, release, futures, 'late_download_not_finalized')
        self.assertEqual(len(attempts), 1)
        self.no_billing()



if __name__ == '__main__':
    unittest.main()
