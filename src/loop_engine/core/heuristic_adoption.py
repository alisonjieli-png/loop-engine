"""Versioned training datasets and the policy that decides when a heuristic may be adopted.

The owner's rule: collect the learning data now, in a versioned place fit
for training specialized models, but adopt no heuristic before a declared
number of recorded runs, except an exact fingerprint at the atomic level of
a reason, build, or execute step. The threshold is a policy value so it can
be reviewed; it is one million runs today.

A ``DatasetVersion`` is a catalog record: it carries the schema, the split
manifest, the exclusion counts, the row count, and a digest, never the rows
themselves in the record. ``HeuristicAdoptionPolicy.decide`` is the only
path that may say yes, and it says yes to a similarity, threshold,
embedding, or routing heuristic only when the evidence run count and a
published dataset version are both present.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..catalog.protocol import CatalogStore, StoreError, require_operation
from ..catalog.query import IntelligenceQuery

HEURISTIC_KINDS = ("exact_fingerprint", "similarity", "learned_threshold", "embedding_block",
                   "routing_model", "specialist_classifier")
SCOPES = ("atomic", "node", "graph", "space")
DATASET_ARTIFACT_KIND = "training_dataset"
DATASET_RECORD_TYPE = "training_dataset_version/v1"
DECISION_RECORD_TYPE = "heuristic_adoption_decision/v1"
DEFAULT_MINIMUM_RUNS = 1_000_000


class HeuristicAdoptionError(ValueError):
    """A dataset version, proposal, or policy is invalid."""


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DatasetVersion:
    """One published, immutable version of a training dataset."""

    dataset_id: str
    version: str
    schema_id: str
    row_count: int
    train_rows: int
    holdout_rows: int
    exclusions: tuple[tuple[str, int], ...]
    content_digest: str
    source_run_count: int
    policy_version: str = ""

    def __post_init__(self):
        for name in ("dataset_id", "version", "schema_id", "content_digest"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise HeuristicAdoptionError(f"a dataset version needs its {name}")
        for name in ("row_count", "train_rows", "holdout_rows", "source_run_count"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise HeuristicAdoptionError(f"{name} is a non-negative integer")
        if self.train_rows + self.holdout_rows != self.row_count:
            raise HeuristicAdoptionError("train and holdout rows add up to the row count")
        exclusions = tuple((str(reason), int(count)) for reason, count in self.exclusions)
        object.__setattr__(self, "exclusions", exclusions)

    @property
    def record_id(self) -> str:
        return f"dataset.{self.dataset_id}"

    def to_record(self, namespace: str) -> dict:
        return {"record_id": self.record_id, "record_version": self.version,
                "intelligence_layer": "runtime_history_solution", "source_collection": "learned",
                "artifact_kind": DATASET_ARTIFACT_KIND, "lifecycle": "active", "namespace": namespace,
                "attributes": {"dataset_id": self.dataset_id, "schema_id": self.schema_id,
                               "row_count": self.row_count, "source_run_count": self.source_run_count,
                               "content_digest": self.content_digest},
                "payload": self.to_dict()}

    def to_dict(self) -> dict:
        return {"record_type": DATASET_RECORD_TYPE, **{
            name: (list(value) if isinstance(value, tuple) else value)
            for name, value in ((name, getattr(self, name)) for name in self.__dataclass_fields__)}}

    @classmethod
    def from_record(cls, record: dict) -> "DatasetVersion":
        payload = record.get("payload") or {}
        if payload.get("record_type") != DATASET_RECORD_TYPE:
            raise HeuristicAdoptionError("not a training dataset version record")
        return cls(payload["dataset_id"], payload["version"], payload["schema_id"], payload["row_count"],
                   payload["train_rows"], payload["holdout_rows"],
                   tuple((item[0], item[1]) for item in payload.get("exclusions") or ()),
                   payload["content_digest"], payload["source_run_count"],
                   str(payload.get("policy_version") or ""))


def dataset_version_from_export(dataset_id: str, version: str, schema_id: str, export: dict) -> DatasetVersion:
    """Describe one training export (as ``export_training_rows`` returns it) as a version."""
    train = export.get("train") or []
    holdout = export.get("holdout") or []
    exclusions: dict = {}
    for item in export.get("excluded") or ():
        exclusions[item.get("reason", "unknown")] = exclusions.get(item.get("reason", "unknown"), 0) + 1
    runs = {row.get("run_id") for row in [*train, *holdout] if isinstance(row, dict) and row.get("run_id")}
    return DatasetVersion(dataset_id, version, schema_id, len(train) + len(holdout), len(train), len(holdout),
                          tuple(sorted(exclusions.items())),
                          str(export.get("content_digest") or _digest({"train": train, "holdout": holdout})),
                          len(runs), str(export.get("policy_version") or ""))


class TrainingDataStore:
    """Publish and list dataset versions inside a catalog store; versions are never overwritten."""

    def __init__(self, store: CatalogStore, namespace: str = "org:local"):
        self.store = store
        self.namespace = namespace

    def publish(self, dataset: DatasetVersion) -> DatasetVersion:
        require_operation(self.store, "write")
        existing = self.store.get(dataset.record_id)
        if existing is not None:
            current = DatasetVersion.from_record(existing)
            if current.version == dataset.version and current.content_digest != dataset.content_digest:
                raise HeuristicAdoptionError(f"{dataset.record_id} {dataset.version} exists with different content")
            if current.version == dataset.version:
                return current
            from ..catalog.versioning import revise
            revise(self.store, dataset.to_record(self.namespace), expected_version=current.version)
            return dataset
        self.store.put(dataset.to_record(self.namespace))
        return dataset

    def current(self, dataset_id: str) -> "DatasetVersion | None":
        record = self.store.get(f"dataset.{dataset_id}")
        return DatasetVersion.from_record(record) if record is not None else None

    def versions(self, dataset_id: str) -> list[str]:
        from ..catalog.versioning import history
        return [item["version"] for item in history(self.store, f"dataset.{dataset_id}")["versions"]]

    def datasets(self) -> list[str]:
        records = self.store.query(IntelligenceQuery(artifact_kinds=(DATASET_ARTIFACT_KIND,),
                                                     lifecycle=("active",), namespaces=(self.namespace,)))
        return sorted(item["attributes"]["dataset_id"] for item in records)


@dataclass(frozen=True)
class HeuristicProposal:
    """A heuristic someone wants the engine to start using."""

    heuristic_id: str
    kind: str
    scope: str
    evidence_runs: int
    dataset_id: str = ""
    dataset_version: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.heuristic_id:
            raise HeuristicAdoptionError("a proposal names its heuristic")
        if self.kind not in HEURISTIC_KINDS:
            raise HeuristicAdoptionError(f"kind must be one of {HEURISTIC_KINDS}")
        if self.scope not in SCOPES:
            raise HeuristicAdoptionError(f"scope must be one of {SCOPES}")
        if type(self.evidence_runs) is not int or self.evidence_runs < 0:
            raise HeuristicAdoptionError("evidence_runs is a non-negative integer")


@dataclass(frozen=True)
class AdoptionDecision:
    heuristic_id: str
    allowed: bool
    reason: str
    minimum_runs: int
    evidence_runs: int

    def to_dict(self) -> dict:
        return {"record_type": DECISION_RECORD_TYPE, **{
            name: getattr(self, name) for name in self.__dataclass_fields__}}


@dataclass(frozen=True)
class HeuristicAdoptionPolicy:
    """When a heuristic may be adopted: a declared run count, with one named exception."""

    minimum_runs: int = DEFAULT_MINIMUM_RUNS
    atomic_exact_fingerprint_allowed: bool = True
    version: str = "1.0.0"

    def __post_init__(self):
        if type(self.minimum_runs) is not int or self.minimum_runs < 1:
            raise HeuristicAdoptionError("minimum_runs is a positive integer")
        if type(self.atomic_exact_fingerprint_allowed) is not bool:
            raise HeuristicAdoptionError("the exception flag is an explicit Boolean")

    def decide(self, proposal: HeuristicProposal, store: "TrainingDataStore | None" = None) -> AdoptionDecision:
        if (proposal.kind == HEURISTIC_KINDS[0] and proposal.scope == SCOPES[0]
                and self.atomic_exact_fingerprint_allowed):
            return AdoptionDecision(proposal.heuristic_id, True,
                                    "an exact fingerprint at the atomic level is allowed by policy",
                                    self.minimum_runs, proposal.evidence_runs)
        if proposal.evidence_runs < self.minimum_runs:
            return AdoptionDecision(proposal.heuristic_id, False,
                                    f"{proposal.evidence_runs} recorded runs are below the declared "
                                    f"minimum of {self.minimum_runs}", self.minimum_runs, proposal.evidence_runs)
        if not proposal.dataset_id or not proposal.dataset_version:
            return AdoptionDecision(proposal.heuristic_id, False,
                                    "a heuristic beyond an atomic fingerprint names the published dataset "
                                    "version it was learned from", self.minimum_runs, proposal.evidence_runs)
        if store is not None:
            published = store.current(proposal.dataset_id)
            versions = store.versions(proposal.dataset_id) if published is not None else []
            if proposal.dataset_version not in versions:
                return AdoptionDecision(proposal.heuristic_id, False,
                                        f"dataset {proposal.dataset_id} has no published version "
                                        f"{proposal.dataset_version}", self.minimum_runs, proposal.evidence_runs)
        return AdoptionDecision(proposal.heuristic_id, True,
                                "the declared run count is reached and the dataset version is published",
                                self.minimum_runs, proposal.evidence_runs)


def self_test() -> dict:
    """Datasets publish as versions; adoption waits for the declared run count, except atomic fingerprints."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except (HeuristicAdoptionError, StoreError):
            return True
        return False

    from ..catalog.stores.in_memory import EphemeralRecordStore
    export = {"record_type": "model_call_training_export/v1", "policy_version": "1.0.0",
              "train": [{"run_id": "run-1", "step": "a"}, {"run_id": "run-2", "step": "a"}],
              "holdout": [{"run_id": "run-3", "step": "a"}],
              "excluded": [{"record_id": "x", "reason": "unverified_outcome"},
                           {"record_id": "y", "reason": "unverified_outcome"},
                           {"record_id": "z", "reason": "secret_pattern"}],
              "content_digest": "d" * 64}
    first = dataset_version_from_export("decide_next_calls", "1.0.0", "model_call_learning_record/v1", export)
    check("a_dataset_version_describes_an_export_without_holding_its_rows",
          first.row_count == 3 and first.train_rows == 2 and first.holdout_rows == 1
          and first.source_run_count == 3 and dict(first.exclusions) == {"secret_pattern": 1, "unverified_outcome": 2}
          and "run-1" not in json.dumps(first.to_record("org:test")["attributes"]))
    store = TrainingDataStore(EphemeralRecordStore(), "org:test")
    store.publish(first)
    second = dataset_version_from_export("decide_next_calls", "1.1.0", "model_call_learning_record/v1",
                                         {**export, "train": [*export["train"], {"run_id": "run-4", "step": "a"}],
                                          "content_digest": "e" * 64})
    store.publish(second)
    check("versions_are_kept_and_never_overwritten",
          store.versions("decide_next_calls") == ["1.0.0", "1.1.0"] and store.current("decide_next_calls").version == "1.1.0"
          and store.datasets() == ["decide_next_calls"]
          and refuses(lambda: store.publish(dataset_version_from_export(
              "decide_next_calls", "1.1.0", "model_call_learning_record/v1", {**export, "content_digest": "f" * 64})))
          and DatasetVersion.from_record(store.store.get("dataset.decide_next_calls")) == second)
    policy = HeuristicAdoptionPolicy()
    atomic = HeuristicProposal("fp.decide_next", "exact_fingerprint", "atomic", 12)
    similarity = HeuristicProposal("sim.decide_next", "similarity", "node", 999_999,
                                   "decide_next_calls", "1.1.0")
    enough = HeuristicProposal("sim.decide_next", "similarity", "node", 1_000_000, "decide_next_calls", "1.1.0")
    unpublished = HeuristicProposal("sim.other", "similarity", "node", 1_000_000, "decide_next_calls", "9.9.9")
    nameless = HeuristicProposal("sim.nameless", "learned_threshold", "graph", 1_000_000)
    check("an_exact_atomic_fingerprint_is_allowed_below_the_threshold_and_nothing_else_is",
          policy.decide(atomic).allowed
          and not policy.decide(similarity, store).allowed
          and "below the declared minimum" in policy.decide(similarity, store).reason
          and not policy.decide(HeuristicProposal("fp.node", "exact_fingerprint", "node", 12)).allowed)
    check("a_heuristic_is_allowed_only_with_the_run_count_and_a_published_dataset_version",
          policy.decide(enough, store).allowed
          and not policy.decide(unpublished, store).allowed
          and not policy.decide(nameless, store).allowed
          and policy.decide(enough, store).to_dict()["minimum_runs"] == DEFAULT_MINIMUM_RUNS)
    lowered = HeuristicAdoptionPolicy(minimum_runs=10, atomic_exact_fingerprint_allowed=False)
    check("the_threshold_and_the_exception_are_policy_values",
          lowered.decide(similarity, store).allowed and not lowered.decide(atomic).allowed
          and refuses(lambda: HeuristicAdoptionPolicy(minimum_runs=0))
          and refuses(lambda: HeuristicProposal("x", "magic", "atomic", 1))
          and refuses(lambda: HeuristicProposal("x", "similarity", "everywhere", 1))
          and refuses(lambda: DatasetVersion("d", "1.0.0", "s", 3, 1, 1, (), "x", 1)))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "heuristic_adoption_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
