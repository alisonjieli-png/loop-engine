"""Small helpers shared by the model and endpoint assembly: sources, slugs, names and prices.

Kind: development tool module with pure functions. A RowSources object collects the sources of one
row, each with its address and the day it was read, and hands back the index that a fact names.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from loop_engine.core.service_runtime import commercial_relationship as commercial

PER_MILLION = 1_000_000


class RowSources:
    """The sources of one row, in the order they were first named."""

    def __init__(self) -> None:
        self.items: list = []
        self._index: dict = {}

    def add(self, source_id: str, address: str, read_on: str) -> int:
        key = (source_id, address)
        if key not in self._index:
            self._index[key] = len(self.items)
            self.items.append({"id": source_id, "address": address, "read": read_on})
        return self._index[key]


def slug_of(identifier: str) -> str:
    """A lowercase address part from an identifier: letters and digits joined by single hyphens."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", identifier.lower())).strip("-")[:120].strip("-")


def unique_slugs(identifiers: list) -> dict:
    """identifier -> slug, with a number added in sorted identifier order when two identifiers share a slug."""
    taken: dict = {}
    result = {}
    for identifier in sorted(identifiers):
        base = slug_of(identifier) or "model"
        slug, number = base, 2
        while slug in taken:
            slug, number = f"{base}-{number}", number + 1
        taken[slug] = identifier
        result[identifier] = slug
    return result


def split_openrouter_name(name: str) -> tuple:
    """OpenRouter writes "Maker: Model". Returns (maker, model name), or ("", name) without a colon."""
    maker, separator, model = name.partition(": ")
    return (maker.strip(), model.strip()) if separator and model.strip() else ("", name.strip())


def record_day(value, fallback: str) -> str:
    """A source's own date when it is a real calendar date of this century, else the fallback."""
    from datetime import date
    if isinstance(value, str) and re.match(r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]$", value):
        try:
            date.fromisoformat(value)
            return value
        except ValueError:
            return fallback
    return fallback


def day_of_epoch(seconds) -> str:
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds <= 0:
        return ""
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%d")


def per_million(value) -> "float | None":
    """A per-token price string as a price per million tokens, or None when unknown or not a price."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return round(number * PER_MILLION, 6)


def scheme_free(address) -> str:
    """An https address without its scheme, or an empty string for anything else."""
    if not isinstance(address, str):
        return ""
    found = re.match(r"^https://([^\s@]+)$", address.strip())
    return found.group(1) if found else ""


def variable_parts(name: str) -> list:
    """A published variable name as the parts a page joins with an underscore, split before its kind."""
    found = re.match(r"^([A-Z0-9_]+?)_((?:API_)?KEY|TOKEN|ACCESS_TOKEN|AUTH_TOKEN|SECRET)$", name or "")
    return [found.group(1), found.group(2)] if found else [name] if name else []


def no_relationship() -> dict:
    """Every row ships without a commercial relationship until the owner approves a programme."""
    return commercial.to_record(commercial.NONE)
