"""Parse one CSV column of numeric text into exact decimals with the declared marks only. Effects: reads_fs (the input CSV under --root); writes_fs only with --output (one new file, never an existing one); no network; no subprocess.

Usage, from the workspace folder (SKILL_DIR is the folder that holds SKILL.md):

    python3 -I -B SKILL_DIR/scripts/parse_numbers.py --input data/sales.csv --column amount \
        --decimal-mark period --grouping-mark comma --currency USD [--output data/sales.numbers.csv]

A value is read only with the declared decimal mark, grouping mark, currency spellings, percent rule
and sign rules. When the declared marks are the period and comma pair, every value is also read with
the two marks swapped: a value that only the swapped reading accepts is held as `other_convention`.
Once one value of the column is held that way, the column mixes conventions, so every value that the
two readings read differently, such as 2,500, is held as `convention_sensitive` too; without that
evidence, such values are parsed and counted unless --hold-convention-sensitive is given.
Results are exact decimal text such as 1234.50, never binary floating point.

Exit 0: every non-empty value was parsed.
Exit 1: the report lists held values for a person to review.
Exit 2: the input or the arguments were refused; nothing was written.
"""
from __future__ import annotations

import argparse
import csv
import decimal
import hashlib
import io
import json
import os
import stat
import sys
from pathlib import Path

TOOL = "parse_numbers_by_declared_separators"
VERSION = "0.2.0"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_VALUE_CHARACTERS = 60
MAX_DIGITS = 40
MAX_CURRENCIES = 10
MAX_LISTED = 500
MAX_ROWS_SHOWN = 5
MAX_SHOWN_CHARACTERS = 120
EXIT_DONE, EXIT_REVIEW, EXIT_REFUSED = 0, 1, 2

#: Why one value is held. references/marks-and-reasons.md explains each one.
HOLD_REASONS = (
    "no_digits", "undeclared_character", "other_convention", "convention_sensitive", "grouping_mismatch",
    "grouping_after_decimal_mark", "decimal_mark_repeated", "decimal_mark_without_digits", "leading_zero",
    "sign_repeated", "space_after_sign", "parentheses_not_declared", "parentheses_misplaced",
    "currency_repeated", "currency_misplaced", "currency_with_percent", "percent_sign_not_declared",
    "percent_sign_missing", "too_long",
)
#: Why a whole run is refused. references/marks-and-reasons.md explains each one.
REFUSAL_REASONS = (
    "arguments_invalid", "delimiter_invalid", "root_missing", "path_invalid", "path_outside_root",
    "input_missing", "input_not_a_file", "input_too_large", "input_not_text", "input_not_utf8",
    "csv_malformed", "header_missing", "row_width_differs", "column_missing", "column_repeated",
    "marks_conflict", "currency_invalid", "output_exists", "output_is_input", "output_folder_missing",
    "output_column_exists", "internal_error",
)

DIGITS = frozenset("0123456789")
SIGNS = {"+": "+", "-": "-", "\N{MINUS SIGN}": "-"}
DECIMAL_MARKS = {"period": ".", "comma": ","}
GROUPING_MARKS = {"comma": frozenset({","}), "period": frozenset({"."}),
                  "space": frozenset({" ", "\N{NO-BREAK SPACE}", "\N{NARROW NO-BREAK SPACE}"}),
                  "apostrophe": frozenset({"'", "\N{RIGHT SINGLE QUOTATION MARK}"}),
                  "underscore": frozenset({"_"}), "none": frozenset()}
RESERVED_IN_CURRENCY = frozenset("+-()%.,'_ \N{NO-BREAK SPACE}\N{NARROW NO-BREAK SPACE}\N{MINUS SIGN}"
                                 "\N{RIGHT SINGLE QUOTATION MARK}") | DIGITS
DELIMITERS = {",": ",", "comma": ",", ";": ";", "semicolon": ";", "|": "|", "pipe": "|", "tab": "\t",
              "\\t": "\t", "\t": "\t"}
EXACT = decimal.Context(prec=MAX_DIGITS + 10)


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


