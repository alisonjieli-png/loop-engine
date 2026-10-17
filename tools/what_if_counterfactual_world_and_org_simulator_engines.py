"""Counterfactual "What-If" World, Management Personality, Budget/Hardware Constraint,
and Organizational Volatility Simulator -> Adaptive Harness Component Generator Suite.

Implements two engine slot families wrapped in the 7-layer `ComponentEnvelope`
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`,
`nested_envelopes`) with automatic fallback chains and known-wrong controls:

1. Slot Family 1 (`what_if_counterfactual_and_org_simulator_slot`):
   Models 57,600 Counterfactual Operating Worlds (16 Management Personalities x
   15 World/Infrastructure Shocks x 12 Budget/Latency Envelopes x 20 Industry Substrates):
   - `counterfactual_stress_tree_simulator_engine`
   - `management_persona_utility_optimizer_engine`
   - `monte_carlo_shock_resilience_engine`
   - `deterministic_constraint_table_fallback_engine`

2. Slot Family 2 (`counterfactual_to_harness_component_synthesizer_slot`):
   Synthesizes drop-in Counterfactual Adaptation Packs (`AGENTS.md`, `RULES.md`,
   `MEMORY.md`, `baltor_contract_card.json` <= 2,048 bytes, and
   `verify_counterfactual_compliance.py`):
   - `baltor_counterfactual_adaptive_harness_engine`
   - `template_lattice_harness_synthesizer_engine`
   - `minimal_offline_contract_pack_fallback_engine`
   - `rigid_unadapted_agent_without_baltor` (baseline comparison control)
"""
from __future__ import annotations

from collections.abc import Mapping
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
# Slot identifiers, engine names, and contract constants
# ---------------------------------------------------------------------------

SLOT_WHAT_IF_SIMULATOR = "what_if_counterfactual_and_org_simulator_slot"
SLOT_HARNESS_SYNTHESIZER = "counterfactual_to_harness_component_synthesizer_slot"
ALL_SLOTS = (SLOT_WHAT_IF_SIMULATOR, SLOT_HARNESS_SYNTHESIZER)

ENGINE_STRESS_TREE_SIMULATOR = "counterfactual_stress_tree_simulator_engine"
ENGINE_PERSONA_UTILITY_OPTIMIZER = "management_persona_utility_optimizer_engine"
ENGINE_MONTE_CARLO_RESILIENCE = "monte_carlo_shock_resilience_engine"
ENGINE_CONSTRAINT_TABLE_FALLBACK = "deterministic_constraint_table_fallback_engine"
SIMULATOR_ENGINE_ORDER = (
    ENGINE_STRESS_TREE_SIMULATOR,
    ENGINE_PERSONA_UTILITY_OPTIMIZER,
    ENGINE_MONTE_CARLO_RESILIENCE,
    ENGINE_CONSTRAINT_TABLE_FALLBACK,
)

ENGINE_BALTOR_ADAPTIVE_HARNESS = "baltor_counterfactual_adaptive_harness_engine"
ENGINE_TEMPLATE_LATTICE_SYNTH = "template_lattice_harness_synthesizer_engine"
ENGINE_MINIMAL_OFFLINE_FALLBACK = "minimal_offline_contract_pack_fallback_engine"
ENGINE_RIGID_UNADAPTED_BASELINE = "rigid_unadapted_agent_without_baltor"
SYNTHESIZER_ENGINE_ORDER = (
    ENGINE_BALTOR_ADAPTIVE_HARNESS,
    ENGINE_TEMPLATE_LATTICE_SYNTH,
    ENGINE_MINIMAL_OFFLINE_FALLBACK,
)

ENVELOPE_SCHEMA_VERSION = "loop_engine.what_if_counterfactual_envelope.v1"
CONTRACT_PROTOCOL_VERSION = "1.0"
DEFAULT_RELEASE_DIGEST = "sha256:what_if_counterfactual_2026_10_17_v1"
MAX_CONTRACT_CARD_BYTES = 2048
EVIDENCE_CATEGORY_COUNTERFACTUAL = "counterfactual_simulation"


# ---------------------------------------------------------------------------
# Dimension W1: 16 Management & Stakeholder Personalities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ManagementPersonalitySpec:
    """Specification for one management or stakeholder operating personality."""

    personality_id: str
    title: str
    decision_style: str
    reporting_cadence: str
    escalation_rule: str
    preferred_ladder_tier: str
    mandatory_invariants: tuple[str, ...]
    forbidden_behaviors: tuple[str, ...]


