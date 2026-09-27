"""Line data_tables: one reference data table per declared file, copied byte for byte, with schema, loader and tests.

```text
One table (declared in data_table_sources.json: repository, branch, path, shape, key field)
├── pinned: the branch's head commit, the file's git blob identity, its bytes proven by that identity
├── licence: GitHub's licence interface and the licence text at that commit agree on an allowlisted
│   licence; the text travels as UPSTREAM-LICENSE beside the copy
├── rows: the declared shape read as rows (records, keyed records, a mapping or a list of values);
│   a file that does not hold that shape, an empty table, a key that repeats or collides with a
│   field, and a file above the review bound are refused by name
└── one package (kind code_module, form data_table)
    ├── data/<file>: the upstream file byte for byte
    ├── schema.json: the JSON Schema of one row, derived from every row (types per field, the
    │   fields every row holds are required), the key field and the row count
    ├── <table>_table.py: rows(), index() and lookup(key); it refuses a data file whose SHA-256 is
    │   not the recorded one and a row that breaks the schema
    ├── test_<table>_table.py: every row passes, keys are unique, and known-wrong rows, keys and a
    │   changed data file are refused
    └── README.md, LICENSE (generated code, MIT), UPSTREAM-LICENSE, ATTRIBUTION.md
```
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath

from .licences import repository_licence
from .openapi_operations import literal, run_tests
from .packaging import (
    LICENCE_NAME, MAXIMUM_REVIEW_FILE_BYTES, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build)
from .reading import RAW_HOST, github_blob_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, DATA_TABLES, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT,
    REFUSAL_REASONS, UPSTREAM_VERBATIM, SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
SOURCES_FILE = Path(__file__).with_name("data_table_sources.json")
SOURCES_RECORD_TYPE = "library_supply_data_table_sources/v1"
SHAPES = ("records", "keyed_records", "mapping", "values")
NATIVE_FORMAT = "reference_data_table"
HOSTS = (RAW_HOST,)
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{1,60}\Z")
#: The JSON Schema dialect every table's schema.json declares (the standard's own identifier).
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


class TableRefused(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


def read_sources(path: Path = SOURCES_FILE) -> list:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD_TYPE:
        raise ValueError(f"expected {SOURCES_RECORD_TYPE}")
    rows, seen = [], set()
    for table_id, title, repository, branch, file_path, shape, key_field, value_field in record["tables"]:
        if (table_id in seen or not _IDENTIFIER.match(table_id) or shape not in SHAPES
                or not isinstance(key_field, str) or not key_field
                or (shape == "mapping") != (value_field is not None)):
            raise ValueError(f"data_table_sources.json: the row of {table_id} is not a declared table")
        seen.add(table_id)
        rows.append({"table_id": table_id, "title": title, "repository": repository, "branch": branch,
                     "path": file_path, "shape": shape, "key_field": key_field, "value_field": value_field})
    return rows


def json_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def table_rows(document, shape: str, key_field: str, value_field: "str | None") -> list:
    """The rows the declared shape holds, or refuse a document of another shape or with colliding keys."""
    if shape == "records":
        if not isinstance(document, list) or not all(isinstance(row, dict) for row in document):
            raise TableRefused("row_violates_schema", "the file is not a list of objects")
        table = [dict(row) for row in document]
    elif shape == "keyed_records":
        if not isinstance(document, dict) or not all(isinstance(value, dict) for value in document.values()):
            raise TableRefused("row_violates_schema", "the file is not an object of objects")
        if any(key_field in value and value[key_field] != key for key, value in document.items()):
            raise TableRefused("row_violates_schema", f"a row's own {key_field} differs from its key")
        table = [{key_field: key, **{name: item for name, item in value.items() if name != key_field}}
                 for key, value in document.items()]
    elif shape == "mapping":
        if not isinstance(document, dict):
            raise TableRefused("row_violates_schema", "the file is not an object")
        table = [{key_field: key, value_field: value} for key, value in document.items()]
    else:
        if not isinstance(document, list) or any(isinstance(value, (dict, list)) for value in document):
            raise TableRefused("row_violates_schema", "the file is not a list of values")
        table = [{key_field: value} for value in document]
    if not table:
        raise TableRefused("table_empty", "the table holds no row")
    keys = [row.get(key_field) for row in table]
    if any(key is None or isinstance(key, (dict, list)) for key in keys):
        raise TableRefused("row_violates_schema", f"a row has no scalar {key_field}")
    repeated = [key for key, count in Counter(keys).items() if count > 1]
    if repeated:
        raise TableRefused("row_violates_schema", f"the key {key_field} repeats: {repeated[:3]}")
    return table


def infer_schema(table: list) -> tuple:
    """(fields with their JSON types, required fields), in the order fields first appear."""
    fields, counts = {}, Counter()
    for row in table:
        for name, value in row.items():
            kinds = fields.setdefault(name, [])
            kind = json_type(value)
            if kind not in kinds:
                kinds.append(kind)
            counts[name] += 1
    required = [name for name in fields if counts[name] == len(table)]
    return {name: sorted(kinds) for name, kinds in fields.items()}, required


LOADER = '''"""{title}: a typed reference table of {count} rows.

