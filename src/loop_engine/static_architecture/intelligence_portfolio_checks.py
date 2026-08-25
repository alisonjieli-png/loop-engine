"""Focused checks for :mod:`intelligence_portfolio`.

Uses the active Context catalog and one real-callable Code pack. No model or
network call is made. The public module owns the collected ``self_test``.
"""
from __future__ import annotations

import hashlib
import inspect
import os
import tempfile

from ..loop.loop_capsule import ExternalPayloadRef
from .code_intelligence_assets import CodeAssetSpec, execute_code_ref
from .intelligence_layers import build_intelligence_catalog
from .intelligence_portfolio import (
    BenchmarkCodePack,
    BenchmarkCodeRegistration,
    IntelligencePortfolioError,
    LensFamily,
    PortfolioMaterializationServices,
    PortfolioRequest,
    PortfolioSelectionServices,
    REQUIRED_LENS_FAMILIES,
    export_intelligence_portfolios,
    materialize_portfolio_for_loop,
    select_intelligence_portfolio,
)


def _normalize_scores(values):
    values = tuple(float(value) for value in values)
    total = sum(values)
    return tuple(value / total for value in values) if total else values


def run_checks() -> dict:
    """Real active-catalog checks plus one real callable Code pack."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": detail})

    with tempfile.TemporaryDirectory(prefix="intelligence_portfolio_") as root:
        catalog = build_intelligence_catalog(
            runs_dir=root, advice_path=os.path.join(root, "advice.jsonl"))
        active_count = len(catalog["context_intelligence"])
        review_catalog = build_intelligence_catalog(
            runs_dir=root, advice_path=os.path.join(root, "advice.jsonl"),
            include_candidates=True)
        packaged_candidate = next(
            record for record in review_catalog["context_intelligence"]
            if record.tier != "core"
            or str((record.body or {}).get("maturity", "")) == "candidate")
        catalog["context_intelligence"].append(packaged_candidate)

        request = PortfolioRequest(
            "compare a reusable machine-learning benchmark solution",
            "consumer.portfolio.1")
        portfolio = select_intelligence_portfolio(
            request, PortfolioSelectionServices(layer_records=catalog))
        selected_ids = {item.record_id for item in portfolio.items}
        layers = {row.layer: row for row in portfolio.layer_coverage}
        check("real_active_catalog_maps_all_required_lenses",
              active_count >= 396 and len(portfolio.items) == 7
              and len({item.family for item in portfolio.items}) == 7
              and len({item.ref.loop_ref for item in portfolio.items}) == 7,
              f"{active_count} active Context records; 7 unique lens refs")
        check("candidate_only_records_are_refused",
              packaged_candidate.record_id not in selected_ids
              and layers["context_intelligence"].excluded_candidate_records >= 1,
              f"packaged candidate {packaged_candidate.record_id} stayed out")
        check("empty_history_and_user_layers_remain_visible",
              layers["runtime_history_solution_intelligence"].state == "empty_visible"
              and layers["user_feedback_intelligence"].state == "empty_visible"
              and all(set(trace.empty_layers) == {
                  "runtime_history_solution_intelligence", "user_feedback_intelligence"}
                  for trace in portfolio.query_traces),
              "both empty layers appear in coverage and every query trace")
        check("selection_uses_loop_native_zero_model_retrieval",
              portfolio.selection_model_calls == 0
              and all(trace.query_loop_id and trace.model_calls == 0
                      for trace in portfolio.query_traces),
              "seven retrieval loops, zero model calls")

        refused = 0
        try:
            PortfolioRequest(
                "x", "consumer.duplicate",
                lens_families=(LensFamily.FIRST_PRINCIPLES,
                               LensFamily.FIRST_PRINCIPLES,
                               *REQUIRED_LENS_FAMILIES[1:]))
        except IntelligencePortfolioError:
            refused += 1
        try:
            PortfolioRequest("x", "consumer.deterministic", mode="deterministic")
        except IntelligencePortfolioError:
            refused += 1
        check("duplicate_families_and_deterministic_consuming_loops_are_refused",
              refused == 2,
              "model consuming Loop requests failed closed; deterministic Code stays eligible")

        source = inspect.getsource(_normalize_scores).encode()
        body_ref = ExternalPayloadRef(
            "python://loop_engine/intelligence_portfolio/normalize_scores",
            hashlib.sha256(source).hexdigest(), size_bytes=len(source),
            media_type="text/x-python")
        code_spec = CodeAssetSpec(
            asset_id="code.benchmark.normalize_scores",
            name="Benchmark score verification normalizer",
            description="Normalize benchmark evaluation scores for verification",
            asset_kind="function", source_kind="local_path",
            body_ref=body_ref, entrypoints=("normalize_scores",),
            input_contract="score_sequence", output_contract="score_sequence",
            load_strategy="import", template_id="pure_function",
            lifecycle="registered",
            admission_ref="admission:self-test:normalize-scores:v1")
        registration = BenchmarkCodeRegistration(
            code_spec, ("portfolio-self-test",),
            (LensFamily.VERIFICATION_EVALUATION,),
            (("normalize_scores", _normalize_scores),))
        code_pack = BenchmarkCodePack(
            "portfolio-self-test-pack", (registration,))
        code_request = PortfolioRequest(
            "evaluate normalized benchmark scores", "consumer.code.1",
            benchmark_id="portfolio-self-test")
        code_portfolio = select_intelligence_portfolio(
            code_request, PortfolioSelectionServices(
                layer_records=catalog, code_pack=code_pack))
        verify_item = next(item for item in code_portfolio.items
                           if item.family ==
                           LensFamily.VERIFICATION_EVALUATION)
        materialized = materialize_portfolio_for_loop(
            code_portfolio, PortfolioMaterializationServices(
                layer_records=catalog, code_pack=code_pack))
        executed = execute_code_ref(
            verify_item.ref, code_pack.resolve,
            entrypoint="normalize_scores", inputs=(2, 3))
        policy = materialized.consumption.context_policy()
        check("benchmark_code_pack_is_registered_real_and_callable",
              verify_item.record_id == code_spec.asset_id
              and verify_item.ref.payload_digest == body_ref.digest
              and executed["value"] == (0.4, 0.6)
              and executed["materialization"]["model_calls"] == 0
              and executed["execution"]["model_calls"] == 0,
              "admitted Code ref materialized and its real entrypoint ran")
        check("each_consuming_record_names_exact_consumed_refs",
              policy.selected_refs == materialized.consumption.consumed_refs
              and materialized.consumption.run_history_fields()["consumed_refs"]
              == materialized.consumption.consumed_refs
              and len(materialized.consumption.consumed_refs) == 7
              and materialized.consumption.materialization_model_calls == 0,
              "delegation and eventual RunHistory fields use the same 7 refs")
        context_values = [item.value for item in materialized.values
                          if item.ref.handshake.role == "context_intelligence"]
        check("selected_loop_refs_materialize_existing_context_bodies",
              len(materialized.values) == 7 and context_values
              and all(value not in (None, "") for value in context_values),
              "all seven refs materialized; existing Context bodies are non-empty")

        variants, variant_materializations = [], []
        for index in range(3):
            variant = select_intelligence_portfolio(
                PortfolioRequest(request.task, f"consumer.variant.{index}"),
                PortfolioSelectionServices(layer_records=catalog))
            variants.append(tuple(ref.loop_ref for ref in variant.refs))
            if index < 2:
                variant_materializations.append(
                    materialize_portfolio_for_loop(
                        variant, PortfolioMaterializationServices(
                            layer_records=catalog)))
        check("consuming_identity_varies_comparable_lens_choices",
              len(set(variants)) > 1,
              f"{len(set(variants))} complete portfolios across 3 consuming Loops")
        consumptions = [item.consumption for item in variant_materializations]
        exported = export_intelligence_portfolios(
            [item.portfolio for item in variant_materializations], consumptions)
        check("map_fold_export_preserves_consuming_ref_provenance",
              exported["consumption"]["consuming_loop_count"] == 2
              and len(exported["consumption"]["by_consuming_loop"]) == 2
              and exported["payload_bodies_exported"] is False,
              "two exact consuming Loop maps folded; retrieved bodies stayed out")
        current = materialized.consumption.to_dict()
        check("current_consuming_loop_identity_is_explicit",
              current["consuming_loop_id"] == "consumer.code.1",
              "the consumption record names its exact consuming Loop")

    passed = sum(test["passed"] for test in tests)
    return {"record_type": "intelligence_portfolio_self_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests), "model_calls": 0}
