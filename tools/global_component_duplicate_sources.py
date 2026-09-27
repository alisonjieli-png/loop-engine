"""Bounded read-only source adapters for the cross-lane duplicate report."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.service_runtime.catalogue_bundle import strict_json
from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
    CataloguePackageFile,
    VolumeBodyStore,
    placement_path,
)
from tools.candidate_review.native import regular_bytes
from tools.licensed_import.packaging import comparison_text

MAX_METADATA = 128 * 1024 * 1024
MAX_VIEW = 8 * 1024 * 1024
ENTRY_ROLES = ('skill_definition', 'instruction_file', 'subagent_definition', 'command',
               'plugin_manifest', 'protocol_server_configuration', 'configuration', 'executable_tool',
               'hook', 'skill_script')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class SourceReader:
    def __init__(self):
        self.metadata = []
        self.exclusions = []
        self.collection_notes = []

    def metadata_bytes(self, path):
        path = Path(path).absolute()
        if path.resolve() != path:
            raise ValueError('comparison_metadata_not_plain')
        before = path.stat()
        raw = regular_bytes(path.parent, path.name, MAX_METADATA)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError('metadata_changed_during_read')
        self.metadata.append({'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)})
        return raw

    def json(self, path):
        return strict_json(self.metadata_bytes(path), 'comparison_metadata_invalid')

    def excluded(self, source, identity, reason):
        self.exclusions.append({'source': str(source), 'identity': str(identity), 'reason': str(reason)[:240]})

    def subject(self, corpus, source, identity, package, read, *, component_type='', primary_digest=None,
                lifecycle='unknown', semantic=None):
        """One logical package observation and one declared comparison view.

        The package digest is a manifest comparison. Only selected view bytes
        are read here. Full package execution/qualification is outside this tool.
        """
        source = str(source)
        key = sha((corpus + '\0' + source + '\0' + identity + '\0' + package.package_digest).encode())
        view_kind, path = 'entry_text', None
        if component_type == 'api_operation_reference':
            entry = next(e for e in package.files if e.path == 'contracts/operation.openapi.json')
            document = strict_json(read(entry), 'operation_view_invalid')
            card = strict_json(read(next(e for e in package.files if e.path == 'references/endpoint.json')),
                               'operation_card_invalid')
            text = json.dumps({'method': card['method'], 'path': card['path_template'],
                               'paths': document['paths'], 'security': document.get('security')},
                              sort_keys=True, ensure_ascii=False)
            view_kind, path = 'documented_operation', entry.path
        elif component_type == 'service_reference':
            entry = next(e for e in package.files if e.path == 'references/service.json')
            text = read(entry).decode('utf-8')
            view_kind, path = 'service_map', entry.path
        else:
            candidates = [e for e in package.files if e.digest == primary_digest] if primary_digest else []
            if not candidates:
                candidates = sorted((e for e in package.files if e.role in ENTRY_ROLES),
                                    key=lambda e: (ENTRY_ROLES.index(e.role), e.path))
            if not candidates:
                candidates = [e for e in package.files if (e.media_type.startswith('text/') or
                    e.media_type in ('application/json','application/yaml','application/toml','application/schema+json'))
                    and not e.path.rsplit('/',1)[-1].lower().startswith(('license','licence','notice','copying','attribution'))]
                if candidates:
                    view_kind = 'metadata_fallback_text'
            if not candidates:
                raise ValueError('no_comparable_entry_view')
            entry = candidates[0]
            raw = read(entry)
            raw.decode('utf-8')  # Lossy decoding must not create a false exact match.
            text = comparison_text(entry.path, raw)
            if not text.strip():
                # A frontmatter-only record can still carry native metadata.
                # Keep that observation and label the narrower comparison view.
                text = raw.decode('utf-8')
                view_kind = 'frontmatter_only_text'
            path = entry.path
        if len(text.encode('utf-8')) > MAX_VIEW:
            raise ValueError('comparison_view_above_limit')
        return {'key': key, 'corpus': corpus, 'source': source, 'identity': identity,
                'package_digest': package.package_digest, 'view': view_kind,
                'view_path': path, 'view_digest': sha(text.encode('utf-8')), 'text': text,
                'component_type': component_type, 'lifecycle': lifecycle,
                'semantic_key': semantic, 'full_payload_verified': False}

    @staticmethod
    def filesystem_reader(root):
        root = Path(root).absolute()
        if root.resolve() != root:
            raise ValueError('comparison_root_not_plain')
        def read(entry):
            raw = regular_bytes(root, entry.path, entry.size_bytes)
            if len(raw) != entry.size_bytes or sha(raw) != entry.digest:
                raise ValueError('comparison_payload_mismatch')
            return raw
        return read

    def bundle(self, root, corpus, fallbacks=()):
        root = Path(root)
        header = self.json(root / 'bundle.json')
        raw = self.metadata_bytes(root / 'items.jsonl')
        if (header.get('record_type') != 'catalogue_release_bundle/v1'
                or len(raw) != header['items_bytes'] or sha(raw) != header['items_digest']):
            raise ValueError('bundle_snapshot_mismatch')
        stores = [VolumeBodyStore(str(root / 'blobs')), *fallbacks]
        def read(entry):
            for store in stores:
                try:
                    return store.read(entry.digest, entry.size_bytes)
                except ValueError as error:
                    if getattr(error, 'code', None) != 'body_missing':
                        raise
            raise ValueError('comparison_body_missing')
        lines = raw.splitlines()
        if len(lines) != header['items']:
            raise ValueError('bundle_population_mismatch')
        for line in lines:
            row = strict_json(line, 'bundle_comparison_row_invalid')
            identity = row.get('reference', {}).get('identity', '?')
            try:
                if row['record_type'] != 'catalogue_bundle_item/v2':
                    raise ValueError('bundle_row_version_unsupported')
                yield self.subject(corpus, root / 'items.jsonl', identity,
                    CataloguePackage.from_dict(row['package']), read,
                    component_type=row.get('attributes', {}).get('component_type', row['reference']['kind']),
                    lifecycle='served_bundle_snapshot')
            except (ValueError, KeyError, StopIteration) as error:
                self.excluded(root, identity, type(error).__name__ + ':' + str(error))

    def imported(self, root, corpus):
        root = Path(root)
        store = SQLiteRecordStore(str(root / 'records.db'), read_only=True)
        try:
            # One SELECT gives this record population a consistent SQLite view,
            # including committed WAL content. No immutable-mode shortcut.
            records = store.query(IntelligenceQuery(namespaces=('library.import',)))
        finally:
            store.close()
        self.collection_notes.append({'source': str(root / 'records.db'), 'rows_read': len(records),
            'snapshot': 'one read-only SELECT; row versions retained; source database not copied or modified'})
        bodies = VolumeBodyStore(str(root / 'bodies'))
        for record in records:
            row = record['payload']
            if row.get('record_type') != 'licensed_import_candidate/v1':
                continue
            try:
                subject = self.subject(corpus, root / 'records.db', record['record_id'],
                    CataloguePackage.from_dict(row['package']), lambda entry: bodies.read(entry.digest, entry.size_bytes),
                    component_type=row['kind'], primary_digest=row['comparison']['primary_sha256'],
                    lifecycle=record['lifecycle'])
                subject['record_version'] = record['record_version']
                yield subject
            except (ValueError, KeyError, StopIteration) as error:
                self.excluded(root, record['record_id'], type(error).__name__ + ':' + str(error))

    def catalogue(self, path, corpus):
        document = self.json(path)
        root = Path(path).parent
        if document.get('record_type') not in ('starter_catalogue_candidate_items/v2', 'starter_catalogue_candidate_items/v3'):
            raise ValueError('candidate_catalogue_unsupported')
        for row in document['items']:
            identity = row.get('reference', {}).get('identity', '?')
            try:
                if 'package' in row:
                    package = CataloguePackage.from_dict(row['package'])
                    read = self.filesystem_reader(root / placement_path(row['package_root']))
                elif 'package_files' in row:
                    package = CataloguePackage.from_dict({'body_form':'package','files':row['package_files']})
                    read = self.filesystem_reader(root / placement_path(row['package_root']))
                else:
                    reference = row['reference']
                    package = CataloguePackage((CataloguePackageFile(row['body_path'], reference['digest'],
                        reference['size_bytes'], 'text/markdown', 'instruction_file'),), 'file')
                    read = self.filesystem_reader(root)
                subject = self.subject(corpus, path, identity, package, read,
                    component_type=row.get('attributes', {}).get('component_type', row['reference']['kind']),
                    lifecycle=row.get('lifecycle', document.get('publication', 'candidate')))
                subject['producer_family'] = row.get('producer', row.get('provenance', {}).get('producer', {})).get('family')
                subject['declared_licence'] = row['reference'].get('license')
                yield subject
            except (ValueError, KeyError, StopIteration) as error:
                self.excluded(path, identity, type(error).__name__ + ':' + str(error))

    def adapted(self, root, corpus):
        root = Path(root)
        for file in sorted(root.glob('specifications-*.json')):
            document = self.json(file)
            if document.get('record_type') != 'candidate_intelligence_specifications/v4':
                raise ValueError('adapted_catalogue_unsupported')
            for row in document['specifications']:
                try:
                    semantic = row['adaptation']['parameters']
                    yield self.subject(corpus, file, row['id'], CataloguePackage.from_dict(row['package']),
                        self.filesystem_reader(root / placement_path(row['package_root'])), component_type=row['component_type'],
                        lifecycle='candidate', semantic=semantic)
                except (ValueError, KeyError, StopIteration) as error:
                    self.excluded(file, row.get('id', '?'), type(error).__name__ + ':' + str(error))

    def proposals(self, path, corpus):
        document = self.json(path)
        if document.get('record_type') != 'harness_candidate_batch_proposals/v2':
            raise ValueError('proposal_version_unsupported')
        for row in document['proposals']:
            try:
                package = CataloguePackage(tuple(CataloguePackageFile.from_dict({k: f[k] for k in
                    ('path', 'digest', 'size_bytes', 'media_type', 'role')}) for f in row['files']))
                files = {f['path']: f for f in row['files']}
                def read(entry, file_records=files):
                    raw = base64.b64decode(file_records[entry.path]['content_base64'], validate=True)
                    if len(raw) != entry.size_bytes or sha(raw) != entry.digest:
                        raise ValueError('proposal_payload_mismatch')
                    return raw
                yield self.subject(corpus, path, row['id'], package, read,
                                   component_type=row['kind'], lifecycle='unprepared_proposal')
            except (ValueError, KeyError, StopIteration) as error:
                self.excluded(path, row.get('id', '?'), type(error).__name__ + ':' + str(error))

    def tree(self, root, corpus):
        root = Path(root)
        before = sorted(root.rglob('items.json'))
        for file in before:
            try:
                yield from self.catalogue(file, corpus)
            except (ValueError, OSError) as error:
                self.excluded(file, '?', type(error).__name__ + ':' + str(error))
        proposal_files = sorted(root.rglob('proposals.json'))
        for file in proposal_files:
            try:
                yield from self.proposals(file, corpus)
            except (ValueError, OSError) as error:
                self.excluded(file, '?', type(error).__name__ + ':' + str(error))
        after = sorted(root.rglob('items.json'))
        self.collection_notes.append({'source': str(root), 'catalogues_at_start': len(before),
            'proposal_files': len(proposal_files), 'catalogues_at_end': len(after),
            'new_catalogues_during_read': sorted(str(p) for p in set(after) - set(before)),
            'raw_unmaterialized_source_files': 'not treated as candidate packages'})
