"""Unit and conformance tests for Pillar 3 Unicorn Enterprise B2B Governance & BYOK Federation engines."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
for _candidate in (_REPOSITORY_ROOT / "src", _REPOSITORY_ROOT / "tools"):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from loop_engine.core.engines.envelope import (  # noqa: E402
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
)
from unicorn_enterprise_b2b_governance_and_byok_engines import (  # noqa: E402
    BYOKAndPrivateVPCFederationRequest,
    BYOKAndPrivateVPCFederationSlot,
    CUSTOMER_INFERENCE_TARGETS,
    DEFAULT_ENTERPRISE_ALLOWED_SPDX,
    DownloadedComponentRecord,
    ENGINE_AIRGAPPED_LOCAL_FEDERATION,
    ENGINE_CROSS_SEAT_LEDGER,
    ENGINE_ORG_LICENSE_POLICY,
    ENGINE_SBOM_PROVENANCE,
    ENGINE_SOC2_CAI_COMPILER,
    ENGINE_ZERO_TRUST_BYOK_ROUTER,
    OrganizationGovernancePolicy,
    SeatMaterializationEvent,
    SYNCHRONIZED_RELEASE_DIGEST,
    TEAM_PLAN_MONTHLY_USD,
    TeamPolicyGovernanceRequest,
    TeamSeatPolicyGovernanceSlot,
    VERIFIED_ENTERPRISE_CONTROLS,
    ZeroTouchSecurityPackRequest,
    ZeroTouchSecurityQuestionnaireSlot,
    run_unicorn_enterprise_b2b_benchmark_suite,
)


class UnicornEnterpriseB2BGovernanceAndBYOKTests(unittest.TestCase):
    """Verify 7-layer ComponentEnvelope behavior, engine failover, and known-wrong controls across all 3 slots."""

    def setUp(self) -> None:
        self.soc2_slot = ZeroTouchSecurityQuestionnaireSlot()
        self.policy_slot = TeamSeatPolicyGovernanceSlot()
        self.byok_slot = BYOKAndPrivateVPCFederationSlot()
        self.sample_downloads = (
            DownloadedComponentRecord(
                component_id="audit_data_splits_for_errors_and_leakage",
                version="2.4.0",
                spdx_license="MIT",
                source_revision=SYNCHRONIZED_RELEASE_DIGEST,
                package_sha256="a" * 64,
                trust_tier="baltor_reviewed",
            ),
            DownloadedComponentRecord(
                component_id="ttl_lru_cache_with_monotonic_clock",
                version="1.9.1",
                spdx_license="Apache-2.0",
                source_revision=SYNCHRONIZED_RELEASE_DIGEST,
                package_sha256="b" * 64,
                trust_tier="enterprise_attested",
            ),
        )
        self.enterprise_policy = OrganizationGovernancePolicy(organization_id="org_acme_enterprise")
        self.compliant_events = (
            SeatMaterializationEvent(
                seat_id="seat_eng_01",
                department="platform_security",
                project_code="proj_zero_trust",
                component_id="audit_data_splits_for_errors_and_leakage",
                spdx_license="MIT",
                trust_tier="baltor_reviewed",
                category="data_assurance",
                units_consumed=1200,
                seat_downloads_today=4,
                seat_units_today=8400,
            ),
        )

    def test_slot1_soc2_and_sbom_evidence_pack_and_failover(self) -> None:
        req = ZeroTouchSecurityPackRequest(
            request_id="soc2-test-1",
            organization_id="org_acme_enterprise",
            billing_period="2026-10",
            plan_tier_name="Baltor Team & Enterprise",
            requested_control_ids=tuple(VERIFIED_ENTERPRISE_CONTROLS.keys()),
            downloaded_components=self.sample_downloads,
        )
        res = self.soc2_slot.handle(req)
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_SOC2_CAI_COMPILER)
        self.assertEqual(res.payload["controls_answered_count"], 8)
        self.assertEqual(res.payload["team_monthly_price_usd"], TEAM_PLAN_MONTHLY_USD)
        self.assertEqual(res.payload["cyclonedx_bom_version"], "CycloneDX-1.5")
        self.assertEqual(res.payload["spdx_spec_version"], "SPDX-2.3")
        self.assertEqual(res.payload["sbom_components_count"], 2)
        self.assertEqual(len(res.payload["evidence_pack_sha256"]), 64)

        failover_res = self.soc2_slot.handle(
            ZeroTouchSecurityPackRequest(
                request_id="soc2-test-failover",
                organization_id="org_acme_enterprise",
                billing_period="2026-10",
                plan_tier_name="Baltor Team & Enterprise",
                requested_control_ids=tuple(VERIFIED_ENTERPRISE_CONTROLS.keys()),
                downloaded_components=self.sample_downloads,
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(failover_res.succeeded)
        self.assertEqual(failover_res.selected_engine, ENGINE_SBOM_PROVENANCE)
        self.assertEqual(
            failover_res.attempted_engines,
            (ENGINE_SOC2_CAI_COMPILER, ENGINE_SBOM_PROVENANCE),
        )

    def test_slot2_org_policy_governance_and_chargeback_ledger(self) -> None:
        req = TeamPolicyGovernanceRequest(
            request_id="policy-test-1",
            caller_organization_id="org_acme_enterprise",
            target_organization_id="org_acme_enterprise",
            policy=self.enterprise_policy,
            events=self.compliant_events,
        )
        res = self.policy_slot.handle(req)
        self.assertTrue(res.succeeded)
        self.assertEqual(res.selected_engine, ENGINE_ORG_LICENSE_POLICY)
        self.assertEqual(frozenset(res.payload["allowed_spdx_licenses"]), DEFAULT_ENTERPRISE_ALLOWED_SPDX)
        self.assertFalse(res.payload["stores_raw_developer_source_code"])
        self.assertEqual(len(res.payload["ledger_root_sha256"]), 64)

        failover_res = self.policy_slot.handle(
            TeamPolicyGovernanceRequest(
                request_id="policy-test-failover",
                caller_organization_id="org_acme_enterprise",
                target_organization_id="org_acme_enterprise",
                policy=self.enterprise_policy,
                events=self.compliant_events,
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(failover_res.succeeded)
        self.assertEqual(failover_res.selected_engine, ENGINE_CROSS_SEAT_LEDGER)

    def test_slot3_byok_and_private_vpc_federation_across_all_targets(self) -> None:
        for target_id, spec in CUSTOMER_INFERENCE_TARGETS.items():
            private_cards = ("internal_repo_card_v1",) if spec.allows_private_repo_context else ()
            res = self.byok_slot.handle(
                BYOKAndPrivateVPCFederationRequest(
                    request_id=f"byok-{target_id}",
                    organization_id="org_acme_enterprise",
                    inference_target_id=target_id,
                    customer_auth_handle_id="keyring://acme/auth_handle_v1",
                    public_baltor_contract_ids=("audit_data_splits_for_errors_and_leakage",),
                    private_internal_contract_ids=private_cards,
                )
            )
            self.assertTrue(res.succeeded, msg=f"Failed for {target_id}")
            self.assertEqual(res.selected_engine, ENGINE_ZERO_TRUST_BYOK_ROUTER)
            self.assertTrue(res.payload["private_code_never_egresses"])
            self.assertTrue(res.payload["raw_byok_key_never_egresses_to_baltor"])

        failover_res = self.byok_slot.handle(
            BYOKAndPrivateVPCFederationRequest(
                request_id="byok-failover",
                organization_id="org_acme_enterprise",
                inference_target_id="local_loopback_ollama",
                customer_auth_handle_id="",
                public_baltor_contract_ids=("audit_data_splits_for_errors_and_leakage",),
                private_internal_contract_ids=("internal_repo_card_v1",),
                simulate_primary_deferral=True,
            )
        )
        self.assertTrue(failover_res.succeeded)
        self.assertEqual(failover_res.selected_engine, ENGINE_AIRGAPPED_LOCAL_FEDERATION)

    def test_known_wrong_a_copyleft_or_unreviewed_item_blocked(self) -> None:
        bad_event = SeatMaterializationEvent(
            seat_id="seat_eng_09",
            department="core_api",
            project_code="proj_gateway",
            component_id="viral_copyleft_helper",
            spdx_license="GPL-3.0-only",
            trust_tier="community_unreviewed",
            category="utilities",
            units_consumed=400,
            seat_downloads_today=1,
            seat_units_today=400,
        )
        res = self.policy_slot.handle(
            TeamPolicyGovernanceRequest(
                request_id="bad-copyleft",
                caller_organization_id="org_acme_enterprise",
                target_organization_id="org_acme_enterprise",
                policy=self.enterprise_policy,
                events=(bad_event,),
            )
        )
        self.assertFalse(res.succeeded)
        self.assertEqual(res.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(res.attempted_engines, ())
        assert res.refusal is not None
        self.assertEqual(res.refusal.code, "enterprise_policy_spdx_or_trust_violation")

    def test_known_wrong_b_private_source_or_raw_byok_egress_blocked(self) -> None:
        res_source_egress = self.byok_slot.handle(
            BYOKAndPrivateVPCFederationRequest(
                request_id="bad-private-egress",
                organization_id="org_acme_enterprise",
                inference_target_id="customer_byok_ollama_cloud",
                customer_auth_handle_id="keyring://acme/cloud_handle",
                public_baltor_contract_ids=("audit_data_splits_for_errors_and_leakage",),
                private_internal_contract_ids=("internal_secret_contract_v1",),
            )
        )
        self.assertFalse(res_source_egress.succeeded)
        self.assertEqual(res_source_egress.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(res_source_egress.attempted_engines, ())
        assert res_source_egress.refusal is not None
        self.assertEqual(res_source_egress.refusal.code, "private_code_or_raw_byok_egress_forbidden")

        res_key_egress = self.byok_slot.handle(
            BYOKAndPrivateVPCFederationRequest(
                request_id="bad-key-egress",
                organization_id="org_acme_enterprise",
                inference_target_id="local_loopback_ollama",
                customer_auth_handle_id="",
                public_baltor_contract_ids=("audit_data_splits_for_errors_and_leakage",),
                private_internal_contract_ids=(),
                attempt_raw_byok_key_egress_to_baltor=True,
            )
        )
        self.assertFalse(res_key_egress.succeeded)
        self.assertEqual(res_key_egress.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(res_key_egress.attempted_engines, ())

    def test_known_wrong_c_cross_organization_audit_read_blocked(self) -> None:
        res = self.policy_slot.handle(
            TeamPolicyGovernanceRequest(
                request_id="bad-cross-org",
                caller_organization_id="org_external_intruder",
                target_organization_id="org_acme_enterprise",
                policy=self.enterprise_policy,
                events=self.compliant_events,
            )
        )
        self.assertFalse(res.succeeded)
        self.assertEqual(res.trace.refused_by, LAYER_ACCOUNT)
        self.assertEqual(res.attempted_engines, ())
        assert res.refusal is not None
        self.assertEqual(res.refusal.code, "cross_organization_audit_read_forbidden")

    def test_known_wrong_d_unverified_compliance_claim_blocked(self) -> None:
        res = self.soc2_slot.handle(
            ZeroTouchSecurityPackRequest(
                request_id="bad-unverified-claim",
                organization_id="org_acme_enterprise",
                billing_period="2026-10",
                plan_tier_name="Baltor Team & Enterprise",
                requested_control_ids=tuple(VERIFIED_ENTERPRISE_CONTROLS.keys()),
                downloaded_components=self.sample_downloads,
                unverified_custom_claims=("ISO42001-Unverified-Marketing-Claim",),
            )
        )
        self.assertFalse(res.succeeded)
        self.assertEqual(res.trace.refused_by, LAYER_HANDSHAKE)
        self.assertEqual(res.attempted_engines, ())
        assert res.refusal is not None
        self.assertEqual(res.refusal.code, "unverified_compliance_claim_forbidden")

    def test_known_wrong_e_preflight_seat_budget_and_carrier_guards(self) -> None:
        over_budget_event = SeatMaterializationEvent(
            seat_id="seat_eng_77",
            department="platform_security",
            project_code="proj_zero_trust",
            component_id="audit_data_splits_for_errors_and_leakage",
            spdx_license="MIT",
            trust_tier="baltor_reviewed",
            category="data_assurance",
            units_consumed=20_000,
            seat_downloads_today=260,
            seat_units_today=490_000,
        )
        res = self.policy_slot.handle(
            TeamPolicyGovernanceRequest(
                request_id="bad-seat-budget",
                caller_organization_id="org_acme_enterprise",
                target_organization_id="org_acme_enterprise",
                policy=self.enterprise_policy,
                events=(over_budget_event,),
            )
        )
        self.assertFalse(res.succeeded)
        self.assertEqual(res.trace.refused_by, LAYER_PREFLIGHT)
        self.assertEqual(res.attempted_engines, ())
        assert res.refusal is not None
        self.assertEqual(res.refusal.code, "seat_daily_budget_exhausted")

        bad_carrier = self.soc2_slot.handle(
            ZeroTouchSecurityPackRequest(
                request_id="bad-carrier",
                organization_id="",
                billing_period="2026-10",
                plan_tier_name="Baltor Team & Enterprise",
                requested_control_ids=(),
                downloaded_components=(),
            )
        )
        self.assertFalse(bad_carrier.succeeded)
        self.assertEqual(bad_carrier.trace.refused_by, LAYER_CARRIER)

    def test_benchmark_suite_summary_all_checks_pass(self) -> None:
        summary = run_unicorn_enterprise_b2b_benchmark_suite()
        self.assertTrue(summary["all_checks_passed"])
        self.assertEqual(len(summary["byok_routes"]), 5)
        self.assertEqual(len(summary["known_wrong_probes"]), 5)


if __name__ == "__main__":
    unittest.main()
