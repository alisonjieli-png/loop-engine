"""Campaign rendering, live destination contracts and negative controls."""
from hashlib import sha256
from html.parser import HTMLParser
import re
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from loop_engine.core.service_runtime import agentfeeds_pages, feed_profiles, meatproxy_pages as pages
from loop_engine.core.service_runtime.web_pages import read_packaged_asset


class Elements(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.elements = []
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def broken_campaign_links(html):
    problems = []
    for tag, attrs in Elements(html).elements:
        href = attrs.get('href', '')
        if tag != 'a' or href.startswith('#'):
            continue
        parsed = urlsplit(href)
        if parsed.netloc:
            if parsed.scheme != 'https' or parsed.netloc != 'agentfeeds.si':
                problems.append(href)
            elif parsed.path not in agentfeeds_pages.routes():
                problems.append(href)
        elif parsed.path not in pages.ROUTES:
            problems.append(href)
    return problems


class MeatProxyPagesTests(unittest.TestCase):
    def test_all_exact_routes_render_with_current_origin(self):
        self.assertEqual(pages.routes(), pages.ROUTES)
        for path in pages.routes():
            for origin in (pages.ORIGIN, 'https://www.dontbeameatproxy.si'):
                with self.subTest(path=path, origin=origin):
                    body, media = pages.render(path, origin=origin)
                    self.assertEqual(media, 'text/html')
                    self.assertIn(('rel="canonical" href="' + origin + path + '"').encode(), body)
                    self.assertIn(b'An AgentFeeds campaign', body)
                    self.assertIn(b'Operated by Baltor.AI', body)

    def test_campaign_links_resolve_to_owned_pages_or_real_agentfeeds_routes(self):
        for path in ('/', '/how-it-works', '/questions'):
            self.assertEqual(broken_campaign_links(pages.render(path)[0].decode()), [], path)

    def test_wrong_campaign_links_are_detected(self):
        html = pages.render('/')[0].decode()
        self.assertTrue(broken_campaign_links(html.replace('https://agentfeeds.si/build', 'https://baltor.ai/build')))
        self.assertTrue(broken_campaign_links(html.replace('/how-it-works', '/not-a-real-page')))
        self.assertTrue(broken_campaign_links(html + '<a href="https://agentfeeds.si/fake">Wrong</a>'))

    def test_unknown_assets_and_path_traversal_refused(self):
        for path in ('/signup', '/account', '/library', '/build', '/unknown', '/assets/meatproxy/../index.html', '/assets/meatproxy/missing.js', '/assets/meatproxy/site.css/extra'):
            with self.subTest(path=path):
                self.assertIsNone(pages.render(path))

    def test_invalid_origins_refused_before_asset_or_page_render(self):
        for origin in ('http://dontbeameatproxy.si', 'https://user@dontbeameatproxy.si', 'https://dontbeameatproxy.si/', 'https://dontbeameatproxy.si/path', 'https://dontbeameatproxy.si?x=1', 'https://dontbeameatproxy.si#x', 'https://dontbeameatproxy.si:444', 'https://dontbeameatproxy.si\\bad', 'https://dontbeameatproxy.si bad'):
            for path in ('/', pages.ASSET_PREFIX + 'site.css'):
                with self.subTest(origin=origin, path=path), self.assertRaises(ValueError):
                    pages.render(path, origin=origin)

    def test_http_loopback_is_explicitly_opt_in(self):
        with self.assertRaises(ValueError):
            pages.render('/', origin='http://127.0.0.1:8800')
        self.assertEqual(pages.render('/', origin='http://127.0.0.1:8800', allow_loopback=True)[1], 'text/html')
        with self.assertRaises(ValueError):
            pages.render('/', origin='http://example.com', allow_loopback=True)

    def test_campaign_assets_are_versioned_and_correctly_typed(self):
        html = pages.render('/')[0].decode()
        for name, media in pages.ASSETS.items():
            body, actual_media = pages.render(pages.ASSET_PREFIX + name)
            self.assertEqual(media, actual_media)
            self.assertGreater(len(body), 0)
            self.assertIn(pages.ASSET_PREFIX + name + '?v=' + sha256(body).hexdigest(), html)
        self.assertEqual(pages.SHARED_ASSETS, frozenset())

    def test_choice_ids_are_current_real_collection_ids(self):
        directory = feed_profiles.current_directory()
        ids = {item.id for item in directory.collections}
        self.assertTrue(set(pages.COLLECTION_IDS) <= ids)
        html = pages.render('/')[0].decode()
        options = [attrs['value'] for tag, attrs in Elements(html).elements if tag == 'option']
        self.assertEqual(options, list(pages.COLLECTION_IDS))
        for key in pages.COLLECTION_IDS:
            self.assertIn('https://agentfeeds.si/feeds/collections/' + key + '.md', pages._instruction(key))

    def test_initial_instruction_and_actions_agree(self):
        html = pages.render('/')[0].decode()
        self.assertIn('https://agentfeeds.si/feeds/collections/coding-benchmarks.md', html)
        self.assertIn('href="https://agentfeeds.si/build?collection=coding-benchmarks"', html)
        self.assertIn('href="https://agentfeeds.si/collections/coding-benchmarks"', html)
        self.assertIn('Ask before taking actions.', html)

    def test_real_availability_is_disclosed_not_hosted_execution(self):
        home = pages.render('/')[0].decode()
        self.assertIn('not a live personalized news stream', home)
        self.assertIn('does not start a hosted schedule', home)
        self.assertIn('need no account', home)
        self.assertNotIn('token savings', home.lower())
        questions = pages.render('/questions')[0].decode()
        self.assertIn('December 31, 2026', questions)
        self.assertIn('$9 a month', questions)
        self.assertNotIn('per month', questions)  # Price wording matches baltor.ai and AgentFeeds.
        self.assertIn('explicit opt-in', questions)

    def test_approved_legal_articles_preserved_exactly(self):
        source = read_packaged_asset('index.html').decode()
        for path, article in (('/privacy', 'privacy-notice'), ('/terms', 'terms-of-service')):
            expected = re.search(r'<article id="' + article + r'"[\s\S]*?</article>', source).group()
            self.assertIn(expected, pages.render(path)[0].decode())

    def test_crawler_files_are_campaign_specific(self):
        sitemap, media = pages.render('/sitemap.xml')
        self.assertEqual(media, 'application/xml')
        urls = [item.text for item in ET.fromstring(sitemap).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        self.assertEqual(urls, [pages.ORIGIN + path for path in pages.ROUTES])
        self.assertIn((pages.ORIGIN + '/sitemap.xml').encode(), pages.render('/robots.txt')[0])
        llms = pages.render('/llms.txt')[0].decode()
        self.assertIn('An AgentFeeds acquisition campaign', llms)
        self.assertIn('https://agentfeeds.si/build', llms)
        self.assertNotIn('/account', sitemap.decode())

    def test_no_accounts_trackers_third_party_scripts_or_storage(self):
        for path in pages.ROUTES:
            elements = Elements(pages.render(path)[0].decode()).elements
            scripts = [attrs.get('src') for tag, attrs in elements if tag == 'script']
            self.assertEqual(len(scripts), 1)
            self.assertTrue(scripts[0].startswith(pages.ASSET_PREFIX))
            self.assertFalse(any(tag == 'form' for tag, _ in elements))
        script = pages.render(pages.ASSET_PREFIX + 'site.js')[0].decode()
        for forbidden in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'document.cookie', 'sendBeacon', 'innerHTML'):
            self.assertNotIn(forbidden, script)

    def test_accessible_navigation_and_copy_fallback_are_present(self):
        html = pages.render('/')[0].decode()
        for fragment in ('class="skip-link"', 'aria-controls="site-nav"', 'aria-expanded="false"', 'id="main" tabindex="-1"', 'for="decision"', 'for="reading-instruction"', 'role="status" aria-live="polite"', '<noscript>'):
            self.assertIn(fragment, html)
        script = pages.render(pages.ASSET_PREFIX + 'site.js')[0].decode()
        self.assertIn('instruction.select()', script)
        self.assertIn("event.key === 'Escape'", script)
        css = pages.render(pages.ASSET_PREFIX + 'site.css')[0].decode()
        self.assertIn('prefers-reduced-motion:reduce', css)

    def test_renderer_uses_no_network_or_customer_mutation(self):
        with patch('socket.create_connection', side_effect=AssertionError('unexpected network')):
            for path in (*pages.ROUTES, *pages.SITE_FILES):
                self.assertIsNotNone(pages.render(path))


if __name__ == '__main__':
    unittest.main()
