"""The review export's kind mix (roadmap S-6.205): every kind a harness picks up, every export.

The balanced rule draws each kind in its declared share by a weighted round
robin, so any prefix of a selection keeps the mix and an exhausted kind spills
over to the others; the ranked rule is the earlier order and stays selectable.
The known-wrong case is the earlier order itself: with skills outranking every
other kind, the first fifty packages of a ranked selection hold no hook, no
plugin manifest and no script, which is how the library came to be skills and
instruction files first.
"""
from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

from candidate_review import native  # noqa: E402
from licensed_import import review_export  # noqa: E402
from licensed_import.discovery import SOURCE_PRIORITY  # noqa: E402
from licensed_import.records import HOOK, PLUGIN_MANIFEST, SKILL  # noqa: E402

KINDS = tuple(review_export.DEFAULT_KIND_SHARES)


def _payload(kind, number, *, code=False, stars=0, repository=None):
    files = [{"path": "README.md", "digest": "a" * 64, "size_bytes": 10, "media_type": "text/markdown", "role": "other"}]
    if code:
        files.append({"path": "scripts/run.py", "digest": "b" * 64, "size_bytes": 10, "media_type": "text/x-python",
                      "role": "skill_script"})
    return {"kind": kind, "name": f"{kind}-{number}", "record_id": f"{kind}.{number}",
            "package": {"body_form": "package", "files": files},
            "provenance": {"repository": repository or f"owner/{kind}-{number}", "path": f"{kind}/{number}"},
            "repository": {"stars": stars}}


def _stock(per_kind=100):
    payloads = []
    for key in KINDS:
        kind = SKILL if key == review_export.SKILL_WITH_SCRIPTS else key
        for number in range(per_kind):
            stars = 1000 if kind == SKILL else 0
            payloads.append(_payload(kind, number, code=key == review_export.SKILL_WITH_SCRIPTS, stars=stars))
    return payloads


class KindMixTest(unittest.TestCase):
    def test_the_balanced_mix_draws_every_kind_in_its_share_and_any_prefix_keeps_the_mix(self):
        chosen, skipped = review_export.select(_stock(), {}, SOURCE_PRIORITY, limit=200, per_repository=50,
                                               kind_mix=review_export.BALANCED)
        self.assertEqual(len(chosen), 200)
        counts = review_export.mix_counts(chosen)
        for key, share in review_export.DEFAULT_KIND_SHARES.items():
            self.assertAlmostEqual(counts.get(key, 0), share * 200, delta=2, msg=key)
        prefix = Counter(review_export.mix_key(payload) for payload in chosen[:50])
        for key, share in review_export.DEFAULT_KIND_SHARES.items():
            if share >= 0.05:
                self.assertGreaterEqual(prefix[key], 1, key)
            self.assertLessEqual(prefix[key], share * 50 + 2, key)
        self.assertEqual(skipped, Counter())

    def test_known_wrong_the_ranked_order_draws_no_hook_manifest_or_script_in_its_first_fifty(self):
        stock = _stock()
        ranked, _skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=200, per_repository=50,
                                                kind_mix=review_export.RANKED)
        first = Counter(review_export.mix_key(payload) for payload in ranked[:50])
        self.assertEqual(first[HOOK] + first[PLUGIN_MANIFEST] + first[review_export.SKILL_WITH_SCRIPTS], 0)
        self.assertEqual(first[SKILL], 50)
        balanced, _skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=200, per_repository=50,
                                                  kind_mix=review_export.BALANCED)
        mixed = Counter(review_export.mix_key(payload) for payload in balanced[:50])
        self.assertGreaterEqual(mixed[HOOK], 1)
        self.assertGreaterEqual(mixed[review_export.SKILL_WITH_SCRIPTS], 1)
        # The ranked rule still keeps code last and the higher source first, as before.
        self.assertTrue(all(not review_export.has_code(payload) for payload in ranked[:100]))
        self.assertEqual(review_export.select([], {}, SOURCE_PRIORITY, limit=5, per_repository=5), ([], Counter()))

    def test_an_exhausted_kind_spills_its_share_over_to_the_others(self):
        stock = [payload for payload in _stock() if payload["kind"] != HOOK] + [_payload(HOOK, n) for n in range(3)]
        chosen, _skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=100, per_repository=50,
                                                kind_mix=review_export.BALANCED)
        counts = review_export.mix_counts(chosen)
        self.assertEqual((len(chosen), counts[HOOK]), (100, 3))
        shares = {"hook": 1.0, **{key: 0.0 for key in KINDS if key != HOOK}}
        only_hooks, skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=100, per_repository=50,
                                                   kind_mix=review_export.BALANCED, kind_shares=shares)
        self.assertEqual([payload["kind"] for payload in only_hooks], [HOOK] * 3)
        self.assertEqual(skipped["kind_share_is_zero"], len(stock) - 3)

    def test_the_repository_ceiling_holds_inside_every_share(self):
        stock = [_payload(SKILL, n, repository="one/repository") for n in range(40)] + \
                [_payload(HOOK, n, repository="one/repository") for n in range(40)]
        chosen, skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=100, per_repository=5,
                                               kind_mix=review_export.BALANCED)
        self.assertEqual(len(chosen), 5)
        self.assertEqual(skipped["repository_ceiling_reached"], 75)

    def test_kind_shares_are_parsed_and_known_wrong_values_are_refused(self):
        shares = review_export.parse_kind_shares(["hook=0.2", "skill=0"])
        self.assertEqual((shares[HOOK], shares[SKILL]), (0.2, 0.0))
        self.assertEqual(review_export.parse_kind_shares(None), review_export.DEFAULT_KIND_SHARES)
        for wrong in (["dance=0.2"], ["hook=two"], ["hook=1.5"], ["hook"], [f"{key}=0" for key in KINDS]):
            with self.assertRaises(ValueError, msg=wrong):
                review_export.parse_kind_shares(wrong)
        with self.assertRaises(ValueError):
            review_export.select([], {}, SOURCE_PRIORITY, limit=1, per_repository=1, kind_mix="random")
        self.assertAlmostEqual(sum(review_export.DEFAULT_KIND_SHARES.values()), 1.0)

    def test_the_reviewable_text_media_are_the_panels_and_now_include_scripts(self):
        self.assertEqual(review_export.TEXT_MEDIA, native.TEXT_MEDIA)
        shell = _payload(SKILL, 1)
        shell["package"]["files"].append({"path": "run.sh", "digest": "c" * 64, "size_bytes": 3,
                                          "media_type": "application/x-sh", "role": "skill_script"})
        self.assertIsNone(review_export.reviewable(shell))
        image = _payload(SKILL, 2)
        image["package"]["files"].append({"path": "logo.png", "digest": "d" * 64, "size_bytes": 3,
                                          "media_type": "image/png", "role": "skill_asset"})
        self.assertEqual(review_export.reviewable(image), "a_file_is_not_reviewable_text")
        self.assertEqual(review_export.mix_key(shell), review_export.SKILL_WITH_SCRIPTS)
        self.assertEqual(review_export.mix_key(image), SKILL)


if __name__ == "__main__":
    unittest.main()
