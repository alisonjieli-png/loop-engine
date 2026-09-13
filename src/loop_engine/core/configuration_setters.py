"""Checked configuration changes through existing parameter precedence and Loop.

This first setter changes only caller-supplied dataclass configurations. It
never mutates a running harness, writes a native configuration file, calls a
provider, or grants effects. Agentic proposals remain lower-priority inputs;
explicit pins and exact target/source identities survive the resolution.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass, replace
from datetime import datetime

from ..loop.loop_control import MODES
from .configuration_capabilities import (
    ConfigurationCapabilityError, ConfigurationTargetSpec, describe_configuration,
    canonical, digest, exact_digest, exact_text)
from .harness_execution_contracts import plain_harness_json
from .parameter_resolution import (
    ParameterInput, ParameterIntelligenceProposal, ParameterResolutionRequest,
    ParameterResolutionStatus, ParameterSource, ParameterSourceKind, ParameterValueState,
    SOURCE_PRECEDENCE, resolve_parameter)
from .record_operations_records import parse_json

# When a configuration change may take effect.
CHANGE_PHASES = ("before_initialization", "per_request", "between_steps")
BEFORE_INITIALIZATION, PER_REQUEST, BETWEEN_STEPS = CHANGE_PHASES


@dataclass(frozen=True)
class ConfigurationValueCandidate:
    """One initial or ordered alternative value, without mutation authority."""

    input: ParameterInput
    intelligence: ParameterIntelligenceProposal | None = None
    _snapshot_json: str = field(init=False, repr=False)

    def __post_init__(self):
        if not isinstance(self.input, ParameterInput):
            raise ConfigurationCapabilityError("configuration candidate needs a tagged parameter input")
        plain_harness_json(self.input.value)
        if self.intelligence is not None:
            if not isinstance(self.intelligence, ParameterIntelligenceProposal):
                raise ConfigurationCapabilityError("intelligence proposal must use its typed contract")
            if (self.intelligence.proposed_input.state != self.input.state
                    or digest(self.intelligence.proposed_input.value) != digest(self.input.value)):
                raise ConfigurationCapabilityError("intelligence proposal does not bind the selected value")
        value = {"input": {"state": self.input.state.value, "value": self.input.value},
                 "intelligence": asdict(self.intelligence) if self.intelligence is not None else None}
        if value["intelligence"] is not None:
            value["intelligence"]["proposed_input"]["state"] = self.input.state.value
        object.__setattr__(self, "_snapshot_json", canonical(value))

    def snapshot(self):
        """Detach the construction-time values from caller-owned mutable aliases."""
        value = parse_json(self._snapshot_json)
        selected = ParameterInput(**value["input"])
        proposal = value["intelligence"]
        if proposal is not None:
            proposal["proposed_input"] = ParameterInput(**proposal["proposed_input"])
            for name in ("evidence_refs", "assumptions", "unknowns", "alternatives"):
                proposal[name] = tuple(proposal[name])
            proposal = ParameterIntelligenceProposal(**proposal)
        return selected, proposal


@dataclass(frozen=True)
class ConfigurationSettingChange:
    """The first candidate is initial; later candidates are ordered fallbacks."""

    parameter_id: str
    candidates: tuple[ConfigurationValueCandidate, ...]

    def __post_init__(self):
        exact_text(self.parameter_id, "parameter identity")
        values = tuple(self.candidates)
        if not values or any(not isinstance(v, ConfigurationValueCandidate) for v in values):
            raise ConfigurationCapabilityError("setting change needs typed ordered candidates")
        object.__setattr__(self, "candidates", values)


@dataclass(frozen=True)
class ConfigurationWriteAuthority:
    """Host-supplied permission to edit named settings, never effect authority."""

    target_ref: str
    allowed_parameter_ids: tuple[str, ...]
    source_kind: ParameterSourceKind
    source_ref: str
    source_version: str
    allow_unqualified: bool = False
    allow_unavailable: bool = False

    def __post_init__(self):
        for name in ("target_ref", "source_ref", "source_version"):
            exact_text(getattr(self, name), name)
        object.__setattr__(self, "source_kind", ParameterSourceKind(self.source_kind))
        values = tuple(self.allowed_parameter_ids)
        if len(set(values)) != len(values):
            raise ConfigurationCapabilityError("setting grants cannot repeat")
        for value in values:
            exact_text(value, "allowed setting")
        object.__setattr__(self, "allowed_parameter_ids", values)
        if type(self.allow_unqualified) is not bool or type(self.allow_unavailable) is not bool:
            raise ConfigurationCapabilityError("experimental allowances must be Booleans")


@dataclass(frozen=True)
class ConfigurationUpdateRequest:
    """A compare-and-swap request over the settings this target owns."""

    expected_target_digest: str
    expected_values_digest: str
    changes: tuple[ConfigurationSettingChange, ...]
    phase: str
    run_mode: str

    def __post_init__(self):
        exact_digest(self.expected_target_digest, "target digest")
        exact_digest(self.expected_values_digest, "current values digest")
        values = tuple(self.changes)
        if (not values or any(not isinstance(v, ConfigurationSettingChange) for v in values)
                or len({v.parameter_id for v in values}) != len(values)):
            raise ConfigurationCapabilityError("update needs unique typed setting changes")
        if self.phase not in CHANGE_PHASES:
            raise ConfigurationCapabilityError("unknown configuration change phase")
        if self.run_mode not in MODES:
            raise ConfigurationCapabilityError("unknown run mode")
        object.__setattr__(self, "changes", values)


@dataclass(frozen=True)
class ConfigurationSetterContext:
    """Existing target, host authority, and earlier owned parameter sources."""

    target: ConfigurationTargetSpec
    current: object = field(repr=False)
    authority: ConfigurationWriteAuthority
    as_of: datetime
    prior_sources: tuple[tuple[str, ParameterSource], ...] = ()

    def __post_init__(self):
        if (not isinstance(self.target, ConfigurationTargetSpec)
                or not isinstance(self.authority, ConfigurationWriteAuthority)
                or not is_dataclass(self.current) or isinstance(self.current, type)
                or not isinstance(self.as_of, datetime) or self.as_of.tzinfo is None):
            raise ConfigurationCapabilityError("setter context requires typed facts, authority, instance, and time")
        sources = tuple(self.prior_sources)
        if any(len(item) != 2 or not isinstance(item[1], ParameterSource)
               or type(item[1].authorized) is not bool for item in sources):
            raise ConfigurationCapabilityError("prior setting sources must be typed")
        keys = []
        for key, source in sources:
            exact_text(key, "prior parameter identity")
            if not isinstance(source.input, ParameterInput):
                raise ConfigurationCapabilityError("prior setting source input must be typed")
            keys.append((key, source.source_kind))
        if len(set(keys)) != len(keys):
            raise ConfigurationCapabilityError("prior setting sources cannot repeat a scope")
        object.__setattr__(self, "prior_sources", sources)


@dataclass(frozen=True)
class ConfigurationUpdateResult:
    """New in-memory configuration plus a secret-safe change report."""

    configuration: object = field(repr=False)
    report: dict


def _apply(request, context):
    target, current, authority = context.target, context.current, context.authority
    before = describe_configuration(target, current, at=context.as_of)
    report = {"record_type": "configuration_update/v1", "target_ref": target.target_ref,
        "as_of": context.as_of.isoformat(),
        "request": {"expected_target_digest": request.expected_target_digest,
            "expected_values_digest": request.expected_values_digest,
            "phase": request.phase, "run_mode": request.run_mode,
            "changes": [{"parameter_id": change.parameter_id,
                "ordered_candidate_digests": [digest(parse_json(c._snapshot_json)) for c in change.candidates]}
                for change in request.changes]},
        "authority": {**asdict(authority), "source_kind": authority.source_kind.value},
        "before": before, "status": "rejected", "attempts": [], "rejections": [],
        "dispatch_performed": False, "native_harness_reconfigured": False,
        "effect_authority_granted": False, "qualification_invalidated": False}
    if (authority.target_ref != target.target_ref
            or request.expected_target_digest != before["target_digest"]
            or request.expected_values_digest != before["values_digest"]):
        report["rejections"].append({"reason": "stale_or_different_target"})
        return ConfigurationUpdateResult(current, report)
    bindings = {s.parameter_id: s for s in target.settings}
    updates = {}
    explicit = authority.source_kind in (ParameterSourceKind.EXPLICIT_INVOCATION,
                                         ParameterSourceKind.RUN_OVERRIDE)
    for change in request.changes:
        setting = bindings.get(change.parameter_id)
        reason = ""
        if setting is None:
            reason = "unknown_setting"
        elif change.parameter_id not in authority.allowed_parameter_ids:
            reason = "setting_change_not_authorized"
        elif not setting.writable or setting.authority_bearing:
            reason = "read_only_or_authority_bearing_setting"
        elif setting.support.current_state(context.as_of) != "supported":
            reason = "setting_" + setting.support.current_state(context.as_of)
        elif request.phase not in setting.phases:
            reason = "setting_requires_another_binding_phase"
        elif request.run_mode not in setting.run_modes:
            reason = "setting_inactive_for_selected_mode"
        elif not authority.allow_unavailable and setting.availability.current_state(context.as_of) != "available":
            reason = "setting_not_currently_available"
        elif not authority.allow_unqualified and setting.qualification.current_state(context.as_of) != "qualified":
            reason = "setting_not_qualified"
        if reason:
            report["rejections"].append({"parameter_id": change.parameter_id, "reason": reason})
            continue
        parameter = setting.parameter()
        resolved = None
        for position, candidate in enumerate(change.candidates):
            selected_input, selected_intelligence = candidate.snapshot()
            previous = tuple(source for key, source in context.prior_sources
                             if key == change.parameter_id and source.source_kind != authority.source_kind)
            definition = parameter
            if selected_input.state != ParameterValueState.OMITTED:
                # Try this source's ordered candidates before its lower-
                # priority defaults. Higher-priority explicit pins still win.
                previous = tuple(source for source in previous if SOURCE_PRECEDENCE[source.source_kind]
                                 < SOURCE_PRECEDENCE[authority.source_kind])
                if SOURCE_PRECEDENCE[authority.source_kind] <= SOURCE_PRECEDENCE[ParameterSourceKind.REPOSITORY_DEFAULT]:
                    definition = replace(parameter, default_input=ParameterInput.omitted())
            if authority.source_kind == ParameterSourceKind.INTELLIGENCE_PROPOSAL:
                sources = previous
                intelligence = selected_intelligence
                if intelligence is None:
                    report["rejections"].append({"parameter_id": change.parameter_id,
                                                  "reason": "agentic_change_lacks_typed_proposal"})
                    break
            else:
                sources = previous + (ParameterSource(authority.source_kind, authority.source_ref,
                                                     authority.source_version, selected_input),)
                intelligence = None
            resolution = resolve_parameter(ParameterResolutionRequest(definition, sources, intelligence))
            safe_resolution = resolution.to_dict()
            # An agent's abstention reason is arbitrary text. It must not
            # disclose a sensitive setting through the resolution trace.
            if parameter.sensitivity == "sensitive":
                for trace in safe_resolution["resolution_trace"]:
                    if trace["source_kind"] == ParameterSourceKind.INTELLIGENCE_PROPOSAL.value:
                        trace["reason"] = "sensitive proposal disposition recorded"
            report["attempts"].append({"parameter_id": change.parameter_id,
                "candidate_position": position, "resolution": safe_resolution})
            if resolution.status == ParameterResolutionStatus.RESOLVED:
                resolved = resolution
                break
            if explicit:
                break
        if resolved is None:
            report["rejections"].append({"parameter_id": change.parameter_id,
                                          "reason": "no_candidate_resolved"})
            continue
        value = plain_harness_json(resolved.value)
        if setting.value_codec == "tuple":
            if not isinstance(value, list):
                report["rejections"].append({"parameter_id": change.parameter_id,
                                              "reason": "tuple_codec_requires_sequence"})
                continue
            value = tuple(value)
        updates[setting.target_field] = value
    if report["rejections"]:
        return ConfigurationUpdateResult(current, report)
    try:
        updated = replace(current, **updates)
        after = describe_configuration(target, updated, at=context.as_of)
    except (ValueError, TypeError):
        report["rejections"].append({"reason": "target_constructor_refused_configuration"})
        return ConfigurationUpdateResult(current, report)
    changed = after["values_digest"] != before["values_digest"]
    report.update(status="applied_in_memory" if changed else "unchanged", after=after,
                  qualification_invalidated=changed)
    return ConfigurationUpdateResult(updated, report)


def apply_configuration_as_loop(request: ConfigurationUpdateRequest,
                                context: ConfigurationSetterContext, *, parent=None):
    """Resolve and apply an atomic in-memory change through the canonical Loop."""
    from ..loop.encapsulate import as_practitioner_loop
    if not isinstance(request, ConfigurationUpdateRequest) or not isinstance(context, ConfigurationSetterContext):
        raise ConfigurationCapabilityError("configuration setter needs typed request and context")
    holder = {}
    def apply():
        result = _apply(request, context)
        holder["result"] = result
        return result.report
    run = as_practitioner_loop("resolve and apply authorized configuration settings", apply, parent=parent)
    return holder["result"], run


def self_test():
    from .configuration_setter_checks import run_checks
    return run_checks()
