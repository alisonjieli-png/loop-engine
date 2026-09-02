"""Thin canonical Loop envelope for bounded operational service calls.

This helper does not introduce another runtime. It initializes and runs the
existing ``Loop`` once with a typed contract, explicit Practitioner profile,
shared parent and ledger, and a terminal event even when the wrapped operation
raises. Approval and workspace services keep their state and backend logic in
private core methods and use this one envelope at their public boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from .loop_contract import contract_for_code_loop
from .loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from .recursive_loop import Loop, LoopConfig, StepOutcome


_T = TypeVar("_T")
_SERVICE_PROFILES = frozenset({
    "practitioner.code_execution", "practitioner.verifier"})


@dataclass(frozen=True)
class ServiceLoopSpec:
    """Identity and typed ports for one deterministic service operation."""

    operation: str
    profile_id: str
    input_role: str
    output_role: str
    effects: tuple[str, ...]
    objective: str
    failure_kind: str

    def __post_init__(self) -> None:
        for name in ("operation", "input_role", "output_role", "objective",
                     "failure_kind"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"service Loop {name} cannot be empty")
        if self.profile_id not in _SERVICE_PROFILES:
            raise ValueError(
                "service Loop needs a verifier or code-execution profile")


def run_service_operation(runtime, spec: ServiceLoopSpec,
                          action: Callable[[Loop], _T]) -> _T:
    """Run one callable once inside the canonical Loop and return its value."""
    contract = contract_for_code_loop(
        spec.operation, input_roles=(spec.input_role,),
        output_roles=(spec.output_role,), effects=spec.effects,
        role=spec.profile_id)
    config = LoopConfig(
        framework="custom", custom_steps=(spec.operation,),
        logical_kind="execution", replay_guarantee="event_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), power="light",
        exit_condition="accepted_success")
    parent = runtime.parent
    identity = LoopRoleIdentity(LoopRole.PRACTITIONER, spec.profile_id)
    relationship = (LoopRelationship.spawned_by(parent.loop_id)
                    if parent is not None else LoopRelationship.starting())
    loop = (parent.spawn(
        spec.objective, config, contract=contract,
        identity=identity, relationship=relationship)
        if parent is not None else Loop(
            spec.objective, config, ledger=runtime.ledger, contract=contract,
            identity=identity, relationship=relationship))
    holder: dict[str, object] = {}

    def handler(active: Loop, _step: str, _context: dict) -> StepOutcome:
        try:
            holder["value"] = action(active)
        except Exception as exc:
            holder["error"] = exc
            active.ledger.record(
                loop_id=active.loop_id, event="failure.detected",
                failure_kind=spec.failure_kind, operation=spec.operation,
                error_type=type(exc).__name__)
        return StepOutcome(
            output=(f"{spec.operation}:failed" if "error" in holder
                    else f"{spec.operation}:completed"),
            mode="deterministic", confidence=1.0)

    result = loop.run(handler=handler, max_steps=1)
    if not result.stopped:
        raise RuntimeError(
            f"service operation Loop {spec.operation!r} did not terminate")
    if "error" in holder:
        raise holder["error"]  # type: ignore[misc]
    return holder["value"]  # type: ignore[return-value]
