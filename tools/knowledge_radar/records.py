"""Typed records of the knowledge radar, each written name/vN and read strictly.

The radar answers recurring engineering questions once, for everyone, and
serves each answer as dated files a harness can load: a decision card, a
data file with its schema, a small decision helper over that data, or a tool
that fetches a fact too volatile to store. Every record below has an exact
type, version and field set; a reader refuses another version, an unknown
field or a missing field before anything is built from it. The shared
reading rules come from the library ingestion component
(`core/library_ingestion/record_rules.py`).

```text
knowledge_radar_question_registry/v1     the declared questions and the delivery rule
└── knowledge_radar_question/v1          one recurring engineering question: audience,
    │                                    constraints, baseline, acceptable evidence, intended
    │                                    output, research cost, volatility, delivery, refresh,
    │                                    sensitivity, questions to ask again, negative knowledge
    ├── source binding                   one engine of the source edge and its parameters
    └── seed                             an official link a person chose, never a number
knowledge_radar_source_contract/v1       how one engine may read its source: access method,
                                         permitted uses, attribution, rate, parser, failure policy
knowledge_radar_observation/v1           one dated claim an engine observed, with its common
                                         origin and every time field
knowledge_radar_source_check/v1          one binding's check outcome for one run
knowledge_radar_plan/v1                  the questions one run selected and why
knowledge_radar_brief/v1                 one question's decision card and evidence
knowledge_radar_vetting/v1               one package's separate vetting dimensions
```

The owner's rule of September 27, 2026 is typed here, not written in prose:
research that costs an engineer more than a few minutes across several
sources, about facts that change more slowly than the radar refreshes, is
done once and delivered as a brief or a data file; a fact that changes
faster than the radar refreshes (a price, a quote, a status) is delivered as
a tool that fetches it, never as a stored number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from loop_engine.core.library_ingestion.record_rules import (
    LibraryRecordError,
    count,
    member,
    read_part,
    read_record,
    text_value,
)

REGISTRY_RECORD_TYPE = "knowledge_radar_question_registry/v1"
QUESTION_RECORD_TYPE = "knowledge_radar_question/v1"
CONTRACTS_RECORD_TYPE = "knowledge_radar_source_contracts/v1"
CONTRACT_RECORD_TYPE = "knowledge_radar_source_contract/v1"
OBSERVATION_RECORD_TYPE = "knowledge_radar_observation/v1"
CHECK_RECORD_TYPE = "knowledge_radar_source_check/v1"
PLAN_RECORD_TYPE = "knowledge_radar_plan/v1"
BRIEF_RECORD_TYPE = "knowledge_radar_brief/v1"
NOTICE_RECORD_TYPE = "knowledge_radar_notice/v1"
VETTING_RECORD_TYPE = "knowledge_radar_vetting/v1"

AREAS = ("papers", "benchmarks", "models", "pipelines", "tools", "infrastructure", "calendars",
         "security", "licences_and_pricing", "regulation", "events", "markets", "standards")
SENSITIVITIES = ("general", "legal", "security", "financial")
#: How fast the facts of a question change, fastest first.
VOLATILITIES = ("hours", "days", "weeks", "months")
#: How often the radar rebuilds a question, fastest first. Each cadence keeps up with
#: the volatility at the same position: a daily refresh keeps up with facts that change
#: over days, not with facts that change within hours.
REFRESHES = ("hourly", "daily", "weekly", "monthly")
REFRESH_DAYS = {"hourly": 0, "daily": 1, "weekly": 7, "monthly": 30}
DELIVERIES = ("brief", "data_file", "decision_helper", "tool")
STORED = frozenset(("brief", "data_file", "decision_helper"))
STATUSES = ("active", "declared_gap")
#: The outcome of checking one source binding. A failed read is never "no change".
CHECK_OUTCOMES = ("checked_no_relevant_change", "checked_material_change", "partially_checked",
                  "could_not_check", "source_disappeared_or_access_changed")
CHECKED_OUTCOMES = frozenset(("checked_no_relevant_change", "checked_material_change"))
#: Why the planner selected a question for a run.
PLAN_REASONS = ("first_run", "overdue", "changed_source", "demand", "exploration")
CONFIDENCE = ("high", "medium", "low")
#: The separate vetting dimensions of a package. There is no single "vetted" flag.
VETTING_DIMENSIONS = ("source_identity_checked", "claim_supported_by_cited_evidence",
                      "implementation_inspected", "implementation_tested_or_reproduced",
                      "compatibility_tested", "publication_approved_for_scope")
VETTING_STATES = ("passed", "failed", "not_applicable", "not_done")
#: Review requirement written on every package of a sensitive question.
STRICT_REVIEW = "two_independent_families_sources_on_every_claim"
ORDINARY_REVIEW = "existing_screen_then_feedback"
ACCESS_METHODS = ("local_file", "https_get", "gh_api")
#: Every time field a claim may carry. Unknown stays null; it is never filled from another field.
TIME_FIELDS = ("event_at", "source_published_at", "observed_at", "effective_from", "effective_until",
               "last_verified_at", "review_after")

_QUESTION_ID = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")
_ENGINE_ID = re.compile(r"[a-z][a-z0-9_]{1,40}\Z")
_ASSET_ID = re.compile(r"[a-z][a-z0-9_]{1,40}\Z")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)?\Z")
_HTTPS = re.compile(r"https://[a-z0-9.-]+\.[a-z]{2,}(?:[/?#][^\s<>\"'`]*)?\Z", re.IGNORECASE)
_NUMBER_BESIDE_UNIT = re.compile(r"\d+\s*(?:%|\$|usd|gb|mb|ms|per\b|/)", re.IGNORECASE)
_QUESTION_FIELDS = ("record_type", "id", "question", "title", "area", "status", "gap_reason", "audience",
                    "constraints", "baseline", "acceptable_evidence", "intended_output", "purpose",
                    "use_when", "sensitivity", "research_cost", "volatility", "refresh", "delivery",
                    "valid_days", "reask", "recheck", "not_established", "would_change", "limit",
                    "sources", "seeds", "assets")
_REGISTRY_FIELDS = ("record_type", "registry_version", "revised_on", "rule", "planner", "questions")
_RULE_FIELDS = ("research_minutes_threshold", "research_sources_threshold")
_PLANNER_FIELDS = ("maximum_questions", "exploration_share")
_SEED_FIELDS = ("name", "url", "kind", "links")
_SEED_KINDS = ("hosted_service", "open_source_project", "official_source", "standard", "dataset", "paper")
_SEED_LINK_NAMES = ("documentation", "pricing", "status", "repository", "terms", "changelog")
_CONTRACT_FIELDS = ("record_type", "engine_id", "parser_version", "access_method", "hosts", "permitted_uses",
                    "never_used", "attribution", "terms_address", "minimum_seconds_between_requests",
                    "maximum_requests_per_run", "failure_policy")
_OBSERVATION_FIELDS = ("record_type", "key", "origin", "title", "url", "engine_id", "engine_version", "section",
                       "source_address", "licence", "licence_basis", "facts", *TIME_FIELDS)
_FACT_VALUE = (str, int, float, bool, type(None))


def refuse(code: str, message: str):
    raise LibraryRecordError(code, message)


def https_address(value, name: str) -> str:
    """A public https address; any other scheme or a malformed address is refused."""
    if type(value) is not str or len(value) > 2048 or not _HTTPS.fullmatch(value):
        refuse("radar_address_invalid", f"{name} must be a public https address")
    return value


def day(value, name: str) -> str:
    if type(value) is not str or not _DAY.fullmatch(value):
        refuse("radar_day_invalid", f"{name} must be a day written YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError:
        refuse("radar_day_invalid", f"{name} must be a real day")
    return value


def time_value(value, name: str):
    """A day or a UTC time, or null for an unknown time. Nothing is guessed."""
    if value is None:
        return None
    if type(value) is not str or not _TIME.fullmatch(value):
        refuse("radar_time_invalid", f"{name} is a day or a UTC time, or null when unknown")
    day(value[:10], name)
    return value


def _texts(values, name: str, *, maximum: int, limit: int = 300, nonempty: bool = True) -> tuple:
    if type(values) is not list or len(values) > maximum or (nonempty and not values):
        refuse("radar_list_invalid", f"{name} must be a list of up to {maximum} lines")
    lines = tuple(text_value(value, name, limit=limit) for value in values)
    if len(set(lines)) != len(lines):
        refuse("radar_list_invalid", f"{name} repeats a line")
    return lines


@dataclass(frozen=True)
class ResearchCost:
    """What one engineer spends to answer the question by hand: minutes and distinct sources."""

    engineer_minutes: int
    sources: int


@dataclass(frozen=True)
class SourceBinding:
    """One engine of the source edge, the section of the brief it fills and its parameters."""

    engine: str
    section: str
    parameters: dict

    def to_dict(self) -> dict:
        return {"engine": self.engine, "section": self.section, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class Seed:
    """An official link a person chose for a question. It holds names and links, never a measured number."""

    name: str
    url: str
    kind: str
    links: dict

    def to_dict(self) -> dict:
        return {"name": self.name, "url": self.url, "kind": self.kind, "links": dict(self.links)}


@dataclass(frozen=True)
class RadarQuestion:
    """One recurring engineering question the radar answers once for everyone."""

    id: str
    question: str
    title: str
    area: str
    status: str
    gap_reason: str
    audience: str
    constraints: tuple
    baseline: str
    acceptable_evidence: tuple
    intended_output: str
    purpose: str
    use_when: str
    sensitivity: str
    research_cost: ResearchCost
    volatility: str
    refresh: str
    delivery: tuple
    valid_days: int
    reask: tuple
    recheck: tuple
    not_established: tuple
    would_change: tuple
    limit: int
    sources: tuple
    seeds: tuple
    assets: dict

    @property
    def review_requirement(self) -> str:
        return STRICT_REVIEW if self.sensitivity != "general" else ORDINARY_REVIEW

    def review_after(self, observed_day: str) -> str:
        return (date.fromisoformat(observed_day[:10]) + timedelta(days=self.valid_days)).isoformat()

    def to_dict(self) -> dict:
        return {"record_type": QUESTION_RECORD_TYPE, "id": self.id, "question": self.question,
                "title": self.title, "area": self.area, "status": self.status, "gap_reason": self.gap_reason,
                "audience": self.audience, "constraints": list(self.constraints), "baseline": self.baseline,
                "acceptable_evidence": list(self.acceptable_evidence), "intended_output": self.intended_output,
                "purpose": self.purpose, "use_when": self.use_when, "sensitivity": self.sensitivity,
                "research_cost": {"engineer_minutes": self.research_cost.engineer_minutes,
                                  "sources": self.research_cost.sources},
                "volatility": self.volatility, "refresh": self.refresh, "delivery": list(self.delivery),
                "valid_days": self.valid_days, "reask": list(self.reask), "recheck": list(self.recheck),
                "not_established": list(self.not_established), "would_change": list(self.would_change),
                "limit": self.limit, "sources": [binding.to_dict() for binding in self.sources],
                "seeds": [seed.to_dict() for seed in self.seeds], "assets": dict(self.assets)}


@dataclass(frozen=True)
class DeliveryRule:
    """The owner's threshold: more than this many minutes or sources is worth doing once for everyone."""

    research_minutes_threshold: int
    research_sources_threshold: int


