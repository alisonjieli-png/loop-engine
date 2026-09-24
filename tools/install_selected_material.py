"""Install selected service material into a supported client's native layout.

The tool closes one gap: bytes fetched from the service are not yet material
that a client has loaded. It searches or takes explicit identities, reads each
manifest, downloads each selected body, checks the body digest against both the
response header and the manifest, and writes the body where the named client
discovers material. It then runs the client's own listing command and records,
for each item, whether the client reports it.

Offered, fetched, installed and reported by the client are separate facts in
the report. The tool never starts a model turn, never takes the service key on
the command line, never follows a symbolic link under the target folder and
never replaces a different existing file. A listing proves discovery by the
client. It does not prove that a model read, used or benefited from the item.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import errno
import hashlib
import hmac
from importlib.resources import files
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import uuid

from loop_engine.core.harness_intelligence import KINDS
from loop_engine.core.provisioning_server import MANIFEST_RECORD_TYPE
from loop_engine.core.service_runtime.http import (
    ERROR_VERSION, MANIFEST_OPERATION, PROVISIONING_REQUEST_VERSION, READ_OPERATION,
    RESULT_VERSION, RETRIEVAL_REQUEST_VERSION,
)
from loop_engine.core.service_runtime.http_auth import validate_public_url

REPORT_RECORD_TYPE = "native_material_install_report/v1"
INSTALL_RECORD_TYPE = "native_material_install_record/v1"
PREVIEW_RECORD_TYPE = "native_material_install_preview/v1"
LAYOUT_PROFILE_RECORD_TYPE = "native_client_layout_profile/v1"
LISTING_RECORD_TYPE = "native_client_listing_observation/v1"
# The service states these values inline in its HTTP adapter. The checks run
# against the real local service, so a change there fails a named check here.
CAPABILITIES_RECORD_TYPE = "service_capabilities/v1"
RETRIEVAL_RESULT_RECORD_TYPE = "service_retrieval_result/v1"
DOWNLOAD_RECORD_TYPE = "service_download/v1"
SUPPORTED_API_VERSION = "v1"
SUPPORTED_BODY_FORMAT = "utf8_text"
CAPABILITIES_ROUTE = "/api/v1/capabilities"
RETRIEVAL_ROUTE = "/api/v1/retrieval"
PROVISIONING_ROUTE = "/api/v1/provisioning"
DOWNLOAD_ROUTE = "/api/v1/download"
DIGEST_HEADER = "X-Content-SHA256"
RECORD_TYPE_HEADER = "X-Loop-Engine-Record-Type"
SKILL_KIND = "skill"
SKILL_FILE_RENDERING = "generated_frontmatter_then_served_body"
LISTING_FORMAT_JSON_ENTRIES = "json_entries"
CLIENT_RECIPES_RESOURCE = ("core", "service_runtime", "web_assets", "client-recipes.json")
# The tool reads one field of the registry, the identifier of each recipe. That field has the
# same place and meaning in both versions named here. Any other version is refused, not guessed.
SUPPORTED_CLIENT_REGISTRY_RECORD_TYPES = ("website_client_recipes/v1", "website_client_recipes/v2")
# Text from the service or the client can hold a code point that UTF-8 cannot carry, such as a
# lone surrogate. The report writes every character outside ASCII as an escape, so no text can
# make the report write fail.
REPORT_ASCII_ONLY = True
# A parser can fail on nesting depth as well as on syntax. Both mean "not a usable record".
JSON_PARSE_ERRORS = (ValueError, RecursionError)
# After the report is reserved, nothing that goes wrong may end the run without a report.
UNEXPECTED_ERRORS = (Exception,)
RESPONSE_READ_CHUNK_BYTES = 1 << 16
PARTIAL_FILE_SUFFIX = ".partial"
# Opening with this flag fails on a symbolic link instead of following it.
# A platform without it is refused before any file access.
NO_FOLLOW_FLAG = getattr(os, "O_NOFOLLOW", None)
DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*")
NATIVE_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VARIABLE_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
KEY_VALUE_PATTERN = re.compile(r"[\x21-\x7e]{8,4096}")
REQUEST_PREFIX_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
ERROR_CODE_PATTERN = re.compile(r"[a-z0-9_]{1,80}")
VERSION_PATTERN = re.compile(r"[0-9][0-9A-Za-z.+-]{0,39}")
# A shortened option such as "--key" would otherwise take the next value as a variable name.
OPTION_ABBREVIATIONS_ALLOWED = False
MAXIMUM_IDENTITY_CHARACTERS = 200
MAXIMUM_NATIVE_NAME_CHARACTERS = 64
MAXIMUM_DESCRIPTION_CHARACTERS = 1024
MAXIMUM_QUERY_BYTES = 4096

if SKILL_KIND not in KINDS:
    raise RuntimeError("the served kinds registry no longer names the skill kind")


class Stage(str, Enum):
    """Where in the journey of one item a refusal happened."""

    SELECTION = "selection"
    OFFER = "offer"
    FETCH = "fetch"
    VERIFICATION = "verification"
    PLACEMENT = "placement"


class RefusalCode(str, Enum):
    """Stable refusal codes. The text beside a code never holds a secret."""

    INSTALL_NOT_AUTHORIZED = "install_not_authorized"
    PREVIEW_EXCLUDES_AUTHORIZATION = "preview_excludes_authorize_install"
    INVALID_ORIGIN = "invalid_origin"
    INVALID_KEY_VARIABLE_NAME = "invalid_key_variable_name"
    KEY_VARIABLE_NOT_SET = "key_variable_not_set"
    KEY_VALUE_NOT_USABLE = "key_value_not_usable"
    KEY_ON_COMMAND_LINE = "key_on_command_line"
    SELECTION_REQUIRED = "exactly_one_of_query_or_identities_required"
    INVALID_QUERY = "invalid_query"
    INVALID_SEARCH_LIMIT = "invalid_search_limit"
    DUPLICATE_IDENTITY = "duplicate_identity"
    INVALID_REQUEST_PREFIX = "invalid_request_prefix"
    INVALID_ARGUMENTS = "invalid_arguments"
    CLIENT_REGISTRY_UNREADABLE = "client_registry_unreadable"
    UNSUPPORTED_CLIENT_REGISTRY_VERSION = "unsupported_client_registry_version"
    UNKNOWN_CLIENT_KIND = "unknown_client_kind"
    CLIENT_HAS_NO_LAYOUT_PROFILE = "client_has_no_layout_profile"
    TARGET_NOT_A_REAL_DIRECTORY = "target_not_a_real_directory"
    REPORT_PATH_NOT_NEW = "report_path_not_new"
    REPORT_PATH_NOT_USABLE = "report_path_not_usable"
    CONFINED_FILE_OPERATIONS_UNAVAILABLE = "confined_file_operations_unavailable"
    INVALID_LIMITS = "invalid_limits"
    UNSUPPORTED_SERVICE_CAPABILITIES = "unsupported_service_capabilities"
    UNSUPPORTED_SERVICE_RECORD = "unsupported_service_record"
    SERVICE_UNREACHABLE = "service_unreachable"
    REDIRECT_REFUSED = "redirect_refused"
    RESPONSE_TOO_LARGE = "response_too_large"
    RESPONSE_DEADLINE_PASSED = "response_deadline_passed"
    SERVICE_REFUSED = "service_refused"
    IDENTITY_HAS_NO_NATIVE_NAME = "identity_has_no_native_name"
    KIND_HAS_NO_NATIVE_LOCATION = "kind_has_no_native_location"
    BODY_NOT_PERMITTED = "body_not_permitted"
    BODY_EXCEEDS_DOWNLOAD_ALLOWANCE = "body_exceeds_download_allowance"
    OFFER_CHANGED = "offer_changed_between_search_and_manifest"
    PURPOSE_HAS_NO_PRINTABLE_TEXT = "purpose_has_no_printable_text"
    DIGEST_HEADER_MISSING_OR_MALFORMED = "digest_header_missing_or_malformed"
    BODY_DIFFERS_FROM_HEADER_DIGEST = "body_differs_from_header_digest"
    BODY_DIFFERS_FROM_MANIFEST_DIGEST = "body_differs_from_manifest_digest"
    BODY_SIZE_DIFFERS_FROM_MANIFEST = "body_size_differs_from_manifest"
    DOWNLOAD_EXCEEDS_DECLARED_SIZE = "download_exceeds_declared_size"
    BODY_IS_NOT_UTF8_TEXT = "body_is_not_utf8_text"
    PATH_TRAVERSAL_REFUSED = "path_traversal_refused"
    SYMBOLIC_LINK_REFUSED = "symbolic_link_refused"
    PATH_COMPONENT_NOT_A_DIRECTORY = "path_component_not_a_directory"
    EXISTING_PATH_NOT_A_REGULAR_FILE = "existing_path_not_a_regular_file"
    DIFFERENT_FILE_EXISTS = "different_file_exists"
    PATH_NOT_USABLE = "path_not_usable"
    TARGET_FOLDER_NOT_WRITABLE = "target_folder_not_writable"
    FILE_CHANGED_AFTER_INSTALL = "file_changed_after_install"
    UNEXPECTED_ERROR = "unexpected_error"
    WRITE_FAILED = "write_failed"
    MODEL_TURN_COMMAND_REFUSED = "model_turn_command_refused"
    INVALID_LAYOUT_PROFILE = "invalid_layout_profile"


class FetchOutcome(str, Enum):
    """What is known about one metered read. No response is unknown, not a failure."""

    NOT_NEEDED = "not_needed_identical_file_present"
    UNKNOWN = "unknown_no_response_received"
    REFUSED_BY_SERVICE = "refused_by_service"
    REJECTED_BY_VERIFICATION = "rejected_by_verification"
    FETCHED_AND_VERIFIED = "fetched_and_verified"


class ListingState(str, Enum):
    """Why a listing was or was not observed. Not checked is never reported as false."""

    OBSERVED = "observed"
    NOTHING_INSTALLED = "nothing_installed"
    PREVIEW_ONLY = "preview_only_no_client_process"
    CLIENT_OFFERS_NO_LISTING = "client_offers_no_listing_command"
    EXECUTABLE_NOT_FOUND = "client_executable_not_found"
    EXECUTABLE_NOT_USABLE = "client_executable_not_usable"
    TIMED_OUT = "listing_timed_out"
    FAILED = "listing_command_failed"
    TOO_LARGE = "listing_too_large"
    UNREADABLE = "listing_unreadable"


class InstallRefusal(Exception):
    """A typed refusal. Its text never holds a credential or a response body."""

    def __init__(self, code: RefusalCode, detail: str = ""):
        super().__init__(code.value)
        self.code, self.detail = code, detail


def _refuse_unless(condition: bool, code: RefusalCode, detail: str = "") -> None:
    if not condition:
        raise InstallRefusal(code, detail)


# ---------------------------------------------------------------------------
# Typed client layout profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NativeLocation:
    """Where one served kind lives inside a project for one client."""

    served_kind: str
    directory_segments: tuple[str, ...]
    file_name: str
    rendering: str

    def __post_init__(self):
        _refuse_unless(self.served_kind in KINDS and self.rendering in RENDERERS,
                       RefusalCode.INVALID_LAYOUT_PROFILE)
        validate_relative_parts((*self.directory_segments, self.file_name))

    def relative_parts(self, native_name: str) -> tuple[str, ...]:
        return (*self.directory_segments, native_name, self.file_name)


@dataclass(frozen=True)
class ListingCommand:
    """The client command that lists what it discovered, without a model turn."""

    arguments: tuple[str, ...]
    process_settings: tuple[tuple[str, str], ...] = ()
    output_format: str = LISTING_FORMAT_JSON_ENTRIES
    location_field: str = "location"
    name_field: str = "name"
    content_field: str = "content"

    def __post_init__(self):
        _refuse_unless(bool(self.arguments) and all(isinstance(value, str) and value for value in self.arguments)
                       and self.output_format == LISTING_FORMAT_JSON_ENTRIES,
                       RefusalCode.INVALID_LAYOUT_PROFILE)


def refuse_model_turn_subcommand(arguments: tuple[str, ...], model_turn_subcommands: tuple[str, ...]) -> None:
    """A listing command may never name a subcommand that starts a model turn."""
    _refuse_unless(not set(arguments) & set(model_turn_subcommands), RefusalCode.MODEL_TURN_COMMAND_REFUSED)


@dataclass(frozen=True)
class ClientLayoutProfile:
    """One supported client: native locations, listing command and evidence."""

    client_kind: str
    executable_name: str
    locations: tuple[NativeLocation, ...]
    unplaced_kinds: tuple[tuple[str, str], ...]
    listing: ListingCommand | None
    version_arguments: tuple[str, ...]
    model_turn_subcommands: tuple[str, ...]
    observed_client_versions: tuple[str, ...]
    record_type: str = LAYOUT_PROFILE_RECORD_TYPE

    def __post_init__(self):
        placed = [location.served_kind for location in self.locations]
        unplaced = [kind for kind, _reason in self.unplaced_kinds]
        _refuse_unless(self.record_type == LAYOUT_PROFILE_RECORD_TYPE and bool(self.client_kind)
                       and bool(self.executable_name) and len(set(placed)) == len(placed)
                       and sorted(placed + unplaced) == sorted(KINDS),
                       RefusalCode.INVALID_LAYOUT_PROFILE)
        refuse_model_turn_subcommand(self.version_arguments, self.model_turn_subcommands)
        if self.listing is not None:
            refuse_model_turn_subcommand(self.listing.arguments, self.model_turn_subcommands)

    def location_for(self, kind: str) -> NativeLocation:
        for location in self.locations:
            if location.served_kind == kind:
                return location
        reasons = dict(self.unplaced_kinds)
        raise InstallRefusal(RefusalCode.KIND_HAS_NO_NATIVE_LOCATION, reasons.get(kind, "kind_not_served"))

    def native_roots(self) -> tuple[str, ...]:
        """The first folder of every native location, for example the client's project folder."""
        return tuple(dict.fromkeys(location.directory_segments[0] for location in self.locations))


