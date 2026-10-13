"""Independent source-shape and uncertainty controls for candidate readers."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
import io

from knowledge_radar import endoflife_cycles as eol, osv_advisories as osv, pypi_releases as pypi
from knowledge_radar.source_capture import read_capture
import read_pypi_releases


class FeedReaderReviewTests(unittest.TestCase):
    def test_osv_paginated_empty_page_is_not_unaffected(self):
        request = osv.OSVBatchRequest((osv.PackagePin('PyPI', 'example', '1.0'),))
        result = osv.parse_batch_response(b'{"results":[{"next_page_token":"next"}]}', request, observed_on='2026-10-13')
        self.assertNotIn('PyPI:example@1.0', result.get('unaffected_pins', []))
        self.assertFalse(result['coverage_complete'])

    def test_osv_falsey_nonlist_is_refused(self):
        request = osv.OSVBatchRequest((osv.PackagePin('PyPI', 'example', '1.0'),))
        for invalid in ({}, False, 0, ''):
            with self.subTest(invalid=invalid), self.assertRaises(osv.OSVQueryError):
                osv.parse_batch_response(json.dumps({'results': [{'vulns': invalid}]}).encode(), request, observed_on='2026-10-13')

    def test_eol_missing_support_is_unknown(self):
        result = eol.parse_product_cycles(b'{"result":{"name":"python","releases":[{"name":"3.99"}]}}', eol.EndOfLifeRequest('python'), as_of='2026-10-13')
        self.assertEqual(result['cycles'][0]['lifecycle_status'], 'unknown_support')

    def test_eol_legacy_unbound_shape_refused(self):
        with self.assertRaises(eol.EndOfLifeReadError):
            eol.parse_product_cycles(b'[{"cycle":"3.9","eol":false}]', eol.EndOfLifeRequest('python'), as_of='2026-10-13')

    def test_eol_string_boolean_refused(self):
        with self.assertRaises(eol.EndOfLifeReadError):
            eol.parse_product_cycles(b'{"result":{"name":"python","releases":[{"name":"3.9","isEol":"false"}]}}', eol.EndOfLifeRequest('python'), as_of='2026-10-13')

    def test_pypi_filename_must_bind_project(self):
        body = {'meta': {'api-version': '1.1'}, 'name': 'example', 'files': [{'filename': 'other-1.0-py3-none-any.whl', 'url': 'https://files.pythonhosted.org/other.whl', 'hashes': {'sha256': 'a'*64}}]}
        with self.assertRaises(pypi.PyPIReadError):
            pypi.parse_simple_index(json.dumps(body).encode(), pypi.PyPIRequest('example'), observed_on='2026-10-13')

    def test_pypi_impossible_date_refused(self):
        with self.assertRaises(pypi.PyPIReadError):
            pypi.parse_simple_index(b'{"meta":{"api-version":"1.1"},"name":"example","files":[]}', pypi.PyPIRequest('example'), observed_on='2026-99-99')

    def test_capture_refuses_size_symlinks_directories_and_fifo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'capture.json'
            path.write_bytes(b'12345')
            self.assertEqual(read_capture(path, 5), b'12345')
            with self.assertRaises(ValueError):
                read_capture(path, 4)
            alias = root / 'alias'
            alias.symlink_to(path)
            parent_alias = root / 'parent_alias'
            parent_alias.symlink_to(root)
            fifo = root / 'fifo'
            os.mkfifo(fifo)
            for invalid in (alias, parent_alias / 'capture.json', root, fifo):
                with self.subTest(path=invalid), self.assertRaises((OSError, ValueError)):
                    read_capture(invalid, 5)

    def test_cli_capture_requires_explicit_date(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            path = Path(directory) / 'capture.json'
            path.write_bytes(b'{"meta":{"api-version":"1.1"},"name":"example","files":[]}')
            self.assertEqual(read_pypi_releases.main(['--project', 'example', '--input-capture', str(path)]), 1)
            self.assertEqual(json.loads(output.getvalue())['status'], 'refused')

    def test_batch_does_not_accept_invented_full_details(self):
        request = osv.OSVBatchRequest((osv.PackagePin('PyPI', 'example', '1.0'),))
        body = {'results': [{'vulns': [{'id': 'GHSA-abcd-efgh-1234', 'modified': '2026-10-13T00:00:00Z', 'affected': []}]}]}
        with self.assertRaises(osv.OSVQueryError):
            osv.parse_batch_response(json.dumps(body).encode(), request, observed_on='2026-10-13')

    def test_continuation_empty_page_does_not_claim_complete_query(self):
        request = osv.OSVBatchRequest((osv.PackagePin('PyPI', 'example', '1.0', page_token='last'),))
        result = osv.parse_batch_response(b'{"results":[{}]}', request, observed_on='2026-10-13')
        self.assertFalse(result['coverage_complete'])
        self.assertEqual(result['no_matches_on_complete_query'], [])

    def test_pypi_input_permutation_cannot_change_selected_versions(self):
        files = [{'filename': f'example-{version}-py3-none-any.whl', 'url': 'https://files.pythonhosted.org/example.whl', 'hashes': {'sha256': 'a'*64}} for version in ('9.0', '10.0', '1.0')]
        request = pypi.PyPIRequest('example', max_releases=2)
        def parse(rows):
            return pypi.parse_simple_index(json.dumps({'meta': {'api-version': '1.1'}, 'name': 'example', 'files': rows}).encode(), request, observed_on='2026-10-13')
        a, b = parse(files), parse(list(reversed(files)))
        self.assertEqual(a['retained_versions'], b['retained_versions'])
        self.assertEqual(a['newly_observed_versions'], [])
        self.assertFalse(a['selection_complete'])
        self.assertFalse(a['installation_compatibility_checked'])

    def test_duplicate_eol_cycles_refused(self):
        with self.assertRaises(eol.EndOfLifeReadError):
            eol.parse_product_cycles(b'{"result":{"name":"python","releases":[{"name":"3.9"},{"name":"3.9"}]}}', eol.EndOfLifeRequest('python'), as_of='2026-10-13')


if __name__ == '__main__':
    unittest.main()
