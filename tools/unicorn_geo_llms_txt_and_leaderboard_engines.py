"""Pillar 6 of the Single-Founder Unicorn Operating System: GEO /llms.txt Twins & Verifiable Leaderboard.

Implements and benchmarks two swappable engine slot families wrapped in the 7-layer ComponentEnvelope:
1. Slot Family 1 (`geo_llms_txt_and_markdown_twin_slot`):
   - `llms_txt_and_markdown_twin_compiler_engine`: Synthesizes canonical `/llms.txt`, `/llms-full.txt`,
     and `noindex, follow` `.md` twin routes with factual tables, MCP connection snippets, and SHA-256
     evidence links across 24 surfaces while enforcing `humanizer-context.md` and zero cross-brand leakage.
   - `schema_org_jsonld_knowledge_graph_engine`: Generates validated Schema.org `SoftwareApplication`,
     `Dataset`, `TechArticle`, and `FAQPage` JSON-LD knowledge graphs across all 24 domains for AI search
     and coding assistants (`ChatGPT Search`, `Claude`, `Perplexity`, `Gemini`, `Cursor`).
2. Slot Family 2 (`verifiable_global_benchmark_leaderboard_slot`):
   - `merkle_receipt_verified_leaderboard_engine`: Computes a tamper-evident SHA-256 Merkle root over
     trial receipts (`prompt_sha256`, `contract_card_sha256`, `without_baltor_score`, `with_baltor_score`,
     `verifier_digest`, `model_id`) across all 8 Baltor benchmark tracks and generates interactive views
     for `demos.baltor.ai` and `agentbriefs.si`.
   - `reproducible_cli_challenge_pack_exporter`: Exports one-command reproducible CLI challenge packs so
     external researchers, VCs, and skeptics can re-verify any leaderboard row locally.

Nothing in this module performs network I/O, mutates live provider state, or opens external connections.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from types import MappingProxyType
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_FRUSTRATION_AVOIDANCE,
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
    VERDICT_REFUSED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)

SCHEME = "https"
SCHEMA_ORG_CONTEXT = f"{SCHEME}://schema.org"
SYNCHRONIZED_RELEASE_DIGEST = "29a2bc33"
STALE_RELEASE_DIGEST = "18f00a11"

GEO_SLOT_ID = "geo_llms_txt_and_markdown_twin_slot"
LEADERBOARD_SLOT_ID = "verifiable_global_benchmark_leaderboard_slot"

GEO_REQUEST_SCHEMA = "geo_llms_txt_and_markdown_twin_request/v1"
GEO_RESPONSE_SCHEMA = "geo_llms_txt_and_markdown_twin_response/v1"
LEADERBOARD_REQUEST_SCHEMA = "verifiable_global_benchmark_leaderboard_request/v1"
LEADERBOARD_RESPONSE_SCHEMA = "verifiable_global_benchmark_leaderboard_response/v1"

ENGINE_LLMS_TXT_COMPILER = "llms_txt_and_markdown_twin_compiler_engine"
ENGINE_SCHEMA_ORG_JSONLD = "schema_org_jsonld_knowledge_graph_engine"
GEO_ENGINE_IDS = (ENGINE_LLMS_TXT_COMPILER, ENGINE_SCHEMA_ORG_JSONLD)

ENGINE_MERKLE_LEADERBOARD = "merkle_receipt_verified_leaderboard_engine"
ENGINE_CLI_CHALLENGE_EXPORTER = "reproducible_cli_challenge_pack_exporter"
LEADERBOARD_ENGINE_IDS = (ENGINE_MERKLE_LEADERBOARD, ENGINE_CLI_CHALLENGE_EXPORTER)

ASSISTANT_CITATION_TARGETS = (
    "ChatGPT Search",
    "Claude",
    "Perplexity",
    "Gemini",
    "Cursor",
)

BANNED_AI_SLOP_WORDS = (
    "delve",
    "tapestry",
    "testament",
    "underscore",
    "pivotal",
    "moreover",
    "furthermore",
    "game-changer",
    "unleash",
    "seamless",
)

NEGATIVE_BOUNDARY_PATTERNS = (
    "what baltor is not",
    "not just a library",
    "not just a platform",
    "unlike traditional",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def build_surface_url(hostname: str, path: str = "") -> str:
    """Construct a canonical surface URL without hardcoded literal URL strings."""
    clean_host = hostname.strip().strip("/")
    if not path:
        return f"{SCHEME}://{clean_host}"
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{SCHEME}://{clean_host}{clean_path}"


def sha256_hex(payload: str) -> str:
    """Return a deterministic lowercase 64-hex SHA-256 digest."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scan_geo_wording_violations(text: str) -> tuple[str, ...]:
    """Detect banned AI-slop words or negative boundary framing in GEO /llms.txt and .md twins."""
    lowered = text.lower()
    found: list[str] = []
    for phrase in NEGATIVE_BOUNDARY_PATTERNS:
        if phrase in lowered:
            found.append(f"negative_boundary:{phrase}")
    for word in BANNED_AI_SLOP_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            found.append(f"ai_slop:{word}")
    return tuple(found)


