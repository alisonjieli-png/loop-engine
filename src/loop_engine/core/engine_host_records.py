"""Passive host configuration and host-start report records for engine slots.

Owns engine_installation/v1, engine_slot_configuration/v1,
service_host_engines/v1 and engine_bindings_report/v1 (architecture 6.3 and
6.6), and the rule that one installation has one qualification source.
Belongs to the shared engine framework (roadmap S-6.30), beside
core.engine_records, whose strict reader and field rules it uses. Never a
loader, a registry or a grant: an installation or a policy declares what a
host installed and switched on; it never enables an engine the registry does
not hold and never widens any permission.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from types import MappingProxyType

from .configuration_capabilities import digest
from .engine_records import (
    ARCHIVED_STAGE, DECLARED_SOURCE, HARNESS_PROJECT_QUALIFICATION_RECORD_TYPE, QUALIFICATION_SOURCE_RECORD_TYPES,
    EngineQualification, EngineRecordError, contract, declaration_source, exact_engine_ref, flag, identifier,
    json_object, member, plain, read_part, read_record, require_derived, sha256, slot_major, slot_version, text)
from .engine_selection_records import EngineSelectionPolicy
from .harness_execution_contracts import credential_metadata_present

INSTALLATION_RECORD_TYPE = "engine_installation/v1"
SLOT_CONFIGURATION_RECORD_TYPE = "engine_slot_configuration/v1"
SERVICE_HOST_ENGINES_RECORD_TYPE = "service_host_engines/v1"
BINDINGS_REPORT_RECORD_TYPE = "engine_bindings_report/v1"


@dataclass(frozen=True)
class FileReference:
    """A file named by its path and the SHA-256 of its bytes."""

    path: str
    sha256: str
    absolute: bool = False

    def __post_init__(self):
        text(self.path, "file path", 1024)
        sha256(self.sha256, "file SHA-256")
        if ".." in self.path.replace("\\", "/").split("/"):
            raise EngineRecordError("invalid_path", "a file reference never climbs out of its folder")
        if self.absolute and not os.path.isabs(self.path):
            raise EngineRecordError("invalid_path", "a host declaration is named by an absolute path")

    def to_dict(self):
        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class QualificationSource:
    """The one qualification source an installation names, with its record type."""

    record_type: str
    path: str
    sha256: str

    def __post_init__(self):
        member(self.record_type, "qualification source record type", QUALIFICATION_SOURCE_RECORD_TYPES)
        FileReference(self.path, self.sha256)

    def to_dict(self):
        return {"record_type": self.record_type, "path": self.path, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value):
        value = read_part(value, "qualification source", ("record_type", "path", "sha256"))
        return cls(value["record_type"], value["path"], value["sha256"])


INSTALLATION_FIELDS = ("installation_id", "engine_id", "engine_kind", "enabled", "settings", "settings_digest",
                       "declaration", "qualification", "installation_digest")


@dataclass(frozen=True)
class EngineInstallation:
    """One host's declaration that an engine is installed, with typed settings.

    Settings never carry authority or a credential: grants stay where the host
    already declares them, and credentials resolve through the host's secret
    references, never through engine settings."""

    installation_id: str
    engine_id: str
    engine_kind: str
    enabled: bool
    settings: object
    declaration: FileReference | None
    qualification: QualificationSource | None

    def __post_init__(self):
        identifier(self.installation_id, "installation_id")
        identifier(self.engine_id, "engine_id")
        identifier(self.engine_kind, "engine_kind")
        flag(self.enabled, "enabled")
        object.__setattr__(self, "settings", json_object(self.settings, "settings"))
        _refuse_credential_settings(self.settings)
        if self.declaration is not None and not (
                isinstance(self.declaration, FileReference) and self.declaration.absolute):
            raise EngineRecordError("invalid_field", "declaration must be an absolute FileReference or null")
        if self.qualification is not None and not isinstance(self.qualification, QualificationSource):
            raise EngineRecordError("invalid_field", "qualification must be a QualificationSource or null")

    @property
    def settings_digest(self) -> str:
        return digest(self.settings)

    @property
    def installation_digest(self) -> str:
        """Binds the engine, its settings and its declaration file."""
        return digest(_installation_identity(self))

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": INSTALLATION_RECORD_TYPE, "installation_id": self.installation_id,
                "engine_id": self.engine_id, "engine_kind": self.engine_kind, "enabled": self.enabled,
                "settings": plain(self.settings), "settings_digest": self.settings_digest,
                "declaration": None if self.declaration is None else self.declaration.to_dict(),
                "qualification": None if self.qualification is None else self.qualification.to_dict(),
                "installation_digest": self.installation_digest}

    @classmethod
    def from_dict(cls, record) -> "EngineInstallation":
        record = read_record(record, INSTALLATION_RECORD_TYPE, INSTALLATION_FIELDS)
        declaration = record["declaration"]
        if declaration is not None:
            declaration = read_part(declaration, "declaration", ("path", "sha256"))
            declaration = FileReference(declaration["path"], declaration["sha256"], absolute=True)
        qualification = record["qualification"]
        value = cls(record["installation_id"], record["engine_id"], record["engine_kind"], record["enabled"],
                    record["settings"], declaration,
                    None if qualification is None else QualificationSource.from_dict(qualification))
        require_derived(record, value.to_dict(), ("settings_digest", "installation_digest"))
        return value


def _installation_identity(installation: EngineInstallation) -> dict:
    """Everything that changes what the installed engine does. The enabled
    switch and the qualification reference stay out: a host qualifies an
    engine while it is switched off and then switches it on, and a
    qualification binds this digest, so it cannot also be part of it."""
    return {"record_type": INSTALLATION_RECORD_TYPE, "installation_id": installation.installation_id,
            "engine_id": installation.engine_id, "engine_kind": installation.engine_kind,
            "settings": plain(installation.settings),
            "declaration": None if installation.declaration is None else installation.declaration.to_dict()}


#: An address that carries user information before its host, the place a key hides in a URL.
_USER_INFORMATION = re.compile(r"[a-z][a-z0-9+.-]*://[^/\s?#]*@", re.IGNORECASE)
#: A key or token carried in the query of an address, as some provider interfaces accept one.
_QUERY_CREDENTIAL = re.compile(r"[?&](?:api[_-]?key|key|access[_-]?token|token|secret|password|sig)=",
                               re.IGNORECASE)
#: A bearer credential written as a value on its own.
_BEARER_VALUE = re.compile(r"^\s*bearer\s+\S+\s*$", re.IGNORECASE)
#: A header line ("Authorization: ...") or a command option ("--api-key", "--token=...") written as text.
_NAMED_TEXT = re.compile(r"^\s*(?:--?([A-Za-z][A-Za-z0-9_-]*)(?:=|$)|([A-Za-z][A-Za-z0-9_-]*)\s*:\s*\S)")
#: The words of a key name, so that api_key, apiKey, api-key, APIKey and OLLAMA_API_KEY compare alike.
_NAME_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+")
#: Credential names beside those core.harness_execution_contracts already refuses.
_MORE_CREDENTIAL_NAMES = ("apikey", "private_key", "access_key", "secret_key", "passphrase", "credential",
                          "credentials")


def _refuse_credential_settings(settings):
    if _credential_named(settings) or any(_credential_text(item) for item in _texts(settings)):
        raise EngineRecordError("credential_in_settings",
                                "engine settings never hold a credential; the host names it through its secret "
                                "references and the credential broker, outside every engine record")


def _credential_name(name) -> bool:
    """A key name that names a credential, in snake, camel, hyphenated or upper case spelling."""
    words = "_".join(word.lower() for word in _NAME_WORDS.findall(str(name)))
    return credential_metadata_present({words: None}) or any(
        words == word or words.endswith("_" + word) for word in _MORE_CREDENTIAL_NAMES)


def _credential_named(value) -> bool:
    if type(value) in (dict, MappingProxyType):
        return any(_credential_name(key) or _credential_named(item) for key, item in value.items())
    if type(value) in (list, tuple):
        return any(_credential_named(item) for item in value)
    return False


def _credential_text(value) -> bool:
    """Text shaped like a credential: user information in an address, a key in a query, a bearer
    value, or a header line or command option whose name is a credential name."""
    named = _NAMED_TEXT.match(value)
    return bool(_USER_INFORMATION.search(value) or _QUERY_CREDENTIAL.search(value) or _BEARER_VALUE.match(value)
                or (named and _credential_name(named.group(1) or named.group(2))))


def _texts(value):
    """Every text value inside frozen JSON settings."""
    if type(value) is str:
        yield value
    elif type(value) in (dict, MappingProxyType):
        for item in value.values():
            yield from _texts(item)
    elif type(value) in (list, tuple):
        for item in value:
            yield from _texts(item)


def admit_engine_qualification(installation: EngineInstallation, qualification: EngineQualification):
    """Refuse a second qualification source for one installation.

    An installation that already names a harness_project_qualification/v1
    keeps it as its one source, projected into the engine qualification shape
    and never copied into a second record. A renewal of an
    engine_qualification/v1 replaces the reference the installation names."""
    if not isinstance(installation, EngineInstallation) or not isinstance(qualification, EngineQualification):
        raise EngineRecordError("invalid_field", "admission needs an installation and a qualification")
    if qualification.installation_digest != installation.installation_digest:
        raise EngineRecordError("qualification_scope_mismatch", "the qualification binds another installation")
    _refuse_second_qualification_source(installation)
    return qualification


def _refuse_second_qualification_source(installation):
    source = installation.qualification
    if source is not None and source.record_type == HARNESS_PROJECT_QUALIFICATION_RECORD_TYPE:
        raise EngineRecordError("qualification_source_exists",
                                "this installation's one qualification source is its "
                                "harness_project_qualification/v1, projected and never copied")


SLOT_CONFIGURATION_FIELDS = ("slot_id", "slot_version", "installed", "selection", "source", "source_digest")


@dataclass(frozen=True)
class EngineSlotConfiguration:
    """One host record per slot: installed engines and one policy per scope key."""

    slot_id: str
    slot_version: str
    installed: tuple[EngineInstallation, ...]
    selection: object
    source: str
    source_digest: str

    def __post_init__(self):
        identifier(self.slot_id, "slot_id")
        slot_version(self.slot_version, "slot_version")
        if type(self.installed) not in (tuple, list) or any(
                not isinstance(item, EngineInstallation) for item in self.installed):
            raise EngineRecordError("invalid_field", "installed must be a sequence of EngineInstallation")
        installed = tuple(self.installed)
        object.__setattr__(self, "installed", installed)
        ids = [item.installation_id for item in installed]
        if len(set(ids)) != len(ids):
            raise EngineRecordError("repeated_value", "an installation identifier appears once per slot")
        by_engine = {}
        for item in installed:
            by_engine.setdefault(item.engine_id, []).append(item)
        for engine_id, items in by_engine.items():
            if len(items) == 1 and items[0].installation_id != engine_id:
                raise EngineRecordError("invalid_installation_id",
                                        "an engine installed once is named by its engine identifier")
            if len({item.engine_kind for item in items}) != 1:
                raise EngineRecordError("invalid_field", "one engine has one engine kind")
        if type(self.selection) not in (dict, MappingProxyType) or not self.selection:
            raise EngineRecordError("invalid_field", "selection maps each scope key to its policy")
        installations = {item.installation_id: item for item in installed}
        for key, policy in self.selection.items():
            identifier(key, "scope key")
            if not isinstance(policy, EngineSelectionPolicy) or policy.scope_key != key:
                raise EngineRecordError("invalid_field", "each scope key maps to its own policy")
            if policy.slot_id != self.slot_id or slot_major(policy.slot_version) != slot_major(self.slot_version):
                raise EngineRecordError("slot_version_mismatch", "a policy names this slot and its major version")
            _refuse_uninstalled_listing(policy, installations)
            _refuse_retired_listing(policy, installations)
        object.__setattr__(self, "selection", MappingProxyType(dict(sorted(self.selection.items()))))
        declaration_source(self.source, "source")
        sha256(self.source_digest, "source_digest")

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": SLOT_CONFIGURATION_RECORD_TYPE, "slot_id": self.slot_id,
                "slot_version": self.slot_version, "installed": [item.to_dict() for item in self.installed],
                "selection": {key: policy.to_dict() for key, policy in self.selection.items()},
                "source": self.source, "source_digest": self.source_digest}

    @classmethod
    def from_dict(cls, record) -> "EngineSlotConfiguration":
        record = read_record(record, SLOT_CONFIGURATION_RECORD_TYPE, SLOT_CONFIGURATION_FIELDS)
        if type(record["installed"]) is not list or type(record["selection"]) is not dict:
            raise EngineRecordError("invalid_field", "installed is a list and selection a mapping")
        return cls(record["slot_id"], record["slot_version"],
                   tuple(EngineInstallation.from_dict(item) for item in record["installed"]),
                   {key: EngineSelectionPolicy.from_dict(value) for key, value in record["selection"].items()},
                   record["source"], record["source_digest"])


def _refuse_uninstalled_listing(policy, installations):
    missing = [item for item in policy.initial + policy.fallbacks if item not in installations]
    if missing:
        raise EngineRecordError("engine_not_installed",
                                f"the policy names installations this slot does not install: {missing}")


def _refuse_retired_listing(policy, installations):
    """Deprecated: never an initial choice. Archived: never listed and never enabled.

    An installation does not name its engine version, so only a retirement of
    every version applies here; selection applies a retirement of one version
    against the descriptor it projects."""
    for retirement in policy.retired:
        def retired(ids):
            return [item for item in ids
                    if item in installations and retirement.covers(installations[item].engine_id)]
        enabled = retired(item.installation_id for item in installations.values() if item.enabled)
        archived = retirement.stage == ARCHIVED_STAGE
        if retired(policy.initial) or (archived and (retired(policy.fallbacks) or enabled)):
            raise EngineRecordError("engine_retired", f"{retirement.engine_id} is {retirement.stage}; "
                                    f"replacement: {retirement.replacement or 'none named'}")


@dataclass(frozen=True)
class ServiceHostEngines:
    """The optional top-level engines block of the service host file.

    A map from slot to its declared configuration. An older release refuses a
    host file that carries this block, which is the intended rollback rule."""

    slots: object

    def __post_init__(self):
        if type(self.slots) not in (dict, MappingProxyType) or not self.slots:
            raise EngineRecordError("invalid_field", "the engines block names at least one slot")
        for slot_id, configuration in self.slots.items():
            if not isinstance(configuration, EngineSlotConfiguration) or configuration.slot_id != slot_id:
                raise EngineRecordError("invalid_field", "each slot maps to its own slot configuration")
            if configuration.source != DECLARED_SOURCE:
                raise EngineRecordError("invalid_field", "the engines block is a declaration, never a projection")
            _refuse_unqualified_on_a_served_path(configuration)
        object.__setattr__(self, "slots", MappingProxyType(dict(sorted(self.slots.items()))))

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": SERVICE_HOST_ENGINES_RECORD_TYPE,
                "slots": {key: value.to_dict() for key, value in self.slots.items()}}

    @classmethod
    def from_dict(cls, record) -> "ServiceHostEngines":
        record = read_record(record, SERVICE_HOST_ENGINES_RECORD_TYPE, ("slots",))
        if type(record["slots"]) is not dict:
            raise EngineRecordError("invalid_field", "slots must be a mapping")
        return cls({key: EngineSlotConfiguration.from_dict(value) for key, value in record["slots"].items()})


def _refuse_unqualified_on_a_served_path(configuration):
    """allow_unqualified is for a declared trial only; the service host is a served path. The ranking
    engines that order a served slot are engines too, so their own allow_unqualified stays false."""
    trials = sorted(key for key, policy in configuration.selection.items()
                    if policy.allow_unqualified or policy.ranking.allow_unqualified)
    if trials:
        raise EngineRecordError("unqualified_on_a_served_path",
                                f"{configuration.slot_id} allows unqualified engines for {trials} on a served host")


@dataclass(frozen=True)
class BoundEngine:
    """What one host-start slot bound: its decision and the engine it chose."""

    decision_digest: str
    installation_id: str
    engine_ref: str

    def __post_init__(self):
        sha256(self.decision_digest, "decision digest")
        identifier(self.installation_id, "installation_id")
        exact_engine_ref(self.engine_ref, "engine_ref")

    def to_dict(self):
        return {"decision_digest": self.decision_digest, "installation_id": self.installation_id,
                "engine_ref": self.engine_ref}


@dataclass(frozen=True)
class FamilyPolicyInForce:
    """The intelligence family policy a host serves under, with the reason it applies."""

    record_type: str
    policy_digest: str
    reason: str

    def __post_init__(self):
        contract(self.record_type, "family policy record type")
        sha256(self.policy_digest, "family policy digest")
        text(self.reason, "family policy reason")

    def to_dict(self):
        return {"record_type": self.record_type, "policy_digest": self.policy_digest, "reason": self.reason}


BINDINGS_REPORT_FIELDS = ("configuration_digest", "bound", "unbound", "family_policy")


@dataclass(frozen=True)
class EngineBindingsReport:
    """What a host bound when it started, and why: one decision per host-start slot,
    the slots left unbound with their reasons, and the family policy in force."""

    configuration_digest: str
    bound: object
    unbound: object
    family_policy: FamilyPolicyInForce

    def __post_init__(self):
        sha256(self.configuration_digest, "configuration_digest")
        for name in ("bound", "unbound"):
            value = getattr(self, name)
            if type(value) not in (dict, MappingProxyType):
                raise EngineRecordError("invalid_field", name + " must map slots")
            for slot_id, item in value.items():
                identifier(slot_id, "slot_id")
                if name == "unbound":
                    identifier(item, "reason a slot is unbound")
                elif not isinstance(item, BoundEngine):
                    raise EngineRecordError("invalid_field", "a bound slot names a BoundEngine")
            object.__setattr__(self, name, MappingProxyType(dict(sorted(value.items()))))
        if set(self.bound) & set(self.unbound):
            raise EngineRecordError("invalid_field", "a slot is either bound or unbound, never both")
        if not isinstance(self.family_policy, FamilyPolicyInForce):
            raise EngineRecordError("invalid_field", "family_policy must be a FamilyPolicyInForce")

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": BINDINGS_REPORT_RECORD_TYPE, "configuration_digest": self.configuration_digest,
                "bound": {key: value.to_dict() for key, value in self.bound.items()},
                "unbound": dict(self.unbound), "family_policy": self.family_policy.to_dict()}

    @classmethod
    def from_dict(cls, record) -> "EngineBindingsReport":
        record = read_record(record, BINDINGS_REPORT_RECORD_TYPE, BINDINGS_REPORT_FIELDS)
        if type(record["bound"]) is not dict:
            raise EngineRecordError("invalid_field", "bound must be a mapping")
        bound = {}
        for slot_id, item in record["bound"].items():
            item = read_part(item, "bound engine", ("decision_digest", "installation_id", "engine_ref"))
            bound[slot_id] = BoundEngine(item["decision_digest"], item["installation_id"], item["engine_ref"])
        family = read_part(record["family_policy"], "family policy", ("record_type", "policy_digest", "reason"))
        return cls(record["configuration_digest"], bound, record["unbound"],
                   FamilyPolicyInForce(family["record_type"], family["policy_digest"], family["reason"]))


def self_test():
    """Run the engine record checks."""
    from .engine_records_checks import self_test as run_engine_record_checks
    return run_engine_record_checks()
