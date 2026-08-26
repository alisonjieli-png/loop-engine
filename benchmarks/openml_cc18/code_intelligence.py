"""Registered Code Intelligence pack for the OpenML-CC18 benchmark."""
from __future__ import annotations

import hashlib
import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from loop_engine.core.store_serve import StoreRecord


PACK_VERSION = "1.0.0"
MODULE = "benchmarks.openml_cc18.openml_runtime"
ADMISSION_REFERENCE = (
    "benchmarks/openml_cc18/run.py:admit_code_intelligence_pack"
)


@dataclass(frozen=True)
class CodeAssetDefinition:
    record_id: str
    title: str
    function: str
    input_roles: tuple[str, ...]
    output_roles: tuple[str, ...]
    effects: tuple[str, ...]
    tags: tuple[str, ...]


ASSETS = (
    CodeAssetDefinition(
        "code.openml.verify_source_artifact",
        "Verify OpenML source bytes and hashes",
        "verify_source_artifact",
        ("artifact_path", "frozen_hash_contract"),
        ("verified_source_check",),
        ("reads_fs",),
        ("openml", "hash", "source", "verify"),
    ),
    CodeAssetDefinition(
        "code.openml.load_arff_frame",
        "Load an official OpenML ARFF without row reordering",
        "load_arff_frame",
        ("verified_arff_path",),
        ("ordered_tabular_frame",),
        ("reads_fs",),
        ("openml", "arff", "load", "data"),
    ),
    CodeAssetDefinition(
        "code.openml.load_official_splits",
        "Load and validate every official OpenML fold",
        "load_official_splits",
        ("verified_split_path", "row_count", "split_contract"),
        ("official_fold_sequence",),
        ("reads_fs",),
        ("openml", "official", "split", "fold"),
    ),
    CodeAssetDefinition(
        "code.openml.load_task_bundle",
        "Build the typed OpenML task input bundle",
        "load_task_bundle",
        ("task_contract", "verified_dataset", "verified_splits"),
        ("openml_task_bundle",),
        ("reads_fs",),
        ("openml", "typed", "task", "bundle"),
    ),
    CodeAssetDefinition(
        "code.openml.build_preprocessor",
        "Build fixed unknown-safe one-hot preprocessing",
        "build_preprocessor",
        ("tabular_feature_frame",),
        ("column_transformer",),
        ("pure",),
        ("preprocess", "one_hot", "unknown", "impute"),
    ),
    CodeAssetDefinition(
        "code.openml.logistic_pipeline",
        "Build C 1.0 logistic pipeline with max_iter 1000",
        "build_logistic_pipeline",
        ("tabular_feature_frame",),
        ("fixed_logistic_pipeline",),
        ("pure",),
        ("logistic", "classification", "one_cpu", "candidate"),
    ),
    CodeAssetDefinition(
        "code.openml.seeded_random_forest",
        "Build 200-tree seeded random forest with one CPU thread",
        "build_random_forest_pipeline",
        ("tabular_feature_frame",),
        ("fixed_random_forest_pipeline",),
        ("pure",),
        ("random_forest", "classification", "seeded", "candidate"),
    ),
    CodeAssetDefinition(
        "code.openml.execute_official_folds",
        "Fit and predict every official fold without grading",
        "execute_fold_solution",
        ("openml_task_bundle", "fixed_candidate_configuration"),
        ("openml_fold_predictions",),
        ("pure",),
        ("execute", "all_folds", "prediction", "canvas"),
    ),
    CodeAssetDefinition(
        "code.openml.accuracy_evaluator",
        "Independently validate predictions and compute fold accuracy",
        "evaluate_accuracy",
        ("openml_fold_predictions", "openml_task_bundle"),
        ("openml_accuracy_evaluation",),
        ("pure",),
        ("accuracy", "independent", "evaluate", "verify"),
    ),
    CodeAssetDefinition(
        "code.openml.canvas_compiler",
        "Compile and render a typed Solution Canvas",
        "compile_tabular_canvas",
        ("solution_spec", "operation_registry"),
        ("compiled_solution_plan", "solution_canvas"),
        ("pure",),
        ("canvas", "compile", "typed", "render"),
    ),
    CodeAssetDefinition(
        "code.openml.canvas_runner",
        "Execute the compiled Canvas through Solution component loops",
        "run_compiled_canvas",
        ("compiled_solution_plan", "openml_task_bundle", "loop_ledger"),
        ("openml_fold_predictions",),
        ("pure",),
        ("canvas", "compiled", "execute", "practitioner_loop"),
    ),
)


def _callable_digest(function: Callable[..., Any]) -> str:
    source = inspect.getsource(function).encode("utf-8")
    return hashlib.sha256(source).hexdigest()


