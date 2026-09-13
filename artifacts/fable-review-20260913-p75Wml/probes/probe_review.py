"""Offline review probes for the 2026-09-13 handoff. No provider is called.

Run from the repository root:
  PYTHONPATH=src .venv/bin/python .loop-engine-dev/fable-review-probe-20260913/probe_review.py
Every probe prints OBSERVED lines; nothing here mutates tracked repository files.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import replace


def section(title):
    print("\n=== " + title + " ===", flush=True)


def observed(label, value):
    print("OBSERVED " + label + ": " + repr(value), flush=True)


# --------------------------------------------------------------------------
section("A. SpawnedTaskCheckpoint reader accepts a tampered record when the digest is blank")
try:
    from loop_engine.loop.delegation_checkpoint_checks import _terminal_checkpoint_case
    from loop_engine.loop.spawned_task_checkpoint import SpawnedTaskCheckpoint, SpawnedTaskCheckpointError
    cp = _terminal_checkpoint_case()["checkpoint"]
    good = cp.to_dict()
    tampered = json.loads(json.dumps(good))
    tampered["spec"]["goal"] = "tampered goal written after the fact"
    tampered["checkpoint_digest"] = ""
    try:
        loaded = SpawnedTaskCheckpoint.from_dict(tampered)
        observed("tampered_record_with_blank_digest_loaded", True)
        observed("loaded_goal", loaded.spec.goal)
        observed("reader_assigned_fresh_digest", loaded.checkpoint_digest[:16] + "...")
    except (SpawnedTaskCheckpointError, ValueError) as exc:
        observed("tampered_record_with_blank_digest_loaded", False)
        observed("refusal", str(exc)[:160])
    control = json.loads(json.dumps(good))
    control["spec"]["goal"] = "tampered goal written after the fact"
    try:
        SpawnedTaskCheckpoint.from_dict(control)
        observed("control_tampered_record_with_original_digest_loaded", True)
    except (SpawnedTaskCheckpointError, ValueError):
        observed("control_tampered_record_with_original_digest_loaded", False)
    missing = json.loads(json.dumps(good))
    missing.pop("checkpoint_digest")
    try:
        SpawnedTaskCheckpoint.from_dict(missing)
        observed("record_without_digest_key_loaded", True)
    except (SpawnedTaskCheckpointError, ValueError, KeyError):
        observed("record_without_digest_key_loaded", False)
except Exception:
    traceback.print_exc()

# --------------------------------------------------------------------------
section("B. Duplicate Run History references satisfy minimum_records in harness selection")
try:
    from loop_engine.core.harness_selection_checks import _scope, _reviewed
    from loop_engine.core.harness_selection_records import (
        HarnessSelectionPolicy, HarnessEvidenceReview, ReviewedHarnessEvidence, content_digest)
    from loop_engine.core.harness_selection import select_harness
    from loop_engine.core.external_harness import HarnessAdapterInfo
    from loop_engine.core.harness_execution_contracts import HarnessExecutionCapabilities
    scope = _scope()
    infos = tuple(HarnessAdapterInfo(n, "1.0.0", "fx", available=True,
        execution_capabilities=HarnessExecutionCapabilities(supported_features=("model_routes",)))
        for n in ("first", "second"))
    first_real = _reviewed("first", scope, 4, 5)
    second_a = _reviewed("second", scope, 3, 5, suffix="-a")
    second_b = _reviewed("second", scope, 3, 5, suffix="-b")
    copy_trial = replace(first_real.trial, trial_id="fixture-trial-first-copy")
    copy_review = HarnessEvidenceReview(copy_trial.digest, "independent-fixture-reviewer",
        "fixture-review:first-copy", content_digest(copy_trial.to_dict()))
    first_copy = ReviewedHarnessEvidence(copy_trial, copy_review)
    observed("copy_shares_history_ref", copy_trial.history_ref == first_real.trial.history_ref)
    observed("copy_shares_history_digest", copy_trial.history_digest == first_real.trial.history_digest)
    honest = HarnessSelectionPolicy(scope.resource_profile_digest, (first_real, second_a, second_b), 2)
    inflated = HarnessSelectionPolicy(scope.resource_profile_digest, (first_real, first_copy, second_a, second_b), 2)
    d_honest = select_harness(honest, scope, infos, provider_id="fixture", model_id="fixture-model")
    d_inflated = select_harness(inflated, scope, infos, provider_id="fixture", model_id="fixture-model")
    observed("honest_reason", d_honest.reason)
    observed("honest_order", d_honest.ordered_harness_ids)
    observed("inflated_reason", d_inflated.reason)
    observed("inflated_order", d_inflated.ordered_harness_ids)
    observed("inflated_first_matching_records", json.loads(d_inflated.assessments_json)[0].get("matching_reviewed_records"))
    observed("inflated_evidence_refs", d_inflated.evidence_refs)
    import inspect
    observed("selector_source_mentions_subject_digest", "subject_digest" in inspect.getsource(select_harness))
except Exception:
    traceback.print_exc()

# --------------------------------------------------------------------------
section("C. Response evaluator sees only text; its Run History record omits the subject contract")
try:
    from loop_engine.core.harness_response_evaluation import (
        HarnessResponseEvaluator, ResponseEvaluationVerdict, evaluate_response_as_loop)
    from loop_engine.loop.recursive_loop import Loop
    ev = HarnessResponseEvaluator(contract_ref="fixture.arithmetic/v1", implementation_digest="a"*64,
        qualification_ref="fixture-controls", qualification_digest="b"*64,
        subject_contract_ref="fixture.answer/v1", subject_contract_digest="c"*64,
        evaluate=lambda text: ResponseEvaluationVerdict("passed") if json.loads(text)["answer"] == 42
        else ResponseEvaluationVerdict("rejected", ("answer_incorrect",)))
    owner = Loop("evaluator subject probe")
    r1 = evaluate_response_as_loop(ev, '{"answer":42}', semantic_call_id="call-1", input_digest="d"*64, parent=owner)
    r2 = evaluate_response_as_loop(ev, '{"answer":42}', semantic_call_id="call-2", input_digest="e"*64, parent=owner)
    observed("verdict_for_prompt_A", r1.status)
    observed("verdict_for_prompt_B_same_text", r2.status)
    keys = sorted(r1.to_dict().keys())
    observed("evaluation_record_keys", keys)
    observed("record_carries_subject_contract_ref", "subject_contract_ref" in keys)
    observed("record_carries_subject_contract_digest", "subject_contract_digest" in keys)
    import inspect
    observed("evaluate_callback_parameters", list(inspect.signature(ev.evaluate).parameters))
except Exception:
    traceback.print_exc()

# --------------------------------------------------------------------------
section("D. verifier_execute: timeout kills bash only; descendants survive; capture is unbounded")
try:
    from loop_engine.core.verifier_execute import verifier_execute_operation, VerifierError, MAX_OUTPUT_BYTES
    import inspect
    src = inspect.getsource(verifier_execute_operation)
    observed("MAX_OUTPUT_BYTES_constant", MAX_OUTPUT_BYTES)
    observed("MAX_OUTPUT_BYTES_used_in_operation", "MAX_OUTPUT_BYTES" in src)
    observed("start_new_session_or_killpg_used", ("start_new_session" in src) or ("killpg" in src))
    folder = tempfile.mkdtemp(prefix="verifier-descendant-probe-")
    marker = os.path.join(folder, "descendant-wrote-this")
    script = os.path.join(folder, "gate.sh")
    # A unique sleep duration identifies this probe's own descendants; nothing
    # else on a shared machine is matched or killed (corrected after review).
    token = "31.7331"
    with open(script, "w") as handle:
        handle.write("#!/bin/bash\n(sleep 3; touch '%s') &\nsleep %s\n" % (marker, token))

    class _Services:
        class request:
            verifier_path = script

    started = time.monotonic()
    try:
        verifier_execute_operation({"timeout_seconds": 1}, _Services)
        observed("timeout_raised", False)
    except VerifierError as exc:
        observed("timeout_raised", True)
        observed("timeout_message", str(exc))
        observed("partial_output_attached_to_error", hasattr(exc, "output_tail"))
    observed("elapsed_seconds_for_1s_timeout", round(time.monotonic() - started, 2))
    time.sleep(4)
    observed("descendant_survived_and_wrote_marker", os.path.exists(marker))
    survivors = subprocess.run(["pgrep", "-f", "^sleep " + token + "$"], capture_output=True, text=True).stdout.split()
    observed("probe_sleep_processes_still_alive", len(survivors))
    for pid in survivors:
        subprocess.run(["kill", pid])
except Exception:
    traceback.print_exc()

# --------------------------------------------------------------------------
section("E. Direct gateway path: a semantic rejection triggers cross-route failover without SEMANTIC_REJECTED permission")
try:
    from loop_engine.code_nodes.solution_model_port import (
        ModelExecution, ModelInvocationRequest, SolutionModelError)
    from loop_engine.core.harness_response_evaluation import HarnessResponseEvaluator, ResponseEvaluationVerdict
    from loop_engine.core.harness_selection_records import response_contract_digest
    from loop_engine.core.model_capabilities import ModelOutputCapability
    from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig, ProviderSpec
    from loop_engine.core.model_routes import ModelRoute, RoutePolicy
    from loop_engine.core.ollama_client import ChatResult
    from loop_engine.core.observation_expectations import ObservationExpectation
    from loop_engine.loop.recursive_loop import Loop

    def adapter(name, answer):
        class Adapter:
            DEFAULT_MODEL = name + "-model"
            calls = []
            @staticmethod
            def output_capability_for(model=""):
                return ModelOutputCapability(64, "offline fixture contract")
            @staticmethod
            def chat_maxout(prompt, **kwargs):
                Adapter.calls.append(prompt[:40])
                return ChatResult(answer, name + "-model", prompt_tokens=2, eval_tokens=3, ok=True)
            @staticmethod
            def verify(model=""):
                return {"ok": True}
            @staticmethod
            def live_models():
                return [name + "-model"]
        return Adapter
    a, b = adapter("alpha", '{"answer":41}'), adapter("beta", '{"answer":42}')
    gateway = ModelGateway(
        providers=(ProviderSpec("alpha", a, "offline_fixture", "not_required", locality="local"),
                   ProviderSpec("beta", b, "offline_fixture", "not_required", locality="local")),
        routes=(ModelRoute("fx.alpha", "alpha", "alpha-model", "local", purposes=("counted_generation",)),
                ModelRoute("fx.beta", "beta", "beta-model", "local", purposes=("counted_generation",))),
        policy=RoutePolicy(allow_local_counted_generation=True))
    observed("ModelGatewayConfig_default_allow_failover", ModelGatewayConfig().allow_failover)
    config = ModelGatewayConfig(route_names=("fx.alpha", "fx.beta"), allowed_localities=("local",))
    base = ModelInvocationRequest("Compute the requested value.", semantic_call_id="direct-eval-1")
    expected = ObservationExpectation("exp", base.semantic_call_id, base.exact_input_digest,
        "fixture.answer/v1", '{"type":"object","properties":{"answer":{"type":"integer"}},"required":["answer"]}')
    evaluator = HarnessResponseEvaluator(contract_ref="fixture.arithmetic/v1", implementation_digest="a"*64,
        qualification_ref="fixture-controls", qualification_digest="b"*64,
        subject_contract_ref="fixture.answer/v1",
        subject_contract_digest=response_contract_digest(expected, None),
        evaluate=lambda text: ResponseEvaluationVerdict("passed") if json.loads(text)["answer"] == 42
        else ResponseEvaluationVerdict("rejected", ("answer_incorrect",)))
    authority = ModelExecution(gateway, config, max_model_calls=4, response_evaluators=(evaluator,))
    session = authority.start_session()
    owner = Loop("direct gateway semantic rejection probe")
    request = replace(base, response_expectation=expected, response_evaluation_ref="fixture.arithmetic/v1")
    try:
        text = session.invoke(request, owner)
        observed("invoke_returned_text", text)
    except SolutionModelError as exc:
        observed("invoke_refused", exc.error_code)
    result = session.results[-1]
    observed("physical_attempts_providers", [x.provider for x in result.physical_provider_attempts])
    observed("attempt_error_codes", [x.error_code for x in result.attempts])
    observed("evaluation_statuses", [e.status for e in result.response_evaluations])
    observed("result_ok", result.ok)
    observed("calls_used", session.calls_used)
    events = [e.get("action") for e in owner.ledger.events if e.get("action")]
    observed("harness_attempt_assessed_events", events.count("harness_attempt_assessed"))
    observed("actions_recorded", sorted(set(events)))
except Exception:
    traceback.print_exc()

# --------------------------------------------------------------------------
section("F. Historical encodings: strict refusals (controls for question 4)")
try:
    import hashlib
    from loop_engine.loop.loop_definition import LoopDefinition, LoopDefinitionError
    from loop_engine.loop.loop_definition_checks import _definition
    definition = _definition()
    def redigest(value):
        body = {k: v for k, v in value.items() if k != "content_digest"}
        value["content_digest"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        return value
    cases = {}
    v1_with_cardinality = definition.to_dict(); v1_with_cardinality["record_type"] = "loop_definition/v1"
    cases["v1_carrying_input_cardinalities"] = redigest(v1_with_cardinality)
    v3 = definition.to_dict(); v3["record_type"] = "loop_definition/v3"
    cases["unsupported_v3"] = redigest(v3)
    undeclared = definition.to_dict()
    undeclared["contract"]["input_cardinalities"] = [{"role": "absent", "cardinality": "multiple", "max_items": 2}]
    cases["v2_cardinality_on_undeclared_role"] = redigest(undeclared)
    boolean = definition.to_dict()
    boolean["contract"]["input_cardinalities"] = [{"role": "request", "cardinality": "multiple", "max_items": True}]
    cases["v2_boolean_max_items"] = redigest(boolean)
    unsorted = definition.to_dict()
    unsorted["contract"]["input_roles"] = ["request", "aux"]
    unsorted["contract"]["input_cardinalities"] = [
        {"role": "request", "cardinality": "multiple", "max_items": 2},
        {"role": "aux", "cardinality": "multiple", "max_items": 2}]
    cases["v2_unsorted_cardinalities_valid_digest"] = redigest(unsorted)
    for name, value in cases.items():
        try:
            LoopDefinition.from_dict(value)
            observed(name, "LOADED")
        except LoopDefinitionError as exc:
            observed(name, "refused: " + str(exc)[:90])
    from loop_engine.loop.spawned_task_checkpoint import SpawnedTaskCheckpoint, SpawnedTaskCheckpointError
    from loop_engine.loop.delegation_checkpoint_checks import _terminal_checkpoint_case
    cp = _terminal_checkpoint_case()["checkpoint"]
    v2 = cp.to_dict(); v2["schema_version"] = "spawned_task_checkpoint/v2"
    v2["spec"]["contract"]["output_type"] = "multiple"; v2["spec"]["contract"]["max_outputs"] = 2
    v2.pop("checkpoint_digest")
    v2["checkpoint_digest"] = hashlib.sha256(json.dumps(v2, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    try:
        SpawnedTaskCheckpoint.from_dict(v2); observed("checkpoint_v2_with_multiple_output", "LOADED")
    except (SpawnedTaskCheckpointError, ValueError) as exc:
        observed("checkpoint_v2_with_multiple_output", "refused: " + str(exc)[:90])
    v1 = cp.to_dict(); v1["schema_version"] = "spawned_task_checkpoint/v1"
    try:
        SpawnedTaskCheckpoint.from_dict(v1); observed("checkpoint_v1", "LOADED")
    except (SpawnedTaskCheckpointError, ValueError) as exc:
        observed("checkpoint_v1", "refused: " + str(exc)[:90])
except Exception:
    traceback.print_exc()

# --------------------------------------------------------------------------
section("G. Harness selection scope is derived only when a response expectation is bound")
try:
    from loop_engine.core.harness_selection_checks import _fixture_runtime, _reviewed, _scope
    from loop_engine.core.harness_selection_records import HarnessSelectionPolicy
    from loop_engine.core.harness_fallback import HarnessFailureKind
    from loop_engine.code_nodes.solution_model_port import ModelInvocationRequest
    with tempfile.TemporaryDirectory(prefix="selection-scope-probe-") as directory:
        scope = _scope()
        adapters, authority, manager, owner = _fixture_runtime(directory, ('{"answer":42}',),
            switch_on=tuple(HarnessFailureKind))
        route = authority.gateway._routes(authority.config)[0][0]
        evidence = tuple(_reviewed(n, scope, q, t, provider=route.provider, model=route.model)
                         for n, q, t in (("first", 1, 2), ("second", 4, 10)))
        binding = replace(authority.harness, selection_policy=HarnessSelectionPolicy(scope.resource_profile_digest, evidence, 1))
        session = replace(authority, harness=binding).start_session(artifact_store=manager)
        session.invoke(ModelInvocationRequest("Compute the requested value without changing authority."), owner)
        actions = [e.get("action") for e in owner.ledger.events if e.get("action")]
        observed("harness_selection_unavailable_recorded", "harness_selection_unavailable" in actions)
        observed("harness_selection_assessed_recorded", "harness_selection_assessed" in actions)
        observed("harness_used", "first" if adapters[0].requests else "second")
except Exception:
    traceback.print_exc()

# --------------------------------------------------------------------------
section("H. Harness path: gateway failover inside one harness attempt bypasses a policy that forbids semantic recovery")
try:
    from pathlib import Path
    from loop_engine.code_nodes.solution_model_port import ModelExecution, ModelInvocationRequest, SolutionModelError
    from loop_engine.core.external_harness import HarnessAdapterInfo, HarnessModelCall, HarnessRegistry, HarnessRunResult
    from loop_engine.core.harness_execution_contracts import HarnessExecutionCapabilities
    from loop_engine.core.harness_semantic import HarnessSemanticBinding
    from loop_engine.core.harness_fallback import HarnessFallbackPolicy
    from loop_engine.core.harness_response_evaluation import HarnessResponseEvaluator, ResponseEvaluationVerdict
    from loop_engine.core.harness_selection_records import response_contract_digest
    from loop_engine.core.context_artifacts import (
        ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
    from loop_engine.core.model_capabilities import ModelOutputCapability
    from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig, ProviderSpec
    from loop_engine.core.model_routes import ModelRoute, RoutePolicy
    from loop_engine.core.ollama_client import ChatResult
    from loop_engine.core.observation_expectations import ObservationExpectation
    from loop_engine.loop.recursive_loop import Loop

    def adapter(name, answer):
        class Adapter:
            DEFAULT_MODEL = name + "-model"
            @staticmethod
            def output_capability_for(model=""):
                return ModelOutputCapability(64, "offline fixture contract")
            @staticmethod
            def chat_maxout(prompt, **kwargs):
                return ChatResult(answer, name + "-model", prompt_tokens=2, eval_tokens=3, ok=True)
            @staticmethod
            def verify(model=""):
                return {"ok": True}
            @staticmethod
            def live_models():
                return [name + "-model"]
        return Adapter

    class FixtureHarness:
        def __init__(self, name):
            self.name = name; self.requests = []
        def info(self):
            return HarnessAdapterInfo(self.name, "1.0.0", "explicit-offline-fixture", available=True,
                execution_capabilities=HarnessExecutionCapabilities(supported_features=("model_routes",)))
        def run(self, request, services):
            self.requests.append(request); client = services.runtime_binding.runtime_object; output = None
            try:
                output = client({"model": request.model_id, "messages": [{"role": "user", "content": request.input_data["prompt"]}]})["choices"][0]["message"]["content"]
            except ValueError:
                pass
            calls = tuple(HarnessModelCall(a.provider, a.model, a.provider_ok, input_tokens=a.input_tokens,
                output_tokens=a.output_tokens, error_code=a.error_code, gateway_loop_id=a.loop_id, route_id=a.route)
                for r in client.results for a in r.physical_provider_attempts)
            return HarnessRunResult(request.request_id, self.name, "completed" if output else "failed",
                output=output, error_code="" if output else "adapter_reported_failure", model_calls=calls,
                adapter_version="1.0.0", provider_id=request.provider_id, model_id=request.model_id)

    gateway = ModelGateway(
        providers=(ProviderSpec("alpha", adapter("alpha", '{"answer":41}'), "offline_fixture", "not_required", locality="local"),
                   ProviderSpec("beta", adapter("beta", '{"answer":42}'), "offline_fixture", "not_required", locality="local")),
        routes=(ModelRoute("fx.alpha", "alpha", "alpha-model", "local", purposes=("counted_generation",)),
                ModelRoute("fx.beta", "beta", "beta-model", "local", purposes=("counted_generation",))),
        policy=RoutePolicy(allow_local_counted_generation=True))
    config = ModelGatewayConfig(route_names=("fx.alpha", "fx.beta"), allowed_localities=("local",))
    base = ModelInvocationRequest("Compute the requested value.", semantic_call_id="harness-eval-1")
    expected = ObservationExpectation("exp-h", base.semantic_call_id, base.exact_input_digest,
        "fixture.answer/v1", '{"type":"object","properties":{"answer":{"type":"integer"}},"required":["answer"]}')
    evaluator = HarnessResponseEvaluator(contract_ref="fixture.arithmetic/v1", implementation_digest="a"*64,
        qualification_ref="fixture-controls", qualification_digest="b"*64,
        subject_contract_ref="fixture.answer/v1", subject_contract_digest=response_contract_digest(expected, None),
        evaluate=lambda text: ResponseEvaluationVerdict("passed") if json.loads(text)["answer"] == 42
        else ResponseEvaluationVerdict("rejected", ("answer_incorrect",)))
    with tempfile.TemporaryDirectory(prefix="harness-path-probe-") as directory:
        manager = ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(ContextArtifactStoreSpec(directory))))
        adapters = (FixtureHarness("first"), FixtureHarness("second"))
        # The policy permits NO recovery of any kind: switch_on is empty.
        binding = HarnessSemanticBinding("first", HarnessRegistry(adapters), str(Path(directory) / "work"),
            artifact_store=manager, fallback_policy=HarnessFallbackPolicy(("first", "second"), ()))
        authority = ModelExecution(gateway, config, max_model_calls=4, response_evaluators=(evaluator,), harness=binding)
        session = authority.start_session(artifact_store=manager)
        owner = Loop("harness path semantic rejection probe")
        request = replace(base, response_expectation=expected, response_evaluation_ref="fixture.arithmetic/v1")
        try:
            observed("invoke_returned_text", session.invoke(request, owner))
        except SolutionModelError as exc:
            observed("invoke_refused", exc.error_code)
        result = session.results[-1]
        observed("policy_switch_on", ())
        observed("physical_attempts_providers", [x.provider for x in result.physical_provider_attempts])
        observed("evaluation_statuses", [e.status for e in result.response_evaluations])
        observed("harness_attempt_decisions", [e.get("decision") for e in owner.ledger.events if e.get("action") == "harness_attempt_assessed"])
        observed("second_harness_requests", len(adapters[1].requests))
        observed("first_harness_requests", len(adapters[0].requests))
        observed("result_ok", result.ok)
        observed("calls_used", session.calls_used)
except Exception:
    traceback.print_exc()

print("\nprobe finished", flush=True)
