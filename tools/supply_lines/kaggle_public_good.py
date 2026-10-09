"""Line kaggle_public_good: one package per downloaded Kaggle dataset whose own files grant an allowlisted licence, with
its schema contract, typed loader, tests and SDG proposal; every other dataset is inventoried and held by name.

```text
kaggle_public_good (one package per licensable dataset folder of a local Kaggle download)
├── facts, all local and pinned by SHA-256: the folder's files (kaggle_profile.py, one streamed pass per file), the
│   download's backup-manifest.json (the account that owns the datasets), and the dataset's Kaggle address built
│   from them; no network address is read and no model is called
├── licence, decided from the dataset's own files (licence_decision)
│   ├── a licence file whose full text matches a licence template (MIT, Apache-2.0) or whose statement names one
│   │   licence by an exact phrase of kaggle_public_good_sources.json (CC BY 4.0, CC BY-SA 4.0, ODbL ...)
│   ├── the licence field of the dataset's Croissant record, citation file or Kaggle metadata file
│   ├── its documentation and table headers only when it has neither (a README's licence section, a terms-of-use
│   │   column name)
│   ├── a declared decision of the sources file for mixed terms, bound to the licence file's SHA-256 and to the
│   │   paths that stay absent
│   └── held by name: licence_unknown, licence_not_on_allowlist, licence_signals_disagree, licence_mixed_terms,
│       licence_permission_required, declared_decision_stale; the Kaggle record itself is not read
├── SDG goals, targets and indicators by a rule that is data (kaggle_sdg_rules.json), each with its matched phrase
├── tables: every profiled table of the folder; the shards of one family (name-00001.jsonl) and its train,
│   validation and test splits with the same columns are one table; a table that is not rectangular (ragged
│   records, unnamed or repeated columns) is left out with its reason
└── one package per licensable dataset with at least one table (kind code_module, form data_table)
    ├── component.json, the contract card a harness reads first (job.source and job.identity are the job key)
    ├── schema.json: JSON Schema 2020-12 with one $defs entry per table, and the profile under x-baltor-dataset
    ├── <dataset>.py: DATASET, TABLES and DATA_FILES written into the shared standard-library reader
    │   (kaggle_files/kaggle_dataset_loader.py), which checks every row of a file the caller names
    ├── test_dataset_contract.py (kaggle_files/, shared) and fixtures/: synthetic rows per table, with known-wrong
    │   controls (a value of the wrong type or a ragged record, a missing column, an unknown column)
    ├── data/: the dataset's own tables byte for byte when its licence allows it and the review bounds hold
    │   (256 KiB a file, 2 MiB and 64 files a package); dropped, with the reason in the card, when the static
    │   checks block them
    └── README.md (the dataset card), LICENSE (MIT, the generated code), UPSTREAM-LICENSE (the licence's legal
        code), SOURCE-LICENSE (the dataset's own licence file, verbatim) and ATTRIBUTION.md
```

A package is a candidate until qualification and the ongoing independent review; its SDG goals are a proposal.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from collections import Counter
from pathlib import Path, PurePosixPath

from loop_engine.core.library_ingestion.licences import match_licence

from . import kaggle_profile, kaggle_sdg
from .data_tables import JSON_SCHEMA_DIALECT
from .packaging import (LICENCE_NAME, MAXIMUM_REVIEW_FILE_BYTES, MAXIMUM_REVIEW_PACKAGE_BYTES, UPSTREAM_LICENCE_NAME,
                        PackageFile, SupplyPackage, build)
from .reading import https_address
from .records import (BLOCKED_BY_STATIC_CHECK, GENERATED, GENERATED_CODE_LICENCE, KAGGLE_PUBLIC_GOOD, LICENCE_EVIDENCE,
                      LICENCE_TEXT, PACKAGE_ABOVE_REVIEW_BOUND, UPSTREAM_VERBATIM, SupplyRecordError, fact_source,
                      provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
HERE = Path(__file__).resolve().parent
SOURCES_FILE = HERE / "kaggle_public_good_sources.json"
SDG_RULES_FILE = HERE / "kaggle_sdg_rules.json"
FILES_FOLDER = HERE / "kaggle_files"
LOADER_SOURCE = FILES_FOLDER / "kaggle_dataset_loader.py"
CONTRACT_TESTS_SOURCE = FILES_FOLDER / "test_dataset_contract.py"
CONTRACT_TESTS_NAME = "test_dataset_contract.py"
POLICY_FILE = HERE.parent / "component_qualification" / "resources" / "qualification-policy.json"
SOURCES_RECORD = "library_supply_kaggle_public_good_sources/v1"
COMPONENT_RECORD = "kaggle_public_good_component/v1"
INVENTORY_RECORD = "kaggle_public_good_inventory/v1"
JOB_SOURCE = "kaggle_dataset"
NATIVE_FORMAT = "kaggle_dataset_contract"
COMPONENT_NAME, SCHEMA_NAME, README_NAME = "component.json", "schema.json", "README.md"
SOURCE_LICENCE_NAME = "SOURCE-LICENSE"
#: Names a dataset's own licence file starts with, preferred over a notice when choosing the one to carry.
LICENCE_FILE_NAMES = ("license", "licence")
#: The family that holds the line's atomic analysis items (tools/creative_originals); a package names the items
#: whose contract lists its dataset.
ANALYSIS_FAMILY = HERE.parent / "creative_originals" / "public_good_analysis"
#: The markers between which the shared reader holds the generated values.
GENERATED_START, GENERATED_END = "#: <generated>", "#: </generated>"

#: The decisions licence_decision gives; every one but LICENSABLE holds the dataset and is a refusal reason.
(LICENSABLE, LICENCE_UNKNOWN, LICENCE_NOT_ON_ALLOWLIST, LICENCE_SIGNALS_DISAGREE, LICENCE_MIXED_TERMS,
 LICENCE_PERMISSION_REQUIRED, DECLARED_DECISION_STALE) = LICENCE_DECISIONS = (
    "licensable", "licence_unknown", "licence_not_on_allowlist", "licence_signals_disagree", "licence_mixed_terms",
    "licence_permission_required", "declared_decision_stale")
#: Why a licensable dataset still yields no package.
SOURCE_UNREADABLE, NO_TABLE, TABLE_UNREADABLE, GENERATED_TEST_FAILED, LICENCE_TEXT_MISSING = (
    "source_unreadable", "no_table", "table_unreadable", "generated_test_failed", "licence_text_missing")
PACKAGE_PATH_INVALID = "package_path_invalid"
#: How a licence was decided, recorded with every fact the package names.
(BASIS_TEMPLATE, BASIS_STATEMENT, BASIS_METADATA, BASIS_DOCUMENTATION, BASIS_DECLARED) = (
    "licence_file_template", "licence_file_statement", "metadata_licence_field", "documentation_statement",
    "declared_decision")
#: Evidence kinds of one licence signal.
SIGNAL_LICENCE_FILE, SIGNAL_METADATA, SIGNAL_DOCUMENTATION, SIGNAL_HEADER = (
    "licence_file", "metadata_field", "documentation", "table_header")
#: The review bound on a package's file count (the panel reads at most this many files).
MAXIMUM_PACKAGE_FILES = 64
#: Room kept for the generated files when choosing which data files fit the package bound.
GENERATED_ROOM_BYTES = 384 * 1024
#: Synthetic rows each fixture holds.
FIXTURE_ROWS = 3
#: Values a fixture uses for a column without listed values, by JSON type.
FIXTURE_VALUES = {"integer": [1, 2, 3], "number": [0.5, 1.5, 2.5], "boolean": [True, False, True],
                  "array": [[], [], []], "object": [{}, {}, {}]}
FIXTURE_DATES = {"date": ["2026-01-01", "2026-01-02", "2026-01-03"],
                 "date-time": ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z"]}
#: A cell that is not a value of a typed column, by JSON type; a JSON string column receives a number instead.
WRONG_TEXT = {"integer": "not-an-integer", "number": "not-a-number", "boolean": "not-a-boolean"}
WRONG_DATE = "2026-13-45"
WRONG_TYPE, RAGGED_RECORD = "wrong_type", "ragged_record"
#: JSON values a column may refuse, each with the JSON types that would accept it.
WRONG_JSON_VALUES = ((12345, {"integer", "number"}), ("a text value", {"string"}), (True, {"boolean"}),
                     ({"not": "a value of this column"}, {"object"}), ([1], {"array"}))
#: Words naming a dataset split; families that differ only by one of them and hold the same columns are one table.
SPLIT_WORDS = ("train", "training", "validation", "valid", "val", "test", "dev", "eval")
#: A file name of one shard of a table family: name-00001, name-00001-of-00007 or name_00001.
_SHARD = re.compile(r"(?P<family>.+?)[-_](?P<shard>[0-9]{3,6})(?:-of-[0-9]{3,6})?\Z")
_IDENTIFIER = re.compile(r"[^a-z0-9]+")
#: Profile column types and the JSON type and format each becomes in a schema.
PROFILE_TO_SCHEMA = {kaggle_profile.BOOLEAN: ("boolean", None), kaggle_profile.INTEGER: ("integer", None),
                     kaggle_profile.NUMBER: ("number", None), kaggle_profile.DATE: ("string", "date"),
                     kaggle_profile.DATE_TIME: ("string", "date-time"), kaggle_profile.TEXT: ("string", None),
                     kaggle_profile.ARRAY: ("array", None), kaggle_profile.OBJECT: ("object", None)}
_CELL = str.maketrans({"|": "/", "\n": " ", "\r": " "})
#: JSON types a column declares, and the ISO 8601 formats a string column may carry.
STRING, INTEGER, NUMBER, BOOLEAN, NULL, ARRAY, OBJECT = JSON_TYPES = (
    "string", "integer", "number", "boolean", "null", "array", "object")
NUMERIC_TYPES = (INTEGER, NUMBER)
DATE_FORMAT, DATE_TIME_FORMAT = "date", "date-time"
#: The format name of a citation file in metadata_licence_fields.
CFF_FORMAT = "cff"
#: The delimiter of a tab-separated table, and the media types fixture and data files declare by suffix (the shared
#: table calls .jsonl and .tsv binary, which qualification would refuse as unverified).
TAB = "\t"
DECLARED_MEDIA = {".jsonl": "text/plain", ".tsv": "text/tab-separated-values"}
#: The dataset's own documentation the SDG rules read, by lower-case root file name.
DOCUMENTATION_NAMES = ("readme.md", "data_card.md", "readme.txt")
#: The inventory outcome of a dataset that became a package.
PACKAGED = "packaged"


class LineError(ValueError):
    """A declaration the line cannot use as written."""


# -- declarations -----------------------------------------------------------------------------------------------------
def read_sources(path: Path = SOURCES_FILE) -> dict:
    """The line's sources file, with its phrase tables compiled and its legal codes checked against their pins."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD:
        raise LineError(f"expected {SOURCES_RECORD}")
    record["_licence_phrases"] = {spdx: [_phrase(text) for text in phrases]
                                  for spdx, phrases in record["licence_phrases"].items()}
    record["_permission"] = [_phrase(text) for text in record["permission_phrases"]]
    record["_mixed"] = [_phrase(text) for text in record["mixed_markers"]]
    for spdx, code in record["legal_codes"].items():
        data = (HERE / code["copy"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != code["sha256"] or len(data) != code["size_bytes"]:
            raise LineError(f"the legal code copy of {spdx} is not the pinned text")
        code["_bytes"] = data
    for slug, declared in record["declared"].items():
        if not {"licence", "evidence_file", "evidence_sha256", "requires_absent", "reason"} <= set(declared):
            raise LineError(f"the declared decision of {slug} names its licence, evidence file and digest, the "
                            "paths that stay absent, and its reason")
    return record


def _phrase(text: str):
    return re.compile(r"(?<![a-z0-9])" + re.escape(_folded(text)) + r"(?![a-z0-9])")


def _folded(text: str) -> str:
    return " ".join(str(text).lower().split())


def accepted_licences(path: Path = POLICY_FILE) -> tuple:
    """The licences qualification accepts, read from the qualification policy (the owner's allowlist)."""
    return tuple(json.loads(Path(path).read_text(encoding="utf-8"))["accepted_licences"])


def backup_account(source_root: Path, sources: dict) -> str:
    """The Kaggle account the download's manifest names; every dataset of the download belongs to it."""
    manifest = json.loads((Path(source_root) / sources["backup_manifest"]).read_text(encoding="utf-8"))
    account = str(manifest.get("account") or "").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", account):
        raise LineError("the backup manifest names no Kaggle account")
    return account


def kaggle_address(sources: dict, owner: str, slug: str, file_name: "str | None" = None) -> str:
    """The dataset's Kaggle address, or the address of one of its files (the dataset page selecting that file)."""
    kaggle = sources["kaggle"]
    address = https_address(kaggle["host"], kaggle["dataset_path"].format(owner=owner, slug=slug))
    if file_name is None:
        return address
    return address + "?" + urllib.parse.urlencode({kaggle["file_parameter"]: file_name})


# -- licence ----------------------------------------------------------------------------------------------------------
def named_licences(text: str, sources: dict) -> list:
    """The licences a text names by an exact phrase of the sources file, in identifier order."""
    folded = _folded(text)
    return sorted(spdx for spdx, patterns in sources["_licence_phrases"].items()
                  if any(pattern.search(folded) for pattern in patterns))


def _says(text: str, patterns) -> bool:
    folded = _folded(text)
    return any(pattern.search(folded) for pattern in patterns)


def _metadata_value(path: Path, row: dict) -> "str | None":
    """The licence a metadata file states, as text: a JSON field (a string, a list or objects with a name or
    address) or a citation file's top-level field."""
    if row["format"] == CFF_FORMAT:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(row["field"] + ":"):
                return line.split(":", 1)[1].strip().strip("\"'")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get(row["field"])
    except (ValueError, AttributeError):
        return None
    values = value if isinstance(value, list) else [value]
    parts = []
    for item in values:
        if isinstance(item, dict):
            parts += [str(item[key]) for key in ("name", "@id", "url") if item.get(key)]
        elif item:
            parts.append(str(item))
    return " ".join(parts) or None


def licence_signals(folder: Path, profile: dict, sources: dict) -> list:
    """Every licence signal of a dataset folder: its root licence files, its metadata licence fields and, only when
    it has neither, its root documentation and its tables' column names."""
    folder = Path(folder)
    signals = []
    root_files = sorted(row["path"] for row in profile.get("files", []) if "/" not in row["path"])
    digests = {row["path"]: row["sha256"] for row in profile.get("files", [])}
    for name in root_files:
        lowered = name.lower()
        if not lowered.startswith(tuple(sources["licence_file_prefixes"])):
            continue
        text = (folder / name).read_text(encoding="utf-8", errors="replace")
        matched = match_licence(text)
        found = [matched.spdx] if matched.spdx else named_licences(text, sources)
        signals.append({"kind": SIGNAL_LICENCE_FILE, "file": name, "sha256": digests.get(name),
                        "found": found, "template": matched.spdx is not None,
                        "similarity": round(matched.similarity, 4),
                        "mixed": _says(text, sources["_mixed"]), "permission": _says(text, sources["_permission"])})
    for row in sources["metadata_licence_fields"]:
        if row["file"] not in root_files:
            continue
        value = _metadata_value(folder / row["file"], row)
        if value is None:
            continue
        signals.append({"kind": SIGNAL_METADATA, "file": row["file"], "sha256": digests.get(row["file"]),
                        "field": row["field"], "value": value[:200], "found": named_licences(value, sources),
                        "template": False, "mixed": _says(value, sources["_mixed"]),
                        "permission": _says(value, sources["_permission"])})
    if signals:
        return signals
    for name in root_files:
        if PurePosixPath(name).suffix.lower() not in sources["documentation_suffixes"]:
            continue
        text = (folder / name).read_text(encoding="utf-8", errors="replace")
        found, permission = named_licences(text, sources), _says(text, sources["_permission"])
        if found or permission:
            signals.append({"kind": SIGNAL_DOCUMENTATION, "file": name, "sha256": digests.get(name), "found": found,
                            "template": False, "mixed": _says(text, sources["_mixed"]), "permission": permission})
    for table in profile.get("tables", []):
        header = " ".join(str(name) for name in table.get("header") or [])
        found, permission = named_licences(header, sources), _says(header, sources["_permission"])
        if found or permission:
            signals.append({"kind": SIGNAL_HEADER, "file": table["file"], "sha256": table["sha256"], "found": found,
                            "template": False, "mixed": False, "permission": permission})
    return signals


def licence_decision(slug: str, profile: dict, signals: list, sources: dict, accepted) -> dict:
    """The dataset's licence: one accepted licence every signal agrees on, a declared decision whose conditions
    still hold, or the reason the dataset is held."""
    found = sorted({spdx for signal in signals for spdx in signal["found"]})
    decision = {"slug": slug, "signals": signals, "found": found}
    declared = sources["declared"].get(slug)
    if declared is not None:
        digests = {row["path"]: row["sha256"] for row in profile.get("files", [])}
        present = [row["path"] for row in profile.get("files", [])
                   if any(row["path"] == prefix or row["path"].startswith(prefix + "/")
                          for prefix in declared["requires_absent"])]
        if digests.get(declared["evidence_file"]) != declared["evidence_sha256"] or present:
            return {**decision, "spdx": None, "decision": DECLARED_DECISION_STALE,
                    "detail": "the declared licence file changed" if not present else f"{present[0]} is present"}
        return {**decision, "spdx": declared["licence"], "decision": LICENSABLE, "basis": BASIS_DECLARED,
                "declared": {key: declared[key] for key in ("licence", "decided_on", "evidence_file",
                                                            "evidence_sha256", "requires_absent", "reason")}}
    if not found:
        permission = any(signal["permission"] for signal in signals)
        return {**decision, "spdx": None, "decision": LICENCE_PERMISSION_REQUIRED if permission else LICENCE_UNKNOWN,
                "detail": ("the dataset asks for permission or for acceptance of terms of use" if permission else
                           "no licence file, licence field or licence statement in the dataset's own files")}
    if any(signal["mixed"] for signal in signals):
        return {**decision, "spdx": None, "decision": LICENCE_MIXED_TERMS,
                "detail": f"mixed terms naming {', '.join(found)}"}
    if len(found) > 1:
        return {**decision, "spdx": None, "decision": LICENCE_SIGNALS_DISAGREE,
                "detail": f"signals name {', '.join(found)}"}
    if found[0] not in accepted:
        return {**decision, "spdx": found[0], "decision": LICENCE_NOT_ON_ALLOWLIST,
                "detail": f"{found[0]} is not on the accepted list"}
    kinds = {signal["kind"] for signal in signals}
    if any(signal["template"] for signal in signals):
        basis = BASIS_TEMPLATE
    elif SIGNAL_LICENCE_FILE in kinds:
        basis = BASIS_STATEMENT
    elif SIGNAL_METADATA in kinds:
        basis = BASIS_METADATA
    else:
        basis = BASIS_DOCUMENTATION
    return {**decision, "spdx": found[0], "decision": LICENSABLE, "basis": basis}


# -- tables -----------------------------------------------------------------------------------------------------------
def identifier(text: str) -> str:
    """A lower-case Python identifier from a name: separators become underscores, a leading digit gains t_."""
    value = _IDENTIFIER.sub("_", str(text).lower()).strip("_") or "table"
    return value if value[0].isalpha() else "t_" + value


def family_of(path: str) -> str:
    """The table family a file belongs to: its stem without a shard number."""
    stem = PurePosixPath(path).stem
    match = _SHARD.fullmatch(stem)
    return match.group("family") if match else stem


def rectangular_problem(table: dict) -> "str | None":
    """Why a profiled table cannot hold a strict schema, or None."""
    if not table.get("profiled") or not table.get("columns"):
        return table.get("reason") or "not profiled"
    if table.get("parse_error"):
        return f"parse error: {table['parse_error']}"
    if table.get("header_problems"):
        return "header: " + "; ".join(table["header_problems"][:3])
    if table.get("ragged_records"):
        return f"{table['ragged_records']} records differ in width from the header"
    if table.get("not_objects"):
        return f"{table['not_objects']} lines are not JSON objects"
    if table.get("encoding", "").startswith("not utf-8"):
        return table["encoding"]
    return None


def _json_types(kinds: dict, empty: bool) -> tuple:
    """(JSON types, format) of a JSON column from the kinds its values took."""
    types, formats = set(), set()
    for kind in kinds:
        schema_type, form = PROFILE_TO_SCHEMA.get(kind, ("string", None))
        types.add(schema_type)
        if schema_type == STRING:
            formats.add(form)
    if set(NUMERIC_TYPES) <= types:
        types.discard(INTEGER)
    if empty or not types:
        types.add(NULL)
    form = None
    if formats == {DATE_FORMAT}:
        form = DATE_FORMAT
    elif formats and formats <= {DATE_FORMAT, DATE_TIME_FORMAT}:
        form = DATE_TIME_FORMAT
    return sorted(types), form


def table_specs(profile: dict) -> tuple:
    """({table name: spec}, [left-out tables with reasons]) from a dataset profile."""
    families, left_out = {}, []
    for table in profile.get("tables", []):
        if table.get("format") == kaggle_profile.JSON_DOCUMENT and not table.get("profiled"):
            continue  # a JSON document that is not an array of objects is a document, not a table
        problem = rectangular_problem(table)
        if problem:
            left_out.append({"file": table["file"], "format": table.get("format"), "reason": problem[:200]})
            continue
        key = (table["format"], table.get("delimiter"), family_of(table["file"]))
        families.setdefault(key, []).append(table)
    # Families that differ only by a split word (train, validation, test) and hold the same columns are one table.
    grouped = {}
    for (form, delimiter, family), tables in families.items():
        base, split = split_of(family)
        grouped.setdefault((form, delimiter, base), []).append((split, family, tables))
    merged = {}
    for (form, delimiter, base), members in grouped.items():
        column_sets = {frozenset(column["name"] for table in tables for column in table["columns"])
                       for _split, _family, tables in members}
        if len(members) > 1 and len(column_sets) == 1:
            merged[(form, delimiter, base)] = ([table for _split, _family, tables in members for table in tables],
                                               sorted(split for split, _family, _tables in members if split))
        else:
            for split, family, tables in members:
                merged[(form, delimiter, family)] = (tables, [])
    specs, names = {}, Counter()
    for (form, delimiter, family), (tables, splits) in sorted(merged.items(), key=lambda item: item[0][2]):
        name = identifier(family)
        names[name] += 1
        if names[name] > 1:
            name = f"{name}_{names[name]}"
        specs[name] = {**_merged_spec(form, delimiter, family, tables), "splits": splits}
    return specs, left_out


def split_of(family: str) -> tuple:
    """(family without its split word, the split word or None): dpo-preference-train is dpo-preference, train."""
    parts = [part for part in re.split(r"[-_]", family) if part]
    splits = [part for part in parts if part.lower() in SPLIT_WORDS]
    rest = [part for part in parts if part.lower() not in SPLIT_WORDS]
    if len(splits) != 1 or not rest:
        return family, None
    return "-".join(rest), splits[0].lower()


def _merged_spec(form: str, delimiter, family: str, tables: list) -> dict:
    order, columns = [], {}
    rows = profiled = 0
    for table in tables:
        rows += table.get("records", 0)
        profiled += table.get("profiled_records", 0)
        seen = set()
        for column in table["columns"]:
            name = column["name"]
            seen.add(name)
            if name not in columns:
                order.append(name)
                columns[name] = {"present": 0, "empty": 0, "absent": 0, "kinds": Counter(), "values": Counter(),
                                 "listed": True, "minimum": None, "maximum": None, "types": set()}
            merged = columns[name]
            for key in ("present", "empty", "absent"):
                merged[key] += column.get(key, 0)
            merged["kinds"].update(column.get("kinds", {}))
            merged["types"].add(column["type"])
            if column.get("values") is None:
                merged["listed"] = False
            else:
                merged["values"].update({json.dumps(row["value"]): row["count"] for row in column["values"]})
            for bound, pick in (("minimum", min), ("maximum", max)):
                if column.get(bound) is not None:
                    current = merged[bound]
                    merged[bound] = column[bound] if current is None else _bounded(pick, current, column[bound])
        for name in columns:
            if name not in seen:
                columns[name]["absent"] += table.get("profiled_records", 0)
    fields, required, observed = {}, [], {}
    for name in order:
        merged = columns[name]
        if form == kaggle_profile.DELIMITED:
            kind = kaggle_profile.column_type(merged["kinds"])
            schema_type, schema_format = PROFILE_TO_SCHEMA.get(kind, ("string", None))
            types = sorted({schema_type, NULL} if merged["empty"] or kind == kaggle_profile.EMPTY_COLUMN
                           else {schema_type})
        else:
            types, schema_format = _json_types(merged["kinds"], merged["empty"] > 0)
        fields[name] = {"type": types, **({"format": schema_format} if schema_format else {})}
        if not merged["absent"]:
            required.append(name)
        seen_values = merged["values"] if merged["listed"] and len(merged["values"]) <= kaggle_profile.MAXIMUM_ENUMERATED \
            else None
        observed[name] = {"present": merged["present"], "empty": merged["empty"], "absent": merged["absent"]}
        if merged["minimum"] is not None and any(kind in fields[name]["type"] for kind in NUMERIC_TYPES) \
                or schema_format and merged["minimum"] is not None:
            observed[name].update(minimum=merged["minimum"], maximum=merged["maximum"])
        if seen_values:
            observed[name]["values"] = [{"value": json.loads(value), "count": count}
                                        for value, count in seen_values.most_common()]
    files = sorted(table["file"] for table in tables)
    return {"family": family, "format": form, "delimiter": delimiter, "files": [PurePosixPath(path).name
                                                                               for path in files],
            "paths": files, "columns": order, "fields": fields, "required": required, "rows": rows,
            "profiled_rows": profiled,
            "profile_basis": "every record" if profiled == rows else f"{profiled} of {rows} records",
            "observed": observed,
            "file_rows": {PurePosixPath(table["file"]).name: table.get("records", 0) for table in tables},
            "sha256": {PurePosixPath(table["file"]).name: table["sha256"] for table in tables},
            "sizes": {PurePosixPath(table["file"]).name: table["size_bytes"] for table in tables}}


def _bounded(pick, left, right):
    try:
        return pick(left, right)
    except TypeError:
        return pick(str(left), str(right))


def loader_tables(specs: dict) -> dict:
    """The TABLES literal of a package's reader: files, format, delimiter, fields and required columns."""
    return {name: {"files": spec["files"], "format": spec["format"],
                   **({"delimiter": spec["delimiter"]} if spec["format"] == kaggle_profile.DELIMITED else {}),
                   "fields": spec["fields"], "required": spec["required"]} for name, spec in specs.items()}


# -- fixtures ---------------------------------------------------------------------------------------------------------
def fixture_rows(spec: dict) -> list:
    """FIXTURE_ROWS synthetic rows of one table: listed values where the profile has them, otherwise plain values of
    each column's type; the last row leaves nullable columns empty and drops columns that are not required."""
    rows = [{} for _ in range(FIXTURE_ROWS)]
    for name in spec["columns"]:
        field = spec["fields"][name]
        listed = [row["value"] for row in spec["observed"][name].get("values", []) if row["value"] is not None]
        kinds = [kind for kind in field["type"] if kind != NULL]
        for index, row in enumerate(rows):
            last = index == FIXTURE_ROWS - 1
            if last and name not in spec["required"]:
                continue
            if last and NULL in field["type"]:
                row[name] = None
                continue
            if not kinds:
                row[name] = None
            elif listed and _fits(listed[index % len(listed)], kinds, field.get("format")):
                row[name] = listed[index % len(listed)]
            elif field.get("format") in FIXTURE_DATES:
                row[name] = FIXTURE_DATES[field["format"]][index]
            elif kinds[0] in FIXTURE_VALUES:
                row[name] = FIXTURE_VALUES[kinds[0]][index]
            else:
                row[name] = f"example {index + 1}"
    return rows


def _fits(value, kinds, form) -> bool:
    checks = {"integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
              "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
              "boolean": lambda item: isinstance(item, bool), "string": lambda item: isinstance(item, str),
              "array": lambda item: isinstance(item, list), "object": lambda item: isinstance(item, dict)}
    if form and not isinstance(value, str):
        return False
    return any(checks[kind](value) for kind in kinds if kind in checks)


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def fixture_bytes(spec: dict, rows: list) -> bytes:
    """A fixture file in the table's own format."""
    if spec["format"] == kaggle_profile.DELIMITED:
        import csv
        import io
        out = io.StringIO()
        writer = csv.writer(out, delimiter=spec["delimiter"], lineterminator="\n")
        writer.writerow(spec["columns"])
        for row in rows:
            writer.writerow([_cell(row.get(name)) if name in row else "" for name in spec["columns"]])
        return out.getvalue().encode("utf-8")
    if spec["format"] == kaggle_profile.JSON_LINES:
        return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    return (json.dumps(rows, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def fixture_name(name: str, spec: dict) -> str:
    suffix = {kaggle_profile.DELIMITED: ".tsv" if spec.get("delimiter") == TAB else ".csv",
              kaggle_profile.JSON_LINES: ".jsonl"}.get(spec["format"], ".json")
    return f"fixtures/{name}{suffix}"


def wrong_value(spec: dict) -> dict:
    """The known-wrong change of a table's fixture: in a delimited table, text in its first typed column (or, when
    every column is text, a record with one cell more than the header); in a JSON table, a value of a type the
    column does not take."""
    if spec["format"] == kaggle_profile.DELIMITED:
        for name in spec["columns"]:
            field = spec["fields"][name]
            kinds = [kind for kind in field["type"] if kind != NULL]
            if field.get("format"):
                return {"reason": WRONG_TYPE, "column": name, "value": WRONG_DATE}
            if kinds and kinds[0] in WRONG_TEXT:
                return {"reason": WRONG_TYPE, "column": name, "value": WRONG_TEXT[kinds[0]]}
        return {"reason": RAGGED_RECORD}
    for name in spec["columns"]:
        taken = set(spec["fields"][name]["type"])
        for value, value_types in WRONG_JSON_VALUES:
            if not value_types & taken:
                return {"reason": WRONG_TYPE, "column": name, "value": value}
    raise LineError("no column of the table refuses any value")


# -- the package ------------------------------------------------------------------------------------------------------
def schema_document(title: str, identity: str, specs: dict, profile: dict) -> dict:
    """schema.json: one JSON Schema 2020-12 row definition per table under $defs, the profile under
    x-baltor-dataset (the source, the job key fields, each table's files, rows and observed values)."""
    definitions = {}
    for name, spec in specs.items():
        properties = {}
        for column in spec["columns"]:
            field = spec["fields"][column]
            entry = {"type": field["type"] if len(field["type"]) > 1 else field["type"][0]}
            if field.get("format"):
                entry["format"] = field["format"]
            observed = spec["observed"][column]
            if "minimum" in observed:
                entry["x-baltor-observed-range"] = [observed["minimum"], observed["maximum"]]
            if observed.get("values"):
                entry["x-baltor-observed-values"] = [row["value"] for row in observed["values"]]
            properties[column] = entry
        definitions[name] = {"type": "object", "title": f"{name} row", "properties": properties,
                             "required": list(spec["required"]), "additionalProperties": False,
                             "x-baltor-table": {"files": spec["files"], "format": spec["format"],
                                                "delimiter": spec["delimiter"], "columns": spec["columns"],
                                                "rows": spec["rows"], "profile_basis": spec["profile_basis"]}}
    return {"$schema": JSON_SCHEMA_DIALECT, "title": title, "type": "object",
            "description": "Row schemas of the dataset's tables; validate a row against $defs/<table>.",
            "$defs": definitions,
            "x-baltor-dataset": {"source": JOB_SOURCE, "identity": identity, "tables": sorted(specs),
                                 "file_list_sha256": profile["file_list_sha256"],
                                 "profiler": profile["profiler_version"]}}


def loader_module(title: str, dataset: dict, tables: dict, data_files: dict) -> str:
    """<dataset>.py: the shared reader with this dataset's DATASET, TABLES and DATA_FILES between its markers."""
    text = LOADER_SOURCE.read_text(encoding="utf-8")
    head, rest = text.split(GENERATED_START, 1)
    _old, tail = rest.split(GENERATED_END, 1)
    docstring_end = head.index('"""', 3) + 3
    header = (f'"""{title}: a typed reader of the Kaggle dataset {dataset["identity"]}.\n\n'
              f'Tables: {", ".join(sorted(tables))}.\nLicensed {dataset["licence"]}; source: {dataset["address"]}\n\n'
              'The kaggle_public_good supply line wrote DATASET, TABLES and DATA_FILES below from the dataset\'s\n'
              'own files; the rest is the shared reader, standard library only. README.md lists the columns and\n'
              'test_dataset_contract.py holds the checks.\n"""')
    generated = ("#: <generated> The supply line wrote these three values from the dataset's own files.\n"
                 f"DATASET = {_literal(dataset)}\nTABLES = {_literal(tables)}\nDATA_FILES = {_literal(data_files)}\n")
    return header + head[docstring_end:] + generated + GENERATED_END + tail


def _literal(value) -> str:
    """A Python literal of plain data (JSON's types), readable and deterministic."""
    import pprint
    return pprint.pformat(value, width=110, sort_dicts=True)


def attribution_line(title: str, authors: str, address: str, spdx: str) -> str:
    """The credit line a reuser gives: title, authors, address and licence."""
    return f"{title}, by {authors}, {address}, licensed {spdx}."


def dataset_title(folder: Path, profile: dict, slug: str) -> str:
    """The dataset's own name from its Croissant record or citation file, else its slug in words."""
    for name in ("croissant.json", "mlcroissant.json"):
        path = Path(folder) / name
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8")).get("name")
            except ValueError:
                value = None
            if isinstance(value, str) and value.strip():
                return " ".join(value.split())[:120]
    path = Path(folder) / "CITATION.cff"
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip().strip("\"'")[:120]
    for name in ("README.md",):
        path = Path(folder) / name
        if path.is_file():
            first = path.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
            if first and first[0].startswith("# "):
                return first[0][2:].strip()[:120]
    return slug.replace("-", " ").capitalize()


def dataset_authors(folder: Path, owner: str) -> str:
    """Who to credit: the citation file's authors, else the Kaggle account that published the dataset."""
    path = Path(folder) / "CITATION.cff"
    names = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        given = family = None
        for line in lines:
            stripped = line.strip().lstrip("- ").strip()
            if stripped.startswith("name:"):
                names.append(stripped.split(":", 1)[1].strip().strip("\"'"))
            elif stripped.startswith("given-names:"):
                given = stripped.split(":", 1)[1].strip().strip("\"'")
            elif stripped.startswith("family-names:"):
                family = stripped.split(":", 1)[1].strip().strip("\"'")
            if given and family:
                names.append(f"{given} {family}")
                given = family = None
    return ", ".join(dict.fromkeys(names)) if names else f"the Kaggle account {owner}"


def documentation_text(folder: Path, profile: dict) -> str:
    """The dataset's own README and data card, which the SDG rules read for the documentation field."""
    parts = []
    for row in profile.get("files", []):
        if "/" not in row["path"] and row["path"].lower() in DOCUMENTATION_NAMES:
            parts.append((Path(folder) / row["path"]).read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def sdg_evidence(slug: str, title: str, profile: dict, documentation: str) -> dict:
    """The evidence fields of one dataset for the SDG rules."""
    files = [row["path"] for row in profile.get("files", [])] or [table["file"] for table in profile["tables"]]
    columns, values = [], []
    for table in profile.get("tables", []):
        columns += [str(column["name"]) for column in table.get("columns", [])]
        for column in table.get("columns", []):
            values += [str(row["value"]) for row in column.get("values") or []
                       if isinstance(row["value"], str) and len(row["value"]) <= 80]
    return kaggle_sdg.evidence_text(name=f"{slug} {title}", files=files, columns=columns, values=values,
                                    documentation=documentation)


def analysis_items(identity: str, family: Path = ANALYSIS_FAMILY) -> list:
    """The atomic analysis items whose contract names this dataset (tools/creative_originals family)."""
    found = []
    items = Path(family) / "items"
    if not items.is_dir():
        return found
    for path in sorted(items.glob("*/item.json")):
        try:
            contract = json.loads(path.read_text(encoding="utf-8")).get("contract", {})
        except ValueError:
            continue
        datasets = (contract.get("derived_from") or {}).get("kaggle_datasets") or []
        if identity in datasets:
            found.append(path.parent.name)
    return found


def _table_lines(spec: dict) -> list:
    lines = ["| Column | Type | Required | Observed |", "|---|---|---|---|"]
    for column in spec["columns"]:
        field = spec["fields"][column]
        observed = spec["observed"][column]
        shown = []
        if "minimum" in observed:
            shown.append(f"{observed['minimum']} to {observed['maximum']}")
        if observed.get("values"):
            listed = [f"{row['value']} ({row['count']})" for row in observed["values"][:8]]
            more = len(observed["values"]) - len(listed)
            shown.append(", ".join(listed) + (f", and {more} more" if more > 0 else ""))
        if observed["empty"]:
            shown.append(f"{observed['empty']} empty")
        if observed["absent"]:
            shown.append(f"absent in {observed['absent']} rows")
        kind = " or ".join(field["type"]) + (f" ({field['format']})" if field.get("format") else "")
        lines.append(f"| `{column}` | {kind} | {'yes' if column in spec['required'] else 'no'} | "
                     f"{'; '.join(shown).translate(_CELL)[:300]} |")
    return lines


def readme(card: dict, specs: dict, goal_names: dict, rules: dict) -> str:
    """README.md, the dataset card: what the dataset holds, its source and licence, the SDG proposal with its
    evidence, every table's columns, how to use the reader, the data in the package and the limits."""
    dataset, licence, sdg = card["dataset"], card["licence"], card["sdg"]
    lines = [f"# {card['title']}", "",
             f"{len(specs)} table{'s' if len(specs) != 1 else ''} from the Kaggle dataset `{dataset['identity']}`, "
             f"{dataset['rows']:,} rows in all. Baltor's kaggle_public_good line wrote the schema contract, the "
             "typed reader, its tests and this card from the dataset's own files; no model wrote any of it.", "",
             "## Source and licence", "", "| | |", "|---|---|",
             f"| Dataset | {dataset['address']} |",
             f"| Files | {dataset['files']:,} files, {dataset['bytes']:,} bytes; file list SHA-256 "
             f"`{dataset['file_list_sha256']}` |",
             f"| Downloaded | {dataset['retrieved_at']} |",
             f"| Licence | {licence['spdx']}, decided by `{licence['basis']}` |",
             f"| Credit | {licence['attribution']} |", ""]
    lines += ["The licence was read from these files of the dataset:", ""]
    for signal in licence["evidence"]:
        named = ", ".join(signal["found"]) or "no licence by name"
        lines.append(f"- `{signal['file']}` ({signal['kind']}, SHA-256 `{signal['sha256']}`): {named}"
                     + ("; states mixed terms" if signal.get("mixed") else ""))
    if licence.get("declared"):
        lines += ["", f"Declared decision of {licence['declared']['decided_on']}: {licence['declared']['reason']}"]
    lines += ["", "The Kaggle record itself was not read; the licence comes from the files above. "
              "`SOURCE-LICENSE` is the dataset's own licence file and `UPSTREAM-LICENSE` the licence's legal code.",
              "", "## SDG proposal", ""]
    if sdg["goals"]:
        goal_text = ", ".join(f"{goal} ({goal_names.get(str(goal), '')})" for goal in sdg["goals"])
        lines += [f"Goals {goal_text}.", "", f"Targets {', '.join(sdg['targets'])}; each rule's reason below says "
                  "what the target covers."]
        if sdg["indicators"]:
            lines += ["", f"Indicators the data informs: {', '.join(sdg['indicators'])}."]
        lines += ["", "| Rule | Matched | Reason |", "|---|---|---|"]
        by_rule = {}
        for match in sdg["matches"]:
            by_rule.setdefault(match["rule"], []).append(f"{match['phrase']} ({match['field']})")
        for row in kaggle_sdg.reasons(rules, sdg["rules"]):
            shown = "; ".join(dict.fromkeys(by_rule.get(row["rule"], [])))[:200]
            lines.append(f"| `{row['rule']}` | {shown.translate(_CELL)} | {row['reason'].translate(_CELL)} |")
    else:
        lines.append("No rule of the SDG rule file matched this dataset, so no goal is proposed.")
    lines += ["", f"The goals are a proposal of rule file version {sdg['rules_version']} "
              "(tools/supply_lines/kaggle_sdg_rules.json): the phrases above matched, and nothing more is "
              "claimed. A reviewer attaches goals only after independent approval.", "", "## Tables", ""]
    for name, spec in specs.items():
        copied = [row for row in card["data_files"] if row["table"] == name]
        lines += [f"### `{name}`", "",
                  f"{spec['rows']:,} rows in {len(spec['files'])} file{'s' if len(spec['files']) != 1 else ''} "
                  f"({spec['format'].replace('_', ' ')}"
                  + (f", delimiter `{spec['delimiter']!r}`" if spec["delimiter"] else "")
                  + f"); schema inferred from {spec['profile_basis']}."
                  + (f" Splits: {', '.join(spec['splits'])}." if spec.get("splits") else "")
                  + (f" Copied into `data/`: {', '.join(row['file'] for row in copied)}." if copied else ""), ""]
        if len(spec["files"]) <= 6:
            lines += [f"Files: {', '.join(f'`{file}`' for file in spec['files'])}.", ""]
        else:
            lines += [f"Files: `{spec['files'][0]}` to `{spec['files'][-1]}`.", ""]
        lines += _table_lines(spec) + [""]
    module = card["loader"]["module"]
    example = sorted(specs)[0]
    lines += ["## Use", "", "```python", f"import {module}", "",
              f"for row in {module}.read_rows({example!r}, \"/path/to/{specs[example]['files'][0]}\"):",
              "    ...  # a dict of typed values; a row that breaks the schema raises SchemaError", "```", "",
              "```bash", f"python3 {module}.py {example} /path/to/{specs[example]['files'][0]}",
              f"python3 {module}.py --tables", "python3 -m unittest test_dataset_contract", "```", "",
              "The reader refuses a file that lacks a required column or names an unknown one, a value of another "
              "type, a ragged record and text that is not UTF-8, each with a reason code (`SchemaError.reason`).",
              "", "## Data in this package", ""]
    if card["data_files"]:
        lines += [f"- `data/{row['file']}`: {row['rows']:,} rows, SHA-256 `{row['sha256']}`, a byte-for-byte copy "
                  "of the dataset's file." for row in card["data_files"]]
    else:
        lines.append("None. Download the tables from the dataset's address; the reader checks them.")
    if card.get("data_note"):
        lines += ["", card["data_note"]]
    if card["analysis_items"]:
        lines += ["", "## Analysis items", "", "Atomic functions built for this dataset (Baltor's "
                  "public_good_analysis family): " + ", ".join(f"`{item}`" for item in card["analysis_items"]) + "."]
    lines += ["", "## Limits", ""] + [f"- {limit}" for limit in card["limits"]] + [""]
    return "\n".join(lines)


def card_limits(specs: dict, left_out: list, decision: dict) -> list:
    limits = ["The schema is the one the downloaded files hold; another version of the dataset can differ, and "
              "the reader then refuses its rows by name rather than guessing.",
              "Values listed under Observed are counts from the download, not a closed vocabulary: the schema "
              "constrains types and required columns only.",
              "The card describes the files, not their accuracy, completeness or fitness for a decision about "
              "people.",
              f"The licence is decided from the dataset's own files ({decision['basis']}); the Kaggle record "
              "and the platform's terms were not read."]
    if any(spec["profiled_rows"] != spec["rows"] for spec in specs.values()):
        limits.append("A large table's types were inferred from its first records; its row count covers "
                      "every record.")
    for row in left_out:
        limits.append(f"Left out: `{row['file']}` ({row['reason']}).")
    return limits


def build_package(folder: Path, slug: str, owner: str, profile: dict, decision: dict, proposal: dict,
                  specs: dict, left_out: list, *, sources: dict, rules: dict, goal_names: dict,
                  licence_text: bytes, code_revision: str, generated_on: str, copy_data: bool = True) -> tuple:
    """(payload, bodies) of one dataset package; SupplyRecordError when it cannot be built or checked."""
    identity = f"{owner}/{slug}"
    title = dataset_title(folder, profile, slug)
    address = kaggle_address(sources, owner, slug)
    spdx = decision["spdx"]
    authors = dataset_authors(folder, owner)
    module = identifier(slug)
    retrieved = profile["latest_modified_at"]
    files, facts, data_files, data_rows = [], [], {}, []
    note = None
    if copy_data:
        budget = MAXIMUM_REVIEW_PACKAGE_BYTES - GENERATED_ROOM_BYTES
        count = 0
        for name, spec in sorted(specs.items()):
            for path in spec["paths"]:
                file_name = PurePosixPath(path).name
                size = spec["sizes"][file_name]
                if size > MAXIMUM_REVIEW_FILE_BYTES or size > budget or count >= MAXIMUM_PACKAGE_FILES // 2:
                    continue
                data = (Path(folder) / path).read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                if digest != spec["sha256"][file_name]:
                    raise SupplyRecordError(SOURCE_UNREADABLE, f"{path} changed since it was profiled")
                budget -= size
                count += 1
                data_files[file_name] = {"table": name, "sha256": digest, "rows": spec["file_rows"][file_name]}
                data_rows.append({"file": file_name, "table": name, "sha256": digest,
                                  "rows": spec["file_rows"][file_name]})
                media = DECLARED_MEDIA.get(PurePosixPath(file_name).suffix.lower())
                files.append(PackageFile(f"data/{file_name}", data, "other", UPSTREAM_VERBATIM,
                                         {"url": kaggle_address(sources, owner, slug, path), "sha256": digest},
                                         media_type=media))
    else:
        note = ("The dataset's small tables were not copied: the static checks of the licensed import blocked a "
                "copy, so this package carries the schema, reader and fixtures only.")
    dataset = {"identity": identity, "address": address, "licence": spdx, "credit": attribution_line(
        title, authors, address, spdx)}
    tables = loader_tables(specs)
    fixtures = {}
    for name, spec in specs.items():
        rows = fixture_rows(spec)
        path = fixture_name(name, spec)
        files.append(PackageFile(path, fixture_bytes(spec, rows), "other", GENERATED,
                                 media_type=DECLARED_MEDIA.get(PurePosixPath(path).suffix.lower())))
        fixtures[name] = {"path": path, "rows": len(rows), "wrong": wrong_value(spec)}
    signals = [{key: signal[key] for key in ("kind", "file", "sha256", "found", "mixed", "permission")}
               for signal in decision["signals"]]
    card = {"record_type": COMPONENT_RECORD, "job": {"source": JOB_SOURCE, "identity": identity}, "title": title,
            "dataset": {"identity": identity, "owner": owner, "slug": slug, "address": address,
                        "files": profile["files_total"], "bytes": profile["bytes_total"],
                        "file_list_sha256": profile["file_list_sha256"], "retrieved_at": retrieved,
                        "formats": profile["formats"], "rows": sum(spec["rows"] for spec in specs.values())},
            "licence": {"spdx": spdx, "basis": decision["basis"], "attribution": dataset["credit"],
                        "evidence": signals, **({"declared": decision["declared"]} if decision.get("declared")
                                                else {})},
            "sdg": {key: proposal[key] for key in ("status", "rules_version", "goals", "targets", "indicators",
                                                   "rules", "matches")},
            "tables": [{"name": name, "files": spec["files"], "format": spec["format"], "rows": spec["rows"],
                        "columns": len(spec["columns"]), "profile_basis": spec["profile_basis"]}
                       for name, spec in specs.items()],
            "loader": {"module": module, "command": f"python3 {module}.py TABLE PATH",
                       "functions": ["table_names", "read_rows", "read_table", "check_row", "validate_file",
                                     "check_data_file", "main"]},
            "fixtures": fixtures, "data_files": data_rows, "analysis_items": analysis_items(identity),
            "left_out": left_out, "limits": card_limits(specs, left_out, decision),
            "generator": {"line": KAGGLE_PUBLIC_GOOD, "version": GENERATOR_VERSION, "code_revision": code_revision}}
    if note:
        card["data_note"] = note
    files += [PackageFile(COMPONENT_NAME, (json.dumps(card, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
                          .encode(), "other"),
              PackageFile(SCHEMA_NAME, (json.dumps(schema_document(title, identity, specs, profile), indent=1,
                                                   ensure_ascii=False) + "\n").encode(), "other"),
              PackageFile(f"{module}.py", loader_module(title, dataset, tables, data_files).encode(),
                          "executable_tool"),
              PackageFile(CONTRACT_TESTS_NAME, CONTRACT_TESTS_SOURCE.read_bytes(), "executable_tool"),
              PackageFile(README_NAME, readme(card, specs, goal_names, rules).encode(), "other"),
              PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT)]
    code = sources["legal_codes"].get(spdx)
    if code is not None:
        legal_address = https_address(code["host"], code["path"])
        files.append(PackageFile(UPSTREAM_LICENCE_NAME, code["_bytes"], "other", LICENCE_TEXT,
                                 {"url": legal_address, "sha256": code["sha256"]}))
        facts.append(fact_source(legal_address, code["retrieved_at"], code["sha256"], code["size_bytes"],
                                 "licence_text", spdx=spdx, basis="legal_code_from_the_licence_steward"))
    licence_files = [signal for signal in decision["signals"] if signal["kind"] == SIGNAL_LICENCE_FILE]
    template = next((signal for signal in licence_files if signal["template"] and signal["found"] == [spdx]), None)
    if code is None and template is None:
        raise SupplyRecordError(LICENCE_TEXT_MISSING, f"no legal code or full licence text of {spdx} to carry")
    for signal in decision["signals"]:
        if spdx not in signal["found"]:
            continue  # a signal that names other terms only (an adapter's Apache text) is evidence of nothing here
        data = (Path(folder) / signal["file"]).read_bytes()
        location = kaggle_address(sources, owner, slug, signal["file"])
        facts.append(fact_source(location, _modified(profile, signal["file"]), signal["sha256"], len(data),
                                 LICENCE_EVIDENCE, spdx=spdx, basis=decision["basis"]))
        if signal is template and code is None:
            files.append(PackageFile(UPSTREAM_LICENCE_NAME, data, "other", LICENCE_TEXT,
                                     {"url": location, "sha256": signal["sha256"]}))
        elif signal["kind"] == SIGNAL_LICENCE_FILE and signal["file"] == _primary_licence_file(
                [row for row in licence_files if spdx in row["found"]]):
            files.append(PackageFile(SOURCE_LICENCE_NAME, data, "other", UPSTREAM_VERBATIM,
                                     {"url": location, "sha256": signal["sha256"]}))
    for spec in specs.values():
        for path in spec["paths"]:
            file_name = PurePosixPath(path).name
            facts.append(fact_source(kaggle_address(sources, owner, slug, path), _modified(profile, path),
                                     spec["sha256"][file_name], spec["sizes"][file_name], "data_source", spdx=spdx,
                                     basis=decision["basis"]))
    if len(files) + 1 > MAXIMUM_PACKAGE_FILES:  # ATTRIBUTION.md is the one more
        raise SupplyRecordError(PACKAGE_ABOVE_REVIEW_BOUND, f"{len(files) + 1} files")
    expression = GENERATED_CODE_LICENCE if spdx == GENERATED_CODE_LICENCE else f"{spdx} AND {GENERATED_CODE_LICENCE}"
    from .creative_originals import derived_effects
    from creative_originals.assemble import Entry
    effects = derived_effects("code_module", [Entry(row.path, row.data, row.role, row.media_type or "")
                                              for row in files])
    supply = SupplyPackage(
        line=KAGGLE_PUBLIC_GOOD, identity=identity, key=upstream_key(KAGGLE_PUBLIC_GOOD, identity),
        kind="code_module", native_format=NATIVE_FORMAT, form="data_table", name=f"{module.replace('_', '-')}-dataset",
        description=(f"{title}: Kaggle dataset {identity} ({spdx}), {len(specs)} table schema"
                     f"{'s' if len(specs) != 1 else ''} with a typed standard-library reader, tests and an SDG "
                     f"proposal (goals {', '.join(str(goal) for goal in proposal['goals']) or 'none'})."),
        files=files, licence_expression=expression,
        provenance=provenance("kaggle_dataset", identity, "", f"sha256:{profile['file_list_sha256']}", facts,
                              {"identity": "tools/supply_lines/kaggle_public_good.py", "version": GENERATOR_VERSION,
                               "code_revision": code_revision}),
        placements=[{"harness": "reference", "path": f"tools/{module.replace('_', '-')}-dataset/",
                     "basis": "documented_layout", "scope": "project", "support": "unverified"}],
        effects=effects, credentials=[],
        tests={"files": [CONTRACT_TESTS_NAME], "command": "python -m unittest test_dataset_contract",
               "network": False},
        repository={"name": identity, "kaggle_address": address, "title": title, "tables": len(specs),
                    "rows": card["dataset"]["rows"], "sdg_goals": proposal["goals"], "sdg_targets": proposal["targets"],
                    "sdg_rules_version": proposal["rules_version"], "licence_basis": decision["basis"],
                    "data_files": len(data_rows), "analysis_items": card["analysis_items"]},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


def _primary_licence_file(signals: list) -> "str | None":
    """The dataset's own licence file a package carries verbatim: LICENSE before the others, by name."""
    names = sorted((signal["file"] for signal in signals),
                   key=lambda name: (not name.lower().startswith(LICENCE_FILE_NAMES), len(name), name))
    return names[0] if names else None


def _modified(profile: dict, path: str) -> str:
    for row in profile.get("files", []):
        if row["path"] == path:
            return row["modified_at"]
    return profile["latest_modified_at"]


# -- the run ----------------------------------------------------------------------------------------------------------
def dataset_folders(source_root: Path, only=()) -> list:
    folders = sorted(path for path in Path(source_root).iterdir() if path.is_dir())
    return [path for path in folders if not only or path.name in only]


def generate(source_root: Path, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
             only=(), workers: int = 1, profile_cache: "Path | None" = None,
             profile_bytes: int = kaggle_profile.DEFAULT_PROFILE_BYTES) -> tuple:
    """(built, refusals, facts, summary, inventory) of every dataset folder under ``source_root``."""
    from .publisher_tables import read_sources as publisher_sources
    sources = read_sources()
    rules = kaggle_sdg.read_rules(SDG_RULES_FILE)
    goal_names = publisher_sources()["sdg_goal_names"]
    accepted = accepted_licences()
    owner = backup_account(source_root, sources)
    folders = dataset_folders(source_root, only)
    profiles = kaggle_profile.profile_folders(folders, cache=profile_cache, workers=workers,
                                              profile_bytes=profile_bytes)
    built, refused, facts, inventory = [], [], {}, []
    for code in sources["legal_codes"].values():
        facts[code["sha256"]] = code["_bytes"]
    counts = Counter()
    for folder in folders:
        slug = folder.name
        profile, error = profiles[slug]
        if profile is None:
            refused.append(refusal(KAGGLE_PUBLIC_GOOD, SOURCE_UNREADABLE, slug, error or ""))
            inventory.append({"slug": slug, "outcome": SOURCE_UNREADABLE, "detail": error})
            counts[SOURCE_UNREADABLE] += 1
            continue
        signals = licence_signals(folder, profile, sources)
        decision = licence_decision(slug, profile, signals, sources, accepted)
        title = dataset_title(folder, profile, slug)
        proposal = kaggle_sdg.propose(sdg_evidence(slug, title, profile, documentation_text(folder, profile)), rules)
        specs, left_out = table_specs(profile)
        row = {"slug": slug, "identity": f"{owner}/{slug}", "title": title, "files": profile["files_total"],
               "bytes": profile["bytes_total"], "formats": profile["formats"],
               "tables": {name: {"files": len(spec["files"]), "rows": spec["rows"], "columns": len(spec["columns"]),
                                 "profile_basis": spec["profile_basis"]} for name, spec in specs.items()},
               "left_out_tables": left_out,
               "licence": {key: decision.get(key) for key in ("decision", "spdx", "basis", "found", "detail")},
               "licence_signals": [{key: signal[key] for key in ("kind", "file", "found", "mixed", "permission")}
                                   for signal in signals],
               "sdg": {key: proposal[key] for key in ("goals", "targets", "indicators", "rules", "matches")}}
        outcome = decision["decision"]
        if outcome == LICENSABLE and not specs:
            outcome = TABLE_UNREADABLE if left_out else NO_TABLE
        if outcome != LICENSABLE:
            detail = decision.get("detail") or ("no table could be profiled" if outcome == TABLE_UNREADABLE else
                                                "the dataset holds no table (code, images, documents or models)")
            refused.append(refusal(KAGGLE_PUBLIC_GOOD, outcome, slug, detail))
            row["outcome"] = outcome
            inventory.append(row)
            counts[outcome] += 1
            continue
        common = dict(sources=sources, rules=rules, goal_names=goal_names, licence_text=licence_text,
                      code_revision=code_revision, generated_on=generated_on)
        try:
            try:
                payload, bodies = build_package(folder, slug, owner, profile, decision, proposal, specs, left_out,
                                                **common)
            except SupplyRecordError as error:
                if error.code != BLOCKED_BY_STATIC_CHECK:
                    raise
                payload, bodies = build_package(folder, slug, owner, profile, decision, proposal, specs, left_out,
                                                copy_data=False, **common)
            passed, tests_run, output = run_package_tests(payload, bodies, Path(staging) / identifier(slug))
            if not passed:
                raise SupplyRecordError(GENERATED_TEST_FAILED, output[-280:])
        except SupplyRecordError as error:
            reason = error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND,
                                                  PACKAGE_PATH_INVALID, SOURCE_UNREADABLE,
                                                  LICENCE_TEXT_MISSING) else GENERATED_TEST_FAILED
            refused.append(refusal(KAGGLE_PUBLIC_GOOD, reason, slug, str(error)[:300]))
            row["outcome"] = reason
            inventory.append(row)
            counts[reason] += 1
            continue
        payload["tests"]["result"], payload["tests"]["tests_run"] = "passed", tests_run
        built.append((payload, bodies))
        for signal in signals:
            data = (folder / signal["file"]).read_bytes()
            facts[hashlib.sha256(data).hexdigest()] = data
        row.update(outcome=PACKAGED, record_id=payload["record_id"], package_digest=payload["package_digest"],
                   data_files=len(json.loads(bodies[_digest_of(payload, COMPONENT_NAME)])["data_files"]))
        inventory.append(row)
        counts[PACKAGED] += 1
    summary = {"datasets": len(folders), "outcomes": dict(sorted(counts.items())), "owner": owner,
               "sdg_rules_version": rules["version"],
               "goals_of_packages": _goal_counts(row for row in inventory if row.get("outcome") == PACKAGED),
               "goals_of_all_datasets": _goal_counts(inventory),
               "datasets_without_goal": sum(1 for row in inventory if not (row.get("sdg") or {}).get("goals"))}
    return built, refused, facts, summary, inventory


def _digest_of(payload: dict, path: str) -> str:
    return next(entry["digest"] for entry in payload["package"]["files"] if entry["path"] == path)


def _goal_counts(rows) -> dict:
    counts = Counter(goal for row in rows for goal in (row.get("sdg") or {}).get("goals", []))
    return {str(goal): counts[goal] for goal in range(1, 18)}


def run_package_tests(payload: dict, bodies: dict, folder: Path) -> tuple:
    """(passed, tests run, output tail) of a package's own tests, run in a child interpreter from the package's
    exact bytes written to ``folder``; the network is not needed and nothing outside the folder is written."""
    import shutil
    import subprocess
    import sys
    folder = Path(folder)
    if folder.exists():
        shutil.rmtree(folder)
    for entry in payload["package"]["files"]:
        target = folder / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bodies[entry["digest"]])
    # The qualification sandbox's flags (-E -s -B): no PYTHON* variables, no user site, no bytecode, and the
    # package folder (the working folder) on the path.
    done = subprocess.run([sys.executable, "-E", "-s", "-B", "-m", "unittest", "-v", "test_dataset_contract"],
                          cwd=folder,
                          capture_output=True, text=True, timeout=300, check=False)
    ran = re.search(r"^Ran (\d+) tests?", done.stderr, re.MULTILINE)
    return done.returncode == 0 and ran is not None and int(ran.group(1)) > 0, int(ran.group(1)) if ran else 0, \
        (done.stderr or done.stdout)[-1200:]


def sdg_map(built, inventory: list, created_on: str) -> dict:
    """The run's SDG proposal in the shape of the publisher line's sdg_supply_source_map/v1, for packages, beside the
    proposal of every inventoried dataset."""
    sources = {payload["repository"]["name"]: payload["repository"]["sdg_goals"] for payload, _bodies in built}
    per_goal = Counter(goal for goals in sources.values() for goal in goals)
    return {"record_type": "sdg_supply_source_map/v1", "created_on": created_on,
            "meaning": ("Proposed SDG goals per Kaggle dataset package, from the line's goal rules. A proposal for "
                        "reviewers attaching PublicGoodGrant goals after independent approval; it grants nothing."),
            "sources": dict(sorted(sources.items())),
            "sources_per_goal": {str(goal): per_goal[goal] for goal in range(1, 18)},
            "without_goal": sum(1 for goals in sources.values() if not goals),
            "inventory_per_goal": _goal_counts(inventory)}


__all__ = ["GENERATOR_VERSION", "SOURCES_FILE", "SDG_RULES_FILE", "LICENCE_DECISIONS", "read_sources",
           "accepted_licences", "backup_account", "kaggle_address", "named_licences", "licence_signals",
           "licence_decision", "identifier", "family_of", "table_specs", "loader_tables", "fixture_rows",
           "fixture_bytes", "wrong_value", "schema_document", "loader_module", "build_package", "generate",
           "run_package_tests", "sdg_map"]