Loaded from data/{file_name}, a byte-for-byte copy of {repository}
at commit {commit} ({path}), licensed {licence}.
Baltor generated this loader, schema.json and the tests; see README.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / {file_name!r}
DATA_SHA256 = {sha256!r}
KEY_FIELD = {key_field!r}
{value_line}#: Each field and the JSON types its values take; a field outside this map is refused.
FIELDS = {fields}
REQUIRED = {required}
ROW_COUNT = {count}
_CACHE = {{}}


def _is(value, kind):
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, {{"boolean": bool, "string": str, "array": list, "object": dict,
                              "null": type(None)}}.get(kind, object))


def check_row(row):
    """Refuse a row that is not an object, lacks a required field, names an unknown field or holds a value of
    another type."""
    if not isinstance(row, dict):
        raise TypeError("a row is an object")
    missing = [name for name in REQUIRED if name not in row]
    if missing:
        raise ValueError(f"the row lacks {{missing}}")
    for name, value in row.items():
        kinds = FIELDS.get(name)
        if kinds is None:
            raise ValueError(f"{{name}} is not a field of this table")
        if not any(_is(value, kind) for kind in kinds):
            raise TypeError(f"{{name}} must be {{' or '.join(kinds)}}, not {{type(value).__name__}}")
    return row


def rows():
    """Every row in the upstream order, each checked; the data file must be the recorded bytes."""
    if "rows" not in _CACHE:
        data = DATA_FILE.read_bytes()
        if hashlib.sha256(data).hexdigest() != DATA_SHA256:
            raise ValueError(f"{{DATA_FILE.name}} is not the recorded file (SHA-256 {{DATA_SHA256}})")
        document = json.loads(data.decode("utf-8"))
        {shape_line}
        _CACHE["rows"] = [check_row(row) for row in table]
    return [dict(row) for row in _CACHE["rows"]]


def index():
    """The rows by their key."""
    return {{row[KEY_FIELD]: row for row in rows()}}


def lookup(key):
    """The row whose key is the given value; KeyError when the table has none."""
    found = index()
    if key not in found:
        raise KeyError(key)
    return found[key]
'''

SHAPE_LINES = {
    "records": "table = [dict(row) for row in document]",
    "keyed_records": "table = [{KEY_FIELD: key, **{name: item for name, item in value.items() if name != KEY_FIELD}}\n"
                     "                 for key, value in document.items()]",
    "mapping": "table = [{KEY_FIELD: key, VALUE_FIELD: value} for key, value in document.items()]",
    "values": "table = [{KEY_FIELD: value} for value in document]"}

TESTS = '''"""Offline tests of the {table_id} table.

Every row passes the schema and keys are unique; known-wrong rows, a missing key and a changed data file are
refused.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import {module} as table  # noqa: E402


class {class_name}(unittest.TestCase):
    def setUp(self):
        table._CACHE.clear()

    def tearDown(self):
        table._CACHE.clear()

    def test_every_row_passes_the_schema_and_keys_are_unique(self):
        rows = table.rows()
        self.assertEqual(len(rows), table.ROW_COUNT)
        self.assertEqual(len(table.index()), table.ROW_COUNT)

    def test_lookup_finds_a_known_row(self):
        self.assertEqual(table.lookup({first_key!r})[table.KEY_FIELD], {first_key!r})

    def test_known_wrong_a_missing_key_raises(self):
        with self.assertRaises(KeyError):
            table.lookup({missing_key!r})

    def test_known_wrong_rows_that_break_the_schema_are_refused(self):
        row = table.rows()[0]
        with self.assertRaises(ValueError):
            table.check_row({{name: value for name, value in row.items() if name != table.KEY_FIELD}})
        with self.assertRaises(TypeError):
            table.check_row({{**row, table.KEY_FIELD: {wrong_key!r}}})
        with self.assertRaises(ValueError):
            table.check_row({{**row, "not_a_field_of_this_table": 1}})

    def test_known_wrong_a_changed_data_file_is_refused(self):
        original = table.DATA_FILE
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / original.name
            shutil.copyfile(original, changed)
            changed.write_bytes(changed.read_bytes() + b"\\n")
            table.DATA_FILE = changed
            try:
                with self.assertRaises(ValueError):
                    table.rows()
            finally:
                table.DATA_FILE = original


if __name__ == "__main__":
    unittest.main()
'''


def readme(row: dict, pinned: dict, licence_spdx: str, table: list, fields: dict, required: list, module: str,
           file_name: str) -> str:
    lines = [f"| `{name}` | {' or '.join(kinds)} | {'yes' if name in required else 'no'} |"
             for name, kinds in fields.items()]
    examples = json.dumps(table[:3], indent=1, ensure_ascii=False)
    first = table[0][row["key_field"]]
    return f"""# {row['title']}

