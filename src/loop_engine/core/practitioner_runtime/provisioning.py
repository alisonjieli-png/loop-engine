"""Immutable configuration for assignment-folder provisioning.

Snapshots contain reference metadata and guardrail rules, never resource
bodies. This boundary grants no task effects, installs no code, and does not
establish independent admission or native loading.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json

from ..guardrail_intelligence import Guardrail, GuardrailSet, RECORD_TYPE as GUARDRAIL_RECORD_TYPE
from ..harness_intelligence import (
    HarnessIntelligenceCatalogue, HarnessIntelligenceItem,
    RECORD_TYPE as ITEM_RECORD_TYPE,
)
from ..intelligence_tagging import TagSet, RECORD_TYPE as TAG_RECORD_TYPE
from ..node_provisioning import NODE_KINDS

ENFORCED_GUARDRAIL_POINTS = ("before_provisioning",)
GUIDANCE_GUARDRAIL_POINTS = ("before_effect",)


class ProvisioningConfigurationError(ValueError):
    """A provisioning snapshot, selection, or authority binding is invalid."""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProvisioningConfigurationError("duplicate snapshot field")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def _tags(value):
    if not isinstance(value, dict) or value.get("record_type") != TAG_RECORD_TYPE:
        raise ProvisioningConfigurationError("tags require their current versioned record")
    return TagSet({key: item for key, item in value.items() if key != "record_type"})


def _item(value):
    expected = {"record_type", "identity", "kind", "purpose", "digest", "source_layer",
                "source_ref", "family", "size_bytes", "license", "declared_effects", "styles",
                "tags", "exposure", "availability", "body_included"}
    if (not isinstance(value, dict) or set(value) != expected
            or value["record_type"] != ITEM_RECORD_TYPE or value["body_included"] is not False):
        raise ProvisioningConfigurationError("catalogue snapshots require current body-free item references")
    return HarnessIntelligenceItem(
        identity=value["identity"], kind=value["kind"], purpose=value["purpose"],
        digest=value["digest"], source_layer=value["source_layer"], source_ref=value["source_ref"],
        size_bytes=value["size_bytes"], license_name=value["license"],
        declared_effects=tuple(value["declared_effects"]), styles=tuple(value["styles"]),
        default_exposure=value["exposure"], availability=value["availability"],
        family=value["family"], tags=_tags(value["tags"]))


def _rule(value):
    expected = {"record_type", "guardrail_id", "purpose", "category", "level", "point",
                "obligation", "judge", "scope", "applies_to", "on_unavailable",
                "evidence_required", "version", "source", "grants_nothing"}
    if (not isinstance(value, dict) or set(value) != expected
            or value["record_type"] != GUARDRAIL_RECORD_TYPE or value["grants_nothing"] is not True):
        raise ProvisioningConfigurationError("guardrails require their current no-grant record")
    return Guardrail(**{key: (_tags(item) if key == "applies_to" else tuple(item)
                             if key == "evidence_required" else item)
                       for key, item in value.items() if key not in ("record_type", "grants_nothing")})


@dataclass(frozen=True)
class HarnessResourceBinding:
    """One exact reference selection, not an execution or admission grant."""

    identity: str
    digest: str
    source_layer: str
    source_ref: str

    def __post_init__(self):
        if any(not isinstance(item, str) or not item.strip()
               for item in (self.identity, self.source_layer, self.source_ref)):
            raise ProvisioningConfigurationError("resource bindings need exact reference identities")
        if (not isinstance(self.digest, str) or len(self.digest) != 64
                or any(character not in "0123456789abcdef" for character in self.digest)):
            raise ProvisioningConfigurationError("resource bindings need an exact SHA-256 digest")

    @classmethod
    def from_item(cls, item):
        if not isinstance(item, HarnessIntelligenceItem):
            raise ProvisioningConfigurationError("resource selection requires a typed catalogue item")
        return cls(item.identity, item.digest, item.source_layer, item.source_ref)

    def to_dict(self):
        return {"record_type": "harness_resource_binding/v1", "identity": self.identity,
                "digest": self.digest, "source_layer": self.source_layer, "source_ref": self.source_ref}


@dataclass(frozen=True)
class HarnessAssignmentConfiguration:
    """Explicit behavior choice and metadata references for one assignment."""

    kind: str
    harness_style: str = ""
    resources: tuple[HarnessResourceBinding, ...] = ()
    tags_json: str = field(default_factory=lambda: _json(TagSet({}).to_dict()))
    workspace_effects: tuple[str, ...] | None = None
    allow_sandbox_commands: bool | None = None

    def __post_init__(self):
        if self.kind not in NODE_KINDS:
            raise ProvisioningConfigurationError(f"assignment kind must be one of {NODE_KINDS}")
        if not isinstance(self.harness_style, str):
            raise ProvisioningConfigurationError("harness style must be explicit text")
        if self.allow_sandbox_commands is not None and type(self.allow_sandbox_commands) is not bool:
            raise ProvisioningConfigurationError("sandbox command selection must be an explicit Boolean or absent")
        if self.workspace_effects is not None:
            values = self.workspace_effects
            if (type(values) not in (tuple, list)
                    or any(not isinstance(value, str) or value not in ("reads_fs", "writes_fs") for value in values)
                    or len(set(values)) != len(values)):
                raise ProvisioningConfigurationError("workspace effects must be explicit supported file effects")
            object.__setattr__(self, "workspace_effects", tuple(values))
        resources = tuple(self.resources)
        if any(not isinstance(item, HarnessResourceBinding) for item in resources):
            raise ProvisioningConfigurationError("resources must be exact typed reference bindings")
        if len({item.identity for item in resources}) != len(resources):
            raise ProvisioningConfigurationError("resource selections cannot repeat an identity")
        tags = _tags(_read_json(self.tags_json))
        object.__setattr__(self, "resources", resources)
        object.__setattr__(self, "tags_json", _json(tags.to_dict()))

    def to_dict(self):
        return {"record_type": "harness_assignment_configuration/v2", "kind": self.kind,
                "harness_style": self.harness_style,
                "workspace_effects": list(self.workspace_effects) if self.workspace_effects is not None else None,
                "allow_sandbox_commands": self.allow_sandbox_commands,
                "resources": [item.to_dict() for item in self.resources],
                "tags": json.loads(self.tags_json)}

    def tag_set(self):
        return _tags(_read_json(self.tags_json))


@dataclass(frozen=True)
class HarnessProvisioningConfiguration:
    """An exact immutable resource snapshot and explicit preparation policy."""

    assignment: HarnessAssignmentConfiguration
    catalogue_json: str = ""
    guardrails_json: str = ""
    assignment_overrides: tuple[tuple[str, HarnessAssignmentConfiguration], ...] = ()
    preparation_writes_authorized: bool = False
    schema_version: str = "harness_provisioning_configuration/v1"

    def __post_init__(self):
        if self.schema_version != "harness_provisioning_configuration/v1":
            raise ProvisioningConfigurationError("unsupported provisioning configuration version")
        if not isinstance(self.assignment, HarnessAssignmentConfiguration):
            raise ProvisioningConfigurationError("an explicit typed assignment choice is required")
        if type(self.preparation_writes_authorized) is not bool:
            raise ProvisioningConfigurationError("preparation writes require explicit Boolean authority")
        for field_name, record_type, factory, identity_name in (
                ("catalogue_json", "harness_catalogue_snapshot/v1", _item, "identity"),
                ("guardrails_json", "harness_guardrail_snapshot/v1", _rule, "guardrail_id")):
            raw = getattr(self, field_name)
            if not isinstance(raw, str):
                raise ProvisioningConfigurationError("resource snapshots must be canonical JSON text")
            if not raw:
                continue
            value = _read_json(raw)
            if (not isinstance(value, dict) or set(value) != {"record_type", "items"}
                    or value["record_type"] != record_type or not isinstance(value["items"], list)):
                raise ProvisioningConfigurationError("invalid current provisioning snapshot")
            items = [factory(item) for item in value["items"]]
            if field_name == "guardrails_json" and any(
                    item.point not in ENFORCED_GUARDRAIL_POINTS + GUIDANCE_GUARDRAIL_POINTS
                    for item in items):
                raise ProvisioningConfigurationError(
                    "assignment provisioning has no installed enforcement or guidance path for this guardrail point")
            if len({getattr(item, identity_name) for item in items}) != len(items):
                raise ProvisioningConfigurationError("snapshot identities must be unique")
            object.__setattr__(self, field_name, _json(value))
        overrides = tuple(self.assignment_overrides)
        if any(not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str)
               or not item[0].strip() or not isinstance(item[1], HarnessAssignmentConfiguration)
               for item in overrides):
            raise ProvisioningConfigurationError("assignment overrides require exact IDs and typed choices")
        if len({identity for identity, _ in overrides}) != len(overrides):
            raise ProvisioningConfigurationError("assignment override IDs must be unique")
        object.__setattr__(self, "assignment_overrides", tuple(sorted(overrides, key=lambda item: item[0])))
        for choice in (self.assignment, *(item[1] for item in overrides)):
            self.catalogue_for(choice)

    @classmethod
    def bind(cls, *, assignment, catalogue=None, guardrails=None, assignment_overrides=(),
             preparation_writes_authorized=False):
        if catalogue is not None and not isinstance(catalogue, HarnessIntelligenceCatalogue):
            raise ProvisioningConfigurationError("catalogue must be the existing typed catalogue")
        if guardrails is not None and not isinstance(guardrails, GuardrailSet):
            raise ProvisioningConfigurationError("guardrails must be the existing typed rule set")
        return cls(assignment=assignment,
            catalogue_json=(_json({"record_type": "harness_catalogue_snapshot/v1",
                "items": [item.reference() for _, item in sorted(catalogue.items.items())]})
                if catalogue is not None else ""),
            guardrails_json=(_json({"record_type": "harness_guardrail_snapshot/v1",
                "items": [item.to_dict() for _, item in sorted(guardrails.rules.items())]})
                if guardrails is not None else ""),
            assignment_overrides=tuple(assignment_overrides),
            preparation_writes_authorized=preparation_writes_authorized)

    def assignment_for(self, assignment_id):
        return dict(self.assignment_overrides).get(assignment_id, self.assignment)

    def catalogue_for(self, choice):
        if not self.catalogue_json:
            if choice.resources:
                raise ProvisioningConfigurationError("resource bindings have no catalogue snapshot")
            return None
        entries = tuple(_item(value) for value in _read_json(self.catalogue_json)["items"])
        items = {item.identity: item for item in entries}
        selected = HarnessIntelligenceCatalogue()
        for binding in choice.resources:
            item = items.get(binding.identity)
            if item is None or HarnessResourceBinding.from_item(item) != binding:
                raise ProvisioningConfigurationError("resource binding does not match the exact catalogue snapshot")
            selected.register(replace(item, default_exposure="metadata_only"))
        return selected

    def guardrail_set(self):
        if not self.guardrails_json:
            return None
        rules = GuardrailSet()
        for value in json.loads(self.guardrails_json)["items"]:
            rules.register(_rule(value))
        return rules

    def to_dict(self):
        return {"record_type": self.schema_version,
                "assignment": self.assignment.to_dict(),
                "assignment_overrides": [{"assignment_id": identity, "configuration": choice.to_dict()}
                                         for identity, choice in self.assignment_overrides],
                "catalogue_digest": _digest(self.catalogue_json) if self.catalogue_json else None,
                "guardrails_digest": _digest(self.guardrails_json) if self.guardrails_json else None,
                "catalogue_items": len(json.loads(self.catalogue_json)["items"]) if self.catalogue_json else None,
                "guardrails": len(json.loads(self.guardrails_json)["items"]) if self.guardrails_json else None,
                "preparation_writes_authorized": self.preparation_writes_authorized,
                "guardrail_supported_enforcement_points": list(ENFORCED_GUARDRAIL_POINTS),
                "guardrail_guidance_only_points": list(GUIDANCE_GUARDRAIL_POINTS),
                "dispatch_or_publication_guardrails_installed": False,
                "resource_bodies_included": False, "resource_admission_established": False,
                "native_loading_observed": False}

    @property
    def content_digest(self):
        return _digest(_json(self.to_dict()))


def provisioning_summary(configuration, spawned_results):
    records = [item["provisioning"] for item in spawned_results
               if isinstance(item, dict) and isinstance(item.get("provisioning"), dict)]
    return {"record_type": "solve_harness_provisioning/v1",
            "configured": configuration is not None,
            "configuration_digest": configuration.content_digest if configuration is not None else None,
            "configuration": configuration.to_dict() if configuration is not None else None,
            "absence_reason": "not_configured" if configuration is None else "",
            "assignments": records, "provisioned_assignments": sum(item.get("provisioned") is True for item in records),
            "resource_bodies_installed": 0, "native_loading_observed": False}