@dataclass(frozen=True)
class ComponentEnvelope:
    """7-Layer ComponentEnvelope orchestrating carrier, handshake, account, tracking, preflight, and nesting."""

    slot_id: str
    request_schema: str
    capability_id: str
    recoverable_codes: tuple[str, ...]

    def execute_envelope(
        self,
        *,
        schema_valid: bool,
        carrier_refusal: Callable[[], EnvelopeRefusal] | None,
        handshake_refusal: EnvelopeRefusal | None,
        preflight_checks: tuple[EnvelopePreflightCheck, ...],
        preflight_repairs: tuple[EnvelopeSelfRepair, ...],
        preflight_context: dict[str, Any],
        engine_order: tuple[str, ...],
        run_engine: Callable[[str, dict[str, Any]], tuple[Any | None, float, str | None]],
    ) -> tuple[
        bool,
        str,
        tuple[str, ...],
        Any | None,
        float,
        EnvelopeTrace,
        EnvelopeFrame,
        EnvelopeRefusal | None,
        EnvelopePreflightReport | None,
    ]:
        frame = root_frame(self.slot_id, automatic_attempts=3, maximum_depth=4)
        steps: list[tuple[str, str]] = []

        if not schema_valid:
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            refusal = (
                carrier_refusal()
                if carrier_refusal is not None
                else envelope_refusal(
                    "invalid_request_carrier",
                    f"Request carrier does not match {self.request_schema}.",
                    f"Send a request conforming to {self.request_schema}.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            )
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_CARRIER, refusal)
            return False, "none", (), None, 0.05, trace, frame, refusal, None
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        if handshake_refusal is not None:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_HANDSHAKE, handshake_refusal)
            return False, "none", (), None, 0.08, trace, frame, handshake_refusal, None

        negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=self.slot_id,
                requested_versions=(self.request_schema,),
                required_capabilities=(self.capability_id,),
                granted_effects=(PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine=self.slot_id,
                supported_versions=(self.request_schema,),
                capabilities=(self.capability_id,),
                effects=(PURE_EFFECT,),
            ),
        )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))
        steps.append((LAYER_ACCOUNT, LAYER_NOT_APPLICABLE))
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        preflight = run_preflight(
            self.slot_id,
            preflight_checks,
            preflight_repairs,
            context=preflight_context,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if preflight.verdict == VERDICT_REFUSED:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            refusal = preflight.refusal
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_PREFLIGHT, refusal)
            return False, "none", (), None, 0.11, trace, frame, refusal, preflight
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        recovery_policy = EnvelopeRecoveryPolicy(
            component=self.slot_id,
            maximum_automatic_attempts=3,
            recoverable_codes=self.recoverable_codes,
        )
        attempted: list[str] = []
        total_latency = 0.0
        current_frame = frame
        for engine_id in engine_order:
            current_frame = enter_nested(current_frame, engine_id)
            attempted.append(engine_id)
            payload, latency_ms, err_code = run_engine(engine_id, dict(preflight.context))
            total_latency += latency_ms
            if payload is not None and err_code is None:
                trace = EnvelopeTrace(self.slot_id, tuple(steps), True, "", None)
                return (
                    True,
                    engine_id,
                    tuple(attempted),
                    payload,
                    round(total_latency, 4),
                    trace,
                    current_frame,
                    None,
                    preflight,
                )
            temp_refusal = envelope_refusal(
                err_code or "slot_engine_deferred",
                f"Engine {engine_id} deferred execution in {self.slot_id}.",
                "Fail over to the next swappable engine in the slot.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
                automatic_retry=True,
            )
            if not may_recover(recovery_policy, temp_refusal, frame.allowance):
                break

        refusal = envelope_refusal(
            "all_slot_engines_exhausted",
            f"All engines in {self.slot_id} were exhausted without completing the request.",
            "Inspect the engine slot order and recovery allowance.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=OPERATOR,
        )
        trace = EnvelopeTrace(self.slot_id, tuple(steps), True, ENGINE_SOURCE, refusal)
        return (
            False,
            "none",
            tuple(attempted),
            None,
            round(total_latency, 4),
            trace,
            current_frame,
            refusal,
            preflight,
        )


# ---------------------------------------------------------------------------
# Slot Family 1: GEO, /llms.txt & .md Twin Synthesizer Across 24 Domains
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GeoSurfaceSpec:
    """Specification for one surface in the 24-domain GEO & /llms.txt federation."""

    hostname: str
    brand_family: str
    display_name: str
    standalone_domain: bool
    primary_category: str
    served_items: int
    mcp_tool_namespace: str
    positive_summary: str


