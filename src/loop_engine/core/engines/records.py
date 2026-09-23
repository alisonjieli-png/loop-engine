"""Passive records that declare one engine of an engine slot, and the reader every engine record shares.

Owns engine_descriptor/v1 (the digested projection of an engine's native
declaration), engine_qualification/v1 and engine_retirement/v1 (architecture
6.2, 6.5 and 11.5), and the one strict reader and field rules that the host
records (core.engines.host_records), the policy and override
(core.engines.selection_records) and the decision
(core.engines.decision_records) also use: every record is name/vN and is
refused, before any effect, for another version, an unknown or a missing
field. Belongs to the shared engine framework (roadmap S-6.30). Never a
registry, a store, a selection procedure or a grant: nothing here imports,
probes or starts an engine, and no record grants model, file, network,
secret, spending or external-effect authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
import re
from types import MappingProxyType

from ..configuration_capabilities import (
    AVAILABILITY_STATES, QUALIFICATION_STATES, ConfigurationCapabilityError,
    ConfigurationFact, digest, exact_digest, exact_text)
from ..facets import COST_CLASSES, EFFECTS, LOCALITY
from ..harness_execution_contracts import (
    ISOLATIONS, LIMITS, frozen_harness_mapping, plain_harness_json, valid_harness_id)
from ..harness_selection_records import APPROVED, REVIEW_DECISIONS

DESCRIPTOR_RECORD_TYPE = "engine_descriptor/v1"
QUALIFICATION_RECORD_TYPE = "engine_qualification/v1"
RETIREMENT_RECORD_TYPE = "engine_retirement/v1"
#: The existing qualification record of a harness project. It stays the one
#: qualification source of its installation and is never copied.
HARNESS_PROJECT_QUALIFICATION_RECORD_TYPE = "harness_project_qualification/v1"
QUALIFICATION_SOURCE_RECORD_TYPES = (QUALIFICATION_RECORD_TYPE, HARNESS_PROJECT_QUALIFICATION_RECORD_TYPE)

UNKNOWN = "unknown"
MAIN_LOCATION = "main"
PURE_EFFECT = "pure"
#: Where a host configuration or policy came from: declared in a host or
#: settings file, or projected from a declaration that already exists.
DECLARED_SOURCE = "declared"
PROJECTED_SOURCE_PREFIX = "projected:"
COST_BASIS_KINDS = ("provider_reported", "price_record", UNKNOWN)
PRICE_RECORD_BASIS = "price_record"
PROOF_LEVELS = ("local_contract", "real_provider", "held_out_comparison", "end_to_end", "operational_drill")
#: The qualification ladder of roadmap S-6.31, lowest rung first.
QUALIFICATION_LADDER = ("connected", "material_listed", "material_loaded", "step_finished",
                        "independently_accepted")
DEPRECATED_STAGE, ARCHIVED_STAGE = "deprecated", "archived"
RETIREMENT_STAGES = (DEPRECATED_STAGE, ARCHIVED_STAGE)

_VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$")
_SLOT_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_CONTRACT = re.compile(r"^[a-z][a-z0-9_.-]{0,95}/v[1-9][0-9]*$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_ORIGIN = re.compile(r"^[a-z][a-z0-9+.-]*://[^\s/?#@]+$")
_CHECK = re.compile(r"^[a-z][a-z0-9_]{0,159}$")
_CHECKPOINT = re.compile(r"^checkpoint@[0-9a-f]{7,40}$")
_TEXT_LIMIT = 512


class EngineRecordError(ConfigurationCapabilityError):
    """An engine record is refused before any effect, with a stable code."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


# The one reader every engine record shares.

def read_record(record, record_type: str, fields: tuple[str, ...]) -> dict:
    """Return the record only when its type, version and field set are exact.

    Nothing is built from a record before this returns, so an unknown version
    or field is refused before any effect."""
    if type(record) is not dict:
        raise EngineRecordError("record_not_a_mapping", record_type + " must be a JSON object")
    _refuse_unsupported_version(record, record_type)
    expected = frozenset(fields) | {"record_type"}
    _refuse_unknown_fields(record, expected, record_type)
    _refuse_missing_fields(record, expected, record_type)
    return record


