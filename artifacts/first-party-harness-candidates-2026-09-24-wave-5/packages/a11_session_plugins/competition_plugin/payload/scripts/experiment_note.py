"""Effects: reads one note draft on standard input, the brief, the notes file and an optional submission file; appends one line to .baltor/state/competition-plugin/experiments.jsonl.

Records one finished experiment. The script computes the cross-validation
mean and the population standard deviation from the fold scores itself; a
draft that carries its own mean is refused. It checks the draft against the
competition brief (metric name, fold count, data version), refuses a reused
experiment id, and records the SHA-256 of the submission file when one is
named, so the pre-submission gate can link that exact file to this note.

Draft fields: experiment_id, hypothesis, change, metric, fold_scores, seed,
data_version, code_revision; optional submission_file and outcome_note.

Exit status: 0 recorded, 1 the draft breaks a rule (nothing written),
2 the draft or the brief cannot be read (nothing written).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import math
import re
import statistics
import sys
from pathlib import Path

REQUIRED = {"experiment_id", "hypothesis", "change", "metric", "fold_scores", "seed", "data_version", "code_revision"}
OPTIONAL = {"submission_file", "outcome_note"}
EXPERIMENT_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
REVISION = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
MAX_DRAFT_BYTES = 64 * 1024
MAX_SUBMISSION_BYTES = 512 * 1024 * 1024


def load_reader():
    spec = importlib.util.spec_from_file_location("competition_brief_summary", Path(__file__).resolve().with_name("brief_summary.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shape_problems(draft) -> list[str]:
    if not isinstance(draft, dict):
        return ["draft_is_not_an_object"]
    missing, extra = sorted(REQUIRED - set(draft)), sorted(set(draft) - REQUIRED - OPTIONAL)
    if missing or extra:
        hint = " (the script computes cv_mean and cv_std; do not send them)" if {"cv_mean", "cv_std"} & set(extra) else ""
        return [f"draft_fields_differ: missing {missing}, extra {extra}{hint}"]
    problems = []
    if not isinstance(draft["experiment_id"], str) or not EXPERIMENT_ID.match(draft["experiment_id"]):
        problems.append("experiment_id_invalid: lower case letters, digits, dot, dash and underscore")
    for field, high in (("hypothesis", 300), ("change", 300), ("metric", 40), ("data_version", 80)):
        value = draft[field]
        if not isinstance(value, str) or not 1 <= len(value) <= high or any(ord(character) < 32 for character in value):
            problems.append(f"{field}_invalid")
    scores = draft["fold_scores"]
    if not isinstance(scores, list) or not 1 <= len(scores) <= 50 or any(
            isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) for score in scores):
        problems.append("fold_scores_invalid: a list of 1 to 50 finite numbers, one per fold, in fold order")
    if type(draft["seed"]) is not int:
        problems.append("seed_invalid")
    if not isinstance(draft["code_revision"], str) or not REVISION.match(draft["code_revision"]):
        problems.append("code_revision_invalid")
    if "outcome_note" in draft and (not isinstance(draft["outcome_note"], str) or len(draft["outcome_note"]) > 300):
        problems.append("outcome_note_invalid")
    if "submission_file" in draft and not isinstance(draft["submission_file"], str):
        problems.append("submission_file_invalid")
    return problems


def file_digest(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            if size > MAX_SUBMISSION_BYTES:
                raise OverflowError("submission file too large")
            digest.update(block)
    return digest.hexdigest(), size


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Record one competition experiment from a draft on standard input.")
    parser.add_argument("--root", help="workspace root; default CLAUDE_PROJECT_DIR, GEMINI_PROJECT_DIR or the current folder")
    options = parser.parse_args(argv)
    reader = load_reader()
    root = reader.workspace_root(options.root)
    try:
        raw = sys.stdin.buffer.read(MAX_DRAFT_BYTES + 1)
        if len(raw) > MAX_DRAFT_BYTES:
            raise reader.Refused("draft_too_large")
        draft = reader.strict_json(raw)
        brief = reader.load_brief(root)
        notes, _unreadable = reader.load_notes(root)
    except reader.Refused as error:
        print(json.dumps({"recorded": False, "error": error.code, "detail": error.detail}))
        return 2
    problems = shape_problems(draft)
    if problems:
        print(json.dumps({"recorded": False, "error": "draft_refused", "problems": problems}))
        return 2
    failures = []
    if draft["metric"] != brief["metric"]["name"]:
        failures.append("metric_differs_from_brief")
    if len(draft["fold_scores"]) != brief["validation"]["folds"]:
        failures.append("fold_count_differs_from_brief")
    if draft["data_version"] != brief["data_version"]:
        failures.append("data_version_differs_from_brief")
    if any(note["experiment_id"] == draft["experiment_id"] for note in notes):
        failures.append("experiment_id_already_recorded")
    submission_sha256, submission_bytes = None, None
    if "submission_file" in draft:
        try:
            path = reader.confined(root, draft["submission_file"])
            if path.is_symlink() or not path.is_file():
                failures.append("submission_file_missing")
            else:
                submission_sha256, submission_bytes = file_digest(path)
        except reader.Refused:
            failures.append("submission_file_path_unsafe")
        except OverflowError:
            failures.append("submission_file_too_large")
    if failures:
        print(json.dumps({"recorded": False, "experiment_id": draft["experiment_id"], "failures": failures}))
        return 1
    scores = [float(score) for score in draft["fold_scores"]]
    note = {"record_type": reader.NOTE_TYPE, **draft, "direction": brief["metric"]["direction"],
            "fold_count": len(scores), "cv_mean": statistics.fmean(scores), "cv_std": statistics.pstdev(scores),
            "submission_sha256": submission_sha256, "submission_bytes": submission_bytes,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        target = reader.confined(root, reader.NOTES)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            raise reader.Refused("notes_file_invalid", "symbolic link")
    except reader.Refused as error:
        print(json.dumps({"recorded": False, "error": error.code, "detail": error.detail}))
        return 2
    with open(target, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(note, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"recorded": True, "experiment_id": note["experiment_id"], "metric": note["metric"],
                      "direction": note["direction"], "cv_mean": note["cv_mean"], "cv_std": note["cv_std"],
                      "fold_count": note["fold_count"], "notes_total": len(notes) + 1,
                      "submission_sha256": submission_sha256, "path": reader.NOTES}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
