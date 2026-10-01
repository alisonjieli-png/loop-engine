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
from dataclasses import asdict, dataclass, field
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
from loop_engine.core.provisioning_server import (
    TIERED_MANIFEST_RECORD_TYPE as MANIFEST_RECORD_TYPE, ProvisioningItemBinding, ProvisioningError,
)
from loop_engine.core.service_runtime.http import (
    ERROR_VERSION, MANIFEST_OPERATION, TIERED_PROVISIONING_REQUEST_VERSION as PROVISIONING_REQUEST_VERSION,
    READ_OPERATION, RESULT_VERSION, RETRIEVAL_REQUEST_VERSION, STEP_EFFECTS,
)
from loop_engine.core.service_runtime.http_auth import validate_public_url

REPORT_RECORD_TYPE = "native_material_install_report/v1"
INSTALL_RECORD_TYPE = "native_material_install_record/v1"
PREVIEW_RECORD_TYPE = "native_material_install_preview/v1"
LAYOUT_PROFILE_RECORD_TYPE = "native_client_layout_profile/v3"
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
    NATIVE_PACKAGE_REFUSED = "native_package_refused"
    NATIVE_PACKAGE_PLAN_REQUIRED = "native_package_plan_required"
    FILE_MODE_MISMATCH = "file_mode_mismatch"


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
    package_binding: NativePackageBinding | None = None
    record_type: str = LAYOUT_PROFILE_RECORD_TYPE

    def __post_init__(self):
        _refuse_unless(self.package_binding is None or isinstance(self.package_binding, NativePackageBinding),
                       RefusalCode.INVALID_LAYOUT_PROFILE)
        placed = [location.served_kind for location in self.locations]
        if self.package_binding is not None:
            _refuse_unless(self.package_binding.runtime.client_kind == self.client_kind, RefusalCode.INVALID_LAYOUT_PROFILE)
            # A package loader is qualified at one exact client version. A profile built from a registered
            # one must not carry that profile's other observed versions as evidence for the package loader.
            _refuse_unless(self.observed_client_versions == (self.package_binding.runtime.exact_version,),
                           RefusalCode.INVALID_LAYOUT_PROFILE, "package_loader_evidence_version_mismatch")
            placed.append(self.package_binding.served_kind)
        unplaced = [kind for kind, _reason in self.unplaced_kinds]
        _refuse_unless(self.record_type == LAYOUT_PROFILE_RECORD_TYPE and bool(self.client_kind)
                       and bool(self.executable_name) and len(set(placed)) == len(placed)
                       and sorted(placed + unplaced) == sorted(KINDS),
                       RefusalCode.INVALID_LAYOUT_PROFILE)
        refuse_model_turn_subcommand(self.version_arguments, self.model_turn_subcommands)
        if self.listing is not None:
            refuse_model_turn_subcommand(self.listing.arguments, self.model_turn_subcommands)

    def location_for(self, kind: str) -> NativeLocation:
        if self.package_binding is not None and kind == self.package_binding.served_kind:
            raise InstallRefusal(RefusalCode.NATIVE_PACKAGE_PLAN_REQUIRED)
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


def write_confined_file(root: Path, parts: tuple[str, ...], data: bytes, *, mode: int | None = None) -> bool:
    """Create the file under the root. True when written, False when identical.

    The bytes go to a new partial name in the same folder first. The final name
    appears only through a hard link to the finished file, so a stopped run never
    leaves a cut file under the name that the client discovers. A hard link never
    replaces an existing name.
    """
    validate_relative_parts(parts)
    _refuse_unless(mode is None or (type(mode) is int and mode in (0o444, 0o644, 0o664)),
                   RefusalCode.FILE_MODE_MISMATCH)
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
                if mode is not None:
                    os.fchmod(descriptor, mode)
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
                if mode is not None:
                    info = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
                    _refuse_unless(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == mode,
                                   RefusalCode.FILE_MODE_MISMATCH)
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
    declared_effects: tuple[str, ...] = ()

    @classmethod
    def from_manifest(cls, identity: str, value: dict) -> "OfferedItem":
        try:
            item = cls(value["identity"], value["kind"], value["purpose"], value["digest"], value["size_bytes"],
                       value["license"], value["body_allowed"], value["source_layer"], value["source_ref"],
                       value["qualification_basis"], service_effects(value["declared_effects"]))
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
                "source_ref": self.source_ref, "qualification_basis": self.qualification_basis,
                "declared_effects": list(self.declared_effects)}


def service_effects(value) -> tuple[str, ...]:
    """Declared metadata effects never supply the caller's execution authority."""
    _refuse_unless(type(value) in (list, tuple) and all(type(effect) is str for effect in value)
                   and len(value) == len(set(value)) and set(value) <= set(STEP_EFFECTS),
                   RefusalCode.UNSUPPORTED_SERVICE_RECORD, "effect_selection_invalid")
    return tuple(value)