@dataclass(frozen=True)
class PlannerPolicy:
    """How many questions one run may take and what share of them explores questions not yet due."""

    maximum_questions: int
    exploration_share: float


@dataclass(frozen=True)
class QuestionRegistry:
    registry_version: str
    revised_on: str
    rule: DeliveryRule
    planner: PlannerPolicy
    questions: tuple

    def question(self, identity: str) -> RadarQuestion:
        for question in self.questions:
            if question.id == identity:
                return question
        refuse("radar_question_unknown", f"{identity!r} is not a declared question")

    def active(self) -> tuple:
        return tuple(question for question in self.questions if question.status == "active")


def _binding(value, question_id: str) -> SourceBinding:
    part = read_part(value, f"{question_id} source", ("engine", "section", "parameters"))
    engine = part["engine"]
    if type(engine) is not str or not _ENGINE_ID.fullmatch(engine):
        refuse("radar_engine_invalid", f"{question_id} names an engine identity that is not a lowercase token")
    section = text_value(part["section"], f"{question_id} section", limit=120)
    parameters = part["parameters"]
    if type(parameters) is not dict or any(type(key) is not str for key in parameters):
        refuse("radar_parameters_invalid", f"{question_id} parameters must be a mapping with text keys")
    for key, item in parameters.items():
        values = item if type(item) is list else [item]
        if any(type(entry) not in (str, int, float, bool) for entry in values):
            refuse("radar_parameters_invalid", f"{question_id} parameter {key} must hold plain values")
    return SourceBinding(engine, section, dict(parameters))


