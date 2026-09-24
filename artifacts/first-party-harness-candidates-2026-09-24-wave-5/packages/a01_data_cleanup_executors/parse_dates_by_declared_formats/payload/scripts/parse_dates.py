"""Parse one CSV date column into ISO 8601 dates with declared formats only. Effects: reads_fs (the input CSV under --root); writes_fs only with --output (one new file, never an existing one); no network; no subprocess.

Usage, from the workspace folder (SKILL_DIR is the folder that holds SKILL.md):

    python3 -I -B SKILL_DIR/scripts/parse_dates.py --input data/orders.csv \
        --column order_date --format DD/MM/YYYY --format YYYY-MM-DD \
        [--output data/orders.dates.csv]

Every declared format is tried on every value. A value is parsed only when at
least one format gives a real calendar date and every format that gives one
gives the same date. Standard output is one JSON object.

Exit 0: every non-empty value was parsed.
Exit 1: the report lists held values for a person to review.
Exit 2: the input or the arguments were refused; nothing was written.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import stat
import sys
from pathlib import Path

TOOL = "parse_dates_by_declared_formats"
VERSION = "0.1.1"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_FORMATS = 20
MAX_FORMAT_CHARACTERS = 40
MAX_LISTED = 500
MAX_ROWS_SHOWN = 5
MAX_SHOWN_CHARACTERS = 120
EXIT_DONE, EXIT_REVIEW, EXIT_REFUSED = 0, 1, 2

#: Why one value is held. references/format-tokens.md explains each one.
HOLD_REASONS = ("ambiguous", "invalid_calendar_date", "no_declared_format_matches", "outside_declared_range")
#: Why a whole run is refused. references/format-tokens.md explains each one.
REFUSAL_REASONS = (
    "arguments_invalid", "delimiter_invalid", "root_missing", "path_invalid", "path_outside_root",
    "input_missing", "input_not_a_file", "input_too_large", "input_not_text", "input_not_utf8",
    "csv_malformed", "header_missing", "row_width_differs", "column_missing", "column_repeated",
    "format_invalid", "format_repeated", "too_many_formats", "two_digit_year_base_missing",
    "two_digit_year_base_invalid", "range_invalid", "output_exists", "output_is_input",
    "output_folder_missing", "output_column_exists", "internal_error",
)

TOKEN_ORDER = ("YYYY", "MONTH", "MON", "YY", "MM", "DD", "M", "D")
TOKEN_RULES = {
    "YYYY": ("year", r"(?P<year>[0-9]{4})"),
    "YY": ("year", r"(?P<year_two>[0-9]{2})"),
    "MONTH": ("month", r"(?P<month_name>[A-Za-z]{3,9})"),
    "MON": ("month", r"(?P<month_short>[A-Za-z]{3})"),
    "MM": ("month", r"(?P<month>[0-9]{2})"),
    "M": ("month", r"(?P<month>[0-9]{1,2})"),
    "DD": ("day", r"(?P<day>[0-9]{2})"),
    "D": ("day", r"(?P<day>[0-9]{1,2})"),
}
NUMERIC_TOKENS = frozenset({"YYYY", "YY", "MM", "M", "DD", "D"})
VARIABLE_WIDTH_TOKENS = frozenset({"M", "D"})
MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september",
               "october", "november", "december")
DELIMITERS = {",": ",", "comma": ",", ";": ";", "semicolon": ";", "|": "|", "pipe": "|", "tab": "\t",
              "\\t": "\t", "\t": "\t"}


class Refusal(Exception):
    """The run is refused. Nothing is written."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class Arguments(argparse.ArgumentParser):
    """Report argument errors as one JSON refusal instead of a usage message."""

    def error(self, message: str):  # type: ignore[override]
        raise Refusal("arguments_invalid", message)


