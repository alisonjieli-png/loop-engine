"""Customer feedback on the library: ratings, requests for material and search gaps.

Kind: internal service adapter over the existing catalogue authority, in the
User Feedback Intelligence layer. Three typed records, each written through the
same atomic batch contract as every other service record, and read by staff.
The "report this item" operation is a separate package and is not here.

```text
feedback records
├── catalogue_item_rating/v1   one account's rating of one downloaded item,
│                              useful or not_useful, with an optional note the
│                              customer wrote on purpose; keyed by account and
│                              item, so a second rating replaces the first
├── material_request/v1        a bounded description of material a customer
│                              wants, written on purpose for staff; keyed by
│                              account and request identity, so a retry
│                              repeats one request instead of making two
└── search_gap/v1              an aggregate count of searches that found
                               nothing, keyed by the hour, the mode, the
                               declared filters and the library tiers; it
                               holds no account and never the query text
```

A rating needs a download. The account's own usage records say which items it
read and at which digest, so a rating of an item the account never downloaded,
or of a revision it never downloaded, is refused before any write.

The search gap record is metadata only. The published privacy notice promises
no log of requests that succeed and, since September 24, 2026, aggregate
counts; a record of the query text would need a notice change the owner
decides, so the text is left out here and the guard below refuses a payload
that carries it. Filter values are kept only when they are short tokens of a
declared attribute; anything else is counted as `other`.

Every refusal has its own code:

```text
feedback refusals
├── rating_value_invalid                 the value is not useful or not_useful
├── feedback_note_too_long               the note is over its bound or is not text
├── rating_requires_download             this account never downloaded that revision
├── material_request_description_invalid the description is missing, empty, over its bound or not text
├── material_request_identity_conflict   the same request identity with a different description
└── search_gap_holds_query_text          the gap payload carries the query, which is never stored
```
"""
from __future__ import annotations

import re
import time

from .account_policy import ACCOUNTS_LIST, USAGE_COUNTS, permissions_for
from .records import ACCESS_MANAGE_SCOPE, ServiceCommitUnknown, ServiceRuntimeError, canonical, digest, identifier
from .runtime import PROVISIONING_METADATA_SCOPE, USAGE, ServiceRuntime

RATING_KIND, REQUEST_KIND, GAP_KIND = "catalogue_item_rating", "material_request", "search_gap"
RATING_SCHEMA, REQUEST_SCHEMA, GAP_SCHEMA = "catalogue_item_rating/v1", "material_request/v1", "search_gap/v1"
RATING_RESULT_VERSION = "catalogue_item_rating_result/v1"
REQUEST_RESULT_VERSION = "material_request_result/v1"
GAP_RESULT_VERSION = "search_gap_result/v1"
STAFF_VIEW_VERSION = "service_feedback_view/v1"
SUMMARY_VERSION = "service_feedback_summary/v1"
RATE_OPERATION, REQUEST_MATERIAL_OPERATION = "rate", "request_material"
FEEDBACK_OPERATIONS = (RATE_OPERATION, REQUEST_MATERIAL_OPERATION)
FEEDBACK_TOOLS = {"provisioning_rate": RATE_OPERATION, "provisioning_request_material": REQUEST_MATERIAL_OPERATION}
REVIEW_TOOL = "feedback_review"
USEFUL, NOT_USEFUL = "useful", "not_useful"
RATING_VALUES = (USEFUL, NOT_USEFUL)
#: The most text a customer may type into a rating note and into a request for material.
NOTE_LIMIT = 500
DESCRIPTION_LIMIT = 2000
#: The fields of each operation. A field outside its set is refused, so a client cannot smuggle a query or a
#: file into a feedback record.
RATE_FIELDS = frozenset({"identity", "expected_digest", "value", "note"})
REQUEST_FIELDS = frozenset({"request_id", "description"})
#: What a search gap keeps of a request: nothing else, and never `query`.
GAP_FIELDS = ("mode", "filters", "library_tiers")
#: The one line a search answer carries when it found nothing.
ASK_FOR_MATERIAL_LINE = ("No item matched. You can ask for material: send the request_material operation to "
                         "/api/v1/provisioning with a short description of what the step needs.")
