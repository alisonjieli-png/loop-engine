"""Template library: registered task templates with discovery.

Templates are Code Intelligence records. The library registers Core
templates and discovers Learned and Plugin templates through the same
catalog. A template is data; binding is a governed Loop operation.
"""
from __future__ import annotations

from .model import TaskTemplate, TemplateError

#: Core task templates shipped with the package.
CORE_TEMPLATES = (
    TaskTemplate(
        template_id="core.task.tabular_classification",
        version="1.0.0",
        name="Tabular classification",
        description="Predict a class label from tabular features.",
        task_type="classification",
        output_kind="label",
        variables={"target_column": "string", "file_path": "string",
                   "metric": "string", "id_column": "string"},
        required_variables=("target_column", "file_path"),
        optional_variables=("metric", "id_column"),
        file_refs=("data.csv",),
        input_contract="tabular_dataset",
        output_contract="prediction_labels"),
    TaskTemplate(
        template_id="core.task.tabular_regression",
        version="1.0.0",
        name="Tabular regression",
        description="Predict a continuous value from tabular features.",
        task_type="regression",
        output_kind="score",
        variables={"target_column": "string", "file_path": "string",
                   "metric": "string"},
        required_variables=("target_column", "file_path"),
        optional_variables=("metric",),
        file_refs=("data.csv",),
        input_contract="tabular_dataset",
        output_contract="prediction_scores"),
    TaskTemplate(
        template_id="core.task.tabular_model_comparison",
        version="1.0.0",
        name="Tabular model comparison",
        description=(
            "Train and compare several supervised prediction models on "
            "shared validation folds and produce a verified report."),
        task_type="prediction",
        output_kind="report",
        variables={
            "dataset_source": "string",
            "target_column": "string",
            "model_families": "list",
            "validation_strategy": "string",
            "report_formats": "list",
        },
        required_variables=("dataset_source", "target_column"),
        optional_variables=(
            "model_families", "validation_strategy", "report_formats"),
        file_refs=(),
        input_contract="authorized_tabular_dataset",
        output_contract="verified_model_comparison_report"),
    TaskTemplate(
        template_id="core.task.data_standardization",
        version="1.0.0",
        name="Data standardization",
        description="Profile, clean, and standardize a messy dataset.",
        task_type="transformation",
        output_kind="artifact",
        variables={"file_path": "string", "target_vocabulary": "string",
                   "output_format": "string"},
        required_variables=("file_path",),
        optional_variables=("target_vocabulary", "output_format"),
        file_refs=("data.csv",),
        input_contract="messy_dataset",
        output_contract="standardized_dataset"),
    TaskTemplate(
        template_id="core.task.source_digestion",
        version="1.0.0",
        name="Source digestion",
        description="Digest documents and links into reusable intelligence.",
        task_type="generation",
        output_kind="artifact",
        variables={"sources": "list", "output_kinds": "list"},
        required_variables=("sources",),
        optional_variables=("output_kinds",),
        file_refs=(),
        input_contract="source_references",
        output_contract="intelligence_candidates"),
    TaskTemplate(
        template_id="core.task.kaggle_competition",
        version="1.0.0",
        name="Kaggle competition",
        description="Complete a Kaggle competition end to end.",
        task_type="prediction",
        output_kind="artifact",
        variables={"competition": "string", "submit": "boolean",
                   "effort": "string"},
        required_variables=("competition",),
        optional_variables=("submit", "effort"),
        file_refs=(),
        input_contract="competition_slug",
        output_contract="submission_file"),
)


class TemplateLibrary:
    """Registered templates with deterministic discovery."""

    def __init__(self, templates: tuple = ()) -> None:
        self._templates: dict[str, TaskTemplate] = {}
        for template in CORE_TEMPLATES + tuple(templates):
            self.register(template)

    def register(self, template: TaskTemplate) -> None:
        key = (template.template_id, template.version)
        existing = self._templates.get(template.template_id)
        if existing is not None and existing.version == template.version:
            if existing.content_digest() != template.content_digest():
                raise TemplateError(
                    f"conflicting content for {template.template_id} "
                    f"version {template.version}")
            return
        self._templates[template.template_id] = template

    def get(self, template_id: str,
            version: str | None = None) -> TaskTemplate | None:
        template = self._templates.get(template_id)
        if template is None:
            return None
        if version is not None and template.version != version:
            return None
        return template

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._templates))

    def search(self, text: str) -> list[TaskTemplate]:
        """Deterministic lexical search over template names and types."""
        terms = set(text.lower().split())
        scored = []
        for template in self._templates.values():
            haystack = " ".join((
                template.name, template.description,
                template.task_type, template.output_kind)).lower()
            overlap = len(terms & set(haystack.split()))
            if overlap:
                scored.append((overlap, template.template_id, template))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored]


def self_test() -> dict:
    """Prove the library registers, searches, and refuses conflicts."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    library = TemplateLibrary()
    check("core_templates_are_registered",
          len(library.ids()) == 6
          and library.get("core.task.tabular_classification") is not None)
    check("exact_version_lookup",
          library.get("core.task.tabular_classification",
                      version="1.0.0") is not None
          and library.get("core.task.tabular_classification",
                          version="9.9.9") is None
          and library.get("missing") is None)
    hits = library.search("predict class label tabular")
    check("lexical_search_finds_relevant_templates",
          hits and hits[0].template_id
          == "core.task.tabular_classification")
    model_hits = library.search(
        "train and compare linear tree boosted model mlp prediction report")
    check("lexical_search_finds_model_comparison_template",
          model_hits and model_hits[0].template_id
          == "core.task.tabular_model_comparison")
    try:
        conflicting = TaskTemplate(
            template_id="core.task.tabular_classification",
            version="1.0.0", name="Different content",
            task_type="classification", output_kind="label",
            variables={"x": "string"}, required_variables=("x",))
        library.register(conflicting)
        check("conflicting_template_version_is_refused", False)
    except TemplateError:
        check("conflicting_template_version_is_refused", True)
    return {"tests": results}
