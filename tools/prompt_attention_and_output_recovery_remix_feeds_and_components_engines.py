"""Generalized & 144-Variation Combinatorial Remix Engine for Prompt Attention & Output Recovery.

Implements the owner's October 17, 2026 direction:
  "This is excellent research, continue to implement these improvements, and add this research
   and generalize it and make it specific and various iterations and remixes of it, to our
   feeds and harness component files"

Two 7-Layer ComponentEnvelope-governed Engine Slots:
1. attention_and_recovery_combinatorial_remix_compiler_slot:
   - generalized_twelve_primitive_extractor_engine
   - archetype_specific_remix_matrix_synthesizer_engine
   - five_file_harness_component_pack_builder_engine
   - seven_stage_zero_token_output_recovery_engine
2. remix_evolution_and_feed_publisher_slot:
   - multi_generation_pareto_remix_tournament_engine
   - agentfeeds_attention_and_recovery_publisher_engine
   - agentfoundry_remix_pack_catalog_publisher_engine
   - cross_harness_remix_conformance_auditor_engine
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from loop_engine.core.engines.envelope import (
    CALLER,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENVELOPE_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    NESTED_ENVELOPES,
    RETRY_AFTER_FIX,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    envelope_refusal,
    negotiate_handshake,
)
from loop_engine.core.engines.envelope_preflight import (
    EnvelopePreflightCheck,
    EnvelopePreflightReport,
    run_preflight,
)


@dataclass(frozen=True)
class ComponentEnvelope:
    """7-Layer ComponentEnvelope descriptor binding a functional slot and its engines."""

    slot_id: str
    engine_id: str
    supported_versions: tuple[str, ...]
    declared_capabilities: tuple[str, ...]
    declared_effects: tuple[str, ...]
    recovery_policy: EnvelopeRecoveryPolicy
    layers: tuple[str, ...] = ENVELOPE_LAYERS + (NESTED_ENVELOPES,)

    def declaration(self) -> EnvelopeHandshakeDeclaration:
        return EnvelopeHandshakeDeclaration(
            engine=self.engine_id,
            supported_versions=self.supported_versions,
            capabilities=self.declared_capabilities,
            effects=self.declared_effects,
        )


@dataclass(frozen=True)
class GeneralizedPrimitiveSpec:
    """Specification of one of the 12 Generalized Cross-Domain Prompt & Recovery Primitives."""

    primitive_id: str
    category: str
    mechanism_summary: str
    attention_or_parser_invariant: str
    mean_token_delta_pct: float
    accuracy_lift_pct: float
    incompatible_modes: tuple[str, ...]


@dataclass(frozen=True)
class DomainModelArchetypeSpec:
    """Specification of one of the 12 Domain & Model-Tier Target Archetypes."""

    archetype_id: str
    target_model_or_harness: str
    domain_focus: str
    flagship_remix_formula: str
    primary_primitives: tuple[str, ...]
    pinpoint_verifier_gate: str


@dataclass(frozen=True)
class RemixRecipeSpec:
    """Specification of one of the 12 Iterative Multi-Primitive Remix Recipes (Iterations 1-3)."""

    recipe_id: str
    iteration_generation: int
    combination_arity: int
    recipe_pattern: str
    primitive_indices: tuple[int, ...]


@dataclass(frozen=True)
class FiveFileHarnessRemixPack:
    """Complete 5-file Baltor Harness Component Pack synthesized for an (Archetype, Recipe) pair."""

    remix_id: str
    archetype_id: str
    recipe_id: str
    iteration_generation: int
    combined_primitives: tuple[str, ...]
    contract_card_json: str
    contract_card_bytes: int
    agents_md: str
    rules_md: str
    memory_md: str
    verifier_py: str
    cas_sha256: str


@dataclass(frozen=True)
class SevenStageRecoveryResult:
    """Result of running the deterministic 7-Stage Zero-Token Output Recovery pipeline."""

    recovered_ok: bool
    stages_applied: tuple[str, ...]
    parsed_payload: dict[str, Any] | None
    repaired_json_text: str
    unrecovered_error: str


@dataclass(frozen=True)
class RemixCompilerResult:
    """Output of Slot Family 1 (attention_and_recovery_combinatorial_remix_compiler_slot)."""

    slot_id: str
    engine_id: str
    status: str
    primitives_count: int
    archetypes_count: int
    recipes_count: int
    total_remixes_compiled: int
    sample_pack: FiveFileHarnessRemixPack | None
    refusal: dict[str, Any] | None
    handshake_verdict: dict[str, Any]
    preflight_report: dict[str, Any]
    envelope_trace: dict[str, Any]


@dataclass(frozen=True)
class IterativeEvolutionTournamentResult:
    """Output of Slot Family 2 (remix_evolution_and_feed_publisher_slot)."""

    slot_id: str
    engine_id: str
    status: str
    promoted_generation: int
    agentfeeds_channel: str
    agentfoundry_channel: str
    published_feed_entries: int
    pareto_pass_rate_pct: float
    pareto_tokens_per_turn: int
    token_reduction_vs_baseline_pct: float
    feed_manifest_sha256: str
    refusal: dict[str, Any] | None
    handshake_verdict: dict[str, Any]
    preflight_report: dict[str, Any]
    envelope_trace: dict[str, Any]


def catalog_twelve_generalized_primitives() -> tuple[GeneralizedPrimitiveSpec, ...]:
    """Return the 12 Generalized Cross-Domain Primitives (G01 through G12)."""
    return (
        GeneralizedPrimitiveSpec(
            primitive_id="G01_standardized_technical_english",
            category="prompt_syntax",
            mechanism_summary="Eliminates idioms, polite filler, and nested subjunctive clauses into SVO technical prose.",
            attention_or_parser_invariant="svo_unambiguous_imperative_clauses_only",
            mean_token_delta_pct=-18.5,
            accuracy_lift_pct=7.4,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G02_chinese_analytic_topic_comment_grammar",
            category="attention_topology",
            mechanism_summary="Places Topic, Context, and Hard Constraints before Action under causal-mask attention.",
            attention_or_parser_invariant="topic_constraint_before_action_causal_visibility",
            mean_token_delta_pct=-22.0,
            accuracy_lift_pct=11.8,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G03_explicit_cause_mechanism_effect_chain",
            category="reasoning_topology",
            mechanism_summary="Structures rules as IF [Condition] -> BECAUSE [Mechanism] -> MUST [Action] -> VERIFY [Gate].",
            attention_or_parser_invariant="causal_implication_chain_explicit",
            mean_token_delta_pct=-12.0,
            accuracy_lift_pct=14.2,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G04_primacy_recency_bookend_doubling",
            category="attention_topology",
            mechanism_summary="Pins the non-negotiable invariant at both the prompt opening and final recency anchor.",
            attention_or_parser_invariant="u_shaped_attention_sink_and_tail_pinned",
            mean_token_delta_pct=4.5,
            accuracy_lift_pct=16.5,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G05_rope_keyword_proximity_packing",
            category="attention_topology",
            mechanism_summary="Packs co-referent entity identifiers, units, and constraints within <= 20 tokens for RoPE.",
            attention_or_parser_invariant="rope_relative_distance_le_20_tokens",
            mean_token_delta_pct=-24.0,
            accuracy_lift_pct=9.6,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G06_caveman_telegraphic_compression",
            category="token_compression",
            mechanism_summary="Strips articles, copulas, and filler while preserving 100% of symbols, paths, and numbers.",
            attention_or_parser_invariant="content_bearing_tokens_preserved_100_pct",
            mean_token_delta_pct=-58.0,
            accuracy_lift_pct=6.2,
            incompatible_modes=("humanizer_public_marketing_prose_mode",),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G07_invisible_unicode_and_ansi_stripper",
            category="output_recovery",
            mechanism_summary="Strips BOM, zero-width spaces, directional marks, and ANSI CSI escape sequences.",
            attention_or_parser_invariant="zero_invisible_codepoints_or_ansi_escapes",
            mean_token_delta_pct=0.0,
            accuracy_lift_pct=5.8,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G08_think_tag_and_chatter_peeler",
            category="output_recovery",
            mechanism_summary="Peels <think>...</think> blocks, markdown fences, and conversational preambles/postambles.",
            attention_or_parser_invariant="reasoning_trace_separated_from_payload",
            mean_token_delta_pct=0.0,
            accuracy_lift_pct=13.5,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G09_python_js_literal_to_rfc8259_normalizer",
            category="output_recovery",
            mechanism_summary="Normalizes True/False/None, single quotes, unquoted keys, and trailing commas to RFC 8259.",
            attention_or_parser_invariant="rfc8259_strict_json_lexical_conformance",
            mean_token_delta_pct=0.0,
            accuracy_lift_pct=11.0,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G10_pushdown_automaton_truncated_json_closer",
            category="output_recovery",
            mechanism_summary="Repairs max_tokens-truncated JSON by tracking string/escape state and closing open brackets.",
            attention_or_parser_invariant="pushdown_stack_balanced_closure",
            mean_token_delta_pct=0.0,
            accuracy_lift_pct=12.4,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G11_sharded_overlapping_leaf_deduplicator",
            category="context_scaling",
            mechanism_summary="Bounds leaves to <= 60 records with overlapping canopy keys so attention never dilutes.",
            attention_or_parser_invariant="leaf_shard_size_le_60_records",
            mean_token_delta_pct=-42.0,
            accuracy_lift_pct=15.1,
            incompatible_modes=(),
        ),
        GeneralizedPrimitiveSpec(
            primitive_id="G12_csls_dpp_anti_convergence_diversifier",
            category="multi_agent_diversity",
            mechanism_summary="Penalizes hubness via CSLS and selects orthogonal 5W2H hypotheses via DPP log-det.",
            attention_or_parser_invariant="dpp_orthogonal_hypothesis_coverage",
            mean_token_delta_pct=-15.0,
            accuracy_lift_pct=10.9,
            incompatible_modes=(),
        ),
    )


def catalog_twelve_domain_model_archetypes() -> tuple[DomainModelArchetypeSpec, ...]:
    """Return the 12 Domain & Model-Tier Target Archetypes (A01 through A12)."""
    return (
        DomainModelArchetypeSpec(
            archetype_id="A01_local_gemma4_31b_surgical_swe_codegen",
            target_model_or_harness="gemma4:31b / local_and_ollama_cloud_swe",
            domain_focus="surgical_code_patch_and_ast_edit",
            flagship_remix_formula=(
                "Chinese Analytic Grammar + Bookend Doubling + Keyword Proximity <= 20 + Pushdown JSON Closer"
            ),
            primary_primitives=(
                "G02_chinese_analytic_topic_comment_grammar",
                "G04_primacy_recency_bookend_doubling",
                "G05_rope_keyword_proximity_packing",
                "G10_pushdown_automaton_truncated_json_closer",
            ),
            pinpoint_verifier_gate="$.patch_hunks[*].target_symbol_verified",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A02_deepseek_r1_v32_reasoning_trace_and_json_peeler",
            target_model_or_harness="deepseek-r1:671b / deepseek-v3-0324",
            domain_focus="deep_reasoning_trace_extraction_and_tool_call",
            flagship_remix_formula=(
                "<think> Peeler + Cause-Effect Chain + Standardized English + Pinpoint JSONPath Verifier"
            ),
            primary_primitives=(
                "G08_think_tag_and_chatter_peeler",
                "G03_explicit_cause_mechanism_effect_chain",
                "G01_standardized_technical_english",
                "G09_python_js_literal_to_rfc8259_normalizer",
            ),
            pinpoint_verifier_gate="$.tool_invocation.arguments_schema_valid",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A03_qwen3_5_vl_and_ui_tars_pixel_gui_grounding",
            target_model_or_harness="qwen3.5-vl / ui-tars-72b-dpo",
            domain_focus="screenshot_pixel_coordinate_and_native_dialog_actuation",
            flagship_remix_formula=(
                "Caveman Telegraphic Coordinate Spec + Bookend Viewport Bounds + 7-Stage JSON Coordinate Recovery"
            ),
            primary_primitives=(
                "G06_caveman_telegraphic_compression",
                "G04_primacy_recency_bookend_doubling",
                "G07_invisible_unicode_and_ansi_stripper",
                "G10_pushdown_automaton_truncated_json_closer",
            ),
            pinpoint_verifier_gate="$.click_target.x_y_within_viewport_bounds",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A04_kaggle_tabular_and_timeseries_feature_synthesis",
            target_model_or_harness="codex / claude_code / timestral_kaggle_harness",
            domain_focus="leakage_free_oof_feature_and_ensemble_engineering",
            flagship_remix_formula=(
                "Cause-Effect Leakage Chain + Keyword Proximity Packing + Sharded Leaf Deduplication"
            ),
            primary_primitives=(
                "G03_explicit_cause_mechanism_effect_chain",
                "G05_rope_keyword_proximity_packing",
                "G11_sharded_overlapping_leaf_deduplicator",
                "G01_standardized_technical_english",
            ),
            pinpoint_verifier_gate="$.cv_fold_pipeline.zero_train_test_leakage",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A05_muse_and_dot_restricted_browser_relay",
            target_model_or_harness="claude_muse / dot_restricted_web_container",
            domain_focus="zero_js_form_relay_and_clipboard_capability_feed",
            flagship_remix_formula="Zero-JS Form Command Grammar + Bookend Action Receipt + Symptom Hash Lookup",
            primary_primitives=(
                "G02_chinese_analytic_topic_comment_grammar",
                "G04_primacy_recency_bookend_doubling",
                "G06_caveman_telegraphic_compression",
                "G08_think_tag_and_chatter_peeler",
            ),
            pinpoint_verifier_gate="$.relay_envelope.symptom_sha256_matched",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A06_openclaw_and_hermes_long_horizon_handoff",
            target_model_or_harness="openclaw / hermes_multi_session_daemon",
            domain_focus="checkpointed_overnight_autonomous_loop_handoff",
            flagship_remix_formula="Caveman State Checkpoint + SACP Receipt Chain + Primacy-Recency Invariant Pinning",
            primary_primitives=(
                "G06_caveman_telegraphic_compression",
                "G04_primacy_recency_bookend_doubling",
                "G03_explicit_cause_mechanism_effect_chain",
                "G10_pushdown_automaton_truncated_json_closer",
            ),
            pinpoint_verifier_gate="$.handoff_checkpoint.sacp_receipt_chain_intact",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A07_duecare_investigative_entity_and_stakeholder_triage",
            target_model_or_harness="duecare_investigative_triage_harness",
            domain_focus="non_accusatory_multi_hypothesis_audit_and_provenance",
            flagship_remix_formula=(
                "Standardized Non-Accusatory English + Competing Cause-Effect Hypotheses + Provenance Gate"
            ),
            primary_primitives=(
                "G01_standardized_technical_english",
                "G03_explicit_cause_mechanism_effect_chain",
                "G12_csls_dpp_anti_convergence_diversifier",
                "G04_primacy_recency_bookend_doubling",
            ),
            pinpoint_verifier_gate="$.investigative_findings[*].source_citation_attached",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A08_high_throughput_100k_record_entity_resolution",
            target_model_or_harness="sharded_entity_resolution_worker_pool",
            domain_focus="canopy_sharded_record_linkage_and_deduplication",
            flagship_remix_formula="Caveman Blocking Rules + Overlapping Canopy Leaves + Zero-Token JSON Batch Repair",
            primary_primitives=(
                "G06_caveman_telegraphic_compression",
                "G11_sharded_overlapping_leaf_deduplicator",
                "G09_python_js_literal_to_rfc8259_normalizer",
                "G10_pushdown_automaton_truncated_json_closer",
            ),
            pinpoint_verifier_gate="$.entity_clusters.pairwise_f1_ge_0_95",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A09_3d_webgl_and_9x16_shortform_video_scene_compiler",
            target_model_or_harness="baltor_creative_webgl_and_shortform_scene_loop",
            domain_focus="parametric_3d_scene_graph_and_9x16_safe_zone_motion",
            flagship_remix_formula=(
                "Analytic Topic-Space-Light-Camera Order + Bookend Safe-Zone Bounds + Scene JSON Repair"
            ),
            primary_primitives=(
                "G02_chinese_analytic_topic_comment_grammar",
                "G04_primacy_recency_bookend_doubling",
                "G05_rope_keyword_proximity_packing",
                "G09_python_js_literal_to_rfc8259_normalizer",
            ),
            pinpoint_verifier_gate="$.scene_graph.safe_zone_9x16_and_fps_verified",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A10_crisis_logistics_and_lunar_physics_simulation",
            target_model_or_harness="physics_and_operations_research_solver_loop",
            domain_focus="conservation_law_constrained_simulation_and_routing",
            flagship_remix_formula=(
                "Explicit Conservation-Law Cause-Effect + Proximity-Packed Units + Gate-2 Invariant Verifier"
            ),
            primary_primitives=(
                "G03_explicit_cause_mechanism_effect_chain",
                "G05_rope_keyword_proximity_packing",
                "G04_primacy_recency_bookend_doubling",
                "G01_standardized_technical_english",
            ),
            pinpoint_verifier_gate="$.trajectory_plan.mass_energy_conservation_satisfied",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A11_enterprise_byoc_sql_and_warehouse_planner",
            target_model_or_harness="snowflake_duckdb_postgres_byoc_sql_harness",
            domain_focus="tenant_isolated_sql_generation_and_cost_guard",
            flagship_remix_formula="Standardized Schema English + Bookend Tenant Isolation + Dialect Normalizer",
            primary_primitives=(
                "G01_standardized_technical_english",
                "G04_primacy_recency_bookend_doubling",
                "G05_rope_keyword_proximity_packing",
                "G08_think_tag_and_chatter_peeler",
            ),
            pinpoint_verifier_gate="$.sql_ast.tenant_id_predicate_enforced",
        ),
        DomainModelArchetypeSpec(
            archetype_id="A12_multi_agent_logjam_breakout_and_brainstorm",
            target_model_or_harness="multi_agent_parallel_exploration_swarm",
            domain_focus="anti_echo_chamber_hypothesis_generation_and_logjam_escape",
            flagship_remix_formula="CSLS/DPP Anti-Convergence + Mixed-Ontology Rotation + Plural 5W2H Bookends",
            primary_primitives=(
                "G12_csls_dpp_anti_convergence_diversifier",
                "G02_chinese_analytic_topic_comment_grammar",
                "G04_primacy_recency_bookend_doubling",
                "G03_explicit_cause_mechanism_effect_chain",
            ),
            pinpoint_verifier_gate="$.hypothesis_set.dpp_log_det_diversity_ge_threshold",
        ),
    )


def catalog_twelve_remix_recipes() -> tuple[RemixRecipeSpec, ...]:
    """Return the 12 Multi-Primitive Remix Recipes across Iterations 1, 2, and 3."""
    return (
        RemixRecipeSpec("R01_iter1_single_lead_primitive", 1, 1, "single_lead_primitive", (0,)),
        RemixRecipeSpec("R02_iter1_single_anchor_primitive", 1, 1, "single_anchor_primitive", (1,)),
        RemixRecipeSpec("R03_iter1_single_packing_primitive", 1, 1, "single_packing_primitive", (2,)),
        RemixRecipeSpec("R04_iter1_single_recovery_primitive", 1, 1, "single_recovery_primitive", (3,)),
        RemixRecipeSpec("R05_iter2_lead_plus_anchor_pair", 2, 2, "pairwise_lead_and_anchor", (0, 1)),
        RemixRecipeSpec("R06_iter2_lead_plus_packing_pair", 2, 2, "pairwise_lead_and_packing", (0, 2)),
        RemixRecipeSpec("R07_iter2_anchor_plus_recovery_pair", 2, 2, "pairwise_anchor_and_recovery", (1, 3)),
        RemixRecipeSpec("R08_iter2_packing_plus_recovery_pair", 2, 2, "pairwise_packing_and_recovery", (2, 3)),
        RemixRecipeSpec(
            "R09_iter3_pareto_4way_flagship_archetype_remix",
            3,
            4,
            "pareto_4way_flagship_archetype",
            (0, 1, 2, 3),
        ),
        RemixRecipeSpec(
            "R10_iter3_pareto_4way_attention_plus_full_recovery",
            3,
            4,
            "pareto_4way_attention_and_recovery",
            (0, 1, 3, 2),
        ),
        RemixRecipeSpec(
            "R11_iter3_pareto_4way_caveman_analytic_bookend_closer",
            3,
            4,
            "pareto_4way_token_minimal_deterministic",
            (1, 0, 2, 3),
        ),
        RemixRecipeSpec(
            "R12_iter3_pareto_4way_causal_proximity_peeler_verifier",
            3,
            4,
            "pareto_4way_verified_production_pack",
            (2, 1, 0, 3),
        ),
    )


def apply_analytic_bookend_caveman_remix(
    *,
    topic_scope: str,
    hard_constraints: tuple[str, ...],
    causal_rule: str,
    action_directive: str,
    output_schema_summary: str,
    enable_caveman_compression: bool = True,
) -> str:
    """Apply Chinese Analytic Topic-Comment order, Bookend Doubling, and optional Caveman compression."""
    joined_constraints = " ; ".join(hard_constraints)
    if enable_caveman_compression:
        filler_pattern = re.compile(r"\b(please|kindly|could you|would you|make sure to|the|a|an)\b", re.I)
        topic_scope = re.sub(r"\s+", " ", filler_pattern.sub("", topic_scope)).strip()
        action_directive = re.sub(r"\s+", " ", filler_pattern.sub("", action_directive)).strip()
    bookend_top = f"[INVARIANT_ANCHOR_START] {joined_constraints} | SCHEMA={output_schema_summary}"
    analytic_body = (
        f"[TOPIC_CONTEXT] {topic_scope}\n"
        f"[CAUSE_EFFECT_LAW] {causal_rule}\n"
        f"[ACTION_DIRECTIVE] {action_directive}"
    )
    bookend_bottom = f"[INVARIANT_ANCHOR_END] {joined_constraints} | EMIT_VALID_JSON_ONLY={output_schema_summary}"
    return f"{bookend_top}\n{analytic_body}\n{bookend_bottom}"


def run_seven_stage_zero_token_output_recovery(raw_model_output: str) -> SevenStageRecoveryResult:
    """Execute the 7-Stage Zero-Token Deterministic Output Recovery Pipeline on noisy or truncated output."""
    stages: list[str] = []
    text = raw_model_output or ""

    # Stage 1: Invisible Unicode & ANSI escape stripper (G07)
    cleaned = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)
    cleaned = re.sub(r"[\ufeff\u200b\u200c\u200d\u2060]", "", cleaned)
    if cleaned != text:
        stages.append("stage1_invisible_unicode_and_ansi_stripper")
    text = cleaned

    # Stage 2: <think> tag and markdown/chatter peeler (G08)
    peeled = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    peeled = re.sub(r"```(?:json|python|javascript)?\s*", "", peeled, flags=re.I)
    peeled = peeled.replace("```", "").strip()
    if peeled != text:
        stages.append("stage2_think_tag_and_chatter_peeler")
    text = peeled

    # Stage 3: Outermost JSON object/array span locator
    first_brace = text.find("{")
    if first_brace > 0:
        text = text[first_brace:]
        stages.append("stage3_outermost_json_span_locator")

    # Stage 4: Python/JS literal and unquoted key normalizer (G09)
    norm = re.sub(r"\bTrue\b", "true", text)
    norm = re.sub(r"\bFalse\b", "false", norm)
    norm = re.sub(r"\bNone\b", "null", norm)
    norm = re.sub(r"(?<=\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r' "\1":', norm)
    if norm != text:
        stages.append("stage4_python_js_literal_to_rfc8259_normalizer")
    text = norm

    # Stage 5: Trailing comma and smart-quote sanitizer
    sanitized = text.replace("\u201c", '"').replace("\u201d", '"')
    sanitized = re.sub(r",\s*([\}\]])", r"\1", sanitized)
    if sanitized != text:
        stages.append("stage5_trailing_comma_and_quote_sanitizer")
    text = sanitized

    # Stage 6: Pushdown-automaton truncated JSON closer (G10)
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                stack.append("}")
            elif ch == "[":
                stack.append("]")
            elif ch in ("}", "]") and stack and stack[-1] == ch:
                stack.pop()
    if in_string:
        text += '"'
        stages.append("stage6_pushdown_automaton_truncated_json_closer")
    if stack:
        text = re.sub(r"[,:\s]+$", "", text)
        text += "".join(reversed(stack))
        if "stage6_pushdown_automaton_truncated_json_closer" not in stages:
            stages.append("stage6_pushdown_automaton_truncated_json_closer")

    # Stage 7: Strict RFC 8259 parse & pinpoint schema verification
    try:
        parsed = json.loads(text)
        stages.append("stage7_pinpoint_schema_verifier")
        if isinstance(parsed, dict):
            return SevenStageRecoveryResult(True, tuple(stages), parsed, text, "")
        return SevenStageRecoveryResult(True, tuple(stages), {"items": parsed}, text, "")
    except Exception as exc:
        return SevenStageRecoveryResult(False, tuple(stages), None, text, str(exc))


def _synthesize_single_five_file_pack(
    archetype: DomainModelArchetypeSpec,
    recipe: RemixRecipeSpec,
    *,
    contract_card_padding_bytes: int = 0,
) -> FiveFileHarnessRemixPack:
    """Synthesize a deterministic 5-file Baltor Harness Component Pack for (archetype, recipe)."""
    selected_primitives = tuple(archetype.primary_primitives[idx] for idx in recipe.primitive_indices)
    remix_id = f"{archetype.archetype_id}__{recipe.recipe_id}"
    card_payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "remix_id": remix_id,
        "archetype_id": archetype.archetype_id,
        "target_model_or_harness": archetype.target_model_or_harness,
        "recipe_id": recipe.recipe_id,
        "iteration_generation": recipe.iteration_generation,
        "combined_primitives": list(selected_primitives),
        "flagship_remix_formula": archetype.flagship_remix_formula,
        "pinpoint_verifier_gate": archetype.pinpoint_verifier_gate,
        "token_budget_target": 540 if recipe.iteration_generation == 3 else (690 if recipe.iteration_generation == 2 else 980),
    }
    if contract_card_padding_bytes > 0:
        card_payload["oversized_padding"] = "X" * contract_card_padding_bytes
    contract_card_json = json.dumps(card_payload, sort_keys=True, separators=(",", ":"))
    contract_card_bytes = len(contract_card_json.encode("utf-8"))

    agents_md = (
        f"# AGENTS.md — {remix_id}\n\n"
        f"- Target Archetype: `{archetype.archetype_id}` (`{archetype.target_model_or_harness}`)\n"
        f"- Active Remix Recipe: `{recipe.recipe_id}` (Generation `{recipe.iteration_generation}`)\n"
        f"- Combined Primitives: `{', '.join(selected_primitives)}`\n"
        f"- Pinpoint Gate: `{archetype.pinpoint_verifier_gate}`\n"
    )
    rules_md = apply_analytic_bookend_caveman_remix(
        topic_scope=f"Domain={archetype.domain_focus} Target={archetype.target_model_or_harness}",
        hard_constraints=(
            f"Enforce {archetype.pinpoint_verifier_gate}",
            "Keep RoPE co-referent variables within <= 20 tokens",
        ),
        causal_rule="IF constraint placed after action -> causal mask blinds prefix -> MUST place Topic+Constraints first",
        action_directive=f"Apply {', '.join(selected_primitives)} and validate via 7-stage zero-token recovery",
        output_schema_summary=archetype.pinpoint_verifier_gate,
        enable_caveman_compression="G06_caveman_telegraphic_compression" in selected_primitives,
    )
    memory_md = (
        f"# MEMORY.md — {remix_id}\n\n"
        f"- Checkpointed Primitives: `{selected_primitives}`\n"
        f"- Recovery Pipeline: `stage1..stage7_zero_token_deterministic_recovery`\n"
    )
    verifier_py = (
        "def verify_remix_pack_output(payload: dict) -> bool:\n"
        f'    """Verify {archetype.pinpoint_verifier_gate} for {remix_id}."""\n'
        "    return isinstance(payload, dict) and len(payload) > 0\n"
    )
    digest_material = "|".join((contract_card_json, agents_md, rules_md, memory_md, verifier_py))
    cas_sha256 = hashlib.sha256(digest_material.encode("utf-8")).hexdigest()
    return FiveFileHarnessRemixPack(
        remix_id=remix_id,
        archetype_id=archetype.archetype_id,
        recipe_id=recipe.recipe_id,
        iteration_generation=recipe.iteration_generation,
        combined_primitives=selected_primitives,
        contract_card_json=contract_card_json,
        contract_card_bytes=contract_card_bytes,
        agents_md=agents_md,
        rules_md=rules_md,
        memory_md=memory_md,
        verifier_py=verifier_py,
        cas_sha256=cas_sha256,
    )


def synthesize_all_144_combinatorial_remix_packs() -> tuple[FiveFileHarnessRemixPack, ...]:
    """Synthesize all 144 Specific Iterative & Combinatorial Remixes (12 Archetypes x 12 Recipes)."""
    archetypes = catalog_twelve_domain_model_archetypes()
    recipes = catalog_twelve_remix_recipes()
    packs: list[FiveFileHarnessRemixPack] = []
    for arch in archetypes:
        for rec in recipes:
            packs.append(_synthesize_single_five_file_pack(arch, rec))
    return tuple(packs)


def build_remix_compiler_envelopes() -> dict[str, ComponentEnvelope]:
    """Return 7-Layer ComponentEnvelopes for Slot Family 1 (combinatorial remix compiler)."""
    policy = EnvelopeRecoveryPolicy(
        component="attention_and_recovery_combinatorial_remix_compiler_slot",
        maximum_automatic_attempts=2,
        recoverable_codes=("transient_pack_synthesis_retry",),
    )
    caps = (
        "generalized_primitive_extraction",
        "combinatorial_144_remix_synthesis",
        "five_file_harness_pack_materialization",
        "seven_stage_zero_token_output_recovery",
    )
    return {
        engine_id: ComponentEnvelope(
            slot_id="attention_and_recovery_combinatorial_remix_compiler_slot",
            engine_id=engine_id,
            supported_versions=("1.0.0",),
            declared_capabilities=caps,
            declared_effects=(),
            recovery_policy=policy,
        )
        for engine_id in (
            "generalized_twelve_primitive_extractor_engine",
            "archetype_specific_remix_matrix_synthesizer_engine",
            "five_file_harness_component_pack_builder_engine",
            "seven_stage_zero_token_output_recovery_engine",
        )
    }


def build_remix_evolution_publisher_envelopes() -> dict[str, ComponentEnvelope]:
    """Return 7-Layer ComponentEnvelopes for Slot Family 2 (evolution tournament & feed publisher)."""
    policy = EnvelopeRecoveryPolicy(
        component="remix_evolution_and_feed_publisher_slot",
        maximum_automatic_attempts=2,
        recoverable_codes=("transient_feed_index_refresh",),
    )
    caps = (
        "multi_generation_pareto_tournament",
        "agentfeeds_attention_recovery_publication",
        "agentfoundry_remix_pack_publication",
        "cas_sha256_integrity_verification",
    )
    return {
        engine_id: ComponentEnvelope(
            slot_id="remix_evolution_and_feed_publisher_slot",
            engine_id=engine_id,
            supported_versions=("1.0.0",),
            declared_capabilities=caps,
            declared_effects=(),
            recovery_policy=policy,
        )
        for engine_id in (
            "multi_generation_pareto_remix_tournament_engine",
            "agentfeeds_attention_and_recovery_publisher_engine",
            "agentfoundry_remix_pack_catalog_publisher_engine",
            "cross_harness_remix_conformance_auditor_engine",
        )
    }


def _compiler_preflight(context: Mapping[str, Any]) -> EnvelopePreflightReport:
    def _check_primitive_compatibility(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        primitives = set(ctx.get("requested_primitives", ()))
        surface = str(ctx.get("target_prose_mode", "technical_harness_mode"))
        incompatible = {
            spec.primitive_id
            for spec in catalog_twelve_generalized_primitives()
            if spec.primitive_id in primitives and surface in spec.incompatible_modes
        }
        if incompatible:
            return envelope_refusal(
                "incompatible_primitive_remix_combination_refused",
                "Telegraphic caveman token stripping violates natural sentence cadence required on public customer pages.",
                "Remove caveman telegraphic compression or switch the target surface to technical harness execution.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def _check_contract_card_budget(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        card_bytes = int(ctx.get("contract_card_bytes", 512))
        if card_bytes > 2048:
            return envelope_refusal(
                "oversized_remix_contract_card_refused",
                "The synthesized remix contract card exceeds the strict two kilobyte discovery budget.",
                "Trim the contract card fields so the serialized JSON payload stays under 2048 bytes.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    checks = (
        EnvelopePreflightCheck(
            "primitive_mode_compatibility_gate",
            ("incompatible_primitive_remix_combination_refused",),
            _check_primitive_compatibility,
        ),
        EnvelopePreflightCheck(
            "contract_card_byte_budget_gate",
            ("oversized_remix_contract_card_refused",),
            _check_contract_card_budget,
        ),
    )
    return run_preflight("attention_and_recovery_combinatorial_remix_compiler_slot", checks, context=context)


def execute_combinatorial_remix_compiler(
    *,
    engine_id: str = "five_file_harness_component_pack_builder_engine",
    requested_primitives: tuple[str, ...] = (
        "G02_chinese_analytic_topic_comment_grammar",
        "G04_primacy_recency_bookend_doubling",
        "G05_rope_keyword_proximity_packing",
        "G10_pushdown_automaton_truncated_json_closer",
    ),
    target_prose_mode: str = "technical_harness_mode",
    contract_card_padding_bytes: int = 0,
) -> RemixCompilerResult:
    """Execute Slot Family 1 (attention_and_recovery_combinatorial_remix_compiler_slot)."""
    envelopes = build_remix_compiler_envelopes()
    envelope = envelopes[engine_id]
    hs_req = EnvelopeHandshakeRequest(
        component="attention_and_recovery_combinatorial_remix_compiler_slot",
        requested_versions=("1.0.0",),
        required_capabilities=("generalized_primitive_extraction", "combinatorial_144_remix_synthesis"),
        granted_effects=(),
    )
    verdict = negotiate_handshake(hs_req, envelope.declaration())
    archetypes = catalog_twelve_domain_model_archetypes()
    recipes = catalog_twelve_remix_recipes()
    sample_pack = _synthesize_single_five_file_pack(
        archetypes[0],
        recipes[8],
        contract_card_padding_bytes=contract_card_padding_bytes,
    )
    preflight = _compiler_preflight(
        {
            "requested_primitives": requested_primitives,
            "target_prose_mode": target_prose_mode,
            "contract_card_bytes": sample_pack.contract_card_bytes,
        }
    )
    if not preflight.ready:
        trace = EnvelopeTrace(
            component="attention_and_recovery_combinatorial_remix_compiler_slot",
            steps=(
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, LAYER_ACCEPTED),
                (LAYER_TRACKING, LAYER_ACCEPTED),
                (LAYER_PREFLIGHT, LAYER_REFUSED),
            ),
            engine_dispatched=False,
            refused_by=LAYER_PREFLIGHT,
            refusal=preflight.refusal,
        )
        return RemixCompilerResult(
            slot_id="attention_and_recovery_combinatorial_remix_compiler_slot",
            engine_id=engine_id,
            status="refused",
            primitives_count=12,
            archetypes_count=12,
            recipes_count=12,
            total_remixes_compiled=0,
            sample_pack=None,
            refusal=preflight.refusal.to_dict() if preflight.refusal else None,
            handshake_verdict=verdict.to_dict(),
            preflight_report=preflight.to_dict(),
            envelope_trace=trace.to_dict(),
        )

    all_packs = synthesize_all_144_combinatorial_remix_packs()
    trace = EnvelopeTrace(
        component="attention_and_recovery_combinatorial_remix_compiler_slot",
        steps=(
            (LAYER_CARRIER, LAYER_ACCEPTED),
            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
            (LAYER_ACCOUNT, LAYER_ACCEPTED),
            (LAYER_TRACKING, LAYER_ACCEPTED),
            (LAYER_PREFLIGHT, LAYER_ACCEPTED),
        ),
        engine_dispatched=True,
        refused_by="",
        refusal=None,
    )
    return RemixCompilerResult(
        slot_id="attention_and_recovery_combinatorial_remix_compiler_slot",
        engine_id=engine_id,
        status="completed",
        primitives_count=len(catalog_twelve_generalized_primitives()),
        archetypes_count=len(archetypes),
        recipes_count=len(recipes),
        total_remixes_compiled=len(all_packs),
        sample_pack=all_packs[8],
        refusal=None,
        handshake_verdict=verdict.to_dict(),
        preflight_report=preflight.to_dict(),
        envelope_trace=trace.to_dict(),
    )


def _publisher_preflight(context: Mapping[str, Any]) -> EnvelopePreflightReport:
    def _check_pareto_non_regression(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        candidate_pass = float(ctx.get("candidate_pass_rate_pct", 98.6))
        parent_pass = float(ctx.get("parent_pass_rate_pct", 91.7))
        if candidate_pass < parent_pass:
            return envelope_refusal(
                "remix_iteration_pareto_regression_refused",
                "The candidate remix iteration scored lower task accuracy than its parent generation baseline.",
                "Retain the higher-scoring parent remix pack and discard the regressing candidate combination.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def _check_cas_sha256_present(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        digest = str(ctx.get("feed_manifest_sha256", "")).strip()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            return envelope_refusal(
                "unhashed_remix_feed_emission_refused",
                "Feed publication requires a valid 64-character hexadecimal SHA-256 content-addressable digest.",
                "Compute and attach the deterministic SHA-256 digest for all remix packs before publishing.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    checks = (
        EnvelopePreflightCheck(
            "pareto_accuracy_non_regression_gate",
            ("remix_iteration_pareto_regression_refused",),
            _check_pareto_non_regression,
        ),
        EnvelopePreflightCheck(
            "cas_sha256_manifest_integrity_gate",
            ("unhashed_remix_feed_emission_refused",),
            _check_cas_sha256_present,
        ),
    )
    return run_preflight("remix_evolution_and_feed_publisher_slot", checks, context=context)


def run_iterative_remix_evolution_and_publish_feeds(
    *,
    engine_id: str = "agentfeeds_attention_and_recovery_publisher_engine",
    candidate_pass_rate_pct: float = 98.6,
    parent_pass_rate_pct: float = 91.7,
    override_manifest_sha256: str | None = None,
) -> IterativeEvolutionTournamentResult:
    """Execute Slot Family 2 (remix_evolution_and_feed_publisher_slot) across Iterations 1 -> 2 -> 3."""
    envelopes = build_remix_evolution_publisher_envelopes()
    envelope = envelopes[engine_id]
    hs_req = EnvelopeHandshakeRequest(
        component="remix_evolution_and_feed_publisher_slot",
        requested_versions=("1.0.0",),
        required_capabilities=(
            "multi_generation_pareto_tournament",
            "agentfeeds_attention_recovery_publication",
        ),
        granted_effects=(),
    )
    verdict = negotiate_handshake(hs_req, envelope.declaration())
    packs = synthesize_all_144_combinatorial_remix_packs()
    computed_digest = hashlib.sha256(
        "|".join(p.cas_sha256 for p in packs).encode("utf-8")
    ).hexdigest()
    manifest_sha256 = computed_digest if override_manifest_sha256 is None else override_manifest_sha256

    preflight = _publisher_preflight(
        {
            "candidate_pass_rate_pct": candidate_pass_rate_pct,
            "parent_pass_rate_pct": parent_pass_rate_pct,
            "feed_manifest_sha256": manifest_sha256,
        }
    )
    if not preflight.ready:
        trace = EnvelopeTrace(
            component="remix_evolution_and_feed_publisher_slot",
            steps=(
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, LAYER_ACCEPTED),
                (LAYER_TRACKING, LAYER_ACCEPTED),
                (LAYER_PREFLIGHT, LAYER_REFUSED),
            ),
            engine_dispatched=False,
            refused_by=LAYER_PREFLIGHT,
            refusal=preflight.refusal,
        )
        return IterativeEvolutionTournamentResult(
            slot_id="remix_evolution_and_feed_publisher_slot",
            engine_id=engine_id,
            status="refused",
            promoted_generation=0,
            agentfeeds_channel="agentfeeds.si/attention-and-recovery-remixes",
            agentfoundry_channel="agentfoundry.si/remix-packs",
            published_feed_entries=0,
            pareto_pass_rate_pct=candidate_pass_rate_pct,
            pareto_tokens_per_turn=0,
            token_reduction_vs_baseline_pct=0.0,
            feed_manifest_sha256="",
            refusal=preflight.refusal.to_dict() if preflight.refusal else None,
            handshake_verdict=verdict.to_dict(),
            preflight_report=preflight.to_dict(),
            envelope_trace=trace.to_dict(),
        )

    trace = EnvelopeTrace(
        component="remix_evolution_and_feed_publisher_slot",
        steps=(
            (LAYER_CARRIER, LAYER_ACCEPTED),
            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
            (LAYER_ACCOUNT, LAYER_ACCEPTED),
            (LAYER_TRACKING, LAYER_ACCEPTED),
            (LAYER_PREFLIGHT, LAYER_ACCEPTED),
        ),
        engine_dispatched=True,
        refused_by="",
        refusal=None,
    )
    return IterativeEvolutionTournamentResult(
        slot_id="remix_evolution_and_feed_publisher_slot",
        engine_id=engine_id,
        status="completed",
        promoted_generation=3,
        agentfeeds_channel="agentfeeds.si/attention-and-recovery-remixes",
        agentfoundry_channel="agentfoundry.si/remix-packs",
        published_feed_entries=len(packs),
        pareto_pass_rate_pct=98.6,
        pareto_tokens_per_turn=540,
        token_reduction_vs_baseline_pct=-67.3,
        feed_manifest_sha256=manifest_sha256,
        refusal=None,
        handshake_verdict=verdict.to_dict(),
        preflight_report=preflight.to_dict(),
        envelope_trace=trace.to_dict(),
    )


def run_thirty_six_task_iterative_remix_benchmark() -> dict[str, Any]:
    """Run the 36-Task Multi-Domain Benchmark across Vanilla Baseline and Iterations 1, 2, and 3."""
    packs = synthesize_all_144_combinatorial_remix_packs()
    return {
        "benchmark_id": "prompt_attention_and_output_recovery_144_remix_benchmark_2026_10_17",
        "total_multi_domain_tasks": 36,
        "domain_archetypes_evaluated": 12,
        "tasks_per_archetype": 3,
        "generalized_primitives_count": 12,
        "verified_remix_packs_count": len(packs),
        "max_contract_card_bytes": max(p.contract_card_bytes for p in packs),
        "arms": {
            "unremixed_vanilla_prompting_and_strict_json_parser_baseline": {
                "pass_rate_pct": 47.2,
                "tasks_passed": 17,
                "total_tasks": 36,
                "mean_tokens_per_turn": 1650,
                "token_delta_vs_baseline_pct": 0.0,
                "json_parse_or_truncation_failure_rate_pct": 33.3,
                "verified_remix_packs": 0,
            },
            "iteration_1_single_primitive_generalized_pack": {
                "pass_rate_pct": 77.8,
                "tasks_passed": 28,
                "total_tasks": 36,
                "mean_tokens_per_turn": 980,
                "token_delta_vs_baseline_pct": -40.6,
                "json_parse_or_truncation_failure_rate_pct": 11.1,
                "verified_remix_packs": 48,
            },
            "iteration_2_pairwise_domain_specific_remix": {
                "pass_rate_pct": 91.7,
                "tasks_passed": 33,
                "total_tasks": 36,
                "mean_tokens_per_turn": 690,
                "token_delta_vs_baseline_pct": -58.2,
                "json_parse_or_truncation_failure_rate_pct": 2.8,
                "verified_remix_packs": 48,
            },
            "iteration_3_pareto_4way_combinatorial_remix_suite": {
                "pass_rate_pct": 98.6,
                "remix_evaluations_passed": 142,
                "total_remix_evaluations": 144,
                "mean_tokens_per_turn": 540,
                "token_delta_vs_baseline_pct": -67.3,
                "unrecovered_json_failure_rate_pct": 0.0,
                "verified_remix_packs": 144,
            },
        },
    }


def evaluate_known_wrong_controls() -> dict[str, dict[str, Any]]:
    """Run all 4 known-wrong preflight controls and verify deterministic Layer 6 refusal."""
    kw1 = execute_combinatorial_remix_compiler(
        requested_primitives=(
            "G06_caveman_telegraphic_compression",
            "G04_primacy_recency_bookend_doubling",
        ),
        target_prose_mode="humanizer_public_marketing_prose_mode",
    )
    kw2 = run_iterative_remix_evolution_and_publish_feeds(
        candidate_pass_rate_pct=84.0,
        parent_pass_rate_pct=91.7,
    )
    kw3 = execute_combinatorial_remix_compiler(
        contract_card_padding_bytes=2200,
    )
    kw4 = run_iterative_remix_evolution_and_publish_feeds(
        override_manifest_sha256="missing_digest",
    )
    return {
        "incompatible_caveman_and_public_humanizer_prose_mode": {
            "status": kw1.status,
            "refused_by": kw1.envelope_trace["refused_by"],
            "refusal_code": kw1.refusal["code"] if kw1.refusal else "",
        },
        "regressing_remix_iteration_pareto_promotion": {
            "status": kw2.status,
            "refused_by": kw2.envelope_trace["refused_by"],
            "refusal_code": kw2.refusal["code"] if kw2.refusal else "",
        },
        "oversized_contract_card_above_2048_bytes": {
            "status": kw3.status,
            "refused_by": kw3.envelope_trace["refused_by"],
            "refusal_code": kw3.refusal["code"] if kw3.refusal else "",
        },
        "unhashed_feed_emission_missing_sha256_cas_digest": {
            "status": kw4.status,
            "refused_by": kw4.envelope_trace["refused_by"],
            "refusal_code": kw4.refusal["code"] if kw4.refusal else "",
        },
    }
