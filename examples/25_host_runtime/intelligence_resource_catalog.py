"""Managed descriptor records projected into the existing intelligence search.

This host example owns no database format, SQL, mutable head, or revision writer.
RecordOperationService owns CRUD. ArtifactStore owns exact bodies. Search uses
the four existing layers. Catalog discovery never grants execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.context_artifacts import ContextArtifactRef
from loop_engine.core.intelligence_layers import (
    LAYERS, IntelligenceSearchRequest, IntelligenceSearchContext, query_intelligence)
from loop_engine.core.record_operations import (
    RecordOperationService, RecordOperationServices, RecordStorageBinding)
from loop_engine.core.record_operations_records import (
    RecordOperationPolicy, RecordOperationRequest, RecordScope, canonical_json, parse_json)
from loop_engine.core.runtime_observer import RuntimeObservationServices
from loop_engine.core.store_serve import StoreRecord
from loop_engine.loop.effect_approval import ApprovalRequest, EffectApprovalService
from loop_engine.loop.recursive_loop import LoopLedger

RESOURCE_LAYERS = {'context': 'context_intelligence', 'skill': 'context_intelligence',
    'plugin': 'code_intelligence', 'tool': 'code_intelligence',
    'module': 'code_intelligence', 'command_line_tool': 'code_intelligence'}


def descriptor_policy(layer):
    if layer not in set(RESOURCE_LAYERS.values()):
        raise ValueError('unsupported descriptor layer')
    fields = {'resource_id': {'type': 'string', 'minLength': 1},
        'version': {'type': 'string', 'minLength': 1},
        'reference': {'type': 'string', 'minLength': 1},
        'kind': {'enum': [kind for kind, target in RESOURCE_LAYERS.items() if target == layer]},
        'description': {'type': 'string', 'maxLength': 4000},
        'relative_path': {'type': 'string'}, 'artifact_ref': {'type': 'object'},
        'source_metadata': {'type': 'object'}}
    return RecordOperationPolicy('host.resource-descriptors.v1.' + layer,
        RecordScope('host.resources.' + layer, 'learned', layer, 'intelligence_record', 'resource.'),
        canonical_json({'type': 'object', 'required': list(fields),
                        'properties': fields, 'additionalProperties': False}),
        indexed_fields=('reference', 'resource_id', 'version', 'kind'), maximum_query_results=1000)


def record_id(reference):
    return 'resource.' + hashlib.sha256(reference.encode()).hexdigest()


def _validate_descriptor(document):
    reference = ContextArtifactRef.from_dict(document['artifact_ref'])
    expected = document['resource_id'] + '@' + document['version'] + '#sha256:' + reference.digest
    if expected != document['reference']:
        raise ValueError('descriptor reference does not bind its exact version and artifact')
    path = Path(document['relative_path'])
    if path.is_absolute() or '..' in path.parts or '\\' in str(path):
        raise ValueError('descriptor path is not a confined relative source location')
    return RESOURCE_LAYERS[document['kind']]


@dataclass(frozen=True)
class DescriptorSnapshot:
    """Frozen JSON avoids mutable aliasing between a search and hydration."""
    records_json: str

    @property
    def records(self):
        return parse_json(self.records_json)

    @property
    def digest(self):
        return hashlib.sha256(self.records_json.encode()).hexdigest()


class ManagedResourceCatalog:
    """A scoped composition of existing record services, not another store."""

    def __init__(self, root, *, runtime=None):
        root = Path(root).absolute()
        if '..' in root.parts or any(path.is_symlink() for path in (root, *root.parents)):
            raise ValueError('catalog paths cannot cross symlinks or traversal')
        self.root = root
        self.runtime = runtime or RuntimeObservationServices(ledger=LoopLedger())
        self.approvals = EffectApprovalService(self.runtime)
        database = root / 'records.sqlite'

        def open_backend(write):
            if any(path.is_symlink() for path in (database, *database.parents)):
                raise ValueError('catalog location changed through a symlink')
            if not write and not database.exists():
                raise FileNotFoundError('catalog_not_created')
            if write:
                root.mkdir(parents=True, exist_ok=True, mode=0o700)
            return SQLiteRecordStore(str(database), read_only=not write)

        binding = RecordStorageBinding('sqlite:' + str(database), str(root / 'artifacts'), open_backend)
        self.services = {layer: RecordOperationService(descriptor_policy(layer),
            RecordOperationServices(binding, self.runtime, self.approvals))
            for layer in set(RESOURCE_LAYERS.values())}

    def publish(self, document, authorize, *, expected_record_version=''):
        """Stage a descriptor candidate, with exact approval and explicit CAS."""
        document = parse_json(canonical_json(document))
        layer = _validate_descriptor(document)
        service = self.services[layer]
        identity = record_id(document['reference'])
        prior = service.execute(RecordOperationRequest('get', identity, materialize=True))
        if prior.status == 'found' and prior.document_json == canonical_json(document):
            return prior
        operation = 'create' if prior.status == 'not_found' else 'update'
        if operation == 'update' and not expected_record_version:
            raise ValueError('changed descriptor requires an explicit expected revision')
        request = RecordOperationRequest(operation, identity,
            expected_record_version=expected_record_version, document_json=canonical_json(document))
        effect = service.effect_for(request)
        approval = ApprovalRequest.create('resource.catalog.publish', effect,
            'Stage this exact source-linked descriptor as a candidate, without promotion.')
        pending = self.approvals.create(approval)
        self.approvals.resume(pending.pending, pending.resume_token, authorize(approval))
        result = service.execute(request, approval_id=approval.request_id)
        if result.committed is not True:
            raise RuntimeError('catalog publication not confirmed: ' + result.status)
        return result

    def snapshot(self, references):
        """Read only host-granted exact references; unknown and retired refs fail."""
        records = []
        for reference in tuple(dict.fromkeys(references)):
            found = []
            for layer, service in self.services.items():
                query = service.execute(RecordOperationRequest('query',
                    filters_json=canonical_json({'reference': reference}), limit=2))
                for card in query.records:
                    if card['record_id'] != record_id(reference) or card['lifecycle'] != 'candidate':
                        continue
                    selected = service.execute(RecordOperationRequest('get', card['record_id'],
                        record_version=card['record_version'], materialize=True))
                    if selected.status != 'found' or not selected.document_json:
                        raise ValueError('selected catalog revision is unavailable')
                    document = parse_json(selected.document_json)
                    if _validate_descriptor(document) != layer or document['reference'] != reference:
                        raise ValueError('selected descriptor identity changed')
                    found.append({'layer': layer, 'card': selected.records[0], 'document': document})
            if len(found) != 1:
                raise ValueError('granted descriptor is missing, retired, or ambiguous')
            records.extend(found)
        return DescriptorSnapshot(canonical_json(records))

    def revalidate(self, snapshot):
        for item in snapshot.records:
            card = item['card']
            current = self.services[item['layer']].execute(RecordOperationRequest('get', card['record_id']))
            if current.status != 'found' or tuple(current.records) != (card,):
                raise PermissionError('descriptor was changed or retired after selection')
        return True

    def loader(self, snapshot, artifact_store):
        """Recheck catalog authority before loading each exact body."""
        def load(reference):
            self.revalidate(snapshot)
            allowed = [ContextArtifactRef.from_dict(item['document']['artifact_ref'])
                       for item in snapshot.records]
            if reference not in allowed:
                raise PermissionError('artifact was not selected through this catalog snapshot')
            body = artifact_store.get(reference)
            if len(body) != reference.byte_count or hashlib.sha256(body).hexdigest() != reference.digest:
                raise ValueError('artifact identity mismatch')
            return body
        return load


def search_snapshot(payload, *, ledger=None):
    """Search descriptor cards through existing Intelligence Query Loops."""
    snapshot = DescriptorSnapshot(payload['snapshot_json'])
    layers = {layer: [] for layer in LAYERS}
    for item in snapshot.records:
        doc = item['document']
        layers[item['layer']].append(StoreRecord(item['card']['record_id'], 'context',
            doc['resource_id'], body={'description': doc['description'],
                'version': doc['version'], 'payload_ref': doc['reference'],
                'body_digest': doc['artifact_ref']['digest'], 'maturity': 'candidate',
                'scope': 'run', 'asset_kind': doc['kind'],
                'entrypoints': doc['source_metadata'].get('entrypoints', [])},
            tags=(doc['kind'], doc['resource_id']), tier='experimental', source='host.resource_catalog'))
    result = query_intelligence(IntelligenceSearchRequest(payload['need'], layers,
        mode='lexical', top_n=payload['limit'], include_candidates=True), IntelligenceSearchContext(ledger=ledger))
    by_id = {item['card']['record_id']: item for item in snapshot.records}
    hits = [{'reference': by_id[hit['record_id']]['document']['reference'],
             'layer': hit['layer'], 'score': hit['score'],
             'intelligence_item_ref': hit['intelligence_item_ref']}
            for hit in result['hits'][:payload['limit']]]
    return {'record_type': 'resource_catalog_search/v1', 'snapshot_digest': snapshot.digest,
            'hits': hits, 'body_materializations': 0, 'promotes_intelligence': False}
