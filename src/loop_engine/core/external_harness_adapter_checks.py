"""Focused SDK adapter contract checks, delegated by the public facade.

These checks exercise local SDK argument and result boundaries with fixtures.
They do not install a package, contact a provider, or establish task quality.
"""
from __future__ import annotations

from .external_harness_adapters import (
    ConfiguredHarnessAdapter,
    HarnessRunRequest,
    HarnessRuntimeBinding,
    HarnessServices,
    PhysicalCallCountingClient,
    _FRAMEWORKS,
    _deep_agents_graph_config,
    _instruction_resource,
    _microsoft_harness_kwargs,
    _normalize,
    _openai_model_settings_kwargs,
    _prompt,
    _pydantic_model_settings_kwargs,
    _pydantic_usage_limit_kwargs,
    _required_runtime_binding,
    _resolve_output_request,
    builtin_harness_adapters,
)


def run_checks() -> dict:
    """Run pure adapter-shape checks without an SDK or model invocation."""
    from dataclasses import replace
    from unittest.mock import patch

    from ..loop.loop_contract import LoopContract
    from .external_harness import (
        HarnessBudget, HarnessError, ModelOutputLimit,
        StaticModelOutputResolver)

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": f"contract_only_{name}",
                      "passed": bool(passed), "detail": detail})

    contract = LoopContract(
        "external", "model_led", input_roles=("problem/v1",),
        output_roles=("answer/v1",))
    request = HarnessRunRequest(
        "contract-shape", "deep_agents", "inspect the selected artifact",
        contract,
        provider_id="ollama_cloud", model_id="configured-model-ref",
        authorize_model_calls=True,
        budget=HarnessBudget(
            max_model_calls=2, max_total_tokens=100),
        metadata={"temperature": 0.2})

    adapters = builtin_harness_adapters()
    check("inventory_has_four_unregistered_optional_adapters",
          len(adapters) == 4
          and {adapter.harness_id for adapter in adapters}
          == set(_FRAMEWORKS))
    infos = {adapter.harness_id: adapter.info() for adapter in adapters}
    check("inventory_lists_only_features_wired_by_each_adapter",
          all(infos[name].features == tuple(facts["features"])
              for name, facts in _FRAMEWORKS.items())
          and "mcp" not in infos["openai_agents"].features
          and "skills" not in infos["microsoft_agent_framework"].features)
    check("package_detection_is_not_reported_as_runtime_integration_proof",
          all(any("not package-backed runtime integration proof" in item
                  for item in info.limitations)
              for info in infos.values())
          and all(info.available or any(
              "runtime integration is unproven" in item
              for item in info.limitations)
              for info in infos.values()))
    check("prompt_contains_contract_without_acceptance_claim",
          "not claim verification or acceptance" in _prompt(request)
          and "answer/v1" in _prompt(request))

    normalized = _normalize({
        "output": {"answer": 1},
        "usage": {"requests": 1, "input_tokens": 9,
                  "output_tokens": 4, "cost": 0.001}},
        request, adapter_version="contract")
    check("provider_neutral_fields_keep_declared_usage",
          normalized.physical_model_calls == 1
          and normalized.total_tokens == 13
          and normalized.total_cost == 0.001
          and normalized.provider_id == "ollama_cloud"
          and normalized.model_id == "configured-model-ref"
          and normalized.model_calls[0].provider == "ollama_cloud"
          and normalized.model_calls[0].provider != request.harness_id
          and normalized.max_output_tokens_used is None)

    instruction = _instruction_resource("deep_agents")
    prompt_bound = _normalize({
        "output": {"answer": 1},
        "usage": {"requests": 1, "input_tokens": 9,
                  "output_tokens": 4}},
        request, adapter_version="contract",
        prompt_resource=instruction)
    check("versioned_prompt_resource_identity_reaches_safe_result",
          prompt_bound.prompt_resource_ref == instruction.bundle_ref
          and prompt_bound.prompt_resource_digest == instruction.bundle_digest
          and prompt_bound.prompt_slot_schema_digest
              == instruction.slot_schema_digest
          and prompt_bound.prompt_render_digest == instruction.render_digest
          and "text" not in prompt_bound.safe_summary())

    unknown = _normalize(
        {"output": {"answer": 1}}, request,
        adapter_version="contract")
    check("missing_usage_is_incomplete_not_zero",
          unknown.physical_model_calls is None
          and not unknown.call_count_complete
          and unknown.total_tokens is None)

    check("unresolved_output_maximum_is_not_reported_as_applied",
          request.budget.max_output_tokens is None
          and normalized.max_output_tokens_used is None)

    limit = ModelOutputLimit(
        65536, "endpoint_observed",
        "ollama-openai-error:deepseek-v4-flash:0731",
        provider_id="ollama_cloud",
        model_id="configured-model-ref")
    resolved = _resolve_output_request(
        request, HarnessServices(model_output_resolver=
                                 StaticModelOutputResolver((limit,))))
    check("typed_capability_resolves_exact_output_maximum",
          resolved.budget.max_output_tokens == 65536
          and resolved.budget.output_limit.reference == limit.reference)
    not_applied = _normalize(
        {"output": {"answer": 1},
         "usage": {"requests": 1, "input_tokens": 1,
                   "output_tokens": 1}},
        resolved, adapter_version="contract")
    applied = _normalize(
        {"output": {"answer": 1},
         "usage": {"requests": 1, "input_tokens": 1,
                   "output_tokens": 1}},
        resolved, adapter_version="contract", applied_output_limit=limit)
    check("normalization_reports_maximum_only_after_adapter_application",
          not_applied.max_output_tokens_used is None
          and not not_applied.model_output_limit_source
          and applied.max_output_tokens_used == 65536
          and applied.model_output_limit_source == "endpoint_observed"
          and applied.model_output_limit_reference == limit.reference)

    injected_seen = []

    def injected_runner(active_request, active_services):
        injected_seen.append(active_request.budget.max_output_tokens)
        return {"output": {"answer": 1},
                "usage": {"requests": 1, "input_tokens": 1,
                          "output_tokens": 1}}

    injected = ConfiguredHarnessAdapter(
        "deep_agents", runner=injected_runner)
    injected_result = injected.run(
        request, HarnessServices(model_output_resolver=
                                 StaticModelOutputResolver((limit,))))
    check("injected_runner_receives_exact_limit_without_automatic_claim",
          injected_seen == [65536]
          and injected_result.max_output_tokens_used is None
          and injected.info().features[-1] == "injected_runner")

    model_binding = HarnessRuntimeBinding(
        "ollama_cloud", "configured-model-ref", "model", object(),
        "settings:ollama-cloud")
    bound_services = HarnessServices(runtime_binding=model_binding)
    binding_ok = _required_runtime_binding(
        resolved, bound_services, runtime_kind="model")
    check("provider_bound_model_is_required_before_package_import",
          binding_ok is model_binding)

    missing_binding_refused = deep_unbound_refused = False
    try:
        _required_runtime_binding(
            resolved, HarnessServices(), runtime_kind="model")
    except HarnessError:
        missing_binding_refused = True
    try:
        _required_runtime_binding(
            resolved, bound_services, runtime_kind="model",
            preconfigured_output_limit=True)
    except HarnessError:
        deep_unbound_refused = True
    check("missing_provider_binding_fails_before_package_import",
          missing_binding_refused)
    check("deep_agents_requires_a_preconfigured_exact_output_maximum",
          deep_unbound_refused)
    deep_binding = HarnessRuntimeBinding(
        "ollama_cloud", "configured-model-ref", "model", object(),
        "settings:ollama-cloud-max-output", output_limit=limit)
    check("deep_agents_accepts_only_the_matching_preconfigured_limit",
          _required_runtime_binding(
              resolved, HarnessServices(runtime_binding=deep_binding),
              runtime_kind="model", preconfigured_output_limit=True)
          is deep_binding)

    openai_settings = _openai_model_settings_kwargs(resolved)
    check("openai_adapter_passes_exact_maximum_to_ModelSettings",
          openai_settings["max_tokens"] == 65536
          and openai_settings["include_usage"] is True)
    check("pydantic_adapter_passes_exact_maximum_and_request_budget",
          _pydantic_model_settings_kwargs(resolved)["max_tokens"] == 65536
          and _pydantic_usage_limit_kwargs(resolved)["request_limit"] == 2
          and _pydantic_usage_limit_kwargs(
              resolved)["total_tokens_limit"] == 100)
    check("deep_agents_graph_recursion_is_bounded",
          _deep_agents_graph_config(resolved)["recursion_limit"] == 10)

    class ProviderBoundaryContract:
        additional_properties = {"contract": True}

        def get_response(self, value, **kwargs):
            return value, kwargs

    counted = PhysicalCallCountingClient(
        ProviderBoundaryContract(), max_calls=2)
    microsoft_settings = _microsoft_harness_kwargs(resolved, counted)
    check("microsoft_adapter_passes_exact_maximum_to_harness_boundary",
          microsoft_settings["max_output_tokens"] == 65536
          and microsoft_settings["client"] is counted
          and microsoft_settings["disable_web_search"] is True
          and microsoft_settings["disable_file_memory"] is True
          and microsoft_settings["disable_compaction"] is True
          and microsoft_settings["disable_todo"] is True
          and microsoft_settings["disable_mode"] is True
          and microsoft_settings["disable_tool_auto_approval"] is True)
    first_value = counted.get_response("one", stream=False)
    second_value = counted.get_response("two", stream=False)
    budget_refused = False
    try:
        counted.get_response("three", stream=False)
    except HarnessError:
        budget_refused = True
    check("physical_call_decorator_counts_the_sdk_request_boundary",
          counted.call_count == 2
          and first_value[0] == "one" and second_value[0] == "two"
          and counted.additional_properties == {"contract": True}
          and budget_refused)

    bad_cap_refused = False
    try:
        ModelOutputLimit(0, "provider_declared", "invalid")
    except HarnessError:
        bad_cap_refused = True
    check("invalid_output_cap_is_refused", bad_cap_refused)

    from .model_capabilities import ModelOutputAllocation, ModelOutputCapability
    allocation = ModelOutputAllocation(
        ModelOutputCapability(limit.max_output_tokens, limit.reference),
        request.provider_id, request.model_id, "fixture.route", 4096,
        "fixture:output-allocation", "Explicit bounded SDK response allocation")
    allocated = replace(resolved, model_routes=("fixture.route",),
                        budget=replace(resolved.budget, output_allocation=allocation))
    check("sdk_builders_apply_selected_allowance_and_preserve_capacity",
          _openai_model_settings_kwargs(allocated)["max_tokens"] == 4096
          and _pydantic_model_settings_kwargs(allocated)["max_tokens"] == 4096
          and _microsoft_harness_kwargs(allocated, counted)["max_output_tokens"] == 4096
          and allocated.budget.max_output_tokens == 65536)
    selected = _normalize({"output": "answer", "usage": {"requests": 1}}, allocated,
                          adapter_version="contract", applied_output_limit=limit)
    mismatch_refused = False
    try:
        _normalize(replace(selected, max_output_tokens_used=65536), allocated,
                   adapter_version="contract", applied_output_limit=limit)
    except HarnessError:
        mismatch_refused = True
    check("normalized_applied_output_reports_allowance_without_relabeling_capacity",
          selected.max_output_tokens_used == 4096
          and selected.model_output_limit_reference == limit.reference and mismatch_refused)
    unbounded = replace(resolved, budget=replace(resolved.budget, max_model_calls=None))
    unbounded_client = PhysicalCallCountingClient(ProviderBoundaryContract(), max_calls=None)
    for name in ("first", "second", "third"):
        unbounded_client.get_response(name)
    check("pydantic_and_counted_client_preserve_explicit_unbounded_call_authority",
          _pydantic_usage_limit_kwargs(unbounded)["request_limit"] is None
          and unbounded_client.call_count == 3)
    refusals = []
    for harness_id, method in (("deep_agents", "_run_deep_agents"),
                               ("openai_agents", "_run_openai_agents")):
        adapter = ConfiguredHarnessAdapter(harness_id)
        with patch.object(adapter, method, side_effect=AssertionError("SDK execution must not start")):
            result = adapter.run(replace(unbounded, harness_id=harness_id), HarnessServices())
        refusals.append(result.status == "refused"
                        and "feature:unbounded_model_calls" in result.capability_evaluation["missing"]
                        and result.capability_evaluation["execution_started"] is False)
    graph_refused = False
    try:
        _deep_agents_graph_config(unbounded)
    except HarnessError:
        graph_refused = True
    check("unsupported_unbounded_sdk_profiles_refuse_before_execution",
          all(refusals) and graph_refused)
    deep = ConfiguredHarnessAdapter("deep_agents")
    with patch.object(deep, "_run_deep_agents", side_effect=AssertionError("SDK execution must not start")):
        refused_allocation = deep.run(allocated, HarnessServices())
    check("deep_agents_refuses_a_reduced_allocation_without_a_matching_preconfigured_binding",
          refused_allocation.status == "refused"
          and "feature:output_allocation" in refused_allocation.capability_evaluation["missing"]
          and refused_allocation.capability_evaluation["execution_started"] is False)
    explicit = ConfiguredHarnessAdapter("deep_agents", runner=lambda current, services: {
        "output": "fixture", "usage": {"requests": 1, "input_tokens": 1, "output_tokens": 1}})
    check("unbounded_injected_runner_is_not_mistaken_for_unsupported_sdk_execution",
          explicit.run(unbounded, HarnessServices()).completed)

    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