RATING_VALUE_INVALID = "rating_value_invalid"
NOTE_TOO_LONG = "feedback_note_too_long"
RATING_REQUIRES_DOWNLOAD = "rating_requires_download"
DESCRIPTION_INVALID = "material_request_description_invalid"
REQUEST_IDENTITY_CONFLICT = "material_request_identity_conflict"
GAP_HOLDS_QUERY_TEXT = "search_gap_holds_query_text"
_DIGEST = re.compile(r"[0-9a-f]{64}")
_FILTER_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")
OTHER_FILTER_VALUE = "other"


def request_schema(operation):
    """The existing customer-feedback fields, as closed MCP input schemas."""
    if operation == RATE_OPERATION:
        return {"type": "object", "additionalProperties": False,
                "required": ["identity", "expected_digest", "value"],
                "properties": {"identity": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
                               "expected_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                               "value": {"enum": list(RATING_VALUES)},
                               "note": {"type": "string", "maxLength": NOTE_LIMIT}}}
    if operation == REQUEST_MATERIAL_OPERATION:
        return {"type": "object", "additionalProperties": False, "required": ["request_id", "description"],
                "properties": {"request_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
                               "description": {"type": "string", "minLength": 1, "maxLength": DESCRIPTION_LIMIT}}}
    raise ServiceRuntimeError("unsupported_operation")


def summary(view):
    """Closed counts for an authorized staff reader, never a public publication projection.

    Do not copy notes, request text, account or item identities, request
    digests, arbitrary filters, timestamps or raw rows.
    """
    if not isinstance(view, dict) or view.get("record_type") != STAFF_VIEW_VERSION:
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    ratings, requests, gaps = view["ratings"], view["material_requests"], view["search_gaps"]
    counts = {"useful": ratings[USEFUL], "not_useful": ratings[NOT_USEFUL], "items_rated": len(ratings["items"])}
    searches = [row["searches"] for row in gaps]
    if any(type(value) is not int or value < 0 for value in (*counts.values(), *searches)):
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return {"record_type": SUMMARY_VERSION, "ratings": counts,
            "material_requests": {"total": len(requests), "open": sum(row.get("state") == "open" for row in requests)},
            "search_gaps": {"groups": len(gaps), "searches": sum(searches)}}


def _bounded_text(value, limit, code, *, required):
    """Text a customer typed on purpose: at most `limit` characters, no control characters, trimmed."""
    if value is None and not required:
        return ""
    if not isinstance(value, str) or any(ord(ch) < 32 and ch not in "\n\t" for ch in value) or len(value) > limit:
        raise ServiceRuntimeError(code)
    stripped = value.strip()
    if required and not stripped:
        raise ServiceRuntimeError(code)
    return stripped


def gap_hour(now):
    """The hour a search gap is counted in, in Coordinated Universal Time."""
    return time.strftime("%Y-%m-%dT%HZ", time.gmtime(now))


def _gap_filters(filters):
    """The declared filters of a search, with only short tokens kept as values."""
    if not isinstance(filters, dict):
        return {}
    kept = {}
    for name in sorted(filters):
        condition = filters[name]
        if not isinstance(name, str) or not _FILTER_TOKEN.fullmatch(name) or not isinstance(condition, dict):
            continue
        values = []
        for operator in sorted(condition):
            chosen = condition[operator]
            for value in (chosen if isinstance(chosen, list) else [chosen]):
                token = value if isinstance(value, str) and _FILTER_TOKEN.fullmatch(value) else (
                    str(value) if type(value) in (int, float, bool) else OTHER_FILTER_VALUE)
                values.append(f"{operator}:{token}")
        kept[name] = values
    return kept


