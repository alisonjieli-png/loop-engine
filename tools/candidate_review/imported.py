"""Read imported licensed packages for the independent review panel, without executing, flattening or admitting them.

The licensed import (`tools/licensed_import`) exports packages copied byte for byte from public repositories under
a permissive licence, in the version-three catalogue layout this panel reads for original packages. Three things
differ on purpose, and this reader checks each of them in place of the original-package rule:

```text
Imported package, as the panel reads it
├── sources: none from this repository
│   └── the items record lists no source digests, and nothing is reread from this repository
├── provenance: the upstream repository, its immutable revision, the path and the source digest
│   ├── the source reference names exactly those four
│   ├── the source digest is one of the package's own files
│   └── the licence evidence decided "verbatim permitted", and its governing licence text is a file
│       of the package, byte for byte, beside the attribution file
└── producer: the upstream author, a family no reviewing model belongs to
    └── so no reviewer is excluded as the producer, and the Community rule is unchanged
```

Every package byte, path, inventory and reference binding is checked exactly as for an original package, by the
reader this one extends. Nothing here approves anything.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from .catalogue import CandidateReviewRequest
from .configuration import ProducerDeclaration
from .native import (
    MAX_METADATA_BYTES,
    NativeCatalogue,
    NativePackageReviewRequest,
    NativeReviewFile,
    json_document,
    regular_bytes,
)
from .records import digest, read_part, read_record, refuse, sha256_hex

IMPORTED_PROFILE = "imported_licensed_package/v1"
IMPORTED_GROUNDING = "imported_licensed_package"
IMPORTED_REQUEST = "candidate_imported_package_review_request/v1"
EXPORT_REPORT, EXPORT_FILE = "licensed_import_review_export/v1", "export-report.json"
OUTSIDE_PROVENANCE = "outside_source_provenance/v1"
LICENCE_EVIDENCE = "outside_licence_evidence/v1"
#: The producer of an imported package: its upstream author, a family no reviewing installation belongs to.
UPSTREAM_FAMILY = "upstream_author"
AUTHORING = "imported_verbatim_under_permissive_licence"
VERBATIM = "verbatim_permitted"
IMPORT_METHOD = re.compile(r"licensed_import/[a-z0-9_.-]+/v[1-9][0-9]*")
REVISION = re.compile(r"[0-9a-f]{40}")
PROVENANCE_FIELDS = ("authoring", "findings", "harness_kind", "license", "merged_sources", "outside_provenance",
                     "placements", "profile", "store_record_id")
PLACEMENT_FIELDS = ("basis", "harness", "path", "scope", "support")
LICENCE_FIELDS = ("attribution", "expression", "texts")
OUTSIDE_FIELDS = ("fetch_digest", "fetched_at", "git_blob_sha", "immutable_revision", "licence_evidence", "origin",
                  "origin_host", "path", "repository", "request_digest", "source_digest", "source_size_bytes")
EVIDENCE_FIELDS = ("decision", "detector", "file_level_notices", "governing_file", "reason", "repository_licence",
                   "spdx_expression")
GOVERNING_FIELDS = ("matched_spdx", "path", "sha256", "similarity")
REPORT_FIELDS = ("by_first_source_and_licence", "code_revision", "differs_from_original_profile", "files", "items",
                 "items_digest", "kinds", "licences", "populations", "profile", "repositories", "selection",
                 "written_at")


def _plain_text(value, limit=400):
    return (type(value) is str and value.strip() and len(value) <= limit
            and not any(ord(character) < 32 for character in value))


@dataclass(frozen=True)
class ImportedPackageReviewRequest(NativePackageReviewRequest):
    """The same exact package material as an original request, under the imported profile and its criteria."""

    review_profile: str = IMPORTED_PROFILE

    @property
    def grounding(self):
        return IMPORTED_GROUNDING

    @property
    def request_sha256(self):
        return digest({"record_type": IMPORTED_REQUEST, "base": CandidateReviewRequest.request_sha256.fget(self),
                       "package": self.package.to_dict(), "profile": self.review_profile,
                       "specification": json.loads(self.specification_json)})

    def to_record(self):
        return {**CandidateReviewRequest.to_record(self), "record_type": IMPORTED_REQUEST,
                "review_profile": self.review_profile, "package": self.package.to_dict(),
                "specification": json.loads(self.specification_json)}

    def package_binding_findings(self):
        if (self.review_profile != IMPORTED_PROFILE or self.body != self.package.document()
                or len(self.files) != len(self.package.files)):
            return [("imported_payload_binding_invalid", "imported review material differs from its package identity")]
        for entry, file in zip(self.package.files, self.files):
            if (not isinstance(file, NativeReviewFile) or file.entry != entry or type(file.payload) is not bytes
                    or len(file.payload) != entry.size_bytes or sha256_hex(file.payload) != entry.digest):
                return [("imported_payload_binding_invalid", "a complete payload differs from its package identity")]
        return []


class ImportedCatalogue(NativeCatalogue):
    """The licensed import's review export, read with the original reader's package rules and the imported ones."""

    @classmethod
    def load(cls, folder, repository):
        instance = super().load(folder, repository)
        instance._check_export_report()
        return instance

    def _read_sources(self, sources):
        if sources != {}:
            refuse("imported_sources_invalid", "an imported package cites no source of this repository")
        self.source_digests = {}

    def _check_export_report(self):
        report = read_record(json_document(regular_bytes(self.folder, EXPORT_FILE, MAX_METADATA_BYTES)), EXPORT_REPORT,
                             REPORT_FIELDS)
        populations = len(list(self.folder.glob("specifications-[0-9][0-9][0-9].json")))
        if (report["profile"] != IMPORTED_PROFILE or report["items"] != len(self._rows)
                or report["code_revision"] != self.source_revision or report["populations"] != populations):
            refuse("imported_export_invalid", "the export report names this imported profile, population and revision")

    def _check_provenance(self, row, spec, package):
        reference = row["reference"]
        if spec["sources"] != [] or spec["symbols"] != []:
            refuse("imported_sources_invalid", "an imported package cites no source of this repository")
        provenance = read_part(spec["provenance"], "imported provenance", PROVENANCE_FIELDS)
        licence = read_part(provenance["license"], "imported licence", LICENCE_FIELDS)
        outside = read_record(provenance["outside_provenance"], OUTSIDE_PROVENANCE, OUTSIDE_FIELDS)
        evidence = read_record(outside["licence_evidence"], LICENCE_EVIDENCE, EVIDENCE_FIELDS)
        governing = read_part(evidence["governing_file"], "governing licence file", GOVERNING_FIELDS)
        files = {entry.path: entry.digest for entry in package.files}
        texts = licence["texts"]
        if (provenance["authoring"] != AUTHORING or evidence["decision"] != VERBATIM
                or not _plain_text(licence["expression"]) or licence["expression"] != reference.get("license")
                or evidence["spdx_expression"] != licence["expression"]
                or type(texts) is not list or not texts or len(set(texts)) != len(texts)
                or any(type(path) is not str or path not in files for path in texts)
                or licence["attribution"] not in files or licence["attribution"] in texts
                or governing["sha256"] not in {files[path] for path in texts}):
            refuse("imported_provenance_invalid",
                   "an imported package carries its licence text, its attribution and a verbatim licence decision")
        placements = provenance["placements"]
        if (provenance["profile"] != IMPORTED_PROFILE or not _plain_text(provenance["store_record_id"])
                or type(placements) is not list or not 1 <= len(placements) <= 32
                or any(not all(_plain_text(value) for value in read_part(placement, "placement", PLACEMENT_FIELDS).values())
                       for placement in placements)):
            refuse("imported_provenance_invalid", "an imported package names its profile, store record and placements")
        revision = outside["immutable_revision"]
        named = (outside["origin"], outside["origin_host"], outside["repository"], outside["path"],
                 provenance["harness_kind"])
        if (type(revision) is not str or REVISION.fullmatch(revision) is None
                or not all(_plain_text(value) for value in named)
                or outside["source_digest"] not in files.values()
                or reference.get("source_ref")
                != f"{outside['origin_host']}/{outside['repository']}/{outside['path']}@{revision}"):
            refuse("imported_upstream_invalid", "the upstream repository, revision, path and source bytes bind the package")

    def _check_producer(self, row):
        producer = super()._check_producer(row)
        if producer["family"] != UPSTREAM_FAMILY or IMPORT_METHOD.fullmatch(producer["method_identity"]) is None:
            refuse("imported_producer_invalid", "an imported package names its upstream author as the producer")
        return producer

    def producer_declaration(self, families):
        """Every producer is the upstream author, and no reviewing family may carry that name."""
        if UPSTREAM_FAMILY in families:
            refuse("imported_producer_family_reused", "the upstream author family is never a reviewing family")
        producers = {identity: self.producer_for(identity) for identity in self.identities()}
        if any(producer.family != UPSTREAM_FAMILY for producer in producers.values()):
            refuse("imported_producer_invalid", "an imported package names its upstream author as the producer")
        try:
            folder = self.folder.relative_to(self.repository).as_posix()
        except ValueError:
            folder = self.folder.as_posix()
        return ProducerDeclaration(folder, next(iter(producers.values())), MappingProxyType(producers),
                                   f"{folder}/items.json", "Each imported item names its upstream author as producer.")

    def request(self, identity, producer, criteria, instructions_sha256):
        if identity not in self._rows:
            refuse("unknown_item_identity", "the selected imported item is absent from this catalogue")
        if producer != self.producer_for(identity) or IMPORTED_GROUNDING not in criteria.groundings:
            refuse("imported_review_profile_mismatch", "imported review requires its exact producer and imported criteria")
        row, spec = self.item(identity), self._specifications[identity]
        package, files = self._payloads[identity]
        return ImportedPackageReviewRequest(identity, row["body_path"], package.document(), json.dumps(row, sort_keys=True),
            (), producer, criteria, instructions_sha256, package, files, tuple(row["dependencies"]),
            json.dumps(spec, sort_keys=True))


def is_imported_catalogue(folder) -> bool:
    """True when a catalogue folder holds a licensed import review export, which this reader must read."""
    return (Path(folder) / EXPORT_FILE).is_file()
