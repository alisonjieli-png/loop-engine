"""The layering dimensions as a configuration target the setters can inspect.

The configuration capability records describe, per setting, whether it is
supported, available now, and qualified, separately from permission to
change it. The two layering axes become two settings on a
``LayeringConfiguration``: the control policy index and the composition
index. Their facts come from the availability projection, so a setter or a
meta-selector learns eligibility from the same rule the semantic binding
applies at invocation: support is declared by the space, availability is
"available" when at least one address executes today and "unavailable"
otherwise, and qualification stays unknown unless the caller supplies a
fact from independent evidence, since no layered executor has been
qualified. The allowed values of the control policy setting are exactly the
policies whose direct-adapter address executes now, and the composition
setting allows only the direct adapter until a wrapper executor exists. The
declared-but-unexecutable remainder stays visible in the availability
summary that travels with the target.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json

from .configuration_capabilities import (ConfigurationCapabilityError, ConfigurationFact,
                                         ConfigurationSettingSpec, ConfigurationTargetSpec,
                                         describe_configuration)
from .external_harness import HARNESS_MODES
from .harness_layering import HarnessLayeringError, LayeredHarnessBinding
from .harness_layering_availability import availability_summary
from .harness_layering_space import LayeringSpace
from .parameter_resolution import ParameterDefinition

LAYERING_CONFIGURATION_RECORD_TYPE = "harness_layering_configuration/v1"
AVAILABILITY_SOURCE_REF = "core.harness_layering_availability@1.0.0"
POLICY_SETTING = "harness_layering.control_policy_index"
COMPOSITION_SETTING = "harness_layering.composition_index"


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LayeringConfiguration:
    """The two layering settings of one assignment, as plain indices."""

    control_policy_index: int = 0
    composition_index: int = 0

    def __post_init__(self):
        for name in ("control_policy_index", "composition_index"):
            value = getattr(self, name)
            if type(value) is not int or isinstance(value, bool) or value < 0:
                raise HarnessLayeringError(f"{name} must be a non-negative integer")

    @classmethod
    def from_binding(cls, space: LayeringSpace, binding: LayeredHarnessBinding):
        if not isinstance(space, LayeringSpace) or not isinstance(binding, LayeredHarnessBinding):
            raise HarnessLayeringError("a configuration is read from a typed space and binding")
        return cls(space.policies.index_of(binding.control_policy),
                   space.compositions.index_of(binding.initial))

    def binding(self, space: LayeringSpace) -> LayeredHarnessBinding:
        if not isinstance(space, LayeringSpace):
            raise HarnessLayeringError("a configuration binds within a typed space")
        return space.candidate_at(space.encode(self.composition_index, self.control_policy_index))


def _setting(parameter_id, field_name, description, allowed, maximum, facts):
    parameter = ParameterDefinition(
        parameter_id, field_name, description, "integer",
        "core.harness_layering_space@1.0.0", "request",
        constraints={"allowed_values": list(allowed), "minimum": 0, "maximum": maximum})
    return ConfigurationSettingSpec.from_parameter(
        parameter, field_name, writable=True, phases=("before_initialization",),
        run_modes=HARNESS_MODES, **facts)


def layering_configuration_target(space: LayeringSpace, *, source_ref: str, source_digest: str,
                                  adapter_native_controls=(), locality: str = "not_applicable",
                                  qualification: ConfigurationFact | None = None
                                  ) -> ConfigurationTargetSpec:
    """The configuration target for one assignment's layering space.

    ``source_ref`` and ``source_digest`` name the owner that supplies the
    target (the assignment or its harness manifest). The facts cite the
    availability projection by its digest, so a changed projection changes
    the target's digest. Locality is descriptive metadata the record format
    asks for; layering does not depend on where an endpoint is, so it
    defaults to not applicable."""
    if not isinstance(space, LayeringSpace):
        raise HarnessLayeringError("a configuration target needs a typed LayeringSpace")
    if qualification is not None and not isinstance(qualification, ConfigurationFact):
        raise ConfigurationCapabilityError("qualification must be a typed configuration fact")
    summary = availability_summary(space, adapter_native_controls)
    summary_digest = _digest(summary)
    executable_policies = sorted({space.decode(index)[1] for index in summary["executable_now_indices"]})
    executable = bool(executable_policies)
    facts = {"support": ConfigurationFact("supported", AVAILABILITY_SOURCE_REF, summary_digest),
             "availability": ConfigurationFact("available" if executable else "unavailable",
                                               AVAILABILITY_SOURCE_REF, summary_digest),
             "qualification": qualification or ConfigurationFact()}
    settings = (
        _setting(POLICY_SETTING, "control_policy_index",
                 "Index of the native control policy in the assignment's control policy space; "
                 "the allowed values are the policies whose direct-adapter address executes today.",
                 executable_policies, space.policies.size - 1, facts),
        _setting(COMPOSITION_SETTING, "composition_index",
                 "Index of the wrapper composition in the assignment's composition space; only "
                 "the direct adapter (index 0) executes until a wrapper executor is registered.",
                 [0] if executable else [], space.compositions.size - 1, facts),
    )
    return ConfigurationTargetSpec("harness_layering:" + space.assignment_ref, settings,
                                   source_ref, source_digest, locality)


def layering_configuration_record(space: LayeringSpace, **options) -> dict:
    """The target and the availability summary it was derived from, joined
    so a reader sees the executable choices and the declared remainder."""
    target = layering_configuration_target(space, **options)
    # The setting records carry tuples; a stored record is plain JSON.
    plain = json.loads(json.dumps(target.to_dict(), allow_nan=False))
    return {"record_type": LAYERING_CONFIGURATION_RECORD_TYPE, "target": plain,
            "availability": availability_summary(space, options.get("adapter_native_controls", ()))}


def describe_layering_configuration(space: LayeringSpace, configuration: LayeringConfiguration,
                                    *, at: datetime, **options) -> dict:
    """Inspect one layering configuration through the setters' own view."""
    if not isinstance(configuration, LayeringConfiguration):
        raise HarnessLayeringError("inspection needs a typed LayeringConfiguration")
    return describe_configuration(layering_configuration_target(space, **options),
                                  configuration, at=at)


def self_test() -> dict:
    from .harness_layering_configuration_checks import run_checks
    return run_checks()
