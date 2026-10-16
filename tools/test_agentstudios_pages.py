"""Independent Studios rendering and exact reuse of catalogue/account material."""
from hashlib import sha256
from html.parser import HTMLParser
from importlib.resources import files
import json
import re
import unittest

from loop_engine.core.service_runtime import agentstudios_pages as pages, gallery_records
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


class AgentStudiosPagesTests(unittest.TestCase):
    def test_every_route_has_independent_shell_and_same_origin(self):
        for path in pages.routes():
            with self.subTest(path=path):
                body, media = pages.render(path)
                self.assertEqual(media, 'text/html')
                html = body.decode()
                self.assertIn('AgentStudios', html)
                self.assertIn('href="https://agentstudios.si' + path + '"', html)
                self.assertEqual(html.count('<h1'), 1)
                if path not in ('/privacy', '/terms'):
                    self.assertEqual(navigation_problems(html), [])

    def test_navigation_guard_detects_cross_brand_ui(self):
        self.assertEqual(navigation_problems(pages.render('/')[0].decode()), [])
        self.assertTrue(navigation_problems('<a href="https://baltor.ai/library">Library</a>'))
        self.assertTrue(navigation_problems('<a href="/overnight">Other product</a>'))

    def test_unknown_and_traversal_paths_refuse(self):
        for path in ('/examples/unknown', '/assets/agentstudios/../index.html', '/assets/agentstudios/secret', '/gallery', '/admin'):
            self.assertIsNone(pages.render(path))

    def test_origin_refusals_and_explicit_loopback(self):
        for origin in ('http://agentstudios.si', 'https://user@agentstudios.si', 'https://agentstudios.si/path',
                       'https://agentstudios.si?x=1', 'https://agentstudios.si#x', 'https://agentstudios.si/'):
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
        self.assertIn('agentstudios.identity-session', script)
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
        origin = 'https://www.agentstudios.si'
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
            self.assertIn('agentstudios.si', body)
            self.assertNotIn('baltor.ai', body)

    def test_public_library_script_uses_existing_contract_and_safe_text(self):
        script = pages.render(pages.ASSET_PREFIX + 'site.js')[0].decode()
        self.assertIn('/api/v1/public-good?', script)
        self.assertIn('public_good_collection/v1', script)
        self.assertIn('service_health/v2', script)
        self.assertNotIn('innerHTML', script)
        self.assertNotIn('localStorage', script)
        self.assertNotIn("page_size:", script)


class AgentStudiosCreativeTests(unittest.TestCase):
    def test_six_lenses_are_metadata_hints_and_all_examples_keep_source(self):
        self.assertEqual({key for key, _ in pages.LENSES}, {'images','audio','video','3d','games','procedural'})
        for item in pages.public_items():
            self.assertTrue(set(pages.media_lenses(item)) <= {key for key, _ in pages.LENSES})
        html = pages.render('/library')[0].decode()
        self.assertIn('do not claim a complete stock library or a hosted editor', html)
        self.assertIn('name="media"', html)
        self.assertIn('data-public-search', html)

    def test_original_media_use_existing_checked_sources_not_new_inventory(self):
        from loop_engine.core.service_runtime import gallery_media
        expected = [item for item in gallery_media.public_previews() if item['source_kind'] == 'website_example']
        self.assertEqual(list(pages.original_media()), expected)
        self.assertTrue(expected)
        for item in expected:
            body = pages.render('/media/' + item['id'])[0].decode()
            self.assertIn(item['url'], body)
            self.assertIn(item['source_page'], body)
            self.assertIn(item['sha256'], body)
            self.assertIn(item['source_version'], body)
            self.assertIn('controls preload="none"', body)
            self.assertIn('not an item from the account-authorized library', body)
            self.assertNotIn('autoplay', body)
            self.assertIn(item['url'], pages.SHARED_ASSETS)
            self.assertIn(item['source_page'], pages.SHARED_ASSETS)
        self.assertEqual(len({item['source_page'] for item in expected}), 1)

    def test_error_escape_and_brand_isolation(self):
        body = pages.error_page(404, message='<script>bad</script>', next_action='<img onerror=bad>', reference='<b>ref</b>').decode()
        self.assertIn('&lt;script&gt;', body)
        self.assertNotIn('<script>', body)
        self.assertIn('&lt;img', body)
        self.assertNotIn('/assets/service.css', body)
        self.assertNotIn('Baltor', body)
        self.assertIn('/assets/agentstudios/site.css?v=', body)
        self.assertIn('noindex', body)
        self.assertIn('Page not found', body)
        self.assertIn('could not be completed', pages.error_page(503).decode())

    def test_phone_hero_keeps_its_words_apart_when_the_break_is_hidden(self):
        # site.css hides the hero <br> at phone width, so the words either side need their own space.
        css = files('loop_engine.core.service_runtime').joinpath('web_assets', 'agentstudios', 'site.css').read_text()
        self.assertIn('.hero h1 br{display:none}', css)
        def phone_heading(markup):
            return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', markup.replace('<br>', ''))).strip()
        heading = re.search(r'<h1>(.*?)</h1>', pages.render('/')[0].decode()).group(1)
        self.assertEqual(phone_heading(heading), 'Working files for creative projects.')
        # Known-wrong: the markup served before October 16, 2026 joins two words on a phone.
        self.assertEqual(phone_heading('Working files for<br><em>creative projects.</em>'), 'Working files forcreative projects.')

    def test_no_trademark_or_unqualified_studio_claims(self):
        home = pages.render('/')[0].decode()
        self.assertNotIn('®', home)
        self.assertNotIn('AgentMedia', home)
        self.assertNotIn('AgentFoundry', home)
        self.assertIn('Editing, generation and rendering happen in the tools you choose', home)
        self.assertIn('Operated by Baltor.AI', home)
        script = pages.render(pages.ASSET_PREFIX + 'site.js')[0].decode()
        self.assertIn('filters.elements.media', script)
        self.assertNotIn('filters.elements.kind', script)


if __name__ == '__main__':
    unittest.main()