@dataclass(frozen=True)
class TransferLimits:
    """Bounds for every request, response and client process.

    request_timeout_seconds bounds one socket operation. response_deadline_seconds
    bounds one whole response, from the request to its last byte.
    """

    request_timeout_seconds: float = 30.0
    response_deadline_seconds: float = 300.0
    maximum_json_bytes: int = 2_000_000
    maximum_body_bytes: int = 64 * 1024 * 1024
    listing_timeout_seconds: float = 30.0
    version_timeout_seconds: float = 10.0
    maximum_listing_bytes: int = 32 * 1024 * 1024
    maximum_watched_paths: int = 20_000

    def __post_init__(self):
        for name in ("request_timeout_seconds", "response_deadline_seconds", "listing_timeout_seconds",
                     "version_timeout_seconds"):
            value = getattr(self, name)
            _refuse_unless(type(value) in (int, float) and math.isfinite(value) and 0 < value <= 600,
                           RefusalCode.INVALID_LIMITS)
        for name in ("maximum_json_bytes", "maximum_body_bytes", "maximum_listing_bytes", "maximum_watched_paths"):
            _refuse_unless(type(getattr(self, name)) is int and getattr(self, name) >= 1, RefusalCode.INVALID_LIMITS)


# ---------------------------------------------------------------------------
# Names and rendering
# ---------------------------------------------------------------------------

def native_name(identity: str) -> str:
    """Map a service identity to the name rule that Agent Skills clients document."""
    _refuse_unless(isinstance(identity, str) and len(identity) <= MAXIMUM_IDENTITY_CHARACTERS
                   and IDENTITY_PATTERN.fullmatch(identity) is not None,
                   RefusalCode.IDENTITY_HAS_NO_NATIVE_NAME)
    name = re.sub(r"[._]", "-", identity.lower())
    _refuse_unless(len(name) <= MAXIMUM_NATIVE_NAME_CHARACTERS and NATIVE_NAME_PATTERN.fullmatch(name) is not None,
                   RefusalCode.IDENTITY_HAS_NO_NATIVE_NAME)
    return name


def single_printable_line(text: str) -> str:
    cleaned = "".join(character if character.isprintable() else " " for character in text)
    return " ".join(cleaned.split())


def render_skill_header(name: str, purpose: str) -> tuple[bytes, bool]:
    """Generated frontmatter. The served body follows it byte for byte.

    The service does not declare the format of a body in a typed field, so the
    tool does not guess whether a body already carries frontmatter.
    """
    description = single_printable_line(purpose)
    _refuse_unless(bool(description), RefusalCode.PURPOSE_HAS_NO_PRINTABLE_TEXT)
    truncated = len(description) > MAXIMUM_DESCRIPTION_CHARACTERS
    description = description[:MAXIMUM_DESCRIPTION_CHARACTERS].rstrip()
    # A JSON string of printable characters is also a YAML double-quoted scalar. The name is quoted
    # too: both observed client versions drop a skill whose bare name reads as a number or a boolean.
    header = ("---\nname: " + json.dumps(name) + "\ndescription: " + json.dumps(description, ensure_ascii=False)
              + "\n---\n")
    return header.encode("utf-8"), truncated


RENDERERS = {SKILL_FILE_RENDERING: render_skill_header}


# ---------------------------------------------------------------------------
# Path confinement
# ---------------------------------------------------------------------------