class DateFormat:
    """One declared format, compiled into an exact pattern."""

    def __init__(self, text: str) -> None:
        self.text = text
        pieces = split_format(text)
        tokens = [value for kind, value in pieces if kind == "token"]
        if sorted(TOKEN_RULES[value][0] for value in tokens) != ["day", "month", "year"]:
            found = ", ".join(tokens) if tokens else "no tokens"
            raise Refusal("format_invalid", f"format {text!r} reads {found}; it needs exactly one year token "
                                            "(YYYY or YY), one month token (MM, M, MON or MONTH) and one day token "
                                            "(DD or D). Tokens are upper case, and upper-case D, M and YY always "
                                            "start a token, even inside words such as MDT or Day")
        for index, (kind, value) in enumerate(pieces):
            if kind == "token" and value in VARIABLE_WIDTH_TOKENS:
                before = pieces[index - 1] if index > 0 else None
                after = pieces[index + 1] if index + 1 < len(pieces) else None
                if touches_digit(before, at_end=True) or touches_digit(after, at_end=False):
                    raise Refusal("format_invalid", f"format {text!r}: {value} may have one or two digits, so a "
                                                    "separator must stand between it and any other digit")
        self.uses_two_digit_year = any(kind == "token" and value == "YY" for kind, value in pieces)
        self.pattern = re.compile("".join(TOKEN_RULES[value][1] if kind == "token" else re.escape(value)
                                          for kind, value in pieces))

    def read(self, value: str, base: int | None) -> tuple[str, str | None]:
        """Return ("valid", iso), ("invalid", None) or ("no_match", None)."""
        match = self.pattern.fullmatch(value)
        if match is None:
            return "no_match", None
        groups = match.groupdict()
        if groups.get("year") is not None:
            year = int(groups["year"])
        else:
            two = int(groups["year_two"])
            year = base + ((two - base) % 100)
        if groups.get("month") is not None:
            month = int(groups["month"])
        elif groups.get("month_short") is not None:
            short = groups["month_short"].lower()
            names = [number for number, name in enumerate(MONTH_NAMES, start=1) if name[:3] == short]
            if not names:
                return "no_match", None
            month = names[0]
        else:
            name = groups["month_name"].lower()
            if name not in MONTH_NAMES:
                return "no_match", None
            month = MONTH_NAMES.index(name) + 1
        try:
            return "valid", dt.date(year, month, int(groups["day"])).isoformat()
        except ValueError:
            return "invalid", None


def split_format(text: str) -> list[tuple[str, str]]:
    """Split a format into ("token", NAME) and ("literal", TEXT) pieces."""
    if not text or len(text) > MAX_FORMAT_CHARACTERS or any(ord(character) < 32 for character in text):
        raise Refusal("format_invalid", f"a format is 1 to {MAX_FORMAT_CHARACTERS} printable characters")
    if "%" in text:
        raise Refusal("format_invalid", f"format {text!r}: write tokens such as DD/MM/YYYY; % directives are "
                                        "not accepted")
    pieces: list[tuple[str, str]] = []
    literal = ""
    position = 0
    while position < len(text):
        token = next((name for name in TOKEN_ORDER if text.startswith(name, position)), None)
        if token is None:
            literal += text[position]
            position += 1
            continue
        if literal:
            pieces.append(("literal", literal))
            literal = ""
        pieces.append(("token", token))
        position += len(token)
    if literal:
        pieces.append(("literal", literal))
    return pieces


def touches_digit(piece: tuple[str, str] | None, *, at_end: bool) -> bool:
    if piece is None:
        return False
    kind, value = piece
    if kind == "token":
        return value in NUMERIC_TOKENS
    character = value[-1] if at_end else value[0]
    return character.isdigit()


def delimiter_of(value: str) -> str:
    if value not in DELIMITERS:
        raise Refusal("delimiter_invalid", "--delimiter is comma, semicolon, pipe or tab")
    return DELIMITERS[value]


def root_of(value: str) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refusal("root_missing", "--root is not an existing folder") from None
    if not root.is_dir():
        raise Refusal("root_missing", "--root is not an existing folder")
    return root


def confined(root: Path, value: str, label: str) -> tuple[Path, Path]:
    """Return the path as written and its resolved form; refuse any path that leaves the root."""
    if not value or "\x00" in value:
        raise Refusal("path_invalid", f"{label} is empty or holds a NUL character")
    written = Path(value)
    if ".." in written.parts:
        raise Refusal("path_outside_root", f"{label} may not use '..'")
    joined = written if written.is_absolute() else root / written
    try:
        resolved = joined.resolve()
    except (OSError, RuntimeError):
        raise Refusal("path_invalid", f"{label} cannot be resolved") from None
    if resolved != root and not resolved.is_relative_to(root):
        raise Refusal("path_outside_root", f"{label} resolves outside --root, for example through a symbolic link")
    return joined, resolved


