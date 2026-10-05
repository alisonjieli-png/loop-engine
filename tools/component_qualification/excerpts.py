"""How a sampled review presents a large data file: a bounded, deterministic excerpt and what it leaves out.

```text
Data file presentation (rule data_file_excerpt/v1)
├── which files: a text file under a data folder of the qualification policy (data/) larger than 16 KiB;
│   every other file is sent whole, exactly as before
├── what the reviewer reads: a statement (path, media type, size, SHA-256, row count, field inventory, the
│   rows shown and how many are not), then the excerpt, labelled as an excerpt and fenced by the file's digest
└── the excerpt
    ├── delimited text (.csv, .tsv): the header record, then the first 20 and the last 20 data records,
    │   each as the file's own lines (a quoted field may span lines)
    ├── JSON: an array's first 20 and last 20 elements, or an object's first 20 and last 20 members in
    │   file order, each written as compact JSON on a line of its own
    ├── any other text: the first 20 and the last 20 lines
    └── a shown record, element or line longer than 400 characters is cut there and says how much it omits
```

On September 30, 2026 every review call for the batch `data_tables/1.1.0@8ebc4a99e5a6` was refused by the model
gateway before it reached the reviewer: each call held twelve data table packages, each with an upstream data file
of up to 256 KiB sent whole, and their estimated input with the answer allowance did not fit the reviewer's
131,072-token context window, so 0 of 52 sampled tables were answered. An excerpt holds at most
MAXIMUM_EXCERPT_CHARACTERS (19,120) characters whatever the file's size. The request still carries every byte, so
the package digest binds the whole file; the deterministic qualification parsed the whole file (CSV or strict JSON)
and ran its safety rules and secret patterns over all of it, and the supply line ran the package's own tests, which
check every row against its schema.json, before storing it. The reviewer judges the rows shown, the row count and
the field inventory; it does not see the other rows.

Apart from reading the qualification policy's data folders once, everything here is a pure function of the file's
path, declared media type and bytes: the same file always yields the same excerpt, and nothing is written or sent.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
import io
import json
from pathlib import PurePosixPath

from tools.candidate_review.native import TEXT_MEDIA, ReviewExcerpt

RULE = "data_file_excerpt/v1"
#: A data file larger than this is excerpted; a file of this size or smaller is sent whole.
THRESHOLD_BYTES = 16 * 1024
#: Records, elements, members or lines shown from each end of a data file.
SHOWN_AT_EACH_END = 20
#: The longest shown record, element, member or line, in characters.
LONGEST_SHOWN = 400
#: The most fields or columns the inventory names; the rest are counted.
INVENTORY_NAMES = 60
#: The longest excerpt text any file can yield: the header and the shown items, each at most LONGEST_SHOWN
#: characters plus its cut note, and one note for the items not shown, each on a line of its own.
MAXIMUM_EXCERPT_CHARACTERS = (2 * SHOWN_AT_EACH_END + 1) * (LONGEST_SHOWN + 64) + 96
DELIMITERS = {".csv": ",", ".tsv": "\t"}
JSON_TYPES = ((bool, "boolean"), (int, "integer"), (float, "number"), (str, "string"), (list, "array"),
              (dict, "object"), (type(None), "null"))


@lru_cache(maxsize=1)
def policy_data_folders() -> tuple:
    """The data folders the qualification policy declares, so a review and a qualification agree on a data file."""
    from .checks import POLICY_PATH
    return tuple(json.loads(POLICY_PATH.read_text(encoding="utf-8"))["data_folders"])


@dataclass(frozen=True)
class _Shown:
    """What one shape rule found: the shape, the unit it counts, the count, the field inventory, an optional header
    and the shown items as (1-based position, text)."""

    shape: str
    unit: str
    total: int
    inventory: str
    header: "str | None"
    items: tuple


def excerpt_for(entry, payload: bytes, data_folders=None) -> "ReviewExcerpt | None":
    """The excerpt a reviewer reads in place of one package file, or None when the file is sent whole."""
    folders = policy_data_folders() if data_folders is None else tuple(data_folders)
    parts = PurePosixPath(entry.path).parts
    if len(parts) < 2 or parts[0] not in folders or len(payload) <= THRESHOLD_BYTES:
        return None
    if entry.media_type not in TEXT_MEDIA:
        return None  # a declared binary file stays a binary file; the prompt says it was not read as text
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None
    suffix = PurePosixPath(entry.path).suffix.lower()
    shown = (_delimited(text, DELIMITERS[suffix]) if suffix in DELIMITERS
             else _json(text) if suffix == ".json" else None) or _lines(text)
    return ReviewExcerpt(RULE, _statement(entry, len(payload), shown), _text(shown))


def _cut(text: str) -> str:
    if len(text) <= LONGEST_SHOWN:
        return text
    return text[:LONGEST_SHOWN] + f" <<< cut here: {len(text) - LONGEST_SHOWN:,} more characters not shown >>>"


def _ends(values) -> tuple:
    """The first and the last SHOWN_AT_EACH_END values with their 1-based positions; all of them when few."""
    values = list(values)
    if len(values) <= 2 * SHOWN_AT_EACH_END:
        return tuple(enumerate(values, 1))
    tail = len(values) - SHOWN_AT_EACH_END
    return tuple(enumerate(values[:SHOWN_AT_EACH_END], 1)) + tuple(
        (position, value) for position, value in enumerate(values[tail:], tail + 1))


def _names(names, more: str) -> str:
    names = list(names)
    shown = ", ".join(name[:80] for name in names[:INVENTORY_NAMES])
    return shown + (f", and {len(names) - INVENTORY_NAMES:,} {more}" if len(names) > INVENTORY_NAMES else "")


def _delimited(text: str, delimiter: str) -> "_Shown | None":
    """Records read the way the csv module reads them, each kept as the file's own lines."""
    lines = list(io.StringIO(text, newline=""))
    reader = csv.reader(iter(lines), delimiter=delimiter)
    records, start = [], 0
    try:
        for fields in reader:
            end = reader.line_num
            if fields:
                records.append((fields, "".join(lines[start:end]).rstrip("\r\n")))
            start = end
    except csv.Error:
        return None
    if not records:
        return None
    header, rows = records[0], records[1:]
    uneven = sum(1 for fields, _text in rows if len(fields) != len(header[0]))
    inventory = f"{len(header[0])} columns: {_names(header[0], 'more columns')}" + (
        f"; {uneven:,} data records have another number of fields than the header" if uneven else "")
    name = "comma-separated" if delimiter == "," else "tab-separated"
    return _Shown(f"{name} text with a header record", "data records", len(rows), inventory, _cut(header[1]),
                  tuple((position, _cut(record)) for position, (_fields, record) in _ends(rows)))


