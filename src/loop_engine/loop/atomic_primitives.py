"""Logical deterministic Loops for finite intrinsic semantic primitives.

Every registered primitive runs as the canonical ``Loop`` runtime and returns
a typed ``LoopValue``. The intrinsic kernel may use native Python operations,
but callers cannot invoke it directly outside this module and its tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from .intrinsic_kernel import (
    INTRINSIC_PRIMITIVES, execute_intrinsic, intrinsic_content_digest)
from .loop_contract import contract_for_code_loop
from .loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from .recursive_loop import LoopConfig, StepOutcome


T = TypeVar("T")


class AtomicPrimitiveError(ValueError):
    """A primitive definition, request, or result violated its contract."""


@dataclass(frozen=True)
class LoopValue(Generic[T]):
    """Typed value with producer, contract, lineage, and verification state."""

    value: T = field(repr=False, compare=False)
    value_contract_ref: str
    semantic_role: str
    producer_loop_id: str
    producer_definition_ref: str
    source_refs: tuple[str, ...]
    content_digest: str
    transformation_lineage: tuple[str, ...]
    privacy_class: str = "run_private"
    materialization_state: str = "materialized"
    verification_state: str = "verified_by_contract"
    record_type: str = "loop_value/v1"

    def __post_init__(self) -> None:
        if (self.record_type != "loop_value/v1"
                or any(not item.strip() for item in (
                    self.value_contract_ref, self.semantic_role,
                    self.producer_loop_id, self.producer_definition_ref,
                    self.privacy_class, self.materialization_state,
                    self.verification_state))
                or len(self.content_digest) != 64):
            raise AtomicPrimitiveError("LoopValue identity is invalid")

    @classmethod
    def create(cls, value: T, request: "LoopValueCreateRequest") -> "LoopValue[T]":
        return cls(
            value, request.value_contract_ref, request.semantic_role,
            request.producer_loop_id, request.producer_definition_ref,
            tuple(request.source_refs), intrinsic_content_digest(value),
            tuple(request.transformation_lineage), request.privacy_class)

    def to_ref(self) -> "LoopValueRef":
        return LoopValueRef(
            self.content_digest, self.value_contract_ref, self.semantic_role,
            self.producer_loop_id, self.producer_definition_ref)

    def to_dict(self, include_value: bool = False) -> dict:
        value = {
            "record_type": self.record_type,
            "value_contract_ref": self.value_contract_ref,
            "semantic_role": self.semantic_role,
            "producer_loop_id": self.producer_loop_id,
            "producer_definition_ref": self.producer_definition_ref,
            "source_refs": list(self.source_refs),
            "content_digest": self.content_digest,
            "transformation_lineage": list(self.transformation_lineage),
            "privacy_class": self.privacy_class,
            "materialization_state": self.materialization_state,
            "verification_state": self.verification_state,
        }
        if include_value:
            value["value"] = self.value
        return value


@dataclass(frozen=True)
class LoopValueCreateRequest:
    """Cohesive producer metadata used inside an owning primitive Loop."""

    value_contract_ref: str
    semantic_role: str
    producer_loop_id: str
    producer_definition_ref: str
    source_refs: tuple[str, ...] = ()
    transformation_lineage: tuple[str, ...] = ()
    privacy_class: str = "run_private"


@dataclass(frozen=True)
class LoopValueRef:
    """Body-free exact reference to one produced semantic value."""

    content_digest: str
    value_contract_ref: str
    semantic_role: str
    producer_loop_id: str
    producer_definition_ref: str

    def __post_init__(self) -> None:
        if (len(self.content_digest) != 64
                or any(character not in "0123456789abcdef"
                       for character in self.content_digest)
                or any(not item.strip() for item in (
                    self.value_contract_ref, self.semantic_role,
                    self.producer_loop_id, self.producer_definition_ref))):
            raise AtomicPrimitiveError("LoopValueRef is invalid")

    def to_dict(self) -> dict:
        return {
            "content_digest": self.content_digest,
            "value_contract_ref": self.value_contract_ref,
            "semantic_role": self.semantic_role,
            "producer_loop_id": self.producer_loop_id,
            "producer_definition_ref": self.producer_definition_ref,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "LoopValueRef":
        """Rebuild one exact body-free value reference."""
        expected = {
            "content_digest", "value_contract_ref", "semantic_role",
            "producer_loop_id", "producer_definition_ref",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise AtomicPrimitiveError("LoopValueRef has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class AtomicPrimitiveDefinition:
    """Immutable data description of one registered atomic operation."""

    primitive_id: str
    input_contract_refs: tuple[str, ...]
    output_contract_ref: str
    intrinsic_id: str
    purity: str = "pure"
    idempotent: bool = True
    cacheable: bool = True
    fusion_allowed: bool = True
    default_mode: str = "deterministic"

    def __post_init__(self) -> None:
        if (self.primitive_id != self.intrinsic_id
                or self.intrinsic_id not in INTRINSIC_PRIMITIVES
                or self.default_mode != "deterministic"
                or self.purity != "pure"
                or not self.output_contract_ref.strip()):
            raise AtomicPrimitiveError("atomic primitive definition is invalid")


ATOMIC_PRIMITIVES = {
    item.primitive_id: item for item in (
        AtomicPrimitiveDefinition(
            "core.primitive.text.constant", (), "text/v1",
            "core.primitive.text.constant"),
        AtomicPrimitiveDefinition(
            "core.primitive.text.combine", ("text/v1",), "text/v1",
            "core.primitive.text.combine"),
        AtomicPrimitiveDefinition(
            "core.primitive.text.normalize", ("text/v1",), "text/v1",
            "core.primitive.text.normalize"),
        AtomicPrimitiveDefinition(
            "core.primitive.text.utf8_size", ("text/v1",), "integer/v1",
            "core.primitive.text.utf8_size"),
        AtomicPrimitiveDefinition(
            "core.primitive.number.ceil_divide", ("integer/v1",),
            "integer/v1", "core.primitive.number.ceil_divide"),
        AtomicPrimitiveDefinition(
            "core.primitive.component.read", (), "value/v1",
            "core.primitive.component.read"),
        AtomicPrimitiveDefinition(
            "core.primitive.json.serialize", ("value/v1",), "json_text/v1",
            "core.primitive.json.serialize"),
        AtomicPrimitiveDefinition(
            "core.primitive.json.deserialize", ("json_text/v1",), "value/v1",
            "core.primitive.json.deserialize"),
        AtomicPrimitiveDefinition(
            "core.primitive.record.project", ("record/v1",), "value/v1",
            "core.primitive.record.project"),
        AtomicPrimitiveDefinition(
            "core.primitive.record.merge", ("record/v1",), "record/v1",
            "core.primitive.record.merge"),
        AtomicPrimitiveDefinition(
            "core.primitive.sequence.order", ("value/v1",), "sequence/v1",
            "core.primitive.sequence.order"),
    )}


@dataclass(frozen=True)
class AtomicPrimitiveRequest:
    """Typed input, parameters, and output semantics for one primitive Loop."""

    primitive_id: str
    inputs: tuple[LoopValue, ...]
    parameters: tuple[tuple[str, object], ...]
    output_contract_ref: str
    output_semantic_role: str
    privacy_class: str = "run_private"

    def __post_init__(self) -> None:
        definition = ATOMIC_PRIMITIVES.get(self.primitive_id)
        if definition is None:
            raise AtomicPrimitiveError("atomic primitive is not registered")
        if self.output_contract_ref != definition.output_contract_ref:
            raise AtomicPrimitiveError("atomic output contract does not match")
        if any(not isinstance(item, LoopValue) for item in self.inputs):
            raise AtomicPrimitiveError("atomic inputs must be LoopValue records")
        keys = tuple(key for key, _value in self.parameters)
        if len(keys) != len(set(keys)):
            raise AtomicPrimitiveError("atomic parameters cannot repeat")


def run_atomic_primitive(
        request: AtomicPrimitiveRequest, parent_loop) -> LoopValue:
    """Execute one registered primitive as a deterministic Spawned Loop."""
    if not isinstance(request, AtomicPrimitiveRequest):
        raise AtomicPrimitiveError("run_atomic_primitive needs typed request")
    if not getattr(parent_loop, "loop_id", ""):
        raise AtomicPrimitiveError("atomic primitive needs an active parent Loop")
    definition = ATOMIC_PRIMITIVES[request.primitive_id]
    contract = contract_for_code_loop(
        "atomic_primitive", input_roles=("atomic_primitive_request/v1",),
        output_roles=(request.output_contract_ref,), effects=("pure",),
        role="practitioner")
    config = LoopConfig(
        framework="custom", custom_steps=("act",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), power="light",
        exit_condition="accepted_success")
    loop = parent_loop.spawn(
        "execute registered atomic primitive", config, contract=contract,
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.code_execution"),
        relationship=LoopRelationship.spawned_by(parent_loop.loop_id))
    holder = {}

    def handler(active, _step, _state):
        try:
            raw = execute_intrinsic(
                request.primitive_id,
                tuple(item.value for item in request.inputs),
                request.parameters)
            holder["value"] = LoopValue.create(raw, LoopValueCreateRequest(
                request.output_contract_ref, request.output_semantic_role,
                active.loop_id, definition.primitive_id,
                source_refs=tuple(
                    item.content_digest for item in request.inputs),
                transformation_lineage=(definition.primitive_id,),
                privacy_class=request.privacy_class))
            active.ledger.record(
                loop_id=active.loop_id, event="custom",
                custom_kind="atomic_primitive_executed",
                primitive_id=definition.primitive_id,
                input_digests=tuple(
                    item.content_digest for item in request.inputs),
                output_digest=holder["value"].content_digest,
                fused=False, cache_hit=False)
            return StepOutcome("atomic:completed", "deterministic", 1.0)
        except Exception as exc:  # noqa: BLE001
            holder["error"] = exc
            return StepOutcome(
                "atomic:failed", "deterministic", 0.0, failed=True)

    result = loop.run(handler=handler, max_steps=1)
    if "error" in holder:
        raise AtomicPrimitiveError(
            "atomic primitive failed inside its Loop") from holder["error"]
    if not result.accepted:
        raise AtomicPrimitiveError("atomic primitive did not reach acceptance")
    return holder["value"]


def self_test() -> dict:
    """Prove defaults and provenance without starting another process."""
    from .recursive_loop import Loop

    parent = Loop("atomic primitive test owner")
    first = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.constant", (), (("value", "a"),),
        "text/v1", "first"), parent)
    second = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.constant", (), (("value", "b"),),
        "text/v1", "second"), parent)
    combined = run_atomic_primitive(AtomicPrimitiveRequest(
        "core.primitive.text.combine", (first, second),
        (("separator", "|"),), "text/v1", "combined"), parent)
    tests = [{
        "test": "atomic_text_combine_runs_as_deterministic_loop",
        "passed": combined.value == "a|b"
        and combined.transformation_lineage
        == ("core.primitive.text.combine",),
        "detail": combined.producer_loop_id,
    }, {
        "test": "loop_value_preserves_input_provenance",
        "passed": combined.source_refs
        == (first.content_digest, second.content_digest),
        "detail": combined.content_digest,
    }, {
        "test": "every_atomic_primitive_defaults_to_deterministic",
        "passed": all(item.default_mode == "deterministic"
                      for item in ATOMIC_PRIMITIVES.values()),
        "detail": "registered primitive defaults verified",
    }]
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "atomic_primitive_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
