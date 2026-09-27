#!/usr/bin/env python3
"""Ask OSV.dev which published advisories affect one version of one package.

The tool sends POST https://api.osv.dev/v1/query with the package name, its
ecosystem and the version, follows OSV's page tokens (at most five pages), and
returns for each advisory its identifier, aliases, dates, severity entries and
the fixed versions named for that package. It does not return the free-text
details of an advisory. It stores no advisory list: every call asks OSV again.

Call it with one JSON object, for example
{"ecosystem": "PyPI", "name": "jinja2", "version": "2.4.1"}, as the only
argument, or with "-" to read that object from standard input. It prints one
JSON object and exits 0 on success, 2 on an invalid request and 3 when the
source could not be read or answered in an unexpected shape.

Effects: HTTPS POST requests to api.osv.dev only. It writes no file.
"""
from __future__ import annotations

import http.client
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

RESULT_RECORD = "knowledge_radar_query_package_advisories_result/v1"
ERROR_RECORD = "knowledge_radar_tool_error/v1"
USER_AGENT = "baltor-radar-tool/1.0"
TIMEOUT_SECONDS = 20
MAXIMUM_BYTES = 2 * 1024 * 1024
MAXIMUM_REQUEST_CHARACTERS = 65536
EXIT_INVALID_REQUEST = 2
EXIT_SOURCE_FAILED = 3

SOURCE = "https://api.osv.dev/v1/query"
DETAILS_ADDRESS = "https://osv.dev/vulnerability/"
ECOSYSTEMS = ("PyPI", "npm", "Go", "crates.io", "Maven", "NuGet", "RubyGems", "Packagist", "Hex", "Pub")
#: Package names such as jinja2, @scope/name, golang.org/x/net, group:artifact or vendor/package.
NAME_PATTERN = r"[A-Za-z0-9@][A-Za-z0-9._/:@+~-]*"
NAME_LIMIT = 300
#: Versions such as 2.4.1, 1.0.0-beta.1, v1.2.3, 2!1.0 or 1.0+local.
VERSION_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._+:~!-]*"
VERSION_LIMIT = 100
#: OSV identifiers such as GHSA-462w-v97r-4m45, PYSEC-2019-217 or RUSTSEC-2021-0001.
IDENTIFIER_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
#: Range types whose fixed events are versions. A GIT range names a commit, not a version.
VERSION_RANGE_TYPES = ("ECOSYSTEM", "SEMVER")
MAXIMUM_PAGES = 5


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
    """GET, or POST when body is bytes, with a 20 second timeout; returns (status, body bytes)."""
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


def validate_request(request) -> tuple:
    """Mirrors contracts/input.schema.json: ecosystem, name and version, and nothing else."""
    if type(request) is not dict:
        raise invalid("the request must be one JSON object")
    if set(request) - {"ecosystem", "name", "version"}:
        raise invalid("the request may hold only the fields ecosystem, name and version")
    for field in ("ecosystem", "name", "version"):
        if field not in request:
            raise invalid(f"the request needs the field {field}")
        if type(request[field]) is not str:
            raise invalid(f"{field} must be a string")
    ecosystem, name, version = request["ecosystem"], request["name"], request["version"]
    if ecosystem not in ECOSYSTEMS:
        raise invalid("ecosystem must be one of: " + ", ".join(ECOSYSTEMS), code="unsupported_ecosystem")
    if len(name) > NAME_LIMIT or re.fullmatch(NAME_PATTERN, name) is None:
        raise invalid(f"name must be a package name of at most {NAME_LIMIT} characters, without spaces")
    if len(version) > VERSION_LIMIT or re.fullmatch(VERSION_PATTERN, version) is None:
        raise invalid(f"version must be one exact version of at most {VERSION_LIMIT} characters, without spaces")
    return ecosystem, name, version


def refuse_constant(name: str):
    raise ValueError(f"{name} is not a JSON number")


def optional_text(mapping: dict, key: str, where: str):
    """The text the source gives, or None when the source leaves it out. Nothing is filled in."""
    value = mapping.get(key)
    if value is None or type(value) is str:
        return value
    raise unexpected(f"{where} {key} is not text")


def objects(value, where: str) -> list:
    """A list of JSON objects; a missing list is empty, anything else is an unexpected shape."""
    if value is None:
        return []
    if type(value) is not list or any(type(item) is not dict for item in value):
        raise unexpected(f"{where} is not a list of objects")
    return value


