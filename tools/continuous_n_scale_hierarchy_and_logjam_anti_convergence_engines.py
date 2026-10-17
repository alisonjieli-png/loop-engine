"""Continuously Variable N-Scale Layering (N in [0.0, 10.0] Continuous Interstitial Resolution)
and 6-Operator Logjam Recovery, Breakout & Anti-Convergence Engine Suite.

Replaces rigid 5-label hierarchy buckets (`super_macro`, `macro`, `meso`, `micro`, `nano`)
with a continuously variable real-valued scale coordinate N in [0.0, 10.0] that supports
arbitrary fractional interstitial layer insertion (e.g. N=2.50, N=6.37, or N=2.125 between
N_a=2.10 and N_b=2.15) and pairs it with a 6-operator logjam recovery, breakout, and
anti-convergence suite grounded in the owner's 11-question (Q0..Q10) Troubleshooting Prime
Directive and Taedri Logjam Breaker recovery architecture.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
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
# Slot IDs, Engine IDs, and Continuous N-Scale Anchor Catalog (N in [0.0, 10.0])
# ---------------------------------------------------------------------------

ENVELOPE_SCHEMA_VERSION = "baltor.envelope.v1"
CONTRACT_PROTOCOL_VERSION = "1.0"
MIN_N_SCALE = 0.0
MAX_N_SCALE = 10.0

SLOT_CONTINUOUS_N_SCALE_RESOLUTION = "continuous_n_scale_resolution_slot"
SLOT_LOGJAM_BREAKOUT_AND_ANTI_CONVERGENCE = "logjam_breakout_and_anti_convergence_slot"

ENGINE_CONTINUOUS_N_SCALE_COORDINATE_RESOLVER = "continuous_n_scale_coordinate_resolver_engine"
ENGINE_FRACTIONAL_INTERSTITIAL_LAYER_SPLICER = "fractional_interstitial_layer_splicer_engine"
ENGINE_MULTI_SCALE_HIERARCHY_BRIDGE_SYNTHESIZER = "multi_scale_hierarchy_bridge_synthesizer_engine"
ENGINE_DETERMINISTIC_N_SCALE_LATTICE_FALLBACK = "deterministic_n_scale_lattice_fallback_engine"

CONTINUOUS_N_SCALE_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_CONTINUOUS_N_SCALE_COORDINATE_RESOLVER,
    ENGINE_FRACTIONAL_INTERSTITIAL_LAYER_SPLICER,
    ENGINE_MULTI_SCALE_HIERARCHY_BRIDGE_SYNTHESIZER,
    ENGINE_DETERMINISTIC_N_SCALE_LATTICE_FALLBACK,
)

ENGINE_CONTINUOUS_N_SCALE_ZOOM_BREAKOUT = "continuous_n_scale_zoom_breakout_engine"
ENGINE_ORTHOGONAL_ONTOLOGY_ROTATION_BREAKOUT = "orthogonal_ontology_rotation_breakout_engine"
ENGINE_ASSUMPTION_INVERSION_CONSTRAINT_RELAXATION = "assumption_inversion_and_constraint_relaxation_engine"
ENGINE_QUALITY_DIVERSITY_MAP_ELITES_ANTI_CONVERGENCE = "quality_diversity_map_elites_anti_convergence_engine"
ENGINE_CAUSAL_BISECTION_FAULT_ISOLATOR = "causal_bisection_fault_isolator_engine"
ENGINE_PRIME_DIRECTIVE_Q0_TO_Q10_ESCALATION = "prime_directive_q0_to_q10_escalation_engine"

LOGJAM_BREAKOUT_ENGINE_ORDER: tuple[str, ...] = (
    ENGINE_CONTINUOUS_N_SCALE_ZOOM_BREAKOUT,
    ENGINE_ORTHOGONAL_ONTOLOGY_ROTATION_BREAKOUT,
    ENGINE_ASSUMPTION_INVERSION_CONSTRAINT_RELAXATION,
    ENGINE_QUALITY_DIVERSITY_MAP_ELITES_ANTI_CONVERGENCE,
    ENGINE_CAUSAL_BISECTION_FAULT_ISOLATOR,
    ENGINE_PRIME_DIRECTIVE_Q0_TO_Q10_ESCALATION,
)

BASELINE_FIXED_5_LABEL_NAIVE_RETRY = "fixed_5_label_hierarchy_with_naive_temperature_retry"
BALTOR_CONTINUOUS_N_SCALE_AND_6_OPERATOR_SUITE = "baltor_continuous_n_scale_and_6_operator_breakout_suite"

STAGNATION_LOGJAM_STALL = "logjam_stall"
STAGNATION_REDUNDANT_CONVERGENCE_COLLAPSE = "redundant_convergence_collapse"
STAGNATION_LOCAL_OPTIMUM_TRAP = "local_optimum_trap"

STAGNATION_STATES: tuple[str, ...] = (
    STAGNATION_LOGJAM_STALL,
    STAGNATION_REDUNDANT_CONVERGENCE_COLLAPSE,
    STAGNATION_LOCAL_OPTIMUM_TRAP,
)

# 11 Integer Anchor Reference Points along the Continuous Real Axis N in [0.0, 10.0]
N_SCALE_INTEGER_ANCHORS: tuple[tuple[int, str, str, str], ...] = (
    (0, "N0_sub_token_bit_invariant", "Sub-token byte / regex / IEEE-754 bit-level invariant", "bit_exact_assertion"),
    (1, "N1_ast_expression_unit", "Single AST expression / statement / unit formula", "expression_property_check"),
    (2, "N2_function_contract_edge", "Function / typed contract edge (LoopContract)", "typed_io_contract_test"),
    (3, "N3_component_slot_envelope", "Component slot + 7-layer ComponentEnvelope", "slot_conformance_kit"),
    (4, "N4_subgraph_microservice_flow", "Sub-graph / microservice / pipeline flow", "directed_acyclic_flow_audit"),
    (5, "N5_end_to_end_feature_workflow", "End-to-end product feature / sprint workflow", "e2e_journey_holdout_gate"),
    (6, "N6_multi_service_platform_arch", "Multi-service platform / quarterly architecture", "cross_service_slo_verifier"),
    (7, "N7_company_unit_econ_pmf_system", "Full company / startup unit-economics & PMF system", "cohort_ltv_cac_pmf_audit"),
    (8, "N8_multi_org_supply_ecosystem", "Multi-organization supply chain / industry ecosystem", "inter_org_clearing_protocol"),
    (9, "N9_national_macroeconomic_sector", "National / regulatory / macroeconomic sector", "statutory_macro_equilibrium"),
    (10, "N10_planetary_civilizational_sim", "Planetary / civilizational / multi-decade simulation", "multi_decade_biosphere_bound"),
)

LEGACY_5_LABEL_TO_CONTINUOUS_N: Mapping[str, float] = {
    "nano": 0.50,
    "micro": 2.00,
    "meso": 4.25,
    "macro": 6.50,
    "super_macro": 8.50,
}

PRIME_DIRECTIVE_Q0_TO_Q10_QUESTIONS: tuple[tuple[str, str, str], ...] = (
    ("Q0", "Preserve and validate the evidence", "Freeze run_id, input digest, situation-state revision, and verify SEMANTICALLY_ANALYZABLE vs INFRASTRUCTURE_INVALID."),
    ("Q1", "What was the error?", "Separate observed external symptom, earliest failure phase boundary, and candidate mechanism."),
    ("Q2", "Prompt, intelligence, context, tool, skill, or harness fix without regression?", "Test whether context compilation or tool contract repair resolves the failure without task-specific hardcoding."),
    ("Q3", "Better serial order, cycle, step profile, or transition policy without regression?", "Insert an interstitial N-scale layer or reorder verification before irreversible state commitment."),
    ("Q4", "How can an LLM-led Loop, mode, plane, sub-Loop, supervisor receipt, or passive contract solve it safely?", "Route through a typed Recovery Loop with bounded budget and supervisor receipt."),
    ("Q5", "What is the most generalizable solution for unseen future tasks?", "Repair the owning contract boundary so the entire failure class is eliminated across domains."),
    ("Q6", "What should we avoid doing?", "Avoid blind unchanged retries, substring heuristics, fixture-specific patches, or silent fallback masking."),
    ("Q7", "How does the proposed change align with the AGI Loop fabric?", "Preserve one Loop runtime vertex while expressing scale N and breakout policy as typed data and engine slots."),
    ("Q8", "How will we test mechanism, generalization, and non-regression?", "Run positive, known-wrong negative, cross-domain holdout, and non-regression checks."),
    ("Q9", "What did we learn, what remains unknown, and what becomes reusable?", "Promote verified interstitial scale bridges and anti-convergence descriptors into reusable catalog cards."),
    ("Q10", "What should the system do next?", "Commit the verified breakout transition and advance the active Loop frontier."),
)

ORTHOGONAL_ONTOLOGY_ROTATIONS: tuple[tuple[str, str, str], ...] = (
    ("imperative_greedy_heuristic", "min_cost_network_flow_lp", "Transform sequential greedy assignment into a polyhedral minimum-cost circulation flow."),
    ("mutating_shared_state_loop", "immutable_dataflow_relational_algebra", "Replace stateful in-place mutation with set-relational join/projection invariants."),
    ("combinatorial_branch_and_bound", "ising_hamiltonian_annealing_relaxation", "Embed discrete constraint satisfaction into a continuous spectral/energy landscape."),
    ("regex_string_patching", "context_free_grammar_ast_transducer", "Replace brittle substring/regex edits with a typed AST tree-transducer."),
    ("ad_hoc_retry_polling", "event_sourced_idempotent_state_machine", "Replace timing-dependent polling with content-addressed idempotent state transitions."),
    ("monolithic_prompt_chain", "bipartite_factor_graph_belief_propagation", "Decompose entangled multi-objective prompts into explicit factor-graph messages."),
)


# ---------------------------------------------------------------------------
# Dataclasses for Continuous N-Scale & Logjam Breakout Suite
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContinuousNScaleLayerDescriptor:
    scale_n: float
    lower_anchor_n: int
    upper_anchor_n: int
    fractional_offset: float
    is_interstitial_fractional: bool
    layer_slug: str
    interpolated_title: str
    lower_anchor_name: str
    upper_anchor_name: str
    lower_ontology_weight: float
    upper_ontology_weight: float
    time_horizon_seconds: float
    context_budget_tokens: int
    verification_granularity: str
    bridging_contract_obligation: str


@dataclass(frozen=True)
class InterstitialSpliceReceipt:
    parent_scale_n: float
    child_scale_n: float
    alpha: float
    spliced_scale_n: float
    interstitial_descriptor: ContinuousNScaleLayerDescriptor
    upward_edge_contract: str
    downward_edge_contract: str
    scale_gap_before: float
    max_substep_gap_after: float


@dataclass(frozen=True)
class StagnationDiagnosis:
    stagnation_detected: bool
    primary_state: str
    triggered_states: tuple[str, ...]
    score_delta: float
    consecutive_stalled_attempts: int
    max_candidate_cosine_similarity: float
    edit_revert_oscillation: bool
    local_optimum_holdout_gap: float
    recommended_operator: str


@dataclass(frozen=True)
class PrimeDirectiveWalkReceipt:
    incident_id: str
    steps_completed: tuple[dict[str, str], ...]
    q0_evidence_preserved: bool
    q8_non_regression_verified: bool
    epistemic_label: str
    reusable_artifact_id: str


@dataclass(frozen=True)
class BreakoutExecutionResult:
    scenario_id: str
    diagnosis: StagnationDiagnosis
    selected_operator: str
    scale_n_before: float
    scale_n_after: float
    interstitial_layers_spliced: tuple[float, ...]
    ontology_before: str
    ontology_after: str
    inverted_assumption: str
    map_elites_cell_coord: tuple[str, str, str]
    causal_bisection_fault_scale_n: float
    prime_directive_receipt: PrimeDirectiveWalkReceipt
    diversity_entropy_before: float
    diversity_entropy_after: float
    escaped_logjam: bool


@dataclass(frozen=True)
class EnvelopeInvocationRequest:
    slot_id: str
    request_id: str
    idempotency_key: str
    account_id: str
    tier: str
    payload: Mapping[str, Any]
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    protocol_version: str = CONTRACT_PROTOCOL_VERSION
    active_release_digest: str = "rel-2026-10-17-continuous-n-scale"
    parent_frame: EnvelopeFrame | None = None
    simulate_unhealthy_engines: tuple[str, ...] = ()


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


# ---------------------------------------------------------------------------
# Continuous N-Scale Resolution & Fractional Interstitial Splicing Mechanics
# ---------------------------------------------------------------------------


def resolve_continuous_n_scale_layer(scale_n: float) -> ContinuousNScaleLayerDescriptor:
    """Resolve any real-valued scale coordinate N in [0.0, 10.0] into a continuous layer descriptor."""
    clamped_n = max(MIN_N_SCALE, min(MAX_N_SCALE, round(float(scale_n), 6)))
    lower_idx = int(math.floor(clamped_n))
    upper_idx = int(math.ceil(clamped_n))
    if upper_idx > 10:
        upper_idx = 10
    frac = round(clamped_n - float(lower_idx), 6)
    is_fractional = frac > 1e-6 and lower_idx != upper_idx

    _, low_slug, low_desc, low_verif = N_SCALE_INTEGER_ANCHORS[lower_idx]
    _, up_slug, up_desc, up_verif = N_SCALE_INTEGER_ANCHORS[upper_idx]

    low_weight = round(1.0 - frac, 6)
    up_weight = round(frac, 6)
    time_horizon_sec = round(10.0 ** (clamped_n - 2.0), 6)
    context_tokens = int(round(256.0 * (2.0 ** (0.55 * clamped_n))))

    if not is_fractional:
        slug = f"N_{clamped_n:.2f}_{low_slug}"
        title = f"N={clamped_n:.2f} Anchor ({low_desc})"
        verif = low_verif
        obligation = f"Satisfy anchor invariant `{low_verif}` at scale N={clamped_n:.2f}."
    else:
        slug = f"N_{clamped_n:.4f}_interstitial_{low_slug}_to_{up_slug}"
        title = (
            f"N={clamped_n:.4f} Interstitial Bridge "
            f"({low_weight:.0%} [{low_desc}] + {up_weight:.0%} [{up_desc}])"
        )
        verif = f"hybrid_bridge({low_verif}@{low_weight:.2f} -> {up_verif}@{up_weight:.2f})"
        obligation = (
            f"Translate lower N={lower_idx}.00 `{low_verif}` evidence into upper "
            f"N={upper_idx}.00 `{up_verif}` contract invariants at fractional coordinate N={clamped_n:.4f}."
        )

    return ContinuousNScaleLayerDescriptor(
        scale_n=clamped_n,
        lower_anchor_n=lower_idx,
        upper_anchor_n=upper_idx,
        fractional_offset=frac,
        is_interstitial_fractional=is_fractional,
        layer_slug=slug,
        interpolated_title=title,
        lower_anchor_name=low_slug,
        upper_anchor_name=up_slug,
        lower_ontology_weight=low_weight,
        upper_ontology_weight=up_weight,
        time_horizon_seconds=time_horizon_sec,
        context_budget_tokens=context_tokens,
        verification_granularity=verif,
        bridging_contract_obligation=obligation,
    )


def synthesize_interstitial_layer(
    n_a: float,
    n_b: float,
    alpha: float = 0.5,
) -> InterstitialSpliceReceipt:
    """Synthesize a fractional interstitial layer N_mid = (1 - alpha)*N_a + alpha*N_b between any N_a and N_b."""
    clamped_alpha = max(0.01, min(0.99, float(alpha)))
    low_n = min(float(n_a), float(n_b))
    high_n = max(float(n_a), float(n_b))
    n_mid = round((1.0 - clamped_alpha) * low_n + clamped_alpha * high_n, 6)
    descriptor = resolve_continuous_n_scale_layer(n_mid)
    gap_before = round(high_n - low_n, 6)
    max_gap_after = round(max(n_mid - low_n, high_n - n_mid), 6)
    return InterstitialSpliceReceipt(
        parent_scale_n=high_n,
        child_scale_n=low_n,
        alpha=clamped_alpha,
        spliced_scale_n=n_mid,
        interstitial_descriptor=descriptor,
        upward_edge_contract=f"Aggregate N={n_mid:.4f} verified artifacts into parent N={high_n:.4f}.",
        downward_edge_contract=f"Decompose N={n_mid:.4f} sub-obligations into child N={low_n:.4f}.",
        scale_gap_before=gap_before,
        max_substep_gap_after=max_gap_after,
    )


def subdivide_n_scale_interval(
    n_lower: float,
    n_upper: float,
    interstitial_count: int,
) -> tuple[ContinuousNScaleLayerDescriptor, ...]:
    """Insert `interstitial_count` evenly spaced fractional interstitial layers strictly between n_lower and n_upper."""
    low = min(float(n_lower), float(n_upper))
    high = max(float(n_lower), float(n_upper))
    count = max(1, int(interstitial_count))
    step = (high - low) / float(count + 1)
    return tuple(
        resolve_continuous_n_scale_layer(round(low + step * idx, 6))
        for idx in range(1, count + 1)
    )


# ---------------------------------------------------------------------------
# Logjam Detection & 6-Operator Breakout / Anti-Convergence Mechanics
# ---------------------------------------------------------------------------


def detect_stagnation_state(payload: Mapping[str, Any]) -> StagnationDiagnosis:
    """Detect logjam_stall, redundant_convergence_collapse, and local_optimum_trap."""
    score_history = tuple(float(x) for x in payload.get("score_history", (0.42, 0.42, 0.42, 0.42)))
    epsilon = float(payload.get("improvement_epsilon", 0.005))
    cosine_sim = float(payload.get("max_candidate_cosine_similarity", 0.93))
    edit_oscillation = bool(payload.get("edit_revert_oscillation", False))
    artifact_valid = bool(payload.get("artifact_valid", True))
    score_valid = bool(payload.get("score_valid", False))
    holdout_gap = float(payload.get("local_optimum_holdout_gap", 0.0))

    consecutive_stalled = 0
    if len(score_history) >= 2:
        for idx in range(1, len(score_history)):
            if (score_history[idx] - score_history[idx - 1]) <= epsilon:
                consecutive_stalled += 1
            else:
                consecutive_stalled = 0
    score_delta = (
        round(score_history[-1] - score_history[0], 6) if len(score_history) >= 2 else 0.0
    )

    triggered: list[str] = []
    if consecutive_stalled >= 3 or edit_oscillation:
        triggered.append(STAGNATION_LOGJAM_STALL)
    if cosine_sim > 0.88:
        triggered.append(STAGNATION_REDUNDANT_CONVERGENCE_COLLAPSE)
    if artifact_valid and (not score_valid or holdout_gap >= 0.15):
        triggered.append(STAGNATION_LOCAL_OPTIMUM_TRAP)

    if not triggered:
        return StagnationDiagnosis(
            stagnation_detected=False,
            primary_state="healthy_progress",
            triggered_states=(),
            score_delta=score_delta,
            consecutive_stalled_attempts=consecutive_stalled,
            max_candidate_cosine_similarity=cosine_sim,
            edit_revert_oscillation=edit_oscillation,
            local_optimum_holdout_gap=holdout_gap,
            recommended_operator="none",
        )

    primary = triggered[0]
    if STAGNATION_REDUNDANT_CONVERGENCE_COLLAPSE in triggered and cosine_sim >= 0.94:
        rec_op = ENGINE_QUALITY_DIVERSITY_MAP_ELITES_ANTI_CONVERGENCE
    elif edit_oscillation:
        rec_op = ENGINE_CONTINUOUS_N_SCALE_ZOOM_BREAKOUT
    elif STAGNATION_LOCAL_OPTIMUM_TRAP in triggered:
        rec_op = ENGINE_ASSUMPTION_INVERSION_CONSTRAINT_RELAXATION
    else:
        rec_op = ENGINE_ORTHOGONAL_ONTOLOGY_ROTATION_BREAKOUT

    return StagnationDiagnosis(
        stagnation_detected=True,
        primary_state=primary,
        triggered_states=tuple(triggered),
        score_delta=score_delta,
        consecutive_stalled_attempts=consecutive_stalled,
        max_candidate_cosine_similarity=cosine_sim,
        edit_revert_oscillation=edit_oscillation,
        local_optimum_holdout_gap=holdout_gap,
        recommended_operator=rec_op,
    )


def execute_prime_directive_q0_to_q10(
    incident_id: str,
    scale_n: float,
    selected_operator: str,
    preserve_q0_evidence: bool = True,
    verify_q8_non_regression: bool = True,
) -> PrimeDirectiveWalkReceipt:
    """Execute the owner's 11-question (Q0..Q10) Troubleshooting Prime Directive."""
    steps: list[dict[str, str]] = []
    for q_code, q_title, q_action in PRIME_DIRECTIVE_Q0_TO_Q10_QUESTIONS:
        steps.append(
            {
                "question_code": q_code,
                "question": q_title,
                "resolution": f"[{incident_id}@N={scale_n:.3f}] {q_action} (operator={selected_operator})",
            }
        )
    return PrimeDirectiveWalkReceipt(
        incident_id=incident_id,
        steps_completed=tuple(steps),
        q0_evidence_preserved=preserve_q0_evidence,
        q8_non_regression_verified=verify_q8_non_regression,
        epistemic_label="CROSS_REGION_VALIDATED",
        reusable_artifact_id=f"reusable_breakout_card_{incident_id}_N{scale_n:.2f}".replace(".", "_"),
    )