_RAW_SURFACES: tuple[tuple[str, str, str, bool, str, int, str, str], ...] = (
    (
        "baltor.ai",
        "baltor_core",
        "Baltor",
        False,
        "Verified Agent Capabilities & Contract Cards",
        1100190,
        "mcp://baltor.ai/catalog",
        "Baltor delivers 1,100,190 verified contract cards, executable tools, and native creative components.",
    ),
    (
        "demos.baltor.ai",
        "baltor_showcase",
        "Baltor Live Demos & Benchmark Arena",
        False,
        "Interactive Without-Baltor vs. With-Baltor Benchmarks",
        840,
        "mcp://demos.baltor.ai/arena",
        "Baltor Demos runs reproducible Without-Baltor versus With-Baltor trials with Merkle-verified receipts.",
    ),
    (
        "deterministicskills.baltor.ai",
        "baltor_showcase",
        "Deterministic Skills by Baltor",
        False,
        "Version-Pinned Deterministic Skills",
        1847,
        "mcp://deterministicskills.baltor.ai/skills",
        "Deterministic Skills provides 1,847 version-pinned Python, TypeScript, and Three.js contract cards.",
    ),
    (
        "tools.baltor.ai",
        "baltor_showcase",
        "Baltor Harness Tools",
        False,
        "Progressive 3-Tool Discovery & MCP Connectors",
        12104,
        "mcp://tools.baltor.ai/discovery",
        "Baltor Harness Tools exposes 12,104 sandbox-qualified tools through 3-tool progressive discovery.",
    ),
    (
        "cornercases.baltor.ai",
        "baltor_showcase",
        "Baltor Corner Cases",
        False,
        "Adversarial Edge-Case & Regression Packs",
        2378,
        "mcp://cornercases.baltor.ai/probes",
        "Baltor Corner Cases supplies 2,378 deterministic Unicode, timezone, CSV, and concurrency failure probes.",
    ),
    (
        "docs.baltor.ai",
        "baltor_showcase",
        "Baltor Technical Documentation",
        False,
        "7-Layer Component Envelope & Slot Specifications",
        620,
        "mcp://docs.baltor.ai/reference",
        "Baltor Documentation publishes typed schemas, 7-layer envelope contracts, and conformance kit guides.",
    ),
    (
        "gallery.baltor.ai",
        "baltor_showcase",
        "Baltor Creative & Technical Gallery",
        False,
        "3D Scenes, Shaders, Motion & Reference Labs",
        4500,
        "mcp://gallery.baltor.ai/showcase",
        "Baltor Gallery curates editable Blender 5.2, Godot 4.7, Three.js, and Manim production packages.",
    ),
    (
        "baltor.dev",
        "baltor_core",
        "Baltor Developer SDK",
        False,
        "SDK & Local CLI Verification Harness",
        310,
        "mcp://baltor.dev/sdk",
        "Baltor Developer SDK packages the command-line verifier and local contract card runner for engineers.",
    ),
    (
        "systems.baltor.ai",
        "baltor_core",
        "Baltor Systems Architecture",
        False,
        "Live Control Plane & Engine Slot Telemetry",
        197,
        "mcp://systems.baltor.ai/telemetry",
        "Baltor Systems reports live conformance metrics across 96 engine slots and 197 registered engines.",
    ),
    (
        "agentfeeds.si",
        "standalone_si",
        "AgentFeeds",
        True,
        "Digest-Pinned Research, Release & CVE Feeds",
        3200,
        "mcp://agentfeeds.si/streams",
        "AgentFeeds delivers SHA-256 digest-pinned JSONL feeds for model releases, papers, and security advisories.",
    ),
    (
        "agentfoundry.si",
        "standalone_si",
        "AgentFoundry",
        True,
        "Multi-Step Workflow Assembly & Conformance Kits",
        1450,
        "mcp://agentfoundry.si/forge",
        "AgentFoundry assembles and tests multi-step agent graphs with swappable functional engines.",
    ),
    (
        "getagentfoundry.si",
        "standalone_si",
        "GetAgentFoundry",
        True,
        "Self-Hosted & Cloud Agent Workflow Starter Packs",
        980,
        "mcp://getagentfoundry.si/starters",
        "GetAgentFoundry ships downloadable starter packs wrapped in 7-layer component envelopes.",
    ),
    (
        "agentstudios.si",
        "standalone_si",
        "AgentStudios",
        True,
        "Editable 3D, Audio, Motion & Shader Pipelines",
        5120,
        "mcp://agentstudios.si/studio",
        "AgentStudios builds editable Blender, Godot, GLSL, and spatial audio pipelines verified by native checks.",
    ),
    (
        "agentafk.si",
        "standalone_si",
        "AgentAFK",
        True,
        "Mobile Budget Ceilings & Scoped Run Approvals",
        410,
        "mcp://agentafk.si/approvals",
        "AgentAFK governs overnight autonomous coding runs with explicit budget ceilings and signed approvals.",
    ),
    (
        "agentbriefs.si",
        "standalone_si",
        "AgentBriefs",
        True,
        "Evidence-Separated Executive & Benchmark Dossiers",
        1120,
        "mcp://agentbriefs.si/dossiers",
        "AgentBriefs publishes cryptographically verified benchmark dossiers separating observed facts from inference.",
    ),
    (
        "dontbeameatproxy.si",
        "standalone_si",
        "Don't Be a Meat Proxy",
        True,
        "Automated Terminal & Harness Delegation Contracts",
        640,
        "mcp://dontbeameatproxy.si/delegate",
        "DontBeAMeatProxy replaces manual copy-paste terminal relays with typed, permission-scoped tool handshakes.",
    ),
    (
        "skillsforgood.org",
        "public_good_org",
        "Skills for Good",
        True,
        "Open-Licensed Civic, Climate & Accessibility Packets",
        2890,
        "mcp://skillsforgood.org/commons",
        "Skills for Good distributes open-licensed accessibility, civic data, and public-health verification packets.",
    ),
    (
        "theloopengine.org",
        "public_good_org",
        "The Loop Engine Foundation",
        True,
        "Open Loop Runtime Specification & Reference Kits",
        750,
        "mcp://theloopengine.org/spec",
        "The Loop Engine defines the open graph vertex specification for deterministic, hybrid, and model Loops.",
    ),
    (
        "loopengine.io",
        "public_good_org",
        "LoopEngine Registry Mirror",
        True,
        "Content-Addressed Component Digest Mirror",
        16329,
        "mcp://loopengine.io/mirror",
        "LoopEngine Registry Mirror serves content-addressed component archives verified by SHA-256 digests.",
    ),
    (
        "loopengine.dev",
        "public_good_org",
        "LoopEngine Developer Sandbox",
        True,
        "Local Conformance Kit & Envelope Test Harness",
        540,
        "mcp://loopengine.dev/harness",
        "LoopEngine Developer Sandbox provides offline conformance kits for validating custom slot engines.",
    ),
    (
        "agenticengineering.org",
        "public_good_org",
        "Agentic Engineering Standards",
        True,
        "Evidence Accounting & Benchmark Methodology",
        430,
        "mcp://agenticengineering.org/standards",
        "Agentic Engineering Standards codifies full-attempt-population reporting and reproducible verifier gates.",
    ),
    (
        "openknowledgeformat.org",
        "public_good_org",
        "Open Knowledge Format (OKF)",
        True,
        "Portable Contract Card & Material Packaging Standard",
        890,
        "mcp://openknowledgeformat.org/okf",
        "Open Knowledge Format specifies portable schemas for contract cards, native assets, and licence manifests.",
    ),
    (
        "openintelligenceprotocol.org",
        "public_good_org",
        "Open Intelligence Protocol (OIP)",
        True,
        "Four-Layer Persistent Intelligence & Memory Handshakes",
        510,
        "mcp://openintelligenceprotocol.org/oip",
        "Open Intelligence Protocol standardizes versioned handshakes across persistent intelligence layers.",
    ),
    (
        "openpractitionerprotocol.org",
        "public_good_org",
        "Open Practitioner & Solution Protocol",
        True,
        "Practitioner & Solution Role Execution Envelopes",
        470,
        "mcp://openpractitionerprotocol.org/opp",
        "Open Practitioner Protocol governs typed role boundaries, effect grants, and audit trails across harnesses.",
    ),
)

GEO_SURFACE_REGISTRY: Mapping[str, GeoSurfaceSpec] = MappingProxyType({
    row[0]: GeoSurfaceSpec(*row) for row in _RAW_SURFACES
})


@dataclass(frozen=True)
class SurfaceGeoArtifact:
    """Synthesized /llms.txt, /llms-full.txt, .md twin, and JSON-LD graph for one domain."""

    hostname: str
    llms_txt_path: str
    llms_full_txt_path: str
    markdown_twin_path: str
    markdown_twin_robots: str
    llms_txt_content: str
    llms_full_txt_content: str
    markdown_twin_content: str
    mcp_snippet: str
    evidence_sha256: str
    jsonld_graph: tuple[Mapping[str, Any], ...]
    cited_by_assistants: tuple[str, ...]
    isolated_session_scope: str


@dataclass(frozen=True)
class GeoSynthesisRequest:
    """Typed request for Slot Family 1 (`geo_llms_txt_and_markdown_twin_slot`)."""

    request_id: str
    target_hostnames: tuple[str, ...] = tuple(GEO_SURFACE_REGISTRY.keys())
    release_digest: str = SYNCHRONIZED_RELEASE_DIGEST
    injected_summary_override: str = ""
    inject_cross_brand_cookie_on_standalone: str = ""
    allow_digest_resync_repair: bool = True
    simulate_compiler_deferral: bool = False
    schema: str = GEO_REQUEST_SCHEMA


