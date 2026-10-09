"""Local profile of one downloaded dataset folder: every file with its size, SHA-256 and format, and a schema
profile of every table, computed from the folder's own bytes.

```text
profile_dataset(folder)
├── files: every regular file under the folder in path order (a symbolic link is followed and marked), each with its
│   size, SHA-256, modification time and format by suffix; a folder holding more than MAXIMUM_LISTED_FILES files keeps
│   its format counts and the digest of its whole file list instead of one row per file
├── tables, one per file of a table format, read in the same streamed pass that digests the file
│   ├── delimited text (.csv, .tsv): the delimiter is the suffix's or the one among , ; tab | that splits the first
│   │   records into the most columns of one width; the record count covers every record, column statistics the
│   │   records within the profile bound, and the profile basis says which
│   ├── JSON lines (.jsonl, .ndjson): one object a line; its keys are the columns, with the JSON type of each value
│   └── JSON (.json) up to MAXIMUM_JSON_BYTES: an array of objects is a table; another document is named with its
│       top-level keys and not profiled
├── per column: values present, empty values and their share, null-like words (NULL, NaN, N/A) counted apart, the
│   narrowest type every present value takes (boolean, integer, number, ISO date, ISO date-time, text), the minimum
│   and maximum, text lengths, and each value with its count while at most MAXIMUM_ENUMERATED distinct values appear
└── not profiled, by format: spreadsheets, geospatial layers, images, models, archives, documents, partial
    downloads, and a table file whose first bytes are a saved web page
```

Nothing here decides a licence or a goal and nothing leaves the machine; the line reads these profiles. Text is
decoded as UTF-8 (a byte-order mark is noted); bytes that are not UTF-8 are replaced and counted, never guessed.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
import os
import re
from collections import Counter
from pathlib import Path, PurePosixPath

PROFILE_RECORD = "kaggle_dataset_profile/v1"
PROFILER_VERSION = "1.0.0"
#: Table formats this module profiles, and the formats it names without profiling.
(DELIMITED, JSON_LINES, JSON_DOCUMENT, SPREADSHEET, GEOSPATIAL, IMAGE, MODEL_OR_BINARY, DOCUMENT, SOURCE_CODE,
 PARTIAL_DOWNLOAD, DATABASE, WEB_PAGE, ARCHIVE, OTHER) = FORMATS = (
    "delimited_text", "json_lines", "json", "spreadsheet", "geospatial", "image", "model_or_binary", "document",
    "source_code", "partial_download", "database", "web_page", "archive", "other")
TABLE_FORMATS = (DELIMITED, JSON_LINES, JSON_DOCUMENT)
FORMAT_BY_SUFFIX = {
    ".csv": DELIMITED, ".tsv": DELIMITED, ".jsonl": JSON_LINES, ".ndjson": JSON_LINES, ".json": JSON_DOCUMENT,
    ".xlsx": SPREADSHEET, ".xls": SPREADSHEET, ".shp": GEOSPATIAL, ".shx": GEOSPATIAL, ".dbf": GEOSPATIAL,
    ".prj": GEOSPATIAL, ".sbn": GEOSPATIAL, ".sbx": GEOSPATIAL, ".cpg": GEOSPATIAL, ".geojson": GEOSPATIAL,
    ".kml": GEOSPATIAL, ".gdbtable": GEOSPATIAL, ".gdbtablx": GEOSPATIAL, ".gdbindexes": GEOSPATIAL,
    ".atx": GEOSPATIAL, ".freelist": GEOSPATIAL, ".spx": GEOSPATIAL, ".horizon": GEOSPATIAL,
    ".png": IMAGE, ".jpg": IMAGE, ".jpeg": IMAGE, ".gif": IMAGE, ".webp": IMAGE,
    ".safetensors": MODEL_OR_BINARY, ".pb": MODEL_OR_BINARY, ".pkl": MODEL_OR_BINARY, ".index": MODEL_OR_BINARY,
    ".bin": MODEL_OR_BINARY, ".npy": MODEL_OR_BINARY, ".parquet": MODEL_OR_BINARY,
    ".pdf": DOCUMENT, ".docx": DOCUMENT, ".md": DOCUMENT, ".txt": DOCUMENT, ".cff": DOCUMENT, ".qmd": DOCUMENT,
    ".rst": DOCUMENT, ".yaml": DOCUMENT, ".yml": DOCUMENT, ".xml": DOCUMENT,
    ".py": SOURCE_CODE, ".js": SOURCE_CODE, ".ts": SOURCE_CODE, ".map": SOURCE_CODE, ".mjs": SOURCE_CODE,
    ".ipynb": SOURCE_CODE, ".m": SOURCE_CODE, ".r": SOURCE_CODE, ".sh": SOURCE_CODE,
    ".crdownload": PARTIAL_DOWNLOAD, ".part": PARTIAL_DOWNLOAD, ".db": DATABASE, ".sqlite": DATABASE,
    ".html": WEB_PAGE, ".htm": WEB_PAGE, ".zip": ARCHIVE, ".gz": ARCHIVE, ".tar": ARCHIVE, ".7z": ARCHIVE}
#: Files named without a suffix that are documentation (a licence, a notice).
DOCUMENT_NAMES = ("license", "licence", "notice", "copying", "readme", "authors")
#: Delimiters a delimited file may use; a .tsv file uses the tab.
DELIMITERS = (",", ";", "\t", "|")
SUFFIX_DELIMITERS = {".tsv": "\t"}
#: Bytes read to choose a delimiter, and the records the choice looks at.
SNIFF_BYTES, SNIFF_RECORDS = 64 * 1024, 40
#: Column statistics stop after this many bytes of a table (the record count still covers every byte).
DEFAULT_PROFILE_BYTES = 64 * 1024 * 1024
#: A JSON document above this size is digested but not parsed.
MAXIMUM_JSON_BYTES = 64 * 1024 * 1024
#: Values listed with their counts while a column holds at most this many distinct values.
MAXIMUM_ENUMERATED = 24
#: A listed value longer than this is cut, with its length kept.
MAXIMUM_VALUE_CHARACTERS = 120
#: Files listed one by one in a profile; a larger folder keeps counts and a digest of its file list.
MAXIMUM_LISTED_FILES = 400
#: The largest delimited field read, so a field holding a whole JSON response does not stop the reader.
MAXIMUM_FIELD_CHARACTERS = 64 * 1024 * 1024
#: Words some publishers write for a missing value; counted beside the empty values, never typed as missing.
NULL_LIKE_WORDS = ("NULL", "null", "None", "NaN", "nan", "N/A", "n/a", "NA", "#N/A")
CHUNK_BYTES = 1024 * 1024
UTF8_MARK = b"\xef\xbb\xbf"
#: The value kinds of a delimited cell and of a JSON value, and the column types they combine into.
(BOOLEAN, INTEGER, NUMBER, DATE, DATE_TIME, TEXT, NULL, ARRAY, OBJECT) = VALUE_KINDS = (
    "boolean", "integer", "number", "date", "date_time", "text", "null", "array", "object")
EMPTY_COLUMN = "empty"
_INTEGER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DATE_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,9})?)?"
                        r"(?:Z|[+-][0-9]{2}:?[0-9]{2})?")
_BOOLEAN_WORDS = ("true", "false")
#: A number written with a leading zero (an identifier such as 007.5) is text.
_LEADING_ZERO = re.compile(r"[+-]?0[0-9]")
_WEB_PAGE_START = (b"<!doctype html", b"<html")


class ProfileError(ValueError):
    """A folder that cannot be profiled as a dataset, with a stable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def file_format(path: str) -> str:
    """The format of one file by its suffix (a name without one is documentation when it names a licence)."""
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    if suffix in FORMAT_BY_SUFFIX:
        return FORMAT_BY_SUFFIX[suffix]
    if name.startswith("data-") and "-of-" in name:
        return MODEL_OR_BINARY
    if not suffix and name.split(".")[0] in DOCUMENT_NAMES:
        return DOCUMENT
    return OTHER


