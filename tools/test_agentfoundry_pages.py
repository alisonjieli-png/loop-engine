"""Independent Foundry rendering and exact reuse of catalogue/account material."""
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
import unittest

from loop_engine.core.service_runtime import agentfoundry_pages as pages, gallery_records
from loop_engine.core.service_runtime.web_pages import read_packaged_asset, WEB_ASSETS


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))


def navigation_problems(html):
    parser = Links()
    parser.feed(html)
    return [href for href in parser.links if href.startswith(('https://baltor.ai', 'https://agentfeeds.si', '/gallery', '/overnight', '/feeds'))]


class AgentFoundryPagesTests(unittest.TestCase):
    def test_escape_closes_the_phone_menu_and_returns_focus(self):
        # The other brands already close their menu on Escape; this one did not before October 16, 2026.
        script = pages.render(pages.ASSET_PREFIX + 'site.js')[0].decode()
        for fragment in ("event.key !== 'Escape'", "button.setAttribute('aria-expanded', 'false')", "classList.remove('open')", 'button.focus()'):
            self.assertIn(fragment, script)

    def test_every_route_has_independent_shell_and_same_origin(self):
        for path in pages.routes():
            with self.subTest(path=path):
                body, media = pages.render(path)
                self.assertEqual(media, 'text/html')
                html = body.decode()
                self.assertIn('AgentFoundry', html)
                self.assertIn('href="https://getagentfoundry.si' + path + '"', html)
                self.assertEqual(html.count('<h1'), 1)
                if path not in ('/privacy', '/terms'):
                    self.assertEqual(navigation_problems(html), [])

    def test_navigation_guard_detects_cross_brand_ui(self):
        self.assertEqual(navigation_problems(pages.render('/')[0].decode()), [])
        self.assertTrue(navigation_problems('<a href="https://baltor.ai/library">Library</a>'))
        self.assertTrue(navigation_problems('<a href="/overnight">Other product</a>'))

    def test_unknown_and_traversal_paths_refuse(self):
        for path in ('/examples/unknown', '/assets/agentfoundry/../index.html', '/assets/agentfoundry/secret', '/gallery', '/admin'):
            self.assertIsNone(pages.render(path))

    def test_origin_refusals_and_explicit_loopback(self):
        for origin in ('http://getagentfoundry.si', 'https://user@getagentfoundry.si', 'https://getagentfoundry.si/path',
                       'https://getagentfoundry.si?x=1', 'https://getagentfoundry.si#x', 'https://getagentfoundry.si/'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                pages.render('/', origin=origin)
        self.assertIn(b'http://127.0.0.1:8888/connect', pages.render('/connect', origin='http://127.0.0.1:8888', allow_loopback=True)[0])

    def test_real_gallery_metadata_is_used_without_private_items(self):
        items = pages.public_items()
        expected = [item for item in gallery_records.record()['items'] if item['tier'] in gallery_records.PUBLIC_TIERS]
        self.assertEqual(list(items), expected)
        html = pages.render('/examples')[0].decode()
        for item in items:
            self.assertIn('/examples/' + item['slug'], html)
        item = items[0]
        detail = pages.render('/examples/' + item['slug'])[0].decode()
        for field in ('identity', 'version', 'licence'):
            self.assertIn(item[field], detail)
        for entry in item['files']:
            self.assertIn(entry['path'], detail)

    def test_shared_assets_are_exact_public_inventory(self):
        self.assertTrue(set(gallery_records.preview_assets()) <= pages.SHARED_ASSETS)
        for name in pages.CLIENT_FILES:
            self.assertIn('/assets/baltor-library/' + name, pages.SHARED_ASSETS)
        self.assertNotIn('/assets/index.html', pages.SHARED_ASSETS)
        self.assertNotIn('/assets/service.js', pages.SHARED_ASSETS)
        self.assertNotIn('/assets/gallery/../secret', pages.SHARED_ASSETS)
        for path in pages.SHARED_ASSETS:
            with self.subTest(path=path):
                self.assertIn(path, WEB_ASSETS)
                self.assertTrue(read_packaged_asset(WEB_ASSETS[path][0]))

    def test_nonlegal_links_stay_in_actual_routes_and_shared_assets(self):
        known = set(pages.routes()) | set(pages.SITE_FILES) | set(pages.SHARED_ASSETS) | {'/api/v1/public-good'}
        for path in pages.routes():
            if path in ('/privacy', '/terms'):
                continue
            parser = Links()
            parser.feed(pages.render(path)[0].decode())
            for href in parser.links:
                if not href.startswith('#'):
                    self.assertIn(href.split('?', 1)[0].split('#', 1)[0], known, (path, href))

    def test_account_protocol_is_existing_adapter_not_another_authority(self):
        script = pages.render(pages.ASSET_PREFIX + 'account.js')[0].decode()
        self.assertIn('agentfoundry.identity-session', script)
        self.assertNotIn('AgentFeeds', script)
        self.assertIn("record_type:signup?'service_account_signup_request/v2'", script)
        self.assertNotIn('billing/checkout', script)
        for path in pages.ACCOUNT_ROUTES:
            html = pages.render(path)[0].decode()
            self.assertIn('/assets/supabase-client.js?v=', html)
            self.assertIn('name="robots" content="noindex"', html)
            self.assertNotIn('reading profiles', html.lower())

    def test_legal_articles_reuse_approved_bytes(self):
        source = read_packaged_asset('index.html').decode()
        for path, article in (('/privacy', 'privacy-notice'), ('/terms', 'terms-of-service')):
            expected = re.search(r'<article id="' + article + r'"[\s\S]*?</article>', source).group()
            self.assertIn(expected, pages.render(path)[0].decode())

    def test_asset_versions_match_bytes(self):
        html = pages.render('/')[0].decode()
        for name in ('site.css', 'site.js', 'mark.svg'):
            body, media = pages.render(pages.ASSET_PREFIX + name)
            self.assertEqual(media, pages.ASSETS[name])
            self.assertIn(pages.ASSET_PREFIX + name + '?v=' + sha256(body).hexdigest(), html)

    def test_client_configuration_uses_selected_origin_and_narrow_effects(self):
        origin = 'https://www.getagentfoundry.si'
        body, media = pages.render('/client.example.json', origin=origin)
        self.assertEqual(media, 'application/json')
        value = json.loads(body)
        self.assertEqual(value['record_type'], 'baltor_library_client_configuration/v2')
        self.assertEqual(value['origin'], origin)
        self.assertEqual(value['authority_effects'], ['reads_fs'])
        self.assertNotIn('token', value)
        self.assertIn(origin + '/mcp', pages.render('/connect', origin=origin)[0].decode())

    def test_discovery_files_are_local_and_exclude_account_pages(self):
        sitemap = pages.render('/sitemap.xml')[0].decode()
        self.assertIn('/examples/' + pages.public_items()[0]['slug'], sitemap)
        self.assertNotIn('/account', sitemap)
        for path in pages.SITE_FILES:
            body = pages.render(path)[0].decode()
            self.assertIn('getagentfoundry.si', body)
            self.assertNotIn('baltor.ai', body)

    def test_public_library_script_uses_existing_contract_and_safe_text(self):
        script = pages.render(pages.ASSET_PREFIX + 'site.js')[0].decode()
        self.assertIn('/api/v1/public-good?', script)
        self.assertIn('public_good_collection/v1', script)
        self.assertIn('service_health/v2', script)
        self.assertNotIn('innerHTML', script)
        self.assertNotIn('localStorage', script)
        self.assertNotIn("page_size:", script)


if __name__ == '__main__':
    unittest.main()
