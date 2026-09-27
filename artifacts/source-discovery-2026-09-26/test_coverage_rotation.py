import copy
import json
import unittest
from pathlib import Path

import coverage_rotation as c


class CoverageRotationTests(unittest.TestCase):
    def configs(self):
        root = Path(__file__).parent
        return (json.loads((root / 'coverage-topics-v1.json').read_bytes()),
                json.loads((root / 'extended-sources-v2.json').read_bytes()))

    def test_rotation_visits_every_topic_before_repeating(self):
        rotation, extra = self.configs()
        state = None
        visited = []
        for _ in range(len(rotation['topics']) // 2):
            config, proposal = c.prepare(rotation, extra, state)
            selected = proposal['selected_topic_ids']
            self.assertEqual(len(selected), 2)
            self.assertLessEqual(len(config['sources']), 10)
            visited.extend(selected)
            state = c.complete(proposal, {'sources': []})
        self.assertEqual(len(visited), len(set(visited)))
        self.assertEqual(set(visited), {s['id'] for s in rotation['topics']})
        _, proposal = c.prepare(rotation, extra, state)
        self.assertEqual(proposal['selected_topic_ids'], visited[:2])

    def test_registry_cursor_advances_only_after_complete_page(self):
        rotation, extra = self.configs()
        _, proposal = c.prepare(rotation, extra, None)
        result = {'sources': [{'source_id': 'protocol-registry', 'outcome': 'ok',
                              'coverage': {'next_cursor': 'opaque:/a+b'}}]}
        state = c.complete(proposal, result)
        config, proposal = c.prepare(rotation, extra, state)
        registry = next(s for s in config['sources'] if s['id'] == 'protocol-registry')
        self.assertEqual(registry['query']['cursor'], 'opaque:/a+b')
        failed = c.complete(proposal, {'sources': [{'source_id': 'protocol-registry', 'outcome': 'partial',
                                                   'coverage': {'next_cursor': 'skip-me'}}]})
        self.assertEqual(failed['registry_cursors']['protocol-registry'], 'opaque:/a+b')
        terminal = c.complete(proposal, {'sources': [{'source_id': 'protocol-registry', 'outcome': 'ok',
                                                     'coverage': {'next_cursor': None}}]})
        self.assertIsNone(terminal['registry_cursors']['protocol-registry'])
        self.assertFalse(terminal['complete_catalogue'])

    def test_foreign_configuration_state_cannot_control_current_queries(self):
        rotation, extra = self.configs()
        _, proposal = c.prepare(rotation, extra, None)
        state = c.complete(proposal, {'sources': []})
        state['configuration_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'coverage_configuration_changed'):
            c.prepare(rotation, extra, state)

    def test_unknown_versions_fields_and_routes_refuse(self):
        rotation, extra = self.configs()
        for change in [lambda x: x.update(record_type='source_discovery_rotation/v0'),
                       lambda x: x.update(unknown=True),
                       lambda x: x['topics'][0].update(host='localhost'),
                       lambda x: x.update(per_run=1000),
                       lambda x: x['topics'].append(copy.deepcopy(x['topics'][0]))]:
            bad = copy.deepcopy(rotation)
            change(bad)
            with self.assertRaises(ValueError):
                c.prepare(bad, extra, None)

    def test_state_cursor_bound_and_repeated_cursor_recorded(self):
        rotation, extra = self.configs()
        _, proposal = c.prepare(rotation, extra, None)
        result = {'sources': [{'source_id': 'protocol-registry', 'outcome': 'ok',
                              'coverage': {'next_cursor': 'same'}}]}
        state = c.complete(proposal, result)
        _, proposal = c.prepare(rotation, extra, state)
        repeated = c.complete(proposal, result)
        self.assertEqual(repeated['last_findings'], ['protocol-registry:cursor_did_not_advance'])
        self.assertIsNone(repeated['registry_cursors']['protocol-registry'])
        state['registry_cursors']['protocol-registry'] = 'x' * 5000
        with self.assertRaises(ValueError):
            c.prepare(rotation, extra, state)

    def test_resolved_plan_can_be_replayed_without_advancing_state(self):
        rotation, extra = self.configs()
        first, proposal = c.prepare(rotation, extra, None)
        second, retry = c.prepare(rotation, extra, None)
        self.assertEqual(first, second)
        self.assertEqual(proposal, retry)
        self.assertEqual(proposal['completed_state']['runs'], 0)


if __name__ == '__main__':
    unittest.main()
