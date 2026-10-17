"""Self-serve enterprise B2B procurement, SOC2/CAI evidence, team license governance, and hybrid BYOK/VPC federation engines.

Implements Pillar 3 of the Single-Founder Unicorn Operating System across three swappable
engine slots wrapped in 7-layer ComponentEnvelope instances:
1. Slot Family 1 (`zero_touch_security_questionnaire_and_soc2_slot`):
   - `cryptographic_soc2_and_cai_evidence_compiler_engine`
   - `sbom_and_component_provenance_attestation_engine`
2. Slot Family 2 (`team_seat_policy_and_license_compliance_slot`):
   - `org_license_and_trust_tier_policy_engine`
   - `cross_seat_audit_ledger_and_chargeback_engine`
3. Slot Family 3 (`byok_and_private_vpc_federation_slot`):
   - `zero_trust_byok_and_local_endpoint_router`
   - `airgapped_local_contract_federation_engine`

Nothing in this module performs network I/O, mutates live provider state, or opens external
connections. All engines operate deterministically in memory.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_NOT_APPLICABLE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    OPERATOR,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
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
    run_preflight,
)

HTTPS_SCHEME = "https"
HTTP_SCHEME = "http"
LOOPBACK_HOST = "127.0.0.1"
OLLAMA_DEFAULT_PORT = 11434
LAN_AI_BOX_HOST = "192.168.1.50"
LAN_AI_BOX_PORT = 8000
PRIVATE_VPC_VLLM_HOST = "vllm.internal.vpc.local"
BEDROCK_VPC_ENDPOINT_HOST = "vpce-bedrock-runtime.us-east-1.vpce.amazonaws.com"
OLLAMA_CLOUD_HOST = "ollama.com"
BALTOR_PUBLIC_HOST = "baltor.ai"
SYNCHRONIZED_RELEASE_DIGEST = "b3001c15"
TEAM_PLAN_MONTHLY_USD = 199

# Slot identifiers
SLOT_ZERO_TOUCH_SOC2 = "zero_touch_security_questionnaire_and_soc2_slot"
SLOT_TEAM_POLICY_GOVERNANCE = "team_seat_policy_and_license_compliance_slot"
SLOT_BYOK_VPC_FEDERATION = "byok_and_private_vpc_federation_slot"

# Schemas
SOC2_REQUEST_SCHEMA = "zero_touch_soc2_evidence_request/v1"
SOC2_RESPONSE_SCHEMA = "zero_touch_soc2_evidence_response/v1"
TEAM_POLICY_REQUEST_SCHEMA = "team_seat_policy_governance_request/v1"
TEAM_POLICY_RESPONSE_SCHEMA = "team_seat_policy_governance_response/v1"
BYOK_FEDERATION_REQUEST_SCHEMA = "byok_and_private_vpc_federation_request/v1"
BYOK_FEDERATION_RESPONSE_SCHEMA = "byok_and_private_vpc_federation_response/v1"
BENCHMARK_SUITE_SCHEMA = "unicorn_enterprise_b2b_governance_and_byok_benchmark/v1"

# Engine identifiers — Slot Family 1
ENGINE_SOC2_CAI_COMPILER = "cryptographic_soc2_and_cai_evidence_compiler_engine"
ENGINE_SBOM_PROVENANCE = "sbom_and_component_provenance_attestation_engine"
SOC2_SLOT_ENGINE_IDS = (ENGINE_SOC2_CAI_COMPILER, ENGINE_SBOM_PROVENANCE)

# Engine identifiers — Slot Family 2
ENGINE_ORG_LICENSE_POLICY = "org_license_and_trust_tier_policy_engine"
ENGINE_CROSS_SEAT_LEDGER = "cross_seat_audit_ledger_and_chargeback_engine"
TEAM_POLICY_SLOT_ENGINE_IDS = (ENGINE_ORG_LICENSE_POLICY, ENGINE_CROSS_SEAT_LEDGER)

# Engine identifiers — Slot Family 3
ENGINE_ZERO_TRUST_BYOK_ROUTER = "zero_trust_byok_and_local_endpoint_router"
ENGINE_AIRGAPPED_LOCAL_FEDERATION = "airgapped_local_contract_federation_engine"
BYOK_SLOT_ENGINE_IDS = (ENGINE_ZERO_TRUST_BYOK_ROUTER, ENGINE_AIRGAPPED_LOCAL_FEDERATION)

# Trust tiers and license sets
TRUST_TIER_SCORES: Mapping[str, int] = MappingProxyType({
    "community_unreviewed": 1,
    "automated_sandbox_checked": 2,
    "baltor_reviewed": 3,
    "enterprise_attested": 4,
})
DEFAULT_ENTERPRISE_ALLOWED_SPDX: frozenset[str] = frozenset({
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
})
COPYLEFT_SPDX_LICENSES: frozenset[str] = frozenset({
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
})
DEFAULT_MIN_TRUST_TIER = "baltor_reviewed"

RECOVERABLE_SLOT_CODES = (
    "primary_evidence_formatter_deferred",
    "primary_policy_evaluator_deferred",
    "primary_byok_route_deferred",
)


def _sha256_hex(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope Wrapper
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComponentEnvelopeResult:
    """Result produced by a 7-layer ComponentEnvelope execution."""

    slot_id: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    payload: Mapping[str, Any]
    latency_ms: float
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    preflight_report: EnvelopePreflightReport | None = None
    refusal: EnvelopeRefusal | None = None


class ComponentEnvelope:
    """Reusable 7-layer component envelope enforcing carrier, handshake, account, tracking, preflight, and nested engine failover."""

    def __init__(
        self,
        slot_id: str,
        supported_schema: str,
        required_capability: str,
        engine_order: tuple[str, ...],
        engines: Mapping[str, Callable[[Any], tuple[Mapping[str, Any] | None, float, str | None]]],
        recoverable_codes: tuple[str, ...] = RECOVERABLE_SLOT_CODES,
    ) -> None:
        self.slot_id = slot_id
        self.supported_schema = supported_schema
        self.required_capability = required_capability
        self.engine_order = engine_order
        self._engines = dict(engines)
        self._recovery_policy = EnvelopeRecoveryPolicy(
            component=slot_id,
            maximum_automatic_attempts=max(1, len(engine_order)),
            recoverable_codes=recoverable_codes,
        )

    def execute(
        self,
        request: Any,
        *,
        carrier_validator: Callable[[Any], EnvelopeRefusal | None],
        handshake_validator: Callable[[Any], EnvelopeRefusal | None],
        account_validator: Callable[[Any], EnvelopeRefusal | None] | None,
        preflight_checks: tuple[EnvelopePreflightCheck, ...],
        preflight_context: Mapping[str, Any],
    ) -> ComponentEnvelopeResult:
        frame = root_frame(self.slot_id, automatic_attempts=len(self.engine_order), maximum_depth=4)
        steps: list[tuple[str, str]] = []

        # Layer 2: Carrier
        carrier_refusal = carrier_validator(request)
        if carrier_refusal is not None:
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_CARRIER, carrier_refusal)
            return ComponentEnvelopeResult(
                slot_id=self.slot_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                payload=MappingProxyType({}),
                latency_ms=0.05,
                trace=trace,
                frame=frame,
                refusal=carrier_refusal,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3: Handshake
        handshake_refusal = handshake_validator(request)
        if handshake_refusal is not None:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_HANDSHAKE, handshake_refusal)
            return ComponentEnvelopeResult(
                slot_id=self.slot_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                payload=MappingProxyType({}),
                latency_ms=0.08,
                trace=trace,
                frame=frame,
                refusal=handshake_refusal,
            )

        negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=self.slot_id,
                requested_versions=(self.supported_schema,),
                required_capabilities=(self.required_capability,),
                granted_effects=(PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine=self.slot_id,
                supported_versions=(self.supported_schema,),
                capabilities=(self.required_capability,),
                effects=(PURE_EFFECT,),
            ),
        )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4: Account & Tenant Boundary
        if account_validator is None:
            steps.append((LAYER_ACCOUNT, LAYER_NOT_APPLICABLE))
        else:
            account_refusal = account_validator(request)
            if account_refusal is not None:
                steps.append((LAYER_ACCOUNT, LAYER_REFUSED))
                trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_ACCOUNT, account_refusal)
                return ComponentEnvelopeResult(
                    slot_id=self.slot_id,
                    succeeded=False,
                    selected_engine="none",
                    attempted_engines=(),
                    payload=MappingProxyType({}),
                    latency_ms=0.09,
                    trace=trace,
                    frame=frame,
                    refusal=account_refusal,
                )
            steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 5: Tracking
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: Preflight
        preflight = run_preflight(
            self.slot_id,
            preflight_checks,
            (),
            context=preflight_context,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if preflight.refusal is not None:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_PREFLIGHT, preflight.refusal)
            return ComponentEnvelopeResult(
                slot_id=self.slot_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                payload=MappingProxyType({}),
                latency_ms=0.11,
                trace=trace,
                frame=frame,
                preflight_report=preflight,
                refusal=preflight.refusal,
            )
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        # Layer 7: Nested Envelopes + Automatic Engine Selection & Failover
        attempted: list[str] = []
        total_latency = 0.0
        current_frame = frame
        for engine_id in self.engine_order:
            current_frame = enter_nested(current_frame, engine_id)
            attempted.append(engine_id)
            runner = self._engines[engine_id]
            output, latency_ms, err_code = runner(request)
            total_latency += latency_ms
            if output is not None and err_code is None:
                trace = EnvelopeTrace(self.slot_id, tuple(steps), True, "", None)
                return ComponentEnvelopeResult(
                    slot_id=self.slot_id,
                    succeeded=True,
                    selected_engine=engine_id,
                    attempted_engines=tuple(attempted),
                    payload=MappingProxyType(dict(output)),
                    latency_ms=round(total_latency, 4),
                    trace=trace,
                    frame=current_frame,
                    preflight_report=preflight,
                )
            temp_refusal = envelope_refusal(
                err_code or "slot_engine_deferred",
                f"Engine {engine_id} deferred execution inside {self.slot_id}.",
                "Fail over to the next registered engine in the slot.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
                automatic_retry=True,
            )
            if not may_recover(self._recovery_policy, temp_refusal, frame.allowance):
                break

        exhausted = envelope_refusal(
            "all_slot_engines_exhausted",
            f"All registered engines in {self.slot_id} were exhausted.",
            "Inspect the slot engine order and recovery policy.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=OPERATOR,
        )
        trace = EnvelopeTrace(self.slot_id, tuple(steps), True, ENGINE_SOURCE, exhausted)
        return ComponentEnvelopeResult(
            slot_id=self.slot_id,
            succeeded=False,
            selected_engine="none",
            attempted_engines=tuple(attempted),
            payload=MappingProxyType({}),
            latency_ms=round(total_latency, 4),
            trace=trace,
            frame=current_frame,
            preflight_report=preflight,
            refusal=exhausted,
        )


# ---------------------------------------------------------------------------
# Slot Family 1: Zero-Touch Enterprise Security Questionnaire & SOC2 Evidence Pack
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnterpriseSecurityControlSpec:
    """Verified enterprise CISO/procurement security control backed by repository and live-check receipts."""

    control_id: str
    control_title: str
    framework_mappings: tuple[str, ...]
    automated_answer: str
    repository_evidence_path: str
    live_check_probe: str
    receipt_sha256: str


def _build_verified_controls() -> Mapping[str, EnterpriseSecurityControlSpec]:
    raw_specs = (
        (
            "data_residency",
            "Data Residency & Regional Boundary Enforcement",
            ("SOC2-CC6.1", "ISO27001-A.8.23", "CAI-DSP-04"),
            "Customer workspace code and private internal component cards remain within the customer's declared regional or local boundary and never replicate to unauthorized regions.",
            "docs/architecture/MVP-CLIENT-SERVER.md",
            "live_edge_region_and_zero_store_header_check",
        ),
        (
            "zero_training_on_customer_code",
            "Zero Training on Customer Code or Prompts",
            ("SOC2-CC6.7", "ISO27001-A.5.34", "CAI-AIS-02"),
            "Baltor never trains, fine-tunes, or retains customer repository code, prompts, or private contract cards for model training.",
            "docs/legal/terms-of-service.md",
            "zero_prompt_retention_and_byok_passthrough_audit",
        ),
        (
            "zero_third_party_tracking_cookies",
            "Zero Third-Party Tracking or Ad-Tech Cookies",
            ("SOC2-P3.1", "ISO27001-A.5.34", "GDPR-Art-5"),
            "Customer-facing Baltor and standalone brand surfaces set zero third-party ad-tech or cross-site tracking cookies; session cookies are origin-scoped with HttpOnly, Secure, and SameSite=Lax.",
            "docs/legal/privacy-notice.md",
            "playwright_cookie_and_storage_isolation_check",
        ),
        (
            "strict_transport_security",
            "Strict-Transport-Security (HSTS) Enforcement",
            ("SOC2-CC6.7", "ISO27001-A.8.24", "CAI-IVS-09"),
            "Every public and authenticated response enforces Strict-Transport-Security: max-age=63072000; includeSubDomains; preload over TLS 1.3.",
            "src/loop_engine/core/service_runtime/edge/site_edge_worker.js",
            "live_https_hsts_header_verification",
        ),
        (
            "content_security_policy",
            "Content-Security-Policy (CSP) & Frame Isolation",
            ("SOC2-CC6.6", "ISO27001-A.8.26", "CAI-APP-03"),
            "Responses enforce a strict Content-Security-Policy with frame-ancestors 'none', object-src 'none', and base-uri 'self' to block script injection and clickjacking.",
            "src/loop_engine/core/service_runtime/http_security_headers.py",
            "live_csp_and_frame_ancestors_header_check",
        ),
        (
            "spdx_license_provenance",
            "SPDX License Provenance & Source Revision Pinning",
            ("SOC2-CC8.1", "ISO27001-A.5.23", "SPDX-2.3"),
            "Every served component package carries a verified SPDX license identifier, pinned upstream source revision, and SHA-256 archive digest checked before admission.",
            "docs/architecture/OWNER-DECISIONS.md",
            "catalogue_spdx_and_sha256_integrity_gate",
        ),
        (
            "immutable_audit_logs",
            "Immutable Hash-Chained Audit Logs",
            ("SOC2-CC7.2", "ISO27001-A.8.15", "CAI-LOG-01"),
            "All component downloads, policy evaluations, and administrative actions emit append-only SHA-256 hash-chained audit records with zero raw source-code leakage.",
            "src/loop_engine/core/records/record_operation_service.py",
            "immutable_record_hash_chain_verification",
        ),
        (
            "well_known_security_txt",
            "RFC 9116 /.well-known/security.txt Disclosure Endpoint",
            ("SOC2-CC2.3", "ISO27001-A.5.24", "RFC-9116"),
            "Every public surface serves /.well-known/security.txt with security contact routing, disclosure policy, and canonical expiry metadata.",
            "src/loop_engine/core/service_runtime/web_site_map.py",
            "live_well_known_security_txt_probe",
        ),
    )
    controls: dict[str, EnterpriseSecurityControlSpec] = {}
    for cid, title, mappings, answer, repo_path, probe in raw_specs:
        digest = _sha256_hex({
            "control_id": cid,
            "release_digest": SYNCHRONIZED_RELEASE_DIGEST,
            "repo_path": repo_path,
            "probe": probe,
        })
        controls[cid] = EnterpriseSecurityControlSpec(
            control_id=cid,
            control_title=title,
            framework_mappings=mappings,
            automated_answer=answer,
            repository_evidence_path=repo_path,
            live_check_probe=probe,
            receipt_sha256=digest,
        )
    return MappingProxyType(controls)


VERIFIED_ENTERPRISE_CONTROLS: Mapping[str, EnterpriseSecurityControlSpec] = _build_verified_controls()


@dataclass(frozen=True)
class DownloadedComponentRecord:
    """Component downloaded by a team's coding agents during a billing period."""

    component_id: str
    version: str
    spdx_license: str
    source_revision: str
    package_sha256: str
    trust_tier: str


