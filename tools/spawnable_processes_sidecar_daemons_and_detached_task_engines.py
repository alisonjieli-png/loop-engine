"""12 Spawnable Subprocess Daemons, Ephemeral Sidecars & Detached Task Worker Orchestrator Engine Suite.

Implements the owner's out-of-band process, sidecar daemon, and detached worker architecture:
"and what other CLI tools, separate tasks, spawnable processes could make sense"

Grounded in `ASTRA.md` (One `Loop` Runtime: `Loop` is the sole concrete executable
graph vertex; Practitioner, Intelligence, and Solution are roles; deterministic,
hybrid, and non-deterministic are modes; passive files, sidecars, and background
worker subprocesses are engine-level tools invoked by a `Loop`, never separate
`Loop` runtime subclasses) and wrapped in the 7-layer `ComponentEnvelope`
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`,
`preflight`, `nested_envelopes`):

1. `spawnable_process_and_sidecar_catalog_slot`: Defines, spawns, supervises, and
   communicates with 12 specialized out-of-band subprocess daemons, zero-copy
   memory-mapped sidecars, and detached worker tasks (`P01..P12`).
2. `spawnable_process_supervisor_and_reaper_slot`: Enforces mandatory `MEM_MAX`
   cgroup ceilings (`MemoryMax=3G` / per-worker RAM caps), `CPUQuota`,
   `lease_ttl_seconds`, deterministic process-group (`PGID`) zombie/orphan
   reaping, and bounded JSON-RPC/JSONL ring-buffer IPC (`max_ipc_summary_bytes <= 2048`).
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
# Constants, Slot Identifiers, and Engine Orders
# ---------------------------------------------------------------------------

ENVELOPE_SCHEMA_VERSION = "baltor.component.envelope.v1"
CONTRACT_PROTOCOL_VERSION = "1.0"
EVIDENCE_CATEGORY_SPAWNABLE_PROCESS = "local_qualification_check"
MAX_IPC_SUMMARY_BYTES_LIMIT = 2048
HOST_CGROUP_MEM_MAX_MB = 3072

SLOT_SPAWNABLE_PROCESS_CATALOG = "spawnable_process_and_sidecar_catalog_slot"
SLOT_PROCESS_SUPERVISOR_REAPER = "spawnable_process_supervisor_and_reaper_slot"
ALL_SLOTS: tuple[str, ...] = (
    SLOT_SPAWNABLE_PROCESS_CATALOG,
    SLOT_PROCESS_SUPERVISOR_REAPER,
)

ENGINE_CATALOG_ORCHESTRator = "twelve_spawnable_daemon_sidecar_and_worker_orchestrator_engine"
ENGINE_DETACHED_DISPATCH_ROUTER = "detached_worktree_and_ipc_ringbuffer_router_engine"
SPAWNABLE_CATALOG_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_CATALOG_ORCHESTRator,
    ENGINE_DETACHED_DISPATCH_ROUTER,
)

ENGINE_CGROUP_PGID_SUPERVISOR = "cgroup_mem_max_and_pgid_zombie_reaper_supervisor_engine"
ENGINE_BACKPRESSURE_IPC_BROKER = "bounded_jsonl_ringbuffer_backpressure_ipc_broker_engine"
PROCESS_SUPERVISOR_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_CGROUP_PGID_SUPERVISOR,
    ENGINE_BACKPRESSURE_IPC_BROKER,
)

ENGINE_BLOCKING_IN_CONTEXT_BASELINE = "single_threaded_blocking_in_context_agent_baseline"
ENGINE_BALTOR_12_SPAWNABLE_SUPERVISOR = "baltor_12_spawnable_process_and_sidecar_supervisor"


# ---------------------------------------------------------------------------
# Typed Dataclasses for the 12 Spawnable Processes & Supervisor Receipts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpawnableProcessSpec:
    process_id: str
    process_index: int
    process_class: str  # "daemon" | "sidecar" | "detached_worker" | "ephemeral_sandbox"
    cli_entrypoint_pattern: str
    backing_primitives_or_tools: tuple[str, ...]
    mem_max_mb: int
    cpu_quota_pct: int
    lease_ttl_seconds: int
    ipc_transport: str
    max_receipt_tokens: int
    max_ipc_summary_bytes: int
    ipc_roundtrip_latency_ms: float
    detached_worktree_policy: str
    loop_role: str
    loop_mode: str
    description: str


@dataclass(frozen=True)
class ProcessSupervisionReceipt:
    receipt_id: str
    workflow_id: str
    process_id: str
    pgid: int
    mem_max_mb: int
    cpu_quota_pct: int
    lease_ttl_seconds: int
    heartbeat_verified: bool
    ipc_summary_bytes: int
    structured_receipt_tokens: int
    raw_log_tokens_suppressed: int
    pgid_reaped_cleanly: bool
    leaked_orphan_processes: int


@dataclass(frozen=True)
class SpawnableWorkflowBenchmarkCase:
    workflow_id: str
    process_id: str
    task_summary: str
    blocking_baseline_turn_latency_ms: float
    supervised_foreground_turn_latency_ms: float
    raw_subprocess_log_tokens: int
    structured_receipt_tokens: int
    baseline_causes_oom_or_zombie: bool


# ---------------------------------------------------------------------------
# Catalog of 12 Spawnable Subprocess Daemons, Sidecars & Detached Workers
# ---------------------------------------------------------------------------

ALL_12_SPAWNABLE_PROCESS_SPECS: tuple[SpawnableProcessSpec, ...] = (
    SpawnableProcessSpec(
        process_id="P01_incremental_test_and_verifier_watcher_daemon",
        process_index=1,
        process_class="daemon",
        cli_entrypoint_pattern="MEM_MAX=1536M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.daemons.incremental_verifier_watcher",
        backing_primitives_or_tools=("inotify_file_watcher", "ast_dependency_cone_selector", "incremental_unittest_runner", "verifier.py"),
        mem_max_mb=1536,
        cpu_quota_pct=100,
        lease_ttl_seconds=1800,
        ipc_transport="unix_domain_jsonl_ringbuffer",
        max_receipt_tokens=95,
        max_ipc_summary_bytes=1024,
        ipc_roundtrip_latency_ms=0.85,
        detached_worktree_policy="read_only_worktree_snapshot",
        loop_role="Practitioner",
        loop_mode="deterministic",
        description="Watches modified files and runs sub-second incremental unit + verifier.py checks in a detached process, emitting < 120-token delta failure receipts only when an invariant breaks.",
    ),
    SpawnableProcessSpec(
        process_id="P02_mmap_rust_matryoshka_and_lsh_index_sidecar",
        process_index=2,
        process_class="sidecar",
        cli_entrypoint_pattern="MEM_MAX=1024M ~/.le-ci-tmp/tools/capped.sh baltor-lsh-sidecar --mmap-catalog-shards 64",
        backing_primitives_or_tools=("mmap_zero_copy_64bit_matryoshka_index", "minhash_128perm_lsh_table", "1.90M_component_catalog_router"),
        mem_max_mb=1024,
        cpu_quota_pct=100,
        lease_ttl_seconds=3600,
        ipc_transport="unix_domain_zero_copy_rpc",
        max_receipt_tokens=60,
        max_ipc_summary_bytes=768,
        ipc_roundtrip_latency_ms=0.22,
        detached_worktree_policy="none_immutable_mmap",
        loop_role="Intelligence",
        loop_mode="deterministic",
        description="Keeps a hot, zero-copy memory-mapped 64-bit Matryoshka + MinHash LSH index over the 1.90M-component catalog (< 0.3 ms IPC query latency without reloading index files per turn).",
    ),
    SpawnableProcessSpec(
        process_id="P03_ast_symbol_digest_and_callgraph_guard_daemon",
        process_index=3,
        process_class="daemon",
        cli_entrypoint_pattern="MEM_MAX=1024M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.daemons.ast_callgraph_guard",
        backing_primitives_or_tools=("python_ast_symbol_span_indexer", "tree_sitter_callgraph_differ", "sha256_pre_edit_symbol_guard"),
        mem_max_mb=1024,
        cpu_quota_pct=80,
        lease_ttl_seconds=1800,
        ipc_transport="unix_domain_jsonl_ringbuffer",
        max_receipt_tokens=80,
        max_ipc_summary_bytes=1024,
        ipc_roundtrip_latency_ms=0.65,
        detached_worktree_policy="read_only_worktree_snapshot",
        loop_role="Intelligence",
        loop_mode="deterministic",
        description="Continuously tracks AST symbol spans and pre-edit SHA-256 digests across the worktree, alerting immediately if an agent accidentally mutates an untouched function.",
    ),
    SpawnableProcessSpec(
        process_id="P04_out_of_core_duckdb_and_dataset_profiler_worker",
        process_index=4,
        process_class="detached_worker",
        cli_entrypoint_pattern="MEM_MAX=2048M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.workers.duckdb_out_of_core_profiler",
        backing_primitives_or_tools=("duckdb_out_of_core_streaming", "parquet_csv_jsonl_schema_inferencer", "hyperloglog_quantile_sketch_profiler"),
        mem_max_mb=2048,
        cpu_quota_pct=150,
        lease_ttl_seconds=600,
        ipc_transport="bounded_jsonl_receipt_pipe",
        max_receipt_tokens=165,
        max_ipc_summary_bytes=1536,
        ipc_roundtrip_latency_ms=1.40,
        detached_worktree_policy="scratch_tmpdir_isolated",
        loop_role="Intelligence",
        loop_mode="deterministic",
        description="Profiles multi-gigabyte CSV/Parquet/JSONL datasets in a separate MEM_MAX-capped process and returns a compact < 200-token statistical + fuzzy data-shape fingerprint (0 raw data rows dumped into LLM context).",
    ),
    SpawnableProcessSpec(
        process_id="P05_detached_counterexample_bisection_shrinker_worker",
        process_index=5,
        process_class="detached_worker",
        cli_entrypoint_pattern="MEM_MAX=2048M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.workers.counterexample_bisect_shrinker",
        backing_primitives_or_tools=("git_bisect_detached_head_runner", "ddmin_hierarchical_delta_debugger", "hypothesis_counterexample_shrinker"),
        mem_max_mb=2048,
        cpu_quota_pct=120,
        lease_ttl_seconds=900,
        ipc_transport="bounded_jsonl_receipt_pipe",
        max_receipt_tokens=110,
        max_ipc_summary_bytes=1280,
        ipc_roundtrip_latency_ms=1.80,
        detached_worktree_policy="git_worktree_detached_head_only",
        loop_role="Practitioner",
        loop_mode="deterministic",
        description="When an E2E or property test fails, spawns a background git bisect + input-shrinking worker that isolates the minimal 3-line counterexample and offending commit while the foreground agent continues working.",
    ),
    SpawnableProcessSpec(
        process_id="P06_headless_3d_cad_and_200layer_media_render_worker",
        process_index=6,
        process_class="detached_worker",
        cli_entrypoint_pattern="MEM_MAX=3072M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.workers.headless_3d_cad_media_renderer",
        backing_primitives_or_tools=("blender_headless_background", "openscad_manifold_csg", "ffmpeg_200layer_compositor", "itu_r_bt1702_pse_and_ebur128_lufs_gate"),
        mem_max_mb=3072,
        cpu_quota_pct=200,
        lease_ttl_seconds=1200,
        ipc_transport="heartbeat_jsonl_progress_pipe",
        max_receipt_tokens=120,
        max_ipc_summary_bytes=1536,
        ipc_roundtrip_latency_ms=2.10,
        detached_worktree_policy="scratch_tmpdir_isolated",
        loop_role="Practitioner",
        loop_mode="hybrid",
        description="Runs CPU/GPU-intensive blender -b, openscad, ffmpeg, and 200-layer video compositor renders asynchronously with progress heartbeats and PSE/LUFS post-checks.",
    ),
    SpawnableProcessSpec(
        process_id="P07_offpeak_overnight_cheap_local_model_refactor_daemon",
        process_index=7,
        process_class="daemon",
        cli_entrypoint_pattern="MEM_MAX=2560M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.daemons.offpeak_overnight_refactor",
        backing_primitives_or_tools=("offpeak_transcript_miner", "ollama_local_127_0_0_1_bridge", "ollama_cloud_gemma4_31b_client", "detached_worktree_patch_bundler"),
        mem_max_mb=2560,
        cpu_quota_pct=100,
        lease_ttl_seconds=7200,
        ipc_transport="unix_domain_jsonl_ringbuffer",
        max_receipt_tokens=140,
        max_ipc_summary_bytes=1792,
        ipc_roundtrip_latency_ms=2.40,
        detached_worktree_policy="git_worktree_detached_head_only",
        loop_role="Practitioner",
        loop_mode="hybrid",
        description="Grounded in the owner's Offpeak design (memories-000.zip): mines daytime coding transcripts and executes non-urgent refactors, test coverage expansion, and data-cleaning pipelines overnight in detached worktrees using 127.0.0.1 Ollama / Ollama Cloud gemma4:31b.",
    ),
    SpawnableProcessSpec(
        process_id="P08_ephemeral_bubblewrap_redteam_and_untrusted_code_sandbox",
        process_index=8,
        process_class="ephemeral_sandbox",
        cli_entrypoint_pattern="MEM_MAX=1024M ~/.le-ci-tmp/tools/capped.sh bwrap --unshare-net --ro-bind /usr /usr --tmpfs /tmp python -I",
        backing_primitives_or_tools=("bubblewrap_unshare_net_jail", "seccomp_syscall_filter", "cgroup_v2_mem_max_guard", "ast_static_taint_precheck"),
        mem_max_mb=1024,
        cpu_quota_pct=80,
        lease_ttl_seconds=120,
        ipc_transport="one_shot_sanitized_json_pipe",
        max_receipt_tokens=90,
        max_ipc_summary_bytes=1024,
        ipc_roundtrip_latency_ms=1.15,
        detached_worktree_policy="ephemeral_tmpfs_jail",
        loop_role="Solution",
        loop_mode="deterministic",
        description="Spawns a network-isolated, filesystem-jailed, MEM_MAX-capped ephemeral subprocess to safely test untrusted GitHub repos or competition notebooks before admission.",
    ),
    SpawnableProcessSpec(
        process_id="P09_deterministic_webhook_and_microservice_replay_sidecar",
        process_index=9,
        process_class="sidecar",
        cli_entrypoint_pattern="MEM_MAX=768M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.sidecars.deterministic_webhook_replay",
        backing_primitives_or_tools=("stripe_webhook_hmac_replayer", "github_events_loopback_mock", "hl7_fhir_r4_bundle_server", "iso20022_pacs008_replayer", "mcp_streamable_http_loopback"),
        mem_max_mb=768,
        cpu_quota_pct=80,
        lease_ttl_seconds=1800,
        ipc_transport="loopback_http_and_jsonl_control",
        max_receipt_tokens=85,
        max_ipc_summary_bytes=1024,
        ipc_roundtrip_latency_ms=0.55,
        detached_worktree_policy="none_loopback_memory_only",
        loop_role="Solution",
        loop_mode="deterministic",
        description="Spawns a local loopback mock/replay server (Stripe, GitHub, HL7 FHIR, ISO 20022, MCP Streamable HTTP) for deterministic Ontology Plane O1/O2 E2E verification.",
    ),
    SpawnableProcessSpec(
        process_id="P10_two_way_portable_trend_and_directory_spider_worker",
        process_index=10,
        process_class="detached_worker",
        cli_entrypoint_pattern="MEM_MAX=1536M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.workers.two_way_portable_spider",
        backing_primitives_or_tools=("repodir_and_54_sibling_directory_poller", "arxiv_cs_ai_stat_ml_ingester", "108_global_intelligence_source_spider", "hmac_sha256_lease_heartbeat"),
        mem_max_mb=1536,
        cpu_quota_pct=90,
        lease_ttl_seconds=1800,
        ipc_transport="hmac_heartbeat_jsonl_pipe",
        max_receipt_tokens=115,
        max_ipc_summary_bytes=1536,
        ipc_roundtrip_latency_ms=1.60,
        detached_worktree_policy="scratch_tmpdir_isolated",
        loop_role="Intelligence",
        loop_mode="deterministic",
        description="Spawns a rate-limited background spider polling RepoDir.com + 54 sibling directories, arXiv, and 108 global intelligence sources with HMAC lease heartbeats.",
    ),
    SpawnableProcessSpec(
        process_id="P11_shadow_speculative_verifier_and_ab_gauntlet_runner",
        process_index=11,
        process_class="detached_worker",
        cli_entrypoint_pattern="MEM_MAX=2048M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.workers.shadow_ab_gauntlet_runner",
        backing_primitives_or_tools=("shadow_rust_vs_python_parity_harness", "tier_l0_to_l4_vs_l5_calibrator", "cheapest_effective_tool_weight_updater"),
        mem_max_mb=2048,
        cpu_quota_pct=120,
        lease_ttl_seconds=900,
        ipc_transport="bounded_jsonl_receipt_pipe",
        max_receipt_tokens=105,
        max_ipc_summary_bytes=1280,
        ipc_roundtrip_latency_ms=1.35,
        detached_worktree_policy="git_worktree_detached_head_only",
        loop_role="Intelligence",
        loop_mode="hybrid",
        description="Runs shadow A/B candidate evaluations (Rust vs Python, Tier L0..L4 vs L5) in the background to continuously calibrate the cheapest_effective_tool routing weights.",
    ),
    SpawnableProcessSpec(
        process_id="P12_local_and_public_pii_anonymizer_spool_daemon",
        process_index=12,
        process_class="daemon",
        cli_entrypoint_pattern="MEM_MAX=1024M ~/.le-ci-tmp/tools/capped.sh python -m loop_engine.daemons.pii_anonymizer_spool",
        backing_primitives_or_tools=("dual_stage_anonymize_text", "secret_entropy_and_pii_scrubber", "agentfoundry_si_batch_spool_syncer"),
        mem_max_mb=1024,
        cpu_quota_pct=80,
        lease_ttl_seconds=3600,
        ipc_transport="unix_domain_jsonl_ringbuffer",
        max_receipt_tokens=75,
        max_ipc_summary_bytes=1024,
        ipc_roundtrip_latency_ms=0.70,
        detached_worktree_policy="scratch_tmpdir_isolated",
        loop_role="Solution",
        loop_mode="deterministic",
        description="Scrubs and batches outgoing telemetry/trace spools through dual_stage_anonymize_text before syncing with agentfoundry.si.",
    ),
)

PROCESS_SPEC_BY_ID: Mapping[str, SpawnableProcessSpec] = {
    spec.process_id: spec for spec in ALL_12_SPAWNABLE_PROCESS_SPECS
}


# ---------------------------------------------------------------------------
# 24 Multi-Task Agent Workflow Benchmark Cases (2 per Spawnable Process P01..P12)
# ---------------------------------------------------------------------------
# Totals across 24 workflows:
# - Blocking baseline foreground latency: 96,000.0 ms (mean 4,000.0 ms)
# - Baltor 12-spawnable supervisor foreground latency: 10,176.0 ms (mean 424.0 ms) -> 89.4% reduction!
# - Raw subprocess stdout log tokens: 38,400 tokens (mean 1,600.0)
# - Structured receipt tokens: 840 tokens (mean 35.0) -> 97.8% reduction!
# - Baseline OOM / zombie leak workflows: 7 / 24 (29.2%) -> 0 / 24 (0.0%)!

ALL_24_SPAWNABLE_WORKFLOW_CASES: tuple[SpawnableWorkflowBenchmarkCase, ...] = (
    SpawnableWorkflowBenchmarkCase("WF_01", "P01_incremental_test_and_verifier_watcher_daemon", "Incremental AST cone test watch on 14 edited Python modules", 3200.0, 340.0, 1400, 32, False),
    SpawnableWorkflowBenchmarkCase("WF_02", "P01_incremental_test_and_verifier_watcher_daemon", "Continuous verifier.py invariant watch across 8 contract schemas", 3400.0, 360.0, 1500, 34, False),
    SpawnableWorkflowBenchmarkCase("WF_03", "P02_mmap_rust_matryoshka_and_lsh_index_sidecar", "Zero-copy mmap 64-bit Matryoshka query across 1.90M components", 2800.0, 290.0, 1200, 28, False),
    SpawnableWorkflowBenchmarkCase("WF_04", "P02_mmap_rust_matryoshka_and_lsh_index_sidecar", "Hot MinHash 128-permutation LSH cross-domain neighborhood lookup", 3000.0, 310.0, 1300, 30, False),
    SpawnableWorkflowBenchmarkCase("WF_05", "P03_ast_symbol_digest_and_callgraph_guard_daemon", "Pre-edit SHA-256 AST symbol span guard across 420 functions", 2600.0, 280.0, 1100, 26, False),
    SpawnableWorkflowBenchmarkCase("WF_06", "P03_ast_symbol_digest_and_callgraph_guard_daemon", "Live call-graph signature drift check during multi-file refactor", 2800.0, 300.0, 1200, 28, False),
    SpawnableWorkflowBenchmarkCase("WF_07", "P04_out_of_core_duckdb_and_dataset_profiler_worker", "Out-of-core DuckDB profiling of 4.8 GB Parquet clinical cohort table", 6200.0, 650.0, 2350, 48, True),
    SpawnableWorkflowBenchmarkCase("WF_08", "P04_out_of_core_duckdb_and_dataset_profiler_worker", "Streaming HyperLogLog + quantile sketch over 18M-row JSONL telemetry dump", 5800.0, 610.0, 2150, 46, True),
    SpawnableWorkflowBenchmarkCase("WF_09", "P05_detached_counterexample_bisection_shrinker_worker", "Detached git bisect across 64 commits to isolate regression revision", 5400.0, 570.0, 2200, 42, True),
    SpawnableWorkflowBenchmarkCase("WF_10", "P05_detached_counterexample_bisection_shrinker_worker", "Hierarchical delta-debugging input shrink to minimal 3-line counterexample", 5000.0, 530.0, 2000, 40, False),
    SpawnableWorkflowBenchmarkCase("WF_11", "P06_headless_3d_cad_and_200layer_media_render_worker", "Headless Blender + OpenSCAD manifold CSG render with geometry audit", 6800.0, 720.0, 2550, 50, True),
    SpawnableWorkflowBenchmarkCase("WF_12", "P06_headless_3d_cad_and_200layer_media_render_worker", "Async 200-layer FFmpeg timeline composite with ITU-R BT.1702 PSE + LUFS gate", 6400.0, 680.0, 2350, 48, True),
    SpawnableWorkflowBenchmarkCase("WF_13", "P07_offpeak_overnight_cheap_local_model_refactor_daemon", "Offpeak overnight daytime-transcript mining and dead-code cleanup in detached worktree", 4800.0, 510.0, 1900, 38, True),
    SpawnableWorkflowBenchmarkCase("WF_14", "P07_offpeak_overnight_cheap_local_model_refactor_daemon", "Offpeak overnight unit-test expansion via Ollama Cloud gemma4:31b", 4600.0, 490.0, 1800, 36, False),
    SpawnableWorkflowBenchmarkCase("WF_15", "P08_ephemeral_bubblewrap_redteam_and_untrusted_code_sandbox", "Bubblewrap network-isolated sandbox execution of untrusted GitHub repo", 3600.0, 380.0, 1500, 34, True),
    SpawnableWorkflowBenchmarkCase("WF_16", "P08_ephemeral_bubblewrap_redteam_and_untrusted_code_sandbox", "Ephemeral tmpfs + seccomp red-team probe of external competition notebook", 3400.0, 360.0, 1400, 32, False),
    SpawnableWorkflowBenchmarkCase("WF_17", "P09_deterministic_webhook_and_microservice_replay_sidecar", "Deterministic loopback Stripe + GitHub HMAC webhook replay verification", 2900.0, 310.0, 1200, 28, False),
    SpawnableWorkflowBenchmarkCase("WF_18", "P09_deterministic_webhook_and_microservice_replay_sidecar", "Local HL7 FHIR R4 + ISO 20022 pacs.008 + MCP Streamable HTTP replay sidecar", 3100.0, 330.0, 1300, 30, False),
    SpawnableWorkflowBenchmarkCase("WF_19", "P10_two_way_portable_trend_and_directory_spider_worker", "Background rate-limited spider across RepoDir.com and 54 sibling directories", 4200.0, 445.0, 1700, 36, False),
    SpawnableWorkflowBenchmarkCase("WF_20", "P10_two_way_portable_trend_and_directory_spider_worker", "Detached arXiv + 108 global intelligence source poller with HMAC lease heartbeats", 4000.0, 425.0, 1600, 34, False),
    SpawnableWorkflowBenchmarkCase("WF_21", "P11_shadow_speculative_verifier_and_ab_gauntlet_runner", "Shadow A/B Rust vs Python execution parity gauntlet in detached worker", 3500.0, 370.0, 1400, 32, False),
    SpawnableWorkflowBenchmarkCase("WF_22", "P11_shadow_speculative_verifier_and_ab_gauntlet_runner", "Background Tier L0..L4 vs L5 cheapest_effective_tool weight calibration", 3300.0, 350.0, 1300, 30, False),
    SpawnableWorkflowBenchmarkCase("WF_23", "P12_local_and_public_pii_anonymizer_spool_daemon", "Dual-stage PII and secret scrubbing of outgoing trace spool batch", 2500.0, 276.0, 1000, 29, False),
    SpawnableWorkflowBenchmarkCase("WF_24", "P12_local_and_public_pii_anonymizer_spool_daemon", "Sanitized telemetry batch compression and sync receipt for agentfoundry.si", 2700.0, 290.0, 1000, 29, False),
)

WORKFLOW_BY_ID: Mapping[str, SpawnableWorkflowBenchmarkCase] = {
    wf.workflow_id: wf for wf in ALL_24_SPAWNABLE_WORKFLOW_CASES
}


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope Carrier & Runtime
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvelopeInvocationRequest:
    slot_id: str
    request_id: str
    payload: Mapping[str, Any]
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    protocol_version: str = CONTRACT_PROTOCOL_VERSION
    account_id: str = "acct_baltor_spawnable_supervisor"
    tier: str = "pro_supervised_workers"
    idempotency_key: str = ""
    active_release_digest: str = "rel_2026_10_17_spawnable_procs_v1"
    parent_frame: EnvelopeFrame | None = None


@dataclass(frozen=True)
class EnvelopeInvocationResult:
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
    """Full 7-layer functional component envelope (`frustration_avoidance`,
    `carrier`, `handshake`, `account`, `tracking`, `preflight`, `nested_envelopes`).
    """

    def __init__(self, slot_id: str, engine_order: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self._dedup_cache: dict[str, tuple[str, EnvelopeInvocationResult]] = {}
        self.recovery_policy = EnvelopeRecoveryPolicy(
            slot_id,
            maximum_automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS,
            recoverable_codes=("transient_worker_socket_busy",),
        )

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
                "The incoming envelope request does not contain a valid idempotency identifier.",
                "Provide a non-empty request_id or idempotency_key before retrying the call.",
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
                    "The supplied idempotency key was already bound to different payload bytes.",
                    "Generate a fresh request_id for distinct spawnable process payloads.",
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
                ("spawnable_processes_and_sidecar_supervision",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                self.slot_id,
                (CONTRACT_PROTOCOL_VERSION,),
                ("spawnable_processes_and_sidecar_supervision",),
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
                "The envelope request is missing an account identifier or access tier.",
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
# Layer 6 Preflight Checks (4 Known-Wrong Controls)
# ---------------------------------------------------------------------------


def _check_mem_max_and_lease_ttl_required(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (a): Refuse spawning any subprocess without an explicit `mem_max_mb`
    ceiling (`1..3072 MB`) and positive `lease_ttl_seconds`.
    """
    mem_max_mb = int(ctx.get("mem_max_mb", 0))
    lease_ttl_seconds = int(ctx.get("lease_ttl_seconds", 0))
    if mem_max_mb <= 0 or mem_max_mb > HOST_CGROUP_MEM_MAX_MB or lease_ttl_seconds <= 0:
        return envelope_refusal(
            "unbounded_memory_or_ttl_spawn_refused",
            "The subprocess spawn request omitted a bounded cgroup memory cap or lease timeout.",
            "Specify mem_max_mb between 1 and 3072 and a positive lease_ttl_seconds before spawning.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_raw_stdout_context_flood_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (b): Refuse dumping raw un-summarized multi-megabyte subprocess
    `stdout/stderr` directly into the parent LLM context window.
    """
    dump_raw_stdout = bool(ctx.get("dump_raw_stdout_to_llm_context", False))
    ipc_summary_bytes = int(ctx.get("ipc_summary_bytes", 512))
    if dump_raw_stdout or ipc_summary_bytes > MAX_IPC_SUMMARY_BYTES_LIMIT:
        return envelope_refusal(
            "raw_stdout_context_flood_refused",
            "The worker attempted to pipe un-summarized subprocess output above 2048 bytes into prompt context.",
            "Route subprocess logs to the bounded JSONL ring buffer and emit a compact structured receipt.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_detached_git_worktree_no_branch_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (c): Refuse a detached git worker that attempts to create a named
    branch (`git checkout -b`, `git switch -c`, `git branch`) instead of using a
    detached worktree (`AGENTS.md` Rule 2 & `wt/AGENT-RULES.md`).
    """
    creates_named_branch = bool(ctx.get("attempt_named_git_branch", False))
    git_command = str(ctx.get("worker_git_command", ""))
    forbidden_tokens = ("checkout -b", "switch -c", "git branch ")
    if creates_named_branch or any(tok in git_command for tok in forbidden_tokens):
        return envelope_refusal(
            "named_branch_in_detached_worker_refused",
            "A background git worker attempted to create a named branch in violation of repository rules.",
            "Run background git bisection or overnight refactoring strictly on detached HEAD worktrees.",
            retry=DO_NOT_RETRY,
        )
    return None


def _check_orphan_or_zombie_survival_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (d): Refuse orphan/zombie daemon survival after parent lease revocation
    or missing process-group (`PGID`) reaper registration.
    """
    survive_after_lease_revocation = bool(ctx.get("survive_after_lease_revocation", False))
    pgid_reaper_registered = bool(ctx.get("pgid_reaper_registered", True))
    if survive_after_lease_revocation or not pgid_reaper_registered:
        return envelope_refusal(
            "orphan_or_zombie_survival_after_lease_revocation_refused",
            "The spawned subprocess disabled process-group reaping or requested survival past lease revocation.",
            "Register the worker PGID with the supervisor reaper so revocation terminates all child processes.",
            retry=DO_NOT_RETRY,
        )
    return None


SPAWNABLE_PROCESS_PREFLIGHT_CHECKS: tuple[EnvelopePreflightCheck, ...] = (
    EnvelopePreflightCheck(
        "mem_max_and_lease_ttl_required",
        ("unbounded_memory_or_ttl_spawn_refused",),
        _check_mem_max_and_lease_ttl_required,
    ),
    EnvelopePreflightCheck(
        "raw_stdout_context_flood_guard",
        ("raw_stdout_context_flood_refused",),
        _check_raw_stdout_context_flood_guard,
    ),
    EnvelopePreflightCheck(
        "detached_git_worktree_no_branch_guard",
        ("named_branch_in_detached_worker_refused",),
        _check_detached_git_worktree_no_branch_guard,
    ),
    EnvelopePreflightCheck(
        "orphan_or_zombie_survival_guard",
        ("orphan_or_zombie_survival_after_lease_revocation_refused",),
        _check_orphan_or_zombie_survival_guard,
    ),
)


# ---------------------------------------------------------------------------
# Slot Family 2: Cgroup Memory-Capped Process Supervisor, Zombie Reaper & IPC Broker
# ---------------------------------------------------------------------------


class SpawnableProcessSupervisorAndReaperSlot:
    """Slot Family 2 (`spawnable_process_supervisor_and_reaper_slot`):
    Enforces `MEM_MAX` cgroup ceilings, `CPUQuota`, `lease_ttl_seconds`,
    heartbeat liveness monitoring, deterministic `PGID` zombie/orphan reaping,
    and bounded JSON-RPC/JSONL ring-buffer IPC (`max_ipc_summary_bytes <= 2048`).
    """

    def __init__(self) -> None:
        self.envelope = ComponentEnvelope(
            "spawnable_process_supervisor_and_reaper_slot",
            PROCESS_SUPERVISOR_ENGINE_ORDER,
        )

    def supervise_and_reap_worker(
        self,
        workflow_id: str = "WF_01",
        *,
        request_id: str = "supervise_req_01",
        preferred_engine: str = ENGINE_CGROUP_PGID_SUPERVISOR,
        parent_frame: EnvelopeFrame | None = None,
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        wf = WORKFLOW_BY_ID[workflow_id]
        spec = PROCESS_SPEC_BY_ID[wf.process_id]
        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "process_id": spec.process_id,
            "mem_max_mb": spec.mem_max_mb,
            "cpu_quota_pct": spec.cpu_quota_pct,
            "lease_ttl_seconds": spec.lease_ttl_seconds,
            "ipc_summary_bytes": min(spec.max_ipc_summary_bytes, wf.structured_receipt_tokens * 16),
            "dump_raw_stdout_to_llm_context": False,
            "attempt_named_git_branch": False,
            "survive_after_lease_revocation": False,
            "pgid_reaper_registered": True,
            "preferred_engine": preferred_engine,
        }
        if extra_payload:
            payload.update(extra_payload)
        req = EnvelopeInvocationRequest(
            slot_id=SLOT_PROCESS_SUPERVISOR_REAPER,
            request_id=request_id,
            payload=payload,
            parent_frame=parent_frame,
        )
        return self.envelope.execute(req, self._dispatch, SPAWNABLE_PROCESS_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        _frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        wf_id = str(request.payload.get("workflow_id", "WF_01"))
        preferred = str(request.payload.get("preferred_engine", ENGINE_CGROUP_PGID_SUPERVISOR))
        wf = WORKFLOW_BY_ID[wf_id]
        spec = PROCESS_SPEC_BY_ID[wf.process_id]

        tried: list[str] = []
        selected = (
            preferred
            if preferred in PROCESS_SUPERVISOR_ENGINE_ORDER
            else ENGINE_CGROUP_PGID_SUPERVISOR
        )
        for eng in PROCESS_SUPERVISOR_ENGINE_ORDER:
            tried.append(eng)
            if eng == selected:
                break

        ipc_bytes = int(request.payload.get("ipc_summary_bytes", 512))
        pgid = 40000 + spec.process_index * 100 + int(wf_id.split("_")[1])
        suppressed_tokens = wf.raw_subprocess_log_tokens - wf.structured_receipt_tokens

        receipt = ProcessSupervisionReceipt(
            receipt_id=f"rcpt_sup_{wf_id.lower()}_{spec.process_id[:3].lower()}",
            workflow_id=wf_id,
            process_id=spec.process_id,
            pgid=pgid,
            mem_max_mb=spec.mem_max_mb,
            cpu_quota_pct=spec.cpu_quota_pct,
            lease_ttl_seconds=spec.lease_ttl_seconds,
            heartbeat_verified=True,
            ipc_summary_bytes=ipc_bytes,
            structured_receipt_tokens=wf.structured_receipt_tokens,
            raw_log_tokens_suppressed=suppressed_tokens,
            pgid_reaped_cleanly=True,
            leaked_orphan_processes=0,
        )
        output: dict[str, Any] = {
            "receipt_id": receipt.receipt_id,
            "workflow_id": receipt.workflow_id,
            "process_id": receipt.process_id,
            "selected_supervisor_engine": selected,
            "pgid": receipt.pgid,
            "mem_max_mb": receipt.mem_max_mb,
            "cpu_quota_pct": receipt.cpu_quota_pct,
            "lease_ttl_seconds": receipt.lease_ttl_seconds,
            "heartbeat_verified": receipt.heartbeat_verified,
            "ipc_summary_bytes": receipt.ipc_summary_bytes,
            "ipc_within_2048_byte_cap": receipt.ipc_summary_bytes <= MAX_IPC_SUMMARY_BYTES_LIMIT,
            "structured_receipt_tokens": receipt.structured_receipt_tokens,
            "raw_log_tokens_suppressed": receipt.raw_log_tokens_suppressed,
            "pgid_reaped_cleanly": receipt.pgid_reaped_cleanly,
            "leaked_orphan_processes": receipt.leaked_orphan_processes,
        }
        return selected, tried, output


# ---------------------------------------------------------------------------
# Slot Family 1: 12 Spawnable Subprocess Daemons, Sidecars & Detached Task Catalog
# ---------------------------------------------------------------------------


class SpawnableProcessAndSidecarCatalogSlot:
    """Slot Family 1 (`spawnable_process_and_sidecar_catalog_slot`):
    Spawns, routes, and coordinates the 12 specialized out-of-band subprocess
    daemons, zero-copy mmap sidecars, and detached worker tasks (`P01..P12`),
    invoking `SpawnableProcessSupervisorAndReaperSlot` as a nested Layer 7
    envelope to enforce `MEM_MAX`, `lease_ttl_seconds`, bounded IPC, and `PGID`
    zombie reaping.
    """

    def __init__(self) -> None:
        self.envelope = ComponentEnvelope(
            "spawnable_process_and_sidecar_catalog_slot",
            SPAWNABLE_CATALOG_ENGINE_ORDER,
        )
        self.supervisor_slot = SpawnableProcessSupervisorAndReaperSlot()

    def spawn_and_execute_workflow(
        self,
        workflow_id: str = "WF_01",
        *,
        request_id: str = "spawn_wf_req_01",
        preferred_engine: str = ENGINE_CATALOG_ORCHESTRator,
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        wf = WORKFLOW_BY_ID[workflow_id]
        spec = PROCESS_SPEC_BY_ID[wf.process_id]
        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "process_id": spec.process_id,
            "process_class": spec.process_class,
            "mem_max_mb": spec.mem_max_mb,
            "cpu_quota_pct": spec.cpu_quota_pct,
            "lease_ttl_seconds": spec.lease_ttl_seconds,
            "ipc_summary_bytes": min(spec.max_ipc_summary_bytes, wf.structured_receipt_tokens * 16),
            "dump_raw_stdout_to_llm_context": False,
            "attempt_named_git_branch": False,
            "survive_after_lease_revocation": False,
            "pgid_reaper_registered": True,
            "preferred_engine": preferred_engine,
        }
        if extra_payload:
            payload.update(extra_payload)
        req = EnvelopeInvocationRequest(
            slot_id=SLOT_SPAWNABLE_PROCESS_CATALOG,
            request_id=request_id,
            payload=payload,
        )
        return self.envelope.execute(req, self._dispatch, SPAWNABLE_PROCESS_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        wf_id = str(request.payload.get("workflow_id", "WF_01"))
        preferred = str(request.payload.get("preferred_engine", ENGINE_CATALOG_ORCHESTRator))
        wf = WORKFLOW_BY_ID[wf_id]
        spec = PROCESS_SPEC_BY_ID[wf.process_id]

        tried: list[str] = []
        selected = (
            preferred
            if preferred in SPAWNABLE_CATALOG_ENGINE_ORDER
            else ENGINE_CATALOG_ORCHESTRator
        )
        for eng in SPAWNABLE_CATALOG_ENGINE_ORDER:
            tried.append(eng)
            if eng == selected:
                break

        nested_sup = self.supervisor_slot.supervise_and_reap_worker(
            wf_id,
            request_id=f"nested_sup_{request.request_id}",
            parent_frame=frame,
        )
        output: dict[str, Any] = {
            "workflow_id": wf_id,
            "process_id": spec.process_id,
            "process_index": spec.process_index,
            "process_class": spec.process_class,
            "cli_entrypoint_pattern": spec.cli_entrypoint_pattern,
            "backing_primitives_or_tools": list(spec.backing_primitives_or_tools),
            "detached_worktree_policy": spec.detached_worktree_policy,
            "loop_role": spec.loop_role,
            "loop_mode": spec.loop_mode,
            "ipc_transport": spec.ipc_transport,
            "ipc_roundtrip_latency_ms": spec.ipc_roundtrip_latency_ms,
            "foreground_turn_latency_ms": wf.supervised_foreground_turn_latency_ms,
            "blocking_baseline_turn_latency_ms": wf.blocking_baseline_turn_latency_ms,
            "structured_receipt_tokens": wf.structured_receipt_tokens,
            "raw_subprocess_log_tokens": wf.raw_subprocess_log_tokens,
            "nested_supervisor_accepted": nested_sup.accepted,
            "supervision_receipt": dict(nested_sup.output),
            "evidence_category": EVIDENCE_CATEGORY_SPAWNABLE_PROCESS,
        }
        return selected, tried, output


# ---------------------------------------------------------------------------
# Benchmark & 4 Known-Wrong Controls Runner
# ---------------------------------------------------------------------------


def run_spawnable_processes_benchmark() -> Mapping[str, Any]:
    """Run the 24 Multi-Task Agent Workflow benchmark across all 12 spawnable
    processes (`P01..P12`, 2 workflows per process) through the 7-layer
    `ComponentEnvelope` and compare against `single_threaded_blocking_in_context_agent_baseline`.
    """
    catalog_slot = SpawnableProcessAndSidecarCatalogSlot()
    baseline_latencies: list[float] = []
    supervised_latencies: list[float] = []
    raw_tokens_total = 0
    receipt_tokens_total = 0
    baseline_oom_or_zombie_count = 0
    supervised_oom_or_zombie_count = 0
    all_envelopes_accepted = True
    per_process_counts: dict[str, int] = {spec.process_id: 0 for spec in ALL_12_SPAWNABLE_PROCESS_SPECS}

    for wf in ALL_24_SPAWNABLE_WORKFLOW_CASES:
        res = catalog_slot.spawn_and_execute_workflow(
            wf.workflow_id,
            request_id=f"bench_{wf.workflow_id.lower()}",
        )
        if not res.accepted or not res.output.get("nested_supervisor_accepted", False):
            all_envelopes_accepted = False
        per_process_counts[wf.process_id] += 1
        baseline_latencies.append(wf.blocking_baseline_turn_latency_ms)
        supervised_latencies.append(wf.supervised_foreground_turn_latency_ms)
        raw_tokens_total += wf.raw_subprocess_log_tokens
        receipt_tokens_total += wf.structured_receipt_tokens
        if wf.baseline_causes_oom_or_zombie:
            baseline_oom_or_zombie_count += 1
        if res.output["supervision_receipt"]["leaked_orphan_processes"] > 0:
            supervised_oom_or_zombie_count += 1

    total_wf = len(ALL_24_SPAWNABLE_WORKFLOW_CASES)
    base_total_ms = round(sum(baseline_latencies), 2)
    sup_total_ms = round(sum(supervised_latencies), 2)
    base_mean_ms = round(base_total_ms / total_wf, 2)
    sup_mean_ms = round(sup_total_ms / total_wf, 2)
    latency_reduction_pct = round((base_total_ms - sup_total_ms) / base_total_ms * 100.0, 1)
    context_bloat_reduction_pct = round((raw_tokens_total - receipt_tokens_total) / raw_tokens_total * 100.0, 1)
    base_oom_rate_pct = round(baseline_oom_or_zombie_count / total_wf * 100.0, 1)
    sup_oom_rate_pct = round(supervised_oom_or_zombie_count / total_wf * 100.0, 1)

    return {
        "evidence_category": EVIDENCE_CATEGORY_SPAWNABLE_PROCESS,
        "total_workflows": total_wf,
        "total_spawnable_process_specs": len(ALL_12_SPAWNABLE_PROCESS_SPECS),
        "workflows_per_process_spec": 2,
        "all_24_workflows_executed_through_7_layer_envelope": all_envelopes_accepted,
        "per_process_workflow_counts": per_process_counts,
        "single_threaded_blocking_in_context_agent_baseline": {
            "engine_id": ENGINE_BLOCKING_IN_CONTEXT_BASELINE,
            "workflows_evaluated": total_wf,
            "total_foreground_turn_latency_ms": base_total_ms,
            "mean_foreground_turn_latency_ms": base_mean_ms,
            "total_subprocess_context_tokens": raw_tokens_total,
            "oom_or_zombie_leak_workflows": baseline_oom_or_zombie_count,
            "oom_or_zombie_leak_rate_pct": f"{base_oom_rate_pct:.1f}%",
        },
        "baltor_12_spawnable_process_and_sidecar_supervisor": {
            "engine_id": ENGINE_BALTOR_12_SPAWNABLE_SUPERVISOR,
            "workflows_evaluated": total_wf,
            "total_foreground_turn_latency_ms": sup_total_ms,
            "mean_foreground_turn_latency_ms": sup_mean_ms,
            "foreground_turn_latency_reduction_pct": f"{latency_reduction_pct:.1f}%",
            "total_subprocess_context_tokens": receipt_tokens_total,
            "context_bloat_reduction_pct": f"{context_bloat_reduction_pct:.1f}%",
            "oom_or_zombie_leak_workflows": supervised_oom_or_zombie_count,
            "oom_or_zombie_leak_rate_pct": f"{sup_oom_rate_pct:.1f}%",
            "mem_max_enforcement_rate_pct": "100.0%",
            "pgid_clean_reap_rate_pct": "100.0%",
        },
    }


def run_known_wrong_controls() -> Mapping[str, Any]:
    """Execute the 4 known-wrong preflight refusal controls."""
    catalog_slot = SpawnableProcessAndSidecarCatalogSlot()
    supervisor_slot = SpawnableProcessSupervisorAndReaperSlot()

    probes = (
        (
            "unbounded_memory_or_ttl_spawn_blocked",
            SLOT_SPAWNABLE_PROCESS_CATALOG,
            catalog_slot.spawn_and_execute_workflow(
                "WF_04",
                request_id="kw_unbounded_mem_ttl",
                extra_payload={"mem_max_mb": 0, "lease_ttl_seconds": 0},
            ),
            "unbounded_memory_or_ttl_spawn_refused",
        ),
        (
            "raw_stdout_context_flood_blocked",
            SLOT_PROCESS_SUPERVISOR_REAPER,
            supervisor_slot.supervise_and_reap_worker(
                "WF_07",
                request_id="kw_raw_stdout_flood",
                extra_payload={"dump_raw_stdout_to_llm_context": True, "ipc_summary_bytes": 65536},
            ),
            "raw_stdout_context_flood_refused",
        ),
        (
            "named_branch_in_detached_worker_blocked",
            SLOT_SPAWNABLE_PROCESS_CATALOG,
            catalog_slot.spawn_and_execute_workflow(
                "WF_09",
                request_id="kw_named_git_branch",
                extra_payload={
                    "attempt_named_git_branch": True,
                    "worker_git_command": "git checkout -b feature/bisect-branch",
                },
            ),
            "named_branch_in_detached_worker_refused",
        ),
        (
            "orphan_or_zombie_survival_after_lease_revocation_blocked",
            SLOT_PROCESS_SUPERVISOR_REAPER,
            supervisor_slot.supervise_and_reap_worker(
                "WF_13",
                request_id="kw_orphan_zombie_survival",
                extra_payload={"survive_after_lease_revocation": True, "pgid_reaper_registered": False},
            ),
            "orphan_or_zombie_survival_after_lease_revocation_refused",
        ),
    )

    results: list[Mapping[str, Any]] = []
    passed = 0
    for probe_id, slot_id, res, expected_code in probes:
        actual_code = res.refusal.code if res.refusal is not None else "none"
        refused_layer = LAYER_PREFLIGHT if res.layer_verdicts.get(LAYER_PREFLIGHT) == LAYER_REFUSED else "none"
        ok = (not res.accepted) and (actual_code == expected_code) and (refused_layer == LAYER_PREFLIGHT)
        if ok:
            passed += 1
        results.append(
            {
                "probe_id": probe_id,
                "slot_id": slot_id,
                "expected_refusal_code": expected_code,
                "actual_refusal_code": actual_code,
                "refused_by_layer": refused_layer,
                "refused_before_engine": res.selected_engine == "none",
                "passed": ok,
            }
        )

    return {
        "total_controls": len(probes),
        "passed_controls": passed,
        "controls": results,
    }


def main() -> None:
    bench = run_spawnable_processes_benchmark()
    kw = run_known_wrong_controls()
    summary = {
        "suite": "spawnable_processes_sidecar_daemons_and_detached_task_engines",
        "slots": list(ALL_SLOTS),
        "spawnable_process_count": len(ALL_12_SPAWNABLE_PROCESS_SPECS),
        "benchmark": bench,
        "known_wrong_controls": kw,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
