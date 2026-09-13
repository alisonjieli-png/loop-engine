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
import hashlib
import json
from threading import Lock
from typing import Callable

from ..core.model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
    ModelGatewayResult,
)
from ..core.model_capabilities import ModelOutputAllocation
from ..core.observation_expectations import (
    ObservationExpectation, ObservationBinding, ExpectationAssessment,
    ExpectationDisposition, assess_observation,
)
from ..loop.recursive_loop import MODEL_THINKING_POWER_LEVELS
from ..core.model_response_admission import ModelResponseAdmissionPolicy
from ..core.harness_selection_records import HarnessSelectionScope, content_digest, response_contract_digest
from ..core.harness_response_evaluation import (
    PASSED,
    HarnessResponseEvaluator, HarnessResponseEvaluationState, evaluate_response_as_loop)

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
    response_expectation: ObservationExpectation | None = None
    response_admission_policy: ModelResponseAdmissionPolicy | None = None
    harness_selection_scope: HarnessSelectionScope | None = None
    response_evaluation_ref: str = ''

    @property
    def exact_input_digest(self) -> str:
        return hashlib.sha256(json.dumps(
            {'prompt': self.prompt, 'system': self.system}, sort_keys=True,
            separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

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
        expected = self.response_expectation
        if self.harness_selection_scope is not None and not isinstance(self.harness_selection_scope,HarnessSelectionScope):
            raise SolutionModelError('harness selection scope must be a typed record')
        if (type(self.response_evaluation_ref) is not str or len(self.response_evaluation_ref)>512
                or any(ord(c)<32 for c in self.response_evaluation_ref)):
            raise SolutionModelError('response evaluation reference must be bounded text')
        if (self.harness_selection_scope is not None or self.response_evaluation_ref) and expected is None:
            raise SolutionModelError('harness selection and response evaluation need a bound response contract')
        if self.response_admission_policy is not None:
            from ..core.model_response_admission import ModelResponseAdmissionPolicy
            if not isinstance(self.response_admission_policy, ModelResponseAdmissionPolicy) or expected is None:
                raise SolutionModelError('response normalization needs a typed policy and bound expectation')
        if expected is not None:
            if not isinstance(expected, ObservationExpectation):
                raise SolutionModelError('response expectation must be typed')
            if (not self.semantic_call_id or expected.operation_id != self.semantic_call_id
                    or expected.input_digest != self.exact_input_digest):
                raise SolutionModelError('response expectation does not bind this exact invocation')
            if expected.semantic_questions:
                raise SolutionModelError('unresolved semantic expectations need a separate verifier Loop')


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
    harness: "object | None" = field(default=None, repr=False, compare=False)
    response_evaluators: tuple[HarnessResponseEvaluator,...] = field(default=(),repr=False,compare=False)
    #: Optional replacement for the in-process session. Every cognitive
    #: step of the Practitioner reaches the model through the object this
    #: returns, so supplying one here redirects the whole loop (for
    #: example onto one OpenCode process per step, with that step's own
    #: tools, skills and permissions) with no change to the Practitioner.
    #: Receives this authority; must return an object exposing invoke(),
    #: results, calls_used and accounting_uncertain. Absent, the default
    #: session runs.
    session_factory: "Callable | None" = field(
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
        if (type(self.response_evaluators) not in (tuple,list)
                or any(not isinstance(item,HarnessResponseEvaluator) for item in self.response_evaluators)):
            raise SolutionModelError('response evaluators must be explicit typed host registrations')
        bindings=tuple(self.response_evaluators)
        if len({item.contract_ref for item in bindings})!=len(bindings):
            raise SolutionModelError('response evaluator references must be unique')
        object.__setattr__(self,'response_evaluators',bindings)

        if self.harness is not None:
            from ..core.harness_semantic import HarnessSemanticBinding
            if not isinstance(self.harness, HarnessSemanticBinding):
                raise SolutionModelError("harness realization must be a typed binding")
        if self.session_factory is not None and not callable(self.session_factory):
            raise SolutionModelError(
                "ModelExecution.session_factory must be callable")

    def start_session(self, *, artifact_store=None):
        """The one seam. Everything the Practitioner asks a model goes here."""
        if self.harness is not None and artifact_store is None and self.harness.artifact_store is None:
            raise SolutionModelError("harness execution needs a run-scoped artifact manager",
                                     error_code="harness_artifacts_required")
        if self.session_factory is None:
            return ModelExecutionSession(self, artifact_store=artifact_store)
        session = self.session_factory(self)
        # Every name the Practitioner reads on model_session, so a session
        # missing one is refused here rather than on a step at 3am.
        # accounting_uncertain is read by adaptive_practitioner.py,
        # adaptive_practitioner_result.py and adaptive_practitioner_scope.py
        # and was not validated: a documented four-member session passed
        # this check and failed with AttributeError when the run reported.
        missing = [name for name in (
            "invoke", "results", "calls_used", "accounting_uncertain")
                   if not hasattr(session, name)]
        if missing:
            raise SolutionModelError(
                "session_factory returned an object missing "
                f"{missing}; the Practitioner reads invoke(), results, "
                "calls_used and accounting_uncertain on every step")
        return session


@dataclass
class ModelExecutionSession:
    """One in-process, single-flight budget owner; results are projections."""

    authority: ModelExecution
    results: list[ModelGatewayResult] = field(default_factory=list)
    artifact_store: object = field(default=None, repr=False, compare=False)
    _calls_charged: int = field(default=0, init=False, repr=False)
    _tokens_charged: int = field(default=0, init=False, repr=False)
    _usage_complete: bool = field(default=True, init=False, repr=False)
    _accounting_uncertain: bool = field(default=False, init=False, repr=False)
    _effect_reconciliation_required: bool = field(default=False, init=False, repr=False)
    _invocation_lock: object = field(default_factory=Lock, init=False, repr=False)
    _bound_authority: ModelExecution = field(init=False, repr=False)
    #: Consecutive failed-invocation error codes, oldest first. Observability
    #: only: feeds the recurrence diagnostic, never alters routing or budgets.
    #: A success resets the streak; only identical consecutive codes count.
    _recent_failure_shapes: list = field(default_factory=list, init=False,
                                         repr=False)

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
    def effect_reconciliation_required(self) -> bool:
        return self._effect_reconciliation_required

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
        if self._effect_reconciliation_required:
            raise SolutionModelError('a previous harness reported effects requiring reconciliation',
                                     error_code='unexpected_effects_require_reconciliation')
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
        validator = self.authority.validator
        expected = request.response_expectation
        evaluation_state=HarnessResponseEvaluationState()
        evaluator=None
        contract_digest=(response_contract_digest(expected,request.response_admission_policy)
                         if expected is not None else '')
        if request.response_evaluation_ref:
            matches=[item for item in self.authority.response_evaluators
                     if item.contract_ref==request.response_evaluation_ref]
        else:
            matches=[item for item in self.authority.response_evaluators
                     if expected is not None and item.subject_contract_ref==expected.output_contract_ref
                     and item.subject_contract_digest==contract_digest]
        if len(matches)>1 or (request.response_evaluation_ref and not matches):
            raise SolutionModelError('response evaluator registration is missing or ambiguous',
                                     error_code='response_evaluator_unavailable')
        if matches:
            evaluator=matches[0]
            if (expected is None or evaluator.subject_contract_ref!=expected.output_contract_ref
                    or evaluator.subject_contract_digest!=contract_digest):
                raise SolutionModelError('response evaluator does not bind the exact subject contract',
                                         error_code='response_evaluator_contract_mismatch')
        selection_scope=request.harness_selection_scope
        harness=self.authority.harness
        selection_policy=harness.selection_policy if harness is not None else None
        if selection_scope is not None and selection_policy is None:
            raise SolutionModelError('harness selection policy is not installed',error_code='harness_selection_unavailable')
        if selection_policy is not None and expected is not None:
            profile_ref=parent_loop.definition.role_profile_id+'@'+parent_loop.definition.role_profile_version
            evaluation_ref=evaluator.contract_ref if evaluator is not None else 'response_admission/v1'
            settings_digest=content_digest({'temperature':request.temperature,
                'output_allowance':config.output_allocation.requested_tokens if config.output_allocation else None,
                'gateway_thinking_power':config.thinking_power,'loop_thinking_power':self.authority.llm_thinking_power,
                'evaluation_implementation':evaluator.implementation_digest if evaluator is not None else None,
                'evaluation_qualification':evaluator.qualification_digest if evaluator is not None else None})
            if selection_scope is None:
                selection_scope=HarnessSelectionScope(operation_contract_ref=expected.output_contract_ref,
                    response_contract_digest=contract_digest,profile_ref=profile_ref,
                    resource_profile_digest=selection_policy.resource_profile_digest,
                    execution_settings_digest=settings_digest,owning_definition_digest=parent_loop.definition.content_digest,
                    evaluation_contract_ref=evaluation_ref)
            elif (selection_scope.operation_contract_ref!=expected.output_contract_ref
                    or selection_scope.response_contract_digest!=contract_digest
                    or selection_scope.profile_ref!=profile_ref
                    or selection_scope.execution_settings_digest!=settings_digest
                    or selection_scope.owning_definition_digest!=parent_loop.definition.content_digest
                    or selection_scope.evaluation_contract_ref!=evaluation_ref):
                raise SolutionModelError('harness selection scope does not bind the actual assignment',
                                         error_code='harness_selection_scope_mismatch')
        response_admissions = []
        if expected is not None:
            parent_loop.ledger.record(loop_id=parent_loop.loop_id, event='custom',
                action='model_response_expectation_bound',
                semantic_call_id=request.semantic_call_id,
                expectation_digest=expected.content_digest,
                input_digest=request.exact_input_digest)
            authority_validator = validator

            def validator(text):
                if request.response_admission_policy is not None:
                    from ..core.model_response_admission import (
                        ModelResponseAdmissionRequest, admit_model_response_as_loop)
                    admitted = admit_model_response_as_loop(ModelResponseAdmissionRequest(
                        text, expected.output_contract_ref, expected.content_digest,
                        schema=json.loads(expected.schema_json), policy=request.response_admission_policy),
                        parent=parent_loop)
                    response_admissions.append(admitted)
                    parent_loop.ledger.record(loop_id=parent_loop.loop_id, event='custom',
                        action='model_response_expectation_assessed',
                        semantic_call_id=request.semantic_call_id,
                        expectation_digest=expected.content_digest,
                        input_digest=expected.input_digest,
                        admission=admitted.to_dict(), task_accepted=False)
                    return (admitted.admitted and
                            (authority_validator is None or bool(authority_validator(text))))
                try:
                    actual = ObservationBinding(expected.operation_id, expected.input_digest, text)
                    assessment = assess_observation(expected, actual)
                except (ValueError, TypeError, RecursionError):
                    assessment = ExpectationAssessment(expected.content_digest,
                        hashlib.sha256(text.encode()).hexdigest(),
                        ExpectationDisposition.INCOMPATIBLE, False, False, ('invalid_json_response',))
                parent_loop.ledger.record(loop_id=parent_loop.loop_id, event='custom',
                    action='model_response_expectation_assessed',
                    semantic_call_id=request.semantic_call_id, **assessment.to_dict())
                return (assessment.handoff_ready and
                        (authority_validator is None or bool(authority_validator(text))))
        if evaluator is not None:
            structural_validator=validator
            def validator(text):
                if structural_validator is not None and not structural_validator(text):
                    return False
                admitted_text=(json.dumps(response_admissions[-1].value,sort_keys=True,separators=(',',':'),
                                         ensure_ascii=False,allow_nan=False)
                               if response_admissions and response_admissions[-1].admitted else text)
                evaluation=evaluate_response_as_loop(evaluator,admitted_text,
                    semantic_call_id=request.semantic_call_id,input_digest=request.exact_input_digest,parent=parent_loop)
                evaluation_state.evaluations.append(evaluation)
                if evaluation.status==PASSED:
                    return True
                # A verdict about meaning is typed so the gateway records it
                # as such and does not treat it as a reason to try another route.
                from ..core.model_gateway import ValidationVerdict
                raise ValidationVerdict(
                    'semantic_response_rejected' if evaluation.status=='rejected'
                    else 'response_evaluation_inconclusive',
                    'registered evaluator '+evaluator.contract_ref+' returned '+evaluation.status)
        try:
            if self.authority.harness is None:
                result = self.authority.gateway.invoke(
                    gateway_request, validate=validator,
                    parent=parent_loop)
            else:
                result = self.authority.harness.invoke(
                    gateway_request, gateway=self.authority.gateway,
                    validate=validator, parent=parent_loop,
                    artifact_store=self.artifact_store,selection_scope=selection_scope,
                    evaluation_state=evaluation_state)
            if response_admissions:
                result = replace(result, response_admissions=tuple(response_admissions))
            if evaluation_state.evaluations:
                result=replace(result,response_evaluations=tuple(evaluation_state.evaluations))
                last=evaluation_state.evaluations[-1]
                if result.error_code=='output_validation_failed' and last.status!=PASSED:
                    result.error_code=('semantic_response_rejected' if last.status=='rejected'
                                       else 'response_evaluation_inconclusive')
            self._calls_charged += result.physical_model_calls
            if result.physical_model_calls:
                if result.total_tokens is None:
                    self._usage_complete = False
                else:
                    self._tokens_charged += result.total_tokens
            if result.error_code in ("token_bound_violated", "provider_attempt_contract_violated"):
                self._accounting_uncertain = True
            if result.error_code == 'unexpected_effects_require_reconciliation':
                self._effect_reconciliation_required = True
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
            self._note_failure_shape(
                result.error_code or "model_gateway_failed", parent_loop)
            raise SolutionModelError(
                f"ModelGateway failed with {result.error_code or 'unknown'}: "
                f"{result.error[:200]}",
                error_code=result.error_code or "model_gateway_failed")
        self._recent_failure_shapes.clear()
        return result.text

    def _note_failure_shape(self, error_code: str, parent_loop) -> None:
        """Record one failed-invocation shape; announce a recurrence streak.

        Three consecutive identical failure codes mean the run is repeating
        itself, not exploring. The announcement is a ledger event only —
        routing, budgets, and retry policy are untouched (a future policy
        change can subscribe to it without touching this path).
        """
        self._recent_failure_shapes.append(str(error_code))
        streak = 0
        for code in reversed(self._recent_failure_shapes):
            if code == error_code:
                streak += 1
            else:
                break
        if streak == 3:
            try:
                parent_loop.ledger.record(
                    loop_id=getattr(parent_loop, "loop_id", ""),
                    event="custom", action="model_recurrence_noticed",
                    error_code=error_code, consecutive_failures=streak)
            except (AttributeError, TypeError, ValueError):
                pass


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

    class _Ledger:
        def __init__(self):
            self.events = []
        def record(self, **fields):
            self.events.append(fields)
            return len(self.events)

    class _Owner:
        def __init__(self):
            self.loop_id = "owner-recurrence-probe"
            self.ledger = _Ledger()

    probe_session = authority.start_session()
    probe_owner = _Owner()
    probe_session._note_failure_shape("model_gateway_failed", probe_owner)
    probe_session._note_failure_shape("model_gateway_failed", probe_owner)
    quiet = len(probe_owner.ledger.events)
    probe_session._note_failure_shape("model_gateway_failed", probe_owner)
    announced = [e for e in probe_owner.ledger.events
                 if e.get("action") == "model_recurrence_noticed"]
    check("third_consecutive_same_shape_failure_is_announced",
          quiet == 0 and len(announced) == 1
          and announced[0]["error_code"] == "model_gateway_failed"
          and announced[0]["consecutive_failures"] == 3,
          "observability only: routing and budgets untouched")
    probe_session._note_failure_shape("timeout", probe_owner)
    check("a_different_shape_breaks_the_streak",
          len([e for e in probe_owner.ledger.events
               if e.get("action") == "model_recurrence_noticed"]) == 1)

    # Fifty was an operator-imposed pilot guard, not a product default. This
    # finite fixture checks that omitting a ceiling actually permits later
    # calls, while the explicit-budget check above still refuses overrun.
    unlimited_fixture = fixture_model_execution()
    unlimited = ModelExecution(
        unlimited_fixture.gateway, unlimited_fixture.config).start_session()
    unlimited_owner = Loop("uncapped offline Solution owner")
    unlimited_port = ModelInvocationPort(
        unlimited, "non_deterministic", unlimited_owner)
    answers = [unlimited_port(ModelInvocationRequest(f"offline call {index}"))
               for index in range(51)]
    check("an_unset_call_ceiling_does_not_stop_at_fifty",
          len(answers) == 51 and unlimited.calls_used == 51
          and unlimited.total_tokens_used == 255
          and all(answer == "fixture answer" for answer in answers),
          "offline gateway fixture only; no live provider calls")

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
    # The session_factory seam. A stand-in is returned unchanged with its
    # authority intact; an object missing what the Practitioner reads on
    # every step is refused here, not on the first step at 3am.
    class _StandIn:
        def __init__(self, authority):
            self.authority, self.results, self.calls_used = authority, [], 0
            self.accounting_uncertain = False

        def invoke(self, request, owner):
            return "{}"

    seam_gateway = _Gateway() if "_Gateway" in dir() else ModelGateway()
    seam_config = ModelGatewayConfig(
        route_names=("seam",), allow_failover=False, max_route_attempts=1)
    hooked = ModelExecution(seam_gateway, seam_config, max_model_calls=2,
                            session_factory=_StandIn).start_session()
    check("session_factory_redirects_start_session",
          isinstance(hooked, _StandIn) and hooked.authority.max_model_calls == 2,
          "every Practitioner step reaches the model through this object")
    check("default_start_session_is_unchanged_without_a_factory",
          isinstance(ModelExecution(seam_gateway, seam_config).start_session(),
                     ModelExecutionSession))
    try:
        ModelExecution(seam_gateway, seam_config,
                       session_factory=lambda authority: object()).start_session()
        check("an_incomplete_session_is_refused_by_name", False, "accepted")
    except SolutionModelError as exc:
        check("an_incomplete_session_is_refused_by_name",
              "invoke" in str(exc) and "calls_used" in str(exc), str(exc)[:80])
    try:
        ModelExecution(seam_gateway, seam_config, session_factory="opencode")
        check("a_non_callable_factory_is_refused", False, "accepted")
    except SolutionModelError:
        check("a_non_callable_factory_is_refused", True)
    return {"tests": results}