def utc_time(seconds: float) -> str:
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _DigestingReader(io.RawIOBase):
    """A binary reader that digests every byte it hands on, so one pass both profiles and pins a file."""

    def __init__(self, handle) -> None:
        super().__init__()
        self.handle = handle
        self.digest = hashlib.sha256()
        self.size = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        count = self.handle.readinto(buffer)
        if count:
            self.digest.update(memoryview(buffer)[:count])
            self.size += count
        return count or 0

    def drain(self) -> None:
        while True:
            chunk = self.handle.read(CHUNK_BYTES)
            if not chunk:
                return
            self.digest.update(chunk)
            self.size += len(chunk)


def cell_kind(text: str) -> str:
    """The narrowest kind one non-empty delimited cell takes. An integer with a leading zero (a postal code, an
    identifier) is text, so its zeros are never lost."""
    if text.lower() in _BOOLEAN_WORDS:
        return BOOLEAN
    if _INTEGER.fullmatch(text):
        return INTEGER
    if _NUMBER.fullmatch(text) and not _LEADING_ZERO.match(text):
        return NUMBER if math.isfinite(float(text)) else TEXT
    if _DATE.fullmatch(text):
        return DATE if _valid_date(text) else TEXT
    if _DATE_TIME.fullmatch(text):
        return DATE_TIME if _valid_date(text[:10]) else TEXT
    return TEXT


