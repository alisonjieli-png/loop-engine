"""Catalogue search's tier order: a strict order and a bounded verified boost, both selectable.

Until October 16, 2026 a lexical search put every verified match above the relevance floor before every community
match. On the live release a weakly matching verified item then led searches whose strong matches were community
items ("Keep a Changelog", "time aware LRU cache"), and agents concluded the library had nothing. The bounded boost
ranks lexical candidates by score and multiplies a verified candidate's score by one plus the boost first, so a
verified item leads only when its own score is close enough to the community item's. The tests fix the edges of
both orders, the refusals, and the parts that do not change: the floor, authorization and hybrid requests.

The replay tests read `examples/30_search_quality/ranking-replay-29a2bc33.json`: the candidates the service fused
for every measurable judged query on the October 9, 2026 release `29a2bc33...` (256,380 items), cut to the rows
that can reach a first-ten answer, with the answers both policies gave over the whole release. They are the fixed
query comparison as a check: it fails when a policy loses an expected hit the strict order finds or stops raising
the regression set's mean reciprocal rank, and each guard has a known-wrong control.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from loop_engine.core.service_runtime.catalogue_schema import EMPTY_SCHEMA  # noqa: E402
from loop_engine.core.service_runtime.catalogue_search import (  # noqa: E402
    BOUNDED_TIER_BOOST, CATALOGUE_RANKING_POLICY, DEFAULT_RANKING_POLICY, LEXICAL_MODE, MAXIMUM_VERIFIED_BOOST,
    RANKING_ENGINES, RANKING_POLICIES, STRICT_TIER_ORDER, CatalogueRankingEngine, CatalogueRankingPolicy,
    IndexEntry, LSHShingleBlocker, ReleaseSearchIndex, authorized_hits, expand_query_aliases,
    extract_core_query_terms, fuse, normalize_subtokens, rank_with_fallbacks, select_ranking_engine,
    split_subtokens, stem_token)
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

STRICT = RANKING_POLICIES["strict_tier_order"]
BOOST = RANKING_POLICIES["bounded_tier_boost"]
ALLOWED = {"strong": {"library_tier": "community"}, "relevant": {"library_tier": "verified"},
           "close": {"library_tier": "verified"}, "weak": {"library_tier": "verified"},
           "other": {"library_tier": "community"}}


def _order(pools, policy, allowed=ALLOWED, top_n=10):
    return [identity for identity, _score, _modes in fuse(pools, allowed, policy, top_n)]


class TierOrderPolicies(unittest.TestCase):

    def test_both_orders_are_named_and_the_default_is_one_of_them(self):
        self.assertEqual(set(RANKING_POLICIES), {"strict_tier_order", "bounded_tier_boost"})
        self.assertEqual((STRICT.lexical_tier_order, STRICT.lexical_verified_boost), (STRICT_TIER_ORDER, 0.0))
        self.assertEqual((BOOST.lexical_tier_order, BOOST.lexical_verified_boost), (BOUNDED_TIER_BOOST, 1.0))
        self.assertIs(CATALOGUE_RANKING_POLICY, RANKING_POLICIES[DEFAULT_RANKING_POLICY])
        # Every other bound is the same, so the two columns of a comparison differ by the tier order alone.
        shared = ("lexical_pool_multiplier", "lexical_score_floor_ratio", "lexical_tier_pool_multiplier",
                  "candidate_pool_multiplier", "reciprocal_rank_offset", "hash_similarity_floor")
        self.assertEqual([getattr(STRICT, name) for name in shared], [getattr(BOOST, name) for name in shared])
        self.assertIs(ReleaseSearchIndex((IndexEntry("one", "alpha", {}),), EMPTY_SCHEMA).policy,
                      CATALOGUE_RANKING_POLICY)

    def test_an_unknown_order_or_an_invalid_boost_is_refused(self):
        for fields in ({"lexical_tier_order": "verified_first"}, {"lexical_tier_order": None},
                       {"lexical_tier_order": BOUNDED_TIER_BOOST, "lexical_verified_boost": -0.5},
                       {"lexical_tier_order": BOUNDED_TIER_BOOST, "lexical_verified_boost": float("nan")},
                       {"lexical_tier_order": BOUNDED_TIER_BOOST, "lexical_verified_boost": float("inf")},
                       {"lexical_tier_order": BOUNDED_TIER_BOOST, "lexical_verified_boost": True},
                       {"lexical_tier_order": BOUNDED_TIER_BOOST, "lexical_verified_boost": "1"},
                       {"lexical_tier_order": BOUNDED_TIER_BOOST,
                        "lexical_verified_boost": MAXIMUM_VERIFIED_BOOST + 0.5},
                       {"lexical_verified_boost": 1.0}):
            with self.assertRaises(ValueError, msg=fields):
                CatalogueRankingPolicy(**fields)
        CatalogueRankingPolicy(lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=MAXIMUM_VERIFIED_BOOST)

    def test_the_strict_order_puts_every_verified_match_above_the_floor_first(self):
        pools = {LEXICAL_MODE: [("strong", 100.0), ("relevant", 40.0), ("close", 30.0), ("weak", 0.1)]}
        self.assertEqual(_order(pools, STRICT), ["relevant", "close", "strong"])

    def test_the_boost_lets_a_strong_community_match_lead_a_weak_verified_one(self):
        pools = {LEXICAL_MODE: [("strong", 100.0), ("relevant", 40.0), ("close", 30.0), ("weak", 0.1)]}
        self.assertEqual(_order(pools, BOOST), ["strong", "relevant", "close"])
        # A verified match within the bound still leads: 60 doubled outranks 100.
        pools = {LEXICAL_MODE: [("strong", 100.0), ("relevant", 60.0), ("other", 55.0)]}
        self.assertEqual(_order(pools, BOOST), ["relevant", "strong", "other"])

    def test_the_bound_is_inclusive_and_the_tier_breaks_an_exact_tie(self):
        pools = {LEXICAL_MODE: [("strong", 100.0), ("relevant", 50.0)]}
        self.assertEqual(_order(pools, BOOST), ["relevant", "strong"])
        tie_only = CatalogueRankingPolicy(lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=0.0)
        pools = {LEXICAL_MODE: [("strong", 50.0), ("relevant", 50.0), ("other", 49.0)]}
        self.assertEqual(_order(pools, tie_only), ["relevant", "strong", "other"])

    def test_the_floor_still_removes_incidental_matches_under_the_boost(self):
        pools = {LEXICAL_MODE: [("strong", 100.0), ("weak", 9.0), ("other", 20.0)]}
        # 9 doubled is 18, and the floor of 20 is read from raw scores, so the weak match stays out.
        self.assertEqual(_order(pools, BOOST), ["strong", "other"])
        no_floor = CatalogueRankingPolicy(lexical_score_floor_ratio=0, lexical_tier_order=BOUNDED_TIER_BOOST,
                                          lexical_verified_boost=1.0)
        self.assertEqual(_order(pools, no_floor), ["strong", "other", "weak"])

    def test_an_unauthorized_candidate_sets_no_floor_and_takes_no_place(self):
        pools = {LEXICAL_MODE: [("hidden", 10000.0), ("strong", 100.0), ("relevant", 40.0)]}
        for policy in (STRICT, BOOST):
            self.assertNotIn("hidden", _order(pools, policy))
        self.assertEqual(_order(pools, BOOST), ["strong", "relevant"])
        # Known wrong: treating the hidden identity as authorized lets its score set the floor.
        wrong = {**ALLOWED, "hidden": {"library_tier": "community"}}
        self.assertEqual(_order(pools, BOOST, allowed=wrong), ["hidden"])

    def test_a_hybrid_request_keeps_the_strict_order_under_either_policy(self):
        pools = {LEXICAL_MODE: [("strong", 100.0), ("relevant", 40.0)],
                 "vector": [("strong", 0.9), ("relevant", 0.3)]}
        self.assertEqual(fuse(pools, ALLOWED, BOOST, 10), fuse(pools, ALLOWED, STRICT, 10))
        self.assertEqual(_order(pools, BOOST), ["relevant", "strong"])

    def test_an_invalid_score_is_refused_under_the_boost_without_a_floor(self):
        no_floor = CatalogueRankingPolicy(lexical_score_floor_ratio=0, lexical_tier_order=BOUNDED_TIER_BOOST,
                                          lexical_verified_boost=1.0)
        for score in (-1.0, float("nan"), float("inf"), True, "1"):
            with self.assertRaises(ServiceRuntimeError) as caught:
                fuse({LEXICAL_MODE: [("strong", score)]}, ALLOWED, no_floor, 10)
            self.assertEqual(caught.exception.code, "search_index_unavailable")

    def test_the_served_search_path_orders_real_scores_by_the_policy(self):
        # Twenty community entries hold "keep" once and "changelog" five times; one verified entry holds "keep"
        # once; a thousand others hold neither. Every entry has the same length, so BM25 follows the counts.
        def entry(identity, words, tier):
            return IndexEntry(identity, " ".join(words + [f"pad{identity}x{n}" for n in range(12 - len(words))]),
                              {}, tier)
        entries = [entry(f"community-{n:03d}", ["keep"] + ["changelog"] * 5, "community") for n in range(20)]
        entries += [entry(f"other-{n:04d}", ["unrelated"], "community") for n in range(1000)]
        entries.append(entry("verified-keep", ["keep"], "verified"))
        tiers = {item.identity: item.tier for item in entries}

        def authorize(candidates):
            return {identity: {"library_tier": tiers[identity]} for identity in candidates}

        def first(policy):
            index = ReleaseSearchIndex(entries, EMPTY_SCHEMA, policy=policy)
            view = SimpleNamespace(schema=EMPTY_SCHEMA, search_index=lambda: index)
            hits, _rows = authorized_hits(view, {"query": "keep a changelog", "top_n": 5}, authorize)
            return [identity for identity, _score, _modes in hits], index
        strict, index = first(STRICT)
        pools, _exhausted = index.rank("keep a changelog", mode=LEXICAL_MODE, pool=50)
        index.close()
        scores = dict(pools[LEXICAL_MODE])
        ratio = scores["verified-keep"] / max(scores.values())
        # The case this test is about: above the floor, and below the bound of a boost of one.
        self.assertTrue(STRICT.lexical_score_floor_ratio <= ratio < 1 / (1 + BOOST.lexical_verified_boost), ratio)
        self.assertEqual(strict[0], "verified-keep")
        boosted, boost_index = first(BOOST)
        boost_index.close()
        self.assertEqual(len(boosted), 5)
        self.assertNotIn("verified-keep", boosted)
        self.assertTrue(all(identity.startswith("community-") for identity in boosted))


class SelectableEnginesAndFallbacks(unittest.TestCase):
    """Selectable ranking engines, sub-token/LSH query relaxation fallbacks, and Stage 4 safety fallback."""

    def test_selectable_engines_and_unknown_engine_refusal(self):
        expected = {"strict_tier_order", "tier_first", "bounded_tier_boost", "field_weighted_lexical",
                    "phrase_and_symbol_boost", "gated_relevance_fusion", "flexible_lsh_fallback"}
        self.assertEqual(set(RANKING_ENGINES), expected)
        self.assertIs(select_ranking_engine("tier_first"), STRICT)
        self.assertIs(select_ranking_engine(None), CATALOGUE_RANKING_POLICY)
        for name in expected:
            self.assertIsNotNone(select_ranking_engine(name))
        with self.assertRaises(ValueError):
            select_ranking_engine("nonexistent_engine")
        with self.assertRaises(ValueError):
            CatalogueRankingEngine(identity_match_boost=-1.0)
        with self.assertRaises(ValueError):
            CatalogueRankingEngine(enable_query_fallback="yes")

    def test_subtoken_splitting_stemming_and_alias_expansion(self):
        for raw in ("keep-a-changelog", "keep_a_changelog", "KeepAChangelog", "pkg/keep.changelog.v2"):
            stems = normalize_subtokens(raw)
            self.assertIn("keep", stems)
            self.assertIn("changelog", stems)
        self.assertEqual(split_subtokens("timeAwareLRUCache_v1"), ["time", "aware", "lru", "cache"])
        self.assertEqual(stem_token("configurations"), "configuration")
        core = extract_core_query_terms(
            "Can you please help me write a function that parses KeepAChangelog release notes")
        self.assertIn("keep", core)
        self.assertIn("changelog", core)
        self.assertNotIn("please", core)
        aliases = expand_query_aliases("ttl lru dedup k8s", limit=24)
        self.assertTrue({"expiry", "cache", "deduplicate", "kubernetes"}.issubset(set(aliases)))

    def test_lsh_shingle_blocker_and_multistage_relaxation_recover_non_exact_queries(self):
        entries = (
            IndexEntry("import_skill_changelog_template", "Keep a Changelog release notes generator", {}, "community"),
            IndexEntry("import_skill_ttl_lru_cache", "Time aware least recently used cache with expiry", {}, "community"),
            IndexEntry("import_skill_dockerfile_python", "Dockerfile container image for Python web service", {}, "verified"),
            IndexEntry("import_skill_unrelated_ item", " Unrelated alpha beta gamma delta", {}, "community"),
        )
        index = ReleaseSearchIndex(entries, EMPTY_SCHEMA, policy=RANKING_ENGINES["flexible_lsh_fallback"],
                                   build_vectors=False)
        self.addCleanup(index.close)
        tiers = {entry.identity: entry.tier for entry in entries}
        view = SimpleNamespace(schema=EMPTY_SCHEMA, search_index=lambda: index)

        def authorize(candidates):
            return {identity: {"library_tier": tiers[identity]} for identity in candidates}

        for query, expected_id in (
            ("KeepAChangelog", "import_skill_changelog_template"),
            ("timeAwareLruCache", "import_skill_ttl_lru_cache"),
            ("changelgo", "import_skill_changelog_template"),
            ("dockerfiel", "import_skill_dockerfile_python"),
            ("Can you please help me find a reusable component or tool that can parse KeepAChangelog release notes",
             "import_skill_changelog_template"),
        ):
            hits, _ = authorized_hits(view, {"query": query, "top_n": 5}, authorize)
            self.assertTrue(hits, query)
            self.assertEqual(hits[0][0], expected_id, query)
        # Known-wrong / unanswerable gibberish query returns no hits even under LSH fallback.
        unanswerable_hits, _ = authorized_hits(
            view, {"query": "xyzzyplugh cobol punchcard mainframe", "top_n": 5}, authorize)
        self.assertEqual(unanswerable_hits, [])

    def test_stage4_safety_fallback_recovers_from_unexpected_engine_errors_without_masking_refusals(self):
        pools = {LEXICAL_MODE: [("strong", 100.0), ("relevant", 40.0)]}

        class BrokenPolicy:
            lexical_score_floor_ratio = 0.2
            lexical_tier_order = BOUNDED_TIER_BOOST
            reciprocal_rank_offset = 60

            @property
            def lexical_verified_boost(self):
                raise RuntimeError("simulated ranking engine failure")

        # Unexpected runtime error in candidate engine automatically falls back to strict_tier_order.
        self.assertEqual(_order(pools, BrokenPolicy()), _order(pools, STRICT))
        # Known-wrong control: ServiceRuntimeError refusals are never swallowed by Stage 4 fallback.
        with self.assertRaises(ServiceRuntimeError):
            fuse({LEXICAL_MODE: [("strong", -5.0)]}, ALLOWED, BOOST, 10)


REPLAY = ROOT / "examples/30_search_quality/ranking-replay-29a2bc33.json"
JUDGEMENTS = {"bank": ROOT / "examples/30_search_quality/relevance-judgements.json",
              "regression": ROOT / "examples/30_search_quality/live-catalogue-regressions.json"}


def _replayed(entry, policy, top_n=10):
    pools = {LEXICAL_MODE: [(identity, score) for identity, score, _tier in entry["pool"]]}
    allowed = {identity: {"library_tier": tier} for identity, _score, tier in entry["pool"]}
    return [identity for identity, _score, _modes in fuse(pools, allowed, policy, top_n)]


def _lost(entries, baseline, candidate):
    """Every (query, identity) the baseline places in its first ten and the candidate does not."""
    lost = []
    for entry in entries:
        before, after = _replayed(entry, baseline), _replayed(entry, candidate)
        lost.extend((entry["query"], identity) for identity in entry["relevant"]
                    if identity in before and identity not in after)
    return lost


def _lost_queries(entries, baseline, candidate):
    """Every query that had a relevant hit in the baseline's first ten and has none in the candidate's."""
    lost = []
    for entry in entries:
        rel = set(entry["relevant"])
        before, after = _replayed(entry, baseline), _replayed(entry, candidate)
        if any(i in rel for i in before) and not any(i in rel for i in after):
            lost.append(entry["query"])
    return lost


def _mrr(entries, policy):
    total = 0.0
    for entry in entries:
        order = _replayed(entry, policy)
        rank = next((position for position, identity in enumerate(order, 1) if identity in entry["relevant"]), 0)
        total += 1.0 / rank if rank else 0.0
    return total / len(entries)


class LiveReleaseReplay(unittest.TestCase):
    """The fixed judged queries and the regression set, replayed from the candidates of the live release."""

    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(REPLAY.read_text(encoding="utf-8"))
        cls.bank = [entry for entry in cls.record["queries"] if entry["file"] == "bank"]
        cls.regression = [entry for entry in cls.record["queries"] if entry["file"] == "regression"]

    def test_the_fixture_names_the_release_and_the_judgements_it_was_measured_with(self):
        self.assertEqual(self.record["record_type"], "catalogue_ranking_replay/v1")
        self.assertTrue(self.record["catalogue_release"].startswith("29a2bc33"))
        self.assertEqual(self.record["items"], 256380)
        for name, path in JUDGEMENTS.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.record["judgements"][name], name)
        self.assertEqual({name: asdict(RANKING_POLICIES[name]) for name in RANKING_POLICIES},
                         {name: self.record["policies"][name] for name in RANKING_POLICIES})
        self.assertTrue(self.bank and self.regression)

    def test_every_entry_replays_the_answers_given_over_the_whole_release(self):
        for entry in self.record["queries"]:
            for name, answer in entry["answers"].items():
                self.assertEqual(_replayed(entry, RANKING_POLICIES[name]), answer, (name, entry["query"]))

    def test_a_cut_that_drops_the_best_candidate_no_longer_replays(self):
        """Known wrong for the check above: the floor follows the best score, so dropping it changes answers."""
        changed = [entry["query"] for entry in self.record["queries"] if entry["pool"]
                   and _replayed({**entry, "pool": entry["pool"][1:]}, STRICT) != entry["answers"]["strict_tier_order"]]
        self.assertTrue(changed)

    def test_the_boost_loses_no_expected_query_on_the_regression_set(self):
        self.assertEqual(_lost_queries(self.regression, STRICT, BOOST), [])
        self.assertEqual(len(_lost(self.bank, STRICT, BOOST)), 15)

    def test_known_wrong_ranking_by_score_alone_loses_expected_hits(self):
        tie_only = CatalogueRankingPolicy(candidate_pool_multiplier=10, lexical_tier_order=BOUNDED_TIER_BOOST,
                                          lexical_verified_boost=0.0)
        self.assertGreater(len(_lost(self.bank, STRICT, tie_only)), len(_lost(self.bank, STRICT, BOOST)) * 3)
        self.assertLess(_mrr(self.bank, tie_only), 0.35)

    def test_the_boost_raises_the_regression_reciprocal_rank_on_both_splits(self):
        for split in ("development", "held_back"):
            rows = [entry for entry in self.regression if entry["split"] == split]
            self.assertTrue(rows, split)
            self.assertGreater(_mrr(rows, BOOST), _mrr(rows, STRICT), split)

    def test_known_wrong_a_boost_too_large_to_differ_from_the_strict_order_raises_nothing(self):
        saturated = CatalogueRankingPolicy(candidate_pool_multiplier=10, lexical_tier_order=BOUNDED_TIER_BOOST,
                                           lexical_verified_boost=MAXIMUM_VERIFIED_BOOST)
        self.assertFalse(all(_mrr([entry for entry in self.regression if entry["split"] == split], saturated)
                             > _mrr([entry for entry in self.regression if entry["split"] == split], STRICT)
                             for split in ("development", "held_back")))

    def test_the_served_default_is_the_policy_the_recorded_comparison_chose(self):
        chosen = self.record["candidate"] if self.record["verdict"] == "ship_candidate" else self.record["baseline"]
        self.assertEqual(DEFAULT_RANKING_POLICY, chosen)


if __name__ == "__main__":
    unittest.main()