class Marks:
    """One reading convention: a decimal mark, grouping characters and a grouping style."""

    def __init__(self, decimal_mark: str, grouping: frozenset, style: str, allow_leading_zeros: bool) -> None:
        self.decimal_mark = decimal_mark
        self.grouping = grouping
        self.style = style
        self.allow_leading_zeros = allow_leading_zeros

    def read(self, text: str) -> tuple[decimal.Decimal | None, str, list[str]]:
        """Return (value, "", []) or (None, reason, offending characters)."""
        allowed = DIGITS | self.grouping | {self.decimal_mark}
        strangers = sorted({character for character in text if character not in allowed})
        if strangers:
            return None, "undeclared_character", strangers
        if text.count(self.decimal_mark) > 1:
            return None, "decimal_mark_repeated", []
        whole, mark, fraction = text.partition(self.decimal_mark)
        if mark and not fraction:
            return None, "decimal_mark_without_digits", []
        if any(character in self.grouping for character in fraction):
            return None, "grouping_after_decimal_mark", []
        groups = [whole]
        for character in self.grouping:
            groups = [piece for group in groups for piece in group.split(character)]
        if len(groups) > 1 and not self.groups_fit(groups):
            return None, "grouping_mismatch", []
        digits = "".join(groups)
        if not digits and not fraction:
            return None, "no_digits", []
        if len(digits) > 1 and digits[0] == "0" and not self.allow_leading_zeros:
            return None, "leading_zero", []
        return decimal.Decimal((digits or "0") + ("." + fraction if fraction else "")), "", []

    def groups_fit(self, groups: list[str]) -> bool:
        if any(not group for group in groups):
            return False
        if self.style == "indian":
            return 1 <= len(groups[0]) <= 2 and all(len(group) == 2 for group in groups[1:-1]) \
                and len(groups[-1]) == 3
        return 1 <= len(groups[0]) <= 3 and all(len(group) == 3 for group in groups[1:])


class Rules:
    """Everything the task declared about one column."""

    def __init__(self, options: argparse.Namespace) -> None:
        self.decimal_mark = DECIMAL_MARKS[options.decimal_mark]
        grouping = GROUPING_MARKS[options.grouping_mark]
        if self.decimal_mark in grouping:
            raise Refusal("marks_conflict", "--decimal-mark and --grouping-mark must differ")
        self.declared = Marks(self.decimal_mark, grouping, options.group_style, options.allow_leading_zeros)
        pair = {options.decimal_mark, options.grouping_mark}
        self.swapped = None
        if pair == {"period", "comma"}:
            other = "." if self.decimal_mark == "," else ","
            self.swapped = Marks(other, frozenset({self.decimal_mark}), options.group_style,
                                 options.allow_leading_zeros)
        spellings = options.currency or []
        if len(spellings) > MAX_CURRENCIES or len({item.casefold() for item in spellings}) != len(spellings):
            raise Refusal("currency_invalid", f"declare at most {MAX_CURRENCIES} distinct currency spellings")
        for spelling in spellings:
            if not 1 <= len(spelling) <= 8 or any(character in RESERVED_IN_CURRENCY or character.isspace()
                                                  or ord(character) < 32 for character in spelling):
                raise Refusal("currency_invalid", f"currency spelling {spelling!r} must be 1 to 8 characters "
                                                  "without digits, spaces, signs, marks or percent signs")
        self.currencies = sorted(spellings, key=len, reverse=True)
        self.percent = options.percent_sign
        self.parentheses = options.negative_parentheses
        self.hold_sensitive = options.hold_convention_sensitive

    def prefix(self, text: str) -> tuple[str | None, str]:
        for spelling in self.currencies:
            if text[:len(spelling)].casefold() == spelling.casefold():
                return text[:len(spelling)], text[len(spelling):].lstrip()
        return None, text

    def suffix(self, text: str) -> tuple[str | None, str]:
        for spelling in self.currencies:
            if len(text) > len(spelling) and text[-len(spelling):].casefold() == spelling.casefold():
                return text[-len(spelling):], text[:-len(spelling)].rstrip()
        return None, text

    def mentions_currency(self, text: str) -> bool:
        """True when a declared currency spelling stands somewhere the rules do not read it."""
        folded = text.casefold()
        return any(spelling.casefold() in folded for spelling in self.currencies)


def held(reason: str, **details) -> dict:
    return {"status": "held", "reason": reason, **details}


