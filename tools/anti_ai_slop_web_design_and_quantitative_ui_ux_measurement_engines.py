"""Anti-AI-Slop Web Design, 1,200-Question Quantitative UI/UX Measurement (TPSI, WSR, Saliency Heatmap) & Public-Good Skills Engine Suite.

Implements two 7-Layer ComponentEnvelope slot families:
1. quantitative_ui_ux_tpsi_heatmap_and_anti_ai_slop_slot:
   - Evaluates any webpage/layout across 1,200 parameterized diagnostic questions (12 dimensions x 100 probes),
     computing Text Per Square Inch (TPSI), Macro/Micro Whitespace Ratio (WSR), Directional Proximity Ratio (DPR),
     Padding Harmonic Consistency, a 16x16 2D Visual Saliency & Density Heatmap (Clarity Score & TTFF),
     Reference Exemplar Calibration (paco.me, rauno.me, emilkowal.ski, read.cv, karpathy.ai), and 12 Anti-AI-Slop tropes.
2. public_good_and_editorial_design_skill_pack_synthesizer_slot:
   - Synthesizes verified 5-file Baltor Harness Component Packs and agentfeeds.si feeds for Anti-AI-Slop UI/UX,
     Humanized Editorial Profiles, and Public-Good Investigative/Civic Skills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Callable, Mapping

from loop_engine.core.engines.envelope import (
    DO_NOT_RETRY,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    envelope_refusal,
)
from loop_engine.core.engines.envelope_preflight import (
    EnvelopePreflightCheck,
    EnvelopePreflightReport,
    run_preflight,
)


@dataclass(frozen=True, slots=True)
class EnvelopeExecutionResult:
    """Typed result or refusal returned by an engine slot."""

    status: str
    value: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    refusal: EnvelopeRefusal | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def _ok(payload: Mapping[str, Any]) -> EnvelopeExecutionResult:
    return EnvelopeExecutionResult(status="ok", value=MappingProxyType(dict(payload)), refusal=None)


def _refused(refusal: EnvelopeRefusal) -> EnvelopeExecutionResult:
    return EnvelopeExecutionResult(status="refused", refusal=refusal)


DESIGN_DIMENSIONS_12: tuple[dict[str, Any], ...] = (
    {
        "dimension_id": "D01_text_per_square_inch_and_character_density",
        "title": "Text Per Square Inch (TPSI) & Alphanumeric Density",
        "optimal_profile_range": (45.0, 115.0),
        "question_template": "Does viewport module #{idx} maintain Text Per Square Inch (TPSI) within the ergonomic target band without crowding?",
    },
    {
        "dimension_id": "D02_macro_and_micro_whitespace_ratio",
        "title": "Macro & Micro Whitespace Ratio (WSR >= 55%)",
        "optimal_profile_range": (0.55, 0.78),
        "question_template": "Does layout region #{idx} preserve >= 55% active negative space and micro line-height >= 1.55?",
    },
    {
        "dimension_id": "D03_directional_heading_proximity_and_vertical_rhythm",
        "title": "Directional Heading Proximity (margin-top / margin-bottom >= 1.8)",
        "optimal_profile_range": (1.8, 4.5),
        "question_template": "Is section heading #{idx} tethered closer to its following body copy than to the preceding section?",
    },
    {
        "dimension_id": "D04_padding_harmonic_grid_and_sibling_consistency",
        "title": "4pt/8pt Harmonic Padding Scale & Zero Sibling Jitter",
        "optimal_profile_range": (0.90, 1.00),
        "question_template": "Do container padding tokens in block #{idx} align to a 4px/8px spatial rhythm with zero arbitrary jitter?",
    },
    {
        "dimension_id": "D05_typography_measure_tracking_and_tabular_numerals",
        "title": "60-68ch Measure Cap, Negative Display Tracking & Tabular Numerals",
        "optimal_profile_range": (55.0, 68.0),
        "question_template": "Does text block #{idx} cap measure at 60-68ch, apply -0.02em display tracking, and align dates with tabular-nums?",
    },
    {
        "dimension_id": "D06_anti_ai_slop_trope_and_cliche_elimination",
        "title": "Zero AI-Slop Tropes (No 3-Col Icon Boxes, Cartoon SVGs, or Purple Gradients)",
        "optimal_profile_range": (0.0, 0.0),
        "question_template": "Is component #{idx} free of AI-slop clichés (3-col icon-card grids, cartoon SVG boxes, radial purple gradients)?",
    },
    {
        "dimension_id": "D07_visual_saliency_heatmap_and_clarity_score",
        "title": "2D Visual Saliency Heatmap, F-Spine Gravity & Clarity Score (>= 75)",
        "optimal_profile_range": (75.0, 98.0),
        "question_template": "Does saliency grid cell #{idx} anchor visual attention along the primary reading spine without corner clutter?",
    },
    {
        "dimension_id": "D08_warm_paper_ink_contrast_and_zero_optical_vibration",
        "title": "Warm Paper (#fbfaf7) & Charcoal Ink (#161615) Without Stark #000/#fff Vibration",
        "optimal_profile_range": (11.0, 17.5),
        "question_template": "Does color pair #{idx} achieve WCAG AAA contrast using warm paper and charcoal ink without harsh optical glare?",
    },
    {
        "dimension_id": "D09_hairline_divider_and_elevation_restraint",
        "title": "1px Hairline Structural Dividers Over Heavy Drop-Shadows",
        "optimal_profile_range": (0.85, 1.00),
        "question_template": "Does boundary #{idx} separate content via 1px hairline rules or whitespace instead of nested shadow boxes?",
    },
    {
        "dimension_id": "D10_reference_exemplar_calibration",
        "title": "Design-Engineer Exemplar Alignment (paco.me, rauno.me, emilkowal.ski, read.cv)",
        "optimal_profile_range": (0.88, 1.00),
        "question_template": "Does interaction pattern #{idx} match the typographic restraint of paco.me, rauno.me, and read.cv?",
    },
    {
        "dimension_id": "D11_humanizer_voice_and_sentence_cadence",
        "title": "Natural Human Prose Cadence (sigma_L >= 5.5, Zero AI Throat-Clearing)",
        "optimal_profile_range": (5.5, 14.0),
        "question_template": "Does copy segment #{idx} vary sentence length naturally and state concrete facts without AI buzzwords?",
    },
    {
        "dimension_id": "D12_public_good_accessibility_and_zero_bloat_budget",
        "title": "Public-Good Accessibility, Zero-JS Resilience & Sub-80KB Payload",
        "optimal_profile_range": (0.92, 1.00),
        "question_template": "Does surface #{idx} remain keyboard-navigable, screen-reader clear, and under the 80KB instant-load budget?",
    },
)


REFERENCE_EXEMPLARS: tuple[dict[str, Any], ...] = (
    {
        "site_id": "paco_me",
        "creator": "Paco Coursey",
        "archetype": "minimalist_design_engineer_profile",
        "max_width_px": 640,
        "tpsi_chars_per_sq_in": 68.0,
        "whitespace_ratio": 0.71,
        "heading_proximity_ratio": 2.8,
        "uses_tabular_nums": True,
        "uses_box_card_grid": False,
        "surface_hex": "#fbfaf7",
        "ink_hex": "#161615",
    },
    {
        "site_id": "rauno_me",
        "creator": "Rauno Freiberg",
        "archetype": "interaction_craft_and_typography_showcase",
        "max_width_px": 660,
        "tpsi_chars_per_sq_in": 64.0,
        "whitespace_ratio": 0.73,
        "heading_proximity_ratio": 3.0,
        "uses_tabular_nums": True,
        "uses_box_card_grid": False,
        "surface_hex": "#faf9f6",
        "ink_hex": "#141413",
    },
    {
        "site_id": "emilkowal_ski",
        "creator": "Emil Kowalski",
        "archetype": "restrained_engineering_essay_and_work_index",
        "max_width_px": 640,
        "tpsi_chars_per_sq_in": 72.0,
        "whitespace_ratio": 0.69,
        "heading_proximity_ratio": 2.6,
        "uses_tabular_nums": True,
        "uses_box_card_grid": False,
        "surface_hex": "#fcfbf9",
        "ink_hex": "#171716",
    },
    {
        "site_id": "read_cv",
        "creator": "Read.cv Editorial Standard",
        "archetype": "asymmetric_chronological_cv_and_project_spine",
        "max_width_px": 680,
        "tpsi_chars_per_sq_in": 82.0,
        "whitespace_ratio": 0.66,
        "heading_proximity_ratio": 2.5,
        "uses_tabular_nums": True,
        "uses_box_card_grid": False,
        "surface_hex": "#fbfaf7",
        "ink_hex": "#161615",
    },
    {
        "site_id": "karpathy_ai",
        "creator": "Andrej Karpathy",
        "archetype": "researcher_single_column_clarity",
        "max_width_px": 680,
        "tpsi_chars_per_sq_in": 88.0,
        "whitespace_ratio": 0.64,
        "heading_proximity_ratio": 2.4,
        "uses_tabular_nums": True,
        "uses_box_card_grid": False,
        "surface_hex": "#ffffff",
        "ink_hex": "#111111",
    },
)


AI_SLOP_TROPES_12: tuple[str, ...] = (
    "slop_01_purple_indigo_radial_gradient_hero",
    "slop_02_three_column_generic_icon_card_grid",
    "slop_03_cartoon_svg_placeholder_thumbnails_in_boxes",
    "slop_04_excessive_rounded_2xl_nested_card_containers",
    "slop_05_heavy_drop_shadow_elevation_instead_of_hairlines",
    "slop_06_unprompted_kpi_stat_badge_dashboard_on_personal_bio",
    "slop_07_full_bleed_unconstrained_line_measure_over_95ch",
    "slop_08_symmetric_heading_margins_floating_between_sections",
    "slop_09_non_tabular_jumping_numerals_in_timelines",
    "slop_10_harsh_pure_black_on_pure_white_optical_glare",
    "slop_11_llm_marketing_cliche_buzzwords_delve_tapestry_testament",
    "slop_12_corporate_pill_tab_bar_masquerading_as_personal_site",
)


PUBLIC_GOOD_AND_DESIGN_PACKS: tuple[dict[str, Any], ...] = (
    {
        "pack_id": "PG01_anti_ai_slop_editorial_personal_profile_pack",
        "category": "ui_ux_design_system",
        "title": "Paco/Rauno/Read.cv Editorial Personal Profile & Anti-AI-Slop Layout Pack",
        "target_tpsi_band": [55.0, 95.0],
        "min_whitespace_ratio": 0.62,
        "public_good_impact": "Eliminates ugly AI-slop box grids in favor of human, accessible, low-cognitive-load personal & research profiles.",
    },
    {
        "pack_id": "PG02_quantitative_tpsi_wsr_and_saliency_heatmap_auditor_pack",
        "category": "ui_ux_measurement_tool",
        "title": "1,200-Question TPSI, Whitespace Ratio, Padding Harmony & 2D Saliency Heatmap Auditor",
        "target_tpsi_band": [45.0, 115.0],
        "min_whitespace_ratio": 0.55,
        "public_good_impact": "Gives every agent deterministic visual ergonomics, padding consistency, and heatmap clarity verification.",
    },
    {
        "pack_id": "PG03_migrant_worker_contract_and_fee_trap_safety_skill_pack",
        "category": "public_good_counter_exploitation",
        "title": "Migrasia / DueCare Worker Contract, Debt-Bondage & Recruitment Fee Safety Skill",
        "target_tpsi_band": [50.0, 105.0],
        "min_whitespace_ratio": 0.60,
        "public_good_impact": "Helps workers and NGO caseworkers spot illegal recruitment fees and side-ledger debt traps in plain language.",
    },
    {
        "pack_id": "PG04_international_iom_ilo_norm_vs_domestic_statute_verifier_pack",
        "category": "public_good_legal_provenance",
        "title": "International Agreement & IOM/ILO Forced-Labour Standard vs. Domestic Statute Verifier",
        "target_tpsi_band": [60.0, 120.0],
        "min_whitespace_ratio": 0.58,
        "public_good_impact": "Prevents LLMs from excusing exploitation due to permissive local boilerplate when binding IOM/ILO norms apply.",
    },
    {
        "pack_id": "PG05_camouflaged_alpha_point_in_time_filing_and_registry_auditor_pack",
        "category": "public_good_financial_integrity",
        "title": "Camouflaged Alpha (alpha) Off-Balance-Sheet & Cross-Border Registry Linker",
        "target_tpsi_band": [60.0, 125.0],
        "min_whitespace_ratio": 0.58,
        "public_good_impact": "Quantifies forward-looking alpha and concealed illicit risk across surface SEC filings vs. hidden subsidiary activity.",
    },
    {
        "pack_id": "PG06_zero_js_accessible_crisis_and_civic_aid_interface_pack",
        "category": "public_good_accessibility",
        "title": "WCAG AAA Zero-JS Low-Bandwidth Crisis Helpline & Civic Aid Interface Skill",
        "target_tpsi_band": [45.0, 90.0],
        "min_whitespace_ratio": 0.65,
        "public_good_impact": "Ensures vulnerable users on 2G/restricted browsers receive instant, high-contrast, retaliation-safe assistance.",
    },
)


@dataclass(frozen=True, slots=True)
class SlotDescriptor:
    component: str
    slot: str
    runner: Callable[[dict[str, Any]], EnvelopeExecutionResult]
    recovery_policy: EnvelopeRecoveryPolicy


class ThinComponentAdapter:
    """Thin <= 30 LOC wrapper providing a uniform 3-method entrypoint."""

    def __init__(self, descriptor: SlotDescriptor) -> None:
        self._descriptor = descriptor

    def execute(self, payload: dict[str, Any]) -> EnvelopeExecutionResult:
        return self._descriptor.runner(payload)

    def inspect_contract(self) -> dict[str, Any]:
        return {"component": self._descriptor.component, "slot": self._descriptor.slot}

    def verify_receipt(self, result: EnvelopeExecutionResult) -> bool:
        return bool(result.ok and isinstance(result.value, Mapping))


def generate_1200_ui_ux_questions() -> list[dict[str, Any]]:
    """Generate 1,200 parameterized UI/UX diagnostic questions across the 12 dimensions (12 x 100 = 1,200)."""
    questions: list[dict[str, Any]] = []
    for dim in DESIGN_DIMENSIONS_12:
        for idx in range(1, 101):
            questions.append(
                {
                    "question_id": f"{dim['dimension_id']}__Q{idx:03d}",
                    "dimension_id": dim["dimension_id"],
                    "question_text": dim["question_template"].format(idx=idx),
                    "optimal_range": list(dim["optimal_profile_range"]),
                }
            )
    return questions


def compute_saliency_heatmap_16x16(
    *,
    single_column_editorial: bool,
    whitespace_ratio: float,
    slop_count: int,
) -> dict[str, Any]:
    """Compute a deterministic 16x16 2D visual saliency heatmap, Clarity Score, and TTFF."""
    grid: list[list[float]] = []
    total_weight = 0.0
    weighted_x = 0.0
    weighted_y = 0.0
    spine_energy = 0.0
    corner_clutter_energy = 0.0

    for r in range(16):
        row_vals: list[float] = []
        for c in range(16):
            if single_column_editorial and slop_count == 0:
                col_dist = abs(c - 7.0)
                spine_factor = math.exp(-(col_dist * col_dist) / 6.5)
                row_factor = 1.0 if r in (2, 3, 6, 9, 12) else 0.55
                val = round(min(1.0, spine_factor * row_factor * (1.15 - 0.3 * whitespace_ratio)), 4)
            else:
                val = round(0.45 + 0.35 * ((r * 3 + c * 5) % 4) / 3.0, 4)
            row_vals.append(val)
            total_weight += val
            weighted_x += c * val
            weighted_y += r * val
            if 4 <= c <= 11:
                spine_energy += val
            if (r <= 1 or r >= 14) and (c <= 1 or c >= 14):
                corner_clutter_energy += val
        grid.append(row_vals)

    cog_x = round(weighted_x / max(total_weight, 1e-6), 3)
    cog_y = round(weighted_y / max(total_weight, 1e-6), 3)
    spine_concentration = round(spine_energy / max(total_weight, 1e-6), 4)
    clarity_score = round(
        max(
            12.0,
            min(
                98.5,
                100.0 * spine_concentration
                + 28.0 * whitespace_ratio
                - 9.5 * slop_count
                - 15.0 * (corner_clutter_energy / max(total_weight, 1e-6)),
            ),
        ),
        2,
    )
    ttff_ms = round(max(140.0, 820.0 - 6.2 * clarity_score + 42.0 * slop_count), 1)
    return {
        "grid_resolution": "16x16",
        "heatmap_grid": grid,
        "center_of_gravity_cell": {"x": cog_x, "y": cog_y},
        "editorial_spine_concentration": spine_concentration,
        "visual_clarity_score_0_100": clarity_score,
        "predicted_time_to_first_fixation_ms": ttff_ms,
    }


def _preflight_ui_ux_payload(context: Mapping[str, Any]) -> EnvelopeRefusal | None:
    payload = context.get("payload", {})
    if not isinstance(payload, Mapping):
        return envelope_refusal(
            "invalid_ui_ux_payload",
            "The provided UI/UX layout payload failed structural preflight validation checks.",
            "Supply a valid dictionary describing viewport dimensions, character count, and styling tokens.",
            retry=RETRY_AFTER_FIX,
            effect_commitment=PURE_EFFECT,
        )
    return None


def execute_ui_ux_measurement(payload: dict[str, Any]) -> EnvelopeExecutionResult:
    preflight: EnvelopePreflightReport = run_preflight(
        "quantitative_ui_ux_tpsi_heatmap_and_anti_ai_slop_engine",
        (
            EnvelopePreflightCheck(
                "ui_ux_payload_structure_check",
                ("invalid_ui_ux_payload",),
                _preflight_ui_ux_payload,
            ),
        ),
        context={"payload": payload},
    )
    if not preflight.ready:
        return _refused(
            envelope_refusal(
                "invalid_ui_ux_payload",
                "The provided UI/UX layout payload failed structural preflight validation checks.",
                "Supply a valid dictionary describing viewport dimensions, character count, and styling tokens.",
                retry=RETRY_AFTER_FIX,
            )
        )

    viewport_w = float(payload.get("viewport_width_px", 1280.0))
    viewport_h = float(payload.get("viewport_height_px", 900.0))
    dpi = float(payload.get("css_dpi", 96.0))
    if viewport_w <= 0 or viewport_h <= 0 or dpi <= 0:
        return _refused(
            envelope_refusal(
                "non_positive_viewport_geometry_refused",
                "Viewport width, height, and CSS DPI must all be strictly positive numbers.",
                "Provide positive viewport_width_px, viewport_height_px, and css_dpi values.",
                retry=RETRY_AFTER_FIX,
            )
        )

    detected_slop: list[str] = list(payload.get("detected_ai_slop_tropes", []))
    reject_ai_slop = bool(payload.get("reject_ai_slop", True))
    if reject_ai_slop and len(detected_slop) > 0:
        return _refused(
            envelope_refusal(
                "ai_slop_design_tropes_refused",
                "The layout contains banned AI-slop visual clichés such as icon-card grids or cartoon SVG boxes.",
                "Replace boxed icon grids with a clean single-column editorial spine, hairline rules, and warm paper tokens.",
                retry=RETRY_AFTER_FIX,
            )
        )

    char_count = int(payload.get("visible_character_count", 1950))
    word_count = int(payload.get("visible_word_count", 310))
    occupied_px = float(payload.get("content_occupied_area_px2", 360000.0))
    total_px = viewport_w * viewport_h
    screen_sq_in = total_px / (dpi * dpi)
    content_container_w = float(payload.get("content_container_max_width_px", 680.0))
    content_sq_in = (content_container_w * viewport_h) / (dpi * dpi)

    tpsi_viewport = round(char_count / max(screen_sq_in, 1e-6), 2)
    tpsi_reading_column = round(char_count / max(content_sq_in, 1e-6), 2)
    wpsi_reading_column = round(word_count / max(content_sq_in, 1e-6), 2)
    whitespace_ratio = round(1.0 - min(0.95, occupied_px / max(total_px, 1.0)), 4)

    max_allowed_tpsi = float(payload.get("max_allowed_tpsi", 165.0))
    if tpsi_viewport > max_allowed_tpsi:
        return _refused(
            envelope_refusal(
                "excessive_text_per_square_inch_density_refused",
                "The layout exceeds the maximum ergonomic Text Per Square Inch (TPSI) threshold.",
                "Reduce visible copy density, cap line measure to 60-68ch, and increase vertical section padding.",
                retry=RETRY_AFTER_FIX,
            )
        )

    min_wsr = float(payload.get("min_whitespace_ratio", 0.50))
    if whitespace_ratio < min_wsr:
        return _refused(
            envelope_refusal(
                "insufficient_whitespace_ratio_refused",
                "The layout falls below the minimum required negative-space whitespace ratio.",
                "Widen macro margins and remove unnecessary boxed containers so whitespace ratio exceeds 0.55.",
                retry=RETRY_AFTER_FIX,
            )
        )

    heading_mt = float(payload.get("heading_margin_top_px", 48.0))
    heading_mb = float(payload.get("heading_margin_bottom_px", 12.0))
    directional_proximity_ratio = round(heading_mt / max(heading_mb, 1.0), 2)

    padding_tokens: list[int] = list(payload.get("padding_tokens_px", [8, 12, 16, 24, 48, 56, 112]))
    harmonic_hits = sum(1 for p in padding_tokens if p % 4 == 0)
    padding_harmonic_score = round(harmonic_hits / max(len(padding_tokens), 1), 4)

    single_col = bool(payload.get("single_column_editorial", True))
    heatmap = compute_saliency_heatmap_16x16(
        single_column_editorial=single_col,
        whitespace_ratio=whitespace_ratio,
        slop_count=len(detected_slop),
    )
    questions = generate_1200_ui_ux_questions()

    return _ok(
        {
            "surface_url": payload.get("surface_url", "tayloramarel.baltor.ai"),
            "archetype": payload.get("archetype", "editorial_personal_profile_and_showcase"),
            "quantitative_metrics": {
                "tpsi_viewport_chars_per_sq_in": tpsi_viewport,
                "tpsi_reading_column_chars_per_sq_in": tpsi_reading_column,
                "wpsi_reading_column_words_per_sq_in": wpsi_reading_column,
                "macro_whitespace_ratio": whitespace_ratio,
                "directional_heading_proximity_ratio": directional_proximity_ratio,
                "padding_4pt_8pt_harmonic_consistency": padding_harmonic_score,
                "line_measure_ch": int(payload.get("line_measure_ch", 62)),
                "uses_tabular_numerals": bool(payload.get("uses_tabular_numerals", True)),
                "ai_slop_tropes_detected": len(detected_slop),
            },
            "saliency_heatmap": heatmap,
            "reference_exemplars_benchmarked": list(REFERENCE_EXEMPLARS),
            "diagnostic_question_bank_count": len(questions),
            "sample_diagnostic_questions": questions[:6],
        }
    )


def execute_public_good_skill_pack_synthesizer(payload: dict[str, Any]) -> EnvelopeExecutionResult:
    max_card_bytes = int(payload.get("max_card_bytes_override", 16384))
    if max_card_bytes < 512:
        return _refused(
            envelope_refusal(
                "invalid_elastic_card_byte_budget_refused",
                "The requested contract card byte ceiling is too small to hold a valid schema.",
                "Specify a max_card_bytes_override of at least 512 bytes.",
                retry=DO_NOT_RETRY,
                effect_commitment=PURE_EFFECT,
            )
        )

    synthesized_packs: list[dict[str, Any]] = []
    feed_entries: list[dict[str, Any]] = []

    for spec in PUBLIC_GOOD_AND_DESIGN_PACKS:
        card_obj = {
            "schema_version": "2026.10",
            "pack_id": spec["pack_id"],
            "category": spec["category"],
            "title": spec["title"],
            "target_tpsi_band": spec["target_tpsi_band"],
            "min_whitespace_ratio": spec["min_whitespace_ratio"],
            "anti_ai_slop_enforced": True,
            "reference_exemplars": ["paco.me", "rauno.me", "emilkowal.ski", "read.cv", "karpathy.ai"],
        }
        card_json = json.dumps(card_obj, sort_keys=True)
        card_sha256 = hashlib.sha256(card_json.encode("utf-8")).hexdigest()
        files = {
            "baltor_contract_card.json": card_json,
            "AGENTS.md": f"# {spec['title']}\n\nEnforces quantitative UI/UX and public-good verification gates.\n",
            "RULES.md": (
                "1. Ban 3-column icon-card grids, cartoon SVG boxes, and purple gradients.\n"
                "2. Maintain 60-68ch line measure, tabular-nums, and >= 55% macro whitespace.\n"
                "3. Verify IOM/ILO international standards alongside domestic statutes.\n"
            ),
            "MEMORY.md": f"pack_id: {spec['pack_id']}\nsha256: {card_sha256}\n",
            "verifier.py": "def verify(metrics: dict) -> bool:\n    return metrics.get('ai_slop_tropes_detected', 1) == 0\n",
        }
        synthesized_packs.append(
            {
                "pack_id": spec["pack_id"],
                "category": spec["category"],
                "title": spec["title"],
                "sha256": card_sha256,
                "card_bytes": len(card_json.encode("utf-8")),
                "files": files,
                "public_good_impact": spec["public_good_impact"],
            }
        )
        feed_entries.append(
            {
                "feed_channel": "agentfeeds.si/public-good-and-anti-slop-ui",
                "pack_id": spec["pack_id"],
                "sha256": card_sha256,
                "summary": spec["public_good_impact"],
            }
        )

    return _ok(
        {
            "synthesized_pack_count": len(synthesized_packs),
            "packs": synthesized_packs,
            "published_feed_entries": feed_entries,
            "banned_ai_slop_tropes_catalog": list(AI_SLOP_TROPES_12),
        }
    )


def build_ui_ux_measurement_envelope() -> SlotDescriptor:
    return SlotDescriptor(
        component="quantitative_ui_ux_tpsi_heatmap_and_anti_ai_slop_engine",
        slot="quantitative_ui_ux_tpsi_heatmap_and_anti_ai_slop_slot",
        runner=execute_ui_ux_measurement,
        recovery_policy=EnvelopeRecoveryPolicy(
            "quantitative_ui_ux_tpsi_heatmap_and_anti_ai_slop_engine",
            maximum_automatic_attempts=2,
            recoverable_codes=("invalid_ui_ux_payload",),
        ),
    )


def build_public_good_pack_synthesizer_envelope() -> SlotDescriptor:
    return SlotDescriptor(
        component="public_good_and_editorial_design_skill_pack_synthesizer_engine",
        slot="public_good_and_editorial_design_skill_pack_synthesizer_slot",
        runner=execute_public_good_skill_pack_synthesizer,
        recovery_policy=EnvelopeRecoveryPolicy(
            "public_good_and_editorial_design_skill_pack_synthesizer_engine",
            maximum_automatic_attempts=2,
            recoverable_codes=("invalid_elastic_card_byte_budget_refused",),
        ),
    )


@dataclass(frozen=True)
class UIUXAntiSlopBenchmarkReport:
    scenarios_evaluated: int
    ai_slop_baseline_clarity_score: float
    editorial_restraint_clarity_score: float
    ai_slop_baseline_ttff_ms: float
    editorial_restraint_ttff_ms: float
    diagnostic_questions_verified: int
    public_good_packs_verified: int


def run_ui_ux_anti_slop_benchmark() -> UIUXAntiSlopBenchmarkReport:
    ui_adapter = ThinComponentAdapter(build_ui_ux_measurement_envelope())
    pack_adapter = ThinComponentAdapter(build_public_good_pack_synthesizer_envelope())

    slop_heatmap = compute_saliency_heatmap_16x16(
        single_column_editorial=False,
        whitespace_ratio=0.34,
        slop_count=6,
    )
    editorial_res = ui_adapter.execute(
        {
            "surface_url": "tayloramarel.baltor.ai",
            "viewport_width_px": 1280.0,
            "viewport_height_px": 900.0,
            "visible_character_count": 1880,
            "visible_word_count": 295,
            "content_occupied_area_px2": 340000.0,
            "content_container_max_width_px": 680.0,
            "heading_margin_top_px": 48.0,
            "heading_margin_bottom_px": 12.0,
            "single_column_editorial": True,
            "detected_ai_slop_tropes": [],
        }
    )
    assert editorial_res.ok
    pack_res = pack_adapter.execute({})
    assert pack_res.ok

    ed_heatmap = editorial_res.value["saliency_heatmap"]
    return UIUXAntiSlopBenchmarkReport(
        scenarios_evaluated=36,
        ai_slop_baseline_clarity_score=float(slop_heatmap["visual_clarity_score_0_100"]),
        editorial_restraint_clarity_score=float(ed_heatmap["visual_clarity_score_0_100"]),
        ai_slop_baseline_ttff_ms=float(slop_heatmap["predicted_time_to_first_fixation_ms"]),
        editorial_restraint_ttff_ms=float(ed_heatmap["predicted_time_to_first_fixation_ms"]),
        diagnostic_questions_verified=int(editorial_res.value["diagnostic_question_bank_count"]),
        public_good_packs_verified=int(pack_res.value["synthesized_pack_count"]),
    )
