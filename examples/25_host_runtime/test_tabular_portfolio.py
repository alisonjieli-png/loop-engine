"""Focused offline tabular host checks; training/scoring only run in Docker."""
from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import tabular_portfolio as portfolio


def recipes(problem='classification'):
    linear = {'family': 'logistic', 'parameters': {'C': 1.0, 'max_iter': 500, 'class_weight': None}}
    if problem == 'regression':
        linear = {'family': 'ridge', 'parameters': {'alpha': 1.0}}
    return [{'family': 'dummy', 'parameters': {}}, linear,
            {'family': 'random_forest', 'parameters': {'n_estimators': 20, 'max_depth': 6,
                                                      'min_samples_leaf': 1, 'max_features': 'sqrt'}},
            {'family': 'hist_gradient_boosting', 'parameters': {'max_iter': 20, 'learning_rate': 0.1,
                'max_leaf_nodes': 7, 'min_samples_leaf': 3, 'l2_regularization': 1.0}}]


def fixture(directory, problem='classification'):
    path = directory / 'data.csv'
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['identifier', 'number', 'category', 'outcome'])
        for i in range(90):
            writer.writerow([i, '' if i % 11 == 0 else i, '' if i % 7 == 0 else 'cat-' + str(i % 13),
                             'label-' + str(i % 3) if problem == 'classification' else i * 2 + i % 3])
    config = directory / 'manifest.json'
    portfolio.write_json(config, {'dataset_csv': str(path), 'target': 'outcome',
        'problem_kind': problem, 'excluded_features': ['identifier']})
    return portfolio.load_manifest(config)


def train(root):
    from loop_engine.core.adaptive_host_runtime_checks import _services
    from loop_engine.core.host_runtime import (
        HostOperationRequest,
        invoke_host_operation,
        verify_host_result,
    )
    host, registry, profile = portfolio.make_host(root, portfolio.IMAGE)
    services, owner = _services(root / 'host-evidence', SimpleNamespace(binding=host))
    observed = invoke_host_operation(HostOperationRequest(host.operations[0].capability_ref, {}), services, owner)
    assert observed['value']['final_test_visible'] is False
    result = invoke_host_operation(HostOperationRequest(host.operations[1].capability_ref,
        {'candidates': recipes(profile['problem_kind'])}), services, owner)
    report = verify_host_result('Train the declared portfolio.', result, services, owner)
    assert report['status'] == 'passed' and report['task_complete'] is True
    return registry, profile


