"""The solutions space: every published Solution Canvas for one task, kept plural.

The solutioning space is where the Practitioner reasons and builds; the
solutions space is where the finished, reusable solutions for one task live.
The owner named both on September 18 and asked that the second stay plural:
a task may have several solutions, each a Solution Canvas that resolves to one
``LoopGraphDefinition``, each with its own evidence, applicability, and cost,
so that a later run can choose among them or add to them instead of replacing
the one that came before.

This module owns the passive record of that space. Adding a member never
removes another; a member is superseded by naming its successor, and a member
with the same graph digest is the same member. Nothing here grants authority,
runs a graph, or approves a solution; verification status comes from the
independent verification records the run already keeps.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

MEMBER_STATUSES = ("candidate", "verified", "superseded", "retired")
RECORD_TYPE = "solutions_space/v1"
MEMBER_RECORD_TYPE = "solutions_space_member/v1"


class SolutionsSpaceError(ValueError):
    """A solutions space record or member is invalid."""


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SolutionsSpaceMember:
    """One published solution for a task, with its evidence and status."""

    candidate_id: str
    graph_digest: str
    status: str = MEMBER_STATUSES[0]
    verification_report_digest: str = ""
    applicability: tuple[tuple[str, str], ...] = ()
    cost: tuple[tuple[str, float], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    source_run_id: str = ""
    superseded_by: str = ""

    def __post_init__(self):
        for name in ("candidate_id", "graph_digest"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise SolutionsSpaceError(f"a member needs a nonempty {name}")
        if self.status not in MEMBER_STATUSES:
            raise SolutionsSpaceError(f"status must be one of {MEMBER_STATUSES}")
        if self.status == MEMBER_STATUSES[1] and not self.verification_report_digest:
            raise SolutionsSpaceError("a verified member cites its verification report digest")
        if self.status == MEMBER_STATUSES[2] and not self.superseded_by:
            raise SolutionsSpaceError("a superseded member names its successor")
        applicability = tuple((str(key), str(value)) for key, value in self.applicability)
        cost = tuple((str(key), float(value)) for key, value in self.cost)
        if any(value < 0 for _key, value in cost):
            raise SolutionsSpaceError("a cost cannot be negative")
        object.__setattr__(self, "applicability", applicability)
        object.__setattr__(self, "cost", cost)
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in self.evidence_refs))

    @property
    def member_id(self) -> str:
        return "member:" + self.graph_digest[:16]

    def to_dict(self) -> dict:
        return {"record_type": MEMBER_RECORD_TYPE, "member_id": self.member_id,
                "candidate_id": self.candidate_id, "graph_digest": self.graph_digest,
                "status": self.status,
                "verification_report_digest": self.verification_report_digest,
                "applicability": [list(item) for item in self.applicability],
                "cost": [list(item) for item in self.cost],
                "evidence_refs": list(self.evidence_refs),
                "source_run_id": self.source_run_id, "superseded_by": self.superseded_by}

    @classmethod
    def from_dict(cls, value) -> "SolutionsSpaceMember":
        if not isinstance(value, dict) or value.get("record_type") != MEMBER_RECORD_TYPE:
            raise SolutionsSpaceError(f"a member record needs record_type {MEMBER_RECORD_TYPE}")
        return cls(candidate_id=value.get("candidate_id", ""),
                   graph_digest=value.get("graph_digest", ""),
                   status=value.get("status", MEMBER_STATUSES[0]),
                   verification_report_digest=value.get("verification_report_digest", ""),
                   applicability=tuple(tuple(item) for item in value.get("applicability") or ()),
                   cost=tuple(tuple(item) for item in value.get("cost") or ()),
                   evidence_refs=tuple(value.get("evidence_refs") or ()),
                   source_run_id=value.get("source_run_id", ""),
                   superseded_by=value.get("superseded_by", ""))


@dataclass(frozen=True)
class SolutionsSpaceRecord:
    """The plural, append-only set of solutions for one task."""

    task_digest: str
    members: tuple[SolutionsSpaceMember, ...] = field(default=())

    def __post_init__(self):
        if not isinstance(self.task_digest, str) or not self.task_digest.strip():
            raise SolutionsSpaceError("a solutions space needs its task digest")
        members = tuple(self.members)
        if any(not isinstance(item, SolutionsSpaceMember) for item in members):
            raise SolutionsSpaceError("members must be typed SolutionsSpaceMember records")
        digests = [item.graph_digest for item in members]
        if len(set(digests)) != len(digests):
            raise SolutionsSpaceError("two members cannot share one graph digest")
        object.__setattr__(self, "members", members)

    def member(self, member_id: str) -> "SolutionsSpaceMember | None":
        return next((item for item in self.members if item.member_id == member_id), None)

    def add_member(self, member: SolutionsSpaceMember) -> "SolutionsSpaceRecord":
        """Return the space with the member added; an existing graph is kept as is."""
        if any(item.graph_digest == member.graph_digest for item in self.members):
            return self
        return SolutionsSpaceRecord(self.task_digest, (*self.members, member))

    def supersede(self, member_id: str, successor_id: str) -> "SolutionsSpaceRecord":
        """Mark one member superseded by another member of the same space."""
        if self.member(successor_id) is None or self.member(member_id) is None:
            raise SolutionsSpaceError("both members of a supersession belong to the space")
        if member_id == successor_id:
            raise SolutionsSpaceError("a member cannot supersede itself")
        replaced = tuple(
            SolutionsSpaceMember(**{**_fields(item), "status": MEMBER_STATUSES[2],
                                    "superseded_by": successor_id})
            if item.member_id == member_id else item for item in self.members)
        return SolutionsSpaceRecord(self.task_digest, replaced)

    def verified_members(self) -> tuple[SolutionsSpaceMember, ...]:
        return tuple(item for item in self.members if item.status == MEMBER_STATUSES[1])

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "task_digest": self.task_digest,
                "members": [item.to_dict() for item in self.members],
                "content_digest": _digest([item.to_dict() for item in self.members])}

    @classmethod
    def from_dict(cls, value) -> "SolutionsSpaceRecord":
        if not isinstance(value, dict) or value.get("record_type") != RECORD_TYPE:
            raise SolutionsSpaceError(f"a solutions space record needs record_type {RECORD_TYPE}")
        return cls(value.get("task_digest", ""),
                   tuple(SolutionsSpaceMember.from_dict(item) for item in value.get("members") or ()))


def _fields(member: SolutionsSpaceMember) -> dict:
    return {"candidate_id": member.candidate_id, "graph_digest": member.graph_digest,
            "status": member.status,
            "verification_report_digest": member.verification_report_digest,
            "applicability": member.applicability, "cost": member.cost,
            "evidence_refs": member.evidence_refs, "source_run_id": member.source_run_id,
            "superseded_by": member.superseded_by}


def solutions_space_from_adaptive(task_digest: str, adaptive: dict) -> SolutionsSpaceRecord:
    """Project one finished run's candidate canvases into a solutions space.

    Every candidate canvas becomes a member. The selected canvas is verified
    only when the run itself is solved and holds a passed independent report,
    whose digest the member cites; every other canvas stays a candidate. The
    projection reads records; it never runs or approves a graph.
    """
    if not isinstance(adaptive, dict):
        raise SolutionsSpaceError("the adaptive result must be a mapping")
    passed = [item for item in adaptive.get("independent_verification_records") or ()
              if isinstance(item, dict) and item.get("status") == "passed"]
    selected = adaptive.get("selected_solution_canvas") or {}
    solved = adaptive.get("solved") is True and bool(passed)
    space = SolutionsSpaceRecord(task_digest)
    for canvas in adaptive.get("candidate_solution_canvases") or ():
        if not isinstance(canvas, dict) or not canvas.get("graph_digest"):
            continue
        is_selected = (canvas.get("candidate_id") == selected.get("candidate_id")
                       and canvas.get("graph_digest") == selected.get("graph_digest"))
        verified = solved and is_selected
        space = space.add_member(SolutionsSpaceMember(
            candidate_id=str(canvas.get("candidate_id") or ""),
            graph_digest=str(canvas["graph_digest"]),
            status=MEMBER_STATUSES[1] if verified else MEMBER_STATUSES[0],
            verification_report_digest=str(passed[-1].get("report_digest") or "") if verified else "",
            evidence_refs=(str(passed[-1].get("report_digest")),) if verified else (),
            source_run_id=str(adaptive.get("run_id") or "")))
    return space


def self_test() -> dict:
    """Plural membership, supersession, verification citation, and projection."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except SolutionsSpaceError:
            return True
        return False

    first = SolutionsSpaceMember("canvas:a", "a" * 64, source_run_id="run-1")
    second = SolutionsSpaceMember("canvas:b", "b" * 64, status=MEMBER_STATUSES[1],
                                  verification_report_digest="r" * 64, cost=(("model_calls", 23),))
    space = SolutionsSpaceRecord("t" * 64).add_member(first).add_member(second)
    check("two_solutions_for_one_task_are_kept_as_members",
          len(space.members) == 2 and space.verified_members() == (second,))
    check("the_same_graph_is_not_added_twice",
          space.add_member(SolutionsSpaceMember("canvas:a2", "a" * 64)) is space)
    replaced = space.supersede(first.member_id, second.member_id)
    check("a_superseded_member_stays_and_names_its_successor",
          len(replaced.members) == 2 and replaced.member(first.member_id).status == MEMBER_STATUSES[2]
          and replaced.member(first.member_id).superseded_by == second.member_id
          and refuses(lambda: space.supersede(first.member_id, first.member_id))
          and refuses(lambda: space.supersede(first.member_id, "member:missing")))
    check("member_and_space_rules_are_enforced",
          all(refuses(action) for action in (
              lambda: SolutionsSpaceMember("", "a" * 64),
              lambda: SolutionsSpaceMember("canvas:x", "c" * 64, status=MEMBER_STATUSES[1]),
              lambda: SolutionsSpaceMember("canvas:x", "c" * 64, status=MEMBER_STATUSES[2]),
              lambda: SolutionsSpaceMember("canvas:x", "c" * 64, cost=(("calls", -1),)),
              lambda: SolutionsSpaceRecord(""),
              lambda: SolutionsSpaceRecord("t" * 64, (first, SolutionsSpaceMember("z", "a" * 64))))))
    check("the_space_round_trips_through_its_record",
          SolutionsSpaceRecord.from_dict(replaced.to_dict()) == replaced
          and replaced.to_dict()["content_digest"] == SolutionsSpaceRecord.from_dict(
              replaced.to_dict()).to_dict()["content_digest"])
    adaptive = {"run_id": "run-9", "solved": True,
                "candidate_solution_canvases": [
                    {"candidate_id": "canvas:1", "graph_digest": "1" * 64, "selected": False},
                    {"candidate_id": "canvas:2", "graph_digest": "2" * 64, "selected": True}],
                "selected_solution_canvas": {"candidate_id": "canvas:2", "graph_digest": "2" * 64},
                "independent_verification_records": [{"status": "failed", "report_digest": "f" * 64},
                                                     {"status": "passed", "report_digest": "p" * 64}]}
    projected = solutions_space_from_adaptive("t" * 64, adaptive)
    unsolved = solutions_space_from_adaptive("t" * 64, {**adaptive, "solved": False})
    check("a_finished_run_projects_every_canvas_and_verifies_only_the_accepted_one",
          len(projected.members) == 2 and len(projected.verified_members()) == 1
          and projected.verified_members()[0].candidate_id == "canvas:2"
          and projected.verified_members()[0].verification_report_digest == "p" * 64
          and unsolved.verified_members() == () and len(unsolved.members) == 2)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "solutions_space_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
