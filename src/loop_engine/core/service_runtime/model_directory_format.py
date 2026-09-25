"""Formatting and ordering shared by the model directory pages.

Kind: pure functions. Numbers are written with their unit and, where a source gives them, their
source and date; an unknown value is written "Unknown". Ordering and filtering live here too, and
they read only editorial facts: the check in `tools/test_model_directory.py` changes every
commercial relationship field of every row and requires the same rows in the same order.
"""
from __future__ import annotations

from html import escape

from . import model_directory as records
from . import model_directory_fit as fit

UNKNOWN = "Unknown"
GIB = fit.GIB


def number(value) -> str:
    return f"{value:,}" if isinstance(value, int) and not isinstance(value, bool) else UNKNOWN


def parameters(value) -> str:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return UNKNOWN
    if value >= 10 ** 12:
        return f"{value / 10 ** 12:.2f} trillion"
    if value >= 10 ** 9:
        return f"{value / 10 ** 9:.1f} billion"
    return f"{value / 10 ** 6:.0f} million"


def short_parameters(value) -> str:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return UNKNOWN
    if value >= 10 ** 12:
        return f"{value / 10 ** 12:.1f}T"
    if value >= 10 ** 9:
        return f"{value / 10 ** 9:.1f}B"
    return f"{value / 10 ** 6:.0f}M"


def tokens(value) -> str:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return UNKNOWN
    return f"{value:,}"


def gib(value) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        return UNKNOWN
    amount = value / GIB
    return f"{amount:.1f} GiB" if amount < 100 else f"{amount:,.0f} GiB"


def price(value) -> str:
    """A price per million tokens in US dollars, written with the currency code after the number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        return UNKNOWN
    if value == 0:
        return "0 USD"
    digits = 2 if value >= 1 else 3 if value >= 0.01 else 4
    return f"{value:,.{digits}f} USD"


def fact_value(row: dict, name: str):
    fact = row["facts"].get(name)
    return fact.get("value") if isinstance(fact, dict) else None


def largest(row: dict, name: str):
    values = [item.get("value") for item in row["facts"].get(name) or () if isinstance(item.get("value"), int)]
    return max(values) if values else None


def cheapest_input(row: dict):
    """The cheapest paid input price; a free route counts only when no paid route is listed."""
    prices = [item for item in row["prices"] if isinstance(item.get("input"), (int, float))]
    paid = [item for item in prices if item["input"] > 0 or item["output"] > 0]
    chosen = paid or prices
    return min(chosen, key=lambda item: (item["input"], item["output"], item["provider"])) if chosen else None


def tool_state(row: dict):
    values = [item.get("value") for item in row["facts"].get("tool_calling") or () if isinstance(item.get("value"), bool)]
    return None if not values else any(values)


def uses(row: dict) -> tuple:
    return tuple(item["value"] for item in row["use_cases"])


def released(row: dict) -> str:
    value = fact_value(row, "released")
    return value if isinstance(value, str) else ""


def is_open(row: dict) -> bool:
    return "huggingface" in row["ids"] or fact_value(row, "open_weights") is True


#: The orders a person can choose on the directory page. Each reads only editorial facts.
ORDER_PROVIDERS, ORDER_NEWEST, ORDER_DOWNLOADS, ORDER_NAME = "providers", "newest", "downloads", "name"
ORDERS = (ORDER_PROVIDERS, ORDER_NEWEST, ORDER_DOWNLOADS, ORDER_NAME)


def provider_count(row: dict) -> int:
    """How many providers list a price for the model, directly or through OpenRouter."""
    return len({price["provider_slug"] for price in row["prices"]})
#: The filters a person can choose. A filter keeps rows by a sourced fact and nothing else.
FILTER_ALL, FILTER_OPEN, FILTER_HOSTED = "all", "open", "hosted"


def order_models(rows, order: str = ORDER_PROVIDERS) -> list:
    """The rows in one of the named orders. The default puts the models most providers serve first, newest first among
    equals, then the models no provider lists, most downloaded first."""
    if order == ORDER_PROVIDERS:
        return sorted(rows, key=lambda row: (provider_count(row) == 0, -provider_count(row),
                                             "" if provider_count(row) == 0 else _descending(released(row) or "0000-00-00"),
                                             -((row.get("popularity") or {}).get("downloads") or 0), row["name"].lower(), row["slug"]))
    if order == ORDER_DOWNLOADS:
        return sorted(rows, key=lambda row: (-((row.get("popularity") or {}).get("downloads") or 0), row["name"].lower(), row["slug"]))
    if order == ORDER_NAME:
        return sorted(rows, key=lambda row: (row["name"].lower(), row["slug"]))
    return sorted(rows, key=lambda row: (released(row) == "", "" if not released(row) else _descending(released(row)),
                                         row["name"].lower(), row["slug"]))


def _descending(day: str) -> str:
    return "".join(chr(ord("9") - ord(char) + ord("0")) if char.isdigit() else char for char in day)


def filter_models(rows, use: str = "", weights: str = FILTER_ALL) -> list:
    """The rows with one sourced use case and one weights kind, or every row for an empty filter."""
    kept = []
    for row in rows:
        if use and use not in uses(row):
            continue
        if weights == FILTER_OPEN and not is_open(row):
            continue
        if weights == FILTER_HOSTED and not row["prices"]:
            continue
        kept.append(row)
    return kept


def order_endpoints(rows) -> list:
    """Reviewed endpoints first, in the reviewed order; then the rest by name; local runtimes last."""
    hosted = [row for row in rows if row["kind"] == records.ENDPOINT_HOSTED]
    reviewed = [row for row in hosted if any(item["id"] == "provider_documentation" for item in row["sources"])]
    listed = sorted((row for row in hosted if row not in reviewed), key=lambda row: (row["name"].lower(), row["slug"]))
    local = [row for row in rows if row["kind"] == records.ENDPOINT_LOCAL]
    return reviewed + listed + local


def link(address: str, text: str, external: bool = True) -> str:
    """A link to a stored source address, which never carries a scheme of its own."""
    target = records.source_address(address) if external else address
    return f'<a href="{escape(target)}" rel="noopener">{escape(text)}</a>'


def cite(row: dict, index: int) -> str:
    """The source of one fact: its name as a link, and the day it was read."""
    if not isinstance(index, int) or not 0 <= index < len(row["sources"]):
        return ""
    source = row["sources"][index]
    names = {"huggingface": "Hugging Face", "huggingface_config": "model configuration", "huggingface_gguf": "GGUF files",
             "openrouter": "OpenRouter", "openrouter_endpoints": "OpenRouter endpoints", "modelsdev": "models.dev",
             "baltor_records": "Baltor records", "provider_documentation": "provider documentation",
             "harness_documentation": "harness documentation"}
    return (f'<span class="md-cite">{link(source["address"], names.get(source["id"], source["id"]))}, '
            f'read <time datetime="{source["read"]}">{source["read"]}</time></span>')
