"""Addresses the directory stopped serving: where each moved, or why it is gone.

Kind: development tool module with pure functions. A daily build compares the rows it replaces with the
rows it writes. An address of a model or endpoint page that is no longer served gets one entry: moved,
with the live address it now has, or gone, with the reason. The service answers a moved address with a
permanent redirect and a gone one with 410 Gone and a way back, so a public address never answers
"not found" after the directory has served it.

An old model row moved only when the new rows say so exactly, in this order:

1. a new row carries one of the old row's identifiers, ignoring case: its Hugging Face repository, its
   models.dev identifier, or an identifier from a source no longer read when a new row names the model
   with the same string, which covers a page whose address changed while its model stayed;
2. a new hosted row is the maker's own models.dev entry that the old row priced: the old row's direct
   price names the same provider address part and the same model identifier as the new row's own
   maker price;
3. the old row's address was its identifier's address with a number added, because another row's
   identifier made the same address, and that other row still has the address.

Nothing is matched on a similar name. Anything else is gone. Earlier entries are kept: an entry whose
address is live again is dropped, and an entry that points at an address that later moved or went is
followed to where that address ends, so no redirect leads to a page that does not answer.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from loop_engine.core.service_runtime import model_directory as records

from .rows import slug_of

MODEL_PREFIX, ENDPOINT_PREFIX = "/models/", "/endpoints/"
#: Why an address is gone. The service writes the sentence for each reason; the record keeps only the code.
GONE_REFUSED_SOURCE = "refused_source"
GONE_NOT_LISTED = "not_listed"
#: How an address was found to have moved, kept with each entry so a reader can check it.
MOVED_SAME_IDENTIFIER = "same_identifier"
MOVED_MAKER_PRICE = "maker_price"
MOVED_SHARED_ADDRESS = "shared_address"


def read_rows(folder: Path, name: str, key: str) -> list:
    """The rows of a packaged file of an earlier build, of any record version, or an empty list."""
    path = Path(folder) / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = value.get(key) if isinstance(value, dict) else None
    return [row for row in rows or () if isinstance(row, dict) and isinstance(row.get("slug"), str)]


def read_record(folder: Path) -> dict:
    """The moved-address record of an earlier build, or an empty one."""
    try:
        value = json.loads((Path(folder) / records.MOVED_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"moved": [], "gone": []}
    return value if isinstance(value, dict) and value.get("record_type") == records.MOVED_RECORD_TYPE else {"moved": [], "gone": []}


def _identifiers(row: dict) -> list:
    """The identifiers a row names, each as its source wrote it, with a variant after a colon left off."""
    return [value.split(":", 1)[0] for value in (row.get("ids") or {}).values() if isinstance(value, str) and value]


def _maker_prices(row: dict) -> set:
    """(provider address part, lowercase model identifier) of each direct price a row lists."""
    return {(price.get("provider_slug"), str(price.get("model_id") or "").lower()) for price in row.get("prices") or ()
            if price.get("route") == records.ROUTE_DIRECT and price.get("provider_slug") and price.get("model_id")}


def _hosted_key(row: dict) -> "tuple | None":
    """(provider address part, lowercase model identifier) of a hosted row's own maker price, or None."""
    identifier = (row.get("ids") or {}).get("modelsdev")
    if not isinstance(identifier, str) or "huggingface" in (row.get("ids") or {}):
        return None
    model = identifier.partition("/")[2].lower()
    own = [price for price in row.get("prices") or () if str(price.get("model_id") or "").lower() == model]
    return (own[0]["provider_slug"], model) if own else None


def _found_move(old: dict, current: list, by_identifier: dict, by_maker_price: dict, live: set) -> "tuple | None":
    """(new slug, how) when the current rows say exactly where an old model row went, or None."""
    for identifier in _identifiers(old):
        found = by_identifier.get(identifier.lower())
        if found:
            return found, MOVED_SAME_IDENTIFIER
    targets = {by_maker_price[key] for key in _maker_prices(old) if key in by_maker_price}
    if len(targets) == 1:
        return targets.pop(), MOVED_MAKER_PRICE
    for identifier in _identifiers(old):
        shared = slug_of(identifier)
        if shared and shared in live and re.fullmatch(re.escape(shared) + r"-[0-9]+", old["slug"]):
            return shared, MOVED_SHARED_ADDRESS
    return None


def _gone_reason(old: dict) -> str:
    named = {item.get("id") for item in old.get("sources") or () if isinstance(item, dict)}
    return GONE_REFUSED_SOURCE if named & set(records.REFUSED_SOURCES) else GONE_NOT_LISTED


def updated_record(previous_models: list, previous_endpoints: list, models: list, endpoints: list,
                   previous_record: dict, today: str) -> dict:
    """The moved-address record after one build: earlier entries followed to where they end, and one entry for each
    address the previous build served and this build does not."""
    live = {MODEL_PREFIX + row["slug"] for row in models} | {ENDPOINT_PREFIX + row["slug"] for row in endpoints}
    model_slugs = {row["slug"] for row in models}
    by_identifier = {}
    for row in models:
        for identifier in _identifiers(row):
            by_identifier.setdefault(identifier.lower(), row["slug"])
    by_maker_price: dict = {}
    for row in models:
        key = _hosted_key(row)
        if key is not None:
            by_maker_price.setdefault(key, set()).add(row["slug"])
    by_maker_price = {key: next(iter(slugs)) for key, slugs in by_maker_price.items() if len(slugs) == 1}
    moved = {item["from"]: dict(item) for item in previous_record.get("moved") or () if isinstance(item, dict)}
    gone = {item["address"]: dict(item) for item in previous_record.get("gone") or () if isinstance(item, dict)}
    for old in previous_models:
        address = MODEL_PREFIX + old["slug"]
        if address in live or address in moved or address in gone:
            continue
        found = _found_move(old, models, by_identifier, by_maker_price, model_slugs)
        if found is not None:
            moved[address] = {"from": address, "to": MODEL_PREFIX + found[0], "since": today, "how": found[1]}
        else:
            gone[address] = {"address": address, "since": today, "reason": _gone_reason(old)}
    for old in previous_endpoints:
        address = ENDPOINT_PREFIX + old["slug"]
        if address not in live and address not in moved and address not in gone:
            gone[address] = {"address": address, "since": today, "reason": _gone_reason(old)}
    for address in [address for address in moved if address in live]:
        del moved[address]
    for address in [address for address in gone if address in live]:
        del gone[address]
    for address, item in list(moved.items()):
        target, seen = item["to"], {address}
        while target in moved and target not in seen:
            seen.add(target)
            target = moved[target]["to"]
        if target in live:
            item["to"] = target
        else:
            end = gone.get(target)
            del moved[address]
            gone[address] = {"address": address, "since": today, "reason": end["reason"] if end else GONE_NOT_LISTED}
    return {"record_type": records.MOVED_RECORD_TYPE,
            "moved": [moved[key] for key in sorted(moved)], "gone": [gone[key] for key in sorted(gone)]}
