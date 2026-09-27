"""Offline controls for cross-corpus comparison; no fixture approves material."""
import hashlib
import json
import random
import tempfile
import unittest
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
    CataloguePackageFile,
)
from tools.global_component_duplicate_sources import SourceReader
from tools.global_component_duplicates import prefix_pairs


def brute(documents, threshold):
    return {(left, right) for left, right in combinations(sorted(documents), 2)
            if documents[left] and documents[right]
            and len(documents[left] & documents[right]) * threshold.denominator >=
            len(documents[left] | documents[right]) * threshold.numerator}


class PrefixComparisonChecks(unittest.TestCase):
    def test_matches_brute_force_for_seeded_varied_sets(self):
        rng = random.Random(4081)
        for threshold in [Fraction(1, 2), Fraction(17, 20), Fraction(1, 1)]:
            documents = {str(i): frozenset(rng.sample(range(60), rng.randrange(1, 50))) for i in range(80)}
            actual = {(a, b) for a, b, _i, _u in prefix_pairs(documents, threshold)}
            self.assertEqual(actual, brute(documents, threshold))

    def test_more_than_two_hundred_near_copies_are_not_dropped(self):
        documents = {str(i): frozenset([*range(30), 1000 + i]) for i in range(205)}
        pairs = list(prefix_pairs(documents, Fraction(9, 10)))
        self.assertEqual(len(pairs), 205 * 204 // 2)

    def test_candidate_overlap_needs_actual_jaccard_confirmation(self):
        documents = {'a': frozenset(range(10)), 'b': frozenset([0, *range(20, 29)])}
        self.assertEqual(list(prefix_pairs(documents, Fraction(4, 5))), [])

    def test_threshold_boundary_uses_exact_arithmetic(self):
        documents = {'a': frozenset(range(9)), 'b': frozenset(range(10))}
        self.assertEqual(len(list(prefix_pairs(documents, Fraction(9, 10)))), 1)
        self.assertEqual(list(prefix_pairs(documents, Fraction(9001, 10000))), [])

    def test_empty_sets_are_not_evidence_of_duplicate_content(self):
        self.assertEqual(list(prefix_pairs({'a': frozenset(), 'b': frozenset()}, Fraction(1, 1))), [])

    def test_similarity_does_not_transitively_create_pairs(self):
        documents = {'a': frozenset(range(10)), 'b': frozenset(range(2, 12)), 'c': frozenset(range(4, 14))}
        pairs = {(a, b) for a, b, _i, _u in prefix_pairs(documents, Fraction(3, 5))}
        self.assertEqual(pairs, {('a', 'b'), ('b', 'c')})


class SourceViewChecks(unittest.TestCase):
    def test_api_view_compares_operation_not_shared_guidance(self):
        payloads = {'AGENTS.md': b'# Same shared guidance',
                    'contracts/operation.openapi.json': json.dumps({'paths': {'/widgets': {'get': {'responses': {'200': {'description': 'widgets'}}}}}}).encode(),
                    'references/endpoint.json': json.dumps({'method': 'GET', 'path_template': '/widgets'}).encode()}
        package = CataloguePackage(tuple(CataloguePackageFile(name, hashlib.sha256(raw).hexdigest(), len(raw),
            'text/markdown' if name.endswith('.md') else 'application/json',
            'instruction_file' if name == 'AGENTS.md' else 'other') for name, raw in payloads.items()))
        subject = SourceReader().subject('test', 'fixture', 'widgets', package,
            lambda entry: payloads[entry.path], component_type='api_operation_reference')
        self.assertEqual(subject['view'], 'documented_operation')
        self.assertNotIn('shared guidance', subject['text'])
        self.assertIn('/widgets', subject['text'])

    def test_file_reader_rejects_changed_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'AGENTS.md').write_bytes(b'changed')
            entry = CataloguePackageFile('AGENTS.md', hashlib.sha256(b'original').hexdigest(), 8,
                                         'text/markdown', 'instruction_file')
            with self.assertRaises(ValueError): SourceReader.filesystem_reader(root)(entry)

    def test_symlinked_metadata_is_not_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'original.json').write_text('{}')
            (root / 'link.json').symlink_to(root / 'original.json')
            with self.assertRaises(ValueError): SourceReader().metadata_bytes(root / 'link.json')

    def test_licence_alone_is_not_a_component_entrypoint(self):
        raw = b'An identical shared licence'
        package = CataloguePackage((CataloguePackageFile('LICENSE', hashlib.sha256(raw).hexdigest(),
            len(raw), 'text/plain', 'other'),))
        with self.assertRaisesRegex(ValueError, 'no_comparable_entry_view'):
            SourceReader().subject('test', 'fixture', 'licence', package, lambda entry: raw)

    def test_shell_hook_role_is_compared_as_text_without_execution(self):
        raw = b'#!/bin/sh\nprintf hello\n'
        package = CataloguePackage((CataloguePackageFile('check.sh', hashlib.sha256(raw).hexdigest(),
            len(raw), 'application/x-sh', 'hook'),))
        row = SourceReader().subject('test', 'fixture', 'hook', package, lambda entry: raw)
        self.assertIn('printf hello', row['text'])
        self.assertEqual(row['view'], 'entry_text')

    def test_frontmatter_only_record_retains_its_metadata_view(self):
        raw = b'---\nname: metadata-only\ndescription: A metadata record.\n---\n'
        package = CataloguePackage((CataloguePackageFile('SKILL.md', hashlib.sha256(raw).hexdigest(),
            len(raw), 'text/markdown', 'skill_definition'),))
        row = SourceReader().subject('test', 'fixture', 'metadata', package, lambda entry: raw)
        self.assertEqual(row['view'], 'frontmatter_only_text')
        self.assertIn('metadata-only', row['text'])


if __name__ == '__main__':
    unittest.main()
