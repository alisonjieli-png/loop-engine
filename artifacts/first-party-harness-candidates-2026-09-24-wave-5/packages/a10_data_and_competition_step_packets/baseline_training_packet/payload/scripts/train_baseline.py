"""Train one simple baseline on a fixed fold file and record it in an experiment ledger. Effects: reads data files and the ledger under --root; creates two prediction files and appends one ledger line.

Baselines: constant (the training mean), group_mean (the smoothed target mean of one column) and
ridge (ridge regression on numeric columns; for a binary target the ridge score becomes a
probability through a two-parameter logistic fit on the training rows). For each fold, the model
is fitted on the other folds, predicts the held-out fold (out-of-fold predictions) and predicts the
test set; the test prediction is the mean over the fold models. The constant baseline is always
scored beside it as a reference. There is no randomness, so a rerun gives the same numbers.

Usage:
  python3 -I -B train_baseline.py --train PATH --test PATH --folds PATH --id-column NAME
      --target-column NAME --task-type regression|binary --metric NAME --baseline NAME
      --features none|A,B --run-id ID --out-dir DIR --ledger PATH [--check-only] [--root DIR]

Exit status: 0 recorded or ready, 2 refused input. Standard output holds one JSON object.
No network use, no subprocess and no model call. MIT licence.
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
from pathlib import Path, PurePosixPath

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_FEATURES = 200
MAX_RIDGE_WORK = 60_000_000
RIDGE_ALPHA = 1.0
GROUP_SMOOTHING = 10.0
PROBABILITY_FLOOR = 1e-6
LOG_LOSS_CLIP = 1e-15
LOGISTIC_STEPS = 50
LOGISTIC_PENALTY = 1.0
TASK_METRICS = {"regression": ("rmse", "mae", "rmsle"), "binary": ("log_loss", "auc", "accuracy")}
DIRECTION = {"rmse": "minimize", "mae": "minimize", "rmsle": "minimize", "log_loss": "minimize",
             "auc": "maximize", "accuracy": "maximize"}
BASELINES = ("constant", "group_mean", "ridge")
MISSING = frozenset(("", "nan", "na", "null"))
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
RESERVED = frozenset(("fold", "prediction"))
#: ASCII decimal notation only, the rule of the submission assembly step. float() alone also reads 7_1 and
#: digits of other scripts, and str.isdigit() accepts a superscript two, which int() then refuses.
PLAIN_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
FOLD_NUMBER = re.compile(r"[0-9]{1,6}")


class Refused(Exception):
    """Input this script will not work on (exit status 2)."""


# Paths and files -----------------------------------------------------------------------------

def relative_path(value, label: str) -> str:
    """Return a clean workspace-relative POSIX path or refuse it."""
    if not isinstance(value, str) or not value.strip() or value.startswith(("/", "~")) or "\\" in value \
            or "\x00" in value:
        raise Refused(f"{label} must be a path relative to the workspace root, not {value!r}")
    parts = [part for part in PurePosixPath(value).parts if part != "."]
    if not parts or ".." in parts:
        raise Refused(f"{label} must stay inside the workspace root, not {value!r}")
    return "/".join(parts)


def inside(root: Path, relative: str, label: str) -> Path:
    """Join a relative path to the root, refusing symbolic links and any escape."""
    current = root
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise Refused(f"{label} passes through a symbolic link: {relative}")
    resolved = current.resolve()
    if resolved != root and root not in resolved.parents:
        raise Refused(f"{label} leaves the workspace root: {relative}")
    return current


def read_csv(root: Path, relative: str, label: str):
    path = inside(root, relative, label)
    if not path.is_file():
        raise Refused(f"{label} is not an existing regular file: {relative}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise Refused(f"{label} is larger than {MAX_FILE_BYTES} bytes; this script refuses instead of truncating")
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refused(f"{label} is not UTF-8 text (first bad byte at offset {error.start})") from None
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows = []
    try:
        header = next(reader, None)
        if not header or len(set(header)) != len(header):
            raise Refused(f"{label} needs a header row with distinct column names")
        for record in reader:
            if not record:
                continue
            if len(record) != len(header):
                raise Refused(f"{label}: data row {len(rows) + 1} has {len(record)} fields; the header has {len(header)}")
            rows.append(record)
    except csv.Error as error:
        raise Refused(f"{label} is not valid CSV near line {reader.line_num}: {error}") from None
    return header, rows, hashlib.sha256(data).hexdigest()


def number(text: str, where: str) -> float | None:
    """Parse a numeric cell; return None for a missing cell and refuse anything else."""
    stripped = text.strip()
    if stripped.casefold() in MISSING:
        return None
    if not PLAIN_NUMBER.fullmatch(stripped):
        raise Refused(f"{where}: {stripped[:40]!r} is not a number written with plain ASCII digits, such as 12, -0.5 "
                      f"or 1e-06")
    try:
        value = float(stripped)
    except ValueError:
        raise Refused(f"{where}: {stripped[:40]!r} is not a number") from None
    if not math.isfinite(value):
        raise Refused(f"{where}: {stripped[:40]!r} is not a finite number")
    return value


# Models ----------------------------------------------------------------------------------------

def sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def mean(values) -> float:
    values = list(values)
    return math.fsum(values) / len(values)


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a square linear system by Gaussian elimination with partial pivoting."""
    size = len(vector)
    rows = [matrix[index][:] + [vector[index]] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda index: abs(rows[index][column]))
        if abs(rows[pivot][column]) < 1e-12:
            raise Refused("the ridge system is singular; remove duplicate or constant features")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for index in range(column + 1, size):
            factor = rows[index][column] / rows[column][column]
            if factor:
                for position in range(column, size + 1):
                    rows[index][position] -= factor * rows[column][position]
    solution = [0.0] * size
    for index in range(size - 1, -1, -1):
        total = rows[index][size] - math.fsum(rows[index][position] * solution[position]
                                              for position in range(index + 1, size))
        solution[index] = total / rows[index][index]
    return solution


