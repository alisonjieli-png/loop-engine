"""Tests for Pillar 2 of the Single-Founder Unicorn Operating System.

Verifies the 7-layer ComponentEnvelope, 3 slot families, 8 swappable engines,
and known-wrong refusal controls in `tools/unicorn_autonomous_ops_sre_and_dataroom_engines.py`.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools"))

import unicorn_autonomous_ops_sre_and_dataroom_engines as uops  # noqa: E402
from loop_engine.core.engines.envelope import COVERAGE_LAYERS, root_frame  # noqa: E402


class SupportTriageEnvelopeTests(unittest.TestCase):
    def test_support_slot_resolves_92pct_and_joins_ref_ids(self) -> None:
        env = uops.build_support_triage_envelope()
        out = env.execute({
            "record_type": uops.SUPPORT_REQUEST_SCHEMA,
            "request_id": "test_sup_01",
            "tickets": uops.default_support_benchmark_tickets(),
        })
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["envelope_layers"], COVERAGE_LAYERS)
        res = out["result"]
        self.assertEqual(res["selected_engine"], uops.ENG_SUPPORT_DIAGNOSTIC)
        self.assertEqual(res["total_tickets"], 25)
        self.assertEqual(res["auto_resolved_count"], 23)
        self.assertEqual(res["founder_escalated_count"], 2)
        self.assertGreaterEqual(res["zero_interruption_resolution_rate"], 0.92)
        self.assertTrue(res["meets_92pct_slo"])
        matched = [r for r in res["resolutions"] if r["ref_id_matched"]]
        self.assertEqual(len(matched), 3)
        self.assertTrue(all(r["humanizer_clean"] for r in res["resolutions"]))
        self.assertTrue(all(r["privacy_notice_compliant"] for r in res["resolutions"]))

    def test_support_slot_falls_back_to_deterministic_runbook_when_model_capped(self) -> None:
        env = uops.build_support_triage_envelope()
        out = env.execute(
            {
                "record_type": uops.SUPPORT_REQUEST_SCHEMA,
                "request_id": "test_sup_fallback",
                "tickets": uops.default_support_benchmark_tickets()[:6],
            },
            simulate_deferrals=(uops.ENG_SUPPORT_DIAGNOSTIC, uops.ENG_SUPPORT_APPROVAL_GATE),
        )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["result"]["selected_engine"], uops.ENG_SUPPORT_RUNBOOK_FALLBACK)
        self.assertEqual(
            out["result"]["attempted_engines"],
            (
                uops.ENG_SUPPORT_DIAGNOSTIC,
                uops.ENG_SUPPORT_APPROVAL_GATE,
                uops.ENG_SUPPORT_RUNBOOK_FALLBACK,
            ),
        )

    def test_tracking_layer_replays_identical_request_without_redispatch(self) -> None:
        env = uops.build_support_triage_envelope()
        req = {
            "record_type": uops.SUPPORT_REQUEST_SCHEMA,
            "request_id": "test_sup_idempotent",
            "tickets": uops.default_support_benchmark_tickets()[:2],
        }
        first = env.execute(req)
        second = env.execute(req)
        self.assertFalse(first["replayed_from_tracking"])
        self.assertTrue(second["replayed_from_tracking"])
        self.assertFalse(second["trace"]["engine_dispatched"])
        self.assertEqual(first["result"]["selected_engine"], second["result"]["selected_engine"])


class SRESelfHealingEnvelopeTests(unittest.TestCase):
    def test_sre_monitors_22_surfaces_and_heals_slo_breaches(self) -> None:
        env = uops.build_sre_self_healing_envelope()
        parent = root_frame("unicorn_ops_orchestrator")
        out = env.execute(
            {
                "record_type": uops.SRE_REQUEST_SCHEMA,
                "request_id": "test_sre_01",
            },
            parent_frame=parent,
        )
        self.assertEqual(out["status"], "ok")
        res = out["result"]
        self.assertEqual(res["monitored_surface_count"], 22)
        self.assertTrue(res["meets_20_plus_domain_target"])
        self.assertEqual(res["achieved_availability_pct"], 99.99)
        self.assertEqual(res["healed_incident_count"], 2)
        self.assertEqual(len(res["tamper_evident_chain_head_sha256"]), 64)

        by_host = {row["surface"]: row for row in res["surface_statuses"]}
        self.assertTrue(by_host["demos.baltor.ai"]["breach_detected"])
        self.assertEqual(
            by_host["demos.baltor.ai"]["active_engine_after_check"],
            "edge_manifest_federation_engine",
        )
        self.assertTrue(by_host["agentstudios.si"]["breach_detected"])
        self.assertFalse(by_host["baltor.ai"]["breach_detected"])

    def test_sre_postmortem_ledger_engine_emits_full_admin_systems_chain(self) -> None:
        env = uops.build_sre_self_healing_envelope()
        out = env.execute(
            {
                "record_type": uops.SRE_REQUEST_SCHEMA,
                "request_id": "test_sre_ledger",
            },
            preferred_engine=uops.ENG_SRE_POSTMORTEM_LEDGER,
        )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["result"]["selected_engine"], uops.ENG_SRE_POSTMORTEM_LEDGER)
        self.assertEqual(len(out["result"]["admin_systems_ledger"]), 22)


class InvestorDataRoomEnvelopeTests(unittest.TestCase):
    def test_investor_dataroom_compiles_signed_observed_and_projected_packet(self) -> None:
        env = uops.build_investor_dataroom_envelope()
        out = env.execute({
            "record_type": uops.DATAROOM_REQUEST_SCHEMA,
            "request_id": "test_dataroom_01",
            "founder_weekly_hours": 40.0,
        })
        self.assertEqual(out["status"], "ok")
        res = out["result"]
        self.assertTrue(res["observed_and_projected_strictly_disjoint"])
        obs = res["observed_facts"]
        proj = res["projected_models"]
        self.assertEqual(obs["evidence_category"], "observed")
        self.assertEqual(obs["live_served_catalogue_components"], 1_560_856)
        self.assertEqual(obs["staged_catalogue_components"], 1_902_758)
        self.assertEqual(obs["monitored_brand_surfaces"], 22)
        self.assertEqual(len(obs["tier_unit_economics"]), 6)
        self.assertEqual(len(obs["benchmark_lifts"]), 6)
        self.assertEqual(proj["evidence_category"], "projected_assumption")
        self.assertEqual(proj["projected_revenue_per_founder_hour_usd"], 6000.0)
        self.assertEqual(len(res["packet_signature_sha256"]), 64)


class KnownWrongControlTests(unittest.TestCase):
    def test_all_four_required_known_wrong_controls_refuse_before_engine(self) -> None:
        probes = uops.run_known_wrong_probes()
        self.assertEqual(set(probes.keys()), {
            "unapproved_refund_or_deletion_blocked",
            "secret_key_or_pii_in_support_draft_blocked",
            "projection_labeled_as_observed_blocked",
            "unhealthy_canary_promotion_blocked",
        })
        for name, bundle in probes.items():
            self.assertEqual(bundle["status"], "refused", name)
            self.assertTrue(bundle["blocked_before_engine"], name)
            self.assertFalse(bundle["trace"]["engine_dispatched"], name)

        self.assertEqual(
            probes["unapproved_refund_or_deletion_blocked"]["refusal"]["code"],
            "founder_escalation_gate_required",
        )
        self.assertEqual(
            probes["secret_key_or_pii_in_support_draft_blocked"]["refusal"]["code"],
            "privacy_notice_secret_or_pii_leak_blocked",
        )
        self.assertEqual(
            probes["projection_labeled_as_observed_blocked"]["refusal"]["code"],
            "evidence_rule_projection_labeled_as_observed",
        )
        self.assertEqual(
            probes["unhealthy_canary_promotion_blocked"]["refusal"]["code"],
            "unhealthy_canary_promotion_blocked",
        )

    def test_resource_deletion_and_memory_ceiling_and_slop_draft_are_refused(self) -> None:
        support_env = uops.build_support_triage_envelope()
        del_out = support_env.execute({
            "record_type": uops.SUPPORT_REQUEST_SCHEMA,
            "request_id": "probe_delete",
            "tickets": ({"ticket_id": "tkt_del", "requested_effect": "delete_resource"},),
        })
        self.assertEqual(del_out["status"], "refused")
        self.assertEqual(del_out["refusal"]["code"], "founder_escalation_gate_required")

        slop_out = support_env.execute({
            "record_type": uops.SUPPORT_REQUEST_SCHEMA,
            "request_id": "probe_slop",
            "tickets": (
                {
                    "ticket_id": "tkt_slop",
                    "draft_override": "Let us delve into this seamless tapestry of debugging.",
                },
            ),
        })
        self.assertEqual(slop_out["status"], "refused")
        self.assertEqual(slop_out["refusal"]["code"], "humanizer_slop_in_support_draft")

        sre_env = uops.build_sre_self_healing_envelope()
        mem_out = sre_env.execute({
            "record_type": uops.SRE_REQUEST_SCHEMA,
            "request_id": "probe_mem",
            "mem_max_mib": 4096,
        })
        self.assertEqual(mem_out["status"], "refused")
        self.assertEqual(mem_out["refusal"]["code"], "sre_memory_ceiling_exceeded")

    def test_module_self_test_passes(self) -> None:
        report = uops.self_test()
        self.assertTrue(report["passed"], report)


if __name__ == "__main__":
    unittest.main()
