"""Personal data masker: find and replace personal identifiers in free text, with an inventory of what was masked.

Detected categories: email addresses, web addresses, IPv4 addresses, payment card numbers (13 to 19 digits that
pass the Luhn check), phone numbers (7 to 15 digits in common groupings), dates (ISO, month/day/year, day.month.year
and written months), United States social security number shapes, ZIP codes (only when asked), names from a supplied
list or after an honorific (Mr, Mrs, Ms, Dr, Prof), and custom patterns with a label. Overlapping matches keep the
earliest, then the longest. The same value always gets the same numbered placeholder. Positions refer to the
original text; the values themselves are not returned. A pure function of its JSON input; the command line reads
standard input and writes standard output.
"""
from __future__ import annotations

import re

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "invalid_pattern": "a custom pattern is not a valid regular expression or matches empty text",
    "label_invalid": "a custom pattern label clashes with a built-in category",
}
#: Also the priority order when two matches start at the same place with the same length.
CATEGORIES = ("email", "url", "ip_address", "card_number", "id_number", "date", "phone", "postal_code", "name")
DEFAULT = ("email", "url", "ip_address", "card_number", "id_number", "date", "phone", "name")
INPUT_SCHEMA = {
    "type": "object", "required": ["text"], "additionalProperties": False,
    "properties": {
        "text": {"type": "string", "maxLength": 500000, "description": "free text to mask"},
        "categories": {"type": "array", "items": {"enum": list(CATEGORIES)}, "uniqueItems": True,
                       "description": "categories to mask (default all but postal_code)"},
        "names": {"type": "array", "items": {"type": "string", "minLength": 2}, "maxItems": 5000,
                  "description": "known names to mask wherever they appear as whole words"},
        "custom_patterns": {"type": "array", "maxItems": 50, "description": "extra identifiers: label and pattern",
                            "items": {"type": "object", "required": ["label", "pattern"], "additionalProperties": False,
                                      "properties": {"label": {"type": "string", "pattern": "^[a-z][a-z0-9_]{1,30}$"},
                                                     "pattern": {"type": "string", "minLength": 1}}}},
        "style": {"enum": ["numbered", "label"],
                  "description": "numbered gives [EMAIL_1] per distinct value; label gives [EMAIL] (default numbered)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["masked_text", "inventory", "findings", "categories_checked"],
    "properties": {
        "masked_text": {"type": "string"},
        "inventory": {"type": "object", "description": "category to count of masked occurrences"},
        "findings": {"type": "array", "description": "category, start, end (original text offsets), placeholder",
                     "items": {"type": "object", "required": ["category", "start", "end", "placeholder"]}},
        "categories_checked": {"type": "array", "items": {"type": "string"}},
    },
}
_MONTHS = ("January|February|March|April|May|June|July|August|September|October|November|December|"
           "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "url": re.compile(r"https?://[^\s<>\"']+"),
    "ip_address": re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
    "card_number": re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
    "id_number": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "date": re.compile(r"(?<!\d)(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}\.\d{1,2}\.\d{4})(?!\d)"
                       r"|\b(?:" + _MONTHS + r")\.? \d{1,2}(?:st|nd|rd|th)?,? \d{4}\b"
                       r"|\b\d{1,2} (?:" + _MONTHS + r")\.? \d{4}\b"),
    "phone": re.compile(r"(?<![\w+])(?:\+\d{1,3}[ .-]?)?(?:\(\d{1,4}\)[ .-]?)?\d{2,4}(?:[ .-]\d{2,4}){1,3}(?![\w])"),
    "postal_code": re.compile(r"(?<!\d)\d{5}(?:-\d{4})?(?!\d)"),
    "name": re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof)\.? [A-Z][a-z]+(?: [A-Z][a-z]+)?"),
}


def luhn_valid(digits: str) -> bool:
    total = 0
    for position, character in enumerate(reversed(digits)):
        value = int(character)
        if position % 2 == 1:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def keep(category: str, value: str) -> bool:
    """Category-specific checks that remove look-alikes."""
    if category == "ip_address":
        return all(0 <= int(part) <= 255 for part in value.split("."))
    if category == "card_number":
        digits = re.sub(r"\D", "", value)
        return 13 <= len(digits) <= 19 and luhn_valid(digits)
    if category == "phone":
        digits = re.sub(r"\D", "", value)
        return 7 <= len(digits) <= 15
    return True


def find(text: str, categories: list, names: list, custom: list) -> list:
    """(start, end, category, value) for every candidate match before overlap resolution."""
    found = []
    order = {category: index for index, category in enumerate(CATEGORIES)}
    for category in categories:
        for match in PATTERNS[category].finditer(text):
            value = match.group().rstrip(".,;:!?)]}") if category == "url" else match.group()
            if value and keep(category, value):
                found.append((match.start(), match.start() + len(value), category, value))
    if "name" in categories:
        for name in sorted(set(names), key=len, reverse=True):
            for match in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE):
                found.append((match.start(), match.end(), "name", match.group()))
    for label, pattern in custom:
        for match in pattern.finditer(text):
            if match.end() > match.start():
                found.append((match.start(), match.end(), label, match.group()))
    found.sort(key=lambda row: (row[0], -(row[1] - row[0]), order.get(row[2], len(order))))
    chosen, end = [], -1
    for row in found:
        if row[0] >= end:
            chosen.append(row)
            end = row[1]
    return chosen


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    text = payload["text"]
    categories = list(payload.get("categories", DEFAULT))
    custom = []
    for row in payload.get("custom_patterns", []):
        if row["label"] in CATEGORIES:
            raise KitRefusal("label_invalid", row["label"])
        try:
            pattern = re.compile(row["pattern"])
        except re.error as error:
            raise KitRefusal("invalid_pattern", f"{row['label']}: {error}") from None
        if pattern.fullmatch(""):
            raise KitRefusal("invalid_pattern", f"{row['label']}: matches empty text")
        custom.append((row["label"], pattern))
    matches = find(text, categories, payload.get("names", []), custom)
    style = payload.get("style", "numbered")
    numbers, pieces, findings, inventory, cursor = {}, [], [], {}, 0
    for start, end, category, value in matches:
        key = (category, value.casefold())
        if key not in numbers:
            numbers[key] = sum(1 for other in numbers if other[0] == category) + 1
        placeholder = f"[{category.upper()}]" if style == "label" else f"[{category.upper()}_{numbers[key]}]"
        pieces.append(text[cursor:start])
        pieces.append(placeholder)
        cursor = end
        findings.append({"category": category, "start": start, "end": end, "placeholder": placeholder})
        inventory[category] = inventory.get(category, 0) + 1
    pieces.append(text[cursor:])
    return {"masked_text": "".join(pieces), "inventory": dict(sorted(inventory.items())), "findings": findings,
            "categories_checked": categories + [label for label, _pattern in custom]}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
