"""Where stage fingerprints are kept, and how a similar one is found again.

A fingerprint that is computed and discarded is arithmetic. The value arrives
only when a stage can ask whether anything like it has been done before, and
that requires the earlier ones to still be somewhere, indexed by the things a
later stage will have in hand.

Three indexes, because there are three different questions:

    exact       this situation, seen before
    motif       this kind of situation, in any domain
    shape       this unit of work, whatever it was about

They are separate rather than blended into one score. A caller that finds an
exact match knows something quite different from one that finds a shape match,
and collapsing them into a single number would hide which it got. A blended
similarity also cannot say why it matched, and a match nobody can inspect is
not evidence.

What comes back is a candidate with what happened to it, never an instruction.
A prior stage that succeeded is a reason to look; it is not a reason to skip
the looking. The moment a lookup starts deciding rather than suggesting, the
corpus stops recording what reasoning does and starts recording what the
corpus already said.

Storage is append-only and keyed by digest, so the same situation recorded
twice is one row with two observations rather than two rows that disagree.

Owns:
    - StageStore: append, lookup by exact digest, motif, or shape.
    - StageObservation: one occurrence and what became of it.

Does not own: computing fingerprints (core.stage_fingerprint), deciding what
to do with a match, or any claim that a match should be reused.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

STAGE_OBSERVATION_RECORD_TYPE = "stage_observation/v1"

#: How a candidate was found. Carried on every result so a caller can weigh
#: an exact repeat differently from a distant shape match.
BY_EXACT, BY_MOTIF, BY_SHAPE = "exact", "motif", "shape"


@dataclass(frozen=True)
class StageObservation:
    """One occurrence of a stage, and what is known about how it went."""

    digest: str
    motif: str
    shape: tuple
    responsibility: str
    run_id: str = ""
    #: What the answer looked like, when the caller knew. Kept as an opaque
    #: label so this module never has to understand response shapes.
    response_shape: str = ""
    model_route: str = ""
    #: None until the run that contained it finished.
    helped: "bool | None" = None
    model_calls: int = 0
    elapsed_seconds: "float | None" = None

    def to_dict(self) -> dict:
        return {"record_type": STAGE_OBSERVATION_RECORD_TYPE,
                "digest": self.digest, "motif": self.motif,
                "shape": list(self.shape),
                "responsibility": self.responsibility,
                "run_id": self.run_id,
                "response_shape": self.response_shape,
                "model_route": self.model_route, "helped": self.helped,
                "model_calls": self.model_calls,
                "elapsed_seconds": self.elapsed_seconds}


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
            # Deliberately not a rate. Two of three is a different thing from
            # two hundred of three hundred, and a single number hides which
            # one a caller is holding.
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
    """Every stage seen, indexed three ways.

    Held in memory and optionally written through to a file. The file is
    newline-delimited JSON: appendable without rewriting, readable without a
    schema, and greppable when something looks wrong.
    """

    path: str = ""
    observations: list = field(default_factory=list)
    _by_digest: dict = field(default_factory=dict)
    _by_motif: dict = field(default_factory=dict)
    _by_shape: dict = field(default_factory=dict)

    def add(self, stage, **fields) -> StageObservation:
        """Record one occurrence of a stage."""
        from .stage_fingerprint import stage_motif
        observation = StageObservation(
            digest=stage.digest, motif=stage_motif(stage),
            shape=tuple(stage.shape),
            responsibility=stage.semantic_responsibility, **fields)
        self.observations.append(observation)
        self._by_digest.setdefault(observation.digest, []).append(observation)
        self._by_motif.setdefault(observation.motif, []).append(observation)
        self._by_shape.setdefault(observation.shape, []).append(observation)
        if self.path:
            self._append(observation)
        return observation

    def _append(self, observation: StageObservation) -> None:
        """Write one row through, never failing the caller if it cannot."""
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(observation.to_dict(),
                                        sort_keys=True,
                                        separators=(",", ":")) + "\n")
        except OSError:
            # A store that cannot persist is a degraded store, not a failed
            # run. The in-memory index still works for this run.
            pass

    def load(self) -> int:
        """Read a stored file back into the indexes. Returns rows read."""
        if not self.path or not os.path.isfile(self.path):
            return 0
        read = 0
        with open(self.path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                observation = StageObservation(
                    digest=value.get("digest", ""),
                    motif=value.get("motif", ""),
                    shape=_hashable(value.get("shape") or ()),
                    responsibility=value.get("responsibility", ""),
                    run_id=value.get("run_id", ""),
                    response_shape=value.get("response_shape", ""),
                    model_route=value.get("model_route", ""),
                    helped=value.get("helped"),
                    model_calls=int(value.get("model_calls") or 0),
                    elapsed_seconds=value.get("elapsed_seconds"))
                self.observations.append(observation)
                self._by_digest.setdefault(
                    observation.digest, []).append(observation)
                self._by_motif.setdefault(
                    observation.motif, []).append(observation)
                self._by_shape.setdefault(
                    observation.shape, []).append(observation)
                read += 1
        return read

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
                (BY_EXACT, self._by_digest, stage.digest),
                (BY_MOTIF, self._by_motif, stage_motif(stage)),
                (BY_SHAPE, self._by_shape, tuple(stage.shape))):
            matched = rows(index, key)
            if matched:
                found.append(StageMatch(found_by=label, observations=matched))
        return tuple(found)

    def to_dict(self) -> dict:
        return {"record_type": "stage_store/v1",
                "observations": len(self.observations),
                "distinct_situations": len(self._by_digest),
                "distinct_motifs": len(self._by_motif),
                "distinct_shapes": len(self._by_shape),
                "path": self.path}


def _hashable(value):
    """Restore a shape read back from JSON to something indexable.

    A shape holds nested tuples, and JSON has only lists. Reading one back
    without this produces a tuple containing a list, which cannot be a dict
    key, so a store round-tripped through a file would index nothing.
    """
    if isinstance(value, list):
        return tuple(_hashable(item) for item in value)
    return value


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
    store.add(billing, run_id="r1", response_shape="record", helped=True)
    store.add(telemetry, run_id="r2", response_shape="record", helped=True)

    found = {item.found_by: item for item in store.lookup(stage(
        "scrub the invoice feed"))}
    check("an unrelated pipeline's stage is found by shape",
          BY_SHAPE in found and found[BY_SHAPE].occurrences == 2,
          "billing and telemetry both match a third domain by shape alone")
    check("a stage nobody has seen exactly is not offered as exact",
          BY_EXACT not in found)

    repeat = {item.found_by: item for item in store.lookup(billing)}
    check("the same situation again is found exactly",
          BY_EXACT in repeat and repeat[BY_EXACT].occurrences == 1)
    check("every level is returned, not only the strongest",
          set(repeat) == {BY_EXACT, BY_MOTIF, BY_SHAPE},
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
          all(item.found_by != BY_EXACT for item in own_run))

    unknown = StageStore()
    unknown.add(stage("do a new thing"), run_id="r3")
    match = unknown.lookup(stage("do a new thing"))[0]
    check("an occurrence with no outcome yet is not counted as helping",
          match.known_outcomes == 0 and match.helped == 0)

    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "nested", "stages.jsonl")
        writing = StageStore(path=path)
        writing.add(billing, run_id="r1", helped=True)
        writing.add(telemetry, run_id="r2", helped=False)
        reading = StageStore(path=path)
        rows = reading.load()
        check("a shape survives serialisation as an indexable key",
              _hashable(json.loads(json.dumps(list(billing.shape))))
              == tuple(billing.shape),
              "JSON has no tuples, and an unhashable shape indexes nothing")
        check("what was written comes back", rows == 2
              and reading.to_dict()["distinct_situations"] == 2)
        restored = {item.found_by: item
                    for item in reading.lookup(billing)}
        check("outcomes survive the round trip",
              restored[BY_SHAPE].known_outcomes == 2
              and restored[BY_SHAPE].helped == 1)

    unwritable = StageStore(path="/proc/definitely/not/writable/x.jsonl")
    unwritable.add(billing, run_id="r9")
    check("a store that cannot persist does not fail the run",
          len(unwritable.observations) == 1)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "stage_store_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