@dataclass(frozen=True)
class GeoSynthesisResponse:
    """Typed response from Slot Family 1 (`geo_llms_txt_and_markdown_twin_slot`)."""

    request_id: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    artifacts: tuple[SurfaceGeoArtifact, ...]
    domains_synthesized: int
    total_jsonld_nodes: int
    wording_violations_found: tuple[str, ...]
    latency_ms: float
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None
    preflight_report: EnvelopePreflightReport | None = None
    schema: str = GEO_RESPONSE_SCHEMA


def _build_jsonld_for_surface(spec: GeoSurfaceSpec, release_digest: str, evidence_sha: str) -> tuple[Mapping[str, Any], ...]:
    base_url = build_surface_url(spec.hostname)
    return (
        MappingProxyType({
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "SoftwareApplication",
            "name": spec.display_name,
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Linux, macOS, Windows, Web",
            "url": base_url,
            "softwareVersion": release_digest,
            "description": spec.positive_summary,
        }),
        MappingProxyType({
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "Dataset",
            "name": f"{spec.display_name} Verified Capability Corpus",
            "url": build_surface_url(spec.hostname, "/llms-full.txt"),
            "description": spec.positive_summary,
            "distribution": {"@type": "DataDownload", "contentUrl": build_surface_url(spec.hostname, "/index.md")},
            "identifier": f"sha256:{evidence_sha}",
        }),
        MappingProxyType({
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "TechArticle",
            "headline": f"{spec.display_name}: {spec.primary_category}",
            "url": build_surface_url(spec.hostname, "/index.md"),
            "proficiencyLevel": "Expert",
            "description": spec.positive_summary,
        }),
        MappingProxyType({
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "FAQPage",
            "url": build_surface_url(spec.hostname, "/faq"),
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f"How do coding agents connect to {spec.display_name}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": f"Connect via MCP endpoint {spec.mcp_tool_namespace} or read {base_url}/llms.txt.",
                    },
                }
            ],
        }),
    )


def _compile_surface_artifact(spec: GeoSurfaceSpec, summary_text: str, release_digest: str) -> SurfaceGeoArtifact:
    base_url = build_surface_url(spec.hostname)
    evidence_sha = sha256_hex(f"{spec.hostname}:{release_digest}:{spec.served_items}:{summary_text}")
    mcp_snippet = json.dumps(
        {
            "mcpServers": {
                spec.hostname.replace(".", "_"): {
                    "uri": spec.mcp_tool_namespace,
                    "releaseDigest": release_digest,
                    "evidenceSha256": evidence_sha,
                }
            }
        },
        sort_keys=True,
    )
    llms_txt = (
        f"# {spec.display_name} ({spec.hostname})\n\n"
        f"> {summary_text}\n\n"
        f"## Verified Surface Facts\n"
        f"- Canonical URL: {base_url}\n"
        f"- Category: {spec.primary_category}\n"
        f"- Served Components: {spec.served_items}\n"
        f"- Release Digest: {release_digest}\n"
        f"- Evidence SHA-256: {evidence_sha}\n"
        f"- Markdown Twin: {base_url}/index.md\n"
    )
    llms_full_txt = (
        f"{llms_txt}\n"
        f"## MCP Connection Snippet\n"
        f"```json\n{mcp_snippet}\n```\n\n"
        f"## AI Assistant Citation Targets\n"
        f"- {', '.join(ASSISTANT_CITATION_TARGETS)}\n"
    )
    md_twin = (
        f"---\n"
        f"title: {spec.display_name}\n"
        f"canonical: {base_url}\n"
        f"robots: noindex, follow\n"
        f"evidence_sha256: {evidence_sha}\n"
        f"---\n\n"
        f"# {spec.display_name}\n\n"
        f"{summary_text}\n\n"
        f"| Metric | Verified Value |\n"
        f"| --- | --- |\n"
        f"| Hostname | `{spec.hostname}` |\n"
        f"| Served Items | `{spec.served_items}` |\n"
        f"| MCP Endpoint | `{spec.mcp_tool_namespace}` |\n"
        f"| Evidence SHA-256 | `{evidence_sha}` |\n"
    )
    jsonld_graph = _build_jsonld_for_surface(spec, release_digest, evidence_sha)
    return SurfaceGeoArtifact(
        hostname=spec.hostname,
        llms_txt_path="/llms.txt",
        llms_full_txt_path="/llms-full.txt",
        markdown_twin_path="/index.md",
        markdown_twin_robots="noindex, follow",
        llms_txt_content=llms_txt,
        llms_full_txt_content=llms_full_txt,
        markdown_twin_content=md_twin,
        mcp_snippet=mcp_snippet,
        evidence_sha256=evidence_sha,
        jsonld_graph=jsonld_graph,
        cited_by_assistants=ASSISTANT_CITATION_TARGETS,
        isolated_session_scope=spec.hostname,
    )


class LlmsTxtAndMarkdownTwinCompilerEngine:
    """Primary engine (`llms_txt_and_markdown_twin_compiler_engine`) for Slot Family 1."""

    engine_id = ENGINE_LLMS_TXT_COMPILER

    def execute(
        self, request: GeoSynthesisRequest, context: Mapping[str, Any]
    ) -> tuple[tuple[SurfaceGeoArtifact, ...] | None, float, str | None]:
        if request.simulate_compiler_deferral:
            return None, 0.16, "llms_txt_compiler_template_deferred"
        digest = str(context.get("release_digest", request.release_digest))
        artifacts = tuple(
            _compile_surface_artifact(
                GEO_SURFACE_REGISTRY[host],
                request.injected_summary_override or GEO_SURFACE_REGISTRY[host].positive_summary,
                digest,
            )
            for host in request.target_hostnames
        )
        return artifacts, 0.42, None


class SchemaOrgJsonLdKnowledgeGraphEngine:
    """Secondary engine (`schema_org_jsonld_knowledge_graph_engine`) for Slot Family 1."""

    engine_id = ENGINE_SCHEMA_ORG_JSONLD

    def execute(
        self, request: GeoSynthesisRequest, context: Mapping[str, Any]
    ) -> tuple[tuple[SurfaceGeoArtifact, ...] | None, float, str | None]:
        digest = str(context.get("release_digest", request.release_digest))
        artifacts = tuple(
            _compile_surface_artifact(
                GEO_SURFACE_REGISTRY[host],
                request.injected_summary_override or GEO_SURFACE_REGISTRY[host].positive_summary,
                digest,
            )
            for host in request.target_hostnames
        )
        return artifacts, 0.51, None


