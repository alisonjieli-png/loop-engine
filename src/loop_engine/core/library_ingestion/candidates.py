"""The fixed edge of the library ingestion source slot, as versioned records.

A source engine is asked with library_candidate_request/v1 and answers with
library_candidate_batch/v1, which carries library_source_candidate/v1 items,
library_candidate_refusal/v1 rows with a reason from a closed vocabulary,
whether the source was read completely and the cursor to continue from.
library_candidate_outline/v1 is what a source without a permissive licence
leaves behind: the abstract purpose and the source identity, never the text.

Every engine behind the slot returns exactly these records, so a new engine
changes no neighbour. Readers refuse another version, an unknown field, a
missing field and a candidate without provenance. No record here approves,
stages or serves an item, and none grants network, file or model authority.
"""
from __future__ import annotations

from .provenance import OUTLINE_ONLY, read_outside_provenance, require_provenance
from .record_rules import (
    LibraryRecordError, canonical_digest, count, digest_value, flag, identifier, member,
    optional_text, read_part, read_record, relative_path, sequence, text_value, utc_time)

SOURCE_CANDIDATE_RECORD_TYPE = "library_source_candidate/v1"
REFUSAL_RECORD_TYPE = "library_candidate_refusal/v1"
OUTLINE_RECORD_TYPE = "library_candidate_outline/v1"
REQUEST_RECORD_TYPE = "library_candidate_request/v1"
BATCH_RECORD_TYPE = "library_candidate_batch/v1"
#: Changing how bytes are normalized changes every candidate key, on purpose.
NORMALIZER_VERSION = "library_normalizer/v1"

SKILL, INSTRUCTION_FILE, TOOL = "skill", "instruction_file", "tool"
KINDS = (SKILL, INSTRUCTION_FILE, TOOL)
NATIVE_FORMATS = ("agent_skill", "copilot_instructions", "cursor_rules", "mcp_server_entry")
STAGES = ("discovery", "fetch", "licence", "format", "size", "safety", "render", "registry",
          "outline", "staging")
#: Every reason a candidate can be refused, by stage. A reason outside this
#: vocabulary is refused by the reader, so a count by reason is always complete.
REASONS = {
    "discovery": ("symlink_not_imported", "submodule_not_imported", "tree_truncated",
                  "source_revision_unreadable", "curated_licence_changed"),
    "fetch": ("source_file_too_large", "blob_identity_mismatch", "fetch_failed", "not_utf8_text",
              "request_ceiling_reached"),
    "licence": ("licence_outline_only", "licence_refused", "copy_of_restricted_source"),
    "format": ("frontmatter_missing", "frontmatter_invalid", "name_invalid", "description_missing",
               "description_too_long", "compatibility_too_long", "reference_validator_refused",
               "body_too_short", "bundled_files_not_supported_yet", "connection_schema_refused",
               "instruction_frontmatter_invalid"),
    "size": ("body_exceeds_staging_limit",),
    "safety": ("safety_scan_blocked",),
    "render": ("render_failed",),
    "registry": ("registry_status_not_active", "registry_entry_not_latest", "remote_endpoint_not_https",
                 "credential_shaped_value_in_entry", "package_type_not_rendered",
                 "required_arguments_not_rendered", "url_template_not_rendered",
                 "package_does_not_resolve", "upstream_repository_unreadable", "no_transport_rendered",
                 "server_name_unusable", "entry_unreadable", "excluded_by_declaration"),
    "outline": ("licence_prohibits_derivatives", "outline_would_copy_source_text",
                "outline_generation_failed"),
    "staging": ("candidate_changed_since_staging",),
}
STOP_REASONS = ("complete", "request_ceiling", "rate_limit_pause_exceeds_bound", "candidate_ceiling",
                "source_refused")

CANDIDATE_FIELDS = ("candidate_key", "kind", "native_format", "name", "provenance", "package_scope",
                    "package_paths")