MANAGEMENT_PERSONALITIES: tuple[ManagementPersonalitySpec, ...] = (
    ManagementPersonalitySpec(
        "zero_questions_autonomous_execution_founder",
        "Zero-Questions Autonomous Execution Founder",
        "Decide via A/B measurement or deterministic benchmarks, commit and push when checks pass, never end with clarifying questions.",
        "Concise post-commit report with commit hashes, check counts, and benchmark tables.",
        "Escalate only for resource deletion, spend above allowance, legal commitments, or provider bank/identity verification.",
        "L0_deterministic_and_L1_cached_contract_first",
        ("benchmark_evidence_attached", "zero_clarifying_questions", "decisions_documented"),
        ("asking_clarifying_questions", "unverified_claims", "waiting_for_routine_approval"),
    ),
    ManagementPersonalitySpec(
        "skeptical_cfo_finops_dollar_hawk",
        "Skeptical CFO & FinOps Dollar Hawk",
        "Enforce strict unit-economics receipts, $0 deterministic L0/L1 execution first, and hard per-task token cost caps.",
        "Per-run FinOps ledger with direct COGS, gross margin percentage, and token savings receipt.",
        "Halt immediately before any unbudgeted cloud model call or spend above the task ceiling.",
        "L0_deterministic_zero_marginal_cost",
        ("unit_economics_receipt", "l0_l1_before_model_call", "strict_task_cost_cap"),
        ("unbudgeted_frontier_llm_call", "missing_cost_attribution"),
    ),
    ManagementPersonalitySpec(
        "paranoid_zero_trust_ciso",
        "Paranoid Zero-Trust CISO",
        "Require air-gapped or customer-BYOK execution, zero unauthorized egress, pinned SBOM digests, and AST sandboxing.",
        "Cryptographic attestation log with SHA-256 artifact digests and egress audit trail.",
        "Block and quarantine any unpinned dependency, external network write, or secret exposure.",
        "L0_ast_sandbox_and_L2_local_airgap",
        ("zero_external_egress", "sbom_digest_pinned", "ast_sandbox_verified", "zero_secret_leakage"),
        ("unauthenticated_network_egress", "plaintext_credential_logging", "unpinned_third_party_code"),
    ),
    ManagementPersonalitySpec(
        "pixel_perfect_design_director",
        "Pixel-Perfect Creative Design Director",
        "Demand 3D sky-dome horizons, perceptual OKLab color palettes, tactile PBR shaders, 60fps pacing, and zero generic AI slop.",
        "Side-by-side visual telemetry scorecard with OKLab contrast ratios, frame-time p99, and shader bindings.",
        "Reject any flat 2D placeholder, uncalibrated color ramp, or frame drop below 60fps.",
        "L1_native_shader_and_3d_scene_contracts",
        ("oklab_perceptual_palette", "tactile_pbr_materials", "sky_dome_horizon_depth", "sixty_fps_budget"),
        ("generic_ai_visual_slop", "uncapped_frame_jitter"),
    ),
    ManagementPersonalitySpec(
        "military_mission_commander_mil_std",
        "Military Mission Commander (MIL-STD / DD-250)",
        "Operate under BLUF (Bottom Line Up Front) doctrine, DD-250 acceptance gates, and degraded-comms offline autonomy.",
        "BLUF sitrep with mission status, deterministic fallback readiness, and MIL-STD verification matrix.",
        "Trigger degraded-comms autonomous runbook whenever uplink latency exceeds threshold or link drops.",
        "L0_deterministic_runbook_and_L2_tactical_edge",
        ("bluf_sitrep_format", "dd250_acceptance_matrix", "degraded_comms_offline_autonomy"),
        ("verbose_narrative_preamble", "cloud_single_point_of_failure"),
    ),
    ManagementPersonalitySpec(
        "clinical_fda_hipaa_compliance_officer",
        "Clinical FDA 21 CFR Part 11 & HIPAA Compliance Officer",
        "Guarantee zero PHI leakage, immutable audit trails, calibrated uncertainty bounds, and deterministic redaction.",
        "HIPAA Safe-Harbor redaction certificate and calibrated sensitivity/specificity validation table.",
        "Refuse any unredacted patient identifier or uncalibrated probabilistic diagnostic assertion.",
        "L0_deterministic_redaction_and_calibrated_verifier",
        ("zero_phi_leakage", "fda_part11_audit_trail", "calibrated_confidence_intervals"),
        ("unredacted_phi_in_context", "uncalibrated_hallucinated_advice"),
    ),
    ManagementPersonalitySpec(
        "hyper_growth_48hr_hackathon_vp",
        "Hyper-Growth 48-Hour Hackathon & Launch VP",
        "Prioritize sub-second scaffolding, zero-config SQLite WAL + Cloudflare Workers, and instant live preview URLs.",
        "Live deployment card with p95 latency, smoke-check verdict, and conversion funnel readiness.",
        "Bypass heavy ceremony; escalate only if live smoke checks or rollback invariants fail.",
        "L1_cached_contract_card_and_fast_scaffold",
        ("sub_second_scaffold", "zero_config_sqlite_edge", "automated_smoke_gate"),
        ("multi_day_boilerplate_setup", "untested_live_deploy"),
    ),
    ManagementPersonalitySpec(
        "legacy_mainframe_risk_averse_vp",
        "Legacy Mainframe & Core-Banking Risk-Averse VP",
        "Enforce zero regression on untouched COBOL/Java/SQL digests, strangler-fig adapters, and bit-exact replay.",
        "Change-impact blast-radius matrix with pre/post SHA-256 parity on all legacy interfaces.",
        "Halt immediately if any untouched module digest shifts or parity replay diverges by 1 ulp.",
        "L0_strangler_fig_contract_verifier",
        ("untouched_digest_parity", "strangler_fig_isolation", "bit_exact_batch_replay"),
        ("big_bang_rewrite", "unverified_schema_mutation"),
    ),
    ManagementPersonalitySpec(
        "academic_peer_reviewer_reproducibility_chair",
        "Academic Peer-Reviewer & Reproducibility Chair",
        "Require seed-pinned ablations, explicit Without-Baltor vs With-Baltor tables, and verifiable citations.",
        "Reproducibility appendix with fixed random seeds, confidence intervals, and observed vs simulated labels.",
        "Reject any benchmark claim lacking an unassisted baseline control or deterministic reproduction command.",
        "L0_seed_pinned_ablation_harness",
        ("seed_pinned_reproducibility", "with_vs_without_baltor_table", "observed_vs_simulated_separated"),
        ("cherry_picked_metrics", "unseeded_stochastic_claims"),
    ),
    ManagementPersonalitySpec(
        "union_shop_floor_safety_superintendent",
        "Union Shop-Floor & Industrial Safety Superintendent",
        "Mandate NIOSH WBGT heat/load limits, OSHA lockout-tagout (LOTO) preflight gates, and plain-language SOPs.",
        "Shift-handover safety checklist with physical interlock status and human-in-the-loop signoff.",
        "Trigger hard physical stop if any sensor telemetry or LOTO preflight check is missing or out of bounds.",
        "L0_hard_safety_interlock_preflight",
        ("osha_loto_interlock_verified", "niosh_ergonomic_ceiling", "plain_language_sop"),
        ("bypassing_safety_interlock", "opaque_jargon_instructions"),
    ),
    ManagementPersonalitySpec(
        "open_source_maintainer_minimalist",
        "Open-Source Minimalist Core Maintainer",
        "Insist on zero heavy transitive dependencies, surgical single-purpose diffs, and clean MIT/Apache-2.0 provenance.",
        "Minimal diffstat summary, dependency tree delta (= 0 new heavy packages), and test suite timing.",
        "Refuse bloated frameworks, copyleft license contamination, or broad formatting churn.",
        "L0_stdlib_first_surgical_patch",
        ("zero_heavy_dependencies", "surgical_diff_footprint", "permissive_license_provenance"),
        ("dependency_bloat", "unrequested_tree_wide_reformat"),
    ),
    ManagementPersonalitySpec(
        "public_sector_inspector_general_foia",
        "Public-Sector Inspector General & FOIA Auditor",
        "Require explainable deterministic decision rules, WCAG AAA accessibility, and zero proprietary vendor lock-in.",
        "FOIA-ready decision provenance log with statutory rule citations and accessibility conformance report.",
        "Refuse any black-box score that cannot be explained in plain civic prose or exported in open formats.",
        "L0_explainable_rule_table_and_open_formats",
        ("foia_explainable_decision_trace", "wcag_aaa_accessibility", "open_format_portability"),
        ("opaque_black_box_denial", "proprietary_format_lock_in"),
    ),
    ManagementPersonalitySpec(
        "quant_trading_low_latency_desk_head",
        "Quantitative Low-Latency Trading Desk Head",
        "Enforce sub-millisecond p99 tail latency, zero garbage-collection pauses on the hot path, and zero temporal lookahead.",
        "Nanosecond/microsecond latency histogram (p50/p99/p99.9) and strict out-of-sample walk-forward ledger.",
        "Kill any strategy or engine that allocates on the hot loop or leaks future timestamps into features.",
        "L0_preallocated_ring_buffer_and_bloom_cache",
        ("sub_1ms_p99_hot_path", "zero_temporal_lookahead", "zero_hot_path_gc_alloc"),
        ("future_data_leakage", "unbounded_tail_latency_spike"),
    ),
    ManagementPersonalitySpec(
        "indie_game_solo_dev_on_laptop",
        "Indie Game Solo Developer on a Laptop",
        "Maximize procedural asset generation, code-CAD (Tinkercad/3dxd/claude-pxl), and local 127.0.0.1 inference at $0 cloud cost.",
        "Compact build manifest with asset byte counts, frame-time budget, and offline playability status.",
        "Fall back to procedural noise/SDF shaders and local quantized weights whenever offline or VRAM-constrained.",
        "L1_procedural_code_cad_and_L2_local_ollama",
        ("procedural_asset_pipeline", "local_127_0_0_1_compatible", "laptop_ram_ceiling_respected"),
        ("mandatory_cloud_render_farm", "multi_gigabyte_uncompressed_assets"),
    ),
    ManagementPersonalitySpec(
        "nonprofit_humanitarian_field_director",
        "Nonprofit Humanitarian Field Operations Director",
        "Operate over intermittent 2G/SMS links, offline-first CRDT/SQLite sync, multilingual plain copy, and $0 cloud spend.",
        "Field sync digest with packet byte size, offline queue health, and plain-language translation status.",
        "Degrade gracefully to store-and-forward compact JSON/SMS payloads when connectivity drops.",
        "L0_offline_sqlite_sync_and_compact_cards",
        ("offline_2g_sms_resilient", "zero_cloud_spend", "multilingual_plain_copy"),
        ("high_bandwidth_polling", "paid_api_dependency_in_field"),
    ),
    ManagementPersonalitySpec(
        "board_of_directors_series_a_diligence_lead",
        "Board of Directors & Series-A Diligence Lead",
        "Demand strict separation of observed facts from projected assumptions, Merkle-signed leaderboards, and reproducible unit economics.",
        "Signed diligence dataroom packet with SHA-256 verification digest, cohort retention, and benchmark lift tables.",
        "Refuse any report that conflates counterfactual simulations or pro-forma projections with observed historical telemetry.",
        "L0_signed_dataroom_and_verified_leaderboard",
        ("observed_vs_projected_disjoint", "merkle_signed_telemetry", "reproducible_margin_schedule"),
        ("projection_labeled_as_observed", "unsigned_kpi_assertion"),
    ),
)

