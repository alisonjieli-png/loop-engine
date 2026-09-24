"""The step edge: step_run_request/v1, step_run_result/v1 and executor_profile/v1.

Owns the typed records one step's assignment crosses into one step executor
engine and returns through (design section 13.3): the request carries the
step's identity, assignment, typed inputs and output ports, the material placed
for it, its authority, its preemptive budget and its executor requirements;
the result carries every key for every engine (a value an engine does not
expose is null and reads as unknown), the observed effects, the accounting and
what the envelope computed about the executor, including ``delegated``. Also
owns executor_profile/v1, the capability record inside every step executor
descriptor, with its compatibility entries (component type, package format,
adapter version, harness interface, scope, activation and support state) and
the requirement comparison unmet_step_requirements. Belongs to the step
execution component (roadmap S-6.31).
Does not own: selection, dispatch, a grant or acceptance. Completion is never
acceptance: a result's task_accepted is constantly false.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from types import MappingProxyType

from ..configuration_capabilities import digest
from ..engines.records import (
    EngineRecordError, contract, engine_modes, exact_engine_ref, flag, identifier, json_object, member, pattern,
    plain, read_part, read_record, sequence, sha256, text)
from ..facets import EFFECTS
from ..harness_execution_contracts import ISOLATIONS, LIMITS

STEP_REQUEST_RECORD_TYPE = "step_run_request/v1"
STEP_RESULT_RECORD_TYPE = "step_run_result/v1"
EXECUTOR_PROFILE_RECORD_TYPE = "executor_profile/v1"
STEP_STATUSES = ("completed", "failed", "refused", "unavailable", "cancelled", "budget_exhausted",
                 "input_required", "auth_required", "effects_uncertain")
(COMPLETED, FAILED, REFUSED, UNAVAILABLE, CANCELLED, BUDGET_EXHAUSTED, INPUT_REQUIRED, AUTH_REQUIRED,
 EFFECTS_UNCERTAIN) = STEP_STATUSES
#: The failure kinds of the step executor slot each status may carry.
STATUS_FAILURE_KINDS = MappingProxyType({
    COMPLETED: ("",), CANCELLED: ("",), INPUT_REQUIRED: ("",), AUTH_REQUIRED: ("",),
    FAILED: ("engine_reported_failure", "output_validation_failed", "semantic_response_rejected",
             "engine_changed_after_selection"),
    REFUSED: ("capability_requirement_unsatisfied", "policy_refused"),
    UNAVAILABLE: ("engine_unavailable",), BUDGET_EXHAUSTED: ("authority_exhausted",),
    EFFECTS_UNCERTAIN: ("effects_uncertain",)})
PUBLICATIONS = ("final_only", "candidates_then_final")
DETERMINISTIC_MODE = "deterministic"
MATERIAL_KINDS = ("instruction_file", "skill", "protocol_server")
#: Evidence states of one piece of material, each a separate fact: its exact
#: source was resolved, its files were materialized with digests, the harness's
#: loader listed it, it entered the active runtime, an attributable action used
#: it, and an independent check verified the result and the required steps.
MATERIAL_EVIDENCE_STATES = ("resolved", "materialized", "available", "loaded", "used", "verified")
#: How a harness supports one component type; supported is too coarse to decide with.
SUPPORT_STATES = ("native", "translated", "embedded", "simulated", "unsupported", "unverified")
USABLE_SUPPORT = SUPPORT_STATES[:3]
COMPONENT_SCOPES = ("step_folder", "project", "global")
ACTIVATION_MODES = ("automatic", "explicit", "tool_mediated")
PLACEMENTS = ("fresh_process", "in_process", "long_lived_session", "pooled_sessions")
FRESH_PROCESS, IN_PROCESS = PLACEMENTS[0], PLACEMENTS[1]
#: What an engine declares about starting fresh for each step. A declaration never
#: proves it: only a qualification at the rung material_loaded or above does.
FRESH_INSTANCE_STATES = ("supported", "unsupported")
NETWORK_NEEDS = ("none", "loopback_model_endpoint")
NATIVE_TOOLS = ("none", "confined_to_step_folder")
EFFECT_STATES = ("none", "committed", "uncertain")
#: Isolation values under which a separately started process can count as delegation.
DELEGATING_ISOLATIONS = ("os_sandbox", "container", "remote")
_NATIVE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_PROFILE = re.compile(r"(?:practitioner|intelligence|solution)\.[A-Za-z0-9_.-]+@[0-9]+\.[0-9]+\.[0-9]+")
_MEDIA_TYPE = re.compile(r"[a-z]+/[a-z0-9.+-]+")
_CODE = re.compile(r"[a-z][a-z0-9_]{0,79}")
TEXT_LIMIT = 1024 * 1024


def text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _body(value, name, *, empty=False):
    if type(value) is not str or "\x00" in value or len(value) > TEXT_LIMIT or (not empty and not value.strip()):
        raise EngineRecordError("invalid_text", f"{name} is bounded text")
    return value


def _count(value, name, *, optional=True):
    if value is None and optional:
        return None
    if type(value) is not int or value < 0:
        raise EngineRecordError("invalid_field", name + " is a count or unknown")
    return value


def _seconds(value, name, *, optional=True):
    if value is None and optional:
        return None
    if type(value) not in (int, float) or not 0 <= value < float("inf"):
        raise EngineRecordError("invalid_field", name + " is finite and nonnegative, or unknown")
    return float(value)


def _typed(values, kind, name):
    values = tuple(values) if type(values) in (tuple, list) else None
    if values is None or any(not isinstance(item, kind) for item in values):
        raise EngineRecordError("invalid_field", f"{name} holds {kind.__name__} values")
    return values


def _unique(values, key, name):
    keys = [key(item) for item in values]
    if len(set(keys)) != len(keys):
        raise EngineRecordError("repeated_value", name + " names each item once")


@dataclass(frozen=True)
class StepInput:
    """One typed input, supplied inline with its digest."""

    name: str
    media_type: str
    text: str

    def __post_init__(self):
        identifier(self.name, "input name")
        pattern(self.media_type, "media_type", _MEDIA_TYPE, "a media type")
        _body(self.text, "input text", empty=True)

    def to_dict(self):
        return {"name": self.name, "media_type": self.media_type, "text": self.text,
                "digest": text_digest(self.text)}


@dataclass(frozen=True)
class StepOutputPort:
    """One declared output port of the step's output contract."""

    name: str
    media_type: str
    required: bool

    def __post_init__(self):
        identifier(self.name, "output port")
        pattern(self.media_type, "media_type", _MEDIA_TYPE, "a media type")
        flag(self.required, "required")

    def to_dict(self):
        return {"name": self.name, "media_type": self.media_type, "required": self.required}


