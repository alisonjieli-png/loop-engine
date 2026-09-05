"""Passive capability facts and requirements for optional harness realizations.

Identifiers select explicitly supplied adapters, never imports or executable
behavior. Declared support is not independent qualification. Limit enforcement
means prevention before the effect; post-run accounting is a different fact.
"""
from __future__ import annotations

import re
import math
from dataclasses import asdict, dataclass
from types import MappingProxyType


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
ISOLATIONS = ("unverified", "none", "cwd_only", "os_sandbox", "container", "remote")
LIMITS = ("model_calls", "total_tokens", "cost", "wall_time", "maximum_output", "spawned_tasks")

SDK_FRAMEWORKS = {
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


def valid_harness_id(value: object) -> bool:
    return type(value) is str and bool(_IDENTIFIER.fullmatch(value))


def validate_harness_strings(record, required, optional=()):
    for name in (*required, *optional):
        value = getattr(record, name)
        if type(value) is not str or (name in required and not value.strip()):
            raise ValueError("invalid harness string field")
        value.encode("utf-8")


def freeze_adapter_info(info):
    if type(info.available) is not bool:
        raise ValueError("adapter availability must be Boolean")
    for field in ("features", "limitations"):
        values = getattr(info, field)
        if type(values) not in (list, tuple) or any(type(v) is not str for v in values):
            raise ValueError("adapter descriptions must be string sequences")
        object.__setattr__(info, field, tuple(values))


def safe_harness_error_code(value):
    """Only boundary-defined categories may enter the public event summary."""
    known = {
        "adapter_unavailable", "context_artifact_manager_required", "adapter_exception",
        "output_capture_failed", "missing_adapter_result", "no_reported_model_call",
        "model_call_accounting_incomplete", "token_accounting_incomplete",
        "cost_accounting_incomplete", "model_call_budget_exhausted",
        "token_budget_exhausted", "cost_budget_exhausted", "time_budget_exhausted",
        "spawned_task_budget_exhausted", "harness_capability_requirement_unsatisfied",
        "opencode_execution_profile_unqualified", "adapter_reported_failure",
    }
    if type(value) is str and value in known:
        return value
    return "adapter_reported_failure" if value else ""


def valid_number(value, *, integer=False, positive=False) -> bool:
    if integer:
        return type(value) is int and (value > 0 if positive else value >= 0)
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        return False


def harness_loop_identity(request):
    """Resolve the caller's exact existing Practitioner profile."""
    from ..loop.loop_profile_catalog import LoopProfileRef
    from ..loop.loop_profile_ontology import get_profile
    from ..loop.loop_role import LoopRoleIdentity
    profile = get_profile(LoopProfileRef(request.profile_id, request.profile_version))
    if profile.family != "practitioner":
        raise ValueError("external harness entry requires a Practitioner profile")
    return LoopRoleIdentity(profile.family, profile.profile_id, profile.version)


def plain_harness_json(value, ancestors=None):
    """Detach finite JSON data without invoking opaque-object conversion hooks."""
    if type(value) is str:
        value.encode("utf-8")
        return value
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) not in (dict, list, tuple, MappingProxyType):
        raise ValueError("harness input must be finite JSON data")
    active = set() if ancestors is None else ancestors
    if id(value) in active:
        raise ValueError("cyclic harness input is not supported")
    active.add(id(value))
    try:
        if type(value) in (dict, MappingProxyType):
            if any(type(key) is not str for key in value):
                raise ValueError("harness mapping keys must be strings")
            return {key: plain_harness_json(item, active) for key, item in value.items()}
        return [plain_harness_json(item, active) for item in value]
    finally:
        active.remove(id(value))


def frozen_harness_mapping(value):
    if type(value) not in (dict, MappingProxyType):
        raise ValueError("harness data must be a JSON mapping")

    def freeze(item):
        if isinstance(item, dict):
            return MappingProxyType({key: freeze(part) for key, part in item.items()})
        if isinstance(item, list):
            return tuple(freeze(part) for part in item)
        return item

    return freeze(plain_harness_json(value))


