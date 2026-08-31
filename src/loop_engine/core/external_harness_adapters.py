"""Optional adapters for four external agent harnesses.

Adapters expose one common Loop Engine request and result while importing each
framework only when selected. External packages are not core dependencies.
Every adapter also accepts an injected runner for deterministic conformance
tests and application-specific SDK configuration.

Pydantic AI, OpenAI Agents, and Microsoft Agent Framework receive the exact
resolved output maximum at their documented SDK boundaries. Deep Agents
requires a provider-bound model whose typed binding records that the same
maximum was applied before the graph was created. No path installs packages,
chooses credentials, approves effects, or claims task acceptance.
"""
from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.util
import inspect
import json
from dataclasses import dataclass
from typing import Callable, Mapping

from .external_harness import (
    HarnessAdapterInfo, HarnessError, HarnessModelCall, HarnessRunRequest,
    HarnessRunResult, HarnessRuntimeBinding, HarnessServices, ModelOutputLimit,
    resolve_harness_output_limit)

RunnerFn = Callable[[HarnessRunRequest, HarnessServices], object]

_FRAMEWORKS = {
    "pydantic_ai": {
        "module": "pydantic_ai", "package": "pydantic-ai",
        "features": ("typed_request", "exact_output_limit",
                     "request_limit", "usage_reporting"),
        "output_limit_binding": "ModelSettings.max_tokens",
        "limitations": (
            "a provider-bound SDK model is required through HarnessServices",
            "tools, multi-agent delegation, memory, MCP, sandbox, and approvals "
            "are intentionally not exposed by this bounded adapter",
        ),
    },
    "deep_agents": {
        "module": "deepagents", "package": "deepagents",
        "features": ("typed_request", "provider_bound_model",
                     "exact_output_limit", "bounded_graph_recursion",
                     "usage_reporting"),
        "output_limit_binding": "HarnessRuntimeBinding.output_limit",
        "limitations": (
            "the supplied SDK model must already enforce the exact output maximum",
            "host filesystem access, persistent memory, skills, MCP, subagents, "
            "and approvals are intentionally not exposed by this bounded adapter",
        ),
    },
    "openai_agents": {
        "module": "agents", "package": "openai-agents",
        "features": ("typed_request", "max_turns", "exact_output_limit",
                     "usage_reporting", "tracing_disabled"),
        "output_limit_binding": "ModelSettings.max_tokens",
        "limitations": (
            "a provider-bound SDK model is required through HarnessServices",
            "handoffs, agents-as-tools, MCP, sandbox, and approvals are not "
            "exposed by this bounded adapter",
        ),
    },
    "microsoft_agent_framework": {
        "module": "agent_framework", "package": "agent-framework-core",
        "features": ("typed_request", "configured_chat_client",
                     "physical_call_counting", "exact_output_limit",
                     "web_search_disabled", "file_memory_disabled"),
        "output_limit_binding": "create_harness_agent.max_output_tokens",
        "limitations": (
            "a provider-bound SDK client is required through HarnessServices",
            "web search, file memory, compaction, todos, autonomous harness "
            "looping, skills, and approvals are disabled at this boundary",
        ),
    },
}

@dataclass(frozen=True)
class _AdapterExecution:
    """Raw SDK result plus the exact limit applied by the built-in boundary."""

    raw: object
    applied_output_limit: "ModelOutputLimit | None" = None
    prompt_resource: object = None

def _instruction_resource(harness_id: str):
    from ..strings.prompt_fragments import external_harness_instruction_bundle
    return external_harness_instruction_bundle(harness_id).render(
        {}, provenance={})

class PhysicalCallCountingClient:
    """Count and stop calls at an SDK client's provider request boundary."""

    def __init__(self, client, *, max_calls: "int | None" = None):
        if not callable(getattr(client, "get_response", None)):
            raise TypeError("counted chat client needs get_response")
        if (max_calls is not None
                and (not isinstance(max_calls, int)
                     or isinstance(max_calls, bool) or max_calls < 1)):
            raise ValueError("max_calls must be a positive integer")
        self._client = client
        self._max_calls = max_calls
        self.call_count = 0

    @property
    def additional_properties(self):
        return getattr(self._client, "additional_properties", {})

    def get_response(self, *args, **kwargs):
        if (self._max_calls is not None
                and self.call_count >= self._max_calls):
            raise HarnessError(
                "external harness model-call budget is exhausted")
        self.call_count += 1
        return self._client.get_response(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._client, name)

