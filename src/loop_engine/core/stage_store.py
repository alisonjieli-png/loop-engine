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

STAGE_OBSERVATION_RECORD_TYPE = "stage_observation/v3"
PREVIOUS_STAGE_OBSERVATION_RECORD_TYPE = "stage_observation/v2"
LEGACY_STAGE_OBSERVATION_RECORD_TYPE = "stage_observation/v1"
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
                    strict_current = record_type == STAGE_OBSERVATION_RECORD_TYPE
                    strict_previous = (
                        record_type == PREVIOUS_STAGE_OBSERVATION_RECORD_TYPE)
                    if record_type not in (
                            None, LEGACY_STAGE_OBSERVATION_RECORD_TYPE,
                            PREVIOUS_STAGE_OBSERVATION_RECORD_TYPE,
                            STAGE_OBSERVATION_RECORD_TYPE):
                        raise ValueError("unsupported stage record type")
                    if strict_current:
                        _records.validate_v3_record(value)
                    elif strict_previous:
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
                            value, strict=(strict_current or strict_previous),
                            stage_record_type=str(record_type or "")),
                        gateway_calls=int(value.get("gateway_calls") or 0),
                        model_calls=int(value.get("model_calls") or 0),
                        elapsed_seconds=value.get("elapsed_seconds"),
                        input_tokens=value.get("input_tokens"),
                        output_tokens=value.get("output_tokens"))
                    if strict_current or strict_previous:
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
    from .stage_store_checks import run_checks
    return run_checks()