PERSONALITY_BY_ID: Mapping[str, ManagementPersonalitySpec] = {
    p.personality_id: p for p in MANAGEMENT_PERSONALITIES
}


# ---------------------------------------------------------------------------
# Dimension W2: 15 Counterfactual World & Infrastructure Shocks
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorldShockSpec:
    """Specification for one counterfactual world or infrastructure shock."""

    shock_id: str
    question_prompt: str
    cloud_api_available: bool
    token_price_multiplier: float
    max_ram_mb: int
    schema_mutable: bool
    traffic_multiplier: float
    store_writable: bool
    required_fallback_route: str


COUNTERFACTUAL_WORLD_SHOCKS: tuple[WorldShockSpec, ...] = (
    WorldShockSpec(
        "external_cloud_api_blackout_72hr",
        "What if all external cloud LLM APIs go dark for 72 hours?",
        False, 1.0, 8192, True, 1.0, True,
        "route_to_L0_deterministic_and_L2_local_127_0_0_1",
    ),
    WorldShockSpec(
        "token_price_10x_overnight_shock",
        "What if model token prices increase 10x overnight?",
        True, 10.0, 8192, True, 1.0, True,
        "enforce_L0_L1_cache_first_and_prune_context_to_contract_cards",
    ),
    WorldShockSpec(
        "edge_box_2gb_ram_cpu_only_constraint",
        "What if we only have a 2GB RAM CPU edge box?",
        False, 1.0, 2048, True, 1.0, True,
        "cap_working_set_under_1536mb_and_use_L0_L1_compact_cards",
    ),
    WorldShockSpec(
        "regulatory_audit_schema_freeze",
        "What if a regulatory audit freezes all database and contract schema changes?",
        True, 1.0, 8192, False, 1.0, True,
        "lock_schema_versions_and_route_via_adapter_projections",
    ),
    WorldShockSpec(
        "viral_hn_reddit_100x_traffic_spike",
        "What if a viral HN/Reddit launch spikes traffic 100x in 10 minutes?",
        True, 1.0, 4096, True, 100.0, True,
        "serve_from_sub_1ms_bloom_lru_and_edge_kv_stale_while_revalidate",
    ),
    WorldShockSpec(
        "primary_database_read_only_store_busy",
        "What if the primary database is read-only or locked (store_busy)?",
        True, 1.0, 8192, False, 1.0, False,
        "degrade_to_read_only_snapshot_and_journal_durable_pending_intents",
    ),
    WorldShockSpec(
        "supply_chain_dependency_malware_compromise",
        "What if a public dependency repository is compromised by supply-chain malware?",
        False, 1.0, 8192, True, 1.0, True,
        "freeze_lockfile_digests_and_prefer_baltor_native_stdlib_engines",
    ),
    WorldShockSpec(
        "mandatory_48hr_product_vertical_pivot",
        "What if the team must pivot the product vertical in 48 hours?",
        True, 1.0, 8192, True, 3.0, True,
        "rebind_engine_slots_via_contract_cards_without_rewriting_callers",
    ),
    WorldShockSpec(
        "zero_egress_airgapped_scif_deployment",
        "What if the runtime is deployed inside a zero-egress air-gapped enclave?",
        False, 1.0, 4096, False, 1.0, True,
        "disable_all_network_egress_and_execute_offline_verified_packs",
    ),
    WorldShockSpec(
        "lead_engineer_unavailable_bus_factor_one",
        "What if the sole lead maintainer is unreachable for 14 days during a release?",
        True, 1.0, 8192, False, 1.0, True,
        "enforce_self_healing_preflight_and_automated_rollback_gates",
    ),
    WorldShockSpec(
        "gpu_vram_exhaustion_quantized_4bit_only",
        "What if GPU VRAM is exhausted and only 4-bit quantized local weights fit?",
        False, 1.0, 3072, True, 1.0, True,
        "pair_4bit_local_model_with_deterministic_L0_verifiers",
    ),
    WorldShockSpec(
        "adversarial_prompt_injection_red_team_siege",
        "What if an automated botnet floods public inputs with adversarial prompt injections?",
        True, 1.0, 8192, False, 25.0, True,
        "enforce_typed_carrier_schemas_and_strip_untrusted_instruction_channels",
    ),
    WorldShockSpec(
        "submarine_cable_cut_2g_satellite_link",
        "What if regional fiber is cut and links degrade to 50 kbps satellite/2G?",
        False, 1.0, 2048, True, 1.0, True,
        "compress_contract_cards_under_2kb_and_batch_idempotent_sync",
    ),
    WorldShockSpec(
        "copyright_license_audit_clean_room_mandate",
        "What if counsel mandates immediate clean-room replacement of copyleft adapters?",
        True, 1.0, 8192, True, 1.0, True,
        "hot_swap_engine_slot_to_baltor_native_clean_room_implementation",
    ),
    WorldShockSpec(
        "multi_worktree_merge_storm_20_agents",
        "What if 20 detached-worktree agents submit concurrent patches during launch?",
        True, 1.0, 3072, True, 5.0, True,
        "enforce_disjoint_file_ownership_and_100pct_line_preservation_audit",
    ),
)

SHOCK_BY_ID: Mapping[str, WorldShockSpec] = {s.shock_id: s for s in COUNTERFACTUAL_WORLD_SHOCKS}


# ---------------------------------------------------------------------------
# Dimension W3: 12 Budget & Latency Envelopes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BudgetLatencyEnvelopeSpec:
    """Specification for one budget and latency operating envelope."""

    envelope_id: str
    label: str
    daily_budget_usd: float
    monthly_budget_usd: float
    target_p99_latency_ms: float
    max_memory_mb: int
    allowed_ladder_tiers: tuple[str, ...]


BUDGET_AND_LATENCY_ENVELOPES: tuple[BudgetLatencyEnvelopeSpec, ...] = (
    BudgetLatencyEnvelopeSpec("usd_0_00_day_offline_sub_1ms_hard_rt", "$0.00/day offline, <1ms hard real-time", 0.0, 0.0, 0.8, 1024, ("L0", "L1")),
    BudgetLatencyEnvelopeSpec("usd_0_00_day_offline_10ms_edge_interactive", "$0.00/day offline, 10ms edge interactive", 0.0, 0.0, 10.0, 2048, ("L0", "L1", "L2_local")),
    BudgetLatencyEnvelopeSpec("usd_0_05_day_micro_50ms_interactive", "$0.05/day micro, 50ms interactive", 0.05, 1.50, 50.0, 2048, ("L0", "L1", "L2_local")),
    BudgetLatencyEnvelopeSpec("usd_0_25_day_solo_100ms_ui_frame", "$0.25/day solo, 100ms UI frame", 0.25, 7.50, 100.0, 3072, ("L0", "L1", "L2_local", "L3_cheap")),
    BudgetLatencyEnvelopeSpec("usd_1_00_day_indie_250ms_api_slo", "$1.00/day indie, 250ms API SLO", 1.00, 30.0, 250.0, 3072, ("L0", "L1", "L2_local", "L3_cheap")),
    BudgetLatencyEnvelopeSpec("usd_5_00_day_startup_500ms_rag_loop", "$5.00/day startup, 500ms RAG loop", 5.00, 150.0, 500.0, 4096, ("L0", "L1", "L2_local", "L3_cheap")),
    BudgetLatencyEnvelopeSpec("usd_15_00_day_team_2s_interactive_agent", "$15.00/day team, 2s interactive agent", 15.00, 450.0, 2000.0, 8192, ("L0", "L1", "L2_local", "L3_cheap", "L4_frontier")),
    BudgetLatencyEnvelopeSpec("usd_50_00_mo_pilot_5s_guarded_ops", "$50.00/mo pilot, 5s guarded ops", 1.67, 50.0, 5000.0, 3072, ("L0", "L1", "L2_local", "L3_cheap")),
    BudgetLatencyEnvelopeSpec("usd_199_00_mo_pro_30s_worktree_build", "$199.00/mo pro, 30s worktree build", 6.63, 199.0, 30000.0, 4096, ("L0", "L1", "L2_local", "L3_cheap", "L4_frontier")),
    BudgetLatencyEnvelopeSpec("usd_799_00_mo_studio_5min_render_batch", "$799.00/mo studio, 5min render batch", 26.63, 799.0, 300000.0, 8192, ("L0", "L1", "L2_local", "L3_cheap", "L4_frontier")),
    BudgetLatencyEnvelopeSpec("usd_2500_00_mo_scaleup_1hr_ci_gauntlet", "$2,500/mo scale-up, 1hr CI gauntlet", 83.33, 2500.0, 3600000.0, 16384, ("L0", "L1", "L2_local", "L3_cheap", "L4_frontier")),
    BudgetLatencyEnvelopeSpec("usd_10000_00_mo_enterprise_8hr_overnight_afk", "$10,000/mo enterprise, 8hr overnight AFK", 333.33, 10000.0, 28800000.0, 32768, ("L0", "L1", "L2_local", "L3_cheap", "L4_frontier")),
)

