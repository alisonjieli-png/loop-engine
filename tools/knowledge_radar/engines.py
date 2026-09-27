"""The radar's source edge, `knowledge_radar_source/v1`, and its engine registry.

One edge, many engines. Every engine answers the same typed request (a
question, one source binding, the run's clock and the run's bounded network)
with the same typed answer: a status, observations, the number of requests
it spent, the source prose it saw and must never be copied, and the entries
it excluded with the reason. The pipeline turns each answer into one of the
check outcomes of `records.CHECK_OUTCOMES`; an engine never decides that
nothing changed.

```text
knowledge_radar_source/v1
├── local engines (read files, no network)
│   ├── collector_state      the source discovery collector's latest private exports
│   ├── model_directory      the packaged model directory data of this repository
│   ├── mcp_directory        the packaged directory of protocol servers and agent APIs
│   └── curated_seed         official links a person declared in the question registry
└── network engines (bounded read-only requests, each under its source contract)
    ├── github_search        repository search through the gh login
    ├── github_advisories    the GitHub Advisory Database through the gh login
    ├── github_releases      the latest releases of named repositories
    ├── owner_directory      the owner's public directory repositories, parsed without running
    ├── huggingface_models   the Hugging Face Hub model listing
    ├── arxiv_listing        the arXiv query interface
    ├── openalex_works       the OpenAlex works listing
    ├── endoflife_calendar   the endoflife.date release and support calendar
    ├── federal_register     the FederalRegister.gov documents interface
    ├── huggingface_new_models  the newest model repositories of named publishers
    ├── models_dev_catalogue  models.dev (MIT): hosted models with capabilities, limits and prices
    └── litellm_prices       the LiteLLM price map (MIT): prices, limits and retirement dates
```

No engine reads OpenRouter or Artificial Analysis by script: their terms forbid it, and the source
contracts name them as hosts that are never read. They appear only as attributed links a customer opens.

An engine is an adapter the radar's Practitioner run uses. It is not a graph
vertex, a role, a mode or a runtime type, and it grants no authority: network
reads come from the run's grant and each engine's source contract.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from .records import Observation, RadarQuestion, SourceBinding, SourceContract

EDGE_VERSION = "knowledge_radar_source/v1"
OK, PARTIAL, FAILED, GONE, NOT_MODIFIED = "ok", "partial", "failed", "gone", "not_modified"
#: not_modified: the source answered 304 to the validators of the last complete read, so nothing changed.
ANSWER_STATUSES = (OK, PARTIAL, FAILED, GONE, NOT_MODIFIED)
MAXIMUM_TITLE = 200

# Source text that tries to steer a reader is data, never an instruction. The patterns are the
# review panel's own static safety rules, so an entry the panel would refuse never reaches a brief.
_STEERING = (
    re.compile(r"(?i)\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|all|any)\b"
               r"[^.\n]{0,20}\b(?:instructions?|prompts?|rules?|guidelines?)\b"),
    re.compile(r"(?i)\b(?:approve this (?:item|skill|file)|mark (?:it|this) (?:as )?approved|you are now in)\b"),
    re.compile(r"(?i)\b(?:curl|wget|fetch|iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z|k|c|da|fi)?sh\b"),
    re.compile(r"(?i)\brm\s+-[a-z]*r[a-z]*\s+(?:/|~|\$HOME)"),
    re.compile(r"(?i)(?:~/\.ssh/|\bid_(?:rsa|ed25519|ecdsa)\b|\.aws/credentials\b|/etc/shadow\b)"),
    re.compile(r"<!--"),
)
_MARKUP = re.compile(r"[`|<>\[\]\\*]")


class RadarEngineError(ValueError):
    """An engine refused its binding before reading anything, with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class ReadContext:
    """What one engine call may use: the question, the binding, the clock, the contract and the network."""

    question: RadarQuestion
    binding: SourceBinding
    observed_at: str
    today: str
    contract: SourceContract
    repository: object
    collector_state: object = None
    network: object = None


@dataclass(frozen=True)
class EngineAnswer:
    status: str
    reason: str
    observations: tuple = ()
    requests: int = 0
    guard_texts: tuple = ()
    excluded: tuple = ()
    #: False when the observations are not the whole current list (some scopes answered 304 or failed),
    #: so a missing entry must not be read as a removal.
    complete: bool = True


class RadarSourceEngine(Protocol):
    engine_id: str
    engine_version: str
    #: The facts whose change is material for this source; a ranking count is not one of them.
    material_facts: tuple

    def read(self, context: ReadContext) -> EngineAnswer: ...


def clean_title(value) -> "tuple[str, str]":
    """A one-line title with invisible and control characters removed, and the reason to exclude it, if any.

    A title that holds steering text or markup that could change how a brief renders is excluded, not
    rewritten: the radar never edits what a source said, it only declines to repeat it.
    """
    if not isinstance(value, str):
        return "", "the source gave no title"
    text = "".join(character for character in value
                   if unicodedata.category(character) not in ("Cc", "Cf") or character in " \t")
    text = " ".join(text.split())
    if not text:
        return "", "the source gave an empty title"
    for pattern in _STEERING:
        if pattern.search(text):
            return "", "the title holds text that tries to steer a reader, so it is kept out of the brief"
    text = _MARKUP.sub(" ", text)
    text = " ".join(text.split())
    if len(text) > MAXIMUM_TITLE:
        text = text[:MAXIMUM_TITLE - 3].rstrip() + "..."
    return text, ""


def number(value):
    """An int or float as given, or None; booleans and text are not numbers."""
    return value if type(value) in (int, float) else None


