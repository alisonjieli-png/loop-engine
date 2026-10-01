"""Real loopback OAuth integration. Synthetic accounts, local JWKS, no remote provider."""
from __future__ import annotations

import asyncio
import base64
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.core.service_runtime import account_origin
from loop_engine.core.service_runtime.access import ServiceAccessAdministration, ServiceClientAccessPolicy
from loop_engine.core.service_runtime.browser_identity import BrowserIdentityAdapter, BrowserIdentityConfiguration
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http, running_key_set
from loop_engine.core.service_runtime.oauth_authorization import CODE, GRANT, OAuthAuthorizationPolicy, OAuthAuthorizationProvider
from loop_engine.core.service_runtime.observability import ServiceObservabilityPolicy
from loop_engine.core.service_runtime.protocol_checks import _protocol_client
from loop_engine.core.service_runtime.records import ServiceCommitUnknown
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding

EVENTS = []


def safe_error(response):
    try:
        value = response.json().get('error')
        code = value.get('code') if isinstance(value, dict) else value
        return code if isinstance(code, str) and re.fullmatch(r'[a-z_]{1,64}', code) else None
    except (ValueError, AttributeError):
        return None


class Credentials:
    def __init__(self, value):
        self.value = value

    def headers(self, _tenant='alpha'):
        return {'Authorization': 'Bearer ' + self.value}


