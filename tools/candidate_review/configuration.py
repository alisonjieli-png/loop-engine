"""The declared configuration of the review panel, read strictly before any review.

Four resources are read here: the panel record (policy, family vocabulary,
pre-check engine settings, reviewer installations), the written criteria quoted
from the catalogue's review sheet, the producer declaration and the reviewer
instructions. Nothing in this module calls a model, reads a credential or
touches the network.

The approval floor is the owner's rule of 22 September 2026: at least three
approving reviewers from at least three model families, none of them the family
that produced the item, and any rejection keeps the item a candidate. A policy
that weakens any part of that rule is refused, not clamped.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .records import (
    CRITERIA_RECORD, INSTALLATION_RECORD, PANEL_RECORD, POLICY_RECORD, PRODUCER_RECORD,
    CandidateReviewError, boolean, canonical_whitespace, digest, identifier, positive_integer,
    positive_number, read_part, read_record, refuse, sha256_hex, text_field,
)

#: The owner's floor for approval: approvals and distinct families. A policy may ask more, never less.
QUORUM_FLOOR = 3
#: The six pre-check kinds. Every one of them must run for every item.
PRECHECK_KINDS = ("licence", "format", "safety", "effects", "secrets", "duplicates")
#: The engines each kind may name, in the only vocabulary a policy can use. The factory table in
#: ``engines`` builds exactly these; a check keeps the two lists equal.
PRECHECK_ENGINES = MappingProxyType({
    "licence": ("builtin_licence_rules",),
    "format": ("builtin_format_rules", "agent_skills_reference"),
    "safety": ("builtin_static_rules", "skillspector_static"),
    "effects": ("builtin_effect_rules",),
    "secrets": ("builtin_secret_patterns",),
    "duplicates": ("exact_shingle_jaccard", "datasketch_minhash_lsh"),
})
#: The licences that allow verbatim copy with attribution (the owner's September 22 list, as
#: SPDX identifiers). A policy may accept fewer, never another identifier.
PERMISSIVE_LICENCES = frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0",
                                 "CC-BY-4.0"})
#: The emphasis an installation adds to the shared instructions. Each has a section in the resource.
LENSES = ("correctness_and_usefulness", "provenance_licence_and_safety", "adversarial")
#: The kinds of reviewer engine. ``fixture`` exists for offline checks and never decides a real record.
ENGINE_KINDS = ("model_gateway", "command_line", "fixture")
FIXTURE_ENGINE_KIND = "fixture"
#: The only criteria match mode this release reads: quotes and sheet compared with whitespace collapsed.
MATCH_MODE = "whitespace_canonical"
CRITERION_IDENTIFIER_LIMIT = 64
MAXIMUM_TEMPERATURE = 2.0


@dataclass(frozen=True)
class RateLimitPolicy:
    """How long the panel may wait when a provider asks it to slow down."""

    initial_seconds: float
    maximum_seconds: float
    maximum_total_seconds: float
    maximum_retries_per_call: int

    @classmethod
    def from_dict(cls, value) -> "RateLimitPolicy":
        part = read_part(value, "rate_limit", ("initial_seconds", "maximum_seconds", "maximum_total_seconds",
                                               "maximum_retries_per_call"))
        retries = part["maximum_retries_per_call"]
        if type(retries) is not int or retries < 0:
            refuse("invalid_policy", "maximum_retries_per_call must be a whole number of zero or more")
        policy = cls(positive_number(part["initial_seconds"], "initial_seconds"),
                     positive_number(part["maximum_seconds"], "maximum_seconds"),
                     positive_number(part["maximum_total_seconds"], "maximum_total_seconds"), retries)
        if policy.initial_seconds > policy.maximum_seconds:
            refuse("invalid_policy", "the first pause cannot be longer than the longest pause")
        return policy

    def to_dict(self) -> dict:
        return {"initial_seconds": self.initial_seconds, "maximum_seconds": self.maximum_seconds,
                "maximum_total_seconds": self.maximum_total_seconds,
                "maximum_retries_per_call": self.maximum_retries_per_call}


POLICY_FIELDS = ("minimum_approvals", "minimum_distinct_families", "exclude_producer_family",
                 "any_rejection_withholds_approval", "reviewers_per_item", "stop_asking_after_first_rejection",
                 "prechecks", "accepted_licences", "output_allocation_tokens", "temperature", "rate_limit")


@dataclass(frozen=True)
class PanelPolicy:
    """The approval rule, the pre-checks, the accepted licences and the call settings of one panel."""

    minimum_approvals: int
    minimum_distinct_families: int
    exclude_producer_family: bool
    any_rejection_withholds_approval: bool
    reviewers_per_item: int
    stop_asking_after_first_rejection: bool
    prechecks: MappingProxyType
    accepted_licences: tuple
    output_allocation_tokens: int
    temperature: float
    rate_limit: RateLimitPolicy

    @classmethod
    def from_dict(cls, value) -> "PanelPolicy":
        part = read_record(value, POLICY_RECORD, POLICY_FIELDS)
        approvals = positive_integer(part["minimum_approvals"], "minimum_approvals")
        families = positive_integer(part["minimum_distinct_families"], "minimum_distinct_families")
        if approvals < QUORUM_FLOOR or families < QUORUM_FLOOR:
            refuse("policy_quorum_below_floor",
                   f"approval needs at least {QUORUM_FLOOR} approvals from {QUORUM_FLOOR} model families")
        if families > approvals:
            refuse("invalid_policy", "a quorum cannot need more families than approvals")
        asked = positive_integer(part["reviewers_per_item"], "reviewers_per_item")
        if asked < approvals:
            refuse("policy_reviewers_below_quorum", "each item must be put to at least as many reviewers as approve it")
        if part["exclude_producer_family"] is not True:
            refuse("policy_producer_family_admitted", "the family that produced an item may never approve it")
        if part["any_rejection_withholds_approval"] is not True:
            refuse("policy_rejection_ignored", "one written rejection must keep the item a candidate")
        temperature = part["temperature"]
        if type(temperature) not in (int, float) or not 0 <= temperature <= MAXIMUM_TEMPERATURE:
            refuse("invalid_policy", f"temperature must be between 0 and {MAXIMUM_TEMPERATURE}")
        return cls(approvals, families, True, True, asked,
                   boolean(part["stop_asking_after_first_rejection"], "stop_asking_after_first_rejection"),
                   _prechecks(part["prechecks"]), _licences(part["accepted_licences"]),
                   positive_integer(part["output_allocation_tokens"], "output_allocation_tokens"),
                   float(temperature), RateLimitPolicy.from_dict(part["rate_limit"]))

    def to_dict(self) -> dict:
        return {"record_type": POLICY_RECORD, "minimum_approvals": self.minimum_approvals,
                "minimum_distinct_families": self.minimum_distinct_families,
                "exclude_producer_family": self.exclude_producer_family,
                "any_rejection_withholds_approval": self.any_rejection_withholds_approval,
                "reviewers_per_item": self.reviewers_per_item,
                "stop_asking_after_first_rejection": self.stop_asking_after_first_rejection,
                "prechecks": {kind: list(engines) for kind, engines in self.prechecks.items()},
                "accepted_licences": list(self.accepted_licences),
                "output_allocation_tokens": self.output_allocation_tokens, "temperature": self.temperature,
                "rate_limit": self.rate_limit.to_dict()}

    @property
    def sha256(self) -> str:
        return digest(self.to_dict())


def _prechecks(value) -> MappingProxyType:
    if type(value) is not dict:
        refuse("invalid_policy", "prechecks must map each kind to its engines")
    unknown = sorted(set(value) - set(PRECHECK_KINDS))
    if unknown:
        refuse("policy_precheck_kind_unknown", f"unknown pre-check kinds {unknown}")
    chosen = {}
    for kind in PRECHECK_KINDS:
        engines = value.get(kind)
        if type(engines) is not list or not engines:
            refuse("policy_precheck_kind_missing", f"every item needs the {kind} pre-check")
        if len(set(engines)) != len(engines):
            refuse("invalid_policy", f"the {kind} pre-check names one engine twice")
        for engine_id in engines:
            if engine_id not in PRECHECK_ENGINES[kind]:
                refuse("policy_precheck_engine_unknown", f"{engine_id!r} is not an engine of the {kind} pre-check")
        chosen[kind] = tuple(engines)
    return MappingProxyType(chosen)


def _licences(value) -> tuple:
    if type(value) is not list or not value or len(set(value)) != len(value):
        refuse("policy_licence_not_permissive", "the accepted licences are a non-empty list without repeats")
    for licence in value:
        if licence not in PERMISSIVE_LICENCES:
            refuse("policy_licence_not_permissive",
                   f"{licence!r} is not one of the permissive licences {sorted(PERMISSIVE_LICENCES)}")
    return tuple(value)


INSTALLATION_FIELDS = ("installation_id", "engine_kind", "family", "model", "quota_group", "lens", "enabled",
                       "disabled_reason", "settings")


@dataclass(frozen=True)
class ReviewerInstallation:
    """One reviewer as a host declares it: an engine, a model, a family, typed settings and a switch."""

    installation_id: str
    engine_kind: str
    family: str
    model: str
    quota_group: str
    lens: str
    enabled: bool
    disabled_reason: str
    settings: MappingProxyType

    @classmethod
    def from_dict(cls, value, families) -> "ReviewerInstallation":
        part = read_record(value, INSTALLATION_RECORD, INSTALLATION_FIELDS)
        if part["engine_kind"] not in ENGINE_KINDS:
            refuse("installation_engine_kind_unknown", f"engine kinds are {list(ENGINE_KINDS)}")
        if part["family"] not in families:
            refuse("installation_family_unknown",
                   f"{part['family']!r} is not in the declared family vocabulary {list(families)}")
        if part["lens"] not in LENSES:
            refuse("installation_lens_unknown", f"lenses are {list(LENSES)}")
        model = text_field(part["model"], "model", limit=160)
        if any(character.isspace() for character in model):
            refuse("invalid_text", "a model identifier has no whitespace")
        enabled = part["enabled"]
        if type(enabled) is not bool:
            refuse("invalid_policy", "enabled must be true or false")
        reason = text_field(part["disabled_reason"], "disabled_reason", limit=2000, empty=True)
        if not enabled and not reason.strip():
            refuse("installation_disabled_without_reason", "a disabled reviewer says why it is disabled")
        if type(part["settings"]) is not dict:
            refuse("invalid_policy", "settings must be a JSON object")
        frozen = _frozen(part["settings"])
        return cls(identifier(part["installation_id"], "installation_id"), part["engine_kind"], part["family"],
                   model, identifier(part["quota_group"], "quota_group"), part["lens"], enabled, reason, frozen)

    def to_dict(self) -> dict:
        return {"record_type": INSTALLATION_RECORD, "installation_id": self.installation_id,
                "engine_kind": self.engine_kind, "family": self.family, "model": self.model,
                "quota_group": self.quota_group, "lens": self.lens, "enabled": self.enabled,
                "disabled_reason": self.disabled_reason, "settings": thawed(self.settings)}

    @property
    def sha256(self) -> str:
        """The installation digest: the engine kind, the model, the family and every setting."""
        return digest(self.to_dict())

    @property
    def is_fixture(self) -> bool:
        return self.engine_kind == FIXTURE_ENGINE_KIND


def _frozen(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_frozen(item) for item in value)
    return value


def thawed(value):
    """A plain, mutable copy of a frozen settings value."""
    if isinstance(value, MappingProxyType):
        return {key: thawed(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thawed(item) for item in value]
    return value


@dataclass(frozen=True)
class PanelConfiguration:
    """The policy, the family vocabulary, the pre-check engine settings and the installations."""

    policy: PanelPolicy
    families: tuple
    precheck_settings: MappingProxyType
    installations: tuple

    @classmethod
    def from_dict(cls, value) -> "PanelConfiguration":
        part = read_record(value, PANEL_RECORD, ("policy", "families", "precheck_engines", "installations"))
        families = part["families"]
        if (type(families) is not list or not families or len(set(families)) != len(families)
                or any(type(item) is not str for item in families)):
            refuse("invalid_families", "families is a non-empty list of distinct identifiers")
        for family in families:
            identifier(family, "family")
        policy = PanelPolicy.from_dict(part["policy"])
        settings = part["precheck_engines"]
        if type(settings) is not dict:
            refuse("invalid_policy", "precheck_engines maps each engine to its settings")
        known = {engine_id for engine_ids in PRECHECK_ENGINES.values() for engine_id in engine_ids}
        for engine_id, engine_settings in settings.items():
            if engine_id not in known:
                refuse("policy_precheck_engine_unknown", f"{engine_id!r} is not a known pre-check engine")
            if type(engine_settings) is not dict:
                refuse("invalid_policy", f"the settings of {engine_id} must be a JSON object")
        for engine_ids in policy.prechecks.values():
            for engine_id in engine_ids:
                if engine_id not in settings:
                    refuse("policy_precheck_settings_missing", f"{engine_id} is named without its settings")
        installations = part["installations"]
        if type(installations) is not list or not installations:
            refuse("invalid_policy", "installations is a non-empty list")
        built = tuple(ReviewerInstallation.from_dict(item, tuple(families)) for item in installations)
        names = [item.installation_id for item in built]
        if len(set(names)) != len(names):
            refuse("installation_identity_repeated", "two installations share one identity")
        return cls(policy, tuple(families), MappingProxyType({key: _frozen(item) for key, item in settings.items()}),
                   built)

    def engine_settings(self, engine_id: str) -> dict:
        """A plain copy of one pre-check engine's settings, so an engine can never change the panel."""
        return thawed(self.precheck_settings[engine_id])

    def installation(self, installation_id: str) -> ReviewerInstallation:
        for item in self.installations:
            if item.installation_id == installation_id:
                return item
        raise KeyError(installation_id)

    def to_dict(self) -> dict:
        return {"record_type": PANEL_RECORD, "policy": self.policy.to_dict(), "families": list(self.families),
                "precheck_engines": {key: thawed(item) for key, item in self.precheck_settings.items()},
                "installations": [item.to_dict() for item in self.installations]}


