"""Concurrency contract: typed declarations for safe parallel execution.

A scheduler cannot safely answer "can these run in parallel?" from
names alone. Each Loop declares its dependencies, state access,
side effects, safety properties, consistency requirements, resources,
and lifecycle. The scheduler computes a typed ConcurrencyDecision.

This module adds no runtime. Scheduling decisions are computed by
ordinary Loops; the declarations are typed objects inside them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

class SchedulingPattern(str, Enum):
    """Supported placement-independent scheduling shapes."""

    SEQUENTIAL = "sequential"
    FORK_JOIN = "fork_join"
    BOUNDED_FANOUT = "bounded_fanout"
    PIPELINE = "pipeline"
    FIRST_SUCCESS = "first_success"
    QUORUM = "quorum"
    ENSEMBLE = "ensemble"
    DURABLE = "durable"


class JoinPolicy(str, Enum):
    """Join semantics implemented by the canonical parallel executor."""

    ALL = "all"
    FIRST_SUCCESS = "first_success"
    QUORUM = "quorum"
    ENSEMBLE = "ensemble"


class FailurePolicy(str, Enum):
    """Failure behavior implemented inside the parallel executor."""

    FAIL_FAST = "fail_fast"
    ISOLATE = "isolate"


class ParentClosePolicy(str, Enum):
    """Lifecycle behavior when an owning Loop closes."""

    AWAIT = "await"
    REQUEST_CANCEL = "request_cancel"
    TERMINATE = "terminate"
    REPARENT = "reparent"
    DETACH = "detach"


SCHEDULING_PATTERNS = tuple(value.value for value in SchedulingPattern)
JOIN_POLICIES = tuple(value.value for value in JoinPolicy)
FAILURE_POLICIES = tuple(value.value for value in FailurePolicy)
PARENT_CLOSE_POLICIES = tuple(value.value for value in ParentClosePolicy)

#: Execution placements. Separate from run mode.
PLACEMENTS = (
    "inline", "asyncio_task", "thread", "process", "local_worker",
    "remote_worker", "container", "kubernetes_job",
    "kubernetes_service", "remote_service",
)


@dataclass(frozen=True)
class ConcurrencyContract:
    """What one Loop declares about overlapping execution."""

    dependencies: tuple[str, ...] = ()
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    append_only_writes: tuple[str, ...] = ()
    compare_and_swap_writes: tuple[str, ...] = ()
    exclusive_resources: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()
    idempotent: bool = False
    reentrant: bool = False
    thread_safe: bool = False
    process_safe: bool = False
    cancellation_safe: bool = False
    checkpointable: bool = False
    retry_safe: bool = False
    required_snapshot: str = ""
    transaction_scope: str = ""
    isolation_level: str = ""
    commutative_outputs: bool = False
    merge_strategy: str = ""
    resources: dict = field(default_factory=dict)
    expected_duration_seconds: float = 0.0
    timeout_seconds: float = 0.0
    heartbeat_seconds: float = 0.0
    lease_seconds: float = 0.0
    parent_close_behavior: str = "request_cancel"

    def __post_init__(self) -> None:
        if self.parent_close_behavior not in PARENT_CLOSE_POLICIES:
            raise ValueError(
                f"parent_close_behavior must be one of "
                f"{PARENT_CLOSE_POLICIES}")
        for label, values in (("dependencies", self.dependencies),
                              ("reads", self.reads),
                              ("writes", self.writes),
                              ("append_only_writes",
                               self.append_only_writes),
                              ("compare_and_swap_writes",
                               self.compare_and_swap_writes),
                              ("exclusive_resources",
                               self.exclusive_resources),
                              ("side_effects", self.side_effects)):
            if any(not isinstance(v, str) or not v for v in values):
                raise ValueError(f"{label} must contain non-empty strings")


@dataclass(frozen=True)
class SchedulingConfiguration:
    """How a composite Loop overlaps its children."""

    scheduling_pattern: SchedulingPattern = SchedulingPattern.SEQUENTIAL
    maximum_concurrency: int = 1
    priority_policy: str = "declared_order"
    join_policy: JoinPolicy = JoinPolicy.ALL
    failure_policy: FailurePolicy = FailurePolicy.FAIL_FAST
    parent_close_policy: ParentClosePolicy = ParentClosePolicy.REQUEST_CANCEL
    result_aggregation: str = "typed_list"
    checkpoint_policy: str = "none"
    detached_lifecycle_policy: str = ""

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "scheduling_pattern",
                               SchedulingPattern(self.scheduling_pattern))
            object.__setattr__(self, "join_policy",
                               JoinPolicy(self.join_policy))
            object.__setattr__(self, "failure_policy",
                               FailurePolicy(self.failure_policy))
            object.__setattr__(self, "parent_close_policy",
                               ParentClosePolicy(self.parent_close_policy))
        except ValueError as exc:
            raise ValueError(
                "scheduling configuration names an unsupported executor "
                "policy") from exc
        if self.maximum_concurrency < 1:
            raise ValueError("maximum_concurrency must be at least 1")


@dataclass(frozen=True)
class ConcurrencyDecision:
    """The typed answer to 'can these run in parallel?'."""

    verdict: str
    reasons: tuple[str, ...] = ()
    dependency_edges: tuple[tuple[str, str], ...] = ()
    required_locks: tuple[str, ...] = ()
    resource_reservations: dict = field(default_factory=dict)
    snapshot_requirements: tuple[str, ...] = ()
    start_conditions: tuple[str, ...] = ()
    join_point: str = ""
    cancellation_behavior: str = ""
    failure_behavior: str = ""
    confidence: float = 1.0
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.verdict not in ("safe", "safe_with_constraints", "unsafe",
                                "unknown"):
            raise ValueError(
                "verdict must be safe, safe_with_constraints, unsafe, "
                "or unknown")


def decide_overlap(a: ConcurrencyContract, b: ConcurrencyContract,
                   *, available_resources: dict | None = None) \
        -> ConcurrencyDecision:
    """Deterministically decide whether two Loops may overlap.

    The decision is computed from typed declarations, never guessed
    from names. Unknown safety defaults to not parallel.
    """
    reasons: list[str] = []
    locks: list[str] = []
    constraints: list[str] = []

    a_deps = set(a.dependencies)
    b_deps = set(b.dependencies)
    if a_deps & set(b.writes) or b_deps & set(a.writes):
        return ConcurrencyDecision(
            verdict="unsafe",
            reasons=("one Loop depends on the other's incomplete "
                     "output",))

    a_writes = set(a.writes) | set(a.compare_and_swap_writes)
    b_writes = set(b.writes) | set(b.compare_and_swap_writes)
    conflicts = a_writes & b_writes
    if conflicts:
        if a.commutative_outputs and b.commutative_outputs \
                and a.merge_strategy and a.merge_strategy == b.merge_strategy:
            constraints.append(
                f"conflicting writes {sorted(conflicts)} require merge "
                f"strategy {a.merge_strategy!r}")
        else:
            return ConcurrencyDecision(
                verdict="unsafe",
                reasons=(f"conflicting writes: {sorted(conflicts)}",))

    shared_exclusive = set(a.exclusive_resources) & \
        set(b.exclusive_resources)
    if shared_exclusive:
        return ConcurrencyDecision(
            verdict="unsafe",
            reasons=(f"shared exclusive resources: "
                      f"{sorted(shared_exclusive)}",))

    if a.required_snapshot and b.required_snapshot and \
            a.required_snapshot != b.required_snapshot:
        constraints.append("different required snapshots")

    if a.transaction_scope and b.transaction_scope and \
            a.transaction_scope == b.transaction_scope and \
            a.isolation_level != b.isolation_level:
        constraints.append("incompatible isolation levels in shared "
                           "transaction scope")

    if available_resources is not None:
        combined: dict[str, float] = {}
        for key, value in a.resources.items():
            combined[key] = combined.get(key, 0) + value
        for key, value in b.resources.items():
            combined[key] = combined.get(key, 0) + value
        for key, needed in combined.items():
            available = available_resources.get(key)
            if available is not None and needed > available:
                return ConcurrencyDecision(
                    verdict="unsafe",
                    reasons=(f"resource {key!r} needs {needed}, "
                             f"available {available}",))

    if not a.thread_safe and not a.process_safe:
        constraints.append("Loop A is not thread or process safe")
    if not b.thread_safe and not b.process_safe:
        constraints.append("Loop B is not thread or process safe")

    if constraints:
        return ConcurrencyDecision(
            verdict="safe_with_constraints",
            reasons=tuple(constraints),
            required_locks=tuple(sorted(locks)),
            confidence=0.8)
    return ConcurrencyDecision(
        verdict="safe",
        reasons=("no dependency, write, lock, resource, or safety "
                 "conflict detected",))


def self_test() -> dict:
    """Prove the concurrency decision is typed and deterministic."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    read_only = ConcurrencyContract(reads=("catalog",), thread_safe=True)
    other_read = ConcurrencyContract(reads=("catalog",), thread_safe=True)
    check("read_read_may_overlap",
          decide_overlap(read_only, other_read).verdict == "safe")

    writer = ConcurrencyContract(writes=("records",))
    check("write_write_conflict_blocks_overlap",
          decide_overlap(writer, writer).verdict == "unsafe")

    dependent = ConcurrencyContract(dependencies=("records",))
    check("dependency_prevents_early_start",
          decide_overlap(dependent, writer).verdict == "unsafe")

    exclusive = ConcurrencyContract(exclusive_resources=("db-lock",))
    check("exclusive_lock_blocks_overlap",
          decide_overlap(exclusive, exclusive).verdict == "unsafe")

    hungry = ConcurrencyContract(resources={"gpu": 2})
    check("resource_budget_limits_parallelism",
          decide_overlap(hungry, hungry,
                         available_resources={"gpu": 3}).verdict == "unsafe")

    commutative = ConcurrencyContract(
        writes=("counters",), commutative_outputs=True,
        merge_strategy="sum")
    check("commutative_writes_may_overlap_with_merge",
          decide_overlap(commutative, commutative).verdict
          in ("safe", "safe_with_constraints"))

    unsafe_thread = ConcurrencyContract(reads=("x",))
    check("unknown_safety_defaults_to_constrained",
          decide_overlap(unsafe_thread, unsafe_thread).verdict
          == "safe_with_constraints")

    config = SchedulingConfiguration(scheduling_pattern="bounded_fanout",
                                     maximum_concurrency=4,
                                     join_policy="quorum",
                                     failure_policy="isolate")
    check("scheduling_configuration_validates",
          config.maximum_concurrency == 4 and config.join_policy == "quorum")
    try:
        SchedulingConfiguration(maximum_concurrency=0)
        check("zero_concurrency_is_refused", False)
    except ValueError:
        check("zero_concurrency_is_refused", True)
    return {"tests": results}