@dataclass(frozen=True)
class StepMaterial:
    """One selected, approved file placed for the step: its kind, native name and body."""

    kind: str
    name: str
    body: str

    def __post_init__(self):
        member(self.kind, "material kind", MATERIAL_KINDS)
        pattern(self.name, "material name", _NATIVE_NAME, "a native name")
        _body(self.body, "material body")

    def to_dict(self):
        return {"kind": self.kind, "name": self.name, "body": self.body, "digest": text_digest(self.body)}


@dataclass(frozen=True)
class StepBudget:
    """Preemptive limits for one attempt; post-run acceptance bounds are kept elsewhere."""

    wall_time_seconds: float
    model_calls: "int | None" = None
    total_tokens: "int | None" = None
    spawned_tasks: int = 0

    def __post_init__(self):
        if type(self.wall_time_seconds) not in (int, float) or not 0 < self.wall_time_seconds <= 86400:
            raise EngineRecordError("invalid_field", "wall_time_seconds is positive and at most one day")
        object.__setattr__(self, "wall_time_seconds", float(self.wall_time_seconds))
        _count(self.model_calls, "model_calls")
        _count(self.total_tokens, "total_tokens")
        _count(self.spawned_tasks, "spawned_tasks", optional=False)

    def to_dict(self):
        return {"wall_time_seconds": self.wall_time_seconds, "model_calls": self.model_calls,
                "total_tokens": self.total_tokens, "spawned_tasks": self.spawned_tasks}


