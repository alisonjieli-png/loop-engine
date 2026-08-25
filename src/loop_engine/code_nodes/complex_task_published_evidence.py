"""Typed catalog for already-published harness benchmark evidence.

This module does not run a harness or model. It stores numeric published
results separately from graphical findings and searches that found no score.
"""
from __future__ import annotations

import datetime as _datetime
import os
from dataclasses import asdict, dataclass
from typing import Mapping

import yaml


EVIDENCE_QUALIFIERS = (
    "harness_measured", "model_only",
    "framework_measured_not_harness_bundle", "unclear")
EVIDENCE_STRENGTHS = (
    "primary_numeric",
    "primary_graphical",
    "official_search_no_score",
    "project_local_no_independent_score",
    "cross_source_gap",
)
FINDING_STATUSES = (
    "graphical_ranking_only",
    "no_qualifying_result_found",
    "dimension_not_measured",
)
SOURCE_STATES = ("source_reviewed", "source_unverified")
METRIC_DIRECTIONS = ("maximize", "minimize")


class PublishedEvidenceError(ValueError):
    """A published-evidence record is incomplete or contradictory."""


def _date(value: str, field_name: str) -> None:
    try:
        _datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise PublishedEvidenceError(
            f"{field_name} must use YYYY-MM-DD") from exc


def _source(url: str) -> None:
    if not url.startswith("https://"):
        raise PublishedEvidenceError("source_url must use HTTPS")


