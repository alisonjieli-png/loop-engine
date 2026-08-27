"""Task compiler: freeform text to typed CompiledTask through a Loop.

The compiler preserves the original input verbatim, discovers
candidate templates, binds exact/composite/partial/open, and records
unmapped requirements. Compilation is a governed Loop operation on the
canonical engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .library import TemplateLibrary
from .model import (BINDING_MODES, CompiledTask, SemanticCoordinates,
                    TaskTemplate, TemplateBinding, TemplateError, WorkItemIR)


_TASK_OPERATOR = {
    "classification": "classify", "regression": "predict",
    "ranking": "rank", "prediction": "predict",
    "optimization": "optimize", "recommendation": "recommend",
    "monitoring": "monitor", "transformation": "transform",
    "validation": "validate", "generation": "generate",
    "retrieval": "retrieve", "comparison": "score",
    "migration": "transform", "audit": "validate", "unknown": "unknown",
}

_OUTPUT_RESPONSE = {
    "label": "label", "probability": "probability", "score": "score",
    "ranked_list": "ranked_list", "report": "artifact",
    "artifact": "artifact", "code": "artifact", "config": "policy",
    "graph": "graph", "service": "artifact", "decision": "action",
    "unknown": "unknown",
}

_OPERATOR_TASK = {
    "classify": "classification", "rank": "ranking",
    "optimize": "optimization", "recommend": "recommendation",
    "monitor": "monitoring", "transform": "transformation",
    "validate": "validation", "generate": "generation",
    "retrieve": "retrieval", "search": "retrieval", "browse": "retrieval",
}


@dataclass(frozen=True)
class TaskCompileRequest:
    """Passive, cohesive input for one task-compilation operation."""

    text: str
    library: TemplateLibrary | None = None
    task_id: str = ""
    source_kind: str = "text"
    source_refs: tuple[str, ...] = field(default_factory=tuple)


def _operator_from_text(text: str) -> str:
    import re
    low = text.lower()
    patterns = (
        ("classify", r"\b(classify|classification|label)\b"),
        ("validate", r"\b(validate|validation|verify|check schema)\b"),
        ("extract", r"\b(extract|parse)\b"),
        ("rank", r"\b(rank|ranking|prioritize)\b"),
        ("predict", r"\b(predict|prediction|regression)\b"),
        ("forecast", r"\b(forecast)\b"),
        ("summarize", r"\b(summarize|summarise|summary)\b"),
        ("search", r"\b(search|find sources)\b"),
        ("browse", r"\b(browse|website|url)\b"),
        ("optimize", r"\b(optimize|optimise)\b"),
        ("generate", r"\b(generate|create|write|build)\b"),
        ("transform", r"\b(transform|normalize|standardize|clean|migrate)\b"),
    )
    for operator, pattern in patterns:
        if re.search(pattern, low):
            return operator
    return "unknown"


def _score_template(template: TaskTemplate, text: str) -> float:
    """Deterministic lexical compatibility score."""
    terms = set(text.lower().split())
    haystack = " ".join((
        template.name, template.description, template.task_type,
        template.output_kind)).lower().split()
    if not terms:
        return 0.0
    return len(terms & set(haystack)) / len(terms)


def _extract_variables(template: TaskTemplate, text: str) -> dict:
    """Deterministically extract declared variables from freeform text.

    The deterministic baseline extracts file paths and simple
    key=value pairs. A model-backed compiler can do richer extraction;
    the baseline never invents values.
    """
    import re
    variables: dict = {}
    for name, kind in template.variables.items():
        if kind == "string":
            match = re.search(rf"{name}\s*=\s*([^\s,]+)", text,
                              re.IGNORECASE)
            if match:
                variables[name] = match.group(1)
        elif kind == "boolean":
            if re.search(rf"{name}\s*=\s*(true|yes)", text,
                         re.IGNORECASE):
                variables[name] = True
            elif re.search(rf"{name}\s*=\s*(false|no)", text,
                           re.IGNORECASE):
                variables[name] = False
        elif kind == "list":
            match = re.search(rf"{name}\s*=\s*\[([^\]]+)\]", text,
                              re.IGNORECASE)
            if match:
                variables[name] = [item.strip()
                                   for item in match.group(1).split(",")]
    return variables


def compile_task_value(request: TaskCompileRequest) -> dict:
    """Pure compiler body, intended to run inside an owning Practitioner Loop."""
    if not isinstance(request, TaskCompileRequest):
        raise TemplateError("compile_task_value needs TaskCompileRequest")
    text = request.text
    if not isinstance(text, str) or not text.strip():
        raise TemplateError("task compilation needs non-empty text")
    lib = request.library or TemplateLibrary()
    candidates = lib.search(text)
    normalized = " ".join(text.split())
    explicit_operator = _operator_from_text(normalized)
    expected_task = _OPERATOR_TASK.get(explicit_operator)
    if expected_task:
        compatible = [candidate for candidate in candidates
                      if candidate.task_type == expected_task]
        if not compatible:
            compatible = [candidate for candidate in
                          (lib.get(template_id) for template_id in lib.ids())
                          if candidate is not None
                          and candidate.task_type == expected_task]
        if compatible:
            candidates = compatible
    if not candidates:
        binding = TemplateBinding(
            template_id="", template_version="", binding_mode="open",
            unmapped_requirements=("no template matched",))
        task_type, output_kind = "unknown", "unknown"
        compiled_id = request.task_id or "task:open"
        mapped = {}
    else:
        best = candidates[0]
        score = _score_template(best, text)
        variables = _extract_variables(best, text)
        mapped = {key: value for key, value in variables.items() if value}
        unmapped = tuple(value for value in best.required_variables
                         if value not in mapped)
        if score >= 0.5 and not unmapped:
            mode = "exact"
        elif score >= 0.3:
            mode = "partial"
        else:
            mode = "ambiguous"
        binding = TemplateBinding(
            template_id=best.template_id, template_version=best.version,
            binding_mode=mode, confidence=round(score, 3),
            mapped_variables=mapped, unmapped_requirements=unmapped,
            rejected_bindings=tuple(
                candidate.template_id for candidate in candidates[1:3]))
        task_type, output_kind = best.task_type, best.output_kind
        compiled_id = request.task_id or f"task:{best.template_id}"
    operator = (explicit_operator if explicit_operator != "unknown"
                else _TASK_OPERATOR[task_type])
    response = _OUTPUT_RESPONSE[output_kind]
    if operator == "classify":
        response = "label"
    elif operator in ("extract", "summarize") and response == "unknown":
        response = "artifact"
    coordinates = SemanticCoordinates(
        question=normalized,
        operator=operator,
        response_topology=response,
        decision_consumer="verify_then_return_or_stage_learning")
    work_item = WorkItemIR(
        work_item_id=compiled_id, source_kind=request.source_kind,
        original_input=text, normalized_interpretation=normalized,
        coordinates=coordinates, source_refs=tuple(request.source_refs),
        acceptance_criteria=("output contract validates",
                             "independent verification passes"),
        unknowns=tuple(binding.unmapped_requirements),
        tags=(f"task:{task_type}", f"response:{output_kind}"),
        provenance="deterministic task compiler")
    return CompiledTask(
        compiled_task_id=compiled_id, original_input=text,
        normalized_interpretation=normalized, task_type=task_type,
        output_kind=output_kind, binding=binding, variables=mapped,
        source_refs=tuple(request.source_refs),
        provenance="deterministic task compiler", work_item=work_item).to_dict()


def compile_task(request: TaskCompileRequest) -> dict:
    """Compile one intake through a canonical Practitioner Loop."""
    from loop_engine.loop.encapsulate import as_practitioner_loop

    result = as_practitioner_loop(
        "compile and bind task",
        lambda: compile_task_value(request))
    return {"loop_id": result["loop_id"],
            "compiled_task": result["value"]}


def self_test() -> dict:
    """Prove compilation preserves input and binds templates honestly."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    result = compile_task(TaskCompileRequest(
        "predict churn from customers.csv target_column=churn"))
    compiled = result["compiled_task"]
    check("compilation_runs_through_canonical_loop",
          result["loop_id"].startswith("loop"))
    check("original_input_is_preserved",
          compiled["original_input"]
          == "predict churn from customers.csv target_column=churn")
    check("question_operator_response_decision_are_explicit",
          compiled["work_item"]["coordinates"]["operator"] == "predict"
          and compiled["work_item"]["coordinates"]["response_topology"]
              == "label"
          and compiled["work_item"]["coordinates"]["decision_consumer"])
    check("template_is_bound",
          compiled["binding"]["template_id"]
          == "core.task.tabular_classification"
          and compiled["binding"]["binding_mode"] in BINDING_MODES)
    check("variables_are_extracted",
          compiled["variables"].get("target_column") == "churn")

    open_result = compile_task(TaskCompileRequest(
        "do something completely novel"))
    check("open_task_falls_back_honestly",
          open_result["compiled_task"]["binding"]["binding_mode"] == "open")

    partial = compile_task(TaskCompileRequest(
        "predict something from data.csv"))
    check("partial_binding_records_unmapped_requirements",
          partial["compiled_task"]["binding"]["binding_mode"]
          in ("partial", "ambiguous")
          and "target_column" in partial["compiled_task"]["binding"]
          ["unmapped_requirements"])
    return {"tests": results}
