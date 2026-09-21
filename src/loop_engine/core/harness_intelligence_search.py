"""How a customer's words are compared with the catalogue, declared not implied.

A customer's coding tool asks for what one step needs and gets back a few
references. If the wrong three come back, everything after them is worse. This
module owns the one decision that settles which three: how the words in the
request are compared with the words an item declares.

WHY THIS IS A CONTRACT AND NOT A HELPER
The September 18 rule in this repository is that every contract names its
matching mode, because exact everywhere is brittle and loose everywhere is
unsafe. Search was the one comparison in the product that never named its
mode: the behaviour lived in the argument defaults of a retrieval call, so
nobody could state it, change it or measure it. Here the mode is a typed
field drawn from the same five modes as every other contract
(``core.contract_matching``), and the fields the search is allowed to read are
a typed list with a weight each.

```text
Catalogue search policy
├── Match mode, strict to open
│   ├── exact             the words meet letter for letter, case included
│   ├── canonical         lower case, straight quotes, single spaces
│   ├── purpose           canonical, plus one general spelling and plural fold,
│   │                     so words that serve the same purpose meet
│   ├── semantic_blocked  purpose, with declared tag dimensions equal exactly
│   │                     and a coverage floor below which nothing is returned
│   └── model_judged      beyond deterministic reach; names the judgment
│                         contract a separate step must answer, and ranks nothing
├── Fields read, each with a weight
│   └── identity, purpose, kind, source_layer, tags, styles
├── Retrieval mode: lexical, vector or hybrid
├── Common term ceiling: a word most of the catalogue holds separates nothing
└── Coverage floor: how much of the request an item must actually hold
```

A policy grants nothing. It never loads a body, never changes an item and
never decides that an item may be disclosed; ``core.provisioning_server``
still settles that. This module only orders the references a caller is already
allowed to see.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .contract_matching import (CANONICAL, EXACT, MATCH_MODES, MODEL_JUDGED, PURPOSE,
                                SEMANTIC_BLOCKED, canonical_text)
from .harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceItem
from .intelligence_tagging import TAG_DIMENSIONS, TagSet

POLICY_RECORD_TYPE = "harness_intelligence_search_policy/v1"
RESULT_RECORD_TYPE = "harness_intelligence_search_result/v1"
#: The declared fields of an item that a search may read. A field that is not
#: here is not searchable, and a body is never one of them.
SEARCHABLE_FIELDS = ("identity", "purpose", "kind", "source_layer", "tags", "styles")
#: Which engines may run behind the policy, named so a change is visible.
RETRIEVAL_MODES = ("lexical", "vector", "hybrid")
#: A weight counts how many times a field's words enter the index. Zero means
#: the field was considered and is deliberately not read.
MAXIMUM_FIELD_WEIGHT = 8

_EXACT_TOKEN = re.compile(r"[A-Za-z0-9]+")
_TOKEN = re.compile(r"[a-z0-9]+")
#: Exact mode writes the case pattern into the token, because a lexical index
#: folds case on its own: ``Inc`` becomes ``incxull`` and ``inc`` becomes
#: ``incxlll``, so two spellings that differ only in case never meet.
_CASE_MARK = "x"
#: One spelling of a word, written as an ending rewrite with its own shortest
#: length. These are spelling rules, never a list of words, so a word this
#: session never saw is folded the same way.
_SPELLING = (("isations", "izations", 8), ("isation", "ization", 7),
             ("ising", "izing", 6), ("ised", "ized", 5), ("ises", "izes", 6),
             ("isable", "izable", 7), ("ise", "ize", 5),
             ("ysing", "yzing", 6), ("ysed", "yzed", 5), ("yses", "yzes", 6),
             ("yse", "yze", 5), ("ogue", "og", 6), ("tre", "ter", 5),
             ("our", "or", 6))
#: The whole -ize family folded to one stem, so normalize, normalise,
#: normalizing and normalisation all meet.
_IZE = (("izations", "iz"), ("ization", "iz"), ("izing", "iz"), ("ized", "iz"),
        ("izes", "iz"), ("ize", "iz"))
#: One of a thing and many of it are the same thing.
_PLURAL = (("ies", "y", 5), ("sses", "ss", 5), ("ches", "ch", 5), ("shes", "sh", 5),
           ("xes", "x", 4), ("zes", "z", 4))
_VOWELS = frozenset("aeiouy")
#: An ending that is not a plural even though it looks like one.
_NOT_PLURAL = ("ss", "us", "is")
_MINIMUM_PLURAL = 4


class CatalogueSearchError(ValueError):
    """A search policy is invalid, or a policy cannot rank in the mode it names."""


def _fold(token: str) -> str:
    """One general spelling and plural fold, applied to the request and the item alike."""
    for suffix, replacement, shortest in _SPELLING:
        if len(token) >= shortest and token.endswith(suffix):
            token = token[:len(token) - len(suffix)] + replacement
            break
    for suffix, replacement in _IZE:
        if len(token) > len(suffix) and token.endswith(suffix):
            return token[:len(token) - len(suffix)] + replacement
    for suffix, replacement, shortest in _PLURAL:
        if len(token) >= shortest and token.endswith(suffix):
            return token[:len(token) - len(suffix)] + replacement
    if (len(token) >= _MINIMUM_PLURAL and token.endswith("s")
            and not token.endswith(_NOT_PLURAL) and set(token[:-1]) & _VOWELS):
        return token[:-1]
    return token


def match_tokens(text: object, match_mode: str) -> tuple[str, ...]:
    """The words one mode compares. The request and the item are always read the same way."""
    if match_mode not in MATCH_MODES:
        raise CatalogueSearchError(f"match mode must be one of {MATCH_MODES}")
    if match_mode == EXACT:
        return tuple(token.lower() + _CASE_MARK
                     + "".join("u" if letter.isupper() else "l" for letter in token)
                     for token in _EXACT_TOKEN.findall(str(text or "")))
    plain = tuple(_TOKEN.findall(canonical_text(str(text or ""))))
    return plain if match_mode == CANONICAL else tuple(_fold(token) for token in plain)


@dataclass(frozen=True)
class CatalogueSearchField:
    """One declared field of an item and how much of the index it occupies."""

    name: str
    weight: int = 1

    def __post_init__(self) -> None:
        if self.name not in SEARCHABLE_FIELDS:
            raise CatalogueSearchError(
                f"{self.name!r} is not one of the searchable fields {SEARCHABLE_FIELDS}")
        if (type(self.weight) is not int or self.weight < 0
                or self.weight > MAXIMUM_FIELD_WEIGHT):
            raise CatalogueSearchError(
                f"a field weight is a whole number from 0 to {MAXIMUM_FIELD_WEIGHT}; "
                "zero records that the field was considered and is not read")

    def to_dict(self) -> dict:
        return {"name": self.name, "weight": self.weight}


@dataclass(frozen=True)
class CatalogueSearchPolicy:
    """The declared way a request is compared with the catalogue."""

    match_mode: str
    fields: tuple[CatalogueSearchField, ...]
    retrieval_mode: str = RETRIEVAL_MODES[0]
    lexical_backend: str = "fts5"
    #: A word that more than this share of the catalogue holds separates nothing.
    #: One means every word of the request is read, which is the safe default.
    common_term_ceiling: float = 1.0
    #: Tag dimensions that must be equal exactly before any ranking, in the one
    #: mode that declares blocking keys.
    blocking_dimensions: tuple[str, ...] = ()
    #: The share of the request's words an item must hold to be returned at all.
    coverage_floor: float = 0.0
    judge_contract_id: str = ""
    record_type: str = POLICY_RECORD_TYPE

    def __post_init__(self) -> None:
        if self.record_type != POLICY_RECORD_TYPE:
            raise CatalogueSearchError("unsupported search policy contract version")
        if self.match_mode not in MATCH_MODES:
            raise CatalogueSearchError(f"match mode must be one of {MATCH_MODES}")
        if self.retrieval_mode not in RETRIEVAL_MODES:
            raise CatalogueSearchError(f"retrieval mode must be one of {RETRIEVAL_MODES}")
        fields = tuple(self.fields)
        if not fields or any(not isinstance(item, CatalogueSearchField) for item in fields):
            raise CatalogueSearchError("a policy names its searchable fields as typed fields")
        names = [item.name for item in fields]
        if len(set(names)) != len(names):
            raise CatalogueSearchError("each searchable field is named once")
        if not any(item.weight for item in fields):
            raise CatalogueSearchError("a search that reads no field can rank nothing")
        object.__setattr__(self, "fields", fields)
        for name in ("common_term_ceiling", "coverage_floor"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not 0 <= value <= 1:
                raise CatalogueSearchError(f"{name} is a share from 0 to 1")
        if self.common_term_ceiling == 0:
            raise CatalogueSearchError(
                "a ceiling of zero would discard every word of the request")
        dimensions = tuple(self.blocking_dimensions)
        object.__setattr__(self, "blocking_dimensions", dimensions)
        unknown = [name for name in dimensions if name not in TAG_DIMENSIONS]
        if unknown:
            raise CatalogueSearchError(f"{unknown} is not drawn from {TAG_DIMENSIONS}")
        if self.match_mode == SEMANTIC_BLOCKED and (not dimensions or self.coverage_floor <= 0):
            raise CatalogueSearchError(
                "a semantic match declares its blocking dimensions and a coverage floor above 0")
        if self.match_mode != SEMANTIC_BLOCKED and dimensions:
            raise CatalogueSearchError("blocking dimensions belong to a semantic match")
        if self.match_mode == MODEL_JUDGED and not self.judge_contract_id.strip():
            raise CatalogueSearchError("a model judged search names the judgment contract it needs")
        if self.match_mode != MODEL_JUDGED and self.judge_contract_id:
            raise CatalogueSearchError("only a model judged search names a judgment contract")

    def weight_of(self, name: str) -> int:
        """How many times a field's words enter the index; zero when it is not read."""
        if name not in SEARCHABLE_FIELDS:
            raise CatalogueSearchError(f"{name!r} is not a searchable field")
        return next((item.weight for item in self.fields if item.name == name), 0)

    @property
    def fields_read(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields if item.weight)

    def to_dict(self) -> dict:
        return {"record_type": self.record_type, "match_mode": self.match_mode,
                "fields": [item.to_dict() for item in self.fields],
                "retrieval_mode": self.retrieval_mode, "lexical_backend": self.lexical_backend,
                "common_term_ceiling": self.common_term_ceiling,
                "blocking_dimensions": list(self.blocking_dimensions),
                "coverage_floor": self.coverage_floor,
                "judge_contract_id": self.judge_contract_id}