def _seed(value, question_id: str) -> Seed:
    part = read_part(value, f"{question_id} seed", _SEED_FIELDS)
    name = text_value(part["name"], f"{question_id} seed name", limit=120)
    if _NUMBER_BESIDE_UNIT.search(name):
        refuse("radar_seed_holds_number", f"{question_id} seed {name!r} holds a measured number")
    url = https_address(part["url"], f"{question_id} seed url")
    kind = member(part["kind"], f"{question_id} seed kind", _SEED_KINDS)
    links = part["links"]
    if type(links) is not dict or any(key not in _SEED_LINK_NAMES for key in links):
        refuse("radar_seed_invalid", f"{question_id} seed links use the names {_SEED_LINK_NAMES}")
    checked = {key: https_address(link, f"{question_id} seed {key}") for key, link in sorted(links.items())}
    return Seed(name, url, kind, checked)


def read_question(value, rule: "DeliveryRule | None" = None) -> RadarQuestion:
    part = read_record(value, QUESTION_RECORD_TYPE, _QUESTION_FIELDS)
    identity = part["id"]
    if type(identity) is not str or not _QUESTION_ID.fullmatch(identity) or len(identity) > 44:
        refuse("radar_question_identity_invalid", "a question identity is a short lowercase snake_case token")
    status = member(part["status"], f"{identity} status", STATUSES)
    gap_reason = part["gap_reason"]
    if type(gap_reason) is not str or len(gap_reason) > 600 or (status == "declared_gap") != bool(gap_reason.strip()):
        refuse("radar_gap_reason_invalid", f"{identity} states a gap reason exactly when it is a declared gap")
    cost = read_part(part["research_cost"], f"{identity} research_cost", ("engineer_minutes", "sources"))
    delivery = part["delivery"]
    if type(delivery) is not list or not delivery or len(set(delivery)) != len(delivery):
        refuse("radar_delivery_invalid", f"{identity} delivery is a nonempty list without repeats")
    for kind in delivery:
        member(kind, f"{identity} delivery", DELIVERIES)
    valid_days = count(part["valid_days"], f"{identity} valid_days", maximum=366)
    limit = count(part["limit"], f"{identity} limit", maximum=60)
    if valid_days < 1 or limit < 1:
        refuse("radar_bound_invalid", f"{identity} valid_days and limit are at least one")
    sources, seeds, assets = part["sources"], part["seeds"], part["assets"]
    if type(sources) is not list or type(seeds) is not list or type(assets) is not dict:
        refuse("radar_question_shape_invalid", f"{identity} sources and seeds are lists, assets a mapping")
    if any(type(key) is not str or key not in DELIVERIES or type(item) is not str or not _ASSET_ID.fullmatch(item)
           for key, item in assets.items()):
        refuse("radar_assets_invalid", f"{identity} assets map a delivery kind to an asset identity")
    question = RadarQuestion(
        id=identity,
        question=text_value(part["question"], f"{identity} question", limit=300),
        title=text_value(part["title"], f"{identity} title", limit=120),
        area=member(part["area"], f"{identity} area", AREAS),
        status=status,
        gap_reason=gap_reason.strip(),
        audience=text_value(part["audience"], f"{identity} audience", limit=200),
        constraints=_texts(part["constraints"], f"{identity} constraints", maximum=8),
        baseline=text_value(part["baseline"], f"{identity} baseline", limit=400),
        acceptable_evidence=_texts(part["acceptable_evidence"], f"{identity} acceptable_evidence", maximum=8),
        intended_output=text_value(part["intended_output"], f"{identity} intended_output", limit=300),
        purpose=text_value(part["purpose"], f"{identity} purpose", limit=400),
        use_when=text_value(part["use_when"], f"{identity} use_when", limit=300),
        sensitivity=member(part["sensitivity"], f"{identity} sensitivity", SENSITIVITIES),
        research_cost=ResearchCost(count(cost["engineer_minutes"], f"{identity} engineer_minutes", maximum=10000),
                                   count(cost["sources"], f"{identity} research sources", maximum=1000)),
        volatility=member(part["volatility"], f"{identity} volatility", VOLATILITIES),
        refresh=member(part["refresh"], f"{identity} refresh", REFRESHES),
        delivery=tuple(delivery),
        valid_days=valid_days,
        reask=_texts(part["reask"], f"{identity} reask", maximum=8),
        recheck=_texts(part["recheck"], f"{identity} recheck", maximum=8),
        not_established=_texts(part["not_established"], f"{identity} not_established", maximum=8),
        would_change=_texts(part["would_change"], f"{identity} would_change", maximum=8),
        limit=limit,
        sources=tuple(_binding(binding, identity) for binding in sources),
        seeds=tuple(_seed(seed, identity) for seed in seeds),
        assets=dict(assets),
    )
    stored = [kind for kind in question.delivery if kind in STORED]
    if status == "active" and stored and not question.sources and not question.seeds:
        refuse("radar_question_without_source", f"{identity} stores an answer but names no source engine and no seed")
    if not stored and (question.sources or question.seeds):
        refuse("radar_tool_question_with_sources", f"{identity} delivers only a tool, which reads its source when called")
    if rule is not None:
        findings = rule_findings(question, rule)
        if findings:
            refuse(findings[0][0], findings[0][1])
    return question


