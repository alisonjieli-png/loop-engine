"""Disk comparison controls, including exact resumption and large near groups."""
import hashlib
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from loop_engine.core.library_ingestion.duplicates import normalized, shingles
from tools.global_component_duplicate_disk import DiskComparison
from tools.global_component_duplicates import prefix_pairs


def subject(identity, text):
    return {'key': identity, 'text': text, 'identity': identity, 'corpus': 'fixture',
            'package_digest': hashlib.sha256(identity.encode()).hexdigest()}


class DiskComparisonChecks(unittest.TestCase):
    def test_disk_pairs_match_exact_memory_engine_and_resume(self):
        texts = {'a': ' '.join('word' + str(i) for i in range(30)),
                 'b': ' '.join('word' + str(i) for i in range(1, 31)),
                 'c': ' '.join('word' + str(i) for i in range(4, 34)),
                 'd': 'unrelated calendar validation and geographic boundary'}
        profiles = {hashlib.sha256(normalized(v).encode()).hexdigest(): shingles(v) for v in texts.values()}
        wanted = set(prefix_pairs(profiles, Fraction(3, 5)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analysis.db'
            disk = DiskComparison(path, {'source': 'fixture'})
            for name, text in texts.items():
                disk.add(subject(name, text))
            disk.freeze_collection({'source': 'fixture'})
            disk.build_profiles(Fraction(3, 5))
            self.assertFalse(disk.compare(Fraction(3, 5), stop_after=2))
            disk.close()
            resumed = DiskComparison(path, {'source': 'fixture'}, resume=True)
            self.assertTrue(resumed.compare(Fraction(3, 5)))
            found = {(min(a, b), max(a, b), i, u) for a, b, i, u in resumed.pair_rows()}
            self.assertEqual(found, wanted)
            self.assertTrue(resumed.compare(Fraction(3, 5)))
            self.assertEqual(found, {(min(a, b), max(a, b), i, u) for a, b, i, u in resumed.pair_rows()})
            resumed.close()

    def test_two_hundred_five_members_are_compared(self):
        with tempfile.TemporaryDirectory() as directory:
            disk = DiskComparison(Path(directory) / 'analysis.db', {})
            common = ' '.join('token' + str(i) for i in range(30))
            for i in range(205):
                disk.add(subject(str(i), common + ' unique' + str(i)))
            disk.freeze_collection({})
            disk.build_profiles(Fraction(9, 10))
            disk.compare(Fraction(9, 10))
            self.assertEqual(disk.connection.execute('SELECT count(*) FROM pairs').fetchone()[0], 205*204//2)
            disk.close()

    def test_resume_refuses_changed_binding_and_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analysis.db'
            disk = DiskComparison(path, {'version': 1})
            disk.add(subject('a', 'One useful complete sentence for comparison.'))
            disk.freeze_collection({})
            disk.build_profiles(Fraction(4, 5))
            with self.assertRaisesRegex(ValueError, 'analysis_threshold_changed'):
                disk.compare(Fraction(9, 10))
            disk.close()
            with self.assertRaisesRegex(ValueError, 'analysis_cache_binding_changed'):
                DiskComparison(path, {'version': 2}, resume=True)

    def test_incomplete_collection_is_not_called_a_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            disk = DiskComparison(Path(directory) / 'analysis.db', {})
            disk.add(subject('a', 'Some source text before collection was complete.'))
            with self.assertRaisesRegex(ValueError, 'incomplete_collection'):
                disk.build_profiles(Fraction(4, 5))
            disk.close()

    def test_exact_text_aliases_do_not_expand_pair_count(self):
        with tempfile.TemporaryDirectory() as directory:
            disk = DiskComparison(Path(directory) / 'analysis.db', {})
            disk.add(subject('a', 'A repeated body of source material.'))
            disk.add(subject('b', 'A repeated body of source material.'))
            self.assertEqual(disk.connection.execute('SELECT count(*) FROM groups').fetchone()[0], 1)
            self.assertEqual(disk.connection.execute('SELECT count(*) FROM subjects').fetchone()[0], 2)
            disk.close()


if __name__ == '__main__':
    unittest.main()