class PortfolioChecks(unittest.TestCase):
    def test_selection_metric_direction_is_explicit_and_supported(self):
        self.assertEqual(portfolio.selection_policy('classification'), ('log_loss', 'minimize'))
        self.assertEqual(portfolio.selection_policy('regression'), ('rmse', 'minimize'))
        self.assertEqual(portfolio.selection_policy('classification', 'roc_auc', 'maximize', 2),
                         ('roc_auc', 'maximize'))
        for args in (('regression', 'accuracy'), ('classification', 'roc_auc', 'maximize', 3),
                     ('regression', 'rmse', 'maximize'), ('regression', 'log_rmse')):
            with self.assertRaises(ValueError):
                portfolio.selection_policy(*args)
        candidates = {'first': {'validation_mean': {'accuracy': 0.8, 'rmse': 1}},
                      'second': {'validation_mean': {'accuracy': 0.9, 'rmse': 2}}}
        self.assertEqual(portfolio.select_candidate(candidates, {'direction': 'maximize', 'primary_metric': 'accuracy'}),
                         'second')
        self.assertEqual(portfolio.select_candidate(candidates, {'direction': 'minimize', 'primary_metric': 'rmse'}),
                         'first')

    def test_unknown_worker_exit_does_not_become_known_completion(self):
        failure = portfolio.WorkerFailure('fit', SimpleNamespace(
            exit_code=None, error_code='command_timeout', stderr='fixture'))
        self.assertFalse(failure.known_complete)

    def test_source_change_between_load_and_copy_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config = fixture(base)
            Path(config['dataset_csv']).write_text('changed\n')
            with self.assertRaisesRegex(ValueError, 'dataset changed'):
                portfolio.prepare(config, base / 'run', portfolio.IMAGE)

    def test_manifest_rejects_target_exclusion_and_boolean_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            fixture(base)
            config = portfolio.read_json(base / 'manifest.json')
            for index, changes in enumerate(({'excluded_features': ['outcome']}, {'split_seeds': [True, 2, 3]})):
                path = base / f'bad-{index}.json'
                portfolio.write_json(path, {**config, **changes})
                with self.assertRaises(ValueError):
                    portfolio.load_manifest(path)

    def test_real_classification_training_scoring_and_sealed_boundaries(self):
        with tempfile.TemporaryDirectory(prefix='loop-tabular-classification-test-') as directory:
            base, root = Path(directory), Path(directory) / 'run'
            portfolio.prepare(fixture(base), root, portfolio.IMAGE)
            split = portfolio.read_json(root / 'split-manifest.json')
            holdout = set(split['holdout_row_ids'])
            self.assertFalse(holdout & set(split['development_row_ids']))
            for fold in split['partitions']:
                self.assertFalse(holdout & set(fold['train_row_ids']))
                self.assertFalse(holdout & set(fold['validation_row_ids']))
                self.assertFalse(set(fold['train_row_ids']) & set(fold['validation_row_ids']))
            registry, profile = train(root)
            self.assertEqual(len(registry), 4)
            self.assertEqual({item['family'] for item in registry.values()},
                             {'dummy', 'logistic', 'random_forest', 'hist_gradient_boosting'})
            self.assertNotIn('identifier', [item['name'] for item in profile['features']])
            labels = root / 'sealed-holdout/holdout_labels.csv'
            original = labels.read_bytes()
            labels.write_bytes(original + b'changed\n')
            with self.assertRaisesRegex(ValueError, 'sealed holdout'):
                portfolio.final_evaluate(root, registry, profile, portfolio.IMAGE)
            labels.write_bytes(original)
            first = next(iter(registry.values()))
            pipeline = root / 'development-workspace' / first['artifact_root'] / 'pipeline-0.joblib'
            model_bytes = pipeline.read_bytes()
            pipeline.write_bytes(model_bytes + b'changed')
            with self.assertRaisesRegex(ValueError, 'estimator changed'):
                portfolio.final_evaluate(root, registry, profile, portfolio.IMAGE)
            # A failed freeze must not be silently reused; finish cleanly in a fresh
            # test workspace instead of deleting historical failure evidence.
            self.assertTrue((root / 'portfolio-freeze.json').is_file())

    def test_real_regression_final_evaluation_and_prediction_refusals(self):
        with tempfile.TemporaryDirectory(prefix='loop-tabular-regression-test-') as directory:
            base, root = Path(directory), Path(directory) / 'run'
            portfolio.prepare(fixture(base, 'regression'), root, portfolio.IMAGE)
            registry, profile = train(root)
            report = portfolio.final_evaluate(root, registry, profile, portfolio.IMAGE)
            self.assertEqual(len(report['per_fold']), 12)
            self.assertFalse((root / 'final-predictor/labels.csv').exists())
            self.assertFalse(list((root / 'final-scorer').glob('*.joblib')))
            self.assertFalse(report['used_for_model_feedback'])
            self.assertEqual(portfolio.read_json(root / 'portfolio-freeze.json')['selected_candidate_id'],
                             report['selected_before_test'])
            original = portfolio.read_json(root / 'final-scorer/predictions.json')
            cases = [[], original[:-1], original + [original[0]],
                     [{**original[0], 'candidate_id': 'unknown'}, *original[1:]],
                     [{**original[0], 'row_ids': list(reversed(original[0]['row_ids']))}, *original[1:]]]
            for index, bad in enumerate(cases):
                target = root / f'adversarial-scorer-{index}'
                target.mkdir()
                for name in ('worker.py', 'labels.csv', 'scoring_manifest.json'):
                    shutil.copyfile(root / 'final-scorer' / name, target / name)
                portfolio.write_json(target / 'predictions.json', bad)
                with self.assertRaises(portfolio.WorkerFailure):
                    portfolio.run_worker(target, portfolio.IMAGE, 'score')
                self.assertFalse((target / 'test-report.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
