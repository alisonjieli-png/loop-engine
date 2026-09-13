"""Acceptance probe for the 2026-09-13 review findings D1 to D6.

Each scenario asserts the behavior the review expects AFTER a fix. Against the
reviewed working tree every scenario prints FAIL; a candidate fix is verified
when its scenario prints PASS without any other scenario regressing.

Run from the repository root:
  PYTHONPATH=src:devtools TMPDIR=$PWD/.loop-engine-dev/fable-review-probe-20260913/tmp \
    .venv/bin/python artifacts/fable-review-20260913-p75Wml/probes/expected_after_fix.py
No provider is called.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import traceback
from dataclasses import replace
from pathlib import Path

RESULTS = []


def scenario(name):
    def wrap(fn):
        try:
            ok, detail = fn()
        except Exception as exc:  # a crash is a failure with its own detail
            ok, detail = False, "exception " + type(exc).__name__ + ": " + str(exc)[:200]
            traceback.print_exc()
        RESULTS.append((name, ok, detail))
        print(("PASS " if ok else "FAIL ") + name + " :: " + detail, flush=True)
        return fn
    return wrap


def two_route_gateway(first_answer='{"answer":41}', second_answer='{"answer":42}'):
    from loop_engine.core.model_capabilities import ModelOutputCapability
    from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig, ProviderSpec
    from loop_engine.core.model_routes import ModelRoute, RoutePolicy
    from loop_engine.core.ollama_client import ChatResult

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
    gateway = ModelGateway(
        providers=(ProviderSpec("alpha", adapter("alpha", first_answer), "offline_fixture", "not_required", locality="local"),
                   ProviderSpec("beta", adapter("beta", second_answer), "offline_fixture", "not_required", locality="local")),
        routes=(ModelRoute("fx.alpha", "alpha", "alpha-model", "local", purposes=("counted_generation",)),
                ModelRoute("fx.beta", "beta", "beta-model", "local", purposes=("counted_generation",))),
        policy=RoutePolicy(allow_local_counted_generation=True))
    config = ModelGatewayConfig(route_names=("fx.alpha", "fx.beta"), allowed_localities=("local",))
    return gateway, config


def arithmetic_evaluator(expected):
    from loop_engine.core.harness_response_evaluation import HarnessResponseEvaluator, ResponseEvaluationVerdict
    from loop_engine.core.harness_selection_records import response_contract_digest
    return HarnessResponseEvaluator(contract_ref="fixture.arithmetic/v1", implementation_digest="a" * 64,
        qualification_ref="fixture-controls", qualification_digest="b" * 64,
        subject_contract_ref="fixture.answer/v1", subject_contract_digest=response_contract_digest(expected, None),
        evaluate=lambda text: ResponseEvaluationVerdict("passed") if json.loads(text)["answer"] == 42
        else ResponseEvaluationVerdict("rejected", ("answer_incorrect",)))


def bound_request(semantic_call_id):
    from loop_engine.code_nodes.solution_model_port import ModelInvocationRequest
    from loop_engine.core.observation_expectations import ObservationExpectation
    base = ModelInvocationRequest("Compute the requested value.", semantic_call_id=semantic_call_id)
    expected = ObservationExpectation("exp-" + semantic_call_id, base.semantic_call_id, base.exact_input_digest,
        "fixture.answer/v1", '{"type":"object","properties":{"answer":{"type":"integer"}},"required":["answer"]}')
    return replace(base, response_expectation=expected, response_evaluation_ref="fixture.arithmetic/v1"), expected


@scenario("D1 direct path: a semantic rejection does not fail over to another route")
def _d1():
    from loop_engine.code_nodes.solution_model_port import ModelExecution, SolutionModelError
    from loop_engine.loop.recursive_loop import Loop
    gateway, config = two_route_gateway()
    request, expected = bound_request("accept-d1")
    session = ModelExecution(gateway, config, max_model_calls=4,
                             response_evaluators=(arithmetic_evaluator(expected),)).start_session()
    owner = Loop("acceptance d1")
    code = ""
    try:
        session.invoke(request, owner)
    except SolutionModelError as exc:
        code = exc.error_code
    result = session.results[-1]
    providers = [x.provider for x in result.physical_provider_attempts]
    ok = providers == ["alpha"] and code == "semantic_response_rejected" and session.calls_used == 1
    return ok, "providers=%r error_code=%r calls=%d" % (providers, code, session.calls_used)


@scenario("D1b direct path: an inconclusive evaluation does not fail over to another route")
def _d1b():
    from loop_engine.code_nodes.solution_model_port import ModelExecution, SolutionModelError
    from loop_engine.core.harness_response_evaluation import HarnessResponseEvaluator, ResponseEvaluationVerdict
    from loop_engine.core.harness_selection_records import response_contract_digest
    from loop_engine.loop.recursive_loop import Loop
    gateway, config = two_route_gateway()
    request, expected = bound_request("accept-d1b")
    evaluator = HarnessResponseEvaluator(contract_ref="fixture.arithmetic/v1", implementation_digest="a" * 64,
        qualification_ref="fixture-controls", qualification_digest="b" * 64,
        subject_contract_ref="fixture.answer/v1", subject_contract_digest=response_contract_digest(expected, None),
        evaluate=lambda text: ResponseEvaluationVerdict("passed") if json.loads(text)["answer"] == 42
        else ResponseEvaluationVerdict("inconclusive", ("missing_evidence",)))
    session = ModelExecution(gateway, config, max_model_calls=4, response_evaluators=(evaluator,)).start_session()
    owner = Loop("acceptance d1b")
    code = ""
    try:
        session.invoke(request, owner)
    except SolutionModelError as exc:
        code = exc.error_code
    result = session.results[-1]
    providers = [x.provider for x in result.physical_provider_attempts]
    ok = providers == ["alpha"] and code == "response_evaluation_inconclusive" and session.calls_used == 1
    return ok, "providers=%r error_code=%r calls=%d statuses=%r" % (
        providers, code, session.calls_used, [e.status for e in result.response_evaluations])


@scenario("D2 harness path: an attempt cannot change provider when the policy forbids recovery")
def _d2():
    from loop_engine.code_nodes.solution_model_port import ModelExecution, SolutionModelError
    from loop_engine.core.context_artifacts import (
        ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
    from loop_engine.core.external_harness import HarnessAdapterInfo, HarnessModelCall, HarnessRegistry, HarnessRunResult
    from loop_engine.core.harness_execution_contracts import HarnessExecutionCapabilities
    from loop_engine.core.harness_fallback import HarnessFallbackPolicy
    from loop_engine.core.harness_semantic import HarnessSemanticBinding
    from loop_engine.loop.recursive_loop import Loop

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
    gateway, config = two_route_gateway()
    request, expected = bound_request("accept-d2")
    with tempfile.TemporaryDirectory(prefix="accept-d2-") as directory:
        manager = ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(ContextArtifactStoreSpec(directory))))
        adapters = (FixtureHarness("first"), FixtureHarness("second"))
        binding = HarnessSemanticBinding("first", HarnessRegistry(adapters), str(Path(directory) / "work"),
            artifact_store=manager, fallback_policy=HarnessFallbackPolicy(("first", "second"), ()))
        session = ModelExecution(gateway, config, max_model_calls=4, response_evaluators=(arithmetic_evaluator(expected),),
                                 harness=binding).start_session(artifact_store=manager)
        owner = Loop("acceptance d2")
        code = ""
        try:
            session.invoke(request, owner)
        except SolutionModelError as exc:
            code = exc.error_code
        result = session.results[-1]
        providers = [x.provider for x in result.physical_provider_attempts]
        decisions = [e.get("decision") for e in owner.ledger.events if e.get("action") == "harness_attempt_assessed"]
        ok = (providers == ["alpha"] and session.calls_used == 1 and not adapters[1].requests
              and decisions == ["failure_not_permitted_by_policy"])
        return ok, "providers=%r decisions=%r error_code=%r calls=%d" % (providers, decisions, code, session.calls_used)


@scenario("D3 selection: duplicate Run History references cannot satisfy minimum_records")
def _d3():
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
    try:
        inflated = HarnessSelectionPolicy(scope.resource_profile_digest, (first_real, first_copy, second_a, second_b), 2)
    except ValueError as exc:
        return True, "refused at construction: " + str(exc)[:120]
    decision = select_harness(inflated, scope, infos, provider_id="fixture", model_id="fixture-model")
    ok = decision.reason == "insufficient_matched_reviewed_evidence"
    return ok, "reason=%r refs=%r" % (decision.reason, decision.evidence_refs)


@scenario("D3b selection: duplicating one successful trial cannot change which harness ranks first")
def _d3b():
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
    # first: 4/4 then 0/4 (pooled 0.5); second: 3/4 then 2/4 (pooled 0.625). Honest order: second, first.
    first_good = _reviewed("first", scope, 4, 5, suffix="-good")
    first_bad = _reviewed("first", scope, 0, 5, suffix="-bad")
    second_a = _reviewed("second", scope, 3, 5, suffix="-a")
    second_b = _reviewed("second", scope, 2, 5, suffix="-b")
    honest = HarnessSelectionPolicy(scope.resource_profile_digest, (first_good, first_bad, second_a, second_b), 2)
    honest_order = select_harness(honest, scope, infos, provider_id="fixture", model_id="fixture-model").ordered_harness_ids
    copy_trial = replace(first_good.trial, trial_id="fixture-trial-first-good-copy")
    first_copy = ReviewedHarnessEvidence(copy_trial, HarnessEvidenceReview(copy_trial.digest, "independent-fixture-reviewer",
        "fixture-review:first-good-copy", content_digest(copy_trial.to_dict())))
    try:
        inflated = HarnessSelectionPolicy(scope.resource_profile_digest,
                                          (first_good, first_copy, first_bad, second_a, second_b), 2)
    except ValueError as exc:
        return honest_order[0] == "second", "refused at construction: " + str(exc)[:120]
    inflated_order = select_harness(inflated, scope, infos, provider_id="fixture", model_id="fixture-model").ordered_harness_ids
    ok = honest_order[0] == "second" and inflated_order == honest_order
    return ok, "honest=%r inflated=%r" % (honest_order, inflated_order)


@scenario("D3 control: distinct repeated trials on the same subject still count")
def _d3_control():
    from loop_engine.core.harness_selection_checks import _scope, _reviewed
    from loop_engine.core.harness_selection_records import HarnessSelectionPolicy, HarnessTrialEvidence, HarnessEvidenceReview, ReviewedHarnessEvidence, content_digest
    from loop_engine.core.harness_selection import select_harness
    from loop_engine.core.external_harness import HarnessAdapterInfo
    from loop_engine.core.harness_execution_contracts import HarnessExecutionCapabilities
    scope = _scope()
    infos = tuple(HarnessAdapterInfo(n, "1.0.0", "fx", available=True,
        execution_capabilities=HarnessExecutionCapabilities(supported_features=("model_routes",)))
        for n in ("first", "second"))
    first_a = _reviewed("first", scope, 4, 5, suffix="-run1")
    # Same subject digest as first_a, but a distinct Run History reference: a legitimate repeat.
    repeat_trial = replace(first_a.trial, trial_id="fixture-trial-first-run2",
                           history_ref="fixture-history:first-run2", history_digest=content_digest("history:first-run2"))
    repeat = ReviewedHarnessEvidence(repeat_trial, HarnessEvidenceReview(repeat_trial.digest, "independent-fixture-reviewer",
        "fixture-review:first-run2", content_digest(repeat_trial.to_dict())))
    second_a = _reviewed("second", scope, 3, 5, suffix="-a")
    second_b = _reviewed("second", scope, 3, 5, suffix="-b")
    policy = HarnessSelectionPolicy(scope.resource_profile_digest, (first_a, repeat, second_a, second_b), 2)
    decision = select_harness(policy, scope, infos, provider_id="fixture", model_id="fixture-model")
    ok = decision.reason == "ranked_matched_reviewed_evidence" and decision.ordered_harness_ids[0] == "first"
    return ok, "reason=%r order=%r" % (decision.reason, decision.ordered_harness_ids)


@scenario("D4 checkpoint reader refuses a blank digest and non-integer counters")
def _d4():
    from loop_engine.loop.delegation_checkpoint_checks import _terminal_checkpoint_case
    from loop_engine.loop.spawned_task_checkpoint import SpawnedTaskCheckpoint, SpawnedTaskCheckpointError
    good = _terminal_checkpoint_case()["checkpoint"].to_dict()
    blank = json.loads(json.dumps(good)); blank["spec"]["goal"] = "tampered"; blank["checkpoint_digest"] = ""
    coerced = json.loads(json.dumps(good)); coerced["update_count"] = 2.9; coerced["checkpoint_digest"] = ""
    outcomes = []
    for label, value in (("blank", blank), ("float_counter", coerced)):
        try:
            SpawnedTaskCheckpoint.from_dict(value); outcomes.append(label + "=loaded")
        except (SpawnedTaskCheckpointError, ValueError, TypeError):
            outcomes.append(label + "=refused")
    ok = outcomes == ["blank=refused", "float_counter=refused"]
    return ok, " ".join(outcomes)


@scenario("D5 verifier timeout terminates descendants and carries the output tail")
def _d5():
    from loop_engine.core.verifier_execute import verifier_execute_operation, VerifierError
    folder = tempfile.mkdtemp(prefix="accept-d5-")
    marker = os.path.join(folder, "descendant-wrote-this")
    script = os.path.join(folder, "gate.sh")
    # A unique sleep duration identifies this probe's own descendants; nothing
    # else on a shared machine is matched or killed.
    token = "31.7331"
    with open(script, "w") as handle:
        handle.write("#!/bin/bash\necho before-timeout\n(sleep 3; touch '%s') &\nsleep %s\n" % (marker, token))

    class _Services:
        class request:
            verifier_path = script
    tail = None
    try:
        verifier_execute_operation({"timeout_seconds": 1}, _Services)
        return False, "no timeout raised"
    except VerifierError as exc:
        tail = getattr(exc, "output_tail", None)
    time.sleep(4)
    survivors = subprocess.run(["pgrep", "-f", "^sleep " + token + "$"], capture_output=True, text=True).stdout.split()
    for pid in survivors:
        subprocess.run(["kill", pid])
    ok = not os.path.exists(marker) and not survivors and tail is not None
    return ok, "marker_written=%s survivors=%d tail=%r" % (os.path.exists(marker), len(survivors), tail)


@scenario("D6 evaluation record binds the subject contract")
def _d6():
    from loop_engine.core.harness_response_evaluation import evaluate_response_as_loop
    from loop_engine.loop.recursive_loop import Loop
    _, expected = bound_request("accept-d6")
    record = evaluate_response_as_loop(arithmetic_evaluator(expected), '{"answer":42}', semantic_call_id="accept-d6",
                                       input_digest="d" * 64, parent=Loop("acceptance d6")).to_dict()
    ok = record.get("subject_contract_ref") == "fixture.answer/v1" and len(record.get("subject_contract_digest") or "") == 64
    return ok, "keys=%r" % sorted(record)


print("\n%d/%d scenarios pass" % (sum(1 for _, ok, _ in RESULTS if ok), len(RESULTS)), flush=True)