def json_kind(value) -> str:
    """The kind of one JSON value; a string is a date or date-time when it is one in ISO 8601."""
    if value is None:
        return NULL
    if isinstance(value, bool):
        return BOOLEAN
    if isinstance(value, int):
        return INTEGER
    if isinstance(value, float):
        return NUMBER
    if isinstance(value, list):
        return ARRAY
    if isinstance(value, dict):
        return OBJECT
    if _DATE.fullmatch(value) and _valid_date(value):
        return DATE
    if _DATE_TIME.fullmatch(value) and _valid_date(value[:10]):
        return DATE_TIME
    return TEXT


def _valid_date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text[:10])
    except ValueError:
        return False
    return True


def column_type(kinds) -> str:
    """The narrowest type that every present value of a column takes."""
    kinds = set(kinds) - {NULL}
    if not kinds:
        return EMPTY_COLUMN
    for candidate, members in ((BOOLEAN, {BOOLEAN}), (INTEGER, {INTEGER}), (NUMBER, {INTEGER, NUMBER}),
                               (DATE, {DATE}), (DATE_TIME, {DATE, DATE_TIME}), (ARRAY, {ARRAY}),
                               (OBJECT, {OBJECT})):
        if kinds <= members:
            return candidate
    return TEXT


class ColumnStatistics:
    """What one column's values show: counts, kinds, range, lengths and the values while they are few."""

    def __init__(self, name: str, position: int) -> None:
        self.name, self.position = name, position
        self.present = self.empty = 0
        self.null_like = Counter()
        self.kinds = Counter()
        self.minimum = self.maximum = None
        self.shortest = self.longest = None
        self.values = Counter()
        self.overflow = False

    def add_text(self, text: str) -> None:
        if not text:
            self.empty += 1
            return
        self.present += 1
        if text in NULL_LIKE_WORDS:
            self.null_like[text] += 1
        kind = cell_kind(text)
        self.kinds[kind] += 1
        self._range(kind, text)
        self._length(len(text))
        self._value(text)

    def add_json(self, value) -> None:
        kind = json_kind(value)
        if kind == NULL:
            self.empty += 1
            return
        self.present += 1
        self.kinds[kind] += 1
        if kind in (INTEGER, NUMBER):
            self._range(kind, value)
        elif kind in (DATE, DATE_TIME, TEXT):
            self._range(kind, value)
            self._length(len(value))
        if kind in (ARRAY, OBJECT):
            self._length(len(value))
            self.overflow = True
        else:
            self._value(value)

    def _range(self, kind: str, value) -> None:
        if kind in (INTEGER, NUMBER):
            number = value if not isinstance(value, str) else (int(value) if kind == INTEGER else float(value))
        elif kind in (DATE, DATE_TIME):
            number = value
        else:
            return
        if self.minimum is None or _less(number, self.minimum):
            self.minimum = number
        if self.maximum is None or _less(self.maximum, number):
            self.maximum = number

    def _length(self, length: int) -> None:
        self.shortest = length if self.shortest is None else min(self.shortest, length)
        self.longest = length if self.longest is None else max(self.longest, length)

    def _value(self, value) -> None:
        if self.overflow:
            return
        if value in self.values or len(self.values) < MAXIMUM_ENUMERATED:
            self.values[value] += 1
        else:
            self.overflow = True
            self.values.clear()

    def to_dict(self, rows: int) -> dict:
        """The column's profile over ``rows`` records; a record that holds no value for the column at all (a short
        delimited record, a JSON object without the key) counts as absent, apart from an empty value."""
        kind = column_type(self.kinds)
        absent = max(0, rows - self.present - self.empty)
        row = {"name": self.name, "position": self.position, "present": self.present, "empty": self.empty,
               "absent": absent, "empty_share": round((self.empty + absent) / rows, 6) if rows else 0.0,
               "type": kind, "kinds": dict(sorted(self.kinds.items()))}
        if self.null_like:
            row["null_like"] = dict(sorted(self.null_like.items()))
        if kind in (INTEGER, NUMBER, DATE, DATE_TIME) and self.minimum is not None:
            # A range is reported only for a column whose every present value has a comparable kind.
            row["minimum"], row["maximum"] = _plain(self.minimum), _plain(self.maximum)
        if self.shortest is not None:
            row["length"] = {"minimum": self.shortest, "maximum": self.longest}
        if not self.overflow and self.values:
            row["values"] = [{"value": _shown(value), "count": count} for value, count in
                             sorted(self.values.items(), key=lambda item: (-item[1], str(item[0])))]
        row["distinct"] = len(self.values) if not self.overflow and self.present else None
        return row