def validate_relative_parts(parts: tuple[str, ...]) -> None:
    """Refuse traversal, absolute paths and separators before any file access."""
    _refuse_unless(bool(parts), RefusalCode.PATH_TRAVERSAL_REFUSED)
    for part in parts:
        _refuse_unless(isinstance(part, str) and part not in ("", ".", "..") and "/" not in part
                       and "\\" not in part and "\x00" not in part and not os.path.isabs(part)
                       and not PureWindowsPath(part).anchor,
                       RefusalCode.PATH_TRAVERSAL_REFUSED)


def _refusal_for_open_error(error: OSError, name: str, directory: int) -> InstallRefusal:
    if error.errno in (errno.ELOOP, errno.ENOTDIR, errno.EMLINK):
        try:
            mode = os.lstat(name, dir_fd=directory).st_mode
        except OSError:
            return InstallRefusal(RefusalCode.PATH_NOT_USABLE)
        if stat.S_ISLNK(mode):
            return InstallRefusal(RefusalCode.SYMBOLIC_LINK_REFUSED)
        return InstallRefusal(RefusalCode.PATH_COMPONENT_NOT_A_DIRECTORY)
    return InstallRefusal(RefusalCode.PATH_NOT_USABLE, type(error).__name__)


def require_confined_file_operations() -> int:
    """The platform flags that open a path without following a link, else a refusal."""
    _refuse_unless(NO_FOLLOW_FLAG is not None and hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NONBLOCK")
                   and all(operation in os.supports_dir_fd
                           for operation in (os.open, os.mkdir, os.link, os.unlink, os.access)),
                   RefusalCode.CONFINED_FILE_OPERATIONS_UNAVAILABLE)
    return NO_FOLLOW_FLAG | getattr(os, "O_CLOEXEC", 0)


def _open_directory(name, directory: int | None = None) -> int:
    flags = require_confined_file_operations() | os.O_RDONLY | os.O_DIRECTORY
    return os.open(name, flags) if directory is None else os.open(name, flags, dir_fd=directory)


def _walk_to_directory(root: Path, directories: tuple[str, ...], *, create: bool) -> int | None:
    """Open each directory below the root without following any link.

    Returns None when a directory is absent and may not be created.
    """
    try:
        current = _open_directory(str(root))
    except OSError:
        raise InstallRefusal(RefusalCode.TARGET_NOT_A_REAL_DIRECTORY) from None
    try:
        for name in directories:
            if create:
                try:
                    os.mkdir(name, 0o755, dir_fd=current)
                except FileExistsError:
                    pass
                except OSError as error:
                    raise InstallRefusal(RefusalCode.PATH_NOT_USABLE, type(error).__name__) from None
            try:
                following = _open_directory(name, current)
            except FileNotFoundError:
                following = None
            except OSError as error:
                raise _refusal_for_open_error(error, name, current) from None
            os.close(current)
            current = following
            if current is None:
                return None
        return current
    except BaseException:
        if current is not None:
            os.close(current)
        raise


def _read_regular_file(name: str, directory: int, maximum_bytes: int) -> bytes | None:
    """Bytes of an existing regular file, None when absent. Never follows a link."""
    flags = require_confined_file_operations() | os.O_RDONLY | os.O_NONBLOCK
    try:
        descriptor = os.open(name, flags, dir_fd=directory)
    except FileNotFoundError:
        return None
    except OSError as error:
        refusal = _refusal_for_open_error(error, name, directory)
        if refusal.code is RefusalCode.PATH_COMPONENT_NOT_A_DIRECTORY:
            refusal = InstallRefusal(RefusalCode.EXISTING_PATH_NOT_A_REGULAR_FILE)
        raise refusal from None
    try:
        _refuse_unless(stat.S_ISREG(os.fstat(descriptor).st_mode), RefusalCode.EXISTING_PATH_NOT_A_REGULAR_FILE)
        chunks, remaining = [], maximum_bytes + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(remaining, 1 << 20))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_confined_file(root: Path, parts: tuple[str, ...], maximum_bytes: int) -> bytes | None:
    """Inspect a path under the root without any effect. None means absent."""
    validate_relative_parts(parts)
    directory = _walk_to_directory(root, parts[:-1], create=False)
    if directory is None:
        return None
    try:
        return _read_regular_file(parts[-1], directory, maximum_bytes)
    finally:
        os.close(directory)


def require_identical_existing(existing: bytes | None, expected: bytes) -> None:
    """An existing file is accepted only when every byte is the same."""
    _refuse_unless(existing is not None and hmac.compare_digest(existing, expected),
                   RefusalCode.DIFFERENT_FILE_EXISTS)


def require_writable_placement(root: Path, directories: tuple[str, ...]) -> None:
    """Refuse before the metered read when the file could not be placed afterwards.

    Nothing is created. The deepest folder that already exists must allow a new
    entry. Every folder on the way is opened without following a link.
    """
    validate_relative_parts(directories)
    try:
        current = _open_directory(str(root))
    except OSError:
        raise InstallRefusal(RefusalCode.TARGET_NOT_A_REAL_DIRECTORY) from None
    try:
        writable = os.access(str(root), os.W_OK | os.X_OK)
        for name in directories:
            try:
                following = _open_directory(name, current)
            except FileNotFoundError:
                break
            except OSError as error:
                raise _refusal_for_open_error(error, name, current) from None
            writable = os.access(name, os.W_OK | os.X_OK, dir_fd=current)
            os.close(current)
            current = following
        _refuse_unless(writable, RefusalCode.TARGET_FOLDER_NOT_WRITABLE)
    finally:
        os.close(current)


def write_confined_file(root: Path, parts: tuple[str, ...], data: bytes) -> bool:
    """Create the file under the root. True when written, False when identical.

    The bytes go to a new partial name in the same folder first. The final name
    appears only through a hard link to the finished file, so a stopped run never
    leaves a cut file under the name that the client discovers. A hard link never
    replaces an existing name.
    """
    validate_relative_parts(parts)
    directory = _walk_to_directory(root, parts[:-1], create=True)
    # Without a directory handle the next open would resolve against the working folder.
    _refuse_unless(directory is not None, RefusalCode.PATH_NOT_USABLE)
    partial = "." + parts[-1] + "." + uuid.uuid4().hex + PARTIAL_FILE_SUFFIX
    try:
        flags = require_confined_file_operations() | os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            descriptor = os.open(partial, flags, 0o644, dir_fd=directory)
        except OSError as error:
            raise _refusal_for_open_error(error, partial, directory) from None
        try:
            try:
                view = memoryview(data)
                while view:
                    view = view[os.write(descriptor, view):]
                os.fsync(descriptor)
            except OSError as error:
                raise InstallRefusal(RefusalCode.WRITE_FAILED, type(error).__name__) from None
            finally:
                os.close(descriptor)
            try:
                os.link(partial, parts[-1], src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            except FileExistsError:
                try:
                    existing = _read_regular_file(parts[-1], directory, len(data))
                except InstallRefusal as refusal:
                    if refusal.code is RefusalCode.PATH_NOT_USABLE:
                        refusal = InstallRefusal(RefusalCode.EXISTING_PATH_NOT_A_REGULAR_FILE)
                    raise refusal from None
                require_identical_existing(existing, data)
                return False
            except OSError as error:
                raise InstallRefusal(RefusalCode.WRITE_FAILED, type(error).__name__) from None
        finally:
            try:
                os.unlink(partial, dir_fd=directory)  # Only the partial name this call created.
            except OSError:
                pass
        written = _read_regular_file(parts[-1], directory, len(data))
        _refuse_unless(written is not None and hmac.compare_digest(written, data), RefusalCode.WRITE_FAILED)
        return True
    finally:
        os.close(directory)


# ---------------------------------------------------------------------------
# Service client
# ---------------------------------------------------------------------------

def require_manifest_record_type(value: dict) -> None:
    """Only the manifest record version that this tool knows is read."""
    _refuse_unless(value.get("record_type") == MANIFEST_RECORD_TYPE, RefusalCode.UNSUPPORTED_SERVICE_RECORD)


def require_manifest_identity(manifest_identity: str, requested_identity: str) -> None:
    """A manifest answers for the identity that was asked for, and for no other."""
    _refuse_unless(manifest_identity == requested_identity, RefusalCode.UNSUPPORTED_SERVICE_RECORD)


def require_encodable_text(texts: tuple[str, ...]) -> None:
    """Manifest text is copied into the file header and the report. It must encode as UTF-8."""
    try:
        for text in texts:
            text.encode("utf-8")
    except UnicodeEncodeError:
        raise InstallRefusal(RefusalCode.UNSUPPORTED_SERVICE_RECORD, "text_does_not_encode_as_utf8") from None


@dataclass(frozen=True)
class OfferedItem:
    """Manifest facts for one identity, parsed strictly."""

    identity: str
    kind: str
    purpose: str
    digest: str
    size_bytes: int
    license_name: str
    body_allowed: bool
    source_layer: str
    source_ref: str
    qualification_basis: str

    @classmethod
    def from_manifest(cls, identity: str, value: dict) -> "OfferedItem":
        try:
            item = cls(value["identity"], value["kind"], value["purpose"], value["digest"], value["size_bytes"],
                       value["license"], value["body_allowed"], value["source_layer"], value["source_ref"],
                       value["qualification_basis"])
        except (KeyError, TypeError):
            raise InstallRefusal(RefusalCode.UNSUPPORTED_SERVICE_RECORD) from None
        texts = (item.identity, item.kind, item.purpose, item.digest, item.license_name, item.source_layer,
                 item.source_ref, item.qualification_basis)
        require_manifest_record_type(value)
        _refuse_unless(all(isinstance(text, str) for text in texts), RefusalCode.UNSUPPORTED_SERVICE_RECORD)
        require_manifest_identity(item.identity, identity)
        require_encodable_text(texts)
        _refuse_unless(item.kind in KINDS
                       and DIGEST_PATTERN.fullmatch(item.digest) is not None
                       and type(item.size_bytes) is int and item.size_bytes >= 0
                       and type(item.body_allowed) is bool,
                       RefusalCode.UNSUPPORTED_SERVICE_RECORD)
        return item

    def to_dict(self, source: str) -> dict:
        return {"source": source, "kind": self.kind, "digest": self.digest, "size_bytes": self.size_bytes,
                "license": self.license_name, "license_declared": bool(self.license_name.strip()),
                "body_allowed": self.body_allowed, "source_layer": self.source_layer,
                "source_ref": self.source_ref, "qualification_basis": self.qualification_basis}


@dataclass(frozen=True)
class DownloadedBody:
    data: bytes = field(repr=False)
    header_digest: str
    record_type: str
    http_status: int


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_arguments, **_fields):
        raise InstallRefusal(RefusalCode.REDIRECT_REFUSED)


