"""The trust tier contract agrees with the ingestion records it admits and with the decision it carries out.

The community criteria read the evidence the library ingestion component
writes. These checks keep the two from drifting apart: the licence allowlist,
the licence decisions that permit serving a file, the process effect that
marks a runnable file, and the exact labels every surface shows. Each check
has a known-wrong control.
"""
from dataclasses import replace
import unittest

from loop_engine.core import provisioning_server
from loop_engine.core.library_ingestion import licences, provenance
from loop_engine.core.service_runtime import catalogue_packages, catalogue_tiers


class TrustTierContractTests(unittest.TestCase):
    def test_the_community_allowlist_is_the_ingestion_allowlist(self):
        self.assertEqual(tuple(catalogue_tiers.COMMUNITY_CRITERIA.licence_allowlist), tuple(licences.DEFAULT_ACCEPTED))

    def test_a_widened_allowlist_is_detected(self):
        widened = replace(catalogue_tiers.COMMUNITY_CRITERIA,
                          licence_allowlist=(*catalogue_tiers.COMMUNITY_CRITERIA.licence_allowlist, "GPL-3.0-only"))
        self.assertNotEqual(tuple(widened.licence_allowlist), tuple(licences.DEFAULT_ACCEPTED))
        self.assertNotEqual(widened.digest, catalogue_tiers.COMMUNITY_CRITERIA.digest)

    def test_only_decisions_that_permit_serving_a_file_are_accepted(self):
        decisions = set(catalogue_tiers.SERVABLE_LICENCE_DECISIONS)
        self.assertTrue(decisions <= set(provenance.LICENCE_DECISIONS))
        self.assertEqual(decisions, {provenance.VERBATIM, provenance.LINK_ONLY})
        self.assertNotIn(provenance.OUTLINE_ONLY, decisions)
        self.assertNotIn(provenance.REFUSED, decisions)

    def test_the_runnable_file_effect_is_the_release_rules_process_effect(self):
        # catalogue_packages.py is a pinned cited source of reviewed candidates, so it keeps its own
        # constant; this check holds the two values together instead.
        self.assertEqual(catalogue_packages.EXECUTABLE_EFFECT, provisioning_server.RUNNABLE_EFFECT)
        self.assertNotEqual("network", provisioning_server.RUNNABLE_EFFECT)

    def test_the_exact_labels_are_the_published_ones(self):
        self.assertEqual(catalogue_tiers.TIER_LABELS, {"baltor_verified": "Baltor verified", "community": "Community"})
        legend = catalogue_tiers.tier_legend()
        self.assertEqual([row["label"] for row in legend["tiers"]], ["Baltor verified", "Community"])
        self.assertEqual(legend["community_items"]["default"], "without_runnable_files")

    def test_a_changed_label_is_detected(self):
        changed = {**catalogue_tiers.TIER_LABELS, "community": "Community reviewed"}
        self.assertNotEqual(changed, {"baltor_verified": "Baltor verified", "community": "Community"})


if __name__ == "__main__":
    unittest.main()
