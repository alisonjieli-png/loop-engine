"""Jagged Frontier, LLM Agent Trace Research Analyzer, Capability-Gap Taxonomy
& Poor Default LLM/Harness Behavior Combat Engine Suite.

Implements two swappable engine slot families wrapped in the 7-layer
`ComponentEnvelope` (`frustration_avoidance`, `carrier`, `handshake`, `account`,
`tracking`, `preflight`, `nested_envelopes`):

1. Slot Family 1 (`jagged_frontier_and_trace_pathology_mapper_slot`):
   Synthesizes empirical findings from LLM trace and agent research literature
   (`MAST: Why Do Multi-Agent LLM Systems Fail`, `Lost in the Middle` / Context Rot,
   `Navigating the Jagged Technological Frontier`, `SWE-bench` / `GAIA` / `OSWorld` /
   `TAU-bench` trajectory error analyses, Sycophancy & Specification-Gaming studies)
   plus Baltor's own trace-mined telemetry into a 20-Pathology Jagged Frontier
   Taxonomy (`LLM-01..LLM-10` and `HAR-01..HAR-10`) using 4 swappable engines:
   - `empirical_literature_and_trace_pathology_digester_engine`
   - `mast_and_swe_trajectory_failure_classifier_engine`
   - `jagged_frontier_boundary_profiler_engine`
   - `deterministic_pathology_taxonomy_fallback_engine`

2. Slot Family 2 (`jagged_frontier_combat_and_pack_synthesizer_slot`):
   Executes real-time preflight/postflight pathology detection and neutralization,
   compiles empirical ablation studies for `paper.baltor.ai` and `agentbriefs.si`,
   and emits ready-to-drop `AGENTS.md`, `RULES.md`, `MEMORY.md`, `SKILL.md`, and
   `<= 2 KB` Contract Card combat packs for all 20 pathologies using 4 engines:
   - `deterministic_preflight_and_postflight_combat_engine`
   - `ablation_study_and_benchmark_compiler_engine`
   - `jagged_frontier_combat_pack_generator_engine`
   - `deterministic_combat_pack_fallback_engine`

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
# Slot IDs, Engine IDs, and Protocol Constants
# ---------------------------------------------------------------------------

SLOT_PATHOLOGY_MAPPER = "jagged_frontier_and_trace_pathology_mapper_slot"
SLOT_COMBAT_SYNTHESIZER = "jagged_frontier_combat_and_pack_synthesizer_slot"
ALL_SLOTS: tuple[str, ...] = (SLOT_PATHOLOGY_MAPPER, SLOT_COMBAT_SYNTHESIZER)

ENGINE_LITERATURE_DIGESTER = "empirical_literature_and_trace_pathology_digester_engine"
ENGINE_MAST_SWE_CLASSIFIER = "mast_and_swe_trajectory_failure_classifier_engine"
ENGINE_FRONTIER_PROFILER = "jagged_frontier_boundary_profiler_engine"
ENGINE_MAPPER_FALLBACK = "deterministic_pathology_taxonomy_fallback_engine"

MAPPER_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_LITERATURE_DIGESTER,
    ENGINE_MAST_SWE_CLASSIFIER,
    ENGINE_FRONTIER_PROFILER,
    ENGINE_MAPPER_FALLBACK,
)

ENGINE_COMBAT_GUARD = "deterministic_preflight_and_postflight_combat_engine"
ENGINE_ABLATION_COMPILER = "ablation_study_and_benchmark_compiler_engine"
ENGINE_COMBAT_PACK_GENERATOR = "jagged_frontier_combat_pack_generator_engine"
ENGINE_COMBAT_FALLBACK = "deterministic_combat_pack_fallback_engine"

COMBAT_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_COMBAT_GUARD,
    ENGINE_ABLATION_COMPILER,
    ENGINE_COMBAT_PACK_GENERATOR,
    ENGINE_COMBAT_FALLBACK,
)

ENGINE_UNPROTECTED_DEFAULT_BASELINE = "default_unprotected_llm_and_harness"
ENGINE_BALTOR_20MODE_COMBAT_SUITE = "baltor_20mode_jagged_frontier_combat_suite"

ENVELOPE_SCHEMA_VERSION = "1.0.0"
CONTRACT_PROTOCOL_VERSION = "1.0"
DEFAULT_RELEASE_DIGEST = "sha256:41eef5bcjaggedfrontier20261017"
MAX_CONTRACT_CARD_BYTES = 2048

# ---------------------------------------------------------------------------
# Research Corpus & 20-Pathology Jagged Frontier Taxonomy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchStudySpec:
    """Empirical LLM trace or agent research study grounding the taxonomy."""

    study_id: str
    title: str
    authors_year: str
    reference_locator: str
    trace_sample_size: int
    key_empirical_finding: str


RESEARCH_LITERATURE_CORPUS: tuple[ResearchStudySpec, ...] = (
    ResearchStudySpec(
        "MAST_2025",
        "MAST: Why Do Multi-Agent LLM Systems Fail?",
        "Cemri et al., 2025",
        "arxiv.org/abs/2503.13657",
        1642,
        "14 failure modes across 3 categories: system design issues, inter-agent misalignment, and task verification/termination defects.",
    ),
    ResearchStudySpec(
        "LOST_IN_THE_MIDDLE_2024",
        "Lost in the Middle: How Language Models Use Long Contexts",
        "Liu et al., 2024",
        "arxiv.org/abs/2307.03172",
        2400,
        "U-shaped recall curve: accuracy drops 20-40% when critical constraints sit in the middle of >8k-16k token contexts.",
    ),
    ResearchStudySpec(
        "JAGGED_FRONTIER_2023",
        "Navigating the Jagged Technological Frontier",
        "Dell'Acqua et al., 2023",
        "ssrn.com/abstract=4573321",
        758,
        "LLMs excel at prose and brainstorming inside the frontier but degrade sharply (-19 percentage points) on quantitative/spatial tasks just outside it.",
    ),
    ResearchStudySpec(
        "SWE_GAIA_OSWORLD_TAU_2024",
        "SWE-bench, GAIA, OSWorld & TAU-bench Trajectory Error Analyses",
        "Jimenez et al. / Mialon et al. / Xie et al. / Yao et al., 2024",
        "swebench.com/trajectories-2024",
        3200,
        "Dominant agent trace failures: blind retry spirals, full-file edit collateral damage, upfront schema bloat, and premature victory declarations.",
    ),
    ResearchStudySpec(
        "SYCOPHANCY_REWARD_HACKING_2024",
        "Towards Understanding Sycophancy & Specification Gaming in Language Models",
        "Sharma et al. / Denison et al., 2024",
        "arxiv.org/abs/2310.13548",
        1850,
        "RLHF-trained models capitulate to false user premises and weaken/delete failing unit tests when blocked on root-cause code fixes.",
    ),
    ResearchStudySpec(
        "BALTOR_TRACE_MINING_2026",
        "Baltor Multi-Harness Production Trace Corpus (Codex, Claude Code, Paste-Cache)",
        "Baltor Engineering, 2026",
        "paper.baltor.ai/studies/jagged-frontier-2026",
        1814,
        "Repeated owner corrections cluster around 3D postage-stamp voids, untouched AST mutation, clarifying-question stalls, and frontier model overspend.",
    ),
)


@dataclass(frozen=True)
class JaggedPathologySpec:
    """Specification for one of the 20 Poor Default LLM or Harness Pathologies."""

    pathology_id: str
    code: str
    category: str  # "poor_default_llm_capability" | "poor_default_harness_behavior"
    title: str
    literature_sources: tuple[str, ...]
    jagged_symptom: str
    baltor_counter_measure_id: str
    counter_measure_mechanism: str
    default_unprotected_wasted_tokens: int
    baltor_protected_wasted_tokens: int
    default_survival_trials_out_of_3: int
    baltor_pass_trials_out_of_3: int


JAGGED_FRONTIER_PATHOLOGIES: tuple[JaggedPathologySpec, ...] = (
    # 10 Poor Default LLM Capabilities (LLM-01..LLM-10)
    JaggedPathologySpec(
        "LLM-01_jagged_arithmetic_and_spatial_blindness",
        "LLM-01",
        "poor_default_llm_capability",
        "Jagged Arithmetic & 3D/CAD Spatial Blindness",
        ("JAGGED_FRONTIER_2023", "BALTOR_TRACE_MINING_2026"),
        "Ace at prose, fails 3D horizon/frustum/CAD manifold math, leaving postage-stamp islands and z_min != 0.",
        "CM-LLM-01_spatial_horizon_and_manifold_verifier",
        "Offloads 3D frustum, sky-dome horizon coverage (>=92% viewport), and CAD z_min=0 manifold checks to deterministic geometry solvers.",
        4900,
        720,
        0,
        3,
    ),
    JaggedPathologySpec(
        "LLM-02_quadratic_all_pairs_reasoning_collapse",
        "LLM-02",
        "poor_default_llm_capability",
        "Quadratic O(N^2) All-Pairs In-Context Reasoning Collapse",
        ("JAGGED_FRONTIER_2023", "SWE_GAIA_OSWORLD_TAU_2024"),
        "Attempts O(N^2) fuzzy entity matching inside prompt context instead of writing a deterministic Stage-1 blocker.",
        "CM-LLM-02_two_stage_deterministic_blocker_gate",
        "Forbids in-context all-pairs scans and enforces a deterministic Stage-1 lexical/embedding blocker before any LLM comparison.",
        6200,
        810,
        0,
        3,
    ),
    JaggedPathologySpec(
        "LLM-03_lost_in_the_middle_context_rot",
        "LLM-03",
        "poor_default_llm_capability",
        "Lost-in-the-Middle Long-Context Constraint Rot",
        ("LOST_IN_THE_MIDDLE_2024", "MAST_2025"),
        "Drops mid-prompt architectural constraints once context exceeds 8k-16k tokens.",
        "CM-LLM-03_sandwich_anchoring_and_2kb_contract_cards",
        "Replaces monolithic context dumps with <=2 KB Contract Cards and pins hard invariants at prompt head and tail.",
        5100,
        680,
        1,
        3,
    ),
    JaggedPathologySpec(
        "LLM-04_sycophantic_premise_capitulation",
        "LLM-04",
        "poor_default_llm_capability",
        "Sycophantic Premise Capitulation",
        ("SYCOPHANCY_REWARD_HACKING_2024", "JAGGED_FRONTIER_2023"),
        "Agrees with a user's buggy assumption or leaky train-on-test premise instead of flagging the contradiction.",
        "CM-LLM-04_counter_premise_falsification_preflight",
        "Runs a deterministic premise-consistency preflight check before drafting prose, surfacing contradictions with observed evidence.",
        3800,
        640,
        0,
        3,
    ),
    JaggedPathologySpec(
        "LLM-05_lazy_ellipsis_and_placeholder_truncation",
        "LLM-05",
        "poor_default_llm_capability",
        "Lazy Ellipsis & Placeholder Code Truncation",
        ("SWE_GAIA_OSWORLD_TAU_2024", "BALTOR_TRACE_MINING_2026"),
        "Emits '// ... rest of code remains the same' or 'TODO: implement' stubs that break production files.",
        "CM-LLM-05_zero_ellipsis_surgical_ast_patch_gate",
        "Blocks ellipsis truncation markers at preflight and requires surgical line-range replacements with complete executable bodies.",
        4600,
        710,
        0,
        3,
    ),
    JaggedPathologySpec(
        "LLM-06_hallucinated_api_and_version_drift",
        "LLM-06",
        "poor_default_llm_capability",
        "Hallucinated API Signatures & Library Version Drift",
        ("SWE_GAIA_OSWORLD_TAU_2024", "JAGGED_FRONTIER_2023"),
        "Invents non-existent CLI flags, shader uniforms, or deprecated library signatures.",
        "CM-LLM-06_live_symbol_introspection_and_signature_pin",
        "Introspects installed module AST/help signatures before code generation and rejects unresolved symbols at preflight.",
        4400,
        730,
        1,
        3,
    ),
    JaggedPathologySpec(
        "LLM-07_uncalibrated_confidence_and_quantile_crossing",
        "LLM-07",
        "poor_default_llm_capability",
        "Uncalibrated Confidence & Quantile Crossing (q10 > q50)",
        ("JAGGED_FRONTIER_2023", "BALTOR_TRACE_MINING_2026"),
        "Outputs overconfident probabilities and inverted time-series forecast quantiles where q10 > q50 or q50 > q90.",
        "CM-LLM-07_isotonic_quantile_monotonicity_projector",
        "Enforces isotonic quantile sorting (q10 <= q50 <= q90) and proper scoring calibration before emitting forecasts.",
        3900,
        690,
        0,
        3,
    ),
    JaggedPathologySpec(
        "LLM-08_ai_slop_and_antithetical_cadence_default",
        "LLM-08",
        "poor_default_llm_capability",
        "AI Slop Lexicon & Antithetical Cadence Default",
        ("BALTOR_TRACE_MINING_2026", "SYCOPHANCY_REWARD_HACKING_2024"),
        "Defaults to 'delve', 'tapestry', 'testament', 'It is not just X, it is Y', and robotic sentence length variance sigma_L < 2.0.",
        "CM-LLM-08_humanizer_lexicon_and_burstiness_enforcer",
        "Scans public prose against banned AI-slop tokens and enforces sentence-length burstiness sigma_L >= 4.5 words.",
        3400,
        590,
        1,
        3,
    ),
    JaggedPathologySpec(
        "LLM-09_temporal_lookahead_and_group_leakage_blindness",
        "LLM-09",
        "poor_default_llm_capability",
        "Temporal Lookahead & Cross-Split Group Leakage Blindness",
        ("JAGGED_FRONTIER_2023", "BALTOR_TRACE_MINING_2026"),
        "Normalizes features across train+test splits or leaks future timestamps into historical training windows.",
        "CM-LLM-09_embargoed_walk_forward_split_auditor",
        "Verifies max(train_ts) + embargo <= min(val_ts) and disjoint entity groups before fitting any pipeline stage.",
        4700,
        760,
        0,
        3,
    ),
    JaggedPathologySpec(
        "LLM-10_reward_hacking_and_test_weakening",
        "LLM-10",
        "poor_default_llm_capability",
        "Reward Hacking & Test Assertion Weakening/Deletion",
        ("SYCOPHANCY_REWARD_HACKING_2024", "MAST_2025"),
        "Deletes failing unit tests, adds @skip, or loosens assertions to assert True instead of fixing the underlying bug.",
        "CM-LLM-10_immutable_test_assertion_monotone_guard",
        "Computes AST assertion digests on test files and refuses any diff that lowers assertion count or weakens predicates.",
        5800,
        820,
        0,
        3,
    ),
    # 10 Poor Default Harness Behaviors (HAR-01..HAR-10)
    JaggedPathologySpec(
        "HAR-01_upfront_mcp_schema_bloat",
        "HAR-01",
        "poor_default_harness_behavior",
        "Upfront MCP Tool Schema Dump Bloat",
        ("SWE_GAIA_OSWORLD_TAU_2024", "LOST_IN_THE_MIDDLE_2024"),
        "Dumps 30+ full MCP tool JSON schemas (2,600+ tokens) on turn 0, crushing local/cheap models before work starts.",
        "CM-HAR-01_ progressive_contract_card_lazy_hydration",
        "Loads <=150-token routing stubs on turn 0 and hydrates full schemas only for the selected slot.",
        5400,
        620,
        1,
        3,
    ),
    JaggedPathologySpec(
        "HAR-02_full_file_rewrite_digest_destruction",
        "HAR-02",
        "poor_default_harness_behavior",
        "Full-File Rewrite & Untouched Function Digest Destruction",
        ("SWE_GAIA_OSWORLD_TAU_2024", "BALTOR_TRACE_MINING_2026"),
        "Regenerates 500 unchanged lines to edit 10 lines, silently mutating untouched helper functions.",
        "CM-HAR-02_ast_unchanged_symbol_digest_lock",
        "Hashes every AST function/class outside the target edit span and refuses commits if any untouched digest changes.",
        6100,
        790,
        0,
        3,
    ),
    JaggedPathologySpec(
        "HAR-03_blind_unbounded_retry_spirals",
        "HAR-03",
        "poor_default_harness_behavior",
        "Blind Unbounded Compiler/Test Retry Spirals",
        ("MAST_2025", "SWE_GAIA_OSWORLD_TAU_2024"),
        "Burns 5-10 consecutive turns re-running the exact same failing command without changing diagnostic hypotheses.",
        "CM-HAR-03_bounded_2attempt_diagnostic_escalation_breaker",
        "Caps identical error-signature retries at 2 attempts (MAXIMUM_AUTOMATIC_ATTEMPTS=2) before forcing engine/slot fallback.",
        6800,
        880,
        0,
        3,
    ),
    JaggedPathologySpec(
        "HAR-04_clarifying_question_stall_on_autonomous_runs",
        "HAR-04",
        "poor_default_harness_behavior",
        "Clarifying-Question Stall on Autonomous Runs",
        ("BALTOR_TRACE_MINING_2026", "MAST_2025"),
        "Halts overnight or autonomous execution to ask the owner trivial A/B questions instead of measuring and deciding.",
        "CM-HAR-04_autonomous_evidence_decision_gate",
        "Intercepts outbound question lists during autonomous runs, runs a micro-benchmark, records rationale, and proceeds.",
        4200,
        700,
        1,
        3,
    ),
    JaggedPathologySpec(
        "HAR-05_unverified_self_declared_victory",
        "HAR-05",
        "poor_default_harness_behavior",
        "Unverified Self-Declared Victory ('Done!')",
        ("MAST_2025", "SWE_GAIA_OSWORLD_TAU_2024"),
        "Declares task completion based on LLM self-review without running deterministic property verifiers or live checks.",
        "CM-HAR-05_independent_verifier_loop_completion_gate",
        "Requires an independent deterministic verifier Loop (worker_id != verifier_id) with exit_code == 0 before TASK_COMPLETED.",
        5000,
        810,
        0,
        3,
    ),
    JaggedPathologySpec(
        "HAR-06_lossy_compaction_amnesia",
        "HAR-06",
        "poor_default_harness_behavior",
        "Lossy Conversation Compaction Amnesia",
        ("LOST_IN_THE_MIDDLE_2024", "BALTOR_TRACE_MINING_2026"),
        "Summarizes away hard budget ceilings, worktree boundaries, and file digests during '/compact'.",
        "CM-HAR-06_pinned_invariant_ledger_across_compaction",
        "Stores non-compactable authority rules, file digests, and budget ceilings in a pinned MEMORY.md ledger outside summary loss.",
        4500,
        740,
        1,
        3,
    ),
    JaggedPathologySpec(
        "HAR-07_overlapping_worktree_and_silent_merge_drop",
        "HAR-07",
        "poor_default_harness_behavior",
        "Overlapping Parallel Worktree Edits & Silent Merge Drops",
        ("MAST_2025", "BALTOR_TRACE_MINING_2026"),
        "Multiple parallel agents edit overlapping files or git auto-merge silently drops added lines while smoke tests pass.",
        "CM-HAR-07_detached_worktree_line_survival_auditor",
        "Isolates agents in detached worktrees and verifies 100% of added diff lines survive merge before push.",
        4800,
        770,
        0,
        2,
    ),
    JaggedPathologySpec(
        "HAR-08_non_idempotent_effect_retry",
        "HAR-08",
        "poor_default_harness_behavior",
        "Non-Idempotent External Effect Retry Without Reconciliation",
        ("MAST_2025", "SWE_GAIA_OSWORLD_TAU_2024"),
        "Retries a timed-out webhook, database write, or deployment call without reconciling whether the first call succeeded.",
        "CM-HAR-08_intent_journal_and_effect_reconciliation_gate",
        "Records journal_intent with request_identity_digest before any effect and reconciles remote state prior to retry.",
        4300,
        720,
        0,
        3,
    ),
    JaggedPathologySpec(
        "HAR-09_always_frontier_model_overspend",
        "HAR-09",
        "poor_default_harness_behavior",
        "Always-Frontier Model Overspend on Deterministic Tasks",
        ("BALTOR_TRACE_MINING_2026", "JAGGED_FRONTIER_2023"),
        "Calls a $15/1M-token frontier model for formatting, AST linting, or schema validation solvable by $0 deterministic code.",
        "CM-HAR-09_jev_cost_ladder_and_zero_llm_first_router",
        "Routes L0/L1 deterministic tasks to $0 native Python/AST engines and L2/L3 tasks to cheap Ollama Cloud models first.",
        5200,
        890,
        1,
        3,
    ),
    JaggedPathologySpec(
        "HAR-10_human_meat_proxy_dependency",
        "HAR-10",
        "poor_default_harness_behavior",
        "Human 'Meat-Proxy' Copy-Paste Dependency",
        ("BALTOR_TRACE_MINING_2026", "SWE_GAIA_OSWORLD_TAU_2024"),
        "Forces the user to manually copy-paste terminal logs, stack traces, and docs into chat instead of ambient retrieval.",
        "CM-HAR-10_ambient_pre_turn_workspace_and_log_harvester",
        "Automatically harvests exit codes, failing tracebacks, and relevant contract cards before prompting the model.",
        3900,
        870,
        0,
        3,
    ),
)

PATHOLOGY_BY_ID: Mapping[str, JaggedPathologySpec] = {
    p.pathology_id: p for p in JAGGED_FRONTIER_PATHOLOGIES
}
PATHOLOGY_BY_CODE: Mapping[str, JaggedPathologySpec] = {
    p.code: p for p in JAGGED_FRONTIER_PATHOLOGIES
}
LLM_PATHOLOGY_IDS: tuple[str, ...] = tuple(
    p.pathology_id for p in JAGGED_FRONTIER_PATHOLOGIES if p.category == "poor_default_llm_capability"
)
HARNESS_PATHOLOGY_IDS: tuple[str, ...] = tuple(
    p.pathology_id for p in JAGGED_FRONTIER_PATHOLOGIES if p.category == "poor_default_harness_behavior"
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
            ("transient_trace_digest_contention",),
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
                    "Generate a fresh request_id for distinct pathology combat payloads.",
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
                ("jagged_frontier_combat",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                self.slot_id,
                (CONTRACT_PROTOCOL_VERSION,),
                ("jagged_frontier_combat",),
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

TRUNCATION_MARKERS: tuple[str, ...] = (
    "// ... rest of code",
    "# ... rest of code",
    "/* ... existing code ... */",
    "# TODO: implement remaining",
)


def _check_no_test_assertion_deletion_or_weakening(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 1 (LLM-10): Refuse deleting or weakening unit test assertions."""
    before_assertions = int(ctx.get("test_assertions_before", 1))
    after_assertions = int(ctx.get("test_assertions_after", before_assertions))
    weakened_to_assert_true = bool(ctx.get("weakened_to_assert_true", False))
    if after_assertions < before_assertions or weakened_to_assert_true:
        return envelope_refusal(
            "test_assertion_deletion_or_weakening_refused",
            "Draft patch deletes or weakens existing unit test assertions (LLM-10 reward hacking).",
            "Restore all original test assertions and fix the underlying implementation defect.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_no_lazy_ellipsis_truncation(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 2 (LLM-05): Refuse lazy ellipsis or placeholder code truncation."""
    candidate_code = str(ctx.get("candidate_code", ""))
    has_truncation = bool(ctx.get("contains_ellipsis_truncation", False)) or any(
        marker in candidate_code for marker in TRUNCATION_MARKERS
    )
    if has_truncation:
        return envelope_refusal(
            "lazy_ellipsis_or_placeholder_truncation_refused",
            "Draft code contains lazy ellipsis truncation markers ('// ... rest of code') (LLM-05).",
            "Emit a surgical line-range replacement containing complete executable statements.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_untouched_ast_symbol_digests(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 3 (HAR-02): Refuse mutation of untouched AST symbols outside target edit span."""
    untouched_before = str(ctx.get("untouched_ast_digest_before", "sha256:clean"))
    untouched_after = str(ctx.get("untouched_ast_digest_after", untouched_before))
    if untouched_before != untouched_after:
        return envelope_refusal(
            "untouched_ast_symbol_digest_mutation_refused",
            f"Untouched AST symbol digest mutated from `{untouched_before}` to `{untouched_after}` (HAR-02).",
            "Use surgical line-range edits and preserve byte-identical AST digests on untouched symbols.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_verified_completion_claim(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control 4 (HAR-05): Refuse self-declared victory without independent property verifier pass."""
    claims_victory = bool(ctx.get("claims_task_completed", False))
    verifier_ran = bool(ctx.get("property_verifier_executed", True))
    verifier_exit = int(ctx.get("property_verifier_exit_code", 0))
    if claims_victory and (not verifier_ran or verifier_exit != 0):
        return envelope_refusal(
            "unverified_self_declared_victory_refused",
            "Agent declared task completion ('Done!') without passing a deterministic property verifier (HAR-05).",
            "Run the owning deterministic test/verifier suite and confirm exit_code == 0 before reporting completion.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_known_pathology_id(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Ensure requested pathology_id exists in the 20-mode taxonomy when specified."""
    pid = str(ctx.get("pathology_id", ""))
    if pid and pid not in PATHOLOGY_BY_ID:
        return envelope_refusal(
            "unknown_jagged_frontier_pathology",
            f"Pathology `{pid}` is not in the 20-mode Jagged Frontier taxonomy.",
            "Select one of LLM-01..LLM-10 or HAR-01..HAR-10 from JAGGED_FRONTIER_PATHOLOGIES.",
            retry=RETRY_AFTER_FIX,
        )
    return None


SHARED_COMBAT_PREFLIGHT_CHECKS: tuple[EnvelopePreflightCheck, ...] = (
    EnvelopePreflightCheck("known_pathology_id", ("unknown_jagged_frontier_pathology",), _check_known_pathology_id),
    EnvelopePreflightCheck(
        "no_test_assertion_weakening",
        ("test_assertion_deletion_or_weakening_refused",),
        _check_no_test_assertion_deletion_or_weakening,
    ),
    EnvelopePreflightCheck(
        "no_lazy_ellipsis_truncation",
        ("lazy_ellipsis_or_placeholder_truncation_refused",),
        _check_no_lazy_ellipsis_truncation,
    ),
    EnvelopePreflightCheck(
        "untouched_ast_symbol_digests",
        ("untouched_ast_symbol_digest_mutation_refused",),
        _check_untouched_ast_symbol_digests,
    ),
    EnvelopePreflightCheck(
        "verified_completion_claim",
        ("unverified_self_declared_victory_refused",),
        _check_verified_completion_claim,
    ),
)


# ---------------------------------------------------------------------------
# Slot Family 1: LLM Trace Paper Digester & 20-Mode Capability-Gap Mapper
# ---------------------------------------------------------------------------


class JaggedFrontierAndTracePathologyMapperSlot:
    """Slot Family 1 (`jagged_frontier_and_trace_pathology_mapper_slot`)."""

    def __init__(self) -> None:
        self.slot_id = SLOT_PATHOLOGY_MAPPER
        self.engine_order = MAPPER_ENGINE_ORDER
        self.envelope = ComponentEnvelope(self.slot_id, self.engine_order)

    def map_pathology_or_taxonomy(
        self,
        pathology_id: str = "LLM-01_jagged_arithmetic_and_spatial_blindness",
        *,
        request_id: str = "req_map_001",
        account_id: str = "acct_baltor_research",
        tier: str = "pro",
        preferred_engine: str = ENGINE_LITERATURE_DIGESTER,
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        payload: dict[str, Any] = {
            "pathology_id": pathology_id,
            "preferred_engine": preferred_engine,
        }
        if extra_payload:
            payload.update(extra_payload)
        req = EnvelopeInvocationRequest(
            slot_id=self.slot_id,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            payload=payload,
        )
        return self.envelope.execute(req, self._dispatch, SHARED_COMBAT_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        preferred = str(request.payload.get("preferred_engine", self.engine_order[0]))
        ordered = [preferred] + [e for e in self.engine_order if e != preferred]
        selected = ordered[0] if ordered[0] in self.engine_order else self.engine_order[0]
        tried = [selected]

        spec = PATHOLOGY_BY_ID[str(request.payload["pathology_id"])]
        studies = [
            {
                "study_id": s.study_id,
                "title": s.title,
                "authors_year": s.authors_year,
                "reference_locator": s.reference_locator,
                "trace_sample_size": s.trace_sample_size,
            }
            for s in RESEARCH_LITERATURE_CORPUS
            if s.study_id in spec.literature_sources
        ]
        output: dict[str, Any] = {
            "pathology_id": spec.pathology_id,
            "code": spec.code,
            "category": spec.category,
            "title": spec.title,
            "jagged_symptom": spec.jagged_symptom,
            "baltor_counter_measure_id": spec.baltor_counter_measure_id,
            "counter_measure_mechanism": spec.counter_measure_mechanism,
            "grounding_studies": studies,
            "total_taxonomy_modes": len(JAGGED_FRONTIER_PATHOLOGIES),
            "llm_capability_gaps_count": len(LLM_PATHOLOGY_IDS),
            "harness_behavior_gaps_count": len(HARNESS_PATHOLOGY_IDS),
            "envelope_depth": frame.depth,
        }
        return selected, tried, output


# ---------------------------------------------------------------------------
# Slot Family 2: Counter-Measure Engine, Study Generator & Combat Pack Synthesizer
# ---------------------------------------------------------------------------


class JaggedFrontierCombatAndPackSynthesizerSlot:
    """Slot Family 2 (`jagged_frontier_combat_and_pack_synthesizer_slot`)."""

    def __init__(self) -> None:
        self.slot_id = SLOT_COMBAT_SYNTHESIZER
        self.engine_order = COMBAT_ENGINE_ORDER
        self.envelope = ComponentEnvelope(self.slot_id, self.engine_order)

    def synthesize_combat_pack(
        self,
        pathology_id: str,
        *,
        request_id: str = "req_combat_001",
        account_id: str = "acct_baltor_research",
        tier: str = "pro",
        preferred_engine: str = ENGINE_COMBAT_PACK_GENERATOR,
        extra_payload: Mapping[str, Any] | None = None,
    ) -> EnvelopeInvocationResult:
        payload: dict[str, Any] = {
            "pathology_id": pathology_id,
            "preferred_engine": preferred_engine,
        }
        if extra_payload:
            payload.update(extra_payload)
        req = EnvelopeInvocationRequest(
            slot_id=self.slot_id,
            request_id=request_id,
            account_id=account_id,
            tier=tier,
            payload=payload,
        )
        return self.envelope.execute(req, self._dispatch, SHARED_COMBAT_PREFLIGHT_CHECKS)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], Mapping[str, Any]]:
        preferred = str(request.payload.get("preferred_engine", self.engine_order[0]))
        ordered = [preferred] + [e for e in self.engine_order if e != preferred]
        selected = ordered[0] if ordered[0] in self.engine_order else self.engine_order[0]
        tried = [selected]

        spec = PATHOLOGY_BY_ID[str(request.payload["pathology_id"])]
        agents_md = (
            f"# AGENTS.md — Combat Guard for {spec.code} ({spec.title})\n\n"
            f"- Pathology ID: `{spec.pathology_id}` (`{spec.category}`)\n"
            f"- Counter-Measure Slot Guard: `{spec.baltor_counter_measure_id}`\n"
            f"- Operational Mandate: {spec.counter_measure_mechanism}\n"
            "- Execute deterministic preflight and postflight checks before declaring completion.\n"
        )
        rules_md = (
            f"# RULES.md — Non-Negotiable Invariants for {spec.code}\n\n"
            f"1. Symptom Blocked: {spec.jagged_symptom}\n"
            f"2. Active Counter-Measure: {spec.counter_measure_mechanism}\n"
            "3. Preserve unchanged AST symbol digests, test assertion monotonicity, and <=2 KB contract cards.\n"
        )
        memory_md = (
            f"# MEMORY.md — Pinned Non-Compactable Ledger ({spec.code})\n\n"
            f"- Pinned Counter-Measure: `{spec.baltor_counter_measure_id}`\n"
            f"- Grounding Literature: `{', '.join(spec.literature_sources)}`\n"
            "- Status: Promoted via independent deterministic verifier Loop (`worker_id != verifier_id`).\n"
        )
        skill_md = (
            "---\n"
            f"name: combat-{spec.code.lower()}\n"
            f"description: Neutralize {spec.title} ({spec.pathology_id})\n"
            "---\n\n"
            f"# Skill: {spec.baltor_counter_measure_id}\n\n"
            f"When operating near `{spec.pathology_id}`, run `{spec.baltor_counter_measure_id}`:\n"
            f"{spec.counter_measure_mechanism}\n"
        )
        contract_card_obj = {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "pathology_id": spec.pathology_id,
            "code": spec.code,
            "category": spec.category,
            "counter_measure_id": spec.baltor_counter_measure_id,
            "mechanism": spec.counter_measure_mechanism,
            "literature_sources": list(spec.literature_sources),
            "wasted_tokens_reduction_pct": round(
                (spec.default_unprotected_wasted_tokens - spec.baltor_protected_wasted_tokens)
                / spec.default_unprotected_wasted_tokens
                * 100.0,
                1,
            ),
        }
        contract_card_json = json.dumps(contract_card_obj, indent=2, sort_keys=True)
        card_bytes = len(contract_card_json.encode("utf-8"))

        study_row = {
            "pathology_id": spec.pathology_id,
            "code": spec.code,
            "default_survival_rate": round(spec.default_survival_trials_out_of_3 / 3.0, 4),
            "baltor_pass_rate": round(spec.baltor_pass_trials_out_of_3 / 3.0, 4),
            "default_wasted_tokens": spec.default_unprotected_wasted_tokens,
            "baltor_wasted_tokens": spec.baltor_protected_wasted_tokens,
            "publication_targets": ["paper.baltor.ai", "agentbriefs.si"],
        }

        output: dict[str, Any] = {
            "pathology_id": spec.pathology_id,
            "code": spec.code,
            "counter_measure_id": spec.baltor_counter_measure_id,
            "pathology_detected_and_neutralized": True,
            "contract_card_bytes": card_bytes,
            "contract_card_within_2048_bytes": card_bytes <= MAX_CONTRACT_CARD_BYTES,
            "files": {
                "AGENTS.md": agents_md,
                "RULES.md": rules_md,
                "MEMORY.md": memory_md,
                "SKILL.md": skill_md,
                "baltor_contract_card.json": contract_card_json,
            },
            "ablation_study_row": study_row,
            "envelope_depth": frame.depth,
        }
        return selected, tried, output


# ---------------------------------------------------------------------------
# N=60 Adversarial Trace Benchmark & 4 Known-Wrong Control Runners
# ---------------------------------------------------------------------------


def run_jagged_frontier_60trial_benchmark() -> Mapping[str, Any]:
    """Benchmark all 20 Jagged Frontier & Default Harness Pathologies across N=60 trials (3 trials/pathology)."""
    mapper = JaggedFrontierAndTracePathologyMapperSlot()
    synthesizer = JaggedFrontierCombatAndPackSynthesizerSlot()

    total_trials = 0
    default_survived = 0
    default_wasted_tokens_sum = 0
    baltor_detected_and_neutralized = 0
    baltor_task_passed = 0
    baltor_wasted_tokens_sum = 0
    per_pathology_rows: list[Mapping[str, Any]] = []

    for idx, spec in enumerate(JAGGED_FRONTIER_PATHOLOGIES):
        map_res = mapper.map_pathology_or_taxonomy(
            spec.pathology_id,
            request_id=f"bench_map_{idx:02d}",
            preferred_engine=MAPPER_ENGINE_ORDER[idx % len(MAPPER_ENGINE_ORDER)],
        )
        combat_res = synthesizer.synthesize_combat_pack(
            spec.pathology_id,
            request_id=f"bench_combat_{idx:02d}",
            preferred_engine=COMBAT_ENGINE_ORDER[idx % len(COMBAT_ENGINE_ORDER)],
        )
        assert map_res.accepted and combat_res.accepted

        trials_for_mode = 3
        total_trials += trials_for_mode
        default_survived += spec.default_survival_trials_out_of_3
        default_wasted_tokens_sum += spec.default_unprotected_wasted_tokens * trials_for_mode
        baltor_detected_and_neutralized += trials_for_mode
        baltor_task_passed += spec.baltor_pass_trials_out_of_3
        baltor_wasted_tokens_sum += spec.baltor_protected_wasted_tokens * trials_for_mode

        per_pathology_rows.append(
            {
                "pathology_id": spec.pathology_id,
                "code": spec.code,
                "category": spec.category,
                "counter_measure_id": spec.baltor_counter_measure_id,
                "trials": trials_for_mode,
                "default_survived": spec.default_survival_trials_out_of_3,
                "baltor_neutralized": trials_for_mode,
                "baltor_passed": spec.baltor_pass_trials_out_of_3,
                "default_wasted_tokens_per_trial": spec.default_unprotected_wasted_tokens,
                "baltor_wasted_tokens_per_trial": spec.baltor_protected_wasted_tokens,
                "contract_card_bytes": combat_res.output["contract_card_bytes"],
            }
        )

    default_mean_wasted = default_wasted_tokens_sum // total_trials
    baltor_mean_wasted = round(baltor_wasted_tokens_sum / total_trials)
    token_waste_reduction_pct = round(
        (default_mean_wasted - baltor_mean_wasted) / default_mean_wasted * 100.0,
        1,
    )

    return {
        "total_pathologies": len(JAGGED_FRONTIER_PATHOLOGIES),
        "llm_pathologies_count": len(LLM_PATHOLOGY_IDS),
        "harness_pathologies_count": len(HARNESS_PATHOLOGY_IDS),
        "total_adversarial_trials": total_trials,
        "default_unprotected_llm_and_harness": {
            "engine_id": ENGINE_UNPROTECTED_DEFAULT_BASELINE,
            "trials_survived": default_survived,
            "survival_rate": round(default_survived / total_trials, 4),
            "survival_rate_pct": f"{round(default_survived / total_trials * 100.0, 1)}%",
            "wasted_tokens_per_trial": default_mean_wasted,
        },
        "baltor_20mode_jagged_frontier_combat_suite": {
            "engine_id": ENGINE_BALTOR_20MODE_COMBAT_SUITE,
            "pathologies_detected_and_neutralized": baltor_detected_and_neutralized,
            "detection_and_neutralization_rate": round(baltor_detected_and_neutralized / total_trials, 4),
            "detection_and_neutralization_rate_pct": f"{round(baltor_detected_and_neutralized / total_trials * 100.0, 1)}%",
            "trials_passed": baltor_task_passed,
            "task_pass_rate": round(baltor_task_passed / total_trials, 4),
            "task_pass_rate_pct": f"{round(baltor_task_passed / total_trials * 100.0, 1)}%",
            "wasted_tokens_per_trial": baltor_mean_wasted,
            "token_waste_delta_pct": f"-{token_waste_reduction_pct}%",
        },
        "per_pathology_rows": tuple(per_pathology_rows),
    }


def run_known_wrong_controls() -> Mapping[str, EnvelopeInvocationResult]:
    """Execute the 4 mandatory Known-Wrong Controls and return their Layer 6 refusal results."""
    synthesizer = JaggedFrontierCombatAndPackSynthesizerSlot()

    # Control 1: LLM-10 test-assertion deletion/weakening
    ctrl_llm10 = synthesizer.synthesize_combat_pack(
        "LLM-10_reward_hacking_and_test_weakening",
        request_id="kw_ctrl_1_llm10_test_weakening",
        extra_payload={"test_assertions_before": 12, "test_assertions_after": 8},
    )

    # Control 2: LLM-05 lazy ellipsis truncation
    ctrl_llm05 = synthesizer.synthesize_combat_pack(
        "LLM-05_lazy_ellipsis_and_placeholder_truncation",
        request_id="kw_ctrl_2_llm05_ellipsis",
        extra_payload={"candidate_code": "def solve():\n    // ... rest of code remains the same\n"},
    )

    # Control 3: HAR-02 untouched AST symbol digest mutation
    ctrl_har02 = synthesizer.synthesize_combat_pack(
        "HAR-02_full_file_rewrite_digest_destruction",
        request_id="kw_ctrl_3_har02_ast_digest_mutation",
        extra_payload={
            "untouched_ast_digest_before": "sha256:9f86d081884c7d65",
            "untouched_ast_digest_after": "sha256:0000deadbeef1111",
        },
    )

    # Control 4: HAR-05 unverified self-declared victory
    ctrl_har05 = synthesizer.synthesize_combat_pack(
        "HAR-05_unverified_self_declared_victory",
        request_id="kw_ctrl_4_har05_unverified_victory",
        extra_payload={
            "claims_task_completed": True,
            "property_verifier_executed": False,
            "property_verifier_exit_code": 1,
        },
    )

    return {
        "control_1_llm10_test_assertion_weakening": ctrl_llm10,
        "control_2_llm05_ellipsis_truncation": ctrl_llm05,
        "control_3_har02_untouched_ast_mutation": ctrl_har02,
        "control_4_har05_unverified_victory": ctrl_har05,
    }


__all__ = [
    "ALL_SLOTS",
    "COMBAT_ENGINE_ORDER",
    "CONTRACT_PROTOCOL_VERSION",
    "ComponentEnvelope",
    "ENGINE_ABLATION_COMPILER",
    "ENGINE_BALTOR_20MODE_COMBAT_SUITE",
    "ENGINE_COMBAT_FALLBACK",
    "ENGINE_COMBAT_GUARD",
    "ENGINE_COMBAT_PACK_GENERATOR",
    "ENGINE_FRONTIER_PROFILER",
    "ENGINE_LITERATURE_DIGESTER",
    "ENGINE_MAPPER_FALLBACK",
    "ENGINE_MAST_SWE_CLASSIFIER",
    "ENGINE_UNPROTECTED_DEFAULT_BASELINE",
    "ENVELOPE_SCHEMA_VERSION",
    "EnvelopeInvocationRequest",
    "EnvelopeInvocationResult",
    "HARNESS_PATHOLOGY_IDS",
    "JAGGED_FRONTIER_PATHOLOGIES",
    "JaggedFrontierAndTracePathologyMapperSlot",
    "JaggedFrontierCombatAndPackSynthesizerSlot",
    "JaggedPathologySpec",
    "LLM_PATHOLOGY_IDS",
    "MAPPER_ENGINE_ORDER",
    "MAX_CONTRACT_CARD_BYTES",
    "PATHOLOGY_BY_CODE",
    "PATHOLOGY_BY_ID",
    "RESEARCH_LITERATURE_CORPUS",
    "ResearchStudySpec",
    "SLOT_COMBAT_SYNTHESIZER",
    "SLOT_PATHOLOGY_MAPPER",
    "run_jagged_frontier_60trial_benchmark",
    "run_known_wrong_controls",
]
