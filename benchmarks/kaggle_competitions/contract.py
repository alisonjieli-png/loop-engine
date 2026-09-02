"""The submission contract of a competition, read independently of any solve.

This is the grading rubric, not an input. The Practitioner is told nothing
here: it must discover the target, the identifier, the task type and the
output contract from the supplied files, which is the whole point of running
several competitions rather than one. This module reads the same files and
states what the answer was, so a run can be graded on whether it discovered
the contract rather than only on whether it emitted a file.

Reading it independently matters because the obvious rule is wrong. In
`playground-series-s6e7` the target `health_condition` is the second of
fifteen train columns, and the last train column, `gender`, is a feature that
also appears in test. Anything that takes the final column as the target gets
a feature, trains on the wrong thing, and can still produce a submission of
exactly the right shape.

The rule used here is the one the data supports: the target is the column
present in the training file and absent from the prediction file, confirmed
against the column the sample submission asks for.

Owns:
    - CompetitionContract and read_contract(): the independent reading.
    - grade_discovery(): compare a run's discovered contract to it.

Does not own: the solve, the submission reading (loop_engine.kaggle_report),
or competition download.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

CONTRACT_RECORD_TYPE = "competition_contract/v1"
_SAMPLE_ROWS = 4000


class CompetitionContractError(ValueError):
    """A competition directory did not hold a readable contract."""


def _header_and_sample(path: str, column: "int | None" = None) -> tuple:
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        header = next(reader, None) or []
        values = []
        if column is not None and 0 <= column < len(header):
            for index, row in enumerate(reader):
                if index >= _SAMPLE_ROWS:
                    break
                if column < len(row):
                    values.append(row[column])
        return header, values


def _numeric(values) -> bool:
    seen = False
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        seen = True
        try:
            float(text)
        except ValueError:
            return False
    return seen


@dataclass(frozen=True)
class CompetitionContract:
    """What the files say the answer must look like."""

    competition: str
    identifier: str
    target: str
    target_position_in_train: int
    train_columns: tuple
    test_columns: tuple
    submission_columns: tuple
    distinct_target_values: int
    target_is_numeric: bool
    target_has_blanks: bool
    submission_value_is_numeric: bool
    submission_rows: int
    task_shape: str
    trap: str

    def to_dict(self) -> dict:
        value = {"record_type": CONTRACT_RECORD_TYPE}
        value.update(self.__dict__)
        for key in ("train_columns", "test_columns", "submission_columns"):
            value[key] = list(value[key])
        return value


def read_contract(directory: str, competition: str = "") -> CompetitionContract:
    """State the contract the supplied files establish."""
    name = competition or os.path.basename(os.path.normpath(directory))
    paths = {stem: os.path.join(directory, f"{stem}.csv")
             for stem in ("train", "test", "sample_submission")}
    missing = [stem for stem, path in paths.items() if not os.path.isfile(path)]
    if missing:
        raise CompetitionContractError(
            f"{name}: no {missing} under {directory}")
    train_columns, _ = _header_and_sample(paths["train"])
    test_columns, _ = _header_and_sample(paths["test"])
    submission_columns, _ = _header_and_sample(paths["sample_submission"])
    if len(submission_columns) < 2:
        raise CompetitionContractError(
            f"{name}: the sample submission has no prediction column")
    identifier = submission_columns[0]
    asked_for = submission_columns[-1]

    # The target is what training has and prediction does not. The sample
    # submission confirms it; where they disagree the submission wins,
    # because that is the file the grader reads.
    only_in_train = [column for column in train_columns
                     if column not in set(test_columns)]
    target = asked_for if asked_for in only_in_train else (
        only_in_train[0] if only_in_train else asked_for)
    position = (train_columns.index(target)
                if target in train_columns else -1)
    _header, values = _header_and_sample(paths["train"], position)
    distinct = len({value for value in values})
    blanks = any(not str(value).strip() for value in values)
    numeric = _numeric(values)
    _sub_header, sub_values = _header_and_sample(
        paths["sample_submission"], len(submission_columns) - 1)
    submission_numeric = _numeric(sub_values)
    with open(paths["sample_submission"], encoding="utf-8",
              errors="replace") as handle:
        submission_rows = max(0, sum(1 for _ in handle) - 1)

    non_blank = distinct - (1 if blanks else 0)
    if non_blank == 2:
        shape = "binary classification"
    elif 2 < non_blank <= 40 and not numeric:
        shape = "multiclass classification"
    elif numeric and distinct > 40:
        shape = "regression"
    else:
        shape = "classification"

    traps = []
    if position not in (-1, len(train_columns) - 1):
        traps.append(
            f"the target is column {position + 1} of {len(train_columns)} in "
            f"train, not the last; the last column "
            f"{train_columns[-1]!r} is a feature that also appears in test")
    if blanks:
        traps.append("the target column contains blank values")
    if submission_numeric and not numeric:
        traps.append("training labels are text but the submission asks for a "
                     "number")
    if numeric and not submission_numeric:
        traps.append("training labels are numeric but the submission asks for "
                     "text")
    # A sample submission whose value is not one the target ever takes is
    # asking for something other than a label. A constant 0.709 against a
    # target of 0 and 1 is a probability, and a pipeline that emits labels
    # produces a perfectly well-formed submission that scores badly.
    # Compared as values, not as text: a target of "0.0" and a sample of "0"
    # are the same label written twice, and reporting that as a trap would
    # send a reader looking for a defect that is not there.
    def _key(value):
        text = str(value).strip()
        try:
            return float(text)
        except ValueError:
            return text

    label_values = {_key(value) for value in values if str(value).strip()}
    sample_values = {_key(value) for value in sub_values
                     if str(value).strip()}
    outside = sorted((str(value) for value in sample_values - label_values),
                     key=str)[:3]
    if shape != "regression" and outside:
        traps.append(
            f"the sample submission holds {outside}, which the target never "
            "takes; the contract asks for a score rather than a label")

    return CompetitionContract(
        competition=name, identifier=identifier, target=target,
        target_position_in_train=position,
        train_columns=tuple(train_columns), test_columns=tuple(test_columns),
        submission_columns=tuple(submission_columns),
        distinct_target_values=distinct, target_is_numeric=numeric,
        target_has_blanks=blanks,
        submission_value_is_numeric=submission_numeric,
        submission_rows=submission_rows, task_shape=shape,
        trap="; ".join(traps))


def grade_discovery(contract: CompetitionContract, discovered: dict) -> dict:
    """Grade what a run discovered against what the files establish.

    A run is graded on the contract it found, separately from whether it
    produced a file. A run that identified the right target and failed to
    execute has shown something different from one that produced a
    well-formed submission for the wrong column.
    """
    found_target = str((discovered or {}).get("target") or "").strip()
    found_id = str((discovered or {}).get("identifier") or "").strip()
    found_shape = str((discovered or {}).get("task_type") or "").strip().lower()
    shape_words = set(contract.task_shape.lower().split())
    return {
        "record_type": "contract_discovery_grade/v1",
        "competition": contract.competition,
        "expected_target": contract.target,
        "found_target": found_target or None,
        "target_correct": found_target == contract.target,
        "expected_identifier": contract.identifier,
        "found_identifier": found_id or None,
        "identifier_correct": found_id == contract.identifier,
        "expected_shape": contract.task_shape,
        "found_shape": found_shape or None,
        "shape_consistent": bool(
            found_shape and shape_words & set(found_shape.split())),
        "trap": contract.trap,
    }
