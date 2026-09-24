"""Normalize one copied package into catalogue_package/v1 and its candidate record.

```text
One copied package (catalogue_package/v1, body form "package")
├── every upstream member, byte for byte, at its place in the package folder, with its role
├── the governing licence texts and every notice file, when they are not members already
├── ATTRIBUTION.md: the repository, commit, licence and every file's upstream path and digest
└── the package digest: SHA-256 of the canonical package document
```

The candidate record `licensed_import_candidate/v1` carries the package,
each file's upstream path, git object identity and licence, the primary
file's `outside_source_provenance/v1` record, the documented native
placements, the declared effects with the rule that declared each, the
caution findings for the reviewers, the plugin a part belongs to and the
sources that found it. `CataloguePackage` owns the path, size and role
rules, so a package it refuses is refused here with its code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from loop_engine.core.library_ingestion.duplicates import normalized
from loop_engine.core.library_ingestion.provenance import GITHUB_ORIGIN, ORIGIN_HOSTS, OutsideSourceProvenance
from loop_engine.core.library_ingestion.record_rules import LibraryRecordError, bytes_digest, canonical_digest
from loop_engine.core.service_runtime.catalogue_packages import (
    EXECUTABLE_EFFECT, PACKAGE_BODY, CataloguePackage, CataloguePackageFile)
from loop_engine.core.service_runtime.records import ServiceRuntimeError

from .checks import frontmatter_of
from .harness_kinds import file_role, media_type, package_path, placements
from .licensing import ATTRIBUTION_NAME, attribution_text, carried_placements
from .records import (
    ATTRIBUTION_FILE, CANDIDATE_LIFECYCLE, CANDIDATE_RECORD_TYPE, IMPORTED_VERBATIM, LICENCE_TEXT, UPSTREAM_FILE,
    candidate_record_id, upstream_key)

_PACKAGE_CODES = {"package_path_invalid": "package_path_invalid", "package_path_duplicate": "package_path_invalid",
                  "package_file_too_large": "package_too_large", "package_too_large": "package_too_large",
                  "package_invalid": "package_too_many_files", "package_media_type_invalid": "package_path_invalid"}
MINIMUM_PRIMARY_CHARACTERS = 40


class PackageRefused(ValueError):
    """The package cannot be normalized; the code is a package-stage refusal reason."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


@dataclass
class BuiltCandidate:
    payload: dict
    bodies: dict
    package: CataloguePackage
    comparison_text: str


def comparison_text(path: str, payload: bytes) -> str:
    """What duplicates are judged on: a Markdown body without its frontmatter, or the whole text."""
    text = payload.decode("utf-8", "replace")
    if path.lower().endswith((".md", ".mdc")) and text.startswith("---"):
        closing = text.find("\n---", 3)
        if closing != -1:
            return text[closing + 4:]
    return text


def _file(path: str, payload: bytes, role: str) -> CataloguePackageFile:
    try:
        return CataloguePackageFile(path, bytes_digest(payload), len(payload), media_type(path), role)
    except ServiceRuntimeError as error:
        raise PackageRefused(_PACKAGE_CODES.get(error.code, "package_path_invalid"), path[:120]) from None


