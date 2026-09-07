"""Typed, serial dependency handoff inside the existing Practitioner runtime.

Assignments and frames are passive run-local records. Planning uses the
existing PlanDefinition compiler; values use LoopValue, LoopPortValue, and
InformationResolver. This module creates no executable runtime or store.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import re

from ..loop.atomic_primitives import LoopValue, LoopValueCreateRequest, LoopValueRef
from ..loop.delegation_runtime import (
    ContextVisibilityPolicy, DelegationBudget, DelegationSpec, LoopPortValue,
    SpawnedTaskId)
from ..loop.loop_contract import (
    LoopConnectionSpec, LoopContract, LoopPortBinding,
    execution_mode_for_runtime_mode, validate_loop_connection)
from ..loop.loop_profile_catalog import LoopProfileRef
from ..scheduling import ConcurrencyContract
from .development_planning import (
    PlanDefinition, PlanningAuthority, RequirementVerificationContract,
    ResolutionDisposition, TaskSliceDefinition, compile_execution_waves)
from .host_runtime import _schema, _validate
from .information_access import (
    InformationAccessOperation, InformationAccessRequest, InformationDurability,
    InformationPublicationRequest, InformationResolver, InformationScope,
    InlineInformationAdapter)
from .runtime_observer import RuntimeObservationServices


ASSIGNMENT_KEY = "_adaptive_spawned_assignment"
ASSIGNMENT_RECORD_TYPE = "adaptive_spawned_assignment/v1"
BASE_ASSIGNMENT_FIELDS = frozenset({"objective", "constraints", "success_criteria"})
EXTENDED_ASSIGNMENT_FIELDS = BASE_ASSIGNMENT_FIELDS | {
    "record_type", "task_id", "depends_on", "inputs", "output_contract"}


class DependencyBindingError(ValueError):
    """A typed dependency could not be admitted or safely consumed."""

    def __init__(self, message, disposition=ResolutionDisposition.MALFORMED):
        self.disposition = ResolutionDisposition(disposition)
        super().__init__(message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _result_digest(value):
    """Use the issuing scope's result identity, including its wire encoding."""
    from .adaptive_practitioner_scope import summary_digest
    return summary_digest(value)


def _fields(value, required, label):
    if type(value) is not dict or set(value) != set(required):
        raise DependencyBindingError(label + ": fields do not match the versioned contract")


def _text(value, label):
    if type(value) is not str or not value.strip():
        raise DependencyBindingError(label + ": expected nonempty text")
    return value


def _versioned(value, label):
    value = _text(value, label)
    if re.fullmatch(r".+/v[1-9][0-9]*", value) is None:
        raise DependencyBindingError(label + ": expected an exact versioned reference")
    return value


def _task_id(value):
    try:
        return str(SpawnedTaskId(_text(value, "task_id")))
    except (TypeError, ValueError, RuntimeError) as exc:
        raise DependencyBindingError("task_id: invalid planned task identity") from exc


def _structural_schema(value):
    """Qualify model-proposed value schemas for this bounded adapter.

    Regex evaluation and reference resolution are not installed dependency
    validation capabilities. Annotation fields never acquire runtime effects.
    """
    allowed = {
        "type", "properties", "required", "additionalProperties", "items", "prefixItems",
        "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties",
        "minLength", "maxLength", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
        "multipleOf", "enum", "const", "allOf", "anyOf", "oneOf", "not",
        "title", "description", "$comment", "default", "examples",
    }

    def inspect(schema):
        if type(schema) is bool:
            return
        if type(schema) is not dict or set(schema) - allowed:
            raise DependencyBindingError("output.schema uses an unsupported structural-schema keyword")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for nested in properties.values():
                inspect(nested)
        for name in ("additionalProperties", "items", "not"):
            if name in schema:
                inspect(schema[name])
        for name in ("prefixItems", "allOf", "anyOf", "oneOf"):
            if isinstance(schema.get(name), list):
                for nested in schema[name]:
                    inspect(nested)

    inspect(value)
    return _schema(value)


