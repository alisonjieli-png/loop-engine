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
from threading import Lock
from typing import Callable

from ..core.model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
    ModelGatewayResult,
)
from ..core.model_capabilities import ModelOutputAllocation
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
    semantic_call_id: str = ""
    output_allocation: ModelOutputAllocation | None = None

    def __post_init__(self) -> None:
        if self.output_allocation is not None and not isinstance(self.output_allocation, ModelOutputAllocation):
            raise SolutionModelError("output allocation must be a typed Loop decision")
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
        if not isinstance(self.semantic_call_id, str):
            raise SolutionModelError(
                "ModelInvocationRequest.semantic_call_id must be text")
        if (self.semantic_call_id
                and (self.semantic_call_id != self.semantic_call_id.strip()
                     or any(character.isspace()
                            for character in self.semantic_call_id)
                     or len(self.semantic_call_id) > 192)):
            raise SolutionModelError(
                "ModelInvocationRequest.semantic_call_id must be bounded text "
                "without whitespace")


@dataclass(frozen=True)
class FixtureModelExecutionRequest:
    """Passive configuration for one offline gateway contract fixture."""

    answers: tuple[str, ...] = ("fixture answer",)
    max_model_calls: int = 2
    validator: "Callable[[str], bool] | None" = field(
        default=None, repr=False, compare=False)
    reported_model: str = "fixture-model"
    required_prompt_fragments: tuple[str, ...] = ()
    forbidden_prompt_fragments: tuple[str, ...] = ()

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
        for name in ("required_prompt_fragments", "forbidden_prompt_fragments"):
            values = tuple(getattr(self, name))
            if (any(not isinstance(item, str) or not item for item in values)
                    or len(values) != len(set(values))):
                raise SolutionModelError(f"fixture {name} must contain text")
            object.__setattr__(self, name, values)
        if set(self.required_prompt_fragments) & set(
                self.forbidden_prompt_fragments):
            raise SolutionModelError("fixture prompt requirements overlap")


