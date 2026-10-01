"""Private work reports over managed records and the existing service store.

Reports and UTF-8 attachments are inert submitted data. The managed-record
owner keeps immutable bodies; this adapter adds authentication guards to its
atomic head write. Nothing here runs code, fetches links or admits material.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re

from ...catalog.protocol import CatalogRecordPrecondition, StoreError
from ..record_operations import RecordOperationService, RecordOperationServices, RecordStorageBinding
from ..record_operations_records import (RecordOperationPolicy, RecordOperationRequest, RecordScope,
                                        canonical_json, parse_json)
from ..runtime_observer import RuntimeObservationServices
from ...loop.effect_approval import ApprovalDecision, ApprovalRequest, EffectApprovalService
from . import dot_pages
from .http_auth import validate_reference_url
from .records import ServiceCommitUnknown, ServiceRuntimeError, digest, identifier

PATH = "/api/v1/admin/work"
REQUEST_VERSION, RESULT_VERSION = "service_staff_work_request/v1", "service_staff_work_result/v1"
DOCUMENT_VERSION = "service_staff_work_document/v1"
PREFIX = "staff-work:"
KINDS = ("research", "test_result", "component", "review", "blocker")
MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES, MAX_MESSAGE = 16, 65536, 262144, 16000
LIST_LIMIT = 100
FIELDS = frozenset({"request_id", "brief", "brief_revision", "task_id", "kind", "title", "message", "links", "files", "reply_to"})
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _text(value, limit, *, empty=False):
    if (not isinstance(value, str) or len(value) > limit or (not empty and not value.strip())
            or any(ord(c) < 32 and c not in "\n\r\t" for c in value)):
        raise ServiceRuntimeError("invalid_work_text")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ServiceRuntimeError("invalid_work_text") from None
    return value


def request_schema():
    text = {"type": "string"}
    return {"type": "object", "additionalProperties": False, "required": sorted(FIELDS), "properties": {
        "request_id": {**text, "maxLength": 128}, "brief": {"enum": ["context", "feedback"]},
        "brief_revision": {**text, "pattern": "^[a-f0-9]{64}$"}, "task_id": {**text, "maxLength": 128},
        "kind": {"enum": list(KINDS)}, "title": {**text, "minLength": 1, "maxLength": 160},
        "message": {**text, "minLength": 1, "maxLength": MAX_MESSAGE},
        "reply_to": {**text, "maxLength": 80},
        "links": {"type": "array", "maxItems": 10, "items": {**text, "maxLength": 2048}},
        "files": {"type": "array", "maxItems": MAX_FILES, "items": {"type": "object",
            "additionalProperties": False, "required": ["name", "content"],
            "properties": {"name": {**text, "maxLength": 160}, "content": {**text, "maxLength": MAX_FILE_BYTES}}}}}}


def read_schema():
    return {"type": "object", "additionalProperties": False,
            "properties": {key: {"type": "string"} for key in ("id", "day", "task_id")}}


def _fields(value):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ServiceRuntimeError("invalid_request")
    identifier(value["request_id"], "request identity")
    identifier(value["task_id"], "task identity")
    if (value["brief"] not in ("context", "feedback") or value["kind"] not in KINDS
            or not isinstance(value["brief_revision"], str) or not SHA.fullmatch(value["brief_revision"])):
        raise ServiceRuntimeError("invalid_work_reference")
    _text(value["title"], 160); _text(value["message"], MAX_MESSAGE)
    parent = _text(value["reply_to"], 80, empty=True)
    if parent and (not parent.startswith(PREFIX) or not SHA.fullmatch(parent[len(PREFIX):])):
        raise ServiceRuntimeError("invalid_work_reference")
    links, files = value["links"], value["files"]
    if not isinstance(links, list) or len(links) > 10 or not isinstance(files, list) or len(files) > MAX_FILES:
        raise ServiceRuntimeError("work_submission_limit")
    for link in links:
        _text(link, 2048)
        try:
            if any(c.isspace() for c in link) or "\\" in link:
                raise ValueError()
            # Reuse the existing pure URL validator. A source fragment is
            # retained as metadata; no address is fetched by this adapter.
            validate_reference_url(link)
        except ValueError:
            raise ServiceRuntimeError("invalid_work_link") from None
    checked, names, total = [], set(), 0
    for file in files:
        if not isinstance(file, dict) or set(file) != {"name", "content"}:
            raise ServiceRuntimeError("invalid_work_file")
        name = _text(file["name"], 160)
        path = PurePosixPath(name)
        if (name in names or name == "." or name != str(path) or path.is_absolute() or ".." in path.parts
                or "\\" in name or ":" in name or any(c.isspace() and c != " " for c in name)):
            raise ServiceRuntimeError("invalid_work_file")
        names.add(name)
        content = _text(file["content"], MAX_FILE_BYTES, empty=True)
        data = content.encode("utf-8"); total += len(data)
        if len(data) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ServiceRuntimeError("work_submission_limit")
        checked.append({"name": name, "content": content, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    return {**value, "links": list(links), "files": checked}


def _brief(fields):
    record = dot_pages.load_record(fields["brief"])
    if (dot_pages.revision(record) != fields["brief_revision"]
            or fields["task_id"] not in {row["id"] for row in record["tasks"]}):
        raise ServiceRuntimeError("work_brief_changed")


class _AuthorizedCatalog:
    """The existing CatalogStore with staff read-set guards on its head write."""

    def __init__(self, catalog, authorize, write, before_write=None):
        self.catalog, self.authorize, self.before_write = catalog, authorize, before_write
        self.context = catalog.store(write=write)
        self.store = self.context.__enter__()
        try:
            authorize(self.store)
            if write and before_write is not None:
                before_write()
        except BaseException:
            self.close()
            raise

    def capabilities(self):
        return self.store.capabilities()

    def get(self, *args, **kwargs):
        return self.store.get(*args, **kwargs)

    def query(self, value):
        return self.store.query(value)

    def put(self, record, *, precondition=None):
        guards = self.authorize(self.store)
        if self.before_write is not None:
            self.before_write()
        if precondition != {"exists": False}:
            raise StoreError("work_log_is_append_only")
        try:
            self.catalog.commit(self.store, (record,), (*guards,
                CatalogRecordPrecondition(record["record_id"], must_not_exist=True)))
        except ServiceCommitUnknown:
            raise StoreError("work_commit_unconfirmed") from None
        return {"stored": True, "record_id": record["record_id"]}

    def close(self):
        self.context.__exit__(None, None, None)


def _service(runtime, authorize, *, before_write=None):
    # Paths and scope come from the installed host, never submitted fields.
    database = Path(runtime.config.database_path).absolute()
    binding = RecordStorageBinding(str(database), str(database.parent / "staff-work-revisions"),
        lambda write: _AuthorizedCatalog(runtime._catalog, authorize, write, before_write))
    schema = {"type": "object", "additionalProperties": False,
              "required": sorted(FIELDS | {"record_type", "actor", "submitted_at", "day", "request_digest"}),
              "properties": {**request_schema()["properties"],
                  "record_type": {"const": DOCUMENT_VERSION}, "actor": {"type": "string"},
                  "submitted_at": {"type": "number"}, "day": {"type": "string"},
                  "request_digest": {"type": "string"}}}
    schema["properties"]["files"] = {"type": "array", "maxItems": MAX_FILES, "items": {
        "type": "object", "additionalProperties": False, "required": ["name", "content", "bytes", "sha256"],
        "properties": {"name": {"type": "string"}, "content": {"type": "string"},
                       "bytes": {"type": "integer", "minimum": 0}, "sha256": {"type": "string"}}}}
    policy = RecordOperationPolicy("staff_work/v1", RecordScope(runtime.config.namespace,
        "staff_work", "user_feedback_intelligence", "intelligence_record", PREFIX), canonical_json(schema),
        allowed_operations=("create", "get", "query"), indexed_fields=("day", "task_id", "kind", "reply_to"),
        # Reserve room for server-owned metadata beyond the bounded wire body.
        maximum_document_bytes=1048576, maximum_query_results=LIST_LIMIT+1)
    observations = RuntimeObservationServices()
    approvals = EffectApprovalService(runtime=observations)
    return RecordOperationService(policy, RecordOperationServices(binding, observations, approvals))


def submit(runtime, authorize, actor, fields):
    fields = _fields(fields)
    service = _service(runtime, authorize, before_write=lambda: _brief(fields))
    record_id = PREFIX + digest([runtime.config.namespace, actor, fields["request_id"]])
    content = digest(fields)
    held = service.execute(RecordOperationRequest("get", record_id, materialize=True)).to_dict()
    if held["status"] == "found":
        if held["document"]["request_digest"] != content:
            raise ServiceRuntimeError("work_request_identity_conflict")
        return {"record_type": RESULT_VERSION, "committed": True, "repeated": True, "id": record_id,
                "record_version": held["records"][0]["record_version"], "promotes_intelligence": False}
    if held["status"] != "not_found":
        raise ServiceRuntimeError("work_record_unavailable")
    _brief(fields)
    if fields["reply_to"]:
        parent = service.execute(RecordOperationRequest("get", fields["reply_to"], materialize=True)).to_dict()
        if (parent["status"] != "found" or parent["document"]["task_id"] != fields["task_id"]
                or parent["document"]["brief"] != fields["brief"]):
            raise ServiceRuntimeError("work_reply_target_invalid")
    moment = runtime._now()
    document = {**fields, "record_type": DOCUMENT_VERSION, "actor": actor,
                "submitted_at": moment, "day": datetime.fromtimestamp(moment, timezone.utc).date().isoformat(),
                "request_digest": content}
    requested = RecordOperationRequest("create", record_id, document_json=canonical_json(document))
    effect = service.effect_for(requested)
    approval = ApprovalRequest.create("authenticated_staff_work", effect,
        "Authenticated staff explicitly submitted this exact bounded work report", requested_by="staff_work_http")
    checkpoint = service.services.approvals.create(approval)
    service.services.approvals.resume(checkpoint.pending, checkpoint.resume_token,
                                    ApprovalDecision.approve(approval.request_id, "authenticated_staff"))
    outcome = service.execute(requested, approval_id=approval.request_id)
    # Commitment is the typed effect disposition; a status label alone is
    # not evidence that the write committed.
    if outcome.committed is None:
        raise ServiceCommitUnknown()
    if outcome.committed is not True:
        raise ServiceRuntimeError("concurrent_update")
    if (outcome.operation != requested.operation or len(outcome.records) != 1
            or outcome.records[0]["record_id"] != record_id):
        raise ServiceCommitUnknown()
    return {"record_type": RESULT_VERSION, "committed": True, "repeated": False, "id": record_id,
            "record_version": outcome.records[0]["record_version"], "promotes_intelligence": False}


def read(runtime, authorize, fields):
    if not isinstance(fields, dict) or set(fields) - {"id", "day", "task_id"}:
        raise ServiceRuntimeError("invalid_request")
    service = _service(runtime, authorize)
    if "id" in fields:
        if set(fields) != {"id"} or not isinstance(fields["id"], str) or not fields["id"].startswith(PREFIX) or not SHA.fullmatch(fields["id"][len(PREFIX):]):
            raise ServiceRuntimeError("invalid_work_reference")
        value = service.execute(RecordOperationRequest("get", fields["id"], materialize=True)).to_dict()
        if value["status"] != "found":
            raise ServiceRuntimeError("work_record_unavailable")
        return {"record_type": RESULT_VERSION, "id": fields["id"], "document": value["document"],
                "record_version": value["records"][0]["record_version"], "promotes_intelligence": False}
    day = fields.get("day", datetime.fromtimestamp(runtime._now(), timezone.utc).date().isoformat())
    try:
        if not isinstance(day, str) or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
            raise ValueError()
    except ValueError:
        raise ServiceRuntimeError("invalid_work_day") from None
    filters = {"day": day}
    if "task_id" in fields:
        filters["task_id"] = identifier(fields["task_id"], "task identity")
    records = service.execute(RecordOperationRequest("query", filters_json=canonical_json(filters), limit=LIST_LIMIT+1)).records
    items = []
    for row in records[:LIST_LIMIT]:
        value = service.execute(RecordOperationRequest("get", row["record_id"], materialize=True)).to_dict()
        if value["status"] != "found":
            raise ServiceRuntimeError("work_record_unavailable")
        doc = value["document"]
        items.append({"id": row["record_id"], "record_version": row["record_version"],
                      **{k: doc[k] for k in ("title", "task_id", "brief", "kind", "day", "submitted_at", "reply_to")},
                      "file_count": len(doc["files"])})
    items.sort(key=lambda item: (item["submitted_at"], item["id"]), reverse=True)
    return {"record_type": RESULT_VERSION, "day": day, "items": items,
            "complete": len(records) <= LIST_LIMIT, "limit": LIST_LIMIT, "promotes_intelligence": False}
