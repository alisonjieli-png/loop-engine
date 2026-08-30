"""Storage-neutral access to exact values produced by Loops.

``LoopValueRef`` is the logical identity.  A storage binding says where one
materialization is available without exposing that location to consumers.
The resolver checks scope, permissions, size, contract identity, and content
digest before returning a value.  It is an internal capability used by Loops,
not another runtime or graph vertex.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from ..loop.atomic_primitives import LoopValue, LoopValueRef
from ..loop.intrinsic_kernel import intrinsic_content_digest


class InformationAccessFailureCode(str, Enum):
    """Closed failure classes for storage-neutral value access."""

    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    ACCESS_DENIED = "access_denied"
    TOO_LARGE = "too_large"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    INTEGRITY_VIOLATION = "integrity_violation"
    UNSUPPORTED_DURABILITY = "unsupported_durability"


class InformationDurability(str, Enum):
    """How long one physical materialization is intended to remain valid."""

    ACTIVATION = "activation"
    RUN = "run"
    SERIES = "series"
    PROJECT = "project"
    PERSISTENT = "persistent"


class InformationScope(str, Enum):
    """Who may request one materialization before permission checks."""

    PRIVATE_LOOP = "private_loop"
    ALLOWED_LOOPS = "allowed_loops"
    RUN_SHARED = "run_shared"
    PROJECT_SHARED = "project_shared"
    PUBLIC = "public"


class InformationAccessOperation(str, Enum):
    """The two storage-neutral read operations in this checkpoint."""

    DESCRIBE = "describe"
    MATERIALIZE = "materialize"


class InformationAccessError(RuntimeError):
    """A value could not be described or materialized safely."""

    def __init__(self, code: InformationAccessFailureCode, detail: str):
        self.code = InformationAccessFailureCode(code)
        super().__init__(detail)


def _names(label: str, values) -> tuple[str, ...]:
    normalized = tuple(values or ())
    if (any(not isinstance(value, str) or not value.strip()
            for value in normalized)
            or len(normalized) != len(set(normalized))):
        raise InformationAccessError(
            InformationAccessFailureCode.INVALID_REQUEST,
            f"{label} must contain unique non-empty strings")
    return tuple(sorted(normalized))


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise InformationAccessError(
            InformationAccessFailureCode.INVALID_REQUEST,
            "durable information materialization requires a JSON value") from exc


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ref_key(reference: LoopValueRef) -> str:
    return _canonical_json(reference.to_dict())


@dataclass(frozen=True)
class InformationPublicationRequest:
    """One exact value plus the storage and access semantics to bind."""

    value: LoopValue
    adapter_id: str
    durability: InformationDurability | str
    scope: InformationScope | str
    run_id: str = ""
    authorized_loop_ids: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    media_type: str = "application/json"

    def __post_init__(self) -> None:
        if not isinstance(self.value, LoopValue):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "publication requires one LoopValue")
        if not isinstance(self.adapter_id, str) or not self.adapter_id.strip():
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "publication requires an adapter ID")
        try:
            object.__setattr__(
                self, "durability", InformationDurability(self.durability))
            object.__setattr__(self, "scope", InformationScope(self.scope))
        except ValueError as exc:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "publication names an unsupported durability or scope") from exc
        loops = _names("authorized_loop_ids", self.authorized_loop_ids)
        permissions = _names(
            "required_permissions", self.required_permissions)
        object.__setattr__(self, "authorized_loop_ids", loops)
        object.__setattr__(self, "required_permissions", permissions)
        if self.scope is InformationScope.ALLOWED_LOOPS and not loops:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "allowed_loops scope requires at least one Loop ID")
        if self.scope is InformationScope.RUN_SHARED and not self.run_id:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "run_shared information requires a run ID")
        if not self.media_type.strip():
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "publication requires a media type")


@dataclass(frozen=True)
class InformationStorageBinding:
    """One physical materialization behind an exact logical value reference."""

    binding_id: str
    value_ref: LoopValueRef
    adapter_id: str
    locator_token: str = field(repr=False, compare=False)
    durability: InformationDurability | str
    scope: InformationScope | str
    owner_loop_id: str
    run_id: str = ""
    authorized_loop_ids: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    media_type: str = "application/json"
    size_bytes: int = 0
    binding_digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.value_ref, LoopValueRef):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "storage binding requires a LoopValueRef")
        if any(not isinstance(item, str) or not item.strip() for item in (
                self.binding_id, self.adapter_id, self.locator_token,
                self.owner_loop_id, self.media_type)):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "storage binding identity is incomplete")
        try:
            object.__setattr__(
                self, "durability", InformationDurability(self.durability))
            object.__setattr__(self, "scope", InformationScope(self.scope))
        except ValueError as exc:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "storage binding names an unsupported durability or scope") from exc
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "storage binding size must be a non-negative integer")
        object.__setattr__(
            self, "authorized_loop_ids",
            _names("authorized_loop_ids", self.authorized_loop_ids))
        object.__setattr__(
            self, "required_permissions",
            _names("required_permissions", self.required_permissions))
        expected = _digest_text(_canonical_json(self._digest_body()))
        if self.binding_digest and self.binding_digest != expected:
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "storage binding digest does not match")
        object.__setattr__(self, "binding_digest", expected)

    def _digest_body(self) -> dict:
        return {
            "binding_id": self.binding_id,
            "value_ref": self.value_ref.to_dict(),
            "adapter_id": self.adapter_id,
            "locator_digest": _digest_text(self.locator_token),
            "durability": self.durability.value,
            "scope": self.scope.value,
            "owner_loop_id": self.owner_loop_id,
            "run_id": self.run_id,
            "authorized_loop_ids": list(self.authorized_loop_ids),
            "required_permissions": list(self.required_permissions),
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
        }

    def to_public_dict(self) -> dict:
        """Return storage metadata without the opaque locator token."""
        return {**self._digest_body(), "binding_digest": self.binding_digest}

    def to_storage_dict(self) -> dict:
        """Return the complete binding for a trusted binding store."""
        return {
            **self.to_public_dict(), "locator_token": self.locator_token,
        }

    @classmethod
    def from_storage_dict(cls, value: dict) -> "InformationStorageBinding":
        expected = {
            "binding_id", "value_ref", "adapter_id", "locator_digest",
            "locator_token", "durability", "scope", "owner_loop_id",
            "run_id", "authorized_loop_ids", "required_permissions",
            "media_type", "size_bytes", "binding_digest",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "stored information binding has an invalid shape")
        if _digest_text(str(value["locator_token"])) != value["locator_digest"]:
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "stored information locator digest does not match")
        return cls(
            binding_id=str(value["binding_id"]),
            value_ref=LoopValueRef.from_dict(value["value_ref"]),
            adapter_id=str(value["adapter_id"]),
            locator_token=str(value["locator_token"]),
            durability=str(value["durability"]),
            scope=str(value["scope"]),
            owner_loop_id=str(value["owner_loop_id"]),
            run_id=str(value["run_id"]),
            authorized_loop_ids=tuple(value["authorized_loop_ids"]),
            required_permissions=tuple(value["required_permissions"]),
            media_type=str(value["media_type"]),
            size_bytes=int(value["size_bytes"]),
            binding_digest=str(value["binding_digest"]),
        )


@dataclass(frozen=True)
class InformationBindingDescriptor:
    """Public location-independent facts for one available materialization."""

    binding_id: str
    adapter_id: str
    durability: InformationDurability
    scope: InformationScope
    media_type: str
    size_bytes: int
    required_permissions: tuple[str, ...]
    binding_digest: str

    @classmethod
    def from_binding(
            cls, binding: InformationStorageBinding
            ) -> "InformationBindingDescriptor":
        return cls(
            binding.binding_id, binding.adapter_id, binding.durability,
            binding.scope, binding.media_type, binding.size_bytes,
            binding.required_permissions, binding.binding_digest)


@dataclass(frozen=True)
class InformationDescriptor:
    """One exact value identity plus accessible materialization choices."""

    value_ref: LoopValueRef
    bindings: tuple[InformationBindingDescriptor, ...]


@dataclass(frozen=True)
class InformationAccessRequest:
    """What one consuming Loop needs, without naming a physical locator."""

    requester_loop_id: str
    value_ref: LoopValueRef
    purpose: str
    operation: InformationAccessOperation | str = (
        InformationAccessOperation.MATERIALIZE)
    requester_run_id: str = ""
    granted_permissions: tuple[str, ...] = ()
    preferred_adapter_ids: tuple[str, ...] = ()
    maximum_bytes: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.value_ref, LoopValueRef):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "information access requires a LoopValueRef")
        if any(not isinstance(item, str) or not item.strip()
               for item in (self.requester_loop_id, self.purpose)):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "information access requires requester and purpose")
        try:
            object.__setattr__(
                self, "operation", InformationAccessOperation(self.operation))
        except ValueError as exc:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "information access operation is unsupported") from exc
        object.__setattr__(
            self, "granted_permissions",
            _names("granted_permissions", self.granted_permissions))
        object.__setattr__(
            self, "preferred_adapter_ids",
            _names("preferred_adapter_ids", self.preferred_adapter_ids))
        if not isinstance(self.maximum_bytes, int) or self.maximum_bytes < 0:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "maximum_bytes must be a non-negative integer")


@dataclass(frozen=True)
class InformationMaterialization:
    """A verified value returned through one selected storage adapter."""

    value_ref: LoopValueRef
    binding_id: str
    adapter_id: str
    value: object = field(repr=False, compare=False)
    media_type: str = "application/json"
    size_bytes: int = 0
    digest_verified: bool = True


class InformationStorageAdapter(Protocol):
    """Backend contract used by the storage-neutral resolver."""

    adapter_id: str

    def store(
            self, request: InformationPublicationRequest
            ) -> InformationStorageBinding: ...

    def load(self, binding: InformationStorageBinding) -> object: ...


def _make_binding(
        request: InformationPublicationRequest, locator: str,
        size_bytes: int) -> InformationStorageBinding:
    value_ref = request.value.to_ref()
    identity = _digest_text(_canonical_json({
        "adapter_id": request.adapter_id,
        "value_ref": value_ref.to_dict(),
        "locator_digest": _digest_text(locator),
    }))[:24]
    return InformationStorageBinding(
        binding_id=f"binding.{identity}", value_ref=value_ref,
        adapter_id=request.adapter_id, locator_token=locator,
        durability=request.durability, scope=request.scope,
        owner_loop_id=request.value.producer_loop_id,
        run_id=request.run_id,
        authorized_loop_ids=request.authorized_loop_ids,
        required_permissions=request.required_permissions,
        media_type=request.media_type, size_bytes=size_bytes)


class InlineInformationAdapter:
    """Process-local materialization for activation and run-scoped values."""

    adapter_id = "runtime.inline"

    def __init__(self) -> None:
        self._values: dict[str, LoopValue] = {}

    def store(
            self, request: InformationPublicationRequest
            ) -> InformationStorageBinding:
        if request.adapter_id != self.adapter_id:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "inline publication names a different adapter")
        if request.durability not in (
                InformationDurability.ACTIVATION, InformationDurability.RUN):
            raise InformationAccessError(
                InformationAccessFailureCode.UNSUPPORTED_DURABILITY,
                "inline values cannot claim series or persistent durability")
        key = _digest_text(_ref_key(request.value.to_ref()))
        self._values[key] = request.value
        try:
            size = len(_canonical_json(request.value.value).encode("utf-8"))
        except InformationAccessError:
            size = len(repr(request.value.value).encode("utf-8"))
        return _make_binding(request, key, size)

    def load(self, binding: InformationStorageBinding) -> object:
        value = self._values.get(binding.locator_token)
        if value is None:
            raise InformationAccessError(
                InformationAccessFailureCode.ADAPTER_UNAVAILABLE,
                "process-local value is no longer available")
        if value.to_ref() != binding.value_ref:
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "process-local value reference changed")
        return value.value


class ContextArtifactInformationAdapter:
    """JSON values stored through the existing content-addressed artifact store."""

    adapter_id = "local.context_artifact"

    def __init__(self, store) -> None:
        from .context_artifacts import ContextArtifactStore
        if not isinstance(store, ContextArtifactStore):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "artifact information adapter requires ContextArtifactStore")
        self._store = store

    def store(
            self, request: InformationPublicationRequest
            ) -> InformationStorageBinding:
        if request.adapter_id != self.adapter_id:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "artifact publication names a different adapter")
        encoded = _canonical_json(request.value.value).encode("utf-8")
        reference = self._store.put(
            encoded, media_type=request.media_type, encoding="utf-8",
            artifact_kind="loop_value")
        locator = _canonical_json(reference.to_dict())
        return _make_binding(request, locator, len(encoded))

    def load(self, binding: InformationStorageBinding) -> object:
        from .context_artifacts import ContextArtifactRef
        try:
            reference = ContextArtifactRef.from_dict(
                json.loads(binding.locator_token))
            encoded = self._store.get(reference)
            return json.loads(encoded.decode("utf-8"))
        except InformationAccessError:
            raise
        except Exception as exc:
            raise InformationAccessError(
                InformationAccessFailureCode.ADAPTER_UNAVAILABLE,
                "artifact materialization is unavailable") from exc


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS loop_value_materializations (
    binding_id TEXT PRIMARY KEY,
    value_ref TEXT NOT NULL,
    payload TEXT NOT NULL,
    media_type TEXT NOT NULL
)
"""


