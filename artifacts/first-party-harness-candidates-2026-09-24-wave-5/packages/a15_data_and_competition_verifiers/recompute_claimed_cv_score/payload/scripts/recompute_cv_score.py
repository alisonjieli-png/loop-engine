"""Recompute a claimed cross-validation score from out-of-fold predictions. Effects: reads the named files under --root or one JSON bundle; prints one JSON object; writes nothing, starts no process and uses no network.

Exit status: 0 every claim is within its tolerance of the recomputed score and every row has a fold,
a prediction and a label, 1 at least one check failed, 2 no verdict (refused input, a metric without
a value for some fold, or an internal error).

The rows that the cross-validation must cover come from the fold file when one is given, else from
the label file, else from the predictions file.

Usage:
    python3 -I -B recompute_cv_score.py --predictions OOF.csv --metric METRIC --claimed-score VALUE
        [--folds FOLDS.csv] [--labels TRAIN.csv] [--id-column id] [--prediction-column prediction]
        [--label-column target] [--fold-column fold] [--positive-label 1] [--threshold X]
        [--claim-kind mean|weighted_mean|pooled] [--claimed-fold FOLD=VALUE ...] [--tolerance X]
        [--root DIR] [--delimiter comma|tab|semicolon|pipe] [--max-bytes N]
    python3 -I -B recompute_cv_score.py --bundle FILE_OR_DASH --metric METRIC --claimed-score VALUE ...

Metrics: accuracy, balanced_accuracy, f1, roc_auc, log_loss, rmse, mae, r2 and rmsle, defined in
references/metrics.md. A bundle is one JSON object with the members "predictions", "folds" and
"labels", each holding the text of that file; "-" reads the bundle from standard input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
from decimal import Decimal
from pathlib import Path

RECORD_TYPE = "cv_score_recomputation/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";", "pipe": "|"}
BUNDLE_MEMBERS = ("predictions", "folds", "labels")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,4})?")
LABEL_METRICS = ("accuracy", "balanced_accuracy", "f1")
SCORE_METRICS = ("roc_auc", "log_loss")
NUMBER_METRICS = ("rmse", "mae", "r2", "rmsle")
METRICS = LABEL_METRICS + SCORE_METRICS + NUMBER_METRICS
CLAIM_KINDS = ("mean", "weighted_mean", "pooled")
LOG_LOSS_CLIP = 1e-15
SLACK = 1e-12
SHOWN_DIGITS = 8


class Refused(Exception):
    """An input or argument the script will not check; reported with exit code 2."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = str(detail)[:400]


class Parser(argparse.ArgumentParser):
    """Argument parser that reports a bad argument as a refused input in JSON."""

    def error(self, message: str):
        raise Refused("bad_arguments", message)


def strict_json(text: str, label: str):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"{name} is not allowed in JSON")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except RecursionError:
        raise Refused("json_invalid", f"{label}: nested too deeply") from None
    except ValueError as error:
        raise Refused("json_invalid", f"{label}: {error}") from None


def decode(data: bytes, label: str) -> str:
    if data[:2] == b"\x1f\x8b" or data[:4] == b"PK\x03\x04":
        raise Refused("compressed_input", f"{label} is a compressed file; check the unpacked text")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refused("not_utf8", f"{label}: byte {error.start} is not UTF-8") from None
    if "\x00" in text:
        raise Refused("not_text", f"{label} holds a NUL character")
    return text


