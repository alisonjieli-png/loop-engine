"""Paged listing of an account's library (roadmap S-6.203, its paged listing part).

On September 26, 2026 a signed-in account's library table asked for the whole
list of 6,398 served packages in one answer, about 6.75 MB, and the service
refused it with 413 `response_limit_exceeded` under the host's
`maximum_response_bytes`. The library grows by about 1,500 packages every six
hours, so a list request of `service_provisioning_request/v2` that names
`page_size` is answered one page at a time, in its own record version. A list
request without `page_size` keeps its earlier answer, `provisioning_list/v3`.

```text
A paged list request (the list operation of service_provisioning_request/v2)
├── page_size   a whole number from 1 to MAXIMUM_LIST_PAGE_SIZE
└── cursor      the next_cursor of the previous page, passed back unchanged

A page, provisioning_list_page/v1
├── items              at most page_size rows, and never more than fit under the answer cap
├── next_cursor        where the next page starts, or null after the last page
├── total_offered      the items offered to this account for this request in the served view
├── catalogue_release  the served release, or null for a catalogue served without one
├── withheld_count     the items this request holds back, on every page
└── withheld           the held-back items with their reasons, at most MAXIMUM_WITHHELD_ROWS,
                       on the first page only; later pages list none and repeat the count
```

A page is filled row by row while the encoded answer stays under the host's
answer cap, with room kept for the result envelope, so a page fits whatever cap
the host sets. A page holds at least one row while rows remain; a single row
larger than the cap is refused as `response_limit_exceeded`.

The withheld list is bounded because it is not bounded by the library: a step
that states only reading files is refused several thousand packages of the
September 26 release, which is more than a default answer holds. The first page
therefore names at most MAXIMUM_WITHHELD_ROWS of them and every page carries the
count, so a client always knows how many items the request held back.

The first page takes a snapshot of the account's whole list: the identities in
order, their digests, the served release and the withheld count, with one list
digest over all of it. The snapshot is kept with the served view, keyed by the
account, the version of its grants record and the request's filters, so every
later page costs the rows of that page rather than the whole library. Every
row of every page is still authorized again, at the moment of that page,
through the provisioning boundary. When those rows disagree with the snapshot,
the service takes the whole list again, and a cursor of the older list is
refused as `list_release_changed`. The snapshot only decides the order and the
count, never what an account may see.

The cursor names the next position and the list digest, and is bound to the
account and the request's filters with a keyed digest. The key is drawn from
the operating system's random source when the service process starts and never
leaves its memory, as the runtime's own principal and effect proofs are, so a
cursor needs no stored state and dies with the process that minted it.
A keyed digest was chosen over a table of minted cursors because it writes
nothing per page and needs no cleanup; the cost is that a cursor minted before
a restart, or by another process, is refused as `list_cursor_invalid`, and the
client starts the list again. Today one Machine runs one service process.

```text
Refusals of a paged list
├── list_page_size_invalid  400  page_size missing beside a cursor, not a whole number, or out of bounds
├── list_cursor_invalid     400  a cursor this process did not mint for this account and these filters
└── list_release_changed    409  the account's list changed since the first page: load it again
```
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import hmac
import json
import re
import secrets
import threading

LIST_PAGE_RECORD_TYPE = "provisioning_list_page/v1"
#: The largest page a request may ask for. A row of the September 26 release is
#: about 1,230 bytes with its attributes, so a full page is about 1.2 MB; the
#: answer cap can still stop a page earlier.
MAXIMUM_LIST_PAGE_SIZE = 1000
#: How many held-back items the first page names. Later pages name none.
MAXIMUM_WITHHELD_ROWS = 200
#: A cursor is short; anything longer was not minted here.
MAXIMUM_CURSOR_CHARACTERS = 128
#: Room kept under the answer cap for the result envelope around a page: the
#: result record type, the operation and the Loop execution record, about 300
#: bytes today.
ENVELOPE_RESERVE_BYTES = 1024
#: The protocol endpoint sends a page twice, as text and as structured content,
#: inside its own result record, so it keeps room for two envelopes and that record.
PROTOCOL_RESERVE_BYTES = 2 * ENVELOPE_RESERVE_BYTES + 512
#: At most this share of a first page's room goes to the withheld list, so the
#: first page always carries offered rows as well.
WITHHELD_SHARE = 4
#: Snapshots kept with one served view. A later page after eviction rebuilds its
#: snapshot, and the list digest decides whether the walk continues.
SNAPSHOTS_KEPT_FOR_EACH_VIEW = 16
ENCODINGS = ("json", "protocol")
JSON_ENCODING, PROTOCOL_ENCODING = ENCODINGS
LIST_PAGE_SIZE_INVALID = "list_page_size_invalid"
LIST_CURSOR_INVALID = "list_cursor_invalid"
LIST_RELEASE_CHANGED = "list_release_changed"
RESPONSE_LIMIT_EXCEEDED = "response_limit_exceeded"
_CURSOR_VERSION = "c1"
_CURSOR = re.compile(r"c1\.(0|[1-9][0-9]{0,8})\.([0-9a-f]{32})\.([0-9a-f]{32})")


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def paging_request(fields):
    """(page_size, cursor) of one list request, or (None, None) for an unpaged one; refuses a malformed pair.

    Read before the request schema, so a bad page size or cursor is refused with its own name. The fields
    are not changed; the caller removes both before the provisioning boundary sees the request."""
    from .http import ServiceHttpError
    page_size, cursor = fields.get("page_size"), fields.get("cursor")
    if "page_size" not in fields and "cursor" not in fields:
        return None, None
    if type(page_size) is not int or not 1 <= page_size <= MAXIMUM_LIST_PAGE_SIZE:
        raise ServiceHttpError(LIST_PAGE_SIZE_INVALID, 400)
    if "cursor" in fields and (not isinstance(cursor, str) or not 0 < len(cursor) <= MAXIMUM_CURSOR_CHARACTERS):
        raise ServiceHttpError(LIST_CURSOR_INVALID, 400)
    return page_size, cursor


def paging_schema_properties():
    """The two optional list fields as the request schema and the protocol tool publish them."""
    return {"page_size": {"type": "integer", "minimum": 1, "maximum": MAXIMUM_LIST_PAGE_SIZE,
                          "description": "Answer in pages of at most this many items; each page names next_cursor."},
            "cursor": {"type": "string", "minLength": 1, "maxLength": MAXIMUM_CURSOR_CHARACTERS,
                       "description": "The next_cursor of the previous page, unchanged. Send page_size with it."}}


def request_digest(fields):
    """The filters that decide an account's list, so a cursor cannot continue a list asked with other filters."""
    chosen = {"style": fields.get("style", ""), "kinds": sorted(fields.get("kinds", ())),
              "authority_effects": sorted(fields.get("authority_effects", ())),
              "community_items": fields.get("community_items", "")}
    return hashlib.sha256(_json_bytes(chosen)).hexdigest()


