import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import collector as c


def repo(source='watch-fixture', stars=10):
    return c.repository({'id': 12, 'full_name': 'example/project', 'html_url': 'https://github.com/example/project',
                         'description': 'Agent memory tools', 'stargazers_count': stars, 'forks_count': 2,
                         'created_at': '2026-09-01T00:00:00Z', 'pushed_at': '2026-09-20T00:00:00Z',
                         'topics': ['agent'], 'license': {'spdx_id': 'MIT'}}, source)


class CollectorChecks(unittest.TestCase):
    def test_repository_identity_not_just_title(self):
        self.assertEqual(repo()['key'], 'github-repository:12')
        with self.assertRaises(ValueError):
            c.repository({'id': True, 'full_name': 'example/project', 'html_url': 'https://github.com/example/project'}, 'x')

    def test_repo_url_cannot_point_to_other_host(self):
        with self.assertRaises(ValueError):
            c.repository({'id': 1, 'full_name': 'example/project', 'html_url': 'https://example.invalid/project'}, 'x')

    def test_source_urls_never_include_credentials(self):
        for value in ['http://example.invalid', 'https://name:password@example.invalid', 'javascript:alert(1)']:
            with self.assertRaises(ValueError):
                c.public_url(value)

    def test_atom_and_rss_dates(self):
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Agent release</title><link href="https://example.invalid/release"/><updated>2026-09-26T03:00:00+03:00</updated></entry></feed>'
        rows = c.parse_feed(atom, 'feed')
        self.assertEqual(rows[0]['updated_at'], '2026-09-26T00:00:00Z')
        self.assertEqual(rows[0]['verification'], 'discovery_only')

    def test_naive_and_invalid_dates_remain_unknown(self):
        self.assertIsNone(c.timestamp('yesterday'))
        self.assertIsNone(c.timestamp('2026-09-26T00:00:00'))

    def test_unknown_feed_is_not_a_successful_empty_feed(self):
        with self.assertRaises(ValueError):
            c.parse_feed(b'<html><body>maintenance</body></html>', 'feed')

    def test_xml_entities_refuse(self):
        with self.assertRaises(ValueError):
            c.parse_feed(b'<!DOCTYPE x [<!ENTITY y "x">]><rss/>', 'feed')

    def test_duplicate_discovery_keeps_one_identity_and_all_sources(self):
        records, changes = c.merge({}, [repo('watch-fixture'), repo('search-fixture')], '2026-09-26T00:00:00Z', ['agent'])
        self.assertEqual(len(records), 1)
        self.assertEqual(changes['new'], 1)
        item = records['github-repository:12']
        self.assertEqual(item['seen_via'], ['search-fixture', 'watch-fixture'])
        self.assertIn('explicit_watchlist', item['priority_reasons'])

    def test_popularity_change_does_not_require_semantic_rereview(self):
        records, _ = c.merge({}, [repo()], '2026-09-26T00:00:00Z', ['agent'])
        records['github-repository:12']['review_state'] = 'reviewed'
        updated, changes = c.merge(records, [repo(stars=30)], '2026-09-26T06:00:00Z', ['agent'])
        self.assertEqual(updated['github-repository:12']['review_state'], 'reviewed')
        self.assertEqual(changes['substantive_changes'], 0)

    def test_changed_source_description_requests_targeted_review(self):
        records, _ = c.merge({}, [repo()], '2026-09-26T00:00:00Z', ['agent'])
        records['github-repository:12']['review_state'] = 'reviewed'
        changed = repo(); changed['summary'] = 'New sandbox execution system'
        updated, counts = c.merge(records, [changed], '2026-09-26T06:00:00Z', ['agent'])
        self.assertEqual(updated['github-repository:12']['review_state'], 'changed_needs_review')
        self.assertEqual(counts['substantive_changes'], 1)

    def test_boolean_budget_and_unknown_source_fields_refuse(self):
        config = json.loads(Path(__file__).with_name('sources.json').read_text())
        for key in ['maximum_requests', 'timeout_seconds', 'queue_size']:
            bad = copy.deepcopy(config); bad[key] = True
            with self.assertRaises(ValueError): c.validate_config(bad)
        config['sources'][0]['credential'] = 'unwanted'
        with self.assertRaises(ValueError): c.validate_config(config)

    def test_empty_collection_retains_previous_observations(self):
        records, _ = c.merge({}, [repo()], '2026-09-26T00:00:00Z', ['agent'])
        self.assertEqual(c.merge(records, [], '2026-09-26T06:00:00Z', ['agent'])[0], records)

    def test_full_local_run_saves_unapproved_projection(self):
        config = json.loads(Path(__file__).with_name('sources.json').read_text())
        config['sources'] = config['sources'][:1]
        class FakeTransport:
            def __init__(self, hosts, budget, log, **kwargs): self.budget = budget
            def get(self, *args):
                self.budget.admit()
                return SimpleNamespace(status=200, body=json.dumps({'id':12,'full_name':'example/project','html_url':'https://github.com/example/project'}).encode())
        with tempfile.TemporaryDirectory() as temp, patch.object(c, 'HttpsGetTransport', FakeTransport):
            report = c.run(config, Path(temp))
            self.assertEqual(report['status'], 'complete')
            queue = json.loads((Path(temp)/'review-queue.json').read_text())
            self.assertEqual(queue['items'][0]['verification'], 'discovery_only')


if __name__ == '__main__':
    unittest.main()