def build_candidate(*, plan, repository: str, commit: str, fetched_at: str, member_bytes: dict, oids: dict,
                    licence, licence_bytes: dict, findings, effects: tuple, effect_evidence: tuple,
                    sources, fetch_digest: str, request_digest: str, imported_on: str,
                    repository_facts: dict) -> BuiltCandidate:
    """The candidate record and every body of one package whose every file may be copied."""
    primary = member_bytes.get(plan.primary)
    if primary is None:
        raise PackageRefused("empty_package", plan.primary[:120])
    primary_text = primary.decode("utf-8", "replace") if _is_text(primary) else None
    if primary_text is None:
        raise PackageRefused("primary_file_not_text", plan.primary[:120])
    if len(primary_text.strip()) < MINIMUM_PRIMARY_CHARACTERS:
        raise PackageRefused("primary_file_too_short", plan.primary[:120])
    bodies, files, rows, entries = {}, [], [], []
    for upstream, payload in sorted(member_bytes.items()):
        path = package_path(plan.kind, plan.root, upstream)
        role = file_role(plan.kind, plan.root, upstream)
        entry = _file(path, payload, role)
        entries.append(entry)
        bodies[entry.digest] = payload
        spdx = (licence.per_file.get(upstream) or {}).get("spdx_expression")
        files.append({**entry.to_dict(), "origin": UPSTREAM_FILE, "upstream_path": upstream,
                      "git_blob_sha": oids.get(upstream), "licence_spdx": spdx})
        rows.append((path, upstream, entry.digest))
    placed = carried_placements([path for path in licence.carried if path not in member_bytes],
                                [entry.path for entry in entries])
    for upstream, path in sorted(placed.items()):
        payload = licence_bytes[upstream]
        entry = _file(path, payload, "other")
        entries.append(entry)
        bodies[entry.digest] = payload
        files.append({**entry.to_dict(), "origin": LICENCE_TEXT, "upstream_path": upstream,
                      "git_blob_sha": oids.get(upstream), "licence_spdx": None})
        rows.append((path, upstream, entry.digest))
    licence_names = [placed.get(path) or package_path(plan.kind, plan.root, path) for path in licence.carried]
    taken = {entry.path.casefold() for entry in entries}
    attribution_name = ATTRIBUTION_NAME if ATTRIBUTION_NAME.casefold() not in taken else "ATTRIBUTION.baltor.md"
    attribution = attribution_text(repository=repository, commit=commit, spdx=licence.spdx_expression, rows=rows,
                                   licence_names=licence_names, imported_on=imported_on)
    entry = _file(attribution_name, attribution, "other")
    entries.append(entry)
    bodies[entry.digest] = attribution
    files.append({**entry.to_dict(), "origin": ATTRIBUTION_FILE, "upstream_path": None, "git_blob_sha": None,
                  "licence_spdx": None})
    try:
        package = CataloguePackage(tuple(entries), PACKAGE_BODY)
    except ServiceRuntimeError as error:
        raise PackageRefused(_PACKAGE_CODES.get(error.code, "package_too_large"), plan.root[:120]) from None
    effects = tuple(effects)
    if package.executable and EXECUTABLE_EFFECT not in effects:
        effects = tuple(effect for effect in effects if effect != "pure") + (EXECUTABLE_EFFECT,)
    try:
        provenance = OutsideSourceProvenance(
            GITHUB_ORIGIN, ORIGIN_HOSTS[GITHUB_ORIGIN], repository, commit, plan.primary, bytes_digest(primary),
            len(primary), oids[plan.primary], fetch_digest, licence.primary_evidence, fetched_at, request_digest)
    except LibraryRecordError as error:
        raise PackageRefused("file_bytes_mismatch", error.code) from None
    front = frontmatter_of(primary_text)
    findings = list(findings) + another_source_cautions(front, repository, plan.primary)
    key = upstream_key(GITHUB_ORIGIN, repository, plan.root, plan.kind)
    record_id = candidate_record_id(plan.kind, key, package.package_digest)
    description = front.get("description") if isinstance(front.get("description"), str) else None
    comparison = comparison_text(plan.primary, primary)
    payload = {
        "record_type": CANDIDATE_RECORD_TYPE, "record_id": record_id, "upstream_key": key, "kind": plan.kind,
        "native_format": plan.native_format, "name": plan.name,
        "declared_name": front.get("name") if isinstance(front.get("name"), str) else None,
        "description": description[:1024] if description else None,
        "package": package.to_dict(), "package_digest": package.package_digest, "files": files,
        "licence": {"spdx_expression": licence.spdx_expression, "reason": licence.reason,
                    "texts": sorted(licence_names), "attribution": attribution_name},
        "provenance": provenance.to_record(), "placements": placements(plan),
        "declared_effects": list(effects), "effect_evidence": list(effect_evidence),
        "findings": sorted(findings, key=lambda row: (row.get("path", ""), row["line"], row["rule"])),
        "plugin": plan.plugin, "sources": sorted(set(sources)), "repository": repository_facts,
        "authoring": IMPORTED_VERBATIM, "lifecycle": CANDIDATE_LIFECYCLE,
        "qualification": "not_independently_reviewed", "imported_on": imported_on,
        "comparison": {"primary_sha256": bytes_digest(primary),
                       "normalized_sha256": bytes_digest(normalized(comparison).encode("utf-8"))},
        "merged": [], "version": {"previous_record_id": None, "supersedes": []},
        "compatibility": {"component_kind": plan.kind, "native_format": plan.native_format,
                          "package_format": "catalogue_package/v1"},
        "evidence": evidence_states()}
    return BuiltCandidate(payload, bodies, package, comparison)


_SOURCE_KEYS = ("source", "author", "origin", "upstream", "original", "repository", "homepage", "url")
_GITHUB_OWNER = re.compile(r"github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100})")


def another_source_cautions(front: dict, repository: str, path: str) -> list:
    """A caution when a file's own metadata names a GitHub repository other than the one it was read from.

    A collection often keeps the original author's address in a copied
    file. The licence gate cannot see that the collection's licence may not
    be the original's, so the reviewer is told which file names another source.
    """
    values = []
    for key in _SOURCE_KEYS:
        value = front.get(key)
        if isinstance(value, dict):
            values += [str(item) for item in value.values()]
        elif value is not None:
            values.append(str(value))
    metadata = front.get("metadata")
    if isinstance(metadata, dict):
        values += [str(metadata.get(key)) for key in _SOURCE_KEYS if metadata.get(key) is not None]
    for value in values:
        for match in _GITHUB_OWNER.finditer(value):
            named = f"{match.group(1)}/{re.sub(r'[.]git$', '', match.group(2))}".lower()
            if named != repository.lower():
                return [{"rule": "names_another_upstream_source", "severity": "caution", "line": 0,
                         "engine_id": "import_static_rules", "path": path}]
    return []


#: The evidence states of a package, in order. Import establishes the first two: the exact
#: source revision and selection (resolved) and the complete files with their digests
#: (materialized). Available, loaded, used and verified need a harness, a run and an
#: independent check, so import records them as not established, never as true.
EVIDENCE_STATES = ("resolved", "materialized", "available", "loaded", "used", "verified")
ESTABLISHED_BY_IMPORT = ("resolved", "materialized")


def evidence_states() -> dict:
    return {state: state in ESTABLISHED_BY_IMPORT for state in EVIDENCE_STATES}


def _is_text(payload: bytes) -> bool:
    try:
        payload.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def fetch_identity(engine_id: str, repository: str, commit: str) -> tuple:
    """(fetch digest, request digest) naming how the bytes were read: engine, repository and commit."""
    request = canonical_digest({"engine": engine_id, "repository": repository, "commit": commit,
                                "operation": "read_selected_blobs"})
    return canonical_digest({"request": request, "verified_by": "git_blob_identity"}), request
