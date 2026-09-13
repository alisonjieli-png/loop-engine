"""Passive contracts for task-conditioned configuration proposals.

These records describe search inputs and measured observations. They do not
grant execution, establish evaluator independence, accept a task, or promote
intelligence. The host must resolve evidence through existing Run History
and artifact contracts before an optimizer can consume it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields
import math
import re

from .model.fragments import GenerationError
from .space import ConfigurationSpace, content_digest

# The states an observed trial can be in; only a completed trial supplies values.
COMPLETED, FAILED, RUNNING, CANCELLED, UNKNOWN = "completed", "failed", "running", "cancelled", "unknown"
OBSERVATION_STATES = (COMPLETED, FAILED, RUNNING, CANCELLED, UNKNOWN)


def exact_text(value, name):
    if (type(value) is not str or not value.strip() or value != value.strip()
            or any(ord(character) < 32 for character in value)):
        raise GenerationError(name + " must be exact nonempty text")


def exact_digest(value, name):
    if type(value) is not str or not re.fullmatch("[0-9a-f]{64}", value):
        raise GenerationError(name + " must be a SHA-256 digest")


def versioned_ref(value, name):
    exact_text(value, name)
    if not re.search(r"(?:/v[1-9][0-9]*|@[0-9]+\.[0-9]+\.[0-9]+)$", value):
        raise GenerationError(name + " must include an explicit version")


OBSERVATION_RECORD_TYPE = "configuration_search_observation/v1"
CURSOR_RECORD_TYPE = "configuration_search_cursor/v1"
REQUEST_RECORD_TYPE = "configuration_search_request/v1"


def _exact_record(record, cls, name, *, record_type=None):
    """The record's fields must be exactly the dataclass's fields (plus the
    record type when one is written); an unknown field is refused rather
    than dropped, since a dropped field would silently change the record."""
    expected = {item.name for item in fields(cls)}
    if record_type is not None:
        expected.add("record_type")
    if not isinstance(record, dict) or set(record) != expected:
        raise GenerationError(name + " record has unexpected or missing fields")
    if record_type is not None and record["record_type"] != record_type:
        raise GenerationError(name + " record is of another type")
    return {key: value for key, value in record.items() if key != "record_type"}


@dataclass(frozen=True)
class SearchObjective:
    """One versioned metric, direction, and comparable value definition."""

    metric_ref: str
    direction: str

    def __post_init__(self):
        versioned_ref(self.metric_ref, "metric reference")
        if self.direction not in ("minimize", "maximize"):
            raise GenerationError("objective direction must be explicit")

    @classmethod
    def from_dict(cls, record) -> "SearchObjective":
        return cls(**_exact_record(record, cls, "search objective"))


@dataclass(frozen=True)
class SearchTask:
    """Exact task identity plus optional host-supplied, versioned features."""

    task_id: str
    task_digest: str
    contract_ref: str
    evaluator_ref: str
    feature_space_ref: str = ""
    features: tuple[float, ...] = ()
    evaluator_digest: str = ""

    def __post_init__(self):
        for name in ("task_id", "contract_ref", "evaluator_ref"):
            exact_text(getattr(self, name), name)
        for name in ("contract_ref", "evaluator_ref"):
            versioned_ref(getattr(self, name), name)
        exact_digest(self.task_digest, "task digest")
        if self.evaluator_digest != "":
            exact_digest(self.evaluator_digest, "evaluator digest")
        values = tuple(self.features)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise GenerationError("task features must be finite numbers")
        if bool(values) != bool(self.feature_space_ref):
            raise GenerationError("task features need their exact feature-space identity")
        if values:
            versioned_ref(self.feature_space_ref, "feature-space reference")
        object.__setattr__(self, "features", values)

    @property
    def digest(self):
        """Record identity: every field, including the optional feature
        encoding. An absent evaluator digest is left out so records written
        before the field existed keep their digests."""
        record = asdict(self)
        if not record["evaluator_digest"]:
            del record["evaluator_digest"]
        return content_digest(record)

    @classmethod
    def from_dict(cls, record) -> "SearchTask":
        values = _exact_record(record, cls, "search task")
        if not isinstance(values["features"], (list, tuple)):
            raise GenerationError("search task features must be a list")
        return cls(**{**values, "features": tuple(values["features"])})

    @property
    def identity_digest(self):
        """Exact-task identity: what makes two observations belong to the
        same task for no-repeat, dominance, and optimizer history. Attaching
        or re-versioning task features does not create another task."""
        return content_digest({"task_id": self.task_id, "task_digest": self.task_digest,
                               "contract_ref": self.contract_ref,
                               "evaluator_ref": self.evaluator_ref})


@dataclass(frozen=True)
class SearchObservation:
    """An exact trial observation, still subject to host evidence resolution."""

    trial_id: str
    task: SearchTask
    space_digest: str
    configuration_index: int
    objectives: tuple[SearchObjective, ...]
    values: tuple[float | None, ...]
    state: str
    trial_occurrence_ref: str
    history_ref: str
    history_digest: str
    evaluation_ref: str
    evaluation_digest: str
    data_partition: str
    version: str = "1.0.0"

    def __post_init__(self):
        for name in ("trial_id", "trial_occurrence_ref", "history_ref", "evaluation_ref"):
            exact_text(getattr(self, name), name)
        for name in ("space_digest", "history_digest", "evaluation_digest"):
            exact_digest(getattr(self, name), name)
        if not isinstance(self.task, SearchTask) or self.version != "1.0.0":
            raise GenerationError("search observation requires a typed task and supported version")
        if type(self.configuration_index) is not int or self.configuration_index < 0:
            raise GenerationError("configuration index must be nonnegative")
        if self.state not in OBSERVATION_STATES:
            raise GenerationError("unknown search observation state")
        if self.data_partition not in ("search_feedback", "sealed_final"):
            raise GenerationError("observation must declare its evaluation partition")
        objectives, values = tuple(self.objectives), tuple(self.values)
        if (not objectives or any(not isinstance(v, SearchObjective) for v in objectives)
                or len(values) != len(objectives)
                or len({v.metric_ref for v in objectives}) != len(objectives)):
            raise GenerationError("observation metrics must bind one value each")
        if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v))
               for v in values):
            raise GenerationError("observations need finite measurements or explicit unknowns")
        if self.state != COMPLETED and any(v is not None for v in values):
            raise GenerationError("unfinished or failed trials cannot supply measured objective values")
        object.__setattr__(self, "objectives", objectives)
        object.__setattr__(self, "values", values)

    @property
    def digest(self):
        return content_digest(asdict(self))

    def to_dict(self):
        return {"record_type": OBSERVATION_RECORD_TYPE, **asdict(self)}

    @classmethod
    def from_dict(cls, record) -> "SearchObservation":
        values = _exact_record(record, cls, "search observation", record_type=OBSERVATION_RECORD_TYPE)
        if not isinstance(values["objectives"], (list, tuple)) or not isinstance(values["values"], (list, tuple)):
            raise GenerationError("search observation objectives and values must be lists")
        return cls(**{**values, "task": SearchTask.from_dict(values["task"]),
                      "objectives": tuple(SearchObjective.from_dict(v) for v in values["objectives"]),
                      "values": tuple(values["values"])})


@dataclass(frozen=True)
class SearchCursor:
    """Where exact enumeration stops in one space and shard, bound to both.

    A bare integer resumes anywhere it is handed; this record refuses a
    request whose space or shard differs from the one that produced it."""

    space_digest: str
    shard_count: int
    shard_index: int
    next_index: int | None
    exhausted: bool

    def __post_init__(self):
        exact_digest(self.space_digest, "cursor space digest")
        if (type(self.shard_count) is not int or self.shard_count < 1
                or type(self.shard_index) is not int or not 0 <= self.shard_index < self.shard_count):
            raise GenerationError("cursor shard must be an explicit index within its count")
        if type(self.exhausted) is not bool:
            raise GenerationError("cursor exhaustion must be a Boolean")
        if self.next_index is None:
            if not self.exhausted:
                raise GenerationError("a cursor without a next index must be exhausted")
        elif type(self.next_index) is not int or isinstance(self.next_index, bool) or self.next_index < 0:
            raise GenerationError("cursor next index must be a nonnegative integer")

    def to_dict(self):
        return {"record_type": CURSOR_RECORD_TYPE, **asdict(self)}

    @classmethod
    def from_dict(cls, record) -> "SearchCursor":
        return cls(**_exact_record(record, cls, "search cursor", record_type=CURSOR_RECORD_TYPE))


@dataclass(frozen=True)
class SearchRequest:
    """One explicit proposal batch, never a total campaign or model budget."""

    space: ConfigurationSpace
    task: SearchTask
    objectives: tuple[SearchObjective, ...]
    batch_size: int
    draw_limit: int
    seed: int
    observations: tuple[SearchObservation, ...] = ()
    cursor: int = 0
    shard_count: int = 1
    shard_index: int = 0
    allow_repeated_configurations: bool = False
    cursor_record: SearchCursor | None = None

    def __post_init__(self):
        if not isinstance(self.space, ConfigurationSpace) or not isinstance(self.task, SearchTask):
            raise GenerationError("search requires a typed configuration space and task")
        if self.cursor_record is not None:
            # A bound cursor sets the integer cursor; it cannot be handed to
            # another space or shard, and cannot disagree with a cursor also
            # given as an integer.
            if not isinstance(self.cursor_record, SearchCursor):
                raise GenerationError("cursor record must be a typed SearchCursor")
            if (self.cursor_record.space_digest != self.space.digest
                    or self.cursor_record.shard_count != self.shard_count
                    or self.cursor_record.shard_index != self.shard_index):
                raise GenerationError("cursor belongs to another space or shard")
            resumed = (self.space.cardinality if self.cursor_record.next_index is None
                       else self.cursor_record.next_index)
            if self.cursor not in (0, resumed):
                raise GenerationError("an integer cursor disagrees with the bound cursor record")
            object.__setattr__(self, "cursor", resumed)
        for name in ("batch_size", "draw_limit", "shard_count"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise GenerationError(name + " must be an explicit positive integer")
        for name in ("seed", "cursor", "shard_index"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise GenerationError(name + " must be a nonnegative integer")
        if self.shard_index >= self.shard_count or self.cursor > self.space.cardinality:
            raise GenerationError("search cursor or shard is outside its declared space")
        if type(self.allow_repeated_configurations) is not bool:
            raise GenerationError("repeat policy must be a Boolean")
        objectives, observations = tuple(self.objectives), tuple(self.observations)
        if (not objectives or any(not isinstance(v, SearchObjective) for v in objectives)
                or len({v.metric_ref for v in objectives}) != len(objectives)
                or any(not isinstance(v, SearchObservation) for v in observations)):
            raise GenerationError("search metrics and observations must be typed")
        object.__setattr__(self, "objectives", objectives)
        object.__setattr__(self, "observations", observations)

    @property
    def digest(self):
        return content_digest({"space_digest": self.space.digest, "task": asdict(self.task),
            "objectives": [asdict(v) for v in self.objectives],
            "batch_size": self.batch_size, "draw_limit": self.draw_limit, "seed": self.seed,
            "cursor": self.cursor, "shard_count": self.shard_count, "shard_index": self.shard_index,
            "allow_repeated_configurations": self.allow_repeated_configurations,
            "observations": [v.digest for v in self.observations]})

    def to_dict(self):
        return {"record_type": REQUEST_RECORD_TYPE, "space": self.space.to_dict(),
                "task": asdict(self.task), "objectives": [asdict(v) for v in self.objectives],
                "batch_size": self.batch_size, "draw_limit": self.draw_limit, "seed": self.seed,
                "observations": [v.to_dict() for v in self.observations], "cursor": self.cursor,
                "shard_count": self.shard_count, "shard_index": self.shard_index,
                "allow_repeated_configurations": self.allow_repeated_configurations,
                "cursor_record": self.cursor_record.to_dict() if self.cursor_record else None}

    @classmethod
    def from_dict(cls, record) -> "SearchRequest":
        values = _exact_record(record, cls, "search request", record_type=REQUEST_RECORD_TYPE)
        if not isinstance(values["objectives"], (list, tuple)) or not isinstance(values["observations"], (list, tuple)):
            raise GenerationError("search request objectives and observations must be lists")
        return cls(**{**values, "space": ConfigurationSpace.from_dict(values["space"]),
                      "task": SearchTask.from_dict(values["task"]),
                      "objectives": tuple(SearchObjective.from_dict(v) for v in values["objectives"]),
                      "observations": tuple(SearchObservation.from_dict(v) for v in values["observations"]),
                      "cursor_record": (SearchCursor.from_dict(values["cursor_record"])
                                        if values["cursor_record"] is not None else None)})


@dataclass(frozen=True)
class SearchServices:
    """Host-bound optimizer and exact evidence resolver; no storage authority."""

    adapter: object = field(repr=False)
    resolve_evidence: object | None = field(default=None, repr=False)

    def __post_init__(self):
        if (not callable(getattr(self.adapter, "propose", None))
                or not callable(getattr(self.adapter, "settings", None))):
            raise GenerationError("an installed proposal adapter is required")
        exact_text(getattr(self.adapter, "adapter_ref", None), "adapter reference")
        if self.resolve_evidence is not None and not callable(self.resolve_evidence):
            raise GenerationError("evidence resolution must be a host callable")