def read_part(value, name: str, fields: tuple[str, ...]) -> dict:
    """The same exact field rule for a part nested inside a record."""
    if type(value) is not dict:
        raise EngineRecordError("record_not_a_mapping", name + " must be a JSON object")
    _refuse_unknown_fields(value, frozenset(fields), name)
    _refuse_missing_fields(value, frozenset(fields), name)
    return value


def _refuse_unsupported_version(record, record_type):
    found = record.get("record_type")
    if found == record_type:
        return
    if type(found) is str and found.rpartition("/")[0] == record_type.rpartition("/")[0]:
        raise EngineRecordError("unsupported_record_version",
                                f"{found} is not read by this release, which reads {record_type}")
    raise EngineRecordError("unknown_record_type", "expected " + record_type)


def _refuse_unknown_fields(record, expected, name):
    unknown = sorted(str(key) for key in set(record) - expected)
    if unknown:
        raise EngineRecordError("unknown_record_fields", f"{name} carries unknown fields {unknown}")


def _refuse_missing_fields(record, expected, name):
    missing = sorted(expected - set(record))
    if missing:
        raise EngineRecordError("missing_record_fields", f"{name} lacks {missing}")


# Field rules. Each raises EngineRecordError with the field's name.

def identifier(value, name):
    if not valid_harness_id(value):
        raise EngineRecordError("invalid_identifier", name + " must match ^[a-z][a-z0-9_.-]{0,95}$")
    return value


def text(value, name, limit=_TEXT_LIMIT):
    try:
        exact_text(value, name)
    except ConfigurationCapabilityError as exc:
        raise EngineRecordError("invalid_text", str(exc)) from exc
    if len(value) > limit:
        raise EngineRecordError("invalid_text", f"{name} is longer than {limit} characters")
    return value


def sha256(value, name):
    try:
        exact_digest(value, name)
    except ConfigurationCapabilityError as exc:
        raise EngineRecordError("invalid_digest", str(exc)) from exc
    return value


def flag(value, name):
    if type(value) is not bool:
        raise EngineRecordError("invalid_boolean", name + " must be an explicit Boolean")
    return value


def pattern(value, name, expression, meaning):
    if type(value) is not str or not expression.fullmatch(value):
        raise EngineRecordError("invalid_field", f"{name} must be {meaning}")
    return value


def contract(value, name):
    return pattern(value, name, _CONTRACT, "an exact versioned contract name/vN")


def member(value, name, allowed):
    if type(value) is not str or value not in allowed:
        raise EngineRecordError("invalid_vocabulary", f"{name} must be one of {sorted(allowed)}")
    return value


def optional(value, rule, name):
    return None if value is None else rule(value, name)


def sequence(values, name, rule, *, nonempty=False):
    """A tuple of unique values, each passing its rule; order is kept."""
    if type(values) not in (tuple, list):
        raise EngineRecordError("invalid_sequence", name + " must be a sequence")
    values = tuple(values)
    if nonempty and not values:
        raise EngineRecordError("invalid_sequence", name + " must not be empty")
    for value in values:
        rule(value, name)
    if len(set(values)) != len(values):
        raise EngineRecordError("repeated_value", name + " must not repeat a value")
    return values


def identifiers(values, name, *, nonempty=False):
    return sequence(values, name, identifier, nonempty=nonempty)


def json_object(value, name):
    """A finite JSON object, frozen so that the record stays immutable."""
    if type(value) not in (dict, MappingProxyType):
        raise EngineRecordError("invalid_json_object", name + " must be a JSON object")
    try:
        return frozen_harness_mapping(value)
    except (ValueError, TypeError, RecursionError) as exc:
        raise EngineRecordError("invalid_json_object", name + " must be finite JSON data") from exc


def plain(value):
    return plain_harness_json(value)


