"""The dimensions intelligence is filed under, so it can be found and generated.

A catalogue that only holds identities can answer "give me this one". A
catalogue tagged on declared dimensions can answer the questions a run
actually asks: what suits this role, in this language, for this region, at
this sensitivity, under this authentication. The same dimensions then say what
does not exist yet, because a combination with nothing in it is a gap that can
be generated rather than discovered by accident.

CLOSED WHERE A WRONG VALUE IS A POLICY ERROR, OPEN WHERE IT IS NOT
Sensitivity, authentication, and lifecycle are closed: a typing mistake there
would let confidential material be served as public, so an unknown value is
refused by name. Role, domain, geography, and language are open, because job
titles and regions are not a list anyone can finish, and refusing an unlisted
one would only push people to mislabel.

MATCHING
Values inside one dimension are alternatives, and dimensions are requirements.
Asking for role marketing or sales, in language English, means an item must
carry one of those roles and that language. An item that declares nothing on a
dimension is general on it and matches any request, because tagging is how
something is narrowed, not how it is admitted.

WHAT A GAP IS
The combination space is the product of the values a caller cares about.
Counting items per combination turns "we should have more intelligence" into a
list of exact combinations with nothing in them, ordered by how many other
combinations they block.
"""
from __future__ import annotations

from dataclasses import dataclass

RECORD_TYPE = "intelligence_tags/v1"
COVERAGE_RECORD_TYPE = "tag_coverage/v1"
#: Every dimension an item can be filed under. Adding one is adding a name here.
TAG_DIMENSIONS = ("role", "domain", "geography", "language", "data_sensitivity",
                  "authentication", "lifecycle")
#: Dimensions whose values are closed, because a wrong value is a policy error.
CLOSED_VALUES = {
    "data_sensitivity": ("public", "internal", "confidential", "regulated"),
    "authentication": ("none", "tenant", "user_delegated", "operator"),
    "lifecycle": ("candidate", "qualified", "deprecated"),
}
#: What an item is when it says nothing on a dimension.
GENERAL = "general"


class TaggingError(ValueError):
    """A tag names an unknown dimension, or an unknown value on a closed one."""


def _clean(values) -> tuple[str, ...]:
    out = []
    for value in values or ():
        text = str(value).strip().lower()
        if text and text not in out:
            out.append(text)
    return tuple(out)


@dataclass(frozen=True)
class TagSet:
    """What one record is filed under, on the declared dimensions only."""

    values: dict

    def __post_init__(self) -> None:
        if not isinstance(self.values, dict):
            raise TaggingError("tags are a mapping of dimension to values")
        cleaned = {}
        for dimension, raw in self.values.items():
            if dimension not in TAG_DIMENSIONS:
                raise TaggingError(
                    f"{dimension!r} is not one of the declared dimensions {TAG_DIMENSIONS}")
            values = _clean(raw if isinstance(raw, (list, tuple, set)) else (raw,))
            allowed = CLOSED_VALUES.get(dimension)
            if allowed is not None:
                unknown = [value for value in values if value not in allowed]
                if unknown:
                    raise TaggingError(
                        f"{dimension!r} is a closed dimension; {unknown} is not drawn from "
                        f"{list(allowed)}, and a wrong value here is a policy error")
            if values:
                cleaned[dimension] = values
        object.__setattr__(self, "values", cleaned)

    def on(self, dimension: str) -> tuple[str, ...]:
        """What this record declares on one dimension, empty when it is general."""
        if dimension not in TAG_DIMENSIONS:
            raise TaggingError(f"{dimension!r} is not a declared dimension")
        return tuple(self.values.get(dimension, ()))

    def matches(self, request: "TagSet") -> bool:
        """True when every dimension the request names is satisfied.

        A dimension the record leaves empty is general and matches anything.
        Values within a dimension are alternatives.
        """
        for dimension, wanted in request.values.items():
            held = self.values.get(dimension)
            if held is None:
                continue
            if not set(held) & set(wanted):
                return False
        return True

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE,
                **{dimension: list(values) for dimension, values in self.values.items()}}

    @property
    def declared_dimensions(self) -> tuple[str, ...]:
        return tuple(dimension for dimension in TAG_DIMENSIONS if dimension in self.values)


EMPTY_TAGS = TagSet({})


def select(rows, request: TagSet, *, tags_of=None) -> tuple:
    """Every row whose tags satisfy the request, in the order given."""
    if not isinstance(request, TagSet):
        raise TaggingError("a typed tag set is required")
    reader = tags_of or (lambda row: getattr(row, "tags", None))
    kept = []
    for row in rows:
        tags = reader(row)
        if not isinstance(tags, TagSet):
            raise TaggingError(
                "a row without a typed tag set cannot be filed; give it the empty tag set "
                "to declare that it is general rather than untagged")
        if tags.matches(request):
            kept.append(row)
    return tuple(kept)


def combinations(space: dict) -> tuple:
    """Every combination of the values a caller cares about, in a stable order."""
    dimensions = []
    for dimension in TAG_DIMENSIONS:
        values = _clean(space.get(dimension, ()))
        if values:
            dimensions.append((dimension, values))
    unknown = [dimension for dimension in space if dimension not in TAG_DIMENSIONS]
    if unknown:
        raise TaggingError(f"{unknown} is not drawn from {TAG_DIMENSIONS}")
    if not dimensions:
        return ()
    out = [{}]
    for dimension, values in dimensions:
        out = [{**row, dimension: (value,)} for row in out for value in values]
    return tuple(TagSet(row) for row in out)


