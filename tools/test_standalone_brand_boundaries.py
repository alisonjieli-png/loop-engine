"""Public-only brand transport refuses effects before body or authentication.

The loopback application uses existing synthetic identity and mail providers.
No DNS, remote provider, live account or production state is touched.
"""
from contextlib import contextmanager
from dataclasses import replace
import re
from types import SimpleNamespace
import unittest
from unittest import mock

import httpx

from loop_engine.core.service_runtime import brand_pages
from loop_engine.core.service_runtime.brand_profiles import ServiceBrandProfile
from loop_engine.core.service_runtime.account_email_checks import _Provider, _adapter, _settings
from loop_engine.core.service_runtime.request_limits import ServiceRequestLimits, SOCKET_PEER_SOURCE
import test_brand_presentations as brand_fixture
import test_oauth_http as existing


BRANDS = {
    'agentfeeds': ('AgentFeeds', 'https://agentfeeds.example.test'),
    'agentfoundry': ('AgentFoundry', 'https://agentfoundry.example.test'),
    'agentstudios': ('AgentStudios', 'https://agentstudios.example.test'),
    'agentafk': ('AgentAFK', 'https://agentafk.example.test'),
    'meatproxy': ("Don't be a meat proxy", 'https://meatproxy.example.test'),
}
PROFILES = tuple(ServiceBrandProfile(brand, origin, display_name=name)
                 for brand, (name, origin) in BRANDS.items())
PUBLIC_PROFILES = tuple(profile for profile in PROFILES if profile.brand in ('agentafk', 'meatproxy'))
ACCOUNT_PROFILES = tuple(profile for profile in PROFILES if not profile.public_only)


def error_page_problems(renderer, display_name, body):
    """A brand's browser error keeps its own chrome, assets and routes, and names no account on a public-only view."""
    problems = []
    for path in (renderer.ASSET_PREFIX + 'site.css?v=', renderer.ASSET_PREFIX + 'mark.svg?v='):
        if path not in body:
            problems.append('missing own asset ' + path)
    for path in ('/assets/service.css', '/assets/architecture.css', '/assets/baltor-mark.svg'):
        if path in body:
            problems.append('foreign Baltor asset ' + path)
    if 'noindex' not in body or display_name.replace("'", '&#x27;') not in body.replace("'", '&#x27;'):
        problems.append('missing noindex or brand name')
    routes = set(renderer.routes())
    for href in re.findall(r'href="([^"]+)"', body):
        address = href.split('?', 1)[0]
        if not (address in routes or address.startswith(renderer.ASSET_PREFIX)):
            problems.append('link outside this brand ' + href)
    if renderer.__name__.rsplit('.', 1)[-1] in ('agentafk_pages', 'meatproxy_pages') and re.search(r'account|\bkey\b', body, re.I):
        problems.append('public-only error names an account or key')
    return problems


def public_effect_refused(response):
    """A generic auth, parser or provider failure is not the presentation guard."""
    try:
        error = response.json().get('error', {})
    except ValueError:
        return False
    return response.status_code == 404 and isinstance(error, dict) and error.get('code') == 'route_unavailable'