def judge(value: str, rules: Rules) -> dict:
    """Decide one trimmed, non-empty value.

    A parsed value that the swapped marks read differently carries "sensitive" and its other reading;
    run() decides whether the column's evidence holds it.
    """
    if len(value) > MAX_VALUE_CHARACTERS:
        return held("too_long")
    text, negative, signs, spaced = value, False, 0, False
    if "(" in text or ")" in text:
        if not rules.parentheses:
            return held("parentheses_not_declared")
        if not (text.startswith("(") and text.endswith(")")) or text.count("(") != 1 or text.count(")") != 1:
            return held("parentheses_misplaced")
        text, negative = text[1:-1].strip(), True
        signs += 1
    suffix, text = rules.suffix(text)
    percent = text.endswith("%")
    if percent:
        text = text[:-1].rstrip()
    if text[:1] in SIGNS:
        negative, signs, text = negative or SIGNS[text[0]] == "-", signs + 1, text[1:]
        spaced = spaced or text[:1].isspace()
    prefix, text = rules.prefix(text)
    if prefix is not None and text[:1] in SIGNS:
        negative, signs, text = negative or SIGNS[text[0]] == "-", signs + 1, text[1:]
        spaced = spaced or text[:1].isspace()
    if signs > 1:
        return held("sign_repeated")
    if spaced:
        return held("space_after_sign")
    if prefix is not None and suffix is not None:
        return held("currency_repeated")
    if percent and (prefix or suffix):
        return held("currency_with_percent")
    if percent and rules.percent == "hold":
        return held("percent_sign_not_declared")
    if not percent and rules.percent == "divide":
        return held("percent_sign_missing")
    if not any(character in DIGITS for character in text):
        return held("no_digits")
    if sum(character in DIGITS for character in text) > MAX_DIGITS:
        return held("too_long")
    number, reason, strangers = rules.declared.read(text)
    other = rules.swapped.read(text)[0] if rules.swapped is not None else None
    if number is None:
        if other is not None:
            return held("other_convention", other_reading=canonical(other, negative, percent, rules))
        if reason == "undeclared_character" and rules.mentions_currency(text):
            return held("currency_misplaced")
        return held(reason, **({"characters": strangers} if strangers else {}))
    outcome = {"status": "parsed", "number": canonical(number, negative, percent, rules), "sensitive": False,
               "currency": prefix or suffix, "percent": percent, "parentheses": value.startswith("(")}
    if other is not None and other != number:
        outcome.update(sensitive=True, other_reading=canonical(other, negative, percent, rules))
    return outcome


def hold_convention_sensitive(outcomes: dict[str, dict], by_flag: bool) -> bool:
    """Hold every sensitive parsed value when the flag asks for it or the column mixes conventions.

    Returns True when at least one value of the column is held as other_convention.
    """
    mixes = any(outcome["status"] == "held" and outcome["reason"] == "other_convention"
                for outcome in outcomes.values())
    if by_flag or mixes:
        for value, outcome in outcomes.items():
            if outcome["status"] == "parsed" and outcome["sensitive"]:
                outcomes[value] = held("convention_sensitive", declared_reading=outcome["number"],
                                       other_reading=outcome["other_reading"])
    return mixes


def canonical(number: decimal.Decimal, negative: bool, percent: bool, rules: Rules) -> str:
    if percent and rules.percent == "divide":
        number = number.scaleb(-2, EXACT)
    if negative:
        number = number.copy_negate()
    if number == 0:
        number = number.copy_abs()
    return format(number, "f")


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


def arguments() -> Arguments:
    parser = Arguments(prog="parse_numbers.py", description="Parse numeric text with declared marks only.")
    parser.add_argument("--input", required=True, help="CSV file, relative to --root")
    parser.add_argument("--column", required=True, help="exact header name of the numeric column")
    parser.add_argument("--decimal-mark", required=True, choices=sorted(DECIMAL_MARKS))
    parser.add_argument("--grouping-mark", required=True, choices=sorted(GROUPING_MARKS),
                        help="space also accepts the no-break spaces; apostrophe also accepts the typographic one")
    parser.add_argument("--group-style", default="thousands", choices=("thousands", "indian"),
                        help="thousands: 1,234,567 (default); indian: 12,34,567")
    parser.add_argument("--currency", action="append", default=None,
                        help="one spelling of the column's one currency, such as USD or $; repeat for more spellings")
    parser.add_argument("--percent-sign", default="hold", choices=("hold", "strip", "divide"),
                        help="hold (default): hold values with %%; strip: 12.5%% gives 12.5; divide: 12.5%% gives "
                             "0.125 and values without %% are held")
    parser.add_argument("--negative-parentheses", action="store_true", help="read (12.50) as -12.50")
    parser.add_argument("--allow-leading-zeros", action="store_true", help="read 007 as 7 instead of holding it")
    parser.add_argument("--hold-convention-sensitive", action="store_true",
                        help="hold values that the swapped period and comma marks read differently even when no "
                             "value of the column is written the other way")
    parser.add_argument("--root", default=".", help="folder that every path must stay inside (default: .)")
    parser.add_argument("--delimiter", default=",", help="comma (default), semicolon, pipe or tab")
    parser.add_argument("--output", default=None, help="new CSV copy to write, relative to --root")
    parser.add_argument("--output-column", default=None, help="name of the added column (default: COLUMN_number)")
    return parser


