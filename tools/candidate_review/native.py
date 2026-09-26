"""Read original native candidate packages without executing, flattening or admitting them."""
from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from loop_engine.core.harness_intelligence import RECORD_TYPE as HARNESS_ITEM_RECORD
from loop_engine.core.record_operations_records import parse_json
from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
    placement_path,
)
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from tools.prepare_harness_candidates import PreparationError, _checked_source

from .catalogue import CandidateReviewRequest, CitedSource
from .configuration import Producer, ProducerDeclaration
from .records import (
    digest,
    read_part,
    read_record,
    refuse,
    sha256_hex,
)

NATIVE_ITEMS = "starter_catalogue_candidate_items/v3"
NATIVE_SPECIFICATIONS = "candidate_intelligence_specifications/v3"
NATIVE_REQUEST = "candidate_native_package_review_request/v1"
NATIVE_PROFILE = "original_native_package/v1"
NATIVE_GROUNDING = "original_native_package"
MAX_METADATA_BYTES = 32 * 1024 * 1024
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 512 * 1024
MAX_ITEMS = 10000
#: The most cited source files one catalogue may pin, the licence included. Each item cites at most 20 of its
#: own, and a batch of original candidates often cites one small idea record per item, so the bound follows
#: the item bound instead of a fixed 64.
MAX_SOURCES = MAX_ITEMS + 1
#: The media types a reviewer reads as text, line by line. Scripts in shell, JavaScript, TypeScript and PowerShell
#: joined on September 26, 2026 so a package with code is read whole (roadmap S-6.205); the licensed import's
#: review export keeps the same set, and its checks compare the two.
TEXT_MEDIA = frozenset({"text/plain", "text/markdown", "text/x-rst", "text/x-python", "application/x-python",
                        "application/json", "application/schema+json", "application/yaml", "text/yaml",
                        "application/toml", "application/x-sh", "text/javascript", "text/x-typescript",
                        "text/x-powershell", "text/x-ruby", "text/x-perl", "text/x-go", "text/x-rust", "text/x-php",
                        "text/x-lua", "text/html", "text/css", "text/csv", "application/xml", "application/sql"})
ITEM_FIELDS = ("reference", "body_path", "package", "package_root", "producer", "dependencies")
REFERENCE_FIELDS = ("identity", "kind", "purpose", "digest", "source_layer", "source_ref", "family", "size_bytes",
                    "license", "declared_effects", "styles", "tags", "exposure", "availability", "body_included")
SPEC_FIELDS = ("id", "layer", "family", "title", "tags", "text", "sources", "symbols", "kind", "purpose",
               "styles", "dependencies", "producer", "declared_effects", "package", "package_digest",
               "package_root", "body_path", "provenance")


def regular_bytes(root: Path, relative: str, limit: int) -> bytes:
    """Bounded regular-file read under a plain, host-owned root; never follow a link."""
    try:
        placement_path(relative)
    except ServiceRuntimeError:
        refuse("native_path_invalid", "a package path must remain within its supplied root")
    path = root
    for part in relative.split("/"):
        path = path / part
        if path.is_symlink():
            refuse("native_path_not_regular", "a package path passes through a link")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as stream:
            observed = os.fstat(stream.fileno())
            if not stat.S_ISREG(observed.st_mode) or observed.st_size > limit:
                refuse("native_file_out_of_bounds", "a source is not a bounded regular file")
            data = stream.read(limit + 1)
    except OSError:
        refuse("native_file_unavailable", "a declared package file is not available")
    if len(data) > limit:
        refuse("native_file_out_of_bounds", "a file exceeds the review byte limit")
    return data


