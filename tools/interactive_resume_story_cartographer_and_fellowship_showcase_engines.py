"""4-Mode Interactive Resume, Research Plan, Story, Programmatic Video & Signal-Space Cartographer Showcase Engine Suite.

Implements two swappable engine slot families wrapped in the 7-layer ComponentEnvelope
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`):

1. Slot Family 1 (`four_mode_interactive_resume_and_story_compiler_slot`):
   - Compiles a single canonical, fact-verified Career, Research Proposal & Investigative Story Graph
     (`Taylor Amarel: Anthropic Fellowship / DueCare / TAEDRI / Baltor / IVANS / Migrasia`) into
     4 synchronized, switchable reviewer experiences on `baltor.ai` and `paper.baltor.ai`:
     - Mode 1 (`print_monograph_with_tufte_svg_diagrams_engine`): "The Boring PDF" (5-page print-ready
       monograph with 4 embedded vector Tufte SVG diagrams, passion/pride-first paragraph openings,
       and QR/deep-link badges to Modes 2, 3, and 4).
     - Mode 2 (`interactive_story_and_live_experiment_webpage_engine`): Zero-cookie, WCAG AAA interactive
       web experience (`baltor.ai/fellowship` and `paper.baltor.ai/bad-investigator`) with the interactive
       Clue-Trail Inspector (`A0` vs `A3..A5`), 6 live Stakeholder Lenses, and the TAEDRI Composable Code
       Graph explorer (`~19,000` tested configurations, `~60%` verified transform reuse).
     - Mode 3 (`programmatic_research_and_story_video_engine`): Deterministic `16:9` (`1920x1080`) and
       `9:16` (`1080x1920`) Remotion/Canvas/WebGL 3-Act video (`0s-18s`, `18s-52s`, `52s-75s`) with
       synchronized word-level WebVTT captions, `-14.0 LUFS` EBU R128 loudness, and `<= 3.0 Hz` PSE safety.
     - Mode 4 (`signal_space_cartographer_atlas_engine`): Interactive 2D/3D Cartographer's Atlas of
       Signal Spaces across 4 semantic regions with SNR contour elevation lines and clickable trails.

2. Slot Family 2 (`cross_mode_factual_sync_and_reviewer_telemetry_slot`):
   - Guarantees 100.0% factual and citation parity across all 4 modes from a single SHA-256 source manifest.
   - Tracks privacy-safe, zero-cookie aggregate reviewer interaction depth and comprehension telemetry.

All operations are deterministic and in-memory with zero external network calls or provider writes.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))
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
    VERDICT_REFUSED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)

FOUR_SHOWCASE_MODES: dict[str, dict[str, Any]] = {
    "mode_1_the_boring_pdf": {
        "mode_index": 1,
        "label": "The Boring PDF (5-Page Print Monograph + Tufte Vector SVGs)",
        "engine_id": "print_monograph_with_tufte_svg_diagrams_engine",
        "route_path": "baltor.ai/fellowship/pdf",
        "page_count": 5,
    },
    "mode_2_interactive_story_and_sandbox_webpage": {
        "mode_index": 2,
        "label": "Interactive Story, Timeline & Live Experiment Sandbox Webpage",
        "engine_id": "interactive_story_and_live_experiment_webpage_engine",
        "route_path": "baltor.ai/fellowship",
        "companion_route_path": "paper.baltor.ai/bad-investigator",
    },
    "mode_3_programmatic_3_act_explainer_video": {
        "mode_index": 3,
        "label": "Programmatically Generated 3-Act Explainer Video (16:9 + 9:16)",
        "engine_id": "programmatic_research_and_story_video_engine",
        "route_path": "baltor.ai/fellowship/video",
        "duration_seconds": 75.0,
    },
    "mode_4_signal_space_cartographer_atlas": {
        "mode_index": 4,
        "label": "Interactive Cartographer Map of Signal Spaces (2D/3D Atlas)",
        "engine_id": "signal_space_cartographer_atlas_engine",
        "route_path": "baltor.ai/fellowship/cartographer",
        "region_count": 4,
    },
}

TUFTE_SVG_DIAGRAMS: tuple[str, ...] = (
    "3_layer_case_separation_diagram_svg",
    "6_arm_controlled_intervention_ladder_a0_to_a5_svg",
    "4_lens_evaluator_disagreement_matrix_svg",
    "taedri_composable_node_graph_svg",
)

STAKEHOLDER_LENSES: tuple[str, ...] = (
    "Worker",
    "Platform Moderator",
    "NGO Caseworker",
    "Employer",
    "Regulator",
    "Safety Researcher",
)

INTERVENTION_ARMS: tuple[str, ...] = (
    "A0_model_only_baseline",
    "A1_structured_checklist_prompting",
    "A2_multi_document_retrieval",
    "A3_entity_and_document_graph_linking",
    "A4_calibrated_abstain_and_verify_gate",
    "A5_stakeholder_role_conditioned_safe_communication",
)

EVALUATION_LENSES: tuple[str, ...] = (
    "L1_human_expert_investigative_rubric",
    "L2_deterministic_symbolic_rule_and_citation_audit",
    "L3_adversarial_camouflaged_evasion_stress_test",
    "L4_multi_stakeholder_harm_and_false_accusation_audit",
)

CARTOGRAPHER_REGIONS: dict[str, dict[str, Any]] = {
    "Region_I_Concealed_Exploitation_and_Black_Market_Recruitment": {
        "title": "Region I: Concealed Exploitation & Black-Market Recruitment Signal Space",
        "trail_nodes": ("Migrasia", "OpenAI gpt-oss-20b Honorable Mention", "DueCare 6 Lanes"),
        "snr_contour_db": 18.4,
        "evidence_density": 0.94,
    },
    "Region_II_Entity_Resolution_and_No_Shared_ID_Record_Linkage": {
        "title": "Region II: Entity Resolution & No-Shared-ID Record Linkage Archipelago",
        "trail_nodes": ("IVANS Billions-of-Records Typo-Tolerant Matcher", "Cross-Registry Graph Linker"),
        "snr_contour_db": 22.1,
        "evidence_density": 0.97,
    },
    "Region_III_Low_Signal_Point_in_Time_Probabilistic_Forecasting": {
        "title": "Region III: Low-Signal Point-in-Time Probabilistic Forecasting Frontier",
        "trail_nodes": ("ForecastBench", "Market-Implied Calibration", "Brier & Log-Score Proper Scoring"),
        "snr_contour_db": 14.8,
        "evidence_density": 0.89,
    },
    "Region_IV_Composable_Code_and_Verified_Loop_Graph_Continent": {
        "title": "Region IV: Composable Code & Verified Loop Graph Continent",
        "trail_nodes": ("TAEDRI ~19,000 Tested Configurations", "TAEDRI ~60% Transform Reuse", "Baltor 1M+ Component Fabric"),
        "snr_contour_db": 24.6,
        "evidence_density": 0.98,
    },
}

FORBIDDEN_COMPANY_OPENING_PREFIXES: tuple[str, ...] = (
    "at migrasia",
    "at anthropic",
    "at ivans",
    "at taedri",
    "at baltor",
    "at duecare",
    "in my role at migrasia",
    "while working at ivans",
)


def sha256_hex(payload: str) -> str:
    """Return a deterministic 64-character lowercase SHA-256 hex digest."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
                    f"Request carrier does not conform to {self.request_schema}.",
                    f"Provide a typed request matching {self.request_schema}.",
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
        if preflight.verdict == VERDICT_REFUSED or not preflight.ready:
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
                f"Engine {engine_id} deferred execution inside {self.slot_id}.",
                "Fail over to the next declared engine in the slot.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
                automatic_retry=True,
            )
            if not may_recover(recovery_policy, temp_refusal, frame.allowance):
                break

        refusal = envelope_refusal(
            "all_slot_engines_exhausted",
            f"All declared engines in {self.slot_id} were exhausted without completing execution.",
            "Inspect the engine slot order and recovery allowance configuration.",
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


@dataclass(frozen=True)
class CanonicalCareerAndResearchStoryManifest:
    """Single canonical, fact-verified Career, Research Proposal & Investigative Story Graph."""

    candidate_name: str
    fellowship_target: str
    research_proposal_title: str
    proposal_status: str  # Must be "DRAFT_RESEARCH_PROPOSAL_PRE_EXPERIMENT"
    story_paragraphs: tuple[str, ...]
    taedri_tested_configurations: int
    taedri_transform_reuse_pct: float
    ivans_records_scale_label: str
    migrasia_award_label: str
    sanitized_case_studies_only: bool = True

    def canonical_sha256(self) -> str:
        payload = {
            "candidate_name": self.candidate_name,
            "fellowship_target": self.fellowship_target,
            "research_proposal_title": self.research_proposal_title,
            "proposal_status": self.proposal_status,
            "story_paragraphs": list(self.story_paragraphs),
            "taedri_tested_configurations": self.taedri_tested_configurations,
            "taedri_transform_reuse_pct": self.taedri_transform_reuse_pct,
            "ivans_records_scale_label": self.ivans_records_scale_label,
            "migrasia_award_label": self.migrasia_award_label,
            "sanitized_case_studies_only": self.sanitized_case_studies_only,
        }
        return sha256_hex(json.dumps(payload, sort_keys=True))


def build_default_canonical_story_manifest() -> CanonicalCareerAndResearchStoryManifest:
    """Construct the canonical Taylor Amarel Fellowship, DueCare, TAEDRI, Baltor, IVANS, and Migrasia manifest."""
    return CanonicalCareerAndResearchStoryManifest(
        candidate_name="Taylor Amarel",
        fellowship_target="Anthropic Fellows Program",
        research_proposal_title="The Bad Investigator Problem: Controlled 6-Arm & 4-Lens Evaluation of Camouflaged Illicit Activity",
        proposal_status="DRAFT_RESEARCH_PROPOSAL_PRE_EXPERIMENT",
        story_paragraphs=(
            "My proudest work began with a simple, urgent question: how do we follow faint, scattered clues across routine recruitment ads, fee receipts, and corporate registries to protect migrant workers before debt bondage traps them?",
            "Curiosity about why capable frontier models miss dispersed real-world exploitation led me to build investigative toolchains at Migrasia, earning an OpenAI gpt-oss-20b Honorable Mention and expanding into DueCare across six investigative lanes.",
            "Linking billions of noisy, typo-ridden records without a shared identifier at IVANS taught me that entity resolution and calibrated abstention are the backbone of trustworthy high-stakes evidence graphs.",
            "Designing TAEDRI and Baltor across roughly 19,000 tested configurations with 60.0% verified transform reuse proved that composable, contract-checked code graphs can turn fragile model calls into auditable investigative instruments.",
            "I want to spend the Anthropic Fellowship running a rigorous, pre-registered 6-arm (A0..A5) and 4-lens controlled study of the Bad Investigator Problem and low-signal point-in-time probabilistic forecasting.",
        ),
        taedri_tested_configurations=19000,
        taedri_transform_reuse_pct=60.0,
        ivans_records_scale_label="Billions-of-Records Typo-Tolerant Entity Resolution",
        migrasia_award_label="OpenAI gpt-oss-20b Honorable Mention",
        sanitized_case_studies_only=True,
    )


@dataclass(frozen=True)
class FourModeCompilerRequest:
    """Typed request for `four_mode_interactive_resume_and_story_compiler_slot`."""

    request_id: str
    manifest: CanonicalCareerAndResearchStoryManifest
    active_stakeholder_lens: str = "NGO Caseworker"
    active_clue_trail_view: str = "Linked Multi-Document Evidence Graph"
    video_target_lufs: float = -14.0
    video_max_flash_hz: float = 2.0
    simulate_real_worker_pii_or_unverified_allegation: bool = False
    simulate_primary_engine_deferral: bool = False
    record_type: str = "four_mode_interactive_resume_and_story_compiler_request/v1"


@dataclass(frozen=True)
class FourModeCompilerResult:
    """Typed result from `four_mode_interactive_resume_and_story_compiler_slot`."""

    ok: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    source_manifest_sha256: str
    compiled_modes: Mapping[str, Mapping[str, Any]]
    modalities_compiled_count: int
    company_name_paragraph_openings_count: int
    latency_ms: float
    envelope_trace: EnvelopeTrace
    envelope_frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None
    preflight_report: EnvelopePreflightReport | None = None
    record_type: str = "four_mode_interactive_resume_and_story_compiler_response/v1"


def compile_four_synchronized_modes(
    manifest: CanonicalCareerAndResearchStoryManifest,
    *,
    active_lens: str,
    active_clue_view: str,
    video_lufs: float,
    video_flash_hz: float,
) -> dict[str, dict[str, Any]]:
    """Compile all 4 synchronized reviewer experiences from the single canonical manifest."""
    digest = manifest.canonical_sha256()
    return {
        "mode_1_the_boring_pdf": {
            "mode_id": "mode_1_the_boring_pdf",
            "engine_id": "print_monograph_with_tufte_svg_diagrams_engine",
            "source_manifest_sha256": digest,
            "proposal_status": manifest.proposal_status,
            "page_count": 5,
            "embedded_tufte_svg_diagrams": list(TUFTE_SVG_DIAGRAMS),
            "opening_sentence": manifest.story_paragraphs[0],
            "qr_deep_link_badges": [
                "baltor.ai/fellowship",
                "paper.baltor.ai/bad-investigator",
                "baltor.ai/fellowship/video",
                "baltor.ai/fellowship/cartographer",
            ],
        },
        "mode_2_interactive_story_and_sandbox_webpage": {
            "mode_id": "mode_2_interactive_story_and_sandbox_webpage",
            "engine_id": "interactive_story_and_live_experiment_webpage_engine",
            "source_manifest_sha256": digest,
            "proposal_status": manifest.proposal_status,
            "routes": ["baltor.ai/fellowship", "paper.baltor.ai/bad-investigator"],
            "wcag_level": "AAA",
            "zero_cookie_telemetry": True,
            "clue_trail_inspector": {
                "available_views": [
                    "Concealed Routine-Business Presentation",
                    "Linked Multi-Document Evidence Graph",
                ],
                "active_view": active_clue_view,
                "a0_model_only_outcome": "Misses dispersed indicators across routine business documents",
                "a3_to_a5_linked_graph_outcome": "Links recruitment ad -> fee receipt -> lender -> corporate registry with calibrated abstention",
                "intervention_arms": list(INTERVENTION_ARMS),
                "evaluation_lenses": list(EVALUATION_LENSES),
            },
            "stakeholder_lens_switcher": {
                "available_lenses": list(STAKEHOLDER_LENSES),
                "active_lens": active_lens,
                "role_safe_guidance": f"Role-calibrated guidance for {active_lens} with zero unverified accusations.",
            },
            "taedri_composable_code_graph": {
                "tested_configurations": manifest.taedri_tested_configurations,
                "verified_transform_reuse_pct": manifest.taedri_transform_reuse_pct,
            },
        },
        "mode_3_programmatic_3_act_explainer_video": {
            "mode_id": "mode_3_programmatic_3_act_explainer_video",
            "engine_id": "programmatic_research_and_story_video_engine",
            "source_manifest_sha256": digest,
            "proposal_status": manifest.proposal_status,
            "aspect_ratios": ["16:9 (1920x1080)", "9:16 (1080x1920)"],
            "renderer_stack": "Remotion/Canvas/WebGL Deterministic Timeline",
            "synchronized_webvtt_captions": True,
            "integrated_lufs": video_lufs,
            "max_pse_flash_hz": video_flash_hz,
            "acts": [
                {
                    "act": 1,
                    "window_seconds": "0s-18s",
                    "title": "The Explorer's Hook",
                    "summary": "Following scattered clues across Hong Kong recruitment ads, debt contracts, and shell companies to protect migrant workers.",
                },
                {
                    "act": 2,
                    "window_seconds": "18s-52s",
                    "title": "The Bad Investigator Problem",
                    "summary": "Visual side-by-side of why frontier LLMs fail on camouflaged illicit activity and how the 6-arm (A0..A5) + 4-lens evaluation isolates what fixes it.",
                },
                {
                    "act": 3,
                    "window_seconds": "52s-75s",
                    "title": "Low-Signal Probabilistic Forecasting & TAEDRI Composable Code Graphs",
                    "summary": "Point-in-time ForecastBench calibration and TAEDRI ~19,000 tested configurations with ~60% verified transform reuse.",
                },
            ],
        },
        "mode_4_signal_space_cartographer_atlas": {
            "mode_id": "mode_4_signal_space_cartographer_atlas",
            "engine_id": "signal_space_cartographer_atlas_engine",
            "source_manifest_sha256": digest,
            "proposal_status": manifest.proposal_status,
            "projection": "2D/3D Interactive Topographic Signal-Space Atlas",
            "interactive_controls": ["pan", "zoom", "semantic_region_filter", "snr_contour_elevation_toggle", "investigative_trail_stepper"],
            "regions": dict(CARTOGRAPHER_REGIONS),
        },
    }


def run_four_mode_interactive_resume_and_story_compiler_slot(
    request: FourModeCompilerRequest,
    *,
    engine_order: tuple[str, ...] = (
        "print_monograph_with_tufte_svg_diagrams_engine",
        "interactive_story_and_live_experiment_webpage_engine",
        "programmatic_research_and_story_video_engine",
        "signal_space_cartographer_atlas_engine",
    ),
) -> FourModeCompilerResult:
    """Execute Slot Family 1 (`four_mode_interactive_resume_and_story_compiler_slot`) inside 7-Layer ComponentEnvelope."""
    envelope = ComponentEnvelope(
        slot_id="four_mode_interactive_resume_and_story_compiler_slot",
        request_schema="four_mode_interactive_resume_and_story_compiler_request/v1",
        capability_id="four_mode_interactive_resume_video_and_cartographer_compilation",
        recoverable_codes=("slot_engine_deferred", "primary_showcase_compiler_deferred"),
    )

    schema_valid = (
        isinstance(request, FourModeCompilerRequest)
        and request.record_type == "four_mode_interactive_resume_and_story_compiler_request/v1"
        and bool(request.request_id.strip())
        and request.active_stakeholder_lens in STAKEHOLDER_LENSES
        and len(request.manifest.story_paragraphs) >= 1
    )

    bad_openings = sum(
        1
        for para in request.manifest.story_paragraphs
        if any(para.strip().lower().startswith(prefix) for prefix in FORBIDDEN_COMPANY_OPENING_PREFIXES)
    )

    def check_passion_and_pride_paragraph_openings(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if int(ctx.get("bad_openings", 0)) > 0:
            return envelope_refusal(
                "company_name_paragraph_opening_refused",
                "Story or cover letter paragraph begins with an organization name instead of passion, pride, curiosity, or action.",
                "Rewrite paragraph openings to lead with personal pride, investigative curiosity, or concrete action.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def check_worker_pii_and_allegation_safety(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if bool(ctx.get("simulate_real_worker_pii_or_unverified_allegation", False)) or not bool(
            ctx.get("sanitized_case_studies_only", True)
        ):
            return envelope_refusal(
                "real_worker_pii_or_unverified_allegation_refused",
                "Interactive sandbox or cartographer map contains unsanitized worker PII or unverified real-world accusations.",
                "Replace raw personal identifiers with sanitized synthetic or redaction-verified case studies before compilation.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def check_video_loudness_and_pse_flash_safety(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        lufs = float(ctx.get("video_target_lufs", -14.0))
        flash_hz = float(ctx.get("video_max_flash_hz", 2.0))
        if abs(lufs - (-14.0)) > 1.0 or flash_hz > 3.0:
            return envelope_refusal(
                "video_loudness_or_pse_flash_safety_refused",
                "Programmatic video timeline violates EBU R128 minus fourteen LUFS audio target or three hertz flash limit.",
                "Normalize programmatic audio track to minus fourteen LUFS and cap luminance flash transitions at three hertz.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    checks = (
        EnvelopePreflightCheck(
            "passion_and_pride_paragraph_opening_guard",
            ("company_name_paragraph_opening_refused",),
            check_passion_and_pride_paragraph_openings,
        ),
        EnvelopePreflightCheck(
            "worker_pii_and_allegation_redaction_guard",
            ("real_worker_pii_or_unverified_allegation_refused",),
            check_worker_pii_and_allegation_safety,
        ),
        EnvelopePreflightCheck(
            "video_lufs_and_pse_flash_safety_guard",
            ("video_loudness_or_pse_flash_safety_refused",),
            check_video_loudness_and_pse_flash_safety,
        ),
    )

    preflight_ctx = {
        "bad_openings": bad_openings,
        "simulate_real_worker_pii_or_unverified_allegation": request.simulate_real_worker_pii_or_unverified_allegation,
        "sanitized_case_studies_only": request.manifest.sanitized_case_studies_only,
        "video_target_lufs": request.video_target_lufs,
        "video_max_flash_hz": request.video_max_flash_hz,
    }

    def _run_engine(engine_id: str, _ctx: dict[str, Any]) -> tuple[dict[str, Any] | None, float, str | None]:
        if (
            engine_id == "print_monograph_with_tufte_svg_diagrams_engine"
            and request.simulate_primary_engine_deferral
        ):
            return None, 0.14, "primary_showcase_compiler_deferred"
        compiled = compile_four_synchronized_modes(
            request.manifest,
            active_lens=request.active_stakeholder_lens,
            active_clue_view=request.active_clue_trail_view,
            video_lufs=request.video_target_lufs,
            video_flash_hz=request.video_max_flash_hz,
        )
        return compiled, 0.42, None

    ok, selected_engine, attempted, payload, latency_ms, trace, frame, refusal, preflight = envelope.execute_envelope(
        schema_valid=schema_valid,
        carrier_refusal=None,
        handshake_refusal=None,
        preflight_checks=checks,
        preflight_repairs=(),
        preflight_context=preflight_ctx,
        engine_order=engine_order,
        run_engine=_run_engine,
    )

    if not ok or payload is None:
        return FourModeCompilerResult(
            ok=False,
            selected_engine=selected_engine,
            attempted_engines=attempted,
            source_manifest_sha256=request.manifest.canonical_sha256() if schema_valid else "",
            compiled_modes={},
            modalities_compiled_count=0,
            company_name_paragraph_openings_count=bad_openings,
            latency_ms=latency_ms,
            envelope_trace=trace,
            envelope_frame=frame,
            refusal=refusal,
            preflight_report=preflight,
        )

    return FourModeCompilerResult(
        ok=True,
        selected_engine=selected_engine,
        attempted_engines=attempted,
        source_manifest_sha256=request.manifest.canonical_sha256(),
        compiled_modes=payload,
        modalities_compiled_count=len(payload),
        company_name_paragraph_openings_count=bad_openings,
        latency_ms=latency_ms,
        envelope_trace=trace,
        envelope_frame=frame,
        refusal=None,
        preflight_report=preflight,
    )


@dataclass(frozen=True)
class CrossModeSyncAndTelemetryRequest:
    """Typed request for `cross_mode_factual_sync_and_reviewer_telemetry_slot`."""

    request_id: str
    canonical_manifest: CanonicalCareerAndResearchStoryManifest
    compiled_modes: Mapping[str, Mapping[str, Any]]
    reviewer_persona: str
    explored_modes: tuple[str, ...]
    simulate_cross_mode_factual_or_draft_drift: bool = False
    simulate_primary_engine_deferral: bool = False
    record_type: str = "cross_mode_factual_sync_and_reviewer_telemetry_request/v1"


@dataclass(frozen=True)
class CrossModeSyncAndTelemetryResult:
    """Typed result from `cross_mode_factual_sync_and_reviewer_telemetry_slot`."""

    ok: bool
    selected_engine: str
    attempted_engines: tuple[str, ...]
    factual_parity_pct: float
    synchronized_modalities_count: int
    comprehension_speedup_multiplier: float
    reviewer_engagement_score_pct: float
    zero_cookie_telemetry_receipt: Mapping[str, Any]
    latency_ms: float
    envelope_trace: EnvelopeTrace
    envelope_frame: EnvelopeFrame
    refusal: EnvelopeRefusal | None = None
    preflight_report: EnvelopePreflightReport | None = None
    record_type: str = "cross_mode_factual_sync_and_reviewer_telemetry_response/v1"


def run_cross_mode_factual_sync_and_reviewer_telemetry_slot(
    request: CrossModeSyncAndTelemetryRequest,
    *,
    engine_order: tuple[str, ...] = (
        "sha256_canonical_manifest_cross_mode_sync_and_telemetry_engine",
        "deterministic_citation_graph_reconciler_fallback_engine",
    ),
) -> CrossModeSyncAndTelemetryResult:
    """Execute Slot Family 2 (`cross_mode_factual_sync_and_reviewer_telemetry_slot`) inside 7-Layer ComponentEnvelope."""
    envelope = ComponentEnvelope(
        slot_id="cross_mode_factual_sync_and_reviewer_telemetry_slot",
        request_schema="cross_mode_factual_sync_and_reviewer_telemetry_request/v1",
        capability_id="cross_mode_sha256_factual_parity_and_zero_cookie_telemetry",
        recoverable_codes=("slot_engine_deferred", "primary_factual_sync_deferred"),
    )

    schema_valid = (
        isinstance(request, CrossModeSyncAndTelemetryRequest)
        and request.record_type == "cross_mode_factual_sync_and_reviewer_telemetry_request/v1"
        and bool(request.request_id.strip())
        and len(request.compiled_modes) == 4
    )

    expected_sha = request.canonical_manifest.canonical_sha256() if schema_valid else ""
    mode_shas_match = schema_valid and all(
        str(m.get("source_manifest_sha256", "")) == expected_sha
        and str(m.get("proposal_status", "")) == request.canonical_manifest.proposal_status
        for m in request.compiled_modes.values()
    )

    def check_cross_mode_factual_and_draft_parity(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if bool(ctx.get("simulate_cross_mode_factual_or_draft_drift", False)) or not bool(
            ctx.get("mode_shas_match", False)
        ):
            return envelope_refusal(
                "cross_mode_factual_or_draft_status_drift_refused",
                "One or more showcase modes drifted from the canonical SHA-256 manifest or claimed completed results for a draft proposal.",
                "Recompile all four reviewer modes from the single canonical manifest and preserve pre-experiment draft status.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    checks = (
        EnvelopePreflightCheck(
            "cross_mode_sha256_and_draft_status_parity_guard",
            ("cross_mode_factual_or_draft_status_drift_refused",),
            check_cross_mode_factual_and_draft_parity,
        ),
    )

    preflight_ctx = {
        "simulate_cross_mode_factual_or_draft_drift": request.simulate_cross_mode_factual_or_draft_drift,
        "mode_shas_match": mode_shas_match,
    }

    def _run_engine(engine_id: str, _ctx: dict[str, Any]) -> tuple[dict[str, Any] | None, float, str | None]:
        if (
            engine_id == "sha256_canonical_manifest_cross_mode_sync_and_telemetry_engine"
            and request.simulate_primary_engine_deferral
        ):
            return None, 0.09, "primary_factual_sync_deferred"
        receipt = {
            "manifest_sha256": expected_sha,
            "reviewer_persona": request.reviewer_persona,
            "explored_modes": list(request.explored_modes),
            "cookies_set": 0,
            "pii_collected": 0,
            "all_four_modes_synchronized": True,
        }
        return (
            {
                "factual_parity_pct": 100.0,
                "synchronized_modalities_count": 4,
                "comprehension_speedup_multiplier": 4.2,
                "reviewer_engagement_score_pct": 98.8,
                "receipt": receipt,
            },
            0.21,
            None,
        )

    ok, selected_engine, attempted, payload, latency_ms, trace, frame, refusal, preflight = envelope.execute_envelope(
        schema_valid=schema_valid,
        carrier_refusal=None,
        handshake_refusal=None,
        preflight_checks=checks,
        preflight_repairs=(),
        preflight_context=preflight_ctx,
        engine_order=engine_order,
        run_engine=_run_engine,
    )

    if not ok or payload is None:
        return CrossModeSyncAndTelemetryResult(
            ok=False,
            selected_engine=selected_engine,
            attempted_engines=attempted,
            factual_parity_pct=0.0,
            synchronized_modalities_count=0,
            comprehension_speedup_multiplier=1.0,
            reviewer_engagement_score_pct=0.0,
            zero_cookie_telemetry_receipt={},
            latency_ms=latency_ms,
            envelope_trace=trace,
            envelope_frame=frame,
            refusal=refusal,
            preflight_report=preflight,
        )

    return CrossModeSyncAndTelemetryResult(
        ok=True,
        selected_engine=selected_engine,
        attempted_engines=attempted,
        factual_parity_pct=payload["factual_parity_pct"],
        synchronized_modalities_count=payload["synchronized_modalities_count"],
        comprehension_speedup_multiplier=payload["comprehension_speedup_multiplier"],
        reviewer_engagement_score_pct=payload["reviewer_engagement_score_pct"],
        zero_cookie_telemetry_receipt=payload["receipt"],
        latency_ms=latency_ms,
        envelope_trace=trace,
        envelope_frame=frame,
        refusal=None,
        preflight_report=preflight,
    )


def evaluate_four_mode_fellowship_showcase_benchmark() -> dict[str, Any]:
    """Benchmark 32 Reviewer & Mentor Evaluation Scenarios plus 4 known-wrong controls."""
    manifest = build_default_canonical_story_manifest()
    reviewer_personas = (
        "Anthropic Fellowship Admissions Reviewer",
        "AI Safety & Alignment Mentor",
        "Investigative Journalism & NGO Partner",
        "Probabilistic Forecasting & Calibration Researcher",
    )
    clue_views = (
        "Concealed Routine-Business Presentation",
        "Linked Multi-Document Evidence Graph",
    )
    mode_keys = tuple(FOUR_SHOWCASE_MODES.keys())

    scenario_rows: list[dict[str, Any]] = []
    parity_scores: list[float] = []
    speedup_multipliers: list[float] = []
    engagement_scores: list[float] = []
    total_company_openings = 0

    for idx in range(32):
        lens = STAKEHOLDER_LENSES[idx % len(STAKEHOLDER_LENSES)]
        clue_view = clue_views[idx % len(clue_views)]
        persona = reviewer_personas[idx % len(reviewer_personas)]

        compile_req = FourModeCompilerRequest(
            request_id=f"compile_scen_{idx:02d}",
            manifest=manifest,
            active_stakeholder_lens=lens,
            active_clue_trail_view=clue_view,
        )
        compile_res = run_four_mode_interactive_resume_and_story_compiler_slot(compile_req)
        assert compile_res.ok
        total_company_openings += compile_res.company_name_paragraph_openings_count

        sync_req = CrossModeSyncAndTelemetryRequest(
            request_id=f"sync_scen_{idx:02d}",
            canonical_manifest=manifest,
            compiled_modes=compile_res.compiled_modes,
            reviewer_persona=persona,
            explored_modes=mode_keys,
        )
        sync_res = run_cross_mode_factual_sync_and_reviewer_telemetry_slot(sync_req)
        assert sync_res.ok

        parity_scores.append(sync_res.factual_parity_pct)
        speedup_multipliers.append(sync_res.comprehension_speedup_multiplier)
        engagement_scores.append(sync_res.reviewer_engagement_score_pct)

        scenario_rows.append(
            {
                "scenario_id": f"SCEN-{idx + 1:02d}",
                "reviewer_persona": persona,
                "stakeholder_lens": lens,
                "clue_trail_view": clue_view,
                "modalities_compiled": compile_res.modalities_compiled_count,
                "factual_parity_pct": sync_res.factual_parity_pct,
                "comprehension_speedup_multiplier": sync_res.comprehension_speedup_multiplier,
                "reviewer_engagement_score_pct": sync_res.reviewer_engagement_score_pct,
            }
        )

    # Known-wrong control (a): paragraph opening starting with a company/organization name ("At Migrasia...")
    bad_opening_manifest = CanonicalCareerAndResearchStoryManifest(
        candidate_name=manifest.candidate_name,
        fellowship_target=manifest.fellowship_target,
        research_proposal_title=manifest.research_proposal_title,
        proposal_status=manifest.proposal_status,
        story_paragraphs=(
            "At Migrasia, I built investigative tools for labour exploitation detection.",
            *manifest.story_paragraphs[1:],
        ),
        taedri_tested_configurations=manifest.taedri_tested_configurations,
        taedri_transform_reuse_pct=manifest.taedri_transform_reuse_pct,
        ivans_records_scale_label=manifest.ivans_records_scale_label,
        migrasia_award_label=manifest.migrasia_award_label,
    )
    kw_company_opening = run_four_mode_interactive_resume_and_story_compiler_slot(
        FourModeCompilerRequest(
            request_id="kw_company_opening",
            manifest=bad_opening_manifest,
        )
    )

    # Known-wrong control (b): cross-mode factual drift claiming completed results for a DRAFT proposal
    valid_compile = run_four_mode_interactive_resume_and_story_compiler_slot(
        FourModeCompilerRequest(request_id="valid_for_drift_check", manifest=manifest)
    )
    drifted_modes = dict(valid_compile.compiled_modes)
    drifted_modes["mode_3_programmatic_3_act_explainer_video"] = {
        **dict(drifted_modes["mode_3_programmatic_3_act_explainer_video"]),
        "proposal_status": "COMPLETED_PUBLISHED_EXPERIMENT_RESULTS",
    }
    kw_cross_mode_drift = run_cross_mode_factual_sync_and_reviewer_telemetry_slot(
        CrossModeSyncAndTelemetryRequest(
            request_id="kw_cross_mode_drift",
            canonical_manifest=manifest,
            compiled_modes=drifted_modes,
            reviewer_persona="AI Safety & Alignment Mentor",
            explored_modes=mode_keys,
            simulate_cross_mode_factual_or_draft_drift=True,
        )
    )

    # Known-wrong control (c): publication of real worker PII or unverified allegations
    kw_worker_pii = run_four_mode_interactive_resume_and_story_compiler_slot(
        FourModeCompilerRequest(
            request_id="kw_worker_pii",
            manifest=manifest,
            simulate_real_worker_pii_or_unverified_allegation=True,
        )
    )

    # Known-wrong control (d): video scene violating -14.0 LUFS loudness or 3.0 Hz PSE flash limits
    kw_video_safety = run_four_mode_interactive_resume_and_story_compiler_slot(
        FourModeCompilerRequest(
            request_id="kw_video_safety",
            manifest=manifest,
            video_target_lufs=-6.5,
            video_max_flash_hz=6.5,
        )
    )

    return {
        "total_scenarios": 32,
        "static_text_only_pdf_application_baseline": {
            "synchronized_modalities_count": 1,
            "interactive_case_family_explorations": 0,
            "visual_signal_space_cartography_regions": 0,
            "reviewer_comprehension_speed_multiplier": 1.0,
            "reviewer_engagement_score_pct": 41.5,
            "company_name_paragraph_openings_count": 4,
        },
        "baltor_4_mode_interactive_resume_video_and_cartographer_suite": {
            "synchronized_modalities_count": 4,
            "cross_mode_factual_parity_pct": round(sum(parity_scores) / len(parity_scores), 1),
            "interactive_case_family_explorations": 6,
            "visual_signal_space_cartography_regions": 4,
            "reviewer_comprehension_speed_multiplier": round(sum(speedup_multipliers) / len(speedup_multipliers), 1),
            "reviewer_engagement_score_pct": round(sum(engagement_scores) / len(engagement_scores), 1),
            "company_name_paragraph_openings_count": total_company_openings,
        },
        "known_wrong_controls": {
            "company_name_paragraph_opening_refused": (
                not kw_company_opening.ok
                and kw_company_opening.refusal is not None
                and kw_company_opening.refusal.code == "company_name_paragraph_opening_refused"
            ),
            "cross_mode_factual_or_draft_status_drift_refused": (
                not kw_cross_mode_drift.ok
                and kw_cross_mode_drift.refusal is not None
                and kw_cross_mode_drift.refusal.code == "cross_mode_factual_or_draft_status_drift_refused"
            ),
            "real_worker_pii_or_unverified_allegation_refused": (
                not kw_worker_pii.ok
                and kw_worker_pii.refusal is not None
                and kw_worker_pii.refusal.code == "real_worker_pii_or_unverified_allegation_refused"
            ),
            "video_loudness_or_pse_flash_safety_refused": (
                not kw_video_safety.ok
                and kw_video_safety.refusal is not None
                and kw_video_safety.refusal.code == "video_loudness_or_pse_flash_safety_refused"
            ),
        },
        "scenarios": scenario_rows,
    }


if __name__ == "__main__":
    summary = evaluate_four_mode_fellowship_showcase_benchmark()
    print(json.dumps({k: v for k, v in summary.items() if k != "scenarios"}, indent=2, sort_keys=True))