def selected_package(summary, served_digest):
    """Read the selected hit's authenticated package summary, never infer it from body text."""
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage
    from loop_engine.core.service_runtime.records import ServiceRuntimeError
    _refuse_unless(type(summary) is dict and set(summary) == {"body_form", "package_digest", "files"},
                   RefusalCode.UNSUPPORTED_SERVICE_RECORD, "package_summary_required")
    try:
        package = CataloguePackage.from_dict({key: summary[key] for key in ("body_form", "files")})
    except (ServiceRuntimeError, TypeError, ValueError):
        raise InstallRefusal(RefusalCode.UNSUPPORTED_SERVICE_RECORD, "package_summary_invalid") from None
    _refuse_unless(package.package_digest == summary["package_digest"]
                   and package.served_digest == served_digest
                   and [entry.to_dict() for entry in package.files] == summary["files"],
                   RefusalCode.UNSUPPORTED_SERVICE_RECORD, "package_summary_binding_mismatch")
    paths = [entry.path.casefold() for entry in package.files]
    _refuse_unless(not any(other.startswith(path + "/") for path in paths for other in paths),
                   RefusalCode.UNSUPPORTED_SERVICE_RECORD, "package_path_collision")
    return package


def selected_reference(value):
    """Read the exact current binding contract through its existing typed owner."""
    _refuse_unless(type(value) is dict and set(value) == {
        "record_type", "identity", "source_layer", "source_ref", "body_digest", "descriptor_digest"},
        RefusalCode.UNSUPPORTED_SERVICE_RECORD, "reference_binding_invalid")
    try:
        return ProvisioningItemBinding(**value)
    except (ProvisioningError, TypeError, ValueError):
        raise InstallRefusal(RefusalCode.UNSUPPORTED_SERVICE_RECORD, "reference_binding_invalid") from None


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

    def __init__(self, origin: str, key: str, limits: TransferLimits, *, authority_effects: tuple[str, ...] = ()):
        self._origin, self._key, self._limits = origin, key, limits
        self.authority_effects = service_effects(authority_effects)
        self.download_allowance = None
        self.maximum_search_results = None
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
        self.download_allowance = None
        self.maximum_search_results = None
        capabilities = self._result(CAPABILITIES_ROUTE, None, authenticated=False)
        self.download_allowance = min(require_supported_service(capabilities, self.authority_effects),
                                      self._limits.maximum_body_bytes)
        self.maximum_search_results = min(50, capabilities["limits"]["search_results"])
        return capabilities

    def _selection(self) -> dict:
        _refuse_unless(self.download_allowance is not None, RefusalCode.UNSUPPORTED_SERVICE_CAPABILITIES,
                       "handshake_required")
        return {"authority_effects": list(self.authority_effects)}

    def search(self, query: str, top_n: int | None, search_mode: str) -> list[dict]:
        payload = {"record_type": RETRIEVAL_REQUEST_VERSION, "query": query, **self._selection()}
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
            binding = selected_reference(hit.get("reference") if isinstance(hit, dict) else None)
            effects = service_effects(hit.get("declared_effects"))
            _refuse_unless(set(effects) <= set(self.authority_effects) and "package" in hit,
                           RefusalCode.UNSUPPORTED_SERVICE_RECORD, "selection_policy_mismatch")
            if hit["package"] is not None:
                selected_package(hit["package"], binding.body_digest)
            _refuse_unless(not any(row["identity"] == binding.identity for row in selected),
                           RefusalCode.UNSUPPORTED_SERVICE_RECORD, "duplicate_selection")
            selected.append({"identity": binding.identity, "digest": binding.body_digest,
                             "package": hit["package"], "declared_effects": effects})
        return selected

    def resolve_identity_selection(self, identity: str, expected_digest: str) -> dict:
        """Bounded current metadata lookup, with exact identity/digest matching and no body fallback."""
        _refuse_unless(self.maximum_search_results is not None,
                       RefusalCode.UNSUPPORTED_SERVICE_CAPABILITIES, "handshake_required")
        hits = self.search(identity, self.maximum_search_results, "lexical")
        matches = [hit for hit in hits if hit["identity"] == identity and hit["digest"] == expected_digest]
        _refuse_unless(len(matches) == 1, RefusalCode.UNSUPPORTED_SERVICE_RECORD,
                       "exact_identity_metadata_unavailable")
        return matches[0]

    def manifest(self, identity: str, expected_digest: str | None) -> OfferedItem:
        payload = {"record_type": PROVISIONING_REQUEST_VERSION, "operation": MANIFEST_OPERATION,
                   "identity": identity, **self._selection()}
        if expected_digest is not None:
            payload["expected_digest"] = expected_digest
        item = OfferedItem.from_manifest(identity, self._result(PROVISIONING_ROUTE, payload))
        _refuse_unless(set(item.declared_effects) <= set(self.authority_effects),
                       RefusalCode.UNSUPPORTED_SERVICE_RECORD, "selection_policy_mismatch")
        return item

    def download(self, item: OfferedItem, request_id: str, maximum_bytes: int, *, path: str | None = None) -> DownloadedBody:
        payload = {"record_type": PROVISIONING_REQUEST_VERSION, "operation": READ_OPERATION,
                   "identity": item.identity, "request_id": request_id, "expected_digest": item.digest,
                   **self._selection()}
        _refuse_unless(type(maximum_bytes) is int and 0 <= maximum_bytes <= self.download_allowance,
                       RefusalCode.RESPONSE_TOO_LARGE)
        if path is not None:
            from loop_engine.core.service_runtime.catalogue_packages import placement_path
            payload["path"] = placement_path(path)
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


