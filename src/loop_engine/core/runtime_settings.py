"""Typed user settings for one Loop Engine runtime.

This module owns configuration types and composition. It does not call a
model, search a store, or start a loop. The main public object is
``RuntimeSettings``. It groups loop defaults, search preferences, model
providers, model tiers, escalation policy, operating permissions, and history
paths without turning them into a long function signature.

``settings_loader`` owns YAML and environment precedence. Keeping parsing
separate from these runtime types keeps both modules small enough to review.
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field, replace
from typing import Mapping

from ..loop.recursive_loop import (EXIT_CONDITIONS, FRAMEWORKS, MODES,
                                   POWER_LEVELS, LoopConfig,
                                   MODEL_THINKING_POWER_LEVELS)
from .model_routes import PURPOSES, ModelRoute, RoutePolicy, default_routes
from .operating_profile import OperatingProfile
from .component_contracts import (
    LoopComponentDraft, component_payload_digest, define_loop_component)
from .parameter_resolution import (
    LoopConfigResolutionRecord, ParameterDefinition, ParameterInput,
    ParameterResolutionRequest, ParameterResolutionStatus, ParameterSource,
    ParameterSourceKind, ParameterValueState, resolve_parameter)

SETTINGS_VERSION = 1
SEARCH_MODES = ("lexical", "vector", "hybrid")
LEXICAL_BACKENDS = ("store", "fts5", "lancedb")
VECTOR_BACKENDS = ("hash", "model2vec")
PROVIDER_KINDS = ("builtin", "custom")
ESCALATION_ERROR_CODES = (
    "rate_limited", "timeout", "network_unreachable",
    "provider_unavailable", "provider_failed", "output_limit_reached",
    "incomplete_response", "empty_response",
    "output_validation_failed", "verification_rejected")
DEFAULT_SETTINGS_ENV = "LOOP_ENGINE_SETTINGS"

class SettingsError(ValueError):
    """The settings source is invalid or unsafe to interpret."""

@dataclass(frozen=True)
class LoopDefaults:
    """Default shape, mode policy, and exit policy for new loops."""

    framework: str = "nine_step"
    allowable_modes: tuple[str, ...] = MODES
    preferred_modes: tuple[str, ...] = MODES
    delegated_modes: tuple[str, ...] = MODES
    max_depth: "int | None" = None
    max_iterations: "int | None" = None
    max_model_calls: "int | None" = None
    exit_condition: str = "steps_complete"
    success_confidence_min: float = 0.5

    def __post_init__(self) -> None:
        if self.framework not in FRAMEWORKS:
            raise SettingsError(f"loop.framework must be one of {FRAMEWORKS}")
        for field_name in ("allowable_modes", "preferred_modes",
                           "delegated_modes"):
            values = getattr(self, field_name)
            if not values or any(value not in MODES for value in values):
                raise SettingsError(f"loop.{field_name} must use {MODES}")
        if any(value not in self.allowable_modes
               for value in self.preferred_modes):
            raise SettingsError(
                "loop.preferred_modes must be a subset of allowable_modes")
        if (self.max_depth is not None
                and (not isinstance(self.max_depth, int)
                     or isinstance(self.max_depth, bool)
                     or self.max_depth < 0)):
            raise SettingsError(
                "loop.max_depth must be non-negative when provided")
        for name in ("max_iterations", "max_model_calls"):
            value = getattr(self, name)
            if (value is not None
                    and (not isinstance(value, int)
                         or isinstance(value, bool) or value < 1)):
                raise SettingsError(
                    f"loop.{name} must be positive when provided")
        if self.exit_condition not in EXIT_CONDITIONS:
            raise SettingsError(
                f"loop.exit_condition must be one of {EXIT_CONDITIONS}")
        if not 0.0 <= self.success_confidence_min <= 1.0:
            raise SettingsError(
                "loop.success_confidence_min must be between 0 and 1")

@dataclass(frozen=True)
class LoopConfigOverride:
    """Optional changes for one loop without a long constructor call."""

    framework: "str | ParameterInput" = ""
    allowable_modes: "tuple[str, ...] | ParameterInput" = ()
    preferred_modes: "tuple[str, ...] | ParameterInput" = ()
    delegated_modes: "tuple[str, ...] | ParameterInput" = ()
    effort: "str | ParameterInput" = ""
    llm_thinking_power: "str | ParameterInput" = ""
    custom_steps: "tuple[str, ...] | ParameterInput" = ()
    max_depth: "int | None | ParameterInput" = None
    max_iterations: "int | None | ParameterInput" = None
    max_model_calls: "int | None | ParameterInput" = None
    exit_condition: "str | ParameterInput" = ""
    success_confidence_min: "float | None | ParameterInput" = None

    def __post_init__(self) -> None:
        for field_name in ("allowable_modes", "preferred_modes",
                           "delegated_modes"):
            raw_value = getattr(self, field_name)
            if isinstance(raw_value, ParameterInput):
                continue
            values = tuple(raw_value)
            object.__setattr__(self, field_name, values)
            if any(value not in MODES for value in values):
                raise SettingsError(f"{field_name} must use {MODES}")
        if (not isinstance(self.effort, ParameterInput)
                and self.effort and self.effort not in POWER_LEVELS):
            raise SettingsError(f"effort must be one of {POWER_LEVELS}")
        if (not isinstance(self.llm_thinking_power, ParameterInput)
                and self.llm_thinking_power and self.llm_thinking_power
                not in MODEL_THINKING_POWER_LEVELS):
            raise SettingsError(
                "llm_thinking_power must be small, medium, high, max, or "
                "specialized")

@dataclass(frozen=True)
class SearchSettings:
    """How the Retrieval Engine ranks and limits local results."""

    mode: str = "hybrid"
    lexical_backend: str = "fts5"
    vector_backend: str = "hash"
    vector_model: str = ""
    top_k: "int | None" = None
    zero_model_first: bool = True

    def __post_init__(self) -> None:
        if self.mode not in SEARCH_MODES:
            raise SettingsError(f"search.mode must be one of {SEARCH_MODES}")
        if self.lexical_backend not in LEXICAL_BACKENDS:
            raise SettingsError(
                f"search.lexical_backend must be one of {LEXICAL_BACKENDS}")
        if self.vector_backend not in VECTOR_BACKENDS:
            raise SettingsError(
                f"search.vector_backend must be one of {VECTOR_BACKENDS}")
        if self.top_k is not None and self.top_k < 1:
            raise SettingsError("search.top_k must be positive when provided")

    def build_retriever(self, records):
        """Create the existing Retriever with these backend choices."""
        from .retrieval import Retriever
        return Retriever(
            records, lexical_backend=self.lexical_backend,
            vector_backend=self.vector_backend,
            vector_model=self.vector_model or None)

@dataclass(frozen=True)
class HistorySettings:
    """Where saved run histories and local viewing state live."""

    runs_dir: str = "~/.loop-engine/runs"
    save_run_history: bool = True

    def resolved_runs_dir(self) -> str:
        return os.path.abspath(os.path.expandvars(os.path.expanduser(
            self.runs_dir)))

@dataclass(frozen=True)
class ProviderSettings:
    """One provider declaration with a credential reference, never a key."""

    provider_id: str
    kind: str = "builtin"
    enabled: bool = True
    credential_env: str = ""
    endpoint: str = ""
    model: str = ""
    wire: str = "openai"
    locality: str = "cloud"
    counts_as_evidence: bool = False
    maximum_output_tokens: "int | None" = None
    maximum_output_source: str = ""
    purposes: tuple[str, ...] = ("counted_generation", "decide_label")
    headers: tuple[tuple[str, str], ...] = ()
    auth_scheme: str = "bearer"
    auth_header: str = ""

    def __post_init__(self) -> None:
        if not self.provider_id or not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_]*", self.provider_id):
            raise SettingsError(
                "provider_id must start with a letter and use letters, "
                "numbers, or underscores")
        if self.kind not in PROVIDER_KINDS:
            raise SettingsError(f"provider.kind must be one of {PROVIDER_KINDS}")
        if self.credential_env and not re.fullmatch(
                r"[A-Z][A-Z0-9_]*", self.credential_env):
            raise SettingsError(
                "provider.credential_env must be an environment variable name")
        if self.locality not in ("cloud", "organization", "local"):
            raise SettingsError(
                "provider.locality must be cloud, organization, or local")
        if self.wire not in ("openai", "ollama"):
            raise SettingsError("provider.wire must be openai or ollama")
        if self.auth_scheme not in ("bearer", "header", "none"):
            raise SettingsError(
                "provider.auth_scheme must be bearer, header, or none")
        if self.auth_scheme == "header":
            if (not self.auth_header.strip()
                    or not re.fullmatch(
                        r"[!#$%&'*+.^_`|~0-9A-Za-z-]+",
                        self.auth_header)
                    or self.auth_header.casefold() in {
                        "authorization", "proxy-authorization", "cookie",
                        "set-cookie"}):
                raise SettingsError(
                    "header authentication needs a valid HTTP header name")
        elif self.auth_header:
            raise SettingsError(
                "provider.auth_header is only valid for header authentication")
        if self.auth_scheme == "none" and self.credential_env:
            raise SettingsError(
                "provider auth_scheme none cannot declare a credential")
        if self.kind == "custom" and not (self.endpoint and self.model):
            raise SettingsError(
                "a custom provider needs endpoint and model")
        if bool(self.maximum_output_tokens) != bool(
                self.maximum_output_source.strip()):
            raise SettingsError(
                "provider.maximum_output_tokens and "
                "provider.maximum_output_source must be declared together")
        if (self.maximum_output_tokens is not None
                and self.maximum_output_tokens < 1):
            raise SettingsError(
                "provider.maximum_output_tokens must be positive")
        if self.kind == "builtin" and self.provider_id not in (
                "ollama_cloud", "mistral", "openrouter"):
            raise SettingsError(
                f"unknown built-in provider {self.provider_id!r}")
        if not self.purposes or any(
                purpose not in PURPOSES for purpose in self.purposes):
            raise SettingsError(f"provider.purposes must use {PURPOSES}")
        headers = tuple(self.headers)
        forbidden_headers = {
            "authorization", "proxy-authorization", "cookie", "set-cookie",
            "x-api-key", "api-key"}
        if any(not isinstance(item, tuple) or len(item) != 2
               or not all(isinstance(value, str) for value in item)
               for item in headers):
            raise SettingsError(
                "provider.headers must contain text name/value pairs")
        if (len(headers) != len({item[0].casefold() for item in headers})
                or any(not item[0].strip() or not item[1].strip()
                       or item[0].casefold() in forbidden_headers
                       or item[0].casefold() == self.auth_header.casefold()
                       or "\n" in item[0] or "\r" in item[0]
                       or "\n" in item[1] or "\r" in item[1]
                       for item in headers)):
            raise SettingsError(
                "provider.headers must be unique non-secret HTTP headers")
        object.__setattr__(self, "headers", tuple(sorted(headers)))

    @property
    def route_name(self) -> str:
        return f"custom.{self.provider_id}"

    def safe_summary(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "kind": self.kind,
            "enabled": self.enabled,
            "credential_ref": (
                f"env:{self.credential_env}" if self.credential_env else ""),
            "endpoint": self.endpoint,
            "model": self.model,
            "wire": self.wire,
            "locality": self.locality,
            "counts_as_evidence": self.counts_as_evidence,
            "maximum_output_tokens": self.maximum_output_tokens,
            "maximum_output_source": self.maximum_output_source,
            "header_names": [item[0] for item in self.headers],
            "auth_scheme": self.auth_scheme,
            "auth_header": self.auth_header,
        }

@dataclass(frozen=True)
class ModelTier:
    """Ordered model routes and per-attempt limits for one thinking tier."""

    name: str
    routes: tuple[str, ...] = ()
    max_output_tokens: "int | None" = None
    timeout_seconds: float = 300.0
    max_attempts: "int | None" = None

    def __post_init__(self) -> None:
        if self.name not in MODEL_THINKING_POWER_LEVELS:
            raise SettingsError(
                f"model tier name must be one of {MODEL_THINKING_POWER_LEVELS}")
        if ((self.max_output_tokens is not None
             and self.max_output_tokens < 1)
                or (self.max_attempts is not None
                    and self.max_attempts < 1)):
            raise SettingsError("model tier limits must be positive")
        if self.timeout_seconds <= 0:
            raise SettingsError("model tier timeout_seconds must be positive")
        if (any(not route.strip() for route in self.routes)
                or len(self.routes) != len(set(self.routes))):
            raise SettingsError(
                "model tier routes must be unique non-empty names")

@dataclass(frozen=True)
class EscalationSettings:
    """When a failed tier may move to a larger tier."""

    enabled: bool = False
    order: tuple[str, ...] = ("small", "medium", "high", "max")
    on_errors: tuple[str, ...] = ("output_validation_failed",)
    max_tier_changes: "int | None" = None

    def __post_init__(self) -> None:
        if (not self.order or len(set(self.order)) != len(self.order)
                or any(value not in MODEL_THINKING_POWER_LEVELS
                       for value in self.order)):
            raise SettingsError(
                "model escalation order must contain unique thinking tiers")
        if "specialized" in self.order:
            raise SettingsError(
                "specialized is selected by task capability, not automatic "
                "power escalation")
        if (self.max_tier_changes is not None
                and self.max_tier_changes < 0):
            raise SettingsError(
                "model escalation max_tier_changes cannot be negative")
        if any(error not in ESCALATION_ERROR_CODES
               for error in self.on_errors):
            raise SettingsError(
                f"model escalation errors must use {ESCALATION_ERROR_CODES}")

def _default_tiers() -> tuple[ModelTier, ...]:
    """Conservative route hints. They are not a measured quality ranking."""
    return (
        ModelTier("small", ("cloud.mistral", "cloud.default"),
                  None, 120.0),
        ModelTier("medium", ("cloud.default", "cloud.glm",
                             "cloud.mistral.large", "cloud.openrouter"),
                  None, 300.0),
        ModelTier("high", ("cloud.mistral.large", "cloud.hard",
                           "cloud.openrouter.reasoning"), None, 600.0),
        ModelTier("max", ("cloud.hard", "cloud.openrouter.reasoning",
                          "cloud.mistral.large"), None, 900.0),
        ModelTier("specialized", (), None, 600.0),
    )

@dataclass(frozen=True)
class ModelPolicyRequest:
    """One model policy request passed as an object, not scattered values."""

    purpose: str = "counted_generation"
    thinking_power: str = ""
    allow_escalation: "bool | None" = None
    max_total_tokens: "int | None" = None
    max_route_attempts: "int | None" = None
    route_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.purpose not in PURPOSES:
            raise SettingsError(f"purpose must be one of {PURPOSES}")
        if (self.thinking_power
                and self.thinking_power not in MODEL_THINKING_POWER_LEVELS):
            raise SettingsError(
                "thinking_power must be small, medium, high, max, or specialized")
        if self.max_total_tokens is not None and self.max_total_tokens < 1:
            raise SettingsError("max_total_tokens must be positive")
        if self.max_route_attempts is not None and self.max_route_attempts < 1:
            raise SettingsError("max_route_attempts must be positive")

@dataclass(frozen=True)
class ModelTask:
    """Prompt, output contract, and policy for one semantic model task."""

    prompt: str
    policy: ModelPolicyRequest = field(default_factory=ModelPolicyRequest)
    system: str = ""
    temperature: float = 0.2
    output_contract: str = ""
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise SettingsError("a ModelTask needs a prompt")
        if not 0.0 <= self.temperature <= 2.0:
            raise SettingsError("ModelTask.temperature must be between 0 and 2")

@dataclass(frozen=True)
class ModelSettings:
    """Provider declarations, route tiers, and bounded escalation policy."""

    default_thinking_power: str = "medium"
    providers: tuple[ProviderSettings, ...] = field(default_factory=lambda: (
        ProviderSettings("ollama_cloud", credential_env="OLLAMA_API_KEY"),
        ProviderSettings("mistral", credential_env="MISTRAL_API_KEY"),
        ProviderSettings("openrouter", credential_env="OPENROUTER_API_KEY"),
    ))
    tiers: tuple[ModelTier, ...] = field(default_factory=_default_tiers)
    escalation: EscalationSettings = field(default_factory=EscalationSettings)
    allow_local_counted_generation: bool = False

    def __post_init__(self) -> None:
        if self.default_thinking_power not in MODEL_THINKING_POWER_LEVELS:
            raise SettingsError(
                "models.default_thinking_power must be small, medium, high, "
                "max, or specialized")
        provider_ids = [provider.provider_id for provider in self.providers]
        if len(provider_ids) != len(set(provider_ids)):
            raise SettingsError("models.providers contains duplicate ids")
        tier_names = [tier.name for tier in self.tiers]
        if len(tier_names) != len(set(tier_names)):
            raise SettingsError("models.tiers contains duplicate names")
        if self.default_thinking_power not in tier_names:
            raise SettingsError(
                "models.default_thinking_power needs a matching tier")

    def tier(self, name: str) -> ModelTier:
        for tier in self.tiers:
            if tier.name == name:
                return tier
        raise SettingsError(f"no model tier named {name!r}")

    def enabled_provider_ids(self) -> tuple[str, ...]:
        return tuple(provider.provider_id for provider in self.providers
                     if provider.enabled)

    def execution_tiers(self, request: ModelPolicyRequest) -> tuple[ModelTier, ...]:
        start = request.thinking_power or self.default_thinking_power
        first = self.tier(start)
        enabled = (self.escalation.enabled if request.allow_escalation is None
                   else request.allow_escalation)
        if not enabled or start == "specialized":
            return (first,)
        order = self.escalation.order
        if start not in order:
            return (first,)
        index = order.index(start)
        changes = self.escalation.max_tier_changes
        names = (order[index:] if changes is None
                 else order[index:index + changes + 1])
        return tuple(self.tier(name) for name in names)

    def gateway_config(self, request: "ModelPolicyRequest | None" = None):
        """Build the existing gateway config from one typed policy request."""
        from .model_gateway import (ModelGatewayConfig,
                                    ModelRouteAttemptSpec)

        req = request or ModelPolicyRequest()
        tiers = self.execution_tiers(req)
        route_plan = []
        if req.route_names:
            tier = tiers[0]
            route_plan.extend(ModelRouteAttemptSpec(
                route, tier.name, tier.max_output_tokens,
                tier.timeout_seconds) for route in req.route_names)
        else:
            for tier in tiers:
                routes = (tier.routes if tier.max_attempts is None
                          else tier.routes[:tier.max_attempts])
                route_plan.extend(ModelRouteAttemptSpec(
                    route, tier.name, tier.max_output_tokens,
                    tier.timeout_seconds) for route in routes)
        if not route_plan:
            raise SettingsError(
                f"model tier {tiers[0].name!r} has no configured routes")
        maximum_attempts = req.max_route_attempts
        selected_attempts = (len(route_plan) if maximum_attempts is None
                             else min(maximum_attempts, len(route_plan)))
        return ModelGatewayConfig(
            purpose=req.purpose,
            thinking_power=tiers[0].name,
            route_plan=tuple(route_plan),
            allow_failover=selected_attempts > 1,
            max_route_attempts=maximum_attempts,
            timeout_seconds=max(item.timeout_seconds for item in route_plan),
            max_output_tokens=(max(
                item.max_output_tokens for item in route_plan
                if item.max_output_tokens is not None)
                if any(item.max_output_tokens is not None
                       for item in route_plan) else None),
            max_total_tokens=req.max_total_tokens,
            allow_power_escalation=len(tiers) > 1,
            max_power_escalations=max(0, len(tiers) - 1),
            escalate_on=self.escalation.on_errors)

@dataclass(frozen=True)
class SettingsLoadResult:
    """Loaded settings plus the non-secret sources that changed them."""

    settings: "RuntimeSettings"
    file_path: str = ""
    environment_overrides: tuple[str, ...] = ()
    loop_id: str = ""

    def safe_summary(self) -> dict:
        value = self.settings.safe_summary()
        value["loaded_file"] = self.file_path
        value["environment_overrides"] = list(self.environment_overrides)
        value["settings_loop_id"] = self.loop_id
        return value

@dataclass(frozen=True)
class SettingsWriteResult:
    """Created settings path plus the loop that performed the file write."""

    path: str
    loop_id: str

@dataclass(frozen=True)
class RuntimeSettings:
    """One composed settings object for the full local runtime."""

    version: int = SETTINGS_VERSION
    loop: LoopDefaults = field(default_factory=LoopDefaults)
    search: SearchSettings = field(default_factory=SearchSettings)
    models: ModelSettings = field(default_factory=ModelSettings)
    operating: OperatingProfile = field(default_factory=OperatingProfile)
    history: HistorySettings = field(default_factory=HistorySettings)

    def __post_init__(self) -> None:
        if self.version != SETTINGS_VERSION:
            raise SettingsError(
                f"settings version {self.version!r} is unsupported; use "
                f"version {SETTINGS_VERSION}")

    def loop_config(self,
                    override: "LoopConfigOverride | None" = None) -> LoopConfig:
        """Create one LoopConfig from defaults plus one typed override."""
        return self.loop_config_with_record(override)[0]

    def loop_config_with_record(
            self, override: "LoopConfigOverride | None" = None) \
            -> tuple[LoopConfig, LoopConfigResolutionRecord]:
        """Resolve one LoopConfig and return safe source evidence for each field."""
        change = override or LoopConfigOverride()
        profile_ref = "core.settings.runtime.loop"
        profile_version = str(self.version)
        records = []

        def input_for(value, legacy_omitted) -> ParameterInput:
            if isinstance(value, ParameterInput):
                return value
            if value == legacy_omitted:
                return ParameterInput.omitted()
            return ParameterInput.from_value(value)

        def resolve(
                name: str, semantic_type: str, explicit, legacy_omitted,
                profile_value=ParameterValueState.OMITTED, *,
                nullable: bool = False, constraints: "Mapping | None" = None,
                profile_source: ParameterSourceKind =
                ParameterSourceKind.LOOP_PROFILE):
            definition = ParameterDefinition(
                f"loop.config.{name}", name.replace("_", " "),
                f"Resolved {name} for one Loop configuration.",
                semantic_type, "loop_engine.core.runtime_settings:RuntimeSettings",
                "loop_invocation", nullable=nullable,
                constraints=dict(constraints or {}),
                affects_semantic_identity=True,
                affects_qualification=(name not in {"max_depth"}))
            sources = [ParameterSource(
                ParameterSourceKind.RUN_OVERRIDE, "LoopConfigOverride",
                "1.0.0", input_for(explicit, legacy_omitted))]
            if profile_value != ParameterValueState.OMITTED:
                sources.append(ParameterSource(
                    profile_source, profile_ref, profile_version,
                    ParameterInput.from_value(profile_value)))
            resolved = resolve_parameter(ParameterResolutionRequest(
                definition, tuple(sources)))
            records.append(resolved)
            if resolved.status != ParameterResolutionStatus.RESOLVED:
                reasons = "; ".join(resolved.warnings) or "unresolved"
                raise SettingsError(
                    f"loop config parameter {name} is invalid: {reasons}")
            return resolved.value

        framework = resolve(
            "framework", "text", change.framework, "", self.loop.framework,
            constraints={"allowed_values": FRAMEWORKS})
        allowable_modes = tuple(resolve(
            "allowable_modes", "text_sequence", change.allowable_modes, (),
            self.loop.allowable_modes,
            constraints={"allowed_values": MODES, "non_empty": True}))
        preferred_modes = tuple(resolve(
            "preferred_modes", "text_sequence", change.preferred_modes, (),
            self.loop.preferred_modes,
            constraints={"allowed_values": MODES, "non_empty": True}))
        delegated_modes = tuple(resolve(
            "delegated_modes", "text_sequence", change.delegated_modes, (),
            self.loop.delegated_modes,
            constraints={"allowed_values": MODES, "non_empty": True}))
        if any(mode not in allowable_modes for mode in preferred_modes):
            raise SettingsError(
                "preferred_modes must be a subset of allowable_modes")
        operating_effort = {
            "minimal": "light", "standard": "standard",
            "deep": "deep", "exhaustive": "max",
        }[self.operating.effort_mode]
        effort = resolve(
            "effort", "text", change.effort, "", operating_effort,
            constraints={"allowed_values": POWER_LEVELS},
            profile_source=ParameterSourceKind.DERIVED_VALUE)
        custom_steps = tuple(resolve(
            "custom_steps", "text_sequence", change.custom_steps, (), (),
            constraints={}))
        max_depth = resolve(
            "max_depth", "integer", change.max_depth, None,
            self.loop.max_depth, nullable=True, constraints={"minimum": 0})
        max_iterations = resolve(
            "max_iterations", "integer", change.max_iterations, None,
            self.loop.max_iterations, nullable=True,
            constraints={"minimum": 1})
        max_model_calls = resolve(
            "max_model_calls", "integer", change.max_model_calls, None,
            self.loop.max_model_calls, nullable=True,
            constraints={"minimum": 1})
        exit_condition = resolve(
            "exit_condition", "text", change.exit_condition, "",
            self.loop.exit_condition,
            constraints={"allowed_values": EXIT_CONDITIONS})
        success_confidence_min = resolve(
            "success_confidence_min", "number",
            change.success_confidence_min, None,
            self.loop.success_confidence_min,
            constraints={"minimum": 0.0, "maximum": 1.0})
        uses_model = any(mode in allowable_modes
                         for mode in ("hybrid", "non_deterministic"))
        if uses_model:
            llm_thinking_power = resolve(
                "llm_thinking_power", "text", change.llm_thinking_power, "",
                self.models.default_thinking_power,
                constraints={"allowed_values": MODEL_THINKING_POWER_LEVELS})
        else:
            explicit_thinking = input_for(change.llm_thinking_power, "")
            if explicit_thinking.state != ParameterValueState.OMITTED:
                raise SettingsError(
                    "llm_thinking_power applies only to a loop that allows "
                    "hybrid or non_deterministic mode")
            llm_thinking_power = ""
            records.append(resolve_parameter(ParameterResolutionRequest(
                ParameterDefinition(
                    "loop.config.llm_thinking_power", "LLM thinking power",
                    "Model thinking setting for a model-authorized Loop.",
                    "text", "loop_engine.core.runtime_settings:RuntimeSettings",
                    "loop_invocation", constraints={
                        "allowed_values": ("", *MODEL_THINKING_POWER_LEVELS)}),
                (ParameterSource(
                    ParameterSourceKind.DERIVED_VALUE,
                    "deterministic_mode_without_model", "1.0.0",
                    ParameterInput.from_value("")),))))
        config = LoopConfig(
            framework=framework, allowable_modes=allowable_modes,
            preferred_modes=preferred_modes,
            delegated_modes=delegated_modes, power=effort,
            llm_thinking_power=llm_thinking_power,
            custom_steps=custom_steps, max_depth=max_depth,
            max_iterations=max_iterations, max_model_calls=max_model_calls,
            exit_condition=exit_condition,
            success_confidence_min=success_confidence_min)
        record = LoopConfigResolutionRecord.from_parameters(
            "core.settings.runtime.loop@1", tuple(records))
        return config, record

    def model_request(self, task: ModelTask):
        """Create one gateway request from a typed model task."""
        from .model_gateway import ModelGatewayConfig, ModelGatewayRequest
        config = self.models.gateway_config(task.policy)
        operating = ModelGatewayConfig.from_operating_profile(self.operating)
        allowed_localities = tuple(
            locality for locality in config.allowed_localities
            if locality in operating.allowed_localities)
        config = replace(
            config, allowed_localities=allowed_localities,
            timeout_seconds=min(config.timeout_seconds,
                                operating.timeout_seconds))
        return ModelGatewayRequest(
            prompt=task.prompt,
            config=config,
            system=task.system,
            temperature=task.temperature,
            output_contract=task.output_contract,
            trace_id=task.trace_id)

    def build_gateway(self, environ: "Mapping[str, str] | None" = None):
        """Build a provider-neutral gateway without probing or calling it."""
        from .custom_endpoint import CustomEndpoint
        from .model_capabilities import ModelOutputCapability
        from .model_gateway import (ModelGateway, builtin_provider_specs,
                                    provider_spec_from_endpoint)
        from .provider_failover import PROVIDERS

        env = dict(os.environ if environ is None else environ)
        providers = []
        routes = list(default_routes())
        for configured in self.models.providers:
            if not configured.enabled:
                continue
            if configured.kind == "builtin":
                adapter = PROVIDERS.get(configured.provider_id)
                if adapter is None:
                    raise SettingsError(
                        f"provider adapter {configured.provider_id!r} is missing")
                built = builtin_provider_specs({
                    configured.provider_id: adapter})
                if configured.maximum_output_tokens is not None:
                    built = tuple(replace(
                        spec,
                        model_output_capability=ModelOutputCapability(
                            configured.maximum_output_tokens,
                            configured.maximum_output_source,
                            endpoint=spec.endpoint),
                        model_output_capability_model=(
                            configured.model or adapter.DEFAULT_MODEL))
                        for spec in built)
                providers.extend(built)
                continue
            endpoint = CustomEndpoint(
                name=configured.provider_id,
                base_url=configured.endpoint,
                model=configured.model,
                api_key=env.get(configured.credential_env, ""),
                wire=configured.wire,
                locality=configured.locality,
                output_capability=(ModelOutputCapability(
                    configured.maximum_output_tokens,
                    configured.maximum_output_source,
                    endpoint=configured.endpoint)
                    if configured.maximum_output_tokens is not None else None),
                counts_as_evidence=configured.counts_as_evidence,
                headers=configured.headers,
                auth_scheme=configured.auth_scheme,
                auth_header=configured.auth_header)
            spec = provider_spec_from_endpoint(endpoint)
            providers.append(replace(
                spec, credential_ref=(
                    f"env:{configured.credential_env}"
                    if configured.credential_env else "not_required")))
            routes.append(ModelRoute(
                configured.route_name, configured.provider_id,
                configured.model, configured.locality,
                configured.purposes))
        policy = RoutePolicy(
            allow_local_counted_generation=
            self.models.allow_local_counted_generation)
        return ModelGateway(
            providers=tuple(providers), routes=tuple(routes), policy=policy)

    def safe_summary(self) -> dict:
        """Return settings and credential references without secret values."""
        return {
            "record_type": "runtime_settings/v1",
            "version": self.version,
            "loop": asdict(self.loop),
            "search": asdict(self.search),
            "models": {
                "default_thinking_power": self.models.default_thinking_power,
                "providers": [provider.safe_summary()
                              for provider in self.models.providers],
                "tiers": [asdict(tier) for tier in self.models.tiers],
                "escalation": asdict(self.models.escalation),
                "allow_local_counted_generation":
                    self.models.allow_local_counted_generation,
            },
            "operating": self.operating.summary(),
            "history": {
                **asdict(self.history),
                "resolved_runs_dir": self.history.resolved_runs_dir(),
            },
        }

    def component_definition(self):
        """Represent the resolved settings snapshot as one static component."""
        payload = self.safe_summary()
        return define_loop_component(LoopComponentDraft(
            "core.settings.runtime", "1.0.0", "settings", "static",
            "runtime_settings/v1", component_payload_digest(payload),
            "resolved Core and user settings",
            role_affinities=("practitioner", "intelligence", "solution"),
            mode_support=("deterministic", "hybrid", "non_deterministic")))
