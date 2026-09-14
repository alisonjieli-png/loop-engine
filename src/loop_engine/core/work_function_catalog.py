"""Open-ended catalog of human-work functions available to Practitioners.

Owns passive versioned descriptions of cognitive, implicit-pattern, judgment,
planning, action, metacognitive, and communication functions. It loads their
Context Intelligence source, validates references, and returns model-selection
candidates. It does not execute a function, select a prompt, grant authority,
claim biological equivalence, or decide that the inventory is exhaustive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

import yaml

from .context_ontology import QUESTION_FAMILIES, THINKING_METHODS


WORK_FUNCTION_FAMILIES = (
    "orientation_and_framing",
    "attention_and_selection",
    "information_acquisition",
    "memory_pattern_and_habit",
    "reasoning_and_modeling",
    "judgment_and_decision",
    "planning_and_coordination",
    "construction_and_action",
    "observation_and_measurement",
    "verification_and_critique",
    "metacognition_and_recovery",
    "learning_and_communication",
)
PROCESSING_VISIBILITIES = (
    "observable_explicit", "configured_implicit",
    "deterministic_control", "mixed", "unknown")
REALIZATION_KINDS = (
    "prompt_guidance", "context_selection", "reviewed_procedure",
    "runtime_control", "capability", "mixed")
INVENTORY_POLICIES = ("open_ended",)
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class WorkFunctionCatalogError(ValueError):
    """A work-function record or catalog violated its typed contract."""


def _texts(value, name: str, *, required=True) -> tuple[str, ...]:
    if (not isinstance(value, (list, tuple))
            or any(not isinstance(item, str) or not item.strip()
                   for item in value)):
        raise WorkFunctionCatalogError(f"{name} must be a text sequence")
    values = tuple(item.strip() for item in value)
    if len(values) != len(set(values)) or (required and not values):
        raise WorkFunctionCatalogError(
            f"{name} must contain unique non-empty values")
    return values


@dataclass(frozen=True)
class WorkFunctionSpec:
    """One configurable solving function, not an executable runtime object."""

    function_id: str
    version: str
    family: str
    processing_visibility: str
    realization_kind: str
    purpose: str
    step_affinities: tuple[str, ...]
    thinking_methods: tuple[str, ...]
    question_families: tuple[str, ...]
    instructions: tuple[str, ...]
    context_requirements: tuple[str, ...]
    expected_observations: tuple[str, ...]
    evaluation_checks: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not re.fullmatch(r"[a-z][a-z0-9_.-]{2,160}", self.function_id)
                or not _SEMVER.fullmatch(self.version)
                or not isinstance(self.purpose, str)
                or not self.purpose.strip()):
            raise WorkFunctionCatalogError("work function identity is invalid")
        if self.family not in WORK_FUNCTION_FAMILIES:
            raise WorkFunctionCatalogError("work function family is invalid")
        if self.processing_visibility not in PROCESSING_VISIBILITIES:
            raise WorkFunctionCatalogError(
                "work function processing visibility is invalid")
        if self.realization_kind not in REALIZATION_KINDS:
            raise WorkFunctionCatalogError(
                "work function realization kind is invalid")
        for name in (
                "step_affinities", "instructions", "context_requirements",
                "expected_observations", "evaluation_checks"):
            object.__setattr__(self, name, _texts(getattr(self, name), name))
        methods = _texts(self.thinking_methods, "thinking_methods", required=False)
        questions = _texts(
            self.question_families, "question_families", required=False)
        if set(methods) - set(THINKING_METHODS):
            raise WorkFunctionCatalogError(
                "work function names an unknown thinking method")
        if set(questions) - set(QUESTION_FAMILIES):
            raise WorkFunctionCatalogError(
                "work function names an unknown question family")
        object.__setattr__(self, "thinking_methods", methods)
        object.__setattr__(self, "question_families", questions)

    @property
    def function_ref(self) -> str:
        return f"{self.function_id}@{self.version}"

    def to_dict(self) -> dict:
        return {
            "record_type": "work_function_spec/v1",
            "function_id": self.function_id,
            "function_ref": self.function_ref,
            "version": self.version,
            "family": self.family,
            "processing_visibility": self.processing_visibility,
            "realization_kind": self.realization_kind,
            "purpose": self.purpose,
            "step_affinities": list(self.step_affinities),
            "thinking_methods": list(self.thinking_methods),
            "question_families": list(self.question_families),
            "instructions": list(self.instructions),
            "context_requirements": list(self.context_requirements),
            "expected_observations": list(self.expected_observations),
            "evaluation_checks": list(self.evaluation_checks),
            "executes_work": False,
            "grants_authority": False,
        }


@dataclass(frozen=True)
class WorkFunctionCatalog:
    """Versioned baseline with an explicit open-ended discovery policy."""

    catalog_id: str
    version: str
    inventory_policy: str
    proposal_channel: str
    functions: tuple[WorkFunctionSpec, ...]
    record_type: str = "practitioner_work_function_catalog/v1"

    def __post_init__(self) -> None:
        if (self.record_type != "practitioner_work_function_catalog/v1"
                or not self.catalog_id.strip()
                or not _SEMVER.fullmatch(self.version)
                or self.inventory_policy not in INVENTORY_POLICIES
                or not self.proposal_channel.strip()):
            raise WorkFunctionCatalogError("work function catalog identity is invalid")
        functions = tuple(self.functions)
        if (not functions
                or any(not isinstance(item, WorkFunctionSpec)
                       for item in functions)
                or len({item.function_ref for item in functions})
                != len(functions)):
            raise WorkFunctionCatalogError(
                "work function catalog needs unique typed functions")
        if set(WORK_FUNCTION_FAMILIES) - {item.family for item in functions}:
            raise WorkFunctionCatalogError(
                "baseline work function catalog must cover every broad family")
        object.__setattr__(self, "functions", functions)

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(item.function_ref for item in self.functions)

    def candidates(self, step_id: str) -> tuple[dict, ...]:
        """Return every function as a candidate; affinity is only a hint."""
        if not isinstance(step_id, str) or not step_id.strip():
            raise WorkFunctionCatalogError("work function selection needs a step")
        return tuple({
            **item.to_dict(),
            "active_step_match": step_id in item.step_affinities,
            "selection_authority": "model",
            "inventory_policy": self.inventory_policy,
        } for item in self.functions)

    def validate_refs(self, refs) -> tuple[str, ...]:
        values = _texts(refs, "work_function_refs")
        unknown = sorted(set(values) - set(self.refs))
        if unknown:
            raise WorkFunctionCatalogError(
                f"unknown work function refs {unknown}")
        return values

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "catalog_id": self.catalog_id,
            "version": self.version,
            "inventory_policy": self.inventory_policy,
            "proposal_channel": self.proposal_channel,
            "functions": [item.to_dict() for item in self.functions],
        }


def _function(value: dict) -> WorkFunctionSpec:
    expected = {
        "function_id", "version", "family", "processing_visibility",
        "realization_kind", "purpose", "step_affinities",
        "thinking_methods", "question_families", "instructions",
        "context_requirements", "expected_observations",
        "evaluation_checks"}
    if not isinstance(value, dict) or set(value) != expected:
        raise WorkFunctionCatalogError("work function fields do not match")
    return WorkFunctionSpec(
        str(value["function_id"]), str(value["version"]),
        str(value["family"]), str(value["processing_visibility"]),
        str(value["realization_kind"]), str(value["purpose"]),
        tuple(value["step_affinities"]), tuple(value["thinking_methods"]),
        tuple(value["question_families"]), tuple(value["instructions"]),
        tuple(value["context_requirements"]),
        tuple(value["expected_observations"]),
        tuple(value["evaluation_checks"]))


@lru_cache(maxsize=1)
def load_work_function_catalog() -> WorkFunctionCatalog:
    """Load and validate the packaged Context Intelligence baseline."""
    path = files("loop_engine").joinpath(
        "intelligence/context/core/practitioner_work_functions.yaml")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {
        "record_type", "catalog_id", "version", "inventory_policy",
        "proposal_channel", "functions"}
    if (not isinstance(value, dict) or set(value) != expected
            or not isinstance(value.get("functions"), list)):
        raise WorkFunctionCatalogError(
            "work function catalog fields do not match")
    return WorkFunctionCatalog(
        str(value["catalog_id"]), str(value["version"]),
        str(value["inventory_policy"]), str(value["proposal_channel"]),
        tuple(_function(item) for item in value["functions"]),
        str(value["record_type"]))


def self_test() -> dict:
    """Check catalog breadth, openness, selection, and invalid references."""
    catalog = load_work_function_catalog()
    candidates = catalog.candidates("verify")
    selected = catalog.validate_refs((catalog.refs[0], catalog.refs[-1]))
    refused = False
    try:
        catalog.validate_refs(("core.work_function.unregistered@1.0.0",))
    except WorkFunctionCatalogError:
        refused = True
    tests = [{
        "test": "baseline_covers_every_work_function_family",
        "passed": {item.family for item in catalog.functions}
        == set(WORK_FUNCTION_FAMILIES),
    }, {
        "test": "inventory_is_explicitly_open_ended",
        "passed": catalog.inventory_policy == "open_ended"
        and bool(catalog.proposal_channel),
    }, {
        "test": "implicit_functions_are_configuration_not_hidden_evidence",
        "passed": any(item.processing_visibility == "configured_implicit"
                      and item.to_dict()["executes_work"] is False
                      for item in catalog.functions),
    }, {
        "test": "all_functions_remain_candidates_and_affinity_selects_nothing",
        "passed": len(candidates) == len(catalog.functions)
        and all(item["selection_authority"] == "model" for item in candidates)
        and any(item["active_step_match"] for item in candidates)
        and any(not item["active_step_match"] for item in candidates),
    }, {
        "test": "selected_refs_must_have_been_registered",
        "passed": selected == (catalog.refs[0], catalog.refs[-1]) and refused,
    }, {
        "test": "functions_have_prompts_context_observations_and_checks",
        "passed": all(item.instructions and item.context_requirements
                      and item.expected_observations and item.evaluation_checks
                      for item in catalog.functions),
    }]
    return {
        "record_type": "work_function_catalog_test/v1", "tests": tests,
        "passed": sum(item["passed"] for item in tests),
        "total": len(tests),
        "all_passed": all(item["passed"] for item in tests)}


__all__ = (
    "WorkFunctionCatalog", "WorkFunctionCatalogError", "WorkFunctionSpec",
    "load_work_function_catalog", "self_test")