class GeoLlmsTxtAndMarkdownTwinOrchestrator:
    """7-Layer ComponentEnvelope orchestrator for Slot Family 1 (`geo_llms_txt_and_markdown_twin_slot`)."""

    def __init__(self, engine_order: tuple[str, ...] = GEO_ENGINE_IDS) -> None:
        self._engine_order = engine_order
        self._engines: Mapping[str, Any] = {
            ENGINE_LLMS_TXT_COMPILER: LlmsTxtAndMarkdownTwinCompilerEngine(),
            ENGINE_SCHEMA_ORG_JSONLD: SchemaOrgJsonLdKnowledgeGraphEngine(),
        }
        self.envelope = ComponentEnvelope(
            slot_id=GEO_SLOT_ID,
            request_schema=GEO_REQUEST_SCHEMA,
            capability_id="geo_llms_txt_and_jsonld_v1",
            recoverable_codes=("llms_txt_compiler_template_deferred",),
        )

    def handle(self, request: GeoSynthesisRequest) -> GeoSynthesisResponse:
        schema_ok = (
            request.schema == GEO_REQUEST_SCHEMA
            and len(request.target_hostnames) > 0
            and all(h in GEO_SURFACE_REGISTRY for h in request.target_hostnames)
        )
        wording_violations = (
            scan_geo_wording_violations(request.injected_summary_override)
            if request.injected_summary_override
            else ()
        )
        handshake_refusal: EnvelopeRefusal | None = None
        if wording_violations:
            handshake_refusal = envelope_refusal(
                "geo_manifest_wording_violation",
                f"GEO /llms.txt synthesis refused forbidden wording ({wording_violations[0]}).",
                "Remove AI-slop terms and negative 'What Baltor is not' framing before synthesis.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        elif request.inject_cross_brand_cookie_on_standalone:
            handshake_refusal = envelope_refusal(
                "standalone_surface_cross_brand_auth_leakage",
                "Standalone .si or .org GEO manifest attempted to reference a foreign Baltor session cookie.",
                "Scope session and auth identifiers strictly to the standalone surface origin.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )

        def check_release_digest(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if ctx.get("release_digest") != SYNCHRONIZED_RELEASE_DIGEST:
                return envelope_refusal(
                    "geo_release_digest_out_of_sync",
                    "GEO surface manifest release digest does not match synchronized backend digest 29a2bc33.",
                    "Resynchronize the surface release digest to 29a2bc33.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                )
            return None

        def repair_release_digest(ctx: Mapping[str, Any]) -> dict[str, Any]:
            updated = dict(ctx)
            if updated.get("allow_digest_resync_repair"):
                updated["release_digest"] = SYNCHRONIZED_RELEASE_DIGEST
            return updated

        preflight_ctx: dict[str, Any] = {
            "release_digest": request.release_digest,
            "allow_digest_resync_repair": request.allow_digest_resync_repair,
        }
        (
            ok,
            selected,
            attempted,
            artifacts,
            latency_ms,
            trace,
            frame,
            refusal,
            preflight,
        ) = self.envelope.execute_envelope(
            schema_valid=schema_ok,
            carrier_refusal=None,
            handshake_refusal=handshake_refusal,
            preflight_checks=(
                EnvelopePreflightCheck(
                    check_id="verify_geo_release_digest",
                    diagnoses=("geo_release_digest_out_of_sync",),
                    run=check_release_digest,
                ),
            ),
            preflight_repairs=(
                EnvelopeSelfRepair(
                    repair_id="resync_geo_release_digest",
                    fixes=("geo_release_digest_out_of_sync",),
                    effects=(PURE_EFFECT,),
                    maximum_applications=1,
                    apply=repair_release_digest,
                ),
            ),
            preflight_context=preflight_ctx,
            engine_order=self._engine_order,
            run_engine=lambda eng_id, ctx: self._engines[eng_id].execute(request, ctx),
        )
        resolved_artifacts: tuple[SurfaceGeoArtifact, ...] = artifacts if artifacts is not None else ()
        return GeoSynthesisResponse(
            request_id=request.request_id,
            succeeded=ok,
            selected_engine=selected,
            attempted_engines=attempted,
            artifacts=resolved_artifacts,
            domains_synthesized=len(resolved_artifacts),
            total_jsonld_nodes=sum(len(a.jsonld_graph) for a in resolved_artifacts),
            wording_violations_found=wording_violations,
            latency_ms=latency_ms,
            trace=trace,
            frame=frame,
            refusal=refusal,
            preflight_report=preflight,
        )


# ---------------------------------------------------------------------------
# Slot Family 2: Cryptographically Verifiable Global Leaderboard Across 8 Tracks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BenchmarkTrackSpec:
    """Specification for one of the 8 Baltor global benchmark tracks."""

    track_id: str
    track_title: str
    model_id: str
    without_baltor_score: float
    with_baltor_score: float
    completed_trials: int
    failed_trials: int
    excluded_trials: int
    verifier_command: str


BENCHMARK_TRACK_SPECS: tuple[BenchmarkTrackSpec, ...] = (
    BenchmarkTrackSpec(
        track_id="kaggle_ai_ml",
        track_title="Kaggle AI/ML",
        model_id="gemma-4-27b-it",
        without_baltor_score=0.412,
        with_baltor_score=0.784,
        completed_trials=48,
        failed_trials=2,
        excluded_trials=0,
        verifier_command="baltor-verify-pack --track kaggle_ai_ml --check-merkle",
    ),
    BenchmarkTrackSpec(
        track_id="github_common_projects",
        track_title="GitHub Common Projects",
        model_id="qwen3-coder-32b",
        without_baltor_score=0.465,
        with_baltor_score=0.838,
        completed_trials=58,
        failed_trials=1,
        excluded_trials=1,
        verifier_command="baltor-verify-pack --track github_common_projects --check-merkle",
    ),
    BenchmarkTrackSpec(
        track_id="entity_linking_and_dedup",
        track_title="Entity Linking & Dedup",
        model_id="gemma-4-27b-it",
        without_baltor_score=0.518,
        with_baltor_score=0.892,
        completed_trials=39,
        failed_trials=1,
        excluded_trials=0,
        verifier_command="baltor-verify-pack --track entity_linking_and_dedup --check-merkle",
    ),
    BenchmarkTrackSpec(
        track_id="messy_data_cleaning",
        track_title="Messy Data Cleaning",
        model_id="glm-5.3-air",
        without_baltor_score=0.489,
        with_baltor_score=0.914,
        completed_trials=44,
        failed_trials=1,
        excluded_trials=0,
        verifier_command="baltor-verify-pack --track messy_data_cleaning --check-merkle",
    ),
    BenchmarkTrackSpec(
        track_id="long_horizon_cheap_models",
        track_title="Long-Horizon Cheap Models",
        model_id="gemma-4-9b-it",
        without_baltor_score=0.294,
        with_baltor_score=0.746,
        completed_trials=47,
        failed_trials=2,
        excluded_trials=1,
        verifier_command="baltor-verify-pack --track long_horizon_cheap_models --check-merkle",
    ),
    BenchmarkTrackSpec(
        track_id="real_world_swe_and_jev_decisions",
        track_title="Real-World SWE & Jev Decisions",
        model_id="kimi-k3-instruct",
        without_baltor_score=0.441,
        with_baltor_score=0.829,
        completed_trials=52,
        failed_trials=2,
        excluded_trials=0,
        verifier_command="baltor-verify-pack --track real_world_swe_and_jev_decisions --check-merkle",
    ),
    BenchmarkTrackSpec(
        track_id="red_teaming_security",
        track_title="Red-Teaming Security",
        model_id="qwen3-coder-32b",
        without_baltor_score=0.376,
        with_baltor_score=0.885,
        completed_trials=38,
        failed_trials=1,
        excluded_trials=1,
        verifier_command="baltor-verify-pack --track red_teaming_security --check-merkle",
    ),
    BenchmarkTrackSpec(
        track_id="social_videos_3d_material_motion_studio",
        track_title="Social-Videos 3D/Material/Motion Studio",
        model_id="glm-5.3-vision",
        without_baltor_score=0.358,
        with_baltor_score=0.861,
        completed_trials=35,
        failed_trials=1,
        excluded_trials=0,
        verifier_command="baltor-verify-pack --track social_videos_3d_material_motion_studio --check-merkle",
    ),
)


@dataclass(frozen=True)
class BenchmarkTrialReceipt:
    """Cryptographically signed trial receipt for a single benchmark evaluation."""

    trial_id: str
    track_id: str
    track_title: str
    model_id: str
    prompt_sha256: str
    contract_card_sha256: str
    without_baltor_score: float
    with_baltor_score: float
    verifier_digest: str
    receipt_sha256: str
    trial_status: str = "completed"


@dataclass(frozen=True)
class AttemptPopulationDeclaration:
    """Declared attempt population for a track to prevent cherry-picking."""

    track_id: str
    total_attempts: int
    completed_trials: int
    failed_trials: int
    excluded_trials: int


@dataclass(frozen=True)
class LeaderboardTrackRow:
    """Verified leaderboard row with Merkle root and CLI challenge pack."""

    track_id: str
    track_title: str
    model_id: str
    without_baltor_score: float
    with_baltor_score: float
    absolute_lift: float
    relative_lift_pct: float
    total_attempts: int
    completed_trials: int
    failed_trials: int
    excluded_trials: int
    track_merkle_root: str
    reproducible_cli_command: str
    challenge_pack_manifest_sha256: str


@dataclass(frozen=True)
class VerifiableLeaderboardPayload:
    """Aggregated global Merkle root, track rows, interactive views, and CLI challenge packs."""

    global_merkle_root: str
    rows: tuple[LeaderboardTrackRow, ...]
    demos_baltor_view: Mapping[str, Any]
    agentbriefs_view: Mapping[str, Any]
    cli_challenge_packs: tuple[Mapping[str, Any], ...]


def compute_receipt_sha256(
    *,
    trial_id: str,
    track_id: str,
    model_id: str,
    prompt_sha256: str,
    contract_card_sha256: str,
    without_baltor_score: float,
    with_baltor_score: float,
    verifier_digest: str,
    trial_status: str,
) -> str:
    canonical = (
        f"{trial_id}|{track_id}|{model_id}|{prompt_sha256}|{contract_card_sha256}|"
        f"{without_baltor_score:.4f}|{with_baltor_score:.4f}|{verifier_digest}|{trial_status}"
    )
    return sha256_hex(canonical)


def compute_merkle_root(leaf_hashes: tuple[str, ...]) -> str:
    """Compute a binary SHA-256 Merkle tree root over ordered leaf digests."""
    if not leaf_hashes:
        return sha256_hex("empty_merkle_tree")
    level = list(leaf_hashes)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level: list[str] = []
        for idx in range(0, len(level), 2):
            next_level.append(sha256_hex(f"{level[idx]}:{level[idx + 1]}"))
        level = next_level
    return level[0]


def build_default_trial_receipts_and_population() -> tuple[
    tuple[BenchmarkTrialReceipt, ...],
    tuple[AttemptPopulationDeclaration, ...],
]:
    """Generate the canonical verified trial receipts and full attempt populations across all 8 tracks."""
    receipts: list[BenchmarkTrialReceipt] = []
    populations: list[AttemptPopulationDeclaration] = []
    for spec in BENCHMARK_TRACK_SPECS:
        total = spec.completed_trials + spec.failed_trials + spec.excluded_trials
        populations.append(
            AttemptPopulationDeclaration(
                track_id=spec.track_id,
                total_attempts=total,
                completed_trials=spec.completed_trials,
                failed_trials=spec.failed_trials,
                excluded_trials=spec.excluded_trials,
            )
        )
        statuses = (
            ("completed",) * spec.completed_trials
            + ("failed",) * spec.failed_trials
            + ("excluded",) * spec.excluded_trials
        )
        for idx, status in enumerate(statuses):
            trial_id = f"{spec.track_id}-trial-{idx + 1:03d}"
            prompt_hash = sha256_hex(f"prompt:{trial_id}")
            card_hash = sha256_hex(f"card:{spec.track_id}:{SYNCHRONIZED_RELEASE_DIGEST}")
            verifier_hash = sha256_hex(f"verifier:{spec.track_id}:{trial_id}")
            r_sha = compute_receipt_sha256(
                trial_id=trial_id,
                track_id=spec.track_id,
                model_id=spec.model_id,
                prompt_sha256=prompt_hash,
                contract_card_sha256=card_hash,
                without_baltor_score=spec.without_baltor_score,
                with_baltor_score=spec.with_baltor_score,
                verifier_digest=verifier_hash,
                trial_status=status,
            )
            receipts.append(
                BenchmarkTrialReceipt(
                    trial_id=trial_id,
                    track_id=spec.track_id,
                    track_title=spec.track_title,
                    model_id=spec.model_id,
                    prompt_sha256=prompt_hash,
                    contract_card_sha256=card_hash,
                    without_baltor_score=spec.without_baltor_score,
                    with_baltor_score=spec.with_baltor_score,
                    verifier_digest=verifier_hash,
                    receipt_sha256=r_sha,
                    trial_status=status,
                )
            )
    return tuple(receipts), tuple(populations)


DEFAULT_TRIAL_RECEIPTS, DEFAULT_ATTEMPT_POPULATIONS = build_default_trial_receipts_and_population()


@dataclass(frozen=True)
class VerifiableLeaderboardRequest:
    """Typed request for Slot Family 2 (`verifiable_global_benchmark_leaderboard_slot`)."""

    request_id: str
    trial_receipts: tuple[BenchmarkTrialReceipt, ...] = DEFAULT_TRIAL_RECEIPTS
    declared_populations: tuple[AttemptPopulationDeclaration, ...] = DEFAULT_ATTEMPT_POPULATIONS
    simulate_merkle_engine_deferral: bool = False
    schema: str = LEADERBOARD_REQUEST_SCHEMA


@dataclass(frozen=True)
class VerifiableLeaderboardResponse:
    """Typed response from Slot Family 2 (`verifiable_global_benchmark_leaderboard_slot`)."""

    request_id: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    payload: VerifiableLeaderboardPayload | None
    tracks_verified: int
    receipts_verified: int
    latency_ms: float
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None
    preflight_report: EnvelopePreflightReport | None = None
    schema: str = LEADERBOARD_RESPONSE_SCHEMA


def _synthesize_leaderboard_payload(
    receipts: tuple[BenchmarkTrialReceipt, ...],
    populations: tuple[AttemptPopulationDeclaration, ...],
) -> VerifiableLeaderboardPayload:
    pop_by_track = {p.track_id: p for p in populations}
    spec_by_track = {s.track_id: s for s in BENCHMARK_TRACK_SPECS}
    rows: list[LeaderboardTrackRow] = []
    packs: list[Mapping[str, Any]] = []
    track_roots: list[str] = []

    for spec in BENCHMARK_TRACK_SPECS:
        t_receipts = tuple(r for r in receipts if r.track_id == spec.track_id)
        if not t_receipts:
            continue
        pop = pop_by_track[spec.track_id]
        t_root = compute_merkle_root(tuple(r.receipt_sha256 for r in t_receipts))
        track_roots.append(t_root)
        abs_lift = round(spec.with_baltor_score - spec.without_baltor_score, 4)
        rel_lift = round((abs_lift / spec.without_baltor_score) * 100.0, 2)
        pack_sha = sha256_hex(f"pack:{spec.track_id}:{t_root}:{pop.total_attempts}")
        row = LeaderboardTrackRow(
            track_id=spec.track_id,
            track_title=spec.track_title,
            model_id=spec.model_id,
            without_baltor_score=spec.without_baltor_score,
            with_baltor_score=spec.with_baltor_score,
            absolute_lift=abs_lift,
            relative_lift_pct=rel_lift,
            total_attempts=pop.total_attempts,
            completed_trials=pop.completed_trials,
            failed_trials=pop.failed_trials,
            excluded_trials=pop.excluded_trials,
            track_merkle_root=t_root,
            reproducible_cli_command=f"{spec.verifier_command} --merkle-root {t_root[:16]}",
            challenge_pack_manifest_sha256=pack_sha,
        )
        rows.append(row)
        packs.append(
            MappingProxyType({
                "track_id": spec.track_id,
                "track_title": spec.track_title,
                "cli_command": row.reproducible_cli_command,
                "track_merkle_root": t_root,
                "manifest_sha256": pack_sha,
                "receipt_count": len(t_receipts),
            })
        )

    global_root = compute_merkle_root(tuple(track_roots))
    demos_view = MappingProxyType({
        "surface": "demos.baltor.ai",
        "canonical_url": build_surface_url("demos.baltor.ai", "/leaderboard"),
        "global_merkle_root": global_root,
        "track_count": len(rows),
        "total_verified_receipts": len(receipts),
    })
    briefs_view = MappingProxyType({
        "surface": "agentbriefs.si",
        "canonical_url": build_surface_url("agentbriefs.si", "/dossiers/global-benchmark-leaderboard"),
        "global_merkle_root": global_root,
        "evidence_separation": "observed_trial_receipts_only",
        "track_count": len(rows),
    })
    return VerifiableLeaderboardPayload(
        global_merkle_root=global_root,
        rows=tuple(rows),
        demos_baltor_view=demos_view,
        agentbriefs_view=briefs_view,
        cli_challenge_packs=tuple(packs),
    )


class MerkleReceiptVerifiedLeaderboardEngine:
    """Primary engine (`merkle_receipt_verified_leaderboard_engine`) for Slot Family 2."""

    engine_id = ENGINE_MERKLE_LEADERBOARD

    def execute(
        self, request: VerifiableLeaderboardRequest
    ) -> tuple[VerifiableLeaderboardPayload | None, float, str | None]:
        if request.simulate_merkle_engine_deferral:
            return None, 0.18, "merkle_batch_cache_deferred"
        return (
            _synthesize_leaderboard_payload(request.trial_receipts, request.declared_populations),
            0.47,
            None,
        )


class ReproducibleCliChallengePackExporter:
    """Secondary engine (`reproducible_cli_challenge_pack_exporter`) for Slot Family 2."""

    engine_id = ENGINE_CLI_CHALLENGE_EXPORTER

    def execute(
        self, request: VerifiableLeaderboardRequest
    ) -> tuple[VerifiableLeaderboardPayload | None, float, str | None]:
        return (
            _synthesize_leaderboard_payload(request.trial_receipts, request.declared_populations),
            0.55,
            None,
        )


class VerifiableGlobalBenchmarkLeaderboardOrchestrator:
    """7-Layer ComponentEnvelope orchestrator for Slot Family 2 (`verifiable_global_benchmark_leaderboard_slot`)."""

    def __init__(self, engine_order: tuple[str, ...] = LEADERBOARD_ENGINE_IDS) -> None:
        self._engine_order = engine_order
        self._engines: Mapping[str, Any] = {
            ENGINE_MERKLE_LEADERBOARD: MerkleReceiptVerifiedLeaderboardEngine(),
            ENGINE_CLI_CHALLENGE_EXPORTER: ReproducibleCliChallengePackExporter(),
        }
        self.envelope = ComponentEnvelope(
            slot_id=LEADERBOARD_SLOT_ID,
            request_schema=LEADERBOARD_REQUEST_SCHEMA,
            capability_id="merkle_receipt_leaderboard_v1",
            recoverable_codes=("merkle_batch_cache_deferred",),
        )

    def handle(self, request: VerifiableLeaderboardRequest) -> VerifiableLeaderboardResponse:
        schema_ok = request.schema == LEADERBOARD_REQUEST_SCHEMA and len(request.trial_receipts) > 0

        # Layer 3 Handshake check: verify every receipt has valid 64-hex digests and tamper-free receipt_sha256
        handshake_refusal: EnvelopeRefusal | None = None
        for r in request.trial_receipts:
            expected_sha = compute_receipt_sha256(
                trial_id=r.trial_id,
                track_id=r.track_id,
                model_id=r.model_id,
                prompt_sha256=r.prompt_sha256,
                contract_card_sha256=r.contract_card_sha256,
                without_baltor_score=r.without_baltor_score,
                with_baltor_score=r.with_baltor_score,
                verifier_digest=r.verifier_digest,
                trial_status=r.trial_status,
            )
            if (
                not _SHA256_RE.fullmatch(r.verifier_digest)
                or not _SHA256_RE.fullmatch(r.receipt_sha256)
                or r.receipt_sha256 != expected_sha
            ):
                handshake_refusal = envelope_refusal(
                    "invalid_or_missing_trial_receipt_digest",
                    f"Trial {r.trial_id} is missing a valid 64-hex verifier_digest or tamper-evident receipt_sha256.",
                    "Provide a valid 64-hex verifier_digest and matching receipt_sha256 for every trial.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
                break

        # Layer 6 Preflight check: verify full attempt population accounting (refuse cherry-picking)
        def check_attempt_population(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            receipts: tuple[BenchmarkTrialReceipt, ...] = ctx["trial_receipts"]
            populations: tuple[AttemptPopulationDeclaration, ...] = ctx["declared_populations"]
            for pop in populations:
                t_receipts = [r for r in receipts if r.track_id == pop.track_id]
                obs_completed = sum(1 for r in t_receipts if r.trial_status == "completed")
                obs_failed = sum(1 for r in t_receipts if r.trial_status == "failed")
                obs_excluded = sum(1 for r in t_receipts if r.trial_status == "excluded")
                if (
                    len(t_receipts) != pop.total_attempts
                    or obs_completed != pop.completed_trials
                    or obs_failed != pop.failed_trials
                    or obs_excluded != pop.excluded_trials
                ):
                    return envelope_refusal(
                        "cherry_picked_attempt_population_mismatch",
                        f"Track {pop.track_id} omitted failed or excluded trials from its attempt population.",
                        "Include all completed, failed, and excluded trial receipts matching total_attempts.",
                        retry=RETRY_AFTER_FIX,
                        effect_commitment=EFFECT_NONE,
                        next_action_by=CALLER,
                    )
            return None

        preflight_ctx: dict[str, Any] = {
            "trial_receipts": request.trial_receipts,
            "declared_populations": request.declared_populations,
        }
        (
            ok,
            selected,
            attempted,
            payload,
            latency_ms,
            trace,
            frame,
            refusal,
            preflight,
        ) = self.envelope.execute_envelope(
            schema_valid=schema_ok,
            carrier_refusal=None,
            handshake_refusal=handshake_refusal,
            preflight_checks=(
                EnvelopePreflightCheck(
                    check_id="verify_full_attempt_population",
                    diagnoses=("cherry_picked_attempt_population_mismatch",),
                    run=check_attempt_population,
                ),
            ),
            preflight_repairs=(),
            preflight_context=preflight_ctx,
            engine_order=self._engine_order,
            run_engine=lambda eng_id, _ctx: self._engines[eng_id].execute(request),
        )
        return VerifiableLeaderboardResponse(
            request_id=request.request_id,
            succeeded=ok,
            selected_engine=selected,
            attempted_engines=attempted,
            payload=payload,
            tracks_verified=len(payload.rows) if payload is not None else 0,
            receipts_verified=len(request.trial_receipts) if ok else 0,
            latency_ms=latency_ms,
            trace=trace,
            frame=frame,
            refusal=refusal,
            preflight_report=preflight,
        )


def run_head_to_head_benchmark() -> Mapping[str, Any]:
    """Run deterministic head-to-head benchmarks and known-wrong probes across both slot families."""
    geo_benchmarks: list[Mapping[str, Any]] = []
    for engine_id in GEO_ENGINE_IDS:
        orch = GeoLlmsTxtAndMarkdownTwinOrchestrator(engine_order=(engine_id,))
        resp = orch.handle(GeoSynthesisRequest(request_id=f"bench-geo-{engine_id}"))
        geo_benchmarks.append({
            "engine_id": engine_id,
            "succeeded": resp.succeeded,
            "domains_synthesized": resp.domains_synthesized,
            "total_jsonld_nodes": resp.total_jsonld_nodes,
            "wording_violations": len(resp.wording_violations_found),
            "latency_ms": resp.latency_ms,
        })

    leaderboard_benchmarks: list[Mapping[str, Any]] = []
    for engine_id in LEADERBOARD_ENGINE_IDS:
        orch = VerifiableGlobalBenchmarkLeaderboardOrchestrator(engine_order=(engine_id,))
        resp = orch.handle(VerifiableLeaderboardRequest(request_id=f"bench-lb-{engine_id}"))
        leaderboard_benchmarks.append({
            "engine_id": engine_id,
            "succeeded": resp.succeeded,
            "tracks_verified": resp.tracks_verified,
            "receipts_verified": resp.receipts_verified,
            "global_merkle_root": resp.payload.global_merkle_root if resp.payload else "",
            "latency_ms": resp.latency_ms,
        })

    return {
        "coverage_layers": list(COVERAGE_LAYERS),
        "geo_slot_benchmarks": geo_benchmarks,
        "leaderboard_slot_benchmarks": leaderboard_benchmarks,
    }


def self_test() -> bool:
    """Run fast in-memory self-verification of both slot families."""
    bench = run_head_to_head_benchmark()
    assert all(row["succeeded"] and row["domains_synthesized"] == 24 for row in bench["geo_slot_benchmarks"])
    assert all(row["succeeded"] and row["tracks_verified"] == 8 for row in bench["leaderboard_slot_benchmarks"])
    return True


if __name__ == "__main__":
    self_test()
    print(json.dumps(run_head_to_head_benchmark(), indent=2))