def fit_logistic(scores: list[float], labels: list[float]) -> tuple[float, float]:
    """Fit probability = sigmoid(slope * score + offset) by damped Newton steps on the penalized log loss.

    The fixed penalty on the slope keeps a fit on training rows from becoming overconfident.
    """
    rate = min(max(mean(labels), 1e-6), 1 - 1e-6)
    slope, offset = 0.0, math.log(rate / (1 - rate))

    def loss(a: float, b: float) -> float:
        total = 0.0
        for score, label in zip(scores, labels):
            probability = min(max(sigmoid(a * score + b), LOG_LOSS_CLIP), 1 - LOG_LOSS_CLIP)
            total -= label * math.log(probability) + (1 - label) * math.log(1 - probability)
        return total + LOGISTIC_PENALTY * a * a / 2

    current = loss(slope, offset)
    for _step in range(LOGISTIC_STEPS):
        grad_a = grad_b = hess_aa = hess_ab = hess_bb = 0.0
        for score, label in zip(scores, labels):
            probability = sigmoid(slope * score + offset)
            weight = probability * (1 - probability)
            grad_a += (probability - label) * score
            grad_b += probability - label
            hess_aa += weight * score * score
            hess_ab += weight * score
            hess_bb += weight
        grad_a += LOGISTIC_PENALTY * slope
        hess_aa += LOGISTIC_PENALTY
        hess_bb += 1e-9
        determinant = hess_aa * hess_bb - hess_ab * hess_ab
        if determinant <= 0:
            break
        step_a = (hess_bb * grad_a - hess_ab * grad_b) / determinant
        step_b = (hess_aa * grad_b - hess_ab * grad_a) / determinant
        scale, improved = 1.0, False
        while scale > 1e-4:
            trial_a, trial_b = slope - scale * step_a, offset - scale * step_b
            trial = loss(trial_a, trial_b)
            if trial <= current:
                improved = True
                break
            scale /= 2
        if not improved:
            break
        moved = abs(trial_a - slope) + abs(trial_b - offset)
        slope, offset, current = trial_a, trial_b, trial
        if moved < 1e-10:
            break
    return slope, offset


