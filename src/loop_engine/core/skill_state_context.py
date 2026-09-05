"""Passive state-centric context candidates for admitted Agent Skills.

The skill procedure stays immutable. Current execution state reuses
``TrustedStateSnapshot`` and an exact JSON Schema field contract. Observation
and selected history values are sealed as canonical JSON before their digests
are computed. Every candidate is bound to task, run, branch, graph, Loop,
state, tenant, privacy, and materialization-authorization references.

This module creates no runtime, performs no state transition, reads no Run
History, calls no model or tool, and grants no authority. Its returned
``LLMContextBlock`` is deliberately not integrated with the product prompt
renderer. A separate reviewed change must preserve the part-level trust and
privacy labels when that integration is attempted.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .context_pack_manifest import TRUST_CLASSES
from .llm_work_packet import LLMContextBlock
from .semantic_runtime_records import TrustedStateSnapshot, canonical_json
from .skill_registry import LoadedSkill

SKILL_STATE_CONTEXT_POLICY = "skill_state_context/v1"
SKILL_STATE_HISTORY_POLICY = "evidence_backed_history_material/v1"
SKILL_STATE_PRODUCT_RENDERER_INTEGRATED = False
STATE_SUFFICIENCY_FLAGS = (
    "delayed_relevance",
    "schema_gap",
    "state_uncertain",
    "trajectory_required",
)
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class SkillStateContextError(ValueError):
    """A state, schema, binding, or context candidate failed closed."""


class _SealedJSON(str):
    """Canonical JSON marker that remains stable through dataclass replace."""


def _text(value: object, name: str, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise SkillStateContextError(f"{name} must be text")
    result = value.strip()
    if not result and not empty:
        raise SkillStateContextError(f"{name} cannot be empty")
    if (
        value != result
        or "\n" in result
        or "\r" in result
        or any(ord(character) < 32 or ord(character) == 127 for character in result)
    ):
        raise SkillStateContextError(f"{name} must be one trimmed line")
    return result


def _digest(value: object, name: str) -> str:
    result = _text(value, name)
    if not _DIGEST.fullmatch(result):
        raise SkillStateContextError(f"{name} must be a SHA-256 digest")
    return result


def _positive(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SkillStateContextError(f"{name} must be a positive integer")
    return value


def _refs(values: object, name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise SkillStateContextError(f"{name} must be a sequence")
    try:
        candidates = tuple(values or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise SkillStateContextError(f"{name} must be a sequence") from exc
    result = tuple(_text(item, name) for item in candidates)
    if len(result) != len(set(result)):
        raise SkillStateContextError(f"{name} must not contain duplicates")
    return result


def _strict_json(value: object, name: str) -> str:
    def finite(item: object) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise SkillStateContextError(f"{name} cannot contain NaN or infinity")
        if isinstance(item, dict):
            for key, nested_value in item.items():
                if not isinstance(key, str):
                    raise SkillStateContextError(f"{name} object keys must be strings")
                finite(nested_value)
        elif isinstance(item, (list, tuple)):
            for nested_value in item:
                finite(nested_value)

    finite(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SkillStateContextError(f"{name} must be strict JSON") from exc


def _decode(value_json: str) -> object:
    return json.loads(value_json)


def _seal_json(value: object, name: str) -> _SealedJSON:
    if isinstance(value, _SealedJSON):
        try:
            decoded = json.loads(str(value))
        except (TypeError, ValueError) as exc:
            raise SkillStateContextError(f"{name} sealed JSON is invalid") from exc
        if _strict_json(decoded, name) != str(value):
            raise SkillStateContextError(f"{name} sealed JSON is not canonical")
        return value
    return _SealedJSON(_strict_json(value, name))


def _privacy_matches(actual: str, binding: str) -> bool:
    return actual == "public" or actual == binding


def _has_schema_reference(value: object) -> bool:
    if isinstance(value, dict):
        return any(key in value for key in ("$ref", "$dynamicRef")) or any(
            _has_schema_reference(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_has_schema_reference(item) for item in value)
    return False


@dataclass(frozen=True)
class SkillExecutionProfile:
    """Exact skill, JSON Schema, and byte policy for one execution shape."""

    profile_id: str
    version: str
    skill_id: str
    skill_version: str
    skill_manifest_digest: str
    state_schema_ref: str
    state_schema_digest: str
    state_schema_json: str
    maximum_state_bytes: int
    maximum_observation_bytes: int
    maximum_context_bytes: int
    context_policy: str = SKILL_STATE_CONTEXT_POLICY
    history_policy: str = SKILL_STATE_HISTORY_POLICY

    def __post_init__(self) -> None:
        for name in ("profile_id", "skill_id", "state_schema_ref"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("version", "skill_version"):
            value = _text(getattr(self, name), name)
            if not _SEMVER.fullmatch(value):
                raise SkillStateContextError(f"{name} must use semantic versioning")
        _digest(self.skill_manifest_digest, "skill_manifest_digest")
        _digest(self.state_schema_digest, "state_schema_digest")
        try:
            raw_schema = json.loads(self.state_schema_json)
        except (TypeError, ValueError) as exc:
            raise SkillStateContextError(
                "state_schema_json must contain JSON Schema"
            ) from exc
        if (
            not isinstance(raw_schema, dict)
            or raw_schema.get("type") != "object"
            or not isinstance(raw_schema.get("properties"), dict)
            or raw_schema.get("additionalProperties") is not False
        ):
            raise SkillStateContextError(
                "state schema must be an exact object field contract with "
                "properties and additionalProperties false"
            )
        if _has_schema_reference(raw_schema):
            raise SkillStateContextError(
                "state schema must be self-contained and cannot use references"
            )
        try:
            Draft202012Validator.check_schema(raw_schema)
        except SchemaError as exc:
            raise SkillStateContextError("state JSON Schema is invalid") from exc
        canonical_schema = _strict_json(raw_schema, "state schema")
        computed = hashlib.sha256(canonical_schema.encode("utf-8")).hexdigest()
        if computed != self.state_schema_digest:
            raise SkillStateContextError(
                "state schema digest does not match state_schema_json"
            )
        object.__setattr__(self, "state_schema_json", canonical_schema)
        for name in (
            "maximum_state_bytes",
            "maximum_observation_bytes",
            "maximum_context_bytes",
        ):
            _positive(getattr(self, name), name)
        if self.context_policy != SKILL_STATE_CONTEXT_POLICY:
            raise SkillStateContextError("unknown skill state context policy")
        if self.history_policy != SKILL_STATE_HISTORY_POLICY:
            raise SkillStateContextError("unknown skill history policy")

    @property
    def profile_digest(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode()).hexdigest()

    @property
    def state_schema(self) -> dict[str, object]:
        return json.loads(self.state_schema_json)

    def validate_state(self, state: TrustedStateSnapshot) -> None:
        if not isinstance(state, TrustedStateSnapshot):
            raise SkillStateContextError("state must use TrustedStateSnapshot")
        errors = sorted(
            Draft202012Validator(self.state_schema).iter_errors(dict(state.values)),
            key=lambda error: tuple(str(item) for item in error.path),
        )
        if errors:
            location = ".".join(str(item) for item in errors[0].path) or "$"
            raise SkillStateContextError(
                f"current state violates its exact field contract at {location}"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "skill_execution_profile/v1",
            **self.__dict__,
        }


@dataclass(frozen=True)
class SkillLatestObservation:
    """Deep-sealed newest observation with exact execution provenance."""

    observation_id: str
    value: Any
    provenance: str
    evidence_ref: str
    evidence_digest: str
    task_id: str
    run_id: str
    loop_id: str
    tenant_id: str
    privacy_class: str
    trust_class: str

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "provenance",
            "evidence_ref",
            "task_id",
            "run_id",
            "loop_id",
            "tenant_id",
            "privacy_class",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        _digest(self.evidence_digest, "evidence_digest")
        if self.trust_class not in TRUST_CLASSES:
            raise SkillStateContextError("observation trust_class is unknown")
        object.__setattr__(self, "value", _seal_json(self.value, "observation value"))

    @property
    def canonical_value(self) -> str:
        return str(self.value)

    @property
    def value_digest(self) -> str:
        return hashlib.sha256(self.canonical_value.encode()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "value": _decode(self.canonical_value),
            "value_digest": self.value_digest,
            "provenance": self.provenance,
            "evidence_ref": self.evidence_ref,
            "evidence_digest": self.evidence_digest,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "loop_id": self.loop_id,
            "tenant_id": self.tenant_id,
            "privacy_class": self.privacy_class,
            "trust_class": self.trust_class,
        }


@dataclass(frozen=True)
class SkillSelectedHistoryMaterial:
    """Deep-sealed, evidence-backed Run History material selected by a Loop."""

    material_id: str
    source_run_id: str
    source_loop_id: str
    source_event_ref: str
    value: Any
    evidence_ref: str
    evidence_digest: str
    tenant_id: str
    privacy_class: str
    trust_class: str = "run_history"

    def __post_init__(self) -> None:
        for name in (
            "material_id",
            "source_run_id",
            "source_loop_id",
            "source_event_ref",
            "evidence_ref",
            "tenant_id",
            "privacy_class",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        _digest(self.evidence_digest, "evidence_digest")
        if self.trust_class != "run_history":
            raise SkillStateContextError(
                "selected history material must use run_history trust"
            )
        object.__setattr__(self, "value", _seal_json(self.value, "history material"))

    @property
    def canonical_value(self) -> str:
        return str(self.value)

    @property
    def material_digest(self) -> str:
        payload = {
            "material_id": self.material_id,
            "source_run_id": self.source_run_id,
            "source_loop_id": self.source_loop_id,
            "source_event_ref": self.source_event_ref,
            "value_digest": hashlib.sha256(self.canonical_value.encode()).hexdigest(),
            "evidence_ref": self.evidence_ref,
            "evidence_digest": self.evidence_digest,
            "tenant_id": self.tenant_id,
            "privacy_class": self.privacy_class,
            "trust_class": self.trust_class,
        }
        return hashlib.sha256(canonical_json(payload).encode()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "material_id": self.material_id,
            "source_run_id": self.source_run_id,
            "source_loop_id": self.source_loop_id,
            "source_event_ref": self.source_event_ref,
            "value": _decode(self.canonical_value),
            "material_digest": self.material_digest,
            "evidence_ref": self.evidence_ref,
            "evidence_digest": self.evidence_digest,
            "tenant_id": self.tenant_id,
            "privacy_class": self.privacy_class,
            "trust_class": self.trust_class,
        }


@dataclass(frozen=True)
class SkillExecutionBinding:
    """Exact externally authorized identity and materialization envelope."""

    binding_id: str
    task_id: str
    run_id: str
    branch_id: str
    graph_id: str
    graph_version: str
    loop_id: str
    tenant_id: str
    privacy_class: str
    destination_ref: str
    profile_digest: str
    state_id: str
    state_revision: int
    state_digest: str
    observation_id: str
    observation_digest: str
    history_material_digests: tuple[str, ...]
    materialization_authorized: bool
    materialization_authorization_ref: str
    materialization_authorization_digest: str

    def __post_init__(self) -> None:
        for name in (
            "binding_id",
            "task_id",
            "run_id",
            "branch_id",
            "graph_id",
            "graph_version",
            "loop_id",
            "tenant_id",
            "privacy_class",
            "destination_ref",
            "state_id",
            "observation_id",
            "materialization_authorization_ref",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "profile_digest",
            "state_digest",
            "observation_digest",
            "materialization_authorization_digest",
        ):
            _digest(getattr(self, name), name)
        history_digests = tuple(
            _digest(value, "history_material_digest")
            for value in self.history_material_digests
        )
        if len(history_digests) != len(set(history_digests)):
            raise SkillStateContextError("history material digests must not repeat")
        object.__setattr__(self, "history_material_digests", history_digests)
        if (
            not isinstance(self.state_revision, int)
            or isinstance(self.state_revision, bool)
            or self.state_revision < 0
        ):
            raise SkillStateContextError(
                "state_revision must be a non-negative integer"
            )
        if not isinstance(self.materialization_authorized, bool):
            raise SkillStateContextError("materialization_authorized must be boolean")

    @property
    def binding_digest(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "skill_execution_binding/v1",
            **{
                name: list(value) if isinstance(value, tuple) else value
                for name, value in self.__dict__.items()
            },
        }


@dataclass(frozen=True)
class SkillStateContextRequest:
    """Exact inputs selected by a Loop for one passive context candidate."""

    profile: SkillExecutionProfile
    skill: LoadedSkill
    state: TrustedStateSnapshot
    latest_observation: SkillLatestObservation
    binding: SkillExecutionBinding
    position: int
    sufficiency_flags: tuple[str, ...] = ()
    selected_history: tuple[SkillSelectedHistoryMaterial, ...] = ()
    history_selection_reason: str = ""
    history_selection_evidence_ref: str = ""
    history_selection_evidence_digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.profile, SkillExecutionProfile):
            raise SkillStateContextError("profile has the wrong type")
        if not isinstance(self.skill, LoadedSkill):
            raise SkillStateContextError("skill has the wrong type")
        if not isinstance(self.state, TrustedStateSnapshot):
            raise SkillStateContextError("state must use TrustedStateSnapshot")
        if not isinstance(self.latest_observation, SkillLatestObservation):
            raise SkillStateContextError("latest_observation has the wrong type")
        if not isinstance(self.binding, SkillExecutionBinding):
            raise SkillStateContextError("binding has the wrong type")
        if not isinstance(self.position, int) or self.position < 0:
            raise SkillStateContextError("position must be non-negative")
        flags = _refs(self.sufficiency_flags, "sufficiency_flags")
        if any(flag not in STATE_SUFFICIENCY_FLAGS for flag in flags):
            raise SkillStateContextError("unknown state sufficiency flag")
        history = tuple(self.selected_history)
        if any(
            not isinstance(item, SkillSelectedHistoryMaterial) for item in history
        ) or len({item.material_id for item in history}) != len(history):
            raise SkillStateContextError("selected_history needs unique typed material")
        reason = _text(
            self.history_selection_reason,
            "history_selection_reason",
            empty=True,
        )
        evidence_ref = _text(
            self.history_selection_evidence_ref,
            "history_selection_evidence_ref",
            empty=True,
        )
        evidence_digest = self.history_selection_evidence_digest
        if history:
            if not reason or not evidence_ref:
                raise SkillStateContextError(
                    "selected history needs a reason and evidence reference"
                )
            _digest(evidence_digest, "history_selection_evidence_digest")
        elif reason or evidence_ref or evidence_digest:
            raise SkillStateContextError(
                "history selection evidence requires selected material"
            )
        if "schema_gap" in flags:
            raise SkillStateContextError(
                "schema_gap requires a new verified execution profile"
            )
        if flags and not history:
            raise SkillStateContextError(
                "state insufficiency requires evidence-backed history material"
            )
        object.__setattr__(self, "sufficiency_flags", flags)
        object.__setattr__(self, "selected_history", history)
        if (
            self.skill.manifest.skill_id != self.profile.skill_id
            or self.skill.manifest.version != self.profile.skill_version
            or self.skill.manifest.manifest_digest != self.profile.skill_manifest_digest
        ):
            raise SkillStateContextError(
                "loaded skill does not match the execution profile"
            )
        admission = self.skill.admission
        if (
            self.skill.manifest.lifecycle != "registered"
            or admission is None
            or admission.skill_id != self.skill.manifest.skill_id
            or admission.version != self.skill.manifest.version
            or admission.manifest_digest != self.skill.manifest.manifest_digest
        ):
            raise SkillStateContextError(
                "state-centric execution needs an exactly admitted skill"
            )
        self.profile.validate_state(self.state)
        expected_binding = (
            (self.binding.profile_digest, self.profile.profile_digest),
            (self.binding.state_id, self.state.state_id),
            (self.binding.state_revision, self.state.version),
            (self.binding.state_digest, self.state.digest),
            (self.binding.observation_id, self.latest_observation.observation_id),
            (self.binding.observation_digest, self.latest_observation.value_digest),
            (
                self.binding.history_material_digests,
                tuple(item.material_digest for item in history),
            ),
        )
        if any(actual != expected for actual, expected in expected_binding):
            raise SkillStateContextError(
                "execution binding does not match its exact context materials"
            )
        observation_scope = self.latest_observation
        if (
            observation_scope.task_id != self.binding.task_id
            or observation_scope.run_id != self.binding.run_id
            or observation_scope.loop_id != self.binding.loop_id
            or observation_scope.tenant_id != self.binding.tenant_id
        ):
            raise SkillStateContextError(
                "latest observation does not match the execution binding"
            )
        if not _privacy_matches(
            observation_scope.privacy_class, self.binding.privacy_class
        ):
            raise SkillStateContextError(
                "latest observation privacy exceeds the execution binding"
            )
        for item in history:
            if (
                item.source_run_id != self.binding.run_id
                or item.tenant_id != self.binding.tenant_id
            ):
                raise SkillStateContextError(
                    "selected history is outside the run or tenant binding"
                )
            if not _privacy_matches(item.privacy_class, self.binding.privacy_class):
                raise SkillStateContextError(
                    "selected history privacy exceeds the execution binding"
                )
        if not self.binding.materialization_authorized:
            raise SkillStateContextError(
                "context materialization needs external authorization"
            )


def compile_state_centric_skill_block(
    request: SkillStateContextRequest,
) -> LLMContextBlock:
    """Compile an immutable passive candidate that no product renderer reads."""
    if not isinstance(request, SkillStateContextRequest):
        raise SkillStateContextError(
            "state-centric compilation needs SkillStateContextRequest"
        )
    request.profile.validate_state(request.state)
    admission = request.skill.admission
    if admission is None:
        raise SkillStateContextError("admitted skill identity was lost")
    state_value = {
        "state_id": request.state.state_id,
        "revision": request.state.version,
        "digest": request.state.digest,
        "values": dict(request.state.values),
    }
    state_bytes = len(_strict_json(state_value, "state").encode("utf-8"))
    observation_bytes = len(request.latest_observation.canonical_value.encode("utf-8"))
    if state_bytes > request.profile.maximum_state_bytes:
        raise SkillStateContextError("current state exceeds its byte budget")
    if observation_bytes > request.profile.maximum_observation_bytes:
        raise SkillStateContextError("latest observation exceeds its byte budget")
    parts = {
        "procedure": {
            "trust_class": "curated_intelligence",
            "privacy_class": request.binding.privacy_class,
            "value": {
                "skill_id": request.skill.manifest.skill_id,
                "version": request.skill.manifest.version,
                "manifest_digest": request.skill.manifest.manifest_digest,
                "admission_digest": admission.digest,
                "instructions": request.skill.instructions,
            },
        },
        "current_state": {
            "trust_class": "run_history",
            "privacy_class": request.binding.privacy_class,
            "value": state_value,
        },
        "latest_observation": {
            "trust_class": request.latest_observation.trust_class,
            "privacy_class": request.latest_observation.privacy_class,
            "value": request.latest_observation.to_dict(),
        },
        "selected_history": [
            {
                "trust_class": item.trust_class,
                "privacy_class": item.privacy_class,
                "value": item.to_dict(),
            }
            for item in request.selected_history
        ],
    }
    content = {
        "record_type": "passive_skill_state_context_candidate/v1",
        "product_renderer_integrated": False,
        "grants_authority": False,
        "profile": {
            "profile_id": request.profile.profile_id,
            "version": request.profile.version,
            "profile_digest": request.profile.profile_digest,
            "context_policy": request.profile.context_policy,
            "history_policy": request.profile.history_policy,
            "maximum_state_bytes": request.profile.maximum_state_bytes,
            "maximum_observation_bytes": (request.profile.maximum_observation_bytes),
            "maximum_context_bytes": request.profile.maximum_context_bytes,
        },
        "execution_binding": {
            **request.binding.to_dict(),
            "binding_digest": request.binding.binding_digest,
        },
        "state_schema": {
            "ref": request.profile.state_schema_ref,
            "digest": request.profile.state_schema_digest,
            "schema": request.profile.state_schema,
        },
        "parts": parts,
        "history_selection": {
            "reason": request.history_selection_reason,
            "evidence_ref": request.history_selection_evidence_ref,
            "evidence_digest": request.history_selection_evidence_digest,
            "full_transcript_included": False,
            "prior_reasoning_included": False,
        },
        "state_sufficiency": {
            "flags": list(request.sufficiency_flags),
            "evidence_backed_history_included": bool(request.selected_history),
            "status": ("supplemented" if request.sufficiency_flags else "state_only"),
        },
        "tool_requests": {
            "names": list(request.skill.manifest.requested_tools),
            "advisory_only": True,
            "grant_authority": False,
        },
    }
    content_json = _strict_json(content, "skill context")
    rendered_content_json = _strict_json(content_json, "sealed skill context")
    if (
        len(rendered_content_json.encode("utf-8"))
        > request.profile.maximum_context_bytes
    ):
        raise SkillStateContextError("compiled skill context exceeds its byte budget")
    return LLMContextBlock.create(
        "skill-state." + request.skill.manifest.skill_id,
        "passive_skill_state_context_candidate",
        request.profile.version,
        request.profile.profile_id + "@" + request.profile.profile_digest,
        "passive candidate; product prompt integration is not implemented",
        request.position,
        content_json,
    )


__all__ = (
    "SKILL_STATE_CONTEXT_POLICY",
    "SKILL_STATE_HISTORY_POLICY",
    "SKILL_STATE_PRODUCT_RENDERER_INTEGRATED",
    "STATE_SUFFICIENCY_FLAGS",
    "SkillExecutionBinding",
    "SkillExecutionProfile",
    "SkillLatestObservation",
    "SkillSelectedHistoryMaterial",
    "SkillStateContextError",
    "SkillStateContextRequest",
    "compile_state_centric_skill_block",
)