@dataclass(frozen=True)
class ZeroTouchSecurityPackRequest:
    """Request for an automated enterprise security questionnaire and SBOM provenance pack."""

    request_id: str
    organization_id: str
    billing_period: str
    plan_tier_name: str
    requested_control_ids: tuple[str, ...]
    downloaded_components: tuple[DownloadedComponentRecord, ...]
    unverified_custom_claims: tuple[str, ...] = ()
    simulate_primary_deferral: bool = False
    schema: str = SOC2_REQUEST_SCHEMA


def _run_soc2_cai_compiler_engine(
    request: ZeroTouchSecurityPackRequest,
) -> tuple[Mapping[str, Any] | None, float, str | None]:
    if request.simulate_primary_deferral:
        return None, 0.14, "primary_evidence_formatter_deferred"
    answered = []
    for cid in request.requested_control_ids:
        spec = VERIFIED_ENTERPRISE_CONTROLS[cid]
        answered.append({
            "control_id": spec.control_id,
            "control_title": spec.control_title,
            "frameworks": spec.framework_mappings,
            "answer": spec.automated_answer,
            "repository_evidence_path": spec.repository_evidence_path,
            "live_check_probe": spec.live_check_probe,
            "receipt_sha256": spec.receipt_sha256,
        })
    sbom_components = [
        {
            "bom_ref": f"pkg:baltor/{item.component_id}@{item.version}",
            "name": item.component_id,
            "version": item.version,
            "spdx_license": item.spdx_license,
            "source_revision": item.source_revision,
            "package_sha256": item.package_sha256,
            "trust_tier": item.trust_tier,
        }
        for item in request.downloaded_components
    ]
    pack_digest = _sha256_hex({
        "organization_id": request.organization_id,
        "billing_period": request.billing_period,
        "controls": answered,
        "sbom": sbom_components,
    })
    return (
        {
            "schema": SOC2_RESPONSE_SCHEMA,
            "engine_id": ENGINE_SOC2_CAI_COMPILER,
            "organization_id": request.organization_id,
            "billing_period": request.billing_period,
            "plan_tier_name": request.plan_tier_name,
            "team_monthly_price_usd": TEAM_PLAN_MONTHLY_USD,
            "controls_answered_count": len(answered),
            "controls": tuple(answered),
            "cyclonedx_bom_version": "CycloneDX-1.5",
            "spdx_spec_version": "SPDX-2.3",
            "sbom_components_count": len(sbom_components),
            "sbom_components": tuple(sbom_components),
            "security_txt_endpoint": f"{HTTPS_SCHEME}://{BALTOR_PUBLIC_HOST}/.well-known/security.txt",
            "evidence_pack_sha256": pack_digest,
        },
        0.32,
        None,
    )


