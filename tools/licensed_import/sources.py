"""The source declaration: licensed_import_sources/v1, read strictly.

The declaration names every place the import may look, with a note saying
why each source is there. It grants nothing: network reads come from the
operator's flag, and every file still passes the licence gate on its own.
"""
from __future__ import annotations

import re

from loop_engine.core.library_ingestion.record_rules import (
    LibraryRecordError, host_name, read_part, read_record, text_value)

from .records import PACKAGE_KINDS, SOURCES_RECORD_TYPE

_SOURCE_ID = re.compile(r"[a-z][a-z0-9_.-]{1,95}\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}\Z")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
FIELDS = ("curated_on", "curated_by", "note", "repositories", "excluded_repositories", "owner_seeds",
          "research_seeds", "feeds", "awesome_lists", "code_search", "topic_search", "npm_search", "registry")


def _source_id(value, name):
    if type(value) is not str or not _SOURCE_ID.match(value):
        raise LibraryRecordError("invalid_source_id", f"{name} must match {_SOURCE_ID.pattern}")
    return value


def _repository(value, name):
    if type(value) is not str or not _REPOSITORY.match(value):
        raise LibraryRecordError("invalid_repository", f"{name} is written owner/name")
    return value


def _list(value, name):
    if type(value) is not list:
        raise LibraryRecordError("invalid_sequence", f"{name} must be a list")
    return value


def read_sources(value) -> dict:
    """Return the declaration only when every section has its exact shape."""
    record = read_record(value, SOURCES_RECORD_TYPE, FIELDS)
    text_value(record["note"], "note", limit=2000, one_line=False)
    seen = set()

    def unique(source_id):
        if source_id in seen:
            raise LibraryRecordError("duplicate_source_id", f"{source_id} is declared twice")
        seen.add(source_id)

    for row in _list(record["repositories"], "repositories"):
        allowed = {"source_id", "repository", "note", "kinds", "include", "exclude"}
        if type(row) is not dict or set(row) - allowed or not {"source_id", "repository", "note"} <= set(row):
            raise LibraryRecordError("unknown_record_fields", "a repository names its id, repository and note, "
                                                              "and may name kinds, include and exclude")
        part = row
        unique(_source_id(part["source_id"], "repositories.source_id"))
        _repository(part["repository"], "repositories.repository")
        text_value(part["note"], "repositories.note", limit=600)
        if any(kind not in PACKAGE_KINDS for kind in part.get("kinds", ())):
            raise LibraryRecordError("invalid_vocabulary", f"{part['source_id']} names a kind outside {PACKAGE_KINDS}")
    for row in _list(record["excluded_repositories"], "excluded_repositories"):
        read_part(row, "excluded_repository", ("repository", "note"))
        _repository(row["repository"], "excluded_repositories.repository")
        text_value(row["note"], "excluded_repositories.note", limit=600)
    for row in _list(record["owner_seeds"], "owner_seeds"):
        allowed = {"source_id", "seed", "repository", "path", "names", "queries", "note"}
        if set(row) - allowed or not {"source_id", "seed", "note"} <= set(row):
            raise LibraryRecordError("unknown_record_fields", "an owner seed names its id, seed and note")
        unique(_source_id(row["source_id"], "owner_seeds.source_id"))
        if row.get("repository"):
            _repository(row["repository"], "owner_seeds.repository")
        elif not row.get("names") or not row.get("queries"):
            raise LibraryRecordError("invalid_seed", f"{row['seed']} needs a repository, or names and queries")
    for row in _list(record["research_seeds"], "research_seeds"):
        read_part(row, "research_seed", ("source_id", "file", "note"))
        unique(_source_id(row["source_id"], "research_seeds.source_id"))
    for row in _list(record["feeds"], "feeds"):
        read_part(row, "feed", ("source_id", "host", "path", "note"))
        unique(_source_id(row["source_id"], "feeds.source_id"))
        host_name(row["host"], "feeds.host")
        if not row["path"].startswith("/"):
            raise LibraryRecordError("invalid_path", "a feed path starts at its host's root")
    for row in _list(record["awesome_lists"], "awesome_lists"):
        read_part(row, "awesome_list", ("source_id", "repository", "path", "note"))
        unique(_source_id(row["source_id"], "awesome_lists.source_id"))
        _repository(row["repository"], "awesome_lists.repository")
    for row in _list(record["code_search"], "code_search"):
        read_part(row, "code_search", ("source_id", "kind", "terms", "size_bands", "pages", "note"))
        unique(_source_id(row["source_id"], "code_search.source_id"))
        if row["kind"] not in PACKAGE_KINDS:
            raise LibraryRecordError("invalid_vocabulary", f"{row['source_id']} names an unknown kind")
        for band in row["size_bands"]:
            if type(band) is not list or len(band) != 2 or not all(type(value) is int for value in band) \
                    or band[0] > band[1]:
                raise LibraryRecordError("invalid_band", f"{row['source_id']} has a size band that is not low..high")
    topic = read_part(record["topic_search"], "topic_search",
                      ("topics", "created_ranges", "minimum_stars", "pages", "note"))
    for start, end in topic["created_ranges"]:
        if not (_DATE.match(start) and _DATE.match(end)) or start > end:
            raise LibraryRecordError("invalid_range", "a creation range is two dates, oldest first")
    read_part(record["npm_search"], "npm_search", ("texts", "pages", "note"))
    registry = read_part(record["registry"], "registry",
                         ("host", "updated_since", "page_size", "maximum_entries", "note"))
    host_name(registry["host"], "registry.host")
    if not _TIME.match(registry["updated_since"]):
        raise LibraryRecordError("invalid_time", "registry.updated_since is an exact UTC time")
    return record
