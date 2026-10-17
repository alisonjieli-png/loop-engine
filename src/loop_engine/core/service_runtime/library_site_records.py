"""Read the two packaged records behind the library sites, and refuse them when they disagree.

Kind: passive data validation owned by the existing web presentation boundary. It reads packaged metadata only,
imports no page renderer and no transport, performs no provider call and grants no access.

```text
web_assets/library-sites/
├── hosts.json   website_library_sites/v1, written by people: each library site's copy, its categories, and the
│                exact library identities each category shows
└── items.json   website_library_site_items/v1, written by tools/build_library_sites.py from the served library release:
                 one record for each identity hosts.json names, bound to the release the repository's publication
                 record confirmed, with the selection digest of the hosts.json it was built from
```

The reader refuses an unknown version or field, a duplicate host, category or item address, a category item that the
item record does not hold (an item that is not in the library's catalogue data), an item record entry that no category
shows, an item whose version is not the SHA-256 its identity names, and an item record built for another selection.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

HOSTS_RECORD_TYPE = "website_library_sites/v1"
ITEMS_RECORD_TYPE = "website_library_site_items/v1"
RECORD_FOLDER = "library-sites"
HOSTS_FILE, ITEMS_FILE = "hosts.json", "items.json"
ITEMS_PATH = Path(__file__).with_name("web_assets") / RECORD_FOLDER / ITEMS_FILE
HOST_FIELDS = {"id", "address", "name", "headline", "lede", "why", "card_alt", "rule", "categories"}
CATEGORY_FIELDS = {"slug", "title", "description", "lede", "watch_for", "items", "library_count"}
ITEM_FIELDS = {"identity", "version", "slug", "name", "title", "summary", "kind", "form", "licence", "effects", "harnesses",
               "source", "files", "bytes", "facts", "cases", "notes", "gallery", "family"}
BUILT_FROM_FIELDS = {"evidence", "release_id", "content_digest", "release_items", "confirmed_at", "selection_sha256"}
RULES = {"no_network", "tests_required"}
DESCRIPTION_MAX_CHARACTERS = 160
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ADDRESS = re.compile(r"^/[a-z0-9]+(?:-[a-z0-9]+)*$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)*$")


class LibrarySiteRecordError(ValueError):
    """A library site record this reader refuses, with the reason."""


def _require(condition, reason):
    if not condition:
        raise LibrarySiteRecordError(reason)


def _text(value, where, limit=None, marks="<>\n\r\t"):
    """A trimmed line of text. Copy people write carries no angle brackets; item text may hold them (a formula such
    as M <- M + v), because every renderer escapes it."""
    _require(isinstance(value, str) and value.strip() and value == value.strip(), f"{where} is a trimmed nonempty string")
    _require(limit is None or len(value) <= limit, f"{where} is at most {limit} characters")
    _require(not any(mark in value for mark in marks), f"{where} is one plain line")
    return value


def parse_hosts(text: str) -> dict:
    """The hosts record, or a refusal naming the first problem."""
    record = json.loads(text)
    _require(record.get("record_type") == HOSTS_RECORD_TYPE, f"this reader reads {HOSTS_RECORD_TYPE}")
    _require(set(record) == {"record_type", "decided_on", "decided_by", "hosts", "titles"}, "unknown or missing fields")
    ids, addresses = set(), set()
    for host in record["hosts"]:
        _require(set(host) == HOST_FIELDS, f"host fields: {sorted(set(host) ^ HOST_FIELDS)}")
        _require(_SLUG.match(host["id"]) and host["id"] not in ids, f"host id {host['id']!r} is not a unique slug")
        _require(_ADDRESS.match(host["address"]) and host["address"] not in addresses,
                 f"{host['id']}: {host['address']!r} is not a unique address below the root")
        ids.add(host["id"])
        addresses.add(host["address"])
        for field in ("name", "headline", "lede", "why", "card_alt"):
            _text(host[field], f"{host['id']}.{field}")
        _require(isinstance(host["rule"], dict) and set(host["rule"]) <= RULES
                 and all(value is True for value in host["rule"].values()), f"{host['id']}: unknown rule")
        slugs = set()
        _require(isinstance(host["categories"], list) and host["categories"], f"{host['id']} has categories")
        for category in host["categories"]:
            where = f"{host['id']}/{category.get('slug')}"
            _require(set(category) == CATEGORY_FIELDS, f"{where} fields: {sorted(set(category) ^ CATEGORY_FIELDS)}")
            _require(_SLUG.match(category["slug"]) and category["slug"] not in slugs, f"{where} is not a unique slug")
            slugs.add(category["slug"])
            _text(category["title"], where + ".title")
            _text(category["description"], where + ".description", DESCRIPTION_MAX_CHARACTERS)
            _text(category["lede"], where + ".lede")
            _require(isinstance(category["watch_for"], list) and len(category["watch_for"]) == 3,
                     f"{where} names three things to watch for")
            for line in category["watch_for"]:
                _text(line, where + ".watch_for")
            items = category["items"]
            _require(isinstance(items, list) and 3 <= len(items) <= 24, f"{where} shows 3 to 24 items")
            _require(len(set(items)) == len(items) and all(isinstance(item, str) and _IDENTITY.match(item) for item in items),
                     f"{where} names each item once by its exact identity")
            rule = category["library_count"]
            _require(rule is None or (isinstance(rule, dict) and ("prefixes" in rule or "evidence" in rule)
                                      and isinstance(rule.get("label"), str)), f"{where}: an unknown count rule")
    shown = {identity for host in record["hosts"] for category in host["categories"] for identity in category["items"]}
    _require(isinstance(record["titles"], dict) and set(record["titles"]) <= shown,
             "a title is written for an item no category shows")
    for identity, title in record["titles"].items():
        _text(title, f"titles.{identity}", 90)
    return record


def selection_digest(hosts: dict) -> str:
    """The SHA-256 of what the item record depends on: each category's exact items and count rule and the titles written
    for items, not the hosts' or categories' own copy."""
    selection = [[host["id"], category["slug"], category["items"], category["library_count"]]
                 for host in hosts["hosts"] for category in host["categories"]] + [sorted(hosts["titles"].items())]
    return hashlib.sha256(json.dumps(selection, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def parse_items(text: str, hosts: dict) -> dict:
    """The item record, or a refusal naming the first problem; it must hold exactly the items the hosts show."""
    record = json.loads(text)
    _require(record.get("record_type") == ITEMS_RECORD_TYPE, f"this reader reads {ITEMS_RECORD_TYPE}")
    _require(set(record) == {"record_type", "built_from", "counts", "items"}, "unknown or missing fields")
    built = record["built_from"]
    _require(set(built) == BUILT_FROM_FIELDS, f"built_from fields: {sorted(set(built) ^ BUILT_FROM_FIELDS)}")
    _require(_DIGEST.match(built["release_id"]) and _DIGEST.match(built["content_digest"]), "built_from names digests")
    _require(built["selection_sha256"] == selection_digest(hosts),
             "the item record was built for another selection; run tools/build_library_sites.py")
    by_identity, slugs = {}, set()
    for item in record["items"]:
        _require(set(item) == ITEM_FIELDS, f"item fields: {sorted(set(item) ^ ITEM_FIELDS)}")
        identity = item["identity"]
        _require(_IDENTITY.match(identity) and identity not in by_identity, f"{identity!r} is not a unique identity")
        _require(_DIGEST.match(item["version"]), f"{identity}: the version is not a SHA-256 digest")
        _version(item)
        _require(_SLUG.match(item["slug"]) and item["slug"] not in slugs, f"{identity}: {item['slug']!r} is not a unique address")
        slugs.add(item["slug"])
        for field in ("name", "title", "summary", "licence"):
            _text(item[field], f"{identity}.{field}", marks="\n\r\t")
        _require(all(isinstance(pair, list) and len(pair) == 2 and all(isinstance(value, str) for value in pair)
                     for pair in item["facts"] + item["cases"] + item["notes"]), f"{identity}: facts are label and value")
        _require(all(isinstance(entry, list) and len(entry) == 2 and isinstance(entry[0], str) and type(entry[1]) is int
                     for entry in item["files"]) and item["files"], f"{identity}: files are paths with sizes")
        _require(item["bytes"] == sum(size for _path, size in item["files"]), f"{identity}: the size is not its files' total")
        by_identity[identity] = item
    _membership(hosts, by_identity)
    counted = {f"{host['id']}/{category['slug']}" for host in hosts["hosts"] for category in host["categories"]
               if category["library_count"]}
    _require(set(record["counts"]) == counted and all(type(value) is int and value >= 0 for value in record["counts"].values()),
             "the counts are the counted categories' whole numbers")
    return record


def _version(item) -> None:
    """A supply line's identity ends with the first characters of the version it names; the record must agree."""
    identity = item["identity"]
    if identity.startswith("library.supply."):
        _require(item["version"].startswith(identity.rsplit(".", 1)[-1]), f"{identity}: the version is not the one its identity names")


def _membership(hosts, by_identity) -> None:
    """Every item a category shows is in the item record the build wrote from the served release, and nothing else is."""
    shown = {identity for host in hosts["hosts"] for category in host["categories"] for identity in category["items"]}
    missing, extra = sorted(shown - set(by_identity)), sorted(set(by_identity) - shown)
    _require(not missing, f"a category shows items the library's catalogue data does not hold: {missing}")
    _require(not extra, f"the item record holds items no category shows: {extra}")


def _packaged(name: str) -> str:
    from importlib.resources import files
    return files(__package__).joinpath("web_assets", RECORD_FOLDER, name).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def hosts_record() -> dict:
    return parse_hosts(_packaged(HOSTS_FILE))


@lru_cache(maxsize=1)
def items_record() -> dict:
    return parse_items(_packaged(ITEMS_FILE), hosts_record())


def items_by_identity() -> dict:
    return {item["identity"]: item for item in items_record()["items"]}
