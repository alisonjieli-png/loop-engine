"""Typed embedding boundary for host-owned capabilities and verification.

Registration is explicit application authority, not learned intelligence.
Operations use the existing CapabilityDirectory and canonical Loop wrappers.
The embedding host owns its sandbox, state-snapshot semantics, and gate code;
this adapter does not make arbitrary Python callbacks an operating-system sandbox.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Callable

from jsonschema import Draft202012Validator

from ..loop.capability_loops import run_capability_as_loop
from ..loop.effect_approval import (
    ApprovalAction, ApprovalDecision, ApprovalRequest, EffectApprovalService, EffectClass, EffectSpec,
)
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import LoopConfig, StepOutcome
from ..loop.runtime_context import (
    CustomPluginsPort, InternalRuntimeMechanics, LoopRuntimeContext,
)
from .capability_directory import (
    CapabilityDirectory, CapabilityInvocationPolicy, capability_handshake_digest,
)
from .context_artifacts import ContextArtifactRef
from .runtime_observer import RuntimeObservationServices


class HostRuntimeError(ValueError):
    """A host binding, operation, or issued observation cannot be admitted."""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _state(value):
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise HostRuntimeError("host snapshot must return a lowercase SHA-256 identity")
    return value


def _schema(value):
    if not isinstance(value, dict):
        raise HostRuntimeError("host schemas must be explicit JSON Schema objects")
    frozen = json.loads(_json(value))
    def check(item):
        if isinstance(item, dict):
            for key, entry in item.items():
                if key in ("$ref", "$dynamicRef") and (
                        not isinstance(entry, str) or not entry.startswith("#")):
                    raise HostRuntimeError("host schemas must be self-contained")
                check(entry)
        elif isinstance(item, list):
            for entry in item:
                check(entry)
    check(frozen)
    Draft202012Validator.check_schema(frozen)
    return frozen


def _validate(schema, value, label):
    _json(value)
    if next(Draft202012Validator(schema).iter_errors(value), None) is not None:
        raise HostRuntimeError(label + " does not match the registered schema")


@dataclass(frozen=True)
class HostOperationBinding:
    """One explicitly selected directory endpoint and its actual value contracts."""

    surface: str
    operation: str
    input_schema: dict
    output_schema: dict
    effect_factory: Callable = field(repr=False, compare=False)
    implementation_ref: str
    permission_names: tuple[str, ...] = ()

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() for v in (
                self.surface, self.operation, self.implementation_ref)):
            raise HostRuntimeError("host operation needs exact registration identities")
        if not callable(self.effect_factory):
            raise HostRuntimeError("host operation needs a trusted exact-effect builder")
        if (not isinstance(self.permission_names, tuple)
                or len(set(self.permission_names)) != len(self.permission_names)
                or any(not isinstance(v, str) or not v.strip() for v in self.permission_names)):
            raise HostRuntimeError("host permission names must be explicit unique scoped labels")
        object.__setattr__(self, "input_schema", _schema(self.input_schema))
        object.__setattr__(self, "output_schema", _schema(self.output_schema))

    @property
    def capability_ref(self):
        return "host:" + self.surface + ":" + self.operation

    def describe(self):
        return {"surface": self.surface, "operation": self.operation,
                "capability_ref": self.capability_ref,
                "input_schema": deepcopy(self.input_schema),
                "output_schema": deepcopy(self.output_schema),
                "permission_names": list(self.permission_names),
                "implementation_ref": self.implementation_ref}


@dataclass(frozen=True)
class HostRuntimeBinding:
    """One caller-owned integration; no alternate registry or execution runtime.

    snapshot is a trusted host read returning the current subject identity.
    It must include verifier inputs/gates and exclude only declared volatile
    material. The host must enforce transactional preconditions at effect time.
    authorize cannot be supplied by a model response. It approves each exact
    scope, argument, state, and registration-bound effect or refuses it.
    """

    directory: CapabilityDirectory = field(repr=False, compare=False)
    operations: tuple[HostOperationBinding, ...]
    verifier: HostOperationBinding
    authorize: Callable = field(repr=False, compare=False)
    snapshot: Callable = field(repr=False, compare=False)
    scope_ref: str
    share_outputs_with_model: bool = False
    _manifest: str = field(init=False, repr=False, compare=False)
    _endpoints: tuple = field(init=False, repr=False, compare=False)
    _controls: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if self.share_outputs_with_model is not True:
            raise HostRuntimeError(
                "host integration requires an explicit share_outputs_with_model grant")
        if not isinstance(self.directory, CapabilityDirectory):
            raise HostRuntimeError("host registration requires CapabilityDirectory")
        if (not isinstance(self.operations, tuple) or not self.operations
                or any(not isinstance(item, HostOperationBinding) for item in self.operations)
                or not isinstance(self.verifier, HostOperationBinding)):
            raise HostRuntimeError("host needs typed operations and a separate verifier")
        specs = (*self.operations, self.verifier)
        if len({item.capability_ref for item in specs}) != len(specs):
            raise HostRuntimeError("host operations and verifier cannot share an endpoint")
        if not callable(self.authorize) or not callable(self.snapshot) or not self.scope_ref.strip():
            raise HostRuntimeError("host needs authority, snapshot, and explicit scope")
        endpoints = []
        for item in specs:
            handshake = self.directory.handshake(item.surface)
            endpoint = self.directory._ep.get((item.surface, item.operation))
            if (not handshake.supports(item.operation) or endpoint is None
                    or not callable(endpoint.fn)):
                raise HostRuntimeError("host endpoint is not currently executable")
            if self.directory._fallback_for(item.surface, item.operation) is not None:
                raise HostRuntimeError("host effects cannot use implicit directory fallback")
            if handshake.max_response_bytes <= 0:
                raise HostRuntimeError("host handshake must declare its response byte allowance")
            endpoints.append((endpoint, endpoint.fn, item.effect_factory))
        if any(item[1] is endpoints[-1][1] for item in endpoints[:-1]):
            raise HostRuntimeError("host verifier must not be the action implementation")
        object.__setattr__(self, "_endpoints", tuple(endpoints))
        object.__setattr__(self, "_controls", (self.authorize, self.snapshot))
        object.__setattr__(self, "_manifest", _json(self._description()))

    def _description(self):
        return {"record_type": "host_runtime_binding/v1", "scope_ref": self.scope_ref,
                "operations": [{**item.describe(), "handshake":
                    self.directory.handshake(item.surface).describe()}
                    for item in self.operations],
                "verifier": {**self.verifier.describe(), "handshake":
                    self.directory.handshake(self.verifier.surface).describe()},
                "authority": "explicit_host_registration",
                "share_outputs_with_model": self.share_outputs_with_model,
                "snapshot_authority": "host_attested",
                "sandbox_authority": "host_owned"}

    def validate(self):
        if (self.authorize is not self._controls[0]
                or self.snapshot is not self._controls[1]):
            raise HostRuntimeError("host authority or snapshot binding changed")
        if _json(self._description()) != self._manifest:
            raise HostRuntimeError("host registration changed after binding")
        for spec, (endpoint, function, factory) in zip(
                (*self.operations, self.verifier), self._endpoints):
            if (self.directory._ep.get((spec.surface, spec.operation)) is not endpoint
                    or endpoint.fn is not function or spec.effect_factory is not factory
                    or self.directory._fallback_for(spec.surface, spec.operation) is not None):
                raise HostRuntimeError("host executable binding or fallback changed")

    def summary(self):
        self.validate()
        value = json.loads(self._manifest)
        return {**value, "binding_digest": hashlib.sha256(self._manifest.encode()).hexdigest()}

    def supports(self, capability_ref):
        self.validate()
        return any(item.capability_ref == capability_ref for item in self.operations)

    def descriptors(self):
        self.validate()
        return tuple({"capability_ref": item.capability_ref,
                      "purpose": self.directory.handshake(item.surface).functionality,
                      "arguments": deepcopy(item.input_schema),
                      "required_permissions": list(item.permission_names),
                      "permission_scope": self.scope_ref,
                      "effects": list(self.directory.handshake(item.surface).effects),
                      "authority": "each exact invocation requires host approval",
                      "binding_digest": self.summary()["binding_digest"]}
                     for item in self.operations)

    def permissions_for(self, capability_ref):
        self.validate()
        return next((item.permission_names for item in self.operations
                     if item.capability_ref == capability_ref), ())

    def runtime_context(self, base_context):
        if not isinstance(base_context, LoopRuntimeContext):
            raise HostRuntimeError("host context requires the resolved base runtime context")
        if base_context.custom_plugins is not None:
            raise HostRuntimeError("host context must not replace another installed plugin port")
        from dataclasses import replace
        return replace(base_context, custom_plugins=CustomPluginsPort(
            "host_runtime", self.directory,
            tuple(item.capability_ref for item in (*self.operations, self.verifier))))


@dataclass(frozen=True)
class HostOperationRequest:
    capability_ref: str
    arguments: dict

    def __post_init__(self):
        if not isinstance(self.capability_ref, str) or not self.capability_ref:
            raise HostRuntimeError("host operation requires its registered reference")
        if not isinstance(self.arguments, dict):
            raise HostRuntimeError("host arguments must be a JSON object")
        object.__setattr__(self, "arguments", json.loads(_json(self.arguments)))


@dataclass(frozen=True)
class HostInvocation:
    """Exact host callback input; metadata cannot be forged by model arguments."""

    invocation_id: str
    scope_ref: str
    state_ref: str
    arguments: dict

    def to_dict(self):
        return {"record_type": "host_invocation/v1", "invocation_id": self.invocation_id,
                "scope_ref": self.scope_ref, "state_ref": self.state_ref,
                "arguments": deepcopy(self.arguments)}


def _host(services):
    host = getattr(services.dependencies, "host_runtime", None)
    if not isinstance(host, HostRuntimeBinding):
        raise HostRuntimeError("no typed host runtime is installed")
    host.validate()
    return host


def _capture(services, value, kind):
    return services.artifacts.capture(
        _json(value), media_type="application/json", artifact_kind=kind).raw.to_dict()


def _load(services, reference):
    return json.loads(services.artifacts.store.get_text(ContextArtifactRef.from_dict(reference)))


def _approve(host, spec, invocation, owner):
    invocation_digest = _digest(invocation.to_dict())
    proposed = spec.effect_factory(invocation)
    if not isinstance(proposed, EffectSpec):
        raise HostRuntimeError("host effect builder did not return an EffectSpec")
    if _digest(invocation.to_dict()) != invocation_digest:
        raise HostRuntimeError("host effect builder changed admitted arguments")
    mutating = proposed.effect_class not in (EffectClass.LOCAL_READ, EffectClass.NETWORK_READ)
    if mutating:
        started = {item["invocation_id"] for item in owner.ledger.events
                   if item.get("custom_kind") == "host_invocation_started"
                   and item.get("scope_ref") == host.scope_ref
                   and item.get("mutating") is True}
        completed = {item["invocation_id"] for item in owner.ledger.events
                     if item.get("custom_kind") == "host_invocation_finished"
                     and item.get("outcome_known") is True}
        if started - completed:
            raise HostRuntimeError("an earlier host effect has unknown outcome; reconciliation is required")
    # Reconstruct the exact envelope after the host's effect proposal. It cannot
    # omit or override the arguments, scope, state or registry identity binding.
    parameters = dict(proposed.parameters)
    required = {"host_invocation_digest": invocation_digest,
                "host_binding_digest": host.summary()["binding_digest"]}
    if set(parameters) & set(required):
        raise HostRuntimeError("host effect uses reserved binding fields")
    effect = EffectSpec(proposed.effect_class, proposed.operation, proposed.target,
                        tuple(sorted({**parameters, **required}.items())))
    approvals = EffectApprovalService(runtime=RuntimeObservationServices(
        parent=owner, ledger=owner.ledger))
    approval = ApprovalRequest.create(owner.loop_id, effect,
                                      "Invoke the selected host capability under its exact scope.")
    pending = approvals.create(approval)
    decision = host.authorize(approval)
    if (not isinstance(decision, ApprovalDecision)
            or decision.action is not ApprovalAction.APPROVE
            or decision.request_id != approval.request_id):
        raise PermissionError("host refused the exact operation")
    if _digest(invocation.to_dict()) != invocation_digest:
        raise HostRuntimeError("host approval changed admitted arguments")
    approvals.resume(pending.pending, pending.resume_token, decision)
    if _state(host.snapshot()) != invocation.state_ref:
        raise HostRuntimeError("host state changed before the approved invocation")
    host.validate()
    approvals.consume(approval.request_id, effect)
    return approval.request_id, _digest(effect.to_dict()), mutating


def _invoke(host, spec, arguments, services, owner):
    host.validate()
    arguments = json.loads(_json(arguments))
    _validate(spec.input_schema, arguments, "host input")
    before = _state(host.snapshot())
    invocation = HostInvocation(
        "host-call:" + uuid.uuid4().hex,
        host.scope_ref, before, arguments)
    admitted_digest = _digest(invocation.to_dict())
    approval_ref, effect_digest, mutating = _approve(host, spec, invocation, owner)
    # Use an independent copy after authorization. Host hooks cannot rewrite
    # the model's admitted arguments or approval-bound request in place.
    if _digest(invocation.to_dict()) != admitted_digest:
        raise HostRuntimeError("host invocation changed during approval")
    owner.ledger.record(loop_id=owner.loop_id, event="custom",
                        custom_kind="host_invocation_started", invocation_id=invocation.invocation_id,
                        scope_ref=host.scope_ref, mutating=mutating, effect_digest=effect_digest)
    known = False
    try:
        dispatched = run_capability_as_loop(
            host.directory, spec.surface, spec.operation,
            request=deepcopy(invocation), parent=owner,
            invocation_policy=CapabilityInvocationPolicy(
                False, capability_handshake_digest(host.directory.handshake(spec.surface)),
                next(function for bound, (_, function, _) in zip(
                    (*host.operations, host.verifier), host._endpoints)
                    if bound.capability_ref == spec.capability_ref)))
        host.validate()
        value = dispatched["value"]
        _validate(spec.output_schema, value, "host output")
        size = len(_json(value).encode())
        if size > host.directory.handshake(spec.surface).max_response_bytes:
            raise HostRuntimeError("host output exceeded its declared response allowance")
        after = _state(host.snapshot())
        known = dispatched["ok"] is True
    finally:
        owner.ledger.record(loop_id=owner.loop_id, event="custom",
                            custom_kind="host_invocation_finished", invocation_id=invocation.invocation_id,
                            scope_ref=host.scope_ref, outcome_known=known)
    return {"ok": dispatched["ok"] is True, "value": deepcopy(value),
            "state_before": before, "state_after": after,
            "invocation_id": invocation.invocation_id,
            "approval_ref": approval_ref, "effect_digest": effect_digest,
            "capability_loop_id": dispatched["loop_id"],
            "binding_digest": host.summary()["binding_digest"],
            "snapshot_authority": "host_attested"}


def _issued(services, owner, value, event, digest_field):
    value[digest_field] = _digest(value)
    reference = _capture(services, value, event)
    owner.ledger.record(loop_id=owner.loop_id, event="custom", custom_kind=event,
                        record_digest=value[digest_field], artifact_ref=reference,
                        run_id=services.run_id)
    return value


def _validate_issued(value, services, owner, event, digest_field):
    body = {key: item for key, item in value.items() if key != digest_field}
    if _digest(body) != value.get(digest_field):
        raise HostRuntimeError("issued host record changed")
    events = [item for item in owner.ledger.events if item.get("custom_kind") == event
              and item.get("record_digest") == value[digest_field]
              and item.get("run_id") == services.run_id]
    if len(events) != 1 or _load(services, events[0]["artifact_ref"]) != value:
        raise HostRuntimeError("host record is not bound to one issued event")


def invoke_host_operation(request, services, owner_loop):
    """Perform one authorized host action without constructing a Python project."""
    if not isinstance(request, HostOperationRequest):
        raise HostRuntimeError("host operation requires its typed request")
    host = _host(services)
    if not host.supports(request.capability_ref):
        raise HostRuntimeError("host operation is not available to the model")
    spec = next(item for item in host.operations
                if item.capability_ref == request.capability_ref)
    result = _invoke(host, spec, request.arguments, services, owner_loop)
    record = {"record_type": "host_operation_result/v1", "run_id": services.run_id,
              "scope_ref": host.scope_ref, "capability_ref": request.capability_ref,
              "arguments_digest": _digest(request.arguments), **result,
              "artifact_refs": [], "acceptance_granted": False}
    record = _issued(services, owner_loop, record, "host_operation_recorded", "result_digest")
    services.host_results.append(deepcopy(record))
    return record


def verify_host_result(task, result, services, owner_loop):
    """Invoke the host's pre-registered gates under a separate verifier Loop."""
    host = _host(services)
    _validate_issued(result, services, owner_loop, "host_operation_recorded", "result_digest")
    config = LoopConfig(framework="custom", custom_steps=("verify",), power="light",
                        allowable_modes=("deterministic",), preferred_modes=("deterministic",),
                        exit_condition="steps_complete")
    loop = owner_loop.spawn(
        "verify host-owned task state against registered gates", config,
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.verifier"),
        relationship=LoopRelationship.spawned_by(owner_loop.loop_id))
    holder = {}

    def handler(active, _step, _context):
        report = {"record_type": "host_verification_report/v1", "status": "unavailable",
                  "task_complete": False, "task_digest": hashlib.sha256(task.encode()).hexdigest(),
                  "subject_digest": result["result_digest"], "state_ref": result["state_after"],
                  "verifier_loop_id": active.loop_id, "producer_loop_id": owner_loop.loop_id,
                  "binding_digest": host.summary()["binding_digest"],
                  "notes": "Host verification is not complete.", "observations": {},
                  "grants_promotion": False}
        try:
            if result["ok"] is not True or _state(host.snapshot()) != result["state_after"]:
                raise HostRuntimeError("host result is failed or no longer the current subject")
            execution = _invoke(host, host.verifier, {
                "task": task, "result": deepcopy(result), "state_ref": result["state_after"]},
                services, active)
            value = execution["value"]
            if (not isinstance(value, dict) or type(value.get("passed")) is not bool
                    or type(value.get("task_complete")) is not bool
                    or not isinstance(value.get("observations"), dict)
                    or not isinstance(value.get("notes"), str)):
                raise HostRuntimeError("host verifier must return explicit checks and completeness")
            if execution["state_before"] != execution["state_after"]:
                raise HostRuntimeError("host verifier changed the subject it evaluated")
            report.update(status="passed" if value["passed"] and execution["ok"] else "failed",
                          task_complete=value["task_complete"] and value["passed"] and execution["ok"],
                          notes=value["notes"], observations=value["observations"],
                          execution=execution)
        except Exception as exc:
            report.update(error_type=type(exc).__name__, notes=str(exc))
        holder["report"] = _issued(services, active, report,
                                    "host_verification_recorded", "report_digest")
        services.host_verification_records.append(deepcopy(holder["report"]))
        return StepOutcome("host verification observation recorded", "deterministic", 1.0)

    loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    return holder["report"]