@dataclass(frozen=True)
class StepRequirements:
    """What the owning Loop requires of any engine; each is a screen, never a grant."""

    required_features: tuple = ()
    required_limits: tuple = ()
    allowed_isolations: tuple = ()
    allowed_engine_kinds: tuple = ()
    delegation_required: bool = True
    fresh_instance_required: bool = True

    def __post_init__(self):
        object.__setattr__(self, "required_features", sequence(self.required_features, "required_features",
                                                               identifier))
        object.__setattr__(self, "required_limits", sequence(
            self.required_limits, "required_limits", lambda v, n: member(v, n, LIMITS)))
        object.__setattr__(self, "allowed_isolations", sequence(
            self.allowed_isolations, "allowed_isolations", lambda v, n: member(v, n, ISOLATIONS)))
        object.__setattr__(self, "allowed_engine_kinds", sequence(self.allowed_engine_kinds,
                                                                  "allowed_engine_kinds", identifier))
        flag(self.delegation_required, "delegation_required")
        flag(self.fresh_instance_required, "fresh_instance_required")

    def to_dict(self):
        return {"required_features": list(self.required_features), "required_limits": list(self.required_limits),
                "allowed_isolations": list(self.allowed_isolations),
                "allowed_engine_kinds": list(self.allowed_engine_kinds),
                "delegation_required": self.delegation_required,
                "fresh_instance_required": self.fresh_instance_required}


REQUEST_FIELDS = (
    "request_id", "owning_loop_ref", "owning_profile_ref", "definition_ref", "definition_digest", "step_name",
    "attempt", "idempotency_key", "goal", "instructions", "inputs", "output_ports", "output_contract_ref",
    "evaluation_contract_ref", "publication", "mode", "procedure_ref", "procedure_parameters", "granted_effects",
    "authorize_model_calls", "model_routes", "material", "budget", "requirements")


