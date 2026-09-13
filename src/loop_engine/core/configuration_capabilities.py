"""Versioned setting capabilities for existing configuration and adapter owners.

Support, availability, qualification, locality, mutability, and permissions
are separate facts. These records do not probe providers, install harnesses,
create another settings store, or grant execution authority. Parameter meaning
and precedence remain owned by the existing parameter-resolution contracts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json

from .harness_execution_contracts import plain_harness_json
from .parameter_resolution import ParameterDefinition, ParameterInput
from .record_operations_records import parse_json

# The states a configuration fact can be in: support, availability, and
# qualification are separate facts, each with its own pair plus unknown.
CONFIGURATION_FACT_STATES = ("supported", "unsupported", "available", "unavailable",
                             "qualified", "unqualified", "unknown")
(SUPPORTED, UNSUPPORTED, AVAILABLE, UNAVAILABLE, QUALIFIED, UNQUALIFIED,
 UNKNOWN_FACT) = CONFIGURATION_FACT_STATES
AVAILABILITY_STATES = (AVAILABLE, UNAVAILABLE, UNKNOWN_FACT)
QUALIFICATION_STATES = (QUALIFIED, UNQUALIFIED, UNKNOWN_FACT)


class ConfigurationCapabilityError(ValueError):
    """Configuration cannot be represented or supported as requested."""


def canonical(value) -> str:
    return json.dumps(plain_harness_json(value), sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def exact_text(value, name):
    if (type(value) is not str or not value.strip() or value != value.strip()
            or any(ord(c) < 32 for c in value)):
        raise ConfigurationCapabilityError(name + " must be exact nonempty text")


def exact_digest(value, name):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ConfigurationCapabilityError(name + " must be a SHA-256 digest")


@dataclass(frozen=True)
class ConfigurationFact:
    """A sourced capability state, not an assertion made by a model proposal."""

    state: str = "unknown"
    source_ref: str = ""
    source_digest: str = ""
    expires_at: str = ""

    def __post_init__(self):
        if self.state not in CONFIGURATION_FACT_STATES:
            raise ConfigurationCapabilityError("unknown configuration fact state")
        if type(self.source_ref) is not str or type(self.source_digest) is not str:
            raise ConfigurationCapabilityError("fact source and digest must be text")
        if self.state != UNKNOWN_FACT:
            exact_text(self.source_ref, "fact source")
            exact_digest(self.source_digest, "fact source digest")
        if type(self.expires_at) is not str:
            raise ConfigurationCapabilityError("capability expiry must be ISO 8601 text")
        if self.expires_at:
            try:
                parsed = datetime.fromisoformat(self.expires_at.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ConfigurationCapabilityError("capability expiry is not ISO 8601") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ConfigurationCapabilityError("capability expiry needs a timezone")
            # One instant, one spelling: the same expiry written with Z or
            # +00:00 must digest identically.
            object.__setattr__(self, "expires_at", parsed.astimezone(timezone.utc).isoformat())

    def current_state(self, at: datetime) -> str:
        if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
            raise ConfigurationCapabilityError("capability observation time needs a timezone")
        if self.expires_at and at >= datetime.fromisoformat(self.expires_at.replace("Z", "+00:00")):
            return "unknown"
        return self.state


@dataclass(frozen=True)
class ConfigurationSettingSpec:
    """One explicit field binding with a frozen existing ParameterDefinition."""

    parameter_json: str
    target_field: str
    support: ConfigurationFact = ConfigurationFact()
    availability: ConfigurationFact = ConfigurationFact()
    qualification: ConfigurationFact = ConfigurationFact()
    phases: tuple[str, ...] = ("before_initialization",)
    run_modes: tuple[str, ...] = ("deterministic", "hybrid", "non_deterministic")
    writable: bool = False
    authority_bearing: bool = False
    value_codec: str = "identity"

    def __post_init__(self):
        exact_text(self.target_field, "target field")
        if not self.target_field.isidentifier() or self.target_field.startswith("_"):
            raise ConfigurationCapabilityError("setting target must be an explicit public field")
        record = parse_json(self.parameter_json)
        expected = {field.name for field in fields(ParameterDefinition)}
        if not isinstance(record, dict) or set(record) != expected:
            raise ConfigurationCapabilityError("setting needs an exact parameter definition")
        object.__setattr__(self, "parameter_json", canonical(record))
        parameter = self.parameter()
        for name in ("required", "nullable", "intelligence_allowed", "affects_semantic_identity", "affects_qualification"):
            if type(getattr(parameter, name)) is not bool:
                raise ConfigurationCapabilityError("parameter switches must be Booleans")
        constraints = parameter.constraints
        if (not isinstance(constraints, dict) or not set(constraints)
                <= {"allowed_values", "non_empty", "minimum", "maximum"}):
            raise ConfigurationCapabilityError("setting constraints must be supported by the parameter resolver")
        for bound in ("minimum", "maximum"):
            if bound in constraints and (isinstance(constraints[bound], bool)
                                         or not isinstance(constraints[bound], (int, float))):
                raise ConfigurationCapabilityError(f"constraint {bound} must be a number")
        if "allowed_values" in constraints and not isinstance(constraints["allowed_values"], (list, tuple)):
            raise ConfigurationCapabilityError("constraint allowed_values must be a sequence")
        if "non_empty" in constraints and type(constraints["non_empty"]) is not bool:
            raise ConfigurationCapabilityError("constraint non_empty must be a Boolean")
        for name, states in (("support", ("supported", "unsupported", "unknown")),
                             ("availability", ("available", "unavailable", "unknown")),
                             ("qualification", ("qualified", "unqualified", "unknown"))):
            fact = getattr(self, name)
            if not isinstance(fact, ConfigurationFact) or fact.state not in states:
                raise ConfigurationCapabilityError(name + " must retain its separate fact state")
        phases, modes = tuple(self.phases), tuple(self.run_modes)
        if (not phases or not set(phases) <= {"before_initialization", "per_request", "between_steps"}
                or not modes or not set(modes) <= {"deterministic", "hybrid", "non_deterministic"}
                or len(set(phases)) != len(phases) or len(set(modes)) != len(modes)):
            raise ConfigurationCapabilityError("invalid binding phase or mode contract")
        if type(self.writable) is not bool or type(self.authority_bearing) is not bool:
            raise ConfigurationCapabilityError("mutability facts must be Booleans")
        if self.value_codec not in ("identity", "tuple"):
            raise ConfigurationCapabilityError("unknown setting value codec")
        object.__setattr__(self, "phases", phases)
        object.__setattr__(self, "run_modes", modes)

    @classmethod
    def from_parameter(cls, parameter: ParameterDefinition, target_field: str, **facts):
        if not isinstance(parameter, ParameterDefinition):
            raise ConfigurationCapabilityError("setting requires ParameterDefinition")
        value = asdict(parameter)
        value["default_input"]["state"] = parameter.default_input.state.value
        return cls(canonical(value), target_field, **facts)

    def parameter(self) -> ParameterDefinition:
        value = parse_json(self.parameter_json)
        value["default_input"] = ParameterInput(**value["default_input"])
        value["aliases"] = tuple(value["aliases"])
        value["deprecated_aliases"] = tuple(value["deprecated_aliases"])
        return ParameterDefinition(**value)

    @property
    def parameter_id(self):
        return self.parameter().parameter_id

    def to_dict(self):
        value = asdict(self)
        value["phases"], value["run_modes"] = list(self.phases), list(self.run_modes)
        parameter = parse_json(value.pop("parameter_json"))
        if parameter["sensitivity"] == "sensitive":
            parameter["default_input"]["value"] = "<redacted>"
            parameter["constraints"] = {"redacted": True}
        value["parameter"] = parameter
        value["definition_digest"] = digest(parse_json(self.parameter_json))
        return value


@dataclass(frozen=True)
class ConfigurationTargetSpec:
    """One immutable target description supplied by an existing owner."""

    target_ref: str
    settings: tuple[ConfigurationSettingSpec, ...]
    source_ref: str
    source_digest: str
    locality: str = "unknown"
    version: str = "1.0.0"

    def __post_init__(self):
        exact_text(self.target_ref, "configuration target")
        exact_text(self.source_ref, "target source")
        exact_digest(self.source_digest, "target source digest")
        settings = tuple(self.settings)
        if (not settings or any(not isinstance(s, ConfigurationSettingSpec) for s in settings)
                or len({s.parameter_id for s in settings}) != len(settings)
                or len({s.target_field for s in settings}) != len(settings)):
            raise ConfigurationCapabilityError("target settings must have unique identities and fields")
        if self.locality not in ("local", "cloud", "not_applicable", "unknown") or self.version != "1.0.0":
            raise ConfigurationCapabilityError("unknown target locality or version")
        object.__setattr__(self, "settings", settings)

    @property
    def content_digest(self):
        return digest({"target_ref": self.target_ref, "source_ref": self.source_ref,
            "source_digest": self.source_digest, "locality": self.locality, "version": self.version,
            "settings": [{**s.to_dict(), "parameter_json": s.parameter_json} for s in self.settings]})

    def to_dict(self):
        return {"record_type": "configuration_target/v1", "target_ref": self.target_ref,
            "settings": [s.to_dict() for s in self.settings], "source_ref": self.source_ref,
            "source_digest": self.source_digest, "locality": self.locality,
            "version": self.version, "target_digest": self.content_digest}


def describe_configuration(target: ConfigurationTargetSpec, current, *, at: datetime) -> dict:
    """Inspect a caller-supplied dataclass; no provider or harness is invoked."""
    if (not isinstance(target, ConfigurationTargetSpec) or not is_dataclass(current)
            or isinstance(current, type)):
        raise ConfigurationCapabilityError("inspection requires a typed target and dataclass instance")
    rows, values = [], {}
    available_fields = {field.name for field in fields(current)}
    for setting in target.settings:
        if setting.target_field not in available_fields:
            raise ConfigurationCapabilityError("target field is absent from the supplied configuration")
        value = plain_harness_json(getattr(current, setting.target_field))
        values[setting.parameter_id] = value
        parameter = setting.parameter()
        rows.append({"parameter_id": setting.parameter_id, "target_field": setting.target_field,
            "support": setting.support.current_state(at),
            "availability": setting.availability.current_state(at),
            "qualification": setting.qualification.current_state(at),
            "writable": setting.writable, "authority_bearing": setting.authority_bearing,
            "phases": list(setting.phases), "run_modes": list(setting.run_modes),
            "value_state": ParameterInput.from_value(value).state.value,
            "value": "<redacted>" if parameter.sensitivity == "sensitive" else value,
            "value_digest": digest(value)})
    return {"record_type": "configuration_inspection/v1", "target_ref": target.target_ref,
            "target_digest": target.content_digest, "values_digest": digest(values),
            "locality": target.locality, "settings": rows, "provider_calls_made": 0}
