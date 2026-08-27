"""Frozen offline checks for Model-Routing Intelligence.

The fixture names contract scenarios and expected outcomes. The executable
cases live in :func:`loop_engine.core.model_routing_intelligence.self_test` so
they also run when the package is installed without the benchmark directory.
This runner binds those checks to a frozen source-tree population and records
the exact fixture digest.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from .intelligence_layers import LAYERS
from .model_gateway import ModelGateway, ProviderSpec
from .model_routes import ModelRoute
from .model_routing_records import (
    MODEL_ROUTING_PORTFOLIO,
    MODEL_ROUTING_PORTFOLIO_ID,
    ROLES,
    ModelCapabilityRecord,
    ModelOutcomeEvidence,
    ModelRouteAvailabilitySnapshot,
    ModelRoutingError,
    ModelRoutingLearningCandidate,
    ModelSelectionRequest,
    ModelSuitabilityRecord,
)
from .model_routing_selector import (
    ModelRouteBootstrapSelector,
    ModelRouteCatalog,
    ModelRoutingEvidence,
    ModelSelectorConfig,
)


def run_contract_checks() -> dict:
    """Run deterministic contract checks with adapters that refuse all calls."""
    from dataclasses import replace

    from .runtime_settings import (
        ModelSettings,
        ModelTier,
        ProviderSettings,
        RuntimeSettings,
    )

    results: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(passed), "detail": detail})

    class NoCallAdapter:
        DEFAULT_MODEL = "fixture-model"

        def __init__(self) -> None:
            self.calls = 0

        def chat_maxout(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("bootstrap selection must not call a provider")

        def verify(self, model=""):
            self.calls += 1
            raise AssertionError("bootstrap selection must not probe a provider")

        def live_models(self):
            self.calls += 1
            raise AssertionError("bootstrap selection must not list models")

        def output_capability_for(self, model):
            self.calls += 1
            raise AssertionError("bootstrap selection must not query an adapter")

    local_adapter = NoCallAdapter()
    cloud_adapter = NoCallAdapter()
    high_adapter = NoCallAdapter()
    providers = (
        ProviderSpec(
            "local_fixture", local_adapter, "fixture", "not_required", "local",
        ),
        ProviderSpec(
            "cloud_fixture", cloud_adapter, "fixture", "env:FIXTURE_KEY", "cloud",
        ),
        ProviderSpec(
            "high_fixture", high_adapter, "fixture", "env:FIXTURE_KEY", "cloud",
        ),
    )
    routes = (
        ModelRoute(
            "local.small.fixture", "local_fixture", "fixture-small-v1", "local",
            purposes=("decide_label", "query_rewrite"),
        ),
        ModelRoute(
            "cloud.medium.fixture", "cloud_fixture", "fixture-medium-v1", "cloud",
            purposes=("decide_label", "generation"),
        ),
        ModelRoute(
            "cloud.high.fixture", "high_fixture", "fixture-high-v1", "cloud",
            purposes=("generation",),
        ),
    )
    settings = RuntimeSettings(models=ModelSettings(
        default_thinking_power="small",
        providers=(
            ProviderSettings(
                "local_fixture", kind="custom", endpoint="http://127.0.0.1:1/v1",
                model="fixture-small-v1", locality="local",
            ),
            ProviderSettings(
                "cloud_fixture", kind="custom", endpoint="https://fixture.invalid/v1",
                model="fixture-medium-v1", credential_env="FIXTURE_KEY",
                locality="cloud",
            ),
            ProviderSettings(
                "high_fixture", kind="custom", endpoint="https://fixture.invalid/v1",
                model="fixture-high-v1", credential_env="FIXTURE_KEY",
                locality="cloud",
            ),
        ),
        tiers=(
            ModelTier("small", ("local.small.fixture",)),
            ModelTier("medium", ("cloud.medium.fixture",)),
            ModelTier("high", ("cloud.high.fixture",)),
            ModelTier("max", ()),
            ModelTier("specialized", ()),
        ),
    ))
    now = "2026-08-27T16:00:00Z"
    capabilities = (
        ModelCapabilityRecord(
            "cap.local.small.v1", "local_fixture", "local.small.fixture",
            "fixture-small-v1", "local", ("classify", "rewrite_query"),
            ("json_object", "text"), model_revision="r1",
            deployment_digest="sha256:local-v1", wire_format="openai",
            structured_output=True, context_limit=8192, maximum_output=2048,
            maximum_output_source="offline fixture contract",
            thinking_power="small", input_cost_per_million=0.0,
            output_cost_per_million=0.0, source_refs=("fixture:local",),
            verification_state="reviewed", valid_from="2026-08-01T00:00:00Z",
            valid_until="2026-09-01T00:00:00Z",
        ),
        ModelCapabilityRecord(
            "cap.cloud.medium.v1", "cloud_fixture", "cloud.medium.fixture",
            "fixture-medium-v1", "cloud", ("classify", "synthesize"),
            ("json_object", "text"), model_revision="r1",
            deployment_digest="sha256:cloud-medium-v1",
            structured_output=True, context_limit=32768, maximum_output=4096,
            maximum_output_source="offline fixture contract",
            thinking_power="medium", input_cost_per_million=0.2,
            output_cost_per_million=0.4, source_refs=("fixture:medium",),
            verification_state="reviewed", valid_from="2026-08-01T00:00:00Z",
            valid_until="2026-09-01T00:00:00Z",
        ),
        ModelCapabilityRecord(
            "cap.cloud.high.v1", "high_fixture", "cloud.high.fixture",
            "fixture-high-v1", "cloud", ("design_architecture",),
            ("text",), model_revision="r1",
            deployment_digest="sha256:cloud-high-v1", context_limit=131072,
            maximum_output=16384,
            maximum_output_source="offline fixture contract",
            thinking_power="high", input_cost_per_million=1.0,
            output_cost_per_million=2.0, source_refs=("fixture:high",),
            verification_state="reviewed", valid_from="2026-08-01T00:00:00Z",
            valid_until="2026-09-01T00:00:00Z",
        ),
    )
    availability = tuple(ModelRouteAvailabilitySnapshot(
        f"availability.{record.route_id}", record.route_id,
        record.provider_id, record.exact_model_id, now,
        "2026-08-28T16:00:00Z", True, True,
        record.locality != "local", True,
        deployment_digest=record.deployment_digest,
        context_limit=record.context_limit,
        maximum_output=record.maximum_output,
        available_concurrency=1,
        source_ref="offline fixture",
    ) for record in capabilities)
    suitability = (
        ModelSuitabilityRecord(
            "suit.local.short-classify.v1", "local.small.fixture",
            "short-record-classification/v1", ("classify",), ("json_object",),
            20, 20, 0.90, 0.95, 0.90,
            capability_record_digest=capabilities[0].content_digest,
            model_revision="r1", deployment_digest="sha256:local-v1",
            applicable_domains=("records",), risk_limit="low",
            context_range=(1, 4096), output_range=(1, 1024),
            benchmark_population_ref="fixture:short-classification",
            benchmark_version="1", environment_ref="fixture:cpu",
            evaluator_ref="fixture:exact-labels",
            latency_distribution=(0.2, 0.3), cost_distribution=(0.0,),
            stability=0.90, confidence=0.85,
            negative_transfer_evidence=("fixture:large-task-refusal",),
            review_ref="review:local-small-independent",
            valid_from="2026-08-01T00:00:00Z",
            valid_until="2026-09-01T00:00:00Z",
            provenance=("fixture:review/local-small",),
        ),
        ModelSuitabilityRecord(
            "suit.cloud.medium.classify.v1", "cloud.medium.fixture",
            "short-record-classification/v1", ("classify",), ("json_object",),
            20, 20, 0.85, 0.95, 0.90,
            capability_record_digest=capabilities[1].content_digest,
            model_revision="r1", deployment_digest="sha256:cloud-medium-v1",
            applicable_domains=("records",), risk_limit="medium",
            context_range=(1, 8192), output_range=(1, 2048),
            benchmark_population_ref="fixture:short-classification",
            benchmark_version="1", environment_ref="fixture:cloud",
            evaluator_ref="fixture:exact-labels",
            latency_distribution=(1.0, 1.2), cost_distribution=(0.001,),
            stability=0.90, confidence=0.80,
            review_ref="review:cloud-medium-independent",
            valid_from="2026-08-01T00:00:00Z",
            valid_until="2026-09-01T00:00:00Z",
            provenance=("fixture:review/cloud-medium",),
        ),
        ModelSuitabilityRecord(
            "suit.cloud.high.architecture.v1", "cloud.high.fixture",
            "repository-architecture/v1", ("design_architecture",), ("text",),
            10, 10, 0.80, 1.0, 0.90,
            capability_record_digest=capabilities[2].content_digest,
            model_revision="r1", deployment_digest="sha256:cloud-high-v1",
            applicable_domains=("software_architecture",), risk_limit="high",
            context_range=(1000, 100000), output_range=(100, 12000),
            benchmark_population_ref="fixture:architecture",
            benchmark_version="1", environment_ref="fixture:cloud",
            evaluator_ref="fixture:architecture-contract",
            latency_distribution=(5.0, 6.0), cost_distribution=(0.03,),
            stability=0.80, confidence=0.75,
            review_ref="review:cloud-high-independent",
            valid_from="2026-08-01T00:00:00Z",
            valid_until="2026-09-01T00:00:00Z",
            provenance=("fixture:review/cloud-high",),
        ),
    )
    gateway = ModelGateway(providers=providers, routes=routes)
    selector = ModelRouteBootstrapSelector.from_gateway(
        gateway,
        ModelRoutingEvidence(capabilities, suitability, availability),
        ModelSelectorConfig(settings),
    )

    base = ModelSelectionRequest(
        "selection.short.practitioner", "run.fixture", "loop.fixture",
        "practitioner", "practitioner.solver", "hybrid", "task:fixture",
        "short-record-classification/v1", "classify", "json_object",
        "schema:labels/v1", "decide_label", structured_output_required=True,
        input_context_estimate=500, expected_output_estimate=200,
        domain="records", consequence="low", cost_ceiling=0.01,
        verification_plan="deterministic schema and label check",
        allowed_localities=("local", "cloud"),
        preferred_localities=("local", "cloud"),
        preferred_thinking_power="small",
    )
    selected = selector.select(base, as_of=now)
    check(
        "portfolio_uses_exactly_the_four_existing_layers",
        MODEL_ROUTING_PORTFOLIO.persistent_layers == LAYERS,
        MODEL_ROUTING_PORTFOLIO.record_id,
    )
    check(
        "capability_suitability_and_availability_stay_distinct",
        len({
            type(capabilities[0]), type(suitability[0]), type(availability[0]),
        }) == 3
        and capabilities[0].content_digest != suitability[0].content_digest
        and availability[0].content_digest != capabilities[0].content_digest,
        "three typed records with independent digests",
    )
    check(
        "hard_filtering_precedes_explainable_ranking",
        selected.status == "selected"
        and selected.selected_route == "local.small.fixture"
        and all(candidate.score_contributions
                for candidate in selected.candidate_routes)
        and len(selected.hard_constraint_results) > 0,
        selected.selected_route,
    )
    no_model = selector.select(replace(
        base, request_id="selection.no-model", run_mode="deterministic",
        deterministic_sufficient=True,
        deterministic_evidence_refs=("fixture:schema-validator",),
    ), as_of=now)
    check(
        "deterministic_evidence_can_return_no_model_required",
        no_model.no_model_required and not no_model.selected_route,
        no_model.status,
    )
    local_only = selector.select(replace(
        base, request_id="selection.local-only",
        allowed_localities=("local",), preferred_providers=("cloud_fixture",),
    ), as_of=now)
    check(
        "local_only_policy_selects_zero_cloud_routes",
        local_only.selected_route == "local.small.fixture"
        and all(candidate.locality == "local"
                for candidate in local_only.candidate_routes)
        and all(item.provider_calls_made == 0
                for item in (selected, no_model, local_only)),
        str([candidate.route_id for candidate in local_only.candidate_routes]),
    )
    role_routes = []
    for role in ROLES:
        decision = selector.select(replace(
            base, request_id=f"selection.role.{role}", role=role,
            profile=f"{role}.fixture",
        ), as_of=now)
        role_routes.append(decision.selected_route)
    check(
        "role_does_not_determine_model_level",
        role_routes == ["local.small.fixture"] * len(ROLES),
        str(dict(zip(ROLES, role_routes))),
    )
    architecture_request = replace(
        base, request_id="selection.architecture",
        task_fingerprint="repository-architecture/v1",
        operator="design_architecture", response_topology="text",
        output_contract="architecture-contract/v1", model_purpose="generation",
        structured_output_required=False, input_context_estimate=10000,
        expected_output_estimate=3000, domain="software_architecture",
        consequence="high", cost_ceiling=1.0,
        verification_plan="independent architecture conformance",
        preferred_thinking_power="high",
    )
    architecture = selector.select(architecture_request, as_of=now)
    check(
        "small_task_suitability_does_not_transfer_to_large_architecture",
        architecture.selected_route == "cloud.high.fixture"
        and "local.small.fixture" in {
            item.route_id for item in architecture.rejected_routes},
        architecture.selected_route,
    )
    stale = replace(
        suitability[0], record_id="suit.local.stale.v1",
        content_digest="", deployment_digest="sha256:old-deployment",
    )
    stale_selector = ModelRouteBootstrapSelector(
        ModelRouteCatalog((routes[0],), (providers[0],)),
        ModelRoutingEvidence(
            (capabilities[0],), (stale,), (availability[0],)),
        ModelSelectorConfig(settings),
    )
    stale_decision = stale_selector.select(base, as_of=now)
    check(
        "deployment_change_invalidates_stale_suitability",
        stale_decision.status == "abstained"
        and any("suitability_scope" in item.reasons
                for item in stale_decision.rejected_routes),
        stale_decision.status,
    )
    stale_availability = replace(
        availability[0], snapshot_id="availability.local.stale",
        content_digest="", expires_at="2026-08-27T16:30:00Z",
    )
    stale_availability_selector = ModelRouteBootstrapSelector(
        ModelRouteCatalog((routes[0],), (providers[0],)),
        ModelRoutingEvidence(
            (capabilities[0],), (suitability[0],), (stale_availability,)),
        ModelSelectorConfig(settings),
    )
    stale_availability_decision = stale_availability_selector.select(
        base, as_of="2026-08-27T17:00:00Z")
    check(
        "stale_runtime_availability_is_rejected",
        stale_availability_decision.status == "abstained"
        and any("availability_freshness" in item.reasons
                for item in stale_availability_decision.rejected_routes),
        stale_availability_decision.status,
    )
    check(
        "bootstrap_selection_makes_no_adapter_calls",
        sum(adapter.calls for adapter in (
            local_adapter, cloud_adapter, high_adapter)) == 0,
        "all fixture adapters remained untouched",
    )
    gateway_config = selected.to_gateway_config()
    check(
        "decision_translates_to_existing_gateway_config",
        gateway_config.route_plan[0].route_name == selected.selected_route
        and gateway_config.purpose == base.model_purpose,
        gateway_config.route_plan[0].route_name,
    )
    from ..loop.recursive_loop import LoopLedger
    from .model_routing_intelligence import (
        ModelSelectionLoopContext,
        select_model_as_loop,
    )
    selection_ledger = LoopLedger()
    wrapped = select_model_as_loop(
        selector, base, ModelSelectionLoopContext(
            as_of=now, ledger=selection_ledger))
    selection_events = [event.get("event")
                        for event in selection_ledger.events]
    check(
        "model_selection_executes_as_a_governed_loop",
        wrapped["loop_id"]
        and wrapped["decision"].selected_route == "local.small.fixture"
        and "model.selection.requested" in selection_events
        and "model.route.selected" in selection_events
        and "model.selection.completed" in selection_events,
        wrapped["loop_id"],
    )
    unknown_usage = ModelOutcomeEvidence(
        "run.fixture", "loop.fixture", "model-loop.fixture",
        "local.small.fixture", "local_fixture", "fixture-small-v1",
        "sha256:local-v1", base.task_fingerprint, base.operator,
        base.response_topology, "sha256:input", "sha256:output", "passed",
        "passed", True, "", 1, None, None, 0.25, None,
        safe_summary="Typed output passed deterministic validation.",
        evidence_refs=("fixture:validator",),
    )
    check(
        "unknown_usage_remains_unknown_not_zero",
        not unknown_usage.accounting_complete
        and unknown_usage.input_tokens is None
        and unknown_usage.output_tokens is None,
    )
    self_review_blocked = False
    try:
        ModelRoutingLearningCandidate(
            "candidate.fixture", (unknown_usage.content_digest,),
            "short-record-classification/v1", ("local.small.fixture",), (),
            "prefer after twenty verified trials", ("fixture:validator",), (),
        20, "bounded holdout", ("operator:classify",), "loop.producer",
        lifecycle="approved", reviewer_loop_id="loop.producer",
        rollback="disable learned preference candidate.fixture",
        )
    except ModelRoutingError:
        self_review_blocked = True
    candidate = ModelRoutingLearningCandidate(
        "candidate.fixture", (unknown_usage.content_digest,),
        "short-record-classification/v1", ("local.small.fixture",), (),
        "prefer after twenty verified trials", ("fixture:validator",), (),
        20, "bounded holdout", ("operator:classify",), "loop.producer",
        lifecycle="approved", reviewer_loop_id="loop.reviewer",
        rollback="disable learned preference candidate.fixture",
    )
    check(
        "routing_learning_requires_independent_review",
        self_review_blocked and candidate.reviewer_loop_id != candidate.producer_loop_id,
    )

    passed = sum(1 for result in results if result["passed"])
    return {
        "record_type": "model_routing_intelligence_self_test/v1",
        "scope": "offline_contract_only",
        "portfolio_id": MODEL_ROUTING_PORTFOLIO_ID,
        "provider_integration_proven": False,
        "provider_calls": 0,
        "tests": results,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results),
    }


DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "benchmarks"
    / "model-routing"
    / "frozen-bootstrap-cases-v1.json"
)


class FrozenModelRoutingFixtureError(ValueError):
    """The frozen benchmark file is malformed or contradicts the suite."""


def run_frozen_benchmark(path: str | Path = DEFAULT_FIXTURE) -> dict:
    """Run the offline contract population and bind results to its digest."""
    fixture_path = Path(path)
    raw = fixture_path.read_bytes()
    try:
        fixture = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FrozenModelRoutingFixtureError(
            "model-routing fixture must be valid JSON") from exc
    required = {
        "benchmark_id", "benchmark_version", "frozen_at", "scope",
        "portfolio_id", "provider_calls_allowed", "cases",
    }
    missing = sorted(required - set(fixture))
    if missing:
        raise FrozenModelRoutingFixtureError(
            f"model-routing fixture misses {missing}")
    if fixture["scope"] != "offline_contract_only":
        raise FrozenModelRoutingFixtureError(
            "the frozen benchmark is an offline contract population")
    if fixture["portfolio_id"] != MODEL_ROUTING_PORTFOLIO_ID:
        raise FrozenModelRoutingFixtureError("portfolio identity changed")
    if fixture["provider_calls_allowed"] is not False:
        raise FrozenModelRoutingFixtureError(
            "the frozen benchmark must forbid provider calls")
    cases = fixture["cases"]
    if not isinstance(cases, list) or not cases:
        raise FrozenModelRoutingFixtureError(
            "the frozen benchmark needs at least one case")
    case_ids = [str(case.get("case_id", "")) for case in cases]
    assertions = [str(case.get("assertion", "")) for case in cases]
    if (any(not value for value in (*case_ids, *assertions))
            or len(case_ids) != len(set(case_ids))
            or len(assertions) != len(set(assertions))):
        raise FrozenModelRoutingFixtureError(
            "case ids and assertions must be unique and non-empty")

    suite = run_contract_checks()
    by_name = {item["test"]: item for item in suite["tests"]}
    results = []
    for case in cases:
        assertion = str(case["assertion"])
        observed = by_name.get(assertion)
        passed = observed is not None and bool(observed["passed"])
        expected_detail = str(case.get("expected_detail_contains", ""))
        if expected_detail:
            passed = bool(
                passed and expected_detail in str(observed.get("detail", "")))
        results.append({
            "case_id": str(case["case_id"]),
            "assertion": assertion,
            "expected": case.get("expected"),
            "passed": passed,
            "detail": "missing assertion" if observed is None
            else str(observed.get("detail", "")),
        })
    extra = sorted(set(by_name) - set(assertions))
    passed = sum(1 for item in results if item["passed"])
    return {
        "record_type": "model_routing_frozen_benchmark_result/v1",
        "benchmark_id": fixture["benchmark_id"],
        "benchmark_version": fixture["benchmark_version"],
        "frozen_at": fixture["frozen_at"],
        "scope": fixture["scope"],
        "fixture": fixture_path.as_posix(),
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "portfolio_id": fixture["portfolio_id"],
        "provider_integration_proven": False,
        "provider_calls": suite["provider_calls"],
        "cases": results,
        "extra_self_tests": extra,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results) and suite["all_passed"],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    path = Path(arguments[0]) if arguments else DEFAULT_FIXTURE
    result = run_frozen_benchmark(path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
