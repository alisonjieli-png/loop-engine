"""Compose reviewed additions into an exact current catalogue baseline, never admit content.

The existing catalogue bundle/version/body-store owners validate every input.
Unchanged rows retain their bytes and item versions; only declared changes are
allowed. The result is a full metadata snapshot with delta-only blobs, plus a
private operator proof that is not uploaded as catalogue material. This tool is
ordinary operator orchestration, not a runtime, registry or access-grant owner.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace

from loop_engine.core.service_runtime.catalogue_bundle import (
    canonical_bytes, read_bundle, strict_json, validated_attributes, write_bundle,
)
from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore
from loop_engine.core.service_runtime.catalogue_releases import _changes, content_digest, release_digest
from loop_engine.core.service_runtime.http_entrypoint import HostFamilyPolicy, HostLicensePolicy
from loop_engine.core.service_runtime.records import ServiceRuntimeError

REQUEST_VERSION = 'catalogue_reconciliation_request/v1'
PROOF_VERSION = 'catalogue_reconciliation_proof/v1'
RESULT_VERSION = 'catalogue_reconciliation_result/v1'
PROOF_FILE = 'reconciliation.json'
MAX_CONTROL_BYTES = 32 * 1024 * 1024
MAX_CHANGES = 200000
REPOSITORY = Path(__file__).resolve().parents[1]


def _sha(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('an exact SHA-256 is required')
    return value


def _identity(value):
    if not isinstance(value, str) or not value or len(value) > 1000 or not value.isprintable():
        raise ValueError('a bounded item identity is required')
    return value


def _shape(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('unsupported reconciliation record shape')


def read_control(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or not path.is_file() or path.stat().st_size > MAX_CONTROL_BYTES:
        raise ValueError('a control is a bounded regular absolute file without links')
    raw = path.read_bytes()
    if len(raw) > MAX_CONTROL_BYTES:
        raise ValueError('control grew beyond its byte bound')
    return raw, strict_json(raw, 'reconciliation_json_invalid')


@dataclass(frozen=True)
class Changes:
    """Passive operator declarations, not admission or effect authority."""
    base_release: str
    base_bundle_digest: str
    additions: tuple
    replacements: tuple
    withdrawals: tuple

    def __post_init__(self):
        _sha(self.base_release)
        _sha(self.base_bundle_digest)
        if any(type(value) is not tuple or len(value) > MAX_CHANGES
               for value in (self.additions,self.replacements,self.withdrawals)):
            raise ValueError('typed change declarations are bounded immutable tuples')
        names = list(self.additions)
        for row in self.replacements:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError('a replacement binds one expected version')
            names.append(row[0])
            _sha(row[1])
        for row in self.withdrawals:
            if type(row) is not tuple or len(row) != 3:
                raise ValueError('a withdrawal binds one expected version and note')
            names.append(row[0])
            _sha(row[1])
            if not isinstance(row[2],str) or not row[2].strip() or len(row[2]) > 400 or not row[2].isprintable():
                raise ValueError('a withdrawal needs a bounded explicit note')
        for name in names:
            _identity(name)
        if len(names) != len(set(names)) or len(names) > MAX_CHANGES:
            raise ValueError('declarations cannot duplicate or overlap identities')

    @classmethod
    def from_dict(cls, value):
        _shape(value, ('record_type','base_release','base_bundle_digest','additions','replacements','withdrawals'))
        if value['record_type'] != REQUEST_VERSION:
            raise ValueError('unsupported reconciliation request version')
        for name in ('additions','replacements','withdrawals'):
            if not isinstance(value[name], list) or len(value[name]) > MAX_CHANGES:
                raise ValueError('change declarations are bounded lists')
        adds = tuple(_identity(identity) for identity in value['additions'])
        replacements, withdrawals = [], []
        for row in value['replacements']:
            _shape(row, ('identity','expected_version'))
            replacements.append((_identity(row['identity']), _sha(row['expected_version'])))
        for row in value['withdrawals']:
            _shape(row, ('identity','expected_version','note'))
            note = row['note']
            if not isinstance(note, str) or not note.strip() or len(note) > 400 or not note.isprintable():
                raise ValueError('a withdrawal needs a bounded explicit note')
            withdrawals.append((_identity(row['identity']), _sha(row['expected_version']), note))
        names = adds + tuple(row[0] for row in replacements) + tuple(row[0] for row in withdrawals)
        if len(names) != len(set(names)) or len(names) > MAX_CHANGES:
            raise ValueError('declarations cannot duplicate or overlap identities')
        return cls(_sha(value['base_release']), _sha(value['base_bundle_digest']), adds,
                   tuple(replacements), tuple(withdrawals))

    def to_dict(self):
        return {'record_type': REQUEST_VERSION, 'base_release': self.base_release,
                'base_bundle_digest': self.base_bundle_digest, 'additions': list(self.additions),
                'replacements': [{'identity':identity,'expected_version':version} for identity,version in self.replacements],
                'withdrawals': [{'identity':identity,'expected_version':version,'note':note} for identity,version,note in self.withdrawals]}


def load_bundle(folder, accepted_licenses):
    return read_bundle(Path(folder), license_policy=HostLicensePolicy(tuple(accepted_licenses)),
                       family_policy=HostFamilyPolicy(), verify_blobs=False)


def bundle_rows(bundle):
    rows = {}
    with (bundle.folder/'items.jsonl').open('rb') as stream:
        for line in stream:
            value = strict_json(line, 'reconciliation_item_invalid')
            if canonical_bytes(value) + b'\n' != line:
                raise ValueError('baseline/update rows must be canonical to preserve their exact bytes')
            rows[value['reference']['identity']] = value
    if set(rows) != {item.identity for item in bundle.items}:
        raise ValueError('bundle changed after validation')
    # Recheck the stream binding, not only its identity set.
    if hashlib.sha256((bundle.folder/'bundle.json').read_bytes()).hexdigest() != bundle.digest:
        raise ValueError('bundle header changed after validation')
    header = json.loads((bundle.folder/'bundle.json').read_bytes())
    if hashlib.sha256((bundle.folder/'items.jsonl').read_bytes()).hexdigest() != header['items_digest']:
        raise ValueError('bundle rows changed after validation')
    return rows


def bundle_content(bundle):
    return content_digest(bundle.schema.digest, tuple((item.identity,item.version) for item in bundle.items))


def require_live_base(base, changes, observed):
    """Bind a complete release inventory to the public, versioned live observation."""
    if not isinstance(changes, Changes) or base.digest != changes.base_bundle_digest:
        raise ValueError('baseline header differs from the declaration')
    if (not isinstance(observed, dict) or observed.get('record_type') != 'service_catalogue_view/v1'
            or observed.get('release_id') != changes.base_release
            or observed.get('content_digest') != bundle_content(base)
            or observed.get('schema_digest') != base.schema.digest
            or type(observed.get('items')) is not int or type(observed.get('withdrawn_left_out')) is not int
            or observed['items'] < 0 or observed['withdrawn_left_out'] < 0
            or observed['items'] + observed['withdrawn_left_out'] != len(base.items)):
        raise ValueError('live baseline release/content/schema/population differs; stop and reconcile')


@dataclass(frozen=True)
class Composed:
    rows: dict
    versions: dict
    withdrawals: tuple


def _declared(base, changes):
    if not isinstance(changes, Changes) or base.digest != changes.base_bundle_digest:
        raise ValueError('baseline header differs from the declaration')
    versions = {item.identity:item.version for item in base.items}
    if set(changes.additions) & set(versions):
        raise ValueError('an addition already exists in the baseline')
    for identity, version in (*changes.replacements, *((i,v) for i,v,_ in changes.withdrawals)):
        if versions.get(identity) != version:
            raise ValueError('an expected version is absent or stale')
    return versions


def _batch_only(before, after):
    a, b = json.loads(json.dumps(before)), json.loads(json.dumps(after))
    a['attributes'].pop('batch', None)
    b['attributes'].pop('batch', None)
    return a == b and before != after


def validate_result(base, candidate, changes):
    """Reject lost live rows, undeclared changes and internal batch-only version churn."""
    old_versions = _declared(base, changes)
    old, new = bundle_rows(base), bundle_rows(candidate)
    removed = {identity for identity,_,_ in changes.withdrawals}
    replaced = {identity for identity,_ in changes.replacements}
    if (candidate.schema.to_dict() != base.schema.to_dict()
            or set(new) != (set(old) - removed) | set(changes.additions)):
        raise ValueError('baseline preservation failed: identities or schema changed without declarations')
    new_versions = {item.identity:item.version for item in candidate.items}
    for identity in set(old) - removed:
        if identity not in replaced:
            if old[identity] != new[identity] or old_versions[identity] != new_versions[identity]:
                raise ValueError('baseline preservation failed: an undeclared row or version changed')
        elif _batch_only(old[identity], new[identity]):
            raise ValueError('batch-only retagging is not a replacement')
        elif old_versions[identity] == new_versions[identity]:
            raise ValueError('an explicit replacement must change its version')
    wanted = tuple(sorted(({'identity':i,'note':note} for i,_,note in changes.withdrawals), key=lambda row:row['identity']))
    if tuple(candidate.withdrawals) != wanted:
        raise ValueError('withdrawals differ from the explicit declarations')
    return Composed(new, new_versions, wanted)


def compose(base, updates, changes):
    old_versions = _declared(base, changes)
    rows, versions, incoming = bundle_rows(base), dict(old_versions), {}
    expected = set(changes.additions) | {identity for identity,_ in changes.replacements}
    for update in updates:
        if update.withdrawals:
            raise ValueError('withdrawals belong to explicit declarations, not update bundles')
        values = bundle_rows(update)
        for row in values.values():
            # A small admitted add-on can declare a subset schema. Its actual
            # rows must still fit the unchanged live schema; no schema merging.
            validated_attributes(base.schema, row['attributes'])
        if set(incoming) & set(values):
            raise ValueError('update bundles repeat an identity')
        incoming.update(values)
        versions.update({item.identity:item.version for item in update.items})
    if set(incoming) != expected:
        raise ValueError('update identities differ from the explicit change declarations')
    for identity,_ in changes.replacements:
        if _batch_only(rows[identity], incoming[identity]):
            raise ValueError('batch-only retagging is not a replacement')
        if old_versions[identity] == versions[identity]:
            raise ValueError('an explicit replacement must change its version')
    rows.update(incoming)
    for identity,_,_ in changes.withdrawals:
        del rows[identity]
        del versions[identity]
    if not rows:
        raise ValueError('the current bundle contract requires a nonempty catalogue')
    return Composed(rows, versions, tuple(sorted(({'identity':i,'note':note} for i,_,note in changes.withdrawals),key=lambda r:r['identity'])))


def _payload(file, stores):
    for store in stores:
        try:
            return store.read(file.digest, file.size_bytes)
        except ServiceRuntimeError as error:
            if error.code != 'body_missing':
                raise
    raise ValueError('a required baseline or update blob is missing; supply explicit body roots')


def verify_files(bundle, extra_roots=()):
    stores = (bundle.blobs(), *(VolumeBodyStore(str(Path(root))) for root in extra_roots))
    files = {}
    for item in bundle.items:
        for file in item.package.files:
            if file.digest in files and files[file.digest].size_bytes != file.size_bytes:
                raise ValueError('one file digest cannot declare conflicting byte sizes')
            files[file.digest] = file
    for file in files.values():
        _payload(file, stores)
    return files


def proof_for(base, candidate, changes):
    result = validate_result(base, candidate, changes)
    changed = _changes(SimpleNamespace(items=tuple((item.identity,item.version) for item in base.items)),
                       candidate, {identity for identity,_,_ in changes.withdrawals})
    release = changes.base_release if bundle_content(base) == bundle_content(candidate) and not changes.withdrawals else release_digest({
        'record_type':'catalogue_release/v1', 'schema_digest':candidate.schema.digest,
        'items':[[item.identity,item.version] for item in candidate.items], 'based_on':changes.base_release,
        'changes':changed, 'notes':candidate.notes})
    return {'record_type':PROOF_VERSION, 'changes':changes.to_dict(),
            'base_content_digest':bundle_content(base), 'bundle_digest':candidate.digest,
            'result_release':release, 'result_content_digest':bundle_content(candidate),
            'unchanged_items':len(base.items)-len(changes.replacements)-len(changes.withdrawals),
            'additions':{identity:result.versions[identity] for identity in changes.additions},
            'replacements':{identity:result.versions[identity] for identity,_ in changes.replacements},
            'body_mode':'full_metadata_snapshot_delta_blobs'}


def check_proof(base, candidate, proof):
    _shape(proof, ('record_type','changes','base_content_digest','bundle_digest','result_release','result_content_digest','unchanged_items','additions','replacements','body_mode'))
    if proof['record_type'] != PROOF_VERSION:
        raise ValueError('unsupported reconciliation proof version')
    if type(proof['unchanged_items']) is not int or proof['unchanged_items'] < 0:
        raise ValueError('proof counts are nonnegative integers, never booleans')
    changes = Changes.from_dict(proof['changes'])
    if proof != proof_for(base, candidate, changes):
        raise ValueError('reconciliation proof differs from exact bundle contents')
    return changes


def write_reconciled(base, updates, changes, output, observed, *, extra_roots=(), notes=''):
    require_live_base(base, changes, observed)
    result = compose(base, updates, changes)
    output = Path(output)
    if not output.is_absolute() or output.resolve() != output or output == REPOSITORY or REPOSITORY in output.parents:
        raise ValueError('write a new plain absolute bundle folder outside the repository')
    # A delta-only baseline is not called complete. Every referenced file must
    # resolve through its own blob folder or explicit read-only extra roots.
    held = verify_files(base, extra_roots)
    for update in updates:
        checked = verify_files(update, (base.folder/'blobs', *extra_roots))
        for digest, file in checked.items():
            if digest in held and held[digest].size_bytes != file.size_bytes:
                raise ValueError('one file digest cannot declare conflicting byte sizes')
    stores = tuple(update.blobs() for update in updates) + (base.blobs(),) + tuple(VolumeBodyStore(str(Path(root))) for root in extra_roots)
    new_files = {file.digest:file for update in updates for item in update.items for file in item.package.files if file.digest not in held}
    payloads = [_payload(file, stores) for file in new_files.values()]
    # Change notes belong to one release, not to unchanged item versions.
    # Withdrawal reasons already live in the explicit withdrawal rows. Do not
    # replay historical notes or duplicate them beyond the header's item bound.
    write_bundle(output, schema=base.schema, lines=result.rows.values(), payloads=payloads,
                 notes=notes, withdrawals=result.withdrawals)
    accepted = tuple(sorted({item.item.license_name for item in base.items} | {item.item.license_name for update in updates for item in update.items}))
    candidate = load_bundle(output, accepted)
    proof = proof_for(base, candidate, changes)
    raw = canonical_bytes(proof) + b'\n'
    with (output/PROOF_FILE).open('xb') as stream:
        stream.write(raw)
    return {'record_type':RESULT_VERSION, 'state':'written', 'base_release':changes.base_release, 'bundle_digest':candidate.digest,
            'reconciliation_digest':hashlib.sha256(raw).hexdigest(), 'items':len(candidate.items),
            'new_blob_count':len(new_files), 'new_blob_bytes':sum(len(payload) for payload in payloads),
            'body_mode':'full_metadata_snapshot_delta_blobs', 'base_bodies_verified':len(held)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-bundle', type=Path, required=True)
    parser.add_argument('--update-bundle', action='append', type=Path, default=[])
    parser.add_argument('--changes', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--body-root', action='append', type=Path, default=[])
    parser.add_argument('--accept-license', action='append', default=[])
    parser.add_argument('--notes', default='')
    parser.add_argument('--write', action='store_true')
    options = parser.parse_args(argv)
    try:
        _, value = read_control(options.changes)
        changes = Changes.from_dict(value)
        licenses = tuple(options.accept_license) or ('MIT',)
        base = load_bundle(options.base_bundle, licenses)
        updates = tuple(load_bundle(path, licenses) for path in options.update_bundle)
        from publish_catalogue_delta import active_catalogue
        observed = active_catalogue()
        require_live_base(base, changes, observed)
        composed = compose(base, updates, changes)
        if options.write:
            result = write_reconciled(base, updates, changes, options.output, observed,
                                      extra_roots=options.body_root, notes=options.notes)
        else:
            result = {'record_type':RESULT_VERSION, 'state':'checked_metadata_only_no_write',
                      'base_release':changes.base_release, 'items':len(composed.rows)}
    except (OSError, ValueError, ServiceRuntimeError) as error:
        print(json.dumps({'record_type':RESULT_VERSION,'refused':True,'code':getattr(error,'code','reconciliation_refused'),'message':str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
