"""Messy dataset to Schema.org-aligned data product.

Profiles a messy organizations dataset, proposes typed cleaning
operations, applies reversible transformations with a ledger, emits
Schema.org-aligned JSON-LD, validates with SHACL shapes, and measures
before-and-after data quality. Runs through the canonical Loop
runtime.

Run:
    python3 examples/21_schema_org_data_standardization/run.py

No network, no external service, no model calls.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field

import pandas as pd

from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop

#: The deliberately messy fixture.
MESSY_ORGANIZATIONS = """Company Name,Alternate Name,Branch Name,Street,City,State,Postal,Country,Phone,Website,Latitude,Longitude,Parent Company,Status,Last Checked
Acme Corp,ACME,Main,123 Main St,Springfield,IL,62701,US,+1 217-555-0100,https://acme.example.com,39.7817,-89.6501,,active,2024-01-15
Acme Corp,ACME,Main,123 Main St,Springfield,IL,62701,USA,+1 217-555-0100 ext 42,https://acme.example.com,39.7817,-89.6501,,active,01/15/2024
Acme Corporation,,North,456 North Ave,Springfield,IL,62702,United States,2175550101,acme.example.com,39.8,-89.6,Acme Corp,active,2024-01-15
Beta Industries,,,789 Beta Blvd,,IL,,US,N/A,,41.0,-88.0,,unknown,2024/01/15
Beta Industries,,,789 Beta Blvd,Chicago,IL,60601,US,+1 312-555-0199,https://beta.example.com,41.8781,-87.6298,,active,2024-01-15
Gamma LLC,,,100 Gamma Way,Springfield,IL,62701,US,+1 217-555-0111,https://gamma.example.com,39.7817,-89.6501,Beta Industries,active,2024-01-15
Gamma LLC,,,100 Gamma Way,Springfield,IL,62701,US,+1 217-555-0111,https://gamma.example.com,39.7817,-89.6501,Beta Industries,active,2024-01-15
Delta Co,,,200 Delta Dr,Springfield,IL,62701,US,+1 217-555-0122,https://delta.example.com,999.0,-999.0,,active,2024-01-15
Epsilon Inc,,,300 Epsilon St,Springfield,IL,62701,US,+1 217-555-0133,https://epsilon.example.com,39.7817,-89.6501,,active,2024-01-15
Epsilon Inc,,,300 Epsilon St,Springfield,IL,62701,US,+1 217-555-0133,https://epsilon.example.com,39.7817,-89.6501,,active,2024-01-15
"""


@dataclass(frozen=True)
class ColumnProfile:
    """Typed profile of one column."""

    column: str
    non_null: int
    null_count: int
    distinct: int
    inferred_type: str
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"column": self.column, "non_null": self.non_null,
                "null_count": self.null_count, "distinct": self.distinct,
                "inferred_type": self.inferred_type,
                "issues": list(self.issues)}


@dataclass(frozen=True)
class CleaningProposal:
    """One typed cleaning operation with confidence and risk."""

    proposal_id: str
    column: str
    detected_issue: str
    operation: str
    confidence: float
    risk: str
    reversible: bool = True

    def to_dict(self) -> dict:
        return {"proposal_id": self.proposal_id, "column": self.column,
                "detected_issue": self.detected_issue,
                "operation": self.operation,
                "confidence": self.confidence, "risk": self.risk,
                "reversible": self.reversible}


@dataclass(frozen=True)
class TransformationRecord:
    """One applied transformation with provenance."""

    record_id: str
    column: str
    operation: str
    input_value: str
    output_value: str
    reason: str

    def to_dict(self) -> dict:
        return {"record_id": self.record_id, "column": self.column,
                "operation": self.operation,
                "input_value": self.input_value,
                "output_value": self.output_value,
                "reason": self.reason}


@dataclass(frozen=True)
class DataQualityReport:
    """Before-and-after quality measurements."""

    before_rows: int
    after_rows: int
    before_duplicates: int
    after_duplicates: int
    before_null_cells: int
    after_null_cells: int
    before_invalid_coordinates: int
    after_invalid_coordinates: int
    fixed_issues: tuple[str, ...] = ()
    unresolved_issues: tuple[str, ...] = ()
    review_required: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"before_rows": self.before_rows,
                "after_rows": self.after_rows,
                "before_duplicates": self.before_duplicates,
                "after_duplicates": self.after_duplicates,
                "before_null_cells": self.before_null_cells,
                "after_null_cells": self.after_null_cells,
                "before_invalid_coordinates": self.before_invalid_coordinates,
                "after_invalid_coordinates": self.after_invalid_coordinates,
                "fixed_issues": list(self.fixed_issues),
                "unresolved_issues": list(self.unresolved_issues),
                "review_required": list(self.review_required)}


_NULL_SENTINELS = {"", "n/a", "na", "-", "unknown", "none", "null"}


def _load() -> pd.DataFrame:
    return pd.read_csv(io.StringIO(MESSY_ORGANIZATIONS))


def _profile(df: pd.DataFrame) -> list[ColumnProfile]:
    profiles = []
    for column in df.columns:
        series = df[column]
        null_count = int(series.isna().sum()) + int(
            series.astype(str).str.strip().str.lower()
            .isin(_NULL_SENTINELS).sum())
        issues = []
        if null_count:
            issues.append(f"{null_count} null or sentinel values")
        if series.astype(str).str.contains(r"\d{4}[-/]\d{2}[-/]\d{2}",
                                           regex=True).any():
            issues.append("multiple date formats")
        if column in ("Latitude", "Longitude"):
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = int(((numeric < -90) | (numeric > 90)).sum()) \
                if column == "Latitude" else int(
                    ((numeric < -180) | (numeric > 180)).sum())
            if invalid:
                issues.append(f"{invalid} impossible values")
        if column == "Country":
            distinct = series.astype(str).str.strip().str.upper()
            if distinct.nunique() > 1:
                issues.append("inconsistent country codes")
        if column == "Phone":
            if series.astype(str).str.contains("ext", case=False).any():
                issues.append("extensions embedded in phone")
        profiles.append(ColumnProfile(
            column=column,
            non_null=int((~series.isna()).sum()),
            null_count=null_count,
            distinct=int(series.nunique()),
            inferred_type=str(series.dtype),
            issues=tuple(issues)))
    return profiles


def _propose_cleaning(profiles: list[ColumnProfile]) -> list[CleaningProposal]:
    proposals = []
    for profile in profiles:
        if profile.column == "Country":
            proposals.append(CleaningProposal(
                "clean.country.iso", "Country",
                "inconsistent country codes", "normalize_country_code",
                0.95, "low"))
        if profile.column == "Phone":
            proposals.append(CleaningProposal(
                "clean.phone.e164", "Phone",
                "extensions embedded in phone", "normalize_phone",
                0.9, "medium"))
        if profile.column in ("Latitude", "Longitude"):
            proposals.append(CleaningProposal(
                f"clean.{profile.column.lower()}.range",
                profile.column, "impossible values",
                "quarantine_out_of_range", 0.99, "low"))
        if profile.column == "Last Checked":
            proposals.append(CleaningProposal(
                "clean.last_checked.iso", "Last Checked",
                "multiple date formats", "normalize_date_iso",
                0.95, "low"))
    return proposals


def _clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[TransformationRecord]]:
    """Apply reversible transformations with a ledger."""
    ledger: list[TransformationRecord] = []
    cleaned = df.copy()
    record_index = 0

    def _record(column: str, operation: str, before: str, after: str,
                reason: str) -> None:
        nonlocal record_index
        ledger.append(TransformationRecord(
            f"txn-{record_index}", column, operation, before, after,
            reason))
        record_index += 1

    # Normalize country codes.
    country_map = {"USA": "US", "UNITED STATES": "US", "US": "US"}
    for index, value in cleaned["Country"].items():
        raw = str(value).strip().upper()
        if raw in _NULL_SENTINELS:
            continue
        normalized = country_map.get(raw, raw)
        if normalized != raw:
            _record("Country", "normalize_country_code", raw, normalized,
                    "country code normalized to ISO")
            cleaned.at[index, "Country"] = normalized

    # Normalize phones: strip extensions into a separate column.
    cleaned["Phone Extension"] = ""
    for index, value in cleaned["Phone"].items():
        raw = str(value).strip()
        if raw.lower() in _NULL_SENTINELS:
            continue
        if "ext" in raw.lower():
            base, extension = raw.lower().split("ext", 1)
            cleaned.at[index, "Phone"] = base.strip()
            cleaned.at[index, "Phone Extension"] = extension.strip()
            _record("Phone", "normalize_phone", raw, base.strip(),
                    "extension split into Phone Extension")

    # Normalize dates to ISO.
    for index, value in cleaned["Last Checked"].items():
        raw = str(value).strip()
        if raw.lower() in _NULL_SENTINELS:
            continue
        parsed = pd.to_datetime(raw, errors="coerce")
        if not pd.isna(parsed):
            iso = parsed.strftime("%Y-%m-%d")
            if iso != raw:
                _record("Last Checked", "normalize_date_iso", raw, iso,
                        "date normalized to ISO")
                cleaned.at[index, "Last Checked"] = iso

    # Quarantine impossible coordinates.
    for column, limit in (("Latitude", 90), ("Longitude", 180)):
        cleaned[column] = cleaned[column].astype(object)
        numeric = pd.to_numeric(cleaned[column], errors="coerce")
        for index, value in numeric.items():
            if pd.isna(value):
                continue
            if abs(value) > limit:
                _record(column, "quarantine_out_of_range", str(value), "",
                        "impossible coordinate quarantined")
                cleaned.at[index, column] = ""

    # Deduplicate exact rows.
    before = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    if len(cleaned) < before:
        _record("_rows", "deduplicate", str(before), str(len(cleaned)),
                "exact duplicate rows removed")
    return cleaned, ledger


def _to_jsonld(df: pd.DataFrame) -> list[dict]:
    """Emit Schema.org-aligned JSON-LD for organizations."""
    records = []
    for _, row in df.iterrows():
        organization = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": row.get("Company Name", ""),
            "alternateName": row.get("Alternate Name", ""),
            "address": {
                "@type": "PostalAddress",
                "streetAddress": row.get("Street", ""),
                "addressLocality": row.get("City", ""),
                "addressRegion": row.get("State", ""),
                "postalCode": row.get("Postal", ""),
                "addressCountry": row.get("Country", ""),
            },
            "telephone": row.get("Phone", ""),
            "url": row.get("Website", ""),
        }
        if row.get("Parent Company"):
            organization["parentOrganization"] = {
                "@type": "Organization",
                "name": row["Parent Company"],
            }
        records.append(organization)
    return records


def _shacl_shapes() -> str:
    """Emit SHACL shapes for the standardized dataset."""
    return """@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