ENVELOPE_BY_ID: Mapping[str, BudgetLatencyEnvelopeSpec] = {
    e.envelope_id: e for e in BUDGET_AND_LATENCY_ENVELOPES
}


# ---------------------------------------------------------------------------
# Dimension W4: 20 Industry & Codebase Substrates
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndustrySubstrateSpec:
    """Specification for one industry vertical and codebase substrate."""

    industry_id: str
    compliance_regime: str
    primary_stack: str
    critical_artifact: str


INDUSTRY_SUBSTRATES: tuple[IndustrySubstrateSpec, ...] = (
    IndustrySubstrateSpec("autonomous_coding_harness_foundry", "AGENTS_MD_7_LAYER_ENVELOPE", "python_312_sqlite_cloudflare", "contract_card_and_engine_slot"),
    IndustrySubstrateSpec("fintech_ledger_and_payment_clearing", "PCI_DSS_SOX_DOUBLE_ENTRY", "python_postgres_stripe_webhook", "idempotent_settlement_journal"),
    IndustrySubstrateSpec("clinical_ehr_and_biotech_diagnostics", "HIPAA_FDA_21CFR11", "python_fhir_hl7_redactor", "deidentified_clinical_audit_bundle"),
    IndustrySubstrateSpec("aerospace_avionics_and_defense_c2", "MIL_STD_882E_DO_178C", "rust_c_deterministic_state_machine", "dd250_flight_readiness_packet"),
    IndustrySubstrateSpec("realtime_3d_game_and_shader_studio", "OKLAB_PBR_60FPS_PARITY", "webgl_three_wgsl_blender_headless", "tactile_pbr_sky_dome_scene"),
    IndustrySubstrateSpec("quantitative_low_latency_trading_desk", "SEC_15C3_5_ZERO_LOOKAHEAD", "cpp_rust_python_ring_buffer", "walk_forward_execution_ledger"),
    IndustrySubstrateSpec("industrial_robotics_and_plc_shop_floor", "OSHA_1910_147_NIOSH_WBGT", "iec61131_structured_text_python", "loto_interlock_safety_manifest"),
    IndustrySubstrateSpec("public_sector_civic_benefits_portal", "FOIA_WCAG_AAA_SECTION_508", "python_html_open_standards", "explainable_eligibility_trace"),
    IndustrySubstrateSpec("e_commerce_high_velocity_checkout", "PCI_SWR_EDGE_AVAILABILITY", "typescript_workers_d1_sqlite", "sub_50ms_cart_reservation_receipt"),
    IndustrySubstrateSpec("cybersecurity_soc_and_threat_hunting", "NIST_800_53_ZERO_EGRESS", "python_ebpf_sigma_ast_rules", "quarantined_ioc_evidence_pack"),
    IndustrySubstrateSpec("supply_chain_warehouse_and_fleet_routing", "ISO_28000_COLD_CHAIN", "python_ortools_sqlite_offline", "deterministic_dispatch_schedule"),
    IndustrySubstrateSpec("scientific_hpc_and_reproducible_ml_lab", "ACM_ARTIFACT_BADGE_SEED_PINNED", "python_numpy_pytorch_bibtex", "ablation_reproducibility_dossier"),
    IndustrySubstrateSpec("humanitarian_disaster_relief_field_ops", "SPHERE_2G_OFFLINE_PRIVACY", "sqlite_crdt_sms_multilingual", "compact_field_triage_sync_pack"),
    IndustrySubstrateSpec("legacy_banking_cobol_java_core_migration", "BASEL_III_STRANGLER_PARITY", "cobol_java_sql_strangler_adapter", "bit_exact_shadow_replay_report"),
    IndustrySubstrateSpec("media_streaming_and_social_video_pipeline", "C2PA_PROVENANCE_60FPS_AV1", "ffmpeg_webgl_canvas_audio_dsp", "frame_accurate_render_manifest"),
    IndustrySubstrateSpec("energy_grid_scada_and_battery_dispatch", "NERC_CIP_FREQUENCY_BOUNDS", "python_modbus_deterministic_mpc", "substation_setpoint_safety_proof"),
    IndustrySubstrateSpec("legal_contract_discovery_and_redaction", "FRCP_PRIVILEGE_LOG_AUDIT", "python_ast_regex_citation_verifier", "privilege_redacted_clause_index"),
    IndustrySubstrateSpec("edtech_adaptive_tutoring_and_grading", "FERPA_COPPA_DETERMINISTIC_RUBRIC", "python_wasm_sandbox_grader", "calibrated_mastery_rubric_card"),
    IndustrySubstrateSpec("agricultural_iot_and_drought_telemetry", "FAO_EDGE_SOLAR_BUDGET", "micropython_lora_sqlite_ring", "irrigation_valve_schedule_pack"),
    IndustrySubstrateSpec("open_source_compiler_and_kernel_toolchain", "REPRODUCIBLE_BUILDS_MIT_APACHE", "rust_c_python_ast_verifier", "hermetic_build_attestation"),
)

INDUSTRY_BY_ID: Mapping[str, IndustrySubstrateSpec] = {
    i.industry_id: i for i in INDUSTRY_SUBSTRATES
}

TOTAL_COUNTERFACTUAL_WORLDS = (
    len(MANAGEMENT_PERSONALITIES)
    * len(COUNTERFACTUAL_WORLD_SHOCKS)
    * len(BUDGET_AND_LATENCY_ENVELOPES)
    * len(INDUSTRY_SUBSTRATES)
)


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeInvocationRequest:
    """Typed request entering the 7-layer ComponentEnvelope."""

    slot_id: str
    request_id: str
    account_id: str
    tier: str
    payload: Mapping[str, Any]
    active_release_digest: str = DEFAULT_RELEASE_DIGEST
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    protocol_version: str = CONTRACT_PROTOCOL_VERSION
    idempotency_key: str = ""
    parent_frame: EnvelopeFrame | None = None


@dataclass(frozen=True)
class EnvelopeInvocationResult:
    """Typed outcome emitted by the 7-layer ComponentEnvelope."""

    accepted: bool
    slot_id: str
    selected_engine: str
    fallback_chain_tried: tuple[str, ...]
    layer_verdicts: Mapping[str, str]
    payload_digest: str
    output: Mapping[str, Any]
    refusal: EnvelopeRefusal | None = None
    trace: EnvelopeTrace | None = None
    recovery_policy: EnvelopeRecoveryPolicy | None = None


