"""Feedback MCP/API/CLI round trips over loopback; synthetic records, no remote providers."""
from __future__ import annotations

import asyncio
from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import httpx

from loop_engine.core.service_runtime import feedback, http as service_http
from loop_engine.core.service_runtime.feedback_checks import prepared
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.protocol_checks import _protocol_client, _protocol_message
from loop_engine.core.service_runtime.records import ServiceCommitUnknown
from tools import baltor_feedback as cli

ROOT = Path(__file__).resolve().parents[1]
NOTE, DESCRIPTION, FILTER = 'PRIVATE_NOTE_FIXTURE', 'PRIVATE_REQUEST_FIXTURE', 'PRIVATE_FILTER_FIXTURE'


class FeedbackAdapters(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.fixture = prepared(folder/'domain')
        self.runtime = self.fixture.runtime
        self.base, self.app = self.stack.enter_context(running_http(self.fixture))
        self.http = self.stack.enter_context(httpx.Client(base_url=self.base, trust_env=False, timeout=15))
        self.binding = self.fixture.bindings['skill.alpha']

    def rate_fields(self, **changes):
        return {'identity': 'skill.alpha', 'expected_digest': self.binding.body_digest, 'value': 'useful', 'note': NOTE, **changes}

    def post(self, operation, fields, tenant='alpha'):
        return self.http.post('/api/v1/provisioning', headers=self.fixture.headers(tenant),
                              json={'record_type': 'service_provisioning_request/v2', 'operation': operation, **fields})

    def mcp(self, name, arguments, tenant='alpha'):
        async def call():
            async with _protocol_client(self.base, self.fixture, '2026-07-28', tenant=tenant) as client:
                value = await client.call_tool(name, arguments)
                return None, {'isError': value.is_error, 'structuredContent': value.structured_content}
        return asyncio.run(call())

    def downloaded(self):
        result = self.fixture.provisioning.invoke(self.fixture.keys['alpha'].key, 'read',
                                                  identity='skill.alpha', request_id='feedback-download')
        self.assertTrue(result)

    def seed(self):
        self.downloaded()
        self.assertEqual(self.post('rate', self.rate_fields()).status_code, 200)
        self.assertEqual(self.post('request_material', {'request_id': 'qa-one', 'description': DESCRIPTION}).status_code, 200)
        self.app.feedback.record_search_gap({'query': 'never retained query', 'mode': 'lexical',
                                            'filters': {'kind': {'equals': FILTER}}})

    def assert_counts_only(self, value):
        self.assertEqual(value, {'record_type': feedback.SUMMARY_VERSION,
            'ratings': {'useful': 1, 'not_useful': 0, 'items_rated': 1},
            'material_requests': {'total': 1, 'open': 1}, 'search_gaps': {'groups': 1, 'searches': 1}})
        encoded = json.dumps(value)
        for private in (NOTE, DESCRIPTION, FILTER, 'skill.alpha', 'tenant_id', 'notes', 'description', 'hour'):
            self.assertNotIn(private, encoded)

    def test_mcp_discovery_and_both_eras_share_domain_contracts(self):
        self.downloaded()
        usage = self.fixture.usage()['records']
        async def check():
            for mode in ('legacy', '2026-07-28'):
                async with _protocol_client(self.base, self.fixture, mode) as client:
                    listed = await client.list_tools()
                    self.assertTrue({'provisioning_rate', 'provisioning_request_material', 'feedback_review'} <= {tool.name for tool in listed.tools})
                    rated = await client.call_tool('provisioning_rate', self.rate_fields())
                    self.assertFalse(rated.is_error)
                    self.assertEqual(rated.structured_content['result']['record_type'], feedback.RATING_RESULT_VERSION)
                    wanted = {'request_id': 'same-logical-request', 'description': DESCRIPTION}
                    first = await client.call_tool('provisioning_request_material', wanted)
                    self.assertFalse(first.is_error)
                    repeat = self.post('request_material', wanted).json()['result']
                    self.assertTrue(repeat['repeated'])
                    self.assertEqual(first.structured_content['result']['request_id_digest'], repeat['request_id_digest'])
        asyncio.run(check())
        self.assertEqual(self.fixture.usage()['records'], usage)
        rows = feedback.feedback_rows(self.runtime)
        self.assertEqual(len(rows[feedback.RATING_KIND]), 1)
        self.assertEqual(rows[feedback.RATING_KIND][0]['revision'], 2)
        self.assertEqual(len(rows[feedback.REQUEST_KIND]), 1)

    def test_rating_tool_does_not_advertise_exact_idempotency(self):
        async def listed():
            async with _protocol_client(self.base, self.fixture, '2026-07-28') as client:
                return {tool.name: tool for tool in (await client.list_tools()).tools}
        tools = asyncio.run(listed())
        self.assertFalse(tools['provisioning_rate'].annotations.idempotent_hint)
        self.assertFalse(tools['provisioning_rate'].annotations.read_only_hint)
        self.assertTrue(tools['provisioning_request_material'].annotations.idempotent_hint)
        self.assertIn('no automatic expiry', tools['provisioning_rate'].description)
        self.assertIn('aggregate feedback counts', tools['feedback_review'].description)

    def test_no_download_wrong_version_and_unknown_fields_refuse(self):
        for values in (self.rate_fields(), self.rate_fields(expected_digest='f'*64), self.rate_fields(tenant_id='beta')):
            _response, result = self.mcp('provisioning_rate', values)
            self.assertTrue(result['isError'])
        _response, result = self.mcp('provisioning_request_material', {'request_id': 'a', 'description': 'x'*2001})
        self.assertTrue(result['isError'])
        self.assertEqual(feedback.feedback_rows(self.runtime)[feedback.RATING_KIND], [])
        self.assertEqual(feedback.feedback_rows(self.runtime)[feedback.REQUEST_KIND], [])

    def test_conflicting_material_request_preserves_first_record(self):
        fields = {'request_id': 'stable', 'description': DESCRIPTION}
        self.assertEqual(self.post('request_material', fields).status_code, 200)
        _response, result = self.mcp('provisioning_request_material', {**fields, 'description': 'Changed text'})
        self.assertTrue(result['isError'])
        self.assertEqual(result['structuredContent']['error']['code'], feedback.REQUEST_IDENTITY_CONFLICT)
        self.assertEqual(feedback.feedback_rows(self.runtime)[feedback.REQUEST_KIND][0]['description'], DESCRIPTION)

    def test_staff_api_and_mcp_return_counts_only_legacy_full_view_unchanged(self):
        self.seed()
        response = self.http.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH, headers=self.fixture.headers('operator'))
        self.assertEqual(response.status_code, 200)
        self.assert_counts_only(response.json()['result'])
        _response, result = self.mcp('feedback_review', {}, 'operator')
        self.assertFalse(result['isError'])
        self.assert_counts_only(result['structuredContent']['result'])
        legacy = self.http.get(service_http.ADMIN_FEEDBACK_PATH, headers=self.fixture.headers('operator')).json()['result']
        self.assertEqual(legacy['ratings']['items'][0]['notes'], [NOTE])
        self.assertEqual(legacy['material_requests'][0]['description'], DESCRIPTION)

    def test_summary_refuses_anonymous_normal_customer_and_injected_filters(self):
        self.seed()
        self.assertEqual(self.http.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH).status_code, 401)
        self.assertEqual(self.http.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH, headers=self.fixture.headers()).status_code, 403)
        for tenant, fields in (('alpha', {}), ('operator', {'tenant_id': 'alpha'})):
            _response, result = self.mcp('feedback_review', fields, tenant)
            self.assertTrue(result['isError'])
            for private in (NOTE, DESCRIPTION, FILTER):
                self.assertNotIn(private, json.dumps(result))
        self.assertEqual(self.http.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH+'?query=anything', headers=self.fixture.headers('operator')).status_code, 400)

    def revoke_when_encoded(self):
        original = service_http._json_bytes
        done = []
        def encode(value):
            encoded = original(value)
            if not done and value.get('result', {}).get('record_type') == feedback.SUMMARY_VERSION:
                done.append(True)
                self.runtime.revoke_key('operator', self.fixture.keys['operator'].key_id)
            return encoded
        return mock.patch.object(service_http, '_json_bytes', encode)

    def test_api_summary_rechecks_revocation_after_serialization(self):
        self.seed()
        with self.revoke_when_encoded():
            response = self.http.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH, headers=self.fixture.headers('operator'))
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('items_rated', response.text)

    def test_mcp_summary_rechecks_revocation_after_serialization(self):
        self.seed()
        with self.revoke_when_encoded():
            _response, result = self.mcp('feedback_review', {}, 'operator')
        self.assertTrue(result['isError'])
        self.assertNotIn('items_rated', json.dumps(result))

    def test_known_wrong_without_completion_guard_releases_revoked_summary(self):
        self.seed()
        with self.revoke_when_encoded(), mock.patch.object(self.app, '_verify_staff_feedback', lambda _context, **_options: None):
            response = self.http.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH, headers=self.fixture.headers('operator'))
        self.assertEqual(response.status_code, 200)
        self.assert_counts_only(response.json()['result'])

    def test_unknown_commit_is_one_attempt_and_does_not_log_private_text(self):
        with mock.patch.object(self.app.feedback, 'request_material', side_effect=ServiceCommitUnknown()) as write:
            _response, result = self.mcp('provisioning_request_material', {'request_id': 'unknown', 'description': DESCRIPTION})
        self.assertEqual(write.call_count, 1)
        self.assertTrue(result['isError'])
        error = result['structuredContent']
        self.assertEqual(error['effect_commitment'], 'not_asserted')
        self.assertFalse(error['automatic_retry'])
        saved = self.app.failure_journal.detail(error['request_reference'])
        self.assertNotIn(DESCRIPTION, json.dumps(saved))
        self.assertNotIn(self.fixture.keys['alpha'].key, json.dumps(saved))

    def test_explicit_request_body_capture_is_private_diagnostics_not_anonymized(self):
        from loop_engine.core.service_runtime.observability import ServiceObservabilityPolicy
        def application(configuration):
            return service_http.ServiceHttpApplication(self.runtime, self.fixture.provisioning, configuration,
                observability=ServiceObservabilityPolicy(payload_capture='metadata_and_request_body'))
        with running_http(self.fixture, application_factory=application) as (base, app):
            async def check():
                async with _protocol_client(base, self.fixture, '2026-07-28') as client:
                    result = await client.call_tool('provisioning_request_material',
                        {'request_id': 'capture-control', 'description': DESCRIPTION+'x'*2001})
                    self.assertTrue(result.is_error)
                    self.assertNotIn(DESCRIPTION, json.dumps(result.structured_content))
                    saved = app.failure_journal.detail(result.structured_content['request_reference'])
                    self.assertIn(DESCRIPTION, json.dumps(saved))
                    self.assertNotIn(self.fixture.keys['alpha'].key, json.dumps(saved))
            asyncio.run(check())

    def run_cli(self, operation, data=None, tenant='alpha', extra=()):
        environment = {'PATH': os.environ.get('PATH', ''), 'BALTOR_SERVICE_TOKEN': self.fixture.keys[tenant].key,
                       'NO_PROXY': '127.0.0.1,localhost'}
        return subprocess.run([sys.executable, '-B', str(ROOT/'tools/baltor_feedback.py'), operation, '--origin', self.base,
                               '--allow-loopback-http', *extra], input=b'' if data is None else json.dumps(data).encode(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, timeout=30)

    def test_cli_submissions_and_staff_summary_round_trip(self):
        self.downloaded()
        rated = self.run_cli('rate', self.rate_fields())
        wanted = self.run_cli('request_material', {'request_id': 'cli-one', 'description': DESCRIPTION})
        reviewed = self.run_cli('review', tenant='operator')
        self.assertEqual((rated.returncode, wanted.returncode, reviewed.returncode), (0, 0, 0))
        self.assertEqual(json.loads(rated.stdout)['result']['record_type'], feedback.RATING_RESULT_VERSION)
        self.assertEqual(json.loads(wanted.stdout)['result']['record_type'], feedback.REQUEST_RESULT_VERSION)
        self.assertEqual(json.loads(reviewed.stdout)['result']['material_requests']['total'], 1)
        for result in (rated, wanted, reviewed):
            self.assertNotIn(DESCRIPTION.encode(), result.stdout+result.stderr)
            self.assertNotIn(self.fixture.keys['alpha'].key.encode(), result.stdout+result.stderr)
        self.assertEqual(self.run_cli('review').returncode, 2)

    def test_cli_refuses_credential_arguments_and_feedback_echo_before_submission(self):
        key = self.fixture.keys['alpha'].key
        for run in (self.run_cli('request_material', {'request_id': 'safe', 'description': key}),
                    self.run_cli('review', extra=('--token', key))):
            self.assertEqual(run.returncode, 2)
            self.assertNotIn(key.encode(), run.stdout+run.stderr)
            self.assertEqual(json.loads(run.stdout)['effect_commitment'], 'not_attempted')
        self.assertEqual(feedback.feedback_rows(self.runtime)[feedback.REQUEST_KIND], [])


class OAuthFeedbackGuards(unittest.TestCase):
    def setUp(self):
        from tools import test_oauth_http as fixtures
        self.case = fixtures.HttpOAuthIntegration('test_origin_browser_and_admin_guards')
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()

    def staff(self, role):
        from loop_engine.core.service_runtime.account_administration import AccountAdministration
        from loop_engine.core.service_runtime.account_policy import ServiceAccountPolicy, StaffMember
        case = self.case
        administration = AccountAdministration(case.fixture.runtime,
            ServiceAccountPolicy(staff=(StaffMember(role, email='synthetic@example.invalid'),)),
            case.identity_base+'/auth/v1')
        case.app.account_administration = administration
        case.fixture.runtime.set_operator_entitlement('alpha', valid_until=int(time.time())+3600, evidence_ref='synthetic-feedback-seed')
        case.fixture.provisioning.invoke(case.fixture.keys['alpha'].key, 'read', identity='skill.alpha', request_id='staff-feedback-seed')
        principal = case.fixture.runtime.authenticate_key(case.fixture.keys['alpha'].key)
        case.app.feedback.rate(principal, {'identity': 'skill.alpha', 'expected_digest': case.fixture.bindings['skill.alpha'].body_digest,
                                         'value': 'useful', 'note': NOTE})
        case.app.feedback.request_material(principal, {'request_id': 'staff-view-request', 'description': DESCRIPTION})
        return administration

    def test_actual_metadata_oauth_can_submit_but_cannot_read_staff_counts(self):
        case = self.case
        tokens = case.issue()
        headers = case.bearer(tokens['access_token'])
        request = {'record_type': 'service_provisioning_request/v2', 'operation': 'request_material',
                   'request_id': 'oauth-feedback', 'description': DESCRIPTION}
        self.assertEqual(case.client.post('/api/v1/provisioning', headers=headers, json=request).status_code, 200)
        self.assertEqual(case.client.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH, headers=headers).status_code, 403)
        async def check():
            from tools.test_oauth_http import Credentials
            async with _protocol_client(case.base, Credentials(tokens['access_token']), '2026-07-28') as client:
                accepted = await client.call_tool('provisioning_request_material', {key: request[key] for key in ('request_id', 'description')})
                self.assertFalse(accepted.is_error)
                denied = await client.call_tool('feedback_review', {})
                self.assertTrue(denied.is_error)
        asyncio.run(check())
        narrowed = case.issue(scope='usage:read')
        denied = case.client.post('/api/v1/provisioning', headers=case.bearer(narrowed['access_token']), json=request)
        self.assertEqual(denied.status_code, 403)
        case.fixture.runtime.set_tenant_enabled(case.tenant, False)
        self.assertEqual(case.client.post('/api/v1/provisioning', headers=headers, json=request).status_code, 401)

    def test_staff_role_is_rechecked_at_summary_response_boundary(self):
        from loop_engine.core.service_runtime.account_policy import ServiceAccountPolicy, StaffMember
        case = self.case
        administration = self.staff('analytics')
        good = case.client.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH, headers=case.browser_headers)
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.json()['result']['record_type'], feedback.SUMMARY_VERSION)
        self.assertNotIn(NOTE, good.text)
        self.assertNotIn(DESCRIPTION, good.text)
        self.assertEqual(case.client.get(service_http.ADMIN_FEEDBACK_PATH, headers=case.browser_headers).status_code, 403)
        original = service_http._json_bytes
        def demote(value):
            encoded = original(value)
            if value.get('result', {}).get('record_type') == feedback.SUMMARY_VERSION:
                administration.policy = ServiceAccountPolicy(staff=(StaffMember('developer', email='synthetic@example.invalid'),))
            return encoded
        with mock.patch.object(service_http, '_json_bytes', demote):
            denied = case.client.get(service_http.ADMIN_FEEDBACK_SUMMARY_PATH, headers=case.browser_headers)
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn('items_rated', denied.text)

    def test_superadmin_raw_schema_and_demotion_completion_guard(self):
        from loop_engine.core.service_runtime.account_policy import ServiceAccountPolicy, StaffMember
        case = self.case
        administration = self.staff('superadmin')
        good = case.client.get(service_http.ADMIN_FEEDBACK_PATH, headers=case.browser_headers)
        self.assertEqual(good.status_code, 200)
        self.assertEqual(good.json()['result']['record_type'], feedback.STAFF_VIEW_VERSION)
        self.assertIn(NOTE, good.text)
        self.assertIn(DESCRIPTION, good.text)
        original = service_http._json_bytes
        def demote(value):
            encoded = original(value)
            if value.get('result', {}).get('record_type') == feedback.STAFF_VIEW_VERSION:
                administration.policy = ServiceAccountPolicy(staff=(StaffMember('analytics', email='synthetic@example.invalid'),))
            return encoded
        with mock.patch.object(service_http, '_json_bytes', demote):
            denied = case.client.get(service_http.ADMIN_FEEDBACK_PATH, headers=case.browser_headers)
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(NOTE, denied.text)

    def test_known_wrong_usage_count_permission_exposes_analytics_private_notes(self):
        from loop_engine.core.service_runtime.account_policy import USAGE_COUNTS
        case = self.case
        self.staff('analytics')
        original = case.app.feedback._authorize_staff_view
        def wrong(store, principal, staff, administration, permission=None):
            return original(store, principal, staff, administration, USAGE_COUNTS)
        with mock.patch.object(case.app.feedback, '_authorize_staff_view', wrong):
            leaked = case.client.get(service_http.ADMIN_FEEDBACK_PATH, headers=case.browser_headers)
        self.assertEqual(leaked.status_code, 200)
        self.assertIn(NOTE, leaked.text)

    def test_staff_account_oauth_still_has_no_staff_read_authority(self):
        case = self.case
        self.staff('superadmin')
        token = case.issue()['access_token']
        for path in (service_http.ADMIN_FEEDBACK_PATH, service_http.ADMIN_FEEDBACK_SUMMARY_PATH):
            self.assertEqual(case.client.get(path, headers=case.bearer(token)).status_code, 403)