def credential_metadata_present(value) -> bool:
    sensitive = {"api_key", "access_token", "bearer_token", "refresh_token",
                 "password", "secret", "client_secret", "token", "authorization"}
    if isinstance(value, (dict, MappingProxyType)):
        for key, item in value.items():
            name = key.lower().replace("-", "_")
            if any(name == word or name.endswith("_" + word) for word in sensitive):
                return True
            if credential_metadata_present(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(credential_metadata_present(item) for item in value)
    return False


def _names(values) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or any(not valid_harness_id(v) for v in values):
        raise ValueError("harness capability names must be bounded identifiers")
    if len(set(values)) != len(values):
        raise ValueError("duplicate harness capability names")
    return tuple(values)


@dataclass(frozen=True)
class HarnessExecutionCapabilities:
    """Version-bound adapter facts, not permissions or a promotion decision."""

    supported_features: tuple[str, ...] = ()
    enforced_limits: tuple[str, ...] = ()
    isolation: str = "unverified"
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "supported_features", _names(self.supported_features))
        limits = _names(self.enforced_limits)
        if not set(limits) <= set(LIMITS) or self.isolation not in ISOLATIONS:
            raise ValueError("invalid harness execution capabilities")
        if type(self.evidence_refs) not in (tuple, list):
            raise ValueError("harness evidence must be a reference sequence")
        refs = tuple(self.evidence_refs)
        if any(not isinstance(ref, str) or not ref or len(ref) > 1024 for ref in refs):
            raise ValueError("invalid harness evidence reference")
        object.__setattr__(self, "enforced_limits", limits)
        object.__setattr__(self, "evidence_refs", refs)

    def to_dict(self) -> dict:
        return {"record_type": "harness_execution_capabilities/v1", **asdict(self)}


@dataclass(frozen=True)
class HarnessExecutionRequirements:
    """Required mechanics, supplied by the owning Loop before dispatch."""

    required_features: tuple[str, ...] = ()
    required_limits: tuple[str, ...] = ()
    allowed_isolations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_features", _names(self.required_features))
        limits = _names(self.required_limits)
        if type(self.allowed_isolations) not in (tuple, list):
            raise ValueError("harness isolations must be a sequence")
        isolations = tuple(self.allowed_isolations)
        if (not set(limits) <= set(LIMITS)
                or not set(isolations) <= set(ISOLATIONS)):
            raise ValueError("invalid harness execution requirements")
        object.__setattr__(self, "required_limits", limits)
        object.__setattr__(self, "allowed_isolations", isolations)

    def to_dict(self) -> dict:
        return {"record_type": "harness_execution_requirements/v1", **asdict(self)}


def unmet_harness_requirements(request, capabilities) -> tuple[str, ...]:
    """Compare explicit and request-implied requirements without dispatch."""
    requirements = request.execution_requirements
    if capabilities is None:
        capabilities = HarnessExecutionCapabilities()
    if not isinstance(capabilities, HarnessExecutionCapabilities):
        return ("invalid_capability_contract",)
    needed = set(requirements.required_features)
    for field in ("context_refs", "tool_refs", "skill_refs"):
        if getattr(request, field):
            needed.add(field)
    if request.approval_policy_ref:
        needed.add("approval_policy")
    if request.context_visibility == "shared_runtime_memory":
        needed.add("shared_runtime_memory")
    if request.context_visibility == "fresh":
        needed.add("fresh_context")
    if request.workspace_ref:
        needed.add("workspace_binding")
    if request.model_routes:
        needed.add("model_routes")
    effects = set(request.contract.effects)
    if effects & {"reads_fs", "writes_fs"}:
        needed.add("filesystem_effects")
    if "spawns_process" in effects:
        needed.add("process_effects")
    if "network" in effects:
        needed.add("network_effects")
    if "reads_secret" in effects:
        needed.add("secret_access")
    missing = ["feature:" + item for item in sorted(needed - set(capabilities.supported_features))]
    missing.extend("preemptive_limit:" + item for item in sorted(
        set(requirements.required_limits) - set(capabilities.enforced_limits)))
    if (requirements.allowed_isolations
            and capabilities.isolation not in requirements.allowed_isolations):
        missing.append("isolation")
    return tuple(missing)
