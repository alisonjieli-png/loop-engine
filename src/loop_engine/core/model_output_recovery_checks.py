"""Offline checks for the existing model-session recovery seam.

The fixture adapter opens no socket. It makes its recovery response depend on
the exact prompt so these checks prove context reached a counted semantic call,
not merely that a canned return value was copied into a record.
"""
from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

from ..code_nodes.solution_model_port import (
    ModelExecution,
    ModelInvocationRequest,
    SolutionModelError,
)
from ..loop.kernel_runtime import _ACTIVE_KERNEL_OWNER
from ..loop.recursive_loop import Loop
from .adaptive_practitioner_records import (
    AdaptivePractitionerRequest,
    AdaptiveRunServices,
    ModelStepRequest,
)
from .context_budget import ContextBudgetPolicy
from .model_capabilities import ModelOutputCapability
from .model_gateway import ModelGateway, ModelGatewayConfig, ProviderSpec
from .model_routes import ModelRoute, RoutePolicy
from .ollama_client import ChatResult
from .recovery import NO_REASONING_ROUTE_AVAILABLE


class _PromptSensitiveRecoveryAdapter:
    DEFAULT_MODEL = "fixture-model"
    prompts: list[str] = []

    @classmethod
    def output_capability_for(cls, model: str) -> ModelOutputCapability:
        return ModelOutputCapability(256, "offline recovery fixture")

    @classmethod
    def chat_maxout(cls, prompt: str, **_kwargs) -> ChatResult:
        cls.prompts.append(prompt)
        if "KIND: choose_recovery" not in prompt:
            return ChatResult(
                "", cls.DEFAULT_MODEL, prompt_tokens=2, eval_tokens=1,
                ok=False, error="offline injected provider failure",
                response_received=True, done=True)
        required = (
            "recover the bounded semantic responsibility",
            "output_validation_failed",
            "maximum_output_tokens",
            "artifact:context-pack",
            "inline:sha256:",
        )
        selected = (
            "retry_same_route" if all(item in prompt for item in required)
            else "abandon_step")
        return ChatResult(
            json.dumps({
                "selected": [selected],
                "reason": "the structured failure context supports this action",
                "expected_observation": "the unchanged model plan responds",
                "exit_condition": "stop after the selected action",
            }),
            cls.DEFAULT_MODEL, prompt_tokens=7, eval_tokens=5,
            ok=True, response_received=True, done=True, done_reason="stop")

    @staticmethod
    def verify(model: str = "") -> dict:
        return {"ok": True, "model": model or "fixture-model"}

    @staticmethod
    def live_models() -> list[str]:
        return ["fixture-model"]


def _session(max_model_calls: int):
    provider = ProviderSpec(
        "fixture", _PromptSensitiveRecoveryAdapter, "offline_fixture",
        "not_required", locality="local", tokens_provider_reported=True)
    route = ModelRoute(
        "fixture.route", "fixture", "fixture-model", "local",
        purposes=("counted_generation",))
    gateway = ModelGateway(
        providers=(provider,), routes=(route,),
        policy=RoutePolicy(allow_local_counted_generation=True))
    authority = ModelExecution(
        gateway,
        ModelGatewayConfig(
            route_names=(route.name,), allowed_localities=("local",),
            allow_failover=False, max_route_attempts=1),
        max_model_calls=max_model_calls)
    return authority.start_session()


def _services(session):
    task = (
        "TASK_HEAD " + "x" * 500 + " PRIVATE_MIDDLE " + "y" * 500
        + " TASK_TAIL")
    request = AdaptivePractitionerRequest(
        task,
        context_budget=ContextBudgetPolicy(
            text_head_bytes=80, text_tail_bytes=40,
            command_output_head_bytes=40, command_output_tail_bytes=20,
            list_total_bytes=256, packet_estimated_tokens_max=2048))
    return SimpleNamespace(
        model_session=session,
        request=request,
        run_id="offline-recovery-run",
        project_attempts=[],
        source_inspections=[],
        selected_intelligence_refs=["intelligence:one"],
        selected_memory_refs=["memory:one"],
        context_snapshots=[{
            "packet_artifact_ref": {"object_key": "artifact:packet"},
            "context_pack_artifact_ref": {
                "object_key": "artifact:context-pack"},
        }],
    )


def _exercise(max_model_calls: int):
    _PromptSensitiveRecoveryAdapter.prompts = []
    session = _session(max_model_calls)
    services = _services(session)
    loop = Loop("offline model recovery owner")
    token = _ACTIVE_KERNEL_OWNER.set(loop)
    try:
        try:
            session.invoke(ModelInvocationRequest(
                "ORIGINAL_FAILURE", semantic_call_id="original:failure"), loop)
        except SolutionModelError:
            pass
        outcome = AdaptiveRunServices._reasoned_recovery(
            services,
            ModelStepRequest(
                "decide_next", "recover the bounded semantic responsibility",
                {}, '{"answer":"string"}'),
            "output_validation_failed", 1, provider_responded=True)
    finally:
        _ACTIVE_KERNEL_OWNER.reset(token)
    return outcome, session, loop


