"""Seven-layer component envelope adapters and multi-engine fallback chains for eight operational slots.

This module implements swappable seven-layer envelope adapters and multi-engine
fallback chains for eight operational, transport, and export engine slots that
previously carried ``none`` coverage across layers in
``src/loop_engine/data/component_envelope_coverage_baseline.yaml``:

1. ``run_history_export`` (``trace_span_exporter``, ``trajectory_exporter``)
2. ``usage_export`` (``no_export``, ``provider_meter_events``)
3. ``failure_journal`` (``in_service_journal``, ``ring_buffer_failure_journal``)
4. ``runtime_memory`` (``run_note_board``, ``bounded_scratchpad_board``)
5. ``paired_agent_transport`` (``signed_https_polling_transport``, ``websocket_lease_transport``)
6. ``telemetry_sink`` (``jsonl_structured_sink``, ``otlp_batch_sink``)
7. ``billing_settlement`` (``stripe_webhook_reconciler``, ``prepaid_credit_ledger``)
8. ``mcp_bridge`` (``stdio_jsonrpc_bridge``, ``http_sse_mcp_bridge``)

Every slot request traverses all seven envelope layers in declared order using
the canonical records from ``loop_engine.core.engines.envelope``,
``envelope_preflight``, and ``envelope_tracking``:

- ``frustration_avoidance``: whitespace and header normalization, idempotency
  key deduplication for rapid retries, bounded automatic recovery via
  ``RecoveryAllowance``, and structured ``EnvelopeRefusal`` recovery hints.
- ``carrier``: versioned ``SlotCarrierEnvelope`` with ``contract_version``,
  ``schema_digest``, and ``payload_sha256`` verification.
- ``handshake``: ``negotiate_handshake`` protocol version and capability match,
  lease HMAC signature and monotonic sequence check on
  ``paired_agent_transport``, Stripe webhook signature and timestamp window
  verification on ``billing_settlement``, and Model Context Protocol version
  (``2025-06-18`` / ``2024-11-05``) plus customer versus staff tool-visibility
  filtering on ``mcp_bridge``.
- ``account``: tenant and account scope binding, active account check, quota
  enforcement, and cross-tenant isolation check.
- ``tracking``: structured ``EngineSelectionReceipt``, latency and outcome
  counters, ``ref_...`` correlation identifier, and hash-chained
  ``EnvelopeJournalEntry`` records.
- ``preflight``: ``run_preflight`` secret and personal-data scrubbing before
  export (``run_history_export``, ``telemetry_sink``, ``failure_journal``),
  payload byte ceiling enforcement (``runtime_memory``), and idempotency ledger
  verification before billing or meter mutation (``billing_settlement``,
  ``usage_export``).
- ``nested_envelopes``: composable parent-to-nested trace and authority
  attenuation across nested slot invocations using ``EnvelopeFrame`` and
  ``enter_nested``.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

import types

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
try:
    import jsonschema as _jsonschema  # noqa: F401
except ModuleNotFoundError:
    _stub = types.ModuleType("jsonschema")
    _stub.__path__ = []  # type: ignore[attr-defined]
    _stub.Draft202012Validator = object  # type: ignore[attr-defined]
    _exc_stub = types.ModuleType("jsonschema.exceptions")
    _exc_stub.SchemaError = Exception  # type: ignore[attr-defined]
    _stub.exceptions = _exc_stub  # type: ignore[attr-defined]
    sys.modules["jsonschema"] = _stub
    sys.modules["jsonschema.exceptions"] = _exc_stub

from loop_engine.core.configuration_capabilities import digest  # noqa: E402
from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    INBOUND_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_FRUSTRATION_AVOIDANCE,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    MAXIMUM_AUTOMATIC_ATTEMPTS,
    MAXIMUM_ENVELOPE_DEPTH,
    NESTED_ENVELOPES,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    RETRY_AFTER_WAIT,
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeError,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeHandshakeVerdict,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REFUSED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    EFFECT_STATE_CONFIRMED,
    EFFECT_STATE_NONE,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
     TASK_FAILED,
    journal_chain,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

SLOT_RUN_HISTORY_EXPORT = "run_history_export"
SLOT_USAGE_EXPORT = "usage_export"
SLOT_FAILURE_JOURNAL = "failure_journal"
SLOT_RUNTIME_MEMORY = "runtime_memory"
SLOT_PAIRED_AGENT_TRANSPORT = "paired_agent_transport"
SLOT_TELEMETRY_SINK = "telemetry_sink"
SLOT_BILLING_SETTLEMENT = "billing_settlement"
SLOT_MCP_BRIDGE = "mcp_bridge"

HARDENED_SLOTS: tuple[str, ...] = (
    SLOT_RUN_HISTORY_EXPORT,
    SLOT_USAGE_EXPORT,
    SLOT_FAILURE_JOURNAL,
    SLOT_RUNTIME_MEMORY,
    SLOT_PAIRED_AGENT_TRANSPORT,
    SLOT_TELEMETRY_SINK,
    SLOT_BILLING_SETTLEMENT,
    SLOT_MCP_BRIDGE,
)

CARRIER_RECORD_TYPE = "slot_carrier_envelope/v1"
SELECTION_RECEIPT_RECORD_TYPE = "engine_selection_receipt/v1"
BENCHMARK_REPORT_RECORD_TYPE = "slot_handshake_hardening_benchmark/v1"

OUTCOME_COMPLETED = "completed"
OUTCOME_FALLBACK_COMPLETED = "fallback_completed"
OUTCOME_DEDUPLICATED = "deduplicated"
OUTCOME_REFUSED = "refused"

ACCOUNT_ACTIVE = "active"
PRINCIPAL_CUSTOMER = "customer"
PRINCIPAL_STAFF = "staff"

MCP_VERSION_2025 = "2025-06-18"
MCP_VERSION_2024 = "2024-11-05"
SUPPORTED_MCP_VERSIONS: tuple[str, ...] = (MCP_VERSION_2025, MCP_VERSION_2024)

CUSTOMER_VISIBLE_TOOLS: frozenset[str] = frozenset({
    "baltor_search",
    "baltor_fetch",
    "baltor_manifest",
    "baltor_discover",
    "baltor_verify",
})
STAFF_ONLY_TOOLS: frozenset[str] = frozenset({
    "staff_systems_inspect",
    "staff_audit_export",
    "staff_everything_reconcile",
    "staff_ledger_override",
})

DEFAULT_WEBHOOK_TOLERANCE_SECONDS = 300
DEFAULT_RUNTIME_MEMORY_BYTE_CEILING = 4096
DEFAULT_TRANSPORT_FRAME_BYTE_CEILING = 65536
FIXED_AUDIT_INSTANT = "2026-10-16T18:00:00Z"

_SECRET_PATTERN = re.compile(
    r"(?i)(?:sk-[a-z0-9_-]{12,}|whsec_[a-z0-9_-]{12,}|rk_live_[a-z0-9_-]{12,}|"
    r"ghp_[a-z0-9_-]{12,}|bearer\s+[a-z0-9._-]{12,}|"
    r"-----BEGIN [A-Z ]+PRIVATE KEY-----)"
)
_PII_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PII_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def compute_payload_sha256(payload: Mapping[str, Any]) -> str:
    """Compute the canonical SHA-256 hex digest of a normalized payload mapping."""
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def compute_schema_digest(slot_id: str, contract_version: str, allowed_fields: tuple[str, ...]) -> str:
    """Compute the deterministic schema digest for a slot's carrier contract."""
    return digest({
        "slot_id": slot_id,
        "contract_version": contract_version,
        "allowed_fields": list(sorted(allowed_fields)),
    })