def _field_text(item: HarnessIntelligenceItem, name: str) -> str:
    if name == "identity":
        return item.identity.replace("_", " ")
    if name == "purpose":
        return item.purpose
    if name == "kind":
        return item.kind
    if name == "source_layer":
        return item.source_layer
    if name == "styles":
        return " ".join(item.styles)
    return " ".join(value for dimension in item.tags.declared_dimensions
                    for value in item.tags.on(dimension))


def item_search_tokens(item: HarnessIntelligenceItem,
                       policy: CatalogueSearchPolicy) -> tuple[str, ...]:
    """The words one item offers the search, from its declared fields only."""
    if not isinstance(item, HarnessIntelligenceItem):
        raise CatalogueSearchError("a typed catalogue item is required")
    if not isinstance(policy, CatalogueSearchPolicy):
        raise CatalogueSearchError("a typed search policy is required")
    words: list[str] = []
    for entry in policy.fields:
        if entry.weight:
            words.extend(match_tokens(_field_text(item, entry.name), policy.match_mode)
                         * entry.weight)
    return tuple(words)


def request_tokens(query: str, policy: CatalogueSearchPolicy,
                   held_by: "dict | None" = None, catalogue_size: int = 0) -> tuple[str, ...]:
    """The words of the request the policy reads, in the policy's own mode.

    ``held_by`` counts how many items hold each word. A word that more of the
    catalogue holds than the declared ceiling separates nothing, so it is left
    out, unless every word of the request is that common, in which case the
    request is read whole rather than answered with silence.
    """
    if not isinstance(policy, CatalogueSearchPolicy):
        raise CatalogueSearchError("a typed search policy is required")
    words = match_tokens(query, policy.match_mode)
    if policy.common_term_ceiling >= 1 or not held_by or catalogue_size <= 0:
        return words
    ceiling = policy.common_term_ceiling * catalogue_size
    kept = tuple(word for word in words if held_by.get(word, 0) <= ceiling)
    return kept or words


