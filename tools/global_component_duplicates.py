"""Read-only cross-lane duplicate diagnostics using exact Jaccard confirmation.

This tool produces research evidence. It does not merge, withdraw, approve or
publish components. A shared entry document is not necessarily a shared complete
capability. Source readers preserve distinct versions and corpus membership.

Prefix filtering follows the set-ordering principle described by Xiao et al.,
Efficient Similarity Joins for Near Duplicate Detection (WWW 2008). The code is
an original implementation, with existing repository normalization reused.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root), str(root / 'src'), str(root / 'tools')]

from loop_engine.core.library_ingestion.duplicates import normalized, shingles
from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore
from tools.global_component_duplicate_sources import SourceReader


def prefix_pairs(documents, threshold: Fraction):
    """Yield every above-threshold pair of supplied nonempty shingle sets.

    Prefix ordering is global (frequency, then token). Candidate pairs are
    confirmed with exact integer arithmetic. No bucket-size cutoff or
    transitive grouping drops or invents a pair.
    """
    if not isinstance(threshold, Fraction) or not 0 < threshold <= 1:
        raise ValueError('explicit_fraction_threshold_required')
    frequencies = Counter()
    for values in documents.values():
        frequencies.update(values)
    order = sorted(documents, key=lambda key: (len(documents[key]), key))
    postings = defaultdict(list)
    numerator, denominator = threshold.numerator, threshold.denominator
    for key in order:
        own = documents[key]
        size = len(own)
        if not size:
            continue
        minimum = (size * numerator + denominator - 1) // denominator
        prefix_length = size - minimum + 1
        prefix = sorted(own, key=lambda token: (frequencies[token], token))[:prefix_length]
        candidates = set()
        for token in prefix:
            candidates.update(other for other in postings[token] if len(documents[other]) >= minimum)
        for other in sorted(candidates):
            intersection = len(own & documents[other])
            union = size + len(documents[other]) - intersection
            if intersection * denominator >= union * numerator:
                left, right = sorted((key, other))
                yield left, right, intersection, union
        for token in prefix:
            postings[token].append(key)


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threshold', type=Fraction, default=Fraction(17, 20))
    args = parser.parse_args()
    if not Fraction(1,2) <= args.threshold <= 1:
        parser.error('threshold must be from one half to one')
    configuration = json.loads(args.configuration.read_bytes())
    if set(configuration) != {'record_type','sources','fallback_body_stores'} or configuration['record_type'] != 'global_component_comparison_sources/v1':
        raise ValueError('source_configuration_unsupported')
    args.output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    reader = SourceReader()
    subjects, texts, normalized_groups, packages = {}, {}, defaultdict(list), defaultdict(list)
    sources = []
    fallbacks = [VolumeBodyStore(str(Path(path).absolute())) for path in configuration['fallback_body_stores']]
    for source in configuration['sources']:
        if set(source) != {'kind','path','corpus'} or source['kind'] not in {'bundle','import_store','catalogue_tree','adapted_catalogue'}:
            raise ValueError('comparison_source_invalid')
        path = Path(source['path']).absolute()
        if not path.is_dir() or path.resolve() != path:
            reader.excluded(path, '?', 'source_root_missing_or_not_plain')
            continue
        if source['kind'] == 'bundle':
            iterator = reader.bundle(path, source['corpus'], fallbacks)
        elif source['kind'] == 'import_store':
            iterator = reader.imported(path, source['corpus'])
        elif source['kind'] == 'catalogue_tree':
            iterator = reader.tree(path, source['corpus'])
        else:
            iterator = reader.adapted(path, source['corpus'])
        count = 0
        try:
            for subject in iterator:
                if subject['key'] in subjects:
                    raise ValueError('duplicate_source_observation_key')
                text = subject.pop('text')
                normal = normalized(text)
                if not normal:
                    reader.excluded(path, subject['identity'], 'empty_comparison_text')
                    continue
                group = hashlib.sha256(normal.encode()).hexdigest()
                subject['comparison_group'] = group
                subjects[subject['key']] = subject
                normalized_groups[group].append(subject['key'])
                packages[subject['package_digest']].append(subject['key'])
                texts.setdefault(group, text)
                count += 1
        except (ValueError, OSError) as error:
            reader.excluded(path, '?', 'source_read_incomplete:' + type(error).__name__ + ':' + str(error))
        sources.append({**source, 'observations': count})
        print(json.dumps({'source': source['corpus'], 'observations': count,
                          'total': len(subjects), 'exclusions': len(reader.exclusions)}), flush=True)

    with (args.output / 'observations.jsonl').open('x') as output:
        for key in sorted(subjects):
            output.write(json.dumps(subjects[key], sort_keys=True) + '\n')
    write_json(args.output / 'collection.json', {'started_at': started, 'sources': sources,
        'metadata_snapshots': reader.metadata, 'notes': reader.collection_notes,
        'exclusions': reader.exclusions, 'configuration_sha256': hashlib.sha256(args.configuration.read_bytes()).hexdigest()})
    # Exact groups are kept as groups. We do not multiply identical release/import
    # aliases into millions of redundant pair rows or choose a winner to delete.
    exact_packages = {key: values for key, values in packages.items() if len(values) > 1}
    exact_text = {key: values for key, values in normalized_groups.items() if len(values) > 1}
    write_json(args.output / 'matching-package-manifests.json', exact_packages)
    write_json(args.output / 'matching-comparison-text.json', exact_text)
    profiles = {key: frozenset(sys.intern(value) for value in shingles(text)) for key, text in texts.items()}
    del texts
    print(json.dumps({'comparison_groups': len(profiles), 'phase': 'exact_prefix_join'}), flush=True)
    pairs = 0
    corpus_edges = Counter()
    with (args.output / 'near-pairs.jsonl').open('x') as output:
        for left, right, intersection, union in prefix_pairs(profiles, args.threshold):
            left_corpora = {subjects[key]['corpus'] for key in normalized_groups[left]}
            right_corpora = {subjects[key]['corpus'] for key in normalized_groups[right]}
            output.write(json.dumps({'left_group': left, 'right_group': right,
                'intersection': intersection, 'union': union, 'jaccard': round(intersection/union, 8),
                'left_members': normalized_groups[left], 'right_members': normalized_groups[right],
                'meaning': 'similar comparison text; functional duplication requires review'}) + '\n')
            pairs += 1
            for first in left_corpora:
                for second in right_corpora:
                    corpus_edges[' | '.join(sorted((first,second)))] += 1
            if pairs % 10000 == 0:
                output.flush()
                print(json.dumps({'near_group_pairs': pairs}), flush=True)
    report = {'record_type': 'global_component_duplicate_report/v1', 'started_at': started,
        'finished_at': datetime.now(timezone.utc).isoformat(), 'observations': len(subjects),
        'corpora': dict(Counter(row['corpus'] for row in subjects.values())),
        'comparison_views': dict(Counter(row['view'] for row in subjects.values())),
        'manifest_match_groups': len(exact_packages), 'normalized_text_groups': len(exact_text),
        'distinct_comparison_groups': len(profiles), 'near_group_pairs': pairs,
        'near_pairs_by_corpus': dict(corpus_edges), 'threshold': str(args.threshold),
        'shingle_words': 5, 'algorithm': 'frequency-ordered prefix filtering with exact Jaccard confirmation',
        'excluded_inputs': len(reader.exclusions), 'source_coverage': 'named catalogues and native proposals during collection window',
        'not_measured': ['all raw unmaterialized source files','semantic equivalence','correctness','global atomic snapshot','every supporting payload'],
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model_calls': 0, 'source_writes': 0, 'automatic_merges': 0, 'approvals': 0,
        'status': 'completed_with_exclusions' if reader.exclusions else 'completed'}
    write_json(args.output / 'summary.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