def _less(left, right) -> bool:
    try:
        return left < right
    except TypeError:
        return str(left) < str(right)


def _plain(value):
    if isinstance(value, float):
        return round(value, 9) if math.isfinite(value) else None
    return value


def _shown(value):
    if isinstance(value, str) and len(value) > MAXIMUM_VALUE_CHARACTERS:
        return value[:MAXIMUM_VALUE_CHARACTERS] + f"... ({len(value)} characters)"
    return value


def choose_delimiter(sample: str, suffix: str) -> "str | None":
    """The delimiter that splits the sample's records into the most columns of one consistent width."""
    if suffix in SUFFIX_DELIMITERS:
        return SUFFIX_DELIMITERS[suffix]
    best, best_width = None, 1
    lines = sample.splitlines(keepends=True)
    if len(sample) >= SNIFF_BYTES and len(lines) > 1:
        lines = lines[:-1]  # the last line of a cut sample may be cut too
    text = "".join(lines)
    for delimiter in DELIMITERS:
        try:
            records = [record for _, record in zip(range(SNIFF_RECORDS), csv.reader(io.StringIO(text, newline=""),
                                                                                       delimiter=delimiter))
                       if record]
        except csv.Error:
            continue
        if not records:
            continue
        width = len(records[0])
        consistent = sum(1 for record in records if len(record) == width)
        if width > best_width and consistent >= max(1, int(0.9 * len(records))):
            best, best_width = delimiter, width
    return best