@dataclass(frozen=True)
class Criterion:
    """One written criterion: a quote of the review sheet, and the kinds of body it applies to.

    An empty ``applies_to_groundings`` means every kind. The review sheet judges
    its two kinds of body by different grounding criteria, so a reviewer is
    given only the criteria that apply to the body in front of it."""

    criterion_id: str
    quote: str
    applies_to_groundings: tuple = ()


def criterion_applies(criterion: Criterion, grounding: str) -> bool:
    """Whether one criterion applies to a body of the declared kind. A mutant control replaces this rule."""
    return not criterion.applies_to_groundings or grounding in criterion.applies_to_groundings


@dataclass(frozen=True)
class CompiledCriteria:
    """The written criteria and the kinds of body, each a quote of the review sheet, with the sheet digest."""

    criteria: tuple
    source_path: str
    source_sha256: str
    match_mode: str
    groundings: MappingProxyType = MappingProxyType({})

    @property
    def ids(self) -> frozenset:
        return frozenset(item.criterion_id for item in self.criteria)

    def applicable(self, grounding: str) -> tuple:
        """The criteria for a body of the declared kind. An undeclared kind receives only the shared ones;
        the format pre-check refuses such a body before any reviewer is asked."""
        return tuple(item for item in self.criteria if criterion_applies(item, grounding))

    def ordinal(self, grounding: str) -> int:
        """The kind's place in the declared order, which is the order the review sheet names its kinds in."""
        names = list(self.groundings)
        return names.index(grounding) + 1 if grounding in names else 0

    def to_dict(self) -> dict:
        return {"record_type": CRITERIA_RECORD, "source_path": self.source_path, "match_mode": self.match_mode,
                "groundings": [{"grounding": name, "meaning": meaning} for name, meaning in self.groundings.items()],
                "criteria": [{"criterion_id": item.criterion_id, "quote": item.quote,
                              "applies_to_groundings": list(item.applies_to_groundings)} for item in self.criteria]}

    @property
    def sha256(self) -> str:
        """The digest of the criteria text itself, which stays the same when another part of the sheet changes."""
        return digest(self.to_dict())


