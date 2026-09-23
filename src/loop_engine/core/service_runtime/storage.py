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
from typing import Callable
import uuid

from ...catalog.protocol import (
    BATCH_ACKNOWLEDGMENT_VERSION, CatalogBatchAcknowledgment, CatalogRecordPrecondition, CatalogWriteBatch,
    PreconditionFailed, StoreError, require_atomic_batch, require_atomic_removal,
)
from ...catalog.handshake import negotiate
from ...catalog.query import IntelligenceQuery
from ...catalog.stores.sqlite_store import SQLiteRecordStore
from .records import (SERVICE_COLLECTION, ServiceCommitUnknown, ServiceRuntimeConfig,
                      ServiceRuntimeError, canonical, digest)


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
        except (StoreError, OSError):
            raise ServiceRuntimeError("store_unavailable") from None
        try:
            decision = negotiate(store.capabilities(), required_operations=("get", "query"), write_requested=False)
            if not decision.permits("get") or not decision.permits("query"):
                raise ServiceRuntimeError("store_contract_unavailable")
            if write:
                require_atomic_batch(store)
            yield store
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
        try:
            acknowledgment = store.apply_batch(request)
        except PreconditionFailed:
            raise ServiceRuntimeError("concurrent_update", "state changed; retry the same operation identity") from None
        except Exception:
            raise ServiceCommitUnknown() from None
        if (not isinstance(acknowledgment, CatalogBatchAcknowledgment)
                or acknowledgment.record_type != BATCH_ACKNOWLEDGMENT_VERSION
                or acknowledgment.batch_digest != request.digest or acknowledgment.committed is not True):
            raise ServiceCommitUnknown()
        removed_versions = {guard.record_id: guard.record_version for guard in request.preconditions}
        try:
            confirmed = (all(store.get(row["record_id"]) == row for row in request.records)
                         and all(_no_longer_held(store.get(identity), removed_versions[identity])
                                 for identity in request.removals))
        except Exception:
            confirmed = False
        if not confirmed:
            raise ServiceCommitUnknown()
        return acknowledgment


def _no_longer_held(row, removed_version):
    """A removal is confirmed when the store no longer holds that record at the removed version.

    A later writer may create the same identity again with a new version; that
    is not the removed record, so it does not make the removal unknown.
    """
    return row is None or row.get("record_version") != removed_version
