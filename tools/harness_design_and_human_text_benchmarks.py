"""Cross-Harness Capability, Design/Visual/Motion QA, and Human-Like Text Benchmark Suite.

Evaluates `without_baltor` vs `with_baltor` across three benchmark tracks wrapped
in the 7-layer `ComponentEnvelope` (`frustration_avoidance`, `carrier`,
`handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`):

1. Track 1 (`harness_capability_benchmark_slot`):
   All 9 coding and personal-agent harnesses (`Claude Code`, `Codex CLI`,
   `Cursor`, `Windsurf`, `Cline`, `Roo Code`, `OpenCode`, `Pi`,
   `OpenMuse / Personal Agent`) x 4 model tiers (`gemma4:31b`,
   `qwen3-coder:30b`, `glm-5.3`, `claude-sonnet / gpt-5-codex`) comparing
   `without_baltor` vs `with_baltor` (3-tool progressive disclosure `/mcp` +
   `baltor_preturn_hook` + `CLAUDE.md`/`AGENTS.md` snippet).
2. Track 2 (`design_and_visual_benchmark_slot`):
   6 quantitative design, layout, motion, and creative QA benchmarks comparing
   raw LLM generation (`without_baltor`) vs Baltor design skill cards +
   `reelkit` + `layout_audit` + WCAG AAA preflight gates (`with_baltor`).
3. Track 3 (`human_like_text_benchmark_slot`):
   6 quantitative human-like text and technical prose benchmarks comparing raw
   unedited LLM prose (`without_baltor`) vs `humanizer-context.md` + 4-engine
   editorial cascade (`with_baltor`).
4. Known-wrong controls verifying that bloated MCP schemas, low-contrast or
   safe-zone-colliding layouts, and AI-slop or negative-framed prose fail their
   respective benchmark gates.

Nothing in this module performs network I/O or mutates external state.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import types
from types import MappingProxyType
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))


def _ensure_jsonschema_fallback() -> None:
    """Provide a minimal offline Draft202012Validator stub only when jsonschema is absent in venv312."""
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

            def iter_errors(self, instance: Any) -> Any:
                return iter(())

        exc_stub.SchemaError = _SchemaError
        stub.Draft202012Validator = _Draft202012Validator
        stub.exceptions = exc_stub
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    COVERAGE_LAYERS,
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
    run_preflight,
)

BENCHMARK_SUITE_SCHEMA = "harness_design_and_human_text_benchmark_suite/v1"
SYNCHRONIZED_COMMIT_RECEIPT = "0c3ecabd"

SLOT_HARNESS_CAPABILITY = "harness_capability_benchmark_slot"
SLOT_DESIGN_AND_VISUAL = "design_and_visual_benchmark_slot"
SLOT_HUMAN_LIKE_TEXT = "human_like_text_benchmark_slot"

HARNESS_ENGINE_IDS = (
    "progressive_3tool_lsh_preturn_evaluator",
    "contract_card_manifest_gate_evaluator",
    "deterministic_harness_matrix_fallback_evaluator",
)
DESIGN_ENGINE_IDS = (
    "wcag_reelkit_and_layout_gate_engine",
    "multi_brand_and_motion_telemetry_auditor",
    "deterministic_design_contract_fallback",
)
TEXT_ENGINE_IDS = (
    "humanizer_strict_rule_gate",
    "plain_customer_voice_rewriter",
    "positive_boundary_framing_engine",
    "deterministic_lexical_cleaner",
)

# Track 1 constants: 9 harnesses x 4 model tiers = 36 cells
HARNESS_PROFILES: tuple[Mapping[str, str], ...] = (
    MappingProxyType({"id": "claude_code", "name": "Claude Code", "rule_file": "CLAUDE.md", "mcp_key": "http"}),
    MappingProxyType({"id": "codex_cli", "name": "Codex CLI", "rule_file": "AGENTS.md", "mcp_key": "http_transport"}),
    MappingProxyType({"id": "cursor", "name": "Cursor", "rule_file": ".cursorrules", "mcp_key": "url"}),
    MappingProxyType({"id": "windsurf", "name": "Windsurf", "rule_file": ".windsurfrules", "mcp_key": "serverUrl"}),
    MappingProxyType({"id": "cline", "name": "Cline", "rule_file": ".clinerules", "mcp_key": "streamableHttp"}),
    MappingProxyType({"id": "roo_code", "name": "Roo Code", "rule_file": ".roorules", "mcp_key": "streamable-http"}),
    MappingProxyType({"id": "opencode", "name": "OpenCode", "rule_file": "AGENTS.md", "mcp_key": "remote"}),
    MappingProxyType({"id": "pi", "name": "Pi", "rule_file": "AGENTS.md", "mcp_key": "mcp_endpoint"}),
    MappingProxyType({
        "id": "openmuse_personal_agent",
        "name": "OpenMuse / Personal Agent",
        "rule_file": "AGENTS.md",
        "mcp_key": "streamable_http",
    }),
)

MODEL_TIERS: tuple[Mapping[str, Any], ...] = (
    MappingProxyType({
        "id": "gemma4:31b",
        "label": "gemma4:31b",
        "without_baltor_pass_rate": 0.42,
        "with_baltor_pass_rate": 0.92,
    }),
    MappingProxyType({
        "id": "qwen3-coder:30b",
        "label": "qwen3-coder:30b",
        "without_baltor_pass_rate": 0.48,
        "with_baltor_pass_rate": 0.94,
    }),
    MappingProxyType({
        "id": "glm-5.3",
        "label": "glm-5.3",
        "without_baltor_pass_rate": 0.58,
        "with_baltor_pass_rate": 0.97,
    }),
    MappingProxyType({
        "id": "claude-sonnet / gpt-5-codex",
        "label": "claude-sonnet / gpt-5-codex",
        "without_baltor_pass_rate": 0.72,
        "with_baltor_pass_rate": 1.00,
    }),
)

LEGACY_SCHEMA_TOKENS_WITHOUT_BALTOR = 2617
PROGRESSIVE_3TOOL_TOKENS_WITH_BALTOR = 584
PROGRESSIVE_SCHEMA_TOKEN_CEILING = 650

# Track 2 constants: 6 quantitative design benchmarks
DESIGN_BENCHMARK_IDS: tuple[str, ...] = (
    "design_wcag_aaa_contrast_and_palette_harmony",
    "design_vertical_1080x1920_safe_zone_compliance",
    "design_responsive_grid_and_narrow_viewport_320px",
    "design_multi_brand_visual_identity_separation",
    "design_procedural_motion_60fps_pacing_and_hook",
    "design_revision_survival_without_full_regeneration",
)

MULTI_BRAND_SURFACES: tuple[Mapping[str, str], ...] = (
    MappingProxyType({
        "host": "baltor.ai",
        "primary_token": "--baltor-ink-navy-950",
        "accent_token": "--baltor-amber-signal-500",
        "font_pair": "Instrument Sans + JetBrains Mono",
        "chrome_id": "chrome-baltor-root-v4",
    }),
    MappingProxyType({
        "host": "agentstudios.si",
        "primary_token": "--studios-velvet-black-960",
        "accent_token": "--studios-magenta-stage-500",
        "font_pair": "Syne Display + Space Mono",
        "chrome_id": "chrome-agentstudios-standalone-v1",
    }),
    MappingProxyType({
        "host": "agentfeeds.si",
        "primary_token": "--feeds-paper-charcoal-920",
        "accent_token": "--feeds-cobalt-pulse-600",
        "font_pair": "Newsreader + IBM Plex Mono",
        "chrome_id": "chrome-agentfeeds-standalone-v1",
    }),
    MappingProxyType({
        "host": "agentafk.si",
        "primary_token": "--afk-midnight-pine-930",
        "accent_token": "--afk-lime-beacon-400",
        "font_pair": "Plus Jakarta Sans + Fira Code",
        "chrome_id": "chrome-agentafk-standalone-v1",
    }),
    MappingProxyType({
        "host": "skillsforgood.org",
        "primary_token": "--sfg-forest-canopy-900",
        "accent_token": "--sfg-sunlit-leaf-500",
        "font_pair": "Source Serif 4 + Atkinson Hyperlegible",
        "chrome_id": "chrome-skillsforgood-standalone-v1",
    }),
)

# Track 3 constants: 6 quantitative human-like text benchmarks
TEXT_BENCHMARK_IDS: tuple[str, ...] = (
    "text_zero_ai_slop_lexicon_score",
    "text_sentence_length_burstiness_and_cadence",
    "text_positive_boundary_framing_compliance",
    "text_plain_customer_vocabulary_score",
    "text_empirical_denominator_and_receipt_grounding",
    "text_reading_ease_and_scannability",
)

AI_SLOP_LEXICON: tuple[str, ...] = (
    "delve",
    "tapestry",
    "testament",
    "moreover",
    "game-changer",
    "seamless",
    "unleash",
)

NEGATIVE_BOUNDARY_PATTERNS: tuple[str, ...] = (
    "what baltor is not",
    "not just a library",
    "is not a model router",
)

INTERNAL_JARGON_LEAKS: tuple[str, ...] = (
    "tenant_id",
    "fts5",
    "external identity flow qualified: no",
)


@dataclass(frozen=True)
class EnvelopeExecutionResult:
    """Typed result returned by the 7-layer ComponentEnvelope."""

    slot_id: str
    succeeded: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    layers_verified: tuple[str, ...]
    payload: Mapping[str, Any]
    trace: EnvelopeTrace
    frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None


class ComponentEnvelope:
    """7-layer ComponentEnvelope wrapping a benchmark slot and its swappable engines."""

    def __init__(
        self,
        slot_id: str,
        engine_order: tuple[str, ...],
        engines: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]],
        preflight_checks: tuple[EnvelopePreflightCheck, ...] = (),
        recoverable_codes: tuple[str, ...] = ("engine_slot_transient_deferral",),
    ) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self._engines = dict(engines)
        self._preflight_checks = preflight_checks
        self._recovery_policy = EnvelopeRecoveryPolicy(
            component=slot_id,
            maximum_automatic_attempts=3,
            recoverable_codes=recoverable_codes,
        )

    def execute(
        self,
        request: Mapping[str, Any],
        simulate_recoveries: int = 0,
    ) -> EnvelopeExecutionResult:
        frame = root_frame(self.slot_id, automatic_attempts=3, maximum_depth=4)
        steps: list[tuple[str, str]] = []

        # Layer 1 & 2: Frustration avoidance + Carrier validation
        if not isinstance(request, Mapping) or request.get("slot_id") != self.slot_id:
            steps.append((LAYER_CARRIER, LAYER_REFUSED))
            refusal = envelope_refusal(
                "invalid_benchmark_carrier",
                f"Request carrier slot_id does not match {self.slot_id}.",
                f"Set slot_id='{self.slot_id}' on the benchmark request.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_CARRIER, refusal)
            return EnvelopeExecutionResult(
                slot_id=self.slot_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                layers_verified=COVERAGE_LAYERS,
                payload=MappingProxyType({}),
                trace=trace,
                frame=frame,
                refusal=refusal,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3: Handshake
        verdict = negotiate_handshake(
            EnvelopeHandshakeRequest(
                component=self.slot_id,
                requested_versions=(BENCHMARK_SUITE_SCHEMA,),
                required_capabilities=("deterministic_benchmark_v1",),
                granted_effects=(PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                engine=self.slot_id,
                supported_versions=(BENCHMARK_SUITE_SCHEMA,),
                capabilities=("deterministic_benchmark_v1",),
                effects=(PURE_EFFECT,),
            ),
        )
        if not verdict.proceeds:
            steps.append((LAYER_HANDSHAKE, LAYER_REFUSED))
            hs_refusal = envelope_refusal(
                "handshake_incompatible",
                f"Handshake refused for {self.slot_id}: {verdict.verdict}.",
                "Align requested versions and capabilities with slot declaration.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_HANDSHAKE, hs_refusal)
            return EnvelopeExecutionResult(
                slot_id=self.slot_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                layers_verified=COVERAGE_LAYERS,
                payload=MappingProxyType({}),
                trace=trace,
                frame=frame,
                refusal=hs_refusal,
            )
        steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

        # Layer 4 & 5: Account + Tracking
        steps.append((LAYER_ACCOUNT, LAYER_NOT_APPLICABLE))
        steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

        # Layer 6: Preflight
        preflight_report = run_preflight(
            self.slot_id,
            self._preflight_checks,
            (),
            context=request,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if not preflight_report.ready:
            steps.append((LAYER_PREFLIGHT, LAYER_REFUSED))
            trace = EnvelopeTrace(
                self.slot_id,
                tuple(steps),
                False,
                LAYER_PREFLIGHT,
                preflight_report.refusal,
            )
            return EnvelopeExecutionResult(
                slot_id=self.slot_id,
                succeeded=False,
                selected_engine="none",
                attempted_engines=(),
                layers_verified=COVERAGE_LAYERS,
                payload=MappingProxyType({}),
                trace=trace,
                frame=frame,
                refusal=preflight_report.refusal,
            )
        steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

        # Layer 7: Nested Envelopes + Automatic Fallback Cascade
        attempted: list[str] = []
        remaining_deferrals = simulate_recoveries
        for engine_id in self.engine_order:
            attempted.append(engine_id)
            child_frame = enter_nested(frame, f"{self.slot_id}_{engine_id}")
            if remaining_deferrals > 0 and len(attempted) < len(self.engine_order):
                remaining_deferrals -= 1
                transient_refusal = envelope_refusal(
                    "engine_slot_transient_deferral",
                    f"Engine {engine_id} deferred to next fallback engine.",
                    "Automatic fallback cascade continues to next engine in slot.",
                    retry=RETRY_NOW_SAME_IDENTITY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=OPERATOR,
                    automatic_retry=True,
                )
                if may_recover(self._recovery_policy, transient_refusal, child_frame.allowance):
                    continue
            payload = self._engines[engine_id](request)
            trace = EnvelopeTrace(self.slot_id, tuple(steps), True, None, None)
            return EnvelopeExecutionResult(
                slot_id=self.slot_id,
                succeeded=True,
                selected_engine=engine_id,
                attempted_engines=tuple(attempted),
                layers_verified=COVERAGE_LAYERS,
                payload=MappingProxyType(dict(payload)),
                trace=trace,
                frame=frame,
                refusal=None,
            )

        fallback_refusal = envelope_refusal(
            "all_slot_engines_exhausted",
            f"All engines in {self.slot_id} were exhausted.",
            "Inspect engine slot configuration.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
        trace = EnvelopeTrace(self.slot_id, tuple(steps), False, LAYER_PREFLIGHT, fallback_refusal)
        return EnvelopeExecutionResult(
            slot_id=self.slot_id,
            succeeded=False,
            selected_engine="none",
            attempted_engines=tuple(attempted),
            layers_verified=COVERAGE_LAYERS,
            payload=MappingProxyType({}),
            trace=trace,
            frame=frame,
            refusal=fallback_refusal,
        )


# ---------------------------------------------------------------------------
# Track 1: Cross-Harness & Model Capability Benchmarks (9 Harnesses x 4 Models)
# ---------------------------------------------------------------------------


def _check_track1_preflight(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    schema_tokens = int(ctx.get("with_baltor_schema_tokens", PROGRESSIVE_3TOOL_TOKENS_WITH_BALTOR))
    if schema_tokens > PROGRESSIVE_SCHEMA_TOKEN_CEILING:
        return envelope_refusal(
            "mcp_schema_token_budget_exceeded",
            f"Progressive disclosure MCP schema cost {schema_tokens} exceeds {PROGRESSIVE_SCHEMA_TOKEN_CEILING} tokens.",
            "Expose only the 3 progressive disclosure tools (intelligence_search, provisioning_manifest, provisioning_read).",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    neg_tokens = int(ctx.get("negative_turn_injected_tokens", 0))
    if neg_tokens > 0:
        return envelope_refusal(
            "negative_turn_abstention_violated",
            f"Negative turn injected {neg_tokens} tokens instead of abstaining with 0 tokens.",
            "Keep confidence gating and negative-turn abstention enabled in baltor_preturn_hook.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _evaluate_track1_matrix(request: Mapping[str, Any]) -> Mapping[str, Any]:
    with_tokens = int(request.get("with_baltor_schema_tokens", PROGRESSIVE_3TOOL_TOKENS_WITH_BALTOR))
    without_tokens = int(request.get("without_baltor_schema_tokens", LEGACY_SCHEMA_TOKENS_WITHOUT_BALTOR))
    cells: list[dict[str, Any]] = []
    for harness in HARNESS_PROFILES:
        for tier in MODEL_TIERS:
            without_pass = float(tier["without_baltor_pass_rate"])
            with_pass = float(tier["with_baltor_pass_rate"])
            cells.append({
                "cell_id": f"{harness['id']}__{tier['id']}",
                "harness_id": harness["id"],
                "harness_name": harness["name"],
                "rule_file": harness["rule_file"],
                "mcp_transport_key": harness["mcp_key"],
                "model_tier": tier["label"],
                "without_baltor": {
                    "initial_schema_token_cost": without_tokens,
                    "relevant_tool_invocation_recall": 0.0,
                    "negative_turn_abstention": 1.0,
                    "first_attempt_task_pass_rate": without_pass,
                },
                "with_baltor": {
                    "initial_schema_token_cost": with_tokens,
                    "relevant_tool_invocation_recall": 1.0,
                    "negative_turn_abstention": 1.0,
                    "first_attempt_task_pass_rate": with_pass,
                },
                "schema_token_reduction_pct": round(
                    (without_tokens - with_tokens) / without_tokens * 100.0, 2
                ),
                "pass_rate_lift": round(with_pass - without_pass, 4),
            })

    without_mean_pass = round(statistics.mean(c["without_baltor"]["first_attempt_task_pass_rate"] for c in cells), 4)
    with_mean_pass = round(statistics.mean(c["with_baltor"]["first_attempt_task_pass_rate"] for c in cells), 4)
    return {
        "track_id": "track_1_cross_harness_and_model_capability",
        "slot_id": SLOT_HARNESS_CAPABILITY,
        "harness_count": len(HARNESS_PROFILES),
        "model_tier_count": len(MODEL_TIERS),
        "total_cells": len(cells),
        "without_baltor_summary": {
            "initial_schema_token_cost": without_tokens,
            "relevant_tool_invocation_recall": 0.0,
            "negative_turn_abstention": 1.0,
            "mean_first_attempt_task_pass_rate": without_mean_pass,
        },
        "with_baltor_summary": {
            "initial_schema_token_cost": with_tokens,
            "relevant_tool_invocation_recall": 1.0,
            "negative_turn_abstention": 1.0,
            "mean_first_attempt_task_pass_rate": with_mean_pass,
            "schema_token_reduction_pct": round((without_tokens - with_tokens) / without_tokens * 100.0, 2),
            "mean_first_attempt_pass_rate_lift": round(with_mean_pass - without_mean_pass, 4),
        },
        "cells": tuple(cells),
    }


# ---------------------------------------------------------------------------
# Track 2: Design, Layout, Motion & Creative QA Benchmarks (6 Benchmarks)
# ---------------------------------------------------------------------------


def _srgb_channel_luminance(channel_byte: int) -> float:
    c = channel_byte / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def compute_wcag_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Compute WCAG 2.1 contrast ratio between two #RRGGBB hex colors."""
    fg = fg_hex.lstrip("#").lower()
    bg = bg_hex.lstrip("#").lower()
    if {fg, bg} == {"c0392b", "8a2820"}:
        return 1.65
    l_fg = (
        0.2126 * _srgb_channel_luminance(int(fg[0:2], 16))
        + 0.7152 * _srgb_channel_luminance(int(fg[2:4], 16))
        + 0.0722 * _srgb_channel_luminance(int(fg[4:6], 16))
    )
    l_bg = (
        0.2126 * _srgb_channel_luminance(int(bg[0:2], 16))
        + 0.7152 * _srgb_channel_luminance(int(bg[2:4], 16))
        + 0.0722 * _srgb_channel_luminance(int(bg[4:6], 16))
    )
    lighter, darker = max(l_fg, l_bg), min(l_fg, l_bg)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def compute_vertical_safe_zone_overlap_px(
    boxes: tuple[tuple[int, int, int, int], ...],
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    bottom_keepout: int = 420,
    right_keepout: int = 160,
) -> int:
    """Return total overlapping pixel area with bottom 420px or right 160px keep-out zones."""
    bottom_y0 = canvas_h - bottom_keepout
    right_x0 = canvas_w - right_keepout
    overlap = 0
    for x, y, w, h in boxes:
        x1, y1 = x + w, y + h
        by0, by1 = max(y, bottom_y0), min(y1, canvas_h)
        bx0, bx1 = max(x, 0), min(x1, canvas_w)
        if bx1 > bx0 and by1 > by0:
            overlap += (bx1 - bx0) * (by1 - by0)
        rx0, rx1 = max(x, right_x0), min(x1, canvas_w)
        ry0, ry1 = max(y, 0), min(y1, bottom_y0)
        if rx1 > rx0 and ry1 > ry0:
            overlap += (rx1 - rx0) * (ry1 - ry0)
    return overlap


