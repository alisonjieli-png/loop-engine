"""Independent brand rendering, exact shared-source reuse and refusal controls."""
from dataclasses import replace
from hashlib import sha256
from html.parser import HTMLParser
import re
import unittest

from loop_engine.core.service_runtime import agentfeeds_pages as pages, feed_profiles
from loop_engine.core.service_runtime.web_pages import read_packaged_asset


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.links.append(attrs.get('href', ''))


def brand_problems(body):
    parser = Links()
    parser.feed(body)
    return [href for href in parser.links if href.startswith(('https://baltor.ai', '/gallery', '/overnight', '/library', '/harness-files'))]


class AgentFeedsPagesTests(unittest.TestCase):
    def test_all_routes_and_resources_render_without_cross_marketing(self):
        for path in pages.routes():
            with self.subTest(path=path):
                body, media = pages.render(path)
                self.assertEqual(media, 'text/html')
                self.assertIn(b'AgentFeeds', body)
                self.assertIn(('https://agentfeeds.si' + path).encode(), body)
                if path not in ('/privacy', '/terms'):
                    self.assertEqual(brand_problems(body.decode()), [])
        for name, media in pages.ASSETS.items():
            self.assertEqual(pages.render(pages.ASSET_PREFIX + name)[1], media)

    def test_brand_scan_rejects_real_wrong_navigation(self):
        html = pages.render('/')[0].decode()
        self.assertEqual(brand_problems(html), [])
        self.assertTrue(brand_problems(html.replace('</nav>', '<a href="https://baltor.ai/">Home</a></nav>', 1)))
        self.assertTrue(brand_problems(html + '<a href="/overnight">Other offering</a>'))

    def test_unknown_paths_and_asset_traversal_are_not_served(self):
        for path in ('/collections/unknown', '/assets/agentfeeds/../index.html', '/assets/agentfeeds/secret', '/admin', '/not-a-page'):
            self.assertIsNone(pages.render(path))

    def test_origin_is_a_plain_secure_origin_not_injected_markup_or_return_url(self):
        for origin in ('http://agentfeeds.si', 'https://user@agentfeeds.si', 'https://agentfeeds.si/path', 'https://agentfeeds.si?x=1', 'https://agentfeeds.si#x', 'https://agentfeeds.si:444'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                pages.render('/', origin=origin)

    def test_inventory_counts_follow_existing_directory_not_a_marketing_constant(self):
        data = feed_profiles.current_directory()
        smaller = replace(data, collections=data.collections[:3])
        html = pages.render('/', directory=smaller)[0].decode()
        self.assertIn('<strong>3</strong><span>decision collections', html)
        self.assertIn(f'<strong>{len(data.sources)}</strong><span>registered sources', html)
        self.assertIn('01 / 3', html)

    def test_collection_output_uses_existing_sources_and_brand_local_feed_links(self):
        data = feed_profiles.current_directory()
        item = data.collections[0]
        html = pages.render('/collections/' + item.id)[0].decode()
        self.assertIn(item.decision_question, html)
        for suffix in ('md', 'json', 'rss'):
            self.assertIn('https://agentfeeds.si/feeds/collections/' + item.id + '.' + suffix, html)
        self.assertIn('rel="alternate" type="application/rss+xml"', html)
        self.assertNotIn('rel="alternate"', pages.render('/login')[0].decode())
        self.assertIn('directory', pages.render('/help')[0].decode())

    def test_builder_uses_real_contract_fields_and_does_not_promise_a_hosted_feed(self):
        html = pages.render('/build')[0].decode()
        self.assertIn(feed_profiles.current_directory().digest, html)
        for field in ('agent_label', 'collection_ids', 'source_ids', 'excluded_source_ids', 'report_format', 'requested_poll_interval_minutes'):
            self.assertIn('name="' + field + '"', html)
        self.assertIn('No hosted feed or schedule is created', html)
        self.assertIn('/assets/feed-profile.js?v=', html)
        self.assertNotIn('type="password"', html)

    def test_approved_legal_articles_are_reused_exactly(self):
        source = read_packaged_asset('index.html').decode()
        for path, article in (('/privacy', 'privacy-notice'), ('/terms', 'terms-of-service')):
            expected = re.search(r'<article id="' + article + r'"[\s\S]*?</article>', source).group()
            self.assertIn(expected, pages.render(path)[0].decode())

    def test_brand_assets_are_content_versioned(self):
        html = pages.render('/')[0].decode()
        for name in ('site.css', 'site.js', 'mark.svg'):
            body, _ = pages.render(pages.ASSET_PREFIX + name)
            self.assertIn(pages.ASSET_PREFIX + name + '?v=' + sha256(body).hexdigest(), html)

    def test_account_pages_have_no_cross_brand_or_payment_action(self):
        for path in pages.ACCOUNT_ROUTES:
            html = pages.render(path)[0].decode()
            self.assertIn('/assets/supabase-client.js?v=', html)
            self.assertNotIn('billing/checkout', html)
            self.assertNotIn('/assets/service.js', html)
            self.assertIn('<meta name="robots" content="noindex">', html)
        consent = pages.render('/oauth/consent')[0].decode()
        for identity in ('oauth-client-name', 'oauth-client-destination', 'oauth-consent-scopes', 'oauth-approve', 'oauth-deny'):
            self.assertIn('id="' + identity + '"', consent)

    def test_brand_discovery_files_exclude_accounts_and_baltor_marketing(self):
        sitemap = pages.render('/sitemap.xml')[0].decode()
        self.assertIn('https://agentfeeds.si/collections/coding-benchmarks', sitemap)
        self.assertNotIn('/account', sitemap)
        for path in pages.SITE_FILES:
            body = pages.render(path)[0].decode()
            self.assertIn('agentfeeds.si', body)
            self.assertNotIn('baltor.ai', body)


if __name__ == '__main__':
    unittest.main()
