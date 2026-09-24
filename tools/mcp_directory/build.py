"""Merge listings into one row per offering, classify each row, order the rows and encode the data files.

Kind: pure functions over typed records. Nothing here reads the network or the disk except the
category rule file it is handed.

Merge rules, in order. Listings are joined into one offering when they share:

1. the same server name, across the official registry, the recorded research and GitHub's directory;
2. the same complete installation surface: every package with its declared arguments, every remote
   endpoint with its query, and the same code repository and folder (two registry names with the same
   surface are one offering listed twice, and the second name is kept as an alias);
3. the same remote endpoint address, with its query.

A listing from GitHub's directory or the Docker catalog that shares none of these joins the one offering
whose official registry or publisher listing names the same code repository and folder, and only when
exactly one such offering exists. One package shared by several servers, such as a monorepo package
started with different arguments, never merges them.

Ordering, filtering and inclusion read only the editorial fields. The commercial relationship of a row is
encoded beside the row and read by nothing here but the encoder.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from loop_engine.core.service_runtime import commercial_relationship as commercial

from .records import (
    API, AUTH_BITS, LICENCE_BASES, LOCATION_KINDS, MANIFEST_RECORD_TYPE, OFFERING_BITS, ORIGIN_MAKER, ORIGIN_OTHER,
    ORIGIN_UNKNOWN, ORIGINS, PACKAGE_KINDS, PUBLISHER_KINDS, REMOTE_KINDS, REPOSITORY_STATES, ROWS_RECORD_TYPE, SOURCE_BITS,
    SOURCE_ORDER, TRANSPORT_BITS, Exclusion, Offering, repository_key, repository_owner)

CATEGORY_RULES_RECORD_TYPE = "mcp_directory_category_rules/v1"
#: The number of row files. It equals the number of rows-N.json addresses the service serves.
PART_COUNT = 8
#: Row columns, in the order each row array holds them. The manifest repeats this list.
COLUMNS = ("id", "name", "publisher", "publisher_kind", "description", "category", "offering", "origin", "locations",
           "transports", "auth", "licence", "licence_basis", "website", "repository", "repository_state", "sources",
           "aliases", "updated", "commercial")
#: Sources whose listing names are server names in the registry's namespace.
NAMED_SOURCES = frozenset({"registry", "codex", "github"})
#: Sources whose code repository anchors a later listing that shares nothing else.
ANCHOR_SOURCES = frozenset({"registry", "docs"})
JOINING_SOURCES = frozenset({"github", "docker"})
ORIGIN_RANK = {ORIGIN_MAKER: 0, ORIGIN_UNKNOWN: 1, ORIGIN_OTHER: 2}
_DAY_ZERO = "1970-01-01"
_WORD = re.compile(r"[a-z0-9]+")


def words(text: str) -> str:
    """Text as lower-case words separated by single spaces, with a space at each end, for whole-word matching."""
    return " " + " ".join(_WORD.findall((text or "").lower())) + " "


class CategoryRules:
    """The versioned keyword rules that name a row's category, read strictly.

    A keyword and the text it is matched in are both reduced to lower-case words, so a keyword matches only whole
    words and whole phrases: "ci/cd" matches "CI/CD" and "ci cd", and "tts" does not match "settings".
    """

    def __init__(self, record: dict) -> None:
        if not isinstance(record, dict) or record.get("record_type") != CATEGORY_RULES_RECORD_TYPE:
            raise ValueError(f"category rules must be {CATEGORY_RULES_RECORD_TYPE}")
        fallback = record.get("fallback") or {}
        self.fallback = (str(fallback.get("id") or ""), str(fallback.get("label") or ""))
        if not all(self.fallback):
            raise ValueError("category rules name a fallback category with a label")
        self.categories = []
        seen = {self.fallback[0]}
        for item in record.get("categories") or ():
            identity, label = str(item.get("id") or ""), str(item.get("label") or "")
            keywords = tuple(dict.fromkeys(words(str(word)) for word in item.get("keywords") or ()))
            hints = tuple(str(word).lower() for word in item.get("docker_categories") or ())
            if not identity or not label or identity in seen or not keywords or any(not word.strip() for word in keywords):
                raise ValueError(f"category {identity!r} needs a unique id, a label and keywords")
            seen.add(identity)
            single = frozenset(keyword.strip() for keyword in keywords if " " not in keyword.strip())
            phrases = tuple(keyword for keyword in keywords if " " in keyword.strip())
            self.categories.append((identity, label, (single, phrases), hints))
        if not self.categories:
            raise ValueError("category rules hold at least one category")

    @classmethod
    def from_file(cls, path: Path) -> "CategoryRules":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def labels(self) -> list:
        return [(identity, label) for identity, label, _keywords, _hints in self.categories] + [self.fallback]

    def classify(self, name: str, description: str, hints=()) -> str:
        """The category with the highest keyword score; the first written wins a tie; none scores the fallback."""
        name_text, description_text = words(name), words(description)
        name_words, description_words = set(name_text.split()), set(description_text.split())
        best, best_score = self.fallback[0], 0
        for identity, _label, (single, phrases), docker in self.categories:
            score = 3 * (len(single & name_words) + sum(1 for phrase in phrases if phrase in name_text))
            score += len(single & description_words) + sum(1 for phrase in phrases if phrase in description_text)
            score += sum(2 for hint in hints if hint and hint in docker)
            if score > best_score:
                best, best_score = identity, score
        return best


def _surface(listing) -> str:
    return json.dumps([list(listing.identities), repository_key(listing.repository, listing.subfolder)])


def merge_listings(listings) -> list:
    """Group listings that describe the same offering; each group comes back in order of trust."""
    ordered = sorted(listings, key=lambda item: (SOURCE_ORDER.index(item.source), item.key))
    parent = list(range(len(ordered)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(first, second):
        a, b = find(first), find(second)
        if a != b:
            parent[max(a, b)] = min(a, b)

    keyed = defaultdict(list)
    for index, listing in enumerate(ordered):
        if listing.source in NAMED_SOURCES:
            keyed["name:" + listing.key.lower()].append(index)
        if listing.identities:
            keyed["surface:" + _surface(listing)].append(index)
        for identity in listing.identities:
            if identity.startswith("remote:"):
                keyed[identity].append(index)
    for members in keyed.values():
        for other in members[1:]:
            union(members[0], other)
    anchors = defaultdict(set)
    for index, listing in enumerate(ordered):
        if listing.source in ANCHOR_SOURCES and listing.repository:
            anchors[repository_key(listing.repository, listing.subfolder)].add(index)
    for index, listing in enumerate(ordered):
        if listing.source not in JOINING_SOURCES or not listing.repository:
            continue
        roots = {find(anchor) for anchor in anchors.get(repository_key(listing.repository, listing.subfolder), ())}
        if len(roots) == 1 and find(index) not in roots:
            union(next(iter(roots)), index)
    groups = defaultdict(list)
    for index, listing in enumerate(ordered):
        groups[find(index)].append(listing)
    return [groups[root] for root in sorted(groups)]


def _primary(group):
    kind_rank = {"domain": 0, "github": 1, "repository": 2, "unknown": 3}
    return min(group, key=lambda item: (SOURCE_ORDER.index(item.source), ORIGIN_RANK.get(item.origin, 1),
                                        kind_rank.get(item.publisher_kind, 3), item.key))


def _identity(listing) -> str:
    return listing.key if listing.source in NAMED_SOURCES else f"{listing.source}/{listing.key}"


def offering_of(group, rules: CategoryRules) -> "Offering | Exclusion":
    """The row one group of listings becomes, or the rule that refuses it."""
    primary = _primary(group)
    seen, locations = set(), []
    for listing in sorted(group, key=lambda item: SOURCE_ORDER.index(item.source)):
        for location in listing.locations:
            key = (location.kind, location.value.lower())
            if key not in seen:
                seen.add(key)
                locations.append(location)
    locations.sort(key=lambda item: (LOCATION_KINDS.index(item.kind), item.value.lower()))
    repository = primary.repository or next((item.repository for item in group if item.repository), "")
    if not locations and not repository:
        return Exclusion(primary.source, primary.key, "no_location", "no package, remote endpoint or code repository")
    transports = 0
    for location in locations:
        if location.transport in TRANSPORT_BITS:
            transports |= TRANSPORT_BITS[location.transport]
    auth = 0
    for listing in group:
        auth |= listing.auth
    if auth & ~AUTH_BITS["none"]:
        auth &= ~AUTH_BITS["none"]
    offering = 0
    kinds = {location.kind for location in locations}
    if kinds & REMOTE_KINDS:
        offering |= OFFERING_BITS["remote"]
    if kinds & PACKAGE_KINDS:
        offering |= OFFERING_BITS["package"]
    if API in kinds:
        offering |= OFFERING_BITS["api"]
    if not offering:
        offering = OFFERING_BITS["source"]
    licensed = next((item for item in sorted(group, key=lambda item: SOURCE_ORDER.index(item.source)) if item.licence), None)
    if any(item.source == "docs" for item in group):
        origin = ORIGIN_MAKER
    elif primary.origin in (ORIGIN_MAKER, ORIGIN_OTHER):
        origin = primary.origin
    else:
        origin = ORIGIN_MAKER if any(item.origin == ORIGIN_MAKER for item in group) else ORIGIN_UNKNOWN
    publisher, publisher_kind = primary.publisher, primary.publisher_kind
    if not publisher and repository_owner(repository):
        publisher, publisher_kind = repository_owner(repository), "repository"
    description = primary.description or next((item.description for item in group if item.description), "")
    website = primary.website or next((item.website for item in group if item.website), "")
    sources = 0
    for listing in group:
        sources |= SOURCE_BITS[listing.source]
    aliases = sorted({item.key for item in group if item.source in NAMED_SOURCES and item.key != primary.key
                      and item.source != "codex"})
    hints = tuple(item.category_hint for item in group if item.category_hint)
    updated = max((item.updated_at for item in group if item.source == "registry" and item.updated_at), default="")
    return Offering(
        listings=list(group), identity=_identity(primary), name=primary.name or primary.key, description=description,
        publisher=publisher, publisher_kind=publisher_kind if publisher else "unknown",
        category=rules.classify(" ".join([primary.name, primary.key.rsplit("/", 1)[-1]]), description, hints),
        offering_bits=offering,
        origin=origin, locations=tuple(locations), transport_bits=transports, auth_bits=auth,
        licence=licensed.licence if licensed else "", licence_basis=licensed.licence_basis if licensed else "",
        docs=website, repository=repository, source_bits=sources, aliases=tuple(aliases),
        references={item.source: item.reference for item in group}, updated_at=updated)


def sort_key(offering: Offering) -> tuple:
    """The default order: listed in more sources first, then listed by its maker, then by name.

    Only editorial fields are read. The commercial relationship is never part of this key.
    """
    return (-bin(offering.source_bits).count("1"), ORIGIN_RANK.get(offering.origin, 1), 0 if offering.description else 1,
            offering.name.lower().encode("utf-16-be"), offering.identity.encode("utf-16-be"))


def default_order(offerings) -> list:
    return sorted(offerings, key=sort_key)


def part_of(identity: str) -> int:
    """The row file that holds an offering, by a stable digest of its identity."""
    return int(hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8], 16) % PART_COUNT


def _days(timestamp: str) -> int:
    from datetime import date
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", timestamp or "")
    if not match:
        return 0
    return (date(*map(int, match.groups())) - date.fromisoformat(_DAY_ZERO)).days


def encode(offerings, rules: CategoryRules, context: dict) -> "tuple[dict, list]":
    """The manifest and the row files. context names generated_at and each source's checked date."""
    licences = [""] + sorted({item.licence for item in offerings if item.licence})
    relationships = [commercial.NONE] + sorted(
        {item.commercial_relationship for item in offerings if item.commercial_relationship != commercial.NONE},
        key=lambda item: json.dumps(commercial.to_record(item)))
    categories = [identity for identity, _label in rules.labels()]
    parts = [[] for _index in range(PART_COUNT)]
    for item in offerings:
        row = [item.identity, item.name, item.publisher, PUBLISHER_KINDS.index(item.publisher_kind), item.description,
               categories.index(item.category), item.offering_bits, ORIGINS.index(item.origin),
               [[LOCATION_KINDS.index(location.kind), location.value] for location in item.locations],
               item.transport_bits, item.auth_bits, licences.index(item.licence),
               LICENCE_BASES.index(item.licence_basis), item.docs, item.repository,
               REPOSITORY_STATES.index(item.repository_state), item.source_bits, list(item.aliases),
               _days(item.updated_at), relationships.index(item.commercial_relationship)]
        parts[part_of(item.identity)].append(row)
    files = []
    for index, rows in enumerate(parts):
        rows.sort(key=lambda row: row[0])
        files.append({"record_type": ROWS_RECORD_TYPE, "part": index, "rows": rows})
    counts = defaultdict(int)
    for item in offerings:
        counts[item.category] += 1
    manifest = {
        "record_type": MANIFEST_RECORD_TYPE, "generated_at": context["generated_at"], "row_count": len(offerings),
        "columns": list(COLUMNS), "day_zero": _DAY_ZERO,
        "parts": [{"address": part_address(index), "rows": len(rows)} for index, rows in enumerate(parts)],
        "categories": [{"id": identity, "label": label, "rows": counts.get(identity, 0)} for identity, label in rules.labels()],
        "location_kinds": list(LOCATION_KINDS), "publisher_kinds": list(PUBLISHER_KINDS), "origins": list(ORIGINS),
        "offering_bits": OFFERING_BITS, "transport_bits": TRANSPORT_BITS, "auth_bits": AUTH_BITS,
        "licences": licences, "licence_bases": list(LICENCE_BASES), "repository_states": list(REPOSITORY_STATES),
        "sources": [{"id": name, "bit": SOURCE_BITS[name],
                     "rows": sum(1 for item in offerings if item.source_bits & SOURCE_BITS[name]),
                     "checked": context["checked"].get(name, "")} for name in SOURCE_ORDER],
        "commercial_relationship_schema": commercial.SCHEMA,
        "commercial_relationships": [commercial.to_record(item) for item in relationships],
        "commercial_labels": {"kinds": list(commercial.KINDS), "labels": commercial.DISCLOSURE_LABELS,
                              "paid_link_rel": commercial.LINK_REL, "owned_link_rel": commercial.OWNED_LINK_REL,
                              "ad_band_heading": commercial.AD_BAND_HEADING, "maximum_ads": commercial.MAXIMUM_ADS,
                              "paid_link_notice": commercial.PAID_LINK_NOTICE,
                              "paid_links_disclosure": commercial.PAID_LINKS_DISCLOSURE},
    }
    return manifest, files