class Inputs:
    """Named inputs read from files under --root, or from members of one JSON bundle."""

    def __init__(self, root: str, bundle: str | None, limit: int) -> None:
        self.limit = limit
        try:
            self.root = Path(root).resolve(strict=True)
        except (OSError, RuntimeError):
            raise Refused("root_missing", root) from None
        if not self.root.is_dir():
            raise Refused("root_not_a_folder", root)
        self.bundle = None
        if bundle is not None:
            data = sys.stdin.buffer.read(limit + 1) if bundle == "-" else self.read_file(bundle)
            if len(data) > limit:
                raise Refused("input_too_large", f"the bundle is larger than {limit} bytes")
            value = strict_json(decode(data, "the bundle"), "the bundle")
            if not isinstance(value, dict):
                raise Refused("bundle_invalid", "the bundle is one JSON object")
            unknown = sorted(set(value) - set(BUNDLE_MEMBERS))
            if unknown:
                raise Refused("bundle_invalid", f"unknown bundle members {unknown}; allowed {list(BUNDLE_MEMBERS)}")
            self.bundle = value

    def read_file(self, value: str) -> bytes:
        if not value or "\x00" in value:
            raise Refused("path_invalid", repr(value))
        given = Path(value)
        if ".." in given.parts:
            raise Refused("path_leaves_root", f"{value}: a path may not contain '..'")
        candidate = given if given.is_absolute() else self.root / given
        try:
            real = candidate.resolve(strict=True)
        except FileNotFoundError:
            raise Refused("input_missing", value) from None
        except (OSError, RuntimeError) as error:
            raise Refused("input_unreadable", f"{value}: {error}") from None
        if real != self.root and self.root not in real.parents:
            raise Refused("path_leaves_root", f"{value} resolves to a place outside --root")
        if not real.is_file():
            raise Refused("not_a_regular_file", value)
        try:
            with open(real, "rb") as handle:
                data = handle.read(self.limit + 1)
        except OSError as error:
            raise Refused("input_unreadable", f"{value}: {error.strerror}") from None
        if len(data) > self.limit:
            raise Refused("input_too_large", f"{value} is larger than {self.limit} bytes; raise --max-bytes on purpose")
        return data

    def get(self, name: str, path: str | None, required: bool):
        """Return (label, bytes) for one input, or None for an optional input that was not given."""
        if self.bundle is not None and name in self.bundle:
            if path is not None:
                raise Refused("bad_arguments", f"--{name} and the bundle member {name!r} were both given; use one")
            value = self.bundle[name]
            if not isinstance(value, str):
                raise Refused("bundle_invalid", f"bundle member {name!r} must hold the file text")
            try:
                return f"bundle:{name}", value.encode("utf-8")
            except UnicodeEncodeError:
                raise Refused("not_utf8", f"bundle member {name!r} holds text that is not valid UTF-8") from None
        if path is None:
            if required:
                raise Refused("bad_arguments", f"--{name} is required (or a bundle member {name!r})")
            return None
        return path, self.read_file(path)


class Table:
    """A UTF-8 delimited text with one header row, read completely and indexed by its id column."""

    def __init__(self, label: str, data: bytes, delimiter: str, limit: int) -> None:
        self.label = label
        self.sha256 = hashlib.sha256(data).hexdigest()
        text = decode(data, label)
        csv.field_size_limit(max(limit, 131072))
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        records, end = [], 0
        try:
            for fields in reader:
                records.append((end + 1, fields))
                end = reader.line_num
        except csv.Error as error:
            raise Refused("malformed_csv", f"{label} near line {reader.line_num}: {error}") from None
        if not records or not records[0][1]:
            raise Refused("header_missing", f"{label}: the first line must be the header row")
        self.header = records[0][1]
        repeated = sorted({name for name in self.header if self.header.count(name) > 1})
        if repeated:
            raise Refused("duplicate_column_name", f"{label}: column names repeat: {repeated[:10]}")
        width = len(self.header)
        self.rows: list = []
        for line, fields in records[1:]:
            if not fields:
                if width != 1:
                    continue
                fields = [""]
            if len(fields) != width:
                raise Refused("ragged_rows", f"{label} line {line} has {len(fields)} fields and the header has "
                              f"{width}; check the table structure first")
            self.rows.append((line, fields))
        self.position = {name: index for index, name in enumerate(self.header)}
        self.index: dict[str, int] = {}

    def column(self, name: str, option: str) -> int:
        if name not in self.position:
            raise Refused("column_missing", f"{option} {name!r} is not a column of {self.label}; its columns are "
                          f"{self.header[:40]}")
        return self.position[name]

    def index_by(self, name: str) -> None:
        at = self.column(name, "--id-column")
        for number, (line, fields) in enumerate(self.rows):
            value = fields[at]
            if value == "":
                raise Refused("empty_id", f"{self.label} line {line} has an empty {name}")
            if value in self.index:
                raise Refused("duplicate_id", f"{self.label} lines {self.rows[self.index[value]][0]} and {line} share "
                              f"one {name}; each row has one prediction, one label and one fold")
            self.index[value] = number

    def value(self, identity: str, column: int):
        number = self.index.get(identity)
        return None if number is None else self.rows[number][1][column]


def number_of(text: str):
    if not NUMBER.fullmatch(text.strip()):
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def class_of(text: str) -> tuple:
    """Labels and predictions that both read as numbers are compared as numbers, so 1 equals 1.0."""
    value = number_of(text)
    return ("number", value) if value is not None else ("text", text)


