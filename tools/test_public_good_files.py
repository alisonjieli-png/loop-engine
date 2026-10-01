"""Public Good file metadata: synthetic passive records, never a public body read."""
from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import socket
import unittest
from unittest.mock import patch

from loop_engine.core.harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceDraft, item_from_body
from loop_engine.core.provisioning_server import ProvisioningItemBinding, ProvisioningQualificationResolver
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile
from loop_engine.core.service_runtime.catalogue_serving import CatalogueView
from loop_engine.core.service_runtime.public_good import PublicGoodGrant, PublicGoodLimits, PublicGoodSnapshot
from loop_engine.core.service_runtime import public_good_files as files
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding


SHARED = b'SYNTHETIC BODY MUST NEVER BE EXPOSED IN PUBLIC METADATA'
LICENCE = b'Synthetic shared supporting licence bytes'


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def forbidden(*args, **kwargs):
    raise AssertionError('projection attempted a body, resolver, store, file or network effect')


class MetadataFixture:
    def __init__(self):
        self.items, self.packages, self.versions, self.grants = {}, {}, {}, []

    def add(self, identity, entries, useful, *, licence='MIT', goals=(4,), initiatives=('learning',),
            title='', purpose='Accessible classroom arithmetic', benefit='Synthetic lesson support'):
        package = CataloguePackage(tuple(CataloguePackageFile(path, sha(body), len(body) + delta, mime, role)
            for path, body, mime, role, delta in entries))
        item = item_from_body(HarnessIntelligenceDraft(identity, 'skill', purpose, 'harness_local',
            '/private/source/' + identity, licence, declared_effects=('spawns_process',)), package.document().decode())
        self.items[identity], self.packages[identity] = item, package
        version = sha('synthetic-version:' + identity)
        self.versions[identity] = version
        self.grants.append(PublicGoodGrant(ProvisioningItemBinding.from_item(item), version, 'private-review:' + identity,
            '/private/rights/' + identity, goals, benefit, 2000, initiatives=initiatives, useful_paths=useful, display_name=title))

    def view(self):
        return CatalogueView(HarnessIntelligenceCatalogue(self.items), ProvisioningQualificationResolver('no-call', forbidden),
            forbidden, release_id='synthetic-release', state_revision=1, packages=self.packages, item_versions=self.versions,
            withdrawal_check=forbidden, body_store=object(), attributes={'private_metadata': {'private': 'not public'}})

    def snapshot(self):
        return PublicGoodSnapshot(tuple(self.grants), PublicGoodLimits(), 'synthetic-policy', None, None)


def entry(path, body, mime='text/markdown', role='instruction_file', delta=0):
    return path, body, mime, role, delta


def fixture():
    held = MetadataFixture()
    held.add('package.alpha', [entry('guide.md', SHARED), entry('alternate.md', SHARED),
        entry('LICENSE', LICENCE, 'text/plain', 'other'), entry('solver.py', b'Synthetic source fixture', 'text/x-python', 'executable_tool')],
        ('guide.md', 'alternate.md', 'solver.py'), title='Alpha Learning')
    held.add('package.beta', [entry('guides/shared.txt', SHARED, 'text/plain'), entry('LICENSE', LICENCE, 'text/plain', 'other'),
        entry('reference.json', b'{"synthetic":true}', 'application/json', 'skill_reference')], ('guides/shared.txt', 'reference.json'),
        licence='Apache-2.0', goals=(), initiatives=('public-data',), title='Beta Public Data', purpose='Structured public datasets')
    held.add('package.gamma', [entry('support/shared.bin', SHARED, 'application/octet-stream', 'skill_asset'),
        entry('NOTICE', b'Synthetic notice', 'text/plain', 'other')], (), licence='BSD-2-Clause', goals=(),
        initiatives=('related-research',), title='Gamma Context')
    held.add('package.delta', [entry('SUPPORT.md', LICENCE, 'text/markdown', 'skill_reference')], (),
        goals=(13,), initiatives=(), title='Delta Planning')
    return held


class FileProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture()
        self.view, self.snapshot = self.fixture.view(), self.fixture.snapshot()

    def project(self, **kwargs):
        return files.collection(self.view, self.snapshot, **kwargs)

    def assert_counts(self, result):
        self.assertEqual({key: result[key] for key in ('packages', 'distinct_files', 'distinct_useful_files',
            'distinct_supporting_files', 'file_placements', 'useful_file_placements', 'supporting_file_placements')},
            {'packages': 4, 'distinct_files': 5, 'distinct_useful_files': 3, 'distinct_supporting_files': 2,
             'file_placements': 10, 'useful_file_placements': 5, 'supporting_file_placements': 5})

    def test_exact_counts_are_not_packages_placements_or_all_supporting_bytes(self):
        result = self.project()
        self.assert_counts(result)
        self.assertEqual(result['record_type'], 'public_good_file_collection/v1')
        self.assertEqual(result['matches'], 3)
        self.assertEqual(result['eligible_fingerprint'], self.snapshot.fingerprint)
        self.assertTrue(result['authentication_required'])
        self.assertFalse(result['subscription_required'])
        self.assertEqual(result['policy_version'], self.snapshot.version)
        # Known-wrong counts: packages, useful placements and all package files
        # must each fail the exact distinct-useful count check.
        for bad_count in (result['packages'], result['useful_file_placements'], result['distinct_files']):
            with self.subTest(bad_count=bad_count), self.assertRaises(AssertionError):
                self.assert_counts({**result, 'distinct_useful_files': bad_count})

    def test_shared_digest_retains_all_paths_parent_digests_and_licences(self):
        result = self.project()
        shared = next(row for row in result['items'] if row['file_sha256'] == sha(SHARED))
        self.assertEqual(len(shared['placements']), 4)
        self.assertEqual({(row['identity'], row['path'], row['licence'], row['is_useful']) for row in shared['placements']}, {
            ('package.alpha', 'guide.md', 'MIT', True), ('package.alpha', 'alternate.md', 'MIT', True),
            ('package.beta', 'guides/shared.txt', 'Apache-2.0', True), ('package.gamma', 'support/shared.bin', 'BSD-2-Clause', False)})
        for placement in shared['placements']:
            identity = placement['identity']
            self.assertEqual(placement['item_version'], self.fixture.versions[identity])
            self.assertEqual(placement['body_digest'], self.fixture.items[identity].digest)
            self.assertTrue(placement['requires_package_context'])
        self.assertIsNone(shared['media_type'])
        self.assertEqual(shared['media_types'], ['application/octet-stream', 'text/markdown', 'text/plain'])

    def test_facets_deduplicate_digests_and_do_not_sum_overlapping_associations(self):
        result = self.project()
        self.assertEqual(len(result['goals']), 17)
        self.assertEqual(next(row['files'] for row in result['goals'] if row['id'] == 4), 2)
        self.assertEqual(next(row['files'] for row in result['goals'] if row['id'] == 13), 0)
        self.assertEqual(result['related_files'], 2)
        self.assertEqual({row['id']: row['files'] for row in result['media_types']}, {
            'application/json': 1, 'text/markdown': 1, 'text/plain': 1, 'text/x-python': 1})
        self.assertEqual(result['initiatives'], [{'id': 'learning', 'files': 2}, {'id': 'public-data', 'files': 2}])
        self.assertGreater(sum(row['files'] for row in result['media_types']), result['distinct_useful_files'])
        self.assertEqual(self.project(query='solver')['goals'], result['goals'])
        self.assertEqual(self.project(goal='related')['initiatives'], result['initiatives'])

    def test_filters_match_one_useful_association_not_different_parents(self):
        self.assertEqual(self.project(goal='4', media_type='text/plain')['matches'], 0)
        self.assertEqual(self.project(goal='related', media_type='text/plain')['matches'], 1)
        self.assertEqual(self.project(initiative='learning', package='package.beta')['matches'], 0)
        self.assertEqual(self.project(media_type='application/octet-stream')['matches'], 0, 'support-only association qualified a file')
        self.assertEqual(self.project(package='package.gamma')['matches'], 0)
        result = self.project(package='package.beta', media_type='text/plain')
        self.assertEqual(result['matches'], 1)
        self.assertEqual(len(result['items'][0]['placements']), 4, 'filter removed licence/context associations')
        self.assertEqual(result['items'][0]['placements'][0]['identity'], 'package.beta')
        self.assertEqual(sum(row['matches_filters'] for row in result['items'][0]['placements']), 1)

    def test_query_matches_path_title_purpose_benefit_and_casefolded_words(self):
        for query, matches in (('SOLVER.PY', 1), ('Alpha arithmetic', 2), ('structured datasets', 2),
                               ('guides/shared.txt', 1), ('lesson support', 3), ('not-present', 0)):
            with self.subTest(query=query):
                self.assertEqual(self.project(query=query)['matches'], matches)
        self.assertEqual(self.project(query='arithmetic shared.txt')['matches'], 0, 'query crossed parents')
        self.assertEqual(self.project(query='   ')['matches'], 3)

    def test_empty_snapshot_has_zero_counts_and_all_seventeen_goal_gaps(self):
        result = files.collection(self.view, replace(self.snapshot, grants=()))
        self.assertEqual(result['items'], [])
        self.assertFalse(result['has_next'])
        for field in ('packages', 'distinct_useful_files', 'file_placements', 'matches'):
            self.assertEqual(result[field], 0)
        self.assertEqual(result['goals'], [{'id': number, 'files': 0} for number in range(1, 18)])

    def test_pagination_is_stable_bounded_and_keeps_global_counts(self):
        all_rows = self.project()['items']
        paged = [self.project(page=number, page_size=1) for number in range(1, 5)]
        self.assertEqual([row for answer in paged for row in answer['items']], all_rows)
        self.assertEqual([answer['has_next'] for answer in paged], [True, True, False, False])
        for result in paged:
            self.assert_counts(result)
        reversed_snapshot = replace(self.snapshot, grants=tuple(reversed(self.snapshot.grants)))
        self.assertEqual(files.collection(self.view, reversed_snapshot)['items'], all_rows)
        self.assertEqual(self.project(page=10000, page_size=50)['items'], [])

    def test_invalid_filters_are_typed_including_booleans_and_nonfinite_values(self):
        invalid = {'query': (None, 3, 'x' * 201, 'line\nbreak', '\x7f'), 'goal': (4, True, '0', '18', '04', []),
            'media_type': (None, True, 'text/*', 'Text/Plain', 'text/plain; charset=utf-8', 'x' * 300),
            'initiative': ([], True, 'MixedCase', 'bad/path', 'x' * 65),
            'package': (None, True, 'x' * 201, 'bad\npackage'), 'page': (0, -1, 10001, True, 1.5, float('nan'), '1'),
            'page_size': (0, 51, False, 1.2, '20')}
        for name, values in invalid.items():
            for value in values:
                with self.subTest(field=name, value=repr(value)), self.assertRaises(ServiceRuntimeError) as refused:
                    self.project(**{name: value})
                self.assertEqual(refused.exception.code, 'invalid_public_good_query')

    def test_invalid_inputs_and_duplicate_grants_refuse_without_padding_counts(self):
        for view, snapshot in ((None, self.snapshot), (self.view, {}), (replace(self.view, packages=None), self.snapshot),
                (self.view, replace(self.snapshot, grants=list(self.snapshot.grants))),
                (self.view, replace(self.snapshot, grants=(*self.snapshot.grants, self.snapshot.grants[0])))):
            with self.subTest(view=type(view).__name__), self.assertRaises(ServiceRuntimeError) as refused:
                files.collection(view, snapshot)
            self.assertEqual(refused.exception.code, 'public_good_file_projection_invalid')

    def test_inactive_mixed_version_and_withdrawn_view_facts_are_not_projected(self):
        changed = dict(self.view.item_versions, **{'package.alpha': 'f' * 64})
        result = files.collection(replace(self.view, item_versions=changed), self.snapshot)
        self.assertEqual(result['packages'], 3)
        self.assertEqual(result['matches'], 2)
        self.assertFalse(any(row['identity'] == 'package.alpha' for item in result['items'] for row in item['placements']))
        withdrawn = replace(self.view, withdrawn=frozenset({('package.alpha', self.fixture.items['package.alpha'].digest)}))
        self.assertEqual(files.collection(withdrawn, self.snapshot)['items'], result['items'])
        inactive = replace(self.snapshot, grants=(replace(self.snapshot.grants[0], active=False), *self.snapshot.grants[1:]))
        self.assertEqual(files.collection(self.view, inactive)['items'], result['items'])

    def test_mixed_package_manifest_and_missing_manifest_are_explicit(self):
        changed = dict(self.view.packages, **{'package.alpha': self.view.packages['package.beta']})
        result = files.collection(replace(self.view, packages=changed), self.snapshot)
        self.assertEqual(result['packages'], 3)
        without = dict(self.view.packages)
        del without['package.delta']
        result = files.collection(replace(self.view, packages=without), self.snapshot)
        self.assertEqual(result['packages_without_file_manifest'], 1)
        self.assertEqual(result['packages'], 4)

    def test_conflicting_sizes_for_one_digest_refuse_instead_of_picking_a_parent(self):
        held = MetadataFixture()
        held.add('size.good', [entry('guide.md', SHARED)], ('guide.md',))
        held.add('size.bad', [entry('guide.md', SHARED, delta=1)], ('guide.md',))
        with self.assertRaises(ServiceRuntimeError) as refused:
            files.collection(held.view(), held.snapshot())
        self.assertEqual(refused.exception.code, 'package_file_size_conflict')

    def test_public_whitelist_no_bodies_private_references_accounts_or_effects(self):
        before = ([asdict(grant) for grant in self.snapshot.grants], {key: value.to_dict() for key, value in self.view.packages.items()})
        with ExitStack() as stack:
            stack.enter_context(patch('builtins.open', forbidden))
            stack.enter_context(patch.object(socket.socket, 'connect', forbidden))
            stack.enter_context(patch.object(ServiceCatalogBinding, 'store', forbidden))
            result = self.project()
        rendered = json.dumps(result)
        for forbidden_value in (SHARED.decode(), '/private/source', '/private/rights', 'private-review:', 'private_metadata'):
            self.assertNotIn(forbidden_value, rendered)
        expected = set(files.FilePlacement.__annotations__)
        for item in result['items']:
            self.assertEqual(set(item), set(files.FileMetadata.__annotations__))
            for placement in item['placements']:
                self.assertEqual(set(placement), expected)
        self.assertEqual(set(result), set(files.FileCollection.__annotations__))
        self.assertEqual(before, ([asdict(grant) for grant in self.snapshot.grants], {key: value.to_dict() for key, value in self.view.packages.items()}))
        result['items'][0]['placements'][0]['sdg_goals'].append(17)
        self.assertNotEqual(self.project()['items'], result['items'], 'output mutation contaminated a subsequent projection')

    def test_package_api_remains_package_oriented(self):
        from loop_engine.core.service_runtime.public_good_page import collection as package_collection
        result = package_collection(self.view, self.snapshot)
        self.assertEqual(result['record_type'], 'public_good_collection/v1')
        self.assertEqual(result['packages'], 4)
        self.assertEqual(len(result['items']), 4)
        self.assertNotIn('placements', result['items'][0])

    def test_two_thousand_three_hundred_twenty_file_population_and_fifty_row_bound(self):
        held = MetadataFixture()
        entries = [entry('rules/rule_%04d.md' % number, ('synthetic-%04d' % number).encode()) for number in range(2320)]
        held.add('scale.fixture', entries, tuple(row[0] for row in entries))
        result = files.collection(held.view(), held.snapshot(), page_size=50)
        self.assertEqual(result['distinct_useful_files'], 2320)
        self.assertEqual(len(result['items']), 50)
        self.assertTrue(result['has_next'])
        last = files.collection(held.view(), held.snapshot(), page=47, page_size=50)
        self.assertEqual(len(last['items']), 20)
        self.assertFalse(last['has_next'])