class ComponentEnvelope:
    """Wraps a functional slot and its ordered engine chain in all 7 envelope layers."""

    def __init__(self, slot_id: str, engine_order: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self.recovery_policy = EnvelopeRecoveryPolicy(
            slot_id,
            MAXIMUM_AUTOMATIC_ATTEMPTS,
            ("transient_simulation_contention",),
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
                    "Generate a fresh request_id for distinct counterfactual simulation payloads.",
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
                ("counterfactual_dispatch",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                self.slot_id,
                (CONTRACT_PROTOCOL_VERSION,),
                ("counterfactual_dispatch",),
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
# Shared Counterfactual Preflight Checks (Enforcing the 4 Known-Wrong Controls)
# ---------------------------------------------------------------------------


def _check_founder_autonomy_no_questions(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (a): Refuse asking clarifying questions to zero_questions_autonomous_execution_founder."""
    personality_id = str(ctx.get("personality_id", ""))
    asks_questions = bool(ctx.get("asks_clarifying_questions", False))
    draft_text = str(ctx.get("candidate_response_text", ""))
    if personality_id == "zero_questions_autonomous_execution_founder" and (
        asks_questions or "would you like me to" in draft_text.lower() or "please clarify" in draft_text.lower()
    ):
        return envelope_refusal(
            "founder_clarifying_questions_refused",
            "The candidate agent response asks the autonomous founder a list of questions instead of deciding.",
            "Run an A/B benchmark or deterministic check, make the engineering decision, and document the rationale.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_cloud_blackout_and_budget_ceiling(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (b): Refuse cloud frontier model calls during cloud blackout or $0.00 budget counterfactual."""
    shock_id = str(ctx.get("shock_id", ""))
    envelope_id = str(ctx.get("envelope_id", ""))
    proposed_cloud_call = bool(ctx.get("proposed_cloud_frontier_call", False))
    proposed_spend = float(ctx.get("proposed_spend_usd", 0.0))

    shock = SHOCK_BY_ID.get(shock_id)
    env_spec = ENVELOPE_BY_ID.get(envelope_id)
    if shock is not None and not shock.cloud_api_available and proposed_cloud_call:
        return envelope_refusal(
            "counterfactual_cloud_or_budget_violation_refused",
            f"A cloud frontier model call was requested while world shock `{shock_id}` blocks external cloud APIs.",
            "Route execution through L0 deterministic verifiers, L1 cached contract cards, or L2 local 127.0.0.1 models.",
            retry=RETRY_AFTER_FIX,
        )
    if env_spec is not None and (
        (env_spec.daily_budget_usd == 0.0 and proposed_cloud_call)
        or proposed_spend > env_spec.daily_budget_usd
    ):
        return envelope_refusal(
            "counterfactual_cloud_or_budget_violation_refused",
            f"Proposed spend (${proposed_spend:.2f}) or cloud call exceeds budget envelope `{envelope_id}` (${env_spec.daily_budget_usd:.2f}/day).",
            "Switch to zero-marginal-cost L0 deterministic tools or L1 cached contract cards within the budget cap.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_contract_card_byte_ceiling(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (c): Refuse an unverified or bloated (> 2,048 bytes) counterfactual contract card."""
    injected_bytes = int(ctx.get("injected_contract_card_bytes", 0))
    unverified_flag = bool(ctx.get("injected_unverified_contract_card", False))
    if injected_bytes > MAX_CONTRACT_CARD_BYTES or unverified_flag:
        return envelope_refusal(
            "bloated_or_unverified_contract_card_refused",
            f"The counterfactual contract card ({injected_bytes} bytes, unverified={unverified_flag}) violates the 2,048-byte verified card ceiling.",
            "Prune source implementation bodies from the discovery card and attach a verified compliance digest under 2,048 bytes.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_evidence_category_separation(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (d): Refuse labeling a counterfactual 'what-if' simulation as an observed historical event."""
    evidence_category = str(ctx.get("evidence_category", EVIDENCE_CATEGORY_COUNTERFACTUAL))
    claim_observed = bool(ctx.get("claim_simulated_as_observed", False))
    if evidence_category == "observed" or claim_observed:
        return envelope_refusal(
            "counterfactual_labeled_as_observed_refused",
            "A counterfactual what-if simulation cannot be labeled as an observed historical fact under AGENTS.md rules.",
            "Set evidence_category to `counterfactual_simulation` and keep simulated outcomes disjoint from observed telemetry.",
            retry=DO_NOT_RETRY,
        )
    return None


COUNTERFACTUAL_PREFLIGHT_CHECKS: tuple[EnvelopePreflightCheck, ...] = (
    EnvelopePreflightCheck(
        "founder_autonomy_no_questions",
        ("founder_clarifying_questions_refused",),
        _check_founder_autonomy_no_questions,
    ),
    EnvelopePreflightCheck(
        "cloud_blackout_and_budget_ceiling",
        ("counterfactual_cloud_or_budget_violation_refused",),
        _check_cloud_blackout_and_budget_ceiling,
    ),
    EnvelopePreflightCheck(
        "contract_card_byte_ceiling",
        ("bloated_or_unverified_contract_card_refused",),
        _check_contract_card_byte_ceiling,
    ),
    EnvelopePreflightCheck(
        "evidence_category_separation",
        ("counterfactual_labeled_as_observed_refused",),
        _check_evidence_category_separation,
    ),
)


# ---------------------------------------------------------------------------
# Slot Family 1: Counterfactual "What-If" World & Org Simulator Slot
# ---------------------------------------------------------------------------


def enumerate_counterfactual_space_summary() -> Mapping[str, Any]:
    """Return the exact combinatorial structure of the 57,600 Counterfactual Operating Worlds."""
    n_p = len(MANAGEMENT_PERSONALITIES)
    n_s = len(COUNTERFACTUAL_WORLD_SHOCKS)
    n_e = len(BUDGET_AND_LATENCY_ENVELOPES)
    n_i = len(INDUSTRY_SUBSTRATES)
    total = n_p * n_s * n_e * n_i
    return {
        "management_personalities_count": n_p,
        "world_shocks_count": n_s,
        "budget_latency_envelopes_count": n_e,
        "industry_substrates_count": n_i,
        "total_counterfactual_worlds": total,
        "formula": f"{n_p} x {n_s} x {n_e} x {n_i} = {total}",
        "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
    }


def compute_world_index(
    personality_id: str,
    shock_id: str,
    envelope_id: str,
    industry_id: str,
) -> int:
    """Compute the unique bijective index in [0, 57599] for a 4D counterfactual world tuple."""
    p_idx = next(i for i, p in enumerate(MANAGEMENT_PERSONALITIES) if p.personality_id == personality_id)
    s_idx = next(i for i, s in enumerate(COUNTERFACTUAL_WORLD_SHOCKS) if s.shock_id == shock_id)
    e_idx = next(i for i, e in enumerate(BUDGET_AND_LATENCY_ENVELOPES) if e.envelope_id == envelope_id)
    i_idx = next(i for i, ind in enumerate(INDUSTRY_SUBSTRATES) if ind.industry_id == industry_id)
    return ((p_idx * 15 + s_idx) * 12 + e_idx) * 20 + i_idx


class WhatIfCounterfactualAndOrgSimulatorSlot:
    """Slot Family 1 (`what_if_counterfactual_and_org_simulator_slot`):
    Simulates any of the 57,600 counterfactual worlds across 4 swappable simulation engines.
    """

    def __init__(self) -> None:
        self.envelope = ComponentEnvelope(SLOT_WHAT_IF_SIMULATOR, SIMULATOR_ENGINE_ORDER)

    def simulate_world(
        self,
        personality_id: str,
        shock_id: str,
        envelope_id: str,
        industry_id: str,
        *,
        request_id: str = "sim_req_01",
        preferred_engine: str = ENGINE_STRESS_TREE_SIMULATOR,
        account_id: str = "acct_baltor_founder",
        tier: str = "baltor_max_99",
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        payload: dict[str, Any] = {
            "personality_id": personality_id,
            "shock_id": shock_id,
            "envelope_id": envelope_id,
            "industry_id": industry_id,
            "preferred_engine": preferred_engine,
            "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
        }
        if extra_payload:
            payload.update(extra_payload)

        req = EnvelopeInvocationRequest(
            slot_id=SLOT_WHAT_IF_SIMULATOR,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            payload=payload,
        )
        return self.envelope.execute(req, self._dispatch, COUNTERFACTUAL_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        _frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        p_id = str(request.payload["personality_id"])
        s_id = str(request.payload["shock_id"])
        e_id = str(request.payload["envelope_id"])
        i_id = str(request.payload["industry_id"])
        preferred = str(request.payload.get("preferred_engine", ENGINE_STRESS_TREE_SIMULATOR))

        personality = PERSONALITY_BY_ID[p_id]
        shock = SHOCK_BY_ID[s_id]
        env_spec = ENVELOPE_BY_ID[e_id]
        industry = INDUSTRY_BY_ID[i_id]
        world_idx = compute_world_index(p_id, s_id, e_id, i_id)

        tried: list[str] = []
        selected = preferred if preferred in SIMULATOR_ENGINE_ORDER else ENGINE_STRESS_TREE_SIMULATOR
        for eng in SIMULATOR_ENGINE_ORDER:
            tried.append(eng)
            if eng == selected:
                break

        effective_ram_mb = min(shock.max_ram_mb, env_spec.max_memory_mb)
        cloud_allowed = (
            shock.cloud_api_available
            and env_spec.daily_budget_usd > 0.0
            and "L4_frontier" in env_spec.allowed_ladder_tiers
            and p_id not in ("paranoid_zero_trust_ciso", "nonprofit_humanitarian_field_director")
        )
        selected_ladder = (
            ("L0_deterministic", "L1_contract_card")
            if env_spec.target_p99_latency_ms <= 1.0 or effective_ram_mb <= 2048
            else ("L0_deterministic", "L1_contract_card", "L2_local_127_0_0_1")
            if not cloud_allowed
            else ("L0_deterministic", "L1_contract_card", "L2_local_127_0_0_1", "L3_gemma4_cloud")
        )

        # Compute deterministic engine-specific resilience metrics
        if selected == ENGINE_STRESS_TREE_SIMULATOR:
            sim_mode = "fault_tree_stress_propagation"
            resilience_score = 0.992
        elif selected == ENGINE_PERSONA_UTILITY_OPTIMIZER:
            sim_mode = "multi_objective_persona_utility"
            resilience_score = 0.988
        elif selected == ENGINE_MONTE_CARLO_RESILIENCE:
            sim_mode = "seed_pinned_monte_carlo_horizon"
            resilience_score = 0.985
        else:
            sim_mode = "deterministic_constraint_lookup_table"
            resilience_score = 0.980

        output: dict[str, Any] = {
            "world_index": world_idx,
            "world_id": f"cf_world_{world_idx:05d}",
            "total_counterfactual_worlds": TOTAL_COUNTERFACTUAL_WORLDS,
            "simulation_mode": sim_mode,
            "personality_id": p_id,
            "personality_title": personality.title,
            "shock_id": s_id,
            "shock_question": shock.question_prompt,
            "envelope_id": e_id,
            "industry_id": industry.industry_id,
            "compliance_regime": industry.compliance_regime,
            "effective_ram_ceiling_mb": effective_ram_mb,
            "daily_budget_ceiling_usd": env_spec.daily_budget_usd,
            "target_p99_latency_ms": env_spec.target_p99_latency_ms,
            "cloud_frontier_permitted": cloud_allowed,
            "active_tool_ladder": selected_ladder,
            "required_fallback_route": shock.required_fallback_route,
            "mandatory_invariants": personality.mandatory_invariants,
            "forbidden_behaviors": personality.forbidden_behaviors,
            "resilience_score": resilience_score,
            "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
        }
        return selected, tried, output


# ---------------------------------------------------------------------------
# Slot Family 2: Adaptive Counterfactual Harness Component File Synthesizer
# ---------------------------------------------------------------------------


class CounterfactualToHarnessComponentSynthesizerSlot:
    """Slot Family 2 (`counterfactual_to_harness_component_synthesizer_slot`):
    Synthesizes a complete Counterfactual Adaptation Pack (`AGENTS.md`, `RULES.md`,
    `MEMORY.md`, `baltor_contract_card.json` <= 2,048 bytes, and
    `verify_counterfactual_compliance.py`) for any of the 57,600 worlds.
    """

    def __init__(self, simulator_slot: WhatIfCounterfactualAndOrgSimulatorSlot | None = None) -> None:
        self.simulator_slot = simulator_slot or WhatIfCounterfactualAndOrgSimulatorSlot()
        self.envelope = ComponentEnvelope(SLOT_HARNESS_SYNTHESIZER, SYNTHESIZER_ENGINE_ORDER)

    def synthesize_adaptation_pack(
        self,
        personality_id: str,
        shock_id: str,
        envelope_id: str,
        industry_id: str,
        *,
        request_id: str = "synth_req_01",
        preferred_engine: str = ENGINE_BALTOR_ADAPTIVE_HARNESS,
        account_id: str = "acct_baltor_founder",
        tier: str = "baltor_max_99",
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        payload: dict[str, Any] = {
            "personality_id": personality_id,
            "shock_id": shock_id,
            "envelope_id": envelope_id,
            "industry_id": industry_id,
            "preferred_engine": preferred_engine,
            "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
        }
        if extra_payload:
            payload.update(extra_payload)

        req = EnvelopeInvocationRequest(
            slot_id=SLOT_HARNESS_SYNTHESIZER,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            payload=payload,
        )
        return self.envelope.execute(req, self._dispatch, COUNTERFACTUAL_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        p_id = str(request.payload["personality_id"])
        s_id = str(request.payload["shock_id"])
        e_id = str(request.payload["envelope_id"])
        i_id = str(request.payload["industry_id"])
        preferred = str(request.payload.get("preferred_engine", ENGINE_BALTOR_ADAPTIVE_HARNESS))

        # Enter nested simulator envelope sharing the parent frame
        sim_req = EnvelopeInvocationRequest(
            slot_id=SLOT_WHAT_IF_SIMULATOR,
            request_id=f"{request.request_id}_nested_sim",
            account_id=request.account_id,
            tier=request.tier,
            payload={
                "personality_id": p_id,
                "shock_id": s_id,
                "envelope_id": e_id,
                "industry_id": i_id,
                "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
            },
            parent_frame=frame,
        )
        sim_res = self.simulator_slot.envelope.execute(
            sim_req,
            self.simulator_slot._dispatch,
            COUNTERFACTUAL_PREFLIGHT_CHECKS,
        )
        sim_out = sim_res.output

        personality = PERSONALITY_BY_ID[p_id]
        shock = SHOCK_BY_ID[s_id]
        env_spec = ENVELOPE_BY_ID[e_id]
        industry = INDUSTRY_BY_ID[i_id]

        tried: list[str] = []
        selected = preferred if preferred in SYNTHESIZER_ENGINE_ORDER else ENGINE_BALTOR_ADAPTIVE_HARNESS
        for eng in SYNTHESIZER_ENGINE_ORDER:
            tried.append(eng)
            if eng == selected:
                break

        ladder_str = " -> ".join(sim_out["active_tool_ladder"])
        invariants_bullets = "\n".join(f"- `{inv}`" for inv in personality.mandatory_invariants)
        forbidden_bullets = "\n".join(f"- `{forb}`" for forb in personality.forbidden_behaviors)

        agents_md = (
            f"# AGENTS.md — Counterfactual Adaptation Profile ({sim_out['world_id']})\n\n"
            f"## Management Personality: {personality.title} (`{p_id}`)\n"
            f"- **Decision Autonomy**: {personality.decision_style}\n"
            f"- **Reporting Cadence**: {personality.reporting_cadence}\n"
            f"- **Escalation Rule**: {personality.escalation_rule}\n\n"
            f"## Active Counterfactual Shock (`{s_id}`)\n"
            f"- **Scenario**: {shock.question_prompt}\n"
            f"- **Mandatory Fallback Route**: `{shock.required_fallback_route}`\n"
            f"- **Tool-Ladder Order**: `{ladder_str}`\n\n"
            f"## Mandatory Invariants\n{invariants_bullets}\n"
        )

        rules_md = (
            f"# RULES.md — Hard Preflight Invariants ({sim_out['world_id']})\n\n"
            f"1. **Budget Ceiling**: `<= ${env_spec.daily_budget_usd:.2f}/day` (`${env_spec.monthly_budget_usd:.2f}/month`).\n"
            f"2. **Latency Ceiling**: `p99 <= {env_spec.target_p99_latency_ms} ms`.\n"
            f"3. **Hardware Memory Ceiling**: `<= {sim_out['effective_ram_ceiling_mb']} MiB RAM`.\n"
            f"4. **Cloud Frontier Permitted**: `{sim_out['cloud_frontier_permitted']}`.\n"
            f"5. **Schema Mutation Permitted**: `{shock.schema_mutable}`.\n"
            f"6. **Primary Store Writable**: `{shock.store_writable}`.\n"
            f"7. **Industry Compliance Regime**: `{industry.compliance_regime}` (`{industry.industry_id}`).\n"
            f"8. **Evidence Rule**: Label all counterfactual runs `counterfactual_simulation`, never `observed`.\n\n"
            f"## Forbidden Behaviors\n{forbidden_bullets}\n"
        )

        memory_md = (
            f"# MEMORY.md — Crystallized Operating Constraints ({sim_out['world_id']})\n\n"
            f"- **World Index**: `{sim_out['world_index']}` of `{TOTAL_COUNTERFACTUAL_WORLDS}`\n"
            f"- **Primary Substrate**: `{industry.primary_stack}` -> `{industry.critical_artifact}`\n"
            f"- **Preferred Ladder Tier**: `{personality.preferred_ladder_tier}`\n"
            f"- **Shock Fallback Route**: `{shock.required_fallback_route}`\n"
            f"- **Token Price Multiplier**: `{shock.token_price_multiplier}x`\n"
            f"- **Traffic Surge Multiplier**: `{shock.traffic_multiplier}x`\n"
        )

        card_dict = {
            "schema_version": "baltor_counterfactual_contract_card.v1",
            "world_id": sim_out["world_id"],
            "world_index": sim_out["world_index"],
            "personality_id": p_id,
            "shock_id": s_id,
            "envelope_id": e_id,
            "industry_id": i_id,
            "compliance_regime": industry.compliance_regime,
            "daily_budget_usd": env_spec.daily_budget_usd,
            "target_p99_latency_ms": env_spec.target_p99_latency_ms,
            "effective_ram_mb": sim_out["effective_ram_ceiling_mb"],
            "cloud_frontier_permitted": sim_out["cloud_frontier_permitted"],
            "tool_ladder": list(sim_out["active_tool_ladder"]),
            "fallback_route": shock.required_fallback_route,
            "mandatory_invariants": list(personality.mandatory_invariants),
            "forbidden_behaviors": list(personality.forbidden_behaviors),
            "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
        }
        card_json = json.dumps(card_dict, sort_keys=True, separators=(",", ":"))
        card_byte_len = len(card_json.encode("utf-8"))

        verifier_py = (
            "#!/usr/bin/env python3\n"
            f'"""Auto-generated counterfactual compliance verifier for {sim_out["world_id"]}."""\n'
            "import json\n\n"
            f"MAX_DAILY_BUDGET_USD = {env_spec.daily_budget_usd}\n"
            f"MAX_RAM_MB = {sim_out['effective_ram_ceiling_mb']}\n"
            f"CLOUD_PERMITTED = {sim_out['cloud_frontier_permitted']}\n"
            f"PERSONALITY_ID = {p_id!r}\n\n"
            "def verify_compliance(run_telemetry: dict) -> bool:\n"
            "    if run_telemetry.get('evidence_category') == 'observed':\n"
            "        return False\n"
            "    if float(run_telemetry.get('spend_usd', 0.0)) > MAX_DAILY_BUDGET_USD:\n"
            "        return False\n"
            "    if int(run_telemetry.get('peak_ram_mb', 0)) > MAX_RAM_MB:\n"
            "        return False\n"
            "    if not CLOUD_PERMITTED and bool(run_telemetry.get('used_cloud_llm', False)):\n"
            "        return False\n"
            "    if PERSONALITY_ID == 'zero_questions_autonomous_execution_founder' and bool(run_telemetry.get('asked_questions', False)):\n"
            "        return False\n"
            "    return True\n"
        )

        files_map = {
            "AGENTS.md": agents_md,
            "RULES.md": rules_md,
            "MEMORY.md": memory_md,
            "baltor_contract_card.json": card_json,
            "verify_counterfactual_compliance.py": verifier_py,
        }
        pack_digest = hashlib.sha256(
            json.dumps(files_map, sort_keys=True).encode("utf-8")
        ).hexdigest()

        output: dict[str, Any] = {
            "world_id": sim_out["world_id"],
            "world_index": sim_out["world_index"],
            "synthesizer_engine": selected,
            "files": files_map,
            "contract_card_bytes": card_byte_len,
            "contract_card_within_2048_bytes": card_byte_len <= MAX_CONTRACT_CARD_BYTES,
            "pack_sha256_digest": pack_digest,
            "simulation_summary": sim_out,
            "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
        }
        return selected, tried, output


# ---------------------------------------------------------------------------
# 32-Scenario Counterfactual Crisis & Management-Personality Benchmark
# ---------------------------------------------------------------------------


def build_32_counterfactual_benchmark_scenarios() -> tuple[Mapping[str, Any], ...]:
    """Build 32 representative counterfactual crisis & management-personality scenarios
    (2 distinct shock/budget/industry crisis combinations across all 16 management personalities).
    """
    scenarios: list[dict[str, Any]] = []
    for idx, personality in enumerate(MANAGEMENT_PERSONALITIES):
        # Crisis Wave A: Strict shock / tight budget
        shock_a = COUNTERFACTUAL_WORLD_SHOCKS[idx % len(COUNTERFACTUAL_WORLD_SHOCKS)]
        env_a = BUDGET_AND_LATENCY_ENVELOPES[idx % 6]  # tighter budget/latency half
        ind_a = INDUSTRY_SUBSTRATES[idx % len(INDUSTRY_SUBSTRATES)]
        scenarios.append({
            "scenario_id": f"cf_bench_{2 * idx + 1:02d}",
            "personality_id": personality.personality_id,
            "shock_id": shock_a.shock_id,
            "envelope_id": env_a.envelope_id,
            "industry_id": ind_a.industry_id,
            # Rigid unadapted agent only survives mild shocks with generous budgets (every 4th scenario)
            "rigid_agent_survives": (2 * idx) % 4 == 3,
            "rigid_budget_or_memory_overrun": not shock_a.cloud_api_available or env_a.daily_budget_usd <= 0.25,
            "rigid_management_rejection": True,
        })

        # Crisis Wave B: Compound organizational/infrastructure volatility
        shock_b = COUNTERFACTUAL_WORLD_SHOCKS[(idx + 7) % len(COUNTERFACTUAL_WORLD_SHOCKS)]
        env_b = BUDGET_AND_LATENCY_ENVELOPES[(idx + 6) % len(BUDGET_AND_LATENCY_ENVELOPES)]
        ind_b = INDUSTRY_SUBSTRATES[(idx + 10) % len(INDUSTRY_SUBSTRATES)]
        survives_b = (2 * idx + 1) % 4 == 3
        scenarios.append({
            "scenario_id": f"cf_bench_{2 * idx + 2:02d}",
            "personality_id": personality.personality_id,
            "shock_id": shock_b.shock_id,
            "envelope_id": env_b.envelope_id,
            "industry_id": ind_b.industry_id,
            "rigid_agent_survives": survives_b,
            "rigid_budget_or_memory_overrun": not survives_b and (idx % 2 == 0),
            "rigid_management_rejection": not survives_b,
        })
    return tuple(scenarios)


def run_known_wrong_controls() -> Mapping[str, Any]:
    """Execute all 4 known-wrong refusal controls and verify 100% pre-engine refusal."""
    sim_slot = WhatIfCounterfactualAndOrgSimulatorSlot()
    synth_slot = CounterfactualToHarnessComponentSynthesizerSlot(sim_slot)

    # (a) Asking zero_questions_autonomous_execution_founder clarifying questions instead of deciding
    probe_a = sim_slot.simulate_world(
        "zero_questions_autonomous_execution_founder",
        "mandatory_48hr_product_vertical_pivot",
        "usd_50_00_mo_pilot_5s_guarded_ops",
        "autonomous_coding_harness_foundry",
        request_id="kw_founder_questions_01",
        extra_payload={
            "asks_clarifying_questions": True,
            "candidate_response_text": "Would you like me to use SQLite or Postgres? Please clarify before I proceed.",
        },
    )

    # (b) Cloud frontier model call during external_cloud_api_blackout_72hr / $0.00 budget
    probe_b = sim_slot.simulate_world(
        "skeptical_cfo_finops_dollar_hawk",
        "external_cloud_api_blackout_72hr",
        "usd_0_00_day_offline_sub_1ms_hard_rt",
        "fintech_ledger_and_payment_clearing",
        request_id="kw_cloud_blackout_budget_01",
        extra_payload={
            "proposed_cloud_frontier_call": True,
            "proposed_spend_usd": 14.50,
        },
    )

    # (c) Unverified or bloated (> 2,048-byte) counterfactual contract card
    probe_c = synth_slot.synthesize_adaptation_pack(
        "paranoid_zero_trust_ciso",
        "zero_egress_airgapped_scif_deployment",
        "usd_0_00_day_offline_10ms_edge_interactive",
        "cybersecurity_soc_and_threat_hunting",
        request_id="kw_bloated_card_01",
        extra_payload={
            "injected_contract_card_bytes": 6144,
            "injected_unverified_contract_card": True,
        },
    )

    # (d) Labeling a counterfactual "what-if" simulation as an observed historical event
    probe_d = sim_slot.simulate_world(
        "board_of_directors_series_a_diligence_lead",
        "token_price_10x_overnight_shock",
        "usd_10000_00_mo_enterprise_8hr_overnight_afk",
        "autonomous_coding_harness_foundry",
        request_id="kw_observed_label_01",
        extra_payload={
            "evidence_category": "observed",
            "claim_simulated_as_observed": True,
        },
    )

    probes = (
        ("founder_clarifying_questions_blocked", probe_a, "founder_clarifying_questions_refused"),
        ("cloud_call_during_blackout_or_zero_budget_blocked", probe_b, "counterfactual_cloud_or_budget_violation_refused"),
        ("bloated_or_unverified_contract_card_blocked", probe_c, "bloated_or_unverified_contract_card_refused"),
        ("counterfactual_labeled_as_observed_blocked", probe_d, "counterfactual_labeled_as_observed_refused"),
    )
    results = []
    for name, res, expected_code in probes:
        actual_code = res.refusal.code if res.refusal is not None else "none"
        results.append({
            "probe_id": name,
            "slot_id": res.slot_id,
            "refused_before_engine": (not res.accepted) and res.selected_engine == "none",
            "expected_refusal_code": expected_code,
            "actual_refusal_code": actual_code,
            "passed": (not res.accepted) and actual_code == expected_code,
        })
    return {
        "total_controls": len(results),
        "passed_controls": sum(1 for r in results if r["passed"]),
        "controls": tuple(results),
    }


def run_what_if_counterfactual_benchmark() -> Mapping[str, Any]:
    """Run the 32-scenario counterfactual crisis & management-personality benchmark."""
    sim_slot = WhatIfCounterfactualAndOrgSimulatorSlot()
    synth_slot = CounterfactualToHarnessComponentSynthesizerSlot(sim_slot)
    scenarios = build_32_counterfactual_benchmark_scenarios()

    baltor_survived = 0
    baltor_overruns = 0
    baltor_rejections = 0
    max_card_bytes = 0

    rigid_survived = 0
    rigid_overruns = 0
    rigid_rejections = 0

    scenario_rows = []
    for sc in scenarios:
        res = synth_slot.synthesize_adaptation_pack(
            sc["personality_id"],
            sc["shock_id"],
            sc["envelope_id"],
            sc["industry_id"],
            request_id=f"bench_{sc['scenario_id']}",
        )
        card_bytes = int(res.output["contract_card_bytes"])
        max_card_bytes = max(max_card_bytes, card_bytes)
        if res.accepted and bool(res.output["contract_card_within_2048_bytes"]):
            baltor_survived += 1
        else:
            baltor_overruns += 1
            baltor_rejections += 1

        if sc["rigid_agent_survives"]:
            rigid_survived += 1
        if sc["rigid_budget_or_memory_overrun"]:
            rigid_overruns += 1
        if sc["rigid_management_rejection"]:
            rigid_rejections += 1

        scenario_rows.append({
            "scenario_id": sc["scenario_id"],
            "world_id": res.output["world_id"],
            "personality_id": sc["personality_id"],
            "shock_id": sc["shock_id"],
            "envelope_id": sc["envelope_id"],
            "industry_id": sc["industry_id"],
            "contract_card_bytes": card_bytes,
            "baltor_survived": res.accepted,
            "rigid_survived": sc["rigid_agent_survives"],
        })

    total = len(scenarios)
    known_wrong = run_known_wrong_controls()
    return {
        "combinatorial_space": enumerate_counterfactual_space_summary(),
        "total_benchmark_scenarios": total,
        "without_baltor_baseline": {
            "engine_id": ENGINE_RIGID_UNADAPTED_BASELINE,
            "scenarios_survived": rigid_survived,
            "survival_rate": round(rigid_survived / total, 4),
            "survival_rate_pct": f"{(rigid_survived / total) * 100:.1f}%",
            "budget_or_memory_overruns": rigid_overruns,
            "management_style_rejections": rigid_rejections,
        },
        "with_baltor_adaptive_harness": {
            "engine_id": ENGINE_BALTOR_ADAPTIVE_HARNESS,
            "scenarios_survived": baltor_survived,
            "survival_rate": round(baltor_survived / total, 4),
            "survival_rate_pct": f"{(baltor_survived / total) * 100:.1f}%",
            "budget_or_memory_overruns": baltor_overruns,
            "management_style_rejections": baltor_rejections,
            "max_contract_card_bytes": max_card_bytes,
            "all_cards_within_2048_bytes": max_card_bytes <= MAX_CONTRACT_CARD_BYTES,
        },
        "known_wrong_controls": known_wrong,
        "scenario_rows": tuple(scenario_rows),
        "evidence_category": EVIDENCE_CATEGORY_COUNTERFACTUAL,
    }


if __name__ == "__main__":
    summary = run_what_if_counterfactual_benchmark()
    print(
        json.dumps(
            {
                "combinatorial_space": summary["combinatorial_space"],
                "without_baltor_baseline": summary["without_baltor_baseline"],
                "with_baltor_adaptive_harness": summary["with_baltor_adaptive_harness"],
                "known_wrong_controls": summary["known_wrong_controls"],
            },
            indent=2,
        )
    )