def read_input(root: Path, value: str) -> tuple[Path, bytes]:
    _written, resolved = confined(root, value, "--input")
    try:
        info = resolved.stat()
    except OSError:
        raise Refusal("input_missing", "--input does not name an existing file") from None
    if not stat.S_ISREG(info.st_mode):
        raise Refusal("input_not_a_file", "--input is not a regular file")
    if info.st_size > MAX_INPUT_BYTES:
        raise Refusal("input_too_large", f"--input is larger than {MAX_INPUT_BYTES} bytes")
    with open(resolved, "rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise Refusal("input_too_large", f"--input is larger than {MAX_INPUT_BYTES} bytes")
    return resolved, data


def parse_table(data: bytes, delimiter: str) -> tuple[list[str], list[list[str]], str]:
    if b"\x00" in data:
        raise Refusal("input_not_text", "the input holds a NUL byte")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refusal("input_not_utf8", f"the input is not UTF-8 text (byte {error.start})") from None
    first_break = text.find("\n")
    newline = "\r\n" if first_break > 0 and text[first_break - 1] == "\r" else "\n"
    csv.field_size_limit(MAX_INPUT_BYTES)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        rows = list(reader)
    except csv.Error as error:
        raise Refusal("csv_malformed", f"CSV line {reader.line_num}: {error}") from None
    if not rows or not any(cell.strip() for cell in rows[0]):
        raise Refusal("header_missing", "the first row must be a header row")
    header, body = rows[0], rows[1:]
    for number, row in enumerate(body, start=1):
        if not row and len(header) == 1:
            body[number - 1] = [""]  # a blank line in a one-column file is one empty value
        elif not row:
            raise Refusal("row_width_differs", f"data row {number} is a blank line; a file with {len(header)} "
                                               "columns has no blank rows, and a stray line break cannot be told "
                                               "apart from a lost row, so the file is refused")
        elif len(row) != len(header):
            raise Refusal("row_width_differs", f"data row {number} has {len(row)} fields; the header has "
                                               f"{len(header)}")
    return header, body, newline


def column_index(header: list[str], name: str) -> int:
    positions = [index for index, cell in enumerate(header) if cell == name]
    if not positions:
        raise Refusal("column_missing", f"no header cell equals {name!r}; header cells are {header[:50]!r}")
    if len(positions) > 1:
        raise Refusal("column_repeated", f"{len(positions)} header cells equal {name!r}")
    return positions[0]


def prepare_output(root: Path, value: str, input_path: Path) -> Path:
    written, resolved = confined(root, value, "--output")
    if os.path.lexists(written) or os.path.lexists(resolved):
        raise Refusal("output_exists", "--output names an existing path; the copy never replaces a file")
    if resolved == input_path:
        raise Refusal("output_is_input", "--output must differ from --input")
    if not resolved.parent.is_dir():
        raise Refusal("output_folder_missing", "the folder of --output does not exist")
    return resolved


def write_copy(target: Path, header: list[str], rows: list[list[str]], delimiter: str, newline: str) -> dict:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator=newline)
    writer.writerow(header)
    writer.writerows(rows)
    payload = buffer.getvalue().encode("utf-8")
    try:
        stream = open(target, "xb")
    except FileExistsError:
        raise Refusal("output_exists", "--output appeared while the script ran; nothing was replaced") from None
    try:
        with stream:
            stream.write(payload)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def shown(value: str) -> str:
    return value if len(value) <= MAX_SHOWN_CHARACTERS else value[:MAX_SHOWN_CHARACTERS] + "...[cut]"


def iso_date(value: str | None, label: str) -> dt.date | None:
    if value is None:
        return None
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError(value)
        return dt.date.fromisoformat(value)
    except ValueError:
        raise Refusal("range_invalid", f"{label} is a date written YYYY-MM-DD") from None


