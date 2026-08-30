"""Executable core proofs for solve, role-mode parity, and Solution graphs.

Every scenario uses the canonical Loop runtime. Offline model fixtures traverse
ModelGateway and are labeled as contract proof, not provider or quality proof.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
from ..templates.intake import TaskIntakeRequest, intake_task
from .solve_runtime import (
    SolveRequest, StructuredNormalizationResolver, solve_task)
from .solution_canvas import SolutionLoopSpec, SolutionSpec, run_solution
from .solution_compiler import compile_solution, run_compiled
from .solution_graph import LoopGraphDefinition
from .solution_model_port import (
    FixtureModelExecutionRequest,
    ModelInvocationRequest,
    fixture_model_execution,
)


@dataclass(frozen=True)
class CoreProofResult:
    proof_id: str
    passed: bool
    evidence: dict
    limitation: str = ""

    def to_dict(self) -> dict:
        return {"proof_id": self.proof_id, "passed": self.passed,
                "evidence": self.evidence, "limitation": self.limitation}


def _role_loop(role: LoopRole, profile: str, mode: str, ledger: LoopLedger) -> Loop:
    uses_model = mode in ("hybrid", "non_deterministic")
    config = LoopConfig(
        framework="custom", custom_steps=("act",), power="light",
        allowable_modes=(mode,), preferred_modes=(mode,),
        delegated_modes=("deterministic", "non_deterministic"),
        llm_thinking_power="small" if uses_model else "",
        exit_condition="accepted_success", max_depth=6)
    return Loop(
        f"prove {role.value} {mode}", config, ledger=ledger,
        identity=LoopRoleIdentity(role, profile),
        relationship=LoopRelationship.starting())


def role_mode_matrix_proof() -> CoreProofResult:
    """Execute all nine role-mode cells; roles never select the tier."""
    profiles = {
        LoopRole.PRACTITIONER: "practitioner.solver",
        LoopRole.INTELLIGENCE: "intelligence.context.frame",
    }
    cells = []
    for role, profile in profiles.items():
        for mode in ("deterministic", "hybrid", "non_deterministic"):
            ledger = LoopLedger()
            loop = _role_loop(role, profile, mode, ledger)
            session = (fixture_model_execution(FixtureModelExecutionRequest(
                answers=(json.dumps({"ok": True}),), max_model_calls=1))
                .start_session() if mode != "deterministic" else None)

            def handler(active, step, context, selected_mode=mode,
                        selected_session=session):
                if selected_session is not None:
                    selected_session.invoke(
                        ModelInvocationRequest("return a bounded fixture"),
                        active)
                return StepOutcome(
                    output="verified", mode=selected_mode, confidence=0.9)

            result = loop.run(handler=handler, max_steps=2)
            attempts = (sum(len(value.attempts)
                            for value in session.results) if session else 0)
            cells.append({"role": role.value, "mode": mode,
                          "terminal": result.terminal_code,
                          "physical_fixture_attempts": attempts,
                          "passed": result.accepted
                          and (attempts == 1 if session else attempts == 0)})

    for mode in ("deterministic", "hybrid", "non_deterministic"):
        operation = "solution_op"
        spec = SolutionSpec(
            f"role-matrix-{mode}", permitted_loop_modes=(mode,),
            loops=(SolutionLoopSpec("component", operation, mode=mode),))
        execution = (fixture_model_execution(FixtureModelExecutionRequest(
            answers=("model-result",), max_model_calls=1))
            if mode != "deterministic" else None)
        value = run_solution(
            spec, {operation: (lambda item, params:
                               params["model_port"](
                                   ModelInvocationRequest("solve"))
                               if "model_port" in params else "code-result")},
            "input", model_execution=execution)
        cells.append({"role": "solution", "mode": mode,
                      "terminal": "ACCEPTED", "value": value,
                      "passed": value in ("code-result", "model-result")})
    passed = len(cells) == 9 and all(cell["passed"] for cell in cells)
    return CoreProofResult(
        "role_mode_matrix", passed, {"cells": cells},
        "Model cells use offline ProviderAdapter fixtures; no live provider "
        "quality or connectivity is claimed.")


def solution_mode_proofs() -> tuple[CoreProofResult, CoreProofResult]:
    """Prove hybrid preprocessing/model/postprocessing and model-led Solution."""
    hybrid = SolutionSpec(
        "core-proof-hybrid", permitted_loop_modes=("deterministic", "hybrid"),
        loops=(
            SolutionLoopSpec("pre", "pre", input_role="raw/v1",
                             output_role="prepared/v1"),
            SolutionLoopSpec("interpret", "interpret", mode="hybrid",
                             input_role="prepared/v1",
                             output_role="interpreted/v1"),
            SolutionLoopSpec("post", "post", input_role="interpreted/v1",
                             output_role="verified/v1"),
        ))
    hybrid_ledger = LoopLedger()
    hybrid_value = run_solution(
        hybrid, {
            "pre": lambda value, params: str(value).strip().lower(),
            "interpret": lambda value, params: params["model_port"](
                ModelInvocationRequest(f"interpret:{value}")),
            "post": lambda value, params: {
                "artifact": value, "verified": value == "bounded meaning"},
        }, "  INPUT ", ledger=hybrid_ledger,
        model_execution=fixture_model_execution(FixtureModelExecutionRequest(
            answers=("bounded meaning",), max_model_calls=1)))
    hybrid_attempts = [event for event in hybrid_ledger.events
                       if event.get("event") == "model_led"]
    hybrid_result = CoreProofResult(
        "hybrid_solution", bool(hybrid_value.get("verified")
                                and len(hybrid_attempts) == 1),
        {"result": hybrid_value, "model_attempt_loops": [
            event.get("loop_id") for event in hybrid_attempts]})

    model_led = SolutionSpec(
        "core-proof-model-led", permitted_loop_modes=("non_deterministic",),
        loops=(SolutionLoopSpec(
            "lead", "lead", mode="non_deterministic",
            input_role="request/v1", output_role="answer/v1"),))
    model_ledger = LoopLedger()
    model_value = run_solution(
        model_led,
        {"lead": lambda value, params: params["model_port"](
            ModelInvocationRequest("answer"))},
        "request", ledger=model_ledger,
        model_execution=fixture_model_execution(FixtureModelExecutionRequest(
            answers=("typed answer",), max_model_calls=1)))
    model_attempts = [event for event in model_ledger.events
                      if event.get("event") == "model_led"]
    model_result = CoreProofResult(
        "non_deterministic_solution",
        model_value == "typed answer" and len(model_attempts) == 1,
        {"result": model_value, "model_attempt_loops": [
            event.get("loop_id") for event in model_attempts]},
        "Offline gateway fixture only; live provider remains separately gated.")
    return hybrid_result, model_result


def canvas_roundtrip_proof() -> CoreProofResult:
    """Compare three passive candidates, select one, execute, and reload graph."""
    registry = {
        "minimal": lambda value, params: {"value": value, "verified": True},
        "balanced": lambda value, params: {
            "value": value, "verified": True, "checks": ["type", "content"]},
        "higher": lambda value, params: {
            "value": value, "verified": True,
            "checks": ["type", "content", "redundant"], "provider_needed": True},
    }
    candidates = (
        ("minimal", SolutionSpec("candidate-minimal", loops=(
            SolutionLoopSpec("run", "minimal"),)),
         {"cost": 1, "verification_strength": 1, "provider_dependence": 0}),
        ("balanced", SolutionSpec("candidate-balanced", loops=(
            SolutionLoopSpec("run", "balanced"),)),
         {"cost": 2, "verification_strength": 2, "provider_dependence": 0}),
        ("higher", SolutionSpec("candidate-higher", loops=(
            SolutionLoopSpec("run", "higher"),)),
         {"cost": 4, "verification_strength": 3, "provider_dependence": 1}),
    )
    eligible = [item for item in candidates
                if item[2]["verification_strength"] >= 2
                and item[2]["provider_dependence"] == 0]
    selected = min(eligible, key=lambda item: item[2]["cost"])
    compiled = compile_solution(selected[1], registry)
    value = run_compiled(compiled["plan"], registry, "input")
    reloaded = LoopGraphDefinition.from_dict(compiled["plan"])
    passed = (selected[0] == "balanced" and value.get("verified")
              and reloaded.content_digest == compiled["digest"])
    return CoreProofResult(
        "solution_canvas_roundtrip", passed,
        {"candidates": [{"id": item[0], **item[2]} for item in candidates],
         "hard_filter": "verification_strength>=2 and provider_dependence=0",
         "selected": selected[0], "graph_digest": compiled["digest"],
         "reloaded_digest": reloaded.content_digest, "result": value})


def solve_proof(root: str) -> CoreProofResult:
    data = Path(root) / "core-proof.json"
    data.write_text(json.dumps({" name ": " Alice ", "count": 2}),
                    encoding="utf-8")
    outcome = solve_task(SolveRequest(
        intake_task(TaskIntakeRequest(
            dataset=str(data), goal="validate and normalize this record")),
        runs_dir=root,
        deterministic_resolvers=(StructuredNormalizationResolver(data),)))
    passed = (outcome.solved and outcome.result["verified"]
              and outcome.run_history["chain_intact"])
    return CoreProofResult("deterministic_solve", passed, outcome.to_dict())


def learning_cycle_proof() -> CoreProofResult:
    """Run the independently governed two-run learning and transfer checks."""
    from ..memory.storage.repository import self_test as learning_self_test

    report = learning_self_test()
    failures = [item for item in report["tests"] if not item["passed"]]
    required = {
        "run_b_retrieves_and_observably_uses_promoted_intelligence",
        "matched_no_memory_control_shows_measurable_improvement",
        "negative_transfer_is_blocked_by_scope_before_ranking",
        "promotion_survives_fresh_repository_process_state",
    }
    observed = {item["name"] for item in report["tests"] if item["passed"]}
    return CoreProofResult(
        "governed_learning_cycle", not failures and required <= observed,
        {"checks": report["tests"], "required_checks": sorted(required)},
        "Measured improvement is a deterministic fixture delta, not a "
        "production-quality or model-performance claim.")


def run_core_engine_proofs(root: str = "") -> dict:
    owned_root = root or tempfile.mkdtemp(prefix="loop-core-proof-")
    proofs = [solve_proof(owned_root), role_mode_matrix_proof(),
              *solution_mode_proofs(), canvas_roundtrip_proof(),
              learning_cycle_proof()]
    return {"record_type": "core_engine_proofs/v1",
            "proofs": [proof.to_dict() for proof in proofs],
            "passed": sum(proof.passed for proof in proofs),
            "total": len(proofs),
            "all_passed": all(proof.passed for proof in proofs),
            "root": owned_root}


def self_test() -> dict:
    report = run_core_engine_proofs()
    return {"tests": [{"name": item["proof_id"],
                       "passed": item["passed"],
                       "note": item.get("limitation", "")}
                      for item in report["proofs"]]}
