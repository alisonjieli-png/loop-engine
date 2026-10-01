"""Exact local package inputs for the existing Practitioner source reader.

This is an intake adapter, not a skill admission or executable loader. It
reads only a caller-selected completed first-party fetch. The current client
record binds the canonical catalogue package and its native file layout;
every subsequent source read checks the captured file binding again. Content
remains advisory source material under the run's source-to-model permission.
No project discovery, network request, write or downloaded code runs here.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .service_runtime.catalogue_packages import (
    CataloguePackage, CataloguePackageFile, FILE_BODY, PACKAGE_BODY,
    MAXIMUM_PACKAGE_BYTES, MAXIMUM_PACKAGE_MANIFEST_BYTES, exact_digest,
)

MATERIAL_PACKAGE_RECORD = "task_material_package/v1"
# The client already publishes this wire name. Only its current v2 is read;
# the adapter does not create or rename the client's saved transfer record.
_FETCH_RECORD = "baltor_library_fetch_receipt/v2"
MAXIMUM_MATERIAL_PACKAGES = 32
MAXIMUM_MATERIAL_FILES = 512
MAXIMUM_FETCH_RECORD_BYTES = 1024 * 1024


class MaterialPackageError(ValueError):
    """A selected local package is unavailable, changed or unsupported."""


def _require(condition, code):
    if not condition:
        raise MaterialPackageError(code)


def _read(path: Path, maximum: int) -> bytes:
    # Reuse the source owner's descriptor walk and stable regular-file read.
    # A late import avoids the request/source type cycle.
    from .adaptive_practitioner_source import _read_source_bytes
    _require(all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"))
             and os.open in os.supports_dir_fd, "material_confined_read_unavailable")
    try:
        body = _read_source_bytes(path, maximum + 1)
    except (OSError, ValueError):
        raise MaterialPackageError("material_file_unavailable") from None
    _require(len(body) <= maximum, "material_file_too_large")
    return body


def _json(raw: bytes) -> dict:
    def pairs(values):
        result = {}
        for key, value in values:
            _require(key not in result, "material_duplicate_json_key")
            result[key] = value
        return result

    def nonfinite(_value):
        raise MaterialPackageError("material_nonfinite_json")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        raise MaterialPackageError("material_record_invalid") from None
    _require(type(value) is dict, "material_record_invalid")
    return value


@dataclass(frozen=True)
class MaterialPackage:
    """A captured local selection; provenance is not an admission claim."""

    root: str
    identity: str
    selected_digest: str
    transfer_record_digest: str
    package: CataloguePackage

    def __post_init__(self):
        _require(type(self.root) is str and Path(self.root).is_absolute()
                 and ".." not in Path(self.root).parts, "material_root_invalid")
        _require(type(self.identity) is str and 1 <= len(self.identity) <= 512
                 and not any(ord(c) < 32 or ord(c) == 127 for c in self.identity),
                 "material_identity_invalid")
        try:
            exact_digest(self.selected_digest)
            exact_digest(self.transfer_record_digest)
        except ValueError:
            raise MaterialPackageError("material_digest_invalid") from None
        _require(type(self.package) is CataloguePackage
                 and self.package.served_digest == self.selected_digest,
                 "material_package_binding_invalid")
        _require(len(self.package.files) <= MAXIMUM_MATERIAL_FILES,
                 "material_file_count_exceeded")
        paths = {entry.path.casefold() for entry in self.package.files}
        _require(not any("/".join(path.split("/")[:n]) in paths
                         for path in paths for n in range(1, len(path.split("/")))),
                 "material_path_collision")

    @property
    def namespace(self) -> str:
        digest = hashlib.sha256((self.identity + "\0" + self.selected_digest).encode()).hexdigest()
        return "components/" + digest[:32]

    def source_path(self, entry: CataloguePackageFile) -> str:
        return self.namespace + "/" + entry.path

    def local_path(self, entry: CataloguePackageFile) -> Path:
        return Path(self.root) / "payload" / entry.path

    def to_dict(self) -> dict:
        return {"record_type": MATERIAL_PACKAGE_RECORD, "root": self.root,
                "identity": self.identity, "selected_digest": self.selected_digest,
                "transfer_record_digest": self.transfer_record_digest,
                "package": self.package.to_dict(), "namespace": self.namespace,
                "use": "advisory_source_material", "runtime_admission": False,
                "execution_authority_granted": False}

    def card(self) -> dict:
        """Metadata only; file bodies enter only after source selection."""
        return {"record_type": MATERIAL_PACKAGE_RECORD, "identity": self.identity,
                "selected_digest": self.selected_digest, "namespace": self.namespace,
                "file_count": len(self.package.files),
                "use": "select_native_paths_through_core.source.inspect",
                "runtime_admission": False, "execution_authority_granted": False}


def validate_material_packages(packages) -> tuple[MaterialPackage, ...]:
    _require(type(packages) is tuple and len(packages) <= MAXIMUM_MATERIAL_PACKAGES
             and all(type(item) is MaterialPackage for item in packages),
             "material_selection_invalid")
    _require(len({item.namespace for item in packages}) == len(packages),
             "material_selection_duplicate")
    files = tuple(entry for item in packages for entry in item.package.files)
    _require(len(files) <= MAXIMUM_MATERIAL_FILES
             and sum(entry.size_bytes for entry in files) <= MAXIMUM_PACKAGE_BYTES,
             "material_selection_too_large")
    return packages


def read_material_file(material: MaterialPackage, entry: CataloguePackageFile) -> bytes:
    """Read one exact native file without following any path-component link."""
    _require(entry in material.package.files, "material_file_not_declared")
    raw = _read(material.local_path(entry), entry.size_bytes)
    _require(len(raw) == entry.size_bytes and hashlib.sha256(raw).hexdigest() == entry.digest,
             "material_file_changed")
    return raw


def load_material_package(root: str, *, byte_allowance: int = MAXIMUM_PACKAGE_BYTES,
                          file_allowance: int = MAXIMUM_MATERIAL_FILES) -> MaterialPackage:
    """Verify a current first-party fetch, without trusting its approval labels.

    Extra files are neither discovered nor read. A transfer without complete
    package metadata refuses; arbitrary single downloaded bodies do not have
    a qualified native layout. Relative roots are captured as absolute paths
    without resolving links, so the source reader can reject linked ancestry.
    """
    _require(type(root) is str and bool(root.strip()), "material_root_invalid")
    _require(type(byte_allowance) is int and 0 <= byte_allowance <= MAXIMUM_PACKAGE_BYTES
             and type(file_allowance) is int and 0 <= file_allowance <= MAXIMUM_MATERIAL_FILES,
             "material_allowance_invalid")
    path = Path(root).expanduser().absolute()
    _require(".." not in path.parts, "material_root_invalid")
    raw = _read(path / "receipt.json", MAXIMUM_FETCH_RECORD_BYTES)
    value = _json(raw)
    _require(value.get("record_type") == _FETCH_RECORD
             and value.get("complete") is True
             and value.get("installed") is False and value.get("executed") is False,
             "material_fetch_incomplete_or_unsupported")
    rows = value.get("files")
    _require(type(rows) is list and 1 <= len(rows) <= file_allowance,
             "material_file_count_exceeded")
    try:
        files = tuple(CataloguePackageFile.from_dict(row) for row in rows)
        package = CataloguePackage(files, PACKAGE_BODY)
        selected = exact_digest(value.get("selected_digest"))
        if len(files) == 1 and selected == files[0].digest:
            package = CataloguePackage(files, FILE_BODY)
        material = MaterialPackage(str(path), value.get("identity"), selected,
                                   hashlib.sha256(raw).hexdigest(), package)
    except (TypeError, ValueError):
        raise MaterialPackageError("material_package_binding_invalid") from None
    _require(sum(entry.size_bytes for entry in package.files) <= byte_allowance,
             "material_selection_too_large")
    body = _read(path / "body", max(MAXIMUM_PACKAGE_MANIFEST_BYTES, package.served_size))
    _require(len(body) == package.served_size
             and hashlib.sha256(body).hexdigest() == selected
             and (package.body_form == FILE_BODY or body == package.document()),
             "material_served_body_changed")
    for entry in package.files:
        read_material_file(material, entry)
    return material


def load_material_packages(roots) -> tuple[MaterialPackage, ...]:
    _require(type(roots) in (list, tuple) and len(roots) <= MAXIMUM_MATERIAL_PACKAGES,
             "material_selection_invalid")
    # Check the aggregate as each input is read, so repeated packages cannot
    # cause an unbounded multi-package read before the final admission check.
    selected = ()
    for root in roots:
        used = tuple(entry for item in selected for entry in item.package.files)
        selected = validate_material_packages((*selected, load_material_package(
            root, byte_allowance=MAXIMUM_PACKAGE_BYTES - sum(entry.size_bytes for entry in used),
            file_allowance=MAXIMUM_MATERIAL_FILES - len(used))))
    return selected


def has_source_material(request) -> bool:
    return bool(request.source_refs or getattr(request, "material_packages", ()))
