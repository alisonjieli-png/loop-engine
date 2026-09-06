"""Explicit host preparation for an already-entered Kaggle CSV competition.

This records access evidence, not a HumanLegalReview or a claim of unseen data.
Raw data and source pages remain private. No competition is joined here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import tabular_portfolio as portfolio


def prepare(args):
    if not args.authorize_download:
        raise PermissionError('Use --authorize-download for the exact entered competition.')
    root = Path(args.output_dir).resolve()
    if root.exists():
        raise FileExistsError('Preserve earlier acquisition; output directory must be new.')
    root.mkdir(parents=True, mode=0o700)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'benchmarks/kaggle_competitions'))
    from preflight import KagglePreflightRequest, run_preflight_as_loop, write_report
    request = KagglePreflightRequest(
        campaign_id='source-' + args.competition + '-20260906', target_competitions=1,
        maximum_pages=1, page_size=20, concurrency=1, timeout_seconds=60,
        search=args.competition, workspace_root=str(root), authorize_network_reads=True)
    report = run_preflight_as_loop(request, str(root / 'access-runs'))
    write_report(report, str(root / 'preflight.json'), str(root))
    selected = report['population']['selected']
    if len(selected) != 1 or selected[0]['slug'] != args.competition or selected[0]['user_has_entered'] is not True:
        raise PermissionError('The current account must already be entered in this exact competition.')
    probe = report['probes'][0]
    expected = {row['name']: row['size_bytes'] for row in probe['files']}
    names = ('train.csv', 'test.csv', 'sample_submission.csv')
    if probe['may_be_truncated'] or any(name not in expected for name in names):
        raise ValueError('Need a complete file listing with the three declared CSV files.')
    executable = shutil.which('kaggle')
    version = subprocess.run([executable, '--version'], capture_output=True, text=True, check=True)
    portfolio.write_json(root / 'cli-identity.json', {
        'path': executable, 'version': version.stdout.strip(),
        'entrypoint_sha256': portfolio.file_digest(executable),
        'note': 'Actual subprocess CLI, separate from preflight Python-package metadata.'})
    pages = subprocess.run([executable, 'competitions', 'pages', args.competition,
                            '--content', '--format', 'json'], capture_output=True, text=True,
                           timeout=60, check=True)
    bodies = json.loads(pages.stdout)
    portfolio.write_json(root / 'competition-pages.json', bodies)
    source = root / 'data'
    source.mkdir(mode=0o700)
    downloads = []
    for name in names:
        command = [executable, 'competitions', 'download', args.competition,
                   '--file', name, '--path', str(source), '--quiet']
        intent = {'command': command, 'expected_filename': name, 'expected_bytes': expected[name],
                  'source_ref': 'https://www.kaggle.com/competitions/' + args.competition + '/data',
                  'authority': 'User requested work on competitions their account already entered.',
                  'new_entry_or_terms_acceptance': False}
        portfolio.write_json(root / (name + '.download-intent.json'), intent)
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        path = source / name
        if result.returncode or not path.is_file() or path.is_symlink():
            portfolio.write_json(root / (name + '.download-failure.json'), {
                'returncode': result.returncode, 'stderr_digest': hashlib.sha256(result.stderr.encode()).hexdigest(),
                'expected_path_exists': path.exists()})
            raise RuntimeError('Download failed or did not produce the declared plain CSV: ' + name)
        if path.stat().st_size != expected[name]:
            raise ValueError('Downloaded byte count differs from the current source listing: ' + name)
        with path.open(newline='', encoding='utf-8') as handle:
            reader = csv.reader(handle)
            columns = next(reader)
            rows = sum(1 for _ in reader)
        downloads.append({'filename': name, 'sha256': portfolio.file_digest(path),
                          'bytes': path.stat().st_size, 'rows': rows, 'columns': columns,
                          'returncode': result.returncode})
    manifest = {
        'record_type': 'tabular_portfolio_input/v1', 'dataset_csv': str(source / 'train.csv'),
        'target': args.target, 'problem_kind': args.problem_kind,
        'excluded_features': list(args.exclude),
        'selection_metric': args.selection_metric,
        'source': {'name': args.competition, 'source_type': 'kaggle_competition',
                   'csv_sha256': downloads[0]['sha256'], 'rows': downloads[0]['rows'],
                   'retrieved_at': datetime.now(timezone.utc).isoformat(),
                   'preflight_ref': str(root / 'preflight.json'),
                   'preflight_report_digest': report['report_digest'],
                   'pages_ref': str(root / 'competition-pages.json'),
                   'pages_sha256': portfolio.file_digest(root / 'competition-pages.json'),
                   'downloads': downloads, 'unseen': False,
                   'preparation': 'Explicit host acquisition under existing account entry; not model-selected download.',
                   'separate_human_legal_review_record': None}}
    portfolio.write_json(root / 'manifest.json', manifest)
    print(json.dumps({'competition': args.competition, 'rows': downloads[0]['rows'],
                      'files': len(downloads), 'bytes': sum(item['bytes'] for item in downloads),
                      'manifest': str(root / 'manifest.json'), 'model_calls': 0}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--competition', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--problem-kind', choices=('classification', 'regression'), required=True)
    parser.add_argument('--selection-metric', required=True)
    parser.add_argument('--exclude', action='append', default=[])
    parser.add_argument('--authorize-download', action='store_true')
    prepare(parser.parse_args())


if __name__ == '__main__':
    main()
