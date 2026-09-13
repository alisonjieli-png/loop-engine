"""Passive records for layered harness wrappers and native control ownership.

Two configuration dimensions the owner asked for on 2026-09-13, recorded in
docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md: which
wrappers compose one harness implementation, and who owns each native
control of the harness. Both are declared, validated, digested, and bound to
one assignment before execution, so a Run History record can name the exact
composition and control policy an attempt ran under.

Nothing here launches a process, enables a native goal, grants tool or effect
authority, or replaces the existing harness registry, fallback policy, or Run
History. A binding without a layering record means the direct adapter, which
is the behavior every current recipe has. The one rule this module enforces
across records is the proposal's coordination requirement for retries: a
native harness may own retry only when the outer fallback policy has said so
explicitly, so a native transport retry can never bypass an outer
semantic-recovery restriction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import re

from .harness_execution_contracts import valid_harness_id
from .harness_fallback import HarnessFailureKind, HarnessFallbackPolicy

#: What one wrapper layer may be responsible for. The vocabulary is closed so
#: two compositions can be compared, and "accounting" is single-owner because
#: physical model calls and external effects are counted once however many
#: wrappers observe them.
WRAPPER_RESPONSIBILITIES = (
    "task_preparation", "instruction_preparation", "context_preparation",
    "intelligence_preparation", "resource_preparation",
    "native_session_bridge", "goal_bridge", "observation_integration",
    "evaluation_integration", "transport", "effect_enforcement",
    "lifecycle", "accounting",
)
SINGLE_OWNER_RESPONSIBILITIES = ("transport", "accounting")

#: What a fallback may change when a permitted failure occurs.
FALLBACK_ACTIONS = ("different_wrapper", "reordered_composition",
                    "native_session_restart", "different_harness")

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}")
_VERSION = re.compile(r"[0-9]+(\.[0-9]+){0,3}([+-][A-Za-z0-9.]{1,32})?")

LAYER_RECORD_TYPE = "harness_wrapper_layer/v1"
COMPOSITION_RECORD_TYPE = "harness_wrapper_composition/v1"
FALLBACK_RECORD_TYPE = "harness_composition_fallback/v1"
CONTROL_POLICY_RECORD_TYPE = "harness_native_control_policy/v1"
BINDING_RECORD_TYPE = "harness_layered_binding/v1"


class HarnessLayeringError(ValueError):
    """A layering record is not a valid declaration."""


def _identifier(value, name):
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise HarnessLayeringError(f"{name} must be a bounded identifier")
    return value


def _version(value, name):
    if type(value) is not str or not _VERSION.fullmatch(value):
        raise HarnessLayeringError(f"{name} must be a bounded version text")
    return value


def _text(value, name, *, limit=512, allow_empty=False):
    if (type(value) is not str or (not value and not allow_empty)
            or value != value.strip() or len(value) > limit
            or any(ord(c) < 32 for c in value)):
        raise HarnessLayeringError(f"{name} must be bounded exact text")
    return value


def _names(values, name, *, vocabulary=None):
    if type(values) not in (tuple, list):
        raise HarnessLayeringError(f"{name} must be an explicit sequence")
    items = tuple(values)
    for item in items:
        _identifier(item, f"{name} entry")
        if vocabulary is not None and item not in vocabulary:
            raise HarnessLayeringError(f"{name} entry {item!r} is outside the closed vocabulary")
    if len(set(items)) != len(items):
        raise HarnessLayeringError(f"{name} entries must not repeat")
    return items


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _settings(value, name):
    """Settings are passive data: finite JSON with text keys, bounded size."""
    if type(value) is not dict:
        raise HarnessLayeringError(f"{name} must be a mapping")
    try:
        text = _canonical(value)
    except (TypeError, ValueError) as exc:
        raise HarnessLayeringError(f"{name} must be plain JSON data") from exc
    if len(text) > 16384:
        raise HarnessLayeringError(f"{name} is larger than the 16 KB bound")
    if any(type(key) is not str for key in value):
        raise HarnessLayeringError(f"{name} keys must be text")
    return json.loads(text)


@dataclass(frozen=True)
class WrapperLayer:
    """One wrapper in a composition: identity, version, and declared duties.

    ``inspects`` and ``transforms`` name the information classes the wrapper
    may read or rewrite (instructions, context, resources, events, outputs)
    so a reviewer can tell an observing wrapper from an enforcing one.
    ``depends_on`` names wrappers that must sit earlier in the composition,
    because layer order changes behavior.
    """

    wrapper_id: str
    version: str
    responsibilities: tuple[str, ...]
    inspects: tuple[str, ...] = ()
    transforms: tuple[str, ...] = ()
    settings: dict = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    initialization: str = ""
    teardown: str = ""

    def __post_init__(self):
        _identifier(self.wrapper_id, "wrapper_id")
        _version(self.version, "wrapper version")
        duties = _names(self.responsibilities, "responsibilities",
                        vocabulary=WRAPPER_RESPONSIBILITIES)
        if not duties:
            raise HarnessLayeringError("a wrapper layer must declare at least one responsibility")
        object.__setattr__(self, "responsibilities", duties)
        object.__setattr__(self, "inspects", _names(self.inspects, "inspects"))
        object.__setattr__(self, "transforms", _names(self.transforms, "transforms"))
        object.__setattr__(self, "settings", _settings(self.settings, "settings"))
        object.__setattr__(self, "depends_on", _names(self.depends_on, "depends_on"))
        if self.wrapper_id in self.depends_on:
            raise HarnessLayeringError("a wrapper cannot depend on itself")
        object.__setattr__(self, "initialization",
                           _text(self.initialization, "initialization", allow_empty=True))
        object.__setattr__(self, "teardown", _text(self.teardown, "teardown", allow_empty=True))

    def to_dict(self) -> dict:
        return {"record_type": LAYER_RECORD_TYPE, "wrapper_id": self.wrapper_id,
                "version": self.version, "responsibilities": list(self.responsibilities),
                "inspects": list(self.inspects), "transforms": list(self.transforms),
                "settings": self.settings, "depends_on": list(self.depends_on),
                "initialization": self.initialization, "teardown": self.teardown}

    @classmethod
    def from_dict(cls, value) -> "WrapperLayer":
        _expect(value, LAYER_RECORD_TYPE, {"wrapper_id", "version", "responsibilities",
                "inspects", "transforms", "settings", "depends_on", "initialization", "teardown"})
        return cls(value["wrapper_id"], value["version"], tuple(value["responsibilities"]),
                   tuple(value["inspects"]), tuple(value["transforms"]), dict(value["settings"]),
                   tuple(value["depends_on"]), value["initialization"], value["teardown"])


def _expect(value, record_type, keys):
    if type(value) is not dict or value.get("record_type") != record_type:
        raise HarnessLayeringError(f"expected a {record_type} record")
    if set(value) != keys | {"record_type"}:
        raise HarnessLayeringError(f"{record_type} has unexpected or missing fields")
    for key in keys:
        if type(value[key]) not in (str, list, dict, bool, int):
            raise HarnessLayeringError(f"{record_type}.{key} has an unsupported value type")


@dataclass(frozen=True)
class WrapperComposition:
    """The ordered wrappers around one registered harness.

    An empty composition is the direct adapter, which is the comparison
    baseline the proposal asks to keep. Order is part of the identity: the
    same layers in another order have another digest.
    """

    composition_id: str
    harness_id: str
    layers: tuple[WrapperLayer, ...] = ()
    version: str = "1.0.0"

    def __post_init__(self):
        _identifier(self.composition_id, "composition_id")
        if not valid_harness_id(self.harness_id):
            raise HarnessLayeringError("a composition must name its registered harness")
        if self.version != "1.0.0":
            raise HarnessLayeringError("unsupported wrapper composition version")
        if type(self.layers) not in (tuple, list) or any(
                not isinstance(item, WrapperLayer) for item in self.layers):
            raise HarnessLayeringError("layers must be typed WrapperLayer records")
        layers = tuple(self.layers)
        ids = [item.wrapper_id for item in layers]
        if len(set(ids)) != len(ids):
            raise HarnessLayeringError("wrapper identities must be unique within a composition")
        seen: set[str] = set()
        for item in layers:
            missing = [dep for dep in item.depends_on if dep not in seen]
            if missing:
                raise HarnessLayeringError(
                    f"wrapper {item.wrapper_id!r} depends on {missing} which must sit earlier")
            seen.add(item.wrapper_id)
        for duty in SINGLE_OWNER_RESPONSIBILITIES:
            owners = [item.wrapper_id for item in layers if duty in item.responsibilities]
            if len(owners) > 1:
                raise HarnessLayeringError(
                    f"{duty} must have one owner; {owners} all claim it")
        object.__setattr__(self, "layers", layers)

    @property
    def is_direct_adapter(self) -> bool:
        return not self.layers

    @property
    def accounting_owner(self) -> str:
        """The wrapper that reports calls and effects, or the harness itself."""
        for item in self.layers:
            if "accounting" in item.responsibilities:
                return item.wrapper_id
        return self.harness_id

    def to_dict(self) -> dict:
        return {"record_type": COMPOSITION_RECORD_TYPE, "version": self.version,
                "composition_id": self.composition_id, "harness_id": self.harness_id,
                "layers": [item.to_dict() for item in self.layers]}

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, value) -> "WrapperComposition":
        _expect(value, COMPOSITION_RECORD_TYPE,
                {"version", "composition_id", "harness_id", "layers"})
        return cls(value["composition_id"], value["harness_id"],
                   tuple(WrapperLayer.from_dict(item) for item in value["layers"]),
                   value["version"])


@dataclass(frozen=True)
class CompositionFallback:
    """What one class of failure permits: another wrapper, another order, a
    native session restart, or another harness. A fallback preserves the
    assignment, its contracts, consumed authority, and committed effects; it
    only changes the implementation composition."""

    on: tuple[HarnessFailureKind, ...]
    action: str
    reason: str
    composition: "WrapperComposition | None" = None
    harness_id: str = ""

    def __post_init__(self):
        if type(self.on) not in (tuple, list) or not self.on or any(
                type(item) is not HarnessFailureKind for item in self.on):
            raise HarnessLayeringError("a fallback needs typed, nonempty failure kinds")
        kinds = tuple(self.on)
        if len(set(kinds)) != len(kinds):
            raise HarnessLayeringError("fallback failure kinds must not repeat")
        object.__setattr__(self, "on", kinds)
        if self.action not in FALLBACK_ACTIONS:
            raise HarnessLayeringError(f"fallback action must be one of {FALLBACK_ACTIONS}")
        _text(self.reason, "fallback reason")
        needs_composition = self.action in ("different_wrapper", "reordered_composition")
        if needs_composition and not isinstance(self.composition, WrapperComposition):
            raise HarnessLayeringError(f"{self.action} needs the alternative composition")
        if not needs_composition and self.composition is not None:
            raise HarnessLayeringError(f"{self.action} does not take a composition")
        if self.action == "different_harness":
            if not valid_harness_id(self.harness_id):
                raise HarnessLayeringError("different_harness needs the alternative harness id")
        elif self.harness_id:
            raise HarnessLayeringError(f"{self.action} does not take a harness id")

    def to_dict(self) -> dict:
        return {"record_type": FALLBACK_RECORD_TYPE, "on": [item.value for item in self.on],
                "action": self.action, "reason": self.reason,
                "composition": self.composition.to_dict() if self.composition else None,
                "harness_id": self.harness_id}

    @classmethod
    def from_dict(cls, value) -> "CompositionFallback":
        if type(value) is not dict or value.get("record_type") != FALLBACK_RECORD_TYPE:
            raise HarnessLayeringError(f"expected a {FALLBACK_RECORD_TYPE} record")
        if set(value) != {"record_type", "on", "action", "reason", "composition", "harness_id"}:
            raise HarnessLayeringError("fallback record has unexpected or missing fields")
        try:
            kinds = tuple(HarnessFailureKind(item) for item in value["on"])
        except (TypeError, ValueError) as exc:
            raise HarnessLayeringError("fallback failure kinds must be known codes") from exc
        composition = (WrapperComposition.from_dict(value["composition"])
                       if value["composition"] is not None else None)
        return cls(kinds, value["action"], value["reason"], composition, value["harness_id"])


class NativeControl(str, Enum):
    """The controls of a native harness whose ownership must be resolved."""

    GOAL = "goal_management"
    PLANNING = "planning_and_continuation"
    TOOLS = "tool_and_resource_use"
    RETRY = "retry_and_fallback"
    SESSION = "context_and_session_state"
    STEERING = "steering_and_queued_work"
    CANCELLATION = "pause_cancellation_and_shutdown"
    COMPLETION = "completion_and_output_publication"


class ControlOwnership(str, Enum):
    """Who owns one native control. Disabled, unsupported, and unknown stay
    distinguishable, as the proposal requires."""

    OWNING_LOOP = "owning_loop"
    DELEGATED = "delegated_within_authority"
    SUPERVISED = "supervised_native"
    DISABLED = "disabled"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


NATIVE_OWNERSHIPS = (ControlOwnership.DELEGATED, ControlOwnership.SUPERVISED)
REASON_REQUIRED = (ControlOwnership.UNSUPPORTED, ControlOwnership.UNKNOWN)


@dataclass(frozen=True)
class NativeControlPolicy:
    """Ownership of every native control, resolved one control at a time.

    The matrix must be complete: an absent control would be an unresolved
    ownership, which is the state the proposal forbids. Completion can never
    be delegated outright, because a native completion claim is never the
    owning task's verified result; it may be supervised, so the claim becomes
    a candidate the owning Loop checks. The record carries no authority: a
    delegated goal or planning control grants no tool, effect, or spending
    authority, which stay with the owning Loop's existing grants.
    """

    ownership: dict = field(default_factory=dict)
    reasons: dict = field(default_factory=dict)
    version: str = "1.0.0"

    def __post_init__(self):
        if self.version != "1.0.0":
            raise HarnessLayeringError("unsupported native control policy version")
        if type(self.ownership) is not dict or type(self.reasons) is not dict:
            raise HarnessLayeringError("control ownership and reasons must be mappings")
        resolved = {}
        for control, owner in self.ownership.items():
            if type(control) is not NativeControl or type(owner) is not ControlOwnership:
                raise HarnessLayeringError("ownership must map typed controls to typed owners")
            resolved[control] = owner
        missing = [item.value for item in NativeControl if item not in resolved]
        if missing:
            raise HarnessLayeringError(f"every native control needs an owner; missing {missing}")
        if resolved[NativeControl.COMPLETION] is ControlOwnership.DELEGATED:
            raise HarnessLayeringError(
                "completion cannot be delegated: a native completion claim is not the "
                "owning task's result; use supervised_native so the claim is checked")
        reasons = {}
        for control, reason in self.reasons.items():
            if type(control) is not NativeControl:
                raise HarnessLayeringError("reasons must be keyed by typed controls")
            reasons[control] = _text(reason, f"reason for {control.value}")
        for control, owner in resolved.items():
            if owner in REASON_REQUIRED and control not in reasons:
                raise HarnessLayeringError(
                    f"{control.value} marked {owner.value} needs a written reason")
        object.__setattr__(self, "ownership", resolved)
        object.__setattr__(self, "reasons", reasons)

    @classmethod
    def owning_loop_for_everything(cls) -> "NativeControlPolicy":
        """The policy every current recipe runs under."""
        return cls({item: ControlOwnership.OWNING_LOOP for item in NativeControl})

    def owner_of(self, control: NativeControl) -> ControlOwnership:
        return self.ownership[control]

    def natively_owned(self) -> tuple[NativeControl, ...]:
        return tuple(item for item in NativeControl
                     if self.ownership[item] in NATIVE_OWNERSHIPS)

    def to_dict(self) -> dict:
        return {"record_type": CONTROL_POLICY_RECORD_TYPE, "version": self.version,
                "ownership": {item.value: self.ownership[item].value for item in NativeControl},
                "reasons": {item.value: self.reasons[item] for item in NativeControl
                            if item in self.reasons}}

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, value) -> "NativeControlPolicy":
        _expect(value, CONTROL_POLICY_RECORD_TYPE, {"version", "ownership", "reasons"})
        try:
            ownership = {NativeControl(k): ControlOwnership(v) for k, v in value["ownership"].items()}
            reasons = {NativeControl(k): v for k, v in value["reasons"].items()}
        except (TypeError, ValueError, AttributeError) as exc:
            raise HarnessLayeringError("control policy names unknown controls or owners") from exc
        return cls(ownership, reasons, value["version"])


@dataclass(frozen=True)
class LayeredHarnessBinding:
    """One assignment's composition, its ordered fallbacks, and its control
    policy, checked against the outer fallback policy before execution.

    The checks are the proposal's coordination requirements: a fallback to
    another harness must be an alternative the outer policy already lists
    for a failure the outer policy already permits; a native retry owner
    needs the outer policy's explicit permission; and nothing here can grant
    authority. The binding is passive data with a digest, so an attempt
    record can cite exactly what it ran under.
    """

    assignment_ref: str
    initial: WrapperComposition
    control_policy: NativeControlPolicy
    fallbacks: tuple[CompositionFallback, ...] = ()
    fallback_policy: "HarnessFallbackPolicy | None" = None

    def __post_init__(self):
        _text(self.assignment_ref, "assignment_ref", limit=192)
        if not isinstance(self.initial, WrapperComposition):
            raise HarnessLayeringError("the initial composition must be typed")
        if not isinstance(self.control_policy, NativeControlPolicy):
            raise HarnessLayeringError("the control policy must be typed")
        if type(self.fallbacks) not in (tuple, list) or any(
                not isinstance(item, CompositionFallback) for item in self.fallbacks):
            raise HarnessLayeringError("fallbacks must be typed CompositionFallback records")
        if self.fallback_policy is not None and not isinstance(
                self.fallback_policy, HarnessFallbackPolicy):
            raise HarnessLayeringError("the outer fallback policy must be typed")
        fallbacks = tuple(self.fallbacks)
        seen_kinds: set[HarnessFailureKind] = set()
        for item in fallbacks:
            repeated = [kind.value for kind in item.on if kind in seen_kinds]
            if repeated:
                raise HarnessLayeringError(
                    f"exactly one fallback must decide each failure kind; {repeated} repeat")
            seen_kinds.update(item.on)
            if item.composition is not None:
                if item.composition.harness_id != self.initial.harness_id:
                    raise HarnessLayeringError(
                        "a wrapper or order fallback keeps the same harness; use "
                        "different_harness to change it")
                if item.composition.content_digest == self.initial.content_digest:
                    raise HarnessLayeringError("a fallback composition must differ from the initial one")
            if item.action == "different_harness":
                if item.harness_id == self.initial.harness_id:
                    raise HarnessLayeringError("different_harness must name another harness")
                if self.fallback_policy is None:
                    raise HarnessLayeringError(
                        "different_harness needs the outer fallback policy that lists the alternative")
                if item.harness_id not in self.fallback_policy.harness_ids:
                    raise HarnessLayeringError(
                        f"{item.harness_id!r} is not an alternative the outer fallback policy lists")
                outside = [kind.value for kind in item.on if kind not in self.fallback_policy.switch_on]
                if outside:
                    raise HarnessLayeringError(
                        f"the outer fallback policy does not permit switching on {outside}")
        if self.initial.harness_id != (self.fallback_policy.harness_ids[0]
                                       if self.fallback_policy else self.initial.harness_id):
            raise HarnessLayeringError(
                "the initial composition must wrap the outer policy's primary harness")
        retry_owner = self.control_policy.owner_of(NativeControl.RETRY)
        if retry_owner in NATIVE_OWNERSHIPS and not (
                self.fallback_policy is not None and self.fallback_policy.allow_native_retry):
            raise HarnessLayeringError(
                "a native harness may own retry only when the outer fallback policy sets "
                "allow_native_retry; otherwise a native transport retry could bypass the "
                "outer semantic-recovery restriction")
        object.__setattr__(self, "fallbacks", fallbacks)

    def to_dict(self) -> dict:
        return {"record_type": BINDING_RECORD_TYPE, "assignment_ref": self.assignment_ref,
                "initial": self.initial.to_dict(),
                "fallbacks": [item.to_dict() for item in self.fallbacks],
                "control_policy": self.control_policy.to_dict(),
                "outer_fallback_policy_digest": (
                    self.fallback_policy.content_digest if self.fallback_policy else "")}

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    def fallback_for(self, failure: HarnessFailureKind) -> "CompositionFallback | None":
        """The one fallback that decides this failure kind, if any."""
        for item in self.fallbacks:
            if failure in item.on:
                return item
        return None


def self_test() -> dict:
    """Prove the declarations, the order sensitivity, and the coordination rules."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:160]})

    def refused(name, thunk):
        try:
            thunk()
        except HarnessLayeringError as exc:
            check(name, True, str(exc)[:120])
        else:
            check(name, False, "accepted")

    preparation = WrapperLayer("instruction-prep", "1.2.0", ("instruction_preparation",),
                               inspects=("instructions",), transforms=("instructions",))
    bridge = WrapperLayer("session-bridge", "0.4", ("native_session_bridge", "accounting"),
                          inspects=("events",), depends_on=("instruction-prep",),
                          settings={"retain_session": False})
    direct = WrapperComposition("direct", "codex")
    layered = WrapperComposition("prepared-bridge", "codex", (preparation, bridge))
    swapped_bridge = WrapperLayer("session-bridge", "0.4", ("native_session_bridge", "accounting"),
                                  inspects=("events",), settings={"retain_session": False})
    reordered = WrapperComposition("bridge-prepared", "codex", (swapped_bridge, preparation))
    check("the_direct_adapter_is_a_valid_empty_composition",
          direct.is_direct_adapter and direct.accounting_owner == "codex"
          and direct.content_digest == WrapperComposition("direct", "codex").content_digest)
    check("layer_order_is_part_of_the_identity",
          layered.content_digest != reordered.content_digest
          and layered.accounting_owner == "session-bridge")
    refused("a_dependency_on_a_later_layer_is_refused",
            lambda: WrapperComposition("x", "codex", (bridge, preparation)))
    refused("two_accounting_owners_are_refused",
            lambda: WrapperComposition("x", "codex", (
                WrapperLayer("a", "1", ("accounting",)), WrapperLayer("b", "1", ("accounting",)))))
    refused("an_unknown_responsibility_is_refused",
            lambda: WrapperLayer("a", "1", ("goal_theft",)))
    refused("settings_must_be_plain_json",
            lambda: WrapperLayer("a", "1", ("transport",), settings={"f": object()}))
    check("a_composition_round_trips_through_its_record",
          WrapperComposition.from_dict(layered.to_dict()).content_digest == layered.content_digest)

    everything = NativeControlPolicy.owning_loop_for_everything()
    check("the_default_policy_is_the_owning_loop_for_every_control",
          everything.natively_owned() == () and len(everything.ownership) == len(NativeControl))
    refused("an_incomplete_control_matrix_is_refused",
            lambda: NativeControlPolicy({NativeControl.GOAL: ControlOwnership.OWNING_LOOP}))
    refused("delegated_completion_is_refused",
            lambda: NativeControlPolicy({**everything.ownership,
                                         NativeControl.COMPLETION: ControlOwnership.DELEGATED}))
    refused("unknown_ownership_needs_a_reason",
            lambda: NativeControlPolicy({**everything.ownership,
                                         NativeControl.STEERING: ControlOwnership.UNKNOWN}))
    explained = NativeControlPolicy(
        {**everything.ownership, NativeControl.STEERING: ControlOwnership.UNSUPPORTED,
         NativeControl.PLANNING: ControlOwnership.SUPERVISED},
        {NativeControl.STEERING: "codex exec has no steer command"})
    check("supervised_planning_with_an_explained_unsupported_control_is_accepted",
          explained.natively_owned() == (NativeControl.PLANNING,)
          and NativeControlPolicy.from_dict(explained.to_dict()).content_digest
          == explained.content_digest)
    check("the_policy_record_carries_no_authority_fields",
          set(explained.to_dict()) == {"record_type", "version", "ownership", "reasons"})

    outer = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,))
    binding = LayeredHarnessBinding(
        "assignment:orient-42", layered, everything,
        (CompositionFallback((HarnessFailureKind.EXECUTION_FAILED,), "reordered_composition",
                             "the bridge may load instructions first", reordered),
         CompositionFallback((HarnessFailureKind.UNAVAILABLE,), "different_harness",
                             "opencode is the registered alternative", harness_id="opencode")),
        outer)
    check("a_binding_names_one_fallback_per_failure_kind",
          binding.fallback_for(HarnessFailureKind.UNAVAILABLE).harness_id == "opencode"
          and binding.fallback_for(HarnessFailureKind.SEMANTIC_REJECTED) is None
          and binding.to_dict()["outer_fallback_policy_digest"] == outer.content_digest)
    refused("a_harness_the_outer_policy_does_not_list_is_refused",
            lambda: LayeredHarnessBinding("a", layered, everything, (
                CompositionFallback((HarnessFailureKind.UNAVAILABLE,), "different_harness",
                                    "x", harness_id="goose"),), outer))
    refused("a_failure_the_outer_policy_does_not_permit_is_refused",
            lambda: LayeredHarnessBinding("a", layered, everything, (
                CompositionFallback((HarnessFailureKind.SEMANTIC_REJECTED,), "different_harness",
                                    "x", harness_id="opencode"),), outer))
    refused("two_fallbacks_for_one_failure_kind_are_refused",
            lambda: LayeredHarnessBinding("a", layered, everything, (
                CompositionFallback((HarnessFailureKind.EXECUTION_FAILED,), "reordered_composition",
                                    "x", reordered),
                CompositionFallback((HarnessFailureKind.EXECUTION_FAILED,), "native_session_restart",
                                    "y")), outer))
    refused("a_fallback_identical_to_the_initial_composition_is_refused",
            lambda: LayeredHarnessBinding("a", layered, everything, (
                CompositionFallback((HarnessFailureKind.EXECUTION_FAILED,), "different_wrapper",
                                    "x", layered),), outer))
    native_retry = NativeControlPolicy({**everything.ownership,
                                        NativeControl.RETRY: ControlOwnership.DELEGATED})
    refused("native_retry_without_the_outer_permission_is_refused",
            lambda: LayeredHarnessBinding("a", layered, native_retry, (), outer))
    permitted = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,),
                                      allow_native_retry=True)
    granted = LayeredHarnessBinding("a", layered, native_retry, (), permitted)
    check("native_retry_with_the_explicit_outer_permission_is_accepted",
          granted.control_policy.owner_of(NativeControl.RETRY) is ControlOwnership.DELEGATED)
    check("the_permission_changes_the_outer_policy_record_and_digest",
          permitted.to_dict()["record_type"] == "harness_fallback_policy/v3"
          and outer.to_dict()["record_type"] == "harness_fallback_policy/v1"
          and "allow_native_retry" not in outer.to_dict()
          and permitted.content_digest != outer.content_digest)
    refused("a_binding_cannot_wrap_a_harness_other_than_the_outer_primary",
            lambda: LayeredHarnessBinding("a", WrapperComposition("d", "opencode"), everything,
                                          (), outer))
    check("a_binding_digest_is_stable_and_reproducible",
          binding.content_digest == LayeredHarnessBinding(
              "assignment:orient-42", layered, everything, binding.fallbacks, outer).content_digest)
    return {"module": "core.harness_layering", "tests": tests,
            "passed": sum(1 for item in tests if item["passed"]), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
