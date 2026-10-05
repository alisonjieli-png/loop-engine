"""Line publisher_tables: one data table per series or table an official publisher serves at its own HTTPS address.

```text
One collection (declared in publisher_table_sources.json)
├── rows: every series of the publisher's catalogue (World Development Indicators, read through the World
│   Bank's API), or the tables the declaration names (the O*NET 31.0 Database text release)
├── facts: the exact bytes at the publisher's HTTPS address on a declared host, their SHA-256 and the
│   retrieval time; an archive member the declaration names; the package's data file is those bytes
├── licence, bound to the exact series or release, with its evidence address
│   ├── series_metadata: the series' own licence field (the World Bank's License_Type), read per series;
│   │   only a value the declaration maps to an allowlisted identifier passes, any other value refuses the
│   │   series by name with the value it found
│   └── collection_statement: the publisher's licence page and the release's own Read Me must both state
│       the declared licence for this release, or every table of it is refused
├── SDG goals by a rule that is data: wdi_sdg_goals.json (the longest code prefix, else the series' topic)
│   or the collection's declared goals, each with its reason; a proposal for reviewers, nothing granted
├── size: a data file above the review panel's file bound is kept as consecutive parts cut at record ends,
│   each within the bound, that join to the exact bytes; a table whose package would exceed the package
│   bound is refused by name (never sampled, never split across packages)
└── one package (kind code_module, form data_table), with the shapes, loader, schema and tests of
    data_tables.py
    ├── data/<file> or its parts, and the series metadata when the publisher has it, byte for byte
    ├── schema.json naming the publisher and the series (the qualification job key), the loader, its tests
    └── README.md (series, unit, period, source, licence, SDG goals, attribution), LICENSE (generated code,
        MIT), UPSTREAM-LICENSE (the licence's legal code from its steward), ATTRIBUTION.md
```

Why a sibling module rather than more of data_tables.py: the two lines share the table half (shapes, schema,
loader and tests), which this module imports from data_tables.py, and differ in the fact half. A GitHub file is
proven by git blob identity under a repository licence that GitHub's licence interface and the licence file
agree on; a publisher's file is proven by its retrieved bytes under a licence the publisher states for that exact
series or release, and a catalogue of 1,498 series is read and decided series by series. Keeping the fact half
apart leaves every GitHub table's package byte for byte as it was.
"""
from __future__ import annotations

import csv
import fnmatch
import hashlib
import html
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from loop_engine.core.library_ingestion.licences import match_licence
from loop_engine.core.library_ingestion.request_log import PauseExceedsBound, RequestCeilingReached

from .data_tables import (
    LOADER_BODY, TESTS, TEXT_SHAPES, TableRefused, _missing_key, _wrong_key, infer_schema, parts_slots, table_rows,
    table_schema, text_shape_line)
from .openapi_operations import literal, run_tests
from .packaging import (
    LICENCE_NAME, MAXIMUM_REVIEW_FILE_BYTES, MAXIMUM_REVIEW_PACKAGE_BYTES, UPSTREAM_LICENCE_NAME, PackageFile,
    SupplyPackage, build)
