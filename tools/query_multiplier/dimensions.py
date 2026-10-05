"""The versioned dimension library: every axis the multiplier can multiply, as data with its source and licence.

`research_dimension_library/v1` lists dimensions. Each dimension has an id, a kind, a source with its licence, a
weight for its null value and values, written inline or read by a named loader from a pinned file (its SHA-256 is
in the library, so a changed table changes the plan digest instead of silently changing queries). A value has a
stable id, the search phrase (`text`), an integer weight and attributes an executor may read to render it (a
GitHub `language:` name, a file extension, an OpenAlex filter value).

```text
research_dimension_library/v1
├── dimensions             id, title, kind, null_share, source{title, url, licence, retrieved, note}
│   ├── values             inline: id, text, weight, attributes
│   └── values_from        loader + path + sha256: onet_occupations, onet_tasks, library_facet_industries,
│                          catalogue_tuple, sdg_goals, sdg_targets, wikidata_geography,
│                          wikidata_languages, wikidata_language_endonyms, quarters
└── rules                  compatibility: when a value of one dimension has an attribute in a set, the listed
                           dimensions must be null (a media format never meets a public-policy topic)
```

The null value is not a missing value: it means "omit this filter", so a query without a geography is the global
baseline every country-specific query is compared with. Search phrases pass the same normalisation and sensitive
pattern screen as the radar's query matrix (`knowledge_radar.query_matrix.words`), so an address, a credential
shape or a private path never becomes a query. The screen is heuristic; the library holds public vocabulary only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from knowledge_radar.query_matrix import digest, freeze, plain, words

LIBRARY = "research_dimension_library/v1"
KINDS = ("topic", "format", "programming_language", "natural_language", "geography", "time_window", "licence",
         "source_type", "qualifier")
_ID = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
_VALUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:+#-]{0,79}\Z")
#: Attribute values an executor renders into a request: names, extensions, qualifier values, never free text.
_ATTRIBUTE_TEXT = re.compile(r"(?:[A-Za-z0-9@.][A-Za-z0-9 @._+#/*>=<,:()|\[\]-]{0,119})?\Z")
MAXIMUM_VALUES = 50000
MAXIMUM_WEIGHT = 50
#: The null value's share of a dimension, in percent: 40 means four queries in ten omit this filter.
MAXIMUM_NULL_SHARE = 90
REPOSITORY = Path(__file__).resolve().parents[2]


class DimensionError(ValueError):
    """The library or one of its tables broke a rule; the code names which."""


@dataclass(frozen=True)
class Value:
    id: str
    text: str
    weight: int
    attributes: MappingProxyType

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "weight": self.weight, "attributes": plain(self.attributes)}


@dataclass(frozen=True)
class Dimension:
    id: str
    title: str
    kind: str
    null_share: int
    source: MappingProxyType
    values: tuple
    by_id: MappingProxyType = field(compare=False, repr=False)

    def value(self, value_id):
        return None if value_id is None else self.by_id[value_id]

    def digest(self) -> str:
        return digest({"id": self.id, "kind": self.kind, "null_share": self.null_share,
                       "source": plain(self.source), "values": [value.to_dict() for value in self.values]})


@dataclass(frozen=True)
class Rule:
    id: str
    dimension: str
    attribute: str
    members: frozenset
    require_null: tuple
    reason: str

    def violated(self, assignment: dict) -> bool:
        value = assignment.get(self.dimension)
        if value is None:
            return False
        if self.attribute == "*":
            return any(assignment.get(name) is not None for name in self.require_null)
        held = value.attributes.get(self.attribute)
        held = held if isinstance(held, (list, tuple)) else (held,)
        if not any(item in self.members for item in held):
            return False
        return any(assignment.get(name) is not None for name in self.require_null)


@dataclass(frozen=True)
class Library:
    version: str
    digest: str
    dimensions: MappingProxyType
    rules: tuple
    provenance: tuple

    def dimension(self, name: str) -> Dimension:
        if name not in self.dimensions:
            raise DimensionError("dimension_unknown:" + name)
        return self.dimensions[name]

    def violations(self, assignment: dict) -> list:
        return [rule.id for rule in self.rules if rule.violated(assignment)]


def _strict(value, required, optional, name):
    if type(value) is not dict or not set(required) <= set(value) or not set(value) <= set(required) | set(optional):
        raise DimensionError(name + "_fields")


def _attributes(value, name):
    if value is None:
        return MappingProxyType({})
    if type(value) is not dict or len(value) > 24:
        raise DimensionError(name + "_attributes")
    for key, item in value.items():
        if not _ID.fullmatch(key):
            raise DimensionError(name + "_attribute_name")
        items = item if isinstance(item, list) else [item]
        if len(items) > 40:
            raise DimensionError(name + "_attribute_bound")
        for part in items:
            if type(part) is bool or part is None:
                continue
            if type(part) is int:
                continue
            if type(part) is not str or not _ATTRIBUTE_TEXT.fullmatch(part):
                raise DimensionError(name + "_attribute_text:" + key)
    return freeze(value)


def make_value(raw: dict, name: str) -> Value:
    _strict(raw, ("id", "text"), ("weight", "attributes"), name)
    if type(raw["id"]) is not str or not _VALUE_ID.fullmatch(raw["id"]):
        raise DimensionError(name + "_value_id")
    weight = raw.get("weight", 1)
    if type(weight) is not int or not 1 <= weight <= MAXIMUM_WEIGHT:
        raise DimensionError(name + "_value_weight")
    try:
        text = words(raw["text"])
    except ValueError as error:
        raise DimensionError(name + "_value_text:" + str(error)) from None
    return Value(raw["id"], text, weight, _attributes(raw.get("attributes"), name))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path_text: str, data_roots: dict) -> Path:
    """A loader path is repository-relative, or names a declared data root as ``<root>/relative``."""
    if path_text.startswith("<"):
        root, _, rest = path_text[1:].partition(">/")
        if root not in data_roots:
            raise DimensionError("data_root_not_declared:" + root)
        base = Path(data_roots[root])
        return base / rest
    candidate = (REPOSITORY / path_text).resolve()
    if not candidate.is_relative_to(REPOSITORY):
        raise DimensionError("loader_path_outside_repository")
    return candidate


# ---------------------------------------------------------------------------------------------------------- loaders
_STOPWORDS = frozenset("""a an and are as at be by for from in into is it its of on or such that the their them this
to with within without other others etc using use used uses via per all any each more most may might must can could
would should will shall not no nor than then these those which who whom whose what when where while about above after
against among before below between both during over under up down out off own same so too very s t just also based
including include includes related relevant appropriate necessary various specific general new other""".split())


_BOUNDARIES = frozenset("""to for by in on with from using through according such including during at as of into
across within without via over under about against between among per than""".split())
_CONNECTORS = frozenset(("and", "or", "and/or"))


def _chunks(text: str) -> list:
    """Split one statement into word chunks at punctuation and prepositions, keeping word order."""
    chunks, current = [], []
    for token in re.findall(r"[a-z][a-z'/-]*|[,;:.()]", text.lower()):
        if token in ",;:.()" or token in _BOUNDARIES:
            if current:
                chunks.append(current)
            current = []
            continue
        current.append(token.removesuffix("'s").strip("'"))
    if current:
        chunks.append(current)
    return chunks


def task_phrase(text: str) -> str:
    """The object of a task statement as a short phrase: the head noun group after the opening verbs.

    Task statements open with one or two verbs ("Prepare and file tax returns"). The phrase is the last three
    content words of the first chunk after those verbs (the head of an English noun group comes last), extended
    with the next chunk's first content words when the head has fewer than two. Deterministic and local.
    """
    chunks = _chunks(text)
    if not chunks:
        return ""
    first = chunks[0]
    index = 1  # the opening verb
    while index + 1 < len(first) and first[index] in _CONNECTORS:
        index += 2  # "prepare and file": the word after a connector is a second verb
    head = [word for word in first[index:] if word not in _STOPWORDS and word not in _CONNECTORS and len(word) > 2][-3:]
    for chunk in chunks[1:]:
        if len(head) >= 2:
            break
        following = [word for word in chunk[1:] if word not in _STOPWORDS and word not in _CONNECTORS and len(word) > 2]
        head += following[:2 - len(head)]
    return " ".join(head)


def _task_phrases(rows: list) -> list:
    """One short searchable phrase per task statement; a phrase two tasks share is kept once."""
    seen, out = set(), []
    for row in rows:
        try:
            phrase = words(task_phrase(row["text"]))
        except ValueError:
            continue
        if phrase in seen or " " not in phrase:
            continue
        seen.add(phrase)
        out.append({"id": "task:" + row["id"], "text": phrase, "attributes": {"soc": row["soc"]}})
    return out


def _tsv(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_onet_occupations(path: Path) -> list:
    rows = _tsv(path)
    return [{"id": "soc:" + row["O*NET-SOC Code"], "text": row["Title"], "attributes": {"family": "occupation"}}
            for row in rows if row.get("O*NET-SOC Code") and row.get("Title")]


def load_onet_tasks(path: Path) -> list:
    rows = [{"id": row["Task ID"], "text": row["Task"], "soc": row["O*NET-SOC Code"]}
            for row in _tsv(path) if row.get("Task ID") and row.get("Task")]
    return _task_phrases(rows)


def load_library_facet_industries(path: Path) -> list:
    import yaml  # the repository's own facet vocabulary is YAML; read it with the loader the repository uses
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [{"id": "industry:" + re.sub(r"[^a-z0-9]+", "_", row["value"]).strip("_"), "text": row["value"],
             "attributes": {"family": "industry"}} for row in document["facets"]["industries"]["values"]]


def _tuple_assignment(path: Path, name: str) -> tuple:
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise DimensionError("source_tuple_missing:" + name)


def load_catalogue_tuple(path: Path, name: str, phrases: dict) -> list:
    """The catalogue's closed vocabulary, read from source text; every member needs a declared search phrase."""
    members = _tuple_assignment(path, name)
    missing = [member for member in members if member not in phrases]
    if missing or set(phrases) - set(members):
        raise DimensionError("catalogue_vocabulary_out_of_sync:" + ",".join(sorted(set(missing) | (set(phrases) - set(members)))))
    return [{"id": member, "text": phrases[member], "attributes": {"family": name.lower()}} for member in members]


