"""Template model: typed task templates and binding modes.

A template standardizes freeform text into typed variables. The
binding is open-set: exact, composite, partial, ambiguous, open, or
new-template-candidate. The original input is never replaced.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

#: Binding modes a compiler may return.
BINDING_MODES = (
    "exact", "composite", "partial", "ambiguous", "open",
    "new_template_candidate",
)

#: Task types a template may declare.
TASK_TYPES = (
    "classification", "regression", "ranking", "prediction",
    "optimization", "recommendation", "monitoring", "transformation",
    "validation", "generation", "retrieval", "comparison", "migration",
    "audit", "unknown",
)

#: Output kinds a template may request.
OUTPUT_KINDS = (
    "label", "probability", "score", "ranked_list", "report", "artifact",
    "code", "config", "graph", "service", "decision", "unknown",
)


class TemplateError(ValueError):
    """A template or binding violated its contract."""


@dataclass(frozen=True)
class TaskTemplate:
    """One versioned task template with a JSON variable schema."""

    template_id: str
    version: str
    name: str
    description: str = ""
    task_type: str = "unknown"
    output_kind: str = "unknown"
    variables: dict = field(default_factory=dict)
    required_variables: tuple[str, ...] = ()
    optional_variables: tuple[str, ...] = ()
    file_refs: tuple[str, ...] = ()
    input_contract: str = ""
    output_contract: str = ""
    maturity: str = "registered"

    def __post_init__(self) -> None:
        if self.task_type not in TASK_TYPES:
            raise TemplateError(f"task_type must be one of {TASK_TYPES}")
        if self.output_kind not in OUTPUT_KINDS:
            raise TemplateError(f"output_kind must be one of {OUTPUT_KINDS}")
        if self.maturity not in ("registered", "candidate", "deprecated"):
            raise TemplateError(
                "maturity must be registered, candidate, or deprecated")
        for name in self.required_variables:
            if name not in self.variables:
                raise TemplateError(
                    f"required variable {name!r} missing from variables")

    def content_digest(self) -> str:
        serialized = json.dumps({
            "template_id": self.template_id, "version": self.version,
            "name": self.name, "task_type": self.task_type,
            "output_kind": self.output_kind, "variables": self.variables,
            "required_variables": list(self.required_variables),
            "optional_variables": list(self.optional_variables),
            "file_refs": list(self.file_refs),
        }, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id, "version": self.version,
            "name": self.name, "description": self.description,
            "task_type": self.task_type, "output_kind": self.output_kind,
            "variables": dict(self.variables),
            "required_variables": list(self.required_variables),
            "optional_variables": list(self.optional_variables),
            "file_refs": list(self.file_refs),
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "maturity": self.maturity,
        }


@dataclass(frozen=True)
class TemplateBinding:
    """One binding decision: which template, which mode, what remains."""

    template_id: str
    template_version: str
    binding_mode: str
    confidence: float = 1.0
    mapped_variables: dict = field(default_factory=dict)
    unmapped_requirements: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    rejected_bindings: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.binding_mode not in BINDING_MODES:
            raise TemplateError(
                f"binding_mode must be one of {BINDING_MODES}")
        if not 0.0 <= self.confidence <= 1.0:
            raise TemplateError("confidence must be in [0, 1]")

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "template_version": self.template_version,
            "binding_mode": self.binding_mode,
            "confidence": self.confidence,
            "mapped_variables": dict(self.mapped_variables),
            "unmapped_requirements": list(self.unmapped_requirements),
            "assumptions": list(self.assumptions),
            "ambiguities": list(self.ambiguities),
            "rejected_bindings": list(self.rejected_bindings),
            "rejection_reasons": list(self.rejection_reasons),
        }


@dataclass(frozen=True)
class CompiledTask:
    """The typed result of task compilation.

    The original input is preserved verbatim alongside the normalized
    interpretation so later review can detect task drift.
    """

    compiled_task_id: str
    original_input: str
    normalized_interpretation: str
    task_type: str = "unknown"
    output_kind: str = "unknown"
    binding: TemplateBinding | None = None
    variables: dict = field(default_factory=dict)
    file_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    provenance: str = ""

    def __post_init__(self) -> None:
        if self.task_type not in TASK_TYPES:
            raise TemplateError(f"task_type must be one of {TASK_TYPES}")
        if self.output_kind not in OUTPUT_KINDS:
            raise TemplateError(f"output_kind must be one of {OUTPUT_KINDS}")

    def to_dict(self) -> dict:
        return {
            "compiled_task_id": self.compiled_task_id,
            "original_input": self.original_input,
            "normalized_interpretation": self.normalized_interpretation,
            "task_type": self.task_type,
            "output_kind": self.output_kind,
            "binding": self.binding.to_dict() if self.binding else None,
            "variables": dict(self.variables),
            "file_refs": list(self.file_refs),
            "source_refs": list(self.source_refs),
            "provenance": self.provenance,
        }


def self_test() -> dict:
    """Prove templates validate and bindings are typed."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    template = TaskTemplate(
        template_id="core.task.tabular_classification",
        version="1.0.0",
        name="Tabular classification",
        task_type="classification",
        output_kind="label",
        variables={"target_column": "string", "file_path": "string",
                   "metric": "string"},
        required_variables=("target_column", "file_path"),
        optional_variables=("metric",),
        file_refs=("data.csv",))
    check("template_validates_required_variables",
          template.content_digest() == template.content_digest()
          and template.required_variables == ("target_column", "file_path"))
    try:
        TaskTemplate(template_id="bad", version="1.0.0", name="bad",
                     task_type="classification", output_kind="label",
                     variables={}, required_variables=("missing",))
        check("missing_required_variable_is_refused", False)
    except TemplateError:
        check("missing_required_variable_is_refused", True)
    try:
        TaskTemplate(template_id="bad", version="1.0.0", name="bad",
                     task_type="bogus", output_kind="label")
        check("unknown_task_type_is_refused", False)
    except TemplateError:
        check("unknown_task_type_is_refused", True)

    binding = TemplateBinding(
        template_id="core.task.tabular_classification",
        template_version="1.0.0",
        binding_mode="partial",
        mapped_variables={"target_column": "churn"},
        unmapped_requirements=("file_path",))
    check("partial_binding_records_unmapped_requirements",
          binding.binding_mode == "partial"
          and binding.unmapped_requirements == ("file_path",))
    try:
        TemplateBinding(template_id="x", template_version="1.0.0",
                        binding_mode="bogus")
        check("unknown_binding_mode_is_refused", False)
    except TemplateError:
        check("unknown_binding_mode_is_refused", True)

    compiled = CompiledTask(
        compiled_task_id="task:1",
        original_input="predict churn from customers.csv",
        normalized_interpretation="predict churn from customers.csv",
        task_type="classification", output_kind="label",
        binding=binding)
    check("compiled_task_preserves_original_input",
          compiled.original_input == "predict churn from customers.csv"
          and compiled.to_dict()["binding"]["binding_mode"] == "partial")
    return {"tests": results}
