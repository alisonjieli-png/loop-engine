"""A typed suggested output for one model call, so every answer can be learned from.

An instruction such as "answer in JSON" leaves the shape of the answer to the
model. A suggested output says what shape the caller wants: a scalar, a list, a
ranked list of at most ten rows with a candidate and a confidence from 0 to
100, a table with named columns, or an object; whether abstaining is allowed;
and which registered contract the answer belongs to. The suggestion is
rendered into the instruction the model receives, recorded beside the call,
and checked deterministically against the admitted value, so records of many
calls share one vocabulary that a later training pass can group by.

A suggestion is advice about shape. It never adds a task requirement, and a
deviation is recorded as a diagnostic, not treated as a task failure.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..strings.output_templates import OUTPUT_FORMS

#: The answer shapes a caller can suggest.
SHAPES = ("scalar", "list", "ranked_list", "table", "object")
#: How a confidence value in the answer is scaled.
CONFIDENCE_SCALES = ("none", "unit_interval", "percent")
#: Shapes whose rows carry named columns.
COLUMN_SHAPES = SHAPES[2:4]
#: The confidence column name a ranked list carries when a scale is set.
CONFIDENCE_COLUMN = "confidence"
#: The abstention envelope a model may return when nothing qualifies.
ABSTENTION_FIELDS = ("abstained", "reason")


class SuggestedOutputError(ValueError):
    """A suggested output is not a valid suggestion."""


@dataclass(frozen=True)
class SuggestedOutput:
    """The shape one model call is asked to answer in."""

    shape: str
    columns: tuple[str, ...] = ()
    cardinality: int = 0
    confidence_scale: str = CONFIDENCE_SCALES[0]
    abstention_allowed: bool = True
    form: str = ""
    schema_ref: str = ""
    notes: str = ""
    #: The one top-level key under which the suggested shape lives; empty
    #: when the whole answer is the shape.
    path: str = ""

    def __post_init__(self):
        if self.shape not in SHAPES:
            raise SuggestedOutputError(f"shape must be one of {SHAPES}")
        columns = tuple(self.columns)
        if any(not isinstance(item, str) or not item.strip() for item in columns):
            raise SuggestedOutputError("columns must be nonempty names")
        if len(set(columns)) != len(columns):
            raise SuggestedOutputError("columns must be unique")
        if self.shape in COLUMN_SHAPES and not columns:
            raise SuggestedOutputError(f"a {self.shape} suggestion names its columns")
        if self.shape not in COLUMN_SHAPES and columns:
            raise SuggestedOutputError(f"a {self.shape} suggestion carries no columns")
        if type(self.cardinality) is not int or self.cardinality < 0:
            raise SuggestedOutputError("cardinality must be a non-negative integer")
        if self.shape in (SHAPES[0], SHAPES[4]) and self.cardinality:
            raise SuggestedOutputError(f"a {self.shape} suggestion has no cardinality")
        if self.confidence_scale not in CONFIDENCE_SCALES:
            raise SuggestedOutputError(f"confidence scale must be one of {CONFIDENCE_SCALES}")
        if (self.confidence_scale != CONFIDENCE_SCALES[0] and self.shape in COLUMN_SHAPES
                and CONFIDENCE_COLUMN not in columns):
            raise SuggestedOutputError(
                f"a scaled confidence needs a {CONFIDENCE_COLUMN!r} column")
        if type(self.abstention_allowed) is not bool:
            raise SuggestedOutputError("abstention_allowed must be a Boolean")
        if self.form and self.form not in OUTPUT_FORMS:
            raise SuggestedOutputError(f"form must be empty or one of {OUTPUT_FORMS}")
        for name in ("schema_ref", "notes", "path"):
            if not isinstance(getattr(self, name), str):
                raise SuggestedOutputError(f"{name} must be text")
        object.__setattr__(self, "columns", columns)

    def to_dict(self) -> dict:
        return {"record_type": "suggested_output/v1", "shape": self.shape,
                "columns": list(self.columns), "cardinality": self.cardinality,
                "confidence_scale": self.confidence_scale,
                "abstention_allowed": self.abstention_allowed, "form": self.form,
                "schema_ref": self.schema_ref, "notes": self.notes, "path": self.path}

    @classmethod
    def from_dict(cls, value) -> "SuggestedOutput":
        if not isinstance(value, dict) or value.get("record_type") != "suggested_output/v1":
            raise SuggestedOutputError("a suggested output record needs record_type suggested_output/v1")
        return cls(shape=value.get("shape", ""), columns=tuple(value.get("columns") or ()),
                   cardinality=value.get("cardinality", 0),
                   confidence_scale=value.get("confidence_scale", CONFIDENCE_SCALES[0]),
                   abstention_allowed=value.get("abstention_allowed", True),
                   form=value.get("form", ""), schema_ref=value.get("schema_ref", ""),
                   notes=value.get("notes", ""), path=value.get("path", ""))

    @property
    def content_digest(self) -> str:
        body = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _confidence_text(self) -> str:
        if self.confidence_scale == CONFIDENCE_SCALES[1]:
            return f"{CONFIDENCE_COLUMN} is a number from 0 to 1"
        if self.confidence_scale == CONFIDENCE_SCALES[2]:
            return f"{CONFIDENCE_COLUMN} is a number from 0 to 100"
        return ""

    def to_instruction(self) -> str:
        """The suggestion as one deterministic sentence for the model."""
        limit = f" of at most {self.cardinality} rows" if self.cardinality else ""
        if self.shape == SHAPES[0]:
            body = "one value"
        elif self.shape == SHAPES[1]:
            body = "a list" + (f" of at most {self.cardinality} items" if self.cardinality else "")
        elif self.shape == SHAPES[2]:
            body = ("a ranked list" + limit + ", best first; each row is an object with at "
                    "least the keys " + ", ".join(self.columns))
        elif self.shape == SHAPES[3]:
            body = ("a table" + limit + "; each row is an object with at least the keys "
                    + ", ".join(self.columns))
        else:
            body = "one object"
        where = f' under the key "{self.path}",' if self.path else ""
        parts = ["Suggested output:" + where + " " + body + "."]
        confidence = self._confidence_text()
        if confidence:
            parts.append(confidence.capitalize() + ".")
        if self.abstention_allowed:
            parts.append("When nothing qualifies, return an object with abstained true and a reason.")
        else:
            parts.append("Abstaining is not an option for this answer.")
        if self.notes:
            parts.append(self.notes)
        return " ".join(parts)

    def _confidence_in_range(self, value) -> bool:
        if type(value) not in (int, float):
            return False
        if self.confidence_scale == CONFIDENCE_SCALES[1]:
            return 0 <= value <= 1
        return 0 <= value <= 100

    def check(self, value) -> dict:
        """Compare one admitted value with the suggestion; never raises."""
        problems = []
        if (isinstance(value, dict) and set(value) == set(ABSTENTION_FIELDS)
                and value.get(ABSTENTION_FIELDS[0]) is True):
            if not self.abstention_allowed:
                problems.append("abstained where abstention is not allowed")
            elif not isinstance(value.get(ABSTENTION_FIELDS[1]), str) or not value[ABSTENTION_FIELDS[1]].strip():
                problems.append("abstention without a reason")
            return {"record_type": "suggested_output_check/v1", "conforms": not problems,
                    "abstained": True, "problems": problems}
        if self.path:
            if not isinstance(value, dict) or self.path not in value:
                return {"record_type": "suggested_output_check/v1", "conforms": False,
                        "abstained": False,
                        "problems": [f"the suggested key {self.path!r} is missing"]}
            value = value[self.path]
        if self.shape == SHAPES[0]:
            if isinstance(value, (dict, list)):
                problems.append("a scalar was suggested, a structure was returned")
        elif self.shape == SHAPES[4]:
            if not isinstance(value, dict):
                problems.append("an object was suggested, another shape was returned")
        elif not isinstance(value, list):
            problems.append(f"a {self.shape} was suggested, a non-list was returned")
        else:
            if self.cardinality and len(value) > self.cardinality:
                problems.append(f"{len(value)} rows exceed the suggested {self.cardinality}")
            if self.shape in COLUMN_SHAPES:
                for index, row in enumerate(value):
                    if not isinstance(row, dict) or not set(self.columns) <= set(row):
                        problems.append(f"row {index} does not carry the suggested keys")
                        break
                    if (self.confidence_scale != CONFIDENCE_SCALES[0]
                            and not self._confidence_in_range(row.get(CONFIDENCE_COLUMN))):
                        problems.append(f"row {index} confidence is outside the suggested scale")
                        break
        return {"record_type": "suggested_output_check/v1", "conforms": not problems,
                "abstained": False, "problems": problems}


def self_test() -> dict:
    """Suggestion validity, the rendered instruction, and the deterministic check."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except SuggestedOutputError:
            return True
        return False

    ranked = SuggestedOutput(SHAPES[2], columns=("candidate", CONFIDENCE_COLUMN), cardinality=10,
                             confidence_scale=CONFIDENCE_SCALES[2])
    instruction = ranked.to_instruction()
    check("a_ranked_list_suggestion_renders_its_rows_scale_and_abstention",
          "at most 10 rows" in instruction and "candidate, confidence" in instruction
          and "from 0 to 100" in instruction and "abstained true" in instruction, instruction)
    rows = [{"candidate": "a", CONFIDENCE_COLUMN: 90}, {"candidate": "b", CONFIDENCE_COLUMN: 40}]
    check("rows_within_the_suggestion_conform", ranked.check(rows)["conforms"])
    too_many = ranked.check([{"candidate": str(i), CONFIDENCE_COLUMN: 1} for i in range(11)])
    wrong_keys = ranked.check([{"name": "a"}])
    out_of_scale = ranked.check([{"candidate": "a", CONFIDENCE_COLUMN: 250}])
    check("rows_outside_the_suggestion_are_named",
          not too_many["conforms"] and "exceed" in too_many["problems"][0]
          and not wrong_keys["conforms"] and "keys" in wrong_keys["problems"][0]
          and not out_of_scale["conforms"] and "scale" in out_of_scale["problems"][0])
    check("an_abstention_with_a_reason_conforms_when_allowed",
          ranked.check({"abstained": True, "reason": "no candidate qualifies"})["abstained"]
          and ranked.check({"abstained": True, "reason": "no candidate qualifies"})["conforms"]
          and not ranked.check({"abstained": True, "reason": ""})["conforms"])
    strict = SuggestedOutput(SHAPES[0], abstention_allowed=False)
    check("a_scalar_suggestion_refuses_abstention_and_structures_when_told",
          not strict.check({"abstained": True, "reason": "none"})["conforms"]
          and not strict.check([1, 2])["conforms"] and strict.check(7)["conforms"]
          and "not an option" in strict.to_instruction())
    check("invalid_suggestions_are_refused",
          all(refuses(action) for action in (
              lambda: SuggestedOutput("matrix"),
              lambda: SuggestedOutput(SHAPES[2]),
              lambda: SuggestedOutput(SHAPES[1], columns=("a",)),
              lambda: SuggestedOutput(SHAPES[0], cardinality=3),
              lambda: SuggestedOutput(SHAPES[2], columns=("a",), confidence_scale=CONFIDENCE_SCALES[2]),
              lambda: SuggestedOutput(SHAPES[2], columns=("a", "a")),
              lambda: SuggestedOutput(SHAPES[1], form="poem"))))
    check("a_suggestion_round_trips_with_a_stable_digest",
          SuggestedOutput.from_dict(ranked.to_dict()) == ranked
          and ranked.content_digest == SuggestedOutput.from_dict(ranked.to_dict()).content_digest
          and refuses(lambda: SuggestedOutput.from_dict({"shape": SHAPES[0]})))
    table = SuggestedOutput(SHAPES[3], columns=("name", "value"), form=OUTPUT_FORMS[2])
    check("a_table_suggestion_checks_its_columns_without_a_confidence",
          table.check([{"name": "x", "value": 1}])["conforms"]
          and not table.check([{"name": "x"}])["conforms"] and "keys name, value" in table.to_instruction())
    nested = SuggestedOutput(SHAPES[2], columns=("action_kind", CONFIDENCE_COLUMN), cardinality=2,
                             confidence_scale=CONFIDENCE_SCALES[1], path="actions")
    check("a_suggestion_may_live_under_one_key_and_rows_may_carry_more_keys",
          nested.check({"actions": [{"action_kind": "BUILD", CONFIDENCE_COLUMN: 0.9, "why": "x"}]})["conforms"]
          and not nested.check({"plans": []})["conforms"]
          and "missing" in nested.check({"plans": []})["problems"][0]
          and not nested.check({"actions": [{"action_kind": "a", CONFIDENCE_COLUMN: 1}] * 3})["conforms"]
          and not nested.check({"actions": [{"action_kind": "a", CONFIDENCE_COLUMN: 7}]})["conforms"]
          and 'under the key "actions", a ranked list of at most 2 rows' in nested.to_instruction()
          and SuggestedOutput.from_dict(nested.to_dict()) == nested)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "suggested_output_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
