"""Answer whether a product version is supported on a day, from the radar's dated support calendar.

Standard library only. It reads the calendar this package carries
(references/support-calendar.json), never the network, and writes nothing.

    python scripts/check_support_window.py '{"product": "python", "version": "3.12.4", "on": "2026-10-01"}'

A version is matched to the longest release cycle it starts with (3.12.4 is
cycle 3.12). A version the calendar does not hold is answered as unknown,
never as supported. After the calendar's valid-until day the helper answers
calendar_expired instead of a support state.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

CALENDAR = Path(__file__).resolve().parent.parent / "references" / "support-calendar.json"
RESULT = "knowledge_radar_support_window_result/v1"
ERROR = "knowledge_radar_tool_error/v1"
FIELDS = ("product", "version", "on", "warn_days")


class RequestInvalid(ValueError):
    pass


class CalendarInvalid(ValueError):
    pass


def check_request(request) -> dict:
    if type(request) is not dict or set(request) - set(FIELDS) or "product" not in request or "version" not in request:
        raise RequestInvalid("the request names product and version, and optionally on and warn_days")
    product, version = request["product"], request["version"]
    if type(product) is not str or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,60}", product):
        raise RequestInvalid("product is an endoflife.date product name such as python")
    if type(version) is not str or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,40}", version):
        raise RequestInvalid("version is a version or a release cycle such as 3.12 or 3.12.4")
    on = request.get("on")
    if on is not None:
        if type(on) is not str:
            raise RequestInvalid("on is a day written YYYY-MM-DD")
        try:
            date.fromisoformat(on)
        except ValueError:
            raise RequestInvalid("on is a day written YYYY-MM-DD") from None
    warn = request.get("warn_days", 90)
    if type(warn) is not int or not 0 <= warn <= 3650:
        raise RequestInvalid("warn_days is 0 to 3650")
    return {"product": product, "version": version, "on": on, "warn_days": warn}


def check_calendar(calendar) -> None:
    if (type(calendar) is not dict or calendar.get("record_type") != "knowledge_radar_table/v1"
            or type(calendar.get("rows")) is not list or type(calendar.get("valid_until")) is not str):
        raise CalendarInvalid("the calendar is not a knowledge_radar_table/v1 record")


def _cycle(rows, product: str, version: str):
    matches = [row for row in rows if isinstance(row, dict) and row.get("product") == product
               and isinstance(row.get("cycle"), str)
               and (version == row["cycle"] or version.startswith(row["cycle"] + "."))]
    return max(matches, key=lambda row: len(row["cycle"]), default=None)


def run(request, calendar, today: "str | None" = None) -> dict:
    need = check_request(request)
    check_calendar(calendar)
    day = need["on"] or today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = {"record_type": RESULT, "product": need["product"], "version": need["version"], "on": day,
              "as_of": calendar.get("as_of"), "valid_until": calendar["valid_until"], "cycle": None,
              "eol_from": None, "eoas_from": None, "days_left": None, "latest": None, "lts": None, "source": None}
    if date.fromisoformat(today or datetime.now(timezone.utc).strftime("%Y-%m-%d")) > date.fromisoformat(calendar["valid_until"]):
        result["state"] = "calendar_expired"
        return result
    row = _cycle(calendar["rows"], need["product"], need["version"])
    if row is None:
        result["state"] = "unknown_version"
        return result
    eol = row.get("eol_from") if isinstance(row.get("eol_from"), str) else None
    result.update(cycle=row["cycle"], eol_from=eol, eoas_from=row.get("eoas_from"), latest=row.get("latest"),
                  lts=row.get("lts"), source=row.get("url"))
    if eol is None:
        result["state"] = "supported_no_end_date_published" if row.get("maintained") else "unknown_version"
        return result
    left = (date.fromisoformat(eol) - date.fromisoformat(day)).days
    result["days_left"] = left
    result["state"] = "unsupported" if left <= 0 else ("support_ending_soon" if left <= need["warn_days"] else "supported")
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
        calendar = json.loads(CALENDAR.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return _error("calendar_unreadable", type(error).__name__, 3)
    try:
        result = run(request, calendar)
    except RequestInvalid as error:
        return _error("request_invalid", str(error), 2)
    except CalendarInvalid as error:
        return _error("calendar_invalid", str(error), 3)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
