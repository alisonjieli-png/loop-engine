"""Choose models from the radar's dated model table under the caller's constraints.

Standard library only. It reads the table this package carries
(references/models-table.json), never the network, and writes nothing.

    python scripts/choose_model.py '{"needs_tool_calling": true, "maximum_output_price": 2}'

Rule: among models that meet every constraint, the lowest listed output price
per published intelligence index point wins; ties go to the lower output
price, then the name. A value the table does not know counts as not meeting a
constraint that needs it. The answer is built from published prices and
published index values: it is not a cost per accepted task on the caller's
own work, and it says so.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

TABLE = Path(__file__).resolve().parent.parent / "references" / "models-table.json"
RESULT = "knowledge_radar_choose_model_result/v1"
ERROR = "knowledge_radar_tool_error/v1"
FIELDS = {"needs_tool_calling": bool, "needs_structured_output": bool, "needs_reasoning": bool,
          "minimum_context": int, "maximum_output_price": (int, float), "minimum_intelligence_index": (int, float),
          "open_weights_only": bool, "allowed_licences": list, "count": int, "today": str}
DEFAULTS = {"needs_tool_calling": True, "needs_structured_output": False, "needs_reasoning": False,
            "minimum_context": 0, "maximum_output_price": None, "minimum_intelligence_index": None,
            "open_weights_only": False, "allowed_licences": None, "count": 3, "today": None}


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
        if item is None and name in ("maximum_output_price", "minimum_intelligence_index", "allowed_licences", "today"):
            continue
        if isinstance(item, bool) and kind is not bool:
            raise RequestInvalid(f"{name} has the wrong type")
        if not isinstance(item, kind):
            raise RequestInvalid(f"{name} has the wrong type")
        value[name] = item
    if not 1 <= value["count"] <= 10:
        raise RequestInvalid("count is 1 to 10")
    if value["minimum_context"] < 0:
        raise RequestInvalid("minimum_context is zero or more")
    if value["maximum_output_price"] is not None and value["maximum_output_price"] < 0:
        raise RequestInvalid("maximum_output_price is zero or more")
    if value["allowed_licences"] is not None and any(type(item) is not str for item in value["allowed_licences"]):
        raise RequestInvalid("allowed_licences is a list of licence names")
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


def _reject(row: dict, need: dict):
    """The first reason a row fails the constraints, or None when it meets them all."""
    for flag, name in (("needs_tool_calling", "tool_calling"), ("needs_structured_output", "structured_output"),
                       ("needs_reasoning", "reasoning")):
        if need[flag] and row.get(name) is not True:
            return f"{name.replace('_', ' ')} not listed"
    if need["open_weights_only"] and row.get("open_weights") is not True:
        return "open weights not listed"
    if need["minimum_context"] and not (isinstance(row.get("context"), int) and row["context"] >= need["minimum_context"]):
        return "context unknown or too small"
    points = row.get("price_per_intelligence_point")
    price = row.get("output_price")
    if not isinstance(points, (int, float)) or not isinstance(price, (int, float)):
        return "price or index unknown"
    if need["maximum_output_price"] is not None and price > need["maximum_output_price"]:
        return "output price above the maximum"
    index = row.get("intelligence_index")
    if need["minimum_intelligence_index"] is not None and not (isinstance(index, (int, float))
                                                               and index >= need["minimum_intelligence_index"]):
        return "intelligence index unknown or below the minimum"
    if need["allowed_licences"] is not None and row.get("licence") not in need["allowed_licences"]:
        return "licence not allowed"
    return None


def run(request, table, today: "str | None" = None) -> dict:
    need = check_request(request)
    check_table(table)
    day = need["today"] or today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = {"record_type": RESULT, "as_of": table.get("as_of"), "valid_until": table["valid_until"], "on": day,
              "rule": "lowest listed output price per published intelligence index point; ties by output price, then name",
              "basis": "published list prices and published index values; not a cost per accepted task on your work",
              "chosen": [], "rejected": {}}
    if date.fromisoformat(day) > date.fromisoformat(table["valid_until"]):
        result["state"] = "table_expired"
        result["note"] = "The table is past its valid-until day; search Baltor for a newer radar table."
        return result
    eligible = []
    for row in table["rows"]:
        if not isinstance(row, dict):
            continue
        reason = _reject(row, need)
        if reason:
            result["rejected"][reason] = result["rejected"].get(reason, 0) + 1
        else:
            eligible.append(row)
    eligible.sort(key=lambda row: (row["price_per_intelligence_point"], row["output_price"], str(row.get("title"))))
    result["chosen"] = [{name: row.get(name) for name in ("title", "url", "output_price", "input_price", "price_provider",
                                                          "price_as_of", "intelligence_index",
                                                          "price_per_intelligence_point", "context", "licence")}
                        for row in eligible[:need["count"]]]
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