class CurrentSnapshotTests(unittest.TestCase):
    def setUp(self):
        import test_public_good
        test_public_good.PublicGoodTests.setUp(self)
        data = self.bodies['public.fixture'].encode()
        package = CataloguePackage((CataloguePackageFile('fixture.txt', sha(data), len(data), 'text/plain', 'instruction_file'),), 'file')
        self.view = replace(self.view, packages={'public.fixture': package})
        self.grant = replace(self.grant, useful_paths=('fixture.txt',))
        prior = self.service.snapshot(self.view)
        self.service.configure(self.view, (self.grant,), expected_version=prior.version)

    def test_new_current_snapshot_removes_expired_files_without_projection_clock_or_cache(self):
        before = self.service.snapshot(self.view)
        self.assertEqual(files.collection(self.view, before)['matches'], 1)
        self.now[0] = self.grant.expires_at
        after = self.service.snapshot(self.view)
        result = files.collection(self.view, after)
        self.assertEqual(result['matches'], 0)
        self.assertNotEqual(before.fingerprint, after.fingerprint)
        self.assertFalse(self.reads)

    def test_new_current_snapshot_removes_policy_withdrawal_and_changed_version(self):
        prior = self.service.snapshot(self.view)
        self.service.configure(self.view, (), expected_version=prior.version)
        current = self.service.snapshot(self.view)
        self.assertEqual(files.collection(self.view, current)['matches'], 0)
        self.assertNotEqual(current.version, prior.version)
        changed = replace(self.view, item_versions={'public.fixture': 'e' * 64})
        self.assertEqual(files.collection(changed, prior)['matches'], 0)
        self.assertFalse(self.reads)


if __name__ == '__main__':
    unittest.main()
