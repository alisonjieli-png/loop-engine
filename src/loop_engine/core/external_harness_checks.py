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
    HarnessModelCall, HarnessModelIdentity, HarnessRegistry, HarnessRunRequest, HarnessRunResult, HarnessServices,
    ModelOutputLimit, StaticModelOutputResolver, _budget_failure,
    resolve_harness_output_limit, run_external_harness,
)
from .harness_execution_contracts import (
    HarnessExecutionCapabilities, HarnessExecutionRequirements,
    harness_loop_identity, plain_harness_json,
)


from pathlib import Path


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
          request.digest == request.digest and len(request.digest) == 64
          and request.outcome_vector_policy
          .continue_while_safe_authorized_work_remains)

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
    check("every_external_harness_result_has_an_owning_loop_outcome_vector",
          failed_once.outcome_vector.execution_succeeded is False
          and small.outcome_vector.execution_succeeded is True
          and small.outcome_vector.output_admitted is None
          and small.outcome_vector.expected_output_satisfied is None
          and small.safe_summary()["outcome_vector"]["task_outcome"] is None)
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

    class NamedPractitionerAdapter(RegisteredAdapter):
        def __init__(self, harness_id):
            super().__init__()
            self.harness_id = harness_id

        def info(self):
            return HarnessAdapterInfo(
                self.harness_id, self.version, "not-imported", available=True,
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
              and custom_result.safe_summary()["acceptance"] == "not_evaluated"
              and custom_result.capability_evaluation[
                  "outcome_vector_policy"]["adapter_may_self_accept"] is False)
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
        portable_vectors = []
        for harness_id in ("custom_practitioner", "opencode", "codex", "pi"):
            adapter = NamedPractitionerAdapter(harness_id)
            portable = run_external_harness(
                adapter, replace(custom_request, request_id="portable-" + harness_id,
                                 harness_id=harness_id), services=services)
            portable_vectors.append(
                portable.completed
                and portable.outcome_vector.execution_succeeded is True
                and portable.outcome_vector.expected_output_satisfied is None
                and portable.outcome_vector.task_outcome is None)
        check("custom_opencode_codex_and_pi_share_the_outcome_vector_boundary",
              all(portable_vectors))

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

        class SelfGradingAdapter(RegisteredAdapter):
            def run(self, active_request, active_services):
                from .outcome_vector import OutcomeVector
                result = super().run(active_request, active_services)
                result.outcome_vector = OutcomeVector(
                    expected_output_satisfied=True, task_outcome=True)
                return result

        for variant in (WrongModelAdapter, WrongVersionAdapter):
            check(f"{variant.__name__}_cannot_return_completion",
                  rejects(lambda variant=variant: run_external_harness(
                      variant(), custom_request, services=services)))
        check("harness_adapter_cannot_self_grade_or_self_accept_its_vector",
              rejects(lambda: run_external_harness(
                  SelfGradingAdapter(), custom_request, services=services)))
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
        check("adapter_exception_names_type_in_memory_and_summary",
              exception_result.underlying_error.startswith("RuntimeError: ")
              and exception_result.safe_summary()["underlying_error_type"]
              == "RuntimeError"
              and "SECRET_FIXTURE_NOT_FOR_HISTORY"
              not in str(exception_result.safe_summary()))

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
          and rejects(lambda: replace(custom_request, tool_refs="tool:one"))
          and rejects(lambda: replace(
              custom_request, outcome_vector_policy={})))
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

    _gateway_binding_checks(check, rejects)

    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


