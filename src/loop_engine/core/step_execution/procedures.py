"""The step procedures Baltor's own Loop runtime can run, and the parked ones it names.

Owns the typed table of deterministic step procedures the custom Loop engine
runs (``step_procedure/v1``): each names its identity and version, its typed
inputs, parameters and output, its effects (none of them has any), the live
module it calls and the collected suite that checks it. It also names the
earlier custom capabilities that stay parked (the solve runtime, the Solution
Canvas, the campaign and Kaggle runners, the text conformance, duplicate
detection, field recovery, address and database copy operations), each with
the checkpoint revision that holds its working implementation and the suite
that must be collected again before it can return here. A parked procedure is
refused with ``procedure_parked``; nothing here imports a parked module.
Belongs to the step execution component (roadmap S-6.30, S-6.31).
Does not own the Loop runtime, selection or any grant.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from string import Template

from ..engines.records import EngineRecordError, identifier, text

PROCEDURE_RECORD_TYPE = "step_procedure/v1"
PROCEDURE_STATES = ("live", "parked")
LIVE, PARKED = PROCEDURE_STATES
#: The revision of checkpoint/full-capability-2026-09-21 that holds every parked implementation.
CHECKPOINT_REVISION = "a3bd0f1"
JSON_MEDIA_TYPE, TEXT_MEDIA_TYPE = "application/json", "text/plain"


class ProcedureRefused(EngineRecordError):
    """A procedure that is unknown, parked or given the wrong inputs; nothing ran."""


def _json_input(inputs: dict, name: str):
    try:
        return json.loads(inputs[name])
    except KeyError as exc:
        raise ProcedureRefused("procedure_input_missing", name) from exc
    except (ValueError, RecursionError) as exc:
        raise ProcedureRefused("procedure_input_not_json", name) from exc


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def match_contract_procedure(inputs: dict, parameters: dict) -> str:
    """Compare an observed value with an expected one under a declared match mode."""
    from ..contract_matching import ContractMatchError, ContractMatchPolicy, match_contract
    try:
        policy = ContractMatchPolicy(parameters.get("mode", ""), tuple(parameters.get("required_keys", ())),
                                     tuple(parameters.get("blocking_keys", ())), parameters.get("threshold", 0.0))
    except (ContractMatchError, TypeError) as exc:
        raise ProcedureRefused("procedure_parameters_refused", str(exc)) from exc
    return _canonical(match_contract(policy, _json_input(inputs, "expected"),
                                     _json_input(inputs, "observed")).to_dict())


def render_template_procedure(inputs: dict, parameters: dict) -> str:
    """Fill a declared text template from named inputs; a missing name refuses."""
    template = parameters.get("template")
    if type(template) is not str or not template:
        raise ProcedureRefused("procedure_parameters_refused", "a template is declared text")
    try:
        return Template(template).substitute(inputs)
    except (KeyError, ValueError) as exc:
        raise ProcedureRefused("procedure_input_missing", str(exc)) from exc


def select_fields_procedure(inputs: dict, parameters: dict) -> str:
    """Keep the declared fields of one JSON object, in canonical form; a missing field refuses."""
    fields = parameters.get("fields")
    if type(fields) not in (list, tuple) or not fields or any(type(item) is not str for item in fields):
        raise ProcedureRefused("procedure_parameters_refused", "fields is a list of names")
    value = _json_input(inputs, "record")
    if not isinstance(value, dict):
        raise ProcedureRefused("procedure_input_not_an_object", "record")
    missing = [item for item in fields if item not in value]
    if missing:
        raise ProcedureRefused("procedure_input_missing", ",".join(missing))
    return _canonical({item: value[item] for item in fields})


@dataclass(frozen=True)
class StepProcedure:
    """One procedure the Loop runtime may run for a step; a declaration, never a grant."""

    procedure_id: str
    version: str
    title: str
    inputs: tuple
    output_media_type: str
    state: str
    module: str
    suite: str
    function: object = None

    def __post_init__(self):
        identifier(self.procedure_id, "procedure_id")
        text(self.version, "version", 32)
        text(self.title, "title", 160)
        if any(not isinstance(item, str) for item in self.inputs):
            raise EngineRecordError("invalid_field", "inputs are names")
        if self.state not in PROCEDURE_STATES:
            raise EngineRecordError("invalid_vocabulary", "state is live or parked")
        text(self.module, "module")
        text(self.suite, "suite")
        if (self.state == LIVE) != callable(self.function):
            raise EngineRecordError("invalid_field", "a live procedure has a function and a parked one has none")

    @property
    def reference(self) -> str:
        return f"{self.procedure_id}@{self.version}"

    def to_dict(self) -> dict:
        return {"record_type": PROCEDURE_RECORD_TYPE, "procedure_id": self.procedure_id, "version": self.version,
                "title": self.title, "inputs": list(self.inputs), "output_media_type": self.output_media_type,
                "state": self.state, "module": self.module, "suite": self.suite, "effects": ["pure"],
                "checkpoint_revision": CHECKPOINT_REVISION if self.state == PARKED else None}


#: What returns through the custom Loop engine now: pure procedures over live modules.
LIVE_PROCEDURES = (
    StepProcedure("contract.match", "1", "Compare an observed value with an expected one under a declared mode",
                  ("expected", "observed"), JSON_MEDIA_TYPE, LIVE, "loop_engine.core.contract_matching",
                  "core.contract_matching", match_contract_procedure),
    StepProcedure("text.render_template", "1", "Fill a declared text template from named inputs",
                  (), TEXT_MEDIA_TYPE, LIVE, "loop_engine.core.step_execution.procedures",
                  "core.step_execution.engines_checks", render_template_procedure),
    StepProcedure("json.select_fields", "1", "Keep the declared fields of one JSON object",
                  ("record",), JSON_MEDIA_TYPE, LIVE, "loop_engine.core.step_execution.procedures",
                  "core.step_execution.engines_checks", select_fields_procedure),
)

#: What stays parked: named with its checkpoint home and the suite that must return first.
PARKED_PROCEDURES = tuple(
    StepProcedure(name, "1", title, (), JSON_MEDIA_TYPE, PARKED, module, suite)
    for name, title, module, suite in (
        ("text.conformance", "Text conformance operations", "loop_engine.code_nodes.text_conformance_operations",
         "code_nodes.text_conformance"),
        ("records.detect_duplicates", "Duplicate detection", "loop_engine.code_nodes.duplicate_detection",
         "code_nodes.duplicate_detection"),
        ("records.recover_fields", "Field recovery", "loop_engine.code_nodes.field_recovery",
         "code_nodes.field_recovery"),
        ("records.address_components", "Address components", "loop_engine.code_nodes.address_components",
         "code_nodes.address_components"),
        ("records.copy_database", "Database copy", "loop_engine.code_nodes.database_copy",
         "code_nodes.database_copy"),
        ("solution.run_canvas", "Solution Canvas execution", "loop_engine.code_nodes.solution_canvas",
         "code_nodes.solution_canvas"),
        ("solution.solve", "The in-process solve runtime", "loop_engine.code_nodes.solve_runtime",
         "code_nodes.solve_runtime"),
        ("campaign.run", "The campaign runner", "loop_engine.code_nodes.campaign_runner",
         "code_nodes.campaign_runner"),
        ("kaggle.execute", "The Kaggle executor", "loop_engine.code_nodes.kaggle_executor",
         "code_nodes.kaggle_executor")))


def procedure_for(reference: str) -> StepProcedure:
    """The live procedure a step names; a parked or unknown one refuses before anything runs."""
    for item in LIVE_PROCEDURES + PARKED_PROCEDURES:
        if item.reference == reference:
            if item.state == PARKED:
                raise ProcedureRefused("procedure_parked", f"{reference} is parked at checkpoint "
                                       f"{CHECKPOINT_REVISION} until its suite {item.suite} is collected again")
            return item
    raise ProcedureRefused("procedure_unknown", reference)


def procedure_table() -> list:
    return [item.to_dict() for item in LIVE_PROCEDURES + PARKED_PROCEDURES]


def self_test():
    """Run the step execution checks, which cover the procedures."""
    from .engines_checks import self_test as run_engine_checks
    return run_engine_checks()
