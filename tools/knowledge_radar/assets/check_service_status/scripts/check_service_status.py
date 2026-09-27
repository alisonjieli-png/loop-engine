#!/usr/bin/env python3
"""Report the current status of a developer service from its public Statuspage v2 JSON.

The tool reads https://<host>/api/v2/summary.json for one provider on its allow
list and returns the overall indicator, the components that are not operational
and the open incidents. It stores no status: every call reads the page again.

Call it with one JSON object, for example {"provider": "github"}, as the only
argument, or with "-" to read that object from standard input. It prints one
JSON object and exits 0 on success, 2 on an invalid request and 3 when the
source could not be read or answered in an unexpected shape.

Effects: one HTTPS GET to the status host of the chosen provider. It follows a
redirect only to the same host over HTTPS. It writes no file.
"""
from __future__ import annotations

import http.client
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

RESULT_RECORD = "knowledge_radar_check_service_status_result/v1"
ERROR_RECORD = "knowledge_radar_tool_error/v1"
USER_AGENT = "baltor-radar-tool/1.0"
TIMEOUT_SECONDS = 20
MAXIMUM_BYTES = 2 * 1024 * 1024
MAXIMUM_REQUEST_CHARACTERS = 65536
EXIT_INVALID_REQUEST = 2
EXIT_SOURCE_FAILED = 3

#: Short provider name and its status host. Each host answered one GET of
#: /api/v2/summary.json in the Statuspage v2 shape on 2026-09-27.
PROVIDERS = {
    "anthropic": "status.claude.com",
    "cloudflare": "www.cloudflarestatus.com",
    "digitalocean": "status.digitalocean.com",
    "flyio": "status.flyio.net",
    "github": "www.githubstatus.com",
    "netlify": "www.netlifystatus.com",
    "npm": "status.npmjs.org",
    "render": "status.render.com",
    "supabase": "status.supabase.com",
    "vercel": "www.vercel-status.com",
}
#: Incident states that mean an incident is over.
CLOSED_INCIDENT_STATES = ("resolved", "postmortem")
INCIDENT_FIELDS = ("name", "status", "impact", "started_at", "shortlink")


class ToolError(Exception):
    """A refusal: a snake_case code, a plain message and the exit code main() returns."""

    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code

    def to_record(self) -> dict:
        return {"record_type": ERROR_RECORD, "code": self.code, "message": self.message}


def invalid(message: str, code: str = "invalid_request") -> ToolError:
    return ToolError(code, message, EXIT_INVALID_REQUEST)


def source_failed(code: str, message: str) -> ToolError:
    return ToolError(code, message, EXIT_SOURCE_FAILED)


def unexpected(message: str) -> ToolError:
    return source_failed("unexpected_source_shape", message)


class SameHostRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to an https address on the host that was asked."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        asked = urllib.parse.urlsplit(req.full_url)
        target = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl))
        if target.scheme != "https" or target.hostname != asked.hostname:
            raise source_failed("redirect_refused", "the source redirected to another host or away from https")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def bounded_read(stream) -> bytes:
    """Reads at most 2 MB; a longer answer is refused, never cut short."""
    body = stream.read(MAXIMUM_BYTES + 1)
    if len(body) > MAXIMUM_BYTES:
        raise source_failed("source_too_large", "the source answer is larger than 2 MB")
    return body


def default_fetch(url: str, body, headers: dict) -> tuple:
    """GET (or POST when body is bytes) with a 20 second timeout; returns (status, body bytes)."""
    request = urllib.request.Request(url, data=body, headers={**headers, "User-Agent": USER_AGENT},
                                     method="GET" if body is None else "POST")
    opener = urllib.request.build_opener(SameHostRedirects)
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, bounded_read(response)
    except urllib.error.HTTPError as error:
        try:
            return error.code, bounded_read(error)
        finally:
            error.close()


def system_now() -> datetime:
    return datetime.now(timezone.utc)


def observed_at(now) -> str:
    moment = (now or system_now)()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_source(fetch, url: str, body, headers: dict) -> tuple:
    try:
        answer = fetch(url, body, headers)
    except (OSError, ValueError, http.client.HTTPException) as error:
        raise source_failed("source_unreachable", f"the source could not be read: {str(error)[:200]}") from error
    if (type(answer) is not tuple or len(answer) != 2 or type(answer[0]) is not int
            or type(answer[1]) is not bytes):
        raise source_failed("fetch_contract_invalid", "the fetch function did not return a status and bytes")
    return answer


def validate_request(request) -> str:
    """Mirrors contracts/input.schema.json: one object with exactly the field provider."""
    if type(request) is not dict:
        raise invalid("the request must be one JSON object")
    if set(request) - {"provider"}:
        raise invalid("the request may hold only the field provider")
    if "provider" not in request:
        raise invalid("the request needs the field provider")
    provider = request["provider"]
    if type(provider) is not str:
        raise invalid("provider must be a string")
    if provider not in PROVIDERS:
        raise invalid("provider must be one of: " + ", ".join(sorted(PROVIDERS)), code="unknown_provider")
    return provider