def instant(value, name):
    """An ISO 8601 time with a timezone, written in one spelling (UTC)."""
    if type(value) is not str or not value:
        raise EngineRecordError("invalid_time", name + " must be ISO 8601 text")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EngineRecordError("invalid_time", name + " is not ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EngineRecordError("invalid_time", name + " needs a timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def calendar_date(value, name):
    try:
        if type(value) is str and date.fromisoformat(value).isoformat() == value:
            return value
    except ValueError:
        pass
    raise EngineRecordError("invalid_date", name + " must be a date written YYYY-MM-DD")


def fact(value, name, states):
    """A sourced ConfigurationFact kept in its own separate state vocabulary."""
    if isinstance(value, dict):
        try:
            value = ConfigurationFact.from_dict(value)
        except ConfigurationCapabilityError as exc:
            raise EngineRecordError("invalid_fact", f"{name}: {exc}") from exc
    if not isinstance(value, ConfigurationFact) or value.state not in states:
        raise EngineRecordError("invalid_fact", name + " must keep its separate fact state")
    return value


def fact_dict(value: ConfigurationFact) -> dict:
    return {"state": value.state, "source_ref": value.source_ref,
            "source_digest": value.source_digest, "expires_at": value.expires_at}


def engine_reference(value, name):
    """engine_id or engine_id@engine_version."""
    if type(value) is not str:
        raise EngineRecordError("invalid_engine_reference", name + " must be text")
    engine, separator, version = value.partition("@")
    identifier(engine, name)
    if separator:
        pattern(version, name, _VERSION, "a bounded engine version")
    return value


def exact_engine_ref(value, name):
    """engine_id@engine_version: the exact engine version that ran or was chosen."""
    engine_reference(value, name)
    if value.partition("@")[1] != "@":
        raise EngineRecordError("invalid_engine_reference", name + " names an exact engine version")
    return value


def slot_version(value, name):
    return pattern(value, name, _SLOT_VERSION, "a semantic version")


def slot_major(version: str) -> str:
    return version.split(".", 1)[0]


def declaration_source(value, name):
    """declared, or projected:<the existing declaration it was projected from>."""
    if value != DECLARED_SOURCE:
        if type(value) is not str or not value.startswith(PROJECTED_SOURCE_PREFIX):
            raise EngineRecordError("invalid_field", name + " is declared or projected:<declaration>")
        text(value[len(PROJECTED_SOURCE_PREFIX):], name)
    return value


@lru_cache(maxsize=1)
def _component_vocabularies():
    from ..component_contracts import load_component_ontology
    ontology = load_component_ontology()
    return tuple(ontology["modes"]), tuple(ontology["lifecycles"])


def engine_modes():
    return _component_vocabularies()[0]


def lifecycles():
    return _component_vocabularies()[1]


@lru_cache(maxsize=1)
def locality_vocabularies():
    """The repository's two locality vocabularies, each named by its source."""
    from ..model_routes import LOCALITIES
    return MappingProxyType({"core.facets.LOCALITY": LOCALITY,
                             "core.model_routes.LOCALITIES": LOCALITIES,
                             UNKNOWN: (UNKNOWN,)})


# Engine descriptor (architecture 6.2).

@dataclass(frozen=True)
class EngineLocality:
    """A locality named beside its vocabulary; two vocabularies never compare."""

    vocabulary: str
    value: str

    def __post_init__(self):
        member(self.vocabulary, "locality vocabulary", locality_vocabularies())
        member(self.value, "locality", locality_vocabularies()[self.vocabulary])

    def same_as(self, other: "EngineLocality") -> bool:
        if not isinstance(other, EngineLocality):
            raise EngineRecordError("invalid_field", "a locality is compared with a locality")
        _refuse_cross_vocabulary(self, other)
        return other.value == self.value

    def to_dict(self):
        return {"vocabulary": self.vocabulary, "value": self.value}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "locality", ("vocabulary", "value"))
        return cls(value["vocabulary"], value["value"])


@dataclass(frozen=True)
class EngineCostBasis:
    """How cost becomes known: provider-reported, a price record, or unknown."""

    kind: str
    price_record_ref: str | None
    price_record_digest: str | None
    read_on: str | None

    def __post_init__(self):
        member(self.kind, "cost basis", COST_BASIS_KINDS)
        parts = (self.price_record_ref, self.price_record_digest, self.read_on)
        if self.kind == PRICE_RECORD_BASIS:
            text(self.price_record_ref, "price record")
            sha256(self.price_record_digest, "price record digest")
            calendar_date(self.read_on, "price record date read")
        elif parts != (None, None, None):
            raise EngineRecordError("invalid_cost_basis", "only a price record basis names a price record")

    def to_dict(self):
        return {"kind": self.kind, "price_record_ref": self.price_record_ref,
                "price_record_digest": self.price_record_digest, "read_on": self.read_on}

    @classmethod
    def from_dict(cls, value):
        names = ("kind", "price_record_ref", "price_record_digest", "read_on")
        value = read_part(value, "cost basis", names)
        return cls(*(value[name] for name in names))


