"""Versioned provenance for every item that came from outside this repository.

A candidate built from outside material carries one record,
outside_source_provenance/v1, that names where its exact bytes came from:
the origin, the repository or registry entry, an immutable revision, the
path, the digest and size of the fetched bytes, the licence evidence (an
SPDX expression with the licence file digest and every file-level notice),
the fetch time and the digest of the request record that fetched it.

The reader refuses a record with another version, an unknown field or a
missing field, and refuses combinations that cannot be true: a GitHub item
without a forty character commit and blob identity, a registry item that
claims verbatim rights, or verbatim rights without a licence file digest.
require_provenance refuses a candidate that carries no provenance at all.
Nothing here fetches, decides a licence, approves or serves anything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .record_rules import (
    LibraryRecordError, canonical_digest, count, digest_value, fraction, git_object,
    host_name, member, read_part, read_record, relative_path, sequence, text_value, utc_time)

PROVENANCE_RECORD_TYPE = "outside_source_provenance/v1"
LICENCE_EVIDENCE_RECORD_TYPE = "outside_licence_evidence/v1"

#: Where outside bytes come from. Each origin has one host.
GITHUB_ORIGIN, REGISTRY_ORIGIN = "github_repository", "mcp_official_registry"
ORIGINS = (GITHUB_ORIGIN, REGISTRY_ORIGIN)
ORIGIN_HOSTS = {GITHUB_ORIGIN: "github.com", REGISTRY_ORIGIN: "registry.modelcontextprotocol.io"}

#: What the licence evidence permits. Only verbatim_permitted allows a copy of
#: the bytes. link_only is a registry entry whose files Baltor writes from
#: facts; outline_only keeps the abstract purpose and the source identity for
#: an original rewrite; refused keeps nothing but the refusal.
VERBATIM, LINK_ONLY, OUTLINE_ONLY, REFUSED = (
    "verbatim_permitted", "link_only", "outline_only", "refused")
LICENCE_DECISIONS = (VERBATIM, LINK_ONLY, OUTLINE_ONLY, REFUSED)

#: SPDX's own words for no licence and for a licence nobody could name.
NO_LICENCE, NO_ASSERTION = "NONE", "NOASSERTION"
#: The kinds of notice that can sit on or beside one file.
NOTICE_KINDS = ("licence_file", "frontmatter_licence", "notice_file", "spdx_header")

PROVENANCE_FIELDS = ("origin", "origin_host", "repository", "immutable_revision", "path",
                     "source_digest", "source_size_bytes", "git_blob_sha", "fetch_digest",
                     "licence_evidence", "fetched_at", "request_digest")
EVIDENCE_FIELDS = ("spdx_expression", "decision", "reason", "detector", "repository_licence",
                   "governing_file", "file_level_notices")
REPOSITORY_LICENCE_FIELDS = ("path", "sha256", "github_spdx_id", "matched_spdx", "similarity")
GOVERNING_FILE_FIELDS = ("path", "sha256", "matched_spdx", "similarity")
NOTICE_FIELDS = ("kind", "path", "sha256", "value")

_SPDX_TOKEN = r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}"
_SPDX_EXPRESSION = re.compile(rf"{_SPDX_TOKEN}(?: (?:AND|OR|WITH) {_SPDX_TOKEN}){{0,7}}\Z")
_GITHUB_REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}\Z")
_REGISTRY_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_REGISTRY_REVISION = re.compile(
    r"version:[^;\s]{1,64};published:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z\Z")
_REGISTRY_PATH_PREFIX = "v0.1/servers/"


def spdx_expression(value, name: str) -> str:
    if type(value) is not str or not _SPDX_EXPRESSION.match(value):
        raise LibraryRecordError("invalid_spdx_expression",
                                 f"{name} must be an SPDX expression, {NO_LICENCE} or {NO_ASSERTION}")
    return value


def _optional_spdx(value, name: str):
    return None if value is None else spdx_expression(value, name)


def _repository_licence(value):
    if value is None:
        return None
    part = read_part(value, "repository_licence", REPOSITORY_LICENCE_FIELDS)
    relative_path(part["path"], "repository_licence.path")
    digest_value(part["sha256"], "repository_licence.sha256")
    _optional_spdx(part["github_spdx_id"], "repository_licence.github_spdx_id")
    _optional_spdx(part["matched_spdx"], "repository_licence.matched_spdx")
    fraction(part["similarity"], "repository_licence.similarity")
    return part


def _governing_file(value):
    if value is None:
        return None
    part = read_part(value, "governing_file", GOVERNING_FILE_FIELDS)
    relative_path(part["path"], "governing_file.path")
    digest_value(part["sha256"], "governing_file.sha256")
    _optional_spdx(part["matched_spdx"], "governing_file.matched_spdx")
    fraction(part["similarity"], "governing_file.similarity")
    return part


def _notice(value, name):
    part = read_part(value, name, NOTICE_FIELDS)
    member(part["kind"], f"{name}.kind", NOTICE_KINDS)
    relative_path(part["path"], f"{name}.path")
    digest_value(part["sha256"], f"{name}.sha256")
    text_value(part["value"], f"{name}.value", limit=512)
    return part


def read_licence_evidence(value) -> dict:
    """Return the licence evidence only when it is exact and internally possible."""
    record = read_record(value, LICENCE_EVIDENCE_RECORD_TYPE, EVIDENCE_FIELDS)
    spdx_expression(record["spdx_expression"], "licence_evidence.spdx_expression")
    decision = member(record["decision"], "licence_evidence.decision", LICENCE_DECISIONS)
    text_value(record["reason"], "licence_evidence.reason", limit=160)
    text_value(record["detector"], "licence_evidence.detector", limit=160)
    _repository_licence(record["repository_licence"])
    governing = _governing_file(record["governing_file"])
    sequence(record["file_level_notices"], "licence_evidence.file_level_notices", _notice)
    if decision == VERBATIM:
        if governing is None:
            raise LibraryRecordError("verbatim_without_licence_file",
                                     "verbatim rights must name the licence file and its digest")
        if record["spdx_expression"] in (NO_LICENCE, NO_ASSERTION):
            raise LibraryRecordError("verbatim_without_licence",
                                     "verbatim rights need a named licence, not "
                                     f"{record['spdx_expression']}")
        if governing["matched_spdx"] != record["spdx_expression"]:
            raise LibraryRecordError("verbatim_licence_disagrees",
                                     "the licence file must match the licence the evidence names")
    return record


@dataclass(frozen=True)
class OutsideSourceProvenance:
    """Where one item's exact bytes came from, and what their licence evidence permits."""

    origin: str
    origin_host: str
    repository: str
    immutable_revision: str
    path: str
    source_digest: str
    source_size_bytes: int
    git_blob_sha: "str | None"
    fetch_digest: str
    licence_evidence: dict
    fetched_at: str
    request_digest: str

    def __post_init__(self) -> None:
        # One validation path: the reader checks exactly what a written record carries.
        read_outside_provenance(self.to_record())

    @property
    def decision(self) -> str:
        return self.licence_evidence["decision"]

    @property
    def spdx(self) -> str:
        return self.licence_evidence["spdx_expression"]

    def to_record(self) -> dict:
        return {"record_type": PROVENANCE_RECORD_TYPE, "origin": self.origin,
                "origin_host": self.origin_host, "repository": self.repository,
                "immutable_revision": self.immutable_revision, "path": self.path,
                "source_digest": self.source_digest, "source_size_bytes": self.source_size_bytes,
                "git_blob_sha": self.git_blob_sha, "fetch_digest": self.fetch_digest,
                "licence_evidence": self.licence_evidence, "fetched_at": self.fetched_at,
                "request_digest": self.request_digest}

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_record())

    def identity_key(self) -> str:
        """Origin, revision, path and source digest: the fields that name the bytes."""
        return canonical_digest({"origin": self.origin, "repository": self.repository,
                                 "immutable_revision": self.immutable_revision,
                                 "path": self.path, "source_digest": self.source_digest})


