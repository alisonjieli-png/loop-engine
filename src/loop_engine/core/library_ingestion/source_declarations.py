"""The curated list of outside sources, as one reviewed and versioned record.

library_outside_sources/v1 names every source an ingestion run may read:
for a GitHub repository, the exact commit, how the repository was curated
(first-party work, contributions under the repository licence, or licences
set file by file), the licence curation verified, and the paths to select;
for the protocol server registry, the host, the entry ceiling and the name
prefixes of known copies to leave out. It also pins the schemas that the
connection files are validated against, by source and digest. The reader
refuses another version, an unknown field and a missing field.

Selection patterns use two wildcards: a single star matches within one path
part, and a double star matches any number of parts.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from .record_rules import (
    LibraryRecordError, count, digest_value, git_object, host_name, identifier, member, read_part,
    read_record, relative_path, sequence, text_value)

SOURCES_RECORD_TYPE = "library_outside_sources/v1"
SOURCES_FILE = Path(__file__).with_name("outside_sources.yaml")
GITHUB_ENGINE, REGISTRY_ENGINE = "github_pinned_repositories", "mcp_official_registry"
USES = ("verbatim", "outline", "link")
CONTENT_ORIGINS = ("first_party", "contributed_under_repository_licence", "per_file_licences",
                   "third_party_or_unclear")
GITHUB_FIELDS = ("source_id", "engine", "repository", "commit", "use", "content_origin",
                 "expected_licence", "include", "exclude", "note")
REGISTRY_FIELDS = ("source_id", "engine", "host", "use", "maximum_entries", "exclude_name_prefixes",
                   "note")
SCHEMA_FIELDS = ("schema_id", "host", "repository", "commit", "path", "sha256", "licence")
RECORD_FIELDS = ("curated_on", "curated_by", "sources", "schemas")
_REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}\Z")


def _pattern(value, name):
    text_value(value, name, limit=200)
    if value.startswith("/") or ".." in value.split("/"):
        raise LibraryRecordError("unsafe_path", f"{name} must be a relative pattern")
    return value


def read_github_source(value) -> dict:
    row = read_part(value, "github source", GITHUB_FIELDS)
    identifier(row["source_id"], "source_id")
    member(row["engine"], "engine", (GITHUB_ENGINE,))
    if type(row["repository"]) is not str or not _REPOSITORY.match(row["repository"]):
        raise LibraryRecordError("invalid_repository", "a repository is written owner/name")
    git_object(row["commit"], "commit")
    member(row["use"], "use", ("verbatim", "outline"))
    member(row["content_origin"], "content_origin", CONTENT_ORIGINS)
    if row["expected_licence"] is not None:
        text_value(row["expected_licence"], "expected_licence", limit=64)
    sequence(row["include"], "include", _pattern, nonempty=True)
    sequence(row["exclude"], "exclude", _pattern)
    text_value(row["note"], "note", limit=400)
    if row["use"] == "verbatim" and row["content_origin"] == "third_party_or_unclear":
        raise LibraryRecordError("verbatim_from_unclear_origin",
                                 "material of unclear origin is read for outlines only")
    return row


def read_registry_source(value) -> dict:
    row = read_part(value, "registry source", REGISTRY_FIELDS)
    identifier(row["source_id"], "source_id")
    member(row["engine"], "engine", (REGISTRY_ENGINE,))
    host_name(row["host"], "host")
    member(row["use"], "use", ("link",))
    count(row["maximum_entries"], "maximum_entries", maximum=100_000)
    sequence(row["exclude_name_prefixes"], "exclude_name_prefixes",
             lambda value, name: text_value(value, name, limit=128))
    text_value(row["note"], "note", limit=400)
    return row


def read_schema(value) -> dict:
    row = read_part(value, "schema", SCHEMA_FIELDS)
    identifier(row["schema_id"], "schema_id")
    host_name(row["host"], "host")
    if row["repository"] is not None:
        if type(row["repository"]) is not str or not _REPOSITORY.match(row["repository"]):
            raise LibraryRecordError("invalid_repository", "a repository is written owner/name")
        git_object(row["commit"], "commit")
    elif row["commit"] is not None:
        raise LibraryRecordError("invalid_revision", "a schema without a repository has no commit")
    relative_path(row["path"], "path")
    digest_value(row["sha256"], "sha256")
    text_value(row["licence"], "licence", limit=64)
    return row


def read_sources(value) -> dict:
    record = read_record(value, SOURCES_RECORD_TYPE, RECORD_FIELDS)
    text_value(record["curated_on"], "curated_on", limit=10)
    text_value(record["curated_by"], "curated_by", limit=120)
    seen = set()
    for row in sequence(record["sources"], "sources", lambda value, name: value, nonempty=True):
        engine = row.get("engine") if type(row) is dict else None
        read_github_source(row) if engine == GITHUB_ENGINE else read_registry_source(row)
        if row["source_id"] in seen:
            raise LibraryRecordError("duplicate_source", f"{row['source_id']} is declared twice")
        seen.add(row["source_id"])
    sequence(record["schemas"], "schemas", lambda value, name: read_schema(value))
    return record


@lru_cache(maxsize=2)
def _load(path: str) -> dict:
    import yaml

    return read_sources(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def load_sources(path: "Path | None" = None) -> dict:
    return _load(str(path or SOURCES_FILE))


@lru_cache(maxsize=512)
def pattern_expression(pattern: str):
    """Translate a selection pattern: '*' within one part, '**' across any number of parts."""
    parts = []
    for part in pattern.split("/"):
        if part == "**":
            parts.append(None)
            continue
        parts.append(re.escape(part).replace(r"\*", "[^/]*").replace(r"\?", "[^/]"))
    expression = ""
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        if part is None:
            expression += "(?:.*)" if last else "(?:[^/]+/)*"
        else:
            expression += part + ("" if last else "/")
    return re.compile(expression + r"\Z")


def selected(path: str, include, exclude) -> bool:
    return (any(pattern_expression(pattern).match(path) for pattern in include)
            and not any(pattern_expression(pattern).match(path) for pattern in exclude))
