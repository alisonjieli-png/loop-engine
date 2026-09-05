"""Paired stage-assistance contracts with a structurally isolated fresh arm.

These passive records define an experiment.  They do not call a provider,
select task semantics, or grant authority.  An owning Practitioner Loop may
execute the two assignments. The contract checks the exposure facts recorded
in Run History before either branch runs. Product packet-artifact inspection
and paired execution remain separate work.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .stage_evidence_records import (
    ADVISORY,
    FRESH,
    FRESH_CONTEXT_POLICY,
    STAGE_ASSISTANCE_ARMS,
    StageExposureManifest,
    StageOccurrenceIdentity,
    StageRetrievalSnapshot,
)

ASSISTANCE_ARMS = STAGE_ASSISTANCE_ARMS
STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION = "stage_experiment_assignment/v1"
STAGE_PACKET_EVENT_KIND = "stage_assistance_packet_assembled"
TREATMENT = "expose_typed_prior_stage_candidates"
CONTROL = "expose_no_prior_stage_candidates"


class StageAssistanceExperimentError(ValueError):
    """A paired assistance experiment would not support a valid comparison."""


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _required(value: object, name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise StageAssistanceExperimentError(f"{name} cannot be empty")
    return result


def _sha256(value: object, name: str) -> str:
    result = _required(value, name)
    if len(result) != 64 or any(character not in "0123456789abcdef"
                                for character in result):
        raise StageAssistanceExperimentError(
            f"{name} must be a lowercase SHA-256 digest")
    return result


@dataclass(frozen=True)
class StageAssistanceExperimentSpec:
    """Versioned definition of one advisory-versus-fresh comparison."""

    experiment_id: str
    version: str
    campaign_seed: str
    verification_contract_ref: str
    treatment: str = TREATMENT
    control: str = CONTROL
    schema_version: str = "stage_assistance_experiment/v1"

    def __post_init__(self) -> None:
        for name in ("experiment_id", "version", "campaign_seed",
                     "verification_contract_ref", "treatment", "control"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.schema_version != "stage_assistance_experiment/v1":
            raise StageAssistanceExperimentError(
                "unsupported stage assistance experiment schema")
        if (self.treatment, self.control) != (TREATMENT, CONTROL):
            raise StageAssistanceExperimentError(
                "v1 compares only typed prior-stage exposure against none")

    def to_dict(self) -> dict:
        return {
            "record_type": self.schema_version,
            "experiment_id": self.experiment_id,
            "version": self.version,
            "campaign_seed": self.campaign_seed,
            "verification_contract_ref": self.verification_contract_ref,
            "treatment": self.treatment,
            "control": self.control,
        }

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def experiment_ref(self) -> str:
        return f"stage-experiment:sha256:{self.content_digest}"

    @property
    def record_ref(self) -> str:
        return self.experiment_ref

    @classmethod
    def from_dict(cls, value: dict) -> StageAssistanceExperimentSpec:
        expected = {
            "record_type", "experiment_id", "version", "campaign_seed",
            "verification_contract_ref", "treatment", "control"}
        if not isinstance(value, dict) or set(value) != expected:
            raise StageAssistanceExperimentError(
                "stage assistance experiment fields do not match v1")
        return cls(
            experiment_id=value["experiment_id"], version=value["version"],
            campaign_seed=value["campaign_seed"],
            verification_contract_ref=value["verification_contract_ref"],
            treatment=value["treatment"], control=value["control"],
            schema_version=value["record_type"])


@dataclass(frozen=True)
class PairedStageAssistanceTrial:
    """Two independent activations beginning from one frozen state."""

    trial_id: str
    experiment_ref: str
    semantic_signature: str
    frozen_state_digest: str
    occurrences: tuple[StageOccurrenceIdentity, StageOccurrenceIdentity]
    schema_version: str = "paired_stage_assistance_trial/v1"

    def __post_init__(self) -> None:
        for name in ("trial_id", "experiment_ref", "semantic_signature"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "frozen_state_digest", _sha256(
            self.frozen_state_digest, "frozen_state_digest"))
        items = tuple(self.occurrences)
        if len(items) != 2 or any(
                not isinstance(item, StageOccurrenceIdentity) for item in items):
            raise StageAssistanceExperimentError(
                "a paired trial needs exactly two StageOccurrenceIdentity values")
        if items[0].loop_activation_ref == items[1].loop_activation_ref:
            raise StageAssistanceExperimentError(
                "paired branches require distinct activation occurrences")
        if items[0].namespace != items[1].namespace:
            raise StageAssistanceExperimentError(
                "paired branches must share one exact evidence namespace")
        for item in items:
            if item.semantic_signature != self.semantic_signature:
                raise StageAssistanceExperimentError(
                    "paired branches must share the declared semantic signature")
            if item.source_state_digest != self.frozen_state_digest:
                raise StageAssistanceExperimentError(
                    "paired branches must begin from the same frozen state")
        if items[0].shape_signature != items[1].shape_signature:
            raise StageAssistanceExperimentError(
                "paired branches must share one exact stage shape")
        if items[0].graph_version != items[1].graph_version:
            raise StageAssistanceExperimentError(
                "paired branches must share one exact graph version")
        if items[0].source_state_revision != items[1].source_state_revision:
            raise StageAssistanceExperimentError(
                "paired branches must share one source-state revision")
        if self.schema_version != "paired_stage_assistance_trial/v1":
            raise StageAssistanceExperimentError(
                "unsupported paired trial schema")
        object.__setattr__(self, "occurrences", items)

    def to_dict(self) -> dict:
        return {
            "record_type": self.schema_version,
            "trial_id": self.trial_id,
            "experiment_ref": self.experiment_ref,
            "semantic_signature": self.semantic_signature,
            "frozen_state_digest": self.frozen_state_digest,
            "occurrences": [item.to_dict() for item in self.occurrences],
        }

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def trial_ref(self) -> str:
        return f"stage-trial:sha256:{self.content_digest}"

    @property
    def record_ref(self) -> str:
        return self.trial_ref

    @classmethod
    def from_dict(cls, value: dict) -> PairedStageAssistanceTrial:
        expected = {"record_type", "trial_id", "experiment_ref",
                    "semantic_signature", "frozen_state_digest", "occurrences"}
        if not isinstance(value, dict) or set(value) != expected:
            raise StageAssistanceExperimentError(
                "paired stage assistance trial fields do not match v1")
        return cls(
            trial_id=value["trial_id"], experiment_ref=value["experiment_ref"],
            semantic_signature=value["semantic_signature"],
            frozen_state_digest=value["frozen_state_digest"],
            occurrences=tuple(StageOccurrenceIdentity.from_dict(item)
                              for item in value["occurrences"]),
            schema_version=value["record_type"])


@dataclass(frozen=True)
class StageExperimentAssignment:
    """One occurrence's retry-stable arm assignment."""

    assignment_id: str
    trial_ref: str
    experiment_ref: str
    occurrence_ref: str
    semantic_signature: str
    arm: str
    campaign_seed: str
    schema_version: str = STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("assignment_id", "trial_ref", "experiment_ref",
                     "occurrence_ref", "semantic_signature", "campaign_seed"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.arm not in ASSISTANCE_ARMS:
            raise StageAssistanceExperimentError(
                f"arm must be one of {ASSISTANCE_ARMS}")
        if self.schema_version != STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION:
            raise StageAssistanceExperimentError(
                "unsupported stage experiment assignment schema")

    def to_dict(self) -> dict:
        return {
            "record_type": self.schema_version,
            "assignment_id": self.assignment_id,
            "trial_ref": self.trial_ref,
            "experiment_ref": self.experiment_ref,
            "occurrence_ref": self.occurrence_ref,
            "semantic_signature": self.semantic_signature,
            "arm": self.arm,
            "campaign_seed": self.campaign_seed,
        }

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def assignment_ref(self) -> str:
        return f"stage-assignment:sha256:{self.content_digest}"

    @property
    def record_ref(self) -> str:
        return self.assignment_ref

    @classmethod
    def from_dict(cls, value: dict) -> StageExperimentAssignment:
        expected = {"record_type", "assignment_id", "trial_ref",
                    "experiment_ref", "occurrence_ref", "semantic_signature",
                    "arm", "campaign_seed"}
        if not isinstance(value, dict) or set(value) != expected:
            raise StageAssistanceExperimentError(
                "stage experiment assignment fields do not match v1")
        return cls(
            assignment_id=value["assignment_id"],
            trial_ref=value["trial_ref"],
            experiment_ref=value["experiment_ref"],
            occurrence_ref=value["occurrence_ref"],
            semantic_signature=value["semantic_signature"],
            arm=value["arm"], campaign_seed=value["campaign_seed"],
            schema_version=value["record_type"])


@dataclass(frozen=True)
class StagePacketEvidence:
    """Run History packet facts used to compile an exposure manifest.

    The event and packet digests are exact. The packet artifact body is not
    loaded by this contract, so a later integration must check that body
    before it describes the control as empirically fresh.
    """

    packet_event_ref: str
    packet_digest: str
    loop_id: str
    assignment_ref: str
    retrieval_snapshot_ref: str = ""
    exposed_prior_refs: tuple[str, ...] = ()
    context_block_ids: tuple[str, ...] = ()
    fresh_policy_id: str = FRESH_CONTEXT_POLICY

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_event_ref", _sha256(
            self.packet_event_ref, "packet_event_ref"))
        object.__setattr__(self, "packet_digest", _sha256(
            self.packet_digest, "packet_digest"))
        for name in ("loop_id", "assignment_ref", "fresh_policy_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "retrieval_snapshot_ref", str(
            self.retrieval_snapshot_ref or "").strip())
        for name in ("exposed_prior_refs", "context_block_ids"):
            values = tuple(getattr(self, name) or ())
            if any(not isinstance(item, str) or not item.strip()
                   for item in values) or len(values) != len(set(values)):
                raise StageAssistanceExperimentError(
                    f"{name} must contain unique non-empty strings")
            object.__setattr__(self, name, values)

    @classmethod
    def from_event(cls, event) -> StagePacketEvidence:
        """Bind packet facts to the digest of an actual Run History event."""
        detail = event.detail if isinstance(getattr(event, "detail", None), dict) \
            else {}
        if (getattr(event, "event_type", "") != "custom"
                or detail.get("custom_kind") != STAGE_PACKET_EVENT_KIND):
            raise StageAssistanceExperimentError(
                "packet evidence needs a stage packet Run History event")
        return cls(
            packet_event_ref=str(getattr(event, "event_digest", "")),
            packet_digest=str(detail.get("packet_digest") or ""),
            loop_id=str(getattr(event, "loop_id", "") or ""),
            assignment_ref=str(detail.get("assignment_ref") or ""),
            retrieval_snapshot_ref=str(
                detail.get("retrieval_snapshot_ref") or ""),
            exposed_prior_refs=tuple(detail.get("stage_prior_refs") or ()),
            context_block_ids=tuple(detail.get("context_block_ids") or ()),
            fresh_policy_id=str(detail.get("fresh_policy_id") or ""))