DESCRIPTOR_FIELDS = (
    "slot_id", "engine_id", "engine_version", "engine_ref", "engine_kind", "implementation_ref",
    "implementation_digest", "native_record_type", "native_record_digest", "capability_record",
    "capability_record_digest", "supported_edge_contracts", "supported_modes", "effects", "isolation",
    "locality", "data_recipients", "enforced_limits", "cost_class", "cost_basis", "licence", "source",
    "availability", "qualification", "lifecycle", "implementation_location", "checks")
#: Observation and governance fields. They change on their own schedule and
#: have their own sources, so they stay out of the identity digest: a renewed
#: availability observation or a lifecycle promotion is not a changed engine,
#: and a qualification can bind the digest without naming itself.
DESCRIPTOR_OBSERVATION_FIELDS = ("availability", "qualification", "lifecycle", "implementation_location")


@dataclass(frozen=True)
class EngineDescriptor:
    """The passive, digested projection of one engine's native declaration.

    Computed by a slot's projection from what the engine already declares in
    its own registry; never written by hand and never a grant."""

    slot_id: str
    engine_id: str
    engine_version: str
    engine_kind: str
    implementation_ref: str
    implementation_digest: str
    native_record_type: str
    native_record_digest: str
    capability_record: object
    supported_edge_contracts: tuple[str, ...]
    supported_modes: tuple[str, ...]
    effects: tuple[str, ...]
    isolation: str
    locality: EngineLocality
    data_recipients: tuple[str, ...]
    enforced_limits: tuple[str, ...]
    cost_class: str
    cost_basis: EngineCostBasis
    licence: str
    source_upstream: str
    source_revision: str
    availability: ConfigurationFact
    qualification: ConfigurationFact
    lifecycle: str
    implementation_location: str
    checks: tuple[str, ...]

    def __post_init__(self):
        set_ = object.__setattr__
        identifier(self.slot_id, "slot_id")
        identifier(self.engine_id, "engine_id")
        pattern(self.engine_version, "engine_version", _VERSION, "a bounded engine version")
        identifier(self.engine_kind, "engine_kind")
        pattern(self.implementation_ref, "implementation_ref", _SYMBOL, "a dotted symbol")
        sha256(self.implementation_digest, "implementation_digest")
        if type(self.native_record_type) is not str or not (
                _CONTRACT.fullmatch(self.native_record_type) or _SYMBOL.fullmatch(self.native_record_type)):
            raise EngineRecordError("invalid_field", "native_record_type must be name/vN or a dotted symbol")
        sha256(self.native_record_digest, "native_record_digest")
        set_(self, "capability_record", json_object(self.capability_record, "capability_record"))
        set_(self, "supported_edge_contracts",
             sequence(self.supported_edge_contracts, "supported_edge_contracts", contract, nonempty=True))
        set_(self, "supported_modes", sequence(
            self.supported_modes, "supported_modes", lambda v, n: member(v, n, engine_modes())))
        set_(self, "effects", sequence(self.effects, "effects", lambda v, n: member(v, n, EFFECTS)))
        if PURE_EFFECT in self.effects and len(self.effects) > 1:
            raise EngineRecordError("invalid_field", "the pure effect excludes every other effect")
        member(self.isolation, "isolation", ISOLATIONS)
        if not isinstance(self.locality, EngineLocality):
            raise EngineRecordError("invalid_field", "locality must be an EngineLocality")
        set_(self, "data_recipients", sequence(self.data_recipients, "data_recipients",
             lambda v, n: pattern(v, n, _ORIGIN, "an origin scheme://host[:port]")))
        set_(self, "enforced_limits", sequence(
            self.enforced_limits, "enforced_limits", lambda v, n: member(v, n, LIMITS)))
        member(self.cost_class, "cost_class", COST_CLASSES)
        if not isinstance(self.cost_basis, EngineCostBasis):
            raise EngineRecordError("invalid_field", "cost_basis must be an EngineCostBasis")
        text(self.licence, "licence", 128)
        text(self.source_upstream, "source upstream")
        text(self.source_revision, "source revision", 128)
        set_(self, "availability", fact(self.availability, "availability", AVAILABILITY_STATES))
        set_(self, "qualification", fact(self.qualification, "qualification", QUALIFICATION_STATES))
        member(self.lifecycle, "lifecycle", lifecycles())
        if self.implementation_location != MAIN_LOCATION:
            pattern(self.implementation_location, "implementation_location", _CHECKPOINT,
                    "main or checkpoint@<revision>")
        set_(self, "checks", sequence(self.checks, "checks",
             lambda v, n: pattern(v, n, _CHECK, "a named check")))

    @property
    def engine_ref(self) -> str:
        return f"{self.engine_id}@{self.engine_version}"

    @property
    def capability_record_digest(self) -> str:
        return digest(self.capability_record)

    @property
    def content_digest(self) -> str:
        """The engine's identity: every declared field, not the observations."""
        return digest(_descriptor_identity(self.to_dict()))

    def to_dict(self) -> dict:
        return {"record_type": DESCRIPTOR_RECORD_TYPE, "slot_id": self.slot_id, "engine_id": self.engine_id,
                "engine_version": self.engine_version, "engine_ref": self.engine_ref,
                "engine_kind": self.engine_kind, "implementation_ref": self.implementation_ref,
                "implementation_digest": self.implementation_digest,
                "native_record_type": self.native_record_type, "native_record_digest": self.native_record_digest,
                "capability_record": plain(self.capability_record),
                "capability_record_digest": self.capability_record_digest,
                "supported_edge_contracts": list(self.supported_edge_contracts),
                "supported_modes": list(self.supported_modes), "effects": list(self.effects),
                "isolation": self.isolation, "locality": self.locality.to_dict(),
                "data_recipients": list(self.data_recipients), "enforced_limits": list(self.enforced_limits),
                "cost_class": self.cost_class, "cost_basis": self.cost_basis.to_dict(), "licence": self.licence,
                "source": {"upstream": self.source_upstream, "revision": self.source_revision},
                "availability": fact_dict(self.availability), "qualification": fact_dict(self.qualification),
                "lifecycle": self.lifecycle, "implementation_location": self.implementation_location,
                "checks": list(self.checks)}

    @classmethod
    def from_dict(cls, record) -> "EngineDescriptor":
        record = read_record(record, DESCRIPTOR_RECORD_TYPE, DESCRIPTOR_FIELDS)
        source = read_part(record["source"], "source", ("upstream", "revision"))
        value = cls(
            record["slot_id"], record["engine_id"], record["engine_version"], record["engine_kind"],
            record["implementation_ref"], record["implementation_digest"], record["native_record_type"],
            record["native_record_digest"], record["capability_record"], record["supported_edge_contracts"],
            record["supported_modes"], record["effects"], record["isolation"],
            EngineLocality.from_dict(record["locality"]), record["data_recipients"], record["enforced_limits"],
            record["cost_class"], EngineCostBasis.from_dict(record["cost_basis"]), record["licence"],
            source["upstream"], source["revision"], fact(record["availability"], "availability",
            AVAILABILITY_STATES), fact(record["qualification"], "qualification", QUALIFICATION_STATES),
            record["lifecycle"], record["implementation_location"], record["checks"])
        require_derived(record, value.to_dict(), ("engine_ref", "capability_record_digest"))
        return value