def class_text(item: tuple) -> str:
    kind, value = item
    return value if kind == "text" else repr(value)


def fold_order(folds) -> list:
    folds = list(folds)
    if all(number_of(fold) is not None for fold in folds):
        return sorted(folds, key=lambda fold: (number_of(fold), fold))
    return sorted(folds)


def mean(values) -> float:
    values = list(values)
    return math.fsum(values) / len(values)


def auc(scores: list, positive: list):
    """Rank formula: the chance that a positive row scores above a negative row, ties counting one half."""
    count = len(scores)
    order = sorted(range(count), key=lambda index: scores[index])
    ranks = [0.0] * count
    start = 0
    while start < count:
        stop = start
        while stop + 1 < count and scores[order[stop + 1]] == scores[order[start]]:
            stop += 1
        for place in range(start, stop + 1):
            ranks[order[place]] = (start + stop) / 2 + 1
        start = stop + 1
    positives = sum(1 for flag in positive if flag)
    negatives = count - positives
    if positives == 0 or negatives == 0:
        return None
    rank_sum = math.fsum(rank for rank, flag in zip(ranks, positive) if flag)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


class Metric:
    """One metric with its settings. Each row is (label text, prediction text)."""

    def __init__(self, name: str, positive_label: str, threshold) -> None:
        self.name, self.threshold = name, threshold
        self.positive = class_of(positive_label)

    def is_positive(self, text: str) -> bool:
        return class_of(text) == self.positive

    def guess_is_positive(self, prediction: str) -> bool:
        if self.threshold is not None:
            return number_of(prediction) >= self.threshold
        return self.is_positive(prediction)

    def score(self, rows: list):
        """Return the metric over the rows, or None when it has no value for them."""
        if not rows:
            return None
        name = self.name
        if name in NUMBER_METRICS:
            pairs = [(number_of(label), number_of(prediction)) for label, prediction in rows]
            if name == "rmse":
                return math.sqrt(mean((guess - truth) ** 2 for truth, guess in pairs))
            if name == "mae":
                return mean(abs(guess - truth) for truth, guess in pairs)
            if name == "rmsle":
                return math.sqrt(mean((math.log1p(guess) - math.log1p(truth)) ** 2 for truth, guess in pairs))
            centre = mean(truth for truth, _guess in pairs)
            spread = math.fsum((truth - centre) ** 2 for truth, _guess in pairs)
            if spread == 0:
                return None
            return 1 - math.fsum((truth - guess) ** 2 for truth, guess in pairs) / spread
        if name == "roc_auc":
            return auc([number_of(prediction) for _label, prediction in rows],
                       [self.is_positive(label) for label, _prediction in rows])
        if name == "log_loss":
            losses = []
            for label, prediction in rows:
                probability = min(max(number_of(prediction), LOG_LOSS_CLIP), 1 - LOG_LOSS_CLIP)
                losses.append(-math.log(probability if self.is_positive(label) else 1 - probability))
            return mean(losses)
        if self.threshold is not None or name == "f1":
            judged = [(self.is_positive(label), self.guess_is_positive(prediction)) for label, prediction in rows]
        else:
            judged = [(class_of(label), class_of(prediction)) for label, prediction in rows]
        if name == "accuracy":
            return sum(1 for truth, guess in judged if truth == guess) / len(judged)
        if name == "balanced_accuracy":
            recalls = []
            for kind in {truth for truth, _guess in judged}:
                members = [guess for truth, guess in judged if truth == kind]
                recalls.append(sum(1 for guess in members if guess == kind) / len(members))
            return mean(sorted(recalls))
        true_positive = sum(1 for truth, guess in judged if truth and guess)
        false_positive = sum(1 for truth, guess in judged if not truth and guess)
        false_negative = sum(1 for truth, guess in judged if truth and not guess)
        denominator = 2 * true_positive + false_positive + false_negative
        return None if denominator == 0 else 2 * true_positive / denominator


def claim_value(text: str, option: str) -> tuple:
    """Return (value, tolerance from the written precision) for one claimed score."""
    if not isinstance(text, str) or not NUMBER.fullmatch(text.strip()):
        raise Refused("bad_arguments", f"{option} is a plain number such as 0.8123, copied as the claim writes it")
    written = Decimal(text.strip())
    return float(written), 0.5 * 10.0 ** written.as_tuple().exponent


def rounded(value):
    return None if value is None else round(value, SHOWN_DIGITS)