def packet_event_detail(*, packet_digest: str, assignment_ref: str,
                        retrieval_snapshot_ref: str = "",
                        exposed_prior_refs=(), context_block_ids=(),
                        fresh_policy_id: str = FRESH_CONTEXT_POLICY) -> dict:
    """Build packet event detail; its event digest is assigned by Run History."""
    _sha256(packet_digest, "packet_digest")
    _required(assignment_ref, "assignment_ref")
    return {
        "custom_kind": STAGE_PACKET_EVENT_KIND,
        "packet_digest": packet_digest,
        "assignment_ref": assignment_ref,
        "retrieval_snapshot_ref": str(retrieval_snapshot_ref or ""),
        "stage_prior_refs": list(exposed_prior_refs),
        "context_block_ids": list(context_block_ids),
        "fresh_policy_id": _required(fresh_policy_id, "fresh_policy_id"),
    }


def assign_paired_trial(
        spec: StageAssistanceExperimentSpec,
        trial: PairedStageAssistanceTrial) -> tuple[StageExperimentAssignment, ...]:
    """Assign exactly one advisory and one fresh branch, reproducibly.

    Physical provider attempts are intentionally absent from the material.
    Recomputing an assignment after any number of retries therefore returns the
    same records.  A seed may re-orient a later campaign without changing code.
    """
    if not isinstance(spec, StageAssistanceExperimentSpec) \
            or not isinstance(trial, PairedStageAssistanceTrial):
        raise StageAssistanceExperimentError(
            "paired assignment needs an experiment spec and paired trial")
    if trial.experiment_ref != spec.experiment_ref:
        raise StageAssistanceExperimentError(
            "paired trial names a different experiment definition")
    ordered = tuple(sorted(trial.occurrences,
                           key=lambda item: item.occurrence_ref))
    orientation = int(_digest({
        "experiment_ref": spec.experiment_ref,
        "trial_ref": trial.trial_ref,
        "semantic_signature": trial.semantic_signature,
        "frozen_state_digest": trial.frozen_state_digest,
        "campaign_seed": spec.campaign_seed,
    })[-1], 16) % 2
    arms = (ADVISORY, FRESH) if orientation == 0 else (FRESH, ADVISORY)
    return tuple(StageExperimentAssignment(
        assignment_id=f"{trial.trial_id}.{arm}",
        trial_ref=trial.trial_ref,
        experiment_ref=spec.experiment_ref,
        occurrence_ref=occurrence.occurrence_ref,
        semantic_signature=trial.semantic_signature,
        arm=arm, campaign_seed=spec.campaign_seed)
        for occurrence, arm in zip(ordered, arms))