def require_supported_service(capabilities: dict, authority_effects: tuple[str, ...] = ()) -> int:
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
    library, retrieval = capabilities.get("library"), capabilities.get("retrieval")
    _refuse_unless(isinstance(library, dict) and isinstance(retrieval, dict)
                   and isinstance(library.get("provisioning_request_record_types"), list)
                   and PROVISIONING_REQUEST_VERSION in library["provisioning_request_record_types"]
                   and retrieval.get("request_record_type") == RETRIEVAL_REQUEST_VERSION
                   and isinstance(library.get("step_effects"), list)
                   and all(type(effect) is str for effect in library["step_effects"])
                   and set(authority_effects) <= set(library["step_effects"])
                   and delivery.get("package_files") == "download_by_path",
                   RefusalCode.UNSUPPORTED_SERVICE_CAPABILITIES, "current_wire_contract_required")
    limits = capabilities.get("limits")
    _refuse_unless(isinstance(limits, dict) and type(limits.get("search_results")) is int
                   and limits["search_results"] >= 1,
                   RefusalCode.UNSUPPORTED_SERVICE_CAPABILITIES, "search_limit_required")
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


# ---------------------------------------------------------------------------
# Candidate complete-package compilation at the existing material_install_layout edge.
# No registered layout enables this branch yet. Planning/staging never launches a client.
# ---------------------------------------------------------------------------

NATIVE_PREVIEW_RECORD_TYPE = "native_material_install_preview/v3"
NATIVE_STAGE_RECORD_TYPE = "native_material_install_record/v3"
NATIVE_FILE_MODES = (0o444, 0o644, 0o664)


def _native_require(condition, detail):
    _refuse_unless(condition, RefusalCode.NATIVE_PACKAGE_REFUSED, detail)


def _native_effects(values):
    from loop_engine.core.facets import EFFECTS
    _native_require(type(values) is tuple and all(type(value) is str for value in values)
                    and len(set(values)) == len(values)
                    and set(values) <= set(EFFECTS) and not ("pure" in values and len(values) > 1),
                    "effects_invalid")


def _native_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class NativeClientBinding:
    """Exact host-observed client/configuration/dependency identities; no install authority."""
    client_kind: str
    interface: str
    exact_version: str
    operating_system: str
    architecture: str
    executable_digest: str
    effective_configuration_digest: str
    dependencies: tuple[tuple[str, str], ...]

    def __post_init__(self):
        _native_require((self.client_kind, self.interface) in (("opencode", "cli"), ("pi", "api"))
                        and self.operating_system == "linux"
                        and self.architecture == "x86_64" and isinstance(self.exact_version, str)
                        and VERSION_PATTERN.fullmatch(self.exact_version), "client_binding_invalid")
        _native_require(all(isinstance(value, str) and DIGEST_PATTERN.fullmatch(value)
                            for value in (self.executable_digest, self.effective_configuration_digest)),
                        "client_binding_invalid")
        _native_require(type(self.dependencies) is tuple and bool(self.dependencies)
                        and all(type(row) is tuple and len(row) == 2 and isinstance(row[0], str) and row[0]
                                and isinstance(row[1], str) and DIGEST_PATTERN.fullmatch(row[1])
                                for row in self.dependencies)
                        and len({row[0] for row in self.dependencies}) == len(self.dependencies),
                        "dependency_binding_invalid")