def run(argv: list[str] | None) -> tuple[dict, int]:
    options = arguments().parse_args(argv)
    delimiter = delimiter_of(options.delimiter)
    rules = Rules(options)
    root = root_of(options.root)
    input_path, data = read_input(root, options.input)
    header, rows, newline = parse_table(data, delimiter)
    index = column_index(header, options.column)
    target = output_column = None
    if options.output is not None:
        output_column = options.output_column or f"{options.column}_number"
        if output_column in header:
            raise Refusal("output_column_exists", f"the header already has a column named {output_column!r}")
        target = prepare_output(root, options.output, input_path)

    values = [row[index].strip() for row in rows]
    seen: dict[str, dict] = {}
    for value in values:
        if value and value not in seen:
            seen[value] = judge(value, rules)
    mixes = hold_convention_sensitive(seen, rules.hold_sensitive)

    value_counts: dict[str, int] = {}
    value_rows: dict[str, list[int]] = {}
    converted: list[str] = []
    empty = parsed = held_count = sensitive = percent_values = parentheses_values = 0
    held_by_reason = {reason: 0 for reason in HOLD_REASONS}
    currencies: dict[str, int] = {}
    for number, value in enumerate(values, start=1):
        if not value:
            empty += 1
            converted.append("")
            continue
        outcome = seen[value]
        value_counts[value] = value_counts.get(value, 0) + 1
        if outcome["status"] == "parsed":
            parsed += 1
            sensitive += outcome["sensitive"]
            percent_values += outcome["percent"]
            parentheses_values += outcome["parentheses"]
            if outcome["currency"]:
                currencies[outcome["currency"]] = currencies.get(outcome["currency"], 0) + 1
            converted.append(outcome["number"])
        else:
            held_count += 1
            held_by_reason[outcome["reason"]] += 1
            converted.append("")
            shown_rows = value_rows.setdefault(value, [])
            if len(shown_rows) < MAX_ROWS_SHOWN:
                shown_rows.append(number)

    held_values = []
    for value in sorted(value_rows, key=lambda item: (-value_counts[item], item)):
        details = {key: item for key, item in seen[value].items() if key not in ("status", "reason")}
        held_values.append({"value": shown(value), "reason": seen[value]["reason"], "count": value_counts[value],
                            "first_data_rows": value_rows[value], **details})

    output = None
    if target is not None:
        copied = [row + [cell] for row, cell in zip(rows, converted)]
        written = write_copy(target, header + [output_column], copied, delimiter, newline)
        output = {"path": options.output, "column": output_column, "data_rows": len(rows), **written}

    document = {
        "tool": TOOL, "version": VERSION, "status": "values_held" if held_count else "all_parsed",
        "input": {"path": options.input, "sha256": hashlib.sha256(data).hexdigest(), "column": options.column,
                  "delimiter": delimiter},
        "rules": {"decimal_mark": options.decimal_mark, "grouping_mark": options.grouping_mark,
                  "group_style": options.group_style, "currency": options.currency or [],
                  "percent_sign": options.percent_sign, "negative_parentheses": options.negative_parentheses,
                  "allow_leading_zeros": options.allow_leading_zeros,
                  "hold_convention_sensitive": options.hold_convention_sensitive,
                  "swapped_marks_checked": rules.swapped is not None},
        "counts": {"data_rows": len(rows), "empty": empty, "parsed": parsed, "held": held_count},
        "held_by_reason": held_by_reason,
        "column_mixes_conventions": mixes,
        "convention_sensitive_parsed": sensitive,
        "currency_seen": currencies,
        "percent_values_parsed": percent_values,
        "parentheses_values_parsed": parentheses_values,
        "held_values": held_values[:MAX_LISTED],
        "held_values_distinct": len(held_values),
        "held_values_complete": len(held_values) <= MAX_LISTED,
        "output": output,
    }
    return document, EXIT_REVIEW if held_count else EXIT_DONE


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
