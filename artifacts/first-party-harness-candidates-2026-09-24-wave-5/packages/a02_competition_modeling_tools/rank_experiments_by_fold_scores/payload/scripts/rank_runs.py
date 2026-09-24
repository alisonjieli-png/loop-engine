"""Rank experiment runs by fold scores. Effects: reads one ledger from a file under --root or from standard input; writes nothing; prints one JSON object; no network.

The ledger holds one record per run and fold with a score, as CSV, a JSON array of
objects or JSON Lines. Runs are ranked by their mean fold score in the declared
direction. A gain of one run over another is compared fold by fold on the folds
both runs share. It is established only when, over at least 3 shared folds, the
mean per-fold gain is larger than the sample standard deviation of the per-fold
gains and larger than --min-gain. Runs scored on different folds are not compared.
The reference fold set is the one most runs use (with a tie, the one with more folds).
Only runs on the reference fold set can lead or tie with the leader; the other runs
are ranked after them.

Exit status: 0 ranked, 1 ranked but some runs use a different fold set, 2 refused input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

RECORD_TYPE = "fold_score_ranking/v2"
DEFAULT_MAX_BYTES = 16 * 1024 * 1024
HARD_MAX_BYTES = 256 * 1024 * 1024
MAX_RECORDS = 200000
MAX_RUNS = 5000
MIN_SHARED_FOLDS = 3
SHOWN_RUNS = 100
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
RULE = ("A gain of one run over another is established when, over at least 3 shared folds, the mean of the "
        "per-fold gains is larger than both the sample standard deviation of those gains and min_gain. "
        "Runs scored on different fold sets are not compared, and only runs on the reference fold set can lead. "
        "This is a decision rule, not a significance test.")
VERDICTS = {
    "gain_established": "the gain is larger than its fold-to-fold variation",
    "gain_not_established": "the gain is positive but not larger than its fold-to-fold variation",
    "no_gain": "the mean per-fold gain is zero or negative",
    "too_few_shared_folds": "fewer than 3 shared folds; no verdict is possible",
    "not_comparable": "the two runs were scored on different fold sets",
}


class Refused(Exception):
    """An input or argument this script will not use."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = str(detail)[:300]


class Parser(argparse.ArgumentParser):
    """Argument parser that reports bad arguments as a refused input in JSON."""

    def error(self, message: str):
        raise Refused("bad_arguments", message)


def root_folder(value: str) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refused("root_missing", value) from None
    if not root.is_dir():
        raise Refused("root_not_a_folder", value)
    return root