def _gateway_binding_checks(check, rejects):
    """Exercise optional authority, allocations and actual gateway event reuse."""
    import tempfile
    from unittest.mock import patch

    from ..code_nodes.solution_model_port import fixture_model_execution
    from ..loop.recursive_loop import Loop, LoopConfig
    from .context_artifacts import (
        ContextArtifactManager,
        ContextArtifactStore,
        ContextArtifactStoreSpec,
    )
    from .instance_instructions_checks import instruction_file_checks
    from .model_capabilities import ModelOutputAllocation, ModelOutputCapability
    from .model_gateway import ModelGatewayRequest
    from .ollama_client import ChatResult

    limit = ModelOutputLimit(64, "custom_endpoint_declared", "offline fixture contract",
                             provider_id="fixture", model_id="fixture-model", route_id="fixture.route")
    allocation = ModelOutputAllocation(
        ModelOutputCapability(64, "offline fixture contract"), "fixture", "fixture-model",
        "fixture.route", 16, "fixture:allocation", "Explicit fixture response allocation")
    budget = HarnessBudget(None, output_limit=limit)
    contract = LoopContract("gateway broker", "model_led", ("prompt/v1",), ("answer/v1",), ("pure",))
    request = HarnessRunRequest(
        "gateway-broker", "host_gateway", "Answer the exact semantic request", contract, budget,
        provider_id="fixture", model_id="fixture-model", model_routes=("fixture.route",),
        authorize_model_calls=True)
    check("unbounded_calls_are_explicit_and_invalid_finite_limits_still_refuse",
          budget.max_model_calls is None and all(rejects(lambda value=value: HarnessBudget(value))
              for value in (0, -1, False, 1.5, "unbounded")))
    allocated = replace(request, budget=replace(budget, output_allocation=allocation))
    check("allocation_keeps_capacity_and_selected_allowance_separate",
          allocated.budget.max_output_tokens == 64 and allocated.budget.requested_output_tokens == 16
          and request.budget.requested_output_tokens == 64 and allocated.digest != request.digest)
    check("allocation_refuses_wrong_provider_model_route_and_capacity",
          all(rejects(lambda change=change: replace(request, budget=replace(
              budget, output_allocation=replace(allocation, **change)))) for change in (
                  {"provider_id": "other"}, {"model_id": "other"}, {"route_name": "other"},
                  {"capability": ModelOutputCapability(128, "other capacity")}))
          and rejects(lambda: replace(budget, output_allocation={"requested_tokens": 16})))
    unresolved = replace(allocated, budget=replace(allocated.budget, output_limit=None))
    resolved = resolve_harness_output_limit(unresolved, HarnessServices(
        model_output_resolver=StaticModelOutputResolver((limit,))))
    check("late_capacity_resolution_preserves_and_checks_the_allocation",
          resolved.budget.requested_output_tokens == 16 and rejects(lambda:
              resolve_harness_output_limit(unresolved, HarnessServices(model_output_resolver=
                  StaticModelOutputResolver((replace(limit, max_output_tokens=128),))))))
    unknown = HarnessRunResult(request.request_id, request.harness_id, "completed",
                               call_count_complete=False)
    check("unbounded_call_authority_preserves_unknown_counts_without_a_fake_zero",
          _budget_failure(request, unknown) is None and unknown.physical_model_calls is None
          and _budget_failure(replace(request, budget=replace(budget, max_model_calls=1)), unknown)
          == "model_call_accounting_incomplete"
          and _budget_failure(replace(request, budget=replace(budget, max_total_tokens=100)), unknown)
          == "token_accounting_incomplete"
          and _budget_failure(replace(request, budget=replace(budget, max_cost=1)), unknown)
          == "cost_accounting_incomplete")
    primary = HarnessModelIdentity("fixture", "fixture-model", "fixture.route")
    fallback = HarnessModelIdentity("second", "second-model", "second.route")
    multi = replace(request, model_routes=("fixture.route", "second.route"),
                    authorized_model_identities=(primary, fallback))
    check("authorized_model_identities_are_typed_unique_and_bind_requested_routes",
          multi.digest != request.digest
          and rejects(lambda: replace(request, authorized_model_identities=(fallback,)))
          and rejects(lambda: replace(multi, authorized_model_identities=(primary, primary)))
          and rejects(lambda: replace(multi, authorized_model_identities=({"provider_id": "fixture"},)))
          and rejects(lambda: HarnessModelIdentity("fixture", "model", "bad route")))
    check("capacity_and_allocation_cannot_rebind_a_route_to_another_authorized_model",
          rejects(lambda: resolve_harness_output_limit(replace(multi, budget=replace(
              budget, output_limit=replace(limit, route_id="second.route")))))
          and rejects(lambda: replace(multi, budget=replace(budget, output_limit=None,
              output_allocation=replace(allocation, route_name="second.route")))))

    authority = fixture_model_execution()
    parent = Loop("gateway broker owner", LoopConfig(max_depth=None))

    class BrokerAdapter:
        def __init__(self, change=None, remembered=None, call_parent=None, duplicate=False):
            self.change, self.remembered = change, remembered
            self.call_parent, self.duplicate = call_parent, duplicate
            self.last_call = None

        @staticmethod
        def info():
            return HarnessAdapterInfo("host_gateway", "fixture/v1", "not-imported", available=True,
                execution_capabilities=HarnessExecutionCapabilities(supported_features=("model_routes",)))

        def run(self, current, services):
            if self.remembered is None:
                result = authority.gateway.invoke(ModelGatewayRequest("fixture prompt", authority.config),
                                                  parent=self.call_parent or parent)
                attempt = result.physical_provider_attempts[0]
                event = next(row for row in parent.ledger.events
                             if row.get("loop_id") == attempt.loop_id and row.get("event") in (
                                 "model_led", "model_invocation_failed"))
                call = HarnessModelCall(attempt.provider, attempt.model, event["event"] == "model_led",
                    input_tokens=event.get("prompt_tokens"), output_tokens=event.get("eval_tokens"),
                    gateway_loop_id=attempt.loop_id, route_id=attempt.route)
            else:
                call = self.remembered
            self.last_call = call
            calls = (replace(call, **self.change),) if self.change else (call,)
            if self.duplicate:
                calls = calls * 2
            return HarnessRunResult(current.request_id, current.harness_id, "completed", output="fixture answer",
                                    model_calls=calls, adapter_version="fixture/v1")

    with tempfile.TemporaryDirectory(prefix="harness-gateway-bindings-") as root:
        services = HarnessServices(artifact_store=ContextArtifactManager(
            ContextArtifactStore(ContextArtifactStoreSpec(root))))

        def invoke(adapter, current=request):
            return run_external_harness(adapter, current, services=services, parent=parent)

        adapter = BrokerAdapter()
        start = len(parent.ledger.events)
        outcome = invoke(adapter)
        new = parent.ledger.events[start:]
        check("gateway_physical_call_is_recorded_once_in_shared_canonical_history",
              outcome.completed and outcome.physical_model_calls == 1 and outcome.total_tokens == 5
              and sum(row.get("event") == "model_led" for row in new) == 1)
        check("gateway_reference_cannot_reuse_an_earlier_harness_attempt",
              rejects(lambda: invoke(BrokerAdapter(remembered=adapter.last_call))))
        check("gateway_reference_refuses_forged_identity_status_and_usage",
              all(rejects(lambda change=change: invoke(BrokerAdapter(change))) for change in (
                  {"gateway_loop_id": "unregistered.loop"}, {"input_tokens": 999}, {"ok": False})))
        foreign = parent.spawn("separately owned gateway work", LoopConfig(max_depth=None))
        check("gateway_reference_refuses_another_owner_or_duplicate_physical_reference",
              rejects(lambda: invoke(BrokerAdapter(call_parent=foreign)))
              and rejects(lambda: invoke(BrokerAdapter(duplicate=True))))
        with patch.object(authority.gateway.providers["fixture"].adapter, "chat_maxout",
                          return_value=ChatResult("fixture answer", "fixture-model", prompt_tokens=None,
                                                  eval_tokens=None, ok=True)):
            start = len(parent.ledger.events)
            missing = invoke(BrokerAdapter())
        check("gateway_reference_preserves_unknown_usage_without_duplicate_events",
              missing.completed and missing.physical_model_calls == 1 and missing.total_tokens is None
              and sum(row.get("event") == "model_led" for row in parent.ledger.events[start:]) == 1)

        class FallbackAdapter(BrokerAdapter):
            def run(self, current, services):
                call = HarnessModelCall("second", "second-model", True, input_tokens=1, output_tokens=2,
                                        route_id="second.route")
                return HarnessRunResult(current.request_id, current.harness_id, "completed", output="fallback answer",
                    model_calls=(call,), provider_id=current.provider_id, model_id=current.model_id,
                    adapter_version="fixture/v1")

        instruction_file_checks(check, request, parent, services)

        fallback_result = invoke(FallbackAdapter(), multi)
        check("explicit_fallback_keeps_actual_calls_and_primary_result_identity",
              fallback_result.completed and fallback_result.provider_id == "fixture"
              and fallback_result.model_calls[0].provider == "second"
              and rejects(lambda: invoke(FallbackAdapter()))
              and rejects(lambda: invoke(FallbackAdapter(), replace(multi,
                  authorized_model_identities=(primary, HarnessModelIdentity("second", "other", "second.route"))))))