REFUSAL_FIELDS = ("stage", "reason", "detail", "source_ref", "candidate_key")
SOURCE_REF_FIELDS = ("origin", "repository", "immutable_revision", "path")
OUTLINE_FIELDS = ("outline_key", "kind", "native_format", "source_name", "topic_words",
                  "abstract_purpose", "provenance", "generator", "text_included", "model_calls")
GENERATOR_FIELDS = ("engine_id", "engine_version")
REQUEST_FIELDS = ("source_id", "cursor", "maximum_candidates", "maximum_requests",
                  "network_reads_authorized", "requested_at")
BATCH_FIELDS = ("request_digest", "source_id", "engine_id", "engine_version", "complete",
                "next_cursor", "stopped_reason", "candidates", "refusals", "requests_made")


def candidate_key(provenance) -> str:
    """Stable key from origin, revision, path, source digest and the normalizer version."""
    record = provenance.to_record()
    return canonical_digest({"origin": record["origin"], "repository": record["repository"],
                             "immutable_revision": record["immutable_revision"],
                             "path": record["path"], "source_digest": record["source_digest"],
                             "normalizer": NORMALIZER_VERSION})


def source_candidate(kind: str, native_format: str, name: str, provenance,
                     package_scope: str = "", package_paths=()) -> dict:
    """Build a candidate record; the reader runs on it before it is returned."""
    record = {"record_type": SOURCE_CANDIDATE_RECORD_TYPE, "candidate_key": candidate_key(provenance),
              "kind": kind, "native_format": native_format, "name": name,
              "provenance": provenance.to_record(), "package_scope": package_scope,
              "package_paths": sorted(package_paths)}
    read_source_candidate(record)
    return record


def read_source_candidate(value) -> dict:
    record = read_record(value, SOURCE_CANDIDATE_RECORD_TYPE, CANDIDATE_FIELDS)
    provenance = require_provenance(record)[0]
    if digest_value(record["candidate_key"], "candidate_key") != candidate_key(provenance):
        raise LibraryRecordError("candidate_key_mismatch", "the key must follow the provenance it names")
    member(record["kind"], "kind", KINDS)
    member(record["native_format"], "native_format", NATIVE_FORMATS)
    text_value(record["name"], "name", limit=160)
    if record["package_scope"]:
        relative_path(record["package_scope"], "package_scope")
    sequence(record["package_paths"], "package_paths", relative_path)
    return record


def source_ref(provenance_record: "dict | None") -> "dict | None":
    if provenance_record is None:
        return None
    return {field: provenance_record[field] for field in SOURCE_REF_FIELDS}


def refusal(stage: str, reason: str, detail: str, *, source: "dict | None" = None,
            key: "str | None" = None) -> dict:
    record = {"record_type": REFUSAL_RECORD_TYPE, "stage": stage, "reason": reason,
              "detail": (detail or reason)[:300], "source_ref": source, "candidate_key": key}
    read_refusal(record)
    return record


def read_refusal(value) -> dict:
    record = read_record(value, REFUSAL_RECORD_TYPE, REFUSAL_FIELDS)
    stage = member(record["stage"], "stage", STAGES)
    member(record["reason"], "reason", REASONS[stage])
    text_value(record["detail"], "detail", limit=300)
    if record["source_ref"] is not None:
        part = read_part(record["source_ref"], "source_ref", SOURCE_REF_FIELDS)
        for field in SOURCE_REF_FIELDS:
            text_value(part[field], f"source_ref.{field}", limit=512)
    if record["candidate_key"] is not None:
        digest_value(record["candidate_key"], "candidate_key")
    return record


