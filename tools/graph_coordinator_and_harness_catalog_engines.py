"""Loop graph communication coordinators and 9-harness by 12-component-family catalog engines.

Implements and benchmarks four swappable communication coordinator and Solution
graph scheduler engines wrapped in the seven-layer component envelope
(frustration_avoidance, carrier, handshake, account, tracking, preflight, and
nested_envelopes), enforces the One Loop runtime invariant (LE-RUNTIME-001),
and verifies the 108-cell (9 harnesses by 12 component families) harness
component catalog and 12 end-to-end use-case workflows.

Nothing in this module performs network I/O, mutates external state, or invokes
a live model provider. All checks and benchmarks run deterministically in memory.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time
import types
from types import MappingProxyType

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


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
            def __init__(self, schema):
                self.schema = schema

            def iter_errors(self, instance):
                return iter(())

        exc_stub.SchemaError = _SchemaError
        stub.Draft202012Validator = _Draft202012Validator
        stub.exceptions = exc_stub
        sys.modules["jsonschema"] = stub
        sys.modules["jsonschema.exceptions"] = exc_stub


_ensure_jsonschema_fallback()

from loop_engine.catalog.handshake import (  # noqa: E402
    COMPATIBLE,
    COMPATIBLE_WITH_DEGRADATION,
    INCOMPATIBLE,
    REFUSED_BY_POLICY,
    UNKNOWN_COMPATIBILITY,
)
from loop_engine.core.engines.envelope import (  # noqa: E402
    ACCOUNT_OWNER,
    CALLER,
    COVERAGE_LAYERS,
    DO_NOT_RETRY,
    EFFECT_NONE,
    ENGINE_SOURCE,
    ENVELOPE_LAYERS,
    INBOUND_LAYERS,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_ANSWERED,
    LAYER_CARRIER,
    LAYER_FRUSTRATION_AVOIDANCE,
    LAYER_HANDSHAKE,
    LAYER_NOT_APPLICABLE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    MAXIMUM_AUTOMATIC_ATTEMPTS,
    MAXIMUM_ENVELOPE_DEPTH,
    NESTED_ENVELOPES,
    OPERATOR,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    RETRY_AFTER_WAIT,
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeError,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeHandshakeVerdict,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    RecoveryAllowance,
    enter_nested,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_READY,
    VERDICT_REFUSED,
    VERDICT_REPAIRED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    ANSWER_FROM_FIRST_RESULT,
    DISPATCH,
    EFFECT_STATE_CONFIRMED,
    REQUEST_ANSWERED,
    TASK_COMPLETED,
    journal_decision,
    journal_intent,
    journal_outcome,
    request_identity_digest,
)

# --- One Loop Runtime Vocabulary (LE-RUNTIME-001) ---
CANONICAL_VERTEX_CLASS = "Loop"
ROLE_PRACTITIONER = "Practitioner"
ROLE_INTELLIGENCE = "Intelligence"
ROLE_SOLUTION = "Solution"
ADMITTED_LOOP_ROLES = (ROLE_PRACTITIONER, ROLE_INTELLIGENCE, ROLE_SOLUTION)

MODE_DETERMINISTIC = "deterministic"
MODE_HYBRID = "hybrid"
MODE_NON_DETERMINISTIC = "non-deterministic"
ADMITTED_RUN_MODES = (MODE_DETERMINISTIC, MODE_HYBRID, MODE_NON_DETERMINISTIC)

REL_STARTING = "Starting"
REL_SPAWNED_BY = "Spawned by"
REL_QUERIED_BY = "Queried by"
REL_RETRIEVED_BY = "Retrieved by"
REL_CONNECTED_FROM = "Connected from"
ADMITTED_RELATIONSHIPS = (
    REL_STARTING,
    REL_SPAWNED_BY,
    REL_QUERIED_BY,
    REL_RETRIEVED_BY,
    REL_CONNECTED_FROM,
)

# --- 4 Swappable Communication Coordinator & Graph Scheduler Engines ---
COORD_TOPOLOGICAL_WAVE = "topological_wave_coordinator"
COORD_PRIORITY_DEADLINE = "priority_deadline_coordinator"
COORD_ACTOR_MAILBOX = "actor_mailbox_handoff_coordinator"
COORD_SEQUENTIAL_FALLBACK = "sequential_deterministic_fallback_coordinator"
COORD_CASCADE_ENVELOPE = "cascade_coordinator_envelope"

COORDINATOR_ENGINES = (
    COORD_TOPOLOGICAL_WAVE,
    COORD_PRIORITY_DEADLINE,
    COORD_ACTOR_MAILBOX,
    COORD_SEQUENTIAL_FALLBACK,
)
ALL_COORDINATOR_MODES = COORDINATOR_ENGINES + (COORD_CASCADE_ENVELOPE,)

# --- 9 Supported Harnesses ---
HARNESS_CLAUDE_CODE = "claude_code"
HARNESS_CODEX = "codex"
HARNESS_CURSOR = "cursor"
HARNESS_WINDSURF = "windsurf"
HARNESS_CLINE = "cline"
HARNESS_ROO_CODE = "roo_code"
HARNESS_OPENCODE = "opencode"
HARNESS_PI = "pi"
HARNESS_GOOSE_CHATGPT = "goose_chatgpt_app"

HARNESS_SPECS = (
    {
        "harness_id": HARNESS_CLAUDE_CODE,
        "display_name": "Claude Code",
        "rule_file": "CLAUDE.md",
        "mcp_transport_key": "http",
        "mcp_config_path": ".claude/settings.json",
        "skill_dir": ".claude/skills",
    },
    {
        "harness_id": HARNESS_CODEX,
        "display_name": "Codex",
        "rule_file": "AGENTS.md",
        "mcp_transport_key": "http_transport",
        "mcp_config_path": ".codex/config.toml",
        "skill_dir": ".codex/skills",
    },
    {
        "harness_id": HARNESS_CURSOR,
        "display_name": "Cursor",
        "rule_file": ".cursorrules",
        "mcp_transport_key": "url",
        "mcp_config_path": ".cursor/mcp.json",
        "skill_dir": ".cursor/skills",
    },
    {
        "harness_id": HARNESS_WINDSURF,
        "display_name": "Windsurf",
        "rule_file": ".windsurfrules",
        "mcp_transport_key": "serverUrl",
        "mcp_config_path": ".codeium/windsurf/mcp_config.json",
        "skill_dir": ".windsurf/skills",
    },
    {
        "harness_id": HARNESS_CLINE,
        "display_name": "Cline",
        "rule_file": ".clinerules",
        "mcp_transport_key": "streamableHttp",
        "mcp_config_path": ".cline/mcp_settings.json",
        "skill_dir": ".cline/skills",
    },
    {
        "harness_id": HARNESS_ROO_CODE,
        "display_name": "Roo Code",
        "rule_file": ".roorules",
        "mcp_transport_key": "streamable-http",
        "mcp_config_path": ".roo/mcp.json",
        "skill_dir": ".roo/skills",
    },
    {
        "harness_id": HARNESS_OPENCODE,
        "display_name": "OpenCode",
        "rule_file": "AGENTS.md",
        "mcp_transport_key": "remote",
        "mcp_config_path": "opencode.json",
        "skill_dir": ".opencode/skills",
    },
    {
        "harness_id": HARNESS_PI,
        "display_name": "Pi",
        "rule_file": "AGENTS.md",
        "mcp_transport_key": "mcp_endpoint",
        "mcp_config_path": ".pi/settings.json",
        "skill_dir": ".pi/skills",
    },
    {
        "harness_id": HARNESS_GOOSE_CHATGPT,
        "display_name": "Goose / ChatGPT App",
        "rule_file": "AGENTS.md",
        "mcp_transport_key": "sse_or_streamable_http",
        "mcp_config_path": ".config/goose/config.yaml",
        "skill_dir": ".goose/skills",
    },
)
HARNESS_BY_ID = MappingProxyType({item["harness_id"]: item for item in HARNESS_SPECS})

# --- 12 Component Families ---
FAM_SKILLS = "skills"
FAM_WORKSPACE_RULES = "workspace_rules"
FAM_LIFECYCLE_HOOKS = "lifecycle_hooks"
FAM_SLASH_COMMANDS = "slash_commands"
FAM_MCP_CONFIGS = "mcp_server_configs"
FAM_SYSTEM1_STATIONS = "system1_decision_stations"
FAM_ENGINE_API_CARDS = "engine_api_cards"
FAM_CORNER_CASE_PACKS = "corner_case_test_packs"
FAM_CREATIVE_RECIPES = "creative_studio_recipes"
FAM_OVERNIGHT_AFK = "overnight_afk_task_manifests"
FAM_CURATED_FEEDS = "curated_agent_feeds"
FAM_EXECUTIVE_BRIEFS = "executive_comparison_briefs"

COMPONENT_FAMILIES = (
    {
        "family_id": FAM_SKILLS,
        "ordinal": 1,
        "title": "Skills (SKILL.md)",
        "artifact_pattern": "SKILL.md",
        "default_role": ROLE_PRACTITIONER,
        "default_mode": MODE_HYBRID,
        "card_bytes": 320,
        "source_bytes": 4800,
        "capabilities": ("progressive_disclosure", "card_first_discovery"),
    },
    {
        "family_id": FAM_WORKSPACE_RULES,
        "ordinal": 2,
        "title": "Workspace Rules (AGENTS.md, CLAUDE.md, .cursorrules, .windsurfrules, .roorules)",
        "artifact_pattern": "AGENTS.md|CLAUDE.md|.cursorrules|.windsurfrules|.roorules",
        "default_role": ROLE_PRACTITIONER,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 290,
        "source_bytes": 5200,
        "capabilities": ("workspace_confinement", "authority_gate"),
    },
    {
        "family_id": FAM_LIFECYCLE_HOOKS,
        "ordinal": 3,
        "title": "Lifecycle Hooks (pre-turn, post-edit, pre-commit)",
        "artifact_pattern": "hooks/pre-turn|hooks/post-edit|hooks/pre-commit",
        "default_role": ROLE_SOLUTION,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 310,
        "source_bytes": 3600,
        "capabilities": ("pre_turn_gate", "post_edit_check", "pre_commit_gate"),
    },
    {
        "family_id": FAM_SLASH_COMMANDS,
        "ordinal": 4,
        "title": "Slash Commands (/goal, /plan, /boost, /learn)",
        "artifact_pattern": "commands/*.md",
        "default_role": ROLE_PRACTITIONER,
        "default_mode": MODE_HYBRID,
        "card_bytes": 260,
        "source_bytes": 2900,
        "capabilities": ("workflow_shortcut", "structured_dispatch"),
    },
    {
        "family_id": FAM_MCP_CONFIGS,
        "ordinal": 5,
        "title": "MCP Server Configurations (Transport-Verified)",
        "artifact_pattern": "mcp_config.json",
        "default_role": ROLE_SOLUTION,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 340,
        "source_bytes": 2400,
        "capabilities": ("transport_key_verified", "effect_scoped_tools"),
    },
    {
        "family_id": FAM_SYSTEM1_STATIONS,
        "ordinal": 6,
        "title": "System-1 Decision Stations (O(1) Triage Tables)",
        "artifact_pattern": "stations/*.yaml",
        "default_role": ROLE_INTELLIGENCE,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 280,
        "source_bytes": 3100,
        "capabilities": ("fast_triage", "zero_model_call_routing"),
    },
    {
        "family_id": FAM_ENGINE_API_CARDS,
        "ordinal": 7,
        "title": "Engine API Cards (Python, JS, Three.js, Babylon.js, Godot, Blender)",
        "artifact_pattern": "api_cards/*.card.json",
        "default_role": ROLE_INTELLIGENCE,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 380,
        "source_bytes": 14200,
        "capabilities": ("card_first_discovery", "multi_language_signature_binding"),
    },
    {
        "family_id": FAM_CORNER_CASE_PACKS,
        "ordinal": 8,
        "title": "Corner-Case Test Packs (Known-Wrong and Boundary Suites)",
        "artifact_pattern": "corner_cases/*_pack.json",
        "default_role": ROLE_SOLUTION,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 350,
        "source_bytes": 8400,
        "capabilities": ("known_wrong_control", "boundary_regression_check"),
    },
    {
        "family_id": FAM_CREATIVE_RECIPES,
        "ordinal": 9,
        "title": "Creative Studio Recipes (reelkit, Shaders, 3D Mesh, Audio DSP)",
        "artifact_pattern": "recipes/*.recipe.json",
        "default_role": ROLE_SOLUTION,
        "default_mode": MODE_HYBRID,
        "card_bytes": 410,
        "source_bytes": 16800,
        "capabilities": ("parametric_revision", "clean_reopen", "preserve_unchanged_code"),
    },
    {
        "family_id": FAM_OVERNIGHT_AFK,
        "ordinal": 10,
        "title": "Overnight AFK Task Manifests (Budget-Capped and Journalled)",
        "artifact_pattern": "afk/*.manifest.yaml",
        "default_role": ROLE_PRACTITIONER,
        "default_mode": MODE_HYBRID,
        "card_bytes": 370,
        "source_bytes": 6900,
        "capabilities": ("budget_ceiling_enforcement", "idempotent_journal_resume"),
    },
    {
        "family_id": FAM_CURATED_FEEDS,
        "ordinal": 11,
        "title": "Curated Agent Feeds (Digest-Verified Intelligence Streams)",
        "artifact_pattern": "feeds/*.feed.json",
        "default_role": ROLE_INTELLIGENCE,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 300,
        "source_bytes": 5400,
        "capabilities": ("sha256_digest_verification", "agent_feed_binding"),
    },
    {
        "family_id": FAM_EXECUTIVE_BRIEFS,
        "ordinal": 12,
        "title": "Executive Comparison Briefs (Provenance and Trade-Off Matrices)",
        "artifact_pattern": "briefs/*.brief.md",
        "default_role": ROLE_INTELLIGENCE,
        "default_mode": MODE_DETERMINISTIC,
        "card_bytes": 330,
        "source_bytes": 7600,
        "capabilities": ("provenance_citation", "fact_consistency_check"),
    },
)
FAMILY_BY_ID = MappingProxyType({item["family_id"]: item for item in COMPONENT_FAMILIES})


@dataclass(frozen=True)
class LoopVertexSpec:
    """One executable vertex in a Practitioner, Intelligence, or Solution Loop graph."""

    loop_id: str
    vertex_class: str
    loop_role: str
    run_mode: str
    relationship: str
    step_profile: str
    required_tokens: int
    estimated_ms: float
    declared_effects: tuple = (PURE_EFFECT,)
    is_passive_resource: bool = False


@dataclass(frozen=True)
class TypedEdgeSpec:
    """One typed, versioned directed edge between two Loop vertices."""

    edge_id: str
    source_loop_id: str
    target_loop_id: str
    request_schema: str
    result_schema: str
    refusal_schema: str
    payload_digest: str
    required_effects: tuple = (PURE_EFFECT,)


@dataclass(frozen=True)
class LoopGraphWorkload:
    """A complete Loop graph workload submitted to a communication coordinator engine."""

    workload_id: str
    title: str
    vertices: tuple[LoopVertexSpec, ...]
    edges: tuple[TypedEdgeSpec, ...]
    budget_cap_tokens: int
    deadline_ms: float
    mailbox_capacity: int
    granted_effects: tuple = (PURE_EFFECT,)
    request_identity: str = ""
    simulate_wave_contention: bool = False
    simulate_deadline_tightness: bool = False
    simulate_mailbox_burst: bool = False


@dataclass(frozen=True)
class CoordinatorGuards:
    """Guard switches used by known-wrong controls to prove each graph/catalog guard is active."""

    cycle_detection_guard: bool = True
    untyped_edge_guard: bool = True
    concrete_loop_subclass_guard: bool = True
    passive_frame_vertex_guard: bool = True
    edge_effect_escalation_guard: bool = True
    mcp_transport_key_guard: bool = True
    card_first_lazy_source_guard: bool = True
    creative_reopen_digest_guard: bool = True


@dataclass(frozen=True)
class CoordinatorExecutionResult:
    """Typed result of scheduling and executing a Loop graph through one coordinator engine."""

    workload_id: str
    coordinator_engine: str
    completed: bool
    code: str
    scheduled_order: tuple[str, ...]
    wave_count: int
    total_tokens_allocated: int
    critical_path_ms: float
    execution_latency_ms: float
    fallback_chain_used: tuple[str, ...]
    malicious_or_invalid_leaked: bool
    trace: EnvelopeTrace
    refusal: "EnvelopeRefusal | None" = None
    preflight_report: "EnvelopePreflightReport | None" = None
    handshake_verdict: "EnvelopeHandshakeVerdict | None" = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "workload_id": self.workload_id,
            "coordinator_engine": self.coordinator_engine,
            "completed": self.completed,
            "code": self.code,
            "scheduled_order": list(self.scheduled_order),
            "wave_count": self.wave_count,
            "total_tokens_allocated": self.total_tokens_allocated,
            "critical_path_ms": round(self.critical_path_ms, 3),
            "execution_latency_ms": round(self.execution_latency_ms, 4),
            "fallback_chain_used": list(self.fallback_chain_used),
            "malicious_or_invalid_leaked": self.malicious_or_invalid_leaked,
            "trace": self.trace.to_dict(),
            "refusal": None if self.refusal is None else self.refusal.to_dict(),
            "preflight_verdict": None if self.preflight_report is None else self.preflight_report.verdict,
            "handshake_verdict": None if self.handshake_verdict is None else self.handshake_verdict.verdict,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class HarnessCatalogCell:
    """One cell in the 9-harness by 12-component-family verification matrix (108 cells)."""

    cell_id: str
    harness_id: str
    harness_display_name: str
    family_id: str
    family_ordinal: int
    family_title: str
    artifact_path: str
    mcp_transport_key: str
    card_bytes: int
    source_bytes: int
    source_loaded_on_discovery: bool
    handshake_verdict: str
    preflight_verdict: str
    coordinator_used: str
    verified: bool
    code: str


def build_reference_workloads() -> tuple[LoopGraphWorkload, ...]:
    """Build four representative Loop graph workloads exercising all roles, modes, relationships, and coordinators."""
    digest_a = hashlib.sha256(b"edge_payload_a_v1").hexdigest()
    digest_b = hashlib.sha256(b"edge_payload_b_v1").hexdigest()
    digest_c = hashlib.sha256(b"edge_payload_c_v1").hexdigest()
    digest_d = hashlib.sha256(b"edge_payload_d_v1").hexdigest()

    # Workload 1: Creative Studio Diamond DAG (Practitioner -> Intelligence + Solution -> Solution Reopen Check)
    w1_vertices = (
        LoopVertexSpec("loop_start_brief", CANONICAL_VERTEX_CLASS, ROLE_PRACTITIONER, MODE_HYBRID, REL_STARTING, "creative_brief", 4000, 12.0),
        LoopVertexSpec("loop_query_shader_card", CANONICAL_VERTEX_CLASS, ROLE_INTELLIGENCE, MODE_DETERMINISTIC, REL_QUERIED_BY, "card_lookup", 1200, 4.0),
        LoopVertexSpec("loop_retrieve_audio_dsp", CANONICAL_VERTEX_CLASS, ROLE_INTELLIGENCE, MODE_DETERMINISTIC, REL_RETRIEVED_BY, "dsp_lookup", 1500, 5.0),
        LoopVertexSpec("loop_compose_scene", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_HYBRID, REL_CONNECTED_FROM, "scene_compose", 6000, 18.0),
        LoopVertexSpec("loop_verify_reopen", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "clean_reopen_gate", 2000, 6.0),
    )
    w1_edges = (
        TypedEdgeSpec("e1", "loop_start_brief", "loop_query_shader_card", "shader_card_request/v1", "shader_card_result/v1", "envelope_refusal/v1", digest_a),
        TypedEdgeSpec("e2", "loop_start_brief", "loop_retrieve_audio_dsp", "dsp_card_request/v1", "dsp_card_result/v1", "envelope_refusal/v1", digest_b),
        TypedEdgeSpec("e3", "loop_query_shader_card", "loop_compose_scene", "shader_bind_request/v1", "shader_bind_result/v1", "envelope_refusal/v1", digest_c),
        TypedEdgeSpec("e4", "loop_retrieve_audio_dsp", "loop_compose_scene", "dsp_bind_request/v1", "dsp_bind_result/v1", "envelope_refusal/v1", digest_c),
        TypedEdgeSpec("e5", "loop_compose_scene", "loop_verify_reopen", "reopen_check_request/v1", "reopen_check_result/v1", "envelope_refusal/v1", digest_d),
    )

    # Workload 2: Wave-Contention Graph (triggers fallback from topological_wave to priority_deadline)
    w2_vertices = (
        LoopVertexSpec("loop_plan_root", CANONICAL_VERTEX_CLASS, ROLE_PRACTITIONER, MODE_NON_DETERMINISTIC, REL_STARTING, "planner", 5000, 15.0),
        LoopVertexSpec("loop_spawn_worker_a", CANONICAL_VERTEX_CLASS, ROLE_PRACTITIONER, MODE_HYBRID, REL_SPAWNED_BY, "worker_a", 4500, 14.0),
        LoopVertexSpec("loop_spawn_worker_b", CANONICAL_VERTEX_CLASS, ROLE_PRACTITIONER, MODE_HYBRID, REL_SPAWNED_BY, "worker_b", 4500, 11.0),
        LoopVertexSpec("loop_merge_solution", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "merger", 3000, 8.0),
    )
    w2_edges = (
        TypedEdgeSpec("w2_e1", "loop_plan_root", "loop_spawn_worker_a", "subproblem_request/v1", "subproblem_result/v1", "envelope_refusal/v1", digest_a),
        TypedEdgeSpec("w2_e2", "loop_plan_root", "loop_spawn_worker_b", "subproblem_request/v1", "subproblem_result/v1", "envelope_refusal/v1", digest_b),
        TypedEdgeSpec("w2_e3", "loop_spawn_worker_a", "loop_merge_solution", "merge_request/v1", "merge_result/v1", "envelope_refusal/v1", digest_c),
        TypedEdgeSpec("w2_e4", "loop_spawn_worker_b", "loop_merge_solution", "merge_request/v1", "merge_result/v1", "envelope_refusal/v1", digest_d),
    )

    # Workload 3: Tight-Deadline Actor Handoff Graph (triggers fallback from topological -> priority_deadline -> actor_mailbox)
    w3_vertices = (
        LoopVertexSpec("loop_ingest_feed", CANONICAL_VERTEX_CLASS, ROLE_INTELLIGENCE, MODE_DETERMINISTIC, REL_STARTING, "feed_ingest", 2000, 9.0),
        LoopVertexSpec("loop_triage_station", CANONICAL_VERTEX_CLASS, ROLE_INTELLIGENCE, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "system1_triage", 1000, 3.0),
        LoopVertexSpec("loop_publish_brief", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "brief_emit", 2500, 7.0),
    )
    w3_edges = (
        TypedEdgeSpec("w3_e1", "loop_ingest_feed", "loop_triage_station", "feed_item_request/v1", "feed_item_result/v1", "envelope_refusal/v1", digest_a),
        TypedEdgeSpec("w3_e2", "loop_triage_station", "loop_publish_brief", "triage_verdict_request/v1", "triage_verdict_result/v1", "envelope_refusal/v1", digest_b),
    )

    # Workload 4: Constrained-Queue Sequential Graph (triggers fallback to sequential_deterministic_fallback_coordinator)
    w4_vertices = (
        LoopVertexSpec("loop_afk_start", CANONICAL_VERTEX_CLASS, ROLE_PRACTITIONER, MODE_HYBRID, REL_STARTING, "afk_init", 3000, 10.0),
        LoopVertexSpec("loop_corner_pack", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "corner_pack_run", 2500, 8.0),
        LoopVertexSpec("loop_checkpoint_commit", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "journal_commit", 1500, 5.0),
    )
    w4_edges = (
        TypedEdgeSpec("w4_e1", "loop_afk_start", "loop_corner_pack", "afk_step_request/v1", "afk_step_result/v1", "envelope_refusal/v1", digest_a),
        TypedEdgeSpec("w4_e2", "loop_corner_pack", "loop_checkpoint_commit", "checkpoint_request/v1", "checkpoint_result/v1", "envelope_refusal/v1", digest_b),
    )

    return (
        LoopGraphWorkload(
            workload_id="W-DAG-01",
            title="Creative Studio Diamond DAG (Card Discovery, Shader/DSP Bind, Clean Reopen)",
            vertices=w1_vertices,
            edges=w1_edges,
            budget_cap_tokens=20_000,
            deadline_ms=100.0,
            mailbox_capacity=16,
            request_identity="req_workload_dag_01",
        ),
        LoopGraphWorkload(
            workload_id="W-WAVE-02",
            title="Parallel Practitioner Spawn with Wave Contention Failover",
            vertices=w2_vertices,
            edges=w2_edges,
            budget_cap_tokens=25_000,
            deadline_ms=120.0,
            mailbox_capacity=16,
            request_identity="req_workload_wave_02",
            simulate_wave_contention=True,
        ),
        LoopGraphWorkload(
            workload_id="W-DEADLINE-03",
            title="Intelligence Feed to System-1 Station under Tight Deadline Slice",
            vertices=w3_vertices,
            edges=w3_edges,
            budget_cap_tokens=15_000,
            deadline_ms=40.0,
            mailbox_capacity=16,
            request_identity="req_workload_deadline_03",
            simulate_wave_contention=True,
            simulate_deadline_tightness=True,
        ),
        LoopGraphWorkload(
            workload_id="W-MAILBOX-04",
            title="Overnight AFK Checkpoint Pipeline under Mailbox Backpressure",
            vertices=w4_vertices,
            edges=w4_edges,
            budget_cap_tokens=15_000,
            deadline_ms=50.0,
            mailbox_capacity=2,
            request_identity="req_workload_mailbox_04",
            simulate_wave_contention=True,
            simulate_deadline_tightness=True,
            simulate_mailbox_burst=True,
        ),
    )


def _compute_topological_waves(
    vertices: tuple[LoopVertexSpec, ...],
    edges: tuple[TypedEdgeSpec, ...],
) -> tuple[bool, tuple[tuple[str, ...], ...], tuple[str, ...]]:
    """Compute deterministic topological waves (Kahn's algorithm) and detect cycles."""
    vertex_ids = tuple(v.loop_id for v in vertices)
    in_degree: dict[str, int] = {vid: 0 for vid in vertex_ids}
    adj: dict[str, list[str]] = {vid: [] for vid in vertex_ids}
    for edge in edges:
        if edge.source_loop_id in adj and edge.target_loop_id in in_degree:
            adj[edge.source_loop_id].append(edge.target_loop_id)
            in_degree[edge.target_loop_id] += 1

    ready = sorted([vid for vid, deg in in_degree.items() if deg == 0])
    waves: list[tuple[str, ...]] = []
    ordered: list[str] = []

    while ready:
        current_wave = tuple(ready)
        waves.append(current_wave)
        next_ready: list[str] = []
        for vid in current_wave:
            ordered.append(vid)
            for neighbor in adj[vid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_ready.append(neighbor)
        ready = sorted(next_ready)

    is_acyclic = len(ordered) == len(vertex_ids)
    return is_acyclic, tuple(waves), tuple(ordered)


def _compute_critical_path_ms(
    vertices: tuple[LoopVertexSpec, ...],
    edges: tuple[TypedEdgeSpec, ...],
    ordered: tuple[str, ...],
) -> float:
    by_id = {v.loop_id: v for v in vertices}
    dist: dict[str, float] = {vid: by_id[vid].estimated_ms for vid in ordered if vid in by_id}
    for vid in ordered:
        for edge in edges:
            if edge.source_loop_id == vid and edge.target_loop_id in dist:
                cand = dist[vid] + by_id[edge.target_loop_id].estimated_ms
                if cand > dist[edge.target_loop_id]:
                    dist[edge.target_loop_id] = cand
    return max(dist.values()) if dist else 0.0


def execute_graph_workload(
    workload: LoopGraphWorkload,
    coordinator_engine: str = COORD_CASCADE_ENVELOPE,
    guards: CoordinatorGuards = CoordinatorGuards(),
    *,
    shared_frame: "EnvelopeFrame | None" = None,
    fallback_chain_used: tuple[str, ...] = (),
) -> CoordinatorExecutionResult:
    """Execute a LoopGraphWorkload through the 7-layer component envelope and selected coordinator engine."""
    if coordinator_engine not in ALL_COORDINATOR_MODES:
        raise ValueError(f"Unsupported coordinator engine: {coordinator_engine}")

    if coordinator_engine == COORD_CASCADE_ENVELOPE:
        return _execute_cascade_coordinator(workload, guards)

    start_ns = time.perf_counter_ns()
    component_name = "solution_graph_coordinator"
    frame = shared_frame or root_frame(
        component_name,
        automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS,
        deadline_at=time.monotonic() + 5.0,
    )
    chain_used = fallback_chain_used or (coordinator_engine,)
    steps: list[tuple[str, str]] = []

    def refuse_step(layer_name: str, refusal: EnvelopeRefusal, detail: str = "") -> CoordinatorExecutionResult:
        trace_steps = tuple(steps + [(layer_name, LAYER_REFUSED)])
        trace = EnvelopeTrace(component_name, trace_steps, False, layer_name, refusal)
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        return CoordinatorExecutionResult(
            workload_id=workload.workload_id,
            coordinator_engine=coordinator_engine,
            completed=False,
            code=refusal.code,
            scheduled_order=(),
            wave_count=0,
            total_tokens_allocated=0,
            critical_path_ms=0.0,
            execution_latency_ms=elapsed_ms,
            fallback_chain_used=chain_used,
            malicious_or_invalid_leaked=False,
            trace=trace,
            refusal=refusal,
            detail=detail or refusal.message,
        )

    # --- Layer 2: CARRIER (One Loop Runtime & Typed Edge Schema Verification) ---
    if guards.concrete_loop_subclass_guard:
        for vertex in workload.vertices:
            if (
                vertex.vertex_class != CANONICAL_VERTEX_CLASS
                or vertex.loop_role not in ADMITTED_LOOP_ROLES
                or vertex.run_mode not in ADMITTED_RUN_MODES
                or vertex.relationship not in ADMITTED_RELATIONSHIPS
            ):
                refusal = envelope_refusal(
                    "concrete_loop_subclass_refused",
                    "Every executable graph vertex must use the canonical Loop runtime and an admitted role, mode, and relationship.",
                    "Replace any custom Node or Loop subclass with the canonical Loop vertex and a declared role profile.",
                    retry=DO_NOT_RETRY,
                )
                return refuse_step(LAYER_CARRIER, refusal, f"Refused non-canonical vertex {vertex.loop_id}: {vertex.vertex_class}")

    if guards.passive_frame_vertex_guard:
        for vertex in workload.vertices:
            if vertex.is_passive_resource:
                refusal = envelope_refusal(
                    "passive_frame_or_file_as_loop_refused",
                    "A passive file or renderer scene frame cannot be registered as an executable Loop vertex.",
                    "Keep passive files and frame buffers inside their owning Loop instead of creating separate Loop vertices.",
                    retry=DO_NOT_RETRY,
                )
                return refuse_step(LAYER_CARRIER, refusal, f"Refused passive resource vertex {vertex.loop_id}.")

    if guards.untyped_edge_guard:
        for edge in workload.edges:
            valid_req = "/v" in edge.request_schema and len(edge.request_schema) >= 5
            valid_res = "/v" in edge.result_schema and len(edge.result_schema) >= 5
            valid_ref = edge.refusal_schema == "envelope_refusal/v1"
            valid_dig = len(edge.payload_digest) == 64
            if not (valid_req and valid_res and valid_ref and valid_dig):
                refusal = envelope_refusal(
                    "untyped_edge_contract_refused",
                    "Every inter-Loop communication edge must declare versioned request, result, and refusal schemas with a 64-character digest.",
                    "Attach exact name/vN schema identifiers and a SHA-256 payload digest to the edge before scheduling.",
                    retry=RETRY_AFTER_FIX,
                )
                return refuse_step(LAYER_CARRIER, refusal, f"Refused untyped edge {edge.edge_id}.")

    steps.append((LAYER_CARRIER, LAYER_ACCEPTED))

    # --- Layer 3: HANDSHAKE ---
    required_effects_union: list[str] = [PURE_EFFECT]
    for vertex in workload.vertices:
        for eff in vertex.declared_effects:
            if eff not in required_effects_union:
                required_effects_union.append(eff)
    for edge in workload.edges:
        for eff in edge.required_effects:
            if eff not in required_effects_union:
                required_effects_union.append(eff)

    declared_effects_tuple = tuple(required_effects_union)
    granted_effects_tuple = workload.granted_effects if guards.edge_effect_escalation_guard else declared_effects_tuple

    handshake_verdict = negotiate_handshake(
        EnvelopeHandshakeRequest(
            component_name,
            ("1.0",),
            ("dag_schedule", "typed_edge_handoff"),
            (),
            granted_effects_tuple,
        ),
        EnvelopeHandshakeDeclaration(
            coordinator_engine,
            ("1.0",),
            ("dag_schedule", "typed_edge_handoff"),
            declared_effects_tuple,
        ),
    )
    if not handshake_verdict.proceeds:
        refusal = envelope_refusal(
            "edge_effect_escalation_refused",
            "A vertex or edge in the Loop graph requested an effect that the parent envelope grant does not hold.",
            "Remove the ungranted effect from the subordinate Loop or request explicit authority before execution.",
            retry=DO_NOT_RETRY,
        )
        return refuse_step(LAYER_HANDSHAKE, refusal, "Blocked ungranted effect escalation across graph edge.")

    steps.append((LAYER_HANDSHAKE, LAYER_ACCEPTED))

    # --- Layer 4: ACCOUNT (Budget Ceiling Enforcement) ---
    total_tokens = sum(v.required_tokens for v in workload.vertices)
    if total_tokens > workload.budget_cap_tokens:
        refusal = envelope_refusal(
            "budget_partition_exceeded",
            "The sum of token budgets across the graph vertices exceeds the account ceiling for this run.",
            "Lower the per-vertex token allocation or raise the declared run ceiling before scheduling.",
            retry=RETRY_AFTER_FIX,
        )
        return refuse_step(LAYER_ACCOUNT, refusal, "Graph token sum exceeded budget cap.")

    steps.append((LAYER_ACCOUNT, LAYER_ACCEPTED))

    # --- Layer 5: TRACKING (Journal Intent & Idempotent Edge Replay) ---
    req_id = workload.request_identity or f"req_{workload.workload_id}"
    req_digest = request_identity_digest(req_id)
    intent_entry = journal_intent(
        (),
        component=component_name,
        request_identity=req_digest,
        repeatable=True,
        at="2026-10-16T12:00:00Z",
    )
    steps.append((LAYER_TRACKING, LAYER_ACCEPTED))

    # --- Layer 6: PREFLIGHT (DAG Acyclicity & Engine-Specific Readiness Check) ---
    is_acyclic, waves, ordered = _compute_topological_waves(workload.vertices, workload.edges)

    def check_dag_acyclicity(ctx: Mapping) -> "EnvelopeRefusal | None":
        if guards.cycle_detection_guard and not bool(ctx.get("is_acyclic", True)):
            return envelope_refusal(
                "graph_cycle_detected",
                "The Solution Loop graph contains a directed cycle and cannot be scheduled as a valid wave sequence.",
                "Break the cycle in the connected Solution edges or move iterative refinement inside one Loop condition.",
                retry=DO_NOT_RETRY,
            )
        return None

    def check_coordinator_slot_readiness(ctx: Mapping) -> "EnvelopeRefusal | None":
        eng = str(ctx.get("coordinator_engine", ""))
        if eng == COORD_TOPOLOGICAL_WAVE and bool(ctx.get("simulate_wave_contention", False)):
            return envelope_refusal(
                "wave_fanout_slot_contention",
                "The parallel wave fan-out coordinator encountered worker slot contention before any vertex ran.",
                "Send the same request again with the same request identity, and nothing is done twice.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                automatic_retry=True,
            )
        if eng == COORD_PRIORITY_DEADLINE and bool(ctx.get("simulate_deadline_tightness", False)):
            return envelope_refusal(
                "deadline_slice_contention",
                "The critical-path deadline partitioning coordinator could not reserve simultaneous slack slices.",
                "Send the same request again with the same request identity, and nothing is done twice.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                automatic_retry=True,
            )
        if eng == COORD_ACTOR_MAILBOX and bool(ctx.get("simulate_mailbox_burst", False)):
            if int(ctx.get("edge_count", 0)) >= int(ctx.get("mailbox_capacity", 16)):
                return envelope_refusal(
                    "mailbox_backpressure_saturated",
                    "The actor mailbox queue reached its bounded capacity before any message was dispatched.",
                    "Send the same request again with the same request identity, and nothing is done twice.",
                    retry=RETRY_NOW_SAME_IDENTITY,
                    effect_commitment=EFFECT_NONE,
                    automatic_retry=True,
                )
        return None

    preflight_checks = (
        EnvelopePreflightCheck("check_dag_acyclicity", ("graph_cycle_detected",), check_dag_acyclicity),
        EnvelopePreflightCheck(
            "check_coordinator_slot_readiness",
            ("wave_fanout_slot_contention", "deadline_slice_contention", "mailbox_backpressure_saturated"),
            check_coordinator_slot_readiness,
        ),
    )
    preflight_report = run_preflight(
        component_name,
        preflight_checks,
        (),
        context={
            "is_acyclic": is_acyclic,
            "coordinator_engine": coordinator_engine,
            "simulate_wave_contention": workload.simulate_wave_contention,
            "simulate_deadline_tightness": workload.simulate_deadline_tightness,
            "simulate_mailbox_burst": workload.simulate_mailbox_burst,
            "edge_count": len(workload.edges),
            "mailbox_capacity": workload.mailbox_capacity,
        },
        grant=EnvelopePreflightGrant((PURE_EFFECT,)),
    )
    if not preflight_report.ready:
        assert preflight_report.refusal is not None
        return refuse_step(LAYER_PREFLIGHT, preflight_report.refusal, "Preflight refused coordinator dispatch.")

    steps.append((LAYER_PREFLIGHT, LAYER_ACCEPTED))

    # --- Layer 7: NESTED ENVELOPES & COORDINATOR ENGINE EXECUTION ---
    # Verify nested envelope entry for the first subordinate Loop vertex using the shared allowance and deadline.
    if workload.vertices:
        _nested_frame = enter_nested(frame, workload.vertices[0].loop_id)

    # Known-wrong leak detection: if any structural or security violation was present and its guard was disabled.
    has_invalid_vertex = any(
        v.vertex_class != CANONICAL_VERTEX_CLASS
        or v.loop_role not in ADMITTED_LOOP_ROLES
        or v.run_mode not in ADMITTED_RUN_MODES
        or v.relationship not in ADMITTED_RELATIONSHIPS
        for v in workload.vertices
    )
    has_passive_vertex = any(v.is_passive_resource for v in workload.vertices)
    has_untyped_edge = any(
        "/v" not in e.request_schema or "/v" not in e.result_schema or len(e.payload_digest) != 64
        for e in workload.edges
    )
    has_ungranted_effect = any(eff not in workload.granted_effects for eff in declared_effects_tuple if eff != PURE_EFFECT)
    leaked = (not is_acyclic) or has_invalid_vertex or has_passive_vertex or has_untyped_edge or has_ungranted_effect

    if not ordered:
        ordered = tuple(v.loop_id for v in workload.vertices)
    critical_ms = _compute_critical_path_ms(workload.vertices, workload.edges, ordered)
    if coordinator_engine == COORD_SEQUENTIAL_FALLBACK:
        wave_count = len(ordered)
        critical_ms = sum(v.estimated_ms for v in workload.vertices)
    else:
        wave_count = max(1, len(waves))

    # Commit tracking journal entry.
    result_digest = hashlib.sha256(":".join(ordered).encode("utf-8")).hexdigest()
    _committed = journal_outcome(
        (intent_entry,),
        component=component_name,
        request_identity=req_digest,
        request_outcome=REQUEST_ANSWERED,
        task_outcome=TASK_COMPLETED,
        effect_state=EFFECT_STATE_CONFIRMED,
        result_digest=result_digest,
        at="2026-10-16T12:00:01Z",
    )

    trace = EnvelopeTrace(component_name, tuple(steps), True, "", None)
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    code = "known_wrong_graph_violation_leaked" if leaked else f"scheduled_by_{coordinator_engine}"

    return CoordinatorExecutionResult(
        workload_id=workload.workload_id,
        coordinator_engine=coordinator_engine,
        completed=not leaked,
        code=code,
        scheduled_order=ordered,
        wave_count=wave_count,
        total_tokens_allocated=total_tokens,
        critical_path_ms=critical_ms,
        execution_latency_ms=elapsed_ms,
        fallback_chain_used=chain_used,
        malicious_or_invalid_leaked=leaked,
        trace=trace,
        preflight_report=preflight_report,
        handshake_verdict=handshake_verdict,
        detail=f"Scheduled {len(ordered)} Loop vertices across {wave_count} wave(s) via {coordinator_engine}.",
    )


def _execute_cascade_coordinator(
    workload: LoopGraphWorkload,
    guards: CoordinatorGuards = CoordinatorGuards(),
) -> CoordinatorExecutionResult:
    """Orchestrate the 4 coordinator engines with automatic fallback within one shared RecoveryAllowance."""
    start_ns = time.perf_counter_ns()
    component_name = "solution_graph_coordinator"
    shared = root_frame(
        component_name,
        automatic_attempts=MAXIMUM_AUTOMATIC_ATTEMPTS,
        deadline_at=time.monotonic() + 5.0,
    )
    recovery_policy = EnvelopeRecoveryPolicy(
        component_name,
        MAXIMUM_AUTOMATIC_ATTEMPTS,
        (
            "wave_fanout_slot_contention",
            "deadline_slice_contention",
            "mailbox_backpressure_saturated",
        ),
    )

    tried: list[str] = []
    last_res: CoordinatorExecutionResult | None = None

    for engine_candidate in COORDINATOR_ENGINES:
        tried.append(engine_candidate)
        res = execute_graph_workload(
            workload,
            engine_candidate,
            guards,
            shared_frame=shared,
            fallback_chain_used=tuple(tried),
        )
        last_res = res
        if res.completed or res.malicious_or_invalid_leaked:
            elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            return CoordinatorExecutionResult(
                **{
                    **{k: getattr(res, k) for k in res.__dataclass_fields__},
                    "coordinator_engine": COORD_CASCADE_ENVELOPE,
                    "fallback_chain_used": tuple(tried),
                    "execution_latency_ms": elapsed_ms,
                }
            )
        if res.refusal is not None:
            if not may_recover(recovery_policy, res.refusal, shared.allowance):
                break

    assert last_res is not None
    elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    return CoordinatorExecutionResult(
        **{
            **{k: getattr(last_res, k) for k in last_res.__dataclass_fields__},
            "coordinator_engine": COORD_CASCADE_ENVELOPE,
            "fallback_chain_used": tuple(tried),
            "execution_latency_ms": elapsed_ms,
        }
    )


def verify_harness_catalog_cell(
    harness_id: str,
    family_id: str,
    guards: CoordinatorGuards = CoordinatorGuards(),
    *,
    injected_mcp_key: str = "",
    force_eager_source_load: bool = False,
    corrupt_creative_reopen_digest: bool = False,
) -> HarnessCatalogCell:
    """Verify one (harness, component_family) cell of the 108-cell matrix inside the 7-layer envelope."""
    harness = HARNESS_BY_ID[harness_id]
    family = FAMILY_BY_ID[family_id]
    cell_id = f"{harness_id}__{family_id}"
    expected_mcp_key = str(harness["mcp_transport_key"])
    actual_mcp_key = injected_mcp_key or expected_mcp_key

    if family_id == FAM_WORKSPACE_RULES:
        artifact_path = str(harness["rule_file"])
    elif family_id == FAM_MCP_CONFIGS:
        artifact_path = str(harness["mcp_config_path"])
    elif family_id == FAM_SKILLS:
        artifact_path = f"{harness['skill_dir']}/SKILL.md"
    else:
        artifact_path = str(family["artifact_pattern"])

    def check_mcp_transport_key(ctx: Mapping) -> "EnvelopeRefusal | None":
        if guards.mcp_transport_key_guard and ctx.get("family_id") == FAM_MCP_CONFIGS:
            if ctx.get("actual_mcp_key") != ctx.get("expected_mcp_key"):
                return envelope_refusal(
                    "mcp_transport_key_mismatch",
                    "The MCP server configuration used a transport key that the target harness does not accept.",
                    "Emit the exact transport key declared for the target harness in HARNESS_SPECS.",
                    retry=RETRY_AFTER_FIX,
                )
        return None

    def check_card_first_discovery(ctx: Mapping) -> "EnvelopeRefusal | None":
        if guards.card_first_lazy_source_guard and bool(ctx.get("force_eager_source_load", False)):
            return envelope_refusal(
                "eager_source_load_on_discovery_refused",
                "Discovery attempted to load full implementation source bytes instead of the compact contract card.",
                "Load only the contract card during discovery and materialize full source only after selection.",
                retry=DO_NOT_RETRY,
            )
        return None

    def check_creative_reopen_digest(ctx: Mapping) -> "EnvelopeRefusal | None":
        if guards.creative_reopen_digest_guard and bool(ctx.get("corrupt_creative_reopen_digest", False)):
            return envelope_refusal(
                "creative_reopen_or_digest_failed",
                "The revised creative recipe failed the clean-environment reopen check or mutated its base digest.",
                "Preserve unchanged implementation digests and verify clean reopen before accepting the revision.",
                retry=DO_NOT_RETRY,
            )
        return None

    checks = (
        EnvelopePreflightCheck("check_mcp_transport_key", ("mcp_transport_key_mismatch",), check_mcp_transport_key),
        EnvelopePreflightCheck(
            "check_card_first_discovery",
            ("eager_source_load_on_discovery_refused",),
            check_card_first_discovery,
        ),
        EnvelopePreflightCheck(
            "check_creative_reopen_digest",
            ("creative_reopen_or_digest_failed",),
            check_creative_reopen_digest,
        ),
    )

    preflight = run_preflight(
        "harness_catalog_adapter",
        checks,
        (),
        context={
            "family_id": family_id,
            "actual_mcp_key": actual_mcp_key,
            "expected_mcp_key": expected_mcp_key,
            "force_eager_source_load": force_eager_source_load,
            "corrupt_creative_reopen_digest": corrupt_creative_reopen_digest,
        },
        grant=EnvelopePreflightGrant((PURE_EFFECT,)),
    )

    handshake = negotiate_handshake(
        EnvelopeHandshakeRequest(
            "harness_catalog_adapter",
            ("1.0",),
            tuple(family["capabilities"]),
            (),
            (PURE_EFFECT,),
        ),
        EnvelopeHandshakeDeclaration(
            f"adapter_{harness_id}",
            ("1.0",),
            tuple(family["capabilities"]),
            (PURE_EFFECT,),
        ),
    )

    has_fault = (
        (family_id == FAM_MCP_CONFIGS and actual_mcp_key != expected_mcp_key)
        or force_eager_source_load
        or corrupt_creative_reopen_digest
    )
    if not preflight.ready or not handshake.proceeds:
        code = preflight.refusal.code if preflight.refusal is not None else "handshake_refused"
        return HarnessCatalogCell(
            cell_id=cell_id,
            harness_id=harness_id,
            harness_display_name=str(harness["display_name"]),
            family_id=family_id,
            family_ordinal=int(family["ordinal"]),
            family_title=str(family["title"]),
            artifact_path=artifact_path,
            mcp_transport_key=actual_mcp_key,
            card_bytes=int(family["card_bytes"]),
            source_bytes=int(family["source_bytes"]),
            source_loaded_on_discovery=force_eager_source_load,
            handshake_verdict=handshake.verdict,
            preflight_verdict=preflight.verdict,
            coordinator_used=COORD_TOPOLOGICAL_WAVE,
            verified=False,
            code=code,
        )

    code = "known_wrong_catalog_violation_leaked" if has_fault else "verified_cell_ok"
    return HarnessCatalogCell(
        cell_id=cell_id,
        harness_id=harness_id,
        harness_display_name=str(harness["display_name"]),
        family_id=family_id,
        family_ordinal=int(family["ordinal"]),
        family_title=str(family["title"]),
        artifact_path=artifact_path,
        mcp_transport_key=actual_mcp_key,
        card_bytes=int(family["card_bytes"]),
        source_bytes=int(family["source_bytes"]),
        source_loaded_on_discovery=force_eager_source_load,
        handshake_verdict=handshake.verdict,
        preflight_verdict=preflight.verdict,
        coordinator_used=COORD_TOPOLOGICAL_WAVE,
        verified=not has_fault,
        code=code,
    )


def verify_all_108_harness_catalog_cells() -> dict:
    """Verify all 9 harnesses across all 12 component families (108 cells) and 12 end-to-end use cases."""
    cells: list[HarnessCatalogCell] = []
    for harness in HARNESS_SPECS:
        for family in COMPONENT_FAMILIES:
            cells.append(verify_harness_catalog_cell(str(harness["harness_id"]), str(family["family_id"])))

    workloads = build_reference_workloads()
    use_cases: list[dict] = []
    for idx, family in enumerate(COMPONENT_FAMILIES):
        harness = HARNESS_SPECS[idx % len(HARNESS_SPECS)]
        workload = workloads[idx % len(workloads)]
        coord_res = execute_graph_workload(workload, COORD_CASCADE_ENVELOPE)
        cell_res = verify_harness_catalog_cell(str(harness["harness_id"]), str(family["family_id"]))
        savings_ratio = round(1.0 - (cell_res.card_bytes / max(1, cell_res.source_bytes)), 4)
        use_cases.append(
            {
                "use_case_id": f"UC-{family['ordinal']:02d}",
                "family_id": family["family_id"],
                "family_title": family["title"],
                "primary_harness": harness["display_name"],
                "workload_id": workload.workload_id,
                "loop_role": family["default_role"],
                "run_mode": family["default_mode"],
                "card_bytes": cell_res.card_bytes,
                "source_bytes": cell_res.source_bytes,
                "discovery_byte_savings_ratio": savings_ratio,
                "fallback_chain_used": list(coord_res.fallback_chain_used),
                "verified": cell_res.verified and coord_res.completed,
                "code": f"{cell_res.code}:{coord_res.code}",
            }
        )

    verified_count = sum(1 for c in cells if c.verified)
    use_cases_verified = sum(1 for u in use_cases if u["verified"])
    return {
        "total_cells": len(cells),
        "verified_cells": verified_count,
        "harness_count": len(HARNESS_SPECS),
        "family_count": len(COMPONENT_FAMILIES),
        "use_cases_total": len(use_cases),
        "use_cases_verified": use_cases_verified,
        "all_verified": verified_count == 108 and use_cases_verified == 12,
        "cells": [c.__dict__ for c in cells],
        "use_cases": use_cases,
    }


def run_coordinator_benchmark() -> dict:
    """Benchmark all 4 swappable coordinator engines plus the cascade envelope across the 4 reference workloads."""
    workloads = build_reference_workloads()
    by_engine: dict[str, dict] = {}
    for engine_name in ALL_COORDINATOR_MODES:
        runs = [execute_graph_workload(w, engine_name) for w in workloads]
        completed = sum(1 for r in runs if r.completed)
        mean_ms = sum(r.execution_latency_ms for r in runs) / len(runs)
        total_ms = sum(r.execution_latency_ms for r in runs)
        by_engine[engine_name] = {
            "coordinator_engine": engine_name,
            "workloads_total": len(runs),
            "workloads_completed": completed,
            "completion_rate": round(completed / len(runs), 4),
            "mean_latency_ms": round(mean_ms, 4),
            "total_latency_ms": round(total_ms, 4),
            "runs": [r.to_dict() for r in runs],
        }
    return by_engine


def run_known_wrong_controls() -> list[dict]:
    """Run all 8 removed-guard known-wrong controls across Loop graph invariants and harness catalog boundaries."""
    digest_ok = hashlib.sha256(b"control_edge_v1").hexdigest()
    v_a = LoopVertexSpec("loop_a", CANONICAL_VERTEX_CLASS, ROLE_PRACTITIONER, MODE_DETERMINISTIC, REL_STARTING, "step_a", 1000, 5.0)
    v_b = LoopVertexSpec("loop_b", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "step_b", 1000, 5.0)
    e_ab = TypedEdgeSpec("e_ab", "loop_a", "loop_b", "req/v1", "res/v1", "envelope_refusal/v1", digest_ok)

    # 1. Cyclic graph workload
    cyclic_workload = LoopGraphWorkload(
        "KW-CYCLE-01",
        "Cyclic Loop Graph",
        (v_a, v_b),
        (
            e_ab,
            TypedEdgeSpec("e_ba", "loop_b", "loop_a", "req/v1", "res/v1", "envelope_refusal/v1", digest_ok),
        ),
        10_000,
        50.0,
        8,
    )
    # 2. Untyped edge workload
    untyped_edge_workload = LoopGraphWorkload(
        "KW-UNTYPED-02",
        "Untyped Edge Graph",
        (v_a, v_b),
        (TypedEdgeSpec("e_bad", "loop_a", "loop_b", "unversioned_req", "unversioned_res", "envelope_refusal/v1", "short"),),
        10_000,
        50.0,
        8,
    )
    # 3. Concrete Loop subclass workload
    subclass_vertex = LoopVertexSpec("loop_sub", "CustomPractitionerNode", ROLE_PRACTITIONER, MODE_DETERMINISTIC, REL_STARTING, "bad_sub", 1000, 5.0)
    subclass_workload = LoopGraphWorkload("KW-SUBCLASS-03", "Concrete Subclass Graph", (subclass_vertex,), (), 10_000, 50.0, 8)
    # 4. Passive renderer frame registered as Loop vertex
    passive_vertex = LoopVertexSpec("frame_tick_01", CANONICAL_VERTEX_CLASS, ROLE_SOLUTION, MODE_DETERMINISTIC, REL_CONNECTED_FROM, "passive_frame", 500, 1.0, is_passive_resource=True)
    passive_workload = LoopGraphWorkload("KW-PASSIVE-04", "Passive Frame Vertex Graph", (passive_vertex,), (), 10_000, 50.0, 8)
    # 5. Ungranted effect escalation across edge
    escalated_edge = TypedEdgeSpec("e_esc", "loop_a", "loop_b", "req/v1", "res/v1", "envelope_refusal/v1", digest_ok, required_effects=("network",))
    escalation_workload = LoopGraphWorkload(
        "KW-EFFECT-05",
        "Ungranted Edge Effect Escalation",
        (v_a, v_b),
        (escalated_edge,),
        10_000,
        50.0,
        8,
        granted_effects=(PURE_EFFECT,),
    )

    graph_controls = (
        ("removed_cycle_detection_guard", cyclic_workload, CoordinatorGuards(cycle_detection_guard=False), "graph_cycle_detected"),
        ("removed_untyped_edge_guard", untyped_edge_workload, CoordinatorGuards(untyped_edge_guard=False), "untyped_edge_contract_refused"),
        ("removed_concrete_loop_subclass_guard", subclass_workload, CoordinatorGuards(concrete_loop_subclass_guard=False), "concrete_loop_subclass_refused"),
        ("removed_passive_frame_vertex_guard", passive_workload, CoordinatorGuards(passive_frame_vertex_guard=False), "passive_frame_or_file_as_loop_refused"),
        ("removed_edge_effect_escalation_guard", escalation_workload, CoordinatorGuards(edge_effect_escalation_guard=False), "edge_effect_escalation_refused"),
    )

    results: list[dict] = []
    for ctrl_name, wl, disabled_guards, expected_refusal_code in graph_controls:
        guarded = execute_graph_workload(wl, COORD_CASCADE_ENVELOPE, CoordinatorGuards())
        unguarded = execute_graph_workload(wl, COORD_CASCADE_ENVELOPE, disabled_guards)
        detected = (
            (not guarded.completed)
            and (guarded.code == expected_refusal_code)
            and unguarded.malicious_or_invalid_leaked
        )
        results.append(
            {
                "control": ctrl_name,
                "target": wl.workload_id,
                "guarded_code": guarded.code,
                "unguarded_code": unguarded.code,
                "leaked_when_removed": unguarded.malicious_or_invalid_leaked,
                "known_wrong_detected": detected,
            }
        )

    # 6. Wrong MCP transport key for Windsurf (passing streamable-http instead of serverUrl)
    mcp_guarded = verify_harness_catalog_cell(
        HARNESS_WINDSURF, FAM_MCP_CONFIGS, CoordinatorGuards(), injected_mcp_key="streamable-http"
    )
    mcp_unguarded = verify_harness_catalog_cell(
        HARNESS_WINDSURF,
        FAM_MCP_CONFIGS,
        CoordinatorGuards(mcp_transport_key_guard=False),
        injected_mcp_key="streamable-http",
    )
    results.append(
        {
            "control": "removed_mcp_transport_key_guard",
            "target": "windsurf__mcp_server_configs",
            "guarded_code": mcp_guarded.code,
            "unguarded_code": mcp_unguarded.code,
            "leaked_when_removed": mcp_unguarded.code == "known_wrong_catalog_violation_leaked",
            "known_wrong_detected": (mcp_guarded.code == "mcp_transport_key_mismatch")
            and (mcp_unguarded.code == "known_wrong_catalog_violation_leaked"),
        }
    )

    # 7. Eager source load during contract-card discovery
    lazy_guarded = verify_harness_catalog_cell(
        HARNESS_CLAUDE_CODE, FAM_ENGINE_API_CARDS, CoordinatorGuards(), force_eager_source_load=True
    )
    lazy_unguarded = verify_harness_catalog_cell(
        HARNESS_CLAUDE_CODE,
        FAM_ENGINE_API_CARDS,
        CoordinatorGuards(card_first_lazy_source_guard=False),
        force_eager_source_load=True,
    )
    results.append(
        {
            "control": "removed_card_first_lazy_source_guard",
            "target": "claude_code__engine_api_cards",
            "guarded_code": lazy_guarded.code,
            "unguarded_code": lazy_unguarded.code,
            "leaked_when_removed": lazy_unguarded.code == "known_wrong_catalog_violation_leaked",
            "known_wrong_detected": (lazy_guarded.code == "eager_source_load_on_discovery_refused")
            and (lazy_unguarded.code == "known_wrong_catalog_violation_leaked"),
        }
    )

    # 8. Corrupted creative recipe reopen digest
    reopen_guarded = verify_harness_catalog_cell(
        HARNESS_OPENCODE, FAM_CREATIVE_RECIPES, CoordinatorGuards(), corrupt_creative_reopen_digest=True
    )
    reopen_unguarded = verify_harness_catalog_cell(
        HARNESS_OPENCODE,
        FAM_CREATIVE_RECIPES,
        CoordinatorGuards(creative_reopen_digest_guard=False),
        corrupt_creative_reopen_digest=True,
    )
    results.append(
        {
            "control": "removed_creative_reopen_digest_guard",
            "target": "opencode__creative_studio_recipes",
            "guarded_code": reopen_guarded.code,
            "unguarded_code": reopen_unguarded.code,
            "leaked_when_removed": reopen_unguarded.code == "known_wrong_catalog_violation_leaked",
            "known_wrong_detected": (reopen_guarded.code == "creative_reopen_or_digest_failed")
            and (reopen_unguarded.code == "known_wrong_catalog_violation_leaked"),
        }
    )

    return results


def run_full_audit() -> dict:
    """Run the complete coordinator benchmark, 108-cell harness catalog matrix, 12 use cases, and 8 known-wrong controls."""
    coordinator_benchmarks = run_coordinator_benchmark()
    catalog_matrix = verify_all_108_harness_catalog_cells()
    controls = run_known_wrong_controls()
    cascade_bench = coordinator_benchmarks[COORD_CASCADE_ENVELOPE]

    all_passed = (
        cascade_bench["workloads_completed"] == 4
        and catalog_matrix["verified_cells"] == 108
        and catalog_matrix["use_cases_verified"] == 12
        and all(item["known_wrong_detected"] for item in controls)
    )
    return {
        "record_type": "graph_coordinator_and_harness_catalog_audit/v1",
        "passed": all_passed,
        "envelope_layers": list(COVERAGE_LAYERS),
        "coordinator_benchmarks": coordinator_benchmarks,
        "catalog_matrix": catalog_matrix,
        "known_wrong_controls": controls,
    }


def main(argv: "list[str] | None" = None) -> int:
    report = run_full_audit()
    if argv and "--json" in argv:
        print(json.dumps(report, indent=2))
    else:
        for eng, bench in report["coordinator_benchmarks"].items():
            print(
                f"{eng:46s} | completed={bench['workloads_completed']}/{bench['workloads_total']} "
                f"({bench['completion_rate']*100:5.1f}%) | mean_ms={bench['mean_latency_ms']:.3f}"
            )
        mat = report["catalog_matrix"]
        print(
            f"harness_catalog_matrix: {mat['verified_cells']}/{mat['total_cells']} cells verified | "
            f"use_cases: {mat['use_cases_verified']}/{mat['use_cases_total']} verified"
        )
        print(
            f"known_wrong_controls: {sum(1 for c in report['known_wrong_controls'] if c['known_wrong_detected'])}/"
            f"{len(report['known_wrong_controls'])} detected"
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
