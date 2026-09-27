#!/usr/bin/env python3
"""Look up legal entities in the GLEIF LEI API by identifier or by legal name.

With {"lei": "<LEI>"} the tool first checks the Legal Entity Identifier locally
(20 characters, 18 letters or digits and then 2 digits, ISO 17442 check digits
by mod 97) and only then reads https://api.gleif.org/api/v1/lei-records/<LEI>.
An identifier that fails the check is refused and nothing is sent. With
{"name": "<legal name>", "page_size": n} it reads the lei-records list filtered
by entity.legalName, with n from 1 to 10 (5 when left out). For each record it
returns the registration fields a harness needs and the address of the record
on search.gleif.org. It stores no record: every call reads GLEIF again.

Call it with one JSON object as the only argument, or with "-" to read that
object from standard input. It prints one JSON object and exits 0 on success, 2
on an invalid request and 3 when the source could not be read or answered in an
unexpected shape.

Effects: one HTTPS GET to api.gleif.org. It writes no file.
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

RESULT_RECORD = "knowledge_radar_lookup_legal_entity_result/v1"
ERROR_RECORD = "knowledge_radar_tool_error/v1"
USER_AGENT = "baltor-radar-tool/1.0"
TIMEOUT_SECONDS = 20
MAXIMUM_BYTES = 2 * 1024 * 1024
MAXIMUM_REQUEST_CHARACTERS = 65536
EXIT_INVALID_REQUEST = 2
EXIT_SOURCE_FAILED = 3

API = "https://api.gleif.org/api/v1/lei-records"
RECORD_ADDRESS = "https://search.gleif.org/#/record/"
LEI_PATTERN = r"[A-Z0-9]{18}[0-9]{2}"
NAME_LIMIT = 200
DEFAULT_PAGE_SIZE = 5
MAXIMUM_PAGE_SIZE = 10


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


def lei_check_digits_valid(lei: str) -> bool:
    """ISO 17442 (ISO 7064 MOD 97-10): letters become 10 to 35, and the number mod 97 must be 1."""
    return int("".join(str(int(character, 36)) for character in lei)) % 97 == 1


def validate_request(request) -> dict:
    """Mirrors contracts/input.schema.json, plus the check digits that a schema cannot express."""
    if type(request) is not dict:
        raise invalid("the request must be one JSON object")
    if set(request) - {"lei", "name", "page_size"}:
        raise invalid("the request may hold only the fields lei, name and page_size")
    if ("lei" in request) == ("name" in request):
        raise invalid("give either lei or name, not both and not neither")
    if "lei" in request:
        if "page_size" in request:
            raise invalid("page_size belongs to a name search, not to an LEI lookup")
        lei = request["lei"]
        if type(lei) is not str or re.fullmatch(LEI_PATTERN, lei) is None:
            raise invalid("lei must be 20 characters: 18 capital letters or digits, then 2 digits", code="invalid_lei")
        if not lei_check_digits_valid(lei):
            raise invalid("lei fails the ISO 17442 check digits (mod 97)", code="invalid_lei")
        return {"lei": lei}
    name = request["name"]
    if (type(name) is not str or not 1 <= len(name) <= NAME_LIMIT or not name.strip()
            or any(ord(character) < 32 or ord(character) == 127 for character in name)):
        raise invalid(f"name must be 1 to {NAME_LIMIT} characters of text, not only spaces, without control characters")
    size = request.get("page_size", DEFAULT_PAGE_SIZE)
    if type(size) is float and size.is_integer():
        size = int(size)
    if type(size) is not int or not 1 <= size <= MAXIMUM_PAGE_SIZE:
        raise invalid(f"page_size must be a whole number from 1 to {MAXIMUM_PAGE_SIZE}")
    return {"name": name, "page_size": size}


def refuse_constant(name: str):
    raise ValueError(f"{name} is not a JSON number")


def parse_json(body: bytes):
    try:
        return json.loads(body.decode("utf-8"), parse_constant=refuse_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise unexpected("GLEIF did not answer with JSON") from error


def mapping(parent: dict, key: str) -> dict:
    """A nested object; a missing or null one reads as empty, so its fields stay null."""
    value = parent.get(key)
    if value is None:
        return {}
    if type(value) is not dict:
        raise unexpected(f"{key} is not an object")
    return value


def optional_text(parent: dict, key: str):
    """The text the source gives, or None when the source leaves it out. Nothing is filled in."""
    value = parent.get(key)
    if value is None or type(value) is str:
        return value
    raise unexpected(f"{key} is not text")


def entity_record(item) -> dict:
    if type(item) is not dict:
        raise unexpected("a record is not an object")
    attributes = mapping(item, "attributes")
    lei = attributes.get("lei")
    if type(lei) is not str or re.fullmatch(LEI_PATTERN, lei) is None:
        raise unexpected("a record has no usable LEI")
    entity, registration = mapping(attributes, "entity"), mapping(attributes, "registration")
    return {
        "lei": lei,
        "legal_name": optional_text(mapping(entity, "legalName"), "name"),
        "jurisdiction": optional_text(entity, "jurisdiction"),
        "legal_form_id": optional_text(mapping(entity, "legalForm"), "id"),
        "entity_status": optional_text(entity, "status"),
        "registration_status": optional_text(registration, "status"),
        "initial_registration_date": optional_text(registration, "initialRegistrationDate"),
        "last_update_date": optional_text(registration, "lastUpdateDate"),
        "next_renewal_date": optional_text(registration, "nextRenewalDate"),
        "managing_lou": optional_text(registration, "managingLou"),
        "record_address": RECORD_ADDRESS + lei,
    }


def not_found_answer(body: bytes) -> bool:
    """GLEIF's 404 for an unknown LEI is a JSON:API errors list with the status 404."""
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return False
    errors = document.get("errors") if type(document) is dict else None
    return type(errors) is list and any(type(error) is dict and error.get("status") == "404" for error in errors)


