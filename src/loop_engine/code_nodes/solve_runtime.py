"""Canonical task intake, compilation, execution, verification, and history.

The Starting Practitioner owns intelligence queries and the selected Solution
graph. Unknown work returns a typed failure instead of placeholder success.
"""
from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..core.run_history import default_runs_dir, verify_saved_run
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome
from ..templates.compiler import TaskCompileRequest, compile_task_value
from ..templates.intake import TaskIntake
from .solution_canvas import (SolutionLoopSpec, SolutionSpec, run_solution)
from .solution_model_port import ModelExecution, ModelInvocationRequest


SOLVE_FAILURE_CODES = (
    "EXECUTOR_UNAVAILABLE", "MODEL_PROVIDER_UNAVAILABLE",
    "MODE_NOT_ALLOWED_BY_DEFINITION", "PERMISSION_DENIED",
    "BUDGET_INSUFFICIENT", "OUTPUT_CONTRACT_VIOLATION",
    "VERIFICATION_FAILED",
)


class SolveError(ValueError):
    """A solve request or result violated its typed contract."""


@dataclass(frozen=True)
class SolveRequest:
    intake: TaskIntake
    model_execution: ModelExecution | None = field(
        default=None, repr=False, compare=False)
    runs_dir: str = ""
    save_run_history: bool = True


@dataclass(frozen=True)
class SolveOutcome:
    run_id: str
    status: str
    solved: bool
    failure_code: str = ""
    result: object = None
    compiled_task: dict = field(default_factory=dict)
    intelligence: dict = field(default_factory=dict)
    selected_mode: str = "deterministic"
    selected_canvas: dict = field(default_factory=dict)
    graph_digest: str = ""
    verification: dict = field(default_factory=dict)
    run_history: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.failure_code and self.failure_code not in SOLVE_FAILURE_CODES:
            raise SolveError(f"unknown solve failure code {self.failure_code!r}")
        if self.solved and self.failure_code:
            raise SolveError("a solved outcome cannot carry a failure code")

    def to_dict(self) -> dict:
        return {
            "record_type": "solve_outcome/v2", "run_id": self.run_id,
            "status": self.status, "solved": self.solved,
            "failure_code": self.failure_code, "result": self.result,
            "compiled_task": self.compiled_task,
            "intelligence": self.intelligence,
            "selected_mode": self.selected_mode,
            "selected_canvas": self.selected_canvas,
            "graph_digest": self.graph_digest,
            "verification": self.verification,
            "run_history": self.run_history,
        }


def _structured_source(intake: TaskIntake) -> Path | None:
    refs = [Path(value) for value in intake.source_refs
            if not str(value).startswith(("http://", "https://"))]
    for path in refs:
        if path.is_file() and path.suffix.lower() in (
                ".csv", ".tsv", ".json", ".jsonl"):
            return path
    return None


def _load_structured(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix in (".csv", ".tsv"):
        delimiter = "\t" if suffix == ".tsv" else ","
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter=delimiter))
        fields = tuple(rows[0]) if rows else ()
        return {"kind": "table", "fields": list(fields), "rows": rows}
    if suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        return {"kind": "records", "rows": rows}
    return {"kind": "json", "value": json.loads(path.read_text(
        encoding="utf-8"))}


def _normalize_structured(value: dict) -> dict:
    def clean(item):
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, list):
            return [clean(value) for value in item]
        if isinstance(item, dict):
            return {str(key).strip(): clean(value)
                    for key, value in item.items()}
        return item

    normalized = clean(value)
    size = len(normalized.get("rows", ())) if isinstance(normalized, dict) else 1
    return {"artifact": normalized, "records": size,
            "verified": True, "transformation": "whitespace_normalization"}


def _valid_model_result(text: str) -> bool:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return False
    return (isinstance(value, dict) and "answer" in value
            and isinstance(value.get("evidence", []), list)
            and "uncertainty" in value)


def _model_prompt(compiled: dict, intelligence: dict) -> str:
    refs = [str(item.get("record_id", "")) for item in
            intelligence.get("hits", ())[:8]]
    return (
        "Perform the compiled task. Return exactly one JSON object with keys "
        "answer, evidence, and uncertainty. Evidence must be a list of short "
        "source or verification references. Do not include private reasoning.\n"
        f"Original request: {compiled['original_input']}\n"
        f"Operator: {compiled['work_item']['coordinates']['operator']}\n"
        f"Response topology: "
        f"{compiled['work_item']['coordinates']['response_topology']}\n"
        f"Selected intelligence refs: {refs}")