def normalize_value(value: Any) -> Any:
    """Normalize whitespace in strings, lists, and nested mappings for frustration avoidance."""
    if isinstance(value, str):
        return re.sub(r"[ \t]+", " ", value.strip())
    if isinstance(value, Mapping):
        return {
            (k.strip() if isinstance(k, str) else k): normalize_value(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_value(item) for item in value)
    return value


def normalize_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    """Normalize header names to lowercase trimmed strings and strip header values."""
    if not headers:
        return {}
    normalized: dict[str, str] = {}
    for key, val in headers.items():
        clean_key = str(key).strip().lower()
        clean_val = re.sub(r"[ \t]+", " ", str(val).strip())
        if clean_key:
            normalized[clean_key] = clean_val
    return normalized


def _contains_secret_or_pii(value: Any) -> bool:
    if isinstance(value, str):
        return bool(
            _SECRET_PATTERN.search(value)
            or _PII_EMAIL_PATTERN.search(value)
            or _PII_SSN_PATTERN.search(value)
        )
    if isinstance(value, Mapping):
        return any(_contains_secret_or_pii(k) or _contains_secret_or_pii(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_secret_or_pii(item) for item in value)
    return False


def _scrub_secret_and_pii(value: Any) -> Any:
    if isinstance(value, str):
        scrubbed = _SECRET_PATTERN.sub("[REDACTED_SECRET]", value)
        scrubbed = _PII_EMAIL_PATTERN.sub("[REDACTED_PII]", scrubbed)
        scrubbed = _PII_SSN_PATTERN.sub("[REDACTED_PII]", scrubbed)
        return scrubbed
    if isinstance(value, Mapping):
        return {k: _scrub_secret_and_pii(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_secret_and_pii(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_secret_and_pii(item) for item in value)
    return value


def sign_paired_transport_frame(
    signing_material: str,
    lease_id: str,
    agent_id: str,
    sequence: int,
    payload_sha256: str,
) -> str:
    """Compute the HMAC-SHA256 signature for a paired agent transport frame."""
    message = f"{lease_id}:{agent_id}:{sequence}:{payload_sha256}".encode("utf-8")
    return hmac.new(signing_material.encode("utf-8"), message, hashlib.sha256).hexdigest()


def sign_stripe_webhook(
    signing_material: str,
    timestamp: int,
    payload: Mapping[str, Any],
) -> str:
    """Build a Stripe-compatible ``t=...,v1=...`` webhook signature header."""
    canonical = _canonical_json_bytes(normalize_value(payload)).decode("utf-8")
    signed_payload = f"{timestamp}.{canonical}".encode("utf-8")
    digest_hex = hmac.new(signing_material.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest_hex}"


@dataclass(frozen=True)
class SlotCarrierEnvelope:
    """Layer 2 (``carrier``): versioned envelope binding schema digest and payload SHA-256."""

    slot_id: str
    contract_version: str
    schema_digest: str
    payload_sha256: str
    payload: Mapping[str, Any]
    record_type: str = CARRIER_RECORD_TYPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "slot_id": self.slot_id,
            "contract_version": self.contract_version,
            "schema_digest": self.schema_digest,
            "payload_sha256": self.payload_sha256,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True)
class AccountScopeContext:
    """Layer 4 (``account``): tenant/account binding, quota state, and principal role."""

    tenant_id: str
    account_id: str
    principal_role: str = PRINCIPAL_CUSTOMER
    account_status: str = ACCOUNT_ACTIVE
    quota_limit: int = 1000
    consumed_units: int = 0
    requested_units: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "principal_role": self.principal_role,
            "account_status": self.account_status,
            "quota_limit": self.quota_limit,
            "consumed_units": self.consumed_units,
            "requested_units": self.requested_units,
        }


@dataclass(frozen=True)
class EngineSelectionReceipt:
    """Layer 5 (``tracking``): structured selection record with correlation ID and latency."""

    slot_id: str
    selected_engine_id: str
    engine_kind: str
    candidate_engines: tuple[str, ...]
    fallback_occurred: bool
    fallback_reason: str
    attempt_count: int
    latency_ms: float
    outcome: str
    correlation_id: str
    parent_correlation_id: str
    request_identity_digest: str
    journal_entry_digests: tuple[str, ...]
    record_type: str = SELECTION_RECEIPT_RECORD_TYPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "slot_id": self.slot_id,
            "selected_engine_id": self.selected_engine_id,
            "engine_kind": self.engine_kind,
            "candidate_engines": list(self.candidate_engines),
            "fallback_occurred": self.fallback_occurred,
            "fallback_reason": self.fallback_reason,
            "attempt_count": self.attempt_count,
            "latency_ms": round(self.latency_ms, 4),
            "outcome": self.outcome,
            "correlation_id": self.correlation_id,
            "parent_correlation_id": self.parent_correlation_id,
            "request_identity_digest": self.request_identity_digest,
            "journal_entry_digests": list(self.journal_entry_digests),
        }


@dataclass
class SlotTrackingMetrics:
    """Per-slot latency and outcome counters updated by the tracking layer."""

    slot_id: str
    total_requests: int = 0
    completed_count: int = 0
    fallback_completed_count: int = 0
    deduplicated_count: int = 0
    refused_count: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    def record(self, outcome: str, latency_ms: float) -> None:
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        if latency_ms > self.max_latency_ms:
            self.max_latency_ms = latency_ms
        if outcome == OUTCOME_COMPLETED:
            self.completed_count += 1
        elif outcome == OUTCOME_FALLBACK_COMPLETED:
            self.fallback_completed_count += 1
        elif outcome == OUTCOME_DEDUPLICATED:
            self.deduplicated_count += 1
        else:
            self.refused_count += 1

    def to_dict(self) -> dict[str, Any]:
        mean_ms = self.total_latency_ms / self.total_requests if self.total_requests else 0.0
        return {
            "slot_id": self.slot_id,
            "total_requests": self.total_requests,
            "completed_count": self.completed_count,
            "fallback_completed_count": self.fallback_completed_count,
            "deduplicated_count": self.deduplicated_count,
            "refused_count": self.refused_count,
            "mean_latency_ms": round(mean_ms, 4),
            "max_latency_ms": round(self.max_latency_ms, 4),
        }


@dataclass(frozen=True)
class SlotEngineSpec:
    """Swappable engine implementation registered behind one of the 8 slots."""

    slot_id: str
    engine_id: str
    engine_kind: str
    supported_versions: tuple[str, ...]
    capabilities: tuple[str, ...]
    effects: tuple[str, ...]
    execute_fn: Callable[[Mapping[str, Any], Mapping[str, str]], dict[str, Any]] = field(compare=False)

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=self.supported_versions,
            capabilities=self.capabilities,
            effects=self.effects,
        )


class TransientEngineUnavailableError(RuntimeError):
    """Raised by an engine when a transient failure wrote nothing and allows fallback."""

    def __init__(self, code: str = "upstream_transient_unavailable", detail: str = "Transient upstream error."):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SlotEnvelopeRequest:
    """Inbound request to a 7-layer hardened engine slot."""

    slot_id: str
    idempotency_key: str
    contract_version: str
    requested_versions: tuple[str, ...]
    payload: Mapping[str, Any]
    account: AccountScopeContext
    headers: Mapping[str, str] = field(default_factory=dict)
    required_capabilities: tuple[str, ...] = ()
    advisory_capabilities: tuple[str, ...] = ()
    granted_effects: tuple[str, ...] = (PURE_EFFECT,)
    schema_digest: str = ""
    payload_sha256: str = ""
    allow_preflight_repair: bool = False
    now_epoch: float = 1792173600.0
    parent_frame: EnvelopeFrame | None = None
    parent_granted_effects: tuple[str, ...] | None = None
    parent_tenant_id: str = ""
    parent_correlation_id: str = ""
    nested_invocations: tuple["SlotEnvelopeRequest", ...] = ()


@dataclass(frozen=True)
class SlotEnvelopeOutcome:
    """Complete 7-layer execution result for one hardened slot invocation."""

    slot_id: str
    accepted: bool
    deduplicated: bool
    output: dict[str, Any] | None
    refusal: EnvelopeRefusal | None
    carrier: SlotCarrierEnvelope | None
    handshake_verdicts: tuple[EnvelopeHandshakeVerdict, ...]
    account_checked: bool
    receipt: EngineSelectionReceipt
    preflight_report: EnvelopePreflightReport | None
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    nested_outcomes: tuple["SlotEnvelopeOutcome", ...] = ()
    normalized_headers: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "accepted": self.accepted,
            "deduplicated": self.deduplicated,
            "output": self.output,
            "refusal": None if self.refusal is None else self.refusal.to_dict(),
            "carrier": None if self.carrier is None else self.carrier.to_dict(),
            "handshake_verdicts": [v.to_dict() for v in self.handshake_verdicts],
            "account_checked": self.account_checked,
            "receipt": self.receipt.to_dict(),
            "preflight_report": None if self.preflight_report is None else self.preflight_report.to_dict(),
            "trace": self.trace.to_dict(),
            "frame": self.frame.to_dict(),
            "nested_outcomes": [child.to_dict() for child in self.nested_outcomes],
            "normalized_headers": dict(self.normalized_headers),
        }


@dataclass(frozen=True)
class SlotContractSpec:
    """Slot-level schema, protocol version, and recovery configuration."""

    slot_id: str
    contract_version: str
    allowed_fields: tuple[str, ...]
    required_fields: tuple[str, ...]
    recoverable_codes: tuple[str, ...] = ("upstream_transient_unavailable", "primary_engine_timeout")

    @property
    def schema_digest(self) -> str:
        return compute_schema_digest(self.slot_id, self.contract_version, self.allowed_fields)


SLOT_CONTRACTS: Mapping[str, SlotContractSpec] = MappingProxyType({
    SLOT_RUN_HISTORY_EXPORT: SlotContractSpec(
        slot_id=SLOT_RUN_HISTORY_EXPORT,
        contract_version="run_history_exporter/v1",
        allowed_fields=("tenant_id", "run_id", "attempt_id", "duration_ms", "spans", "destination"),
        required_fields=("tenant_id", "run_id", "duration_ms", "spans"),
    ),
    SLOT_USAGE_EXPORT: SlotContractSpec(
        slot_id=SLOT_USAGE_EXPORT,
        contract_version="usage_exporter/v1",
        allowed_fields=("tenant_id", "meter_event_id", "metric_name", "quantity", "recorded_at"),
        required_fields=("tenant_id", "meter_event_id", "metric_name", "quantity"),
    ),
    SLOT_FAILURE_JOURNAL: SlotContractSpec(
        slot_id=SLOT_FAILURE_JOURNAL,
        contract_version="service_observability_policy/v1",
        allowed_fields=("tenant_id", "failure_ref", "route", "status_code", "summary", "alive", "ready"),
        required_fields=("tenant_id", "failure_ref", "route", "summary"),
    ),
    SLOT_RUNTIME_MEMORY: SlotContractSpec(
        slot_id=SLOT_RUNTIME_MEMORY,
        contract_version="runtime_memory_service/v1",
        allowed_fields=("tenant_id", "run_id", "loop_id", "note_key", "note_body", "max_bytes"),
        required_fields=("tenant_id", "run_id", "loop_id", "note_key", "note_body"),
    ),
    SLOT_PAIRED_AGENT_TRANSPORT: SlotContractSpec(
        slot_id=SLOT_PAIRED_AGENT_TRANSPORT,
        contract_version="paired_agent_transport/v1",
        allowed_fields=("tenant_id", "lease_id", "agent_id", "sequence", "lease_expires_at", "command_frame"),
        required_fields=("tenant_id", "lease_id", "agent_id", "sequence", "lease_expires_at", "command_frame"),
    ),
    SLOT_TELEMETRY_SINK: SlotContractSpec(
        slot_id=SLOT_TELEMETRY_SINK,
        contract_version="telemetry_sink/v1",
        allowed_fields=("tenant_id", "stream_name", "events", "batch_size"),
        required_fields=("tenant_id", "stream_name", "events"),
    ),
    SLOT_BILLING_SETTLEMENT: SlotContractSpec(
        slot_id=SLOT_BILLING_SETTLEMENT,
        contract_version="billing_settlement/v1",
        allowed_fields=("tenant_id", "event_id", "event_type", "amount_cents", "currency", "plan_tier"),
        required_fields=("tenant_id", "event_id", "event_type", "amount_cents", "currency"),
    ),
    SLOT_MCP_BRIDGE: SlotContractSpec(
        slot_id=SLOT_MCP_BRIDGE,
        contract_version="mcp_bridge/v1",
        allowed_fields=("tenant_id", "mcp_protocol_version", "jsonrpc_method", "tool_name", "arguments"),
        required_fields=("tenant_id", "mcp_protocol_version", "jsonrpc_method", "tool_name"),
    ),
})


def _correlation_id(slot_id: str, idempotency_key: str, payload_sha256: str) -> str:
    raw = hashlib.sha256(f"{slot_id}:{idempotency_key}:{payload_sha256}".encode("utf-8")).hexdigest()
    return f"ref_{raw[:16]}"


