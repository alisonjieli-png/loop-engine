"""One immutable, versioned definition for every runnable Loop.

This module owns definition identity, canonical serialization, digest checks,
and the typed request that starts the canonical Loop runtime.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field, replace
from typing import Any

from .loop_contract import LoopContract
from .loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from .runtime_context import LoopRuntimeContext, LoopRuntimeContextError


_DEFINITION_ID = re.compile(
    r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MODES = ("deterministic", "hybrid", "non_deterministic")


class LoopDefinitionError(ValueError):
    """A Loop definition is invalid, incompatible, or was changed in transit."""


def _names(label: str, values, *, sort: bool = True) -> tuple[str, ...]:
    normalized = tuple(values)
    if any(not isinstance(value, str) or not value.strip()
           for value in normalized):
        raise LoopDefinitionError(f"{label} must contain non-empty strings")
    if len(normalized) != len(set(normalized)):
        raise LoopDefinitionError(f"{label} cannot contain duplicates")
    return tuple(sorted(normalized)) if sort else normalized


def _strict_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise LoopDefinitionError(
                "configuration facts cannot contain NaN or infinity")
        return value
    if isinstance(value, (list, tuple)):
        return [_strict_json_value(item) for item in value]
    if isinstance(value, dict):
        if any(not isinstance(key, str) or not key.strip() for key in value):
            raise LoopDefinitionError(
                "configuration fact keys must be non-empty strings")
        return {key: _strict_json_value(value[key]) for key in sorted(value)}
    raise LoopDefinitionError(
        f"configuration fact type {type(value).__name__} is not supported")


@dataclass(frozen=True)
class ConfigurationFacts:
    """Canonical JSON facts with no mutable mapping retained by the object."""

    canonical_json: str = "{}"

    def __post_init__(self) -> None:
        if not isinstance(self.canonical_json, str):
            raise LoopDefinitionError("canonical_json must be a string")
        try:
            decoded = json.loads(self.canonical_json)
        except (TypeError, ValueError) as exc:
            raise LoopDefinitionError(
                "configuration facts must be valid JSON") from exc
        if not isinstance(decoded, dict):
            raise LoopDefinitionError(
                "configuration facts must be one JSON object")
        normalized = _strict_json_value(decoded)
        canonical = json.dumps(
            normalized, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)
        object.__setattr__(self, "canonical_json", canonical)

    @classmethod
    def from_mapping(cls, values: dict | None = None) -> "ConfigurationFacts":
        normalized = _strict_json_value(dict(values or {}))
        return cls(json.dumps(
            normalized, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False))

    def to_dict(self) -> dict:
        return json.loads(self.canonical_json)


@dataclass(frozen=True)
class LoopDefinitionRef:
    """Exact identity for one immutable Loop definition."""

    definition_id: str
    version: str
    content_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.definition_id, str) or not _DEFINITION_ID.fullmatch(
                self.definition_id):
            raise LoopDefinitionError(
                "definition_id must use lowercase dotted names")
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(
                self.version):
            raise LoopDefinitionError("version must use MAJOR.MINOR.PATCH")
        if not isinstance(self.content_digest, str) or not _DIGEST.fullmatch(
                self.content_digest):
            raise LoopDefinitionError(
                "content_digest must be a lowercase SHA-256 digest")

    def to_dict(self) -> dict[str, str]:
        return {
            "definition_id": self.definition_id,
            "version": self.version,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopDefinitionRef":
        if not isinstance(value, dict) or set(value) != {
                "definition_id", "version", "content_digest"}:
            raise LoopDefinitionError(
                "LoopDefinitionRef has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class LoopDefinition:
    """All immutable facts needed to validate and start one Loop."""

    definition_id: str
    version: str
    role_profile_id: str
    role_profile_version: str
    contract: LoopContract
    configuration_facts: ConfigurationFacts
    supported_modes: tuple[str, ...]
    installed_executor_modes: tuple[str, ...]
    step_profile: str
    loop_condition: str
    exit_condition: str
    effects: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        LoopDefinitionRef(
            self.definition_id, self.version, "0" * 64)
        if not isinstance(self.contract, LoopContract):
            raise LoopDefinitionError("contract must be a LoopContract")
        if not isinstance(self.configuration_facts, ConfigurationFacts):
            raise LoopDefinitionError(
                "configuration_facts must be ConfigurationFacts")
        if not isinstance(self.step_profile, str) or not self.step_profile.strip():
            raise LoopDefinitionError("step_profile must be a non-empty string")

        from .loop_control import EXIT_CONDITIONS, LOOP_CONDITIONS
        if self.loop_condition not in LOOP_CONDITIONS:
            raise LoopDefinitionError(
                f"loop_condition must be one of {LOOP_CONDITIONS}")
        if self.exit_condition not in EXIT_CONDITIONS:
            raise LoopDefinitionError(
                f"exit_condition must be one of {EXIT_CONDITIONS}")

        supported = _names("supported_modes", self.supported_modes)
        installed = _names(
            "installed_executor_modes", self.installed_executor_modes)
        if not supported or any(mode not in _MODES for mode in supported):
            raise LoopDefinitionError(
                f"supported_modes must use {_MODES} and cannot be empty")
        if not installed or any(mode not in _MODES for mode in installed):
            raise LoopDefinitionError(
                "installed_executor_modes must name at least one known mode")
        if not set(installed) <= set(supported):
            raise LoopDefinitionError(
                "installed_executor_modes must be a subset of supported_modes")
        object.__setattr__(self, "supported_modes", supported)
        object.__setattr__(self, "installed_executor_modes", installed)

        effects = _names("effects", self.effects)
        permissions = _names("permissions", self.permissions)
        capabilities = _names(
            "required_capabilities", self.required_capabilities)
        if effects != tuple(sorted(self.contract.effects)):
            raise LoopDefinitionError(
                "definition effects must exactly match contract effects")
        object.__setattr__(self, "effects", effects)
        object.__setattr__(self, "permissions", permissions)
        object.__setattr__(self, "required_capabilities", capabilities)

        from .loop_profile_catalog import LoopProfileRef
        from .loop_profile_ontology import resolve_profile
        try:
            resolved = resolve_profile(LoopProfileRef(
                self.role_profile_id, self.role_profile_version))
        except Exception as exc:  # normalized to this boundary's error
            raise LoopDefinitionError(
                "role profile is not registered") from exc
        if resolved.spec.state != "registered":
            raise LoopDefinitionError(
                f"role profile {self.role_profile_id!r} is "
                f"{resolved.spec.state!r}, not registered")
        try:
            role = LoopRole(resolved.spec.family)
        except ValueError as exc:
            raise LoopDefinitionError(
                "role profile does not belong to a runnable Loop role") from exc
        if self.contract.role != role.value:
            raise LoopDefinitionError(
                f"contract role {self.contract.role!r} does not match "
                f"profile role {role.value!r}")
        if not set(supported) <= set(resolved.allowed_modes):
            raise LoopDefinitionError(
                f"supported modes exceed profile modes {resolved.allowed_modes}")
        if self.contract.runtime_mode not in supported:
            raise LoopDefinitionError(
                f"contract mode {self.contract.runtime_mode!r} is not in "
                f"supported_modes {supported}")
        if not set(resolved.required_capabilities) <= set(capabilities):
            missing = sorted(
                set(resolved.required_capabilities) - set(capabilities))
            raise LoopDefinitionError(
                f"definition omits profile capabilities {missing}")

        facts = self.configuration_facts.to_dict()
        if ("allowable_modes" in facts
                and set(facts["allowable_modes"]) != set(supported)):
            raise LoopDefinitionError(
                "configuration allowable_modes conflicts with supported_modes")
        if ("preferred_modes" in facts
                and not set(facts["preferred_modes"]) <= set(supported)):
            raise LoopDefinitionError(
                "configuration preferred_modes exceed supported_modes")
        if ("loop_condition" in facts
                and facts["loop_condition"] != self.loop_condition):
            raise LoopDefinitionError(
                "configuration loop_condition conflicts with definition")
        if ("exit_condition" in facts
                and facts["exit_condition"] != self.exit_condition):
            raise LoopDefinitionError(
                "configuration exit_condition conflicts with definition")

    @property
    def identity(self) -> LoopRoleIdentity:
        from .loop_profile_catalog import LoopProfileRef
        from .loop_profile_ontology import identity_for_profile
        return identity_for_profile(LoopProfileRef(
            self.role_profile_id, self.role_profile_version))

    def _canonical_body(self) -> dict:
        return {
            "record_type": "loop_definition/v1",
            "definition_id": self.definition_id,
            "version": self.version,
            "role_profile": {
                "profile_id": self.role_profile_id,
                "version": self.role_profile_version,
            },
            "contract": {
                "name": self.contract.name,
                "execution_mode": self.contract.execution_mode,
                "input_roles": list(self.contract.input_roles),
                "output_roles": list(self.contract.output_roles),
                "effects": list(self.contract.effects),
                "locality": self.contract.locality,
                "cost_class": self.contract.cost_class,
                "role": self.contract.role,
            },
            "configuration_facts": self.configuration_facts.to_dict(),
            "supported_modes": list(self.supported_modes),
            "installed_executor_modes": list(self.installed_executor_modes),
            "step_profile": self.step_profile,
            "loop_condition": self.loop_condition,
            "exit_condition": self.exit_condition,
            "effects": list(self.effects),
            "permissions": list(self.permissions),
            "required_capabilities": list(self.required_capabilities),
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self._canonical_body(), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()

    @property
    def ref(self) -> LoopDefinitionRef:
        return LoopDefinitionRef(
            self.definition_id, self.version, self.content_digest)

    def to_dict(self) -> dict:
        value = self._canonical_body()
        value["content_digest"] = self.content_digest
        return value

    @classmethod
    def from_dict(cls, value: dict) -> "LoopDefinition":
        required = {
            "record_type", "definition_id", "version", "role_profile",
            "contract", "configuration_facts", "supported_modes",
            "installed_executor_modes", "step_profile", "loop_condition",
            "exit_condition", "effects", "permissions",
            "required_capabilities", "content_digest",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise LoopDefinitionError("LoopDefinition has an invalid shape")
        if value["record_type"] != "loop_definition/v1":
            raise LoopDefinitionError("unsupported LoopDefinition record type")
        role_profile = value["role_profile"]
        if not isinstance(role_profile, dict) or set(role_profile) != {
                "profile_id", "version"}:
            raise LoopDefinitionError("role_profile has an invalid shape")
        contract_values = value["contract"]
        if not isinstance(contract_values, dict) or set(contract_values) != {
                "name", "execution_mode", "input_roles", "output_roles",
                "effects", "locality", "cost_class", "role"}:
            raise LoopDefinitionError("contract has an invalid shape")
        definition = cls(
            definition_id=value["definition_id"], version=value["version"],
            role_profile_id=role_profile["profile_id"],
            role_profile_version=role_profile["version"],
            contract=LoopContract(
                **{**contract_values,
                   "input_roles": tuple(contract_values["input_roles"]),
                   "output_roles": tuple(contract_values["output_roles"]),
                   "effects": tuple(contract_values["effects"])}),
            configuration_facts=ConfigurationFacts.from_mapping(
                value["configuration_facts"]),
            supported_modes=tuple(value["supported_modes"]),
            installed_executor_modes=tuple(value["installed_executor_modes"]),
            step_profile=value["step_profile"],
            loop_condition=value["loop_condition"],
            exit_condition=value["exit_condition"],
            effects=tuple(value["effects"]),
            permissions=tuple(value["permissions"]),
            required_capabilities=tuple(value["required_capabilities"]),
        )
        expected = value["content_digest"]
        if not isinstance(expected, str) or not _DIGEST.fullmatch(expected):
            raise LoopDefinitionError(
                "content_digest must be a lowercase SHA-256 digest")
        if definition.content_digest != expected:
            raise LoopDefinitionError(
                "LoopDefinition content digest does not match its content")
        return definition

    @classmethod
    def from_runtime(cls, *, identity: LoopRoleIdentity, contract: Any,
                     config: Any, definition_id: str = "", version: str = "",
                     installed_executor_modes=(), permissions=(),
                     compatibility: bool = False) -> "LoopDefinition":
        """Compose the established runtime fields into one strict definition."""
        if not isinstance(identity, LoopRoleIdentity):
            raise LoopDefinitionError("identity must be LoopRoleIdentity")
        supported = tuple(config.allowable_modes)
        terminal_execution_mode = (
            "model_led" if "non_deterministic" in supported
            else "hybrid" if "hybrid" in supported else "code_only")
        if isinstance(contract, LoopContract):
            current_contract = contract
            if compatibility and contract.role != identity.role.value:
                current_contract = replace(contract, role=identity.role.value)
        else:
            output_roles = tuple(getattr(contract, "output_roles", ())) or (
                "result",)
            input_roles = tuple(getattr(contract, "input_roles", ()))
            effects = tuple(getattr(contract, "effects", ("pure",)))
            current_contract = LoopContract(
                name=str(getattr(contract, "goal", "loop work")),
                execution_mode=terminal_execution_mode,
                input_roles=input_roles, output_roles=output_roles,
                effects=effects, role=identity.role.value)
        if compatibility and current_contract.runtime_mode not in supported:
            current_contract = replace(
                current_contract, execution_mode=terminal_execution_mode,
                role=identity.role.value)

        from .loop_profile_catalog import LoopProfileRef
        from .loop_profile_ontology import resolve_profile
        try:
            resolved = resolve_profile(LoopProfileRef(
                identity.profile_id, identity.profile_version))
        except Exception as exc:
            raise LoopDefinitionError(
                "role profile is not registered") from exc
        preferred_modes = tuple(
            mode for mode in config.preferred_modes if mode in supported)
        if not preferred_modes:
            preferred_modes = supported
        facts = ConfigurationFacts.from_mapping({
            "framework": config.framework,
            "logical_kind": config.logical_kind,
            "replay_guarantee": config.replay_guarantee,
            "allowable_modes": list(supported),
            "preferred_modes": list(preferred_modes),
            "delegated_modes": list(config.delegated_modes),
            "power": config.power,
            "llm_thinking_power": config.llm_thinking_power,
            "custom_steps": list(config.custom_steps),
            "max_depth": config.max_depth,
            "loop_condition": config.loop_condition,
            "exit_condition": config.exit_condition,
            "success_confidence_min": config.success_confidence_min,
        })
        return cls(
            definition_id=definition_id or identity.profile_id,
            version=version or identity.profile_version,
            role_profile_id=identity.profile_id,
            role_profile_version=identity.profile_version,
            contract=current_contract,
            configuration_facts=facts,
            supported_modes=supported,
            installed_executor_modes=(
                tuple(installed_executor_modes) if installed_executor_modes
                else supported),
            step_profile=resolved.step_template_id,
            loop_condition=config.loop_condition,
            exit_condition=config.exit_condition,
            effects=tuple(current_contract.effects),
            permissions=tuple(permissions),
            required_capabilities=resolved.required_capabilities,
        )

    def to_loop_config(self):
        """Build the current mutable execution state from immutable facts."""
        from .recursive_loop import LoopConfig
        facts = self.configuration_facts.to_dict()
        return LoopConfig(
            framework=facts.get("framework", "nine_step"),
            logical_kind=facts.get("logical_kind", "execution"),
            replay_guarantee=facts.get("replay_guarantee", "event_equivalent"),
            allowable_modes=self.supported_modes,
            preferred_modes=tuple(
                facts.get("preferred_modes", self.supported_modes)),
            delegated_modes=tuple(
                facts.get("delegated_modes", self.supported_modes)),
            power=facts.get("power", "standard"),
            llm_thinking_power=facts.get("llm_thinking_power", ""),
            custom_steps=tuple(facts.get("custom_steps", ())),
            max_depth=int(facts.get("max_depth", 3)),
            loop_condition=self.loop_condition,
            exit_condition=self.exit_condition,
            success_confidence_min=float(
                facts.get("success_confidence_min", 0.5)),
        )


@dataclass(frozen=True)
class LoopStartRequest:
    """One object that carries every public input needed to start a Loop."""

    goal: str
    definition: LoopDefinition
    relationship: LoopRelationship
    runtime_context: LoopRuntimeContext
    event_log: Any = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise LoopDefinitionError("a Loop start request needs a goal")
        if not isinstance(self.definition, LoopDefinition):
            raise LoopDefinitionError("definition must be a LoopDefinition")
        if not isinstance(self.relationship, LoopRelationship):
            raise LoopDefinitionError(
                "relationship must be a LoopRelationship")
        if not isinstance(self.runtime_context, LoopRuntimeContext):
            raise LoopDefinitionError(
                "runtime_context must be a LoopRuntimeContext")
        if (self.event_log is None
                or not callable(getattr(self.event_log, "next_id", None))
                or not callable(getattr(self.event_log, "record", None))
                or not callable(getattr(
                    self.event_log, "register_definition", None))):
            raise LoopDefinitionError(
                "event_log must provide next_id(), record(), and "
                "register_definition()")
        try:
            self.runtime_context.require(
                capabilities=self.definition.required_capabilities,
                permissions=self.definition.permissions,
                executor_modes=self.definition.installed_executor_modes)
        except LoopRuntimeContextError as exc:
            raise LoopDefinitionError(
                f"runtime context cannot start this Loop: {exc}") from exc
