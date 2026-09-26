"""Facet tags: the job titles, industries, levels, languages and geographies an item names, as five served attributes.

The owner, September 26, 2026: "tag/label our harness component files by
job title, industry, level, language, geography, etc, and allow people to
search in the dashboard (when they sign up not on the home pages)". A tag
answers one of those questions for one item, so a signed-in customer can
filter the library by the work the item is for (roadmap S-6.209).

```text
library_facet_tagging (engine slot, one_of)
├── edge: tag(facet_material/v1) -> facet_tags/v1
├── facet_rules: phrase rules over a declared vocabulary, no model, no network
│   ├── job_titles    the pinned occupation grid and the packaged occupation seeds
│   ├── industries    a declared list of thirty-four, written as data
│   ├── levels        student, junior, mid, senior, lead, executive
│   ├── languages     english by default; twelve languages by script or stopwords
│   └── geographies   countries and regions from a declared list
└── a text model engine may follow behind the same edge; the tags record
    which engine wrote them, so a rule tag is never mistaken for a judged one
```

This is the second rules engine of the library, beside the step function
tagger and behind its own slot: the step function edge keeps its request and
result records unchanged, and a facet result is five attributes, not one. The
vocabulary is data (data/library_facets.yaml), so every value is a stable word
a filter can name. An item whose words name nothing gets no value for that
facet, which is the honest answer, not a guess. A tag is descriptive only: it
grants nothing, and no code that decides access reads it.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from .record_rules import LibraryRecordError, read_record

MATERIAL_RECORD_TYPE = "facet_material/v1"
TAGS_RECORD_TYPE = "facet_tags/v1"
VOCABULARY_RECORD_TYPE = "library_facet_vocabulary/v1"
VOCABULARY_FILE = Path(__file__).resolve().parents[2] / "data" / "library_facets.yaml"
#: The five facets, each the name of the served keyword_list attribute it fills, in the order the tags list them.
FACETS = ("job_titles", "industries", "levels", "languages", "geographies")
JOB_TITLES, INDUSTRIES, LEVELS, LANGUAGES, GEOGRAPHIES = FACETS
PHRASE_FACETS = (JOB_TITLES, INDUSTRIES, LEVELS, GEOGRAPHIES)
MAXIMUM_VALUES = {JOB_TITLES: 6, INDUSTRIES: 4, LEVELS: 3, LANGUAGES: 2, GEOGRAPHIES: 6}
#: A served keyword is bounded printable text of this length (catalogue_schema restates the same bound).
VALUE_BOUND = 120
TEXT_BOUND = 6000
NAME_BOUND = 256
PURPOSE_BOUND = 2048
#: A value is tagged when the name or purpose names it, or when the body names it by at least this many
#: distinct phrases, a singular and its plural counting once. A hand check of 100 tags on September 26, 2026
#: found body-only tags wrong 19 of 49 times, mostly one word said twice in a long body ("vehicle" in a
#: planning framework, "doctor" as a command name), while 11 of the 14 correct ones named two distinct phrases.
MINIMUM_BODY_PHRASES = 2
#: The score ranks the values of one facet: a mention in the name or purpose weighs two, one in the body one,
#: each place capped at two mentions.
HEADLINE_WEIGHT = 2
MENTION_CAP = 2
#: The language rules. A Latin-script language needs this many stopword hits and this share of the Latin
#: words; a script language needs this share of the letters; kana at this share says Japanese rather than
#: Chinese; the default applies only to a text whose letters are mostly Latin.
DEFAULT_LANGUAGE = "english"
MINIMUM_STOPWORD_HITS = 12
MINIMUM_STOPWORD_SHARE = 0.10
MINIMUM_SCRIPT_SHARE = 0.15
MINIMUM_KANA_SHARE = 0.02
LATIN_MAJORITY = 0.5
#: The scripts a language entry may name, with the code point ranges that count as its letters.
SCRIPT_RANGES = {
    "latin": ((0x0041, 0x024F), (0x1E00, 0x1EFF)),
    "han": ((0x4E00, 0x9FFF), (0x3400, 0x4DBF)),
    "kana": ((0x3040, 0x30FF),),
    "hangul": ((0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)),
    "cyrillic": ((0x0400, 0x04FF),),
    "arabic": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "devanagari": ((0x0900, 0x097F),),
}
#: Letters that mark Ukrainian or Belarusian rather than Russian, and Persian or Urdu rather than Arabic.
_NOT_RUSSIAN = frozenset("їєґіЇЄҐІ")
_NOT_ARABIC = frozenset("پچژگٹڈڑںے")
_LATIN_WORD = re.compile(r"[^\W\d_]+")
_SEPARATORS = re.compile(r"[_\-./]+")
_TITLE_SPLIT = re.compile(r",\s*(?:and\s+)?|\s+and\s+")


def _attribute(name: str, description: str, searchable: bool = True) -> dict:
    return {"name": name, "type": "keyword_list", "searchable": searchable, "filterable": True, "shown": True,
            "description": description}


#: The attributes a release schema declares so the tags are filtered and shown. Languages are not searched,
#: because nearly every item would answer to the default and crowd the word index.
JOB_TITLES_ATTRIBUTE = _attribute(JOB_TITLES, (
    "The job titles the item names, from the pinned occupation grid (O*NET titles) and the packaged occupation "
    "seeds. Tagged by rules from the item's own words, so a tag says whom the item talks about, not that it was "
    "judged."))
INDUSTRIES_ATTRIBUTE = _attribute(INDUSTRIES, (
    "The industries the item names, from a declared list of thirty-four. Tagged by rules from the item's own "
    "words, so a tag says what the item talks about, not that it was judged."))
LEVELS_ATTRIBUTE = _attribute(LEVELS, (
    "The experience levels the item names: student, junior, mid, senior, lead or executive. Tagged by rules "
    "from the item's own words."))
LANGUAGES_ATTRIBUTE = _attribute(LANGUAGES, (
    "The natural language of the item's text: english by default, or one of twelve languages found by its "
    "script or its stopwords. Not searched, because nearly every item would answer to english."), searchable=False)
GEOGRAPHIES_ATTRIBUTE = _attribute(GEOGRAPHIES, (
    "The countries and regions the item names, from a declared list. Tagged by rules from the item's own "
    "words, so a tag says where the item talks about, not that it was judged."))
FACET_ATTRIBUTES = (JOB_TITLES_ATTRIBUTE, INDUSTRIES_ATTRIBUTE, LEVELS_ATTRIBUTE, LANGUAGES_ATTRIBUTE,
                    GEOGRAPHIES_ATTRIBUTE)


def _refuse(code: str, message: str):
    raise LibraryRecordError(code, message)


def _fields(entry, name: str, required, optional=()) -> dict:
    if type(entry) is not dict:
        _refuse("facet_vocabulary_invalid", f"{name} is a mapping")
    unknown = sorted(str(key) for key in set(entry) - set(required) - set(optional))
    missing = sorted(set(required) - set(entry))
    if unknown or missing:
        _refuse("facet_vocabulary_invalid", f"{name} has unknown fields {unknown} or lacks {missing}")
    return entry


def _value(raw, name: str) -> str:
    if (not isinstance(raw, str) or not raw or raw != raw.strip() or len(raw) > VALUE_BOUND
            or not all(character.isprintable() for character in raw)):
        _refuse("facet_vocabulary_invalid", f"{name} is a bounded printable value")
    return raw


def _phrase_list(raw, name: str) -> tuple:
    if not isinstance(raw, list) or not raw or any(not isinstance(item, str) or not item.strip() for item in raw):
        _refuse("facet_vocabulary_invalid", f"{name} lists at least one phrase")
    return tuple(" ".join(item.split()) if item.isupper() else " ".join(item.lower().split()) for item in raw)


def _singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("ches", "shes", "sses", "xes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _singular_phrase(phrase: str) -> str:
    """The phrase with its head noun in the singular: the word before "of" when there is one, else the last."""
    words = phrase.split()
    head = words.index("of") - 1 if "of" in words[1:] else len(words) - 1
    return " ".join(words[:head] + [_singular(words[head])] + words[head + 1:])


def title_phrases(title: str, also_known_as=()) -> tuple:
    """The name phrases an item may use for one title.

    The title itself and its singular; then, for a title that joins several occupations with commas or "and",
    each joined occupation of at least two words whose head noun is plural, and its singular. A single word
    cut from a joined title (agents, records, judges, runners) is never a phrase, because such words are
    everywhere in harness material; a title that needs one lists it under also_known_as in the data."""
    whole = " ".join(title.lower().split())
    parts = [whole]
    for part in (piece.strip() for piece in _TITLE_SPLIT.split(whole)):
        words = part.split()
        head = words[words.index("of") - 1] if "of" in words[1:] else words[-1] if words else ""
        if len(words) >= 2 and part != whole and head.endswith("s") and not head.endswith("ss"):
            parts.append(part)
    phrases = []
    for part in parts:
        for form in (part, _singular_phrase(part)):
            if form not in phrases:
                phrases.append(form)
    for phrase in also_known_as:
        if phrase not in phrases:
            phrases.append(phrase)
    return tuple(phrases)


def _pattern(phrases) -> re.Pattern:
    """One pattern over every phrase, longest first, so a longer name wins over a shorter name inside it.

    An upper-case phrase (USA, EU, APAC) is matched exactly; every other phrase without regard to case. A
    match starts and ends at a word edge."""
    parts = []
    for phrase in sorted(phrases, key=lambda item: (-len(item), item)):
        escaped = re.escape(phrase)
        parts.append(escaped if phrase.isupper() else f"(?i:{escaped})")
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)")


@dataclass(frozen=True)
class FacetVocabulary:
    """The declared values of every facet, the phrase table of each phrase facet and the language rules."""

    version: str
    values: dict
    patterns: dict
    phrases: dict
    shared_phrases: dict
    descriptions: dict
    stopwords: dict
    shared_stopwords: tuple
    scripts: dict

    def lookup(self, facet: str, matched: str) -> tuple:
        """(value, phrase) of one matched text; exact for an abbreviation, by lower case for any other phrase."""
        table = self.phrases[facet]
        found = table.get(matched) or table.get(matched.lower())
        if found is None:
            _refuse("facet_vocabulary_invalid", f"{matched!r} matched no declared phrase of {facet}")
        return found


def _phrase_entries(facet: str, raw, drop_shared: bool):
    """(values, descriptions, table, shared) of one phrase facet."""
    if not isinstance(raw, list) or not raw:
        _refuse("facet_vocabulary_invalid", f"{facet} lists its values")
    values, descriptions, claims = [], {}, defaultdict(list)
    for index, entry in enumerate(raw):
        name = f"{facet}[{index}]"
        if facet == JOB_TITLES:
            entry = _fields(entry, name, ("value", "source", "code"), ("also_known_as",))
            if entry["source"] not in ("grid", "seed") or not isinstance(entry["code"], str):
                _refuse("facet_vocabulary_invalid", f"{name} names its grid or seed source and code")
            value = _value(entry["value"], name)
            phrases = title_phrases(value, _phrase_list(entry["also_known_as"], name)
                                    if "also_known_as" in entry else ())
            descriptions[value] = f"{entry['source']} {entry['code']}"
        else:
            entry = _fields(entry, name, ("value", "phrases", "description" if facet != GEOGRAPHIES else "kind"))
            value = _value(entry["value"], name)
            phrases = _phrase_list(entry["phrases"], name)
            descriptions[value] = str(entry.get("description") or entry.get("kind") or "")
            if facet == GEOGRAPHIES and entry["kind"] not in ("country", "region"):
                _refuse("facet_vocabulary_invalid", f"{name} is a country or a region")
        if value in values:
            _refuse("facet_vocabulary_invalid", f"{facet} declares {value!r} twice")
        values.append(value)
        for phrase in phrases:
            if value not in claims[phrase]:
                claims[phrase].append(value)
    shared = tuple(sorted(phrase for phrase, owners in claims.items() if len(owners) > 1))
    table = {phrase: (owners[0], phrase) for phrase, owners in claims.items()
             if len(owners) == 1 or not drop_shared}
    return tuple(values), descriptions, table, shared


def read_vocabulary(record, *, drop_shared: bool = True) -> FacetVocabulary:
    """The vocabulary of one library_facet_vocabulary/v1 record, or a typed refusal.

    ``drop_shared`` is the rule that a phrase several values claim names none of them and a stopword two
    languages claim counts for neither; the checks switch it off to show that the rule matters."""
    record = read_record(record, VOCABULARY_RECORD_TYPE, ("version", "facets"))
    if not isinstance(record["version"], str) or not record["version"]:
        _refuse("facet_vocabulary_invalid", "the vocabulary names its version")
    facets = _fields(record["facets"], "facets", FACETS)
    values, patterns, phrases, shared, descriptions = {}, {}, {}, {}, {}
    for facet in PHRASE_FACETS:
        block = _fields(facets[facet], facet, ("description", "values"))
        values[facet], descriptions[facet], table, shared[facet] = _phrase_entries(facet, block["values"], drop_shared)
        patterns[facet] = _pattern(table)
        phrases[facet] = table
    block = _fields(facets[LANGUAGES], LANGUAGES, ("description", "values"))
    if not isinstance(block["values"], list) or not block["values"]:
        _refuse("facet_vocabulary_invalid", "languages lists its values")
    languages, stopwords, scripts, descriptions[LANGUAGES] = [], {}, {}, {}
    for index, entry in enumerate(block["values"]):
        name = f"languages[{index}]"
        entry = _fields(entry, name, ("value", "description"), ("stopwords", "script"))
        value = _value(entry["value"], name)
        if value in languages or ("stopwords" in entry) == ("script" in entry):
            _refuse("facet_vocabulary_invalid", f"{name} is declared once, by its stopwords or by its script")
        languages.append(value)
        descriptions[LANGUAGES][value] = str(entry["description"])
        if "script" in entry:
            if entry["script"] not in SCRIPT_RANGES or entry["script"] == "latin":
                _refuse("facet_vocabulary_invalid", f"{name} names a known non-Latin script")
            scripts[value] = entry["script"]
        else:
            stopwords[value] = tuple(word.lower() for word in _phrase_list(entry["stopwords"], name))
    if DEFAULT_LANGUAGE not in stopwords:
        _refuse("facet_vocabulary_invalid", f"the default language {DEFAULT_LANGUAGE} is declared by its stopwords")
    counted = Counter(word for words in stopwords.values() for word in set(words))
    shared_words = tuple(sorted(word for word, owners in counted.items() if owners > 1))
    if drop_shared:
        stopwords = {language: frozenset(word for word in words if counted[word] == 1)
                     for language, words in stopwords.items()}
    else:
        stopwords = {language: frozenset(words) for language, words in stopwords.items()}
    values[LANGUAGES] = tuple(languages)
    return FacetVocabulary(record["version"], values, patterns, phrases, shared, descriptions, stopwords,
                           shared_words, scripts)


def vocabulary_record(path: str = str(VOCABULARY_FILE)) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=2)
def facet_vocabulary(path: str = str(VOCABULARY_FILE)) -> FacetVocabulary:
    return read_vocabulary(vocabulary_record(path))


def _text(value, name: str, bound: int) -> str:
    if not isinstance(value, str):
        raise LibraryRecordError("facet_material_invalid", f"{name} is text")
    return value[:bound]


@dataclass(frozen=True)
class FacetMaterial:
    """What the tagger reads about one item: its kinds, name, purpose, entry text and file roles."""

    kind: str
    harness_kind: str
    name: str
    purpose: str
    text: str
    file_roles: tuple = ()

    def __post_init__(self) -> None:
        for field in ("kind", "harness_kind"):
            value = getattr(self, field)
            if not isinstance(value, str) or len(value) > NAME_BOUND:
                raise LibraryRecordError("facet_material_invalid", f"{field} is a bounded name")
        object.__setattr__(self, "name", _text(self.name, "name", NAME_BOUND))
        object.__setattr__(self, "purpose", _text(self.purpose, "purpose", PURPOSE_BOUND))
        object.__setattr__(self, "text", _text(self.text, "text", TEXT_BOUND))
        roles = tuple(self.file_roles)
        if any(not isinstance(role, str) for role in roles):
            raise LibraryRecordError("facet_material_invalid", "file roles are names")
        object.__setattr__(self, "file_roles", roles)

    def to_dict(self) -> dict:
        return {"record_type": MATERIAL_RECORD_TYPE, "kind": self.kind, "harness_kind": self.harness_kind,
                "name": self.name, "purpose": self.purpose, "text": self.text, "file_roles": list(self.file_roles)}


@dataclass(frozen=True)
class FacetTags:
    """The values of the five facets for one item, the engine that wrote them and the basis of each value."""

    values: dict
    engine_id: str
    engine_version: str
    evidence: tuple = ()

    def __post_init__(self) -> None:
        vocabulary = facet_vocabulary()
        given = dict(self.values) if isinstance(self.values, dict) else None
        if given is None or set(given) - set(FACETS):
            raise LibraryRecordError("facet_tags_invalid", f"tags name the facets {FACETS} only")
        normalized = {}
        for facet in FACETS:
            chosen = tuple(given.get(facet, ()))
            declared = set(vocabulary.values[facet])
            if (len(chosen) > MAXIMUM_VALUES[facet] or len(set(chosen)) != len(chosen)
                    or any(value not in declared for value in chosen)):
                raise LibraryRecordError("facet_tags_invalid", f"{facet} holds at most {MAXIMUM_VALUES[facet]} "
                                                               "distinct declared values")
            normalized[facet] = chosen
        if not self.engine_id or not self.engine_version:
            raise LibraryRecordError("facet_tags_invalid", "tags name the engine that wrote them")
        evidence = []
        for row in self.evidence:
            facet, value, basis = (str(part) for part in row)
            if facet not in FACETS or value not in normalized[facet]:
                raise LibraryRecordError("facet_tags_invalid", "evidence names a tagged value of a facet")
            evidence.append((facet, value, basis))
        object.__setattr__(self, "values", normalized)
        object.__setattr__(self, "evidence", tuple(evidence))

    def to_dict(self) -> dict:
        return {"record_type": TAGS_RECORD_TYPE, "values": {facet: list(self.values[facet]) for facet in FACETS},
                "engine": {"engine_id": self.engine_id, "engine_version": self.engine_version},
                "evidence": [{"facet": facet, "value": value, "basis": basis} for facet, value, basis in self.evidence]}

    def attribute_values(self) -> dict:
        """The attribute values a release line carries: only the facets that hold a value."""
        return {facet: list(self.values[facet]) for facet in FACETS if self.values[facet]}


class FacetTagger:
    """The edge every facet engine implements: engine_id, engine_version, engine_kind and tag()."""

    engine_id = ""
    engine_version = ""
    engine_kind = "facet_tagger"

    def tag(self, material: FacetMaterial) -> FacetTags:
        raise NotImplementedError


def _script_of(character: str) -> str:
    ordinal = ord(character)
    for script, ranges in SCRIPT_RANGES.items():
        if any(low <= ordinal <= high for low, high in ranges):
            return script
    return "other"


class RulesFacetTagger(FacetTagger):
    """Engine facet_rules: declared phrases in the name, purpose and entry text; scripts and stopwords for the language.

    A value is tagged when the name or purpose names it once, or when the body names it by two distinct
    phrases (a singular and its plural count once). A mention in the name or purpose weighs two and a mention
    in the body one, each capped at two, and the highest scores are kept up to each facet's bound, in declared
    order among equals. The language comes from the share of letters in a
    non-Latin script, or from the share of a Latin language's own stopwords among the Latin words; a text whose
    letters are mostly Latin and reaches no threshold is english by default. The evidence names each phrase,
    script or count, so a sampled tag can be checked against the item by hand.
    """

    engine_id = "facet_rules"
    engine_version = "1.0.0"
    engine_kind = "facet_tagger"
    effects = ("pure",)
    third_party = "none"

    def __init__(self, vocabulary: FacetVocabulary | None = None) -> None:
        self.vocabulary = vocabulary or facet_vocabulary()

    @classmethod
    def availability(cls, settings: dict):
        return True, "always_available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "vocabulary_version": self.vocabulary.version, "minimum_body_phrases": MINIMUM_BODY_PHRASES,
                "maximum_values": dict(MAXIMUM_VALUES), "text_bound": TEXT_BOUND,
                "default_language": DEFAULT_LANGUAGE}

    def scores(self, material: FacetMaterial) -> dict:
        """For each phrase facet, the score, evidence and eligibility of every value the item mentions.

        A value is eligible when the name or purpose names it, or when the body names it by the minimum number
        of distinct phrases."""
        headline = _SEPARATORS.sub(" ", material.name) + "\n" + material.purpose
        result = {}
        for facet in PHRASE_FACETS:
            pattern = self.vocabulary.patterns[facet]
            mentions = defaultdict(lambda: (Counter(), Counter()))
            for place, source in ((0, headline), (1, material.text)):
                for match in pattern.finditer(source):
                    value, phrase = self.vocabulary.lookup(facet, match.group(0))
                    mentions[value][place][phrase] += 1
            scored = {}
            for value, (head, body) in mentions.items():
                score = HEADLINE_WEIGHT * min(sum(head.values()), MENTION_CAP) + min(sum(body.values()), MENTION_CAP)
                evidence = ([f"name or purpose: {phrase}" for phrase in sorted(head)]
                            + [f"text: {phrase}, {count} mention" + ("s" if count != 1 else "")
                               for phrase, count in sorted(body.items())])
                eligible = bool(head) or len({_singular_phrase(phrase) for phrase in body}) >= MINIMUM_BODY_PHRASES
                scored[value] = (score, tuple(evidence), eligible)
            result[facet] = scored
        return result

    def language_scores(self, material: FacetMaterial) -> dict:
        """Every language the text reaches a threshold for, as value -> (share, basis); the default when none."""
        text = "\n".join((material.name, material.purpose, material.text))
        letters = Counter(_script_of(character) for character in text if character.isalpha())
        total = sum(letters.values())
        words = [word.lower() for word in _LATIN_WORD.findall(text)
                 if all(_script_of(character) == "latin" for character in word)]
        found = {}
        for language, stopwords in self.vocabulary.stopwords.items():
            hits = sum(1 for word in words if word in stopwords)
            share = hits / len(words) if words else 0.0
            if hits >= MINIMUM_STOPWORD_HITS and share >= MINIMUM_STOPWORD_SHARE:
                found[language] = (share, f"stopwords: {hits} of {len(words)} latin words")
        if total:
            shares = {script: count / total for script, count in letters.items()}
            kana = shares.get("kana", 0.0)
            present = set(text)
            for language, script in self.vocabulary.scripts.items():
                share = shares.get(script, 0.0)
                if script == "kana":
                    tagged = kana >= MINIMUM_KANA_SHARE
                elif script == "han":
                    tagged = share >= MINIMUM_SCRIPT_SHARE and kana < MINIMUM_KANA_SHARE
                elif script == "cyrillic":
                    tagged = share >= MINIMUM_SCRIPT_SHARE and not (present & _NOT_RUSSIAN)
                elif script == "arabic":
                    tagged = share >= MINIMUM_SCRIPT_SHARE and not (present & _NOT_ARABIC)
                else:
                    tagged = share >= MINIMUM_SCRIPT_SHARE
                if tagged:
                    found[language] = (share, f"script: {script} {share:.0%} of letters")
        if not found and DEFAULT_LANGUAGE and total and letters.get("latin", 0) / total >= LATIN_MAJORITY:
            found[DEFAULT_LANGUAGE] = (0.0, "default: no other language reached its threshold")
        return found

    def tag(self, material: FacetMaterial) -> FacetTags:
        if not isinstance(material, FacetMaterial):
            raise LibraryRecordError("facet_material_invalid", "the tagger reads facet_material/v1")
        scored = self.scores(material)
        values, evidence = {}, []
        for facet in PHRASE_FACETS:
            order = {value: index for index, value in enumerate(self.vocabulary.values[facet])}
            chosen = sorted((value for value, (_score, _basis, eligible) in scored[facet].items() if eligible),
                            key=lambda value: (-scored[facet][value][0], order[value]))[:MAXIMUM_VALUES[facet]]
            values[facet] = tuple(chosen)
            evidence.extend((facet, value, basis) for value in chosen for basis in scored[facet][value][1])
        languages = self.language_scores(material)
        order = {value: index for index, value in enumerate(self.vocabulary.values[LANGUAGES])}
        chosen = sorted(languages, key=lambda value: (-languages[value][0], order[value]))[:MAXIMUM_VALUES[LANGUAGES]]
        values[LANGUAGES] = tuple(chosen)
        evidence.extend((LANGUAGES, value, languages[value][1]) for value in chosen)
        return FacetTags(values, self.engine_id, self.engine_version, tuple(evidence))