def load_sdg(path: Path, level: str) -> list:
    document = json.loads(path.read_bytes())
    if document.get("record_type") != "research_sdg_vocabulary/v1":
        raise DimensionError("sdg_vocabulary_version")
    rows = document["goals"] if level == "goals" else document["targets"]
    out = []
    for row in rows:
        identity = "sdg:" + row["id"]
        attributes = {"goal": row["id"].split(".")[0], "family": "sdg_" + level[:-1]}
        out.append({"id": identity, "text": row["phrase"], "attributes": attributes})
    return out


def load_wikidata_geography(path: Path, part: str, overrides: dict) -> list:
    document = json.loads(path.read_bytes())
    if document.get("record_type") != "research_reference_geography/v1":
        raise DimensionError("geography_version")
    out = []
    if part == "countries":
        for row in document["countries_or_areas"]:
            text = overrides.get(row["iso2"], row["label"])
            out.append({"id": "iso:" + row["iso2"], "text": text,
                        "attributes": {"iso2": row["iso2"], "iso3": row["iso3"] or "", "m49": row["m49"] or "",
                                       "geo_kind": "country_or_area"}})
    else:
        for row in document["regions"]:
            out.append({"id": "m49:" + row["m49"], "text": overrides.get(row["m49"], row["label"]),
                        "attributes": {"m49": row["m49"], "geo_kind": "region"}})
    return out


