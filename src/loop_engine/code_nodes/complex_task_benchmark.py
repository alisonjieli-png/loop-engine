"""Public facade for source-backed published harness benchmark evidence.

Loop Engine does not rerun external harnesses through this module. It records
published results and compares only records with the same benchmark facts.
"""
from __future__ import annotations

from pathlib import Path

from .complex_task_published_evidence import (
    EVIDENCE_QUALIFIERS,
    EVIDENCE_STRENGTHS,
    FINDING_STATUSES,
    METRIC_DIRECTIONS,
    SOURCE_STATES,
    PublishedBenchmarkEvidence,
    PublishedComparisonGroup,
    PublishedEvidenceFinding,
    PublishedEvidenceCatalog,
    PublishedEvidenceError,
    load_published_evidence,
    published_catalog_from_mapping,
    self_test as _published_evidence_self_test,
)
from .complex_task_native_evidence import (
    NATIVE_EVIDENCE_STATES,
    LoopEngineBenchmarkEvidence,
    LoopEngineEvidenceCatalog,
    PublishedHarnessMatch,
    PublishedHarnessMatchReport,
    load_native_evidence,
    match_loop_engine_to_published,
    native_catalog_from_mapping,
    self_test as _native_evidence_self_test,
)

__all__ = (
    "EVIDENCE_QUALIFIERS", "EVIDENCE_STRENGTHS", "FINDING_STATUSES",
    "METRIC_DIRECTIONS", "SOURCE_STATES",
    "PublishedBenchmarkEvidence", "PublishedComparisonGroup",
    "PublishedEvidenceCatalog", "PublishedEvidenceError",
    "PublishedEvidenceFinding", "NATIVE_EVIDENCE_STATES",
    "LoopEngineBenchmarkEvidence", "LoopEngineEvidenceCatalog",
    "PublishedHarnessMatch", "PublishedHarnessMatchReport",
    "default_loop_engine_catalog_path", "default_published_catalog_path",
    "load_native_evidence", "load_published_evidence",
    "match_loop_engine_to_published", "native_catalog_from_mapping",
    "published_catalog_from_mapping", "self_test",
)


def default_published_catalog_path() -> Path:
    """Return the installed package's reviewed published-evidence catalog."""
    return (Path(__file__).resolve().parents[1] / "data"
            / "published-harness-evidence.json")


def default_loop_engine_catalog_path() -> Path:
    """Return the installed package's verified Loop Engine evidence catalog."""
    return (Path(__file__).resolve().parents[1] / "data"
            / "loop-engine-benchmark-evidence.json")


def self_test() -> dict:
    """Validate schema behavior and the current catalog without running arms."""
    result = _published_evidence_self_test()
    tests = list(result["tests"])
    native_result = _native_evidence_self_test()
    tests.extend(native_result["tests"])
    catalog = load_published_evidence(default_published_catalog_path())
    accounting = catalog.accounting()
    repository_copy = (Path(__file__).resolve().parents[3] / "docs"
                       / "benchmarks" / "published-harness-evidence.json")
    native_repository_copy = (Path(__file__).resolve().parents[3] / "docs"
                              / "benchmarks"
                              / "loop-engine-benchmark-evidence.json")
    tests.append({
        "test": "installed_catalog_matches_the_repository_document_copy",
        "passed": (not repository_copy.exists()
                   or repository_copy.read_bytes()
                   == default_published_catalog_path().read_bytes()),
        "detail": str(default_published_catalog_path()),
    })
    tests.append({
        "test": "installed_native_catalog_matches_the_repository_document_copy",
        "passed": (not native_repository_copy.exists()
                   or native_repository_copy.read_bytes()
                   == default_loop_engine_catalog_path().read_bytes()),
        "detail": str(default_loop_engine_catalog_path()),
    })
    tests.append({
        "test": "current_published_catalog_is_valid_and_claims_only_eligible_groups",
        "passed": (
            accounting["numeric_records"] == len(catalog.records)
            and accounting["comparable_groups"]
            == sum(group.comparable for group in catalog.comparison_groups())),
        "detail": str(accounting),
    })
    comparable = [group for group in catalog.comparison_groups()
                  if group.comparable]
    tests.append({
        "test": "artificial_analysis_is_the_only_exact_cross_harness_group",
        "passed": (
            len(comparable) == 1
            and comparable[0].harness_names
            == ("Claude Code", "Cursor CLI", "Opencode")),
        "detail": str([group.to_dict() for group in comparable]),
    })
    tests.append({
        "test": "reviewed_intelligence_reuse_gap_is_not_a_superiority_claim",
        "passed": any(
            finding.status == "dimension_not_measured"
            and "not evidence that Loop Engine is better"
            in " ".join(finding.limitations)
            for finding in catalog.findings),
        "detail": str(accounting),
    })
    deep_agents = next(
        row for row in accounting["configuration_comparisons"]
        if row["comparison_id"]
        == "deep-agents-terminal-bench-harness-engineering")
    tests.append({
        "test": "deep_agents_terminal_bench_records_tool_changes",
        "passed": deep_agents["tools_held_fixed"] is False,
        "detail": str(deep_agents),
    })
    passed = sum(item["passed"] for item in tests)
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
