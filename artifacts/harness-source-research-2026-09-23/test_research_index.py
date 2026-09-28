"""Offline source-integrity, isolation and candidate-only retrieval controls."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research_index import ResearchIndexError, build_index, query_index, validate_rows, public_source_url


def item(category, rank):
    return {'record_type': 'harness_source_research_item/v1', 'category': category,
            'research_id': f'{category}-fixture-{rank:04d}', 'name': f'{category} zebra fixture {rank}',
            'repository': None, 'source_url': f'https://example.org/{category}/{rank}', 'source_path': None,
            'source_snapshot_digest': hashlib.sha256(b'fixture snapshot').hexdigest(),
            'upstream_revision': None, 'upstream_blob_sha': None, 'license_reported': None,
            'license_verified': False, 'rank': rank, 'priority_score': 10, 'score_components': {'fixture': 10},
            'evidence_level': 'fixture_metadata', 'qualification_status': 'unreviewed',
            'compatibility_status': 'unverified', 'inspiration_methods': ['Inspect supplied metadata.'], 'notes': []}


class ResearchIndexControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='research-index-controls-')
        cls.base = Path(cls.tmp.name)
        cls.sources = {}
        for category in ('skill', 'plugin', 'contract', 'tool'):
            path = cls.base/f'{category}s-ranked.jsonl'
            path.write_text(''.join(json.dumps(item(category, rank), sort_keys=True)+'\n' for rank in range(1,1001)))
            cls.sources[category] = path
        digest = hashlib.sha256(b'fixture snapshot').hexdigest()
        cls.quarantine = cls.base/'quarantine'
        (cls.quarantine/digest[:2]).mkdir(parents=True)
        (cls.quarantine/digest[:2]/digest).write_bytes(b'fixture snapshot')
        cls.db = cls.base/'research-index.db'
        cls.manifest = cls.base/'manifest.json'
        cls.report = build_index(cls.sources, cls.db, cls.manifest, authorize=True,
                                 isolated_root=cls.base, quarantine_roots=(cls.quarantine,))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def rows(self):
        return [item('tool', rank) for rank in range(1,1001)]

    def test_all4000_exact_payloads_acknowledged_and_active_hidden(self):
        self.assertEqual(self.report['readback_exact_payloads'], 4000)
        self.assertEqual(self.report['active_store_rows'], 0)
        self.assertEqual(self.report['default_active_search_hits'], 0)
        self.assertEqual(self.report['default_active_search_excluded'], 4000)

    def test_explicit_candidate_search_and_category(self):
        result = query_index(self.sources, self.db, self.manifest, query='zebra', category='contract', limit=3)
        self.assertEqual(len(result['hits']), 3)
        self.assertTrue(all(x['category']=='contract' and x['lifecycle']=='candidate' and x['execution_available'] is False for x in result['hits']))

    def test_exact_lookup_and_missing(self):
        result = query_index(self.sources, self.db, self.manifest, lookup='skill-fixture-0042')
        self.assertEqual(result['hits'][0]['research_id'], 'skill-fixture-0042')
        self.assertEqual(result['hits'][0]['rank'], 42)
        self.assertIsNone(result['hits'][0]['query_score'])
        self.assertEqual(query_index(self.sources, self.db, self.manifest, lookup='not-present')['hits'], [])

    def test_no_index_write_without_explicit_authorization(self):
        target = self.base/'not-authorized.db'
        with self.assertRaisesRegex(ResearchIndexError, 'authorization_required'):
            build_index(self.sources, target, self.base/'other.json', authorize=False,
                        isolated_root=self.base, quarantine_roots=(self.quarantine,))
        self.assertFalse(target.exists())

    def test_existing_database_is_not_overwritten(self):
        before = self.db.read_bytes()
        with self.assertRaisesRegex(ResearchIndexError, 'existing_index_refused'):
            build_index(self.sources, self.db, self.manifest, authorize=True,
                        isolated_root=self.base, quarantine_roots=(self.quarantine,))
        self.assertEqual(before, self.db.read_bytes())

    def test_duplicate_id_refused(self):
        rows = self.rows(); rows[1]['research_id']=rows[0]['research_id']
        with self.assertRaisesRegex(ResearchIndexError, 'duplicate_research_id'):
            validate_rows(rows, 'tool')

    def test_rank_gap_refused(self):
        rows=self.rows(); rows[20]['rank']=9001
        with self.assertRaisesRegex(ResearchIndexError, 'rank_sequence_invalid'):
            validate_rows(rows, 'tool')

    def test_forged_qualification_refused(self):
        for field,value in [('qualification_status','approved'),('compatibility_status','qualified'),
                            ('license_verified',True),('execution_available',True),('approved',True),('lifecycle','active')]:
            rows=self.rows(); rows[0][field]=value
            with self.subTest(field=field), self.assertRaisesRegex(ResearchIndexError, 'candidate_status_required'):
                validate_rows(rows,'tool')

    def test_source_digest_shape_refused(self):
        rows=self.rows(); rows[0]['source_snapshot_digest']='not-a-digest'
        with self.assertRaisesRegex(ResearchIndexError, 'source_digest_invalid'):
            validate_rows(rows,'tool')

    def test_private_and_credential_source_urls_refused(self):
        for url in ['https://127.0.0.1/a','https://[::1]/a','https://localhost/a',
                    'https://example.org/a?api_key=fixture','https://user:pass@example.org/a',
                    'file:///tmp/source','https://2130706433/a']:
            with self.subTest(url=url), self.assertRaisesRegex(ResearchIndexError,'unsafe_source_url'):
                public_source_url(url)

    def test_percent_encoded_path_space_is_a_valid_public_url(self):
        url='https://api.apis.guru/v2/specs/example/version%20unknown/swagger.json'
        self.assertEqual(public_source_url(url),url)
        with self.assertRaisesRegex(ResearchIndexError,'unsafe_source_url'):
            public_source_url(url.replace('%20',' '))

    def test_api_license_object_is_preserved_as_unverified_metadata(self):
        rows=self.rows();rows[0]['license_reported']={'name':'MIT','url':'https://opensource.org/licenses/MIT'}
        self.assertEqual(validate_rows(rows,'tool')[0]['license_reported'],rows[0]['license_reported'])
        self.assertFalse(rows[0]['license_verified'])

    def test_source_file_drift_refuses_query(self):
        copies={}
        folder=self.base/'drift';folder.mkdir(exist_ok=True)
        for category,path in self.sources.items():
            copies[category]=folder/path.name;copies[category].write_bytes(path.read_bytes())
        copies['tool'].write_bytes(copies['tool'].read_bytes()+b' ')
        with self.assertRaisesRegex(ResearchIndexError, 'source_file_drift'):
            query_index(copies,self.db,self.manifest,lookup='tool-fixture-0001')

    def test_database_drift_refuses_query(self):
        target=self.base/'drift.db';target.write_bytes(self.db.read_bytes()+b'changed')
        with self.assertRaisesRegex(ResearchIndexError,'index_database_drift'):
            query_index(self.sources,target,self.manifest,lookup='tool-fixture-0001')

    def test_missing_source_snapshot_refuses_before_database_creation(self):
        target=self.base/'missing-source.db'
        with self.assertRaisesRegex(ResearchIndexError,'source_snapshot_missing'):
            build_index(self.sources,target,self.base/'missing-source.json',authorize=True,
                        isolated_root=self.base,quarantine_roots=(self.base/'empty',))
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
