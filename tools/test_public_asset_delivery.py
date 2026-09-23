"""Public assets may be cached; account, protocol and error responses may not."""
from __future__ import annotations

import hashlib
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http


class PublicAssetDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.fixture = HttpDomainFixture(Path(cls.temporary.name))
        cls.server = running_http(cls.fixture)
        base, _application = cls.server.__enter__()
        cls.client = httpx.Client(base_url=base, trust_env=False, timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.server.__exit__(None, None, None)
        cls.temporary.cleanup()

    def test_asset_cache_is_bound_to_exact_bytes(self):
        response = self.client.get('/assets/service.css')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'public, max-age=300')
        self.assertEqual(response.headers['etag'], '"' + hashlib.sha256(response.content).hexdigest() + '"')

    def test_matching_weak_list_or_wildcard_validator_returns_no_body(self):
        first = self.client.get('/assets/service.css')
        tag = first.headers.get('etag', '"missing-validator"')
        for validator in (tag, 'W/' + tag, '"different", ' + tag, '*'):
            with self.subTest(validator=validator):
                response = self.client.get('/assets/service.css', headers={'If-None-Match': validator})
                self.assertEqual(response.status_code, 304)
                self.assertEqual(response.content, b'')
                self.assertEqual(response.headers['etag'], tag)
                self.assertEqual(response.headers['cache-control'], 'public, max-age=300')

    def test_stale_validator_gets_current_body(self):
        response = self.client.get('/assets/service.css', headers={'If-None-Match': '"old-release"'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content)

    def test_page_versions_each_direct_asset_reference(self):
        page = self.client.get('/')
        paths = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', page.text)
        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            with self.subTest(path=path):
                asset = self.client.get(path)
                versions = parse_qs(urlsplit(path).query).get('v')
                self.assertEqual(versions, [hashlib.sha256(asset.content).hexdigest()])
        self.assertEqual(page.headers['cache-control'], 'no-store')

    def test_head_reports_metadata_without_body(self):
        for path in ('/', '/terms', '/assets/service.css', '/assets/baltor-mark.svg'):
            with self.subTest(path=path):
                get = self.client.get(path)
                head = self.client.head(path)
                self.assertEqual(head.status_code, 200)
                self.assertEqual(head.content, b'')
                self.assertEqual(head.headers['content-length'], str(len(get.content)))
                self.assertEqual(head.headers['cache-control'], get.headers['cache-control'])
                self.assertEqual(head.headers.get('etag'), get.headers.get('etag'))

    def test_private_dynamic_and_error_responses_remain_uncacheable(self):
        for path in ('/', '/login', '/account', '/api/v1/health', '/api/v1/session',
                     '/assets/absent.css', '/assets/service.css/extra'):
            with self.subTest(path=path):
                response = self.client.get(path, headers={'If-None-Match': '*'})
                self.assertNotEqual(response.status_code, 304)
                self.assertEqual(response.headers['cache-control'], 'no-store')
        refused = self.client.get('/assets/service.css', headers={'Host': 'untrusted.invalid'})
        self.assertEqual(refused.status_code, 421)
        self.assertEqual(refused.headers['cache-control'], 'no-store')

    def test_writing_an_asset_is_not_a_cacheable_route(self):
        response = self.client.post('/assets/service.css')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers['cache-control'], 'no-store')


if __name__ == '__main__':
    unittest.main()
