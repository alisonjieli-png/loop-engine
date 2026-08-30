"""Standardize freeform text as an open typed task through a Loop.

The compiler preserves the original input and exposes matching templates as
advisory candidates. It never chooses one, infers task semantics, or executes
the task. A later model-led Practitioner decision may use, adapt, combine, or
ignore any candidate.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .library import TemplateLibrary
from .model import (
    CompiledTask, InteractionMode, SemanticCoordinates, TaskFeedback,
    TaskTemplate, TemplateError, WorkItemIR)


@dataclass(frozen=True)
class TaskCompileRequest:
    """Passive input for open task standardization."""

    text: str
    library: TemplateLibrary | None = None
    task_id: str = ""
    source_kind: str = "text"
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    interaction_mode: InteractionMode = InteractionMode.ASK_WHEN_MATERIAL
    feedback: tuple[TaskFeedback, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        mode = self.interaction_mode
        if not isinstance(mode, InteractionMode):
            try:
                mode = InteractionMode(mode)
            except (TypeError, ValueError) as exc:
                raise TemplateError(
                    "interaction_mode is not recognized") from exc
            object.__setattr__(self, "interaction_mode", mode)
        feedback = tuple(self.feedback)
        if any(not isinstance(item, TaskFeedback) for item in feedback):
            raise TemplateError("feedback must contain TaskFeedback values")
        slots = tuple(item.slot_ref for item in feedback)
        if len(slots) != len(set(slots)):
            raise TemplateError("task feedback slots cannot repeat")
        object.__setattr__(self, "feedback", feedback)


def _score_template(template: TaskTemplate, text: str) -> float:
    """Return a lexical search score with no selection authority."""
    terms = set(text.lower().split())
    haystack = set(" ".join((
        template.name, template.description, template.task_type,
        template.output_kind)).lower().split())
    return len(terms & haystack) / len(terms) if terms else 0.0


def compile_task_value(request: TaskCompileRequest) -> dict:
    """Preserve one open task and expose optional template candidates."""
    if not isinstance(request, TaskCompileRequest):
        raise TemplateError("compile_task_value needs TaskCompileRequest")
    text = request.text
    if not isinstance(text, str) or not text.strip():
        raise TemplateError("task compilation needs non-empty text")
    normalized = " ".join(text.split())
    candidates = (request.library or TemplateLibrary()).search(text)
    template_candidates = [{
        "template_id": candidate.template_id,
        "template_version": candidate.version,
        "task_type": candidate.task_type,
        "output_kind": candidate.output_kind,
        "lexical_score": round(_score_template(candidate, text), 3),
        "advisory_only": True,
    } for candidate in candidates]
    compiled_id = request.task_id or (
        "task:open:" + hashlib.sha256(
            text.encode("utf-8")).hexdigest()[:20])
    coordinates = SemanticCoordinates(
        question=normalized, operator="unknown", response_topology="unknown",
        decision_consumer="verify_then_return_or_stage_learning")
    work_item = WorkItemIR(
        work_item_id=compiled_id, source_kind=request.source_kind,
        original_input=text, normalized_interpretation=normalized,
        coordinates=coordinates, source_refs=tuple(request.source_refs),
        acceptance_criteria=("output contract validates",
                             "independent verification passes"),
        unknowns=(), requirement_dispositions=(),
        tags=("task:open", "response:unknown"),
        provenance="LLM-first open task compiler")
    value = CompiledTask(
        compiled_task_id=compiled_id, original_input=text,
        normalized_interpretation=normalized, task_type="unknown",
        output_kind="unknown", binding=None,
        variables={item.slot_ref: item.value for item in request.feedback},
        source_refs=tuple(request.source_refs),
        provenance="LLM-first open task compiler",
        work_item=work_item).to_dict()
    value["template_selection_authority"] = "model_only"
    value["template_candidates"] = template_candidates
    value["task_feedback"] = [item.to_dict() for item in request.feedback]
    return value


def compile_task(request: TaskCompileRequest) -> dict:
    """Standardize one intake through a canonical Practitioner Loop."""
    from loop_engine.loop.encapsulate import as_practitioner_loop

    result = as_practitioner_loop(
        "standardize an open task", lambda: compile_task_value(request))
    return {"loop_id": result["loop_id"],
            "model_calls": result["model_calls"],
            "compiled_task": result["value"]}


def self_test() -> dict:
    """Prove standardization never selects task semantics or a template."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": detail})

    task = "predict churn from customers.csv target_column=churn"
    result = compile_task(TaskCompileRequest(task))
    compiled = result["compiled_task"]
    check("standardization_runs_through_one_practitioner_loop",
          result["loop_id"].startswith("loop") and result["model_calls"] == 0)
    check("original_task_is_preserved",
          compiled["original_input"] == task)
    check("task_semantics_remain_open_for_model_orientation",
          compiled["task_type"] == "unknown"
          and compiled["output_kind"] == "unknown"
          and compiled["work_item"]["coordinates"]["operator"] == "unknown")
    check("templates_are_advisory_and_never_bound",
          compiled["binding"] is None
          and compiled["template_selection_authority"] == "model_only"
          and compiled["template_candidates"]
          and all(item["advisory_only"]
                  for item in compiled["template_candidates"]))
    feedback = TaskFeedback(
        "required_destination", "./results/final.md")
    answered = compile_task(TaskCompileRequest(task, feedback=(feedback,)))[
        "compiled_task"]
    check("feedback_stays_separate_without_selecting_a_template",
          answered["binding"] is None
          and answered["variables"] == {
              "required_destination": "./results/final.md"}
          and answered["task_feedback"] == [feedback.to_dict()])
    unattended = compile_task(TaskCompileRequest(
        "Do an unfamiliar task.",
        interaction_mode=InteractionMode.AUTONOMOUS))["compiled_task"]
    check("interaction_policy_cannot_select_task_semantics",
          unattended["binding"] is None
          and unattended["task_type"] == "unknown")
    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
