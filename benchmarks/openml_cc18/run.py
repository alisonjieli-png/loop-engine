#!/usr/bin/env python3
"""Run the selected three-task OpenML-CC18 portfolio through Loop Engine.

Selected mode: one non-deterministic reference-nine-step Practitioner per
task. Each task uses two distinct model-led candidate loops, one model-led
synthesis loop, and at most one evaluator-triggered repair loop. Every actual
provider request uses Ollama Cloud, the exact discovered model ID, and its
source-backed maximum output setting.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import yaml


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
for candidate in (str(REPOSITORY_ROOT), str(SOURCE_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from benchmarks.openml_cc18.code_intelligence import (  # noqa: E402
    build_code_records,
    build_portfolio_code_pack,
    code_pack_as_dict,
    materialize_record,
)
from benchmarks.openml_cc18.openml_runtime import (  # noqa: E402
    FoldPredictionArtifact,
    OpenMLTaskBundle,
    canonical_json_digest,
    prediction_artifact_as_dict,
)
from loop_engine.code_nodes.run_playback import playback, render_run_report  # noqa: E402
from loop_engine.code_nodes.solution_canvas import SolutionLoopSpec, SolutionSpec  # noqa: E402
from loop_engine import (  # noqa: E402
    PortfolioMaterializationServices,
    PortfolioRequest,
    PortfolioSelectionServices,
    export_intelligence_portfolios,
    materialize_portfolio_for_loop,
    select_intelligence_portfolio,
)
from loop_engine.loop.loop_contract import LoopContract  # noqa: E402
from loop_engine.loop.loop_profile_catalog import LoopProfileRef  # noqa: E402
from loop_engine.loop.loop_profile_ontology import (  # noqa: E402
    LoopProfileBindingRequest,
    bind_profile,
)
from loop_engine.loop.recursive_loop import (  # noqa: E402
    Loop,
    LoopConfig,
    LoopLedger,
    StepOutcome,
)
from loop_engine.core.run_history import RunHistory  # noqa: E402
from loop_engine.core.model_capabilities import (  # noqa: E402
    require_declared_maximum,
)
from loop_engine.core.ollama_client import (  # noqa: E402
    DEFAULT_MODEL,
    live_models,
    output_capability_for,
)
from loop_engine.core.provider_pinned import (  # noqa: E402
    ProviderPinnedRequest,
    invoke_provider_model,
)
from loop_engine.core.store_serve import StoreRecord  # noqa: E402


TRACK_ID = "openml_cc18_smallest_metadata_workload_slice"
PORTFOLIO_PATH = REPOSITORY_ROOT / "docs" / "benchmarks" / "first-loop-engine-portfolio.yaml"
PROVIDER = "ollama_cloud"
MODEL = "deepseek-v4-flash:0731"
MAXIMUM_OUTPUT_TOKENS = 65536
PER_TASK_PHYSICAL_CALL_CEILING = 4
TRACK_PHYSICAL_CALL_CEILING = 12
PACKET_PHYSICAL_CALL_CEILING = 14
EXPECTED_CALLS_WITHOUT_REPAIR = 9
PROVIDER_TIMEOUT_SECONDS = 120.0
FOLD_EXECUTOR_ID = "code.openml.execute_official_folds"
CODE_RECORD_IDS = {
    "source": "code.openml.verify_source_artifact",
    "arff": "code.openml.load_arff_frame",
    "splits": "code.openml.load_official_splits",
    "bundle": "code.openml.load_task_bundle",
    "preprocessor": "code.openml.build_preprocessor",
    "logistic": "code.openml.logistic_pipeline",
    "random_forest": "code.openml.seeded_random_forest",
    "executor": FOLD_EXECUTOR_ID,
    "evaluator": "code.openml.accuracy_evaluator",
    "compiler": "code.openml.canvas_compiler",
    "runner": "code.openml.canvas_runner",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_is_valid(evaluation: Mapping[str, Any] | None) -> bool:
    """Keep score validity separate from any later quality threshold."""
    if not evaluation:
        return False
    return bool(evaluation.get("score_valid"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, default=str) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def plain_punctuation(value: Any) -> Any:
    """Keep benchmark-owned human output on plain ASCII punctuation."""

    if isinstance(value, str):
        return value.replace(chr(0x2014), "-").replace(chr(0x2013), "-")
    if isinstance(value, list):
        return [plain_punctuation(item) for item in value]
    if isinstance(value, tuple):
        return tuple(plain_punctuation(item) for item in value)
    if isinstance(value, dict):
        return {key: plain_punctuation(item) for key, item in value.items()}
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fetch_bytes(url: str, *, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "loop-engine-openml-cc18/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = fetch_bytes(url)
    parsed = json.loads(raw.decode("utf-8"))
    return parsed, {
        "url": url,
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
        "fetched_at": utc_now(),
    }


def load_track_contract() -> dict[str, Any]:
    document = yaml.safe_load(PORTFOLIO_PATH.read_text(encoding="utf-8"))
    matches = [track for track in document["tracks"] if track["id"] == TRACK_ID]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one track {TRACK_ID!r}")
    track = matches[0]
    selected = [int(value) for value in track["selection"]["task_ids"]]
    if selected != [11, 10101, 3560]:
        raise RuntimeError(f"frozen selected task order changed: {selected}")
    return track


def _task_source_data(task_document: Mapping[str, Any]) -> dict[str, Any]:
    inputs = task_document["task"]["input"]
    matches = [item["data_set"] for item in inputs if item.get("name") == "source_data"]
    if len(matches) != 1:
        raise ValueError("OpenML task must have exactly one source_data input")
    return matches[0]


def _task_estimation(task_document: Mapping[str, Any]) -> dict[str, Any]:
    inputs = task_document["task"]["input"]
    matches = [
        item["estimation_procedure"]
        for item in inputs
        if item.get("name") == "estimation_procedure"
    ]
    if len(matches) != 1:
        raise ValueError("OpenML task must have exactly one estimation procedure")
    return matches[0]


def _parameter_map(estimation: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(item["name"]): str(item.get("value", ""))
        for item in estimation.get("parameter", [])
    }


def _path_from_url(url: str) -> str:
    return urllib.parse.urlparse(url).path


def verify_live_mapping(
    track: Mapping[str, Any],
    study_document: Mapping[str, Any],
    task_document: Mapping[str, Any],
    data_document: Mapping[str, Any],
    task_spec: Mapping[str, Any],
) -> dict[str, Any]:
    study = study_document["study"]
    task = task_document["task"]
    data = data_document["data_set_description"]
    source_data = _task_source_data(task_document)
    estimation = _task_estimation(task_document)
    parameters = _parameter_map(estimation)
    suite_tasks = [int(value) for value in study["tasks"]["task_id"]]
    expected_task_id = int(task_spec["task_id"])
    violations = []
    checks = {
        "suite_id": int(study.get("id", -1)) == int(track["source"]["suite_id"]),
        "suite_alias": study.get("alias") == track["source"]["suite_alias"],
        "suite_status": study.get("status") == track["source"]["suite_status"],
        "suite_task_count": len(suite_tasks) == int(track["source"]["suite_task_count"]),
        "task_in_suite": expected_task_id in suite_tasks,
        "task_id": int(task.get("task_id", -1)) == expected_task_id,
        "task_type": task.get("task_type") == "Supervised Classification",
        "data_id": int(source_data.get("data_set_id", -1)) == int(task_spec["data_id"]),
        "target": source_data.get("target_feature") == task_spec["target"],
        "data_name": data.get("name") == task_spec["name"],
        "data_version": int(data.get("version", -1)) == int(task_spec["dataset_version"]),
        "data_status": data.get("status") == "active",
        "license_label": data.get("licence") == "Public",
        "dataset_md5": data.get("md5_checksum") == task_spec["dataset_md5"],
        "default_target": data.get("default_target_attribute") == task_spec["target"],
        "split_type": estimation.get("type") == track["split_contract"]["type"],
        "split_repeats": int(parameters.get("number_repeats", -1))
        == int(track["split_contract"]["repeats"]),
        "split_folds": int(parameters.get("number_folds", -1))
        == int(track["split_contract"]["folds"]),
        "split_stratified": parameters.get("stratified_sampling", "").lower()
        == str(track["split_contract"]["stratified"]).lower(),
        "split_path": _path_from_url(estimation.get("data_splits_url", ""))
        == _path_from_url(task_spec["split_url"]),
    }
    for name, passed in checks.items():
        if not passed:
            violations.append(name)
    if violations:
        raise ValueError(
            f"live OpenML mapping failed for task {expected_task_id}: {violations}"
        )
    return {
        "record_type": "openml_live_mapping_check/v1",
        "task_id": expected_task_id,
        "data_id": int(task_spec["data_id"]),
        "dataset_name": task_spec["name"],
        "target": task_spec["target"],
        "suite_id": int(study["id"]),
        "suite_task_count": len(suite_tasks),
        "license_label": data["licence"],
        "license_precision": "OpenML literal label, not a precise SPDX license",
        "checks": checks,
        "verified": True,
    }


def ensure_download(
    destination: Path,
    url: str,
    verifier: Callable[..., dict[str, Any]],
    verifier_kwargs: Mapping[str, Any],
) -> dict[str, Any]:
    if destination.exists():
        return verifier(destination, **dict(verifier_kwargs))
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = fetch_bytes(url)
    temporary = destination.with_suffix(destination.suffix + ".download")
    temporary.write_bytes(raw)
    try:
        check = verifier(temporary, **dict(verifier_kwargs))
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.replace(destination)
    check["path"] = str(destination)
    return check


def prepare_sources(
    track: Mapping[str, Any],
    data_directory: Path,
    verifier: Callable[..., dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    study_document, study_fetch = fetch_json(str(track["source_url"]))
    task_specs = {int(task["task_id"]): dict(task) for task in track["tasks"]}
    ordered_specs = [task_specs[int(task_id)] for task_id in track["selection"]["task_ids"]]
    prepared = []
    source_rows = []
    for task_spec in ordered_specs:
        task_id = int(task_spec["task_id"])
        task_document, task_fetch = fetch_json(
            f"https://www.openml.org/api/v1/json/task/{task_id}"
        )
        data_document, data_fetch = fetch_json(
            f"https://www.openml.org/api/v1/json/data/{int(task_spec['data_id'])}"
        )
        mapping = verify_live_mapping(
            track, study_document, task_document, data_document, task_spec
        )
        dataset_path = data_directory / f"task-{task_id}-dataset.arff"
        split_path = data_directory / f"task-{task_id}-splits.arff"
        dataset_check = ensure_download(
            dataset_path,
            str(task_spec["dataset_url"]),
            verifier,
            {
                "expected_sha256": task_spec["dataset_sha256"],
                "expected_bytes": int(task_spec["dataset_bytes"]),
                "expected_md5": task_spec["dataset_md5"],
            },
        )
        split_check = ensure_download(
            split_path,
            str(task_spec["split_url"]),
            verifier,
            {
                "expected_sha256": task_spec["split_sha256"],
                "expected_bytes": int(task_spec["split_bytes"]),
            },
        )
        prepared.append(
            {
                "task_spec": task_spec,
                "dataset_path": dataset_path,
                "split_path": split_path,
                "mapping": mapping,
                "source_checks": {"dataset": dataset_check, "split": split_check},
            }
        )
        source_rows.append(
            {
                "task_id": task_id,
                "task_api": task_fetch,
                "data_api": data_fetch,
                "mapping": mapping,
                "dataset": dataset_check,
                "split": split_check,
            }
        )
    snapshot = {
        "record_type": "openml_cc18_source_snapshot/v1",
        "captured_at": utc_now(),
        "portfolio_contract": str(PORTFOLIO_PATH.relative_to(REPOSITORY_ROOT)),
        "portfolio_contract_sha256": sha256_bytes(PORTFOLIO_PATH.read_bytes()),
        "suite_api": study_fetch,
        "suite": {
            "id": int(study_document["study"]["id"]),
            "alias": study_document["study"]["alias"],
            "status": study_document["study"]["status"],
            "task_count": len(study_document["study"]["tasks"]["task_id"]),
            "creation_date": study_document["study"]["creation_date"],
        },
        "selection": [int(value) for value in track["selection"]["task_ids"]],
        "tasks": source_rows,
        "license_use_note": (
            "The live metadata label is Public. This run is a user-directed local "
            "evaluation and does not convert that label into a legal conclusion."
        ),
    }
    return prepared, snapshot


def environment_lock() -> dict[str, Any]:
    distributions = sorted(
        (
            {
                "name": distribution.metadata.get("Name", ""),
                "version": distribution.version,
            }
            for distribution in importlib.metadata.distributions()
        ),
        key=lambda item: item["name"].lower(),
    )
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except Exception:
        revision = "unknown"
    important = {}
    for name in ("numpy", "pandas", "scipy", "scikit-learn", "threadpoolctl", "PyYAML"):
        try:
            important[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            important[name] = None
    return {
        "record_type": "openml_cc18_environment_lock/v1",
        "captured_at": utc_now(),
        "python": sys.version,
        "python_executable": sys.executable,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "loop_engine_revision": revision,
        "important_packages": important,
        "all_distributions": distributions,
    }


def context_records() -> dict[str, StoreRecord]:
    definitions = {
        "first_principles": (
            "First principles for small tabular classification",
            "Reason from sample size, feature representation, class count, bias, variance, "
            "and the fixed official split geometry. Do not use benchmark outcomes.",
            {
                "context_type": "method",
                "question_family": "first_principles",
                "thinking_style": "first_principles",
            },
        ),
        "alternatives": (
            "Alternative fixed model families",
            "Compare the declared linear logistic candidate with the declared nonlinear "
            "200-tree seeded random forest. Do not invent a third candidate.",
            {
                "context_type": "method",
                "question_family": "novel_alternatives",
                "thinking_style": "maximum_diversity",
            },
        ),
        "missing_information": (
            "Missing information before model selection",
            "Identify what schema-only metadata cannot establish, including interactions, "
            "separability, calibration, and generalization on unseen official folds.",
            {
                "context_type": "checklist",
                "question_family": "missing_items",
                "thinking_style": "information_gain",
            },
        ),
        "failure_modes": (
            "Failure modes for official-fold tabular execution",
            "Check convergence, sparse one-hot compatibility, unseen categories, class "
            "coverage, split integrity, prediction alignment, and evaluator independence.",
            {
                "context_type": "warning",
                "question_family": "adversarial_review",
                "thinking_style": "failure_analysis",
            },
        ),
        "cost": (
            "Cost and resource lens",
            "Account for one CPU thread, ten complete fits, estimator count, model-call count, "
            "elapsed time, provider tokens, and unknown provider price.",
            {
                "context_type": "constraint",
                "question_family": "cost_compression",
            },
        ),
        "verification": (
            "Independent verification contract",
            "A deterministic accuracy evaluator outside model judgment checks official row "
            "IDs, frozen labels, per-fold accuracy, and the ten-fold mean.",
            {
                "context_type": "evaluation",
                "question_family": "evidence_needed",
                "thinking_style": "verification",
                "response_shape": "evaluation",
            },
        ),
        "output_contract": (
            "Typed output and format contract",
            "The compiled Canvas must emit openml_fold_predictions/v1 for every official "
            "fold, followed by an openml_accuracy_evaluation/v1 decision object.",
            {
                "context_type": "output_contract",
                "category": "output_template",
                "serialization_format": "json",
            },
        ),
    }
    output = {}
    for key, (title, text, ontology) in definitions.items():
        facets = {
            "category": ontology.get("category", "method"),
            "subcategory": key,
            "scope": "benchmark_task",
            "lifecycle": "registered",
            **{name: value for name, value in ontology.items() if name != "category"},
        }
        output[key] = StoreRecord(
            record_id=f"context.openml.{key}",
            kind="context",
            title=title,
            body={
                "role": "context_intelligence",
                "text": text,
                "maturity": "registered",
                "facets": facets,
            },
            tags=("openml_cc18", "context", key),
            tier="core",
            source="portfolio_run_contract",
        )
    return output


def user_feedback_intelligence_records() -> list[StoreRecord]:
    rules = {
        "full_end_to_end": (
            "Run the full end-to-end Loop Engine Practitioner path only. A partial "
            "Canvas or evaluator probe is not the selected run."
        ),
        "selected_mode": (
            "The selected benchmark mode is non-deterministic. Do not label a "
            "hybrid or deterministic comparison arm as selected."
        ),
        "source_backed_maximum": (
            "Use the exact discovered Ollama Cloud model and its source-backed "
            "maximum output tokens. Never lower or invent the output cap."
        ),
        "real_provider_only": (
            "Never use a fake or synthetic model provider. Cross-provider failover "
            "is disabled."
        ),
        "varied_context": (
            "Use varied Context Intelligence lenses, separate model-led candidate "
            "loops, and a model-led synthesis loop."
        ),
        "visible_failures": (
            "Failures remain visible in the three-task denominator. Missing usage "
            "and provider price remain unknown, not zero."
        ),
    }
    combined = " ".join(f"{key}: {value}" for key, value in rules.items())
    return [StoreRecord(
        record_id="user.openml.active_owner_rules",
        kind="strategy",
        title="Active owner rules for the full OpenML Practitioner run",
        body={
            "role": "user_feedback_intelligence",
            "guidance_type": "instruction",
            "instruction": combined,
            "text": combined,
            "rules": rules,
            "status": "active",
            "maturity": "registered",
            "facets": {
                "category": "instruction",
                "subcategory": "active_owner_rules",
                "scope": "benchmark_campaign",
                "lifecycle": "registered",
                "context_type": "constraint",
                "question_family": "constraint_review",
                "thinking_style": "constraint_analysis",
            },
        },
        tags=(
            "owner_rule", "openml_cc18", "full_end_to_end",
            "non_deterministic", "source_backed_maximum", "no_fake_models",
            "varied_context", "failures_visible",
        ),
        tier="core",
        source="active_owner_direction_2026_08_25",
    )]


def previous_run_records(current_summaries: Iterable[Mapping[str, Any]]) -> list[StoreRecord]:
    records = []
    root = Path.home() / ".loop-engine"
    manifests = []
    if root.is_dir():
        manifests = sorted(
            root.rglob("manifest.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:12]
    for manifest_path in manifests:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            run_id = str(manifest["run_id"])
            run_history = RunHistory.load(str(manifest_path.parent.parent), run_id)
            chain = run_history.verify_chain()
            if not chain["intact"]:
                continue
            goal = ""
            for event in run_history.event_log:
                if event.event_type == "loop_init" and event.detail.get("goal"):
                    goal = str(event.detail["goal"])
                    break
            records.append(
                StoreRecord(
                    record_id=f"past.external.{sha256_bytes(str(manifest_path).encode())[:16]}",
                    kind="strategy",
                    title=f"Previous verified Loop Engine run: {goal or run_id}",
                    body={
                        "role": "runtime_history_solution_intelligence",
                        "history_type": "run",
                        "run_id": run_id,
                        "events": chain["events"],
                        "chain_intact": True,
                        "text": "Previous run with a verified hash chain and recorded provider or deterministic Loop history.",
                        "maturity": "committed",
                        "facets": {
                            "category": "run",
                            "subcategory": "run_history",
                            "scope": "cross_run",
                            "lifecycle": "committed",
                        },
                    },
                    tags=("previous", "run", "run_history", "loop_engine"),
                    tier="core",
                    source="verified_local_run_history",
                )
            )
        except Exception:
            continue
    for summary in current_summaries:
        run_id = str(summary["run_id"])
        records.append(
            StoreRecord(
                record_id=f"past.openml.{run_id}",
                kind="strategy",
                title=f"Previous OpenML full Practitioner run for task {summary['task_id']}",
                body={
                    "role": "runtime_history_solution_intelligence",
                    "history_type": "run",
                    "run_id": run_id,
                    "selected_algorithm": summary.get("selected_algorithm"),
                    "physical_calls": summary.get("physical_calls"),
                    "chain_intact": summary.get("run_history_chain_intact"),
                    "text": "Earlier task in this frozen campaign completed the same full loop and Canvas contract.",
                    "maturity": "committed",
                    "facets": {
                        "category": "run",
                        "subcategory": "openml_cc18",
                        "scope": "campaign",
                        "lifecycle": "committed",
                    },
                },
                tags=("previous", "run", "openml_cc18", "practitioner"),
                tier="core",
                source="current_campaign_verified_run_history",
            )
        )
    deduplicated = {record.record_id: record for record in records}
    return list(deduplicated.values())


def core_layer_records(
    current_summaries: Iterable[Mapping[str, Any]],
) -> dict[str, list[StoreRecord]]:
    """Supply the four canonical layers to the core portfolio selector."""

    return {
        "context_intelligence": list(context_records().values()),
        "code_intelligence": [],
        "runtime_history_solution_intelligence": previous_run_records(current_summaries),
        "user_feedback_intelligence": user_feedback_intelligence_records(),
    }


def select_and_materialize_core_portfolio(
    parent: Loop,
    *,
    task_state: dict[str, Any],
    consuming_loop_id: str,
    candidate: str,
    task_query: str = "",
) -> Any:
    """Use the core seven-lens selector and materializer for one spawned_loop."""

    benchmark_id = f"openml-cc18-task-{task_state['task_id']}-{candidate}"
    code_pack = build_portfolio_code_pack(
        benchmark_id, candidate=candidate
    )
    request = PortfolioRequest(
        task=task_query or (
            f"Select and verify a fixed tabular pipeline for OpenML task "
            f"{task_state['task_id']} using official folds"
        ),
        consuming_loop_id=consuming_loop_id,
        benchmark_id=benchmark_id,
        mode="non_deterministic",
    )
    selection_services = PortfolioSelectionServices(
        layer_records=task_state["layer_records"],
        code_pack=code_pack,
        ledger=parent.ledger,
        parent=parent,
    )
    portfolio = select_intelligence_portfolio(request, selection_services)
    materialized = materialize_portfolio_for_loop(
        portfolio,
        PortfolioMaterializationServices(
            layer_records=task_state["layer_records"],
            code_pack=code_pack,
            ledger=parent.ledger,
            parent=parent,
        ),
    )
    selected_layers = [item.layer for item in portfolio.items]
    selected_ids = [item.record_id for item in portfolio.items]
    if "code_intelligence" not in selected_layers:
        raise RuntimeError("core portfolio did not select the real candidate Code ref")
    if "user.openml.active_owner_rules" not in selected_ids:
        raise RuntimeError("core portfolio did not consume the active User Feedback Intelligence rules")
    coverage = {row.layer: row for row in portfolio.layer_coverage}
    if any(
        coverage[layer].state not in ("queried", "empty_visible")
        for layer in (
            "context_intelligence",
            "code_intelligence",
            "runtime_history_solution_intelligence",
            "user_feedback_intelligence",
        )
    ):
        raise RuntimeError("core portfolio did not query all four intelligence layers")
    parent.ledger.record(
        loop_id=parent.loop_id,
        event="intelligence.portfolio.consumed",
        portfolio_id=portfolio.portfolio_id,
        consuming_loop_id=consuming_loop_id,
        consumed_intelligence_refs=materialized.consumption.consumed_refs,
        consumption_digest=materialized.consumption.record_digest,
        selected_record_ids=tuple(selected_ids),
        selector="core.intelligence_portfolio",
        selection_model_calls=portfolio.selection_model_calls,
        materialization_model_calls=materialized.consumption.materialization_model_calls,
    )
    task_state.setdefault("intelligence_portfolios", []).append(portfolio)
    task_state.setdefault("intelligence_consumption", []).append(
        materialized.consumption
    )
    return materialized


def core_portfolio_prompt(materialized: Any) -> str:
    """Render the seven consumed core refs without exposing callable bodies."""

    items = {item.family: item for item in materialized.portfolio.items}
    blocks = []
    for value in materialized.values:
        item = items[value.family]
        payload = value.value
        if isinstance(payload, dict) and any(callable(entry) for entry in payload.values()):
            visible = {
                "callable_entrypoints": sorted(
                    key for key, entry in payload.items() if callable(entry)
                )
            }
        elif isinstance(payload, str):
            visible = payload
        elif isinstance(payload, Mapping):
            visible = {
                key: payload[key]
                for key in (
                    "run_id",
                    "events",
                    "chain_intact",
                    "selected_algorithm",
                    "physical_calls",
                    "text",
                )
                if key in payload
            }
        else:
            visible = type(payload).__name__
        blocks.append(
            json.dumps(
                {
                    "lens_family": value.family.value,
                    "loop_ref": value.ref.loop_ref,
                    "record_id": item.record_id,
                    "layer": item.layer,
                    "value": visible,
                },
                sort_keys=True,
                default=str,
            )
        )
    return "\n".join(blocks)


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("model output must be a JSON object")
    return value


def candidate_validator(expected: str) -> Callable[[str], bool]:
    def validate(text: str) -> bool:
        value = parse_json_object(text)
        return (
            value.get("candidate") == expected
            and isinstance(value.get("assessment"), str)
            and bool(value["assessment"].strip())
            and value.get("advance") in (True, False)
        )

    return validate


def selection_validator(text: str) -> bool:
    value = parse_json_object(text)
    return (
        value.get("choice") in ("logistic", "random_forest")
        and isinstance(value.get("reason"), str)
        and bool(value["reason"].strip())
    )


def provider_preflight() -> dict[str, Any]:
    if DEFAULT_MODEL != MODEL:
        raise RuntimeError(f"package default {DEFAULT_MODEL!r} differs from frozen model {MODEL!r}")
    models = live_models()
    if MODEL not in models:
        raise RuntimeError(f"exact Ollama Cloud model {MODEL!r} is not currently discoverable")
    capability = output_capability_for(MODEL)
    maximum = require_declared_maximum(MAXIMUM_OUTPUT_TOKENS, capability)
    if maximum != MAXIMUM_OUTPUT_TOKENS:
        raise RuntimeError("resolved model maximum changed")
    return {
        "record_type": "ollama_provider_preflight/v1",
        "provider": PROVIDER,
        "exact_model_id": MODEL,
        "exact_model_present": True,
        "discovered_models_count": len(models),
        "maximum_output_tokens": maximum,
        "maximum_output_source": capability.source,
        "maximum_output_observed_at": capability.observed_at,
        "endpoint": capability.endpoint or "https://ollama.com/api/chat",
        "cross_provider_failover": False,
        "fake_or_synthetic_provider": False,
        "preflight_inference_calls": 0,
    }


def invoke_model_spawned_loop(
    parent: Loop,
    *,
    task_state: dict[str, Any],
    campaign_state: dict[str, Any],
    role: str,
    candidate: str,
    prompt_builder: Callable[[Any], str],
    intelligence_task: str = "",
    validate: Callable[[str], bool],
    call_log_path: Path,
) -> dict[str, Any]:
    if len(task_state["model_calls"]) >= PER_TASK_PHYSICAL_CALL_CEILING:
        raise RuntimeError("per-task physical call ceiling exhausted")
    if campaign_state["physical_calls"] >= TRACK_PHYSICAL_CALL_CEILING:
        raise RuntimeError("track physical call ceiling exhausted")
    contract = LoopContract(
        name=f"OpenML task {task_state['task_id']} {role}",
        execution_mode="model_led",
        input_roles=("schema_metadata", "intelligence_refs"),
        output_roles=("bounded_model_advice",),
        effects=("reads_secret", "network"),
        locality="api_calling",
        cost_class="metered",
        role="model_led_spawned_loop",
    )
    config = LoopConfig(
        framework="custom",
        custom_steps=("invoke",),
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",),
        delegated_modes=("deterministic", "non_deterministic"),
        power="light",
        llm_thinking_power="medium",
        max_depth=parent.config.max_depth,
    )
    spawned_loop = parent.spawn(
        f"model-led {role} for OpenML task {task_state['task_id']}",
        config,
        contract=contract,
    )
    intelligence = select_and_materialize_core_portfolio(
        spawned_loop,
        task_state=task_state,
        consuming_loop_id=spawned_loop.loop_id,
        candidate=candidate,
        task_query=intelligence_task,
    )
    consumed_refs = list(intelligence.consumption.consumed_refs)
    if len(consumed_refs) != 7 or len(set(consumed_refs)) != 7:
        raise RuntimeError(
            "every provider call must consume seven unique core portfolio refs"
        )
    prompt = prompt_builder(intelligence)
    holder: dict[str, Any] = {}

    def handler(loop: Loop, step: str, context: dict[str, Any]) -> StepOutcome:
        loop.ledger.record(
            loop_id=loop.loop_id,
            event="model.call.intelligence.bound",
            task_id=task_state["task_id"],
            call_role=role,
            provider=PROVIDER,
            model=MODEL,
            maximum_output_tokens=MAXIMUM_OUTPUT_TOKENS,
            consumed_intelligence_refs=tuple(consumed_refs),
            intelligence_portfolio_id=intelligence.portfolio.portfolio_id,
            intelligence_consumption_digest=intelligence.consumption.record_digest,
        )
        result = invoke_provider_model(
            ProviderPinnedRequest(
                prompt=prompt,
                provider=PROVIDER,
                model=MODEL,
                purpose="counted_generation",
                system=(
                    "You are a cost-sensitive tabular ML advisor. Use only the supplied "
                    "schema and referenced context. Be concise and return JSON only."
                ),
                temperature=0.0,
                timeout_seconds=PROVIDER_TIMEOUT_SECONDS,
                max_output_tokens=MAXIMUM_OUTPUT_TOKENS,
                thinking_power="medium",
            ),
            validate=validate,
            ledger=loop.ledger,
            parent=loop,
        )
        physical_attempts = [attempt for attempt in result.attempts if attempt.loop_id]
        physical_count = len(physical_attempts)
        if physical_count != 1:
            raise RuntimeError(
                f"model spawned_loop {role} made {physical_count} physical attempts, expected exactly one"
            )
        task_state["model_calls"].append(result)
        campaign_state["physical_calls"] += physical_count
        if len(task_state["model_calls"]) > PER_TASK_PHYSICAL_CALL_CEILING:
            raise RuntimeError("per-task physical call ceiling exceeded")
        if campaign_state["physical_calls"] > TRACK_PHYSICAL_CALL_CEILING:
            raise RuntimeError("track physical call ceiling exceeded")
        attempt = physical_attempts[0]
        log_row = {
            "record_type": "openml_model_call/v1",
            "recorded_at": utc_now(),
            "task_id": task_state["task_id"],
            "call_role": role,
            "provider": attempt.provider,
            "model": attempt.model,
            "route": attempt.route,
            "attempt_loop_id": attempt.loop_id,
            "ok": attempt.ok,
            "provider_ok": attempt.provider_ok,
            "input_tokens": attempt.input_tokens,
            "output_tokens": attempt.output_tokens,
            "token_accounting_complete": attempt.input_tokens is not None
            and attempt.output_tokens is not None,
            "maximum_output_tokens": attempt.maximum_output_tokens,
            "maximum_output_source": attempt.maximum_output_source,
            "elapsed_seconds": attempt.elapsed_seconds,
            "consumed_intelligence_refs": list(consumed_refs),
            "intelligence_portfolio_id": intelligence.portfolio.portfolio_id,
            "intelligence_consumption_digest": intelligence.consumption.record_digest,
            "cross_provider_failover": False,
            "physical_calls": physical_count,
            "provider_cost": None,
            "provider_cost_state": "unknown",
            "error_code": attempt.error_code or None,
            "error": attempt.error or None,
        }
        append_jsonl(call_log_path, log_row)
        loop.ledger.record(
            loop_id=loop.loop_id,
            event="model.call.intelligence.consumed",
            task_id=task_state["task_id"],
            call_role=role,
            attempt_loop_id=attempt.loop_id,
            consumed_intelligence_refs=tuple(consumed_refs),
            intelligence_portfolio_id=intelligence.portfolio.portfolio_id,
            intelligence_consumption_digest=intelligence.consumption.record_digest,
            provider_ok=attempt.provider_ok,
            validation_ok=attempt.validation_ok,
        )
        holder["result"] = result
        return StepOutcome(
            output=f"{role}:{'accepted' if result.ok else 'failed'}",
            mode="non_deterministic",
            confidence=0.9 if result.ok else 0.5,
            model_calls=physical_count,
        )

    spawned_loop.run(handler=handler, max_steps=2)
    result = holder["result"]
    output_reference = (
        f"modelout.{task_state['task_id']}.{role}."
        f"{sha256_bytes((result.text or result.error or role).encode())[:20]}"
    )
    return {
        "role": role,
        "spawned_loop_id": spawned_loop.loop_id,
        "result": result,
        "output_reference": output_reference,
        "parsed": parse_json_object(result.text) if result.ok else None,
        "intelligence_portfolio_id": intelligence.portfolio.portfolio_id,
        "intelligence_consumption_digest": intelligence.consumption.record_digest,
        "consumed_intelligence_refs": consumed_refs,
    }


def admit_code_intelligence_pack(
    code_records: list[StoreRecord],
    prepared_tasks: list[dict[str, Any]],
) -> tuple[dict[str, Callable[..., Any]], list[OpenMLTaskBundle], dict[str, Any]]:
    by_id = {record.record_id: record for record in code_records}
    if set(by_id) != set(CODE_RECORD_IDS.values()):
        raise RuntimeError(
            f"Code pack IDs {sorted(by_id)} do not match required {sorted(CODE_RECORD_IDS.values())}"
        )
    materialized = {record_id: materialize_record(record) for record_id, record in by_id.items()}
    bundles = []
    compile_checks = []
    for prepared in prepared_tasks:
        task_spec = prepared["task_spec"]
        bundle = materialized[CODE_RECORD_IDS["bundle"]](
            task_spec,
            dataset_path=prepared["dataset_path"],
            split_path=prepared["split_path"],
        )
        bundles.append(bundle)
        materialized[CODE_RECORD_IDS["preprocessor"]](bundle.features)
        materialized[CODE_RECORD_IDS["logistic"]](bundle.features)
        materialized[CODE_RECORD_IDS["random_forest"]](bundle.features)
        for algorithm in ("logistic", "random_forest"):
            spec = SolutionSpec(
                solution_id=f"admission-task-{task_spec['task_id']}-{algorithm}",
                allowed_modes=("deterministic",),
                loops=(
                    SolutionLoopSpec(
                        loop_id="official-fold-executor",
                        operation=FOLD_EXECUTOR_ID,
                        mode="deterministic",
                        params={
                            "algorithm": algorithm,
                            "input_type": "openml_task_bundle/v1",
                            "output_type": "openml_fold_predictions/v1",
                            "official_folds": 10,
                        },
                    ),
                ),
            )
            compiled = materialized[CODE_RECORD_IDS["compiler"]](
                spec, {FOLD_EXECUTOR_ID: materialized[FOLD_EXECUTOR_ID]}
            )
            compile_checks.append(
                {
                    "task_id": int(task_spec["task_id"]),
                    "algorithm": algorithm,
                    "plan_digest": compiled["compiled"]["digest"],
                    "canvas_rendered": bool(compiled["canvas"]["mermaid"]),
                }
            )
    admission = {
        "record_type": "openml_code_pack_admission/v1",
        "admitted_at": utc_now(),
        "registered_records": len(code_records),
        "all_entrypoints_materialized": True,
        "all_source_digests_matched": True,
        "real_task_bundles_loaded": len(bundles),
        "official_folds_per_task": [len(bundle.folds) for bundle in bundles],
        "candidate_pipelines_constructed": 2 * len(bundles),
        "typed_canvases_compiled": compile_checks,
        "fold_training_or_scoring_during_admission": False,
        "admitted": True,
    }
    return materialized, bundles, admission


def bind_root_profile(task_id: int) -> tuple[Any, LoopContract]:
    goal = (
        f"Select, compile, execute, and independently evaluate one full OpenML task {task_id} "
        "Solution Canvas on all official folds"
    )
    contract = LoopContract(
        name=f"OpenML task {task_id} full Practitioner",
        execution_mode="model_led",
        input_roles=("openml_task_bundle", "intelligence_portfolio"),
        output_roles=("evaluated_solution_canvas",),
        effects=("reads_fs", "writes_fs", "reads_secret", "network"),
        locality="external_resources",
        cost_class="metered",
        role="practitioner",
    )
    bound = bind_profile(
        LoopProfileBindingRequest(
            profile=LoopProfileRef("practitioner.reference_nine_step"),
            goal=goal,
            contract=contract,
            capabilities=("loop_spawn", "run_history_write"),
            modes=("deterministic", "hybrid", "non_deterministic"),
            preferred_modes=("non_deterministic", "deterministic", "hybrid"),
            delegated_modes=("deterministic", "hybrid", "non_deterministic"),
            logical_kind="task_semantic",
            effort="deep",
            llm_thinking_power="medium",
            max_depth=5,
        )
    )
    return bound, contract


def stage_spawned_loop(parent: Loop, stage: str, action: Callable[[Loop], Any]) -> dict[str, Any]:
    config = LoopConfig(
        framework="custom",
        custom_steps=("act",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic", "hybrid", "non_deterministic"),
        power="light",
        max_depth=parent.config.max_depth,
    )
    spawned_loop = parent.spawn(f"{stage} spawned_loop for {parent.goal}", config)
    holder: dict[str, Any] = {}

    def handler(loop: Loop, step: str, context: dict[str, Any]) -> StepOutcome:
        try:
            holder["value"] = action(loop)
            return StepOutcome(
                output=f"{stage}:completed", mode="deterministic", confidence=1.0
            )
        except Exception as error:
            holder["error"] = error
            loop.ledger.record(
                loop_id=loop.loop_id,
                event="failure.detected",
                failure_kind=f"{stage}_spawned_loop_failure",
                error_type=type(error).__name__,
                error=str(error),
            )
            return StepOutcome(
                output=f"{stage}:failed:{type(error).__name__}",
                mode="deterministic",
                confidence=0.5,
            )

    result = spawned_loop.run(handler=handler, max_steps=2)
    return {
        "loop_id": spawned_loop.loop_id,
        "value": holder.get("value"),
        "error": holder.get("error"),
        "result": result,
    }


def compile_selected_canvas(
    state: dict[str, Any],
    *,
    algorithm: str,
    materialized: Mapping[str, Callable[..., Any]],
) -> dict[str, Any]:
    spec = SolutionSpec(
        solution_id=f"openml-task-{state['task_id']}-{algorithm}",
        allowed_modes=("deterministic",),
        loops=(
            SolutionLoopSpec(
                loop_id=f"task-{state['task_id']}-official-fold-execution",
                operation=FOLD_EXECUTOR_ID,
                mode="deterministic",
                params={
                    "algorithm": algorithm,
                    "input_type": "openml_task_bundle/v1",
                    "output_type": "openml_fold_predictions/v1",
                    "official_repeats": 1,
                    "official_folds": 10,
                    "one_cpu_thread": True,
                },
            ),
        ),
    )
    registry = {FOLD_EXECUTOR_ID: materialized[FOLD_EXECUTOR_ID]}
    compiled = materialized[CODE_RECORD_IDS["compiler"]](spec, registry)
    state["selected_algorithm"] = algorithm
    state["solution_spec"] = spec
    state["registry"] = registry
    state["compiled"] = compiled
    return compiled


def execute_selected_canvas(
    state: dict[str, Any],
    *,
    parent: Loop,
    materialized: Mapping[str, Callable[..., Any]],
) -> FoldPredictionArtifact:
    trace: list[dict[str, Any]] = []
    artifact = materialized[CODE_RECORD_IDS["runner"]](
        state["compiled"]["compiled"]["plan"],
        state["registry"],
        state["bundle"],
        ledger=parent.ledger,
        parent=parent,
        trace=trace,
    )
    state["solution_trace"] = trace
    state["predictions"] = artifact
    return artifact


def run_evaluator_spawned_loop(
    parent: Loop,
    *,
    state: dict[str, Any],
    materialized: Mapping[str, Callable[..., Any]],
) -> dict[str, Any]:
    config = LoopConfig(
        framework="custom",
        custom_steps=("validate_contract", "score", "accept"),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        power="light",
        max_depth=parent.config.max_depth,
    )
    evaluator = parent.spawn(
        f"independent accuracy evaluator for OpenML task {state['task_id']}", config
    )
    holder: dict[str, Any] = {}

    def handler(loop: Loop, step: str, context: dict[str, Any]) -> StepOutcome:
        if step == "validate_contract":
            if not isinstance(state.get("predictions"), FoldPredictionArtifact):
                raise TypeError("no typed prediction artifact reached the evaluator")
            return StepOutcome("prediction_contract:present", "deterministic", 1.0)
        if step == "score":
            holder["evaluation"] = materialized[CODE_RECORD_IDS["evaluator"]](
                state["predictions"], state["bundle"]
            )
            return StepOutcome("accuracy:computed", "deterministic", 1.0)
        if not score_is_valid(holder.get("evaluation")):
            raise ValueError("independent evaluator did not produce a valid score")
        return StepOutcome("evaluation:score_valid", "deterministic", 1.0)

    result = evaluator.run(handler=handler, max_steps=4)
    state["evaluation"] = holder.get("evaluation")
    parent.ledger.record(
        loop_id=evaluator.loop_id,
        event="evaluation",
        task_id=state["task_id"],
        metric="predictive_accuracy",
        mean_accuracy=(state["evaluation"] or {}).get("mean_accuracy"),
        score_valid=score_is_valid(state.get("evaluation")),
        evaluator="sklearn.metrics.accuracy_score",
        independent_from_model_selection=True,
    )
    return {"loop_id": evaluator.loop_id, "result": result, "evaluation": state["evaluation"]}


def run_one_task(
    *,
    prepared: Mapping[str, Any],
    bundle: OpenMLTaskBundle,
    code_records: list[StoreRecord],
    materialized: Mapping[str, Callable[..., Any]],
    current_summaries: list[Mapping[str, Any]],
    campaign_directory: Path,
    campaign_state: dict[str, Any],
) -> dict[str, Any]:
    task_id = int(prepared["task_spec"]["task_id"])
    run_id = f"openml-cc18-task-{task_id}-non-deterministic-{campaign_directory.name}"
    bound, root_contract = bind_root_profile(task_id)
    ledger = LoopLedger()
    root = Loop(
        (
            f"Select, compile, execute, and independently evaluate OpenML task {task_id} "
            "on all ten official folds"
        ),
        bound.config,
        ledger=ledger,
        contract=root_contract,
    )
    root.ledger.record(
        loop_id=root.loop_id,
        event="benchmark.run.classified",
        task_id=task_id,
        selected_mode="non_deterministic",
        selected_profile=bound.profile.spec.profile_id,
        selected_profile_version=bound.profile.spec.version,
        step_template=bound.profile.step_template_id,
        partial_path=False,
        deterministic_comparison_arm=False,
        hybrid_selected=False,
    )
    run_history_root = campaign_directory / "run-histories"
    usage_log: list[dict[str, Any]] = []
    root.enable_run_history(run_id, root_dir=str(run_history_root), usage_log=usage_log)
    state: dict[str, Any] = {
        "task_id": task_id,
        "run_id": run_id,
        "bundle": bundle,
        "layer_records": core_layer_records(current_summaries),
        "intelligence_portfolios": [],
        "intelligence_consumption": [],
        "model_calls": [],
        "errors": [],
        "repair_used": False,
    }
    call_log_path = campaign_directory / "model-calls.jsonl"
    started = time.monotonic()

    def orient_action(spawned_loop: Loop) -> dict[str, Any]:
        dataset = materialized[CODE_RECORD_IDS["source"]](
            prepared["dataset_path"],
            expected_sha256=prepared["task_spec"]["dataset_sha256"],
            expected_bytes=int(prepared["task_spec"]["dataset_bytes"]),
            expected_md5=prepared["task_spec"]["dataset_md5"],
        )
        split = materialized[CODE_RECORD_IDS["source"]](
            prepared["split_path"],
            expected_sha256=prepared["task_spec"]["split_sha256"],
            expected_bytes=int(prepared["task_spec"]["split_bytes"]),
        )
        if len(bundle.folds) != 10:
            raise ValueError("task bundle does not contain all ten official folds")
        spawned_loop.ledger.record(
            loop_id=spawned_loop.loop_id,
            event="benchmark.source.verified",
            task_id=task_id,
            dataset_sha256=dataset["sha256"],
            split_sha256=split["sha256"],
            official_folds=len(bundle.folds),
            live_mapping_verified=prepared["mapping"]["verified"],
        )
        state["source_checks"] = {"dataset": dataset, "split": split}
        return {"dataset": dataset, "split": split, "schema": bundle.schema}

    def reconcile_action(spawned_loop: Loop) -> dict[str, Any]:
        intelligence = select_and_materialize_core_portfolio(
            spawned_loop,
            task_state=state,
            consuming_loop_id=spawned_loop.parent.loop_id,
            candidate="both",
            task_query=(
                f"Orient the full non-deterministic OpenML task {task_id} run with "
                "Context Code Previous Run and active User Feedback Intelligence"
            ),
        )
        state["root_intelligence"] = intelligence
        spawned_loop.ledger.record(
            loop_id=spawned_loop.parent.loop_id,
            event="root.intelligence.bound",
            portfolio_id=intelligence.portfolio.portfolio_id,
            consumed_intelligence_refs=intelligence.consumption.consumed_refs,
            consumption_digest=intelligence.consumption.record_digest,
            selector="core.intelligence_portfolio",
        )
        return intelligence.portfolio.to_dict()

    def candidate_logistic_action(spawned_loop: Loop) -> dict[str, Any]:
        def prompt_builder(intelligence: Any) -> str:
            return f"""Evaluate only the fixed logistic candidate for this task.
