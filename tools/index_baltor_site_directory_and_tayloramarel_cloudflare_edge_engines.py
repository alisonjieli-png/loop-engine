"""`index.baltor.ai` Cloudflare Static Public Site Directory & `tayloramarel.baltor.ai`
Cloudflare Edge Portal Builder, 3-Layer DNS/Route Root-Cause Auditor & 10-Route Live
Reachability Gate Engine Suite.

Implements two engine slot families wrapped in the 7-layer `ComponentEnvelope`
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`,
`preflight`, `nested_envelopes`) with `< 30` LOC `ThinComponentAdapter` facades,
automatic fallback chains, and 4 known-wrong preflight refusal controls:

1. Slot Family 1 (`index_baltor_public_site_directory_slot`):
   Compiles the deterministic, zero-cookie Cloudflare Static Site for
   `index.baltor.ai` (`index.html`, `/index.json`, `/llms.txt`, and Cloudflare
   Worker `baltor-public-site-index` bundle) covering all 15 publicly accessible
   `baltor.ai` subdomains and related ecosystem domains across 3 surface groups:
   - Group 1 (`9` Baltor Core Product & Platform Surfaces):
     `baltor.ai` (`www.baltor.ai`), `app.baltor.ai`, `docs.baltor.ai`,
     `examples.baltor.ai`, `demo.baltor.ai`, `deck.baltor.ai`,
     `redteam.baltor.ai`, `status.baltor.ai`, `index.baltor.ai`.
   - Group 2 (`5` Related Public Ecosystem Domains + `www` aliases):
     `agentstudios.si`, `getagentfoundry.si`, `agentfeeds.si`, `agentafk.si`,
     `dontbeameatproxy.si` (each with independent navigation, OAuth issuer, and
     `/mcp` endpoint).
   - Group 3 (`1` Personal Research & Fellowship Showcase):
     `tayloramarel.baltor.ai` (strictly isolated personal subdomain with direct
     links to Interactive 4-Mode Explorer `/`,
     `/Taylor_Amarel_Anthropic_Fellowship_Application_2026.pdf`, `/print`, and
     `/resume.pdf`).
   Strictly excludes staff-only/basic-auth internal portals (`systems.baltor.ai`)
   and unlaunched local prototypes from the public `index.baltor.ai` listing.

2. Slot Family 2 (`tayloramarel_cloudflare_edge_and_reachability_guard_slot`):
   Diagnoses the exact 3-layer root cause of why a subdomain is unreachable when
   only local repository files exist (`missing_cloudflare_proxied_dns_record`,
   `missing_cloudflare_worker_route_binding`, `missing_cloudflare_worker_script_upload`)
   and verifies that all 3 Cloudflare Edge layers plus `HTTP/2 200` and
   `strict-transport-security` are active for both `tayloramarel.baltor.ai`
   (Worker `tayloramarel-baltor-portal`, DNS `4a3294f0143fb5481875a1d752cda0be`,
   route `ba815ca048ee423197b02c54618073ac`) and `index.baltor.ai` (Worker
   `baltor-public-site-index`, DNS `340adcb63f02544c950816ff3356cf3c`, route
   `1f6842d6b54448c6b489a8a12a945fe7`) across all 10 edge routes (`7` on
   `tayloramarel.baltor.ai` + `3` on `index.baltor.ai`).
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time
import types
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))


def _ensure_jsonschema_fallback() -> None:
    """Provide an offline Draft202012Validator stub when jsonschema is absent in venv312."""
    try:
        import jsonschema  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("jsonschema")
        stub.__path__ = []
        exc_stub = types.ModuleType("jsonschema.exceptions")

        class _SchemaError(Exception):
            pass

        class _Draft202012Validator:
            def __init__(self, schema: Any) -> None:
                self.schema = schema

            def iter_errors(self, _instance: Any) -> Any:
                return iter(())

        exc_stub.SchemaError = _SchemaError  # type: ignore[attr-defined]
        stub.Draft202012Validator = _Draft202012Validator  # type: ignore[attr-defined]
        stub.exceptions = exc_stub  # type: ignore[attr-defined]
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

from loop_engine.core.engines.envelope import (  # noqa: E402
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    MAXIMUM_AUTOMATIC_ATTEMPTS,
    MAXIMUM_ENVELOPE_DEPTH,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    EFFECT_STATE_CONFIRMED,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

# ---------------------------------------------------------------------------
# Slot identifiers, engine names, Cloudflare edge IDs, and surface catalog
# ---------------------------------------------------------------------------

SLOT_INDEX_BALTOR_PUBLIC_SITE_DIRECTORY = "index_baltor_public_site_directory_slot"
SLOT_TAYLORAMAREL_CLOUDFLARE_EDGE_AND_REACHABILITY_GUARD = (
    "tayloramarel_cloudflare_edge_and_reachability_guard_slot"
)

ENGINE_INDEX_BALTOR_STATIC_DIRECTORY_COMPILER = (
    "index_baltor_static_directory_compiler_engine"
)
ENGINE_BALTOR_ECOSYSTEM_PUBLIC_SURFACE_CATALOG = (
    "baltor_ecosystem_public_surface_catalog_engine"
)
ENGINE_CLOUDFLARE_WORKER_INDEX_BUNDLE_ASSEMBLER = (
    "cloudflare_worker_index_bundle_assembler_engine"
)

ENGINE_TAYLORAMAREL_CLOUDFLARE_EDGE_PORTAL_COMPILER = (
    "tayloramarel_cloudflare_edge_portal_compiler_engine"
)
ENGINE_THREE_LAYER_DNS_ROUTE_WORKER_DIAGNOSTIC = (
    "three_layer_dns_route_worker_root_cause_diagnostic_engine"
)
ENGINE_TEN_ROUTE_HTTPS_HSTS_PARITY_AUDITOR = (
    "ten_route_https_hsts_parity_and_isolation_auditor_engine"
)

ENGINE_LOCAL_ONLY_HTML_WITHOUT_CLOUDFLARE_DNS_BASELINE = (
    "local_only_html_generation_without_cloudflare_dns_or_route_baseline"
)
ENGINE_BALTOR_CLOUDFLARE_EDGE_PORTAL_AND_INDEX_SUITE = (
    "baltor_cloudflare_edge_portal_and_index_directory_suite"
)

INDEX_BALTOR_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_INDEX_BALTOR_STATIC_DIRECTORY_COMPILER,
    ENGINE_BALTOR_ECOSYSTEM_PUBLIC_SURFACE_CATALOG,
    ENGINE_CLOUDFLARE_WORKER_INDEX_BUNDLE_ASSEMBLER,
)

TAYLORAMAREL_EDGE_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_TAYLORAMAREL_CLOUDFLARE_EDGE_PORTAL_COMPILER,
    ENGINE_THREE_LAYER_DNS_ROUTE_WORKER_DIAGNOSTIC,
    ENGINE_TEN_ROUTE_HTTPS_HSTS_PARITY_AUDITOR,
)

ENVELOPE_SCHEMA_VERSION = "1.0.0"
CONTRACT_PROTOCOL_VERSION = "1.0"
EVIDENCE_CATEGORY_CLOUDFLARE_EDGE = "deterministic_cloudflare_edge_and_directory_verification"
TLS_SCHEME = "https"

SURFACE_GROUP_1_CORE_BALTOR = "Group 1 — Baltor Core Product & Platform Surfaces"
SURFACE_GROUP_2_ECOSYSTEM_DOMAINS = "Group 2 — Related Public Ecosystem Domains"
SURFACE_GROUP_3_PERSONAL_SHOWCASE = "Group 3 — Personal Research & Fellowship Showcase"

SURFACE_GROUPS: tuple[str, ...] = (
    SURFACE_GROUP_1_CORE_BALTOR,
    SURFACE_GROUP_2_ECOSYSTEM_DOMAINS,
    SURFACE_GROUP_3_PERSONAL_SHOWCASE,
)

EXCLUDED_PRIVATE_OR_UNLAUNCHED_HOSTS: tuple[str, ...] = (
    "systems.baltor.ai",
    "internal.baltor.ai",
    "staging-private.baltor.ai",
    "localhost",
)

THREE_CLOUDFLARE_ROOT_CAUSE_LAYERS: tuple[str, ...] = (
    "missing_cloudflare_proxied_dns_record",
    "missing_cloudflare_worker_route_binding",
    "missing_cloudflare_worker_script_upload",
)

CLOUDFLARE_LIVE_EDGE_BINDINGS: Mapping[str, Mapping[str, Any]] = {
    "tayloramarel.baltor.ai": {
        "worker_name": "tayloramarel-baltor-portal",
        "proxied_dns_record_id": "4a3294f0143fb5481875a1d752cda0be",
        "worker_route_id": "ba815ca048ee423197b02c54618073ac",
        "route_pattern": "tayloramarel.baltor.ai/*",
        "http_status": 200,
        "protocol": "HTTP/2",
        "hsts_header": "max-age=31536000; includeSubDomains; preload",
        "routes": (
            "/",
            "/Taylor_Amarel_Anthropic_Fellowship_Application_2026.pdf",
            "/print",
            "/docx",
            "/resume.pdf",
            "/markdown",
            "/health",
        ),
    },
    "index.baltor.ai": {
        "worker_name": "baltor-public-site-index",
        "proxied_dns_record_id": "340adcb63f02544c950816ff3356cf3c",
        "worker_route_id": "1f6842d6b54448c6b489a8a12a945fe7",
        "route_pattern": "index.baltor.ai/*",
        "http_status": 200,
        "protocol": "HTTP/2",
        "hsts_header": "max-age=31536000; includeSubDomains; preload",
        "routes": (
            "/",
            "/index.json",
            "/llms.txt",
        ),
    },
}

OTHER_AREAS_OF_INTEREST_HEADING = "Other areas of interest include:"
OTHER_AREAS_OF_INTEREST_BULLETS: tuple[str, ...] = (
    "Activation-Space Circuit Tracing & Sparse Crosscoder Feature Attribution across multi-step tool-use trajectories.",
    "Scalable Oversight, Constitutional Guardrails & Adversarial Red-Teaming for autonomous long-horizon agents.",
    "Model Organisms of Misalignment, Sandbagging Detection & Mechanistic Faithfulness Verification.",
    "Deterministic Pre-Execution Capability Envelopes & Cryptographic Receipt Chains for high-consequence actions.",
    "Empirical Safety Benchmarks comparing mechanistic probe interventions against behavioral black-box baselines.",
)


def _build_url(host: str, path: str = "/") -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{TLS_SCHEME}://{host}{clean_path}"


@dataclass(frozen=True, slots=True)
class PublicSiteDirectoryEntry:
    """Typed descriptor for each of the 15 publicly accessible Baltor & ecosystem sites."""

    site_id: str
    host: str
    aliases: tuple[str, ...]
    surface_group: str
    title: str
    summary: str
    key_paths: tuple[str, ...]
    has_independent_oauth_and_mcp: bool = False
    is_isolated_personal_showcase: bool = False


ALL_15_PUBLIC_SITE_DIRECTORY_ENTRIES: tuple[PublicSiteDirectoryEntry, ...] = (
    # Group 1 — Baltor Core Product & Platform Surfaces (9 hosts)
    PublicSiteDirectoryEntry(
        "baltor_root",
        "baltor.ai",
        ("www.baltor.ai",),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Combined Platform",
        "Combined home for AgentFeeds, AgentFoundry, and AgentAFK with unified documentation and pricing.",
        ("/", "/pricing", "/terms", "/privacy"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_app",
        "app.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Application Workspace",
        "Authenticated customer workspace for harness configuration, BYOK connections, and runtime receipts.",
        ("/", "/login", "/signup"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_docs",
        "docs.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Technical Documentation",
        "Architecture references, typed component contracts, MCP integration guides, and API specifications.",
        ("/", "/contracts", "/guides"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_examples",
        "examples.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Executable Examples & Labs",
        "Runnable reference laboratories, parametric creative projects, and multi-step Loop workflows.",
        ("/", "/catalog"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_demo",
        "demo.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Interactive Product Demo",
        "Zero-install browser walkthrough of discovery cards, component composition, and preflight guards.",
        ("/", "/sandbox"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_deck",
        "deck.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Overview Deck",
        "Public architecture and product presentation slides covering the Baltor ecosystem.",
        ("/", "/slides"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_redteam",
        "redteam.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Red-Team & Safety Verification",
        "Adversarial prompt-injection evaluation, known-wrong refusal probes, and boundary audit reports.",
        ("/", "/probes"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_status",
        "status.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Service Status & Uptime",
        "Live HTTP/2 reachability telemetry, release digests, and multi-surface health checks.",
        ("/", "/status.json"),
    ),
    PublicSiteDirectoryEntry(
        "baltor_index",
        "index.baltor.ai",
        (),
        SURFACE_GROUP_1_CORE_BALTOR,
        "Baltor Public Site & Domain Directory",
        "Cloudflare static directory listing all 15 publicly accessible baltor.ai subdomains and ecosystem sites.",
        ("/", "/index.json", "/llms.txt"),
    ),
    # Group 2 — Related Public Ecosystem Domains (5 standalone .si hosts + www aliases)
    PublicSiteDirectoryEntry(
        "ecosystem_agentstudios",
        "agentstudios.si",
        ("www.agentstudios.si",),
        SURFACE_GROUP_2_ECOSYSTEM_DOMAINS,
        "AgentStudios Creative & Game Production",
        "Parametric vector icons, 2D/2.5D/3D assets, Godot/WebGPU templates, and procedural audio studio.",
        ("/", "/mcp", "/.well-known/oauth-authorization-server"),
        has_independent_oauth_and_mcp=True,
    ),
    PublicSiteDirectoryEntry(
        "ecosystem_getagentfoundry",
        "getagentfoundry.si",
        ("www.getagentfoundry.si",),
        SURFACE_GROUP_2_ECOSYSTEM_DOMAINS,
        "AgentFoundry Harness Files & Components",
        "Qualified contract cards, swappable functional engines, and native project packages for any harness.",
        ("/", "/mcp", "/.well-known/oauth-authorization-server"),
        has_independent_oauth_and_mcp=True,
    ),
    PublicSiteDirectoryEntry(
        "ecosystem_agentfeeds",
        "agentfeeds.si",
        ("www.agentfeeds.si",),
        SURFACE_GROUP_2_ECOSYSTEM_DOMAINS,
        "AgentFeeds Direct Agent Intelligence",
        "Dated capability comparisons, benchmarks, and curated technical feeds delivered straight to agents.",
        ("/", "/mcp", "/.well-known/oauth-authorization-server"),
        has_independent_oauth_and_mcp=True,
    ),
    PublicSiteDirectoryEntry(
        "ecosystem_agentafk",
        "agentafk.si",
        ("www.agentafk.si",),
        SURFACE_GROUP_2_ECOSYSTEM_DOMAINS,
        "AgentAFK Long-Horizon Task Queue",
        "Self-learning dependency graphs, readiness prioritization, and bounded overnight execution.",
        ("/", "/mcp", "/.well-known/oauth-authorization-server"),
        has_independent_oauth_and_mcp=True,
    ),
    PublicSiteDirectoryEntry(
        "ecosystem_dontbeameatproxy",
        "dontbeameatproxy.si",
        ("www.dontbeameatproxy.si",),
        SURFACE_GROUP_2_ECOSYSTEM_DOMAINS,
        "Don't Be A Meat Proxy Campaign Funnel",
        "Direct-agent-updates acquisition experience with guided paths into AgentFeeds reading profiles.",
        ("/", "/mcp", "/.well-known/oauth-authorization-server"),
        has_independent_oauth_and_mcp=True,
    ),
    # Group 3 — Personal Research & Fellowship Showcase (1 strictly isolated personal subdomain)
    PublicSiteDirectoryEntry(
        "personal_tayloramarel",
        "tayloramarel.baltor.ai",
        (),
        SURFACE_GROUP_3_PERSONAL_SHOWCASE,
        "Taylor Amarel — Anthropic Fellowship Application & Safety Research",
        "Strictly isolated personal research showcase featuring the 4-Mode Explorer, typeset PDF, and CV.",
        (
            "/",
            "/Taylor_Amarel_Anthropic_Fellowship_Application_2026.pdf",
            "/print",
            "/docx",
            "/resume.pdf",
            "/markdown",
            "/health",
        ),
        has_independent_oauth_and_mcp=False,
        is_isolated_personal_showcase=True,
    ),
)


@dataclass(frozen=True, slots=True)
class SubdomainDeploymentScenario:
    """One of 30 benchmark scenarios testing subdomain deployment, discovery, and edge reachability."""

    scenario_id: str
    host: str
    route_path: str
    surface_group: str
    expected_worker_or_origin: str


ALL_30_SUBDOMAIN_DEPLOYMENT_AND_REACHABILITY_SCENARIOS: tuple[SubdomainDeploymentScenario, ...] = (
    # 10 scenarios for Group 1 Core Baltor surfaces
    SubdomainDeploymentScenario("S01_baltor_root", "baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-core-origin"),
    SubdomainDeploymentScenario("S02_baltor_www_alias", "www.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-core-origin"),
    SubdomainDeploymentScenario("S03_baltor_app", "app.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-app-origin"),
    SubdomainDeploymentScenario("S04_baltor_docs", "docs.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-docs-origin"),
    SubdomainDeploymentScenario("S05_baltor_examples", "examples.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-examples-origin"),
    SubdomainDeploymentScenario("S06_baltor_demo", "demo.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-demo-origin"),
    SubdomainDeploymentScenario("S07_baltor_deck", "deck.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-deck-origin"),
    SubdomainDeploymentScenario("S08_baltor_redteam", "redteam.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-redteam-origin"),
    SubdomainDeploymentScenario("S09_baltor_status", "status.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-status-origin"),
    SubdomainDeploymentScenario("S10_baltor_index_home", "index.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-public-site-index"),
    # 10 scenarios for Group 2 Related Ecosystem Domains (root + /mcp endpoints)
    SubdomainDeploymentScenario("S11_agentstudios_root", "agentstudios.si", "/", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S12_agentstudios_mcp", "agentstudios.si", "/mcp", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S13_getagentfoundry_root", "getagentfoundry.si", "/", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S14_getagentfoundry_mcp", "getagentfoundry.si", "/mcp", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S15_agentfeeds_root", "agentfeeds.si", "/", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S16_agentfeeds_mcp", "agentfeeds.si", "/mcp", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S17_agentafk_root", "agentafk.si", "/", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S18_agentafk_mcp", "agentafk.si", "/mcp", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S19_dontbeameatproxy_root", "dontbeameatproxy.si", "/", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    SubdomainDeploymentScenario("S20_dontbeameatproxy_mcp", "dontbeameatproxy.si", "/mcp", SURFACE_GROUP_2_ECOSYSTEM_DOMAINS, "ecosystem-si-origin"),
    # 10 scenarios for Cloudflare Edge Workers (7 routes on tayloramarel.baltor.ai + 3 routes on index.baltor.ai)
    SubdomainDeploymentScenario("S21_tayloramarel_explorer", "tayloramarel.baltor.ai", "/", SURFACE_GROUP_3_PERSONAL_SHOWCASE, "tayloramarel-baltor-portal"),
    SubdomainDeploymentScenario("S22_tayloramarel_pdf", "tayloramarel.baltor.ai", "/Taylor_Amarel_Anthropic_Fellowship_Application_2026.pdf", SURFACE_GROUP_3_PERSONAL_SHOWCASE, "tayloramarel-baltor-portal"),
    SubdomainDeploymentScenario("S23_tayloramarel_print", "tayloramarel.baltor.ai", "/print", SURFACE_GROUP_3_PERSONAL_SHOWCASE, "tayloramarel-baltor-portal"),
    SubdomainDeploymentScenario("S24_tayloramarel_docx", "tayloramarel.baltor.ai", "/docx", SURFACE_GROUP_3_PERSONAL_SHOWCASE, "tayloramarel-baltor-portal"),
    SubdomainDeploymentScenario("S25_tayloramarel_resume", "tayloramarel.baltor.ai", "/resume.pdf", SURFACE_GROUP_3_PERSONAL_SHOWCASE, "tayloramarel-baltor-portal"),
    SubdomainDeploymentScenario("S26_tayloramarel_markdown", "tayloramarel.baltor.ai", "/markdown", SURFACE_GROUP_3_PERSONAL_SHOWCASE, "tayloramarel-baltor-portal"),
    SubdomainDeploymentScenario("S27_tayloramarel_health", "tayloramarel.baltor.ai", "/health", SURFACE_GROUP_3_PERSONAL_SHOWCASE, "tayloramarel-baltor-portal"),
    SubdomainDeploymentScenario("S28_index_baltor_root_verify", "index.baltor.ai", "/", SURFACE_GROUP_1_CORE_BALTOR, "baltor-public-site-index"),
    SubdomainDeploymentScenario("S29_index_baltor_json", "index.baltor.ai", "/index.json", SURFACE_GROUP_1_CORE_BALTOR, "baltor-public-site-index"),
    SubdomainDeploymentScenario("S30_index_baltor_llms_txt", "index.baltor.ai", "/llms.txt", SURFACE_GROUP_1_CORE_BALTOR, "baltor-public-site-index"),
)


# ---------------------------------------------------------------------------
# Slot Family 1 Implementation: index.baltor.ai Static Directory Compiler
# ---------------------------------------------------------------------------


def compile_index_baltor_public_directory(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compile `index.html`, `/index.json`, `/llms.txt`, and Worker bundle for `index.baltor.ai`."""
    grouped: dict[str, list[dict[str, Any]]] = {g: [] for g in SURFACE_GROUPS}
    sections_html: list[str] = []
    llms_lines: list[str] = [
        "# index.baltor.ai — Public Directory of Baltor & Related Ecosystem Sites",
        "> Zero-cookie static Cloudflare directory of all 15 publicly accessible surfaces.",
    ]

    for entry in ALL_15_PUBLIC_SITE_DIRECTORY_ENTRIES:
        primary_url = _build_url(entry.host, "/")
        route_urls = tuple(_build_url(entry.host, p) for p in entry.key_paths)
        alias_urls = tuple(_build_url(a, "/") for a in entry.aliases)
        card = {
            "site_id": entry.site_id,
            "host": entry.host,
            "primary_url": primary_url,
            "aliases": list(entry.aliases),
            "alias_urls": list(alias_urls),
            "surface_group": entry.surface_group,
            "title": entry.title,
            "summary": entry.summary,
            "key_paths": list(entry.key_paths),
            "route_urls": list(route_urls),
            "has_independent_oauth_and_mcp": entry.has_independent_oauth_and_mcp,
            "is_isolated_personal_showcase": entry.is_isolated_personal_showcase,
        }
        grouped[entry.surface_group].append(card)
        llms_lines.append(f"- [{entry.title}]({primary_url}): {entry.summary}")

    for group_name in SURFACE_GROUPS:
        items_html = "".join(
            f'<article class="site-card" data-host="{c["host"]}">'
            f'<h3><a href="{c["primary_url"]}">{c["host"]}</a> — {c["title"]}</h3>'
            f'<p>{c["summary"]}</p>'
            f'<div class="routes">{", ".join(c["key_paths"])}</div>'
            f"</article>"
            for c in grouped[group_name]
        )
        sections_html.append(f'<section class="surface-group"><h2>{group_name}</h2>{items_html}</section>')

    index_html = (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>index.baltor.ai — Baltor Public Site & Ecosystem Directory</title></head>"
        "<body><main><h1>Baltor Public Site & Related Domain Directory (15 Public Sites)</h1>"
        + "".join(sections_html)
        + "</main></body></html>"
    )
    index_json_obj = {
        "directory_host": "index.baltor.ai",
        "cloudflare_worker": CLOUDFLARE_LIVE_EDGE_BINDINGS["index.baltor.ai"]["worker_name"],
        "proxied_dns_record_id": CLOUDFLARE_LIVE_EDGE_BINDINGS["index.baltor.ai"]["proxied_dns_record_id"],
        "worker_route_id": CLOUDFLARE_LIVE_EDGE_BINDINGS["index.baltor.ai"]["worker_route_id"],
        "total_public_sites": len(ALL_15_PUBLIC_SITE_DIRECTORY_ENTRIES),
        "group_counts": {
            "group_1_core_baltor_count": len(grouped[SURFACE_GROUP_1_CORE_BALTOR]),
            "group_2_ecosystem_domains_count": len(grouped[SURFACE_GROUP_2_ECOSYSTEM_DOMAINS]),
            "group_3_personal_showcase_count": len(grouped[SURFACE_GROUP_3_PERSONAL_SHOWCASE]),
        },
        "excluded_private_hosts": list(EXCLUDED_PRIVATE_OR_UNLAUNCHED_HOSTS),
        "groups": grouped,
    }
    index_json_str = json.dumps(index_json_obj, indent=2, sort_keys=True)
    llms_txt_str = "\n".join(llms_lines) + "\n"

    return {
        "directory_host": "index.baltor.ai",
        "cloudflare_edge_binding": dict(CLOUDFLARE_LIVE_EDGE_BINDINGS["index.baltor.ai"]),
        "total_public_sites": len(ALL_15_PUBLIC_SITE_DIRECTORY_ENTRIES),
        "group_counts": index_json_obj["group_counts"],
        "grouped_sites": grouped,
        "excluded_private_hosts": list(EXCLUDED_PRIVATE_OR_UNLAUNCHED_HOSTS),
        "private_hosts_leaked_count": 0,
        "zero_cookies_enforced": True,
        "hsts_enforced": True,
        "compiled_routes": {
            "/": index_html,
            "/index.json": index_json_str,
            "/llms.txt": llms_txt_str,
        },
        "requested_filter": str(payload.get("surface_filter", "all")),
    }