def load_wikidata_languages(path: Path, mode: str) -> list:
    """ISO 639-1 languages by English label (mode ``english``) or by their own name (mode ``native``).

    The native mode answers the review finding that language facets were English labels only: a query for
    Spanish material can say "español". A language whose native label is missing, or repeats another
    language's, is left out of the native mode rather than given an English stand-in.
    """
    document = json.loads(path.read_bytes())
    if document.get("record_type") != "research_reference_languages/v1":
        raise DimensionError("languages_version")
    out, seen = [], set()
    for row in document["languages"]:
        attributes = {"iso639_1": row["iso639_1"]}
        if mode == "english":
            text = row["label"]
        else:
            text = None
            for label in row["native_labels"]:
                try:
                    candidate = words(label)
                except ValueError:
                    continue
                if candidate not in seen:
                    text = candidate
                    break
            if text is None:
                continue
        seen.add(words(text))
        out.append({"id": "lang:" + row["iso639_1"], "text": text, "attributes": attributes})
    return out


def load_quarters(first: str, last: str) -> list:
    start_year, start_quarter = int(first[:4]), int(first[-1])
    end_year, end_quarter = int(last[:4]), int(last[-1])
    out, year, quarter = [], start_year, start_quarter
    ends = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
    while (year, quarter) <= (end_year, end_quarter):
        begin = f"{year}-{(quarter - 1) * 3 + 1:02d}-01"
        out.append({"id": f"{year}q{quarter}", "text": f"{year} q{quarter}",
                    "attributes": {"from": begin, "to": f"{year}-{ends[quarter]}"}})
        year, quarter = (year + 1, 1) if quarter == 4 else (year, quarter + 1)
    return out