@dataclass(frozen=True)
class NativePackageProjection:
    """An exact package tree and explicit placement modes, independent of ambient file modes."""
    identity: str
    package_digest: str
    target_root: tuple[str, ...]
    file_modes: tuple[tuple[str, int], ...]

    def __post_init__(self):
        from loop_engine.core.service_runtime.catalogue_packages import placement_path
        _native_require(isinstance(self.identity, str) and IDENTITY_PATTERN.fullmatch(self.identity)
                        and isinstance(self.package_digest, str) and DIGEST_PATTERN.fullmatch(self.package_digest),
                        "package_projection_invalid")
        _native_require(type(self.target_root) is tuple, "package_projection_invalid")
        if self.target_root:
            validate_relative_parts(self.target_root)
        _native_require(type(self.file_modes) is tuple
                        and all(type(row) is tuple and len(row) == 2 and isinstance(row[0], str)
                                for row in self.file_modes), "file_mode_inventory_mismatch")
        for path, mode in self.file_modes:
            placement_path(path)
            _native_require(type(mode) is int and mode in NATIVE_FILE_MODES, "file_mode_unsupported")
        _native_require(len({row[0] for row in self.file_modes}) == len(self.file_modes), "file_mode_inventory_mismatch")


@dataclass(frozen=True)
class NativePackageBinding:
    """One qualified loader shape's candidate projections and distinct effect phases."""
    runtime: NativeClientBinding
    loader: str
    projections: tuple[NativePackageProjection, ...]
    entrypoint_target: str
    supported_roles: tuple[str, ...]
    load_effects: tuple[str, ...]
    invocation_effects: tuple[str, ...]
    read_only_mounts: tuple[tuple[str, str], ...] = ()
    dependency_mounts: tuple[tuple[str, str], ...] = ()
    served_kind: str = "tool"

    def __post_init__(self):
        from loop_engine.core.service_runtime.catalogue_packages import FILE_ROLES, placement_path
        _native_require(isinstance(self.runtime, NativeClientBinding)
                        and self.loader in ("opencode_project_tool/v1", "pi_project_extension/v1")
                        and self.served_kind == "tool", "native_loader_unsupported")
        expected = ".opencode/tools/" if self.loader == "opencode_project_tool/v1" else ".pi/extensions/"
        _native_require(self.runtime.client_kind == ("opencode" if self.loader.startswith("opencode") else "pi")
                        and self.entrypoint_target.startswith(expected)
                        and "/" not in self.entrypoint_target[len(expected):]
                        and self.entrypoint_target.endswith((".ts", ".js")), "native_loader_unsupported")
        placement_path(self.entrypoint_target)
        _native_require(type(self.projections) is tuple and 1 <= len(self.projections) <= 8
                        and all(isinstance(p, NativePackageProjection) for p in self.projections)
                        and len({p.identity for p in self.projections}) == len(self.projections), "package_projection_invalid")
        _native_require(type(self.supported_roles) is tuple and bool(self.supported_roles)
                        and all(type(role) is str for role in self.supported_roles)
                        and set(self.supported_roles) <= set(FILE_ROLES), "unsupported_mandatory_role")
        _native_effects(self.load_effects)
        _native_require("reads_fs" in self.load_effects, "native_import_effect_missing")
        _native_effects(self.invocation_effects)
        _native_require(type(self.read_only_mounts) is tuple
                        and all(type(row) is tuple and len(row) == 2
                                and row[0] in {p.identity for p in self.projections} and row[1] == "/package"
                                for row in self.read_only_mounts)
                        and len({row[1] for row in self.read_only_mounts}) == len(self.read_only_mounts),
                        "runtime_mount_unsupported")
        _native_require(type(self.dependency_mounts) is tuple
                        and all(type(row) is tuple and len(row) == 2
                                and row[0] in dict(self.runtime.dependencies) and isinstance(row[1], str)
                                for row in self.dependency_mounts)
                        and len({row[1] for row in self.dependency_mounts}) == len(self.dependency_mounts),
                        "dependency_mount_invalid")
        for _identity, target in self.dependency_mounts:
            validate_relative_parts(tuple(target.split("/")))
            _native_require(self.runtime.client_kind == "opencode"
                            and target.startswith(".opencode/node_modules/")
                            and len(target.split("/")) == 3, "dependency_mount_invalid")


@dataclass(frozen=True)
class NativePackageInput:
    identity: str
    package: object
    payloads: tuple[tuple[str, bytes], ...] = field(repr=False)
    declared_effects: tuple[str, ...] = ()

    def __post_init__(self):
        from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage
        _native_require(type(self.identity) is str and IDENTITY_PATTERN.fullmatch(self.identity)
                        and isinstance(self.package, CataloguePackage) and type(self.payloads) is tuple,
                        "package_input_invalid")
        _native_effects(self.declared_effects)


