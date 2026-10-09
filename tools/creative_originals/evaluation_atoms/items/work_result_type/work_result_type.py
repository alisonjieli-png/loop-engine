"""Typed work result: the one outcome a bounded unit of work returns, as a JSON Schema and a validator.

    Completed(artifact, evidence) | NoChangeNeeded(evidence) | NeedsInput(required_fields)
    | NeedsScopeExpansion(reason, proposed_scope) | Unsupported(reason) | BudgetExhausted(checkpoint, remaining_obligations)

The structural rules live in schema.json (embedded below so the module reads no file; the tests check the two are
identical). The validator adds the rules a schema cannot state:
- the artifact is not evidence for itself: a completed result cites at least one reference other than the artifact;
- needs_input field names are unique, and a "choice" field lists its choices (and only a choice field does);
- remaining obligations are unique;
- a scope expansion adds items it does not also remove, without repeats.

    echo '{"call": "validate_work_result", "arguments": {"result": {"record_type": "work_result/v1", "outcome": "unsupported", "reason": "needs a GPU"}}}' | python3 work_result_type.py
"""
from __future__ import annotations

import json

import atom_cli
import schema_lite

RECORD_TYPE = "work_result/v1"
#: The six outcomes, one for each result shape of the schema.
COMPLETED, NO_CHANGE_NEEDED, NEEDS_INPUT, NEEDS_SCOPE_EXPANSION, UNSUPPORTED, BUDGET_EXHAUSTED = (
    "completed", "no_change_needed", "needs_input", "needs_scope_expansion", "unsupported", "budget_exhausted")
TERMINAL = {COMPLETED: True, NO_CHANGE_NEEDED: True, UNSUPPORTED: True, NEEDS_INPUT: False,
            NEEDS_SCOPE_EXPANSION: False, BUDGET_EXHAUSTED: False}
NEXT_STEP = {
    COMPLETED: "check the cited evidence independently before accepting the artifact",
    NO_CHANGE_NEEDED: "close the work item and keep the evidence",
    NEEDS_INPUT: "ask for the listed fields, then rerun within the same budget",
    NEEDS_SCOPE_EXPANSION: "the owner of the scope decides; nothing outside the current scope runs meanwhile",
    UNSUPPORTED: "route the work to another capability or close it as unsupported",
    BUDGET_EXHAUSTED: "resume from the checkpoint with new budget, or record the remaining obligations as open",
}

_SCHEMA_TEXT = r'''{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Work result",
  "description": "The one outcome a bounded unit of work returns. Exactly one of six shapes, chosen by the outcome field: completed, no_change_needed, needs_input, needs_scope_expansion, unsupported or budget_exhausted.",
  "type": "object",
  "oneOf": [
    {"$ref": "#/$defs/completed"},
    {"$ref": "#/$defs/no_change_needed"},
    {"$ref": "#/$defs/needs_input"},
    {"$ref": "#/$defs/needs_scope_expansion"},
    {"$ref": "#/$defs/unsupported"},
    {"$ref": "#/$defs/budget_exhausted"}
  ],
  "$defs": {
    "text": {"type": "string", "minLength": 1, "maxLength": 2000, "pattern": "\\S"},
    "reference": {
      "description": "Where something can be found again: a file, a commit, a record, a message or an address.",
      "type": "object",
      "required": ["kind", "locator"],
      "additionalProperties": false,
      "properties": {
        "kind": {"enum": ["file", "commit", "record", "message", "address"]},
        "locator": {"$ref": "#/$defs/text"},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
      }
    },
    "evidence": {
      "description": "One observation that supports the outcome, how it was obtained and where it is kept.",
      "type": "object",
      "required": ["claim", "method", "reference"],
      "additionalProperties": false,
      "properties": {
        "claim": {"$ref": "#/$defs/text"},
        "method": {"enum": ["test", "measurement", "inspection", "citation", "external_confirmation"]},
        "reference": {"$ref": "#/$defs/reference"}
      }
    },
    "completed": {
      "type": "object",
      "required": ["record_type", "outcome", "artifact", "evidence"],
      "additionalProperties": false,
      "properties": {
        "record_type": {"const": "work_result/v1"},
        "outcome": {"const": "completed"},
        "artifact": {"$ref": "#/$defs/reference"},
        "evidence": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/evidence"}},
        "notes": {"$ref": "#/$defs/text"}
      }
    },
    "no_change_needed": {
      "type": "object",
      "required": ["record_type", "outcome", "evidence"],
      "additionalProperties": false,
      "properties": {
        "record_type": {"const": "work_result/v1"},
        "outcome": {"const": "no_change_needed"},
        "evidence": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/evidence"}},
        "notes": {"$ref": "#/$defs/text"}
      }
    },
    "needs_input": {
      "type": "object",
      "required": ["record_type", "outcome", "required_fields"],
      "additionalProperties": false,
      "properties": {
        "record_type": {"const": "work_result/v1"},
        "outcome": {"const": "needs_input"},
        "required_fields": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["name", "description"],
            "additionalProperties": false,
            "properties": {
              "name": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,63}$"},
              "description": {"$ref": "#/$defs/text"},
              "type": {"enum": ["text", "number", "integer", "boolean", "choice", "file", "secret_reference"]},
              "choices": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/text"}}
            }
          }
        },
        "notes": {"$ref": "#/$defs/text"}
      }
    },
    "needs_scope_expansion": {
      "type": "object",
      "required": ["record_type", "outcome", "reason", "proposed_scope"],
      "additionalProperties": false,
      "properties": {
        "record_type": {"const": "work_result/v1"},
        "outcome": {"const": "needs_scope_expansion"},
        "reason": {"$ref": "#/$defs/text"},
        "proposed_scope": {
          "type": "object",
          "required": ["add"],
          "additionalProperties": false,
          "properties": {
            "add": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/text"}},
            "remove": {"type": "array", "items": {"$ref": "#/$defs/text"}}
          }
        },
        "notes": {"$ref": "#/$defs/text"}
      }
    },
    "unsupported": {
      "type": "object",
      "required": ["record_type", "outcome", "reason"],
      "additionalProperties": false,
      "properties": {
        "record_type": {"const": "work_result/v1"},
        "outcome": {"const": "unsupported"},
        "reason": {"$ref": "#/$defs/text"},
        "notes": {"$ref": "#/$defs/text"}
      }
    },
    "budget_exhausted": {
      "type": "object",
      "required": ["record_type", "outcome", "checkpoint", "remaining_obligations"],
      "additionalProperties": false,
      "properties": {
        "record_type": {"const": "work_result/v1"},
        "outcome": {"const": "budget_exhausted"},
        "checkpoint": {"$ref": "#/$defs/reference"},
        "remaining_obligations": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/text"}},
        "consumed": {
          "type": "object",
          "additionalProperties": {"type": "number", "minimum": 0},
          "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,63}$"}
        },
        "notes": {"$ref": "#/$defs/text"}
      }
    }
  }
}
'''
SCHEMA = json.loads(_SCHEMA_TEXT)


