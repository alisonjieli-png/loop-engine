import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collector
import extended_sources
import run_discovery as runner


class CombinedRunTests(unittest.TestCase):
    def configs(self):
        root = Path(__file__).parent
        return (json.loads((root / 'sources-core-v3.json').read_bytes()),
                json.loads((root / 'extended-sources-v2.json').read_bytes()))

    def test_total_budget_is_checked_before_network(self):
        core, extra = self.configs()
        extra = copy.deepcopy(extra)
        extra['maximum_requests'] = 20
        with patch.object(collector, 'run') as network:
            with self.assertRaisesRegex(ValueError, 'combined_request_bound'):
                runner.run(core, extra, Path('/does-not-matter'))
            network.assert_not_called()

    def test_failed_family_is_not_reported_complete(self):
        core, extra = self.configs()
        with tempfile.TemporaryDirectory() as d, patch.object(collector, 'run', return_value={'status': 'complete'}) as watcher, patch.object(extended_sources, 'run') as expanded:
            def record(config, folder):
                folder.mkdir()
                return {'status': 'partial', 'observations': 4, 'families': {'papers': 4}}
            expanded.side_effect = record
            result = runner.run(core, extra, Path(d))
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['component_approvals'], 0)
            self.assertTrue((Path(d) / 'combined-latest.json').is_file())
            self.assertEqual(watcher.call_count, 1)

    def test_rotation_outcome_is_saved_before_pointer_and_failure_does_not_advance(self):
        core, extra = self.configs()
        rotation = json.loads(Path(__file__).with_name('coverage-topics-v1.json').read_bytes())
        with tempfile.TemporaryDirectory() as d, patch.object(collector, 'run', return_value={'status': 'complete'}), patch.object(extended_sources, 'run') as expanded:
            def record(config, folder):
                folder.mkdir()
                return {'status': 'complete', 'observations': 0, 'families': {}, 'sources': []}
            expanded.side_effect = record
            result = runner.run(core, extra, Path(d), rotation)
            self.assertEqual(result['record_type'], 'combined_source_discovery_run/v2')
            self.assertEqual(result['coverage']['selected_topic_ids'], ['domain-api-contracts', 'domain-data-cleaning'])
            path = Path(d) / 'coverage-state.json'
            before = path.read_bytes()
            folder = Path(result['extended_report']).parent
            self.assertTrue((folder / 'coverage-completed.json').exists())
            self.assertEqual(json.loads(before)['runs'], 1)
            expanded.side_effect = RuntimeError('interrupted before report')
            with self.assertRaises(RuntimeError):
                runner.run(core, extra, Path(d), rotation)
            self.assertEqual(path.read_bytes(), before)

    def test_bad_coverage_state_refuses_before_network(self):
        core, extra = self.configs()
        rotation = json.loads(Path(__file__).with_name('coverage-topics-v1.json').read_bytes())
        with tempfile.TemporaryDirectory() as d, patch.object(collector, 'run') as network:
            (Path(d) / 'coverage-state.json').write_text('{}')
            with self.assertRaises(ValueError):
                runner.run(core, extra, Path(d), rotation)
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
