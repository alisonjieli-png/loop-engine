"""Service-domain records over the existing negotiated catalogue authority.

This is a scoped domain binding, not another database adapter. SQLite remains
the default CatalogStore. Writes require exact atomic read-set semantics;
other declared adapters can supply the same versioned optional protocol.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
from typing import Callable
import uuid

from ...catalog.protocol import (
    BATCH_ACKNOWLEDGMENT_VERSION, CatalogBatchAcknowledgment, CatalogRecordPrecondition, CatalogWriteBatch,
    PreconditionFailed, StoreError, require_atomic_batch,
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

    @staticmethod
    def guard(row, identity=None):
        return (CatalogRecordPrecondition(identity, must_not_exist=True) if row is None else
                CatalogRecordPrecondition(row["record_id"], row["record_version"]))

    def commit(self, store, records, guards):
        request = CatalogWriteBatch.from_records(records, guards)
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
        try:
            confirmed = all(store.get(row["record_id"]) == row for row in request.records)
        except Exception:
            confirmed = False
        if not confirmed:
            raise ServiceCommitUnknown()
        return acknowledgment
