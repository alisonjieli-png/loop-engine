"""Canonical task intake, compilation, execution, verification, and history.

The Starting Practitioner owns intelligence queries and the selected Solution
graph. Unknown work returns a typed failure instead of placeholder success.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Callable

from .material_questions import screen_material_questions
from .solve_region_evidence import region_evidence_for_solve
from ..core.adaptive_practitioner import run_adaptive_practitioner
from ..core.adaptive_practitioner_records import (
    AdaptivePractitionerDependencies, AdaptivePractitionerRequest)
from ..templates.compiler import TaskCompileRequest, compile_task_value
from ..templates.intake import TaskIntake
from ..templates.model import InteractionMode, TaskFeedback
from ..core.generated_project import execute_generated_project
from ..core.terminal_layer import deepest_layer_reached
from .solution_model_port import ModelExecution
from .solve_terminal import (
    SOLVE_FAILURE_CODES, SolveTerminalCode, failure_code_for)


class SolveError(ValueError):
    """A solve request or result violated its typed contract."""


@dataclass(frozen=True)
class MaterialQuestion:
    """One material clarification the Practitioner needs before continuing."""

    question_id: str
    question: str
    subject: str
    answer_slot: str
    reason: str

    def __post_init__(self) -> None:
        values = (
            self.question_id, self.question, self.subject,
            self.answer_slot, self.reason)
        if any(not isinstance(value, str) or not value.strip()
               for value in values):
            raise SolveError("material question fields must be non-empty text")
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{0,127}", self.answer_slot):
            raise SolveError("material question answer_slot is not portable")

    def to_dict(self) -> dict:
        return {
            "record_type": "material_question/v1",
            "question_id": self.question_id,
            "question": self.question,
            "subject": self.subject,
            "answer_slot": self.answer_slot,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SolveRequest:
    intake: TaskIntake
    model_execution: ModelExecution | None = field(
        default=None, repr=False, compare=False)
    runs_dir: str = ""
    save_run_history: bool = True
    interaction_mode: InteractionMode = InteractionMode.ASK_WHEN_MATERIAL
    practitioner_mode: str = "non_deterministic"
    feedback: tuple[TaskFeedback, ...] = ()
    max_passes: "int | None" = None
    allow_network_reads: bool = False
    allow_workspace_writes: bool = False
    allow_sandbox_commands: bool = False
    workspace_root: str = ""
    allow_source_materialization_to_model: bool = False
    deterministic_resolvers: tuple[object, ...] = field(
        default=(), repr=False, compare=False)
    extension_snapshot: dict = field(default_factory=dict)
    progress: "Callable[[dict], None] | None" = field(
        default=None, repr=False, compare=False)
    reuse_observation_port: "object | None" = field(
        default=None, repr=False, compare=False)
    project_executor: "Callable | None" = field(
        default=None, repr=False, compare=False)
    quiet_model_io: bool = False
    #: Host execution when Docker is absent; off by default (no OS sandbox).
    allow_local_execution: bool = False
    #: Operator context budget; None selects the canonical policy default.
    context_budget: "object | None" = field(
        default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        mode = self.interaction_mode
        if not isinstance(mode, InteractionMode):
            try:
                mode = InteractionMode(mode)
            except (TypeError, ValueError) as exc:
                raise SolveError("interaction_mode is not recognized") from exc
            object.__setattr__(self, "interaction_mode", mode)
        if self.practitioner_mode not in (
                "deterministic", "hybrid", "non_deterministic"):
            raise SolveError("practitioner_mode is not recognized")
        feedback = tuple(self.feedback)
        if any(not isinstance(item, TaskFeedback) for item in feedback):
            raise SolveError("feedback must contain TaskFeedback values")
        slots = tuple(item.slot_ref for item in feedback)
        if len(slots) != len(set(slots)):
            raise SolveError("task feedback slots cannot repeat")
        object.__setattr__(self, "feedback", feedback)
        if (self.max_passes is not None
                and (not isinstance(self.max_passes, int)
                     or isinstance(self.max_passes, bool)
                     or self.max_passes < 1)):
            raise SolveError("max_passes must be positive when provided")
        if any(not callable(getattr(item, "supports", None))
               or not callable(getattr(item, "execute", None))
               for item in self.deterministic_resolvers):
            raise SolveError(
                "deterministic_resolvers must implement supports and execute")
        if (not isinstance(self.extension_snapshot, dict)
                or (self.extension_snapshot
                and self.extension_snapshot.get("record_type")
                != "extension_snapshot/v1")):
            raise SolveError("extension_snapshot has an invalid contract")
        if self.progress is not None and not callable(self.progress):
            raise SolveError("progress must be callable when supplied")
        from ..core.reusable_capability_harvest import ReuseObservationPort
        if (self.reuse_observation_port is not None
                and not isinstance(
                    self.reuse_observation_port, ReuseObservationPort)):
            raise SolveError(
                "reuse_observation_port must be a ReuseObservationPort")
        if (self.project_executor is not None
                and not callable(self.project_executor)):
            raise SolveError("project_executor must be callable when supplied")


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
    #: What was asked for, beside what was got: a run asked to reason and
    #: unable to is a different event from one nobody asked.
    requested_mode: str = ""
    mode_demoted_because: str = ""
    selected_canvas: dict = field(default_factory=dict)
    graph_digest: str = ""
    verification: dict = field(default_factory=dict)
    run_history: dict = field(default_factory=dict)
    summary: str = ""
    artifacts: tuple[dict, ...] = ()
    workspace: str = ""
    limitations: tuple[str, ...] = ()
    questions: tuple[MaterialQuestion, ...] = ()
    next_action: str = ""
    inspect_commands: tuple[str, ...] = ()
    model_calls: int = 0
    tool_calls: int = 0
    loop_count: int = 0
    elapsed_seconds: float = 0.0
    model_usage: tuple[dict, ...] = ()
    reuse_observation: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        valid_codes = {item.value for item in SolveTerminalCode}
        if self.status not in valid_codes:
            raise SolveError(f"unknown terminal code {self.status!r}")
        if self.failure_code and self.failure_code not in SOLVE_FAILURE_CODES:
            raise SolveError(f"unknown solve failure code {self.failure_code!r}")
        if self.solved and self.failure_code:
            raise SolveError("a solved outcome cannot carry a failure code")
        if any(not isinstance(item, MaterialQuestion)
               for item in self.questions):
            raise SolveError("questions must contain MaterialQuestion values")
        if self.questions and self.status != \
                SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value:
            raise SolveError(
                "material questions require BLOCKED_MATERIAL_INPUT")
        if (self.status == SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value
                and not self.questions):
            raise SolveError(
                "BLOCKED_MATERIAL_INPUT requires an answerable question")

    def to_dict(self) -> dict:
        return {
            "record_type": "solve_outcome/v4", "run_id": self.run_id,
            "terminal_code": self.status, "status": self.status,
            "solved": self.solved, "summary": self.summary,
            "failure_code": self.failure_code, "result": self.result,
            "compiled_task": self.compiled_task,
            "intelligence": self.intelligence,
            "selected_mode": self.selected_mode,
            "requested_mode": self.requested_mode or self.selected_mode,
            **({"mode_demoted_because": self.mode_demoted_because}
               if self.mode_demoted_because else {}),
            "selected_canvas": self.selected_canvas,
            "graph_digest": self.graph_digest,
            "verification": self.verification,
            "run_history": self.run_history,
            "artifacts": list(self.artifacts), "workspace": self.workspace,
            "limitations": list(self.limitations),
            "questions": [item.to_dict() for item in self.questions],
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


def _question_slot(subject: str, index: int) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", subject.lower()).strip("_")
    if not normalized or not normalized[0].isalpha():
        normalized = f"material_input_{index + 1}"
    return normalized[:128]


def _material_questions(result: dict) -> tuple[MaterialQuestion, ...]:
    """Project the latest accepted orientation into answerable questions."""
    orientations = tuple(result.get("orientations") or ())
    if not orientations:
        return ()
    latest = orientations[-1]
    # A run pauses for a person only on text a person can answer. The screen
    # is deterministic and keeps every rejected entry as a recorded reason,
    # so a model writing "None for this step" never blocks the run.
    raw_questions, screened_out = screen_material_questions(
        latest.get("blocking_questions", ()))
    if screened_out:
        result.setdefault("screened_material_questions", list(screened_out))
    if not raw_questions:
        return ()
    ambiguities = [
        item for item in latest.get("ambiguities", ())
        if isinstance(item, dict) and item.get("state")
        in ("USER_CLARIFICATION_REQUIRED", "BLOCKED")]
    output = []
    used_slots = set()
    for index, question in enumerate(raw_questions):
        question_terms = set(re.findall(r"[a-z0-9]{4,}", question.lower()))
        matched = next((
            item for item in ambiguities
            if question_terms & set(re.findall(
                r"[a-z0-9]{4,}", str(item.get("subject") or "").lower()))
        ), ambiguities[index] if index < len(ambiguities) else {})
        subject = str(matched.get("subject") or f"material input {index + 1}")
        reason = str(matched.get("reason") or
                     "The answer can materially change the work or result.")
        base_slot = _question_slot(subject, index)
        slot = base_slot
        suffix = 2
        while slot in used_slots:
            slot = f"{base_slot[:120]}_{suffix}"
            suffix += 1
        used_slots.add(slot)
        question_id = "question:" + hashlib.sha256(json.dumps(
            {"question": question, "subject": subject, "slot": slot},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:20]
        output.append(MaterialQuestion(
            question_id, question, subject, slot, reason))
    return tuple(output)


def _terminal_questions(result: dict, solved: bool) -> tuple:
    """Split the latest orientation's questions into blocking and open.

    A question blocks only when the run stopped without solving. A solved run
    that still lists questions in its last orientation did not need them
    answered; they are reported as open questions on the result, never as a
    blocking terminal, so a verified result is not refused by its own typed
    contract.
    """
    projected = _material_questions(result)
    if solved:
        return (), tuple(projected)
    return tuple(projected), ()


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
    # Becoming deterministic in silence leaves a record indistinguishable
    # from a run that never asked to reason at all.
    mode, mode_demoted_because = request.practitioner_mode, ""
    if request.model_execution is None:
        if request.practitioner_mode != "deterministic":
            mode_demoted_because = (
                f"asked for {request.practitioner_mode!r} but no model "
                "execution was configured, so no model was ever called")
        mode = "deterministic"
    region_evidence, tuned_budget = region_evidence_for_solve(request)
    adaptive = run_adaptive_practitioner(
        AdaptivePractitionerRequest(
            request.intake.original_input, mode=mode,
            runs_dir=request.runs_dir,
            max_passes=request.max_passes,
            interaction_mode=request.interaction_mode.value,
            allow_network_reads=request.allow_network_reads,
            allow_workspace_writes=request.allow_workspace_writes,
            allow_sandbox_commands=request.allow_sandbox_commands,
            source_kind=request.intake.kind,
            source_refs=request.intake.source_refs,
            feedback=request.feedback,
            workspace_root=request.workspace_root,
            allow_source_materialization_to_model=
                request.allow_source_materialization_to_model,
            persist_run_history=request.save_run_history,
            quiet_model_io=request.quiet_model_io,
            allow_local_execution=request.allow_local_execution,
            prior_region_evidence=region_evidence,
            **({"context_budget": request.context_budget}
               if request.context_budget is not None
               else {"context_budget": tuned_budget}
               if tuned_budget is not None else {})),
        AdaptivePractitionerDependencies(
            model_execution=request.model_execution,
            deterministic_resolvers=resolvers,
            progress=request.progress,
            reuse_observation_port=request.reuse_observation_port,
            project_executor=(request.project_executor
                              or execute_generated_project),
            extension_snapshot=request.extension_snapshot))
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
    questions, open_questions = _terminal_questions(adaptive, solved)
    terminal = (SolveTerminalCode.COMPLETED_VERIFIED.value if solved
                else SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value
                if questions
                else failure_code_for(adaptive))
    history = adaptive.get("run_history") or {}
    inspect = tuple(filter(None, (
        (f"loop-engine report {adaptive.get('run_id')} --runs-dir "
         f"{request.runs_dir}" if adaptive.get("run_id") and request.runs_dir
         else ""),
        (f"loop-engine studio --port 0 --runs-dir {request.runs_dir}"
         if request.runs_dir else ""),
    )))
    deterministic_trace = adaptive.get("deterministic_attempt") or {}
    limitations = (() if solved else tuple(str(item) for item in (
        adaptive.get("failures")
        or deterministic_trace.get("unresolved_requirements")
        or deterministic_trace.get("diagnostics")
        or ("No compatible verified capability completed the task.",))))
    summary = ("Material input is required before work can continue."
               if terminal == SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value
               else product["summary"])
    outcome = SolveOutcome(
        run_id=str(adaptive.get("run_id") or ""),
        status=terminal,
        solved=solved,
        failure_code="" if solved else terminal,
        result=({**product["result"],
                 **({"open_questions": [
                     item.to_dict() for item in open_questions]}
                    if open_questions else {})} if solved else {
            "error": adaptive.get("failure") or adaptive.get("failures")
                     or "solve did not complete"}),
        compiled_task=compiled,
        intelligence={
            "context": adaptive.get("context_intelligence", {}),
            # What the run drew on from the portfolio it was offered. Carried
            # out to the caller because a tally that only exists inside run
            # history cannot answer the question it was built for — which
            # options earn their place across many runs.
            "option_selection": adaptive.get("option_selection", {}),
            "search_candidates": adaptive.get("web_search_candidates", []),
            "fetched_sources": adaptive.get("web_evidence", []),
            "extensions": dict(request.extension_snapshot),
            "region_evidence": region_evidence,
        },
        selected_mode=mode,
        requested_mode=request.practitioner_mode,
        mode_demoted_because=mode_demoted_because,
        selected_canvas=selected,
        graph_digest=str(selected.get("graph_digest") or ""),
        verification=verification,
        run_history=history,
        summary=summary, artifacts=product["artifacts"],
        workspace=product["workspace"], limitations=limitations,
        questions=questions,
        next_action=("Inspect the verified artifacts and Run History."
                     if solved else _next_recovery(terminal)),
        inspect_commands=inspect,
        model_calls=int(adaptive.get("model_calls") or 0),
        tool_calls=int(product["tool_calls"]),
        loop_count=len(adaptive.get("loop_details") or ()),
        elapsed_seconds=round(time.monotonic() - started, 3),
        model_usage=_model_usage(adaptive),
        reuse_observation=dict(
            adaptive.get("reuse_observation") or {}))
    if request.save_run_history and outcome.run_id and history.get("path"):
        from ..core.run_history import bind_product_outcome
        run_root = str(Path(str(history["path"])).parent)
        outcome_ref = bind_product_outcome(
            run_root, outcome.run_id, outcome.to_dict())
        outcome = replace(outcome, run_history={
            **dict(history), "product_outcome_bound": True,
            "product_outcome_digest": outcome_ref.content_digest,
            "terminal_code": outcome.status,
            "product_outcome": outcome_ref.to_dict()})
    return outcome


def _next_recovery(terminal: str) -> str:
    return {
        SolveTerminalCode.BLOCKED_MATERIAL_INPUT.value:
            "Answer the listed material questions with --task-feedback "
            "answer_slot=value, then run the same task again.",
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
    from unittest.mock import patch

    from ..templates.intake import TaskIntakeRequest, intake_task
    from .solution_model_port import (
        FixtureModelExecutionRequest,
        fixture_model_execution,
    )

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    check("an_explicit_failure_code_still_wins_over_layer_inference",
          failure_code_for({"failure_code": "timeout"})
          == SolveTerminalCode.PROVIDER_UNAVAILABLE.value
          and failure_code_for({"failure_code": "CANCELLED"})
          == SolveTerminalCode.CANCELLED.value,
          "layer inference is the fallback, not an override")

    class NonMatchingResolver:
        """Registered exact resolver that correctly declines this task."""

        resolver_id = "fixture.non_matching@1"

        def supports(self, _task):
            return False

        def execute(self, _task):
            raise AssertionError("a non-matching resolver must not execute")

    observed_pass_limits = []

    def capture_adaptive_request(adaptive_request, _dependencies):
        observed_pass_limits.append(adaptive_request.max_passes)
        return {
            "run_id": "fixture-no-injected-pass-ceiling",
            "solved": False,
            "failure_code": "NO_VERIFIED_CAPABILITY",
            "deterministic_attempt": {
                "status": "NO_VERIFIED_CAPABILITY",
                "diagnostics": ["fixture stopped before semantic work"],
            },
            "run_history": {},
            "loop_details": [],
        }

    with patch(
            "loop_engine.code_nodes.solve_runtime.run_adaptive_practitioner",
            side_effect=capture_adaptive_request):
        solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                text="Solve work not covered by the exact resolver.")),
            deterministic_resolvers=(NonMatchingResolver(),),
            save_run_history=False))
    check(
        "registered_resolver_does_not_inject_a_practitioner_pass_ceiling",
        observed_pass_limits == [None],
        "resolver presence changes eligibility, not semantic stopping")

    with tempfile.TemporaryDirectory() as root:
        data = Path(root) / "rows.csv"
        data.write_text("id,name\n1, Alice \n2,Bob\n", encoding="utf-8")
        extension_snapshot = {
            "record_type": "extension_snapshot/v1",
            "content_digest": "a" * 64, "loop_id": "loop-extension",
            "roots": [], "providers": [],
            "capabilities": [{"capability_ref": "plugin.test.candidate",
                              "lifecycle": "candidate"}],
            "skills": [], "plugins": [], "intelligence_entries": [],
            "reasons": []}
        deterministic = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                dataset=str(data), goal="validate and normalize this dataset")),
            runs_dir=root,
            deterministic_resolvers=(StructuredNormalizationResolver(data),),
            extension_snapshot=extension_snapshot))
        check("deterministic_structured_task_does_real_work",
              deterministic.solved
              and deterministic.result["artifact"]["rows"][0]["name"]
                  == "Alice"
              and deterministic.run_history["chain_intact"])
        check("solve_result_preserves_exact_added_file_snapshot",
              deterministic.intelligence["extensions"]
              == extension_snapshot)
        from ..core.run_history import load_saved_run_bundle
        deterministic_bundle = load_saved_run_bundle(
            root, deterministic.run_id)
        check("solve_terminal_and_result_are_bound_to_run_history",
              deterministic_bundle.outcome["terminal_code"]
              == "COMPLETED_VERIFIED"
              and deterministic_bundle.outcome["verification"]["passed"]
              and deterministic.run_history["product_outcome"][
                  "content_digest"]
              == deterministic_bundle.outcome_ref.content_digest
              and deterministic.run_history["product_outcome_bound"] is True
              and deterministic.run_history["terminal_code"]
                  == "COMPLETED_VERIFIED")
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
              and model.failure_code == "BUDGET_EXHAUSTED"
              and model.run_history["chain_intact"])
        from ..core.adaptive_practitioner_acceptance_checks import (
            _decision, _orientation)
        material_orientation = _orientation(
            unknowns=["required destination"],
            ambiguities=[{
                "subject": "required destination",
                "state": "USER_CLARIFICATION_REQUIRED",
                "reason": "The destination changes authority and delivery."}],
            blocking_questions=["Which destination is required?"],
            proposed_next_action="ASK_USER")
        ask_answers = tuple(json.dumps(item) for item in (
            material_orientation,
            {"actions": [_decision(
                "ASK_USER", goal="Ask for the required destination.",
                reason="The answer materially changes delivery authority.",
                expected_output="One destination answer.")]},
            {"verdict": "stop", "best_index": 0, "scores": [0.0],
             "notes": "Material input is missing.",
             "remaining_gaps": [{"criterion_ref": "criterion:destination",
                                  "gap": "required destination"}],
             "advisory_findings": [], "new_requirement_proposals": []},
            {"route": "stop_unprofitable",
             "reason": "Material input is missing."},
        ))
        asked = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                text="Deliver the verified result to the required destination.")),
            model_execution=fixture_model_execution(
                FixtureModelExecutionRequest(
                    answers=ask_answers, max_model_calls=len(ask_answers))),
            runs_dir=root,
            interaction_mode=InteractionMode.ASK_WHEN_MATERIAL))
        asked_bundle = load_saved_run_bundle(root, asked.run_id)
        check("material_question_is_a_typed_answerable_terminal_result",
              not asked.solved
              and asked.failure_code == "BLOCKED_MATERIAL_INPUT"
              and len(asked.questions) == 1
              and asked.questions[0].answer_slot == "required_destination"
              and asked.run_history["product_outcome_bound"] is True
              and asked.run_history["terminal_code"]
                  == "BLOCKED_MATERIAL_INPUT"
              and asked.to_dict()["record_type"] == "solve_outcome/v4"
              and asked_bundle.outcome["questions"][0]["answer_slot"]
                  == "required_destination",
              asked.summary)
        unavailable = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(text="invent a new theorem")),
            runs_dir=root))
        check("unavailable_executor_never_returns_solved_true",
              not unavailable.solved
              and unavailable.failure_code == "CAPABILITY_GAP")
        unsaved_root = str(Path(root) / "unsaved")
        unsaved = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(text="invent another theorem")),
            runs_dir=unsaved_root, save_run_history=False))
        from ..core.run_history import saved_run_ids
        check("save_run_history_false_creates_no_saved_run_authority",
              not unsaved.solved and unsaved.run_history["path"] == ""
              and saved_run_ids(unsaved_root) == [])
        autonomous = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(
                text="Train and compare several supervised prediction models.")),
            runs_dir=root,
            interaction_mode=InteractionMode.AUTONOMOUS))
        stale = {"solved": True, "orientations": [{
            "blocking_questions": ["Which metric should the report lead with?"],
            "ambiguities": [{"subject": "lead metric",
                             "state": "USER_CLARIFICATION_REQUIRED",
                             "reason": "presentation only"}]}]}
        blocking, open_items = _terminal_questions(stale, True)
        still_blocking, _ = _terminal_questions(dict(stale, solved=False), False)
        region_evidence = asked.intelligence.get("region_evidence") or {}
        tuning = region_evidence.get("tuning_decision") or {}
        check("solve_records_region_evidence_and_a_tuned_context_budget_decision",
              region_evidence.get("advisory") is True
              and str(region_evidence.get("region_ref", "")).startswith(
                  "region.")
              and tuning.get("setting") == "context_budget"
              and bool(tuning.get("chosen_variant_key"))
              and asked_bundle.outcome["intelligence"]["region_evidence"]
              ["tuning_decision"]["setting"] == "context_budget",
              str(tuning.get("reason", ""))[:100])
        check("solved_run_reports_stale_questions_as_open_not_as_a_refusal",
              blocking == () and len(open_items) == 1
              and open_items[0].answer_slot == "lead_metric"
              and len(still_blocking) == 1
              and SolveOutcome(
                  run_id="r", status="COMPLETED_VERIFIED", solved=True,
                  failure_code="", result={"open_questions": [
                      open_items[0].to_dict()]},
                  compiled_task={}, intelligence={}, selected_mode="model_led",
                  selected_canvas={}, graph_digest="",
                  verification={"passed": True}).status
              == "COMPLETED_VERIFIED",
              f"open={len(open_items)} blocking={len(blocking)}")
        check("autonomous_interaction_terminates_without_a_question",
              not autonomous.solved
              and autonomous.failure_code == "CAPABILITY_GAP"
              and autonomous.compiled_task["binding"] is None
              and autonomous.compiled_task["template_selection_authority"]
                  == "model_only"
              and autonomous.compiled_task["template_candidates"])
    from .solve_mode_checks import mode_checks
    return {"tests": [*results, *mode_checks()]}