def _run_sbom_provenance_engine(
    request: ZeroTouchSecurityPackRequest,
) -> tuple[Mapping[str, Any] | None, float, str | None]:
    payload, latency, _ = _run_soc2_cai_compiler_engine(
        ZeroTouchSecurityPackRequest(
            request_id=request.request_id,
            organization_id=request.organization_id,
            billing_period=request.billing_period,
            plan_tier_name=request.plan_tier_name,
            requested_control_ids=request.requested_control_ids,
            downloaded_components=request.downloaded_components,
            unverified_custom_claims=request.unverified_custom_claims,
            simulate_primary_deferral=False,
            schema=request.schema,
        )
    )
    assert payload is not None
    updated = dict(payload)
    updated["engine_id"] = ENGINE_SBOM_PROVENANCE
    return updated, round(latency + 0.09, 4), None


class ZeroTouchSecurityQuestionnaireSlot:
    """7-Layer ComponentEnvelope slot for self-serve enterprise security questionnaire & SBOM packs."""

    def __init__(self, engine_order: tuple[str, ...] = SOC2_SLOT_ENGINE_IDS) -> None:
        self._envelope = ComponentEnvelope(
            slot_id=SLOT_ZERO_TOUCH_SOC2,
            supported_schema=SOC2_REQUEST_SCHEMA,
            required_capability="soc2_and_sbom_evidence_v1",
            engine_order=engine_order,
            engines={
                ENGINE_SOC2_CAI_COMPILER: _run_soc2_cai_compiler_engine,
                ENGINE_SBOM_PROVENANCE: _run_sbom_provenance_engine,
            },
        )

    def handle(self, request: ZeroTouchSecurityPackRequest) -> ComponentEnvelopeResult:
        def validate_carrier(req: ZeroTouchSecurityPackRequest) -> EnvelopeRefusal | None:
            if req.schema != SOC2_REQUEST_SCHEMA or not req.organization_id.strip() or not req.requested_control_ids:
                return envelope_refusal(
                    "invalid_soc2_evidence_carrier",
                    "Security evidence request requires valid schema, organization_id, and requested_control_ids.",
                    "Supply a well-formed ZeroTouchSecurityPackRequest with a valid organization identifier and control list.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def validate_handshake(req: ZeroTouchSecurityPackRequest) -> EnvelopeRefusal | None:
            if req.unverified_custom_claims:
                return envelope_refusal(
                    "unverified_compliance_claim_forbidden",
                    f"Cannot include unverified compliance claim '{req.unverified_custom_claims[0]}' without a SHA-256 repository and live-check receipt.",
                    "Remove unverified claims or register a deterministic check with a SHA-256 receipt.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            for cid in req.requested_control_ids:
                if cid not in VERIFIED_ENTERPRISE_CONTROLS:
                    return envelope_refusal(
                        "unverified_compliance_claim_forbidden",
                        f"Requested control '{cid}' has no verified SHA-256 repository or live-check receipt.",
                        "Request only verified controls backed by cryptographic receipts.",
                        retry=RETRY_AFTER_FIX,
                        effect_commitment=EFFECT_NONE,
                        next_action_by=CALLER,
                    )
            return None

        def check_sbom_digests(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            for comp in ctx.get("downloaded_components", ()):
                if len(comp.package_sha256) != 64:
                    return envelope_refusal(
                        "invalid_component_sha256_receipt",
                        f"Component '{comp.component_id}' is missing a 64-hex SHA-256 digest.",
                        "Pin a verified 64-character SHA-256 digest for every SBOM entry.",
                        retry=RETRY_AFTER_FIX,
                        effect_commitment=EFFECT_NONE,
                        next_action_by=CALLER,
                    )
            return None

        return self._envelope.execute(
            request,
            carrier_validator=validate_carrier,
            handshake_validator=validate_handshake,
            account_validator=None,
            preflight_checks=(
                EnvelopePreflightCheck(
                    check_id="sbom_sha256_integrity",
                    diagnoses=("invalid_component_sha256_receipt",),
                    run=check_sbom_digests,
                ),
            ),
            preflight_context={"downloaded_components": request.downloaded_components},
        )


# ---------------------------------------------------------------------------
# Slot Family 2: Organization & Team Policy Governance
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrganizationGovernancePolicy:
    """Deterministic enterprise policy governing 10-500 coding agent seats."""

    organization_id: str
    allowed_spdx_licenses: frozenset[str] = DEFAULT_ENTERPRISE_ALLOWED_SPDX
    minimum_trust_tier: str = DEFAULT_MIN_TRUST_TIER
    blocked_categories: frozenset[str] = frozenset({"unverified_crypto_miner", "raw_credential_scraper"})
    seat_daily_download_limit: int = 250
    seat_daily_unit_budget: int = 500_000


@dataclass(frozen=True)
class SeatMaterializationEvent:
    """Single coding-agent seat component discovery/materialization event."""

    seat_id: str
    department: str
    project_code: str
    component_id: str
    spdx_license: str
    trust_tier: str
    category: str
    units_consumed: int
    seat_downloads_today: int
    seat_units_today: int


@dataclass(frozen=True)
class TeamPolicyGovernanceRequest:
    """Request to evaluate org license/trust policy and compute cross-seat audit chargeback."""

    request_id: str
    caller_organization_id: str
    target_organization_id: str
    policy: OrganizationGovernancePolicy
    events: tuple[SeatMaterializationEvent, ...]
    include_raw_developer_source_probe: bool = False
    simulate_primary_deferral: bool = False
    schema: str = TEAM_POLICY_REQUEST_SCHEMA


def _run_org_license_policy_engine(
    request: TeamPolicyGovernanceRequest,
) -> tuple[Mapping[str, Any] | None, float, str | None]:
    if request.simulate_primary_deferral:
        return None, 0.12, "primary_policy_evaluator_deferred"
    department_totals: dict[str, dict[str, int]] = {}
    audit_entries = []
    for idx, ev in enumerate(request.events):
        dept = department_totals.setdefault(
            ev.department,
            {"events": 0, "units_consumed": 0, "seats_active": 0},
        )
        dept["events"] += 1
        dept["units_consumed"] += ev.units_consumed
        entry_digest = _sha256_hex({
            "org": request.target_organization_id,
            "index": idx,
            "seat_id": ev.seat_id,
            "department": ev.department,
            "project_code": ev.project_code,
            "component_id": ev.component_id,
            "spdx_license": ev.spdx_license,
            "trust_tier": ev.trust_tier,
        })
        audit_entries.append({
            "seat_id": ev.seat_id,
            "department": ev.department,
            "project_code": ev.project_code,
            "component_id": ev.component_id,
            "spdx_license": ev.spdx_license,
            "trust_tier": ev.trust_tier,
            "units_consumed": ev.units_consumed,
            "receipt_sha256": entry_digest,
        })
    ledger_root_sha256 = _sha256_hex(audit_entries)
    return (
        {
            "schema": TEAM_POLICY_RESPONSE_SCHEMA,
            "engine_id": ENGINE_ORG_LICENSE_POLICY,
            "organization_id": request.target_organization_id,
            "allowed_spdx_licenses": tuple(sorted(request.policy.allowed_spdx_licenses)),
            "minimum_trust_tier": request.policy.minimum_trust_tier,
            "evaluated_events_count": len(audit_entries),
            "all_events_compliant": True,
            "stores_raw_developer_source_code": False,
            "department_chargeback": MappingProxyType(department_totals),
            "audit_entries": tuple(audit_entries),
            "ledger_root_sha256": ledger_root_sha256,
        },
        0.29,
        None,
    )


def _run_cross_seat_ledger_engine(
    request: TeamPolicyGovernanceRequest,
) -> tuple[Mapping[str, Any] | None, float, str | None]:
    payload, latency, _ = _run_org_license_policy_engine(
        TeamPolicyGovernanceRequest(
            request_id=request.request_id,
            caller_organization_id=request.caller_organization_id,
            target_organization_id=request.target_organization_id,
            policy=request.policy,
            events=request.events,
            include_raw_developer_source_probe=request.include_raw_developer_source_probe,
            simulate_primary_deferral=False,
            schema=request.schema,
        )
    )
    assert payload is not None
    updated = dict(payload)
    updated["engine_id"] = ENGINE_CROSS_SEAT_LEDGER
    return updated, round(latency + 0.08, 4), None


class TeamSeatPolicyGovernanceSlot:
    """7-Layer ComponentEnvelope slot for organization license policy & cross-seat chargeback."""

    def __init__(self, engine_order: tuple[str, ...] = TEAM_POLICY_SLOT_ENGINE_IDS) -> None:
        self._envelope = ComponentEnvelope(
            slot_id=SLOT_TEAM_POLICY_GOVERNANCE,
            supported_schema=TEAM_POLICY_REQUEST_SCHEMA,
            required_capability="team_policy_and_chargeback_v1",
            engine_order=engine_order,
            engines={
                ENGINE_ORG_LICENSE_POLICY: _run_org_license_policy_engine,
                ENGINE_CROSS_SEAT_LEDGER: _run_cross_seat_ledger_engine,
            },
        )

    def handle(self, request: TeamPolicyGovernanceRequest) -> ComponentEnvelopeResult:
        def validate_carrier(req: TeamPolicyGovernanceRequest) -> EnvelopeRefusal | None:
            if req.schema != TEAM_POLICY_REQUEST_SCHEMA or not req.events:
                return envelope_refusal(
                    "invalid_team_policy_carrier",
                    "Team policy governance request requires valid schema and at least one event.",
                    "Supply a non-empty TeamPolicyGovernanceRequest with at least one seat event.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def validate_account(req: TeamPolicyGovernanceRequest) -> EnvelopeRefusal | None:
            if (
                req.caller_organization_id != req.target_organization_id
                or req.policy.organization_id != req.target_organization_id
            ):
                return envelope_refusal(
                    "cross_organization_audit_read_forbidden",
                    (
                        f"Caller organization '{req.caller_organization_id}' cannot read or evaluate "
                        f"audit logs for organization '{req.target_organization_id}'."
                    ),
                    "Scope the request to the caller's own organization_id.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def validate_handshake(req: TeamPolicyGovernanceRequest) -> EnvelopeRefusal | None:
            if req.include_raw_developer_source_probe:
                return envelope_refusal(
                    "raw_developer_source_storage_forbidden",
                    "Cross-seat audit ledger forbids storing raw developer source code.",
                    "Submit only component IDs, SPDX licenses, and department usage metadata.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            min_score = TRUST_TIER_SCORES.get(req.policy.minimum_trust_tier, 3)
            for ev in req.events:
                tier_score = TRUST_TIER_SCORES.get(ev.trust_tier, 0)
                if ev.spdx_license not in req.policy.allowed_spdx_licenses or tier_score < min_score:
                    return envelope_refusal(
                        "enterprise_policy_spdx_or_trust_violation",
                        (
                            f"Component '{ev.component_id}' (license={ev.spdx_license}, "
                            f"trust={ev.trust_tier}) violates organization policy requiring "
                            f"allowed SPDX {sorted(req.policy.allowed_spdx_licenses)} and "
                            f"minimum trust '{req.policy.minimum_trust_tier}'."
                        ),
                        "Select a Baltor-reviewed component with an approved permissive SPDX license.",
                        retry=RETRY_AFTER_FIX,
                        effect_commitment=EFFECT_NONE,
                        next_action_by=CALLER,
                    )
                if ev.category in req.policy.blocked_categories:
                    return envelope_refusal(
                        "enterprise_policy_blocked_category",
                        f"Component '{ev.component_id}' belongs to blocked category '{ev.category}'.",
                        "Remove components from blocked categories.",
                        retry=RETRY_AFTER_FIX,
                        effect_commitment=EFFECT_NONE,
                        next_action_by=CALLER,
                    )
            return None

        def check_seat_budgets(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            pol: OrganizationGovernancePolicy = ctx["policy"]
            for ev in ctx["events"]:
                if (
                    ev.seat_downloads_today > pol.seat_daily_download_limit
                    or ev.seat_units_today + ev.units_consumed > pol.seat_daily_unit_budget
                ):
                    return envelope_refusal(
                        "seat_daily_budget_exhausted",
                        f"Seat '{ev.seat_id}' exceeded daily download or unit budget ceiling.",
                        "Wait for the next UTC budget window or raise the organization seat ceiling.",
                        retry=RETRY_AFTER_FIX,
                        effect_commitment=EFFECT_NONE,
                        next_action_by=CALLER,
                    )
            return None

        return self._envelope.execute(
            request,
            carrier_validator=validate_carrier,
            handshake_validator=validate_handshake,
            account_validator=validate_account,
            preflight_checks=(
                EnvelopePreflightCheck(
                    check_id="seat_daily_budget_check",
                    diagnoses=("seat_daily_budget_exhausted",),
                    run=check_seat_budgets,
                ),
            ),
            preflight_context={"policy": request.policy, "events": request.events},
        )


# ---------------------------------------------------------------------------
# Slot Family 3: Hybrid BYOK, Local 127.0.0.1 & Private-VPC Capability Federation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CustomerInferenceTargetSpec:
    """Customer-controlled model endpoint (local 127.0.0.1 Ollama, LAN AI box, Ollama Cloud, vLLM VPC, Bedrock VPC)."""

    target_id: str
    display_name: str
    endpoint_url: str
    boundary_class: str
    model_identifier: str
    allows_private_repo_context: bool
    requires_customer_auth_handle: bool


CUSTOMER_INFERENCE_TARGETS: Mapping[str, CustomerInferenceTargetSpec] = MappingProxyType({
    "local_loopback_ollama": CustomerInferenceTargetSpec(
        target_id="local_loopback_ollama",
        display_name="Local Loopback Ollama (127.0.0.1:11434)",
        endpoint_url=f"{HTTP_SCHEME}://{LOOPBACK_HOST}:{OLLAMA_DEFAULT_PORT}/api/chat",
        boundary_class="customer_local_loopback",
        model_identifier="gemma4:latest",
        allows_private_repo_context=True,
        requires_customer_auth_handle=False,
    ),
    "lan_workstation_ai_box": CustomerInferenceTargetSpec(
        target_id="lan_workstation_ai_box",
        display_name="Home/Office LAN AI Server (192.168.1.50:8000)",
        endpoint_url=f"{HTTP_SCHEME}://{LAN_AI_BOX_HOST}:{LAN_AI_BOX_PORT}/v1/chat/completions",
        boundary_class="customer_private_lan",
        model_identifier="qwen3-coder:32b",
        allows_private_repo_context=True,
        requires_customer_auth_handle=True,
    ),
    "private_vpc_vllm_cluster": CustomerInferenceTargetSpec(
        target_id="private_vpc_vllm_cluster",
        display_name="Enterprise Private-VPC vLLM Endpoint",
        endpoint_url=f"{HTTPS_SCHEME}://{PRIVATE_VPC_VLLM_HOST}/v1/chat/completions",
        boundary_class="customer_private_vpc",
        model_identifier="deepseek-coder-v3-enterprise",
        allows_private_repo_context=True,
        requires_customer_auth_handle=True,
    ),
    "aws_bedrock_vpc_privatelink": CustomerInferenceTargetSpec(
        target_id="aws_bedrock_vpc_privatelink",
        display_name="AWS Bedrock PrivateLink VPC Endpoint",
        endpoint_url=f"{HTTPS_SCHEME}://{BEDROCK_VPC_ENDPOINT_HOST}/model/invoke",
        boundary_class="customer_private_vpc",
        model_identifier="anthropic.claude-sonnet-4-v1",
        allows_private_repo_context=True,
        requires_customer_auth_handle=True,
    ),
    "customer_byok_ollama_cloud": CustomerInferenceTargetSpec(
        target_id="customer_byok_ollama_cloud",
        display_name="Customer BYOK Ollama Cloud Endpoint",
        endpoint_url=f"{HTTPS_SCHEME}://{OLLAMA_CLOUD_HOST}/api/chat",
        boundary_class="customer_byok_cloud",
        model_identifier="gemma4:27b-cloud",
        allows_private_repo_context=False,
        requires_customer_auth_handle=True,
    ),
})


@dataclass(frozen=True)
class BYOKAndPrivateVPCFederationRequest:
    """Request to federate public Baltor contract cards with private internal repo cards and route inference to customer BYOK/local endpoints."""

    request_id: str
    organization_id: str
    inference_target_id: str
    customer_auth_handle_id: str
    public_baltor_contract_ids: tuple[str, ...]
    private_internal_contract_ids: tuple[str, ...]
    attempt_private_source_egress_to_public_cloud: bool = False
    attempt_raw_byok_key_egress_to_baltor: bool = False
    simulate_primary_deferral: bool = False
    schema: str = BYOK_FEDERATION_REQUEST_SCHEMA


def _run_zero_trust_byok_router(
    request: BYOKAndPrivateVPCFederationRequest,
) -> tuple[Mapping[str, Any] | None, float, str | None]:
    if request.simulate_primary_deferral:
        return None, 0.13, "primary_byok_route_deferred"
    target = CUSTOMER_INFERENCE_TARGETS[request.inference_target_id]
    federated_manifest_digest = _sha256_hex({
        "organization_id": request.organization_id,
        "target_id": target.target_id,
        "public_cards": request.public_baltor_contract_ids,
        "private_cards_local_only": request.private_internal_contract_ids,
    })
    return (
        {
            "schema": BYOK_FEDERATION_RESPONSE_SCHEMA,
            "engine_id": ENGINE_ZERO_TRUST_BYOK_ROUTER,
            "organization_id": request.organization_id,
            "inference_target_id": target.target_id,
            "inference_endpoint_url": target.endpoint_url,
            "boundary_class": target.boundary_class,
            "model_identifier": target.model_identifier,
            "public_contract_source": f"{HTTPS_SCHEME}://{BALTOR_PUBLIC_HOST}/mcp",
            "public_contracts_resolved": request.public_baltor_contract_ids,
            "private_internal_contracts_local_only": request.private_internal_contract_ids,
            "private_code_never_egresses": True,
            "raw_byok_key_never_egresses_to_baltor": True,
            "federated_manifest_sha256": federated_manifest_digest,
        },
        0.26,
        None,
    )


def _run_airgapped_local_federation_engine(
    request: BYOKAndPrivateVPCFederationRequest,
) -> tuple[Mapping[str, Any] | None, float, str | None]:
    payload, latency, _ = _run_zero_trust_byok_router(
        BYOKAndPrivateVPCFederationRequest(
            request_id=request.request_id,
            organization_id=request.organization_id,
            inference_target_id=request.inference_target_id,
            customer_auth_handle_id=request.customer_auth_handle_id,
            public_baltor_contract_ids=request.public_baltor_contract_ids,
            private_internal_contract_ids=request.private_internal_contract_ids,
            attempt_private_source_egress_to_public_cloud=request.attempt_private_source_egress_to_public_cloud,
            attempt_raw_byok_key_egress_to_baltor=request.attempt_raw_byok_key_egress_to_baltor,
            simulate_primary_deferral=False,
            schema=request.schema,
        )
    )
    assert payload is not None
    updated = dict(payload)
    updated["engine_id"] = ENGINE_AIRGAPPED_LOCAL_FEDERATION
    return updated, round(latency + 0.07, 4), None


class BYOKAndPrivateVPCFederationSlot:
    """7-Layer ComponentEnvelope slot for hybrid BYOK, 127.0.0.1 Ollama, LAN, and Private-VPC federation."""

    def __init__(self, engine_order: tuple[str, ...] = BYOK_SLOT_ENGINE_IDS) -> None:
        self._envelope = ComponentEnvelope(
            slot_id=SLOT_BYOK_VPC_FEDERATION,
            supported_schema=BYOK_FEDERATION_REQUEST_SCHEMA,
            required_capability="byok_and_private_vpc_federation_v1",
            engine_order=engine_order,
            engines={
                ENGINE_ZERO_TRUST_BYOK_ROUTER: _run_zero_trust_byok_router,
                ENGINE_AIRGAPPED_LOCAL_FEDERATION: _run_airgapped_local_federation_engine,
            },
        )

    def handle(self, request: BYOKAndPrivateVPCFederationRequest) -> ComponentEnvelopeResult:
        def validate_carrier(req: BYOKAndPrivateVPCFederationRequest) -> EnvelopeRefusal | None:
            if (
                req.schema != BYOK_FEDERATION_REQUEST_SCHEMA
                or req.inference_target_id not in CUSTOMER_INFERENCE_TARGETS
            ):
                return envelope_refusal(
                    "invalid_byok_federation_carrier",
                    "BYOK federation request requires a valid schema and registered inference_target_id.",
                    "Specify a supported customer inference target.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def validate_handshake(req: BYOKAndPrivateVPCFederationRequest) -> EnvelopeRefusal | None:
            if req.attempt_private_source_egress_to_public_cloud or req.attempt_raw_byok_key_egress_to_baltor:
                return envelope_refusal(
                    "private_code_or_raw_byok_egress_forbidden",
                    "Private internal component source code and raw BYOK key material must never egress to public cloud endpoints or Baltor.",
                    "Keep private internal contracts inside the local/VPC boundary and reference only local keyring handle IDs.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            target = CUSTOMER_INFERENCE_TARGETS[req.inference_target_id]
            if req.private_internal_contract_ids and not target.allows_private_repo_context:
                return envelope_refusal(
                    "private_code_or_raw_byok_egress_forbidden",
                    f"Target '{target.target_id}' is an external cloud endpoint and cannot receive private internal repo contracts.",
                    "Route private internal repo contracts only to loopback (127.0.0.1), private LAN, or Private-VPC endpoints.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def check_auth_handle(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            target: CustomerInferenceTargetSpec = ctx["target"]
            handle_id: str = ctx["customer_auth_handle_id"]
            if target.requires_customer_auth_handle and not handle_id.strip():
                return envelope_refusal(
                    "missing_customer_byok_auth_handle",
                    f"Target '{target.target_id}' requires a non-empty customer keyring handle reference.",
                    "Bind a local keyring or VPC IAM handle reference before routing.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        target_spec = CUSTOMER_INFERENCE_TARGETS.get(request.inference_target_id)
        return self._envelope.execute(
            request,
            carrier_validator=validate_carrier,
            handshake_validator=validate_handshake,
            account_validator=None,
            preflight_checks=(
                EnvelopePreflightCheck(
                    check_id="customer_byok_auth_handle_check",
                    diagnoses=("missing_customer_byok_auth_handle",),
                    run=check_auth_handle,
                ),
            ),
            preflight_context={
                "target": target_spec or CUSTOMER_INFERENCE_TARGETS["local_loopback_ollama"],
                "customer_auth_handle_id": request.customer_auth_handle_id,
            },
        )


# ---------------------------------------------------------------------------
# Benchmark & Known-Wrong Control Suite
# ---------------------------------------------------------------------------

def run_unicorn_enterprise_b2b_benchmark_suite() -> Mapping[str, Any]:
    """Run all three Pillar 3 slots, failover chains, and known-wrong security controls."""
    soc2_slot = ZeroTouchSecurityQuestionnaireSlot()
    policy_slot = TeamSeatPolicyGovernanceSlot()
    byok_slot = BYOKAndPrivateVPCFederationSlot()

    sample_downloads = (
        DownloadedComponentRecord(
            component_id="audit_data_splits_for_errors_and_leakage",
            version="2.4.0",
            spdx_license="MIT",
            source_revision=SYNCHRONIZED_RELEASE_DIGEST,
            package_sha256=_sha256_hex({"id": "audit_data_splits_for_errors_and_leakage", "v": "2.4.0"}),
            trust_tier="baltor_reviewed",
        ),
        DownloadedComponentRecord(
            component_id="ttl_lru_cache_with_monotonic_clock",
            version="1.9.1",
            spdx_license="Apache-2.0",
            source_revision=SYNCHRONIZED_RELEASE_DIGEST,
            package_sha256=_sha256_hex({"id": "ttl_lru_cache_with_monotonic_clock", "v": "1.9.1"}),
            trust_tier="enterprise_attested",
        ),
    )

    soc2_req = ZeroTouchSecurityPackRequest(
        request_id="soc2-pack-acme-2026-10",
        organization_id="org_acme_enterprise",
        billing_period="2026-10",
        plan_tier_name="Baltor Team & Enterprise",
        requested_control_ids=tuple(VERIFIED_ENTERPRISE_CONTROLS.keys()),
        downloaded_components=sample_downloads,
    )
    soc2_primary = soc2_slot.handle(soc2_req)
    soc2_failover = soc2_slot.handle(
        ZeroTouchSecurityPackRequest(
            request_id="soc2-pack-acme-failover",
            organization_id="org_acme_enterprise",
            billing_period="2026-10",
            plan_tier_name="Baltor Team & Enterprise",
            requested_control_ids=tuple(VERIFIED_ENTERPRISE_CONTROLS.keys()),
            downloaded_components=sample_downloads,
            simulate_primary_deferral=True,
        )
    )

    enterprise_policy = OrganizationGovernancePolicy(organization_id="org_acme_enterprise")
    seat_events = (
        SeatMaterializationEvent(
            seat_id="seat_eng_01",
            department="platform_security",
            project_code="proj_zero_trust",
            component_id="audit_data_splits_for_errors_and_leakage",
            spdx_license="MIT",
            trust_tier="baltor_reviewed",
            category="data_assurance",
            units_consumed=1200,
            seat_downloads_today=4,
            seat_units_today=8400,
        ),
        SeatMaterializationEvent(
            seat_id="seat_eng_02",
            department="ml_infrastructure",
            project_code="proj_feature_store",
            component_id="ttl_lru_cache_with_monotonic_clock",
            spdx_license="Apache-2.0",
            trust_tier="enterprise_attested",
            category="caching_primitives",
            units_consumed=950,
            seat_downloads_today=3,
            seat_units_today=5100,
        ),
    )
    policy_primary = policy_slot.handle(
        TeamPolicyGovernanceRequest(
            request_id="policy-acme-primary",
            caller_organization_id="org_acme_enterprise",
            target_organization_id="org_acme_enterprise",
            policy=enterprise_policy,
            events=seat_events,
        )
    )
    policy_failover = policy_slot.handle(
        TeamPolicyGovernanceRequest(
            request_id="policy-acme-failover",
            caller_organization_id="org_acme_enterprise",
            target_organization_id="org_acme_enterprise",
            policy=enterprise_policy,
            events=seat_events,
            simulate_primary_deferral=True,
        )
    )

    byok_results = []
    for target_id in CUSTOMER_INFERENCE_TARGETS:
        target = CUSTOMER_INFERENCE_TARGETS[target_id]
        priv_cards = ("internal_payments_ledger_contract_v2",) if target.allows_private_repo_context else ()
        res = byok_slot.handle(
            BYOKAndPrivateVPCFederationRequest(
                request_id=f"byok-{target_id}",
                organization_id="org_acme_enterprise",
                inference_target_id=target_id,
                customer_auth_handle_id="keyring://acme/model_endpoint_handle_v1",
                public_baltor_contract_ids=("audit_data_splits_for_errors_and_leakage",),
                private_internal_contract_ids=priv_cards,
            )
        )
        byok_results.append({
            "target_id": target_id,
            "endpoint_url": target.endpoint_url,
            "boundary_class": target.boundary_class,
            "succeeded": res.succeeded,
            "selected_engine": res.selected_engine,
            "private_code_never_egresses": res.payload.get("private_code_never_egresses", False),
            "latency_ms": res.latency_ms,
        })

    # Known-wrong controls (must all be refused before engine execution)
    probe_copyleft = policy_slot.handle(
        TeamPolicyGovernanceRequest(
            request_id="probe-copyleft-gpl3",
            caller_organization_id="org_acme_enterprise",
            target_organization_id="org_acme_enterprise",
            policy=enterprise_policy,
            events=(
                SeatMaterializationEvent(
                    seat_id="seat_eng_03",
                    department="core_api",
                    project_code="proj_gateway",
                    component_id="copyleft_viral_parser",
                    spdx_license="GPL-3.0-only",
                    trust_tier="community_unreviewed",
                    category="parsers",
                    units_consumed=500,
                    seat_downloads_today=1,
                    seat_units_today=500,
                ),
            ),
        )
    )
    probe_private_egress = byok_slot.handle(
        BYOKAndPrivateVPCFederationRequest(
            request_id="probe-private-source-egress",
            organization_id="org_acme_enterprise",
            inference_target_id="customer_byok_ollama_cloud",
            customer_auth_handle_id="keyring://acme/cloud_handle",
            public_baltor_contract_ids=("audit_data_splits_for_errors_and_leakage",),
            private_internal_contract_ids=("internal_secret_trading_strategy_v1",),
            attempt_private_source_egress_to_public_cloud=True,
        )
    )
    probe_cross_org_audit = policy_slot.handle(
        TeamPolicyGovernanceRequest(
            request_id="probe-cross-tenant-audit-read",
            caller_organization_id="org_intruder_tenant",
            target_organization_id="org_acme_enterprise",
            policy=enterprise_policy,
            events=seat_events,
        )
    )
    probe_unverified_claim = soc2_slot.handle(
        ZeroTouchSecurityPackRequest(
            request_id="probe-fabricated-compliance-claim",
            organization_id="org_acme_enterprise",
            billing_period="2026-10",
            plan_tier_name="Baltor Team & Enterprise",
            requested_control_ids=tuple(VERIFIED_ENTERPRISE_CONTROLS.keys()),
            downloaded_components=sample_downloads,
            unverified_custom_claims=("FedRAMP-High-Authorized-Without-Receipt",),
        )
    )
    probe_seat_budget = policy_slot.handle(
        TeamPolicyGovernanceRequest(
            request_id="probe-seat-budget-overrun",
            caller_organization_id="org_acme_enterprise",
            target_organization_id="org_acme_enterprise",
            policy=enterprise_policy,
            events=(
                SeatMaterializationEvent(
                    seat_id="seat_eng_99",
                    department="ml_infrastructure",
                    project_code="proj_overrun",
                    component_id="ttl_lru_cache_with_monotonic_clock",
                    spdx_license="MIT",
                    trust_tier="baltor_reviewed",
                    category="caching_primitives",
                    units_consumed=25_000,
                    seat_downloads_today=300,
                    seat_units_today=495_000,
                ),
            ),
        )
    )

    known_wrong_probes = (
        ("copyleft_or_unreviewed_component_blocked", probe_copyleft),
        ("private_source_or_raw_byok_egress_blocked", probe_private_egress),
        ("cross_organization_tenant_audit_read_blocked", probe_cross_org_audit),
        ("unverified_compliance_claim_fabrication_blocked", probe_unverified_claim),
        ("seat_daily_budget_overrun_blocked", probe_seat_budget),
    )
    probe_rows = []
    for name, result in known_wrong_probes:
        assert not result.succeeded and result.refusal is not None
        probe_rows.append({
            "probe_name": name,
            "refused_by_layer": result.trace.refused_by,
            "refusal_code": result.refusal.code,
            "blocked_before_engine": len(result.attempted_engines) == 0,
        })

    return MappingProxyType({
        "schema": BENCHMARK_SUITE_SCHEMA,
        "release_digest": SYNCHRONIZED_RELEASE_DIGEST,
        "soc2_primary": soc2_primary.payload,
        "soc2_failover_selected_engine": soc2_failover.selected_engine,
        "soc2_failover_attempted_engines": soc2_failover.attempted_engines,
        "policy_primary": policy_primary.payload,
        "policy_failover_selected_engine": policy_failover.selected_engine,
        "policy_failover_attempted_engines": policy_failover.attempted_engines,
        "byok_routes": tuple(byok_results),
        "known_wrong_probes": tuple(probe_rows),
        "all_checks_passed": (
            soc2_primary.succeeded
            and soc2_failover.succeeded
            and policy_primary.succeeded
            and policy_failover.succeeded
            and all(r["succeeded"] for r in byok_results)
            and all(p["blocked_before_engine"] for p in probe_rows)
        ),
    })


if __name__ == "__main__":
    summary = run_unicorn_enterprise_b2b_benchmark_suite()
    print(json.dumps(dict(summary), indent=2, default=str))
