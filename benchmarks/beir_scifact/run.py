#!/usr/bin/env python3
"""Run a deterministic BEIR SciFact engineering diagnostic.

The diagnostic exercises a complete Practitioner and Solution Canvas path. It
is excluded from the selected benchmark evidence because selected benchmarks
require non-deterministic runs.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Callable, Mapping, Sequence

from download import EXPECTED_MD5, EXPECTED_SHA256, SOURCE_URL, verify_existing_source
from reference_metrics import ReferenceMetrics, calculate_reference_metrics

from loop_engine.code_nodes.loop_report import report_from_ledger
from loop_engine.code_nodes.run_playback import playback, render_run_report
from loop_engine.code_nodes.solution_canvas import (
    SolutionLoopSpec,
    SolutionSpec,
    run_solution,
)
from loop_engine.code_nodes.solution_compiler import compile_solution, render_canvas
from loop_engine.loop.intelligence_loops import search_as_loop
from loop_engine.loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
from loop_engine.loop.recursive_loop import (
    Loop,
    LoopConfig,
    LoopLedger,
    StepOutcome,
)
from loop_engine.core.run_history import RunHistory
from loop_engine.core.retrieval import Retriever
from loop_engine.core.store_serve import (
    SolverStore,
    StoreRecord,
    core_seed,
)


EXPECTED_CORPUS_DOCUMENTS = 5_183
EXPECTED_QUERY_FILE_ROWS = 1_109
EXPECTED_TEST_QUERIES = 300
EXPECTED_QREL_ROWS = 339
RANK_CUTOFF = 10
OBSERVED_BASELINE = {
    "ndcg_at_10": 0.6384475973112258,
    "recall_at_10": 0.7469444444444445,
    "mrr_at_10": 0.6114695767195767,
}


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    text: str


@dataclass(frozen=True)
class BenchmarkTask:
    dataset: str = "BEIR SciFact"
    split: str = "test"
    objective: str = "Retrieve scientific evidence for each test claim"
    metrics: tuple[str, ...] = ("nDCG@10", "Recall@10", "MRR@10")
    population_rule: str = "all queries with an official test qrel"
    model_policy: str = "deterministic, zero model calls"


@dataclass(frozen=True)
class DatasetBundle:
    documents: tuple[Document, ...]
    queries: Mapping[str, str]
    qrels: Mapping[str, Mapping[str, int]]
    query_file_rows: int
    qrel_rows: int
    population_sha256: str


@dataclass(frozen=True)
class CandidateMethod:
    candidate_id: str
    title_field: bool
    abstract_field: bool
    description: str


@dataclass(frozen=True)
class MetricValues:
    ndcg_at_10: float
    recall_at_10: float
    mrr_at_10: float


@dataclass(frozen=True)
class MethodEvaluation:
    candidate: CandidateMethod
    metrics: MetricValues
    rankings: Mapping[str, tuple[str, ...]]
    query_loop_ids: tuple[str, ...]
    model_calls: int


@dataclass(frozen=True)
class CandidateDiagnostic:
    candidate_id: str
    description: str
    metrics: MetricValues
    queries: int
    query_loops: int
    model_calls: int
    reference_verified: bool


@dataclass(frozen=True)
class EngineeringDiagnosticResult:
    record_type: str
    status: str
    engineering_checks_passed: bool
    selected_benchmark_evidence: bool
    exclusion_reason: str
    benchmark: str
    split: str
    scope: str
    source: dict[str, object]
    population: dict[str, object]
    root_practitioner: dict[str, object]
    solution_canvas: dict[str, object]
    diagnostic_metrics: MetricValues
    component_diagnostics: tuple[CandidateDiagnostic, ...]
    run_shape_assertions: dict[str, bool]
    run_history: dict[str, object]
    report_files: dict[str, str]
    diagnostic_baseline_match: bool
    limitations: tuple[str, ...]


class LexicalSearchSurface:
    """Expose one fixed Retriever configuration to search_as_loop."""

    def __init__(self, records: Sequence[StoreRecord]):
        self.retriever = Retriever(records, lexical_backend="fts5")

    def search(self, query: str, *, top_n: int) -> dict[str, object]:
        return self.retriever.search(query, mode="lexical", top_n=top_n)


def _sort_identifier(value: str) -> tuple[int, object]:
    return (0, int(value)) if value.isdigit() else (1, value)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON at {path}:{line_number}") from error
            if not isinstance(row, dict):
                raise ValueError(f"expected an object at {path}:{line_number}")
            rows.append(row)
    return rows


def load_dataset(data_root: Path) -> DatasetBundle:
    """Load and validate the full official test population."""
    dataset = data_root / "scifact"
    corpus_rows = _load_jsonl(dataset / "corpus.jsonl")
    query_rows = _load_jsonl(dataset / "queries.jsonl")

    documents: list[Document] = []
    document_ids: set[str] = set()
    for row in corpus_rows:
        document_id = str(row.get("_id", ""))
        if not document_id or document_id in document_ids:
            raise ValueError(f"missing or duplicate corpus id {document_id!r}")
        document_ids.add(document_id)
        documents.append(
            Document(
                document_id=document_id,
                title=str(row.get("title", "")),
                text=str(row.get("text", "")),
            )
        )

    queries: dict[str, str] = {}
    for row in query_rows:
        query_id = str(row.get("_id", ""))
        if not query_id or query_id in queries:
            raise ValueError(f"missing or duplicate query id {query_id!r}")
        queries[query_id] = str(row.get("text", ""))

    qrels: dict[str, dict[str, int]] = {}
    qrel_rows = 0
    with (dataset / "qrels" / "test.tsv").open(
        encoding="utf-8", newline=""
    ) as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["query-id", "corpus-id", "score"]:
            raise ValueError(f"unexpected qrel columns {reader.fieldnames}")
        for row in reader:
            query_id = str(row["query-id"])
            document_id = str(row["corpus-id"])
            score = int(row["score"])
            if query_id not in queries:
                raise ValueError(f"qrel query {query_id} is missing from queries")
            if document_id not in document_ids:
                raise ValueError(f"qrel document {document_id} is missing from corpus")
            if document_id in qrels.setdefault(query_id, {}):
                raise ValueError(f"duplicate qrel {query_id}/{document_id}")
            qrels[query_id][document_id] = score
            qrel_rows += 1

    observed = (
        len(documents),
        len(queries),
        len(qrels),
        qrel_rows,
    )
    expected = (
        EXPECTED_CORPUS_DOCUMENTS,
        EXPECTED_QUERY_FILE_ROWS,
        EXPECTED_TEST_QUERIES,
        EXPECTED_QREL_ROWS,
    )
    if observed != expected:
        raise ValueError(f"SciFact population mismatch: expected {expected}, got {observed}")

    population = [
        {
            "query_id": query_id,
            "query": queries[query_id],
            "qrels": sorted(qrels[query_id].items()),
        }
        for query_id in sorted(qrels, key=_sort_identifier)
    ]
    return DatasetBundle(
        documents=tuple(documents),
        queries=queries,
        qrels=qrels,
        query_file_rows=len(queries),
        qrel_rows=qrel_rows,
        population_sha256=_sha256_json(population),
    )


def _records_for_candidate(
    dataset: DatasetBundle, candidate: CandidateMethod
) -> list[StoreRecord]:
    return [
        StoreRecord(
            record_id=document.document_id,
            kind="context",
            title=document.title if candidate.title_field else "",
            body={"text": document.text if candidate.abstract_field else ""},
        )
        for document in dataset.documents
    ]


def calculate_primary_metrics(
    qrels: Mapping[str, Mapping[str, int]],
    rankings: Mapping[str, Sequence[str]],
) -> MetricValues:
    """Primary evaluator path used by the benchmark task."""
    per_query: list[tuple[float, float, float]] = []
    for query_id in sorted(qrels, key=_sort_identifier):
        relevance = qrels[query_id]
        ranked = tuple(rankings[query_id])[:RANK_CUTOFF]
        dcg = sum(
            int(relevance.get(document_id, 0)) / math.log2(rank + 2)
            for rank, document_id in enumerate(ranked)
        )
        ideal = sorted((int(value) for value in relevance.values()), reverse=True)[
            :RANK_CUTOFF
        ]
        ideal_dcg = sum(
            value / math.log2(rank + 2) for rank, value in enumerate(ideal)
        )
        relevant = {
            document_id
            for document_id, value in relevance.items()
            if int(value) > 0
        }
        recall = len(relevant.intersection(ranked)) / len(relevant)
        reciprocal_rank = next(
            (
                1.0 / rank
                for rank, document_id in enumerate(ranked, start=1)
                if document_id in relevant
            ),
            0.0,
        )
        per_query.append((dcg / ideal_dcg, recall, reciprocal_rank))
    count = len(per_query)
    return MetricValues(
        ndcg_at_10=sum(row[0] for row in per_query) / count,
        recall_at_10=sum(row[1] for row in per_query) / count,
        mrr_at_10=sum(row[2] for row in per_query) / count,
    )


def _metric_match(primary: MetricValues, reference: ReferenceMetrics) -> bool:
    return (
        abs(primary.ndcg_at_10 - reference.ndcg_at_10) < 1e-12
        and abs(primary.recall_at_10 - reference.recall_at_10) < 1e-12
        and abs(primary.mrr_at_10 - reference.mrr_at_10) < 1e-12
    )


def evaluate_candidate(
    dataset: DatasetBundle,
    candidate: CandidateMethod,
    *,
    parent: Loop,
) -> MethodEvaluation:
    """Run all 300 official queries, with every search in a spawned_loop loop."""
    surface = LexicalSearchSurface(_records_for_candidate(dataset, candidate))
    rankings: dict[str, tuple[str, ...]] = {}
    query_loop_ids: list[str] = []
    model_calls = 0
    for query_id in sorted(dataset.qrels, key=_sort_identifier):
        wrapped = search_as_loop(
            surface,
            dataset.queries[query_id],
            pillar="context_intelligence",
            top_n=RANK_CUTOFF,
            parent=parent,
        )
        if wrapped.get("error") is not None:
            raise RuntimeError(
                f"query {query_id} search failed: {wrapped.get('error')}"
            )
        hits = wrapped["value"]["hits"]
        rankings[query_id] = tuple(str(hit["record_id"]) for hit in hits)
        query_loop_ids.append(str(wrapped["loop_id"]))
        model_calls += int(wrapped.get("model_calls", 0) or 0)
    if len(query_loop_ids) != EXPECTED_TEST_QUERIES:
        raise RuntimeError(
            f"candidate {candidate.candidate_id} ran {len(query_loop_ids)} "
            f"query loops, expected {EXPECTED_TEST_QUERIES}"
        )
    return MethodEvaluation(
        candidate=candidate,
        metrics=calculate_primary_metrics(dataset.qrels, rankings),
        rankings=rankings,
        query_loop_ids=tuple(query_loop_ids),
        model_calls=model_calls,
    )


def _spawned_loop_config() -> LoopConfig:
    return LoopConfig(
        framework="five_step",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        power="deep",
        max_depth=3,
    )


def run_spawned_loop(
    parent: Loop, goal: str, work: Callable[[Loop], object]
) -> tuple[Loop, object]:
    """Run one owned spawned_loop through the standard five-step profile."""
    spawned_loop = parent.spawn(goal, _spawned_loop_config())
    holder: dict[str, object] = {}

    def handler(loop: Loop, step: str, context: dict) -> StepOutcome:
        if step == "act":
            holder["value"] = work(loop)
            return StepOutcome("act:completed", mode="deterministic", confidence=0.95)
        if step == "check":
            passed = "value" in holder
            return StepOutcome(
                f"check:{'passed' if passed else 'failed'}",
                mode="deterministic",
                confidence=0.95 if passed else 0.1,
                failed=not passed,
            )
        return StepOutcome(
            f"{step}:completed", mode="deterministic", confidence=0.95
        )

    result = spawned_loop.run(handler=handler, max_steps=len(spawned_loop.steps()) + 1)
    if result.stopped != "done" or "value" not in holder:
        raise RuntimeError(f"spawned_loop {spawned_loop.loop_id} did not complete: {result.stopped}")
    closure = spawned_loop.audit_closure()
    if not closure["closed"]:
        raise RuntimeError(
            f"spawned_loop {spawned_loop.loop_id} has orphaned loops: "
            f"{closure['orphaned_spawned_loops']}"
        )
    return spawned_loop, holder["value"]


def _candidate_plan() -> tuple[CandidateMethod, ...]:
    return (
        CandidateMethod(
            "fts5_title_and_abstract",
            title_field=True,
            abstract_field=True,
            description="SQLite FTS5 BM25 over paper titles and abstracts",
        ),
        CandidateMethod(
            "fts5_title_only",
            title_field=True,
            abstract_field=False,
            description="SQLite FTS5 BM25 over paper titles only",
        ),
        CandidateMethod(
            "fts5_abstract_only",
            title_field=False,
            abstract_field=True,
            description="SQLite FTS5 BM25 over paper abstracts only",
        ),
    )


def _select_candidate(evaluations: Sequence[MethodEvaluation]) -> MethodEvaluation:
    """Select by official nDCG, then recall, MRR, and stable id."""
    return sorted(
        evaluations,
        key=lambda item: (
            -item.metrics.ndcg_at_10,
            -item.metrics.recall_at_10,
            -item.metrics.mrr_at_10,
            item.candidate.candidate_id,
        ),
    )[0]


def _reference_config() -> LoopConfig:
    template = next(
        item for item in TEMPLATE_LIBRARY if item["template_id"] == "reference_nine_step"
    )
    configured = config_from_template(template, power="deep", max_depth=3)
    return replace(
        configured,
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        llm_thinking_power="",
    )


def _model_event_count(events: Sequence[dict[str, object]]) -> int:
    model_events = {
        "model_led",
        "model_escalation",
        "model_invocation",
        "model_invocation_failed",
    }
    return sum(1 for event in events if event.get("event") in model_events)


def _trec_run_text(rankings: Mapping[str, Sequence[str]]) -> str:
    lines = []
    for query_id in sorted(rankings, key=_sort_identifier):
        for rank, document_id in enumerate(rankings[query_id], start=1):
            lines.append(
                f"{query_id}\tQ0\t{document_id}\t{rank}\t{1.0 / rank:.12f}\t"
                "loop-engine"
            )
    return "\n".join(lines) + "\n"


def execute_engineering_diagnostic(
    *, data_root: Path, output_root: Path, run_id: str
) -> EngineeringDiagnosticResult:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ValueError("run id may contain only letters, numbers, dot, underscore, dash")
    source_manifest = verify_existing_source(data_root)
    output_root = output_root.resolve()
    runs_root = output_root / "runs"
    artifact_dir = output_root / run_id
    if artifact_dir.exists() or (runs_root / run_id).exists():
        raise FileExistsError(f"run {run_id!r} already exists under {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    runs_root.mkdir(parents=True, exist_ok=True)

    ledger = LoopLedger()
    root = Loop(
        "Build and run a verified retrieval solution for BEIR SciFact test",
        _reference_config(),
        ledger=ledger,
    )
    root.enable_run_history(run_id, root_dir=str(runs_root), usage_log=[])
    state: dict[str, object] = {"task": BenchmarkTask()}

    def handler(loop: Loop, step: str, context: dict) -> StepOutcome:
        if step == "orient":
            _, dataset = run_spawned_loop(
                loop,
                "intake the SciFact task and verify its frozen source",
                lambda spawned_loop: load_dataset(data_root),
            )
            state["dataset"] = dataset
            output = (
                f"task accepted; source {EXPECTED_SHA256[:12]}; "
                f"{len(dataset.qrels)} official test queries"
            )
        elif step == "reconcile_horizon":
            from loop_engine.loop.loop_templates import template_records

            intelligence_store = SolverStore(
                core_records=core_seed() + template_records()
            )
            searches = []
            for need in (
                "hypothesis experiment compare candidate methods",
                "adversarial review independently verify results",
            ):
                found = search_as_loop(
                    intelligence_store,
                    need,
                    pillar="runtime_history_solution_intelligence",
                    kind="strategy",
                    top_n=3,
                    parent=loop,
                )
                if found.get("error") is not None or not found["value"]["hits"]:
                    raise RuntimeError(f"intelligence search failed for {need!r}")
                searches.append(found)
            state["intelligence_searches"] = tuple(searches)
            output = "retrieved experiment and independent review loop guidance"
        elif step == "assess_prepare":
            dataset = state["dataset"]
            _, plan = run_spawned_loop(
                loop,
                "plan distinct deterministic retrieval candidates",
                lambda spawned_loop: _candidate_plan(),
            )
            if len(plan) < 2:
                raise RuntimeError("candidate planning produced fewer than two methods")
            state["candidates"] = plan
            output = (
                f"prepared {len(plan)} candidates for {len(dataset.qrels)} queries"
            )
        elif step == "decide_next":
            state["selection_rule"] = (
                "highest nDCG@10, then Recall@10, then MRR@10, then candidate id"
            )
            output = "freeze candidates, evaluator, population, and selection rule"
        elif step == "how":
            candidates = state["candidates"]
            if any(
                not (candidate.title_field or candidate.abstract_field)
                for candidate in candidates
            ):
                raise RuntimeError("a candidate has no searchable field")
            output = (
                "use SQLite FTS5 lexical retrieval through one search loop per query"
            )
        elif step == "act":
            dataset = state["dataset"]
            evaluations: list[MethodEvaluation] = []
            experiment_spawned_loops: list[str] = []
            for candidate in state["candidates"]:
                spawned_loop, evaluation = run_spawned_loop(
                    loop,
                    f"experiment with {candidate.candidate_id} on full SciFact test",
                    lambda experiment, candidate=candidate: evaluate_candidate(
                        dataset, candidate, parent=experiment
                    ),
                )
                experiment_spawned_loops.append(spawned_loop.loop_id)
                evaluations.append(evaluation)
            state["experiment_spawned_loops"] = tuple(experiment_spawned_loops)
            state["evaluations"] = tuple(evaluations)
            output = f"completed {len(evaluations)} full-population spawned_loop experiments"
        elif step == "verify":
            dataset = state["dataset"]

            def verify_all(spawned_loop: Loop) -> tuple[bool, ...]:
                return tuple(
                    _metric_match(
                        evaluation.metrics,
                        calculate_reference_metrics(dataset.qrels, evaluation.rankings),
                    )
                    for evaluation in state["evaluations"]
                )

            _, verified = run_spawned_loop(
                loop, "independently verify every candidate metric", verify_all
            )
            if not verified or not all(verified):
                raise RuntimeError("primary and independent candidate metrics disagree")
            selected = _select_candidate(state["evaluations"])
            state["reference_verified"] = verified
            state["selected"] = selected
            output = f"verified and selected {selected.candidate.candidate_id}"
        elif step == "integrate_commit":
            selected = state["selected"]
            spec = SolutionSpec(
                "beir_scifact_retrieval",
                allowed_modes=("deterministic",),
                loops=(
                    SolutionLoopSpec(
                        "retrieve_and_evaluate_test",
                        "evaluate_scifact_test",
                        mode="deterministic",
                        params={"candidate_id": selected.candidate.candidate_id},
                    ),
                ),
            )
            registry_stub = {"evaluate_scifact_test": lambda value, params: value}
            compiled = compile_solution(spec, registry_stub)
            if compiled["plan"] is None:
                raise RuntimeError(f"Solution Canvas did not compile: {compiled['violations']}")
            state["solution_spec"] = spec
            state["compiled"] = compiled
            state["canvas"] = render_canvas(compiled["plan"])
            ledger.record(
                loop_id=loop.loop_id,
                event="solution.canvas.updated",
                solution=spec.solution_id,
                plan_digest=compiled["digest"],
            )
            output = f"compiled Solution Canvas {compiled['digest'][:12]}"
        elif step == "route":
            dataset = state["dataset"]
            selected = state["selected"]

            def execute_canvas(owner: Loop) -> MethodEvaluation:
                def operation(value: DatasetBundle, params: dict) -> MethodEvaluation:
                    if params.get("candidate_id") != selected.candidate.candidate_id:
                        raise RuntimeError("Canvas candidate binding changed")
                    return evaluate_candidate(value, selected.candidate, parent=owner)

                trace: list[dict[str, object]] = []
                final_value = run_solution(
                    state["solution_spec"],
                    {"evaluate_scifact_test": operation},
                    dataset,
                    trace=trace,
                    ledger=ledger,
                    parent=owner,
                )
                state["solution_trace"] = tuple(trace)
                return final_value

            solution_owner, final_evaluation = run_spawned_loop(
                loop, "execute the final SciFact Solution Canvas", execute_canvas
            )
            final_reference = calculate_reference_metrics(
                dataset.qrels, final_evaluation.rankings
            )
            if not _metric_match(final_evaluation.metrics, final_reference):
                raise RuntimeError("final Canvas metrics failed independent verification")
            state["solution_owner"] = solution_owner.loop_id
            state["final_evaluation"] = final_evaluation
            state["final_reference"] = final_reference
            state["preclose_playback"] = tuple(playback(ledger.events))
            state["preclose_report"] = render_run_report(
                ledger.events,
                canvas=state["canvas"],
                title="BEIR SciFact end-to-end Loop Engine run",
            )
            output = (
                f"finish: Canvas nDCG@10={final_evaluation.metrics.ndcg_at_10:.10f}"
            )
        else:
            raise RuntimeError(f"unhandled reference step {step!r}")
        return StepOutcome(output, mode="deterministic", confidence=0.95)

    root_result = root.run(handler=handler, max_steps=len(root.steps()) + 1)
    if root_result.stopped != "done":
        raise RuntimeError(f"root Practitioner did not complete: {root_result.stopped}")

    saved = RunHistory.load(str(runs_root), run_id)
    chain = saved.verify_chain()
    final_playback = playback(saved.event_log)
    final_report = render_run_report(
        saved.event_log,
        canvas=state["canvas"],
        title="BEIR SciFact end-to-end Loop Engine run",
    )
    final_evaluation: MethodEvaluation = state["final_evaluation"]
    selected: MethodEvaluation = state["selected"]
    evaluations: tuple[MethodEvaluation, ...] = state["evaluations"]
    reference_verified: tuple[bool, ...] = state["reference_verified"]

    root_steps = [
        str(event.get("step"))
        for event in ledger.events
        if event.get("event") == "run_step" and event.get("loop_id") == root.loop_id
    ]
    query_ids = [
        query_loop
        for evaluation in evaluations + (final_evaluation,)
        for query_loop in evaluation.query_loop_ids
    ]
    terminal_ids = {
        str(event.get("loop_id"))
        for event in ledger.events
        if event.get("event") == "terminal"
    }
    solution_trace = state["solution_trace"]
    component_trace = [
        row for row in solution_trace if row.get("component_loop_id")
    ]
    root_report = report_from_ledger(
        saved.event_log, run_id=run_id, chain_intact=chain["intact"]
    )
    loop_object_ids = {
        str(event.get("loop_id"))
        for event in ledger.events
        if event.get("event") == "init"
    }
    assertions = {
        "official_source_integrity": (
            source_manifest["archive"]["url"] == SOURCE_URL
            and source_manifest["archive"]["archive_md5"] == EXPECTED_MD5
            and source_manifest["archive"]["archive_sha256"] == EXPECTED_SHA256
        ),
        "full_official_test_population": (
            len(state["dataset"].documents) == EXPECTED_CORPUS_DOCUMENTS
            and len(state["dataset"].qrels) == EXPECTED_TEST_QUERIES
            and state["dataset"].qrel_rows == EXPECTED_QREL_ROWS
        ),
        "one_reference_nine_step_root": (
            root.config.framework == "nine_step"
            and root_steps == list(root.steps())
            and root_result.steps_run == len(root.steps())
        ),
        "root_completed": root_result.stopped == "done",
        "intelligence_searches_completed": len(state["intelligence_searches"]) == 2,
        "candidate_plan_and_selection_rule_frozen": (
            len(state["candidates"]) == 3 and bool(state["selection_rule"])
        ),
        "spawned_loop_experiments_completed": (
            len(state["experiment_spawned_loops"]) == 3 and len(evaluations) == 3
        ),
        "all_candidate_metrics_independently_verified": all(reference_verified),
        "solution_canvas_compiled": (
            state["compiled"]["plan"] is not None
            and state["solution_spec"].validate()["valid"]
        ),
        "final_solution_loop_executed": (
            len(component_trace) == 1
            and component_trace[0].get("used_fallback") is False
        ),
        "final_solution_loop_owned_by_practitioner": (
            len(component_trace) == 1
            and any(
                event.get("event") == "spawn"
                and event.get("parent") == state["solution_owner"]
                and event.get("loop_id") == component_trace[0]["component_loop_id"]
                for event in ledger.events
            )
        ),
        "final_full_population_evaluated": (
            len(final_evaluation.rankings) == EXPECTED_TEST_QUERIES
            and len(final_evaluation.query_loop_ids) == EXPECTED_TEST_QUERIES
        ),
        "every_retrieval_query_crossed_a_loop": (
            len(query_ids) == EXPECTED_TEST_QUERIES * 4
            and len(set(query_ids)) == len(query_ids)
            and all(loop_id in terminal_ids for loop_id in query_ids)
        ),
        "final_metrics_independently_verified": _metric_match(
            final_evaluation.metrics, state["final_reference"]
        ),
        "final_canvas_reproduced_selected_method": (
            final_evaluation.metrics == selected.metrics
            and final_evaluation.rankings == selected.rankings
        ),
        "no_orphaned_starting_loop_spawns": root.audit_closure()["closed"],
        "zero_model_calls": (
            root_report.model_calls == 0
            and _model_event_count(ledger.events) == 0
            and all(evaluation.model_calls == 0 for evaluation in evaluations)
            and final_evaluation.model_calls == 0
        ),
        "run_history_saved_and_chain_verified": chain["intact"],
        "playback_includes_root_terminal": (
            bool(final_playback)
            and any(
                line.startswith(f"[{root.loop_id}] TERMINAL: done")
                for line in final_playback
            )
        ),
        "root_prepared_playback_and_report_before_close": (
            bool(state["preclose_playback"])
            and bool(state["preclose_report"]["transcript"])
            and bool(state["preclose_report"]["canvas_mermaid"])
        ),
        "final_report_uses_completed_run_history": (
            final_report["transcript"] == final_playback
            and final_report["analysis"]["totals"]["loops"] > 0
            and bool(final_report["canvas_mermaid"])
        ),
    }
    engineering_checks_passed = all(assertions.values())
    status = (
        "engineering_diagnostic_excluded"
        if engineering_checks_passed
        else "engineering_diagnostic_failed"
    )
    diagnostic_baseline_match = all(
        abs(getattr(final_evaluation.metrics, key) - value) < 1e-12
        for key, value in OBSERVED_BASELINE.items()
    )

    diagnostics = tuple(
        CandidateDiagnostic(
            candidate_id=evaluation.candidate.candidate_id,
            description=evaluation.candidate.description,
            metrics=evaluation.metrics,
            queries=len(evaluation.rankings),
            query_loops=len(evaluation.query_loop_ids),
            model_calls=evaluation.model_calls,
            reference_verified=reference_verified[index],
        )
        for index, evaluation in enumerate(evaluations)
    )
    artifact_dir.mkdir(parents=False, exist_ok=False)
    report_files = {
        "result": str(artifact_dir / "result.json"),
        "html_report": str(artifact_dir / "report.html"),
        "playback": str(artifact_dir / "playback.txt"),
        "canvas": str(artifact_dir / "solution-canvas.mmd"),
        "final_ranking": str(artifact_dir / "final-ranking.tsv"),
        "run_history": str(runs_root / run_id),
    }
    result = EngineeringDiagnosticResult(
        record_type="beir_scifact_engineering_diagnostic/v1",
        status=status,
        engineering_checks_passed=engineering_checks_passed,
        selected_benchmark_evidence=False,
        exclusion_reason=(
            "Selected benchmarks require non-deterministic runs. This "
            "deterministic zero-model-call diagnostic does not answer that question."
        ),
        benchmark="BEIR SciFact",
        split="test",
        scope=(
            "deterministic engineering diagnostic of the reference nine-step "
            "Practitioner and final Solution Canvas"
        ),
        source={
            "url": SOURCE_URL,
            "archive_md5": EXPECTED_MD5,
            "archive_sha256": EXPECTED_SHA256,
        },
        population={
            "corpus_documents": len(state["dataset"].documents),
            "query_file_rows": state["dataset"].query_file_rows,
            "test_queries": len(state["dataset"].qrels),
            "qrel_rows": state["dataset"].qrel_rows,
            "population_sha256": state["dataset"].population_sha256,
        },
        root_practitioner={
            "run_id": run_id,
            "loop_id": root.loop_id,
            "profile": "reference_nine_step",
            "steps": list(root.steps()),
            "mode": "deterministic",
            "model_calls": root_report.model_calls,
            "loop_objects": len(loop_object_ids),
        },
        solution_canvas={
            "solution_id": state["solution_spec"].solution_id,
            "plan_digest": state["compiled"]["digest"],
            "selected_candidate": selected.candidate.candidate_id,
            "final_query_loops": len(final_evaluation.query_loop_ids),
            "model_calls": final_evaluation.model_calls,
        },
        diagnostic_metrics=final_evaluation.metrics,
        component_diagnostics=diagnostics,
        run_shape_assertions=assertions,
        run_history={
            "events": chain["events"],
            "head_digest": saved.event_log[-1].event_digest if saved.event_log else "",
            "chain_intact": chain["intact"],
            "playback_lines": len(final_playback),
        },
        report_files=report_files,
        diagnostic_baseline_match=diagnostic_baseline_match,
        limitations=(
            "This is one retrieval dataset and does not establish general task quality.",
            "The three candidate methods share one lexical engine and are not "
            "an exhaustive search.",
            "The run measures retrieval quality, not downstream claim verification quality.",
        ),
    )

    (artifact_dir / "result.json").write_text(
        json.dumps(asdict(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "report.html").write_text(
        final_report["html"], encoding="utf-8"
    )
    (artifact_dir / "playback.txt").write_text(
        "\n".join(final_playback) + "\n", encoding="utf-8"
    )
    (artifact_dir / "solution-canvas.mmd").write_text(
        state["canvas"]["mermaid"] + "\n", encoding="utf-8"
    )
    (artifact_dir / "final-ranking.tsv").write_text(
        _trec_run_text(final_evaluation.rankings), encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    parser.add_argument("--data-root", type=Path, default=here / "data")
    parser.add_argument("--output-root", type=Path, default=here / "output")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = execute_engineering_diagnostic(
        data_root=args.data_root,
        output_root=args.output_root,
        run_id=args.run_id,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.engineering_checks_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