from .reading import is_https
from .records import (
    ALLOWED_LICENCES, BLOCKED_BY_STATIC_CHECK, GENERATED_CODE_LICENCE, LICENCE_EVIDENCE, LICENCE_TEXT, ORIGINS,
    PACKAGE_ABOVE_REVIEW_BOUND, PUBLISHER_TABLES, UPSTREAM_VERBATIM, SupplyRecordError, fact_source, provenance,
    refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
SOURCES_FILE = Path(__file__).with_name("publisher_table_sources.json")
SOURCES_RECORD_TYPE = "library_supply_publisher_table_sources/v1"
SDG_RULES_RECORD_TYPE = "library_supply_sdg_goal_rules/v1"
#: The record type of a run's SDG proposal, the one artifacts/sdg-supply-2026-10-01/sdg-source-map.json uses.
SDG_MAP_RECORD_TYPE = "sdg_supply_source_map/v1"
NATIVE_FORMAT = "reference_data_table"
WORLD_BANK_SERIES, DECLARED_TABLES = MODES = ("world_bank_series", "declared_tables")
SERIES_METADATA, COLLECTION_STATEMENT = LICENCE_RULES = ("series_metadata", "collection_statement")
#: The largest archive member read; a declared table is far smaller, and this bounds a damaged archive.
MAXIMUM_MEMBER_BYTES = 128 * 1024 * 1024
#: Room a package keeps for its generated files (loader, schema, tests, README, attribution) when the line
#: decides, before writing them, whether a table can fit the package bound; the build checks the exact total.
GENERATED_ROOM_BYTES = 96 * 1024
#: Failed answers in a row after which a run stops reading a publisher, so a struggling service is not pressed.
MAXIMUM_FAILURES_IN_A_ROW = 5
#: The reasons that say the publisher could not be read, which make a run incomplete (it withdraws nothing).
UNREAD_REASONS = ("source_unreadable", "licence_evidence_missing")
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{1,60}\Z")
_SERIES = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_UTF8_MARK = b"\xef\xbb\xbf"
#: Cells of a README table hold one line without the column separator.
_CELL = str.maketrans({"|": "/", "\n": " ", "\r": " "})


def _host(address: str) -> str:
    return urlsplit(str(address).replace("{series}", "x")).hostname or ""


def _collection_problems(collection: dict, texts: dict) -> list:
    """What makes a declared collection unusable; empty when it is complete."""
    problems = []
    hosts = collection.get("hosts") or []
    if collection.get("mode") not in MODES:
        problems.append(f"mode {collection.get('mode')!r}")
    if collection.get("origin") not in ORIGINS or ORIGINS.get(collection.get("origin")) not in hosts:
        problems.append("its origin is not a known origin whose host it declares")
    if not _IDENTIFIER.match(str(collection.get("table_prefix", ""))):
        problems.append("table_prefix")
    addresses = [collection.get("data_address")]
    if collection.get("mode") == WORLD_BANK_SERIES:
        addresses += [collection.get("catalogue"), collection.get("metadata_address")]
    licence = collection.get("licence") or {}
    if licence.get("rule") == COLLECTION_STATEMENT:
        addresses.append(licence.get("evidence_address"))
        if licence.get("spdx") not in texts or not licence.get("statement") or not licence.get("archive_member") \
                or not licence.get("archive_statement"):
            problems.append("a collection statement names an allowlisted licence with a text, its statement, the "
                            "release's own notice file and that notice's statement")
    elif licence.get("rule") == SERIES_METADATA:
        values = licence.get("values") or {}
        if not licence.get("field") or not values or any(spdx not in texts for spdx in values.values()):
            problems.append("a series rule names its field and maps exact values to allowlisted licences with texts")
    else:
        problems.append(f"licence rule {licence.get('rule')!r}")
    for address in addresses:
        if not address or not is_https(address) or _host(address) not in hosts:
            problems.append(f"{str(address)[:80]} is not an HTTPS address on a declared host")
    if collection.get("shape") not in TEXT_SHAPES:
        problems.append("the shape is a delimited text table")
    if collection.get("mode") == DECLARED_TABLES:
        seen = set()
        for row in collection.get("tables") or [None]:
            if not isinstance(row, list) or len(row) != 5 or not _IDENTIFIER.match(str(row[0])) or row[0] in seen:
                problems.append(f"table {str(row)[:60]}")
                continue
            seen.add(row[0])
        sdg = collection.get("sdg") or {}
        if not _goals_valid(sdg.get("goals")) or not sdg.get("reason"):
            problems.append("declared tables name their SDG goals and the reason")
    else:
        missing = [name for name in ("sdg_rules", "archive_member", "file_name", "metadata_file_name", "key_field")
                   if not collection.get(name)]
        if missing:
            problems.append(f"a series catalogue names {', '.join(missing)}")
    if not collection.get("attribution") or not collection.get("publisher") or not collection.get("title"):
        problems.append("a collection names its publisher, title and attribution")
    return problems


def read_sources(path: Path = SOURCES_FILE) -> dict:
    """The declared collections, each checked; a collection that cannot be read as declared stops the line."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SOURCES_RECORD_TYPE:
        raise ValueError(f"expected {SOURCES_RECORD_TYPE}")
    texts = record.get("licence_texts") or {}
    if any(spdx not in ALLOWED_LICENCES or not isinstance(text, dict) or not is_https(text.get("legal_code", ""))
           or not is_https(text.get("deed", "")) for spdx, text in texts.items()):
        raise ValueError("a licence text is an allowlisted licence's legal code and deed at HTTPS addresses")
    if sorted(record.get("sdg_goal_names") or {}, key=int) != [str(goal) for goal in range(1, 18)]:
        raise ValueError("sdg_goal_names names the 17 goals")
    for collection_id, collection in record["collections"].items():
        problems = _collection_problems(collection, texts) if _IDENTIFIER.match(collection_id) else ["its name"]
        if problems:
            raise ValueError(f"publisher_table_sources.json: {collection_id}: {'; '.join(problems)}")
    return record


def hosts(sources: dict, collection_id: str) -> tuple:
    """Every host a run of one collection reads: the collection's own and the licence texts' stewards."""
    return tuple(sorted(set(sources["collections"][collection_id]["hosts"])
                        | {_host(text["legal_code"]) for text in sources["licence_texts"].values()}))


def _goals_valid(goals) -> bool:
    return (isinstance(goals, list) and all(type(goal) is int and 1 <= goal <= 17 for goal in goals)
            and len(set(goals)) == len(goals))


def read_sdg_rules(path: Path) -> dict:
    """The SDG goal rules of a collection: code prefixes and topics, each with its goals and its reason."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != SDG_RULES_RECORD_TYPE:
        raise ValueError(f"expected {SDG_RULES_RECORD_TYPE}")
    prefixes = [rule["prefix"] for rule in record["code_prefixes"]]
    rules = list(record["code_prefixes"]) + list(record["topics"].values())
    if len(set(prefixes)) != len(prefixes) or any(not _goals_valid(rule.get("goals")) or not rule.get("reason")
                                                  for rule in rules):
        raise ValueError(f"{Path(path).name}: every rule names distinct goals from 1 to 17 and its reason")
    return record


def sdg_goals(series: str, topic: str, rules: dict) -> dict:
    """The proposed goals of one series: the longest code prefix it starts with, else its exact topic, else none."""
    matches = [rule for rule in rules["code_prefixes"] if series.startswith(rule["prefix"])]
    if matches:
        rule = max(matches, key=lambda rule: len(rule["prefix"]))
        return {"goals": sorted(rule["goals"]), "rule": f"code_prefix:{rule['prefix']}", "reason": rule["reason"]}
    name = str(topic or "").strip()
    found = rules["topics"].get(name)
    if found is not None:
        return {"goals": sorted(found["goals"]), "rule": f"topic:{name}", "reason": found["reason"]}
    return {"goals": [], "rule": "none", "reason": f"no rule names the code or the topic {name!r}"}


def series_licence(metadata: dict, rule: dict) -> tuple:
    """(SPDX identifier or None, decision, the publisher's own value, the licence address it names) of one series.

    Only an exact value the declaration maps to an allowlisted licence passes; a missing value is unknown and any
    other value is refused as off the allowlist, whatever licence it names."""
    value = metadata.get(rule["field"])
    address = str(metadata.get(rule.get("address_field") or "", "") or "")
    if not isinstance(value, str) or not value.strip():
        return None, "licence_unknown", value, address
    spdx = rule["values"].get(value.strip())
    if spdx is None or spdx not in ALLOWED_LICENCES:
        return None, "licence_not_on_allowlist", value, address
    return spdx, "agreed", value, address


def states(document: bytes, statement: str) -> bool:
    """Whether a page or a text states a sentence, compared without markup, entities, case or spacing."""
    text = document.decode("utf-8", "replace")
    text = re.sub(r"<(script|style)\b.*?</\1\s*>", " ", text, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return " ".join(statement.split()).casefold() in " ".join(text.split()).casefold()


def world_bank_metadata(document, series: str) -> "dict | None":
    """The metadata fields (metatype name to value) the World Bank's API gives one series, or None."""
    for source in (document.get("source") or []) if isinstance(document, dict) else ():
        for concept in source.get("concept") or []:
            for variable in concept.get("variable") or []:
                if concept.get("id") == "Series" and variable.get("id") == series:
                    return {str(item.get("id")): item.get("value") for item in variable.get("metatype") or []}
    return None


def archive_member(body: bytes, pattern: str) -> tuple:
    """(name, bytes) of the one member of a ZIP archive whose name matches the pattern (shell wildcards), compared
    without regard to case: the World Bank writes some series codes in upper case in its member names
    (API_PER_ALLSP.COV_POP_TOT_... for per_allsp.cov_pop_tot). More than one match refuses, as none does."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
        found = [info for info in archive.infolist()
                 if not info.is_dir() and fnmatch.fnmatchcase(info.filename.casefold(), pattern.casefold())]
    except (zipfile.BadZipFile, ValueError) as error:
        raise TableRefused("source_unreadable", f"not a ZIP archive: {type(error).__name__}") from None
    if len(found) != 1:
        raise TableRefused("archive_member_missing", f"{len(found)} members match {pattern}")
    if found[0].file_size > MAXIMUM_MEMBER_BYTES:
        raise TableRefused("table_above_review_bound", f"{found[0].filename}: {found[0].file_size} bytes")
    try:
        return found[0].filename, archive.read(found[0])
    except (zipfile.BadZipFile, RuntimeError, ValueError, OSError) as error:
        raise TableRefused("source_unreadable", f"{found[0].filename}: {type(error).__name__}") from None


def record_ends(data: bytes, delimiter: str) -> list:
    """The byte offsets just after each record of a delimited text file, as its shape's own reader reads records
    (a quoted value may hold a line break, so a line end is not always a record end)."""
    start = len(_UTF8_MARK) if data.startswith(_UTF8_MARK) else 0
    try:
        lines = list(io.StringIO(data[start:].decode("utf-8"), newline=""))
    except UnicodeDecodeError:
        raise TableRefused("source_unreadable", "the file is not UTF-8 text") from None
    line_ends, position = [], start
    for line in lines:
        position += len(line.encode("utf-8"))
        line_ends.append(position)
    reader = csv.reader(iter(lines), delimiter=delimiter)
    ends = []
    try:
        for _values in reader:
            ends.append(line_ends[reader.line_num - 1])
    except csv.Error as error:
        raise TableRefused("source_unreadable", f"not a delimited text table: {error}"[:200]) from None
    return ends


def split_at_record_ends(data: bytes, delimiter: str, bound: int = MAXIMUM_REVIEW_FILE_BYTES) -> list:
    """The size rule: the file whole when it is within the bound, else consecutive parts of at most ``bound``
    bytes, each ending at a record end, that join to the file exactly. A record longer than the bound cannot be
    cut and refuses the table."""
    if len(data) <= bound:
        return [data]
    parts, start, cut = [], 0, 0
    for end in record_ends(data, delimiter) + [len(data)]:
        if end - start <= bound:
            cut = end
            continue
        if cut == start or end - cut > bound:
            raise TableRefused("table_above_review_bound", f"a record after byte {cut} is longer than {bound} bytes")
        parts.append(data[start:cut])
        start = cut
        cut = end
    parts.append(data[start:])
    if b"".join(parts) != data or any(len(part) > bound for part in parts):
        raise TableRefused("table_above_review_bound", "the file could not be cut at record ends within the bound")
    return parts


def part_names(file_name: str, count: int) -> list:
    """The file's own name when it is kept whole, else <stem>-part-<i>-of-<n><suffix> in order."""
    if count == 1:
        return [file_name]
    path = PurePosixPath(file_name)
    return [f"{path.stem}-part-{index}-of-{count}{path.suffix}" for index in range(1, count + 1)]


def preamble(text: str, delimiter: str, skip_rows: int) -> dict:
    """The name and value pairs of the lines before a table's header (a publisher's title and date lines)."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    pairs = {}
    for _number, values in zip(range(skip_rows), reader):
        filled = [value for value in values if value]
        if len(filled) >= 2:
            pairs[filled[0]] = filled[1]
    return pairs


def observations(table: list, pattern: "str | None") -> dict:
    """How many rows hold a value in the fields the pattern names (years), and the first and last such field."""
    if not pattern:
        return {}
    matcher = re.compile(pattern)
    names = sorted({name for row in table for name in row if matcher.fullmatch(str(name))})
    filled = [name for name in names if any(row.get(name) not in (None, "") for row in table)]
    rows = sum(1 for row in table if any(row.get(name) not in (None, "") for name in names))
    values = sum(1 for row in table for name in names if row.get(name) not in (None, ""))
    return {"fields": len(names), "first_field": names[0] if names else None, "last_field": names[-1] if names else None,
            "rows_with_values": rows, "values": values, "first_observed": filled[0] if filled else None,
            "last_observed": filled[-1] if filled else None}


# -- the licence texts --------------------------------------------------------------------------------------------
def licence_texts(reader, sources: dict) -> dict:
    """SPDX identifier to (address, fetched answer, deed) of each declared legal code whose text matches its
    licence."""
    found = {}
    for spdx, text in sorted(sources["licence_texts"].items()):
        address = text["legal_code"]
        answer = reader.get(address)
        if answer.status != 200:
            continue
        try:
            matched = match_licence(answer.body.decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001 - an unreadable text is no licence text, never a pass
            continue
        if matched.spdx == spdx:
            found[spdx] = (address, answer, text["deed"])
    return found


# -- rows of a collection -------------------------------------------------------------------------------------------
def _catalogue(reader, address: str) -> list:
    """Every entry of a World Bank API catalogue, page by page ([pagination, entries] per page)."""
    entries, page, pages = [], 1, 1
    while page <= pages:
        answer = reader.get(address if page == 1 else f"{address}&page={page}")
        if answer.status != 200:
            raise LookupError(f"the catalogue answered {answer.status} on page {page}")
        head, rows = json.loads(answer.body)
        pages = int(head.get("pages") or 1)
        entries += rows or []
        page += 1
    return entries


def _table_id(collection: dict, name: str) -> str:
    return f"{collection['table_prefix']}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}"


def world_bank_rows(reader, collection_id: str, collection: dict, rules: dict, only=(), maximum: int = 0,
                    deeds: "dict | None" = None) -> tuple:
    """(rows, refusals, summary) of a World Bank series catalogue: each series whose own metadata states a licence
    the declaration allows, with its metadata, its SDG goals and the facts the README names."""
    rows, refused, decisions = [], [], Counter()
    entries = _catalogue(reader, collection["catalogue"])
    if only:
        wanted = set(only)
        entries = [entry for entry in entries if entry.get("id") in wanted]
    if maximum:
        entries = entries[:maximum]
    failures, stopped, seen = 0, None, set()
    for number, entry in enumerate(entries):
        series = str(entry.get("id") or "")
        table_id = _table_id(collection, series)
        if not _SERIES.match(series) or not _IDENTIFIER.match(table_id):
            refused.append(refusal(PUBLISHER_TABLES, "source_unreadable", series[:80], "not a series code"))
            continue
        if table_id in seen:
            refused.append(refusal(PUBLISHER_TABLES, "duplicate_table", series, f"{table_id} is taken"))
            continue
        seen.add(table_id)
        address = collection["metadata_address"].format(series=series)
        try:
            answer = reader.get(address)
        except (RequestCeilingReached, PauseExceedsBound) as error:
            stopped = {"reason": type(error).__name__, "series_left": len(entries) - number}
            break
        if answer.status != 200:
            failures += 1
            refused.append(refusal(PUBLISHER_TABLES, "source_unreadable", series, f"metadata answered {answer.status}"))
            if failures >= MAXIMUM_FAILURES_IN_A_ROW:
                stopped = {"reason": "failed_answers_in_a_row", "series_left": len(entries) - number - 1}
                break
            continue
        failures = 0
        try:
            fields = world_bank_metadata(json.loads(answer.body), series)
        except ValueError:
            fields = None
        if fields is None:
            refused.append(refusal(PUBLISHER_TABLES, "licence_unknown", series, "the metadata holds no such series"))
            continue
        spdx, decision, value, licence_address = series_licence(fields, collection["licence"])
        decisions[(decision, str(value)[:80])] += 1
        if spdx is None:
            refused.append(refusal(PUBLISHER_TABLES, decision, series,
                                   f"{collection['licence']['field']} {str(value)[:200]!r} at {address}"))
            continue
        name = str(fields.get("IndicatorName") or entry.get("name") or series)
        rows.append({
            "collection_id": collection_id, "table_id": table_id, "title": name, "series": series,
            "path": series, "address": collection["data_address"].format(series=series),
            "member": collection["archive_member"].format(series=series),
            "file_name": collection["file_name"].format(series=series),
            "key_field": collection["key_field"],
            "licence": {"spdx": spdx, "value": value, "address": licence_address,
                        "basis": f"series_metadata_{collection['licence']['field']}",
                        "evidence": answer, "evidence_url": address},
            "extra_files": [{"path": "data/" + collection["metadata_file_name"].format(series=series),
                             "answer": answer, "url": address}],
            "sdg": sdg_goals(series, str(fields.get("Topic") or ""), rules),
            "about": [("Series", f"{name} (`{series}`)"),
                      ("Unit", fields.get("Unitofmeasure") or "as the series name states"),
                      ("Periodicity", fields.get("Periodicity") or ""),
                      ("Reference period", fields.get("Referenceperiod") or ""),
                      ("Topic", fields.get("Topic") or ""),
                      ("Source", fields.get("Source") or entry.get("sourceOrganization") or "")],
            "licence_line": (f"CC BY 4.0 for this series: its World Bank metadata gives "
                             f"`{collection['licence']['field']}` \"{value}\" ({licence_address}); evidence {address}"),
            "definition": [("Definition", fields.get("Longdefinition")),
                           ("Limitations and exceptions", fields.get("Limitationsandexceptions"))],
            "lead": (f"World Development Indicators series `{series}` from {collection['publisher']}, as one table: "
                     "every economy and aggregate (regions and income groups are rows too) in one row each, keyed "
                     "by `Country Code`, and one column per year."),
            "attribution": collection["attribution"].format(
                name=name, series=series, source=" ".join(str(fields.get("Source") or "").split()) or "not named",
                licence_address=licence_address or (deeds or {}).get(spdx, "")),
        })
    summary = {"catalogue_entries": len(entries), "licence_decisions": [
        {"decision": decision, "value": value, "series": count} for (decision, value), count in decisions.most_common()],
        "stopped": stopped}
    return rows, refused, summary


def declared_rows(reader, collection_id: str, collection: dict, only=()) -> tuple:
    """(rows, refusals, summary) of a release whose tables the declaration names: the publisher's licence page and
    the release's own Read Me must both state the declared licence, or every table is refused."""
    tables = [row for row in collection["tables"] if not only or row[0] in only]
    licence = collection["licence"]
    archive = reader.get(collection["data_address"])
    page = reader.get(licence["evidence_address"])

    def everything(reason, detail):
        return [], [refusal(PUBLISHER_TABLES, reason, f"{collection['table_prefix']}_{row[0]}", detail)
                    for row in tables], {"tables_declared": len(tables), "release": None}

    if archive.status != 200:
        return everything("source_unreadable", f"{collection['data_address']} answered {archive.status}")
    if page.status != 200 or not states(page.body, licence["statement"]):
        return everything("licence_evidence_missing", f"{licence['evidence_address']} does not state the licence")
    try:
        _name, notice = archive_member(archive.body, licence["archive_member"])
    except TableRefused as error:
        return everything("licence_evidence_missing", f"{licence['archive_member']}: {error.detail}")
    if not states(notice, licence["archive_statement"]):
        return everything("licence_evidence_missing", f"{licence['archive_member']} does not state the licence")
    release = ", ".join(line.strip() for line in notice.decode("utf-8", "replace").splitlines()[:2] if line.strip())
    rows = []
    for table_id, title, member, key_field, description in tables:
        rows.append({
            "collection_id": collection_id, "table_id": f"{collection['table_prefix']}_{table_id}", "title": title,
            "heading": f"{title}, {collection['title']}", "series": title, "path": member,
            "address": collection["data_address"], "member": member,
            "file_name": re.sub(r"[^a-z0-9.]+", "_", PurePosixPath(member).name.lower()),
            "key_field": key_field, "archive": archive,
            "licence": {"spdx": licence["spdx"], "value": licence["statement"], "address": licence["evidence_address"],
                        "basis": "publisher_licence_page_and_release_notice", "evidence": page,
                        "evidence_url": licence["evidence_address"]},
            "extra_files": [],
            "sdg": {"goals": sorted(collection["sdg"]["goals"]), "rule": f"collection:{collection_id}",
                    "reason": collection["sdg"]["reason"]},
            "about": [("Table", f"`{member}` of the text release"), ("Release", release),
                      ("Publisher", collection["publisher"])],
            "licence_line": (f"CC BY 4.0 for the release: {licence['evidence_address']} and the release's own "
                             f"`{licence['archive_member']}` state it"),
            "definition": [],
            "lead": f"{description} From the {collection['title']}, published by {collection['publisher']}.",
            "attribution": collection["attribution"],
        })
    return rows, [], {"tables_declared": len(tables), "release": release,
                      "archive_sha256": archive.sha256, "archive_bytes": len(archive.body)}


# -- one package ------------------------------------------------------------------------------------------------------
PUBLISHER_LOADER_HEADER = '''"""{title}: a typed reference table of {count} rows.

Loaded from data/{first_file}: the exact bytes {publisher} publishes at
{address}
{member}retrieved {retrieved_at} and licensed {licence}.
Baltor generated this loader, schema.json and the tests; see README.md.
"""
'''


def _docstring_text(value) -> str:
    return " ".join(str(value).replace("\\", "/").replace('"""', "'''").split())


def _fields_section(row: dict, fields: dict, required: list) -> str:
    key = row["key_field"] or "row"
    lead = (f"The key is `{key}`; every key is unique." if row["key_field"] else
            "The key is `row`, the row's number in the file (from 1), which the loader adds; every key is unique.")
    if len(fields) > 24:
        names = ", ".join(f"`{name}`" for name in fields)
        kinds = sorted({kind for value in fields.values() for kind in value})
        return (f"{lead} Every field is {' or '.join(kinds)} and every row holds every field. The values are text "
                f"exactly as published; an empty value means no data.\n\nFields: {names}.")
    lines = [f"| `{name}` | {' or '.join(kinds)} | {'yes' if name in required else 'no'} |"
             for name, kinds in fields.items()]
    return (f"{lead} The values are text exactly as published.\n\n| Field | Type | In every row |\n|---|---|---|\n"
            + "\n".join(lines))


def _example_rows(table: list, count: int = 2) -> str:
    def cut(value):
        return value if not isinstance(value, str) or len(value) <= 160 else value[:157] + "..."
    return json.dumps([{name: cut(value) for name, value in row.items()} for row in table[:count]], indent=1,
                      ensure_ascii=False)


def readme(row: dict, *, collection: dict, table: list, fields: dict, required: list, module: str, names: list,
           data: bytes, data_sha256: str, fetched, member_name: "str | None", pairs: dict, seen: dict,
           goal_names: dict, deed: str) -> str:
    """README.md: the series or table, unit, period, source, licence, SDG goals, fields, use and attribution."""
    about = [(label, value) for label, value in row["about"] if str(value or "").strip()]
    about += [(label, value) for label, value in pairs.items()]
    if seen:
        about.append(("Values", f"{seen['rows_with_values']} of {len(table)} rows hold at least one value; observed "
                                f"years {seen['first_observed']} to {seen['last_observed']}, in columns "
                                f"{seen['first_field']} to {seen['last_field']}"))
    goals = row["sdg"]["goals"]
    goal_text = (", ".join(f"{goal} ({goal_names.get(str(goal), '')})" for goal in goals) if goals else "none")
    about += [("Licence", row["licence_line"]),
              ("SDG goals", f"{goal_text}; rule `{row['sdg']['rule']}`: {row['sdg']['reason']}"),
              ("Retrieved", f"{fetched.retrieved_at} from {row['address']}"
                            + (f", archive member `{member_name}`" if member_name else "")
                            + f"; data SHA-256 `{data_sha256}`")]
    table_lines = "\n".join(f"| {label} | {str(value).translate(_CELL).strip()} |" for label, value in about)
    sections = "".join(f"\n## {label}\n\n{' '.join(str(text).split())}\n" for label, text in row["definition"]
                       if str(text or "").strip())
    if len(names) > 1:
        layout = (f"The published file is {len(data):,} bytes, above the {MAXIMUM_REVIEW_FILE_BYTES // 1024} KiB a "
                  f"reviewer reads in one file, so it is kept as {len(names)} consecutive parts cut at record ends: "
                  + ", ".join(f"`data/{name}`" for name in names)
                  + ". Joined in order they are the published bytes exactly; the loader joins them and checks the "
                    "SHA-256 above.")
    else:
        layout = f"`data/{names[0]}` is the published file byte for byte."
    extras = "".join(f" `{extra['path']}` is the publisher's metadata of the series, byte for byte."
                     for extra in row["extra_files"])
    first = table[0][row["key_field"] or "row"]
    return f"""# {row.get('heading') or row['title']}

{row['lead']} {len(table)} rows.

| | |
|---|---|
{table_lines}
{sections}
## Fields

{_fields_section(row, fields, required)}

## First rows

```json
{_example_rows(table, 1 if len(fields) > 24 else 2)}
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

## Data files

{layout}{extras}

## Attribution

{row['attribution']}

The data files are the publisher's bytes, unchanged. Baltor generated the
loader, `schema.json`, the tests and this README; {collection['publisher']}
has not reviewed or endorsed them. Licence: {deed} (its legal code is
`UPSTREAM-LICENSE`).
"""


def table_package(row: dict, *, collection: dict, texts: dict, generator: dict, licence_text: bytes,
                  generated_on: str, staging: Path, goal_names: dict) -> tuple:
    """(payload, bodies) of one table, or raise TableRefused or SupplyRecordError with the reason."""
    fetched = row["archive"]
    if fetched.status != 200:
        raise TableRefused("source_unreadable", f"{row['address']} answered {fetched.status}")
    member_name, data = archive_member(fetched.body, row["member"]) if row.get("member") else (None, fetched.body)
    shape, delimiter = collection["shape"], TEXT_SHAPES[collection["shape"]]
    skip_rows, trailing = int(collection.get("skip_rows") or 0), bool(collection.get("trailing_delimiter"))
    key_field = row["key_field"] or "row"
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise TableRefused("source_unreadable", "the table is not UTF-8 text") from None
    table = table_rows(text, shape, key_field, None, skip_rows=skip_rows, trailing_delimiter=trailing)
    seen = observations(table, collection.get("observation_fields"))
    if seen and not seen["values"]:
        raise TableRefused("no_observations", f"no row holds a value in the {seen['fields']} year columns")
    licence_url, licence_answer, deed = texts[row["licence"]["spdx"]]
    extra_bytes = sum(len(extra["answer"].body) for extra in row["extra_files"])
    fixed = len(data) + extra_bytes + len(licence_text) + len(licence_answer.body)
    if fixed + GENERATED_ROOM_BYTES > MAXIMUM_REVIEW_PACKAGE_BYTES:
        raise TableRefused("table_above_review_bound",
                           f"{len(data)} bytes of data; a package holds at most {MAXIMUM_REVIEW_PACKAGE_BYTES} bytes")
    parts = split_at_record_ends(data, delimiter)
    names = part_names(row["file_name"], len(parts))
    data_sha256 = hashlib.sha256(data).hexdigest()
    fields, required = infer_schema(table)
    module = f"{row['table_id']}_table"
    header = PUBLISHER_LOADER_HEADER.format(
        title=_docstring_text(row["title"]), count=len(table), first_file=names[0],
        publisher=_docstring_text(collection["publisher"]), address=row["address"],
        member=f"(archive member {_docstring_text(member_name)}), " if member_name else "",
        retrieved_at=fetched.retrieved_at, licence=row["licence"]["spdx"])
    loader = header + LOADER_BODY.format(
        file_name=names[0], sha256=data_sha256, key_field=key_field, value_line="", fields=literal(fields, 0),
        required=literal(required), count=len(table),
        shape_line=text_shape_line(shape, row["key_field"] is None, skip_rows, trailing), **parts_slots(names))
    key_kinds = fields[key_field]
    class_name = "".join(part.capitalize() for part in row["table_id"].split("_")) + "TableTest"
    tests = TESTS.format(table_id=row["table_id"], module=module, class_name=class_name,
                         first_key=table[0][key_field], missing_key=_missing_key(table, key_field, key_kinds),
                         wrong_key=_wrong_key(key_kinds))
    described = {"publisher": collection["publisher"], "collection": collection["title"], "series": row["series"],
                 "source_address": row["address"]}
    if member_name:
        described["archive_member"] = member_name
    if len(names) > 1:
        described["data_parts"] = [f"data/{name}" for name in names[1:]]
    if skip_rows or trailing:
        described.update({"skip_rows": skip_rows, "trailing_delimiter": trailing})
    schema = table_schema(row["title"], fields, required, key_field, len(table), shape, f"data/{names[0]}",
                          data_sha256, **described)
    schema_text = json.dumps(schema, indent=1, ensure_ascii=False) + "\n"
    folder = staging / module
    (folder / "data").mkdir(parents=True, exist_ok=True)
    for name, part in zip(names, parts):
        (folder / "data" / name).write_bytes(part)
    (folder / f"{module}.py").write_text(loader, encoding="utf-8")
    (folder / f"test_{module}.py").write_text(tests, encoding="utf-8")
    passed, count, output = run_tests(folder, module)
    if not passed:
        raise SupplyRecordError("generated_test_failed", output[-280:])
    pairs = preamble(text, delimiter, skip_rows) if skip_rows else {}
    text_readme = readme(row, collection=collection, table=table, fields=fields, required=required, module=module,
                         names=names, data=data, data_sha256=data_sha256, fetched=fetched, member_name=member_name,
                         pairs=pairs, seen=seen, goal_names=goal_names, deed=deed)
    offsets = [0]
    for part in parts:
        offsets.append(offsets[-1] + len(part))
    files = []
    for index, (name, part) in enumerate(zip(names, parts)):
        upstream = {"url": row["address"], "sha256": hashlib.sha256(part).hexdigest()}
        if member_name:
            upstream.update({"archive_member": member_name, "archive_sha256": fetched.sha256})
        if len(parts) > 1:
            upstream.update({"file_sha256": data_sha256, "part": [index + 1, len(parts)],
                             "byte_range": [offsets[index], offsets[index + 1]]})
        files.append(PackageFile(f"data/{name}", part, "other", UPSTREAM_VERBATIM, upstream))
    for extra in row["extra_files"]:
        files.append(PackageFile(extra["path"], extra["answer"].body, "other", UPSTREAM_VERBATIM,
                                 {"url": extra["url"], "sha256": extra["answer"].sha256}))
    files += [PackageFile("schema.json", schema_text.encode(), "other"),
              PackageFile(f"{module}.py", loader.encode(), "executable_tool"),
              PackageFile(f"test_{module}.py", tests.encode(), "executable_tool"),
              PackageFile("README.md", text_readme.encode(), "other"),
              PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
              PackageFile(UPSTREAM_LICENCE_NAME, licence_answer.body, "other", LICENCE_TEXT,
                          {"url": licence_url, "sha256": licence_answer.sha256})]
    spdx = row["licence"]["spdx"]
    evidence = row["licence"]["evidence"]
    facts = [fact_source(row["address"], fetched.retrieved_at, fetched.sha256, len(fetched.body), "data_source",
                         spdx=spdx, basis=row["licence"]["basis"], evidence_sha256=evidence.sha256),
             fact_source(row["licence"]["evidence_url"], evidence.retrieved_at, evidence.sha256, len(evidence.body),
                         LICENCE_EVIDENCE, spdx=spdx, basis=row["licence"]["basis"]),
             fact_source(licence_url, licence_answer.retrieved_at, licence_answer.sha256, len(licence_answer.body),
                         "licence_text", spdx=spdx, basis="legal_code_from_the_licence_steward")]
    name = f"{row['table_id'].replace('_', '-')}-table"
    named = row["title"] if row["series"] == row["title"] else f"{row['title']} ({row['series']})"
    identity = f"{row['collection_id']}:{row['series']}"
    supply = SupplyPackage(
        line=PUBLISHER_TABLES, identity=identity, key=upstream_key(PUBLISHER_TABLES, identity), kind="code_module",
        native_format=NATIVE_FORMAT, form="data_table", name=name,
        description=(f"{named}, {collection['publisher']}, {collection['title']}: {len(table)} rows with a JSON "
                     "Schema, a checked loader and tests."),
        files=files, licence_expression=f"{spdx} AND {GENERATED_CODE_LICENCE}",
        provenance=provenance(collection["origin"], collection["repository"], row["path"], f"sha256:{data_sha256}",
                              facts, generator),
        placements=[{"harness": "reference", "path": f"tools/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=[("reads_fs", "the loader reads its data file")], credentials=[],
        tests={"files": [f"test_{module}.py"], "command": f"python -m unittest test_{module}", "result": "passed",
               "tests_run": count, "network": False},
        repository={"name": collection["title"], "publisher": collection["publisher"], "series": row["series"],
                    "table_id": row["table_id"], "rows": len(table), "fields": len(fields), "parts": len(parts),
                    "sdg_goals": list(row["sdg"]["goals"]), "sdg_rule": row["sdg"]["rule"],
                    "licence_evidence": row["licence"]["evidence_url"]},
        generated_on=generated_on, comparison_text=identity)
    return build(supply)


def generate(reader, collection_id: str, *, code_revision: str, licence_text: bytes, generated_on: str,
             staging: Path, sources: "dict | None" = None, only=(), maximum: int = 0) -> tuple:
    """(built, refusals, facts, summary) of one declared collection."""
    sources = sources or read_sources()
    collection = sources["collections"][collection_id]
    generator = {"identity": "tools/supply_lines/publisher_tables.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    rules = read_sdg_rules(SOURCES_FILE.with_name(collection["sdg_rules"])) if collection.get("sdg_rules") else None
    goal_names = sources["sdg_goal_names"]
    texts = licence_texts(reader, sources)
    if collection["mode"] == WORLD_BANK_SERIES:
        try:
            rows, refused, summary = world_bank_rows(reader, collection_id, collection, rules, only, maximum,
                                                     {spdx: text["deed"] for spdx, text in
                                                      sources["licence_texts"].items()})
        except (LookupError, ValueError, TypeError) as error:
            rows, summary = [], {"catalogue_entries": 0, "stopped": {"reason": "catalogue_unreadable"}}
            refused = [refusal(PUBLISHER_TABLES, "source_unreadable", collection["catalogue"], str(error)[:200])]
    else:
        rows, refused, summary = declared_rows(reader, collection_id, collection, only)
    built, facts, kept_goals, failures = [], {}, Counter(), 0
    for answer in [answer for _spdx, (_address, answer, _deed) in sorted(texts.items())]:
        facts[answer.sha256] = answer.body
    for number, row in enumerate(rows):
        if row["licence"]["spdx"] not in texts:
            refused.append(refusal(PUBLISHER_TABLES, "licence_unknown", row["table_id"],
                                   f"no legal code of {row['licence']['spdx']} could be read and matched"))
            continue
        if "archive" not in row:
            try:
                row["archive"] = reader.get(row["address"])
            except (RequestCeilingReached, PauseExceedsBound) as error:
                summary["stopped"] = {"reason": type(error).__name__, "tables_left": len(rows) - number}
                break
            failures = failures + 1 if row["archive"].status != 200 else 0
            if failures >= MAXIMUM_FAILURES_IN_A_ROW:
                refused.append(refusal(PUBLISHER_TABLES, "source_unreadable", row["table_id"],
                                       f"{row['address']} answered {row['archive'].status}"))
                summary["stopped"] = {"reason": "failed_answers_in_a_row", "tables_left": len(rows) - number - 1}
                break
        try:
            payload, bodies = table_package(row, collection=collection, texts=texts, generator=generator,
                                            licence_text=licence_text, generated_on=generated_on, staging=staging,
                                            goal_names=goal_names)
        except TableRefused as error:
            refused.append(refusal(PUBLISHER_TABLES, error.reason, row["table_id"], error.detail))
            continue
        except SupplyRecordError as error:
            reason = (error.code if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND)
                      else "generated_test_failed")
            refused.append(refusal(PUBLISHER_TABLES, reason, row["table_id"], str(error)[:280]))
            continue
        built.append((payload, bodies))
        kept_goals.update(row["sdg"]["goals"] or ["none"])
        for answer in [row["archive"], row["licence"]["evidence"]] + [extra["answer"] for extra in row["extra_files"]]:
            facts[answer.sha256] = answer.body
    summary["kept_per_goal"] = {str(goal): kept_goals[goal] for goal in sorted(kept_goals, key=str)}
    return built, refused, facts, summary


def sdg_map(built, created_on: str) -> dict:
    """The run's proposal in the shape of artifacts/sdg-supply-2026-10-01/sdg-source-map.json: table to goals."""
    sources = {payload["repository"]["table_id"]: payload["repository"]["sdg_goals"] for payload, _bodies in built}
    per_goal = Counter(goal for goals in sources.values() for goal in goals)
    return {"record_type": SDG_MAP_RECORD_TYPE, "created_on": created_on,
            "meaning": ("Proposed SDG goals per publisher table, from the line's goal rules. A proposal for reviewers "
                        "attaching PublicGoodGrant goals after independent approval; it grants nothing."),
            "sources": dict(sorted(sources.items())),
            "sources_per_goal": {str(goal): per_goal[goal] for goal in range(1, 18)},
            "without_goal": sum(1 for goals in sources.values() if not goals)}


def payload_counts(built) -> dict:
    """Distinct files of the run by what they are: the published data (whole files and parts), the publisher's
    metadata, generated files (loader, tests, schema, README) and supporting licence and attribution files."""
    kinds = {"data_tables": set(), "data_files": set(), "metadata_files": set(), "generated_files": set(),
             "supporting_files": set()}
    for payload, _bodies in built:
        texts = set(payload["licence"]["texts"]) | {payload["licence"]["attribution"]}
        for entry in payload["files"]:
            if entry["path"] in texts:
                kinds["supporting_files"].add(entry["digest"])
            elif entry["origin"] == UPSTREAM_VERBATIM and entry["path"].endswith(".metadata.json"):
                kinds["metadata_files"].add(entry["digest"])
            elif entry["origin"] == UPSTREAM_VERBATIM:
                kinds["data_files"].add(entry["digest"])
                kinds["data_tables"].add((entry["upstream"] or {}).get("file_sha256") or entry["digest"])
            else:
                kinds["generated_files"].add(entry["digest"])
    return {name: len(values) for name, values in kinds.items()}