def _semantic_errors(result):
    errors, outcome = [], result.get("outcome")
    if outcome == COMPLETED:
        artifact = json.dumps(result["artifact"], sort_keys=True)
        if all(json.dumps(row["reference"], sort_keys=True) == artifact for row in result["evidence"]):
            errors.append("#/evidence: the artifact is not evidence for itself; cite a test, record or measurement")
    if outcome == NEEDS_INPUT:
        names = [row["name"] for row in result["required_fields"]]
        if len(set(names)) != len(names):
            errors.append("#/required_fields: field names repeat")
        for index, row in enumerate(result["required_fields"]):
            if (row.get("type") == "choice") != ("choices" in row):
                errors.append(f"#/required_fields/{index}: a choice field lists choices, and only a choice field")
    if outcome == BUDGET_EXHAUSTED:
        obligations = result["remaining_obligations"]
        if len(set(obligations)) != len(obligations):
            errors.append("#/remaining_obligations: obligations repeat")
    if outcome == NEEDS_SCOPE_EXPANSION:
        add, remove = result["proposed_scope"]["add"], result["proposed_scope"].get("remove", [])
        if len(set(add)) != len(add) or set(add) & set(remove):
            errors.append("#/proposed_scope: items repeat or are both added and removed")
    return errors


def validate_work_result(result):
    """Check one work result against the schema and the semantic rules.

    Returns {"valid", "outcome" (or null when the outcome is unknown), "terminal" (or null), "errors"}."""
    errors = schema_lite.validate(result, SCHEMA)
    outcome = result.get("outcome") if isinstance(result, dict) else None
    known = isinstance(outcome, str) and outcome in TERMINAL
    if errors and known:
        # name the specific violations of the shape the outcome selects
        branch = {"$defs": SCHEMA["$defs"], **SCHEMA["$defs"][outcome]}
        errors = schema_lite.validate(result, branch) or errors
    if not errors:
        errors = _semantic_errors(result)
    return {"valid": not errors, "outcome": outcome if known else None,
            "terminal": TERMINAL[outcome] if known else None, "errors": errors}


def classify_work_result(result):
    """The outcome of a valid result, whether the work item is finished, and the next step it calls for.

    Raises ValueError for an invalid result. Returns {"outcome", "terminal", "next_step"}."""
    report = validate_work_result(result)
    if not report["valid"]:
        raise ValueError("invalid work result: " + "; ".join(report["errors"][:5]))
    outcome = report["outcome"]
    return {"outcome": outcome, "terminal": TERMINAL[outcome], "next_step": NEXT_STEP[outcome]}


def make_work_result(outcome, fields):
    """Build a result with the record type and outcome filled in; ValueError when it would be invalid."""
    if outcome not in TERMINAL:
        raise ValueError(f"outcome is one of {sorted(TERMINAL)}")
    if not isinstance(fields, dict) or {"record_type", "outcome"} & set(fields):
        raise ValueError("fields is an object without record_type or outcome")
    result = {"record_type": RECORD_TYPE, "outcome": outcome, **fields}
    report = validate_work_result(result)
    if not report["valid"]:
        raise ValueError("invalid work result: " + "; ".join(report["errors"][:5]))
    return result


FUNCTIONS = {"validate_work_result": validate_work_result, "classify_work_result": classify_work_result,
             "make_work_result": make_work_result}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["RECORD_TYPE", "TERMINAL", "NEXT_STEP", "SCHEMA", "validate_work_result", "classify_work_result",
           "make_work_result", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