class Constant:
    def fit(self, rows, targets):
        self.value = mean(targets)
        return {}

    def predict(self, rows):
        return [self.value] * len(rows)


class GroupMean:
    def __init__(self, position: int) -> None:
        self.position = position

    def fit(self, rows, targets):
        self.overall = mean(targets)
        totals: dict[str, list] = {}
        for row, target in zip(rows, targets):
            totals.setdefault(row[self.position].strip(), []).append(target)
        self.levels = {level: (math.fsum(values) + GROUP_SMOOTHING * self.overall) / (len(values) + GROUP_SMOOTHING)
                       for level, values in totals.items()}
        return {}

    def predict(self, rows):
        return [self.levels.get(row[self.position].strip(), self.overall) for row in rows]


class Ridge:
    def __init__(self, positions: list[int], names: list[str], binary: bool) -> None:
        self.positions, self.names, self.binary = positions, names, binary

    def matrix(self, rows):
        return [[number(row[position], f"feature {name}") for position, name in zip(self.positions, self.names)]
                for row in rows]

    def standardize(self, raw):
        return [[((value if value is not None else center) - center) / spread
                 for value, center, spread in zip((row[index] for index in self.kept), self.centers, self.spreads)]
                for row in raw]

    def fit(self, rows, targets):
        raw = self.matrix(rows)
        self.kept, self.centers, self.spreads, dropped = [], [], [], []
        for index, name in enumerate(self.names):
            observed = [row[index] for row in raw if row[index] is not None]
            center = mean(observed) if observed else 0.0
            spread = math.sqrt(mean((value - center) ** 2 for value in observed)) if observed else 0.0
            if spread < 1e-12:
                dropped.append(name)
                continue
            self.kept.append(index)
            self.centers.append(center)
            self.spreads.append(spread)
        self.target_center = mean(targets)
        features = self.standardize(raw)
        size = len(self.kept)
        normal = [[RIDGE_ALPHA if row == column else 0.0 for column in range(size)] for row in range(size)]
        right = [0.0] * size
        for values, target in zip(features, targets):
            centered = target - self.target_center
            for row_index in range(size):
                value = values[row_index]
                if value == 0.0:
                    continue
                right[row_index] += value * centered
                normal_row = normal[row_index]
                for column_index in range(row_index, size):
                    normal_row[column_index] += value * values[column_index]
        for row_index in range(size):
            for column_index in range(row_index):
                normal[row_index][column_index] = normal[column_index][row_index]
        self.weights = solve(normal, right) if size else []
        if self.binary:
            self.slope, self.offset = fit_logistic(self.scores(features), targets)
        return {"dropped_features": dropped}

    def scores(self, features):
        return [self.target_center + math.fsum(weight * value for weight, value in zip(self.weights, row))
                for row in features]

    def predict(self, rows):
        scores = self.scores(self.standardize(self.matrix(rows)))
        if self.binary:
            return [sigmoid(self.slope * score + self.offset) for score in scores]
        return scores


# Metrics ---------------------------------------------------------------------------------------

def auc(truth: list[float], predicted: list[float]) -> float:
    order = sorted(range(len(truth)), key=lambda index: predicted[index])
    ranks = [0.0] * len(truth)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and predicted[order[end + 1]] == predicted[order[start]]:
            end += 1
        for position in range(start, end + 1):
            ranks[order[position]] = (start + end) / 2 + 1
        start = end + 1
    positives = sum(1 for value in truth if value == 1)
    negatives = len(truth) - positives
    rank_sum = math.fsum(rank for rank, value in zip(ranks, truth) if value == 1)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def score(metric: str, truth: list[float], predicted: list[float]) -> float:
    pairs = list(zip(truth, predicted))
    if metric == "rmse":
        return math.sqrt(mean((actual - guess) ** 2 for actual, guess in pairs))
    if metric == "mae":
        return mean(abs(actual - guess) for actual, guess in pairs)
    if metric == "rmsle":
        return math.sqrt(mean((math.log1p(max(guess, 0.0)) - math.log1p(actual)) ** 2 for actual, guess in pairs))
    if metric == "log_loss":
        clipped = [(actual, min(max(guess, LOG_LOSS_CLIP), 1 - LOG_LOSS_CLIP)) for actual, guess in pairs]
        return -mean(actual * math.log(guess) + (1 - actual) * math.log(1 - guess) for actual, guess in clipped)
    if metric == "accuracy":
        return mean(1.0 if (guess >= 0.5) == (actual == 1) else 0.0 for actual, guess in pairs)
    return auc(truth, predicted)