def service_error_code(data: bytes) -> str:
    """The service's own refusal code when the body is its error record."""
    try:
        value = json.loads(data)
        code = value["error"]["code"] if value.get("record_type") == ERROR_VERSION else ""
    except (*JSON_PARSE_ERRORS, KeyError, TypeError, AttributeError):
        return "unrecognized"
    return code if isinstance(code, str) and ERROR_CODE_PATTERN.fullmatch(code) else "unrecognized"


def service_opener():
    """The key goes to the named origin only: no proxy from the environment and no redirect."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _RefuseRedirect())


def require_within_deadline(deadline: float) -> None:
    """The whole response must arrive before this moment on the monotonic clock."""
    _refuse_unless(time.monotonic() < deadline, RefusalCode.RESPONSE_DEADLINE_PASSED)


def read_bounded(response, bound: int, deadline: float) -> bytes:
    """Read at most bound plus one bytes, and stop when the whole-response deadline passes.

    The extra byte lets the caller tell a response of exactly the bound from a longer one.
    """
    chunks, remaining = [], bound + 1
    while remaining > 0:
        require_within_deadline(deadline)
        chunk = response.read1(min(remaining, RESPONSE_READ_CHUNK_BYTES))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def require_bounded_response(data: bytes, bound: int) -> None:
    _refuse_unless(len(data) <= bound, RefusalCode.RESPONSE_TOO_LARGE)


class ServiceClient:
    """Bounded requests to one origin. Proxies are ignored and redirects refused."""

    def __init__(self, origin: str, key: str, limits: TransferLimits):
        self._origin, self._key, self._limits = origin, key, limits
        self._opener = service_opener()
        self.calls = 0

    def _exchange(self, route: str, payload: dict | None, *, authenticated: bool, maximum_bytes: int):
        """One request. A refusal is read up to the JSON bound so that its code stays readable."""
        fields = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            fields["Content-Type"] = "application/json"
        if authenticated:
            fields["Authorization"] = "Bearer " + self._key
        request = urllib.request.Request(self._origin + route, data=data, headers=fields)
        self.calls += 1
        deadline = time.monotonic() + self._limits.response_deadline_seconds
        try:
            try:
                response = self._opener.open(request, timeout=self._limits.request_timeout_seconds)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                bound = maximum_bytes if response.status == 200 else self._limits.maximum_json_bytes
                return response.status, response.headers, read_bounded(response, bound, deadline)
        except InstallRefusal:
            raise
        except Exception as error:  # Only the type is kept: the text could hold a header value.
            raise InstallRefusal(RefusalCode.SERVICE_UNREACHABLE, type(error).__name__) from None

    def _result(self, route: str, payload: dict | None, *, authenticated: bool = True) -> dict:
        status, _headers, data = self._exchange(route, payload, authenticated=authenticated,
                                                maximum_bytes=self._limits.maximum_json_bytes)
        require_bounded_response(data, self._limits.maximum_json_bytes)
        if status != 200:
            raise InstallRefusal(RefusalCode.SERVICE_REFUSED, str(status) + ":" + service_error_code(data))
        try:
            value = json.loads(data)
            result = value["result"] if value.get("record_type") == RESULT_VERSION else None
        except (*JSON_PARSE_ERRORS, KeyError, TypeError, AttributeError):
            result = None
        _refuse_unless(isinstance(result, dict), RefusalCode.UNSUPPORTED_SERVICE_RECORD)
        return result

    def capabilities(self) -> dict:
        return self._result(CAPABILITIES_ROUTE, None, authenticated=False)

    def search(self, query: str, top_n: int | None, search_mode: str) -> list[dict]:
        payload = {"record_type": RETRIEVAL_REQUEST_VERSION, "query": query}
        if top_n is not None:
            payload["top_n"] = top_n
        if search_mode:
            payload["mode"] = search_mode
        result = self._result(RETRIEVAL_ROUTE, payload)
        hits = result.get("hits")
        _refuse_unless(result.get("record_type") == RETRIEVAL_RESULT_RECORD_TYPE and isinstance(hits, list),
                       RefusalCode.UNSUPPORTED_SERVICE_RECORD)
        require_references_only(result)
        selected = []
        for hit in hits:
            reference = hit.get("reference") if isinstance(hit, dict) else None
            _refuse_unless(isinstance(reference, dict) and isinstance(reference.get("identity"), str)
                           and isinstance(reference.get("body_digest"), str)
                           and DIGEST_PATTERN.fullmatch(reference["body_digest"]) is not None,
                           RefusalCode.UNSUPPORTED_SERVICE_RECORD)
            selected.append({"identity": reference["identity"], "digest": reference["body_digest"]})
        return selected

    def manifest(self, identity: str, expected_digest: str | None) -> OfferedItem:
        payload = {"record_type": PROVISIONING_REQUEST_VERSION, "operation": MANIFEST_OPERATION, "identity": identity}
        if expected_digest is not None:
            payload["expected_digest"] = expected_digest
        return OfferedItem.from_manifest(identity, self._result(PROVISIONING_ROUTE, payload))

    def download(self, item: OfferedItem, request_id: str, maximum_bytes: int) -> DownloadedBody:
        payload = {"record_type": PROVISIONING_REQUEST_VERSION, "operation": READ_OPERATION,
                   "identity": item.identity, "request_id": request_id, "expected_digest": item.digest}
        status, headers, data = self._exchange(DOWNLOAD_ROUTE, payload, authenticated=True,
                                               maximum_bytes=maximum_bytes)
        digests = headers.get_all(DIGEST_HEADER) or []
        kinds = headers.get_all(RECORD_TYPE_HEADER) or []
        return DownloadedBody(data, digests[0] if len(digests) == 1 else "",
                              kinds[0] if len(kinds) == 1 else "", status)


def require_references_only(result: dict) -> None:
    """A search answer must say that it loaded no body. Bodies are read one by one, and metered."""
    _refuse_unless(result.get("bodies_loaded") is False, RefusalCode.UNSUPPORTED_SERVICE_RECORD)


def require_supported_body_format(delivery: dict) -> None:
    """The file rendering is defined for text bodies in UTF-8 only."""
    _refuse_unless(delivery.get("body_format") == SUPPORTED_BODY_FORMAT,
                   RefusalCode.UNSUPPORTED_SERVICE_CAPABILITIES, "body_format")


def require_supported_service(capabilities: dict) -> int:
    """Refuse an unknown service contract before any authenticated request.

    Returns the download allowance that the service declares.
    """
    delivery = capabilities.get("delivery")
    _refuse_unless(capabilities.get("record_type") == CAPABILITIES_RECORD_TYPE
                   and capabilities.get("api_version") == SUPPORTED_API_VERSION and isinstance(delivery, dict)
                   and delivery.get("download_endpoint") == DOWNLOAD_ROUTE
                   and type(delivery.get("download_bytes")) is int and delivery["download_bytes"] >= 1,
                   RefusalCode.UNSUPPORTED_SERVICE_CAPABILITIES)
    require_supported_body_format(delivery)
    return delivery["download_bytes"]


# ---------------------------------------------------------------------------
# Guards on one item
# ---------------------------------------------------------------------------

def require_body_permitted(item: OfferedItem) -> None:
    """Do not spend a request on a body that the manifest says this key may not read."""
    _refuse_unless(item.body_allowed is True, RefusalCode.BODY_NOT_PERMITTED)


def require_within_download_allowance(item: OfferedItem, allowance: int) -> None:
    """Do not start a read that is declared larger than the service and this tool allow."""
    _refuse_unless(item.size_bytes <= allowance, RefusalCode.BODY_EXCEEDS_DOWNLOAD_ALLOWANCE)


def require_offer_unchanged(search_digest: str | None, item: OfferedItem) -> None:
    """The manifest must name the digest that the search named."""
    _refuse_unless(search_digest in (None, item.digest), RefusalCode.OFFER_CHANGED)


def require_download_status(download: DownloadedBody) -> None:
    """Any status other than success is the refusal of the service, with its own code."""
    if download.http_status != 200:
        raise InstallRefusal(RefusalCode.SERVICE_REFUSED,
                             str(download.http_status) + ":" + service_error_code(download.data))


def require_download_record_type(download: DownloadedBody) -> None:
    """Only a response of the download record type carries a body."""
    _refuse_unless(download.record_type == DOWNLOAD_RECORD_TYPE, RefusalCode.UNSUPPORTED_SERVICE_RECORD)


def require_successful_download(download: DownloadedBody) -> None:
    require_download_status(download)
    require_download_record_type(download)


def require_header_digest(body_digest: str, download: DownloadedBody) -> None:
    _refuse_unless(DIGEST_PATTERN.fullmatch(download.header_digest) is not None,
                   RefusalCode.DIGEST_HEADER_MISSING_OR_MALFORMED)
    _refuse_unless(hmac.compare_digest(body_digest, download.header_digest),
                   RefusalCode.BODY_DIFFERS_FROM_HEADER_DIGEST)


def require_manifest_digest(body_digest: str, body_bytes: int, item: OfferedItem) -> None:
    _refuse_unless(hmac.compare_digest(body_digest, item.digest), RefusalCode.BODY_DIFFERS_FROM_MANIFEST_DIGEST)
    _refuse_unless(body_bytes == item.size_bytes, RefusalCode.BODY_SIZE_DIFFERS_FROM_MANIFEST)


def require_declared_text_format(data: bytes) -> None:
    """The service declares bodies as text in UTF-8. Other bytes do not belong in a skill file."""
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise InstallRefusal(RefusalCode.BODY_IS_NOT_UTF8_TEXT) from None


def verify_downloaded_body(item: OfferedItem, download: DownloadedBody) -> str:
    """The body must agree with the response header and with the manifest."""
    require_successful_download(download)
    _refuse_unless(len(download.data) <= item.size_bytes, RefusalCode.DOWNLOAD_EXCEEDS_DECLARED_SIZE)
    body_digest = hashlib.sha256(download.data).hexdigest()
    require_header_digest(body_digest, download)
    require_manifest_digest(body_digest, len(download.data), item)
    require_declared_text_format(download.data)
    return body_digest


def existing_header_is_the_generated_one(existing: bytes, header: bytes) -> bool:
    return existing[:len(header)] == header


def existing_file_is_the_expected_one(existing: bytes, header: bytes, item: OfferedItem) -> bool:
    body = existing[len(header):]
    return (existing_header_is_the_generated_one(existing, header) and len(body) == item.size_bytes
            and hmac.compare_digest(hashlib.sha256(body).hexdigest(), item.digest))


def refuse_different_existing_file(existing: bytes | None, header: bytes, item: OfferedItem) -> bool:
    """Decide before the metered read. True means the identical file is already there."""
    if existing is None:
        return False
    _refuse_unless(existing_file_is_the_expected_one(existing, header, item), RefusalCode.DIFFERENT_FILE_EXISTS)
    return True


# ---------------------------------------------------------------------------
# What the client itself reports
# ---------------------------------------------------------------------------

def client_process_environment(key_variable: str, settings: tuple[tuple[str, str], ...]) -> dict:
    """The client process never receives the service key."""
    values = {name: value for name, value in os.environ.items() if name != key_variable}
    values.update(dict(settings))
    return values


def _run_client(command: tuple[str, ...], project: Path, process_environment: dict, timeout: float,
                maximum_bytes: int):
    """Run one client command. Output goes through a regular file, not a pipe.

    With OpenCode 1.17.9 and 1.18.31, a Python subprocess pipe capture of the
    listing held exactly 65,536 bytes with exit code 0. A shell pipe to a fast
    reader delivered the whole listing, and so did a regular file. The cut
    depends on the reader, so this tool uses the regular file.
    """
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        started = time.monotonic()
        completed = subprocess.run(list(command), cwd=str(project), env=process_environment,
                                   stdin=subprocess.DEVNULL, stdout=output, stderr=errors, timeout=timeout)
        elapsed = round(time.monotonic() - started, 3)
        size = output.seek(0, os.SEEK_END)
        output.seek(0)
        return completed.returncode, elapsed, size, output.read(maximum_bytes + 1)


def paths_below(project: Path, roots: tuple[str, ...], maximum_entries: int):
    """Relative paths below the client's native folders. None when there are too many to compare."""
    found = set()
    for root in roots:
        for directory, folder_names, file_names in os.walk(project / root, followlinks=False):
            for name in (*folder_names, *file_names):
                found.add(os.path.relpath(os.path.join(directory, name), project))
                if len(found) > maximum_entries:
                    return None
    return found


