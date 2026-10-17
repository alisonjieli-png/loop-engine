"""Multi-surface startup federation and shared backend dispatch engines wrapped in 7-layer envelopes.

Models all 22 startup surface areas across four surface families (Commercial Core, Standalone
Product Brand, Library Showcase Subdomains, and Public Good / Open Protocol Surfaces), six
shared backend planes plus the staff systems view plane, strict cross-surface security and
isolation handshakes in Layer 3 (handshake) and Layer 6 (preflight), and four swappable
multi-surface backend dispatch engines with bounded cascade failover.

Nothing in this module performs network I/O, mutates live provider state, or opens external
connections. All functions and engines operate deterministically in memory.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
import hashlib
import json
from types import MappingProxyType
from typing import Any

from loop_engine.core.engines.envelope import (
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    ENVELOPE_LAYERS,
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
    RecoveryAllowance,
    enter_nested,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (
    STEP_PASSED,
    STEP_REPAIRED,
    VERDICT_READY,
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (
    ANSWER_FROM_FIRST_RESULT,
    DISPATCH,
    EFFECT_STATE_CONFIRMED,
    EFFECT_STATE_NONE,
    REQUEST_ANSWERED,
    REQUEST_OUTCOMES,
    RESYNC_IN_SYNC,
    RESYNC_NOW,
    RESYNC_WAIT,
    TASK_COMPLETED,
    TASK_FAILED,
    EnvelopeJournalEntry,
    EnvelopeResyncBackoff,
    EnvelopeResyncObservation,
    journal_decision,
    journal_intent,
    journal_outcome,
    request_identity_digest,
    resync_decision,
)
from loop_engine.core.service_runtime.brand_profiles import BRAND_NAMES
from loop_engine.core.service_runtime.web_site_map import load_site_map

SCHEME = "https"
FEDERATION_COMPONENT_ID = "multi_surface_federation_router"
FEDERATION_REQUEST_RECORD = "cross_surface_federation_request/v1"
FEDERATION_RESPONSE_RECORD = "cross_surface_federation_response/v1"
BENCHMARK_REPORT_RECORD = "multi_surface_federation_benchmark/v1"

# Surface families
FAMILY_COMMERCIAL_CORE = "commercial_core"
FAMILY_STANDALONE_BRAND = "standalone_product_brand"
FAMILY_LIBRARY_SHOWCASE = "library_showcase_subdomain"
FAMILY_PUBLIC_GOOD_PROTOCOL = "public_good_and_open_protocol"
SURFACE_FAMILIES = (
    FAMILY_COMMERCIAL_CORE,
    FAMILY_STANDALONE_BRAND,
    FAMILY_LIBRARY_SHOWCASE,
    FAMILY_PUBLIC_GOOD_PROTOCOL,
)

# Shared backend planes (typed, versioned contracts)
PLANE_CATALOGUE_PROJECTION = "catalogue_projection_plane/v1"
PLANE_FEED_DIGEST = "feed_digest_plane/v1"
PLANE_IDENTITY_ENTITLEMENT = "identity_and_entitlement_plane/v1"
PLANE_TELEMETRY_ROLLUP = "telemetry_rollup_plane/v1"
PLANE_BRIEFS_EVIDENCE = "briefs_evidence_plane/v1"
PLANE_AFK_APPROVAL_GATE = "afk_approval_gate_plane/v1"
PLANE_SYSTEMS_VIEW = "systems_view/v1"

SHARED_BACKEND_PLANES = (
    PLANE_CATALOGUE_PROJECTION,
    PLANE_FEED_DIGEST,
    PLANE_IDENTITY_ENTITLEMENT,
    PLANE_TELEMETRY_ROLLUP,
    PLANE_BRIEFS_EVIDENCE,
    PLANE_AFK_APPROVAL_GATE,
    PLANE_SYSTEMS_VIEW,
)

PUBLIC_PROJECTION_PLANES = (
    PLANE_CATALOGUE_PROJECTION,
    PLANE_FEED_DIGEST,
    PLANE_TELEMETRY_ROLLUP,
    PLANE_BRIEFS_EVIDENCE,
    PLANE_AFK_APPROVAL_GATE,
)

# Four swappable multi-surface backend dispatch engine identifiers
ENGINE_EDGE_MANIFEST = "edge_manifest_federation_engine"
ENGINE_HYBRID_SWR = "hybrid_stale_while_revalidate_engine"
ENGINE_ORIGIN_GATEWAY = "origin_scoped_gateway_engine"
ENGINE_STATIC_FAILOVER = "static_bundle_failover_engine"

FEDERATION_ENGINE_IDS = (
    ENGINE_EDGE_MANIFEST,
    ENGINE_HYBRID_SWR,
    ENGINE_ORIGIN_GATEWAY,
    ENGINE_STATIC_FAILOVER,
)

DEFAULT_RELEASE_DIGEST = "a" * 64
STALE_RELEASE_DIGEST = "b" * 64
REQUIRED_ZERO_CACHE = "no-store"
REQUIRED_HSTS_HEADER = "max-age=63072000; includeSubDomains; preload"

RECOVERABLE_ENGINE_CODES = (
    "edge_snapshot_unavailable",
    "swr_cache_and_circuit_open",
    "origin_sqlite_lock_contention",
    "origin_rate_budget_exhausted",
)


@dataclass(frozen=True)
class SurfaceDescriptor:
    """Topology and capability boundary for one startup surface area."""

    surface_id: str
    hostname: str
    family: str
    display_name: str
    allowed_planes: tuple[str, ...]
    public_projection_only: bool
    canonical_section: bool = False
    section_root: str = "/"
    requires_staff_grant: bool = False
    rate_budget_per_window: int = 120

    @property
    def origin(self) -> str:
        return f"{SCHEME}://{self.hostname}"


@dataclass(frozen=True)
class SharedBackendPlaneContract:
    """Typed, versioned contract for a shared backend projection or control plane."""

    plane_schema: str
    owner_component: str
    required_capabilities: tuple[str, ...]
    requires_signed_projection: bool
    mutates_state: bool
    staff_only: bool = False


PLANE_CONTRACTS: Mapping[str, SharedBackendPlaneContract] = MappingProxyType({
    PLANE_CATALOGUE_PROJECTION: SharedBackendPlaneContract(
        plane_schema=PLANE_CATALOGUE_PROJECTION,
        owner_component="catalogue_projection_plane",
        required_capabilities=("signed_projection_read", "digest_verification"),
        requires_signed_projection=True,
        mutates_state=False,
    ),
    PLANE_FEED_DIGEST: SharedBackendPlaneContract(
        plane_schema=PLANE_FEED_DIGEST,
        owner_component="feed_digest_plane",
        required_capabilities=("signed_projection_read", "feed_collection_index"),
        requires_signed_projection=True,
        mutates_state=False,
    ),
    PLANE_IDENTITY_ENTITLEMENT: SharedBackendPlaneContract(
        plane_schema=PLANE_IDENTITY_ENTITLEMENT,
        owner_component="identity_and_entitlement_plane",
        required_capabilities=("origin_bound_session", "entitlement_check"),
        requires_signed_projection=True,
        mutates_state=False,
    ),
    PLANE_TELEMETRY_ROLLUP: SharedBackendPlaneContract(
        plane_schema=PLANE_TELEMETRY_ROLLUP,
        owner_component="telemetry_rollup_plane",
        required_capabilities=("signed_projection_read", "aggregate_telemetry_read"),
        requires_signed_projection=True,
        mutates_state=False,
    ),
    PLANE_BRIEFS_EVIDENCE: SharedBackendPlaneContract(
        plane_schema=PLANE_BRIEFS_EVIDENCE,
        owner_component="briefs_evidence_plane",
        required_capabilities=("signed_projection_read", "evidence_digest_pin"),
        requires_signed_projection=True,
        mutates_state=False,
    ),
    PLANE_AFK_APPROVAL_GATE: SharedBackendPlaneContract(
        plane_schema=PLANE_AFK_APPROVAL_GATE,
        owner_component="afk_approval_gate_plane",
        required_capabilities=("signed_projection_read", "paired_device_gate_read"),
        requires_signed_projection=True,
        mutates_state=False,
    ),
    PLANE_SYSTEMS_VIEW: SharedBackendPlaneContract(
        plane_schema=PLANE_SYSTEMS_VIEW,
        owner_component="systems_staff_plane",
        required_capabilities=("staff_plane_read", "zero_cache_hsts_guard"),
        requires_signed_projection=True,
        mutates_state=False,
        staff_only=True,
    ),
})


def _build_surface_registry() -> Mapping[str, SurfaceDescriptor]:
    surfaces = (
        # 1. Commercial Core Surfaces (3)
        SurfaceDescriptor(
            surface_id="baltor_ai",
            hostname="baltor.ai",
            family=FAMILY_COMMERCIAL_CORE,
            display_name="Baltor",
            allowed_planes=(
                PLANE_CATALOGUE_PROJECTION,
                PLANE_FEED_DIGEST,
                PLANE_IDENTITY_ENTITLEMENT,
                PLANE_TELEMETRY_ROLLUP,
                PLANE_BRIEFS_EVIDENCE,
                PLANE_AFK_APPROVAL_GATE,
            ),
            public_projection_only=False,
            canonical_section=False,
            section_root="/",
            requires_staff_grant=False,
            rate_budget_per_window=250,
        ),
        SurfaceDescriptor(
            surface_id="baltor_dev",
            hostname="baltor.dev",
            family=FAMILY_COMMERCIAL_CORE,
            display_name="Baltor Developer Hub",
            allowed_planes=(
                PLANE_CATALOGUE_PROJECTION,
                PLANE_FEED_DIGEST,
                PLANE_IDENTITY_ENTITLEMENT,
                PLANE_TELEMETRY_ROLLUP,
                PLANE_BRIEFS_EVIDENCE,
            ),
            public_projection_only=False,
            canonical_section=False,
            section_root="/",
            requires_staff_grant=False,
            rate_budget_per_window=200,
        ),
        SurfaceDescriptor(
            surface_id="systems_baltor_ai",
            hostname="systems.baltor.ai",
            family=FAMILY_COMMERCIAL_CORE,
            display_name="Baltor Systems Staff View",
            allowed_planes=(
                PLANE_SYSTEMS_VIEW,
                PLANE_TELEMETRY_ROLLUP,
                PLANE_CATALOGUE_PROJECTION,
            ),
            public_projection_only=False,
            canonical_section=False,
            section_root="/",
            requires_staff_grant=True,
            rate_budget_per_window=80,
        ),
        # 2. Standalone Product Brand Surfaces (5)
        SurfaceDescriptor(
            surface_id="agentfeeds_si",
            hostname="agentfeeds.si",
            family=FAMILY_STANDALONE_BRAND,
            display_name=BRAND_NAMES["agentfeeds"],
            allowed_planes=(PLANE_FEED_DIGEST, PLANE_CATALOGUE_PROJECTION),
            public_projection_only=True,
            rate_budget_per_window=160,
        ),
        SurfaceDescriptor(
            surface_id="agentfoundry_si",
            hostname="agentfoundry.si",
            family=FAMILY_STANDALONE_BRAND,
            display_name=BRAND_NAMES["agentfoundry"],
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_TELEMETRY_ROLLUP),
            public_projection_only=True,
            rate_budget_per_window=160,
        ),
        SurfaceDescriptor(
            surface_id="agentstudios_si",
            hostname="agentstudios.si",
            family=FAMILY_STANDALONE_BRAND,
            display_name=BRAND_NAMES["agentstudios"],
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_TELEMETRY_ROLLUP),
            public_projection_only=True,
            rate_budget_per_window=160,
        ),
        SurfaceDescriptor(
            surface_id="agentafk_si",
            hostname="agentafk.si",
            family=FAMILY_STANDALONE_BRAND,
            display_name=BRAND_NAMES["agentafk"],
            allowed_planes=(PLANE_AFK_APPROVAL_GATE, PLANE_CATALOGUE_PROJECTION),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="agentbriefs_si",
            hostname="agentbriefs.si",
            family=FAMILY_STANDALONE_BRAND,
            display_name="AgentBriefs",
            allowed_planes=(PLANE_BRIEFS_EVIDENCE, PLANE_CATALOGUE_PROJECTION),
            public_projection_only=True,
            rate_budget_per_window=140,
        ),
        # 3. Library Showcase Subdomains (5)
        SurfaceDescriptor(
            surface_id="deterministicskills_baltor_ai",
            hostname="deterministicskills.baltor.ai",
            family=FAMILY_LIBRARY_SHOWCASE,
            display_name="Deterministic Skills Showcase",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_BRIEFS_EVIDENCE),
            public_projection_only=True,
            canonical_section=True,
            section_root="/deterministic-skills",
            rate_budget_per_window=150,
        ),
        SurfaceDescriptor(
            surface_id="tools_baltor_ai",
            hostname="tools.baltor.ai",
            family=FAMILY_LIBRARY_SHOWCASE,
            display_name="Harness Tools Showcase",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_BRIEFS_EVIDENCE),
            public_projection_only=True,
            canonical_section=True,
            section_root="/tools",
            rate_budget_per_window=150,
        ),
        SurfaceDescriptor(
            surface_id="cornercases_baltor_ai",
            hostname="cornercases.baltor.ai",
            family=FAMILY_LIBRARY_SHOWCASE,
            display_name="Corner Cases Showcase",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_BRIEFS_EVIDENCE),
            public_projection_only=True,
            canonical_section=True,
            section_root="/corner-cases",
            rate_budget_per_window=150,
        ),
        SurfaceDescriptor(
            surface_id="docs_baltor_ai",
            hostname="docs.baltor.ai",
            family=FAMILY_LIBRARY_SHOWCASE,
            display_name="Baltor Documentation Surface",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_FEED_DIGEST),
            public_projection_only=True,
            canonical_section=False,
            section_root="/docs",
            rate_budget_per_window=150,
        ),
        SurfaceDescriptor(
            surface_id="gallery_baltor_ai",
            hostname="gallery.baltor.ai",
            family=FAMILY_LIBRARY_SHOWCASE,
            display_name="Baltor Creative Gallery Surface",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_TELEMETRY_ROLLUP),
            public_projection_only=True,
            canonical_section=False,
            section_root="/gallery",
            rate_budget_per_window=150,
        ),
        # 4. Public Good & Open Protocol Surfaces (9)
        SurfaceDescriptor(
            surface_id="skillsforgood_org",
            hostname="skillsforgood.org",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Skills for Good",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_BRIEFS_EVIDENCE),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="theloopengine_org",
            hostname="theloopengine.org",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="The Loop Engine Foundation",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_TELEMETRY_ROLLUP),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="loopengine_io",
            hostname="loopengine.io",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Loop Engine Ecosystem",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_FEED_DIGEST),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="loopengine_dev",
            hostname="loopengine.dev",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Loop Engine Developer Portal",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_TELEMETRY_ROLLUP),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="agenticengineering_org",
            hostname="agenticengineering.org",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Agentic Engineering Standards",
            allowed_planes=(PLANE_BRIEFS_EVIDENCE, PLANE_CATALOGUE_PROJECTION),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="openknowledgeformat_org",
            hostname="openknowledgeformat.org",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Open Knowledge Format",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION,),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="openintelligenceprotocol_org",
            hostname="openintelligenceprotocol.org",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Open Intelligence Protocol",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_FEED_DIGEST),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="openpractitionerprotocol_org",
            hostname="openpractitionerprotocol.org",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Open Practitioner Protocol",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION,),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
        SurfaceDescriptor(
            surface_id="opensolutionprotocol_org",
            hostname="opensolutionprotocol.org",
            family=FAMILY_PUBLIC_GOOD_PROTOCOL,
            display_name="Open Solution Protocol",
            allowed_planes=(PLANE_CATALOGUE_PROJECTION, PLANE_BRIEFS_EVIDENCE),
            public_projection_only=True,
            rate_budget_per_window=120,
        ),
    )
    return MappingProxyType({item.hostname: item for item in surfaces})


SURFACE_TOPOLOGY_REGISTRY: Mapping[str, SurfaceDescriptor] = _build_surface_registry()


def verify_site_map_and_brand_alignment() -> dict[str, Any]:
    """Check that canonical section hostnames in the topology registry match web_site_map.json."""
    site_map = load_site_map()
    by_host = {surface.hostname: surface for surface in site_map.hostnames}
    checked_sections = []
    mismatches = []
    for hostname in ("deterministicskills.baltor.ai", "tools.baltor.ai", "cornercases.baltor.ai"):
        descriptor = SURFACE_TOPOLOGY_REGISTRY[hostname]
        site_entry = by_host.get(hostname)
        if site_entry is None:
            mismatches.append(f"missing_in_site_map:{hostname}")
            continue
        if site_entry.canonical_section != descriptor.canonical_section or site_entry.address != descriptor.section_root:
            mismatches.append(f"section_mismatch:{hostname}")
        checked_sections.append(hostname)
    return {
        "aligned": len(mismatches) == 0,
        "checked_sections": tuple(checked_sections),
        "mismatches": tuple(mismatches),
        "total_surfaces": len(SURFACE_TOPOLOGY_REGISTRY),
    }


@dataclass(frozen=True)
class CrossSurfaceFederationRequest:
    """One inbound cross-surface shared-backend plane request wrapped in the 7-layer envelope."""

    request_id: str
    surface_hostname: str
    plane_schema: str
    section_root: str = "/"
    release_digest: str = DEFAULT_RELEASE_DIGEST
    served_release_digest: str = DEFAULT_RELEASE_DIGEST
    has_session_cookie: bool = False
    invokes_staff_tool: bool = False
    mutates_account_state: bool = False
    includes_external_idp_csp: bool = False
    staff_grant: bool = False
    hsts_enabled: bool = True
    cache_control: str = REQUIRED_ZERO_CACHE
    signature_verified: bool = True
    principal_id: str = ""
    allow_release_resync: bool = False
    at: str = "2026-10-16T18:00:00Z"
    schema_tag: str = FEDERATION_REQUEST_RECORD


@dataclass(frozen=True)
class EngineDispatchOutcome:
    """Result returned by one of the four swappable multi-surface backend dispatch engines."""

    engine_id: str
    succeeded: bool
    payload: Mapping[str, Any] | None
    latency_ms: float
    origin_lock_wait_ms: float
    cache_hit: bool
    stale_served: bool
    revalidation_queued: bool
    circuit_breaker_open: bool
    refusal: EnvelopeRefusal | None = None


@dataclass(frozen=True)
class CrossSurfaceFederationResponse:
    """Complete 7-layer envelope response for a multi-surface federation request."""

    request_id: str
    surface_hostname: str
    family: str
    plane_schema: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    handshake_verdict: EnvelopeHandshakeVerdict | None
    preflight_report: EnvelopePreflightReport | None
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    journal_entries: tuple[EnvelopeJournalEntry, ...]
    resync_state: str
    payload: Mapping[str, Any] | None
    refusal: EnvelopeRefusal | None
    latency_ms: float
    origin_lock_wait_ms: float
    schema_tag: str = FEDERATION_RESPONSE_RECORD

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.schema_tag,
            "request_id": self.request_id,
            "surface_hostname": self.surface_hostname,
            "family": self.family,
            "plane_schema": self.plane_schema,
            "succeeded": self.succeeded,
            "selected_engine": self.selected_engine,
            "attempted_engines": list(self.attempted_engines),
            "handshake_verdict": None if self.handshake_verdict is None else self.handshake_verdict.to_dict(),
            "preflight_report": None if self.preflight_report is None else self.preflight_report.to_dict(),
            "trace": self.trace.to_dict(),
            "frame": self.frame.to_dict(),
            "resync_state": self.resync_state,
            "payload": None if self.payload is None else dict(self.payload),
            "refusal": None if self.refusal is None else self.refusal.to_dict(),
            "latency_ms": round(self.latency_ms, 4),
            "origin_lock_wait_ms": round(self.origin_lock_wait_ms, 4),
        }


def _projection_digest(surface_hostname: str, plane_schema: str, release_digest: str) -> str:
    body = json.dumps(
        {"surface": surface_hostname, "plane": plane_schema, "release": release_digest},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _build_projection_payload(
    surface: SurfaceDescriptor,
    plane_schema: str,
    release_digest: str,
    engine_id: str,
    *,
    fallback_mode: str = "primary",
) -> Mapping[str, Any]:
    return MappingProxyType({
        "record_type": plane_schema,
        "surface_id": surface.surface_id,
        "surface_hostname": surface.hostname,
        "surface_family": surface.family,
        "origin": surface.origin,
        "section_root": surface.section_root,
        "canonical_section": surface.canonical_section,
        "release_digest": release_digest,
        "projection_sha256": _projection_digest(surface.hostname, plane_schema, release_digest),
        "served_by_engine": engine_id,
        "delivery_tier": fallback_mode,
        "cross_surface_cookies_stripped": surface.public_projection_only,
    })


# ============================================================================
# 4 Swappable Multi-Surface Backend Dispatch Engines
# ============================================================================


class EdgeManifestFederationEngine:
    """Engine 1: Serves signed immutable R2/Edge snapshots across all 22 surfaces with O(1) lookup."""

    engine_id = ENGINE_EDGE_MANIFEST

    def __init__(
        self,
        *,
        served_release_digest: str = DEFAULT_RELEASE_DIGEST,
        evicted_surfaces: frozenset[str] = frozenset(),
        degraded: bool = False,
    ) -> None:
        self._served_release_digest = served_release_digest
        self._evicted_surfaces = frozenset(evicted_surfaces)
        self._degraded = degraded
        self._manifest_index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
        for hostname, surface in SURFACE_TOPOLOGY_REGISTRY.items():
            for plane in surface.allowed_planes:
                self._manifest_index[(hostname, plane, served_release_digest)] = _build_projection_payload(
                    surface, plane, served_release_digest, self.engine_id
                )

    def dispatch(
        self,
        request: CrossSurfaceFederationRequest,
        surface: SurfaceDescriptor,
        repaired_release_digest: str,
    ) -> EngineDispatchOutcome:
        if self._degraded or surface.hostname in self._evicted_surfaces:
            refusal = envelope_refusal(
                "edge_snapshot_unavailable",
                "The immutable edge manifest snapshot is unavailable in the current edge pop.",
                "Allow the federation router to fail over to the hybrid stale-while-revalidate engine.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
                automatic_retry=True,
            )
            return EngineDispatchOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                payload=None,
                latency_ms=0.18,
                origin_lock_wait_ms=0.0,
                cache_hit=False,
                stale_served=False,
                revalidation_queued=False,
                circuit_breaker_open=False,
                refusal=refusal,
            )
        key = (surface.hostname, request.plane_schema, repaired_release_digest)
        payload = self._manifest_index.get(key)
        if payload is None:
            refusal = envelope_refusal(
                "edge_snapshot_unavailable",
                "The requested release projection is not indexed in the immutable edge manifest.",
                "Fail over to the next configured federation engine or refresh the edge manifest.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
                automatic_retry=True,
            )
            return EngineDispatchOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                payload=None,
                latency_ms=0.21,
                origin_lock_wait_ms=0.0,
                cache_hit=False,
                stale_served=False,
                revalidation_queued=False,
                circuit_breaker_open=False,
                refusal=refusal,
            )
        return EngineDispatchOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            payload=payload,
            latency_ms=0.42,
            origin_lock_wait_ms=0.0,
            cache_hit=True,
            stale_served=False,
            revalidation_queued=False,
            circuit_breaker_open=False,
            refusal=None,
        )


class HybridStaleWhileRevalidateEngine:
    """Engine 2: Serves cached edge projections immediately while queueing async origin revalidation."""

    engine_id = ENGINE_HYBRID_SWR

    def __init__(
        self,
        *,
        served_release_digest: str = DEFAULT_RELEASE_DIGEST,
        circuit_failure_threshold: int = 3,
        origin_failures: int = 0,
        cold_surfaces: frozenset[str] = frozenset(),
    ) -> None:
        self._served_release_digest = served_release_digest
        self._circuit_failure_threshold = circuit_failure_threshold
        self._origin_failures = origin_failures
        self._cold_surfaces = frozenset(cold_surfaces)
        self._revalidation_queue: list[tuple[str, str]] = []

    @property
    def revalidation_queue_depth(self) -> int:
        return len(self._revalidation_queue)

    @property
    def circuit_breaker_open(self) -> bool:
        return self._origin_failures >= self._circuit_failure_threshold

    def record_origin_failure(self) -> None:
        self._origin_failures += 1

    def dispatch(
        self,
        request: CrossSurfaceFederationRequest,
        surface: SurfaceDescriptor,
        repaired_release_digest: str,
    ) -> EngineDispatchOutcome:
        breaker_open = self.circuit_breaker_open
        if surface.hostname in self._cold_surfaces and breaker_open:
            refusal = envelope_refusal(
                "swr_cache_and_circuit_open",
                "The stale-while-revalidate cache is cold for this surface while the origin circuit breaker is open.",
                "Fail over to the static bundle failover engine until the origin circuit breaker resets.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
                automatic_retry=True,
            )
            return EngineDispatchOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                payload=None,
                latency_ms=0.65,
                origin_lock_wait_ms=0.0,
                cache_hit=False,
                stale_served=False,
                revalidation_queued=False,
                circuit_breaker_open=True,
                refusal=refusal,
            )
        self._revalidation_queue.append((surface.hostname, request.plane_schema))
        payload = _build_projection_payload(
            surface,
            request.plane_schema,
            repaired_release_digest,
            self.engine_id,
            fallback_mode="swr_cached_projection",
        )
        return EngineDispatchOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            payload=payload,
            latency_ms=1.15,
            origin_lock_wait_ms=0.0,
            cache_hit=True,
            stale_served=True,
            revalidation_queued=True,
            circuit_breaker_open=breaker_open,
            refusal=None,
        )


class OriginScopedGatewayEngine:
    """Engine 3: Direct origin SQLite/service-runtime plane router with per-surface rate budgets."""

    engine_id = ENGINE_ORIGIN_GATEWAY

    def __init__(
        self,
        *,
        simulated_concurrent_writers: int = 0,
        lock_saturation_threshold: int = 8,
        rate_budget_override: int | None = None,
    ) -> None:
        self._concurrent_writers = simulated_concurrent_writers
        self._lock_saturation_threshold = lock_saturation_threshold
        self._rate_budget_override = rate_budget_override
        self._surface_counts: dict[str, int] = {}

    def dispatch(
        self,
        request: CrossSurfaceFederationRequest,
        surface: SurfaceDescriptor,
        repaired_release_digest: str,
    ) -> EngineDispatchOutcome:
        budget = (
            self._rate_budget_override
            if self._rate_budget_override is not None
            else surface.rate_budget_per_window
        )
        used = self._surface_counts.get(surface.hostname, 0)
        if used >= budget:
            refusal = envelope_refusal(
                "origin_rate_budget_exhausted",
                "The origin gateway rate budget for this surface window has been exhausted.",
                "Fail over to the static bundle failover engine or wait for the next rate window.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
                automatic_retry=True,
            )
            return EngineDispatchOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                payload=None,
                latency_ms=1.8,
                origin_lock_wait_ms=0.0,
                cache_hit=False,
                stale_served=False,
                revalidation_queued=False,
                circuit_breaker_open=False,
                refusal=refusal,
            )
        lock_wait_ms = float(self._concurrent_writers) * 2.75
        if self._concurrent_writers >= self._lock_saturation_threshold:
            refusal = envelope_refusal(
                "origin_sqlite_lock_contention",
                "Origin SQLite write lock contention exceeded the gateway wait threshold for this plane.",
                "Fail over to an edge snapshot or static bundle engine while origin locks clear.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
                automatic_retry=True,
            )
            return EngineDispatchOutcome(
                engine_id=self.engine_id,
                succeeded=False,
                payload=None,
                latency_ms=4.2 + lock_wait_ms,
                origin_lock_wait_ms=lock_wait_ms,
                cache_hit=False,
                stale_served=False,
                revalidation_queued=False,
                circuit_breaker_open=False,
                refusal=refusal,
            )
        self._surface_counts[surface.hostname] = used + 1
        payload = _build_projection_payload(
            surface,
            request.plane_schema,
            repaired_release_digest,
            self.engine_id,
            fallback_mode="origin_direct",
        )
        return EngineDispatchOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            payload=payload,
            latency_ms=3.4 + lock_wait_ms,
            origin_lock_wait_ms=lock_wait_ms,
            cache_hit=False,
            stale_served=False,
            revalidation_queued=False,
            circuit_breaker_open=False,
            refusal=None,
        )


class StaticBundleFailoverEngine:
    """Engine 4: Guaranteed zero-downtime deterministic fallback when origin or edge KV is degraded."""

    engine_id = ENGINE_STATIC_FAILOVER

    def dispatch(
        self,
        request: CrossSurfaceFederationRequest,
        surface: SurfaceDescriptor,
        repaired_release_digest: str,
    ) -> EngineDispatchOutcome:
        payload = _build_projection_payload(
            surface,
            request.plane_schema,
            repaired_release_digest,
            self.engine_id,
            fallback_mode="static_deterministic_failover",
        )
        return EngineDispatchOutcome(
            engine_id=self.engine_id,
            succeeded=True,
            payload=payload,
            latency_ms=0.29,
            origin_lock_wait_ms=0.0,
            cache_hit=True,
            stale_served=True,
            revalidation_queued=False,
            circuit_breaker_open=False,
            refusal=None,
        )


# ============================================================================
# 7-Layer Envelope Router & Cross-Surface Security Handshake Enforcement
# ============================================================================


def _carrier_check(
    request: CrossSurfaceFederationRequest,
) -> tuple[SurfaceDescriptor | None, SharedBackendPlaneContract | None, EnvelopeRefusal | None]:
    """Layer 2 (carrier): validate schema tag, registered surface hostname, and versioned plane contract."""
    if request.schema_tag != FEDERATION_REQUEST_RECORD:
        return (
            None,
            None,
            envelope_refusal(
                "unsupported_carrier_schema",
                "The cross-surface request does not carry the expected federation request schema.",
                "Send the request using the versioned cross_surface_federation_request/v1 schema.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            ),
        )
    surface = SURFACE_TOPOLOGY_REGISTRY.get(request.surface_hostname)
    if surface is None:
        return (
            None,
            None,
            envelope_refusal(
                "unregistered_surface_hostname",
                "The target hostname is not registered in the startup surface topology registry.",
                "Choose one of the admitted startup surface hostnames before sending the request.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            ),
        )
    plane = PLANE_CONTRACTS.get(request.plane_schema)
    if plane is None:
        return (
            surface,
            None,
            envelope_refusal(
                "unsupported_shared_plane_schema",
                "The requested shared backend plane version is not registered at this boundary.",
                "Request one of the versioned shared backend planes declared by the federation router.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            ),
        )
    return surface, plane, None


def _handshake_check(
    request: CrossSurfaceFederationRequest,
    surface: SurfaceDescriptor,
    plane: SharedBackendPlaneContract,
) -> tuple[EnvelopeHandshakeVerdict | None, EnvelopeRefusal | None]:
    """Layer 3 (handshake): enforce cross-surface isolation and compute EnvelopeHandshakeVerdict."""
    if surface.public_projection_only:
        if request.has_session_cookie:
            return (
                None,
                envelope_refusal(
                    "cross_surface_session_cookie_forbidden",
                    "Public projection surfaces refuse requests that attach session cookies across origins.",
                    "Strip session cookies before reading a public shared backend projection.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                ),
            )
        if request.invokes_staff_tool:
            return (
                None,
                envelope_refusal(
                    "cross_surface_staff_tool_forbidden",
                    "Public projection surfaces never expose staff plane tools or operator mutations.",
                    "Invoke staff operations only through the dedicated systems staff surface with a staff grant.",
                    retry= DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                ),
            )
        if request.mutates_account_state:
            return (
                None,
                envelope_refusal(
                    "cross_surface_account_mutation_forbidden",
                    "Public brand and protocol surfaces cannot mutate account or billing state on shared planes.",
                    "Perform account or billing updates on the canonical commercial origin directly.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                ),
            )
        if request.includes_external_idp_csp:
            return (
                None,
                envelope_refusal(
                    "cross_surface_external_idp_csp_forbidden",
                    "Public projection surfaces forbid external identity provider scripts in their content policy.",
                    "Remove the external identity provider script directive from the surface request.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                ),
            )

    if request.plane_schema not in surface.allowed_planes:
        return (
            None,
            envelope_refusal(
                "plane_not_admitted_for_surface",
                "The target surface is not admitted to read or invoke the requested shared backend plane.",
                "Select a shared backend plane that the surface topology declaration permits.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            ),
        )

    hs_request = EnvelopeHandshakeRequest(
        component=FEDERATION_COMPONENT_ID,
        requested_versions=(request.plane_schema,),
        required_capabilities=plane.required_capabilities,
        advisory_capabilities=("edge_manifest_pin",),
        granted_effects=(PURE_EFFECT,),
    )
    hs_declaration = EnvelopeHandshakeDeclaration(
        engine=plane.owner_component,
        supported_versions=surface.allowed_planes,
        capabilities=plane.required_capabilities + ("edge_manifest_pin",),
        effects=(PURE_EFFECT,),
    )
    verdict = negotiate_handshake(hs_request, hs_declaration)
    if not verdict.proceeds:
        return (
            verdict,
            envelope_refusal(
                "cross_surface_handshake_incompatible",
                "The caller and shared backend plane declarations did not produce a compatible handshake verdict.",
                "Align the requested plane version and capabilities with the surface declaration.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            ),
        )
    return verdict, None


def _account_check(
    request: CrossSurfaceFederationRequest,
    surface: SurfaceDescriptor,
    plane: SharedBackendPlaneContract,
) -> EnvelopeRefusal | None:
    """Layer 4 (account): verify staff grant on systems.baltor.ai and principal scope on entitlement plane."""
    if surface.requires_staff_grant or plane.staff_only:
        if not request.staff_grant:
            return envelope_refusal(
                "staff_grant_required",
                "The staff systems surface requires an explicit verified operator staff grant before access.",
                "Authenticate with a verified operator account holding a current staff grant.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
            )
    if request.plane_schema == PLANE_IDENTITY_ENTITLEMENT and not request.principal_id.strip():
        return envelope_refusal(
            "principal_identity_required",
            "Reading the identity and entitlement plane requires an explicit origin-bound principal identifier.",
            "Supply the authenticated principal identifier for the commercial core origin.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _build_preflight_checks_and_repairs(
    surface: SurfaceDescriptor,
    plane: SharedBackendPlaneContract,
) -> tuple[tuple[EnvelopePreflightCheck, ...], tuple[EnvelopeSelfRepair, ...]]:
    """Layer 6 (preflight): section-canonical binding, release digest parity, HSTS/zero-cache, and signature."""

    def check_section_binding(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if surface.canonical_section and ctx.get("section_root") != surface.section_root:
            return envelope_refusal(
                "section_root_binding_mismatch",
                "The canonical section hostname request does not match its bound section root path.",
                "Bind the request to the exact section root declared for this canonical section hostname.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def check_release_digest_parity(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if ctx.get("release_digest") != ctx.get("served_release_digest"):
            return envelope_refusal(
                "served_release_digest_mismatch",
                "The surface projection release digest does not match the currently served library release digest.",
                "Resynchronize the surface projection to the current served release digest before serving.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
            )
        return None

    def check_staff_headers(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if surface.requires_staff_grant or plane.staff_only:
            if not ctx.get("hsts_enabled") or ctx.get("cache_control") != REQUIRED_ZERO_CACHE:
                return envelope_refusal(
                    "staff_surface_security_headers_missing",
                    "The staff surface requires Strict-Transport-Security and zero-cache headers on every response.",
                    "Enable Strict-Transport-Security and set Cache-Control to no-store on the staff surface.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                )
        return None

    def check_projection_signature(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if plane.requires_signed_projection and not ctx.get("signature_verified"):
            return envelope_refusal(
                "unsigned_shared_projection_refused",
                "The shared backend projection lacks a verified release signature and cannot be served.",
                "Sign the projection manifest with the release authority before publishing to the edge.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
            )
        return None

    def repair_stale_release_digest(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
        updated = dict(ctx)
        if updated.get("allow_release_resync"):
            updated["release_digest"] = updated["served_release_digest"]
        return updated

    checks = (
        EnvelopePreflightCheck(
            check_id="section_canonical_binding_check",
            diagnoses=("section_root_binding_mismatch",),
            run=check_section_binding,
        ),
        EnvelopePreflightCheck(
            check_id="served_release_digest_parity_check",
            diagnoses=("served_release_digest_mismatch",),
            run=check_release_digest_parity,
        ),
        EnvelopePreflightCheck(
            check_id="staff_surface_headers_check",
            diagnoses=("staff_surface_security_headers_missing",),
            run=check_staff_headers,
        ),
        EnvelopePreflightCheck(
            check_id="projection_signature_check",
            diagnoses=("unsigned_shared_projection_refused",),
            run=check_projection_signature,
        ),
    )
    repairs = (
        EnvelopeSelfRepair(
            repair_id="resync_edge_release_digest_repair",
            fixes=("served_release_digest_mismatch",),
            effects=(PURE_EFFECT,),
            maximum_applications=1,
            apply=repair_stale_release_digest,
        ),
    )
    return checks, repairs


class MultiSurfaceFederationOrchestrator:
    """7-Layer Envelope router and 4-engine cascade failover orchestrator across all 22 startup surfaces."""

    def __init__(
        self,
        *,
        edge_engine: EdgeManifestFederationEngine | None = None,
        swr_engine: HybridStaleWhileRevalidateEngine | None = None,
        origin_engine: OriginScopedGatewayEngine | None = None,
        static_engine: StaticBundleFailoverEngine | None = None,
        engine_order: tuple[str, ...] = FEDERATION_ENGINE_IDS,
    ) -> None:
        self.edge_engine = edge_engine or EdgeManifestFederationEngine()
        self.swr_engine = swr_engine or HybridStaleWhileRevalidateEngine()
        self.origin_engine = origin_engine or OriginScopedGatewayEngine()
        self.static_engine = static_engine or StaticBundleFailoverEngine()
        self.engine_order = engine_order
        self._engines = {
            ENGINE_EDGE_MANIFEST: self.edge_engine,
            ENGINE_HYBRID_SWR: self.swr_engine,
            ENGINE_ORIGIN_GATEWAY: self.origin_engine,
            ENGINE_STATIC_FAILOVER: self.static_engine,
        }
        self._journal: list[EnvelopeJournalEntry] = []
        self._cached_responses: dict[str, CrossSurfaceFederationResponse] = {}
        self._recovery_policy = EnvelopeRecoveryPolicy(
            component=FEDERATION_COMPONENT_ID,
            maximum_automatic_attempts=3,
            recoverable_codes=RECOVERABLE_ENGINE_CODES,
        )
        self._backoff = EnvelopeResyncBackoff(first_wait_seconds=2.0, longest_wait_seconds=60.0)

    def handle(self, request: CrossSurfaceFederationRequest) -> CrossSurfaceFederationResponse:
        """Execute all 7 envelope layers and dispatch through the configured engine cascade chain."""
        frame = root_frame(FEDERATION_COMPONENT_ID, automatic_attempts=3, maximum_depth=4)
        steps: list[tuple[str, str]] = []

        # Layer 2: Carrier
        surface, plane, carrier_refusal = _carrier_check(request)
        if carrier_refusal is not None or surface is None or plane is None:
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            trace = EnvelopeTrace(FEDERATION_COMPONENT_ID, tuple(steps), False, LAYER_CARRIER, carrier_refusal)
            return CrossSurfaceFederationResponse(
                request_id=request.request_id,
                surface_hostname=request.surface_hostname,
                family=surface.family if surface else "unknown",
                plane_schema=request.plane_schema,
                succeeded=False,
                selected_engine="",
                attempted_engines=(),
                handshake_verdict=None,
                preflight_report=None,
                trace=trace,
                frame=frame,
                journal_entries=(),
                resync_state=RESYNC_IN_SYNC,
                payload=None,
                refusal=carrier_refusal,
                latency_ms=0.05,
                origin_lock_wait_ms=0.0,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3: Handshake
        verdict, hs_refusal = _handshake_check(request, surface, plane)
        if hs_refusal is not None:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(FEDERATION_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, hs_refusal)
            return CrossSurfaceFederationResponse(
                request_id=request.request_id,
                surface_hostname=request.surface_hostname,
                family=surface.family,
                plane_schema=request.plane_schema,
                succeeded=False,
                selected_engine="",
                attempted_engines=(),
                handshake_verdict=verdict,
                preflight_report=None,
                trace=trace,
                frame=frame,
                journal_entries=(),
                resync_state=RESYNC_IN_SYNC,
                payload=None,
                refusal=hs_refusal,
                latency_ms=0.08,
                origin_lock_wait_ms=0.0,
            )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4: Account
        account_refusal = _account_check(request, surface, plane)
        if account_refusal is not None:
            steps.append((LAYER_ACCOUNT, LAYER_REFUSED))
            trace = EnvelopeTrace(FEDERATION_COMPONENT_ID, tuple(steps), False, LAYER_ACCOUNT, account_refusal)
            return CrossSurfaceFederationResponse(
                request_id=request.request_id,
                surface_hostname=request.surface_hostname,
                family=surface.family,
                plane_schema=request.plane_schema,
                succeeded=False,
                selected_engine="",
                attempted_engines=(),
                handshake_verdict=verdict,
                preflight_report=None,
                trace=trace,
                frame=frame,
                journal_entries=(),
                resync_state=RESYNC_IN_SYNC,
                payload=None,
                refusal=account_refusal,
                latency_ms=0.10,
                origin_lock_wait_ms=0.0,
            )
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 5: Tracking (journal replay + release resync observation)
        req_digest = request_identity_digest(request.request_id)
        decision = journal_decision(self._journal, req_digest)
        resync_obs = EnvelopeResyncObservation(
            desired=request.served_release_digest,
            observed=request.release_digest,
        )
        resync_state = resync_decision(resync_obs, self._backoff)
        if decision.decision == ANSWER_FROM_FIRST_RESULT and req_digest in self._cached_responses:
            prior = self._cached_responses[req_digest]
            steps.append((LAYER_TRACKING, LAYER_ANSWERED))
            trace = EnvelopeTrace(FEDERATION_COMPONENT_ID, tuple(steps), False, "", None)
            return replace(prior, trace=trace, resync_state=resync_state)
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: Preflight (section root binding, release digest parity, HSTS/zero-cache, signature)
        checks, repairs = _build_preflight_checks_and_repairs(surface, plane)
        preflight_ctx = {
            "section_root": request.section_root,
            "release_digest": request.release_digest,
            "served_release_digest": request.served_release_digest,
            "hsts_enabled": request.hsts_enabled,
            "cache_control": request.cache_control,
            "signature_verified": request.signature_verified,
            "allow_release_resync": request.allow_release_resync,
        }
        preflight_report = run_preflight(
            FEDERATION_COMPONENT_ID,
            checks,
            repairs,
            context=preflight_ctx,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not preflight_report.ready:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            trace = EnvelopeTrace(
                FEDERATION_COMPONENT_ID,
                tuple(steps),
                False,
                LAYER_PREFLIGHT,
                preflight_report.refusal,
            )
            return CrossSurfaceFederationResponse(
                request_id=request.request_id,
                surface_hostname=request.surface_hostname,
                family=surface.family,
                plane_schema=request.plane_schema,
                succeeded=False,
                selected_engine="",
                attempted_engines=(),
                handshake_verdict=verdict,
                preflight_report=preflight_report,
                trace=trace,
                frame=frame,
                journal_entries=(),
                resync_state=resync_state,
                payload=None,
                refusal=preflight_report.refusal,
                latency_ms=0.14,
                origin_lock_wait_ms=0.0,
            )
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))
        repaired_digest = str(preflight_report.context.get("release_digest", request.release_digest))

        # Layer 7: Nested Envelopes & Swappable Engine Dispatch with Bounded Failover
        intent_entry = journal_intent(
            self._journal,
            component=FEDERATION_COMPONENT_ID,
            request_identity=req_digest,
            repeatable=True,
            at=request.at,
        )
        self._journal.append(intent_entry)

        attempted: list[str] = []
        total_latency_ms = 0.0
        total_lock_wait_ms = 0.0
        last_outcome: EngineDispatchOutcome | None = None
        current_frame = frame

        for engine_id in self.engine_order:
            current_frame = enter_nested(current_frame, engine_id)
            engine = self._engines[engine_id]
            attempted.append(engine_id)
            outcome = engine.dispatch(request, surface, repaired_digest)
            total_latency_ms += outcome.latency_ms
            total_lock_wait_ms += outcome.origin_lock_wait_ms
            last_outcome = outcome
            if outcome.succeeded and outcome.payload is not None:
                payload_digest = hashlib.sha256(
                    json.dumps(dict(outcome.payload), sort_keys=True).encode("utf-8")
                ).hexdigest()
                committed_entry = journal_outcome(
                    self._journal,
                    component=FEDERATION_COMPONENT_ID,
                    request_identity=req_digest,
                    request_outcome=REQUEST_ANSWERED,
                    task_outcome=TASK_COMPLETED,
                    effect_state=EFFECT_STATE_CONFIRMED,
                    result_digest=payload_digest,
                    at=request.at,
                )
                self._journal.append(committed_entry)
                trace = EnvelopeTrace(FEDERATION_COMPONENT_ID, tuple(steps), True, "", None)
                response = CrossSurfaceFederationResponse(
                    request_id=request.request_id,
                    surface_hostname=request.surface_hostname,
                    family=surface.family,
                    plane_schema=request.plane_schema,
                    succeeded=True,
                    selected_engine=engine_id,
                    attempted_engines=tuple(attempted),
                    handshake_verdict=verdict,
                    preflight_report=preflight_report,
                    trace=trace,
                    frame=current_frame,
                    journal_entries=(intent_entry, committed_entry),
                    resync_state=resync_state,
                    payload=outcome.payload,
                    refusal=None,
                    latency_ms=total_latency_ms,
                    origin_lock_wait_ms=total_lock_wait_ms,
                )
                self._cached_responses[req_digest] = response
                return response

            if outcome.refusal is None or not may_recover(
                self._recovery_policy, outcome.refusal, frame.allowance
            ):
                break

        final_refusal = (
            last_outcome.refusal
            if last_outcome and last_outcome.refusal
            else envelope_refusal(
                "all_federation_engines_exhausted",
                "Every configured multi-surface backend dispatch engine failed to serve the projection.",
                "Inspect the engine health metrics and restore the static bundle or edge snapshot.",
                retry=RETRY_AFTER_WAIT,
                retry_after_seconds=5,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
            )
        )
        failed_entry = journal_outcome(
            self._journal,
            component=FEDERATION_COMPONENT_ID,
            request_identity=req_digest,
            request_outcome=REQUEST_OUTCOMES[-1],
            task_outcome=TASK_FAILED,
            effect_state=EFFECT_STATE_NONE,
            result_digest="",
            at=request.at,
        )
        self._journal.append(failed_entry)
        trace = EnvelopeTrace(FEDERATION_COMPONENT_ID, tuple(steps), True, ENGINE_SOURCE, final_refusal)
        return CrossSurfaceFederationResponse(
            request_id=request.request_id,
            surface_hostname=request.surface_hostname,
            family=surface.family,
            plane_schema=request.plane_schema,
            succeeded=False,
            selected_engine="",
            attempted_engines=tuple(attempted),
            handshake_verdict=verdict,
            preflight_report=preflight_report,
            trace=trace,
            frame=current_frame,
            journal_entries=(intent_entry, failed_entry),
            resync_state=resync_state,
            payload=None,
            refusal=final_refusal,
            latency_ms=total_latency_ms,
            origin_lock_wait_ms=total_lock_wait_ms,
        )


# ============================================================================
# Head-to-Head Benchmark & Security Probe Suite
# ============================================================================


def run_head_to_head_benchmark() -> dict[str, Any]:
    """Benchmark all 4 engines and their cascade fallback chain across 22 surfaces and adversarial probes."""
    surfaces = list(SURFACE_TOPOLOGY_REGISTRY.values())
    engine_summaries: list[dict[str, Any]] = []

    # 1. Benchmark each engine solo across all 22 startup surfaces (nominal load + burst writer contention)
    solo_configs = (
        (
            ENGINE_EDGE_MANIFEST,
            lambda: MultiSurfaceFederationOrchestrator(
                edge_engine=EdgeManifestFederationEngine(),
                engine_order=(ENGINE_EDGE_MANIFEST,),
            ),
        ),
        (
            ENGINE_HYBRID_SWR,
            lambda: MultiSurfaceFederationOrchestrator(
                swr_engine=HybridStaleWhileRevalidateEngine(),
                engine_order=(ENGINE_HYBRID_SWR,),
            ),
        ),
        (
            ENGINE_ORIGIN_GATEWAY,
            lambda: MultiSurfaceFederationOrchestrator(
                origin_engine=OriginScopedGatewayEngine(simulated_concurrent_writers=4),
                engine_order=(ENGINE_ORIGIN_GATEWAY,),
            ),
        ),
        (
            ENGINE_STATIC_FAILOVER,
            lambda: MultiSurfaceFederationOrchestrator(
                static_engine=StaticBundleFailoverEngine(),
                engine_order=(ENGINE_STATIC_FAILOVER,),
            ),
        ),
    )

    for engine_id, factory in solo_configs:
        orchestrator = factory()
        latencies: list[float] = []
        lock_waits: list[float] = []
        successes = 0
        for idx, surface in enumerate(surfaces):
            plane = surface.allowed_planes[0]
            req = CrossSurfaceFederationRequest(
                request_id=f"bench-{engine_id}-{idx}-{surface.surface_id}",
                surface_hostname=surface.hostname,
                plane_schema=plane,
                section_root=surface.section_root,
                staff_grant=surface.requires_staff_grant,
                principal_id="principal_bench_01" if plane == PLANE_IDENTITY_ENTITLEMENT else "",
            )
            resp = orchestrator.handle(req)
            latencies.append(resp.latency_ms)
            lock_waits.append(resp.origin_lock_wait_ms)
            if resp.succeeded:
                successes += 1
        sorted_lat = sorted(latencies)
        p95_idx = min(len(sorted_lat) - 1, int(len(sorted_lat) * 0.95))
        engine_summaries.append({
            "engine_id": engine_id,
            "requests": len(surfaces),
            "succeeded": successes,
            "success_rate": round(successes / len(surfaces), 4),
            "mean_latency_ms": round(sum(latencies) / len(latencies), 4),
            "p95_latency_ms": round(sorted_lat[p95_idx], 4),
            "mean_origin_lock_wait_ms": round(sum(lock_waits) / len(lock_waits), 4),
        })

    # 2. Cascade fallback chain under multi-tier degradation (Edge evicted -> SWR cold+breaker -> Origin lock -> Static)
    cascade_orchestrator = MultiSurfaceFederationOrchestrator(
        edge_engine=EdgeManifestFederationEngine(
            evicted_surfaces=frozenset({"agentfeeds.si", "agentfoundry.si", "skillsforgood.org"})
        ),
        swr_engine=HybridStaleWhileRevalidateEngine(
            origin_failures=4,
            circuit_failure_threshold=3,
            cold_surfaces=frozenset({"agentfoundry.si", "skillsforgood.org"}),
        ),
        origin_engine=OriginScopedGatewayEngine(
            simulated_concurrent_writers=10,
            lock_saturation_threshold=8,
        ),
        static_engine=StaticBundleFailoverEngine(),
    )
    cascade_results: list[dict[str, Any]] = []
    for idx, surface in enumerate(surfaces):
        plane = surface.allowed_planes[0]
        req = CrossSurfaceFederationRequest(
            request_id=f"cascade-{idx}-{surface.surface_id}",
            surface_hostname=surface.hostname,
            plane_schema=plane,
            section_root=surface.section_root,
            staff_grant=surface.requires_staff_grant,
            principal_id="principal_bench_01" if plane == PLANE_IDENTITY_ENTITLEMENT else "",
        )
        resp = cascade_orchestrator.handle(req)
        cascade_results.append({
            "surface_hostname": surface.hostname,
            "selected_engine": resp.selected_engine,
            "attempted_engines": list(resp.attempted_engines),
            "succeeded": resp.succeeded,
            "latency_ms": round(resp.latency_ms, 4),
        })

    # 3. Adversarial cross-surface security and stale-digest probes (known-wrong controls)
    probe_orchestrator = MultiSurfaceFederationOrchestrator()
    probes = (
        (
            "cookie_leakage_on_public_brand",
            CrossSurfaceFederationRequest(
                request_id="probe-cookie-agentfeeds",
                surface_hostname="agentfeeds.si",
                plane_schema=PLANE_FEED_DIGEST,
                has_session_cookie=True,
            ),
            "cross_surface_session_cookie_forbidden",
            LAYER_HANDSHAKE,
        ),
        (
            "staff_tool_on_public_brand",
            CrossSurfaceFederationRequest(
                request_id="probe-staff-agentstudios",
                surface_hostname="agentstudios.si",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
                invokes_staff_tool=True,
            ),
            "cross_surface_staff_tool_forbidden",
            LAYER_HANDSHAKE,
        ),
        (
            "account_mutation_on_public_good",
            CrossSurfaceFederationRequest(
                request_id="probe-mutate-skillsforgood",
                surface_hostname="skillsforgood.org",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
                mutates_account_state=True,
            ),
            "cross_surface_account_mutation_forbidden",
            LAYER_HANDSHAKE,
        ),
        (
            "external_idp_csp_on_afk_surface",
            CrossSurfaceFederationRequest(
                request_id="probe-csp-agentafk",
                surface_hostname="agentafk.si",
                plane_schema=PLANE_AFK_APPROVAL_GATE,
                includes_external_idp_csp=True,
            ),
            "cross_surface_external_idp_csp_forbidden",
            LAYER_HANDSHAKE,
        ),
        (
            "section_root_mismatch_on_showcase",
            CrossSurfaceFederationRequest(
                request_id="probe-section-deterministicskills",
                surface_hostname="deterministicskills.baltor.ai",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
                section_root="/wrong-section",
            ),
            "section_root_binding_mismatch",
            LAYER_PREFLIGHT,
        ),
        (
            "stale_release_digest_on_canonical_section",
            CrossSurfaceFederationRequest(
                request_id="probe-stale-digest-tools",
                surface_hostname="tools.baltor.ai",
                plane_schema=PLANE_CATALOGUE_PROJECTION,
                section_root="/tools",
                release_digest=STALE_RELEASE_DIGEST,
                served_release_digest=DEFAULT_RELEASE_DIGEST,
                allow_release_resync=False,
            ),
            "served_release_digest_mismatch",
            LAYER_PREFLIGHT,
        ),
        (
            "missing_staff_grant_on_systems_surface",
            CrossSurfaceFederationRequest(
                request_id="probe-staff-grant-systems",
                surface_hostname="systems.baltor.ai",
                plane_schema=PLANE_SYSTEMS_VIEW,
                staff_grant=False,
            ),
            "staff_grant_required",
            LAYER_ACCOUNT,
        ),
        (
            "missing_zero_cache_or_hsts_on_systems_surface",
            CrossSurfaceFederationRequest(
                request_id="probe-staff-headers-systems",
                surface_hostname="systems.baltor.ai",
                plane_schema=PLANE_SYSTEMS_VIEW,
                staff_grant=True,
                hsts_enabled=False,
                cache_control="public, max-age=3600",
            ),
            "staff_surface_security_headers_missing",
            LAYER_PREFLIGHT,
        ),
    )

    probe_results: list[dict[str, Any]] = []
    for probe_name, req, expected_code, expected_layer in probes:
        resp = probe_orchestrator.handle(req)
        actual_code = resp.refusal.code if resp.refusal else ""
        blocked_correctly = (
            not resp.succeeded
            and not resp.trace.engine_dispatched
            and actual_code == expected_code
            and resp.trace.refused_by == expected_layer
        )
        probe_results.append({
            "probe": probe_name,
            "surface_hostname": req.surface_hostname,
            "expected_refusal_code": expected_code,
            "actual_refusal_code": actual_code,
            "refused_by_layer": resp.trace.refused_by,
            "engine_dispatched": resp.trace.engine_dispatched,
            "blocked_before_engine": blocked_correctly,
        })

    return {
        "record_type": BENCHMARK_REPORT_RECORD,
        "surface_count": len(surfaces),
        "family_counts": {
            family: sum(1 for s in surfaces if s.family == family)
            for family in SURFACE_FAMILIES
        },
        "plane_count": len(SHARED_BACKEND_PLANES),
        "envelope_layers": list(COVERAGE_LAYERS),
        "site_map_alignment": verify_site_map_and_brand_alignment(),
        "engine_benchmarks": engine_summaries,
        "cascade_failover": {
            "total_surfaces": len(cascade_results),
            "succeeded": sum(1 for item in cascade_results if item["succeeded"]),
            "by_selected_engine": {
                eng_id: sum(1 for item in cascade_results if item["selected_engine"] == eng_id)
                for eng_id in FEDERATION_ENGINE_IDS
            },
            "results": cascade_results,
        },
        "security_probes": {
            "total_probes": len(probe_results),
            "all_blocked_before_engine": all(item["blocked_before_engine"] for item in probe_results),
            "probes": probe_results,
        },
    }


def self_test() -> dict[str, Any]:
    """Run deterministic self-tests for the multi-surface startup federation engine suite."""
    report = run_head_to_head_benchmark()
    checks = [
        ("twenty_two_surfaces_registered", report["surface_count"] == 22),
        ("site_map_alignment_holds", report["site_map_alignment"]["aligned"]),
        (
            "cascade_failover_zero_downtime",
            report["cascade_failover"]["succeeded"] == report["surface_count"],
        ),
        (
            "all_adversarial_probes_blocked_before_engine",
            report["security_probes"]["all_blocked_before_engine"],
        ),
    ]
    return {
        "passed": all(ok for _, ok in checks),
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "benchmark": report,
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2, sort_keys=True))