class FeedbackClientClosedProjection(unittest.TestCase):
    def test_raw_staff_view_or_extra_private_fields_cannot_reach_cli_stdout(self):
        safe = feedback.summary({'record_type': feedback.STAFF_VIEW_VERSION,
            'ratings': {'useful': 0, 'not_useful': 0, 'items': []}, 'material_requests': [], 'search_gaps': []})
        outer = {'record_type': 'service_http_result/v1', 'result': safe}
        self.assertEqual(cli.checked_result('review', outer), safe)
        for bad in ({**safe, 'notes': [NOTE]}, {**safe, 'ratings': {**safe['ratings'], 'account': 'private'}},
                    {'record_type': feedback.STAFF_VIEW_VERSION, 'notes': [NOTE]}):
            with self.assertRaises(cli.Refusal):
                cli.checked_result('review', {**outer, 'result': bad})

    def test_escaped_credentials_are_detected_before_submission_and_after_parsing(self):
        credential = 'synthetic"credential\\value'
        fields = {'request_id': 'safe', 'description': credential}
        opener = mock.Mock()
        with self.assertRaisesRegex(cli.Refusal, 'credential_in_feedback'):
            cli.exchange('https://baltor.invalid', 'request_material', fields, credential, 1, opener=opener)
        opener.open.assert_not_called()
        self.assertTrue(cli.contains_credential(cli.parse_json(json.dumps({'nested': [credential]}).encode()), credential))

    def test_cli_transport_failure_never_retries(self):
        opener = mock.Mock()
        opener.open.side_effect = OSError('synthetic private detail that must not escape')
        with self.assertRaisesRegex(cli.Refusal, '^transport_failed$'):
            cli.exchange('https://baltor.invalid', 'request_material', {'request_id': 'one', 'description': 'Wanted'},
                         'synthetic-token', 1, opener=opener)
        self.assertEqual(opener.open.call_count, 1)

    def test_cli_origin_and_input_boundaries(self):
        for value in ('http://baltor.ai', 'https://user:secret@baltor.ai', 'https://baltor.ai/path',
                      'https://baltor.ai?', 'https://baltor.ai#', 'http://127.0.0.1:1234'):
            with self.subTest(value=value), self.assertRaises(cli.Refusal):
                cli.origin(value, False)
        self.assertEqual(cli.origin('http://127.0.0.1:1234', True), 'http://127.0.0.1:1234')
        for raw in (b'{}', b'{"request_id":"one","request_id":"two","description":"wanted"}', b'x'*(cli.INPUT_LIMIT+1)):
            with self.assertRaises(cli.Refusal):
                cli.fields_for('request_material', raw)


if __name__ == '__main__':
    unittest.main()