def token_coverage(request: "tuple[str, ...]", held: "tuple[str, ...]") -> float:
    """The share of the request's distinct words an item's declared fields hold."""
    wanted = set(request)
    if not wanted:
        return 0.0
    return len(wanted & set(held)) / len(wanted)


def _items_of(catalogue) -> tuple[HarnessIntelligenceItem, ...]:
    values = (catalogue.items.values() if isinstance(catalogue, HarnessIntelligenceCatalogue)
              else catalogue)
    items = tuple(values)
    if any(not isinstance(item, HarnessIntelligenceItem) for item in items):
        raise CatalogueSearchError("only typed catalogue items can be searched")
    return items


class PreparedCatalogueSearch:
    """One policy's reading of one set of items, built once and asked many times.

    Reading every item and building the engine index again for every request is
    the same work repeated: a hosted service answers thousands of requests
    against a catalogue that changed for none of them. The blocking decision
    belongs to the preparation because it happens before anything is ranked, so
    a prepared search is bound to the exact tag request it was prepared for and
    refuses any other.
    """

    def __init__(self, catalogue, policy: CatalogueSearchPolicy, *,
                 request_tags: "TagSet | None" = None) -> None:
        if not isinstance(policy, CatalogueSearchPolicy):
            raise CatalogueSearchError("a typed search policy is required")
        if policy.match_mode == MODEL_JUDGED:
            raise CatalogueSearchError(
                "a model judged search ranks nothing on its own; the judgment contract "
                f"{policy.judge_contract_id!r} must answer it in a separate step")
        wanted = request_tags if request_tags is not None else TagSet({})
        if not isinstance(wanted, TagSet):
            raise CatalogueSearchError("a tag request must be a typed tag set")
        self.policy = policy
        self.request_tags = wanted
        self.blocked: list = []
        eligible: list = []
        for item in _items_of(catalogue):
            # An item that declares nothing on a dimension is general, exactly
            # as ``TagSet.matches`` already reads it for disclosure in
            # ``core.harness_intelligence.visibility``. Two different answers to
            # "do these tags satisfy this request" inside one product is a
            # defect, so ranking reads the dimension the same way access does.
            differing = [dimension for dimension in policy.blocking_dimensions
                         if set(wanted.on(dimension)) and set(item.tags.on(dimension))
                         and not set(item.tags.on(dimension)) & set(wanted.on(dimension))]
            if differing:
                self.blocked.append({"identity": item.identity, "dimensions": differing})
            else:
                eligible.append(item)
        self.eligible = tuple(eligible)
        self.held = {item.identity: item_search_tokens(item, policy) for item in self.eligible}
        self.held_by: dict = {}
        for words in self.held.values():
            for word in set(words):
                self.held_by[word] = self.held_by.get(word, 0) + 1
        self._by_identity = {item.identity: item for item in self.eligible}
        self._engine = None

    def _ranked(self, request: "tuple[str, ...]", top_n: int) -> list:
        from .retrieval import Retriever
        from .store_serve import StoreRecord
        if self._engine is None:
            records = [StoreRecord(identity, "context", " ".join(words), body={})
                       for identity, words in self.held.items() if words]
            self._engine = (Retriever(records, lexical_backend=self.policy.lexical_backend)
                            if records else False)
        if self._engine is False or not request:
            return []
        result = self._engine.search(" ".join(request), mode=self.policy.retrieval_mode,
                                     top_n=top_n)
        return [(hit["record_id"], hit["rrf"], list(hit["modes"])) for hit in result["hits"]]

    def search(self, query: str, *, top_n: int = 10) -> dict:
        """Order the eligible references the way the policy declares.

        ``top_n`` bounds the window the engine ranks, and a declared coverage
        floor then removes items inside that window. So a policy with a floor
        can return fewer than ``top_n`` hits while items further down would
        have passed the floor. The items removed are named in
        ``withheld_below_floor`` rather than dropped silently.
        """
        if type(top_n) is not int or top_n < 1:
            raise CatalogueSearchError("top_n must be a positive whole number")
        if not isinstance(query, str) or not query.strip():
            raise CatalogueSearchError("a search needs a request in words")
        policy = self.policy
        request = request_tokens(query, policy, self.held_by, len(self.eligible))
        hits, withheld = [], []
        for identity, score, modes in self._ranked(request, top_n):
            share = token_coverage(request, self.held[identity])
            if share < policy.coverage_floor:
                withheld.append({"identity": identity, "coverage": round(share, 4),
                                 "reason": "below the declared coverage floor"})
                continue
            hits.append({"identity": identity, "rank": len(hits) + 1,
                         "coverage": round(share, 4), "rank_score": score, "modes": modes,
                         "reference": self._by_identity[identity].reference()})
        return {"record_type": RESULT_RECORD_TYPE, "query": query,
                "policy": policy.to_dict(), "match_mode": policy.match_mode,
                "retrieval_mode": policy.retrieval_mode,
                "fields_read": list(policy.fields_read),
                "request_terms": list(request), "considered": len(self.eligible),
                "blocked_by_tags": list(self.blocked), "withheld_below_floor": withheld,
                "hits": hits, "body_included": False}


