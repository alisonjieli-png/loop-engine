"""Persist stage occurrences and retrieve inspectable similarity candidates.
Signature, motif, and shape remain separate indexes. Results never become
instructions, and exact occurrence identity remains separate from similarity.
An owning Practitioner Loop decides whether to use a match.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

from . import stage_store_records as _records
from .outcome_vector import HELPED, SIGNAL_SCOPES, UNKNOWN, OutcomeVector
from .outcome_vector import observe as observe_outcome

STAGE_OBSERVATION_RECORD_TYPE = "stage_observation/v2"
BY_SIGNATURE, BY_MOTIF, BY_SHAPE = "signature", "motif", "shape"


@dataclass(frozen=True)
class StageObservation:
    """One occurrence of a stage, and what is known about how it went."""

    digest: str
    motif: str
    shape: tuple
    responsibility: str
    run_id: str = ""
    #: Similar stages share ``digest``; occurrences never share this ID.
    occurrence_id: str = ""
    semantic_call_id: str = ""
    owner_loop_id: str = ""
    response_shape: str = ""
    model_route: str = ""
    model_provider: str = ""
    model_name: str = ""
    model_routes: tuple[str, ...] = ()
    model_attempt_loop_ids: tuple[str, ...] = ()
    pass_number: int = 0
    #: Separate local and run signals prevent pass-wide Boolean credit.
    outcome: OutcomeVector = field(default_factory=OutcomeVector)
    gateway_calls: int = 0
    model_calls: int = 0
    elapsed_seconds: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def observation_ref(self) -> str:
        """Stable reference whose identity does not change with outcomes."""
        return "stage-observation:sha256:" + hashlib.sha256(
            self.occurrence_id.encode("utf-8")).hexdigest()

    @property
    def helped(self) -> bool | None:
        """The outcome as one boolean, for callers that can only hold one.

        This lossy compatibility projection is computed from ``outcome``.
        Evidence-aware callers should read the complete vector.
        """
        credit = self.outcome.credit
        if credit == HELPED:
            return True
        return None if credit == UNKNOWN else False

    def to_dict(self) -> dict:
        return {"record_type": STAGE_OBSERVATION_RECORD_TYPE,
                "digest": self.digest, "motif": self.motif,
                "shape": list(self.shape),
                "responsibility": self.responsibility,
                "run_id": self.run_id,
                "occurrence_id": self.occurrence_id,
                "observation_ref": self.observation_ref,
                "semantic_call_id": self.semantic_call_id,
                "owner_loop_id": self.owner_loop_id,
                "response_shape": self.response_shape,
                "model_route": self.model_route,
                "model_provider": self.model_provider,
                "model_name": self.model_name,
                "model_routes": list(self.model_routes),
                "model_attempt_loop_ids": list(
                    self.model_attempt_loop_ids),
                "pass_number": self.pass_number,
                "outcome": self.outcome.to_dict(),
                # Compatibility projection for older readers.
                "helped": self.helped,
                "gateway_calls": self.gateway_calls,
                "model_calls": self.model_calls,
                "elapsed_seconds": self.elapsed_seconds,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "usage_complete": (
                    self.input_tokens is not None
                    and self.output_tokens is not None)}


@dataclass
class StageMatch:
    """A prior stage offered as a candidate, with how it was found."""

    found_by: str
    observations: tuple[StageObservation, ...]

    @property
    def occurrences(self) -> int:
        return len(self.observations)

    @property
    def known_outcomes(self) -> int:
        return sum(1 for item in self.observations if item.helped is not None)

    @property
    def helped(self) -> int:
        return sum(1 for item in self.observations if item.helped)

    def to_dict(self) -> dict:
        return {
            "found_by": self.found_by,
            "occurrences": self.occurrences,
            "known_outcomes": self.known_outcomes,
            "helped": self.helped,
            # Counts preserve the denominator; a bare rate would not.
            "response_shapes": sorted({item.response_shape
                                       for item in self.observations
                                       if item.response_shape}),
            "model_routes": sorted({item.model_route
                                    for item in self.observations
                                    if item.model_route}),
            "responsibilities": sorted({item.responsibility
                                        for item in self.observations})[:5],
        }


@dataclass
class StageStore:
    """Every observed stage, indexed in memory and optionally as JSONL."""

    path: str = ""
    observations: list = field(default_factory=list)
    _by_digest: dict = field(default_factory=dict)
    _by_motif: dict = field(default_factory=dict)
    _by_shape: dict = field(default_factory=dict)
    _by_occurrence: dict = field(default_factory=dict)
    #: Non-fatal loss remains distinguishable from an empty history.
    write_failures: int = 0
    read_failures: int = 0
    unreadable_rows: int = 0
    last_storage_error: str = ""
    degradation_events: list[dict] = field(default_factory=list)

    def add(self, stage, **fields) -> StageObservation:
        """Record one occurrence of a stage.

        Direct outcome signals are folded into the vector. Legacy ``helped``
        means the run outcome and never becomes local credit.
        """
        from .stage_fingerprint import stage_motif
        signals = {name: fields.pop(name) for name in list(fields)
                   if name in SIGNAL_SCOPES}
        if "helped" in fields:
            signals.setdefault("task_outcome", fields.pop("helped"))
        if signals:
            fields["outcome"] = observe_outcome(
                fields.get("outcome") or OutcomeVector(), **signals)
        occurrence_id = str(fields.get("occurrence_id") or "")
        if not occurrence_id:
            occurrence_id = _records.occurrence_id(
                str(fields.get("run_id") or ""), stage.digest,
                len(self.observations))
            fields["occurrence_id"] = occurrence_id
        if occurrence_id in self._by_occurrence:
            raise ValueError(
                f"stage occurrence {occurrence_id!r} is already recorded")
        observation = StageObservation(
            digest=stage.digest, motif=stage_motif(stage),
            shape=tuple(stage.shape),
            responsibility=stage.semantic_responsibility, **fields)
        self._index(observation)
        return observation

    def observe(self, observation: StageObservation,
                **signals) -> StageObservation:
        """Record something newly known about one stage's fate.

        Stale handles resolve to the newest occurrence. Unknown signal names
        raise instead of creating evidence that only appears to be stored.
        """
        from dataclasses import replace as _replace
        current = self._current(observation)
        updated = _replace(
            current, outcome=observe_outcome(current.outcome, **signals))
        self._replace(current, updated)
        return updated

    def record_execution(self, observation: StageObservation,
                         results) -> StageObservation:
        """Join actual gateway and physical-attempt facts to one occurrence.

        Missing usage stays ``None``. Stale handles resolve to the newest
        stored observation before the update.
        """
        from dataclasses import replace as _replace
        current = self._current(observation)
        gateway_results = tuple(results or ())
        all_attempts = tuple(
            attempt for result in gateway_results
            for attempt in tuple(getattr(result, "attempts", ()) or ()))
        # GatewayAttempt also represents effect-free route/preflight refusals.
        # Only an attempt with a model Loop ID crossed the physical provider
        # boundary and may enter call, latency, or token accounting.
        attempts = tuple(
            attempt for attempt in all_attempts
            if str(getattr(attempt, "loop_id", "") or ""))
        routes = _records.unique_text(
            str(getattr(item, "route", "") or "")
                         for item in attempts)
        loop_ids = _records.unique_text(
            str(getattr(item, "loop_id", "") or "")
                           for item in attempts)
        if len(loop_ids) != len(attempts):
            raise ValueError(
                "physical model attempts need distinct non-empty Loop IDs")
        route = next((str(getattr(item, "route", "") or "")
                      for item in reversed(gateway_results)
                      if getattr(item, "route", "")), "") or next((
                          str(getattr(item, "route", "") or "")
                          for item in reversed(attempts)
                          if getattr(item, "route", "")), "")
        provider = next((str(getattr(item, "provider", "") or "")
                         for item in reversed(gateway_results)
                         if getattr(item, "provider", "")), "") or next((
                             str(getattr(item, "provider", "") or "")
                             for item in reversed(attempts)
                             if getattr(item, "provider", "")), "")
        model = next((str(getattr(item, "model", "") or "")
                      for item in reversed(gateway_results)
                      if getattr(item, "model", "")), "") or next((
                          str(getattr(item, "model", "") or "")
                          for item in reversed(attempts)
                          if getattr(item, "model", "")), "")
        elapsed = (round(sum(float(getattr(item, "elapsed_seconds", 0) or 0)
                             for item in attempts), 6)
                   if attempts else None)
        input_tokens = _records.complete_sum(
            getattr(item, "input_tokens", None) for item in attempts)
        output_tokens = _records.complete_sum(
            getattr(item, "output_tokens", None) for item in attempts)
        updated = _replace(
            current,
            model_route=route,
            model_provider=provider,
            model_name=model,
            model_routes=routes,
            model_attempt_loop_ids=loop_ids,
            gateway_calls=len(gateway_results),
            model_calls=len(attempts),
            elapsed_seconds=elapsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens)
        self._replace(current, updated)
        return updated

    def record_response(self, observation: StageObservation,
                        response_shape: str) -> StageObservation:
        """Record the observed output shape without changing outcome credit."""
        from dataclasses import replace as _replace
        current = self._current(observation)
        updated = _replace(current, response_shape=str(response_shape or ""))
        self._replace(current, updated)
        return updated

    def _current(self, observation: StageObservation) -> StageObservation:
        current = self._by_occurrence.get(observation.occurrence_id)
        if current is None:
            raise ValueError(
                f"stage occurrence {observation.occurrence_id!r} is not in "
                "this store")
        return current

    def _index(self, observation: StageObservation) -> None:
        self.observations.append(observation)
        self._by_occurrence[observation.occurrence_id] = observation
        self._by_digest.setdefault(observation.digest, []).append(observation)
        self._by_motif.setdefault(observation.motif, []).append(observation)
        self._by_shape.setdefault(observation.shape, []).append(observation)

    def _replace(self, current: StageObservation,
                 updated: StageObservation) -> None:
        """Replace one exact occurrence in every index."""
        for holder in (self.observations,
                       self._by_digest.get(current.digest),
                       self._by_motif.get(current.motif),
                       self._by_shape.get(current.shape)):
            if not holder:
                continue
            for position, item in enumerate(holder):
                if item.occurrence_id == current.occurrence_id:
                    holder[position] = updated
        self._by_occurrence[current.occurrence_id] = updated

    def close_run(self, helped: bool | None, *, path: str = "") -> int:
        """Tell this run's observations how it ended, then persist them.

        The run outcome is stored beside local evidence and does not replace
        it. Rows are written only when the run closes.
        """
        from dataclasses import replace as _replace
        resolved = [_replace(item, outcome=observe_outcome(
            item.outcome, task_outcome=helped))
            for item in self.observations]
        self.observations = resolved
        for index in (self._by_digest, self._by_motif, self._by_shape,
                      self._by_occurrence):
            index.clear()
        for item in resolved:
            self._by_occurrence[item.occurrence_id] = item
            self._by_digest.setdefault(item.digest, []).append(item)
            self._by_motif.setdefault(item.motif, []).append(item)
            self._by_shape.setdefault(item.shape, []).append(item)
        target = path or self.path
        if not target:
            return 0
        self.path = target
        written = 0
        for item in resolved:
            written += int(self._append(item))
        return written

    def _append(self, observation: StageObservation) -> bool:
        """Write one row through, never failing the caller if it cannot."""
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(observation.to_dict(),
                                        sort_keys=True,
                                        separators=(",", ":")) + "\n")
            return True
        except OSError as exc:
            # A store that cannot persist is a degraded store, not a failed
            # run: the in-memory index still serves this run. The failure is
            # counted rather than swallowed, so a later reader can tell a
            # short history from a broken one.
            self._degrade("write", exc)
            return False

    def load(self) -> int:
        """Read a stored file back into the indexes. Returns rows read."""
        if not self.path or not os.path.isfile(self.path):
            return 0
        read = 0
        try:
            handle = open(  # noqa: SIM115
                self.path, encoding="utf-8", errors="replace")
        except OSError as exc:
            self._degrade("read", exc)
            return 0
        with handle:
            for row_number, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except ValueError:
                    self._unreadable(row_number, "invalid_json")
                    continue
                try:
                    if not isinstance(value, dict):
                        raise ValueError("stage record must be an object")
                    record_type = value.get("record_type")
                    strict_v2 = record_type == STAGE_OBSERVATION_RECORD_TYPE
                    if record_type not in (
                            None, "stage_observation/v1",
                            STAGE_OBSERVATION_RECORD_TYPE):
                        raise ValueError("unsupported stage record type")
                    if strict_v2:
                        _records.validate_v2_record(value)
                    else:
                        _records.validate_legacy_record(value)
                    occurrence_id = str(value.get("occurrence_id") or
                                        _records.legacy_occurrence_id(
                                            self.path, row_number, value))
                    if occurrence_id in self._by_occurrence:
                        raise ValueError("duplicate occurrence identity")
                    observation = StageObservation(
                        digest=value.get("digest", ""),
                        motif=value.get("motif", ""),
                        shape=_records.hashable(value.get("shape") or ()),
                        responsibility=value.get("responsibility", ""),
                        run_id=value.get("run_id", ""),
                        occurrence_id=occurrence_id,
                        semantic_call_id=value.get("semantic_call_id", ""),
                        owner_loop_id=value.get("owner_loop_id", ""),
                        response_shape=value.get("response_shape", ""),
                        model_route=value.get("model_route", ""),
                        model_provider=value.get("model_provider", ""),
                        model_name=value.get("model_name", ""),
                        model_routes=tuple(value.get("model_routes") or ()),
                        model_attempt_loop_ids=tuple(
                            value.get("model_attempt_loop_ids") or ()),
                        pass_number=int(value.get("pass_number") or 0),
                        outcome=_records.outcome_from(
                            value, strict=strict_v2),
                        gateway_calls=int(value.get("gateway_calls") or 0),
                        model_calls=int(value.get("model_calls") or 0),
                        elapsed_seconds=value.get("elapsed_seconds"),
                        input_tokens=value.get("input_tokens"),
                        output_tokens=value.get("output_tokens"))
                    if strict_v2:
                        if value.get("observation_ref") \
                                != observation.observation_ref:
                            raise ValueError(
                                "stage observation reference does not match")
                        if value.get("helped") is not observation.helped:
                            raise ValueError(
                                "stage helped projection does not match outcome")
                        if value.get("usage_complete") is not (
                                observation.input_tokens is not None
                                and observation.output_tokens is not None):
                            raise ValueError(
                                "stage usage completeness does not match tokens")
                        if observation.model_calls != len(
                                observation.model_attempt_loop_ids):
                            raise ValueError(
                                "physical call count does not match Loop IDs")
                except (TypeError, ValueError):
                    self._unreadable(row_number, "invalid_stage_record")
                    continue
                self._index(observation)
                read += 1
        return read

    def _degrade(self, operation: str, exc: OSError) -> None:
        detail = f"{type(exc).__name__}: {exc}"[:200]
        if operation == "write":
            self.write_failures += 1
        else:
            self.read_failures += 1
        self.last_storage_error = detail
        self.degradation_events.append({
            "record_type": "stage_storage_degraded/v1",
            "operation": operation,
            "path": self.path,
            "error": detail,
            "replay_required": operation == "write",
        })

    def _unreadable(self, row_number: int, reason: str) -> None:
        """Record one unreadable row without retaining its possibly private body."""
        self.unreadable_rows += 1
        self.last_storage_error = f"row {row_number}: {reason}"
        self.degradation_events.append({
            "record_type": "stage_storage_degraded/v1",
            "operation": "decode",
            "path": self.path,
            "row_number": row_number,
            "error": reason,
            "replay_required": True,
        })

    def lookup(self, stage, *, exclude_run: str = "") -> tuple:
        """Candidates for this stage, strongest match first.

        Every level is returned rather than only the best, because a caller
        weighing whether to reuse anything needs to see that the exact match
        is one occurrence and the shape match is four hundred.
        """
        from .stage_fingerprint import stage_motif

        def rows(index, key):
            return tuple(item for item in index.get(key, ())
                         if not exclude_run or item.run_id != exclude_run)

        found = []
        for label, index, key in (
                (BY_SIGNATURE, self._by_digest, stage.digest),
                (BY_MOTIF, self._by_motif, stage_motif(stage)),
                (BY_SHAPE, self._by_shape, tuple(stage.shape))):
            matched = rows(index, key)
            if matched:
                found.append(StageMatch(found_by=label, observations=matched))
        return tuple(found)

    def to_dict(self) -> dict:
        return {"record_type": "stage_store/v1",
                "degraded": bool(self.write_failures or self.read_failures
                                 or self.unreadable_rows),
                "write_failures": self.write_failures,
                "read_failures": self.read_failures,
                "unreadable_rows": self.unreadable_rows,
                "last_storage_error": self.last_storage_error,
                "degradation_events": list(self.degradation_events),
                "observations": len(self.observations),
                "distinct_situations": len(self._by_digest),
                "distinct_motifs": len(self._by_motif),
                "distinct_shapes": len(self._by_shape),
                "path": self.path}


def self_test() -> dict:
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