def _package_state(harness_id: str, injected: bool) -> tuple[bool, str, str]:
    facts = _FRAMEWORKS[harness_id]
    if injected:
        return True, "injected", ""
    if importlib.util.find_spec(facts["module"]) is None:
        return False, "", (
            f"optional package {facts['package']!r} is not installed")
    try:
        version = importlib.metadata.version(facts["package"])
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    if not facts["output_limit_binding"]:
        return False, version, (
            "package detected, but the built-in adapter has no verified exact "
            "maximum-output binding and will not execute")
    return True, version, ""

def _prompt(request: HarnessRunRequest) -> str:
    payload = json.dumps(dict(request.input_data), sort_keys=True, default=str)
    if len(payload) > 50_000:
        payload = payload[:50_000] + "\n[bounded input preview]"
    return (
        f"Goal: {request.goal}\n"
        f"Input contract: {list(request.contract.input_roles)}\n"
        f"Output contract: {list(request.contract.output_roles)}\n"
        f"Context references: {list(request.context_refs)}\n"
        f"Input data: {payload}\n"
        "Return the requested result. Do not claim verification or acceptance; "
        "the spawning Loop performs the independent evaluation."
    )

def _required_output_limit(request: HarnessRunRequest) -> ModelOutputLimit:
    limit = request.budget.output_limit
    if limit is None:
        raise HarnessError(
            "adapter execution needs a resolved exact model output maximum")
    if (limit.provider_id != request.provider_id
            or limit.model_id != request.model_id):
        raise HarnessError(
            "resolved model output maximum does not match provider and model")
    return limit

def _required_runtime_binding(
        request: HarnessRunRequest, services: HarnessServices, *,
        runtime_kind: str,
        preconfigured_output_limit: bool = False) -> HarnessRuntimeBinding:
    binding = services.runtime_binding
    if binding is None:
        raise HarnessError(
            "package-backed harness execution needs a typed, provider-bound "
            "HarnessRuntimeBinding")
    binding.validate_for(
        request, runtime_kind=runtime_kind,
        preconfigured_output_limit=preconfigured_output_limit)
    return binding

def _openai_model_settings_kwargs(request: HarnessRunRequest) -> dict:
    limit = _required_output_limit(request)
    return {
        "max_tokens": limit.max_output_tokens,
        "temperature": float(request.metadata.get("temperature", 0.2)),
        "include_usage": True,
    }

def _pydantic_model_settings_kwargs(request: HarnessRunRequest) -> dict:
    settings = {
        "max_tokens": _required_output_limit(request).max_output_tokens,
        "temperature": float(request.metadata.get("temperature", 0.2)),
    }
    if request.budget.max_seconds is not None:
        settings["timeout"] = float(request.budget.max_seconds)
    return settings

def _pydantic_usage_limit_kwargs(request: HarnessRunRequest) -> dict:
    values = {"request_limit": request.budget.max_model_calls}
    if request.budget.max_total_tokens is not None:
        values["total_tokens_limit"] = request.budget.max_total_tokens
    return values

def _deep_agents_graph_config(request: HarnessRunRequest) -> dict:
    # LangGraph counts graph steps rather than physical model calls. The
    # preconfigured model binding remains responsible for the physical limit.
    return {"recursion_limit": max(4, request.budget.max_model_calls * 4 + 2)}

def _microsoft_harness_kwargs(
        request: HarnessRunRequest, counted_client: object) -> dict:
    limit = _required_output_limit(request)
    return {
        "client": counted_client,
        "disable_web_search": True,
        "disable_file_memory": True,
        "disable_compaction": True,
        "disable_todo": True,
        "disable_mode": True,
        "disable_tool_auto_approval": True,
        "max_output_tokens": limit.max_output_tokens,
    }

def _resolve_output_request(
        request: HarnessRunRequest,
        services: HarnessServices) -> HarnessRunRequest:
    return resolve_harness_output_limit(request, services)

def _value(source, names, default=None):
    for name in names:
        if isinstance(source, Mapping) and name in source:
            return source[name]
        if hasattr(source, name):
            value = getattr(source, name)
            try:
                return value() if callable(value) else value
            except TypeError:
                continue
    return default