def catalogue_search(catalogue, query: str, policy: CatalogueSearchPolicy, *,
                     top_n: int = 10, request_tags: "TagSet | None" = None,
                     prepared: "PreparedCatalogueSearch | None" = None) -> dict:
    """Order the references a caller may already see, the way the policy declares.

    Nothing here grants access, loads a body or changes an item: the caller
    supplies the items it is allowed to see and gets the same items back in an
    order, each hit naming the mode that surfaced it. Supplying ``prepared``
    reuses an index already built for this exact policy and tag request; a
    prepared search built for anything else is refused rather than reused.
    """
    if prepared is None:
        prepared = PreparedCatalogueSearch(catalogue, policy, request_tags=request_tags)
    elif not isinstance(prepared, PreparedCatalogueSearch):
        raise CatalogueSearchError("a prepared search must be the typed prepared object")
    elif prepared.policy != policy or prepared.request_tags != (
            request_tags if request_tags is not None else TagSet({})):
        raise CatalogueSearchError(
            "the prepared search was built for a different policy or tag request; "
            "prepare one for this request rather than reusing another one's index")
    return prepared.search(query, top_n=top_n)


def _fields(**weights) -> tuple[CatalogueSearchField, ...]:
    return tuple(CatalogueSearchField(name, weights.get(name, 0)) for name in SEARCHABLE_FIELDS)