_TABLE_BREAKING = re.compile(r"[`|\\]")


def text_fact(value, limit: int = 120):
    """A short fact value with invisible characters removed. Comparison signs are kept: in a version
    range such as "< 1.7.4" they carry the meaning. Only characters that break a table are replaced."""
    if not isinstance(value, str):
        return None
    text = "".join(character for character in value
                   if unicodedata.category(character) not in ("Cc", "Cf") or character in " \t")
    text = " ".join(_TABLE_BREAKING.sub(" ", text).split())
    if not text or any(pattern.search(text) for pattern in _STEERING):
        return None
    return text[:limit]


def iso_time(value):
    """A day or a UTC second from a source timestamp, or None. Fractions and offsets are normalised to Z."""
    if not isinstance(value, str) or len(value) < 10:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    match = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", value)
    if not match:
        return value[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value[:10]) else None
    suffix = value[match.end():]
    if suffix and not re.fullmatch(r"(?:\.\d+)?(?:Z|[+-]00:?00)?", suffix):
        return match.group(1)
    return f"{match.group(1)}T{match.group(2)}Z"


_TIME_RANKS = ("event_at", "source_published_at", "effective_from", "effective_until")


def rank_value(item, rank_by: str):
    return getattr(item, rank_by) if rank_by in _TIME_RANKS else item.facts.get(rank_by)


def ranked(observations, rank_by: str, *, descending: bool = True) -> list:
    """Sort by one fact or time, entries without it last, ties in key order so every run orders the same way."""
    by_key = sorted(observations, key=lambda item: item.key)
    numeric = [item for item in by_key if type(rank_value(item, rank_by)) in (int, float)]
    textual = [item for item in by_key if isinstance(rank_value(item, rank_by), str)]
    absent = [item for item in by_key if item not in numeric and item not in textual]
    numeric.sort(key=lambda item: rank_value(item, rank_by), reverse=descending)
    textual.sort(key=lambda item: rank_value(item, rank_by), reverse=descending)
    return numeric + textual + absent


_VERIFIED_WHEN_READ = object()


def observation(context: ReadContext, engine, *, key: str, origin: str, title: str, url: str,
                source_address: str, facts=None, licence=None, licence_basis: str = "not stated by the source",
                event_at=None, source_published_at=None, effective_from=None, effective_until=None,
                observed_at=None, last_verified_at=_VERIFIED_WHEN_READ,
                claim_dated_by_source: bool = False) -> Observation:
    """One observation with the run's time fields filled by rule and nothing guessed.

    A claim read from its source is verified when it is read. A claim a person declared (a seed) is not
    verified by reading the registry, so its engine passes ``last_verified_at=None`` and only a later
    check of the link can fill it. The review date follows the evidence: it is counted from when the
    claim was last verified, or, for a claim the source itself dated, from that date when it is earlier.
    """
    seen = observed_at or context.observed_at
    verified = seen if last_verified_at is _VERIFIED_WHEN_READ else last_verified_at
    basis = verified or seen
    if claim_dated_by_source and source_published_at and source_published_at[:10] < basis[:10]:
        # Reading an old claim again today does not make it new: its review date counts from its own date.
        basis = source_published_at
    return Observation(
        key=key, origin=origin, title=title, url=url, engine_id=engine.engine_id,
        engine_version=engine.engine_version, section=context.binding.section, source_address=source_address,
        observed_at=seen, licence=licence, licence_basis=licence_basis,
        facts={name: item for name, item in (facts or {}).items() if item is not None},
        event_at=event_at, source_published_at=source_published_at, effective_from=effective_from,
        effective_until=effective_until, last_verified_at=verified,
        review_after=context.question.review_after(basis))


def parameter(context: ReadContext, name: str, default=None, *, kind=None, choices=None):
    value = context.binding.parameters.get(name, default)
    if kind is not None and value is not None and not isinstance(value, kind):
        raise RadarEngineError("radar_parameter_invalid", f"{context.binding.engine} parameter {name} has the wrong type")
    if choices is not None and value not in choices:
        raise RadarEngineError("radar_parameter_invalid", f"{context.binding.engine} parameter {name} is not one of {choices}")
    return value


def limit_of(context: ReadContext, maximum: int = 60) -> int:
    value = parameter(context, "limit", context.question.limit, kind=int)
    if not 1 <= value <= maximum:
        raise RadarEngineError("radar_parameter_invalid", f"limit is 1 to {maximum}")
    return value


@dataclass
class EngineRegistry:
    """The installed engines by identity. Selection is by the binding's engine name, one binding at a time."""

    engines: dict = field(default_factory=dict)

    def install(self, engine) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", getattr(engine, "engine_id", "")):
            raise RadarEngineError("radar_engine_invalid", "an engine needs a lowercase identity")
        if engine.engine_id in self.engines:
            raise RadarEngineError("radar_engine_duplicate", f"{engine.engine_id} is installed once")
        self.engines[engine.engine_id] = engine

    def engine(self, engine_id: str):
        engine = self.engines.get(engine_id)
        if engine is None:
            raise RadarEngineError("radar_engine_not_installed", f"{engine_id} is not installed in this run")
        return engine


def default_registry(*, network_allowed: bool) -> EngineRegistry:
    """Every Baltor-native engine. Network engines are installed only when the run holds network authority."""
    from . import engines_local, engines_network
    registry = EngineRegistry()
    for engine in engines_local.ENGINES:
        registry.install(engine)
    if network_allowed:
        for engine in engines_network.ENGINES:
            registry.install(engine)
    return registry
