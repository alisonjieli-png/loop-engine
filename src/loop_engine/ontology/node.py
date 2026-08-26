"""The foundational CatalogRecord object: one passive persistent record at rest.

A ``CatalogRecord`` is a catalog record. It is not executable, it is not a
runtime graph vertex, and it never runs work. The only executable
specialization is ``loop_engine.ontology.loop_node.LoopNode``, and even
that names a definition at rest: execution still starts only through the
canonical ``LoopStartRequest`` into the one ``Loop`` runtime.

HARD ONTOLOGY INVARIANT: Node is a category and namespace only. There is
no concrete Node class. LoopNode is the only node-named class, and it is
a record at rest, not a runtime.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .artifacts import (
    ARTIFACT_KINDS,
    ONTOLOGY_OBJECT_KINDS,
    SOURCE_CLASSES,
)

_ID = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")

#: Lifecycle states reuse the existing asset lifecycle vocabulary.
_LIFECYCLE_STATES = (
    "draft", "candidate", "validated", "registered", "preferred",
    "deprecated", "retired",
)


class NodeError(ValueError):
    """A catalog node, its identity, or its classification is invalid."""


def _roles(label: str, values) -> tuple[str, ...]:
    normalized = tuple(values or ())
    if any(not isinstance(v, str) or not _ID.fullmatch(v) for v in normalized):
        raise NodeError(f"{label} must use lowercase dotted identifiers")
    if len(normalized) != len(set(normalized)):
        raise NodeError(f"{label} cannot contain duplicates")
    return tuple(sorted(normalized))


@dataclass(frozen=True)
class ObjectIdentity:
    """Stable identity triple shared by every ontological object."""

    object_id: str
    version: str
    content_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.object_id, str) or not _ID.fullmatch(
                self.object_id):
            raise NodeError("object_id must use lowercase dotted names")
        if not isinstance(self.version, str) or not _SEMVER.fullmatch(
                self.version):
            raise NodeError("version must use MAJOR.MINOR.PATCH")
        if not isinstance(self.content_digest, str) or not _DIGEST.fullmatch(
                self.content_digest):
            raise NodeError(
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
            raise NodeError("identity has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class CatalogRecord:
    """One passive persistent record in the Loop Engine ontology.

    Classification axes stay separate on purpose: provenance (core,
    learned, plugin) says where a record came from; the layer says which
    persistent intelligence collection it belongs to, when any; the
    lifecycle state says whether independent review has admitted it.
    None of these grant execution authority.
    """

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
            raise NodeError(f"kind must be one of {ONTOLOGY_OBJECT_KINDS}")
        if self.artifact_kind not in ARTIFACT_KINDS:
            raise NodeError(f"artifact_kind must be one of {ARTIFACT_KINDS}")
        if self.source_class not in SOURCE_CLASSES:
            raise NodeError(f"source_class must be one of {SOURCE_CLASSES}")
        if self.lifecycle not in _LIFECYCLE_STATES:
            raise NodeError(
                f"lifecycle must be one of {_LIFECYCLE_STATES}")
        if self.parent_collection and not _ID.fullmatch(
                self.parent_collection):
            raise NodeError(
                "parent_collection must use lowercase dotted names")
        if self.kind == "loop_node" and self.lifecycle not in (
                "registered", "preferred"):
            raise NodeError(
                "a loop_node catalog record must be registered or preferred;"
                " candidates are staged under governance, not executed")
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
            raise NodeError("catalog record has an invalid shape")
        return cls(
            identity=ObjectIdentity.from_mapping(value["identity"]),
            kind=value["kind"],
            artifact_kind=value["artifact_kind"],
            source_class=value["source_class"],
            layer=value["layer"],
            lifecycle=value["lifecycle"],
            parent_collection=value["parent_collection"],
            input_roles=tuple(value["input_roles"]),
            output_roles=tuple(value["output_roles"]),
        )
