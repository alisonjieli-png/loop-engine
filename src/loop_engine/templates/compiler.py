"""Task compiler: freeform text to typed CompiledTask through a Loop.

The compiler preserves the original input verbatim, discovers
candidate templates, binds exact/composite/partial/open, and records
unmapped requirements. Compilation is a governed Loop operation on the
canonical engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .library import TemplateLibrary
from .model import (
    BINDING_MODES,
    CompiledTask,
    InteractionMode,
    RequirementDisposition,
    RequirementDispositionState,
    SemanticCoordinates,
    TaskTemplate,
    TaskFeedback,
    TemplateBinding,
    TemplateError,
    WorkItemIR,
)


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

_OPERATOR_TASK_TYPES = {
    "classify": ("classification",),
    "predict": ("prediction", "classification", "regression"),
    "forecast": ("prediction",),
    "rank": ("ranking",),
    "optimize": ("optimization",),
    "recommend": ("recommendation",),
    "monitor": ("monitoring",),
    "transform": ("transformation",),
    "validate": ("validation",),
    "generate": ("generation",),
    "retrieve": ("retrieval",),
    "search": ("retrieval",),
    "browse": ("retrieval",),
}


@dataclass(frozen=True)
class TaskCompileRequest:
    """Passive, cohesive input for one task-compilation operation."""

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
                raise TemplateError("interaction_mode is not recognized") from exc
            object.__setattr__(self, "interaction_mode", mode)
        feedback = tuple(self.feedback)
        if any(not isinstance(item, TaskFeedback) for item in feedback):
            raise TemplateError("feedback must contain TaskFeedback values")
        slots = tuple(item.slot_ref for item in feedback)
        if len(slots) != len(set(slots)):
            raise TemplateError("task feedback slots cannot repeat")
        object.__setattr__(self, "feedback", feedback)


def _operator_from_text(text: str) -> str:
    import re
    low = text.lower()
    patterns = (
        ("classify", r"\b(classify|classification|label)\b"),
        ("predict", r"\b(predict|prediction|regression)\b"),
        ("forecast", r"\b(forecast)\b"),
        ("validate", r"\b(validate|validation|verify|check schema)\b"),
        ("extract", r"\b(extract|parse)\b"),
        ("rank", r"\b(rank|ranking|prioritize)\b"),
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


def _feedback_variables(
        template: TaskTemplate,
        feedback: tuple[TaskFeedback, ...]) -> dict:
    policies = {
        policy.feedback_slot_ref: policy
        for policy in template.requirement_policies
        if policy.feedback_slot_ref
    }
    variables: dict = {}
    for item in feedback:
        policy = policies.get(item.slot_ref)
        if policy is None:
            raise TemplateError(
                f"feedback slot {item.slot_ref!r} is not registered for "
                f"{template.template_id}")
        if template.variables.get(policy.requirement_id) != "string":
            raise TemplateError(
                "this compiler accepts feedback only for string requirements")
        variables[policy.requirement_id] = item.value
    return variables


def _requirement_dispositions(
        template: TaskTemplate,
        request: TaskCompileRequest,
        mapped: dict) -> tuple[RequirementDisposition, ...]:
    """Resolve provided, delegated, and clarification-required values."""
    policies = {
        policy.requirement_id: policy
        for policy in template.requirement_policies
    }
    dispositions: list[RequirementDisposition] = []
    for requirement_id in template.required_variables:
        provided = requirement_id in mapped
        policy = policies.get(requirement_id)
        if policy is not None:
            dispositions.append(policy.resolve(
                request.text, provided, request.interaction_mode))
            continue
        state = (
            RequirementDispositionState.PROVIDED if provided else
            RequirementDispositionState.ABSTAIN_REQUIRED
            if request.interaction_mode == InteractionMode.AUTONOMOUS else
            RequirementDispositionState.NEEDS_CLARIFICATION)
        dispositions.append(RequirementDisposition(
            requirement_id=requirement_id,
            state=state,
            reason_code=("explicit_value" if provided
                         else "autonomous_run_cannot_resolve_safely"
                         if request.interaction_mode == InteractionMode.AUTONOMOUS
                         else "required_value_missing")))
    return tuple(dispositions)


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
    expected_task_types = _OPERATOR_TASK_TYPES.get(explicit_operator)
    if expected_task_types:
        compatible = [candidate for candidate in candidates
                      if candidate.task_type in expected_task_types]
        if not compatible:
            compatible = [candidate for candidate in
                          (lib.get(template_id) for template_id in lib.ids())
                          if candidate is not None
                          and candidate.task_type in expected_task_types]
        if compatible:
            candidates = compatible
    if not candidates:
        if request.feedback:
            raise TemplateError(
                "task feedback cannot bind without a registered template")
        open_state = (
            RequirementDispositionState.ABSTAIN_REQUIRED
            if request.interaction_mode == InteractionMode.AUTONOMOUS
            else RequirementDispositionState.NEEDS_CLARIFICATION)
        binding = TemplateBinding(
            template_id="", template_version="", binding_mode="open",
            unmapped_requirements=("template_match",),
            requirement_dispositions=(RequirementDisposition(
                "template_match", open_state,
                ("autonomous_run_cannot_resolve_safely"
                 if open_state == RequirementDispositionState.ABSTAIN_REQUIRED
                 else "no_template_matched")),))
        task_type, output_kind = "unknown", "unknown"
        compiled_id = request.task_id or "task:open"
        mapped = {}
    else:
        best = candidates[0]
        score = _score_template(best, text)
        variables = _extract_variables(best, text)
        feedback_variables = _feedback_variables(best, request.feedback)
        conflicts = [
            name for name, value in feedback_variables.items()
            if name in variables and variables[name] != value
        ]
        if conflicts:
            raise TemplateError(
                f"structured feedback conflicts with task text: {conflicts!r}")
        variables.update(feedback_variables)
        mapped = {key: value for key, value in variables.items() if value}
        unmapped = tuple(value for value in best.required_variables
                         if value not in mapped)
        dispositions = _requirement_dispositions(best, request, mapped)
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
            requirement_dispositions=dispositions,
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
        requirement_dispositions=tuple(binding.requirement_dispositions),
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
            "model_calls": result["model_calls"],
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
          result["loop_id"].startswith("loop")
          and result["model_calls"] == 0)
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
          open_result["compiled_task"]["binding"]["binding_mode"] == "open"
          and open_result["compiled_task"]["binding"]
              ["requires_clarification"])
    autonomous_open = compile_task(TaskCompileRequest(
        "do something completely novel",
        interaction_mode=InteractionMode.AUTONOMOUS))
    check("autonomous_open_task_abstains_instead_of_waiting",
          autonomous_open["compiled_task"]["binding"]["requires_abstention"]
          and not autonomous_open["compiled_task"]["binding"]
              ["requires_clarification"])

    partial = compile_task(TaskCompileRequest(
        "predict something from data.csv"))
    check("partial_binding_records_unmapped_requirements",
          partial["compiled_task"]["binding"]["binding_mode"]
          in ("partial", "ambiguous")
          and "target_column" in partial["compiled_task"]["binding"]
          ["unmapped_requirements"]
          and partial["compiled_task"]["binding"]
          ["requires_clarification"])
    flagship = compile_task(TaskCompileRequest(
        "Download an authorized public dataset. Train a linear model, tree "
        "model, boosted-tree model, and MLP on identical validation folds to "
        "predict the target variable. Compare them honestly and produce "
        "verified PDF and HTML reports."))
    flagship_task = flagship["compiled_task"]
    check("prediction_goal_precedes_downstream_verification_wording",
          flagship_task["work_item"]["coordinates"]["operator"] == "predict")
    check("flagship_binds_model_comparison_template",
          flagship_task["binding"]["template_id"]
          == "core.task.tabular_model_comparison"
          and flagship_task["task_type"] == "prediction"
          and flagship_task["output_kind"] == "report"
          and flagship_task["work_item"]["coordinates"]["response_topology"]
          == "artifact")
    flagship_binding = flagship_task["binding"]
    dispositions = {
        item["requirement_id"]: item
        for item in flagship_binding["requirement_dispositions"]
    }
    check("flagship_delegates_low_risk_dataset_and_target_choices",
          not flagship_binding["requires_clarification"]
          and flagship_binding["delegated_requirements"]
              == ["dataset_source", "target_column"]
          and dispositions["dataset_source"]["state"]
              == "delegated_choice"
          and dispositions["target_column"]["depends_on"]
              == ["dataset_source"])
    autonomous = compile_task(TaskCompileRequest(
        "Train and compare several supervised prediction models.",
        interaction_mode=InteractionMode.AUTONOMOUS))
    autonomous_binding = autonomous["compiled_task"]["binding"]
    check("autonomous_mode_uses_policy_without_waiting_for_feedback",
          autonomous_binding["can_continue_without_user_input"]
          and autonomous_binding["delegated_requirements"]
              == ["dataset_source", "target_column"])
    feedback = compile_task(TaskCompileRequest(
        "Train and compare several supervised prediction models.",
        interaction_mode=InteractionMode.AUTONOMOUS,
        feedback=(TaskFeedback(
            "task.preference.dataset_source", "openml:61"),)))
    check("optional_feedback_slot_binds_without_becoming_required",
          feedback["compiled_task"]["variables"]["dataset_source"]
              == "openml:61"
          and feedback["compiled_task"]["binding"]["delegated_requirements"]
              == ["target_column"])
    no_safe_policy = compile_task(TaskCompileRequest(
        "predict class label from tabular data",
        interaction_mode=InteractionMode.AUTONOMOUS))
    check("autonomous_mode_abstains_instead_of_asking_or_inventing",
          no_safe_policy["compiled_task"]["binding"]["requires_abstention"]
          and not no_safe_policy["compiled_task"]["binding"]
              ["requires_clarification"])
    return {"tests": results}