def worse(metric: str, first: float, second: float) -> bool:
    return first > second if DIRECTION[metric] == "minimize" else first < second


# Inputs ----------------------------------------------------------------------------------------

def feature_names(options) -> list[str]:
    if options.features == "none":
        names = []
    else:
        names = options.features.split(",")
        if any(not NAME.fullmatch(name) for name in names) or len(set(names)) != len(names):
            raise Refused("--features is none, or distinct column names separated by commas")
    wanted = {"constant": (0, 0), "group_mean": (1, 1), "ridge": (1, MAX_FEATURES)}[options.baseline]
    if not wanted[0] <= len(names) <= wanted[1]:
        raise Refused(f"the {options.baseline} baseline takes {wanted[0]} to {wanted[1]} feature columns, "
                      f"not {len(names)}")
    return names


def load(options, root: Path) -> dict:
    if options.metric not in TASK_METRICS[options.task_type]:
        raise Refused(f"the metric {options.metric} does not fit a {options.task_type} task; use one of "
                      f"{', '.join(TASK_METRICS[options.task_type])}")
    if not RUN_ID.fullmatch(options.run_id):
        raise Refused("--run-id uses letters, digits, dot, dash and underscore, at most 64 characters")
    identity, target = options.id_column, options.target_column
    if not NAME.fullmatch(identity) or not NAME.fullmatch(target) or identity == target \
            or {identity, target} & RESERVED:
        raise Refused("--id-column and --target-column are two different plain names, not fold or prediction")
    features = feature_names(options)
    if {identity, target} & set(features):
        raise Refused("the id and target columns cannot be features")
    paths = {name: relative_path(getattr(options, name), f"--{name}") for name in ("train", "test", "folds")}
    train_header, train_rows, train_digest = read_csv(root, paths["train"], "the training file")
    test_header, test_rows, test_digest = read_csv(root, paths["test"], "the test file")
    folds_header, fold_rows, folds_digest = read_csv(root, paths["folds"], "the fold file")
    for label, header, needed in (("training file", train_header, [identity, target, *features]),
                                  ("test file", test_header, [identity, *features])):
        missing = [name for name in needed if name not in header]
        if missing:
            raise Refused(f"the {label} lacks the columns {missing}")
    if target in test_header:
        raise Refused(f"the test file holds the target column {target!r}; check that the right files were given")
    if folds_header != [identity, "fold"]:
        raise Refused(f"the fold file header must be exactly {identity},fold")
    train_ids = [row[train_header.index(identity)].strip() for row in train_rows]
    test_ids = [row[test_header.index(identity)].strip() for row in test_rows]
    for label, ids in (("training", train_ids), ("test", test_ids)):
        if not ids or len(set(ids)) != len(ids) or "" in ids:
            raise Refused(f"the {label} ids must be present, nonempty and distinct")
    folds = {}
    for number_index, (fold_id, fold) in enumerate(fold_rows, start=1):
        fold_id, fold = fold_id.strip(), fold.strip()
        if not FOLD_NUMBER.fullmatch(fold) or fold_id in folds:
            raise Refused(f"fold file row {number_index}: the fold is a whole number of one to six ASCII digits, and "
                          f"each id appears once")
        folds[fold_id] = int(fold)
    if set(folds) != set(train_ids):
        extra, missing = sorted(set(folds) - set(train_ids))[:3], sorted(set(train_ids) - set(folds))[:3]
        raise Refused(f"the fold file must cover exactly the training ids; missing {missing}, unknown {extra}")
    fold_ids = sorted(set(folds.values()))
    if len(fold_ids) < 2:
        raise Refused("the fold file needs at least two folds")
    position = train_header.index(target)
    targets = []
    for index, row in enumerate(train_rows, start=1):
        text = row[position].strip()
        if options.task_type == "binary":
            if text not in ("0", "1"):
                raise Refused(f"training row {index}: a binary target is 0 or 1, not {text[:20]!r}")
            targets.append(float(text))
        else:
            value = number(text, f"training row {index} target")
            if value is None:
                raise Refused(f"training row {index}: the target is missing")
            if options.metric == "rmsle" and value < 0:
                raise Refused(f"training row {index}: rmsle needs targets of zero or more")
            targets.append(value)
    assignment = [folds[identity_value] for identity_value in train_ids]
    if options.task_type == "binary":
        if len(set(targets)) < 2:
            raise Refused("the binary target has only one class")
        for fold in fold_ids:
            held = {target_value for target_value, where in zip(targets, assignment) if where == fold}
            if options.metric == "auc" and len(held) < 2:
                raise Refused(f"fold {fold} holds one class only, so its AUC is undefined; use a stratified fold file")
    if options.baseline == "ridge":
        for label, header, rows in (("training", train_header, train_rows), ("test", test_header, test_rows)):
            for name in features:
                column = header.index(name)
                for index, row in enumerate(rows, start=1):
                    number(row[column], f"{label} row {index} feature {name}")
    largest_training_part = max(sum(1 for where in assignment if where != fold) for fold in fold_ids)
    if options.baseline == "ridge" and largest_training_part * (len(features) + 1) ** 2 > MAX_RIDGE_WORK:
        raise Refused("the ridge baseline is too large for this standard library script; use fewer features or "
                      "rows, or the constant or group_mean baseline")
    return {"paths": paths, "features": features, "targets": targets, "assignment": assignment, "fold_ids": fold_ids,
            "train": (train_header, train_rows, train_digest), "test": (test_header, test_rows, test_digest),
            "folds_digest": folds_digest, "train_ids": train_ids, "test_ids": test_ids}


