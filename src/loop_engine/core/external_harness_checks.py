"""Focused offline checks for the external harness contract.

The production boundary delegates here so it stays below the repository module
size cap. These checks use local protocol fixtures only.
"""
from __future__ import annotations

from dataclasses import replace
from operator import setitem

from ..loop.loop_contract import LoopContract
from .external_harness import (
    HarnessAdapterInfo, HarnessArtifactRef, HarnessBudget, HarnessError,
    HarnessModelCall, HarnessRegistry, HarnessRunRequest, HarnessRunResult, HarnessServices,
    ModelOutputLimit, StaticModelOutputResolver, _budget_failure,
    resolve_harness_output_limit, run_external_harness,
)
from .harness_execution_contracts import (
    HarnessExecutionCapabilities, HarnessExecutionRequirements,
    harness_loop_identity, plain_harness_json,
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

    def rejects(action):
        try:
            action()
        except (HarnessError, ValueError, TypeError):
            return True
        return False

    class RegisteredAdapter(OutputProtocolAdapter):
        """An explicitly supplied host fixture, not a discovered module."""

        def __init__(self):
            super().__init__({"answer": 42})
            self.version = "protocol-fixture/v1"

        def info(self):
            return HarnessAdapterInfo(
                "host_supplied_solver", self.version, "not-imported", available=True,
                execution_capabilities=HarnessExecutionCapabilities())

    custom = RegisteredAdapter()
    custom_request = replace(one_call_request, harness_id="host_supplied_solver")
    registry = HarnessRegistry((custom,))
    check("arbitrary_adapter_identifier_requires_explicit_host_registration",
          registry.get(custom_request.harness_id) is custom
          and rejects(lambda: registry.get("not_registered"))
          and rejects(lambda: registry.register(custom)))
    custom.version = "protocol-fixture/v2"
    check("registration_version_drift_requires_explicit_replacement",
          rejects(lambda: registry.get(custom_request.harness_id)))
    custom.version = "protocol-fixture/v1"
    check("path_and_import_shaped_adapter_identifiers_are_refused",
          all(rejects(lambda value=value: replace(custom_request, harness_id=value))
              for value in ("../escape", "module:Class", "", "x" * 97)))

    with tempfile.TemporaryDirectory(prefix="loop-engine-harness-contract-") as root:
        manager = ContextArtifactManager(ContextArtifactStore(ContextArtifactStoreSpec(root)))
        services = HarnessServices(artifact_store=manager)
        custom_result = run_external_harness(registry.get(custom_request.harness_id),
                                             custom_request, services=services)
        check("new_host_adapter_executes_through_the_same_loop_runtime",
              custom.calls == 1 and custom_result.completed
              and bool(custom_result.loop_id)
              and custom_result.safe_summary()["acceptance"] == "not_evaluated")
        requirements = (
            {"tool_refs": ("tool:read",)}, {"skill_refs": ("skill:review",)},
            {"context_refs": ("context:source",)},
            {"workspace_ref": "workspace:confined"},
            {"approval_policy_ref": "policy:exact-effects"},
            {"model_routes": ("route:one",)}, {"context_visibility": "fresh"},
            {"context_visibility": "shared_runtime_memory"},
            {"contract": replace(contract, effects=("writes_fs",))},
            {"contract": replace(contract, effects=("spawns_process",))},
            {"contract": replace(contract, effects=("network",))},
            {"contract": replace(contract, effects=("reads_secret",))},
            {"execution_requirements": HarnessExecutionRequirements(
                required_features=("body_hydration",))},
            {"execution_requirements": HarnessExecutionRequirements(
                required_limits=("total_tokens", "cost"))},
            {"execution_requirements": HarnessExecutionRequirements(
                allowed_isolations=("container",))},
        )
        for index, changes in enumerate(requirements):
            before = custom.calls
            refused_result = run_external_harness(
                custom, replace(custom_request, **changes), services=services)
            check(f"unsupported_mechanic_{index}_refused_before_adapter_run",
                  refused_result.status == "refused" and custom.calls == before
                  and refused_result.capability_evaluation["execution_started"] is False)
        before = custom.calls
        check("unknown_profile_version_refused_without_dispatch",
              rejects(lambda: run_external_harness(custom, replace(
                  custom_request, profile_version="999.0.0"), services=services))
              and custom.calls == before)
        research = replace(custom_request, profile_id="practitioner.research")
        identity = harness_loop_identity(research)
        research_result = run_external_harness(custom, research, services=services)
        check("requested_exact_practitioner_profile_is_resolved",
              identity.profile_id == research.profile_id and research_result.completed)

        class WrongModelAdapter(RegisteredAdapter):
            def run(self, active_request, active_services):
                result = super().run(active_request, active_services)
                result.model_calls = (replace(result.model_calls[0], model="different"),)
                return result

        class WrongVersionAdapter(RegisteredAdapter):
            def run(self, active_request, active_services):
                result = super().run(active_request, active_services)
                result.adapter_version = "changed-version"
                return result

        class ExceptionAdapter(RegisteredAdapter):
            def run(self, active_request, active_services):
                raise RuntimeError("SECRET_FIXTURE_NOT_FOR_HISTORY")

        for variant in (WrongModelAdapter, WrongVersionAdapter):
            check(f"{variant.__name__}_cannot_return_completion",
                  rejects(lambda variant=variant: run_external_harness(
                      variant(), custom_request, services=services)))
        exception_result = run_external_harness(ExceptionAdapter(), custom_request,
                                              services=services)
        check("adapter_exception_text_not_published",
              not exception_result.completed
              and "SECRET_FIXTURE" not in str(exception_result.safe_summary())
              and "SECRET_FIXTURE" not in exception_result.error)
        shared = {"nested": [1]}
        producer = RegisteredAdapter()
        producer.output = shared
        detached = run_external_harness(producer, custom_request, services=services)
        shared["nested"].append(2)
        check("small_harness_output_detached_from_producer",
              detached.output == {"nested": [1]})
        detached.output["nested"].append(3)
        check("returned_output_mutation_cannot_change_producer",
              shared == {"nested": [1, 2]})
        private = HarnessRunResult(custom_request.request_id, custom_request.harness_id,
                                   "failed", error="PRIVATE_FIXTURE", error_code="PRIVATE_FIXTURE")
        check("unregistered_adapter_error_code_not_published",
              "PRIVATE_FIXTURE" not in str(private.safe_summary()))

        class RetainedResultAdapter(RegisteredAdapter):
            def run(self, active_request, active_services):
                self.returned = super().run(active_request, active_services)
                return self.returned

        retained_adapter = RetainedResultAdapter()
        retained_adapter.output = {"nested": {"parts": [1]}}
        owned = run_external_harness(retained_adapter, custom_request,
                                     services=services)
        captured_ref = owned.artifacts[0]
        retained_adapter.returned.output["nested"]["parts"].append(2)
        retained_adapter.returned.status = "failed"
        check("result_envelope_and_nested_output_detached_from_retained_adapter_result",
              owned is not retained_adapter.returned and owned.completed
              and owned.output == {"nested": {"parts": [1]}}
              and manager.store.get_text(ContextArtifactRef(
                  captured_ref.digest, captured_ref.size_bytes or 0,
                  media_type=captured_ref.media_type,
                  artifact_kind="external_harness_output"))
              == '{"nested":{"parts":[1]}}')
        owned.output["nested"]["parts"].append(3)
        check("consumer_result_mutation_cannot_change_retained_adapter_result",
              retained_adapter.returned.output == {"nested": {"parts": [1, 2]}})

        class ReturnedErrorAdapter(RegisteredAdapter):
            def run(self, active_request, active_services):
                result = super().run(active_request, active_services)
                result.status = "failed"
                result.error = "SYNTHETIC_PRIVATE_ERROR_FIXTURE"
                result.error_code = "SYNTHETIC_PRIVATE_CODE_FIXTURE"
                return result

        from ..loop.recursive_loop import LoopLedger
        error_ledger = LoopLedger()
        returned_error = run_external_harness(
            ReturnedErrorAdapter(), custom_request, services=services,
            ledger=error_ledger)
        check("returned_adapter_error_and_code_are_redacted_in_actual_result_and_history",
              returned_error.status == "failed"
              and returned_error.error_code == "adapter_reported_failure"
              and "SYNTHETIC_PRIVATE" not in returned_error.error
              and "SYNTHETIC_PRIVATE" not in str(returned_error.safe_summary())
              and "SYNTHETIC_PRIVATE" not in str(error_ledger.events))
        check("adapter_exception_retains_unknown_call_and_token_accounting",
              not exception_result.call_count_complete
              and exception_result.physical_model_calls is None
              and exception_result.total_tokens is None
              and exception_result.total_cost is None)

        class MutatedAccountingAdapter(RegisteredAdapter):
            def run(self, active_request, active_services):
                result = super().run(active_request, active_services)
                result.reported_model_call_count = -1
                return result

        malformed_adapter = MutatedAccountingAdapter()
        malformed_result = run_external_harness(
            malformed_adapter, custom_request, services=services)
        check("postconstruction_invalid_accounting_is_revalidated_before_acceptance",
              malformed_adapter.calls == 1 and not malformed_result.completed
              and malformed_result.physical_model_calls is None
              and not malformed_result.call_count_complete)

    check("adapter_availability_requires_a_literal_boolean",
          all(rejects(lambda value=value: HarnessAdapterInfo(
              "host_supplied_solver", "1.0.0", "not-imported", available=value))
              for value in ("false", 0, 1, None)))
    features, limitations = ["typed_request"], ["local fixture only"]
    info_snapshot = HarnessAdapterInfo(
        "host_supplied_solver", "1.0.0", "not-imported", available=True,
        features=features, limitations=limitations)
    features.append("unqualified_feature")
    limitations.clear()
    check("adapter_description_sequences_are_detached_from_caller_aliases",
          info_snapshot.features == ("typed_request",)
          and info_snapshot.limitations == ("local fixture only",))

    from .external_harness_adapters import ConfiguredHarnessAdapter
    sdk_dispatches = []

    def unexpected_sdk_runner(active_request, active_services):
        sdk_dispatches.append(active_request.harness_id)
        return {"output": "unexpected local fixture"}

    sdk_refusals = []
    for harness_id in ("pydantic_ai", "deep_agents", "openai_agents",
                       "microsoft_agent_framework"):
        sdk_adapter = ConfiguredHarnessAdapter(harness_id, runner=unexpected_sdk_runner)
        sdk_result = sdk_adapter.run(replace(
            custom_request, harness_id=harness_id,
            contract=replace(contract, effects=("reads_secret",))), HarnessServices())
        sdk_refusals.append(
            sdk_result.status == "refused"
            and sdk_result.capability_evaluation["execution_started"] is False
            and "feature:secret_access" in sdk_result.capability_evaluation["missing"])
    check("secret_access_is_refused_before_all_four_direct_sdk_runner_boundaries",
          all(sdk_refusals) and not sdk_dispatches)

    original = {"nested": {"values": [1, {"name": "original"}]}}
    metadata = {"source": {"revision": "one"}}
    snap = replace(custom_request, input_data=original, metadata=metadata)
    snap_digest = snap.digest
    original["nested"]["values"][1]["name"] = "changed"
    metadata["source"]["revision"] = "two"
    exposed = plain_harness_json(snap.input_data)
    exposed["nested"]["values"].append(99)
    check("nested_request_and_metadata_are_detached_and_digest_stable",
          snap.digest == snap_digest
          and plain_harness_json(snap.input_data) == {"nested": {"values": [1, {"name": "original"}]}}
          and snap.metadata["source"]["revision"] == "one")
    check("nested_request_cannot_be_mutated_in_place",
          rejects(lambda: setitem(snap.input_data["nested"], "other", 1)))
    check("identity_binds_full_contract_visibility_and_requirements",
          len({custom_request.digest,
               replace(custom_request, contract=replace(contract, output_roles=("other/v1",))).digest,
               replace(custom_request, contract=replace(contract, effects=("writes_fs",))).digest,
               replace(custom_request, context_visibility="fresh").digest,
               replace(custom_request, execution_requirements=HarnessExecutionRequirements(
                   required_features=("context_refs",))).digest}) == 5)
    cycle = []
    cycle.append(cycle)

    class Opaque:
        def __str__(self):
            raise AssertionError("opaque conversion hook must not run")

    for index, value in enumerate((object(), Opaque(), cycle, float("nan"), float("inf"), {1: "bad"})):
        check(f"non_plain_input_{index}_is_refused",
              rejects(lambda value=value: replace(custom_request, input_data={"value": value})))
    check("nested_credential_metadata_is_refused",
          rejects(lambda: replace(custom_request, metadata={"deep": [{"api_key": "fixture"}]})))
    check("authority_requires_boolean_true_and_refs_are_sequences",
          rejects(lambda: replace(custom_request, authorize_model_calls="false"))
          and rejects(lambda: replace(custom_request, tool_refs="tool:one")))
    from .external_harness_adapters import _prompt
    large_input = {"nested": {"body": "a" * 60_000 + "END_MARKER"}}
    prompt = _prompt(replace(custom_request, input_data=large_input))
    check("sdk_prompt_preserves_nested_json_without_silent_truncation",
          '"nested": {"body": "' in prompt and "END_MARKER" in prompt
          and "mappingproxy" not in prompt)
    check("negative_nonfinite_and_boolean_usage_are_refused",
          all(rejects(lambda value=value: HarnessModelCall(
              "provider", "model", True, input_tokens=value))
              for value in (-1, True, 1.5, float("nan")))
          and all(rejects(lambda value=value: HarnessBudget(1, max_cost=value))
                  for value in (-1, True, float("inf"), float("nan"))))
    check("post_run_budget_assessment_does_not_claim_preemptive_enforcement",
          "post_run_acceptance" in custom_result.safe_summary()["budget_assessment"])

    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
