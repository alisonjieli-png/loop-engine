"""The fixed edge of ontology change planning: typed, versioned records and explicit failures.

```text
Edge contract (ontology_change_planning, edge version 1)
├── ontology_change_request/v1     the base ontology (Turtle or N-Triples), its digest, the change
│                                  (added and removed triples), the rule profile, bounds, locks
├── ontology_change_plan/v1        bound to the base digest and the proposed digest: asserted change,
│                                  new and lost entailed triples (counts and bounded lists), affected
│                                  terms, the locks checked and touched, the verdict word, optional
│                                  traces, and plan_digest over every other field
├── ontology_change_apply_request/v1   the plan and an approval naming that plan's digest
├── ontology_change_apply_result/v1    the digests before and after, and the rollback record
├── ontology_change_rollback/v1        what a rollback replaces and what it restores
└── ontology_change_failure/v1         one closed failure code with its stage and detail
```

Engines see only ``PlanningInput`` and answer only ``EngineOutcome``: the
envelope reads the request, checks the digest, selects, dispatches, checks every
listed derivation with the independent trace checker and writes the plan. An
engine never applies a change; apply and rollback belong to the store
(``store.py``), never to an engine. Nothing here imports an engine.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Protocol

from .rdf_terms import RdfSyntaxError, is_blank, parse_term

SLOT_ID = "ontology_change_planning"
SLOT_VERSION = "1.0.0"
ENGINE_PROTOCOL_VERSION = "ontology_change_engine/v1"
REQUEST_RECORD_TYPE = "ontology_change_request/v1"
PLAN_RECORD_TYPE = "ontology_change_plan/v1"
FAILURE_RECORD_TYPE = "ontology_change_failure/v1"
APPLY_REQUEST_RECORD_TYPE = "ontology_change_apply_request/v1"
APPLY_RESULT_RECORD_TYPE = "ontology_change_apply_result/v1"
ROLLBACK_RECORD_TYPE = "ontology_change_rollback/v1"
ROLLBACK_REQUEST_RECORD_TYPE = "ontology_change_rollback_request/v1"
ROLLBACK_RESULT_RECORD_TYPE = "ontology_change_rollback_result/v1"
DECLARATION_RECORD_TYPE = "ontology_change_engine_declaration/v1"
CONFORMANCE_REPORT_RECORD_TYPE = "ontology_change_conformance_report/v1"

PROFILES = ("rdfs", "owl-rl")
ONTOLOGY_FORMATS = ("turtle", "ntriples")
#: The rule table of each profile, spelled as the W3C RDFS and OWL 2 RL tables spell them, with premises in
#: the order the trace checker reads. The six RDFS names are OWL 2 RL rules under other names: rdfs2 is
#: prp-dom, rdfs3 prp-rng, rdfs5 scm-spo, rdfs7 prp-spo1, rdfs9 cax-sco and rdfs11 scm-sco.
RDFS_RULES = ("rdfs2", "rdfs3", "rdfs5", "rdfs7", "rdfs9", "rdfs11")
OWL_RL_RULES = RDFS_RULES + ("prp-trp", "prp-symp", "prp-inv1", "prp-inv2", "eq-sym", "scm-eqc1",
                             "scm-eqp1", "scm-dom1", "scm-dom2", "scm-rng1", "scm-rng2")
RULE_TABLES = MappingProxyType({"rdfs": RDFS_RULES, "owl-rl": OWL_RL_RULES})

VERDICTS = ("conservative_under_rule_table", "not_conservative_under_rule_table")
CONSERVATIVE, NOT_CONSERVATIVE = VERDICTS
STAGES = ("request", "selection", "engine", "result", "apply", "rollback")
FAILURE_CODES = (
    "request_invalid", "unsupported_syntax", "base_digest_mismatch", "change_invalid", "profile_unsupported",
    "limit_exceeded", "no_eligible_engine", "engine_unavailable", "engine_failed", "result_invalid",
    "plan_invalid", "approval_required", "approval_mismatch", "stale_base", "locked_term", "store_corrupt",
    "rollback_invalid", "stale_rollback", "rollback_mismatch")
#: What an engine may report. The first three let the envelope try the next declared engine before
#: anything else happens; a closure over the bound stops the whole request, because every engine computes
#: the same closure.
ENGINE_FAILURE_KINDS = ("engine_unavailable", "engine_reported_failure", "capability_requirement_unsatisfied",
                        "limit_exceeded")
FALLBACK_FAILURE_KINDS = ENGINE_FAILURE_KINDS[:3]

MAXIMUM_ONTOLOGY_CHARACTERS = 8 * 1024 * 1024
MAXIMUM_CHANGE_TRIPLES = 10_000
MAXIMUM_LOCKED_TERMS = 10_000
DEFAULT_MAXIMUM_LISTED = 200
LISTED_CEILING = 5_000
DEFAULT_MAXIMUM_CLOSURE = 1_000_000
CLOSURE_CEILING = 5_000_000
MAXIMUM_APPROVAL_CHARACTERS = 200
_SHA256 = re.compile(r"[0-9a-f]{64}")

Triple = tuple


class OntologyChangeRefused(Exception):
    """A typed refusal: one closed code, the stage that refused, and a bounded detail."""

    def __init__(self, code: str, detail: str = "", stage: str = "request"):
        if code not in FAILURE_CODES or stage not in STAGES:
            raise ValueError(f"unknown failure code or stage: {code} {stage}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail, self.stage = code, str(detail)[:400], stage

    def to_record(self) -> dict:
        return {"record_type": FAILURE_RECORD_TYPE, "code": self.code, "stage": self.stage,
                "detail": self.detail}


class EngineFailure(Exception):
    """What an engine raises; the envelope turns it into a fallback or a failure record."""

    def __init__(self, kind: str, detail: str = ""):
        if kind not in ENGINE_FAILURE_KINDS:
            raise ValueError(f"unknown engine failure kind: {kind}")
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind, self.detail = kind, str(detail)[:400]


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_digest(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def is_sha256(value) -> bool:
    return type(value) is str and bool(_SHA256.fullmatch(value))


def _refuse(code: str, detail: str, stage: str = "request"):
    raise OntologyChangeRefused(code, detail, stage)


def _keys(value, fields: tuple, name: str, code: str = "request_invalid", stage: str = "request") -> dict:
    if not isinstance(value, dict):
        _refuse(code, f"{name} is not a mapping", stage)
    unknown, missing = sorted(set(value) - set(fields)), [key for key in fields if key not in value]
    if unknown or missing:
        _refuse(code, f"{name}: unknown {unknown} missing {missing}", stage)
    return value


def read_triple(value, name: str = "triple", *, allow_blank: bool = False) -> Triple:
    """A triple given as three N-Triples terms, made canonical; a blank node only where allowed."""
    if not isinstance(value, (list, tuple)) or len(value) != 3 or any(type(term) is not str for term in value):
        _refuse("change_invalid", f"{name} is three N-Triples terms")
    try:
        triple = tuple(parse_term(term, position) for term, position in
                       zip(value, ("subject", "predicate", "object")))
    except RdfSyntaxError as error:
        _refuse("change_invalid", f"{name}: {error}")
    if not allow_blank and any(is_blank(term) for term in triple):
        _refuse("change_invalid", f"{name} names a blank node; a change names IRIs and literals only")
    return triple


def triples_list(triples) -> list:
    return [list(triple) for triple in sorted(triples)]


@dataclass(frozen=True)
class PlanRequest:
    """``ontology_change_request/v1`` after strict reading."""

    ontology_format: str
    ontology_text: str
    base_digest: str
    added: tuple
    removed: tuple
    profile: str
    maximum_listed: int
    maximum_closure: int
    include_traces: bool
    locked_terms: tuple

    @classmethod
    def from_dict(cls, value) -> "PlanRequest":
        record = _keys(value, ("record_type", "ontology", "base_digest", "change", "profile", "limits",
                               "include_traces", "locked_terms"), "request")
        if record["record_type"] != REQUEST_RECORD_TYPE:
            _refuse("request_invalid", f"unsupported request version {record['record_type']!r}")
        ontology = _keys(record["ontology"], ("format", "text"), "ontology")
        if ontology["format"] not in ONTOLOGY_FORMATS:
            _refuse("unsupported_syntax", f"ontology format is one of {ONTOLOGY_FORMATS}")
        if type(ontology["text"]) is not str or len(ontology["text"]) > MAXIMUM_ONTOLOGY_CHARACTERS:
            _refuse("request_invalid", f"ontology text is at most {MAXIMUM_ONTOLOGY_CHARACTERS} characters")
        if not is_sha256(record["base_digest"]):
            _refuse("request_invalid", "base_digest is a lowercase SHA-256")
        if record["profile"] not in PROFILES:
            _refuse("profile_unsupported", f"profile is one of {PROFILES}")
        change = _keys(record["change"], ("added", "removed"), "change", code="change_invalid")
        added, removed = (cls._triples(change[name], name) for name in ("added", "removed"))
        if not added and not removed:
            _refuse("change_invalid", "a change adds or removes at least one triple")
        if set(added) & set(removed):
            _refuse("change_invalid", "a triple is both added and removed")
        limits = _keys(record["limits"], ("max_listed", "max_closure_triples"), "limits")
        listed, closure = limits["max_listed"], limits["max_closure_triples"]
        if type(listed) is not int or not 0 <= listed <= LISTED_CEILING:
            _refuse("request_invalid", f"max_listed is an integer from 0 to {LISTED_CEILING}")
        if type(closure) is not int or not 1 <= closure <= CLOSURE_CEILING:
            _refuse("request_invalid", f"max_closure_triples is an integer from 1 to {CLOSURE_CEILING}")
        if type(record["include_traces"]) is not bool:
            _refuse("request_invalid", "include_traces is a Boolean")
        locks = record["locked_terms"]
        if not isinstance(locks, list) or len(locks) > MAXIMUM_LOCKED_TERMS:
            _refuse("request_invalid", "locked_terms is a bounded list of IRIs")
        locked = tuple(sorted({read_locked_term(term) for term in locks}))
        return cls(ontology["format"], ontology["text"], record["base_digest"], added, removed,
                   record["profile"], listed, closure, record["include_traces"], locked)

    @staticmethod
    def _triples(values, name) -> tuple:
        if not isinstance(values, list) or len(values) > MAXIMUM_CHANGE_TRIPLES:
            _refuse("change_invalid", f"{name} is a list of at most {MAXIMUM_CHANGE_TRIPLES} triples")
        triples = [read_triple(item, f"{name}[{index}]") for index, item in enumerate(values)]
        if len(set(triples)) != len(triples):
            _refuse("change_invalid", f"{name} repeats a triple")
        return tuple(sorted(triples))


def read_locked_term(term) -> str:
    if type(term) is not str:
        _refuse("request_invalid", "a locked term is an IRI in N-Triples spelling")
    try:
        spelled = parse_term(term, "predicate")
    except RdfSyntaxError as error:
        _refuse("request_invalid", f"locked term: {error}")
    return spelled


def request_record(ontology_text: str, base_digest: str, *, added=(), removed=(), profile: str = "owl-rl",
                   ontology_format: str = "turtle", include_traces: bool = True,
                   max_listed: int = DEFAULT_MAXIMUM_LISTED, locked_terms=()) -> dict:
    """Write an ``ontology_change_request/v1``; reading it back applies every rule."""
    return {"record_type": REQUEST_RECORD_TYPE, "ontology": {"format": ontology_format, "text": ontology_text},
            "base_digest": base_digest,
            "change": {"added": [list(item) for item in added], "removed": [list(item) for item in removed]},
            "profile": profile, "limits": {"max_listed": max_listed, "max_closure_triples": DEFAULT_MAXIMUM_CLOSURE},
            "include_traces": include_traces, "locked_terms": list(locked_terms)}


@dataclass(frozen=True)
class PlanningInput:
    """What an engine receives: both graphs already read and checked, and the bounds."""

    base: frozenset
    proposed: frozenset
    profile: str
    maximum_closure: int

    @property
    def has_blank_nodes(self) -> bool:
        return any(is_blank(term) for graph in (self.base, self.proposed) for triple in graph for term in triple)


@dataclass(frozen=True)
class EngineOutcome:
    """What an engine answers: both closures, the first derivation of every derived triple, the table used.

    A derivation is (rule, premises) with the premises in the rule's order. The envelope checks the
    closures against the asserted graphs and every listed derivation with the independent checker."""

    engine_ref: str
    rule_table: tuple
    base_closure: frozenset
    proposed_closure: frozenset
    base_derivations: Mapping = field(default_factory=dict)
    proposed_derivations: Mapping = field(default_factory=dict)
    notes: Mapping = field(default_factory=dict)


@dataclass(frozen=True)
class EngineDeclaration:
    """``ontology_change_engine_declaration/v1``: what one engine says of itself, in its factory table."""

    engine_id: str
    engine_version: str
    engine_kind: str
    implementation_ref: str
    profiles: tuple
    blank_nodes: bool
    effects: tuple
    isolation: str
    licence: str
    source_upstream: str
    source_revision: str
    pinned_artifact: "Mapping | None" = None

    def to_dict(self) -> dict:
        return {"record_type": DECLARATION_RECORD_TYPE, "engine_id": self.engine_id,
                "engine_version": self.engine_version, "engine_kind": self.engine_kind,
                "implementation_ref": self.implementation_ref, "profiles": list(self.profiles),
                "blank_nodes": self.blank_nodes, "effects": list(self.effects), "isolation": self.isolation,
                "licence": self.licence, "source_upstream": self.source_upstream,
                "source_revision": self.source_revision,
                "pinned_artifact": None if self.pinned_artifact is None else dict(self.pinned_artifact)}

    @property
    def engine_ref(self) -> str:
        return f"{self.engine_id}@{self.engine_version}"


class OntologyChangeEngine(Protocol):
    """``ontology_change_engine/v1``: the one call an engine of this slot answers."""

    declaration: EngineDeclaration

    def availability(self) -> tuple:
        """(available, reason): whether this engine can run on this machine now, without running it."""

    def plan(self, planning_input: PlanningInput) -> EngineOutcome:
        """Both closures and their derivations, or EngineFailure."""


PLAN_FIELDS = ("record_type", "base_digest", "proposed_digest", "profile", "rule_table", "engine", "change",
               "asserted", "entailed", "affected_terms", "locks", "verdict", "closure", "traces", "plan_digest")


def plan_digest(plan: dict) -> str:
    """The digest of every plan field except plan_digest itself."""
    return record_digest({key: value for key, value in plan.items() if key != "plan_digest"})


def read_plan(plan, *, stage: str = "apply") -> dict:
    """A plan whose fields are exactly the plan fields and whose digest still matches its body."""
    _keys(plan, PLAN_FIELDS, "plan", code="plan_invalid", stage=stage)
    if plan["record_type"] != PLAN_RECORD_TYPE:
        _refuse("plan_invalid", f"unsupported plan version {plan['record_type']!r}", stage)
    for name in ("base_digest", "proposed_digest", "plan_digest"):
        if not is_sha256(plan[name]):
            _refuse("plan_invalid", f"{name} is a lowercase SHA-256", stage)
    if plan_digest(plan) != plan["plan_digest"]:
        _refuse("plan_invalid", "plan_digest does not match the plan's fields; the plan was changed", stage)
    change = _keys(plan["change"], ("added", "removed"), "plan change", code="plan_invalid", stage=stage)
    for name in ("added", "removed"):
        for item in change[name]:
            read_triple(item, f"plan {name}")
    locks = _keys(plan["locks"], ("checked", "touched"), "plan locks", code="plan_invalid", stage=stage)
    if not isinstance(locks["checked"], list) or not isinstance(locks["touched"], list) or any(
            not isinstance(item, dict) or set(item) != {"term", "how"} for item in locks["touched"]):
        _refuse("plan_invalid", "locks lists the terms checked and each term touched with how", stage)
    return plan


def read_approval(value, plan: dict, *, stage: str = "apply") -> str:
    """An approval is a bounded reference that names the exact plan digest it approves."""
    if value is None or value == "" or value == {}:
        _refuse("approval_required", "an apply or rollback names an approval reference", stage)
    approval = _keys(value, ("approval_ref", "plan_digest"), "approval", code="approval_required", stage=stage)
    reference = approval["approval_ref"]
    if (type(reference) is not str or not reference.strip() or len(reference) > MAXIMUM_APPROVAL_CHARACTERS
            or not reference.isprintable()):
        _refuse("approval_required", "approval_ref is printable text of at most 200 characters", stage)
    if approval["plan_digest"] != plan["plan_digest"]:
        _refuse("approval_mismatch", "the approval names another plan", stage)
    return reference