@dataclass(frozen=True)
class ListSnapshot:
    """One account's whole list for one request in one served view: order, count and digest only."""

    catalogue: object
    rows: tuple
    withheld: tuple
    withheld_count: int
    digest: str

    @property
    def total(self):
        return len(self.rows)

    @classmethod
    def of(cls, answer, view):
        rows = tuple((row["identity"], row["digest"]) for row in answer["items"])
        withheld = tuple({"identity": row["identity"], "reason": row["reason"]} for row in answer["withheld"])
        document = {"release": view.release_id or "", "offered": rows,
                    "withheld": [(row["identity"], row["reason"]) for row in withheld]}
        return cls(view.catalogue, rows, withheld[:MAXIMUM_WITHHELD_ROWS], len(withheld),
                   hashlib.sha256(_json_bytes(document)).hexdigest()[:32])


def _snapshots(view):
    lock = view._lazy.setdefault("list_snapshot_lock", threading.Lock())
    return lock, view._lazy.setdefault("list_snapshots", OrderedDict())


def cached_snapshot(view, key):
    lock, held = _snapshots(view)
    with lock:
        snapshot = held.get(key)
        # A snapshot belongs to the exact catalogue object it was taken from.
        if snapshot is None or snapshot.catalogue is not view.catalogue:
            return None
        held.move_to_end(key)
        return snapshot


