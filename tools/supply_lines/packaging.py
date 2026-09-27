"""Build one supply package: its files, licence texts, attribution, checks and candidate record.

```text
One supplied package (catalogue_package/v1, body form "package")
├── generated files: the harness files, the code, the schemas, the tests and README.md
├── upstream files copied verbatim, when a licence allows it (a data file), with their digests
├── LICENSE: the package licence text, and UPSTREAM-LICENSE when the upstream's licence differs
└── ATTRIBUTION.md: the generator, every fact source with its digest and licence, every file's origin
```

The static checks of the licensed import (the built-in rules and the import's
own rules) run over every text file before the record is built; a blocking
finding refuses the package by rule name and a caution travels with it for
the reviewer. A clean check is triage, not proof of safety.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from loop_engine.core.library_ingestion.duplicates import normalized
from loop_engine.core.library_ingestion.record_rules import bytes_digest
from loop_engine.core.service_runtime.catalogue_attributes import FORM_DECLARED, component_form_record
from loop_engine.core.service_runtime.catalogue_packages import PACKAGE_BODY, CataloguePackage, CataloguePackageFile

from licensed_import.checks import StaticChecks, blocking_rules
from licensed_import.harness_kinds import media_type

from .records import (
    ATTRIBUTION, AUTHORING, CANDIDATE_RECORD_TYPE, FILE_ORIGINS, GENERATED, LICENCE_TEXT, REVIEW_PROFILE,
    SupplyRecordError, licence_allowed, read_supply_candidate, record_id)

ATTRIBUTION_NAME = "ATTRIBUTION.md"
LICENCE_NAME = "LICENSE"
UPSTREAM_LICENCE_NAME = "UPSTREAM-LICENSE"
#: The review panel reads files up to these bounds (tools/licensed_import/review_export.py); a package above them
#: could never be reviewed, so a line refuses it before it is stored.
MAXIMUM_REVIEW_FILE_BYTES = 256 * 1024
MAXIMUM_REVIEW_PACKAGE_BYTES = 2 * 1024 * 1024
_CHECKS = None


def static_checks() -> StaticChecks:
    """The licensed import's static checks, built once per process."""
    global _CHECKS
    if _CHECKS is None:
        _CHECKS = StaticChecks({})
    return _CHECKS


@dataclass(frozen=True)
class PackageFile:
    path: str
    data: bytes
    role: str
    origin: str = GENERATED
    upstream: "dict | None" = None  # {"url": ..., "sha256": ...} for a verbatim copy


@dataclass
class SupplyPackage:
    """The facts one generator decided, before the package record is built."""

    line: str
    identity: str  # the stable upstream identity the key is derived from
    key: str
    kind: str
    native_format: str
    form: str
    name: str
    description: str
    files: list
    licence_expression: str
    provenance: dict
    placements: list
    effects: list  # [(effect, rule)]
    credentials: list
    tests: dict
    repository: dict
    generated_on: str
    comparison_text: str = ""
    findings: list = field(default_factory=list)


def attribution_text(package: SupplyPackage, rows) -> bytes:
    """ATTRIBUTION.md: who wrote the package from which facts, under which licences, file by file."""
    generator = package.provenance["generator"]
    lines = ["# Attribution", "",
             f"Baltor's deterministic generator `{generator['identity']}` version {generator['version']} "
             f"(code revision {generator['code_revision']}) wrote this package on {package.generated_on} from the "
             "facts listed below. No model wrote any of it.", "",
             f"Package licence: {package.licence_expression}.", "",
             "## Facts", "", "| Source | Role | Retrieved | SHA-256 | Licence |", "|---|---|---|---|---|"]
    for fact in package.provenance["facts"]:
        lines.append(f"| {fact['url']} | {fact['role']} | {fact['retrieved_at']} | `{fact['sha256']}` | "
                     f"{fact['licence']['spdx_expression']} ({fact['licence']['basis']}) |")
    lines += ["", "## Files", "", "| File | Origin | SHA-256 |", "|---|---|---|"]
    for path, origin, digest in rows:
        lines.append(f"| `{path}` | {origin} | `{digest}` |")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def _entry(path: str, data: bytes, role: str) -> CataloguePackageFile:
    return CataloguePackageFile(path, bytes_digest(data), len(data), media_type(path), role)