def fetch_selected_native_package(client, selected, request_id, record, persist):
    """Fetch one explicitly selected tool package; every file shares one journaled logical read.

    This reuses the service client and existing canonical package parser. It
    neither writes a package tree nor grants load/invocation permission.
    The caller must persist the supplied record before a metered request.
    No transport error is retried automatically.
    """
    from dataclasses import replace
    _native_require(isinstance(client, ServiceClient) and type(selected) is dict
                    and type(record) is dict and not record and callable(persist), "package_fetch_input_invalid")
    _native_require(type(selected.get("identity")) is str and IDENTITY_PATTERN.fullmatch(selected["identity"]),
                    "package_fetch_identity_invalid")
    _native_require(isinstance(request_id, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", request_id),
                    "logical_transfer_identity_invalid")
    package = selected_package(selected.get("package"), selected.get("digest"))
    effects = service_effects(selected.get("declared_effects"))
    offered = client.manifest(selected["identity"], selected["digest"])
    require_offer_unchanged(selected["digest"], offered)
    require_body_permitted(offered)
    _native_require(offered.kind == "tool" and offered.declared_effects == effects
                    and offered.size_bytes == package.served_size, "selected_package_manifest_mismatch")
    _native_require(client.download_allowance is not None
                    and all(entry.size_bytes <= client.download_allowance for entry in package.files),
                    "package_file_exceeds_allowance")
    require_within_download_allowance(offered, client.download_allowance)
    record.update({"record_type": "native_package_fetch_record/v1", "identity": offered.identity,
                   "package_digest": package.package_digest, "selected_digest": offered.digest,
                   "declared_effects": list(effects), "complete": False, "files": [],
                   "automatic_retries": 0, "runtime_admitted": False})
    record_pending_fetch(record, request_id, persist)
    try:
        body = client.download(offered, request_id, offered.size_bytes)
        verify_downloaded_body(offered, body)
        if package.body_form == "package":
            _native_require(body.data == package.document(), "package_document_differs_from_selection")
        payloads = []
        for entry in package.files:
            file_record = {"path": entry.path, "digest": entry.digest, "size_bytes": entry.size_bytes,
                           "role": entry.role, "media_type": entry.media_type, "verified": False}
            record["files"].append(file_record)
            persist()
            download = (client.download(offered, request_id, entry.size_bytes, path=entry.path)
                        if package.body_form == "package" else body)
            require_successful_download(download)
            require_bounded_response(download.data, entry.size_bytes)
            digest = hashlib.sha256(download.data).hexdigest()
            require_header_digest(digest, download)
            require_manifest_digest(digest, len(download.data), replace(offered, digest=entry.digest,
                                                                       size_bytes=entry.size_bytes))
            payloads.append((entry.path, download.data))
            file_record["verified"] = True
            persist()
        result = NativePackageInput(offered.identity, package, tuple(payloads), effects)
        record["fetch"].update({"outcome": FetchOutcome.FETCHED_AND_VERIFIED,
                                "http_status": body.http_status, "header_digest": body.header_digest,
                                "body_sha256": offered.digest, "body_bytes": len(body.data)})
        record["complete"] = True
        persist()
        return result
    except InstallRefusal as error:
        record["refusal"] = {"code": error.code, "detail": error.detail}
        persist()
        raise


@dataclass(frozen=True)
class NativeCompiledFile:
    package_identity: str
    source_path: str
    target_path: str
    file_role: str
    media_type: str
    digest: str
    mode: int
    payload: bytes = field(repr=False)

    def reference(self):
        return {"package_identity": self.package_identity, "source_path": self.source_path,
                "target_path": self.target_path, "file_role": self.file_role, "media_type": self.media_type,
                "digest": self.digest, "mode": self.mode, "size_bytes": len(self.payload)}


@dataclass(frozen=True)
class NativeMaterialPlan:
    profile_digest: str
    runtime: NativeClientBinding
    files: tuple[NativeCompiledFile, ...]
    entrypoint_target: str
    load_effects: tuple[str, ...]
    invocation_effects: tuple[str, ...]
    read_only_mounts: tuple[tuple[str, str], ...]
    dependency_mounts: tuple[tuple[str, str], ...]
    record_type: str = NATIVE_PREVIEW_RECORD_TYPE

    @property
    def runtime_admitted(self):
        return False

    def to_dict(self):
        return {"record_type": self.record_type, "slot_id": "material_install_layout",
                "profile_digest": self.profile_digest, "client_binding": asdict(self.runtime),
                "files": [entry.reference() for entry in self.files], "entrypoint_target": self.entrypoint_target,
                "required_effects": {"placement": ["writes_fs"], "load": list(self.load_effects),
                                     "invocation": list(self.invocation_effects)},
                "read_only_mounts": [list(row) for row in self.read_only_mounts],
                "dependency_mounts": [{"dependency": identity, "project_path": path, "read_only": True}
                                      for identity, path in self.dependency_mounts],
                "activation": "fresh_process_after_complete_staging", "runtime_admitted": False,
                "dependency_installation": "not_supported", "writes_performed": False}

    @property
    def digest(self):
        return _native_digest(self.to_dict())


def require_native_placements(files, runtime, entrypoint_target):
    """Closed destinations for these two loader shapes, including every passive support file.

    A generic package projection is not permission to introduce another plugin,
    hook, instruction, skill or extension surface. Configuration is limited to
    the explicitly bound OpenCode fixture files; support stays under the loader's
    dedicated package folder. All other destinations refuse.
    """
    root, entry_folder = ((".opencode", "tools") if runtime.client_kind == "opencode"
                          else (".pi", "extensions"))
    entry_parts = entrypoint_target.split("/")
    _native_require(len(entry_parts) == 3 and entry_parts[:2] == [root, entry_folder]
                    and entrypoint_target.endswith((".ts", ".js")), "native_loader_unsupported")
    for entry in files:
        parts = entry.target_path.split("/")
        support = len(parts) >= 4 and parts[:2] == [root, "baltor-packages"]
        configuration = (runtime.client_kind == "opencode"
                         and entry.target_path in ("opencode.json", ".opencode/.gitignore")
                         and entry.file_role == "configuration")
        _native_require(entry.target_path == entrypoint_target or support or configuration,
                        "unsupported_native_placement")


def validate_native_stage_plan(plan):
    """Validate received v3 plan values before computing their identity or creating a stage."""
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackageFile, placement_path
    from loop_engine.core.service_runtime.records import ServiceRuntimeError
    _native_require(type(plan.profile_digest) is str and DIGEST_PATTERN.fullmatch(plan.profile_digest)
                    and isinstance(plan.runtime, NativeClientBinding) and type(plan.files) is tuple
                    and 1 <= len(plan.files) <= 512 and type(plan.entrypoint_target) is str,
                    "plan_shape_invalid")
    for entry in plan.files:
        _native_require(isinstance(entry, NativeCompiledFile) and type(entry.mode) is int
                        and entry.mode in NATIVE_FILE_MODES and type(entry.payload) is bytes
                        and type(entry.package_identity) is str and IDENTITY_PATTERN.fullmatch(entry.package_identity),
                        "plan_file_shape_invalid")
        try:
            CataloguePackageFile(entry.source_path, entry.digest, len(entry.payload), entry.media_type, entry.file_role)
            placement_path(entry.target_path)
        except (ServiceRuntimeError, TypeError, ValueError):
            raise InstallRefusal(RefusalCode.NATIVE_PACKAGE_REFUSED, "plan_file_shape_invalid") from None
    _native_require(sum(len(entry.payload) for entry in plan.files) <= 32 * 1024 * 1024,
                    "package_inventory_too_large")
    paths = [entry.target_path.casefold() for entry in plan.files]
    _native_require(len(set(paths)) == len(paths) and not any(
        other.startswith(path + "/") for path in paths for other in paths), "plan_path_collision")
    require_native_placements(plan.files, plan.runtime, plan.entrypoint_target)
    _native_require(any(entry.target_path == plan.entrypoint_target and entry.file_role == "executable_tool"
                        for entry in plan.files), "native_entrypoint_missing")
    _native_effects(plan.load_effects)
    _native_effects(plan.invocation_effects)
    _native_require("reads_fs" in plan.load_effects and "spawns_process" in plan.invocation_effects,
                    "plan_effects_invalid")
    identities = {entry.package_identity for entry in plan.files}
    _native_require(type(plan.read_only_mounts) is tuple and len(plan.read_only_mounts) <= 1
                    and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                            and row[0] in identities and row[1] == "/package"
                            for row in plan.read_only_mounts), "runtime_mount_unsupported")
    _native_require(type(plan.dependency_mounts) is tuple
                    and all(type(row) is tuple and len(row) == 2 and type(row[0]) is str
                            and row[0] in dict(plan.runtime.dependencies)
                            and type(row[1]) is str for row in plan.dependency_mounts), "dependency_mount_invalid")
    targets = [row[1] for row in plan.dependency_mounts]
    _native_require(len({target.casefold() for target in targets}) == len(targets), "dependency_mount_invalid")
    for target in targets:
        _native_require(plan.runtime.client_kind == "opencode" and target.startswith(".opencode/node_modules/")
                        and len(target.split("/")) == 3, "dependency_mount_invalid")
        try:
            placement_path(target)
        except (ServiceRuntimeError, TypeError, ValueError):
            raise InstallRefusal(RefusalCode.NATIVE_PACKAGE_REFUSED, "dependency_mount_invalid") from None
        folded = target.casefold()
        _native_require(not any(path == folded or path.startswith(folded + "/") or folded.startswith(path + "/")
                                for path in paths), "dependency_mount_collision")