@dataclass(frozen=True)
class StepRunRequest:
    """One step's typed assignment, authority, budget and requirements (step_run_request/v1)."""

    request_id: str
    owning_loop_ref: str
    owning_profile_ref: str
    definition_ref: str
    definition_digest: str
    step_name: str
    attempt: int
    idempotency_key: str
    goal: str
    instructions: str
    inputs: tuple
    output_ports: tuple
    output_contract_ref: str
    evaluation_contract_ref: str
    publication: str
    mode: str
    procedure_ref: str
    procedure_parameters: object
    granted_effects: tuple
    authorize_model_calls: bool
    model_routes: tuple
    material: tuple
    budget: StepBudget
    requirements: StepRequirements

    def __post_init__(self):
        set_ = object.__setattr__
        for name in ("request_id", "owning_loop_ref", "definition_ref", "idempotency_key", "evaluation_contract_ref"):
            text(getattr(self, name), name)
        pattern(self.owning_profile_ref, "owning_profile_ref", _PROFILE, "an exact role.profile@x.y.z")
        sha256(self.definition_digest, "definition_digest")
        identifier(self.step_name, "step_name")
        if type(self.attempt) is not int or self.attempt < 1:
            raise EngineRecordError("invalid_field", "attempt counts from one")
        _body(self.goal, "goal")
        _body(self.instructions, "instructions", empty=True)
        set_(self, "inputs", _typed(self.inputs, StepInput, "inputs"))
        set_(self, "output_ports", _typed(self.output_ports, StepOutputPort, "output_ports"))
        _unique(self.inputs, lambda item: item.name, "inputs")
        _unique(self.output_ports, lambda item: item.name, "output_ports")
        if not self.output_ports:
            raise EngineRecordError("invalid_field", "a step declares at least one output port")
        contract(self.output_contract_ref, "output_contract_ref")
        member(self.publication, "publication", PUBLICATIONS)
        member(self.mode, "mode", engine_modes())
        if self.procedure_ref:
            text(self.procedure_ref, "procedure_ref")
        set_(self, "procedure_parameters", json_object(self.procedure_parameters, "procedure_parameters"))
        set_(self, "granted_effects", sequence(self.granted_effects, "granted_effects",
                                               lambda v, n: member(v, n, EFFECTS)))
        flag(self.authorize_model_calls, "authorize_model_calls")
        set_(self, "model_routes", sequence(self.model_routes, "model_routes", text))
        set_(self, "material", _typed(self.material, StepMaterial, "material"))
        _unique(self.material, lambda item: (item.kind, item.name), "material")
        if not isinstance(self.budget, StepBudget) or not isinstance(self.requirements, StepRequirements):
            raise EngineRecordError("invalid_field", "budget and requirements are typed records")
        _require_mode_rules(self)

    def to_dict(self) -> dict:
        return {"record_type": STEP_REQUEST_RECORD_TYPE, "request_id": self.request_id,
                "owning_loop_ref": self.owning_loop_ref, "owning_profile_ref": self.owning_profile_ref,
                "definition_ref": self.definition_ref, "definition_digest": self.definition_digest,
                "step_name": self.step_name, "attempt": self.attempt, "idempotency_key": self.idempotency_key,
                "goal": self.goal, "instructions": self.instructions,
                "inputs": [item.to_dict() for item in self.inputs],
                "output_ports": [item.to_dict() for item in self.output_ports],
                "output_contract_ref": self.output_contract_ref,
                "evaluation_contract_ref": self.evaluation_contract_ref, "publication": self.publication,
                "mode": self.mode, "procedure_ref": self.procedure_ref,
                "procedure_parameters": plain(self.procedure_parameters),
                "granted_effects": list(self.granted_effects), "authorize_model_calls": self.authorize_model_calls,
                "model_routes": list(self.model_routes), "material": [item.to_dict() for item in self.material],
                "budget": self.budget.to_dict(), "requirements": self.requirements.to_dict()}

    @property
    def digest(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, record) -> "StepRunRequest":
        record = read_record(record, STEP_REQUEST_RECORD_TYPE, REQUEST_FIELDS)
        for name in ("inputs", "output_ports", "material"):
            if type(record[name]) is not list:
                raise EngineRecordError("invalid_field", name + " must be a list")
        inputs = []
        for item in record["inputs"]:
            item = read_part(item, "input", ("name", "media_type", "text", "digest"))
            inputs.append(StepInput(item["name"], item["media_type"], item["text"]))
            if text_digest(inputs[-1].text) != item["digest"]:
                raise EngineRecordError("derived_value_mismatch", "an input digest does not match its text")
        material = []
        for item in record["material"]:
            item = read_part(item, "material", ("kind", "name", "body", "digest"))
            material.append(StepMaterial(item["kind"], item["name"], item["body"]))
            if text_digest(material[-1].body) != item["digest"]:
                raise EngineRecordError("derived_value_mismatch", "a material digest does not match its body")
        ports = [StepOutputPort(**read_part(item, "output port", ("name", "media_type", "required")))
                 for item in record["output_ports"]]
        budget = StepBudget(**read_part(record["budget"], "budget", ("wall_time_seconds", "model_calls",
                                                                      "total_tokens", "spawned_tasks")))
        wanted = read_part(record["requirements"], "requirements", tuple(StepRequirements().to_dict()))
        return cls(**{name: record[name] for name in REQUEST_FIELDS if name not in (
            "inputs", "output_ports", "material", "budget", "requirements")},
            inputs=tuple(inputs), output_ports=tuple(ports), material=tuple(material), budget=budget,
            requirements=StepRequirements(**wanted))


def _require_mode_rules(request):
    """A deterministic step calls no model; a model-led step is delegated to a harness
    (the harness-first rule, roadmap S-6.28); a procedure is deterministic work."""
    deterministic = request.mode == DETERMINISTIC_MODE
    if deterministic and (request.authorize_model_calls or request.model_routes):
        raise EngineRecordError("mode_rule", "a deterministic step authorizes no model call")
    if not deterministic and not request.requirements.delegation_required:
        raise EngineRecordError("mode_rule", "a hybrid or model-led step is delegated to a harness")
    if request.procedure_ref and not deterministic:
        raise EngineRecordError("mode_rule", "a procedure is deterministic work")
    if request.model_routes and not request.authorize_model_calls:
        raise EngineRecordError("mode_rule", "model routes need model-call authority")
    if request.mode not in _profile_modes(request.owning_profile_ref):
        raise EngineRecordError("mode_rule", "the owning Loop's profile does not allow the step's mode")


