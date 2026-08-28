"""Canonical task intake, compilation, execution, verification, and history.

The Starting Practitioner owns intelligence queries and the selected Solution
graph. Unknown work returns a typed failure instead of placeholder success.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from ..core.adaptive_practitioner import run_adaptive_practitioner
from ..core.adaptive_practitioner_records import (
    AdaptivePractitionerDependencies, AdaptivePractitionerRequest)
from ..templates.compiler import TaskCompileRequest, compile_task_value
from ..templates.intake import TaskIntake
from ..templates.model import InteractionMode, TaskFeedback
from .solution_model_port import ModelExecution


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
    interaction_mode: InteractionMode = InteractionMode.ASK_WHEN_MATERIAL
    feedback: tuple[TaskFeedback, ...] = ()
    max_passes: int = 24
    allow_network_reads: bool = False
    allow_workspace_writes: bool = False
    allow_sandbox_commands: bool = False

    def __post_init__(self) -> None:
        mode = self.interaction_mode
        if not isinstance(mode, InteractionMode):
            try:
                mode = InteractionMode(mode)
            except (TypeError, ValueError) as exc:
                raise SolveError("interaction_mode is not recognized") from exc
            object.__setattr__(self, "interaction_mode", mode)
        feedback = tuple(self.feedback)
        if any(not isinstance(item, TaskFeedback) for item in feedback):
            raise SolveError("feedback must contain TaskFeedback values")
        slots = tuple(item.slot_ref for item in feedback)
        if len(slots) != len(set(slots)):
            raise SolveError("task feedback slots cannot repeat")
        object.__setattr__(self, "feedback", feedback)
        if not 1 <= self.max_passes <= 32:
            raise SolveError("max_passes must be from 1 through 32")


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


@dataclass(frozen=True)
class StructuredNormalizationResolver:
    """Exact registered file procedure used by the deterministic baseline."""

    path: Path
    resolver_id: str = "core.structured.normalize@1"

    def supports(self, task: str) -> bool:
        return bool(task.strip() and self.path.is_file())

    def execute(self, task: str) -> dict:
        del task
        return _normalize_structured(_load_structured(self.path))


def _failure_code(result: dict) -> str:
    code = str(result.get("failure_code") or "")
    if code in ("NO_VERIFIED_CAPABILITY", "EXECUTOR_UNAVAILABLE"):
        return "EXECUTOR_UNAVAILABLE"
    if code in ("SolutionModelError", "MODEL_PROVIDER_UNAVAILABLE"):
        return "MODEL_PROVIDER_UNAVAILABLE"
    if code in ("PermissionError", "PERMISSION_DENIED"):
        return "PERMISSION_DENIED"
    if code in ("AdaptivePractitionerError", "OUTPUT_CONTRACT_VIOLATION"):
        return "OUTPUT_CONTRACT_VIOLATION"
    return "VERIFICATION_FAILED"


def solve_task(request: SolveRequest) -> SolveOutcome:
    """Run one intake through the universal adaptive Practitioner."""
    if not isinstance(request, SolveRequest):
        raise SolveError("solve_task needs SolveRequest")
    compiled = compile_task_value(TaskCompileRequest(
        text=request.intake.original_input,
        source_kind=request.intake.kind,
        source_refs=request.intake.source_refs,
        interaction_mode=request.interaction_mode,
        feedback=request.feedback))
    source = _structured_source(request.intake)
    exact = bool(source is not None and compiled.get("binding", {}).get(
        "template_id") == "core.task.data_standardization")
    resolvers = ((StructuredNormalizationResolver(source),)
                 if exact and source is not None else ())
    mode = "hybrid" if request.model_execution is not None else "deterministic"
    adaptive = run_adaptive_practitioner(
        AdaptivePractitionerRequest(
            request.intake.original_input, mode=mode,
            runs_dir=request.runs_dir,
            max_passes=(1 if resolvers else request.max_passes),
            interaction_mode=request.interaction_mode.value,
            allow_network_reads=request.allow_network_reads,
            allow_workspace_writes=request.allow_workspace_writes,
            allow_sandbox_commands=request.allow_sandbox_commands,
            source_kind=request.intake.kind,
            source_refs=request.intake.source_refs,
            feedback=request.feedback),
        AdaptivePractitionerDependencies(
            model_execution=request.model_execution,
            deterministic_resolvers=resolvers))
    solved = bool(adaptive.get("solved"))
    selected = adaptive.get("selected_solution_canvas") or {}
    verification = ((adaptive.get("verification") or [{}])[-1]
                    if adaptive.get("verification") else {
                        "passed": solved,
                        "method": ("exact registered deterministic resolver"
                                   if resolvers else "not completed"),
                        "independent_from_provider": bool(resolvers)})
    if "passed" not in verification:
        verification = {**verification, "passed": bool(
            solved or verification.get("verdict") == "accept")}
    return SolveOutcome(
        run_id=str(adaptive.get("run_id") or ""),
        status=str(adaptive.get("status") or "NOT_YET_PROVEN"),
        solved=solved,
        failure_code="" if solved else _failure_code(adaptive),
        result=(adaptive.get("result") if solved else {
            "error": adaptive.get("failure") or adaptive.get("failures")
                     or "solve did not complete"}),
        compiled_task=compiled,
        intelligence={
            "context": adaptive.get("context_intelligence", {}),
            "search_candidates": adaptive.get("web_search_candidates", []),
            "fetched_sources": adaptive.get("web_evidence", []),
        },
        selected_mode=mode,
        selected_canvas=selected,
        graph_digest=str(selected.get("graph_digest") or ""),
        verification=verification,
        run_history=adaptive.get("run_history") or {})


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
        check("one_model_answer_cannot_bypass_the_practitioner_cycle",
              not model.solved
              and model.failure_code == "OUTPUT_CONTRACT_VIOLATION"
              and model.run_history["chain_intact"])
        unavailable = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(text="invent a new theorem")),
            runs_dir=root))
        check("unavailable_executor_never_returns_solved_true",
              not unavailable.solved
              and unavailable.failure_code == "EXECUTOR_UNAVAILABLE")
        autonomous = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                text="Train and compare several supervised prediction models.")),
            runs_dir=root,
            interaction_mode=InteractionMode.AUTONOMOUS))
        check("autonomous_interaction_terminates_without_a_question",
              not autonomous.solved
              and autonomous.failure_code == "EXECUTOR_UNAVAILABLE"
              and autonomous.compiled_task["binding"]
                  ["can_continue_without_user_input"]
              and autonomous.compiled_task["binding"]
                  ["delegated_requirements"]
                  == ["dataset_source", "target_column"])
    return {"tests": results}
