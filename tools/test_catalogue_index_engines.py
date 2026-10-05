"""The judged queries of examples/30_search_quality, run against every engine of the catalogue search index slot.

The conformance kit in `core/service_runtime/catalogue_index_checks.py` proves the engines' behaviour and exact
pools on synthetic entries; this test adds the 354 judgements over the 123 published items of the starter
catalogue, which only the repository carries. Each engine indexes the items as the service indexes a packaged
catalogue (`catalogue_search.index_for_items`), ranks every judged request in lexical and hybrid mode through the
same fusion the service uses, and is scored by mean reciprocal rank and hits within the first ten.

1. The disk engine on a fresh build ranks every request exactly as the in-memory engine: equal metrics follow.
2. An overlay (a base without a tenth of the items and a delta holding them) keeps its metrics within a stated
   tolerance of a fresh build, because only the corpus statistics of the lexical stage move.
3. The known-wrong engine that scores vectors in float32 is caught by the exact comparison.
4. The engine (c) prototype on Lance, which is not exact, stays within the same tolerance of the baseline.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[1]
for folder in (REPOSITORY / "src", REPOSITORY / "examples/30_search_quality"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import measure  # noqa: E402
from loop_engine.core.service_runtime import catalogue_disk_index  # noqa: E402
from loop_engine.core.service_runtime.catalogue_disk_index import (DiskIndex, DiskSearchIndex,  # noqa: E402
                                                                   build_disk_index)
from loop_engine.core.service_runtime.catalogue_schema import EMPTY_SCHEMA  # noqa: E402
from loop_engine.core.service_runtime.catalogue_search import (IndexEntry, ReleaseSearchIndex, entry_text,  # noqa: E402
                                                               fuse)

TOP_N = 10
#: An overlay may move the mean reciprocal rank by at most this much against a fresh build of the same items.
OVERLAY_MRR_TOLERANCE = 0.05


def _ranked(index, query, mode):
    pool = TOP_N * index.policy.candidate_pool_multiplier
    pools, _exhausted = index.rank(query, mode=mode, pool=pool)
    allowed = {identity: {} for rows in pools.values() for identity, _score in rows}
    return [identity for identity, _score, _modes in fuse(pools, allowed, index.policy, TOP_N)]


def _metrics(index, judgements, mode):
    reciprocal, hits, answerable = 0.0, 0, 0
    for judgement in judgements:
        if not judgement.relevant:
            continue
        answerable += 1
        order = _ranked(index, judgement.query, mode)
        rank = next((position for position, identity in enumerate(order, 1) if identity in judgement.relevant), 0)
        reciprocal += 1.0 / rank if rank else 0.0
        hits += 1 if rank else 0
    return {"mrr": round(reciprocal / answerable, 4), "hit_at_10": round(hits / answerable, 4),
            "answerable": answerable}


class JudgedQueries(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        catalogue = measure.load_catalogue(measure.DEFAULT_CATALOGUE)
        cls.judgements = measure.load_judgements(measure.DEFAULT_JUDGEMENTS, catalogue)
        items = sorted(catalogue.items.values(), key=lambda item: item.identity)
        cls.entries = tuple(IndexEntry(item.identity, entry_text(item), {}) for item in items)
        cls.temp = tempfile.TemporaryDirectory(prefix="catalogue-index-judged-")
        root = Path(cls.temp.name)
        cls.memory = ReleaseSearchIndex(cls.entries, EMPTY_SCHEMA)
        cls.disk = DiskSearchIndex(DiskIndex(build_disk_index(root / "fresh", cls.entries)), EMPTY_SCHEMA)
        cut = len(cls.entries) - len(cls.entries) // 10
        base = DiskIndex(build_disk_index(root / "base", cls.entries[:cut]))
        delta = DiskIndex(build_disk_index(root / "delta", cls.entries[cut:]))
        cls.overlay = DiskSearchIndex(base, EMPTY_SCHEMA, delta=delta)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def _differing_pools(self, mode):
        """Requests whose candidate pools, identities and scores, differ between the two engines."""
        pool = TOP_N * self.memory.policy.candidate_pool_multiplier
        return [judgement.query for judgement in self.judgements
                if self.memory.rank(judgement.query, mode=mode, pool=pool)
                != self.disk.rank(judgement.query, mode=mode, pool=pool)]

    def test_the_disk_engine_ranks_every_judged_request_as_the_in_memory_engine(self):
        for mode in ("lexical", "hybrid"):
            self.assertEqual(self._differing_pools(mode), [], f"{mode}: the disk engine's pools differ")
            differing = [judgement.query for judgement in self.judgements
                         if _ranked(self.memory, judgement.query, mode) != _ranked(self.disk, judgement.query, mode)]
            self.assertEqual(differing, [], f"{mode}: the disk engine ranked these requests differently")
            self.assertEqual(_metrics(self.memory, self.judgements, mode), _metrics(self.disk, self.judgements, mode))

    def test_an_overlay_keeps_the_judged_metrics_within_the_tolerance(self):
        for mode in ("lexical", "hybrid"):
            fresh, overlay = _metrics(self.disk, self.judgements, mode), _metrics(self.overlay, self.judgements, mode)
            self.assertEqual(overlay["answerable"], fresh["answerable"])
            self.assertLessEqual(abs(overlay["mrr"] - fresh["mrr"]), OVERLAY_MRR_TOLERANCE, (mode, fresh, overlay))

    def test_the_lance_prototype_stays_within_the_tolerance_of_the_baseline(self):
        from loop_engine.core.service_runtime.catalogue_lance_index import (LanceSearchIndex, availability,
                                                                            build_lance_index)
        if not availability()["available"]:
            self.skipTest("lancedb is not installed; the prototype is optional")
        lance = LanceSearchIndex(build_lance_index(Path(self.temp.name) / "lance", self.entries), EMPTY_SCHEMA)
        for mode in ("lexical", "hybrid"):
            baseline, prototype = _metrics(self.memory, self.judgements, mode), _metrics(lance, self.judgements, mode)
            self.assertLessEqual(abs(prototype["mrr"] - baseline["mrr"]), OVERLAY_MRR_TOLERANCE,
                                 (mode, baseline, prototype))

    def test_a_float32_vector_stage_is_caught_by_the_exact_comparison(self):
        def float32_top(index, weights, pool, keep_mask, floor):
            numpy = index.numpy
            scores = numpy.zeros(index.size, dtype=numpy.float32)
            for dimension, weight in weights:
                scores += index.columns[dimension] * numpy.float32(weight)
            rows = [(float(scores[p]), int(p)) for p in numpy.flatnonzero(scores > floor)]
            return sorted(rows, key=lambda row: (-row[0], row[1]))[:pool + 1]
        with mock.patch.object(catalogue_disk_index.DiskIndex, "vector_top", float32_top):
            differing = self._differing_pools("hybrid")
        self.assertTrue(differing, "a float32 vector stage must not pass as exact")


if __name__ == "__main__":
    unittest.main()