def _profile_modes(profile_ref: str) -> tuple:
    """The modes the exact owning profile allows; an unknown profile allows none."""
    from ...loop.loop_profile_catalog import LoopProfileRef
    from ...loop.loop_profile_ontology import get_profile
    profile_id, _, version = profile_ref.partition("@")
    try:
        return tuple(get_profile(LoopProfileRef(profile_id, version)).allowed_modes)
    except Exception:
        return ()


@dataclass(frozen=True)
class StepOutput:
    """One output by port, with its digest."""

    port: str
    media_type: str
    text: str

    def __post_init__(self):
        identifier(self.port, "output port")
        pattern(self.media_type, "media_type", _MEDIA_TYPE, "a media type")
        _body(self.text, "output text", empty=True)

    def to_dict(self):
        return {"port": self.port, "media_type": self.media_type, "text": self.text,
                "digest": text_digest(self.text)}


@dataclass(frozen=True)
class MaterialObservation:
    """The highest evidence state one piece of material reached, with what showed it."""

    kind: str
    name: str
    material_digest: str
    state: str
    observed_by: str

    def __post_init__(self):
        member(self.kind, "material kind", MATERIAL_KINDS)
        pattern(self.name, "material name", _NATIVE_NAME, "a native name")
        sha256(self.material_digest, "material_digest")
        member(self.state, "material evidence state", MATERIAL_EVIDENCE_STATES)
        text(self.observed_by, "observed_by")

    def to_dict(self):
        return {"kind": self.kind, "name": self.name, "material_digest": self.material_digest,
                "state": self.state, "observed_by": self.observed_by}


@dataclass(frozen=True)
class StepAccounting:
    """Calls counted by the broker and tokens as the provider reported them; unknown stays unknown."""

    model_calls: "int | None"
    input_tokens: "int | None"
    output_tokens: "int | None"
    cost: "float | None"

    def __post_init__(self):
        for name in ("model_calls", "input_tokens", "output_tokens"):
            _count(getattr(self, name), name)
        _seconds(self.cost, "cost")

    def to_dict(self):
        return {"model_calls": self.model_calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "cost": self.cost,
                "cost_state": "unknown" if self.cost is None else "known"}


NO_MODEL_CALLS = StepAccounting(0, 0, 0, 0.0)
UNKNOWN_ACCOUNTING = StepAccounting(None, None, None, None)


@dataclass(frozen=True)
class ExecutorIdentity:
    """The executor actually used, and whether the envelope counts it as delegation."""

    engine_ref: str
    descriptor_digest: str
    installation_digest: str
    process_identity: str
    sandbox_profile_digest: str
    delegated: bool

    def __post_init__(self):
        exact_engine_ref(self.engine_ref, "engine_ref")
        sha256(self.descriptor_digest, "descriptor_digest")
        sha256(self.installation_digest, "installation_digest")
        for name in ("process_identity", "sandbox_profile_digest"):
            if getattr(self, name):
                sha256(getattr(self, name), name)
        flag(self.delegated, "delegated")

    def to_dict(self):
        return {"engine_ref": self.engine_ref, "descriptor_digest": self.descriptor_digest,
                "installation_digest": self.installation_digest, "process_identity": self.process_identity,
                "sandbox_profile_digest": self.sandbox_profile_digest, "delegated": self.delegated}


RESULT_FIELDS = (
    "request_id", "request_digest", "status", "failure_kind", "error_code", "outputs", "candidates",
    "workspace_changes", "effects", "accounting", "material", "native_identities", "executor",
    "engine_preferences", "engine_reported_seconds", "measured_seconds", "task_accepted")