@dataclass(frozen=True)
class PublishedBenchmarkEvidence:
    """One numeric result stated by a named primary or official source."""

    record_id: str
    comparison_id: str
    configuration_label: str
    harness_name: str
    harness_version: str
    benchmark_name: str
    benchmark_version: str
    model_name: str
    model_version: str
    model_effort: str
    population_name: str
    population_count: "int | None"
    population_selection: str
    tools: tuple[str, ...]
    evaluation_protocol: str
    external_environment: str
    score_value: float
    score_metric: str
    score_unit: str
    metric_direction: str
    score_is_approximate: bool
    evaluation_date: str
    source_url: str
    source_title: str
    source_date: str
    source_state: str
    evidence_qualifier: str
    evidence_strength: str
    limitations: tuple[str, ...]
    model_calls: "int | None" = None
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    cost_usd: "float | None" = None
    component_scores: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        required = (
            self.record_id, self.comparison_id, self.configuration_label,
            self.harness_name, self.harness_version, self.benchmark_name,
            self.benchmark_version, self.model_name, self.model_version,
            self.model_effort,
            self.population_name, self.population_selection,
            self.evaluation_protocol, self.external_environment,
            self.score_metric, self.score_unit, self.evaluation_date,
            self.source_url, self.source_title, self.source_date)
        if any(not str(value).strip() for value in required):
            raise PublishedEvidenceError(
                "published evidence is missing a required named fact")
        if self.population_count is not None and self.population_count < 1:
            raise PublishedEvidenceError(
                "population_count must be positive or unknown")
        if self.metric_direction not in METRIC_DIRECTIONS:
            raise PublishedEvidenceError("unknown metric direction")
        if self.evidence_qualifier not in EVIDENCE_QUALIFIERS:
            raise PublishedEvidenceError("unknown evidence qualifier")
        if self.evidence_strength not in EVIDENCE_STRENGTHS:
            raise PublishedEvidenceError("unknown evidence strength")
        if self.source_state not in SOURCE_STATES:
            raise PublishedEvidenceError("unknown source state")
        _date(self.evaluation_date, "evaluation_date")
        _date(self.source_date, "source_date")
        _source(self.source_url)
        if len(self.tools) != len(set(self.tools)):
            raise PublishedEvidenceError("tools cannot contain duplicates")
        if not self.limitations:
            raise PublishedEvidenceError("limitations cannot be empty")
        for name in ("model_calls", "input_tokens", "output_tokens"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise PublishedEvidenceError(f"{name} cannot be negative")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise PublishedEvidenceError("cost_usd cannot be negative")
        component_names = [name for name, _score in self.component_scores]
        if len(component_names) != len(set(component_names)):
            raise PublishedEvidenceError(
                "component score names cannot contain duplicates")
        if self.evidence_qualifier == "model_only" and self.harness_name != "none":
            raise PublishedEvidenceError(
                "model-only evidence must use harness_name='none'")
        if self.evidence_strength != "primary_numeric":
            raise PublishedEvidenceError(
                "numeric records require primary_numeric strength")

    @property
    def comparison_key(self) -> tuple:
        return (
            self.benchmark_name,
            self.benchmark_version,
            self.population_name,
            self.population_count,
            self.population_selection,
            self.model_name,
            self.model_version,
            self.model_effort,
            self.score_metric,
            self.score_unit,
            self.metric_direction,
            self.evaluation_protocol,
            self.external_environment,
        )

    @property
    def eligible_for_harness_comparison(self) -> bool:
        return (self.source_state == "source_reviewed"
                and self.evidence_qualifier == "harness_measured"
                and not self.score_is_approximate)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["tools"] = list(self.tools)
        value["limitations"] = list(self.limitations)
        value["component_scores"] = dict(self.component_scores)
        value["eligible_for_harness_comparison"] = (
            self.eligible_for_harness_comparison)
        return value


@dataclass(frozen=True)
class PublishedEvidenceFinding:
    """A qualitative graph result or a documented search with no score."""

    finding_id: str
    subject: str
    status: str
    statement: str
    benchmark_name: str
    benchmark_version: str
    population_name: str
    population_count: "int | None"
    compared_systems: tuple[str, ...]
    qualitative_ranking: tuple[str, ...]
    exact_values_available: bool
    source_url: str
    reviewed_sources: tuple[str, ...]
    source_title: str
    source_date: str
    source_state: str
    evidence_strength: str
    search_scope: str
    search_date: str
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        required = (
            self.finding_id, self.subject, self.status, self.statement,
            self.source_url, self.source_title, self.source_state,
            self.evidence_strength, self.search_scope, self.search_date)
        if any(not str(value).strip() for value in required):
            raise PublishedEvidenceError(
                "published finding is missing a required named fact")
        if self.status not in FINDING_STATUSES:
            raise PublishedEvidenceError("unknown finding status")
        if self.source_state not in SOURCE_STATES:
            raise PublishedEvidenceError("unknown source state")
        if self.evidence_strength not in EVIDENCE_STRENGTHS:
            raise PublishedEvidenceError("unknown evidence strength")
        if self.population_count is not None and self.population_count < 1:
            raise PublishedEvidenceError(
                "population_count must be positive or unknown")
        _date(self.search_date, "search_date")
        if self.source_date:
            _date(self.source_date, "source_date")
        _source(self.source_url)
        if not self.reviewed_sources:
            raise PublishedEvidenceError("reviewed_sources cannot be empty")
        for url in self.reviewed_sources:
            _source(url)
        if len(self.reviewed_sources) != len(set(self.reviewed_sources)):
            raise PublishedEvidenceError(
                "reviewed_sources cannot contain duplicates")
        if not self.limitations:
            raise PublishedEvidenceError("limitations cannot be empty")
        if (self.status == "graphical_ranking_only"
                and self.exact_values_available):
            raise PublishedEvidenceError(
                "graphical-only finding cannot claim exact values")
        if (self.status == "no_qualifying_result_found"
                and (self.qualitative_ranking or self.exact_values_available)):
            raise PublishedEvidenceError(
                "no-result finding cannot carry a ranking or score")
        if (self.status == "dimension_not_measured"
                and (self.qualitative_ranking or self.exact_values_available)):
            raise PublishedEvidenceError(
                "evidence-gap finding cannot carry a ranking or score")

    def to_dict(self) -> dict:
        value = asdict(self)
        value["compared_systems"] = list(self.compared_systems)
        value["qualitative_ranking"] = list(self.qualitative_ranking)
        value["reviewed_sources"] = list(self.reviewed_sources)
        value["limitations"] = list(self.limitations)
        return value


@dataclass(frozen=True)
class PublishedComparisonGroup:
    comparison_key: tuple
    record_ids: tuple[str, ...]
    harness_names: tuple[str, ...]
    comparable: bool
    exclusion_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "comparison_key": list(self.comparison_key),
            "record_ids": list(self.record_ids),
            "harness_names": list(self.harness_names),
            "comparable": self.comparable,
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass(frozen=True)
class PublishedEvidenceCatalog:
    schema_version: str
    as_of: str
    records: tuple[PublishedBenchmarkEvidence, ...]
    findings: tuple[PublishedEvidenceFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != "published_harness_evidence/v1":
            raise PublishedEvidenceError("unsupported published catalog schema")
        _date(self.as_of, "catalog as_of")
        ids = ([record.record_id for record in self.records]
               + [finding.finding_id for finding in self.findings])
        if len(ids) != len(set(ids)):
            raise PublishedEvidenceError("catalog ids must be unique")

    def comparison_groups(self) -> tuple[PublishedComparisonGroup, ...]:
        grouped: dict[tuple, list[PublishedBenchmarkEvidence]] = {}
        for record in self.records:
            grouped.setdefault(record.comparison_key, []).append(record)
        groups = []
        for key, records in sorted(grouped.items(), key=lambda item: str(item[0])):
            eligible = [record for record in records
                        if record.eligible_for_harness_comparison]
            harnesses = {record.harness_name for record in eligible}
            comparable = len(eligible) >= 2 and len(harnesses) >= 2
            reason = "" if comparable else (
                "needs two reviewed exact scores from different harnesses on "
                "the same benchmark, population, model, effort, evaluator, "
                "external environment, and metric")
            groups.append(PublishedComparisonGroup(
                key, tuple(record.record_id for record in records),
                tuple(sorted({record.harness_name for record in records})),
                comparable, reason))
        return tuple(groups)

    def accounting(self) -> dict:
        groups = self.comparison_groups()
        return {
            "record_type": "published_harness_evidence_accounting/v1",
            "schema_version": self.schema_version,
            "as_of": self.as_of,
            "numeric_records": len(self.records),
            "findings": len(self.findings),
            "harness_measured": sum(
                record.evidence_qualifier == "harness_measured"
                for record in self.records),
            "model_only": sum(
                record.evidence_qualifier == "model_only"
                for record in self.records),
            "framework_not_harness_bundle": sum(
                record.evidence_qualifier
                == "framework_measured_not_harness_bundle"
                for record in self.records),
            "graphical_only": sum(
                finding.status == "graphical_ranking_only"
                for finding in self.findings),
            "no_qualifying_result_found": sum(
                finding.status == "no_qualifying_result_found"
                for finding in self.findings),
            "dimension_not_measured": sum(
                finding.status == "dimension_not_measured"
                for finding in self.findings),
            "comparison_groups": len(groups),
            "comparable_groups": sum(group.comparable for group in groups),
            "groups": [group.to_dict() for group in groups],
            "configuration_comparisons": self.configuration_comparisons(),
        }

    def configuration_comparisons(self) -> list[dict]:
        """Summarize source-linked before and after configuration studies."""
        grouped: dict[str, list[PublishedBenchmarkEvidence]] = {}
        for record in self.records:
            grouped.setdefault(record.comparison_id, []).append(record)
        out = []
        for comparison_id, records in grouped.items():
            if len(records) < 2:
                continue
            first = records[0]
            same_basis = all(
                record.harness_name == first.harness_name
                and record.model_name == first.model_name
                and record.model_version == first.model_version
                and record.model_effort == first.model_effort
                and record.benchmark_name == first.benchmark_name
                and record.benchmark_version == first.benchmark_version
                and record.population_name == first.population_name
                and record.population_count == first.population_count
                and record.population_selection == first.population_selection
                and record.score_metric == first.score_metric
                and record.score_unit == first.score_unit
                and record.evaluation_protocol == first.evaluation_protocol
                and record.external_environment == first.external_environment
                for record in records[1:])
            out.append({
                "comparison_id": comparison_id,
                "record_ids": [record.record_id for record in records],
                "same_harness_model_population_metric": same_basis,
                "configuration_labels": [
                    record.configuration_label for record in records],
                "score_values": [record.score_value for record in records],
                "score_change_first_to_last": (
                    round(records[-1].score_value - first.score_value, 10)),
                "tools_held_fixed": all(
                    record.tools == first.tools for record in records[1:]),
            })
        return out


def _rows(value, name: str) -> list:
    rows = value.get(name, [])
    if not isinstance(rows, list):
        raise PublishedEvidenceError(f"catalog {name} must be a list")
    return rows


def _typed_rows(rows: list, cls, tuple_fields: tuple[str, ...], name: str):
    fields = set(cls.__dataclass_fields__)
    out = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise PublishedEvidenceError(f"{name} {index} must be an object")
        unexpected = sorted(set(raw) - fields)
        if unexpected:
            raise PublishedEvidenceError(
                f"{name} {index} has unknown fields: {unexpected}")
        body = dict(raw)
        for field_name in tuple_fields:
            body[field_name] = tuple(body.get(field_name, ()))
        if cls is PublishedBenchmarkEvidence:
            components = body.get("component_scores", {})
            if not isinstance(components, Mapping):
                raise PublishedEvidenceError(
                    f"{name} {index} component_scores must be an object")
            body["component_scores"] = tuple(
                (str(key), float(score))
                for key, score in sorted(components.items()))
        try:
            out.append(cls(**body))
        except TypeError as exc:
            raise PublishedEvidenceError(
                f"{name} {index} is missing required fields") from exc
    return tuple(out)


def published_catalog_from_mapping(
        value: Mapping[str, object]) -> PublishedEvidenceCatalog:
    allowed = {"schema_version", "as_of", "records", "findings"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise PublishedEvidenceError(f"unknown catalog fields: {unknown}")
    records = _typed_rows(
        _rows(value, "records"), PublishedBenchmarkEvidence,
        ("tools", "limitations"), "record")
    findings = _typed_rows(
        _rows(value, "findings"), PublishedEvidenceFinding,
        ("compared_systems", "qualitative_ranking", "reviewed_sources",
         "limitations"),
        "finding")
    return PublishedEvidenceCatalog(
        str(value.get("schema_version", "")),
        str(value.get("as_of", "")), records, findings)


def load_published_evidence(path: os.PathLike | str
                            ) -> PublishedEvidenceCatalog:
    with open(path, encoding="utf-8") as stream:
        value = yaml.safe_load(stream) or {}
    if not isinstance(value, Mapping):
        raise PublishedEvidenceError("published catalog must be an object")
    return published_catalog_from_mapping(value)


def self_test() -> dict:
    """Pure schema checks. No harness, model, or benchmark is executed."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": f"contract_only_{name}",
                      "passed": bool(passed), "detail": detail})

    empty = published_catalog_from_mapping({
        "schema_version": "published_harness_evidence/v1",
        "as_of": "2026-08-25", "records": [], "findings": []})
    check("empty_catalog_makes_no_comparison_claim",
          empty.accounting()["comparable_groups"] == 0)

    missing_source_refused = False
    try:
        published_catalog_from_mapping({
            "schema_version": "published_harness_evidence/v1",
            "as_of": "2026-08-25",
            "records": [{"record_id": "incomplete"}]})
    except PublishedEvidenceError:
        missing_source_refused = True
    check("record_without_named_source_is_refused", missing_source_refused)

    graphical_exact_refused = False
    try:
        PublishedEvidenceFinding(
            "contract", "subject", "graphical_ranking_only", "statement",
            "benchmark", "version", "subset", 5, ("a", "b"), ("a>b",),
            True, "https://example.invalid/source",
            ("https://example.invalid/source",), "contract source",
            "2026-08-25", "source_unverified", "primary_graphical",
            "contract-only search", "2026-08-25", ("contract only",))
    except PublishedEvidenceError:
        graphical_exact_refused = True
    check("graphical_finding_cannot_invent_exact_values",
          graphical_exact_refused)

    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
