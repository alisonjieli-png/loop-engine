"""Typed boundary for optional external agent harnesses.

Loop Engine keeps goal, mode, authority, intelligence, evaluation, and run
history ownership. An adapter may supply commodity agent mechanics such as
subagents, context compression, skills, MCP, or a sandbox. The adapter always
runs inside one Loop and returns one provider-neutral result.

This module defines contracts and offline enforcement. Framework-specific
imports live in separate adapter modules and remain optional dependencies.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field, replace
from typing import Mapping, Protocol, Sequence, TYPE_CHECKING

from ..loop.loop_contract import LoopContract

if TYPE_CHECKING:
    from .context_artifacts import ContextArtifactManager


HARNESS_IDS = (
    "pydantic_ai", "deep_agents", "openai_agents",
    "microsoft_agent_framework", "opencode")
HARNESS_MODES = ("hybrid", "non_deterministic")
HARNESS_STATUSES = (
    "completed", "failed", "unavailable", "refused", "cancelled",
    "budget_exhausted")
CONTEXT_VISIBILITY = (
    "fresh", "selected_refs", "shared_runtime_memory", "summary_return")


class HarnessError(RuntimeError):
    """An external harness request or adapter violated its contract."""


@dataclass(frozen=True)
class ModelOutputLimit:
    """Exact provider or endpoint maximum with its source reference."""

    max_output_tokens: int
    source: str
    reference: str
    provider_id: str = ""
    model_id: str = ""
    route_id: str = ""

    def __post_init__(self) -> None:
        if self.max_output_tokens < 1:
            raise HarnessError("resolved model output maximum must be positive")
        if self.source not in (
                "provider_declared", "provider_catalog",
                "endpoint_observed", "custom_endpoint_declared"):
            raise HarnessError("unknown model output maximum source")
        if not self.reference.strip():
            raise HarnessError("model output maximum needs a source reference")
        if not self.provider_id.strip() or not self.model_id.strip():
            raise HarnessError(
                "model output maximum needs exact provider_id and model_id")


@dataclass(frozen=True)
class HarnessBudget:
    """Hard physical limits declared before an external harness run."""

    max_model_calls: int
    max_total_tokens: "int | None" = None
    max_cost: "float | None" = None
    max_seconds: "float | None" = None
    max_spawned_tasks: "int | None" = None
    output_limit: "ModelOutputLimit | None" = None

    def __post_init__(self) -> None:
        if self.max_model_calls < 1:
            raise HarnessError("max_model_calls must be positive")
        for field_name in ("max_total_tokens", "max_cost", "max_seconds"):
            value = getattr(self, field_name)
            if value is not None and value <= 0:
                raise HarnessError(f"{field_name} must be positive when set")
        if (self.max_spawned_tasks is not None
                and self.max_spawned_tasks < 0):
            raise HarnessError("max_spawned_tasks cannot be negative")
        if (self.output_limit is not None
                and not isinstance(self.output_limit, ModelOutputLimit)):
            raise HarnessError("output_limit must be ModelOutputLimit")

    @property
    def max_output_tokens(self) -> "int | None":
        return (self.output_limit.max_output_tokens
                if self.output_limit is not None else None)


@dataclass(frozen=True)
class HarnessRunRequest:
    """One fully bounded request passed to an external harness adapter."""

    request_id: str
    harness_id: str
    goal: str
    contract: LoopContract
    budget: HarnessBudget
    mode: str = "non_deterministic"
    llm_thinking_power: str = "medium"
    profile_id: str = "practitioner.solver"
    profile_version: str = "1.0.0"
    input_data: Mapping[str, object] = field(default_factory=dict)
    context_refs: tuple[str, ...] = ()
    context_visibility: str = "selected_refs"
    tool_refs: tuple[str, ...] = ()
    skill_refs: tuple[str, ...] = ()
    provider_id: str = ""
    model_id: str = ""
    model_routes: tuple[str, ...] = ()
    workspace_ref: str = ""
    approval_policy_ref: str = ""
    authorize_model_calls: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id or not self.goal.strip():
            raise HarnessError("a harness request needs request_id and goal")
        if self.harness_id not in HARNESS_IDS:
            raise HarnessError(f"harness_id must be one of {HARNESS_IDS}")
        if self.mode not in HARNESS_MODES:
            raise HarnessError(
                "external LLM harnesses run only in hybrid or "
                "non_deterministic mode")
        if not isinstance(self.contract, LoopContract):
            raise HarnessError("contract must be a LoopContract")
        allowed_contract_modes = {
            "hybrid": ("hybrid", "model_led"),
            "non_deterministic": ("model_led",),
        }[self.mode]
        if self.contract.execution_mode not in allowed_contract_modes:
            raise HarnessError(
                f"{self.mode} request cannot use contract mode "
                f"{self.contract.execution_mode!r}")
        if self.llm_thinking_power not in (
                "small", "medium", "high", "max", "specialized"):
            raise HarnessError(
                "llm_thinking_power must be small, medium, high, max, or "
                "specialized")
        if self.context_visibility not in CONTEXT_VISIBILITY:
            raise HarnessError(
                f"context_visibility must be one of {CONTEXT_VISIBILITY}")
        if not self.provider_id.strip() or not self.model_id.strip():
            raise HarnessError(
                "external harness requests need exact provider_id and model_id")
        if not self.authorize_model_calls:
            raise HarnessError(
                "external harness requests require authorize_model_calls=True")
        for field_name in ("context_refs", "tool_refs", "skill_refs",
                           "model_routes"):
            values = tuple(getattr(self, field_name))
            if any(not isinstance(value, str) or not value.strip()
                   for value in values):
                raise HarnessError(
                    f"{field_name} must contain non-empty references")
            if len(values) != len(set(values)):
                raise HarnessError(f"{field_name} cannot contain duplicates")
            object.__setattr__(self, field_name, values)
        credential_names = (
            "api_key", "access_token", "bearer_token", "refresh_token",
            "password", "secret", "client_secret", "token")
        secret_keys = []
        for key in self.metadata:
            normalized = str(key).lower().replace("-", "_")
            if any(normalized == name or normalized.endswith(f"_{name}")
                   for name in credential_names):
                secret_keys.append(key)
        if secret_keys:
            raise HarnessError(
                f"metadata contains secret-shaped keys {secret_keys}; pass "
                "credential references through configured services")

    @property
    def digest(self) -> str:
        safe = {
            "request_id": self.request_id,
            "harness_id": self.harness_id,
            "goal": self.goal,
            "contract": self.contract.name,
            "mode": self.mode,
            "thinking_power": self.llm_thinking_power,
            "profile": f"{self.profile_id}@{self.profile_version}",
            "context_refs": self.context_refs,
            "tool_refs": self.tool_refs,
            "skill_refs": self.skill_refs,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "model_routes": self.model_routes,
            "workspace_ref": self.workspace_ref,
            "approval_policy_ref": self.approval_policy_ref,
            "budget": asdict(self.budget),
            "input_data": dict(self.input_data),
            "metadata": dict(self.metadata),
        }
        return hashlib.sha256(json.dumps(
            safe, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class HarnessModelCall:
    """One physical model attempt reported by an external harness."""

    provider: str
    model: str
    ok: bool
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    cost: "float | None" = None
    error_code: str = ""
    elapsed_seconds: "float | None" = None

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip():
            raise HarnessError("model-call records need provider and model")
        if self.provider in HARNESS_IDS:
            raise HarnessError(
                "model-call provider must name the provider, not the harness")

    @property
    def total_tokens(self) -> "int | None":
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class HarnessToolEvent:
    """One normalized tool event without unbounded tool output."""

    tool_name: str
    status: str
    effect: str = "pure"
    input_digest: str = ""
    output_ref: str = ""
    approval_id: str = ""
    elapsed_seconds: "float | None" = None


@dataclass(frozen=True)
class HarnessArtifactRef:
    """A generated artifact kept outside the model context."""

    artifact_id: str
    uri: str
    digest: str
    media_type: str = "application/octet-stream"
    size_bytes: "int | None" = None


@dataclass
class HarnessRunResult:
    """Provider-neutral external run result. Completion is not acceptance."""

    request_id: str
    harness_id: str
    status: str
    output: object = None
    error_code: str = ""
    error: str = ""
    model_calls: tuple[HarnessModelCall, ...] = ()
    tool_events: tuple[HarnessToolEvent, ...] = ()
    artifacts: tuple[HarnessArtifactRef, ...] = ()
    spawned_task_ids: tuple[str, ...] = ()
    checkpoint_ref: str = ""
    trace_ref: str = ""
    raw_events_ref: str = ""
    elapsed_seconds: "float | None" = None
    adapter_version: str = ""
    provider_id: str = ""
    model_id: str = ""
    loop_id: str = ""
    call_count_complete: bool = True
    reported_model_call_count: "int | None" = None
    aggregate_input_tokens: "int | None" = None
    aggregate_output_tokens: "int | None" = None
    aggregate_cost: "float | None" = None
    max_output_tokens_used: "int | None" = None
    model_output_limit_source: str = ""
    model_output_limit_reference: str = ""
    prompt_resource_ref: str = ""
    prompt_resource_digest: str = ""
    prompt_slot_schema_digest: str = ""
    prompt_render_digest: str = ""

    def __post_init__(self) -> None:
        if self.status not in HARNESS_STATUSES:
            raise HarnessError(f"status must be one of {HARNESS_STATUSES}")
        if not self.request_id or self.harness_id not in HARNESS_IDS:
            raise HarnessError("result needs a valid request and harness id")
        if bool(self.provider_id) != bool(self.model_id):
            raise HarnessError(
                "result provider_id and model_id must be present together")
        if self.provider_id in HARNESS_IDS:
            raise HarnessError(
                "result provider_id must name the provider, not the harness")
        self.model_calls = tuple(self.model_calls)
        self.tool_events = tuple(self.tool_events)
        self.artifacts = tuple(self.artifacts)
        self.spawned_task_ids = tuple(self.spawned_task_ids)
        if self.reported_model_call_count is None and self.call_count_complete:
            self.reported_model_call_count = len(self.model_calls)
        if (self.reported_model_call_count is not None
                and self.reported_model_call_count < len(self.model_calls)):
            raise HarnessError(
                "reported_model_call_count cannot be below detailed calls")

    @property
    def completed(self) -> bool:
        return self.status == "completed"

    @property
    def accounting_complete(self) -> bool:
        aggregate_known = (self.aggregate_input_tokens is not None
                           and self.aggregate_output_tokens is not None)
        detailed_known = (
            self.physical_model_calls == len(self.model_calls)
            and all(call.total_tokens is not None for call in self.model_calls))
        return aggregate_known or detailed_known

    @property
    def total_tokens(self) -> "int | None":
        if (self.aggregate_input_tokens is not None
                and self.aggregate_output_tokens is not None):
            return self.aggregate_input_tokens + self.aggregate_output_tokens
        if not self.accounting_complete:
            return None
        return sum(call.total_tokens or 0 for call in self.model_calls)

    @property
    def total_cost(self) -> "float | None":
        if self.aggregate_cost is not None:
            return self.aggregate_cost
        if (self.physical_model_calls != len(self.model_calls)
                or any(call.cost is None for call in self.model_calls)):
            return None
        return sum(call.cost or 0.0 for call in self.model_calls)

    @property
    def physical_model_calls(self) -> "int | None":
        return self.reported_model_call_count

    def safe_summary(self) -> dict:
        return {
            "record_type": "external_harness_result/v2",
            "request_id": self.request_id,
            "harness_id": self.harness_id,
            "status": self.status,
            "completed": self.completed,
            "acceptance": "not_evaluated",
            "physical_model_calls": self.physical_model_calls,
            "detailed_model_calls": len(self.model_calls),
            "call_count_complete": self.call_count_complete,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "accounting_complete": self.accounting_complete,
            "aggregate_input_tokens": self.aggregate_input_tokens,
            "aggregate_output_tokens": self.aggregate_output_tokens,
            "tool_events": len(self.tool_events),
            "artifacts": [artifact.artifact_id for artifact in self.artifacts],
            "spawned_task_ids": list(self.spawned_task_ids),
            "checkpoint_ref": self.checkpoint_ref,
            "trace_ref": self.trace_ref,
            "raw_events_ref": self.raw_events_ref,
            "elapsed_seconds": self.elapsed_seconds,
            "adapter_version": self.adapter_version,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "max_output_tokens_used": self.max_output_tokens_used,
            "model_output_limit_source": self.model_output_limit_source,
            "model_output_limit_reference": self.model_output_limit_reference,
            "prompt_resource_ref": self.prompt_resource_ref,
            "prompt_resource_digest": self.prompt_resource_digest,
            "prompt_slot_schema_digest": self.prompt_slot_schema_digest,
            "prompt_render_digest": self.prompt_render_digest,
            "loop_id": self.loop_id,
            "error_code": self.error_code,
            "error": self.error[:200],
        }


@dataclass(frozen=True)
class HarnessAdapterInfo:
    harness_id: str
    adapter_version: str
    package_name: str
    package_version: str = ""
    features: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    available: bool = False
    availability_reason: str = ""

    def __post_init__(self) -> None:
        if self.harness_id not in HARNESS_IDS:
            raise HarnessError(f"harness_id must be one of {HARNESS_IDS}")


@dataclass(frozen=True)
class HarnessRuntimeBinding:
    """Provider-bound runtime object supplied to one optional harness.

    The binding prevents an adapter from treating a model name as sufficient
    provider configuration.  ``runtime_object`` is an SDK model or client that
    application code configured outside Loop Engine.  ``configuration_ref``
    is a non-secret reference to that reviewed configuration.

    Deep Agents cannot apply a per-run output maximum at its graph boundary,
    so its model binding must carry the exact already-applied output limit.
    Other adapters apply the resolved limit themselves and may leave
    ``output_limit`` empty.
    """

    provider_id: str
    model_id: str
    runtime_kind: str
    runtime_object: object
    configuration_ref: str
    output_limit: "ModelOutputLimit | None" = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.model_id.strip():
            raise HarnessError(
                "a harness runtime binding needs provider_id and model_id")
        if self.runtime_kind not in ("model", "client"):
            raise HarnessError("runtime_kind must be model or client")
        if self.runtime_object is None:
            raise HarnessError("a harness runtime binding needs an SDK object")
        if not self.configuration_ref.strip():
            raise HarnessError(
                "a harness runtime binding needs a non-secret configuration reference")
        if self.output_limit is not None:
            _validate_output_limit_binding_fields(
                self.provider_id, self.model_id, self.output_limit)

    def validate_for(self, request: HarnessRunRequest, *,
                     runtime_kind: str,
                     preconfigured_output_limit: bool = False) -> None:
        if self.provider_id != request.provider_id:
            raise HarnessError(
                "harness runtime binding provider does not match the request")
        if self.model_id != request.model_id:
            raise HarnessError(
                "harness runtime binding model does not match the request")
        if self.runtime_kind != runtime_kind:
            raise HarnessError(
                f"harness runtime binding must contain an SDK {runtime_kind}")
        if self.output_limit is not None:
            if self.output_limit != request.budget.output_limit:
                raise HarnessError(
                    "harness runtime binding output maximum does not match the request")
        elif preconfigured_output_limit:
            raise HarnessError(
                "this harness needs a model binding with the exact output maximum already applied")


@dataclass(frozen=True)
class HarnessServices:
    """Run-scoped services passed as one object to every adapter."""

    runtime_binding: "HarnessRuntimeBinding | None" = None
    artifact_store: "ContextArtifactManager | None" = None
    model_output_resolver: object = None

    def __post_init__(self) -> None:
        if (self.runtime_binding is not None
                and not isinstance(self.runtime_binding,
                                   HarnessRuntimeBinding)):
            raise HarnessError(
                "runtime_binding must be a HarnessRuntimeBinding")
        if self.artifact_store is not None:
            from .context_artifacts import ContextArtifactManager
            if not isinstance(self.artifact_store, ContextArtifactManager):
                raise HarnessError(
                    "artifact_store must be a ContextArtifactManager")


class ModelOutputResolver(Protocol):
    def resolve(self, request: HarnessRunRequest) -> "ModelOutputLimit | None": ...


@dataclass(frozen=True)
class StaticModelOutputResolver:
    """Resolve exact model maxima from reviewed capability records."""

    limits: tuple[ModelOutputLimit, ...]

    def resolve(self, request: HarnessRunRequest) -> "ModelOutputLimit | None":
        for limit in self.limits:
            provider_matches = limit.provider_id == request.provider_id
            model_matches = limit.model_id == request.model_id
            route_matches = (not limit.route_id
                             or limit.route_id in request.model_routes)
            if provider_matches and model_matches and route_matches:
                return limit
        return None


def _validate_output_limit_binding(
        request: HarnessRunRequest, limit: ModelOutputLimit) -> None:
    _validate_output_limit_binding_fields(
        request.provider_id, request.model_id, limit)
    if limit.route_id and limit.route_id not in request.model_routes:
        raise HarnessError(
            "model output maximum route does not match the request")


def _validate_output_limit_binding_fields(
        provider_id: str, model_id: str, limit: ModelOutputLimit) -> None:
    if limit.provider_id != provider_id:
        raise HarnessError(
            "model output maximum provider does not match the request")
    if limit.model_id != model_id:
        raise HarnessError(
            "model output maximum model does not match the request")


def resolve_harness_output_limit(
        request: HarnessRunRequest,
        services: "HarnessServices | None" = None) -> HarnessRunRequest:
    """Resolve the exact provider maximum before creating the run identity."""
    if request.budget.output_limit is not None:
        _validate_output_limit_binding(request, request.budget.output_limit)
        return request
    active = services or HarnessServices()
    resolver = active.model_output_resolver
    if resolver is None or not callable(getattr(resolver, "resolve", None)):
        raise HarnessError(
            "external harness needs a typed model output capability resolver")
    limit = resolver.resolve(request)
    if limit is None:
        raise HarnessError(
            "no exact provider output maximum matches this model and route")
    _validate_output_limit_binding(request, limit)
    return replace(
        request, budget=replace(request.budget, output_limit=limit))


class ExternalHarnessAdapter(Protocol):
    def info(self) -> HarnessAdapterInfo: ...
    def run(self, request: HarnessRunRequest,
            services: HarnessServices) -> HarnessRunResult: ...


class HarnessRegistry:
    """Explicit adapter registry. Importing an adapter registers nothing."""

    def __init__(self, adapters: Sequence[ExternalHarnessAdapter] = ()):
        self._adapters: dict[str, ExternalHarnessAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: ExternalHarnessAdapter, *,
                 replace: bool = False) -> None:
        info = adapter.info()
        if info.harness_id in self._adapters and not replace:
            raise HarnessError(
                f"adapter {info.harness_id!r} is already registered")
        self._adapters[info.harness_id] = adapter

    def get(self, harness_id: str) -> ExternalHarnessAdapter:
        if harness_id not in self._adapters:
            raise HarnessError(
                f"no adapter {harness_id!r}; have {sorted(self._adapters)}")
        return self._adapters[harness_id]

    def inventory(self) -> tuple[HarnessAdapterInfo, ...]:
        return tuple(self._adapters[name].info()
                     for name in sorted(self._adapters))


def _budget_failure(request: HarnessRunRequest,
                    result: HarnessRunResult) -> "str | None":
    if not result.call_count_complete:
        return "model_call_accounting_incomplete"
    if result.completed and not result.physical_model_calls:
        return "no_reported_model_call"
    if ((result.physical_model_calls or 0)
            > request.budget.max_model_calls):
        return "model_call_budget_exhausted"
    if (request.budget.max_total_tokens is not None
            and not result.accounting_complete):
        return "token_accounting_incomplete"
    if (request.budget.max_total_tokens is not None
            and result.total_tokens is not None
            and result.total_tokens > request.budget.max_total_tokens):
        return "token_budget_exhausted"
    if (request.budget.max_cost is not None
            and result.total_cost is None):
        return "cost_accounting_incomplete"
    if (request.budget.max_cost is not None
            and result.total_cost is not None
            and result.total_cost > request.budget.max_cost):
        return "cost_budget_exhausted"
    if (request.budget.max_seconds is not None
            and result.elapsed_seconds is not None
            and result.elapsed_seconds > request.budget.max_seconds):
        return "time_budget_exhausted"
    if (request.budget.max_spawned_tasks is not None
            and len(result.spawned_task_ids)
            > request.budget.max_spawned_tasks):
        return "spawned_task_budget_exhausted"
    return None


def _serialize_harness_output(value: object) -> tuple[str, str]:
    """Return one deterministic text body for ContextArtifactManager."""
    if isinstance(value, str):
        return value, "text/plain"
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        value = model_dump(mode="json")
    try:
        text = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HarnessError(
            "external harness output is not text or JSON-compatible") from exc
    return text, "application/json"


def _capture_harness_output(
        result: HarnessRunResult,
        manager: "ContextArtifactManager") -> None:
    """Store raw output first, then keep inline data or publish only its ref."""
    if result.output is None:
        return
    if isinstance(result.output, HarnessArtifactRef):
        from .context_artifacts import ContextArtifactRef
        stored = ContextArtifactRef(
            result.output.digest, result.output.size_bytes or 0,
            media_type=result.output.media_type,
            artifact_kind="external_harness_output")
        manager.store.get(stored)
        if result.output.uri != stored.object_key:
            raise HarnessError(
                "external harness artifact URI does not match its digest")
        if result.output not in result.artifacts:
            result.artifacts = (*result.artifacts, result.output)
        return
    body, media_type = _serialize_harness_output(result.output)
    payload = manager.capture(
        body, media_type=media_type,
        artifact_kind="external_harness_output")
    reference = HarnessArtifactRef(
        artifact_id=f"context-output:{payload.raw.digest}",
        uri=payload.raw.object_key,
        digest=payload.raw.digest,
        media_type=payload.raw.media_type,
        size_bytes=payload.raw.byte_count)
    if all(item.digest != reference.digest for item in result.artifacts):
        result.artifacts = (*result.artifacts, reference)
    if payload.offloaded:
        result.output = reference


def run_external_harness(
        adapter: ExternalHarnessAdapter, request: HarnessRunRequest, *,
        services: "HarnessServices | None" = None, parent=None, ledger=None
        ) -> HarnessRunResult:
    """Run one external harness inside one Loop and import bounded events."""
    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome

    active_services = services or HarnessServices()
    info = adapter.info()
    if info.harness_id != request.harness_id:
        raise HarnessError(
            f"adapter {info.harness_id!r} cannot run {request.harness_id!r}")
    if not info.available:
        return HarnessRunResult(
            request.request_id, request.harness_id, "unavailable",
            error_code="adapter_unavailable",
            error=info.availability_reason,
            adapter_version=info.adapter_version,
            provider_id=request.provider_id, model_id=request.model_id)
    if active_services.artifact_store is None:
        return HarnessRunResult(
            request.request_id, request.harness_id, "refused",
            error_code="context_artifact_manager_required",
            error=("an available external harness needs a typed "
                   "ContextArtifactManager before execution"),
            adapter_version=info.adapter_version,
            provider_id=request.provider_id, model_id=request.model_id)
    request = resolve_harness_output_limit(request, active_services)

    config = LoopConfig(
        framework="custom", custom_steps=("run_external_harness",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        allowable_modes=(request.mode,), preferred_modes=(request.mode,),
        delegated_modes=("deterministic", *HARNESS_MODES),
        power="standard", llm_thinking_power=request.llm_thinking_power,
        max_depth=3, exit_condition="accepted_success")
    loop = (parent.spawn(request.goal, config, contract=request.contract)
            if parent is not None else Loop(
                request.goal, config, ledger=ledger,
                contract=request.contract))
    holder: dict[str, HarnessRunResult] = {}
    started = time.monotonic()

    def handler(active_loop, step, context):
        try:
            result = adapter.run(request, active_services)
        except Exception as exc:
            result = HarnessRunResult(
                request.request_id, request.harness_id, "failed",
                error_code="adapter_exception",
                error=f"{type(exc).__name__}: {str(exc)[:160]}",
                adapter_version=info.adapter_version,
                provider_id=request.provider_id, model_id=request.model_id)
        if result.request_id != request.request_id:
            raise HarnessError("adapter changed request_id")
        if result.harness_id != request.harness_id:
            raise HarnessError("adapter changed harness_id")
        if result.provider_id and result.provider_id != request.provider_id:
            raise HarnessError("adapter changed provider_id")
        if result.model_id and result.model_id != request.model_id:
            raise HarnessError("adapter changed model_id")
        result.provider_id = request.provider_id
        result.model_id = request.model_id
        if any(call.provider != request.provider_id
               for call in result.model_calls):
            raise HarnessError(
                "adapter model-call provider does not match provider_id")
        try:
            _capture_harness_output(result, active_services.artifact_store)
        except Exception as exc:
            result.status = "failed"
            result.error_code = "output_capture_failed"
            result.error = f"{type(exc).__name__}: {str(exc)[:160]}"
            result.output = None
        elapsed = result.elapsed_seconds
        if elapsed is None:
            elapsed = round(time.monotonic() - started, 6)
            result.elapsed_seconds = elapsed
        exceeded = _budget_failure(request, result)
        if exceeded:
            result.status = "budget_exhausted"
            result.error_code = exceeded
            result.error = "external harness exceeded a declared hard budget"
        holder["result"] = result
        for call in result.model_calls:
            event = {
                "loop_id": active_loop.loop_id,
                "event": "model_led" if call.ok
                else "model_invocation_failed",
                "provider": call.provider,
                "model": call.model,
                "usage_known": call.total_tokens is not None,
            }
            if call.input_tokens is not None:
                event["prompt_tokens"] = call.input_tokens
            if call.output_tokens is not None:
                event["eval_tokens"] = call.output_tokens
            active_loop.ledger.record(**event)
        missing_call_details = ((result.physical_model_calls or 0)
                                - len(result.model_calls))
        for _index in range(max(0, missing_call_details)):
            active_loop.ledger.record(
                loop_id=active_loop.loop_id, event="model_led",
                provider=request.provider_id, model=request.model_id,
                usage_known=False, imported_without_call_detail=True)
        active_loop.ledger.record(
            loop_id=active_loop.loop_id, event="custom",
            external_harness_result=result.safe_summary(),
            request_digest=request.digest)
        return StepOutcome(
            output=f"external_harness:{result.status}", mode=request.mode,
            confidence=0.8 if result.completed else 0.1,
            failed=not result.completed)

    # One Loop invocation owns one physical adapter invocation. Retrying the
    # step here can repeat model calls or committed tool effects inside the
    # external harness while returning only the last attempt's accounting.
    # Retry and repair need a new, explicitly budgeted spawned Loop.
    loop.run(handler=handler, max_steps=1)
    result = holder.get("result") or HarnessRunResult(
        request.request_id, request.harness_id, "failed",
        error_code="missing_adapter_result", adapter_version=info.adapter_version,
        provider_id=request.provider_id, model_id=request.model_id)
    result.loop_id = loop.loop_id
    return result



def self_test() -> dict:
    """Run focused offline checks without a package or provider call."""
    from .external_harness_checks import run_checks
    return run_checks()
