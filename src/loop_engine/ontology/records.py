"""Passive ontology records and their stable identities.

Records describe persisted facts. They never execute work or become graph
vertices. The executable runtime is ``Loop`` in ``loop.recursive_loop``.
"""
from __future__ import annotations

import re
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .artifacts import ARTIFACT_KINDS, ONTOLOGY_OBJECT_KINDS, SOURCE_CLASSES

_ID = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_LIFECYCLE_STATES = (
    "draft", "candidate", "validated", "registered", "preferred",
    "deprecated", "retired",
)
_LEGACY_KIND_MIGRATIONS = {
    "node": "catalog_record",
    "loop_node": "loop_definition_record",
}


class OntologyRecordError(ValueError):
    """A passive ontology record or its classification is invalid."""


@dataclass(frozen=True)
class StableIdentityRequest:
    """Canonical content-addressed identity input for a passive object."""

    prefix: str
    components: tuple[object, ...]
    digest_length: int = 16
    separator: str = "."

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", self.prefix):
            raise OntologyRecordError("identity prefix is invalid")
        if not 8 <= self.digest_length <= 64:
            raise OntologyRecordError(
                "identity digest_length must be between 8 and 64")
        if self.separator not in (".", ":"):
            raise OntologyRecordError("identity separator must be dot or colon")


def stable_content_id(request: StableIdentityRequest) -> str:
    """Return one cross-process stable identity from canonical JSON fields."""
    if not isinstance(request, StableIdentityRequest):
        raise TypeError("stable_content_id needs StableIdentityRequest")
    encoded = json.dumps(
        request.components, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, default=str).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:request.digest_length]
    return f"{request.prefix}{request.separator}{digest}"


def _roles(label: str, values) -> tuple[str, ...]:
    normalized = tuple(values or ())
    if any(not isinstance(value, str) or not _ID.fullmatch(value)
           for value in normalized):
        raise OntologyRecordError(
            f"{label} must use lowercase dotted identifiers")
    if len(normalized) != len(set(normalized)):
        raise OntologyRecordError(f"{label} cannot contain duplicates")
    return tuple(sorted(normalized))


def canonical_record_kind(kind: str) -> str:
    """Map one immutable legacy spelling to its canonical record kind."""
    return _LEGACY_KIND_MIGRATIONS.get(kind, kind)


@dataclass(frozen=True)
class ObjectIdentity:
    """Stable identity triple shared by passive ontology objects."""

    object_id: str
    version: str
    content_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.object_id, str) or not _ID.fullmatch(
                self.object_id):
            raise OntologyRecordError(
                "object_id must use lowercase dotted names")
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(
                self.version):
            raise OntologyRecordError("version must use MAJOR.MINOR.PATCH")
        if not isinstance(self.content_digest, str) or not _DIGEST.fullmatch(
                self.content_digest):
            raise OntologyRecordError(
                "content_digest must be a lowercase SHA-256 digest")

    def to_dict(self) -> dict[str, str]:
        return {
            "object_id": self.object_id,
            "version": self.version,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_mapping(cls, value: dict) -> "ObjectIdentity":
        if not isinstance(value, dict) or set(value) != {
                "object_id", "version", "content_digest"}:
            raise OntologyRecordError("identity has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class CatalogRecord:
    """One passive persistent record in the Loop Engine ontology."""

    identity: ObjectIdentity
    kind: str
    artifact_kind: str
    source_class: str = "core"
    layer: str = ""
    lifecycle: str = "candidate"
    parent_collection: str = ""
    input_roles: tuple[str, ...] = field(default=())
    output_roles: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if self.kind not in ONTOLOGY_OBJECT_KINDS:
            raise OntologyRecordError(
                f"kind must be one of {ONTOLOGY_OBJECT_KINDS}")
        if self.artifact_kind not in ARTIFACT_KINDS:
            raise OntologyRecordError(
                f"artifact_kind must be one of {ARTIFACT_KINDS}")
        if self.source_class not in SOURCE_CLASSES:
            raise OntologyRecordError(
                f"source_class must be one of {SOURCE_CLASSES}")
        if self.lifecycle not in _LIFECYCLE_STATES:
            raise OntologyRecordError(
                f"lifecycle must be one of {_LIFECYCLE_STATES}")
        if self.parent_collection and not _ID.fullmatch(
                self.parent_collection):
            raise OntologyRecordError(
                "parent_collection must use lowercase dotted names")
        if self.kind == "loop_definition_record" and self.lifecycle not in (
                "registered", "preferred"):
            raise OntologyRecordError(
                "a LoopDefinition record must be registered or preferred; "
                "candidates remain in governed candidate storage")
        object.__setattr__(self, "input_roles",
                           _roles("input_roles", self.input_roles))
        object.__setattr__(self, "output_roles",
                           _roles("output_roles", self.output_roles))

    @property
    def is_candidate(self) -> bool:
        return self.lifecycle in ("draft", "candidate", "validated")

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "kind": self.kind,
            "artifact_kind": self.artifact_kind,
            "source_class": self.source_class,
            "layer": self.layer,
            "lifecycle": self.lifecycle,
            "parent_collection": self.parent_collection,
            "input_roles": list(self.input_roles),
            "output_roles": list(self.output_roles),
        }

    @classmethod
    def from_mapping(cls, value: dict) -> "CatalogRecord":
        required = {
            "identity", "kind", "artifact_kind", "source_class", "layer",
            "lifecycle", "parent_collection", "input_roles", "output_roles",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise OntologyRecordError("catalog record has an invalid shape")
        return cls(
            identity=ObjectIdentity.from_mapping(value["identity"]),
            kind=canonical_record_kind(value["kind"]),
            artifact_kind=value["artifact_kind"],
            source_class=value["source_class"],
            layer=value["layer"],
            lifecycle=value["lifecycle"],
            parent_collection=value["parent_collection"],
            input_roles=tuple(value["input_roles"]),
            output_roles=tuple(value["output_roles"]),
        )


def self_test() -> dict:
    """Prove record kinds and semantic identities are canonical and stable."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    left = stable_content_id(StableIdentityRequest(
        "candidate.semantic", ({"b": 2, "a": 1}, "scope")))
    right = stable_content_id(StableIdentityRequest(
        "candidate.semantic", ({"a": 1, "b": 2}, "scope")))
    check("canonical_identity_ignores_mapping_insertion_order",
          left == right and len(left.rsplit(".", 1)[-1]) == 16, left)
    check("legacy_record_kinds_migrate_without_reemission",
          canonical_record_kind("node") == "catalog_record"
          and canonical_record_kind("loop_node")
          == "loop_definition_record")
    return {"tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests), "all_passed": all(
                item["passed"] for item in tests)}


__all__ = (
    "CatalogRecord", "ObjectIdentity", "OntologyRecordError",
    "StableIdentityRequest", "canonical_record_kind", "stable_content_id",
)
