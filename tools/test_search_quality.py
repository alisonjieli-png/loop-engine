"""Checks for the catalogue search measurement.

Three things are checked, and each one has a known-wrong case beside it.

1. The measurement's baseline really is what the hosted service does. The
   baseline policy is compared, query by query, against a copy of the record
   construction in ``core.service_runtime.http.ServiceHttpApplication._search``,
   read from that source on 21 September 2026 and handed to the same retrieval
   engine. It compares the ordering, not a call to the running service. A
   baseline that flattered the new ranking would make every later number
   meaningless.
2. The judgements are a usable population: every expected item exists in the
   catalogue, every catalogue item is expected by at least one query, and the
   split is decided by the query text alone.
3. The declared default ranks at least as well as the baseline on the queries
   that were held back. The known-wrong case is the mode the default replaced:
   with the fold removed the same guard fails.
"""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
for folder in (REPOSITORY / "src", REPOSITORY / "examples/30_search_quality"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import measure  # noqa: E402
from loop_engine.core.contract_matching import CANONICAL, PURPOSE  # noqa: E402
from loop_engine.core.harness_intelligence_search import (  # noqa: E402
    DEFAULT_SEARCH_POLICY, SERVED_BEFORE_2026_09_21, CatalogueSearchField,
    CatalogueSearchPolicy, PreparedCatalogueSearch)

#: How deep the checks look. The reported measurement uses a larger depth; the
#: positions a customer reads are the same either way.
DEPTH = 10
#: The saved measurement these checks defend, so a number here is a number
#: somebody can open and read rather than one remembered in a comment.
REPORT = Path(__file__).resolve().parents[1] / "examples/30_search_quality/report-2026-09-21.json"


def _service_records(catalogue):
    """The records the deployed search builds, field for field.

    Read from ``ServiceHttpApplication._search`` on 21 September 2026: the
    purpose is the title and the description, and the identity, kind and source
    layer are the keywords. Nothing else of an item reaches the index.
    """
    from loop_engine.core.store_serve import StoreRecord
    return [StoreRecord(item.identity, "context", item.purpose,
                        body={"description": item.purpose,
                              "keywords": [item.identity, item.kind, item.source_layer]})
            for item in catalogue.items.values()]


class SearchQualityChecks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.catalogue = measure.load_catalogue(measure.DEFAULT_CATALOGUE)
        cls.judgements = measure.load_judgements(measure.DEFAULT_JUDGEMENTS, cls.catalogue)
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_the_measured_baseline_orders_items_as_the_deployed_search_does(self):
        from loop_engine.core.retrieval import Retriever
        deployed = Retriever(_service_records(self.catalogue))
        prepared = PreparedCatalogueSearch(self.catalogue, SERVED_BEFORE_2026_09_21)
        differences = []
        for judgement in self.judgements:
            theirs = [hit["record_id"] for hit in
                      deployed.search(judgement.query, mode="lexical", top_n=3)["hits"]]
            ours = [hit["identity"] for hit in prepared.search(judgement.query, top_n=3)["hits"]]
            if theirs != ours:
                differences.append((judgement.query, theirs, ours))
        self.assertEqual(differences, [], "the baseline policy is not the deployed search")

    def test_a_baseline_that_reads_other_fields_is_not_the_deployed_search(self):
        """The known-wrong case for the check above: change one weight and it fails."""
        from loop_engine.core.retrieval import Retriever
        deployed = Retriever(_service_records(self.catalogue))
        wrong = CatalogueSearchPolicy(
            CANONICAL, tuple(CatalogueSearchField(entry.name,
                                                  1 if entry.name == "purpose" else 0)
                             for entry in SERVED_BEFORE_2026_09_21.fields))
        prepared = PreparedCatalogueSearch(self.catalogue, wrong)
        differences = [judgement.query for judgement in self.judgements
                       if [hit["record_id"] for hit in deployed.search(
                           judgement.query, mode="lexical", top_n=3)["hits"]]
                       != [hit["identity"] for hit in prepared.search(judgement.query, top_n=3)["hits"]]]
        self.assertTrue(differences,
                        "a policy reading fewer fields still matched the deployed search, "
                        "so the equivalence check proves nothing")

    def test_every_judgement_names_an_item_and_every_item_has_a_judgement(self):
        held = set(self.catalogue.items)
        expected = {name for judgement in self.judgements for name in judgement.relevant}
        self.assertEqual(expected - held, set())
        self.assertEqual(held - expected, set(),
                         "a catalogue item no query asks for is never measured")
        self.assertTrue(any(not judgement.answerable for judgement in self.judgements),
                        "without a request this catalogue cannot answer, a confident "
                        "wrong answer is invisible")

    def test_the_split_follows_from_the_query_text_alone(self):
        record = json.loads(measure.DEFAULT_JUDGEMENTS.read_text(encoding="utf-8"))
        rule = record["split_rule"]
        self.assertEqual(rule["method"], "sha256_of_query_text")
        for judgement in self.judgements:
            digest = hashlib.sha256(judgement.query.encode("utf-8")).hexdigest()
            expected = "held_back" if int(digest[:8], 16) % 4 == 0 else "development"
            self.assertEqual(judgement.split, expected, judgement.query)

    def test_a_judgement_naming_an_item_outside_the_catalogue_is_refused(self):
        import tempfile
        record = json.loads(measure.DEFAULT_JUDGEMENTS.read_text(encoding="utf-8"))
        record["judgements"] = [{**record["judgements"][0], "relevant": ["not_in_this_catalogue"]}]
        with tempfile.TemporaryDirectory(prefix="loop-search-quality-") as folder:
            path = Path(folder) / "judgements.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(measure.MeasurementError):
                measure.load_judgements(path, self.catalogue)
            path.write_text(json.dumps({**record, "record_type": "something_else/v1"}),
                            encoding="utf-8")
            with self.assertRaises(measure.MeasurementError):
                measure.load_judgements(path, self.catalogue)

    def test_the_declared_default_beats_the_baseline_on_the_queries_held_back(self):
        held_back = [judgement for judgement in self.judgements
                     if judgement.split == "held_back"]
        self.assertTrue(held_back)
        baseline = measure.measure(self.catalogue, held_back, SERVED_BEFORE_2026_09_21, depth=DEPTH)
        current = measure.measure(self.catalogue, held_back, DEFAULT_SEARCH_POLICY, depth=DEPTH)
        for name in ("recall_at_1", "recall_at_3", "mean_reciprocal_rank"):
            self.assertGreaterEqual(
                current["overall"][name], baseline["overall"][name],
                f"the declared default is worse than the deployed search on {name}; "
                f"failing queries: {[row['query'] for row in current['failed_queries']]}")
        self.assertGreater(current["overall"]["mean_reciprocal_rank"],
                           baseline["overall"]["mean_reciprocal_rank"],
                           "the declared default gains nothing on the held-back queries")

    def test_removing_the_fold_makes_the_same_guard_fail(self):
        """The known-wrong case: the default without its match mode loses the gain."""
        held_back = [judgement for judgement in self.judgements
                     if judgement.split == "held_back"]
        baseline = measure.measure(self.catalogue, held_back, SERVED_BEFORE_2026_09_21, depth=DEPTH)
        without_fold = CatalogueSearchPolicy(CANONICAL, DEFAULT_SEARCH_POLICY.fields)
        self.assertEqual(DEFAULT_SEARCH_POLICY.match_mode, PURPOSE)
        mutant = measure.measure(self.catalogue, held_back, without_fold, depth=DEPTH)
        self.assertLessEqual(mutant["overall"]["mean_reciprocal_rank"],
                             baseline["overall"]["mean_reciprocal_rank"],
                             "taking the fold out did not lose the gain, so the guard above "
                             "is not measuring the fold")

    def test_the_saved_report_matches_what_the_measurement_produces_now(self):
        saved = {row["policy"]: row for row in self.report["comparison"]}
        self.assertIn("default", saved)
        self.assertEqual(self.report["catalogue_items"], len(self.catalogue.items))
        self.assertEqual(self.report["queries"], len(self.judgements))
        current = measure.measure(self.catalogue, self.judgements, DEFAULT_SEARCH_POLICY,
                                  depth=self.report["depth"])
        self.assertEqual(current["overall"]["recall_at_3"], saved["default"]["overall_recall_at_3"])
        self.assertEqual(current["overall"]["mean_reciprocal_rank"],
                         saved["default"]["overall_mean_reciprocal_rank"])


if __name__ == "__main__":
    unittest.main()