class SQLiteInformationAdapter:
    """Durable JSON value materialization in one explicit SQLite file."""

    adapter_id = "local.sqlite_information"

    def __init__(self, database_path: str) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "SQLite information adapter requires an explicit path")
        path = Path(database_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = str(path)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.execute(_SQLITE_SCHEMA)
        self._connection.commit()

    def store(
            self, request: InformationPublicationRequest
            ) -> InformationStorageBinding:
        if request.adapter_id != self.adapter_id:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "SQLite publication names a different adapter")
        if request.durability is InformationDurability.ACTIVATION:
            raise InformationAccessError(
                InformationAccessFailureCode.UNSUPPORTED_DURABILITY,
                "SQLite publication must outlive one activation")
        payload = _canonical_json(request.value.value)
        locator = "value." + _digest_text(_ref_key(request.value.to_ref()))[:24]
        binding = _make_binding(request, locator, len(payload.encode("utf-8")))
        existing = self._connection.execute(
            "SELECT value_ref, payload, media_type FROM "
            "loop_value_materializations WHERE binding_id = ?",
            (binding.locator_token,)).fetchone()
        row = (_ref_key(binding.value_ref), payload, binding.media_type)
        if existing is not None and tuple(existing) != row:
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "SQLite binding identity already names different content")
        if existing is None:
            self._connection.execute(
                "INSERT INTO loop_value_materializations VALUES (?, ?, ?, ?)",
                (binding.locator_token, *row))
            self._connection.commit()
        return binding

    def load(self, binding: InformationStorageBinding) -> object:
        row = self._connection.execute(
            "SELECT value_ref, payload, media_type FROM "
            "loop_value_materializations WHERE binding_id = ?",
            (binding.locator_token,)).fetchone()
        if row is None:
            raise InformationAccessError(
                InformationAccessFailureCode.ADAPTER_UNAVAILABLE,
                "SQLite value materialization is unavailable")
        try:
            stored_ref = LoopValueRef.from_dict(json.loads(row[0]))
            value = json.loads(row[1])
        except Exception as exc:
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "SQLite value materialization is malformed") from exc
        if stored_ref != binding.value_ref or row[2] != binding.media_type:
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "SQLite materialization metadata changed")
        return value

    def close(self) -> None:
        self._connection.close()