def build(package: SupplyPackage, *, check: bool = True) -> tuple:
    """(payload, bodies) of one package, or raise SupplyRecordError with a refusal reason."""
    if not licence_allowed(package.licence_expression):
        raise SupplyRecordError("licence_not_on_allowlist", package.licence_expression)
    if not any(row.path == LICENCE_NAME for row in package.files):
        raise SupplyRecordError("licence_files_missing", "a supplied package carries its licence text")
    if any(row.origin not in FILE_ORIGINS for row in package.files):
        raise SupplyRecordError("file_origins_invalid", "every file names its origin")
    files = sorted(package.files, key=lambda row: row.path)
    texts = [row.path for row in files if row.origin == LICENCE_TEXT]
    rows = [(row.path, row.origin, bytes_digest(row.data)) for row in files]
    attribution = attribution_text(package, rows)
    files.append(PackageFile(ATTRIBUTION_NAME, attribution, "other", ATTRIBUTION))
    if any(len(row.data) > MAXIMUM_REVIEW_FILE_BYTES for row in files) or \
            sum(len(row.data) for row in files) > MAXIMUM_REVIEW_PACKAGE_BYTES:
        raise SupplyRecordError("package_above_review_bound", package.name)
    entries = [_entry(row.path, row.data, row.role) for row in files]
    catalogue_package = CataloguePackage(tuple(entries), PACKAGE_BODY)
    findings = list(package.findings)
    if check:
        scanned = static_checks().scan({"package": [(row.path, row.data) for row in files]})
        findings += scanned.get("package", [])
        blocked = blocking_rules(findings)
        if blocked:
            raise SupplyRecordError("blocked_by_static_check", ",".join(blocked))
    effects = sorted({effect for effect, _rule in package.effects})
    evidence = [{"effect": effect, "rule": rule} for effect, rule in sorted(set(package.effects))]
    identity = record_id(package.line, package.key, catalogue_package.package_digest)
    payload = {
        "record_type": CANDIDATE_RECORD_TYPE, "record_id": identity, "upstream_key": package.key,
        "line": package.line, "kind": package.kind, "native_format": package.native_format,
        "component_form": component_form_record(package.form, package.kind, FORM_DECLARED),
        "name": package.name, "description": package.description[:1024],
        "package": catalogue_package.to_dict(), "package_digest": catalogue_package.package_digest,
        "files": [{**entry.to_dict(), "origin": row.origin, "upstream": row.upstream}
                  for entry, row in zip(entries, files)],
        "licence": {"spdx_expression": package.licence_expression, "texts": texts, "attribution": ATTRIBUTION_NAME},
        "provenance": package.provenance, "placements": package.placements, "declared_effects": effects,
        "effect_evidence": evidence, "credentials": sorted(set(package.credentials)), "tests": package.tests,
        "findings": sorted(findings, key=lambda row: (row.get("path", ""), row.get("line", 0), row["rule"])),
        "authoring": AUTHORING, "review_profile": REVIEW_PROFILE, "lifecycle": "candidate",
        "qualification": "not_independently_reviewed", "generated_on": package.generated_on,
        "repository": package.repository, "sources": [package.line], "merged": [],
        "comparison": {"normalized_sha256": bytes_digest(normalized(package.comparison_text or package.name)
                                                         .encode("utf-8"))},
        "version": {"previous_record_id": None},
        "evidence": {"resolved": True, "materialized": True, "available": False, "loaded": False, "used": False,
                     "verified": False}}
    read_supply_candidate(payload)
    bodies = {entry.digest: row.data for entry, row in zip(entries, files)}
    return payload, bodies
