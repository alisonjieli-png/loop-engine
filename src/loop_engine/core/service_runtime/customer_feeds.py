"""Saved customer feeds with per-agent assignments: account controls, permission and pull delivery.

Kind: internal service adapter over the existing catalogue authority. It adds no
runtime type, no store, no account system and no notification registry. Saved
settings, assignments and delivery metadata are typed records in the service
collection, written through the same atomic batch contract as every other
service record. Customer browser sessions are checked by
`access.verified_customer_session`, agent credentials are the existing
customer client keys, and entitlement is the runtime's own answer.

```text
One pull of a saved feed by an agent credential
├── selection, in customer_feed_records.select: what the definition chooses; it reads no account
└── permission, checked again before every pull and again inside the delivery write
    ├── the credential: a current customer client key with the metadata scope and an enabled owner sign-in
    ├── the account: the entitlement the host requires in service_customer_feeds_policy/v1
    ├── the feed: saved by the same owner in the same account, and active
    ├── the assignment: this exact credential reads this feed, and the assignment is active
    └── each item: in the admitted population read now, with an access class this account holds
```

A pull answers one page of one immutable population. Its cursor is bound to
the account, the assignment, the credential, the feed, the definition version,
the filter digest and the population digest, so a changed filter, a new
snapshot or a withdrawn item refuses an old cursor by name and never skips or
repeats items silently. A page carries an ETag; a matching `If-None-Match`
answers not modified after the same permission checks and writes nothing.
Feed text is untrusted data: nothing in an item is parsed as a request, a
setting or a tool call.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import math
import threading
import time
import uuid

from .access import verified_customer_session
# The wire contracts live beside the records; their names stay importable from here as well.
from .customer_feed_records import (
    ASSIGNED_PATH, ASSIGNED_RECORD_TYPE, ASSIGNED_TOOL, ASSIGNED_TOOL_DESCRIPTION, ASSIGNMENT_KIND,
    ASSIGNMENT_RECORD_TYPE, CADENCES, CONTENT_POLICY, CONTEXT_MODES, DEFAULT_SETTINGS, DEFINITION_KIND,
    DEFINITION_RECORD_TYPE, DELIVERY_KIND, DELIVERY_RECORD_TYPE, ENTITLED_ACCESS, EVIDENCE_REQUIREMENTS,
    EXPORT_RECORD_TYPE, FAILED, FORMATS, LIBRARY_STREAM, MANAGEMENT_PATH, MAXIMUM_REQUEST_BYTES,
    NOT_MODIFIED_RECORD_TYPE, ORDER, OVERVIEW_RECORD_TYPE, OWNER_KIND, OWNER_RECORD_TYPE, PAGE_RECORD_TYPE,
    PREVIEW_RECORD_TYPE, PUBLIC_ACCESS, PULL_PATH, PULL_TOOL, PULL_TOOL_DESCRIPTION, READ_OPERATIONS, RECORD_TYPES,
    REQUEST_RECORD_TYPE, RESULT_RECORD_TYPE, SEARCHED, SOURCE_STREAM, STALE_POLICIES, STREAMS, UPDATE_TYPES,
    CustomerFeedError, CustomerFeedsPolicy, FeedSnapshot, StreamRead, capability, cursor_binding, definition_settings,
    delivery_state, feed_identifier, feed_name, filter_digest, library_update_items, management_request,
    markdown_page, mint_cursor, population_digest, privacy_notice_covers_feeds, pull_request, pull_schema,
    read_cursor, select, served_privacy_notice, source_reference_items, templates
)
from .records import CLIENT_ACCESS_PROFILE, ServiceRuntimeError, canonical, digest
from .runtime import BODIES, KEY, PROVISIONING_METADATA_SCOPE, ServiceRuntime

#: The most item rows a preview lists in each of its lists. Its counts always cover every item.
PREVIEW_ROWS = 200
#: How long the pull window counts a pull, and how many assignment windows one process keeps.
PULL_WINDOW_SECONDS, PULL_WINDOWS_KEPT = 60.0, 10_000


@dataclass(frozen=True)
class FeedReadContext:
    """What a stream reader may use: the runtime, the served catalogue view if any, and the host's public origin."""

    runtime: object
    view: object = None
    origin: str = ""


def read_source_references(context):
    """The registered source directory, read afresh so a withdrawn source leaves the population at once."""
    from .feed_profiles import FeedProfileError, current_directory
    try:
        directory = current_directory()
    except (ServiceRuntimeError, FeedProfileError, OSError):
        return StreamRead(SOURCE_STREAM, FAILED, reason="feed_source_directory_unavailable")
    return StreamRead(SOURCE_STREAM, SEARCHED, directory.source_docs_checked_on, directory.digest,
                      source_reference_items(directory))


def read_library_updates(context):
    """The public library updates notice of the served catalogue, or a failed read that names its reason."""
    from . import catalogue_feed
    if context.view is None:
        return StreamRead(LIBRARY_STREAM, FAILED, reason="catalogue_view_unavailable")
    try:
        record = catalogue_feed.snapshot(context.runtime, context.view())
    except ServiceRuntimeError as error:
        return StreamRead(LIBRARY_STREAM, FAILED, reason=error.code)
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return StreamRead(LIBRARY_STREAM, FAILED, reason="catalogue_feed_unavailable")
    return StreamRead(LIBRARY_STREAM, SEARCHED, record["state_changed_at"], digest(record),
                      library_update_items(record, context.origin))