def compile_native_package_plan(profile, packages, observed_runtime):
    """Pure candidate compiler. Exact package bytes stay opaque; unsupported semantics refuse."""
    from loop_engine.core.service_runtime.catalogue_packages import placement_path
    _native_require(isinstance(profile, ClientLayoutProfile) and profile.package_binding is not None,
                    "native_package_profile_required")
    binding = profile.package_binding
    _native_require(observed_runtime == binding.runtime, "client_binding_mismatch")
    _native_require(type(packages) is tuple and all(isinstance(p, NativePackageInput) for p in packages)
                    and len({p.identity for p in packages}) == len(packages), "package_inventory_mismatch")
    selected = {p.identity: p for p in packages}
    _native_require(set(selected) == {p.identity for p in binding.projections}, "package_inventory_mismatch")
    files = []
    for projection in binding.projections:
        item = selected[projection.identity]
        _native_require(item.package.package_digest == projection.package_digest, "package_digest_mismatch")
        _native_require(set(item.declared_effects) - {"pure"} <= set(binding.invocation_effects), "package_effects_omitted")
        _native_require(not item.package.executable or "spawns_process" in item.declared_effects,
                        "package_executable_effect_missing")
        _native_require(all(type(row) is tuple and len(row) == 2 and type(row[0]) is str and type(row[1]) is bytes
                            for row in item.payloads), "package_input_invalid")
        payloads, modes = dict(item.payloads), dict(projection.file_modes)
        paths = {entry.path for entry in item.package.files}
        _native_require(len(payloads) == len(item.payloads) and set(payloads) == paths, "package_inventory_mismatch")
        _native_require(set(modes) == paths, "file_mode_inventory_mismatch")
        for entry in item.package.files:
            raw = payloads[entry.path]
            _native_require(hashlib.sha256(raw).hexdigest() == entry.digest and len(raw) == entry.size_bytes,
                            "package_bytes_mismatch")
            _native_require(entry.role in binding.supported_roles, "unsupported_mandatory_role")
            target = "/".join((*projection.target_root, *entry.path.split("/")))
            placement_path(target)
            files.append(NativeCompiledFile(item.identity, entry.path, target, entry.role, entry.media_type,
                                            entry.digest, modes[entry.path], raw))
    _native_require(len(files) <= 512 and sum(len(entry.payload) for entry in files) <= 32 * 1024 * 1024,
                    "package_inventory_too_large")
    paths = [entry.target_path.casefold() for entry in files]
    _native_require(len(set(paths)) == len(paths), "target_collision")
    _native_require(not any("/".join(path.split("/")[:n]) in paths for path in paths
                            for n in range(1, len(path.split("/")))), "parent_file_collision")
    for _dependency, target in binding.dependency_mounts:
        _native_require(not any(path == target.casefold() or path.startswith(target.casefold() + "/")
                                or target.casefold().startswith(path + "/") for path in paths),
                        "dependency_mount_collision")
    entrypoint = next((entry for entry in files if entry.target_path == binding.entrypoint_target), None)
    _native_require(entrypoint is not None and entrypoint.file_role == "executable_tool", "native_entrypoint_missing")
    native_root = binding.entrypoint_target.rsplit("/", 1)[0] + "/"
    _native_require(not any(entry.target_path.startswith(native_root) and entry is not entrypoint for entry in files),
                    "extra_native_discovery_file")
    require_native_placements(files, observed_runtime, binding.entrypoint_target)
    return NativeMaterialPlan(_native_digest(asdict(profile)), observed_runtime,
        tuple(sorted(files, key=lambda entry: entry.target_path)), binding.entrypoint_target,
        binding.load_effects, binding.invocation_effects, binding.read_only_mounts, binding.dependency_mounts)