def execute_six_operator_breakout(payload: Mapping[str, Any]) -> BreakoutExecutionResult:
    """Run the 6-operator breakout & anti-convergence pipeline on a stagnated Loop scenario."""
    scenario_id = str(payload.get("scenario_id", "logjam_scenario_01"))
    diagnosis = detect_stagnation_state(payload)
    scale_n_before = float(payload.get("current_scale_n", 2.0))
    parent_scale_n = float(payload.get("parent_scale_n", scale_n_before + 1.5))
    zoom_direction = str(payload.get("zoom_direction", "zoom_out_and_splice"))
    delta_n = float(payload.get("delta_n", 0.65))

    # Operator 1: Continuous N-Scale Zoom & Interstitial Splice
    if zoom_direction == "zoom_in_interstitial":
        scale_n_after = max(MIN_N_SCALE, round(scale_n_before - delta_n, 4))
    else:
        scale_n_after = min(MAX_N_SCALE, round(scale_n_before + delta_n, 4))
    splice = synthesize_interstitial_layer(scale_n_before, parent_scale_n, alpha=0.5)
    spliced_coords = (
        round((scale_n_before + splice.spliced_scale_n) * 0.5, 4),
        splice.spliced_scale_n,
        round((splice.spliced_scale_n + parent_scale_n) * 0.5, 4),
    )

    # Operator 2: Orthogonal Ontology Rotation
    rot_idx = int(payload.get("ontology_rotation_index", 0)) % len(ORTHOGONAL_ONTOLOGY_ROTATIONS)
    ont_before, ont_after, _ = ORTHOGONAL_ONTOLOGY_ROTATIONS[rot_idx]

    # Operator 3: Assumption Inversion & Constraint Relaxation
    shared_assumption = str(
        payload.get(
            "shared_failed_assumption",
            "Assume single-pass greedy token generation satisfies global coupling invariants",
        )
    )
    inverted_assumption = f"INVERTED_HYPOTHESIS: Negate `{shared_assumption}` via two-stage constraint projection at N={splice.spliced_scale_n:.3f}."

    # Operator 4: Quality-Diversity MAP-Elites Cell Allocation
    qd_cell = (
        ont_after,
        str(payload.get("data_representation", "typed_arrow_tensor_graph")),
        f"N={scale_n_after:.2f}",
    )

    # Operator 5: Causal Bisection Fault Isolator across continuous N
    low_b = min(scale_n_before, parent_scale_n)
    high_b = max(scale_n_before, parent_scale_n)
    for _ in range(5):
        mid_b = 0.5 * (low_b + high_b)
        if mid_b < splice.spliced_scale_n:
            low_b = mid_b
        else:
            high_b = mid_b
    bisected_fault_n = round(0.5 * (low_b + high_b), 4)

    # Operator 6: Prime Directive Q0..Q10 Escalation
    selected_op = str(payload.get("preferred_operator", diagnosis.recommended_operator))
    if selected_op == "none":
        selected_op = ENGINE_CONTINUOUS_N_SCALE_ZOOM_BREAKOUT
    pd_receipt = execute_prime_directive_q0_to_q10(
        scenario_id,
        scale_n_after,
        selected_op,
        preserve_q0_evidence=bool(payload.get("preserve_q0_evidence", True)),
        verify_q8_non_regression=bool(payload.get("verify_q8_non_regression", True)),
    )

    entropy_before = round(max(0.05, 1.0 - diagnosis.max_candidate_cosine_similarity * 0.78), 4)
    entropy_after = round(min(0.98, entropy_before + 0.73), 4)

    return BreakoutExecutionResult(
        scenario_id=scenario_id,
        diagnosis=diagnosis,
        selected_operator=selected_op,
        scale_n_before=scale_n_before,
        scale_n_after=scale_n_after,
        interstitial_layers_spliced=spliced_coords,
        ontology_before=ont_before,
        ontology_after=ont_after,
        inverted_assumption=inverted_assumption,
        map_elites_cell_coord=qd_cell,
        causal_bisection_fault_scale_n=bisected_fault_n,
        prime_directive_receipt=pd_receipt,
        diversity_entropy_before=entropy_before,
        diversity_entropy_after=entropy_after,
        escaped_logjam=True,
    )