def _load(spec: dict, data_roots: dict) -> tuple[list, dict]:
    loader = spec["loader"]
    if loader == "quarters":
        return load_quarters(spec["first"], spec["last"]), {"loader": loader}
    path = _resolve(spec["path"], data_roots)
    if not path.is_file():
        raise DimensionError("loader_source_missing:" + spec["path"])
    found = _sha256(path)
    if spec.get("sha256") and found != spec["sha256"]:
        raise DimensionError("loader_source_digest_changed:" + spec["path"])
    pin = {"loader": loader, "path": spec["path"], "sha256": found}
    if loader == "onet_occupations":
        return load_onet_occupations(path), pin
    if loader == "onet_tasks":
        return load_onet_tasks(path), pin
    if loader == "library_facet_industries":
        return load_library_facet_industries(path), pin
    if loader == "catalogue_tuple":
        return load_catalogue_tuple(path, spec["name"], spec["phrases"]), pin
    if loader in ("sdg_goals", "sdg_targets"):
        return load_sdg(path, loader[4:]), pin
    if loader in ("wikidata_countries", "wikidata_regions"):
        return load_wikidata_geography(path, loader[9:], spec.get("overrides", {})), pin
    if loader == "wikidata_geography":
        overrides = spec.get("overrides", {})
        return load_wikidata_geography(path, "regions", overrides) + load_wikidata_geography(path, "countries", overrides), pin
    if loader in ("wikidata_languages", "wikidata_language_endonyms"):
        return load_wikidata_languages(path, "english" if loader == "wikidata_languages" else "native"), pin
    raise DimensionError("loader_unknown:" + loader)


