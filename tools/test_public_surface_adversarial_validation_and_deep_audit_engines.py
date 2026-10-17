"""Tests for the 600-question Public Surface Adversarial Validation & PDF Showcase Verifier."""

from __future__ import annotations

from tools.public_surface_adversarial_validation_and_deep_audit_engines import (
    PublicSurfaceAdversarialAuditEngine,
    ShowcaseAndPdfCompletenessVerifierEngine,
    ThinComponentAdapter,
    run_public_surface_adversarial_benchmark,
)


def test_600_question_public_surface_adversarial_audit_passes() -> None:
    engine = PublicSurfaceAdversarialAuditEngine()
    adapter = ThinComponentAdapter(engine, slot_id="public_surface_adversarial_validation_matrix_slot")
    contract = adapter.inspect_contract()
    assert contract["slot_id"] == "public_surface_adversarial_validation_matrix_slot"
    assert contract["adapter_loc"] <= 30

    res = adapter.execute({"mode": "full_audit"})
    assert res["status"] == "ok"
    assert res["total_surfaces_audited"] == 15
    assert res["questions_per_surface"] == 40
    assert res["total_adversarial_questions_evaluated"] == 600
    assert res["post_remediation_pass_count"] == 600
    assert res["post_remediation_pass_rate_pct"] == 100.0
    assert res["production_defects_discovered_and_fixed"] == 5
    assert adapter.verify_receipt(res) is True


def test_showcase_and_binary_pdf_completeness_verifier() -> None:
    engine = ShowcaseAndPdfCompletenessVerifierEngine()
    adapter = ThinComponentAdapter(engine, slot_id="surface_remediation_and_pdf_showcase_verifier_slot")
    res = adapter.execute({"mode": "verify_all"})
    assert res["status"] == "ok"
    assert res["fellowship_showcase"]["pdf_bytes"] == 213133
    assert res["fellowship_showcase"]["pdf_pages"] == 5
    assert res["personal_profile_showcase"]["pdf_bytes"] == 90263
    assert res["personal_profile_showcase"]["pdf_pages"] == 2
    assert res["editorial_design_compliance"]["ai_slop_score"] == 0.0
    assert adapter.verify_receipt(res) is True


def test_known_wrong_controls_refuse_defective_surface_states() -> None:
    audit_engine = PublicSurfaceAdversarialAuditEngine()

    r1 = audit_engine.run({"allow_registrar_parking_pass_through": True})
    assert r1["status"] == "refused"
    assert r1["error"]["code"] == "registrar_parking_trap_pass_through_refused"

    r2 = audit_engine.run({"allow_http_404_route_unavailable_on_cta": True})
    assert r2["status"] == "refused"
    assert r2["error"]["code"] == "cta_route_unavailable_404_refused"

    r3 = audit_engine.run({"conflate_personal_and_product_brands": True})
    assert r3["status"] == "refused"
    assert r3["error"]["code"] == "personal_and_product_brand_conflation_refused"

    r4 = audit_engine.run({"serve_html_disguised_as_binary_pdf": True})
    assert r4["status"] == "refused"
    assert r4["error"]["code"] == "invalid_binary_pdf_magic_bytes_refused"

    showcase_engine = ShowcaseAndPdfCompletenessVerifierEngine()
    r5 = showcase_engine.run({"emit_stale_model_names": True})
    assert r5["status"] == "refused"
    assert r5["error"]["code"] == "stale_model_name_in_showcase_refused"


def test_before_and_after_remediation_benchmark() -> None:
    bench = run_public_surface_adversarial_benchmark()
    assert bench["status"] == "ok"
    assert bench["baseline_unremediated_surface_state"]["passed_questions"] == 296
    assert bench["baseline_unremediated_surface_state"]["unresolved_production_defects"] == 5
    assert bench["baltor_adversarial_validated_and_remediated_surface_suite"]["passed_questions"] == 600
    assert bench["baltor_adversarial_validated_and_remediated_surface_suite"]["pass_rate_pct"] == 100.0
    assert bench["baltor_adversarial_validated_and_remediated_surface_suite"]["binary_pdf_endpoints_live"] == 2
    assert bench["audit_receipt_verified"] is True
    assert bench["showcase_receipt_verified"] is True
