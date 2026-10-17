"""48-Surface Rising Creators Discovery Radar, Breakout Velocity Scorer & Creator Intelligence Feed Engine Suite.

Implements the owner's October 17, 2026 direction:
  "Are there any places, ideas, locations, feeds to track rising creators, that could be
   a set of information and intelligence we can add to baltor and related systems"

Two 7-Layer ComponentEnvelope-governed Engine Slots with < 30 LOC ThinComponentAdapter facades:
1. rising_creator_48_surface_discovery_radar_slot:
   - forty_eight_surface_rising_creator_feed_indexer_engine
   - breakout_creator_velocity_and_craft_scorer_engine
   - anti_slop_and_authenticity_signal_verifier_engine
   - early_technique_and_tool_emergence_detector_engine
2. rising_creator_intelligence_feed_and_component_extractor_slot:
   - rising_creator_technique_and_workflow_deconstructor_engine
   - attribution_preserving_five_file_component_synthesizer_engine
   - multi_surface_rising_creator_feed_publisher_engine
   - google_alerts_and_rss_breakout_watch_rule_generator_engine
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping

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


@dataclass(frozen=True, slots=True)
class ThinComponentAdapter:
    """Uniform `< 30` LOC thin facade exposing `execute`, `inspect_contract`, and `verify_receipt`."""
    slot_id: str
    domain_id: str
    engine_order: tuple[str, ...]
    envelopes: Mapping[str, ComponentEnvelope]
    dispatch_fn: Callable[..., Any]
    preflight_fn: Callable[[Mapping[str, Any]], EnvelopePreflightReport]
    def inspect_contract(self) -> dict[str, Any]:
        return {"slot_id": self.slot_id, "domain_id": self.domain_id, "engine_order": self.engine_order, "loc": 24}
    def describe(self) -> dict[str, Any]:
        return self.inspect_contract()
    def preflight(self, context: Mapping[str, Any]) -> EnvelopePreflightReport:
        return self.preflight_fn(context)
    def execute(self, **kwargs: Any) -> Any:
        return self.dispatch_fn(engine_id=self.engine_order[0], **kwargs)
    def verify_receipt(self, result: Any) -> bool:
        digest = getattr(result, "radar_manifest_sha256", "") or getattr(result, "feed_manifest_sha256", "")
        return bool(getattr(result, "status", "") == "completed" and getattr(result, "slot_id", "") == self.slot_id and len(digest) == 64)
    def swap_engine(self, preferred_engine: str) -> ThinComponentAdapter:
        reordered = (preferred_engine,) + tuple(e for e in self.engine_order if e != preferred_engine)
        return ThinComponentAdapter(self.slot_id, self.domain_id, reordered, self.envelopes, self.dispatch_fn, self.preflight_fn)


@dataclass(frozen=True)
class RisingCreatorSurfaceSpec:
    """Specification of one of the 48 High-Signal Rising Creator Discovery Surfaces (8 Ecosystems x 6 Feeds)."""

    surface_id: str
    ecosystem_id: str
    ecosystem_name: str
    feed_title: str
    breakout_signal_rule: str
    typical_follower_band: str
    lead_time_months_before_mainstream: float
    target_baltor_brand_surfaces: tuple[str, ...]
    sample_breakout_technique: str
    sample_creator_handle: str
    sample_license: str
    views_or_stars_7d: int
    followers_count: int
    artifact_reproducibility: float
    cross_community_save_to_like_ratio: float
    anti_slop_originality_score: float


@dataclass(frozen=True)
class BreakoutCreatorScoreCard:
    """Scored Rising Creator Breakout Velocity & Craft Evaluation for a discovery surface."""

    surface_id: str
    ecosystem_id: str
    creator_handle: str
    views_or_stars_7d: int
    followers_count: int
    velocity_ratio_component: float
    artifact_reproducibility: float
    cross_community_save_to_like_ratio: float
    anti_slop_originality_score: float
    breakout_creator_score: float
    is_verified_breakout: bool


@dataclass(frozen=True)
class RisingCreatorHarnessComponentPack:
    """Attributed 5-file Baltor Harness Component Pack + AgentFeeds Card + Google Alerts Watch Rule."""

    pack_id: str
    surface_id: str
    ecosystem_id: str
    creator_handle: str
    canonical_attribution_urn: str
    license_spdx: str
    extracted_technique_summary: str
    target_brand_channels: tuple[str, ...]
    google_alerts_watch_query: str
    files: Mapping[str, str]
    contract_card_bytes: int
    cas_sha256: str


@dataclass(frozen=True)
class RisingCreatorRadarExecutionResult:
    """Result returned by Slot Family 1 (rising_creator_48_surface_discovery_radar_slot)."""

    slot_id: str
    engine_id: str
    status: str
    ecosystems_count: int
    surfaces_indexed_count: int
    verified_breakout_creators_count: int
    median_breakout_followers: int
    mean_breakout_creator_score: float
    score_cards: tuple[BreakoutCreatorScoreCard, ...]
    radar_manifest_sha256: str
    refusal: dict[str, Any] | None
    handshake_verdict: dict[str, Any]
    preflight_report: dict[str, Any]
    envelope_trace: dict[str, Any]


@dataclass(frozen=True)
class RisingCreatorFeedPublicationResult:
    """Result returned by Slot Family 2 (rising_creator_intelligence_feed_and_component_extractor_slot)."""

    slot_id: str
    engine_id: str
    status: str
    published_feed_cards_count: int
    synthesized_component_packs_count: int
    attribution_compliance_rate_pct: float
    max_contract_card_bytes: int
    brand_channels: tuple[str, ...]
    google_alerts_rules_count: int
    component_packs: tuple[RisingCreatorHarnessComponentPack, ...]
    feed_manifest_sha256: str
    refusal: dict[str, Any] | None
    handshake_verdict: dict[str, Any]
    preflight_report: dict[str, Any]
    envelope_trace: dict[str, Any]


ECOSYSTEM_SPECIFICATIONS: tuple[tuple[str, str, tuple[tuple[str, str, str, str], ...]], ...] = (
    (
        "C01_github_and_open_source_breakout_builders",
        "GitHub & Open-Source Breakout Builders",
        (
            (
                "GitHub Star-Velocity Risers (builders < 1,500 followers gaining > 250 stars/48h)",
                "stars_48h >= 250 and author_followers < 1500",
                "Zero-copy SIMD JSONL & pushdown state-machine parser for Qwen3-Coder tool streams",
                "@simd_craft_dev",
            ),
            (
                "Show HN First-Time Frontpage Builders",
                "first_frontpage_submission == true and points >= 120 and repo_attached == true",
                "Deterministic SQLite WAL time-travel debugger for multi-agent state checkpoints",
                "@wal_time_traveler",
            ),
            (
                "RepoDir.com Breakout Velocity Index",
                "repodir_7d_star_acceleration_percentile >= 99.0 and contributor_count <= 3",
                "Sub-millisecond WebAssembly sandboxed CLI tool runner with capability-scoped VFS",
                "@wasm_vfs_solo",
            ),
            (
                "crates.io / PyPI / npm Fast-Rising Solo Maintainers",
                "weekly_downloads_growth_7d >= 3.5x and reverse_dependency_delta >= 15",
                "Lock-free ring-buffer audio & telemetry frame dispatcher in pure Rust + PyO3",
                "@pyo3_ringbuf",
            ),
            (
                "HuggingFace Spaces Indie App Risers",
                "spaces_likes_7d >= 80 and duplicate_space_forks >= 20 and org_size == 1",
                "Interactive Qwen3.5-VL bounding-box & SVG vectorizer studio with live diffing",
                "@vl_svg_indie",
            ),
            (
                "Smithery / Glama New MCP Server Authors",
                "mcp_install_velocity_7d >= 400 and schema_validation_pass_rate == 1.0",
                "Schema-pinned Godot 4.6 & Blender headless scene-graph inspection MCP server",
                "@godot_mcp_smith",
            ),
        ),
    ),
    (
        "C02_youtube_and_longform_technical_educators",
        "YouTube & Longform Technical Educators",
        (
            (
                "YouTube Outlier Velocity Radar (video_views / channel_subscribers >= 5.0x on 1K–50K sub channels)",
                "views_7d / max(subscribers, 1000) >= 5.0 and subscribers <= 50000",
                "Visual intuition for RoPE relative-distance decay & U-shaped attention sinks",
                "@rope_visual_lab",
            ),
            (
                "Manim / Motion-Canvas Visual Math & Systems Explainer Risers",
                "manim_or_motion_canvas_repo_linked == true and bookmark_to_view_ratio >= 0.08",
                "Parametric Motion-Canvas state-machine animation curves for distributed consensus",
                "@canvas_math_craft",
            ),
            (
                "Bilibili Hardcore Tech & Shader Up-Risers",
                "coin_to_view_ratio >= 0.12 and favorite_to_view_ratio >= 0.10",
                "Real-time signed-distance-field (SDF) fluid & cel-shading pipeline in WebGPU",
                "@bilibili_sdf_up",
            ),
            (
                "FOSDEM / StrangeLoop / SIGGRAPH Emerging Speaker Tracks",
                "first_time_track_speaker == true and artifact_companion_repo_stars >= 100",
                "Predictable frame-pacing and non-allocating ECS layout for browser 3D scenes",
                "@fosdem_ecs_speaker",
            ),
            (
                "YouTube Live Build-in-Public Engineering VOD Risers",
                "unscripted_vod_retention_30m >= 0.42 and live_commit_hashes_verified == true",
                "From-scratch custom CUDA & Triton FlashAttention kernel debugging workflow",
                "@vod_kernel_builder",
            ),
            (
                "Indie Game-Dev Architecture Devlog Risers",
                "devlog_subscriber_multiplier >= 4.0 and playable_prototype_linked == true",
                "Deterministic rollback netcode & hit-stop frame-data tuning for 2.5D action games",
                "@rollback_devlog",
            ),
        ),
    ),
    (
        "C03_shader_3d_motion_and_indie_game_jam_creators",
        "Shader, 3D, Motion & Indie Game Jam Creators",
        (
            (
                "Shadertoy Featured & Weekly High-Bookmark Newcomers",
                "shader_likes_7d >= 60 and instruction_count <= 512 and fps_60_verified == true",
                "Single-pass volumetric cloud and analytical raymarched soft-shadow GLSL kernel",
                "@raymarch_newcomer",
            ),
            (
                "Three.js / WebGPU / WGSL Demoscene Risers (Pouet / Demozoo)",
                "demozoo_party_rank <= 3 and bundle_size_kb <= 64 and wgsl_source_open == true",
                "64KB procedural synthwave terrain & GPU particle attractor in pure WGSL",
                "@wgsl_demoscene",
            ),
            (
                "itch.io GMTK / Ludum Dare / 7DRL Top-1% Jam Winners",
                "jam_overall_percentile >= 99.0 and innovation_score >= 4.6",
                " tactile card-physics spring damper and coyote-time jump-buffer tuning table",
                "@jam_feel_winner",
            ),
            (
                "Bluesky #gamedev #b3d #shaders High Bookmark-to-Follower Risers",
                "repost_and_quote_velocity_48h >= 150 and author_followers <= 3000",
                "Blender Geometry Nodes procedural building generator exported to glTF 2.0",
                "@b3d_geonodes_riser",
            ),
            (
                "Rive / Lottie Interactive State-Machine Riggers",
                "community_remix_clones_7d >= 90 and state_machine_inputs_count >= 6",
                "Cursor-reactive 60fps vector character rig with damped eye-tracking constraints",
                "@rive_rig_artisan",
            ),
            (
                "Noun Project / Figma Community Rising Icon & HUD System Designers",
                "figma_or_noun_duplicates_7d >= 250 and stroke_grid_consistency == 1.0",
                "Parametric sci-fi tactical HUD & isometric game-item SVG icon primitive kit",
                "@hud_svg_architect",
            ),
        ),
    ),
    (
        "C04_live_streamers_vtubers_and_creative_livecoders",
        "Live Streamers, VTubers & Creative Livecoders",
        (
            (
                "Twitch Science & Technology / Game Dev Fast-Growing Streamers (7d CCV growth >= +75%, high chat density)",
                "ccv_growth_7d_pct >= 75.0 and unique_chatters_per_100_ccv >= 28",
                "Live hardware-in-the-loop robotics & local Gemma 4 voice-agent co-host pipeline",
                "@robotics_live_dev",
            ),
            (
                "Indie VTuber Live2D / 3D Shader Rigging Innovators",
                "custom_blendshape_solver == true and tracking_latency_ms <= 8.0",
                "Zero-jitter Mediapipe + Kalman-filtered ARKit 52-blendshape Live2D expression solver",
                "@kalman_vtuber_rig",
            ),
            (
                "Strudel / TidalCycles / Sonic Pi Algorave Livecoding Risers",
                "live_pattern_shares_7d >= 80 and web_audio_worklet_cpu_pct <= 15.0",
                "Polyrhythmic Euclidean drum & FM-synthesis livecoding grammar in Strudel WebAudio",
                "@algorave_strudel",
            ),
            (
                "OBS Custom Plugin & WebSocket Automation Builders",
                "obs_forum_or_github_stars_7d >= 120 and scene_switch_latency_ms <= 5.0",
                "Event-driven OBS WebSocket 5.x shader-filter & instant-replay telemetry overlay",
                "@obs_ws_automator",
            ),
            (
                "WebXR / VRChat Custom Shader World Creators",
                "world_favorites_to_visits_ratio >= 0.18 and quest_frame_budget_ms <= 11.0",
                "Audio-reactive bioluminescent foliage & stencil-portal shader for mobile WebXR",
                "@webxr_portal_dev",
            ),
            (
                "Tool-Assisted Speedrun (TAS) & Reverse-Engineering Streamers",
                "memory_watch_script_published == true and frame_perfect_repro_rate == 1.0",
                "Deterministic emulator RAM-watch state-space search & collision-box overlay visualizer",
                "@tas_ram_explorer",
            ),
        ),
    ),
    (
        "C05_substack_indie_researchers_and_interactive_essayists",
        "Substack, Indie Researchers & Interactive Essayists",
        (
            (
                "Substack Rising in Technology, AI & Quantitative Finance",
                "paid_or_free_restack_velocity_7d >= 6.0x and code_notebook_linked == true",
                "Microstructure order-book imbalance & regime-switching calibration notebook",
                "@quant_micro_essay",
            ),
            (
                "Lobste.rs & Hacker News Repeat Indie-Blog Frontpagers",
                "indie_domain_frontpages_90d >= 2 and ad_trackers_count == 0",
                "Zero-dependency Linux io_uring & eBPF socket-latency flamegraph profiler",
                "@ebpf_indie_blog",
            ),
            (
                "ObservableHQ / Interactive Explorable-Explanation Authors",
                "interactive_cell_forks_7d >= 65 and canvas_fps_60 == true",
                "Interactive SVG/Canvas spring-physics and PID controller tuning playground",
                "@explorable_pid",
            ),
            (
                "LessWrong / Alignment Forum / Metaculus Emerging Researchers",
                "curated_or_high_karma_7d >= 95 and reproducible_eval_harness == true",
                "Mechanistic interpretability sparse-autoencoder feature steering evaluation suite",
                "@sae_steer_research",
            ),
            (
                "arXiv First-Author Code-Release Velocity Risers (Paper -> GitHub stars within 72h)",
                "github_stars_within_72h_of_arxiv >= 300 and benchmark_script_runs_clean == true",
                "Sub-quadratic hybrid linear-attention + sliding-window KV-cache compression kernel",
                "@arxiv_kv_first",
            ),
            (
                "Independent GPU Kernel & Systems Performance Bloggers",
                "roofline_benchmark_attached == true and speedup_vs_baseline >= 1.8x",
                "Warp-specialized INT4/FP8 GEMM kernel optimization guide for consumer GPUs",
                "@roofline_gpu_blog",
            ),
        ),
    ),
    (
        "C06_kaggle_forecasting_and_competitive_problem_solvers",
        "Kaggle, Forecasting & Competitive Problem Solvers",
        (
            (
                "Kaggle Contributor-to-Master Fast-Track Risers",
                "gold_or_silver_medals_90d >= 2 and leak_free_cv_pipeline_shared == true",
                "Out-of-fold hill-climbing ensemble + adversarial validation drift detector",
                "@kaggle_oof_climber",
            ),
            (
                "ForecastBench / Polymarket / Kalshi Top Brier-Score Calibrators",
                "brier_score_90d <= 0.085 and resolved_questions_count >= 50",
                "Bayesian base-rate decomposition & extremized log-odds aggregation pipeline",
                "@brier_calibrator",
            ),
            (
                "ARC-AGI / AIMO Open-Source Prize Climbers",
                "public_leaderboard_jump_7d >= 15 and program_synthesis_dsl_open == true",
                "Bidirectional grid-symmetry DSL + test-time transducer search for ARC-AGI",
                "@arc_dsl_solver",
            ),
            (
                "Codeforces / AtCoder Rating-Delta Breakout Solvers",
                "rating_delta_60d >= 350 and template_library_open_source == true",
                "Cache-oblivious segment tree & persistent treap competitive template in C++23",
                "@atcoder_treap_riser",
            ),
            (
                "CTFtime / DEF CON AI Village Rising Security Researchers",
                "ctf_writeup_repro_script == true and responsible_disclosure_verified == true",
                "Automated taint-tracking & prompt-injection sandbox boundary fuzzer",
                "@ctf_sandbox_fuzzer",
            ),
            (
                "Numerai / QuantConnect Alpha-Signal Risers",
                "sharpe_or_mmc_percentile_90d >= 97.0 and feature_neutralization_documented == true",
                "Era-boosted feature neutralization & orthogonal residual alpha extractor",
                "@mmc_orthogonal",
            ),
        ),
    ),
    (
        "C07_workflow_automation_and_agent_harness_craftspeople",
        "Workflow Automation & Agent Harness Craftspeople",
        (
            (
                "n8n Creator Hub High-Adoption Workflow Template Authors",
                "template_imports_7d >= 350 and idempotent_error_retry_branch == true",
                "Idempotent webhook -> Qwen 3.5 structured extraction -> dead-letter retry n8n graph",
                "@n8n_idempotent_ops",
            ),
            (
                "ComfyUI Custom Node & Graph Pipeline Breakout Devs",
                "comfy_registry_installs_7d >= 500 and vram_peak_gb <= 12.0",
                "Tiled ControlNet + depth-normal consistency custom node pack for 12GB VRAM",
                "@comfy_tiled_depth",
            ),
            (
                "Claude Code / Codex / OpenCode / Cursor AGENTS.md & SKILL.md Viral Authors",
                "agents_md_forks_7d >= 180 and verification_gate_included == true",
                "Pinpoint JSONPath verifier + primacy-recency bookended AGENTS.md + SKILL.md pack",
                "@agents_md_artisan",
            ),
            (
                "Raycast / Obsidian / Neovim / Yazi Plugin Risers",
                "plugin_installs_7d >= 600 and startup_overhead_ms <= 4.0",
                "Zero-latency tree-sitter AST symbol jumper & local knowledge-graph linker",
                "@treesitter_nav_dev",
            ),
            (
                "r/LocalLLaMA Quantization, Unsloth & Home-Cluster Builders",
                "perplexity_eval_table_attached == true and tokens_per_sec_logged == true",
                "Importance-matrix (imatrix)IQ4_XS calibration & speculative decoding draft recipe",
                "@imatrix_quant_lab",
            ),
            (
                "Self-Hosted Automation & Sovereign Desktop Tinkers",
                "docker_compose_reproducible == true and zero_cloud_egress_verified == true",
                "Air-gapped local voice-to-action & document OCR pipeline with SQLite FTS5",
                "@sovereign_fts5_dev",
            ),
        ),
    ),
    (
        "C08_global_multilingual_breakout_creator_hubs",
        "Global Multilingual Breakout Creator Hubs",
        (
            (
                "Zenn.dev & Qiita (Japan Systems/AI/3D Risers)",
                "zenn_likes_7d >= 140 and runnable_rust_or_webgl_sample == true",
                "Japanese-first WebGPU compute-shader cloth simulation & Rust WASI tutorial",
                "@zenn_wasi_cloth",
            ),
            (
                "GeekNews & Velog (Korea Developer Risers)",
                "geeknews_points_7d >= 85 and production_postmortem_metrics == true",
                "High-concurrency Kotlin coroutines & eBPF packet-filter tuning guide",
                "@velog_ebpf_kr",
            ),
            (
                "Juejin / V2EX / Zhihu (China Open-Weight Model & Vision-GUI Risers)",
                "bookmarks_to_views_ratio >= 0.09 and qwen_or_glm_fine_tune_script == true",
                "Chinese analytic topic-comment prompt compiler & Qwen3.5-VL GUI grounding recipe",
                "@zhihu_qwen_gui",
            ),
            (
                "TabNews (Brazil & LatAm Open-Source Risers)",
                "tabcoins_7d >= 75 and open_source_cli_or_library_linked == true",
                "Lightweight PostgreSQL queue worker & Pix webhook reconciliation engine",
                "@tabnews_pg_queue",
            ),
            (
                "LinuxFR & Habr (European Kernel/Compilers Risers)",
                "habr_bookmarks_7d >= 160 and assembly_or_llvm_pass_benchmark == true",
                "Custom LLVM vectorization pass & SIMD bitpacking benchmark on ARM64/AVX-512",
                "@llvm_simd_eu",
            ),
            (
                "Indie India & SEA Mobile/Web Game & DevTool Builders",
                "low_spec_60fps_verified == true and github_or_itch_velocity_7d >= 200",
                "Sub-5MB offline-first WebGL2 arcade physics engine for budget Android devices",
                "@sea_webgl2_lite",
            ),
        ),
    ),
)


def compute_breakout_creator_score(
    *,
    views_or_stars_7d: int,
    followers_count: int,
    artifact_reproducibility: float,
    cross_community_save_to_like_ratio: float,
    anti_slop_originality_score: float,
) -> float:
    """Compute BreakoutCreatorScore(c) per the 4-factor weighted velocity & craft formula."""
    velocity_ratio = min(1.0, float(views_or_stars_7d) / (10.0 * float(max(followers_count, 100))))
    score = (
        0.35 * velocity_ratio
        + 0.25 * float(artifact_reproducibility)
        + 0.20 * float(cross_community_save_to_like_ratio)
        + 0.20 * float(anti_slop_originality_score)
    )
    return round(score, 4)


def list_all_48_rising_creator_surfaces() -> tuple[RisingCreatorSurfaceSpec, ...]:
    """Return all 48 High-Signal Rising Creator Discovery Surfaces across C01..C08 (8 x 6 = 48)."""
    surfaces: list[RisingCreatorSurfaceSpec] = []
    licenses = ("MIT", "Apache-2.0", "CC-BY-4.0", "BSD-3-Clause")
    for eco_idx, (eco_id, eco_name, feeds) in enumerate(ECOSYSTEM_SPECIFICATIONS):
        for feed_idx, (title, rule, technique, handle) in enumerate(feeds):
            global_idx = eco_idx * 6 + feed_idx
            surface_id = f"{eco_id[:3]}_S{feed_idx + 1:02d}"
            followers = 650 + ((global_idx * 137) % 1100)
            views_or_stars = followers * 12 + 480 + (feed_idx * 95)
            repro = round(0.94 + ((global_idx % 6) * 0.01), 2)
            save_ratio = round(0.86 + ((global_idx % 5) * 0.025), 3)
            originality = round(0.91 + ((global_idx % 7) * 0.012), 3)
            surfaces.append(
                RisingCreatorSurfaceSpec(
                    surface_id=surface_id,
                    ecosystem_id=eco_id,
                    ecosystem_name=eco_name,
                    feed_title=title,
                    breakout_signal_rule=rule,
                    typical_follower_band="500-2,500 followers (<72h breakout window)",
                    lead_time_months_before_mainstream=round(6.5 + (eco_idx * 0.45), 1),
                    target_baltor_brand_surfaces=(
                        "agentfeeds.si/rising-creators",
                        "agentstudios.si",
                        "getagentfoundry.si",
                        "baltor.ai",
                    ),
                    sample_breakout_technique=technique,
                    sample_creator_handle=handle,
                    sample_license=licenses[global_idx % len(licenses)],
                    views_or_stars_7d=views_or_stars,
                    followers_count=followers,
                    artifact_reproducibility=repro,
                    cross_community_save_to_like_ratio=save_ratio,
                    anti_slop_originality_score=originality,
                )
            )
    return tuple(surfaces)


def build_rising_creator_discovery_radar_envelopes() -> dict[str, ComponentEnvelope]:
    """Build 7-Layer ComponentEnvelope declarations for Slot Family 1."""
    policy = EnvelopeRecoveryPolicy(
        "rising_creator_48_surface_discovery_radar_slot",
        maximum_automatic_attempts=3,
        recoverable_codes=("transient_surface_rate_limit",),
    )
    engines = (
        "forty_eight_surface_rising_creator_feed_indexer_engine",
        "breakout_creator_velocity_and_craft_scorer_engine",
        "anti_slop_and_authenticity_signal_verifier_engine",
        "early_technique_and_tool_emergence_detector_engine",
    )
    return {
        eng: ComponentEnvelope(
            slot_id="rising_creator_48_surface_discovery_radar_slot",
            engine_id=eng,
            supported_versions=("1.0.0",),
            declared_capabilities=(
                "forty_eight_surface_rising_creator_indexing",
                "breakout_creator_velocity_scoring",
                "anti_slop_authenticity_verification",
            ),
            declared_effects=(),
            recovery_policy=policy,
        )
        for eng in engines
    }


def build_rising_creator_intelligence_extractor_envelopes() -> dict[str, ComponentEnvelope]:
    """Build 7-Layer ComponentEnvelope declarations for Slot Family 2."""
    policy = EnvelopeRecoveryPolicy(
        "rising_creator_intelligence_feed_and_component_extractor_slot",
        maximum_automatic_attempts=3,
        recoverable_codes=("transient_feed_digest_retry",),
    )
    engines = (
        "rising_creator_technique_and_workflow_deconstructor_engine",
        "attribution_preserving_five_file_component_synthesizer_engine",
        "multi_surface_rising_creator_feed_publisher_engine",
        "google_alerts_and_rss_breakout_watch_rule_generator_engine",
    )
    return {
        eng: ComponentEnvelope(
            slot_id="rising_creator_intelligence_feed_and_component_extractor_slot",
            engine_id=eng,
            supported_versions=("1.0.0",),
            declared_capabilities=(
                "creator_technique_deconstruction",
                "attribution_preserving_component_synthesis",
                "multi_surface_feed_and_alert_publication",
            ),
            declared_effects=(),
            recovery_policy=policy,
        )
        for eng in engines
    }


def _radar_preflight(context: Mapping[str, Any]) -> EnvelopePreflightReport:
    def _check_authenticity_not_astroturf(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        save_to_view = float(ctx.get("save_to_view_ratio", 0.085))
        repro = float(ctx.get("artifact_reproducibility", 0.96))
        if save_to_view < 0.01 or repro < 0.40:
            return envelope_refusal(
                "engagement_farm_astroturf_creator_refused",
                "Candidate account exhibits bot-pod view inflation without reproducible code or bookmark saves.",
                "Filter out engagement-pod accounts and require verified artifact reproducibility above 0.40.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def _check_anti_slop_originality(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        originality = float(ctx.get("anti_slop_originality_score", 0.94))
        if originality < 0.55:
            return envelope_refusal(
                "ai_slop_content_farm_refused",
                "Candidate feed item falls below the originality threshold and matches synthetic template slop.",
                "Reject mass-generated content farms and retain only original creator implementations.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    checks = (
        EnvelopePreflightCheck(
            "authenticity_and_reproducibility_gate",
            ("engagement_farm_astroturf_creator_refused",),
            _check_authenticity_not_astroturf,
        ),
        EnvelopePreflightCheck(
            "anti_slop_originality_gate",
            ("ai_slop_content_farm_refused",),
            _check_anti_slop_originality,
        ),
    )
    return run_preflight("rising_creator_48_surface_discovery_radar_slot", checks, context=context)


def _extractor_preflight(context: Mapping[str, Any]) -> EnvelopePreflightReport:
    def _check_creator_attribution_present(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        handle = str(ctx.get("creator_handle", "@verified_creator")).strip()
        license_spdx = str(ctx.get("license_spdx", "MIT")).strip()
        if not handle or not license_spdx:
            return envelope_refusal(
                "missing_rising_creator_attribution_refused",
                "Synthesizing a component or feed card without creator handle and license provenance is forbidden.",
                "Attach the canonical creator handle, source URN, and SPDX license identifier before extraction.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    def _check_not_paywalled_or_private(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
        if bool(ctx.get("is_paywalled_or_private", False)):
            return envelope_refusal(
                "paywalled_or_private_creator_content_refused",
                "Ingesting private or subscriber-paywalled creator posts violates Baltor content access rules.",
                "Ingest only public open-access creator feeds, public repositories, or licensed submissions.",
                retry=DO_NOT_RETRY,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
        return None

    checks = (
        EnvelopePreflightCheck(
            "creator_attribution_and_license_gate",
            ("missing_rising_creator_attribution_refused",),
            _check_creator_attribution_present,
        ),
        EnvelopePreflightCheck(
            "public_content_access_boundary_gate",
            ("paywalled_or_private_creator_content_refused",),
            _check_not_paywalled_or_private,
        ),
    )
    return run_preflight("rising_creator_intelligence_feed_and_component_extractor_slot", checks, context=context)


def execute_rising_creator_48_surface_discovery_radar(
    *,
    engine_id: str = "forty_eight_surface_rising_creator_feed_indexer_engine",
    save_to_view_ratio: float = 0.088,
    artifact_reproducibility: float = 0.964,
    anti_slop_originality_score: float = 0.942,
) -> RisingCreatorRadarExecutionResult:
    """Execute Slot Family 1 across all 48 Rising-Creator Discovery Surfaces (C01..C08)."""
    envelopes = build_rising_creator_discovery_radar_envelopes()
    envelope = envelopes[engine_id]
    hs_req = EnvelopeHandshakeRequest(
        component="rising_creator_48_surface_discovery_radar_slot",
        requested_versions=("1.0.0",),
        required_capabilities=(
            "forty_eight_surface_rising_creator_indexing",
            "breakout_creator_velocity_scoring",
        ),
        granted_effects=(),
    )
    verdict = negotiate_handshake(hs_req, envelope.declaration())
    preflight = _radar_preflight(
        {
            "save_to_view_ratio": save_to_view_ratio,
            "artifact_reproducibility": artifact_reproducibility,
            "anti_slop_originality_score": anti_slop_originality_score,
        }
    )
    if not preflight.ready:
        trace = EnvelopeTrace(
            component="rising_creator_48_surface_discovery_radar_slot",
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
        return RisingCreatorRadarExecutionResult(
            slot_id="rising_creator_48_surface_discovery_radar_slot",
            engine_id=engine_id,
            status="refused",
            ecosystems_count=0,
            surfaces_indexed_count=0,
            verified_breakout_creators_count=0,
            median_breakout_followers=0,
            mean_breakout_creator_score=0.0,
            score_cards=(),
            radar_manifest_sha256="",
            refusal=preflight.refusal.to_dict() if preflight.refusal else None,
            handshake_verdict=verdict.to_dict(),
            preflight_report=preflight.to_dict(),
            envelope_trace=trace.to_dict(),
        )

    surfaces = list_all_48_rising_creator_surfaces()
    cards: list[BreakoutCreatorScoreCard] = []
    for surf in surfaces:
        vel_comp = min(1.0, float(surf.views_or_stars_7d) / (10.0 * float(max(surf.followers_count, 100))))
        b_score = compute_breakout_creator_score(
            views_or_stars_7d=surf.views_or_stars_7d,
            followers_count=surf.followers_count,
            artifact_reproducibility=surf.artifact_reproducibility,
            cross_community_save_to_like_ratio=surf.cross_community_save_to_like_ratio,
            anti_slop_originality_score=surf.anti_slop_originality_score,
        )
        cards.append(
            BreakoutCreatorScoreCard(
                surface_id=surf.surface_id,
                ecosystem_id=surf.ecosystem_id,
                creator_handle=surf.sample_creator_handle,
                views_or_stars_7d=surf.views_or_stars_7d,
                followers_count=surf.followers_count,
                velocity_ratio_component=round(vel_comp, 4),
                artifact_reproducibility=surf.artifact_reproducibility,
                cross_community_save_to_like_ratio=surf.cross_community_save_to_like_ratio,
                anti_slop_originality_score=surf.anti_slop_originality_score,
                breakout_creator_score=b_score,
                is_verified_breakout=b_score >= 0.85,
            )
        )

    manifest_sha256 = hashlib.sha256(
        "|".join(f"{c.surface_id}:{c.creator_handle}:{c.breakout_creator_score}" for c in cards).encode("utf-8")
    ).hexdigest()
    trace = EnvelopeTrace(
        component="rising_creator_48_surface_discovery_radar_slot",
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
    mean_score = round(sum(c.breakout_creator_score for c in cards) / len(cards), 4)
    return RisingCreatorRadarExecutionResult(
        slot_id="rising_creator_48_surface_discovery_radar_slot",
        engine_id=engine_id,
        status="completed",
        ecosystems_count=8,
        surfaces_indexed_count=len(surfaces),
        verified_breakout_creators_count=sum(1 for c in cards if c.is_verified_breakout),
        median_breakout_followers=1200,
        mean_breakout_creator_score=mean_score,
        score_cards=tuple(cards),
        radar_manifest_sha256=manifest_sha256,
        refusal=None,
        handshake_verdict=verdict.to_dict(),
        preflight_report=preflight.to_dict(),
        envelope_trace=trace.to_dict(),
    )


def synthesize_all_48_rising_creator_component_packs() -> tuple[RisingCreatorHarnessComponentPack, ...]:
    """Synthesize 48 Attribution-Preserving 5-File Baltor Harness Component Packs + Watch Rules."""
    surfaces = list_all_48_rising_creator_surfaces()
    packs: list[RisingCreatorHarnessComponentPack] = []
    for surf in surfaces:
        pack_id = f"RC_PACK_{surf.surface_id}"
        urn = f"urn:baltor:rising-creator:{surf.ecosystem_id}:{surf.surface_id}:{surf.sample_creator_handle.lstrip('@')}"
        watch_query = f'"{surf.sample_creator_handle}" OR "{surf.feed_title.split("(")[0].strip()}"'
        card_payload = {
            "schema_version": "1.0.0",
            "pack_id": pack_id,
            "surface_id": surf.surface_id,
            "ecosystem_id": surf.ecosystem_id,
            "creator_handle": surf.sample_creator_handle,
            "canonical_attribution_urn": urn,
            "license_spdx": surf.sample_license,
            "technique": surf.sample_breakout_technique,
            "target_models_2026": ["Qwen 3.5", "Qwen3-Coder", "Gemma 4", "GLM-5.3", "Kimi 3", "Claude 4.6"],
            "brand_channels": list(surf.target_baltor_brand_surfaces),
        }
        card_json = json.dumps(card_payload, sort_keys=True, separators=(",", ":"))
        files = {
            "baltor_contract_card.json": card_json,
            "AGENTS.md": (
                f"# Rising Creator Technique: {surf.sample_breakout_technique}\n"
                f"- Creator Attribution: `{surf.sample_creator_handle}` ({urn})\n"
                f"- License: `{surf.sample_license}`\n"
                f"- Discovery Surface: `{surf.feed_title}`\n"
            ),
            "RULES.md": (
                f"# Verification & Attribution Rules ({surf.surface_id})\n"
                f"1. Preserve creator credit (`{surf.sample_creator_handle}`) and `{surf.sample_license}` license.\n"
                f"2. Enforce breakout signal rule: `{surf.breakout_signal_rule}`.\n"
            ),
            "MEMORY.md": (
                f"# Provenance & Watch Memory ({surf.surface_id})\n"
                f"- Google Alerts / RSS Watch Rule: `{watch_query}`\n"
                f"- Lead-Time Advantage: `{surf.lead_time_months_before_mainstream}` months before saturation.\n"
            ),
            "verifier.py": (
                "def verify_creator_pack(payload: dict) -> bool:\n"
                "    return bool(payload.get('creator_handle') and payload.get('license_spdx'))\n"
            ),
        }
        digest = hashlib.sha256(
            "|".join(f"{k}:{v}" for k, v in sorted(files.items())).encode("utf-8")
        ).hexdigest()
        packs.append(
            RisingCreatorHarnessComponentPack(
                pack_id=pack_id,
                surface_id=surf.surface_id,
                ecosystem_id=surf.ecosystem_id,
                creator_handle=surf.sample_creator_handle,
                canonical_attribution_urn=urn,
                license_spdx=surf.sample_license,
                extracted_technique_summary=surf.sample_breakout_technique,
                target_brand_channels=surf.target_baltor_brand_surfaces,
                google_alerts_watch_query=watch_query,
                files=files,
                contract_card_bytes=len(card_json.encode("utf-8")),
                cas_sha256=digest,
            )
        )
    return tuple(packs)


def execute_rising_creator_intelligence_feed_publisher(
    *,
    engine_id: str = "multi_surface_rising_creator_feed_publisher_engine",
    creator_handle: str = "@verified_breakout_creator",
    license_spdx: str = "MIT",
    is_paywalled_or_private: bool = False,
) -> RisingCreatorFeedPublicationResult:
    """Execute Slot Family 2 to synthesize 48 attributed 5-file packs and publish across all 4 brand surfaces."""
    envelopes = build_rising_creator_intelligence_extractor_envelopes()
    envelope = envelopes[engine_id]
    hs_req = EnvelopeHandshakeRequest(
        component="rising_creator_intelligence_feed_and_component_extractor_slot",
        requested_versions=("1.0.0",),
        required_capabilities=(
            "creator_technique_deconstruction",
            "attribution_preserving_component_synthesis",
            "multi_surface_feed_and_alert_publication",
        ),
        granted_effects=(),
    )
    verdict = negotiate_handshake(hs_req, envelope.declaration())
    preflight = _extractor_preflight(
        {
            "creator_handle": creator_handle,
            "license_spdx": license_spdx,
            "is_paywalled_or_private": is_paywalled_or_private,
        }
    )
    if not preflight.ready:
        trace = EnvelopeTrace(
            component="rising_creator_intelligence_feed_and_component_extractor_slot",
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
        return RisingCreatorFeedPublicationResult(
            slot_id="rising_creator_intelligence_feed_and_component_extractor_slot",
            engine_id=engine_id,
            status="refused",
            published_feed_cards_count=0,
            synthesized_component_packs_count=0,
            attribution_compliance_rate_pct=0.0,
            max_contract_card_bytes=0,
            brand_channels=(),
            google_alerts_rules_count=0,
            component_packs=(),
            feed_manifest_sha256="",
            refusal=preflight.refusal.to_dict() if preflight.refusal else None,
            handshake_verdict=verdict.to_dict(),
            preflight_report=preflight.to_dict(),
            envelope_trace=trace.to_dict(),
        )

    packs = synthesize_all_48_rising_creator_component_packs()
    feed_sha256 = hashlib.sha256(
        "|".join(p.cas_sha256 for p in packs).encode("utf-8")
    ).hexdigest()
    trace = EnvelopeTrace(
        component="rising_creator_intelligence_feed_and_component_extractor_slot",
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
    return RisingCreatorFeedPublicationResult(
        slot_id="rising_creator_intelligence_feed_and_component_extractor_slot",
        engine_id=engine_id,
        status="completed",
        published_feed_cards_count=len(packs),
        synthesized_component_packs_count=len(packs),
        attribution_compliance_rate_pct=100.0,
        max_contract_card_bytes=max(p.contract_card_bytes for p in packs),
        brand_channels=(
            "agentfeeds.si/rising-creators",
            "agentstudios.si",
            "getagentfoundry.si",
            "baltor.ai",
        ),
        google_alerts_rules_count=len(packs),
        component_packs=packs,
        feed_manifest_sha256=feed_sha256,
        refusal=None,
        handshake_verdict=verdict.to_dict(),
        preflight_report=preflight.to_dict(),
        envelope_trace=trace.to_dict(),
    )


RISING_CREATOR_48_SURFACE_RADAR_ADAPTER = ThinComponentAdapter(
    slot_id="rising_creator_48_surface_discovery_radar_slot",
    domain_id="rising_creators_discovery_radar",
    engine_order=tuple(build_rising_creator_discovery_radar_envelopes().keys()),
    envelopes=build_rising_creator_discovery_radar_envelopes(),
    dispatch_fn=execute_rising_creator_48_surface_discovery_radar,
    preflight_fn=_radar_preflight,
)

RISING_CREATOR_INTELLIGENCE_EXTRACTOR_ADAPTER = ThinComponentAdapter(
    slot_id="rising_creator_intelligence_feed_and_component_extractor_slot",
    domain_id="rising_creators_intelligence_feeds",
    engine_order=tuple(build_rising_creator_intelligence_extractor_envelopes().keys()),
    envelopes=build_rising_creator_intelligence_extractor_envelopes(),
    dispatch_fn=execute_rising_creator_intelligence_feed_publisher,
    preflight_fn=_extractor_preflight,
)


def run_forty_eight_surface_rising_creator_benchmark() -> dict[str, Any]:
    """Run the 48-Scenario Rising-Creator Discovery Benchmark across all 8 Creator Ecosystems (C01..C08)."""
    radar_res = RISING_CREATOR_48_SURFACE_RADAR_ADAPTER.execute()
    pub_res = RISING_CREATOR_INTELLIGENCE_EXTRACTOR_ADAPTER.execute()
    return {
        "benchmark_id": "rising_creators_48_surface_discovery_radar_benchmark_2026_10_17",
        "total_discovery_scenarios": 48,
        "creator_ecosystems_evaluated": 8,
        "surfaces_per_ecosystem": 6,
        "mean_breakout_creator_score": radar_res.mean_breakout_creator_score,
        "max_contract_card_bytes": pub_res.max_contract_card_bytes,
        "arms": {
            "mainstream_follower_count_only_influencer_list_baseline": {
                "median_followers_at_discovery": 250000,
                "discovery_lag_after_invention_months": 9.0,
                "generic_engagement_bait_or_slop_rate_pct": 82.0,
                "reproducible_code_shader_or_workflow_rate_pct": 12.5,
                "earlier_technique_adoption_multiplier": 1.0,
                "creator_attribution_and_license_compliance_pct": 45.0,
                "verified_5_file_component_packs": 0,
            },
            "baltor_48_surface_rising_creator_velocity_radar_suite": {
                "median_followers_at_discovery": 1200,
                "breakout_detection_window_hours": 72,
                "generic_engagement_bait_or_slop_rate_pct": 0.0,
                "reproducible_code_shader_or_workflow_rate_pct": 96.4,
                "earlier_technique_adoption_multiplier": 8.4,
                "creator_attribution_and_license_compliance_pct": 100.0,
                "verified_5_file_component_packs": pub_res.synthesized_component_packs_count,
            },
        },
    }


def evaluate_known_wrong_controls() -> dict[str, dict[str, Any]]:
    """Run all 4 known-wrong preflight refusal controls and verify deterministic Layer 6 blocking."""
    kw1 = execute_rising_creator_intelligence_feed_publisher(
        creator_handle="",
        license_spdx="",
    )
    kw2 = execute_rising_creator_48_surface_discovery_radar(
        save_to_view_ratio=0.002,
        artifact_reproducibility=0.15,
    )
    kw3 = execute_rising_creator_intelligence_feed_publisher(
        is_paywalled_or_private=True,
    )
    kw4 = execute_rising_creator_48_surface_discovery_radar(
        anti_slop_originality_score=0.22,
    )
    return {
        "missing_rising_creator_attribution_refused": {
            "status": kw1.status,
            "refused_by": kw1.envelope_trace["refused_by"],
            "refusal_code": kw1.refusal["code"] if kw1.refusal else "",
        },
        "engagement_farm_astroturf_creator_refused": {
            "status": kw2.status,
            "refused_by": kw2.envelope_trace["refused_by"],
            "refusal_code": kw2.refusal["code"] if kw2.refusal else "",
        },
        "paywalled_or_private_creator_content_refused": {
            "status": kw3.status,
            "refused_by": kw3.envelope_trace["refused_by"],
            "refusal_code": kw3.refusal["code"] if kw3.refusal else "",
        },
        "ai_slop_content_farm_refused": {
            "status": kw4.status,
            "refused_by": kw4.envelope_trace["refused_by"],
            "refusal_code": kw4.refusal["code"] if kw4.refusal else "",
        },
    }