def stage_native_package_plan(plan, parent, report_path, expected_digest, placement_effects, observed_runtime):
    """Place into a NEW private attempt only; never update a live root or launch a client.

    The report is reserved before file effects and the native entrypoint is written last.
    A failure keeps its partial stage/report for inspection; nothing auto-activates it.
    Host admission, load/invocation grants, mount enforcement and fresh launch stay separate.
    """
    _native_require(isinstance(plan, NativeMaterialPlan) and plan.record_type == NATIVE_PREVIEW_RECORD_TYPE,
                    "plan_version_unsupported")
    validate_native_stage_plan(plan)
    _native_require(expected_digest == plan.digest, "plan_digest_mismatch")
    _native_require(all(type(entry.payload) is bytes and hashlib.sha256(entry.payload).hexdigest() == entry.digest
                        for entry in plan.files), "plan_payload_mismatch")
    _native_require(observed_runtime == plan.runtime, "client_binding_mismatch")
    _native_effects(placement_effects)
    _native_require("writes_fs" in placement_effects, "placement_not_authorized")
    root = real_target_directory(Path(parent))
    _native_require(Path(report_path).parent.resolve() == root, "report_scope_invalid")
    descriptor = reserve_report(Path(report_path))
    report = {"record_type": NATIVE_STAGE_RECORD_TYPE, "plan_digest": plan.digest, "complete": False,
              "runtime_admitted": False, "activated": False, "workspace": None, "files": [], "refusal": None}
    try:
        workspace = Path(tempfile.mkdtemp(prefix="native-package-", dir=root))
        report["workspace"] = str(workspace)
        _write_report(descriptor, report)
        for _dependency, target in plan.dependency_mounts:
            directory = _walk_to_directory(workspace, tuple(target.split("/")), create=True)
            if directory is not None:
                os.close(directory)
        for entry in sorted(plan.files, key=lambda row: row.target_path == plan.entrypoint_target):
            write_confined_file(workspace, tuple(entry.target_path.split("/")), entry.payload, mode=entry.mode)
            report["files"].append(entry.reference())
            _write_report(descriptor, report)
        report["complete"] = True
        _write_report(descriptor, report)
        return report
    except Exception as error:
        report["refusal"] = {"type": type(error).__name__, "code": getattr(error, "code", "write_failed")}
        _write_report(descriptor, report)
        raise
    finally:
        os.close(descriptor)


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