def read_outline(value) -> dict:
    """An outline names the abstract purpose and the source; it never carries source text."""
    record = read_record(value, OUTLINE_RECORD_TYPE, OUTLINE_FIELDS)
    digest_value(record["outline_key"], "outline_key")
    member(record["kind"], "kind", KINDS)
    member(record["native_format"], "native_format", NATIVE_FORMATS)
    text_value(record["source_name"], "source_name", limit=128)
    sequence(record["topic_words"], "topic_words", lambda value, name: text_value(value, name, limit=40))
    text_value(record["abstract_purpose"], "abstract_purpose", limit=600)
    provenance = read_outside_provenance(record["provenance"])
    if provenance.decision != OUTLINE_ONLY:
        raise LibraryRecordError("outline_without_outline_rights",
                                 "an outline is written only for an outline-only source")
    generator = read_part(record["generator"], "generator", GENERATOR_FIELDS)
    identifier(generator["engine_id"], "generator.engine_id")
    text_value(generator["engine_version"], "generator.engine_version", limit=32)
    if flag(record["text_included"], "text_included") is not False:
        raise LibraryRecordError("outline_carries_text", "an outline never carries the source text")
    sequence(record["model_calls"], "model_calls", digest_value)
    return record


def candidate_request(source_id: str, *, cursor: "str | None" = None, maximum_candidates: int = 2000,
                      maximum_requests: int = 3000, network_reads_authorized: bool = False,
                      requested_at: str) -> dict:
    record = {"record_type": REQUEST_RECORD_TYPE, "source_id": source_id, "cursor": cursor,
              "maximum_candidates": maximum_candidates, "maximum_requests": maximum_requests,
              "network_reads_authorized": network_reads_authorized, "requested_at": requested_at}
    read_candidate_request(record)
    return record


def read_candidate_request(value) -> dict:
    record = read_record(value, REQUEST_RECORD_TYPE, REQUEST_FIELDS)
    identifier(record["source_id"], "source_id")
    optional_text(record["cursor"], "cursor", limit=512)
    count(record["maximum_candidates"], "maximum_candidates", maximum=100_000)
    count(record["maximum_requests"], "maximum_requests", maximum=100_000)
    flag(record["network_reads_authorized"], "network_reads_authorized")
    utc_time(record["requested_at"], "requested_at")
    return record


def read_candidate_batch(value) -> dict:
    """Every engine behind the source slot answers with exactly this shape."""
    record = read_record(value, BATCH_RECORD_TYPE, BATCH_FIELDS)
    digest_value(record["request_digest"], "request_digest")
    identifier(record["source_id"], "source_id")
    identifier(record["engine_id"], "engine_id")
    text_value(record["engine_version"], "engine_version", limit=32)
    complete = flag(record["complete"], "complete")
    optional_text(record["next_cursor"], "next_cursor", limit=512)
    stopped = member(record["stopped_reason"], "stopped_reason", STOP_REASONS)
    if complete != (stopped == "complete"):
        raise LibraryRecordError("batch_completion_inconsistent",
                                 "a batch is complete exactly when its stop reason says so")
    sequence(record["candidates"], "candidates", lambda value, name: read_source_candidate(value))
    sequence(record["refusals"], "refusals", lambda value, name: read_refusal(value))
    count(record["requests_made"], "requests_made")
    keys = [row["candidate_key"] for row in record["candidates"]]
    if len(keys) != len(set(keys)):
        raise LibraryRecordError("duplicate_candidate_key", "a batch names each candidate once")
    return record


def candidate_batch(request: dict, engine, *, complete: bool, next_cursor, stopped_reason: str,
                    candidates, refusals, requests_made: int) -> dict:
    record = {"record_type": BATCH_RECORD_TYPE, "request_digest": canonical_digest(request),
              "source_id": request["source_id"], "engine_id": engine.engine_id,
              "engine_version": engine.engine_version, "complete": complete,
              "next_cursor": next_cursor, "stopped_reason": stopped_reason,
              "candidates": list(candidates), "refusals": list(refusals),
              "requests_made": requests_made}
    return read_candidate_batch(record)