def listing_entry_for(entries: list, listing: ListingCommand, absolute_path: str):
    """The entry whose location is exactly the installed file, else None."""
    wanted = os.path.realpath(absolute_path)
    for entry in entries:
        location = entry.get(listing.location_field) if isinstance(entry, dict) else None
        if location_is_the_installed_file(location, wanted):
            return entry
    return None


def location_is_the_installed_file(location, wanted: str) -> bool:
    """A location that the platform cannot resolve, such as one with a NUL, is no match."""
    if not isinstance(location, str) or not os.path.isabs(location):
        return False
    try:
        return os.path.realpath(location) == wanted
    except (ValueError, OSError):
        return False


def describe_client_report(entries: list, listing: ListingCommand, record: dict) -> dict:
    entry = listing_entry_for(entries, listing, record["absolute_path"])
    names = [row.get(listing.name_field) for row in entries if isinstance(row, dict)]
    if entry is None:
        return {"reported": False, "same_name_reported_from_another_location": record["native_name"] in names}
    content = entry.get(listing.content_field)
    content_digest = None
    if isinstance(content, str):
        try:
            content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        except UnicodeEncodeError:
            content_digest = None
    reported_name = entry.get(listing.name_field)
    return {"reported": True, "reported_name": reported_name if isinstance(reported_name, str) else None,
            "name_matches": reported_name == record["native_name"],
            "reported_content_sha256": content_digest,
            "content_matches_served_body": None if content_digest is None
            else hmac.compare_digest(content_digest, record["body_sha256"])}


def reported_with_same_name_and_content(client_report: dict) -> bool:
    """The headline fact: the client names that exact file, under that name, with the served content."""
    return (client_report["reported"] is True and client_report.get("name_matches") is True
            and client_report.get("content_matches_served_body") is True)


def observe_client_listing(profile: ClientLayoutProfile, command_prefix: tuple[str, ...] | None, project: Path,
                           key_variable: str, limits: TransferLimits) -> tuple[dict, list | None]:
    """Run the listing command once. Returns the observation and the parsed entries."""
    observation = {"record_type": LISTING_RECORD_TYPE, "client_kind": profile.client_kind,
                   "state": None, "model_turns_started": 0, "client_version": None,
                   "layout_observed_with_this_version": None, "command_arguments": None,
                   "exit_code": None, "elapsed_seconds": None, "output_bytes": None, "entries": None,
                   "paths_created_by_the_client_process": None}
    if profile.listing is None:
        observation["state"] = ListingState.CLIENT_OFFERS_NO_LISTING
        return observation, None
    if command_prefix is None:
        found = shutil.which(profile.executable_name)
        if found is None:
            observation["state"] = ListingState.EXECUTABLE_NOT_FOUND
            return observation, None
        command_prefix = (found,)
    process_environment = client_process_environment(key_variable, profile.listing.process_settings)
    observation["command_arguments"] = list(profile.listing.arguments)
    before = paths_below(project, profile.native_roots(), limits.maximum_watched_paths)
    try:
        return _observe(profile, command_prefix, project, process_environment, limits, observation)
    finally:
        # The client process is not this tool's code. What it adds to the project is shown, not hidden.
        after = paths_below(project, profile.native_roots(), limits.maximum_watched_paths)
        if before is not None and after is not None:
            observation["paths_created_by_the_client_process"] = sorted(after - before)[:50]