def _quoted(value, name: str, sheet: str, source_path: str) -> str:
    quote = text_field(value, name, limit=4000)
    if canonical_whitespace(quote) not in sheet:
        refuse("criteria_quote_not_in_source", f"the quote of {name} is not in {source_path}")
    return quote


def compile_criteria(value, source_text: str) -> CompiledCriteria:
    part = read_record(value, CRITERIA_RECORD, ("source_path", "match_mode", "groundings", "criteria"))
    if part["match_mode"] != MATCH_MODE:
        refuse("criteria_match_mode_unsupported", f"this release reads the match mode {MATCH_MODE} only")
    source_path = text_field(part["source_path"], "source_path", limit=400)
    sheet = canonical_whitespace(source_text)
    kinds = part["groundings"]
    if type(kinds) is not list or not kinds:
        refuse("invalid_criteria", "groundings is a non-empty list of the kinds of body")
    groundings = {}
    for row in kinds:
        item = read_part(row, "grounding", ("grounding", "meaning"))
        name = identifier(item["grounding"], "grounding")
        if name in groundings:
            refuse("criteria_identity_repeated", f"the kind {name} is declared twice")
        groundings[name] = _quoted(item["meaning"], f"the kind {name}", sheet, source_path)
    rows = part["criteria"]
    if type(rows) is not list or not rows:
        refuse("invalid_criteria", "criteria is a non-empty list")
    built, seen = [], set()
    for row in rows:
        item = read_part(row, "criterion", ("criterion_id", "quote", "applies_to_groundings"))
        criterion_id = item["criterion_id"]
        if (type(criterion_id) is not str or not 3 <= len(criterion_id) <= CRITERION_IDENTIFIER_LIMIT
                or not criterion_id.replace("_", "").isalnum() or not criterion_id[0].isalpha()
                or criterion_id != criterion_id.lower()):
            refuse("invalid_criteria", "a criterion identifier is lower case letters, digits and underscores")
        if criterion_id in seen:
            refuse("criteria_identity_repeated", f"{criterion_id} is named twice")
        seen.add(criterion_id)
        applies = item["applies_to_groundings"]
        if type(applies) is not list or len(set(map(str, applies))) != len(applies):
            refuse("invalid_criteria", f"the kinds of {criterion_id} are a list without repeats")
        unknown = sorted(str(kind) for kind in applies if kind not in groundings)
        if unknown:
            refuse("criteria_grounding_unknown", f"{criterion_id} names the undeclared kinds {unknown}")
        built.append(Criterion(criterion_id, _quoted(item["quote"], criterion_id, sheet, source_path),
                               tuple(applies)))
    return CompiledCriteria(tuple(built), source_path, sha256_hex(source_text.encode("utf-8")), MATCH_MODE,
                            MappingProxyType(groundings))


