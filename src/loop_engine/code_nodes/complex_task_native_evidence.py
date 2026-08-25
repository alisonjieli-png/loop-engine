"""Typed Loop Engine benchmark evidence and strict published-result matching.

This module does not run a benchmark. It joins verified Loop Engine results to
the reviewed published-harness catalog only when the benchmark, population,
model, effort, metric, evaluator, and external environment match exactly.
"""
from __future__ import annotations

import datetime as _datetime
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from .complex_task_published_evidence import (
    METRIC_DIRECTIONS,
    PublishedEvidenceCatalog,
    PublishedEvidenceError,
)


NATIVE_EVIDENCE_STATES = (
    "full_system_verified",
    "component_only",
    "invalidated",
)


def _date(value: str, name: str) -> None:
    try:
        _datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise PublishedEvidenceError(f"{name} must use YYYY-MM-DD") from exc


@dataclass(frozen=True)
class LoopEngineBenchmarkEvidence:
    """One exact result produced by a saved Loop Engine run."""

    record_id: str
    evidence_state: str
    benchmark_name: str
    benchmark_version: str
    population_name: str
    population_count: int
    population_selection: str
    model_name: str
    model_version: str
    model_effort: str
    score_value: float
    score_metric: str
    score_unit: str
    metric_direction: str
    evaluation_protocol: str
    external_environment: str
    evaluation_date: str
    provider_id: str
    selected_mode: str
    selected_model_calls: int
    packet_model_calls: int
    excluded_model_calls: int
    known_input_tokens_subtotal: "int | None"
    known_output_tokens_subtotal: "int | None"
    token_accounting_complete: bool
    cost_usd: "float | None"
    cost_state: str
    artifact_refs: tuple[str, ...]
    verification_ref: str
    limitations: tuple[str, ...]
    score_is_approximate: bool = False

    def __post_init__(self) -> None:
        required = (
            self.record_id, self.benchmark_name, self.benchmark_version,
            self.population_name, self.population_selection,
            self.model_name, self.model_version, self.model_effort,
            self.score_metric, self.score_unit, self.evaluation_protocol,
            self.external_environment, self.evaluation_date,
            self.provider_id, self.selected_mode, self.verification_ref,
        )
        if any(not str(value).strip() for value in required):
            raise PublishedEvidenceError(
                "Loop Engine evidence is missing a required named fact")
        if self.evidence_state not in NATIVE_EVIDENCE_STATES:
            raise PublishedEvidenceError("unknown Loop Engine evidence state")
        if self.population_count < 1:
            raise PublishedEvidenceError("population_count must be positive")
        if self.metric_direction not in METRIC_DIRECTIONS:
            raise PublishedEvidenceError("unknown metric direction")
        counts = (self.selected_model_calls, self.packet_model_calls,
                  self.excluded_model_calls)
        if any(value < 0 for value in counts):
            raise PublishedEvidenceError("model-call counts cannot be negative")
        if (self.packet_model_calls
                != self.selected_model_calls + self.excluded_model_calls):
            raise PublishedEvidenceError(
                "packet model calls must include selected and excluded calls")
        for name in ("known_input_tokens_subtotal",
                     "known_output_tokens_subtotal"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise PublishedEvidenceError(f"{name} cannot be negative")
        if not isinstance(self.token_accounting_complete, bool):
            raise PublishedEvidenceError(
                "token_accounting_complete must be a boolean")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise PublishedEvidenceError("cost_usd cannot be negative")
        if self.cost_state not in ("known", "unknown"):
            raise PublishedEvidenceError("cost_state must be known or unknown")
        if ((self.cost_usd is None) != (self.cost_state == "unknown")):
            raise PublishedEvidenceError(
                "cost value and cost_state contradict each other")
        if not self.artifact_refs or not self.limitations:
            raise PublishedEvidenceError(
                "Loop Engine evidence needs artifacts and limitations")
        if len(self.artifact_refs) != len(set(self.artifact_refs)):
            raise PublishedEvidenceError("artifact_refs cannot repeat")
        _date(self.evaluation_date, "evaluation_date")

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
    def eligible_for_published_match(self) -> bool:
        return (
            self.evidence_state == "full_system_verified"
            and not self.score_is_approximate
        )

    def to_dict(self) -> dict:
        value = asdict(self)
        value["artifact_refs"] = list(self.artifact_refs)
        value["limitations"] = list(self.limitations)
        value["eligible_for_published_match"] = (
            self.eligible_for_published_match)
        return value


@dataclass(frozen=True)
class LoopEngineEvidenceCatalog:
    schema_version: str
    as_of: str
    records: tuple[LoopEngineBenchmarkEvidence, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "loop_engine_benchmark_evidence/v1":
            raise PublishedEvidenceError(
                "unsupported Loop Engine evidence schema")
        _date(self.as_of, "catalog as_of")
        ids = [record.record_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise PublishedEvidenceError(
                "Loop Engine evidence record IDs must be unique")


@dataclass(frozen=True)
class PublishedHarnessMatch:
    """Exact published-harness matches for one Loop Engine result."""

    loop_engine_record_id: str
    comparison_key: tuple
    published_record_ids: tuple[str, ...]
    harness_names: tuple[str, ...]
    comparison_ready: bool
    exclusion_reason: str

    def to_dict(self) -> dict:
        return {
            "loop_engine_record_id": self.loop_engine_record_id,
            "comparison_key": list(self.comparison_key),
            "published_record_ids": list(self.published_record_ids),
            "harness_names": list(self.harness_names),
            "comparison_ready": self.comparison_ready,
            "exclusion_reason": self.exclusion_reason,
        }


@dataclass(frozen=True)
class PublishedHarnessMatchReport:
    matches: tuple[PublishedHarnessMatch, ...]

    @property
    def comparison_ready(self) -> int:
        return sum(item.comparison_ready for item in self.matches)

    def to_dict(self) -> dict:
        return {
            "record_type": "loop_engine_published_harness_match_report/v1",
            "loop_engine_records": len(self.matches),
            "comparison_ready": self.comparison_ready,
            "matches": [item.to_dict() for item in self.matches],
        }


def match_loop_engine_to_published(
        native: LoopEngineEvidenceCatalog,
        published: PublishedEvidenceCatalog) -> PublishedHarnessMatchReport:
    """Match exact comparison keys without running any competitor harness."""
    eligible_published = tuple(
        record for record in published.records
        if record.eligible_for_harness_comparison)
    matches = []
    for record in native.records:
        exact = tuple(
            item for item in eligible_published
            if item.comparison_key == record.comparison_key)
        ready = record.eligible_for_published_match and bool(exact)
        if ready:
            reason = ""
        elif not record.eligible_for_published_match:
            reason = (
                "the Loop Engine record is not an exact verified full-system result")
        else:
            reason = (
                "no reviewed published harness result uses the same benchmark, "
                "population, model, effort, metric, evaluator, and environment")
        matches.append(PublishedHarnessMatch(
            record.record_id,
            record.comparison_key,
            tuple(item.record_id for item in exact),
            tuple(sorted({item.harness_name for item in exact})),
            ready,
            reason,
        ))
    return PublishedHarnessMatchReport(tuple(matches))


def native_catalog_from_mapping(
        value: Mapping[str, object]) -> LoopEngineEvidenceCatalog:
    allowed = {"schema_version", "as_of", "records"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise PublishedEvidenceError(
            f"unknown Loop Engine catalog fields: {unknown}")
    raw_records = value.get("records", [])
    if not isinstance(raw_records, list):
        raise PublishedEvidenceError("Loop Engine records must be a list")
    fields = set(LoopEngineBenchmarkEvidence.__dataclass_fields__)
    records = []
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, Mapping):
            raise PublishedEvidenceError(
                f"Loop Engine record {index} must be an object")
        unexpected = sorted(set(raw) - fields)
        if unexpected:
            raise PublishedEvidenceError(
                f"Loop Engine record {index} has unknown fields: {unexpected}")
        body = dict(raw)
        for name in ("artifact_refs", "limitations"):
            body[name] = tuple(body.get(name, ()))
        try:
            records.append(LoopEngineBenchmarkEvidence(**body))
        except TypeError as exc:
            raise PublishedEvidenceError(
                f"Loop Engine record {index} is missing required fields") from exc
    return LoopEngineEvidenceCatalog(
        str(value.get("schema_version", "")),
        str(value.get("as_of", "")),
        tuple(records),
    )


def load_native_evidence(path: str | Path) -> LoopEngineEvidenceCatalog:
    with Path(path).open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, Mapping):
        raise PublishedEvidenceError(
            "Loop Engine evidence catalog must contain one object")
    return native_catalog_from_mapping(value)


def self_test() -> dict:
    from .complex_task_benchmark import (
        default_loop_engine_catalog_path,
        default_published_catalog_path,
        load_published_evidence,
    )
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    native = load_native_evidence(default_loop_engine_catalog_path())
    published = load_published_evidence(default_published_catalog_path())
    report = match_loop_engine_to_published(native, published)
    check("saved_native_catalog_has_two_verified_full_system_smoke_results",
          len(native.records) == 2
          and all(item.eligible_for_published_match for item in native.records))
    check("no_unmatched_population_is_reported_as_a_fair_comparison",
          report.comparison_ready == 0
          and all(not item.comparison_ready for item in report.matches))
    check("matching_requires_the_full_exact_comparison_key",
          all(len(item.comparison_key) == 13 for item in report.matches))
    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