@dataclass(frozen=True)
class ModelExecution:
    """Explicit model authority supplied to one Solution execution."""

    gateway: ModelGateway = field(repr=False, compare=False)
    config: ModelGatewayConfig
    max_model_calls: "int | None" = None
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
        if (self.max_model_calls is not None
                and (not isinstance(self.max_model_calls, int)
                     or isinstance(self.max_model_calls, bool)
                     or self.max_model_calls < 1)):
            raise SolutionModelError(
                "ModelExecution.max_model_calls must be positive when set")
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
    """One in-process, single-flight budget owner; results are projections."""

    authority: ModelExecution
    results: list[ModelGatewayResult] = field(default_factory=list)
    _calls_charged: int = field(default=0, init=False, repr=False)
    _tokens_charged: int = field(default=0, init=False, repr=False)
    _usage_complete: bool = field(default=True, init=False, repr=False)
    _accounting_uncertain: bool = field(default=False, init=False, repr=False)
    _invocation_lock: object = field(default_factory=Lock, init=False, repr=False)
    _bound_authority: ModelExecution = field(init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.authority, ModelExecution) or self.results:
            raise SolutionModelError("session requires authority and an empty result projection")
        self._bound_authority = self.authority

    @property
    def calls_used(self) -> int:
        """Known physical subtotal; accounting_uncertain flags missing outcomes."""
        return self._calls_charged

    @property
    def accounting_uncertain(self) -> bool:
        return self._accounting_uncertain

    @property
    def semantic_calls_used(self) -> int:
        return len(self.results)

    @property
    def total_tokens_used(self) -> "int | None":
        if not self._usage_complete or self._accounting_uncertain:
            return None
        return self._tokens_charged

    def invoke(self, request: ModelInvocationRequest, parent_loop) -> str:
        """Invoke the gateway for one typed request owned by ``parent_loop``."""
        if not self._invocation_lock.acquire(blocking=False):
            raise SolutionModelError("a bounded session already has an invocation in flight",
                                     error_code="model_invocation_in_progress")
        try:
            return self._invoke_serial(request, parent_loop)
        finally:
            self._invocation_lock.release()

    def _invoke_serial(self, request: ModelInvocationRequest, parent_loop) -> str:
        if not isinstance(request, ModelInvocationRequest):
            raise SolutionModelError(
                "ModelExecutionSession.invoke requires ModelInvocationRequest")
        if self.authority is not self._bound_authority:
            raise SolutionModelError("session authority cannot be replaced",
                                     error_code="model_authority_changed")
        if self._accounting_uncertain:
            raise SolutionModelError("a previous invocation has unresolved accounting",
                                     error_code="token_accounting_unavailable")
        maximum_calls = self.authority.max_model_calls
        if maximum_calls is not None and self.calls_used >= maximum_calls:
            raise SolutionModelError(
                "whole-Solution model-call budget exhausted: "
                f"{self.calls_used}/{maximum_calls}",
                error_code="model_call_budget_exhausted")
        config = self.authority.config
        if maximum_calls is not None:
            remaining_calls = maximum_calls - self.calls_used
            configured_attempts = config.max_route_attempts
            config = replace(
                config,
                max_route_attempts=(
                    remaining_calls if configured_attempts is None
                    else min(configured_attempts, remaining_calls)))
        if config.max_total_tokens is not None:
            used_tokens = self.total_tokens_used
            if used_tokens is None:
                raise SolutionModelError(
                    "whole-Solution token accounting is incomplete; the "
                    "declared total-token ceiling cannot be enforced",
                    error_code="token_accounting_unavailable")
            remaining_tokens = config.max_total_tokens - used_tokens
            if remaining_tokens < 1:
                raise SolutionModelError(
                    "whole-Solution total-token budget exhausted",
                    error_code="token_budget_exhausted")
            config = replace(config, max_total_tokens=remaining_tokens)
        if request.model:
            if config.allowed_models and request.model not in config.allowed_models:
                raise SolutionModelError("requested model is outside the session authority",
                                         error_code="model_not_authorized")
            config = replace(config, allowed_models=(request.model,))
        if request.output_allocation is not None:
            config = replace(config, output_allocation=request.output_allocation)
        gateway_request = ModelGatewayRequest(
            prompt=request.prompt, config=config, system=request.system,
            temperature=request.temperature,
            semantic_call_id=request.semantic_call_id)
        try:
            result = self.authority.gateway.invoke(
                gateway_request, validate=self.authority.validator,
                parent=parent_loop)
            self._calls_charged += result.physical_model_calls
            if result.physical_model_calls:
                if result.total_tokens is None:
                    self._usage_complete = False
                else:
                    self._tokens_charged += result.total_tokens
            if result.error_code in ("token_bound_violated", "provider_attempt_contract_violated"):
                self._accounting_uncertain = True
            self.results.append(result)
        except BaseException as exc:
            # An orchestration exception can occur after dispatch. Never refund
            # authority based on a missing public result or reset through retry.
            self._accounting_uncertain = True
            if not isinstance(exc, Exception):
                raise
            raise SolutionModelError("gateway invocation ended with uncertain accounting",
                                     error_code="token_accounting_unavailable") from None
        if maximum_calls is not None and self.calls_used > maximum_calls:
            raise SolutionModelError(
                "ModelGateway exceeded the whole-Solution physical-call budget",
                error_code="model_call_budget_exhausted")
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
            missing = tuple(
                item for item in fixture.required_prompt_fragments
                if item not in prompt
            )
            forbidden = tuple(
                item for item in fixture.forbidden_prompt_fragments
                if item in prompt
            )
            if missing or forbidden:
                result = ChatResult(
                    "",
                    fixture.reported_model,
                    ok=False,
                    error=(
                        "fixture_prompt_contract_failed: "
                        f"missing={missing!r} forbidden={forbidden!r}"
                    ),
                )
                result.provider_status = "fixture_prompt_contract_failed"
                return result
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
    uncapped_authority = ModelExecution(authority.gateway, authority.config)
    check("model_execution_has_no_implicit_whole_run_call_ceiling",
          uncapped_authority.max_model_calls is None)
    session = authority.start_session()
    owner = Loop("fixture Solution owner")
    port = ModelInvocationPort(session, "hybrid", owner)
    first = port(ModelInvocationRequest(
        "one", semantic_call_id="semantic-call:solution-port-first"))
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
    from ..core.run_history import RunHistory
    history = RunHistory.from_ledger(
        owner.ledger.events, run_id="solution-model-port-correlation")
    history.commit()
    invocation_events = tuple(
        event for event in history.event_log
        if event.event_type == "model_invocation")
    semantic_call_ids = tuple(
        item.semantic_call_id for item in session.results)
    check("model_port_projects_logical_call_and_owner_into_run_history",
          semantic_call_ids[0] == "semantic-call:solution-port-first"
          and len(set(semantic_call_ids)) == 2
          and len(invocation_events) == 2
          and {event.detail.get("semantic_call_id")
               for event in invocation_events} == set(semantic_call_ids)
          and all(event.detail.get("owner_loop_id") == owner.loop_id
                  for event in invocation_events)
          and {event.loop_id for event in invocation_events}
              == set(attempt_ids)
          and history.verify_chain()["intact"],
          "separate logical calls retain distinct physical attempt Loops")
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
    prompt_guard = fixture_model_execution(FixtureModelExecutionRequest(
        answers=("guarded",), max_model_calls=1,
        required_prompt_fragments=("required-marker",),
        forbidden_prompt_fragments=("forbidden-marker",))).start_session()
    prompt_guard_refused = False
    try:
        ModelInvocationPort(prompt_guard, "non_deterministic", owner)(
            ModelInvocationRequest("marker is absent"))
    except SolutionModelError:
        prompt_guard_refused = True
    prompt_guard_result = prompt_guard.results[0]
    prompt_guard_attempt = prompt_guard_result.attempts[0]
    check("fixture_can_prove_prompt_body_reached_the_provider_adapter",
          prompt_guard_refused
          and prompt_guard_result.error_code == "provider_failed"
          and prompt_guard_attempt.provider_status
              == "fixture_prompt_contract_failed"
          and prompt_guard_attempt.prompt_digest
              == ModelGatewayRequest("marker is absent").prompt_digest
          and "required-marker" not in prompt_guard_result.error)
    arbitrary_refused = False
    try:
        ModelExecution(lambda prompt: prompt, ModelGatewayConfig())  # type: ignore[arg-type]
    except SolutionModelError:
        arbitrary_refused = True
    check("arbitrary_callable_is_not_model_authority", arbitrary_refused)
    return {"tests": results}
