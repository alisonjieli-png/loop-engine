"""Prepare an immutable public OpenML dataset for the host portfolio example.

This is explicit host preparation, not an engine-selected download capability.
Downloaded data and license metadata remain local; do not publish source rows.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


def validate_source_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in (
            'www.openml.org', 'openml.org', 'data.openml.org') or (
            parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443)):
        raise ValueError('Only public HTTPS OpenML source endpoints are allowed.')


class SourceRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        validate_source_url(new_url)
        return super().redirect_request(request, response, code, message, headers, new_url)


def fetch(url: str) -> bytes:
    validate_source_url(url)
    with build_opener(SourceRedirectHandler()).open(url, timeout=60) as response:
        validate_source_url(response.url)
        payload = response.read(64 * 1024 * 1024 + 1)
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError('This small-data example refuses sources above 64 MiB.')
    return payload


def prepare(dataset_id: int, output_dir: Path, problem_kind: str,
            excluded_features: tuple[str, ...]) -> dict:
    import pandas as pd

    if dataset_id <= 0 or problem_kind not in ('classification', 'regression'):
        raise ValueError('Supply an exact positive dataset ID and task kind.')
    if output_dir.exists():
        raise ValueError('Output must not exist; previous source evidence is preserved.')
    metadata_url = f'https://www.openml.org/api/v1/json/data/{dataset_id}'
    metadata_bytes = fetch(metadata_url)
    metadata = json.loads(metadata_bytes)['data_set_description']
    if (int(metadata['id']) != dataset_id or metadata['status'] != 'active'
            or metadata['visibility'] != 'public'):
        raise ValueError('Expected the exact active public source.')
    parquet_url = metadata['parquet_url']
    parquet_bytes = fetch(parquet_url)
    frame = pd.read_parquet(io.BytesIO(parquet_bytes))
    target = metadata['default_target_attribute']
    if target not in frame or any(name not in frame for name in excluded_features):
        raise ValueError('Target or excluded feature does not exist in the actual source.')
    if frame[target].isna().any() or not len(frame):
        raise ValueError('This supervised example requires complete target labels.')
    csv_bytes = frame.to_csv(index=False, lineterminator='\n').encode('utf-8')
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, body in (('source-metadata.json', metadata_bytes),
                       ('source.parquet', parquet_bytes), ('dataset.csv', csv_bytes)):
        with (output_dir / name).open('xb') as handle:
            handle.write(body)
    manifest = {
        'record_type': 'tabular_portfolio_input/v1',
        'dataset_csv': str((output_dir / 'dataset.csv').resolve()),
        'target': target, 'problem_kind': problem_kind,
        'excluded_features': list(excluded_features),
        'source': {
            'dataset_id': dataset_id, 'name': metadata['name'],
            'version': metadata['version'], 'metadata_url': metadata_url,
            'download_url': parquet_url, 'license': metadata.get('licence', 'unknown'),
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'rows': len(frame), 'columns': len(frame.columns),
            'columns_in_order': list(frame.columns),
            'metadata_sha256': hashlib.sha256(metadata_bytes).hexdigest(),
            'parquet_sha256': hashlib.sha256(parquet_bytes).hexdigest(),
            'csv_sha256': hashlib.sha256(csv_bytes).hexdigest(),
            'preparation': 'Host download and CSV conversion; not an engine action.',
            'unseen': False, 'kaggle_submission': False,
        },
    }
    with (output_dir / 'manifest.json').open('x', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-id', type=int, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--problem-kind', choices=('classification', 'regression'), required=True)
    parser.add_argument('--exclude', action='append', default=[])
    args = parser.parse_args()
    print(json.dumps(prepare(args.dataset_id, args.output_dir, args.problem_kind,
                             tuple(args.exclude)), indent=2))


if __name__ == '__main__':
    main()