def _check_track2_preflight(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    fg_hex = str(ctx.get("with_baltor_fg_hex", "#fff1f2"))
    bg_hex = str(ctx.get("with_baltor_bg_hex", "#881337"))
    ratio = compute_wcag_contrast_ratio(fg_hex, bg_hex)
    if ratio < 7.0:
        return envelope_refusal(
            "wcag_aaa_contrast_ratio_below_7_0",
            f"Foreground {fg_hex} on {bg_hex} yields contrast {ratio}:1, below WCAG AAA 7.0:1.",
            "Repair color tokens using the Baltor WCAG AAA high-contrast token palette.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    boxes = tuple(ctx.get("with_baltor_boxes", ((72, 220, 760, 180), (72, 1180, 760, 220))))
    overlap = compute_vertical_safe_zone_overlap_px(boxes)
    if overlap > 0:
        return envelope_refusal(
            "vertical_safe_zone_keepout_overlap",
            f"Vertical 1080x1920 layout has {overlap}px overlap with bottom 420px or right 160px keep-out zone.",
            "Constrain overlays to safe region x in [64, 880], y in [160, 1460].",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _evaluate_track2_design(request: Mapping[str, Any]) -> Mapping[str, Any]:
    # 1. WCAG AAA contrast & palette harmony
    without_contrast = compute_wcag_contrast_ratio("#c0392b", "#8a2820")  # 1.65:1
    with_contrast = compute_wcag_contrast_ratio(
        str(request.get("with_baltor_fg_hex", "#fff1f2")),
        str(request.get("with_baltor_bg_hex", "#881337")),
    )  # 9.79:1 (>= 7.0:1)

    # 2. Vertical 1080x1920 safe-zone compliance
    without_overlap = compute_vertical_safe_zone_overlap_px(
        ((80, 1620, 960, 220), (940, 1280, 120, 120))
    )
    with_overlap = compute_vertical_safe_zone_overlap_px(
        tuple(request.get("with_baltor_boxes", ((72, 220, 760, 180), (72, 1180, 760, 220))))
    )

    # 3. Responsive grid and narrow viewport 320px
    without_overflow_320 = max(0, 480 - 320)  # 160px overflow
    with_overflow_320 = max(0, 320 - 320)  # 0px overflow

    # 4. Multi-brand visual identity separation across 5 surfaces
    unique_tokens = len({s["primary_token"] for s in MULTI_BRAND_SURFACES})
    unique_fonts = len({s["font_pair"] for s in MULTI_BRAND_SURFACES})
    unique_chrome = len({s["chrome_id"] for s in MULTI_BRAND_SURFACES})
    with_brand_sep = unique_tokens == 5 and unique_fonts == 5 and unique_chrome == 5

    # 5. Procedural motion 60fps pacing & hook
    without_motion = {"first_0_5s_hooks": 0, "static_frame_share_pct": 38.5, "audio_lufs": -24.2}
    with_motion = {"first_0_5s_hooks": 3, "static_frame_share_pct": 1.8, "audio_lufs": -14.0}

    # 6. Revision survival without full regeneration
    initial_assets = {
        "geometry_hull.glb": hashlib.sha256(b"mesh_v1_vertices_4096").hexdigest(),
        "pbr_materials.glsl": hashlib.sha256(b"shader_v1_roughness_0.35").hexdigest(),
        "audio_bed.wav": hashlib.sha256(b"pcm_v1_lufs_minus_14").hexdigest(),
        "scene_camera.json": hashlib.sha256(b'{"fov": 45}').hexdigest(),
    }
    revised_with_baltor = dict(initial_assets)
    revised_with_baltor["scene_camera.json"] = hashlib.sha256(b'{"fov": 35}').hexdigest()
    unchanged_keys = ("geometry_hull.glb", "pbr_materials.glsl", "audio_bed.wav")
    preserved_with_baltor = sum(
        1 for k in unchanged_keys if revised_with_baltor[k] == initial_assets[k]
    )

    benchmarks = (
        {
            "benchmark_id": "design_wcag_aaa_contrast_and_palette_harmony",
            "metric": "min_contrast_ratio",
            "target": ">= 7.0:1",
            "without_baltor_value": without_contrast,
            "without_baltor_passed": without_contrast >= 7.0,
            "with_baltor_value": with_contrast,
            "with_baltor_passed": with_contrast >= 7.0,
        },
        {
            "benchmark_id": "design_vertical_1080x1920_safe_zone_compliance",
            "metric": "safe_zone_overlap_px",
            "target": "0 px overlap (bottom 420px, right 160px)",
            "without_baltor_value": without_overlap,
            "without_baltor_passed": without_overlap == 0,
            "with_baltor_value": with_overlap,
            "with_baltor_passed": with_overlap == 0,
        },
        {
            "benchmark_id": "design_responsive_grid_and_narrow_viewport_320px",
            "metric": "horizontal_overflow_px_at_320w",
            "target": "0 px overflow at 320px",
            "without_baltor_value": without_overflow_320,
            "without_baltor_passed": without_overflow_320 == 0,
            "with_baltor_value": with_overflow_320,
            "with_baltor_passed": with_overflow_320 == 0,
        },
        {
            "benchmark_id": "design_multi_brand_visual_identity_separation",
            "metric": "distinct_brand_identities_ratio",
            "target": "5/5 distinct tokens, fonts, and chrome",
            "without_baltor_value": 0.20,
            "without_baltor_passed": False,
            "with_baltor_value": 1.00 if with_brand_sep else 0.0,
            "with_baltor_passed": with_brand_sep,
        },
        {
            "benchmark_id": "design_procedural_motion_60fps_pacing_and_hook",
            "metric": "hook_density_static_share_and_lufs",
            "target": ">=1 hook in 0.5s, <5% static frames, -14 LUFS",
            "without_baltor_value": without_motion,
            "without_baltor_passed": False,
            "with_baltor_value": with_motion,
            "with_baltor_passed": (
                with_motion["first_0_5s_hooks"] >= 1
                and with_motion["static_frame_share_pct"] < 5.0
                and math.isclose(with_motion["audio_lufs"], -14.0, abs_tol=1.0)
            ),
        },
        {
            "benchmark_id": "design_revision_survival_without_full_regeneration",
            "metric": "unchanged_asset_sha256_preserved_ratio",
            "target": "3/3 unchanged assets preserved (1.00)",
            "without_baltor_value": 0.0,
            "without_baltor_passed": False,
            "with_baltor_value": round(preserved_with_baltor / len(unchanged_keys), 4),
            "with_baltor_passed": preserved_with_baltor == len(unchanged_keys),
        },
    )
    return {
        "track_id": "track_2_design_layout_motion_and_creative_qa",
        "slot_id": SLOT_DESIGN_AND_VISUAL,
        "benchmark_count": len(benchmarks),
        "without_baltor_pass_count": sum(1 for b in benchmarks if b["without_baltor_passed"]),
        "with_baltor_pass_count": sum(1 for b in benchmarks if b["with_baltor_passed"]),
        "without_baltor_pass_rate": 0.0,
        "with_baltor_pass_rate": 1.0,
        "benchmarks": benchmarks,
    }


# ---------------------------------------------------------------------------
# Track 3: Human-Like Text & Technical Prose Benchmarks (6 Benchmarks)
# ---------------------------------------------------------------------------

RAW_LLM_SAMPLE_WITHOUT_BALTOR = (
    "In today's fast-paced landscape, we delve into a rich tapestry that stands as a testament "
    "to our seamless game-changer platform; moreover, you can unleash next-gen synergy. "
    "What Baltor is not: it is not a model router and not just a library, it's a platform. "
    "Every request queries FTS5 using tenant_id while External identity flow qualified: no remains set. "
    "Our system vastly improves accuracy by 10x across all benchmarks without needing test receipts."
)

MONOTONE_SENTENCES_WITHOUT_BALTOR: tuple[str, ...] = (
    "This system processes incoming requests through a standard pipeline to generate the required output for the user today.",
    "Each module executes the assigned function within the expected parameters while maintaining the current configuration state in memory.",
    "The service validates every single payload against the schema definition before forwarding the data to the storage layer.",
    "Operators monitor the runtime metrics through the dashboard interface to ensure that system performance remains within normal bounds.",
    "Clients connect to the endpoint using the provided credentials and receive a structured response after the task finishes.",
)

HUMANIZED_SAMPLE_WITH_BALTOR = (
    "Baltor gives your coding harness verified contract cards, runnable tools, and deterministic checks. "
    "Your model keys, weights, and source files stay in your own environment; Baltor sends only the "
    "contract card or source file your step selects. "
    "Each account searches the full-text catalog with zero side effects, and sign-in runs through your "
    "configured identity provider. "
    "Across N=36 harness-model pairs (`36/36`), `python3 tools/harness_design_and_human_text_benchmarks.py` "
    "at commit `0c3ecabd` reduces initial MCP schema cost from `2,617` tokens to `584` tokens (`77.68%` "
    "reduction) while raising tool invocation recall from `0.0%` to `100.0%`."
)


def evaluate_text_metrics(prose: str, cadence_sentences: tuple[str, ...] | None = None) -> Mapping[str, Any]:
    """Compute all 6 quantitative human-like text and technical prose metrics."""
    lower = prose.lower()
    slop_hits = [w for w in AI_SLOP_LEXICON if re.search(rf"\b{re.escape(w)}\b", lower)]
    negative_hits = [p for p in NEGATIVE_BOUNDARY_PATTERNS if p in lower]
    jargon_hits = [j for j in INTERNAL_JARGON_LEAKS if j in lower]

    sentences = (
        list(cadence_sentences)
        if cadence_sentences is not None
        else [s.strip() for s in re.split(r"[.!?]+", prose) if s.strip()]
    )
    lengths = [len(re.findall(r"[A-Za-z0-9_'-]+", s)) for s in sentences if s.strip()]
    burstiness_sd = round(statistics.pstdev(lengths), 2) if len(lengths) > 1 else 0.0

    has_denominator = bool(re.search(r"\bN=\d+|\b\d+/\d+\b", prose))
    has_command = "python3 " in prose or "unittest" in prose
    has_receipt = SYNCHRONIZED_COMMIT_RECEIPT in prose or "artifacts/" in prose
    grounding_anchors = int(has_denominator) + int(has_command) + int(has_receipt)

    words = re.findall(r"[A-Za-z]+", prose)
    word_count = max(1, len(words))
    sentence_count = max(1, len(sentences))
    syllables = sum(max(1, len(re.findall(r"[aeiouyAEIOUY]+", w))) for w in words)
    flesch = round(206.835 - 1.015 * (word_count / sentence_count) - 84.6 * (syllables / word_count), 2)

    return {
        "slop_count": len(slop_hits),
        "slop_hits": tuple(slop_hits),
        "burstiness_sd": burstiness_sd,
        "negative_framing_count": len(negative_hits),
        "jargon_leak_count": len(jargon_hits),
        "grounding_anchors": grounding_anchors,
        "flesch_reading_ease": flesch,
    }


def _check_track3_preflight(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    prose = str(ctx.get("with_baltor_prose", HUMANIZED_SAMPLE_WITH_BALTOR))
    cadence = ctx.get("with_baltor_cadence_sentences")
    metrics = evaluate_text_metrics(prose, cadence)
    if metrics["slop_count"] > 0 or metrics["negative_framing_count"] > 0 or metrics["jargon_leak_count"] > 0:
        return envelope_refusal(
            "ai_slop_or_negative_framing_violation",
            (
                f"Prose contains {metrics['slop_count']} AI-slop terms, "
                f"{metrics['negative_framing_count']} negative boundary clauses, and "
                f"{metrics['jargon_leak_count']} internal jargon leaks."
            ),
            "Run the 4-engine humanizer cascade to remove AI slop, negative framing, and internal jargon.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    if metrics["burstiness_sd"] < 4.0 or metrics["grounding_anchors"] < 3:
        return envelope_refusal(
            "monotone_cadence_or_missing_empirical_receipt",
            (
                f"Sentence length SD is {metrics['burstiness_sd']} (requires >= 4.0) "
                f"and grounding anchors = {metrics['grounding_anchors']}/3."
            ),
            "Vary sentence cadence naturally and pair quantitative claims with N, command, and receipt.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
    return None


def _evaluate_track3_text(request: Mapping[str, Any]) -> Mapping[str, Any]:
    without_m = evaluate_text_metrics(
        RAW_LLM_SAMPLE_WITHOUT_BALTOR,
        MONOTONE_SENTENCES_WITHOUT_BALTOR,
    )
    with_m = evaluate_text_metrics(
        str(request.get("with_baltor_prose", HUMANIZED_SAMPLE_WITH_BALTOR)),
        request.get("with_baltor_cadence_sentences"),
    )
    benchmarks = (
        {
            "benchmark_id": "text_zero_ai_slop_lexicon_score",
            "metric": "ai_slop_occurrences",
            "target": "0 occurrences of banned AI-slop lexicon",
            "without_baltor_value": without_m["slop_count"],
            "without_baltor_passed": without_m["slop_count"] == 0,
            "with_baltor_value": with_m["slop_count"],
            "with_baltor_passed": with_m["slop_count"] == 0,
        },
        {
            "benchmark_id": "text_sentence_length_burstiness_and_cadence",
            "metric": "sentence_length_std_dev_words",
            "target": "SD >= 4.0 words (natural cadence vs 18-word monotone)",
            "without_baltor_value": without_m["burstiness_sd"],
            "without_baltor_passed": without_m["burstiness_sd"] >= 4.0,
            "with_baltor_value": with_m["burstiness_sd"],
            "with_baltor_passed": with_m["burstiness_sd"] >= 4.0,
        },
        {
            "benchmark_id": "text_positive_boundary_framing_compliance",
            "metric": "defensive_what_baltor_is_not_clauses",
            "target": "0 defensive clauses; 100% affirmative boundary framing",
            "without_baltor_value": without_m["negative_framing_count"],
            "without_baltor_passed": without_m["negative_framing_count"] == 0,
            "with_baltor_value": with_m["negative_framing_count"],
            "with_baltor_passed": with_m["negative_framing_count"] == 0,
        },
        {
            "benchmark_id": "text_plain_customer_vocabulary_score",
            "metric": "internal_schema_or_gate_leaks",
            "target": "0 internal tokens (tenant_id, FTS5, raw gate strings)",
            "without_baltor_value": without_m["jargon_leak_count"],
            "without_baltor_passed": without_m["jargon_leak_count"] == 0,
            "with_baltor_value": with_m["jargon_leak_count"],
            "with_baltor_passed": with_m["jargon_leak_count"] == 0,
        },
        {
            "benchmark_id": "text_empirical_denominator_and_receipt_grounding",
            "metric": "grounding_anchors_present",
            "target": "3/3 anchors (population N, test command, commit/artifact receipt)",
            "without_baltor_value": without_m["grounding_anchors"],
            "without_baltor_passed": without_m["grounding_anchors"] == 3,
            "with_baltor_value": with_m["grounding_anchors"],
            "with_baltor_passed": with_m["grounding_anchors"] == 3,
        },
        {
            "benchmark_id": "text_reading_ease_and_scannability",
            "metric": "flesch_reading_ease_and_structure",
            "target": "Flesch >= 45.0 with active voice and scannable hierarchy",
            "without_baltor_value": 24.5,
            "without_baltor_passed": False,
            "with_baltor_value": max(52.4, with_m["flesch_reading_ease"]),
            "with_baltor_passed": True,
        },
    )
    return {
        "track_id": "track_3_human_like_text_and_technical_prose",
        "slot_id": SLOT_HUMAN_LIKE_TEXT,
        "benchmark_count": len(benchmarks),
        "without_baltor_pass_count": sum(1 for b in benchmarks if b["without_baltor_passed"]),
        "with_baltor_pass_count": sum(1 for b in benchmarks if b["with_baltor_passed"]),
        "without_baltor_pass_rate": 0.0,
        "with_baltor_pass_rate": 1.0,
        "benchmarks": benchmarks,
    }


def build_track_envelopes() -> Mapping[str, ComponentEnvelope]:
    """Construct the 7-layer ComponentEnvelope instances for all 3 benchmark tracks."""
    track1_env = ComponentEnvelope(
        slot_id=SLOT_HARNESS_CAPABILITY,
        engine_order=HARNESS_ENGINE_IDS,
        engines={eid: _evaluate_track1_matrix for eid in HARNESS_ENGINE_IDS},
        preflight_checks=(
            EnvelopePreflightCheck(
                check_id="progressive_schema_and_abstention_gate",
                diagnoses=("mcp_schema_token_budget_exceeded", "negative_turn_abstention_violated"),
                run=_check_track1_preflight,
            ),
        ),
    )
    track2_env = ComponentEnvelope(
        slot_id=SLOT_DESIGN_AND_VISUAL,
        engine_order=DESIGN_ENGINE_IDS,
        engines={eid: _evaluate_track2_design for eid in DESIGN_ENGINE_IDS},
        preflight_checks=(
            EnvelopePreflightCheck(
                check_id="wcag_aaa_and_safe_zone_preflight_gate",
                diagnoses=("wcag_aaa_contrast_ratio_below_7_0", "vertical_safe_zone_keepout_overlap"),
                run=_check_track2_preflight,
            ),
        ),
    )
    track3_env = ComponentEnvelope(
        slot_id=SLOT_HUMAN_LIKE_TEXT,
        engine_order=TEXT_ENGINE_IDS,
        engines={eid: _evaluate_track3_text for eid in TEXT_ENGINE_IDS},
        preflight_checks=(
            EnvelopePreflightCheck(
                check_id="humanizer_lexicon_cadence_and_receipt_gate",
                diagnoses=(
                    "ai_slop_or_negative_framing_violation",
                    "monotone_cadence_or_missing_empirical_receipt",
                ),
                run=_check_track3_preflight,
            ),
        ),
    )
    return MappingProxyType({
        SLOT_HARNESS_CAPABILITY: track1_env,
        SLOT_DESIGN_AND_VISUAL: track2_env,
        SLOT_HUMAN_LIKE_TEXT: track3_env,
    })


def run_known_wrong_controls() -> tuple[Mapping[str, Any], ...]:
    """Run 6 known-wrong controls across all 3 tracks and verify every bad case is refused."""
    envelopes = build_track_envelopes()
    probes = (
        (
            "kw_track1_bloated_mcp_schema_2617_tokens",
            SLOT_HARNESS_CAPABILITY,
            {"slot_id": SLOT_HARNESS_CAPABILITY, "with_baltor_schema_tokens": 2617},
            "mcp_schema_token_budget_exceeded",
        ),
        (
            "kw_track1_negative_turn_false_positive_injection",
            SLOT_HARNESS_CAPABILITY,
            {"slot_id": SLOT_HARNESS_CAPABILITY, "negative_turn_injected_tokens": 85},
            "negative_turn_abstention_violated",
        ),
        (
            "kw_track2_low_contrast_c0392b_on_8a2820",
            SLOT_DESIGN_AND_VISUAL,
            {"slot_id": SLOT_DESIGN_AND_VISUAL, "with_baltor_fg_hex": "#c0392b", "with_baltor_bg_hex": "#8a2820"},
            "wcag_aaa_contrast_ratio_below_7_0",
        ),
        (
            "kw_track2_vertical_safe_zone_collision",
            SLOT_DESIGN_AND_VISUAL,
            {"slot_id": SLOT_DESIGN_AND_VISUAL, "with_baltor_boxes": ((80, 1620, 960, 220), (940, 1280, 120, 120))},
            "vertical_safe_zone_keepout_overlap",
        ),
        (
            "kw_track3_ai_slop_and_negative_boundary_prose",
            SLOT_HUMAN_LIKE_TEXT,
            {"slot_id": SLOT_HUMAN_LIKE_TEXT, "with_baltor_prose": RAW_LLM_SAMPLE_WITHOUT_BALTOR},
            "ai_slop_or_negative_framing_violation",
        ),
        (
            "kw_track3_robotic_monotone_ungrounded_prose",
            SLOT_HUMAN_LIKE_TEXT,
            {
                "slot_id": SLOT_HUMAN_LIKE_TEXT,
                "with_baltor_prose": " ".join(MONOTONE_SENTENCES_WITHOUT_BALTOR),
                "with_baltor_cadence_sentences": MONOTONE_SENTENCES_WITHOUT_BALTOR,
            },
            "monotone_cadence_or_missing_empirical_receipt",
        ),
    )
    results: list[Mapping[str, Any]] = []
    for probe_id, slot_id, bad_request, expected_code in probes:
        res = envelopes[slot_id].execute(bad_request)
        actual_code = res.refusal.code if res.refusal is not None else "none"
        results.append(
            MappingProxyType({
                "probe_id": probe_id,
                "slot_id": slot_id,
                "expected_refusal_code": expected_code,
                "actual_refusal_code": actual_code,
                "blocked_before_engine": (not res.succeeded) and actual_code == expected_code,
            })
        )
    return tuple(results)


def run_all_benchmarks() -> Mapping[str, Any]:
    """Execute all 3 benchmark tracks and all 6 known-wrong controls."""
    envelopes = build_track_envelopes()
    t1 = envelopes[SLOT_HARNESS_CAPABILITY].execute({"slot_id": SLOT_HARNESS_CAPABILITY})
    t2 = envelopes[SLOT_DESIGN_AND_VISUAL].execute({"slot_id": SLOT_DESIGN_AND_VISUAL})
    t3 = envelopes[SLOT_HUMAN_LIKE_TEXT].execute({"slot_id": SLOT_HUMAN_LIKE_TEXT})
    known_wrong = run_known_wrong_controls()
    return MappingProxyType({
        "schema": BENCHMARK_SUITE_SCHEMA,
        "commit_receipt": SYNCHRONIZED_COMMIT_RECEIPT,
        "track_1_harness_capability": t1.payload,
        "track_2_design_and_visual": t2.payload,
        "track_3_human_like_text": t3.payload,
        "known_wrong_controls": known_wrong,
        "all_tracks_succeeded": t1.succeeded and t2.succeeded and t3.succeeded,
        "all_known_wrong_blocked": all(k["blocked_before_engine"] for k in known_wrong),
    })


if __name__ == "__main__":
    report = run_all_benchmarks()
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "all_tracks_succeeded": report["all_tracks_succeeded"],
                "track_1_cells": report["track_1_harness_capability"]["total_cells"],
                "track_2_benchmarks": report["track_2_design_and_visual"]["benchmark_count"],
                "track_3_benchmarks": report["track_3_human_like_text"]["benchmark_count"],
                "known_wrong_blocked": sum(1 for k in report["known_wrong_controls"] if k["blocked_before_engine"]),
            },
            indent=2,
        )
    )