def _descriptor_identity(record: dict) -> dict:
    return {name: value for name, value in record.items() if name not in DESCRIPTOR_OBSERVATION_FIELDS}


def _refuse_cross_vocabulary(locality, other):
    if other.vocabulary != locality.vocabulary:
        raise EngineRecordError("locality_vocabularies_differ",
                                "localities from two vocabularies are never compared")


def require_derived(record: dict, rebuilt: dict, names: tuple[str, ...]):
    """A stored derived value (a digest, a reference) must equal the recomputed one."""
    for name in names:
        if record[name] != rebuilt[name]:
            raise EngineRecordError("derived_value_mismatch", name + " does not match the record's content")


# Qualification (architecture 6.5).

@dataclass(frozen=True)
class QualificationScope:
    """What a qualification covers: the edge version, recipe variant and step contracts."""

    edge_contract: str
    recipe_variant: str | None
    step_contracts: tuple[str, ...]

    def __post_init__(self):
        contract(self.edge_contract, "qualified edge contract")
        optional(self.recipe_variant, identifier, "recipe variant")
        object.__setattr__(self, "step_contracts",
                           sequence(self.step_contracts, "step contracts", contract))

    def to_dict(self):
        return {"edge_contract": self.edge_contract, "recipe_variant": self.recipe_variant,
                "step_contracts": list(self.step_contracts)}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "qualification scope", ("edge_contract", "recipe_variant", "step_contracts"))
        return cls(value["edge_contract"], value["recipe_variant"], value["step_contracts"])


