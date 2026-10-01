"""Selected host maintenance uses real temporary SQLite/bodies, never production."""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from test_grant_operator_bootstrap import configured
from loop_engine.core.practitioner_runtime.provisioning import _item
from loop_engine.core.provisioning_server import ProvisioningItemBinding
from loop_engine.core.service_runtime import catalogue_releases as releases, catalogue_search, catalogue_serving
from loop_engine.core.service_runtime import public_good_operator as operator, public_good_selection as selection
from loop_engine.core.service_runtime.catalogue_bundle import canonical_bytes
from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore, sha256_hex
from loop_engine.core.service_runtime.http_entrypoint import HostLicensePolicy
from loop_engine.core.service_runtime.public_good import PublicGoodAccess, PublicGoodGrant, PublicGoodLimits
from loop_engine.core.service_runtime.records import ServiceCommitUnknown, ServiceRuntimeError
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding


class SelectedPolicyOperatorTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory(prefix='public-good-selection-')
        self.addCleanup(self.folder.cleanup)
        self.case, self.host, self.configuration = configured(Path(self.folder.name))
        self.binding = self.case.runtime._catalog
        with self.binding.store() as store:
            _, pointer = releases.read_pointer(self.binding, store)
            self.header = releases.load_release_header(self.binding, store, pointer['release_id'])
            self.version = dict(self.header.items)['keeper']
            self.payload = releases.load_item_version(self.binding, store, 'keeper', self.version)
        item = _item(self.payload['reference'])
        self.grant = PublicGoodGrant(ProvisioningItemBinding.from_item(item), self.version, self.payload['approval_ref'],
            'fixture-rights', (4,), 'Synthetic selected operator check', int(self.case.runtime._now()) + 3600,
            useful_paths=('SKILL.md',))
        self.grants = (self.grant,)
        self.request = {'record_type': operator.REQUEST_VERSION, 'expected_release': self.header.release_id,
            'expected_version': None, 'grants': [asdict(self.grant)], 'limits': asdict(PublicGoodLimits())}
        self.policy = Path(self.folder.name) / 'policy.json'

    def raw(self):
        return json.dumps(self.request).encode()

    def load(self, **changes):
        fields = {'expected_release': self.request['expected_release'], 'license_policy': self.case.license_policy,
                  'family_policy': self.case.family_policy, **changes}
        return selection.load_selection(self.binding, self.case.settings, self.grants, **fields)

    def code(self, action):
        try:
            action()
        except ServiceRuntimeError as error:
            return error.code
        return None

    def cli(self, *arguments):
        self.policy.write_bytes(self.raw())
        with redirect_stdout(StringIO()) as output:
            status = operator.main(['--config', str(self.host), '--policy', str(self.policy), *arguments])
        return status, json.loads(output.getvalue())

    def read(self, kind, logical):
        with self.binding.store() as store:
            return self.binding.read(store, kind, logical)

    def put(self, kind, logical, payload):
        """Canonical, scoped fixture corruption; no raw SQL or external store."""
        with self.binding.store(write=True) as store:
            held = self.binding.read(store, kind, logical)
            row = self.binding.record(kind, logical, payload)
            self.binding.commit(store, (row,), (self.binding.guard(held, row['record_id']),))

    def changed_header(self, document):
        identity = releases.release_digest(document)
        self.put(releases.RELEASE_KIND, identity, {**document, 'release_id': identity})
        row = self.read(releases.POINTER_KIND, releases.POINTER_LOGICAL)
        self.put(releases.POINTER_KIND, releases.POINTER_LOGICAL, {**row['payload'], 'release_id': identity})
        self.request['expected_release'] = identity

    def forge_item(self, change):
        payload = json.loads(json.dumps(self.payload))
        change(payload)
        version = sha256_hex(canonical_bytes(payload))
        self.put(releases.ITEM_KIND, version, payload)
        document = {**self.header.document, 'items': [[identity, version if identity == 'keeper' else old]
                                                     for identity, old in self.header.items]}
        self.changed_header(document)
        self.grants = (replace(self.grant, item_version=version),)
        self.request['grants'] = [asdict(self.grants[0])]

    def test_cli_plan_reads_only_selected_files_without_search_or_serving_loader(self):
        calls, writes = [], []
        body_read, store_open = VolumeBodyStore.read, ServiceCatalogBinding.store
        def measured(store, digest, size):
            calls.append((digest, size))
            return body_read(store, digest, size)
        def opened(binding, *, write=False):
            writes.append(write)
            return store_open(binding, write=write)
        with mock.patch.object(VolumeBodyStore, 'read', measured), mock.patch.object(ServiceCatalogBinding, 'store', opened), \
             mock.patch.object(catalogue_serving, 'load_catalogue_view', side_effect=AssertionError('full loader')), \
             mock.patch.object(catalogue_search, 'ReleaseSearchIndex', side_effect=AssertionError('search construction')):
            status, result = self.cli()
        self.assertEqual(status, 0)
        self.assertFalse(result['applied'])
        self.assertEqual(result['selection']['full_release_membership_count'], 3)
        self.assertEqual(result['selection']['selected_versions_verified'], 1)
        self.assertEqual(result['selection']['selected_file_placements_verified'], 1)
        self.assertFalse(result['selection']['full_catalogue_bodies_verified'])
        self.assertEqual(len(calls), 1)
        self.assertFalse(any(writes))
        self.assertNotIn(self.folder.name, json.dumps(result))

    def test_selected_facts_cannot_be_installed_as_a_serving_view(self):
        picked = self.load()
        self.assertNotIsInstance(picked, catalogue_serving.CatalogueView)
        self.assertFalse(hasattr(picked, 'body_reader'))
        self.assertFalse(hasattr(picked, 'search_index'))
        binding = self.case.binding()
        self.assertEqual(self.code(lambda: binding.install_view(picked)), 'invalid_provisioning_binding')

    def test_selected_corrupt_body_refuses_and_unselected_corruption_is_not_claimed_verified(self):
        with self.binding.store() as store:
            other = releases.load_item_version(self.binding, store, 'denied', dict(self.header.items)['denied'])
        for payload, expected in ((other, None), (self.payload, 'body_digest_mismatch')):
            file = payload['package']['files'][0]
            path = self.case.root / 'bodies' / VolumeBodyStore.object_key(file['digest'])
            path.chmod(0o600)
            path.write_bytes(b'!' * file['size_bytes'])
            self.assertEqual(self.code(self.load), expected)
        self.assertEqual(self.code(self.case.view), 'body_digest_mismatch')

    def test_full_header_hash_guard_and_its_known_wrong_removed_control(self):
        self.put(releases.RELEASE_KIND, self.header.release_id, {**self.header.document, 'notes': 'altered'})
        self.assertEqual(self.code(self.load), 'catalogue_release_digest_mismatch')
        with mock.patch.object(releases, 'release_digest', return_value=self.header.release_id):
            self.assertIsNone(self.code(self.load), 'removed header guard control did not accept its planted corruption')

    def test_duplicate_or_invalid_full_membership_refuses_even_outside_selection(self):
        for member in (self.header.document['items'][0], ['unselected', 'not-a-digest']):
            self.changed_header({**self.header.document, 'items': [*self.header.document['items'], member]})
            self.assertEqual(self.code(self.load), 'catalogue_release_digest_mismatch')

    def test_changed_selected_version_and_wrong_item_record_digest_refuse(self):
        self.grants = (replace(self.grant, item_version='f' * 64),)
        self.assertEqual(self.code(self.load), 'public_good_grant_not_current')
        self.grants = (self.grant,)
        self.put(releases.ITEM_KIND, self.version, {**self.payload, 'approval_ref': 'changed-ref'})
        self.assertEqual(self.code(self.load), 'catalogue_release_digest_mismatch')

    def test_missing_selected_version_refuses_through_canonical_reader(self):
        original = ServiceCatalogBinding.read
        def missing(binding, store, kind, logical):
            if kind == releases.ITEM_KIND and logical == self.version:
                return None
            return original(binding, store, kind, logical)
        with mock.patch.object(ServiceCatalogBinding, 'read', missing):
            self.assertEqual(self.code(self.load), 'catalogue_release_incomplete')

    def test_schema_content_or_version_refuses(self):
        schema = json.loads(json.dumps(self.header.schema.to_dict()))
        schema['attributes'][0]['description'] = 'altered description'
        self.put(releases.SCHEMA_KIND, self.header.schema.digest, schema)
        self.assertEqual(self.code(self.load), 'catalogue_release_digest_mismatch')
        schema['record_type'] = 'unknown-schema/v999'
        self.put(releases.SCHEMA_KIND, self.header.schema.digest, schema)
        self.assertEqual(self.code(self.load), 'catalogue_record_unsupported')

    def test_rehashed_invalid_admission_reference_refuses(self):
        self.forge_item(lambda payload: payload.update(approval_ref=''))
        self.assertEqual(self.code(self.load), 'explicit_host_review_required')

    def test_rehashed_undeclared_attributes_refuse(self):
        self.forge_item(lambda payload: payload.update(attributes={'undeclared': 'value'}))
        self.assertEqual(self.code(self.load), 'attribute_not_declared')

    def test_rehashed_reference_package_mismatch_refuses(self):
        self.forge_item(lambda payload: payload['reference'].update(size_bytes=payload['reference']['size_bytes'] + 1))
        self.assertEqual(self.code(self.load), 'bundle_item_digest_mismatch')

    def test_rehashed_executable_without_declared_effect_refuses(self):
        self.forge_item(lambda payload: payload['package']['files'][0].update(role='executable_tool'))
        self.assertEqual(self.code(self.load), 'package_executable_effect_undeclared')

    def test_host_policy_and_exact_useful_path_guards_are_preserved(self):
        self.assertEqual(self.code(lambda: self.load(license_policy=HostLicensePolicy(accepted_licenses=()))), 'item_license_not_accepted')
        with mock.patch.object(type(self.case.family_policy), 'refusal', return_value='item_family_not_accepted'):
            self.assertEqual(self.code(self.load), 'item_family_not_accepted')
        self.grants = (replace(self.grant, useful_paths=('missing.py',)),)
        self.assertEqual(self.code(self.load), 'public_good_grant_not_current')

    def test_withdrawn_and_unknown_withdrawal_versions_refuse(self):
        releases.withdraw(self.case.context, identity='keeper', item_version=self.version, note_text='synthetic withdrawal')
        self.assertEqual(self.code(self.load), 'public_good_grant_not_current')
        self.put(releases.WITHDRAWAL_KIND, ('keeper', self.grant.binding.body_digest), {'record_type': 'unknown-withdrawal/v999'})
        self.assertEqual(self.code(self.load), 'catalogue_record_unsupported')

    def test_state_or_pointer_change_during_selected_body_verification_refuses(self):
        original = releases.verify_release_bodies
        def changed(*args, **kwargs):
            original(*args, **kwargs)
            row = self.read(releases.POINTER_KIND, releases.POINTER_LOGICAL)
            self.put(releases.POINTER_KIND, releases.POINTER_LOGICAL, {**row['payload'], 'release_id': 'e' * 64})
        with mock.patch.object(releases, 'verify_release_bodies', changed):
            self.assertEqual(self.code(self.load), 'public_good_release_changed')
        row = self.read(releases.POINTER_KIND, releases.POINTER_LOGICAL)
        self.put(releases.POINTER_KIND, releases.POINTER_LOGICAL, {**row['payload'], 'release_id': self.header.release_id})
        def state_changed(*args, **kwargs):
            original(*args, **kwargs)
            row = self.read(releases.STATE_KIND, releases.STATE_LOGICAL)
            self.put(releases.STATE_KIND, releases.STATE_LOGICAL, {**row['payload'], 'revision': row['payload']['revision'] + 1})
        with mock.patch.object(releases, 'verify_release_bodies', state_changed):
            self.assertEqual(self.code(self.load), 'catalogue_state_changed')

    def test_empty_previous_policy_cannot_accept_stale_plan_and_removed_guard_is_detected(self):
        picked = self.load()
        full = self.case.view()
        row = self.read(releases.STATE_KIND, releases.STATE_LOGICAL)
        self.put(releases.STATE_KIND, releases.STATE_LOGICAL, {**row['payload'], 'revision': row['payload']['revision'] + 1})
        for view in (picked, full):
            self.assertEqual(self.code(lambda: operator.apply_policy(self.case.runtime, view, self.raw())), 'catalogue_state_changed')
        with mock.patch.object(operator, '_current', return_value=None):
            self.assertIsNone(self.code(lambda: operator.apply_policy(self.case.runtime, picked, self.raw())),
                              'removed current-state guard did not reproduce the stale empty-policy plan')

    def test_actual_apply_keeps_digest_cas_and_never_claims_a_full_serving_load(self):
        status, _ = self.cli('--apply', '--expected-digest', 'f' * 64)
        self.assertEqual(status, 1)
        self.assertEqual(PublicGoodAccess(self.case.runtime).snapshot(self.load()).version, '')
        status, result = self.cli('--apply', '--expected-digest', hashlib.sha256(self.raw()).hexdigest())
        self.assertEqual(status, 0)
        self.assertTrue(result['applied'])
        self.assertFalse(result['selection']['serving_view_installed'])
        status, refused = self.cli('--apply', '--expected-digest', hashlib.sha256(self.raw()).hexdigest())
        self.assertEqual(status, 1)
        self.assertEqual(refused['code'], 'public_good_policy_changed')

    def test_unknown_application_is_called_once_and_preserves_unknown_code(self):
        configure = PublicGoodAccess.configure
        def committed_unknown(access, *args, **kwargs):
            configure(access, *args, **kwargs)
            raise ServiceCommitUnknown()
        with mock.patch.object(PublicGoodAccess, 'configure', autospec=True, side_effect=committed_unknown) as apply:
            status, result = self.cli('--apply', '--expected-digest', hashlib.sha256(self.raw()).hexdigest())
        self.assertEqual(status, 1)
        self.assertEqual(result['code'], 'commit_unknown')
        self.assertEqual(apply.call_count, 1)
        self.assertTrue(PublicGoodAccess(self.case.runtime).snapshot(self.load()).version,
                        'unknown must not be described as rolled back or not applied')

    def test_exact_2048_well_typed_requests_are_accepted_by_parser(self):
        compact = replace(self.grant, approval_ref='a', rights_ref='r', public_benefit_reason='p', useful_paths=())
        values = [asdict(replace(compact, binding=replace(compact.binding, identity='synthetic_%04d' % number,
                                                        source_ref='synthetic'))) for number in range(2048)]
        raw = json.dumps({**self.request, 'grants': values}, separators=(',', ':')).encode()
        self.assertLess(len(raw), operator.MAXIMUM_POLICY_BYTES)
        self.assertEqual(len(operator.read_request(raw)[1]), 2048)

    def test_2048_and_two_megabyte_caps_refuse_before_host_or_grant_reads(self):
        too_many = {**self.request, 'grants': [{}] * 2049}
        with mock.patch.object(PublicGoodGrant, 'from_dict', side_effect=AssertionError('over-limit parsing')):
            self.assertEqual(self.code(lambda: operator.read_request(json.dumps(too_many).encode())), 'public_good_selection_limit')
            self.assertEqual(self.code(lambda: operator.read_request(b' ' * 2_000_001)), 'public_good_policy_file_invalid')
        self.grants = (self.grant,) * 2049
        with mock.patch.object(ServiceCatalogBinding, 'store', side_effect=AssertionError('over-limit store read')):
            self.assertEqual(self.code(self.load), 'public_good_selection_limit')
        self.grants = (self.grant, self.grant)
        self.assertEqual(self.code(self.load), 'public_good_grant_not_current')

    def test_invalid_file_record_and_apply_types_refuse_before_effects(self):
        self.policy.write_bytes(self.raw())
        symlink = Path(self.folder.name) / 'policy-link.json'
        symlink.symlink_to(self.policy)
        with redirect_stdout(StringIO()), mock.patch.object(operator, 'host_selection', side_effect=AssertionError('invalid file opened host')):
            self.assertEqual(operator.main(['--config', str(self.host), '--policy', str(symlink)]), 1)
        fifo = Path(self.folder.name) / 'not-a-policy-fifo'
        os.mkfifo(fifo)
        self.assertEqual(self.code(lambda: operator.read_policy_file(fifo)), 'public_good_policy_file_invalid')
        for apply in ('yes', 1, None):
            self.assertEqual(self.code(lambda: operator.apply_policy(self.case.runtime, self.load(), self.raw(), apply=apply)),
                             'public_good_policy_file_invalid')
        self.request['record_type'] = 'service_public_good_policy_request/v999'
        self.policy.write_bytes(self.raw())
        with redirect_stdout(StringIO()), mock.patch.object(operator, 'host_selection', side_effect=AssertionError('invalid record opened host')):
            self.assertEqual(operator.main(['--config', str(self.host), '--policy', str(self.policy)]), 1)


if __name__ == '__main__':
    unittest.main()