DEFAULT_READERS = {SOURCE_STREAM: read_source_references, LIBRARY_STREAM: read_library_updates}


def checked(row, kind):
    """`row` when it holds the record version this release reads for `kind`, or None for no row; anything else refuses."""
    if row is not None and (not isinstance(row.get("payload"), dict)
                            or row["payload"].get("record_type") != RECORD_TYPES[kind]):
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return row


def _etag(value):
    data = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return '"' + sha256(data).hexdigest() + '"'


def _validator_matches(value, etag):
    from .web_pages import validator_matches
    return bool(value) and validator_matches(value, etag)


class CustomerFeeds:
    """Saved feeds for one host. Construction refuses an enabled policy the served privacy notice does not cover."""

    def __init__(self, runtime, policy, *, streams=None, privacy_notice=None, monotonic=time.monotonic):
        if not isinstance(runtime, ServiceRuntime) or not isinstance(policy, CustomerFeedsPolicy) or not callable(monotonic):
            raise ServiceRuntimeError("invalid_configuration")
        if policy.enabled and not privacy_notice_covers_feeds(
                served_privacy_notice() if privacy_notice is None else privacy_notice):
            raise ServiceRuntimeError("customer_feeds_privacy_notice_not_published")
        readers = {**DEFAULT_READERS, **(streams or {})}
        if set(readers) != set(STREAMS) or not all(callable(reader) for reader in readers.values()):
            raise ServiceRuntimeError("invalid_configuration")
        self.runtime, self.policy, self._readers, self._monotonic = runtime, policy, readers, monotonic
        self._pulls, self._pull_lock = {}, threading.Lock()

    @property
    def available(self):
        return self.policy.enabled

    def _require_enabled(self):
        if not self.policy.enabled:
            raise CustomerFeedError("customer_feeds_unavailable", 404)

    def _now(self):
        return int(self.runtime._now())

    def _today(self):
        return datetime.fromtimestamp(self.runtime._now(), timezone.utc).date()

    @staticmethod
    def _directory():
        from .feed_profiles import FeedProfileError, current_directory
        try:
            return current_directory()
        except (ServiceRuntimeError, FeedProfileError, OSError):
            raise CustomerFeedError("feed_source_directory_unavailable", 503) from None

    # Owned records ---------------------------------------------------------------------------------------------

    def _record(self, store, kind, tenant_id, identity):
        return checked(self.runtime._catalog.read(store, kind, (tenant_id, identity)), kind)

    def _owned_rows(self, store, current, kind):
        rows = [checked(row, kind) for row in self.runtime._catalog.rows(store, kind, current.tenant_id)]
        return [row for row in rows if row["payload"].get("owner_subject_record_id") == current.authentication_record_id]

    def _owned(self, store, current, kind, identity, code):
        row = self._record(store, kind, current.tenant_id, feed_identifier(identity, code))
        if row is None or row["payload"].get("owner_subject_record_id") != current.authentication_record_id:
            raise CustomerFeedError(code, 404)
        return row

    def _customer_keys(self, store, current):
        rows = []
        for row in self.runtime._catalog.rows(store, KEY, current.tenant_id):
            value = self.runtime._payload(row, KEY)
            if (value.get("management_profile") == CLIENT_ACCESS_PROFILE
                    and value.get("owner_subject_record_id") == current.authentication_record_id):
                rows.append((row, value))
        return rows

    def _key_state(self, value):
        expires = value.get("expires_at")
        return ("revoked" if value.get("enabled") is not True else
                "expired" if type(expires) is not int or expires <= self._now() else "active")

    @staticmethod
    def _definition_view(row):
        value = row["payload"]
        return {"feed_id": value["feed_id"], "revision": row["record_version"], "name": value["settings"]["name"],
                "definition_version": value["version"], "state": value["state"], "settings": value["settings"],
                "filter_digest": value["filter_digest"], "created_at": value["created_at"],
                "updated_at": value["updated_at"]}

    @staticmethod
    def _assignment_view(row, keys, deliveries):
        value = row["payload"]
        key = keys.get(value["agent_key_record_id"])
        return {"assignment_id": value["assignment_id"], "revision": row["record_version"], "feed_id": value["feed_id"],
                "key_id": value["agent_key_id"], "key_label": key[1].get("label") if key else None,
                "key_state": key[2] if key else "missing", "state": value["state"],
                "created_at": value["created_at"], "updated_at": value["updated_at"],
                "deliveries": deliveries.get(value["assignment_id"], [])}

    def _settings_state(self, store, current):
        keys = {row["record_id"]: (row, value, self._key_state(value)) for row, value in self._customer_keys(store, current)}
        deliveries = {row["payload"]["assignment_id"]: row["payload"]["entries"]
                      for row in self._owned_rows(store, current, DELIVERY_KIND)}
        definitions = sorted((self._definition_view(row) for row in self._owned_rows(store, current, DEFINITION_KIND)),
                             key=lambda view: (view["created_at"], view["feed_id"]))
        assignments = sorted((self._assignment_view(row, keys, deliveries)
                              for row in self._owned_rows(store, current, ASSIGNMENT_KIND)),
                             key=lambda view: (view["created_at"], view["assignment_id"]))
        agent_keys = sorted(({"key_id": value.get("key_id"), "label": value.get("label"), "state": state,
                              "expires_at": value.get("expires_at"),
                              "reads_feeds": PROVISIONING_METADATA_SCOPE in (value.get("scopes") or ())}
                             for _row, value, state in keys.values()),
                            key=lambda view: (view["state"] != "active", view["label"] or "", view["key_id"] or ""))
        return definitions, assignments, agent_keys

    # Account controls ------------------------------------------------------------------------------------------

    def overview(self, principal, session):
        """Everything one signed-in customer has saved, the agent keys they may assign, and the choices available."""
        self._require_enabled()
        directory = self._directory()
        with self.runtime._catalog.store() as store:
            current, _guards = verified_customer_session(self.runtime, store, principal, session)
            definitions, assignments, agent_keys = self._settings_state(store, current)
        return {"record_type": OVERVIEW_RECORD_TYPE, "available": True, "definitions": definitions,
                "assignments": assignments, "agent_keys": agent_keys, "templates": templates(directory),
                "inventory": {"directory_digest": directory.digest,
                              "source_docs_checked_on": directory.source_docs_checked_on,
                              "topics": list(dict.fromkeys(item.group for item in directory.collections)),
                              "collections": [{"id": item.id, "title": item.title, "topic": item.group}
                                              for item in directory.collections],
                              "sources": [{"id": item.id, "name": item.name, "kind": item.kind}
                                          for item in directory.sources],
                              "streams": list(STREAMS), "update_types": list(UPDATE_TYPES),
                              "evidence_requirements": list(EVIDENCE_REQUIREMENTS),
                              "stale_policies": list(STALE_POLICIES), "cadences": list(CADENCES),
                              "formats": list(FORMATS), "context_modes": list(CONTEXT_MODES),
                              "defaults": dict(DEFAULT_SETTINGS)},
                "limits": self._limits(), "endpoints": {"pull": PULL_PATH, "assigned": ASSIGNED_PATH,
                                                        "protocol_tools": [ASSIGNED_TOOL, PULL_TOOL]},
                "content_policy": CONTENT_POLICY,
                "not_included": ["daily_snapshots", "notifications", "custom_source_urls", "new_prices"]}

    def _limits(self):
        policy = self.policy
        return {"maximum_definitions": policy.maximum_definitions, "maximum_assignments": policy.maximum_assignments,
                "maximum_page_items": policy.maximum_page_items,
                "maximum_pulls_per_minute": policy.maximum_pulls_per_minute,
                "delivery_history_entries": policy.delivery_history_entries,
                "required_entitlement": policy.required_entitlement}

    def apply(self, principal, session, fields, *, view=None, origin=""):
        """Apply one account control. Writes are atomic, idempotent by request identity and owner-scoped."""
        self._require_enabled()
        operation, request_id, body, request_digest = management_request(fields)
        if operation == "preview_definition":
            return self.preview(principal, session, body, view=view, origin=origin)
        if operation == "export_settings":
            return self.export(principal, session)
        handler = {"create_definition": self._create_definition, "update_definition": self._update_definition,
                   "clone_definition": self._clone_definition, "pause_definition": self._pause_definition,
                   "resume_definition": self._resume_definition, "delete_definition": self._delete_definition,
                   "create_assignment": self._create_assignment, "pause_assignment": self._pause_assignment,
                   "resume_assignment": self._resume_assignment, "delete_assignment": self._delete_assignment}[operation]
        directory = self._directory() if operation in ("create_definition", "update_definition") else None
        catalog = self.runtime._catalog
        with catalog.store(write=True) as store:
            current, guards = verified_customer_session(self.runtime, store, principal, session)
            # The owner revision is read before anything is counted, so a concurrent write of the same owner
            # changes it and this batch is refused instead of committing past a limit it counted too early.
            identity = (current.tenant_id, current.authentication_record_id)
            held = checked(catalog.read(store, OWNER_KIND, identity), OWNER_KIND)
            outcome = handler(store, current, request_id, body, request_digest, directory)
            if outcome.get("records") is not None:
                owner = catalog.record(OWNER_KIND, identity, {
                    "record_type": OWNER_RECORD_TYPE, "tenant_id": current.tenant_id,
                    "owner_subject_record_id": current.authentication_record_id, "updated_at": self._now()},
                    tenant_id=current.tenant_id)
                all_guards = (*guards, catalog.guard(held, owner["record_id"]), *outcome["guards"])
                unique = {}
                for guard in all_guards:
                    if guard.record_id in unique and unique[guard.record_id] != guard:
                        raise ServiceRuntimeError("concurrent_update")
                    unique[guard.record_id] = guard
                catalog.commit(store, (*outcome["records"], owner), tuple(unique.values()), outcome.get("removals", ()))
        return {"record_type": RESULT_RECORD_TYPE, "operation": operation, "committed": True,
                "replayed": outcome.get("records") is None, **outcome["result"]}

    def _new_definition(self, current, feed_id, settings, request_digest):
        now = self._now()
        payload = {"record_type": DEFINITION_RECORD_TYPE, "tenant_id": current.tenant_id,
                   "owner_subject_record_id": current.authentication_record_id, "feed_id": feed_id, "version": 1,
                   "state": "active", "settings": settings, "filter_digest": filter_digest(settings),
                   "created_at": now, "updated_at": now, "creation_request_digest": request_digest,
                   "last_request_digest": request_digest}
        return self.runtime._catalog.record(DEFINITION_KIND, (current.tenant_id, feed_id), payload,
                                            tenant_id=current.tenant_id)

    def _created(self, store, current, request_id, request_digest, settings):
        catalog = self.runtime._catalog
        feed_id = digest(["customer_feed_definition", current.authentication_record_id, request_id])[:32]
        held = self._record(store, DEFINITION_KIND, current.tenant_id, feed_id)
        if held is not None:
            if held["payload"].get("creation_request_digest") != request_digest:
                raise CustomerFeedError("customer_feed_request_identity_conflict", 409)
            return {"records": None, "result": {"definition": self._definition_view(held)}}
        if len(self._owned_rows(store, current, DEFINITION_KIND)) >= self.policy.maximum_definitions:
            raise CustomerFeedError("customer_feed_definition_limit_reached", 409)
        row = self._new_definition(current, feed_id, settings, request_digest)
        return {"records": (row,), "guards": (catalog.guard(None, row["record_id"]),),
                "result": {"definition": self._definition_view(row)}}

    def _create_definition(self, store, current, request_id, body, request_digest, directory):
        return self._created(store, current, request_id, request_digest, definition_settings(body["definition"], directory))

    def _clone_definition(self, store, current, request_id, body, request_digest, _directory):
        source = self._owned(store, current, DEFINITION_KIND, body["feed_id"], "customer_feed_not_found")
        return self._created(store, current, request_id, request_digest,
                             {**source["payload"]["settings"], "name": feed_name(body["name"])})

    def _changed(self, store, current, kind, identity, body, request_digest, code):
        row = self._owned(store, current, kind, identity, code)
        if row["payload"].get("last_request_digest") == request_digest:
            return row, True
        if body.get("expected_revision") != row["record_version"]:
            raise CustomerFeedError("customer_feed_revision_conflict", 409, details={
                "record_type": "customer_feed_revision_conflict/v1", "current_revision": row["record_version"]})
        return row, False

    def _rewrite(self, row, request_digest, **changes):
        payload = {**row["payload"], **changes, "updated_at": self._now(), "last_request_digest": request_digest}
        return {**row, "record_version": self._version(), "payload": payload}

    @staticmethod
    def _version():
        return uuid.uuid4().hex

    def _update_definition(self, store, current, _request_id, body, request_digest, directory):
        row, replayed = self._changed(store, current, DEFINITION_KIND, body["feed_id"], body, request_digest,
                                      "customer_feed_not_found")
        if replayed:
            return {"records": None, "result": {"definition": self._definition_view(row)}}
        settings = definition_settings(body["definition"], directory)
        version = row["payload"]["version"] + (settings != row["payload"]["settings"])
        changed = self._rewrite(row, request_digest, settings=settings, version=version,
                                filter_digest=filter_digest(settings))
        return {"records": (changed,), "guards": (self.runtime._catalog.guard(row),),
                "result": {"definition": self._definition_view(changed)}}

    def _definition_state(self, store, current, body, request_digest, state):
        row, replayed = self._changed(store, current, DEFINITION_KIND, body["feed_id"], body, request_digest,
                                      "customer_feed_not_found")
        if replayed:
            return {"records": None, "result": {"definition": self._definition_view(row)}}
        changed = self._rewrite(row, request_digest, state=state)
        return {"records": (changed,), "guards": (self.runtime._catalog.guard(row),),
                "result": {"definition": self._definition_view(changed)}}

    def _pause_definition(self, store, current, _request_id, body, request_digest, _directory):
        return self._definition_state(store, current, body, request_digest, "paused")

    def _resume_definition(self, store, current, _request_id, body, request_digest, _directory):
        return self._definition_state(store, current, body, request_digest, "active")

    def _delete_definition(self, store, current, _request_id, body, request_digest, _directory):
        """Remove the definition, its assignments and their delivery history in one batch."""
        catalog = self.runtime._catalog
        row, _replayed = self._changed(store, current, DEFINITION_KIND, body["feed_id"], body, request_digest,
                                       "customer_feed_not_found")
        assignments = [item for item in self._owned_rows(store, current, ASSIGNMENT_KIND)
                       if item["payload"]["feed_id"] == row["payload"]["feed_id"]]
        deliveries = [item for item in (self._record(store, DELIVERY_KIND, current.tenant_id,
                                                   assignment["payload"]["assignment_id"])
                                        for assignment in assignments) if item is not None]
        removed = [row, *assignments, *deliveries]
        return {"records": (), "guards": tuple(catalog.guard(item) for item in removed),
                "removals": tuple(item["record_id"] for item in removed),
                "result": {"removed": {"definitions": 1, "assignments": len(assignments),
                                       "delivery_histories": len(deliveries)}, "feed_id": row["payload"]["feed_id"]}}

    def _create_assignment(self, store, current, _request_id, body, request_digest, _directory):
        catalog = self.runtime._catalog
        definition = self._owned(store, current, DEFINITION_KIND, body["feed_id"], "customer_feed_not_found")
        key_id = body["key_id"]
        found = [(row, value) for row, value in self._customer_keys(store, current)
                 if isinstance(key_id, str) and value.get("key_id") == key_id]
        if len(found) != 1:
            raise CustomerFeedError("customer_feed_agent_key_not_found", 404)
        key_row, key = found[0]
        if self._key_state(key) != "active":
            raise CustomerFeedError("customer_feed_agent_key_inactive", 409)
        if PROVISIONING_METADATA_SCOPE not in (key.get("scopes") or ()):
            raise CustomerFeedError("customer_feed_agent_key_scope_required", 409)
        feed_id = definition["payload"]["feed_id"]
        assignment_id = digest(["customer_feed_assignment", feed_id, key_row["record_id"]])[:32]
        held = self._record(store, ASSIGNMENT_KIND, current.tenant_id, assignment_id)
        if held is not None:
            if held["payload"].get("creation_request_digest") != request_digest:
                raise CustomerFeedError("customer_feed_assignment_exists", 409)
            return {"records": None, "result": {"assignment_id": assignment_id, "feed_id": feed_id}}
        if len(self._owned_rows(store, current, ASSIGNMENT_KIND)) >= self.policy.maximum_assignments:
            raise CustomerFeedError("customer_feed_assignment_limit_reached", 409)
        now = self._now()
        row = catalog.record(ASSIGNMENT_KIND, (current.tenant_id, assignment_id), {
            "record_type": ASSIGNMENT_RECORD_TYPE, "tenant_id": current.tenant_id,
            "owner_subject_record_id": current.authentication_record_id, "assignment_id": assignment_id,
            "feed_id": feed_id, "agent_key_record_id": key_row["record_id"], "agent_key_id": key["key_id"],
            "state": "active", "created_at": now, "updated_at": now, "creation_request_digest": request_digest,
            "last_request_digest": request_digest}, tenant_id=current.tenant_id)
        return {"records": (row,), "guards": (catalog.guard(None, row["record_id"]), catalog.guard(definition),
                                              catalog.guard(key_row)),
                "result": {"assignment_id": assignment_id, "feed_id": feed_id, "revision": row["record_version"]}}

    def _assignment_state(self, store, current, body, request_digest, state):
        row, replayed = self._changed(store, current, ASSIGNMENT_KIND, body["assignment_id"], body, request_digest,
                                      "customer_feed_assignment_not_found")
        if replayed:
            return {"records": None, "result": {"assignment_id": row["payload"]["assignment_id"], "state": state}}
        changed = self._rewrite(row, request_digest, state=state)
        return {"records": (changed,), "guards": (self.runtime._catalog.guard(row),),
                "result": {"assignment_id": row["payload"]["assignment_id"], "state": state,
                           "revision": changed["record_version"]}}

    def _pause_assignment(self, store, current, _request_id, body, request_digest, _directory):
        return self._assignment_state(store, current, body, request_digest, "paused")

    def _resume_assignment(self, store, current, _request_id, body, request_digest, _directory):
        return self._assignment_state(store, current, body, request_digest, "active")

    def _delete_assignment(self, store, current, _request_id, body, request_digest, _directory):
        catalog = self.runtime._catalog
        row, _replayed = self._changed(store, current, ASSIGNMENT_KIND, body["assignment_id"], body, request_digest,
                                       "customer_feed_assignment_not_found")
        delivery = self._record(store, DELIVERY_KIND, current.tenant_id, row["payload"]["assignment_id"])
        removed = [row, *([delivery] if delivery is not None else [])]
        return {"records": (), "guards": tuple(catalog.guard(item) for item in removed),
                "removals": tuple(item["record_id"] for item in removed),
                "result": {"assignment_id": row["payload"]["assignment_id"],
                           "removed": {"assignments": 1, "delivery_histories": len(removed) - 1}}}

    def export(self, principal, session):
        """Every saved setting and delivery history entry of one customer, with no credential or key digest."""
        self._require_enabled()
        with self.runtime._catalog.store() as store:
            current, _guards = verified_customer_session(self.runtime, store, principal, session)
            definitions, assignments, _keys = self._settings_state(store, current)
        document = {"record_type": EXPORT_RECORD_TYPE, "exported_at": self._now(),
                    "definitions": [{key: view[key] for key in ("feed_id", "name", "definition_version", "state",
                                                                "settings", "created_at", "updated_at")}
                                    for view in definitions],
                    "assignments": [{key: view[key] for key in ("assignment_id", "feed_id", "key_id", "key_label",
                                                                "state", "created_at", "updated_at", "deliveries")}
                                    for view in assignments],
                    "credentials_included": False}
        return {**document, "export_digest": digest(document)}

    # Selection, permission and delivery ------------------------------------------------------------------------

    def _read(self, stream, context):
        try:
            read = self._readers[stream](context)
        except (ServiceRuntimeError, AttributeError, KeyError, TypeError, ValueError, OSError):
            return StreamRead(stream, FAILED, reason="stream_read_failed")
        if not isinstance(read, StreamRead) or read.stream != stream:
            return StreamRead(stream, FAILED, reason="stream_read_invalid")
        return read

    def _deliverable(self, settings, context, entitlement):
        """Select from the population read now, then keep only items whose access class this account holds."""
        snapshot = FeedSnapshot(tuple(self._read(stream, context) for stream in STREAMS if stream in settings["streams"]))
        selection = select(settings, snapshot, as_of=self._today())
        delivered, withheld = [], []
        for item, matched, stale in selection.included:
            if self._item_permitted(item, entitlement):
                delivered.append({**item, "matched_by": list(matched), "stale": stale})
            else:
                withheld.append({"item_id": item["item_id"], "title": item["title"], "stream": item["stream"],
                                 "reasons": ["item_access_denied"]})
        return snapshot, selection, delivered, withheld

    @staticmethod
    def _item_permitted(item, entitlement):
        """Exact item access: a public item for any enabled account, an entitled item only with library access.

        An unknown access class is refused, so a population that names a new class cannot widen delivery.
        """
        return item.get("access") == PUBLIC_ACCESS or (item.get("access") == ENTITLED_ACCESS and entitlement == BODIES)

    def preview(self, principal, session, body, *, view=None, origin=""):
        """What a saved or draft definition would deliver now, and why. It saves, activates and authorizes nothing."""
        self._require_enabled()
        with self.runtime._catalog.store() as store:
            current, _guards = verified_customer_session(self.runtime, store, principal, session)
            if "feed_id" in body:
                settings = self._owned(store, current, DEFINITION_KIND, body["feed_id"],
                                       "customer_feed_not_found")["payload"]["settings"]
            else:
                settings = definition_settings(body["definition"], self._directory())
        snapshot, selection, delivered, withheld = self._deliverable(
            settings, FeedReadContext(self.runtime, view, origin), current.entitlement)
        sizes = [len(canonical(item).encode("utf-8")) for item in delivered]
        stale = [{"item_id": item["item_id"], "title": item["title"], "checked_at": item["checked_at"]}
                 for item in delivered if item["stale"]]
        stale += [{"item_id": row["item_id"], "title": row["title"], "checked_at": None}
                  for row in selection.excluded if "stale_source" in row["reasons"]]
        return {"record_type": PREVIEW_RECORD_TYPE,
                "delivery_state": delivery_state(snapshot, selection, len(delivered)), "settings": settings,
                "filter_digest": filter_digest(settings),
                "snapshot": {"snapshot_id": snapshot.snapshot_id, "as_of": self._today().isoformat(),
                             "population_digest": population_digest(delivered)},
                "streams": [read.summary() for read in snapshot.reads],
                "items": [{key: item.get(key) for key in ("item_id", "title", "stream", "url", "checked_at", "stale",
                                                         "evidence_state", "matched_by", "update_types")}
                          for item in delivered[:PREVIEW_ROWS]],
                "excluded": [*selection.excluded[:PREVIEW_ROWS], *withheld[:PREVIEW_ROWS]],
                "stale_sources": stale[:PREVIEW_ROWS], "withdrawn_references": list(selection.withdrawn_references),
                "counts": {"delivered": len(delivered), "excluded": len(selection.excluded),
                           "withheld_for_access": len(withheld), "not_matched": selection.not_matched,
                           "truncated": selection.truncated},
                "estimated_usage": {"items": len(delivered), "bytes": sum(sizes),
                                    "byte_basis": "UTF-8 JSON of each delivered item record",
                                    "pages_at_maximum_page_size": math.ceil(len(delivered) / self.policy.maximum_page_items),
                                    "pulls_per_day": 1 if settings["cadence"] == "daily" else None,
                                    "tokens": None, "token_basis": "not estimated; no tokenizer is named"},
                "effects": {"settings_saved": False, "subscription_activated": False, "receiver_authorized": False,
                            "project_files_read": False},
                "content_policy": CONTENT_POLICY}

    def _agent(self, store, principal):
        """The checks every agent read makes: a current customer client key with the scope and the entitlement."""
        current, guards = self.runtime._revalidate(store, principal)
        if current.authentication_kind != KEY:
            raise CustomerFeedError("customer_feed_agent_credential_required", 403)
        key_row = self.runtime._catalog.read_id(store, current.authentication_record_id, kind=KEY)
        key = self.runtime._payload(key_row, KEY)
        if key.get("management_profile") != CLIENT_ACCESS_PROFILE or not key.get("owner_subject_record_id"):
            raise CustomerFeedError("customer_feed_agent_credential_required", 403)
        if PROVISIONING_METADATA_SCOPE not in current.scopes:
            raise CustomerFeedError("scope_required", 403)
        if self.policy.required_entitlement == BODIES and current.entitlement != BODIES:
            raise CustomerFeedError("customer_feed_entitlement_required", 403)
        return current, guards, key

    def _authorize_agent(self, store, principal, feed_id):
        """Every permission a pull needs, read in one store read: credential, account, feed and assignment."""
        catalog = self.runtime._catalog
        current, guards, key = self._agent(store, principal)
        definition = self._record(store, DEFINITION_KIND, current.tenant_id, feed_id)
        if definition is None or definition["payload"].get("owner_subject_record_id") != key["owner_subject_record_id"]:
            raise CustomerFeedError("customer_feed_not_found", 404)
        if definition["payload"].get("state") != "active":
            raise CustomerFeedError("customer_feed_paused", 409)
        assignment = self._assignment_for(store, current, key, feed_id)
        if assignment["payload"].get("state") != "active":
            raise CustomerFeedError("customer_feed_assignment_paused", 409)
        return current, guards, definition, assignment

    def _assignment_for(self, store, current, key, feed_id):
        """The assignment that lets this exact credential read this feed, or the refusal that it has none."""
        assignment_id = digest(["customer_feed_assignment", feed_id, current.authentication_record_id])[:32]
        assignment = self._record(store, ASSIGNMENT_KIND, current.tenant_id, assignment_id)
        if (assignment is None or assignment["payload"].get("agent_key_record_id") != current.authentication_record_id
                or assignment["payload"].get("feed_id") != feed_id
                or assignment["payload"].get("owner_subject_record_id") != key["owner_subject_record_id"]):
            raise CustomerFeedError("customer_feed_not_assigned", 403)
        return assignment

    def assigned(self, principal):
        """The feeds assigned to the calling agent credential, with their states. Metadata only."""
        self._require_enabled()
        catalog = self.runtime._catalog
        with catalog.store() as store:
            current, _guards, key = self._agent(store, principal)
            feeds = []
            for row in catalog.rows(store, ASSIGNMENT_KIND, current.tenant_id):
                value = checked(row, ASSIGNMENT_KIND)["payload"]
                if value.get("agent_key_record_id") != current.authentication_record_id:
                    continue
                definition = self._record(store, DEFINITION_KIND, current.tenant_id, value["feed_id"])
                if definition is None or definition["payload"]["owner_subject_record_id"] != key["owner_subject_record_id"]:
                    continue
                payload = definition["payload"]
                feeds.append({"feed_id": value["feed_id"], "name": payload["settings"]["name"],
                              "definition_version": payload["version"], "feed_state": payload["state"],
                              "assignment_state": value["state"], "cadence": payload["settings"]["cadence"],
                              "format": payload["settings"]["format"]})
        return {"record_type": ASSIGNED_RECORD_TYPE, "feeds": sorted(feeds, key=lambda row: row["feed_id"]),
                "pull_endpoint": PULL_PATH, "content_policy": CONTENT_POLICY}

    def _count_pull(self, tenant_id, key_record_id, feed_id):
        now, key = self._monotonic(), (tenant_id, key_record_id, feed_id)
        with self._pull_lock:
            window = self._pulls.setdefault(key, deque())
            while window and now - window[0] >= PULL_WINDOW_SECONDS:
                window.popleft()
            if len(window) >= self.policy.maximum_pulls_per_minute:
                wait = max(1, math.ceil(PULL_WINDOW_SECONDS - (now - window[0])))
                raise CustomerFeedError("customer_feed_quota_reached", 429, headers={"Retry-After": str(wait)},
                                        details={"record_type": "customer_feed_quota_refusal/v1",
                                                 "maximum_pulls_per_minute": self.policy.maximum_pulls_per_minute,
                                                 "retry_after_seconds": wait})
            window.append(now)
            if len(self._pulls) > PULL_WINDOWS_KEPT:
                for stale in [name for name, held in self._pulls.items() if not held or now - held[-1] >= PULL_WINDOW_SECONDS]:
                    self._pulls.pop(stale, None)

    def pull(self, principal, fields, *, view=None, origin="", byte_budget=200_000):
        """One page of one assigned feed, or a not modified answer, after every permission check.

        Returns `{"not_modified", "etag", "page", "markdown"}`. A served page writes its delivery metadata in an
        atomic batch that repeats the permission checks, so a revocation between the read and the delivery refuses
        the delivery instead of recording it.
        """
        self._require_enabled()
        query = pull_request(fields, self.policy)
        self._count_pull(principal.tenant_id, principal.authentication_record_id, query["feed_id"])
        with self.runtime._catalog.store() as store:
            current, _guards, definition, assignment = self._authorize_agent(store, principal, query["feed_id"])
        payload = definition["payload"]
        settings, version = payload["settings"], payload["version"]
        snapshot, selection, delivered, withheld = self._deliverable(
            settings, FeedReadContext(self.runtime, view, origin), current.entitlement)
        population = population_digest(delivered)
        assignment_id = assignment["payload"]["assignment_id"]
        binding = cursor_binding(current.tenant_id, assignment_id, current.authentication_record_id, query["feed_id"])
        offset = 0 if query["cursor"] is None else read_cursor(
            query["cursor"], version=version, filter_value=payload["filter_digest"], population=population,
            binding=binding, total=len(delivered))
        items = []
        used = 0
        for item in delivered[offset:offset + query["page_size"]]:
            size = len(canonical(item).encode("utf-8")) + 1
            if items and used + size > byte_budget:
                break
            if not items and size > byte_budget:
                raise CustomerFeedError("response_limit_exceeded", 413)
            items.append(item)
            used += size
        following = offset + len(items)
        page = {"record_type": PAGE_RECORD_TYPE,
                "feed": {"feed_id": query["feed_id"], "name": settings["name"], "definition_version": version,
                         "filter_digest": payload["filter_digest"], "cadence": settings["cadence"]},
                "assignment_id": assignment_id,
                "snapshot": {"snapshot_id": snapshot.snapshot_id, "population_digest": population, "order": ORDER,
                             "as_of": self._today().isoformat()},
                "delivery_state": delivery_state(snapshot, selection, len(delivered)),
                "streams": [read.summary() for read in snapshot.reads],
                "selection": {"delivered_items": len(delivered), "withheld_for_access": len(withheld),
                              "excluded_items": len(selection.excluded), "not_matched": selection.not_matched,
                              "truncated": selection.truncated, "stale_items": selection.stale_included,
                              "stale_withheld": selection.stale_withheld,
                              "withdrawn_references": list(selection.withdrawn_references)},
                "page": {"offset": offset, "items_on_page": len(items), "complete": following >= len(delivered),
                         "next_cursor": (mint_cursor(following, version, payload["filter_digest"], population, binding)
                                         if following < len(delivered) else None)},
                "context_policy": {"mode": settings["context_mode"], "max_items": settings["max_items"],
                                   "max_bytes": settings["max_bytes"], "max_age_days": settings["max_age_days"],
                                   "on_stale": settings["on_stale"]},
                "content_policy": CONTENT_POLICY, "items": items}
        markdown = markdown_page(page) if query["format"] == "markdown" else None
        etag = _etag(markdown.encode("utf-8") if markdown is not None else page)
        if _validator_matches(query["if_none_match"], etag):
            return {"not_modified": True, "etag": etag, "page": None, "markdown": None}
        self._record_delivery(principal, query["feed_id"], (definition, assignment), page, used)
        return {"not_modified": False, "etag": etag, "page": page, "markdown": markdown}

    def _record_delivery(self, principal, feed_id, rows, page, size):
        """Write one page's delivery metadata, after every permission check again, or refuse the delivery."""
        catalog = self.runtime._catalog
        definition, assignment = rows
        assignment_id = page["assignment_id"]
        with catalog.serialized(("customer_feed_delivery", principal.tenant_id, assignment_id)):
            with catalog.store(write=True) as store:
                current, guards, held_definition, held_assignment = self._authorize_agent(store, principal, feed_id)
                if (held_definition["record_version"] != definition["record_version"]
                        or held_assignment["record_version"] != assignment["record_version"]):
                    raise CustomerFeedError("customer_feed_changed_during_delivery", 409)
                previous = self._record(store, DELIVERY_KIND, current.tenant_id, assignment_id)
                entries = list(previous["payload"]["entries"]) if previous is not None else []
                version, population = page["feed"]["definition_version"], page["snapshot"]["population_digest"]
                now, offset, count = self._now(), page["page"]["offset"], page["page"]["items_on_page"]
                found = next((entry for entry in entries if entry["definition_version"] == version
                              and entry["population_digest"] == population), None)
                if found is None:
                    found = {"definition_version": version, "population_digest": population,
                             "snapshot_id": page["snapshot"]["snapshot_id"], "delivery_state": page["delivery_state"],
                             "total_items": page["selection"]["delivered_items"], "first_delivered_at": now,
                             "pages_served": 0, "items_served": 0, "bytes_served": 0, "served_through": 0,
                             "repeated_pages": 0, "complete": False}
                else:
                    entries.remove(found)
                    found = dict(found)
                found["repeated_pages"] += int(offset + count <= found["served_through"] and found["pages_served"] > 0)
                found.update(last_delivered_at=now, pages_served=found["pages_served"] + 1,
                             items_served=found["items_served"] + count, bytes_served=found["bytes_served"] + size,
                             served_through=max(found["served_through"], offset + count),
                             delivery_state=page["delivery_state"])
                found["complete"] = found["served_through"] >= found["total_items"]
                entries = [found, *entries][:self.policy.delivery_history_entries]
                row = catalog.record(DELIVERY_KIND, (current.tenant_id, assignment_id), {
                    "record_type": DELIVERY_RECORD_TYPE, "tenant_id": current.tenant_id,
                    "owner_subject_record_id": assignment["payload"]["owner_subject_record_id"],
                    "assignment_id": assignment_id, "feed_id": feed_id, "entries": entries},
                    tenant_id=current.tenant_id)
                catalog.commit(store, (row,), (*guards, catalog.guard(held_definition), catalog.guard(held_assignment),
                                               catalog.guard(previous, row["record_id"])))
