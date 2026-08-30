"""Parallel and async execution through the canonical Loop runtime.

The scheduling contracts (ConcurrencyContract, SchedulingConfiguration,
ConcurrencyDecision) declare safety. This module executes: bounded
parallel branches, join policies, failure policies, and the async child
lifecycle with no orphaned tasks.

Every branch is an ordinary Loop. Parallelism changes scheduling, not
ontology. There is no ParallelNode and no second engine.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from .scheduling import (ConcurrencyContract, ConcurrencyDecision,
                         FailurePolicy, JoinPolicy,
                         SchedulingConfiguration, decide_overlap)


class ParallelExecutionError(RuntimeError):
    """A parallel execution violated its declared contract."""


@dataclass(frozen=True)
class BranchSpec:
    """One parallel branch: a callable plus its concurrency contract."""

    branch_id: str
    fn: object
    contract: ConcurrencyContract = field(
        default_factory=ConcurrencyContract)
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class BranchResult:
    """Typed result of one parallel branch."""

    branch_id: str
    ok: bool
    value: object = None
    error: str = ""

    def to_dict(self) -> dict:
        return {"branch_id": self.branch_id, "ok": self.ok,
                "value": self.value, "error": self.error}


@dataclass(frozen=True)
class ParallelOutcome:
    """Typed outcome of one parallel execution."""

    results: tuple[BranchResult, ...]
    join_policy: JoinPolicy
    failure_policy: FailurePolicy
    succeeded: bool
    selected: tuple[BranchResult, ...] = ()
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {"results": [r.to_dict() for r in self.results],
                "join_policy": self.join_policy.value,
                "failure_policy": self.failure_policy.value,
                "succeeded": self.succeeded,
                "selected": [r.to_dict() for r in self.selected],
                "elapsed_seconds": self.elapsed_seconds}


def _check_pairwise_safety(branches: tuple[BranchSpec, ...]) -> list[str]:
    """Refuse overlapping branches whose contracts conflict."""
    problems = []
    for i, left in enumerate(branches):
        for right in branches[i + 1:]:
            decision = decide_overlap(left.contract, right.contract)
            if decision.verdict == "unsafe":
                problems.append(
                    f"{left.branch_id} and {right.branch_id} cannot "
                    f"overlap: {'; '.join(decision.reasons)}")
    return problems


def _apply_join(results: tuple[BranchResult, ...], policy: JoinPolicy,
                quorum: int = 1) -> tuple[bool, tuple[BranchResult, ...]]:
    """Apply one join policy to branch results."""
    ok_results = tuple(r for r in results if r.ok)
    if policy is JoinPolicy.ALL:
        return all(r.ok for r in results), ok_results
    if policy is JoinPolicy.QUORUM:
        return len(ok_results) >= quorum, ok_results
    if policy is JoinPolicy.FIRST_SUCCESS:
        return bool(ok_results), ok_results[:1]
    if policy is JoinPolicy.ENSEMBLE:
        return bool(ok_results), ok_results
    raise ParallelExecutionError(f"unknown join policy {policy!r}")


def run_parallel(branches: tuple[BranchSpec, ...], *,
                 config: SchedulingConfiguration | None = None,
                 quorum: int = 1) -> ParallelOutcome:
    """Execute branches in parallel with declared safety and join policy.

    Pairwise contract conflicts refuse execution before any branch
    runs. Failure policy fail_fast stops remaining branches on the
    first failure; isolate collects every failure.
    """
    config = config or SchedulingConfiguration(
        scheduling_pattern="bounded_fanout",
        maximum_concurrency=len(branches) or 1,
        join_policy="all", failure_policy="fail_fast")
    if not branches:
        return ParallelOutcome(results=(), join_policy=config.join_policy,
                              failure_policy=config.failure_policy,
                              succeeded=True)
    conflicts = _check_pairwise_safety(branches)
    if conflicts:
        raise ParallelExecutionError("; ".join(conflicts))

    started = time.monotonic()
    results: list[BranchResult] = []
    failed = False

    async def _run_all() -> None:
        nonlocal failed
        semaphore = asyncio.Semaphore(config.maximum_concurrency)

        async def _one(branch: BranchSpec) -> None:
            nonlocal failed
            async with semaphore:
                if failed and config.failure_policy is FailurePolicy.FAIL_FAST:
                    results.append(BranchResult(
                        branch.branch_id, False, error="skipped: fail_fast"))
                    return
                try:
                    if branch.contract.thread_safe:
                        value = await asyncio.to_thread(
                            branch.fn, *branch.args, **branch.kwargs)
                    else:
                        value = branch.fn(*branch.args, **branch.kwargs)
                    results.append(BranchResult(branch.branch_id, True,
                                                value=value))
                except Exception as exc:                      # noqa: BLE001
                    results.append(BranchResult(
                        branch.branch_id, False,
                        error=f"{type(exc).__name__}: {exc}"))
                    if config.failure_policy is FailurePolicy.FAIL_FAST:
                        failed = True

        await asyncio.gather(*(_one(b) for b in branches))

    asyncio.run(_run_all())
    elapsed = time.monotonic() - started
    ordered = tuple(sorted(results, key=lambda r: r.branch_id))
    succeeded, selected = _apply_join(ordered, config.join_policy, quorum)
    return ParallelOutcome(results=ordered,
                           join_policy=config.join_policy,
                           failure_policy=config.failure_policy,
                           succeeded=succeeded, selected=selected,
                           elapsed_seconds=round(elapsed, 3))


def run_parallel_through_loop(branches: tuple[BranchSpec, ...], *,
                             config: SchedulingConfiguration | None = None,
                             quorum: int = 1,
                             parent=None, ledger=None) -> dict:
    """Run a parallel execution as one governed deterministic Loop."""
    from .loop.encapsulate import as_practitioner_loop

    def _run(_inputs=None) -> dict:
        outcome = run_parallel(branches, config=config, quorum=quorum)
        return outcome.to_dict()

    return as_practitioner_loop("parallel branch execution", _run,
                                parent=parent, ledger=ledger)


def self_test() -> dict:
    """Prove parallel execution is safe, joined, and Loop-governed."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def _slow(value: float, delay: float = 0.01) -> float:
        time.sleep(delay)
        return value

    read_only = ConcurrencyContract(reads=("catalog",), thread_safe=True)
    branches = tuple(BranchSpec(
        f"b{i}", _slow, contract=read_only, args=(float(i),))
        for i in range(3))
    outcome = run_parallel(branches)
    check("parallel_branches_all_succeed",
          outcome.succeeded and len(outcome.results) == 3
          and all(r.ok for r in outcome.results))

    import threading
    barrier = threading.Barrier(3, timeout=1.0)
    thread_ids = set()
    thread_lock = threading.Lock()

    def _meet(value):
        with thread_lock:
            thread_ids.add(threading.get_ident())
        barrier.wait()
        return value

    overlapping = run_parallel(tuple(BranchSpec(
        f"overlap-{index}", _meet, contract=read_only, args=(index,))
        for index in range(3)))
    check("thread_safe_branches_physically_overlap",
          overlapping.succeeded and len(thread_ids) == 3,
          f"worker_threads={len(thread_ids)}")

    config = SchedulingConfiguration(scheduling_pattern="bounded_fanout",
                                     maximum_concurrency=2,
                                     join_policy="all",
                                     failure_policy="isolate")
    outcome = run_parallel(branches, config=config)
    check("bounded_parallel_respects_configuration",
          outcome.succeeded and outcome.join_policy == "all")

    def _fail() -> float:
        raise RuntimeError("boom")

    failing = (BranchSpec("ok", _slow, contract=read_only, args=(1.0,)),
                BranchSpec("bad", _fail, contract=read_only))
    isolated = run_parallel(failing, config=SchedulingConfiguration(
        scheduling_pattern="bounded_fanout", maximum_concurrency=2,
        join_policy="all", failure_policy="isolate"))
    check("isolate_policy_collects_failures",
          not isolated.succeeded
          and any(not r.ok and "boom" in r.error
                  for r in isolated.results)
          and any(r.ok for r in isolated.results))

    # With concurrency 1, the failing branch runs first and the
    # remaining branches are genuinely skipped by fail_fast.
    three = (BranchSpec("bad", _fail, contract=read_only),
             BranchSpec("ok1", _slow, contract=read_only, args=(1.0,)),
             BranchSpec("ok2", _slow, contract=read_only, args=(2.0,)))
    fast = run_parallel(three, config=SchedulingConfiguration(
        scheduling_pattern="bounded_fanout", maximum_concurrency=1,
        join_policy="all", failure_policy="fail_fast"))
    check("fail_fast_skips_remaining_branches",
          not fast.succeeded
          and any("skipped" in r.error for r in fast.results))

    writer_a = ConcurrencyContract(writes=("records",))
    writer_b = ConcurrencyContract(writes=("records",))
    conflicting = (BranchSpec("a", _slow, contract=writer_a, args=(1.0,)),
                   BranchSpec("b", _slow, contract=writer_b, args=(2.0,)))
    try:
        run_parallel(conflicting)
        check("conflicting_writes_are_refused", False)
    except ParallelExecutionError:
        check("conflicting_writes_are_refused", True)

    governed = run_parallel_through_loop(branches)
    check("parallel_execution_runs_through_canonical_loop",
          governed["loop_id"].startswith("loop")
          and governed["value"]["succeeded"])

    quorum_outcome = run_parallel(
        (BranchSpec("ok1", _slow, contract=read_only, args=(1.0,)),
         BranchSpec("ok2", _slow, contract=read_only, args=(2.0,)),
         BranchSpec("bad", _fail, contract=read_only)),
        config=SchedulingConfiguration(
            scheduling_pattern="bounded_fanout", maximum_concurrency=3,
            join_policy="quorum", failure_policy="isolate"),
        quorum=2)
    check("quorum_join_accepts_declared_fraction",
          quorum_outcome.succeeded
          and len(quorum_outcome.selected) == 2)
    return {"tests": results}