def publish_date(document: dict):
    return optional_text(mapping(mapping(document, "meta"), "goldenCopy"), "publishDate")


def run(request, fetch=None, now=None) -> dict:
    """Validates the request, reads GLEIF once and returns the result record.

    fetch(url, body_or_None, headers) returns (status, body bytes); now() returns the
    current time. Both default to the network and the system clock. A refusal raises
    ToolError; no partial result is ever returned.
    """
    query = validate_request(request)
    if "lei" in query:
        url = f"{API}/{query['lei']}"
    else:
        url = f"{API}?filter[entity.legalName]={urllib.parse.quote(query['name'], safe='')}&page[size]={query['page_size']}"
    status, body = read_source(fetch or default_fetch, url, None, {"Accept": "application/vnd.api+json"})
    moment = observed_at(now)
    records, total, published = [], None, None
    try:
        if "lei" in query and status == 404 and not_found_answer(body):
            pass  # GLEIF holds no record for this LEI: the answer is an empty list, not a failure.
        elif status != 200:
            raise source_failed("source_http_error", f"GLEIF answered with HTTP status {status}")
        else:
            document = parse_json(body)
            if type(document) is not dict:
                raise unexpected("the GLEIF answer is not a JSON object")
            published = publish_date(document)
            data = document.get("data")
            if "lei" in query:
                if type(data) is not dict:
                    raise unexpected("the answer to an LEI lookup holds no single record")
                records = [entity_record(data)]
                if records[0]["lei"] != query["lei"]:
                    raise unexpected("the answer is a record for another LEI")
            else:
                if type(data) is not list:
                    raise unexpected("the answer to a name search holds no list of records")
                records = [entity_record(item) for item in data]
                total = mapping(mapping(document, "meta"), "pagination").get("total")
                if total is not None and (type(total) is not int or total < 0):
                    raise unexpected("the total number of matches is not a whole number")
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise unexpected(f"the GLEIF answer could not be read ({type(error).__name__})") from error
    return {
        "record_type": RESULT_RECORD,
        "query": query,
        "count": len(records),
        "total_matches": total,
        "golden_copy_published_at": published,
        "records": records,
        "source": url,
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
