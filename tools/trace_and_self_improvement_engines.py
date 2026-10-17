"""Swappable multi-engine trace, sync, and continuous self-improvement suite.

Implements four engine slot families wrapped in the 7-layer component envelope
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`,
`preflight`, `nested_envelopes`) with automatic fallback chains:

1. Slot Family A (`frontend_behavior_trace`):
   - `in_tab_session_ring_buffer`
   - `aggregate_funnel_step_counter`
   - `voluntary_redacted_diagnostic_bundle`
2. Slot Family B (`harness_local_trace_store`):
   - `local_sqlite_wal_trace_store`
   - `local_jsonl_ring_spool`
   - `in_memory_ephemeral_trace_buffer`
3. Slot Family C (`cloud_trace_sync`):
   - `cloud_batch_digest_exporter`
   - `edge_worker_beacon_exporter`
   - `offline_spool_with_circuit_breaker`
4. Slot Family D (`continuous_self_improvement`):
   - `heuristic_gap_cluster_improver`
   - `lsh_alias_and_query_relaxation_synthesizer`
   - `harmony_pareto_verified_promoter`
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_DURABLE_PENDING,
    EFFECT_NONE,
    ENGINE_SOURCE,
    INBOUND_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_NOT_APPLICABLE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    OPERATOR,
    PURE_EFFECT,
    RECONCILE_BEFORE_RETRY,
    RETRY_AFTER_FIX,
    RETRY_AFTER_WAIT,
    RETRY_NOW_SAME_IDENTITY,
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
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    ANSWER_FROM_FIRST_RESULT,
    DISPATCH,
    EFFECT_STATE_CONFIRMED,
    EFFECT_STATE_NONE,
    RECONCILE_FIRST,
    REQUEST_ANSWERED,
    RESYNC_IN_SYNC,
    RESYNC_NOW,
    RESYNC_WAIT,
    TASK_COMPLETED,
    EnvelopeResyncBackoff,
    EnvelopeResyncObservation,
    journal_decision,
    journal_intent,
    journal_outcome,
    journal_reconciliation,
    request_identity_digest,
    resync_decision,
)
from loop_engine.core.run_history_usage import normalized_model_usage  # noqa: E402
from loop_engine.core.service_runtime.feedback import (  # noqa: E402
    GAP_HOLDS_QUERY_TEXT,
    GAP_SCHEMA,
    RATING_SCHEMA,
    REQUEST_SCHEMA,
    ServiceRuntimeError,
    assert_metadata_only,
    gap_hour,
    gap_identity,
    search_gap_payload,
)
from loop_engine.core.service_runtime.observability import (  # noqa: E402
    FAILURE_RECORD_VERSION,
    new_request_reference,
    valid_reference,
)

# ---------------------------------------------------------------------------
# Slot family identifiers, record versions, and refusal guidance
# ---------------------------------------------------------------------------

SLOT_FRONTEND_TRACE = "frontend_behavior_trace"
SLOT_LOCAL_TRACE_STORE = "harness_local_trace_store"
SLOT_CLOUD_TRACE_SYNC = "cloud_trace_sync"
SLOT_SELF_IMPROVEMENT = "continuous_self_improvement"
ALL_SLOTS = (
    SLOT_FRONTEND_TRACE,
    SLOT_LOCAL_TRACE_STORE,
    SLOT_CLOUD_TRACE_SYNC,
    SLOT_SELF_IMPROVEMENT,
)

FRONTEND_REQUEST_VERSION = "frontend_trace_request/v1"
FRONTEND_OUTCOME_VERSION = "frontend_trace_outcome/v1"
DIAGNOSTIC_BUNDLE_VERSION = "voluntary_diagnostic_bundle/v1"
FUNNEL_COUNTER_VERSION = "aggregate_funnel_step_count/v1"

LOCAL_TRACE_REQUEST_VERSION = "harness_trace_request/v1"
LOCAL_TRACE_OUTCOME_VERSION = "harness_trace_outcome/v1"
HARNESS_SPAN_VERSION = "harness_turn_trace/v1"

CLOUD_SYNC_REQUEST_VERSION = "cloud_trace_sync_request/v1"
CLOUD_SYNC_OUTCOME_VERSION = "cloud_trace_sync_outcome/v1"
CLOUD_BATCH_VERSION = "cloud_trace_batch_digest/v1"
EDGE_BEACON_VERSION = "edge_worker_aggregate_beacon/v1"

SELF_IMPROVEMENT_REQUEST_VERSION = "self_improvement_request/v1"
SELF_IMPROVEMENT_OUTCOME_VERSION = "self_improvement_outcome/v1"
PROPOSAL_RECORD_VERSION = "self_improvement_proposal/v1"
PARETO_VERIFICATION_VERSION = "pareto_verification_report/v1"
CANARY_PROMOTION_VERSION = "canary_promotion_decision/v1"

#: How the 4 slot families close the `none` and `partial` gaps recorded in
#: `src/loop_engine/data/component_envelope_coverage_baseline.yaml`.
BASELINE_ENVELOPE_GAP_CLOSURE = MappingProxyType({
    "runtime_memory": {
        "slot_family": SLOT_FRONTEND_TRACE,
        "baseline": {
            "frustration_avoidance": "none",
            "carrier": "none",
            "handshake": "none",
            "account": "not_applicable",
            "tracking": "none",
            "preflight": "none",
            "nested_envelopes": "not_applicable",
        },
        "target_with_envelope_suite": {
            "frustration_avoidance": "full",
            "carrier": "full",
            "handshake": "full",
            "account": "full",
            "tracking": "full",
            "preflight": "full",
            "nested_envelopes": "full",
        },
    },
    "run_history_export": {
        "slot_family": SLOT_LOCAL_TRACE_STORE,
        "baseline": {
            "frustration_avoidance": "none",
            "carrier": "none",
            "handshake": "none",
            "account": "not_applicable",
            "tracking": "none",
            "preflight": "none",
            "nested_envelopes": "not_applicable",
        },
        "target_with_envelope_suite": {
            "frustration_avoidance": "full",
            "carrier": "full",
            "handshake": "full",
            "account": "full",
            "tracking": "full",
            "preflight": "full",
            "nested_envelopes": "full",
        },
    },
    "usage_export": {
        "slot_family": SLOT_CLOUD_TRACE_SYNC,
        "baseline": {
            "frustration_avoidance": "none",
            "carrier": "none",
            "handshake": "none",
            "account": "none",
            "tracking": "none",
            "preflight": "none",
            "nested_envelopes": "not_applicable",
        },
        "target_with_envelope_suite": {
            "frustration_avoidance": "full",
            "carrier": "full",
            "handshake": "full",
            "account": "full",
            "tracking": "full",
            "preflight": "full",
            "nested_envelopes": "full",
        },
    },
    "failure_journal": {
        "slot_family": SLOT_SELF_IMPROVEMENT,
        "baseline": {
            "frustration_avoidance": "partial",
            "carrier": "none",
            "handshake": "none",
            "account": "not_applicable",
            "tracking": "partial",
            "preflight": "none",
            "nested_envelopes": "not_applicable",
        },
        "target_with_envelope_suite": {
            "frustration_avoidance": "full",
            "carrier": "full",
            "handshake": "full",
            "account": "full",
            "tracking": "full",
            "preflight": "full",
            "nested_envelopes": "full",
        },
    },
})

REFUSAL_GUIDANCE = MappingProxyType({
    "carrier_schema_invalid": (
        "The request record is missing a required field or carries an undeclared version.",
        "Format the request using the slot's declared record version and required fields, then send it again.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "cookie_or_third_party_tracker_forbidden": (
        "The browser trace payload attempted to set a cookie or load an external analytics script.",
        "Remove cookies and third-party script references so the trace stays inside the tab memory.",
        DO_NOT_RETRY,
        CALLER,
        EFFECT_NONE,
    ),
    "raw_query_text_forbidden_in_aggregate_gap": (
        "The aggregate funnel or search gap payload carried raw query text, which the privacy notice forbids.",
        "Strip raw query text and retain only the UTC hour, mode, and allowlisted filter tokens before recording.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "voluntary_opt_in_required": (
        "A diagnostic bundle attachment requires explicit customer opt-in before any trace leaves the browser tab.",
        "Ask the customer to confirm diagnostic attachment opt-in on the support or material request form first.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "invalid_refusal_reference": (
        "The trace carried a refusal reference that does not match the issued base32 reference format.",
        "Pass only an issued ref_ request reference from a service refusal response, then record the step again.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "secret_or_pii_detected_in_trace": (
        "The trace payload contained an unredacted API key, bearer token, environment secret, email, or home path.",
        "Remove the credential or personal path, or enable the preflight scrubber repair before writing the trace.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "secret_or_pii_repairable": (
        "The preflight check found a credential, email, or home path that the pure scrubber self-repair can redact.",
        "Allow the preflight scrubber self-repair to redact sensitive tokens before the trace engine runs.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "account_authority_missing": (
        "The request lacks a valid tenant identity or the entitlement scope needed for this trace operation.",
        "Authenticate with an active tenant session or grant the required scope before sending the request.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "handshake_incompatible": (
        "No installed engine in the slot matched the requested version, capabilities, and granted effects.",
        "Grant the required effects or select a compatible engine version in the slot request, then try again.",
        RETRY_AFTER_FIX,
        OPERATOR,
        EFFECT_NONE,
    ),
    "journal_reconcile_required": (
        "An earlier attempt for this request identity stopped with an unsettled effect state.",
        "Reconcile the earlier attempt against the destination store before sending this request identity again.",
        RECONCILE_BEFORE_RETRY,
        OPERATOR,
        EFFECT_DURABLE_PENDING,
    ),
    "cloud_budget_exceeded": (
        "The trace batch exceeds the remaining cloud sync byte budget or rate allowance for this window.",
        "Wait for the next sync window or switch to the edge beacon or offline spool fallback engine.",
        RETRY_AFTER_WAIT,
        CALLER,
        EFFECT_NONE,
    ),
    "self_approval_refused": (
        "The candidate proposal producer and the independent verifier share the same identity, which is forbidden.",
        "Route the candidate proposal to an independent verifier Loop with a distinct reviewer identity.",
        DO_NOT_RETRY,
        CALLER,
        EFFECT_NONE,
    ),
    "pareto_regression_refused": (
        "The candidate change regressed at least one Pareto objective or failed held-out negative-transfer checks.",
        "Keep the candidate in candidate_only status, inspect the regressed objective, and revise the proposal.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
    ),
    "all_slot_engines_failed": (
        "Every eligible engine in the slot's fallback chain reported an operational failure.",
        "Inspect the engine failure details in the outcome trace and restore storage or network availability.",
        RETRY_AFTER_WAIT,
        OPERATOR,
        EFFECT_NONE,
    ),
})


def build_refusal(
    code: str,
    *,
    retry_after_seconds: int | None = None,
    automatic_retry: bool = False,
) -> EnvelopeRefusal:
    """Build a canonical `envelope_refusal/v1` from the closed guidance table."""
    message, next_action, retry, by, commitment = REFUSAL_GUIDANCE[code]
    wait = retry_after_seconds if retry == RETRY_AFTER_WAIT else None
    if retry == RETRY_AFTER_WAIT and wait is None:
        wait = 5
    return envelope_refusal(
        code,
        message,
        next_action,
        retry=retry,
        effect_commitment=commitment,
        next_action_by=by,
        retry_after_seconds=wait,
        automatic_retry=automatic_retry,
    )


def canonical_json(value: Any) -> str:
    """Deterministic JSON serialization for content-addressed SHA-256 digests."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_digest(value: Any) -> str:
    """Compute a 64-hex-character SHA-256 digest over canonical JSON or text."""
    raw = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Layer 3 / Layer 6 Secret, Credential & PII Scrubber
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "baltor_api_key",
        re.compile(r"\bbaltor_[A-Za-z0-9_-]{8,}\b"),
        "[REDACTED_BALTOR_KEY]",
    ),
    (
        "provider_api_key",
        re.compile(r"\b(?:sk-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{10,}|xoxb-[A-Za-z0-9-]+)\b"),
        "[REDACTED_API_KEY]",
    ),
    (
        "bearer_token",
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
        "Bearer [REDACTED_TOKEN]",
    ),
    (
        "env_secret",
        re.compile(
            r"\b(BALTOR_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|SUPABASE_SERVICE_ROLE_KEY|"
            r"STRIPE_SECRET_KEY|RESEND_API_KEY|DATABASE_URL|SECRET_KEY|PASSWORD)\s*=\s*([^\s\"',;]+)"
        ),
        r"\1=[REDACTED_ENV_SECRET]",
    ),
    (
        "email_pii",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    (
        "home_path_pii",
        re.compile(r"(?:/home/|/Users/|C:\\Users\\)[A-Za-z0-9._-]+(?:/[^\s\"',;)]*)?"),
        "[REDACTED_HOME_PATH]",
    ),
)