def ledger_path(options, root: Path) -> tuple[str, Path]:
    relative = relative_path(options.ledger, "--ledger")
    path = inside(root, relative, "--ledger")
    if path.exists():
        if not path.is_file():
            raise Refused(f"the ledger {relative} is not a regular file")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise Refused(f"the ledger {relative} is larger than {MAX_FILE_BYTES} bytes")
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            raise Refused(f"the ledger {relative} is not UTF-8 text; it may be damaged") from None
        if text and not text.endswith("\n"):
            raise Refused(f"the ledger {relative} does not end with a line break; it may be damaged")
        for number_index, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                raise Refused(f"ledger line {number_index} is not JSON") from None
            if isinstance(entry, dict) and entry.get("run_id") == options.run_id:
                raise Refused(f"the run id {options.run_id} is already in the ledger; ask the host for a new run id")
    return relative, path


# Training ----------------------------------------------------------------------------------------

def make_model(kind: str, binary: bool, header: list[str], features: list[str]):
    if kind == "constant":
        return Constant()
    if kind == "group_mean":
        return GroupMean(header.index(features[0]))
    return Ridge([header.index(name) for name in features], features, binary)


def finish(options, values: list[float]) -> list[float]:
    """Turn model outputs into predictions on the scale of the target."""
    if options.metric == "rmsle":
        return [max(math.expm1(value), 0.0) for value in values]
    if options.task_type == "binary":
        return [min(max(value, PROBABILITY_FLOOR), 1 - PROBABILITY_FLOOR) for value in values]
    return values


def aligned_test_rows(train_header: list[str], test_header: list[str], test_rows: list) -> list:
    """Test rows in the training column order; a column the test file lacks, such as the target, stays empty."""
    if train_header == test_header:
        return test_rows
    where = [test_header.index(name) if name in test_header else None for name in train_header]
    return [[row[index] if index is not None else "" for index in where] for row in test_rows]


