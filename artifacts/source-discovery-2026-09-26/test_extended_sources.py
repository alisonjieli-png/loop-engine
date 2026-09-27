import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import extended_sources as e

CONFIG = json.loads(Path(__file__).with_name('extended-sources-v1.json').read_bytes())


def source(kind):
    return next(s for s in CONFIG['sources'] if s['kind'] == kind)


class ExtendedSourcesTests(unittest.TestCase):
    def test_configuration_refuses_undeclared_routes_and_unbounded_pages(self):
        self.assertEqual(len(e.validate(CONFIG)['sources']), 8)
        for field, value in [('host', '127.0.0.1'), ('path', '/other'), ('maximum_entries', True)]:
            bad = copy.deepcopy(CONFIG)
            bad['sources'][0][field] = value
            with self.assertRaises(ValueError):
                e.validate(bad)
        bad = copy.deepcopy(CONFIG)
        bad['sources'][0]['query']['limit'] = 1000
        with self.assertRaises(ValueError):
            e.validate(bad)

    def test_papers_keep_identity_without_abstract_or_access_claim(self):
        rows, omitted, coverage = e.parse(json.dumps([{'paper': {'id': '2609.12345', 'title': 'Test paper', 'summary': 'Do not republish this abstract.'}}]).encode(), source('daily_papers'))
        self.assertEqual(rows[0]['key'], 'paper:2609.12345')
        self.assertNotIn('abstract', json.dumps(rows))
        self.assertIsNone(rows[0]['summary'])
        self.assertFalse(rows[0]['source_body_read'])
        self.assertFalse(coverage['complete_source'])
        self.assertEqual(omitted, [])

    def test_registry_keeps_deleted_status_and_opaque_cursor(self):
        data = {'servers': [{'server': {'name': 'org.example/tool', 'version': '1+2'}, '_meta': {'io.modelcontextprotocol.registry/official': {'status': 'deleted', 'isLatest': True}}}], 'metadata': {'nextCursor': 'opaque:/a+b'}}
        rows, _, coverage = e.parse(json.dumps(data).encode(), source('mcp_registry'))
        self.assertEqual(rows[0]['facts']['registry_status'], 'deleted')
        self.assertIn('org.example%2Ftool/versions/1%2B2', rows[0]['url'])
        self.assertEqual(coverage['next_cursor'], 'opaque:/a+b')
        self.assertEqual(rows[0]['component_admission'], 'not_requested')

    def test_overfull_registry_page_records_unseen_rows(self):
        s = dict(source('mcp_registry'), maximum_entries=1)
        item = {'server': {'name': 'org.example/tool', 'version': '1'}, '_meta': {'io.modelcontextprotocol.registry/official': {}}}
        raw = json.dumps({'servers': [item, item], 'metadata': {'nextCursor': 'after-second'}}).encode()
        rows, omitted, coverage = e.parse(raw, s)
        self.assertEqual(len(rows), 1)
        self.assertEqual(omitted, [{'entry_index': 1, 'omitted_entries': 1, 'reason': 'source_page_exceeds_bound'}])
        self.assertEqual(coverage['page_entries'], 2)

    def test_malformed_registry_metadata_keeps_other_sources_running(self):
        config = dict(CONFIG, sources=[source('mcp_registry'), source('daily_papers')])
        responses = [SimpleNamespace(status=200, body=b'{"servers":[],"metadata":null}'),
                     SimpleNamespace(status=200, body=b'[{"paper":{"id":"2609.12345","title":"A"}}]')]
        with tempfile.TemporaryDirectory() as d, patch.object(e.base.HttpsGetTransport, 'get', side_effect=responses):
            report = e.run(config, Path(d) / 'run')
            self.assertEqual(report['status'], 'partial')
            self.assertEqual(report['sources'][0]['outcome'], 'failed')
            self.assertEqual(report['sources'][1]['observations'], 1)

    def test_null_individual_registry_metadata_is_a_recorded_exclusion(self):
        raw = json.dumps({'servers': [{'server': {'name': 'org.example/tool', 'version': '1'},
                                      '_meta': {'io.modelcontextprotocol.registry/official': None}}]}).encode()
        rows, omitted, _ = e.parse(raw, source('mcp_registry'))
        self.assertFalse(rows)
        self.assertEqual(len(omitted), 1)

    def test_bad_rows_are_excluded_without_discarding_valid_rows(self):
        raw = json.dumps([{'paper': {'id': '2609.12345', 'title': 'Valid'}}, {'paper': {'id': '../secrets', 'title': 'Bad'}}]).encode()
        rows, omitted, _ = e.parse(raw, source('daily_papers'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(omitted[0]['entry_index'], 1)

    def test_npm_scopes_and_versions_are_distinct(self):
        raw = json.dumps({'objects': [{'package': {'name': '@example/tool', 'version': '1.2.3', 'license': 'MIT'}}], 'total': 100}).encode()
        rows, _, coverage = e.parse(raw, source('npm_search'))
        self.assertEqual(rows[0]['key'], 'npm:@example/tool@1.2.3')
        self.assertFalse(rows[0]['licence_verified'])
        self.assertEqual(coverage['available_entries'], 100)

    def test_skill_links_reject_external_scripts_and_parent_steps(self):
        raw = b'<a href="/owner/repo/skill">Skill</a><a href="/owner/repo/skill">Again</a><a href="https://elsewhere.test/a/b/c">No</a><a href="/owner/../bad">No</a><script>"<a href=\"/x/y/z\">fake</a>"</script>'
        rows, _, _ = e.parse(raw, source('skills_directory'))
        self.assertEqual([r['title'] for r in rows], ['owner/repo/skill'])

    def test_trending_excludes_navigation_and_sponsor_links(self):
        raw = b'<a href="/topics/python">nav</a><article><h2><a href="/owner/repo">repo</a></h2><a href="/sponsors/owner">sponsor</a></article>'
        rows, _, _ = e.parse(raw, source('github_trending'))
        self.assertEqual([r['title'] for r in rows], ['owner/repo'])

    def test_html_drift_is_failure_not_empty_success(self):
        with self.assertRaisesRegex(ValueError, 'directory_shape_not_observed'):
            e.parse(b'<h1>Login required</h1>', source('skills_directory'))

    def test_distillation_keeps_origins_and_failure(self):
        row = e.entry('paper:2609.12345', 'Paper', 'https://huggingface.co/papers/2609.12345', source=source('daily_papers'))
        records = e.distill([row, dict(row, source_id='another')], [{'family': 'papers', 'outcome': 'failed'}], '2026-09-26T00:00:00Z')
        self.assertEqual(records[0]['distinct_source_identities'], 1)
        self.assertEqual(records[0]['observations'], 2)
        self.assertEqual(records[0]['status'], 'partial')
        self.assertEqual(records[0]['new_components'], 0)

    def test_actual_runner_writes_partial_receipt_and_preserves_capture(self):
        config = dict(CONFIG, sources=[source('daily_papers'), source('skills_directory')])
        responses = [SimpleNamespace(status=200, body=b'[{"paper":{"id":"2609.12345","title":"A"}}]'), SimpleNamespace(status=503, body=b'Unavailable')]
        with tempfile.TemporaryDirectory() as d, patch.object(e.base.HttpsGetTransport, 'get', side_effect=responses):
            output = Path(d) / 'run'
            report = e.run(config, output)
            self.assertEqual(report['status'], 'partial')
            self.assertEqual(report['observations'], 1)
            self.assertTrue((output / 'daily-papers.response').is_file())
            self.assertTrue((output / 'skills.json').is_file())
            with self.assertRaises(FileExistsError):
                e.run(config, output)


if __name__ == '__main__':
    unittest.main()