def under_root(root: Path, relative: str) -> Path:
    """Join a relative path to the root; refuse absolute paths, '..' and symbolic links."""
    if not relative or relative.startswith("/") or "\x00" in relative:
        raise Refused("path_not_relative", relative)
    parts = [part for part in relative.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        raise Refused("path_leaves_root", relative)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise Refused("path_has_symbolic_link", relative)
    return current


def read_input(root: Path, relative: str, limit: int) -> bytes:
    if relative == "-":
        data = sys.stdin.buffer.read(limit + 1)
    else:
        path = under_root(root, relative)
        if not path.is_file():
            raise Refused("input_missing", relative)
        with open(path, "rb") as handle:
            data = handle.read(limit + 1)
    if len(data) > limit:
        raise Refused("input_too_large", f"{relative} is larger than {limit} bytes; raise --max-bytes on purpose")
    return data


def strict_json(text: str):
    def pairs(items):
        keys = [key for key, _value in items]
        if len(keys) != len(set(keys)):
            raise ValueError("an object repeats a key")
        return dict(items)

    def constant(name):
        raise ValueError(f"{name} is not a number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def records_of(text: str) -> tuple[list, str]:
    start = text.lstrip()[:1]
    try:
        if start == "[":
            records = strict_json(text)
            if not isinstance(records, list):
                raise ValueError("the JSON value is not an array")
            return records, "json_array"
        if start == "{":
            return [strict_json(line) for line in text.splitlines() if line.strip()], "json_lines"
    except ValueError as error:
        raise Refused("ledger_not_json", str(error)) from None
    try:
        return list(csv.DictReader(io.StringIO(text, newline=""), strict=True)), "csv"
    except csv.Error as error:
        raise Refused("malformed_csv", str(error)) from None


def text_value(value, what: str, number: int) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise Refused(f"{what}_invalid", f"record {number}: {what} must be text or a whole number")
    text = str(value).strip()
    if not text:
        raise Refused(f"{what}_invalid", f"record {number}: {what} is empty")
    return text


def score_value(value, number: int) -> float:
    if isinstance(value, bool):
        raise Refused("score_invalid", f"record {number}: the score is not a number")
    if isinstance(value, (int, float)):
        score = float(value)
    elif isinstance(value, str) and NUMBER.match(value.strip()):
        score = float(value.strip())
    else:
        raise Refused("score_invalid", f"record {number}: the score {str(value)[:30]!r} is not a number")
    if not math.isfinite(score):
        raise Refused("score_invalid", f"record {number}: the score is not finite")
    return score


def load_runs(data: bytes, args) -> tuple[dict, str, int]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refused("input_not_utf8", f"byte {error.start}") from None
    if not text.strip():
        raise Refused("ledger_empty", args.ledger)
    records, form = records_of(text)
    if not records:
        raise Refused("ledger_empty", args.ledger)
    if len(records) > MAX_RECORDS:
        raise Refused("ledger_too_long", f"{len(records)} records; at most {MAX_RECORDS}")
    runs: dict = {}
    for number, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise Refused("ledger_field_missing", f"record {number} is not an object")
        missing = [name for name in (args.run_column, args.fold_column, args.score_column) if name not in record]
        if missing:
            raise Refused("ledger_field_missing", f"record {number} has no {missing}")
        run = text_value(record[args.run_column], "run", number)
        fold = text_value(record[args.fold_column], "fold", number)
        score = score_value(record[args.score_column], number)
        folds = runs.setdefault(run, {})
        if fold in folds:
            raise Refused("duplicate_run_fold", f"run {run!r} has fold {fold!r} twice (record {number})")
        folds[fold] = score
    if len(runs) > MAX_RUNS:
        raise Refused("ledger_too_long", f"{len(runs)} runs; at most {MAX_RUNS}")
    return runs, form, len(records)


def rounded(value):
    return round(value, 10) if isinstance(value, float) else value


def compare(runs: dict, better: str, other: str, sign: int, min_gain: float, tiny: float) -> dict:
    """Per-fold gains of `better` over `other` in the declared direction, with a verdict."""
    first, second = runs[better], runs[other]
    result = {"shared_folds": len(set(first) & set(second))}
    if set(first) != set(second):
        return {**result, "verdict": "not_comparable"}
    gains = [sign * (first[fold] - second[fold]) for fold in sorted(first)]
    mean = math.fsum(gains) / len(gains)
    spread = statistics.stdev(gains) if len(gains) > 1 else None
    if len(gains) < MIN_SHARED_FOLDS:
        verdict = "too_few_shared_folds"
    elif mean <= tiny:
        verdict = "no_gain"
    elif mean > max(spread, min_gain, tiny):
        verdict = "gain_established"
    else:
        verdict = "gain_not_established"
    return {**result, "mean_gain": rounded(mean), "gain_spread": rounded(spread),
            "folds_with_gain": sum(1 for gain in gains if gain > tiny), "verdict": verdict}


def rank(runs: dict, args) -> tuple[dict, int]:
    sign = 1 if args.direction == "maximize" else -1
    scale = max([1.0] + [abs(score) for folds in runs.values() for score in folds.values()])
    tiny = 1e-12 * scale
    facts = {}
    for run, folds in runs.items():
        scores = list(folds.values())
        facts[run] = {"mean": math.fsum(scores) / len(scores),
                      "fold_std": statistics.stdev(scores) if len(scores) > 1 else None, "folds": len(scores)}
    fold_sets = Counter(frozenset(folds) for folds in runs.values())
    reference = min(fold_sets, key=lambda folds: (-fold_sets[folds], -len(folds), sorted(folds)))
    order = sorted(runs, key=lambda run: (frozenset(runs[run]) != reference, -sign * facts[run]["mean"],
                                          facts[run]["fold_std"] if facts[run]["fold_std"] is not None else math.inf,
                                          run))
    mismatch = [run for run in order if frozenset(runs[run]) != reference]
    comparable = len(order) - len(mismatch)
    leader = order[0]
    ranking = []
    for position, run in enumerate(order):
        row = {"rank": position + 1, "run": run, "mean": rounded(facts[run]["mean"]),
               "fold_std": rounded(facts[run]["fold_std"]), "folds": facts[run]["folds"],
               "same_folds_as_reference": position < comparable}
        if position > 0:
            row["leader_over_this"] = compare(runs, leader, run, sign, args.min_gain, tiny)
        if position + 1 < len(order):
            row["over_next"] = {"next_run": order[position + 1],
                                **compare(runs, run, order[position + 1], sign, args.min_gain, tiny)}
        ranking.append(row)
    tied = [row["run"] for row in ranking[1:comparable]
            if row["leader_over_this"]["verdict"] in ("gain_not_established", "no_gain")]
    baseline = None
    if args.baseline is not None:
        if args.baseline not in runs:
            raise Refused("baseline_missing", f"no run named {args.baseline!r}; runs: {order[:20]}")
        comparisons = [{"run": run, **compare(runs, run, args.baseline, sign, args.min_gain, tiny)}
                       for run in order if run != args.baseline]
        baseline = {"run": args.baseline, "comparisons": comparisons[:SHOWN_RUNS],
                    "beats_baseline": [item["run"] for item in comparisons if item["verdict"] == "gain_established"]}
    report = {"record_type": RECORD_TYPE, "status": "fold_sets_differ" if mismatch else "pass",
              "settings": {"direction": args.direction, "baseline": args.baseline, "min_gain": args.min_gain,
                           "columns": {"run": args.run_column, "fold": args.fold_column, "score": args.score_column}},
              "rule": RULE, "verdict_meanings": VERDICTS, "runs": len(order), "leader": leader,
              "leader_established": ranking[1]["leader_over_this"]["verdict"] == "gain_established"
              if comparable > 1 else None,
              "tied_with_leader": tied[:SHOWN_RUNS], "ranking": ranking[:SHOWN_RUNS],
              "ranking_truncated": len(ranking) > SHOWN_RUNS, "baseline": baseline,
              "fold_set_mismatch": mismatch[:SHOWN_RUNS], "reference_folds": sorted(reference)[:50]}
    return report, 1 if mismatch else 0


def build_parser() -> Parser:
    parser = Parser(description="Rank experiment runs by per-fold scores. Exit 0 ranked, 1 fold sets differ, 2 refused.")
    parser.add_argument("--root", default=".", help="folder that the ledger path is relative to (default: current folder)")
    parser.add_argument("--ledger", required=True, help="CSV, JSON array or JSON Lines ledger under --root, or - for standard input")
    parser.add_argument("--direction", required=True, choices=("maximize", "minimize"),
                        help="maximize for accuracy or AUC, minimize for errors and losses")
    parser.add_argument("--baseline", help="run to compare every other run against")
    parser.add_argument("--min-gain", type=float, default=0.0,
                        help="smallest mean gain that can count as established (default 0)")
    parser.add_argument("--run-column", default="run", help="field that names the run (default run)")
    parser.add_argument("--fold-column", default="fold", help="field that names the fold (default fold)")
    parser.add_argument("--score-column", default="score", help="field that holds the score (default score)")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"refuse a ledger larger than this (default {DEFAULT_MAX_BYTES}, at most {HARD_MAX_BYTES})")
    return parser


def execute(args) -> tuple[dict, int]:
    if not 1 <= args.max_bytes <= HARD_MAX_BYTES:
        raise Refused("bad_arguments", f"--max-bytes must be between 1 and {HARD_MAX_BYTES}")
    if not math.isfinite(args.min_gain) or args.min_gain < 0:
        raise Refused("bad_arguments", "--min-gain must be a number of at least 0")
    root = root_folder(args.root)
    data = read_input(root, args.ledger, args.max_bytes)
    runs, form, count = load_runs(data, args)
    report, status = rank(runs, args)
    report["input"] = {"path": args.ledger, "sha256": hashlib.sha256(data).hexdigest(), "format": form,
                       "records": count}
    return report, status


def main(argv=None) -> int:
    try:
        args = build_parser().parse_args(argv)
        report, status = execute(args)
    except Refused as error:
        report, status = {"record_type": RECORD_TYPE, "status": "refused", "reason": error.reason,
                          "detail": error.detail}, 2
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return status


if __name__ == "__main__":
    sys.exit(main())