def rule_findings(question: RadarQuestion, rule: DeliveryRule) -> list:
    """The owner's delivery rule as checks. An empty list means the question's delivery follows it.

    1. A fact that changes faster than the radar refreshes is served as a tool, and nothing stored
       (no brief, data file or decision helper) may be the delivery of that fact.
    2. Research above the threshold about facts no faster than the refresh is served as a stored
       file: a brief or a data file.
    3. Research at or below the threshold is not worth holding as a file; at most a tool is served.
    4. A tool or a decision helper names the asset that implements it, and a helper reads a data file.
    """
    findings = []
    fast = VOLATILITIES.index(question.volatility) < REFRESHES.index(question.refresh)
    costly = (question.research_cost.engineer_minutes > rule.research_minutes_threshold
              or question.research_cost.sources > rule.research_sources_threshold)
    stored = [kind for kind in question.delivery if kind in STORED]
    if fast and "tool" not in question.delivery:
        findings.append(("radar_volatile_fact_needs_tool",
                         f"{question.id} changes within {question.volatility} but refreshes {question.refresh}; "
                         "serve a tool that fetches it"))
    if fast and stored:
        findings.append(("radar_volatile_fact_stored",
                         f"{question.id} would store {stored} for facts that change within {question.volatility}"))
    if costly and not fast and not ({"brief", "data_file"} & set(question.delivery)):
        findings.append(("radar_costly_research_not_stored",
                         f"{question.id} costs {question.research_cost.engineer_minutes} minutes across "
                         f"{question.research_cost.sources} sources; serve a brief or a data file"))
    if not costly and stored:
        findings.append(("radar_trivial_research_stored",
                         f"{question.id} costs {question.research_cost.engineer_minutes} minutes in "
                         f"{question.research_cost.sources} source; a harness can look it up or call a tool"))
    for kind in ("tool", "decision_helper"):
        if kind in question.delivery and kind not in question.assets:
            findings.append(("radar_asset_missing", f"{question.id} delivers a {kind} but names no asset"))
    if any(kind not in question.delivery for kind in question.assets):
        findings.append(("radar_asset_not_delivered", f"{question.id} names an asset for a kind it does not deliver"))
    if "decision_helper" in question.delivery and "data_file" not in question.delivery:
        findings.append(("radar_helper_without_data", f"{question.id} has a decision helper with no data file to read"))
    return findings