def _query_intelligence(goal: str, *, parent: Loop) -> dict:
    from ..core.intelligence_layers import (
        IntelligenceSearchContext, IntelligenceSearchRequest,
        build_intelligence_catalog, query_intelligence)
    from ..loop.intelligence_loops import serve_context_intelligence

    catalog = build_intelligence_catalog()
    served = serve_context_intelligence(
        "solve-query", lambda: query_intelligence(
            IntelligenceSearchRequest(goal, catalog),
            IntelligenceSearchContext(parent=parent)),
        parent=parent, query_hint=goal,
        profile_id="intelligence.search")
    value = dict(served["value"])
    compact_hits = [{
        "record_id": item.get("record_id", ""),
        "layer": item.get("layer", ""),
        "score": item.get("score"),
        "intelligence_item_ref": (item.get("intelligence_item_ref") or {}).get(
            "intelligence_item_ref", ""),
    } for item in value.get("hits", [])]
    return {
        "query_loop_id": served["loop_id"], "need": value.get("need", goal),
        "hits": compact_hits,
        "unqueried": value.get("unqueried_public", value.get("unqueried", [])),
        "intelligence_item_refs": value.get("intelligence_item_refs", []),
    }


def solve_task(request: SolveRequest) -> SolveOutcome:
    """Run one intake through a Starting Practitioner and owned Solution graph."""
    if not isinstance(request, SolveRequest):
        raise SolveError("solve_task needs SolveRequest")
    run_id = ("solve-" + request.intake.content_digest[:12] + "-"
              + str(time.time_ns()))
    ledger = LoopLedger()
    config = LoopConfig(
        framework="custom",
        custom_steps=("orient", "compile_bind_task", "query_intelligence",
                      "act", "verify"),
        power="deep", allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic", "hybrid", "non_deterministic"),
        max_depth=10, exit_condition="steps_complete")
    practitioner = Loop(
        f"solve {request.intake.kind} task", config, ledger=ledger,
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER,
                                  "practitioner.solver"),
        relationship=LoopRelationship.starting())
    selected_runs_dir = default_runs_dir(request.runs_dir)
    if request.save_run_history:
        practitioner.enable_run_history(run_id, root_dir=selected_runs_dir)
    state: dict = {"failure_code": "", "result": None,
                   "verification": {"passed": False}}

    def handler(active: Loop, step: str, context: dict) -> StepOutcome:
        if step == "orient":
            state["intake"] = request.intake.to_dict()
        elif step == "compile_bind_task":
            state["compiled"] = compile_task_value(TaskCompileRequest(
                text=request.intake.original_input,
                source_kind=request.intake.kind,
                source_refs=request.intake.source_refs))
            active.ledger.record(
                loop_id=active.loop_id, event="state.committed",
                artifact_kind="compiled_task",
                compiled_task_id=state["compiled"]["compiled_task_id"])
        elif step == "query_intelligence":
            state["intelligence"] = _query_intelligence(
                request.intake.original_input, parent=active)
        elif step == "act":
            source = _structured_source(request.intake)
            if source is not None:
                spec = SolutionSpec(
                    "core.solve.structured",
                    permitted_loop_modes=("deterministic",),
                    loops=(
                        SolutionLoopSpec(
                            "load", "load_structured",
                            input_role="task.input/v1",
                            output_role="structured.value/v1",
                            params={"path": str(source)}),
                        SolutionLoopSpec(
                            "normalize", "normalize_structured",
                            input_role="structured.value/v1",
                            output_role="solution.verified_result/v1"),
                    ))
                registry = {
                    "load_structured": lambda _value, params: _load_structured(
                        Path(params["path"])),
                    "normalize_structured": lambda value, _params:
                        _normalize_structured(value),
                }
                state["selected_mode"] = "deterministic"
                state["result"] = run_solution(
                    spec, registry, state["compiled"], parent=active)
            elif request.model_execution is not None:
                authority = replace(request.model_execution,
                                    validator=_valid_model_result)
                spec = SolutionSpec(
                    "core.solve.model",
                    permitted_loop_modes=("deterministic",
                                          "non_deterministic"),
                    loops=(
                        SolutionLoopSpec(
                            "answer", "model_answer",
                            mode="non_deterministic",
                            input_role="task.compiled/v1",
                            output_role="solution.answer_text/v1"),
                        SolutionLoopSpec(
                            "verify", "verify_answer",
                            input_role="solution.answer_text/v1",
                            output_role="solution.verified_result/v1"),
                    ))
                prompt = _model_prompt(state["compiled"], state["intelligence"])
                registry = {
                    "model_answer": lambda _value, params:
                        params["model_port"](ModelInvocationRequest(
                            prompt, temperature=0.2)),
                    "verify_answer": lambda value, _params: {
                        **json.loads(value), "verified": _valid_model_result(value)},
                }
                state["selected_mode"] = "non_deterministic"
                state["result"] = run_solution(
                    spec, registry, state["compiled"], parent=active,
                    model_execution=authority)
            else:
                state["failure_code"] = "EXECUTOR_UNAVAILABLE"
                state["failure"] = (
                    "no verified deterministic procedure matches this intake, "
                    "and no authorized ModelGateway execution was supplied")
                return StepOutcome(
                    output="act:executor_unavailable", mode="deterministic",
                    confidence=0.0, failed=True)
            state["canvas"] = spec.graph.to_dict() if spec.graph else {}
            state["graph_digest"] = (
                spec.graph.content_digest if spec.graph else "")
        elif step == "verify":
            if state.get("failure_code"):
                return StepOutcome(
                    output="verify:not_run_after_execution_failure",
                    mode="deterministic", confidence=0.0, failed=True)
            value = state.get("result")
            passed = bool(isinstance(value, dict) and value.get("verified"))
            state["verification"] = {
                "passed": passed,
                "method": "deterministic output-contract verification",
                "independent_from_provider": True,
            }
            if not passed:
                state["failure_code"] = "VERIFICATION_FAILED"
                return StepOutcome(
                    output="verify:failed", mode="deterministic",
                    confidence=0.0, failed=True)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.95)

    try:
        practitioner.run(handler=handler,
                         max_steps=len(practitioner.steps()) + 1)
    except Exception as exc:  # the typed outcome retains the failure
        if not state.get("failure_code"):
            state["failure_code"] = (
                "MODEL_PROVIDER_UNAVAILABLE" if request.model_execution
                else "VERIFICATION_FAILED")
        state["failure"] = f"{type(exc).__name__}: {exc}"[:500]

    if request.save_run_history:
        history_summary = verify_saved_run(selected_runs_dir, run_id)
    else:
        history_summary = {
            "run_id": run_id, "events": len(ledger.events),
            "head_digest": "", "chain_intact": None, "broken_at": [],
            "path": "",
        }
    solved = bool(state.get("verification", {}).get("passed")
                  and not state.get("failure_code"))
    return SolveOutcome(
        run_id=run_id, status="VERIFIED_WORKING" if solved else "NOT_YET_PROVEN",
        solved=solved, failure_code=state.get("failure_code", ""),
        result=state.get("result") if solved else {
            "error": state.get("failure", "solve did not complete")},
        compiled_task=state.get("compiled", {}),
        intelligence=state.get("intelligence", {}),
        selected_mode=state.get("selected_mode", "deterministic"),
        selected_canvas=state.get("canvas", {}),
        graph_digest=state.get("graph_digest", ""),
        verification=state.get("verification", {}),
        run_history=history_summary)