def listing_exceeds_bound(size: int, limits: TransferLimits) -> bool:
    return size > limits.maximum_listing_bytes


def parse_listing_entries(data: bytes):
    """The entries of a listing, or None when it cannot be read.

    Nesting depth is a parse failure like any other. A listing that does not
    parse is unknown. It is never read as "not reported".
    """
    try:
        entries = json.loads(data.decode("utf-8"))
    except JSON_PARSE_ERRORS:  # UnicodeDecodeError is a ValueError.
        return None
    return entries if isinstance(entries, list) else None


def _observe(profile, command_prefix, project, process_environment, limits, observation):
    try:
        _code, _elapsed, _size, text = _run_client((*command_prefix, *profile.version_arguments), project,
                                                   process_environment, limits.version_timeout_seconds, 4096)
        line = text.decode("utf-8", errors="replace").strip().splitlines()[:1]
        if line and VERSION_PATTERN.fullmatch(line[0]):
            observation["client_version"] = line[0]
            observation["layout_observed_with_this_version"] = line[0] in profile.observed_client_versions
    except (subprocess.TimeoutExpired, OSError):
        pass  # An unknown version stays unknown. The listing below decides the state.
    try:
        code, elapsed, size, data = _run_client((*command_prefix, *profile.listing.arguments), project,
                                                process_environment, limits.listing_timeout_seconds,
                                                limits.maximum_listing_bytes)
    except subprocess.TimeoutExpired:
        observation["state"] = ListingState.TIMED_OUT
        return observation, None
    except OSError:
        observation["state"] = ListingState.EXECUTABLE_NOT_USABLE
        return observation, None
    observation.update({"exit_code": code, "elapsed_seconds": elapsed, "output_bytes": size})
    if code != 0:
        observation["state"] = ListingState.FAILED
        return observation, None
    if listing_exceeds_bound(size, limits):
        observation["state"] = ListingState.TOO_LARGE
        return observation, None
    entries = parse_listing_entries(data)
    if entries is None:
        observation["state"] = ListingState.UNREADABLE
        return observation, None
    observation.update({"state": ListingState.OBSERVED, "entries": len(entries)})
    return observation, entries


# ---------------------------------------------------------------------------
# The request and the run
# ---------------------------------------------------------------------------

def registered_client_kinds() -> tuple[str, ...]:
    """Client identifiers come from the existing recipes registry, not from this tool."""
    try:
        registry = read_client_registry()
        require_supported_client_registry(registry)
        return tuple(row["id"] for row in registry["recipes"])
    except (OSError, *JSON_PARSE_ERRORS, KeyError, TypeError, AttributeError):
        raise InstallRefusal(RefusalCode.CLIENT_REGISTRY_UNREADABLE) from None


def read_client_registry():
    resource = files("loop_engine").joinpath(*CLIENT_RECIPES_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def require_supported_client_registry(registry: dict) -> None:
    """A registry version that this tool does not know is refused, not read as a known one."""
    _refuse_unless(registry.get("record_type") in SUPPORTED_CLIENT_REGISTRY_RECORD_TYPES,
                   RefusalCode.UNSUPPORTED_CLIENT_REGISTRY_VERSION)


OPENCODE_PROFILE = ClientLayoutProfile(
    client_kind="opencode",
    executable_name="opencode",
    locations=(NativeLocation(SKILL_KIND, (".opencode", "skills"), "SKILL.md", SKILL_FILE_RENDERING),),
    unplaced_kinds=(
        ("instruction_file", "client_reads_instruction_files_only_through_files_the_project_owns"),
        ("reusable_code", "code_needs_independent_admission_before_local_use"),
        ("tool", "code_needs_independent_admission_before_local_use"),
    ),
    listing=ListingCommand(
        arguments=("debug", "skill", "--pure"),
        process_settings=(("OPENCODE_CONFIG_CONTENT",
                           json.dumps({"autoupdate": False, "plugin": [], "share": "disabled"})),),
    ),
    version_arguments=("--version",),
    model_turn_subcommands=("run",),
    observed_client_versions=("1.17.9", "1.18.31"),
)

# The verified native skill roots, from the placement research of
# September 22, 2026 (docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
# and the harness file standards record of September 23, 2026: Claude Code
# reads project skills at .claude/skills/<name>/SKILL.md; Codex 0.155.1 reads
# repository skills at .agents/skills/<name>/SKILL.md (with user skills at
# ~/.agents/skills/, which is outside the project and therefore not this
# tool's placement). Neither client offers a no-model listing command that
# this tool can run, so their listing is None and discovery is proved by a
# separate native instance probe, not by this tool.
CLAUDE_CODE_PROFILE = ClientLayoutProfile(
    client_kind="claude-code",
    executable_name="claude",
    locations=(NativeLocation(SKILL_KIND, (".claude", "skills"), "SKILL.md", SKILL_FILE_RENDERING),),
    unplaced_kinds=(
        ("instruction_file", "client_reads_instruction_files_only_through_files_the_project_owns"),
        ("reusable_code", "code_needs_independent_admission_before_local_use"),
        ("tool", "code_needs_independent_admission_before_local_use"),
    ),
    listing=None,
    version_arguments=("--version",),
    model_turn_subcommands=(),
    observed_client_versions=("2.1.280",),
)

CODEX_PROFILE = ClientLayoutProfile(
    client_kind="codex",
    executable_name="codex",
    locations=(NativeLocation(SKILL_KIND, (".agents", "skills"), "SKILL.md", SKILL_FILE_RENDERING),),
    unplaced_kinds=(
        ("instruction_file", "client_reads_instruction_files_only_through_files_the_project_owns"),
        ("reusable_code", "code_needs_independent_admission_before_local_use"),
        ("tool", "code_needs_independent_admission_before_local_use"),
    ),
    listing=None,
    version_arguments=("--version",),
    model_turn_subcommands=("exec",),
    observed_client_versions=("0.155.1",),
)

CLIENT_LAYOUT_PROFILES = {
    OPENCODE_PROFILE.client_kind: OPENCODE_PROFILE,
    CLAUDE_CODE_PROFILE.client_kind: CLAUDE_CODE_PROFILE,
    CODEX_PROFILE.client_kind: CODEX_PROFILE,
}


def layout_profile_for(client_kind: str) -> ClientLayoutProfile:
    _refuse_unless(client_kind in registered_client_kinds(), RefusalCode.UNKNOWN_CLIENT_KIND)
    _refuse_unless(client_kind in CLIENT_LAYOUT_PROFILES, RefusalCode.CLIENT_HAS_NO_LAYOUT_PROFILE)
    return CLIENT_LAYOUT_PROFILES[client_kind]


@dataclass(frozen=True)
class InstallRequest:
    """One validated invocation. Validation has no effect outside this process."""

    origin: str
    key_variable: str
    client_kind: str
    target: Path
    report: Path
    query: str = ""
    identities: tuple[str, ...] = ()
    top_n: int | None = None
    search_mode: str = ""
    client_command: tuple[str, ...] | None = None
    allow_loopback_http: bool = False
    authorized: bool = False
    preview: bool = False
    request_prefix: str = ""
    limits: TransferLimits = field(default_factory=TransferLimits)

    def __post_init__(self):
        _refuse_unless(type(self.authorized) is bool and type(self.preview) is bool
                       and (self.authorized or self.preview), RefusalCode.INSTALL_NOT_AUTHORIZED)
        _refuse_unless(not (self.authorized and self.preview), RefusalCode.PREVIEW_EXCLUDES_AUTHORIZATION)
        try:
            origin = validate_public_url(self.origin, permit_loopback=self.allow_loopback_http is True)
        except (ValueError, TypeError, AttributeError):
            raise InstallRefusal(RefusalCode.INVALID_ORIGIN) from None
        _refuse_unless(urlsplit(origin).path == "" and origin == self.origin, RefusalCode.INVALID_ORIGIN)
        _refuse_unless(isinstance(self.key_variable, str)
                       and VARIABLE_NAME_PATTERN.fullmatch(self.key_variable) is not None,
                       RefusalCode.INVALID_KEY_VARIABLE_NAME)
        object.__setattr__(self, "identities", tuple(self.identities))
        _refuse_unless(bool(self.query) != bool(self.identities), RefusalCode.SELECTION_REQUIRED)
        if self.query:
            _refuse_unless(isinstance(self.query, str) and bool(self.query.strip())
                           and len(self.query.encode("utf-8")) <= MAXIMUM_QUERY_BYTES, RefusalCode.INVALID_QUERY)
        _refuse_unless(self.top_n is None or (type(self.top_n) is int and self.top_n >= 1 and bool(self.query)),
                       RefusalCode.INVALID_SEARCH_LIMIT)
        _refuse_unless(len(set(self.identities)) == len(self.identities), RefusalCode.DUPLICATE_IDENTITY)
        for identity in self.identities:
            native_name(identity)
        _refuse_unless(not self.request_prefix or REQUEST_PREFIX_PATTERN.fullmatch(self.request_prefix) is not None,
                       RefusalCode.INVALID_REQUEST_PREFIX)
        _refuse_unless(isinstance(self.limits, TransferLimits), RefusalCode.INVALID_LIMITS)
        layout_profile_for(self.client_kind)


def resolve_service_key(variable_name: str) -> str:
    """Read the key from the named variable. The value is never printed or recorded."""
    value = os.environ.get(variable_name)
    _refuse_unless(value is not None, RefusalCode.KEY_VARIABLE_NOT_SET)
    _refuse_unless(KEY_VALUE_PATTERN.fullmatch(value) is not None, RefusalCode.KEY_VALUE_NOT_USABLE)
    return value


def refuse_key_on_command_line(key: str, arguments) -> None:
    _refuse_unless(not any(key in str(argument) for argument in arguments), RefusalCode.KEY_ON_COMMAND_LINE)


def real_target_directory(target: Path) -> Path:
    """The target must be a real folder, and the platform must open paths without following links."""
    _refuse_unless(not target.is_symlink() and target.is_dir(), RefusalCode.TARGET_NOT_A_REAL_DIRECTORY)
    require_confined_file_operations()
    return target.resolve(strict=True)


def reserve_report(path: Path) -> int:
    """Create the report exclusively before any request, so a run never replaces one."""
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0), 0o644)
    except FileExistsError:
        raise InstallRefusal(RefusalCode.REPORT_PATH_NOT_NEW) from None
    except OSError as error:
        raise InstallRefusal(RefusalCode.REPORT_PATH_NOT_USABLE, type(error).__name__) from None
    _write_report(descriptor, {"record_type": REPORT_RECORD_TYPE, "complete": False})
    return descriptor