def _int_value(source, names) -> "int | None":
    value = _value(source, names)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None

def _float_value(source, names) -> "float | None":
    value = _value(source, names)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

def _message_usage(raw, request: HarnessRunRequest
                   ) -> tuple[list[HarnessModelCall], int]:
    messages = _value(raw, ("messages",), ()) or ()
    calls = []
    for message in messages:
        usage = _value(message, ("usage_metadata", "usage"), None)
        if usage is None:
            continue
        input_tokens = _int_value(
            usage, ("input_tokens", "prompt_tokens", "request_tokens"))
        output_tokens = _int_value(
            usage, ("output_tokens", "completion_tokens", "response_tokens"))
        response = _value(message, ("response_metadata",), {}) or {}
        model = str(_value(response, ("model_name", "model"), "")
                    or request.model_id)
        calls.append(HarnessModelCall(
            provider=request.provider_id, model=model, ok=True,
            input_tokens=input_tokens, output_tokens=output_tokens))
    return calls, len(calls)

def _normalize(raw, request: HarnessRunRequest, *,
               adapter_version: str,
               applied_output_limit: "ModelOutputLimit | None" = None,
               prompt_resource=None,
               ) -> HarnessRunResult:
    if isinstance(raw, HarnessRunResult):
        if raw.provider_id and raw.provider_id != request.provider_id:
            raise HarnessError("adapter result changed provider_id")
        if raw.model_id and raw.model_id != request.model_id:
            raise HarnessError("adapter result changed model_id")
        raw.provider_id = request.provider_id
        raw.model_id = request.model_id
        if any(call.provider != request.provider_id
               for call in raw.model_calls):
            raise HarnessError(
                "adapter result model-call provider does not match provider_id")
        claimed = (
            raw.max_output_tokens_used is not None
            or bool(raw.model_output_limit_source)
            or bool(raw.model_output_limit_reference))
        limit = applied_output_limit
        if limit is not None:
            _required_output_limit(request)
            if limit != request.budget.output_limit:
                raise HarnessError(
                    "adapter applied a different model output maximum")
            if (claimed and (
                    raw.max_output_tokens_used != limit.max_output_tokens
                    or raw.model_output_limit_source != limit.source
                    or raw.model_output_limit_reference != limit.reference)):
                raise HarnessError(
                    "adapter output-limit record contradicts the applied limit")
            raw.max_output_tokens_used = limit.max_output_tokens
            raw.model_output_limit_source = limit.source
            raw.model_output_limit_reference = limit.reference
        elif claimed:
            expected = _required_output_limit(request)
            if (raw.max_output_tokens_used != expected.max_output_tokens
                    or raw.model_output_limit_source != expected.source
                    or raw.model_output_limit_reference != expected.reference):
                raise HarnessError(
                    "injected runner reported a mismatched output limit")
        if prompt_resource is not None:
            raw.prompt_resource_ref = prompt_resource.bundle_ref
            raw.prompt_resource_digest = prompt_resource.bundle_digest
            raw.prompt_slot_schema_digest = prompt_resource.slot_schema_digest
            raw.prompt_render_digest = prompt_resource.render_digest
        return raw
    output = _value(raw, ("final_output", "output", "data", "text"), None)
    if output is None and isinstance(raw, Mapping):
        messages = raw.get("messages") or ()
        if messages:
            output = _value(messages[-1], ("content", "text"), messages[-1])
    if output is None:
        output = raw

    usage = _value(raw, ("usage", "usage_details"), None)
    if usage is None:
        context_wrapper = _value(raw, ("context_wrapper",), None)
        usage = _value(context_wrapper, ("usage",), None)
    input_tokens = _int_value(
        usage, ("input_tokens", "prompt_tokens", "request_tokens",
                "input_token_count"))
    output_tokens = _int_value(
        usage, ("output_tokens", "completion_tokens", "response_tokens",
                "output_token_count"))
    requests = _int_value(
        usage, ("requests", "request_count", "model_requests", "calls"))
    cost = _float_value(usage, ("cost", "total_cost", "cost_usd"))
    message_calls, message_count = _message_usage(raw, request)
    if requests is None and message_count:
        requests = message_count
    calls = tuple(message_calls)
    if requests == 1 and not calls:
        calls = (HarnessModelCall(
            provider=request.provider_id, model=request.model_id, ok=True,
            input_tokens=input_tokens, output_tokens=output_tokens, cost=cost),)
    count_complete = requests is not None
    limit = applied_output_limit
    if limit is not None:
        expected = _required_output_limit(request)
        if limit != expected:
            raise HarnessError(
                "adapter applied a different model output maximum")
    result = HarnessRunResult(
        request_id=request.request_id, harness_id=request.harness_id,
        status="completed", output=output, model_calls=calls,
        adapter_version=adapter_version, provider_id=request.provider_id,
        model_id=request.model_id,
        call_count_complete=count_complete,
        reported_model_call_count=requests,
        aggregate_input_tokens=input_tokens,
        aggregate_output_tokens=output_tokens,
        aggregate_cost=cost,
        max_output_tokens_used=(limit.max_output_tokens if limit else None),
        model_output_limit_source=(limit.source if limit else ""),
        model_output_limit_reference=(limit.reference if limit else ""))
    if prompt_resource is not None:
        result.prompt_resource_ref = prompt_resource.bundle_ref
        result.prompt_resource_digest = prompt_resource.bundle_digest
        result.prompt_slot_schema_digest = prompt_resource.slot_schema_digest
        result.prompt_render_digest = prompt_resource.render_digest
    return result