def coverage(rows, space: dict, *, tags_of=None) -> dict:
    """How many rows sit in each combination, and which combinations hold nothing specific.

    Two counts, because they answer different questions. ``items`` is
    everything a caller would receive there, including records that are
    general on these dimensions. ``specific`` is the records that actually
    declare a value on every dimension of the space. A general reading skill
    is served to a nurse asking in German, and it is not material written for
    a nurse in German, so only the second count says whether the combination
    is really covered. The empty list uses the second, and names exactly what
    to generate without anyone deciding by feel.
    """
    def _reader(row):
        if tags_of is not None:
            return tags_of(row)
        return getattr(row, "tags", None)

    wanted = [dimension for dimension in TAG_DIMENSIONS if space.get(dimension)]
    cells = []
    for combination in combinations(space):
        matched = select(rows, combination, tags_of=tags_of)
        specific = [row for row in matched
                    if all((_reader(row) or EMPTY_TAGS).on(dimension) for dimension in wanted)]
        cells.append({"tags": combination.to_dict(), "items": len(matched),
                      "specific": len(specific)})
    empty = [cell["tags"] for cell in cells if cell["specific"] == 0]
    return {"record_type": COVERAGE_RECORD_TYPE, "combinations": len(cells),
            "covered": len(cells) - len(empty), "empty": len(empty),
            "cells": cells, "empty_cells": empty, "dimensions": wanted}


def self_test() -> dict:
    """Closed dimensions refuse an unknown value, general matches anything, gaps are named."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except TaggingError:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    analyst = TagSet({"role": ("data analyst", "Data Analyst"), "language": ("en",),
                      "data_sensitivity": ("internal",)})
    check("a_closed_dimension_refuses_an_unknown_value_and_an_open_one_does_not",
          analyst.on("role") == ("data analyst",)
          and analyst.on("geography") == ()
          and refuses(lambda: TagSet({"data_sensitivity": ("secret",)}))
          and refuses(lambda: TagSet({"authentication": ("magic",)}))
          and refuses(lambda: TagSet({"job": ("analyst",)}))
          and refuses(lambda: TagSet("not a mapping"))
          and TagSet({"role": ("chief financial officer",)}).on("role")
          == ("chief financial officer",),
          str(analyst.to_dict()))

    class _Row:
        def __init__(self, identity, tags):
            self.identity, self.tags = identity, TagSet(tags)

    rows = (
        _Row("general.reading", {}),
        _Row("analyst.english", {"role": ("data analyst",), "language": ("en",)}),
        _Row("analyst.german", {"role": ("data analyst",), "language": ("de",)}),
        _Row("nurse.regulated", {"role": ("nurse",), "data_sensitivity": ("regulated",)}),
    )
    english_analyst = select(rows, TagSet({"role": ("data analyst",), "language": ("en",)}))
    any_role = select(rows, TagSet({"language": ("de",)}))
    check("a_record_general_on_a_dimension_matches_any_request_on_it",
          [row.identity for row in english_analyst] == ["general.reading", "analyst.english"]
          and [row.identity for row in any_role] == [
              "general.reading", "analyst.german", "nurse.regulated"]
          and [row.identity for row in select(rows, EMPTY_TAGS)] == [
              "general.reading", "analyst.english", "analyst.german", "nurse.regulated"],
          str([row.identity for row in english_analyst]))
    check("alternatives_within_a_dimension_and_requirements_across_them",
          [row.identity for row in select(
              rows, TagSet({"role": ("data analyst", "nurse")}))]
          == ["general.reading", "analyst.english", "analyst.german", "nurse.regulated"]
          and [row.identity for row in select(
              rows, TagSet({"role": ("nurse",), "data_sensitivity": ("regulated",)}))]
          == ["general.reading", "nurse.regulated"]
          and [row.identity for row in select(
              rows, TagSet({"role": ("nurse",), "language": ("en",)}))]
          == ["general.reading", "nurse.regulated"])
    space = {"role": ("data analyst", "nurse"), "language": ("en", "de")}
    every = combinations(space)
    report = coverage(rows, space)
    check("the_combination_space_is_enumerated_and_the_empty_cells_are_named",
          len(every) == 4 and report["combinations"] == 4
          and report["covered"] == 2 and report["empty"] == 2
          # Every cell receives the general record, and only two hold material
          # written for that exact role and language.
          and all(cell["items"] >= 1 for cell in report["cells"])
          and sorted(tuple(cell["role"]) + tuple(cell["language"])
                     for cell in report["empty_cells"])
          == [("nurse", "de"), ("nurse", "en")]
          and report["dimensions"] == ["role", "language"],
          str(report["empty_cells"]))
    check("an_unknown_dimension_in_a_space_and_an_untyped_row_are_refused",
          refuses(lambda: combinations({"job": ("analyst",)}))
          and refuses(lambda: select(rows, {"role": ("x",)}))
          and refuses(lambda: select((object(),), EMPTY_TAGS))
          and refuses(lambda: select((_Row("x", {}), object()), EMPTY_TAGS))
          and combinations({}) == ()
          and coverage(rows, {})["combinations"] == 0)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "intelligence_tagging_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
