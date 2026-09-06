"""Offline source-preparation tests; these make no network or model calls."""
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

import pandas as pd

SPEC = importlib.util.spec_from_file_location('portfolio_fetch', Path(__file__).with_name('fetch_openml.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourcePreparationTests(unittest.TestCase):
    def payloads(self, **changes):
        metadata = {'id': '61', 'name': 'fixture', 'version': '1', 'status': 'active',
                    'visibility': 'public', 'parquet_url': 'https://data.openml.org/fixture.pq',
                    'default_target_attribute': 'label'}
        metadata.update(changes)
        buffer = io.BytesIO()
        pd.DataFrame({'value': [1, 2], 'label': ['a', 'b']}).to_parquet(buffer, index=False)
        return [json.dumps({'data_set_description': metadata}).encode(), buffer.getvalue()]

    def test_preserves_sources_and_manifest(self):
        with tempfile.TemporaryDirectory() as root, patch.object(
                MODULE, 'fetch', side_effect=self.payloads()):
            target = Path(root) / 'source'
            result = MODULE.prepare(61, target, 'classification', ())
            self.assertEqual(result['source']['rows'], 2)
            self.assertFalse(result['source']['unseen'])
            self.assertEqual(result['source']['license'], 'unknown')
            self.assertEqual(len(result['source']['csv_sha256']), 64)
            self.assertEqual(json.loads((target / 'manifest.json').read_text()), result)

    def test_refuses_existing_output_without_network(self):
        with tempfile.TemporaryDirectory() as root, patch.object(MODULE, 'fetch') as fetch:
            with self.assertRaises(ValueError):
                MODULE.prepare(61, Path(root), 'classification', ())
            fetch.assert_not_called()

    def test_refuses_wrong_source_identity(self):
        with tempfile.TemporaryDirectory() as root, patch.object(
                MODULE, 'fetch', side_effect=self.payloads(id='62')):
            with self.assertRaises(ValueError):
                MODULE.prepare(61, Path(root) / 'source', 'classification', ())

    def test_refuses_unknown_exclusion(self):
        with tempfile.TemporaryDirectory() as root, patch.object(
                MODULE, 'fetch', side_effect=self.payloads()):
            with self.assertRaises(ValueError):
                MODULE.prepare(61, Path(root) / 'source', 'classification', ('missing',))

    def test_refuses_unregistered_endpoint(self):
        with patch.object(MODULE, 'build_opener') as request:
            with self.assertRaises(ValueError):
                MODULE.fetch('http://127.0.0.1/private')
            request.assert_not_called()

    def test_refuses_redirect_before_dispatch(self):
        request = Request('https://openml.org/source')
        with self.assertRaises(ValueError):
            MODULE.SourceRedirectHandler().redirect_request(
                request, None, 302, 'Found', {}, 'http://127.0.0.1/private')

    def test_allows_registered_https_redirect(self):
        request = Request('https://openml.org/source')
        redirected = MODULE.SourceRedirectHandler().redirect_request(
            request, None, 302, 'Found', {}, 'https://data.openml.org/source.pq')
        self.assertEqual(redirected.full_url, 'https://data.openml.org/source.pq')

    def test_refuses_embedded_credentials_and_alternate_port(self):
        for url in ('https://secret@openml.org/data', 'https://openml.org:8443/data'):
            with self.assertRaises(ValueError):
                MODULE.validate_source_url(url)


if __name__ == '__main__':
    unittest.main()