class HttpOAuthIntegration(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='loopback-oauth-')))
        self.fixture = HttpDomainFixture(folder, operator_access=False)
        identity_base, public_keys = self.stack.enter_context(running_key_set())
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_keys['keys'] = [{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())),
                                'kid': 'synthetic-oauth-key', 'alg': 'RS256', 'use': 'sig'}]
        self.identity_base = identity_base
        self.stub_identity_reads = 0
        self.subject = 'synthetic-oauth-user'
        account_origin.record_origin(self.fixture.runtime, identity_base + '/auth/v1', self.subject, account_origin.SIGNUP_ORIGIN)
        self.browser_token = jwt.encode({'iss': identity_base + '/auth/v1', 'aud': 'authenticated', 'sub': self.subject,
            'exp': int(time.time()) + 1800, 'iat': int(time.time()), 'role': 'authenticated', 'is_anonymous': False},
            key, algorithm='RS256', headers={'kid': 'synthetic-oauth-key'})
        self.credentials_seen = [self.browser_token]
        def user(request):
            self.stub_identity_reads += 1
            return {'id': self.subject, 'role': 'authenticated', 'is_anonymous': False,
                    'email_confirmed_at': '2026-01-01T00:00:00Z', 'email': 'synthetic@example.invalid',
                    'user_metadata': {'role': 'administrator', 'tenant_id': 'alpha'},
                    'app_metadata': {account_origin.ACCOUNT_MARKER: account_origin.ACCOUNT_MARK}}
        browser = BrowserIdentityAdapter(self.fixture.runtime,
            BrowserIdentityConfiguration(identity_base, 'fixture:publishable', 'oauth-fixture',
                registration_enabled=True, allow_network=True, allow_loopback=True),
            lambda _: 'sb_publishable_local_fixture', starter_bindings=(self.fixture.bindings['skill.alpha'],), transport=user)
        access = ServiceAccessAdministration(self.fixture.runtime, ServiceClientAccessPolicy(writes_authorized=True))
        self.callback = 'http://127.0.0.1:43111/oauth/callback'
        def application(config):
            policy = OAuthAuthorizationPolicy(config.public_base_url, config.public_base_url + '/mcp',
                identity_base + '/auth/v1', config.public_base_url + '/oauth/consent',
                native_loopback_paths=('/oauth/callback',), allow_loopback_http=True)
            self.provider = OAuthAuthorizationProvider(self.fixture.runtime, policy)
            return ServiceHttpApplication(self.fixture.runtime, self.fixture.provisioning, config,
                browser_identity=browser, client_access=access, access_administration=access,
                oauth_authorization=self.provider, observability=ServiceObservabilityPolicy(payload_capture='metadata_and_request_body'))
        self.base, self.app = self.stack.enter_context(running_http(self.fixture, application_factory=application))
        self.client = self.stack.enter_context(httpx.Client(base_url=self.base, trust_env=False, follow_redirects=False, timeout=15))
        self.browser_headers = {'Authorization': 'Bearer ' + self.browser_token, 'Origin': self.base}
        activation = self.client.post('/api/v1/account/activate', headers=self.browser_headers,
                                     json={'record_type': 'service_account_activation_request/v1'})
        self.expect(activation, 200, 'synthetic_account_activation')
        self.tenant = activation.json()['result']['tenant_id']
        self.verifier = 'v' * 64
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip('=')
        self.client_id = self.register()['client_id']

    def expect(self, response, status, label):
        row = {'case': self.id().rsplit('.', 1)[-1], 'step': label, 'status': response.status_code,
               'expected_status': status, 'error_code': safe_error(response), 'passed': response.status_code == status}
        EVENTS.append(row)
        if not row['passed']:
            print(json.dumps({'concrete_failure': row}), flush=True)
        self.assertEqual(response.status_code, status, label)
        return response

    def register(self, **changes):
        response = self.client.post('/register', json={'client_name': 'Synthetic QA client',
            'redirect_uris': [self.callback], 'scope': 'provisioning:metadata provisioning:read usage:read', **changes})
        self.expect(response, 201, 'dynamic_registration_default_none')
        data = response.json()
        self.assertEqual(data['token_endpoint_auth_method'], 'none')
        self.assertFalse(data.get('client_secret'), 'a public client received a secret')
        return data

    def authorization_fields(self, **changes):
        return {'client_id': self.client_id, 'response_type': 'code', 'redirect_uri': self.callback,
                'state': 'synthetic-state', 'scope': 'provisioning:metadata', 'code_challenge': self.challenge,
                'code_challenge_method': 'S256', 'resource': self.base + '/mcp', **changes}

    def pending(self, **changes):
        response = self.client.get('/authorize', params=self.authorization_fields(**changes))
        self.expect(response, 302, 'authorize_redirects_to_consent')
        url = urlsplit(response.headers['location'])
        self.assertEqual(url.scheme + '://' + url.netloc + url.path, self.base + '/oauth/consent')
        return parse_qs(url.query)['authorization_id'][0]

    def decision_body(self, pending, decision='approve'):
        return {'record_type': 'service_oauth_consent_decision/v1', 'authorization_id': pending, 'decision': decision}

    def code(self, **changes):
        pending = self.pending(**changes)
        inspected = self.client.get('/api/v1/oauth/consent', params={'authorization_id': pending}, headers=self.browser_headers)
        self.expect(inspected, 200, 'browser_reads_consent')
        response = self.client.post('/api/v1/oauth/consent', headers=self.browser_headers, json=self.decision_body(pending))
        self.expect(response, 200, 'browser_explicit_consent')
        location = response.json()['result']['redirect_uri']
        parsed = urlsplit(location)
        self.assertEqual(parsed.scheme + '://' + parsed.netloc + parsed.path, self.callback)
        values = parse_qs(parsed.query)
        self.assertEqual(values.get('state'), ['synthetic-state'])
        raw = values['code'][0]
        self.credentials_seen.append(raw)
        return raw

    def token_fields(self, code, **changes):
        return {'grant_type': 'authorization_code', 'client_id': self.client_id, 'code': code,
                'code_verifier': self.verifier, 'redirect_uri': self.callback, 'resource': self.base + '/mcp', **changes}

    def issue(self, **changes):
        response = self.client.post('/token', data=self.token_fields(self.code(**changes)))
        self.expect(response, 200, 'code_exchange')
        result = response.json()
        self.credentials_seen.extend([result['access_token'], result['refresh_token']])
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        return result

    def bearer(self, token):
        return {'Authorization': 'Bearer ' + token}

    def rows(self, kind):
        with self.fixture.runtime._catalog.store() as store:
            return store.query(IntelligenceQuery(artifact_kinds=(kind,)))

    def test_discovery_dcr_signed_consent_scoped_api_and_real_mcp(self):
        protected = self.expect(self.client.get('/.well-known/oauth-protected-resource/mcp'), 200, 'resource_discovery').json()
        self.assertEqual(protected['resource'], self.base + '/mcp')
        self.assertEqual(protected['authorization_servers'], [self.base])
        metadata = self.expect(self.client.get('/.well-known/oauth-authorization-server'), 200, 'authorization_discovery').json()
        self.assertEqual(metadata['token_endpoint_auth_methods_supported'], ['none'])
        self.assertEqual(metadata['revocation_endpoint_auth_methods_supported'], ['none'])
        self.assertIn('S256', metadata['code_challenge_methods_supported'])
        self.assertFalse(metadata.get('authorization_response_iss_parameter_supported', False))
        challenge = self.client.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        self.expect(challenge, 401, 'unauthenticated_mcp_challenge')
        self.assertIn('/.well-known/oauth-protected-resource/mcp', challenge.headers.get('www-authenticate', ''))
        generic_identity = self.client.post('/mcp', headers={**self.bearer(self.browser_token), 'Accept': 'application/json, text/event-stream'},
            json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        self.expect(generic_identity, 401, 'browser_session_is_not_an_mcp_access_token')
        tokens = self.issue()
        session = self.expect(self.client.get('/api/v1/session', headers=self.bearer(tokens['access_token'])), 200, 'oauth_session').json()['result']
        self.assertEqual(session['authentication_mode'], 'oauth_access_token')
        self.assertEqual(session['principal']['tenant_id'], self.tenant)
        self.assertNotEqual(self.tenant, 'alpha', 'editable identity metadata selected a different tenant')
        self.assertEqual(session['principal']['scopes'], ['provisioning:metadata'])
        self.assertEqual(session['principal']['entitlement'], 'metadata')
        search = self.client.post('/api/v1/retrieval', headers=self.bearer(tokens['access_token']),
            json={'record_type': 'service_retrieval_request/v2', 'query': 'alpha', 'mode': 'lexical'})
        self.expect(search, 200, 'scoped_api_search')
        self.assertTrue(search.json()['result']['hits'])
        self.expect(self.client.get('/api/v1/usage', headers=self.bearer(tokens['access_token'])), 403, 'ungranted_usage_scope')
        async def mcp():
            async with _protocol_client(self.base, Credentials(tokens['access_token']), 'legacy') as protocol:
                tools = await protocol.list_tools()
                found = await protocol.call_tool('intelligence_search', {'query': 'alpha'})
                denied = await protocol.call_tool('provisioning_read', {'identity': 'skill.alpha', 'request_id': 'scoped-denial'})
                return len(tools.tools), not found.is_error and bool(found.structured_content['result']['hits']), denied.is_error, denied.structured_content['error']['code']
        count, found, denied, denied_code = asyncio.run(mcp())
        self.assertGreater(count, 0)
        self.assertTrue(found)
        self.assertTrue(denied)
        self.assertIn(denied_code, ('insufficient_scope', 'scope_required'))
        EVENTS.append({'case': self.id().rsplit('.', 1)[-1], 'step': 'real_official_mcp_client_scoped_calls', 'passed': found and denied})

    def test_wrong_resource_pkce_redirect_and_code_replay(self):
        raw = self.code()
        for name, change, code in (('wrong_resource', {'resource': 'http://127.0.0.1:1/other'}, 'invalid_target'),
                                  ('wrong_pkce', {'code_verifier': 'w' * 64}, 'invalid_grant'),
                                  ('wrong_redirect', {'redirect_uri': 'http://127.0.0.1:43111/other'}, 'invalid_request')):
            response = self.client.post('/token', data=self.token_fields(raw, **change))
            self.expect(response, 400, name)
            self.assertEqual(safe_error(response), code)
        good = self.expect(self.client.post('/token', data=self.token_fields(raw)), 200, 'same_code_after_failed_checks')
        self.credentials_seen.extend([good.json()['access_token'], good.json()['refresh_token']])
        response = self.client.post('/token', data=self.token_fields(raw))
        self.expect(response, 400, 'code_replay_refused')
        self.assertEqual(safe_error(response), 'invalid_grant')
        self.assertEqual(len(self.rows(GRANT)), 1)

    def test_origin_browser_and_admin_guards(self):
        pending = self.pending()
        body = self.decision_body(pending)
        for label, headers in (('missing_origin', self.bearer(self.browser_token)),
                               ('wrong_origin', {**self.bearer(self.browser_token), 'Origin': 'http://127.0.0.1:5173'}),
                               ('nonbrowser_service_key', {**self.fixture.headers(), 'Origin': self.base})):
            response = self.client.post('/api/v1/oauth/consent', headers=headers, json=body)
            self.expect(response, 403, label)
        self.assertEqual(len(self.rows(CODE)), 0)
        tokens = self.issue()
        for path in ('/api/v1/admin/access', '/api/v1/account/access'):
            self.expect(self.client.get(path, headers=self.bearer(tokens['access_token'])), 403, 'oauth_cannot_access_' + path.rsplit('/', 1)[-1])
        self.expect(self.client.post('/api/v1/oauth/consent', headers={**self.bearer(tokens['access_token']), 'Origin': self.base}, json=body),
                    403, 'oauth_cannot_approve_consent')

    def test_refresh_scope_resource_rotation_and_revocation(self):
        tokens = self.issue(scope='provisioning:metadata provisioning:read')
        refresh = {'grant_type': 'refresh_token', 'client_id': self.client_id, 'refresh_token': tokens['refresh_token'], 'resource': self.base + '/mcp'}
        self.expect(self.client.post('/token', data={**refresh, 'resource': self.base + '/wrong'}), 400, 'refresh_wrong_resource')
        self.expect(self.client.post('/token', data={**refresh, 'scope': 'usage:read'}), 400, 'refresh_cannot_expand_scopes')
        response = self.expect(self.client.post('/token', data={**refresh, 'scope': 'provisioning:metadata'}), 200, 'refresh_downscope')
        next_tokens = response.json()
        self.credentials_seen.extend([next_tokens['access_token'], next_tokens['refresh_token']])
        self.assertEqual(next_tokens['scope'], 'provisioning:metadata')
        self.expect(self.client.get('/api/v1/session', headers=self.bearer(tokens['access_token'])), 401, 'old_access_invalidated')
        self.expect(self.client.post('/token', data=refresh), 400, 'old_refresh_invalidated')
        self.expect(self.client.get('/api/v1/session', headers=self.bearer(next_tokens['access_token'])), 200, 'rotated_access_works')
        self.expect(self.client.post('/revoke', data={'client_id': self.client_id, 'token': next_tokens['access_token']}), 200, 'revoke_delegation')
        self.expect(self.client.get('/api/v1/session', headers=self.bearer(next_tokens['access_token'])), 401, 'revoked_access_refused')
        self.expect(self.client.post('/token', data={**refresh, 'refresh_token': next_tokens['refresh_token']}), 400, 'revoked_refresh_refused')

    def test_denial_bad_client_registration_and_duplicate_resource(self):
        denied = self.client.post('/register', json={'client_name': 'Synthetic', 'redirect_uris': ['https://unapproved.example/callback']})
        self.expect(denied, 400, 'remote_redirect_registration_refused')
        pending = self.pending()
        answer = self.expect(self.client.post('/api/v1/oauth/consent', headers=self.browser_headers,
                                              json=self.decision_body(pending, 'deny')), 200, 'explicit_denial')
        self.assertEqual(parse_qs(urlsplit(answer.json()['result']['redirect_uri']).query)['error'], ['access_denied'])
        self.assertEqual(len(self.rows(CODE)), 0)
        raw = self.code()
        from urllib.parse import urlencode
        duplicate = urlencode(list(self.token_fields(raw).items()) + [('resource', self.base + '/mcp')])
        self.expect(self.client.post('/token', content=duplicate, headers={'Content-Type': 'application/x-www-form-urlencoded'}),
                    400, 'duplicate_resource_refused')

    def test_public_profile_rejects_secret_transfer_without_consuming_code(self):
        raw = self.code()
        fields = self.token_fields(raw)
        self.expect(self.client.post('/token', data={**fields, 'client_secret': 'synthetic-unneeded-secret'}),
                    401, 'public_token_client_secret_refused')
        self.expect(self.client.post('/token', data=fields, headers=self.bearer(self.browser_token)),
                    401, 'public_token_authorization_header_refused')
        tokens = self.expect(self.client.post('/token', data=fields), 200, 'secret_refusals_did_not_consume_code').json()
        self.credentials_seen.extend([tokens['access_token'], tokens['refresh_token']])
        self.expect(self.client.post('/revoke', data={'client_id': self.client_id, 'token': tokens['access_token'],
            'client_secret': 'synthetic-unneeded-secret'}), 401, 'public_revoke_secret_refused')
        self.expect(self.client.get('/api/v1/session', headers=self.bearer(tokens['access_token'])), 200,
                    'refused_secret_transfer_did_not_revoke')

    def test_unknown_commit_preserved_and_credentials_not_journaled(self):
        raw = self.code()
        original = ServiceCatalogBinding.commit
        grant_writes = []
        def uncertain(binding, store, records, guards, removals=()):
            answer = original(binding, store, records, guards, removals)
            if any(row['artifact_kind'] == GRANT for row in records):
                grant_writes.append(1)
                raise ServiceCommitUnknown()
            return answer
        with mock.patch.object(ServiceCatalogBinding, 'commit', uncertain):
            result = self.client.post('/token', data=self.token_fields(raw))
        self.expect(result, 503, 'unknown_commit_not_misreported_as_invalid_grant')
        self.assertEqual(safe_error(result), 'commit_unknown')
        self.assertNotIn('access_token', result.text)
        self.assertNotIn('nothing_recorded', result.text)
        self.assertEqual(grant_writes, [1])
        self.assertEqual(len(self.rows(GRANT)), 1)
        replay = self.client.post('/token', data=self.token_fields(raw))
        self.expect(replay, 400, 'unknown_outcome_code_not_replayed')
        marker = 'SYNTHETIC_OAUTH_BODY_SECRET_DO_NOT_LOG'
        bad = self.client.post('/api/v1/oauth/consent', headers=self.browser_headers,
                              json={**self.decision_body(self.pending()), 'extra': marker})
        self.expect(bad, 400, 'credential_body_refusal')
        journal = json.dumps(self.app.failure_journal.recent(limit=100))
        for secret in [*self.credentials_seen, self.verifier, marker]:
            self.assertFalse(secret in journal, 'OAuth credential or body reached the failure journal')
        with self.fixture.runtime._catalog.store() as store:
            stored = json.dumps(store.query(IntelligenceQuery()))
        for secret in [*self.credentials_seen, self.verifier]:
            self.assertFalse(secret in stored, 'raw OAuth credential reached persistent records')
        EVENTS.append({'case': self.id().rsplit('.', 1)[-1], 'step': 'no_credential_journal_or_plaintext_persistence', 'passed': True})

    def test_disabled_account_invalidates_delegation(self):
        tokens = self.issue()
        self.fixture.runtime.set_tenant_enabled(self.tenant, False)
        self.expect(self.client.get('/api/v1/session', headers=self.bearer(tokens['access_token'])), 401, 'disabled_tenant_access')
        self.expect(self.client.post('/token', data={'grant_type': 'refresh_token', 'client_id': self.client_id,
            'refresh_token': tokens['refresh_token'], 'resource': self.base + '/mcp'}), 400, 'disabled_tenant_refresh')

    def test_oauth_unpaid_account_reads_exact_public_good_without_billing(self):
        from dataclasses import replace
        from loop_engine.core.service_runtime.public_good import PublicGoodGrant
        binding = self.fixture.provisioning
        view = replace(binding.current_view(), item_versions={'skill.alpha':'a'*64})
        binding.install_view(view)
        selected = self.fixture.bindings['skill.alpha']
        grant = PublicGoodGrant(selected, 'a'*64, view.qualification_resolver.resolve(selected).approval_ref,
            'synthetic-rights', (4,), 'Synthetic learning check', int(time.time())+3600)
        binding.public_good.configure(view, (grant,))
        token = self.issue(scope='provisioning:metadata provisioning:read')['access_token']
        response = self.client.post('/api/v1/download', headers=self.bearer(token), json={
            'record_type':'service_provisioning_request/v2', 'operation':'read', 'identity':'skill.alpha',
            'expected_digest':selected.body_digest, 'request_id':'oauth-free-download'})
        self.expect(response, 200, 'oauth_unpaid_public_good_download')
        self.assertEqual(hashlib.sha256(response.content).hexdigest(), selected.body_digest)
        principal = self.provider.resolve_access(token).principal
        self.assertEqual(principal.entitlement, 'metadata')
        self.assertEqual(self.fixture.runtime.usage_for(principal)['records'], 0)


class OAuthImportBoundary(unittest.TestCase):
    def test_sdk_error_adapter_preserves_type_fields_and_python_tracebacks(self):
        from contextlib import contextmanager
        from dataclasses import FrozenInstanceError
        from loop_engine.core.service_runtime import oauth_authorization as adapted
        from mcp.server.auth import provider as sdk
        @contextmanager
        def scope():
            yield
        for name in ('AuthorizeError','RegistrationError','TokenError'):
            cls, base = getattr(adapted,name), getattr(sdk,name)
            error = cls('invalid_request','Synthetic refusal')
            self.assertIsInstance(error,base)
            error.__traceback__ = None
            with self.assertRaises(FrozenInstanceError):
                error.error = 'access_denied'
            with self.assertRaises(base) as captured:
                with scope():
                    raise error
            self.assertIs(captured.exception,error)
            with self.assertRaises(FrozenInstanceError):
                base('invalid_request','Known wrong frozen error').__traceback__ = None

    def test_authorization_and_inbound_adapter_have_no_outbound_client_imports(self):
        import ast
        from loop_engine.core.service_runtime import oauth_authorization, oauth_http
        for module in (oauth_authorization, oauth_http):
            tree = ast.parse(Path(module.__file__).read_text())
            for node in ast.walk(tree):
                names = ([node.module] if isinstance(node, ast.ImportFrom)
                         else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
                for name in names:
                    if name and name.split('.')[0] in {'urllib','http','httpx','requests','aiohttp','socket'}:
                        self.assertEqual(name, 'urllib.parse', module.__name__)



if __name__ == '__main__':
    unittest.main()
