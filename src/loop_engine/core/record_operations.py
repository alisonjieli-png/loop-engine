"""Loop-owned operations over existing catalog and immutable artifact stores.

The catalog owns one current managed-record head. ContextArtifactStore owns
immutable revision bodies; predecessor references preserve history across CAS
updates. Neither Markdown exports nor this service create another store or
Run History authority. A failed CAS can leave an unreferenced artifact, never
a committed revision. All model-provided values are constrained by host policy.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator

from ..catalog.handshake import negotiate
from ..catalog.protocol import CatalogStore, PreconditionFailed, StoreError
from ..catalog.query import IntelligenceQuery
from ..loop.effect_approval import EffectApprovalService, EffectClass, EffectSpec
from ..loop.service_loop_envelope import ServiceLoopSpec, run_service_operation
from .context_artifacts import (
    ContextArtifactRef,
    ContextArtifactStore,
    ContextArtifactStoreSpec,
)
from .record_operations_records import (
    MUTATIONS,
    RecordOperationError,
    RecordOperationPolicy,
    RecordOperationRequest,
    canonical_json,
    content_digest,
    parse_json,
)
from .runtime_observer import RuntimeObservationServices


@dataclass(frozen=True)
class RecordStorageBinding:
    """Host-owned backend identity and lazy opener; never supplied by a model."""

    backend_locator: str
    artifact_root: str
    open_backend: Callable[[bool], CatalogStore] = field(repr=False, compare=False)
    effect_class: EffectClass = EffectClass.LOCAL_WRITE

    def __post_init__(self) -> None:
        if (not isinstance(self.backend_locator, str) or not self.backend_locator.strip()
                or not isinstance(self.artifact_root, str) or not self.artifact_root.strip()
                or not callable(self.open_backend)
                or self.effect_class not in (EffectClass.LOCAL_WRITE, EffectClass.NETWORK_WRITE)):
            raise RecordOperationError("invalid_storage_binding")
        root = Path(self.artifact_root).expanduser().absolute()
        if ".." in root.parts:
            raise RecordOperationError("invalid_artifact_root")
        object.__setattr__(self, "artifact_root", str(root))

    @property
    def locator_digest(self) -> str:
        return content_digest(self.backend_locator)

    @property
    def artifact_root_digest(self) -> str:
        return content_digest(self.artifact_root)


@dataclass(frozen=True)
class RecordOperationServices:
    """Existing operational dependencies resolved by a trusted host."""

    storage: RecordStorageBinding
    runtime: RuntimeObservationServices = field(default_factory=RuntimeObservationServices)
    approvals: EffectApprovalService | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.storage, RecordStorageBinding)
                or not isinstance(self.runtime, RuntimeObservationServices)
                or (self.approvals is not None
                    and not isinstance(self.approvals, EffectApprovalService))):
            raise RecordOperationError("typed_record_dependencies_required")


@dataclass(frozen=True)
class RecordOperationResult:
    """Scoped metadata, optional selected body, and honest commit disposition."""

    operation: str
    status: str
    records: tuple[dict, ...] = ()
    document_json: str = field(default="", repr=False)
    committed: bool | None = False
    effect_digest: str = ""
    orphan_artifact_ref: ContextArtifactRef | None = None
    potential_orphan_artifact_ref: ContextArtifactRef | None = None
    diagnostic_code: str = ""

    def to_dict(self) -> dict:
        value = {"record_type": "record_operation_result/v1", "operation": self.operation,
                 "status": self.status, "records": list(self.records),
                 "committed": self.committed, "effect_digest": self.effect_digest,
                 "grants_authority": False, "promotes_intelligence": False,
                 "diagnostic_code": self.diagnostic_code,
                 "orphan_artifact_ref": (self.orphan_artifact_ref.to_dict()
                                         if self.orphan_artifact_ref else None),
                 "potential_orphan_artifact_ref": (
                     self.potential_orphan_artifact_ref.to_dict()
                     if self.potential_orphan_artifact_ref else None)}
        if self.document_json:
            value["document"] = parse_json(self.document_json)
        return value


def effect_digest(effect: EffectSpec) -> str:
    return content_digest(effect.to_dict())


class RecordOperationService:
    """Managed generic records through canonical code-execution Loops."""

    def __init__(self, policy: RecordOperationPolicy, services: RecordOperationServices):
        if not isinstance(policy, RecordOperationPolicy) or not isinstance(services, RecordOperationServices):
            raise RecordOperationError("typed_record_service_required")
        if services.approvals is not None and services.approvals.runtime != services.runtime:
            raise RecordOperationError("approval_runtime_mismatch")
        self.policy = policy
        self.services = services

    def _validate_request(self, request: RecordOperationRequest) -> None:
        if not isinstance(request, RecordOperationRequest):
            raise RecordOperationError("typed_record_request_required")
        if request.operation not in self.policy.allowed_operations:
            raise RecordOperationError("operation_not_authorized_by_policy")
        if request.record_id and not request.record_id.startswith(self.policy.scope.record_id_prefix):
            raise RecordOperationError("record_id_outside_scope")
        if ((request.limit is not None and request.limit > self.policy.maximum_query_results)
                or request.maximum_history_depth > self.policy.maximum_history_depth):
            raise RecordOperationError("operation_limit_exceeds_policy")
        if not set(parse_json(request.filters_json)) <= set(self.policy.indexed_fields):
            raise RecordOperationError("query_field_not_indexed")
        if request.document_json:
            self._validate_document(parse_json(request.document_json))

    def _validate_document(self, document: object) -> None:
        body = canonical_json(document).encode("utf-8")
        if not isinstance(document, dict) or len(body) > self.policy.maximum_document_bytes:
            raise RecordOperationError("document_size_or_type_refused")
        validator = Draft202012Validator(parse_json(self.policy.document_schema_json))
        if not validator.is_valid(document):
            raise RecordOperationError("document_schema_failed")

    def effect_for(self, request: RecordOperationRequest) -> EffectSpec:
        """Plan an exact mutation without opening a backend or creating paths."""
        self._validate_request(request)
        if request.operation not in MUTATIONS:
            raise RecordOperationError("read_operation_needs_no_write_approval")
        binding = self.services.storage
        return EffectSpec(binding.effect_class, "managed_record_" + request.operation,
                          "catalog-record:" + request.record_id, tuple(sorted({
                              "policy_digest": self.policy.digest,
                              "request_digest": request.digest,
                              "backend_locator_digest": binding.locator_digest,
                              "artifact_root_digest": binding.artifact_root_digest,
                              "expected_record_version": request.expected_record_version,
                          }.items())))

    def execute(self, request: RecordOperationRequest, *, approval_id: str = "") -> RecordOperationResult:
        """Execute one read or exactly approved mutation, with one Loop owner."""
        self._validate_request(request)
        effects = ("reads_fs", "writes_fs") if request.operation in MUTATIONS else ("reads_fs",)
        return run_service_operation(self.services.runtime, ServiceLoopSpec(
            operation="managed_record_operation", profile_id="practitioner.code_execution",
            input_role="record_operation_request", output_role="record_operation_result",
            effects=effects, objective="perform one scoped catalog record operation",
            failure_kind="record_operation_failed"),
            lambda active: self._execute(request, approval_id, active))

    def _execute(self, request, approval_id, active):
        effect = self.effect_for(request) if request.operation in MUTATIONS else None
        if effect is not None:
            if not approval_id or self.services.approvals is None:
                raise RecordOperationError("record_write_approval_required")
            try:
                self.services.approvals.consume(approval_id, effect)
            except (KeyError, PermissionError, RuntimeError, ValueError):
                raise RecordOperationError("record_write_approval_unusable") from None
        try:
            store = self.services.storage.open_backend(effect is not None)
        except FileNotFoundError:
            if effect is not None:
                raise RecordOperationError("record_backend_unavailable") from None
            return RecordOperationResult(request.operation, "not_found")
        try:
            capabilities = store.capabilities()
            if capabilities.compatibility_verdict != "compatible":
                raise RecordOperationError("store_compatibility_not_established")
            operations = ("get", "write") if effect is not None else (
                "query",) if request.operation == "query" else ("get",)
            handshake = negotiate(capabilities, required_operations=operations,
                                  write_requested=effect is not None)
            if not all(handshake.permits(operation) for operation in operations):
                raise RecordOperationError("store_operation_unsupported")
            if effect is not None and (
                    capabilities.authority != "authoritative"
                    or not capabilities.transactions.get("atomic_preconditions")):
                raise RecordOperationError("atomic_authoritative_store_required")
            result = self._mutate(store, request, effect) if effect is not None else self._read(store, request)
            active.ledger.record(
                loop_id=active.loop_id, event="custom", action="managed_record_operation",
                operation=request.operation, status=result.status,
                policy_digest=self.policy.digest, request_digest=request.digest,
                effect_digest=result.effect_digest, committed=result.committed,
                returned_records=len(result.records))
            return result
        finally:
            store.close()

    def _in_scope(self, record: dict) -> bool:
        scope = self.policy.scope
        return (isinstance(record, dict)
                and record.get("namespace") == scope.namespace
                and record.get("source_collection") == scope.source_collection
                and record.get("intelligence_layer") == scope.intelligence_layer
                and record.get("artifact_kind") == scope.artifact_kind
                and str(record.get("record_id", "")).startswith(scope.record_id_prefix)
                and record.get("lifecycle") in ("candidate", "retired"))

    def _managed(self, record: dict) -> bool:
        payload = record.get("payload") or {}
        return (self._in_scope(record) and isinstance(payload, dict)
                and payload.get("record_type") == "managed_record_head/v1"
                and payload.get("policy_digest") == self.policy.digest)

    def _card(self, record: dict) -> dict:
        payload = record.get("payload") or {}
        managed = self._managed(record)
        return {"record_id": record["record_id"], "record_version": record.get("record_version"),
                "namespace": record.get("namespace"), "artifact_kind": record.get("artifact_kind"),
                "lifecycle": record.get("lifecycle"), "managed": managed,
                "revision_ref": payload.get("revision_ref") if managed else None}

    def _artifact_store(self, *, write: bool) -> ContextArtifactStore:
        root = Path(self.services.storage.artifact_root)
        objects = root / "managed_records" / "objects"
        current = Path(objects.anchor)
        for part in objects.parts[1:]:
            current /= part
            if current.is_symlink():
                raise RecordOperationError("artifact_root_symlink_refused")
        if not write and not objects.is_dir():
            raise RecordOperationError("revision_artifact_unavailable")
        return ContextArtifactStore(ContextArtifactStoreSpec(str(root), "managed_records"))

    def _artifact_path_safe(self, digest: str) -> None:
        objects = Path(self.services.storage.artifact_root) / "managed_records" / "objects"
        if (objects / digest[:2]).is_symlink() or (objects / digest[:2] / digest).is_symlink():
            raise RecordOperationError("revision_artifact_symlink_refused")

    def _revision(self, reference: dict, record_id: str, version: str) -> dict:
        try:
            ref = ContextArtifactRef.from_dict(reference)
            if ref.byte_count > self.policy.maximum_document_bytes + 8192:
                raise RecordOperationError("revision_size_refused")
            self._artifact_path_safe(ref.digest)
            value = parse_json(self._artifact_store(write=False).get(ref).decode("utf-8"))
        except (KeyError, TypeError, OSError, RuntimeError, UnicodeError):
            raise RecordOperationError("revision_artifact_invalid") from None
        expected = {"record_type", "record_id", "record_version", "policy_digest",
                    "scope", "document_schema_digest", "document_digest", "document",
                    "previous", "retired"}
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type") != "managed_record_revision/v1"
                or value.get("record_id") != record_id or value.get("record_version") != version
                or value.get("scope") != self.policy.scope.to_dict()
                or value.get("policy_digest") != self.policy.digest
                or value.get("document_schema_digest") != self.policy.schema_digest
                or value.get("document_digest") != content_digest(value.get("document"))
                or type(value.get("retired")) is not bool):
            raise RecordOperationError("revision_contract_invalid")
        self._validate_document(value["document"])
        previous = value["previous"]
        if (not isinstance(version, str) or not version.isascii() or not version.isdigit()
                or not 1 <= int(version) <= 999_999_999_999):
            raise RecordOperationError("revision_number_invalid")
        if version == "1":
            if previous is not None:
                raise RecordOperationError("revision_predecessor_invalid")
        elif (not isinstance(previous, dict) or set(previous) != {"record_version", "revision_ref"}
              or previous.get("record_version") != str(int(version) - 1)):
            raise RecordOperationError("revision_predecessor_invalid")
        return value

    def _read(self, store, request):
        if request.operation == "query":
            scope = self.policy.scope
            limit = self.policy.maximum_query_results if request.limit is None else request.limit
            query = IntelligenceQuery(
                layers=(scope.intelligence_layer,), source_collections=(scope.source_collection,),
                artifact_kinds=(scope.artifact_kind,), lifecycle=("candidate", "retired"),
                namespaces=(scope.namespace,),
                attributes={key: {"equals": value} for key, value in parse_json(request.filters_json).items()},
                limit=limit)
            rows = store.query(query)
            # Defense in depth: backend filtering never expands caller scope.
            selected = [row for row in rows if self._in_scope(row) and query.matches(row)]
            return RecordOperationResult("query", "found" if selected else "not_found",
                                         tuple(self._card(row) for row in selected[:limit]))
        record = store.get(request.record_id)
        if record is None or not self._in_scope(record):
            return RecordOperationResult("get", "not_found")
        if not self._managed(record):
            return RecordOperationResult("get", "unmanaged", (self._card(record),))
        version = record["record_version"]
        reference = record["payload"]["revision_ref"]
        for _hop in range(request.maximum_history_depth):
            revision = self._revision(reference, request.record_id, version)
            if not request.record_version or version == request.record_version:
                card = {**self._card(record), "record_version": version,
                        "lifecycle": "retired" if revision["retired"] else "candidate",
                        "revision_ref": reference, "previous": revision["previous"]}
                return RecordOperationResult("get", "retired" if revision["retired"] else "found",
                    (card,), canonical_json(revision["document"]) if request.materialize else "")
            previous = revision["previous"]
            if previous is None:
                return RecordOperationResult("get", "not_found")
            if (not isinstance(previous, dict) or set(previous) != {"record_version", "revision_ref"}
                    or str(int(version) - 1) != previous.get("record_version")):
                raise RecordOperationError("revision_predecessor_invalid")
            version, reference = previous["record_version"], previous["revision_ref"]
        raise RecordOperationError("history_depth_exhausted")

    def _mutate(self, store, request, effect):
        current = store.get(request.record_id)
        previous = None
        if request.operation == "create":
            if current is not None:
                return RecordOperationResult(request.operation, "conflict", effect_digest=effect_digest(effect))
            version, precondition = "1", {"exists": False}
            document = parse_json(request.document_json)
        else:
            if current is None or not self._managed(current):
                return RecordOperationResult(request.operation, "not_found", effect_digest=effect_digest(effect))
            if (current.get("record_version") != request.expected_record_version
                    or current.get("lifecycle") == "retired"):
                return RecordOperationResult(request.operation, "conflict", effect_digest=effect_digest(effect))
            prior = self._revision(current["payload"]["revision_ref"], request.record_id,
                                   request.expected_record_version)
            version = str(int(request.expected_record_version) + 1)
            if int(version) > 999_999_999_999:
                raise RecordOperationError("revision_number_exhausted")
            precondition = {"record_version": request.expected_record_version}
            previous = {"record_version": request.expected_record_version,
                        "revision_ref": current["payload"]["revision_ref"]}
            document = prior["document"] if request.operation == "retire" else parse_json(request.document_json)
        retired = request.operation == "retire"
        revision = {"record_type": "managed_record_revision/v1", "record_id": request.record_id,
                    "record_version": version, "policy_digest": self.policy.digest,
                    "scope": self.policy.scope.to_dict(), "document_schema_digest": self.policy.schema_digest,
                    "document": document, "document_digest": content_digest(document),
                    "previous": previous, "retired": retired}
        encoded = canonical_json(revision)
        self._artifact_path_safe(hashlib.sha256(encoded.encode("utf-8")).hexdigest())
        ref = self._artifact_store(write=True).put_text(
            encoded, media_type="application/json", artifact_kind="managed_record_revision")
        scope = self.policy.scope
        record = {"record_id": request.record_id, "record_version": version,
                  "namespace": scope.namespace, "source_collection": scope.source_collection,
                  "intelligence_layer": scope.intelligence_layer, "artifact_kind": scope.artifact_kind,
                  "lifecycle": "retired" if retired else "candidate",
                  "attributes": {key: document[key] for key in self.policy.indexed_fields if key in document},
                  "payload": {"record_type": "managed_record_head/v1", "policy_digest": self.policy.digest,
                              "revision_ref": ref.to_dict()}}
        try:
            write_confirmation = store.put(record, precondition=precondition)
        except PreconditionFailed:
            return RecordOperationResult(request.operation, "conflict", effect_digest=effect_digest(effect),
                                         orphan_artifact_ref=ref)
        except StoreError:
            return RecordOperationResult(
                request.operation, "commit_unknown", committed=None,
                effect_digest=effect_digest(effect), potential_orphan_artifact_ref=ref,
                diagnostic_code="backend_write_unconfirmed")
        if (not isinstance(write_confirmation, dict) or write_confirmation.get("stored") is not True
                or write_confirmation.get("record_id") != request.record_id):
            return RecordOperationResult(
                request.operation, "commit_unknown", committed=None,
                effect_digest=effect_digest(effect), potential_orphan_artifact_ref=ref,
                diagnostic_code="record_write_confirmation_invalid")
        if not self._write_confirmed(store, record, request.maximum_history_depth):
            return RecordOperationResult(
                request.operation, "commit_unknown", committed=None,
                effect_digest=effect_digest(effect), potential_orphan_artifact_ref=ref,
                diagnostic_code="record_write_readback_unconfirmed")
        return RecordOperationResult(request.operation, "retired" if retired else "stored",
                                     (self._card(record),), committed=True,
                                     effect_digest=effect_digest(effect))

    def _write_confirmed(self, store, expected: dict, maximum_depth: int) -> bool:
        """Confirm exact head or a newer valid chain containing our revision."""
        try:
            current = store.get(expected["record_id"])
            if current == expected:
                self._revision(expected["payload"]["revision_ref"], expected["record_id"],
                               expected["record_version"])
                return True
            if not current or not self._managed(current):
                return False
            version = current["record_version"]
            if int(version) <= int(expected["record_version"]):
                return False
            reference = current["payload"]["revision_ref"]
            for _hop in range(min(maximum_depth, self.policy.maximum_history_depth)):
                revision = self._revision(reference, expected["record_id"], version)
                if version == expected["record_version"]:
                    return reference == expected["payload"]["revision_ref"]
                previous = revision["previous"]
                if previous is None:
                    return False
                version, reference = previous["record_version"], previous["revision_ref"]
            return False
        except (OSError, RuntimeError, ValueError, TypeError, KeyError):
            return False


__all__ = (
    "RecordOperationResult",
    "RecordOperationService",
    "RecordOperationServices",
    "RecordStorageBinding",
    "effect_digest",
)