def self_test() -> dict:
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    outcome, session, owner = _exercise(2)
    prompts = tuple(_PromptSensitiveRecoveryAdapter.prompts)
    recovery_prompt = prompts[-1]
    check(
        "prompt_sensitive_recovery_uses_same_counted_session",
        outcome.reasoned and outcome.selected == ("retry_same_route",)
        and session.calls_used == 2 and session.semantic_calls_used == 2
        and len(prompts) == 2)
    check(
        "recovery_prompt_carries_failure_capacity_contract_and_history",
        all(value in recovery_prompt for value in (
            "recover the bounded semantic responsibility",
            "output_validation_failed", "maximum_output_tokens",
            "artifact:context-pack", "inline:sha256:")))
    check(
        "declared_context_policy_bounds_task_text",
        "TASK_HEAD" in recovery_prompt and "TASK_TAIL" in recovery_prompt
        and "PRIVATE_MIDDLE" not in recovery_prompt)
    check(
        "unimplemented_recovery_controls_are_not_advertised",
        all(value not in recovery_prompt for value in (
            "compact_and_resubmit", "wait_then_retry"))
        and "requested_output_tokens" in recovery_prompt)
    result = session.results[-1]
    check(
        "recovery_has_distinct_semantic_call_and_current_loop_owner",
        result.semantic_call_id.startswith("recovery:")
        and result.semantic_call_id != "original:failure"
        and all(item.owner_loop_id == owner.loop_id
                for item in result.physical_provider_attempts))
    compiled = [item for item in owner.ledger.events
                if item.get("custom_kind")
                == "model_recovery_context_compiled"]
    check(
        "run_history_logs_context_digest_not_private_body",
        len(compiled) == 1 and compiled[0].get("recovery_context_digest")
        and "PRIVATE_MIDDLE" not in repr(compiled[0]))

    blocked, exhausted, _owner = _exercise(1)
    check(
        "same_budget_exhaustion_blocks_recovery_without_an_extra_call",
        blocked.blocker == NO_REASONING_ROUTE_AVAILABLE
        and not blocked.reasoned and exhausted.calls_used == 1
        and exhausted.semantic_calls_used == 1)

    class AllocationFixture(_PromptSensitiveRecoveryAdapter):
        wire: list[int] = []

        @classmethod
        def chat_maxout(cls, prompt, **kwargs):
            cls.wire.append(kwargs["max_output_tokens"])
            if "KIND: choose_recovery" in prompt:
                selected = 128 if '"length"' in prompt else 32
                return ChatResult(json.dumps({
                    "selected": ["retry_same_route"],
                    "adjustments": {"requested_output_tokens": selected},
                    "reason": "choose response room from the supplied completion history",
                    "expected_observation": "a complete response within the selected allowance",
                    "exit_condition": "stop after the checked retry",
                }), cls.DEFAULT_MODEL, prompt_tokens=5, eval_tokens=5,
                    ok=True, response_received=True, done=True, done_reason="stop")
            if prompt == "RETRY_WITH_DECISION":
                return ChatResult("accepted", cls.DEFAULT_MODEL,
                    prompt_tokens=2, eval_tokens=1, ok=True,
                    response_received=True, done=True, done_reason="stop")
            long_failure = prompt == "LONG_FAILURE"
            return ChatResult("partial", cls.DEFAULT_MODEL,
                prompt_tokens=2, eval_tokens=1, ok=False,
                error="output_limit_reached" if long_failure else "output_validation_failed",
                response_received=True, done=True,
                done_reason="length" if long_failure else "stop",
                output_limit_reached=long_failure)

    decisions = []
    for failure_prompt, expected in (("SHORT_FAILURE", 32), ("LONG_FAILURE", 128)):
        active_session = _session(3)
        gateway = active_session.authority.gateway
        gateway.providers["fixture"] = replace(gateway.providers["fixture"], adapter=AllocationFixture)
        active_services = _services(active_session)
        active_services.request = replace(active_services.request,
            task="Recover one response from its observed failure.",
            context_budget=ContextBudgetPolicy())
        active_owner = Loop("allocation from observed logs")
        token = _ACTIVE_KERNEL_OWNER.set(active_owner)
        AllocationFixture.wire = []
        try:
            try:
                active_session.invoke(ModelInvocationRequest(failure_prompt), active_owner)
            except SolutionModelError:
                pass
            decision = AdaptiveRunServices._reasoned_recovery(
                active_services, ModelStepRequest("decide_next", "produce a complete response", {},
                                                  '{"answer":"string"}'),
                active_session.results[-1].error_code, 1, provider_responded=True)
            allocation = decision.output_allocation
            result = active_session.invoke(ModelInvocationRequest(
                "RETRY_WITH_DECISION", output_allocation=allocation), active_owner)
        finally:
            _ACTIVE_KERNEL_OWNER.reset(token)
        check(f"history_dependent_allocation_{expected}_reaches_counted_retry",
              decision.reasoned and allocation is not None
              and allocation.requested_tokens == expected
              and allocation.capability.declared_maximum == 256
              and AllocationFixture.wire == [256, 256, expected]
              and active_session.calls_used == 3 and result == "accepted")
        decisions.append(allocation.requested_tokens if allocation else None)
    check("different_failure_histories_produce_different_explicit_allocations",
          decisions == [32, 128])

    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "model_output_recovery_checks/v1",
        "provider_calls": 0,
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
