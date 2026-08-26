"""Focused durability checks for the approval state store.

The fixtures cover restart, stale state, concurrent consumption, integrity,
and digest-safe local persistence without executing an effect.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor

from .approval_state_store import (
    ApprovalStateConflict, ApprovalStateIntegrityError,
    LocalJsonApprovalStateStore)
from .effect_approval import (
    ApprovalDecision, ApprovalRequest, ApprovalStatus, EffectApprovalService,
    EffectClass, EffectSpec)
from .recursive_loop import Loop, LoopConfig, LoopLedger
from ..core.runtime_observer import RuntimeObservationServices


class _OrderingStore:
    """Record whether each persistence call followed a service Loop init."""

    def __init__(self, delegate, ledger):
        self.delegate = delegate
        self.ledger = ledger
        self.calls: list[tuple[str, int]] = []

    def _mark(self, name: str) -> None:
        count = sum(event.get("event") == "init"
                    for event in self.ledger.events)
        self.calls.append((name, count))

    def create(self, state):
        self._mark("create")
        return self.delegate.create(state)

    def load(self, request_id):
        self._mark("load")
        return self.delegate.load(request_id)

    def compare_and_swap(self, expected, replacement):
        self._mark("compare_and_swap")
        return self.delegate.compare_and_swap(expected, replacement)


def run_checks() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    with tempfile.TemporaryDirectory(prefix="loop-engine-approval-store-") as root:
        store_one = LocalJsonApprovalStateStore(root)
        store_two = LocalJsonApprovalStateStore(root)
        effect = EffectSpec(
            EffectClass.LOCAL_WRITE, "write", "workspace:test:file:a.txt",
            (("content_digest", "a" * 64),))
        request = ApprovalRequest(
            "approval/restart unsafe id", "loop_store", effect,
            "Write one reviewed file.")
        runtime = RuntimeObservationServices(ledger=LoopLedger())
        first = EffectApprovalService(runtime, store_one)
        checkpoint = first.create(request)
        decided = first.resume(
            checkpoint.pending, checkpoint.resume_token,
            ApprovalDecision.approve(request.request_id, "reviewer"))

        path = store_one.object_path(request.request_id)
        digest_name = path.stem
        check("local_store_uses_only_a_digest_safe_filename",
              len(digest_name) == 64
              and all(char in "0123456789abcdef" for char in digest_name)
              and request.request_id not in str(path)
              and path.exists())
        check("local_store_uses_process_locking_when_the_platform_supports_it",
              isinstance(store_one.process_locking_supported, bool))

        restarted = EffectApprovalService(runtime, store_two)
        restored = restarted.state(request.request_id)
        consumed = restarted.consume(request.request_id, effect)
        check("decided_state_survives_restart_and_advances_by_compare_and_swap",
              restored == decided
              and consumed.status is ApprovalStatus.CONSUMED
              and consumed.state_revision == 2)

        stale_failed = False
        try:
            store_one.compare_and_swap(decided, consumed)
        except ApprovalStateConflict:
            stale_failed = True
        replay_failed = False
        after_restart = EffectApprovalService(
            runtime, LocalJsonApprovalStateStore(root))
        try:
            after_restart.consume(request.request_id, effect)
        except RuntimeError:
            replay_failed = True
        check("stale_and_restarted_consumers_cannot_reuse_consumed_state",
              stale_failed and replay_failed)

        duplicate_failed = False
        try:
            EffectApprovalService(
                runtime, LocalJsonApprovalStateStore(root)).create(request)
        except ApprovalStateConflict:
            duplicate_failed = True
        check("duplicate_request_id_cannot_create_a_second_effect_path",
              duplicate_failed)

        concurrent_request = ApprovalRequest(
            "approval_concurrent_store", "loop_store", effect,
            "Consume one decision across two services.")
        concurrent_owner = EffectApprovalService(runtime, store_one)
        concurrent_checkpoint = concurrent_owner.create(concurrent_request)
        concurrent_owner.resume(
            concurrent_checkpoint.pending, concurrent_checkpoint.resume_token,
            ApprovalDecision.approve(
                concurrent_request.request_id, "reviewer"))
        service_a = EffectApprovalService(
            runtime, LocalJsonApprovalStateStore(root))
        service_b = EffectApprovalService(
            runtime, LocalJsonApprovalStateStore(root))

        def consume_once(service):
            try:
                return service.consume(
                    concurrent_request.request_id, effect).status.value
            except (RuntimeError, ApprovalStateConflict):
                return "refused"

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = tuple(workers.map(
                consume_once, (service_a, service_b)))
        check("two_services_cannot_consume_the_same_revision_twice",
              sorted(outcomes) == ["consumed", "refused"])

        process_request = ApprovalRequest(
            "approval_process_store", "loop_store", effect,
            "Consume one decision across two processes.")
        process_owner = EffectApprovalService(runtime, store_one)
        process_checkpoint = process_owner.create(process_request)
        process_decided = process_owner.resume(
            process_checkpoint.pending, process_checkpoint.resume_token,
            ApprovalDecision.approve(process_request.request_id, "reviewer"))
        process_consumed = process_decided.consume(
            process_request.request_id, effect)
        process_lock_passed = True
        if store_one.process_locking_supported:
            import multiprocessing
            context = multiprocessing.get_context("fork")
            start = context.Event()
            outcomes_queue = context.Queue()
            workers = [context.Process(
                target=_process_compare_and_swap,
                args=(root, process_decided.to_json(),
                      process_consumed.to_json(), start, outcomes_queue))
                for _index in range(2)]
            for worker in workers:
                worker.start()
            start.set()
            process_outcomes = sorted(
                outcomes_queue.get(timeout=5) for _index in range(2))
            for worker in workers:
                worker.join(timeout=5)
            process_lock_passed = (
                process_outcomes == ["conflict", "stored"]
                and all(worker.exitcode == 0 for worker in workers))
        check("process_lock_allows_only_one_compare_and_swap",
              process_lock_passed)

        changed_request_failed = False
        try:
            other_request = ApprovalRequest(
                "approval_other", "loop_store", effect,
                "Different request.")
            other_checkpoint = EffectApprovalService(runtime).create(
                other_request)
            store_one.compare_and_swap(
                consumed, other_checkpoint.pending)
        except ApprovalStateConflict:
            changed_request_failed = True
        check("compare_and_swap_refuses_a_changed_request_id",
              changed_request_failed)

        envelope = json.loads(path.read_text(encoding="utf-8"))
        envelope["state"]["request"]["request_id"] = "approval_tampered"
        canonical_state = json.dumps(
            envelope["state"], sort_keys=True, separators=(",", ":"),
            ensure_ascii=False)
        envelope["state_digest"] = hashlib.sha256(
            canonical_state.encode("utf-8")).hexdigest()
        path.write_text(json.dumps(
            envelope, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False), encoding="utf-8")
        tamper_failed = False
        try:
            store_one.load(request.request_id)
        except (ApprovalStateIntegrityError, ValueError):
            tamper_failed = True
        check("changed_stored_request_fails_integrity_validation",
              tamper_failed)

        temporary_files = [
            item for item in path.parent.iterdir()
            if item.name.startswith(f".{path.stem}.")]
        check("atomic_replace_leaves_no_partial_state_file",
              not temporary_files)

    with tempfile.TemporaryDirectory(
            prefix="loop-engine-approval-loop-order-") as root:
        loop_ledger = LoopLedger()
        ordered_store = _OrderingStore(
            LocalJsonApprovalStateStore(root), loop_ledger)
        loop_runtime = RuntimeObservationServices(ledger=loop_ledger)
        loop_service = EffectApprovalService(loop_runtime, ordered_store)
        loop_effect = EffectSpec(
            EffectClass.LOCAL_WRITE, "write", "workspace:loop:file:a.txt")
        loop_request = ApprovalRequest(
            "approval_loop_relationship", "requesting_loop", loop_effect,
            "Verify one approval service Loop.")
        loop_checkpoint = loop_service.create(loop_request)
        loop_service.state(loop_request.request_id)
        loop_service.serialize(loop_request.request_id)
        loop_decided = loop_service.resume(
            loop_checkpoint.pending, loop_checkpoint.resume_token,
            ApprovalDecision.approve(loop_request.request_id, "reviewer"))
        loop_consumed = loop_service.consume(
            loop_request.request_id, loop_effect)
        loop_service.restore(loop_consumed)
        loop_service.restore_json(loop_consumed.to_json())
        init_events = [event for event in loop_ledger.events
                       if event.get("event") == "init"]
        terminal_ids = {event["loop_id"] for event in loop_ledger.events
                        if event.get("event") == "terminal"}
        check("approval_public_operations_are_terminal_starting_verifier_loops",
              len(init_events) == 7
              and all(event.get("relationship_kind") == "starting"
                      and event.get("role") == "practitioner"
                      and event.get("profile_id") == "practitioner.verifier"
                      and len(event.get("input_roles", ())) == 1
                      and len(event.get("output_roles", ())) == 1
                      and event["loop_id"] in terminal_ids
                      for event in init_events))
        check("approval_store_calls_begin_only_after_the_owning_loop_init",
              bool(ordered_store.calls)
              and tuple(count for _name, count in ordered_store.calls)
              == (1, 2, 3, 4, 4, 5, 5, 6, 7))
        check("approval_loop_envelopes_preserve_one_use_consumption",
              loop_decided.status is ApprovalStatus.DECIDED
              and loop_service._states[loop_request.request_id].status
              is ApprovalStatus.CONSUMED)

    spawned_ledger = LoopLedger()
    parent = Loop(
        "own approval spawned operations",
        LoopConfig(allowable_modes=("deterministic",),
                   preferred_modes=("deterministic",),
                   delegated_modes=("deterministic",)),
        ledger=spawned_ledger)
    spawned_service = EffectApprovalService(RuntimeObservationServices(
        parent=parent, ledger=spawned_ledger))
    spawned_service.create(ApprovalRequest(
        "approval_spawned_relationship", parent.loop_id,
        EffectSpec(EffectClass.LOCAL_READ, "read", "workspace:spawned:file"),
        "Verify spawned relationship."))
    spawned_init = [event for event in spawned_ledger.events
                  if event.get("event") == "init"][-1]
    check("approval_service_uses_spawned_relationship_when_dynamically_owned",
          spawned_init.get("relationship_kind") == "spawned_by"
          and spawned_init.get("spawned_by_loop_id") == parent.loop_id
          and spawned_init.get("profile_id") == "practitioner.verifier"
          and any(event.get("event") == "terminal"
                  and event.get("loop_id") == spawned_init["loop_id"]
                  for event in spawned_ledger.events))

    passed = sum(1 for test in tests if test["passed"])
    return {
        "tests": tests,
        "passed": passed,
        "total": len(tests),
        "all_passed": passed == len(tests),
    }


def _process_compare_and_swap(root: str, expected_json: str,
                              replacement_json: str, start, output) -> None:
    from .effect_approval import PendingApprovalState
    store = LocalJsonApprovalStateStore(root)
    expected = PendingApprovalState.from_json(expected_json)
    replacement = PendingApprovalState.from_json(replacement_json)
    start.wait(timeout=5)
    try:
        store.compare_and_swap(expected, replacement)
    except ApprovalStateConflict:
        output.put("conflict")
    else:
        output.put("stored")
