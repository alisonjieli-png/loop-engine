"""Generated components as qualification reads them: the stored candidate record and its exact files.

The supply lines write each generated package into the import store's own namespace, ``library.supply``:
the candidate record holds the typed package (``catalogue_package/v1``) and every file is a body stored
under its SHA-256. This module reads one query snapshot of the records and then the bodies, read-only.
The body store checks each file's size and digest as it reads it, so a component that loads here has
exactly the bytes its record names; a component that does not load is reported with its reason and is
never qualified.

A folder reader exists for check fixtures: ``candidate.json`` beside the package files.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType

from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, sha256_hex
from loop_engine.core.service_runtime.records import ServiceRuntimeError

SUPPLY_NAMESPACE = "library.supply"
CANDIDATE_RECORD = "library_supply_candidate/v1"
GENERATED_AUTHORING = "generated_from_licensed_facts"
CANDIDATE_LIFECYCLE = "candidate"
#: The largest package qualification reads; the catalogue's own package bound.
MAXIMUM_PACKAGE_BYTES = 32 * 1024 * 1024


class ComponentReadError(ValueError):
    """A component whose record or bytes cannot be read exactly as declared."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GeneratedComponent:
    """One generated component: its identity, record version, candidate record, package and exact files."""

    identity: str
    record_version: str
    candidate: MappingProxyType
    package: CataloguePackage
    payloads: MappingProxyType

    @property
    def line(self) -> str:
        return str(self.candidate.get("line", ""))

    @property
    def generator(self) -> dict:
        provenance = self.candidate.get("provenance")
        value = provenance.get("generator") if isinstance(provenance, dict) else None
        return dict(value) if isinstance(value, dict) else {}

    @property
    def batch(self) -> str:
        """The generator batch: one supply line at one generator version and code revision."""
        generator = self.generator
        return f"{self.line}/{generator.get('version', '?')}@{str(generator.get('code_revision', '?'))[:12]}"

    @property
    def form(self) -> str:
        value = self.candidate.get("component_form")
        return str(value.get("form", "")) if isinstance(value, dict) else ""

    @property
    def kind(self) -> str:
        return str(self.candidate.get("kind", ""))

    @property
    def licence_expression(self) -> str:
        value = self.candidate.get("licence")
        return str(value.get("spdx_expression", "")) if isinstance(value, dict) else ""

    def text(self, path: str) -> "str | None":
        payload = self.payloads.get(path)
        if payload is None:
            return None
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def replaced(self, *, identity: "str | None" = None, payloads: "dict | None" = None,
                 candidate: "dict | None" = None) -> "GeneratedComponent":
        """A new component with other files or record fields; its package follows the new bytes.

        Controls and fixtures use this. The package is rebuilt from the new bytes, so a changed file gets
        its own digest and the package digest changes with it, exactly as a real regenerated package would."""
        from loop_engine.core.service_runtime.catalogue_packages import CataloguePackageFile
        files = dict(self.payloads if payloads is None else payloads)
        entries = {entry.path: entry for entry in self.package.files}
        new_entries = []
        for path, payload in sorted(files.items()):
            old = entries.get(path)
            media_type = old.media_type if old else _media_type(path)
            role = old.role if old else "other"
            new_entries.append(CataloguePackageFile(path, sha256_hex(payload), len(payload), media_type, role))
        package = CataloguePackage(tuple(new_entries), self.package.body_form)
        record = json.loads(json.dumps(dict(self.candidate) if candidate is None else candidate))
        record["package"] = package.to_dict()
        record["package_digest"] = package.package_digest
        name = identity or self.identity
        record["record_id"] = name
        return GeneratedComponent(name, self.record_version, MappingProxyType(record), package,
                                  MappingProxyType(dict(files)))


def _media_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {".py": "text/x-python", ".json": "application/json", ".md": "text/markdown", ".toml": "application/toml",
            ".txt": "text/plain", ".csv": "text/csv", ".sh": "application/x-sh", ".js": "text/javascript"}.get(
                suffix, "text/plain")


def _component(identity: str, version: str, payload: dict, read) -> GeneratedComponent:
    if payload.get("record_type") != CANDIDATE_RECORD:
        raise ComponentReadError("record_type_unsupported", f"{identity} is not a {CANDIDATE_RECORD} record")
    try:
        package = CataloguePackage.from_dict(payload.get("package"))
    except (ServiceRuntimeError, TypeError, ValueError) as error:
        raise ComponentReadError("package_invalid", f"{identity}: the package record does not parse") from error
    if package.package_digest != payload.get("package_digest"):
        raise ComponentReadError("package_digest_mismatch", f"{identity}: the package digest differs from its record")
    if sum(entry.size_bytes for entry in package.files) > MAXIMUM_PACKAGE_BYTES:
        raise ComponentReadError("package_too_large", f"{identity}: the package exceeds the qualification bound")
    payloads = {}
    for entry in package.files:
        try:
            data = read(entry)
        except (ServiceRuntimeError, OSError, ValueError) as error:
            raise ComponentReadError("body_unreadable", f"{identity}: {entry.path} cannot be read exactly") from error
        if len(data) != entry.size_bytes or sha256_hex(data) != entry.digest:
            raise ComponentReadError("body_digest_mismatch", f"{identity}: {entry.path} differs from its digest")
        payloads[entry.path] = data
    return GeneratedComponent(identity, version, MappingProxyType(payload), package, MappingProxyType(payloads))


class StoreReader:
    """Read-only access to the supply namespace of one import store."""

    def __init__(self, root) -> None:
        from tools.licensed_import.storage import ImportStore
        root = Path(root)
        if not (root / "records.db").is_file() or not (root / "bodies").is_dir():
            raise ComponentReadError("store_missing", "the import store root holds no records.db and bodies")
        self.store = ImportStore(root, writes_authorized=False)

    def rows(self, *, lines=(), limit: "int | None" = None) -> list:
        """One consistent snapshot of the current supply candidates, in record order."""
        from loop_engine.catalog.query import IntelligenceQuery
        rows = self.store.records.query(IntelligenceQuery(namespaces=(SUPPLY_NAMESPACE,),
                                                          lifecycle=(CANDIDATE_LIFECYCLE,)))
        rows = [row for row in rows if row.get("payload", {}).get("record_type") == CANDIDATE_RECORD
                and (not lines or row["payload"].get("line") in lines)]
        rows.sort(key=lambda row: row["record_id"])
        return rows[:limit] if limit is not None else rows

    def component(self, row: dict) -> GeneratedComponent:
        return _component(row["record_id"], row["record_version"], row["payload"],
                          lambda entry: self.store.bodies.read(entry.digest, entry.size_bytes))

    def close(self) -> None:
        self.store.close()


def from_folder(folder) -> GeneratedComponent:
    """A component from ``candidate.json`` and the files beside it (check fixtures and inspection copies)."""
    folder = Path(folder)
    payload = json.loads((folder / "candidate.json").read_text(encoding="utf-8"))
    identity = payload.get("record_id") or folder.name

    def read(entry):
        path = folder / entry.path
        if path.is_symlink() or not path.is_file():
            raise OSError("not a regular file")
        return path.read_bytes()

    return _component(identity, payload.get("version", {}).get("record_version", "") if isinstance(
        payload.get("version"), dict) else "", payload, read)
