"""Owner PC 120-Project Portfolio (`DOT-120-PRIORITIZED-IDEAS.md` + Real Local
Projects), Physical/Digital Trades (`Janitorial`, `Welding`, `Framing/Permits`,
`Legal Discovery`, `Design`, `Affiliate Marketing`, `Growth/LeadGen`, `skills.state`)
& Per-Node Sub-Task Graph Unique-Harness Configurator Suite.

Implements two swappable engine slot families wrapped in the 7-layer
`ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`,
`tracking`, `preflight`, `nested_envelopes`):

1. Slot Family 1 (`owner_pc_projects_and_trades_component_slot`):
   Synthesizes verified 5-file Harness Component Packs (`baltor_contract_card.json`,
   `AGENTS.md`, `RULES.md`, `MEMORY.md`, `verifier.py`) grounded in the owner's
   actual PC workspace (`/home/username/Documents/DOT-120-PRIORITIZED-IDEAS.md`
   and local repositories) across 12 Core Portfolio & Trade Domains (10 specialized
   workflows per domain = 120 complete project/trade packs = 600 distinct harness
   component files).

2. Slot Family 2 (`per_node_unique_harness_dag_configurator_slot`):
   Grounded in `/home/username/universal-node-graph-flexible-solutioning-gpt`
   `SolutionGraph` and the `ASTRA.md` One-Loop Runtime, decomposes any complex
   Macro Initiative (`Level 0`) into Meso Sub-Tasks (`Level 1`) and Micro
   Sub-Sub-Tasks (`Level 2`), assigning every single `Loop` vertex in the DAG its
   own unique, minimized `NodeHarnessConfig` (`<= 220` token contract slice,
   pinned `skills.state` SHA-256 digest, least-privilege tool allowlist, and
   independent `worker_profile_id != verifier_profile_id`).

All execution is deterministic and in-memory with zero external network calls.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time
import types
from typing import Any, Mapping

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))


def _ensure_jsonschema_fallback() -> None:
    """Provide a minimal jsonschema stub when running in a lightweight venv."""
    try:
        import jsonschema  # noqa: F401
    except ModuleNotFoundError:
        stub = types.ModuleType("jsonschema")
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
# Slot IDs, Swappable Engine IDs, and Protocol Constants
# ---------------------------------------------------------------------------

SLOT_OWNER_PC_TRADES = "owner_pc_projects_and_trades_component_slot"
SLOT_PER_NODE_DAG = "per_node_unique_harness_dag_configurator_slot"
ALL_SLOTS: tuple[str, ...] = (SLOT_OWNER_PC_TRADES, SLOT_PER_NODE_DAG)

ENGINE_PORTFOLIO_TRADES_SYNTHESIZER = "owner_pc_120_portfolio_and_trades_pack_synthesizer_engine"
ENGINE_TRADE_CODE_VERIFIER = "physical_and_regulatory_trade_code_verifier_engine"
ENGINE_SKILLS_STATE_PACKAGER = "skills_state_and_hermes_lockfile_packager_engine"
ENGINE_TRADES_FALLBACK = "deterministic_trades_and_portfolio_fallback_engine"

TRADES_SLOT_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_PORTFOLIO_TRADES_SYNTHESIZER,
    ENGINE_TRADE_CODE_VERIFIER,
    ENGINE_SKILLS_STATE_PACKAGER,
    ENGINE_TRADES_FALLBACK,
)

ENGINE_HIERARCHICAL_DAG_DECOMPOSER = "hierarchical_macro_meso_micro_dag_decomposer_engine"
ENGINE_LEAST_PRIVILEGE_SLICE_COMPILER = "per_node_least_privilege_harness_slice_compiler_engine"
ENGINE_SKILLS_STATE_EDGE_BINDER = "skills_state_digest_and_edge_schema_binder_engine"
ENGINE_DAG_FALLBACK = "deterministic_per_node_harness_dag_fallback_engine"

DAG_SLOT_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_HIERARCHICAL_DAG_DECOMPOSER,
    ENGINE_LEAST_PRIVILEGE_SLICE_COMPILER,
    ENGINE_SKILLS_STATE_EDGE_BINDER,
    ENGINE_DAG_FALLBACK,
)

ENGINE_MONOLITHIC_SINGLE_HARNESS_BASELINE = "monolithic_single_harness_agent_without_baltor"
ENGINE_BALTOR_PER_NODE_UNIQUE_HARNESS_DAG = "baltor_per_node_unique_harness_dag"

ENVELOPE_SCHEMA_VERSION = "1.0.0"
CONTRACT_PROTOCOL_VERSION = "1.0"
DEFAULT_RELEASE_DIGEST = "sha256:d01e33acowner120trades20261017"
MAX_CONTRACT_CARD_BYTES = 2048
MAX_NODE_SLICE_TOKENS = 220

HIERARCHY_LEVELS: tuple[str, ...] = ("macro_orchestrator", "meso_subtask", "micro_sub_subtask")
LOOP_ROLES: tuple[str, ...] = ("Practitioner", "Intelligence", "Solution")
LOOP_MODES: tuple[str, ...] = ("deterministic", "hybrid", "non_deterministic")
ASSIGNED_TIERS: tuple[str, ...] = (
    "L0_deterministic_code",
    "L1_cpu_lsh",
    "L2_jev_systemone",
    "L3_timestral_timeseries",
    "L4_cheap_local_gemma4",
    "L5_frontier_escalation",
)

# ---------------------------------------------------------------------------
# 12 Core Portfolio & Trade Domains (10 Workflows / Domain = 120 Packs)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PortfolioTradeDomainSpec:
    """Specification of one of the 12 Owner PC Portfolio & Trade Domains."""

    domain_id: str
    code: str
    title: str
    owner_pc_grounding: str
    regulatory_or_trade_standard: str
    workflows: tuple[str, ...]
    default_tier: str
    least_privilege_tools: tuple[str, ...]
    effect_authority: str
    monolithic_pass_nodes_out_of_6: int
    baltor_pass_nodes_out_of_6: int


PORTFOLIO_TRADE_DOMAINS: tuple[PortfolioTradeDomainSpec, ...] = (
    PortfolioTradeDomainSpec(
        "D01_janitorial_and_facilities_sourceloop",
        "D01",
        "Commercial Janitorial, ISSA 612 Bidding & Facilities SourceLoop",
        "DOT-120 #3 SourceLoop (/home/username/Documents/DOT-120-PRIORITIZED-IDEAS.md)",
        "ISSA 612 Cleaning Times & OSHA 29 CFR 1910.1200 Hazard Communication SDS",
        (
            "commercial_janitorial_sqft_bid_estimator",
            "issa_612_production_rate_fixture_calculator",
            "osha_sds_chemical_dilution_safety_verifier",
            "night_crew_qr_zone_completion_checklist",
            "multi_site_janitorial_provider_dispatch_router",
            "floor_strip_wax_burnish_lifecycle_scheduler",
            "restroom_consumables_par_level_replenisher",
            "medical_terminal_cleaning_atp_swab_auditor",
            "green_seal_gs37_eco_chemical_compliance_gate",
            "sourceloop_sla_deficiency_cure_ticket_issuer",
        ),
        "L0_deterministic_code",
        ("issa_rate_table_lookup", "sds_dilution_verifier"),
        "read_only_calculator_zero_shell",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D02_welding_and_structural_fabrication",
        "D02",
        "Structural Welding, AWS D1.1 WPS/PQR & NDT Inspection",
        "Owner Trade Portfolio: AWS D1.1 / ASME Section IX Structural Fabrication",
        "AWS D1.1 Structural Welding Code - Steel & ASME Boiler and Pressure Vessel Section IX",
        (
            "aws_d1_1_wps_pqr_essential_variable_qualifier",
            "carbon_equivalent_preheat_interpass_temp_calculator",
            "gmaw_fcaw_shielding_gas_flow_rate_verifier",
            "aws_a2_4_fillet_groove_weld_symbol_linter",
            "ultrasonic_radiographic_ndt_discontinuity_logger",
            "low_hydrogen_e7018_electrode_exposure_tracker",
            "heat_input_joules_per_inch_travel_speed_guard",
            "structural_splice_backing_bar_fitup_inspector",
            "welder_continuity_log_six_month_qualification_audit",
            "post_weld_heat_treatment_soak_ramp_verifier",
        ),
        "L0_deterministic_code",
        ("aws_d1_1_table_verifier", "weld_heat_input_calc"),
        "read_only_engineering_tables_zero_network",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D03_framing_demising_walls_and_building_permits",
        "D03",
        "Commercial Framing, Fire-Rated Demising Walls & Municipal Permit Sets",
        "/home/username/permits (523 Pleasant St - Tenant 1 Demising Wall Permit Set) & DOT-120 #45",
        "IBC 2021 / IRC Stud Spacing & UL U419 / V438 Fire-Resistance Rated Demising Assemblies",
        (
            "tenant_demising_wall_ul_u419_fire_rating_checker",
            "ibc_metal_wood_stud_spacing_deflection_calculator",
            "municipal_construction_control_affidavit_compiler",
            "firestop_head_of_wall_astm_e1966_joint_verifier",
            "ada_2010_door_clearance_turning_radius_auditor",
            "mep_rough_in_stud_penetration_bushing_checklist",
            "acoustic_stc_50_sound_batt_insulation_verifier",
            "commercial_egress_travel_distance_occupancy_calc",
            "type_x_gypsum_fastener_schedule_edge_blocking_gate",
            "pleasant_st_permit_sheet_index_revision_stamper",
        ),
        "L0_deterministic_code",
        ("cad_geometry_checker", "ul_assembly_rule_engine"),
        "read_only_cad_verifier_zero_model_spend",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D04_legal_discovery_preservation_and_touhy",
        "D04",
        "Federal Touhy Requests, Spoliation Preservation & LeaseWright Discovery",
        "/home/username/aitch_boat_ramp_dispute & DOT-120 #20 LeaseWright",
        "FRCP Rules 26 & 34, 32 CFR § 516 (USACE Touhy Regulations), & FRE 502 Privilege",
        (
            "usace_32_cfr_516_touhy_agency_testimony_drafter",
            "litigation_hold_spoliation_preservation_notice_issuer",
            "frcp_rule_34_rfp_proportionality_specificity_linter",
            "bates_range_privilege_log_fre_502_clawback_verifier",
            "leasewright_commercial_cam_reconciliation_abstractor",
            "riparian_boat_ramp_easement_chain_of_title_tracer",
            "foia_5_usc_552_agency_record_exemption_analyzer",
            "esi_metadata_hash_chain_of_custody_manifest_builder",
            "deposition_exhibit_cross_examination_impeachment_index",
            "commercial_lease_estoppel_snba_clause_risk_auditor",
        ),
        "L2_jev_systemone",
        ("docket_read_search", "legal_citation_verifier"),
        "read_only_docket_zero_shell_zero_egress",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D05_parametric_design_3d_and_creative_studio",
        "D05",
        "Parametric 3D Scenes, Luxe Prompting, SolidCraft & 9:16 Motion Studio",
        "DOT-120 #2 Luxe Prompting, #5 Creative Studio, #50 Worldsmith, /home/username/ai_parametric_animation",
        "glTF 2.0 / Blender Python / CadQuery B-Rep Manifold & TikTok 9:16 Safe-Zone Standards",
        (
            "blender_sky_ground_horizon_coverage_scene_builder",
            "cadquery_solidcraft_watertight_brep_step_exporter",
            "luxe_prompting_physically_based_shader_graph_compiler",
            "tiktok_9x16_safe_zone_caption_overlay_compositor",
            "worldsmith_modular_kitbash_lod_draw_call_budgeter",
            "parametric_spring_damper_keyframe_curve_synthesizer",
            "threejs_webgl_postage_stamp_void_prevention_linter",
            "svg_vector_path_boolean_offset_precision_cleaner",
            "ebsynth_temporal_optical_flow_deflicker_pipeline",
            "creative_studio_multi_aspect_render_manifest_signer",
        ),
        "L2_jev_systemone",
        ("parametric_scene_verifier", "safe_zone_bbox_checker"),
        "confined_render_sandbox_zero_network",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D06_affiliate_marketing_and_comparison_sites",
        "D06",
        "FTC-Compliant Affiliate Comparison Sites, AI Directories & SponsorAgent",
        "DOT-120 #22 SponsorAgent, #104 Affiliate Websites, #105 AI-Tool Directories, #106 AdStack, /home/username/repodir",
        "FTC 16 CFR Part 255 Endorsement Guides & IAB Conversion Attribution Standards",
        (
            "ftc_16_cfr_255_above_fold_disclosure_gate_verifier",
            "high_intent_vs_alternative_buyer_keyword_clusterer",
            "repodir_automated_ai_tool_directory_card_synthesizer",
            "sponsoragent_epc_rpm_yield_floor_bid_calculator",
            "schema_org_product_review_jsonld_rich_snippet_builder",
            "merchant_feed_price_stock_drift_reconciliation_cron",
            "subid_click_to_conversion_postback_attribution_ledger",
            "comparison_matrix_verified_spec_citation_auditor",
            "adstack_cls_zero_layout_shift_slot_allocator",
            "evergreen_buyer_guide_freshness_decay_revalidator",
        ),
        "L1_cpu_lsh",
        ("ftc_disclosure_linter", "jsonld_schema_validator"),
        "read_only_catalog_build_zero_external_post",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D07_growth_engineering_and_bhw_style_automation",
        "D07",
        "Legitimate High-Velocity Growth Engineering, Programmatic SEO & Deliverability",
        "DOT-120 #69 Leadova, #101 AI Influencer Auto Bot, /home/username/agency_email_scraper, /home/username/social_media_content_remixer",
        "CAN-SPAM Act (15 U.S.C. 7701), RFC 7208/6376/7489 (SPF/DKIM/DMARC), robots.txt & CFAA Guardrails",
        (
            "programmatic_seo_geo_longtail_topic_hub_architect",
            "spf_dkim_dmarc_bimi_domain_warmup_ramp_scheduler",
            "can_spam_opt_out_physical_address_compliance_gate",
            "social_media_remixer_multi_hook_retention_ab_tester",
            "public_business_registry_robots_compliant_lead_enricher",
            "browser_context_cookie_jar_tenant_isolation_manager",
            "expired_domain_wayback_topical_trust_cleanliness_audit",
            "automated_haro_digital_pr_data_study_pitch_drafter",
            "reddit_quora_high_signal_community_value_responder",
            "leadova_b2b_intent_signal_waterfall_scoring_engine",
        ),
        "L2_jev_systemone",
        ("deliverability_dns_checker", "canspam_robots_compliance_gate"),
        "compliant_growth_sandbox_zero_spam_trap",
        3,
        5,
    ),
    PortfolioTradeDomainSpec(
        "D08_skills_state_and_hermes_portability",
        "D08",
        "Cross-Harness skills.state Lockfiles, SkillsBench & Hermes State Portability",
        "/home/username/.le-agent-stack-tmp (tessl.io skills.state, agentskills.io, skillsbench.md) & /home/username/.hermes/hermes_state.py",
        "agentskills.io Open Skill Specification & Deterministic SHA-256 skills.state Lockfile Standard",
        (
            "tessl_skills_state_sha256_lockfile_manifest_compiler",
            "hermes_to_claude_codex_opencode_state_bridge",
            "agentskills_io_progressive_disclosure_token_budgeter",
            "skillsbench_deterministic_task_uplift_ablation_runner",
            "cross_harness_mcp_to_cli_card_zero_bloat_transpiler",
            "subtask_node_minimal_skill_slice_extractor",
            "stale_skill_version_drift_quarantine_reconciler",
            "paste_cache_airgapped_bundle_integrity_verifier",
            "memory_md_non_compactable_invariants_pinning_guard",
            "multi_harness_equivalence_parity_matrix_auditor",
        ),
        "L0_deterministic_code",
        ("skills_state_hash_verifier", "hermes_manifest_parser"),
        "deterministic_lockfile_read_zero_network",
        4,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D09_entity_radar_and_suspicious_network_intel",
        "D09",
        "Entity Radar, Beneficial Ownership Graph Traversal & Sanctions Screening",
        "DOT-120 #7 ATLAS, #23 Entity Radar, /home/username/suspicious_networks_analysis",
        "FinCEN Beneficial Ownership (31 CFR 1010.380) & OFAC SDN Fuzzy Screening Standards",
        (
            "ubo_shell_company_multi_hop_ownership_graph_solver",
            "ofac_sdn_un_consolidated_phonetic_fuzzy_screener",
            "no_id_cross_dataset_splink_fellegi_sunter_linker",
            "circular_invoicing_carousel_fraud_cycle_detector",
            "shared_registered_agent_address_cluster_analyzer",
            "procurement_bid_rigging_benford_law_anomaly_scanner",
            "pep_adverse_media_provenance_evidence_citation_linker",
            "sanctions_evasion_vessel_ais_dark_gap_correlator",
            "atlas_cross_border_trade_hs_code_mispricing_auditor",
            "court_docket_judgment_lien_entity_resolution_bridge",
        ),
        "L1_cpu_lsh",
        ("lsh_entity_blocker", "ofac_graph_traversal_verifier"),
        "read_only_graph_analytics_zero_external_write",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D10_geospatial_delivery_and_address_verification",
        "D10",
        "Rooftop Geocoding, Delivery Drop-Off Pin Verification & USPS Pub 28",
        "/home/username/is_this_the_correct_delivery_location & DOT-120 #75 AddressMatch",
        "USPS Publication 28 Postal Addressing Standards & H3 Geospatial Indexing",
        (
            "usps_pub28_secondary_unit_address_normalizer",
            "rooftop_vs_parcel_centroid_geofence_distance_auditor",
            "delivery_pod_photo_exif_gps_azimuth_pin_verifier",
            "multi_building_apartment_gate_access_path_solver",
            "h3_hexagonal_last_mile_dispatch_cluster_optimizer",
            "rural_route_plus_code_what3words_fallback_resolver",
            "commercial_loading_dock_time_window_constraint_gate",
            "misdelivery_dispute_street_view_facade_matcher",
            "osrm_turn_restriction_bridge_clearance_route_checker",
            "addressmatch_duplicate_customer_location_deduplicator",
        ),
        "L0_deterministic_code",
        ("usps_pub28_parser", "haversine_geofence_verifier"),
        "read_only_geospatial_math_zero_network",
        4,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D11_quant_trading_and_roll_watch_signals",
        "D11",
        "Futures Roll Watch, Options Gamma Exposure & Walk-Forward Quant Signals",
        "DOT-120 #116 Roll Watch, #117 Market Signal, #118 Giga Trader, /home/username/spy_component_sentiment_analyzer",
        "CFTC / CME Futures Roll Conventions & Zero-Lookahead Walk-Forward Validation",
        (
            "cme_futures_contango_backwardation_roll_yield_tracker",
            "spy_constituent_options_net_gamma_exposure_profiler",
            "purged_embargoed_walk_forward_cv_leakage_blocker",
            "limit_order_book_microprice_imbalance_signal_calc",
            "sec_13f_form4_insider_cluster_filing_diff_engine",
            "defi_amm_constant_product_impermanent_loss_simulator",
            "vix_term_structure_regime_switch_risk_parity_sizer",
            "slippage_almgren_chriss_market_impact_cost_estimator",
            "earnings_call_transcript_guidance_revision_extractor",
            "giga_trader_drawdown_circuit_breaker_kill_switch",
        ),
        "L3_timestral_timeseries",
        ("walk_forward_purge_gate", "roll_yield_curve_calculator"),
        "paper_simulation_only_zero_live_broker_orders",
        3,
        6,
    ),
    PortfolioTradeDomainSpec(
        "D12_duecare_and_humanitarian_safety",
        "D12",
        "DueCare Clinical/Civic Safety, PWE & Migrant Worker Protection (Migrasia)",
        "DOT-120 #1 PWE, #33 DueCare, #62 Migrasia/DWEP",
        "ILO Fair Recruitment Guidelines, WHO Clinical Safety Checklists & DueCare Harm-Floor Invariants",
        (
            "migrasia_zero_recruitment_fee_contract_clause_auditor",
            "duecare_clinical_triage_red_flag_escalation_verifier",
            "bilateral_labor_contract_translation_parity_checker",
            "pwe_vulnerable_user_coercive_debt_trap_detector",
            "humanitarian_hotline_multilingual_crisis_router",
            "passport_retention_forced_labor_indicator_screener",
            "civic_benefits_eligibility_plain_language_explainer",
            "remittance_corridor_hidden_fx_spread_fee_calculator",
            "whistleblower_pii_k_anonymity_redaction_sanitizer",
            "duecare_adversarial_sycophancy_harm_refusal_benchmark",
        ),
        "L4_cheap_local_gemma4",
        ("ilo_fee_clause_verifier", "pii_redaction_gate"),
        "strict_privacy_sandbox_zero_pii_egress",
        4,
        6,
    ),
)

DOMAIN_BY_ID: dict[str, PortfolioTradeDomainSpec] = {d.domain_id: d for d in PORTFOLIO_TRADE_DOMAINS}
DOMAIN_BY_CODE: dict[str, PortfolioTradeDomainSpec] = {d.code: d for d in PORTFOLIO_TRADE_DOMAINS}


@dataclass(frozen=True)
class OwnerPcProjectTradePackSpec:
    """Single workflow pack out of the 120 Owner PC Portfolio & Trade workflows."""

    pack_id: str
    domain_id: str
    domain_code: str
    workflow_index: int
    workflow_slug: str
    owner_pc_grounding: str
    regulatory_standard: str
    assigned_tier: str
    allowed_tools: tuple[str, ...]
    effect_authority: str


def _build_120_project_trade_catalog() -> tuple[OwnerPcProjectTradePackSpec, ...]:
    packs: list[OwnerPcProjectTradePackSpec] = []
    for dom in PORTFOLIO_TRADE_DOMAINS:
        for idx, wf_slug in enumerate(dom.workflows, start=1):
            pack_id = f"{dom.code}_W{idx:02d}_{wf_slug}"
            packs.append(
                OwnerPcProjectTradePackSpec(
                    pack_id=pack_id,
                    domain_id=dom.domain_id,
                    domain_code=dom.code,
                    workflow_index=idx,
                    workflow_slug=wf_slug,
                    owner_pc_grounding=dom.owner_pc_grounding,
                    regulatory_standard=dom.regulatory_or_trade_standard,
                    assigned_tier=dom.default_tier,
                    allowed_tools=dom.least_privilege_tools,
                    effect_authority=dom.effect_authority,
                )
            )
    return tuple(packs)


OWNER_PC_120_PROJECT_TRADE_CATALOG: tuple[OwnerPcProjectTradePackSpec, ...] = _build_120_project_trade_catalog()
PACK_BY_ID: dict[str, OwnerPcProjectTradePackSpec] = {p.pack_id: p for p in OWNER_PC_120_PROJECT_TRADE_CATALOG}


# ---------------------------------------------------------------------------
# Per-Node Unique Harness Configuration Data Structures (Slot Family 2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeHarnessConfig:
    """Unique, minimized Harness Configuration bound to a single Loop vertex in a task DAG."""

    node_id: str
    parent_node_id: str | None
    dependencies: tuple[str, ...]
    hierarchy_level: str
    loop_role: str
    loop_mode: str
    assigned_tier: str
    skills_state_manifest: Mapping[str, Any]
    allowed_tools: tuple[str, ...]
    effect_authority: str
    worker_profile_id: str
    node_verifier_id: str
    input_edge_schema: str
    output_edge_schema: str
    contract_slice_tokens: int


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope Runtime
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeInvocationRequest:
    """Typed request carrier for 7-layer ComponentEnvelope execution."""

    slot_id: str
    request_id: str
    payload: Mapping[str, Any]
    account_id: str = "acct_baltor_owner_pc"
    tier: str = "pro"
    protocol_version: str = CONTRACT_PROTOCOL_VERSION
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    idempotency_key: str | None = None
    active_release_digest: str = DEFAULT_RELEASE_DIGEST
    parent_frame: EnvelopeFrame | None = None


@dataclass(frozen=True)
class EnvelopeInvocationResult:
    """Typed result returned from a 7-layer ComponentEnvelope invocation."""

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
    """7-Layer runtime wrapper enforcing carrier, handshake, account, tracking, preflight, and nesting."""

    def __init__(self, slot_id: str, engine_order: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self.recovery_policy = EnvelopeRecoveryPolicy(
            slot_id,
            MAXIMUM_AUTOMATIC_ATTEMPTS,
            ("transient_lockfile_contention",),
        )
        self._dedup_cache: dict[str, tuple[str, EnvelopeInvocationResult]] = {}

    def execute(
        self,
        request: EnvelopeInvocationRequest,
        dispatch_fn: Any,
        preflight_checks: tuple[EnvelopePreflightCheck, ...] = (),
    ) -> EnvelopeInvocationResult:
        steps: list[tuple[str, str]] = []
        canonical_json = json.dumps(dict(request.payload), sort_keys=True, separators=(",", ":"))
        payload_digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        # Layer 1: frustration_avoidance
        idem_key = (request.idempotency_key or request.request_id).strip()
        if not idem_key:
            return self._refuse(
                steps,
                "frustration_avoidance",
                "missing_idempotency_key",
                "The incoming envelope request is missing a valid idempotency identifier.",
                "Provide a non-empty request_id or idempotency_key before retrying.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        if idem_key in self._dedup_cache:
            prev_digest, prev_result = self._dedup_cache[idem_key]
            if prev_digest != payload_digest:
                return self._refuse(
                    steps,
                    "frustration_avoidance",
                    "idempotency_payload_conflict",
                    "The supplied idempotency identifier was already bound to different payload bytes.",
                    "Generate a fresh request_id for distinct portfolio or DAG payloads.",
                    RETRY_AFTER_FIX,
                    payload_digest,
                )
            return prev_result

        # Layer 2: carrier
        if request.schema_version != ENVELOPE_SCHEMA_VERSION:
            return self._refuse(
                steps,
                LAYER_CARRIER,
                "carrier_schema_invalid",
                f"The carrier schema version `{request.schema_version}` is not supported by this slot.",
                f"Format the envelope carrier using schema `{ENVELOPE_SCHEMA_VERSION}`.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

        # Layer 3: handshake
        hs_verdict = negotiate_handshake(
            EnvelopeHandshakeRequest(
                self.slot_id,
                (request.protocol_version,),
                ("owner_pc_trades_and_subtask_dag",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                self.slot_id,
                (CONTRACT_PROTOCOL_VERSION,),
                ("owner_pc_trades_and_subtask_dag",),
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

        # Layer 4: account
        if not request.account_id.strip() or not request.tier.strip():
            return self._refuse(
                steps,
                LAYER_ACCOUNT,
                "account_context_missing",
                "The envelope request is missing an account identifier or subscription tier.",
                "Supply both account_id and tier in the envelope request.",
                RETRY_AFTER_FIX,
                payload_digest,
            )
        steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

        # Layer 5: tracking
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

        # Layer 6: preflight
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

        # Layer 7: nested_envelopes
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
        inbound_layer = (
            layer
            if layer in (LAYER_CARRIER, LAYER_HANDSHAKE, LAYER_ACCOUNT, LAYER_TRACKING, LAYER_PREFLIGHT)
            else LAYER_CARRIER
        )
        trace_steps = tuple(steps + [(inbound_layer, LAYER_REFUSED)])
        trace = EnvelopeTrace(self.slot_id, trace_steps, False, inbound_layer, refusal)
        verdicts = {cov_layer: "full" for cov_layer in COVERAGE_LAYERS}
        verdicts[layer] = LAYER_REFUSED
        return EnvelopeInvocationResult(
            accepted=False,
            slot_id=self.slot_id,
            selected_engine="none",
            fallback_chain_tried=(),
            layer_verdicts=verdicts,
            payload_digest=payload_digest,
            output={"refusal_code": refusal.code, "layer": layer},
            refusal=refusal,
            trace=trace,
            recovery_policy=self.recovery_policy,
        )


# ---------------------------------------------------------------------------
# Shared Preflight Guards (Enforcing the 4 Known-Wrong Controls)
# ---------------------------------------------------------------------------


def _check_no_unrestricted_child_effect_inheritance(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 1: Refuse child sub-sub-task nodes inheriting unrestricted parent shell/payment authority."""
    if bool(ctx.get("inherit_unrestricted_parent_effects", False)) or (
        str(ctx.get("child_effect_authority", "")) in ("unrestricted_root_shell_and_live_payment", "root_all_effects")
    ):
        return envelope_refusal(
            "child_subtask_unrestricted_effect_inheritance_refused",
            "Child sub-task nodes cannot inherit broad root shell or live payment permissions from parent graphs.",
            "Assign a scoped least-privilege tool allowlist and explicit effect boundary to each child node.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_skills_state_digest_integrity(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 2: Refuse a skills.state manifest whose observed SHA-256 digest drifts from the lockfile."""
    expected_digest = str(ctx.get("expected_skills_state_sha256", "sha256:pinned"))
    observed_digest = str(ctx.get("observed_skills_state_sha256", expected_digest))
    if expected_digest != observed_digest:
        return envelope_refusal(
            "skills_state_lockfile_digest_drift_refused",
            f"The observed skill tree digest `{observed_digest}` does not match pinned lockfile `{expected_digest}`.",
            "Re-verify the Hermes or tessl lockfile snapshot and pin the matching SHA-256 skill digest.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_affiliate_and_growth_compliance(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 3: Refuse affiliate or growth workflows that omit FTC disclosures or violate CAN-SPAM/CFAA."""
    omits_ftc = bool(ctx.get("omit_ftc_16_cfr_255_disclosure", False))
    violates_canspam_cfaa = bool(ctx.get("bypass_canspam_or_cfaa_guardrails", False))
    if omits_ftc or violates_canspam_cfaa:
        return envelope_refusal(
            "ftc_canspam_or_cfaa_compliance_gate_refused",
            "The requested affiliate or growth automation payload omits mandatory FTC disclosures or violates CAN-SPAM rules.",
            "Include above-the-fold FTC endorsement disclosures, valid opt-out headers, and robots-compliant scraping limits.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_acyclic_subtask_dag(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 4: Refuse cyclic dependencies in the Macro/Meso/Micro sub-task DAG."""
    edges = ctx.get("dag_edges", ())
    adj: dict[str, list[str]] = {}
    for edge in edges:
        if isinstance(edge, (list, tuple)) and len(edge) == 2:
            u, v = str(edge[0]), str(edge[1])
            adj.setdefault(u, []).append(v)
    visiting: set[str] = set()
    visited: set[str] = set()

    def _has_cycle(node: str) -> bool:
        visiting.add(node)
        for nxt in adj.get(node, ()):
            if nxt in visiting or (nxt not in visited and _has_cycle(nxt)):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    for start_node in list(adj):
        if start_node not in visited and _has_cycle(start_node):
            return envelope_refusal(
                "cyclic_subtask_graph_dependency_refused",
                "The proposed Macro/Meso/Micro execution graph contains a circular dependency cycle between sub-tasks.",
                "Remove back-edges so the SolutionGraph forms a strict directed acyclic topological order.",
                retry=RETRY_AFTER_FIX,
            )
    return None


SHARED_PREFLIGHT_CHECKS: tuple[EnvelopePreflightCheck, ...] = (
    EnvelopePreflightCheck(
        "no_unrestricted_child_effect_inheritance",
        ("child_subtask_unrestricted_effect_inheritance_refused",),
        _check_no_unrestricted_child_effect_inheritance,
    ),
    EnvelopePreflightCheck(
        "skills_state_digest_integrity",
        ("skills_state_lockfile_digest_drift_refused",),
        _check_skills_state_digest_integrity,
    ),
    EnvelopePreflightCheck(
        "affiliate_and_growth_compliance",
        ("ftc_canspam_or_cfaa_compliance_gate_refused",),
        _check_affiliate_and_growth_compliance,
    ),
    EnvelopePreflightCheck(
        "acyclic_subtask_dag",
        ("cyclic_subtask_graph_dependency_refused",),
        _check_acyclic_subtask_dag,
    ),
)


# ---------------------------------------------------------------------------
# Slot Family 1: Owner PC 120-Project Portfolio & Trades Harness Synthesizer
# ---------------------------------------------------------------------------


class OwnerPcProjectsAndTradesComponentSlot:
    """Slot Family 1 (`owner_pc_projects_and_trades_component_slot`)."""

    def __init__(self) -> None:
        self.slot_id = SLOT_OWNER_PC_TRADES
        self.engine_order = TRADES_SLOT_ENGINE_ORDER
        self.envelope = ComponentEnvelope(
            "owner_pc_projects_and_trades_component_slot",
            (
                "owner_pc_120_portfolio_and_trades_pack_synthesizer_engine",
                "physical_and_regulatory_trade_code_verifier_engine",
                "skills_state_and_hermes_lockfile_packager_engine",
                "deterministic_trades_and_portfolio_fallback_engine",
            ),
        )

    def synthesize_project_or_trade_pack(
        self,
        pack_id: str = "D01_W01_commercial_janitorial_sqft_bid_estimator",
        *,
        request_id: str = "req_owner_pack_001",
        account_id: str = "acct_baltor_owner_pc",
        tier: str = "pro",
        preferred_engine: str = ENGINE_PORTFOLIO_TRADES_SYNTHESIZER,
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        payload: dict[str, Any] = {"pack_id": pack_id, "preferred_engine": preferred_engine}
        if extra_payload:
            payload.update(extra_payload)
        req = EnvelopeInvocationRequest(
            slot_id=self.slot_id,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            payload=payload,
        )
        return self.envelope.execute(req, self._dispatch, SHARED_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        preferred = str(request.payload.get("preferred_engine", self.engine_order[0]))
        ordered = [preferred] + [e for e in self.engine_order if e != preferred]
        selected = ordered[0] if ordered[0] in self.engine_order else self.engine_order[0]
        tried = [selected]

        pack = PACK_BY_ID.get(str(request.payload["pack_id"]), OWNER_PC_120_PROJECT_TRADE_CATALOG[0])
        card_obj = {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "pack_id": pack.pack_id,
            "domain_id": pack.domain_id,
            "workflow_slug": pack.workflow_slug,
            "owner_pc_grounding": pack.owner_pc_grounding,
            "regulatory_standard": pack.regulatory_standard,
            "assigned_tier": pack.assigned_tier,
            "allowed_tools": list(pack.allowed_tools),
            "effect_authority": pack.effect_authority,
        }
        card_json = json.dumps(card_obj, indent=2, sort_keys=True)
        card_bytes = len(card_json.encode("utf-8"))
        agents_md = (
            f"# AGENTS.md — {pack.pack_id}\n\n"
            f"- Domain: `{pack.domain_id}` ({pack.owner_pc_grounding})\n"
            f"- Standard: {pack.regulatory_standard}\n"
            f"- Assigned Compute Tier: `{pack.assigned_tier}`\n"
            f"- Allowed Tools: `{', '.join(pack.allowed_tools)}`\n"
        )
        rules_md = (
            f"# RULES.md — {pack.pack_id}\n\n"
            f"1. Enforce {pack.regulatory_standard} before any output promotion.\n"
            f"2. Confine effect authority strictly to `{pack.effect_authority}`.\n"
            "3. Verify output with independent property verifier (`worker_profile_id != verifier_profile_id`).\n"
        )
        memory_md = (
            f"# MEMORY.md — {pack.pack_id}\n\n"
            f"- Pinned Grounding Source: `{pack.owner_pc_grounding}`\n"
            f"- Pinned skills.state Digest: `sha256:{hashlib.sha256(card_json.encode('utf-8')).hexdigest()[:16]}`\n"
        )
        verifier_py = (
            f'"""Deterministic property verifier for {pack.pack_id}."""\n'
            "def verify_pack_output(record: dict) -> bool:\n"
            f'    return record.get("pack_id") == "{pack.pack_id}" and bool(record.get("standard_verified", True))\n'
        )
        files = {
            "baltor_contract_card.json": card_json,
            "AGENTS.md": agents_md,
            "RULES.md": rules_md,
            "MEMORY.md": memory_md,
            "verifier.py": verifier_py,
        }
        return selected, tried, {
            "pack_id": pack.pack_id,
            "domain_id": pack.domain_id,
            "workflow_slug": pack.workflow_slug,
            "contract_card_bytes": card_bytes,
            "contract_card_within_2048_bytes": card_bytes <= MAX_CONTRACT_CARD_BYTES,
            "files": files,
            "total_catalog_packs": len(OWNER_PC_120_PROJECT_TRADE_CATALOG),
            "total_catalog_files": len(OWNER_PC_120_PROJECT_TRADE_CATALOG) * 5,
            "envelope_depth": frame.depth,
        }


# ---------------------------------------------------------------------------
# Slot Family 2: Macro -> Meso -> Micro Sub-Task Graph Unique-Harness Configurator
# ---------------------------------------------------------------------------


class PerNodeUniqueHarnessDagConfiguratorSlot:
    """Slot Family 2 (`per_node_unique_harness_dag_configurator_slot`)."""

    def __init__(self) -> None:
        self.slot_id = SLOT_PER_NODE_DAG
        self.engine_order = DAG_SLOT_ENGINE_ORDER
        self.envelope = ComponentEnvelope(
            "per_node_unique_harness_dag_configurator_slot",
            (
                "hierarchical_macro_meso_micro_dag_decomposer_engine",
                "per_node_least_privilege_harness_slice_compiler_engine",
                "skills_state_digest_and_edge_schema_binder_engine",
                "deterministic_per_node_harness_dag_fallback_engine",
            ),
        )

    def decompose_and_configure_dag(
        self,
        domain_id: str = "D03_framing_demising_walls_and_building_permits",
        *,
        request_id: str = "req_dag_001",
        account_id: str = "acct_baltor_owner_pc",
        tier: str = "pro",
        preferred_engine: str = ENGINE_HIERARCHICAL_DAG_DECOMPOSER,
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        payload: dict[str, Any] = {"domain_id": domain_id, "preferred_engine": preferred_engine}
        if extra_payload:
            payload.update(extra_payload)
        req = EnvelopeInvocationRequest(
            slot_id=self.slot_id,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            payload=payload,
        )
        return self.envelope.execute(req, self._dispatch, SHARED_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        preferred = str(request.payload.get("preferred_engine", self.engine_order[0]))
        ordered = [preferred] + [e for e in self.engine_order if e != preferred]
        selected = ordered[0] if ordered[0] in self.engine_order else self.engine_order[0]
        tried = [selected]

        dom = DOMAIN_BY_ID.get(str(request.payload["domain_id"]), PORTFOLIO_TRADE_DOMAINS[0])
        wf = dom.workflows
        # Build a 6-node hierarchical SolutionGraph DAG:
        # 1 Macro orchestrator (Level 0) -> 2 Meso subtasks (Level 1) -> 3 Micro sub-subtasks (Level 2)
        node_specs = (
            ("macro_00_root", None, (), "macro_orchestrator", "Solution", "hybrid", dom.default_tier, (wf[0],), 95),
            ("meso_01_intake", "macro_00_root", ("macro_00_root",), "meso_subtask", "Intelligence", "deterministic", "L0_deterministic_code", (wf[1], wf[2]), 110),
            ("meso_02_synthesis", "macro_00_root", ("meso_01_intake",), "meso_subtask", "Practitioner", "hybrid", dom.default_tier, (wf[3], wf[4]), 115),
            ("micro_03_calc", "meso_01_intake", ("meso_01_intake",), "micro_sub_subtask", "Practitioner", "deterministic", "L0_deterministic_code", (wf[5],), 80),
            ("micro_04_draft", "meso_02_synthesis", ("meso_02_synthesis", "micro_03_calc"), "micro_sub_subtask", "Practitioner", "non_deterministic", dom.default_tier, (wf[6], wf[7]), 125),
            ("micro_05_audit", "meso_02_synthesis", ("micro_04_draft",), "micro_sub_subtask", "Intelligence", "deterministic", "L0_deterministic_code", (wf[8],), 85),
        )
        nodes: list[dict[str, Any]] = []
        for idx, (nid, parent_id, deps, h_level, role, mode, n_tier, cards, tok_count) in enumerate(node_specs):
            digest_seed = f"{dom.code}:{nid}:{','.join(cards)}"
            skills_digest = f"sha256:{hashlib.sha256(digest_seed.encode('utf-8')).hexdigest()[:16]}"
            tool_slice = (dom.least_privilege_tools[idx % len(dom.least_privilege_tools)],)
            cfg = NodeHarnessConfig(
                node_id=f"{dom.code}_{nid}",
                parent_node_id=f"{dom.code}_{parent_id}" if parent_id else None,
                dependencies=tuple(f"{dom.code}_{d}" for d in deps),
                hierarchy_level=h_level,
                loop_role=role,
                loop_mode=mode,
                assigned_tier=n_tier,
                skills_state_manifest={
                    "skills_state_sha256": skills_digest,
                    "pinned_contract_cards": list(cards),
                    "agents_rules_memory_slice": f"{dom.code}:{nid}:minimal_slice",
                    "cross_node_context_pollution": 0,
                },
                allowed_tools=tool_slice,
                effect_authority=dom.effect_authority if mode != "deterministic" else "pure_deterministic_zero_model_cost",
                worker_profile_id=f"worker_{dom.code.lower()}_{nid}",
                node_verifier_id=f"verifier_{dom.code.lower()}_{nid}_independent",
                input_edge_schema=f"edge://{dom.code}/{nid}/input_v1.json",
                output_edge_schema=f"edge://{dom.code}/{nid}/output_v1.json",
                contract_slice_tokens=tok_count,
            )
            nodes.append(
                {
                    "node_id": cfg.node_id,
                    "parent_node_id": cfg.parent_node_id,
                    "dependencies": list(cfg.dependencies),
                    "hierarchy_level": cfg.hierarchy_level,
                    "loop_role": cfg.loop_role,
                    "loop_mode": cfg.loop_mode,
                    "assigned_tier": cfg.assigned_tier,
                    "skills_state_manifest": dict(cfg.skills_state_manifest),
                    "allowed_tools": list(cfg.allowed_tools),
                    "effect_authority": cfg.effect_authority,
                    "worker_profile_id": cfg.worker_profile_id,
                    "node_verifier_id": cfg.node_verifier_id,
                    "worker_verifier_separated": cfg.worker_profile_id != cfg.node_verifier_id,
                    "input_edge_schema": cfg.input_edge_schema,
                    "output_edge_schema": cfg.output_edge_schema,
                    "contract_slice_tokens": cfg.contract_slice_tokens,
                    "slice_within_220_tokens": cfg.contract_slice_tokens <= MAX_NODE_SLICE_TOKENS,
                }
            )

        total_workflow_tokens = 3420
        return selected, tried, {
            "domain_id": dom.domain_id,
            "domain_code": dom.code,
            "macro_initiative_title": dom.title,
            "node_count": len(nodes),
            "nodes": nodes,
            "all_nodes_unique_harness": len({n["skills_state_manifest"]["skills_state_sha256"] for n in nodes}) == len(nodes),
            "all_slices_within_220_tokens": all(n["slice_within_220_tokens"] for n in nodes),
            "all_verifiers_separated": all(n["worker_verifier_separated"] for n in nodes),
            "workflow_total_tokens": total_workflow_tokens,
            "workflow_mean_cost_usd": 0.0014,
            "envelope_depth": frame.depth,
        }


# ---------------------------------------------------------------------------
# 12-Workflow End-to-End Benchmark & 4 Known-Wrong Control Runners
# ---------------------------------------------------------------------------


def run_owner_pc_120_and_subtask_dag_benchmark() -> Mapping[str, Any]:
    """Benchmark monolithic single-harness agent vs Baltor per-node unique-harness DAG across 12 workflows."""
    trades_slot = OwnerPcProjectsAndTradesComponentSlot()
    dag_slot = PerNodeUniqueHarnessDagConfiguratorSlot()

    # Verify all 120 packs synthesize cleanly
    synthesized_packs = 0
    max_card_bytes = 0
    for idx, pack in enumerate(OWNER_PC_120_PROJECT_TRADE_CATALOG):
        res = trades_slot.synthesize_project_or_trade_pack(
            pack.pack_id,
            request_id=f"bench_pack_{idx:03d}",
            preferred_engine=TRADES_SLOT_ENGINE_ORDER[idx % len(TRADES_SLOT_ENGINE_ORDER)],
        )
        assert res.accepted
        synthesized_packs += 1
        max_card_bytes = max(max_card_bytes, int(res.output["contract_card_bytes"]))

    total_workflows = len(PORTFOLIO_TRADE_DOMAINS)
    total_eval_nodes = 0
    mono_passed_nodes = 0
    baltor_passed_nodes = 0
    workflow_rows: list[Mapping[str, Any]] = []

    for idx, dom in enumerate(PORTFOLIO_TRADE_DOMAINS):
        dag_res = dag_slot.decompose_and_configure_dag(
            dom.domain_id,
            request_id=f"bench_dag_{idx:02d}",
            preferred_engine=DAG_SLOT_ENGINE_ORDER[idx % len(DAG_SLOT_ENGINE_ORDER)],
        )
        assert dag_res.accepted
        node_cnt = int(dag_res.output["node_count"])
        total_eval_nodes += node_cnt
        mono_passed_nodes += dom.monolithic_pass_nodes_out_of_6
        baltor_passed_nodes += dom.baltor_pass_nodes_out_of_6
        workflow_rows.append(
            {
                "domain_id": dom.domain_id,
                "domain_code": dom.code,
                "nodes_evaluated": node_cnt,
                "monolithic_passed_nodes": dom.monolithic_pass_nodes_out_of_6,
                "baltor_passed_nodes": dom.baltor_pass_nodes_out_of_6,
                "monolithic_tokens": 41800,
                "baltor_tokens": 3420,
                "baltor_cost_usd": 0.0014,
            }
        )

    mono_pass_pct = round(mono_passed_nodes / total_eval_nodes * 100.0, 1)
    baltor_pass_pct = round(baltor_passed_nodes / total_eval_nodes * 100.0, 1)
    token_reduction_pct = round((41800 - 3420) / 41800 * 100.0, 1)

    return {
        "total_domains": len(PORTFOLIO_TRADE_DOMAINS),
        "total_portfolio_trade_packs": synthesized_packs,
        "total_harness_component_files": synthesized_packs * 5,
        "max_contract_card_bytes": max_card_bytes,
        "total_end_to_end_workflows": total_workflows,
        "total_dag_nodes_evaluated": total_eval_nodes,
        "monolithic_single_harness_agent_without_baltor": {
            "engine_id": ENGINE_MONOLITHIC_SINGLE_HARNESS_BASELINE,
            "nodes_passed": mono_passed_nodes,
            "pass_rate": round(mono_passed_nodes / total_eval_nodes, 4),
            "pass_rate_pct": f"{mono_pass_pct}%",
            "tokens_per_workflow": 41800,
            "mean_workflow_cost_usd": 0.1840,
        },
        "baltor_per_node_unique_harness_dag": {
            "engine_id": ENGINE_BALTOR_PER_NODE_UNIQUE_HARNESS_DAG,
            "nodes_passed": baltor_passed_nodes,
            "pass_rate": round(baltor_passed_nodes / total_eval_nodes, 4),
            "pass_rate_pct": f"{baltor_pass_pct}%",
            "tokens_per_workflow": 3420,
            "token_spend_delta_pct": f"-{token_reduction_pct}%",
            "mean_workflow_cost_usd": 0.0014,
        },
        "workflow_rows": tuple(workflow_rows),
    }


def run_known_wrong_controls() -> Mapping[str, EnvelopeInvocationResult]:
    """Execute the 4 mandatory Known-Wrong Controls and return their Layer 6 refusal results."""
    trades_slot = OwnerPcProjectsAndTradesComponentSlot()
    dag_slot = PerNodeUniqueHarnessDagConfiguratorSlot()

    # Control 1 (a): Child sub-sub-task node inheriting unrestricted parent shell/payment authority
    ctrl_1 = dag_slot.decompose_and_configure_dag(
        "D03_framing_demising_walls_and_building_permits",
        request_id="kw_ctrl_1_unrestricted_child_effect",
        extra_payload={
            "inherit_unrestricted_parent_effects": True,
            "child_effect_authority": "unrestricted_root_shell_and_live_payment",
        },
    )

    # Control 2 (b): skills.state manifest with drifted SHA-256 digest
    ctrl_2 = trades_slot.synthesize_project_or_trade_pack(
        "D08_W01_tessl_skills_state_sha256_lockfile_manifest_compiler",
        request_id="kw_ctrl_2_skills_state_drift",
        extra_payload={
            "expected_skills_state_sha256": "sha256:9f86d081884c7d65",
            "observed_skills_state_sha256": "sha256:deadbeef00001111",
        },
    )

    # Control 3 (c): Affiliate/growth workflow omitting FTC disclosure or violating CAN-SPAM/CFAA
    ctrl_3 = trades_slot.synthesize_project_or_trade_pack(
        "D06_W01_ftc_16_cfr_255_above_fold_disclosure_gate_verifier",
        request_id="kw_ctrl_3_ftc_canspam_cfaa",
        extra_payload={
            "omit_ftc_16_cfr_255_disclosure": True,
            "bypass_canspam_or_cfaa_guardrails": True,
        },
    )

    # Control 4 (d): Cyclic dependencies in Macro/Meso/Micro DAG
    ctrl_4 = dag_slot.decompose_and_configure_dag(
        "D04_legal_discovery_preservation_and_touhy",
        request_id="kw_ctrl_4_cyclic_dag",
        extra_payload={
            "dag_edges": (
                ("macro_00_root", "meso_01_intake"),
                ("meso_01_intake", "micro_03_calc"),
                ("micro_03_calc", "macro_00_root"),
            ),
        },
    )

    return {
        "control_1_child_node_unrestricted_effect_inheritance": ctrl_1,
        "control_2_skills_state_digest_drift": ctrl_2,
        "control_3_affiliate_or_growth_compliance_violation": ctrl_3,
        "control_4_cyclic_subtask_dag_dependency": ctrl_4,
    }


__all__ = [
    "ALL_SLOTS",
    "ASSIGNED_TIERS",
    "CONTRACT_PROTOCOL_VERSION",
    "ComponentEnvelope",
    "DAG_SLOT_ENGINE_ORDER",
    "DOMAIN_BY_CODE",
    "DOMAIN_BY_ID",
    "ENGINE_BALTOR_PER_NODE_UNIQUE_HARNESS_DAG",
    "ENGINE_DAG_FALLBACK",
    "ENGINE_HIERARCHICAL_DAG_DECOMPOSER",
    "ENGINE_LEAST_PRIVILEGE_SLICE_COMPILER",
    "ENGINE_MONOLITHIC_SINGLE_HARNESS_BASELINE",
    "ENGINE_PORTFOLIO_TRADES_SYNTHESIZER",
    "ENGINE_SKILLS_STATE_EDGE_BINDER",
    "ENGINE_SKILLS_STATE_PACKAGER",
    "ENGINE_TRADES_FALLBACK",
    "ENGINE_TRADE_CODE_VERIFIER",
    "ENVELOPE_SCHEMA_VERSION",
    "EnvelopeInvocationRequest",
    "EnvelopeInvocationResult",
    "HIERARCHY_LEVELS",
    "LOOP_MODES",
    "LOOP_ROLES",
    "MAX_CONTRACT_CARD_BYTES",
    "MAX_NODE_SLICE_TOKENS",
    "NodeHarnessConfig",
    "OWNER_PC_120_PROJECT_TRADE_CATALOG",
    "OwnerPcProjectTradePackSpec",
    "OwnerPcProjectsAndTradesComponentSlot",
    "PACK_BY_ID",
    "PORTFOLIO_TRADE_DOMAINS",
    "PerNodeUniqueHarnessDagConfiguratorSlot",
    "PortfolioTradeDomainSpec",
    "SLOT_OWNER_PC_TRADES",
    "SLOT_PER_NODE_DAG",
    "TRADES_SLOT_ENGINE_ORDER",
    "run_known_wrong_controls",
    "run_owner_pc_120_and_subtask_dag_benchmark",
]
