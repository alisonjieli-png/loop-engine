"""Run the repository operation behind each approved item on every row, with no model.

Every approved item in the material names the repository source it was
compiled from. This script runs that source operation on each input row, with
the item's own defaults and the thresholds of the approved item
`apply_hold_or_escalate_each_correction` (apply at or above 0.9; anything else
that would change a value keeps the input and sets `review` to yes), writes
the result as an output file and scores it with the study's scorer.

It answers two questions before any counted model call:

- Coverage: on which rows does the item's own method give the frozen truth,
  and on which rows does it give a different answer? The labels come from
  running code, not from a reading of the item text.
- Reference: how far does the reusable code behind the items go with no
  model at all? This is a reference line, not an arm of the study, and it is
  not a result of Baltor material: the items are Markdown methods, and the
  code itself is not served with them.

Two choices are this study's, not the items': for addresses, which name no
thresholds, a result below the escalation threshold 0.6 or with an unplaced
remainder is sent to review; for duplicates, the item's `duplicate` outcome
is written as `same` and its `possible` outcome as `review`.

    PYTHONPATH=src python case-studies/overnight-cheap-model-with-and-without-baltor/runner/item_reference.py
    ... --check    # exit 1 when a written file differs

Needs the repository source on the import path and PyYAML, which the packaged
catalogs of the capitalisation operation are read with.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
POPULATION = STUDY / "population"
OUT_FOLDER = POPULATION / "item-reference"
OUT_RECORD = POPULATION / "item-reference.json"
sys.path.insert(0, str(STUDY / "scorer"))

import score_step  # noqa: E402

APPLY_AT_OR_ABOVE = 0.9
ESCALATE_BELOW = 0.6
ADDRESS_PARTS = ("house_number", "street", "unit", "city", "region", "postal_code", "country")


def operations():
    from loop_engine.code_nodes import text_conformance_operations as ops
    from loop_engine.code_nodes.address_components import extract_components
    from loop_engine.code_nodes.duplicate_detection import (
        DuplicateFieldSpec, DuplicatePolicy, find_duplicates)
    from loop_engine.code_nodes.field_recovery import recover_email
    from loop_engine.code_nodes.text_conformance import load_packaged_catalogs, merge_layers
    catalogs = merge_layers([load_packaged_catalogs()])
    return {
        "ops": ops, "catalogs": catalogs, "extract_components": extract_components,
        "recover_email": recover_email, "find_duplicates": find_duplicates,
        "DuplicateFieldSpec": DuplicateFieldSpec, "DuplicatePolicy": DuplicatePolicy,
    }


def decide(ops, value, result):
    """(value, review) written by the method under the declared thresholds."""
    outcome = ops.classify(result["confidence"], result["changed"], APPLY_AT_OR_ABOVE,
                           ESCALATE_BELOW)
    if outcome == "applied":
        return result["output"], "no", outcome
    if outcome == "unchanged":
        return value, "no", outcome
    return value, "yes", outcome


def value_family(family, rows, tools):
    ops, catalogs = tools["ops"], tools["catalogs"]
    methods = {
        "phones": (lambda value: ops.phone_normalize(value, {"default_country_code": "1"}, catalogs),
                   "src/loop_engine/code_nodes/text_conformance_operations.py: phone_normalize",
                   {"default_country_code": "1", "national_number_length": 10}),
        "emails": (lambda value: tools["recover_email"](value),
                   "src/loop_engine/code_nodes/field_recovery.py: recover_email",
                   {"tables": "the declared default tables"}),
        "names": (lambda value: ops.case_normalize(value, {}, catalogs),
                  "src/loop_engine/code_nodes/text_conformance_operations.py: case_normalize",
                  {"catalogs": "the packaged catalogs"}),
        "websites": (lambda value: ops.website_normalize(value, {}, catalogs),
                     "src/loop_engine/code_nodes/text_conformance_operations.py: website_normalize",
                     {"default_scheme": "https", "strip_www": False, "strip_trailing_slash": True}),
    }
    method, source, parameters = methods[family]
    written, details = [], []
    for row in rows:
        result = method(row["input"])
        value, review, outcome = decide(ops, row["input"], result)
        written.append((row["id"], value, review))
        details.append({"id": row["id"], "outcome": outcome, "confidence": result["confidence"],
                        "reasons": result["reasons"]})
    column = {"phones": "phone", "emails": "email", "names": "name", "websites": "website"}[family]
    return ("id", column, "review"), written, details, source, parameters


def addresses(rows, tools):
    written, details = [], []
    for row in rows:
        result = tools["extract_components"](row["input"])
        review = "yes" if result.confidence < ESCALATE_BELOW or result.remainder else "no"
        written.append((row["id"],) + tuple(result.components.get(part, "")
                                             for part in ADDRESS_PARTS) + (review,))
        details.append({"id": row["id"], "confidence": result.confidence,
                        "remainder": result.remainder, "reasons": list(result.reasons)})
    return (("id",) + ADDRESS_PARTS + ("review",), written, details,
            "src/loop_engine/code_nodes/address_components.py: extract_components",
            {"parser": "stdlib"})


def duplicates(records, tools):
    fields = tools["DuplicateFieldSpec"](name="name", address="address", email="email",
                                         phone="phone", identity="id")
    report = tools["find_duplicates"](
        [{key: record[key] for key in ("id", "name", "address", "email", "phone")}
         for record in records], fields, tools["DuplicatePolicy"]())
    written, details = [], []
    for pair in report.pairs:
        decision = {"duplicate": "same", "possible": "review"}.get(pair.outcome)
        details.append({"pair": [pair.left, pair.right], "outcome": pair.outcome,
                        "confidence": pair.confidence, "blocking_key": pair.blocking_key})
        if decision:
            first, second = sorted((pair.left, pair.right), key=int)
            written.append((first, second, decision))
    written.sort(key=lambda row: (int(row[0]), int(row[1])))
    return (("id_a", "id_b", "decision"), written, details,
            "src/loop_engine/code_nodes/duplicate_detection.py: find_duplicates",
            {"policy": "the default DuplicatePolicy", "comparisons": report.comparisons})


def csv_text(header, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def build(tools):
    files, record = {}, {"record_type": "overnight_item_reference/v1",
                         "thresholds": {"apply_at_or_above": APPLY_AT_OR_ABOVE,
                                        "escalate_below": ESCALATE_BELOW},
                         "families": {}}
    for family in ("phones", "emails", "addresses", "duplicates", "names", "websites"):
        truth = json.loads((POPULATION / family / "truth.json").read_text(encoding="utf-8"))
        if family == "addresses":
            header, written, details, source, parameters = addresses(truth["rows"], tools)
        elif family == "duplicates":
            header, written, details, source, parameters = duplicates(truth["rows"], tools)
        else:
            header, written, details, source, parameters = value_family(family, truth["rows"], tools)
        text = csv_text(header, written)
        path = OUT_FOLDER / f"{family}-output.csv"
        files[path] = text
        OUT_FOLDER.mkdir(parents=True, exist_ok=True)
        scratch = OUT_FOLDER / f".{family}-scoring.csv"
        scratch.write_text(text, encoding="utf-8")
        try:
            score = score_step.score(family, POPULATION / family / "truth.json", scratch)
        finally:
            scratch.unlink()
        entry = {"source_operation": source, "parameters": parameters,
                 "primary_metric": score["primary_metric"], "primary": score["primary"],
                 "passed": score["passed"], "metrics": score["metrics"]}
        if family == "duplicates":
            entry["pairs_scored"] = score["outcomes"]
        else:
            labels = {}
            for outcome in score["outcomes"]:
                labels[outcome["id"]] = ("item_method_gives_the_truth"
                                         if outcome["outcome"] == "correct"
                                         else "item_method_gives_a_different_answer")
            entry["row_labels"] = labels
            entry["rows_where_item_method_gives_the_truth"] = sum(
                label == "item_method_gives_the_truth" for label in labels.values())
            entry["method_details"] = details
        record["families"][family] = entry
    files[OUT_RECORD] = json.dumps(record, indent=1, ensure_ascii=True) + "\n"
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    files = build(operations())
    stale = [path for path, text in files.items()
             if not path.is_file() or path.read_text(encoding="utf-8") != text]
    if args.check:
        for path in stale:
            print(f"differs: {path.relative_to(STUDY)}")
        return 1 if stale else 0
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    summary = {family: (entry["primary"], entry["passed"])
               for family, entry in json.loads(files[OUT_RECORD])["families"].items()}
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