class StandaloneProfileTests(unittest.TestCase):
    def test_closed_brand_names_and_public_only_classification(self):
        for profile in PROFILES:
            self.assertEqual(profile.public_only, profile.brand in ('agentafk', 'meatproxy'))
            self.assertEqual(profile.host, profile.public_base_url.removeprefix('https://'))
            with self.assertRaises(ValueError):
                replace(profile, display_name=profile.display_name + ' other')
        for changes in ({'brand': 'other'}, {'brand': 'agentafk_pages'},
                        {'record_type': 'service_brand_profile/v0'}, {'public_base_url': 'https://brand.example.test/path'},
                        {'public_base_url': 'https://user@brand.example.test'}, {'public_base_url': 'https://brand.example.test/'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(PROFILES[0], **changes)

    def test_renderer_selection_is_closed_not_a_module_import_parameter(self):
        for profile in PROFILES:
            renderer = brand_pages.renderer_for(profile.brand)
            self.assertIsNotNone(renderer.render('/', origin=profile.public_base_url))
        for value in ('', '../web_pages', 'os', 'agentafk_pages', 'agentfeeds.__class__', '__import__'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                brand_pages.renderer_for(value)

    def test_shared_assets_are_exact_paths_never_prefix_or_traversal_grants(self):
        declared = '/assets/afk-review-example.json'
        renderer = SimpleNamespace(SHARED_ASSETS=frozenset((declared,)))
        granted = brand_pages.shared_assets(renderer)
        self.assertIn(declared, granted)
        self.assertNotIn('/assets/', granted)
        self.assertNotIn(declared + '/extra', granted)
        bad = (['/assets/a.js'], {'/assets/a.js'}, frozenset(('/assets/',)),
               frozenset(('/assets/../index.html',)), frozenset(('/assets/./a.js',)),
               frozenset(('/assets//a.js',)), frozenset(('/assets/a.js?x=1',)),
               frozenset(('/assets/a.js#x',)), frozenset(('/assets/%2e%2e/index.html',)),
               frozenset(('/assets\\a.js',)), frozenset(('https://example.com/a.js',)),
               frozenset((None,)))
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                brand_pages.shared_assets(SimpleNamespace(SHARED_ASSETS=value))

    def test_every_brand_error_page_keeps_its_own_assets_routes_and_escapes_text(self):
        from loop_engine.core.service_runtime import web_pages
        for profile in PROFILES:
            renderer = brand_pages.renderer_for(profile.brand)
            with self.subTest(brand=profile.brand):
                body = renderer.error_page(404, message='<script>bad</script>', next_action='<img onerror=bad>', reference='<b>ref</b>').decode()
                self.assertEqual(error_page_problems(renderer, profile.display_name, body), [])
                self.assertIn('Page not found', body)
                for raw, escaped in (('<script>bad', '&lt;script&gt;bad'), ('<img onerror', '&lt;img onerror'), ('<b>ref', '&lt;b&gt;ref')):
                    self.assertNotIn(raw, body)
                    self.assertIn(escaped, body)
                failed = renderer.error_page(503, message='The shared service is busy.', reference='fail-1').decode()
                self.assertIn('could not be completed', failed)
                self.assertEqual(error_page_problems(renderer, profile.display_name, failed), [])
                # The shared fallback that brands without this hook used to serve must fail the same oracle.
                self.assertTrue(error_page_problems(renderer, profile.display_name, web_pages.missing_address_page(profile.display_name).decode()))

    def test_every_brand_page_carries_link_preview_metadata(self):
        def preview_problems(html, display_name):
            head = html.split('</head>', 1)[0]
            tags = dict(re.findall(r'<meta (?:property|name)="(og:[a-z_]+|twitter:card|description)" content="([^"]*)"', head))
            problems = [name for name in ('description', 'og:title', 'og:url', 'og:description', 'og:type', 'og:site_name', 'twitter:card') if not tags.get(name)]
            if tags.get('og:site_name', '').replace('&#x27;', "'") != display_name:
                problems.append('og:site_name')
            return problems
        for profile in PROFILES:
            renderer = brand_pages.renderer_for(profile.brand)
            for path in renderer.routes():
                with self.subTest(brand=profile.brand, path=path):
                    html = renderer.render(path, origin=profile.public_base_url)[0].decode()
                    self.assertEqual(preview_problems(html, profile.display_name), [])
        # Known-wrong: the head served before October 16, 2026 had no og:description, og:site_name or card.
        old = ('<title>Help | AgentFoundry</title><meta name="description" content="Skills."><meta property="og:title" content="Help | AgentFoundry">'
               '<meta property="og:url" content="https://agentfoundry.example.test/help"></head>')
        self.assertEqual(preview_problems(old, 'AgentFoundry'), ['og:description', 'og:type', 'og:site_name', 'twitter:card', 'og:site_name'])

    def test_refusal_checker_detects_wrong_status_or_wrong_guard(self):
        self.assertTrue(public_effect_refused(httpx.Response(404, json={'error': {'code': 'route_unavailable'}})))
        for status, body in ((200, {'result': {}}), (401, {'error': {'code': 'authentication_required'}}),
                             (404, {'error': {'code': 'external_authorization_not_configured'}}),
                             (503, {'error': {'code': 'browser_identity_unavailable'}})):
            self.assertFalse(public_effect_refused(httpx.Response(status, json=body)))


class StandalonePublicHttpTests(unittest.TestCase):
    def setUp(self):
        self.mail = _Provider()
        self.billing = brand_fixture.SharedBillingFixture()
        original = existing.running_http

        @contextmanager
        def branded(fixture, **kwargs):
            factory = kwargs.pop('application_factory')

            def application(config):
                config = replace(config,
                    allowed_hosts=(*config.allowed_hosts, *(profile.host for profile in PROFILES)),
                    allowed_origins=(*config.allowed_origins, *(profile.public_base_url for profile in PROFILES)),
                    brand_profiles=PROFILES,
                    request_limits=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE))
                result = factory(config)
                result.account_email = _adapter(self.mail, _settings(allow_loopback=True))
                result.billing_sessions = self.billing
                self.presentations = result.brand_presentations()
                result.brand_presentations = lambda: self.presentations
                return result

            with original(fixture, application_factory=application, **kwargs) as value:
                yield value

        self.fixture = existing.HttpOAuthIntegration(methodName='runTest')
        with mock.patch.object(existing, 'running_http', branded):
            self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = httpx.Client(base_url=self.fixture.base, trust_env=False, follow_redirects=False, timeout=15)
        self.addCleanup(self.client.close)

    def headers(self, profile):
        return {'Host': profile.host, 'Origin': profile.public_base_url,
                'Authorization': 'Bearer ' + self.fixture.browser_token}

    def test_public_views_share_runtime_but_install_no_email_or_authorization_issuer(self):
        for profile in PUBLIC_PROFILES:
            view = self.presentations[profile.host]
            for name in ('runtime', 'provisioning', 'retention_schedule', 'renewal_schedule', 'request_limiter', 'failure_journal'):
                self.assertIs(getattr(view, name), getattr(self.fixture.app, name), name)
            for name in ('account_email', 'oauth_authorization', 'oauth_http'):
                self.assertIsNone(getattr(view, name), name)
        for profile in ACCOUNT_PROFILES:
            view = self.presentations[profile.host]
            self.assertIsNotNone(view.account_email)
            self.assertIsNotNone(view.oauth_authorization)

    def test_public_pages_assets_and_health_work_without_cross_brand_html_fallback(self):
        for profile in PUBLIC_PROFILES:
            headers = self.headers(profile)
            renderer = brand_pages.renderer_for(profile.brand)
            for path in renderer.routes():
                response = self.client.get(path, headers=headers)
                self.assertEqual(response.status_code, 200, (profile.brand, path, response.text[:200]))
                self.assertIn('text/html', response.headers['content-type'])
                self.assertIn(profile.public_base_url + path, response.text)
            home = self.client.get('/', headers=headers)
            head = self.client.head('/', headers=headers)
            self.assertEqual(head.status_code, 200)
            self.assertEqual(head.content, b'')
            self.assertEqual(head.headers['content-length'], str(len(home.content)))
            self.assertEqual(head.headers['etag'], home.headers['etag'])
            for asset in renderer.ASSETS:
                response = self.client.get(renderer.ASSET_PREFIX + asset, headers=headers)
                self.assertEqual(response.status_code, 200, asset)
            health = self.client.get('/api/v1/health', headers=headers)
            self.assertEqual(health.status_code, 200, health.text)
            self.assertIs(health.json()['result']['alive'], True)
            for path in ('/library', '/login', '/signup', '/oauth/consent', '/auth/confirm', '/assets/service.js', '/assets/agentfeeds/site.css', '/feeds/catalogue.json', '/feeds/sources.json', '/feeds/collections/coding-benchmarks.md'):
                with self.subTest(brand=profile.brand, path=path):
                    self.assertTrue(public_effect_refused(self.client.get(path, headers=headers)))

    def test_public_only_rejects_all_api_identity_and_protocol_discovery(self):
        paths = ('/api/v1/capabilities', '/api/v1/account/identity', '/api/v1/billing/plans', '/api/v1/usage',
                 '/.well-known/oauth-authorization-server', '/.well-known/oauth-protected-resource',
                 '/.well-known/oauth-protected-resource/mcp', '/authorize', '/api/v1/oauth/consent',
                 '/mcp', '/openapi.json', '/api/v1/connect/openapi.json')
        reads_before = self.fixture.stub_identity_reads
        for profile in PUBLIC_PROFILES:
            for path in paths:
                response = self.client.get(path, headers=self.headers(profile))
                self.assertTrue(public_effect_refused(response), (profile.brand, path, response.status_code, response.text[:200]))
        self.assertEqual(self.fixture.stub_identity_reads, reads_before)

    def test_effects_rejected_before_body_authentication_or_provider_call(self):
        paths = ('/', '/api/v1/health', '/api/v1/account/signup', '/api/v1/account/recovery',
                 '/api/v1/account/activate', '/api/v1/billing/checkout', '/api/v1/billing/portal',
                 '/api/v1/billing/webhook', '/api/v1/feeds/profile', '/api/v1/oauth/consent',
                 '/register', '/token', '/revoke', '/mcp', '/api/v1/connect/search', '/api/v1/connect/manifest', '/api/v1/connect/read')
        reads_before = self.fixture.stub_identity_reads
        for profile in PUBLIC_PROFILES:
            view = self.presentations[profile.host]
            with (mock.patch.object(view, '_body', side_effect=AssertionError('body parsed before presentation refusal')) as body,
                  mock.patch.object(view, '_authenticated', side_effect=AssertionError('authenticated before presentation refusal')) as auth):
                for path in paths:
                    response = self.client.post(path, headers=self.headers(profile), content=b'{invalid request body')
                    self.assertTrue(public_effect_refused(response), (profile.brand, path, response.status_code, response.text[:200]))
                body.assert_not_called()
                auth.assert_not_called()
            for path in ('/', '/mcp', '/api/v1/account/signup', '/api/v1/health', '/api/v1/connect/search', '/api/v1/connect/openapi.json'):
                for method in ('OPTIONS', 'PUT', 'DELETE', 'PATCH'):
                    response = self.client.request(method, path, headers=self.headers(profile))
                    self.assertTrue(public_effect_refused(response), (profile.brand, method, path, response.status_code))
        self.assertEqual(self.fixture.stub_identity_reads, reads_before)
        self.assertEqual(self.mail.identity_requests, [])
        self.assertEqual(self.mail.mail_requests, [])
        self.assertEqual(self.billing.created, [])

    def test_exact_host_origin_checks_still_precede_public_route_policy(self):
        profile = PUBLIC_PROFILES[0]
        for headers, status in (({'Host': profile.host, 'Origin': self.fixture.base}, 403),
                                ({'Host': 'unknown.example.test', 'Origin': profile.public_base_url}, 421),
                                ({'Host': profile.host, 'Origin': profile.public_base_url + '.evil.invalid'}, 403)):
            response = self.client.post('/api/v1/account/signup', headers=headers, content=b'{}')
            self.assertEqual(response.status_code, status)
            self.assertNotIn('access-control-allow-origin', response.headers)
        self.assertEqual(self.mail.mail_requests, [])

    def test_account_enabled_brands_and_default_site_keep_qualified_capabilities(self):
        for profile in ACCOUNT_PROFILES:
            response = self.client.get('/api/v1/account/identity', headers=self.headers(profile))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['result']['redirect_url'], profile.public_base_url + '/auth/callback')
            metadata = self.client.get('/.well-known/oauth-authorization-server', headers=self.headers(profile))
            self.assertEqual(metadata.status_code, 200, metadata.text)
            self.assertEqual(metadata.json()['issuer'], profile.public_base_url)
        response = self.fixture.client.get('/api/v1/capabilities')
        self.assertEqual(response.status_code, 200, response.text)

    def test_browser_404_serves_each_brand_error_page_without_reflecting_the_request(self):
        from loop_engine.core.service_runtime import web_pages
        for profile in PROFILES:
            renderer = brand_pages.renderer_for(profile.brand)
            headers = {'Host': profile.host, 'Origin': profile.public_base_url, 'Accept': 'text/html'}
            with self.subTest(brand=profile.brand):
                response = self.client.get('/no-such-brand-page?private-context=must-not-be-reflected', headers=headers)
                self.assertEqual(response.status_code, 404, response.text[:200])
                self.assertIn('text/html', response.headers['content-type'])
                self.assertEqual(error_page_problems(renderer, profile.display_name, response.text), [])
                self.assertNotIn('must-not-be-reflected', response.text)
                self.assertIn("default-src 'none'", response.headers['content-security-policy'])
                for asset in (renderer.ASSET_PREFIX + 'site.css', renderer.ASSET_PREFIX + 'mark.svg'):
                    self.assertEqual(self.client.get(asset, headers=headers).status_code, 200, asset)
        profile = PUBLIC_PROFILES[1]
        renderer = brand_pages.renderer_for(profile.brand)
        with mock.patch.object(renderer, 'error_page', return_value=web_pages.missing_address_page(profile.display_name)):
            wrong = self.client.get('/no-such-brand-page', headers={'Host': profile.host, 'Origin': profile.public_base_url, 'Accept': 'text/html'})
        self.assertEqual(wrong.status_code, 404)
        self.assertTrue(error_page_problems(renderer, profile.display_name, wrong.text), 'the oracle accepted the shared fallback page')

    def test_public_only_pages_cannot_connect_to_the_identity_provider(self):
        def connections(response):
            policy = response.headers['content-security-policy']
            return next(part.split()[1:] for part in policy.split(';') if part.split()[:1] == ['connect-src'])
        for profile in PROFILES:
            with self.subTest(brand=profile.brand):
                page = self.client.get('/', headers={'Host': profile.host, 'Origin': profile.public_base_url})
                self.assertEqual(page.status_code, 200)
                if profile.public_only:
                    self.assertEqual(connections(page), ["'self'"])
                else:
                    self.assertEqual(len(connections(page)), 2, connections(page))
        # Known-wrong: treating a public-only view as account-enabled restores the identity origin.
        profile = PUBLIC_PROFILES[0]
        with mock.patch.object(ServiceBrandProfile, 'public_only', property(lambda self: False)):
            wrong = self.client.get('/', headers={'Host': profile.host, 'Origin': profile.public_base_url})
        self.assertNotEqual(connections(wrong), ["'self'"])

    def test_known_wrong_removed_public_guard_is_detected(self):
        profile = PUBLIC_PROFILES[0]
        before = self.client.get('/api/v1/account/identity', headers=self.headers(profile))
        self.assertTrue(public_effect_refused(before))
        with mock.patch.object(ServiceBrandProfile, 'public_only', property(lambda self: False)):
            wrong = self.client.get('/api/v1/account/identity', headers=self.headers(profile))
        self.assertEqual(wrong.status_code, 200, wrong.text)
        self.assertFalse(public_effect_refused(wrong), 'the control failed to detect removal of the guard')
        self.assertTrue(public_effect_refused(self.client.get('/api/v1/account/identity', headers=self.headers(profile))))


if __name__ == '__main__':
    unittest.main()
