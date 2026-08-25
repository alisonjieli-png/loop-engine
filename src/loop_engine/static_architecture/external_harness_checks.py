"""Focused offline checks for the external harness contract.

The production boundary delegates here so it stays below the repository module
size cap. These checks use local protocol fixtures only.
"""
from __future__ import annotations

from dataclasses import replace

from ..loop.loop_contract import LoopContract
from .external_harness import (
    HarnessAdapterInfo, HarnessArtifactRef, HarnessBudget, HarnessError,
    HarnessModelCall, HarnessRunRequest, HarnessRunResult, HarnessServices,
    ModelOutputLimit, StaticModelOutputResolver, _budget_failure,
    resolve_harness_output_limit, run_external_harness,
)


def run_checks() -> dict:
    """Run offline contracts with local injected adapters only."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": f"contract_only_{name}",
                      "passed": bool(passed), "detail": detail})

    contract = LoopContract(
        "external-solver", "model_led", input_roles=("problem/v1",),
        output_roles=("answer/v1",), effects=("pure",))
    budget = HarnessBudget(max_model_calls=2, max_total_tokens=100)
    refused = False
    try:
        HarnessRunRequest(
            "req-no-auth", "deep_agents", "solve", contract, budget,
            provider_id="ollama_cloud", model_id="configured-model-ref")
    except HarnessError:
        refused = True
    check("model_authorization_is_explicit", refused)

    request = HarnessRunRequest(
        "req-contract", "deep_agents", "solve the selected problem",
        contract, budget, authorize_model_calls=True,
        context_refs=("ctx:one",), provider_id="ollama_cloud",
        model_id="configured-model-ref")
    check("request_digest_is_stable_and_full_length",
          request.digest == request.digest and len(request.digest) == 64)

    limit = ModelOutputLimit(
        65536, "endpoint_observed",
        "ollama-openai-error:deepseek-v4-flash:0731",
        provider_id="ollama_cloud",
        model_id="configured-model-ref")
    resolved = resolve_harness_output_limit(
        request, HarnessServices(model_output_resolver=
                                 StaticModelOutputResolver((limit,))))
    check("resolved_output_capability_precedes_run_identity",
          resolved.budget.max_output_tokens == 65536
          and resolved.digest != request.digest
          and resolved.budget.output_limit.reference == limit.reference)
    provider_mismatch_refused = False
    wrong_provider_limit = ModelOutputLimit(
        65536, "endpoint_observed", "wrong-provider-fixture",
        provider_id="mistral", model_id="configured-model-ref")
    try:
        resolve_harness_output_limit(
            replace(request, budget=replace(
                request.budget, output_limit=wrong_provider_limit)))
    except HarnessError:
        provider_mismatch_refused = True
    check("output_maximum_is_bound_to_exact_provider_and_model",
          provider_mismatch_refused)

    calls = (HarnessModelCall(
        "mistral", "configured-model-ref", True,
        input_tokens=10, output_tokens=5, cost=0.01),)
    result = HarnessRunResult(
        request.request_id, request.harness_id, "completed",
        output={"answer": 42}, model_calls=calls,
        adapter_version="contract")
    check("known_physical_usage_is_preserved",
          result.physical_model_calls == 1
          and result.total_tokens == 15
          and result.total_cost == 0.01
          and result.accounting_complete)
    check("adapter_completion_does_not_claim_task_acceptance",
          result.safe_summary()["acceptance"] == "not_evaluated")
    incomplete = HarnessRunResult(
        request.request_id, request.harness_id, "completed",
        output={"answer": 42}, call_count_complete=False,
        reported_model_call_count=None)
    check("missing_call_accounting_remains_unknown",
          incomplete.physical_model_calls is None
          and incomplete.total_tokens is None
          and not incomplete.accounting_complete)
    check("incomplete_accounting_fails_the_budget_contract",
          _budget_failure(request, incomplete)
          == "model_call_accounting_incomplete")

    too_many = HarnessRunResult(
        request.request_id, request.harness_id, "completed",
        output={"answer": 42}, model_calls=calls * 3,
        adapter_version="contract")
    check("physical_calls_over_the_ceiling_are_rejected",
          _budget_failure(request, too_many)
          == "model_call_budget_exhausted")

    secret_refused = False
    try:
        HarnessRunRequest(
            "secret", "deep_agents", "solve", contract, budget,
            authorize_model_calls=True,
            provider_id="ollama_cloud", model_id="configured-model-ref",
            metadata={"api_key": "must-not-enter-request"})
    except HarnessError:
        secret_refused = True
    check("secret_shaped_metadata_is_refused", secret_refused)

    sensitive_names = (
        "api_key", "access_token", "bearer_token", "password", "secret")
    refused_names = []
    for name in sensitive_names:
        try:
            HarnessRunRequest(
                f"secret-{name}", "deep_agents", "solve", contract, budget,
                authorize_model_calls=True, provider_id="ollama_cloud",
                model_id="configured-model-ref",
                metadata={name: "not-allowed"})
        except HarnessError:
            refused_names.append(name)
    safe_budget_metadata = HarnessRunRequest(
        "safe-budget", "deep_agents", "solve", contract, budget,
        authorize_model_calls=True, provider_id="ollama_cloud",
        model_id="configured-model-ref",
        metadata={"max_total_tokens": 100, "token_budget": 100})
    check("credential_names_are_refused_but_budget_names_are_allowed",
          tuple(refused_names) == sensitive_names
          and safe_budget_metadata.metadata["token_budget"] == 100)

    invalid_output_refused = False
    try:
        ModelOutputLimit(0, "provider_declared", "invalid")
    except HarnessError:
        invalid_output_refused = True
    provider_native = HarnessBudget(
        max_model_calls=1, max_total_tokens=100)
    check("unresolved_output_maximum_remains_unknown_until_resolution",
          invalid_output_refused
          and provider_native.max_output_tokens is None)

    class FailingProtocolAdapter:
        def __init__(self):
            self.calls = 0

        @staticmethod
        def info():
            return HarnessAdapterInfo(
                "deep_agents", "protocol-fixture/v1", "not-imported",
                available=True,
                limitations=("no provider integration is exercised",))

        def run(self, active_request, active_services):
            self.calls += 1
            return HarnessRunResult(
                active_request.request_id, active_request.harness_id,
                "failed", error_code="declared_fixture_failure",
                model_calls=(HarnessModelCall(
                    active_request.provider_id, active_request.model_id, False,
                    input_tokens=1, output_tokens=0,
                    error_code="declared_fixture_failure"),),
                adapter_version="protocol-fixture/v1")

    class OutputProtocolAdapter:
        def __init__(self, output):
            self.output = output
            self.calls = 0

        @staticmethod
        def info():
            return HarnessAdapterInfo(
                "deep_agents", "protocol-fixture/v1", "not-imported",
                available=True,
                limitations=("local protocol fixture only",))

        def run(self, active_request, active_services):
            self.calls += 1
            return HarnessRunResult(
                active_request.request_id, active_request.harness_id,
                "completed", output=self.output,
                model_calls=(HarnessModelCall(
                    active_request.provider_id, active_request.model_id, True,
                    input_tokens=1, output_tokens=1),),
                adapter_version="protocol-fixture/v1")

    one_call_budget = HarnessBudget(
        max_model_calls=1, output_limit=limit)
    one_call_request = HarnessRunRequest(
        "req-one-adapter-call", "deep_agents", "exercise one boundary",
        contract, one_call_budget, authorize_model_calls=True,
        provider_id="ollama_cloud", model_id="configured-model-ref")
    failing_adapter = FailingProtocolAdapter()
    import tempfile
    from .context_artifacts import (
        ContextArtifactManager, ContextArtifactStore,
        ContextArtifactStoreSpec)
    with tempfile.TemporaryDirectory(prefix="loop-engine-harness-") as root:
        manager = ContextArtifactManager(ContextArtifactStore(
            ContextArtifactStoreSpec(root)))
        failed_once = run_external_harness(
            failing_adapter, one_call_request,
            services=HarnessServices(artifact_store=manager))
        small_adapter = OutputProtocolAdapter({"answer": 42})
        small = run_external_harness(
            small_adapter, replace(one_call_request, request_id="small-output"),
            services=HarnessServices(artifact_store=manager))
        large_text = "large external harness output " * 2_000
        large_adapter = OutputProtocolAdapter(large_text)
        large = run_external_harness(
            large_adapter, replace(one_call_request, request_id="large-output"),
            services=HarnessServices(artifact_store=manager))
        forged_adapter = OutputProtocolAdapter(HarnessArtifactRef(
            "context-output:" + "a" * 64,
            "sha256/aa/" + "a" * 64, "a" * 64,
            media_type="text/plain", size_bytes=4))
        forged = run_external_harness(
            forged_adapter, replace(one_call_request, request_id="forged-ref"),
            services=HarnessServices(artifact_store=manager))
        from .context_artifacts import ContextArtifactRef
        small_ref = small.artifacts[0]
        large_ref = large.artifacts[0]
        stored_small = manager.store.get_text(ContextArtifactRef(
            small_ref.digest, small_ref.size_bytes or 0,
            media_type=small_ref.media_type,
            artifact_kind="external_harness_output"))
        stored_large = manager.store.get_text(ContextArtifactRef(
            large_ref.digest, large_ref.size_bytes or 0,
            media_type=large_ref.media_type,
            artifact_kind="external_harness_output"))
        missing_manager_adapter = OutputProtocolAdapter("must not run")
        missing_manager = run_external_harness(
            missing_manager_adapter,
            replace(one_call_request, request_id="missing-manager"))
    check("failed_adapter_crosses_the_physical_runner_boundary_once",
          failing_adapter.calls == 1
          and failed_once.status == "failed"
          and failed_once.physical_model_calls == 1,
          "This is a local protocol fixture, not provider integration proof.")
    check("available_adapter_requires_context_artifact_manager_before_execution",
          missing_manager.status == "refused"
          and missing_manager.error_code == "context_artifact_manager_required"
          and missing_manager_adapter.calls == 0)
    check("small_adapter_output_is_stored_then_kept_inline",
          small.output == {"answer": 42}
          and len(small.artifacts) == 1
          and stored_small == '{"answer":42}')
    check("large_adapter_output_is_stored_then_replaced_by_typed_reference",
          isinstance(large.output, HarnessArtifactRef)
          and large.output == large_ref
          and stored_large == large_text
          and large_text not in str(large.safe_summary()))
    check("unresolvable_adapter_artifact_reference_fails_closed",
          forged.status == "failed"
          and forged.error_code == "output_capture_failed"
          and forged.output is None)

    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
