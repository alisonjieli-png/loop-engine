"""The report every asset contract tool returns, and the command line behaviour they share.

A report is one JSON object: record_type, tool, subject, ok, failures, warnings and facts. ``ok`` is true
exactly when there are no failures. Each failure or warning carries a closed code, the place it was found
(``where``) and a short detail. Facts are what the tool read from the input, rounded so the same input always
prints the same report. A tool's command line prints the report and exits 0 when ok, 1 when not, and 2 when
its arguments are unusable (argparse's own exit).
"""
from __future__ import annotations

import json
import math

RECORD_TYPE = "asset_contract_report/v1"
DETAIL_LIMIT = 500


def rounded(value, places: int = 6):
    """``value`` with every float rounded and every non-finite float replaced by None, recursively."""
    if isinstance(value, float):
        return round(value, places) + 0.0 if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): rounded(item, places) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(item, places) for item in value]
    return value


class Report:
    """Failures, warnings and facts collected by one tool run over one subject."""

    def __init__(self, tool: str, subject: str = "") -> None:
        self.tool, self.subject = tool, subject
        self.failures, self.warnings, self.facts = [], [], {}

    def fail(self, code: str, where="", detail="") -> None:
        self.failures.append({"code": code, "where": str(where), "detail": str(detail)[:DETAIL_LIMIT]})

    def warn(self, code: str, where="", detail="") -> None:
        self.warnings.append({"code": code, "where": str(where), "detail": str(detail)[:DETAIL_LIMIT]})

    def codes(self) -> list:
        """The distinct failure codes, sorted."""
        return sorted({failure["code"] for failure in self.failures})

    def as_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "tool": self.tool, "subject": self.subject,
                "ok": not self.failures, "failures": self.failures, "warnings": self.warnings,
                "facts": rounded(self.facts)}


def emit(report: dict) -> int:
    """Print the report as JSON and return the exit status: 0 when ok, 1 otherwise."""
    print(json.dumps(report, indent=1, sort_keys=True, allow_nan=False))
    return 0 if report.get("ok") is True else 1


def read_json_file(path, report: Report, code: str = "file_unreadable"):
    """A JSON file's value, or None after recording ``code`` (unreadable, not UTF-8, invalid or repeated keys)."""
    def pairs(entries):
        keys = [key for key, _value in entries]
        if len(keys) != len(set(keys)):
            raise ValueError("repeated key " + ", ".join(sorted({key for key in keys if keys.count(key) > 1})))
        return dict(entries)

    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=pairs)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        report.fail(code, str(path), f"{type(error).__name__}: {error}"[:200])
        return None


__all__ = ["RECORD_TYPE", "Report", "rounded", "emit", "read_json_file"]
