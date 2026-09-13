"""Passive model identities, capacity and budget records for harness adapters.

The public external_harness module re-exports these records. This module does
not import the execution boundary, so direct imports cannot form a cycle.
"""
from __future__ import annotations

from dataclasses import dataclass

from .harness_execution_contracts import valid_number, validate_harness_strings
from .model_capabilities import ModelOutputAllocation


class HarnessError(RuntimeError):
    """An external harness request or adapter violated its contract."""


@dataclass(frozen=True)
class ModelOutputLimit:
    """Exact provider or endpoint maximum with its source reference."""

    max_output_tokens: int
    source: str
    reference: str
    provider_id: str = ""
    model_id: str = ""
    route_id: str = ""

    def __post_init__(self) -> None:
        if not valid_number(self.max_output_tokens, integer=True, positive=True):
            raise HarnessError("resolved model output maximum must be positive")
        if self.source not in (
                "provider_declared", "provider_catalog",
                "endpoint_observed", "custom_endpoint_declared"):
            raise HarnessError("unknown model output maximum source")
        if not self.reference.strip():
            raise HarnessError("model output maximum needs a source reference")
        if not self.provider_id.strip() or not self.model_id.strip():
            raise HarnessError("model output maximum needs exact provider_id and model_id")


@dataclass(frozen=True)
class HarnessBudget:
    """Post-run acceptance bounds; preemptive controls must be required separately."""

    max_model_calls: int | None
    max_total_tokens: int | None = None
    max_cost: float | None = None
    max_seconds: float | None = None
    max_spawned_tasks: int | None = None
    output_limit: ModelOutputLimit | None = None
    output_allocation: ModelOutputAllocation | None = None

    def __post_init__(self) -> None:
        if (self.max_model_calls is not None
                and not valid_number(self.max_model_calls, integer=True, positive=True)):
            raise HarnessError("max_model_calls must be positive when set")
        for field_name in ("max_total_tokens", "max_cost", "max_seconds"):
            value = getattr(self, field_name)
            if value is not None and not valid_number(
                    value, integer=field_name == "max_total_tokens", positive=True):
                raise HarnessError(f"{field_name} must be positive when set")
        if (self.max_spawned_tasks is not None
                and not valid_number(self.max_spawned_tasks, integer=True)):
            raise HarnessError("max_spawned_tasks cannot be negative")
        if (self.output_limit is not None
                and not isinstance(self.output_limit, ModelOutputLimit)):
            raise HarnessError("output_limit must be ModelOutputLimit")
        if self.output_allocation is not None:
            if not isinstance(self.output_allocation, ModelOutputAllocation):
                raise HarnessError("output_allocation must be ModelOutputAllocation")
            if self.output_limit is not None:
                _validate_allocation_capacity(self.output_allocation, self.output_limit)

    @property
    def max_output_tokens(self) -> int | None:
        return self.output_limit.max_output_tokens if self.output_limit is not None else None

    @property
    def requested_output_tokens(self) -> int | None:
        """Selected allowance; absence retains the full resolved capacity."""
        return (self.output_allocation.requested_tokens
                if self.output_allocation is not None else self.max_output_tokens)


@dataclass(frozen=True)
class HarnessModelIdentity:
    """One exact provider/model/route already authorized by the host gateway."""

    provider_id: str
    model_id: str
    route_id: str

    def __post_init__(self) -> None:
        validate_harness_strings(self, ("provider_id", "model_id", "route_id"))
        if any(len(value) > 512 or any(character.isspace() for character in value)
               for value in (self.provider_id, self.model_id, self.route_id)):
            raise HarnessError("model identities must be bounded exact identifiers")


def _validate_allocation_capacity(
        allocation: ModelOutputAllocation, limit: ModelOutputLimit) -> None:
    if ((allocation.provider_id, allocation.model_id)
            != (limit.provider_id, limit.model_id)
            or allocation.maximum_output_tokens != limit.max_output_tokens
            or (limit.route_id and allocation.route_name != limit.route_id)):
        raise HarnessError("output allocation differs from the resolved model capacity or route")