def read_registry(value) -> QuestionRegistry:
    part = read_record(value, REGISTRY_RECORD_TYPE, _REGISTRY_FIELDS)
    version = text_value(part["registry_version"], "registry_version", limit=20)
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        refuse("radar_registry_version_invalid", "registry_version is major.minor.patch")
    rule_part = read_part(part["rule"], "rule", _RULE_FIELDS)
    rule = DeliveryRule(count(rule_part["research_minutes_threshold"], "research_minutes_threshold", maximum=600),
                        count(rule_part["research_sources_threshold"], "research_sources_threshold", maximum=50))
    planner_part = read_part(part["planner"], "planner", _PLANNER_FIELDS)
    share = planner_part["exploration_share"]
    if type(share) not in (int, float) or not 0 <= share <= 0.5:
        refuse("radar_planner_invalid", "exploration_share is a fraction from 0 to 0.5")
    planner = PlannerPolicy(count(planner_part["maximum_questions"], "maximum_questions", maximum=400), float(share))
    questions = part["questions"]
    if type(questions) is not list or not questions or len(questions) > 400:
        refuse("radar_questions_invalid", "questions is a nonempty bounded list")
    read = tuple(read_question(question, rule) for question in questions)
    identities = [question.id for question in read]
    if len(set(identities)) != len(identities):
        refuse("radar_question_duplicate", "each question identity appears once")
    return QuestionRegistry(version, day(part["revised_on"], "revised_on"), rule, planner, read)