@dataclass(frozen=True)
class SpawnedOutputContract:
    role: str
    value_contract_ref: str
    schema_json: str
    result_path: tuple[str | int, ...] = ()

    def __post_init__(self):
        _versioned(self.role, "output.role")
        _versioned(self.value_contract_ref, "output.value_contract_ref")
        try:
            object.__setattr__(self, "schema_json", _json(_structural_schema(json.loads(self.schema_json))))
        except Exception as exc:
            raise DependencyBindingError("output.schema: invalid self-contained JSON Schema") from exc
        path = tuple(self.result_path)
        if any(not (type(part) is str or type(part) is int and part >= 0) for part in path):
            raise DependencyBindingError("output.result_path: use exact object keys or nonnegative array indexes")
        object.__setattr__(self, "result_path", path)

    @classmethod
    def from_mapping(cls, value):
        _fields(value, {"role", "value_contract_ref", "schema", "result_path"}, "output_contract")
        if type(value["result_path"]) is not list:
            raise DependencyBindingError("output.result_path: expected array")
        return cls(value["role"], value["value_contract_ref"], _json(value["schema"]),
                   tuple(value["result_path"]))

    @property
    def schema_digest(self):
        return hashlib.sha256(self.schema_json.encode()).hexdigest()

    @property
    def bound_contract_ref(self):
        return self.value_contract_ref + "#sha256:" + self.schema_digest

    def to_dict(self):
        return {"role": self.role, "value_contract_ref": self.value_contract_ref,
                "schema": json.loads(self.schema_json), "result_path": list(self.result_path)}

    def select(self, result):
        value = result
        try:
            for part in self.result_path:
                if type(part) is str and type(value) is dict:
                    value = value[part]
                elif type(part) is int and type(value) is list:
                    value = value[part]
                else:
                    raise KeyError()
            _validate(json.loads(self.schema_json), value, "dependency output")
        except Exception as exc:
            raise DependencyBindingError("dependency output does not satisfy its declared path and schema",
                                         ResolutionDisposition.INCOMPATIBLE) from exc
        return value


@dataclass(frozen=True)
class SpawnedInputBinding:
    role: str
    source_task_id: str
    source_role: str
    value_contract_ref: str
    delivery: str = "value"

    def __post_init__(self):
        _versioned(self.role, "input.role")
        _task_id(self.source_task_id)
        _versioned(self.source_role, "input.source_role")
        _versioned(self.value_contract_ref, "input.value_contract_ref")
        if self.delivery not in ("value", "reference"):
            raise DependencyBindingError("input.delivery: expected value or reference")

    @classmethod
    def from_mapping(cls, value):
        _fields(value, {"role", "source_task_id", "source_role", "value_contract_ref", "delivery"}, "input")
        return cls(**value)

    def to_dict(self):
        return {name: getattr(self, name) for name in (
            "role", "source_task_id", "source_role", "value_contract_ref", "delivery")}


@dataclass(frozen=True)
class SpawnedAssignment:
    task_id: str
    depends_on: tuple[str, ...]
    inputs: tuple[SpawnedInputBinding, ...]
    output_contract: SpawnedOutputContract | None

    def __post_init__(self):
        _task_id(self.task_id)
        dependencies = tuple(self.depends_on)
        if len(dependencies) != len(set(dependencies)):
            raise DependencyBindingError("depends_on: repeated task identity")
        for value in dependencies:
            _task_id(value)
        inputs = tuple(self.inputs)
        if any(type(value) is not SpawnedInputBinding for value in inputs):
            raise DependencyBindingError("inputs require typed binding records")
        if len({value.role for value in inputs}) != len(inputs):
            raise DependencyBindingError("inputs: each consumer role must be bound once")
        if self.output_contract is not None and type(self.output_contract) is not SpawnedOutputContract:
            raise DependencyBindingError("output_contract requires its typed record")
        object.__setattr__(self, "depends_on", dependencies)
        object.__setattr__(self, "inputs", inputs)

    @classmethod
    def from_mapping(cls, value):
        _fields(value, EXTENDED_ASSIGNMENT_FIELDS, "spawned_assignment")
        if value["record_type"] != ASSIGNMENT_RECORD_TYPE:
            raise DependencyBindingError("spawned assignment version is unsupported")
        if type(value["depends_on"]) is not list or type(value["inputs"]) is not list:
            raise DependencyBindingError("depends_on and inputs must be arrays")
        return cls(value["task_id"], tuple(value["depends_on"]),
                   tuple(SpawnedInputBinding.from_mapping(item) for item in value["inputs"]),
                   None if value["output_contract"] is None
                   else SpawnedOutputContract.from_mapping(value["output_contract"]))

    def to_dict(self):
        return {"record_type": ASSIGNMENT_RECORD_TYPE, "task_id": self.task_id,
                "depends_on": list(self.depends_on),
                "inputs": [item.to_dict() for item in self.inputs],
                "output_contract": self.output_contract.to_dict() if self.output_contract else None}


