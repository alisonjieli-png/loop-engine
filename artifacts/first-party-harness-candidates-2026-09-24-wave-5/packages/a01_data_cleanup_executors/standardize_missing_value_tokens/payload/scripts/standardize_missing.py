"""Turn declared missing-value tokens into empty cells in declared CSV columns only. Effects: reads_fs (the input CSV under --root); writes_fs only with --output (one new file, never an existing one); no network; no subprocess.

Usage, from the workspace folder (SKILL_DIR is the folder that holds SKILL.md):

    python3 -I -B SKILL_DIR/scripts/standardize_missing.py --input data/survey.csv \
        --column age --column income --token n/a --token null --token=- [--output data/survey.blanked.csv]

A cell is blanked only when, with its outer spaces trimmed, it equals a declared token (in any
case only with --ignore-case). Zero, false and every other value stay as written. A token that
looks like a real value, such as 0, -999 or false, is refused unless --allow-value-token names it
too. Cells that resemble a missing marker but were not declared are listed, never changed.

Exit 0: done, and nothing needs review.
Exit 1: done, and the report lists look-alike cells or cells of only spaces for review.
Exit 2: the input or the arguments were refused; nothing was written.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import stat
import sys
from pathlib import Path

TOOL = "standardize_missing_value_tokens"
VERSION = "0.1.1"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_TOKENS = 50
MAX_TOKEN_CHARACTERS = 64
MAX_LISTED = 200
MAX_ROWS_SHOWN = 5
MAX_SHOWN_CHARACTERS = 120
EXIT_DONE, EXIT_REVIEW, EXIT_REFUSED = 0, 1, 2

#: Why a whole run is refused. references/tokens-and-counts.md explains each one.
REFUSAL_REASONS = (
    "arguments_invalid", "delimiter_invalid", "root_missing", "path_invalid", "path_outside_root",
    "input_missing", "input_not_a_file", "input_too_large", "input_not_text", "input_not_utf8",
    "csv_malformed", "header_missing", "row_width_differs", "column_missing", "column_repeated",
    "columns_not_declared", "token_invalid", "token_repeated", "token_looks_like_a_value",
    "allow_value_token_not_declared", "output_exists", "output_is_input", "output_folder_missing",
    "internal_error",
)
#: Spellings that often mean "no value". They are only reported, never changed, unless declared.
LOOKALIKES = frozenset({
    "n/a", "na", "n.a.", "n.a", "null", "nil", "none", "nan", "-", "--", "---", ".", "?", "??", "missing",
    "unknown", "not known", "not available", "not applicable", "no data", "#n/a", "#null!", "(blank)", "blank",
    "empty", "undefined", "tbd",
})
BOOLEAN_WORDS = frozenset({"true", "false", "yes", "no", "y", "n", "t", "f", "on", "off"})
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


def looks_like_a_value(token: str) -> bool:
    """A token with a digit, or a true or false word, could be real data."""
    return any(character.isdigit() for character in token) or token.casefold() in BOOLEAN_WORDS


class Tokens:
    """The declared tokens and how cells are compared with them."""

    def __init__(self, declared: list[str], allowed: list[str], ignore_case: bool) -> None:
        if not declared or len(declared) > MAX_TOKENS:
            raise Refusal("token_invalid", f"declare 1 to {MAX_TOKENS} tokens with --token")
        self.ignore_case = ignore_case
        self.spelling: dict[str, str] = {}
        for raw in declared:
            token = raw.strip()
            if not token or len(token) > MAX_TOKEN_CHARACTERS or any(ord(character) < 32 for character in token):
                raise Refusal("token_invalid", f"token {raw!r} is empty after trimming, too long or holds a "
                                               "control character; use --blank-whitespace-cells for cells of "
                                               "only spaces")
            key = self.key(token)
            if key in self.spelling:
                raise Refusal("token_repeated", f"token {raw!r} repeats {self.spelling[key]!r}")
            self.spelling[key] = token
        allowed_tokens = {item.strip() for item in allowed}
        for item in sorted(allowed_tokens):
            if self.key(item) not in self.spelling:
                raise Refusal("allow_value_token_not_declared", f"--allow-value-token {item!r} is not also given "
                                                                "with --token")
        allowed_keys = {self.key(item) for item in allowed_tokens}
        for token in self.spelling.values():
            if looks_like_a_value(token) and self.key(token) not in allowed_keys:
                raise Refusal("token_looks_like_a_value", f"token {token!r} could be a real value; pass it again "
                                                          "with --allow-value-token only if the task names it as a "
                                                          "missing marker")
        self.allowed = sorted(allowed_tokens)
        self.folded = {token.casefold() for token in self.spelling.values()}

    def key(self, text: str) -> str:
        return text.casefold() if self.ignore_case else text

    def match(self, stripped: str) -> str | None:
        return self.spelling.get(self.key(stripped))

    def resembles(self, stripped: str) -> bool:
        folded = stripped.casefold()
        return folded in LOOKALIKES or folded in self.folded


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
    parser = Arguments(prog="standardize_missing.py",
                       description="Blank declared missing-value tokens in declared columns only.")
    parser.add_argument("--input", required=True, help="CSV file, relative to --root")
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--column", action="append", default=None, dest="columns",
                       help="exact header name of one column to clean; repeat for more columns")
    which.add_argument("--all-columns", action="store_true", help="clean every column")
    parser.add_argument("--token", action="append", default=None, dest="tokens",
                        help="one declared missing-value token such as n/a; write --token=- for a lone dash")
    parser.add_argument("--ignore-case", action="store_true", help="match tokens in any letter case")
    parser.add_argument("--blank-whitespace-cells", action="store_true",
                        help="also blank cells that hold only spaces or tabs")
    parser.add_argument("--allow-value-token", action="append", default=[], dest="allowed",
                        help="confirm a declared token that looks like a real value, such as -999")
    parser.add_argument("--root", default=".", help="folder that every path must stay inside (default: .)")
    parser.add_argument("--delimiter", default=",", help="comma (default), semicolon, pipe or tab")
    parser.add_argument("--output", default=None, help="new CSV copy to write, relative to --root")
    return parser


def run(argv: list[str] | None) -> tuple[dict, int]:
    options = arguments().parse_args(argv)
    delimiter = delimiter_of(options.delimiter)
    if not options.columns and not options.all_columns:
        raise Refusal("columns_not_declared", "name each column with --column, or pass --all-columns")
    if options.columns and len(set(options.columns)) != len(options.columns):
        raise Refusal("arguments_invalid", "each --column is named once")
    tokens = Tokens(options.tokens or [], options.allowed, options.ignore_case)
    root = root_of(options.root)
    input_path, data = read_input(root, options.input)
    header, rows, newline = parse_table(data, delimiter)
    if options.all_columns:
        positions = list(range(len(header)))
    else:
        positions = [column_index(header, name) for name in options.columns]
    target = prepare_output(root, options.output, input_path) if options.output is not None else None

    stats = []
    for position in positions:
        stats.append({"column": header[position], "position": position + 1, "cells": 0, "blanked": 0,
                      "blanked_by_token": {token: 0 for token in tokens.spelling.values()},
                      "whitespace_blanked": 0, "whitespace_kept": 0, "already_empty": 0, "kept": 0})
    lookalikes: dict[tuple[int, str], dict] = {}
    for number, row in enumerate(rows, start=1):
        for slot, position in enumerate(positions):
            cell, record = row[position], stats[slot]
            record["cells"] += 1
            stripped = cell.strip()
            if not stripped:
                if not cell:
                    record["already_empty"] += 1
                elif options.blank_whitespace_cells:
                    record["whitespace_blanked"] += 1
                    row[position] = ""
                else:
                    record["whitespace_kept"] += 1
                continue
            token = tokens.match(stripped)
            if token is not None:
                record["blanked"] += 1
                record["blanked_by_token"][token] += 1
                row[position] = ""
                continue
            record["kept"] += 1
            if tokens.resembles(stripped):
                entry = lookalikes.setdefault((slot, stripped), {"count": 0, "first_data_rows": []})
                entry["count"] += 1
                if len(entry["first_data_rows"]) < MAX_ROWS_SHOWN:
                    entry["first_data_rows"].append(number)

    listed = [{"column": stats[slot]["column"], "value": shown(value), "count": entry["count"],
               "first_data_rows": entry["first_data_rows"]}
              for (slot, value), entry in sorted(lookalikes.items(), key=lambda item: (-item[1]["count"], item[0]))]
    totals = {"data_rows": len(rows)}
    for field in ("cells", "blanked", "whitespace_blanked", "whitespace_kept", "already_empty", "kept"):
        totals[field] = sum(record[field] for record in stats)
    review = bool(listed) or totals["whitespace_kept"] > 0

    output = None
    if target is not None:
        output = {"path": options.output, "data_rows": len(rows),
                  **write_copy(target, header, rows, delimiter, newline)}

    document = {
        "tool": TOOL, "version": VERSION, "status": "review_listed" if review else "done",
        "input": {"path": options.input, "sha256": hashlib.sha256(data).hexdigest(), "delimiter": delimiter},
        "rules": {"tokens": list(tokens.spelling.values()), "ignore_case": options.ignore_case,
                  "blank_whitespace_cells": options.blank_whitespace_cells, "allowed_value_tokens": tokens.allowed,
                  "columns": [header[position] for position in positions]},
        "totals": totals,
        "columns": stats,
        "undeclared_lookalikes": listed[:MAX_LISTED],
        "undeclared_lookalikes_distinct": len(listed),
        "undeclared_lookalikes_complete": len(listed) <= MAX_LISTED,
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
