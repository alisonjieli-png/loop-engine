"""Passive controls for a bounded public-solve assistance experiment.

The source-state digest answers a narrow task and policy identity question.
This module separately records whether context, model execution, capabilities,
environment, evaluation, workspace, and observer surfaces were controlled.
Unknown is explicit. A mechanism-only record cannot become paired evidence.

An owning Loop may persist these records. They do not execute a task, select a
model, grant authority, or establish that a provider behaved deterministically.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

CONTROL_COMPONENT_IDS = (
    "task_and_source",
    "solver_policy",
    "runtime_definition",
    "context_and_interface",
    "model_execution",
    "capability_surface",
    "execution_environment",
    "evaluation",
    "workspace_isolation",
    "observer_sinks",
)
CONTROL_STATUSES = ("exact", "metadata_only", "unknown")
CONTROL_EVIDENCE_CLASSES = ("mechanism_only",)
ASSISTANCE_MODES = ("advisory", "fresh")
_SENSITIVE_KEYS = {
    "api_key", "authorization", "authorization_header", "access_token",
    "refresh_token", "password", "secret", "secret_value", "private_prompt",
    "raw_prompt",
}


class SolveControlManifestError(ValueError):
    """A control record is ambiguous, mutable, or overclaims its evidence."""


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SolveControlManifestError(
            "control material must be finite JSON data") from exc


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _required(value: object, name: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise SolveControlManifestError(f"{name} cannot be empty")
    return result


def _sha256(value: object, name: str) -> str:
    result = _required(value, name)
    if len(result) != 64 or any(character not in "0123456789abcdef"
                                for character in result):
        raise SolveControlManifestError(
            f"{name} must be a lowercase SHA-256 digest")
    return result


def _unique_text(values, name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise SolveControlManifestError(f"{name} must be a sequence")
    items = tuple(values or ())
    if (any(not isinstance(item, str) or not item.strip() for item in items)
            or len(items) != len(set(items))):
        raise SolveControlManifestError(
            f"{name} must contain unique non-empty text")
    return items


def _sensitive_paths(value: object, path: str = "") -> tuple[str, ...]:
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            name = str(key).lower()
            nested_path = f"{path}.{key}" if path else str(key)
            if name in _SENSITIVE_KEYS or any(name.endswith(suffix) for suffix in (
                    "_api_key", "_access_token", "_refresh_token",
                    "_password", "_secret_value")):
                found.append(nested_path)
            found.extend(_sensitive_paths(item, nested_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_sensitive_paths(item, f"{path}[{index}]"))
    return tuple(found)


@dataclass(frozen=True)
class ControlComponentRecord:
    """One detached, inspectable component of the comparison controls."""

    component_id: str
    status: str
    body_json: str
    unresolved_fields: tuple[str, ...] = ()
    schema_version: str = "solve_control_component/v1"

    def __post_init__(self) -> None:
        if self.component_id not in CONTROL_COMPONENT_IDS:
            raise SolveControlManifestError("unknown control component")
        if self.status not in CONTROL_STATUSES:
            raise SolveControlManifestError("unknown control status")
        if self.schema_version != "solve_control_component/v1":
            raise SolveControlManifestError("unsupported control component schema")
        try:
            body = json.loads(self.body_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise SolveControlManifestError(
                "control component body must be canonical JSON") from exc
        if not isinstance(body, dict) or _canonical(body) != self.body_json:
            raise SolveControlManifestError(
                "control component body must be a canonical JSON object")
        sensitive = _sensitive_paths(body)
        if sensitive:
            raise SolveControlManifestError(
                f"control component contains sensitive fields {sensitive}")
        unresolved = _unique_text(
            self.unresolved_fields, "unresolved_fields")
        if self.status == "exact" and unresolved:
            raise SolveControlManifestError(
                "an exact control component cannot have unresolved fields")
        if self.status == "unknown" and not unresolved:
            raise SolveControlManifestError(
                "an unknown control component must name what is unresolved")
        object.__setattr__(self, "unresolved_fields", unresolved)

    @classmethod
    def create(cls, component_id: str, status: str, body: dict,
               unresolved_fields: tuple[str, ...] = ()) \
            -> ControlComponentRecord:
        return cls(component_id, status, _canonical(body), unresolved_fields)

    @property
    def body(self) -> dict:
        return json.loads(self.body_json)

    def to_dict(self) -> dict:
        return {
            "record_type": self.schema_version,
            "component_id": self.component_id,
            "status": self.status,
            "body": self.body,
            "unresolved_fields": list(self.unresolved_fields),
        }

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def component_ref(self) -> str:
        return f"solve-control-component:sha256:{self.content_digest}"

    @classmethod
    def from_dict(cls, value: dict) -> ControlComponentRecord:
        expected = {"record_type", "component_id", "status", "body",
                    "unresolved_fields"}
        if not isinstance(value, dict) or set(value) != expected:
            raise SolveControlManifestError(
                "control component fields do not match v1")
        return cls(
            value["component_id"], value["status"],
            _canonical(value["body"]), tuple(value["unresolved_fields"]),
            value["record_type"])


@dataclass(frozen=True)
class PublicSolveControlManifest:
    """Complete pre-run control inventory for one bounded comparison."""

    manifest_id: str
    evidence_class: str
    components: tuple[ControlComponentRecord, ...]
    blocking_unknowns: tuple[str, ...] = ()
    nonblocking_unknowns: tuple[str, ...] = ()
    schema_version: str = "public_solve_control_manifest/v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest_id", _required(
            self.manifest_id, "manifest_id"))
        if self.evidence_class not in CONTROL_EVIDENCE_CLASSES:
            raise SolveControlManifestError("unknown control evidence class")
        items = tuple(self.components)
        if (any(not isinstance(item, ControlComponentRecord) for item in items)
                or tuple(item.component_id for item in items)
                != CONTROL_COMPONENT_IDS):
            raise SolveControlManifestError(
                "control manifest needs every component exactly once in order")
        blocking = _unique_text(self.blocking_unknowns, "blocking_unknowns")
        nonblocking = _unique_text(
            self.nonblocking_unknowns, "nonblocking_unknowns")
        if set(blocking) & set(nonblocking):
            raise SolveControlManifestError(
                "one unknown cannot be both blocking and nonblocking")
        unresolved = {
            field for item in items for field in item.unresolved_fields}
        if unresolved != set(blocking) | set(nonblocking):
            raise SolveControlManifestError(
                "manifest unknowns must exactly match component unknowns")
        if self.schema_version != "public_solve_control_manifest/v1":
            raise SolveControlManifestError(
                "unsupported public solve control manifest schema")
        object.__setattr__(self, "components", items)
        object.__setattr__(self, "blocking_unknowns", blocking)
        object.__setattr__(self, "nonblocking_unknowns", nonblocking)

    def to_dict(self) -> dict:
        return {
            "record_type": self.schema_version,
            "manifest_id": self.manifest_id,
            "evidence_class": self.evidence_class,
            "components": [item.to_dict() for item in self.components],
            "blocking_unknowns": list(self.blocking_unknowns),
            "nonblocking_unknowns": list(self.nonblocking_unknowns),
        }

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def control_set_digest(self) -> str:
        """Identity of the controls, excluding only the display manifest ID."""
        value = self.to_dict()
        value.pop("manifest_id")
        return _digest(value)

    @property
    def manifest_ref(self) -> str:
        return f"solve-control-manifest:sha256:{self.content_digest}"

    @property
    def record_ref(self) -> str:
        return self.manifest_ref

    def component(self, component_id: str) -> ControlComponentRecord:
        try:
            return next(item for item in self.components
                        if item.component_id == component_id)
        except StopIteration as exc:
            raise SolveControlManifestError(
                f"control component {component_id!r} is unavailable") from exc

    @classmethod
    def from_dict(cls, value: dict) -> PublicSolveControlManifest:
        expected = {"record_type", "manifest_id", "evidence_class",
                    "components", "blocking_unknowns", "nonblocking_unknowns"}
        if not isinstance(value, dict) or set(value) != expected:
            raise SolveControlManifestError(
                "public solve control manifest fields do not match v1")
        return cls(
            value["manifest_id"], value["evidence_class"],
            tuple(ControlComponentRecord.from_dict(item)
                  for item in value["components"]),
            tuple(value["blocking_unknowns"]),
            tuple(value["nonblocking_unknowns"]), value["record_type"])


@dataclass(frozen=True)
class StageControlApplicationCandidate:
    """Unverified candidate controls and packet digests for one stage."""

    control_manifest_ref: str
    control_manifest_digest: str
    control_set_digest: str
    stage_occurrence_ref: str
    mode: str
    source_state_revision: int
    base_state_digest: str
    base_packet_digest: str
    treatment_delta_digest: str
    final_packet_digest: str
    context_pack_digest: str
    prompt_digest: str
    realized_execution_json: str
    evaluator_binding_digest: str
    workspace_seed_digest: str
    schema_version: str = "stage_control_application_candidate/v1"

    def __post_init__(self) -> None:
        for name in ("control_manifest_ref", "stage_occurrence_ref"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        for name in (
            "control_manifest_digest", "control_set_digest",
            "base_state_digest",
            "base_packet_digest", "treatment_delta_digest",
            "final_packet_digest", "context_pack_digest", "prompt_digest",
            "evaluator_binding_digest", "workspace_seed_digest",
        ):
            object.__setattr__(self, name, _sha256(getattr(self, name), name))
        if self.control_manifest_ref != (
                "solve-control-manifest:sha256:"
                + self.control_manifest_digest):
            raise SolveControlManifestError(
                "stage application manifest ref and digest differ")
        if self.mode not in ASSISTANCE_MODES:
            raise SolveControlManifestError("stage control mode is invalid")
        if (isinstance(self.source_state_revision, bool)
                or not isinstance(self.source_state_revision, int)
                or self.source_state_revision < 0):
            raise SolveControlManifestError(
                "source_state_revision must be a non-negative integer")
        try:
            realized = json.loads(self.realized_execution_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise SolveControlManifestError(
                "realized execution must be canonical JSON") from exc
        if not isinstance(realized, dict) \
                or _canonical(realized) != self.realized_execution_json:
            raise SolveControlManifestError(
                "realized execution must be a canonical JSON object")
        if self.schema_version != "stage_control_application_candidate/v1":
            raise SolveControlManifestError(
                "unsupported stage control application candidate schema")

    @classmethod
    def create(cls, *, realized_execution: dict, **fields) \
            -> StageControlApplicationCandidate:
        return cls(realized_execution_json=_canonical(realized_execution),
                   **fields)

    def to_dict(self) -> dict:
        return {
            "record_type": self.schema_version,
            "control_manifest_ref": self.control_manifest_ref,
            "control_manifest_digest": self.control_manifest_digest,
            "control_set_digest": self.control_set_digest,
            "stage_occurrence_ref": self.stage_occurrence_ref,
            "mode": self.mode,
            "source_state_revision": self.source_state_revision,
            "base_state_digest": self.base_state_digest,
            "base_packet_digest": self.base_packet_digest,
            "treatment_delta_digest": self.treatment_delta_digest,
            "final_packet_digest": self.final_packet_digest,
            "context_pack_digest": self.context_pack_digest,
            "prompt_digest": self.prompt_digest,
            "realized_execution": json.loads(self.realized_execution_json),
            "evaluator_binding_digest": self.evaluator_binding_digest,
            "workspace_seed_digest": self.workspace_seed_digest,
        }

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def application_ref(self) -> str:
        return f"stage-control-application-candidate:sha256:{self.content_digest}"

    @classmethod
    def from_dict(cls, value: dict) -> StageControlApplicationCandidate:
        expected = {
            "record_type", "control_manifest_ref", "control_manifest_digest",
            "control_set_digest",
            "stage_occurrence_ref", "mode", "source_state_revision",
            "base_state_digest", "base_packet_digest", "treatment_delta_digest",
            "final_packet_digest", "context_pack_digest", "prompt_digest",
            "realized_execution", "evaluator_binding_digest",
            "workspace_seed_digest",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise SolveControlManifestError(
                "stage control application candidate fields do not match v1")
        fields = {key: item for key, item in value.items()
                  if key not in ("record_type", "realized_execution")}
        return cls.create(
            realized_execution=value["realized_execution"],
            schema_version=value["record_type"], **fields)


def record_control_manifest(owner_loop, manifest: PublicSolveControlManifest) \
        -> dict:
    """Let the owning Loop append the complete passive manifest before work."""
    if not isinstance(manifest, PublicSolveControlManifest):
        raise SolveControlManifestError(
            "record_control_manifest needs a typed manifest")
    events = getattr(getattr(owner_loop, "ledger", None), "events", None)
    if not isinstance(events, list):
        raise SolveControlManifestError(
            "control manifest needs the owning Loop ledger")
    if any(item.get("custom_kind") == "public_solve_control_manifest"
           for item in events):
        raise SolveControlManifestError(
            "one run can record its control manifest only once")
    if any(
            str(item.get("event") or "").startswith("model")
            or item.get("custom_kind") == "llm_work_packet_assembled"
            or str(item.get("custom_kind") or "").startswith("stage_")
            for item in events):
        raise SolveControlManifestError(
            "control manifest must precede stage and model work")
    owner_loop.ledger.record(
        loop_id=owner_loop.loop_id, event="custom",
        custom_kind="public_solve_control_manifest",
        control_manifest_ref=manifest.manifest_ref,
        control_manifest_digest=manifest.content_digest,
        control_evidence_class=manifest.evidence_class,
        control_manifest=manifest.to_dict())
    return {
        "record_type": "recorded_solve_control_manifest/v1",
        "recorded": True,
        "control_manifest_ref": manifest.manifest_ref,
        "control_manifest_digest": manifest.content_digest,
        "control_set_digest": manifest.control_set_digest,
        "control_evidence_class": manifest.evidence_class,
    }


def self_test() -> dict[str, object]:
    """Prove strict, detached, content-addressed control records offline."""
    base_body = {"binding": "fixture", "known": True}
    components = tuple(ControlComponentRecord.create(
        name, "exact", {**base_body, "component": name})
        for name in CONTROL_COMPONENT_IDS)
    exact_mechanism = PublicSolveControlManifest(
        "exact-fixture", "mechanism_only", components)
    round_trip = PublicSolveControlManifest.from_dict(
        exact_mechanism.to_dict())
    base_body["late_mutation"] = True
    unknown = ControlComponentRecord.create(
        "model_execution", "unknown", {"provider": None},
        ("provider_revision",))
    mechanism_components = tuple(
        unknown if item.component_id == "model_execution" else item
        for item in components)
    mechanism = PublicSolveControlManifest(
        "mechanism-fixture", "mechanism_only", mechanism_components,
        ("provider_revision",))

    def refused(callable_) -> bool:
        try:
            callable_()
        except (TypeError, ValueError):
            return True
        return False

    application = StageControlApplicationCandidate.create(
        control_manifest_ref=mechanism.manifest_ref,
        control_manifest_digest=mechanism.content_digest,
        control_set_digest=mechanism.control_set_digest,
        stage_occurrence_ref="stage-occurrence.fixture",
        mode="fresh", source_state_revision=1,
        base_state_digest="a" * 64, base_packet_digest="b" * 64,
        treatment_delta_digest="c" * 64, final_packet_digest="d" * 64,
        context_pack_digest="e" * 64, prompt_digest="f" * 64,
        realized_execution={"provider": "fixture", "model": "fixture"},
        evaluator_binding_digest="1" * 64,
        workspace_seed_digest="2" * 64)
    events = []
    ledger = type("Ledger", (), {
        "record": lambda _self, **value: events.append(value)})()
    ledger.events = events
    owner = type("Owner", (), {
        "loop_id": "loop.fixture",
        "ledger": ledger,
    })()
    record_control_manifest(owner, mechanism)
    tests = [{
        "test": "complete_exact_manifest_remains_mechanism_only",
        "passed": exact_mechanism.evidence_class == "mechanism_only"
        and len(exact_mechanism.components) == len(CONTROL_COMPONENT_IDS),
    }, {
        "test": "manifest_round_trip_preserves_content_identity",
        "passed": round_trip == exact_mechanism
        and round_trip.manifest_ref == exact_mechanism.manifest_ref
        and PublicSolveControlManifest(
            "another-display-id", "mechanism_only", components
        ).manifest_ref != exact_mechanism.manifest_ref
        and PublicSolveControlManifest(
            "another-display-id", "mechanism_only", components
        ).control_set_digest == exact_mechanism.control_set_digest,
    }, {
        "test": "component_body_is_detached_from_caller_mutation",
        "passed": "late_mutation" not in components[0].body,
    }, {
        "test": "unknown_component_keeps_mechanism_evidence_bounded",
        "passed": mechanism.evidence_class == "mechanism_only"
        and mechanism.blocking_unknowns == ("provider_revision",),
    }, {
        "test": "paired_candidate_claim_is_not_an_admitted_evidence_class",
        "passed": refused(lambda: PublicSolveControlManifest(
            "overclaim", "paired_candidate", mechanism_components,
            ("provider_revision",))),
    }, {
        "test": "missing_or_reordered_component_is_refused",
        "passed": refused(lambda: PublicSolveControlManifest(
            "missing", "mechanism_only", components[:-1]))
        and refused(lambda: PublicSolveControlManifest(
            "reordered", "mechanism_only", tuple(reversed(components)))),
    }, {
        "test": "unlisted_component_unknown_is_refused",
        "passed": refused(lambda: PublicSolveControlManifest(
            "unlisted", "mechanism_only", mechanism_components)),
    }, {
        "test": "nonfinite_or_nonjson_control_body_is_refused",
        "passed": refused(lambda: ControlComponentRecord.create(
            "task_and_source", "exact", {"bad": float("nan")}))
        and refused(lambda: ControlComponentRecord.create(
            "task_and_source", "exact", {"bad": object()}))
        and refused(lambda: ControlComponentRecord.create(
            "task_and_source", "exact", {"nested": {"api_key": "private"}})),
    }, {
        "test": "stage_application_binds_realized_execution_and_all_digests",
        "passed": application.to_dict()["realized_execution"]["model"]
        == "fixture" and application.application_ref.startswith(
            "stage-control-application-candidate:sha256:")
        and StageControlApplicationCandidate.from_dict(application.to_dict())
        == application,
    }, {
        "test": "owning_loop_records_complete_manifest_before_execution",
        "passed": len(events) == 1
        and events[0]["control_manifest"] == mechanism.to_dict()
        and events[0]["control_manifest_digest"] == mechanism.content_digest
        and refused(lambda: record_control_manifest(owner, mechanism)),
    }]
    passed = sum(bool(item["passed"]) for item in tests)
    return {
        "record_type": "public_solve_control_manifest_checks/v1",
        "provider_calls": 0, "tests": tests,
        "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }


__all__ = (
    "ASSISTANCE_MODES", "CONTROL_COMPONENT_IDS", "CONTROL_EVIDENCE_CLASSES",
    "CONTROL_STATUSES", "ControlComponentRecord", "PublicSolveControlManifest",
    "SolveControlManifestError", "StageControlApplicationCandidate",
    "record_control_manifest", "self_test",
)
