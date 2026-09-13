"""Regenerate the canonical catalog projection with a database-owned writer.

The catalog generator owns the content and canonical layout. DuckDB validates
the JSON and exports its exact text, preserving the existing byte-level gate.
An expected digest prevents overwriting a concurrently changed projection.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import os
import tempfile

import duckdb


def refresh(package_root: Path, expected_digest: str):
    from loop_engine.ontology.catalog import UnifiedCatalog
    package_root = package_root.resolve(strict=True)
    target = package_root/'ontology/index.json'
    if target.is_symlink() or not target.is_file():
        raise ValueError('an existing ordinary ontology projection is required')
    previous = target.read_bytes()
    if hashlib.sha256(previous).hexdigest() != expected_digest:
        raise ValueError('ontology projection changed before regeneration')
    snapshot = UnifiedCatalog(package_root=str(package_root)).discover()
    if snapshot.problems:
        raise ValueError('catalog discovery is not valid: '+str(snapshot.problems))
    canonical = snapshot.index_json()
    with tempfile.TemporaryDirectory(prefix='index-export-',dir=target.parent) as temporary:
        staged = Path(temporary)/'index.json'
        database = duckdb.connect()
        try:
            database.execute('CREATE TABLE projection AS SELECT ?::VARCHAR AS canonical_json', [canonical])
            if not database.execute('SELECT json_valid(canonical_json) FROM projection').fetchone()[0]:
                raise ValueError('generator produced invalid JSON')
            # A single unquoted text column preserves the generator's required
            # JSON whitespace. No Python file writer materializes the payload.
            database.execute("COPY projection TO '"+str(staged).replace("'","''")+
                "' (FORMAT CSV, HEADER false, QUOTE '', ESCAPE '')")
        finally:
            database.close()
        if staged.read_bytes() != (canonical+'\n').encode():
            raise ValueError('database export changed canonical projection bytes')
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected_digest:
            raise ValueError('ontology projection changed during regeneration')
        os.replace(staged,target)
    return {'before':expected_digest,'after':hashlib.sha256(target.read_bytes()).hexdigest(),
            'entries':len(snapshot.entries)}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--package-root',required=True,type=Path)
    parser.add_argument('--expected-digest',required=True)
    args=parser.parse_args()
    print(refresh(args.package_root,args.expected_digest))