def _header_problems(header: list) -> list:
    problems = []
    for position, name in enumerate(header):
        if not name.strip():
            problems.append(f"column {position + 1} has no name")
    for name, count in Counter(header).items():
        if name.strip() and count > 1:
            problems.append(f"the name {name!r} repeats {count} times")
    return problems


def profile_delimited(path: Path, *, profile_bytes: int = DEFAULT_PROFILE_BYTES) -> tuple:
    """(table profile, SHA-256, size) of a delimited text file, from one streamed pass over its bytes."""
    with open(path, "rb") as handle:
        start = handle.read(SNIFF_BYTES)
        handle.seek(0)
        if start.lstrip()[:16].lower().startswith(_WEB_PAGE_START):
            reader = _DigestingReader(handle)
            reader.drain()
            return {"format": WEB_PAGE, "profiled": False, "reason": "the file holds a saved web page, not a table"}, \
                reader.digest.hexdigest(), reader.size
        marked = start.startswith(UTF8_MARK)
        sample = start.decode("utf-8-sig", "replace")
        delimiter = choose_delimiter(sample, PurePosixPath(path.name).suffix.lower())
        raw = _DigestingReader(handle)
        buffered = io.BufferedReader(raw, CHUNK_BYTES)
        text = io.TextIOWrapper(buffered, encoding="utf-8-sig", errors="replace", newline="")
        table = {"format": DELIMITED, "delimiter": delimiter, "profiled": True,
                 "encoding": "utf-8 with byte-order mark" if marked else "utf-8"}
        if delimiter is None:
            raw.drain()
            table.update(profiled=False, reason="no delimiter splits the first records into columns of one width")
            return table, raw.digest.hexdigest(), raw.size
        saved_limit = csv.field_size_limit()
        csv.field_size_limit(MAXIMUM_FIELD_CHARACTERS)
        try:
            records = csv.reader(text, delimiter=delimiter)
            try:
                header = next(records)
            except StopIteration:
                table.update(profiled=False, reason="the file holds no header record", records=0)
                return table, raw.digest.hexdigest(), raw.size
            columns = [ColumnStatistics(name, position) for position, name in enumerate(header)]
            count = profiled = ragged = blank = 0
            replaced = 0
            try:
                for record in records:
                    if not record:
                        blank += 1
                        continue
                    count += 1
                    if raw.size <= profile_bytes:
                        profiled += 1
                        if len(record) != len(header):
                            ragged += 1
                        for column, value in zip(columns, record):
                            column.add_text(value)
                            if "�" in value:
                                replaced += 1
                    elif len(record) != len(header):
                        ragged += 1
            except csv.Error as error:
                table["parse_error"] = f"record {count + 1}: {str(error)[:160]}"
            raw.drain()
        finally:
            csv.field_size_limit(saved_limit)
        if replaced:
            table["encoding"] = f"not utf-8: {replaced} profiled values hold replaced bytes"
        table.update(header=list(header), header_problems=_header_problems(header), records=count,
                     records_basis="every record" if "parse_error" not in table else "records before the parse error",
                     profiled_records=profiled,
                     profile_basis="every record" if profiled == count else f"the first {profiled} records "
                                                                              f"({profile_bytes} bytes bound)",
                     ragged_records=ragged, blank_lines=blank,
                     columns=[column.to_dict(profiled) for column in columns])
        return table, raw.digest.hexdigest(), raw.size


