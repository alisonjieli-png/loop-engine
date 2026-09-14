"""Negative controls for report identity, incomplete usage and setup admission."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from embodiment_lab.campaign_report import _tokens, campaign_report, render_campaign_html
from embodiment_lab.trial_evidence import _checkpoint_contains_attempts, _step_history_verified
from loop_engine.core.harness_configuration import load_harness_binding
from loop_engine.core.harness_process import HarnessProcessError
from loop_engine.core.product_outcome_store import (
    ProductOutcomeRef, SavedRunBundle, matches_bound_product_outcome)
from loop_engine.core.run_history import RunHistory


class EvidenceIntegrityChecks(unittest.TestCase):
    def test_an_intact_earlier_checkpoint_cannot_claim_a_later_call(self):
        from collections import Counter
        from loop_engine.core.run_history import MODEL_INVOCATION_EVENT
        with tempfile.TemporaryDirectory(prefix='invocation-checkpoint-check-') as directory:
            history = RunHistory('fixture-prefix')
            history.append('loop_init', loop_id='fixture-owner')
            first = history.append_checkpoint(directory)
            history.append(MODEL_INVOCATION_EVENT, loop_id='provider-call',
                           detail={'semantic_call_id': 'repeated'})
            second = history.append_checkpoint(directory)
            history.append(MODEL_INVOCATION_EVENT, loop_id='provider-call',
                           detail={'semantic_call_id': 'repeated'})
            third = history.append_checkpoint(directory)
            row = lambda checkpoint: {'history': str(Path(directory) / 'fixture-prefix'),
                                      'revision': checkpoint['revision']}
            once = Counter({('provider-call', 'repeated'): 1})
            twice = Counter({('provider-call', 'repeated'): 2})
            cache = {}
            self.assertTrue(_step_history_verified(row(first), cache))
            self.assertFalse(_checkpoint_contains_attempts(row(first), once, cache))
            self.assertTrue(_checkpoint_contains_attempts(row(second), once, cache))
            self.assertFalse(_checkpoint_contains_attempts(row(second), twice, cache))
            self.assertTrue(_checkpoint_contains_attempts(row(third), twice, cache))

    def test_trillion_level_range_is_projected_without_enumeration(self):
        from embodiment_lab.campaign_report import campaign_grid
        from loop_engine.generation.space import ConfigurationAxis, ConfigurationSpace
        space = ConfigurationSpace('wide-fixture', '1.0.0', (
            ConfigurationAxis('seed', 'integer_range', minimum=1, maximum=10**12),))
        report = campaign_grid(space.to_dict(), [
            {'task_id': 'fixture', 'configuration': space.configuration_at(10**12 - 1),
             'status': 'finished', 'family': 'fixture'}])
        self.assertEqual(report['cardinality'], 10**12)
        self.assertEqual(report['axes'][0]['levels'], [])
        self.assertEqual(report['axes'][0]['level_domain']['maximum'], 10**12)
        self.assertEqual(report['placed'][0]['coordinates'], [str(10**12)])
        self.assertEqual(len(report['by_level']['seed']), 1)

    def test_usage_missing_partial_invalid_and_zero_remain_distinct(self):
        self.assertIsNone(_tokens({})['total_tokens'])
        no_calls = _tokens({'model_calls': 0, 'model_call_accounting_complete': True})
        self.assertEqual(no_calls['total_tokens'], 0)
        value = _tokens({'model_usage': [{'prompt_tokens': 2, 'eval_tokens': 3},
                                        {'prompt_tokens': None, 'eval_tokens': 5}]})
        self.assertIsNone(value['total_tokens'])
        self.assertEqual(value['known_tokens_subtotal'], 10)
        self.assertEqual(value['completion_tokens'], 8)
        invalid = _tokens({'model_usage': [{'prompt_tokens': True, 'eval_tokens': -1}]})
        self.assertEqual(invalid['entries_without_counts'], 1)
        self.assertFalse(invalid['accounting_complete'])

    def test_full_outcome_or_exact_public_projection_only(self):
        outcome = {'status': 'NO_PROGRESS', 'run_history': {'run_id': 'test'},
                   'task_accepted': False}
        reference = ProductOutcomeRef('outcome.json', 'a' * 64, 'solve_outcome/v5', 'NO_PROGRESS', False)
        bundle = SavedRunBundle(RunHistory('test'), outcome, reference)
        public = deepcopy(outcome)
        public['run_history'].update(product_outcome_bound=True,
            product_outcome_digest=reference.content_digest, terminal_code='NO_PROGRESS',
            product_outcome=reference.to_dict())
        self.assertTrue(matches_bound_product_outcome(outcome, bundle))
        self.assertTrue(matches_bound_product_outcome(public, bundle))
        for path, value in (('task_accepted', True), ('status', 'COMPLETED_VERIFIED'), ('extra', 'unbound')):
            changed = deepcopy(public)
            changed[path] = value
            self.assertFalse(matches_bound_product_outcome(changed, bundle))
        public['run_history']['product_outcome_digest'] = 'b' * 64
        self.assertFalse(matches_bound_product_outcome(public, bundle))

    def test_checkpoint_verification_reads_a_store_once_and_never_uses_latest(self):
        with tempfile.TemporaryDirectory(prefix='checkpoint-report-check-') as directory:
            saved = Path(directory) / 'history'
            saved.mkdir()
            (saved / 'checkpoints.jsonl').touch()
            cache = {}
            with patch.object(RunHistory, 'verified_checkpoints', return_value={1: True, 2: False}) as verify:
                self.assertTrue(_step_history_verified({'history': str(saved), 'revision': 1}, cache))
                self.assertFalse(_step_history_verified({'history': str(saved), 'revision': 2}, cache))
                self.assertFalse(_step_history_verified({'history': str(saved), 'revision': 3}, cache))
                self.assertFalse(_step_history_verified({'history': str(saved)}, cache))
                self.assertEqual(verify.call_count, 1)

    def test_report_explains_completion_and_missing_accounting(self):
        with tempfile.TemporaryDirectory(prefix='campaign-page-check-') as directory:
            report = campaign_report(directory)
            report['accounting']['model_calls'] = None
            report['accounting']['total_tokens'] = None
            rendered = render_campaign_html(report)
            self.assertNotIn('>None<', rendered)
            self.assertIn('unknown', rendered)
            self.assertIn('not that its task was accepted', rendered)

    def test_uninstalled_or_unsupported_harness_is_not_a_malformed_configuration(self):
        with tempfile.TemporaryDirectory(prefix='harness-admission-check-') as directory:
            root = Path(directory)
            source = root / 'harness.json'
            value = {'schema_version': 1, 'harness_id': 'fixture_harness', 'package_version': '1.0.0',
                     'command_prefix': [sys.executable], 'read_only_paths': [], 'style': 'unsupported_fixture'}
            source.write_text(json.dumps(value))
            binding = load_harness_binding(str(source), work_root=str(root / 'work'),
                                          socket_directory=str(root), allow_unavailable=True)
            info = binding.registry.get('fixture_harness').info()
            self.assertFalse(info.available)
            self.assertEqual(info.availability_reason, 'unsupported_style')
            with self.assertRaises(HarnessProcessError):
                load_harness_binding(str(source), work_root=str(root / 'work'), socket_directory=str(root))
            value['read_only_paths'] = ['/']
            source.write_text(json.dumps(value))
            with self.assertRaises(HarnessProcessError):
                load_harness_binding(str(source), work_root=str(root / 'work'),
                                     socket_directory=str(root), allow_unavailable=True)


if __name__ == '__main__':
    unittest.main()