def explain(metric: str, kind: str, value: float, tolerance: float, results: dict) -> list:
    """Say what a failed claim matches instead, when it matches something."""
    hints = []
    for other, result in results.items():
        if other != kind and result is not None and abs(value - result) <= tolerance + SLACK:
            hints.append(f"the claim matches the {other} score, not the {kind} score; if that is what the claim "
                         "means, run again with --claim-kind " + other)
    target = results[kind]
    if target is not None:
        if target != 0 and abs(value + target) <= tolerance + SLACK:
            hints.append("the claim has the opposite sign; some libraries report error metrics as negative scores")
        if metric == "roc_auc" and abs(value - (1 - target)) <= tolerance + SLACK:
            hints.append("the claim equals 1 minus the recomputed AUC; the positive label or the score direction may "
                         "be reversed")
        if metric == "rmse" and abs(value - target ** 2) <= tolerance + SLACK:
            hints.append("the claim equals the squared error, not its square root")
    if not hints:
        hints.append("the claim matches no score this script computes from these files; report where the claim "
                     "came from")
    return hints


def build_parser() -> Parser:
    parser = Parser(description="Recompute a claimed cross-validation score. Exit 0 pass, 1 fail, 2 no verdict.")
    parser.add_argument("--predictions", help="the out-of-fold predictions, relative to --root")
    parser.add_argument("--folds", help="the fold file; without it the fold column is read from --predictions")
    parser.add_argument("--labels", help="the table with true labels; without it the label is read from --predictions")
    parser.add_argument("--bundle", help="one JSON object with the members predictions, folds and labels; "
                        "- reads standard input")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--metric", choices=METRICS, help="the metric the claim uses")
    parser.add_argument("--claimed-score", help="the claimed score, copied with all its decimals")
    parser.add_argument("--claim-kind", choices=CLAIM_KINDS, default="mean",
                        help="what the claim is: the mean of fold scores (default), the mean weighted by rows, or "
                        "one pooled score over all rows")
    parser.add_argument("--claimed-fold", action="append", default=[], metavar="FOLD=VALUE",
                        help="a claimed score for one fold; repeat it for each fold claim")
    parser.add_argument("--tolerance", type=float,
                        help="largest allowed difference; default: half a unit of the last decimal of each claim")
    parser.add_argument("--id-column", default="id", help="row id column in every file (default id)")
    parser.add_argument("--prediction-column", default="prediction", help="prediction column (default prediction)")
    parser.add_argument("--label-column", default="target", help="true label column (default target)")
    parser.add_argument("--fold-column", default="fold", help="fold column (default fold)")
    parser.add_argument("--positive-label", default="1",
                        help="the positive label for f1, roc_auc, log_loss and --threshold (default 1)")
    parser.add_argument("--threshold", type=float, help="turn probability predictions into labels: a prediction at "
                        "or above it means the positive label (accuracy, balanced_accuracy and f1)")
    parser.add_argument("--delimiter", default="comma", help="comma (default), tab, semicolon, pipe or one character")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"refuse a file larger than this (default {DEFAULT_MAX_BYTES})")
    return parser


def check_arguments(args) -> tuple:
    if not 1 <= args.max_bytes <= HARD_MAX_BYTES:
        raise Refused("bad_arguments", f"--max-bytes is between 1 and {HARD_MAX_BYTES}")
    delimiter = DELIMITERS.get(args.delimiter, args.delimiter)
    if len(delimiter) != 1 or delimiter in "\"\r\n":
        raise Refused("bad_arguments", "--delimiter is comma, tab, semicolon, pipe or one character")
    if args.metric is None:
        raise Refused("bad_arguments", f"--metric is required: one of {list(METRICS)}")
    if args.claimed_score is None and not args.claimed_fold:
        raise Refused("bad_arguments", "give the claim with --claimed-score, copied from where the claim is written; "
                      "a score printed by this script is not a claim")
    if args.tolerance is not None and not (math.isfinite(args.tolerance) and args.tolerance >= 0):
        raise Refused("bad_arguments", "--tolerance is a number of 0 or more")
    if args.threshold is not None:
        if args.metric not in LABEL_METRICS:
            raise Refused("bad_arguments", f"--threshold applies to {list(LABEL_METRICS)}, not {args.metric}")
        if not math.isfinite(args.threshold):
            raise Refused("bad_arguments", "--threshold is a finite number")
    fold_claims = {}
    for item in args.claimed_fold:
        fold, separator, value = item.partition("=")
        if not separator or not fold or fold in fold_claims:
            raise Refused("bad_arguments", f"--claimed-fold {item!r} is FOLD=VALUE, once for each fold")
        fold_claims[fold] = claim_value(value, f"--claimed-fold {fold}")
    claimed = claim_value(args.claimed_score, "--claimed-score") if args.claimed_score is not None else None
    return delimiter, claimed, fold_claims


