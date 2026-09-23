"""Score one step output against the frozen truth of its task family.

The scorer reads only two files: the frozen `truth.json` and the `output.csv`
that the step wrote. It never reads the harness transcript or the model's own
statement that it finished. It is deterministic and uses only the Python
standard library.

Usage:

    python score_step.py --family phones --truth ../population/phones/truth.json \
        --output /path/to/output.csv

Leniency, fixed before any run:

- Column names are compared after trimming spaces and ignoring case. Extra
  columns are ignored and counted. A missing required column makes the whole
  output invalid, and every row then counts as missing.
- Values are compared after trimming surrounding spaces. Phone and address
  values also have runs of inner spaces reduced to one space. Email values
  keep inner spaces, because a space inside an address is an error.
- `review` accepts yes, y, true and 1 for yes, and no, n, false, 0 and an
  empty cell for no. Anything else is an invalid review value.
- For duplicates, the order of the two ids in a pair does not matter.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

RECORD_TYPE = "data_cleanup_step_score/v1"

#: Acceptance thresholds, fixed before the first model call.
THRESHOLDS = {
    "phones": {"record_accuracy_at_least": 0.90, "wrong_changes_to_correct_values": 0},
    "emails": {"record_accuracy_at_least": 0.90, "wrong_changes_to_correct_values": 0},
    "addresses": {"record_accuracy_at_least": 0.90, "rewritten_parts": 0},
    "duplicates": {"pair_f1_at_least": 0.90, "hard_negative_merges": 0},
}
YES = {"yes", "y", "true", "1"}
NO = {"no", "n", "false", "0", ""}


def collapse(value):
    return " ".join((value or "").split())


def review_value(value):
    text = (value or "").strip().lower()
    if text in YES:
        return "yes"
    if text in NO:
        return "no"
    return "invalid"


def ratio(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def read_output(path, required):
    """Return (rows, problems). rows is None when the output cannot be scored."""
    path = Path(path)
    problems = {}
    if not path.is_file():
        return None, {"missing_output_file": 1}
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, {"not_utf8": 1}
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration:
        return None, {"empty_output_file": 1}
    except csv.Error:
        return None, {"unreadable_csv": 1}
    names = [name.strip().lower() for name in header]
    missing = [name for name in required if name not in names]
    if missing:
        return None, {"missing_columns": len(missing)}
    extra = [name for name in names if name not in required]
    if extra:
        problems["extra_columns"] = len(extra)
    index = {name: names.index(name) for name in required}
    rows = []
    try:
        for record in reader:
            if not any(cell.strip() for cell in record):
                continue
            if len(record) < len(names):
                problems["short_rows"] = problems.get("short_rows", 0) + 1
                record = record + [""] * (len(names) - len(record))
            rows.append({name: record[position] for name, position in index.items()})
    except csv.Error:
        return None, {"unreadable_csv": 1}
    return rows, problems


def by_id(rows, truth_ids, problems):
    result = {}
    for row in rows:
        identity = (row.get("id") or "").strip()
        if identity not in truth_ids:
            problems["unknown_ids"] = problems.get("unknown_ids", 0) + 1
            continue
        if identity in result:
            problems["repeated_ids"] = problems.get("repeated_ids", 0) + 1
            continue
        result[identity] = row
    return result


# ---------------------------------------------------------------------------
# Phones and emails


def score_value_family(family, truth, output_path):
    column = truth["value_column"]
    normalise = collapse if family == "phones" else (lambda value: (value or "").strip())
    rows, problems = read_output(output_path, truth["output_columns"])
    truth_rows = truth["rows"]
    produced = by_id(rows, {row["id"] for row in truth_rows}, problems) if rows is not None else {}
    outcomes, by_case = [], {}
    for row in truth_rows:
        source = normalise(row["input"])
        accepted = row.get("accepted") or [[row["expected"], row["review"]]]
        accepted = [(normalise(value), review) for value, review in accepted]
        output = produced.get(row["id"])
        if output is None:
            outcome, value, review = "missing", None, None
        else:
            value, review = normalise(output[column]), review_value(output["review"])
            if (value, review) in accepted:
                outcome = "correct"
            elif review == "invalid":
                outcome = "invalid_review_value"
            elif row["kind"] == "keep":
                outcome = "wrong_change" if value != source else "unneeded_review"
            elif row["kind"] == "hold":
                outcome = "guessed_instead_of_hold" if value != source else "missed_hold"
            elif any(candidate == value for candidate, _ in accepted):
                outcome = "right_value_wrong_review"
            elif value == source:
                outcome = "missed_change" if row["kind"] == "change" else "missed_hold"
            else:
                outcome = "wrong_value"
        outcomes.append(dict(
            id=row["id"], case_type=row["case_type"], kind=row["kind"], outcome=outcome,
            output_value=value, output_review=review,
            value_ok=value is not None and any(candidate == value for candidate, _ in accepted),
            changed=value is not None and value != source))
        bucket = by_case.setdefault(row["case_type"], {"rows": 0, "correct": 0})
        bucket["rows"] += 1
        bucket["correct"] += outcome == "correct"

    def count(kind=None, outcome=None, flag=None):
        return sum(1 for item in outcomes
                   if (kind is None or item["kind"] == kind)
                   and (outcome is None or item["outcome"] == outcome)
                   and (flag is None or item[flag]))

    wrong_changes = count("keep", flag="changed")
    metrics = {
        "rows": len(truth_rows),
        "correct": count(outcome="correct"),
        "record_accuracy": ratio(count(outcome="correct"), len(truth_rows)),
        "value_accuracy": ratio(count(flag="value_ok"), len(truth_rows)),
        "change_recall": ratio(count("change", "correct"), count("change")),
        "change_precision": ratio(count(outcome="correct", flag="changed"), count(flag="changed")),
        "wrong_changes_to_correct_values": wrong_changes,
        "wrong_change_rate_on_correct_values": ratio(wrong_changes, count("keep")),
        "correct_hold_rate": ratio(count("hold", "correct"), count("hold")),
        "guess_rate_on_hold_rows": ratio(count("hold", flag="changed"), count("hold")),
        "missing_rows": count(outcome="missing"),
    }
    limits = THRESHOLDS[family]
    passed = (rows is not None
              and metrics["record_accuracy"] >= limits["record_accuracy_at_least"]
              and wrong_changes <= limits["wrong_changes_to_correct_values"])
    return finish(family, "record_accuracy", metrics, passed, problems, rows is not None,
                  outcomes, by_case)


# ---------------------------------------------------------------------------
# Addresses


def score_addresses(truth, output_path):
    parts = truth["parts"]
    rows, problems = read_output(output_path, truth["output_columns"])
    truth_rows = truth["rows"]
    produced = by_id(rows, {row["id"] for row in truth_rows}, problems) if rows is not None else {}
    outcomes, by_case = [], {}
    part_checks = part_hits = rewritten = filled = 0
    per_part = {part: [0, 0] for part in parts}
    for row in truth_rows:
        output = produced.get(row["id"])
        source = collapse(row["input"])
        wrong_parts, row_rewrites = [], []
        if output is None:
            outcome = "missing"
        else:
            review = review_value(output["review"])
            for part in parts:
                value = collapse(output[part])
                if value:
                    filled += 1
                    if value not in source:
                        rewritten += 1
                        row_rewrites.append(part)
            if row["review"] == "yes":
                outcome = "correct" if review == "yes" else (
                    "invalid_review_value" if review == "invalid" else "missed_hold")
            else:
                for part in parts:
                    hit = collapse(output[part]) == collapse(row["expected"][part])
                    part_checks += 1
                    part_hits += hit
                    per_part[part][0] += 1
                    per_part[part][1] += hit
                    if not hit:
                        wrong_parts.append(part)
                if review == "invalid":
                    outcome = "invalid_review_value"
                elif wrong_parts:
                    outcome = "wrong_parts"
                elif review == "yes":
                    outcome = "unneeded_review"
                else:
                    outcome = "correct"
        if output is None and row["review"] == "no":
            part_checks += len(parts)
            for part in parts:
                per_part[part][0] += 1
        outcomes.append(dict(id=row["id"], case_type=row["case_type"], kind=row["kind"],
                             outcome=outcome, wrong_parts=wrong_parts,
                             rewritten_parts=row_rewrites))
        bucket = by_case.setdefault(row["case_type"], {"rows": 0, "correct": 0})
        bucket["rows"] += 1
        bucket["correct"] += outcome == "correct"
    hold_rows = [item for item in outcomes if item["kind"] == "hold"]
    split_rows = [item for item in outcomes if item["kind"] != "hold"]
    correct = sum(item["outcome"] == "correct" for item in outcomes)
    metrics = {
        "rows": len(truth_rows),
        "correct": correct,
        "record_accuracy": ratio(correct, len(truth_rows)),
        "part_accuracy": ratio(part_hits, part_checks),
        "part_accuracy_by_part": {part: ratio(hit, total) for part, (total, hit) in per_part.items()},
        "rewritten_parts": rewritten,
        "rewritten_part_rate": ratio(rewritten, filled),
        "correct_hold_rate": ratio(sum(item["outcome"] == "correct" for item in hold_rows),
                                   len(hold_rows)),
        "unneeded_review_rate": ratio(sum(item["outcome"] == "unneeded_review" for item in split_rows),
                                      len(split_rows)),
        "missing_rows": sum(item["outcome"] == "missing" for item in outcomes),
    }
    limits = THRESHOLDS["addresses"]
    passed = (rows is not None
              and metrics["record_accuracy"] >= limits["record_accuracy_at_least"]
              and rewritten <= limits["rewritten_parts"])
    return finish("addresses", "record_accuracy", metrics, passed, problems, rows is not None,
                  outcomes, by_case)


# ---------------------------------------------------------------------------
# Duplicates


def pair_key(first, second):
    return tuple(sorted((first, second), key=lambda value: (len(value), value)))


def closure_pairs(pairs):
    parent = {}

    def find(item):
        parent.setdefault(item, item)
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for first, second in pairs:
        parent[find(first)] = find(second)
    groups = {}
    for item in list(parent):
        groups.setdefault(find(item), []).append(item)
    result = set()
    for members in groups.values():
        for index, first in enumerate(members):
            for second in members[index + 1:]:
                result.add(pair_key(first, second))
    return result


def prf(predicted, actual):
    hits = len(predicted & actual)
    precision = hits / len(predicted) if predicted else 0.0
    recall = hits / len(actual) if actual else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return round(precision, 6), round(recall, 6), round(f1, 6)


def score_duplicates(truth, output_path):
    rows, problems = read_output(output_path, truth["output_columns"])
    ids = {row["id"] for row in truth["rows"]}
    same, review = set(), set()
    if rows is not None:
        seen = {}
        for row in rows:
            first, second = (row.get("id_a") or "").strip(), (row.get("id_b") or "").strip()
            decision = (row.get("decision") or "").strip().lower()
            if first not in ids or second not in ids or first == second:
                problems["invalid_pairs"] = problems.get("invalid_pairs", 0) + 1
                continue
            if decision not in ("same", "review"):
                problems["invalid_decisions"] = problems.get("invalid_decisions", 0) + 1
                continue
            key = pair_key(first, second)
            if key in seen:
                if seen[key] != decision:
                    problems["conflicting_pairs"] = problems.get("conflicting_pairs", 0) + 1
                else:
                    problems["repeated_pairs"] = problems.get("repeated_pairs", 0) + 1
                continue
            seen[key] = decision
            (same if decision == "same" else review).add(key)
    duplicates = {pair_key(*pair) for pair in truth["duplicate_pairs"]}
    ambiguous = {pair_key(*item["pair"]) for item in truth["ambiguous_pairs"]}
    hard = {pair_key(*item["pair"]) for item in truth["hard_negative_pairs"]}
    precision, recall, f1 = prf(same, duplicates)
    closure = closure_pairs(same)
    c_precision, c_recall, c_f1 = prf(closure, duplicates)
    hard_merges = len(same & hard)
    metrics = {
        "rows": len(truth["rows"]),
        "true_duplicate_pairs": len(duplicates),
        "pairs_marked_same": len(same),
        "pairs_marked_review": len(review),
        "pair_precision": precision,
        "pair_recall": recall,
        "pair_f1": f1,
        "closure_pair_precision": c_precision,
        "closure_pair_recall": c_recall,
        "closure_pair_f1": c_f1,
        "false_merges": len(same - duplicates),
        "hard_negative_merges": hard_merges,
        "ambiguous_pairs_marked_same": len(same & ambiguous),
        "correct_hold_rate": ratio(len(review & ambiguous), len(ambiguous)),
        "true_duplicates_only_marked_review": len(review & duplicates),
    }
    limits = THRESHOLDS["duplicates"]
    passed = (rows is not None and f1 >= limits["pair_f1_at_least"]
              and hard_merges <= limits["hard_negative_merges"])
    outcomes = [dict(pair=list(pair), truth=("duplicate" if pair in duplicates else "ambiguous"
                                             if pair in ambiguous else "hard_negative"
                                             if pair in hard else "distinct"),
                     decision=("same" if pair in same else "review"))
                for pair in sorted(same | review, key=lambda p: (int(p[0]), int(p[1])))]
    return finish("duplicates", "pair_f1", metrics, passed, problems, rows is not None,
                  outcomes, {})


# ---------------------------------------------------------------------------


def finish(family, primary_name, metrics, passed, problems, readable, outcomes, by_case):
    primary = metrics.get(primary_name)
    return {
        "record_type": RECORD_TYPE,
        "family": family,
        "output_readable": readable,
        "primary_metric": primary_name,
        "primary": primary if primary is not None else 0.0,
        "passed": bool(passed),
        "thresholds": THRESHOLDS[family],
        "metrics": metrics,
        "format_problems": problems,
        "by_case_type": by_case,
        "outcomes": outcomes,
    }


def score(family, truth_path, output_path):
    truth = json.loads(Path(truth_path).read_text(encoding="utf-8"))
    if truth.get("family") != family:
        raise ValueError(f"truth file is for {truth.get('family')!r}, not {family!r}")
    if family in ("phones", "emails"):
        return score_value_family(family, truth, output_path)
    if family == "addresses":
        return score_addresses(truth, output_path)
    if family == "duplicates":
        return score_duplicates(truth, output_path)
    raise ValueError(f"unknown family {family!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--family", required=True, choices=sorted(THRESHOLDS))
    parser.add_argument("--truth", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--full", action="store_true", help="print every row outcome")
    args = parser.parse_args(argv)
    result = score(args.family, args.truth, args.output)
    if not args.full:
        result = {key: value for key, value in result.items() if key != "outcomes"}
    print(json.dumps(result, indent=1, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