def assignment_for(spec):
    """Only admitted typed records may use the reserved ProblemSpec field."""
    if type(spec.seed_facts) is not dict:
        raise DependencyBindingError("ProblemSpec seed_facts must be an object")
    if any(key.startswith(ASSIGNMENT_KEY) and key != ASSIGNMENT_KEY for key in spec.seed_facts
           if isinstance(key, str)):
        raise DependencyBindingError("reserved dependency metadata key collision")
    value = spec.seed_facts.get(ASSIGNMENT_KEY)
    if ASSIGNMENT_KEY in spec.seed_facts and type(value) is not SpawnedAssignment:
        raise DependencyBindingError("reserved dependency metadata requires a runtime-admitted typed assignment")
    return value


def assignment_task_view(spec):
    assignment = assignment_for(spec)
    return assignment.to_dict() if assignment is not None else None


def compile_assignments(specs, goal):
    """Validate the entire passive plan before any spawned execution."""
    assignments = tuple(assignment_for(spec) for spec in specs)
    if not any(assignments):
        return tuple(range(len(specs))), ""
    if not all(assignments):
        raise DependencyBindingError("one dependency plan cannot mix named and legacy assignments")
    by_id = {item.task_id: item for item in assignments}
    if len(by_id) != len(assignments):
        raise DependencyBindingError("planned task identities must be unique")
    schemas = {}
    for item in assignments:
        if set(item.depends_on) - set(by_id):
            raise DependencyBindingError("depends_on names an unknown task")
        if item.output_contract:
            output = item.output_contract
            prior = schemas.setdefault(output.value_contract_ref, output.schema_digest)
            if prior != output.schema_digest:
                raise DependencyBindingError("one value contract reference cannot name different schemas")
        for binding in item.inputs:
            producer = by_id.get(binding.source_task_id)
            if producer is None or binding.source_task_id not in item.depends_on:
                raise DependencyBindingError("each input must name an explicit same-plan dependency")
            output = producer.output_contract
            if (output is None or output.role != binding.source_role
                    or output.value_contract_ref != binding.value_contract_ref):
                raise DependencyBindingError("input does not match its producer's exact output contract",
                                             ResolutionDisposition.INCOMPATIBLE)
            producer_contract = LoopContract("dependency producer", "code_only", output_roles=(output.role,))
            consumer_contract = LoopContract("dependency consumer", "code_only",
                input_roles=(binding.role,), output_roles=("kernel_run/v1",))
            connection = validate_loop_connection(LoopConnectionSpec(
                producer_contract, consumer_contract,
                (LoopPortBinding(binding.source_role, binding.role),)))
            if not connection.compatible:
                raise DependencyBindingError("dependency roles require an explicit compatible connection",
                                             ResolutionDisposition.INCOMPATIBLE)
    # Slot identities preserve declared order among equally ready tasks.
    slots = {item.task_id: f"slot.{index:08d}" for index, item in enumerate(assignments)}
    slices = tuple(TaskSliceDefinition(
        slots[item.task_id], spec.objective,
        tuple("task:" + binding.source_task_id for binding in item.inputs),
        ((item.output_contract.bound_contract_ref,) if item.output_contract else ("kernel_run/v1",)),
        tuple(slots[name] for name in item.depends_on),
        tuple(RequirementVerificationContract(
            f"criterion.{index}.{number}", text, "independent_task_verification",
            ("issued_verification_record",), "unverified", True)
            for number, text in enumerate(spec.success_criteria)),
        ConcurrencyContract(exclusive_resources=("adaptive_model_session",)),
        ("practitioner.reference_nine_step",))
        for index, (item, spec) in enumerate(zip(assignments, specs)))
    plan = PlanDefinition("adaptive-dependency-plan", "task:" + _digest(goal), _digest(goal),
        goal, ("serial_adaptive_delegation",), (), PlanningAuthority.PARENT_LOOP_AUTHORIZED, (), slices)
    execution = compile_execution_waves(plan)
    index_by_slot = {slots[item.task_id]: index for index, item in enumerate(assignments)}
    identity = _digest({"record_type": "adaptive_dependency_plan/v1",
                        "ordering_plan_digest": plan.content_digest,
                        "assignments": [item.to_dict() for item in assignments]})
    return tuple(index_by_slot[name] for wave in execution.waves for name in wave), identity


