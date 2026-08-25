"""Standalone OpenML-CC18 runtime operations used by the full benchmark.

The benchmark keeps these operations outside the installable Loop Engine
package. Each operation has a concrete callable, a typed Python boundary, and
an entry in the local Code Intelligence pack.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.io import arff
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits


RUNTIME_VERSION = "1.0.0"
RANDOM_FOREST_SEED = 20260825


@dataclass(frozen=True)
class OfficialFold:
    """One official OpenML train/test partition."""

    repeat: int
    fold: int
    train_row_ids: tuple[int, ...]
    test_row_ids: tuple[int, ...]


@dataclass
class OpenMLTaskBundle:
    """Frozen task inputs accepted by the Canvas fold executor."""

    task_spec: dict[str, Any]
    features: pd.DataFrame
    target: pd.Series
    folds: tuple[OfficialFold, ...]
    source_checks: dict[str, Any]
    schema: dict[str, Any]


@dataclass(frozen=True)
class FoldPrediction:
    """Predictions for one official fold, before evaluator scoring."""

    repeat: int
    fold: int
    test_row_ids: tuple[int, ...]
    y_true: tuple[Any, ...]
    y_pred: tuple[Any, ...]
    fit_seconds: float
    predict_seconds: float


@dataclass
class FoldPredictionArtifact:
    """All predictions emitted by one compiled Solution Canvas."""

    record_type: str
    task_id: int
    algorithm: str
    folds: tuple[FoldPrediction, ...]
    executor_version: str


def _hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source_artifact(
    path: str | Path,
    *,
    expected_sha256: str,
    expected_bytes: int,
    expected_md5: str = "",
) -> dict[str, Any]:
    """Verify one downloaded official artifact against the frozen contract."""

    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(target)
    observed_bytes = target.stat().st_size
    observed_sha256 = _hash_file(target, "sha256")
    observed_md5 = _hash_file(target, "md5") if expected_md5 else ""
    violations = []
    if observed_bytes != int(expected_bytes):
        violations.append(
            f"bytes {observed_bytes} != expected {int(expected_bytes)}"
        )
    if observed_sha256 != expected_sha256:
        violations.append(
            f"sha256 {observed_sha256} != expected {expected_sha256}"
        )
    if expected_md5 and observed_md5 != expected_md5:
        violations.append(f"md5 {observed_md5} != expected {expected_md5}")
    if violations:
        raise ValueError(f"artifact verification failed for {target}: " + "; ".join(violations))
    return {
        "record_type": "openml_source_check/v1",
        "path": str(target),
        "bytes": observed_bytes,
        "sha256": observed_sha256,
        "md5": observed_md5 or None,
        "verified": True,
    }


def _decode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="strict")
    if isinstance(value, np.generic):
        return value.item()
    return value


def load_arff_frame(path: str | Path) -> pd.DataFrame:
    """Load an official OpenML ARFF file without changing row order."""

    rows, _metadata = arff.loadarff(str(path))
    frame = pd.DataFrame(rows)
    for column in frame.columns:
        if frame[column].dtype == object:
            frame[column] = frame[column].map(_decode_value)
    return frame


def load_official_splits(
    path: str | Path,
    *,
    number_of_rows: int,
    expected_repeats: int = 1,
    expected_folds: int = 10,
) -> tuple[OfficialFold, ...]:
    """Load and validate the exact official OpenML task split file."""

    frame = load_arff_frame(path)
    required = {"type", "rowid", "repeat", "fold"}
    if set(frame.columns) != required:
        raise ValueError(
            f"split columns {tuple(frame.columns)} do not equal {tuple(sorted(required))}"
        )
    for column in ("rowid", "repeat", "fold"):
        values = frame[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or not np.equal(values, np.floor(values)).all():
            raise ValueError(f"split column {column} must contain finite integers")
        frame[column] = values.astype(int)
    if set(frame["type"]) != {"TRAIN", "TEST"}:
        raise ValueError("split type must contain exactly TRAIN and TEST")
    repeats = sorted(int(value) for value in frame["repeat"].unique())
    folds = sorted(int(value) for value in frame["fold"].unique())
    if repeats != list(range(expected_repeats)):
        raise ValueError(f"split repeats {repeats} do not match {expected_repeats}")
    if folds != list(range(expected_folds)):
        raise ValueError(f"split folds {folds} do not match {expected_folds}")

    expected_rows = set(range(number_of_rows))
    output: list[OfficialFold] = []
    all_test_counts = {row_id: 0 for row_id in expected_rows}
    for repeat in repeats:
        for fold in folds:
            selected = frame[(frame["repeat"] == repeat) & (frame["fold"] == fold)]
            train_ids = tuple(int(value) for value in selected[selected["type"] == "TRAIN"]["rowid"])
            test_ids = tuple(int(value) for value in selected[selected["type"] == "TEST"]["rowid"])
            train_set, test_set = set(train_ids), set(test_ids)
            if len(train_ids) != len(train_set) or len(test_ids) != len(test_set):
                raise ValueError(f"repeat {repeat} fold {fold} has duplicate row IDs")
            if train_set & test_set:
                raise ValueError(f"repeat {repeat} fold {fold} overlaps train and test")
            if train_set | test_set != expected_rows:
                raise ValueError(f"repeat {repeat} fold {fold} does not partition all rows")
            for row_id in test_ids:
                all_test_counts[row_id] += 1
            output.append(OfficialFold(repeat, fold, train_ids, test_ids))
    if set(all_test_counts.values()) != {expected_repeats}:
        raise ValueError("each row must occur in exactly one test fold per repeat")
    return tuple(output)


def load_task_bundle(
    task_spec: Mapping[str, Any],
    *,
    dataset_path: str | Path,
    split_path: str | Path,
) -> OpenMLTaskBundle:
    """Load one verified dataset and its complete official fold geometry."""

    dataset_check = verify_source_artifact(
        dataset_path,
        expected_sha256=str(task_spec["dataset_sha256"]),
        expected_bytes=int(task_spec["dataset_bytes"]),
        expected_md5=str(task_spec["dataset_md5"]),
    )
    split_check = verify_source_artifact(
        split_path,
        expected_sha256=str(task_spec["split_sha256"]),
        expected_bytes=int(task_spec["split_bytes"]),
    )
    frame = load_arff_frame(dataset_path)
    target_name = str(task_spec["target"])
    if target_name not in frame.columns:
        raise ValueError(f"target {target_name!r} is not in {tuple(frame.columns)}")
    if len(frame) != int(task_spec["rows"]):
        raise ValueError(f"rows {len(frame)} != expected {task_spec['rows']}")
    if len(frame.columns) != int(task_spec["features"]):
        raise ValueError(
            f"ARFF attributes {len(frame.columns)} != expected {task_spec['features']}"
        )
    target = frame[target_name].map(_decode_value)
    if target.isna().any():
        raise ValueError("target contains missing values")
    observed_classes = int(target.nunique(dropna=True))
    if observed_classes != int(task_spec["classes"]):
        raise ValueError(
            f"classes {observed_classes} != expected {task_spec['classes']}"
        )
    features = frame.drop(columns=[target_name])
    official_folds = load_official_splits(
        split_path,
        number_of_rows=len(frame),
        expected_repeats=1,
        expected_folds=10,
    )
    numeric = [str(column) for column in features.select_dtypes(include=[np.number]).columns]
    categorical = [str(column) for column in features.columns if str(column) not in numeric]
    schema = {
        "record_type": "openml_schema/v1",
        "task_id": int(task_spec["task_id"]),
        "data_id": int(task_spec["data_id"]),
        "dataset_name": str(task_spec["name"]),
        "rows": len(frame),
        "input_features": len(features.columns),
        "arff_attributes_including_target": len(frame.columns),
        "numeric_features": numeric,
        "categorical_features": categorical,
        "missing_feature_values": int(features.isna().sum().sum()),
        "target": target_name,
        "classes": observed_classes,
        "folds": len(official_folds),
    }
    return OpenMLTaskBundle(
        task_spec=dict(task_spec),
        features=features,
        target=target,
        folds=official_folds,
        source_checks={"dataset": dataset_check, "split": split_check},
        schema=schema,
    )


def build_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    """Build the fixed one-hot preprocessing boundary for both candidates."""

    numeric = list(features.select_dtypes(include=[np.number]).columns)
    categorical = [column for column in features.columns if column not in numeric]
    transformers = []
    if numeric:
        transformers.append(
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median"))]), numeric)
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )
    if not transformers:
        raise ValueError("a tabular task needs at least one input feature")
    return ColumnTransformer(transformers=transformers, remainder="drop")


def build_logistic_pipeline(features: pd.DataFrame) -> Pipeline:
    """Build the exact fixed logistic candidate from the portfolio contract."""

    return Pipeline(
        [
            ("preprocess", build_preprocessor(features)),
            (
                "classifier",
                LogisticRegression(C=1.0, max_iter=1000, n_jobs=1),
            ),
        ]
    )


def build_random_forest_pipeline(features: pd.DataFrame) -> Pipeline:
    """Build the 200-tree, one-thread, seeded random forest candidate."""

    return Pipeline(
        [
            ("preprocess", build_preprocessor(features)),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=RANDOM_FOREST_SEED,
                    n_jobs=1,
                ),
            ),
        ]
    )


def execute_fold_solution(
    inputs: OpenMLTaskBundle, params: Mapping[str, Any]
) -> FoldPredictionArtifact:
    """Fit and predict every official fold without computing the metric."""

    if not isinstance(inputs, OpenMLTaskBundle):
        raise TypeError("fold executor requires OpenMLTaskBundle")
    algorithm = str(params.get("algorithm", ""))
    builders = {
        "logistic": build_logistic_pipeline,
        "random_forest": build_random_forest_pipeline,
    }
    if algorithm not in builders:
        raise ValueError(f"unknown fixed candidate {algorithm!r}")
    predictions: list[FoldPrediction] = []
    for official_fold in inputs.folds:
        train_ids = list(official_fold.train_row_ids)
        test_ids = list(official_fold.test_row_ids)
        pipeline = builders[algorithm](inputs.features)
        with threadpool_limits(limits=1):
            started = time.monotonic()
            pipeline.fit(inputs.features.iloc[train_ids], inputs.target.iloc[train_ids])
            fit_seconds = time.monotonic() - started
            started = time.monotonic()
            predicted = pipeline.predict(inputs.features.iloc[test_ids])
            predict_seconds = time.monotonic() - started
        predictions.append(
            FoldPrediction(
                repeat=official_fold.repeat,
                fold=official_fold.fold,
                test_row_ids=tuple(test_ids),
                y_true=tuple(_decode_value(value) for value in inputs.target.iloc[test_ids]),
                y_pred=tuple(_decode_value(value) for value in predicted),
                fit_seconds=round(fit_seconds, 6),
                predict_seconds=round(predict_seconds, 6),
            )
        )
    return FoldPredictionArtifact(
        record_type="openml_fold_predictions/v1",
        task_id=int(inputs.task_spec["task_id"]),
        algorithm=algorithm,
        folds=tuple(predictions),
        executor_version=RUNTIME_VERSION,
    )


def evaluate_accuracy(
    artifact: FoldPredictionArtifact, bundle: OpenMLTaskBundle
) -> dict[str, Any]:
    """Independently validate predictions and compute official-fold accuracy."""

    if not isinstance(artifact, FoldPredictionArtifact):
        raise TypeError("accuracy evaluator requires FoldPredictionArtifact")
    if artifact.task_id != int(bundle.task_spec["task_id"]):
        raise ValueError("prediction task ID does not match evaluator task")
    expected = {(fold.repeat, fold.fold): fold for fold in bundle.folds}
    observed = {(fold.repeat, fold.fold): fold for fold in artifact.folds}
    if set(observed) != set(expected):
        raise ValueError(
            f"prediction folds {sorted(observed)} do not match official folds {sorted(expected)}"
        )
    rows = []
    for key in sorted(expected):
        official = expected[key]
        predicted = observed[key]
        if predicted.test_row_ids != official.test_row_ids:
            raise ValueError(f"fold {key} prediction row order differs from official split")
        if len(predicted.y_true) != len(predicted.y_pred):
            raise ValueError(f"fold {key} true and predicted lengths differ")
        expected_true = tuple(
            _decode_value(value) for value in bundle.target.iloc[list(official.test_row_ids)]
        )
        if predicted.y_true != expected_true:
            raise ValueError(f"fold {key} y_true differs from frozen dataset")
        score = float(accuracy_score(predicted.y_true, predicted.y_pred))
        rows.append(
            {
                "repeat": key[0],
                "fold": key[1],
                "test_rows": len(predicted.test_row_ids),
                "accuracy": score,
            }
        )
    mean_accuracy = float(np.mean([row["accuracy"] for row in rows]))
    return {
        "record_type": "openml_accuracy_evaluation/v2",
        "task_id": artifact.task_id,
        "metric": "predictive_accuracy",
        "direction": "higher_is_better",
        "fold_aggregation": "mean_of_10_official_fold_accuracies",
        "folds": rows,
        "mean_accuracy": mean_accuracy,
        "artifact_valid": True,
        "score_valid": True,
        "quality_acceptance_rule": "not_defined",
        "quality_accepted": None,
        "evaluator": "sklearn.metrics.accuracy_score",
        "independent_from_model_selection": True,
    }


def compile_tabular_canvas(spec: Any, registry: Mapping[str, Any]) -> dict[str, Any]:
    """Compile and render one typed Loop Engine Solution Canvas."""

    from loop_engine.code_nodes.solution_compiler import compile_solution, render_canvas

    compiled = compile_solution(spec, dict(registry))
    if compiled["plan"] is None:
        raise ValueError("Solution Canvas did not compile: " + "; ".join(compiled["violations"]))
    return {"compiled": compiled, "canvas": render_canvas(compiled["plan"])}


def run_compiled_canvas(
    plan: Mapping[str, Any],
    registry: Mapping[str, Any],
    inputs: OpenMLTaskBundle,
    *,
    ledger: Any,
    parent: Any,
    trace: list[dict[str, Any]],
) -> FoldPredictionArtifact:
    """Execute the exact compiled plan through Solution component loops."""

    from loop_engine.code_nodes.solution_compiler import _spec_from_dict, compile_solution
    from loop_engine.code_nodes.solution_canvas import run_solution

    if plan.get("record_type") != "solution_plan/v1":
        raise ValueError("Canvas runner requires solution_plan/v1")
    spec = _spec_from_dict(dict(plan["spec"]))
    rebuilt = compile_solution(spec, dict(registry))
    if rebuilt["digest"] != plan.get("digest"):
        raise ValueError("compiled Canvas digest changed before execution")
    output = run_solution(
        spec,
        dict(registry),
        inputs,
        trace=trace,
        ledger=ledger,
        parent=parent,
    )
    if not isinstance(output, FoldPredictionArtifact):
        raise TypeError("compiled Canvas did not emit FoldPredictionArtifact")
    return output


def prediction_artifact_as_dict(artifact: FoldPredictionArtifact) -> dict[str, Any]:
    """Make the typed prediction artifact JSON serializable."""

    return asdict(artifact)


def canonical_json_digest(value: Any) -> str:
    """Return a stable SHA-256 digest for one JSON-compatible value."""

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