def refuse_constant(name: str):
    raise ValueError(f"{name} is not a JSON number")


def optional_text(mapping: dict, key: str, where: str):
    """The text the source gives, or None when the source leaves it out. Nothing is filled in."""
    value = mapping.get(key)
    if value is None or type(value) is str:
        return value
    raise unexpected(f"{where}.{key} is not text")


def parse_summary(body: bytes) -> dict:
    try:
        document = json.loads(body.decode("utf-8"), parse_constant=refuse_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise unexpected("the status page did not answer with JSON") from error
    if type(document) is not dict:
        raise unexpected("the status page answer is not a JSON object")
    for key, kind in (("page", dict), ("status", dict), ("components", list), ("incidents", list)):
        if type(document.get(key)) is not kind:
            raise unexpected(f"the answer has no Statuspage v2 {key} {'object' if kind is dict else 'list'}")
    return document


def non_operational(components: list) -> list:
    found = []
    for component in components:
        if (type(component) is not dict or type(component.get("name")) is not str
                or type(component.get("status")) is not str):
            raise unexpected("a component has no name and status text")
        if component["status"] != "operational":
            found.append({"name": component["name"], "status": component["status"]})
    return found


def open_incidents(incidents: list) -> list:
    found = []
    for incident in incidents:
        if type(incident) is not dict:
            raise unexpected("an incident is not a JSON object")
        record = {field: optional_text(incident, field, "incident") for field in INCIDENT_FIELDS}
        if record["status"] not in CLOSED_INCIDENT_STATES:
            found.append(record)
    return found


def run(request, fetch=None, now=None) -> dict:
    """Validates the request, reads the status page once and returns the result record.

    fetch(url, body_or_None, headers) returns (status, body bytes); now() returns the
    current time. Both default to the network and the system clock. A refusal raises
    ToolError; no partial result is ever returned.
    """
    provider = validate_request(request)
    url = f"https://{PROVIDERS[provider]}/api/v2/summary.json"
    status, body = read_source(fetch or default_fetch, url, None, {"Accept": "application/json"})
    moment = observed_at(now)
    if status != 200:
        raise source_failed("source_http_error", f"the status page answered with HTTP status {status}")
    try:
        summary = parse_summary(body)
        page, overall = summary["page"], summary["status"]
        return {
            "record_type": RESULT_RECORD,
            "provider": provider,
            "indicator": optional_text(overall, "indicator", "status"),
            "description": optional_text(overall, "description", "status"),
            "updated_at": optional_text(page, "updated_at", "page"),
            "non_operational_components": non_operational(summary["components"]),
            "open_incidents": open_incidents(summary["incidents"]),
            "source": url,
            "observed_at": moment,
        }
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise unexpected(f"the status page answer could not be read ({type(error).__name__})") from error


def unique_keys(pairs: list) -> dict:
    keys = [key for key, _value in pairs]
    if len(set(keys)) != len(keys):
        raise ValueError("a key is repeated")
    return dict(pairs)


def read_request(arguments: list, stdin):
    if len(arguments) != 1:
        raise invalid("give one JSON object as the only argument, or - to read it from standard input")
    text = stdin.read(MAXIMUM_REQUEST_CHARACTERS + 1) if arguments[0] == "-" else arguments[0]
    if len(text) > MAXIMUM_REQUEST_CHARACTERS:
        raise invalid(f"the request is longer than {MAXIMUM_REQUEST_CHARACTERS} characters")
    try:
        return json.loads(text, object_pairs_hook=unique_keys, parse_constant=refuse_constant)
    except (ValueError, RecursionError) as error:
        raise invalid("the request is not one valid JSON object") from error


def emit(stdout, record: dict) -> None:
    stdout.write(json.dumps(record) + "\n")


def main(arguments=None, fetch=None, now=None, stdin=None, stdout=None) -> int:
    """Command line: prints exactly one JSON object, the result or an error record."""
    arguments = sys.argv[1:] if arguments is None else arguments
    stdout = sys.stdout if stdout is None else stdout
    try:
        result = run(read_request(arguments, sys.stdin if stdin is None else stdin), fetch=fetch, now=now)
    except ToolError as error:
        emit(stdout, error.to_record())
        return error.exit_code
    except Exception as error:  # a defect still ends in the error record, never in a partial result
        emit(stdout, {"record_type": ERROR_RECORD, "code": "internal_error",
                      "message": f"the tool stopped on an unexpected {type(error).__name__}"})
        return EXIT_SOURCE_FAILED
    emit(stdout, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
