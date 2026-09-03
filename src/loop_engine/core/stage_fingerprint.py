"""The cognitive situation a call is in, named so it can be recognised again.

A task fingerprint identifies the problem. It is too coarse for learning what
a response should contain, because one competition, ticket or thread holds
many different cognitive situations: inferring an output contract, testing for
leakage, comparing two candidates, diagnosing a failed command, deciding
whether a result is good enough. Those share a task and need almost nothing
else in common.

This names the smaller unit. A stage fingerprint says what this call is
responsible for, where it sits between the ultimate goal and the immediate
step, what it already knows, and what its answer will be used for. Two stages
with the same shape are comparable even when their tasks are not: a provider
failing over and a test failing to reproduce are both "an observed failure,
several plausible causes, one discriminating experiment to choose between
them", and what makes a good answer to one is evidence about the other.

That cross-domain motif is the point. Matching Kaggle to Kaggle finds the
obvious; matching a recovery stage to a repair stage is where a response shape
learned in one place could be worth anything in another.

Nothing here retrieves, ranks, or decides. It describes a situation and
computes a stable identity for it, so that other things can.

Owns:
    - SemanticStageFingerprint: one cognitive situation, and its digest.
    - COGNITIVE_PHASES, RESPONSE_TOPOLOGIES: open vocabularies, not gates.
    - stage_motif(): the cross-domain shape, coarser than the fingerprint.

Does not own: retrieval, template selection, or any claim that two similar
stages should be answered the same way.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

STAGE_FINGERPRINT_RECORD_TYPE = "semantic_stage_fingerprint/v1"
SEGMENT_FINGERPRINT_RECORD_TYPE = "semantic_segment_fingerprint/v1"

#: The scales a situation can be named at. One model call sits at OPERATION,
#: one bounded responsibility at LOOP, a run of consecutive responsibilities
#: at SEGMENT, the whole attempt at RUN. They are separate because they match
#: different things: two runs can be unalike while containing the same loop,
#: and two loops can be alike while sitting in unrelated runs.
OPERATION, LOOP, SEGMENT, RUN = "operation", "loop", "segment", "run"
FINGERPRINT_SCOPES = (OPERATION, LOOP, SEGMENT, RUN)

#: Phases seen so far. Open on purpose: a stage whose phase nobody named is
#: recorded under the name it gives itself, because the unnamed ones are
#: where the next useful category comes from.
COGNITIVE_PHASES = (
    "orient", "decompose", "context_selection", "hypothesis_generation",
    "experiment_design", "execution", "observation_interpretation",
    "failure_diagnosis", "recovery_choice", "comparison", "verification",
    "stopping", "learning",
)

#: Shapes an answer might take. Also open, and deliberately broader than
#: "a JSON object": a plan, a graph and a matrix are different answers, and
#: flattening them into one record is how structure gets lost.
RESPONSE_TOPOLOGIES = (
    "scalar", "label", "typed_list", "record", "configuration_patch",
    "conditional_plan", "decision_tree", "experiment_spec",
    "comparison_matrix", "hypothesis_portfolio", "graph_mutation",
    "artifact_manifest", "verification_rubric", "raw_artifact",
)


@dataclass(frozen=True)
class SemanticStageFingerprint:
    """One bounded piece of reasoning, described so it can be matched later.

    The horizons are kept apart because they answer different questions. Two
    stages doing the same immediate work toward different ultimate goals are
    similar in a way that matters for response shape and different in a way
    that matters for whether the answer was any good.
    """

    semantic_responsibility: str
    cognitive_phase: str = ""

    ultimate_horizon: str = ""
    medium_horizon: str = ""
    near_horizon: str = ""
    micro_horizon: str = ""

    parent_responsibility: str = ""
    branch_depth: int = 0
    incoming_observation: str = ""

    knowns: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    verified_artifacts: tuple[str, ...] = ()

    candidate_topologies: tuple[str, ...] = ()
    consumer: str = ""
    expected_use: tuple[str, ...] = ()

    context_pressure: "float | None" = None
    reversibility: "float | None" = None

    task_ref: str = ""
    loop_ref: str = ""
    branch_ref: str = ""

    #: The scale this names. A finer scope matches more situations and says
    #: less about each; a coarser one says more and matches less.
    scope: str = LOOP

    def __post_init__(self):
        if not str(self.semantic_responsibility or "").strip():
            raise ValueError("a stage fingerprint needs a responsibility")
        if self.scope not in FINGERPRINT_SCOPES:
            raise ValueError(f"unknown fingerprint scope {self.scope!r}")

    @property
    def digest(self) -> str:
        """A stable identity for this exact situation.

        Deliberately excludes the run, loop and branch references: the same
        situation arising in a different run is the same situation, and
        including the identifiers would make every stage unique and the
        whole record useless for matching.
        """
        material = {
            "scope": self.scope,
            "responsibility": self.semantic_responsibility.strip().lower(),
            "phase": self.cognitive_phase.strip().lower(),
            "near": self.near_horizon.strip().lower(),
            "micro": self.micro_horizon.strip().lower(),
            "unknowns": sorted(item.strip().lower() for item in self.unknowns),
            "topologies": sorted(self.candidate_topologies),
            "consumer": self.consumer.strip().lower(),
        }
        return "stage:sha256:" + hashlib.sha256(json.dumps(
            material, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()[:32]

    @property
    def shape(self) -> tuple:
        """What this stage looks like as a unit of work, without its subject.

        Inputs and outputs by kind, the phase, and what remains open — the
        things two loops can share when their domains do not. A cleaning step
        in a billing pipeline and a cleaning step in a telemetry pipeline
        differ in every noun and can be identical here.
        """
        return (self.cognitive_phase or "unnamed",
                tuple(sorted(self.candidate_topologies)),
                self.consumer or "unnamed",
                bool(self.incoming_observation),
                len(self.unknowns) > 0)

    @property
    def facets(self) -> dict:
        """The dimensions two stages can be compared on, coarsest first."""
        return {
            "phase": self.cognitive_phase or "unnamed",
            "topologies": tuple(sorted(self.candidate_topologies)),
            "consumer": self.consumer or "unnamed",
            "has_incoming_observation": bool(self.incoming_observation),
            "unknown_count": len(self.unknowns),
            "known_count": len(self.knowns),
            "branch_depth": self.branch_depth,
        }

    def to_dict(self) -> dict:
        return {
            "record_type": STAGE_FINGERPRINT_RECORD_TYPE,
            "digest": self.digest,
            "motif": stage_motif(self),
            "semantic_responsibility": self.semantic_responsibility,
            "cognitive_phase": self.cognitive_phase,
            "horizons": {"ultimate": self.ultimate_horizon,
                         "medium": self.medium_horizon,
                         "near": self.near_horizon,
                         "micro": self.micro_horizon},
            "graph_position": {
                "parent_responsibility": self.parent_responsibility,
                "branch_depth": self.branch_depth,
                "incoming_observation": self.incoming_observation},
            "state": {"knowns": list(self.knowns),
                      "unknowns": list(self.unknowns),
                      "verified_artifacts": list(self.verified_artifacts)},
            "response_need": {
                "candidate_topologies": list(self.candidate_topologies),
                "consumer": self.consumer,
                "expected_use": list(self.expected_use)},
            "context_pressure": self.context_pressure,
            "reversibility": self.reversibility,
            "task_ref": self.task_ref, "loop_ref": self.loop_ref,
            "branch_ref": self.branch_ref,
            "scope": self.scope,
            "shape": list(self.shape),
            "facets": {name: (list(value) if isinstance(value, tuple)
                              else value)
                       for name, value in self.facets.items()},
        }


#: The shapes a stage can take, coarser than any of them. Two stages with the
#: same motif are worth comparing across domains; the motif is what a
#: recovery stage and a repair stage have in common when their tasks have
#: nothing in common at all.
_MOTIFS = (
    ("choose_among_causes",
     lambda item: bool(item.incoming_observation) and len(item.unknowns) > 1),
    ("interpret_an_observation",
     lambda item: bool(item.incoming_observation)),
    ("decide_with_open_questions",
     lambda item: len(item.unknowns) > 0),
    ("produce_from_what_is_known",
     lambda item: bool(item.knowns) and not item.unknowns),
)


def stage_motif(stage: SemanticStageFingerprint) -> str:
    """The cross-domain shape of this stage.

    Coarse on purpose. A motif that separated every situation would match
    nothing, and the value here is in matching a stage from one domain to a
    stage from another. The phase qualifies it so that diagnosing and
    comparing do not collapse into the same bucket.
    """
    for name, holds in _MOTIFS:
        if holds(stage):
            base = name
            break
    else:
        base = "unclassified"
    phase = stage.cognitive_phase or "unnamed"
    return f"{phase}/{base}"


@dataclass(frozen=True)
class SegmentFingerprint:
    """A run of consecutive stages, identified by the shape of the work.

    Composed from its members' motifs rather than their subjects, so that a
    cleaning-then-validating-then-loading segment in a billing pipeline and
    the same three moves over telemetry come out identical. That is the
    match worth having: the domains share no nouns and the work is the same
    work, and whatever was learned about doing it once applies to the other.

    The member digests are kept so a match can be opened and inspected. A
    segment that matches and turns out to be nothing alike is a finding
    about the motif vocabulary, and there is no way to see that without the
    members.
    """

    motifs: tuple[str, ...]
    member_digests: tuple[str, ...] = ()
    scope: str = SEGMENT

    def __post_init__(self):
        if not self.motifs:
            raise ValueError("a segment fingerprint needs at least one motif")

    @property
    def digest(self) -> str:
        """Identity from the ordered motifs alone."""
        return "segment:sha256:" + hashlib.sha256(
            "|".join(self.motifs).encode("utf-8")).hexdigest()[:32]

    @property
    def unordered_digest(self) -> str:
        """Identity ignoring order.

        Two pipelines may do the same work in a different sequence. That is a
        weaker match than the ordered one and is kept separately so a caller
        can tell which kind it got rather than being handed one number.
        """
        return "segment-set:sha256:" + hashlib.sha256(
            "|".join(sorted(set(self.motifs))).encode("utf-8")
        ).hexdigest()[:32]

    def to_dict(self) -> dict:
        return {"record_type": SEGMENT_FINGERPRINT_RECORD_TYPE,
                "scope": self.scope, "digest": self.digest,
                "unordered_digest": self.unordered_digest,
                "motifs": list(self.motifs), "length": len(self.motifs),
                "member_digests": list(self.member_digests)}


def compose_segment(stages) -> SegmentFingerprint:
    """Name the shape of a run of stages, in the order they happened."""
    members = tuple(stages)
    if not members:
        raise ValueError("a segment needs at least one stage")
    return SegmentFingerprint(
        motifs=tuple(stage_motif(item) for item in members),
        member_digests=tuple(item.digest for item in members))


def sliding_segments(stages, length: int = 3) -> tuple:
    """Every run of `length` consecutive stages.

    The unit that transfers between pipelines is rarely a whole run and
    rarely one stage. Overlapping windows let a middle-of-the-pipeline
    sequence match without the ends having to agree.
    """
    members = tuple(stages)
    if length < 1:
        raise ValueError("a segment length must be positive")
    if len(members) < length:
        return ()
    return tuple(compose_segment(members[index:index + length])
                 for index in range(len(members) - length + 1))


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    leakage = SemanticStageFingerprint(
        semantic_responsibility="design one discriminating leakage experiment",
        cognitive_phase="experiment_design",
        ultimate_horizon="produce the strongest verified submission",
        near_horizon="resolve possible author leakage",
        micro_horizon="define one changed validation experiment",
        incoming_observation="the random split score looks unusually high",
        knowns=("author labels exist",),
        unknowns=("whether repeated sources cross folds",
                  "whether the metric is affected"),
        candidate_topologies=("experiment_spec", "decision_tree"),
        consumer="Practitioner Loop", branch_depth=4,
        task_ref="task:kaggle-spooky", loop_ref="loop:17")

    same_elsewhere = SemanticStageFingerprint(
        semantic_responsibility="design one discriminating leakage experiment",
        cognitive_phase="experiment_design",
        near_horizon="resolve possible author leakage",
        micro_horizon="define one changed validation experiment",
        incoming_observation="a different wording of the same symptom",
        knowns=("something else entirely",),
        unknowns=("whether repeated sources cross folds",
                  "whether the metric is affected"),
        candidate_topologies=("decision_tree", "experiment_spec"),
        consumer="Practitioner Loop", branch_depth=9,
        task_ref="task:something-else", loop_ref="loop:203")

    check("the same situation in another run has the same identity",
          leakage.digest == same_elsewhere.digest,
          "run, loop and branch refs must not enter the digest")

    different = SemanticStageFingerprint(
        semantic_responsibility="design one discriminating leakage experiment",
        cognitive_phase="verification",
        consumer="Practitioner Loop")
    check("a different phase is a different situation",
          leakage.digest != different.digest)

    # The point of the motif: two stages from unrelated domains.
    recovery = SemanticStageFingerprint(
        semantic_responsibility="choose how to recover a failed model call",
        cognitive_phase="failure_diagnosis",
        incoming_observation="the provider returned no answer",
        unknowns=("whether the route is busy or broken",
                  "whether the packet is too large"))
    repair = SemanticStageFingerprint(
        semantic_responsibility="find why the test does not reproduce",
        cognitive_phase="failure_diagnosis",
        incoming_observation="the failure vanishes on rerun",
        unknowns=("whether the test is order dependent",
                  "whether a fixture leaks state"))
    check("unrelated domains sharing a shape share a motif",
          stage_motif(recovery) == stage_motif(repair)
          == "failure_diagnosis/choose_among_causes",
          "a recovery stage and a repair stage are the same kind of problem")

    check("a stage with nothing open is a different motif",
          stage_motif(SemanticStageFingerprint(
              semantic_responsibility="write the submission file",
              cognitive_phase="execution", knowns=("the contract",)))
          == "execution/produce_from_what_is_known")

    check("the phase keeps different work from collapsing together",
          stage_motif(recovery) != stage_motif(
              SemanticStageFingerprint(
                  semantic_responsibility="compare two candidates",
                  cognitive_phase="comparison",
                  incoming_observation="both scored similarly",
                  unknowns=("which generalises", "which costs less"))))

    check("an unnamed phase is recorded, not refused",
          stage_motif(SemanticStageFingerprint(
              semantic_responsibility="something new under the sun"))
          .startswith("unnamed/"))

    empty = False
    try:
        SemanticStageFingerprint(semantic_responsibility="  ")
    except ValueError:
        empty = True
    check("a stage with no responsibility is refused", empty)

    value = leakage.to_dict()
    check("the record carries both the exact identity and the coarse shape",
          value["digest"].startswith("stage:sha256:")
          and value["motif"] == "experiment_design/choose_among_causes"
          and value["horizons"]["ultimate"].startswith("produce the strongest"))

    def pipeline(rows):
        return [SemanticStageFingerprint(
            semantic_responsibility=f"{verb} the {noun}",
            cognitive_phase=phase, knowns=("schema",)) for verb, noun, phase
            in rows]

    billing = pipeline([("clean", "billing extract", "execution"),
                        ("validate", "billing rows", "verification"),
                        ("load", "billing warehouse", "execution")])
    telemetry = pipeline([("normalise", "telemetry stream", "execution"),
                          ("check", "telemetry rows", "verification"),
                          ("write", "telemetry store", "execution")])
    check("two loops from unrelated domains can share a shape",
          billing[0].shape == telemetry[0].shape
          and billing[0].digest != telemetry[0].digest,
          "the subjects differ and the unit of work does not")

    left, right = compose_segment(billing), compose_segment(telemetry)
    check("unrelated pipelines doing the same work match as a segment",
          left.digest == right.digest,
          "a segment is identified by its motifs, not its nouns")
    check("a segment keeps its members so a match can be inspected",
          left.member_digests == tuple(item.digest for item in billing))

    reordered = compose_segment([billing[1], billing[0], billing[2]])
    check("order matters to a segment and is separable from set membership",
          reordered.digest != left.digest
          and reordered.unordered_digest == left.unordered_digest)

    check("overlapping windows let a middle sequence match on its own",
          len(sliding_segments(billing, 2)) == 2
          and sliding_segments(billing, 9) == ())

    thin = False
    try:
        compose_segment([])
    except ValueError:
        thin = True
    check("an empty segment is refused", thin)

    bad_scope = False
    try:
        SemanticStageFingerprint(semantic_responsibility="x", scope="galaxy")
    except ValueError:
        bad_scope = True
    check("an unknown scope is refused", bad_scope)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "stage_fingerprint_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