@dataclass(frozen=True)
class StepRunResult:
    """What one attempt produced; every key present whichever engine ran (step_run_result/v1)."""

    request_id: str
    request_digest: str
    status: str
    failure_kind: str
    error_code: str
    outputs: tuple
    candidates: tuple
    workspace_changes: tuple
    effects: str
    accounting: StepAccounting
    material: tuple
    native_identities: object
    executor: "ExecutorIdentity | None"
    engine_preferences: tuple
    engine_reported_seconds: "float | None"
    measured_seconds: "float | None"

    def __post_init__(self):
        set_ = object.__setattr__
        text(self.request_id, "request_id")
        sha256(self.request_digest, "request_digest")
        member(self.status, "status", STEP_STATUSES)
        member(self.failure_kind, "failure_kind", STATUS_FAILURE_KINDS[self.status])
        if self.error_code:
            pattern(self.error_code, "error_code", _CODE, "a bounded code")
        set_(self, "outputs", _typed(self.outputs, StepOutput, "outputs"))
        set_(self, "candidates", _typed(self.candidates, StepOutput, "candidates"))
        _unique(self.outputs, lambda item: item.port, "outputs")
        changes = tuple(self.workspace_changes) if type(self.workspace_changes) in (tuple, list) else None
        if changes is None or any(type(item) is not tuple or len(item) != 2 for item in changes):
            raise EngineRecordError("invalid_field", "workspace changes are (relative path, digest or deleted)")
        for path, content in changes:
            text(path, "changed path")
            if path.startswith("/") or ".." in path.split("/"):
                raise EngineRecordError("invalid_path", "a workspace change stays inside the step folder")
            if content != "deleted":
                sha256(content, "changed file digest")
        set_(self, "workspace_changes", changes)
        member(self.effects, "effects", EFFECT_STATES)
        if (self.status == EFFECTS_UNCERTAIN) != (self.effects == "uncertain"):
            raise EngineRecordError("invalid_field", "effects are uncertain exactly when the status says so")
        if not isinstance(self.accounting, StepAccounting):
            raise EngineRecordError("invalid_field", "accounting is a StepAccounting")
        set_(self, "material", _typed(self.material, MaterialObservation, "material"))
        set_(self, "native_identities", json_object(self.native_identities, "native_identities"))
        if self.executor is not None and not isinstance(self.executor, ExecutorIdentity):
            raise EngineRecordError("invalid_field", "executor is an ExecutorIdentity or null")
        prefs = tuple(self.engine_preferences) if type(self.engine_preferences) in (tuple, list) else None
        if prefs is None:
            raise EngineRecordError("invalid_field", "engine_preferences is a sequence of override records")
        set_(self, "engine_preferences", tuple(json_object(item, "engine preference") for item in prefs))
        set_(self, "engine_reported_seconds", _seconds(self.engine_reported_seconds, "engine_reported_seconds"))
        set_(self, "measured_seconds", _seconds(self.measured_seconds, "measured_seconds"))

    @property
    def task_accepted(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {"record_type": STEP_RESULT_RECORD_TYPE, "request_id": self.request_id,
                "request_digest": self.request_digest, "status": self.status, "failure_kind": self.failure_kind,
                "error_code": self.error_code, "outputs": [item.to_dict() for item in self.outputs],
                "candidates": [item.to_dict() for item in self.candidates],
                "workspace_changes": [list(item) for item in self.workspace_changes], "effects": self.effects,
                "accounting": self.accounting.to_dict(), "material": [item.to_dict() for item in self.material],
                "native_identities": plain(self.native_identities),
                "executor": None if self.executor is None else self.executor.to_dict(),
                "engine_preferences": [plain(item) for item in self.engine_preferences],
                "engine_reported_seconds": self.engine_reported_seconds,
                "measured_seconds": self.measured_seconds, "task_accepted": False}

    @classmethod
    def from_dict(cls, record) -> "StepRunResult":
        """Read a result an engine wrote; an unknown key, another version or a claimed acceptance refuses."""
        record = read_record(record, STEP_RESULT_RECORD_TYPE, RESULT_FIELDS)
        if record["task_accepted"] is not False:
            raise EngineRecordError("self_acceptance", "an engine never accepts its own step")
        for name in ("outputs", "candidates", "workspace_changes", "material", "engine_preferences"):
            if type(record[name]) is not list:
                raise EngineRecordError("invalid_field", name + " must be a list")
        outputs = tuple(_output(item) for item in record["outputs"])
        candidates = tuple(_output(item) for item in record["candidates"])
        accounting = read_part(record["accounting"], "accounting", ("model_calls", "input_tokens", "output_tokens",
                                                                     "cost", "cost_state"))
        spent = StepAccounting(accounting["model_calls"], accounting["input_tokens"], accounting["output_tokens"],
                               accounting["cost"])
        if spent.to_dict()["cost_state"] != accounting["cost_state"]:
            raise EngineRecordError("derived_value_mismatch", "cost_state does not match the cost")
        material = tuple(MaterialObservation(**read_part(item, "material observation", (
            "kind", "name", "material_digest", "state", "observed_by"))) for item in record["material"])
        executor = record["executor"]
        if executor is not None:
            executor = ExecutorIdentity(**read_part(executor, "executor", (
                "engine_ref", "descriptor_digest", "installation_digest", "process_identity",
                "sandbox_profile_digest", "delegated")))
        changes = []
        for item in record["workspace_changes"]:
            if type(item) is not list or len(item) != 2:
                raise EngineRecordError("invalid_field", "a workspace change is [path, digest]")
            changes.append(tuple(item))
        return cls(record["request_id"], record["request_digest"], record["status"], record["failure_kind"],
                   record["error_code"], outputs, candidates, tuple(changes), record["effects"], spent, material,
                   record["native_identities"], executor, tuple(record["engine_preferences"]),
                   record["engine_reported_seconds"], record["measured_seconds"])


def _output(item) -> StepOutput:
    item = read_part(item, "output", ("port", "media_type", "text", "digest"))
    output = StepOutput(item["port"], item["media_type"], item["text"])
    if text_digest(output.text) != item["digest"]:
        raise EngineRecordError("derived_value_mismatch", "an output digest does not match its text")
    return output


@dataclass(frozen=True)
class CompatibilityEntry:
    """One compatibility key: component type, package format and version, adapter version,
    harness interface and version, scope, activation and permission mode, and support."""

    component_type: str
    package_format: str
    adapter_version: str
    harness_interface: str
    scope: str
    activation: str
    support: str

    def __post_init__(self):
        member(self.component_type, "component type", MATERIAL_KINDS)
        for name in ("package_format", "adapter_version", "harness_interface"):
            text(getattr(self, name), name, 128)
        member(self.scope, "scope", COMPONENT_SCOPES)
        member(self.activation, "activation", ACTIVATION_MODES)
        member(self.support, "support", SUPPORT_STATES)

    def to_dict(self):
        return {"component_type": self.component_type, "package_format": self.package_format,
                "adapter_version": self.adapter_version, "harness_interface": self.harness_interface,
                "scope": self.scope, "activation": self.activation, "support": self.support}


PROFILE_FIELDS = ("engine_kind", "isolation", "placement", "fresh_instance_per_step", "supported_modes",
                  "supported_features", "enforced_limits", "native_controls", "network", "model_wire",
                  "native_tools", "required_effects", "compatibility")


@dataclass(frozen=True)
class ExecutorProfile:
    """The capability record of one step executor engine; projected, never a grant."""

    engine_kind: str
    isolation: str
    placement: str
    fresh_instance_per_step: str
    supported_modes: tuple
    supported_features: tuple
    enforced_limits: tuple
    native_controls: tuple
    network: str
    model_wire: str
    native_tools: str
    required_effects: tuple
    compatibility: tuple

    def __post_init__(self):
        set_ = object.__setattr__
        identifier(self.engine_kind, "engine_kind")
        member(self.isolation, "isolation", ISOLATIONS)
        member(self.placement, "placement", PLACEMENTS)
        member(self.fresh_instance_per_step, "fresh_instance_per_step", FRESH_INSTANCE_STATES)
        set_(self, "supported_modes", sequence(self.supported_modes, "supported_modes",
                                               lambda v, n: member(v, n, engine_modes()), nonempty=True))
        set_(self, "supported_features", sequence(self.supported_features, "supported_features", identifier))
        set_(self, "enforced_limits", sequence(self.enforced_limits, "enforced_limits",
                                               lambda v, n: member(v, n, LIMITS)))
        set_(self, "native_controls", sequence(self.native_controls, "native_controls", identifier))
        member(self.network, "network", NETWORK_NEEDS)
        identifier(self.model_wire, "model_wire")
        member(self.native_tools, "native_tools", NATIVE_TOOLS)
        set_(self, "required_effects", sequence(self.required_effects, "required_effects",
                                                lambda v, n: member(v, n, EFFECTS)))
        set_(self, "compatibility", _typed(self.compatibility, CompatibilityEntry, "compatibility"))
        _unique(self.compatibility, lambda item: (item.component_type, item.package_format, item.scope),
                "compatibility")
        if self.placement == IN_PROCESS and self.isolation not in ("none", "unverified"):
            raise EngineRecordError("invalid_field", "an in-process engine has no process isolation")

    def to_dict(self) -> dict:
        record = {"record_type": EXECUTOR_PROFILE_RECORD_TYPE}
        for name in PROFILE_FIELDS:
            value = getattr(self, name)
            record[name] = ([item.to_dict() for item in value] if name == "compatibility"
                            else list(value) if isinstance(value, tuple) else value)
        return record

    @classmethod
    def from_dict(cls, record) -> "ExecutorProfile":
        record = read_record(dict(record) if type(record) is not dict else record, EXECUTOR_PROFILE_RECORD_TYPE,
                             PROFILE_FIELDS)
        if type(record["compatibility"]) not in (list, tuple):
            raise EngineRecordError("invalid_field", "compatibility must be a list")
        entries = tuple(CompatibilityEntry(**read_part(plain(item) if not isinstance(item, dict) else item,
                                                       "compatibility entry", tuple(
                                                           CompatibilityEntry.__dataclass_fields__)))
                        for item in record["compatibility"])
        return cls(**{name: (tuple(record[name]) if isinstance(record[name], (list, tuple)) else record[name])
                      for name in PROFILE_FIELDS if name != "compatibility"}, compatibility=entries)

    def support_for(self, component_type: str) -> str:
        """The strongest support any entry declares for one component type, or unsupported."""
        states = [item.support for item in self.compatibility if item.component_type == component_type]
        return min(states, key=SUPPORT_STATES.index) if states else "unsupported"


@dataclass(frozen=True)
class StepServices:
    """Run-scoped services the envelope passes to one engine attempt; none is a grant.

    ``broker`` is the owning Loop's model broker, bound only when the step
    authorizes model calls; ``attempt_loop`` is the attempt's Spawned Loop;
    ``decoy_binds`` are read-only files a qualification plants outside the step."""

    work_root: str
    broker: object = None
    attempt_loop: object = None
    keep_launch_folders: bool = False
    decoy_binds: tuple = ()

    def __post_init__(self):
        text(self.work_root, "work_root", 4096)
        if self.broker is not None and not callable(self.broker):
            raise EngineRecordError("invalid_field", "a broker is callable")
        flag(self.keep_launch_folders, "keep_launch_folders")
        object.__setattr__(self, "decoy_binds", tuple(self.decoy_binds))


def unmet_step_requirements(request: StepRunRequest, profile: ExecutorProfile) -> tuple:
    """Every reason one executor profile cannot serve one step, compared without dispatch.

    A declaration can only make an engine ineligible; it never widens what
    the step's owning Loop granted."""
    requirements, missing = request.requirements, []
    if request.mode not in profile.supported_modes:
        missing.append("mode:" + request.mode)
    missing += ["feature:" + item for item in requirements.required_features
                if item not in profile.supported_features]
    missing += ["preemptive_limit:" + item for item in requirements.required_limits
                if item not in profile.enforced_limits]
    tools_or_files = "writes_fs" in request.granted_effects or bool(request.material and any(
        item.kind == "protocol_server" for item in request.material))
    if tools_or_files and profile.native_tools == "none" and profile.placement != IN_PROCESS:
        missing.append("tools_or_file_effects:text_only_engine")
    for kind in sorted({item.kind for item in request.material}):
        if profile.support_for(kind) not in USABLE_SUPPORT:
            missing.append("component:" + kind)
    if request.authorize_model_calls and profile.model_wire == "none":
        missing.append("model_wire:none")
    if request.procedure_ref and profile.placement not in (IN_PROCESS, FRESH_PROCESS):
        missing.append("procedure:placement")
    return tuple(missing)


def self_test():
    """Run the step edge checks."""
    from .records_checks import self_test as run_records_checks
    return run_records_checks()