def cross_validate(options, data: dict, kind: str) -> dict:
    train_header, train_rows, _digest = data["train"]
    test_header, test_rows, _test_digest = data["test"]
    fitted_targets = [math.log1p(value) for value in data["targets"]] if options.metric == "rmsle" else data["targets"]
    test_model_rows = aligned_test_rows(train_header, test_header, test_rows)
    oof = [0.0] * len(train_rows)
    test_sum = [0.0] * len(test_rows)
    scores, dropped = [], {}
    for fold in data["fold_ids"]:
        fit_index = [index for index, where in enumerate(data["assignment"]) if where != fold]
        held_index = [index for index, where in enumerate(data["assignment"]) if where == fold]
        model = make_model(kind, options.task_type == "binary", train_header, data["features"])
        details = model.fit([train_rows[index] for index in fit_index], [fitted_targets[index] for index in fit_index])
        if details.get("dropped_features"):
            dropped[str(fold)] = details["dropped_features"]
        held_predictions = finish(options, model.predict([train_rows[index] for index in held_index]))
        for index, prediction in zip(held_index, held_predictions):
            oof[index] = prediction
        for index, prediction in enumerate(finish(options, model.predict(test_model_rows))):
            test_sum[index] += prediction
        scores.append(score(options.metric, [data["targets"][index] for index in held_index], held_predictions))
    return {"oof": oof, "test": [value / len(data["fold_ids"]) for value in test_sum], "scores": scores,
            "dropped": dropped}


def summary_of(scores: list[float]) -> tuple[float, float]:
    center = mean(scores)
    return round(center, 10), round(math.sqrt(mean((value - center) ** 2 for value in scores)), 10)


def flags_for(options, data: dict, center: float, reference_center: float) -> list[str]:
    """Signals for a person, from declared thresholds; a flag is a reason to look, not a verdict."""
    flags = []
    if options.baseline != "constant" and worse(options.metric, center, reference_center):
        flags.append("worse_than_constant")
    if options.task_type == "binary":
        perfect = {"auc": center >= 0.9999, "accuracy": center >= 0.9999, "log_loss": center <= 0.001}[options.metric]
    else:
        values = [math.log1p(value) for value in data["targets"]] if options.metric == "rmsle" else data["targets"]
        spread = math.sqrt(mean((value - mean(values)) ** 2 for value in values))
        perfect = spread > 0 and center <= 1e-3 * spread
    if perfect:
        flags.append("suspiciously_perfect")
    return flags


