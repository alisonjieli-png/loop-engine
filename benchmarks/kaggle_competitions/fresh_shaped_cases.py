"""Deterministic Kaggle-shaped cases with hidden independent scoring.

This benchmark helper creates three generated task sources. They are not
Kaggle competitions and do not establish performance on an external task
population. The materializer writes only after exact local authority is
supplied. It performs no network request, provider call, model call, package
installation, or submission.

The generated source for each case contains only ``task.txt``, ``train.csv``,
``test.csv``, and ``sample_submission.csv``. Hidden labels and manifests live
in separate sibling trees and must never be supplied as solver source or
workspace. The scorer reads the submitted artifact rather than a run's own
conclusion and implements each metric independently from the solver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import random
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

NOVELTY_SCOPE = "GENERATED_KAGGLE_SHAPED"
GENERATOR_VERSION = "1.0.0"
CASE_MANIFEST_TYPE = "fresh_kaggle_shaped_case_manifest/v1"
CAMPAIGN_MANIFEST_TYPE = "fresh_kaggle_shaped_campaign_manifest/v1"
SCORE_RESULT_TYPE = "fresh_kaggle_shaped_score/v1"
COMMON_TASK = (
    "Build and verify a reproducible baseline for the supplied "
    "competition-shaped directory. Infer file roles, identifier, target, "
    "task type, validation method, and submission contract from the files. "
    "Use only the supplied training data. Write submission.csv and "
    "metrics.json. Do not submit externally. "
)
_HEX = frozenset("0123456789abcdef")


class FreshShapedCaseError(ValueError):
    """A generated case, path, manifest, or submission failed closed."""


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise FreshShapedCaseError("record must be finite strict JSON") from exc


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: object) -> str:
    return _digest_bytes(_canonical(value).encode("utf-8"))


def _require_digest(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in _HEX for character in value):
        raise FreshShapedCaseError(f"{name} must be lowercase SHA-256")


def _text(value: object, name: str) -> str:
    if (not isinstance(value, str) or not value.strip()
            or value != value.strip() or "\n" in value or "\r" in value):
        raise FreshShapedCaseError(f"{name} must be trimmed non-empty text")
    return value


@dataclass(frozen=True)
class FreshCaseSpec:
    """Passive versioned definition and predeclared acceptance policy."""

    case_id: str
    seed: int
    prediction_kind: str
    metric: str
    metric_direction: str
    target: str
    feature_columns: tuple[str, ...]
    categorical_columns: tuple[str, ...]
    target_position_in_train: int
    train_rows: int = 1_000
    test_rows: int = 250
    labels: tuple[str, ...] = ()
    minimum_metric: float | None = None
    minimum_improvement_over_constant: float | None = None
    maximum_ratio_to_constant: float | None = None
    version: str = GENERATOR_VERSION

    def __post_init__(self) -> None:
        for name in ("case_id", "prediction_kind", "metric",
                     "metric_direction", "target", "version"):
            _text(getattr(self, name), name)
        if self.prediction_kind not in ("binary_probability", "regression",
                                        "multiclass_label"):
            raise FreshShapedCaseError("prediction kind is not registered")
        if self.metric_direction not in ("maximize", "minimize"):
            raise FreshShapedCaseError("metric direction is not registered")
        if (isinstance(self.seed, bool) or not isinstance(self.seed, int)
                or self.seed < 0):
            raise FreshShapedCaseError("seed must be a non-negative integer")
        if not 800 <= self.train_rows <= 1_200:
            raise FreshShapedCaseError("train rows must be between 800 and 1200")
        if not 200 <= self.test_rows <= 300:
            raise FreshShapedCaseError("test rows must be between 200 and 300")
        features = tuple(self.feature_columns)
        categoricals = tuple(self.categorical_columns)
        if (not 8 <= len(features) <= 12
                or len(features) != len(set(features))
                or any(not item.strip() for item in features)
                or not set(categoricals) < set(features)):
            raise FreshShapedCaseError(
                "features need 8-12 unique columns and mixed data types")
        if not 1 <= self.target_position_in_train <= len(features) + 1:
            raise FreshShapedCaseError("target position is outside train header")
        if self.prediction_kind == "multiclass_label":
            if len(self.labels) != 3 or len(set(self.labels)) != 3:
                raise FreshShapedCaseError("multiclass case needs three labels")
        elif self.labels:
            raise FreshShapedCaseError("only the text-label case declares labels")
        for name in ("minimum_metric", "minimum_improvement_over_constant",
                     "maximum_ratio_to_constant"):
            value = getattr(self, name)
            if (value is not None and (
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(float(value)) or value < 0)):
                raise FreshShapedCaseError(f"{name} must be finite and non-negative")
        if self.metric_direction == "maximize" and (
                self.minimum_metric is None
                or self.minimum_improvement_over_constant is None
                or self.maximum_ratio_to_constant is not None):
            raise FreshShapedCaseError(
                "maximize cases need absolute and baseline-improvement floors")
        if self.metric_direction == "minimize" and (
                self.maximum_ratio_to_constant is None
                or self.minimum_metric is not None
                or self.minimum_improvement_over_constant is not None):
            raise FreshShapedCaseError(
                "minimize cases need a constant-baseline ratio ceiling")

    @property
    def numeric_columns(self) -> tuple[str, ...]:
        return tuple(item for item in self.feature_columns
                     if item not in self.categorical_columns)

    def to_dict(self) -> dict:
        return {
            "record_type": "fresh_kaggle_shaped_case_spec/v1",
            "case_id": self.case_id,
            "version": self.version,
            "seed": self.seed,
            "prediction_kind": self.prediction_kind,
            "metric": self.metric,
            "metric_direction": self.metric_direction,
            "target": self.target,
            "feature_columns": list(self.feature_columns),
            "numeric_columns": list(self.numeric_columns),
            "categorical_columns": list(self.categorical_columns),
            "target_position_in_train": self.target_position_in_train,
            "train_rows": self.train_rows,
            "test_rows": self.test_rows,
            "labels": list(self.labels),
            "acceptance": {
                "minimum_metric": self.minimum_metric,
                "minimum_improvement_over_constant":
                    self.minimum_improvement_over_constant,
                "maximum_ratio_to_constant": self.maximum_ratio_to_constant,
                "declared_before_generation": True,
            },
            "novelty_scope": NOVELTY_SCOPE,
            "actual_kaggle_competition": False,
        }

    @property
    def spec_digest(self) -> str:
        return _digest(self.to_dict())


CASE_SPECS = (
    FreshCaseSpec(
        "fresh-shaped-case-a-v1", 910_001, "binary_probability",
        "roc_auc", "maximize", "outcome_probability",
        ("signal_a", "signal_b", "signal_c", "signal_d", "signal_e",
         "signal_f", "segment", "region", "channel", "tier"),
        ("segment", "region", "channel", "tier"), 11,
        minimum_metric=0.78, minimum_improvement_over_constant=0.20),
    FreshCaseSpec(
        "fresh-shaped-case-b-v1", 910_002, "regression",
        "rmse", "minimize", "continuous_target",
        ("measure_a", "measure_b", "measure_c", "measure_d", "measure_e",
         "measure_f", "measure_g", "group", "site", "season"),
        ("group", "site", "season"), 4,
        maximum_ratio_to_constant=0.65),
    FreshCaseSpec(
        "fresh-shaped-case-c-v1", 910_003, "multiclass_label",
        "accuracy", "maximize", "class_label",
        ("reading_a", "reading_b", "reading_c", "reading_d", "reading_e",
         "reading_f", "cohort", "source", "band", "zone"),
        ("cohort", "source", "band", "zone"), 6,
        labels=("amber", "cobalt", "jade"),
        minimum_metric=0.72, minimum_improvement_over_constant=0.30),
)
_SPEC_BY_ID = {item.case_id: item for item in CASE_SPECS}


@dataclass(frozen=True)
class ArtifactRecord:
    """One exact generated file reference relative to the campaign root."""

    relative_path: str
    byte_count: int
    sha256: str
    visibility: str

    def __post_init__(self) -> None:
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts or not self.relative_path:
            raise FreshShapedCaseError("artifact path must be confined and relative")
        if (isinstance(self.byte_count, bool) or not isinstance(self.byte_count, int)
                or self.byte_count < 1):
            raise FreshShapedCaseError("artifact byte count must be positive")
        _require_digest(self.sha256, "artifact digest")
        if self.visibility not in ("solver_input", "evaluator_only"):
            raise FreshShapedCaseError("artifact visibility is invalid")

    def to_dict(self) -> dict:
        return {
            "relative_path": self.relative_path,
            "byte_count": self.byte_count,
            "sha256": self.sha256,
            "visibility": self.visibility,
        }


@dataclass(frozen=True)
class CaseManifest:
    """Passive source, evaluator, and acceptance identity for one case."""

    spec: FreshCaseSpec
    generator_source_digest: str
    task_text_digest: str
    source_artifacts: tuple[ArtifactRecord, ...]
    evaluator_artifact: ArtifactRecord
    constant_baseline_prediction: str
    record_type: str = CASE_MANIFEST_TYPE

    def __post_init__(self) -> None:
        if self.record_type != CASE_MANIFEST_TYPE:
            raise FreshShapedCaseError("case manifest version is unsupported")
        if not isinstance(self.spec, FreshCaseSpec):
            raise FreshShapedCaseError("case manifest needs a typed specification")
        _require_digest(self.generator_source_digest, "generator source digest")
        _require_digest(self.task_text_digest, "task text digest")
        artifacts = tuple(self.source_artifacts)
        expected = {
            f"sources/{self.spec.case_id}/{name}"
            for name in ("task.txt", "train.csv", "test.csv",
                         "sample_submission.csv")}
        if (any(not isinstance(item, ArtifactRecord) for item in artifacts)
                or {item.relative_path for item in artifacts} != expected
                or any(item.visibility != "solver_input" for item in artifacts)):
            raise FreshShapedCaseError(
                "manifest needs exactly four solver-visible source artifacts")
        if (not isinstance(self.evaluator_artifact, ArtifactRecord)
                or self.evaluator_artifact.visibility != "evaluator_only"
                or self.evaluator_artifact.relative_path
                != f"evaluator/{self.spec.case_id}/labels.csv"):
            raise FreshShapedCaseError("hidden labels have the wrong boundary")
        _text(self.constant_baseline_prediction,
              "constant_baseline_prediction")
        object.__setattr__(self, "source_artifacts", artifacts)

    def to_dict(self, *, include_digest: bool = True) -> dict:
        value = {
            "record_type": self.record_type,
            "spec": self.spec.to_dict(),
            "spec_digest": self.spec.spec_digest,
            "generator_source_digest": self.generator_source_digest,
            "task_text_digest": self.task_text_digest,
            "source_artifacts": [item.to_dict() for item in self.source_artifacts],
            "evaluator_artifact": self.evaluator_artifact.to_dict(),
            "constant_baseline_prediction": self.constant_baseline_prediction,
            "solver_source_relative_path": f"sources/{self.spec.case_id}",
            "evaluator_relative_path": f"evaluator/{self.spec.case_id}",
            "boundaries": {
                "hidden_path_outside_declared_solver_source": True,
                "generator_source_supplied_to_solver": False,
                "manifest_supplied_to_solver": False,
                "runtime_mount_and_context_isolation_verified": False,
            },
            "network_calls": 0,
            "provider_calls": 0,
            "submissions": 0,
        }
        if include_digest:
            value["content_digest"] = self.content_digest
        return value

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict(include_digest=False))


@dataclass(frozen=True)
class ScoreResult:
    """Independent reading of one submitted artifact and hidden labels."""

    case_id: str
    campaign_manifest_digest: str
    case_manifest_digest: str
    submission_digest: str
    metric: str
    metric_direction: str
    observed_metric: float
    constant_baseline_metric: float
    threshold_passed: bool
    checks: tuple[tuple[str, bool], ...]

    def to_dict(self) -> dict:
        return {
            "record_type": SCORE_RESULT_TYPE,
            "case_id": self.case_id,
            "campaign_manifest_digest": self.campaign_manifest_digest,
            "case_manifest_digest": self.case_manifest_digest,
            "submission_digest": self.submission_digest,
            "metric": self.metric,
            "metric_direction": self.metric_direction,
            "observed_metric": self.observed_metric,
            "constant_baseline_metric": self.constant_baseline_metric,
            "threshold_passed": self.threshold_passed,
            "artifact_valid": all(passed for _name, passed in self.checks),
            "accepted": self.threshold_passed
            and all(passed for _name, passed in self.checks),
            "acceptance_scope": "artifact_and_hidden_evaluator_only",
            "checks": [
                {"check": name, "passed": passed}
                for name, passed in self.checks],
            "novelty_scope": NOVELTY_SCOPE,
            "actual_kaggle_competition": False,
            "causal_assistance_evidence": False,
            "cross_family_generalization_claimed": False,
            "expected_digest_match": True,
            "prelaunch_freeze_verified_by_this_scorer": False,
            "runtime_isolation_verified": False,
            "runtime_isolation_verification_owner": "external_driver",
            "grants_authority": False,
        }


def _csv_bytes(header: list[str], rows: list[list[object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _number(value: float) -> str:
    return format(float(value), ".12g")


def _task_text(spec: FreshCaseSpec) -> str:
    if spec.prediction_kind == "binary_probability":
        contract = (
            "The evaluation metric is ROC AUC and higher is better. The "
            "submission value must be a finite probability in [0,1] for "
            "label 1. Acceptance requires AUC at least 0.78 and at least "
            "0.20 above the constant-prediction baseline."
        )
    elif spec.prediction_kind == "regression":
        contract = (
            "The evaluation metric is root mean squared error (RMSE) and "
            "lower is better. The submission value must be one finite "
            "continuous prediction per test identifier. Acceptance requires "
            "RMSE no more than 0.65 times the constant training-mean baseline."
        )
    else:
        contract = (
            "The evaluation metric is accuracy and higher is better. The "
            "submission value must be one of the exact class labels present "
            "in training: amber, cobalt, or jade. Acceptance requires "
            "accuracy at least 0.72 and at least 0.30 above the constant "
            "training-majority baseline."
        )
    return COMMON_TASK + contract


def _with_missing(values: list[str], spec: FreshCaseSpec,
                  row_index: int) -> list[str]:
    output = list(values)
    for index, _name in enumerate(spec.feature_columns):
        modulus = 29 if index % 2 == 0 else 37
        if (row_index * 17 + index * 31 + spec.seed) % modulus == 0:
            output[index] = ""
    return output


def _binary_row(rng: random.Random, index: int) -> tuple[list[str], str]:
    numeric = [rng.uniform(-2.5, 2.5) for _ in range(6)]
    segment = rng.choice(("north", "south", "central"))
    region = rng.choice(("rural", "urban", "mixed"))
    channel = rng.choice(("direct", "partner", "organic"))
    tier = rng.choice(("basic", "plus", "premium"))
    category_effect = {
        "north": 0.8, "south": -0.5, "central": 0.1,
        "rural": -0.4, "urban": 0.5, "mixed": 0.0,
        "direct": 0.4, "partner": -0.2, "organic": 0.1,
        "basic": -0.5, "plus": 0.1, "premium": 0.7,
    }
    logit = (
        1.5 * numeric[0] - 1.2 * numeric[1]
        + 0.9 * numeric[2] * numeric[3]
        + 0.8 * math.sin(1.7 * numeric[4]) + 0.35 * numeric[5]
        + sum(category_effect[item]
              for item in (segment, region, channel, tier))
        + rng.uniform(-0.35, 0.35)
    )
    probability = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, logit))))
    label = "1" if rng.random() < probability else "0"
    values = [_number(item) for item in numeric] \
        + [segment, region, channel, tier]
    return _with_missing(values, _SPEC_BY_ID[
        "fresh-shaped-case-a-v1"], index), label


def _regression_row(rng: random.Random, index: int) -> tuple[list[str], str]:
    numeric = [rng.uniform(-3.0, 3.0) for _ in range(7)]
    group = rng.choice(("g0", "g1", "g2", "g3"))
    site = rng.choice(("east", "west", "remote"))
    season = rng.choice(("winter", "spring", "summer", "fall"))
    effects = {
        "g0": -2.0, "g1": -0.5, "g2": 1.0, "g3": 2.5,
        "east": 0.8, "west": -0.7, "remote": 1.7,
        "winter": -1.0, "spring": 0.3, "summer": 1.2, "fall": -0.2,
    }
    target = (
        4.0 * math.sin(numeric[0]) + 1.4 * numeric[1] ** 2
        - 1.8 * numeric[2] * numeric[3] + 0.7 * numeric[4]
        + 0.5 * numeric[5] ** 3 / 9.0 - 0.4 * numeric[6]
        + effects[group] + effects[site] + effects[season]
        + rng.uniform(-0.45, 0.45)
    )
    values = [_number(item) for item in numeric] + [group, site, season]
    return _with_missing(values, _SPEC_BY_ID[
        "fresh-shaped-case-b-v1"], index), _number(target)


def _multiclass_row(rng: random.Random, index: int) -> tuple[list[str], str]:
    numeric = [rng.uniform(-2.5, 2.5) for _ in range(6)]
    cohort = rng.choice(("c0", "c1", "c2"))
    source = rng.choice(("internal", "external", "hybrid"))
    band = rng.choice(("low", "mid", "high"))
    zone = rng.choice(("z0", "z1", "z2"))
    categories = (cohort, source, band, zone)
    boosts = {
        "amber": {"c0", "internal", "low", "z0"},
        "cobalt": {"c1", "external", "mid", "z1"},
        "jade": {"c2", "hybrid", "high", "z2"},
    }
    scores = {
        "amber": 1.3 * numeric[0] - 0.7 * numeric[1]
        + 0.5 * numeric[4] ** 2,
        "cobalt": -0.9 * numeric[0] + 1.4 * numeric[2]
        + 0.8 * math.sin(numeric[5]),
        "jade": 0.8 * numeric[1] - 1.1 * numeric[2]
        + 1.0 * numeric[3],
    }
    for label in scores:
        scores[label] += 0.8 * sum(
            item in boosts[label] for item in categories)
        scores[label] += rng.uniform(-0.2, 0.2)
    label = max(sorted(scores), key=lambda item: scores[item])
    values = [_number(item) for item in numeric] \
        + [cohort, source, band, zone]
    return _with_missing(values, _SPEC_BY_ID[
        "fresh-shaped-case-c-v1"], index), label


_ROW_BUILDERS = {
    "binary_probability": _binary_row,
    "regression": _regression_row,
    "multiclass_label": _multiclass_row,
}


def _case_bodies(spec: FreshCaseSpec) -> tuple[dict[str, bytes], bytes, str]:
    rng = random.Random(spec.seed)
    rows = [_ROW_BUILDERS[spec.prediction_kind](rng, index)
            for index in range(spec.train_rows + spec.test_rows)]
    training = rows[:spec.train_rows]
    testing = rows[spec.train_rows:]
    training_labels = [label for _values, label in training]
    if spec.prediction_kind == "binary_probability":
        constant = _number(sum(map(int, training_labels)) / len(training_labels))
    elif spec.prediction_kind == "regression":
        constant = _number(math.fsum(map(float, training_labels))
                           / len(training_labels))
    else:
        counts = Counter(training_labels)
        constant = min(spec.labels, key=lambda item: (-counts[item], item))
    feature_header = ["id", *spec.feature_columns]
    train_header = list(feature_header)
    train_header.insert(spec.target_position_in_train, spec.target)
    train_rows: list[list[object]] = []
    test_rows: list[list[object]] = []
    sample_rows: list[list[object]] = []
    hidden_rows: list[list[object]] = []
    for index, (values, label) in enumerate(training):
        row: list[object] = [f"train_{index:06d}", *values]
        row.insert(spec.target_position_in_train, label)
        train_rows.append(row)
    for offset, (values, label) in enumerate(testing):
        identifier = f"test_{offset:06d}"
        test_rows.append([identifier, *values])
        sample_rows.append([identifier, constant])
        hidden_rows.append([identifier, label, constant])
    visible = {
        "task.txt": (_task_text(spec) + "\n").encode("utf-8"),
        "train.csv": _csv_bytes(train_header, train_rows),
        "test.csv": _csv_bytes(feature_header, test_rows),
        "sample_submission.csv": _csv_bytes(
            ["id", spec.target], sample_rows),
    }
    hidden = _csv_bytes(
        ["id", spec.target, "constant_prediction"], hidden_rows)
    return visible, hidden, constant


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(str(path.expanduser())))


def _reject_symlink_components(path: Path, *, allow_missing_leaf: bool) -> None:
    """Refuse a symlink at any existing component without following it."""
    absolute = _absolute_without_resolving(path)
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for index, part in enumerate(parts):
        current /= part
        if current.is_symlink():
            raise FreshShapedCaseError("path contains a symlink component")
        if not current.exists():
            if allow_missing_leaf:
                return
            raise FreshShapedCaseError("required path component is unavailable")
        if index < len(parts) - 1 and not current.is_dir():
            raise FreshShapedCaseError("path ancestor is not a directory")


def _contains(parent: Path, child: Path) -> bool:
    return child == parent or parent in child.parents


def _safe_campaign_paths(workspace_root: str, campaign_root: str) \
        -> tuple[Path, Path]:
    workspace_input = Path(workspace_root).expanduser()
    _reject_symlink_components(workspace_input, allow_missing_leaf=False)
    if (not workspace_input.exists() or not workspace_input.is_dir()
            or workspace_input.is_symlink()):
        raise FreshShapedCaseError(
            "workspace root must be an existing non-symlink directory")
    workspace = workspace_input.resolve()
    candidate_input = Path(campaign_root).expanduser()
    _reject_symlink_components(candidate_input.parent, allow_missing_leaf=True)
    if candidate_input.exists() or candidate_input.is_symlink():
        raise FreshShapedCaseError("campaign root already exists")
    candidate = candidate_input.resolve()
    if candidate == workspace or not _contains(workspace, candidate):
        raise FreshShapedCaseError(
            "campaign root must be a new child of workspace root")
    return workspace, candidate


def _artifact(relative_path: str, body: bytes, visibility: str) \
        -> ArtifactRecord:
    return ArtifactRecord(relative_path, len(body), _digest_bytes(body), visibility)


def _write_new(path: Path, body: bytes, *, private: bool = False) -> None:
    if path.exists() or path.is_symlink():
        raise FreshShapedCaseError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as handle:
        handle.write(body)
    os.chmod(path, 0o600 if private else 0o644)


def materialize_cases(
        workspace_root: str, campaign_root: str, *, authorize_writes: bool) \
        -> dict:
    """Create a new isolated campaign tree after exact write authority."""
    if authorize_writes is not True:
        raise PermissionError("materialization needs --authorize-writes")
    _workspace, campaign = _safe_campaign_paths(workspace_root, campaign_root)
    campaign.parent.mkdir(parents=True, exist_ok=True)
    source_digest = _digest_bytes(Path(__file__).read_bytes())
    manifests = []
    with tempfile.TemporaryDirectory(
            prefix=".fresh-shaped-stage-", dir=str(campaign.parent)) as temporary:
        staged = Path(temporary)
        for spec in CASE_SPECS:
            visible, hidden, constant = _case_bodies(spec)
            source_records = []
            for name, body in sorted(visible.items()):
                relative = f"sources/{spec.case_id}/{name}"
                _write_new(staged / relative, body)
                source_records.append(_artifact(relative, body, "solver_input"))
            hidden_relative = f"evaluator/{spec.case_id}/labels.csv"
            _write_new(staged / hidden_relative, hidden, private=True)
            os.chmod((staged / hidden_relative).parent, 0o700)
            hidden_record = _artifact(
                hidden_relative, hidden, "evaluator_only")
            manifest = CaseManifest(
                spec, source_digest, _digest_bytes(
                    (_task_text(spec) + "\n").encode("utf-8")),
                tuple(source_records), hidden_record, constant)
            manifest_relative = f"manifests/{spec.case_id}.json"
            manifest_body = (_canonical(manifest.to_dict()) + "\n").encode("utf-8")
            _write_new(staged / manifest_relative, manifest_body, private=True)
            manifests.append({
                "case_id": spec.case_id,
                "manifest_relative_path": manifest_relative,
                "manifest_digest": manifest.content_digest,
                "manifest_file_sha256": _digest_bytes(manifest_body),
                "source_relative_path": f"sources/{spec.case_id}",
            })
        campaign_record = {
            "record_type": CAMPAIGN_MANIFEST_TYPE,
            "generator_version": GENERATOR_VERSION,
            "generator_source_digest": source_digest,
            "novelty_scope": NOVELTY_SCOPE,
            "actual_kaggle_competitions": 0,
            "cases": manifests,
            "authority_boundary": {
                "materializer_write_scope": "new campaign root only",
                "solver_read_scope": "one sources/<case-id> directory",
                "solver_workspace_scope": "separate caller-owned directory",
                "scorer_read_scope": (
                    "one case manifest, its exact source records, hidden "
                    "labels, and one submitted artifact"),
                "runtime_routes_created": 0,
            },
            "network_calls": 0,
            "provider_calls": 0,
            "submissions": 0,
        }
        campaign_record["content_digest"] = _digest(campaign_record)
        _write_new(
            staged / "campaign-manifest.json",
            (_canonical(campaign_record) + "\n").encode("utf-8"),
            private=True)
        os.chmod(staged / "evaluator", 0o700)
        os.chmod(staged / "manifests", 0o700)
        # Create the destination itself with exclusive mkdir semantics. A
        # late competing writer therefore causes a refusal instead of letting
        # directory rename replace an empty destination.
        campaign.mkdir(mode=0o700)
        for child in sorted(staged.iterdir(), key=lambda item: item.name):
            child.rename(campaign / child.name)
    return {
        **campaign_record,
        "campaign_root": str(campaign),
        "writes_authorized": True,
    }


def _confined_file(root: Path, relative_path: str,
                   scope_relative_path: str) -> Path:
    relative = Path(relative_path)
    scope_relative = Path(scope_relative_path)
    if (relative.is_absolute() or scope_relative.is_absolute()
            or ".." in relative.parts or ".." in scope_relative.parts):
        raise FreshShapedCaseError("artifact scope must be confined and relative")
    candidate = root / relative
    scope = root / scope_relative
    _reject_symlink_components(scope, allow_missing_leaf=False)
    _reject_symlink_components(candidate, allow_missing_leaf=False)
    resolved_scope = scope.resolve(strict=True)
    resolved_candidate = candidate.resolve(strict=True)
    if not resolved_scope.is_dir() or resolved_scope not in resolved_candidate.parents:
        raise FreshShapedCaseError("artifact escapes its declared path scope")
    if not resolved_candidate.is_file():
        raise FreshShapedCaseError("artifact is not a regular file")
    return resolved_candidate


def _load_campaign_manifest(
        root: Path, expected_campaign_digest: str) -> dict:
    _require_digest(expected_campaign_digest, "expected campaign digest")
    path = _confined_file(root, "campaign-manifest.json", ".")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshShapedCaseError("campaign manifest is unreadable") from exc
    expected_fields = {
        "record_type", "generator_version", "generator_source_digest",
        "novelty_scope", "actual_kaggle_competitions", "cases",
        "authority_boundary", "network_calls", "provider_calls",
        "submissions", "content_digest",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise FreshShapedCaseError("campaign manifest fields differ from v1")
    declared_digest = value.get("content_digest")
    _require_digest(str(declared_digest or ""), "campaign manifest digest")
    body = {key: item for key, item in value.items()
            if key != "content_digest"}
    if (_digest(body) != declared_digest
            or declared_digest != expected_campaign_digest):
        raise FreshShapedCaseError(
            "campaign manifest differs from the externally expected digest")
    current_generator_digest = _digest_bytes(Path(__file__).read_bytes())
    if (value.get("record_type") != CAMPAIGN_MANIFEST_TYPE
            or value.get("generator_version") != GENERATOR_VERSION
            or value.get("generator_source_digest")
            != current_generator_digest
            or value.get("novelty_scope") != NOVELTY_SCOPE
            or value.get("actual_kaggle_competitions") != 0
            or any(value.get(name) != 0 for name in (
                "network_calls", "provider_calls", "submissions"))):
        raise FreshShapedCaseError(
            "campaign identity, generator, or effect boundary changed")
    rows = value.get("cases")
    if not isinstance(rows, list) or len(rows) != len(CASE_SPECS):
        raise FreshShapedCaseError("campaign membership is incomplete")
    member_fields = {
        "case_id", "manifest_relative_path", "manifest_digest",
        "manifest_file_sha256", "source_relative_path",
    }
    if any(not isinstance(row, dict) or set(row) != member_fields
           for row in rows):
        raise FreshShapedCaseError("campaign member fields differ from v1")
    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(_SPEC_BY_ID):
        raise FreshShapedCaseError("campaign members differ from registered cases")
    for row in rows:
        case_id = row["case_id"]
        if (row["manifest_relative_path"] != f"manifests/{case_id}.json"
                or row["source_relative_path"] != f"sources/{case_id}"):
            raise FreshShapedCaseError("campaign member paths are not canonical")
        _require_digest(row["manifest_digest"], "case manifest digest")
        _require_digest(row["manifest_file_sha256"], "case manifest file digest")
    return value


def _load_manifest(
        campaign_root: Path, case_id: str, *,
        expected_campaign_digest: str,
        expected_case_manifest_digest: str) -> tuple[CaseManifest, dict]:
    spec = _SPEC_BY_ID.get(case_id)
    if spec is None:
        raise FreshShapedCaseError("case_id is not registered")
    _require_digest(
        expected_case_manifest_digest, "expected case manifest digest")
    campaign = _load_campaign_manifest(
        campaign_root, expected_campaign_digest)
    member = next(row for row in campaign["cases"]
                  if row["case_id"] == case_id)
    if member["manifest_digest"] != expected_case_manifest_digest:
        raise FreshShapedCaseError(
            "case membership differs from the externally expected digest")
    path = _confined_file(
        campaign_root, member["manifest_relative_path"], "manifests")
    manifest_file = path.read_bytes()
    if _digest_bytes(manifest_file) != member["manifest_file_sha256"]:
        raise FreshShapedCaseError("case manifest file digest changed")
    try:
        value = json.loads(manifest_file.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshShapedCaseError("case manifest is unreadable") from exc
    if value.get("record_type") != CASE_MANIFEST_TYPE:
        raise FreshShapedCaseError("case manifest type is unsupported")
    expected_fields = {
        "record_type", "spec", "spec_digest", "generator_source_digest",
        "task_text_digest", "source_artifacts", "evaluator_artifact",
        "constant_baseline_prediction", "solver_source_relative_path",
        "evaluator_relative_path", "boundaries", "network_calls",
        "provider_calls", "submissions", "content_digest",
    }
    if set(value) != expected_fields:
        raise FreshShapedCaseError("case manifest fields differ from v1")
    if value.get("spec") != spec.to_dict() or value.get("spec_digest") != spec.spec_digest:
        raise FreshShapedCaseError("case manifest specification changed")
    source_records = tuple(ArtifactRecord(
        item["relative_path"], item["byte_count"], item["sha256"],
        item["visibility"]) for item in value.get("source_artifacts", ()))
    hidden = value.get("evaluator_artifact") or {}
    manifest = CaseManifest(
        spec=spec,
        generator_source_digest=value["generator_source_digest"],
        task_text_digest=value["task_text_digest"],
        source_artifacts=source_records,
        evaluator_artifact=ArtifactRecord(
            hidden["relative_path"], hidden["byte_count"], hidden["sha256"],
            hidden["visibility"]),
        constant_baseline_prediction=value["constant_baseline_prediction"],
        record_type=value["record_type"])
    if (value != manifest.to_dict()
            or manifest.content_digest != member["manifest_digest"]
            or manifest.content_digest != expected_case_manifest_digest
            or manifest.generator_source_digest
            != campaign["generator_source_digest"]):
        raise FreshShapedCaseError("case manifest body or digest does not match")
    return manifest, campaign


def _read_exact_artifact(
        root: Path, record: ArtifactRecord, scope_relative_path: str) -> bytes:
    path = _confined_file(root, record.relative_path, scope_relative_path)
    body = path.read_bytes()
    if len(body) != record.byte_count or _digest_bytes(body) != record.sha256:
        raise FreshShapedCaseError(
            f"artifact identity changed: {record.relative_path}")
    return body


def _rows(body: bytes, label: str) -> tuple[list[str], list[list[str]]]:
    try:
        values = list(csv.reader(io.StringIO(body.decode("utf-8"))))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise FreshShapedCaseError(f"{label} is not readable UTF-8 CSV") from exc
    if not values:
        raise FreshShapedCaseError(f"{label} is empty")
    return values[0], values[1:]


def _auc(labels: list[int], predictions: list[float]) -> float:
    if len(labels) != len(predictions) or not labels:
        raise FreshShapedCaseError("AUC needs equal non-empty arrays")
    if any(label not in (0, 1) for label in labels):
        raise FreshShapedCaseError("AUC labels must be binary")
    positives = sum(labels)
    negatives = len(labels) - positives
    if not positives or not negatives:
        raise FreshShapedCaseError("AUC needs both classes")
    ordered = sorted(enumerate(predictions), key=lambda item: item[1])
    ranks = [0.0] * len(labels)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for position in range(start, end):
            ranks[ordered[position][0]] = average_rank
        start = end
    positive_rank_sum = math.fsum(
        rank for rank, label in zip(ranks, labels) if label == 1)
    return ((positive_rank_sum - positives * (positives + 1) / 2.0)
            / (positives * negatives))


def _rmse(labels: list[float], predictions: list[float]) -> float:
    if len(labels) != len(predictions) or not labels:
        raise FreshShapedCaseError("RMSE needs equal non-empty arrays")
    differences = []
    for actual, predicted in zip(labels, predictions):
        difference = actual - predicted
        if not math.isfinite(difference):
            raise FreshShapedCaseError(
                "RMSE difference overflowed its finite range")
        differences.append(difference)
    scale = max(map(abs, differences))
    if scale == 0.0:
        return 0.0
    # Scaling before squaring prevents a finite value such as 1e308 from
    # raising OverflowError merely because its square cannot be represented.
    normalized = math.fsum((value / scale) ** 2 for value in differences)
    result = scale * math.sqrt(normalized / len(differences))
    if not math.isfinite(result):
        raise FreshShapedCaseError("RMSE result overflowed its finite range")
    return result


def _accuracy(labels: list[str], predictions: list[str]) -> float:
    if len(labels) != len(predictions) or not labels:
        raise FreshShapedCaseError("accuracy needs equal non-empty arrays")
    return sum(actual == predicted for actual, predicted in zip(
        labels, predictions)) / len(labels)


def score_submission(
        campaign_root: str, case_id: str, submission_path: str, *,
        submission_root: str, expected_campaign_digest: str,
        expected_case_manifest_digest: str) -> ScoreResult:
    """Verify and score one artifact without reading a solver conclusion."""
    root_input = Path(campaign_root).expanduser()
    _reject_symlink_components(root_input, allow_missing_leaf=False)
    if (root_input.is_symlink() or not root_input.is_dir()
            or any((root_input / name).is_symlink()
                   for name in ("sources", "evaluator", "manifests"))):
        raise FreshShapedCaseError("campaign root is unavailable or symlinked")
    root = root_input.resolve()
    submission_root_input = Path(submission_root).expanduser()
    _reject_symlink_components(
        submission_root_input, allow_missing_leaf=False)
    if (submission_root_input.is_symlink()
            or not submission_root_input.is_dir()):
        raise FreshShapedCaseError(
            "submission root must be an existing non-symlink directory")
    resolved_submission_root = submission_root_input.resolve()
    if (_contains(root, resolved_submission_root)
            or _contains(resolved_submission_root, root)):
        raise FreshShapedCaseError(
            "submission root and campaign evidence root must be disjoint")
    submission_input = Path(submission_path).expanduser()
    absolute_submission = _absolute_without_resolving(submission_input)
    try:
        submission_relative = absolute_submission.relative_to(
            _absolute_without_resolving(submission_root_input))
    except ValueError as exc:
        raise FreshShapedCaseError(
            "submission must remain below its declared root") from exc
    submission_file = _confined_file(
        resolved_submission_root, str(submission_relative), ".")
    manifest, campaign = _load_manifest(
        root, case_id,
        expected_campaign_digest=expected_campaign_digest,
        expected_case_manifest_digest=expected_case_manifest_digest)
    for artifact in manifest.source_artifacts:
        _read_exact_artifact(
            root, artifact, f"sources/{manifest.spec.case_id}")
    hidden_body = _read_exact_artifact(
        root, manifest.evaluator_artifact,
        f"evaluator/{manifest.spec.case_id}")
    hidden_header, hidden_rows = _rows(hidden_body, "hidden labels")
    expected_hidden_header = [
        "id", manifest.spec.target, "constant_prediction"]
    if hidden_header != expected_hidden_header:
        raise FreshShapedCaseError("hidden evaluator header changed")
    submission_body = submission_file.read_bytes()
    header, submitted = _rows(submission_body, "submission")
    expected_header = ["id", manifest.spec.target]
    if header != expected_header:
        raise FreshShapedCaseError(
            f"submission header {header!r} != {expected_header!r}")
    if any(len(row) != 2 for row in submitted):
        raise FreshShapedCaseError("submission rows must have exactly two fields")
    expected_ids = [row[0] for row in hidden_rows]
    submitted_ids = [row[0] for row in submitted]
    if len(submitted_ids) != len(set(submitted_ids)):
        raise FreshShapedCaseError("submission identifiers repeat")
    if submitted_ids != expected_ids:
        raise FreshShapedCaseError(
            "submission identifiers do not match hidden test order")
    raw_predictions = [row[1] for row in submitted]
    raw_labels = [row[1] for row in hidden_rows]
    raw_constant = [row[2] for row in hidden_rows]
    spec = manifest.spec
    if spec.prediction_kind in ("binary_probability", "regression"):
        try:
            predictions = [float(value) for value in raw_predictions]
            labels = [float(value) for value in raw_labels]
            constants = [float(value) for value in raw_constant]
        except ValueError as exc:
            raise FreshShapedCaseError("numeric submission contains text") from exc
        if not all(math.isfinite(value) for value in (
                *predictions, *labels, *constants)):
            raise FreshShapedCaseError("numeric submission must be finite")
        if spec.prediction_kind == "binary_probability" and any(
                value < 0.0 or value > 1.0 for value in predictions):
            raise FreshShapedCaseError(
                "binary probability submission must stay within [0,1]")
        if spec.prediction_kind == "binary_probability":
            observed = _auc([int(value) for value in labels], predictions)
            baseline = _auc([int(value) for value in labels], constants)
        else:
            observed = _rmse(labels, predictions)
            baseline = _rmse(labels, constants)
    else:
        allowed = set(spec.labels)
        if any(value not in allowed for value in raw_predictions):
            raise FreshShapedCaseError("submission contains an unknown class label")
        observed = _accuracy(raw_labels, raw_predictions)
        baseline = _accuracy(raw_labels, raw_constant)
    if spec.metric_direction == "maximize":
        threshold = (
            observed >= float(spec.minimum_metric)
            and observed - baseline
            >= float(spec.minimum_improvement_over_constant)
        )
    else:
        threshold = baseline > 0.0 and observed / baseline \
            <= float(spec.maximum_ratio_to_constant)
    return ScoreResult(
        case_id, campaign["content_digest"], manifest.content_digest,
        _digest_bytes(submission_body),
        spec.metric, spec.metric_direction, observed, baseline, threshold,
        (("manifest_and_source_hashes_match", True),
         ("hidden_manifest_and_path_scope_match", True),
         ("submission_header_matches", True),
         ("identifier_order_matches", True),
         ("values_are_admitted", True)))


def _write_submission(path: Path, target: str,
                      rows: list[list[object]]) -> None:
    _write_new(path, _csv_bytes(["id", target], rows), private=True)


def self_test() -> dict:
    """Exercise generation, isolation, metrics, scoring, and refusal paths."""
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refused(operation) -> bool:
        try:
            operation()
        except (OSError, TypeError, ValueError):
            return True
        return False

    from contract import read_contract

    with tempfile.TemporaryDirectory(prefix="fresh-shaped-check-") as workspace:
        first_root = str(Path(workspace) / "campaign-a")
        first = materialize_cases(workspace, first_root, authorize_writes=True)
        second_root = str(Path(workspace) / "campaign-b")
        second = materialize_cases(workspace, second_root, authorize_writes=True)
        first_path = Path(first_root)
        second_path = Path(second_root)
        submission_root = Path(workspace) / "solver-output"
        submission_root.mkdir()

        def member(report: dict, case_id: str) -> dict:
            return next(item for item in report["cases"]
                        if item["case_id"] == case_id)

        def load_manifest(root: Path, report: dict,
                          case_id: str) -> CaseManifest:
            value, _campaign = _load_manifest(
                root, case_id,
                expected_campaign_digest=report["content_digest"],
                expected_case_manifest_digest=(
                    member(report, case_id)["manifest_digest"]))
            return value

        def score(root: str, report: dict, case_id: str,
                  submission: Path) -> ScoreResult:
            return score_submission(
                root, case_id, str(submission),
                submission_root=str(submission_root),
                expected_campaign_digest=report["content_digest"],
                expected_case_manifest_digest=(
                    member(report, case_id)["manifest_digest"]))
        check("three_fixed_generated_cases_are_materialized",
              len(first["cases"]) == 3 and first["actual_kaggle_competitions"] == 0)
        check("generation_is_byte_deterministic",
              all(
                  (first_path / row["manifest_relative_path"]).read_bytes()
                  == (second_path / row["manifest_relative_path"]).read_bytes()
                  for row in first["cases"]))
        check("overwrite_and_missing_authority_are_refused",
              refused(lambda: materialize_cases(
                  workspace, str(Path(workspace) / "denied"),
                  authorize_writes=False))
              and refused(lambda: materialize_cases(
                  workspace, first_root, authorize_writes=True)))
        outside = str(Path(workspace).parent / "outside-fresh-shaped")
        check("campaign_must_remain_below_the_authorized_workspace",
              refused(lambda: materialize_cases(
                  workspace, outside, authorize_writes=True)))
        link = Path(workspace) / "campaign-link"
        try:
            link.symlink_to(first_path, target_is_directory=True)
            symlink_refused = refused(lambda: materialize_cases(
                workspace, str(link), authorize_writes=True))
        except OSError:
            symlink_refused = True
        check("symlink_campaign_root_is_refused", symlink_refused)

        perfect_results = []
        constant_results = []
        perfect_paths: dict[str, Path] = {}
        for spec in CASE_SPECS:
            manifest = load_manifest(first_path, first, spec.case_id)
            source = first_path / "sources" / spec.case_id
            visible_names = sorted(path.name for path in source.iterdir())
            hidden_path = first_path / manifest.evaluator_artifact.relative_path
            task_body = (source / "task.txt").read_text(encoding="utf-8")
            check(f"{spec.case_id}_source_and_hidden_trees_are_disjoint",
                  visible_names == ["sample_submission.csv", "task.txt",
                                    "test.csv", "train.csv"]
                  and source not in hidden_path.parents
                  and hidden_path.parent.stat().st_mode & 0o077 == 0
                  and hidden_path.stat().st_mode & 0o077 == 0)
            output_semantics = {
                "binary_probability": ("ROC AUC", "higher is better", "label 1"),
                "regression": ("RMSE", "lower is better", "continuous"),
                "multiclass_label": (
                    "accuracy", "higher is better", "amber, cobalt, or jade"),
            }[spec.prediction_kind]
            check(f"{spec.case_id}_task_exposes_metric_and_output_not_generator",
                  all(item in task_body for item in output_semantics)
                  and str(spec.seed) not in task_body
                  and spec.case_id not in task_body
                  and "_row" not in task_body
                  and "generator" not in task_body.lower()
                  and "coefficient" not in task_body.lower())
            train_header, train_rows = _rows(
                (source / "train.csv").read_bytes(), "train")
            test_header, test_rows = _rows(
                (source / "test.csv").read_bytes(), "test")
            sample_header, sample_rows = _rows(
                (source / "sample_submission.csv").read_bytes(), "sample")
            independent_contract = read_contract(str(source), spec.case_id)
            check(f"{spec.case_id}_shape_and_missingness_are_present",
                  len(train_rows) == spec.train_rows
                  and len(test_rows) == spec.test_rows
                  and len(spec.feature_columns) == 10
                  and spec.target in train_header
                  and spec.target not in test_header
                  and sample_header == ["id", spec.target]
                  and len(sample_rows) == spec.test_rows
                  and any("" in row for row in train_rows)
                  and independent_contract.identifier == "id"
                  and independent_contract.target == spec.target
                  and independent_contract.submission_rows == spec.test_rows)
            if spec.prediction_kind != "binary_probability":
                check(f"{spec.case_id}_target_is_not_last",
                      train_header.index(spec.target) != len(train_header) - 1)
            hidden_header, hidden_rows = _rows(
                hidden_path.read_bytes(), "hidden")
            perfect = submission_root / f"perfect-{spec.case_id}.csv"
            _write_submission(
                perfect, spec.target,
                [[row[0], row[1]] for row in hidden_rows])
            perfect_result = score(first_root, first, spec.case_id, perfect)
            perfect_results.append(perfect_result)
            perfect_paths[spec.case_id] = perfect
            constant = submission_root / f"constant-{spec.case_id}.csv"
            _write_submission(
                constant, spec.target,
                [[row[0], row[2]] for row in hidden_rows])
            constant_results.append(score(
                first_root, first, spec.case_id, constant))
            check(f"{spec.case_id}_hidden_header_is_exact",
                  hidden_header == ["id", spec.target, "constant_prediction"])
        check("perfect_outputs_pass_predeclared_thresholds",
              all(item.to_dict()["accepted"] for item in perfect_results)
              and [item.observed_metric for item in perfect_results]
              == [1.0, 0.0, 1.0])
        check("constant_outputs_fail_predeclared_thresholds",
              all(not item.threshold_passed for item in constant_results))
        scored = perfect_results[0].to_dict()
        check("score_does_not_claim_runtime_isolation",
              scored["runtime_isolation_verified"] is False
              and scored["prelaunch_freeze_verified_by_this_scorer"] is False
              and "hidden_labels_are_evaluator_only" not in {
                  item["check"] for item in scored["checks"]})

        binary_spec, regression_spec, class_spec = CASE_SPECS
        binary_manifest = load_manifest(first_path, first, binary_spec.case_id)
        _head, binary_hidden = _rows(_read_exact_artifact(
            first_path, binary_manifest.evaluator_artifact,
            f"evaluator/{binary_spec.case_id}"), "hidden")
        wrong_header = submission_root / "wrong-header.csv"
        _write_new(wrong_header, _csv_bytes(
            ["id", "wrong"], [[row[0], row[1]] for row in binary_hidden]))
        wrong_order = submission_root / "wrong-order.csv"
        _write_submission(wrong_order, binary_spec.target,
                          [[row[0], row[1]] for row in reversed(binary_hidden)])
        duplicate_id = submission_root / "duplicate-id.csv"
        duplicate_rows = [[row[0], row[1]] for row in binary_hidden]
        duplicate_rows[1][0] = duplicate_rows[0][0]
        _write_submission(duplicate_id, binary_spec.target, duplicate_rows)
        out_of_range = submission_root / "out-of-range.csv"
        _write_submission(out_of_range, binary_spec.target,
                          [[row[0], 1.5] for row in binary_hidden])
        check("bad_header_ids_and_probability_range_are_refused",
              refused(lambda: score(
                  first_root, first, binary_spec.case_id, wrong_header))
              and refused(lambda: score(
                  first_root, first, binary_spec.case_id, wrong_order))
              and refused(lambda: score(
                  first_root, first, binary_spec.case_id, duplicate_id))
              and refused(lambda: score(
                  first_root, first, binary_spec.case_id, out_of_range)))

        regression_manifest = load_manifest(
            first_path, first, regression_spec.case_id)
        _head, regression_hidden = _rows(_read_exact_artifact(
            first_path, regression_manifest.evaluator_artifact,
            f"evaluator/{regression_spec.case_id}"), "hidden")
        nonfinite = submission_root / "nonfinite.csv"
        _write_submission(nonfinite, regression_spec.target,
                          [[row[0], "nan"] for row in regression_hidden])
        class_manifest = load_manifest(first_path, first, class_spec.case_id)
        _head, class_hidden = _rows(_read_exact_artifact(
            first_path, class_manifest.evaluator_artifact,
            f"evaluator/{class_spec.case_id}"), "hidden")
        unknown_label = submission_root / "unknown-label.csv"
        _write_submission(unknown_label, class_spec.target,
                          [[row[0], "unknown"] for row in class_hidden])
        check("nonfinite_regression_and_unknown_labels_are_refused",
              refused(lambda: score(
                  first_root, first, regression_spec.case_id, nonfinite))
              and refused(lambda: score(
                  first_root, first, class_spec.case_id, unknown_label)))

        huge_finite = submission_root / "huge-finite.csv"
        _write_submission(huge_finite, regression_spec.target,
                          [[row[0], "1e308"] for row in regression_hidden])
        huge_result = score(
            first_root, first, regression_spec.case_id, huge_finite)
        numeric_infinity = submission_root / "numeric-infinity.csv"
        _write_submission(numeric_infinity, regression_spec.target,
                          [[row[0], "1e309"] for row in regression_hidden])
        check("large_finite_rmse_is_stable_and_nonfinite_is_refused",
              math.isfinite(huge_result.observed_metric)
              and not huge_result.threshold_passed
              and refused(lambda: score(
                  first_root, first, regression_spec.case_id,
                  numeric_infinity)))

        check("external_campaign_and_case_digest_anchors_are_required",
              refused(lambda: score_submission(
                  first_root, binary_spec.case_id,
                  str(perfect_paths[binary_spec.case_id]),
                  submission_root=str(submission_root),
                  expected_campaign_digest="f" * 64,
                  expected_case_manifest_digest=member(
                      first, binary_spec.case_id)["manifest_digest"]))
              and refused(lambda: score_submission(
                  first_root, binary_spec.case_id,
                  str(perfect_paths[binary_spec.case_id]),
                  submission_root=str(submission_root),
                  expected_campaign_digest=first["content_digest"],
                  expected_case_manifest_digest="f" * 64)))

        escaped_hidden = Path(workspace) / "escaped-hidden-case"
        nested_hidden = second_path / "evaluator" / binary_spec.case_id
        nested_hidden.rename(escaped_hidden)
        nested_hidden.symlink_to(escaped_hidden, target_is_directory=True)
        check("nested_evaluator_symlink_escape_is_refused",
              refused(lambda: score(
                  second_root, second, binary_spec.case_id,
                  perfect_paths[binary_spec.case_id])))

        external_output = Path(workspace) / "external-output"
        external_output.mkdir()
        external_submission = external_output / "submission.csv"
        external_submission.write_bytes(
            perfect_paths[binary_spec.case_id].read_bytes())
        linked_output = submission_root / "linked-output"
        linked_output.symlink_to(external_output, target_is_directory=True)
        check("submission_ancestor_symlink_escape_is_refused",
              refused(lambda: score_submission(
                  first_root, binary_spec.case_id,
                  str(linked_output / "submission.csv"),
                  submission_root=str(submission_root),
                  expected_campaign_digest=first["content_digest"],
                  expected_case_manifest_digest=member(
                      first, binary_spec.case_id)["manifest_digest"])))

        rewrite_root = str(Path(workspace) / "campaign-rewritten")
        rewrite_report = materialize_cases(
            workspace, rewrite_root, authorize_writes=True)
        rewrite_path = Path(rewrite_root)
        rewrite_member = member(rewrite_report, binary_spec.case_id)
        case_path = rewrite_path / rewrite_member["manifest_relative_path"]
        case_value = json.loads(case_path.read_text(encoding="utf-8"))
        case_value["generator_source_digest"] = "a" * 64
        case_value["content_digest"] = _digest({
            key: item for key, item in case_value.items()
            if key != "content_digest"})
        case_bytes = (_canonical(case_value) + "\n").encode("utf-8")
        case_path.write_bytes(case_bytes)
        campaign_path = rewrite_path / "campaign-manifest.json"
        campaign_value = json.loads(campaign_path.read_text(encoding="utf-8"))
        campaign_value["generator_source_digest"] = "a" * 64
        rewritten_member = next(
            item for item in campaign_value["cases"]
            if item["case_id"] == binary_spec.case_id)
        rewritten_member["manifest_digest"] = case_value["content_digest"]
        rewritten_member["manifest_file_sha256"] = _digest_bytes(case_bytes)
        campaign_value["content_digest"] = _digest({
            key: item for key, item in campaign_value.items()
            if key != "content_digest"})
        campaign_path.write_text(
            _canonical(campaign_value) + "\n", encoding="utf-8")
        check("self_consistent_rewrite_needs_external_freeze_and_generator",
              refused(lambda: score_submission(
                  rewrite_root, binary_spec.case_id,
                  str(perfect_paths[binary_spec.case_id]),
                  submission_root=str(submission_root),
                  expected_campaign_digest=rewrite_report["content_digest"],
                  expected_case_manifest_digest=rewrite_member[
                      "manifest_digest"]))
              and refused(lambda: score_submission(
                  rewrite_root, binary_spec.case_id,
                  str(perfect_paths[binary_spec.case_id]),
                  submission_root=str(submission_root),
                  expected_campaign_digest=campaign_value["content_digest"],
                  expected_case_manifest_digest=case_value["content_digest"])))

        changed = first_path / "sources" / binary_spec.case_id / "task.txt"
        original = changed.read_bytes()
        changed.write_bytes(original + b"changed\n")
        check("source_mutation_is_refused_before_scoring",
              refused(lambda: score(
                  first_root, first, binary_spec.case_id,
                  perfect_paths[binary_spec.case_id])))

    try:
        from sklearn.metrics import (
            accuracy_score,
            roc_auc_score,
            root_mean_squared_error,
        )
        auc_labels = [0, 0, 1, 1]
        auc_predictions = [0.1, 0.4, 0.35, 0.8]
        rmse_labels = [1.0, 2.0, 4.0]
        rmse_predictions = [1.5, 2.0, 3.0]
        class_labels = ["a", "b", "a", "c"]
        class_predictions = ["a", "a", "a", "c"]
        check("manual_metrics_match_sklearn_analytic_cases",
              math.isclose(_auc(auc_labels, auc_predictions),
                           roc_auc_score(auc_labels, auc_predictions),
                           rel_tol=0.0, abs_tol=1e-12)
              and math.isclose(_rmse(rmse_labels, rmse_predictions),
                               root_mean_squared_error(
                                   rmse_labels, rmse_predictions),
                               rel_tol=0.0, abs_tol=1e-12)
              and math.isclose(_accuracy(class_labels, class_predictions),
                               accuracy_score(class_labels, class_predictions),
                               rel_tol=0.0, abs_tol=1e-12))
    except ImportError as exc:
        check("manual_metrics_match_sklearn_analytic_cases", False, str(exc))
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "fresh_kaggle_shaped_cases_checks/v1",
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
        "network_calls": 0,
        "provider_calls": 0,
        "submissions": 0,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize or score generated Kaggle-shaped cases")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("self-test")
    materialize = commands.add_parser("materialize")
    materialize.add_argument("--workspace-root", required=True)
    materialize.add_argument("--campaign-root", required=True)
    materialize.add_argument("--authorize-writes", action="store_true")
    score = commands.add_parser("score")
    score.add_argument("--campaign-root", required=True)
    score.add_argument("--case-id", required=True, choices=tuple(_SPEC_BY_ID))
    score.add_argument("--submission-root", required=True)
    score.add_argument("--submission", required=True)
    score.add_argument("--expected-campaign-digest", required=True)
    score.add_argument("--expected-case-manifest-digest", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "self-test":
            result = self_test()
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0 if result["all_passed"] else 1
        if args.command == "materialize":
            result = materialize_cases(
                args.workspace_root, args.campaign_root,
                authorize_writes=args.authorize_writes)
        else:
            result = score_submission(
                args.campaign_root, args.case_id, args.submission,
                submission_root=args.submission_root,
                expected_campaign_digest=args.expected_campaign_digest,
                expected_case_manifest_digest=(
                    args.expected_case_manifest_digest)).to_dict()
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (OSError, TypeError, ValueError) as exc:
        print(json.dumps({
            "record_type": "fresh_kaggle_shaped_failure/v1",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "network_calls": 0,
            "provider_calls": 0,
            "submissions": 0,
        }, sort_keys=True, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
