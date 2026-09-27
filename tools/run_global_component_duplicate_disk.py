"""Run/resume cross-lane duplicate diagnostics with disk-backed profiles."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tools')]

from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore
from tools.global_component_duplicate_disk import DiskComparison
from tools.global_component_duplicate_sources import SourceReader


def save(path, value):
    with exact_output(path) as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def exact_output(path):
    """Publish one complete export; preserve interrupted files and refuse drift."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    temporary = path.with_name(path.name + '.' + stamp + '.partial')
    with temporary.open('x') as stream:
        yield stream
        stream.flush()
        os.fsync(stream.fileno())
    if path.exists():
        if path.is_symlink() or file_digest(path) != file_digest(temporary):
            raise ValueError('report_export_changed')
        temporary.unlink()  # Only this attempt's exact duplicate temporary export.
    else:
        os.replace(temporary, path)


def progress(value):
    print(json.dumps(value), flush=True)


def collect(configuration, disk):
    reader = SourceReader()
    fallbacks = [VolumeBodyStore(str(Path(path).absolute())) for path in configuration['fallback_body_stores']]
    sources = []
    started = datetime.now(timezone.utc).isoformat()
    for source in configuration['sources']:
        if set(source) != {'kind','path','corpus'}:
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
        elif source['kind'] == 'adapted_catalogue':
            iterator = reader.adapted(path, source['corpus'])
        else:
            raise ValueError('comparison_source_invalid')
        count = 0
        try:
            for subject in iterator:
                try:
                    disk.add(subject)
                    count += 1
                except ValueError as error:
                    if str(error) != 'empty_comparison_text':
                        raise
                    reader.excluded(path, subject['identity'], str(error))
                if count % 1000 == 0:
                    disk.connection.commit()
                    progress({'phase':'collecting','corpus':source['corpus'],'observations':count})
        except (ValueError, OSError) as error:
            reader.excluded(path, '?', 'source_read_incomplete:' + type(error).__name__ + ':' + str(error))
        disk.connection.commit()
        sources.append({**source,'observations':count})
        progress({'phase':'collected_source','corpus':source['corpus'],'observations':count,
                  'exclusions':len(reader.exclusions)})
    disk.freeze_collection({'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),
                            'sources':sources,'metadata_snapshots':reader.metadata,
                            'notes':reader.collection_notes,'exclusions':reader.exclusions})


def exact_reports(disk, output):
    corpora, views, states = Counter(), Counter(), Counter()
    with exact_output(output / 'observations.jsonl') as stream:
        for (payload,) in disk.connection.execute('SELECT payload FROM subjects ORDER BY key'):
            stream.write(payload + '\n')
            value = json.loads(payload)
            corpora[value['corpus']] += 1
            views[value['view']] += 1
            states[value['corpus'] + ':' + value['lifecycle']] += 1
    package_groups, text_groups = 0, 0
    with exact_output(output / 'matching-package-manifests.jsonl') as stream:
        for digest, count in disk.connection.execute(
                'SELECT package_digest,count(*) FROM subjects GROUP BY package_digest HAVING count(*)>1'):
            members = [r[0] for r in disk.connection.execute('SELECT key FROM subjects WHERE package_digest=? ORDER BY key',(digest,))]
            stream.write(json.dumps({'package_digest':digest,'members':members,'count':count})+'\n')
            package_groups += 1
    with exact_output(output / 'matching-comparison-text.jsonl') as stream:
        for group_id, count in disk.connection.execute('SELECT group_id,count(*) FROM subjects GROUP BY group_id HAVING count(*)>1'):
            key = disk.connection.execute('SELECT group_key FROM groups WHERE id=?',(group_id,)).fetchone()[0]
            members = [r[0] for r in disk.connection.execute('SELECT key FROM subjects WHERE group_id=? ORDER BY key',(group_id,))]
            stream.write(json.dumps({'group':key,'members':members,'count':count})+'\n')
            text_groups += 1
    return {'corpora':dict(corpora),'comparison_views':dict(views),'observed_lifecycle_labels':dict(states),
            'observations':sum(corpora.values()),'manifest_match_groups':package_groups,
            'normalized_text_groups':text_groups}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threshold', type=Fraction, default=Fraction(17,20))
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not Fraction(1,2) <= args.threshold <= 1:
        parser.error('threshold must be from one half to one')
    raw = args.configuration.read_bytes()
    configuration = json.loads(raw)
    if set(configuration) != {'record_type','sources','fallback_body_stores'} or configuration['record_type'] != 'global_component_comparison_sources/v1':
        raise ValueError('source_configuration_unsupported')
    if not args.resume:
        args.output.mkdir(parents=True, exist_ok=False)
    elif not args.output.is_dir():
        raise ValueError('resume_folder_missing')
    binding = {'record_type':'component_comparison_run_binding/v1',
               'configuration_sha256':hashlib.sha256(raw).hexdigest(),'threshold':str(args.threshold),
               'sources_sha256':hashlib.sha256((ROOT/'tools/global_component_duplicate_sources.py').read_bytes()).hexdigest(),
               'engine_sha256':hashlib.sha256((ROOT/'tools/global_component_duplicate_disk.py').read_bytes()).hexdigest(),
               'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    disk = DiskComparison(args.output/'comparison.db',binding,resume=args.resume)
    try:
        if disk.get_meta('phase') == 'collecting':
            if args.resume:
                raise ValueError('incomplete_collection_requires_new_snapshot')
            collect(configuration,disk)
        collection = disk.get_meta('collection')
        if disk.get_meta('exact_report') is None:
            exact = exact_reports(disk,args.output)
            disk.set_meta('exact_report',exact)
            disk.connection.commit()
        else:
            exact = disk.get_meta('exact_report')
        disk.build_profiles(args.threshold,progress)
        disk.compare(args.threshold,progress)
        report_path = args.output/'summary.json'
        pair_count = 0
        with exact_output(args.output/'near-pairs.jsonl') as stream:
            for left,right,intersection,union in disk.pair_rows():
                stream.write(json.dumps({'left_group':left,'right_group':right,'intersection':intersection,
                    'union':union,'jaccard':round(intersection/union,8),
                    'meaning':'similar comparison text; functional duplication requires review'})+'\n')
                pair_count += 1
        save(args.output/'collection.json',collection)
        report = disk.get_meta('final_report') or {'record_type':'global_component_duplicate_report/v2',**exact,
            'started_at':collection['started_at'],'finished_at':datetime.now(timezone.utc).isoformat(),
            'distinct_comparison_groups':disk.connection.execute('SELECT count(*) FROM groups').fetchone()[0],
            'near_group_pairs':pair_count,'threshold':str(args.threshold),'shingle_words':5,
            'algorithm':'disk-backed exact prefix join; globally fixed word-frequency order; exact Jaccard confirmation',
            'excluded_inputs':len(collection['exclusions']),'model_calls':0,'source_writes':0,
            'automatic_merges':0,'approvals':0,'binding':binding,
            'not_measured':['semantic equivalence','correctness','all raw unmaterialized files','global atomic snapshot','every supporting payload'],
            'status':'completed_with_exclusions' if collection['exclusions'] else 'completed'}
        if report['binding'] != binding or report['near_group_pairs'] != pair_count:
            raise ValueError('completed_report_binding_mismatch')
        disk.set_meta('final_report',report)
        disk.connection.commit()
        save(report_path,report)
        progress(report)
    finally:
        disk.close()


if __name__ == '__main__':
    main()