def json_document(data: bytes):
    try:
        return parse_json(data.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        refuse("native_json_invalid", "metadata must be strict bounded UTF-8 JSON")


@dataclass(frozen=True)
class NativeReviewFile:
    entry: object
    payload: bytes

    @property
    def text(self):
        if self.entry.media_type not in TEXT_MEDIA:
            return None
        try:
            return self.payload.decode("utf-8")
        except UnicodeError:
            refuse("native_text_encoding_invalid", "a declared text payload is not UTF-8")


@dataclass(frozen=True)
class NativePackageReviewRequest(CandidateReviewRequest):
    package: CataloguePackage
    files: tuple
    dependencies: tuple
    specification_json: str
    review_profile: str = NATIVE_PROFILE

    @property
    def grounding(self):
        return NATIVE_GROUNDING

    @property
    def request_sha256(self):
        return digest({"record_type": NATIVE_REQUEST, "base": super().request_sha256,
                       "package": self.package.to_dict(), "profile": self.review_profile,
                       "specification": json.loads(self.specification_json)})

    @property
    def duplicate_material(self):
        return b"\n".join(file.entry.path.encode() + b"\n" + file.payload for file in self.files)

    def to_record(self):
        return {**super().to_record(), "record_type": NATIVE_REQUEST,
                "review_profile": self.review_profile, "package": self.package.to_dict(),
                "specification": json.loads(self.specification_json)}

    def package_binding_findings(self):
        if (self.review_profile != NATIVE_PROFILE or self.body != self.package.document()
                or len(self.files) != len(self.package.files)):
            return [("native_payload_binding_invalid", "native review material differs from its package identity")]
        for entry, file in zip(self.package.files, self.files):
            if (not isinstance(file, NativeReviewFile) or file.entry != entry or type(file.payload) is not bytes
                    or len(file.payload) != entry.size_bytes or sha256_hex(file.payload) != entry.digest):
                return [("native_payload_binding_invalid", "a complete payload differs from its package identity")]
        return []


class NativeCatalogue:
    """Adapter over the factory's version-three files, using the existing typed package identity."""

    @classmethod
    def load(cls, folder: Path, repository: Path):
        root, repository = Path(folder).absolute(), Path(repository).resolve()
        if not root.is_dir() or root.resolve() != root:
            refuse("native_root_invalid", "a native review root must be a plain existing directory")
        record = read_record(json_document(regular_bytes(root, "items.json", MAX_METADATA_BYTES)), NATIVE_ITEMS,
                             ("source_revision", "source_digests", "publication", "items"))
        if record["publication"] != "not_published":
            refuse("native_publication_invalid", "this adapter accepts unpublished candidates only")
        if type(record["items"]) is not list or not 1 <= len(record["items"]) <= MAX_ITEMS:
            refuse("native_population_out_of_bounds", "the native population is bounded and nonempty")
        revision = record["source_revision"]
        if type(revision) is not str or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
            refuse("native_source_revision_invalid", "sources require an exact committed revision")
        instance = cls()
        instance.folder, instance.repository = root, repository
        instance.source_revision = revision
        instance.items_record_type, instance.review_record_sha256 = NATIVE_ITEMS, ""
        instance._rows, instance._specifications, instance._payloads, instance._sources = {}, {}, {}, {}
        instance._read_sources(record["source_digests"])
        names = sorted(path.name for path in root.glob("specifications-[0-9][0-9][0-9].json"))
        if not names:
            refuse("native_specifications_missing", "the catalogue has no native specification populations")
        for number, name in enumerate(names, 1):
            part = read_record(json_document(regular_bytes(root, name, MAX_METADATA_BYTES)), NATIVE_SPECIFICATIONS,
                               ("population", "populations", "specifications"))
            if (type(part["population"]) is not int or type(part["populations"]) is not int
                    or part["population"] != number or part["populations"] != len(names)
                    or type(part["specifications"]) is not list):
                refuse("native_population_inconsistent", "the specification populations must be complete")
            for raw in part["specifications"]:
                spec = read_part(raw, "native specification", SPEC_FIELDS)
                if type(spec["id"]) is not str or spec["id"] in instance._specifications:
                    refuse("native_identity_duplicate", "each native specification has one identity")
                instance._specifications[spec["id"]] = spec
        for raw in record["items"]:
            row = read_part(raw, "native item", ITEM_FIELDS)
            reference = read_record(row["reference"], HARNESS_ITEM_RECORD, REFERENCE_FIELDS)
            identity = reference.get("identity")
            if type(identity) is not str or identity in instance._rows or identity not in instance._specifications:
                refuse("native_identity_invalid", "each native item needs its matching specification")
            instance._rows[identity] = row
            instance._payloads[identity] = instance._verified_files(identity, row, instance._specifications[identity])
        if set(instance._rows) != set(instance._specifications):
            refuse("native_population_inconsistent", "items and specifications must name the same population")
        return instance

    def _read_sources(self, sources):
        """Original items cite files of this repository at the pinned revision, its licence among them."""
        if type(sources) is not dict or "LICENSE" not in sources or len(sources) > MAX_SOURCES:
            refuse("native_sources_invalid", "source digests include the original licence and stay within the bound")
        self.source_digests = dict(sources)
        for path, expected in sources.items():
            payload = regular_bytes(self.repository, path, MAX_SOURCE_BYTES)
            if sha256_hex(payload) != expected:
                refuse("native_source_binding_invalid", "the cited source snapshot differs from its declared digest")
            try:
                _checked_source(self.repository, self.source_revision, path, expected)
            except PreparationError:
                refuse("native_source_binding_invalid", "a source differs from its committed declared bytes")
            try:
                self._sources[path] = CitedSource(path, self.source_revision, sha256_hex(payload), payload.decode("utf-8"))
            except UnicodeError:
                refuse("native_source_not_text", "a cited source is not UTF-8 text")

    def _check_provenance(self, row, spec, package):
        """Original MIT authorship bound to the pinned sources of this repository."""
        reference = row["reference"]
        provenance = read_part(spec["provenance"], "native provenance",
                               ("authoring", "source_revision", "source_digests", "license"))
        licence = read_part(provenance["license"], "native licence", ("expression", "path", "sha256"))
        if (provenance["authoring"] != "original_assistant_authored" or provenance["source_revision"] != self.source_revision
                or licence != {"expression": "MIT", "path": "LICENSE", "sha256": self.source_digests["LICENSE"]}
                or reference.get("license") != "MIT"):
            refuse("native_provenance_invalid", "only source-bound original MIT candidates use this profile")
        paths = spec["sources"]
        if (type(paths) is not list or not paths or any(type(path) is not str for path in paths)
                or len(set(paths)) != len(paths) or "LICENSE" not in paths
                or any(path not in self._sources for path in paths)
                or provenance["source_digests"] != {path: self.source_digests[path] for path in paths if path != "LICENSE"}
                or reference.get("source_ref") != f"{paths[0]}@{self.source_revision}"):
            refuse("native_source_binding_invalid", "the native source inventory must match its pinned declarations")

    def _check_producer(self, row):
        producer = read_part(row["producer"], "native producer", ("producer_identity", "family", "method_identity"))
        if (any(type(value) is not str or not value.strip() or len(value) > 160
                or any(ord(character) < 32 for character in value) for value in producer.values())
                or re.fullmatch(r"[a-z][a-z0-9_.-]*(?:/[a-z0-9_.-]+)*/v[1-9][0-9]*", producer["method_identity"]) is None):
            refuse("native_producer_invalid", "a native producer declares identity, family and versioned method")
        return producer

    def _verified_files(self, identity, row, spec):
        try:
            package = CataloguePackage.from_dict(row["package"])
        except (ServiceRuntimeError, TypeError, ValueError):
            refuse("native_package_invalid", "the native item needs a valid typed package")
        if package.body_form != "package" or sum(file.size_bytes for file in package.files) > MAX_PAYLOAD_BYTES:
            refuse("native_package_out_of_bounds", "native review requires a bounded complete package")
        reference = row["reference"]
        for name in ("package", "package_root", "body_path", "producer", "dependencies"):
            if row[name] != spec[name]:
                refuse("native_item_specification_mismatch", "item and specification declarations disagree")
        for name in ("kind", "purpose", "styles", "declared_effects"):
            if reference.get(name) != spec[name]:
                refuse("native_item_specification_mismatch", "reference and specification declarations disagree")
        if (spec["package_digest"] != package.package_digest or reference.get("digest") != package.package_digest
                or type(reference.get("size_bytes")) is not int or reference["size_bytes"] != package.served_size
                or reference.get("source_layer") != "harness_local" or reference.get("family") != "harness"):
            refuse("native_package_binding_invalid", "the reference must name the exact native package")
        expected_root, expected_body = f"packages/{identity}", f"bodies/{identity}.package.json"
        if row["package_root"] != expected_root or row["body_path"] != expected_body:
            refuse("native_package_path_invalid", "the native package paths must bind the selected identity")
        self._check_provenance(row, spec, package)
        self._check_producer(row)
        if (type(row["dependencies"]) is not list or len(row["dependencies"]) > 64
                or any(type(value) is not str or not value.strip() or len(value) > 200 for value in row["dependencies"])):
            refuse("native_dependencies_invalid", "dependencies are a bounded explicit string list")
        if regular_bytes(self.folder, expected_body, MAX_METADATA_BYTES) != package.document():
            refuse("native_package_document_mismatch", "the served document must be the canonical package bytes")
        root = self.folder / expected_root
        if not root.is_dir() or root.resolve() != root:
            refuse("native_package_root_invalid", "the package tree must be a plain directory")
        expected = {file.path for file in package.files}
        found = set()
        pending, visited = [root], 0
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    visited += 1
                    if visited > 576:
                        refuse("native_inventory_out_of_bounds", "the native tree exceeds the bounded inventory")
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        found.add(Path(entry.path).relative_to(root).as_posix())
                    else:
                        refuse("native_path_not_regular", "the package contains a link or special file")
        if found != expected:
            refuse("native_inventory_mismatch", "the complete package tree must equal its declared files")
        files = []
        for entry in package.files:
            payload = regular_bytes(root, entry.path, min(entry.size_bytes, MAX_FILE_BYTES))
            if len(payload) != entry.size_bytes or sha256_hex(payload) != entry.digest:
                refuse("native_file_binding_invalid", "a payload differs from its declared exact bytes")
            file = NativeReviewFile(entry, payload)
            _validated_text = file.text  # validate declared text before any reviewer sees it
            files.append(file)
        return package, tuple(files)

    def identities(self):
        return tuple(self._rows)

    def not_reviewed(self):
        return self.identities()

    def item(self, identity):
        return json.loads(json.dumps(self._rows[identity]))

    def outcome(self, identity):
        return "not_reviewed" if identity in self._rows else ""

    def producer_for(self, identity):
        value = self._rows[identity]["producer"]
        return Producer(value["producer_identity"], value["family"])

    def producer_declaration(self, families):
        producers = {identity: self.producer_for(identity) for identity in self.identities()}
        if any(producer.family not in families for producer in producers.values()):
            refuse("native_producer_family_unknown", "a declared producer family is outside the panel vocabulary")
        try:
            folder = self.folder.relative_to(self.repository).as_posix()
        except ValueError:
            # Library bodies live outside the public repository. Such a catalogue is named by its absolute
            # folder; the dated review record's reader refuses any absolute path, so a committed record can
            # never point outside the repository.
            folder = self.folder.as_posix()
        return ProducerDeclaration(folder, next(iter(producers.values())), MappingProxyType(producers),
                                   f"{folder}/items.json", "Producer identity, family and versioned method are declared per item.")

    def body_bytes(self, identity):
        return self._payloads[identity][0].document()

    def population_bodies(self):
        return {identity: b"\n".join(file.entry.path.encode() + b"\n" + file.payload for file in files)
                for identity, (_package, files) in self._payloads.items()}

    def request(self, identity, producer, criteria, instructions_sha256):
        if identity not in self._rows:
            refuse("unknown_item_identity", "the selected native item is absent from this catalogue")
        if producer != self.producer_for(identity) or NATIVE_GROUNDING not in criteria.groundings:
            refuse("native_review_profile_mismatch", "native review requires its exact producer and native criteria")
        row, spec = self.item(identity), self._specifications[identity]
        package, files = self._payloads[identity]
        return NativePackageReviewRequest(identity, row["body_path"], package.document(), json.dumps(row, sort_keys=True),
            tuple(self._sources[path] for path in spec["sources"]), producer, criteria, instructions_sha256,
            package, files, tuple(row["dependencies"]), json.dumps(spec, sort_keys=True))