def build_code_records() -> list[StoreRecord]:
    """Build searchable records only for importable real callables."""

    module = importlib.import_module(MODULE)
    records = []
    for asset in ASSETS:
        function = getattr(module, asset.function, None)
        if not callable(function):
            raise RuntimeError(
                f"Code Intelligence asset {asset.record_id} has no callable {MODULE}:{asset.function}"
            )
        entrypoint = f"{MODULE}:{asset.function}"
        records.append(
            StoreRecord(
                record_id=asset.record_id,
                kind="node",
                title=asset.title,
                body={
                    "role": "registered_code_intelligence",
                    "asset_kind": "function",
                    "entrypoint": entrypoint,
                    "callable_sha256": _callable_digest(function),
                    "typed_contract": {
                        "input_roles": list(asset.input_roles),
                        "output_roles": list(asset.output_roles),
                    },
                    "effects": list(asset.effects),
                    "version": PACK_VERSION,
                    "maturity": "registered",
                    "admission_test": ADMISSION_REFERENCE,
                    "facets": {
                        "category": "execute",
                        "subcategory": asset.function,
                        "scope": "benchmark_standalone",
                        "lifecycle": "registered",
                    },
                },
                tags=("openml_cc18", "registered") + asset.tags,
                tier="core",
                source="standalone_openml_cc18_code_pack",
            )
        )
    return records


def materialize_record(record: StoreRecord) -> Callable[..., Any]:
    """Resolve one searched Code reference and recheck its source digest."""

    body = dict(record.body or {})
    if body.get("maturity") != "registered":
        raise RuntimeError(f"Code record {record.record_id} is not registered")
    entrypoint = str(body.get("entrypoint", ""))
    module_name, separator, function_name = entrypoint.partition(":")
    if not separator:
        raise RuntimeError(f"Code record {record.record_id} has no entrypoint")
    function = getattr(importlib.import_module(module_name), function_name, None)
    if not callable(function):
        raise RuntimeError(f"Code record {record.record_id} entrypoint is not callable")
    observed = _callable_digest(function)
    if observed != body.get("callable_sha256"):
        raise RuntimeError(f"Code record {record.record_id} callable digest changed")
    return function


def code_pack_as_dict(records: list[StoreRecord]) -> dict[str, Any]:
    """Return the non-executable, JSON-safe registry view."""

    return {
        "record_type": "openml_code_intelligence_pack/v1",
        "version": PACK_VERSION,
        "admission_reference": ADMISSION_REFERENCE,
        "records": [
            {
                "record_id": record.record_id,
                "title": record.title,
                "entrypoint": record.body["entrypoint"],
                "callable_sha256": record.body["callable_sha256"],
                "typed_contract": record.body["typed_contract"],
                "effects": record.body["effects"],
                "version": record.body["version"],
                "maturity": record.body["maturity"],
                "admission_test": record.body["admission_test"],
            }
            for record in records
        ],
    }


def build_portfolio_code_pack(
    benchmark_id: str, *, candidate: str
):
    """Project the admitted local pack into the core portfolio contract.

    Candidate-specific packs make the alternatives family consume the exact
    logistic or random-forest implementation being reviewed. The complete
    eleven-record pack is admitted and materialized before calls; this narrow
    projection keeps the remaining portfolio families available to Context,
    Previous Run, and User Feedback Intelligence. ``both`` keeps both admitted
    alternatives available to a synthesis or repair spawned_loop.
    """

    from loop_engine.loop.loop_capsule import ExternalPayloadRef
    from loop_engine.core.code_intelligence_assets import (
        CodeAssetSpec,
    )
    from loop_engine import (
        BenchmarkCodePack,
        BenchmarkCodeRegistration,
        LensFamily,
    )

    if candidate not in ("logistic", "random_forest", "both"):
        raise ValueError("candidate must be logistic, random_forest, or both")
    by_function = {asset.function: asset for asset in ASSETS}
    selected = []
    if candidate in ("logistic", "both"):
        selected.append(
            ("build_logistic_pipeline", LensFamily.ALTERNATIVES_ANALOGY)
        )
    if candidate in ("random_forest", "both"):
        selected.append(
            ("build_random_forest_pipeline", LensFamily.ALTERNATIVES_ANALOGY)
        )
    module = importlib.import_module(MODULE)
    registrations = []
    for function_name, family in selected:
        asset = by_function[function_name]
        function = getattr(module, function_name)
        source = inspect.getsource(function).encode("utf-8")
        digest = hashlib.sha256(source).hexdigest()
        body_ref = ExternalPayloadRef(
            f"python://benchmarks/openml_cc18/openml_runtime/{function_name}",
            digest,
            size_bytes=len(source),
            media_type="text/x-python",
        )
        spec = CodeAssetSpec(
            asset_id=asset.record_id,
            name=asset.title,
            description=asset.title,
            asset_kind="function",
            source_kind="local_path",
            body_ref=body_ref,
            entrypoints=(function_name,),
            modes=("deterministic",),
            input_contract="|".join(asset.input_roles),
            output_contract="|".join(asset.output_roles),
            effects=asset.effects,
            dependencies=("loop-engine",),
            file_count=1,
            line_count=source.count(b"\n") + 1,
            load_strategy="import",
            template_id="pure_function",
            version=PACK_VERSION,
            license="MIT",
            lifecycle="registered",
            admission_ref=ADMISSION_REFERENCE,
            metadata={"benchmark_operation": function_name},
        )
        registrations.append(
            BenchmarkCodeRegistration(
                spec=spec,
                benchmark_ids=(benchmark_id,),
                lens_families=(family,),
                entrypoints=((function_name, function),),
            )
        )
    return BenchmarkCodePack(
        f"openml-cc18-{candidate}-portfolio-code-pack",
        tuple(registrations),
    )