class InformationResolver:
    """Resolve exact Loop values without exposing physical locator tokens."""

    def __init__(self, observations=None) -> None:
        from .runtime_observer import RuntimeObservationServices
        self._adapters: dict[str, InformationStorageAdapter] = {}
        self._bindings: dict[str, list[InformationStorageBinding]] = {}
        self._observations = observations or RuntimeObservationServices()

    def register(self, adapter: InformationStorageAdapter) -> None:
        adapter_id = getattr(adapter, "adapter_id", "")
        if (not isinstance(adapter_id, str) or not adapter_id
                or not callable(getattr(adapter, "store", None))
                or not callable(getattr(adapter, "load", None))):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "information adapter does not satisfy its protocol")
        if adapter_id in self._adapters:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                f"information adapter {adapter_id!r} is already registered")
        self._adapters[adapter_id] = adapter

    def attach(self, binding: InformationStorageBinding) -> None:
        if not isinstance(binding, InformationStorageBinding):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "resolver attachment requires an information binding")
        key = _ref_key(binding.value_ref)
        existing = self._bindings.setdefault(key, [])
        if any(item.binding_id == binding.binding_id for item in existing):
            return
        existing.append(binding)

    def publish(
            self, request: InformationPublicationRequest
            ) -> InformationStorageBinding:
        if not isinstance(request, InformationPublicationRequest):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "publish requires an InformationPublicationRequest")
        adapter = self._adapters.get(request.adapter_id)
        if adapter is None:
            raise InformationAccessError(
                InformationAccessFailureCode.ADAPTER_UNAVAILABLE,
                f"information adapter {request.adapter_id!r} is unavailable")
        binding = adapter.store(request)
        if binding.value_ref != request.value.to_ref():
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "information adapter returned a different value reference")
        self.attach(binding)
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "information_binding_published", {
                "binding_id": binding.binding_id,
                "adapter_id": binding.adapter_id,
                "value_digest": binding.value_ref.content_digest,
                "durability": binding.durability.value,
                "scope": binding.scope.value,
                "size_bytes": binding.size_bytes, "status": "published",
            }, loop_id=request.value.producer_loop_id))
        return binding

    def describe(self, request: InformationAccessRequest) -> InformationDescriptor:
        if request.operation is not InformationAccessOperation.DESCRIBE:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "describe requires a describe access request")
        bindings = tuple(
            InformationBindingDescriptor.from_binding(binding)
            for binding in self._eligible_bindings(request))
        return InformationDescriptor(request.value_ref, bindings)

    def materialize(
            self, request: InformationAccessRequest
            ) -> InformationMaterialization:
        if request.operation is not InformationAccessOperation.MATERIALIZE:
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "materialize requires a materialize access request")
        bindings = self._eligible_bindings(request)
        if request.preferred_adapter_ids:
            preference = {
                adapter_id: index for index, adapter_id
                in enumerate(request.preferred_adapter_ids)}
            bindings = tuple(sorted(
                (item for item in bindings
                 if item.adapter_id in preference),
                key=lambda item: preference[item.adapter_id]))
        if not bindings:
            raise InformationAccessError(
                InformationAccessFailureCode.NOT_FOUND,
                "no eligible materialization matches the request")
        binding = bindings[0]
        adapter = self._adapters.get(binding.adapter_id)
        if adapter is None:
            raise InformationAccessError(
                InformationAccessFailureCode.ADAPTER_UNAVAILABLE,
                f"information adapter {binding.adapter_id!r} is unavailable")
        value = adapter.load(binding)
        if intrinsic_content_digest(value) != request.value_ref.content_digest:
            raise InformationAccessError(
                InformationAccessFailureCode.INTEGRITY_VIOLATION,
                "materialized value content digest does not match its reference")
        materialization = InformationMaterialization(
            request.value_ref, binding.binding_id, binding.adapter_id, value,
            binding.media_type, binding.size_bytes, True)
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "information_materialized", {
                "binding_id": binding.binding_id,
                "adapter_id": binding.adapter_id,
                "value_digest": binding.value_ref.content_digest,
                "size_bytes": binding.size_bytes, "status": "materialized",
            }, loop_id=request.requester_loop_id))
        return materialization

    def _eligible_bindings(
            self, request: InformationAccessRequest
            ) -> tuple[InformationStorageBinding, ...]:
        if not isinstance(request, InformationAccessRequest):
            raise InformationAccessError(
                InformationAccessFailureCode.INVALID_REQUEST,
                "information resolver requires an access request")
        bindings = tuple(self._bindings.get(_ref_key(request.value_ref), ()))
        if not bindings:
            raise InformationAccessError(
                InformationAccessFailureCode.NOT_FOUND,
                "no storage binding exists for this value reference")
        authorized = tuple(
            item for item in bindings if self._authorized(item, request))
        if not authorized:
            raise InformationAccessError(
                InformationAccessFailureCode.ACCESS_DENIED,
                "no storage binding is accessible to the requesting Loop")
        sized = tuple(
            item for item in authorized
            if not request.maximum_bytes
            or item.size_bytes <= request.maximum_bytes)
        if not sized:
            raise InformationAccessError(
                InformationAccessFailureCode.TOO_LARGE,
                "every accessible materialization exceeds maximum_bytes")
        return sized

    @staticmethod
    def _authorized(
            binding: InformationStorageBinding,
            request: InformationAccessRequest) -> bool:
        if not set(binding.required_permissions) <= set(
                request.granted_permissions):
            return False
        if binding.scope is InformationScope.PRIVATE_LOOP:
            return request.requester_loop_id == binding.owner_loop_id
        if binding.scope is InformationScope.ALLOWED_LOOPS:
            return request.requester_loop_id in binding.authorized_loop_ids
        if binding.scope is InformationScope.RUN_SHARED:
            return bool(binding.run_id) and (
                request.requester_run_id == binding.run_id)
        if binding.scope is InformationScope.PROJECT_SHARED:
            return "information.read.project" in request.granted_permissions
        return binding.scope is InformationScope.PUBLIC


__all__ = (
    "ContextArtifactInformationAdapter", "InformationAccessError",
    "InformationAccessFailureCode", "InformationAccessOperation",
    "InformationAccessRequest", "InformationBindingDescriptor",
    "InformationDescriptor", "InformationDurability",
    "InformationMaterialization", "InformationPublicationRequest",
    "InformationResolver", "InformationScope", "InformationStorageAdapter",
    "InformationStorageBinding", "InlineInformationAdapter",
    "SQLiteInformationAdapter",
)
