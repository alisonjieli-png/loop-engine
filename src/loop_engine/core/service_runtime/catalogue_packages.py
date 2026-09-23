"""Harness intelligence packages and the content-addressed body store edge.

A catalogue item is a package of one or more files that a harness picks up
from its working directory: an instruction file such as `AGENTS.md` or
`CLAUDE.md`, a skill folder with its scripts, references and assets, a
subagent definition, a command, a hook, a protocol server configuration, a
plugin manifest or an executable tool. No file is assumed to be Markdown or
text. Each file carries its own digest, size, media type and placement role,
and the package is identified by the digest of one canonical document that
lists those files, the way an image manifest lists its layers.

```text
Catalogue package
├── files, one to MAXIMUM_PACKAGE_FILES
│   ├── path        relative placement inside the package folder, never `..` or `.git`
│   ├── digest      SHA-256 of the exact bytes
│   ├── size_bytes  bounded by MAXIMUM_FILE_BYTES
│   ├── media_type  type/subtype, declared, never inferred at serving time
│   └── role        one of FILE_ROLES, the intended placement
├── body_form
│   ├── file        one UTF-8 text file; the served body is that file
│   └── package     the served body is the canonical package document
└── package digest  SHA-256 of the canonical package document
```

Bodies live behind one fixed edge, `catalogue_body_store/v1`. The first engine
keeps immutable files on the service volume under a host-declared folder,
addressed as `sha256/<first two>/<digest>`: the object key of the existing
`ContextArtifactRef` in `core/context_artifacts.py` and the blob layout of an
OCI image layout. It does not reuse that class, because that class creates
folders when it is constructed, follows symbolic links in its root and object
folders, and has no read-only mode. Object storage is a later engine behind
the same edge. Discovery is effect-free: constructing an engine opens nothing
and creates nothing.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .records import ServiceRuntimeError

BODY_STORE_EDGE_VERSION = "catalogue_body_store/v1"
BODY_STORE_CAPABILITIES_VERSION = "catalogue_body_store_capabilities/v1"
PACKAGE_RECORD_TYPE = "catalogue_package/v1"
VOLUME_ENGINE = "service_volume_files"
#: What one file is for. A harness reads each kind from a different place, so
#: the role is declared with the file rather than guessed from its name.
FILE_ROLES = ("instruction_file", "skill_definition", "skill_script", "skill_reference",
              "skill_asset", "subagent_definition", "command", "hook",
              "protocol_server_configuration", "plugin_manifest", "executable_tool",
              "configuration", "other")
#: Roles whose file a harness may run. A package holding one must declare a
#: process effect, so the existing effect filter withholds it from a client
#: that did not declare that authority.
EXECUTABLE_ROLES = ("skill_script", "hook", "executable_tool")
EXECUTABLE_EFFECT = "spawns_process"
BODY_FORMS = ("file", "package")
FILE_BODY, PACKAGE_BODY = BODY_FORMS
MAXIMUM_PACKAGE_FILES = 64
MAXIMUM_FILE_BYTES = 8 * 1024 * 1024
MAXIMUM_PACKAGE_BYTES = 32 * 1024 * 1024
MAXIMUM_PATH_CHARACTERS = 200
MAXIMUM_PATH_DEPTH = 8
_SEGMENT = re.compile(r"[A-Za-z0-9._@+-]{1,100}")
_MEDIA_TYPE = re.compile(r"[a-z0-9][a-z0-9!#$&^_.+-]{0,62}/[a-z0-9][a-z0-9!#$&^_.+-]{0,126}")
_DIGEST = re.compile(r"[0-9a-f]{64}")


def _refuse(code, message="catalogue package refused"):
    raise ServiceRuntimeError(code, message)


def sha256_hex(payload):
    return hashlib.sha256(payload).hexdigest()


def exact_digest(value, code="body_digest_invalid"):
    """Return a lowercase SHA-256 digest, or refuse; a digest is never a path."""
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        _refuse(code, "an exact lowercase SHA-256 digest is required")
    return value


def placement_path(value):
    """Return a safe relative placement path inside a package folder, or refuse.

    A path is written with forward slashes, has at most MAXIMUM_PATH_DEPTH
    segments of letters, digits and `._@+-`, and never names `.`, `..` or a
    `.git` folder, because a file placed there would change the customer's
    repository rather than give a harness something to read.
    """
    if (not isinstance(value, str) or not value or len(value) > MAXIMUM_PATH_CHARACTERS
            or value.startswith("/") or value.endswith("/")):
        _refuse("package_path_invalid", "a placement path is relative, nonempty and bounded")
    segments = value.split("/")
    if (len(segments) > MAXIMUM_PATH_DEPTH
            or any(not _SEGMENT.fullmatch(part) or part in (".", "..") or part.casefold() == ".git"
                   for part in segments)):
        _refuse("package_path_invalid", "a placement path uses safe segments and never names .., . or .git")
    return value


@dataclass(frozen=True)
class CataloguePackageFile:
    """One file of a package: exact bytes, declared type and intended placement."""

    path: str
    digest: str
    size_bytes: int
    media_type: str
    role: str

    def __post_init__(self):
        placement_path(self.path)
        exact_digest(self.digest, "package_file_digest_invalid")
        if type(self.size_bytes) is not int or not 0 <= self.size_bytes <= MAXIMUM_FILE_BYTES:
            _refuse("package_file_too_large", f"a file holds at most {MAXIMUM_FILE_BYTES} bytes")
        if not isinstance(self.media_type, str) or not _MEDIA_TYPE.fullmatch(self.media_type):
            _refuse("package_media_type_invalid", "a media type is a lowercase type/subtype pair")
        if self.role not in FILE_ROLES:
            _refuse("package_file_role_invalid", f"a file role is one of {FILE_ROLES}")

    def to_dict(self):
        return {"path": self.path, "digest": self.digest, "size_bytes": self.size_bytes,
                "media_type": self.media_type, "role": self.role}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"path", "digest", "size_bytes", "media_type", "role"}:
            _refuse("package_file_invalid", "a package file names path, digest, size, media type and role only")
        return cls(**value)


@dataclass(frozen=True)
class CataloguePackage:
    """The files of one item version and the form its served body takes."""

    files: tuple
    body_form: str = PACKAGE_BODY

    def __post_init__(self):
        files = tuple(self.files)
        if not 1 <= len(files) <= MAXIMUM_PACKAGE_FILES or any(
                not isinstance(entry, CataloguePackageFile) for entry in files):
            _refuse("package_invalid", f"a package holds one to {MAXIMUM_PACKAGE_FILES} typed files")
        folded = [entry.path.casefold() for entry in files]
        if len(set(folded)) != len(folded):
            # Two paths that differ only in letter case land on one file on a
            # case-insensitive disk, so they are the same placement.
            _refuse("package_path_duplicate", "each file of a package has its own placement path")
        if sum(entry.size_bytes for entry in files) > MAXIMUM_PACKAGE_BYTES:
            _refuse("package_too_large", f"a package holds at most {MAXIMUM_PACKAGE_BYTES} bytes")
        if self.body_form not in BODY_FORMS:
            _refuse("package_body_form_invalid", f"a body form is one of {BODY_FORMS}")
        if self.body_form == FILE_BODY and len(files) != 1:
            _refuse("package_body_form_invalid", "the file body form serves exactly one file")
        object.__setattr__(self, "files", tuple(sorted(files, key=lambda entry: entry.path)))

    def document(self):
        """The canonical package document; its digest is the package digest."""
        return json.dumps({"record_type": PACKAGE_RECORD_TYPE,
                           "files": [entry.to_dict() for entry in self.files]},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @property
    def package_digest(self):
        return sha256_hex(self.document())

    @property
    def served_digest(self):
        return self.files[0].digest if self.body_form == FILE_BODY else self.package_digest

    @property
    def served_size(self):
        return self.files[0].size_bytes if self.body_form == FILE_BODY else len(self.document())

    @property
    def executable(self):
        return any(entry.role in EXECUTABLE_ROLES for entry in self.files)

    def file(self, path):
        for entry in self.files:
            if entry.path == path:
                return entry
        _refuse("package_file_not_found", "the package has no file at that path")

    def to_dict(self):
        return {"body_form": self.body_form, "files": [entry.to_dict() for entry in self.files]}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"body_form", "files"} or not isinstance(value["files"], list):
            _refuse("package_invalid", "a package names its body form and its files only")
        return cls(tuple(CataloguePackageFile.from_dict(entry) for entry in value["files"]), value["body_form"])


def parse_package_document(payload):
    """Read a served package document back into typed files, refusing any other shape."""
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        _refuse("package_document_invalid", "a package document is canonical JSON")
    if not isinstance(value, dict) or set(value) != {"record_type", "files"} or value["record_type"] != PACKAGE_RECORD_TYPE:
        _refuse("package_document_invalid", f"this release reads {PACKAGE_RECORD_TYPE} only")
    package = CataloguePackage(tuple(CataloguePackageFile.from_dict(entry) for entry in value["files"]), PACKAGE_BODY)
    if package.document() != (payload.encode("utf-8") if isinstance(payload, str) else payload):
        _refuse("package_document_invalid", "a package document is written in its canonical form")
    return package


@runtime_checkable
class CatalogueBodyStore(Protocol):
    """The fixed edge every body engine implements; callers never branch on an engine class."""

    def capabilities(self) -> dict: ...

    def read(self, digest: str, size_bytes: int) -> bytes: ...

    def put(self, payload: bytes, *, expected_digest: "str | None" = None, durable: bool = True) -> dict: ...

    def sync(self) -> None: ...


def require_body_store(store, *, write=False):
    """Negotiate the exact edge before any read or write, refusing an unknown engine contract."""
    try:
        capabilities = store.capabilities()
    except Exception:
        _refuse("body_store_contract_unavailable", "the body store did not state its contract")
    if (not isinstance(store, CatalogueBodyStore) or not isinstance(capabilities, dict)
            or capabilities.get("record_type") != BODY_STORE_CAPABILITIES_VERSION
            or capabilities.get("edge") != BODY_STORE_EDGE_VERSION
            or capabilities.get("content_addressed") is not True or capabilities.get("digest") != "sha256"
            or (write and capabilities.get("writes") is not True)):
        _refuse("body_store_contract_unavailable", f"a body store must speak {BODY_STORE_EDGE_VERSION}")
    return store


class VolumeBodyStore:
    """The first engine: immutable files under one host-declared folder on the service volume.

    Every object is written once through a temporary file and a hard link, so
    an existing name is never replaced. Reading opens the object without
    following a symbolic link and checks its size and digest. Every folder
    between the root and an object must be a real folder, so no object can be
    read from or written to anywhere outside the declared root.
    """

    def __init__(self, root, *, writes_authorized=False, maximum_file_bytes=MAXIMUM_FILE_BYTES):
        if type(writes_authorized) is not bool:
            _refuse("body_store_root_invalid", "body store write authority is an explicit Boolean")
        if not isinstance(root, str) or not root:
            _refuse("body_store_root_invalid", "the body store root is an absolute folder")
        path = Path(root)
        if not path.is_absolute() or path.resolve() != path or not path.is_dir():
            _refuse("body_store_root_invalid",
                    "the body store root is an existing absolute folder without symbolic links")
        if type(maximum_file_bytes) is not int or not 1 <= maximum_file_bytes <= MAXIMUM_PACKAGE_BYTES:
            _refuse("body_store_root_invalid", "the file allowance is a positive bounded byte count")
        self.root = path
        self._root = str(path)
        self.writes_authorized = writes_authorized
        self.maximum_file_bytes = maximum_file_bytes

    def capabilities(self):
        return {"record_type": BODY_STORE_CAPABILITIES_VERSION, "edge": BODY_STORE_EDGE_VERSION,
                "engine": VOLUME_ENGINE, "engine_version": "1.0.0", "content_addressed": True,
                "digest": "sha256", "writes": self.writes_authorized, "object_key": "sha256/<first two>/<digest>",
                "maximum_file_bytes": self.maximum_file_bytes}

    @staticmethod
    def object_key(digest):
        exact_digest(digest)
        return f"sha256/{digest[:2]}/{digest}"

    def _folders(self, digest, *, create=False):
        """Return the object's folder after checking every folder on the way is real."""
        folder = self._root
        for part in ("sha256", digest[:2]):
            folder = os.path.join(folder, part)
            try:
                info = os.lstat(folder)
            except FileNotFoundError:
                if not create:
                    _refuse("body_missing", "the body store holds no object with that digest")
                try:
                    os.mkdir(folder, 0o755)
                except FileExistsError:
                    pass
                info = os.lstat(folder)
            if not real_folder(info):
                _refuse("body_path_unsafe", "a body store folder is a symbolic link or not a folder")
        return folder

    def read(self, digest, size_bytes):
        exact_digest(digest)
        if type(size_bytes) is not int or size_bytes < 0:
            _refuse("body_size_mismatch", "a read names the exact size it expects")
        if size_bytes > self.maximum_file_bytes:
            _refuse("body_too_large", "the object is larger than this store's file allowance")
        target = os.path.join(self._folders(digest), digest)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            descriptor = os.open(target, flags)
        except FileNotFoundError:
            _refuse("body_missing", "the body store holds no object with that digest")
        except OSError as error:
            _refuse("body_path_unsafe" if error.errno == errno.ELOOP else "body_unreadable",
                    "the object could not be opened as a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                _refuse("body_path_unsafe", "the object is not a regular file")
            if info.st_size != size_bytes:
                _refuse("body_size_mismatch", "the object size differs from the recorded size")
            payload = handle.read(size_bytes + 1)
        if len(payload) != size_bytes:
            _refuse("body_size_mismatch", "the object size differs from the recorded size")
        if sha256_hex(payload) != digest:
            _refuse("body_digest_mismatch", "the object bytes differ from their digest")
        return payload

    def put(self, payload, *, expected_digest=None, durable=True):
        """Store bytes under their digest once; an existing different object is never replaced.

        `durable=False` leaves the flush to one later `sync()`, for a caller
        that writes many objects and syncs once before anything refers to them.
        """
        if not self.writes_authorized:
            _refuse("body_store_writes_not_authorized", "this body store was opened for reading")
        if not isinstance(payload, bytes):
            _refuse("body_payload_invalid", "a body is bytes")
        if len(payload) > self.maximum_file_bytes:
            _refuse("body_too_large", "the body is larger than this store's file allowance")
        digest = sha256_hex(payload)
        if expected_digest is not None and exact_digest(expected_digest) != digest:
            _refuse("body_digest_mismatch", "the bytes differ from the digest they were declared under")
        folder = self._folders(digest, create=True)
        if self._present(digest, len(payload)):
            return {"digest": digest, "size_bytes": len(payload), "written": False}
        temporary = os.path.join(folder, f".{digest}.{secrets.token_hex(8)}.partial")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(temporary, flags, 0o444)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                if durable:
                    os.fsync(handle.fileno())
            try:
                # A hard link creates the name only when it is absent, so a
                # second writer, a crash or a planted file can never be
                # replaced by this write.
                _link_once(temporary, os.path.join(folder, digest))
            except FileExistsError:
                pass
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        if durable:
            _sync_folder(folder)
        if not self._present(digest, len(payload)):
            _refuse("body_store_write_failed", "the stored object could not be read back")
        return {"digest": digest, "size_bytes": len(payload), "written": True}

    def sync(self):
        """Make every object written with `durable=False` durable before anything refers to it."""
        os.sync()

    def _present(self, digest, size_bytes):
        try:
            self.read(digest, size_bytes)
            return True
        except ServiceRuntimeError as error:
            if error.code == "body_missing":
                return False
            if error.code in ("body_size_mismatch", "body_digest_mismatch"):
                _refuse("body_digest_conflict",
                        "an object already stored under this digest holds other bytes; it is never overwritten")
            raise


def real_folder(info):
    """A folder on the way to an object is a real folder, never a symbolic link to somewhere else."""
    return not stat.S_ISLNK(info.st_mode) and stat.S_ISDIR(info.st_mode)


#: Creates the object's name only when it is absent; it never replaces a name.
_link_once = os.link


def _sync_folder(folder):
    try:
        descriptor = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
