"""The LoopNode object: the at-rest definition of one executable vertex.

``LoopNode`` extends the passive ``CatalogRecord`` record with exactly the facts a
Loop definition carries: role, registered profile, supported modes, step
profile, loop condition, exit condition, effects, permissions, and
required capabilities. It adds no runtime. A ``LoopNode`` becomes live
work only when its matching ``LoopDefinitionRef`` resolves through the
existing registry and starts through ``LoopStartRequest``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..loop.loop_control import EXIT_CONDITIONS, LOOP_CONDITIONS
from ..loop.loop_definition import LoopDefinition, LoopDefinitionError
from ..loop.loop_role import LOOP_ROLES
from .artifacts import ONTOLOGY_OBJECT_KINDS, SOURCE_CLASSES
from .node import CatalogRecord, NodeError, ObjectIdentity

_MODES = ("deterministic", "hybrid", "non_deterministic")

_RECORD_KEYS = frozenset({
    "identity", "kind", "artifact_kind", "source_class", "layer",
    "lifecycle", "parent_collection", "input_roles", "output_roles",
    "role", "role_profile_id", "role_profile_version", "supported_modes",
    "step_profile", "loop_condition", "exit_condition", "effects",
    "permissions", "required_capabilities",
})


@dataclass(frozen=True)
class LoopNode(CatalogRecord):
    """One executable-vertex definition at rest; still never a runtime."""

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
        if self.kind != "loop_node":
            raise NodeError("LoopNode requires kind 'loop_node'")
        if self.role not in LOOP_ROLES:
            raise NodeError(f"role must be one of {LOOP_ROLES}")
        for label, value in (("role_profile_id", self.role_profile_id),
                             ("step_profile", self.step_profile)):
            if not isinstance(value, str) or not value.strip():
                raise NodeError(f"{label} must be a non-empty string")
        unknown = [m for m in self.supported_modes if m not in _MODES]
        if not self.supported_modes or unknown:
            raise NodeError(
                f"supported_modes must be non-empty members of {_MODES};"
                f" rejected: {unknown}")
        if self.loop_condition not in LOOP_CONDITIONS:
            raise NodeError(
                f"loop_condition must be one of {LOOP_CONDITIONS}")
        if self.exit_condition not in EXIT_CONDITIONS:
            raise NodeError(
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
    def from_mapping(cls, value: dict) -> "LoopNode":
        if not isinstance(value, dict) or set(value) != _RECORD_KEYS:
            raise NodeError("loop_node record has an invalid shape")
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
        cls,
        definition: LoopDefinition,
        *,
        source_class: str = "core",
        layer: str = "",
        parent_collection: str = "",
    ) -> "LoopNode":
        """Project an authoritative LoopDefinition into catalog form.

        The projection keeps the definition's own identity triple, so a
        catalog entry and its runtime definition share one digest and
        neither can drift from the other silently.
        """
        if not isinstance(definition, LoopDefinition):
            raise NodeError("from_definition needs a LoopDefinition")
        if source_class not in SOURCE_CLASSES:
            raise NodeError(f"source_class must be one of {SOURCE_CLASSES}")
        try:
            return cls(
                identity=ObjectIdentity(
                    object_id=definition.definition_id,
                    version=definition.version,
                    content_digest=definition.content_digest),
                kind="loop_node",
                artifact_kind="loop_definition",
                source_class=source_class,
                layer=layer,
                lifecycle="registered",
                parent_collection=parent_collection,
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
            raise NodeError(f"definition projection refused: {exc}") from exc