{len(table)} rows from `{row['repository']}` at commit `{pinned['commit']}`, file `{row['path']}`
(SHA-256 `{pinned['sha256']}`), licensed {licence_spdx}. The file is copied byte for byte to
`data/{file_name}`; Baltor generated the loader, `schema.json` and the tests.

## Fields

The key is `{row['key_field']}`; every key is unique.

| Field | Type | In every row |
|---|---|---|
{chr(10).join(lines)}

## First rows

```json
{examples}
```

## Use

```python
import {module}

rows = {module}.rows()           # every row, checked against the schema
row = {module}.lookup({first!r})
```

The loader refuses a data file whose SHA-256 is not the recorded one and a
row that lacks a required field, names an unknown field or holds a value of
another type.

```bash
python -m unittest test_{module}
```
"""


def _wrong_key(kinds: list):
    return 12345 if "string" in kinds else "not a key of this table"


def _missing_key(table: list, key_field: str, kinds: list):
    keys = {row[key_field] for row in table}
    candidate = "__not_a_key_of_this_table__" if "string" in kinds else -987654321
    while candidate in keys:
        candidate = candidate + "_" if isinstance(candidate, str) else candidate - 1
    return candidate


def generate(reader, rows, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             repository_facts: dict) -> tuple:
    """(built, refusals, facts) of every declared table."""
    built, refused, facts = [], [], {}
    generator = {"identity": "tools/supply_lines/data_tables.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    licences = {}
    for row in rows:
        try:
            pinned = reader.pinned_file(row["repository"], row["branch"], row["path"])
        except LookupError as error:
            refused.append(refusal(DATA_TABLES, "source_unreadable", row["table_id"], str(error)))
            continue
        facts[pinned["sha256"]] = pinned["bytes"]
        key = (row["repository"], pinned["commit"])
        if key not in licences:
            licences[key] = repository_licence(reader, row["repository"], pinned["commit"])
        licence = licences[key]
        if not licence.allowed:
            reason = licence.refusal_reason(REFUSAL_REASONS[DATA_TABLES])
            refused.append(refusal(DATA_TABLES, reason, row["table_id"], f"{licence.reason} {licence.github_spdx}"))
            continue
        if len(pinned["bytes"]) > MAXIMUM_REVIEW_FILE_BYTES:
            refused.append(refusal(DATA_TABLES, "table_above_review_bound", row["table_id"],
                                   f"{len(pinned['bytes'])} bytes"))
            continue
        try:
            built.append(_package(row, pinned, licence, generator, licence_text, generated_on, staging,
                                  repository_facts))
        except TableRefused as error:
            refused.append(refusal(DATA_TABLES, error.reason, row["table_id"], error.detail))
        except SupplyRecordError as error:
            reason = error.code if error.code == BLOCKED_BY_STATIC_CHECK else GENERATED_TEST_FAILED
            refused.append(refusal(DATA_TABLES, reason, row["table_id"], str(error)[:280]))
    return built, refused, facts


def _package(row, pinned, licence, generator, licence_text, generated_on, staging, repository_facts):
    try:
        document = json.loads(pinned["bytes"].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise TableRefused("source_unreadable", f"not JSON: {type(error).__name__}") from None
    table = table_rows(document, row["shape"], row["key_field"], row["value_field"])
    fields, required = infer_schema(table)
    file_name = PurePosixPath(row["path"]).name
    module = f"{row['table_id']}_table"
    value_line = f"VALUE_FIELD = {row['value_field']!r}\n" if row["shape"] == "mapping" else ""
    loader = LOADER.format(title=row["title"], count=len(table), file_name=file_name, repository=row["repository"],
                           commit=pinned["commit"], path=row["path"], licence=licence.spdx, sha256=pinned["sha256"],
                           key_field=row["key_field"], value_line=value_line, fields=literal(fields, 0),
                           required=literal(required), shape_line=SHAPE_LINES[row["shape"]])
    key_kinds = fields[row["key_field"]]
    class_name = "".join(part.capitalize() for part in row["table_id"].split("_")) + "TableTest"
    tests = TESTS.format(table_id=row["table_id"], module=module, class_name=class_name,
                         first_key=table[0][row["key_field"]], missing_key=_missing_key(table, row["key_field"], key_kinds),
                         wrong_key=_wrong_key(key_kinds))
    schema = {"$schema": JSON_SCHEMA_DIALECT, "title": row["title"], "type": "object",
              "properties": {name: {"type": kinds if len(kinds) > 1 else kinds[0]} for name, kinds in fields.items()},
              "required": required, "additionalProperties": False,
              "x-baltor-table": {"key_field": row["key_field"], "rows": len(table), "shape": row["shape"],
                                 "data_file": f"data/{file_name}", "data_sha256": pinned["sha256"]}}
    schema_text = json.dumps(schema, indent=1, ensure_ascii=False) + "\n"
    folder = staging / module
    (folder / "data").mkdir(parents=True, exist_ok=True)
    (folder / "data" / file_name).write_bytes(pinned["bytes"])
    (folder / f"{module}.py").write_text(loader, encoding="utf-8")
    (folder / f"test_{module}.py").write_text(tests, encoding="utf-8")
    passed, count, output = run_tests(folder, module)
    if not passed:
        raise SupplyRecordError("generated_test_failed", output[-280:])
    text = readme(row, pinned, licence.spdx, table, fields, required, module, file_name)
    files = [PackageFile(f"data/{file_name}", pinned["bytes"], "other", UPSTREAM_VERBATIM,
                         {"url": pinned["url"], "sha256": pinned["sha256"]}),
             PackageFile("schema.json", schema_text.encode(), "other"),
             PackageFile(f"{module}.py", loader.encode(), "executable_tool"),
             PackageFile(f"test_{module}.py", tests.encode(), "executable_tool"),
             PackageFile("README.md", text.encode(), "other"),
             PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
             PackageFile(UPSTREAM_LICENCE_NAME, licence.text, "other", LICENCE_TEXT,
                         {"url": github_blob_address(row["repository"], pinned["commit"], licence.path),
                          "sha256": licence.sha256})]
    expression = GENERATED_CODE_LICENCE if licence.spdx == GENERATED_CODE_LICENCE else \
        f"{licence.spdx} AND {GENERATED_CODE_LICENCE}"
    facts = [fact_source(pinned["url"], pinned["retrieved_at"], pinned["sha256"], len(pinned["bytes"]), "data_source",
                         spdx=licence.spdx, basis="github_licence_interface_and_text_agree",
                         evidence_sha256=licence.sha256),
             fact_source(github_blob_address(row["repository"], pinned["commit"], licence.path),
                         pinned["retrieved_at"], licence.sha256, len(licence.text), "licence_text", spdx=licence.spdx,
                         basis="licence_file_at_the_pinned_commit")]
    name = f"{row['table_id'].replace('_', '-')}-table"
    stars = ((repository_facts.get(row["repository"].lower()) or {}).get("stargazerCount")) or 0
    supply = SupplyPackage(
        line=DATA_TABLES, identity=f"{row['repository']}:{row['path']}",
        key=upstream_key(DATA_TABLES, f"{row['repository']}:{row['path']}"), kind="code_module",
        native_format=NATIVE_FORMAT, form="data_table", name=name,
        description=f"{row['title']}: {len(table)} rows with a JSON Schema, a checked loader and tests.",
        files=files, licence_expression=expression,
        provenance=provenance("github_repository", row["repository"], row["path"], pinned["commit"], facts,
                              generator),
        placements=[{"harness": "reference", "path": f"tools/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=[("reads_fs", "the loader reads its data file")], credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False},
        repository={"name": row["repository"], "stars": stars, "rows": len(table), "fields": len(fields),
                    "table_id": row["table_id"]},
        generated_on=generated_on, comparison_text=f"{row['repository']}:{row['path']}")
    return build(supply)
