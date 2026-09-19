"""What is missing, stated precisely enough that something can be built for it.

Generating capabilities by asking a model for a thousand instruction files
produces a thousand files and no knowledge of whether any of them were needed.
This module produces the other thing: a queue of exact gaps, each one carrying
the combination it fills, what would count as satisfying it, and where to look
before building anything.

WHERE A NEED COMES FROM
Five origins, and none of them is a hunch. A combination of tags with nothing
written for it. A step that failed for want of a capability. An operation that
keeps costing more than it should. A source that changed under material that
was derived from it. A person asking for something by name.

WHAT A NEED IS NOT
A need is not a capability, and nothing here creates one. It carries no body,
claims no implementation, and cannot promote itself. It is the input to a
bounded builder and to the admission ladder that already exists, both of which
stay exactly as strict as they were.

SEARCH BEFORE BUILDING
Every need names the places to look first. The right answer to a gap is often
an existing implementation with different explanatory material around it, and
writing a second parser because two roles need one is how a catalogue becomes
a pile.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from .intelligence_tagging import EMPTY_TAGS, TagSet, coverage

RECORD_TYPE = "capability_need/v1"
QUEUE_RECORD_TYPE = "capability_need_queue/v1"
#: Why this need exists. A need without one of these is a hunch.
ORIGINS = ("coverage_gap", "failed_step", "expensive_operation", "source_changed",
           "asked_for")
#: What kind of thing would satisfy the need, drawn from what can be given to
#: an instance. A need may accept more than one.
SATISFIED_BY = ("reusable_code", "skill", "tool", "instruction_file")
#: A need with nothing at all in its combination outranks one with general
#: material already serving it.
UNSERVED = "nothing serves this combination"
PARTLY_SERVED = "general material serves this combination"


class CapabilityNeedError(ValueError):
    """The need names an unknown origin, or states no way to know it is satisfied."""


@dataclass(frozen=True)
class CapabilityNeed:
    """One gap, precise enough to build against and to refuse a wrong answer."""

    need_id: str
    purpose: str
    origin: str
    acceptance: tuple[str, ...]
    tags: TagSet = EMPTY_TAGS
    satisfied_by: tuple[str, ...] = SATISFIED_BY
    search_first: tuple[str, ...] = ()
    serving_note: str = ""
    existing_items: int = 0

    def __post_init__(self) -> None:
        if not self.need_id.strip() or not self.purpose.strip():
            raise CapabilityNeedError("a need has an identifier and a purpose")
        if self.origin not in ORIGINS:
            raise CapabilityNeedError(f"origin must be one of {ORIGINS}")
        if not self.acceptance:
            raise CapabilityNeedError(
                f"need {self.need_id!r} states no acceptance; a builder that cannot know "
                "when it is finished will decide for itself")
        unknown = [kind for kind in self.satisfied_by if kind not in SATISFIED_BY]
        if unknown:
            raise CapabilityNeedError(f"{unknown} is not drawn from {SATISFIED_BY}")
        if not self.satisfied_by:
            raise CapabilityNeedError("a need names at least one kind that would satisfy it")
        if not isinstance(self.tags, TagSet):
            raise CapabilityNeedError("tags must be a typed tag set")
        if not isinstance(self.existing_items, int) or self.existing_items < 0:
            raise CapabilityNeedError("existing items is a count")

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "need_id": self.need_id,
                "purpose": self.purpose, "origin": self.origin,
                "acceptance": list(self.acceptance), "tags": self.tags.to_dict(),
                "satisfied_by": list(self.satisfied_by),
                "search_first": list(self.search_first),
                "serving_note": self.serving_note,
                "existing_items": self.existing_items,
                "is_a_capability": False}

    @property
    def digest(self) -> str:
        import json
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")).hexdigest()


def _identifier(tags: TagSet) -> str:
    parts = []
    for dimension in tags.declared_dimensions:
        parts.append(dimension + "-" + "-".join(tags.on(dimension)))
    return "need." + (".".join(parts) if parts else "general")


def needs_from_coverage(report: dict, *, purpose: str, acceptance,
                        satisfied_by=SATISFIED_BY, search_first=()) -> tuple:
    """Turn the empty cells of a coverage report into typed needs.

    ``purpose`` is a sentence with the combination appended, so a builder reads
    what it is for rather than a row of labels. Nothing is built here: the
    result is a queue.
    """
    if report.get("record_type") != "tag_coverage/v1":
        raise CapabilityNeedError("a coverage report is required")
    if not purpose.strip() or not tuple(acceptance):
        raise CapabilityNeedError("a purpose and an acceptance are required")
    by_tags = {_stable(cell["tags"]): cell for cell in report.get("cells", ())}
    needs = []
    for empty in report.get("empty_cells", ()):
        values = {key: tuple(value) for key, value in empty.items()
                  if key != "record_type"}
        tags = TagSet(values)
        cell = by_tags.get(_stable(empty), {})
        serving = UNSERVED if not cell.get("items") else PARTLY_SERVED
        described = ", ".join(f"{dimension} {', '.join(tags.on(dimension))}"
                              for dimension in tags.declared_dimensions)
        needs.append(CapabilityNeed(
            _identifier(tags), f"{purpose.strip()} for {described}", ORIGINS[0],
            tuple(acceptance), tags, tuple(satisfied_by), tuple(search_first),
            serving, int(cell.get("items", 0))))
    return tuple(needs)


def _stable(tags: dict) -> tuple:
    return tuple(sorted((key, tuple(value)) for key, value in tags.items()
                        if key != "record_type"))


def queue(needs, *, limit: int = 0) -> dict:
    """Order needs so the combinations nothing serves come first.

    Within that, a need whose combination is described on more dimensions is
    more specific and comes first, because a gap stated precisely is one a
    builder can finish.
    """
    prepared = tuple(needs)
    for need in prepared:
        if not isinstance(need, CapabilityNeed):
            raise CapabilityNeedError("only typed needs can be queued")
    identities = [need.need_id for need in prepared]
    duplicates = sorted({name for name in identities if identities.count(name) > 1})
    if duplicates:
        raise CapabilityNeedError(f"these needs share an identifier: {duplicates}")
    ordered = sorted(
        prepared,
        key=lambda need: (need.existing_items,
                          -len(need.tags.declared_dimensions),
                          need.need_id))
    if limit:
        ordered = ordered[:limit]
    return {"record_type": QUEUE_RECORD_TYPE, "needs": [need.to_dict() for need in ordered],
            "count": len(ordered), "unserved": sum(1 for need in ordered
                                                   if need.serving_note == UNSERVED),
            "origins": sorted({need.origin for need in ordered})}


def assignment_for(need: CapabilityNeed, *, node_id: str = "", effects=("reads_fs",),
                   harness_style: str = ""):
    """The build node that would work on this need, with its acceptance carried.

    A need becomes a build node because producing a capability writes files.
    The acceptance travels into the objective, so the instance is told how the
    result will be judged rather than being left to decide.
    """
    from .node_provisioning import NodeAssignment
    if not isinstance(need, CapabilityNeed):
        raise CapabilityNeedError("a typed need is required")
    objective = (f"{need.purpose}. It is satisfied by "
                 f"{' or '.join(need.satisfied_by)}. It is accepted when: "
                 + "; ".join(need.acceptance)
                 + (". Look first at: " + ", ".join(need.search_first)
                    if need.search_first else "."))
    return NodeAssignment(node_id or need.need_id, "build", objective,
                          ("capability_candidate/v1",), (), need.search_first,
                          tuple(effects), harness_style)


def self_test() -> dict:
    """Gaps become needs, needs carry acceptance, and nothing here makes a capability."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except CapabilityNeedError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    class _Row:
        def __init__(self, identity, tags):
            self.identity, self.tags = identity, TagSet(tags)

    rows = (
        _Row("general.reading", {}),
        _Row("analyst.english", {"role": ("data analyst",), "language": ("en",)}),
    )
    space = {"role": ("data analyst", "nurse"), "language": ("en", "de")}
    report = coverage(rows, space)
    needs = needs_from_coverage(
        report, purpose="Intake guidance", acceptance=(
            "it states when to use it in one sentence",
            "it names the source it was derived from",
            "it carries a check that fails on a wrong answer"),
        satisfied_by=("skill",), search_first=("ctx.skill.intake",))
    check("every_empty_combination_becomes_one_need_that_names_its_combination",
          len(needs) == 3
          and all(need.origin == "coverage_gap" for need in needs)
          and all(need.tags.on("role") and need.tags.on("language") for need in needs)
          and any("nurse" in need.purpose and "de" in need.purpose for need in needs)
          and all(need.satisfied_by == ("skill",) for need in needs),
          str([need.need_id for need in needs]))
    check("a_need_carries_acceptance_and_never_claims_to_be_a_capability",
          all(len(need.acceptance) == 3 for need in needs)
          and needs[0].to_dict()["is_a_capability"] is False
          and "body" not in needs[0].to_dict()
          and len(needs[0].digest) == 64
          and refuses(lambda: CapabilityNeed("n", "p", "coverage_gap", ()))
          and refuses(lambda: CapabilityNeed("n", "p", "guessing", ("a",)))
          and refuses(lambda: CapabilityNeed("n", "p", "coverage_gap", ("a",),
                                             satisfied_by=("poster",)))
          and refuses(lambda: CapabilityNeed("", "p", "coverage_gap", ("a",))),
          needs[0].digest[:12])
    def mixed_needs_limit():
        return (CapabilityNeed("need.one", "p", "coverage_gap", ("a",)),
                CapabilityNeed("need.two", "p", "coverage_gap", ("a",)))

    ordered = queue(needs)
    first = ordered["needs"][0]
    # A mixed queue, so the ordering is exercised rather than assumed: one gap
    # nothing serves, one that general material already serves, and one
    # described on fewer dimensions than the others.
    mixed = queue((
        CapabilityNeed("need.served", "p", "coverage_gap", ("a",),
                       TagSet({"role": ("nurse",), "language": ("de",)}),
                       serving_note=PARTLY_SERVED, existing_items=4),
        CapabilityNeed("need.vague", "p", "coverage_gap", ("a",),
                       TagSet({"role": ("nurse",)}),
                       serving_note=UNSERVED, existing_items=0),
        CapabilityNeed("need.precise", "p", "coverage_gap", ("a",),
                       TagSet({"role": ("nurse",), "language": ("de",),
                               "data_sensitivity": ("regulated",)}),
                       serving_note=UNSERVED, existing_items=0)))
    check("the_combinations_nothing_serves_come_first_and_the_counts_are_reported",
          ordered["count"] == 3 and ordered["origins"] == ["coverage_gap"]
          # The general record serves every combination, so none is unserved here,
          # and the order falls back to how precisely each gap is described.
          and ordered["unserved"] == 0
          and all(row["existing_items"] >= 1 for row in ordered["needs"])
          and first["serving_note"] == PARTLY_SERVED
          # Nothing served first, then the more precisely described gap, then
          # the one that something already serves.
          and [row["need_id"] for row in mixed["needs"]]
          == ["need.precise", "need.vague", "need.served"]
          and mixed["unserved"] == 2
          and queue(mixed_needs_limit(), limit=1)["count"] == 1,
          str([row["need_id"] for row in mixed["needs"]]))
    bare = coverage((_Row("analyst.english", {"role": ("data analyst",),
                                              "language": ("en",)}),), space)
    bare_needs = needs_from_coverage(
        bare, purpose="Intake guidance", acceptance=("it names its source",))
    bare_queue = queue(bare_needs)
    check("with_no_general_record_the_unserved_combinations_are_named_as_such",
          bare_queue["unserved"] == 3
          and all(row["serving_note"] == UNSERVED for row in bare_queue["needs"])
          and all(row["existing_items"] == 0 for row in bare_queue["needs"]),
          str(bare_queue["unserved"]))
    check("a_bad_report_a_repeated_identifier_and_an_untyped_need_are_refused",
          refuses(lambda: needs_from_coverage({}, purpose="x", acceptance=("a",)))
          and refuses(lambda: needs_from_coverage(report, purpose="", acceptance=("a",)))
          and refuses(lambda: needs_from_coverage(report, purpose="x", acceptance=()))
          and refuses(lambda: queue((needs[0], needs[0])))
          and refuses(lambda: queue(("not a need",))))
    assignment = assignment_for(needs[0], effects=("reads_fs", "writes_fs"))
    check("a_need_becomes_a_build_node_that_is_told_how_it_will_be_judged",
          assignment.kind == "build"
          and assignment.node_id == needs[0].need_id
          and "accepted when" in assignment.objective
          and "Look first at" in assignment.objective
          and assignment.output_contract_refs == ("capability_candidate/v1",)
          and assignment.effects == ("reads_fs", "writes_fs")
          and refuses(lambda: assignment_for("not a need")),
          assignment.objective[:70])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "capability_needs_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