_SENSITIVE_KEY_NAMES = frozenset({
    "api_key",
    "access_token",
    "authorization",
    "bearer_token",
    "client_secret",
    "cookie",
    "password",
    "private_key",
    "raw_credential",
    "secret",
    "secret_key",
    "session_cookie",
})


class SecretAndPiiScrubber:
    """Inspects and scrubs raw API keys, Bearer tokens, env secrets, emails, and home paths."""

    @classmethod
    def inspect(cls, payload: Any) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        cls._walk_inspect(payload, path="$", findings=findings)
        return findings

    @classmethod
    def _walk_inspect(cls, value: Any, *, path: str, findings: list[dict[str, str]]) -> None:
        if isinstance(value, Mapping):
            for k, v in value.items():
                key_str = str(k)
                subpath = f"{path}.{key_str}"
                if key_str.lower() in _SENSITIVE_KEY_NAMES and isinstance(v, str) and v and not v.startswith("[REDACTED"):
                    findings.append({"path": subpath, "kind": "sensitive_field_name"})
                cls._walk_inspect(v, path=subpath, findings=findings)
        elif isinstance(value, (list, tuple)):
            for idx, item in enumerate(value):
                cls._walk_inspect(item, path=f"{path}[{idx}]", findings=findings)
        elif isinstance(value, str):
            for kind, pattern, _replacement in _SECRET_PATTERNS:
                if pattern.search(value):
                    findings.append({"path": path, "kind": kind})

    @classmethod
    def scrub(cls, payload: Any) -> tuple[Any, int]:
        """Return `(scrubbed_payload, redaction_count)` without mutating the input."""
        count = 0

        def _walk_scrub(value: Any) -> Any:
            nonlocal count
            if isinstance(value, Mapping):
                out: dict[str, Any] = {}
                for k, v in value.items():
                    key_str = str(k)
                    if (
                        key_str.lower() in _SENSITIVE_KEY_NAMES
                        and isinstance(v, str)
                        and v
                        and not v.startswith("[REDACTED")
                    ):
                        out[key_str] = "[REDACTED_CREDENTIAL_FIELD]"
                        count += 1
                    else:
                        out[key_str] = _walk_scrub(v)
                return out
            if isinstance(value, tuple):
                return tuple(_walk_scrub(item) for item in value)
            if isinstance(value, list):
                return [_walk_scrub(item) for item in value]
            if isinstance(value, str):
                text = value
                for _kind, pattern, replacement in _SECRET_PATTERNS:
                    text, replacements = pattern.subn(replacement, text)
                    count += replacements
                return text
            return value

        scrubbed = _walk_scrub(payload)
        return scrubbed, count


def make_scrubber_preflight(secret_policy: str = "refuse") -> tuple[tuple[EnvelopePreflightCheck, ...], tuple[EnvelopeSelfRepair, ...]]:
    """Build Layer 6 preflight checks and optional pure self-repair for secret/PII scrubbing."""

    def _check_payload(context: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = context.get("payload")
        findings = SecretAndPiiScrubber.inspect(payload)
        if not findings:
            return None
        if secret_policy == "scrub":
            return build_refusal("secret_or_pii_repairable")
        return build_refusal("secret_or_pii_detected_in_trace")

    check = EnvelopePreflightCheck(
        "secret_credential_and_pii_scrubber",
        ("secret_or_pii_detected_in_trace", "secret_or_pii_repairable"),
        _check_payload,
    )
    if secret_policy != "scrub":
        return (check,), ()

    def _repair_payload(context: Mapping[str, Any]) -> Mapping[str, Any]:
        scrubbed, redactions = SecretAndPiiScrubber.scrub(context.get("payload"))
        updated = dict(context)
        updated["payload"] = scrubbed
        updated["redactions_applied"] = int(context.get("redactions_applied", 0)) + redactions
        return updated

    repair = EnvelopeSelfRepair(
        "scrub_secrets_and_pii_before_write",
        ("secret_or_pii_repairable",),
        (PURE_EFFECT,),
        1,
        _repair_payload,
    )
    return (check,), (repair,)


# ---------------------------------------------------------------------------
# Shared 7-Layer Envelope Runner with Automatic Fallback Cascade
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineSpec:
    """Declaration of one swappable engine inside a slot family."""

    slot_id: str
    engine_id: str
    supported_versions: tuple[str, ...]
    capabilities: tuple[str, ...]
    effects: tuple[str, ...]
    runner: Callable[[Mapping[str, Any]], dict[str, Any]] = field(compare=False)


@dataclass(frozen=True)
class EnvelopeExecutionOutcome:
    """Complete 7-layer envelope outcome for any of the four slot families."""

    record_type: str
    slot_id: str
    ok: bool
    selected_engine: str
    fallback_chain_tried: tuple[str, ...]
    result: dict[str, Any] | None
    refusal: dict[str, Any] | None
    handshake: tuple[dict[str, Any], ...]
    preflight: tuple[dict[str, Any], ...]
    tracking_decision: dict[str, Any] | None
    frame: dict[str, Any]
    trace: dict[str, Any]
    redactions_applied: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "slot_id": self.slot_id,
            "ok": self.ok,
            "selected_engine": self.selected_engine,
            "fallback_chain_tried": list(self.fallback_chain_tried),
            "result": self.result,
            "refusal": self.refusal,
            "handshake": list(self.handshake),
            "preflight": list(self.preflight),
            "tracking_decision": self.tracking_decision,
            "frame": self.frame,
            "trace": self.trace,
            "redactions_applied": self.redactions_applied,
        }


