#!/usr/bin/env python3
"""Read the European Central Bank daily euro reference rates and return rates for a chosen base.

The tool reads https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml,
returns the reference date and the requested rates for the requested base
currency, and computes a rate between two currencies other than the euro
through the euro, with decimal arithmetic, rounded half up to 6 decimal places.
It marks the answer stale when the reference date is more than 4 calendar days
before today (UTC). It stores no rate: every call reads the file again.

Call it with one JSON object, for example {"base": "USD", "symbols": ["EUR", "JPY"]},
as the only argument, or with "-" to read that object from standard input. It
prints one JSON object and exits 0 on success, 2 on an invalid request (also when
the bank did not publish a requested currency) and 3 when the source could not
be read or answered in an unexpected shape.

Effects: one HTTPS GET to www.ecb.europa.eu. It writes no file.
"""
from __future__ import annotations

import http.client
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from xml.etree import ElementTree

RESULT_RECORD = "knowledge_radar_fetch_reference_rates_result/v1"
ERROR_RECORD = "knowledge_radar_tool_error/v1"
USER_AGENT = "baltor-radar-tool/1.0"
TIMEOUT_SECONDS = 20
MAXIMUM_BYTES = 2 * 1024 * 1024
MAXIMUM_REQUEST_CHARACTERS = 65536
EXIT_INVALID_REQUEST = 2
EXIT_SOURCE_FAILED = 3

SOURCE = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ENVELOPE = "{http://www.gesmes.org/xml/2002-08-01}Envelope"
CUBE = "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"
ATTRIBUTION = ("Source: European Central Bank, euro foreign exchange reference rates. The reference rates are "
               "published for information purposes only. Using the rates for transaction purposes is strongly "
               "discouraged.")
CURRENCY_PATTERN = r"[A-Z]{3}"
RATE_PATTERN = r"[0-9]{1,12}(?:\.[0-9]{1,12})?"
DAY_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
MAXIMUM_SYMBOLS = 40
STALE_AFTER_DAYS = 4
SIX_PLACES = Decimal("0.000001")


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


def utc_moment(now) -> datetime:
    moment = (now or system_now)()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def read_source(fetch, url: str, body, headers: dict) -> tuple:
    try:
        answer = fetch(url, body, headers)
    except (OSError, ValueError, http.client.HTTPException) as error:
        raise source_failed("source_unreachable", f"the source could not be read: {str(error)[:200]}") from error
    if (type(answer) is not tuple or len(answer) != 2 or type(answer[0]) is not int
            or type(answer[1]) is not bytes):
        raise source_failed("fetch_contract_invalid", "the fetch function did not return a status and bytes")
    return answer


def currency(value, field: str) -> str:
    if type(value) is not str or re.fullmatch(CURRENCY_PATTERN, value) is None:
        raise invalid(f"{field} must be a three-letter currency code in capital letters, for example USD")
    return value


def validate_request(request) -> tuple:
    """Mirrors contracts/input.schema.json: base, and optionally a list of unique symbols."""
    if type(request) is not dict:
        raise invalid("the request must be one JSON object")
    if set(request) - {"base", "symbols"}:
        raise invalid("the request may hold only the fields base and symbols")
    if "base" not in request:
        raise invalid("the request needs the field base")
    base = currency(request["base"], "base")
    if "symbols" not in request:
        return base, None
    symbols = request["symbols"]
    if type(symbols) is not list or not 1 <= len(symbols) <= MAXIMUM_SYMBOLS:
        raise invalid(f"symbols must be a list of 1 to {MAXIMUM_SYMBOLS} currency codes")
    codes = [currency(symbol, "each symbol") for symbol in symbols]
    if len(set(codes)) != len(codes):
        raise invalid("symbols must not repeat a currency")
    return base, codes


def reference_rates(body: bytes) -> tuple:
    """The reference date and the rates in currency units for one euro, exactly as published."""
    if b"<!DOCTYPE" in body or b"<!ENTITY" in body:
        raise unexpected("the answer declares a document type, which the tool does not read")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        raise unexpected("the answer is not XML") from error
    if root.tag != ENVELOPE:
        raise unexpected("the answer is not the reference rate envelope")
    dated = [cube for cube in root.iter(CUBE) if "time" in cube.attrib]
    if len(dated) != 1:
        raise unexpected("the answer does not hold exactly one day of rates")
    day_text = dated[0].attrib["time"]
    if re.fullmatch(DAY_PATTERN, day_text) is None:
        raise unexpected("the reference date is not written YYYY-MM-DD")
    try:
        reference_date = date.fromisoformat(day_text)
    except ValueError as error:
        raise unexpected("the reference date is not a real day") from error
    rates = {}
    for cube in dated[0]:
        code, rate = cube.attrib.get("currency"), cube.attrib.get("rate")
        if (cube.tag != CUBE or type(code) is not str or re.fullmatch(CURRENCY_PATTERN, code) is None
                or type(rate) is not str or re.fullmatch(RATE_PATTERN, rate) is None
                or code in rates or code == "EUR" or Decimal(rate) <= 0):
            raise unexpected("a rate is not a currency code with a positive decimal rate")
        rates[code] = Decimal(rate)
    if not rates:
        raise unexpected("the answer holds no rates")
    return reference_date, rates


def cross_rate(symbol_per_euro: Decimal, base_per_euro: Decimal) -> float:
    """Units of the symbol for one unit of the base, through the euro, rounded half up to 6 places."""
    with localcontext() as context:
        context.prec = 34
        return float((symbol_per_euro / base_per_euro).quantize(SIX_PLACES, rounding=ROUND_HALF_UP))


def run(request, fetch=None, now=None) -> dict:
    """Validates the request, reads the daily file once and returns the result record.

    fetch(url, body_or_None, headers) returns (status, body bytes); now() returns the
    current time. Both default to the network and the system clock. A refusal raises
    ToolError; no partial result is ever returned.
    """
    base, symbols = validate_request(request)
    status, body = read_source(fetch or default_fetch, SOURCE, None, {"Accept": "application/xml, text/xml"})
    moment = utc_moment(now)
    if status != 200:
        raise source_failed("source_http_error", f"the European Central Bank answered with HTTP status {status}")
    try:
        reference_date, published = reference_rates(body)
    except (KeyError, TypeError, ValueError, AttributeError, InvalidOperation) as error:
        raise unexpected(f"the reference rate file could not be read ({type(error).__name__})") from error
    per_euro = {"EUR": Decimal(1), **published}
    missing = [code for code in [base, *(symbols or [])] if code not in per_euro]
    if missing:
        raise invalid(f"the European Central Bank published no rate for {', '.join(missing)} on {reference_date}",
                      code="currency_not_published")
    wanted = symbols if symbols is not None else [code for code in per_euro if code != base]
    return {
        "record_type": RESULT_RECORD,
        "base": base,
        "reference_date": reference_date.isoformat(),
        "rates": {code: cross_rate(per_euro[code], per_euro[base]) for code in wanted},
        "stale": (moment.date() - reference_date).days > STALE_AFTER_DAYS,
        "attribution": ATTRIBUTION,
        "source": SOURCE,
        "observed_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def refuse_constant(name: str):
    raise ValueError(f"{name} is not a JSON number")


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
