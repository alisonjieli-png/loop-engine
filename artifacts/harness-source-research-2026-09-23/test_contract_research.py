"""Offline discriminating checks for the dated research adapter, not admission tests."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('contract_research', Path(__file__).with_name('collect_contract_candidates.py'))
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class ResearchBoundaryChecks(unittest.TestCase):
    def test_private_credential_query_port_and_deceptive_origins_refuse(self):
        for url in ('https://user:secret@raw.githubusercontent.com/a/b/main/x.json',
            'https://raw.githubusercontent.com.evil.invalid/x', 'http://www.schemastore.org/x',
            'https://127.0.0.1/x', 'https://www.schemastore.org/x?api_key=x',
            'https://www.schemastore.org/../x', 'https://www.schemastore.org:443/x',
            'https://api.apis.guru/v2/specs/europeana.eu/version unknown/swagger.json'):
            with self.subTest(url=url): self.assertIsNone(subject.safe_address(url))

    def test_duplicate_keys_and_nonfinite_values_do_not_become_parsed_evidence(self):
        for data in (b'{"type":"object","type":"array"}', b'{"x":NaN}', b'{"x":Infinity}', b'[1,2]'):
            with self.subTest(data=data), self.assertRaises(ValueError): subject.inspect_body(data, 'document_schema')

    def test_remote_reference_is_counted_without_fetching_or_evaluation(self):
        row = subject.inspect_body(b'{"type":"object","$ref":"http://127.0.0.1/private"}', 'document_schema')
        self.assertEqual(row['external_reference_count'], 1)
        self.assertFalse(row['remote_references_resolved'])
        self.assertFalse(row['metaschema_validated'])

    def test_boolean_schema_and_empty_schema_remain_valid_parse_shapes(self):
        self.assertEqual(subject.inspect_body(b'true', 'document_schema')['root_kind'], 'boolean')
        self.assertTrue(subject.inspect_body(b'{}', 'document_schema')['json_parsed'])

    def test_plain_schema_is_not_an_openapi_document(self):
        with self.assertRaises(ValueError): subject.inspect_body(b'{"type":"object"}', 'service_api')

    def test_catalogue_version_aliases_do_not_inflate_selected_count(self):
        rows, collapsed, _ = subject.catalogue_rows(); selected = subject.select(rows)
        self.assertEqual(len(selected), 1000)
        self.assertEqual(len({r['logical_contract_key'] for r in selected}), 1000)
        self.assertEqual(len({r['research_id'] for r in selected}), 1000)
        self.assertLess(len(rows), 1474 + 2529)
        self.assertTrue(any(r['kind'] == 'provider_title_family' for r in collapsed))
        self.assertTrue(all(r['qualification_status'] == 'unreviewed' and not r['license_verified'] for r in selected))

    def test_future_ranked_lists_exclude_invalid_navigation_without_guessing(self):
        rows, collapsed, _ = subject.catalogue_rows()
        self.assertTrue(all(subject.navigation_address(row['source_url']) for row in rows))
        self.assertTrue(any(row['kind'] == 'invalid_navigation_url_excluded' for row in collapsed))
        self.assertFalse(subject.navigation_address('https://api.apis.guru/v2/specs/europeana.eu/version unknown/swagger.json'))
        self.assertTrue(subject.navigation_address('https://api.apis.guru/v2/specs/europeana.eu/version%20unknown/swagger.json'))


if __name__ == '__main__': unittest.main()
