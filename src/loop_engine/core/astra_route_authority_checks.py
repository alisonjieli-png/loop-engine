"""Offline checks for quarantined GPT-6 Astra candidate-route analysis.

The fixtures construct passive records and injected adapters only. They open no
socket, read no environment credential, make no model call, and cannot build a
``ModelRoute`` or ``ProviderSpec`` plan while execution qualification is false.
"""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal

from .astra_route_authority import (
    ASTRA_ADAPTER_CAPABILITIES,
    ASTRA_CONTEXT_WINDOW_TOKENS,
    ASTRA_CREDENTIAL_REF,
    ASTRA_EXECUTABLE_ROUTE_QUALIFIED,
    ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON,
    ASTRA_LONG_CONTEXT_THRESHOLD,
    ASTRA_MAXIMUM_INPUT_TOKENS,
    ASTRA_MAXIMUM_OUTPUT_TOKENS,
    ASTRA_PRICING,
    ASTRA_QUALIFIED_DATA_LOCALITY,
    ASTRA_QUALIFIED_SERVICE_TIER,
    ASTRA_REASONING_POLICY,
    ASTRA_REMAINING_INTEGRATION_REQUIREMENTS,
    ASTRA_ROUTE_NAME,
    PRICING_WORKFLOWS,
    RESPONSES_SERVICE_TIERS,
    AdapterCapabilityQualification,
    AstraModelDemand,
    AstraProviderReadiness,
    AstraRouteReadinessError,
    AstraRouteReadinessRequest,
    PaidModelRouteAuthority,
    ThinkingPowerReasoningPolicy,
    conservative_astra_cost_exposure,
)
from .astra_route_planning import (
    AstraRoutePlan,
    assess_astra_route_readiness,
    build_explicit_astra_route_plan,
)
from .model_routes import default_routes
from .model_routing_records import ModelRouteAvailabilitySnapshot
from .openai_responses_client import (
    DEFAULT_MODEL,
    PROVIDER_ID,
    OpenAIResponsesAdapter,
)


