"""Strict reading rules shared by every record of the library ingestion component.

Every record here is written as name/vN. A reader returns a record only when
its type, version and field set are exact, so another version, an unknown
field or a missing field is refused before anything is built from it. Each
rule raises LibraryRecordError with a stable code and a message that names
the field, never a body. The shared engine framework (roadmap S-6.30) is not
on this line yet; when it lands, these rules can move behind its reader
without changing any record.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_GIT_OBJECT = re.compile(r"[0-9a-f]{40}\Z")
_UTC_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,95}\Z")
_HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+\Z")
#: The longest path a record may name, in characters.
MAXIMUM_PATH_CHARACTERS = 512


class LibraryRecordError(ValueError):
    """A record of this component is refused, with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def read_record(value, record_type: str, fields) -> dict:
    """Return the record only when its type, version and field set are exact."""
    if type(value) is not dict:
        raise LibraryRecordError("record_not_a_mapping", f"{record_type} must be a JSON object")
    found = value.get("record_type")
    if found != record_type:
        family = record_type.rpartition("/")[0]
        if type(found) is str and found.rpartition("/")[0] == family:
            raise LibraryRecordError("unsupported_record_version",
                                     f"{found} is not read here; this release reads {record_type}")
        raise LibraryRecordError("unknown_record_type", f"expected {record_type}")
    return read_part(value, record_type, (*fields, "record_type"))


def read_part(value, name: str, fields) -> dict:
    """The same exact field rule for a part nested inside a record."""
    if type(value) is not dict:
        raise LibraryRecordError("record_not_a_mapping", f"{name} must be a JSON object")
    expected = set(fields)
    unknown = sorted(str(key) for key in set(value) - expected)
    if unknown:
        raise LibraryRecordError("unknown_record_fields", f"{name} carries unknown fields {unknown}")
    missing = sorted(expected - set(value))
    if missing:
        raise LibraryRecordError("missing_record_fields", f"{name} lacks {missing}")
    return value


def digest_value(value, name: str) -> str:
    if type(value) is not str or not _DIGEST.match(value):
        raise LibraryRecordError("invalid_digest", f"{name} must be a lowercase SHA-256 digest")
    return value


def git_object(value, name: str) -> str:
    if type(value) is not str or not _GIT_OBJECT.match(value):
        raise LibraryRecordError("invalid_revision",
                                 f"{name} must be one full forty character object identity")
    return value


def text_value(value, name: str, *, limit: int = 512, one_line: bool = True) -> str:
    if type(value) is not str or not value.strip() or value != value.strip() or len(value) > limit:
        raise LibraryRecordError("invalid_text", f"{name} must be exact nonempty text of at most "
                                                 f"{limit} characters")
    if "\x00" in value or (one_line and any(ord(character) < 32 for character in value)):
        raise LibraryRecordError("invalid_text", f"{name} carries a control character")
    return value


def optional_text(value, name: str, *, limit: int = 512):
    return None if value is None else text_value(value, name, limit=limit)


def identifier(value, name: str) -> str:
    if type(value) is not str or not _IDENTIFIER.match(value):
        raise LibraryRecordError("invalid_identifier", f"{name} must match {_IDENTIFIER.pattern}")
    return value


def host_name(value, name: str) -> str:
    if type(value) is not str or len(value) > 253 or not _HOST.match(value):
        raise LibraryRecordError("invalid_host", f"{name} must be a lowercase host name")
    return value


def member(value, name: str, allowed) -> str:
    if type(value) is not str or value not in allowed:
        raise LibraryRecordError("invalid_vocabulary", f"{name} must be one of {sorted(allowed)}")
    return value


def flag(value, name: str) -> bool:
    if type(value) is not bool:
        raise LibraryRecordError("invalid_boolean", f"{name} must be an explicit Boolean")
    return value


def count(value, name: str, *, maximum: int = 2 ** 40) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise LibraryRecordError("invalid_count", f"{name} must be a whole number from 0 to {maximum}")
    return value


def fraction(value, name: str):
    """A similarity or share from 0 to 1, or None when nothing was measured."""
    if value is None:
        return None
    if type(value) not in (int, float) or not 0 <= value <= 1:
        raise LibraryRecordError("invalid_fraction", f"{name} must be a number from 0 to 1")
    return value


def utc_time(value, name: str) -> str:
    """An exact UTC time written YYYY-MM-DDTHH:MM:SSZ, and a real one."""
    if type(value) is not str or not _UTC_TIME.match(value):
        raise LibraryRecordError("invalid_time", f"{name} must be written YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise LibraryRecordError("invalid_time", f"{name} is not a real time") from None
    return value


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def relative_path(value, name: str) -> str:
    """A confined forward-slash path: no root, no parent step, no empty part."""
    if (type(value) is not str or not value or len(value) > MAXIMUM_PATH_CHARACTERS
            or "\\" in value or "\x00" in value or any(ord(character) < 32 for character in value)):
        raise LibraryRecordError("unsafe_path", f"{name} must be a confined relative path")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or any(part in ("", ".", "..") for part in parts):
        raise LibraryRecordError("unsafe_path", f"{name} must be a confined relative path")
    return value


def sequence(values, name: str, rule, *, nonempty: bool = False) -> tuple:
    if type(values) not in (list, tuple):
        raise LibraryRecordError("invalid_sequence", f"{name} must be a list")
    values = tuple(values)
    if nonempty and not values:
        raise LibraryRecordError("invalid_sequence", f"{name} must not be empty")
    return tuple(rule(value, name) for value in values)


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def canonical_digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bytes_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_identity(data: bytes) -> str:
    """The identity git gives a file's bytes, so fetched bytes can be proven committed."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()  # noqa: S324 - git's own identity