@dataclass(frozen=True)
class Producer:
    producer_identity: str
    family: str

    def to_dict(self) -> dict:
        return {"producer_identity": self.producer_identity, "family": self.family}


@dataclass(frozen=True)
class ProducerDeclaration:
    """Who produced each item, declared with evidence. A family is never inferred from a name."""

    catalogue_folder: str
    default_producer: Producer
    item_producers: MappingProxyType
    evidence_path: str
    evidence_quote: str

    @classmethod
    def from_dict(cls, value, evidence_text: str, families) -> "ProducerDeclaration":
        part = read_record(value, PRODUCER_RECORD, ("catalogue_folder", "default_producer", "item_producers",
                                                    "evidence"))

        def producer(raw, name, fields=("producer_identity", "family")):
            item = read_part(raw, name, fields)
            if item["family"] not in families:
                refuse("producer_family_unknown", f"{item['family']!r} is not in the family vocabulary")
            return Producer(text_field(item["producer_identity"], "producer_identity", limit=200), item["family"])

        overrides = part["item_producers"]
        if type(overrides) is not list:
            refuse("invalid_producers", "item_producers is a list")
        mapped = {}
        for raw in overrides:
            item = read_part(raw, "item_producer", ("identity", "producer_identity", "family"))
            if item["identity"] in mapped:
                refuse("invalid_producers", f"{item['identity']} is declared twice")
            mapped[item["identity"]] = producer({"producer_identity": item["producer_identity"],
                                                 "family": item["family"]}, "item_producer")
        evidence = read_part(part["evidence"], "evidence", ("path", "quote"))
        quote = text_field(evidence["quote"], "evidence quote", limit=1000)
        if canonical_whitespace(quote) not in canonical_whitespace(evidence_text):
            refuse("producer_evidence_not_in_source", f"the evidence quote is not in {evidence['path']}")
        return cls(text_field(part["catalogue_folder"], "catalogue_folder", limit=400),
                   producer(part["default_producer"], "default_producer"), MappingProxyType(mapped),
                   text_field(evidence["path"], "evidence path", limit=400), quote)

    def producer_for(self, identity: str) -> Producer:
        return self.item_producers.get(identity, self.default_producer)

    def to_dict(self) -> dict:
        return {"record_type": PRODUCER_RECORD, "catalogue_folder": self.catalogue_folder,
                "default_producer": self.default_producer.to_dict(),
                "item_producers": [{"identity": identity, **producer.to_dict()}
                                   for identity, producer in sorted(self.item_producers.items())],
                "evidence": {"path": self.evidence_path, "quote": self.evidence_quote}}