def parse_page(body: bytes) -> tuple:
    try:
        document = json.loads(body.decode("utf-8"), parse_constant=refuse_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise unexpected("OSV did not answer with JSON") from error
    if type(document) is not dict:
        raise unexpected("the OSV answer is not a JSON object")
    # OSV leaves the vulns list out when no advisory matches.
    vulnerabilities = objects(document.get("vulns"), "vulns")
    token = document.get("next_page_token")
    if token is not None and type(token) is not str:
        raise unexpected("next_page_token is not text")
    return vulnerabilities, token or None


def canonical_name(ecosystem: str, name: str) -> str:
    if ecosystem == "PyPI":
        return re.sub(r"[-_.]+", "-", name).lower()
    if ecosystem == "NuGet":
        return name.lower()
    return name


def same_package(package, ecosystem: str, name: str) -> bool:
    if type(package) is not dict:
        return False
    their_ecosystem, their_name = package.get("ecosystem"), package.get("name")
    if type(their_ecosystem) is not str or type(their_name) is not str:
        return False
    if their_ecosystem != ecosystem and not their_ecosystem.startswith(ecosystem + ":"):
        return False
    return canonical_name(ecosystem, their_name) == canonical_name(ecosystem, name)


def fixed_versions(vulnerability: dict, ecosystem: str, name: str) -> list:
    """Fixed events of ECOSYSTEM and SEMVER ranges for the asked package, in source order, once each."""
    found = []
    for affected in objects(vulnerability.get("affected"), "affected"):
        if not same_package(affected.get("package"), ecosystem, name):
            continue
        for version_range in objects(affected.get("ranges"), "affected ranges"):
            if version_range.get("type") not in VERSION_RANGE_TYPES:
                continue
            for event in objects(version_range.get("events"), "range events"):
                fixed = event.get("fixed")
                if fixed is not None and type(fixed) is not str:
                    raise unexpected("a fixed version is not text")
                if fixed is not None and fixed not in found:
                    found.append(fixed)
    return found


def text_list(vulnerability: dict, key: str):
    value = vulnerability.get(key)
    if value is None:
        return None
    if type(value) is not list or any(type(item) is not str for item in value):
        raise unexpected(f"{key} is not a list of text")
    return list(value)


def severity_entries(vulnerability: dict):
    if vulnerability.get("severity") is None:
        return None
    return [{"type": optional_text(entry, "type", "severity"), "score": optional_text(entry, "score", "severity")}
            for entry in objects(vulnerability["severity"], "severity")]


def advisory(vulnerability: dict, ecosystem: str, name: str) -> dict:
    identifier = vulnerability.get("id")
    if type(identifier) is not str or re.fullmatch(IDENTIFIER_PATTERN, identifier) is None:
        raise unexpected("an advisory has no usable identifier")
    return {
        "id": identifier,
        "aliases": text_list(vulnerability, "aliases"),
        "published": optional_text(vulnerability, "published", "advisory"),
        "modified": optional_text(vulnerability, "modified", "advisory"),
        "severity": severity_entries(vulnerability),
        "fixed_versions": fixed_versions(vulnerability, ecosystem, name),
        "details_address": DETAILS_ADDRESS + identifier,
    }


def run(request, fetch=None, now=None) -> dict:
    """Validates the request, asks OSV (following page tokens) and returns the result record.

    fetch(url, body_or_None, headers) returns (status, body bytes); now() returns the
    current time. Both default to the network and the system clock. A refusal raises
    ToolError; no partial result is ever returned.
    """
    ecosystem, name, version = validate_request(request)
    query = {"package": {"name": name, "ecosystem": ecosystem}, "version": version}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    collected, token = [], None
    for _page in range(MAXIMUM_PAGES):
        body = dict(query, page_token=token) if token else query
        status, answer = read_source(fetch or default_fetch, SOURCE, json.dumps(body).encode("utf-8"), headers)
        if status != 200:
            raise source_failed("source_http_error", f"OSV answered with HTTP status {status}")
        vulnerabilities, token = parse_page(answer)
        collected.extend(vulnerabilities)
        if token is None:
            break
    else:
        raise source_failed("too_many_pages", f"OSV answered with more than {MAXIMUM_PAGES} pages; "
                                              "the tool does not return a partial list")
    moment = observed_at(now)
    try:
        advisories, seen = [], set()
        for vulnerability in collected:
            entry = advisory(vulnerability, ecosystem, name)
            if entry["id"] not in seen:
                seen.add(entry["id"])
                advisories.append(entry)
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise unexpected(f"the OSV answer could not be read ({type(error).__name__})") from error
    return {
        "record_type": RESULT_RECORD,
        "ecosystem": ecosystem,
        "name": name,
        "version": version,
        "count": len(advisories),
        "vulnerabilities": advisories,
        "source": SOURCE,
        "observed_at": moment,
    }


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
