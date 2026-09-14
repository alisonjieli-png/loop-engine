"""Offline checks for the stage store: observation credit, degradation,
ranking by situation, motif, and shape, persistence, and refusals of
malformed rows. Split out of stage_store at the module size cap; no
provider is contacted.
"""
from __future__ import annotations

import json
import os

from .stage_store import BY_MOTIF, BY_SHAPE, BY_SIGNATURE, HELPED, UNKNOWN, StageStore
from . import stage_store_records as _records


def run_checks() -> dict:
    """Offline checks. No provider is contacted."""
    import tempfile

    from .stage_fingerprint import SemanticStageFingerprint

    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    def stage(responsibility, phase="execution", **fields):
        return SemanticStageFingerprint(
            semantic_responsibility=responsibility, cognitive_phase=phase,
            knowns=("schema",), **fields)

    store = StageStore()
    billing = stage("clean the billing extract")
    telemetry = stage("normalise the telemetry stream")
    store.add(billing, run_id="r1", response_shape="record",
              local_verification=True)
    store.add(telemetry, run_id="r2", response_shape="record",
              local_verification=True)

    found = {item.found_by: item for item in store.lookup(stage(
        "scrub the invoice feed"))}
    check("an unrelated pipeline's stage is found by shape",
          BY_SHAPE in found and found[BY_SHAPE].occurrences == 2,
          "billing and telemetry both match a third domain by shape alone")
    check("a stage nobody has seen exactly is not offered as exact",
          BY_SIGNATURE not in found)

    repeat = {item.found_by: item for item in store.lookup(billing)}
    check("the same situation again is found by signature",
          BY_SIGNATURE in repeat and repeat[BY_SIGNATURE].occurrences == 1,
          "a signature match is the same situation, not the same activation")
    check("every level is returned, not only the strongest",
          set(repeat) == {BY_SIGNATURE, BY_MOTIF, BY_SHAPE},
          "a caller needs to see one exact against two by shape")

    check("outcomes travel with the candidate",
          repeat[BY_SHAPE].known_outcomes == 2
          and repeat[BY_SHAPE].helped == 2)
    check("a match reports counts rather than a rate",
          "occurrences" in repeat[BY_SHAPE].to_dict()
          and "rate" not in json.dumps(repeat[BY_SHAPE].to_dict()),
          "two of three and two hundred of three hundred are different")

    own_run = store.lookup(billing, exclude_run="r1")
    check("a run can exclude its own earlier stages",
          all(item.found_by != BY_SIGNATURE for item in own_run))

    unknown = StageStore()
    unseen = unknown.add(stage("do a new thing"), run_id="r3")
    match = unknown.lookup(stage("do a new thing"))[0]
    check("an occurrence with no outcome yet is not counted as helping",
          match.known_outcomes == 0 and match.helped == 0)
    duplicate_refused = False
    try:
        unknown.add(stage("do it again"), run_id="r3",
                    occurrence_id=unseen.occurrence_id)
    except ValueError:
        duplicate_refused = True
    check("duplicate exact occurrence identity is refused",
          duplicate_refused and len(unknown.observations) == 1)

    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "nested", "stages.jsonl")
        writing = StageStore(path=path)
        writing.add(billing, run_id="r1")
        writing.add(telemetry, run_id="r2")
        wrote = writing.close_run(helped=True)
        check("nothing is written until the run's outcome is known",
              wrote == 2,
              "an unresolved row cannot be told from one that finished unknown")
        reading = StageStore(path=path)
        rows = reading.load()
        check("a shape survives serialisation as an indexable key",
              _records.hashable(json.loads(json.dumps(list(billing.shape))))
              == tuple(billing.shape),
              "JSON has no tuples, and an unhashable shape indexes nothing")
        check("what was written comes back", rows == 2
              and reading.to_dict()["distinct_situations"] == 2)
        restored = {item.found_by: item
                    for item in reading.lookup(billing)}
        check("run closure does not invent stage-local outcomes",
              restored[BY_SHAPE].known_outcomes == 0
              and restored[BY_SHAPE].helped == 0,
              "a successful run is context, not stage credit")

    unwritable = StageStore(path="/proc/definitely/not/writable/x.jsonl")
    unwritable.add(billing, run_id="r9")
    wrote = unwritable.close_run(helped=True)
    check("a store that cannot persist does not fail the run",
          len(unwritable.observations) == 1
          and unwritable.observations[0].helped is None and wrote == 0)
    broken = unwritable.to_dict()
    check("a store that lost evidence says so",
          broken["degraded"] and broken["write_failures"] == 1
          and broken["last_storage_error"]
          and broken["degradation_events"][0]["replay_required"],
          "an empty history and a broken recorder need opposite responses")
    check("a healthy store is not marked degraded",
          not StageStore().to_dict()["degraded"])

    closing = StageStore()
    closing.add(billing, run_id="r1")
    failed = closing.add(telemetry, run_id="r2")
    closing.observe(failed, local_verification=False)
    closing.close_run(helped=True)
    check("closing does not overwrite an outcome already known",
          [item.helped for item in closing.observations] == [None, False],
          "a stage that already failed is not relabelled by the run")

    # --- credit is per stage, not per run -------------------------------
    from .outcome_vector import HURT, NEUTRAL, RUN, STAGE

    graded = StageStore()
    carried = graded.add(stage("build the submission"), run_id="r9")
    wasted = graded.add(stage("try a second encoder"), run_id="r9")
    graded.observe(carried, local_verification=True, branch_contribution=True)
    graded.observe(wasted, local_verification=True, branch_contribution=False)
    graded.close_run(True)

    kept, spent = graded.observations
    check("a run's fate does not erase what was seen inside it",
          kept.outcome.local_verification is True
          and kept.outcome.task_outcome is True,
          "close_run used to overwrite every stage with one boolean")
    check("work that carried the run reads as helped",
          kept.outcome.credit == HELPED and kept.helped is True)
    check("a wasted loop inside a winning run is neutral, not helped",
          spent.outcome.credit == NEUTRAL,
          "this is the row that used to be labelled helped and trained on")
    check("both stages of one run can now disagree",
          kept.outcome.credit != spent.outcome.credit,
          "a run-level boolean made this impossible by construction")

    losing = StageStore()
    sound = losing.add(stage("diagnose the failing join"), run_id="r10")
    losing.observe(sound, local_verification=True, branch_contribution=True)
    losing.close_run(False)
    check("good work inside a failed run is not marked harmful",
          losing.observations[0].outcome.credit == HELPED,
          "the losing run used to poison every decision it contained")

    check("observing a stage updates the copy the indexes hold",
          graded._by_digest[spent.digest][0].outcome.credit == NEUTRAL,
          "a second copy left behind is the drift this store must not have")

    check("the store has no pass-wide grading operation",
          not hasattr(StageStore, "observe_pass"),
          "one pass verdict cannot establish every stage's local outcome")

    admitted_wrong = StageStore()
    wrong = admitted_wrong.add(stage("draft an unchecked answer"), run_id="r12")
    admitted_wrong.observe(wrong, output_admitted=True)
    admitted_wrong.close_run(True)
    check("admission and run success still leave contribution unknown",
          admitted_wrong.observations[0].helped is None
          and admitted_wrong.observations[0].outcome.credit == UNKNOWN,
          "schema validity and run success are not stage verification")

    stale = StageStore()
    original = stale.add(stage("diagnose one failing join"), run_id="r13")
    after_admission = stale.observe(original, output_admitted=True)
    after_verification = stale.observe(original, local_verification=True)
    check("a stale immutable handle updates the newest stored outcome",
          after_verification.outcome.output_admitted is True
          and after_verification.outcome.local_verification is True
          and stale.observations[0] == after_verification,
          "an older handle must not overwrite evidence added after it")
    stale.observe(after_admission, later_invalidated=True)
    check("later invalidation survives a stale-handle update",
          stale.observations[0].outcome.local_verification is True
          and stale.observations[0].outcome.later_invalidated is True
          and stale.observations[0].outcome.credit == HURT)

    from types import SimpleNamespace
    attempt = SimpleNamespace(
        route="fixture.route", loop_id="model-attempt-1",
        input_tokens=13, output_tokens=5, elapsed_seconds=0.125)
    gateway_result = SimpleNamespace(
        route="fixture.route", provider="fixture", model="fixture-model",
        attempts=[attempt])
    stale.record_execution(original, [gateway_result])
    execution = stale.observations[0]
    check("actual gateway facts join to the exact occurrence",
          execution.model_route == "fixture.route"
          and execution.model_provider == "fixture"
          and execution.model_name == "fixture-model"
          and execution.gateway_calls == 1 and execution.model_calls == 1
          and execution.model_attempt_loop_ids == ("model-attempt-1",)
          and execution.input_tokens == 13 and execution.output_tokens == 5
          and execution.elapsed_seconds == 0.125)
    retry_attempt = SimpleNamespace(
        route="fallback.route", provider="fixture-two", model="fixture-two",
        loop_id="model-attempt-2", input_tokens=7, output_tokens=2,
        elapsed_seconds=0.075)
    stale.record_execution(original, [
        gateway_result,
        SimpleNamespace(route="fallback.route", provider="fixture-two",
                        model="fixture-two", attempts=[retry_attempt]),
    ])
    retried = stale.observations[0]
    check("several gateway calls keep distinct physical attempt identities",
          retried.gateway_calls == 2 and retried.model_calls == 2
          and retried.model_attempt_loop_ids
          == ("model-attempt-1", "model-attempt-2")
          and retried.model_routes
          == ("fixture.route", "fallback.route")
          and retried.input_tokens == 20 and retried.output_tokens == 7
          and retried.elapsed_seconds == 0.2)
    unknown_usage_attempt = SimpleNamespace(
        route="fixture.route", loop_id="model-attempt-3",
        input_tokens=None, output_tokens=None, elapsed_seconds=0.1)
    stale.record_execution(original, [SimpleNamespace(
        route="", provider="", model="", attempts=[unknown_usage_attempt])])
    check("missing provider usage remains unknown rather than zero",
          stale.observations[0].input_tokens is None
          and stale.observations[0].output_tokens is None)

    preflight_store = StageStore()
    preflight_stage = preflight_store.add(
        stage("refuse before provider use"), run_id="r-preflight")
    preflight_store.record_execution(preflight_stage, [SimpleNamespace(
        route="", provider="", model="", attempts=[SimpleNamespace(
            route="blocked.route", loop_id="", input_tokens=None,
            output_tokens=None, elapsed_seconds=0.0)])])
    check("effect_free_preflight_rows_are_not_physical_model_calls",
          preflight_store.observations[0].model_calls == 0
          and not preflight_store.observations[0].model_attempt_loop_ids
          and preflight_store.observations[0].elapsed_seconds is None)

    # --- migration: an old corpus must not claim credit it never had -----
    with tempfile.TemporaryDirectory() as folder:
        legacy = os.path.join(folder, "old.jsonl")
        with open(legacy, "w", encoding="utf-8") as handle:
            handle.write("not-json\n")
            handle.write(json.dumps({
                "digest": "d1", "motif": "m1", "shape": ["a"],
                "responsibility": "clean the extract", "run_id": "old",
                "helped": True}) + "\n")
        old = StageStore(path=legacy)
        check("a row written before the vector existed still loads",
              old.load() == 1)
        check("an unreadable row is visible without retaining its body",
              old.unreadable_rows == 1 and old.to_dict()["degraded"]
              and old.degradation_events[0]["operation"] == "decode"
              and "not-json" not in json.dumps(old.degradation_events))
        restored = old.observations[0]
        check("an old boolean is restored as run-level evidence only",
              restored.outcome.granularity == RUN
              and restored.outcome.local_verification is None,
              "an old corpus must not claim stage credit it never had")
        check("the old run boolean is not exposed as stage training credit",
              restored.helped is None,
              "legacy run success remains available in outcome.task_outcome")

        fresh = os.path.join(folder, "new.jsonl")
        writing = StageStore(path=fresh)
        one = writing.add(stage("write the report"), run_id="r11")
        writing.observe(one, local_verification=True, downstream_use=True)
        disputed = writing.add(stage("review the disputed result"),
                                run_id="r11")
        disputed = writing.observe(disputed, local_verification=True)
        writing.observe(disputed, local_verification=False)
        writing.close_run(True)
        back = StageStore(path=fresh)
        back.load()
        check("a vector round-trips through the file",
              back.observations[0].outcome.granularity == STAGE
              and back.observations[0].outcome.downstream_use is True)
        check("outcome contradictions survive the v2 round trip",
              back.observations[1].outcome.contradictions
              == ("local_verification",)
              and back.observations[1].outcome.credit == UNKNOWN)

        previous = os.path.join(folder, "previous-v2.jsonl")
        previous_row = writing.observations[0].to_dict()
        previous_row["record_type"] = "stage_observation/v2"
        current_outcome = previous_row["outcome"]
        legacy_names = (
            "output_admitted", "local_verification", "downstream_use",
            "branch_contribution", "later_invalidated", "task_outcome")
        previous_row["outcome"] = {
            "record_type": "outcome_vector/v1",
            "credit": current_outcome["credit"],
            "granularity": current_outcome["granularity"],
            "known": [name for name in current_outcome["known"]
                      if name in legacy_names],
            "unknown": [name for name in current_outcome["unknown"]
                        if name in legacy_names],
            "contradictions": [
                name for name in current_outcome["contradictions"]
                if name in legacy_names],
            "reading": current_outcome["reading"],
            **{name: current_outcome[name] for name in legacy_names},
        }
        with open(previous, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(previous_row) + "\n")
        migrated = StageStore(path=previous)
        check("stage_v2_and_outcome_vector_v1_migrate_without_new_claims",
              migrated.load() == 1
              and migrated.observations[0].outcome.local_verification is True
              and migrated.observations[0].outcome.observable_process_aligned
              is None
              and migrated.observations[0].outcome.continuation_available
              is None)

        malformed = os.path.join(folder, "malformed-v2.jsonl")
        with open(malformed, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "record_type": "unrelated_record/v99",
                "outcome": {"local_verification": "false"}}) + "\n")
            bad = writing.observations[0].to_dict()
            bad["outcome"]["local_verification"] = "false"
            handle.write(json.dumps(bad) + "\n")
        rejected = StageStore(path=malformed)
        check("unknown_and_ill_typed_v2_rows_cannot_create_credit",
              rejected.load() == 0 and rejected.unreadable_rows == 2
              and not rejected.observations)

    check("an unknown signal name is refused rather than dropped",
          _records.refuses_unknown_signal(graded, kept))

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "stage_store_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
