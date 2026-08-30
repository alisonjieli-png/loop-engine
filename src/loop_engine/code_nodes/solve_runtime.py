"""Canonical task intake, compilation, execution, verification, and history.

The Starting Practitioner owns intelligence queries and the selected Solution
graph. Unknown work returns a typed failure instead of placeholder success.
"""
from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..core.adaptive_practitioner import run_adaptive_practitioner
from ..core.adaptive_practitioner_records import (
    AdaptivePractitionerDependencies, AdaptivePractitionerRequest)
from ..templates.compiler import TaskCompileRequest, compile_task_value
from ..templates.intake import TaskIntake
from ..templates.model import InteractionMode, TaskFeedback
from .solution_model_port import ModelExecution


class SolveTerminalCode(str, Enum):
    COMPLETED_VERIFIED = "COMPLETED_VERIFIED"
    COMPLETED_PARTIAL = "COMPLETED_PARTIAL"
    BLOCKED_MATERIAL_INPUT = "BLOCKED_MATERIAL_INPUT"
    AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"
    CAPABILITY_GAP = "CAPABILITY_GAP"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REPAIR_UNAVAILABLE = "REPAIR_UNAVAILABLE"
    NO_PROGRESS = "NO_PROGRESS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    DEADLINE_EXHAUSTED = "DEADLINE_EXHAUSTED"
    ABSTAINED = "ABSTAINED"
    CANCELLED = "CANCELLED"