def judge(value: str, formats: list[DateFormat], base: int | None, earliest: dt.date | None,
          latest: dt.date | None) -> dict:
    """Decide one trimmed, non-empty value."""
    readings: dict[str, str] = {}
    invalid: list[str] = []
    for date_format in formats:
        state, iso = date_format.read(value, base)
        if state == "valid":
            readings[date_format.text] = iso
        elif state == "invalid":
            invalid.append(date_format.text)
    if not readings:
        if invalid:
            return {"status": "held", "reason": "invalid_calendar_date", "formats_matched_invalid": invalid,
                    "readings": readings}
        return {"status": "held", "reason": "no_declared_format_matches", "readings": readings}
    distinct = sorted(set(readings.values()))
    if len(distinct) > 1:
        return {"status": "held", "reason": "ambiguous", "readings": readings}
    iso = distinct[0]
    day = dt.date.fromisoformat(iso)
    if (earliest is not None and day < earliest) or (latest is not None and day > latest):
        return {"status": "held", "reason": "outside_declared_range", "reading": iso, "readings": readings}
    credited = next(date_format.text for date_format in formats if date_format.text in readings)
    return {"status": "parsed", "iso": iso, "format": credited, "readings": readings}


def mixed_conventions(formats: list[DateFormat], seen: dict[str, dict], counts: dict[str, int]) -> list[dict]:
    """Pairs of formats that read some value differently while each also reads values the other cannot."""
    order = [date_format.text for date_format in formats]
    reads = dict.fromkeys(order, 0)
    both: dict[tuple[str, str], int] = {}
    differ: dict[tuple[str, str], int] = {}
    for value, outcome in seen.items():
        readings = outcome["readings"]
        present = [text for text in order if text in readings]
        for text in present:
            reads[text] += counts[value]
        for first_index, first in enumerate(present):
            for second in present[first_index + 1:]:
                both[(first, second)] = both.get((first, second), 0) + counts[value]
                if readings[first] != readings[second]:
                    differ[(first, second)] = differ.get((first, second), 0) + counts[value]
    found = []
    for first, second in sorted(differ, key=lambda pair: (order.index(pair[0]), order.index(pair[1]))):
        only_first = reads[first] - both[(first, second)]
        only_second = reads[second] - both[(first, second)]
        if only_first and only_second:
            found.append({"formats": [first, second], "rows_only_first_reads": only_first,
                          "rows_only_second_reads": only_second, "rows_read_differently": differ[(first, second)]})
    return found


def arguments() -> Arguments:
    parser = Arguments(prog="parse_dates.py", description="Parse one CSV date column with declared formats only.")
    parser.add_argument("--input", required=True, help="CSV file, relative to --root")
    parser.add_argument("--column", required=True, help="exact header name of the date column")
    parser.add_argument("--format", action="append", required=True, dest="formats",
                        help="declared format such as DD/MM/YYYY; repeat in the declared order")
    parser.add_argument("--root", default=".", help="folder that every path must stay inside (default: .)")
    parser.add_argument("--delimiter", default=",", help="comma (default), semicolon, pipe or tab")
    parser.add_argument("--two-digit-year-base", type=int, default=None,
                        help="first year of the 100-year window that YY values fall into, such as 1950")
    parser.add_argument("--earliest", default=None, help="hold parsed dates before this YYYY-MM-DD date")
    parser.add_argument("--latest", default=None, help="hold parsed dates after this YYYY-MM-DD date")
    parser.add_argument("--output", default=None, help="new CSV copy to write, relative to --root")
    parser.add_argument("--output-column", default=None, help="name of the added column (default: COLUMN_iso)")
    return parser