def _dimension(raw: dict, data_roots: dict) -> Dimension:
    _strict(raw, ("id", "title", "kind", "null_share", "source"), ("values", "values_from", "note"), "dimension")
    name = raw["id"]
    if type(name) is not str or not _ID.fullmatch(name):
        raise DimensionError("dimension_id")
    if raw["kind"] not in KINDS:
        raise DimensionError(name + "_kind")
    if type(raw["null_share"]) is not int or not 0 <= raw["null_share"] <= MAXIMUM_NULL_SHARE:
        raise DimensionError(name + "_null_share")
    source = raw["source"]
    _strict(source, ("title", "licence"), ("url", "retrieved", "note", "reference"), name + "_source")
    if ("values" in raw) == ("values_from" in raw):
        raise DimensionError(name + "_values_or_loader")
    pins = {}
    if "values" in raw:
        rows = raw["values"]
    else:
        spec = dict(raw["values_from"])
        rows, pins = _load(spec, data_roots)
        excluded = set(spec.get("exclude_ids") or ())
        weights = spec.get("weights") or {}
        rows = [row | ({"weight": weights[row["id"]]} if row["id"] in weights else {})
                for row in rows if row["id"] not in excluded] + list(spec.get("extra_values") or [])
    if type(rows) is not list or not 1 <= len(rows) <= MAXIMUM_VALUES:
        raise DimensionError(name + "_values_bound")
    values, ids, texts, skipped = [], set(), set(), Counter()
    for row in rows:
        try:
            value = make_value(row, name)
        except DimensionError as error:
            # A loaded table may hold a row that is no usable search phrase (too long, an address, a control
            # character); it is skipped and counted. A hand-written value must be valid, so the error stands.
            if "values" in raw:
                raise
            skipped[str(error).rsplit(":", 1)[-1]] += 1
            continue
        if value.id in ids:
            raise DimensionError(name + "_duplicate_value_id:" + value.id)
        if value.text in texts:
            if "values" in raw:
                raise DimensionError(name + "_duplicate_value_text:" + value.text)
            skipped["duplicate_text"] += 1
            continue
        ids.add(value.id)
        texts.add(value.text)
        values.append(value)
    if pins and skipped:
        pins = pins | {"skipped_rows": dict(sorted(skipped.items()))}
    source = dict(source) | ({"pinned": pins} if pins else {})
    return Dimension(name, raw["title"], raw["kind"], raw["null_share"], freeze(source), tuple(values),
                     MappingProxyType({value.id: value for value in values}))


def _rule(raw: dict, dimensions: set) -> Rule:
    _strict(raw, ("id", "if", "require_null", "reason"), (), "rule")
    condition = raw["if"]
    _strict(condition, ("dimension", "attribute", "in"), (), "rule_if")
    if condition["dimension"] not in dimensions or any(name not in dimensions for name in raw["require_null"]):
        raise DimensionError("rule_dimension_unknown:" + raw["id"])
    return Rule(raw["id"], condition["dimension"], condition["attribute"], frozenset(condition["in"]),
                tuple(raw["require_null"]), raw["reason"])


def read_library(value: dict, *, data_roots: "dict | None" = None, only: "set | None" = None) -> Library:
    """Validate the library and load every table it names; ``only`` limits loading to the dimensions a plan uses."""
    _strict(value, ("record_type", "version", "dimensions", "rules", "provenance"), (), "library")
    if value["record_type"] != LIBRARY or type(value["version"]) is not str:
        raise DimensionError("library_version")
    dimensions = {}
    for raw in value["dimensions"]:
        if only is not None and raw.get("id") not in only:
            continue
        dimension = _dimension(raw, data_roots or {})
        if dimension.id in dimensions:
            raise DimensionError("dimension_duplicate:" + dimension.id)
        dimensions[dimension.id] = dimension
    declared = {raw.get("id") for raw in value["dimensions"] if type(raw) is dict}
    rules = tuple(_rule(raw, declared) for raw in value["rules"])
    identity = digest({"version": value["version"], "dimensions": {name: dimension.digest() for name, dimension in sorted(dimensions.items())},
                       "rules": [raw for raw in value["rules"]]})
    return Library(value["version"], identity, MappingProxyType(dimensions), rules, tuple(value["provenance"]))


def default_library_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "dimensions-v1.json"


def load_library(path: "Path | None" = None, *, data_roots: "dict | None" = None, only: "set | None" = None) -> Library:
    return read_library(json.loads(Path(path or default_library_path()).read_bytes()), data_roots=data_roots, only=only)