EVERY_REVIEWER, ANSWER, LENS_PREFIX = "Every reviewer", "Answer", "Lens: "


@dataclass(frozen=True)
class Instructions:
    """The versioned instruction resource, split into its named sections."""

    path: str
    text: str
    sections: MappingProxyType

    @classmethod
    def from_text(cls, path: str, text: str) -> "Instructions":
        sections, name, lines = {}, None, []
        for line in text.splitlines():
            if line.startswith("## "):
                if name is not None:
                    sections[name] = "\n".join(lines).strip()
                name, lines = line[3:].strip(), []
            elif name is not None:
                lines.append(line)
        if name is not None:
            sections[name] = "\n".join(lines).strip()
        required = [EVERY_REVIEWER, ANSWER] + [LENS_PREFIX + lens for lens in LENSES]
        for section in required:
            if not sections.get(section):
                refuse("instructions_section_missing", f"the instructions need the section {section!r}")
        return cls(path, text, MappingProxyType(sections))

    @property
    def sha256(self) -> str:
        return sha256_hex(self.text.encode("utf-8"))

    def every_reviewer(self) -> str:
        return self.sections[EVERY_REVIEWER]

    def lens(self, name: str) -> str:
        if name not in LENSES:
            raise CandidateReviewError("installation_lens_unknown", f"lenses are {list(LENSES)}")
        return self.sections[LENS_PREFIX + name]

    def answer(self) -> str:
        return self.sections[ANSWER]


def load_instructions(path: Path) -> Instructions:
    return Instructions.from_text(str(path), Path(path).read_text(encoding="utf-8"))
