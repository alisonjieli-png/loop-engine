"""Passive catalog projection of an immutable LoopDefinition.

The projection supports search and storage. It never executes. The executable
object is ``Loop``; the authoritative description is ``LoopDefinition``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..loop.loop_control import EXIT_CONDITIONS, LOOP_CONDITIONS
from ..loop.loop_definition import LoopDefinition, LoopDefinitionError
from ..loop.loop_role import LOOP_ROLES
from .artifacts import SOURCE_CLASSES
from .records import CatalogRecord, ObjectIdentity, OntologyRecordError

_MODES = ("deterministic", "hybrid", "non_deterministic")
_RECORD_KEYS = frozenset({
    "identity", "kind", "artifact_kind", "source_class", "layer",
    "lifecycle", "parent_collection", "input_roles", "output_roles",
    "role", "role_profile_id", "role_profile_version", "supported_modes",
    "step_profile", "loop_condition", "exit_condition", "effects",
    "permissions", "required_capabilities",
})


@dataclass(frozen=True)
class LoopDefinitionProjectionRequest:
    """Passive request for one definition-to-catalog projection."""

    definition: LoopDefinition
    source_class: str = "core"
    layer: str = ""
    parent_collection: str = ""


@dataclass(frozen=True)
class LoopDefinitionRecord(CatalogRecord):
    """Searchable at-rest projection of one authoritative definition."""

    role: str = ""
    role_profile_id: str = ""
    role_profile_version: str = ""
    supported_modes: tuple[str, ...] = ()
    step_profile: str = ""
    loop_condition: str = ""
    exit_condition: str = ""
    effects: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.kind != "loop_definition_record":
            raise OntologyRecordError(
                "LoopDefinitionRecord requires kind "
                "'loop_definition_record'")
        if self.role not in LOOP_ROLES:
            raise OntologyRecordError(f"role must be one of {LOOP_ROLES}")
        for label, value in (("role_profile_id", self.role_profile_id),
                             ("step_profile", self.step_profile)):
            if not isinstance(value, str) or not value.strip():
                raise OntologyRecordError(
                    f"{label} must be a non-empty string")
        unknown = [mode for mode in self.supported_modes
                   if mode not in _MODES]
        if not self.supported_modes or unknown:
            raise OntologyRecordError(
                f"supported_modes must be members of {_MODES}; "
                f"rejected: {unknown}")
        if self.loop_condition not in LOOP_CONDITIONS:
            raise OntologyRecordError(
                f"loop_condition must be one of {LOOP_CONDITIONS}")
        if self.exit_condition not in EXIT_CONDITIONS:
            raise OntologyRecordError(
                f"exit_condition must be one of {EXIT_CONDITIONS}")

    def to_dict(self) -> dict[str, Any]:
        value = super().to_dict()
        value.update({
            "role": self.role,
            "role_profile_id": self.role_profile_id,
            "role_profile_version": self.role_profile_version,
            "supported_modes": list(self.supported_modes),
            "step_profile": self.step_profile,
            "loop_condition": self.loop_condition,
            "exit_condition": self.exit_condition,
            "effects": list(self.effects),
            "permissions": list(self.permissions),
            "required_capabilities": list(self.required_capabilities),
        })
        return value

    @classmethod
    def from_mapping(cls, value: dict) -> "LoopDefinitionRecord":
        if not isinstance(value, dict) or set(value) != _RECORD_KEYS:
            raise OntologyRecordError(
                "LoopDefinition record has an invalid shape")
        kind = value["kind"]
        if kind == "loop_node":
            kind = "loop_definition_record"
        return cls(
            identity=ObjectIdentity.from_mapping(value["identity"]),
            kind=kind,
            artifact_kind=value["artifact_kind"],
            source_class=value["source_class"],
            layer=value["layer"],
            lifecycle=value["lifecycle"],
            parent_collection=value["parent_collection"],
            input_roles=tuple(value["input_roles"]),
            output_roles=tuple(value["output_roles"]),
            role=value["role"],
            role_profile_id=value["role_profile_id"],
            role_profile_version=value["role_profile_version"],
            supported_modes=tuple(value["supported_modes"]),
            step_profile=value["step_profile"],
            loop_condition=value["loop_condition"],
            exit_condition=value["exit_condition"],
            effects=tuple(value["effects"]),
            permissions=tuple(value["permissions"]),
            required_capabilities=tuple(value["required_capabilities"]),
        )

    @classmethod
    def from_definition(
            cls, request: LoopDefinitionProjectionRequest
    ) -> "LoopDefinitionRecord":
        """Project one authoritative definition without creating runtime work."""
        definition = request.definition
        if not isinstance(definition, LoopDefinition):
            raise OntologyRecordError(
                "projection request needs a LoopDefinition")
        if request.source_class not in SOURCE_CLASSES:
            raise OntologyRecordError(
                f"source_class must be one of {SOURCE_CLASSES}")
        try:
            return cls(
                identity=ObjectIdentity(
                    definition.definition_id,
                    definition.version,
                    definition.content_digest),
                kind="loop_definition_record",
                artifact_kind="loop_definition",
                source_class=request.source_class,
                layer=request.layer,
                lifecycle="registered",
                parent_collection=request.parent_collection,
                input_roles=tuple(definition.contract.input_roles),
                output_roles=tuple(definition.contract.output_roles),
                role=definition.contract.role,
                role_profile_id=definition.role_profile_id,
                role_profile_version=definition.role_profile_version,
                supported_modes=tuple(definition.supported_modes),
                step_profile=definition.step_profile,
                loop_condition=definition.loop_condition,
                exit_condition=definition.exit_condition,
                effects=tuple(definition.effects),
                permissions=tuple(definition.permissions),
                required_capabilities=tuple(
                    definition.required_capabilities),
            )
        except LoopDefinitionError as exc:
            raise OntologyRecordError(
                f"definition projection refused: {exc}") from exc


def self_test() -> dict:
    """Prove legacy input migrates and canonical output never re-emits it."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    legacy = {
        "identity": {"object_id": "definition.legacy.example",
                     "version": "1.0.0", "content_digest": "a" * 64},
        "kind": "loop_node", "artifact_kind": "loop_definition",
        "source_class": "core", "layer": "", "lifecycle": "registered",
        "parent_collection": "", "input_roles": ["task.input"],
        "output_roles": ["task.result"], "role": "practitioner",
        "role_profile_id": "practitioner.solver",
        "role_profile_version": "1.0.0",
        "supported_modes": ["deterministic"],
        "step_profile": "atomic", "loop_condition": "steps_remain",
        "exit_condition": "steps_complete", "effects": [],
        "permissions": [], "required_capabilities": [],
    }
    from .loop_node import read_legacy_loop_node_record
    migrated = read_legacy_loop_node_record(legacy)
    check("legacy_kind_migrates_to_definition_record",
          isinstance(migrated, LoopDefinitionRecord)
          and migrated.kind == "loop_definition_record")
    emitted = migrated.to_dict()
    check("canonical_projection_never_emits_legacy_kind",
          emitted["kind"] == "loop_definition_record"
          and "loop_node" not in emitted.values())
    check("definition_record_is_passive",
          not any(hasattr(migrated, name)
                  for name in ("run", "execute", "invoke")))
    refused = False
    try:
        read_legacy_loop_node_record({**legacy, "kind": "catalog_record"})
    except ValueError:
        refused = True
    check("legacy_reader_is_exact", refused)
    return {"tests": tests, "passed": sum(item["passed"] for item in tests),
            "total": len(tests), "all_passed": all(
                item["passed"] for item in tests)}


__all__ = (
    "LoopDefinitionProjectionRequest", "LoopDefinitionRecord",
)