# Pi joined the recipes registry on September 24, 2026. Pi 0.73.1 loads project
# skills from .pi/skills/<name>/SKILL.md, and only when the file begins with a
# name and a description, which the generated header supplies. That was observed
# end to end with Pi's own skill loader in the Pi setup run of September 23, 2026.
# Pi offers no listing command that starts no model turn, so its listing is None.
PI_PROFILE = ClientLayoutProfile(
    client_kind="pi",
    executable_name="pi",
    locations=(NativeLocation(SKILL_KIND, (".pi", "skills"), "SKILL.md", SKILL_FILE_RENDERING),),
    unplaced_kinds=(
        ("instruction_file", "client_reads_instruction_files_only_through_files_the_project_owns"),
        ("reusable_code", "code_needs_independent_admission_before_local_use"),
        ("tool", "code_needs_independent_admission_before_local_use"),
    ),
    listing=None,
    version_arguments=("--version",),
    model_turn_subcommands=("-p", "--print"),
    observed_client_versions=("0.73.1",),
)

# Baltor solve reads completed package folders with --material-package through
# its source owner. That explicit read does not create an auto-discovered skill
# location or qualify this installer's placement path. No listing runs here.
BALTOR_HARNESS_PROFILE = ClientLayoutProfile(
    client_kind="baltor-harness",
    executable_name="loop-engine",
    locations=(),
    unplaced_kinds=(
        ("skill", "engine_reads_selected_packages_through_explicit_material_package_input"),
        ("instruction_file", "engine_reads_selected_packages_through_explicit_material_package_input"),
        ("reusable_code", "code_needs_independent_admission_before_local_use"),
        ("tool", "code_needs_independent_admission_before_local_use"),
    ),
    listing=None,
    version_arguments=(),
    model_turn_subcommands=("solve", "overnight"),
    observed_client_versions=("0.1.0",),
)

CLIENT_LAYOUT_PROFILES = {
    OPENCODE_PROFILE.client_kind: OPENCODE_PROFILE,
    CLAUDE_CODE_PROFILE.client_kind: CLAUDE_CODE_PROFILE,
    CODEX_PROFILE.client_kind: CODEX_PROFILE,
    PI_PROFILE.client_kind: PI_PROFILE,
    BALTOR_HARNESS_PROFILE.client_kind: BALTOR_HARNESS_PROFILE,
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
    authority_effects: tuple[str, ...] = ()

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
        object.__setattr__(self, "authority_effects", service_effects(self.authority_effects))
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
        if "package" not in selected:
            selected = client.resolve_identity_selection(offered.identity, offered.digest)
        _refuse_unless(selected["package"] is None or selected["package"]["body_form"] == "file",
                       RefusalCode.NATIVE_PACKAGE_PLAN_REQUIRED)
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
    client = ServiceClient(request.origin, key, request.limits, authority_effects=request.authority_effects)
    request_prefix = request.request_prefix or "native-install-" + uuid.uuid4().hex
    report = {
        "record_type": REPORT_RECORD_TYPE, "complete": False,
        "mode": "preview_without_body_read_or_file_write" if request.preview else "install",
        "observed_at": datetime.now(timezone.utc).isoformat(), "origin": request.origin,
        "client": {"kind": profile.client_kind, "layout_profile": profile.record_type,
                   "layout_observed_with_versions": list(profile.observed_client_versions)},
        "target_folder": str(root),
        "selection": {"by": "query" if request.query else "identities",
                      "authority_effects": list(request.authority_effects),
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
    parser.add_argument("--step-effect", choices=STEP_EFFECTS, action="append", default=[],
                        help="Effect already held by the customer step, for metadata eligibility only. Repeatable.")
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
            authorized=args.authorize_install, preview=args.preview, request_prefix=args.request_prefix,
            authority_effects=tuple(args.step_effect))
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