SOLVE_FAILURE_CODES = tuple(
    item.value for item in SolveTerminalCode
    if item is not SolveTerminalCode.COMPLETED_VERIFIED)


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
    workspace_root: str = ""
    allow_source_materialization_to_model: bool = False
    deterministic_resolvers: tuple[object, ...] = field(
        default=(), repr=False, compare=False)

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
        if any(not callable(getattr(item, "supports", None))
               or not callable(getattr(item, "execute", None))
               for item in self.deterministic_resolvers):
            raise SolveError(
                "deterministic_resolvers must implement supports and execute")


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
    summary: str = ""
    artifacts: tuple[dict, ...] = ()
    workspace: str = ""
    limitations: tuple[str, ...] = ()
    next_action: str = ""
    inspect_commands: tuple[str, ...] = ()
    model_calls: int = 0
    tool_calls: int = 0
    loop_count: int = 0
    elapsed_seconds: float = 0.0
    model_usage: tuple[dict, ...] = ()

    def __post_init__(self) -> None:
        valid_codes = {item.value for item in SolveTerminalCode}
        if self.status not in valid_codes:
            raise SolveError(f"unknown terminal code {self.status!r}")
        if self.failure_code and self.failure_code not in SOLVE_FAILURE_CODES:
            raise SolveError(f"unknown solve failure code {self.failure_code!r}")
        if self.solved and self.failure_code:
            raise SolveError("a solved outcome cannot carry a failure code")

    def to_dict(self) -> dict:
        return {
            "record_type": "solve_outcome/v3", "run_id": self.run_id,
            "terminal_code": self.status, "status": self.status,
            "solved": self.solved, "summary": self.summary,
            "failure_code": self.failure_code, "result": self.result,
            "compiled_task": self.compiled_task,
            "intelligence": self.intelligence,
            "selected_mode": self.selected_mode,
            "selected_canvas": self.selected_canvas,
            "graph_digest": self.graph_digest,
            "verification": self.verification,
            "run_history": self.run_history,
            "artifacts": list(self.artifacts), "workspace": self.workspace,
            "limitations": list(self.limitations),
            "next_action": self.next_action,
            "inspect_commands": list(self.inspect_commands),
            "model_calls": self.model_calls, "tool_calls": self.tool_calls,
            "loop_count": self.loop_count,
            "elapsed_seconds": self.elapsed_seconds,
            "model_usage": list(self.model_usage),
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
        return SolveTerminalCode.CAPABILITY_GAP.value
    if code in ("SolutionModelError", "MODEL_PROVIDER_UNAVAILABLE"):
        return SolveTerminalCode.PROVIDER_UNAVAILABLE.value
    if code in ("PermissionError", "PERMISSION_DENIED"):
        return SolveTerminalCode.AUTHORITY_REQUIRED.value
    if code in ("AdaptivePractitionerError", "OUTPUT_CONTRACT_VIOLATION"):
        return SolveTerminalCode.VERIFICATION_FAILED.value
    if code in ("NO_PROGRESS", "stop_unprofitable"):
        return SolveTerminalCode.NO_PROGRESS.value
    return SolveTerminalCode.VERIFICATION_FAILED.value


def _model_usage(adaptive: dict) -> tuple[dict, ...]:
    return tuple(adaptive.get("model_usage") or ())


def _product_result(adaptive: dict, solved: bool) -> dict:
    attempt = ((adaptive.get("project_attempts") or [])[-1]
               if adaptive.get("project_attempts") else None)
    if not attempt:
        return {
            "result": adaptive.get("result"), "summary": (
                "Completed an exact registered deterministic procedure."
                if solved else "No verified artifact was produced."),
            "artifacts": (), "workspace": "", "tool_calls": 0,
        }
    workspace = str(attempt.get("workspace_path")
                    or (attempt.get("workspace") or {}).get("root") or "")
    artifacts = []
    for item in attempt.get("artifacts", ()):
        path = str(Path(workspace) / str(item.get("path"))) if workspace else str(
            item.get("path") or "")
        artifacts.append({**item, "path": path})
    return {
        "result": attempt,
        "summary": str((attempt.get("manifest") or {}).get("summary")
                       or "Generated and verified the requested project."),
        "artifacts": tuple(artifacts), "workspace": workspace,
        "tool_calls": len(attempt.get("writes", ()))
        + len(attempt.get("commands", ())),
    }


def solve_task(request: SolveRequest) -> SolveOutcome:
    """Run one intake through the universal adaptive Practitioner."""
    if not isinstance(request, SolveRequest):
        raise SolveError("solve_task needs SolveRequest")
    started = time.monotonic()
    compiled = compile_task_value(TaskCompileRequest(
        text=request.intake.original_input,
        source_kind=request.intake.kind,
        source_refs=request.intake.source_refs,
        interaction_mode=request.interaction_mode,
        feedback=request.feedback))
    resolvers = tuple(request.deterministic_resolvers)
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
            feedback=request.feedback,
            workspace_root=request.workspace_root,
            allow_source_materialization_to_model=
                request.allow_source_materialization_to_model),
        AdaptivePractitionerDependencies(
            model_execution=request.model_execution,
            deterministic_resolvers=resolvers))
    solved = bool(adaptive.get("solved"))
    product = _product_result(adaptive, solved)
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
    terminal = (SolveTerminalCode.COMPLETED_VERIFIED.value if solved
                else _failure_code(adaptive))
    history = adaptive.get("run_history") or {}
    inspect = tuple(filter(None, (
        (f"loop-engine --report {adaptive.get('run_id')} --runs-dir "
         f"{request.runs_dir}" if adaptive.get("run_id") and request.runs_dir
         else ""),
        (f"loop-engine --studio --runs-dir {request.runs_dir}"
         if request.runs_dir else ""),
    )))
    deterministic_trace = adaptive.get("deterministic_attempt") or {}
    limitations = (() if solved else tuple(str(item) for item in (
        adaptive.get("failures")
        or deterministic_trace.get("unresolved_requirements")
        or deterministic_trace.get("diagnostics")
        or ("No compatible verified capability completed the task.",))))
    return SolveOutcome(
        run_id=str(adaptive.get("run_id") or ""),
        status=terminal,
        solved=solved,
        failure_code="" if solved else terminal,
        result=(product["result"] if solved else {
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
        run_history=history,
        summary=product["summary"], artifacts=product["artifacts"],
        workspace=product["workspace"], limitations=limitations,
        next_action=("Inspect the verified artifacts and Run History."
                     if solved else _next_recovery(terminal)),
        inspect_commands=inspect,
        model_calls=int(adaptive.get("model_calls") or 0),
        tool_calls=int(product["tool_calls"]),
        loop_count=len(adaptive.get("loop_details") or ()),
        elapsed_seconds=round(time.monotonic() - started, 3),
        model_usage=_model_usage(adaptive))


def _next_recovery(terminal: str) -> str:
    return {
        SolveTerminalCode.CAPABILITY_GAP.value:
            "Configure a supported model route or install a compatible capability.",
        SolveTerminalCode.PROVIDER_UNAVAILABLE.value:
            "Check the configured provider route and run a live provider probe.",
        SolveTerminalCode.AUTHORITY_REQUIRED.value:
            "Grant the exact workspace, source, or command authority requested.",
        SolveTerminalCode.VERIFICATION_FAILED.value:
            "Inspect the failed command and use an executable repair delta.",
    }.get(terminal, "Inspect Run History for the exact blocker before retrying.")


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
            runs_dir=root,
            deterministic_resolvers=(StructuredNormalizationResolver(data),)))
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
              and model.failure_code == "VERIFICATION_FAILED"
              and model.run_history["chain_intact"])
        unavailable = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(text="invent a new theorem")),
            runs_dir=root))
        check("unavailable_executor_never_returns_solved_true",
              not unavailable.solved
              and unavailable.failure_code == "CAPABILITY_GAP")
        autonomous = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                text="Train and compare several supervised prediction models.")),
            runs_dir=root,
            interaction_mode=InteractionMode.AUTONOMOUS))
        check("autonomous_interaction_terminates_without_a_question",
              not autonomous.solved
              and autonomous.failure_code == "CAPABILITY_GAP"
              and autonomous.compiled_task["binding"]
                  ["can_continue_without_user_input"]
              and autonomous.compiled_task["binding"]
                  ["delegated_requirements"]
                  == ["dataset_source", "target_column"])
    return {"tests": results}
