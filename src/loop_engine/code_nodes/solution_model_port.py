"""ModelGateway-backed execution for model-using Solution Loops.

This module does not define another model runtime. It binds one run-scoped,
shared call budget to the existing :class:`ModelGateway`. Each invocation is
owned by the active Solution ``Loop``; the gateway then creates its routing
Loop and one model-attempt Loop per physical provider call.

An arbitrary callable is intentionally not accepted as model authority. Offline
tests use a deterministic ``ProviderAdapter`` fixture behind ``ModelGateway``,
which exercises the same provider-neutral path without claiming live provider
connectivity or model quality.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from ..core.model_gateway import (ModelGateway, ModelGatewayConfig,
                                  ModelGatewayRequest, ModelGatewayResult)
from ..loop.recursive_loop import MODEL_THINKING_POWER_LEVELS

MODEL_LEAF_MODES = ("hybrid", "non_deterministic")


class SolutionModelError(ValueError):
    """A model-using Solution Loop lacked valid or sufficient authority."""

    def __init__(self, message: str, *, error_code: str = "") -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(frozen=True)
class ModelInvocationRequest:
    """Passive input contract for one authorized model invocation."""

    prompt: str
    system: str = ""
    model: str = ""
    temperature: float = 0.7

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise SolutionModelError(
                "ModelInvocationRequest.prompt must be non-empty text")
        if not isinstance(self.system, str) or not isinstance(self.model, str):
            raise SolutionModelError(
                "model invocation system and model values must be text")
        if (not isinstance(self.temperature, (int, float))
                or isinstance(self.temperature, bool)):
            raise SolutionModelError(
                "ModelInvocationRequest.temperature must be numeric")


@dataclass(frozen=True)
class FixtureModelExecutionRequest:
    """Passive configuration for one offline gateway contract fixture."""

    answers: tuple[str, ...] = ("fixture answer",)
    max_model_calls: int = 2
    validator: "Callable[[str], bool] | None" = field(
        default=None, repr=False, compare=False)
    reported_model: str = "fixture-model"

    def __post_init__(self) -> None:
        if not isinstance(self.answers, tuple) or not all(
                isinstance(answer, str) for answer in self.answers):
            raise SolutionModelError("fixture answers must be a tuple of text")
        if (not isinstance(self.max_model_calls, int)
                or isinstance(self.max_model_calls, bool)
                or self.max_model_calls < 1):
            raise SolutionModelError(
                "fixture max_model_calls must be a positive integer")
        if self.validator is not None and not callable(self.validator):
            raise SolutionModelError("fixture validator must be callable")
        if not isinstance(self.reported_model, str) or not self.reported_model:
            raise SolutionModelError("fixture reported_model must be non-empty")


@dataclass(frozen=True)
class ModelExecution:
    """Explicit model authority supplied to one Solution execution."""

    gateway: ModelGateway = field(repr=False, compare=False)
    config: ModelGatewayConfig
    max_model_calls: int = 1
    llm_thinking_power: str = "medium"
    validator: "Callable[[str], bool] | None" = field(
        default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.gateway, ModelGateway):
            raise SolutionModelError(
                "ModelExecution.gateway must be the canonical ModelGateway")
        if not isinstance(self.config, ModelGatewayConfig):
            raise SolutionModelError(
                "ModelExecution.config must be a ModelGatewayConfig")
        if (not isinstance(self.max_model_calls, int)
                or isinstance(self.max_model_calls, bool)
                or self.max_model_calls < 1):
            raise SolutionModelError(
                "ModelExecution.max_model_calls must be a positive integer")
        if self.llm_thinking_power not in MODEL_THINKING_POWER_LEVELS:
            raise SolutionModelError(
                "ModelExecution.llm_thinking_power must be one of "
                f"{MODEL_THINKING_POWER_LEVELS}")
        if self.validator is not None and not callable(self.validator):
            raise SolutionModelError("ModelExecution.validator must be callable")

    def start_session(self) -> "ModelExecutionSession":
        return ModelExecutionSession(self)


@dataclass
class ModelExecutionSession:
    """Mutable run-scoped accounting shared by every model-using leaf."""

    authority: ModelExecution
    results: list[ModelGatewayResult] = field(default_factory=list)

    @property
    def calls_used(self) -> int:
        return len(self.results)

    def invoke(self, request: ModelInvocationRequest, parent_loop) -> str:
        """Invoke the gateway for one typed request owned by ``parent_loop``."""
        if not isinstance(request, ModelInvocationRequest):
            raise SolutionModelError(
                "ModelExecutionSession.invoke requires ModelInvocationRequest")
        if self.calls_used >= self.authority.max_model_calls:
            raise SolutionModelError(
                "whole-Solution model-call budget exhausted: "
                f"{self.calls_used}/{self.authority.max_model_calls}",
                error_code="model_call_budget_exhausted")
        config = self.authority.config
        if request.model:
            config = replace(config, allowed_models=(request.model,))
        gateway_request = ModelGatewayRequest(
            prompt=request.prompt, config=config, system=request.system,
            temperature=request.temperature)
        result = self.authority.gateway.invoke(
            gateway_request, validate=self.authority.validator,
            parent=parent_loop)
        self.results.append(result)
        if not result.ok:
            raise SolutionModelError(
                f"ModelGateway failed with {result.error_code or 'unknown'}: "
                f"{result.error[:200]}",
                error_code=result.error_code or "model_gateway_failed")
        return result.text


@dataclass(frozen=True)
class ModelInvocationPort:
    """Narrow port exposed to one active Solution operation callable."""

    session: ModelExecutionSession = field(repr=False, compare=False)
    mode: str
    parent_loop: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.mode not in MODEL_LEAF_MODES:
            raise SolutionModelError(
                f"a model invocation port serves {MODEL_LEAF_MODES}, "
                f"not {self.mode!r}")
        if self.parent_loop is None or not hasattr(self.parent_loop, "loop_id"):
            raise SolutionModelError(
                "a model invocation port needs its owning Solution Loop")

    @property
    def calls_used(self) -> int:
        return self.session.calls_used

    def __call__(self, request: ModelInvocationRequest) -> str:
        """Submit one typed invocation through the owning Solution Loop."""
        return self.session.invoke(request, self.parent_loop)


def collect_model_mode_loops(spec) -> tuple:
    """Return every hybrid or non-deterministic leaf in a Solution tree."""
    leaves = tuple(loop for loop in spec.loops
                   if loop.mode in MODEL_LEAF_MODES)
    for member in spec.members:
        leaves += collect_model_mode_loops(member)
    return leaves


def preflight_model_execution(spec, model_execution) -> list[str]:
    """Refuse model-using leaves before work unless gateway authority exists."""
    leaves = collect_model_mode_loops(spec)
    if not leaves:
        return []
    if not isinstance(model_execution, ModelExecution):
        return [
            f"solution {spec.solution_id}/{loop.loop_id}: declared mode "
            f"{loop.mode!r} needs explicit model authority through ModelGateway"
            for loop in leaves]
    return []


def fixture_model_execution(
    request: FixtureModelExecutionRequest | None = None,
) -> ModelExecution:
    """Offline contract fixture that still traverses the real gateway."""
    from ..core.model_capabilities import ModelOutputCapability
    from ..core.model_gateway import ProviderSpec
    from ..core.model_routes import ModelRoute, RoutePolicy
    from ..core.ollama_client import ChatResult

    fixture = request or FixtureModelExecutionRequest()
    queue = list(fixture.answers)

    class FixtureAdapter:
        DEFAULT_MODEL = "fixture-model"

        @staticmethod
        def output_capability_for(model=""):
            return ModelOutputCapability(64, "offline fixture contract")

        @staticmethod
        def chat_maxout(prompt, **kwargs):
            text = queue.pop(0) if queue else "fixture answer"
            return ChatResult(text, fixture.reported_model, prompt_tokens=2,
                              eval_tokens=3, ok=True)

        @staticmethod
        def verify(model=""):
            return {"ok": True, "model": model or "fixture-model"}

        @staticmethod
        def live_models():
            return ["fixture-model"]

    provider = ProviderSpec(
        "fixture", FixtureAdapter, "offline_fixture", "not_required",
        locality="local", tokens_provider_reported=True)
    route = ModelRoute(
        "fixture.route", "fixture", "fixture-model", "local",
        purposes=("counted_generation",))
    gateway = ModelGateway(
        providers=(provider,), routes=(route,),
        policy=RoutePolicy(allow_local_counted_generation=True))
    config = ModelGatewayConfig(
        route_names=("fixture.route",), allowed_localities=("local",),
        allow_failover=False, max_route_attempts=1)
    return ModelExecution(
        gateway, config, max_model_calls=fixture.max_model_calls,
        validator=fixture.validator)


def self_test() -> dict:
    """Prove canonical-gateway use, attempt identity, and shared budgeting."""
    from ..loop.recursive_loop import Loop

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    authority = fixture_model_execution(FixtureModelExecutionRequest(
        answers=("<think>private scratch</think>first", "second"),
        max_model_calls=2))
    session = authority.start_session()
    owner = Loop("fixture Solution owner")
    port = ModelInvocationPort(session, "hybrid", owner)
    first = port(ModelInvocationRequest("one"))
    second = port(ModelInvocationRequest("two"))
    check("model_port_uses_canonical_gateway",
          first == "first" and second == "second"
          and all(item.gateway_loop_id for item in session.results))
    check("private_reasoning_is_removed_before_solution_use",
          session.results[0].reasoning_present
          and "private scratch" not in session.results[0].text)
    attempt_ids = [attempt.loop_id for item in session.results
                   for attempt in item.attempts]
    check("every_physical_attempt_has_its_own_loop_identity",
          len(attempt_ids) == 2 and len(set(attempt_ids)) == 2
          and all(attempt_ids))
    refused = False
    try:
        port(ModelInvocationRequest("three"))
    except SolutionModelError:
        refused = True
    check("whole_solution_budget_is_fail_closed",
          refused and session.calls_used == 2)
    mismatch_session = fixture_model_execution(FixtureModelExecutionRequest(
        answers=("wrong deployment",), reported_model="unexpected-model",
        max_model_calls=1)).start_session()
    mismatch_refused = False
    try:
        ModelInvocationPort(mismatch_session, "non_deterministic", owner)(
            ModelInvocationRequest("identity probe"))
    except SolutionModelError:
        mismatch_refused = True
    check("unexpected_model_identity_is_rejected",
          mismatch_refused
          and mismatch_session.results[0].error_code
              == "model_identity_mismatch")
    arbitrary_refused = False
    try:
        ModelExecution(lambda prompt: prompt, ModelGatewayConfig())  # type: ignore[arg-type]
    except SolutionModelError:
        arbitrary_refused = True
    check("arbitrary_callable_is_not_model_authority", arbitrary_refused)
    return {"tests": results}
