"""Universal passive component identity for Loop Engine semantic records.

``LoopComponentDefinition`` is not a runtime and never executes. It gives
settings, intelligence, questions, personas, packets, policies, capabilities,
and other semantic building blocks one versioned component vocabulary. Work on
those components still executes through the sole concrete ``Loop`` runtime.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.resources import files

import yaml

from ..ontology.records import ObjectIdentity


class LoopComponentError(ValueError):
    """A passive component definition, reference, or ontology is invalid."""


def component_payload_digest(value: object) -> str:
    """Canonical serializer boundary for passive component payload digests."""
    body = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_component_ontology() -> dict:
    """Load the one installed closed vocabulary for semantic components."""
    path = files("loop_engine").joinpath("data/component_ontology.yaml")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict)
            or value.get("record_type") != "loop_component_ontology/v1"):
        raise LoopComponentError("component ontology is invalid")
    for name in ("operationality", "component_kinds", "roles", "modes",
                 "lifecycles", "static_invariants"):
        values = value.get(name)
        if (not isinstance(values, list) or not values
                or len(values) != len(set(values))):
            raise LoopComponentError(
                f"component ontology {name} must be a unique list")
    return value


def load_component_resource(
        filename: str, expected_record_type: str) -> dict:
    """Load one installed component catalog with an exact record type."""
    if filename not in (
            "component_interactions.yaml", "component_folder_map.yaml"):
        raise LoopComponentError("component resource name is not registered")
    path = files("loop_engine").joinpath("data", filename)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict)
            or value.get("record_type") != expected_record_type):
        raise LoopComponentError("component resource contract is invalid")
    return value


@dataclass(frozen=True)
class LoopComponentDraft:
    """Cohesive input used to create one content-addressed component."""

    component_id: str
    semantic_version: str
    component_kind: str
    operationality: str
    payload_contract_ref: str
    payload_digest: str
    provenance: str
    role_affinities: tuple[str, ...] = ()
    mode_support: tuple[str, ...] = ()
    input_contract_refs: tuple[str, ...] = ()
    output_contract_refs: tuple[str, ...] = ()
    settings_refs: tuple[str, ...] = ()
    policy_refs: tuple[str, ...] = ()
    intelligence_refs: tuple[str, ...] = ()
    capability_refs: tuple[str, ...] = ()
    verification_refs: tuple[str, ...] = ()
    scope: str = "global"
    permissions: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    lifecycle: str = "active"
    compatibility: tuple[str, ...] = ()
    extension_points: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoopComponentDefinition:
    """Passive universal envelope for one semantic building block."""

    identity: ObjectIdentity
    component_kind: str
    operationality: str
    payload_contract_ref: str
    payload_digest: str
    provenance: str
    role_affinities: tuple[str, ...]
    mode_support: tuple[str, ...]
    input_contract_refs: tuple[str, ...]
    output_contract_refs: tuple[str, ...]
    settings_refs: tuple[str, ...]
    policy_refs: tuple[str, ...]
    intelligence_refs: tuple[str, ...]
    capability_refs: tuple[str, ...]
    verification_refs: tuple[str, ...]
    scope: str
    permissions: tuple[str, ...]
    effects: tuple[str, ...]
    lifecycle: str
    compatibility: tuple[str, ...]
    extension_points: tuple[str, ...]
    record_type: str = "loop_component_definition/v1"

    def __post_init__(self) -> None:
        ontology = load_component_ontology()
        if self.record_type != "loop_component_definition/v1":
            raise LoopComponentError("component record type is unsupported")
        if self.component_kind not in ontology["component_kinds"]:
            raise LoopComponentError("component kind is not registered")
        if self.operationality not in ontology["operationality"]:
            raise LoopComponentError("component operationality is not registered")
        if self.lifecycle not in ontology["lifecycles"]:
            raise LoopComponentError("component lifecycle is not registered")
        if any(item not in ontology["roles"] for item in self.role_affinities):
            raise LoopComponentError("component role affinity is invalid")
        if any(item not in ontology["modes"] for item in self.mode_support):
            raise LoopComponentError("component mode support is invalid")
        if self.operationality == "static" and (
                self.permissions or self.effects):
            raise LoopComponentError(
                "a static component cannot carry permission or effects")
        if not self.payload_contract_ref.strip() or not self.provenance.strip():
            raise LoopComponentError(
                "component payload contract and provenance are required")
        if (len(self.payload_digest) != 64
                or any(item not in "0123456789abcdef"
                       for item in self.payload_digest)):
            raise LoopComponentError("component payload digest is invalid")

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "identity": self.identity.to_dict(),
            "component_kind": self.component_kind,
            "operationality": self.operationality,
            "payload_contract_ref": self.payload_contract_ref,
            "payload_digest": self.payload_digest,
            "provenance": self.provenance,
            "role_affinities": list(self.role_affinities),
            "mode_support": list(self.mode_support),
            "input_contract_refs": list(self.input_contract_refs),
            "output_contract_refs": list(self.output_contract_refs),
            "settings_refs": list(self.settings_refs),
            "policy_refs": list(self.policy_refs),
            "intelligence_refs": list(self.intelligence_refs),
            "capability_refs": list(self.capability_refs),
            "verification_refs": list(self.verification_refs),
            "scope": self.scope,
            "permissions": list(self.permissions),
            "effects": list(self.effects),
            "lifecycle": self.lifecycle,
            "compatibility": list(self.compatibility),
            "extension_points": list(self.extension_points),
        }


def define_loop_component(draft: LoopComponentDraft) -> LoopComponentDefinition:
    """Validate a draft and return one immutable content-addressed definition."""
    if not isinstance(draft, LoopComponentDraft):
        raise LoopComponentError("define_loop_component needs a typed draft")
    body = {
        key: value for key, value in draft.__dict__.items()
        if key not in ("component_id", "semantic_version")}
    digest = component_payload_digest(body)
    return LoopComponentDefinition(
        ObjectIdentity(draft.component_id, draft.semantic_version, digest),
        draft.component_kind, draft.operationality,
        draft.payload_contract_ref, draft.payload_digest, draft.provenance,
        tuple(draft.role_affinities), tuple(draft.mode_support),
        tuple(draft.input_contract_refs), tuple(draft.output_contract_refs),
        tuple(draft.settings_refs), tuple(draft.policy_refs),
        tuple(draft.intelligence_refs), tuple(draft.capability_refs),
        tuple(draft.verification_refs), draft.scope,
        tuple(draft.permissions), tuple(draft.effects), draft.lifecycle,
        tuple(draft.compatibility), tuple(draft.extension_points))


@dataclass(frozen=True)
class LoopComponentRef:
    """Exact version and digest pointer to one passive component."""

    identity: ObjectIdentity
    expected_kind: str
    scope: str = "global"
    compatibility_requirement: str = "exact"

    def __post_init__(self) -> None:
        ontology = load_component_ontology()
        if (self.expected_kind not in ontology["component_kinds"]
                or not self.scope.strip()
                or not self.compatibility_requirement.strip()):
            raise LoopComponentError("component reference is invalid")

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "expected_kind": self.expected_kind, "scope": self.scope,
            "compatibility_requirement": self.compatibility_requirement,
        }


def self_test() -> dict:
    """Prove static passivity, closed kinds, and exact references."""
    static = define_loop_component(LoopComponentDraft(
        "core.persona.test", "1.0.0", "persona", "static",
        "persona_context/v1", "a" * 64, "core fixture"))
    refused = False
    try:
        define_loop_component(LoopComponentDraft(
            "core.persona.invalid", "1.0.0", "persona", "static",
            "persona_context/v1", "a" * 64, "core fixture",
            permissions=("network_read",)))
    except LoopComponentError:
        refused = True
    reference = LoopComponentRef(static.identity, "persona")
    interactions = load_component_resource(
        "component_interactions.yaml", "component_interaction_catalog/v1")
    folders = load_component_resource(
        "component_folder_map.yaml", "component_folder_map/v1")
    tests = [{
        "test": "static_component_is_inert_and_content_addressed",
        "passed": (not static.permissions and not static.effects
                   and len(static.identity.content_digest) == 64),
        "detail": static.identity.object_id,
    }, {
        "test": "static_component_cannot_grant_permission",
        "passed": refused, "detail": "refused before any operation",
    }, {
        "test": "component_ref_pins_version_digest_and_kind",
        "passed": (reference.identity == static.identity
                   and reference.expected_kind == "persona"),
        "detail": reference.identity.content_digest,
    }, {
        "test": "component_interactions_are_unique_and_typed",
        "passed": len({item["interaction_id"]
                       for item in interactions["interactions"]})
        == len(interactions["interactions"]),
        "detail": "machine interaction catalog loaded",
    }, {
        "test": "component_folder_owners_are_unique",
        "passed": len({item["path"] for item in folders["folders"]})
        == len(folders["folders"]),
        "detail": "machine folder map loaded",
    }]
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "loop_component_contract_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
