"""Optional model-assisted orientation after deterministic task compilation.

The deterministic compiler remains authoritative for preserved input, template
binding, and requirement policy. This module asks one explicitly authorized
provider route for an advisory semantic review, validates a closed JSON
contract, and returns only the reviewed fields plus secret-safe attempt facts.
It never receives or persists a provider credential.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Mapping


COMPILE_MODEL_PROVIDERS = (
    "ollama_cloud", "mistral", "openrouter", "opencode_zen",
    "opencode_go")
MODEL_ASSISTED_COMPILE_PROMPT_VERSION = \
    "core.prompt.model_assisted_task_compile@1"
COMPILE_REVIEW_STATUSES = (
    "ready", "needs_clarification", "abstain_required")
OPENCODE_GO_ENDPOINT = "https://opencode.ai/zen/go/v1"
OPENCODE_GO_DEFAULT_MODEL = "deepseek-v4-flash"
OPENCODE_GO_MAXIMUM_OUTPUT = 384_000
OPENCODE_ZEN_ENDPOINT = "https://opencode.ai/zen/v1"


class ModelAssistedCompileError(ValueError):
    """A provider-assisted compilation precondition or contract failed."""


@dataclass(frozen=True)
class ModelAssistedCompileReview:
    """Validated advisory interpretation returned by one model attempt."""

    status: str
    task_summary: str
    task_family: str
    delegated_choices: tuple[str, ...]
    unresolved_facts: tuple[str, ...]
    material_questions: tuple[str, ...]
    next_action: str
    confidence: float

    @classmethod
    def from_mapping(cls, value: object, interaction_mode: str):
        required = {
            "status", "task_summary", "task_family", "delegated_choices",
            "unresolved_facts", "material_questions", "next_action",
            "confidence"}
        if not isinstance(value, dict) or set(value) != required:
            raise ModelAssistedCompileError(
                "model review must contain the exact registered fields")
        status = value.get("status")
        if status not in COMPILE_REVIEW_STATUSES:
            raise ModelAssistedCompileError(
                "model review status is not registered")
        summary = value.get("task_summary")
        family = value.get("task_family")
        next_action = value.get("next_action")
        if not isinstance(summary, str) or not summary.strip() \
                or len(summary) > 500:
            raise ModelAssistedCompileError(
                "task_summary must be a non-empty string of at most 500 chars")
        if not isinstance(family, str) or not re.fullmatch(
                r"[a-z0-9][a-z0-9_]{0,79}", family):
            raise ModelAssistedCompileError(
                "task_family must be one lowercase underscore identifier")
        if not isinstance(next_action, str) or not next_action.strip() \
                or len(next_action) > 300:
            raise ModelAssistedCompileError(
                "next_action must be a non-empty string of at most 300 chars")

        def strings(name: str) -> tuple[str, ...]:
            items = value.get(name)
            if not isinstance(items, list) or len(items) > 12 or any(
                    not isinstance(item, str) or not item.strip()
                    or len(item) > 160 for item in items):
                raise ModelAssistedCompileError(
                    f"{name} must contain at most 12 short strings")
            return tuple(item.strip() for item in items)

        confidence = value.get("confidence")
        if isinstance(confidence, bool) or not isinstance(
                confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ModelAssistedCompileError(
                "confidence must be a number from zero through one")
        questions = strings("material_questions")
        if interaction_mode == "autonomous" and (
                status == "needs_clarification" or questions):
            raise ModelAssistedCompileError(
                "an autonomous review must choose readiness or abstention "
                "without returning user questions")
        return cls(
            status=status,
            task_summary=summary.strip(),
            task_family=family,
            delegated_choices=strings("delegated_choices"),
            unresolved_facts=strings("unresolved_facts"),
            material_questions=questions,
            next_action=next_action.strip(),
            confidence=float(confidence),
        )

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "task_summary": self.task_summary,
            "task_family": self.task_family,
            "delegated_choices": list(self.delegated_choices),
            "unresolved_facts": list(self.unresolved_facts),
            "material_questions": list(self.material_questions),
            "next_action": self.next_action,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ModelAssistedCompileRequest:
    """One compiled task plus exact provider route and bounded authority."""

    compiled_task: Mapping[str, object]
    provider: str
    route_name: str
    interaction_mode: str
    max_physical_model_calls: int
    max_total_tokens: "int | None" = None
    timeout_seconds: float = 180.0
    thinking_power: str = "medium"

    def __post_init__(self) -> None:
        if self.provider not in COMPILE_MODEL_PROVIDERS:
            raise ModelAssistedCompileError(
                "compile provider must be ollama_cloud, mistral, openrouter, "
                "opencode_zen, or opencode_go")
        if not self.route_name.strip():
            raise ModelAssistedCompileError("a compile model route is required")
        if self.interaction_mode not in (
                "ask_when_material", "autonomous"):
            raise ModelAssistedCompileError(
                "compile interaction mode is not registered")
        if self.max_physical_model_calls != 1:
            raise ModelAssistedCompileError(
                "model-assisted compilation requires exactly one model call")
        if (self.max_total_tokens is not None and self.max_total_tokens < 1) \
                or self.timeout_seconds <= 0:
            raise ModelAssistedCompileError(
                "model-assisted compile budgets must be positive")
        if not self.compiled_task.get("compiled_task_id"):
            raise ModelAssistedCompileError(
                "model-assisted compilation needs a compiled task")


def opencode_go_gateway(api_key: str):
    """Bind one OpenCode Go API key behind the existing custom endpoint port."""
    if not api_key.strip():
        raise ModelAssistedCompileError("OpenCode Go API key is empty")
    from .custom_endpoint import CustomEndpoint
    from .model_capabilities import ModelOutputCapability
    from .model_gateway import ModelGateway, provider_spec_from_endpoint
    from .model_routes import ModelRoute

    endpoint = CustomEndpoint(
        name="opencode_go",
        base_url=OPENCODE_GO_ENDPOINT,
        model=OPENCODE_GO_DEFAULT_MODEL,
        api_key=api_key,
        wire="openai",
        locality="cloud",
        output_capability=ModelOutputCapability(
            OPENCODE_GO_MAXIMUM_OUTPUT,
            "OpenCode models metadata for opencode-go/deepseek-v4-flash",
            endpoint=f"{OPENCODE_GO_ENDPOINT}/chat/completions",
            observed_at="2026-08-27"),
        counts_as_evidence=True,
        timeout=180.0,
    )
    provider = provider_spec_from_endpoint(endpoint)
    route = ModelRoute(
        "cloud.opencode_go", "opencode_go", endpoint.model, "cloud",
        purposes=("counted_generation",))
    return ModelGateway(providers=(provider,), routes=(route,))


def openrouter_zero_cost_gateway(api_key: str, model: str = "", *,
                                 selection=None):
    """Bind one current zero-price OpenRouter model to an exact route.

    Selection uses the live provider catalog after model-call authority exists.
    The chosen model and declared output maximum are then frozen for the run.
    """
    if not api_key.strip():
        raise ModelAssistedCompileError("OpenRouter API key is empty")
    from datetime import datetime, timezone

    from . import openrouter_client
    from .custom_endpoint import CustomEndpoint
    from .model_capabilities import ModelOutputCapability
    from .model_gateway import ModelGateway, provider_spec_from_endpoint
    from .model_routes import ModelRoute

    rows = (openrouter_client.zero_cost_models()
            if selection is None else [selection])
    if model:
        rows = [item for item in rows if str(item.get("id")) == model]
    if not rows:
        raise ModelAssistedCompileError(
            "OpenRouter has no current zero-price structured model with a "
            "declared output maximum matching this request")
    selected = rows[0]
    selected_model = str(selected.get("id") or "")
    maximum = (selected.get("top_provider") or {}).get(
        "max_completion_tokens")
    if not selected_model or not isinstance(maximum, int) or maximum < 1:
        raise ModelAssistedCompileError(
            "OpenRouter zero-price selection lacks an exact model or output "
            "maximum")
    endpoint = CustomEndpoint(
        name="openrouter_zero_cost",
        base_url="https://openrouter.ai/api/v1",
        model=selected_model, api_key=api_key, wire="openai",
        locality="cloud",
        output_capability=ModelOutputCapability(
            maximum,
            "OpenRouter live Models API zero input/output price and "
            "top_provider.max_completion_tokens",
            endpoint=openrouter_client.MODELS_URL,
            observed_at=datetime.now(timezone.utc).isoformat()),
        counts_as_evidence=True, timeout=180.0)
    provider = provider_spec_from_endpoint(endpoint)
    route = ModelRoute(
        "cloud.openrouter.zero_cost", "openrouter_zero_cost",
        endpoint.model, "cloud", purposes=("counted_generation",))
    return ModelGateway(providers=(provider,), routes=(route,))


def opencode_zen_gateway(api_key: str, model: str = "", *, selection=None):
    """Bind a currently offered zero-cost OpenCode Zen model.

    ``selection`` is an injected typed catalog record for offline contract
    checks.  Production resolution intersects the live OpenCode list with
    Models.dev metadata before this gateway is built.
    """
    if not api_key.strip():
        raise ModelAssistedCompileError("OpenCode Zen API key is empty")
    from datetime import datetime, timezone

    from .custom_endpoint import CustomEndpoint
    from .model_capabilities import ModelOutputCapability
    from .model_gateway import ModelGateway, provider_spec_from_endpoint
    from .model_routes import ModelRoute
    from .opencode_zen_catalog import (
        OpenCodeZenModel, select_zero_cost_model, zero_cost_models)

    selected = selection
    if selected is None:
        if model:
            selected = next(
                (item for item in zero_cost_models(api_key=api_key)
                 if item.model == model), None)
            if selected is None:
                raise ModelAssistedCompileError(
                    "the selected OpenCode Zen model is not currently offered "
                    "as a zero-cost OpenAI-compatible model with a declared "
                    "output limit")
        else:
            selected = select_zero_cost_model(api_key=api_key)
    if not isinstance(selected, OpenCodeZenModel):
        raise ModelAssistedCompileError(
            "OpenCode Zen selection is not a typed catalog record")
    if model and model != selected.model:
        raise ModelAssistedCompileError(
            "OpenCode Zen model does not match the resolved catalog record")
    endpoint = CustomEndpoint(
        name="opencode_zen",
        base_url=OPENCODE_ZEN_ENDPOINT,
        model=selected.model,
        api_key=api_key,
        wire="openai",
        locality="cloud",
        output_capability=ModelOutputCapability(
            selected.maximum_output_tokens,
            "OpenCode live models intersected with Models.dev price and "
            "limit metadata",
            endpoint="https://models.dev/api.json",
            observed_at=datetime.now(timezone.utc).isoformat()),
        counts_as_evidence=True,
        timeout=180.0,
    )
    provider = provider_spec_from_endpoint(endpoint)
    route = ModelRoute(
        "cloud.opencode_zen.zero_cost", "opencode_zen", endpoint.model,
        "cloud", purposes=("counted_generation",))
    return ModelGateway(providers=(provider,), routes=(route,))


def _prompt(request: ModelAssistedCompileRequest):
    from .reasoning_call import (
        PromptAssemblySpec, ReasoningRequest, assemble_prompt, to_invocation)

    compiled = request.compiled_task
    binding = compiled.get("binding") or {
        "binding_mode": "open", "mapped_variables": {},
        "unmapped_requirements": [], "requirement_dispositions": []}
    work_item = compiled.get("work_item")
    if not isinstance(binding, dict) or not isinstance(work_item, dict):
        raise ModelAssistedCompileError(
            "compiled task is missing binding or WorkItemIR data")
    state = {
        "compiled_task_id": compiled.get("compiled_task_id"),
        "original_input": compiled.get("original_input"),
        "normalized_interpretation": compiled.get(
            "normalized_interpretation"),
        "task_type": compiled.get("task_type"),
        "output_kind": compiled.get("output_kind"),
        "template_id": binding.get("template_id"),
        "mapped_variables": binding.get("mapped_variables"),
        "unmapped_requirements": binding.get("unmapped_requirements"),
        "requirement_dispositions": binding.get(
            "requirement_dispositions"),
        "coordinates": work_item.get("coordinates"),
        "interaction_mode": request.interaction_mode,
    }
    schema = (
        "Return one JSON object with exactly these fields: status as ready, "
        "needs_clarification, or abstain_required; task_summary as a short "
        "string; task_family as one lowercase underscore identifier; "
        "delegated_choices, unresolved_facts, and material_questions as arrays "
        "of short strings; next_action as one chosen action string; and "
        "confidence as a number from 0 through 1.")
    reasoning = ReasoningRequest(
        question=str(compiled.get("original_input") or ""),
        objective=(
            "Review the deterministic task compilation and choose one safe "
            "next preparation action."),
        problem_state=state,
        output_schema=schema,
        allowed_tools=(),
        allowed_routes=(request.route_name,),
    )
    specification = PromptAssemblySpec(blocks={
        "authority_and_policy": (
            "You are an advisory Orientation reviewer inside Loop Engine. "
            "The deterministic compiled task and hard requirement policies "
            "remain authoritative. You may interpret and recommend, but you "
            "may not grant file, network, model, spending, or external-effect "
            "permission and may not claim that work ran."),
        "model_role_and_capabilities": (
            "Use semantic judgment to clarify task family, delegated choices, "
            "unresolved facts, and one next action. Do not return an option "
            "menu for the user to resolve."),
        "objective_and_success": reasoning.objective,
        "immediate_question": reasoning.question,
        "hard_constraints_and_tools": (
            "A safe ordinary selection may remain delegated when the request "
            "permits best judgment. Readiness means the next governed "
            "preparation step can begin, not that the full task is executable. "
            "In autonomous mode, never ask a question: choose ready when a "
            "safe next step exists, otherwise choose abstain_required. Preserve "
            "unknown facts and never treat them as false."),
        "verified_problem_state": json.dumps(
            state, sort_keys=True, separators=(",", ":")),
        "output_contract": schema,
        "final_directive": "Return only the JSON object.",
    })
    invocation = to_invocation(reasoning, specification, temperature=0.0)
    prompt, order = assemble_prompt(specification)
    if prompt != invocation.prompt:
        raise ModelAssistedCompileError(
            "model-assisted compile prompt materialization drifted")
    return invocation, tuple(order)


def _json_object(text: str):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def review_compiled_task(request: ModelAssistedCompileRequest, gateway) -> dict:
    """Run one model review through ModelGateway and return safe typed output."""
    route = gateway.registry.get(request.route_name)
    if route.provider != request.provider:
        raise ModelAssistedCompileError(
            "compile route does not belong to the selected provider")
    provider = gateway.providers.get(request.provider)
    if provider is None:
        raise ModelAssistedCompileError(
            "compile provider is not configured in the gateway")
    invocation, ordered_blocks = _prompt(request)
    try:
        capability = provider.output_capability_for(route.model)
    except Exception as exc:  # noqa: BLE001
        raise ModelAssistedCompileError(str(exc)) from exc
    minimum_total = (
        capability.maximum_output_tokens
        + len(invocation.prompt.encode("utf-8")))
    effective_total = request.max_total_tokens
    if effective_total is not None and effective_total < minimum_total:
        raise ModelAssistedCompileError(
            "max_total_tokens is too small for the selected model's exact "
            f"output maximum; required minimum is {minimum_total}")

    from .model_gateway import ModelGatewayConfig, ModelGatewayRequest

    review: ModelAssistedCompileReview | None = None

    def validate(text: str) -> bool:
        nonlocal review
        try:
            review = ModelAssistedCompileReview.from_mapping(
                _json_object(text), request.interaction_mode)
        except ModelAssistedCompileError:
            review = None
        return review is not None

    started = time.monotonic()
    result = gateway.invoke(ModelGatewayRequest(
        prompt=invocation.prompt,
        config=ModelGatewayConfig(
            route_names=(route.name,),
            allow_failover=False,
            max_route_attempts=1,
            timeout_seconds=request.timeout_seconds,
            max_total_tokens=effective_total,
            thinking_power=request.thinking_power),
        temperature=0.0,
        output_contract="one model-assisted task compile review JSON object",
        trace_id=f"model-assisted-task-compile.{time.time_ns()}",
    ), validate=validate)
    attempts = [item for item in result.attempts if item.loop_id]
    accepted = bool(
        result.ok and review is not None and result.provider_responded
        and result.accounting_complete and len(attempts) == 1)
    return {
        "record_type": "model_assisted_task_compile/v1",
        "ok": accepted,
        "advisory_only": True,
        "compiled_task_id": request.compiled_task.get("compiled_task_id"),
        "provider": result.provider or request.provider,
        "model": result.model or route.model,
        "route_name": result.route or route.name,
        "model_calls": len(attempts),
        "gateway_loop_id": result.gateway_loop_id,
        "model_loop_ids": [item.loop_id for item in attempts],
        "provider_responded": result.provider_responded,
        "usage_accounting_complete": result.accounting_complete,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
        "total_token_ceiling": effective_total,
        "total_token_ceiling_source": (
            "user_override" if request.max_total_tokens is not None
            else "unset"),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "prompt_version": MODEL_ASSISTED_COMPILE_PROMPT_VERSION,
        "prompt_blocks": list(ordered_blocks),
        "prompt_sha256": invocation.prompt_digest,
        "review": review.to_dict() if review is not None else None,
        "failure_code": "" if accepted else result.error_code,
        "failure_detail_sha256": (
            "" if accepted else hashlib.sha256(
                result.error.encode("utf-8")).hexdigest()),
    }


def self_test() -> dict:
    """Prove provider selection, exact grading, budgets, and secret safety."""
    results = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    from types import SimpleNamespace
    from .model_capabilities import ModelOutputCapability
    from .model_gateway import GatewayAttempt, ModelGatewayResult
    from .model_routes import ModelRoute
    from ..templates.compiler import TaskCompileRequest, compile_task_value
    from ..templates.model import InteractionMode

    compiled = compile_task_value(TaskCompileRequest(
        "Download an authorized public dataset and compare several models.",
        interaction_mode=InteractionMode.AUTONOMOUS))
    request = ModelAssistedCompileRequest(
        compiled_task=compiled, provider="ollama_cloud",
        route_name="cloud.default", interaction_mode="autonomous",
        max_physical_model_calls=1, max_total_tokens=None)

    class FakeRegistry:
        def get(self, name):
            return ModelRoute(
                name, "ollama_cloud", "fake-model", "cloud",
                purposes=("counted_generation",))

    class FakeGateway:
        def __init__(self):
            capability = ModelOutputCapability(
                512, "offline injected compile capability")
            self.registry = FakeRegistry()
            self.providers = {"ollama_cloud": SimpleNamespace(
                output_capability_for=lambda model: capability)}
            self.calls = 0

        def invoke(self, gateway_request, validate=None):
            self.calls += 1
            text = json.dumps({
                "status": "ready",
                "task_summary": "Compare models on a suitable public dataset.",
                "task_family": "tabular_model_comparison",
                "delegated_choices": ["dataset_source", "target_column"],
                "unresolved_facts": [],
                "material_questions": [],
                "next_action": "Select and verify one public dataset.",
                "confidence": 0.9,
            }, separators=(",", ":"))
            valid = bool(validate and validate(text))
            attempt = GatewayAttempt(
                "ollama_cloud", "fake-model", "cloud.default", "loop-model",
                valid, input_tokens=8, output_tokens=6,
                validation_ok=valid, provider_ok=True,
                maximum_output_tokens=512,
                maximum_output_source="offline injected compile capability",
                expected_model="fake-model")
            return ModelGatewayResult(
                ok=valid, text=text, provider="ollama_cloud",
                model="fake-model", route="cloud.default",
                input_tokens=8, output_tokens=6, attempts=[attempt],
                gateway_loop_id="loop-gateway")

    fake = FakeGateway()
    reviewed = review_compiled_task(request, fake)
    check("one_authorized_review_uses_one_gateway_attempt",
          reviewed["ok"] and reviewed["model_calls"] == 1
          and fake.calls == 1 and reviewed["review"]["status"] == "ready"
          and reviewed["total_token_ceiling_source"]
          == "unset" and reviewed["total_token_ceiling"] is None)
    check("the_review_is_advisory_and_preserves_delegated_choices",
          reviewed["advisory_only"]
          and reviewed["review"]["delegated_choices"]
          == ["dataset_source", "target_column"])

    too_small = False
    try:
        review_compiled_task(
            ModelAssistedCompileRequest(
                compiled_task=compiled, provider="ollama_cloud",
                route_name="cloud.default", interaction_mode="autonomous",
                max_physical_model_calls=1, max_total_tokens=1), fake)
    except ModelAssistedCompileError as exc:
        too_small = "max_total_tokens" in str(exc)
    check("an_insufficient_token_ceiling_refuses_before_a_call",
          too_small and fake.calls == 1)

    autonomous_question = {
        "status": "needs_clarification", "task_summary": "x",
        "task_family": "test", "delegated_choices": [],
        "unresolved_facts": ["source"],
        "material_questions": ["Which source?"], "next_action": "Ask.",
        "confidence": 0.5}
    refused = False
    try:
        ModelAssistedCompileReview.from_mapping(
            autonomous_question, "autonomous")
    except ModelAssistedCompileError:
        refused = True
    check("autonomous_review_cannot_return_a_user_question", refused)

    opencode = opencode_go_gateway("test-key-not-saved")
    description = opencode.providers["opencode_go"].describe()
    check("opencode_go_uses_the_existing_custom_endpoint_contract",
          opencode.registry.get("cloud.opencode_go").provider == "opencode_go"
          and description["credential_ref"] == "custom:opencode_go"
          and "test-key-not-saved" not in json.dumps(description))

    from .opencode_zen_catalog import OpenCodeZenModel
    zen = opencode_zen_gateway(
        "test-key-not-saved",
        selection=OpenCodeZenModel(
            "fixture-free", 100_000, 20_000, True))
    zen_description = zen.providers["opencode_zen"].describe()
    check("opencode_zen_uses_a_typed_zero_cost_dynamic_route",
          zen.registry.get("cloud.opencode_zen.zero_cost").model
              == "fixture-free"
          and zen_description["model_output_capability"][
              "maximum_output_tokens"] == 20_000
          and "test-key-not-saved" not in json.dumps(zen_description))

    openrouter_free = openrouter_zero_cost_gateway(
        "test-key-not-saved", selection={
            "id": "fixture/free", "pricing": {"prompt": "0",
                                                  "completion": "0"},
            "supported_parameters": ["response_format"],
            "top_provider": {"max_completion_tokens": 12_345}})
    free_description = openrouter_free.providers[
        "openrouter_zero_cost"].describe()
    check("openrouter_key_uses_a_current_zero_price_exact_route",
          openrouter_free.registry.get(
              "cloud.openrouter.zero_cost").model == "fixture/free"
          and free_description["model_output_capability"][
              "maximum_output_tokens"] == 12_345
          and "test-key-not-saved" not in json.dumps(free_description))

    import os
    from ..cli_operations import (
        _apply_compile_provider_shortcut, _compile_provider_key,
        _temporary_provider_key)

    source_env = "LOOP_ENGINE_TEST_COMPILE_KEY"
    standard_env = "OLLAMA_API_KEY"
    previous_source = os.environ.get(source_env)
    previous_standard = os.environ.get(standard_env)
    try:
        os.environ[source_env] = "offline-key-not-for-network"
        args = SimpleNamespace(
            compile_provider="ollama_cloud",
            prompt_for_provider_key=False,
            provider_key_env=source_env)
        selected_env, selected_key = _compile_provider_key(args)
        with _temporary_provider_key(selected_env, selected_key):
            installed_during_call = os.environ.get(standard_env)
        restored = os.environ.get(standard_env)
        check("cli_key_reference_is_temporary_and_restored_after_the_call",
              selected_env == standard_env
              and installed_during_call == "offline-key-not-for-network"
              and restored == previous_standard)

        os.environ[standard_env] = "offline-key-not-for-network"
        shortcut = SimpleNamespace(
            ollama_api_key="direct-test-key", mistral_api_key=None,
            openrouter_api_key=None,
            opencode_zen_api_key=None, opencode_go_api_key=None,
            compile_provider="",
            provider_key_env="", prompt_for_provider_key=False,
            authorize_model_calls=False, max_model_calls=0,
            max_total_tokens=None)
        _apply_compile_provider_shortcut(shortcut)
        direct_env, direct_key = _compile_provider_key(shortcut)
        check("ollama_key_shortcut_selects_one_bounded_advisory_call",
              shortcut.compile_provider == "ollama_cloud"
              and shortcut.authorize_model_calls
              and shortcut.max_model_calls == 1
              and shortcut.max_total_tokens is None
              and not shortcut.prompt_for_provider_key
              and shortcut._provider_key_value == "direct-test-key"
              and direct_env == standard_env
              and direct_key == "direct-test-key")
        os.environ.pop(standard_env, None)
        prompt_shortcut = SimpleNamespace(
            ollama_api_key="__prompt__", mistral_api_key=None,
            openrouter_api_key=None,
            opencode_zen_api_key=None, opencode_go_api_key=None,
            compile_provider="",
            provider_key_env="", prompt_for_provider_key=False,
            authorize_model_calls=False, max_model_calls=0,
            max_total_tokens=None)
        _apply_compile_provider_shortcut(prompt_shortcut)
        check("ollama_key_shortcut_prompts_when_no_environment_key_exists",
              prompt_shortcut.prompt_for_provider_key
              and prompt_shortcut.compile_provider == "ollama_cloud")
        from ..solve_cli import ProviderSetupError, _apply_quickstart
        os.environ[standard_env] = "offline-key-not-for-network"
        quickstart = SimpleNamespace(
            quickstart=True, ollama_api_key=None, mistral_api_key=None,
            openrouter_api_key=None, opencode_zen_api_key=None,
            opencode_go_api_key=None, compile_provider="",
            interaction_mode="ask_when_material",
            authorize_model_calls=False, max_model_calls=0,
            max_total_tokens=None)
        _apply_quickstart(quickstart)
        check("quickstart_selects_one_known_key_and_bounded_authority",
              quickstart.compile_provider == "ollama_cloud"
              and quickstart.interaction_mode == "ask_when_material"
              and quickstart.practitioner_mode == "non_deterministic"
              and quickstart.authorize_model_calls
              and quickstart.max_model_calls is None
              and quickstart.max_total_tokens is None)
        previous_openrouter = os.environ.get("OPENROUTER_API_KEY")
        try:
            os.environ["OPENROUTER_API_KEY"] = "offline-key-not-for-network"
            preferred_free = SimpleNamespace(
                quickstart=True, ollama_api_key=None, mistral_api_key=None,
                openrouter_api_key=None, opencode_zen_api_key=None,
                opencode_go_api_key=None, compile_provider="",
                interaction_mode="ask_when_material",
                authorize_model_calls=False, max_model_calls=0,
                max_total_tokens=None)
            _apply_quickstart(preferred_free)
            check(
                "quickstart_prefers_a_dynamic_zero_price_route_when_available",
                preferred_free.compile_provider == "openrouter")
        finally:
            if previous_openrouter is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = previous_openrouter
        os.environ.pop(standard_env, None)
        missing_refused = False
        provider_environment_names = (
            "OPENROUTER_API_KEY", "OPENCODE_ZEN_API_KEY",
            "MISTRAL_API_KEY", "OPENCODE_GO_API_KEY")
        saved_provider_environment = {
            name: os.environ.pop(name, None)
            for name in provider_environment_names}
        try:
            _apply_quickstart(SimpleNamespace(
                quickstart=True, ollama_api_key=None, mistral_api_key=None,
                openrouter_api_key=None, opencode_zen_api_key=None,
                opencode_go_api_key=None, compile_provider="",
                interaction_mode="ask_when_material",
                authorize_model_calls=False, max_model_calls=0,
                max_total_tokens=None))
        except ProviderSetupError:
            missing_refused = True
        finally:
            os.environ.update({name: value for name, value in
                               saved_provider_environment.items()
                               if value is not None})
        check("quickstart_without_a_provider_is_an_actionable_refusal",
              missing_refused)
    finally:
        if previous_source is None:
            os.environ.pop(source_env, None)
        else:
            os.environ[source_env] = previous_source
        if previous_standard is None:
            os.environ.pop(standard_env, None)
        else:
            os.environ[standard_env] = previous_standard

    passed = sum(1 for item in results if item["passed"])
    return {
        "record_type": "model_assisted_task_compile_contract_test/v1",
        "scope": "offline_contract_only",
        "tests": results,
        "passed": passed,
        "total": len(results),
        "all_passed": passed == len(results),
    }