# Concrete primary and fallback engine implementations for all 8 slots.

def _exec_trace_span_exporter(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    spans = payload.get("spans", ())
    return {
        "exporter": "trace_span_exporter",
        "exported_span_count": len(spans),
        "duration_ms": payload["duration_ms"],
        "destination": payload.get("destination", "otel_collector"),
    }


def _exec_trajectory_exporter(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    spans = payload.get("spans", ())
    return {
        "exporter": "trajectory_exporter",
        "trajectory_steps": len(spans),
        "duration_ms": payload["duration_ms"],
        "destination": payload.get("destination", "jsonl_trajectory"),
    }


def _exec_no_export(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "exporter": "no_export",
        "meter_event_id": payload["meter_event_id"],
        "exported": False,
        "quantity": payload["quantity"],
    }


def _exec_provider_meter_events(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "exporter": "provider_meter_events",
        "meter_event_id": payload["meter_event_id"],
        "exported": True,
        "quantity": payload["quantity"],
    }


def _exec_in_service_journal(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "journal_engine": "in_service_journal",
        "failure_ref": payload["failure_ref"],
        "alive": bool(payload.get("alive", True)),
        "ready": bool(payload.get("ready", True)),
        "stored": True,
    }


def _exec_ring_buffer_failure_journal(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "journal_engine": "ring_buffer_failure_journal",
        "failure_ref": payload["failure_ref"],
        "alive": bool(payload.get("alive", True)),
        "ready": bool(payload.get("ready", True)),
        "stored": True,
    }


def _exec_run_note_board(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    body_bytes = len(str(payload["note_body"]).encode("utf-8"))
    return {
        "memory_engine": "run_note_board",
        "run_id": payload["run_id"],
        "note_key": payload["note_key"],
        "stored_bytes": body_bytes,
    }


def _exec_bounded_scratchpad_board(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    body_bytes = len(str(payload["note_body"]).encode("utf-8"))
    return {
        "memory_engine": "bounded_scratchpad_board",
        "run_id": payload["run_id"],
        "note_key": payload["note_key"],
        "stored_bytes": body_bytes,
    }


def _exec_signed_https_polling_transport(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "transport_engine": "signed_https_polling_transport",
        "lease_id": payload["lease_id"],
        "agent_id": payload["agent_id"],
        "accepted_sequence": payload["sequence"],
        "delivery_mode": "https_long_poll",
    }


def _exec_websocket_lease_transport(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "transport_engine": "websocket_lease_transport",
        "lease_id": payload["lease_id"],
        "agent_id": payload["agent_id"],
        "accepted_sequence": payload["sequence"],
        "delivery_mode": "websocket_frame",
    }


def _exec_jsonl_structured_sink(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    events = payload.get("events", ())
    return {
        "sink_engine": "jsonl_structured_sink",
        "stream_name": payload["stream_name"],
        "written_events": len(events),
    }


def _exec_otlp_batch_sink(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    events = payload.get("events", ())
    return {
        "sink_engine": "otlp_batch_sink",
        "stream_name": payload["stream_name"],
        "written_events": len(events),
    }


def _exec_stripe_webhook_reconciler(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "settlement_engine": "stripe_webhook_reconciler",
        "event_id": payload["event_id"],
        "settled_amount_cents": payload["amount_cents"],
        "plan_tier": payload.get("plan_tier", "pro"),
    }


def _exec_prepaid_credit_ledger(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "settlement_engine": "prepaid_credit_ledger",
        "event_id": payload["event_id"],
        "settled_amount_cents": payload["amount_cents"],
        "plan_tier": payload.get("plan_tier", "prepaid"),
    }


def _exec_stdio_jsonrpc_bridge(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "bridge_engine": "stdio_jsonrpc_bridge",
        "mcp_protocol_version": payload["mcp_protocol_version"],
        "tool_name": payload["tool_name"],
        "visible_tools": sorted(CUSTOMER_VISIBLE_TOOLS),
    }


def _exec_http_sse_mcp_bridge(payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
    return {
        "bridge_engine": "http_sse_mcp_bridge",
        "mcp_protocol_version": payload["mcp_protocol_version"],
        "tool_name": payload["tool_name"],
        "visible_tools": sorted(CUSTOMER_VISIBLE_TOOLS),
    }


def build_default_slot_engines() -> dict[str, tuple[SlotEngineSpec, ...]]:
    """Build the default primary and fallback engine chains for all 8 hardened slots."""
    return {
        SLOT_RUN_HISTORY_EXPORT: (
            SlotEngineSpec(
                slot_id=SLOT_RUN_HISTORY_EXPORT,
                engine_id="trace_span_exporter",
                engine_kind="trace_span_exporter",
                supported_versions=("run_history_exporter/v1",),
                capabilities=("otel_spans", "duration_bounds", "secret_scrub"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_trace_span_exporter,
            ),
            SlotEngineSpec(
                slot_id=SLOT_RUN_HISTORY_EXPORT,
                engine_id="trajectory_exporter",
                engine_kind="trajectory_exporter",
                supported_versions=("run_history_exporter/v1",),
                capabilities=("otel_spans", "duration_bounds", "secret_scrub", "trajectory_jsonl"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_trajectory_exporter,
            ),
        ),
        SLOT_USAGE_EXPORT: (
            SlotEngineSpec(
                slot_id=SLOT_USAGE_EXPORT,
                engine_id="provider_meter_events",
                engine_kind="provider_meter_events",
                supported_versions=("usage_exporter/v1",),
                capabilities=("idempotent_meter", "overage_export"),
                effects=("external_effect",),
                execute_fn=_exec_provider_meter_events,
            ),
            SlotEngineSpec(
                slot_id=SLOT_USAGE_EXPORT,
                engine_id="no_export",
                engine_kind="no_export",
                supported_versions=("usage_exporter/v1",),
                capabilities=("idempotent_meter", "overage_export"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_no_export,
            ),
        ),
        SLOT_FAILURE_JOURNAL: (
            SlotEngineSpec(
                slot_id=SLOT_FAILURE_JOURNAL,
                engine_id="in_service_journal",
                engine_kind="in_service_journal",
                supported_versions=("service_observability_policy/v1",),
                capabilities=("ref_lookup", "alive_ready_split"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_in_service_journal,
            ),
            SlotEngineSpec(
                slot_id=SLOT_FAILURE_JOURNAL,
                engine_id="ring_buffer_failure_journal",
                engine_kind="in_service_journal",
                supported_versions=("service_observability_policy/v1",),
                capabilities=("ref_lookup", "alive_ready_split"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_ring_buffer_failure_journal,
            ),
        ),
        SLOT_RUNTIME_MEMORY: (
            SlotEngineSpec(
                slot_id=SLOT_RUNTIME_MEMORY,
                engine_id="run_note_board",
                engine_kind="run_note_board",
                supported_versions=("runtime_memory_service/v1",),
                capabilities=("sibling_notes", "byte_ceiling"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_run_note_board,
            ),
            SlotEngineSpec(
                slot_id=SLOT_RUNTIME_MEMORY,
                engine_id="bounded_scratchpad_board",
                engine_kind="run_note_board",
                supported_versions=("runtime_memory_service/v1",),
                capabilities=("sibling_notes", "byte_ceiling"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_bounded_scratchpad_board,
            ),
        ),
        SLOT_PAIRED_AGENT_TRANSPORT: (
            SlotEngineSpec(
                slot_id=SLOT_PAIRED_AGENT_TRANSPORT,
                engine_id="signed_https_polling_transport",
                engine_kind="signed_https_polling_transport",
                supported_versions=("paired_agent_transport/v1",),
                capabilities=("lease_hmac", "monotonic_sequence"),
                effects=("network",),
                execute_fn=_exec_signed_https_polling_transport,
            ),
            SlotEngineSpec(
                slot_id=SLOT_PAIRED_AGENT_TRANSPORT,
                engine_id="websocket_lease_transport",
                engine_kind="websocket_lease_transport",
                supported_versions=("paired_agent_transport/v1",),
                capabilities=("lease_hmac", "monotonic_sequence", "bidirectional_stream"),
                effects=("network",),
                execute_fn=_exec_websocket_lease_transport,
            ),
        ),
        SLOT_TELEMETRY_SINK: (
            SlotEngineSpec(
                slot_id=SLOT_TELEMETRY_SINK,
                engine_id="jsonl_structured_sink",
                engine_kind="jsonl_structured_sink",
                supported_versions=("telemetry_sink/v1",),
                capabilities=("structured_events", "pii_scrub"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_jsonl_structured_sink,
            ),
            SlotEngineSpec(
                slot_id=SLOT_TELEMETRY_SINK,
                engine_id="otlp_batch_sink",
                engine_kind="otlp_batch_sink",
                supported_versions=("telemetry_sink/v1",),
                capabilities=("structured_events", "pii_scrub", "otlp_batch"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_otlp_batch_sink,
            ),
        ),
        SLOT_BILLING_SETTLEMENT: (
            SlotEngineSpec(
                slot_id=SLOT_BILLING_SETTLEMENT,
                engine_id="stripe_webhook_reconciler",
                engine_kind="stripe_webhook_reconciler",
                supported_versions=("billing_settlement/v1",),
                capabilities=("webhook_hmac", "idempotent_ledger"),
                effects=("external_effect",),
                execute_fn=_exec_stripe_webhook_reconciler,
            ),
            SlotEngineSpec(
                slot_id=SLOT_BILLING_SETTLEMENT,
                engine_id="prepaid_credit_ledger",
                engine_kind="prepaid_credit_ledger",
                supported_versions=("billing_settlement/v1",),
                capabilities=("webhook_hmac", "idempotent_ledger"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_prepaid_credit_ledger,
            ),
        ),
        SLOT_MCP_BRIDGE: (
            SlotEngineSpec(
                slot_id=SLOT_MCP_BRIDGE,
                engine_id="stdio_jsonrpc_bridge",
                engine_kind="stdio_jsonrpc_bridge",
                supported_versions=("mcp_bridge/v1",),
                capabilities=("mcp_2025_06_18", "mcp_2024_11_05", "visibility_filter"),
                effects=(PURE_EFFECT,),
                execute_fn=_exec_stdio_jsonrpc_bridge,
            ),
            SlotEngineSpec(
                slot_id=SLOT_MCP_BRIDGE,
                engine_id="http_sse_mcp_bridge",
                engine_kind="http_sse_mcp_bridge",
                supported_versions=("mcp_bridge/v1",),
                capabilities=("mcp_2025_06_18", "mcp_2024_11_05", "visibility_filter"),
                effects=("network",),
                execute_fn=_exec_http_sse_mcp_bridge,
            ),
        ),
    }


def _build_refusal(
    code: str,
    message: str,
    next_action: str,
    *,
    retry: str = RETRY_AFTER_FIX,
    retry_after_seconds: int | None = None,
    automatic_retry: bool = False,
) -> EnvelopeRefusal:
    return envelope_refusal(
        code,
        message,
        next_action,
        retry=retry,
        effect_commitment=EFFECT_NONE,
        next_action_by=CALLER,
        retry_after_seconds=retry_after_seconds,
        automatic_retry=automatic_retry,
    )


class SevenLayerSlotHub:
    """Executes all 8 operational engine slots through their 7-layer component envelopes."""

    def __init__(
        self,
        engines_by_slot: Mapping[str, tuple[SlotEngineSpec, ...]] | None = None,
        *,
        lease_signing_material: str = "lease_hmac_key_v1_99a8b7c6d5e4f3",
        webhook_signing_material: str = "whsec_key_v1_1122334455667788",
        webhook_tolerance_seconds: int = DEFAULT_WEBHOOK_TOLERANCE_SECONDS,
        memory_byte_ceiling: int = DEFAULT_RUNTIME_MEMORY_BYTE_CEILING,
    ) -> None:
        self._engines: dict[str, tuple[SlotEngineSpec, ...]] = dict(
            engines_by_slot or build_default_slot_engines()
        )
        self._lease_signing_material = lease_signing_material
        self._webhook_signing_material = webhook_signing_material
        self._webhook_tolerance_seconds = webhook_tolerance_seconds
        self._memory_byte_ceiling = memory_byte_ceiling

        self._idempotency_cache: dict[tuple[str, str], tuple[str, SlotEnvelopeOutcome]] = {}
        self._journal_entries: dict[str, list[Any]] = {slot: [] for slot in HARDENED_SLOTS}
        self._metrics: dict[str, SlotTrackingMetrics] = {
            slot: SlotTrackingMetrics(slot_id=slot) for slot in HARDENED_SLOTS
        }
        self._settled_ledger_ids: dict[str, set[str]] = {
            SLOT_BILLING_SETTLEMENT: set(),
            SLOT_USAGE_EXPORT: set(),
        }
        self._paired_agent_sequences: dict[tuple[str, str], int] = {}

    def metrics_for(self, slot_id: str) -> SlotTrackingMetrics:
        return self._metrics[slot_id]

    def journal_for(self, slot_id: str) -> tuple[Any, ...]:
        return tuple(self._journal_entries[slot_id])

    def _finish_refusal(
        self,
        request: SlotEnvelopeRequest,
        frame: EnvelopeFrame,
        steps: list[tuple[str, str]],
        refused_by: str,
        refusal: EnvelopeRefusal,
        *,
        carrier: SlotCarrierEnvelope | None,
        verdicts: tuple[EnvelopeHandshakeVerdict, ...],
        account_checked: bool,
        preflight_report: EnvelopePreflightReport | None,
        normalized_headers: Mapping[str, str],
        started_ns: int,
        candidate_engines: tuple[str, ...],
        req_digest: str,
        attempt_count: int = 0,
    ) -> SlotEnvelopeOutcome:
        elapsed_ms = max(0.001, (time.perf_counter_ns() - started_ns) / 1_000_000.0)
        self._metrics[request.slot_id].record(OUTCOME_REFUSED, elapsed_ms)
        trace = EnvelopeTrace(
            component=request.slot_id,
            steps=tuple(steps),
            engine_dispatched=(refused_by == ENGINE_SOURCE),
            refused_by=refused_by,
            refusal=refusal,
        )
        payload_hash = carrier.payload_sha256 if carrier else compute_payload_sha256(
            normalize_value(request.payload)
        )
        corr_id = _correlation_id(request.slot_id, request.idempotency_key, payload_hash)
        chain_digests = tuple(
            e.entry_digest for e in self._journal_entries[request.slot_id]
            if e.request_identity == req_digest
        )
        receipt = EngineSelectionReceipt(
            slot_id=request.slot_id,
            selected_engine_id="",
            engine_kind="",
            candidate_engines=candidate_engines,
            fallback_occurred=False,
            fallback_reason=refusal.code,
            attempt_count=attempt_count,
            latency_ms=elapsed_ms,
            outcome=OUTCOME_REFUSED,
            correlation_id=corr_id,
            parent_correlation_id=request.parent_correlation_id,
            request_identity_digest=req_digest,
            journal_entry_digests=chain_digests,
        )
        return SlotEnvelopeOutcome(
            slot_id=request.slot_id,
            accepted=False,
            deduplicated=False,
            output=None,
            refusal=refusal,
            carrier=carrier,
            handshake_verdicts=verdicts,
            account_checked=account_checked,
            receipt=receipt,
            preflight_report=preflight_report,
            trace=trace,
            frame=frame,
            nested_outcomes=(),
            normalized_headers=normalized_headers,
        )

    def execute(self, request: SlotEnvelopeRequest) -> SlotEnvelopeOutcome:
        """Run one request through all 7 layers of its slot envelope."""
        started_ns = time.perf_counter_ns()
        slot_id = request.slot_id
        if slot_id not in SLOT_CONTRACTS:
            raise EnvelopeError("unknown_slot_id", f"{slot_id} is not one of {list(HARDENED_SLOTS)}")

        contract = SLOT_CONTRACTS[slot_id]
        engines = self._engines.get(slot_id, ())
        candidate_ids = tuple(item.engine_id for item in engines)

        # Layer 1 (frustration_avoidance): normalize whitespace and headers, check idempotency cache.
        normalized_payload: dict[str, Any] = normalize_value(dict(request.payload))
        normalized_headers = normalize_headers(request.headers)
        clean_idempotency_key = request.idempotency_key.strip()
        req_digest = request_identity_digest(f"{slot_id}:{clean_idempotency_key or 'missing'}")

        # Layer 7 (nested_envelopes) frame initialization or inheritance.
        if request.parent_frame is None:
            frame = root_frame(slot_id, automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS, deadline_at=request.now_epoch + 30.0)
        else:
            try:
                frame = enter_nested(request.parent_frame, slot_id, now=request.now_epoch)
            except EnvelopeError as exc:
                fallback_frame = request.parent_frame
                refusal = _build_refusal(
                    exc.code,
                    "The nested slot invocation violated the envelope frame nesting rules.",
                    "Remove the cycle, reduce the nesting depth, or extend the parent deadline before retrying.",
                    retry=DO_NOT_RETRY,
                )
                return self._finish_refusal(
                    request,
                    fallback_frame,
                    [(LAYER_CARRIER, LAYER_REFUSED)],
                    LAYER_CARRIER,
                    refusal,
                    carrier=None,
                    verdicts=(),
                    account_checked=False,
                    preflight_report=None,
                    normalized_headers=normalized_headers,
                    started_ns=started_ns,
                    candidate_engines=candidate_ids,
                    req_digest=req_digest,
                )

        if not clean_idempotency_key:
            refusal = _build_refusal(
                "missing_idempotency_key",
                "The slot request arrived without a non-empty idempotency key string.",
                "Supply a stable idempotency key for this request and send it again.",
                retry=RETRY_AFTER_FIX,
            )
            return self._finish_refusal(
                request,
                frame,
                [(LAYER_CARRIER, LAYER_REFUSED)],
                LAYER_CARRIER,
                refusal,
                carrier=None,
                verdicts=(),
                account_checked=False,
                preflight_report=None,
                normalized_headers=normalized_headers,
                started_ns=started_ns,
                candidate_engines=candidate_ids,
                req_digest=req_digest,
            )

        computed_payload_sha = compute_payload_sha256(normalized_payload)
        cache_key = (slot_id, clean_idempotency_key)
        if cache_key in self._idempotency_cache:
            cached_sha, cached_outcome = self._idempotency_cache[cache_key]
            if cached_sha != computed_payload_sha:
                refusal = _build_refusal(
                    "idempotency_payload_conflict",
                    "The same idempotency key was reused with different payload bytes.",
                    "Generate a fresh idempotency key for the new payload or restore the original payload bytes.",
                    retry=RETRY_AFTER_FIX,
                )
                return self._finish_refusal(
                    request,
                    frame,
                    [(LAYER_CARRIER, LAYER_REFUSED)],
                    LAYER_CARRIER,
                    refusal,
                    carrier=None,
                    verdicts=(),
                    account_checked=False,
                    preflight_report=None,
                    normalized_headers=normalized_headers,
                    started_ns=started_ns,
                    candidate_engines=candidate_ids,
                    req_digest=req_digest,
                )
            elapsed_ms = max(0.001, (time.perf_counter_ns() - started_ns) / 1_000_000.0)
            self._metrics[slot_id].record(OUTCOME_DEDUPLICATED, elapsed_ms)
            dedup_trace = EnvelopeTrace(
                component=slot_id,
                steps=(
                    (LAYER_CARRIER, LAYER_ACCEPTED),
                    (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                    (LAYER_ACCOUNT, LAYER_ACCEPTED),
                    (LAYER_TRACKING, LAYER_ANSWERED),
                ),
                engine_dispatched=False,
                refused_by="",
                refusal=None,
            )
            dedup_receipt = EngineSelectionReceipt(
                slot_id=slot_id,
                selected_engine_id=cached_outcome.receipt.selected_engine_id,
                engine_kind=cached_outcome.receipt.engine_kind,
                candidate_engines=candidate_ids,
                fallback_occurred=False,
                fallback_reason="idempotent_replay_short_circuit",
                attempt_count=0,
                latency_ms=elapsed_ms,
                outcome=OUTCOME_DEDUPLICATED,
                correlation_id=cached_outcome.receipt.correlation_id,
                parent_correlation_id=request.parent_correlation_id,
                request_identity_digest=req_digest,
                journal_entry_digests=cached_outcome.receipt.journal_entry_digests,
            )
            return SlotEnvelopeOutcome(
                slot_id=slot_id,
                accepted=True,
                deduplicated=True,
                output=cached_outcome.output,
                refusal=None,
                carrier=cached_outcome.carrier,
                handshake_verdicts=cached_outcome.handshake_verdicts,
                account_checked=True,
                receipt=dedup_receipt,
                preflight_report=cached_outcome.preflight_report,
                trace=dedup_trace,
                frame=frame,
                nested_outcomes=cached_outcome.nested_outcomes,
                normalized_headers=normalized_headers,
            )

        steps: list[tuple[str, str]] = []

        # Layer 2 (carrier): check contract_version, schema_digest, payload_sha256, and schema fields.
        expected_schema_digest = contract.schema_digest
        caller_schema_digest = request.schema_digest or expected_schema_digest
        caller_payload_sha = request.payload_sha256 or computed_payload_sha

        unknown_fields = sorted(set(normalized_payload) - set(contract.allowed_fields))
        missing_fields = [f for f in contract.required_fields if f not in normalized_payload]
        carrier_refusal: EnvelopeRefusal | None = None
        if request.contract_version != contract.contract_version:
            carrier_refusal = _build_refusal(
                "carrier_contract_version_mismatch",
                "The carrier envelope named an unsupported contract version for this slot.",
                "Set the carrier contract version to the slot's declared version and send the request again.",
                retry=RETRY_AFTER_FIX,
            )
        elif caller_schema_digest != expected_schema_digest:
            carrier_refusal = _build_refusal(
                "carrier_schema_digest_mismatch",
                "The carrier schema digest does not match the slot's current schema digest.",
                "Recompute the schema digest from the slot's declared field list and send the request again.",
                retry=RETRY_AFTER_FIX,
            )
        elif caller_payload_sha != computed_payload_sha:
            carrier_refusal = _build_refusal(
                "carrier_payload_digest_mismatch",
                "The carrier payload digest does not match the normalized payload bytes.",
                "Recompute the SHA-256 digest over the canonical payload JSON and send the request again.",
                retry=RETRY_AFTER_FIX,
            )
        elif unknown_fields or missing_fields:
            carrier_refusal = _build_refusal(
                "carrier_schema_fields_invalid",
                "The carrier payload is missing required fields or includes undeclared fields.",
                "Remove undeclared fields and supply every required field named in the slot contract.",
                retry=RETRY_AFTER_FIX,
            )

        carrier = SlotCarrierEnvelope(
            slot_id=slot_id,
            contract_version=request.contract_version,
            schema_digest=caller_schema_digest,
            payload_sha256=computed_payload_sha,
            payload=MappingProxyType(dict(normalized_payload)),
        )
        if carrier_refusal is not None:
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            return self._finish_refusal(
                request,
                frame,
                steps,
                LAYER_CARRIER,
                carrier_refusal,
                carrier=carrier,
                verdicts=(),
                account_checked=False,
                preflight_report=None,
                normalized_headers=normalized_headers,
                started_ns=started_ns,
                candidate_engines=candidate_ids,
                req_digest=req_digest,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3 (handshake): check parent authority attenuation, negotiate_handshake, and slot-specific rules.
        if request.parent_granted_effects is not None:
            unattenuated = set(request.granted_effects) - set(request.parent_granted_effects) - {PURE_EFFECT}
            if unattenuated:
                steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
                refusal = _build_refusal(
                    "nested_authority_escalation_refused",
                    "The nested slot requested effect permissions that its parent envelope does not hold.",
                    "Narrow the nested slot's granted effects to a subset of the parent's granted effects.",
                    retry=DO_NOT_RETRY,
                )
                return self._finish_refusal(
                    request,
                    frame,
                    steps,
                    LAYER_HANDSHAKE,
                    refusal,
                    carrier=carrier,
                    verdicts=(),
                    account_checked=False,
                    preflight_report=None,
                    normalized_headers=normalized_headers,
                    started_ns=started_ns,
                    candidate_engines=candidate_ids,
                    req_digest=req_digest,
                )

        handshake_req = EnvelopeHandshakeRequest(
            component=slot_id,
            requested_versions=request.requested_versions,
            required_capabilities=request.required_capabilities,
            advisory_capabilities=request.advisory_capabilities,
            granted_effects=request.granted_effects,
        )
        verdicts: list[EnvelopeHandshakeVerdict] = []
        eligible_engines: list[SlotEngineSpec] = []
        for engine_spec in engines:
            verdict = negotiate_handshake(handshake_req, engine_spec.declaration())
            verdicts.append(verdict)
            if verdict.proceeds:
                eligible_engines.append(engine_spec)

        slot_handshake_refusal = self._check_slot_specific_handshake(
            slot_id,
            normalized_payload,
            normalized_headers,
            request.account,
            computed_payload_sha,
            request.now_epoch,
        )
        if slot_handshake_refusal is not None or not eligible_engines:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            refusal = slot_handshake_refusal or _build_refusal(
                "handshake_no_compatible_engine",
                "No registered engine for this slot satisfied the requested version, capabilities, and effects.",
                "Align the requested protocol version, required capabilities, and granted effects with the slot.",
                retry=RETRY_AFTER_FIX,
            )
            return self._finish_refusal(
                request,
                frame,
                steps,
                LAYER_HANDSHAKE,
                refusal,
                carrier=carrier,
                verdicts=tuple(verdicts),
                account_checked=False,
                preflight_report=None,
                normalized_headers=normalized_headers,
                started_ns=started_ns,
                candidate_engines=candidate_ids,
                req_digest=req_digest,
            )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4 (account): verify active status, tenant isolation, parent tenant match, and quota.
        account_refusal = self._check_account_layer(request, normalized_payload)
        if account_refusal is not None:
            steps.append((LAYER_ACCOUNT, LAYER_REFUSED))
            return self._finish_refusal(
                request,
                frame,
                steps,
                LAYER_ACCOUNT,
                account_refusal,
                carrier=carrier,
                verdicts=tuple(verdicts),
                account_checked=True,
                preflight_report=None,
                normalized_headers=normalized_headers,
                started_ns=started_ns,
                candidate_engines=candidate_ids,
                req_digest=req_digest,
            )
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 5 (tracking): verify journal chain integrity before preflight and dispatch.
        try:
            journal_chain(self._journal_entries[slot_id], req_digest)
        except EnvelopeError as exc:
            steps.append((LAYER_TRACKING, LAYER_REFUSED))
            refusal = _build_refusal(
                exc.code,
                "The tracking journal chain for this request identity failed digest verification.",
                "Reconcile the corrupted journal entries before sending another request under this identity.",
                retry=DO_NOT_RETRY,
            )
            return self._finish_refusal(
                request,
                frame,
                steps,
                LAYER_TRACKING,
                refusal,
                carrier=carrier,
                verdicts=tuple(verdicts),
                account_checked=True,
                preflight_report=None,
                normalized_headers=normalized_headers,
                started_ns=started_ns,
                candidate_engines=candidate_ids,
                req_digest=req_digest,
            )
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6 (preflight): run declared checks and optional self-repairs before dispatch.
        preflight_report = self._run_slot_preflight(
            slot_id,
            normalized_payload,
            allow_repair=request.allow_preflight_repair,
        )
        if preflight_report.verdict == VERDICT_REFUSED or preflight_report.refusal is not None:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            return self._finish_refusal(
                request,
                frame,
                steps,
                LAYER_PREFLIGHT,
                preflight_report.refusal,
                carrier=carrier,
                verdicts=tuple(verdicts),
                account_checked=True,
                preflight_report=preflight_report,
                normalized_headers=normalized_headers,
                started_ns=started_ns,
                candidate_engines=candidate_ids,
                req_digest=req_digest,
            )
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))
        dispatch_payload = dict(preflight_report.context)

        # Engine dispatch with multi-engine fallback governed by RecoveryPolicy & RecoveryAllowance.
        recovery_policy = EnvelopeRecoveryPolicy(
            component=slot_id,
            maximum_automatic_attempts=min(2, MAXIMUM_AUTOMATIC_ATTEMPTS),
            recoverable_codes=contract.recoverable_codes,
        )
        selected_engine: SlotEngineSpec | None = None
        engine_output: dict[str, Any] | None = None
        fallback_occurred = False
        fallback_reason = ""
        attempt_count = 0
        last_engine_refusal: EnvelopeRefusal | None = None

        for idx, engine_spec in enumerate(eligible_engines):
            attempt_count += 1
            intent_entry = journal_intent(
                self._journal_entries[slot_id],
                component=slot_id,
                request_identity=req_digest,
                repeatable=True,
                at=FIXED_AUDIT_INSTANT,
            )
            self._journal_entries[slot_id].append(intent_entry)
            try:
                engine_output = engine_spec.execute_fn(dispatch_payload, normalized_headers)
                selected_engine = engine_spec
                if idx > 0:
                    fallback_occurred = True
                result_sha = compute_payload_sha256(engine_output)
                outcome_entry = journal_outcome(
                    self._journal_entries[slot_id],
                    component=slot_id,
                    request_identity=req_digest,
                    request_outcome=REQUEST_ANSWERED,
                    task_outcome=TASK_COMPLETED,
                    effect_state=EFFECT_STATE_CONFIRMED,
                    result_digest=result_sha,
                    at=FIXED_AUDIT_INSTANT,
                )
                self._journal_entries[slot_id].append(outcome_entry)
                break
            except TransientEngineUnavailableError as exc:
                outcome_entry = journal_outcome(
                    self._journal_entries[slot_id],
                    component=slot_id,
                    request_identity=req_digest,
                    request_outcome="refused",
                    task_outcome=TASK_FAILED,
                    effect_state=EFFECT_STATE_NONE,
                    result_digest="",
                    at=FIXED_AUDIT_INSTANT,
                )
                self._journal_entries[slot_id].append(outcome_entry)
                transient_refusal = _build_refusal(
                    exc.code,
                    "The primary slot engine experienced a transient unavailability before writing any effect.",
                    "Retry the request with the same identity or allow the slot fallback chain to proceed.",
                    retry=RETRY_NOW_SAME_IDENTITY,
                    automatic_retry=True,
                )
                last_engine_refusal = transient_refusal
                fallback_reason = exc.code
                has_next_engine = (idx + 1) < len(eligible_engines)
                if not has_next_engine or not may_recover(recovery_policy, transient_refusal, frame.allowance):
                    break

        if selected_engine is None or engine_output is None:
            final_refusal = last_engine_refusal or _build_refusal(
                "all_slot_engines_failed",
                "Every eligible engine in the slot fallback chain failed to complete the request.",
                "Inspect the upstream engine health and retry after restoring service availability.",
                retry=RETRY_AFTER_WAIT,
                retry_after_seconds=15,
            )
            return self._finish_refusal(
                request,
                frame,
                steps,
                ENGINE_SOURCE,
                final_refusal,
                carrier=carrier,
                verdicts=tuple(verdicts),
                account_checked=True,
                preflight_report=preflight_report,
                normalized_headers=normalized_headers,
                started_ns=started_ns,
                candidate_engines=candidate_ids,
                req_digest=req_digest,
                attempt_count=attempt_count,
            )

        # Record post-commit state for idempotency ledgers and transport sequence tracking.
        if slot_id == SLOT_BILLING_SETTLEMENT:
            self._settled_ledger_ids[SLOT_BILLING_SETTLEMENT].add(str(dispatch_payload["event_id"]))
        elif slot_id == SLOT_USAGE_EXPORT:
            self._settled_ledger_ids[SLOT_USAGE_EXPORT].add(str(dispatch_payload["meter_event_id"]))
        elif slot_id == SLOT_PAIRED_AGENT_TRANSPORT:
            seq_key = (str(dispatch_payload["lease_id"]), str(dispatch_payload["agent_id"]))
            self._paired_agent_sequences[seq_key] = int(dispatch_payload["sequence"])

        corr_id = _correlation_id(slot_id, clean_idempotency_key, computed_payload_sha)

        # Layer 7 (nested_envelopes): execute any nested child slot invocations with inherited frame & attenuated authority.
        nested_outcomes: list[SlotEnvelopeOutcome] = []
        for child_req in request.nested_invocations:
            bound_child = SlotEnvelopeRequest(
                slot_id=child_req.slot_id,
                idempotency_key=child_req.idempotency_key,
                contract_version=child_req.contract_version,
                requested_versions=child_req.requested_versions,
                payload=child_req.payload,
                account=child_req.account,
                headers=child_req.headers,
                required_capabilities=child_req.required_capabilities,
                advisory_capabilities=child_req.advisory_capabilities,
                granted_effects=child_req.granted_effects,
                schema_digest=child_req.schema_digest,
                payload_sha256=child_req.payload_sha256,
                allow_preflight_repair=child_req.allow_preflight_repair,
                now_epoch=request.now_epoch,
                parent_frame=frame,
                parent_granted_effects=request.granted_effects,
                parent_tenant_id=request.account.tenant_id,
                parent_correlation_id=corr_id,
                nested_invocations=child_req.nested_invocations,
            )
            child_outcome = self.execute(bound_child)
            nested_outcomes.append(child_outcome)
            if not child_outcome.accepted:
                child_refusal = child_outcome.refusal or _build_refusal(
                    "nested_slot_refused",
                    "A nested component envelope refused its part of the composite operation.",
                    "Inspect the nested refusal code and fix the child slot input or permissions.",
                    retry=RETRY_AFTER_FIX,
                )
                return self._finish_refusal(
                    request,
                    frame,
                    steps,
                    ENGINE_SOURCE,
                    child_refusal,
                    carrier=carrier,
                    verdicts=tuple(verdicts),
                    account_checked=True,
                    preflight_report=preflight_report,
                    normalized_headers=normalized_headers,
                    started_ns=started_ns,
                    candidate_engines=candidate_ids,
                    req_digest=req_digest,
                    attempt_count=attempt_count,
                )

        elapsed_ms = max(0.001, (time.perf_counter_ns() - started_ns) / 1_000_000.0)
        outcome_label = OUTCOME_FALLBACK_COMPLETED if fallback_occurred else OUTCOME_COMPLETED
        self._metrics[slot_id].record(outcome_label, elapsed_ms)

        chain_digests = tuple(
            e.entry_digest for e in self._journal_entries[slot_id]
            if e.request_identity == req_digest
        )
        receipt = EngineSelectionReceipt(
            slot_id=slot_id,
            selected_engine_id=selected_engine.engine_id,
            engine_kind=selected_engine.engine_kind,
            candidate_engines=candidate_ids,
            fallback_occurred=fallback_occurred,
            fallback_reason=fallback_reason,
            attempt_count=attempt_count,
            latency_ms=elapsed_ms,
            outcome=outcome_label,
            correlation_id=corr_id,
            parent_correlation_id=request.parent_correlation_id,
            request_identity_digest=req_digest,
            journal_entry_digests=chain_digests,
        )
        trace = EnvelopeTrace(
            component=slot_id,
            steps=tuple(steps),
            engine_dispatched=True,
            refused_by="",
            refusal=None,
        )
        outcome = SlotEnvelopeOutcome(
            slot_id=slot_id,
            accepted=True,
            deduplicated=False,
            output=engine_output,
            refusal=None,
            carrier=carrier,
            handshake_verdicts=tuple(verdicts),
            account_checked=True,
            receipt=receipt,
            preflight_report=preflight_report,
            trace=trace,
            frame=frame,
            nested_outcomes=tuple(nested_outcomes),
            normalized_headers=normalized_headers,
        )
        self._idempotency_cache[cache_key] = (computed_payload_sha, outcome)
        return outcome

    def _check_slot_specific_handshake(
        self,
        slot_id: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        account: AccountScopeContext,
        payload_sha256: str,
        now_epoch: float,
    ) -> EnvelopeRefusal | None:
        if slot_id == SLOT_PAIRED_AGENT_TRANSPORT:
            lease_id = str(payload.get("lease_id", ""))
            agent_id = str(payload.get("agent_id", ""))
            sequence = payload.get("sequence")
            lease_expires_at = payload.get("lease_expires_at")
            if not isinstance(sequence, int) or not isinstance(lease_expires_at, (int, float)):
                return _build_refusal(
                    "paired_transport_invalid_lease_fields",
                    "The paired transport request requires integer sequence and numeric lease expiration.",
                    "Supply a valid integer sequence number and numeric lease expiration timestamp.",
                    retry=RETRY_AFTER_FIX,
                )
            if float(lease_expires_at) <= now_epoch:
                return _build_refusal(
                    "paired_transport_lease_expired",
                    "The paired agent lease has already expired according to the envelope clock.",
                    "Renew the paired agent transport lease before sending additional frames.",
                    retry=RETRY_AFTER_FIX,
                )
            provided_sig = headers.get("x-paired-lease-signature", "")
            expected_sig = sign_paired_transport_frame(
                self._lease_signing_material,
                lease_id,
                agent_id,
                sequence,
                payload_sha256,
            )
            if not provided_sig or not hmac.compare_digest(provided_sig, expected_sig):
                return _build_refusal(
                    "paired_transport_signature_invalid",
                    "The paired agent transport frame signature failed HMAC verification.",
                    "Sign the lease identifier, agent identifier, sequence, and payload digest with the active lease key.",
                    retry=DO_NOT_RETRY,
                )
            last_seq = self._paired_agent_sequences.get((lease_id, agent_id), 0)
            if sequence <= last_seq:
                return _build_refusal(
                    "paired_transport_sequence_replay",
                    "The paired agent transport frame sequence number was already processed.",
                    "Advance the frame sequence number monotonically for each new paired transport frame.",
                    retry=DO_NOT_RETRY,
                )

        elif slot_id == SLOT_BILLING_SETTLEMENT:
            sig_header = headers.get("stripe-signature", "")
            parts = dict(
                item.split("=", 1) for item in sig_header.split(",")
                if "=" in item
            )
            ts_text = parts.get("t", "")
            v1_sig = parts.get("v1", "")
            if not ts_text.isdigit() or not v1_sig:
                return _build_refusal(
                    "webhook_signature_missing",
                    "The billing settlement request is missing a well-formed Stripe signature header.",
                    "Include the timestamp and HMAC signature in the stripe-signature header.",
                    retry=DO_NOT_RETRY,
                )
            ts_val = int(ts_text)
            if abs(now_epoch - ts_val) > self._webhook_tolerance_seconds:
                return _build_refusal(
                    "webhook_timestamp_outside_window",
                    "The billing webhook signature timestamp lies outside the allowed replay window.",
                    "Send a freshly signed webhook event within the five-minute tolerance window.",
                    retry=DO_NOT_RETRY,
                )
            expected_header = sign_stripe_webhook(self._webhook_signing_material, ts_val, payload)
            expected_v1 = dict(item.split("=", 1) for item in expected_header.split(","))["v1"]
            if not hmac.compare_digest(v1_sig, expected_v1):
                return _build_refusal(
                    "webhook_signature_invalid",
                    "The billing webhook HMAC signature did not match the canonical event payload.",
                    "Verify the webhook signing key and sign the exact canonical payload bytes.",
                    retry=DO_NOT_RETRY,
                )

        elif slot_id == SLOT_MCP_BRIDGE:
            mcp_version = str(payload.get("mcp_protocol_version", ""))
            tool_name = str(payload.get("tool_name", ""))
            if mcp_version not in SUPPORTED_MCP_VERSIONS:
                return _build_refusal(
                    "mcp_protocol_version_unsupported",
                    "The requested Model Context Protocol version is not supported by this bridge.",
                    "Negotiate version 2025-06-18 or 2024-11-05 during initialization and retry.",
                    retry=RETRY_AFTER_FIX,
                )
            if tool_name in STAFF_ONLY_TOOLS and account.principal_role != PRINCIPAL_STAFF:
                return _build_refusal(
                    "mcp_tool_visibility_refused",
                    "The requested tool is restricted to staff principals and hidden from customer bridges.",
                    "Call a customer-visible tool or authenticate with a staff principal session.",
                    retry=DO_NOT_RETRY,
                )
            if tool_name not in CUSTOMER_VISIBLE_TOOLS and tool_name not in STAFF_ONLY_TOOLS:
                return _build_refusal(
                    "mcp_tool_unknown",
                    "The requested tool is not registered on the Model Context Protocol bridge.",
                    "List the bridge tools first and select a registered tool name.",
                    retry=RETRY_AFTER_FIX,
                )

        return None

    def _check_account_layer(
        self,
        request: SlotEnvelopeRequest,
        payload: Mapping[str, Any],
    ) -> EnvelopeRefusal | None:
        acct = request.account
        if acct.account_status != ACCOUNT_ACTIVE or not acct.tenant_id.strip() or not acct.account_id.strip():
            return _build_refusal(
                "account_not_active",
                "The calling account is not active or lacks a bound tenant identifier.",
                "Activate the account and bind a valid tenant scope before invoking this slot.",
                retry=DO_NOT_RETRY,
            )
        payload_tenant = str(payload.get("tenant_id", ""))
        if payload_tenant != acct.tenant_id:
            return _build_refusal(
                "cross_tenant_isolation_violation",
                "The payload tenant identifier does not match the authenticated account tenant scope.",
                "Bind the request payload to the authenticated tenant identifier and never cross tenants.",
                retry=DO_NOT_RETRY,
            )
        if request.parent_tenant_id and request.parent_tenant_id != acct.tenant_id:
            return _build_refusal(
                "nested_cross_tenant_violation",
                "The nested slot invocation attempted to switch tenants away from its parent envelope.",
                "Keep the parent tenant scope unchanged across every nested slot call.",
                retry=DO_NOT_RETRY,
            )
        if acct.requested_units <= 0 or (acct.consumed_units + acct.requested_units) > acct.quota_limit:
            return _build_refusal(
                "account_quota_exhausted",
                "The tenant account has exhausted its allocated quota for this slot operation.",
                "Wait for the quota window to reset or increase the account plan allowance.",
                retry=RETRY_AFTER_WAIT,
                retry_after_seconds=60,
            )
        return None

    def _run_slot_preflight(
        self,
        slot_id: str,
        payload: Mapping[str, Any],
        *,
        allow_repair: bool,
    ) -> EnvelopePreflightReport:
        checks: list[EnvelopePreflightCheck] = []
        repairs: list[EnvelopeSelfRepair] = []

        if slot_id in (SLOT_RUN_HISTORY_EXPORT, SLOT_TELEMETRY_SINK, SLOT_FAILURE_JOURNAL):
            def _check_no_secrets_or_pii(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
                if _contains_secret_or_pii(ctx):
                    return _build_refusal(
                        "preflight_secret_or_pii_blocked",
                        "The export payload contains unredacted secret material or personal data.",
                        "Scrub all credentials and personal addresses from the payload before exporting.",
                        retry=RETRY_AFTER_FIX,
                    )
                return None

            checks.append(
                EnvelopePreflightCheck(
                    check_id="no_unredacted_secrets_or_pii",
                    diagnoses=("preflight_secret_or_pii_blocked",),
                    run=_check_no_secrets_or_pii,
                )
            )
            if allow_repair:
                repairs.append(
                    EnvelopeSelfRepair(
                        repair_id="scrub_secrets_and_pii_in_memory",
                        fixes=("preflight_secret_or_pii_blocked",),
                        effects=(PURE_EFFECT,),
                        maximum_applications=1,
                        apply=lambda ctx: _scrub_secret_and_pii(dict(ctx)),
                    )
                )

        if slot_id == SLOT_RUN_HISTORY_EXPORT:
            def _check_positive_duration(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
                dur = ctx.get("duration_ms")
                if not isinstance(dur, (int, float)) or dur < 0:
                    return _build_refusal(
                        "preflight_invalid_span_duration",
                        "The exported attempt span is missing a non-negative measured duration.",
                        "Record a non-negative duration in milliseconds before exporting run history.",
                        retry=RETRY_AFTER_FIX,
                    )
                return None

            checks.append(
                EnvelopePreflightCheck(
                    check_id="measured_span_duration_present",
                    diagnoses=("preflight_invalid_span_duration",),
                    run=_check_positive_duration,
                )
            )

        elif slot_id == SLOT_RUNTIME_MEMORY:
            ceiling = self._memory_byte_ceiling

            def _check_memory_ceiling(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
                body_bytes = len(str(ctx.get("note_body", "")).encode("utf-8"))
                effective_limit = min(ceiling, int(ctx.get("max_bytes", ceiling)))
                if body_bytes > effective_limit:
                    return _build_refusal(
                        "preflight_memory_byte_ceiling_exceeded",
                        "The runtime memory note exceeds the maximum byte ceiling for one run note.",
                        "Trim or summarize the runtime memory note so its UTF-8 byte length fits the ceiling.",
                        retry=RETRY_AFTER_FIX,
                    )
                return None

            checks.append(
                EnvelopePreflightCheck(
                    check_id="runtime_memory_byte_ceiling",
                    diagnoses=("preflight_memory_byte_ceiling_exceeded",),
                    run=_check_memory_ceiling,
                )
            )

        elif slot_id == SLOT_BILLING_SETTLEMENT:
            settled_events = self._settled_ledger_ids[SLOT_BILLING_SETTLEMENT]

            def _check_billing_ledger(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
                event_id = str(ctx.get("event_id", ""))
                amount = ctx.get("amount_cents")
                if event_id in settled_events:
                    return _build_refusal(
                        "preflight_duplicate_settlement_blocked",
                        "The billing settlement event identifier has already been applied in the ledger.",
                        "Do not replay settled billing events; query the settlement ledger instead.",
                        retry=DO_NOT_RETRY,
                    )
                if not isinstance(amount, int) or amount <= 0:
                    return _build_refusal(
                        "preflight_invalid_settlement_amount",
                        "The billing settlement amount must be a positive integer number of cents.",
                        "Provide a positive integer amount in cents before settling the billing event.",
                        retry=RETRY_AFTER_FIX,
                    )
                return None

            checks.append(
                EnvelopePreflightCheck(
                    check_id="billing_idempotency_ledger_check",
                    diagnoses=("preflight_duplicate_settlement_blocked", "preflight_invalid_settlement_amount"),
                    run=_check_billing_ledger,
                )
            )

        elif slot_id == SLOT_USAGE_EXPORT:
            settled_meters = self._settled_ledger_ids[SLOT_USAGE_EXPORT]

            def _check_usage_ledger(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
                meter_id = str(ctx.get("meter_event_id", ""))
                qty = ctx.get("quantity")
                if meter_id in settled_meters:
                    return _build_refusal(
                        "preflight_duplicate_meter_event_blocked",
                        "The usage meter event identifier was already exported to the billing provider.",
                        "Do not resend an already exported usage meter event identifier.",
                        retry=DO_NOT_RETRY,
                    )
                if not isinstance(qty, int) or qty <= 0:
                    return _build_refusal(
                        "preflight_invalid_meter_quantity",
                        "The usage export quantity must be a positive whole number of metered units.",
                        "Supply a positive integer quantity before exporting the usage event.",
                        retry=RETRY_AFTER_FIX,
                    )
                return None

            checks.append(
                EnvelopePreflightCheck(
                    check_id="usage_idempotency_ledger_check",
                    diagnoses=("preflight_duplicate_meter_event_blocked", "preflight_invalid_meter_quantity"),
                    run=_check_usage_ledger,
                )
            )

        elif slot_id == SLOT_PAIRED_AGENT_TRANSPORT:
            def _check_frame_size(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
                frame_bytes = len(_canonical_json_bytes({"frame": ctx.get("command_frame")}))
                if frame_bytes > DEFAULT_TRANSPORT_FRAME_BYTE_CEILING:
                    return _build_refusal(
                        "preflight_transport_frame_too_large",
                        "The paired agent command frame exceeds the maximum frame byte ceiling.",
                        "Split the command payload into smaller frames within the transport limit.",
                        retry=RETRY_AFTER_FIX,
                    )
                return None

            checks.append(
                EnvelopePreflightCheck(
                    check_id="paired_transport_frame_ceiling",
                    diagnoses=("preflight_transport_frame_too_large",),
                    run=_check_frame_size,
                )
            )

        elif slot_id == SLOT_MCP_BRIDGE:
            def _check_jsonrpc_method(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
                method = str(ctx.get("jsonrpc_method", ""))
                if method not in ("tools/call", "tools/list"):
                    return _build_refusal(
                        "preflight_mcp_method_not_allowed",
                        "The Model Context Protocol bridge preflight only admits tool listing and invocation.",
                        "Set the JSON-RPC method to tools/list or tools/call and retry.",
                        retry=RETRY_AFTER_FIX,
                    )
                return None

            checks.append(
                EnvelopePreflightCheck(
                    check_id="mcp_jsonrpc_method_check",
                    diagnoses=("preflight_mcp_method_not_allowed",),
                    run=_check_jsonrpc_method,
                )
            )

        return run_preflight(
            slot_id,
            checks,
            repairs=tuple(repairs),
            context=payload,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )


def _sample_valid_payloads(tenant_id: str = "tenant_alpha") -> dict[str, dict[str, Any]]:
    return {
        SLOT_RUN_HISTORY_EXPORT: {
            "tenant_id": tenant_id,
            "run_id": "run_20261016_01",
            "attempt_id": "att_01",
            "duration_ms": 42.5,
            "spans": [{"name": "step.execute", "duration_ms": 42.5}],
            "destination": "otel_collector",
        },
        SLOT_USAGE_EXPORT: {
            "tenant_id": tenant_id,
            "meter_event_id": "meter_evt_001",
            "metric_name": "intelligence_units",
            "quantity": 5,
            "recorded_at": FIXED_AUDIT_INSTANT,
        },
        SLOT_FAILURE_JOURNAL: {
            "tenant_id": tenant_id,
            "failure_ref": "ref_fail_001",
            "route": "/v1/protocol",
            "status_code": 503,
            "summary": "Upstream storage pool temporarily busy.",
            "alive": True,
            "ready": False,
        },
        SLOT_RUNTIME_MEMORY: {
            "tenant_id": tenant_id,
            "run_id": "run_20261016_01",
            "loop_id": "loop_sibling_1",
            "note_key": "hypothesis_summary",
            "note_body": "Verified invariant holds across all eight operational slots.",
            "max_bytes": 4096,
        },
        SLOT_PAIRED_AGENT_TRANSPORT: {
            "tenant_id": tenant_id,
            "lease_id": "lease_9001",
            "agent_id": "agent_paired_01",
            "sequence": 1,
            "lease_expires_at": 1792177200.0,
            "command_frame": {"op": "status_ping", "step": 1},
        },
        SLOT_TELEMETRY_SINK: {
            "tenant_id": tenant_id,
            "stream_name": "slot_envelope_telemetry",
            "events": [{"event": "slot.dispatched", "ok": True}],
            "batch_size": 1,
        },
        SLOT_BILLING_SETTLEMENT: {
            "tenant_id": tenant_id,
            "event_id": "evt_stripe_001",
            "event_type": "checkout.session.completed",
            "amount_cents": 2900,
            "currency": "usd",
            "plan_tier": "pro",
        },
        SLOT_MCP_BRIDGE: {
            "tenant_id": tenant_id,
            "mcp_protocol_version": MCP_VERSION_2025,
            "jsonrpc_method": "tools/call",
            "tool_name": "baltor_search",
            "arguments": {"query": "component envelope layers"},
        },
    }


def make_valid_request(
    slot_id: str,
    *,
    idempotency_key: str = "idem_valid_001",
    tenant_id: str = "tenant_alpha",
    principal_role: str = PRINCIPAL_CUSTOMER,
    payload_overrides: Mapping[str, Any] | None = None,
    lease_signing_material: str = "lease_hmac_key_v1_99a8b7c6d5e4f3",
    webhook_signing_material: str = "whsec_key_v1_1122334455667788",
    now_epoch: float = 1792173600.0,
    allow_preflight_repair: bool = False,
    nested_invocations: tuple[SlotEnvelopeRequest, ...] = (),
) -> SlotEnvelopeRequest:
    """Construct a valid, properly signed 7-layer request for any of the 8 hardened slots."""
    contract = SLOT_CONTRACTS[slot_id]
    payload = dict(_sample_valid_payloads(tenant_id)[slot_id])
    if payload_overrides:
        payload.update(payload_overrides)
    normalized_payload = normalize_value(payload)
    payload_sha = compute_payload_sha256(normalized_payload)

    headers: dict[str, str] = {"x-request-source": "slot-hardening-suite"}
    if slot_id == SLOT_PAIRED_AGENT_TRANSPORT:
        headers["x-paired-lease-signature"] = sign_paired_transport_frame(
            lease_signing_material,
            str(normalized_payload["lease_id"]),
            str(normalized_payload["agent_id"]),
            int(normalized_payload["sequence"]),
            payload_sha,
        )
    elif slot_id == SLOT_BILLING_SETTLEMENT:
        headers["stripe-signature"] = sign_stripe_webhook(
            webhook_signing_material,
            int(now_epoch),
            normalized_payload,
        )

    return SlotEnvelopeRequest(
        slot_id=slot_id,
        idempotency_key=idempotency_key,
        contract_version=contract.contract_version,
        requested_versions=(contract.contract_version,),
        payload=payload,
        account=AccountScopeContext(
            tenant_id=tenant_id,
            account_id=f"acct_{tenant_id}",
            principal_role=principal_role,
        ),
        headers=headers,
        required_capabilities=(),
        advisory_capabilities=(),
        granted_effects=(PURE_EFFECT, "network", "external_effect"),
        schema_digest=contract.schema_digest,
        payload_sha256=payload_sha,
        allow_preflight_repair=allow_preflight_repair,
        now_epoch=now_epoch,
        nested_invocations=nested_invocations,
    )


def run_eight_slot_benchmark() -> dict[str, Any]:
    """Benchmark primary vs fallback engines and verify all 7 layers across all 8 slots."""
    hub = SevenLayerSlotHub()
    slot_rows: list[dict[str, Any]] = []
    matrix: dict[str, dict[str, str]] = {}

    for slot_id in HARDENED_SLOTS:
        # 1. Primary engine execution
        primary_req = make_valid_request(slot_id, idempotency_key=f"bench_primary_{slot_id}")
        primary_out = hub.execute(primary_req)

        # 2. Rapid retry deduplication (Layer 1 frustration_avoidance)
        dedup_out = hub.execute(primary_req)

        # 3. Fallback chain benchmark: primary raises transient failure, secondary engine completes
        base_engines = build_default_slot_engines()[slot_id]
        primary_spec, fallback_spec = base_engines[0], base_engines[1]

        def _failing_primary(_payload: Mapping[str, Any], _headers: Mapping[str, str]) -> dict[str, Any]:
            raise TransientEngineUnavailableError("upstream_transient_unavailable", "Simulated primary outage.")

        fallback_hub = SevenLayerSlotHub(
            engines_by_slot={
                **build_default_slot_engines(),
                slot_id: (
                    SlotEngineSpec(
                        slot_id=primary_spec.slot_id,
                        engine_id=primary_spec.engine_id,
                        engine_kind=primary_spec.engine_kind,
                        supported_versions=primary_spec.supported_versions,
                        capabilities=primary_spec.capabilities,
                        effects=primary_spec.effects,
                        execute_fn=_failing_primary,
                    ),
                    fallback_spec,
                ),
            }
        )
        fb_overrides: dict[str, Any] = {}
        if slot_id == SLOT_PAIRED_AGENT_TRANSPORT:
            fb_overrides["sequence"] = 2
        elif slot_id == SLOT_BILLING_SETTLEMENT:
            fb_overrides["event_id"] = "evt_stripe_fallback_002"
        elif slot_id == SLOT_USAGE_EXPORT:
            fb_overrides["meter_event_id"] = "meter_evt_fallback_002"

        fallback_req = make_valid_request(
            slot_id,
            idempotency_key=f"bench_fallback_{slot_id}",
            payload_overrides=fb_overrides,
        )
        fallback_out = fallback_hub.execute(fallback_req)

        # 4. Nested envelope check (Layer 7): invoke telemetry_sink or failure_journal as a child slot
        child_slot = SLOT_FAILURE_JOURNAL if slot_id == SLOT_TELEMETRY_SINK else SLOT_TELEMETRY_SINK
        child_req = make_valid_request(
            child_slot,
            idempotency_key=f"bench_nested_child_{slot_id}",
        )
        nested_overrides: dict[str, Any] = {}
        if slot_id == SLOT_PAIRED_AGENT_TRANSPORT:
            nested_overrides["sequence"] = 3
        elif slot_id == SLOT_BILLING_SETTLEMENT:
            nested_overrides["event_id"] = "evt_stripe_nested_003"
        elif slot_id == SLOT_USAGE_EXPORT:
            nested_overrides["meter_event_id"] = "meter_evt_nested_003"

        parent_with_nested_req = make_valid_request(
            slot_id,
            idempotency_key=f"bench_nested_parent_{slot_id}",
            payload_overrides=nested_overrides,
            nested_invocations=(child_req,),
        )
        nested_out = hub.execute(parent_with_nested_req)

        # 5. Known-wrong control per slot (carrier tamper, cross-tenant, and bad version)
        tampered_carrier_req = SlotEnvelopeRequest(
            **{
                **primary_req.__dict__,
                "idempotency_key": f"bench_tampered_{slot_id}",
                "payload_sha256": "0" * 64,
            }
        )
        tampered_out = hub.execute(tampered_carrier_req)

        cross_tenant_overrides: dict[str, Any] = {"tenant_id": "tenant_beta"}
        if slot_id == SLOT_PAIRED_AGENT_TRANSPORT:
            cross_tenant_overrides["sequence"] = 4
        cross_tenant_req = make_valid_request(
            slot_id,
            idempotency_key=f"bench_cross_tenant_{slot_id}",
            tenant_id="tenant_alpha",
            payload_overrides=cross_tenant_overrides,
        )
        cross_tenant_out = hub.execute(cross_tenant_req)

        all_layers_verified = (
            primary_out.accepted
            and dedup_out.accepted
            and dedup_out.deduplicated
            and fallback_out.accepted
            and fallback_out.receipt.fallback_occurred
            and fallback_out.receipt.selected_engine_id == fallback_spec.engine_id
            and nested_out.accepted
            and len(nested_out.nested_outcomes) == 1
            and nested_out.nested_outcomes[0].accepted
            and nested_out.nested_outcomes[0].frame.depth == 1
            and not tampered_out.accepted
            and tampered_out.trace.refused_by == LAYER_CARRIER
            and not cross_tenant_out.accepted
            and cross_tenant_out.trace.refused_by == LAYER_ACCOUNT
        )

        matrix[slot_id] = {
            LAYER_FRUSTRATION_AVOIDANCE: "full" if dedup_out.deduplicated else "none",
            LAYER_CARRIER: "full" if not tampered_out.accepted else "none",
            LAYER_HANDSHAKE: "full" if bool(primary_out.handshake_verdicts) else "none",
            LAYER_ACCOUNT: "full" if not cross_tenant_out.accepted else "none",
            LAYER_TRACKING: "full" if primary_out.receipt.correlation_id.startswith("ref_") else "none",
            LAYER_PREFLIGHT: "full" if primary_out.preflight_report is not None and primary_out.preflight_report.ready else "none",
            NESTED_ENVELOPES: "full" if (nested_out.accepted and nested_out.nested_outcomes[0].frame.depth == 1) else "none",
        }

        slot_rows.append({
            "slot_id": slot_id,
            "primary_engine_id": primary_out.receipt.selected_engine_id,
            "fallback_engine_id": fallback_out.receipt.selected_engine_id,
            "primary_latency_ms": primary_out.receipt.latency_ms,
            "fallback_latency_ms": fallback_out.receipt.latency_ms,
            "dedup_latency_ms": dedup_out.receipt.latency_ms,
            "fallback_attempts": fallback_out.receipt.attempt_count,
            "nested_child_slot": child_slot,
            "nested_depth": nested_out.nested_outcomes[0].frame.depth,
            "all_layers_verified": all_layers_verified,
            "layer_coverage": matrix[slot_id],
        })

    return {
        "record_type": BENCHMARK_REPORT_RECORD_TYPE,
        "slot_count": len(HARDENED_SLOTS),
        "layer_count": len(COVERAGE_LAYERS),
        "all_verified": all(row["all_layers_verified"] for row in slot_rows),
        "slots": slot_rows,
        "verification_matrix": matrix,
    }


def self_test() -> dict[str, Any]:
    """Run deterministic self-tests for all 8 hardened slots and their 7 envelope layers."""
    report = run_eight_slot_benchmark()
    return {
        "record_type": "slot_handshake_hardening_self_test/v1",
        "all_passed": report["all_verified"],
        "slot_count": report["slot_count"],
        "verification_matrix": report["verification_matrix"],
    }


if __name__ == "__main__":
    print(json.dumps(run_eight_slot_benchmark(), indent=2))