def profile_json_lines(path: Path, *, profile_bytes: int = DEFAULT_PROFILE_BYTES) -> tuple:
    """(table profile, SHA-256, size) of a JSON lines file: every line an object, its keys the columns."""
    digest, size = hashlib.sha256(), 0
    columns, order = {}, []
    count = profiled = not_objects = 0
    parse_error = None
    with open(path, "rb") as handle:
        for line in handle:
            digest.update(line)
            size += len(line)
            if not line.strip():
                continue
            count += 1
            if size > profile_bytes or parse_error:
                continue
            try:
                value = json.loads(line)
            except ValueError as error:
                parse_error = f"line {count}: {str(error)[:160]}"
                continue
            if not isinstance(value, dict):
                not_objects += 1
                continue
            profiled += 1
            for name, item in value.items():
                if name not in columns:
                    columns[name] = ColumnStatistics(name, len(order))
                    order.append(name)
                columns[name].add_json(item)
    table = {"format": JSON_LINES, "profiled": True, "encoding": "utf-8", "records": count,
             "records_basis": "every non-empty line", "profiled_records": profiled,
             "profile_basis": "every record" if profiled + not_objects == count and not parse_error
             else f"the first {profiled} records", "not_objects": not_objects}
    if parse_error:
        table["parse_error"] = parse_error
    table["columns"] = [columns[name].to_dict(profiled) for name in order]
    table["header"] = list(order)
    return table, digest.hexdigest(), size


def profile_json(path: Path) -> tuple:
    """(table profile, SHA-256, size) of a JSON document: a list of objects is a table, anything else is named."""
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) > MAXIMUM_JSON_BYTES:
        return {"format": JSON_DOCUMENT, "profiled": False, "reason": "above the JSON parse bound"}, digest, len(data)
    try:
        value = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as error:
        return {"format": JSON_DOCUMENT, "profiled": False, "reason": f"not JSON: {str(error)[:120]}"}, digest, \
            len(data)
    if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
        columns, order = {}, []
        for row in value:
            for name, item in row.items():
                if name not in columns:
                    columns[name] = ColumnStatistics(name, len(order))
                    order.append(name)
                columns[name].add_json(item)
        return {"format": JSON_DOCUMENT, "profiled": True, "shape": "array_of_objects", "records": len(value),
                "records_basis": "every element", "profiled_records": len(value), "profile_basis": "every record",
                "header": list(order), "columns": [columns[name].to_dict(len(value)) for name in order]}, digest, \
            len(data)
    keys = sorted(value)[:40] if isinstance(value, dict) else []
    shape = "object" if isinstance(value, dict) else type(value).__name__
    return {"format": JSON_DOCUMENT, "profiled": False, "shape": shape, "top_level_keys": keys,
            "reason": "a JSON document that is not an array of objects"}, digest, len(data)


