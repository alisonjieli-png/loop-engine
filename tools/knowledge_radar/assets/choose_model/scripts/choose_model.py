"""Shortlist models for a structured extraction step from the radar's dated table, under the caller's constraints.

Standard library only. It reads the table this package carries
(references/models-table.json), never the network, and writes nothing.

    python scripts/choose_model.py '{"expected_input_tokens": 1500, "expected_output_tokens": 200, "count": 3}'

Rule: among models that meet every constraint, the lowest estimated listed
cost per call wins (listed input price times the expected input tokens plus
listed output price times the expected output tokens); ties go to the lower
output price, then the name. A value the table does not know counts as not
meeting a constraint that needs it, and a model whose retirement date has
passed is never chosen. The table holds listed prices and capability flags
from openly licensed catalogues (models.dev and the LiteLLM price map): the
answer is a shortlist for an acceptance check on the caller's own route, not
a measured cost per accepted task, and it says so.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

TABLE = Path(__file__).resolve().parent.parent / "references" / "models-table.json"
RESULT = "knowledge_radar_choose_model_result/v2"
ERROR = "knowledge_radar_tool_error/v1"
FIELDS = {"needs_structured_output": bool, "needs_tool_calling": bool, "needs_reasoning": bool,
          "minimum_context": int, "maximum_output_price": (int, float), "maximum_cost_per_call": (int, float),
          "expected_input_tokens": int, "expected_output_tokens": int, "open_weights_only": bool,
          "allowed_providers": list, "include_free_listings": bool, "count": int, "today": str}
DEFAULTS = {"needs_structured_output": True, "needs_tool_calling": False, "needs_reasoning": False,
            "minimum_context": 0, "maximum_output_price": None, "maximum_cost_per_call": None,
            "expected_input_tokens": 1000, "expected_output_tokens": 300, "open_weights_only": False,
            "allowed_providers": None, "include_free_listings": False, "count": 5, "today": None}
NULLABLE = ("maximum_output_price", "maximum_cost_per_call", "allowed_providers", "today")


class RequestInvalid(ValueError):
    pass


class TableInvalid(ValueError):
    pass


def check_request(request) -> dict:
    if type(request) is not dict or set(request) - set(FIELDS):
        raise RequestInvalid("the request is one JSON object with only the documented fields")
    value = dict(DEFAULTS)
    for name, item in request.items():
        kind = FIELDS[name]
        if item is None and name in NULLABLE:
            continue
        if isinstance(item, bool) and kind is not bool:
            raise RequestInvalid(f"{name} has the wrong type")
        if not isinstance(item, kind):
            raise RequestInvalid(f"{name} has the wrong type")
        value[name] = item
    if not 1 <= value["count"] <= 20:
        raise RequestInvalid("count is 1 to 20")
    for name in ("minimum_context", "expected_input_tokens", "expected_output_tokens"):
        if value[name] < 0:
            raise RequestInvalid(f"{name} is zero or more")
    for name in ("maximum_output_price", "maximum_cost_per_call"):
        if value[name] is not None and value[name] < 0:
            raise RequestInvalid(f"{name} is zero or more")
    if value["allowed_providers"] is not None and any(type(item) is not str for item in value["allowed_providers"]):
        raise RequestInvalid("allowed_providers is a list of provider names")
    if value["today"] is not None:
        try:
            date.fromisoformat(value["today"])
        except ValueError:
            raise RequestInvalid("today is a day written YYYY-MM-DD") from None
    return value


def check_table(table) -> None:
    if (type(table) is not dict or table.get("record_type") != "knowledge_radar_table/v1"
            or type(table.get("rows")) is not list or type(table.get("valid_until")) is not str):
        raise TableInvalid("the model table is not a knowledge_radar_table/v1 record")


def cost_per_call(row: dict, need: dict):
    """Listed US dollars for one call of the expected size, or None when a price is unknown."""
    output = row.get("output_price")
    given = row.get("input_price")
    if not isinstance(output, (int, float)) or isinstance(output, bool):
        return None
    if not isinstance(given, (int, float)) or isinstance(given, bool):
        return None
    return round((given * need["expected_input_tokens"] + output * need["expected_output_tokens"]) / 1_000_000, 8)


def _reject(row: dict, need: dict, day: str):
    """The first reason a row fails the constraints, or None when it meets them all."""
    for flag, name in (("needs_structured_output", "structured_output"), ("needs_tool_calling", "tool_calling"),
                       ("needs_reasoning", "reasoning")):
        if need[flag] and row.get(name) is not True:
            return f"{name.replace('_', ' ')} not listed"
    retires = row.get("deprecation_date")
    if isinstance(retires, str) and retires[:10] <= day:
        return "retirement date reached"
    if need["open_weights_only"] and row.get("open_weights") is not True:
        return "open weights not listed"
    if need["minimum_context"] and not (isinstance(row.get("context"), int) and row["context"] >= need["minimum_context"]):
        return "context unknown or too small"
    if need["allowed_providers"] is not None and row.get("provider") not in need["allowed_providers"]:
        return "provider not allowed"
    cost = cost_per_call(row, need)
    if cost is None:
        return "price unknown"
    if cost == 0 and not need["include_free_listings"]:
        return "free listing; its limits and terms vary"
    if need["maximum_output_price"] is not None and row["output_price"] > need["maximum_output_price"]:
        return "output price above the maximum"
    if need["maximum_cost_per_call"] is not None and cost > need["maximum_cost_per_call"]:
        return "cost per call above the maximum"
    return None


def run(request, table, today: "str | None" = None) -> dict:
    need = check_request(request)
    check_table(table)
    day = need["today"] or today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = {"record_type": RESULT, "as_of": table.get("as_of"), "valid_until": table["valid_until"], "on": day,
              "rule": "lowest estimated listed cost per call; ties by output price, then name",
              "basis": "listed prices and capability flags from openly licensed catalogues; a shortlist for the "
                       "acceptance check on your own route, not a measured cost per accepted task",
              "expected_input_tokens": need["expected_input_tokens"],
              "expected_output_tokens": need["expected_output_tokens"], "chosen": [], "rejected": {}}
    if date.fromisoformat(day) > date.fromisoformat(table["valid_until"]):
        result["state"] = "table_expired"
        result["note"] = "The table is past its valid-until day; search Baltor for a newer radar table."
        return result
    eligible = []
    for row in table["rows"]:
        if not isinstance(row, dict):
            continue
        reason = _reject(row, need, day)
        if reason:
            result["rejected"][reason] = result["rejected"].get(reason, 0) + 1
        else:
            eligible.append((cost_per_call(row, need), row))
    eligible.sort(key=lambda pair: (pair[0], pair[1]["output_price"], str(pair[1].get("title"))))
    result["chosen"] = [{**{name: row.get(name) for name in ("title", "url", "provider", "model_id", "input_price",
                                                            "output_price", "context", "structured_output",
                                                            "tool_calling", "deprecation_date")},
                         "estimated_cost_per_call": cost} for cost, row in eligible[:need["count"]]]
    result["state"] = "chosen" if result["chosen"] else "no_eligible_option"
    return result


def _error(code: str, message: str, exit_code: int) -> int:
    print(json.dumps({"record_type": ERROR, "code": code, "message": message[:300]}))
    return exit_code


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        request = json.loads(sys.stdin.read() if argv and argv[0] == "-" else (argv[0] if argv else "{}"))
    except ValueError:
        return _error("request_invalid", "the argument is not one JSON object", 2)
    try:
        table = json.loads(TABLE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return _error("table_unreadable", type(error).__name__, 3)
    try:
        result = run(request, table)
    except RequestInvalid as error:
        return _error("request_invalid", str(error), 2)
    except TableInvalid as error:
        return _error("table_invalid", str(error), 3)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
