"""The staff Systems view: recorded release, catalogue and edge facts beside what the running service measures now.

Kind: internal service mechanics over one packaged record. It adds no runtime type, no store and no graph vertex.
Roadmap S-6.35.11 replaced the separate systems.baltor.ai portal, which served invented figures and unmeasured pass
labels without access control, with this view inside the existing staff Administration area.

```text
GET /api/v1/admin/systems            the overview: what the running service measures now, with its read time, the
                                     current deployment statement compared with the newest release record, the
                                     newest release with every row, and the index of every recorded entry
GET /api/v1/admin/systems?state=S    the rows in one result state, newest entry first, a page at a time
GET /api/v1/admin/systems?entry=ID   one entry and every row it holds, earlier attempts included
```

Who may read it is decided before this module runs: a signed-in staff member whose role holds `service.diagnostics`,
rechecked against the sign-out record and the session expiry (`AccountAdministration.systems`). A service key, an
ordinary account or another role is refused.

The recorded part is `systems_view.json` beside this module, written by `tools/build_systems_view.py` from the
release, catalogue and edge records of the repository and checked against `systems_view.schema.json`. The service
reads no artifacts folder and no roadmap at run time, and it serves the record through this route only: the file is
not in the served address table, so no public address returns it.

The five result states, passed, failed, pending, skipped and unknown, stay separate in every answer. A recorded row
names the source revision, the environment or host, the attempt and its time, and the record that holds it; what a
record does not state is null, never filled in. The live part is labelled as live and carries its read time.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import re

from .records import ServiceRuntimeError

PATH = "/api/v1/admin/systems"
RECORD_TYPE = "service_systems_view/v1"
RESULT_VERSION = "service_staff_systems/v1"
LIVE_VERSION = "service_staff_systems_live/v1"
RECORD_FILE = "systems_view.json"
SCHEMA_FILE = "systems_view.schema.json"
STATES = ("passed", "failed", "pending", "skipped", "unknown")
#: Rows in one page of a state's list. A page stays well inside the service's answer limit.
PAGE_SIZE = 25
MOST_PAGES = 10_000
QUERY_FIELDS = frozenset({"state", "entry", "page"})
_ENTRY = re.compile(r"[a-z0-9][a-z0-9.-]{0,159}")
_PAGE = re.compile(r"[1-9][0-9]{0,4}")
#: The entry fields the overview's index carries; the entry answer carries every field.
INDEX_FIELDS = ("id", "kind", "title", "number", "at", "source_revision", "environment_or_host", "evidence")


@lru_cache(maxsize=1)
def packaged_record():
    """The packaged record, checked against its schema once, and the SHA-256 of its exact bytes."""
    from importlib.resources import files
    folder = files("loop_engine").joinpath("core", "service_runtime")
    try:
        raw = folder.joinpath(RECORD_FILE).read_bytes()
        schema = folder.joinpath(SCHEMA_FILE).read_text("utf-8")
    except OSError:
        raise ServiceRuntimeError("systems_record_unavailable") from None
    return checked_record(raw, schema)


def checked_record(raw, schema_text):
    """(record, digest) for record bytes its schema accepts. Any other bytes are refused as unavailable evidence."""
    from jsonschema import Draft202012Validator
    try:
        value = json.loads(raw.decode("utf-8"))
        schema = json.loads(schema_text)
    except (UnicodeDecodeError, ValueError):
        raise ServiceRuntimeError("systems_record_unavailable") from None
    if not isinstance(value, dict) or value.get("record_type") != RECORD_TYPE:
        raise ServiceRuntimeError("systems_record_unavailable")
    if next(Draft202012Validator(schema).iter_errors(value), None) is not None:
        raise ServiceRuntimeError("systems_record_unavailable")
    return value, hashlib.sha256(raw).hexdigest()


def staff_query(fields):
    """The one view a query names: the overview, one state's page, or one entry. Anything else is refused."""
    if not isinstance(fields, dict) or set(fields) - QUERY_FIELDS:
        raise ServiceRuntimeError("invalid_systems_query")
    if not fields:
        return {"view": "overview"}
    if "entry" in fields:
        if set(fields) != {"entry"} or not isinstance(fields["entry"], str) or not _ENTRY.fullmatch(fields["entry"]):
            raise ServiceRuntimeError("invalid_systems_query")
        return {"view": "entry", "entry": fields["entry"]}
    if "state" not in fields or fields["state"] not in STATES:
        raise ServiceRuntimeError("invalid_systems_query")
    page = fields.get("page", "1")
    if not isinstance(page, str) or not _PAGE.fullmatch(page) or int(page) > MOST_PAGES:
        raise ServiceRuntimeError("invalid_systems_query")
    return {"view": "state", "state": fields["state"], "page": int(page)}


def live_reading(health, read_at):
    """What the running service measured for this request, labelled as live, with the moment it was read."""
    return {"record_type": LIVE_VERSION, "source": "measured by this service process for this request",
            "read_at": read_at, "health": health}


def _titled(record, rows):
    titles = {entry["id"]: entry["title"] for entry in record["entries"]}
    return [{**row, "entry_title": titles.get(row["entry"], row["entry"])} for row in rows]


def staff_view(query, *, live=None, loaded=None):
    """The answer for one checked query. `live` is the live reading, measured only for the overview."""
    record, digest = loaded or packaged_record()
    head = {"record_type": RESULT_VERSION, "view": query["view"], "states": list(STATES),
            "record": {"record_type": record["record_type"], "generated_by": record["generated_by"],
                       "reading_rules": record["reading_rules"], "sha256": digest}}
    if query["view"] == "overview":
        applications = [entry for entry in record["entries"] if entry["kind"] == "application_release"]
        newest = applications[0] if applications else None
        return {**head, "live": live, "current_deployment": record["current_deployment"],
                "newest": None if newest is None else {
                    "entry": newest, "rows": _titled(record, [row for row in record["rows"]
                                                              if row["entry"] == newest["id"]])},
                "entries": [{name: entry[name] for name in INDEX_FIELDS} for entry in record["entries"]]}
    if query["view"] == "entry":
        entry = next((item for item in record["entries"] if item["id"] == query["entry"]), None)
        if entry is None:
            raise ServiceRuntimeError("systems_entry_not_found")
        sources = [item for item in record["sources"] if item["path"] in (entry["evidence"], *entry["also_recorded_in"])
                   or any(row["evidence"] == item["path"] for row in record["rows"] if row["entry"] == entry["id"])]
        return {**head, "entry": entry, "rows": _titled(record, [row for row in record["rows"]
                                                                 if row["entry"] == entry["id"]]),
                "sources": sources}
    matching = [row for row in record["rows"] if row["state"] == query["state"]]
    start = (query["page"] - 1) * PAGE_SIZE
    return {**head, "state": query["state"], "page": query["page"], "page_size": PAGE_SIZE,
            "has_next": start + PAGE_SIZE < len(matching), "rows": _titled(record, matching[start:start + PAGE_SIZE])}
