"""AgentAFK presentation reuses qualified tools without implying dispatch."""
from hashlib import sha256
from html.parser import HTMLParser
import re
import unittest

from loop_engine.core.service_runtime import agentafk_pages as pages
from loop_engine.core.service_runtime.web_pages import WEB_ASSETS, read_packaged_asset


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.labels = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
        if 'id' in attrs:
            self.ids.append(attrs['id'])


class AgentAFKPagesTests(unittest.TestCase):
    def test_all_public_pages_render_as_independent_brand(self):
        for path in pages.routes():
            with self.subTest(path=path):
                body, media = pages.render(path)
                self.assertEqual(media, 'text/html')
                html = body.decode()
                self.assertIn('AgentAFK', html)
                self.assertIn('https://agentafk.si' + path, html)
                self.assertEqual(html.count('<h1'), 1)
                self.assertIn('Skip to content', html)
                self.assertNotIn('/assets/service.js', html)
                self.assertNotIn('billing/checkout', html)
                parser = Links()
                parser.feed(html)
                if path not in ('/privacy', '/terms'):
                    self.assertEqual(len(parser.ids), len(set(parser.ids)))
                if path not in ('/privacy', '/terms'):
                    self.assertFalse(any(href.startswith(('https://baltor.ai', 'https://agentfeeds.si', 'https://getagentfoundry.si')) for href in parser.links))

    def test_public_navigation_resolves_to_declared_local_routes(self):
        for path in pages.routes():
            if path in ('/privacy', '/terms'):
                continue  # Approved shared legal links are deliberately unchanged.
            parser = Links()
            parser.feed(pages.render(path)[0].decode())
            for href in parser.links:
                target = href.split('#', 1)[0]
                if target.startswith('/'):
                    self.assertIn(target, (*pages.ROUTES, *pages.SHARED_ASSETS), (path, href))

    def test_unknown_routes_and_asset_traversal_are_refused(self):
        for path in ('/admin', '/account', '/library', '/not-a-page', '/assets/agentafk/../index.html', '/assets/agentafk/missing.js'):
            self.assertIsNone(pages.render(path))

    def test_origin_validation_refuses_injection_and_plaintext_public_host(self):
        for origin in ('http://agentafk.si', 'https://user@agentafk.si', 'https://agentafk.si/path', 'https://agentafk.si?x=1', 'https://agentafk.si#x', 'https://agentafk.si:444', 'https://agentafk.si/\"><script>'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                pages.render('/', origin=origin)
        self.assertIn(b'https://www.agentafk.si/plan', pages.render('/plan', origin='https://www.agentafk.si')[0])
        self.assertIn(b'http://127.0.0.1:8765/plan', pages.render('/plan', origin='http://127.0.0.1:8765', allow_loopback=True)[0])
        with self.assertRaises(ValueError):
            pages.render('/', origin='http://127.0.0.1:8765')

    def test_assets_are_exact_and_content_versioned(self):
        html = pages.render('/')[0].decode()
        for name, media in pages.ASSETS.items():
            body, observed_media = pages.render(pages.ASSET_PREFIX + name)
            self.assertEqual(observed_media, media)
            self.assertIn(pages.ASSET_PREFIX + name + '?v=' + sha256(body).hexdigest(), html)
        self.assertTrue(pages.SHARED_ASSETS <= set(WEB_ASSETS))

    def test_existing_run_desk_contract_fields_and_ids_are_preserved(self):
        html = pages.render('/plan')[0].decode()
        for name in ('tasks', 'checkout', 'runs', 'workspace', 'calls', 'budget', 'timeout', 'deadline'):
            self.assertIn('name="' + name + '"', html)
        for identity in ('run-desk-form', 'run-desk-message', 'run-desk-command', 'run-desk-status-command', 'run-desk-download', 'run-desk-report', 'run-desk-summary', 'run-desk-attempts'):
            self.assertIn('id="' + identity + '"', html)
        self.assertIn('/assets/run-desk.js?v=' + sha256(read_packaged_asset('run-desk.js')).hexdigest(), html)
        self.assertIn('You start the run on that worker.', html)
        self.assertIn('Queue a dependent task once its prerequisite output is checked.', html)
        self.assertIn('The table shows only your own recorded attempts.', html)

    def test_scope_distinguishes_live_tools_from_planned_execution(self):
        home = pages.render('/')[0].decode()
        help_page = pages.render('/help')[0].decode()
        self.assertIn('Illustrative example plan.', home)
        self.assertIn('runs tasks in the exact order of the task manifest', help_page)
        self.assertIn('On your own computer or a cloud machine you control.', help_page)
        # The explicit hosted-execution limit stays where a visitor decides to pay and where agents read scope.
        self.assertIn('does not start a subscription or offer paid hosted execution', pages.render('/pricing')[0].decode())
        self.assertIn('Hosted execution and cloud supervision are unavailable.', pages.render('/llms.txt')[0].decode())
        self.assertIn('does not guarantee task completion', help_page)
        self.assertIn('Max subscriptions are not sold', pages.render('/pricing')[0].decode())

    def test_approved_legal_articles_are_reused_exactly(self):
        source = read_packaged_asset('index.html').decode()
        for path, article in (('/privacy', 'privacy-notice'), ('/terms', 'terms-of-service')):
            expected = re.search(r'<article id="' + article + r'"[\s\S]*?</article>', source).group()
            self.assertIn(expected, pages.render(path)[0].decode())

    def test_discovery_files_retain_origin_and_scope(self):
        for path in pages.SITE_FILES:
            body = pages.render(path, origin='https://www.agentafk.si')[0].decode()
            self.assertIn('https://www.agentafk.si', body)
            self.assertNotIn('baltor.ai', body)
        text = pages.render('/llms.txt')[0].decode()
        self.assertIn('not an adaptive dependency scheduler', text)
        self.assertIn('does not start a worker', text)

    def test_readiness_is_not_reported_as_worker_status(self):
        html = pages.render('/status')[0].decode()
        self.assertIn('Your worker reports the state of its own tasks.', html)
        js = pages.render(pages.ASSET_PREFIX + 'site.js')[0].decode()
        self.assertIn("fetch('/api/v1/health'", js)
        self.assertIn('body.result?.ready !== true', js)
        self.assertNotIn('localStorage', js)
        self.assertNotIn('POST', js)


if __name__ == '__main__':
    unittest.main()
