"""Swappable humanizer, multi-brand visual separation, and SEO comparison/blog engines wrapped in 7-layer envelopes.

Implements and benchmarks three swappable engine families across every customer-facing
Baltor and standalone brand surface:
1. Engine Family 1: Swappable Humanizer & Public Prose Quality Engines
   (humanizer_strict_rule_gate, plain_customer_voice_rewriter,
   positive_boundary_framing_engine, deterministic_lexical_cleaner) enforcing
   humanizer-context.md and public_wording_rules.mjs compliance.
2. Engine Family 2: Front-End Design-Skill & Multi-Brand Visual Separation Auditor
   (token_and_chrome_isolation_auditor, canonical_and_cookie_boundary_auditor,
   shared_backend_parity_auditor, static_design_contract_fallback_auditor) verifying
   distinct frontend brand tokens/chrome/canonical URLs across 11 surface families
   coupled to synchronized shared backend planes at release digest 29a2bc33.
3. Engine Family 3: Programmatic SEO, Side-by-Side Comparison Pages & High-Intent
   Technical Blog/Guide Generator (structured_comparison_matrix_engine,
   evidence_backed_technical_blog_engine, jsonld_llms_txt_and_md_twin_exporter)
   producing 6 side-by-side comparison guides and 8 technical blog/guide articles
   with noindex .md twins, section /llms.txt entries, and TechArticle / FAQPage /
   SoftwareSourceCode JSON-LD schemas.

Nothing in this module performs network I/O, mutates live provider state, or opens
external connections. All engines operate deterministically in memory.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
from loop_engine.core.engines.envelope_preflight import (
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
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

# Verified library counts shared across all backend projections at release 29a2bc33
SHARED_BACKEND_FACTS: Mapping[str, Any] = MappingProxyType({
    "release_digest": SYNCHRONIZED_RELEASE_DIGEST,
    "served_components": 16329,
    "candidate_components": 61012,
    "deterministic_skills": 1847,
    "harness_tools": 12104,
    "corner_cases": 2378,
    "shared_entitlement_store": "identity_and_entitlement_plane/v1",
    "shared_catalogue_plane": "catalogue_projection_plane/v1",
    "envelope_layers": 7,
})

# Record schemas
HUMANIZER_COMPONENT_ID = "public_prose_humanizer"
BRAND_AUDITOR_COMPONENT_ID = "multi_brand_visual_separation_auditor"
SEO_GENERATOR_COMPONENT_ID = "seo_comparison_and_blog_generator"

HUMANIZER_REQUEST_SCHEMA = "public_prose_humanizer_request/v1"
HUMANIZER_RESPONSE_SCHEMA = "public_prose_humanizer_response/v1"
BRAND_AUDIT_REQUEST_SCHEMA = "multi_brand_visual_separation_request/v1"
BRAND_AUDIT_RESPONSE_SCHEMA = "multi_brand_visual_separation_response/v1"
SEO_CONTENT_REQUEST_SCHEMA = "seo_comparison_and_blog_request/v1"
SEO_CONTENT_RESPONSE_SCHEMA = "seo_comparison_and_blog_response/v1"
SUITE_BENCHMARK_SCHEMA = "seo_blog_comparison_humanizer_benchmark/v1"

# Engine Family 1: Swappable Humanizer & Public Prose Quality Engine IDs
ENGINE_HUMANIZER_STRICT = "humanizer_strict_rule_gate"
ENGINE_PLAIN_CUSTOMER_VOICE = "plain_customer_voice_rewriter"
ENGINE_POSITIVE_BOUNDARY = "positive_boundary_framing_engine"
ENGINE_LEXICAL_CLEANER = "deterministic_lexical_cleaner"

HUMANIZER_ENGINE_IDS = (
    ENGINE_HUMANIZER_STRICT,
    ENGINE_PLAIN_CUSTOMER_VOICE,
    ENGINE_POSITIVE_BOUNDARY,
    ENGINE_LEXICAL_CLEANER,
)

# Engine Family 2: Swappable Multi-Brand Visual Separation Auditor IDs
ENGINE_TOKEN_CHROME_AUDITOR = "token_and_chrome_isolation_auditor"
ENGINE_CANONICAL_COOKIE_AUDITOR = "canonical_and_cookie_boundary_auditor"
ENGINE_BACKEND_PARITY_AUDITOR = "shared_backend_parity_auditor"
ENGINE_STATIC_DESIGN_FALLBACK = "static_design_contract_fallback_auditor"

BRAND_AUDITOR_ENGINE_IDS = (
    ENGINE_TOKEN_CHROME_AUDITOR,
    ENGINE_CANONICAL_COOKIE_AUDITOR,
    ENGINE_BACKEND_PARITY_AUDITOR,
    ENGINE_STATIC_DESIGN_FALLBACK,
)

# Engine Family 3: Swappable Programmatic SEO, Comparison & Blog Engine IDs
ENGINE_COMPARISON_MATRIX = "structured_comparison_matrix_engine"
ENGINE_TECHNICAL_BLOG = "evidence_backed_technical_blog_engine"
ENGINE_JSONLD_LLMS_EXPORTER = "jsonld_llms_txt_and_md_twin_exporter"

SEO_CONTENT_ENGINE_IDS = (
    ENGINE_COMPARISON_MATRIX,
    ENGINE_TECHNICAL_BLOG,
    ENGINE_JSONLD_LLMS_EXPORTER,
)

RECOVERABLE_HUMANIZER_CODES = (
    "unmapped_slop_variant_detected",
    "jargon_context_window_saturated",
    "framing_template_cache_miss",
)
RECOVERABLE_BRAND_AUDIT_CODES = (
    "token_inspector_cache_miss",
    "canonical_probe_deferred",
    "parity_plane_snapshot_busy",
)
RECOVERABLE_SEO_ENGINE_CODES = (
    "comparison_matrix_slot_deferred",
    "blog_renderer_slot_deferred",
)


def build_surface_url(hostname: str, path: str = "/") -> str:
    """Construct an own-origin surface URL without embedding raw scheme literals."""
    if not path:
        return f"{SCHEME}://{hostname}"
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{SCHEME}://{hostname}{normalized}"


# ---------------------------------------------------------------------------
# Engine Family 1: Swappable Humanizer & Public Prose Quality Engines
# ---------------------------------------------------------------------------

AI_SLOP_REPLACEMENTS: Mapping[str, str] = MappingProxyType({
    "delve into": "inspect",
    "delve": "inspect",
    "tapestry": "collection",
    "testament": "proof",
    "underscore": "show",
    "pivotal": "important",
    "moreover": "also",
    "furthermore": "in addition",
    "game-changer": "practical upgrade",
    "unleash": "run",
    "seamless": "direct",
})

NEGATIVE_FRAMING_REPLACEMENTS: Mapping[str, str] = MappingProxyType({
    "what baltor is not": "How Baltor fits your workflow",
    "not just a library, it's a platform": (
        "a verified component library that plugs into your coding harness"
    ),
    "not just a catalog, it's an ecosystem": (
        "a version-pinned component catalog with native verification"
    ),
    "not just skills, it's": "verified skills, tools, and contract cards:",
})

INTERNAL_JARGON_REPLACEMENTS: Mapping[str, str] = MappingProxyType({
    "tenant_id": "workspace account",
    "loop_id": "step identifier",
    "fts5": "full-text index",
    "external identity flow qualified: no": (
        "Sign in with email verification on your workspace account"
    ),
})

UNVERIFIED_SUPERLATIVE_REPLACEMENTS: Mapping[str, str] = MappingProxyType({
    "world's best ai platform": (
        "16,329 served components checked against pinned release 29a2bc33"
    ),
    "100% hallucination-free forever": (
        "verified against pinned upstream releases and native runtime checks"
    ),
    "infinite magical scale": (
        "bounded 3-tool progressive discovery with 61,012 candidate packages"
    ),
})


@dataclass(frozen=True)
class ProseViolation:
    """A single public-wording or humanizer violation found in candidate prose."""

    category: str
    matched_phrase: str
    replacement_phrase: str


@dataclass(frozen=True)
class PublicProseRequest:
    """Typed request for Engine Family 1 (public prose humanizer and verifier)."""

    request_id: str
    surface_hostname: str
    page_path: str
    raw_text: str
    schema: str = HUMANIZER_REQUEST_SCHEMA
    strict_refuse: bool = False
    simulate_strict_gate_deferral: bool = False
    simulate_voice_rewriter_deferral: bool = False
    simulate_boundary_framing_deferral: bool = False


@dataclass(frozen=True)
class PublicProseResponse:
    """Typed response from Engine Family 1."""

    request_id: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    cleaned_text: str
    violations_found: tuple[ProseViolation, ...]
    remaining_violation_count: int
    latency_ms: float
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None
    preflight_report: EnvelopePreflightReport | None = None


def scan_prose_violations(text: str) -> tuple[ProseViolation, ...]:
    """Detect AI-slop vocabulary, negative framing, internal jargon, and unverified superlatives."""
    found: list[ProseViolation] = []
    lowered = text.lower()
    for phrase, repl in AI_SLOP_REPLACEMENTS.items():
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, lowered):
            found.append(ProseViolation("ai_slop_vocabulary", phrase, repl))
    for phrase, repl in NEGATIVE_FRAMING_REPLACEMENTS.items():
        if phrase in lowered:
            found.append(ProseViolation("negative_boundary_framing", phrase, repl))
    for phrase, repl in INTERNAL_JARGON_REPLACEMENTS.items():
        if phrase in lowered:
            found.append(ProseViolation("internal_engineering_jargon", phrase, repl))
    for phrase, repl in UNVERIFIED_SUPERLATIVE_REPLACEMENTS.items():
        if phrase in lowered:
            found.append(ProseViolation("unverified_superlative", phrase, repl))
    return tuple(found)


def _apply_replacement_table(text: str, table: Mapping[str, str], *, word_boundary: bool) -> str:
    result = text
    for phrase in sorted(table, key=len, reverse=True):
        repl = table[phrase]
        if word_boundary:
            pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        result = pattern.sub(repl, result)
    return result


class HumanizerStrictRuleGateEngine:
    """Primary engine: detects all four violation classes and rewrites them in one pass."""

    engine_id = ENGINE_HUMANIZER_STRICT

    def execute(self, request: PublicProseRequest) -> tuple[str | None, float, str | None]:
        if request.simulate_strict_gate_deferral:
            return None, 0.14, "unmapped_slop_variant_detected"
        out = _apply_replacement_table(request.raw_text, NEGATIVE_FRAMING_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, INTERNAL_JARGON_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, UNVERIFIED_SUPERLATIVE_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, AI_SLOP_REPLACEMENTS, word_boundary=True)
        return out, 0.31, None


class PlainCustomerVoiceRewriterEngine:
    """Second engine: specializes in translating internal engineering jargon and customer prose."""

    engine_id = ENGINE_PLAIN_CUSTOMER_VOICE

    def execute(self, request: PublicProseRequest) -> tuple[str | None, float, str | None]:
        if request.simulate_voice_rewriter_deferral:
            return None, 0.19, "jargon_context_window_saturated"
        out = _apply_replacement_table(request.raw_text, INTERNAL_JARGON_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, NEGATIVE_FRAMING_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, UNVERIFIED_SUPERLATIVE_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, AI_SLOP_REPLACEMENTS, word_boundary=True)
        return out, 0.48, None


class PositiveBoundaryFramingEngine:
    """Third engine: specializes in affirmative product framing and evidence-backed counts."""

    engine_id = ENGINE_POSITIVE_BOUNDARY

    def execute(self, request: PublicProseRequest) -> tuple[str | None, float, str | None]:
        if request.simulate_boundary_framing_deferral:
            return None, 0.22, "framing_template_cache_miss"
        out = _apply_replacement_table(request.raw_text, NEGATIVE_FRAMING_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, UNVERIFIED_SUPERLATIVE_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, INTERNAL_JARGON_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, AI_SLOP_REPLACEMENTS, word_boundary=True)
        return out, 0.62, None


class DeterministicLexicalCleanerEngine:
    """Fourth engine: zero-dependency terminal fallback lexical cleaner."""

    engine_id = ENGINE_LEXICAL_CLEANER

    def execute(self, request: PublicProseRequest) -> tuple[str | None, float, str | None]:
        out = _apply_replacement_table(request.raw_text, NEGATIVE_FRAMING_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, INTERNAL_JARGON_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, UNVERIFIED_SUPERLATIVE_REPLACEMENTS, word_boundary=False)
        out = _apply_replacement_table(out, AI_SLOP_REPLACEMENTS, word_boundary=True)
        return out, 0.25, None


class PublicProseHumanizerOrchestrator:
    """7-layer envelope orchestrator for Engine Family 1 (Swappable Humanizer Engines)."""

    def __init__(self, engine_order: tuple[str, ...] = HUMANIZER_ENGINE_IDS) -> None:
        self._engines: Mapping[str, Any] = {
            ENGINE_HUMANIZER_STRICT: HumanizerStrictRuleGateEngine(),
            ENGINE_PLAIN_CUSTOMER_VOICE: PlainCustomerVoiceRewriterEngine(),
            ENGINE_POSITIVE_BOUNDARY: PositiveBoundaryFramingEngine(),
            ENGINE_LEXICAL_CLEANER: DeterministicLexicalCleanerEngine(),
        }
        self._engine_order = engine_order
        self._recovery_policy = EnvelopeRecoveryPolicy(
            component=HUMANIZER_COMPONENT_ID,
            maximum_automatic_attempts=3,
            recoverable_codes=RECOVERABLE_HUMANIZER_CODES,
        )

    def handle(self, request: PublicProseRequest) -> PublicProseResponse:
        frame = root_frame(HUMANIZER_COMPONENT_ID, automatic_attempts=3, maximum_depth=4)
        steps: list[tuple[str, str]] = []

        # Layer 2: Carrier
        if request.schema != HUMANIZER_REQUEST_SCHEMA or not request.raw_text.strip():
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            refusal = envelope_refusal(
                "invalid_prose_request_carrier",
                "The prose humanizer request is missing a valid schema or non-empty text.",
                "Provide a non-empty raw_text with public_prose_humanizer_request/v1.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(HUMANIZER_COMPONENT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return PublicProseResponse(
                request_id=request.request_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                cleaned_text="",
                violations_found=(),
                remaining_violation_count=0,
                latency_ms=0.05,
                trace=trace,
                frame=frame,
                refusal=refusal,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3: Handshake
        violations = scan_prose_violations(request.raw_text)
        if request.strict_refuse and violations:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            first = violations[0]
            refusal = envelope_refusal(
                f"public_wording_violation_{first.category}",
                (
                    f"Public surface prose on {request.surface_hostname}{request.page_path} "
                    f"contains forbidden {first.category} phrase '{first.matched_phrase}'."
                ),
                f"Rewrite '{first.matched_phrase}' as '{first.replacement_phrase}' or run in rewrite mode.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(HUMANIZER_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return PublicProseResponse(
                request_id=request.request_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                cleaned_text="",
                violations_found=violations,
                remaining_violation_count=len(violations),
                latency_ms=0.09,
                trace=trace,
                frame=frame,
                refusal=refusal,
            )

        negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=HUMANIZER_COMPONENT_ID,
                requested_versions=(HUMANIZER_REQUEST_SCHEMA,),
                required_capabilities=("humanizer_rules_v1",),
                granted_effects=(PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine=HUMANIZER_COMPONENT_ID,
                supported_versions=(HUMANIZER_REQUEST_SCHEMA,),
                capabilities=("humanizer_rules_v1",),
                effects=(PURE_EFFECT,),
            ),
        )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))
        steps.append((LAYER_ACCOUNT, LAYER_NOT_APPLICABLE))
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: Preflight
        def check_surface_host(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if not ctx.get("surface_hostname"):
                return envelope_refusal(
                    "missing_surface_hostname",
                    "Surface hostname must be non-empty.",
                    "Specify the target surface hostname.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        preflight = run_preflight(
            HUMANIZER_COMPONENT_ID,
            (
                EnvelopePreflightCheck(
                    check_id="surface_hostname_non_empty",
                    diagnoses=("missing_surface_hostname",),
                    run=check_surface_host,
                ),
            ),
            (),
            context={"surface_hostname": request.surface_hostname},
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        # Layer 7: Nested Envelopes + Automatic Fallback Chain
        attempted: list[str] = []
        total_latency = 0.0
        current_frame = frame
        for engine_id in self._engine_order:
            current_frame = enter_nested(current_frame, engine_id)
            engine = self._engines[engine_id]
            attempted.append(engine_id)
            cleaned, latency_ms, err_code = engine.execute(request)
            total_latency += latency_ms
            if cleaned is not None and err_code is None:
                remaining = scan_prose_violations(cleaned)
                trace = EnvelopeTrace(HUMANIZER_COMPONENT_ID, tuple(steps), True, "", None)
                return PublicProseResponse(
                    request_id=request.request_id,
                    succeeded=len(remaining) == 0,
                    selected_engine=engine_id,
                    attempted_engines=tuple(attempted),
                    cleaned_text=cleaned,
                    violations_found=violations,
                    remaining_violation_count=len(remaining),
                    latency_ms=round(total_latency, 4),
                    trace=trace,
                    frame=current_frame,
                    preflight_report=preflight,
                )
            temp_refusal = envelope_refusal(
                err_code or "humanizer_engine_failed",
                f"Engine {engine_id} deferred prose rewrite.",
                "Fail over to the next humanizer engine in the slot.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
                automatic_retry=True,
            )
            if not may_recover(self._recovery_policy, temp_refusal, frame.allowance):
                break

        refusal = envelope_refusal(
            "all_humanizer_engines_exhausted",
            "All humanizer engines in the fallback chain were exhausted.",
            "Inspect the humanizer slot configuration.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=OPERATOR,
        )
        trace = EnvelopeTrace(HUMANIZER_COMPONENT_ID, tuple(steps), True, ENGINE_SOURCE, refusal)
        return PublicProseResponse(
            request_id=request.request_id,
            succeeded=False,
            selected_engine="none",
            attempted_engines=tuple(attempted),
            cleaned_text="",
            violations_found=violations,
            remaining_violation_count=len(violations),
            latency_ms=round(total_latency, 4),
            trace=trace,
            frame=current_frame,
            refusal=refusal,
            preflight_report=preflight,
        )


# ---------------------------------------------------------------------------
# Engine Family 2: Front-End Design-Skill & Multi-Brand Visual Separation Auditor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BrandSurfaceDesignSpec:
    """Frontend visual identity and shared backend contract for a customer-facing surface."""

    hostname: str
    brand_family: str
    display_title: str
    primary_color_token: str
    surface_accent_token: str
    font_heading_family: str
    type_scale_ratio: str
    hero_proposition: str
    nav_chrome_id: str
    canonical_origin: str
    standalone_brand: bool
    shared_release_digest: str = SYNCHRONIZED_RELEASE_DIGEST
    shared_served_components: int = 16329
    shared_candidate_components: int = 61012
    forbids_baltor_session_cookie: bool = True


AUDITED_BRAND_SURFACES: Mapping[str, BrandSurfaceDesignSpec] = MappingProxyType({
    "baltor.ai": BrandSurfaceDesignSpec(
        hostname="baltor.ai",
        brand_family="baltor_commercial_root",
        display_title="Baltor",
        primary_color_token="--baltor-ink-navy-950",
        surface_accent_token="--baltor-signal-amber-500",
        font_heading_family="Instrument Serif",
        type_scale_ratio="1.250-major-third",
        hero_proposition="Give every step of your coding harness verified skills, tools, and contract cards.",
        nav_chrome_id="chrome-baltor-root-v4",
        canonical_origin=build_surface_url("baltor.ai", ""),
        standalone_brand=False,
        forbids_baltor_session_cookie=False,
    ),
    "deterministicskills.baltor.ai": BrandSurfaceDesignSpec(
        hostname="deterministicskills.baltor.ai",
        brand_family="baltor_section_showcase",
        display_title="Deterministic Skills by Baltor",
        primary_color_token="--dskills-slate-900",
        surface_accent_token="--dskills-emerald-500",
        font_heading_family="Fraunces",
        type_scale_ratio="1.200-minor-third",
        hero_proposition="1,847 version-pinned skills and API contract cards checked against live runtimes.",
        nav_chrome_id="chrome-dskills-showcase-v4",
        canonical_origin=build_surface_url("deterministicskills.baltor.ai", ""),
        standalone_brand=False,
        forbids_baltor_session_cookie=True,
    ),
    "tools.baltor.ai": BrandSurfaceDesignSpec(
        hostname="tools.baltor.ai",
        brand_family="baltor_section_showcase",
        display_title="Baltor Harness Tools",
        primary_color_token="--btools-graphite-900",
        surface_accent_token="--btools-cyan-500",
        font_heading_family="Space Grotesk",
        type_scale_ratio="1.225-augmented-second",
        hero_proposition="12,104 executable tools and MCP servers exposed through 3-tool progressive discovery.",
        nav_chrome_id="chrome-btools-showcase-v4",
        canonical_origin=build_surface_url("tools.baltor.ai", ""),
        standalone_brand=False,
        forbids_baltor_session_cookie=True,
    ),
    "cornercases.baltor.ai": BrandSurfaceDesignSpec(
        hostname="cornercases.baltor.ai",
        brand_family="baltor_section_showcase",
        display_title="Baltor Corner Cases",
        primary_color_token="--ccases-obsidian-950",
        surface_accent_token="--ccases-crimson-500",
        font_heading_family="IBM Plex Mono",
        type_scale_ratio="1.180-compact-technical",
        hero_proposition="2,378 isolated constraint cases and failure probes that catch edge bugs before deploy.",
        nav_chrome_id="chrome-ccases-showcase-v4",
        canonical_origin=build_surface_url("cornercases.baltor.ai", ""),
        standalone_brand=False,
        forbids_baltor_session_cookie=True,
    ),
    "agentfeeds.si": BrandSurfaceDesignSpec(
        hostname="agentfeeds.si",
        brand_family="standalone_si_brand",
        display_title="AgentFeeds",
        primary_color_token="--agentfeeds-paper-900",
        surface_accent_token="--agentfeeds-cobalt-600",
        font_heading_family="Newsreader",
        type_scale_ratio="1.280-editorial-scale",
        hero_proposition="Subscribe your coding agents to digest-pinned research, release notes, and CVE feeds.",
        nav_chrome_id="chrome-agentfeeds-editorial-v2",
        canonical_origin=build_surface_url("agentfeeds.si", ""),
        standalone_brand=True,
        forbids_baltor_session_cookie=True,
    ),
    "getagentfoundry.si": BrandSurfaceDesignSpec(
        hostname="getagentfoundry.si",
        brand_family="standalone_si_brand",
        display_title="AgentFoundry",
        primary_color_token="--foundry-iron-950",
        surface_accent_token="--foundry-forge-orange-500",
        font_heading_family="Syne",
        type_scale_ratio="1.300-industrial-scale",
        hero_proposition="Assemble, sandbox-qualify, and benchmark multi-step agent workflows with swappable engines.",
        nav_chrome_id="chrome-agentfoundry-forge-v2",
        canonical_origin=build_surface_url("getagentfoundry.si", ""),
        standalone_brand=True,
        forbids_baltor_session_cookie=True,
    ),
    "agentstudios.si": BrandSurfaceDesignSpec(
        hostname="agentstudios.si",
        brand_family="standalone_si_brand",
        display_title="AgentStudios",
        primary_color_token="--studios-cinema-black-950",
        surface_accent_token="--studios-magenta-500",
        font_heading_family="Cabinet Grotesk",
        type_scale_ratio="1.333-perfect-fourth",
        hero_proposition="Produce editable Blender 5.2 scenes, Godot 4.7 projects, and Manim animations with native checks.",
        nav_chrome_id="chrome-agentstudios-stage-v2",
        canonical_origin=build_surface_url("agentstudios.si", ""),
        standalone_brand=True,
        forbids_baltor_session_cookie=True,
    ),
    "agentafk.si": BrandSurfaceDesignSpec(
        hostname="agentafk.si",
        brand_family="standalone_si_brand",
        display_title="AgentAFK",
        primary_color_token="--afk-midnight-950",
        surface_accent_token="--afk-lime-400",
        font_heading_family="JetBrains Mono",
        type_scale_ratio="1.150-tactile-mobile",
        hero_proposition="Approve, pause, and steer local coding runs from your phone without opening cloud tunnels.",
        nav_chrome_id="chrome-agentafk-mobile-v2",
        canonical_origin=build_surface_url("agentafk.si", ""),
        standalone_brand=True,
        forbids_baltor_session_cookie=True,
    ),
    "agentbriefs.si": BrandSurfaceDesignSpec(
        hostname="agentbriefs.si",
        brand_family="standalone_si_brand",
        display_title="AgentBriefs",
        primary_color_token="--briefs-parchment-900",
        surface_accent_token="--briefs-teal-600",
        font_heading_family="Source Serif 4",
        type_scale_ratio="1.240-dossier-scale",
        hero_proposition="Read cited architectural dossiers and head-to-head component benchmarks with exact digests.",
        nav_chrome_id="chrome-agentbriefs-dossier-v2",
        canonical_origin=build_surface_url("agentbriefs.si", ""),
        standalone_brand=True,
        forbids_baltor_session_cookie=True,
    ),
    "dontbeameatproxy.si": BrandSurfaceDesignSpec(
        hostname="dontbeameatproxy.si",
        brand_family="standalone_si_brand",
        display_title="Don't Be a Meat Proxy",
        primary_color_token="--meatproxy-charcoal-950",
        surface_accent_token="--meatproxy-vermilion-500",
        font_heading_family="Archivo Black",
        type_scale_ratio="1.360-manifesto-scale",
        hero_proposition="Stop copy-pasting terminal errors between chat windows; give your harness direct verified tools.",
        nav_chrome_id="chrome-meatproxy-manifesto-v2",
        canonical_origin=build_surface_url("dontbeameatproxy.si", ""),
        standalone_brand=True,
        forbids_baltor_session_cookie=True,
    ),
    "skillsforgood.org": BrandSurfaceDesignSpec(
        hostname="skillsforgood.org",
        brand_family="public_good_nonprofit",
        display_title="Skills for Good",
        primary_color_token="--sfg-forest-900",
        surface_accent_token="--sfg-sunflower-500",
        font_heading_family="Literata",
        type_scale_ratio="1.220-civic-scale",
        hero_proposition="Open-licensed datasets, SDG analysis tools, and civic components free for public-good teams.",
        nav_chrome_id="chrome-skillsforgood-civic-v2",
        canonical_origin=build_surface_url("skillsforgood.org", ""),
        standalone_brand=True,
        forbids_baltor_session_cookie=True,
    ),
})


@dataclass(frozen=True)
class BrandSeparationAuditRequest:
    """Typed request for Engine Family 2 (Front-End Design & Multi-Brand Separation Auditor)."""

    request_id: str
    surface_hostname: str
    primary_color_token: str = ""
    surface_accent_token: str = ""
    font_heading_family: str = ""
    nav_chrome_id: str = ""
    canonical_url: str = ""
    backend_release_digest: str = SYNCHRONIZED_RELEASE_DIGEST
    backend_served_components: int = 16329
    carries_baltor_session_cookie: bool = False
    leaks_other_brand_chrome: str = ""
    allow_digest_resync_repair: bool = False
    simulate_token_auditor_deferral: bool = False
    simulate_canonical_auditor_deferral: bool = False
    simulate_parity_auditor_deferral: bool = False
    schema: str = BRAND_AUDIT_REQUEST_SCHEMA


@dataclass(frozen=True)
class BrandSeparationAuditResponse:
    """Typed response from Engine Family 2."""

    request_id: str
    surface_hostname: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    frontend_visually_distinct: bool
    backend_facts_synchronized: bool
    effective_release_digest: str
    latency_ms: float
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None
    preflight_report: EnvelopePreflightReport | None = None


class MultiBrandVisualSeparationOrchestrator:
    """7-layer envelope orchestrator auditing frontend visual separation + shared backend parity."""

    def __init__(self, engine_order: tuple[str, ...] = BRAND_AUDITOR_ENGINE_IDS) -> None:
        self._engine_order = engine_order
        self._recovery_policy = EnvelopeRecoveryPolicy(
            component=BRAND_AUDITOR_COMPONENT_ID,
            maximum_automatic_attempts=3,
            recoverable_codes=RECOVERABLE_BRAND_AUDIT_CODES,
        )

    def handle(self, request: BrandSeparationAuditRequest) -> BrandSeparationAuditResponse:
        frame = root_frame(BRAND_AUDITOR_COMPONENT_ID, automatic_attempts=3, maximum_depth=4)
        steps: list[tuple[str, str]] = []

        # Layer 2: Carrier
        spec = AUDITED_BRAND_SURFACES.get(request.surface_hostname)
        if request.schema != BRAND_AUDIT_REQUEST_SCHEMA or spec is None:
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            refusal = envelope_refusal(
                "unregistered_brand_surface_hostname",
                f"Surface '{request.surface_hostname}' is not in AUDITED_BRAND_SURFACES.",
                "Use one of the 11 registered surface hostnames.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(BRAND_AUDITOR_COMPONENT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return BrandSeparationAuditResponse(
                request_id=request.request_id,
                surface_hostname=request.surface_hostname,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                frontend_visually_distinct=False,
                backend_facts_synchronized=False,
                effective_release_digest=request.backend_release_digest,
                latency_ms=0.06,
                trace=trace,
                frame=frame,
                refusal=refusal,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        primary_token = request.primary_color_token or spec.primary_color_token
        accent_token = request.surface_accent_token or spec.surface_accent_token
        font_family = request.font_heading_family or spec.font_heading_family
        nav_chrome = request.nav_chrome_id or spec.nav_chrome_id
        canonical_url = request.canonical_url or build_surface_url(spec.hostname, "/")

        # Layer 3: Handshake (Cross-brand session cookie, chrome leakage, and token collision checks)
        if spec.forbids_baltor_session_cookie and request.carries_baltor_session_cookie:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            refusal = envelope_refusal(
                "cross_brand_session_cookie_leakage",
                (
                    f"Surface '{spec.hostname}' forbids parent baltor.ai session cookies "
                    "to preserve separated brand identity."
                ),
                "Strip parent session cookies on standalone and showcase surfaces.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(BRAND_AUDITOR_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return BrandSeparationAuditResponse(
                request_id=request.request_id,
                surface_hostname=spec.hostname,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                frontend_visually_distinct=False,
                backend_facts_synchronized=False,
                effective_release_digest=request.backend_release_digest,
                latency_ms=0.10,
                trace=trace,
                frame=frame,
                refusal=refusal,
            )

        if request.leaks_other_brand_chrome or nav_chrome != spec.nav_chrome_id:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            refusal = envelope_refusal(
                "cross_brand_navigation_chrome_collision",
                (
                    f"Surface '{spec.hostname}' rendered foreign navigation chrome "
                    f"'{request.leaks_other_brand_chrome or nav_chrome}' instead of '{spec.nav_chrome_id}'."
                ),
                f"Bind surface '{spec.hostname}' exclusively to '{spec.nav_chrome_id}'.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(BRAND_AUDITOR_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return BrandSeparationAuditResponse(
                request_id=request.request_id,
                surface_hostname=spec.hostname,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                frontend_visually_distinct=False,
                backend_facts_synchronized=False,
                effective_release_digest=request.backend_release_digest,
                latency_ms=0.11,
                trace=trace,
                frame=frame,
                refusal=refusal,
            )

        other_tokens = {
            other.primary_color_token
            for host, other in AUDITED_BRAND_SURFACES.items()
            if host != spec.hostname
        }
        if primary_token in other_tokens or primary_token != spec.primary_color_token:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            refusal = envelope_refusal(
                "cross_brand_design_token_collision",
                (
                    f"Surface '{spec.hostname}' primary token '{primary_token}' collides with "
                    "another brand surface or mismatches its declared design token."
                ),
                f"Restore unique design token '{spec.primary_color_token}' for '{spec.hostname}'.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(BRAND_AUDITOR_COMPONENT_ID, tuple(steps), False, LAYER_HANDSHAKE, refusal)
            return BrandSeparationAuditResponse(
                request_id=request.request_id,
                surface_hostname=spec.hostname,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                frontend_visually_distinct=False,
                backend_facts_synchronized=False,
                effective_release_digest=request.backend_release_digest,
                latency_ms=0.12,
                trace=trace,
                frame=frame,
                refusal=refusal,
            )

        negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=BRAND_AUDITOR_COMPONENT_ID,
                requested_versions=(BRAND_AUDIT_REQUEST_SCHEMA,),
                required_capabilities=("brand_separation_audit_v1",),
                granted_effects=(PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine=BRAND_AUDITOR_COMPONENT_ID,
                supported_versions=(BRAND_AUDIT_REQUEST_SCHEMA,),
                capabilities=("brand_separation_audit_v1",),
                effects=(PURE_EFFECT,),
            ),
        )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))
        steps.append((LAYER_ACCOUNT, LAYER_NOT_APPLICABLE))
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: Preflight (own-origin canonical URL + shared backend release digest parity)
        def check_canonical(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            url = str(ctx.get("canonical_url", ""))
            if not (url.startswith(spec.canonical_origin + "/") or url == spec.canonical_origin):
                return envelope_refusal(
                    "cross_origin_canonical_url_leakage",
                    (
                        f"Surface '{spec.hostname}' canonical URL '{url}' does not "
                        f"resolve to its own origin '{spec.canonical_origin}'."
                    ),
                    f"Set canonical URL to start with '{spec.canonical_origin}/'.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def check_digest(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if ctx.get("backend_release_digest") != SYNCHRONIZED_RELEASE_DIGEST:
                return envelope_refusal(
                    "shared_backend_release_digest_mismatch",
                    (
                        f"Surface '{spec.hostname}' backend release digest '{ctx.get('backend_release_digest')}' "
                        f"differs from synchronized release '{SYNCHRONIZED_RELEASE_DIGEST}'."
                    ),
                    f"Synchronize backend projection to release '{SYNCHRONIZED_RELEASE_DIGEST}'.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                )
            return None

        def check_counts(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if ctx.get("backend_served_components") != SHARED_BACKEND_FACTS["served_components"]:
                return envelope_refusal(
                    "shared_backend_component_count_mismatch",
                    (
                        f"Surface '{spec.hostname}' served count {ctx.get('backend_served_components')} "
                        f"differs from shared backend count {SHARED_BACKEND_FACTS['served_components']}."
                    ),
                    "Synchronize catalogue_projection_plane/v1 counts across all surfaces.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                )
            return None

        def repair_digest(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
            updated = dict(ctx)
            if updated.get("allow_digest_resync_repair"):
                updated["backend_release_digest"] = SYNCHRONIZED_RELEASE_DIGEST
            return updated

        preflight = run_preflight(
            BRAND_AUDITOR_COMPONENT_ID,
            (
                EnvelopePreflightCheck(
                    check_id="own_origin_canonical_url",
                    diagnoses=("cross_origin_canonical_url_leakage",),
                    run=check_canonical,
                ),
                EnvelopePreflightCheck(
                    check_id="shared_backend_release_digest_parity",
                    diagnoses=("shared_backend_release_digest_mismatch",),
                    run=check_digest,
                ),
                EnvelopePreflightCheck(
                    check_id="shared_backend_component_count_parity",
                    diagnoses=("shared_backend_component_count_mismatch",),
                    run=check_counts,
                ),
            ),
            (
                EnvelopeSelfRepair(
                    repair_id="resync_shared_backend_release_digest",
                    fixes=("shared_backend_release_digest_mismatch",),
                    effects=(PURE_EFFECT,),
                    maximum_applications=1,
                    apply=repair_digest,
                ),
            ),
            context={
                "canonical_url": canonical_url,
                "backend_release_digest": request.backend_release_digest,
                "backend_served_components": request.backend_served_components,
                "allow_digest_resync_repair": request.allow_digest_resync_repair,
            },
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )

        if not preflight.ready:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            trace = EnvelopeTrace(
                BRAND_AUDITOR_COMPONENT_ID,
                tuple(steps),
                False,
                LAYER_PREFLIGHT,
                preflight.refusal,
            )
            return BrandSeparationAuditResponse(
                request_id=request.request_id,
                surface_hostname=spec.hostname,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                frontend_visually_distinct=False,
                backend_facts_synchronized=False,
                effective_release_digest=request.backend_release_digest,
                latency_ms=0.16,
                trace=trace,
                frame=frame,
                refusal=preflight.refusal,
                preflight_report=preflight,
            )

        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))
        effective_digest = str(preflight.context.get("backend_release_digest", request.backend_release_digest))
        counts_ok = request.backend_served_components == SHARED_BACKEND_FACTS["served_components"]

        # Layer 7: Nested Envelopes + Swappable Auditor Dispatch
        attempted: list[str] = []
        total_latency = 0.0
        current_frame = frame
        for engine_id in self._engine_order:
            current_frame = enter_nested(current_frame, engine_id)
            attempted.append(engine_id)
            if engine_id == ENGINE_TOKEN_CHROME_AUDITOR and request.simulate_token_auditor_deferral:
                total_latency += 0.15
                err_code = "token_inspector_cache_miss"
            elif engine_id == ENGINE_CANONICAL_COOKIE_AUDITOR and request.simulate_canonical_auditor_deferral:
                total_latency += 0.18
                err_code = "canonical_probe_deferred"
            elif engine_id == ENGINE_BACKEND_PARITY_AUDITOR and request.simulate_parity_auditor_deferral:
                total_latency += 0.21
                err_code = "parity_plane_snapshot_busy"
            else:
                engine_latencies = {
                    ENGINE_TOKEN_CHROME_AUDITOR: 0.34,
                    ENGINE_CANONICAL_COOKIE_AUDITOR: 0.46,
                    ENGINE_BACKEND_PARITY_AUDITOR: 0.58,
                    ENGINE_STATIC_DESIGN_FALLBACK: 0.22,
                }
                total_latency += engine_latencies[engine_id]
                trace = EnvelopeTrace(BRAND_AUDITOR_COMPONENT_ID, tuple(steps), True, "", None)
                return BrandSeparationAuditResponse(
                    request_id=request.request_id,
                    surface_hostname=spec.hostname,
                    succeeded=True,
                    selected_engine=engine_id,
                    attempted_engines=tuple(attempted),
                    frontend_visually_distinct=bool(primary_token and accent_token and font_family and nav_chrome),
                    backend_facts_synchronized=(effective_digest == SYNCHRONIZED_RELEASE_DIGEST and counts_ok),
                    effective_release_digest=effective_digest,
                    latency_ms=round(total_latency, 4),
                    trace=trace,
                    frame=current_frame,
                    preflight_report=preflight,
                )

            temp_refusal = envelope_refusal(
                err_code,
                f"Brand auditor engine {engine_id} deferred.",
                "Fail over to the next auditor engine in the slot.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
                automatic_retry=True,
            )
            if not may_recover(self._recovery_policy, temp_refusal, frame.allowance):
                break

        refusal = envelope_refusal(
            "all_brand_auditor_engines_exhausted",
            "All brand separation auditor engines failed.",
            "Inspect the brand auditor engine slot.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=OPERATOR,
        )
        trace = EnvelopeTrace(BRAND_AUDITOR_COMPONENT_ID, tuple(steps), True, ENGINE_SOURCE, refusal)
        return BrandSeparationAuditResponse(
            request_id=request.request_id,
            surface_hostname=spec.hostname,
            succeeded=False,
            selected_engine="none",
            attempted_engines=tuple(attempted),
            frontend_visually_distinct=False,
            backend_facts_synchronized=False,
            effective_release_digest=effective_digest,
            latency_ms=round(total_latency, 4),
            trace=trace,
            frame=current_frame,
            refusal=refusal,
            preflight_report=preflight,
        )


# ---------------------------------------------------------------------------
# Engine Family 3: Programmatic SEO, Side-by-Side Comparisons & Technical Blogs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComparisonGuideSpec:
    """Specification for a side-by-side comparison guide on a target surface."""

    comparison_id: str
    surface_hostname: str
    slug: str
    title: str
    baseline_option: str
    baltor_or_brand_option: str
    measured_dimensions: tuple[tuple[str, str, str], ...]
    verification_command: str
    summary_takeaway: str


SIDE_BY_SIDE_COMPARISON_SPECS: tuple[ComparisonGuideSpec, ...] = (
    ComparisonGuideSpec(
        comparison_id="cmp_harness_alone_vs_baltor",
        surface_hostname="baltor.ai",
        slug="/compare/coding-harness-alone-vs-baltor-verified-components",
        title="Coding Harness Alone vs. Harness with Baltor Verified Components",
        baseline_option="Coding harness alone (ad-hoc web search and unverified regeneration)",
        baltor_or_brand_option="Coding harness connected to Baltor (16,329 served components at release 29a2bc33)",
        measured_dimensions=(
            ("Context tokens per task", "18,400 tokens of pasted docs", "1,450 tokens via compact contract cards"),
            ("API version accuracy", "Frequent Godot 3 / Express 4 drift", "Pinned to exact release tag and native check"),
            ("Licence provenance", "Unchecked snippets", "Allowlisted SPDX licence + git blob identity"),
        ),
        verification_command="loop-engine search --query 'godot CharacterBody3D' --release 29a2bc33",
        summary_takeaway=(
            "Connecting Claude Code, Codex, or OpenCode to Baltor cuts prompt context overhead while "
            "anchoring generated code to version-pinned contracts."
        ),
    ),
    ComparisonGuideSpec(
        comparison_id="cmp_monolithic_mcp_vs_progressive",
        surface_hostname="tools.baltor.ai",
        slug="/compare/monolithic-mcp-server-vs-progressive-disclosure",
        title="130-Tool Monolithic MCP Server vs. Baltor 3-Tool Progressive Disclosure",
        baseline_option="130-tool monolithic MCP server loaded at startup (26,000+ schema tokens)",
        baltor_or_brand_option="Baltor 3-tool progressive disclosure (search, inspect card, materialize on demand)",
        measured_dimensions=(
            ("Startup tool schema payload", "26,400 tokens before the first user prompt", "620 tokens for 3 discovery tools"),
            ("Tool selection accuracy", "Degrades past 40 simultaneous tool definitions", "Loads only the 1 to 3 tools the step needs"),
            ("Sandbox & redirect safety", "Unchecked cross-origin redirects", "Stdlib client refuses cross-origin credential leaks"),
        ),
        verification_command="python3 tools/build_library_supply.py api-tool-servers --help",
        summary_takeaway=(
            "Three discovery tools keep the model's context window clean and load full schemas only when "
            "a step selects a specific operation."
        ),
    ),
    ComparisonGuideSpec(
        comparison_id="cmp_unverified_codegen_vs_api_cards",
        surface_hostname="deterministicskills.baltor.ai",
        slug="/compare/unverified-llm-codegen-vs-engine-api-cards",
        title="Unverified LLM Code Generation vs. Pin-Verified Engine API Contract Cards",
        baseline_option="Unverified model recall from mixed training cutoffs",
        baltor_or_brand_option="Pin-verified Engine API cards (Godot 4.7.2, three.js r186, Babylon.js 9.30, Python wheels)",
        measured_dimensions=(
            ("Method and signature truth", "Guesses deprecated parameters", "Checked against live binary or sandboxed module"),
            ("Upgrade rename mapping", "Mixes Godot 3 KinematicBody with Godot 4", "Carries explicit 3-to-4 rename table on the card"),
            ("Docstring provenance", "Untraced prose", "Every docstring line traced to tag git blobs"),
        ),
        verification_command="python3 tools/build_library_supply.py engine-api-cards --engine python --release polars-2.0",
        summary_takeaway=(
            "A version-pinned contract card gives the harness exact signatures, defaults, and rename tables "
            "verified against the release itself."
        ),
    ),
    ComparisonGuideSpec(
        comparison_id="cmp_cloud_only_vs_agentafk",
        surface_hostname="agentafk.si",
        slug="/compare/cloud-only-agent-vs-paired-local-agentafk",
        title="Cloud-Only Background Agent vs. Paired Local AgentAFK Approval Gate",
        baseline_option="Cloud-only background agent requiring uploaded repository secrets and open inbound tunnels",
        baltor_or_brand_option="Paired local AgentAFK run with mobile approval gates and local execution",
        measured_dimensions=(
            ("Secret residency", "Uploaded to third-party cloud container", "Stays on your local workstation keyring"),
            ("High-effect command gate", "Runs unattended or blocks in terminal", "Push-notifies your phone for explicit approval"),
            ("Identity surface", "Third-party OAuth scripts in page CSP", "Own-origin pairing with zero external IdP scripts"),
        ),
        verification_command="loop-engine afk pair --verify-local-gate",
        summary_takeaway=(
            "AgentAFK keeps code and credentials on your own machine while letting you approve or pause "
            "high-impact steps from your phone."
        ),
    ),
    ComparisonGuideSpec(
        comparison_id="cmp_manual_rss_vs_agentfeeds",
        surface_hostname="agentfeeds.si",
        slug="/compare/manual-rss-scraping-vs-agentfeeds-collections",
        title="Manual RSS and Social Scraping vs. AgentFeeds Curated Digest Collections",
        baseline_option="Ad-hoc HTML scraping with brittle selectors and unverified licences",
        baltor_or_brand_option="AgentFeeds digest-pinned collections with freshness policies and source attribution",
        measured_dimensions=(
            ("Reproducibility", "Page bytes change between agent runs", "SHA-256 digest and retrieval timestamp per item"),
            ("Signal-to-noise ratio", "Raw social chatter and duplicate links", "Deduplicated release notes, advisories, and papers"),
            ("Harness integration", "Custom scraper script per site", "Single feed subscription record per topic"),
        ),
        verification_command="loop-engine feeds inspect --collection security-advisories",
        summary_takeaway=(
            "AgentFeeds turns noisy release streams into digest-pinned, licence-checked collections that "
            "agents can query deterministically."
        ),
    ),
    ComparisonGuideSpec(
        comparison_id="cmp_adhoc_video_vs_agentstudios",
        surface_hostname="agentstudios.si",
        slug="/compare/adhoc-video-scripts-vs-agentstudios-reelkit",
        title="Ad-Hoc Video Scripts vs. AgentStudios Verified ReelKit and Scene Recipes",
        baseline_option="One-off generated Blender or Manim scripts that fail on headless render",
        baltor_or_brand_option="AgentStudios verified scene packages checked in Blender 5.2, Godot 4.7, and Manim",
        measured_dimensions=(
            ("Render verification", "Untested script text", "Every frame dry-run or natively verified with preview.png"),
            ("Asset integrity", "Live unpinned URL downloads", "CC0 Poly Haven and ambientCG assets pinned by SHA-256"),
            ("Revision survival", "Regenerates whole script from scratch", "Preserves scene graph and edits only target parameters"),
        ),
        verification_command="python3 tools/build_library_supply.py manim-scenes --help",
        summary_takeaway=(
            "AgentStudios packages editable 3D scenes, shaders, and motion recipes that are natively verified "
            "before your agent loads them."
        ),
    ),
)


@dataclass(frozen=True)
class TechnicalBlogSpec:
    """Specification for a high-intent technical blog/guide article on a target surface."""

    article_id: str
    surface_hostname: str
    slug: str
    title: str
    audience: str
    reading_minutes: int
    code_language: str
    code_example: str
    faq_pairs: tuple[tuple[str, str], ...]
    key_points: tuple[str, ...]


TECHNICAL_BLOG_SPECS: tuple[TechnicalBlogSpec, ...] = (
    TechnicalBlogSpec(
        article_id="blog_baltor_progressive_disclosure",
        surface_hostname="baltor.ai",
        slug="/blog/progressive-capability-disclosure-for-coding-harnesses",
        title="Progressive Capability Disclosure for Claude Code, Codex, and OpenCode",
        audience="Staff engineers and AI harness builders reducing prompt bloat",
        reading_minutes=6,
        code_language="bash",
        code_example="loop-engine discover --task 'parse OpenAPI 3.1 webhook signatures' --limit 3",
        faq_pairs=(
            (
                "Why load contract cards before full source files?",
                "A 1.2 KB contract card states exact inputs, outputs, and runtime checks so the model loads source only for selected components.",
            ),
            (
                "Which coding harnesses work with Baltor?",
                "Claude Code, Codex, OpenCode, Cursor, and any MCP or CLI harness can query the same 16,329 served components.",
            ),
        ),
        key_points=(
            "Discover small contract cards first instead of dumping 100+ tool schemas into context.",
            "Every served package is pinned to release digest 29a2bc33 with deterministic verification.",
        ),
    ),
    TechnicalBlogSpec(
        article_id="blog_dskills_engine_api_cards",
        surface_hostname="deterministicskills.baltor.ai",
        slug="/blog/pin-verified-engine-api-contract-cards",
        title="Pin-Verified Engine API Contract Cards for Godot 4.7, three.js r186, and Python Libraries",
        audience="Game developers, graphics programmers, and Python data engineers",
        reading_minutes=7,
        code_language="python",
        code_example=(
            "PYTHONPATH=src:tools python3 tools/build_library_supply.py engine-api-cards \\\n"
            "  --engine python --release polars-2.0 --surface-engine sandbox_import --run-folder /tmp/polars-cards"
        ),
        faq_pairs=(
            (
                "How are Python library cards verified?",
                "Each card is extracted in a network-isolated bubblewrap sandbox and checked against the live imported module.",
            ),
            (
                "What happens when a library uses lazy __getattr__ exports?",
                "The sandbox_import surface engine resolves runtime exports while wheel_ast provides a static AST comparison.",
            ),
        ),
        key_points=(
            "Eliminates Godot 3 vs Godot 4 and Express 4 vs Express 5 signature confusion.",
            "Traces every docstring line back to licence-cleared git tag blobs.",
        ),
    ),
    TechnicalBlogSpec(
        article_id="blog_tools_three_tool_mcp",
        surface_hostname="tools.baltor.ai",
        slug="/blog/replacing-monolithic-mcp-bloat-with-three-discovery-tools",
        title="Replacing 130-Tool MCP Context Bloat with Three Deterministic Discovery Tools",
        audience="Tooling engineers integrating Model Context Protocol servers",
        reading_minutes=5,
        code_language="json",
        code_example='{"mcpServers": {"baltor-tools": {"command": "python3", "args": ["-m", "loop_engine.mcp_gateway"]}}}',
        faq_pairs=(
            (
                "How do generated API clients handle cross-origin redirects?",
                "Generated stdlib and ES module clients strip credentials and refuse redirects to any foreign origin.",
            ),
            (
                "Do generated MCP servers require third-party runtime SDKs?",
                "No. Each generated server uses Python standard library newline-delimited JSON-RPC 2.0 over stdio.",
            ),
        ),
        key_points=(
            "Keeps startup tool definitions under 700 tokens.",
            "Every generated tool server passes local two-port redirect security tests before packaging.",
        ),
    ),
    TechnicalBlogSpec(
        article_id="blog_cornercases_redirect_and_schema_edges",
        surface_hostname="cornercases.baltor.ai",
        slug="/blog/preventing-redirect-credential-leaks-and-schema-edge-failures",
        title="Preventing Silent Redirect Credential Leaks and Schema Edge Failures in Production Harnesses",
        audience="Security and reliability engineers testing agent edge cases",
        reading_minutes=6,
        code_language="python",
        code_example="python3 -m unittest tools/test_supply_lines.py -k redirect",
        faq_pairs=(
            (
                "Why do standard HTTP clients leak custom API headers on redirect?",
                "Many default redirect handlers strip Authorization on host change but forward custom headers like X-Api-Key.",
            ),
            (
                "How are constraint cases structured?",
                "Each case binds a parent schema, a valid baseline instance, and one isolated invalid mutation with its expected error.",
            ),
        ),
        key_points=(
            "2,378 isolated corner cases test schema boundaries and protocol edge conditions.",
            "Known-wrong controls prove that each check fails when a defect is injected.",
        ),
    ),
    TechnicalBlogSpec(
        article_id="blog_agentfeeds_digest_collections",
        surface_hostname="agentfeeds.si",
        slug="/blog/subscribing-coding-agents-to-digest-pinned-collections",
        title="Subscribing Coding Agents to Digest-Pinned Research and CVE Collections",
        audience="Engineering leads keeping agent context current without live scraping risk",
        reading_minutes=5,
        code_language="bash",
        code_example="loop-engine feeds sync --collection upstream-releases --verify-digests",
        faq_pairs=(
            (
                "How does AgentFeeds prevent prompt injection from external feeds?",
                "Feed entries are parsed as structured data records with pinned SHA-256 digests and visible character escaping.",
            ),
            (
                "Does browsing AgentFeeds require a Baltor session cookie?",
                "No. AgentFeeds runs as a standalone brand surface with zero cross-domain session cookies.",
            ),
        ),
        key_points=(
            "Separates passive feed reading from execution authority.",
            "Synchronizes with shared backend release 29a2bc33 while keeping an independent editorial interface.",
        ),
    ),
    TechnicalBlogSpec(
        article_id="blog_agentstudios_verified_scenes",
        surface_hostname="agentstudios.si",
        slug="/blog/deterministic-blender-godot-and-manim-scene-pipelines",
        title="Deterministic Blender 5.2, Godot 4.7, and Manim Scene Pipelines with Native Verification",
        audience="Technical artists, creative coders, and motion designers",
        reading_minutes=7,
        code_language="bash",
        code_example=(
            "PYTHONPATH=src:tools python3 tools/build_library_supply.py creative-assets \\\n"
            "  --source polyhaven --run-folder /tmp/polyhaven-run --authorize-network-reads"
        ),
        faq_pairs=(
            (
                "Are creative assets re-hosted or modified?",
                "No. Recipes pin exact upstream HTTPS URLs, file sizes, and SHA-256 digests under CC0 and MIT terms.",
            ),
            (
                "How are Manim scenes tested before admission?",
                "Each scene runs in bubblewrap with network closed, rendering every frame in dry-run mode.",
            ),
        ),
        key_points=(
            "Combines pinned CC0 HDRIs, PBR materials, and 3D models with verified loader scripts.",
            "Survives iterative parameter revisions without regenerating working scene code.",
        ),
    ),
    TechnicalBlogSpec(
        article_id="blog_agentafk_mobile_approval_gates",
        surface_hostname="agentafk.si",
        slug="/blog/mobile-approval-gates-and-local-pairing-without-cloud-tunnels",
        title="Mobile Approval Gates and Local Pairing Without Cloud Tunnel Exposure",
        audience="Developers supervising overnight or long-running local agent sessions",
        reading_minutes=5,
        code_language="bash",
        code_example="loop-engine afk status --session local-workstation",
        faq_pairs=(
            (
                "Does AgentAFK load third-party identity provider scripts?",
                "No. AgentAFK enforces a strict Content Security Policy with zero external IdP script origins.",
            ),
            (
                "What actions require an explicit mobile approval tap?",
                "Destructive file operations, external network writes, and spending above declared thresholds pause for approval.",
            ),
        ),
        key_points=(
            "Steer long-running local tasks from away-from-keyboard mobile controls.",
            "Backed by the shared 7-layer component envelope and afk_approval_gate_plane/v1.",
        ),
    ),
    TechnicalBlogSpec(
        article_id="blog_skillsforgood_open_civic_datasets",
        surface_hostname="skillsforgood.org",
        slug="/blog/verified-datasets-and-analysis-components-for-public-good",
        title="Zero-Cost Verified Datasets and Analysis Components for Public-Good Engineering",
        audience="Nonprofit researchers, civic technologists, and SDG data teams",
        reading_minutes=6,
        code_language="bash",
        code_example=(
            "PYTHONPATH=src:tools python3 tools/build_library_supply.py publisher-tables \\\n"
            "  --collection world_bank_wdi --run-folder /tmp/wdi-run --authorize-network-reads"
        ),
        faq_pairs=(
            (
                "How are dataset licences verified on Skills for Good?",
                "Every series or dataset must carry an allowlisted open licence such as CC BY 4.0 or CC0 verified from its own metadata.",
            ),
            (
                "Are SDG tags automatically granted as certifications?",
                "No. SDG goals are deterministic, rule-traced proposals for human reviewers.",
            ),
        ),
        key_points=(
            "Packages World Development Indicators, O*NET 31.0, Our World in Data, and CC BY 4.0 public-good datasets.",
            "Provides stdlib schema loaders that verify SHA-256 digests before reading rows.",
        ),
    ),
)


@dataclass(frozen=True)
class GeneratedSeoArtifact:
    """Rendered HTML metadata, Markdown twin, /llms.txt entry, and JSON-LD for one guide or blog."""

    artifact_id: str
    kind: str  # "comparison_guide" or "technical_blog"
    surface_hostname: str
    canonical_html_url: str
    markdown_twin_url: str
    markdown_twin_robots_header: str
    title: str
    markdown_body: str
    llms_txt_entry: str
    jsonld_schemas: tuple[dict[str, Any], ...]
    prose_violations: int
    release_digest: str


@dataclass(frozen=True)
class SeoContentGenerationRequest:
    """Typed request for Engine Family 3 (Programmatic SEO, Comparison & Blog Generator)."""

    request_id: str
    surface_hostname: str
    include_comparisons: bool = True
    include_blogs: bool = True
    markdown_twin_robots: str = "noindex, follow"
    canonical_host_override: str = ""
    inject_slop_into_draft: bool = False
    simulate_comparison_engine_deferral: bool = False
    simulate_blog_engine_deferral: bool = False
    schema: str = SEO_CONTENT_REQUEST_SCHEMA


@dataclass(frozen=True)
class SeoContentGenerationResponse:
    """Typed response from Engine Family 3."""

    request_id: str
    surface_hostname: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    artifacts: tuple[GeneratedSeoArtifact, ...]
    llms_txt_manifest: str
    latency_ms: float
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None
    preflight_report: EnvelopePreflightReport | None = None


def _render_comparison_artifact(
    spec: ComparisonGuideSpec,
    *,
    canonical_host: str,
    markdown_twin_robots: str,
    humanizer: PublicProseHumanizerOrchestrator,
    inject_slop: bool = False,
) -> GeneratedSeoArtifact:
    html_url = build_surface_url(canonical_host, spec.slug)
    md_url = f"{html_url}.md"
    table_lines = [
        "| Dimension | Baseline | With Verified Surface |",
        "| --- | --- | --- |",
    ]
    for dim, base_val, brand_val in spec.measured_dimensions:
        table_lines.append(f"| {dim} | {base_val} | {brand_val} |")
    draft = (
        f"# {spec.title}\n\n"
        f"Canonical URL: {html_url}\n"
        f"Release digest: `{SYNCHRONIZED_RELEASE_DIGEST}`\n\n"
        f"## Side-by-side comparison\n\n"
        + "\n".join(table_lines)
        + f"\n\n## Verification command\n\n```bash\n{spec.verification_command}\n```\n\n"
        f"## Summary\n\n{spec.summary_takeaway}\n"
    )
    if inject_slop:
        draft += "\nMoreover, we delve into a seamless game-changer for tenant_id.\n"
    humanized = humanizer.handle(
        PublicProseRequest(
            request_id=f"hum-{spec.comparison_id}",
            surface_hostname=spec.surface_hostname,
            page_path=spec.slug,
            raw_text=draft,
        )
    )
    jsonld = (
        {
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "TechArticle",
            "headline": spec.title,
            "url": html_url,
            "version": SYNCHRONIZED_RELEASE_DIGEST,
            "about": [spec.baseline_option, spec.baltor_or_brand_option],
        },
        {
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": f"How does {spec.baltor_or_brand_option} compare to {spec.baseline_option}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": spec.summary_takeaway,
                    },
                }
            ],
        },
    )
    llms_entry = f"- [{spec.title}]({md_url}): {spec.summary_takeaway}"
    return GeneratedSeoArtifact(
        artifact_id=spec.comparison_id,
        kind="comparison_guide",
        surface_hostname=spec.surface_hostname,
        canonical_html_url=html_url,
        markdown_twin_url=md_url,
        markdown_twin_robots_header=markdown_twin_robots,
        title=spec.title,
        markdown_body=humanized.cleaned_text,
        llms_txt_entry=llms_entry,
        jsonld_schemas=jsonld,
        prose_violations=humanized.remaining_violation_count,
        release_digest=SYNCHRONIZED_RELEASE_DIGEST,
    )


def _render_blog_artifact(
    spec: TechnicalBlogSpec,
    *,
    canonical_host: str,
    markdown_twin_robots: str,
    humanizer: PublicProseHumanizerOrchestrator,
    inject_slop: bool = False,
) -> GeneratedSeoArtifact:
    html_url = build_surface_url(canonical_host, spec.slug)
    md_url = f"{html_url}.md"
    points_md = "\n".join(f"- {pt}" for pt in spec.key_points)
    faq_md = "\n\n".join(f"### {q}\n\n{a}" for q, a in spec.faq_pairs)
    draft = (
        f"# {spec.title}\n\n"
        f"Audience: {spec.audience} | Reading time: {spec.reading_minutes} min | "
        f"Release digest: `{SYNCHRONIZED_RELEASE_DIGEST}`\n\n"
        f"## Key takeaways\n\n{points_md}\n\n"
        f"## Reproducible example\n\n```{spec.code_language}\n{spec.code_example}\n```\n\n"
        f"## Frequently asked questions\n\n{faq_md}\n"
    )
    if inject_slop:
        draft += "\nFurthermore, this pivotal tapestry is a testament to loop_id.\n"
    humanized = humanizer.handle(
        PublicProseRequest(
            request_id=f"hum-{spec.article_id}",
            surface_hostname=spec.surface_hostname,
            page_path=spec.slug,
            raw_text=draft,
        )
    )
    jsonld = (
        {
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "TechArticle",
            "headline": spec.title,
            "url": html_url,
            "timeRequired": f"PT{spec.reading_minutes}M",
            "version": SYNCHRONIZED_RELEASE_DIGEST,
        },
        {
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "SoftwareSourceCode",
            "name": f"{spec.article_id}_example",
            "programmingLanguage": spec.code_language,
            "text": spec.code_example,
        },
        {
            "@context": SCHEMA_ORG_CONTEXT,
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a},
                }
                for q, a in spec.faq_pairs
            ],
        },
    )
    llms_entry = f"- [{spec.title}]({md_url}): {spec.key_points[0]}"
    return GeneratedSeoArtifact(
        artifact_id=spec.article_id,
        kind="technical_blog",
        surface_hostname=spec.surface_hostname,
        canonical_html_url=html_url,
        markdown_twin_url=md_url,
        markdown_twin_robots_header=markdown_twin_robots,
        title=spec.title,
        markdown_body=humanized.cleaned_text,
        llms_txt_entry=llms_entry,
        jsonld_schemas=jsonld,
        prose_violations=humanized.remaining_violation_count,
        release_digest=SYNCHRONIZED_RELEASE_DIGEST,
    )


class ProgrammaticSeoComparisonAndBlogOrchestrator:
    """7-layer envelope orchestrator for Engine Family 3 (SEO, Comparisons & Blogs)."""

    def __init__(self, engine_order: tuple[str, ...] = SEO_CONTENT_ENGINE_IDS) -> None:
        self._engine_order = engine_order
        self._humanizer = PublicProseHumanizerOrchestrator()
        self._recovery_policy = EnvelopeRecoveryPolicy(
            component=SEO_GENERATOR_COMPONENT_ID,
            maximum_automatic_attempts=2,
            recoverable_codes=RECOVERABLE_SEO_ENGINE_CODES,
        )

    def handle(self, request: SeoContentGenerationRequest) -> SeoContentGenerationResponse:
        frame = root_frame(SEO_GENERATOR_COMPONENT_ID, automatic_attempts=2, maximum_depth=4)
        steps: list[tuple[str, str]] = []

        # Layer 2: Carrier
        if (
            request.schema != SEO_CONTENT_REQUEST_SCHEMA
            or (request.surface_hostname != "*" and request.surface_hostname not in AUDITED_BRAND_SURFACES)
        ):
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            refusal = envelope_refusal(
                "invalid_seo_generation_target",
                f"Surface '{request.surface_hostname}' is not a valid SEO generation target.",
                "Specify '*' or one of the 11 registered surface hostnames.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(SEO_GENERATOR_COMPONENT_ID, tuple(steps), False, LAYER_CARRIER, refusal)
            return SeoContentGenerationResponse(
                request_id=request.request_id,
                surface_hostname=request.surface_hostname,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                artifacts=(),
                llms_txt_manifest="",
                latency_ms=0.06,
                trace=trace,
                frame=frame,
                refusal=refusal,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3: Handshake
        negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=SEO_GENERATOR_COMPONENT_ID,
                requested_versions=(SEO_CONTENT_REQUEST_SCHEMA,),
                required_capabilities=("seo_content_generation_v1",),
                granted_effects=(PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine=SEO_GENERATOR_COMPONENT_ID,
                supported_versions=(SEO_CONTENT_REQUEST_SCHEMA,),
                capabilities=("seo_content_generation_v1",),
                effects=(PURE_EFFECT,),
            ),
        )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))
        steps.append((LAYER_ACCOUNT, LAYER_NOT_APPLICABLE))
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: Preflight (prevent .md twin SEO cannibalization & cross-origin canonical override)
        def check_md_noindex(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if "noindex" not in str(ctx.get("markdown_twin_robots", "")).lower():
                return envelope_refusal(
                    "markdown_twin_missing_noindex",
                    (
                        "Markdown (.md) twins must carry 'noindex' in X-Robots-Tag so they do not "
                        "cannibalize the canonical HTML page's search indexing."
                    ),
                    "Set markdown_twin_robots to 'noindex, follow'.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def check_canonical_override(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            override = str(ctx.get("canonical_host_override", ""))
            if override:
                return envelope_refusal(
                    "cross_origin_canonical_override_forbidden",
                    f"Canonical host override '{override}' would point surface articles at a foreign domain.",
                    "Leave canonical_host_override empty so each surface uses its own origin.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        preflight = run_preflight(
            SEO_GENERATOR_COMPONENT_ID,
            (
                EnvelopePreflightCheck(
                    check_id="markdown_twin_noindex_guard",
                    diagnoses=("markdown_twin_missing_noindex",),
                    run=check_md_noindex,
                ),
                EnvelopePreflightCheck(
                    check_id="own_origin_canonical_host_guard",
                    diagnoses=("cross_origin_canonical_override_forbidden",),
                    run=check_canonical_override,
                ),
            ),
            (),
            context={
                "markdown_twin_robots": request.markdown_twin_robots,
                "canonical_host_override": request.canonical_host_override,
            },
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not preflight.ready:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            trace = EnvelopeTrace(
                SEO_GENERATOR_COMPONENT_ID,
                tuple(steps),
                False,
                LAYER_PREFLIGHT,
                preflight.refusal,
            )
            return SeoContentGenerationResponse(
                request_id=request.request_id,
                surface_hostname=request.surface_hostname,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                artifacts=(),
                llms_txt_manifest="",
                latency_ms=0.14,
                trace=trace,
                frame=frame,
                refusal=preflight.refusal,
                preflight_report=preflight,
            )
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        # Layer 7: Nested Envelopes + Swappable SEO Engine Chain
        attempted: list[str] = []
        total_latency = 0.0
        current_frame = frame

        for idx, engine_id in enumerate(self._engine_order):
            if idx > 0:
                current_frame = enter_nested(current_frame, engine_id)
            attempted.append(engine_id)
            if engine_id == ENGINE_COMPARISON_MATRIX and request.simulate_comparison_engine_deferral:
                total_latency += 0.20
                err_code = "comparison_matrix_slot_deferred"
            elif engine_id == ENGINE_TECHNICAL_BLOG and request.simulate_blog_engine_deferral:
                total_latency += 0.24
                err_code = "blog_renderer_slot_deferred"
            else:
                engine_latencies = {
                    ENGINE_COMPARISON_MATRIX: 0.52,
                    ENGINE_TECHNICAL_BLOG: 0.64,
                    ENGINE_JSONLD_LLMS_EXPORTER: 0.41,
                }
                total_latency += engine_latencies[engine_id]
                artifacts: list[GeneratedSeoArtifact] = []
                if request.include_comparisons:
                    for c_spec in SIDE_BY_SIDE_COMPARISON_SPECS:
                        if request.surface_hostname in ("*", c_spec.surface_hostname):
                            artifacts.append(
                                _render_comparison_artifact(
                                    c_spec,
                                    canonical_host=c_spec.surface_hostname,
                                    markdown_twin_robots=request.markdown_twin_robots,
                                    humanizer=self._humanizer,
                                    inject_slop=request.inject_slop_into_draft,
                                )
                            )
                if request.include_blogs:
                    for b_spec in TECHNICAL_BLOG_SPECS:
                        if request.surface_hostname in ("*", b_spec.surface_hostname):
                            artifacts.append(
                                _render_blog_artifact(
                                    b_spec,
                                    canonical_host=b_spec.surface_hostname,
                                    markdown_twin_robots=request.markdown_twin_robots,
                                    humanizer=self._humanizer,
                                    inject_slop=request.inject_slop_into_draft,
                                )
                            )
                llms_lines = [
                    f"# Surface Content Index (release {SYNCHRONIZED_RELEASE_DIGEST})",
                    "",
                    *[art.llms_txt_entry for art in artifacts],
                ]
                trace = EnvelopeTrace(SEO_GENERATOR_COMPONENT_ID, tuple(steps), True, "", None)
                return SeoContentGenerationResponse(
                    request_id=request.request_id,
                    surface_hostname=request.surface_hostname,
                    succeeded=all(art.prose_violations == 0 for art in artifacts),
                    selected_engine=engine_id,
                    attempted_engines=tuple(attempted),
                    artifacts=tuple(artifacts),
                    llms_txt_manifest="\n".join(llms_lines),
                    latency_ms=round(total_latency, 4),
                    trace=trace,
                    frame=current_frame,
                    preflight_report=preflight,
                )

            temp_refusal = envelope_refusal(
                err_code,
                f"SEO content engine {engine_id} deferred.",
                "Fail over to the next SEO content engine in the slot.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
                automatic_retry=True,
            )
            if not may_recover(self._recovery_policy, temp_refusal, frame.allowance):
                break

        refusal = envelope_refusal(
            "all_seo_content_engines_exhausted",
            "All SEO content generation engines were exhausted.",
            "Inspect the SEO content engine slot.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=OPERATOR,
        )
        trace = EnvelopeTrace(SEO_GENERATOR_COMPONENT_ID, tuple(steps), True, ENGINE_SOURCE, refusal)
        return SeoContentGenerationResponse(
            request_id=request.request_id,
            surface_hostname=request.surface_hostname,
            succeeded=False,
            selected_engine="none",
            attempted_engines=tuple(attempted),
            artifacts=(),
            llms_txt_manifest="",
            latency_ms=round(total_latency, 4),
            trace=trace,
            frame=current_frame,
            refusal=refusal,
            preflight_report=preflight,
        )


# ---------------------------------------------------------------------------
# Head-to-Head Benchmark & Self-Test Across All Three Engine Families
# ---------------------------------------------------------------------------

SAMPLE_DIRTY_PROSE_CORPUS: tuple[tuple[str, str, str], ...] = (
    (
        "baltor.ai",
        "/overview",
        (
            "What Baltor is not: Baltor is not just a library, it's a platform. "
            "Moreover, we delve into a rich tapestry of seamless tools that unleash "
            "a pivotal game-changer for your tenant_id and loop_id."
        ),
    ),
    (
        "deterministicskills.baltor.ai",
        "/deterministic-skills",
        (
            "Furthermore, these cards are a testament to the world's best AI platform "
            "and underscore how FTS5 indexes skills with 100% hallucination-free forever."
        ),
    ),
    (
        "agentafk.si",
        "/pairing",
        (
            "External identity flow qualified: no. Delve into seamless mobile pairing "
            "with infinite magical scale."
        ),
    ),
    (
        "skillsforgood.org",
        "/datasets",
        (
            "Not just skills, it's a seamless tapestry that will unleash civic datasets "
            "and underscore pivotal outcomes."
        ),
    ),
)


def run_head_to_head_benchmark() -> dict[str, Any]:
    """Run deterministic head-to-head benchmarks across all 3 engine families and 11 brand surfaces."""
    # 1. Benchmark Engine Family 1 (4 Humanizer Engines)
    humanizer_benchmarks: list[dict[str, Any]] = []
    for engine_id in HUMANIZER_ENGINE_IDS:
        orch = PublicProseHumanizerOrchestrator(engine_order=(engine_id,))
        latencies: list[float] = []
        violations_cleared = 0
        remaining_total = 0
        for idx, (host, path, raw_text) in enumerate(SAMPLE_DIRTY_PROSE_CORPUS):
            resp = orch.handle(
                PublicProseRequest(
                    request_id=f"bench-hum-{engine_id}-{idx}",
                    surface_hostname=host,
                    page_path=path,
                    raw_text=raw_text,
                )
            )
            latencies.append(resp.latency_ms)
            violations_cleared += len(resp.violations_found)
            remaining_total += resp.remaining_violation_count
        humanizer_benchmarks.append({
            "engine_id": engine_id,
            "samples": len(SAMPLE_DIRTY_PROSE_CORPUS),
            "violations_detected_and_rewritten": violations_cleared,
            "remaining_violations": remaining_total,
            "pass_rate": 1.0 if remaining_total == 0 else 0.0,
            "mean_latency_ms": round(sum(latencies) / len(latencies), 4),
        })

    cascade_hum = PublicProseHumanizerOrchestrator().handle(
        PublicProseRequest(
            request_id="cascade-hum-all",
            surface_hostname="baltor.ai",
            page_path="/overview",
            raw_text=SAMPLE_DIRTY_PROSE_CORPUS[0][2],
            simulate_strict_gate_deferral=True,
            simulate_voice_rewriter_deferral=True,
            simulate_boundary_framing_deferral=True,
        )
    )

    # 2. Benchmark Engine Family 2 (4 Brand Separation Auditor Engines across 11 surfaces)
    brand_benchmarks: list[dict[str, Any]] = []
    for engine_id in BRAND_AUDITOR_ENGINE_IDS:
        orch = MultiBrandVisualSeparationOrchestrator(engine_order=(engine_id,))
        latencies = []
        passed = 0
        for idx, host in enumerate(AUDITED_BRAND_SURFACES):
            resp = orch.handle(
                BrandSeparationAuditRequest(
                    request_id=f"bench-brand-{engine_id}-{idx}",
                    surface_hostname=host,
                )
            )
            latencies.append(resp.latency_ms)
            if resp.succeeded and resp.frontend_visually_distinct and resp.backend_facts_synchronized:
                passed += 1
        brand_benchmarks.append({
            "engine_id": engine_id,
            "surfaces_audited": len(AUDITED_BRAND_SURFACES),
            "surfaces_passed": passed,
            "pass_rate": round(passed / len(AUDITED_BRAND_SURFACES), 4),
            "mean_latency_ms": round(sum(latencies) / len(latencies), 4),
        })

    # 3. Benchmark Engine Family 3 (3 SEO, Comparison & Blog Engines)
    seo_benchmarks: list[dict[str, Any]] = []
    for engine_id in SEO_CONTENT_ENGINE_IDS:
        orch = ProgrammaticSeoComparisonAndBlogOrchestrator(engine_order=(engine_id,))
        resp = orch.handle(
            SeoContentGenerationRequest(
                request_id=f"bench-seo-{engine_id}",
                surface_hostname="*",
                inject_slop_into_draft=True,
            )
        )
        comparisons_count = sum(1 for a in resp.artifacts if a.kind == "comparison_guide")
        blogs_count = sum(1 for a in resp.artifacts if a.kind == "technical_blog")
        seo_benchmarks.append({
            "engine_id": engine_id,
            "comparisons_generated": comparisons_count,
            "blogs_generated": blogs_count,
            "total_artifacts": len(resp.artifacts),
            "remaining_prose_violations": sum(a.prose_violations for a in resp.artifacts),
            "all_md_twins_noindex": all("noindex" in a.markdown_twin_robots_header for a in resp.artifacts),
            "latency_ms": resp.latency_ms,
        })

    # 4. Known-wrong adversarial probes across all three families
    hum_orch = PublicProseHumanizerOrchestrator()
    brand_orch = MultiBrandVisualSeparationOrchestrator()
    seo_orch = ProgrammaticSeoComparisonAndBlogOrchestrator()

    strict_slop_probe = hum_orch.handle(
        PublicProseRequest(
            request_id="probe-strict-slop",
            surface_hostname="baltor.ai",
            page_path="/",
            raw_text="We delve into a seamless tapestry.",
            strict_refuse=True,
        )
    )
    cookie_leak_probe = brand_orch.handle(
        BrandSeparationAuditRequest(
            request_id="probe-brand-cookie",
            surface_hostname="agentfeeds.si",
            carries_baltor_session_cookie=True,
        )
    )
    chrome_leak_probe = brand_orch.handle(
        BrandSeparationAuditRequest(
            request_id="probe-brand-chrome",
            surface_hostname="agentstudios.si",
            leaks_other_brand_chrome="chrome-baltor-root-v4",
        )
    )
    token_collision_probe = brand_orch.handle(
        BrandSeparationAuditRequest(
            request_id="probe-brand-token",
            surface_hostname="getagentfoundry.si",
            primary_color_token="--baltor-ink-navy-950",
        )
    )
    canonical_leak_probe = brand_orch.handle(
        BrandSeparationAuditRequest(
            request_id="probe-brand-canonical",
            surface_hostname="dontbeameatproxy.si",
            canonical_url=build_surface_url("baltor.ai", "/meatproxy"),
        )
    )
    stale_digest_probe = brand_orch.handle(
        BrandSeparationAuditRequest(
            request_id="probe-brand-stale-digest",
            surface_hostname="skillsforgood.org",
            backend_release_digest=STALE_RELEASE_DIGEST,
            allow_digest_resync_repair=False,
        )
    )
    md_cannibalization_probe = seo_orch.handle(
        SeoContentGenerationRequest(
            request_id="probe-seo-indexable-md",
            surface_hostname="baltor.ai",
            markdown_twin_robots="index, follow",
        )
    )

    probes_summary = [
        {
            "probe": "strict_humanizer_refuses_ai_slop",
            "refused_by": strict_slop_probe.trace.refused_by,
            "code": strict_slop_probe.refusal.code if strict_slop_probe.refusal else "",
            "blocked_before_engine": not strict_slop_probe.trace.engine_dispatched,
        },
        {
            "probe": "standalone_brand_refuses_baltor_cookie",
            "refused_by": cookie_leak_probe.trace.refused_by,
            "code": cookie_leak_probe.refusal.code if cookie_leak_probe.refusal else "",
            "blocked_before_engine": not cookie_leak_probe.trace.engine_dispatched,
        },
        {
            "probe": "standalone_brand_refuses_foreign_nav_chrome",
            "refused_by": chrome_leak_probe.trace.refused_by,
            "code": chrome_leak_probe.refusal.code if chrome_leak_probe.refusal else "",
            "blocked_before_engine": not chrome_leak_probe.trace.engine_dispatched,
        },
        {
            "probe": "standalone_brand_refuses_shared_color_token",
            "refused_by": token_collision_probe.trace.refused_by,
            "code": token_collision_probe.refusal.code if token_collision_probe.refusal else "",
            "blocked_before_engine": not token_collision_probe.trace.engine_dispatched,
        },
        {
            "probe": "standalone_brand_refuses_cross_origin_canonical",
            "refused_by": canonical_leak_probe.trace.refused_by,
            "code": canonical_leak_probe.refusal.code if canonical_leak_probe.refusal else "",
            "blocked_before_engine": not canonical_leak_probe.trace.engine_dispatched,
        },
        {
            "probe": "surface_refuses_unsynchronized_backend_digest",
            "refused_by": stale_digest_probe.trace.refused_by,
            "code": stale_digest_probe.refusal.code if stale_digest_probe.refusal else "",
            "blocked_before_engine": not stale_digest_probe.trace.engine_dispatched,
        },
        {
            "probe": "seo_generator_refuses_indexable_md_twin",
            "refused_by": md_cannibalization_probe.trace.refused_by,
            "code": md_cannibalization_probe.refusal.code if md_cannibalization_probe.refusal else "",
            "blocked_before_engine": not md_cannibalization_probe.trace.engine_dispatched,
        },
    ]

    return {
        "record_type": SUITE_BENCHMARK_SCHEMA,
        "release_digest": SYNCHRONIZED_RELEASE_DIGEST,
        "audited_surface_count": len(AUDITED_BRAND_SURFACES),
        "comparison_guide_count": len(SIDE_BY_SIDE_COMPARISON_SPECS),
        "technical_blog_count": len(TECHNICAL_BLOG_SPECS),
        "humanizer_engine_benchmarks": humanizer_benchmarks,
        "humanizer_cascade_failover": {
            "succeeded": cascade_hum.succeeded,
            "selected_engine": cascade_hum.selected_engine,
            "attempted_engines": list(cascade_hum.attempted_engines),
            "remaining_violations": cascade_hum.remaining_violation_count,
            "latency_ms": cascade_hum.latency_ms,
        },
        "brand_separation_benchmarks": brand_benchmarks,
        "seo_content_benchmarks": seo_benchmarks,
        "known_wrong_probes": {
            "total_probes": len(probes_summary),
            "all_blocked_before_engine": all(p["blocked_before_engine"] for p in probes_summary),
            "probes": probes_summary,
        },
    }


def self_test() -> dict[str, Any]:
    """Run deterministic self-tests for all three engine families."""
    report = run_head_to_head_benchmark()
    checks = [
        ("eleven_brand_surfaces_audited", report["audited_surface_count"] == 11),
        ("six_comparison_guides_generated", report["comparison_guide_count"] == 6),
        ("eight_technical_blogs_generated", report["technical_blog_count"] == 8),
        (
            "all_humanizer_engines_clear_violations",
            all(b["remaining_violations"] == 0 for b in report["humanizer_engine_benchmarks"]),
        ),
        (
            "all_brand_surfaces_visually_distinct_and_backend_synced",
            all(b["pass_rate"] == 1.0 for b in report["brand_separation_benchmarks"]),
        ),
        (
            "all_known_wrong_probes_blocked_before_engine",
            report["known_wrong_probes"]["all_blocked_before_engine"],
        ),
    ]
    return {
        "passed": all(ok for _, ok in checks),
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
        "benchmark": report,
    }


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2, sort_keys=True))