def run_checks() -> dict[str, object]:
    """Run passive-analysis and execution-quarantine checks."""
    tests: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    demand = AstraModelDemand(
        demand_id="demand:fixture",
        model_purpose="reasoning",
        thinking_power="medium",
        maximum_model_calls=1,
        maximum_input_tokens_per_call=1_000,
        maximum_output_tokens_per_call=ASTRA_MAXIMUM_OUTPUT_TOKENS,
        service_tier=ASTRA_QUALIFIED_SERVICE_TIER,
        required_data_locality=ASTRA_QUALIFIED_DATA_LOCALITY,
    )
    exposure = conservative_astra_cost_exposure(demand)
    authority = PaidModelRouteAuthority(
        authority_id="authority:fixture",
        issuer_ref="user:explicit-fixture",
        model_calls_authorized=True,
        paid_route_opt_in=True,
        credential_ref=ASTRA_CREDENTIAL_REF,
        authorized_route_name=ASTRA_ROUTE_NAME,
        authorized_provider_id=PROVIDER_ID,
        authorized_model_id=DEFAULT_MODEL,
        allowed_data_localities=(ASTRA_QUALIFIED_DATA_LOCALITY,),
        allowed_service_tiers=(ASTRA_QUALIFIED_SERVICE_TIER,),
        maximum_model_calls=1,
        maximum_input_tokens=1_000,
        maximum_output_tokens=ASTRA_MAXIMUM_OUTPUT_TOKENS,
        maximum_total_tokens=129_000,
        maximum_cost_usd=exposure.maximum_cost_usd,
    )
    available = ModelRouteAvailabilitySnapshot(
        snapshot_id="availability:fixture",
        route_ref=ASTRA_ROUTE_NAME,
        provider_id=PROVIDER_ID,
        exact_model_id=DEFAULT_MODEL,
        observed_at="2026-09-04T13:00:00Z",
        expires_at="2026-09-04T15:00:00Z",
        reachable=True,
        model_loaded=True,
        credential_required=True,
        credential_available=True,
        context_limit=ASTRA_CONTEXT_WINDOW_TOKENS,
        maximum_output=ASTRA_MAXIMUM_OUTPUT_TOKENS,
        source_ref="fixture:authorized-live-probe",
    )
    provider = AstraProviderReadiness(
        availability=available,
        data_locality=ASTRA_QUALIFIED_DATA_LOCALITY,
        data_locality_source_ref="fixture:deployment-policy",
    )

    def request_with(
        selected_demand: AstraModelDemand | None = None,
        selected_authority: PaidModelRouteAuthority | None = None,
        selected_provider: AstraProviderReadiness | None = None,
        *,
        request_id: str = "request:fixture",
        evaluated_at: str = "2026-09-04T14:00:00Z",
        reasoning_policy: ThinkingPowerReasoningPolicy = ASTRA_REASONING_POLICY,
        adapter_capabilities=ASTRA_ADAPTER_CAPABILITIES,
    ) -> AstraRouteReadinessRequest:
        return AstraRouteReadinessRequest(
            request_id=request_id,
            demand=selected_demand if selected_demand is not None else demand,
            authority=(
                selected_authority if selected_authority is not None else authority
            ),
            provider_readiness=(
                selected_provider if selected_provider is not None else provider
            ),
            evaluated_at=evaluated_at,
            reasoning_policy=reasoning_policy,
            adapter_capabilities=adapter_capabilities,
        )

    baseline_request = request_with()
    decision = assess_astra_route_readiness(baseline_request)
    decision_record = decision.to_dict()

    check(
        "executable_astra_route_is_unconditionally_unqualified",
        ASTRA_EXECUTABLE_ROUTE_QUALIFIED is False
        and decision.state == "refused"
        and not decision.ready
        and decision.refusal_reasons == (ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON,),
    )
    check(
        "quarantine_record_names_every_remaining_runtime_integration",
        decision_record["executable_route_qualified"] is False
        and decision_record["execution_authorized"] is False
        and tuple(decision_record["remaining_integration_requirements"])
        == ASTRA_REMAINING_INTEGRATION_REQUIREMENTS
        and decision.provider_calls_made == 0
        and decision.credential_reads == 0,
    )
    check(
        "documented_context_output_and_derived_input_allowance_are_distinct",
        ASTRA_CONTEXT_WINDOW_TOKENS == 1_050_000
        and ASTRA_MAXIMUM_OUTPUT_TOKENS == 128_000
        and ASTRA_MAXIMUM_INPUT_TOKENS
        == ASTRA_CONTEXT_WINDOW_TOKENS - ASTRA_MAXIMUM_OUTPUT_TOKENS
        and ASTRA_LONG_CONTEXT_THRESHOLD == 272_000,
        "922,000 is derived, not a separately documented input limit",
    )
    check(
        "official_nominal_price_table_is_preserved_for_candidate_analysis",
        ASTRA_PRICING.input_per_million_usd == Decimal(10)
        and ASTRA_PRICING.cached_input_per_million_usd == Decimal(1)
        and ASTRA_PRICING.cache_write_per_million_usd == Decimal("12.5")
        and ASTRA_PRICING.output_per_million_usd == Decimal(50)
        and dict(ASTRA_PRICING.service_tier_multipliers)
        == {
            "standard": Decimal(1),
            "batch": Decimal("0.5"),
            "flex": Decimal("0.5"),
            "fast": Decimal(2),
        }
        and set(PRICING_WORKFLOWS) == {"standard", "batch", "flex", "fast"},
    )
    check(
        "batch_is_pricing_data_not_a_responses_service_tier",
        "batch" not in RESPONSES_SERVICE_TIERS
        and "batch" not in authority.allowed_service_tiers,
    )
    batch_demand_refused = False
    try:
        replace(demand, service_tier="batch")
    except AstraRouteReadinessError:
        batch_demand_refused = True
    check("batch_cannot_enter_a_responses_route_demand", batch_demand_refused)
    check(
        "short_standard_exposure_remains_available_without_cache_discount",
        exposure.input_rate_per_million_usd == Decimal("12.5")
        and exposure.output_rate_per_million_usd == Decimal(50)
        and exposure.maximum_cost_usd == Decimal("6.412500")
        and not exposure.long_context_surcharge_applied,
    )
    long_exposure = conservative_astra_cost_exposure(
        replace(
            demand,
            maximum_input_tokens_per_call=ASTRA_MAXIMUM_INPUT_TOKENS,
        )
    )
    check(
        "long_standard_exposure_uses_documented_full_request_multipliers",
        long_exposure.input_rate_per_million_usd == Decimal(25)
        and long_exposure.output_rate_per_million_usd == Decimal(75)
        and long_exposure.maximum_cost_usd == Decimal("32.650000")
        and long_exposure.long_context_surcharge_applied,
    )
    threshold = conservative_astra_cost_exposure(
        replace(
            demand,
            maximum_input_tokens_per_call=ASTRA_LONG_CONTEXT_THRESHOLD,
        )
    )
    above_threshold = conservative_astra_cost_exposure(
        replace(
            demand,
            maximum_input_tokens_per_call=ASTRA_LONG_CONTEXT_THRESHOLD + 1,
        )
    )
    check(
        "long_context_pricing_starts_only_above_272k_input_tokens",
        not threshold.long_context_surcharge_applied
        and above_threshold.long_context_surcharge_applied,
    )

    expected_mapping = {
        "small": "low",
        "medium": "medium",
        "high": "high",
        "max": "max",
        "specialized": "xhigh",
    }
    check(
        "thinking_power_mapping_remains_versioned_candidate_policy",
        {key: ASTRA_REASONING_POLICY.effort_for(key) for key in expected_mapping}
        == expected_mapping,
    )
    alternative_policy = ThinkingPowerReasoningPolicy(
        policy_id="policy:alternative-effort-map",
        version="2.0.0",
        mappings=(
            ("small", "medium"),
            ("medium", "high"),
            ("high", "xhigh"),
            ("max", "max"),
            ("specialized", "low"),
        ),
        supported_efforts=("low", "medium", "high", "xhigh", "max"),
    )
    check(
        "reasoning_policy_changes_are_bound_into_the_request_digest",
        request_with(reasoning_policy=alternative_policy).content_digest
        != baseline_request.content_digest,
    )
    invalid_credentials = (
        "",
        "env:OTHER_API_KEY",
        "sk-not-a-real-key",
        "secret:sk-not-a-real-key",
        "env:sk-not-a-real-key",
    )
    refused_credentials = 0
    for credential_ref in invalid_credentials:
        try:
            replace(authority, credential_ref=credential_ref)
        except AstraRouteReadinessError:
            refused_credentials += 1
    check(
        "only_the_exact_openai_environment_reference_is_accepted",
        refused_credentials == len(invalid_credentials)
        and authority.credential_ref == ASTRA_CREDENTIAL_REF,
    )
    invalid_issuers = (
        "fixture:issuer",
        "sk-not-a-real-key",
        "secret:sk-not-a-real-key",
        "user:bearer token",
        "approval:api_key=not-a-real-key",
    )
    refused_issuers = 0
    for issuer_ref in invalid_issuers:
        try:
            replace(authority, issuer_ref=issuer_ref)
        except AstraRouteReadinessError:
            refused_issuers += 1
    check(
        "issuer_references_have_a_narrow_non_secret_contract",
        refused_issuers == len(invalid_issuers),
    )
    authority_summary = authority.safe_summary()
    authority_json = json.dumps(authority_summary, sort_keys=True)
    check(
        "safe_summary_omits_raw_issuer_and_only_names_the_exact_credential_ref",
        authority.issuer_ref not in authority_json
        and authority_summary["issuer_ref_present"] is True
        and len(str(authority_summary["issuer_ref_sha256"])) == 64
        and authority_summary["credential_ref"] == ASTRA_CREDENTIAL_REF
        and authority_summary["credential_value_present"] is False
        and "sk-" not in authority_json.lower(),
    )

    check(
        "complete_request_digest_is_stable_and_present_on_the_decision",
        len(baseline_request.content_digest) == 64
        and decision.request_digest == baseline_request.content_digest
        and request_with().content_digest == baseline_request.content_digest,
    )
    semantically_equal_money = request_with(
        selected_authority=replace(
            authority,
            maximum_cost_usd=Decimal("6.4125000"),
        )
    )
    equivalent_time = request_with(
        evaluated_at="2026-09-04T10:00:00-04:00",
    )
    check(
        "digest_canonicalizes_decimal_and_evaluation_timestamp_representations",
        semantically_equal_money.content_digest == baseline_request.content_digest
        and equivalent_time.content_digest == baseline_request.content_digest,
    )

    changed_availability = replace(
        available,
        reachable=False,
        content_digest="",
    )
    changed_capabilities = replace(
        ASTRA_ADAPTER_CAPABILITIES,
        text_output_qualified=False,
    )
    digest_variants = (
        request_with(request_id="request:other"),
        request_with(selected_demand=replace(demand, demand_id="demand:other")),
        request_with(selected_demand=replace(demand, model_purpose="code")),
        request_with(selected_demand=replace(demand, thinking_power="high")),
        request_with(selected_demand=replace(demand, maximum_model_calls=2)),
        request_with(
            selected_demand=replace(demand, maximum_input_tokens_per_call=2_000)
        ),
        request_with(selected_demand=replace(demand, service_tier="flex")),
        request_with(selected_demand=replace(demand, required_data_locality="eu")),
        request_with(
            selected_demand=replace(demand, required_modalities=("text", "image"))
        ),
        request_with(selected_demand=replace(demand, requires_tool_calling=True)),
        request_with(
            selected_authority=replace(
                authority,
                authority_id="authority:other",
            )
        ),
        request_with(
            selected_authority=replace(authority, issuer_ref="approval:other")
        ),
        request_with(
            selected_authority=replace(authority, model_calls_authorized=False)
        ),
        request_with(selected_authority=replace(authority, maximum_model_calls=2)),
        request_with(
            selected_authority=replace(authority, maximum_cost_usd=Decimal(7))
        ),
        request_with(selected_authority=replace(authority, version="2.0.0")),
        request_with(
            selected_provider=replace(
                provider,
                availability=changed_availability,
            )
        ),
        request_with(evaluated_at="2026-09-04T14:01:00Z"),
        request_with(
            selected_provider=replace(
                provider,
                data_locality="ordinary",
                data_locality_source_ref="fixture:ordinary-policy",
            )
        ),
        request_with(reasoning_policy=alternative_policy),
        request_with(adapter_capabilities=changed_capabilities),
    )
    variant_digests = {item.content_digest for item in digest_variants}
    check(
        "complete_request_digest_changes_for_every_governed_input_group",
        baseline_request.content_digest not in variant_digests
        and len(variant_digests) == len(digest_variants),
        f"{len(variant_digests)} distinct changed digests",
    )

    forged_ready_refused = False
    try:
        replace(decision, state="ready", refusal_reasons=())
    except AstraRouteReadinessError:
        forged_ready_refused = True
    check(
        "a_forged_ready_decision_cannot_exist_during_quarantine",
        forged_ready_refused,
    )
    historical = replace(
        available,
        observed_at="2000-01-01T00:00:00Z",
        expires_at="2000-01-01T02:00:00Z",
        content_digest="",
    )
    historical_request = request_with(
        selected_provider=replace(provider, availability=historical),
        evaluated_at="2000-01-01T01:00:00Z",
    )
    historical_decision = assess_astra_route_readiness(historical_request)
    check(
        "caller_selected_historical_time_cannot_make_execution_ready",
        not historical_decision.ready
        and ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON in historical_decision.refusal_reasons
        and "trusted_clock_provider_availability"
        in historical_decision.to_dict()["remaining_integration_requirements"],
    )
    no_credential_contract = replace(
        available,
        credential_required=False,
        credential_available=False,
        content_digest="",
    )
    no_credential_decision = assess_astra_route_readiness(
        request_with(
            selected_provider=replace(
                provider,
                availability=no_credential_contract,
            )
        )
    )
    check(
        "openai_availability_cannot_claim_credentials_are_unnecessary",
        "provider_credential_requirement_mismatch"
        in no_credential_decision.refusal_reasons,
    )

    eu_demand = replace(demand, required_data_locality="eu")
    eu_authority = replace(authority, allowed_data_localities=("eu",))
    eu_provider = AstraProviderReadiness(
        availability=available,
        data_locality="eu",
        data_locality_source_ref="fixture:eu-deployment-policy",
    )
    eu_decision = assess_astra_route_readiness(
        request_with(eu_demand, eu_authority, eu_provider)
    )
    check(
        "non_global_locality_is_refused_until_a_regional_adapter_exists",
        "astra_data_locality_not_qualified" in eu_decision.refusal_reasons
        and not eu_decision.ready,
    )
    nonstandard_results = {}
    for service_tier in ("flex", "fast"):
        tier_demand = replace(demand, service_tier=service_tier)
        tier_authority = replace(
            authority,
            allowed_service_tiers=(service_tier,),
            maximum_cost_usd=Decimal(100),
        )
        nonstandard_results[service_tier] = assess_astra_route_readiness(
            request_with(tier_demand, tier_authority)
        ).refusal_reasons
    check(
        "flex_and_fast_are_refused_until_exact_workflows_exist",
        all(
            "astra_service_tier_not_qualified" in reasons
            for reasons in nonstandard_results.values()
        ),
    )
    check(
        "future_route_purpose_is_the_single_requested_purpose",
        demand.requested_route_purposes == ("reasoning",)
        and replace(demand, model_purpose="code").requested_route_purposes == ("code",),
    )

    text_input_off = assess_astra_route_readiness(
        request_with(
            adapter_capabilities=replace(
                ASTRA_ADAPTER_CAPABILITIES,
                text_input_qualified=False,
            )
        )
    )
    text_output_off = assess_astra_route_readiness(
        request_with(
            adapter_capabilities=replace(
                ASTRA_ADAPTER_CAPABILITIES,
                text_output_qualified=False,
            )
        )
    )
    check(
        "text_input_and_output_qualification_are_independent_hard_gates",
        "text_input_adapter_unqualified" in text_input_off.refusal_reasons
        and "text_output_adapter_unqualified" in text_output_off.refusal_reasons,
    )
    capability_cases = (
        ("requires_structured_output", "structured_output_adapter_unqualified"),
        ("requires_tool_calling", "tool_calling_adapter_unqualified"),
        (
            "requires_async_tool_calling",
            "async_tool_calling_adapter_unqualified",
        ),
    )
    check(
        "structured_tool_and_async_capabilities_fail_independently",
        all(
            reason
            in assess_astra_route_readiness(
                request_with(selected_demand=replace(demand, **{field: True}))
            ).refusal_reasons
            for field, reason in capability_cases
        ),
    )
    qualified_tool = AdapterCapabilityQualification(
        "tool_calling",
        model_declared=True,
        adapter_qualified=True,
        qualification_ref="qualification:caller-asserted",
    )
    caller_qualified_capabilities = replace(
        ASTRA_ADAPTER_CAPABILITIES,
        tool_calling=qualified_tool,
    )
    caller_qualified_decision = assess_astra_route_readiness(
        request_with(
            selected_demand=replace(demand, requires_tool_calling=True),
            adapter_capabilities=caller_qualified_capabilities,
        )
    )
    check(
        "self_asserted_capability_qualification_cannot_escape_quarantine",
        not caller_qualified_decision.ready
        and ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON
        in caller_qualified_decision.refusal_reasons,
    )

    def authority_reasons(**changes: object) -> tuple[str, ...]:
        return assess_astra_route_readiness(
            request_with(selected_authority=replace(authority, **changes))
        ).refusal_reasons

    check(
        "model_call_and_paid_route_flags_remain_independent_diagnostics",
        "model_calls_not_authorized" in authority_reasons(model_calls_authorized=False)
        and "paid_route_not_authorized" in authority_reasons(paid_route_opt_in=False),
    )
    check(
        "exact_route_provider_and_model_remain_diagnostic_gates",
        "route_not_authorized" in authority_reasons(authorized_route_name="other.route")
        and "provider_not_authorized"
        in authority_reasons(authorized_provider_id="other")
        and "model_not_authorized"
        in authority_reasons(authorized_model_id="other-model"),
    )
    check(
        "unknown_budget_ceilings_remain_explicit_diagnostics",
        all(
            reason in authority_reasons(**{field: None})
            for field, reason in (
                ("maximum_model_calls", "maximum_model_calls_authority_unknown"),
                ("maximum_input_tokens", "maximum_input_tokens_authority_unknown"),
                ("maximum_output_tokens", "maximum_output_tokens_authority_unknown"),
                ("maximum_total_tokens", "maximum_total_tokens_authority_unknown"),
                ("maximum_cost_usd", "maximum_cost_authority_unknown"),
            )
        ),
    )
    check(
        "insufficient_budget_ceilings_remain_explicit_diagnostics",
        "maximum_model_calls_authority_insufficient"
        in authority_reasons(maximum_model_calls=0)
        and "maximum_input_tokens_authority_insufficient"
        in authority_reasons(maximum_input_tokens=999)
        and "maximum_output_tokens_authority_insufficient"
        in authority_reasons(maximum_output_tokens=127_999)
        and "maximum_total_tokens_authority_insufficient"
        in authority_reasons(maximum_total_tokens=128_999)
        and "maximum_cost_authority_insufficient"
        in authority_reasons(maximum_cost_usd=Decimal("6.412499")),
    )

    class NoNetworkTransport:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, request: object, *, timeout: float) -> object:
            del request, timeout
            self.calls += 1
            raise AssertionError("quarantined plan construction opened transport")

    transport = NoNetworkTransport()
    credential_reads = 0

    def credential_source() -> str:
        nonlocal credential_reads
        credential_reads += 1
        raise AssertionError("quarantined plan construction read a credential")

    adapter = OpenAIResponsesAdapter(
        transport=transport,
        api_key_source=credential_source,
        reasoning_effort="medium",
    )
    exact_adapter_blocked = False
    exact_adapter_error = ""
    try:
        build_explicit_astra_route_plan(baseline_request, decision, adapter)
    except AstraRouteReadinessError as exc:
        exact_adapter_blocked = True
        exact_adapter_error = str(exc)
    check(
        "exact_adapter_reaches_the_unconditional_plan_quarantine",
        exact_adapter_blocked
        and ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON in exact_adapter_error
        and transport.calls == 0
        and credential_reads == 0,
    )
    mismatched_effort_refused = False
    try:
        build_explicit_astra_route_plan(
            baseline_request,
            decision,
            OpenAIResponsesAdapter(
                transport=transport,
                api_key_source=credential_source,
                reasoning_effort="xhigh",
            ),
        )
    except AstraRouteReadinessError as exc:
        mismatched_effort_refused = "reasoning effort" in str(exc)
    check(
        "wire_reasoning_effort_cannot_diverge_from_the_bound_policy",
        mismatched_effort_refused and transport.calls == 0 and credential_reads == 0,
    )

    class ImpostorAdapter:
        DEFAULT_MODEL = DEFAULT_MODEL
        WIRE_FORMAT = "openai_responses"
        reasoning_effort = "medium"

    class AdapterSubclass(OpenAIResponsesAdapter):
        pass

    impostor_refused = False
    subclass_refused = False
    try:
        build_explicit_astra_route_plan(
            baseline_request,
            decision,
            ImpostorAdapter(),
        )
    except AstraRouteReadinessError as exc:
        impostor_refused = "exact quarantined OpenAIResponsesAdapter" in str(exc)
    try:
        build_explicit_astra_route_plan(
            baseline_request,
            decision,
            AdapterSubclass(
                transport=transport,
                api_key_source=credential_source,
                reasoning_effort="medium",
            ),
        )
    except AstraRouteReadinessError as exc:
        subclass_refused = "exact quarantined OpenAIResponsesAdapter" in str(exc)
    check(
        "duck_typed_and_subclassed_adapters_are_refused",
        impostor_refused
        and subclass_refused
        and transport.calls == 0
        and credential_reads == 0,
    )

    changed_purpose_request = request_with(
        selected_demand=replace(demand, model_purpose="code")
    )
    stale_decision_refused = False
    try:
        build_explicit_astra_route_plan(
            changed_purpose_request,
            decision,
            adapter,
        )
    except AstraRouteReadinessError as exc:
        stale_decision_refused = "request digest" in str(exc)
    check(
        "a_decision_cannot_be_reused_for_a_changed_request",
        stale_decision_refused
        and decision.request_digest != changed_purpose_request.content_digest,
    )
    changed_capability_request = request_with(
        selected_demand=replace(demand, requires_tool_calling=True),
        adapter_capabilities=caller_qualified_capabilities,
    )
    changed_capability_refused = False
    try:
        build_explicit_astra_route_plan(
            changed_capability_request,
            decision,
            adapter,
        )
    except AstraRouteReadinessError as exc:
        changed_capability_refused = "request digest" in str(exc)
    check(
        "an_old_decision_cannot_advertise_new_caller_qualified_capabilities",
        changed_capability_refused
        and decision != assess_astra_route_readiness(changed_capability_request),
    )

    repeated_compilations_blocked = 0
    for _ in range(2):
        try:
            build_explicit_astra_route_plan(baseline_request, decision, adapter)
        except AstraRouteReadinessError as exc:
            if ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON in str(exc):
                repeated_compilations_blocked += 1
    check(
        "one_candidate_authority_cannot_compile_even_one_reusable_plan",
        repeated_compilations_blocked == 2
        and transport.calls == 0
        and credential_reads == 0,
    )

    direct_plan_refused = False
    try:
        AstraRoutePlan(
            request_id=baseline_request.request_id,
            request_digest=baseline_request.content_digest,
            demand_id=demand.demand_id,
            model_purpose=demand.model_purpose,
            route=object(),
            provider=object(),
            reasoning_effort="medium",
            maximum_model_calls=1,
            maximum_input_tokens=1_000,
            maximum_output_tokens=128_000,
            maximum_total_tokens=129_000,
            maximum_cost_exposure_usd=exposure.maximum_cost_usd,
            authority_ref=authority.authority_id,
            availability_snapshot_ref=available.snapshot_id,
            capability_policy=ASTRA_ADAPTER_CAPABILITIES,
        )
    except AstraRouteReadinessError as exc:
        direct_plan_refused = ASTRA_EXECUTABLE_ROUTE_REFUSAL_REASON in str(exc)
    check(
        "direct_route_plan_construction_is_also_quarantined",
        direct_plan_refused,
    )
    check(
        "astra_remains_absent_from_default_routes",
        all(route.name != ASTRA_ROUTE_NAME for route in default_routes()),
    )

    passed = sum(1 for item in tests if item["passed"])
    return {
        "record_type": "astra_route_authority_offline_checks/v2",
        "scope": "passive_policy_quarantine_only",
        "model": DEFAULT_MODEL,
        "executable_route_qualified": ASTRA_EXECUTABLE_ROUTE_QUALIFIED,
        "remaining_integration_requirements": list(
            ASTRA_REMAINING_INTEGRATION_REQUIREMENTS
        ),
        "route_plan_constructed": False,
        "provider_integration_proven": False,
        "paid_route_registered": False,
        "network_calls": transport.calls,
        "credential_reads": credential_reads,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


def self_test() -> dict[str, object]:
    """Package-suite entry point for the offline quarantine checks."""
    return run_checks()