Schema metadata, with no current fold outcomes:
{json.dumps(bundle.schema, sort_keys=True)}
Consumed core Intelligence Portfolio:
{core_portfolio_prompt(intelligence)}
Candidate contract: one-hot unknown categories ignored; LogisticRegression C=1.0, max_iter=1000, n_jobs=1; all 10 official folds.
Return one concise JSON object with exactly these keys: candidate, assessment, advance, primary_risk. candidate must be logistic and advance must be true or false."""
        call = invoke_model_spawned_loop(
            spawned_loop,
            task_state=state,
            campaign_state=campaign_state,
            role="logistic_candidate",
            candidate="logistic",
            prompt_builder=prompt_builder,
            intelligence_task=(
                f"Evaluate the fixed logistic candidate for OpenML task {task_id} "
                "before any official fold outcome exists"
            ),
            validate=candidate_validator("logistic"),
            call_log_path=call_log_path,
        )
        state["logistic_candidate"] = call
        return call

    def decide_action(spawned_loop: Loop) -> dict[str, Any]:
        def forest_prompt_builder(intelligence: Any) -> str:
            return f"""Evaluate only the fixed random_forest candidate for this task.
Schema metadata, with no current fold outcomes:
{json.dumps(bundle.schema, sort_keys=True)}
Consumed core Intelligence Portfolio:
{core_portfolio_prompt(intelligence)}
Candidate contract: same one-hot preprocessing; RandomForestClassifier n_estimators=200, random_state=20260825, n_jobs=1; all 10 official folds.
Return one concise JSON object with exactly these keys: candidate, assessment, advance, primary_risk. candidate must be random_forest and advance must be true or false."""
        forest_call = invoke_model_spawned_loop(
            spawned_loop,
            task_state=state,
            campaign_state=campaign_state,
            role="random_forest_candidate",
            candidate="random_forest",
            prompt_builder=forest_prompt_builder,
            intelligence_task=(
                f"Evaluate the fixed seeded random forest candidate for OpenML task "
                f"{task_id} before any official fold outcome exists"
            ),
            validate=candidate_validator("random_forest"),
            call_log_path=call_log_path,
        )
        state["random_forest_candidate"] = forest_call
        logistic_value = (
            state.get("logistic_candidate", {}).get("result").text
            if state.get("logistic_candidate")
            else "logistic candidate call unavailable"
        )
        forest_value = forest_call["result"].text or "random forest candidate call unavailable"
        def synthesis_prompt_builder(intelligence: Any) -> str:
            return f"""Select exactly one fixed candidate after comparing the two independent candidate analyses.
