"""Train a small specialist from recorded rows and register it as a candidate resolver.

A specialist is a bounded model: its input, output, and purpose are fixed
by a classification-shaped contract, and it is trained from recorded rows
with a run-level split. The trainer here is a multinomial naive Bayes over
named features, written with the standard library so it runs anywhere the
engine runs and exports as JSON weights. It is deliberately small; the
point is the pipeline, not the model class. A trained specialist is a
candidate until an independent process qualifies it, and its held-out
accuracy is measured on rows whose runs never appeared in training.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass

SPECIALIST_RECORD_TYPE = "specialist_model/v1"
TASK_RECORD_TYPE = "specialist_classification_task/v1"
LIFECYCLES = ("candidate", "qualified", "retired")


class SpecialistTrainingError(ValueError):
    """A training row, specification, or model is invalid."""


@dataclass(frozen=True)
class SpecialistSpec:
    """What the specialist answers: the label field, the feature fields, and the contract."""

    specialist_id: str
    contract_id: str
    label_field: str
    feature_fields: tuple[str, ...]
    smoothing: float = 1.0
    minimum_train_rows: int = 10
    minimum_holdout_accuracy: float = 0.7

    def __post_init__(self):
        if not self.specialist_id or not self.contract_id or not self.label_field:
            raise SpecialistTrainingError("a specialist names its identifier, contract, and label field")
        fields = tuple(self.feature_fields)
        if not fields or any(not isinstance(item, str) or not item for item in fields):
            raise SpecialistTrainingError("a specialist names at least one feature field")
        if self.smoothing <= 0:
            raise SpecialistTrainingError("smoothing is positive")
        if type(self.minimum_train_rows) is not int or self.minimum_train_rows < 1:
            raise SpecialistTrainingError("minimum_train_rows is a positive integer")
        if not 0.0 <= self.minimum_holdout_accuracy <= 1.0:
            raise SpecialistTrainingError("minimum_holdout_accuracy lies in [0, 1]")
        object.__setattr__(self, "feature_fields", fields)


def features_of(row: dict, spec: SpecialistSpec) -> list[str]:
    """Named features: field=value tokens; a list value contributes one token per item."""
    tokens = []
    for name in spec.feature_fields:
        value = row.get(name)
        if isinstance(value, (list, tuple)):
            tokens.extend(f"{name}={item}" for item in value)
        elif value is not None and value != "":
            tokens.append(f"{name}={value}")
    return tokens


@dataclass(frozen=True)
class SpecialistModel:
    """JSON-exportable weights: log priors and per-label log likelihoods."""

    spec: SpecialistSpec
    labels: tuple[str, ...]
    log_priors: dict
    log_likelihoods: dict
    vocabulary: tuple[str, ...]
    train_rows: int
    train_runs: int
    holdout_accuracy: "float | None"
    holdout_rows: int
    lifecycle: str = LIFECYCLES[0]
    dataset_ref: str = ""

    def __post_init__(self):
        if self.lifecycle not in LIFECYCLES:
            raise SpecialistTrainingError(f"lifecycle must be one of {LIFECYCLES}")

    def predict(self, row: dict) -> tuple[str, float]:
        """The label and its normalized probability."""
        tokens = features_of(row, self.spec)
        scores = {}
        for label in self.labels:
            score = self.log_priors[label]
            likelihood = self.log_likelihoods[label]
            unseen = likelihood["__unseen__"]
            for token in tokens:
                score += likelihood.get(token, unseen)
            scores[label] = score
        top = max(scores.values())
        total = sum(math.exp(value - top) for value in scores.values())
        best = max(self.labels, key=lambda label: (scores[label], label))
        return best, round(math.exp(scores[best] - top) / total, 4)

    def evaluate(self, rows) -> dict:
        rows = list(rows)
        correct = sum(1 for row in rows if self.predict(row)[0] == str(row.get(self.spec.label_field)))
        return {"rows": len(rows), "correct": correct,
                "accuracy": (correct / len(rows)) if rows else None}

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(json.dumps(
            {"labels": self.labels, "log_priors": self.log_priors, "log_likelihoods": self.log_likelihoods},
            sort_keys=True).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {"record_type": SPECIALIST_RECORD_TYPE, "specialist_id": self.spec.specialist_id,
                "contract_id": self.spec.contract_id, "label_field": self.spec.label_field,
                "feature_fields": list(self.spec.feature_fields), "labels": list(self.labels),
                "log_priors": self.log_priors, "log_likelihoods": self.log_likelihoods,
                "vocabulary_size": len(self.vocabulary), "train_rows": self.train_rows,
                "train_runs": self.train_runs, "holdout_accuracy": self.holdout_accuracy,
                "holdout_rows": self.holdout_rows, "lifecycle": self.lifecycle,
                "dataset_ref": self.dataset_ref, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, value: dict) -> "SpecialistModel":
        if value.get("record_type") != SPECIALIST_RECORD_TYPE:
            raise SpecialistTrainingError("not a specialist model record")
        spec = SpecialistSpec(value["specialist_id"], value["contract_id"], value["label_field"],
                              tuple(value["feature_fields"]))
        likelihoods = value["log_likelihoods"]
        vocabulary = tuple(sorted({token for table in likelihoods.values() for token in table if token != "__unseen__"}))
        return cls(spec, tuple(value["labels"]), value["log_priors"], likelihoods, vocabulary,
                   int(value["train_rows"]), int(value["train_runs"]), value.get("holdout_accuracy"),
                   int(value.get("holdout_rows", 0)), value.get("lifecycle", LIFECYCLES[0]),
                   str(value.get("dataset_ref") or ""))

    @property
    def meets_threshold(self) -> bool:
        return (self.holdout_accuracy is not None
                and self.holdout_accuracy >= self.spec.minimum_holdout_accuracy)


def train_specialist(spec: SpecialistSpec, train_rows, holdout_rows, *, dataset_ref: str = "") -> SpecialistModel:
    """Fit the naive Bayes weights on train rows; measure on holdout rows from other runs."""
    train = [row for row in train_rows if isinstance(row, dict)]
    holdout = [row for row in holdout_rows if isinstance(row, dict)]
    if len(train) < spec.minimum_train_rows:
        raise SpecialistTrainingError(f"training needs at least {spec.minimum_train_rows} rows; got {len(train)}")
    train_runs = {row.get("run_id") for row in train if row.get("run_id")}
    leaked = train_runs & {row.get("run_id") for row in holdout if row.get("run_id")}
    if leaked:
        raise SpecialistTrainingError(f"holdout rows share runs with training rows: {sorted(leaked)[:3]}")
    labels = sorted({str(row.get(spec.label_field)) for row in train if row.get(spec.label_field) is not None})
    if len(labels) < 2:
        raise SpecialistTrainingError("training needs at least two labels")
    counts = {label: Counter() for label in labels}
    label_rows = Counter()
    vocabulary = set()
    for row in train:
        label = str(row.get(spec.label_field))
        if label not in counts:
            continue
        label_rows[label] += 1
        tokens = features_of(row, spec)
        vocabulary.update(tokens)
        counts[label].update(tokens)
    total_rows = sum(label_rows.values())
    size = len(vocabulary)
    log_priors = {label: math.log(label_rows[label] / total_rows) for label in labels}
    log_likelihoods = {}
    for label in labels:
        total = sum(counts[label].values()) + spec.smoothing * (size + 1)
        table = {token: math.log((counts[label][token] + spec.smoothing) / total) for token in vocabulary}
        table["__unseen__"] = math.log(spec.smoothing / total)
        log_likelihoods[label] = table
    model = SpecialistModel(spec, tuple(labels), log_priors, log_likelihoods, tuple(sorted(vocabulary)),
                            total_rows, len(train_runs), None, len(holdout), dataset_ref=dataset_ref)
    evaluation = model.evaluate(holdout)
    return SpecialistModel(spec, model.labels, log_priors, log_likelihoods, model.vocabulary, total_rows,
                           len(train_runs), evaluation["accuracy"], len(holdout), dataset_ref=dataset_ref)


class SpecialistResolver:
    """A candidate exact resolver that answers only its typed classification task."""

    def __init__(self, model: SpecialistModel):
        self.model = model
        self.resolver_id = f"specialist.{model.spec.specialist_id}@{model.content_digest[:12]}"

    def _parse(self, task: str) -> "dict | None":
        try:
            value = json.loads(task)
        except (TypeError, ValueError):
            return None
        if not isinstance(value, dict) or value.get("record_type") != TASK_RECORD_TYPE:
            return None
        return value if value.get("specialist_id") == self.model.spec.specialist_id else None

    def supports(self, task: str) -> bool:
        return self._parse(task) is not None

    def execute(self, task: str) -> dict:
        record = self._parse(task)
        if record is None:
            raise SpecialistTrainingError("not a task for this specialist")
        label, probability = self.model.predict(record.get("row") or {})
        return {"verified": False, "label": label, "confidence": probability,
                "lifecycle": self.model.lifecycle, "specialist_id": self.model.spec.specialist_id,
                "model_digest": self.model.content_digest,
                "note": "a specialist answer is a candidate; independent verification decides"}


def self_test() -> dict:
    """Training splits by run, measures on held-out runs, exports, and refuses leaks and small sets."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except SpecialistTrainingError:
            return True
        return False

    spec = SpecialistSpec("route_label", "practitioner.route", "route", ("step", "contract_id", "deviation_problems"))
    rows = []
    for index in range(40):
        run = f"run-{index % 8}"
        if index % 2 == 0:
            rows.append({"run_id": run, "step": "verify", "contract_id": "practitioner.verify",
                         "deviation_problems": ["missing_field"], "route": "repair"})
        else:
            rows.append({"run_id": run, "step": "decide_next", "contract_id": "practitioner.route",
                         "deviation_problems": [], "route": "continue"})
    train = [row for row in rows if row["run_id"] not in ("run-6", "run-7")]
    holdout = [row for row in rows if row["run_id"] in ("run-6", "run-7")]
    model = train_specialist(spec, train, holdout, dataset_ref="dataset.route_calls@1.0.0")
    check("a_specialist_learns_a_separable_label_and_measures_on_held_out_runs",
          model.holdout_accuracy == 1.0 and model.holdout_rows == 10 and model.train_runs == 6
          and model.predict({"step": "verify", "contract_id": "practitioner.verify",
                             "deviation_problems": ["missing_field"]})[0] == "repair"
          and model.predict({"step": "decide_next", "contract_id": "practitioner.route"})[0] == "continue"
          and model.meets_threshold and model.lifecycle == "candidate")
    exported = SpecialistModel.from_dict(json.loads(json.dumps(model.to_dict())))
    check("the_model_exports_as_json_weights_and_predicts_the_same_after_reload",
          exported.content_digest == model.content_digest
          and exported.predict({"step": "verify", "contract_id": "practitioner.verify",
                                "deviation_problems": ["missing_field"]}) == model.predict(
              {"step": "verify", "contract_id": "practitioner.verify", "deviation_problems": ["missing_field"]})
          and "run-0" not in json.dumps(model.to_dict()))
    check("a_leaked_split_too_few_rows_and_one_label_are_refused",
          refuses(lambda: train_specialist(spec, train, train[:4]))
          and refuses(lambda: train_specialist(spec, train[:5], holdout))
          and refuses(lambda: train_specialist(spec, [row for row in train if row["route"] == "repair"], holdout)))
    resolver = SpecialistResolver(model)
    task = json.dumps({"record_type": TASK_RECORD_TYPE, "specialist_id": "route_label",
                       "row": {"step": "verify", "contract_id": "practitioner.verify",
                               "deviation_problems": ["missing_field"]}})
    answer = resolver.execute(task)
    check("the_resolver_supports_only_its_typed_task_and_never_claims_verification",
          resolver.supports(task) and not resolver.supports("classify this")
          and not resolver.supports(json.dumps({"record_type": TASK_RECORD_TYPE, "specialist_id": "other"}))
          and answer["label"] == "repair" and answer["verified"] is False and 0 < answer["confidence"] <= 1
          and resolver.resolver_id.startswith("specialist.route_label@"))
    check("specifications_refuse_bad_values",
          refuses(lambda: SpecialistSpec("", "c", "l", ("f",)))
          and refuses(lambda: SpecialistSpec("s", "c", "l", ()))
          and refuses(lambda: SpecialistSpec("s", "c", "l", ("f",), smoothing=0))
          and refuses(lambda: SpecialistSpec("s", "c", "l", ("f",), minimum_holdout_accuracy=2))
          and refuses(lambda: SpecialistModel.from_dict({"record_type": "other"})))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "specialist_training_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