def run(argv: list[str] | None) -> tuple[dict, int]:
    options = arguments().parse_args(argv)
    delimiter = delimiter_of(options.delimiter)
    root = root_of(options.root)
    if len(options.formats) > MAX_FORMATS:
        raise Refusal("too_many_formats", f"declare at most {MAX_FORMATS} formats")
    if len(set(options.formats)) != len(options.formats):
        raise Refusal("format_repeated", "each format is declared once")
    formats = [DateFormat(text) for text in options.formats]
    base = options.two_digit_year_base
    if any(date_format.uses_two_digit_year for date_format in formats):
        if base is None:
            raise Refusal("two_digit_year_base_missing", "a YY format needs --two-digit-year-base, such as 1950")
    if base is not None and not 1000 <= base <= 9900:
        raise Refusal("two_digit_year_base_invalid", "--two-digit-year-base is a year from 1000 to 9900")
    earliest, latest = iso_date(options.earliest, "--earliest"), iso_date(options.latest, "--latest")
    if earliest and latest and earliest > latest:
        raise Refusal("range_invalid", "--earliest is after --latest")
    input_path, data = read_input(root, options.input)
    header, rows, newline = parse_table(data, delimiter)
    index = column_index(header, options.column)
    target = output_column = None
    if options.output is not None:
        output_column = options.output_column or f"{options.column}_iso"
        if output_column in header:
            raise Refusal("output_column_exists", f"the header already has a column named {output_column!r}")
        target = prepare_output(root, options.output, input_path)

    seen: dict[str, dict] = {}
    value_counts: dict[str, int] = {}
    value_rows: dict[str, list[int]] = {}
    converted: list[str] = []
    empty = parsed = held = 0
    parsed_by_format = {date_format.text: 0 for date_format in formats}
    held_by_reason = {reason: 0 for reason in HOLD_REASONS}
    for number, row in enumerate(rows, start=1):
        value = row[index].strip()
        if not value:
            empty += 1
            converted.append("")
            continue
        outcome = seen.get(value)
        if outcome is None:
            outcome = seen[value] = judge(value, formats, base, earliest, latest)
        value_counts[value] = value_counts.get(value, 0) + 1
        if outcome["status"] == "parsed":
            parsed += 1
            parsed_by_format[outcome["format"]] += 1
            converted.append(outcome["iso"])
        else:
            held += 1
            held_by_reason[outcome["reason"]] += 1
            converted.append("")
            shown_rows = value_rows.setdefault(value, [])
            if len(shown_rows) < MAX_ROWS_SHOWN:
                shown_rows.append(number)

    held_values = []
    for value in sorted(value_rows, key=lambda item: (-value_counts[item], item)):
        outcome = seen[value]
        entry = {"value": shown(value), "reason": outcome["reason"], "count": value_counts[value],
                 "first_data_rows": value_rows[value]}
        if outcome["reason"] == "ambiguous":
            entry["readings"] = outcome["readings"]
        elif outcome["reason"] == "invalid_calendar_date":
            entry["formats_matched_invalid"] = outcome["formats_matched_invalid"]
        elif outcome["reason"] == "outside_declared_range":
            entry["reading"] = outcome["reading"]
        held_values.append(entry)

    output = None
    if target is not None:
        copied = [row + [cell] for row, cell in zip(rows, converted)]
        written = write_copy(target, header + [output_column], copied, delimiter, newline)
        output = {"path": options.output, "column": output_column, "data_rows": len(rows), **written}

    document = {
        "tool": TOOL, "version": VERSION, "status": "values_held" if held else "all_parsed",
        "input": {"path": options.input, "sha256": hashlib.sha256(data).hexdigest(), "column": options.column,
                  "delimiter": delimiter},
        "rules": {"formats": [date_format.text for date_format in formats], "two_digit_year_base": base,
                  "earliest": options.earliest, "latest": options.latest},
        "counts": {"data_rows": len(rows), "empty": empty, "parsed": parsed, "held": held},
        "parsed_by_format": parsed_by_format,
        "held_by_reason": held_by_reason,
        "mixed_conventions": mixed_conventions(formats, seen, value_counts),
        "held_values": held_values[:MAX_LISTED],
        "held_values_distinct": len(held_values),
        "held_values_complete": len(held_values) <= MAX_LISTED,
        "output": output,
    }
    return document, EXIT_REVIEW if held else EXIT_DONE


def render(document: dict) -> str:
    """One JSON object: one line per top-level key and one line per listed entry."""
    lines = []
    keys = list(document)
    for position, key in enumerate(keys):
        value, tail = document[key], "," if position + 1 < len(keys) else ""
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            inner = ",\n".join("  " + json.dumps(item, ensure_ascii=False) for item in value)
            lines.append(f" {json.dumps(key)}: [\n{inner}\n ]{tail}")
        else:
            lines.append(f" {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}{tail}")
    return "{\n" + "\n".join(lines) + "\n}\n"


def emit(document: dict) -> None:
    sys.stdout.buffer.write(render(document).encode("utf-8"))
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    try:
        document, code = run(argv)
    except Refusal as refusal:
        document, code = {"tool": TOOL, "version": VERSION, "status": "refused", "reason": refusal.reason,
                          "detail": refusal.detail}, EXIT_REFUSED
    except Exception as error:  # noqa: BLE001 - report instead of a bare traceback
        document, code = {"tool": TOOL, "version": VERSION, "status": "refused", "reason": "internal_error",
                          "detail": f"{type(error).__name__}: {error}"}, EXIT_REFUSED
    emit(document)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