@dataclass(frozen=True)
class EvidenceReference:
    """One piece of evidence named by its reference and its SHA-256."""

    ref: str
    sha256: str

    def __post_init__(self):
        text(self.ref, "evidence reference", 1024)
        sha256(self.sha256, "evidence SHA-256")

    def to_dict(self):
        return {"ref": self.ref, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "evidence reference", ("ref", "sha256"))
        return cls(value["ref"], value["sha256"])


QUALIFICATION_FIELDS = ("slot_id", "engine_ref", "descriptor_digest", "installation_digest", "scope",
                        "proof_level", "ladder_rung", "evidence", "reviewer", "decision", "issued_at",
                        "expires_at")


@dataclass(frozen=True)
class EngineQualification:
    """An independent record that one engine installation passed, for a scope and proof level.

    Qualification binds the exact descriptor and installation digests, expires,
    and grants no authority. A step executor engine also names the highest rung
    of the qualification ladder it reached."""

    slot_id: str
    engine_ref: str
    descriptor_digest: str
    installation_digest: str
    scope: QualificationScope
    proof_level: str
    ladder_rung: str | None
    evidence: tuple[EvidenceReference, ...]
    reviewer: str
    decision: str
    issued_at: str
    expires_at: str

    def __post_init__(self):
        identifier(self.slot_id, "slot_id")
        exact_engine_ref(self.engine_ref, "engine_ref")
        sha256(self.descriptor_digest, "descriptor_digest")
        sha256(self.installation_digest, "installation_digest")
        if not isinstance(self.scope, QualificationScope):
            raise EngineRecordError("invalid_field", "scope must be a QualificationScope")
        member(self.proof_level, "proof_level", PROOF_LEVELS)
        if self.ladder_rung is not None:
            member(self.ladder_rung, "ladder_rung", QUALIFICATION_LADDER)
        evidence = tuple(self.evidence) if type(self.evidence) in (tuple, list) else None
        if not evidence or any(not isinstance(item, EvidenceReference) for item in evidence) \
                or len({item.ref for item in evidence}) != len(evidence):
            raise EngineRecordError("invalid_field", "a qualification cites unique evidence references")
        object.__setattr__(self, "evidence", evidence)
        text(self.reviewer, "reviewer")
        if self.reviewer in (self.engine_ref, self.engine_ref.partition("@")[0]):
            raise EngineRecordError("self_qualification", "an engine never qualifies itself")
        member(self.decision, "decision", REVIEW_DECISIONS)
        object.__setattr__(self, "issued_at", instant(self.issued_at, "issued_at"))
        object.__setattr__(self, "expires_at", instant(self.expires_at, "expires_at"))
        if datetime.fromisoformat(self.expires_at) <= datetime.fromisoformat(self.issued_at):
            raise EngineRecordError("invalid_time", "a qualification expires after it is issued")

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": QUALIFICATION_RECORD_TYPE, "slot_id": self.slot_id, "engine_ref": self.engine_ref,
                "descriptor_digest": self.descriptor_digest, "installation_digest": self.installation_digest,
                "scope": self.scope.to_dict(), "proof_level": self.proof_level, "ladder_rung": self.ladder_rung,
                "evidence": [item.to_dict() for item in self.evidence], "reviewer": self.reviewer,
                "decision": self.decision, "issued_at": self.issued_at, "expires_at": self.expires_at}

    @classmethod
    def from_dict(cls, record) -> "EngineQualification":
        record = read_record(record, QUALIFICATION_RECORD_TYPE, QUALIFICATION_FIELDS)
        if type(record["evidence"]) is not list:
            raise EngineRecordError("invalid_field", "evidence must be a list")
        return cls(record["slot_id"], record["engine_ref"], record["descriptor_digest"],
                   record["installation_digest"], QualificationScope.from_dict(record["scope"]),
                   record["proof_level"], record["ladder_rung"],
                   tuple(EvidenceReference.from_dict(item) for item in record["evidence"]),
                   record["reviewer"], record["decision"], record["issued_at"], record["expires_at"])

    def fact_for(self, descriptor: EngineDescriptor, installation_digest: str, *,
                 source_ref: str) -> ConfigurationFact:
        """The qualification as a sourced fact for exactly one engine installation.

        A qualification bound to another slot, engine version, descriptor or
        installation is refused rather than read as qualified; past its
        expiry the fact reads unknown."""
        if not isinstance(descriptor, EngineDescriptor):
            raise EngineRecordError("invalid_field", "a qualification is read against an EngineDescriptor")
        _refuse_unbound_qualification(self, descriptor, installation_digest)
        state = QUALIFIED_STATE if self.decision == APPROVED else UNQUALIFIED_STATE
        return ConfigurationFact(state, text(source_ref, "qualification source"), self.content_digest,
                                 _fact_expiry(self))