def file_digest(path: Path) -> tuple:
    digest, size = hashlib.sha256(), 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def dataset_files(folder: Path) -> list:
    """Every regular file under the folder, as (relative POSIX path, absolute path, is a link), in path order."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ProfileError("folder_missing", str(folder))
    rows, seen = [], set()
    for base, directories, names in os.walk(folder, followlinks=True):
        real = os.path.realpath(base)
        if real in seen:
            directories[:] = []
            continue
        seen.add(real)
        directories.sort()
        for name in sorted(names):
            path = Path(base) / name
            if path.is_file():
                rows.append((path.relative_to(folder).as_posix(), path, path.is_symlink()))
    return sorted(rows)


def profile_dataset(folder: Path, *, profile_bytes: int = DEFAULT_PROFILE_BYTES) -> dict:
    """The profile of one dataset folder: its files and its tables (see the module tree)."""
    folder = Path(folder)
    files, tables, formats = [], [], Counter()
    total = 0
    latest = 0.0
    for relative, path, linked in dataset_files(folder):
        kind = file_format(relative)
        stat = path.stat()
        latest = max(latest, stat.st_mtime)
        if kind == DELIMITED:
            table, digest, size = profile_delimited(path, profile_bytes=profile_bytes)
        elif kind == JSON_LINES:
            table, digest, size = profile_json_lines(path, profile_bytes=profile_bytes)
        elif kind == JSON_DOCUMENT:
            table, digest, size = profile_json(path)
        else:
            table = None
            digest, size = file_digest(path)
        if table is not None:
            if table.get("format") != kind:
                kind = table["format"]
            tables.append({"file": relative, "sha256": digest, "size_bytes": size, **table})
        formats[kind] += 1
        total += size
        files.append({"path": relative, "size_bytes": size, "sha256": digest, "format": kind,
                      "modified_at": utc_time(stat.st_mtime), **({"link": True} if linked else {})})
    listing = hashlib.sha256(json.dumps([(row["path"], row["sha256"]) for row in files]).encode()).hexdigest()
    record = {"record_type": PROFILE_RECORD, "profiler_version": PROFILER_VERSION, "folder": folder.name,
              "files_total": len(files), "bytes_total": total, "formats": dict(sorted(formats.items())),
              "file_list_sha256": listing, "latest_modified_at": utc_time(latest) if files else None,
              "tables": tables, "files_listed": len(files) <= MAXIMUM_LISTED_FILES}
    if len(files) <= MAXIMUM_LISTED_FILES:
        record["files"] = files
    else:
        # A folder of thousands of images keeps the files a reader needs: tables, documents and source code.
        record["files"] = [row for row in files if row["format"] in TABLE_FORMATS + (DOCUMENT,)][:MAXIMUM_LISTED_FILES]
    return record


def cache_key(folder: Path, profile_bytes: int = DEFAULT_PROFILE_BYTES) -> str:
    """The identity of a folder's bytes for a profile cache: every file's path, size and modification time, the
    profiler version and the profile bound."""
    rows = []
    for relative, path, _linked in dataset_files(folder):
        stat = path.stat()
        rows.append((relative, stat.st_size, stat.st_mtime_ns))
    return hashlib.sha256(json.dumps([PROFILER_VERSION, profile_bytes, rows]).encode()).hexdigest()


def cached_profile(folder: Path, cache: "Path | None", *, profile_bytes: int = DEFAULT_PROFILE_BYTES) -> dict:
    """The folder's profile, read from the cache when its files are unchanged, else computed and cached.

    A cached profile is reused only under the same key (paths, sizes, modification times, profiler version and
    bound); the digests inside it were computed from the bytes, so a reader that needs certainty re-profiles."""
    folder = Path(folder)
    if cache is None:
        return profile_dataset(folder, profile_bytes=profile_bytes)
    key = cache_key(folder, profile_bytes)
    target = Path(cache) / f"{folder.name}.{key[:24]}.json"
    if target.is_file():
        return json.loads(target.read_text(encoding="utf-8"))
    record = profile_dataset(folder, profile_bytes=profile_bytes)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial")
    partial.write_text(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    partial.replace(target)
    return record


def _profile_task(arguments) -> tuple:
    folder, cache, profile_bytes = arguments
    try:
        return folder, cached_profile(Path(folder), Path(cache) if cache else None, profile_bytes=profile_bytes), None
    except (OSError, ProfileError) as error:
        return folder, None, f"{type(error).__name__}: {str(error)[:200]}"


def profile_folders(folders, *, cache: "Path | None", workers: int = 1,
                    profile_bytes: int = DEFAULT_PROFILE_BYTES) -> dict:
    """{folder name: (profile or None, error or None)} for each folder, profiled in ``workers`` processes."""
    tasks = [(str(folder), str(cache) if cache else None, profile_bytes) for folder in folders]
    results = {}
    if workers <= 1:
        for task in tasks:
            folder, record, error = _profile_task(task)
            results[Path(folder).name] = (record, error)
        return results
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for folder, record, error in pool.map(_profile_task, tasks):
            results[Path(folder).name] = (record, error)
    return results


__all__ = ["PROFILE_RECORD", "PROFILER_VERSION", "FORMATS", "TABLE_FORMATS", "VALUE_KINDS", "EMPTY_COLUMN",
           "ProfileError", "file_format", "cell_kind", "json_kind", "column_type", "choose_delimiter",
           "profile_delimited", "profile_json_lines", "profile_json", "profile_dataset", "dataset_files", "cache_key",
           "cached_profile", "profile_folders", "utc_time", "DEFAULT_PROFILE_BYTES", "MAXIMUM_ENUMERATED"]