@dataclass(frozen=True)
class SourceContract:
    """The ingestion contract of one engine: how it may read, what it may keep and what failure means."""

    engine_id: str
    parser_version: str
    access_method: str
    hosts: tuple
    permitted_uses: str
    never_used: str
    attribution: str
    terms_address: str
    minimum_seconds_between_requests: float
    maximum_requests_per_run: int
    failure_policy: str

    def to_dict(self) -> dict:
        return {"record_type": CONTRACT_RECORD_TYPE, "engine_id": self.engine_id,
                "parser_version": self.parser_version, "access_method": self.access_method,
                "hosts": list(self.hosts), "permitted_uses": self.permitted_uses, "never_used": self.never_used,
                "attribution": self.attribution, "terms_address": self.terms_address,
                "minimum_seconds_between_requests": self.minimum_seconds_between_requests,
                "maximum_requests_per_run": self.maximum_requests_per_run, "failure_policy": self.failure_policy}


def read_contracts(value) -> dict:
    part = read_record(value, CONTRACTS_RECORD_TYPE, ("record_type", "revised_on", "contracts"))
    day(part["revised_on"], "revised_on")
    rows = part["contracts"]
    if type(rows) is not list or not rows:
        refuse("radar_contracts_invalid", "contracts is a nonempty list")
    contracts = {}
    for row in rows:
        item = read_record(row, CONTRACT_RECORD_TYPE, _CONTRACT_FIELDS)
        engine = item["engine_id"]
        if type(engine) is not str or not _ENGINE_ID.fullmatch(engine) or engine in contracts:
            refuse("radar_contract_invalid", "each contract names one engine once")
        hosts = item["hosts"]
        if type(hosts) is not list or any(type(host) is not str or not re.fullmatch(r"[a-z0-9.-]+", host)
                                          for host in hosts):
            refuse("radar_contract_invalid", f"{engine} hosts are lowercase host names")
        method = member(item["access_method"], f"{engine} access_method", ACCESS_METHODS)
        if (method == "local_file") != (not hosts):
            refuse("radar_contract_invalid", f"{engine} names hosts exactly when it reads the network")
        pause = item["minimum_seconds_between_requests"]
        if type(pause) not in (int, float) or not 0 <= pause <= 60:
            refuse("radar_contract_invalid", f"{engine} minimum_seconds_between_requests is 0 to 60")
        contracts[engine] = SourceContract(
            engine, text_value(item["parser_version"], f"{engine} parser_version", limit=20), method, tuple(hosts),
            text_value(item["permitted_uses"], f"{engine} permitted_uses", limit=400),
            text_value(item["never_used"], f"{engine} never_used", limit=400),
            text_value(item["attribution"], f"{engine} attribution", limit=300),
            https_address(item["terms_address"], f"{engine} terms_address"), float(pause),
            count(item["maximum_requests_per_run"], f"{engine} maximum_requests_per_run", maximum=500),
            text_value(item["failure_policy"], f"{engine} failure_policy", limit=300))
    return contracts