@dataclass(frozen=True)
class BoundDependencyInput:
    port: LoopPortValue
    reference: LoopValueRef
    source_task_id: str
    schema_digest: str
    delivery: str

    def to_dict(self):
        result = {"role": self.port.role, "source_task_id": self.source_task_id,
                  "schema_digest": self.schema_digest, "delivery": self.delivery,
                  "value_ref": self.reference.to_dict()}
        if self.delivery == "value":
            result["value"] = deepcopy(self.port.value)
        return result


@dataclass
class SpawnedDependencyFrame:
    """Private state for one admitted serial batch, consumed by its Loop."""

    owner: object = field(repr=False)
    run_id: str
    plan_digest: str
    assignments: dict[str, SpawnedAssignment]
    starts: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    resolvers: dict = field(default_factory=dict, repr=False)

    def start(self, assignment, owner):
        if (self.assignments.get(assignment.task_id) != assignment
                or owner.relationship.spawned_by_loop_id != self.owner.loop_id
                or owner.identity.role.value != "practitioner" or owner.is_terminal
                or owner.ledger is not self.owner.ledger or assignment.task_id in self.starts):
            raise DependencyBindingError("dependency execution crossed its owning scope",
                                         ResolutionDisposition.UNAUTHORIZED)
        self.starts[assignment.task_id] = (owner.loop_id, owner.definition_ref.to_dict())

    def register(self, assignment, summary):
        expected = self.starts.get(assignment.task_id)
        definition = {"definition_id": summary.get("definition_id"),
                      "version": summary.get("definition_version"),
                      "content_digest": summary.get("definition_digest")}
        if (expected != (summary.get("loop_id"), definition)
                or summary.get("spawned_by_loop_id") != self.owner.loop_id
                or summary.get("dependency_plan_digest") != self.plan_digest
                or self.assignments.get(assignment.task_id) != assignment):
            raise DependencyBindingError("dependency producer identity changed", ResolutionDisposition.UNAUTHORIZED)
        if summary.get("task_complete") is not True or assignment.output_contract is None:
            self.results[assignment.task_id] = (summary, _result_digest(summary))
            return
        contract = assignment.output_contract
        value = contract.select(summary["accepted_result"]["result"])
        wrapped = LoopValue.create(deepcopy(value), LoopValueCreateRequest(
            contract.bound_contract_ref, contract.role, summary["loop_id"], _json(definition),
            source_refs=("run:" + self.run_id,), transformation_lineage=(summary["verification_record_digest"],)))
        # Validate the supported data domain without publishing an ambient grant.
        check = InlineInformationAdapter()
        check.store(InformationPublicationRequest(wrapped, check.adapter_id,
            InformationDurability.RUN, InformationScope.PRIVATE_LOOP, run_id=self.run_id))
        self.results[assignment.task_id] = (summary, _result_digest(summary))
        self.outputs[assignment.task_id] = (wrapped, summary, _result_digest(summary), contract.schema_digest)

    def resolve(self, assignment, consumer, *, request, spec):
        self.start(assignment, consumer)
        for dependency in assignment.depends_on:
            result = self.results.get(dependency)
            if result is None or result[0].get("task_complete") is not True:
                raise DependencyBindingError("prerequisite has not completed with verification", ResolutionDisposition.BLOCKED)
            if _result_digest(result[0]) != result[1]:
                raise DependencyBindingError("prerequisite result changed", ResolutionDisposition.STALE)
            if not any(event.get("custom_kind") == "adaptive_spawned_result_returned"
                       and event.get("spawned_loop_id") == result[0].get("loop_id")
                       and event.get("result_digest") == result[1]
                       and event.get("spawned_task_complete") is True
                       and event.get("loop_id") == self.owner.loop_id
                       for event in self.owner.ledger.events):
                raise DependencyBindingError("prerequisite lacks its issued completion", ResolutionDisposition.UNAUTHORIZED)
        resolver = InformationResolver(RuntimeObservationServices(parent=consumer, ledger=consumer.ledger))
        adapter = InlineInformationAdapter()
        resolver.register(adapter)
        bound = []
        for binding in assignment.inputs:
            wrapped, source, source_digest, schema_digest = self.outputs[binding.source_task_id]
            output = self.assignments[binding.source_task_id].output_contract
            definition = {"definition_id": source.get("definition_id"),
                          "version": source.get("definition_version"),
                          "content_digest": source.get("definition_digest")}
            if (source.get("spawned_by_loop_id") != self.owner.loop_id
                    or self.starts.get(binding.source_task_id) != (source.get("loop_id"), definition)
                    or wrapped.producer_loop_id != source.get("loop_id")
                    or wrapped.producer_definition_ref != _json(definition)):
                raise DependencyBindingError("dependency reference crossed its producer scope", ResolutionDisposition.UNAUTHORIZED)
            if (_result_digest(source) != source_digest or source.get("task_complete") is not True
                    or schema_digest != output.schema_digest
                    or wrapped.value_contract_ref != output.bound_contract_ref
                    or wrapped.semantic_role != binding.source_role):
                raise DependencyBindingError("dependency source or contract changed", ResolutionDisposition.STALE)
            if not any(event.get("custom_kind") == "adaptive_spawned_result_returned"
                       and event.get("spawned_loop_id") == source["loop_id"]
                       and event.get("result_digest") == source_digest
                       and event.get("loop_id") == self.owner.loop_id
                       for event in self.owner.ledger.events):
                raise DependencyBindingError("dependency result lacks its issued history binding", ResolutionDisposition.UNAUTHORIZED)
            # Revalidate the exact source selection before creating this consumer's grant.
            selected = output.select(source["accepted_result"]["result"])
            if LoopValue.create(selected, LoopValueCreateRequest(output.bound_contract_ref,
                    output.role, source["loop_id"], _json(definition))).to_ref() != wrapped.to_ref():
                raise DependencyBindingError("dependency value changed", ResolutionDisposition.STALE)
            resolver.publish(InformationPublicationRequest(wrapped, adapter.adapter_id,
                InformationDurability.ACTIVATION, InformationScope.ALLOWED_LOOPS,
                run_id=self.run_id, authorized_loop_ids=(consumer.loop_id,)))
            access = InformationAccessRequest(value_ref=wrapped.to_ref(), requester_loop_id=consumer.loop_id,
                purpose="consume an admitted dependency", requester_run_id=self.run_id)
            materialized = resolver.materialize(access)
            _validate(json.loads(output.schema_json), materialized.value, "dependency input")
            value = materialized.value if binding.delivery == "value" else wrapped.to_ref()
            bound.append(BoundDependencyInput(LoopPortValue(binding.role, value), wrapped.to_ref(),
                                             binding.source_task_id, schema_digest, binding.delivery))
        delegation = DelegationSpec(
            goal=spec.objective, profile=LoopProfileRef("practitioner.reference_nine_step"),
            contract=LoopContract("typed adaptive dependency inputs", execution_mode_for_runtime_mode(request.mode),
                input_roles=tuple(item.port.role for item in bound), output_roles=("kernel_run/v1",)),
            inputs=tuple(item.port for item in bound), mode=request.mode,
            budget=DelegationBudget(),
            context=ContextVisibilityPolicy(selected_refs=tuple(_json(item.reference.to_dict()) for item in bound)))
        self.resolvers[consumer.loop_id] = resolver
        return tuple(bound), delegation, resolver


def self_test():
    from .adaptive_practitioner_bindings_checks import run_checks
    return run_checks()