def keep_snapshot(view, key, snapshot):
    lock, held = _snapshots(view)
    with lock:
        held[key] = snapshot
        held.move_to_end(key)
        while len(held) > SNAPSHOTS_KEPT_FOR_EACH_VIEW:
            held.popitem(last=False)


def forget_snapshot(view, key):
    lock, held = _snapshots(view)
    with lock:
        held.pop(key, None)


class ListCursors:
    """Mints and reads list cursors with a key that exists only in this process's memory."""

    def __init__(self):
        self._key = secrets.token_bytes(32)

    def _mac(self, tenant_id, request, offset, list_digest):
        message = "\n".join((_CURSOR_VERSION, tenant_id, request, str(offset), list_digest)).encode("utf-8")
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()[:32]

    def mint(self, tenant_id, request, offset, list_digest):
        return ".".join((_CURSOR_VERSION, str(offset), list_digest, self._mac(tenant_id, request, offset, list_digest)))

    def read(self, cursor, tenant_id, request):
        """(offset, list digest) of a cursor this process minted for this account and these filters."""
        from .http import ServiceHttpError
        found = _CURSOR.fullmatch(cursor) if isinstance(cursor, str) else None
        if found is None:
            raise ServiceHttpError(LIST_CURSOR_INVALID, 400)
        offset, list_digest, mac = int(found.group(1)), found.group(2), found.group(3)
        if not hmac.compare_digest(mac, self._mac(tenant_id, request, offset, list_digest)):
            raise ServiceHttpError(LIST_CURSOR_INVALID, 400)
        return offset, list_digest


def _escaped_size(raw):
    """Bytes the protocol endpoint's text copy of `raw` JSON takes, inside its quotes."""
    return len(json.dumps(raw.decode("utf-8"), ensure_ascii=False).encode("utf-8")) - 2


def _size(value, encoding):
    raw = _json_bytes(value)
    return len(raw) + (_escaped_size(raw) if encoding == PROTOCOL_ENCODING else 0)


def fill_page(header, rows, withheld, *, budget, encoding, cursor_placeholder):
    """The page answer holding as many `rows`, and first-page `withheld` rows, as fit in `budget` bytes.

    Returns (answer, rows used). Every added row is counted as it is added, in the encoding the transport
    sends, and `rows` may be lazy, so a row after the budget is never prepared; `cursor_placeholder` is a cursor
    of the longest length this list can mint, so the real cursor written afterwards never makes the answer larger
    than was measured."""
    from .http import ServiceHttpError
    answer = {**header, "items": [], "next_cursor": cursor_placeholder, "withheld": []}
    used = _size(answer, encoding)
    separator = 2 if encoding == PROTOCOL_ENCODING else 1
    room = budget - used
    listed_withheld, withheld_room = [], room // WITHHELD_SHARE
    for row in withheld:
        cost = _size(row, encoding) + separator
        if cost > withheld_room:
            break
        listed_withheld.append(row)
        withheld_room -= cost
        room -= cost
    chosen, offered = [], False
    for row in rows:
        offered = True
        cost = _size(row, encoding) + separator
        if cost > room:
            break
        chosen.append(row)
        room -= cost
    if offered and not chosen:
        # One row alone is larger than this host's answer cap. No page can hold it.
        raise ServiceHttpError(RESPONSE_LIMIT_EXCEEDED, 413)
    answer["items"], answer["withheld"] = chosen, listed_withheld
    return answer, len(chosen)


def reserve_for(encoding):
    return PROTOCOL_RESERVE_BYTES if encoding == PROTOCOL_ENCODING else ENVELOPE_RESERVE_BYTES


