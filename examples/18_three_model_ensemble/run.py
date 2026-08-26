"""Three-model ensemble through the canonical Loop runtime.

Build a linear model, a neural-network model, and a tree model, then
ensemble them. Each model trains as an independent child Loop with its
own typed contract. The same immutable split is shared across all
members. Per-member and ensemble metrics are reported, and the
ensemble is verified not to be silently worse than every member.

Run:
    python3 examples/18_three_model_ensemble/run.py

No network, no external service, no model calls.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop
from loop_engine.loop.recursive_loop import Loop, LoopConfig
from loop_engine.loop.loop_role import LoopRelationship


@dataclass(frozen=True)
class DatasetSpec:
    """Typed description of the synthetic dataset."""

    n_samples: int = 1200
    n_features: int = 12
    n_informative: int = 8
    n_classes: int = 2
    random_state: int = 42


@dataclass(frozen=True)
class DatasetSplit:
    """One immutable train/test split shared by every model."""

    x_train: object
    x_test: object
    y_train: object
    y_test: object
    random_state: int = 42

    def digest(self) -> str:
        import hashlib
        payload = json.dumps({
            "x_train_shape": list(np.asarray(self.x_train).shape),
            "x_test_shape": list(np.asarray(self.x_test).shape),
            "y_train_sum": int(np.asarray(self.y_train).sum()),
            "y_test_sum": int(np.asarray(self.y_test).sum()),
            "random_state": self.random_state,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModelArtifact:
    """Typed result of one model-training child Loop."""

    model_id: str
    family: str
    probabilities: object
    accuracy: float
    roc_auc: float
    seed: int = 42

    def to_dict(self) -> dict:
        return {"model_id": self.model_id, "family": self.family,
                "accuracy": round(self.accuracy, 4),
                "roc_auc": round(self.roc_auc, 4), "seed": self.seed}


@dataclass(frozen=True)
class EnsembleResult:
    """Typed ensemble outcome with per-member evidence."""

    members: tuple[ModelArtifact, ...]
    ensemble_accuracy: float
    ensemble_roc_auc: float
    best_member_accuracy: float
    best_member_roc_auc: float
    ensemble_beats_all_members: bool

    def to_dict(self) -> dict:
        return {
            "members": [m.to_dict() for m in self.members],
            "ensemble_accuracy": round(self.ensemble_accuracy, 4),
            "ensemble_roc_auc": round(self.ensemble_roc_auc, 4),
            "best_member_accuracy": round(self.best_member_accuracy, 4),
            "best_member_roc_auc": round(self.best_member_roc_auc, 4),
            "ensemble_beats_all_members": self.ensemble_beats_all_members,
        }


def _make_split(spec: DatasetSpec) -> DatasetSplit:
    x, y = make_classification(
        n_samples=spec.n_samples, n_features=spec.n_features,
        n_informative=spec.n_informative, n_classes=spec.n_classes,
        random_state=spec.random_state)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=spec.random_state,
        stratify=y)
    return DatasetSplit(x_train=x_train, x_test=x_test,
                        y_train=y_train, y_test=y_test,
                        random_state=spec.random_state)


def _train_member(family: str, split: DatasetSplit, seed: int,
                  parent: Loop, ledger: LoopLedger) -> ModelArtifact:
    """Train one model as an independent child Loop."""
    x_train = np.asarray(split.x_train)
    x_test = np.asarray(split.x_test)
    y_train = np.asarray(split.y_train)
    y_test = np.asarray(split.y_test)

    def _fit() -> dict:
        if family == "linear":
            model = LogisticRegression(max_iter=1000, random_state=seed)
        elif family == "neural":
            model = MLPClassifier(hidden_layer_sizes=(32, 16),
                                  max_iter=500, random_state=seed)
        else:
            model = RandomForestClassifier(n_estimators=200,
                                           random_state=seed)
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_test)[:, 1]
        predictions = model.predict(x_test)
        return {"probabilities": probabilities.tolist(),
                "accuracy": float(accuracy_score(y_test, predictions)),
                "roc_auc": float(roc_auc_score(y_test, probabilities))}

    result = as_practitioner_loop(
        f"train {family} model", _fit, parent=parent, ledger=ledger)
    value = result["value"]
    return ModelArtifact(
        model_id=f"{family}-{result['loop_id']}", family=family,
        probabilities=np.asarray(value["probabilities"]),
        accuracy=value["accuracy"], roc_auc=value["roc_auc"], seed=seed)


def _ensemble(members: tuple[ModelArtifact, ...],
              split: DatasetSplit) -> EnsembleResult:
    """Average member probabilities and verify the ensemble honestly."""
    y_test = np.asarray(split.y_test)
    stacked = np.mean([m.probabilities for m in members], axis=0)
    ensemble_predictions = (stacked >= 0.5).astype(int)
    ensemble_accuracy = float(accuracy_score(y_test, ensemble_predictions))
    ensemble_roc_auc = float(roc_auc_score(y_test, stacked))
    best_accuracy = max(m.accuracy for m in members)
    best_roc_auc = max(m.roc_auc for m in members)
    return EnsembleResult(
        members=members,
        ensemble_accuracy=ensemble_accuracy,
        ensemble_roc_auc=ensemble_roc_auc,
        best_member_accuracy=best_accuracy,
        best_member_roc_auc=best_roc_auc,
        ensemble_beats_all_members=(
            ensemble_accuracy >= best_accuracy
            and ensemble_roc_auc >= best_roc_auc))


def run_ensemble(spec: DatasetSpec | None = None) -> dict:
    """Run the full three-model ensemble through the canonical runtime."""
    spec = spec or DatasetSpec()
    ledger = LoopLedger()
    split = _make_split(spec)

    root = Loop("build a three-model classification ensemble",
                LoopConfig(framework="five_step", power="small",
                           allowable_modes=("deterministic",),
                           preferred_modes=("deterministic",)),
                ledger=ledger)

    members = tuple(_train_member(family, split, spec.random_state,
                                  parent=root, ledger=ledger)
                    for family in ("linear", "neural", "tree"))
    ensemble = _ensemble(members, split)

    ledger.record(loop_id=root.loop_id, event="ensemble.completed",
                  ensemble_accuracy=ensemble.ensemble_accuracy,
                  ensemble_roc_auc=ensemble.ensemble_roc_auc,
                  member_count=len(members),
                  split_digest=split.digest())
    return {"record_type": "three_model_ensemble/v1",
            "split_digest": split.digest(),
            "ensemble": ensemble.to_dict(),
            "ledger_events": len(ledger.events),
            "root_loop_id": root.loop_id}


def main() -> None:
    result = run_ensemble()
    ensemble = result["ensemble"]
    print("THREE-MODEL ENSEMBLE")
    print(f"split digest: {result['split_digest'][:16]}...")
    print(f"root loop: {result['root_loop_id']}")
    print(f"ledger events: {result['ledger_events']}")
    print()
    print("MEMBER RESULTS")
    for member in ensemble["members"]:
        print(f"  {member['family']:<8} acc={member['accuracy']:.4f}  "
              f"auc={member['roc_auc']:.4f}")
    print()
    print("ENSEMBLE RESULT")
    print(f"  accuracy: {ensemble['ensemble_accuracy']:.4f}")
    print(f"  roc_auc:  {ensemble['ensemble_roc_auc']:.4f}")
    print(f"  best member accuracy: {ensemble['best_member_accuracy']:.4f}")
    print(f"  best member roc_auc:  {ensemble['best_member_roc_auc']:.4f}")
    print(f"  ensemble beats all members: "
          f"{ensemble['ensemble_beats_all_members']}")


if __name__ == "__main__":
    main()
