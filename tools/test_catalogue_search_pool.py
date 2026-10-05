"""Catalogue search's candidate pool: verified-first ordering must survive catalogue growth.

A top-n answer is drawn from `candidate_pool_multiplier` times n lexical candidates, then verified items come
first. With the shared retrieval default of 2, a verified match ranked 21st or lower never reached a top ten; on
October 5, 2026 adding 8,953 items to the live catalogue pushed three judged verified answers out that way. The
catalogue now draws from 10 times n. These tests fix both edges: a verified match within the pool leads the
answer, and one far below it does not.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from loop_engine.core.retrieval_backends import RetrievalRankingPolicy  # noqa: E402
from loop_engine.core.service_runtime.catalogue_search import (  # noqa: E402
    CATALOGUE_RANKING_POLICY, LEXICAL_MODE, IndexEntry, ReleaseSearchIndex, fuse)

LENGTH = 400


def _entry(identity, matches, tier):
    """One entry of LENGTH tokens holding `matches` copies of the query term; equal lengths make BM25 follow them."""
    return IndexEntry(identity, " ".join(["alpha"] * matches + ["zeta"] * (LENGTH - matches)), {}, tier)


def _index(policy=None):
    # Community entries hold 300, 298, ... 2 matches, so their lexical ranks are fixed. The verified entry within
    # the pool sits between the 35th and 36th of them (rank 36); the one far below sits at rank 131.
    entries = [_entry(f"community-{rank:03d}", 300 - 2 * rank, "community") for rank in range(150)]
    entries += [_entry("verified-near", 300 - 2 * 35 + 1, "verified"),
                _entry("verified-far", 300 - 2 * 130 + 1, "verified")]
    return ReleaseSearchIndex(tuple(entries), policy=policy)


def _top(index, top_n=10):
    pools, _exhausted = index.rank("alpha", mode=LEXICAL_MODE, pool=top_n * index.policy.candidate_pool_multiplier)
    tiers = {identity: {"library_tier": identity.split("-")[0]} for rows in pools.values() for identity, _ in rows}
    return [identity for identity, _score, _modes in fuse(pools, tiers, index.policy, top_n)]


class CataloguePool(unittest.TestCase):
    def test_the_catalogue_index_uses_its_own_pool_and_leaves_the_shared_default(self):
        self.assertIs(_index().policy, CATALOGUE_RANKING_POLICY)
        self.assertEqual(CATALOGUE_RANKING_POLICY.candidate_pool_multiplier, 10)
        self.assertEqual(RetrievalRankingPolicy().candidate_pool_multiplier, 2)

    def test_a_verified_match_within_the_pool_leads_the_answer(self):
        top = _top(_index())
        self.assertEqual(top[0], "verified-near")
        self.assertEqual(top[1:], [f"community-{rank:03d}" for rank in range(9)])

    def test_a_verified_match_far_below_the_pool_is_not_promoted(self):
        self.assertNotIn("verified-far", _top(_index()))

    def test_known_wrong_the_shared_default_pool_drops_the_verified_match(self):
        top = _top(_index(RetrievalRankingPolicy()))
        self.assertNotIn("verified-near", top)
        self.assertEqual(top, [f"community-{rank:03d}" for rank in range(10)])


if __name__ == "__main__":
    unittest.main()