@dataclass(frozen=True)
class Observation:
    """One claim an engine observed in a source: a name, a link, plain facts and every known time.

    ``origin`` is the common origin of the claim: the paper, repository, model, advisory or product it
    is about. Several listings repeating one origin are one source, not several confirmations.
    """

    key: str
    origin: str
    title: str
    url: str
    engine_id: str
    engine_version: str
    section: str
    source_address: str
    observed_at: str
    licence: "str | None" = None
    licence_basis: str = "not stated by the source"
    facts: dict = field(default_factory=dict)
    event_at: "str | None" = None
    source_published_at: "str | None" = None
    effective_from: "str | None" = None
    effective_until: "str | None" = None
    last_verified_at: "str | None" = None
    review_after: "str | None" = None

    def to_dict(self) -> dict:
        return {"record_type": OBSERVATION_RECORD_TYPE, "key": self.key, "origin": self.origin,
                "title": self.title, "url": self.url, "engine_id": self.engine_id,
                "engine_version": self.engine_version, "section": self.section,
                "source_address": self.source_address, "licence": self.licence,
                "licence_basis": self.licence_basis, "facts": dict(sorted(self.facts.items())),
                "event_at": self.event_at, "source_published_at": self.source_published_at,
                "observed_at": self.observed_at, "effective_from": self.effective_from,
                "effective_until": self.effective_until, "last_verified_at": self.last_verified_at,
                "review_after": self.review_after}


def read_observation(value) -> Observation:
    part = read_record(value, OBSERVATION_RECORD_TYPE, _OBSERVATION_FIELDS)
    facts = part["facts"]
    if type(facts) is not dict or any(type(key) is not str or type(item) not in _FACT_VALUE
                                      for key, item in facts.items()):
        refuse("radar_observation_invalid", "facts holds plain named values")
    licence = part["licence"]
    if licence is not None:
        text_value(licence, "licence", limit=80)
    times = {name: time_value(part[name], name) for name in TIME_FIELDS}
    if times["observed_at"] is None:
        refuse("radar_observation_invalid", "every observation states when it was observed")
    return Observation(
        key=text_value(part["key"], "key", limit=300), origin=text_value(part["origin"], "origin", limit=300),
        title=text_value(part["title"], "title", limit=300), url=https_address(part["url"], "url"),
        engine_id=text_value(part["engine_id"], "engine_id", limit=60),
        engine_version=text_value(part["engine_version"], "engine_version", limit=20),
        section=text_value(part["section"], "section", limit=120),
        source_address=text_value(part["source_address"], "source_address", limit=400),
        licence=licence, licence_basis=text_value(part["licence_basis"], "licence_basis", limit=200),
        facts=dict(facts), **times)


@dataclass(frozen=True)
class SourceCheck:
    """One binding's check outcome for one run, with the observations it produced or why it has none."""

    question_id: str
    engine_id: str
    engine_version: str
    section: str
    outcome: str
    reason: str
    observations: tuple
    requests: int
    checked_at: str
    changes: tuple = ()

    def to_dict(self) -> dict:
        return {"record_type": CHECK_RECORD_TYPE, "question_id": self.question_id, "engine_id": self.engine_id,
                "engine_version": self.engine_version, "section": self.section, "outcome": self.outcome,
                "reason": self.reason, "observations": [item.to_dict() for item in self.observations],
                "requests": self.requests, "checked_at": self.checked_at, "changes": list(self.changes)}


def read_check(value) -> SourceCheck:
    part = read_record(value, CHECK_RECORD_TYPE, ("record_type", "question_id", "engine_id", "engine_version",
                                                   "section", "outcome", "reason", "observations", "requests",
                                                   "checked_at", "changes"))
    outcome = member(part["outcome"], "outcome", CHECK_OUTCOMES)
    rows = part["observations"]
    if type(rows) is not list or (outcome not in CHECKED_OUTCOMES and outcome != "partially_checked" and rows):
        refuse("radar_check_invalid", "only a completed or partial check carries observations")
    changes = part["changes"]
    if type(changes) is not list or any(type(item) is not str for item in changes):
        refuse("radar_check_invalid", "changes is a list of text lines")
    return SourceCheck(text_value(part["question_id"], "question_id", limit=60),
                       text_value(part["engine_id"], "engine_id", limit=60),
                       text_value(part["engine_version"], "engine_version", limit=20),
                       text_value(part["section"], "section", limit=120), outcome,
                       text_value(part["reason"], "reason", limit=600) if part["reason"] else "",
                       tuple(read_observation(row) for row in rows),
                       count(part["requests"], "requests", maximum=1000),
                       text_value(part["checked_at"], "checked_at", limit=30), tuple(changes))