def part_address(index: int) -> str:
    return f"/assets/directory/rows-{index}.json"


def serialized_part(part: dict) -> str:
    """One row file: its envelope on the first line and one row on each line after it, for small daily changes."""
    rows = part["rows"]
    head = json.dumps({key: value for key, value in part.items() if key != "rows"}, ensure_ascii=False)[:-1]
    body = ",\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows)
    return head + ', "rows": [\n' + body + ("\n" if rows else "") + "]}\n"


class CommercialPlacementError(ValueError):
    """A reviewed commercial relationship names a row it may not be attached to."""


def with_relationships(offerings, relationships: dict) -> list:
    """The same offerings, each with the reviewed commercial relationship named for its identity, or none.

    A relationship other than none goes only on a row whose publisher listed it (origin maker): a paid link on a
    row someone else listed would send a reader somewhere other than the thing listed. A name that matches no row
    is refused too, so a stale review cannot pass unnoticed.
    """
    known = {item.identity: item for item in offerings}
    for identity, relationship in relationships.items():
        if relationship == commercial.NONE:
            continue
        if identity not in known:
            raise CommercialPlacementError(f"the reviewed relationship names {identity!r}, which is not a row")
        if known[identity].origin != ORIGIN_MAKER:
            raise CommercialPlacementError(f"{identity!r} is not listed by its publisher, so it carries no paid link")
    return [replace(item, commercial_relationship=relationships.get(item.identity, commercial.NONE)) for item in offerings]
