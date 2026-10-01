"""Service-domain records over the existing negotiated catalogue authority.

This is a scoped domain binding, not another database adapter. SQLite remains
the default CatalogStore. Writes require exact atomic read-set semantics;
other declared adapters can supply the same versioned optional protocol. A
commit that removes records also requires the negotiated removal extension,
and it is refused before any effect by a store that does not declare it.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import threading
import time
from typing import Callable
import uuid

from ...catalog.protocol import (
    BATCH_ACKNOWLEDGMENT_VERSION, CatalogBatchAcknowledgment, CatalogRecordPrecondition, CatalogWriteBatch,
    PreconditionFailed, StoreBusy, StoreError, require_atomic_batch, require_atomic_removal,
)
from ...catalog.handshake import negotiate
from ...catalog.query import IntelligenceQuery
from ...catalog.stores.sqlite_store import SQLiteRecordStore
from .records import (SERVICE_COLLECTION, ServiceCommitUnknown, ServiceRuntimeConfig,
                      ServiceRuntimeError, canonical, digest)

#: A store read or uncommitted batch was blocked. This does not assert that an earlier operation wrote nothing.
STORE_BUSY_CODE = "store_busy"
#: How long one write waits behind the other writes of this process to the same store before it answers
#: `store_busy`. The store is one serialized writer, so queueing here costs no throughput, and a queue is fairer than
#: every thread retrying inside SQLite's own busy wait, where one writer can lose to the others until it times out.
WRITE_QUEUE_SECONDS = 5.0
#: A committed batch has this retry window, plus an in-flight store call's timeout, for read-only confirmation.
#: Exhaustion stays unknown, never a no-write refusal or another write attempt.
COMMIT_CONFIRMATION_SECONDS, COMMIT_CONFIRMATION_RETRY_SECONDS = 5.0, 0.05
_WRITE_QUEUES, _WRITE_QUEUES_GUARD = {}, threading.Lock()


def write_queue(database_path):
    """The one lock the writes of this process to one store take in turn.

    It is re-entrant, so a write made from inside another write's store call on the same thread, as a check that
    stages a race does, passes instead of waiting on itself."""
    with _WRITE_QUEUES_GUARD:
        return _WRITE_QUEUES.setdefault(database_path, threading.RLock())


@dataclass(frozen=True)
class ServiceCatalogBinding:
    """Host-installed opener; the request cannot supply its database or namespace."""

    config: ServiceRuntimeConfig
    open_store: Callable[[bool], object] | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.config, ServiceRuntimeConfig):
            raise ServiceRuntimeError("invalid_configuration")
        if self.open_store is not None and not callable(self.open_store):
            raise ServiceRuntimeError("invalid_configuration")

    @contextmanager
    def store(self, *, write=False):
        self.config.__post_init__()
        if write and self.config.writes_authorized is not True:
            raise ServiceRuntimeError("host_write_authority_required")
        try:
            store = (self.open_store(write) if self.open_store is not None else
                     SQLiteRecordStore(self.config.database_path, read_only=not write))
        except StoreBusy:
            # The opening DDL met another connection's held lock. Nothing was read or written, so the
            # same open may be sent again: this is the store's own queueing state, not an unavailable store.
            raise ServiceRuntimeError(STORE_BUSY_CODE, "the store stayed locked; nothing was read; retry") from None
        except (StoreError, OSError):
            raise ServiceRuntimeError("store_unavailable") from None
        try:
            decision = negotiate(store.capabilities(), required_operations=("get", "query"), write_requested=False)
            if not decision.permits("get") or not decision.permits("query"):
                raise ServiceRuntimeError("store_contract_unavailable")
            if write:
                require_atomic_batch(store)
            yield store
        except StoreBusy:
            raise ServiceRuntimeError(STORE_BUSY_CODE, "the store read stayed locked; retry") from None
        except StoreError:
            raise ServiceRuntimeError("store_unavailable") from None
        finally:
            store.close()

    def identity(self, kind, logical_identity):
        return "service:" + digest([self.config.namespace, kind, logical_identity])

    def record(self, kind, logical_identity, payload, *, tenant_id=""):
        row = {"record_id": self.identity(kind, logical_identity), "record_version": uuid.uuid4().hex,
                "namespace": self.config.namespace, "source_collection": SERVICE_COLLECTION,
                "artifact_kind": kind, "intelligence_layer": "", "lifecycle": "service_internal",
                "attributes": {"tenant_id": tenant_id}, "payload": payload}
        return json.loads(canonical(row))

    def read(self, store, kind, logical_identity):
        return self.read_id(store, self.identity(kind, logical_identity), kind=kind)

    def read_id(self, store, identity, *, kind=None):
        row = store.get(identity)
        if row is None:
            return None
        if (row.get("namespace") != self.config.namespace or row.get("source_collection") != SERVICE_COLLECTION
                or (kind is not None and row.get("artifact_kind") != kind)
                or not isinstance(row.get("payload"), dict)):
            raise ServiceRuntimeError("record_scope_or_shape_invalid")
        return row

    def rows(self, store, kind, tenant_id):
        rows = store.query(IntelligenceQuery(namespaces=(self.config.namespace,),
            source_collections=(SERVICE_COLLECTION,), artifact_kinds=(kind,),
            attributes={"tenant_id": {"equals": tenant_id}}))
        return [row for row in rows if row.get("namespace") == self.config.namespace
                and row.get("source_collection") == SERVICE_COLLECTION and row.get("artifact_kind") == kind
                and row.get("attributes", {}).get("tenant_id") == tenant_id]

    def rows_all(self, store, kind):
        """Every record of one kind in this namespace, for a host-side report.

        The tenant attribute is not part of this query, so an operator report
        can walk all accounts. No customer path uses it; a request that acts for
        one account keeps using `rows`, which filters on the exact tenant.
        """
        rows = store.query(IntelligenceQuery(namespaces=(self.config.namespace,),
            source_collections=(SERVICE_COLLECTION,), artifact_kinds=(kind,)))
        return [row for row in rows if row.get("namespace") == self.config.namespace
                and row.get("source_collection") == SERVICE_COLLECTION and row.get("artifact_kind") == kind]

    @staticmethod
    def guard(row, identity=None):
        return (CatalogRecordPrecondition(identity, must_not_exist=True) if row is None else
                CatalogRecordPrecondition(row["record_id"], row["record_version"]))

    def commit(self, store, records, guards, removals=()):
        """Commit writes and exact removals in one atomic batch, or raise.

        A removal names a record identity, and `guards` must hold that record's
        exact version, as `guard(row)` gives it. A store that does not declare
        the removal extension is refused with `store_contract_unavailable`
        before the batch is built or sent. The acknowledgment must name this
        exact batch, and every write and removal is read back before success.
        """
        removals = tuple(removals)
        if removals:
            try:
                require_atomic_removal(store)
            except StoreError:
                raise ServiceRuntimeError("store_contract_unavailable") from None
        request = CatalogWriteBatch.from_records(records, guards, removals)
        queue = write_queue(self.config.database_path)
        if not queue.acquire(timeout=WRITE_QUEUE_SECONDS):
            raise ServiceRuntimeError(STORE_BUSY_CODE, "other writes held the store; nothing was written; retry")
        try:
            acknowledgment = store.apply_batch(request)
        except PreconditionFailed:
            raise ServiceRuntimeError("concurrent_update", "state changed; retry the same operation identity") from None
        except StoreBusy:
            raise ServiceRuntimeError(STORE_BUSY_CODE, "the store stayed locked; nothing was written; retry") from None
        except Exception:
            raise ServiceCommitUnknown() from None
        finally:
            queue.release()
        if (not isinstance(acknowledgment, CatalogBatchAcknowledgment)
                or acknowledgment.record_type != BATCH_ACKNOWLEDGMENT_VERSION
                or acknowledgment.batch_digest != request.digest or acknowledgment.committed is not True):
            raise ServiceCommitUnknown()
        removed_versions = {guard.record_id: guard.record_version for guard in request.preconditions}
        deadline = time.monotonic() + COMMIT_CONFIRMATION_SECONDS
        while True:
            try:
                confirmed = (all(store.get(row["record_id"]) == row for row in request.records)
                             and all(_no_longer_held(store.get(identity), removed_versions[identity])
                                     for identity in request.removals))
                break
            except StoreBusy:
                if time.monotonic() + COMMIT_CONFIRMATION_RETRY_SECONDS >= deadline:
                    confirmed = False
                    break
                time.sleep(COMMIT_CONFIRMATION_RETRY_SECONDS)
            except Exception:
                confirmed = False
                break
        if not confirmed:
            raise ServiceCommitUnknown()
        return acknowledgment


def _no_longer_held(row, removed_version):
    """A removal is confirmed when the store no longer holds that record at the removed version.

    A later writer may create the same identity again with a new version; that
    is not the removed record, so it does not make the removal unknown.
    """
    return row is None or row.get("record_version") != removed_version