schema:OrganizationShape
    a sh:NodeShape ;
    sh:targetClass schema:Organization ;
    sh:property [
        sh:path schema:name ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path schema:address ;
        sh:minCount 1 ;
        sh:node schema:PostalAddressShape ;
    ] .

schema:PostalAddressShape
    a sh:NodeShape ;
    sh:property [
        sh:path schema:addressCountry ;
        sh:minCount 1 ;
        sh:maxLength 2 ;
    ] .
"""


def _validate_shacl(records: list[dict]) -> dict:
    """Deterministic SHACL-style validation of the JSON-LD records."""
    violations = []
    for index, record in enumerate(records):
        if not record.get("name"):
            violations.append(f"record {index}: missing name")
        address = record.get("address", {})
        if not address:
            violations.append(f"record {index}: missing address")
        country = address.get("addressCountry", "")
        if not country:
            violations.append(f"record {index}: missing country")
        elif len(str(country)) > 2:
            violations.append(
                f"record {index}: country {country!r} exceeds 2 chars")
    return {"record_type": "shacl_validation/v1",
            "records_checked": len(records),
            "violations": violations,
            "passed": not violations}


def _quality(before: pd.DataFrame, after: pd.DataFrame) -> DataQualityReport:
    def _null_cells(df: pd.DataFrame) -> int:
        return int(df.isna().sum().sum()) + int(
            df.astype(str).isin(_NULL_SENTINELS).sum().sum())

    def _invalid_coordinates(df: pd.DataFrame) -> int:
        lat = pd.to_numeric(df["Latitude"], errors="coerce")
        lon = pd.to_numeric(df["Longitude"], errors="coerce")
        return int(((lat.abs() > 90) | (lon.abs() > 180)).sum())

    return DataQualityReport(
        before_rows=len(before), after_rows=len(after),
        before_duplicates=int(before.duplicated().sum()),
        after_duplicates=int(after.duplicated().sum()),
        before_null_cells=_null_cells(before),
        after_null_cells=_null_cells(after),
        before_invalid_coordinates=_invalid_coordinates(before),
        after_invalid_coordinates=_invalid_coordinates(after),
        fixed_issues=("duplicates", "country codes", "phone extensions",
                      "date formats", "impossible coordinates"),
        unresolved_issues=(),
        review_required=("entity resolution across alternate names",))


def run_standardization() -> dict:
    """Run the full standardization through the canonical Loop runtime."""
    ledger = LoopLedger()

    def _run(_inputs=None) -> dict:
        before = _load()
        profiles = _profile(before)
        proposals = _propose_cleaning(profiles)
        cleaned, transformations = _clean(before)
        jsonld = _to_jsonld(cleaned)
        validation = _validate_shacl(jsonld)
        quality = _quality(before, cleaned)
        return {
            "profiles": [p.to_dict() for p in profiles],
            "proposals": [p.to_dict() for p in proposals],
            "transformations": [t.to_dict() for t in transformations],
            "jsonld_records": len(jsonld),
            "shacl": validation,
            "quality": quality.to_dict(),
        }

    result = as_practitioner_loop(
        "standardize messy organizations to Schema.org", _run,
        ledger=ledger)
    return {"loop_id": result["loop_id"],
            "ledger_events": len(ledger.events),
            **result["value"]}


def main() -> None:
    result = run_standardization()
    print("SCHEMA.ORG DATA STANDARDIZATION")
    print(f"loop: {result['loop_id']}  ledger events: "
          f"{result['ledger_events']}")
    print()
    print("COLUMN PROFILES")
    for profile in result["profiles"]:
        issues = "; ".join(profile["issues"]) or "clean"
        print(f"  {profile['column']:<16} nulls={profile['null_count']:>2} "
              f"distinct={profile['distinct']:>2}  {issues}")
    print()
    print("CLEANING PROPOSALS")
    for proposal in result["proposals"]:
        print(f"  {proposal['proposal_id']:<28} "
              f"confidence={proposal['confidence']:.2f} "
              f"risk={proposal['risk']}")
    print()
    print("TRANSFORMATIONS APPLIED")
    for txn in result["transformations"]:
        print(f"  {txn['record_id']}: {txn['column']} "
              f"{txn['operation']} ({txn['reason']})")
    print()
    print("SHACL VALIDATION")
    print(f"  records: {result['shacl']['records_checked']}  "
          f"violations: {len(result['shacl']['violations'])}  "
          f"passed: {result['shacl']['passed']}")
    print()
    print("DATA QUALITY")
    quality = result["quality"]
    print(f"  rows: {quality['before_rows']} -> {quality['after_rows']}")
    print(f"  duplicates: {quality['before_duplicates']} -> "
          f"{quality['after_duplicates']}")
    print(f"  null cells: {quality['before_null_cells']} -> "
          f"{quality['after_null_cells']}")
    print(f"  invalid coordinates: "
          f"{quality['before_invalid_coordinates']} -> "
          f"{quality['after_invalid_coordinates']}")
    print(f"  review required: {', '.join(quality['review_required'])}")


if __name__ == "__main__":
    main()