@dataclass
class ConfiguredHarnessAdapter:
    """Base adapter with an optional injected runner."""

    harness_id: str
    runner: "RunnerFn | None" = None
    adapter_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.harness_id not in _FRAMEWORKS:
            raise ValueError(f"unknown external harness {self.harness_id!r}")

    def info(self) -> HarnessAdapterInfo:
        available, package_version, reason = _package_state(
            self.harness_id, self.runner is not None)
        facts = _FRAMEWORKS[self.harness_id]
        features = tuple(facts["features"])
        limitations = list(facts["limitations"])
        if self.runner is not None:
            features = ("typed_request", "normalized_result",
                        "injected_runner")
            limitations = [
                "an injected runner is application code, not package-backed "
                "runtime integration proof",
                "normalization records an output limit only when the runner "
                "returns a matching typed record",
            ]
        else:
            limitations.append(
                "package detection alone is not package-backed runtime "
                "integration proof")
            if not available:
                limitations.append(
                    "package-backed runtime integration is unproven in this "
                    "installation")
        return HarnessAdapterInfo(
            harness_id=self.harness_id,
            adapter_version=self.adapter_version,
            package_name=facts["package"], package_version=package_version,
            features=features,
            limitations=tuple(limitations), available=available,
            availability_reason=reason)

    def run(self, request: HarnessRunRequest,
            services: HarnessServices) -> HarnessRunResult:
        request = _resolve_output_request(request, services)
        applied_output_limit = None
        prompt_resource = None
        if self.runner is not None:
            raw = self.runner(request, services)
        elif self.harness_id == "pydantic_ai":
            raw = self._run_pydantic(request, services)
        elif self.harness_id == "deep_agents":
            raw = self._run_deep_agents(request, services)
        elif self.harness_id == "openai_agents":
            raw = self._run_openai_agents(request, services)
        else:
            raw = self._run_microsoft(request, services)
        if isinstance(raw, _AdapterExecution):
            applied_output_limit = raw.applied_output_limit
            prompt_resource = raw.prompt_resource
            raw = raw.raw
        return _normalize(
            raw, request, adapter_version=self.adapter_version,
            applied_output_limit=applied_output_limit,
            prompt_resource=prompt_resource)

    @staticmethod
    def _run_pydantic(request: HarnessRunRequest,
                      services: HarnessServices):
        limit = _required_output_limit(request)
        binding = _required_runtime_binding(
            request, services, runtime_kind="model")
        from pydantic_ai import Agent, ModelSettings, UsageLimits

        instruction = _instruction_resource("pydantic_ai")

        agent = Agent(
            binding.runtime_object,
            instructions=instruction.text)
        raw = agent.run_sync(
            _prompt(request),
            model_settings=ModelSettings(
                **_pydantic_model_settings_kwargs(request)),
            usage_limits=UsageLimits(
                **_pydantic_usage_limit_kwargs(request)))
        return _AdapterExecution(raw, limit, instruction)

    @staticmethod
    def _run_deep_agents(request: HarnessRunRequest,
                         services: HarnessServices):
        limit = _required_output_limit(request)
        binding = _required_runtime_binding(
            request, services, runtime_kind="model",
            preconfigured_output_limit=True)
        from deepagents import create_deep_agent

        instruction = _instruction_resource("deep_agents")

        agent = create_deep_agent(
            model=binding.runtime_object,
            tools=[],
            system_prompt=instruction.text,
            subagents=[], skills=[], memory=[], permissions=[],
            checkpointer=False)
        raw = agent.invoke(
            {"messages": [{"role": "user", "content": _prompt(request)}]},
            config=_deep_agents_graph_config(request))
        return _AdapterExecution(raw, limit, instruction)

    @staticmethod
    def _run_openai_agents(request: HarnessRunRequest,
                           services: HarnessServices):
        limit = _required_output_limit(request)
        binding = _required_runtime_binding(
            request, services, runtime_kind="model")
        from agents import Agent, ModelSettings, RunConfig, Runner

        instruction = _instruction_resource("openai_agents")

        agent = Agent(
            name="Loop Engine external specialist",
            instructions=instruction.text,
            model=binding.runtime_object)
        raw = Runner.run_sync(
            agent, _prompt(request), max_turns=request.budget.max_model_calls,
            run_config=RunConfig(
                tracing_disabled=True,
                model_settings=ModelSettings(
                    **_openai_model_settings_kwargs(request))))
        return _AdapterExecution(raw, limit, instruction)

    @staticmethod
    def _run_microsoft(request: HarnessRunRequest,
                       services: HarnessServices):
        limit = _required_output_limit(request)
        binding = _required_runtime_binding(
            request, services, runtime_kind="client")
        from agent_framework import create_harness_agent

        client = binding.runtime_object
        counted_client = PhysicalCallCountingClient(
            client, max_calls=request.budget.max_model_calls)
        agent = create_harness_agent(
            **_microsoft_harness_kwargs(request, counted_client))
        session = agent.create_session()
        run_sync = getattr(agent, "run_sync", None)
        if callable(run_sync):
            response = run_sync(_prompt(request), session=session)
            return _AdapterExecution(
                ConfiguredHarnessAdapter._microsoft_result(
                    response, counted_client), limit)
        value = agent.run(_prompt(request), session=session)
        if inspect.isawaitable(value):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                response = asyncio.run(value)
                return _AdapterExecution(
                    ConfiguredHarnessAdapter._microsoft_result(
                        response, counted_client), limit)
            raise RuntimeError(
                "Microsoft synchronous adapter cannot run inside an active "
                "event loop; inject an async application runner")
        return _AdapterExecution(
            ConfiguredHarnessAdapter._microsoft_result(
                value, counted_client), limit)

    @staticmethod
    def _microsoft_result(response, client):
        usage = getattr(response, "usage_details", None) or {}
        count = None
        for name in ("model_call_count", "call_count", "calls"):
            value = getattr(client, name, None)
            if isinstance(value, int):
                count = value
                break
            if isinstance(value, (list, tuple)):
                count = len(value)
                break
        normalized_usage = dict(usage)
        if count is not None:
            normalized_usage["requests"] = count
        return {"output": getattr(response, "text", response),
                "usage": normalized_usage}

