"""Independent offline checks for typed competition prediction formatting.

No model, network, or Docker execution is involved. Fixtures establish exact
identifier coverage, target vocabulary, probability interpretation, and writes.
"""
from __future__ import annotations

import copy
import csv
import tempfile
import unittest
from pathlib import Path

import competition_prediction as competition


def config(kind='label', **changes):
    value = {
        'id_column': 'id', 'target_column': 'outcome', 'prediction_kind': kind,
        'schemas': {'submission_columns': ['id', 'outcome']},
        'template_ids': ['003', '001', '002'],
        'test_ids': ['001', '002', '003'],
    }
    value.update(changes)
    return value


def predictions(values=None, **changes):
    value = {'row_ids': ['002', '003', '001'], 'classes': ['no', 'yes'],
             'predictions': ['yes', 'no', 'yes'] if values is None else values}
    value.update(changes)
    return value


class CompetitionPredictionChecks(unittest.TestCase):
    def _format(self, request, rows, classes):
        with tempfile.TemporaryDirectory(prefix='competition-format-') as directory:
            destination = Path(directory) / 'submission.csv'
            result = competition.format_submission(request, rows, classes, destination)
            self.assertIsInstance(result, dict)
            self.assertTrue(destination.is_file())
            with destination.open(newline='', encoding='utf-8') as stream:
                reader = csv.DictReader(stream)
                return reader.fieldnames, list(reader)

    def _refuses(self, request, rows, classes):
        with tempfile.TemporaryDirectory(prefix='competition-refusal-') as directory:
            destination = Path(directory) / 'submission.csv'
            with self.assertRaises((ValueError, TypeError)):
                competition.format_submission(request, rows, classes, destination)
            self.assertFalse(destination.exists(), 'invalid predictions left a partial submission')

    def test_labels_follow_template_order_and_keep_leading_zero_ids(self):
        header, rows = self._format(config(), predictions(), ['no', 'yes'])
        self.assertEqual(header, ['id', 'outcome'])
        self.assertEqual(rows, [
            {'id': '003', 'outcome': 'no'},
            {'id': '001', 'outcome': 'yes'},
            {'id': '002', 'outcome': 'yes'},
        ])

    def test_boolean_competition_labels_keep_the_training_vocabulary(self):
        request = config(target_column='Transported',
                         schemas={'submission_columns': ['id', 'Transported']})
        _, rows = self._format(request, predictions(
            ['True', 'False', 'True'], classes=['False', 'True']), ['False', 'True'])
        self.assertEqual([row['Transported'] for row in rows], ['False', 'True', 'True'])

    def test_regression_predictions_are_aligned_by_id_not_position(self):
        header, rows = self._format(
            config('regression'), predictions([20.5, -3.25, 100], classes=None), [])
        self.assertEqual(header, ['id', 'outcome'])
        self.assertEqual([float(row['outcome']) for row in rows], [-3.25, 100.0, 20.5])

    def test_positive_probability_uses_explicit_positive_class(self):
        _, rows = self._format(
            config('positive_probability', positive_label='yes'),
            predictions([[0.9, 0.1], [0.2, 0.8], [0.7, 0.3]], classes=['yes', 'no']),
            ['no', 'yes'])
        self.assertEqual([float(row['outcome']) for row in rows], [0.2, 0.7, 0.9])

    def test_multiclass_probability_columns_have_explicit_class_mapping(self):
        request = config('class_probabilities', target_column='author',
                         schemas={'submission_columns': ['id', 'MWS', 'EAP', 'HPL']},
                         column_class_map={'MWS': 'Mary', 'EAP': 'Edgar', 'HPL': 'Howard'})
        header, rows = self._format(request, predictions(
            [[0.3, 0.2, 0.5], [0.1, 0.6, 0.3], [0.8, 0.1, 0.1]],
            classes=['Mary', 'Edgar', 'Howard']), ['Edgar', 'Howard', 'Mary'])
        self.assertEqual(header, ['id', 'MWS', 'EAP', 'HPL'])
        self.assertEqual([float(rows[0][column]) for column in header[1:]], [0.1, 0.6, 0.3])
        self.assertEqual([row['id'] for row in rows], ['003', '001', '002'])

    def test_duplicate_missing_extra_or_nonstring_prediction_ids_are_refused(self):
        cases = [
            predictions(row_ids=['001', '001', '003']),
            predictions(['no', 'yes'], row_ids=['001', '002']),
            predictions(row_ids=['001', '002', 'elsewhere']),
            predictions(row_ids=['001', '002', 3]),
        ]
        for case in cases:
            with self.subTest(case=case):
                self._refuses(config(), case, ['no', 'yes'])

    def test_template_and_test_identifier_contract_must_agree(self):
        cases = [
            config(template_ids=['001', '001', '003']),
            config(test_ids=['001', '002', '002']),
            config(template_ids=['001', '002', '004']),
            config(template_ids=[]),
        ]
        for case in cases:
            with self.subTest(case=case):
                self._refuses(case, predictions(), ['no', 'yes'])

    def test_wrong_prediction_count_and_unknown_labels_are_refused_before_write(self):
        for values in (['no'], ['no', 'yes', 'unknown'], ['no', 'yes', None]):
            with self.subTest(values=values):
                self._refuses(config(), predictions(values), ['no', 'yes'])

    def test_nonfinite_regression_values_are_refused(self):
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.subTest(value=value):
                self._refuses(config('regression'), predictions([1, 2, value], classes=None), [])

    def test_probability_shape_range_sum_and_finiteness_are_checked(self):
        bad_vectors = ([0.8], [0.8, 0.2, 0.0], [-0.1, 1.1], [0.4, 0.4],
                       [float('nan'), 0.5], [float('inf'), 0.0])
        for row in bad_vectors:
            with self.subTest(row=row):
                self._refuses(config('positive_probability', positive_label='yes'),
                              predictions([[0.2, 0.8], [0.9, 0.1], row]), ['no', 'yes'])

    def test_probability_class_identity_cannot_be_missing_duplicated_or_invented(self):
        for classes in (None, ['no', 'no'], ['no', 'other'], ['yes']):
            with self.subTest(classes=classes):
                self._refuses(config('positive_probability', positive_label='yes'),
                              predictions([[0.2, 0.8]] * 3, classes=classes), ['no', 'yes'])
        self._refuses(config('positive_probability', positive_label='unknown'),
                      predictions([[0.2, 0.8]] * 3), ['no', 'yes'])

    def test_multiclass_mapping_is_complete_and_unambiguous(self):
        request = config('class_probabilities', target_column='author',
                         schemas={'submission_columns': ['id', 'a', 'b']},
                         column_class_map={'a': 'no', 'b': 'yes'})
        for mapping in ({'a': 'no'}, {'a': 'no', 'b': 'no'}, {'a': 'no', 'b': 'other'}):
            with self.subTest(mapping=mapping):
                self._refuses({**request, 'column_class_map': mapping},
                              predictions([[0.2, 0.8]] * 3), ['no', 'yes'])

    def test_submission_headers_cannot_repeat_or_omit_the_identifier(self):
        for columns in (['id', 'id'], ['outcome'], ['other', 'outcome']):
            with self.subTest(columns=columns):
                self._refuses(config(schemas={'submission_columns': columns}),
                              predictions(), ['no', 'yes'])

    def test_formatting_preserves_inputs_and_refuses_overwriting_prior_output(self):
        request, rows = config(), predictions()
        originals = copy.deepcopy((request, rows))
        self._format(request, rows, ['no', 'yes'])
        self.assertEqual((request, rows), originals)
        with tempfile.TemporaryDirectory(prefix='competition-existing-') as directory:
            destination = Path(directory) / 'submission.csv'
            destination.write_text('previous output\n', encoding='utf-8')
            with self.assertRaises((FileExistsError, ValueError)):
                competition.format_submission(request, rows, ['no', 'yes'], destination)
            self.assertEqual(destination.read_text(), 'previous output\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