def self_test() -> dict:
    import tempfile

    from ..templates.intake import TaskIntakeRequest, intake_task
    from .solution_model_port import (
        FixtureModelExecutionRequest,
        fixture_model_execution,
    )

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as root:
        data = Path(root) / "rows.csv"
        data.write_text("id,name\n1, Alice \n2,Bob\n", encoding="utf-8")
        deterministic = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                dataset=str(data), goal="validate and normalize this dataset")),
            runs_dir=root))
        check("deterministic_structured_task_does_real_work",
              deterministic.solved
              and deterministic.result["artifact"]["rows"][0]["name"]
                  == "Alice"
              and deterministic.run_history["chain_intact"])
        model = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(text="explain this bounded task")),
            model_execution=fixture_model_execution(
                FixtureModelExecutionRequest(
                    answers=(json.dumps({
                        "answer": "done", "evidence": ["fixture"],
                        "uncertainty": "offline fixture",
                    }),), max_model_calls=1)), runs_dir=root))
        check("model_task_uses_solution_gateway_and_verifier",
              model.solved and model.selected_mode == "non_deterministic"
              and model.result["answer"] == "done"
              and model.verification["independent_from_provider"])
        unavailable = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(text="invent a new theorem")),
            runs_dir=root))
        check("unavailable_executor_never_returns_solved_true",
              not unavailable.solved
              and unavailable.failure_code == "EXECUTOR_UNAVAILABLE")
    return {"tests": results}