#: What the hosted service did before this module existed, kept by name so the
#: comparison stays reproducible rather than remembered. It reads the purpose
#: twice, because the same sentence was both the title and the description of
#: the record it built, and it folds only case, quotes and spacing.
SERVED_BEFORE_2026_09_21 = CatalogueSearchPolicy(
    CANONICAL, _fields(purpose=2, identity=1, kind=1, source_layer=1))
#: The measured default, reported in
#: docs/components/intelligence-layers/SEARCH-QUALITY.md against 354 queries
#: over the 123 item starter catalogue. Two findings decided it. The spelling
#: and plural fold gained more on the 93 queries held back than on the 261 it
#: was chosen from, so the gain is not a fit to the development set. The other
#: four searchable fields were measured and read nothing useful: the declared
#: tags, the kind and the source layer are the same words on every item of this
#: catalogue, and a field every item answers the same way separates nothing. A
#: weight of zero records that the field was considered, so re-measure when the
#: catalogue carries tags that differ between items.
DEFAULT_SEARCH_POLICY = CatalogueSearchPolicy(
    PURPOSE, _fields(purpose=2, identity=1))


def self_test() -> dict:
    """The mode is declared, the request and the item are read alike, and a looser mode never widens authority."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except CatalogueSearchError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    from .harness_intelligence import HarnessIntelligenceDraft, item_from_body
    def make(identity, purpose, tags=None, styles=(), effects=()):
        return item_from_body(HarnessIntelligenceDraft(
            identity, "skill", purpose, "context_intelligence", f"ctx.{identity}", "MIT",
            tuple(effects), tuple(styles), tags=TagSet(tags or {})), f"# {identity}\n")

    catalogue = HarnessIntelligenceCatalogue()
    for item in (
            make("normalize_phone_numbers", "Normalize phone numbers to an international form",
                 {"domain": ("data cleaning", "contact records")}),
            make("audit_data_splits", "Audit training and test splits for leakage",
                 {"domain": ("model evaluation",)}),
            make("intake_questions_de", "Intake questions for a nurse",
                 {"language": ("de",), "role": ("nurse",)}),
            make("intake_questions_en", "Intake questions for a nurse",
                 {"language": ("en",), "role": ("nurse",)})):
        catalogue.register(item)

    check("a_policy_names_its_match_mode_and_the_fields_it_reads",
          DEFAULT_SEARCH_POLICY.to_dict()["match_mode"] == PURPOSE
          and DEFAULT_SEARCH_POLICY.fields_read == ("identity", "purpose")
          and DEFAULT_SEARCH_POLICY.weight_of("source_layer") == 0
          and DEFAULT_SEARCH_POLICY.weight_of("tags") == 0
          and DEFAULT_SEARCH_POLICY.weight_of("purpose") == 2
          and SERVED_BEFORE_2026_09_21.match_mode == CANONICAL
          and refuses(lambda: CatalogueSearchPolicy("fuzzy", _fields(purpose=1)))
          and refuses(lambda: CatalogueSearchPolicy(CANONICAL, ()))
          and refuses(lambda: CatalogueSearchPolicy(CANONICAL, _fields()))
          and refuses(lambda: CatalogueSearchPolicy(CANONICAL, (CatalogueSearchField("body", 1),)))
          and refuses(lambda: CatalogueSearchPolicy(
              CANONICAL, (CatalogueSearchField("purpose", 1), CatalogueSearchField("purpose", 2))))
          and refuses(lambda: CatalogueSearchPolicy(CANONICAL, _fields(purpose=1), retrieval_mode="magic"))
          and refuses(lambda: CatalogueSearchField("purpose", -1))
          and refuses(lambda: CatalogueSearchPolicy(
              CANONICAL, _fields(purpose=1), record_type=POLICY_RECORD_TYPE + "x")),
          str(DEFAULT_SEARCH_POLICY.fields_read))

    exact = CatalogueSearchPolicy(EXACT, _fields(purpose=1))
    canonical = CatalogueSearchPolicy(CANONICAL, _fields(purpose=1))
    purpose = CatalogueSearchPolicy(PURPOSE, _fields(purpose=1))
    check("each_mode_reads_the_request_and_the_item_the_same_way",
          match_tokens("Inc", EXACT) == ("incxull",)
          and match_tokens("inc", EXACT) == ("incxlll",)
          and match_tokens("Inc", EXACT) != match_tokens("inc", EXACT)
          and match_tokens("Inc", CANONICAL) == match_tokens("inc", CANONICAL)
          and match_tokens("normalise", PURPOSE) == match_tokens("normalizing", PURPOSE)
          == match_tokens("Normalisation", PURPOSE) == ("normaliz",)
          and match_tokens("splits", PURPOSE) == match_tokens("split", PURPOSE)
          and match_tokens("queries", PURPOSE) == match_tokens("query", PURPOSE)
          and match_tokens("analysis", PURPOSE) == ("analysis",)
          and match_tokens("splits", CANONICAL) != match_tokens("split", CANONICAL)
          and refuses(lambda: match_tokens("x", "fuzzy")),
          str(match_tokens("Normalisation", PURPOSE)))

    # The known-wrong case for the fold, with one word in the request so that
    # the fold is the only thing that can make the two sides meet. A request
    # with a second word the item already holds would pass in every mode and
    # would prove nothing about folding.
    canonical_hits = [hit["identity"] for hit in catalogue_search(
        catalogue, "normalising", canonical, top_n=3)["hits"]]
    purpose_hits = [hit["identity"] for hit in catalogue_search(
        catalogue, "normalising", purpose, top_n=3)["hits"]]
    check("a_spelling_a_customer_really_types_is_found_only_in_the_purpose_mode",
          canonical_hits == [] and purpose_hits[:1] == ["normalize_phone_numbers"],
          f"canonical {canonical_hits} against purpose {purpose_hits}")

    # One word again, so case is the only difference between the two requests.
    check("an_exact_search_refuses_a_spelling_that_differs_only_in_case",
          [hit["identity"] for hit in catalogue_search(
              catalogue, "normalize", exact, top_n=3)["hits"]] == []
          and [hit["identity"] for hit in catalogue_search(
              catalogue, "Normalize", exact, top_n=3)["hits"]][:1]
          == ["normalize_phone_numbers"]
          and [hit["identity"] for hit in catalogue_search(
              catalogue, "normalize", canonical, top_n=3)["hits"]][:1]
          == ["normalize_phone_numbers"])

    tagged = CatalogueSearchPolicy(SEMANTIC_BLOCKED, _fields(purpose=1, tags=1),
                                   blocking_dimensions=("language",), coverage_floor=0.5)
    german = catalogue_search(catalogue, "intake questions for a nurse", tagged,
                              top_n=5, request_tags=TagSet({"language": ("de",)}))
    check("a_blocking_dimension_is_equal_exactly_before_anything_is_ranked",
          [hit["identity"] for hit in german["hits"]] == ["intake_questions_de"]
          and [row["identity"] for row in german["blocked_by_tags"]] == ["intake_questions_en"]
          and german["blocked_by_tags"][0]["dimensions"] == ["language"]
          and refuses(lambda: CatalogueSearchPolicy(SEMANTIC_BLOCKED, _fields(purpose=1),
                                                    coverage_floor=0.5))
          and refuses(lambda: CatalogueSearchPolicy(SEMANTIC_BLOCKED, _fields(purpose=1),
                                                    blocking_dimensions=("language",)))
          and refuses(lambda: CatalogueSearchPolicy(PURPOSE, _fields(purpose=1),
                                                    blocking_dimensions=("language",)))
          and refuses(lambda: CatalogueSearchPolicy(SEMANTIC_BLOCKED, _fields(purpose=1),
                                                    blocking_dimensions=("topic",), coverage_floor=0.5))
          and refuses(lambda: catalogue_search(catalogue, "x", tagged, request_tags={"language": ("de",)})),
          str([hit["identity"] for hit in german["hits"]]))

    floored = CatalogueSearchPolicy(PURPOSE, _fields(purpose=1), coverage_floor=0.6)
    unanswerable = catalogue_search(catalogue, "book a meeting room for tomorrow", floored, top_n=5)
    answerable = catalogue_search(catalogue, "audit training and test splits", floored, top_n=5)
    check("a_request_this_catalogue_cannot_answer_is_not_answered_confidently",
          unanswerable["hits"] == [] and unanswerable["withheld_below_floor"]
          and answerable["hits"][0]["identity"] == "audit_data_splits"
          and answerable["hits"][0]["coverage"] >= 0.6
          and catalogue_search(catalogue, "book a meeting room for tomorrow",
                               purpose, top_n=5)["hits"],
          f"{len(unanswerable['withheld_below_floor'])} withheld below the floor")

    # A separate small catalogue, because the rule is about how many items hold
    # a word: with three items and a ceiling of one half, a word all three hold
    # separates nothing and a word one holds still does.
    crowded = HarnessIntelligenceCatalogue()
    for item in (make("intake_questions_nurse", "Intake questions for a nurse"),
                 make("survey_questions_patient", "Survey questions for a patient"),
                 make("screening_questions_clinic", "Screening questions for a clinic")):
        crowded.register(item)
    common = CatalogueSearchPolicy(PURPOSE, _fields(purpose=1), common_term_ceiling=0.5)
    narrowed = catalogue_search(crowded, "intake questions for a nurse", common, top_n=5)
    every_word_common = catalogue_search(crowded, "questions for a", common, top_n=5)
    check("a_word_most_of_the_catalogue_holds_is_left_out_but_never_all_of_them",
          "question" not in narrowed["request_terms"]
          and "intake" in narrowed["request_terms"]
          and narrowed["hits"][0]["identity"] == "intake_questions_nurse"
          and "question" in every_word_common["request_terms"]
          and every_word_common["hits"]
          and refuses(lambda: CatalogueSearchPolicy(PURPOSE, _fields(purpose=1),
                                                    common_term_ceiling=0)),
          str(narrowed["request_terms"]))

    judged = CatalogueSearchPolicy(MODEL_JUDGED, _fields(purpose=1),
                                   judge_contract_id="independent.catalogue_relevance")
    check("a_model_judged_search_ranks_nothing_and_names_its_judgment_contract",
          judged.to_dict()["judge_contract_id"] == "independent.catalogue_relevance"
          and refuses(lambda: catalogue_search(catalogue, "anything", judged))
          and refuses(lambda: CatalogueSearchPolicy(MODEL_JUDGED, _fields(purpose=1)))
          and refuses(lambda: CatalogueSearchPolicy(PURPOSE, _fields(purpose=1),
                                                    judge_contract_id="x")))

    result = catalogue_search(catalogue, "phone numbers", DEFAULT_SEARCH_POLICY, top_n=2)
    check("a_hit_names_its_mode_and_carries_a_reference_without_a_body",
          result["hits"] and result["hits"][0]["modes"] == ["lexical"]
          and result["hits"][0]["reference"]["body_included"] is False
          and "body" not in result["hits"][0]["reference"]
          and result["body_included"] is False
          and result["match_mode"] == PURPOSE and result["considered"] == 4
          and [hit["rank"] for hit in result["hits"]] == list(
              range(1, len(result["hits"]) + 1))
          and refuses(lambda: catalogue_search(catalogue, "  ", DEFAULT_SEARCH_POLICY))
          and refuses(lambda: catalogue_search(catalogue, "x", DEFAULT_SEARCH_POLICY, top_n=0))
          and refuses(lambda: catalogue_search(catalogue, "x", "not a policy"))
          and refuses(lambda: catalogue_search([object()], "x", DEFAULT_SEARCH_POLICY))
          and refuses(lambda: item_search_tokens(object(), DEFAULT_SEARCH_POLICY)),
          str([hit["identity"] for hit in result["hits"]]))

    prepared = PreparedCatalogueSearch(catalogue, DEFAULT_SEARCH_POLICY)
    check("a_prepared_search_answers_exactly_as_an_unprepared_one_and_refuses_another_policy",
          [hit["identity"] for hit in prepared.search("phone numbers", top_n=2)["hits"]]
          == [hit["identity"] for hit in result["hits"]]
          and catalogue_search(catalogue, "phone numbers", DEFAULT_SEARCH_POLICY,
                               top_n=2, prepared=prepared)["hits"] == result["hits"]
          # The known-wrong case: an index built for one policy or one tag
          # request would silently answer for another without this refusal.
          and refuses(lambda: catalogue_search(catalogue, "phone numbers", canonical,
                                               prepared=prepared))
          and refuses(lambda: catalogue_search(
              catalogue, "phone numbers", DEFAULT_SEARCH_POLICY, prepared=prepared,
              request_tags=TagSet({"language": ("de",)})))
          and refuses(lambda: catalogue_search(catalogue, "phone numbers",
                                               DEFAULT_SEARCH_POLICY, prepared=object()))
          and refuses(lambda: PreparedCatalogueSearch(catalogue, judged))
          and refuses(lambda: PreparedCatalogueSearch(catalogue, DEFAULT_SEARCH_POLICY,
                                                      request_tags={"language": ("de",)}))
          and refuses(lambda: prepared.search("  "))
          and refuses(lambda: prepared.search("phone", top_n=0)),
          str([hit["identity"] for hit in prepared.search("phone numbers", top_n=2)["hits"]]))

    reads_tags = CatalogueSearchPolicy(PURPOSE, _fields(purpose=2, identity=1, tags=2))
    check("declared_tags_reach_the_index_only_when_the_policy_reads_them",
          "cleaning" in item_search_tokens(
              catalogue.items["normalize_phone_numbers"], reads_tags)
          and "cleaning" not in item_search_tokens(
              catalogue.items["normalize_phone_numbers"], DEFAULT_SEARCH_POLICY)
          and "cleaning" not in item_search_tokens(
              catalogue.items["normalize_phone_numbers"], SERVED_BEFORE_2026_09_21)
          and item_search_tokens(catalogue.items["normalize_phone_numbers"],
                                 SERVED_BEFORE_2026_09_21).count("phone") == 3
          and token_coverage(("a", "b"), ("b", "c")) == 0.5
          and token_coverage((), ("b",)) == 0.0)

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "harness_intelligence_search_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
