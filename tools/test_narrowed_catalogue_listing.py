"""A legacy listing selects its checked tier before reading excluded disk records.

Real temporary publication, both view engines and real HTTP; no providers.
Record-parse counts, rather than wall-clock thresholds, detect the expensive
whole-library walk. The projection never substitutes for access checks.
"""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from loop_engine.core.service_runtime import catalogue_disk_index, catalogue_disk_view
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.catalogue_attributes import TIER_ATTRIBUTE
from loop_engine.core.service_runtime.catalogue_releases import withdraw
from loop_engine.core.service_runtime.catalogue_serving import store_view
from loop_engine.core.service_runtime.http_test_fixtures import running_http


class NarrowedListing(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory(prefix='narrowed-list-')
        self.addCleanup(self.folder.cleanup)
        self.case = Fixture(self.folder.name)
        rows = []
        for number in range(61):
            name = 'z_keeper' if number == 60 else f'a_community_{number:03d}'
            row = self.case.line(name, 'Original local fixture ' + name)
            if number < 60:
                row['approval']['tier'] = 'community'
            row['attributes']['tier'] = row['approval']['tier']
            rows.append(row)
        self.case.publish(rows, schema={'record_type':'catalogue_attribute_schema/v1','attributes':[TIER_ATTRIBUTE]})
        self.settings = replace(self.case.settings, record_type='service_catalogue_source/v2',
            search_engine='sqlite_disk_index', index_root=str(Path(self.folder.name) / 'index'))
        self.disk = self.view()

    def view(self):
        return store_view(self.case.config, self.settings, license_policy=self.case.license_policy,
                          family_policy=self.case.family_policy)

    def listing(self, view=None, **fields):
        return self.case.binding(view or self.disk).invoke(self.case.key.key, 'list', **fields)

    def test_exact_answer_matches_memory_without_parsing_the_excluded_population(self):
        expected = self.listing(self.case.view())
        self.assertTrue(self.disk.index.tier_filter_complete)
        self.assertEqual(self.listing(), expected)
        self.assertEqual([row['identity'] for row in expected['items']], ['z_keeper'])
        self.assertLessEqual(self.disk.disk.records_parsed, 2)

    def test_removed_optimization_preserves_answer_but_is_detected_by_record_reads(self):
        expected = self.listing()
        fresh = self.view()
        with mock.patch.object(catalogue_disk_view.DiskCatalogueView, 'listing_candidates', return_value=None):
            self.assertEqual(self.listing(fresh), expected)
        self.assertGreaterEqual(fresh.disk.records_parsed, 61)

    def test_included_community_and_explicit_search_candidates_are_not_narrowed(self):
        self.assertEqual(len(self.listing(community_items='included')['items']), 61)
        answer = self.case.binding(self.disk).invoke(self.case.key.key, 'list',
            community_items='included', candidates=('a_community_000',))
        self.assertEqual([row['identity'] for row in answer['items']], ['a_community_000'])

    def test_unknown_projection_uses_the_existing_complete_walk(self):
        with mock.patch.object(catalogue_disk_index.DiskIndex, 'tier_filter_complete',
                               new_callable=mock.PropertyMock, return_value=False):
            self.assertIsNone(self.disk.listing_candidates({}))
            self.assertEqual([row['identity'] for row in self.listing()['items']], ['z_keeper'])
        self.assertGreaterEqual(self.disk.disk.records_parsed, 61)

    def test_a_candidate_cannot_grant_access(self):
        self.case.runtime.set_grants('alpha', ())
        self.assertEqual(self.disk.listing_candidates({}), ('z_keeper',))
        self.assertEqual(self.listing()['items'], [])

    def test_withdrawn_verified_item_does_not_survive_the_projection(self):
        withdraw(self.case.context, identity='z_keeper', note_text='Synthetic withdrawal')
        fresh = self.view()
        self.assertEqual(fresh.listing_candidates({}), ())
        self.assertEqual(self.listing(fresh)['items'], [])

    def test_legacy_and_tiered_http_keep_the_same_result_and_authority(self):
        import httpx
        served = type('Served', (), {'runtime': self.case.runtime, 'provisioning': self.case.binding(self.disk)})()
        with running_http(served) as (base, _app), httpx.Client(base_url=base, trust_env=False) as client:
            headers = {'Authorization': 'Bearer ' + self.case.key.key}
            answer = client.post('/api/v1/provisioning', headers=headers,
                json={'record_type':'service_provisioning_request/v1','operation':'list'})
            self.assertEqual(answer.status_code, 200)
            self.assertEqual([row['identity'] for row in answer.json()['result']['items']], ['z_keeper'])
            self.assertLessEqual(self.disk.disk.records_parsed, 2)
            answer = client.post('/api/v1/provisioning', headers=headers,
                json={'record_type':'service_provisioning_request/v2','operation':'list', 'library_tiers':['verified']})
            self.assertEqual(answer.status_code, 200)
            self.assertEqual([row['identity'] for row in answer.json()['result']['items']], ['z_keeper'])


if __name__ == '__main__':
    unittest.main()