def validate_host_verification(report, task, result, services, owner_loop):
    host = _host(services)
    _validate_issued(result, services, owner_loop, "host_operation_recorded", "result_digest")
    _validate_issued(report, services, owner_loop, "host_verification_recorded", "report_digest")
    if (report.get("status") != "passed"
            or report.get("subject_digest") != result["result_digest"]
            or report.get("task_digest") != hashlib.sha256(task.encode()).hexdigest()
            or report.get("binding_digest") != host.summary()["binding_digest"]
            or result.get("binding_digest") != report["binding_digest"]
            or report.get("producer_loop_id") != owner_loop.loop_id
            or report.get("verifier_loop_id") == owner_loop.loop_id
            or _state(host.snapshot()) != report.get("state_ref")
            or report["state_ref"] != result["state_after"]):
        raise HostRuntimeError("host verification does not bind the current task and result")
    initial = [item for item in owner_loop.ledger.events if item.get("event") == "init"
               and item.get("loop_id") == report["verifier_loop_id"]]
    if (len(initial) != 1 or initial[0].get("role") != "practitioner"
            or initial[0].get("profile_id") != "practitioner.verifier"):
        raise HostRuntimeError("host verification has no canonical verifier identity")


def self_test():
    from .adaptive_host_runtime_checks import host_contract_checks
    return host_contract_checks()