QUALIFIED_STATE, UNQUALIFIED_STATE = QUALIFICATION_STATES[0], QUALIFICATION_STATES[1]


def _refuse_unbound_qualification(qualification, descriptor, installation_digest):
    bound = (qualification.slot_id, qualification.engine_ref, qualification.descriptor_digest,
             qualification.installation_digest)
    if bound != (descriptor.slot_id, descriptor.engine_ref, descriptor.content_digest, installation_digest):
        raise EngineRecordError("qualification_scope_mismatch",
                                "the qualification binds another slot, engine version, descriptor or installation")


def _fact_expiry(qualification) -> str:
    return qualification.expires_at


# Retirement (architecture 11.5).

RETIREMENT_FIELDS = ("slot_id", "engine_id", "engine_version", "stage", "reason", "replacement",
                     "decision_ref", "decision_digest")


@dataclass(frozen=True)
class EngineRetirement:
    """Retire one engine, or one version of it, with a reason, replacement and decision.

    Deprecated: never an initial choice, still a valid fallback. Archived: a
    host that enables it is refused with the named replacement. A null
    engine_version retires every version of the engine."""

    slot_id: str
    engine_id: str
    engine_version: str | None
    stage: str
    reason: str
    replacement: str | None
    decision_ref: str
    decision_digest: str

    def __post_init__(self):
        identifier(self.slot_id, "slot_id")
        identifier(self.engine_id, "engine_id")
        if self.engine_version is not None:
            pattern(self.engine_version, "engine_version", _VERSION, "a bounded engine version")
        member(self.stage, "retirement stage", RETIREMENT_STAGES)
        text(self.reason, "retirement reason")
        if self.replacement is not None:
            engine_reference(self.replacement, "replacement")
            engine, _, version = self.replacement.partition("@")
            if engine == self.engine_id and (not version or version == self.engine_version
                                             or self.engine_version is None):
                raise EngineRecordError("invalid_field", "an engine is never its own replacement")
        text(self.decision_ref, "retirement decision")
        sha256(self.decision_digest, "retirement decision digest")

    def covers(self, engine_id: str, engine_version: str | None = None) -> bool:
        return engine_id == self.engine_id and (self.engine_version is None
                                                or engine_version == self.engine_version)

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": RETIREMENT_RECORD_TYPE, "slot_id": self.slot_id, "engine_id": self.engine_id,
                "engine_version": self.engine_version, "stage": self.stage, "reason": self.reason,
                "replacement": self.replacement, "decision_ref": self.decision_ref,
                "decision_digest": self.decision_digest}

    @classmethod
    def from_dict(cls, record) -> "EngineRetirement":
        record = read_record(record, RETIREMENT_RECORD_TYPE, RETIREMENT_FIELDS)
        return cls(*(record[name] for name in RETIREMENT_FIELDS))


def self_test():
    """Run the engine record checks."""
    from .records_checks import self_test as run_engine_record_checks
    return run_engine_record_checks()
