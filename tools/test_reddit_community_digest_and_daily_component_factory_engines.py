"""Tests and known-wrong controls for `tools/reddit_community_digest_and_daily_component_factory_engines.py`."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(HERE.parent / "src") not in sys.path:
    sys.path.insert(0, str(HERE.parent / "src"))

import reddit_community_digest_and_daily_component_factory_engines as reddit_suite  # noqa: E402


class RedditCommunityDigestAndDailyComponentFactoryTests(unittest.TestCase):
    """Verify the 24-subreddit scanner, 5-file bundle synthesizer, 63,360 / 1,013,760 matrix, and 4 controls."""

    def test_slot1_reddit_scanner_collapses_aliases_into_24_canonical_domains(self) -> None:
        scanner = reddit_suite.RedditCommunitySignalScannerSlot()
        corpus = reddit_suite.build_daily_28_thread_corpus()
        self.assertEqual(len(corpus), 28)
        for eng in scanner.envelope.supported_engines:
            out = scanner.scan_and_cluster(corpus, engine_id=eng)
            self.assertTrue(out.succeeded)
            self.assertEqual(len(out.clusters), 24)
            self.assertEqual(out.duplicates_collapsed, 4)

    def test_slot2_synthesizer_emits_5_file_bundle_under_2kb_card_budget(self) -> None:
        scanner = reddit_suite.RedditCommunitySignalScannerSlot()
        synthesizer = reddit_suite.DailyRedditToHarnessComponentSynthesizerSlot()
        corpus = reddit_suite.build_daily_28_thread_corpus()
        scan_out = scanner.scan_and_cluster(corpus[:4])
        self.assertTrue(scan_out.succeeded)
        for idx, eng in enumerate(synthesizer.envelope.supported_engines):
            syn_out = synthesizer.synthesize_bundle(scan_out.clusters[idx], engine_id=eng)
            self.assertTrue(syn_out.succeeded)
            assert syn_out.bundle is not None
            self.assertLessEqual(syn_out.bundle.baltor_contract_card_bytes, 2048)
            self.assertIn("baltor_contract_card.json", syn_out.bundle.agents_md_snippet)
            self.assertTrue(bool(syn_out.bundle.rules_md_snippet.strip()))
            self.assertTrue(bool(syn_out.bundle.memory_md_snippet.strip()))
            self.assertIn("def verify_", syn_out.bundle.verifier_py_code)

    def test_slot3_combinatorial_matrix_63360_and_1013760_blueprints(self) -> None:
        matrix = reddit_suite.CombinatorialTopicAndTransformationMatrixSlot()
        self.assertEqual(matrix.base_cardinality, 63360)
        self.assertEqual(matrix.million_scale_cardinality, 1013760)
        for eng in matrix.envelope.supported_engines:
            out = matrix.expand_matrix(engine_id=eng)
            self.assertTrue(out.succeeded)
            self.assertEqual(out.base_matrix_cardinality, 63360)
            self.assertEqual(out.million_scale_cardinality, 1013760)
            self.assertEqual(len(out.sampled_blueprints), 7)

    def test_self_test_and_all_four_known_wrong_controls(self) -> None:
        res = reddit_suite.self_test()
        self.assertEqual(res["status"], "passed")
        bench = res["benchmark"]
        self.assertEqual(bench["canonical_subreddit_domains_count"], 24)
        self.assertEqual(bench["synthesized_5_file_bundles_count"], 24)
        self.assertEqual(bench["synthesized_component_files_count"], 120)


if __name__ == "__main__":
    unittest.main()
