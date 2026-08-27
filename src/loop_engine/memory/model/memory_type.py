"""Memory model: types, identity, references, scope, and lifecycle.

These are the shared typed primitives for all four memory types. They
are data objects contained by or referenced from Loops, never Nodes
and never runtimes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

#: The four memory types. Working memory is runtime state; episodic,
#: semantic, and procedural are persistent record types.
MEMORY_TYPES = ("working", "episodic", "semantic", "procedural")

#: The three persistent record types.
PERSISTENT_MEMORY_TYPES = ("episodic", "semantic", "procedural")

#: Nine non-exclusive Functional Intelligence Domains. These answer why
#: intelligence is useful and are independent of memory type.
INTELLIGENCE_FUNCTIONS = (
    "ask", "horizon", "readiness", "deliberation", "implementation",
    "execution", "verification", "integration", "routing",
)

#: Perspectives: whose or what viewpoint the record represents.
PERSPECTIVES = (
    "user", "domain", "environment", "experience", "governance",
    "system", "repository", "architecture", "runtime", "storage",
    "security", "delivery", "assurance",
)

#: Trust levels for persistent records.
TRUST_LEVELS = (
    "unreviewed", "candidate", "reviewed", "verified", "distrusted",
)

#: Producer origins.
PRODUCER_ORIGINS = (
    "core_release", "practitioner_run", "user", "project", "plugin",
    "external_import", "administrator", "consolidation",
)


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryScope(str, Enum):
    RUN = "run"
    USER = "user"
    PROJECT = "project"
    WORKSPACE = "workspace"
    ORGANIZATION = "organization"
    GLOBAL = "global"


class MemoryLifecycle(str, Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    UNDER_REVIEW = "under_review"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"
    REVOKED = "revoked"
    ARCHIVED = "archived"
    TOMBSTONED = "tombstoned"


@dataclass(frozen=True)
class MemoryIdentity:
    """Stable identity for one persistent memory record."""

    record_id: str
    version: str
    content_digest: str
    memory_type: MemoryType

    def __post_init__(self) -> None:
        # Coerce str values first: ``value in EnumClass`` is legal only for
        # members on Python < 3.12 (it raises TypeError), and is legal for
        # str values on 3.12+, so a raw membership test is not
        # version-portable. isinstance + constructor coercion is.
        if not isinstance(self.memory_type, MemoryType):
            try:
                memory_type = MemoryType(self.memory_type)
            except (ValueError, KeyError):
                raise ValueError(
                    f"unknown memory type {self.memory_type!r}") from None
            object.__setattr__(self, "memory_type", memory_type)
        if not self.record_id or not self.version or not self.content_digest:
            raise ValueError("memory identity needs id, version, and digest")


@dataclass(frozen=True)
class MemoryRef:
    """Typed reference to one exact memory record version."""

    record_id: str
    version: str
    memory_type: MemoryType

    def to_dict(self) -> dict:
        return {"record_id": self.record_id, "version": self.version,
                "memory_type": self.memory_type.value}


@dataclass(frozen=True)
class MemoryProvenance:
    """Who or what produced a record and how."""

    producer_origin: str = "practitioner_run"
    producer_loop_id: str = ""
    producer_run_id: str = ""
    derivation_method: str = ""
    source_refs: tuple[MemoryRef, ...] = ()

    def __post_init__(self) -> None:
        if self.producer_origin not in PRODUCER_ORIGINS:
            raise ValueError(
                f"producer_origin must be one of {PRODUCER_ORIGINS}")


@dataclass(frozen=True)
class MemoryValidity:
    """Temporal validity: when the claim held vs when we learned it."""

    valid_from: str = ""
    valid_until: str = ""
    observed_at: str = ""
    recorded_at: str = ""

    def __post_init__(self) -> None:
        if self.valid_from and self.valid_until \
                and self.valid_from > self.valid_until:
            raise ValueError("valid_from must not exceed valid_until")


@dataclass(frozen=True)
class MemoryEvidenceRef:
    """One evidence reference supporting or opposing a record."""

    ref: str
    kind: str = "artifact"
    relationship: str = "supports"


def self_test() -> dict:
    """Prove the shared model validates and remains orthogonal."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    check("four_memory_types_are_defined",
          MEMORY_TYPES == ("working", "episodic", "semantic", "procedural"))
    check("persistent_types_exclude_working",
          PERSISTENT_MEMORY_TYPES
          == ("episodic", "semantic", "procedural"))
    check("nine_intelligence_functions_are_defined",
          len(INTELLIGENCE_FUNCTIONS) == 9
          and "verification" in INTELLIGENCE_FUNCTIONS)
    identity = MemoryIdentity("mem.ep.1", "1.0.0", "a" * 64,
                              MemoryType.EPISODIC)
    check("identity_validates",
          identity.memory_type is MemoryType.EPISODIC)
    try:
        MemoryIdentity("x", "1.0.0", "a" * 64, "bogus")
        check("unknown_memory_type_is_rejected", False)
    except ValueError:
        check("unknown_memory_type_is_rejected", True)
    validity = MemoryValidity(valid_from="2026-01-01",
                              valid_until="2026-02-01")
    check("validity_interval_is_typed", validity.valid_from
          < validity.valid_until)
    try:
        MemoryValidity(valid_from="2026-02-01", valid_until="2026-01-01")
        check("inverted_validity_interval_is_rejected", False)
    except ValueError:
        check("inverted_validity_interval_is_rejected", True)
    provenance = MemoryProvenance(producer_origin="consolidation",
                                  source_refs=(MemoryRef(
                                      "mem.ep.1", "1.0.0",
                                      MemoryType.EPISODIC),))
    check("provenance_links_source_refs",
          len(provenance.source_refs) == 1)
    try:
        MemoryProvenance(producer_origin="bogus")
        check("unknown_producer_origin_is_rejected", False)
    except ValueError:
        check("unknown_producer_origin_is_rejected", True)
    return {"tests": results}
