"""Plan remote MCP setup from the package's dated table. No network, mutation, authentication or tool calls."""
from __future__ import annotations

from datetime import date, datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

REQUEST = "mcp_setup_plan_request/v1"
RESULT = "mcp_setup_plan_result/v1"
ERROR = "mcp_setup_plan_error/v1"
MAXIMUM_BYTES = 131072
MAXIMUM_ROWS = 100
TABLE = Path(__file__).resolve().parent.parent / "references/mcp-services-table.json"
FIELDS = {"record_type", "query", "publisher", "transport", "count", "on"}
AUTH = {"unknown", "none_declared", "oauth", "key", "oauth_or_key"}
ROW_FIELDS = {"key", "title", "url", "documentation", "publisher", "transport", "authentication",
              "capabilities", "compatibility_basis", "transport_conflict", "source_updated_at", "last_verified_at", "review_after"}


class Invalid(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Invalid(code)


def text(value, maximum=300):
    return isinstance(value, str) and 0 < len(value) <= maximum and all(ord(character) >= 32 for character in value)


def day(value):
    require(isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d\d-\d\d", value)), "invalid_date")
    try:
        require(date.fromisoformat(value).isoformat() == value, "invalid_date")
    except ValueError:
        raise Invalid("invalid_date") from None
    return value


def public_url(value):
    require(text(value, 600), "invalid_source_url")
    try:
        parts = urlsplit(value)
        host = parts.hostname or ""
        require(parts.scheme == "https" and parts.username is None and parts.password is None
                and parts.port is None and not parts.query and not parts.fragment and "." in host
                and not host.endswith((".local", ".internal", ".localhost", ".localdomain", ".lan", ".home", ".corp", ".test", ".invalid", ".example", "."))
                and not host.split(".")[-1].isdigit()
                and all(re.fullmatch(r"(?!-)[a-z0-9-]{1,63}(?<!-)", label) for label in host.split("."))
                and bool(re.fullmatch(r"[a-z0-9.-]+", host))
                and not any(char in value for char in ('\\', ' ', '<', '>', '"', '{', '}')),
                "invalid_source_url")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return value
        raise Invalid("invalid_source_url")
    except ValueError:
        raise Invalid("invalid_source_url") from None


def parse_json(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAXIMUM_BYTES, "input_too_large")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def constant(_value):
        raise Invalid("nonfinite_json_value")
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, Invalid):
            raise
        raise Invalid("invalid_json") from None


def check_request(request):
    require(type(request) is dict and not set(request) - FIELDS and request.get("record_type") == REQUEST,
            "invalid_request")
    value = {"query": "", "publisher": "", "transport": "streamable-http", "count": 5,
             "on": datetime.now(timezone.utc).date().isoformat(), **request}
    require(isinstance(value["query"], str) and len(value["query"]) <= 160
            and bool(re.fullmatch(r"[A-Za-z0-9 ._-]*", value["query"])), "invalid_query")
    require(isinstance(value["publisher"], str) and len(value["publisher"]) <= 120
            and bool(re.fullmatch(r"[a-z0-9.-]*", value["publisher"])), "invalid_publisher")
    require(value["transport"] in ("streamable-http", "sse") and type(value["count"]) is int
            and 1 <= value["count"] <= 20, "invalid_request")
    day(value["on"])
    return value


def check_table(table):
    require(type(table) is dict and set(table) == {"record_type", "question_id", "as_of", "valid_until", "columns", "rows"}
            and table["record_type"] == "knowledge_radar_table/v1" and table["question_id"] == "mcp_service_setup",
            "invalid_table")
    day(table["as_of"]); day(table["valid_until"])
    require(table["as_of"] <= table["valid_until"] and type(table["columns"]) is list
            and all(isinstance(column, str) for column in table["columns"])
            and len(table["columns"]) == len(ROW_FIELDS) and set(table["columns"]) == ROW_FIELDS
            and type(table["rows"]) is list and len(table["rows"]) <= MAXIMUM_ROWS, "invalid_table")
    seen = set()
    for row in table["rows"]:
        require(type(row) is dict and set(row) == ROW_FIELDS, "invalid_row")
        for field in ("key", "title", "publisher", "capabilities"):
            require(text(row[field]), "invalid_row")
        require(row["key"] not in seen and isinstance(row["authentication"], str) and row["authentication"] in AUTH
                and row["transport"] in ("streamable-http", "sse")
                and row["compatibility_basis"] in ("publisher_declared", "registry_declared")
                and type(row["transport_conflict"]) is bool, "invalid_row")
        seen.add(row["key"])
        public_url(row["url"]); public_url(row["documentation"])
        day(row["last_verified_at"]); day(row["review_after"])
        require(row["last_verified_at"] <= table["as_of"] and row["last_verified_at"] <= row["review_after"], "invalid_row")
        if row["source_updated_at"] is not None:
            day(row["source_updated_at"])


def run(request, table):
    need = check_request(request)
    check_table(table)
    result = {"record_type": RESULT, "on": need["on"], "as_of": table["as_of"], "valid_until": table["valid_until"],
              "state": "source_candidates", "candidates": [], "withheld": [], "connection_attempted": False,
              "tool_calls_performed": 0, "effects_authorized": [], "client_configuration_generated": False,
              "basis": "Dated source declarations only; no authenticated connection or successful tool operation is established."}
    if need["on"] < table["as_of"]:
        result["state"] = "table_not_yet_current"
        return result
    if need["on"] > table["valid_until"]:
        result["state"] = "table_expired"
        return result
    tokens = need["query"].lower().split()
    for row in sorted(table["rows"], key=lambda row: (row["publisher"], row["title"], row["key"])):
        searchable = (row["title"] + " " + row["capabilities"]).lower()
        if any(token not in searchable for token in tokens) or (need["publisher"] and row["publisher"] != need["publisher"]):
            continue
        reason = ("source_review_due" if row["review_after"] < need["on"] else
                  "transport_conflict" if row["transport_conflict"] else
                  "transport_not_matched" if row["transport"] != need["transport"] else None)
        if reason:
            result["withheld"].append({"key": row["key"], "reason": reason, "documentation": row["documentation"]})
            continue
        if len(result["candidates"]) == need["count"]:
            continue
        result["candidates"].append({
            "key": row["key"], "title": row["title"], "endpoint": row["url"], "documentation": row["documentation"],
            "publisher": row["publisher"], "transport": row["transport"], "authentication": row["authentication"],
            "compatibility_basis": row["compatibility_basis"], "source_updated_at": row["source_updated_at"],
            "documentation_checked_on": row["last_verified_at"], "setup_state": "not_connected_not_tested",
            "next_checks": ["Confirm current publisher endpoint and client transport support.",
                            "Resolve authentication and least required scopes; obtain separate connection authority.",
                            "After authorized setup, record the negotiated protocol and actual tool schemas.",
                            "Test one permitted harmless read; keep write effects disabled unless separately authorized."]})
    if not result["candidates"]:
        result["state"] = "source_recheck_required" if result["withheld"] else "no_matching_source"
    return result


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    try:
        require(len(arguments) == 1, "one_request_required")
        raw = sys.stdin.buffer.read(MAXIMUM_BYTES + 1) if arguments[0] == "-" else arguments[0].encode("utf-8")
        request = check_request(parse_json(raw))
        require(TABLE.resolve().is_relative_to(Path(__file__).resolve().parent.parent), "table_path_unsafe")
        with TABLE.open("rb") as stream:
            table = parse_json(stream.read(MAXIMUM_BYTES + 1))
        result = run(request, table)
    except (Invalid, OSError) as error:
        code = str(error) if isinstance(error, Invalid) else "table_unavailable"
        print(json.dumps({"record_type": ERROR, "code": code}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