def run(args) -> tuple:
    delimiter, claimed, fold_claims = check_arguments(args)
    inputs = Inputs(args.root, args.bundle, args.max_bytes)
    predictions = Table(*inputs.get("predictions", args.predictions, True), delimiter, args.max_bytes)
    folds_given = inputs.get("folds", args.folds, False)
    labels_given = inputs.get("labels", args.labels, False)
    fold_table = Table(*folds_given, delimiter, args.max_bytes) if folds_given else predictions
    label_table = Table(*labels_given, delimiter, args.max_bytes) if labels_given else predictions
    for table in {id(table): table for table in (predictions, fold_table, label_table)}.values():
        table.index_by(args.id_column)
    prediction_at = predictions.column(args.prediction_column, "--prediction-column")
    fold_at = fold_table.column(args.fold_column, "--fold-column")
    label_at = label_table.column(args.label_column, "--label-column")
    population, origin = (fold_table, "folds") if folds_given else (label_table, "labels") if labels_given \
        else (predictions, "predictions")

    checks = {"rows_without_fold": 0, "rows_without_prediction": 0, "rows_without_label": 0,
              "predictions_for_unknown_rows": sum(1 for identity in predictions.index
                                                  if identity not in population.index)}
    copy_at = predictions.position.get(args.fold_column) if folds_given else None
    if copy_at is not None:
        checks["fold_column_differs"] = 0
    scored = []
    for identity in population.index:
        fold = fold_table.value(identity, fold_at)
        prediction = predictions.value(identity, prediction_at)
        label = label_table.value(identity, label_at)
        if fold in (None, ""):
            checks["rows_without_fold"] += 1
        if prediction in (None, ""):
            checks["rows_without_prediction"] += 1
        if label in (None, ""):
            checks["rows_without_label"] += 1
        if copy_at is not None and prediction is not None and predictions.value(identity, copy_at) != fold:
            checks["fold_column_differs"] += 1
        if fold not in (None, "") and prediction not in (None, "") and label not in (None, ""):
            scored.append((fold, label, prediction))
    if not scored:
        raise Refused("nothing_to_score", "no row has a fold, a prediction and a label; check --id-column and the "
                      "column names")

    # Refuse values the metric cannot use, before any score is computed.
    metric = Metric(args.metric, args.positive_label, args.threshold)
    needs_two_labels = args.metric in SCORE_METRICS or args.metric == "f1" or args.threshold is not None
    classes = sorted({class_of(label) for _fold, label, _prediction in scored}, key=repr)
    if needs_two_labels and (len(classes) != 2 or metric.positive not in classes):
        raise Refused("labels_not_binary", f"{args.metric} with these settings needs exactly two label values, one of "
                      f"them --positive-label {args.positive_label!r}; the labels hold {len(classes)} values, such as "
                      f"{[class_text(item) for item in classes[:10]]}")
    for fold, label, prediction in scored:
        if args.metric in NUMBER_METRICS:
            truth, guess = number_of(label), number_of(prediction)
            if truth is None or guess is None:
                raise Refused("not_a_number", f"{args.metric} needs numeric labels and predictions; a row of fold "
                              f"{fold!r} holds text")
            if args.metric == "rmsle" and (truth < 0 or guess < 0):
                raise Refused("negative_value", "rmsle needs labels and predictions of 0 or more")
        elif args.metric in SCORE_METRICS or args.threshold is not None:
            guess = number_of(prediction)
            if guess is None:
                raise Refused("not_a_number", f"{args.metric} with these settings needs numeric predictions; a row of "
                              f"fold {fold!r} holds text")
            if args.metric == "log_loss" and not 0 <= guess <= 1:
                raise Refused("probability_out_of_range", f"log_loss needs probabilities from 0 to 1; a row of fold "
                              f"{fold!r} holds {guess}")

    rows_by_fold: dict[str, list] = {}
    for fold, label, prediction in scored:
        rows_by_fold.setdefault(fold, []).append((label, prediction))
    fold_names = fold_order(rows_by_fold)
    scores = {}
    for fold in fold_names:
        score = metric.score(rows_by_fold[fold])
        if score is None:
            raise Refused("metric_undefined", f"{args.metric} has no value for fold {fold!r}, for example because the "
                          "fold holds one label value or a constant label; no mean of fold scores exists")
        scores[fold] = score
    every_row = [row for fold in fold_names for row in rows_by_fold[fold]]
    results = {"mean": mean(scores.values()),
               "weighted_mean": math.fsum(scores[fold] * len(rows_by_fold[fold]) for fold in fold_names) / len(every_row),
               "pooled": metric.score(every_row)}
    values = list(scores.values())
    recomputed = {kind: rounded(value) for kind, value in results.items()}
    recomputed.update({"fold_min": rounded(min(values)), "fold_max": rounded(max(values)),
                       "fold_standard_deviation": rounded(math.sqrt(mean((value - results["mean"]) ** 2
                                                                          for value in values)))})

    hints, claim_report = [], None
    if claimed is not None:
        value, precision = claimed
        tolerance = args.tolerance if args.tolerance is not None else precision
        target = results[args.claim_kind]
        within = target is not None and abs(value - target) <= tolerance + SLACK
        checks["claim_differs"] = 0 if within else 1
        claim_report = {"kind": args.claim_kind, "claimed": value, "recomputed": rounded(target),
                        "difference": None if target is None else rounded(value - target), "tolerance": tolerance,
                        "tolerance_source": "--tolerance" if args.tolerance is not None else "claim_precision",
                        "within_tolerance": within}
        if not within:
            hints += explain(args.metric, args.claim_kind, value, tolerance, results)
    unknown = sorted(set(fold_claims) - set(scores))
    if unknown:
        raise Refused("claimed_fold_unknown", f"--claimed-fold names {unknown[:10]}, which are not folds of the file; "
                      f"its folds are {fold_names[:20]}")
    if fold_claims:
        checks["fold_claims_differ"] = 0
    fold_report = []
    for fold in fold_names:
        item = {"fold": fold, "rows": len(rows_by_fold[fold]), "score": rounded(scores[fold])}
        if fold in fold_claims:
            value, precision = fold_claims[fold]
            tolerance = args.tolerance if args.tolerance is not None else precision
            within = abs(value - scores[fold]) <= tolerance + SLACK
            item.update({"claimed": value, "difference": rounded(value - scores[fold]), "tolerance": tolerance,
                         "within_tolerance": within})
            checks["fold_claims_differ"] += 0 if within else 1
        fold_report.append(item)
    failed = [name for name, count in checks.items() if count]
    inputs_report = {}
    for name, table in (("predictions", predictions), ("folds", fold_table), ("labels", label_table)):
        if name == "predictions" or table is not predictions:
            inputs_report[name] = {"path": table.label, "sha256": table.sha256, "rows": len(table.rows)}
    report = {
        "record_type": RECORD_TYPE,
        "status": "fail" if failed else "pass",
        "metric": args.metric,
        "positive_label": args.positive_label if needs_two_labels else None,
        "threshold": args.threshold,
        "claim": claim_report,
        "recomputed": recomputed,
        "folds": fold_report,
        "coverage": {"rows_expected": len(population.index), "rows_expected_from": origin,
                     "rows_scored": len(scored), **{name: checks[name] for name in (
                         "rows_without_fold", "rows_without_prediction", "rows_without_label",
                         "predictions_for_unknown_rows")}},
        "checks": checks,
        "failed_checks": failed,
        "hints": hints,
        "inputs": inputs_report,
        "rounding": f"scores in this report are rounded to {SHOWN_DIGITS} decimals; comparisons use full precision",
    }
    return report, 1 if failed else 0


def emit(report: dict) -> None:
    sys.stdout.buffer.write((json.dumps(report, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def main(argv=None) -> int:
    try:
        report, status = run(build_parser().parse_args(argv))
    except Refused as error:
        report, status = {"record_type": RECORD_TYPE, "status": "refused", "reason": error.reason,
                          "detail": error.detail}, 2
    except Exception as error:  # noqa: BLE001 - an internal error must not look like a failed check
        report, status = {"record_type": RECORD_TYPE, "status": "error", "reason": "internal_error",
                          "detail": f"{type(error).__name__}: {error}"[:400]}, 2
    emit(report)
    return status


if __name__ == "__main__":
    sys.exit(main())