Schema metadata, with no current fold outcomes:
{json.dumps(bundle.schema, sort_keys=True)}
Logistic candidate analysis:
{logistic_value}
Random forest candidate analysis:
{forest_value}
Consumed core Intelligence Portfolio:
{core_portfolio_prompt(intelligence)}
Return one concise JSON object with exactly these keys: choice, reason, rejected_candidate. choice must be logistic or random_forest."""
        synthesis_call = invoke_model_spawned_loop(
            spawned_loop,
            task_state=state,
            campaign_state=campaign_state,
            role="synthesis_selection",
            candidate="both",
            prompt_builder=synthesis_prompt_builder,
            intelligence_task=(
                f"Compare logistic and seeded random forest candidate analyses and select "
                f"one for OpenML task {task_id} before fold outcomes"
            ),
            validate=selection_validator,
            call_log_path=call_log_path,
        )
        state["synthesis"] = synthesis_call
        if synthesis_call["parsed"]:
            state["selected_algorithm"] = synthesis_call["parsed"]["choice"]
        else:
            state["errors"].append(
                {
                    "stage": "synthesis",
                    "error": synthesis_call["result"].error or "invalid synthesis output",
                }
            )
        return {"forest": forest_call, "synthesis": synthesis_call}

    def construction_action(spawned_loop: Loop) -> dict[str, Any]:
        algorithm = state.get("selected_algorithm")
        if algorithm not in ("logistic", "random_forest"):
            raise ValueError("model synthesis did not produce a valid fixed candidate")
        compiled = compile_selected_canvas(
            state, algorithm=algorithm, materialized=materialized
        )
        spawned_loop.ledger.record(
            loop_id=spawned_loop.loop_id,
            event="solution.canvas.updated",
            task_id=task_id,
            solution_id=compiled["compiled"]["plan"]["solution_id"],
            plan_digest=compiled["compiled"]["digest"],
            selected_algorithm=algorithm,
            input_type="openml_task_bundle/v1",
            output_type="openml_fold_predictions/v1",
            official_folds=10,
        )
        return compiled

    def execution_action(spawned_loop: Loop) -> dict[str, Any]:
        artifact = execute_selected_canvas(
            state, parent=spawned_loop, materialized=materialized
        )
        spawned_loop.ledger.record(
            loop_id=spawned_loop.loop_id,
            event="solution.run.completed",
            task_id=task_id,
            solution_id=state["compiled"]["compiled"]["plan"]["solution_id"],
            plan_digest=state["compiled"]["compiled"]["digest"],
            folds_executed=len(artifact.folds),
            prediction_artifact_digest=canonical_json_digest(
                prediction_artifact_as_dict(artifact)
            ),
        )
        return {"folds": len(artifact.folds), "algorithm": artifact.algorithm}

    def verification_action(spawned_loop: Loop) -> dict[str, Any]:
        first_error = ""
        try:
            evaluated = run_evaluator_spawned_loop(
                spawned_loop, state=state, materialized=materialized
            )
            if not score_is_valid(evaluated.get("evaluation")):
                raise ValueError(
                    "independent evaluator did not produce a valid score")
            return {"first": evaluated, "repair_used": False}
        except Exception as error:
            first_error = f"{type(error).__name__}: {error}"
            state["errors"].append({"stage": "independent_evaluator", "error": first_error})

        state["repair_used"] = True
        def repair_prompt_builder(intelligence: Any) -> str:
            return f"""The independent evaluator rejected the first compiled execution.