def build_exposure_manifest(
        assignment: StageExperimentAssignment,
        snapshot: StageRetrievalSnapshot | None = None, *,
        packet_evidence: StagePacketEvidence,
        exposed_prior_refs: tuple[str, ...] | None = None,
        ) -> StageExposureManifest:
    """Compile the arm into an auditable model-exposure manifest."""
    if not isinstance(assignment, StageExperimentAssignment):
        raise StageAssistanceExperimentError(
            "exposure compilation needs a StageExperimentAssignment")
    if not isinstance(packet_evidence, StagePacketEvidence):
        raise StageAssistanceExperimentError(
            "exposure compilation needs actual typed packet evidence")
    if packet_evidence.assignment_ref != assignment.assignment_ref:
        raise StageAssistanceExperimentError(
            "packet evidence belongs to another assignment")
    if assignment.arm == FRESH:
        if snapshot is not None or exposed_prior_refs not in (None, ()):
            raise StageAssistanceExperimentError(
                "the fresh arm cannot retrieve or expose prior stage references")
        retrieved: tuple[str, ...] = ()
        exposed: tuple[str, ...] = ()
        snapshot_ref = ""
    else:
        if not isinstance(snapshot, StageRetrievalSnapshot):
            raise StageAssistanceExperimentError(
                "the advisory arm needs a typed retrieval snapshot")
        if snapshot.occurrence_ref != assignment.occurrence_ref:
            raise StageAssistanceExperimentError(
                "retrieval snapshot belongs to another occurrence")
        if snapshot.semantic_signature != assignment.semantic_signature:
            raise StageAssistanceExperimentError(
                "retrieval snapshot belongs to another stage signature")
        retrieved = tuple(item.candidate_ref for item in snapshot.candidates)
        compatible = tuple(
            item.candidate_ref for item in snapshot.candidates
            if all(value is True for value in (
                item.contract_compatible, item.effect_compatible,
                item.authority_compatible, item.privacy_compatible)))
        exposed = (compatible if exposed_prior_refs is None
                   else tuple(exposed_prior_refs))
        unknown = set(exposed) - set(retrieved)
        if unknown:
            raise StageAssistanceExperimentError(
                f"exposure names un-retrieved prior refs {sorted(unknown)!r}")
        by_ref = {item.candidate_ref: item for item in snapshot.candidates}
        incompatible = [ref for ref in exposed if ref not in compatible]
        if incompatible:
            privacy = [ref for ref in incompatible
                       if by_ref[ref].privacy_compatible is not True]
            reason = (f"privacy compatibility is not proven for {privacy!r}"
                      if privacy else
                      f"hard compatibility is not proven for {incompatible!r}")
            raise StageAssistanceExperimentError(reason)
        snapshot_ref = snapshot.snapshot_ref
    if packet_evidence.retrieval_snapshot_ref != snapshot_ref:
        raise StageAssistanceExperimentError(
            "packet evidence names a different retrieval snapshot")
    if packet_evidence.exposed_prior_refs != exposed:
        raise StageAssistanceExperimentError(
            "packet evidence and exposure disagree about prior references")
    if packet_evidence.fresh_policy_id != FRESH_CONTEXT_POLICY:
        raise StageAssistanceExperimentError(
            "packet evidence does not use the stage-prior isolation policy")
    return StageExposureManifest(
        manifest_id=f"exposure.{assignment.assignment_id}",
        occurrence_ref=assignment.occurrence_ref,
        experiment_ref=assignment.experiment_ref,
        assignment_ref=assignment.assignment_ref,
        packet_event_ref=packet_evidence.packet_event_ref,
        packet_digest=packet_evidence.packet_digest,
        fresh_policy_id=packet_evidence.fresh_policy_id,
        arm=assignment.arm,
        retrieval_snapshot_ref=snapshot_ref,
        retrieved_prior_refs=retrieved,
        exposed_prior_refs=exposed,
        packet_context_block_ids=packet_evidence.context_block_ids)


def experiment_record_from_dict(value: dict):
    """Strict reader for records owned by this experiment module."""
    if not isinstance(value, dict):
        raise StageAssistanceExperimentError(
            "experiment record must be a mapping")
    readers = {
        "stage_assistance_experiment/v1":
            StageAssistanceExperimentSpec.from_dict,
        "paired_stage_assistance_trial/v1":
            PairedStageAssistanceTrial.from_dict,
        STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION:
            StageExperimentAssignment.from_dict,
    }
    record_type = value.get("record_type")
    if record_type not in readers:
        raise StageAssistanceExperimentError(
            f"unsupported experiment record type {record_type!r}")
    return readers[record_type](value)


__all__ = (
    "ADVISORY",
    "ASSISTANCE_ARMS",
    "FRESH",
    "STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION",
    "STAGE_PACKET_EVENT_KIND",
    "PairedStageAssistanceTrial",
    "StageAssistanceExperimentError",
    "StageAssistanceExperimentSpec",
    "StageExperimentAssignment",
    "StagePacketEvidence",
    "assign_paired_trial",
    "build_exposure_manifest",
    "experiment_record_from_dict",
    "packet_event_detail",
)
