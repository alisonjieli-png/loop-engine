"""Task compiler: freeform text to typed CompiledTask through a Loop.

The compiler preserves the original input verbatim, discovers
candidate templates, binds exact/composite/partial/open, and records
unmapped requirements. Compilation is a governed Loop operation on the
canonical engine.
"""
from __future__ import annotations

from .library import TemplateLibrary
from .model import (BINDING_MODES, CompiledTask, TaskTemplate,
                    TemplateBinding, TemplateError)


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


def compile_task(text: str, *, library: TemplateLibrary | None = None,
                 task_id: str = "") -> dict:
    """Compile freeform text into a typed task through a canonical Loop.

    Returns the CompiledTask dict plus the Loop identity that governed
    the compilation.
    """
    from loop_engine.loop.encapsulate import as_practitioner_loop

    def _compile(_inputs=None) -> dict:
        lib = library or TemplateLibrary()
        candidates = lib.search(text)
        if not candidates:
            compiled = CompiledTask(
                compiled_task_id=task_id or "task:open",
                original_input=text,
                normalized_interpretation=text,
                task_type="unknown", output_kind="unknown",
                binding=TemplateBinding(
                    template_id="", template_version="",
                    binding_mode="open",
                    unmapped_requirements=("no template matched",)))
            return compiled.to_dict()
        best = candidates[0]
        score = _score_template(best, text)
        variables = _extract_variables(best, text)
        mapped = {k: v for k, v in variables.items() if v}
        unmapped = tuple(v for v in best.required_variables
                         if v not in mapped)
        if score >= 0.5 and not unmapped:
            mode = "exact"
        elif score >= 0.3:
            mode = "partial"
        else:
            mode = "ambiguous"
        binding = TemplateBinding(
            template_id=best.template_id,
            template_version=best.version,
            binding_mode=mode,
            confidence=round(score, 3),
            mapped_variables=mapped,
            unmapped_requirements=unmapped,
            rejected_bindings=tuple(
                t.template_id for t in candidates[1:3]))
        compiled = CompiledTask(
            compiled_task_id=task_id or f"task:{best.template_id}",
            original_input=text,
            normalized_interpretation=text,
            task_type=best.task_type,
            output_kind=best.output_kind,
            binding=binding,
            variables=mapped)
        return compiled.to_dict()

    result = as_practitioner_loop("compile and bind task", _compile)
    return {"loop_id": result["loop_id"],
            "compiled_task": result["value"]}


def self_test() -> dict:
    """Prove compilation preserves input and binds templates honestly."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    result = compile_task(
        "predict churn from customers.csv target_column=churn")
    compiled = result["compiled_task"]
    check("compilation_runs_through_canonical_loop",
          result["loop_id"].startswith("loop"))
    check("original_input_is_preserved",
          compiled["original_input"]
          == "predict churn from customers.csv target_column=churn")
    check("template_is_bound",
          compiled["binding"]["template_id"]
          == "core.task.tabular_classification"
          and compiled["binding"]["binding_mode"] in BINDING_MODES)
    check("variables_are_extracted",
          compiled["variables"].get("target_column") == "churn")

    open_result = compile_task("do something completely novel")
    check("open_task_falls_back_honestly",
          open_result["compiled_task"]["binding"]["binding_mode"] == "open")

    partial = compile_task("predict something from data.csv")
    check("partial_binding_records_unmapped_requirements",
          partial["compiled_task"]["binding"]["binding_mode"]
          in ("partial", "ambiguous")
          and "target_column" in partial["compiled_task"]["binding"]
          ["unmapped_requirements"])
    return {"tests": results}