def _write_report(descriptor: int, report: dict) -> None:
    data = (json.dumps(report, indent=2, ensure_ascii=REPORT_ASCII_ONLY) + "\n").encode("utf-8")
    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view):]
    os.fsync(descriptor)


def _new_item(identity: str) -> dict:
    return {"identity": identity, "native_name": None,
            "facts": {"offered": False, "fetched": False, "installed": False, "reported_by_client": None},
            "offer": None, "preview": None, "fetch": None, "install": None, "client_report": None,
            "refusal": None}


def record_selection_before_any_request(persist) -> None:
    """Put the origin, the request prefix and the selection on disk before the first request.

    A run that is stopped during the first request then still names the request
    prefix that a repeat reuses, so the same read is not metered twice.
    """
    persist()


def record_pending_fetch(item: dict, request_id: str, persist) -> None:
    """Write the request identity to the report before the metered read is sent.

    Until a response arrives the outcome is unknown. A stopped run then still
    names the request identity that a repeat can reuse.
    """
    item["fetch"] = {"outcome": FetchOutcome.UNKNOWN, "request_id": request_id, "http_status": None,
                     "header_digest": None, "body_sha256": None, "body_bytes": None}
    persist()


@dataclass(frozen=True)
class ItemJourney:
    """What one item needs from the run. It holds no credential."""

    profile: ClientLayoutProfile
    root: Path
    request_prefix: str
    maximum_body_bytes: int
    preview: bool


def preview_stops_here(journey: ItemJourney) -> bool:
    """A preview ends before the metered read, the file write and the client process."""
    return journey.preview is True


def install_one_item(client: ServiceClient, journey: ItemJourney, selected: dict, item: dict, persist) -> None:
    """Carry one identity as far as its checks allow and record every fact on the way."""
    stage = Stage.SELECTION
    try:
        name = item["native_name"] = native_name(selected["identity"])
        stage = Stage.OFFER
        if selected.get("digest") is not None:
            # The search named it for this key. The manifest below must agree.
            item["facts"]["offered"] = True
            item["offer"] = {"source": "search", "digest": selected["digest"]}
        offered = client.manifest(selected["identity"], selected.get("digest"))
        require_offer_unchanged(selected.get("digest"), offered)
        item["facts"]["offered"] = True
        item["offer"] = offered.to_dict("search_and_manifest" if selected.get("digest") else "manifest")
        location = journey.profile.location_for(offered.kind)
        require_body_permitted(offered)
        require_within_download_allowance(offered, journey.maximum_body_bytes)
        header, truncated = RENDERERS[location.rendering](name, offered.purpose)
        parts = location.relative_parts(name)
        stage = Stage.PLACEMENT
        existing = read_confined_file(journey.root, parts, len(header) + offered.size_bytes)
        already_present = refuse_different_existing_file(existing, header, offered)
        if not already_present:
            require_writable_placement(journey.root, parts[:-1])
        if preview_stops_here(journey):
            item["preview"] = {"record_type": PREVIEW_RECORD_TYPE, "path": "/".join(parts),
                               "identical_file_present": already_present,
                               "metered_body_read_needed": not already_present,
                               "file_bytes": len(header) + offered.size_bytes}
            return
        body_digest = offered.digest
        if already_present:
            item["fetch"] = {"outcome": FetchOutcome.NOT_NEEDED, "request_id": None}
            content, written = existing, False
        else:
            stage = Stage.FETCH
            request_id = (journey.request_prefix + "-"
                          + hashlib.sha256(offered.identity.encode("utf-8")).hexdigest()[:16])
            record_pending_fetch(item, request_id, persist)
            download = client.download(offered, request_id, offered.size_bytes)
            item["fetch"].update({"outcome": FetchOutcome.REFUSED_BY_SERVICE, "http_status": download.http_status,
                                  "header_digest": download.header_digest or None})
            require_download_status(download)
            stage = Stage.VERIFICATION
            item["fetch"].update({"outcome": FetchOutcome.REJECTED_BY_VERIFICATION,
                                  "body_bytes": len(download.data)})
            body_digest = verify_downloaded_body(offered, download)
            item["fetch"].update({"outcome": FetchOutcome.FETCHED_AND_VERIFIED, "body_sha256": body_digest})
            item["facts"]["fetched"] = True
            stage = Stage.PLACEMENT
            content = header + download.data
            written = write_confined_file(journey.root, parts, content)
        item["facts"]["installed"] = True
        item["install"] = {
            "record_type": INSTALL_RECORD_TYPE, "identity": offered.identity, "kind": offered.kind,
            "native_name": name, "body_sha256": body_digest, "body_bytes": offered.size_bytes,
            "path": "/".join(parts), "absolute_path": str(journey.root.joinpath(*parts)),
            "file_sha256": hashlib.sha256(content).hexdigest(), "file_bytes": len(content),
            "body_offset_bytes": len(header), "rendering": location.rendering,
            "description_truncated": truncated, "license": offered.license_name,
            "source_layer": offered.source_layer, "source_ref": offered.source_ref,
            "written_by_this_run": written, "already_present_identical": not written,
            "file_unchanged_at_end_of_run": None}
    except InstallRefusal as refusal:
        item["refusal"] = {"stage": stage, "code": refusal.code, "detail": refusal.detail}


def installed_file_is_unchanged(root: Path, record: dict) -> bool:
    """Read the installed file again through the confined reader and compare it with the install record."""
    try:
        current = read_confined_file(root, tuple(record["path"].split("/")), record["file_bytes"])
    except InstallRefusal:
        return False
    return current is not None and hmac.compare_digest(hashlib.sha256(current).hexdigest(), record["file_sha256"])


def _summarize(report: dict, http_calls: int) -> None:
    items = report["items"]
    facts = [item["facts"] for item in items]
    installed = [item for item in items if item["install"] is not None]
    report["summary"] = {
        "selected": len(facts), "offered": sum(row["offered"] for row in facts),
        "fetched": sum(row["fetched"] for row in facts), "installed": len(installed),
        "written_by_this_run": sum(item["install"]["written_by_this_run"] for item in installed),
        "already_present_identical": sum(item["install"]["already_present_identical"] for item in installed),
        "listed_at_installed_path": sum(item["client_report"] is not None and item["client_report"]["reported"] is True
                                        for item in items),
        "reported_by_client": sum(row["reported_by_client"] is True for row in facts),
        "refused": sum(item["refusal"] is not None for item in items)}
    report["http_calls"] = http_calls
    report["all_selected_installed_and_reported"] = (
        bool(items) and report["service_refusal"] is None and report.get("interrupted_by") is None
        and all(item["facts"]["installed"] and item["facts"]["reported_by_client"] is True
                and item["install"]["file_unchanged_at_end_of_run"] is True for item in items))