class EngineOperationalFailure(RuntimeError):
    """Raised by an engine when a runtime condition (lock, network, quota) triggers fallback."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


class SevenLayerSlotEnvelope:
    """Executes a slot request through all 7 envelope layers and an ordered engine fallback chain."""

    def __init__(
        self,
        slot_id: str,
        outcome_record_type: str,
        engines: tuple[EngineSpec, ...],
        *,
        recovery_policy: EnvelopeRecoveryPolicy | None = None,
    ):
        self.slot_id = slot_id
        self.outcome_record_type = outcome_record_type
        self.engines = engines
        self.recovery_policy = recovery_policy or EnvelopeRecoveryPolicy(slot_id, 1, ("transient_lock_contended",))
        self.journal_entries: list[ Any ] = []
        self.confirmed_results: dict[str, dict[str, Any]] = {}

    def execute(
        self,
        request: Mapping[str, Any],
        *,
        granted_effects: tuple[str, ...] = ("pure", "reads_fs", "writes_fs", "network"),
        parent_frame: EnvelopeFrame | None = None,
        now: float | None = None,
        extra_preflight_checks: tuple[EnvelopePreflightCheck, ...] = (),
        extra_repairs: tuple[EnvelopeSelfRepair, ...] = (),
    ) -> EnvelopeExecutionOutcome:
        current_now = time.monotonic() if now is None else now
        frame = (
            enter_nested(parent_frame, self.slot_id, now=current_now)
            if parent_frame is not None
            else root_frame(self.slot_id)
        )

        # Layer 2: Carrier check
        carrier_refusal = self._check_carrier(request)
        if carrier_refusal is not None:
            trace = EnvelopeTrace(
                self.slot_id,
                ((LAYER_CARRIER, LAYER_REFUSED),),
                False,
                LAYER_CARRIER,
                carrier_refusal,
            )
            return EnvelopeExecutionOutcome(
                self.outcome_record_type,
                self.slot_id,
                False,
                "",
                (),
                None,
                carrier_refusal.to_dict(),
                (),
                (),
                None,
                frame.to_dict(),
                trace.to_dict(),
            )

        # Layer 3: Handshake across installed engines in declared order
        req_version = str(request["record_type"])
        req_caps = tuple(request.get("required_capabilities", ()))
        adv_caps = tuple(request.get("advisory_capabilities", ()))
        preferred = tuple(request.get("preferred_engines", ())) or tuple(e.engine_id for e in self.engines)

        handshake_verdicts: list[EnvelopeHandshakeVerdict] = []
        eligible_engines: list[EngineSpec] = []
        engine_map = {e.engine_id: e for e in self.engines}
        ordered_specs = [engine_map[eid] for eid in preferred if eid in engine_map] + [
            e for e in self.engines if e.engine_id not in preferred
        ]
        for spec in ordered_specs:
            h_req = EnvelopeHandshakeRequest(
                self.slot_id,
                (req_version,),
                req_caps,
                adv_caps,
                granted_effects,
            )
            h_decl = EnvelopeHandshakeDeclaration(
                spec.engine_id,
                spec.supported_versions,
                spec.capabilities,
                spec.effects,
            )
            verdict = negotiate_handshake(h_req, h_decl)
            handshake_verdicts.append(verdict)
            if verdict.proceeds:
                eligible_engines.append(spec)

        if not eligible_engines:
            refusal = build_refusal("handshake_incompatible")
            trace = EnvelopeTrace(
                self.slot_id,
                ((LAYER_CARRIER, LAYER_ACCEPTED), (LAYER_HANDSHAKE, LAYER_REFUSED)),
                False,
                LAYER_HANDSHAKE,
                refusal,
            )
            return EnvelopeExecutionOutcome(
                self.outcome_record_type,
                self.slot_id,
                False,
                "",
                (),
                None,
                refusal.to_dict(),
                tuple(v.to_dict() for v in handshake_verdicts),
                (),
                None,
                frame.to_dict(),
                trace.to_dict(),
            )

        # Layer 4: Account check
        account_result, account_refusal = self._check_account(request)
        if account_refusal is not None:
            trace = EnvelopeTrace(
                self.slot_id,
                (
                    (LAYER_CARRIER, LAYER_ACCEPTED),
                    (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                    (LAYER_ACCOUNT, LAYER_REFUSED),
                ),
                False,
                LAYER_ACCOUNT,
                account_refusal,
            )
            return EnvelopeExecutionOutcome(
                self.outcome_record_type,
                self.slot_id,
                False,
                "",
                (),
                None,
                account_refusal.to_dict(),
                tuple(v.to_dict() for v in handshake_verdicts),
                (),
                None,
                frame.to_dict(),
                trace.to_dict(),
            )

        # Layer 5: Tracking & idempotency replay check
        req_id_raw = request.get("request_id")
        tracking_layer_state = LAYER_NOT_APPLICABLE
        tracking_decision_dict: dict[str, Any] | None = None
        req_digest = ""
        if req_id_raw:
            req_digest = request_identity_digest(str(req_id_raw))
            decision = journal_decision(self.journal_entries, req_digest)
            tracking_decision_dict = decision.to_dict()
            if decision.decision == ANSWER_FROM_FIRST_RESULT:
                cached = self.confirmed_results.get(decision.result_digest)
                if cached is not None:
                    trace = EnvelopeTrace(
                        self.slot_id,
                        (
                            (LAYER_CARRIER, LAYER_ACCEPTED),
                            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                            (LAYER_ACCOUNT, account_result),
                            (LAYER_TRACKING, LAYER_ANSWERED),
                        ),
                        False,
                        "",
                        None,
                    )
                    return EnvelopeExecutionOutcome(
                        self.outcome_record_type,
                        self.slot_id,
                        True,
                        cached.get("engine_id", eligible_engines[0].engine_id),
                        (cached.get("engine_id", eligible_engines[0].engine_id),),
                        {**cached, "replayed_from_journal": True},
                        None,
                        tuple(v.to_dict() for v in handshake_verdicts),
                        (),
                        tracking_decision_dict,
                        frame.to_dict(),
                        trace.to_dict(),
                    )
            if decision.decision == RECONCILE_FIRST:
                refusal = build_refusal("journal_reconcile_required")
                trace = EnvelopeTrace(
                    self.slot_id,
                    (
                        (LAYER_CARRIER, LAYER_ACCEPTED),
                        (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                        (LAYER_ACCOUNT, account_result),
                        (LAYER_TRACKING, LAYER_REFUSED),
                    ),
                    False,
                    LAYER_TRACKING,
                    refusal,
                )
                return EnvelopeExecutionOutcome(
                    self.outcome_record_type,
                    self.slot_id,
                    False,
                    "",
                    (),
                    None,
                    refusal.to_dict(),
                    tuple(v.to_dict() for v in handshake_verdicts),
                    (),
                    tracking_decision_dict,
                    frame.to_dict(),
                    trace.to_dict(),
                )
            tracking_layer_state = LAYER_ACCEPTED

        # Layer 6: Preflight checks and bounded self-repair
        secret_policy = str(request.get("secret_policy", "refuse"))
        scrubber_checks, scrubber_repairs = make_scrubber_preflight(secret_policy)
        all_checks = scrubber_checks + tuple(extra_preflight_checks)
        all_repairs = scrubber_repairs + tuple(extra_repairs)
        preflight_ctx = {
            "request": dict(request),
            "payload": request.get("payload", {}),
            "redactions_applied": 0,
            "parent_frame": frame,
        }
        preflight_report = run_preflight(
            self.slot_id,
            all_checks,
            all_repairs,
            preflight_ctx,
            EnvelopePreflightGrant(granted_effects),
        )
        redactions = int(preflight_report.context.get("redactions_applied", 0))
        if not preflight_report.ready:
            refusal = preflight_report.refusal
            assert refusal is not None
            trace = EnvelopeTrace(
                self.slot_id,
                (
                    (LAYER_CARRIER, LAYER_ACCEPTED),
                    (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                    (LAYER_ACCOUNT, account_result),
                    (LAYER_TRACKING, tracking_layer_state),
                    (LAYER_PREFLIGHT, LAYER_REFUSED),
                ),
                False,
                LAYER_PREFLIGHT,
                refusal,
            )
            return EnvelopeExecutionOutcome(
                self.outcome_record_type,
                self.slot_id,
                False,
                "",
                (),
                None,
                refusal.to_dict(),
                tuple(v.to_dict() for v in handshake_verdicts),
                (preflight_report.to_dict(),),
                tracking_decision_dict,
                frame.to_dict(),
                trace.to_dict(),
                redactions_applied=redactions,
            )

        # Layer 7: Engine slot dispatch with automatic fallback cascade
        repaired_payload = preflight_report.context.get("payload", request.get("payload", {}))
        dispatch_context = {
            **dict(request),
            "payload": repaired_payload,
            "redactions_applied": redactions,
            "frame": frame,
        }
        tried: list[str] = []
        timestamp_iso = "2026-10-16T23:00:00Z"
        if req_digest:
            intent = journal_intent(
                self.journal_entries,
                component=self.slot_id,
                request_identity=req_digest,
                repeatable=True,
                at=timestamp_iso,
            )
            self.journal_entries.append(intent)

        for spec in eligible_engines:
            tried.append(spec.engine_id)
            while True:
                try:
                    engine_result = spec.runner(dispatch_context)
                    engine_result = {
                        **engine_result,
                        "engine_id": spec.engine_id,
                        "redactions_applied": engine_result.get("redactions_applied", 0) + redactions,
                    }
                    result_dig = sha256_digest(engine_result)
                    if req_digest:
                        committed = journal_outcome(
                            self.journal_entries,
                            component=self.slot_id,
                            request_identity=req_digest,
                            request_outcome=REQUEST_ANSWERED,
                            task_outcome=TASK_COMPLETED,
                            effect_state=EFFECT_STATE_CONFIRMED,
                            result_digest=result_dig,
                            at=timestamp_iso,
                        )
                        self.journal_entries.append(committed)
                        self.confirmed_results[result_dig] = engine_result
                    trace = EnvelopeTrace(
                        self.slot_id,
                        (
                            (LAYER_CARRIER, LAYER_ACCEPTED),
                            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                            (LAYER_ACCOUNT, account_result),
                            (LAYER_TRACKING, tracking_layer_state),
                            (LAYER_PREFLIGHT, LAYER_ACCEPTED),
                        ),
                        True,
                        "",
                        None,
                    )
                    return EnvelopeExecutionOutcome(
                        self.outcome_record_type,
                        self.slot_id,
                        True,
                        spec.engine_id,
                        tuple(tried),
                        engine_result,
                        None,
                        tuple(v.to_dict() for v in handshake_verdicts),
                        (preflight_report.to_dict(),),
                        tracking_decision_dict,
                        frame.to_dict(),
                        trace.to_dict(),
                        redactions_applied=engine_result["redactions_applied"],
                    )
                except EngineOperationalFailure as exc:
                    if exc.code == "transient_lock_contended":
                        transient_refusal = envelope_refusal(
                            "transient_lock_contended",
                            "A transient local lock prevented the write from starting on this attempt.",
                            "Retry the same write immediately under the shared recovery allowance.",
                            retry=RETRY_NOW_SAME_IDENTITY,
                            effect_commitment=EFFECT_NONE,
                            automatic_retry=True,
                        )
                        if may_recover(self.recovery_policy, transient_refusal, frame.allowance):
                            dispatch_context["recovered_retry"] = True
                            continue
                    break

        if req_digest:
            failed_outcome = journal_outcome(
                self.journal_entries,
                component=self.slot_id,
                request_identity=req_digest,
                request_outcome="refused",
                task_outcome="failed",
                effect_state=EFFECT_STATE_NONE,
                result_digest="",
                at=timestamp_iso,
            )
            self.journal_entries.append(failed_outcome)

        refusal = build_refusal("all_slot_engines_failed", retry_after_seconds=5)
        trace = EnvelopeTrace(
            self.slot_id,
            (
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, account_result),
                (LAYER_TRACKING, tracking_layer_state),
                (LAYER_PREFLIGHT, LAYER_ACCEPTED),
            ),
            True,
            ENGINE_SOURCE,
            refusal,
        )
        return EnvelopeExecutionOutcome(
            self.outcome_record_type,
            self.slot_id,
            False,
            "",
            tuple(tried),
            None,
            refusal.to_dict(),
            tuple(v.to_dict() for v in handshake_verdicts),
            (preflight_report.to_dict(),),
            tracking_decision_dict,
            frame.to_dict(),
            trace.to_dict(),
            redactions_applied=redactions,
        )

    def _check_carrier(self, request: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if not isinstance(request, Mapping):
            return build_refusal("carrier_schema_invalid")
        if "record_type" not in request or "payload" not in request:
            return build_refusal("carrier_schema_invalid")
        if not isinstance(request["payload"], Mapping):
            return build_refusal("carrier_schema_invalid")
        return None

    def _check_account(self, request: Mapping[str, Any]) -> tuple[str, EnvelopeRefusal | None]:
        account = request.get("account")
        if account is None:
            return LAYER_NOT_APPLICABLE, None
        if not isinstance(account, Mapping) or not account.get("tenant_id") or not account.get("authorized", True):
            return LAYER_REFUSED, build_refusal("account_authority_missing")
        return LAYER_ACCEPTED, None


# ---------------------------------------------------------------------------
# Slot Family A — Frontend User Behavior & Friction Trace Engines
# ---------------------------------------------------------------------------

FRONTEND_SETUP_RECIPE_SELECTED = "setup_recipe_selected"
FRONTEND_CONNECTION_CHECK = "connection_check"
FRONTEND_FUNNEL_STEP = "funnel_step"
FRONTEND_REFUSAL_ENCOUNTERED = "refusal_encountered"
FRONTEND_FRUSTRATION_SIGNAL = "frustration_signal"
FUNNEL_SEARCH = "search"
FUNNEL_PREVIEW = "preview"
FUNNEL_DOWNLOAD = "download"
ALLOWED_FUNNEL_VALUES = (FUNNEL_SEARCH, FUNNEL_PREVIEW, FUNNEL_DOWNLOAD)
ENGINE_DIAGNOSTIC_BUNDLE = "voluntary_redacted_diagnostic_bundle"


class InTabSessionRingBufferEngine:
    """`in_tab_session_ring_buffer`: zero-cookie in-memory ring buffer for tab session telemetry."""

    def __init__(self, max_events: int = 128):
        self.max_events = max_events
        self._ring: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._frustration_Window: dict[str, list[float]] = {}

    def record_event(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_session_storage_unavailable"):
            raise EngineOperationalFailure("session_ring_unavailable", "in-tab ring buffer disabled by policy")

        event_kind = str(payload.get("event_kind", FRONTEND_FUNNEL_STEP))
        now_ms = float(payload.get("timestamp_ms", time.time() * 1000.0))
        entry: dict[str, Any] = {
            "event_kind": event_kind,
            "timestamp_ms": now_ms,
            "cookies_set": 0,
            "third_party_scripts": 0,
        }

        if event_kind == FRONTEND_SETUP_RECIPE_SELECTED:
            entry["harness_id"] = str(payload.get("harness_id", "opencode"))
            entry["recipe_id"] = str(payload.get("recipe_id", "quickstart_mcp"))
            entry["step"] = str(payload.get("step", "select_recipe"))
        elif event_kind == FRONTEND_CONNECTION_CHECK:
            entry["latency_ms"] = float(payload.get("latency_ms", 0.0))
            entry["status"] = str(payload.get("status", "connected"))
        elif event_kind == FRONTEND_FUNNEL_STEP:
            stage = str(payload.get("stage", FUNNEL_SEARCH))
            if stage not in ALLOWED_FUNNEL_VALUES:
                stage = FUNNEL_SEARCH
            entry["stage"] = stage
            entry["mode"] = str(payload.get("mode", "lexical"))[:16]
            entry["hit_count"] = int(payload.get("hit_count", 0))
            entry["latency_ms"] = float(payload.get("latency_ms", 0.0))
        elif event_kind == FRONTEND_REFUSAL_ENCOUNTERED:
            ref = str(payload.get("request_reference", ""))
            entry["request_reference"] = ref
            entry["route"] = str(payload.get("route", "/api/v1/provisioning"))
            entry["refusal_code"] = str(payload.get("refusal_code", "rate_limit_exceeded"))
        elif event_kind == FRONTEND_FRUSTRATION_SIGNAL:
            signal_kind = str(payload.get("signal_kind", "rage_click"))
            target = str(payload.get("target_control", "copy_recipe_button"))
            clicks = int(payload.get("click_count", 4))
            window_ms = float(payload.get("window_ms", 600.0))
            entry["signal_kind"] = signal_kind
            entry["target_control"] = target
            entry["click_count"] = clicks
            entry["window_ms"] = window_ms
            entry["frustration_detected"] = clicks >= 3 and window_ms <= 1500.0

        self._ring.append(entry)
        funnel_counts = {"search": 0, "preview": 0, "download": 0}
        refusal_refs: list[str] = []
        frustration_signals = 0
        for item in self._ring:
            if item["event_kind"] == "funnel_step":
                funnel_counts[item["stage"]] = funnel_counts.get(item["stage"], 0) + 1
            elif item["event_kind"] == "refusal_encountered":
                refusal_refs.append(item["request_reference"])
            elif item["event_kind"] == "frustration_signal" and item.get("frustration_detected"):
                frustration_signals += 1

        return {
            "record_type": "in_tab_session_snapshot/v1",
            "buffered_events": len(self._ring),
            "capacity": self.max_events,
            "cookies_set": 0,
            "third_party_analytics_loaded": False,
            "funnel_counts": funnel_counts,
            "refusal_references": refusal_refs,
            "frustration_signals": frustration_signals,
            "latest_event": entry,
        }


class AggregateFunnelStepCounterEngine:
    """`aggregate_funnel_step_counter`: privacy-notice-compliant hourly aggregate funnel & gap counter."""

    def __init__(self) -> None:
        self._hourly_buckets: dict[str, dict[str, Any]] = {}

    def record_event(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_counter_unavailable"):
            raise EngineOperationalFailure("aggregate_counter_unavailable", "aggregate counter unavailable")

        now_sec = float(payload.get("now_epoch", 1792191600.0))
        stage = str(payload.get("stage", payload.get("event_kind", "search")))
        hit_count = int(payload.get("hit_count", 0))
        mode = str(payload.get("mode", "lexical"))[:16]
        filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
        tiers = payload.get("library_tiers") if isinstance(payload.get("library_tiers"), list) else ["free"]

        # Build canonical search_gap/v1 payload via feedback.py to enforce metadata-only rule
        gap_base = search_gap_payload(
            {"mode": mode, "filters": filters, "library_tiers": tiers, "query": payload.get("query")},
            now_sec,
        )
        bucket_record = {
            "record_type": FUNNEL_COUNTER_VERSION,
            "hour": gap_hour(now_sec),
            "stage": stage,
            "mode": gap_base["mode"],
            "filters": gap_base["filters"],
            "library_tiers": gap_base["library_tiers"],
            "zero_hit": hit_count == 0,
        }
        assert_metadata_only(bucket_record, payload.get("query"))
        bucket_id = gap_identity(gap_base) + ":" + stage
        existing = self._hourly_buckets.get(bucket_id)
        if existing is None:
            stored = {**bucket_record, "count": 1, "zero_hit_count": 1 if hit_count == 0 else 0}
        else:
            stored = {
                **existing,
                "count": existing["count"] + 1,
                "zero_hit_count": existing["zero_hit_count"] + (1 if hit_count == 0 else 0),
            }
        self._hourly_buckets[bucket_id] = stored
        return {
            "record_type": FUNNEL_COUNTER_VERSION,
            "bucket_id": bucket_id,
            "hour": stored["hour"],
            "stage": stage,
            "count": stored["count"],
            "zero_hit_count": stored["zero_hit_count"],
            "search_gap_compatible": True,
            "retains_query_text": False,
            "retains_account_id": False,
        }


class VoluntaryRedactedDiagnosticBundleEngine:
    """`voluntary_redacted_diagnostic_bundle`: opt-in support/material-request diagnostic bundle with redaction."""

    def record_event(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        scrubbed_payload, extra_redactions = SecretAndPiiScrubber.scrub(payload)
        total_redactions = int(context.get("redactions_applied", 0)) + extra_redactions

        target_endpoint = str(scrubbed_payload.get("target_endpoint", "/support"))
        if target_endpoint not in ("/support", "request_material"):
            target_endpoint = "/support"

        refusal_refs = [
            ref for ref in scrubbed_payload.get("refusal_references", ()) if valid_reference(ref)
        ]
        bundle = {
            "record_type": DIAGNOSTIC_BUNDLE_VERSION,
            "opt_in": True,
            "target_endpoint": target_endpoint,
            "note": str(scrubbed_payload.get("note", ""))[:500],
            "session_events": list(scrubbed_payload.get("session_events", ()))[:32],
            "refusal_references": refusal_refs,
            "redactions_applied": total_redactions,
        }
        bundle["bundle_digest"] = sha256_digest(bundle)
        return bundle


def create_frontend_trace_envelope(max_ring_events: int = 128) -> tuple[SevenLayerSlotEnvelope, dict[str, Any]]:
    """Build Slot Family A wrapped in the 7-layer envelope with preflight guards."""
    ring_engine = InTabSessionRingBufferEngine(max_events=max_ring_events)
    counter_engine = AggregateFunnelStepCounterEngine()
    diagnostic_engine = VoluntaryRedactedDiagnosticBundleEngine()

    def _check_zero_cookies_and_trackers(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = ctx.get("payload", {})
        if payload.get("cookies") or payload.get("third_party_script_url"):
            return build_refusal("cookie_or_third_party_tracker_forbidden")
        return None

    def _check_refusal_reference_shape(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = ctx.get("payload", {})
        if payload.get("event_kind") == "refusal_encountered":
            ref = payload.get("request_reference", "")
            if not valid_reference(ref):
                return build_refusal("invalid_refusal_reference")
        return None

    def _check_aggregate_no_raw_query(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = ctx.get("payload", {})
        req = ctx.get("request", {})
        preferred = req.get("preferred_engines", ())
        if "query" in payload and ("aggregate_funnel_step_counter" in preferred or payload.get("aggregate_only")):
            return build_refusal("raw_query_text_forbidden_in_aggregate_gap")
        return None

    def _check_voluntary_opt_in(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = ctx.get("payload", {})
        req = ctx.get("request", {})
        preferred = req.get("preferred_engines", ())
        if (
            "voluntary_redacted_diagnostic_bundle" in preferred
            or payload.get("event_kind") == "diagnostic_bundle"
        ):
            if payload.get("opt_in") is not True:
                return build_refusal("voluntary_opt_in_required")
        return None

    extra_checks = (
        EnvelopePreflightCheck(
            "zero_cookie_and_tracker_guard",
            ("cookie_or_third_party_tracker_forbidden",),
            _check_zero_cookies_and_trackers,
        ),
        EnvelopePreflightCheck(
            "issued_refusal_reference_guard",
            ("invalid_refusal_reference",),
            _check_refusal_reference_shape,
        ),
        EnvelopePreflightCheck(
            "aggregate_gap_no_raw_query_guard",
            ("raw_query_text_forbidden_in_aggregate_gap",),
            _check_aggregate_no_raw_query,
        ),
        EnvelopePreflightCheck(
            "voluntary_diagnostic_opt_in_guard",
            ("voluntary_opt_in_required",),
            _check_voluntary_opt_in,
        ),
    )

    specs = (
        EngineSpec(
            SLOT_FRONTEND_TRACE,
            "in_tab_session_ring_buffer",
            (FRONTEND_REQUEST_VERSION,),
            ("session_ring", "frustration_signals", "funnel_tracking"),
            (PURE_EFFECT,),
            ring_engine.record_event,
        ),
        EngineSpec(
            SLOT_FRONTEND_TRACE,
            "aggregate_funnel_step_counter",
            (FRONTEND_REQUEST_VERSION,),
            ("hourly_aggregate", "search_gap_v1", "funnel_tracking"),
            (PURE_EFFECT,),
            counter_engine.record_event,
        ),
        EngineSpec(
            SLOT_FRONTEND_TRACE,
            "voluntary_redacted_diagnostic_bundle",
            (FRONTEND_REQUEST_VERSION,),
            ("voluntary_diagnostic", "pii_redaction"),
            (PURE_EFFECT,),
            diagnostic_engine.record_event,
        ),
    )
    envelope = SevenLayerSlotEnvelope(SLOT_FRONTEND_TRACE, FRONTEND_OUTCOME_VERSION, specs)
    return envelope, {
        "ring": ring_engine,
        "counter": counter_engine,
        "diagnostic": diagnostic_engine,
        "extra_checks": extra_checks,
    }


# ---------------------------------------------------------------------------
# Slot Family B — Model & Harness Call `Local-to-Database` Trace Engines
# ---------------------------------------------------------------------------

def _normalize_trace_span(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a harness turn trace with LSH/Jev router decision, MCP spans, tokens, and acceptance."""
    usage = normalized_model_usage({
        "prompt_tokens": payload.get("prompt_tokens", 0),
        "eval_tokens": payload.get("eval_tokens", 0),
        "total_tokens": payload.get("total_tokens"),
    })
    router = payload.get("router_decision") if isinstance(payload.get("router_decision"), Mapping) else {}
    mcp_spans = []
    for span in payload.get("mcp_spans", ()):
        if isinstance(span, Mapping) and span.get("tool_name") in ("search", "inspect", "download"):
            mcp_spans.append({
                "tool_name": str(span["tool_name"]),
                "latency_ms": float(span.get("latency_ms", 0.0)),
                "status": str(span.get("status", "ok")),
                "selected_id": str(span.get("selected_id", "")),
                "hit_count": int(span.get("hit_count", 0)),
            })
    acceptance = payload.get("acceptance") if isinstance(payload.get("acceptance"), Mapping) else {}
    normalized = {
        "record_type": HARNESS_SPAN_VERSION,
        "run_id": str(payload.get("run_id", "run-default")),
        "turn_index": int(payload.get("turn_index", 1)),
        "harness_id": str(payload.get("harness_id", "opencode")),
        "loop_id": str(payload.get("loop_id", "loop-main")),
        "model": str(payload.get("model", "gemma4:31b")),
        "router_decision": {
            "route_selected": str(router.get("route_selected", "hybrid_lsh_lexical")),
            "lsh_bucket": str(router.get("lsh_bucket", "bucket_00")),
            "jev_score": float(router.get("jev_score", 0.0)),
            "candidates_considered": int(router.get("candidates_considered", 0)),
        },
        "mcp_spans": mcp_spans,
        "usage": usage,
        "latency_ms": float(payload.get("latency_ms", 0.0)),
        "acceptance": {
            "kept_in_worktree": bool(acceptance.get("kept_in_worktree", False)),
            "tests_passed": bool(acceptance.get("tests_passed", False)),
        },
    }
    normalized["trace_digest"] = sha256_digest(normalized)
    return normalized


