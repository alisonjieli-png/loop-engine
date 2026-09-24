"""Trust tiers of the library, the community admission criteria, and the library setting.

The owner, September 24, 2026: "we need to have a continuously updating
database of millions of skills, tooks, code, functions, plugins, contracts,
rules, agents, agent support files, agent support code, etc that coding
harnesses can detect and freely use". Millions of packages cannot all pass the
independent review panel, so an approved item passes one of two admission
paths, and every answer about it says which:

```text
Trust tier of an approved item
├── baltor_verified   the independent review panel, unchanged: three approvals
│                     from three model families other than the producer's,
│                     bound to the exact bytes
└── community         the written criteria below, applied automatically by a
                      process that is not the producer, bound to the exact bytes
    ├── every file carries an allowlisted licence with the decision that permits it
    ├── every file names a pinned source: origin, immutable revision, path, digest
    ├── the licence text and the attribution travel inside the package
    ├── at least two distinct static scanners passed and none blocked it
    └── Baltor never ran it, and says so
```

The community path never reads a retrieval count, a score or a model's
confidence, and it never promotes an item to the verified tier. A community
item becomes verified only when the review panel approves its exact bytes.

A customer chooses which community items their account receives. The
default, `without_runnable_files`, offers community instructions, skills and
references, and leaves out every community package holding a file a harness
may run (a script, a hook or an executable tool, which the release rules
require to declare the process effect). `included` adds those; `excluded`
serves verified items only. Verified items rank before community items in
every search and listing.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from ..provisioning_server import (COMMUNITY_EXCLUDED, COMMUNITY_INCLUDED, COMMUNITY_ITEM_CHOICES,
                                   COMMUNITY_TIER, COMMUNITY_WITHOUT_RUNNABLE, TIER_ORDER, TRUST_TIERS,
                                   VERIFIED_TIER)
from .records import ServiceRuntimeError

__all__ = ["COMMUNITY_EXCLUDED", "COMMUNITY_INCLUDED", "COMMUNITY_ITEM_CHOICES", "COMMUNITY_TIER",
           "COMMUNITY_WITHOUT_RUNNABLE", "TIER_ORDER", "TRUST_TIERS", "VERIFIED_TIER"]

CRITERIA_RECORD_TYPE = "community_admission_criteria/v1"
ADMISSION_RECORD_TYPE = "community_admission/v1"
LIBRARY_SETTINGS_RECORD_TYPE = "account_library_settings/v1"
#: The exact words every surface shows for a tier. A page, a download and a
#: search result use these and nothing shorter.
TIER_LABELS = {VERIFIED_TIER: "Baltor verified", COMMUNITY_TIER: "Community"}
TIER_MEANINGS = {
    VERIFIED_TIER: ("Approved by Baltor's independent review panel: three approvals from three model families "
                    "other than the producer's, bound to these exact bytes."),
    COMMUNITY_TIER: ("Admitted by written automated criteria that a process other than the producer applied: an "
                     "allowlisted licence for every file, a pinned source, and at least two static scanners "
                     "passed. No person at Baltor reviewed it and Baltor never ran it.")}
#: The good default: community text, never community code a harness may run.
DEFAULT_COMMUNITY_ITEMS = COMMUNITY_WITHOUT_RUNNABLE
COMMUNITY_ITEM_MEANINGS = {
    COMMUNITY_EXCLUDED: "Verified items only.",
    COMMUNITY_WITHOUT_RUNNABLE: ("Verified items, and community items that hold no file a development tool may "
                                 "run. This is the default."),
    COMMUNITY_INCLUDED: "Verified items and every community item, including scripts, hooks and tools."}
#: The licence decisions of `outside_licence_evidence/v1` that permit serving a file.
#: `verbatim_permitted` copies an accepted licence's bytes; `link_only` is a
#: registry entry whose connection files Baltor wrote from facts.
SERVABLE_LICENCE_DECISIONS = ("verbatim_permitted", "link_only")
#: Licences whose terms require the licence text or an attribution to travel with a copy.
LICENCES_WITHOUT_NOTICE = ("CC0-1.0",)
SCAN_RESULTS = ("passed", "blocked", "incomplete")
MAXIMUM_ADMISSION_FILES = 64
MAXIMUM_TEXT = 400
_DIGEST = re.compile(r"[0-9a-f]{64}")
_GIT_OBJECT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_REGISTRY_REVISION = re.compile(r"version:[^;\s]{1,64};published:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z)?")
_PROCESS = re.compile(r"[a-z][a-z0-9_]{1,63}")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def _text(value, limit=MAXIMUM_TEXT):
    return isinstance(value, str) and value == value.strip() and 0 < len(value) <= limit and value.isprintable()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CommunityAdmissionCriteria:
    """The written criteria of the community tier, identified by the digest of their canonical form."""

    licence_allowlist: tuple = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0", "CC-BY-4.0")
    servable_licence_decisions: tuple = SERVABLE_LICENCE_DECISIONS
    minimum_passing_scanners: int = 2
    execution: str = "none"
    record_type: str = CRITERIA_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != CRITERIA_RECORD_TYPE:
            _refuse("community_criteria_unsupported", f"this release reads {CRITERIA_RECORD_TYPE} only")
        if (not self.licence_allowlist or len(set(self.licence_allowlist)) != len(self.licence_allowlist)
                or any(not _text(name, 64) or " " in name for name in self.licence_allowlist)):
            _refuse("community_criteria_invalid", "the licence allowlist names distinct SPDX identifiers")
        if not set(self.servable_licence_decisions) <= set(SERVABLE_LICENCE_DECISIONS):
            _refuse("community_criteria_invalid", "only decisions that permit serving a file are listed")
        if type(self.minimum_passing_scanners) is not int or self.minimum_passing_scanners < 2:
            # The owner's criterion is several static scanners; one is never enough.
            _refuse("community_criteria_invalid", "at least two static scanners must pass")
        if self.execution != "none":
            _refuse("community_criteria_invalid", "the community tier never runs what it admits")

    def to_dict(self):
        return {"record_type": self.record_type, "licence_allowlist": list(self.licence_allowlist),
                "servable_licence_decisions": list(self.servable_licence_decisions),
                "minimum_passing_scanners": self.minimum_passing_scanners, "execution": self.execution}

    @property
    def digest(self):
        return canonical_digest(self.to_dict())


#: The criteria this release applies. Changing them is a new digest, and an
#: admission made under other criteria is refused until it is made again.
COMMUNITY_CRITERIA = CommunityAdmissionCriteria()


def _source(value):
    fields = {"origin", "repository", "immutable_revision", "path", "source_digest", "fetched_at"}
    if not isinstance(value, dict) or set(value) != fields:
        _refuse("community_admission_invalid", "a file source names origin, repository, revision, path, digest and time")
    for name in ("origin", "repository", "path"):
        if not _text(value[name]):
            _refuse("community_admission_invalid", f"a file source names its {name}")
    return value


def _file(value):
    fields = {"path", "digest", "spdx", "licence_decision", "source"}
    if not isinstance(value, dict) or set(value) != fields:
        _refuse("community_admission_invalid", "an admitted file names path, digest, licence, decision and source")
    if not _text(value["path"], 200) or not isinstance(value["digest"], str) or not _DIGEST.fullmatch(value["digest"]):
        _refuse("community_admission_invalid", "an admitted file names its placement path and exact digest")
    if not _text(value["spdx"], 64) or not _text(value["licence_decision"], 64):
        _refuse("community_admission_invalid", "an admitted file names its licence and the decision that permits it")
    return {**value, "source": _source(value["source"])}


def _scanner(value):
    if not isinstance(value, dict) or set(value) != {"engine", "version", "result"}:
        _refuse("community_admission_invalid", "a scanner result names its engine, version and result")
    if not _text(value["engine"], 80) or not _text(value["version"], 80) or value["result"] not in SCAN_RESULTS:
        _refuse("community_admission_invalid", f"a scanner result is one of {SCAN_RESULTS}")
    return value


@dataclass(frozen=True)
class CommunityAdmission:
    """One automated admission of one exact package version to the community tier."""

    criteria_digest: str
    package_digest: str
    producer: str
    admitted_by: str
    admitted_at: str
    files: tuple
    licence_file: str
    attribution: str
    scanners: tuple
    execution: str = "none"
    record_type: str = ADMISSION_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != ADMISSION_RECORD_TYPE:
            _refuse("community_admission_unsupported", f"this release reads {ADMISSION_RECORD_TYPE} only")
        for name in ("criteria_digest", "package_digest"):
            if not isinstance(getattr(self, name), str) or not _DIGEST.fullmatch(getattr(self, name)):
                _refuse("community_admission_invalid", f"the admission names its exact {name}")
        for name in ("producer", "admitted_by"):
            if not _text(getattr(self, name), 160):
                _refuse("community_admission_invalid", f"the admission names its {name}")
        if not isinstance(self.admitted_at, str) or not _DATE.fullmatch(self.admitted_at):
            _refuse("community_admission_invalid", "the admission names when it was made")
        files = tuple(self.files) if isinstance(self.files, (list, tuple)) else None
        if not files or len(files) > MAXIMUM_ADMISSION_FILES:
            _refuse("community_admission_invalid", "an admission lists every file of its package")
        object.__setattr__(self, "files", tuple(_file(entry) for entry in files))
        scanners = tuple(self.scanners) if isinstance(self.scanners, (list, tuple)) else None
        if scanners is None or len(scanners) > 16:
            _refuse("community_admission_invalid", "an admission lists its scanner results")
        object.__setattr__(self, "scanners", tuple(_scanner(entry) for entry in scanners))
        if not isinstance(self.licence_file, str) or len(self.licence_file) > 200:
            _refuse("community_admission_invalid", "the licence file is a placement path or empty")
        if not isinstance(self.attribution, str) or len(self.attribution) > 2000:
            _refuse("community_admission_invalid", "the attribution is bounded text")
        if not isinstance(self.execution, str):
            _refuse("community_admission_invalid", "the admission states whether Baltor ran the package")

    def to_dict(self):
        return {"record_type": self.record_type, "criteria_digest": self.criteria_digest,
                "package_digest": self.package_digest, "producer": self.producer, "admitted_by": self.admitted_by,
                "admitted_at": self.admitted_at, "files": [dict(entry) for entry in self.files],
                "licence_file": self.licence_file, "attribution": self.attribution,
                "scanners": [dict(entry) for entry in self.scanners], "execution": self.execution}

    @classmethod
    def from_dict(cls, value):
        fields = {"record_type", "criteria_digest", "package_digest", "producer", "admitted_by", "admitted_at",
                  "files", "licence_file", "attribution", "scanners", "execution"}
        if not isinstance(value, dict) or set(value) != fields:
            _refuse("community_admission_invalid", f"a {ADMISSION_RECORD_TYPE} record has exactly its own fields")
        return cls(**value)

    @property
    def digest(self):
        return canonical_digest(self.to_dict())

    def public_summary(self):
        """What a customer reads about an admission: licences, the licence file, attribution and sources."""
        return {"licences": sorted({entry["spdx"] for entry in self.files}), "licence_file": self.licence_file or None,
                "attribution": self.attribution or None,
                "sources": [{"path": entry["path"], "origin": entry["source"]["origin"],
                             "repository": entry["source"]["repository"],
                             "immutable_revision": entry["source"]["immutable_revision"],
                             "source_path": entry["source"]["path"]} for entry in self.files],
                "scanners_passed": sorted({entry["engine"] for entry in self.scanners if entry["result"] == "passed"}),
                "criteria_digest": self.criteria_digest, "executed_by_baltor": False}


def _process_name(identity):
    """The process part of `process:run` style identities, compared to decide independence."""
    name = identity.split(":", 1)[0].strip().lower()
    return name if _PROCESS.fullmatch(name) else ""


def community_admission_refusal(admission, item, package, criteria=None):
    """Empty text when the written criteria admit exactly this package, otherwise the refusal code.

    `item` is the served harness item reference and `package` its
    `CataloguePackage`. The criteria are this release's unless others are
    named. Every rule reads a typed field. None reads a retrieval count, a
    score or a model's confidence.
    """
    criteria = criteria if criteria is not None else COMMUNITY_CRITERIA
    if not isinstance(admission, CommunityAdmission):
        return "community_admission_required"
    if admission.criteria_digest != criteria.digest:
        return "community_criteria_mismatch"
    if admission.package_digest != package.served_digest:
        return "admission_not_bound_to_bytes"
    producer, admitter = _process_name(admission.producer), _process_name(admission.admitted_by)
    if not producer or not admitter or producer == admitter:
        return "admission_not_independent"
    if admission.execution != criteria.execution:
        return "community_admission_path_invalid"
    served = {entry.path: entry.digest for entry in package.files}
    admitted = {entry["path"]: entry["digest"] for entry in admission.files}
    if served != admitted or len(admitted) != len(admission.files):
        return "admission_files_mismatch"
    for entry in admission.files:
        if entry["spdx"] not in criteria.licence_allowlist:
            return "community_licence_not_allowed"
        if entry["licence_decision"] not in criteria.servable_licence_decisions:
            return "community_licence_decision_invalid"
        source = entry["source"]
        revision = source["immutable_revision"]
        if (not isinstance(revision, str)
                or not (_GIT_OBJECT.fullmatch(revision) or _REGISTRY_REVISION.fullmatch(revision))
                or not isinstance(source["source_digest"], str) or not _DIGEST.fullmatch(source["source_digest"])
                or not isinstance(source["fetched_at"], str) or not _DATE.fullmatch(source["fetched_at"])):
            return "community_provenance_unpinned"
    if item.license_name not in {entry["spdx"] for entry in admission.files}:
        return "community_licence_not_declared"
    needs_notice = any(entry["licence_decision"] == "verbatim_permitted" and entry["spdx"] not in LICENCES_WITHOUT_NOTICE
                       for entry in admission.files)
    if needs_notice and (admission.licence_file not in served or not _text(admission.attribution, 2000)):
        return "community_licence_text_missing"
    passed = {entry["engine"] for entry in admission.scanners if entry["result"] == "passed"}
    if any(entry["result"] == "blocked" for entry in admission.scanners):
        return "community_scan_blocked"
    if len(passed) < criteria.minimum_passing_scanners:
        return "community_scan_insufficient"
    return ""


@dataclass(frozen=True)
class LibrarySettings:
    """What one account chooses to receive from the library; it can only narrow what the plan allows."""

    community_items: str = DEFAULT_COMMUNITY_ITEMS
    record_type: str = LIBRARY_SETTINGS_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != LIBRARY_SETTINGS_RECORD_TYPE:
            _refuse("library_settings_unsupported", f"this release reads {LIBRARY_SETTINGS_RECORD_TYPE} only")
        if self.community_items not in COMMUNITY_ITEM_CHOICES:
            _refuse("library_settings_invalid", f"community items are one of {COMMUNITY_ITEM_CHOICES}")

    def to_dict(self):
        return {"record_type": self.record_type, "community_items": self.community_items}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"record_type", "community_items"}:
            _refuse("library_settings_invalid", "library settings name their record version and community items only")
        return cls(value["community_items"], value["record_type"])


DEFAULT_LIBRARY_SETTINGS = LibrarySettings()


def narrowed(settings, requested_tiers):
    """The community choice for one request: the account's setting, narrowed by the tiers the request names.

    A request can ask for fewer tiers than the account receives, never more.
    `requested_tiers` of None means the request did not narrow.
    """
    if requested_tiers is None:
        return settings.community_items
    tiers = tuple(requested_tiers)
    if not tiers or len(set(tiers)) != len(tiers) or any(tier not in TRUST_TIERS for tier in tiers):
        _refuse("trust_tiers_invalid", f"trust tiers are distinct values of {TRUST_TIERS}")
    return settings.community_items if COMMUNITY_TIER in tiers else COMMUNITY_EXCLUDED


def tier_legend():
    """The published meaning of each tier and each library choice, for capabilities and results."""
    return {"record_type": "catalogue_trust_tiers/v1",
            "tiers": [{"tier": tier, "label": TIER_LABELS[tier], "meaning": TIER_MEANINGS[tier],
                       "rank": TIER_ORDER[tier]} for tier in TRUST_TIERS],
            "community_items": {"default": DEFAULT_COMMUNITY_ITEMS,
                                "choices": [{"value": choice, "meaning": COMMUNITY_ITEM_MEANINGS[choice]}
                                            for choice in COMMUNITY_ITEM_CHOICES]},
            "community_criteria": {**COMMUNITY_CRITERIA.to_dict(), "digest": COMMUNITY_CRITERIA.digest}}
