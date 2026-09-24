"""Flag numeric CSV values beyond a declared multiple of the median absolute deviation, per column or per group. Effects: reads_fs (the input CSV under --root); writes_fs only with --output (one new file, never an existing one); no network; no subprocess.

Usage, from the workspace folder (SKILL_DIR is the folder that holds SKILL.md):

    python3 -I -B SKILL_DIR/scripts/flag_outliers.py --input data/orders.csv --column amount \
        --multiple 5 [--group-by region] [--output data/orders.flagged.csv]

For each column and group, the median and the median absolute deviation (MAD, the median of the
distances from the median) are computed with exact decimals. A value is flagged when its distance
from the median is larger than the declared multiple times the MAD. No row is deleted and no value
is changed; the optional copy only adds one flag column per checked column. A group with fewer
values than --min-group-size, or with a MAD of zero, is reported as not evaluated instead of flagged.
Group labels are compared with their outer spaces trimmed, so "B" and "B " form one group; letter case
and every other character still count.

Exit 0: nothing flagged and nothing left for review.
Exit 1: the report lists flagged values, groups not evaluated or values that are not plain numbers.
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
import re
import stat
import sys
from pathlib import Path

TOOL = "flag_outliers_by_median_deviation"
VERSION = "0.2.0"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_COLUMNS = 20
MAX_GROUP_COLUMNS = 3
MAX_DIGITS = 40
MAX_FLAGGED_LISTED = 1000
MAX_LISTED = 200
MAX_ROWS_SHOWN = 5
MAX_SHOWN_CHARACTERS = 120
EXIT_DONE, EXIT_REVIEW, EXIT_REFUSED = 0, 1, 2
WIDE = decimal.Context(prec=120)
PLAIN_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)")

#: Why a group is reported instead of checked. references/method-and-fields.md explains each one.
GROUP_REASONS = ("too_few_values", "mad_is_zero")
#: Why a whole run is refused. references/method-and-fields.md explains each one.
REFUSAL_REASONS = (
    "arguments_invalid", "delimiter_invalid", "root_missing", "path_invalid", "path_outside_root",
    "input_missing", "input_not_a_file", "input_too_large", "input_not_text", "input_not_utf8",
    "csv_malformed", "header_missing", "row_width_differs", "column_missing", "column_repeated",
    "multiple_invalid", "min_group_size_invalid", "group_by_invalid", "output_exists", "output_is_input",
    "output_folder_missing", "output_column_exists", "internal_error",
)
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


def plain_number(text: str) -> decimal.Decimal | None:
    """Read a plain decimal such as -12.5; anything else is not a plain number."""
    if not PLAIN_NUMBER.fullmatch(text) or sum(character.isdigit() for character in text) > MAX_DIGITS:
        return None
    return decimal.Decimal(text)


def median(values: list[decimal.Decimal]) -> decimal.Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return WIDE.divide(WIDE.add(ordered[middle - 1], ordered[middle]), 2)


def text_of(value: decimal.Decimal) -> str:
    value = WIDE.plus(value)
    return format(value.copy_abs() if value == 0 else value, "f")


def ratio_text(value: decimal.Decimal) -> str:
    try:
        return text_of(value.quantize(decimal.Decimal("0.0001"), context=WIDE))
    except decimal.InvalidOperation:
        return format(value, ".6E")


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


def multiple_of(text: str) -> decimal.Decimal:
    value = plain_number(text.strip())
    if value is None or not 0 < value <= 1000 or len(value.as_tuple().digits) > 12:
        raise Refusal("multiple_invalid", "--multiple is a plain number above 0 and at most 1000, such as 5")
    return value


def arguments() -> Arguments:
    parser = Arguments(prog="flag_outliers.py", description="Flag values far from the median, measured in MADs.")
    parser.add_argument("--input", required=True, help="CSV file, relative to --root")
    parser.add_argument("--column", action="append", required=True, dest="columns",
                        help="exact header name of one numeric column; repeat for more columns")
    parser.add_argument("--multiple", required=True,
                        help="declared multiple of the MAD beyond which a value is flagged, such as 5")
    parser.add_argument("--group-by", action="append", default=[], dest="groups",
                        help="column whose values form separate groups; repeat for a combined group key")
    parser.add_argument("--min-group-size", type=int, default=5,
                        help="groups with fewer plain numbers are reported, not checked (default 5, at least 3)")
    parser.add_argument("--root", default=".", help="folder that every path must stay inside (default: .)")
    parser.add_argument("--delimiter", default=",", help="comma (default), semicolon, pipe or tab")
    parser.add_argument("--output", default=None, help="new CSV copy with one added flag column per checked column")
    return parser


def run(argv: list[str] | None) -> tuple[dict, int]:
    options = arguments().parse_args(argv)
    delimiter = delimiter_of(options.delimiter)
    multiple = multiple_of(options.multiple)
    if not 3 <= options.min_group_size <= 1_000_000:
        raise Refusal("min_group_size_invalid", "--min-group-size is a whole number from 3 to 1000000")
    if len(options.columns) > MAX_COLUMNS or len(set(options.columns)) != len(options.columns):
        raise Refusal("arguments_invalid", f"name 1 to {MAX_COLUMNS} distinct columns")
    if len(options.groups) > MAX_GROUP_COLUMNS or len(set(options.groups)) != len(options.groups) \
            or set(options.groups) & set(options.columns):
        raise Refusal("group_by_invalid", f"--group-by names at most {MAX_GROUP_COLUMNS} distinct columns that "
                                          "are not also checked with --column")
    root = root_of(options.root)
    input_path, data = read_input(root, options.input)
    header, rows, newline = parse_table(data, delimiter)
    checked = [column_index(header, name) for name in options.columns]
    grouping = [column_index(header, name) for name in options.groups]
    target = None
    added = [f"{header[position]}_outlier" for position in checked]
    if options.output is not None:
        clash = sorted(set(added) & set(header))
        if clash:
            raise Refusal("output_column_exists", f"the header already has the columns {clash!r}")
        target = prepare_output(root, options.output, input_path)

    flags = [["not_evaluated"] * len(checked) for _ in rows]
    labels_trimmed = sum(any(row[index] != row[index].strip() for index in grouping) for row in rows)
    summaries, flagged, skipped_groups, statistics, strangers = [], [], [], [], {}
    for slot, position in enumerate(checked):
        column = header[position]
        groups: dict[tuple, list[tuple[decimal.Decimal, int, str]]] = {}
        empty = not_numeric = 0
        for number, row in enumerate(rows, start=1):
            raw = row[position].strip()
            if not raw:
                empty += 1
                continue
            value = plain_number(raw)
            if value is None:
                not_numeric += 1
                entry = strangers.setdefault((slot, raw), {"count": 0, "first_data_rows": []})
                entry["count"] += 1
                if len(entry["first_data_rows"]) < MAX_ROWS_SHOWN:
                    entry["first_data_rows"].append(number)
                continue
            key = tuple(row[index].strip() for index in grouping)
            groups.setdefault(key, []).append((value, number, raw))
        high = low = evaluated = 0
        for key in sorted(groups):
            members = groups[key]
            label = dict(zip(options.groups, key)) if grouping else None
            if len(members) < options.min_group_size:
                skipped_groups.append({"column": column, "group": label, "values": len(members),
                                       "reason": "too_few_values"})
                continue
            center = median([value for value, _number, _raw in members])
            spread = median([WIDE.abs(WIDE.subtract(value, center)) for value, _number, _raw in members])
            if spread == 0:
                differing = sum(value != center for value, _number, _raw in members)
                skipped_groups.append({"column": column, "group": label, "values": len(members),
                                       "reason": "mad_is_zero", "median": text_of(center),
                                       "values_differing_from_median": differing})
                continue
            evaluated += 1
            limit = WIDE.multiply(multiple, spread)
            group_flags = 0
            for value, number, raw in members:
                distance = WIDE.abs(WIDE.subtract(value, center))
                if distance > limit:
                    direction = "high" if value > center else "low"
                    high, low = high + (direction == "high"), low + (direction == "low")
                    group_flags += 1
                    flags[number - 1][slot] = direction
                    flagged.append({"column": column, "group": label, "data_row": number, "value": shown(raw),
                                    "median": text_of(center), "mad": text_of(spread),
                                    "deviation_in_mads": WIDE.divide(distance, spread), "direction": direction})
                else:
                    flags[number - 1][slot] = "within"
            statistics.append({"column": column, "group": label, "values": len(members), "median": text_of(center),
                               "mad": text_of(spread), "flagged": group_flags})
        summaries.append({"column": column, "numeric": sum(len(members) for members in groups.values()),
                          "empty": empty, "not_numeric": not_numeric, "groups": len(groups),
                          "groups_evaluated": evaluated, "groups_not_evaluated": len(groups) - evaluated,
                          "flagged": high + low, "flagged_high": high, "flagged_low": low})

    order = {name: index for index, name in enumerate(options.columns)}
    flagged.sort(key=lambda item: (order[item["column"]], -item["deviation_in_mads"], item["data_row"]))
    for item in flagged:
        item["deviation_in_mads"] = ratio_text(item["deviation_in_mads"])
    unreadable = [{"column": header[checked[slot]], "value": shown(raw), "count": entry["count"],
                   "first_data_rows": entry["first_data_rows"]}
                  for (slot, raw), entry in sorted(strangers.items(), key=lambda item: (-item[1]["count"], item[0]))]
    review = bool(flagged or skipped_groups or unreadable)

    output = None
    if target is not None:
        copied = [row + cells for row, cells in zip(rows, flags)]
        output = {"path": options.output, "columns_added": added, "data_rows": len(rows),
                  **write_copy(target, header + added, copied, delimiter, newline)}

    document = {
        "tool": TOOL, "version": VERSION, "status": "review_listed" if review else "nothing_flagged",
        "input": {"path": options.input, "sha256": hashlib.sha256(data).hexdigest(), "delimiter": delimiter,
                  "data_rows": len(rows)},
        "rules": {"columns": options.columns, "group_by": options.groups, "multiple": text_of(multiple),
                  "min_group_size": options.min_group_size},
        "columns": summaries,
        "group_labels_trimmed": labels_trimmed,
        "flagged": flagged[:MAX_FLAGGED_LISTED],
        "flagged_total": len(flagged),
        "flagged_complete": len(flagged) <= MAX_FLAGGED_LISTED,
        "groups_not_evaluated": skipped_groups[:MAX_LISTED],
        "groups_not_evaluated_total": len(skipped_groups),
        "groups_not_evaluated_complete": len(skipped_groups) <= MAX_LISTED,
        "group_statistics": statistics[:MAX_LISTED],
        "group_statistics_complete": len(statistics) <= MAX_LISTED,
        "not_numeric_values": unreadable[:MAX_LISTED],
        "not_numeric_values_distinct": len(unreadable),
        "not_numeric_values_complete": len(unreadable) <= MAX_LISTED,
        "output": output,
    }
    return document, EXIT_REVIEW if review else EXIT_DONE


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