Failure: {first_error}
Schema: {json.dumps(bundle.schema, sort_keys=True)}
First selected candidate: {state.get('selected_algorithm')}
Failure-specific core Intelligence Portfolio:
{core_portfolio_prompt(intelligence)}
Choose logistic or random_forest for one final compile, execution, and evaluator attempt. Return one concise JSON object with exactly these keys: choice, reason, repair_action."""
        repair_call = invoke_model_spawned_loop(
            spawned_loop,
            task_state=state,
            campaign_state=campaign_state,
            role="evaluator_repair",
            candidate="both",
            prompt_builder=repair_prompt_builder,
            intelligence_task=(
                f"Repair OpenML task {task_id} after independent evaluator failure: "
                f"{first_error}"
            ),
            validate=selection_validator,
            call_log_path=call_log_path,
        )
        state["repair"] = repair_call
        if not repair_call["parsed"]:
            raise ValueError("repair model call did not produce a valid fixed candidate")
        compile_selected_canvas(
            state,
            algorithm=repair_call["parsed"]["choice"],
            materialized=materialized,
        )
        spawned_loop.ledger.record(
            loop_id=spawned_loop.loop_id,
            event="solution.canvas.updated",
            task_id=task_id,
            plan_digest=state["compiled"]["compiled"]["digest"],
            selected_algorithm=state["selected_algorithm"],
            repair=True,
        )
        execute_selected_canvas(state, parent=spawned_loop, materialized=materialized)
        repaired = run_evaluator_spawned_loop(spawned_loop, state=state, materialized=materialized)
        if not score_is_valid(repaired.get("evaluation")):
            raise ValueError(
                "independent evaluator did not score the one repair attempt")
        return {"first_error": first_error, "repair": repaired, "repair_used": True}

    def integrate_action(spawned_loop: Loop) -> dict[str, Any]:
        score_valid = score_is_valid(state.get("evaluation"))
        task_directory = campaign_directory / "tasks" / f"task-{task_id}"
        if state.get("predictions") is not None:
            prediction_body = prediction_artifact_as_dict(state["predictions"])
            write_json(task_directory / "predictions.json", prediction_body)
            prediction_digest = canonical_json_digest(prediction_body)
        else:
            prediction_digest = None
        integration = {
            "task_id": task_id,
            "artifact_valid": bool(state.get("predictions") is not None),
            "score_valid": score_valid,
            "quality_acceptance_rule": "not_defined",
            "quality_accepted": None,
            "selected_algorithm": state.get("selected_algorithm"),
            "mean_accuracy": (state.get("evaluation") or {}).get("mean_accuracy"),
            "prediction_artifact_digest": prediction_digest,
            "plan_digest": (state.get("compiled") or {}).get("compiled", {}).get("digest"),
            "physical_calls": len(state["model_calls"]),
            "repair_used": state["repair_used"],
            "failures": list(state["errors"]),
        }
        write_json(task_directory / "integrated-result.json", integration)
        spawned_loop.ledger.record(
            loop_id=spawned_loop.loop_id,
            event="benchmark.result.integrated",
            **integration,
        )
        state["integration"] = integration
        return integration

    def route_action(spawned_loop: Loop) -> dict[str, Any]:
        spawned = {
            event["loop_id"]
            for event in spawned_loop.ledger.events
            if event.get("event") == "spawn"
        }
        terminal = {
            event["loop_id"]
            for event in spawned_loop.ledger.events
            if event.get("event") == "terminal"
        }
        current_open = sorted((spawned - terminal) - {spawned_loop.loop_id})
        status = "score_valid" if score_is_valid(
            state.get("evaluation")) else "failed"
        spawned_loop.ledger.record(
            loop_id=spawned_loop.loop_id,
            event="benchmark.route.final",
            task_id=task_id,
            status=status,
            physical_calls=len(state["model_calls"]),
            repair_used=state["repair_used"],
            open_spawned_loops=tuple(current_open),
            failures_visible=tuple(state["errors"]),
        )
        state["route_status"] = status
        return {"status": status, "open_spawned_loops_before_route_close": current_open}

    actions = {
        "orient": orient_action,
        "reconcile_horizon": reconcile_action,
        "assess_prepare": candidate_logistic_action,
        "decide_next": decide_action,
        "how": construction_action,
        "act": execution_action,
        "verify": verification_action,
        "integrate_commit": integrate_action,
        "route": route_action,
    }

    def root_handler(loop: Loop, step: str, context: dict[str, Any]) -> StepOutcome:
        outcome = stage_spawned_loop(loop, step, actions[step])
        if outcome["error"] is not None:
            state["errors"].append(
                {
                    "stage": step,
                    "error": f"{type(outcome['error']).__name__}: {outcome['error']}",
                }
            )
        state.setdefault("stage_spawned_loopren", []).append(
            {
                "stage": step,
                "loop_id": outcome["loop_id"],
                "ok": outcome["error"] is None,
            }
        )
        return StepOutcome(
            output=f"{step}:spawned_loop:{outcome['loop_id']}:{'ok' if outcome['error'] is None else 'failed'}",
            mode="deterministic",
            confidence=1.0 if outcome["error"] is None else 0.5,
        )

    root_result = root.run(handler=root_handler, max_steps=len(root.steps()) + 1)
    elapsed = time.monotonic() - started
    saved = RunHistory.load(str(run_history_root), run_id)
    chain = saved.verify_chain()
    run_history_model_events = [
        event for event in saved.event_log if event.event_type == "model_invocation"
    ]
    physical_calls = len(state["model_calls"])
    if len(run_history_model_events) != physical_calls:
        raise RuntimeError(
            f"Run history has {len(run_history_model_events)} model events for {physical_calls} physical calls"
        )
    if physical_calls not in (3, 4):
        raise RuntimeError(f"task {task_id} used {physical_calls} physical calls")
    if physical_calls == 4 and not state["repair_used"]:
        raise RuntimeError("fourth physical call occurred without evaluator repair")
    orphaned = sorted(
        {
            event.detail.get("_ledger_event")
            for event in saved.event_log
            if event.detail.get("_ledger_event")
        }
    )
    solution_events = [name for name in orphaned if str(name).startswith("solution")]
    if not solution_events:
        raise RuntimeError("saved run history contains no Solution events")
    if not chain["intact"]:
        raise RuntimeError(f"saved run history chain is not intact: {chain}")

    task_directory = campaign_directory / "tasks" / f"task-{task_id}"
    intelligence_export = export_intelligence_portfolios(
        state["intelligence_portfolios"], state["intelligence_consumption"]
    )
    write_json(
        task_directory / "intelligence-portfolios.json", intelligence_export
    )
    canvas = (state.get("compiled") or {}).get("canvas")
    report = plain_punctuation(render_run_report(
        saved.event_log,
        title=f"OpenML task {task_id} full non-deterministic Practitioner run",
        canvas=canvas,
    ))
    transcript = playback(saved.event_log)
    write_text(task_directory / "playback.txt", "\n".join(transcript) + "\n")
    write_text(task_directory / "report.html", report["html"])
    report_without_html = {key: value for key, value in report.items() if key != "html"}
    write_json(task_directory / "report.json", report_without_html)
    if canvas:
        write_json(task_directory / "canvas.json", canvas["canonical"])
        write_text(task_directory / "canvas.mmd", canvas["mermaid"] + "\n")

    calls = []
    for role_name in (
        "logistic_candidate",
        "random_forest_candidate",
        "synthesis",
        "repair",
    ):
        call = state.get(role_name)
        if call:
            calls.append(
                {
                    "role": call["role"],
                    "spawned_loop_id": call["spawned_loop_id"],
                    "output_reference": call["output_reference"],
                    "parsed": call["parsed"],
                    "gateway": call["result"].to_dict(),
                    "raw_text": call["result"].text,
                }
            )
    score_valid = score_is_valid(state.get("evaluation"))
    task_result = {
        "record_type": "openml_cc18_full_practitioner_task/v2",
        "task_id": task_id,
        "data_id": int(prepared["task_spec"]["data_id"]),
        "name": prepared["task_spec"]["name"],
        "selected_population_denominator": 1,
        "selected_mode": "non_deterministic",
        "selected_profile": bound.profile.spec.profile_id,
        "selected_profile_version": bound.profile.spec.version,
        "step_template": bound.profile.step_template_id,
        "root_loop_id": root.loop_id,
        "root_result": {
            "stopped": root_result.stopped,
            "terminal_code": root_result.terminal_code,
            "steps_run": root_result.steps_run,
            "stage_order": list(root.steps()),
        },
        "stage_spawned_loopren": state.get("stage_spawned_loopren", []),
        "schema": bundle.schema,
        "source_checks": state.get("source_checks"),
        "live_mapping": prepared["mapping"],
        "selected_algorithm": state.get("selected_algorithm"),
        "candidate_calls": calls,
        "intelligence_portfolios": {
            "selector": "core.intelligence_portfolio",
            "portfolio_count": len(state["intelligence_portfolios"]),
            "consumption_count": len(state["intelligence_consumption"]),
            "fold_digest": intelligence_export["consumption"]["fold_digest"],
            "payload_bodies_exported": intelligence_export["payload_bodies_exported"],
        },
        "physical_calls": physical_calls,
        "call_ceiling": PER_TASK_PHYSICAL_CALL_CEILING,
        "repair_used": state["repair_used"],
        "canvas_plan_digest": (state.get("compiled") or {}).get("compiled", {}).get("digest"),
        "canvas_compiled": bool((state.get("compiled") or {}).get("compiled", {}).get("plan")),
        "canvas_executed": isinstance(state.get("predictions"), FoldPredictionArtifact),
        "official_folds_executed": len(state["predictions"].folds)
        if isinstance(state.get("predictions"), FoldPredictionArtifact)
        else 0,
        "evaluation": state.get("evaluation"),
        "artifact_valid": isinstance(
            state.get("predictions"), FoldPredictionArtifact),
        "score_valid": score_valid,
        "quality_acceptance_rule": "not_defined",
        "quality_accepted": None,
        "failure_reason": None if score_valid else list(state["errors"]),
        "run_history": {
            "run_id": run_id,
            "directory": str((run_history_root / run_id).relative_to(REPOSITORY_ROOT)),
            "events": chain["events"],
            "chain_intact": chain["intact"],
            "model_invocation_events": len(run_history_model_events),
            "solution_event_kinds": solution_events,
        },
        "playback_lines": len(transcript),
        "report_rendered_from_saved_run_history": True,
        "elapsed_seconds": round(elapsed, 6),
        "errors": list(state["errors"]),
    }
    write_json(task_directory / "task-result.json", task_result)
    return task_result


def summarize_usage(call_log_path: Path) -> dict[str, Any]:
    rows = []
    if call_log_path.exists():
        rows = [json.loads(line) for line in call_log_path.read_text(encoding="utf-8").splitlines()]
    complete = all(row.get("token_accounting_complete") for row in rows)
    known_rows = [row for row in rows if row.get("token_accounting_complete")]
    unknown_rows = [row for row in rows if not row.get("token_accounting_complete")]
    input_tokens = sum(int(row["input_tokens"]) for row in rows) if complete else None
    output_tokens = sum(int(row["output_tokens"]) for row in rows) if complete else None
    return {
        "physical_calls": sum(int(row.get("physical_calls", 0)) for row in rows),
        "calls": len(rows),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens if complete else None,
        "token_accounting_complete": complete,
        "calls_with_complete_token_usage": len(known_rows),
        "calls_with_unknown_token_usage": len(unknown_rows),
        "known_input_tokens_subtotal": sum(
            int(row["input_tokens"]) for row in known_rows
        ),
        "known_output_tokens_subtotal": sum(
            int(row["output_tokens"]) for row in known_rows
        ),
        "known_total_tokens_subtotal": sum(
            int(row["input_tokens"]) + int(row["output_tokens"])
            for row in known_rows
        ),
        "unknown_token_usage_calls": [
            {
                "task_id": row.get("task_id"),
                "call_role": row.get("call_role"),
                "error_code": row.get("error_code"),
            }
            for row in unknown_rows
        ],
        "provider_cost": None,
        "provider_cost_state": "unknown",
        "provider": PROVIDER,
        "model": MODEL,
        "maximum_output_tokens_each_call": MAXIMUM_OUTPUT_TOKENS,
        "cross_provider_failover": False,
    }


def excluded_campaign_attempts(
    output_root: Path, current_campaign_id: str
) -> list[dict[str, Any]]:
    """Keep earlier failed or aborted campaign costs visible."""

    attempts = []
    if not output_root.is_dir():
        return attempts
    for state_path in sorted(output_root.glob("*/campaign-state.json")):
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if state.get("campaign_id") == current_campaign_id:
            continue
        if state.get("status") == "complete":
            continue
        attempts.append(
            {
                "campaign_id": state.get("campaign_id"),
                "status": state.get("status"),
                "physical_calls": int(state.get("physical_calls", 0) or 0),
                "failure": state.get("failure"),
                "excluded_from_selected_population": True,
                "provider_usage": summarize_usage(
                    state_path.parent / "model-calls.jsonl"
                ),
            }
        )
    return attempts


def execute_campaign(args: argparse.Namespace) -> dict[str, Any]:
    track = load_track_contract()
    code_records = build_code_records()
    code_lookup = {record.record_id: record for record in code_records}
    verifier = materialize_record(code_lookup[CODE_RECORD_IDS["source"]])
    data_directory = HERE / "data"
    prepared, source_snapshot = prepare_sources(track, data_directory, verifier)
    materialized, bundles, admission = admit_code_intelligence_pack(code_records, prepared)
    provider = provider_preflight()
    lock = environment_lock()

    if args.prepare_only:
        preflight = {
            "record_type": "openml_cc18_preflight/v1",
            "prepared_at": utc_now(),
            "selected_tasks": [item["task_spec"]["task_id"] for item in prepared],
            "source_snapshot": source_snapshot,
            "code_pack": code_pack_as_dict(code_records),
            "code_pack_admission": admission,
            "provider": provider,
            "environment": lock,
            "model_inference_calls": 0,
            "selected_benchmark_executed": False,
        }
        write_json(HERE / "preflight-latest.json", preflight)
        return preflight

    if (HERE / "verified-result.json").exists():
        raise FileExistsError(
            "a completed selected campaign already exists; refusing to rerun provider calls"
        )

    campaign_id = args.campaign_id or datetime.now(timezone.utc).strftime(
        "campaign-%Y%m%dT%H%M%SZ"
    )
    if not re.fullmatch(r"[A-Za-z0-9._-]+", campaign_id):
        raise ValueError("campaign ID must contain only letters, numbers, dot, underscore, hyphen")
    campaign_directory = Path(args.output_root).resolve() / campaign_id
    if campaign_directory.exists():
        raise FileExistsError(
            f"campaign directory already exists: {campaign_directory}; refusing to rerun model calls"
        )
    campaign_directory.mkdir(parents=True, exist_ok=False)
    active = {
        "record_type": "openml_cc18_campaign_state/v1",
        "campaign_id": campaign_id,
        "status": "running",
        "started_at": utc_now(),
        "selected_tasks": [int(item["task_spec"]["task_id"]) for item in prepared],
        "selected_mode": "non_deterministic",
        "physical_call_ceiling": TRACK_PHYSICAL_CALL_CEILING,
    }
    write_json(campaign_directory / "campaign-state.json", active)
    write_json(campaign_directory / "source-snapshot.json", source_snapshot)
    write_json(campaign_directory / "environment-lock.json", lock)
    write_json(campaign_directory / "code-intelligence-pack.json", code_pack_as_dict(code_records))
    write_json(campaign_directory / "code-pack-admission.json", admission)
    write_json(campaign_directory / "provider-preflight.json", provider)

    campaign_state = {"physical_calls": 0}
    task_results = []
    current_summaries: list[Mapping[str, Any]] = []
    campaign_started = time.monotonic()
    for prepared_task, bundle in zip(prepared, bundles):
        try:
            task_result = run_one_task(
                prepared=prepared_task,
                bundle=bundle,
                code_records=code_records,
                materialized=materialized,
                current_summaries=current_summaries,
                campaign_directory=campaign_directory,
                campaign_state=campaign_state,
            )
        except Exception as error:
            task_id = int(prepared_task["task_spec"]["task_id"])
            task_result = {
                "record_type": "openml_cc18_full_practitioner_task/v2",
                "task_id": task_id,
                "data_id": int(prepared_task["task_spec"]["data_id"]),
                "name": prepared_task["task_spec"]["name"],
                "selected_population_denominator": 1,
                "selected_mode": "non_deterministic",
                "artifact_valid": False,
                "score_valid": False,
                "quality_acceptance_rule": "not_defined",
                "quality_accepted": None,
                "evaluation": None,
                "physical_calls": None,
                "failure_reason": f"{type(error).__name__}: {error}",
                "failure_preserved_in_denominator": True,
            }
            write_json(
                campaign_directory / "tasks" / f"task-{task_id}" / "task-result.json",
                task_result,
            )
        task_results.append(task_result)
        current_summaries.append(
            {
                "run_id": task_result.get("run_history", {}).get("run_id", f"failed-task-{task_result['task_id']}"),
                "task_id": task_result["task_id"],
                "selected_algorithm": task_result.get("selected_algorithm"),
                "physical_calls": task_result.get("physical_calls"),
                "run_history_chain_intact": task_result.get("run_history", {}).get("chain_intact"),
            }
        )

    usage = summarize_usage(campaign_directory / "model-calls.jsonl")
    excluded_attempts = excluded_campaign_attempts(
        Path(args.output_root).resolve(), campaign_id
    )
    packet_physical_calls = (
        usage["physical_calls"]
        + sum(item["physical_calls"] for item in excluded_attempts)
    )
    packet_known_input_tokens = usage["known_input_tokens_subtotal"] + sum(
        item["provider_usage"]["known_input_tokens_subtotal"]
        for item in excluded_attempts
    )
    packet_known_output_tokens = usage["known_output_tokens_subtotal"] + sum(
        item["provider_usage"]["known_output_tokens_subtotal"]
        for item in excluded_attempts
    )
    packet_unknown_token_calls = usage["calls_with_unknown_token_usage"] + sum(
        item["provider_usage"]["calls_with_unknown_token_usage"]
        for item in excluded_attempts
    )
    score_valid = [result for result in task_results
                   if result.get("score_valid")]
    scored = [
        result
        for result in task_results
        if (result.get("evaluation") or {}).get("mean_accuracy") is not None
    ]
    overall = {
        "record_type": "openml_cc18_full_practitioner_campaign/v2",
        "campaign_id": campaign_id,
        "completed_at": utc_now(),
        "elapsed_seconds": round(time.monotonic() - campaign_started, 6),
        "portfolio_contract": str(PORTFOLIO_PATH.relative_to(REPOSITORY_ROOT)),
        "track_id": TRACK_ID,
        "selected_mode": "non_deterministic",
        "selected_profile": "practitioner.reference_nine_step",
        "task_population": [11, 10101, 3560],
        "population_denominator": 3,
        "tasks_artifact_valid": sum(bool(result.get("artifact_valid"))
                                    for result in task_results),
        "tasks_score_valid": len(score_valid),
        "quality_acceptance_rule": "not_defined",
        "tasks_quality_accepted": None,
        "tasks_failed_before_score": 3 - len(score_valid),
        "task_completion_rate": len(score_valid) / 3,
        "scored_tasks": len(scored),
        "mean_accuracy_over_scored_tasks": (
            sum(result["evaluation"]["mean_accuracy"] for result in scored) / len(scored)
            if scored
            else None
        ),
        "missing_task_accuracy_treatment": "unknown, never converted to zero",
        "failures_stay_in_denominator": True,
        "task_results": task_results,
        "provider_usage": usage,
        "excluded_prior_campaign_attempts": excluded_attempts,
        "physical_calls_including_excluded_attempts": packet_physical_calls,
        "packet_physical_call_ceiling": PACKET_PHYSICAL_CALL_CEILING,
        "packet_physical_call_ceiling_respected": (
            packet_physical_calls <= PACKET_PHYSICAL_CALL_CEILING
        ),
        "packet_provider_usage": {
            "known_input_tokens_subtotal": packet_known_input_tokens,
            "known_output_tokens_subtotal": packet_known_output_tokens,
            "known_total_tokens_subtotal": (
                packet_known_input_tokens + packet_known_output_tokens
            ),
            "calls_with_unknown_token_usage": packet_unknown_token_calls,
            "token_accounting_complete": packet_unknown_token_calls == 0,
            "provider_cost": None,
            "provider_cost_state": "unknown",
        },
        "expected_calls_without_repair": EXPECTED_CALLS_WITHOUT_REPAIR,
        "physical_call_ceiling": TRACK_PHYSICAL_CALL_CEILING,
        "physical_call_ceiling_respected": usage["physical_calls"] <= TRACK_PHYSICAL_CALL_CEILING,
        "all_calls_consumed_intelligence_refs": all(
            row.get("consumed_intelligence_refs")
            for row in (
                json.loads(line)
                for line in (campaign_directory / "model-calls.jsonl").read_text(encoding="utf-8").splitlines()
            )
        )
        if (campaign_directory / "model-calls.jsonl").exists()
        else False,
        "provider_preflight": provider,
        "code_pack_admission": admission,
        "source_snapshot_digest": canonical_json_digest(source_snapshot),
        "environment_lock_digest": canonical_json_digest(lock),
        "provider_cost": None,
        "provider_cost_state": "unknown",
    }
    active.update(status="complete", completed_at=overall["completed_at"])
    write_json(campaign_directory / "campaign-result.json", overall)
    write_json(campaign_directory / "campaign-state.json", active)
    write_json(
        HERE / "verified-result.json",
        {
            "record_type": "openml_cc18_verified_result_pointer/v2",
            "campaign_id": campaign_id,
            "campaign_result": str(
                (campaign_directory / "campaign-result.json").relative_to(REPOSITORY_ROOT)
            ),
            "population_denominator": 3,
            "tasks_artifact_valid": sum(bool(result.get("artifact_valid"))
                                        for result in task_results),
            "tasks_score_valid": len(score_valid),
            "quality_acceptance_rule": "not_defined",
            "tasks_quality_accepted": None,
            "physical_calls": usage["physical_calls"],
            "physical_calls_including_excluded_attempts": overall[
                "physical_calls_including_excluded_attempts"
            ],
            "provider": PROVIDER,
            "model": MODEL,
            "maximum_output_tokens_each_call": MAXIMUM_OUTPUT_TOKENS,
            "provider_cost_state": "unknown",
            "completed_at": overall["completed_at"],
        },
    )
    return overall


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--campaign-id", default="")
    parser.add_argument("--output-root", default=str(HERE / "artifacts"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = execute_campaign(args)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    if args.prepare_only:
        return 0
    return 0 if result.get("tasks_score_valid") == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