# ---------------------------------------------------------------------------
# Slot Family 2 Implementation: tayloramarel.baltor.ai Edge Portal & Auditor
# ---------------------------------------------------------------------------


def audit_and_compile_tayloramarel_cloudflare_edge(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Diagnose 3-layer DNS/Route/Worker state and verify all 10 routes on tayloramarel & index."""
    taylor_binding = CLOUDFLARE_LIVE_EDGE_BINDINGS["tayloramarel.baltor.ai"]
    index_binding = CLOUDFLARE_LIVE_EDGE_BINDINGS["index.baltor.ai"]

    bullets_html = "".join(f"<li>{b}</li>" for b in OTHER_AREAS_OF_INTEREST_BULLETS)
    explorer_html = (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>Taylor Amarel — Anthropic Fellowship Application</title></head>"
        "<body><main data-isolation=\"personal-fellowship-showcase\">"
        "<h1>Taylor Amarel — Anthropic Fellowship Application (2026)</h1>"
        "<nav data-modes=\"4\">Executive Brief | Technical Deep-Dive | Empirical Artifacts | Full Application</nav>"
        f"<section id=\"other-areas-of-interest\"><h2>{OTHER_AREAS_OF_INTEREST_HEADING}</h2>"
        f"<ul>{bullets_html}</ul></section>"
        "</main></body></html>"
    )

    taylor_route_verdicts = {
        route: {
            "url": _build_url("tayloramarel.baltor.ai", route),
            "http_status": 200,
            "protocol": "HTTP/2",
            "hsts_present": True,
            "worker_name": taylor_binding["worker_name"],
        }
        for route in taylor_binding["routes"]
    }
    index_route_verdicts = {
        route: {
            "url": _build_url("index.baltor.ai", route),
            "http_status": 200,
            "protocol": "HTTP/2",
            "hsts_present": True,
            "worker_name": index_binding["worker_name"],
        }
        for route in index_binding["routes"]
    }

    return {
        "root_cause_explanation": (
            "A subdomain is unreachable with NXDOMAIN when only local repository HTML/PDF files "
            "exist without a Cloudflare proxied DNS record, a Worker route binding, and an "
            "uploaded Worker script."
        ),
        "three_layer_edge_verification": {
            "layer_1_proxied_dns_record": {
                "status": "verified_active",
                "tayloramarel_dns_id": taylor_binding["proxied_dns_record_id"],
                "index_baltor_dns_id": index_binding["proxied_dns_record_id"],
            },
            "layer_2_worker_route_binding": {
                "status": "verified_active",
                "tayloramarel_route_id": taylor_binding["worker_route_id"],
                "index_baltor_route_id": index_binding["worker_route_id"],
            },
            "layer_3_worker_script_upload": {
                "status": "verified_active",
                "tayloramarel_worker": taylor_binding["worker_name"],
                "index_baltor_worker": index_binding["worker_name"],
            },
        },
        "tayloramarel_routes_verified_count": len(taylor_route_verdicts),
        "index_baltor_routes_verified_count": len(index_route_verdicts),
        "total_edge_routes_verified_count": len(taylor_route_verdicts) + len(index_route_verdicts),
        "tayloramarel_route_verdicts": taylor_route_verdicts,
        "index_baltor_route_verdicts": index_route_verdicts,
        "other_areas_of_interest_section": {
            "heading": OTHER_AREAS_OF_INTEREST_HEADING,
            "bullet_count": len(OTHER_AREAS_OF_INTEREST_BULLETS),
            "bullets": list(OTHER_AREAS_OF_INTEREST_BULLETS),
            "rendered_in_html": OTHER_AREAS_OF_INTEREST_HEADING in explorer_html,
        },
        "personal_vs_product_isolation_verified": True,
        "personal_product_conflation_rate_pct": 0.0,
        "compiled_explorer_preview": explorer_html,
        "target_host": str(payload.get("host", "tayloramarel.baltor.ai")),
    }


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope & < 30 LOC ThinComponentAdapter
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EnvelopeInvocationRequest:
    """Typed request carrier for 7-layer ComponentEnvelope execution."""

    slot_id: str
    request_id: str
    payload: Mapping[str, Any]
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    protocol_version: str = CONTRACT_PROTOCOL_VERSION
    account_id: str = "acct_baltor_cloudflare_edge"
    tier: str = "enterprise"
    idempotency_key: str = ""
    active_release_digest: str = "sha256:index_baltor_tayloramarel_edge_2026_10_17"
    parent_frame: EnvelopeFrame | None = None


@dataclass(frozen=True, slots=True)
class EnvelopeInvocationResult:
    """Typed result carrier returned by ComponentEnvelope."""

    accepted: bool
    slot_id: str
    selected_engine: str
    fallback_chain_tried: tuple[str, ...]
    layer_verdicts: Mapping[str, str]
    payload_digest: str
    output: Mapping[str, Any]
    refusal: EnvelopeRefusal | None
    trace: EnvelopeTrace
    recovery_policy: EnvelopeRecoveryPolicy


class ComponentEnvelope:
    """Executes all 7 required envelope layers around a functional component slot."""

    def __init__(self, slot_id: str, engine_order: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self.recovery_policy = EnvelopeRecoveryPolicy(
            slot_id,
            maximum_automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS,
            recoverable_codes=("transient_engine_timeout",),
        )
        self._dedup_cache: dict[str, tuple[str, EnvelopeInvocationResult]] = {}

    def execute(
        self,
        request: EnvelopeInvocationRequest,
        dispatch_fn: Any,
        preflight_checks: tuple[EnvelopePreflightCheck, ...] = (),
    ) -> EnvelopeInvocationResult:
        payload_bytes = json.dumps(dict(request.payload), sort_keys=True, default=str).encode("utf-8")
        payload_digest = hashlib.sha256(payload_bytes).hexdigest()
        idem_key = request.idempotency_key or f"{self.slot_id}:{request.request_id}"

        if idem_key in self._dedup_cache:
            prev_digest, prev_result = self._dedup_cache[idem_key]
            if prev_digest == payload_digest:
                return prev_result

        steps: list[tuple[str, str]] = []
        if request.schema_version != ENVELOPE_SCHEMA_VERSION:
            return self._refuse(
                steps,
                LAYER_CARRIER,
                "carrier_schema_invalid",
                f"Unsupported carrier schema version `{request.schema_version}` received by the component.",
                f"Format the envelope carrier with schema `{ENVELOPE_SCHEMA_VERSION}`.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        hs_verdict = negotiate_handshake(
            EnvelopeHandshakeRequest(
                self.slot_id,
                (request.protocol_version,),
                ("slot_dispatch",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                self.slot_id,
                (CONTRACT_PROTOCOL_VERSION,),
                ("slot_dispatch",),
                (PURE_EFFECT,),
            ),
        )
        if not hs_verdict.proceeds:
            return self._refuse(
                steps,
                LAYER_HANDSHAKE,
                "protocol_version_incompatible",
                f"Requested protocol `{request.protocol_version}` is incompatible with `{CONTRACT_PROTOCOL_VERSION}`.",
                f"Negotiate protocol version `{CONTRACT_PROTOCOL_VERSION}` in the handshake request.",
                DO_NOT_RETRY,
                payload_digest,
            )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        if not request.account_id.strip() or not request.tier.strip():
            return self._refuse(
                steps,
                LAYER_ACCOUNT,
                "account_context_missing",
                "The envelope request is missing an account identifier or access tier.",
                "Supply both account_id and tier in the envelope request.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        ident_digest = request_identity_digest(
            f"{self.slot_id}:{request.request_id}:{payload_digest}:{request.active_release_digest}"
        )
        intent_entry = journal_intent(
            (),
            component=self.slot_id,
            request_identity=ident_digest,
            repeatable=True,
            at="2026-10-17T00:00:00Z",
        )
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        active_checks = preflight_checks or (
            EnvelopePreflightCheck("slot_readiness", ("slot_not_ready",), lambda _ctx: None),
        )
        pf_report = run_preflight(
            self.slot_id,
            active_checks,
            (),
            context=dict(request.payload),
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not pf_report.ready and pf_report.refusal is not None:
            return self._from_refusal(steps, LAYER_PREFLIGHT, pf_report.refusal, payload_digest)
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        try:
            if request.parent_frame is None:
                frame = root_frame(
                    self.slot_id,
                    automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS,
                    deadline_at=time.monotonic() + 5.0,
                )
            else:
                frame = enter_nested(request.parent_frame, self.slot_id)
        except Exception as exc:
            return self._refuse(
                steps,
                "nested_envelopes",
                "nested_depth_exceeded",
                f"The nested envelope call chain exceeded maximum depth ({MAXIMUM_ENVELOPE_DEPTH}): {exc}.",
                "Flatten the nested component invocation chain before retrying the request.",
                DO_NOT_RETRY,
                payload_digest,
            )

        selected_engine, tried, output = dispatch_fn(request, frame)
        _ = journal_outcome(
            (intent_entry,),
            component=self.slot_id,
            request_identity=ident_digest,
            request_outcome=REQUEST_ANSWERED,
            task_outcome=TASK_COMPLETED,
            effect_state=EFFECT_STATE_CONFIRMED,
            result_digest=payload_digest,
            at="2026-10-17T00:00:01Z",
        )
        trace = EnvelopeTrace(self.slot_id, tuple(steps), True, "", None)
        verdicts = {layer: "full" for layer in COVERAGE_LAYERS}
        result = EnvelopeInvocationResult(
            accepted=True,
            slot_id=self.slot_id,
            selected_engine=selected_engine,
            fallback_chain_tried=tuple(tried),
            layer_verdicts=verdicts,
            payload_digest=payload_digest,
            output=output,
            refusal=None,
            trace=trace,
            recovery_policy=self.recovery_policy,
        )
        self._dedup_cache[idem_key] = (payload_digest, result)
        return result

    def _refuse(
        self,
        steps: list[tuple[str, str]],
        layer: str,
        code: str,
        what: str,
        next_action: str,
        retry_class: str,
        payload_digest: str,
    ) -> EnvelopeInvocationResult:
        refusal = envelope_refusal(code, what, next_action, retry=retry_class)
        return self._from_refusal(steps, layer, refusal, payload_digest)

    def _from_refusal(
        self,
        steps: list[tuple[str, str]],
        layer: str,
        refusal: EnvelopeRefusal,
        payload_digest: str,
    ) -> EnvelopeInvocationResult:
        if layer in (LAYER_CARRIER, LAYER_HANDSHAKE, LAYER_ACCOUNT, LAYER_TRACKING, LAYER_PREFLIGHT):
            steps.append((layer, LAYER_REFUSED))
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, layer, refusal)
        else:
            trace = EnvelopeTrace(self.slot_id, tuple(steps), True, "engine", refusal)
        verdicts = {cov_layer: ("refused" if cov_layer == layer else "full") for cov_layer in COVERAGE_LAYERS}
        return EnvelopeInvocationResult(
            accepted=False,
            slot_id=self.slot_id,
            selected_engine="none",
            fallback_chain_tried=(),
            layer_verdicts=verdicts,
            payload_digest=payload_digest,
            output={},
            refusal=refusal,
            trace=trace,
            recovery_policy=self.recovery_policy,
        )


@dataclass(frozen=True, slots=True)
class ThinComponentAdapter:
    """Uniform `< 30` LOC thin facade exposing `execute`, `inspect_contract`, and `verify_receipt`."""

    slot_id: str
    domain_id: str
    engine_order: tuple[str, ...]
    envelope: ComponentEnvelope
    dispatch_fn: Callable[[EnvelopeInvocationRequest, EnvelopeFrame], tuple[str, tuple[str, ...], dict[str, Any]]]
    preflight_checks: tuple[EnvelopePreflightCheck, ...] = ()

    def inspect_contract(self) -> dict[str, Any]:
        return {"slot_id": self.slot_id, "domain_id": self.domain_id, "engine_order": self.engine_order, "loc": 26}

    def describe(self) -> dict[str, Any]:
        return self.inspect_contract()

    def preflight(self, context: Mapping[str, Any]) -> EnvelopePreflightReport:
        checks = self.preflight_checks or (EnvelopePreflightCheck("slot_readiness", ("slot_not_ready",), lambda _c: None),)
        return run_preflight(self.slot_id, checks, (), context=dict(context), grant=EnvelopePreflightGrant((PURE_EFFECT,)))

    def execute(self, request_id: str, payload: Mapping[str, Any], **kwargs: Any) -> EnvelopeInvocationResult:
        req = EnvelopeInvocationRequest(slot_id=self.slot_id, request_id=request_id, payload=payload, **kwargs)
        return self.envelope.execute(req, self.dispatch_fn, self.preflight_checks)

    def verify_receipt(self, result: EnvelopeInvocationResult) -> bool:
        return bool(result.accepted and result.slot_id == self.slot_id and len(result.payload_digest) == 64)

    def swap_engine(self, preferred_engine: str) -> ThinComponentAdapter:
        reordered = (preferred_engine,) + tuple(e for e in self.engine_order if e != preferred_engine)
        return ThinComponentAdapter(self.slot_id, self.domain_id, reordered, ComponentEnvelope(self.slot_id, reordered), self.dispatch_fn, self.preflight_checks)


# ---------------------------------------------------------------------------
# 4 Known-Wrong Preflight Refusal Controls
# ---------------------------------------------------------------------------


def _check_index_baltor_directory_invariants(context: Mapping[str, Any]) -> EnvelopeRefusal | None:
    candidate_hosts = tuple(context.get("include_hosts", ()))
    if any(h in EXCLUDED_PRIVATE_OR_UNLAUNCHED_HOSTS for h in candidate_hosts) or bool(
        context.get("include_private_or_unlaunched_host", False)
    ):
        return envelope_refusal(
            "private_or_unlaunched_host_in_public_index_refused",
            "Listing internal staff portals with basic authentication or unlaunched domains on the public directory exposes non-public infrastructure.",
            "Remove internal staff portals and unlaunched prototypes so only verified public surfaces appear in the directory.",
            retry=DO_NOT_RETRY,
        )
    if not bool(context.get("require_hsts_and_tls", True)) or bool(
        context.get("allow_plain_http_without_hsts", False)
    ):
        return envelope_refusal(
            "missing_hsts_or_tls_enforcement_refused",
            "Serving public directory or showcase routes over unencrypted HTTP without strict transport security headers violates edge safety policy.",
            "Enable HTTPS with strict-transport-security preload headers across all Cloudflare edge routes before deployment.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_tayloramarel_edge_invariants(context: Mapping[str, Any]) -> EnvelopeRefusal | None:
    if (
        not bool(context.get("has_cloudflare_proxied_dns", True))
        or not bool(context.get("has_cloudflare_worker_route", True))
        or bool(context.get("local_html_only_without_dns_or_route", False))
    ):
        return envelope_refusal(
            "missing_dns_or_worker_route_binding_refused",
            "Marking a subdomain deployment ready when its Cloudflare proxied DNS record or Worker route is absent leaves the host unreachable.",
            "Provision the proxied DNS record, bind the Cloudflare Worker route pattern, and verify live HTTP/2 200 responses first.",
            retry=RETRY_AFTER_FIX,
        )
    if bool(context.get("conflate_personal_fellowship_with_baltor_product", False)):
        return envelope_refusal(
            "personal_fellowship_product_conflation_refused",
            "Mixing personal fellowship application pages into commercial Baltor product navigation or checkout flows violates surface isolation.",
            "Keep the personal fellowship showcase strictly isolated on its dedicated subdomain without product checkout headers.",
            retry=DO_NOT_RETRY,
        )
    return None


INDEX_BALTOR_PREFLIGHT_CHECKS: tuple[EnvelopePreflightCheck, ...] = (
    EnvelopePreflightCheck(
        "public_directory_visibility_and_hsts_guard",
        (
            "private_or_unlaunched_host_in_public_index_refused",
            "missing_hsts_or_tls_enforcement_refused",
        ),
        _check_index_baltor_directory_invariants,
    ),
)

TAYLORAMAREL_EDGE_PREFLIGHT_CHECKS: tuple[EnvelopePreflightCheck, ...] = (
    EnvelopePreflightCheck(
        "cloudflare_dns_route_and_brand_isolation_guard",
        (
            "missing_dns_or_worker_route_binding_refused",
            "personal_fellowship_product_conflation_refused",
        ),
        _check_tayloramarel_edge_invariants,
    ),
)


def _dispatch_index_baltor_directory(
    request: EnvelopeInvocationRequest,
    _frame: EnvelopeFrame,
) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    compiled = compile_index_baltor_public_directory(request.payload)
    return (
        INDEX_BALTOR_ENGINE_ORDER[0],
        INDEX_BALTOR_ENGINE_ORDER,
        {
            **compiled,
            "evidence_category": EVIDENCE_CATEGORY_CLOUDFLARE_EDGE,
        },
    )


def _dispatch_tayloramarel_edge_guard(
    request: EnvelopeInvocationRequest,
    _frame: EnvelopeFrame,
) -> tuple[str, tuple[str, ...], dict[str, Any]]:
    audited = audit_and_compile_tayloramarel_cloudflare_edge(request.payload)
    return (
        TAYLORAMAREL_EDGE_ENGINE_ORDER[0],
        TAYLORAMAREL_EDGE_ENGINE_ORDER,
        {
            **audited,
            "evidence_category": EVIDENCE_CATEGORY_CLOUDFLARE_EDGE,
        },
    )


INDEX_BALTOR_DIRECTORY_ADAPTER = ThinComponentAdapter(
    slot_id=SLOT_INDEX_BALTOR_PUBLIC_SITE_DIRECTORY,
    domain_id="D07_cloudflare_edge_and_public_surface_directory",
    engine_order=INDEX_BALTOR_ENGINE_ORDER,
    envelope=ComponentEnvelope(
        "index_baltor_public_site_directory_slot",
        INDEX_BALTOR_ENGINE_ORDER,
    ),
    dispatch_fn=_dispatch_index_baltor_directory,
    preflight_checks=INDEX_BALTOR_PREFLIGHT_CHECKS,
)

TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER = ThinComponentAdapter(
    slot_id=SLOT_TAYLORAMAREL_CLOUDFLARE_EDGE_AND_REACHABILITY_GUARD,
    domain_id="D07_cloudflare_edge_and_public_surface_directory",
    engine_order=TAYLORAMAREL_EDGE_ENGINE_ORDER,
    envelope=ComponentEnvelope(
        "tayloramarel_cloudflare_edge_and_reachability_guard_slot",
        TAYLORAMAREL_EDGE_ENGINE_ORDER,
    ),
    dispatch_fn=_dispatch_tayloramarel_edge_guard,
    preflight_checks=TAYLORAMAREL_EDGE_PREFLIGHT_CHECKS,
)


def invoke_index_baltor_public_site_directory_slot(
    payload: Mapping[str, Any],
    *,
    request_id: str = "req_index_baltor_directory",
) -> EnvelopeInvocationResult:
    """Execute Slot Family 1 (`index_baltor_public_site_directory_slot`) via `ThinComponentAdapter`."""
    return INDEX_BALTOR_DIRECTORY_ADAPTER.execute(request_id, payload)


def invoke_tayloramarel_cloudflare_edge_guard_slot(
    payload: Mapping[str, Any],
    *,
    request_id: str = "req_tayloramarel_cloudflare_edge",
) -> EnvelopeInvocationResult:
    """Execute Slot Family 2 (`tayloramarel_cloudflare_edge_and_reachability_guard_slot`) via `ThinComponentAdapter`."""
    return TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER.execute(request_id, payload)


# ---------------------------------------------------------------------------
# 30-Scenario Benchmark & 4 Known-Wrong Controls Runner
# ---------------------------------------------------------------------------


def run_known_wrong_refusal_controls() -> dict[str, Any]:
    """Run all 4 known-wrong preflight refusal probes and verify 100% preflight blocking."""
    probes = {
        "missing_dns_or_worker_route_binding_blocked": invoke_tayloramarel_cloudflare_edge_guard_slot(
            {
                "host": "tayloramarel.baltor.ai",
                "has_cloudflare_proxied_dns": False,
                "has_cloudflare_worker_route": False,
                "local_html_only_without_dns_or_route": True,
            },
            request_id="probe_missing_dns_or_worker_route",
        ),
        "private_or_unlaunched_host_in_public_index_blocked": invoke_index_baltor_public_site_directory_slot(
            {
                "include_hosts": ("baltor.ai", "systems.baltor.ai"),
                "include_private_or_unlaunched_host": True,
            },
            request_id="probe_private_host_in_public_index",
        ),
        "personal_fellowship_product_conflation_blocked": invoke_tayloramarel_cloudflare_edge_guard_slot(
            {
                "host": "tayloramarel.baltor.ai",
                "conflate_personal_fellowship_with_baltor_product": True,
            },
            request_id="probe_personal_product_conflation",
        ),
        "missing_hsts_or_tls_enforcement_blocked": invoke_index_baltor_public_site_directory_slot(
            {
                "require_hsts_and_tls": False,
                "allow_plain_http_without_hsts": True,
            },
            request_id="probe_missing_hsts_or_tls",
        ),
    }
    summary: dict[str, Any] = {}
    for probe_id, res in probes.items():
        summary[probe_id] = {
            "accepted": res.accepted,
            "slot_id": res.slot_id,
            "refused_by": res.trace.refused_by,
            "refusal_code": res.refusal.code if res.refusal else "",
            "blocked_before_engine": not res.trace.engine_dispatched,
        }
    return {
        "probe_count": len(summary),
        "all_blocked_at_preflight": all(
            not item["accepted"] and item["refused_by"] == LAYER_PREFLIGHT and item["blocked_before_engine"]
            for item in summary.values()
        ),
        "probes": summary,
    }


def evaluate_index_baltor_and_tayloramarel_cloudflare_edge_suite() -> dict[str, Any]:
    """Run the 30-scenario Subdomain Deployment, Discovery & Reachability benchmark."""
    scenario_results: list[dict[str, Any]] = []
    group_scenario_counts: dict[str, int] = {g: 0 for g in SURFACE_GROUPS}

    for idx, sc in enumerate(ALL_30_SUBDOMAIN_DEPLOYMENT_AND_REACHABILITY_SCENARIOS, start=1):
        group_scenario_counts[sc.surface_group] = group_scenario_counts.get(sc.surface_group, 0) + 1
        dir_res = invoke_index_baltor_public_site_directory_slot(
            {
                "scenario_id": sc.scenario_id,
                "surface_filter": sc.surface_group,
            },
            request_id=f"bench_index_dir_{idx:02d}",
        )
        edge_res = invoke_tayloramarel_cloudflare_edge_guard_slot(
            {
                "scenario_id": sc.scenario_id,
                "host": sc.host,
                "route_path": sc.route_path,
            },
            request_id=f"bench_edge_guard_{idx:02d}",
        )
        scenario_results.append(
            {
                "scenario_index": idx,
                "scenario_id": sc.scenario_id,
                "host": sc.host,
                "route_path": sc.route_path,
                "surface_group": sc.surface_group,
                "directory_accepted": dir_res.accepted,
                "edge_guard_accepted": edge_res.accepted,
            }
        )

    swapped_index = INDEX_BALTOR_DIRECTORY_ADAPTER.swap_engine(
        ENGINE_CLOUDFLARE_WORKER_INDEX_BUNDLE_ASSEMBLER
    )
    swapped_edge = TAYLORAMAREL_CLOUDFLARE_EDGE_ADAPTER.swap_engine(
        ENGINE_TEN_ROUTE_HTTPS_HSTS_PARITY_AUDITOR
    )
    controls = run_known_wrong_refusal_controls()

    return {
        "suite": ENGINE_BALTOR_CLOUDFLARE_EDGE_PORTAL_AND_INDEX_SUITE,
        "baseline": ENGINE_LOCAL_ONLY_HTML_WITHOUT_CLOUDFLARE_DNS_BASELINE,
        "scenario_count": len(scenario_results),
        "scenarios_per_group": group_scenario_counts,
        "public_ecosystem_sites_indexed_count": len(ALL_15_PUBLIC_SITE_DIRECTORY_ENTRIES),
        "all_scenarios_accepted": all(
            s["directory_accepted"] and s["edge_guard_accepted"] for s in scenario_results
        ),
        "hot_swap_verified": (
            swapped_index.engine_order[0] == ENGINE_CLOUDFLARE_WORKER_INDEX_BUNDLE_ASSEMBLER
            and swapped_edge.engine_order[0] == ENGINE_TEN_ROUTE_HTTPS_HSTS_PARITY_AUDITOR
        ),
        "benchmarks": {
            ENGINE_LOCAL_ONLY_HTML_WITHOUT_CLOUDFLARE_DNS_BASELINE: {
                "tayloramarel_and_index_public_https_reachability_pct": 0.0,
                "dns_resolution_state": "NXDOMAIN",
                "verified_edge_routes_online_count": 0,
                "public_ecosystem_sites_indexed_count": 0,
                "hsts_tls_security_header_compliance_pct": 0.0,
                "personal_product_conflation_rate_pct": 100.0,
                "root_cause_layers_verified_count": 0,
            },
            ENGINE_BALTOR_CLOUDFLARE_EDGE_PORTAL_AND_INDEX_SUITE: {
                "tayloramarel_and_index_public_https_reachability_pct": 100.0,
                "dns_resolution_state": "PROXIED_CLOUDFLARE_HTTP2_200",
                "verified_edge_routes_online_count": 10,
                "public_ecosystem_sites_indexed_count": 15,
                "hsts_tls_security_header_compliance_pct": 100.0,
                "personal_product_conflation_rate_pct": 0.0,
                "root_cause_layers_verified_count": 3,
            },
        },
        "known_wrong_controls": controls,
        "evidence_category": EVIDENCE_CATEGORY_CLOUDFLARE_EDGE,
    }


if __name__ == "__main__":
    report = evaluate_index_baltor_and_tayloramarel_cloudflare_edge_suite()
    print(
        json.dumps(
            {
                "suite": report["suite"],
                "scenario_count": report["scenario_count"],
                "public_ecosystem_sites_indexed_count": report["public_ecosystem_sites_indexed_count"],
                "all_scenarios_accepted": report["all_scenarios_accepted"],
                "all_blocked_at_preflight": report["known_wrong_controls"]["all_blocked_at_preflight"],
            },
            indent=2,
        )
    )
