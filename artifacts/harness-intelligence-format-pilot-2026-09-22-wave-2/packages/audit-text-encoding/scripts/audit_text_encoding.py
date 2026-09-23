"""Bounded UTF-8 and newline audit without returning source text."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

from confined_input import ConfinedInputError, open_approved_file

MAX_INPUT_BYTES = 20_000_000
MAX_LINE_CHARS = 100_000
NEWLINES = re.compile(r"\r\n|\r|\n")


def audit(args: argparse.Namespace) -> dict[str, object]:
    if not 0 < args.max_bytes <= MAX_INPUT_BYTES:
        raise ConfinedInputError("max_bytes_outside_supported_ceiling")
    if not 0 < args.max_line_chars <= MAX_LINE_CHARS:
        raise ConfinedInputError("max_line_chars_outside_supported_ceiling")
    with open_approved_file(args.approved_root, args.input_relative) as handle:
        if os.fstat(handle.fileno()).st_size > args.max_bytes:
            raise ConfinedInputError("input_exceeds_byte_ceiling")
        raw = handle.read(args.max_bytes + 1)
    if len(raw) > args.max_bytes:
        raise ConfinedInputError("input_exceeds_byte_ceiling")
    digest = hashlib.sha256(raw).hexdigest()
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig" if bom else "utf-8")
    except UnicodeDecodeError:
        return {
            "schema": "text_encoding_audit/v1",
            "status": "fail",
            "sha256": digest,
            "bytes": len(raw),
            "failures": ["invalid_utf8"],
        }
    endings = {"crlf": text.count("\r\n")}
    endings["lf"] = text.count("\n") - endings["crlf"]
    endings["cr"] = text.count("\r") - endings["crlf"]
    lines = NEWLINES.split(text)
    if text.endswith(("\r", "\n")):
        lines.pop()
    if not text:
        lines = []
    too_long = sum(len(line) > args.max_line_chars for line in lines)
    trailing_whitespace = sum(line.endswith((" ", "\t")) for line in lines)
    failures = []
    if "\x00" in text:
        failures.append("nul_character")
    if sum(bool(value) for value in endings.values()) > 1:
        failures.append("mixed_newline_styles")
    if too_long:
        failures.append("line_length_exceeds_ceiling")
    return {
        "schema": "text_encoding_audit/v1",
        "status": "fail" if failures else "pass",
        "sha256": digest,
        "bytes": len(raw),
        "utf8_bom": bom,
        "physical_lines": len(lines),
        "newline_counts": endings,
        "lines_over_limit": too_long,
        "lines_with_trailing_whitespace": trailing_whitespace,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-root", required=True)
    parser.add_argument("--input-relative", required=True)
    parser.add_argument("--max-bytes", type=int, default=MAX_INPUT_BYTES)
    parser.add_argument("--max-line-chars", type=int, default=10_000)
    args = parser.parse_args()
    try:
        result = audit(args)
    except (ConfinedInputError, OSError) as error:
        result = {
            "schema": "text_encoding_audit/v1",
            "status": "refused",
            "reason": str(error),
        }
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "refused": 2}[str(result["status"])]


if __name__ == "__main__":
    sys.exit(main())