def write_csv(path: Path, header: list[str], rows) -> str:
    with open(path, "x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(options) -> tuple[dict, int]:
    root = Path(options.root).resolve()
    data = load(options, root)
    ledger_rel, ledger = ledger_path(options, root)
    out_rel = relative_path(options.out_dir, "--out-dir")
    out_dir = inside(root, out_rel, "--out-dir")
    if out_dir.exists() and not out_dir.is_dir():
        raise Refused(f"--out-dir {out_rel} exists and is not a folder")
    names = {"oof": f"{options.run_id}.oof.csv", "test_predictions": f"{options.run_id}.test.csv"}
    for name in names.values():
        if (out_dir / name).exists() or (out_dir / name).is_symlink():
            raise Refused(f"{out_rel}/{name} already exists; this step never overwrites")
    train_header, train_rows, train_digest = data["train"]
    test_header, test_rows, test_digest = data["test"]
    if options.check_only:
        return {"status": "ready", "train_rows": len(train_rows), "test_rows": len(test_rows),
                "folds": data["fold_ids"], "features": data["features"],
                "will_write": [f"{out_rel}/{name}" for name in names.values()], "will_append_to": ledger_rel}, 0
    # Every number is computed before any file is written, so a failed calculation leaves no partial output.
    try:
        result = cross_validate(options, data, options.baseline)
        reference = cross_validate(options, data, "constant")
        center, spread = summary_of(result["scores"])
        reference_center, _reference_spread = summary_of(reference["scores"])
        flags = flags_for(options, data, center, reference_center)
    except ArithmeticError as error:
        raise Refused(f"a calculation failed on this data ({type(error).__name__}: {error}); check the target and "
                      f"feature columns for extreme values") from None
    computed = [*result["oof"], *result["test"], *result["scores"], *reference["scores"], center, spread,
                reference_center]
    if not all(math.isfinite(value) for value in computed):
        raise Refused("the baseline produced a prediction or score that is not a finite number; check the target and "
                      "feature columns for extreme values")
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    target_position = train_header.index(options.target_column)
    oof_digest = write_csv(out_dir / names["oof"], [options.id_column, "fold", options.target_column, "prediction"],
                           ([identity, fold, row[target_position].strip(), repr(round(prediction, 10))]
                            for identity, fold, row, prediction in zip(data["train_ids"], data["assignment"], train_rows,
                                                                       result["oof"])))
    test_digest_out = write_csv(out_dir / names["test_predictions"], [options.id_column, "prediction"],
                                ([identity, repr(round(prediction, 10))]
                                 for identity, prediction in zip(data["test_ids"], result["test"])))
    rows_per_fold = {str(fold): data["assignment"].count(fold) for fold in data["fold_ids"]}
    record = {
        "record_type": "experiment_record/v1", "run_id": options.run_id, "step": "baseline_training",
        "task_type": options.task_type, "id_column": options.id_column, "target_column": options.target_column,
        "metric": {"name": options.metric, "direction": DIRECTION[options.metric]},
        "model": {"baseline": options.baseline, "features": data["features"],
                  "parameters": {"ridge_alpha": RIDGE_ALPHA, "group_smoothing": GROUP_SMOOTHING,
                                 "logistic_slope_penalty": LOGISTIC_PENALTY},
                  "target_transform": "log1p" if options.metric == "rmsle" else "none",
                  "probability": "logistic_fit_on_training_scores"
                  if options.baseline == "ridge" and options.task_type == "binary" else "none",
                  "dropped_features": result["dropped"]},
        "folds": {"path": data["paths"]["folds"], "sha256": data["folds_digest"], "count": len(data["fold_ids"]),
                  "rows_per_fold": rows_per_fold},
        "data": {"train": {"path": data["paths"]["train"], "sha256": train_digest, "rows": len(train_rows)},
                 "test": {"path": data["paths"]["test"], "sha256": test_digest, "rows": len(test_rows)}},
        "fold_scores": [round(value, 10) for value in result["scores"]], "mean_score": center, "std_score": spread,
        "reference_constant": {"fold_scores": [round(value, 10) for value in reference["scores"]],
                               "mean_score": reference_center},
        "flags": flags,
        "outputs": {"oof": {"path": f"{out_rel}/{names['oof']}", "sha256": oof_digest, "rows": len(train_rows)},
                    "test_predictions": {"path": f"{out_rel}/{names['test_predictions']}", "sha256": test_digest_out,
                                         "rows": len(test_rows)}},
        "test_prediction_rule": "mean_of_fold_models",
        "script": {"name": Path(__file__).name, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    with open(ledger, "a", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"status": "recorded", "ledger": ledger_rel, "record": record}, 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Train one baseline on fixed folds and record it in a ledger.")
    for name in ("--train", "--test", "--folds", "--id-column", "--target-column", "--features", "--run-id",
                 "--out-dir", "--ledger"):
        parser.add_argument(name, required=True)
    parser.add_argument("--task-type", required=True, choices=sorted(TASK_METRICS))
    parser.add_argument("--metric", required=True, choices=sorted(DIRECTION))
    parser.add_argument("--baseline", required=True, choices=BASELINES)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--root", default=".")
    try:
        options = parser.parse_args(argv)
    except SystemExit as error:
        if error.code == 0:
            return 0
        print(json.dumps({"status": "refused", "reason": "the command line is invalid; see standard error"}))
        return 2
    try:
        result, code = run(options)
    except Refused as error:
        result, code = {"status": "refused", "reason": str(error)}, 2
    except OSError as error:
        result, code = {"status": "refused", "reason": f"file system error: {error}"}, 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
