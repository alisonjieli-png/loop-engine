"""Refit a frozen validation-selected recipe and create a checked competition CSV.

This post-solve host operation makes no model or Kaggle calls. It keeps the
earlier holdout evaluation separate from a new full-labeled-data estimator.
Training and prediction use separate pinned Docker workspaces; no persisted
estimator is deserialized in the controller or in the CSV formatter.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

import tabular_portfolio as portfolio

SOURCE_KEYS = ('portfolio_freeze', 'local_evaluation', 'training_csv', 'test_csv', 'sample_submission_csv')
KINDS = ('label', 'positive_probability', 'regression', 'class_probabilities')


def _json(path):
    def invalid(_value):
        raise ValueError('nonfinite JSON value')
    return json.loads(Path(path).read_text(), parse_constant=invalid)


def _csv(path):
    with Path(path).open(newline='', encoding='utf-8') as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
        if not header or len(header) != len(set(header)):
            raise ValueError('CSV header is empty or duplicated')
        rows = list(reader)
    if any(len(row) != len(header) for row in rows):
        raise ValueError('CSV has inconsistent row widths')
    return header, rows


def _identifiers(header, rows, column):
    if column not in header:
        raise ValueError('identifier is absent from the declared table')
    values = [row[header.index(column)] for row in rows]
    if not values or any(not value for value in values) or len(set(values)) != len(values):
        raise ValueError('identifiers must be nonempty and unique')
    return values


def _plain_file(path):
    value = Path(path)
    if (not value.is_absolute() or not value.is_file()
            or any(part.is_symlink() for part in (value, *value.parents))):
        raise ValueError('source must be an absolute regular file without symlinks')
    return value


def load_request(path):
    from jsonschema import Draft202012Validator
    value = _json(path)
    properties = {key: {'type': 'string', 'minLength': 1} for key in SOURCE_KEYS}
    properties.update({
        'record_type': {'const': 'competition_prediction_request/v1'},
        'source_hashes': portfolio.object_schema({key: {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
                                                for key in SOURCE_KEYS}, SOURCE_KEYS),
        'id_column': {'type': 'string', 'minLength': 1},
        'target_column': {'type': 'string', 'minLength': 1},
        'feature_columns': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                            'items': {'type': 'string', 'minLength': 1}},
        'problem_kind': {'enum': ['classification', 'regression']},
        'prediction_kind': {'enum': list(KINDS)},
        'positive_label': {'type': 'string'},
        'column_class_map': {'type': 'object', 'additionalProperties': {'type': 'string'}},
        'refit_seed': {'type': 'integer', 'minimum': 0, 'maximum': 2 ** 32 - 1},
        'schemas': portfolio.object_schema({key: {'type': 'array', 'minItems': 1, 'uniqueItems': True,
            'items': {'type': 'string', 'minLength': 1}} for key in (
                'training_columns', 'test_columns', 'submission_columns')},
            ('training_columns', 'test_columns', 'submission_columns'))})
    required = (*SOURCE_KEYS, 'record_type', 'source_hashes', 'id_column', 'target_column',
                'feature_columns', 'problem_kind', 'prediction_kind', 'refit_seed', 'schemas')
    Draft202012Validator(portfolio.object_schema(properties, required)).validate(value)
    for key in SOURCE_KEYS:
        if portfolio.file_digest(_plain_file(value[key])) != value['source_hashes'][key]:
            raise ValueError('source digest mismatch: ' + key)
    if (value['prediction_kind'] == 'regression') != (value['problem_kind'] == 'regression'):
        raise ValueError('prediction kind and problem kind disagree')
    if value['prediction_kind'] == 'positive_probability' and 'positive_label' not in value:
        raise ValueError('positive probability output requires an explicit positive_label')
    train_header, _ = _csv(value['training_csv'])
    test_header, test_rows = _csv(value['test_csv'])
    sample_header, sample_rows = _csv(value['sample_submission_csv'])
    for observed, key in ((train_header, 'training_columns'), (test_header, 'test_columns'),
                          (sample_header, 'submission_columns')):
        if observed != value['schemas'][key]:
            raise ValueError('actual columns differ from declared schema: ' + key)
    identifier, target = value['id_column'], value['target_column']
    features = value['feature_columns']
    if (identifier == target or target not in train_header or target in test_header
            or {identifier, target} & set(features)
            or not set(features) <= set(train_header) or not set(features) <= set(test_header)):
        raise ValueError('identifier, target, or feature-role contract is inconsistent')
    test_ids = _identifiers(test_header, test_rows, identifier)
    template_ids = _identifiers(sample_header, sample_rows, identifier)
    if set(test_ids) != set(template_ids):
        raise ValueError('test and template identifier sets differ')
    output_columns = [name for name in sample_header if name != identifier]
    if value['prediction_kind'] == 'class_probabilities':
        if set(value.get('column_class_map', {})) != set(output_columns):
            raise ValueError('class probability map must cover every output column exactly')
    elif output_columns != [target]:
        raise ValueError('single-output submission must contain exactly identifier and target')
    frozen = _json(value['portfolio_freeze'])
    if (frozen.get('record_type') != 'tabular_portfolio_freeze/v1'
            or frozen.get('test_results_used_for_selection') is not False):
        raise ValueError('a validation-only frozen portfolio is required')
    candidates, selected = frozen['candidates'], frozen['selected_candidate_id']
    if selected not in candidates or not candidates:
        raise ValueError('frozen winner is missing')
    metric, direction = portfolio.selection_policy(value['problem_kind'], frozen['selection_metric'],
                                                   frozen['selection_direction'])
    winner = portfolio.select_candidate(candidates, {'primary_metric': metric, 'direction': direction})
    if selected != winner:
        raise ValueError('frozen selection does not follow its validation metric')
    candidate = candidates[selected]
    Draft202012Validator(portfolio.candidate_schema(value['problem_kind'])).validate(candidate['spec'])
    if portfolio.digest(candidate['spec']) != selected:
        raise ValueError('winner identity differs from its exact recipe')
    evaluation = _json(value['local_evaluation'])
    if (evaluation.get('record_type') != 'frozen_tabular_holdout_evaluation/v1'
            or evaluation.get('selected_before_test') != selected
            or evaluation.get('used_for_model_feedback') is not False
            or evaluation.get('freeze_digest') != value['source_hashes']['portfolio_freeze']):
        raise ValueError('prior local evaluation does not bind the frozen selection')
    return {**value, 'test_ids': test_ids, 'template_ids': template_ids,
            'selected_candidate_id': selected, 'selected_spec': candidate['spec'],
            'expected_versions': candidate['versions']}


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('predictions must be finite JSON numbers')
    return value


def format_submission(config, predictions, training_classes, destination):
    """Validate every prediction before writing; join lexical IDs to template order."""
    identifier, target, kind = config['id_column'], config['target_column'], config['prediction_kind']
    columns = config['schemas']['submission_columns']
    if (kind not in KINDS or not isinstance(columns, list)
            or any(type(name) is not str or not name for name in columns)
            or len(columns) != len(set(columns)) or columns.count(identifier) != 1
            or identifier == target or len(columns) < 2):
        raise ValueError('submission header or prediction kind is invalid')
    if kind != 'class_probabilities' and set(columns) != {identifier, target}:
        raise ValueError('single-output header must contain exactly identifier and target')
    row_ids, values = predictions.get('row_ids'), predictions.get('predictions')
    if (not isinstance(row_ids, list) or any(type(value) is not str or not value for value in row_ids)
            or not row_ids or len(row_ids) != len(set(row_ids)) or set(row_ids) != set(config['test_ids'])
            or not isinstance(values, list) or len(values) != len(row_ids)
            or len(config['template_ids']) != len(set(config['template_ids']))
            or set(config['template_ids']) != set(config['test_ids'])):
        raise ValueError('prediction or template identifier coverage is invalid')
    classes = predictions.get('classes')
    if kind != 'regression':
        if (not isinstance(classes, list) or any(type(label) is not str for label in classes)
                or len(classes) != len(set(classes)) or set(classes) != set(training_classes)):
            raise ValueError('prediction classes differ from training label vocabulary')
    if kind == 'positive_probability' and config.get('positive_label') not in classes:
        raise ValueError('positive_label is absent from estimator classes')
    output_columns = [column for column in columns if column != identifier]
    mapping = config.get('column_class_map', {})
    if kind == 'class_probabilities' and (set(mapping) != set(output_columns)
            or len(set(mapping.values())) != len(mapping) or set(mapping.values()) != set(classes)):
        raise ValueError('class probability columns must map one-to-one to all classes')
    converted = {}
    for row_id, prediction in zip(row_ids, values):
        if kind == 'regression':
            row = {target: _number(prediction)}
        elif kind == 'label':
            if type(prediction) is not str or prediction not in training_classes:
                raise ValueError('predicted label is outside the training vocabulary')
            row = {target: prediction}
        else:
            if not isinstance(prediction, list) or len(prediction) != len(classes):
                raise ValueError('probability vector has incorrect class width')
            probabilities = [_number(value) for value in prediction]
            if any(not 0 <= value <= 1 for value in probabilities) or not math.isclose(sum(probabilities), 1, abs_tol=1e-8):
                raise ValueError('probability values or their row sum are invalid')
            row = ({target: probabilities[classes.index(config['positive_label'])]}
                   if kind == 'positive_probability' else
                   {column: probabilities[classes.index(label)] for column, label in mapping.items()})
        converted[row_id] = {identifier: row_id, **row}
    output = [[converted[row_id][name] for name in columns] for row_id in config['template_ids']]
    with Path(destination).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(output)
    header, rows = _csv(destination)
    if header != columns or _identifiers(header, rows, identifier) != config['template_ids']:
        raise ValueError('written submission did not preserve its contract')
    return {'rows': len(rows), 'columns': columns, 'prediction_kind': kind,
            'identifier_digest': portfolio.digest(config['template_ids']),
            'submission_sha256': portfolio.file_digest(destination)}


def _copy(source, destination, expected):
    if portfolio.file_digest(_plain_file(source)) != expected:
        raise ValueError('source changed before copy')
    shutil.copyfile(source, destination)
    if portfolio.file_digest(destination) != expected:
        raise ValueError('source changed during copy')


def _worker_train():
    import joblib
    import numpy as np
    import pandas as pd
    config = _json('job.json')
    if portfolio._versions() != config['expected_versions']:
        raise ValueError('refit library versions differ from the evaluated candidate')
    if portfolio.file_digest('training.csv') != config['training_digest']:
        raise ValueError('refit training source digest differs')
    dtypes = {config['id_column']: str}
    if config['problem_kind'] == 'classification':
        dtypes[config['target_column']] = str
    frame = pd.read_csv('training.csv', dtype=dtypes)
    y = frame[config['target_column']]
    if y.isna().any():
        raise ValueError('refit training target has missing values')
    if config['problem_kind'] == 'regression':
        y = pd.to_numeric(y, errors='raise')
        if not np.isfinite(y).all():
            raise ValueError('refit regression target is not finite')
    x = frame[config['feature_columns']].replace([np.inf, -np.inf], np.nan)
    pipeline = portfolio._pipeline(config['spec'], x, config['problem_kind'], config['refit_seed'])
    pipeline.fit(x, y)
    joblib.dump(pipeline, 'pipeline.joblib')
    portfolio.write_json('training-report.json', {'training_rows': len(frame), 'features': config['feature_columns'],
        'classes': pipeline.classes_.tolist() if config['problem_kind'] == 'classification' else [],
        'pipeline_digest': portfolio.file_digest('pipeline.joblib'), 'versions': portfolio._versions(),
        'fit_scope': 'all_labeled_rows_after_frozen_local_evaluation'})
    print(json.dumps({'ok': True, 'training_rows': len(frame)}))


def _worker_predict():
    import joblib
    import numpy as np
    import pandas as pd
    config = _json('job.json')
    if portfolio.file_digest('pipeline.joblib') != config['pipeline_digest']:
        raise ValueError('refitted pipeline digest changed')
    if portfolio.file_digest('test.csv') != config['test_digest']:
        raise ValueError('competition test source digest changed')
    frame = pd.read_csv('test.csv', dtype={config['id_column']: str})
    pipeline = joblib.load('pipeline.joblib')
    x = frame[config['feature_columns']].replace([np.inf, -np.inf], np.nan)
    kind = config['prediction_kind']
    predicted = pipeline.predict_proba(x) if kind in ('positive_probability', 'class_probabilities') else pipeline.predict(x)
    portfolio.write_json('predictions.json', {'row_ids': frame[config['id_column']].tolist(),
        'classes': pipeline.classes_.tolist() if kind != 'regression' else None,
        'predictions': predicted.tolist()})
    print(json.dumps({'ok': True, 'prediction_rows': len(frame)}))


def _execute(root, image, operation):
    from loop_engine.core.workspace_backends import CommandRequest
    result = portfolio.backend(root, image).command(CommandRequest(
        ('python', 'competition_prediction.py', '_worker', operation), execution_authorized=True,
        timeout_seconds=600, max_output_bytes=1024 * 1024))
    if not result.ok or result.output_truncated:
        raise portfolio.WorkerFailure(operation, result)
    return {'argv': list(result.argv), 'exit_code': result.exit_code, 'stdout': result.stdout,
            'stderr': result.stderr, 'image': image, 'network': False, 'host_fallback': False}


def execute_prediction(config, root, image=portfolio.IMAGE):
    root = Path(root)
    if root.exists():
        raise ValueError('output directory must be new; historical evidence is not overwritten')
    root.mkdir(parents=True, mode=0o700)
    train, predict = root / 'full-data-refit', root / 'competition-predictor'
    train.mkdir(mode=0o700)
    predict.mkdir(mode=0o700)
    worker_sources = {Path(__file__).resolve(): 'competition_prediction.py',
                      Path(portfolio.__file__).resolve(): 'tabular_portfolio.py'}
    worker_hashes = {name: portfolio.file_digest(path) for path, name in worker_sources.items()}
    for directory in (train, predict):
        for source, name in worker_sources.items():
            _copy(source, directory / name, worker_hashes[name])
    for key in SOURCE_KEYS:
        if portfolio.file_digest(_plain_file(config[key])) != config['source_hashes'][key]:
            raise ValueError('submission source binding changed: ' + key)
    _copy(config['training_csv'], train / 'training.csv', config['source_hashes']['training_csv'])
    portfolio.write_json(train / 'job.json', {'spec': config['selected_spec'],
        'training_digest': config['source_hashes']['training_csv'], 'problem_kind': config['problem_kind'],
        'id_column': config['id_column'], 'target_column': config['target_column'],
        'feature_columns': config['feature_columns'], 'refit_seed': config['refit_seed'],
        'expected_versions': config['expected_versions']})
    training_execution = _execute(train, image, 'train')
    training = _json(train / 'training-report.json')
    _copy(train / 'pipeline.joblib', predict / 'pipeline.joblib', training['pipeline_digest'])
    _copy(config['test_csv'], predict / 'test.csv', config['source_hashes']['test_csv'])
    portfolio.write_json(predict / 'job.json', {'pipeline_digest': training['pipeline_digest'],
        'test_digest': config['source_hashes']['test_csv'], 'id_column': config['id_column'],
        'feature_columns': config['feature_columns'], 'prediction_kind': config['prediction_kind']})
    prediction_execution = _execute(predict, image, 'predict')
    reading = format_submission(config, _json(predict / 'predictions.json'), training['classes'], root / 'submission.csv')
    receipt = {'record_type': 'competition_prediction_receipt/v1', **reading,
        'selected_candidate_id': config['selected_candidate_id'], 'selected_spec': config['selected_spec'],
        'source_hashes': config['source_hashes'], 'worker_hashes': worker_hashes,
        'training': training, 'training_execution': training_execution, 'prediction_execution': prediction_execution,
        'local_evaluation_scope': 'previously_frozen_holdout_models_not_this_full_data_refit',
        'selection_uses_competition_test': False, 'model_calls': 0, 'network_calls': 0,
        'submitted_to_kaggle': False, 'prediction_workspace_has_training_labels': False,
        'controller_loaded_pickle': False}
    portfolio.write_json(root / 'submission-receipt.json', receipt)
    return receipt


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '_worker':
        for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
            os.environ[variable] = '1'
        {'train': _worker_train, 'predict': _worker_predict}[sys.argv[2]]()
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--image', default=portfolio.IMAGE)
    parser.add_argument('--authorize-local-compute', action='store_true')
    args = parser.parse_args()
    if not args.authorize_local_compute:
        parser.error('--authorize-local-compute is required; no network submission is performed')
    receipt = execute_prediction(load_request(args.manifest), Path(args.output_dir).resolve(), args.image)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