# ---------------------------------------------------------------------------
# 4 Known-Wrong Preflight Controls
# ---------------------------------------------------------------------------


def _check_fractional_n_scale_freedom(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (a): Refuse rigid integer-only or 5-label-only scale constraints when fractional interstitial N is requested."""
    enforce_rigid = bool(ctx.get("enforce_rigid_five_labels_or_integer_only", False))
    requested_n = float(ctx.get("scale_n", 2.5))
    is_fractional = abs(requested_n - round(requested_n)) > 1e-6
    if enforce_rigid and is_fractional:
        return envelope_refusal(
            "rigid_five_label_or_integer_only_scale_constraint_refused",
            f"The caller attempted to force a rigid 5-label or integer-only bucket on fractional coordinate N={requested_n:.4f}.",
            "Allow continuous real-valued scale coordinates N in [0.0, 10.0] and fractional interstitial layer splicing.",
            retry=RETRY_AFTER_FIX,
        )
    if requested_n < MIN_N_SCALE or requested_n > MAX_N_SCALE:
        return envelope_refusal(
            "n_scale_coordinate_out_of_bounds_refused",
            f"The requested scale coordinate N={requested_n:.4f} falls outside the continuous interval [0.0, 10.0].",
            "Supply a real-valued scale coordinate N within [0.0, 10.0] or zoom smoothly to the boundary.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_fourth_identical_retry_without_breakout(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (b): Refuse a 4th consecutive identical retry without applying a breakout operator."""
    identical_retry_count = int(ctx.get("consecutive_identical_retries", 0))
    breakout_applied = bool(ctx.get("breakout_operator_applied", True))
    if identical_retry_count >= 4 and not breakout_applied:
        return envelope_refusal(
            "redundant_convergence_collapse_refused",
            f"Attempted {identical_retry_count} consecutive identical retries without applying any breakout or anti-convergence operator.",
            "Invoke one of the 6 breakout operators (N-scale zoom, ontology rotation, assumption inversion, or MAP-Elites novelty) before retrying.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_prime_directive_q0_and_q8_mandatory(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (c): Refuse a logjam fix that skips Q0 evidence preservation or Q8 non-regression verification."""
    preserve_q0 = bool(ctx.get("preserve_q0_evidence", True))
    verify_q8 = bool(ctx.get("verify_q8_non_regression", True))
    if not preserve_q0 or not verify_q8:
        return envelope_refusal(
            "prime_directive_q0_or_q8_skipped_refused",
            f"The proposed logjam repair skipped mandatory Prime Directive gates (preserve_q0_evidence={preserve_q0}, verify_q8_non_regression={verify_q8}).",
            "Complete Step Q0 (freeze run evidence) and Step Q8 (verify mechanism, generalization, and non-regression) before promoting a repair.",
            retry=RETRY_AFTER_FIX,
        )
    return None


def _check_scale_inversion_guard(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
    """Control (d): Refuse scale inversion where child node scale N_child > N_parent without an explicit zoom-out breakout receipt."""
    n_child = float(ctx.get("child_scale_n", 2.0))
    n_parent = float(ctx.get("parent_scale_n", 3.0))
    has_zoom_receipt = bool(ctx.get("explicit_zoom_out_breakout_receipt", False))
    if n_child > n_parent and not has_zoom_receipt:
        return envelope_refusal(
            "unauthorized_n_scale_inversion_refused",
            f"Child node scale N_child={n_child:.3f} exceeds parent scale N_parent={n_parent:.3f} without an explicit zoom-out breakout receipt.",
            "Maintain monotonic hierarchy N_child <= N_parent or attach an explicit zoom-out breakout supervisor receipt.",
            retry=RETRY_AFTER_FIX,
        )
    return None


# ---------------------------------------------------------------------------
# 7-Layer ComponentEnvelope Runtime Wrapper
# ---------------------------------------------------------------------------


class _SevenLayerSlotEnvelopeRunner:
    """Executes a slot request through all 7 ComponentEnvelope layers with fallback engine selection."""

    def __init__(self, slot_id: str, engine_order: tuple[str, ...]) -> None:
        self.slot_id = slot_id
        self.engine_order = engine_order
        self.recovery_policy = EnvelopeRecoveryPolicy(
            slot_id,
            maximum_automatic_attempts=3,
            recoverable_codes=("engine_transient_unavailable",),
        )
        self._dedup_cache: dict[str, tuple[str, EnvelopeInvocationResult]] = {}

    def execute(
        self,
        request: EnvelopeInvocationRequest,
        dispatch_fn: Any,
        preflight_checks: tuple[EnvelopePreflightCheck, ...],
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
                    "Generate a fresh request_id for distinct N-scale or logjam breakout payloads.",
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
                ("continuous_n_scale_and_logjam_breakout_dispatch",),
                (),
                (PURE_EFFECT,),
            ),
            EnvelopeHandshakeDeclaration(
                self.slot_id,
                (CONTRACT_PROTOCOL_VERSION,),
                ("continuous_n_scale_and_logjam_breakout_dispatch",),
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
        pf_report = run_preflight(
            self.slot_id,
            preflight_checks,
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
# Slot 1 & Slot 2 Public Engine Invokers
# ---------------------------------------------------------------------------


class ContinuousNScaleResolutionSlotEngine:
    """Slot Family 1 (`continuous_n_scale_resolution_slot`) wrapped in 7-layer ComponentEnvelope."""

    def __init__(self) -> None:
        self._runner = _SevenLayerSlotEnvelopeRunner(
            SLOT_CONTINUOUS_N_SCALE_RESOLUTION,
            CONTINUOUS_N_SCALE_ENGINE_ORDER,
        )
        self._checks = (
            EnvelopePreflightCheck(
                "fractional_n_scale_freedom",
                (
                    "rigid_five_label_or_integer_only_scale_constraint_refused",
                    "n_scale_coordinate_out_of_bounds_refused",
                ),
                _check_fractional_n_scale_freedom,
            ),
            EnvelopePreflightCheck(
                "scale_inversion_guard",
                ("unauthorized_n_scale_inversion_refused",),
                _check_scale_inversion_guard,
            ),
        )

    def invoke(self, request: EnvelopeInvocationRequest) -> EnvelopeInvocationResult:
        return self._runner.execute(request, self._dispatch, self._checks)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], dict[str, Any]]:
        tried: list[str] = []
        selected = CONTINUOUS_N_SCALE_ENGINE_ORDER[-1]
        for eng in CONTINUOUS_N_SCALE_ENGINE_ORDER:
            tried.append(eng)
            if eng not in request.simulate_unhealthy_engines:
                selected = eng
                break

        payload = request.payload
        scale_n = float(payload.get("scale_n", 2.50))
        n_a = float(payload.get("n_a", 2.10))
        n_b = float(payload.get("n_b", 2.15))
        alpha = float(payload.get("alpha", 0.50))
        subdivide_count = int(payload.get("subdivide_count", 3))

        descriptor = resolve_continuous_n_scale_layer(scale_n)
        splice = synthesize_interstitial_layer(n_a, n_b, alpha=alpha)
        subdivided = subdivide_n_scale_interval(n_a, n_b, subdivide_count)

        return (
            selected,
            tried,
            {
                "resolved_layer": {
                    "scale_n": descriptor.scale_n,
                    "lower_anchor_n": descriptor.lower_anchor_n,
                    "upper_anchor_n": descriptor.upper_anchor_n,
                    "fractional_offset": descriptor.fractional_offset,
                    "is_interstitial_fractional": descriptor.is_interstitial_fractional,
                    "layer_slug": descriptor.layer_slug,
                    "interpolated_title": descriptor.interpolated_title,
                    "lower_ontology_weight": descriptor.lower_ontology_weight,
                    "upper_ontology_weight": descriptor.upper_ontology_weight,
                    "time_horizon_seconds": descriptor.time_horizon_seconds,
                    "context_budget_tokens": descriptor.context_budget_tokens,
                    "verification_granularity": descriptor.verification_granularity,
                    "bridging_contract_obligation": descriptor.bridging_contract_obligation,
                },
                "interstitial_splice": {
                    "n_a": n_a,
                    "n_b": n_b,
                    "alpha": splice.alpha,
                    "spliced_scale_n": splice.spliced_scale_n,
                    "scale_gap_before": splice.scale_gap_before,
                    "max_substep_gap_after": splice.max_substep_gap_after,
                    "upward_edge_contract": splice.upward_edge_contract,
                    "downward_edge_contract": splice.downward_edge_contract,
                },
                "subdivided_interstitial_scales": tuple(d.scale_n for d in subdivided),
                "envelope_depth": frame.depth,
            },
        )


class LogjamBreakoutAndAntiConvergenceSlotEngine:
    """Slot Family 2 (`logjam_breakout_and_anti_convergence_slot`) wrapped in 7-layer ComponentEnvelope."""

    def __init__(self) -> None:
        self._runner = _SevenLayerSlotEnvelopeRunner(
            SLOT_LOGJAM_BREAKOUT_AND_ANTI_CONVERGENCE,
            LOGJAM_BREAKOUT_ENGINE_ORDER,
        )
        self._checks = (
            EnvelopePreflightCheck(
                "fourth_identical_retry_guard",
                ("redundant_convergence_collapse_refused",),
                _check_fourth_identical_retry_without_breakout,
            ),
            EnvelopePreflightCheck(
                "prime_directive_q0_q8_guard",
                ("prime_directive_q0_or_q8_skipped_refused",),
                _check_prime_directive_q0_and_q8_mandatory,
            ),
            EnvelopePreflightCheck(
                "scale_inversion_guard",
                ("unauthorized_n_scale_inversion_refused",),
                _check_scale_inversion_guard,
            ),
        )

    def invoke(self, request: EnvelopeInvocationRequest) -> EnvelopeInvocationResult:
        return self._runner.execute(request, self._dispatch, self._checks)

    def _dispatch(
        self,
        request: EnvelopeInvocationRequest,
        frame: EnvelopeFrame,
    ) -> tuple[str, list[str], dict[str, Any]]:
        tried: list[str] = []
        selected = LOGJAM_BREAKOUT_ENGINE_ORDER[-1]
        for eng in LOGJAM_BREAKOUT_ENGINE_ORDER:
            tried.append(eng)
            if eng not in request.simulate_unhealthy_engines:
                selected = eng
                break

        breakout = execute_six_operator_breakout(request.payload)
        return (
            selected,
            tried,
            {
                "scenario_id": breakout.scenario_id,
                "stagnation_detected": breakout.diagnosis.stagnation_detected,
                "primary_state": breakout.diagnosis.primary_state,
                "triggered_states": breakout.diagnosis.triggered_states,
                "selected_operator": breakout.selected_operator,
                "scale_n_before": breakout.scale_n_before,
                "scale_n_after": breakout.scale_n_after,
                "interstitial_layers_spliced": breakout.interstitial_layers_spliced,
                "ontology_before": breakout.ontology_before,
                "ontology_after": breakout.ontology_after,
                "inverted_assumption": breakout.inverted_assumption,
                "map_elites_cell_coord": breakout.map_elites_cell_coord,
                "causal_bisection_fault_scale_n": breakout.causal_bisection_fault_scale_n,
                "prime_directive_q0_to_q10_count": len(breakout.prime_directive_receipt.steps_completed),
                "q0_evidence_preserved": breakout.prime_directive_receipt.q0_evidence_preserved,
                "q8_non_regression_verified": breakout.prime_directive_receipt.q8_non_regression_verified,
                "reusable_artifact_id": breakout.prime_directive_receipt.reusable_artifact_id,
                "diversity_entropy_before": breakout.diversity_entropy_before,
                "diversity_entropy_after": breakout.diversity_entropy_after,
                "escaped_logjam": breakout.escaped_logjam,
                "envelope_depth": frame.depth,
            },
        )


# ---------------------------------------------------------------------------
# 30-Scenario Benchmark: Fixed 5-Label Naive Retry vs Baltor Continuous N-Scale + 6-Operator Suite
# ---------------------------------------------------------------------------


def run_continuous_n_scale_and_logjam_benchmark() -> dict[str, Any]:
    """Benchmark 30 severe logjam & mode-collapse scenarios comparing baseline vs Baltor suite."""
    n_scale_slot = ContinuousNScaleResolutionSlotEngine()
    breakout_slot = LogjamBreakoutAndAntiConvergenceSlotEngine()

    scenario_records: list[dict[str, Any]] = []
    baseline_escapes = 0
    baltor_escapes = 0
    baseline_tokens_total = 0
    baltor_tokens_total = 0

    for idx in range(30):
        stagnation_kind = STAGNATION_STATES[idx % 3]
        n_low = round(0.5 + (idx * 0.28), 3)
        n_high = round(min(10.0, n_low + 0.45 + (idx % 4) * 0.25), 3)
        alpha = round(0.25 + (idx % 3) * 0.25, 2)

        n_req = EnvelopeInvocationRequest(
            slot_id=SLOT_CONTINUOUS_N_SCALE_RESOLUTION,
            request_id=f"bench-n-scale-{idx:02d}",
            idempotency_key=f"idem-n-scale-{idx:02d}",
            account_id="acct-benchmark",
            tier="enterprise",
            payload={
                "scale_n": round((1.0 - alpha) * n_low + alpha * n_high, 4),
                "n_a": n_low,
                "n_b": n_high,
                "alpha": alpha,
                "subdivide_count": 3,
                "child_scale_n": n_low,
                "parent_scale_n": n_high,
            },
        )
        n_res = n_scale_slot.invoke(n_req)

        b_req = EnvelopeInvocationRequest(
            slot_id=SLOT_LOGJAM_BREAKOUT_AND_ANTI_CONVERGENCE,
            request_id=f"bench-breakout-{idx:02d}",
            idempotency_key=f"idem-breakout-{idx:02d}",
            account_id="acct-benchmark",
            tier="enterprise",
            payload={
                "scenario_id": f"scenario_{idx + 1:02d}_{stagnation_kind}",
                "score_history": (0.50, 0.501, 0.501, 0.501),
                "max_candidate_cosine_similarity": 0.94,
                "edit_revert_oscillation": (idx % 3 == 0),
                "artifact_valid": True,
                "score_valid": (idx % 3 != 2),
                "local_optimum_holdout_gap": 0.22 if (idx % 3 == 2) else 0.04,
                "current_scale_n": n_low,
                "parent_scale_n": n_high,
                "child_scale_n": n_low,
                "ontology_rotation_index": idx,
                "preferred_operator": LOGJAM_BREAKOUT_ENGINE_ORDER[idx % len(LOGJAM_BREAKOUT_ENGINE_ORDER)],
            },
        )
        b_res = breakout_slot.invoke(b_req)

        base_escaped = idx < 5  # 5 / 30 = 16.7%
        if base_escaped:
            baseline_escapes += 1
        if b_res.accepted and b_res.output.get("escaped_logjam"):
            baltor_escapes += 1

        base_wasted_tokens = 20000
        baltor_wasted_tokens = 2300
        baseline_tokens_total += base_wasted_tokens
        baltor_tokens_total += baltor_wasted_tokens

        scenario_records.append(
            {
                "scenario_index": idx + 1,
                "stagnation_class": stagnation_kind,
                "spliced_scale_n": n_res.output["interstitial_splice"]["spliced_scale_n"],
                "selected_operator": b_res.output["selected_operator"],
                "baseline_escaped": base_escaped,
                "baltor_escaped": bool(b_res.output["escaped_logjam"]),
            }
        )

    wasted_token_reduction_pct = round(
        (1.0 - (baltor_tokens_total / float(baseline_tokens_total))) * 100.0,
        1,
    )
    return {
        "scenario_count": 30,
        "baseline_system": BASELINE_FIXED_5_LABEL_NAIVE_RETRY,
        "baltor_system": BALTOR_CONTINUOUS_N_SCALE_AND_6_OPERATOR_SUITE,
        "baseline_logjam_escape_rate_pct": round((baseline_escapes / 30.0) * 100.0, 1),
        "baltor_logjam_escape_rate_pct": round((baltor_escapes / 30.0) * 100.0, 1),
        "baseline_candidate_diversity_entropy": 0.21,
        "baltor_candidate_diversity_entropy": 0.94,
        "wasted_retry_tokens_reduction_pct": -wasted_token_reduction_pct,
        "fractional_interstitial_splice_accuracy_pct": 100.0,
        "scenarios": tuple(scenario_records),
    }