def read_outside_provenance(value) -> OutsideSourceProvenance:
    """Return typed provenance, or refuse the record before anything is built from it."""
    record = read_record(value, PROVENANCE_RECORD_TYPE, PROVENANCE_FIELDS)
    origin = member(record["origin"], "origin", ORIGINS)
    host_name(record["origin_host"], "origin_host")
    if record["origin_host"] != ORIGIN_HOSTS[origin]:
        raise LibraryRecordError("origin_host_mismatch",
                                 f"the origin {origin} is read from {ORIGIN_HOSTS[origin]} only")
    relative_path(record["path"], "path")
    digest_value(record["source_digest"], "source_digest")
    count(record["source_size_bytes"], "source_size_bytes")
    digest_value(record["fetch_digest"], "fetch_digest")
    utc_time(record["fetched_at"], "fetched_at")
    digest_value(record["request_digest"], "request_digest")
    evidence = read_licence_evidence(record["licence_evidence"])
    if origin == GITHUB_ORIGIN:
        if type(record["repository"]) is not str or not _GITHUB_REPOSITORY.match(record["repository"]):
            raise LibraryRecordError("invalid_repository", "a GitHub repository is written owner/name")
        git_object(record["immutable_revision"], "immutable_revision")
        git_object(record["git_blob_sha"], "git_blob_sha")
        if evidence["decision"] == LINK_ONLY:
            raise LibraryRecordError("link_only_outside_registry",
                                     "link-only rights belong to registry entries, not to files")
    else:
        if type(record["repository"]) is not str or not _REGISTRY_NAME.match(record["repository"]):
            raise LibraryRecordError("invalid_repository", "a registry entry is written by its server name")
        if type(record["immutable_revision"]) is not str \
                or not _REGISTRY_REVISION.match(record["immutable_revision"]):
            raise LibraryRecordError("invalid_revision",
                                     "a registry revision is written version:V;published:TIME")
        if record["git_blob_sha"] is not None:
            raise LibraryRecordError("invalid_revision", "a registry entry has no git blob identity")
        if not record["path"].startswith(_REGISTRY_PATH_PREFIX):
            raise LibraryRecordError("unsafe_path", "a registry path names its server version resource")
        if evidence["decision"] == VERBATIM:
            raise LibraryRecordError("registry_entry_is_never_verbatim",
                                     "registry text is never copied; entries are link-only")
    return _build(record)


def _build(record: dict) -> OutsideSourceProvenance:
    """Construct without validating twice: the reader has already checked every field."""
    built = object.__new__(OutsideSourceProvenance)
    for field in PROVENANCE_FIELDS:
        object.__setattr__(built, field, record[field])
    return built


def require_provenance(candidate, field: str = "provenance") -> tuple:
    """Refuse a candidate that carries no provenance, and read every record it carries.

    A candidate may carry one record or, after duplicates were merged, a list
    whose first record names the kept bytes. An empty list is no provenance.
    """
    if type(candidate) is not dict or field not in candidate:
        raise LibraryRecordError("provenance_required",
                                 "outside material is never a candidate without its provenance")
    value = candidate[field]
    records = value if type(value) is list else [value]
    if not records or any(item is None for item in records):
        raise LibraryRecordError("provenance_required",
                                 "outside material is never a candidate without its provenance")
    return tuple(read_outside_provenance(item) for item in records)