def builtin_harness_adapters(
        runners: "Mapping[str, RunnerFn] | None" = None
        ) -> tuple[ConfiguredHarnessAdapter, ...]:
    """Create all adapters without importing or registering frameworks."""
    supplied = dict(runners or {})
    return tuple(ConfiguredHarnessAdapter(
        harness_id, runner=supplied.get(harness_id))
                 for harness_id in _FRAMEWORKS)

def self_test() -> dict:
    """Run pure adapter-shape checks without an SDK or model invocation."""
    from ..loop.loop_contract import LoopContract
    from .external_harness import (
        HarnessBudget, HarnessError, ModelOutputLimit,
        StaticModelOutputResolver)

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": f"contract_only_{name}",
                      "passed": bool(passed), "detail": detail})

    contract = LoopContract(
        "external", "model_led", input_roles=("problem/v1",),
        output_roles=("answer/v1",))
    request = HarnessRunRequest(
        "contract-shape", "deep_agents", "inspect the selected artifact",
        contract,
        provider_id="ollama_cloud", model_id="configured-model-ref",
        authorize_model_calls=True,
        budget=HarnessBudget(
            max_model_calls=2, max_total_tokens=100),
        metadata={"temperature": 0.2})

    adapters = builtin_harness_adapters()
    check("inventory_has_four_unregistered_optional_adapters",
          len(adapters) == 4
          and {adapter.harness_id for adapter in adapters}
          == set(_FRAMEWORKS))
    infos = {adapter.harness_id: adapter.info() for adapter in adapters}
    check("inventory_lists_only_features_wired_by_each_adapter",
          all(infos[name].features == tuple(facts["features"])
              for name, facts in _FRAMEWORKS.items())
          and "mcp" not in infos["openai_agents"].features
          and "skills" not in infos["microsoft_agent_framework"].features)
    check("package_detection_is_not_reported_as_runtime_integration_proof",
          all(any("not package-backed runtime integration proof" in item
                  for item in info.limitations)
              for info in infos.values())
          and all(info.available or any(
              "runtime integration is unproven" in item
              for item in info.limitations)
              for info in infos.values()))
    check("prompt_contains_contract_without_acceptance_claim",
          "not claim verification or acceptance" in _prompt(request)
          and "answer/v1" in _prompt(request))

    normalized = _normalize({
        "output": {"answer": 1},
        "usage": {"requests": 1, "input_tokens": 9,
                  "output_tokens": 4, "cost": 0.001}},
        request, adapter_version="contract")
    check("provider_neutral_fields_keep_declared_usage",
          normalized.physical_model_calls == 1
          and normalized.total_tokens == 13
          and normalized.total_cost == 0.001
          and normalized.provider_id == "ollama_cloud"
          and normalized.model_id == "configured-model-ref"
          and normalized.model_calls[0].provider == "ollama_cloud"
          and normalized.model_calls[0].provider != request.harness_id
          and normalized.max_output_tokens_used is None)

    instruction = _instruction_resource("deep_agents")
    prompt_bound = _normalize({
        "output": {"answer": 1},
        "usage": {"requests": 1, "input_tokens": 9,
                  "output_tokens": 4}},
        request, adapter_version="contract",
        prompt_resource=instruction)
    check("versioned_prompt_resource_identity_reaches_safe_result",
          prompt_bound.prompt_resource_ref == instruction.bundle_ref
          and prompt_bound.prompt_resource_digest == instruction.bundle_digest
          and prompt_bound.prompt_slot_schema_digest
              == instruction.slot_schema_digest
          and prompt_bound.prompt_render_digest == instruction.render_digest
          and "text" not in prompt_bound.safe_summary())

    unknown = _normalize(
        {"output": {"answer": 1}}, request,
        adapter_version="contract")
    check("missing_usage_is_incomplete_not_zero",
          unknown.physical_model_calls is None
          and not unknown.call_count_complete
          and unknown.total_tokens is None)

    check("unresolved_output_maximum_is_not_reported_as_applied",
          request.budget.max_output_tokens is None
          and normalized.max_output_tokens_used is None)

    limit = ModelOutputLimit(
        65536, "endpoint_observed",
        "ollama-openai-error:deepseek-v4-flash:0731",
        provider_id="ollama_cloud",
        model_id="configured-model-ref")
    resolved = _resolve_output_request(
        request, HarnessServices(model_output_resolver=
                                 StaticModelOutputResolver((limit,))))
    check("typed_capability_resolves_exact_output_maximum",
          resolved.budget.max_output_tokens == 65536
          and resolved.budget.output_limit.reference == limit.reference)
    not_applied = _normalize(
        {"output": {"answer": 1},
         "usage": {"requests": 1, "input_tokens": 1,
                   "output_tokens": 1}},
        resolved, adapter_version="contract")
    applied = _normalize(
        {"output": {"answer": 1},
         "usage": {"requests": 1, "input_tokens": 1,
                   "output_tokens": 1}},
        resolved, adapter_version="contract", applied_output_limit=limit)
    check("normalization_reports_maximum_only_after_adapter_application",
          not_applied.max_output_tokens_used is None
          and not not_applied.model_output_limit_source
          and applied.max_output_tokens_used == 65536
          and applied.model_output_limit_source == "endpoint_observed"
          and applied.model_output_limit_reference == limit.reference)

    injected_seen = []

    def injected_runner(active_request, active_services):
        injected_seen.append(active_request.budget.max_output_tokens)
        return {"output": {"answer": 1},
                "usage": {"requests": 1, "input_tokens": 1,
                          "output_tokens": 1}}

    injected = ConfiguredHarnessAdapter(
        "deep_agents", runner=injected_runner)
    injected_result = injected.run(
        request, HarnessServices(model_output_resolver=
                                 StaticModelOutputResolver((limit,))))
    check("injected_runner_receives_exact_limit_without_automatic_claim",
          injected_seen == [65536]
          and injected_result.max_output_tokens_used is None
          and injected.info().features[-1] == "injected_runner")

    model_binding = HarnessRuntimeBinding(
        "ollama_cloud", "configured-model-ref", "model", object(),
        "settings:ollama-cloud")
    bound_services = HarnessServices(runtime_binding=model_binding)
    binding_ok = _required_runtime_binding(
        resolved, bound_services, runtime_kind="model")
    check("provider_bound_model_is_required_before_package_import",
          binding_ok is model_binding)

    missing_binding_refused = deep_unbound_refused = False
    try:
        _required_runtime_binding(
            resolved, HarnessServices(), runtime_kind="model")
    except HarnessError:
        missing_binding_refused = True
    try:
        _required_runtime_binding(
            resolved, bound_services, runtime_kind="model",
            preconfigured_output_limit=True)
    except HarnessError:
        deep_unbound_refused = True
    check("missing_provider_binding_fails_before_package_import",
          missing_binding_refused)
    check("deep_agents_requires_a_preconfigured_exact_output_maximum",
          deep_unbound_refused)
    deep_binding = HarnessRuntimeBinding(
        "ollama_cloud", "configured-model-ref", "model", object(),
        "settings:ollama-cloud-max-output", output_limit=limit)
    check("deep_agents_accepts_only_the_matching_preconfigured_limit",
          _required_runtime_binding(
              resolved, HarnessServices(runtime_binding=deep_binding),
              runtime_kind="model", preconfigured_output_limit=True)
          is deep_binding)

    openai_settings = _openai_model_settings_kwargs(resolved)
    check("openai_adapter_passes_exact_maximum_to_ModelSettings",
          openai_settings["max_tokens"] == 65536
          and openai_settings["include_usage"] is True)
    check("pydantic_adapter_passes_exact_maximum_and_request_budget",
          _pydantic_model_settings_kwargs(resolved)["max_tokens"] == 65536
          and _pydantic_usage_limit_kwargs(resolved)["request_limit"] == 2
          and _pydantic_usage_limit_kwargs(
              resolved)["total_tokens_limit"] == 100)
    check("deep_agents_graph_recursion_is_bounded",
          _deep_agents_graph_config(resolved)["recursion_limit"] == 10)

    class ProviderBoundaryContract:
        additional_properties = {"contract": True}

        def get_response(self, value, **kwargs):
            return value, kwargs

    counted = PhysicalCallCountingClient(
        ProviderBoundaryContract(), max_calls=2)
    microsoft_settings = _microsoft_harness_kwargs(resolved, counted)
    check("microsoft_adapter_passes_exact_maximum_to_harness_boundary",
          microsoft_settings["max_output_tokens"] == 65536
          and microsoft_settings["client"] is counted
          and microsoft_settings["disable_web_search"] is True
          and microsoft_settings["disable_file_memory"] is True
          and microsoft_settings["disable_compaction"] is True
          and microsoft_settings["disable_todo"] is True
          and microsoft_settings["disable_mode"] is True
          and microsoft_settings["disable_tool_auto_approval"] is True)
    first_value = counted.get_response("one", stream=False)
    second_value = counted.get_response("two", stream=False)
    budget_refused = False
    try:
        counted.get_response("three", stream=False)
    except HarnessError:
        budget_refused = True
    check("physical_call_decorator_counts_the_sdk_request_boundary",
          counted.call_count == 2
          and first_value[0] == "one" and second_value[0] == "two"
          and counted.additional_properties == {"contract": True}
          and budget_refused)

    bad_cap_refused = False
    try:
        ModelOutputLimit(0, "provider_declared", "invalid")
    except HarnessError:
        bad_cap_refused = True
    check("invalid_output_cap_is_refused", bad_cap_refused)

    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