def _type_name(value) -> str:
    return next(name for kind, name in JSON_TYPES if isinstance(value, kind))


def _object_inventory(values) -> str:
    """Every field the objects hold, in the order fields first appear, with every JSON type it takes."""
    fields = {}
    for value in values:
        for name, field in value.items():
            kinds = fields.setdefault(name, [])
            kind = _type_name(field)
            if kind not in kinds:
                kinds.append(kind)
    return f"{len(fields)} fields: " + _names((f"{name} ({', '.join(kinds)})" for name, kinds in fields.items()),
                                             "more fields")


def _value_inventory(values) -> str:
    values = list(values)
    if values and all(isinstance(value, dict) for value in values):
        return _object_inventory(values)
    counts = {}
    for value in values:
        counts[_type_name(value)] = counts.get(_type_name(value), 0) + 1
    return "value types: " + ", ".join(f"{name} {count:,}" for name, count in counts.items())


def _compact(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json(text: str) -> "_Shown | None":
    try:
        document = json.loads(text)
    except ValueError:
        return None
    if isinstance(document, list):
        return _Shown("a JSON array", "elements", len(document), _value_inventory(document), None,
                      tuple((position, _cut(_compact(value))) for position, value in _ends(document)))
    if isinstance(document, dict):
        members = list(document.items())
        return _Shown("a JSON object", "members", len(members), _value_inventory(document.values()), None,
                      tuple((position, _cut(_compact(key) + ":" + _compact(value)))
                            for position, (key, value) in _ends(members)))
    return None


def _lines(text: str) -> _Shown:
    lines = text.splitlines()
    return _Shown("text", "lines", len(lines), "no fields are read from plain text", None,
                  tuple((position, _cut(line)) for position, line in _ends(lines)))


def _text(shown: _Shown) -> str:
    out = [] if shown.header is None else [shown.header]
    previous = 0
    for position, item in shown.items:
        if position != previous + 1:
            out.append(f"<<< {position - previous - 1:,} {shown.unit} not shown: {previous + 1:,} to "
                       f"{position - 1:,} >>>")
        out.append(item)
        previous = position
    return "\n".join(out)


def _statement(entry, size: int, shown: _Shown) -> str:
    positions = [position for position, _item in shown.items]
    runs, start = [], None
    for index, position in enumerate(positions):
        if start is None:
            start = position
        if index + 1 == len(positions) or positions[index + 1] != position + 1:
            runs.append(f"{start:,}" if start == position else f"{start:,} to {position:,}")
            start = None
    hidden = shown.total - len(positions)
    if runs:
        listed = ("the header record and " if shown.header is not None else "") + f"{shown.unit} {' and '.join(runs)}"
    else:
        listed = "the header record only" if shown.header is not None else f"no {shown.unit}"
    cut = (f" A shown {shown.unit[:-1]} longer than {LONGEST_SHOWN} characters is cut where it says so.")
    return (f"The file is {entry.media_type}, {size:,} bytes, SHA-256 {entry.digest}: {shown.shape} of "
            f"{shown.total:,} {shown.unit}; {shown.inventory}. Shown: {listed}; {hidden:,} {shown.unit} are not "
            f"shown.{cut} The request carries every byte of the file, bound by its digest, and the deterministic "
            "qualification parsed the whole file and ran its safety rules and secret patterns over all of it.")