@dataclass(frozen=True)
class ListPageRequest:
    """One paged list request as the transport resolved it.

    `fields` are the provisioning request fields without the paging pair, after the step effects and the
    community choice were resolved. `answer_limit` is the host's answer cap and `encoding` the form the
    transport sends the answer in. `decorate` adds what the transport adds to every listed row: the served
    attributes, and the body permission of this credential."""

    principal: object
    view: object
    fields: dict
    page_size: int
    cursor: str | None
    answer_limit: int
    encoding: str = JSON_ENCODING
    decorate: object = None

    def __post_init__(self):
        if self.encoding not in ENCODINGS:
            raise ValueError("unknown answer encoding")
        if type(self.page_size) is not int or not 1 <= self.page_size <= MAXIMUM_LIST_PAGE_SIZE:
            raise ValueError("a page size is a whole number within the published bounds")
        if type(self.answer_limit) is not int or self.answer_limit < 1:
            raise ValueError("an answer cap is a positive whole number")


def list_page(paged, *, provisioning, runtime, cursors):
    """One page of an account's list: a fresh authorization of the page's rows, ordered by the snapshot."""
    from .http import ServiceHttpError
    principal, view, fields, page_size = paged.principal, paged.view, paged.fields, paged.page_size
    cursor, encoding = paged.cursor, paged.encoding
    decorate = paged.decorate if callable(paged.decorate) else (lambda row: row)
    tenant = principal.tenant_id
    request = request_digest(fields)
    position = cursors.read(cursor, tenant, request) if cursor is not None else None
    offset = position[0] if position is not None else 0
    _grants, guard = runtime.grant_snapshot(principal)
    key = (tenant, guard.record_id, guard.record_version, guard.must_not_exist, request)
    snapshot, rows = cached_snapshot(view, key), None
    if snapshot is not None and (position is None or (position[1] == snapshot.digest and offset < snapshot.total)):
        # The page's rows are authorized again now, through the same boundary as a whole list, and must be
        # exactly the rows the snapshot placed here.
        wanted = snapshot.rows[offset:offset + page_size]
        answer = provisioning.invoke_for_principal(principal, "list", view=view,
                                                   candidates=[identity for identity, _digest in wanted], **fields)
        rows = answer["items"]
        if answer["withheld"] or tuple((row["identity"], row["digest"]) for row in rows) != wanted:
            forget_snapshot(view, key)
            rows = None
    if rows is None:
        # No snapshot, or one the cursor or the fresh rows disagree with: the whole list is taken again rather
        # than trusted, so a stale snapshot can neither refuse an unchanged walk nor continue a changed one.
        answer = provisioning.invoke_for_principal(principal, "list", view=view, **fields)
        snapshot = ListSnapshot.of(answer, view)
        _grants, after = runtime.grant_snapshot(principal)
        if (after.record_id, after.record_version, after.must_not_exist) == key[1:4]:
            keep_snapshot(view, key, snapshot)
        rows = answer["items"][offset:offset + page_size]
    if position is not None:
        if position[1] != snapshot.digest:
            raise ServiceHttpError(LIST_RELEASE_CHANGED, 409)
        if not 0 < offset < snapshot.total:
            raise ServiceHttpError(LIST_CURSOR_INVALID, 400)
    header = {"record_type": LIST_PAGE_RECORD_TYPE, "tenant_id": answer["tenant_id"],
              "entitlement": answer["entitlement"], "community_items": answer["community_items"],
              "metered": False, "catalogue_release": view.release_id or None, "page_size": page_size,
              "total_offered": snapshot.total, "withheld_count": snapshot.withheld_count}
    placeholder = cursors.mint(tenant, request, snapshot.total, snapshot.digest)
    page, used = fill_page(header, (decorate(row) for row in rows), snapshot.withheld if offset == 0 else (),
                           budget=paged.answer_limit - reserve_for(encoding), encoding=encoding,
                           cursor_placeholder=placeholder)
    following = offset + used
    page["next_cursor"] = cursors.mint(tenant, request, following, snapshot.digest) \
        if following < snapshot.total else None
    return page
