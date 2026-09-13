"""Enumerable, indexable spaces for the two layering dimensions.

A configuration search must be able to say how many wrapper compositions and
native control policies exist for one harness, address any one of them by an
integer index without materializing the rest, and walk them in a stable
order. This module gives the records in core.harness_layering that shape:

``ControlPolicySpace``
    Every complete NativeControlPolicy an adapter can honor. A control the
    adapter declares in ``native_controls`` may be owned by the Loop,
    delegated, supervised, or disabled; a control it does not declare may
    only be owned by the Loop or disabled. Completion is never delegated.
    Unsupported and unknown states need written reasons, so they are not
    enumerated; a caller declares them explicitly.

``CompositionSpace``
    Every ordered selection of distinct wrapper layers from a catalogue, up
    to a depth, that keeps each layer's dependencies earlier and gives
    transport and accounting at most one owner. The empty selection is the
    direct adapter, always index 0.

``LayeringSpace``
    The product of the two, decoded with mixed radix so index arithmetic is
    exact, producing LayeredHarnessBinding candidates for one assignment
    against one outer fallback policy.

Nothing here runs anything. The spaces are passive descriptions with a
digest, and every candidate they yield is the same validated record a
caller could have written by hand.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json

from .harness_execution_contracts import valid_harness_id
from .harness_fallback import HarnessFallbackPolicy
from .harness_layering import (
    ControlOwnership, HarnessLayeringError, LayeredHarnessBinding, NativeControl,
    NativeControlPolicy, SINGLE_OWNER_RESPONSIBILITIES, WrapperComposition, WrapperLayer,
)

#: Owners a declared control may take in an enumerated policy, in index order.
DECLARED_OWNERS = (ControlOwnership.OWNING_LOOP, ControlOwnership.DELEGATED,
                   ControlOwnership.SUPERVISED, ControlOwnership.DISABLED)
#: Owners an undeclared control may take: the adapter cannot hand it over.
UNDECLARED_OWNERS = (ControlOwnership.OWNING_LOOP, ControlOwnership.DISABLED)
#: Owners completion may take even when declared: a native claim is checked,
#: never accepted outright.
COMPLETION_OWNERS = (ControlOwnership.OWNING_LOOP, ControlOwnership.SUPERVISED,
                     ControlOwnership.DISABLED)

SPACE_RECORD_TYPE = "harness_layering_space/v1"


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _index(value, size, name):
    if type(value) is not int or isinstance(value, bool):
        raise HarnessLayeringError(f"{name} index must be an integer")
    if not 0 <= value < size:
        raise HarnessLayeringError(f"{name} index {value} is outside 0..{size - 1}")
    return value


@dataclass(frozen=True)
class ControlPolicySpace:
    """Every complete control policy one adapter can honor, indexable."""

    adapter_native_controls: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.adapter_native_controls) not in (tuple, list):
            raise HarnessLayeringError("adapter native controls must be a sequence")
        known = {item.value for item in NativeControl}
        declared = tuple(self.adapter_native_controls)
        if any(item not in known for item in declared) or len(set(declared)) != len(declared):
            raise HarnessLayeringError("adapter native controls must be distinct known controls")
        object.__setattr__(self, "adapter_native_controls", declared)

    def owners_for(self, control: NativeControl) -> tuple[ControlOwnership, ...]:
        if control is NativeControl.COMPLETION:
            return COMPLETION_OWNERS if control.value in self.adapter_native_controls \
                else UNDECLARED_OWNERS
        return DECLARED_OWNERS if control.value in self.adapter_native_controls \
            else UNDECLARED_OWNERS

    @property
    def radices(self) -> tuple[int, ...]:
        return tuple(len(self.owners_for(item)) for item in NativeControl)

    @property
    def size(self) -> int:
        total = 1
        for radix in self.radices:
            total *= radix
        return total

    def policy_at(self, index: int) -> NativeControlPolicy:
        """Decode one policy from its index with mixed radix; index 0 is the
        owning Loop for everything, the policy every current recipe runs."""
        remaining = _index(index, self.size, "control policy")
        ownership = {}
        for control in NativeControl:
            owners = self.owners_for(control)
            ownership[control] = owners[remaining % len(owners)]
            remaining //= len(owners)
        return NativeControlPolicy(ownership)

    def index_of(self, policy: NativeControlPolicy) -> int:
        """The index a policy decodes from, or a refusal when this space
        cannot produce it (an unsupported or unknown state, a delegated
        control the adapter did not declare)."""
        if not isinstance(policy, NativeControlPolicy):
            raise HarnessLayeringError("index_of needs a typed control policy")
        index = 0
        weight = 1
        for control in NativeControl:
            owners = self.owners_for(control)
            owner = policy.owner_of(control)
            if owner not in owners:
                raise HarnessLayeringError(
                    f"{control.value} owned by {owner.value} is outside this space")
            index += owners.index(owner) * weight
            weight *= len(owners)
        return index

    def __iter__(self):
        for index in range(self.size):
            yield self.policy_at(index)

    def to_dict(self) -> dict:
        return {"record_type": SPACE_RECORD_TYPE, "kind": "control_policy",
                "adapter_native_controls": list(self.adapter_native_controls),
                "radices": list(self.radices), "size": self.size}

    @classmethod
    def from_dict(cls, value) -> "ControlPolicySpace":
        _expect_space(value, "control_policy", {"adapter_native_controls", "radices", "size"})
        space = cls(tuple(value["adapter_native_controls"]))
        if list(space.radices) != list(value["radices"]) or space.size != value["size"]:
            raise HarnessLayeringError("the stored control policy space does not match its record")
        return space


@dataclass(frozen=True)
class CompositionSpace:
    """Every valid ordered selection of catalogue layers around one harness,
    up to the depth the caller states, indexable. Index 0 is the direct
    adapter. Sequences are enumerated lazily in a stable order, so a large
    catalogue costs time per lookup, never memory for the whole table, and
    no size ceiling is invented here: the caller's depth and catalogue are
    the only bounds."""

    harness_id: str
    catalogue: tuple[WrapperLayer, ...]
    max_depth: int

    def __post_init__(self):
        if not valid_harness_id(self.harness_id):
            raise HarnessLayeringError("a composition space must name its registered harness")
        if type(self.catalogue) not in (tuple, list) or any(
                not isinstance(item, WrapperLayer) for item in self.catalogue):
            raise HarnessLayeringError("the catalogue must hold typed WrapperLayer records")
        catalogue = tuple(self.catalogue)
        ids = [item.wrapper_id for item in catalogue]
        if len(set(ids)) != len(ids):
            raise HarnessLayeringError("catalogue wrapper identities must be unique")
        if type(self.max_depth) is not int or isinstance(self.max_depth, bool) \
                or self.max_depth < 0:
            raise HarnessLayeringError("the caller states a non-negative composition depth")
        object.__setattr__(self, "catalogue", catalogue)

    def _valid(self, sequence) -> bool:
        seen: set[str] = set()
        owners = {duty: 0 for duty in SINGLE_OWNER_RESPONSIBILITIES}
        for layer in sequence:
            if any(dep not in seen for dep in layer.depends_on):
                return False
            for duty in SINGLE_OWNER_RESPONSIBILITIES:
                if duty in layer.responsibilities:
                    owners[duty] += 1
                    if owners[duty] > 1:
                        return False
            seen.add(layer.wrapper_id)
        return True

    def sequences(self):
        """The valid sequences in index order, produced one at a time."""
        yield ()
        for depth in range(1, min(self.max_depth, len(self.catalogue)) + 1):
            for sequence in itertools.permutations(self.catalogue, depth):
                if self._valid(sequence):
                    yield sequence

    @property
    def size(self) -> int:
        return sum(1 for _ in self.sequences())

    def composition_at(self, index: int) -> WrapperComposition:
        if type(index) is not int or isinstance(index, bool) or index < 0:
            raise HarnessLayeringError("composition index must be a non-negative integer")
        for position, sequence in enumerate(self.sequences()):
            if position == index:
                name = "direct" if not sequence else ".".join(
                    item.wrapper_id for item in sequence)
                return WrapperComposition(name[:96], self.harness_id, sequence)
        raise HarnessLayeringError(f"composition index {index} is outside this space")

    def index_of(self, composition: WrapperComposition) -> int:
        if not isinstance(composition, WrapperComposition):
            raise HarnessLayeringError("index_of needs a typed composition")
        wanted = tuple(item.wrapper_id for item in composition.layers)
        for index, sequence in enumerate(self.sequences()):
            if tuple(item.wrapper_id for item in sequence) == wanted:
                return index
        raise HarnessLayeringError("that composition is outside this space")

    def __iter__(self):
        for index, sequence in enumerate(self.sequences()):
            yield WrapperComposition(
                ("direct" if not sequence else ".".join(
                    item.wrapper_id for item in sequence))[:96], self.harness_id, sequence)

    def to_dict(self) -> dict:
        return {"record_type": SPACE_RECORD_TYPE, "kind": "composition",
                "harness_id": self.harness_id, "max_depth": self.max_depth,
                "catalogue": [item.to_dict() for item in self.catalogue],
                "size": self.size}

    @classmethod
    def from_dict(cls, value) -> "CompositionSpace":
        _expect_space(value, "composition", {"harness_id", "max_depth", "catalogue", "size"})
        space = cls(value["harness_id"],
                    tuple(WrapperLayer.from_dict(item) for item in value["catalogue"]),
                    value["max_depth"])
        if space.size != value["size"]:
            raise HarnessLayeringError("the stored composition space does not match its record")
        return space


@dataclass(frozen=True)
class LayeringSpace:
    """The product of a composition space and a control policy space for one
    assignment, yielding validated LayeredHarnessBinding candidates."""

    assignment_ref: str
    compositions: CompositionSpace
    policies: ControlPolicySpace
    fallback_policy: "HarnessFallbackPolicy | None" = None

    def __post_init__(self):
        if not isinstance(self.compositions, CompositionSpace) or not isinstance(
                self.policies, ControlPolicySpace):
            raise HarnessLayeringError("a layering space needs both typed component spaces")
        if self.fallback_policy is not None and not isinstance(
                self.fallback_policy, HarnessFallbackPolicy):
            raise HarnessLayeringError("the outer fallback policy must be typed")

    @property
    def size(self) -> int:
        return self.compositions.size * self.policies.size

    def decode(self, index: int) -> tuple[int, int]:
        remaining = _index(index, self.size, "layering")
        return remaining % self.compositions.size, remaining // self.compositions.size

    def encode(self, composition_index: int, policy_index: int) -> int:
        _index(composition_index, self.compositions.size, "composition")
        _index(policy_index, self.policies.size, "control policy")
        return policy_index * self.compositions.size + composition_index

    def candidate_at(self, index: int) -> LayeredHarnessBinding:
        """The validated binding at one index. A candidate whose control
        policy natively owns retry needs the outer policy's permission; that
        is the binding's own rule, so such an index raises the same
        HarnessLayeringError a hand-written binding would."""
        composition_index, policy_index = self.decode(index)
        return LayeredHarnessBinding(
            self.assignment_ref, self.compositions.composition_at(composition_index),
            self.policies.policy_at(policy_index), (), self.fallback_policy)

    def admissible(self, index: int) -> bool:
        """Whether the index decodes to a binding the outer policy admits."""
        try:
            self.candidate_at(index)
        except HarnessLayeringError:
            return False
        return True

    def to_dict(self) -> dict:
        return {"record_type": SPACE_RECORD_TYPE, "kind": "layering",
                "assignment_ref": self.assignment_ref,
                "compositions": self.compositions.to_dict(),
                "policies": self.policies.to_dict(), "size": self.size,
                "outer_fallback_policy_digest": (
                    self.fallback_policy.content_digest if self.fallback_policy else "")}

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, value, *, fallback_policy=None) -> "LayeringSpace":
        """Rebuild a space from its record. The outer fallback policy is not
        stored in the record, only its digest, so the caller supplies it and
        the digest is checked; a record with a digest and no policy is
        refused rather than rebuilt without its rule."""
        _expect_space(value, "layering", {"assignment_ref", "compositions", "policies",
                                          "size", "outer_fallback_policy_digest"})
        stored = value["outer_fallback_policy_digest"]
        if stored and (fallback_policy is None or fallback_policy.content_digest != stored):
            raise HarnessLayeringError(
                "the layering space record names an outer fallback policy digest; supply "
                "the same policy to rebuild it")
        if not stored and fallback_policy is not None:
            raise HarnessLayeringError("the record has no outer policy; do not add one on rebuild")
        space = cls(value["assignment_ref"], CompositionSpace.from_dict(value["compositions"]),
                    ControlPolicySpace.from_dict(value["policies"]), fallback_policy)
        if space.size != value["size"]:
            raise HarnessLayeringError("the stored layering space does not match its record")
        return space


def _expect_space(value, kind, keys):
    if (type(value) is not dict or value.get("record_type") != SPACE_RECORD_TYPE
            or value.get("kind") != kind):
        raise HarnessLayeringError(f"expected a {SPACE_RECORD_TYPE} record of kind {kind}")
    if set(value) != keys | {"record_type", "kind"}:
        raise HarnessLayeringError(f"{kind} space record has unexpected or missing fields")


def self_test() -> dict:
    """Sizes, index round trips, constraint honoring, and determinism."""
    from .harness_fallback import HarnessFailureKind
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:160]})

    undeclared = ControlPolicySpace()
    check("an_adapter_declaring_nothing_has_two_owners_per_control",
          undeclared.radices == (2,) * len(NativeControl) and undeclared.size == 2 ** 8)
    check("index_zero_is_the_owning_loop_for_everything",
          undeclared.policy_at(0).content_digest
          == NativeControlPolicy.owning_loop_for_everything().content_digest)
    declared = ControlPolicySpace(("goal_management", "planning_and_continuation",
                                   "completion_and_output_publication"))
    check("declared_controls_widen_the_space_and_completion_is_never_delegated",
          declared.size == 4 * 4 * 3 * 2 ** 5
          and all(policy.owner_of(NativeControl.COMPLETION) is not ControlOwnership.DELEGATED
                  for policy in declared))
    round_trip = all(declared.index_of(declared.policy_at(index)) == index
                     for index in range(declared.size))
    check("every_control_policy_index_round_trips", round_trip)
    digests = {policy.content_digest for policy in declared}
    check("every_enumerated_control_policy_is_distinct", len(digests) == declared.size)
    try:
        declared.index_of(NativeControlPolicy(
            {**NativeControlPolicy.owning_loop_for_everything().ownership,
             NativeControl.STEERING: ControlOwnership.UNKNOWN},
            {NativeControl.STEERING: "not enumerated"}))
        check("a_policy_outside_the_space_is_refused_by_index_of", False, "accepted")
    except HarnessLayeringError:
        check("a_policy_outside_the_space_is_refused_by_index_of", True)

    prep = WrapperLayer("prep", "1", ("instruction_preparation",))
    bridge = WrapperLayer("bridge", "1", ("native_session_bridge", "accounting"),
                          depends_on=("prep",))
    meter = WrapperLayer("meter", "1", ("accounting",))
    transport = WrapperLayer("transport", "1", ("transport",))
    space = CompositionSpace("codex", (prep, bridge, meter, transport), 3)
    sequences = [tuple(item.wrapper_id for item in comp.layers) for comp in space]
    check("the_direct_adapter_is_index_zero",
          sequences[0] == () and space.composition_at(0).is_direct_adapter)
    check("a_dependency_must_sit_earlier_in_every_enumerated_composition",
          all(("prep" in seq[:seq.index("bridge")]) for seq in sequences if "bridge" in seq)
          and ("bridge",) not in sequences and ("prep", "bridge") in sequences)
    check("two_accounting_owners_never_appear_together",
          all(not ({"bridge", "meter"} <= set(seq)) for seq in sequences))
    check("order_is_enumerated_as_distinct_compositions",
          ("prep", "transport") in sequences and ("transport", "prep") in sequences)
    check("every_composition_index_round_trips",
          all(space.index_of(space.composition_at(index)) == index
              for index in range(space.size)))
    check("the_size_is_the_count_of_valid_sequences_only",
          space.size == len(sequences) == len(set(sequences)) and space.size < 1 + 4 + 12 + 24)
    try:
        CompositionSpace("codex", (prep,), -1)
        check("a_negative_depth_is_refused_and_the_depth_is_the_callers", False, "accepted")
    except HarnessLayeringError:
        check("a_negative_depth_is_refused_and_the_depth_is_the_callers", True)
    wide = CompositionSpace("codex", tuple(WrapperLayer(f"w{i}", "1", ("instruction_preparation",))
                                           for i in range(9)), 2)
    check("a_wide_catalogue_is_walked_lazily_without_a_table",
          wide.size == 1 + 9 + 72 and wide.composition_at(81).layers[0].wrapper_id == "w8"
          and "_sequences" not in vars(wide))

    outer = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,))
    layering = LayeringSpace("assignment:space-check", space, declared, outer)
    check("the_product_size_and_index_arithmetic_agree",
          layering.size == space.size * declared.size
          and all(layering.encode(*layering.decode(index)) == index
                  for index in range(0, layering.size, 97)))
    candidate = layering.candidate_at(0)
    check("index_zero_of_the_product_is_the_direct_adapter_owned_by_the_loop",
          candidate.initial.is_direct_adapter
          and candidate.control_policy.natively_owned() == ()
          and candidate.fallback_policy is outer)
    retry_delegated = next(index for index in range(declared.size)
                           if declared.policy_at(index).owner_of(NativeControl.RETRY)
                           is ControlOwnership.DELEGATED) if any(
        p.owner_of(NativeControl.RETRY) is ControlOwnership.DELEGATED for p in declared) else None
    check("retry_is_not_enumerable_for_an_adapter_that_does_not_declare_it",
          retry_delegated is None)
    retry_space = ControlPolicySpace(("retry_and_fallback",))
    permitted = HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,),
                                      allow_native_retry=True)
    without = LayeringSpace("assignment:space-check", space, retry_space, outer)
    with_permission = LayeringSpace("assignment:space-check", space, retry_space, permitted)
    delegated_index = with_permission.encode(0, retry_space.index_of(NativeControlPolicy(
        {**NativeControlPolicy.owning_loop_for_everything().ownership,
         NativeControl.RETRY: ControlOwnership.DELEGATED})))
    check("a_native_retry_candidate_is_inadmissible_without_the_outer_permission",
          not without.admissible(delegated_index) and with_permission.admissible(delegated_index))
    rebuilt = LayeringSpace.from_dict(layering.to_dict(), fallback_policy=outer)
    check("a_layering_space_round_trips_through_its_record_with_its_outer_policy",
          rebuilt.content_digest == layering.content_digest
          and rebuilt.candidate_at(0).content_digest == layering.candidate_at(0).content_digest)
    try:
        LayeringSpace.from_dict(layering.to_dict())
        check("a_record_naming_an_outer_policy_cannot_be_rebuilt_without_it", False, "accepted")
    except HarnessLayeringError:
        check("a_record_naming_an_outer_policy_cannot_be_rebuilt_without_it", True)
    tampered = dict(layering.to_dict()); tampered["size"] = tampered["size"] + 1
    try:
        LayeringSpace.from_dict(tampered, fallback_policy=outer)
        check("a_record_whose_size_disagrees_with_its_definition_is_refused", False, "accepted")
    except HarnessLayeringError:
        check("a_record_whose_size_disagrees_with_its_definition_is_refused", True)
    check("the_space_digest_is_stable_and_reproducible",
          layering.content_digest == LayeringSpace(
              "assignment:space-check", CompositionSpace("codex", (prep, bridge, meter, transport), 3),
              ControlPolicySpace(("goal_management", "planning_and_continuation",
                                  "completion_and_output_publication")), outer).content_digest)
    return {"module": "core.harness_layering_space", "tests": tests,
            "passed": sum(1 for item in tests if item["passed"]), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}
