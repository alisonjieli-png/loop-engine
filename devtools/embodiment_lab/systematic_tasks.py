"""Admit a real task-folder problem with fresh sealed query cases.

The task is density-normalized nearest-neighbor retrieval from the raw task
collection. Original training coordinates are used; development and final
query instances are newly generated. Task novelty and pretraining exposure
are not established by this preparation tool.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import io
import json
import math
from pathlib import Path
import secrets
import zipfile

import numpy as np

from .systematic_records import CampaignProjection, canonical, digest


SOURCE_TASK = '1-c-qualification-machine-learning'
TASK_ID = 'density_normalized_neighbors_v1'


def reference_neighbors(training, queries):
    """Trusted vector implementation of the source task's declared formula."""
    values = np.asarray([[r[1], r[2]] for r in training], dtype=float)
    if len(training) < 21 or not np.isfinite(values).all():
        raise ValueError('training requires at least 21 finite points')
    # Work in batches, so source size does not create a square resident array.
    sigmas = []
    for start in range(0, len(values), 64):
        block = values[start:start+64]
        distances = np.sqrt(((block[:, None, :] - values[None, :, :]) ** 2).sum(axis=2))
        for offset in range(len(block)):
            distances[offset, start+offset] = np.inf
        near = np.partition(distances, 19, axis=1)[:, :20]
        sigmas.extend(near.mean(axis=1).tolist())
    sigmas = np.asarray(sigmas)
    output = []
    for query in queries:
        distances = np.sqrt(((values - np.asarray(query[1:], dtype=float)) ** 2).sum(axis=1))
        sigma_query = np.partition(distances, 19)[:20].mean()
        normalized = distances / (1e-8 + sigma_query + sigmas)
        ordering = sorted(range(len(training)), key=lambda i: (normalized[i], str(training[i][0])))[:5]
        output.append([str(training[i][0]) for i in ordering])
    return output


def independent_reference(training, queries):
    """Small reference using scalar distances and heaps, not the vector code."""
    density = []
    for i, point in enumerate(training):
        distances = [math.hypot(point[1]-other[1], point[2]-other[2])
                     for j, other in enumerate(training) if i != j]
        density.append(math.fsum(heapq.nsmallest(20, distances)) / 20)
    result = []
    for query in queries:
        distances = [math.hypot(query[1]-point[1], query[2]-point[2]) for point in training]
        scale = math.fsum(heapq.nsmallest(20, distances)) / 20
        result.append([str(training[i][0]) for i in sorted(range(len(training)),
            key=lambda i: (distances[i] / (1e-8 + scale + density[i]), str(training[i][0])))[:5]])
    return result


def prepare(study_root):
    study_root = Path(study_root)
    source = Path('/home/username/task_database/kaggle_tasks') / SOURCE_TASK
    archives = sorted((source / 'data').glob('*.zip'))
    if len(archives) != 1:
        raise ValueError('the admitted source must have one exact archive')
    archive = archives[0]
    with zipfile.ZipFile(archive) as z:
        raw = z.read('ml_train.csv')
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf8'))))
    if not rows or set(rows[0]) != {'id', 'x1', 'x2'}:
        raise ValueError('actual source schema differs from the reviewed task description')
    training = [[str(r['id']), float(r['x1']), float(r['x2'])] for r in rows]
    if len({r[0] for r in training}) != len(training):
        raise ValueError('source identifiers are not unique')
    seed = secrets.randbits(63)
    rng = np.random.default_rng(seed)
    values = np.asarray([r[1:] for r in training]);low = values.min(axis=0); high = values.max(axis=0)

    def queries(count, prefix):
        points = rng.uniform(low, high, size=(count, 2))
        return [[prefix + str(i), float(p[0]), float(p[1])] for i, p in enumerate(points)]

    development_queries = queries(8, 'dev-')
    heldout_queries = queries(48, 'held-')
    development_expected = reference_neighbors(training, development_queries)
    heldout_expected = reference_neighbors(training, heldout_queries)
    small_train = training[:43]
    small_queries = queries(7, 'control-')
    if reference_neighbors(small_train, small_queries) != independent_reference(small_train, small_queries):
        raise ValueError('independent evaluator implementations disagree')
    # Permutations must not change identifier-based results.
    if reference_neighbors(list(reversed(small_train)), small_queries) != independent_reference(small_train, small_queries):
        raise ValueError('reference depends on training row order')
    statement = (
        'Implement solve(training_points, query_points) in solution.py. Each point is [id, x1, x2]; '
        'ids are strings and coordinates are finite numbers. Return one list of five training ids per query, in query order. '
        'For each training point, sigma is the mean Euclidean distance to its 20 nearest OTHER training points. '
        'For each query, sigma_query is the mean Euclidean distance to its 20 nearest training points. '
        'Rank every training point i by Euclidean_distance(query,i)/(1e-8+sigma_query+sigma_i) and return the first five ids. '
        'Every query is independent; other queries never affect its neighbors or density. '
        'If normalized distances tie, order tied ids lexicographically. Training has at least 21 points. '
        'Do not mutate input lists. You may use Python standard library or NumPy/SciPy available in the declared runtime. '
        'Build a reusable implementation; fixed answers for development queries cannot pass the separately sealed cases.')
    task = {'record_type': 'systematic_admitted_task/v1', 'task_id': TASK_ID,
            'origin_task_id': SOURCE_TASK, 'source_directory': str(source),
            'source_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'training_csv_sha256': hashlib.sha256(raw).hexdigest(),
            'description_sha256': hashlib.sha256((source/'description.json').read_bytes()).hexdigest(),
            'prompt': statement, 'entrypoint': 'solve',
            'training_count': len(training), 'validation_count': len(development_queries),
            'heldout_count': len(heldout_queries), 'training_points': training,
            'development_queries': development_queries, 'development_expected': development_expected,
            'local_protocol_adaptations': ['function interface', 'lexicographic tie rule', 'no input mutation'],
            'independent_reference_agreement': True,
            'unseen_claim': 'new query instances; task novelty and pretraining exposure are not established by this preparation tool'}
    secret = {'record_type': 'systematic_sealed_cases/v1', 'task_id': TASK_ID,
              'seed': seed, 'queries': heldout_queries, 'expected': heldout_expected,
              'release_policy': 'after cohort candidate freeze; never feedback to the current solve'}
    store = CampaignProjection(study_root/'campaign.duckdb')
    if store.latest('admitted_task', TASK_ID):
        raise ValueError('task is already frozen; do not regenerate a holdout')
    store.record('admitted_task', TASK_ID, task)
    store.record('sealed_cases', TASK_ID, secret)
    store.record('evaluator_controls', TASK_ID,
                 {'independent_algorithms_agree': True, 'training_permutation_invariant': True,
                  'expected_outputs_have_five_unique_identifiers': all(len(set(row)) == 5 for row in development_expected),
                  'task_digest': digest(task), 'secret_digest': digest(secret)})
    store.export_object(study_root/'tasks'/TASK_ID/'task-manifest.json',
        {k:v for k,v in task.items() if k not in ('training_points','development_queries','development_expected')})
    store.close()
    print('Admitted', SOURCE_TASK, 'training=', len(training), 'development=', len(development_queries),
          'sealed=', len(heldout_queries), 'independent-reference agreement verified')


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True)
    prepare(p.parse_args().root)
