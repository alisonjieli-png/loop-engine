"""The versioned engine protocol of the step executor slot, and the envelope clock.

Owns: the adapter contract version ``external_harness_adapter/v2``, the closed
engine kinds of the ``step_executor`` slot, the edges the harness registry
serves with the adapter operation each edge calls, the refusals applied when an
adapter is registered and again when the envelope uses it, the registration
digest, and the rule that the envelope's own clock sets an attempt's time.
Belongs to: the external harness boundary (``core.external_harness``), which
imports this module. This module does not import that boundary when it loads,
so no cycle forms.
Does not own: engine selection, eligibility for one step, which kinds count as
delegation (the planned envelope of the step edge is to compute that from the
observed process), the step edge records, or any permission. A declaration is
a fact about an adapter, never a grant and never an independent qualification.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import fields
from types import MappingProxyType

from .harness_execution_contracts import plain_harness_json, valid_harness_id
from .harness_model_authority import HarnessError

#: The engine protocol an adapter implements: ``info()``, plus ``run()`` for
#: the model response edge and ``run_step()`` for the step edge. The first
#: protocol was undeclared and duck typed; an adapter written for it declares
#: no version and is refused, because the project has not launched and keeps
#: no reader for unpublished shapes.
ADAPTER_CONTRACT_VERSION = "external_harness_adapter/v2"
SUPPORTED_ADAPTER_CONTRACT_VERSIONS = (ADAPTER_CONTRACT_VERSION,)

#: The engine slot whose engines this registry holds.
STEP_EXECUTOR_SLOT = "step_executor"

#: The closed engine kinds of the step executor slot (engine design, section
#: 13.5). The design also says which of them may count as delegation, and the
#: planned slot catalogue is to list the same kinds; this tuple only bounds what
#: an adapter may declare.
STEP_EXECUTOR_ENGINE_KINDS = (
    "agent_protocol_harness", "native_protocol_harness", "text_relay_harness",
    "custom_loop_harness", "remote_agent", "agent_framework_kit", "direct_model_step",
    "in_process_runner", "typed_decision_step", "structural")

#: The edges the registry serves, named by their request record type, newest
#: first. Each names its result record type and the adapter operation that
#: serves it. An adapter may declare more edges; only these are used.
MODEL_RESPONSE_EDGE = "harness_request_identity/v3"
STEP_EDGE = "step_run_request/v1"
SERVED_EDGE_CONTRACTS = MappingProxyType({
    STEP_EDGE: ("step_run_result/v1", "run_step"),
    MODEL_RESPONSE_EDGE: ("external_harness_result/v3", "run"),
})

_VERSIONED_NAME = re.compile(r"^[a-z][a-z0-9_]{0,95}/v[1-9][0-9]{0,5}$")


class HarnessAdapterRefused(HarnessError):
    """An adapter refused before any run, with every reason as a stable code."""

    def __init__(self, harness_id: str, refusals: tuple[str, ...]):
        self.harness_id, self.refusals = harness_id, tuple(refusals)
        super().__init__(f"adapter {harness_id!r} refused: " + ", ".join(self.refusals))


def validate_declared_contract(info) -> None:
    """Check the shape of the three declared fields and freeze the edge list.

    An empty value means "not declared" and registration refuses it. A
    malformed value is refused here, when the declaration is made.
    """
    version, kind = info.adapter_contract_version, info.engine_kind
    edges = info.supported_edge_contracts
    if type(version) is not str or (version and not _VERSIONED_NAME.fullmatch(version)):
        raise HarnessError("adapter_contract_version must be a versioned name, for example "
                           + ADAPTER_CONTRACT_VERSION)
    if type(kind) is not str or (kind and not valid_harness_id(kind)):
        raise HarnessError("engine_kind must be a bounded identifier")
    if type(edges) not in (tuple, list) or any(
            type(edge) is not str or not _VERSIONED_NAME.fullmatch(edge) for edge in edges):
        raise HarnessError("supported_edge_contracts must be a sequence of versioned names")
    if len(set(edges)) != len(edges):
        raise HarnessError("supported_edge_contracts cannot name one edge twice")
    object.__setattr__(info, "supported_edge_contracts", tuple(edges))


def contract_version_refusal(info) -> str:
    """The refusal code for a missing or unknown contract version, or empty."""
    version = info.adapter_contract_version
    if not version:
        return "adapter_contract_version_missing"
    if version not in SUPPORTED_ADAPTER_CONTRACT_VERSIONS:
        return "adapter_contract_version_unsupported"
    return ""


def engine_kind_refusal(info) -> str:
    """The refusal code for a missing kind or one the slot does not list, or empty."""
    if not info.engine_kind:
        return "engine_kind_missing"
    return "" if info.engine_kind in STEP_EXECUTOR_ENGINE_KINDS else "engine_kind_not_in_slot"


def served_edge_contracts(info) -> tuple[str, ...]:
    """The declared edges this registry serves: the negotiated set, newest first."""
    return tuple(edge for edge in SERVED_EDGE_CONTRACTS
                 if edge in info.supported_edge_contracts)


def edge_refusals(adapter, info) -> tuple[str, ...]:
    """Refuse an adapter serving no known edge, or lacking an edge's operation."""
    served = served_edge_contracts(info)
    if not served:
        return ("no_supported_edge_contract",)
    operations = (SERVED_EDGE_CONTRACTS[edge][1] for edge in served)
    return tuple("edge_operation_missing:" + name for name in operations
                 if not callable(getattr(adapter, name, None)))


def adapter_contract_refusals(adapter, info) -> tuple[str, ...]:
    """Every reason the adapter is outside the contract, in a fixed order."""
    return tuple(code for code in (contract_version_refusal(info), engine_kind_refusal(info),
                                   *edge_refusals(adapter, info)) if code)


def require_adapter_contract(adapter, info, *, edge: str = "") -> None:
    """Refuse, before any effect, an adapter outside the contract or the named edge."""
    refusals = adapter_contract_refusals(adapter, info)
    if edge and edge not in info.supported_edge_contracts:
        refusals += ("edge_not_declared:" + edge,)
    if refusals:
        raise HarnessAdapterRefused(info.harness_id, refusals)


def registration_digest(adapter, info) -> str:
    """Digest one registration: the adapter's whole declaration and its code.

    Two registrations share a digest only when the declaration and the
    implementation class are both the same. The registry therefore refuses a
    replacement that changes neither: a decision bound to the old digest could
    not tell the two engines apart.
    """
    declaration = {item.name: getattr(info, item.name) for item in fields(info)}
    capabilities = info.execution_capabilities
    declaration["execution_capabilities"] = (
        capabilities.to_dict() if capabilities is not None else None)
    record = {"record_type": "harness_adapter_registration/v1", "slot_id": STEP_EXECUTOR_SLOT,
              "implementation_ref": type(adapter).__module__ + "." + type(adapter).__qualname__,
              "declaration": declaration}
    return hashlib.sha256(json.dumps(
        plain_harness_json(record), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def measured_and_reported_seconds(started: float, engine_reported: "float | None"
                                  ) -> "tuple[float, float | None]":
    """Return the attempt time the envelope measured, and the engine's own figure.

    The envelope's monotonic clock is authoritative, so an engine cannot make
    itself look fast or slow. Its own figure is returned unchanged, kept apart
    as ``engine_reported_seconds`` and never ranked.
    """
    return round(time.monotonic() - started, 6), engine_reported


def self_test() -> dict:
    """Run the named contract, identity and clock checks offline."""
    from .external_harness_contract_checks import run_checks
    return run_checks()