def search_gap_payload(fields, now):
    """The metadata-only payload of one search that found nothing, built from an allowlist of fields."""
    if not isinstance(fields, dict):
        raise ServiceRuntimeError("invalid_request")
    tiers = fields.get("library_tiers")
    payload = {"record_type": GAP_SCHEMA, "hour": gap_hour(now), "mode": str(fields.get("mode", "lexical"))[:16],
               "filters": _gap_filters(fields.get("filters")),
               "library_tiers": sorted(str(tier) for tier in tiers) if isinstance(tiers, list) else [],
               "hit_count": 0, "searches": 1}
    assert_metadata_only(payload, fields.get("query"))
    return payload


def assert_metadata_only(payload, query):
    """Refuse a gap payload that carries the query text, under any key or inside any value."""
    if "query" in payload:
        raise ServiceRuntimeError(GAP_HOLDS_QUERY_TEXT)
    if isinstance(query, str) and query.strip() and query.strip() in canonical(payload):
        raise ServiceRuntimeError(GAP_HOLDS_QUERY_TEXT)
    return payload


def gap_identity(payload):
    """One record for each hour, mode, filter set and tier set, so repeats add to a count."""
    return digest({key: payload[key] for key in ("hour", "mode", "filters", "library_tiers")})


class ServiceFeedback:
    """The three feedback operations over the runtime's own records."""

    def __init__(self, runtime: ServiceRuntime, *, clock=time.time):
        if not isinstance(runtime, ServiceRuntime) or not callable(clock):
            raise ServiceRuntimeError("invalid_configuration")
        self.runtime, self._clock = runtime, clock

    def _downloaded(self, store, tenant_id, identity, body_digest):
        """True when this account holds a usage record of exactly this item at this digest."""
        from .catalogue_reports import downloaded
        return downloaded(self.runtime._catalog, store, tenant_id, identity, body_digest)

    def rate(self, principal, fields):
        """Record one account's rating of an item it downloaded; a second rating of the item replaces the first."""
        if not isinstance(fields, dict) or set(fields) - RATE_FIELDS or not {"identity", "expected_digest", "value"} <= set(fields):
            raise ServiceRuntimeError("invalid_request")
        item = identifier(fields["identity"], "item identity")
        expected = fields["expected_digest"]
        if not isinstance(expected, str) or not _DIGEST.fullmatch(expected):
            raise ServiceRuntimeError("invalid_selected_digest")
        value = fields["value"]
        if value not in RATING_VALUES:
            raise ServiceRuntimeError(RATING_VALUE_INVALID)
        note = _bounded_text(fields.get("note"), NOTE_LIMIT, NOTE_TOO_LONG, required=False)
        catalog = self.runtime._catalog
        with catalog.store(write=True) as store:
            current, guards = self.runtime._revalidate(store, principal)
            if PROVISIONING_METADATA_SCOPE not in current.scopes:
                raise ServiceRuntimeError("scope_required")
            if not self._downloaded(store, current.tenant_id, item, expected):
                raise ServiceRuntimeError(RATING_REQUIRES_DOWNLOAD)
            previous = catalog.read(store, RATING_KIND, (current.tenant_id, item))
            revision = (previous["payload"].get("revision", 0) + 1) if previous is not None else 1
            row = catalog.record(RATING_KIND, (current.tenant_id, item), {
                "record_type": RATING_SCHEMA, "tenant_id": current.tenant_id, "item_identity": item,
                "body_digest": expected, "value": value, "note": note, "at": self.runtime._now(),
                "revision": revision}, tenant_id=current.tenant_id)
            catalog.commit(store, (row,), (*guards, catalog.guard(previous, row["record_id"])))
        return {"record_type": RATING_RESULT_VERSION, "committed": True, "item_identity": item,
                "body_digest": expected, "value": value, "replaced": previous is not None, "revision": revision}

    def request_material(self, principal, fields):
        """Record a request for material the customer wrote on purpose; the same request identity repeats it."""
        if not isinstance(fields, dict) or set(fields) != REQUEST_FIELDS:
            raise ServiceRuntimeError("invalid_request")
        request_id = identifier(fields["request_id"], "request identity")
        description = _bounded_text(fields["description"], DESCRIPTION_LIMIT, DESCRIPTION_INVALID, required=True)
        catalog = self.runtime._catalog
        with catalog.store(write=True) as store:
            current, guards = self.runtime._revalidate(store, principal)
            if PROVISIONING_METADATA_SCOPE not in current.scopes:
                raise ServiceRuntimeError("scope_required")
            logical = (current.tenant_id, request_id)
            content = digest({"description": description})
            held = catalog.read(store, REQUEST_KIND, logical)
            if held is not None:
                if held["payload"].get("content_digest") != content:
                    raise ServiceRuntimeError(REQUEST_IDENTITY_CONFLICT)
                return {"record_type": REQUEST_RESULT_VERSION, "committed": True, "repeated": True,
                        "request_id_digest": held["payload"]["request_id_digest"], "state": held["payload"]["state"]}
            row = catalog.record(REQUEST_KIND, logical, {
                "record_type": REQUEST_SCHEMA, "tenant_id": current.tenant_id,
                "request_id_digest": digest(request_id), "content_digest": content,
                "description": description, "at": self.runtime._now(), "state": "open"}, tenant_id=current.tenant_id)
            catalog.commit(store, (row,), (*guards, catalog.guard(None, row["record_id"])))
        return {"record_type": REQUEST_RESULT_VERSION, "committed": True, "repeated": False,
                "request_id_digest": digest(request_id), "state": "open"}

    def record_search_gap(self, fields):
        """Count one search that found nothing. Names no account and keeps no query text.

        A failure to count is returned, never raised, so the search that found
        nothing is still answered; the outcome says what happened.
        """
        try:
            payload = search_gap_payload(fields, self._clock())
        except ServiceRuntimeError as error:
            return {"record_type": GAP_RESULT_VERSION, "recorded": False, "reason": error.code}
        catalog = self.runtime._catalog
        try:
            with catalog.store(write=True) as store:
                logical = gap_identity(payload)
                held = catalog.read(store, GAP_KIND, logical)
                if held is not None:
                    payload = {**held["payload"], "searches": held["payload"].get("searches", 0) + 1}
                row = catalog.record(GAP_KIND, logical, payload)
                catalog.commit(store, (row,), (catalog.guard(held, row["record_id"]),))
        except (ServiceRuntimeError, ServiceCommitUnknown) as error:
            return {"record_type": GAP_RESULT_VERSION, "recorded": False,
                    "reason": getattr(error, "code", "commit_unknown")}
        return {"record_type": GAP_RESULT_VERSION, "recorded": True, "hour": payload["hour"],
                "searches": payload["searches"]}

    def staff_view(self, principal, *, staff=None, administration=None):
        """Every private rating, request and gap, for account-list staff or an operator.

        A staff session is rechecked at its record, the sign-out record and the
        expiry, as every other staff read is. Without one, the principal must
        hold the administration scope, as the waiting list's operator view does.
        """
        catalog = self.runtime._catalog
        with catalog.store() as store:
            self._authorize_staff_view(store, principal, staff, administration)
            ratings = [row["payload"] for row in catalog.rows_all(store, RATING_KIND)]
            requests = [row["payload"] for row in catalog.rows_all(store, REQUEST_KIND)]
            gaps = [row["payload"] for row in catalog.rows_all(store, GAP_KIND)]
        items = {}
        for value in ratings:
            entry = items.setdefault(value["item_identity"], {"item_identity": value["item_identity"],
                                                              USEFUL: 0, NOT_USEFUL: 0, "notes": []})
            entry[value["value"]] += 1
            if value.get("note"):
                entry["notes"].append(value["note"])
        return {"record_type": STAFF_VIEW_VERSION,
                "ratings": {USEFUL: sum(1 for value in ratings if value["value"] == USEFUL),
                            NOT_USEFUL: sum(1 for value in ratings if value["value"] == NOT_USEFUL),
                            "items": sorted(items.values(), key=lambda row: row["item_identity"])},
                "material_requests": sorted(({"tenant_id": value["tenant_id"], "description": value["description"],
                                              "at": value["at"], "state": value["state"]} for value in requests),
                                            key=lambda row: (-row["at"], row["tenant_id"])),
                "search_gaps": sorted(({key: value[key] for key in ("hour", "mode", "filters", "library_tiers",
                                                                    "hit_count", "searches")} for value in gaps),
                                      key=lambda row: (row["hour"], row["mode"], canonical(row["filters"])),
                                      reverse=True)}

    def _authorize_staff_view(self, store, principal, staff, administration, permission=ACCOUNTS_LIST):
        if staff is not None:
            if administration is None:
                raise ServiceRuntimeError("account_administration_unavailable")
            _current, guards = administration._current_session(store, staff)
            if administration.policy.role_for(staff.subject, staff.email) != staff.role:
                raise ServiceRuntimeError("account_administration_forbidden")
            if permission not in permissions_for(staff.role):
                raise ServiceRuntimeError("account_administration_forbidden")
        else:
            current, guards = self.runtime._revalidate(store, principal)
            if ACCESS_MANAGE_SCOPE not in current.scopes:
                raise ServiceRuntimeError("account_administration_forbidden")
        return guards

    def authorize_staff_view(self, principal, *, staff=None, administration=None):
        """Recheck the existing staff gate without rereading private feedback."""
        with self.runtime._catalog.store() as store:
            self._authorize_staff_view(store, principal, staff, administration)

    def staff_summary(self, principal, *, staff=None, administration=None):
        """Count stored feedback under the usage-count permission, without building a private-text view."""
        catalog = self.runtime._catalog
        with catalog.store() as store:
            self._authorize_staff_view(store, principal, staff, administration, USAGE_COUNTS)
            ratings = [row["payload"] for row in catalog.rows_all(store, RATING_KIND)]
            requests = [row["payload"] for row in catalog.rows_all(store, REQUEST_KIND)]
            gaps = [row["payload"] for row in catalog.rows_all(store, GAP_KIND)]
        return summary({"record_type": STAFF_VIEW_VERSION,
            "ratings": {USEFUL: sum(row["value"] == USEFUL for row in ratings),
                        NOT_USEFUL: sum(row["value"] == NOT_USEFUL for row in ratings),
                        "items": list({row["item_identity"] for row in ratings})},
            "material_requests": [{"state": row["state"]} for row in requests],
            "search_gaps": [{"searches": row["searches"]} for row in gaps]})

    def authorize_staff_summary(self, principal, *, staff=None, administration=None):
        with self.runtime._catalog.store() as store:
            self._authorize_staff_view(store, principal, staff, administration, USAGE_COUNTS)


def feedback_rows(runtime):
    """Every feedback record of a host, for the report tool: no account is read for a gap, because it holds none."""
    catalog = runtime._catalog
    with catalog.store() as store:
        return {RATING_KIND: [row["payload"] for row in catalog.rows_all(store, RATING_KIND)],
                REQUEST_KIND: [row["payload"] for row in catalog.rows_all(store, REQUEST_KIND)],
                GAP_KIND: [row["payload"] for row in catalog.rows_all(store, GAP_KIND)]}


# The checks of this module live in feedback_checks.py and run inside the HTTP suite (http_checks.self_test), as
# every other service check module does; a second self_test here would be a registration no suite collects.
