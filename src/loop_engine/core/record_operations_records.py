"""Passive contracts for scoped generic report and note operations.

Host policy owns classification, schema, and limits. Untrusted requests own
document values, never backend paths, SQL, lifecycle promotion, or authority.
Revision numbers are positive integer strings; schema versions are separate.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ..ontology.artifacts import ARTIFACT_KINDS
from .intelligence_layers import LAYERS

OPERATIONS = ("create", "get", "query", "update", "retire")
MUTATIONS = ("create", "update", "retire")
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9._:-]{0,159}$")
_VERSION = re.compile(r"^[1-9][0-9]{0,11}$")


class RecordOperationError(ValueError):
    """A fixed, content-free record operation failure."""


def canonical_json(value: object) -> str:
    """Serialize finite JSON deterministically; this is not an RFC 8785 claim."""
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
        text.encode("utf-8")
        return text
    except (ValueError, TypeError, UnicodeError) as exc:
        raise RecordOperationError("invalid_json_value") from exc


def content_digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecordOperationError("duplicate_json_key")
        result[key] = value
    return result


def parse_json(text: str) -> object:
    try:
        value = json.loads(text, object_pairs_hook=_pairs)
        canonical_json(value)
        return value
    except (ValueError, TypeError, UnicodeError) as exc:
        raise RecordOperationError("invalid_json") from exc


def _text(value: object) -> str:
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > 160 or "\n" in value or "\r" in value):
        raise RecordOperationError("invalid_policy_text")
    return value


def _bounded_integer(value: object, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise RecordOperationError("invalid_operation_limit")
    return value


def _local_schema(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("$ref", "$dynamicRef") and (
                    not isinstance(item, str) or not item.startswith("#")):
                raise RecordOperationError("external_schema_reference_refused")
            _local_schema(item)
    elif isinstance(value, list):
        for item in value:
            _local_schema(item)


@dataclass(frozen=True)
class RecordScope:
    """Exact classification granted by host configuration, not model output."""

    namespace: str
    source_collection: str
    intelligence_layer: str
    artifact_kind: str
    record_id_prefix: str

    def __post_init__(self) -> None:
        for value in (self.namespace, self.source_collection,
                      self.record_id_prefix):
            _text(value)
        if (self.intelligence_layer not in LAYERS
                or self.artifact_kind not in ARTIFACT_KINDS
                or not _IDENTIFIER.fullmatch(self.record_id_prefix)):
            raise RecordOperationError("invalid_record_scope")

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class RecordOperationPolicy:
    """Frozen schema and scope for one host-configured managed collection."""

    policy_id: str
    scope: RecordScope
    document_schema_json: str = field(repr=False)
    allowed_operations: tuple[str, ...] = OPERATIONS
    indexed_fields: tuple[str, ...] = ()
    maximum_document_bytes: int = 65_536
    maximum_query_results: int = 100
    maximum_history_depth: int = 100

    def __post_init__(self) -> None:
        _text(self.policy_id)
        if not isinstance(self.scope, RecordScope):
            raise RecordOperationError("typed_record_scope_required")
        schema = parse_json(self.document_schema_json)
        if not isinstance(schema, dict):
            raise RecordOperationError("object_schema_required")
        _local_schema(schema)
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError:
            raise RecordOperationError("invalid_document_schema") from None
        object.__setattr__(self, "document_schema_json", canonical_json(schema))
        operations = tuple(self.allowed_operations)
        if (not operations or len(set(operations)) != len(operations)
                or not set(operations) <= set(OPERATIONS)):
            raise RecordOperationError("invalid_allowed_operations")
        fields = tuple(self.indexed_fields)
        if (len(set(fields)) != len(fields) or len(fields) > 20
                or any(not _IDENTIFIER.fullmatch(item)
                       or item.startswith("__") for item in fields)):
            raise RecordOperationError("invalid_indexed_fields")
        object.__setattr__(self, "allowed_operations", operations)
        object.__setattr__(self, "indexed_fields", fields)
        _bounded_integer(self.maximum_document_bytes, 1_048_576)
        _bounded_integer(self.maximum_query_results, 1_000)
        _bounded_integer(self.maximum_history_depth, 1_000)

    @property
    def schema_digest(self) -> str:
        return content_digest(parse_json(self.document_schema_json))

    @property
    def digest(self) -> str:
        return content_digest(self.to_dict())

    def to_dict(self) -> dict:
        return {"record_type": "record_operation_policy/v1",
                "policy_id": self.policy_id, "scope": self.scope.to_dict(),
                "document_schema": parse_json(self.document_schema_json),
                "allowed_operations": list(self.allowed_operations),
                "indexed_fields": list(self.indexed_fields),
                "maximum_document_bytes": self.maximum_document_bytes,
                "maximum_query_results": self.maximum_query_results,
                "maximum_history_depth": self.maximum_history_depth}

    @classmethod
    def from_mapping(cls, value: dict) -> RecordOperationPolicy:
        allowed = {"record_type", "policy_id", "scope", "document_schema",
                   "allowed_operations", "indexed_fields", "maximum_document_bytes",
                   "maximum_query_results", "maximum_history_depth"}
        if (not isinstance(value, dict) or set(value) - allowed
                or value.get("record_type") != "record_operation_policy/v1"):
            raise RecordOperationError("invalid_policy_record")
        try:
            options = {key: value[key] for key in allowed - {
                "record_type", "policy_id", "scope", "document_schema"} if key in value}
            return cls(value["policy_id"], RecordScope(**value["scope"]),
                       canonical_json(value["document_schema"]), **options)
        except (KeyError, TypeError):
            raise RecordOperationError("invalid_policy_record") from None


@dataclass(frozen=True)
class RecordOperationRequest:
    """One content request without SQL, backend paths, or authority fields."""

    operation: str
    record_id: str = ""
    expected_record_version: str = ""
    record_version: str = ""
    document_json: str = field(default="", repr=False)
    filters_json: str = field(default="{}", repr=False)
    limit: int | None = None
    maximum_history_depth: int = 20
    materialize: bool = False

    def __post_init__(self) -> None:
        if self.operation not in OPERATIONS:
            raise RecordOperationError("unsupported_record_operation")
        if self.operation != "query" and not _IDENTIFIER.fullmatch(self.record_id):
            raise RecordOperationError("invalid_record_id")
        if self.operation == "query" and self.record_id:
            raise RecordOperationError("query_record_id_not_permitted")
        if self.operation in ("update", "retire"):
            if not _VERSION.fullmatch(self.expected_record_version):
                raise RecordOperationError("expected_record_version_required")
        elif self.expected_record_version:
            raise RecordOperationError("unexpected_record_precondition")
        if self.record_version and (self.operation != "get"
                                    or not _VERSION.fullmatch(self.record_version)):
            raise RecordOperationError("invalid_requested_revision")
        if self.operation in ("create", "update"):
            if not isinstance(parse_json(self.document_json), dict):
                raise RecordOperationError("document_must_be_object")
        elif self.document_json:
            raise RecordOperationError("unexpected_document")
        filters = parse_json(self.filters_json)
        if not isinstance(filters, dict) or (filters and self.operation != "query"):
            raise RecordOperationError("invalid_query_filters")
        object.__setattr__(self, "filters_json", canonical_json(filters))
        if self.document_json:
            object.__setattr__(self, "document_json",
                               canonical_json(parse_json(self.document_json)))
        if self.limit is not None:
            _bounded_integer(self.limit, 1_000)
        _bounded_integer(self.maximum_history_depth, 1_000)
        if type(self.materialize) is not bool or (self.materialize and self.operation != "get"):
            raise RecordOperationError("invalid_materialization_request")

    def to_dict(self) -> dict:
        value = {"record_type": "record_operation_request/v1", "operation": self.operation,
                 "record_id": self.record_id, "expected_record_version": self.expected_record_version,
                 "record_version": self.record_version, "filters": parse_json(self.filters_json),
                 "limit": self.limit, "maximum_history_depth": self.maximum_history_depth,
                 "materialize": self.materialize}
        if self.document_json:
            value["document"] = parse_json(self.document_json)
        return value

    @property
    def digest(self) -> str:
        return content_digest(self.to_dict())

    @classmethod
    def from_mapping(cls, value: dict) -> RecordOperationRequest:
        allowed = {"record_type", "operation", "record_id", "expected_record_version",
                   "record_version", "document", "filters", "limit",
                   "maximum_history_depth", "materialize"}
        if (not isinstance(value, dict) or set(value) - allowed
                or value.get("record_type") != "record_operation_request/v1"):
            raise RecordOperationError("invalid_record_request")
        options = {key: item for key, item in value.items()
                   if key not in ("record_type", "document", "filters")}
        if "document" in value:
            options["document_json"] = canonical_json(value["document"])
        if "filters" in value:
            options["filters_json"] = canonical_json(value["filters"])
        try:
            return cls(**options)
        except TypeError:
            raise RecordOperationError("invalid_record_request") from None
