"""Generic tabular host portfolio with a sealed holdout and a pinned ML worker.

Only the host-controlled sklearn specification is executable. Models choose
families and parameters, never worker code, file paths, split membership, or
test observations. Public dataset acquisition precedes this example.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

IMAGE = 'loop-engine-ds1000-runtime@sha256:d29a0fedd17671510b759b15f276b73ee9ba813868653d8923c7365482ee328d'
ROW = '__loop_row_id__'
TARGET = '__loop_target__'
SEEDS = (1729, 1730, 1731)
FRACTIONS = {'train': 0.6, 'validation': 0.2, 'test': 0.2}
METRICS = {'classification': {'log_loss': 'minimize', 'accuracy': 'maximize', 'roc_auc': 'maximize'},
           'regression': {'rmse': 'minimize', 'mae': 'minimize', 'r2': 'maximize'}}


def selection_policy(problem, metric=None, direction=None, class_count=None):
    metric = metric if metric is not None else ('log_loss' if problem == 'classification' else 'rmse')
    if not isinstance(metric, str) or metric not in METRICS.get(problem, {}):
        raise ValueError('selection metric is unsupported for this problem kind')
    expected = METRICS[problem][metric]
    if direction is not None and direction != expected:
        raise ValueError('selection direction contradicts the declared measured metric')
    if metric == 'roc_auc' and class_count is not None and class_count != 2:
        raise ValueError('ROC-AUC selection currently requires binary classification')
    return metric, expected


def select_candidate(registry, profile):
    if profile['direction'] not in ('minimize', 'maximize'):
        raise ValueError('unknown selection direction')
    chooser = min if profile['direction'] == 'minimize' else max
    return chooser(registry, key=lambda key: registry[key]['validation_mean'][profile['primary_metric']])


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(encoded(value) + b'\n')


def read_json(path):
    return json.loads(Path(path).read_text())


def object_schema(properties, required=()):
    return {'type': 'object', 'properties': properties, 'required': list(required),
            'additionalProperties': False}


def candidate_schema(problem):
    positive = {'type': 'number', 'exclusiveMinimum': 0}
    integer = {'type': 'integer', 'minimum': 1}
    depth = {'anyOf': [integer, {'type': 'null'}]}
    families = {
        'dummy': {},
        'random_forest': {'n_estimators': integer, 'max_depth': depth,
                          'min_samples_leaf': integer,
                          'max_features': {'anyOf': [{'enum': ['sqrt', 'log2']},
                              {'type': 'number', 'exclusiveMinimum': 0, 'maximum': 1}, {'type': 'null'}]}},
        'hist_gradient_boosting': {'max_iter': integer, 'learning_rate': positive,
                                  'max_leaf_nodes': {'type': 'integer', 'minimum': 2},
                                  'min_samples_leaf': integer, 'l2_regularization': {'type': 'number', 'minimum': 0}},
    }
    linear = 'logistic' if problem == 'classification' else 'ridge'
    families[linear] = ({'C': positive, 'max_iter': integer,
                         'class_weight': {'enum': [None, 'balanced']}}
                        if problem == 'classification' else {'alpha': {'type': 'number', 'minimum': 0}})
    return {'oneOf': [object_schema({'family': {'const': name},
                                    'parameters': object_schema(parameters, tuple(parameters))},
                                   ('family', 'parameters')) for name, parameters in families.items()]}


def load_manifest(path):
    value = read_json(path)
    required = {'dataset_csv', 'target', 'problem_kind', 'excluded_features'}
    if not required <= set(value) or value['problem_kind'] not in ('classification', 'regression'):
        raise ValueError('manifest needs dataset_csv, target, problem_kind, excluded_features')
    source = Path(value['dataset_csv'])
    if source.is_symlink() or not source.is_file():
        raise ValueError('dataset_csv must be an existing regular file, not a symlink')
    expected = value.get('source', {}).get('csv_sha256')
    if expected and file_digest(source) != expected:
        raise ValueError('downloaded CSV digest differs from its provenance')
    with source.open(newline='', encoding='utf-8') as stream:
        columns = next(csv.reader(stream))
    if len(set(columns)) != len(columns) or ROW in columns or TARGET in columns:
        raise ValueError('duplicate or reserved source columns')
    excluded = value['excluded_features']
    if (not isinstance(excluded, list) or len(set(excluded)) != len(excluded)
            or any(name not in columns for name in excluded)
            or value['target'] not in columns or value['target'] in excluded):
        raise ValueError('target and excluded_features must name distinct existing columns')
    seeds = value.get('split_seeds', list(SEEDS))
    fractions = value.get('split_fractions', FRACTIONS)
    if (not isinstance(seeds, list) or len(seeds) != 3 or len(set(seeds)) != 3
            or any(type(seed) is not int or not 0 <= seed < 2 ** 32 for seed in seeds)):
        raise ValueError('split_seeds must contain three distinct uint32 integers')
    if (not isinstance(fractions, dict) or set(fractions) != set(FRACTIONS)
            or any(type(x) not in (int, float) or not math.isfinite(x) or not 0 < x < 1
                   for x in fractions.values()) or not math.isclose(sum(fractions.values()), 1.0)):
        raise ValueError('train/validation/test fractions must be positive and sum to one')
    metric, direction = selection_policy(value['problem_kind'], value.get('selection_metric'),
                                         value.get('selection_direction'))
    return {**value, 'dataset_csv': str(source.resolve()), 'dataset_digest': file_digest(source),
            'selection_metric': metric, 'selection_direction': direction,
            'split_seeds': seeds, 'split_fractions': fractions}


def _versions():
    import joblib
    import numpy
    import pandas
    import sklearn
    return {'numpy': numpy.__version__, 'pandas': pandas.__version__,
            'sklearn': sklearn.__version__, 'joblib': joblib.__version__}


def _read_frame(path):
    import pandas as pd
    return pd.read_csv(path, dtype={ROW: str})


def _prepare_worker():
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split
    config = read_json('config.json')
    frame = pd.read_csv('dataset.csv')
    y = frame[config['target']]
    if y.isna().any():
        raise ValueError('labeled source contains missing target values')
    y = y.astype(str) if config['problem_kind'] == 'classification' else pd.to_numeric(y, errors='raise')
    if config['problem_kind'] == 'regression' and not np.isfinite(y).all():
        raise ValueError('regression target must be finite')
    features = frame.drop(columns=[config['target'], *config['excluded_features']]).copy()
    if not len(features.columns):
        raise ValueError('no features remain after explicit exclusions')
    features.insert(0, ROW, [str(i) for i in range(len(frame))])
    labeled = features.copy()
    labeled[TARGET] = y
    index = np.arange(len(frame))
    stratify = y if config['problem_kind'] == 'classification' else None
    development, test = train_test_split(index, test_size=config['split_fractions']['test'],
        random_state=config['split_seeds'][0], stratify=stratify)
    dev = labeled.iloc[development].reset_index(drop=True)
    dev.to_csv('development.csv', index=False)
    features.iloc[test].to_csv('holdout_features.csv', index=False)
    labeled.iloc[test][[ROW, TARGET]].to_csv('holdout_labels.csv', index=False)
    ratio = config['split_fractions']['validation'] / (1 - config['split_fractions']['test'])
    partitions = []
    for seed in config['split_seeds']:
        train, validation = train_test_split(np.arange(len(dev)), test_size=ratio,
            random_state=seed, stratify=dev[TARGET] if config['problem_kind'] == 'classification' else None)
        partitions.append({'seed': seed, 'train': train.tolist(), 'validation': validation.tolist(),
                           'train_row_ids': dev.iloc[train][ROW].tolist(),
                           'validation_row_ids': dev.iloc[validation][ROW].tolist()})
    write_json('development_splits.json', partitions)
    classes = sorted(dev[TARGET].unique().tolist()) if config['problem_kind'] == 'classification' else []
    metric, direction = selection_policy(config['problem_kind'], config.get('selection_metric'),
                                         config.get('selection_direction'), len(classes))
    profile = {'record_type': 'tabular_development_profile/v1', 'problem_kind': config['problem_kind'],
               'development_rows': len(dev), 'holdout_rows': len(test), 'feature_count': len(features.columns) - 1,
               'features': [{'name': name, 'dtype': str(dev[name].dtype),
                             'missing': int(dev[name].isna().sum()), 'unique': int(dev[name].nunique())}
                            for name in features.columns if name != ROW],
               'classes': classes, 'excluded_features': config['excluded_features'],
               'target': config['target'], 'versions': _versions(),
               'primary_metric': metric, 'direction': direction,
               'split_seeds': config['split_seeds'], 'split_fractions': config['split_fractions']}
    write_json('profile.json', profile)
    write_json('split_manifest.json', {'dataset_digest': config['dataset_digest'],
        'development_row_ids': dev[ROW].tolist(), 'holdout_row_ids': features.iloc[test][ROW].tolist(),
        'partitions': partitions, 'classes': classes, 'global_holdout_shared_across_repetitions': True})
    print(json.dumps({'ok': True, 'development_rows': len(dev), 'holdout_rows': len(test)}))


def _pipeline(spec, frame, problem, seed):
    from sklearn.compose import ColumnTransformer
    from sklearn.dummy import DummyClassifier, DummyRegressor
    from sklearn.ensemble import (
        HistGradientBoostingClassifier,
        HistGradientBoostingRegressor,
        RandomForestClassifier,
        RandomForestRegressor,
    )
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    numeric = [name for name in frame.columns if frame[name].dtype.kind in 'biufc']
    categorical = [name for name in frame.columns if name not in numeric]
    preprocessing = ColumnTransformer([
        ('numeric', Pipeline([('imputer', SimpleImputer(strategy='median', keep_empty_features=True)),
                              ('scale', StandardScaler())]), numeric),
        ('categorical', Pipeline([('imputer', SimpleImputer(strategy='most_frequent', keep_empty_features=True)),
                                  ('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False))]), categorical)])
    family, parameters = spec['family'], dict(spec['parameters'])
    if family == 'dummy':
        estimator = DummyClassifier(strategy='prior') if problem == 'classification' else DummyRegressor(strategy='mean')
    elif family == 'logistic':
        estimator = LogisticRegression(**parameters, solver='lbfgs', random_state=seed)
    elif family == 'ridge':
        estimator = Ridge(**parameters, solver='lsqr')
    elif family == 'random_forest':
        cls = RandomForestClassifier if problem == 'classification' else RandomForestRegressor
        estimator = cls(**parameters, random_state=seed, n_jobs=1)
    else:
        cls = HistGradientBoostingClassifier if problem == 'classification' else HistGradientBoostingRegressor
        estimator = cls(**parameters, random_state=seed, early_stopping=False)
    return Pipeline([('preprocess', preprocessing), ('estimator', estimator)])


def _metrics(problem, labels, prediction, classes=None):
    import numpy as np
    from sklearn.metrics import (
        accuracy_score,
        log_loss,
        mean_absolute_error,
        mean_squared_error,
        r2_score,
        roc_auc_score,
    )
    if problem == 'regression':
        values = np.asarray(prediction, dtype=float)
        if values.shape != (len(labels),) or not np.isfinite(values).all():
            raise ValueError('invalid regression predictions')
        return {'rmse': float(np.sqrt(mean_squared_error(labels, values))),
                'mae': float(mean_absolute_error(labels, values)), 'r2': float(r2_score(labels, values))}
    values = np.asarray(prediction, dtype=float)
    if (values.shape != (len(labels), len(classes)) or not np.isfinite(values).all()
            or (values < 0).any() or (values > 1).any() or not np.allclose(values.sum(axis=1), 1)):
        raise ValueError('invalid classification probabilities')
    guessed = np.asarray(classes)[values.argmax(axis=1)]
    result = {'log_loss': float(log_loss(labels, values, labels=classes)),
              'accuracy': float(accuracy_score(labels, guessed))}
    if len(classes) == 2:
        result['roc_auc'] = float(roc_auc_score(np.asarray(labels) == classes[1], values[:, 1]))
    return result


def _fit_worker(candidate_id):
    import joblib
    import numpy as np
    spec = read_json(Path('candidates') / candidate_id / 'spec.json')
    profile = read_json('profile.json')
    data = _read_frame('development.csv')
    problem = profile['problem_kind']
    y = data[TARGET].astype(str) if problem == 'classification' else data[TARGET]
    x = data.drop(columns=[ROW, TARGET])
    x = x.replace([np.inf, -np.inf], np.nan)
    partitions = read_json('development_splits.json')
    output = Path('candidates') / candidate_id
    reports = []
    for index, partition in enumerate(partitions):
        train, validation = partition['train'], partition['validation']
        pipeline = _pipeline(spec, x.iloc[train], problem, partition['seed'])
        pipeline.fit(x.iloc[train], y.iloc[train])
        classes = pipeline.classes_.tolist() if problem == 'classification' else None
        values = (pipeline.predict_proba(x.iloc[validation]) if classes is not None
                  else pipeline.predict(x.iloc[validation]))
        metrics = _metrics(problem, y.iloc[validation], values, classes)
        joblib.dump(pipeline, output / f'pipeline-{index}.joblib')
        predictions = {'row_ids': data.iloc[validation][ROW].astype(str).tolist(),
                       'classes': classes, 'predictions': values.tolist()}
        write_json(output / f'validation-predictions-{index}.json', predictions)
        reports.append({'seed': partition['seed'], 'train_rows': len(train),
                        'validation_rows': len(validation), 'metrics': metrics,
                        'train_ids_digest': digest(partition['train_row_ids']),
                        'validation_ids_digest': digest(partition['validation_row_ids']),
                        'fit_scope': 'preprocessing_and_estimator_fit_on_train_only'})
    aggregate = {name: float(np.mean([row['metrics'][name] for row in reports])) for name in reports[0]['metrics']}
    report = {'candidate_id': digest(spec), 'attempt_ref': candidate_id, 'family': spec['family'], 'spec': spec,
              'folds': reports, 'validation_mean': aggregate, 'versions': _versions()}
    write_json(output / 'validation-report.json', report)
    print(json.dumps({'ok': True, 'candidate_id': candidate_id}))


def _predict_worker():
    import joblib
    import numpy as np
    metadata = read_json('prediction_manifest.json')
    frame = _read_frame('features.csv')
    x = frame.drop(columns=[ROW]).replace([np.inf, -np.inf], np.nan)
    rows = []
    for item in metadata['pipelines']:
        if file_digest(item['path']) != item['digest']:
            raise ValueError('frozen estimator digest mismatch')
        pipeline = joblib.load(item['path'])
        classes = pipeline.classes_.tolist() if metadata['problem_kind'] == 'classification' else None
        prediction = pipeline.predict_proba(x) if classes is not None else pipeline.predict(x)
        rows.append({'candidate_id': item['candidate_id'], 'fold': item['fold'],
                     'row_ids': frame[ROW].astype(str).tolist(), 'classes': classes,
                     'predictions': prediction.tolist()})
    write_json('predictions.json', rows)
    print(json.dumps({'ok': True, 'prediction_sets': len(rows)}))


def _score_worker():
    import numpy as np
    import pandas as pd
    metadata = read_json('scoring_manifest.json')
    labels = pd.read_csv('labels.csv', dtype={ROW: str, TARGET: str} if metadata['problem_kind'] == 'classification' else {ROW: str})
    expected_ids = labels[ROW].tolist()
    reports = []
    predictions = read_json('predictions.json')
    expected = {tuple(item) for item in metadata['expected_prediction_sets']}
    actual = [(row['candidate_id'], row['fold']) for row in predictions]
    if not expected or len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('prediction candidate/fold coverage differs from frozen portfolio')
    for row in predictions:
        if row['row_ids'] != expected_ids or len(set(row['row_ids'])) != len(expected_ids):
            raise ValueError('prediction row identities or ordering differ from sealed labels')
        if metadata['problem_kind'] == 'classification' and row['classes'] != metadata['classes']:
            raise ValueError('prediction probability columns differ from frozen class order')
        metrics = _metrics(metadata['problem_kind'], labels[TARGET], row['predictions'], row['classes'])
        reports.append({'candidate_id': row['candidate_id'], 'fold': row['fold'], 'metrics': metrics})
    grouped = {}
    for candidate_id in sorted({row['candidate_id'] for row in reports}):
        selected = [row['metrics'] for row in reports if row['candidate_id'] == candidate_id]
        grouped[candidate_id] = {name: float(np.mean([row[name] for row in selected])) for name in selected[0]}
    result = {'record_type': 'frozen_tabular_holdout_evaluation/v1', 'test_rows': len(labels),
              'per_fold': reports, 'candidate_test_mean': grouped,
              'selected_before_test': metadata['selected_candidate_id'],
              'selection_metric': metadata['primary_metric'], 'used_for_model_feedback': False}
    write_json('test-report.json', result)
    print(json.dumps({'ok': True, 'evaluated_candidates': len(grouped)}))


def backend(root, image):
    from loop_engine.core.workspace_backends import (
        DockerResourceLimits,
        DockerWorkspace,
        DockerWorkspaceDeclaration,
        WorkspaceSpec,
    )
    value = DockerWorkspace(WorkspaceSpec('tabular-host-' + root.name, str(root), backend_kind='docker',
        execution_enabled=True, allowed_commands=('python',), network_access=False),
        DockerWorkspaceDeclaration(image, limits=DockerResourceLimits(
            memory='4g', cpus=2.0, pids=128, temporary_bytes=512 * 1024 * 1024)))
    if not value.availability().available:
        raise RuntimeError('pinned ML Docker runtime is unavailable; host fallback is forbidden')
    return value


class WorkerFailure(RuntimeError):
    """An observed worker result; only a finished process is a known failure."""

    def __init__(self, operation, result):
        self.known_complete = (type(result.exit_code) is int and result.exit_code >= 0
                               and result.error_code == 'command_failed')
        self.observation = {'operation': operation, 'exit_code': result.exit_code,
                            'error_code': result.error_code, 'stderr': result.stderr[-1500:],
                            'known_complete': self.known_complete}
        super().__init__(f'{operation} worker failed: {result.error_code}')


def run_worker(workspace, image, operation, *arguments):
    from loop_engine.core.workspace_backends import CommandRequest
    result = backend(workspace, image).command(CommandRequest(
        ('python', 'worker.py', '_worker', operation, *arguments), execution_authorized=True,
        timeout_seconds=600, max_output_bytes=1024 * 1024))
    if not result.ok or result.output_truncated:
        raise WorkerFailure(operation, result)
    return {'argv': list(result.argv), 'exit_code': result.exit_code,
            'stdout': result.stdout, 'stderr': result.stderr, 'image': image,
            'network': False, 'host_fallback': False}


def prepare(manifest, root, image):
    if root.exists():
        raise ValueError('work directory must not exist; previous evidence is never overwritten')
    root.mkdir(parents=True, mode=0o700)
    staging, workspace, holdout = (root / name for name in ('preparation', 'development-workspace', 'sealed-holdout'))
    for directory in (staging, workspace, holdout):
        directory.mkdir(mode=0o700)
    shutil.copyfile(Path(__file__), staging / 'worker.py')
    shutil.copyfile(manifest['dataset_csv'], staging / 'dataset.csv')
    if file_digest(staging / 'dataset.csv') != manifest['dataset_digest']:
        raise ValueError('dataset changed between admission and preparation copy')
    write_json(staging / 'config.json', manifest)
    execution = run_worker(staging, image, 'prepare')
    for name in ('development.csv', 'development_splits.json', 'profile.json', 'worker.py'):
        shutil.copyfile(staging / name, workspace / name)
    for name in ('holdout_features.csv', 'holdout_labels.csv'):
        shutil.copyfile(staging / name, holdout / name)
    write_json(root / 'input-manifest.json', manifest)
    shutil.copyfile(staging / 'split_manifest.json', root / 'split-manifest.json')
    write_json(root / 'sealed-input-digests.json', {name: file_digest(root / name) for name in (
        'sealed-holdout/holdout_features.csv', 'sealed-holdout/holdout_labels.csv', 'split-manifest.json')})
    write_json(root / 'prepared-input-digests.json', {name: file_digest(workspace / name) for name in (
        'development.csv', 'development_splits.json', 'profile.json', 'worker.py')})
    write_json(root / 'preparation-execution.json', execution)
    return workspace


def make_host(root, image):
    from jsonschema import Draft202012Validator

    from loop_engine.core.capability_directory import (
        CapabilityDirectory,
        CapabilityHandshake,
        Endpoint,
    )
    from loop_engine.core.host_runtime import HostOperationBinding, HostRuntimeBinding
    from loop_engine.loop.effect_approval import (
        ApprovalDecision,
        EffectClass,
        EffectSpec,
    )
    workspace = root / 'development-workspace'
    profile = read_json(workspace / 'profile.json')
    expected = read_json(root / 'prepared-input-digests.json')
    registry, attempts = {}, []
    schema = candidate_schema(profile['problem_kind'])
    families = {'dummy', 'random_forest', 'hist_gradient_boosting',
                'logistic' if profile['problem_kind'] == 'classification' else 'ridge'}

    def snapshot():
        for name, sha in expected.items():
            if file_digest(workspace / name) != sha:
                raise ValueError('frozen development inputs or trusted worker changed')
        for record in attempts:
            for name, sha in record['artifact_digests'].items():
                if file_digest(workspace / name) != sha:
                    raise ValueError('candidate artifact changed')
        return digest({'inputs': expected, 'registry': registry, 'attempts': attempts})

    def inspect(request):
        if request.state_ref != snapshot():
            raise ValueError('stale host profile request')
        return {'ok': True, 'profile': profile, 'candidate_spec_schema': schema,
                'candidates': list(registry.values()), 'attempts': attempts, 'final_test_visible': False}

    def fit(request):
        if request.state_ref != snapshot() or (root / 'portfolio-freeze.json').exists():
            raise ValueError('stale state or frozen portfolio')
        results = []
        for spec in request.arguments['candidates']:
            Draft202012Validator(schema).validate(spec)
            identity = digest(spec)
            if identity not in registry:
                attempt_ref = identity + '/attempt-' + str(len(attempts) + 1)
                target = workspace / 'candidates' / attempt_ref
                target.mkdir(parents=True)
                write_json(target / 'spec.json', spec)
                try:
                    execution = run_worker(workspace, image, 'fit', attempt_ref)
                except WorkerFailure as exc:
                    if not exc.known_complete:
                        raise
                    failure = {'candidate_id': identity, 'family': spec['family'], 'spec': spec,
                        'attempt_ref': attempt_ref, 'status': 'failed', 'execution': exc.observation,
                        'artifact_digests': {path.relative_to(workspace).as_posix(): file_digest(path)
                            for path in sorted(target.iterdir()) if path.is_file()}}
                    attempts.append(failure)
                    write_json(root / 'attempt-records' / (str(len(attempts)) + '.json'), failure)
                    results.append(failure)
                    continue
                report = read_json(target / 'validation-report.json')
                artifact_digests = {path.relative_to(workspace).as_posix(): file_digest(path)
                                    for path in sorted(target.iterdir()) if path.is_file()}
                registry[identity] = {**report, 'artifact_digests': artifact_digests,
                    'artifact_root': target.relative_to(workspace).as_posix(),
                    'attempt_ref': attempt_ref, 'status': 'fitted', 'execution': execution}
                attempts.append(registry[identity])
                write_json(root / 'candidate-records' / (identity + '.json'), registry[identity])
            results.append(registry[identity])
        return {'ok': True, 'validation_results': results,
                'portfolio_families': sorted({item['family'] for item in registry.values()}),
                'test_observations_exposed': False}

    def verify(request):
        if request.state_ref != snapshot():
            raise ValueError('stale host verification request')
        found = {item['family'] for item in registry.values()}
        complete = families <= found
        return {'passed': True, 'task_complete': complete,
                'observations': {'successful_candidates': len(registry), 'families': sorted(found),
                                 'missing_families': sorted(families - found), 'test_evaluated': False},
                'notes': ('All requested model families and baseline were fitted and evaluated on validation only.'
                          if complete else 'Train the missing model families; the final test remains sealed.')}

    def effect(kind, operation):
        return lambda request: EffectSpec(kind, operation, 'tabular-development:' + str(workspace),
                                           (('state', request.state_ref),))

    directory = CapabilityDirectory()
    bindings = []
    for surface, operation, callback, purpose, effects, input_schema, effect_class, permissions in (
            ('tabular_profile', 'invoke', inspect, 'Inspect development-only schema and validation portfolio.',
             ('reads_fs',), object_schema({}), EffectClass.LOCAL_READ, ('source_read',)),
            ('tabular_fit', 'invoke', fit, 'Fit one or more distinct sklearn candidate specs in the pinned offline sandbox; return validation metrics.',
             ('reads_fs', 'writes_fs', 'spawns_process'), object_schema({'candidates': {'type': 'array', 'minItems': 1,
                'items': schema}}, ('candidates',)), EffectClass.COMMAND_EXECUTION, ('sandbox_command', 'workspace_write')),
            ('tabular_verifier', 'validate', verify, 'Verify actual fit artifacts and portfolio family coverage, without test access.',
             ('reads_fs',), {'type': 'object'}, EffectClass.LOCAL_READ, ('source_read',))):
        directory.register(CapabilityHandshake(surface, 'static_component', purpose, (operation,),
            effects=effects, max_response_bytes=2 * 1024 * 1024), [Endpoint(operation, callback)])
        bindings.append(HostOperationBinding(surface, operation, input_schema, {'type': 'object'},
            effect(effect_class, surface), 'tabular.portfolio/v1:' + surface, permission_names=permissions))

    def authorize(request):
        return ApprovalDecision.approve(request.request_id, 'tabular_host_policy',
                                         reason='Exact operation in the declared development-only workspace.')

    host = HostRuntimeBinding(directory, tuple(bindings[:2]), bindings[2], authorize, snapshot,
        'tabular-portfolio:' + digest(expected), share_outputs_with_model=True)
    return host, registry, profile


def final_evaluate(root, registry, profile, image):
    if not registry:
        raise ValueError('cannot evaluate an empty portfolio')
    workspace = root / 'development-workspace'
    prepared = read_json(root / 'prepared-input-digests.json')
    if any(file_digest(workspace / name) != sha for name, sha in prepared.items()):
        raise ValueError('prepared development inputs or worker changed before final evaluation')
    sealed = read_json(root / 'sealed-input-digests.json')
    if any(file_digest(root / name) != sha for name, sha in sealed.items()):
        raise ValueError('sealed holdout or split provenance changed before evaluation')
    primary = profile['primary_metric']
    selected = select_candidate(registry, profile)
    frozen = {'record_type': 'tabular_portfolio_freeze/v1', 'candidates': registry,
              'selected_candidate_id': selected, 'selection_metric': primary,
              'selection_direction': profile['direction'], 'test_results_used_for_selection': False}
    write_json(root / 'portfolio-freeze.json', frozen)
    predictor, scorer = root / 'final-predictor', root / 'final-scorer'
    predictor.mkdir(mode=0o700)
    scorer.mkdir(mode=0o700)
    shutil.copyfile(workspace / 'worker.py', predictor / 'worker.py')
    shutil.copyfile(workspace / 'worker.py', scorer / 'worker.py')
    if any(file_digest(folder / 'worker.py') != prepared['worker.py'] for folder in (predictor, scorer)):
        raise ValueError('frozen worker copy changed')
    shutil.copyfile(root / 'sealed-holdout/holdout_features.csv', predictor / 'features.csv')
    if file_digest(predictor / 'features.csv') != sealed['sealed-holdout/holdout_features.csv']:
        raise ValueError('held-out feature copy changed')
    models = []
    for candidate_id, record in registry.items():
        for index in range(3):
            relative = record['artifact_root'] + f'/pipeline-{index}.joblib'
            if file_digest(workspace / relative) != record['artifact_digests'][relative]:
                raise ValueError('estimator changed after validation')
            destination = predictor / f'{candidate_id}-{index}.joblib'
            shutil.copyfile(workspace / relative, destination)
            if file_digest(destination) != record['artifact_digests'][relative]:
                raise ValueError('frozen estimator copy changed')
            models.append({'candidate_id': candidate_id, 'fold': index, 'path': destination.name,
                           'digest': file_digest(destination)})
    write_json(predictor / 'prediction_manifest.json', {'pipelines': models, 'problem_kind': profile['problem_kind']})
    prediction_execution = run_worker(predictor, image, 'predict')
    shutil.copyfile(predictor / 'predictions.json', scorer / 'predictions.json')
    shutil.copyfile(root / 'sealed-holdout/holdout_labels.csv', scorer / 'labels.csv')
    if file_digest(scorer / 'labels.csv') != sealed['sealed-holdout/holdout_labels.csv']:
        raise ValueError('held-out label copy changed')
    write_json(scorer / 'scoring_manifest.json', {'problem_kind': profile['problem_kind'], 'classes': profile['classes'],
        'selected_candidate_id': selected, 'primary_metric': primary,
        'expected_prediction_sets': [[item['candidate_id'], item['fold']] for item in models]})
    scoring_execution = run_worker(scorer, image, 'score')
    report = {**read_json(scorer / 'test-report.json'), 'freeze_digest': file_digest(root / 'portfolio-freeze.json'),
              'prediction_execution': prediction_execution, 'scoring_execution': scoring_execution,
              'sealed_input_digests': sealed, 'worker_digest': file_digest(workspace / 'worker.py'),
              'predictor_has_test_labels': False, 'pipelines_loaded_in_controller': False}
    write_json(root / 'final-evaluation.json', report)
    return report


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '_worker':
        import os
        for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
            os.environ[variable] = '1'
        operation = sys.argv[2]
        {'prepare': _prepare_worker, 'fit': lambda: _fit_worker(sys.argv[3]),
         'predict': _predict_worker, 'score': _score_worker}[operation]()
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--work-dir', required=True)
    parser.add_argument('--authorize-model-calls', action='store_true')
    parser.add_argument('--allow-source-to-model', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--model-route', default='cloud.default')
    parser.add_argument('--model-id', default='deepseek-v4-flash:0731')
    parser.add_argument('--image', default=IMAGE)
    args = parser.parse_args()
    if not args.prepare_only and not (args.authorize_model_calls and args.allow_source_to_model):
        parser.error('live solve requires --authorize-model-calls and --allow-source-to-model')
    root = Path(args.work_dir).resolve()
    manifest = load_manifest(args.manifest)
    prepare(manifest, root, args.image)
    if args.prepare_only:
        print(json.dumps({'prepared': str(root), 'model_calls': 0}))
        return 0
    from loop_engine import SolveRequest, solve_task
    from loop_engine.code_nodes.solution_model_port import ModelExecution
    from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig
    from loop_engine.templates.intake import TaskIntakeRequest, intake_task
    host, registry, profile = make_host(root, args.image)
    task = ('Use the registered tabular host to inspect development data and build a portfolio of real fitted models. '
            'Fit dummy baseline and each of the three distinct non-dummy families in the supplied candidate schema. '
            'Choose explicit actual hyperparameters based on the profile; the schema requires every listed parameter. '
            'You may fit all four candidates in one tabular_fit request to avoid unnecessary passes. '
            'The host fits each recipe on three fixed development train/validation partitions, with preprocessing fit '
            'only on training rows. Compare validation metrics; you may revise candidates using validation evidence. '
            'Once all families are successfully fitted, return the verified portfolio. Do not request test data, alter '
            'splits, or fabricate metrics. The final untouched test will be scored independently only after you finish. '
            'This is a dataset exercise, not a Kaggle submission. Problem kind: ' + manifest['problem_kind'] + '.')
    model = ModelExecution(ModelGateway(), ModelGatewayConfig(route_names=(args.model_route,),
        allowed_models=(args.model_id,), allow_failover=False))

    def progress(value):
        if value.get('event_type') in ('model.step.started', 'model.step.completed', 'practitioner.diagnostic'):
            print(json.dumps({key: value.get(key) for key in ('event_type', 'run_id', 'step',
                'model_calls_completed', 'elapsed_seconds', 'diagnostic_code')}), flush=True)

    outcome = solve_task(SolveRequest(intake_task(TaskIntakeRequest(text=task)), model_execution=model,
        host_runtime=host, runs_dir=str(root / 'runs'), interaction_mode='autonomous',
        quiet_model_io=True, progress=progress))
    write_json(root / 'solve-outcome.json', outcome.to_dict())
    if not outcome.solved:
        print(json.dumps({'solved': False, 'status': outcome.status, 'work_dir': str(root)}))
        return 1
    final = final_evaluate(root, registry, profile, args.image)
    print(json.dumps({'solved': True, 'work_dir': str(root), 'model_calls': outcome.model_calls,
                      'final_evaluation': final}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