class LocalSqliteWalTraceStoreEngine:
    """`local_sqlite_wal_trace_store`: durable SQLite WAL engine storing harness turns & acceptance."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._initialized = False

    def _ensure_schema(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=1.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        if not self._initialized:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS harness_traces (
                    trace_digest TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    harness_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    route_selected TEXT NOT NULL,
                    lsh_bucket TEXT NOT NULL,
                    prompt_tokens INTEGER,
                    eval_tokens INTEGER,
                    latency_ms REAL NOT NULL,
                    kept_in_worktree INTEGER NOT NULL,
                    tests_passed INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.commit()
            self._initialized = True
        return conn

    def write_trace(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_sqlite_locked") and not context.get("recovered_retry"):
            if payload.get("persistent_sqlite_lock"):
                raise EngineOperationalFailure("sqlite_locked", "database table is locked by another writer")
            raise EngineOperationalFailure("transient_lock_contended", "transient WAL lock contention")
        if payload.get("simulate_sqlite_locked") and payload.get("persistent_sqlite_lock"):
            raise EngineOperationalFailure("sqlite_locked", "database table is locked by another writer")

        span = _normalize_trace_span(payload)
        conn = self._ensure_schema()
        try:
            journal_mode = str(conn.execute("PRAGMA journal_mode;").fetchone()[0]).lower()
            conn.execute(
                """
                INSERT OR REPLACE INTO harness_traces (
                    trace_digest, run_id, turn_index, harness_id, model,
                    route_selected, lsh_bucket, prompt_tokens, eval_tokens,
                    latency_ms, kept_in_worktree, tests_passed, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    span["trace_digest"],
                    span["run_id"],
                    span["turn_index"],
                    span["harness_id"],
                    span["model"],
                    span["router_decision"]["route_selected"],
                    span["router_decision"]["lsh_bucket"],
                    span["usage"]["prompt_tokens"],
                    span["usage"]["eval_tokens"],
                    span["latency_ms"],
                    int(span["acceptance"]["kept_in_worktree"]),
                    int(span["acceptance"]["tests_passed"]),
                    canonical_json(span),
                ),
            )
            conn.commit()
            row_count = int(conn.execute("SELECT COUNT(*) FROM harness_traces").fetchone()[0])
        finally:
            conn.close()

        return {
            "record_type": HARNESS_SPAN_VERSION,
            "storage_backend": "sqlite_wal",
            "journal_mode": journal_mode,
            "trace_digest": span["trace_digest"],
            "stored_rows": row_count,
            "span": span,
        }

    def query_traces(self, *, run_id: str | None = None) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        conn = self._ensure_schema()
        try:
            if run_id:
                rows = conn.execute(
                    "SELECT payload_json FROM harness_traces WHERE run_id = ? ORDER BY turn_index ASC",
                    (run_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT payload_json FROM harness_traces ORDER BY run_id ASC, turn_index ASC"
                ).fetchall()
            return [json.loads(r[0]) for r in rows]
        finally:
            conn.close()


class LocalJsonlRingSpoolEngine:
    """`local_jsonl_ring_spool`: append-only bounded JSONL ring spool with SHA-256 chain digests."""

    def __init__(self, spool_path: str | Path, max_lines: int = 256):
        self.spool_path = Path(spool_path)
        self.max_lines = max_lines

    def write_trace(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_disk_readonly"):
            raise EngineOperationalFailure("disk_readonly", "JSONL spool directory is not writable")

        span = _normalize_trace_span(payload)
        self.spool_path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if self.spool_path.exists():
            existing = [
                json.loads(line)
                for line in self.spool_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if len(existing) >= self.max_lines:
            existing = existing[-(self.max_lines - 1):]
        prev_digest = existing[-1]["spool_entry_digest"] if existing else ""
        entry = {
            "sequence": (existing[-1]["sequence"] + 1) if existing else 1,
            "prev_digest": prev_digest,
            "trace_digest": span["trace_digest"],
            "span": span,
        }
        entry["spool_entry_digest"] = sha256_digest(entry)
        existing.append(entry)
        self.spool_path.write_text(
            "\n".join(canonical_json(item) for item in existing) + "\n",
            encoding="utf-8",
        )
        return {
            "record_type": HARNESS_SPAN_VERSION,
            "storage_backend": "jsonl_ring_spool",
            "trace_digest": span["trace_digest"],
            "spool_entry_digest": entry["spool_entry_digest"],
            "spooled_lines": len(existing),
            "span": span,
        }


class InMemoryEphemeralTraceBufferEngine:
    """`in_memory_ephemeral_trace_buffer`: zero-disk fallback when filesystem authority is off."""

    def __init__(self, max_entries: int = 128):
        self.max_entries = max_entries
        self.entries: deque[dict[str, Any]] = deque(maxlen=max_entries)

    def write_trace(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_ephemeral_disabled"):
            raise EngineOperationalFailure("ephemeral_disabled", "ephemeral trace buffer disabled")
        span = _normalize_trace_span(payload)
        self.entries.append(span)
        return {
            "record_type": HARNESS_SPAN_VERSION,
            "storage_backend": "in_memory_ephemeral",
            "trace_digest": span["trace_digest"],
            "buffered_entries": len(self.entries),
            "span": span,
        }


def create_local_trace_store_envelope(
    work_dir: str | Path,
) -> tuple[SevenLayerSlotEnvelope, dict[str, Any]]:
    """Build Slot Family B (`local_sqlite_wal_trace_store -> local_jsonl_ring_spool -> in_memory_ephemeral_trace_buffer`)."""
    root = Path(work_dir)
    sqlite_engine = LocalSqliteWalTraceStoreEngine(root / "traces.sqlite")
    jsonl_engine = LocalJsonlRingSpoolEngine(root / "traces_spool.jsonl")
    mem_engine = InMemoryEphemeralTraceBufferEngine()

    specs = (
        EngineSpec(
            SLOT_LOCAL_TRACE_STORE,
            "local_sqlite_wal_trace_store",
            (LOCAL_TRACE_REQUEST_VERSION,),
            ("durable_wal", "router_trace", "mcp_spans", "workspace_acceptance"),
            ("reads_fs", "writes_fs"),
            sqlite_engine.write_trace,
        ),
        EngineSpec(
            SLOT_LOCAL_TRACE_STORE,
            "local_jsonl_ring_spool",
            (LOCAL_TRACE_REQUEST_VERSION,),
            ("bounded_ring_spool", "router_trace", "mcp_spans", "workspace_acceptance"),
            ("reads_fs", "writes_fs"),
            jsonl_engine.write_trace,
        ),
        EngineSpec(
            SLOT_LOCAL_TRACE_STORE,
            "in_memory_ephemeral_trace_buffer",
            (LOCAL_TRACE_REQUEST_VERSION,),
            ("zero_disk_ephemeral", "router_trace", "mcp_spans", "workspace_acceptance"),
            (PURE_EFFECT,),
            mem_engine.write_trace,
        ),
    )
    envelope = SevenLayerSlotEnvelope(SLOT_LOCAL_TRACE_STORE, LOCAL_TRACE_OUTCOME_VERSION, specs)
    return envelope, {
        "sqlite": sqlite_engine,
        "jsonl": jsonl_engine,
        "memory": mem_engine,
    }


# ---------------------------------------------------------------------------
# Slot Family C — `Local-to-Cloud` & Cloud Function Sync Engines
# ---------------------------------------------------------------------------

class CloudBatchDigestExporterEngine:
    """`cloud_batch_digest_exporter`: batched, gzip-compressed, content-addressed idempotent sync engine."""

    def __init__(self) -> None:
        self.uploaded_batches: dict[str, dict[str, Any]] = {}
        self.known_trace_digests: set[str] = set()

    def sync_traces(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_network_unreachable") or payload.get("simulate_rate_limited"):
            raise EngineOperationalFailure("cloud_network_unavailable", "cloud batch endpoint unreachable or 429")
        if payload.get("simulate_origin_lock_contention"):
            raise EngineOperationalFailure("origin_lock_contended", "origin store busy; route to edge beacon")

        traces = list(payload.get("traces", ()))
        deduplicated: list[dict[str, Any]] = []
        skipped_duplicates = 0
        for item in traces:
            tdig = str(item.get("trace_digest") or sha256_digest(item))
            if tdig in self.known_trace_digests:
                skipped_duplicates += 1
            else:
                self.known_trace_digests.add(tdig)
                deduplicated.append({**dict(item), "trace_digest": tdig})

        raw_bytes = canonical_json(deduplicated).encode("utf-8")
        compressed_bytes = gzip.compress(raw_bytes, compresslevel=6)
        batch_digest = sha256_digest({
            "trace_digests": sorted(item["trace_digest"] for item in deduplicated),
            "tenant_id": context.get("account", {}).get("tenant_id", "tenant-default"),
        })

        record = {
            "record_type": CLOUD_BATCH_VERSION,
            "sync_mode": "cloud_batch_digest",
            "batch_digest": batch_digest,
            "submitted_traces": len(traces),
            "uploaded_new_traces": len(deduplicated),
            "deduplicated_skipped": skipped_duplicates,
            "uncompressed_bytes": len(raw_bytes),
            "compressed_bytes": len(compressed_bytes),
            "compression_ratio": round(len(compressed_bytes) / max(1, len(raw_bytes)), 4),
        }
        self.uploaded_batches[batch_digest] = record
        return record


class EdgeWorkerBeaconExporterEngine:
    """`edge_worker_beacon_exporter`: lightweight Cloudflare Worker / Edge function aggregate beacon."""

    def __init__(self) -> None:
        self.edge_lsh_misses: dict[str, int] = {}
        self.edge_funnel_counts: dict[str, int] = {}

    def sync_traces(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_network_unreachable"):
            raise EngineOperationalFailure("edge_network_unavailable", "edge worker unreachable while offline")

        traces = list(payload.get("traces", ()))
        for item in traces:
            router = item.get("router_decision") or {}
            bucket = str(router.get("lsh_bucket", "bucket_00"))
            spans = item.get("mcp_spans") or ()
            zero_hit = any(s.get("tool_name") == "search" and s.get("hit_count", 0) == 0 for s in spans)
            if zero_hit:
                self.edge_lsh_misses[bucket] = self.edge_lsh_misses.get(bucket, 0) + 1
            for s in spans:
                tool = str(s.get("tool_name", "search"))
                self.edge_funnel_counts[tool] = self.edge_funnel_counts.get(tool, 0) + 1

        beacon = {
            "record_type": EDGE_BEACON_VERSION,
            "sync_mode": "edge_worker_beacon",
            "origin_sqlite_locks_acquired": 0,
            "edge_lsh_misses": dict(sorted(self.edge_lsh_misses.items())),
            "edge_funnel_counts": dict(sorted(self.edge_funnel_counts.items())),
            "aggregated_traces": len(traces),
        }
        beacon["beacon_digest"] = sha256_digest(beacon)
        return beacon


class OfflineSpoolWithCircuitBreakerEngine:
    """`offline_spool_with_circuit_breaker`: offline spool with exponential backoff + jitter & idempotent replay."""

    def __init__(self, spool_file: str | Path):
        self.spool_file = Path(spool_file)
        self.rejected_attempts = 0
        self.last_rejected_digest = ""
        self.replayed_digests: set[str] = set()

    def _compute_backoff_seconds(self, attempt: int, digest_seed: str) -> float:
        base = min(60.0, 1.0 * (2 ** max(0, attempt - 1)))
        jitter_int = int(digest_seed[:8], 16) if digest_seed else 0
        jitter = (jitter_int % 250) / 1000.0
        return round(base + jitter, 3)

    def sync_traces(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        traces = list(payload.get("traces", ()))
        batch_digest = sha256_digest([item.get("trace_digest", sha256_digest(item)) for item in traces])
        self.rejected_attempts += 1
        self.last_rejected_digest = batch_digest

        observation = EnvelopeResyncObservation(
            desired=f"batch:{batch_digest[:16]}",
            observed="batch:offline_spooled",
            last_rejected=f"batch:{batch_digest[:16]}",
            rejected_attempts=self.rejected_attempts,
            seconds_since_last_attempt=float(payload.get("seconds_since_last_attempt", 0.2)),
        )
        backoff_policy = EnvelopeResyncBackoff(first_wait_seconds=1.0, longest_wait_seconds=60.0)
        decision = resync_decision(observation, backoff_policy)
        backoff_sec = self._compute_backoff_seconds(self.rejected_attempts, batch_digest)

        self.spool_file.parent.mkdir(parents=True, exist_ok=True)
        spooled: list[dict[str, Any]] = []
        if self.spool_file.exists():
            spooled = [
                json.loads(line)
                for line in self.spool_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if not any(row.get("batch_digest") == batch_digest for row in spooled):
            spooled.append({
                "batch_digest": batch_digest,
                "traces": traces,
                "attempt": self.rejected_attempts,
                "backoff_seconds": backoff_sec,
            })
            self.spool_file.write_text(
                "\n".join(canonical_json(row) for row in spooled) + "\n",
                encoding="utf-8",
            )

        return {
            "record_type": CLOUD_BATCH_VERSION,
            "sync_mode": "offline_spool_circuit_breaker",
            "circuit_state": "open",
            "resync_decision": decision,
            "backoff_seconds": backoff_sec,
            "batch_digest": batch_digest,
            "spooled_batches": len(spooled),
        }

    def replay_spooled(self, cloud_exporter: CloudBatchDigestExporterEngine) -> dict[str, Any]:
        """Replay spooled batches idempotently to `cloud_exporter` once network recovers."""
        if not self.spool_file.exists():
            return {"replayed_batches": 0, "skipped_already_replayed": 0}
        rows = [
            json.loads(line)
            for line in self.spool_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        replayed = 0
        skipped = 0
        for row in rows:
            b_dig = row["batch_digest"]
            if b_dig in self.replayed_digests:
                skipped += 1
                continue
            cloud_exporter.sync_traces({"payload": {"traces": row["traces"]}, "account": {"tenant_id": "replayed"}})
            self.replayed_digests.add(b_dig)
            replayed += 1
        self.rejected_attempts = 0
        return {
            "replayed_batches": replayed,
            "skipped_already_replayed": skipped,
            "circuit_state": "closed",
            "resync_decision": RESYNC_IN_SYNC,
        }


def create_cloud_trace_sync_envelope(
    work_dir: str | Path,
) -> tuple[SevenLayerSlotEnvelope, dict[str, Any]]:
    """Build Slot Family C (`cloud_batch_digest_exporter -> edge_worker_beacon_exporter -> offline_spool_with_circuit_breaker`)."""
    root = Path(work_dir)
    cloud_engine = CloudBatchDigestExporterEngine()
    edge_engine = EdgeWorkerBeaconExporterEngine()
    spool_engine = OfflineSpoolWithCircuitBreakerEngine(root / "cloud_offline_spool.jsonl")

    def _check_cloud_budget(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = ctx.get("payload", {})
        max_bytes = int(payload.get("max_batch_bytes", 1_000_000))
        traces = payload.get("traces", ())
        estimated = len(canonical_json(traces).encode("utf-8"))
        if estimated > max_bytes:
            return build_refusal("cloud_budget_exceeded", retry_after_seconds=10)
        return None

    extra_checks = (
        EnvelopePreflightCheck("cloud_sync_byte_budget_guard", ("cloud_budget_exceeded",), _check_cloud_budget),
    )

    specs = (
        EngineSpec(
            SLOT_CLOUD_TRACE_SYNC,
            "cloud_batch_digest_exporter",
            (CLOUD_SYNC_REQUEST_VERSION,),
            ("batch_digest_sync", "gzip_compression", "idempotent_dedup"),
            ("network",),
            cloud_engine.sync_traces,
        ),
        EngineSpec(
            SLOT_CLOUD_TRACE_SYNC,
            "edge_worker_beacon_exporter",
            (CLOUD_SYNC_REQUEST_VERSION,),
            ("edge_beacon", "zero_origin_lock"),
            ("network",),
            edge_engine.sync_traces,
        ),
        EngineSpec(
            SLOT_CLOUD_TRACE_SYNC,
            "offline_spool_with_circuit_breaker",
            (CLOUD_SYNC_REQUEST_VERSION,),
            ("offline_spool", "circuit_breaker", "idempotent_replay"),
            ("reads_fs", "writes_fs"),
            spool_engine.sync_traces,
        ),
    )
    envelope = SevenLayerSlotEnvelope(SLOT_CLOUD_TRACE_SYNC, CLOUD_SYNC_OUTCOME_VERSION, specs)
    return envelope, {
        "cloud": cloud_engine,
        "edge": edge_engine,
        "spool": spool_engine,
        "extra_checks": extra_checks,
    }


# ---------------------------------------------------------------------------
# Slot Family D — Closed-Loop Continuous Self-Improvement & Promotion Engines
# ---------------------------------------------------------------------------

class HeuristicGapClusterImproverEngine:
    """`heuristic_gap_cluster_improver`: deterministic clustering into `ranking_miss`, `alias_or_lsh_trigger_miss`, or `supply_gap`."""

    def improve(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_heuristic_unavailable"):
            raise EngineOperationalFailure("heuristic_unavailable", "heuristic clusterer delegated to synthesizer")

        signals = payload.get("signals", {})
        search_gaps = list(signals.get("search_gaps", ()))
        material_requests = list(signals.get("material_requests", ()))
        ratings = list(signals.get("catalogue_ratings", ()))
        failures = list(signals.get("service_failures", ()))
        harness_traces = list(signals.get("harness_traces", ()))

        proposals: list[dict[str, Any]] = []
        producer_id = str(payload.get("producer_id", "loop.self_improvement.heuristic_cluster"))

        # 1. Classify ranking_miss: item rated not_useful at rank 1 or harness rejected worktree after download
        negative_items = {
            r["item_identity"]
            for r in ratings
            if r.get("record_type") == RATING_SCHEMA and r.get("value") == "not_useful"
        }
        for trace in harness_traces:
            if not trace.get("acceptance", {}).get("tests_passed", True):
                for span in trace.get("mcp_spans", ()):
                    if span.get("tool_name") == "download" and span.get("selected_id"):
                        negative_items.add(span["selected_id"])

        for item_id in sorted(negative_items):
            proposals.append({
                "record_type": PROPOSAL_RECORD_VERSION,
                "proposal_id": f"prop-ranking-{sha256_digest(item_id)[:10]}",
                "classification": "ranking_miss",
                "target_item_id": item_id,
                "proposed_action": "demote_unaccepted_item_and_boost_verified_test_passing_variant",
                "producer_id": producer_id,
                "commit_status": "candidate_only",
                "active_intelligence_updated": False,
                "independent_review_required": True,
            })

        # 2. Classify alias_or_lsh_trigger_miss: search span had 0 hits, then retry in same run succeeded
        for trace in harness_traces:
            spans = trace.get("mcp_spans", ())
            had_zero = any(s.get("tool_name") == "search" and s.get("hit_count", 0) == 0 for s in spans)
            later_hit = any(s.get("tool_name") == "search" and s.get("hit_count", 0) > 0 for s in spans)
            if had_zero and later_hit:
                lsh_bucket = trace.get("router_decision", {}).get("lsh_bucket", "bucket_00")
                proposals.append({
                    "record_type": PROPOSAL_RECORD_VERSION,
                    "proposal_id": f"prop-alias-{sha256_digest(lsh_bucket + trace.get('run_id', ''))[:10]}",
                    "classification": "alias_or_lsh_trigger_miss",
                    "target_lsh_bucket": lsh_bucket,
                    "proposed_action": "expand_subtoken_alias_and_lsh_shingle_trigger",
                    "producer_id": producer_id,
                    "commit_status": "candidate_only",
                    "active_intelligence_updated": False,
                    "independent_review_required": True,
                })

        # 3. Classify supply_gap: repeated search_gap/v1 or explicit material_request/v1
        if search_gaps or material_requests:
            total_gap_searches = sum(int(g.get("searches", 1)) for g in search_gaps if g.get("record_type") == GAP_SCHEMA)
            open_requests = [
                req for req in material_requests if req.get("record_type") == REQUEST_SCHEMA and req.get("state") == "open"
            ]
            if total_gap_searches > 0 or open_requests:
                proposals.append({
                    "record_type": PROPOSAL_RECORD_VERSION,
                    "proposal_id": f"prop-supply-{sha256_digest({'gaps': total_gap_searches, 'reqs': len(open_requests)})[:10]}",
                    "classification": "supply_gap",
                    "gap_search_count": total_gap_searches,
                    "open_material_requests": len(open_requests),
                    "service_failure_refs": [
                        f.get("request_reference")
                        for f in failures
                        if f.get("record_type") == FAILURE_RECORD_VERSION
                    ],
                    "proposed_action": "queue_overnight_candidate_synthesis_for_missing_capability",
                    "producer_id": producer_id,
                    "commit_status": "candidate_only",
                    "active_intelligence_updated": False,
                    "independent_review_required": True,
                })

        return {
            "record_type": "heuristic_gap_cluster_report/v1",
            "stage": "diagnosis_and_candidate_generation",
            "producer_id": producer_id,
            "commit_status": "candidate_only",
            "active_intelligence_updated": False,
            "proposals": proposals,
            "proposal_count": len(proposals),
        }


class LshAliasAndQueryRelaxationSynthesizerEngine:
    """`lsh_alias_and_query_relaxation_synthesizer`: synthesizes sub-token aliases, synonyms, and LSH shingles."""

    @staticmethod
    def _subtokens(term: str) -> tuple[str, ...]:
        # Split CamelCase, snake_case, and kebab-case into normalized lower sub-tokens
        camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", term)
        camel_split = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", camel_split)
        parts = [p.lower() for p in re.split(r"[^A-Za-z0-9]+", camel_split) if p]
        return tuple(dict.fromkeys(parts))

    @staticmethod
    def _shingles(text: str, k: int = 3) -> tuple[str, ...]:
        cleaned = re.sub(r"\s+", " ", text.lower().strip())
        if len(cleaned) < k:
            return (cleaned,) if cleaned else ()
        return tuple(dict.fromkeys(cleaned[i : i + k] for i in range(len(cleaned) - k + 1)))

    def improve(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        if payload.get("simulate_synthesizer_unavailable"):
            raise EngineOperationalFailure("synthesizer_unavailable", "synthesizer delegated to verifier")

        retry_pairs = list(payload.get("retry_trace_pairs", ()))
        producer_id = str(payload.get("producer_id", "loop.self_improvement.lsh_alias_synthesizer"))
        synthesized_rules: list[dict[str, Any]] = []

        for pair in retry_pairs:
            failed_tokens = str(pair.get("failed_symbol_or_token", ""))
            succeeded_target = str(pair.get("succeeded_item_identity", ""))
            subtokens = self._subtokens(failed_tokens) + self._subtokens(succeeded_target)
            unique_subtokens = tuple(dict.fromkeys(subtokens))
            shingles = self._shingles(" ".join(unique_subtokens), k=3)
            rule = {
                "rule_id": f"alias-{sha256_digest({'f': failed_tokens, 's': succeeded_target})[:10]}",
                "source_token_pattern": failed_tokens,
                "target_item_identity": succeeded_target,
                "subtoken_aliases": list(unique_subtokens),
                "lsh_3gram_shingles": list(shingles[:16]),
                "query_relaxation": "drop_strict_punctuation_and_match_subtoken_prefix",
            }
            synthesized_rules.append(rule)

        return {
            "record_type": "lsh_alias_synthesis_bundle/v1",
            "stage": "diagnosis_and_candidate_generation",
            "producer_id": producer_id,
            "commit_status": "candidate_only",
            "active_intelligence_updated": False,
            "independent_review_required": True,
            "synthesized_rules": synthesized_rules,
            "rule_count": len(synthesized_rules),
        }


class HarmonyParetoVerifiedPromoterEngine:
    """`harmony_pareto_verified_promoter`: independent 4-objective Pareto verifier + canary promoter with rollback."""

    def improve(self, context: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(context["payload"])
        producer_id = str(payload.get("producer_id", ""))
        reviewer_id = str(payload.get("reviewer_id", ""))
        candidate = dict(payload.get("candidate_proposal", {}))
        baseline = dict(payload.get("baseline_metrics", {}))
        candidate_metrics = dict(payload.get("candidate_metrics", {}))
        canary_window = payload.get("canary_live_observation")

        # Evaluate 4 Pareto objectives:
        # 1. relevance_mrr_at_5 (higher is better)
        # 2. non_exact_query_recall (higher is better)
        # 3. latency_p95_ms (lower is better)
        # 4. token_cost_per_solve (lower is better)
        b_mrr = float(baseline.get("relevance_mrr_at_5", 0.65))
        c_mrr = float(candidate_metrics.get("relevance_mrr_at_5", b_mrr))

        b_recall = float(baseline.get("non_exact_query_recall", 0.55))
        c_recall = float(candidate_metrics.get("non_exact_query_recall", b_recall))

        b_lat = float(baseline.get("latency_p95_ms", 45.0))
        c_lat = float(candidate_metrics.get("latency_p95_ms", b_lat))

        b_tok = float(baseline.get("token_cost_per_solve", 1200.0))
        c_tok = float(candidate_metrics.get("token_cost_per_solve", b_tok))

        negative_transfer_failures = int(candidate_metrics.get("held_out_negative_transfer_regressions", 0))

        mrr_ok = c_mrr >= b_mrr
        recall_ok = c_recall >= b_recall
        lat_ok = c_lat <= b_lat
        tok_ok = c_tok <= b_tok
        strictly_better = (c_mrr > b_mrr) or (c_recall > b_recall) or (c_lat < b_lat) or (c_tok < b_tok)
        pareto_dominates = (
            mrr_ok
            and recall_ok
            and lat_ok
            and tok_ok
            and strictly_better
            and negative_transfer_failures == 0
        )

        deltas = {
            "relevance_mrr_at_5_delta": round(c_mrr - b_mrr, 4),
            "non_exact_query_recall_delta": round(c_recall - b_recall, 4),
            "latency_p95_ms_delta": round(c_lat - b_lat, 4),
            "token_cost_per_solve_delta": round(c_tok - b_tok, 2),
            "held_out_negative_transfer_regressions": negative_transfer_failures,
        }

        # Check live canary window for automatic rollback if already promoted to canary
        canary_rolled_back = False
        rollback_reason = ""
        promotion_state = "promoted_canary"
        if isinstance(canary_window, Mapping):
            live_acceptance = float(canary_window.get("live_acceptance_rate", 1.0))
            baseline_acceptance = float(canary_window.get("baseline_acceptance_rate", 0.8))
            live_refusal_rate = float(canary_window.get("live_refusal_rate", 0.0))
            live_p95_ms = float(canary_window.get("live_latency_p95_ms", c_lat))
            if (
                live_acceptance < baseline_acceptance - 0.02
                or live_refusal_rate > 0.05
                or live_p95_ms > b_lat * 1.15
            ):
                canary_rolled_back = True
                promotion_state = "rolled_back_to_baseline"
                rollback_reason = "live_canary_degradation_detected"

        return {
            "record_type": CANARY_PROMOTION_VERSION,
            "stage": "independent_pareto_verification_and_canary_promotion",
            "producer_id": producer_id,
            "reviewer_id": reviewer_id,
            "independent_review_verified": producer_id != reviewer_id and bool(producer_id) and bool(reviewer_id),
            "proposal_id": candidate.get("proposal_id", "prop-candidate"),
            "pareto_dominates": pareto_dominates,
            "objective_deltas": deltas,
            "promotion_state": promotion_state,
            "canary_rolled_back": canary_rolled_back,
            "rollback_reason": rollback_reason,
            "active_intelligence_updated": not canary_rolled_back,
        }


def create_self_improvement_envelope() -> tuple[SevenLayerSlotEnvelope, dict[str, Any]]:
    """Build Slot Family D with producer != reviewer independence guard and Pareto regression guard."""
    heuristic_engine = HeuristicGapClusterImproverEngine()
    synthesizer_engine = LshAliasAndQueryRelaxationSynthesizerEngine()
    promoter_engine = HarmonyParetoVerifiedPromoterEngine()

    def _check_independent_reviewer(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = ctx.get("payload", {})
        req = ctx.get("request", {})
        preferred = req.get("preferred_engines", ())
        if "harmony_pareto_verified_promoter" in preferred or payload.get("require_promotion_review"):
            producer_id = str(payload.get("producer_id", "")).strip()
            reviewer_id = str(payload.get("reviewer_id", "")).strip()
            if not producer_id or not reviewer_id or producer_id == reviewer_id:
                return build_refusal("self_approval_refused")
        return None

    def _check_pareto_non_regression(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        payload = ctx.get("payload", {})
        req = ctx.get("request", {})
        preferred = req.get("preferred_engines", ())
        if "harmony_pareto_verified_promoter" in preferred or payload.get("require_promotion_review"):
            baseline = payload.get("baseline_metrics", {})
            cand = payload.get("candidate_metrics", {})
            if baseline and cand:
                b_mrr = float(baseline.get("relevance_mrr_at_5", 0.65))
                c_mrr = float(cand.get("relevance_mrr_at_5", b_mrr))
                b_rec = float(baseline.get("non_exact_query_recall", 0.55))
                c_rec = float(cand.get("non_exact_query_recall", b_rec))
                b_lat = float(baseline.get("latency_p95_ms", 45.0))
                c_lat = float(cand.get("latency_p95_ms", b_lat))
                b_tok = float(baseline.get("token_cost_per_solve", 1200.0))
                c_tok = float(cand.get("token_cost_per_solve", b_tok))
                neg = int(cand.get("held_out_negative_transfer_regressions", 0))
                strictly_better = (c_mrr > b_mrr) or (c_rec > b_rec) or (c_lat < b_lat) or (c_tok < b_tok)
                if c_mrr < b_mrr or c_rec < b_rec or c_lat > b_lat or c_tok > b_tok or neg > 0 or not strictly_better:
                    return build_refusal("pareto_regression_refused")
        return None

    extra_checks = (
        EnvelopePreflightCheck(
            "independent_reviewer_separation_guard",
            ("self_approval_refused",),
            _check_independent_reviewer,
        ),
        EnvelopePreflightCheck(
            "pareto_zero_regression_guard",
            ("pareto_regression_refused",),
            _check_pareto_non_regression,
        ),
    )

    specs = (
        EngineSpec(
            SLOT_SELF_IMPROVEMENT,
            "heuristic_gap_cluster_improver",
            (SELF_IMPROVEMENT_REQUEST_VERSION,),
            ("gap_clustering", "candidate_generation"),
            (PURE_EFFECT,),
            heuristic_engine.improve,
        ),
        EngineSpec(
            SLOT_SELF_IMPROVEMENT,
            "lsh_alias_and_query_relaxation_synthesizer",
            (SELF_IMPROVEMENT_REQUEST_VERSION,),
            ("alias_synthesis", "lsh_shingle_expansion", "candidate_generation"),
            (PURE_EFFECT,),
            synthesizer_engine.improve,
        ),
        EngineSpec(
            SLOT_SELF_IMPROVEMENT,
            "harmony_pareto_verified_promoter",
            (SELF_IMPROVEMENT_REQUEST_VERSION,),
            ("independent_pareto_verifier", "canary_promotion", "automatic_rollback"),
            (PURE_EFFECT,),
            promoter_engine.improve,
        ),
    )
    envelope = SevenLayerSlotEnvelope(SLOT_SELF_IMPROVEMENT, SELF_IMPROVEMENT_OUTCOME_VERSION, specs)
    return envelope, {
        "heuristic": heuristic_engine,
        "synthesizer": synthesizer_engine,
        "promoter": promoter_engine,
        "extra_checks": extra_checks,
    }


# ---------------------------------------------------------------------------
# Head-to-Head Benchmark Runner Across All 4 Slot Families & Fallback Chains
# ---------------------------------------------------------------------------

def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(round((p / 100.0) * (len(sorted_values) - 1)))))
    return round(sorted_values[idx], 3)


def run_all_benchmarks(*, iterations: int = 40) -> dict[str, Any]:
    """Run deterministic head-to-head benchmarks across all 12 engines and fallback cascades."""
    temp_root = Path(tempfile.mkdtemp(prefix="trace_bench_"))
    ref_sample = new_request_reference().value

    # 1. Benchmark Slot Family A
    env_a, ctx_a = create_frontend_trace_envelope(max_ring_events=128)
    checks_a = ctx_a["extra_checks"]
    slot_a_metrics: dict[str, dict[str, Any]] = {}
    for engine_id, sample_payload in (
        (
            "in_tab_session_ring_buffer",
            {
                "event_kind": "funnel_step",
                "stage": "search",
                "mode": "lexical",
                "hit_count": 3,
                "latency_ms": 11.4,
            },
        ),
        (
            "aggregate_funnel_step_counter",
            {
                "stage": "search",
                "mode": "lexical",
                "hit_count": 0,
                "filters": {"category": {"equals": "creative_3d"}},
                "library_tiers": ["free"],
                "now_epoch": 1792191600.0,
            },
        ),
        (
            "voluntary_redacted_diagnostic_bundle",
            {
                "event_kind": "diagnostic_bundle",
                "opt_in": True,
                "target_endpoint": "/support",
                "note": "Connection check failed for user@example.com in /home/alice/project with baltor_secretkey12345",
                "refusal_references": [ref_sample],
            },
        ),
    ):
        latencies_us: list[float] = []
        last_outcome = None
        for i in range(iterations):
            t0 = time.perf_counter()
            last_outcome = env_a.execute(
                {
                    "record_type": FRONTEND_REQUEST_VERSION,
                    "preferred_engines": (engine_id,),
                    "secret_policy": "scrub" if engine_id == ENGINE_DIAGNOSTIC_BUNDLE else "refuse",
                    "payload": {**sample_payload, "seq": i},
                },
                extra_preflight_checks=checks_a,
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000.0)
        latencies_us.sort()
        assert last_outcome is not None and last_outcome.ok
        slot_a_metrics[engine_id] = {
            "iterations": iterations,
            "p50_us": _percentile(latencies_us, 50),
            "p95_us": _percentile(latencies_us, 95),
            "cookies_set": 0,
            "redactions_per_call": last_outcome.redactions_applied,
        }

    # 2. Benchmark Slot Family B
    env_b, ctx_b = create_local_trace_store_envelope(temp_root / "slot_b")
    slot_b_metrics: dict[str, dict[str, Any]] = {}
    for engine_id in (
        "local_sqlite_wal_trace_store",
        "local_jsonl_ring_spool",
        "in_memory_ephemeral_trace_buffer",
    ):
        latencies_us = []
        last_outcome = None
        for i in range(iterations):
            t0 = time.perf_counter()
            last_outcome = env_b.execute(
                {
                    "record_type": LOCAL_TRACE_REQUEST_VERSION,
                    "preferred_engines": (engine_id,),
                    "secret_policy": "scrub",
                    "payload": {
                        "run_id": "run-bench-01",
                        "turn_index": i + 1,
                        "harness_id": "opencode",
                        "model": "gemma4:31b",
                        "router_decision": {
                            "route_selected": "hybrid_lsh_lexical",
                            "lsh_bucket": f"bucket_{i % 8:02d}",
                            "jev_score": 0.87,
                            "candidates_considered": 12,
                        },
                        "mcp_spans": [
                            {"tool_name": "search", "latency_ms": 8.2, "status": "ok", "hit_count": 4},
                            {"tool_name": "download", "latency_ms": 14.1, "status": "ok", "selected_id": "item_tlru"},
                        ],
                        "prompt_tokens": 1420,
                        "eval_tokens": 310,
                        "latency_ms": 410.5,
                        "acceptance": {"kept_in_worktree": True, "tests_passed": True},
                    },
                }
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000.0)
        latencies_us.sort()
        assert last_outcome is not None and last_outcome.ok
        slot_b_metrics[engine_id] = {
            "iterations": iterations,
            "p50_us": _percentile(latencies_us, 50),
            "p95_us": _percentile(latencies_us, 95),
            "storage_backend": last_outcome.result["storage_backend"],
        }

    # 3. Benchmark Slot Family C
    env_c, ctx_c = create_cloud_trace_sync_envelope(temp_root / "slot_c")
    checks_c = ctx_c["extra_checks"]
    sample_traces = ctx_b["sqlite"].query_traces(run_id="run-bench-01")[:10]
    slot_c_metrics: dict[str, dict[str, Any]] = {}
    for engine_id in (
        "cloud_batch_digest_exporter",
        "edge_worker_beacon_exporter",
        "offline_spool_with_circuit_breaker",
    ):
        latencies_us = []
        last_outcome = None
        for i in range(iterations):
            t0 = time.perf_counter()
            last_outcome = env_c.execute(
                {
                    "record_type": CLOUD_SYNC_REQUEST_VERSION,
                    "preferred_engines": (engine_id,),
                    "account": {"tenant_id": "tenant_bench", "authorized": True},
                    "payload": {
                        "traces": sample_traces,
                        "batch_seq": i,
                    },
                },
                extra_preflight_checks=checks_c,
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000.0)
        latencies_us.sort()
        assert last_outcome is not None and last_outcome.ok
        slot_c_metrics[engine_id] = {
            "iterations": iterations,
            "p50_us": _percentile(latencies_us, 50),
            "p95_us": _percentile(latencies_us, 95),
            "sync_mode": last_outcome.result["sync_mode"],
            "compression_ratio": last_outcome.result.get("compression_ratio", 1.0),
        }

    # 4. Benchmark Slot Family D
    env_d, ctx_d = create_self_improvement_envelope()
    checks_d = ctx_d["extra_checks"]
    slot_d_metrics: dict[str, dict[str, Any]] = {}
    for engine_id, d_payload in (
        (
            "heuristic_gap_cluster_improver",
            {
                "producer_id": "loop.self_improvement.heuristic_cluster",
                "signals": {
                    "search_gaps": [
                        {
                            "record_type": GAP_SCHEMA,
                            "hour": "2026-10-16T22Z",
                            "mode": "lexical",
                            "filters": {},
                            "library_tiers": ["free"],
                            "hit_count": 0,
                            "searches": 9,
                        }
                    ],
                    "material_requests": [
                        {
                            "record_type": REQUEST_SCHEMA,
                            "tenant_id": "tenant_1",
                            "description": "Need WebGPU instanced grass shader with wind",
                            "state": "open",
                        }
                    ],
                    "catalogue_ratings": [
                        {
                            "record_type": RATING_SCHEMA,
                            "item_identity": "legacy_shader_v1",
                            "value": "not_useful",
                        }
                    ],
                    "service_failures": [
                        {
                            "record_type": FAILURE_RECORD_VERSION,
                            "request_reference": ref_sample,
                            "route": "/api/v1/provisioning",
                            "refusal_code": "rate_limit_exceeded",
                        }
                    ],
                    "harness_traces": [
                        {
                            "run_id": "run-gap-1",
                            "router_decision": {"lsh_bucket": "bucket_04"},
                            "mcp_spans": [
                                {"tool_name": "search", "hit_count": 0},
                                {"tool_name": "search", "hit_count": 3},
                            ],
                            "acceptance": {"kept_in_worktree": True, "tests_passed": True},
                        }
                    ],
                },
            },
        ),
        (
            "lsh_alias_and_query_relaxation_synthesizer",
            {
                "producer_id": "loop.self_improvement.lsh_alias_synthesizer",
                "retry_trace_pairs": [
                    {
                        "failed_symbol_or_token": "TLRUCache time to use",
                        "succeeded_item_identity": "cachetools_tlru_cache_reference",
                    },
                    {
                        "failed_symbol_or_token": "dotenv single quote backslash",
                        "succeeded_item_identity": "python_dotenv_single_quoted_parser",
                    },
                ],
            },
        ),
        (
            "harmony_pareto_verified_promoter",
            {
                "producer_id": "loop.self_improvement.lsh_alias_synthesizer",
                "reviewer_id": "loop.verifier.harmony_pareto_independent",
                "candidate_proposal": {"proposal_id": "prop-alias-tlru"},
                "baseline_metrics": {
                    "relevance_mrr_at_5": 0.640,
                    "non_exact_query_recall": 0.520,
                    "latency_p95_ms": 42.0,
                    "token_cost_per_solve": 1350.0,
                },
                "candidate_metrics": {
                    "relevance_mrr_at_5": 0.785,
                    "non_exact_query_recall": 0.810,
                    "latency_p95_ms": 39.5,
                    "token_cost_per_solve": 1080.0,
                    "held_out_negative_transfer_regressions": 0,
                },
            },
        ),
    ):
        latencies_us = []
        last_outcome = None
        for _ in range(iterations):
            t0 = time.perf_counter()
            last_outcome = env_d.execute(
                {
                    "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                    "preferred_engines": (engine_id,),
                    "payload": d_payload,
                },
                extra_preflight_checks=checks_d,
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000.0)
        latencies_us.sort()
        assert last_outcome is not None and last_outcome.ok
        slot_d_metrics[engine_id] = {
            "iterations": iterations,
            "p50_us": _percentile(latencies_us, 50),
            "p95_us": _percentile(latencies_us, 95),
            "stage": last_outcome.result["stage"],
        }

    # 5. Benchmark Automatic Fallback Cascades across all 4 slot families
    cascades: dict[str, dict[str, Any]] = {}

    # Cascade A: session ring disabled -> aggregate_funnel_step_counter
    casc_a = env_a.execute(
        {
            "record_type": FRONTEND_REQUEST_VERSION,
            "payload": {
                "simulate_session_storage_unavailable": True,
                "stage": "search",
                "mode": "lexical",
                "hit_count": 0,
                "now_epoch": 1792191600.0,
            },
        },
        extra_preflight_checks=checks_a,
    )
    cascades[SLOT_FRONTEND_TRACE] = {
        "tried": list(casc_a.fallback_chain_tried),
        "selected": casc_a.selected_engine,
        "ok": casc_a.ok,
    }

    # Cascade B: SQLite locked -> JSONL readonly -> in_memory_ephemeral_trace_buffer
    casc_b = env_b.execute(
        {
            "record_type": LOCAL_TRACE_REQUEST_VERSION,
            "payload": {
                "simulate_sqlite_locked": True,
                "persistent_sqlite_lock": True,
                "simulate_disk_readonly": True,
                "run_id": "run-cascade",
                "turn_index": 1,
            },
        }
    )
    cascades[SLOT_LOCAL_TRACE_STORE] = {
        "tried": list(casc_b.fallback_chain_tried),
        "selected": casc_b.selected_engine,
        "ok": casc_b.ok,
    }

    # Cascade C: Cloud network unreachable -> offline_spool_with_circuit_breaker
    casc_c = env_c.execute(
        {
            "record_type": CLOUD_SYNC_REQUEST_VERSION,
            "account": {"tenant_id": "tenant_casc", "authorized": True},
            "payload": {
                "simulate_network_unreachable": True,
                "traces": sample_traces[:2],
            },
        },
        extra_preflight_checks=checks_c,
    )
    cascades[SLOT_CLOUD_TRACE_SYNC] = {
        "tried": list(casc_c.fallback_chain_tried),
        "selected": casc_c.selected_engine,
        "ok": casc_c.ok,
    }

    # Cascade D: Heuristic clusterer delegated -> lsh_alias_and_query_relaxation_synthesizer
    casc_d = env_d.execute(
        {
            "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
            "payload": {
                "simulate_heuristic_unavailable": True,
                "producer_id": "loop.self_improvement.lsh_alias_synthesizer",
                "retry_trace_pairs": [
                    {
                        "failed_symbol_or_token": "TLRUCache",
                        "succeeded_item_identity": "cachetools_tlru",
                    }
                ],
            },
        },
        extra_preflight_checks=checks_d,
    )
    cascades[SLOT_SELF_IMPROVEMENT] = {
        "tried": list(casc_d.fallback_chain_tried),
        "selected": casc_d.selected_engine,
        "ok": casc_d.ok,
    }
    shutil.rmtree(temp_root, ignore_errors=True)

    return {
        "record_type": "trace_and_self_improvement_benchmarks/v1",
        "slots": {
            SLOT_FRONTEND_TRACE: slot_a_metrics,
            SLOT_LOCAL_TRACE_STORE: slot_b_metrics,
            SLOT_CLOUD_TRACE_SYNC: slot_c_metrics,
            SLOT_SELF_IMPROVEMENT: slot_d_metrics,
        },
        "fallback_cascades": cascades,
        "baseline_envelope_gap_closure": dict(BASELINE_ENVELOPE_GAP_CLOSURE),
    }


def self_test() -> dict[str, Any]:
    """Run deterministic self-tests including positive flows and known-wrong controls."""
    tests: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    benchmarks = run_all_benchmarks(iterations=10)
    check(
        "all_four_slot_families_and_twelve_engines_benchmarked",
        len(benchmarks["slots"]) == 4
        and all(len(v) == 3 for v in benchmarks["slots"].values())
        and all(c["ok"] for c in benchmarks["fallback_cascades"].values()),
        "12 engines across 4 slots + 4 fallback cascades verified",
    )

    # Known-wrong 1: Secret leakage refused before engine dispatch when secret_policy='refuse'
    temp_dir = Path(tempfile.mkdtemp(prefix="trace_selftest_"))
    try:
        env_b, _ = create_local_trace_store_envelope(temp_dir / "b")
        leak_outcome = env_b.execute(
            {
                "record_type": LOCAL_TRACE_REQUEST_VERSION,
                "secret_policy": "refuse",
                "payload": {
                    "run_id": "run-leak",
                    "turn_index": 1,
                    " leaked_token": "baltor_live_secret_token_987654321",
                },
            }
        )
        check(
            "known_wrong_secret_leakage_refused_at_preflight",
            not leak_outcome.ok
            and leak_outcome.trace["refused_by"] == LAYER_PREFLIGHT
            and not leak_outcome.trace["engine_dispatched"]
            and leak_outcome.refusal["code"] == "secret_or_pii_detected_in_trace",
            "raw baltor_ key refused at preflight before any local DB write",
        )

        # Known-wrong 2: Producer self-approval refused in Slot Family D
        env_d, ctx_d = create_self_improvement_envelope()
        self_approve = env_d.execute(
            {
                "record_type": SELF_IMPROVEMENT_REQUEST_VERSION,
                "preferred_engines": ("harmony_pareto_verified_promoter",),
                "payload": {
                    "producer_id": "loop.producer.same_agent",
                    "reviewer_id": "loop.producer.same_agent",
                    "baseline_metrics": {"relevance_mrr_at_5": 0.65},
                    "candidate_metrics": {"relevance_mrr_at_5": 0.75},
                },
            },
            extra_preflight_checks=ctx_d["extra_checks"],
        )
        check(
            "known_wrong_producer_self_approval_refused",
            not self_approve.ok
            and self_approve.refusal["code"] == "self_approval_refused"
            and not self_approve.trace["engine_dispatched"],
            "producer_id == reviewer_id refused before promotion engine runs",
        )

        # Known-wrong 3: Offline failover to spool and idempotent replay
        env_c, ctx_c = create_cloud_trace_sync_envelope(temp_dir / "c")
        offline_out = env_c.execute(
            {
                "record_type": CLOUD_SYNC_REQUEST_VERSION,
                "account": {"tenant_id": "tenant_offline", "authorized": True},
                "payload": {
                    "simulate_network_unreachable": True,
                    "traces": [{"trace_digest": "a" * 64, "run_id": "run-off"}],
                },
            },
            extra_preflight_checks=ctx_c["extra_checks"],
        )
        replay_stats_1 = ctx_c["spool"].replay_spooled(ctx_c["cloud"])
        replay_stats_2 = ctx_c["spool"].replay_spooled(ctx_c["cloud"])
        check(
            "offline_failover_and_idempotent_replay_verified",
            offline_out.ok
            and offline_out.selected_engine == "offline_spool_with_circuit_breaker"
            and replay_stats_1["replayed_batches"] == 1
            and replay_stats_2["replayed_batches"] == 0
            and replay_stats_2["skipped_already_replayed"] == 1,
            "offline circuit breaker spooled and replayed exactly once",
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    passed = sum(1 for t in tests if t["passed"])
    return {
        "record_type": "trace_and_self_improvement_self_test/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
        "benchmarks": benchmarks,
    }


if __name__ == "__main__":
    report = self_test()
    print(json.dumps(report, indent=2, sort_keys=True))
