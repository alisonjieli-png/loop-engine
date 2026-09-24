"""Assemble a submission file from one recorded run and check it against the sample submission. Effects: reads the ledger, prediction, test and sample files under --root; creates two new files in --out-dir. It uploads nothing.

The run is chosen by its run id; this script never picks a run. It finds the run's line in the
experiment ledger, confirms that the test predictions and the test data still have the digests
recorded there, and writes the predictions in the exact header and row order of the sample
submission. After a self-check it writes a provenance record naming the run, the ledger line and
every file digest. With --check-only it validates everything and writes nothing.

Usage:
  python3 -I -B assemble_submission.py --sample PATH --ledger PATH --run-id ID --id-column NAME
      --value-type probability|real_number|binary_label --out-dir DIR [--check-only] [--root DIR]

Exit status: 0 assembled or ready, 1 the self-check failed, 2 refused input. Standard output holds
one JSON object. No network use, no subprocess and no model call. MIT licence.
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
VALUE_TYPES = ("probability", "real_number", "binary_label")
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
DIGEST = re.compile(r"[0-9a-f]{64}")
#: ASCII decimal notation only. Python's float() also reads "1_0" and non-ASCII digits, which platforms may refuse.
PLAIN_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


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


def existing_bytes(root: Path, relative: str, label: str) -> bytes:
    path = inside(root, relative, label)
    if not path.is_file():
        raise Refused(f"{label} is not an existing regular file: {relative}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise Refused(f"{label} is larger than {MAX_FILE_BYTES} bytes; this script refuses instead of truncating")
    return path.read_bytes()


def parse_csv(data: bytes, label: str) -> tuple[list[str], list[list[str]]]:
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
    return header, rows


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Ledger ----------------------------------------------------------------------------------------

def find_run(root: Path, ledger_rel: str, run_id: str) -> tuple[dict, int, str]:
    data = existing_bytes(root, ledger_rel, "the ledger")
    found = []
    for number, raw in enumerate(data.split(b"\n"), start=1):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError:
            raise Refused(f"ledger line {number} is not UTF-8 text; the ledger may be damaged") from None
        except ValueError:
            raise Refused(f"ledger line {number} is not JSON; the ledger may be damaged") from None
        if isinstance(entry, dict) and entry.get("run_id") == run_id:
            found.append((entry, number, sha256(raw)))
    if not found:
        raise Refused(f"the run id {run_id} is not in the ledger {ledger_rel}")
    if len(found) > 1:
        raise Refused(f"the run id {run_id} appears {len(found)} times in the ledger; ask which line is meant")
    entry, number, digest = found[0]
    try:
        predictions = entry["outputs"]["test_predictions"]
        test = entry["data"]["test"]
        wanted = (entry["record_type"], predictions["path"], predictions["sha256"], test["path"], test["sha256"])
    except (KeyError, TypeError):
        raise Refused(f"ledger line {number} lacks outputs.test_predictions or data.test; it is not a usable run record") from None
    if wanted[0] != "experiment_record/v1" or not all(isinstance(value, str) for value in wanted) \
            or not DIGEST.fullmatch(wanted[2]) or not DIGEST.fullmatch(wanted[4]):
        raise Refused(f"ledger line {number} is not an experiment_record/v1 with file digests")
    return entry, number, digest


# Assembly ----------------------------------------------------------------------------------------

def convert(value_text: str, value_type: str, identity: str) -> str:
    if not PLAIN_NUMBER.fullmatch(value_text.strip()):
        raise Refused(f"the prediction for id {identity!r} is not a plain decimal number: {value_text[:40]!r}")
    try:
        value = float(value_text.strip())
    except ValueError:
        raise Refused(f"the prediction for id {identity!r} is not a number: {value_text[:40]!r}") from None
    if not math.isfinite(value):
        raise Refused(f"the prediction for id {identity!r} is not a finite number")
    if value_type == "probability":
        if not 0.0 <= value <= 1.0:
            raise Refused(f"the prediction for id {identity!r} is {value}, outside 0 to 1, so it is not a probability")
        return value_text.strip()
    if value_type == "binary_label":
        return "1" if value >= 0.5 else "0"
    return value_text.strip()


def verify(submission: bytes, sample_header: list[str], sample_ids: list[str], id_position: int,
           value_position: int, value_type: str) -> dict:
    """Re-read the written file and compare it with the sample; every check must be true."""
    try:
        header, rows = parse_csv(submission, "the submission")
    except Refused:
        return {"header_matches_sample": False, "ids_match_sample_order": False, "row_count_matches": False,
                "values_valid": False}
    valid = True
    for row in rows:
        try:
            value = float(row[value_position])
        except (ValueError, IndexError):
            valid = False
            break
        if not PLAIN_NUMBER.fullmatch(row[value_position]) or not math.isfinite(value) \
                or (value_type == "probability" and not 0.0 <= value <= 1.0) \
                or (value_type == "binary_label" and row[value_position] not in ("0", "1")):
            valid = False
            break
    return {"header_matches_sample": header == sample_header,
            "ids_match_sample_order": [row[id_position] for row in rows] == sample_ids,
            "row_count_matches": len(rows) == len(sample_ids), "values_valid": valid}


def run(options) -> tuple[dict, int]:
    root = Path(options.root).resolve()
    if not RUN_ID.fullmatch(options.run_id):
        raise Refused("--run-id uses letters, digits, dot, dash and underscore, at most 64 characters")
    if not NAME.fullmatch(options.id_column):
        raise Refused("--id-column is a plain column name")
    sample_rel = relative_path(options.sample, "--sample")
    ledger_rel = relative_path(options.ledger, "--ledger")
    out_rel = relative_path(options.out_dir, "--out-dir")
    entry, line_number, line_digest = find_run(root, ledger_rel, options.run_id)
    predictions_rel = relative_path(entry["outputs"]["test_predictions"]["path"], "the recorded predictions path")
    test_rel = relative_path(entry["data"]["test"]["path"], "the recorded test data path")
    predictions_data = existing_bytes(root, predictions_rel, "the recorded predictions")
    if sha256(predictions_data) != entry["outputs"]["test_predictions"]["sha256"]:
        raise Refused(f"{predictions_rel} changed after the run was recorded; its digest differs from the ledger")
    test_data = existing_bytes(root, test_rel, "the recorded test data")
    if sha256(test_data) != entry["data"]["test"]["sha256"]:
        raise Refused(f"{test_rel} changed after the run was recorded, so the predictions may not fit it")
    sample_data = existing_bytes(root, sample_rel, "the sample submission")
    sample_header, sample_rows = parse_csv(sample_data, "the sample submission")
    if options.id_column not in sample_header:
        raise Refused(f"the sample submission has no column {options.id_column!r}")
    if len(sample_header) != 2:
        raise Refused(f"the sample submission has the columns {sample_header}; this step handles one id column and "
                      f"one prediction column only")
    id_position = sample_header.index(options.id_column)
    value_position = 1 - id_position
    sample_ids = [row[id_position].strip() for row in sample_rows]
    if not sample_ids or "" in sample_ids or len(set(sample_ids)) != len(sample_ids):
        raise Refused("the sample submission ids must be present, nonempty and distinct")
    prediction_header, prediction_rows = parse_csv(predictions_data, "the recorded predictions")
    if prediction_header != [options.id_column, "prediction"]:
        raise Refused(f"the recorded predictions must have the header {options.id_column},prediction")
    predicted = {}
    for identity, value in prediction_rows:
        identity = identity.strip()
        if identity in predicted:
            raise Refused(f"the recorded predictions name the id {identity!r} twice")
        predicted[identity] = value
    missing = [identity for identity in sample_ids if identity not in predicted]
    extra = sorted(set(predicted) - set(sample_ids))
    if missing or extra:
        raise Refused(f"the prediction ids differ from the sample ids; missing {missing[:3]}, not in the sample {extra[:3]}")
    values = [convert(predicted[identity], options.value_type, identity) for identity in sample_ids]
    out_dir = inside(root, out_rel, "--out-dir")
    if out_dir.exists() and not out_dir.is_dir():
        raise Refused(f"--out-dir {out_rel} exists and is not a folder")
    names = {"submission": f"{options.run_id}.submission.csv", "record": f"{options.run_id}.submission_record.json"}
    for name in names.values():
        if (out_dir / name).exists() or (out_dir / name).is_symlink():
            raise Refused(f"{out_rel}/{name} already exists; this step never overwrites")
    if options.check_only:
        return {"status": "ready", "run_id": options.run_id, "ledger_line": line_number,
                "prediction_column": sample_header[value_position], "rows": len(sample_ids),
                "run_flags": entry.get("flags", []), "will_write": [f"{out_rel}/{name}" for name in names.values()]}, 0
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(sample_header)
    for identity, value in zip(sample_ids, values):
        row = ["", ""]
        row[id_position], row[value_position] = identity, value
        writer.writerow(row)
    submission = buffer.getvalue().encode("utf-8")
    checks = verify(submission, sample_header, sample_ids, id_position, value_position, options.value_type)
    if not all(checks.values()):
        return {"status": "self_check_failed", "checks": checks, "note": "Nothing was written."}, 1
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / names["submission"], "xb") as stream:
        stream.write(submission)
    record = {
        "record_type": "submission_record/v1", "status": "assembled", "run_id": options.run_id,
        "ledger": {"path": ledger_rel, "line": line_number, "line_sha256": line_digest},
        "cross_validation": {"metric": entry.get("metric"), "fold_scores": entry.get("fold_scores"),
                             "mean_score": entry.get("mean_score")},
        "run_flags": entry.get("flags", []),
        "predictions": {"path": predictions_rel, "sha256": sha256(predictions_data), "rows": len(prediction_rows)},
        "test_data": {"path": test_rel, "sha256": sha256(test_data)},
        "sample": {"path": sample_rel, "sha256": sha256(sample_data), "rows": len(sample_ids), "header": sample_header},
        "submission": {"path": f"{out_rel}/{names['submission']}", "sha256": sha256(submission), "rows": len(sample_ids),
                       "prediction_column": sample_header[value_position], "value_type": options.value_type},
        "checks": checks, "upload": "not_uploaded"}
    with open(out_dir / names["record"], "x", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    return record, 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Assemble and check a submission file from one recorded run.")
    for name in ("--sample", "--ledger", "--run-id", "--id-column", "--out-dir"):
        parser.add_argument(name, required=True)
    parser.add_argument("--value-type", required=True, choices=VALUE_TYPES)
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
