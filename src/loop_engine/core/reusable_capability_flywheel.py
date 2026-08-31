"""Repository-native Reusable Capability Flywheel operations.

The unified catalog remains the authoritative record store. Code bodies remain
behind immutable ``ExternalPayloadRef`` values. Search projections are derived
and rebuildable. Every operation in this module enters through the canonical
``Loop`` runtime with an exact registered role profile.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from ..catalog.query import IntelligenceQuery
from ..loop.encapsulate import as_loop
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from .code_intelligence_assets import (
    CodeAssetAdmissionRecord,
    CodeAssetSpec,
    admit_code_asset,
)
from .reusable_capability_records import (
    CapabilityGeneralizationRecord,
    ReuseAssessment,
    ReuseOpportunityObserved,
    ReuseRecommendation,
    content_digest,
)


class ReusableCapabilityError(RuntimeError):
    """A reuse operation failed without changing trusted capability state."""


_CREATE_RECOMMENDATIONS = frozenset({
    ReuseRecommendation.CREATE_NEW_CAPABILITY_CANDIDATE,
    ReuseRecommendation.CREATE_NEW_VERSION_CANDIDATE,
    ReuseRecommendation.CREATE_ADAPTER_CANDIDATE,
    ReuseRecommendation.MERGE_INTO_EXISTING_CANDIDATE,
    ReuseRecommendation.CREATE_COMPOSITE_CANDIDATE,
})

_STATE_TRANSITIONS = {
    "candidate": frozenset({
        "validated", "quarantined", "rejected", "retired"}),
    "validated": frozenset({"registered", "quarantined", "retired"}),
    "registered": frozenset({
        "deprecated", "quarantined", "superseded", "retired"}),
    "deprecated": frozenset({"retired"}),
    "quarantined": frozenset({"retired"}),
    "rejected": frozenset({"retired"}),
    "superseded": frozenset({"registered", "retired"}),
    "retired": frozenset(),
}


def _relationship(parent, role: LoopRole, kind: str) -> LoopRelationship:
    if parent is None:
        return LoopRelationship.starting()
    if kind == "queried_by":
        return LoopRelationship.queried_by(parent.loop_id)
    if kind == "retrieved_by":
        return LoopRelationship.retrieved_by(parent.loop_id)
    return LoopRelationship.spawned_by(parent.loop_id)


def _run_operation(
        objective: str,
        operation: Callable[[], object],
        role: LoopRole,
        profile_id: str,
        relationship_kind: str,
        *, ledger=None, parent=None) -> dict:
    result = as_loop(
        objective, operation, kind="callable", ledger=ledger, parent=parent,
        identity=LoopRoleIdentity(role, profile_id),
        relationship=_relationship(parent, role, relationship_kind))
    if result.get("error") is not None:
        raise ReusableCapabilityError(
            f"{objective} failed inside Loop {result['loop_id']}") \
            from result["error"]
    return result


def _asset_record_id(spec: CodeAssetSpec) -> str:
    return (f"code_asset.{spec.asset_id}.{spec.version}."
            f"{spec.lifecycle}.{spec.qualification_digest[:16]}")


def _state_record_id(asset_id: str, version: str) -> str:
    return f"code_asset_state.{asset_id}.{version}"


def _admission_record_id(admission_id: str) -> str:
    return f"code_asset_admission.{admission_id}"


def _assessment_record(assessment: ReuseAssessment) -> dict:
    return {
        "record_id": f"reuse_assessment.{assessment.assessment_id}",
        "record_version": "1.0.0",
        "intelligence_layer": "runtime_history_solution",
        "source_collection": "learned",
        "artifact_kind": "reuse_assessment",
        "lifecycle": "candidate",
        "namespace": "org:local",
        "attributes": {
            "assessment": assessment.to_dict(),
            "assessment_digest": assessment.digest,
        },
    }


def _generalization_record(
        generalization: CapabilityGeneralizationRecord) -> dict:
    return {
        "record_id": (
            f"capability_generalization.{generalization.generalization_id}"),
        "record_version": "1.0.0",
        "intelligence_layer": "runtime_history_solution",
        "source_collection": "learned",
        "artifact_kind": "capability_generalization",
        "lifecycle": "candidate",
        "namespace": "org:local",
        "attributes": {
            "generalization": generalization.to_dict(),
            "generalization_digest": generalization.digest,
        },
    }


def _put_immutable(store, record: dict) -> None:
    existing = store.get(record["record_id"])
    if existing is not None and existing != record:
        raise ReusableCapabilityError(
            f"record {record['record_id']!r} already names different evidence")
    if existing is None:
        store.put(record)


def _authority_record(
        spec: CodeAssetSpec,
        producer_id: str,
        source_refs: tuple[str, ...],
        admission: CodeAssetAdmissionRecord | None = None,
        supersedes_ref: str = "") -> dict:
    return {
        "record_id": _asset_record_id(spec),
        "record_version": spec.version,
        "intelligence_layer": "code",
        "source_collection": "learned",
        "artifact_kind": "code_asset",
        "lifecycle": spec.lifecycle,
        "namespace": str(spec.metadata.get("namespace") or "org:local"),
        "attributes": {
            "spec": spec.to_dict(),
            "producer_id": producer_id,
            "source_refs": list(source_refs),
            "operation_family": str(
                spec.metadata.get("operation_family") or ""),
            "admission": admission.to_dict() if admission else {},
            "supersedes_ref": supersedes_ref,
        },
    }


def _lifecycle_record(
        spec: CodeAssetSpec,
        exact_record_id: str,
        sequence: int,
        *, admission_ref: str = "",
        transition_record_ref: str = "") -> dict:
    return {
        "record_id": _state_record_id(spec.asset_id, spec.version),
        "record_version": str(sequence),
        "intelligence_layer": "code",
        "source_collection": "learned",
        "artifact_kind": "code_asset_state",
        "lifecycle": spec.lifecycle,
        "namespace": str(spec.metadata.get("namespace") or "org:local"),
        "attributes": {
            "asset_id": spec.asset_id,
            "asset_version": spec.version,
            "qualification_digest": spec.qualification_digest,
            "exact_record_id": exact_record_id,
            "admission_ref": admission_ref,
            "transition_record_ref": transition_record_ref,
            "sequence": sequence,
        },
    }


def _transition_record(
        spec: CodeAssetSpec,
        from_state: str,
        to_state: str,
        actor_id: str,
        evidence_refs: tuple[str, ...],
        sequence: int) -> dict:
    body = {
        "asset_id": spec.asset_id,
        "asset_version": spec.version,
        "qualification_digest": spec.qualification_digest,
        "from_state": from_state,
        "to_state": to_state,
        "actor_id": actor_id,
        "evidence_refs": list(evidence_refs),
        "sequence": sequence,
    }
    digest = content_digest(body)
    return {
        "record_id": f"capability_transition.{digest[:24]}",
        "record_version": "1.0.0",
        "intelligence_layer": "runtime_history_solution",
        "source_collection": "learned",
        "artifact_kind": "capability_transition",
        "lifecycle": "registered",
        "namespace": str(spec.metadata.get("namespace") or "org:local"),
        "attributes": {**body, "transition_digest": digest},
    }


@dataclass(frozen=True)
class CandidateRegistrationRequest:
    opportunity: ReuseOpportunityObserved
    assessment: ReuseAssessment
    spec: CodeAssetSpec
    producer_id: str
    source_refs: tuple[str, ...]
    generalization: CapabilityGeneralizationRecord | None = None

    def __post_init__(self) -> None:
        refs = tuple(self.source_refs)
        if (not isinstance(self.producer_id, str)
                or not self.producer_id.strip() or not refs
                or len(refs) != len(set(refs))
                or any(not isinstance(item, str) or not item.strip()
                       for item in refs)):
            raise ReusableCapabilityError(
                "candidate registration needs producer and source evidence")
        object.__setattr__(self, "source_refs", refs)
        if (self.generalization is not None
                and not isinstance(
                    self.generalization, CapabilityGeneralizationRecord)):
            raise ReusableCapabilityError(
                "candidate generalization has the wrong contract")


@dataclass(frozen=True)
class CandidateRegistrationResult:
    outcome: str
    capability_record_ref: str
    lifecycle_state: str
    duplicate_of: str = ""
    loop_id: str = ""
    model_calls: int = 0


@dataclass(frozen=True)
class QualificationRequest:
    asset_id: str
    asset_version: str
    admission: CodeAssetAdmissionRecord

    def __post_init__(self) -> None:
        if (not isinstance(self.asset_id, str) or not self.asset_id.strip()
                or not isinstance(self.asset_version, str)
                or not self.asset_version.strip()
                or not isinstance(self.admission, CodeAssetAdmissionRecord)):
            raise ReusableCapabilityError(
                "qualification request identity is invalid")


@dataclass(frozen=True)
class PromotionRequest:
    asset_id: str
    asset_version: str
    promoter_id: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        refs = tuple(self.evidence_refs)
        if (not isinstance(self.asset_id, str) or not self.asset_id.strip()
                or not isinstance(self.asset_version, str)
                or not self.asset_version.strip()
                or not isinstance(self.promoter_id, str)
                or not self.promoter_id.strip() or not refs
                or len(refs) != len(set(refs))
                or any(not isinstance(item, str) or not item.strip()
                       for item in refs)):
            raise ReusableCapabilityError(
                "promotion request requires identity and evidence")
        object.__setattr__(self, "evidence_refs", refs)


@dataclass(frozen=True)
class LifecycleTransitionResult:
    asset_id: str
    asset_version: str
    lifecycle_state: str
    exact_record_ref: str
    transition_record_ref: str
    loop_id: str = ""
    model_calls: int = 0


class CapabilityAuthority:
    """Govern exact Code assets through one supplied unified catalog store."""

    def __init__(self, store) -> None:
        for operation in ("get", "query", "put"):
            if not callable(getattr(store, operation, None)):
                raise ReusableCapabilityError(
                    "capability authority requires a writable CatalogStore")
        self.store = store

    def _code_assets(self) -> tuple[dict, ...]:
        return tuple(self.store.query(IntelligenceQuery(
            layers=("code",), artifact_kinds=("code_asset",))))

    def state(self, asset_id: str, version: str) -> dict | None:
        return self.store.get(_state_record_id(asset_id, version))

    def exact_spec(self, record_ref: str) -> CodeAssetSpec:
        record = self.store.get(record_ref)
        if record is None or record.get("artifact_kind") != "code_asset":
            raise ReusableCapabilityError(
                f"Code asset record {record_ref!r} is unavailable")
        try:
            return CodeAssetSpec.from_dict(record["attributes"]["spec"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReusableCapabilityError(
                "authoritative Code asset record is malformed") from exc

    def active_spec(self, asset_id: str, version: str) -> CodeAssetSpec:
        state = self.state(asset_id, version)
        if state is None or state.get("lifecycle") != "registered":
            raise ReusableCapabilityError(
                "only the current registered lifecycle may execute")
        spec = self.exact_spec(state["attributes"]["exact_record_id"])
        if spec.lifecycle != "registered":
            raise ReusableCapabilityError(
                "active lifecycle points to a non-registered exact artifact")
        admission_value = self.store.get(_admission_record_id(
            state["attributes"]["admission_ref"]))
        if admission_value is None:
            raise ReusableCapabilityError(
                "active Code asset is missing exact admission authority")
        admission = CodeAssetAdmissionRecord.from_dict(
            admission_value["attributes"]["admission"])
        admit_code_asset(replace(
            spec, lifecycle="validated", admission_ref=""), admission)
        return spec

    def producer_id(self, asset_id: str, version: str) -> str:
        state = self.state(asset_id, version)
        if state is None:
            raise ReusableCapabilityError("capability state is unavailable")
        record = self.store.get(state["attributes"]["exact_record_id"])
        producer = str((record or {}).get("attributes", {}).get(
            "producer_id") or "")
        if not producer:
            raise ReusableCapabilityError(
                "capability producer provenance is unavailable")
        return producer

    def register_candidate_as_loop(
            self, request: CandidateRegistrationRequest, *,
            ledger=None, parent=None) -> CandidateRegistrationResult:
        if not isinstance(request, CandidateRegistrationRequest):
            raise ReusableCapabilityError(
                "candidate registration requires its typed request")

        def register() -> CandidateRegistrationResult:
            opportunity = request.opportunity
            assessment = request.assessment
            spec = request.spec
            if assessment.opportunity_id != opportunity.event_id:
                raise ReusableCapabilityError(
                    "reuse assessment references a different opportunity")
            if (not assessment.source_success_verified
                    or assessment.recommendation not in _CREATE_RECOMMENDATIONS):
                raise ReusableCapabilityError(
                    "structured evidence does not authorize candidate creation")
            if (spec.lifecycle != "candidate" or spec.admission_ref
                    or spec.metadata.get("operation_family")
                    != opportunity.operation_family):
                raise ReusableCapabilityError(
                    "candidate does not preserve the observed operation family")
            if opportunity.execution_record_ref not in request.source_refs:
                raise ReusableCapabilityError(
                    "candidate source evidence omits the observed execution")
            generalization = request.generalization
            if spec.body_ref.digest != opportunity.artifact_digest:
                if generalization is None:
                    raise ReusableCapabilityError(
                        "a changed candidate artifact needs generalization lineage")
                if (generalization.opportunity_id != opportunity.event_id
                        or generalization.source_artifact_ref
                        != opportunity.artifact_ref
                        or generalization.source_artifact_digest
                        != opportunity.artifact_digest
                        or generalization.candidate_artifact_ref
                        != spec.body_ref.uri
                        or generalization.candidate_artifact_digest
                        != spec.body_ref.digest
                        or generalization.producer_loop_id
                        != request.producer_id):
                    raise ReusableCapabilityError(
                        "generalization does not bind source and candidate")
            elif generalization is not None and (
                    generalization.opportunity_id != opportunity.event_id
                    or generalization.source_artifact_digest
                    != opportunity.artifact_digest
                    or generalization.candidate_artifact_digest
                    != spec.body_ref.digest):
                raise ReusableCapabilityError(
                    "identity generalization does not bind exact artifacts")
            _put_immutable(self.store, _assessment_record(assessment))
            if generalization is not None:
                _put_immutable(
                    self.store, _generalization_record(generalization))
            exact = next((record for record in self._code_assets()
                          if record.get("attributes", {}).get("spec", {}).get(
                              "qualification_digest")
                          == spec.qualification_digest), None)
            if exact is not None:
                alias = {
                    "record_id": f"capability_alias.{opportunity.event_id}",
                    "record_version": "1.0.0",
                    "intelligence_layer": "runtime_history_solution",
                    "source_collection": "learned",
                    "artifact_kind": "capability_alias",
                    "lifecycle": "registered",
                    "namespace": exact.get("namespace", "org:local"),
                    "attributes": {
                        "opportunity_id": opportunity.event_id,
                        "existing_capability_ref": exact["record_id"],
                        "qualification_digest": spec.qualification_digest,
                        "evidence_refs": list(request.source_refs),
                    },
                }
                self.store.put(alias)
                return CandidateRegistrationResult(
                    "duplicate_consolidated", exact["record_id"],
                    str(exact.get("lifecycle") or "candidate"),
                    exact["record_id"])
            conflicting = [record for record in self._code_assets()
                           if record.get("attributes", {}).get("spec", {}).get(
                               "asset_id") == spec.asset_id
                           and record.get("attributes", {}).get("spec", {}).get(
                               "version") == spec.version]
            if conflicting:
                raise ReusableCapabilityError(
                    "asset ID and version already name different content")
            exact_record = _authority_record(
                spec, request.producer_id, tuple(request.source_refs))
            self.store.put(exact_record)
            state = _lifecycle_record(spec, exact_record["record_id"], 1)
            self.store.put(state)
            return CandidateRegistrationResult(
                "candidate_created", exact_record["record_id"], "candidate")

        run = _run_operation(
            f"register reusable capability candidate {request.spec.asset_id}",
            register, LoopRole.PRACTITIONER,
            "practitioner.self_improvement", "spawned_by",
            ledger=ledger, parent=parent)
        value = run["value"]
        return replace(
            value, loop_id=run["loop_id"], model_calls=run["model_calls"])

    def qualify_as_loop(
            self, request: QualificationRequest, *,
            ledger=None, parent=None) -> LifecycleTransitionResult:
        if not isinstance(request, QualificationRequest):
            raise ReusableCapabilityError(
                "qualification requires its typed request")

        def qualify() -> LifecycleTransitionResult:
            state = self.state(request.asset_id, request.asset_version)
            if state is None or state.get("lifecycle") != "candidate":
                raise ReusableCapabilityError(
                    "qualification requires a current candidate")
            current = self.exact_spec(state["attributes"]["exact_record_id"])
            producer = self.store.get(
                state["attributes"]["exact_record_id"])["attributes"][
                    "producer_id"]
            if request.admission.producer_id != producer:
                raise ReusableCapabilityError(
                    "qualification producer identity does not match provenance")
            admitted = admit_code_asset(current, request.admission)
            validated = replace(
                admitted, lifecycle="validated",
                admission_ref=request.admission.admission_id)
            exact_record = _authority_record(
                validated, producer,
                tuple(self.store.get(
                    state["attributes"]["exact_record_id"])["attributes"].get(
                        "source_refs") or ()), request.admission)
            admission_record = {
                "record_id": _admission_record_id(
                    request.admission.admission_id),
                "record_version": "1.0.0",
                "intelligence_layer": "code",
                "source_collection": "learned",
                "artifact_kind": "code_asset_admission",
                "lifecycle": "validated",
                "namespace": exact_record["namespace"],
                "attributes": {"admission": request.admission.to_dict()},
            }
            existing_admission = self.store.get(admission_record["record_id"])
            if (existing_admission is not None
                    and existing_admission != admission_record):
                raise ReusableCapabilityError(
                    "admission identity already names different evidence")
            self.store.put(exact_record)
            if existing_admission is None:
                self.store.put(admission_record)
            transition = _transition_record(
                validated, "candidate", "validated",
                request.admission.verifier_id,
                request.admission.evidence_refs, 2)
            self.store.put(transition)
            self.store.put(_lifecycle_record(
                validated, exact_record["record_id"], 2,
                admission_ref=request.admission.admission_id,
                transition_record_ref=transition["record_id"]),
                precondition={"record_version": state["record_version"]})
            return LifecycleTransitionResult(
                validated.asset_id, validated.version, "validated",
                exact_record["record_id"], transition["record_id"])

        run = _run_operation(
            f"qualify reusable capability {request.asset_id}", qualify,
            LoopRole.PRACTITIONER, "practitioner.verifier", "spawned_by",
            ledger=ledger, parent=parent)
        return replace(
            run["value"], loop_id=run["loop_id"],
            model_calls=run["model_calls"])

    def promote_as_loop(
            self, request: PromotionRequest, *,
            ledger=None, parent=None) -> LifecycleTransitionResult:
        if not isinstance(request, PromotionRequest):
            raise ReusableCapabilityError(
                "promotion requires its typed request")

        def promote() -> LifecycleTransitionResult:
            state = self.state(request.asset_id, request.asset_version)
            if state is None or state.get("lifecycle") != "validated":
                raise ReusableCapabilityError(
                    "promotion requires a current qualified asset")
            validated_ref = state["attributes"]["exact_record_id"]
            validated_record = self.store.get(validated_ref)
            validated = self.exact_spec(validated_ref)
            producer = validated_record["attributes"]["producer_id"]
            if request.promoter_id.casefold() == producer.casefold():
                raise ReusableCapabilityError(
                    "a capability producer cannot promote its own artifact")
            admission_id = state["attributes"]["admission_ref"]
            admission_record = self.store.get(
                _admission_record_id(admission_id))
            if admission_record is None:
                raise ReusableCapabilityError(
                    "qualified asset admission record is missing")
            admission = CodeAssetAdmissionRecord.from_dict(
                admission_record["attributes"]["admission"])
            registered = admit_code_asset(replace(
                validated, lifecycle="validated", admission_ref=""), admission)
            exact_record = _authority_record(
                registered, producer,
                tuple(validated_record["attributes"].get("source_refs") or ()),
                admission)
            self.store.put(exact_record)
            transition = _transition_record(
                registered, "validated", "registered", request.promoter_id,
                tuple(request.evidence_refs), 3)
            self.store.put(transition)
            self.store.put(_lifecycle_record(
                registered, exact_record["record_id"], 3,
                admission_ref=admission_id,
                transition_record_ref=transition["record_id"]),
                precondition={"record_version": state["record_version"]})
            return LifecycleTransitionResult(
                registered.asset_id, registered.version, "registered",
                exact_record["record_id"], transition["record_id"])

        run = _run_operation(
            f"promote reusable capability {request.asset_id}", promote,
            LoopRole.PRACTITIONER, "practitioner.verifier", "spawned_by",
            ledger=ledger, parent=parent)
        return replace(
            run["value"], loop_id=run["loop_id"],
            model_calls=run["model_calls"])

    def transition_as_loop(
            self, asset_id: str, version: str, to_state: str,
            actor_id: str, evidence_refs: tuple[str, ...], *,
            ledger=None, parent=None) -> LifecycleTransitionResult:
        refs = tuple(evidence_refs)
        if (not isinstance(asset_id, str) or not asset_id.strip()
                or not isinstance(version, str) or not version.strip()
                or not isinstance(actor_id, str) or not actor_id.strip()
                or not refs or len(refs) != len(set(refs))
                or any(not isinstance(item, str) or not item.strip()
                       for item in refs)):
            raise ReusableCapabilityError(
                "lifecycle transition requires exact identity and evidence")

        def transition_state() -> LifecycleTransitionResult:
            state = self.state(asset_id, version)
            if state is None:
                raise ReusableCapabilityError("capability state is unavailable")
            before = str(state["lifecycle"])
            if to_state not in _STATE_TRANSITIONS.get(before, frozenset()):
                raise ReusableCapabilityError(
                    f"lifecycle cannot move from {before} to {to_state}")
            current_ref = state["attributes"]["exact_record_id"]
            current = self.exact_spec(current_ref)
            changed = replace(current, lifecycle=to_state)
            sequence = int(state["attributes"]["sequence"]) + 1
            transition = _transition_record(
                changed, before, to_state, actor_id,
                refs, sequence)
            self.store.put(transition)
            self.store.put(_lifecycle_record(
                changed, current_ref, sequence,
                admission_ref=str(state["attributes"].get(
                    "admission_ref") or ""),
                transition_record_ref=transition["record_id"]),
                precondition={"record_version": state["record_version"]})
            return LifecycleTransitionResult(
                asset_id, version, to_state, current_ref,
                transition["record_id"])

        run = _run_operation(
            f"transition reusable capability {asset_id} to {to_state}",
            transition_state, LoopRole.PRACTITIONER,
            "practitioner.verifier", "spawned_by", ledger=ledger,
            parent=parent)
        return replace(
            run["value"], loop_id=run["loop_id"],
            model_calls=run["model_calls"])


__all__ = (
    "CandidateRegistrationRequest", "CandidateRegistrationResult",
    "CapabilityAuthority", "LifecycleTransitionResult",
    "PromotionRequest", "QualificationRequest",
    "ReusableCapabilityError",
)