def _run_journey(request: InstallRequest, client: ServiceClient, profile: ClientLayoutProfile, root: Path,
                 report: dict, persist) -> None:
    try:
        allowance = min(require_supported_service(client.capabilities()), request.limits.maximum_body_bytes)
        selection = (client.search(request.query, request.top_n, request.search_mode) if request.query
                     else [{"identity": identity, "digest": None} for identity in request.identities])
        journey = ItemJourney(profile, root, report["request_prefix"], allowance, request.preview)
        for selected in selection:
            item = _new_item(selected["identity"])
            report["items"].append(item)
            install_one_item(client, journey, selected, item, persist)
            persist()  # Keep what is known if a later step stops the run.
    except InstallRefusal as refusal:
        report["service_refusal"] = {"code": refusal.code, "detail": refusal.detail}
    installed = [item for item in report["items"] if item["facts"]["installed"]]
    observation = {"record_type": LISTING_RECORD_TYPE, "client_kind": profile.client_kind,
                   "state": ListingState.PREVIEW_ONLY if request.preview else ListingState.NOTHING_INSTALLED,
                   "model_turns_started": 0}
    if installed:
        observation, entries = observe_client_listing(profile, request.client_command, root,
                                                      request.key_variable, request.limits)
        report["listing"] = observation
        persist()
        if entries is not None:
            for item in installed:
                item["client_report"] = describe_client_report(entries, profile.listing, item["install"])
                item["facts"]["reported_by_client"] = reported_with_same_name_and_content(item["client_report"])
        # The client process is not this tool's code. The install record must still describe the file.
        for item in installed:
            unchanged = item["install"]["file_unchanged_at_end_of_run"] = installed_file_is_unchanged(
                root, item["install"])
            if not unchanged:
                item["refusal"] = {"stage": Stage.PLACEMENT, "code": RefusalCode.FILE_CHANGED_AFTER_INSTALL,
                                   "detail": ""}
    report["listing"] = observation


def install_selected_material(request: InstallRequest, key: str, report_descriptor: int) -> dict:
    """Run the whole journey and return the report. The key never enters the report."""
    profile = layout_profile_for(request.client_kind)
    root = real_target_directory(request.target)
    client = ServiceClient(request.origin, key, request.limits)
    request_prefix = request.request_prefix or "native-install-" + uuid.uuid4().hex
    report = {
        "record_type": REPORT_RECORD_TYPE, "complete": False,
        "mode": "preview_without_body_read_or_file_write" if request.preview else "install",
        "observed_at": datetime.now(timezone.utc).isoformat(), "origin": request.origin,
        "client": {"kind": profile.client_kind, "layout_profile": profile.record_type,
                   "layout_observed_with_versions": list(profile.observed_client_versions)},
        "target_folder": str(root),
        "selection": {"by": "query" if request.query else "identities",
                      "query_sha256": hashlib.sha256(request.query.encode("utf-8")).hexdigest() if request.query else None,
                      "query_characters": len(request.query) if request.query else None,
                      "largest_number_of_hits": request.top_n,
                      "identities": list(request.identities)},
        "key": {"source": "environment_variable", "variable_name": request.key_variable, "value_recorded": False},
        "request_prefix": request_prefix, "model_turns_started": 0, "automatic_retries": 0,
        "service_refusal": None, "interrupted_by": None, "items": [], "listing": None,
        "limits": ["A listing shows that the client discovered the file and what content it holds.",
                   "It does not show that a model read, used or benefited from the item.",
                   "The layout was observed with the client versions named above only."]}

    def persist() -> None:
        _write_report(report_descriptor, report)

    record_selection_before_any_request(persist)
    try:
        _run_journey(request, client, profile, root, report, persist)
        _summarize(report, client.calls)
        report["complete"] = True
    except UNEXPECTED_ERRORS as error:  # Only the type is kept: the text could hold foreign content.
        report["interrupted_by"] = {"code": RefusalCode.UNEXPECTED_ERROR, "detail": type(error).__name__}
        try:
            _summarize(report, client.calls)
        except UNEXPECTED_ERRORS:
            report["summary"] = None
        report["all_selected_installed_and_reported"] = False
    return report


class QuietArgumentParser(argparse.ArgumentParser):
    """Refuses a bad command line without repeating any of its values.

    The standard message repeats an unknown argument. A key typed after a wrong
    option would then reach the terminal and every log that keeps its output.
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        print(json.dumps({"refused": RefusalCode.INVALID_ARGUMENTS, "detail": ""}), file=sys.stderr)
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    parser = QuietArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 allow_abbrev=OPTION_ABBREVIATIONS_ALLOWED)
    parser.add_argument("--origin", required=True, help="Exact service origin, without a path.")
    parser.add_argument("--key-variable", required=True, metavar="NAME",
                        help="Name of the variable that holds the service key. Never the key itself.")
    parser.add_argument("--client", required=True, help="Client kind from the client recipes registry.")
    parser.add_argument("--target", required=True, type=Path, help="Existing project folder to install into.")
    parser.add_argument("--report", required=True, type=Path, help="New report path. It may not exist yet.")
    parser.add_argument("--query", default="", help="Search text. Every hit is selected.")
    parser.add_argument("--identity", action="append", default=[], help="Explicit identity. Repeatable.")
    parser.add_argument("--top-n", type=int, default=None, help="Largest number of search hits to select.")
    parser.add_argument("--search-mode", default="", help="Passed to the service as given.")
    parser.add_argument("--client-executable", type=Path, default=None, help="Client binary to ask for its listing.")
    parser.add_argument("--request-prefix", default="",
                        help="Reuse the prefix of an earlier report to repeat the same read requests.")
    parser.add_argument("--allow-loopback-http", action="store_true", help="Permit plain HTTP to a loopback address.")
    parser.add_argument("--authorize-install", action="store_true",
                        help="Approve metered body reads, file writes under the target and one listing process.")
    parser.add_argument("--preview", action="store_true",
                        help="Only show what would be selected: no body read, no file write, no client process.")
    return parser


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(arguments)
    descriptor = None
    try:
        request = InstallRequest(
            origin=args.origin, key_variable=args.key_variable, client_kind=args.client, target=args.target,
            report=args.report, query=args.query, identities=tuple(args.identity), top_n=args.top_n,
            search_mode=args.search_mode, allow_loopback_http=args.allow_loopback_http,
            client_command=None if args.client_executable is None else (os.path.abspath(args.client_executable),),
            authorized=args.authorize_install, preview=args.preview, request_prefix=args.request_prefix)
        key = resolve_service_key(request.key_variable)
        refuse_key_on_command_line(key, arguments)
        real_target_directory(request.target)
        descriptor = reserve_report(request.report)
    except InstallRefusal as refusal:
        # Argument values are never repeated here: one of them could be a pasted key.
        print(json.dumps({"refused": refusal.code, "detail": refusal.detail}), file=sys.stderr)
        return 2
    try:
        try:
            report = install_selected_material(request, key, descriptor)
        except InstallRefusal as refusal:
            report = {"record_type": REPORT_RECORD_TYPE, "complete": False,
                      "interrupted_by": {"code": refusal.code, "detail": refusal.detail}}
        try:
            _write_report(descriptor, report)
        except UNEXPECTED_ERRORS as error:
            # The last complete write stays on disk when this one cannot be made.
            report = {"record_type": REPORT_RECORD_TYPE, "complete": False,
                      "interrupted_by": {"code": RefusalCode.UNEXPECTED_ERROR, "detail": type(error).__name__}}
    finally:
        os.close(descriptor)
    if report.get("interrupted_by") is not None:
        print(json.dumps({"refused": report["interrupted_by"]["code"],
                          "detail": report["interrupted_by"]["detail"], "report": str(request.report)}),
              file=sys.stderr)
        return 1
    print(json.dumps({"record_type": REPORT_RECORD_TYPE, "mode": report["mode"], **report["summary"],
                      "listing_state": report["listing"]["state"],
                      "all_selected_installed_and_reported": report["all_selected_installed_and_reported"],
                      "report": str(request.report)}))
    if request.preview:
        # A preview succeeds when every selected item could be installed. It installs nothing.
        return 0 if report["items"] and report["service_refusal"] is None and not report["summary"]["refused"] else 1
    return 0 if report["all_selected_installed_and_reported"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
