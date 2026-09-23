"""Tests for the step scorer, with known-wrong outputs that must fail.

Run from this folder:

    python -m unittest test_score_step -v
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
POPULATION = HERE.parent / "population"
sys.path.insert(0, str(HERE))

import score_step  # noqa: E402

FAMILIES = ("phones", "emails", "addresses", "duplicates", "names", "websites")
VALUE_FAMILIES = ("phones", "emails", "names", "websites")


def truth(family):
    return json.loads((POPULATION / family / "truth.json").read_text(encoding="utf-8"))


def write_csv(folder, header, rows, name="output.csv"):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    path = Path(folder) / name
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path


def perfect_rows(family):
    """(header, rows) of an output that follows the truth exactly."""
    data = truth(family)
    if family in VALUE_FAMILIES:
        return data["output_columns"], [(row["id"], row["expected"], row["review"])
                                        for row in data["rows"]]
    if family == "addresses":
        return data["output_columns"], [
            (row["id"],) + tuple(row["expected"][part] for part in data["parts"]) + (row["review"],)
            for row in data["rows"]]
    rows = [(a, b, "same") for a, b in data["duplicate_pairs"]]
    rows += [(item["pair"][0], item["pair"][1], "review") for item in data["ambiguous_pairs"]]
    return data["output_columns"], rows


def score_rows(family, header, rows):
    with tempfile.TemporaryDirectory() as folder:
        path = write_csv(folder, header, rows)
        return score_step.score(family, POPULATION / family / "truth.json", path)


class PerfectOutputTests(unittest.TestCase):
    def test_a_perfect_output_passes_every_family(self):
        for family in FAMILIES:
            header, rows = perfect_rows(family)
            result = score_rows(family, header, rows)
            self.assertTrue(result["passed"], family)
            self.assertEqual(result["primary"], 1.0, family)

    def test_row_order_header_case_and_an_extra_column_are_tolerated(self):
        header, rows = perfect_rows("phones")
        loud = [name.upper() for name in header] + ["notes"]
        result = score_rows("phones", loud, [row + ("x",) for row in reversed(rows)])
        self.assertTrue(result["passed"])
        self.assertEqual(result["format_problems"], {"extra_columns": 1})

    def test_pair_order_inside_a_duplicate_pair_is_tolerated(self):
        header, rows = perfect_rows("duplicates")
        result = score_rows("duplicates", header, [(b, a, d) for a, b, d in rows])
        self.assertTrue(result["passed"])


class KnownWrongFixtureTests(unittest.TestCase):
    def test_every_frozen_known_wrong_fixture_fails(self):
        for family in FAMILIES:
            fixtures = sorted((POPULATION / family / "known-wrong").glob("*.csv"))
            self.assertGreaterEqual(len(fixtures), 3, family)
            for fixture in fixtures:
                result = score_step.score(family, POPULATION / family / "truth.json", fixture)
                self.assertFalse(result["passed"], f"{family}/{fixture.name}")
                self.assertLess(result["primary"], 0.5, f"{family}/{fixture.name}")

    def test_the_three_required_kinds_exist_for_every_family(self):
        for family in FAMILIES:
            names = {path.name for path in (POPULATION / family / "known-wrong").glob("*.csv")}
            self.assertTrue({"copied-input.csv", "all-null.csv", "shuffled.csv"} <= names, family)

    def test_a_missing_output_file_fails_and_is_not_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            result = score_step.score("phones", POPULATION / "phones" / "truth.json",
                                      Path(folder) / "output.csv")
        self.assertFalse(result["passed"])
        self.assertFalse(result["output_readable"])
        self.assertEqual(result["metrics"]["missing_rows"], result["metrics"]["rows"])

    def test_a_missing_required_column_makes_the_output_unreadable(self):
        header, rows = perfect_rows("emails")
        result = score_rows("emails", header[:2], [row[:2] for row in rows])
        self.assertFalse(result["output_readable"])
        self.assertFalse(result["passed"])


class GuardTests(unittest.TestCase):
    """Each second condition of a threshold rejects an output that is otherwise accurate."""

    def value_family_with_one_wrong_change(self, family):
        header, rows = perfect_rows(family)
        data = truth(family)
        keep = next(row["id"] for row in data["rows"] if row["kind"] == "keep" and row["input"])
        rows = [(i, "WRONG" if i == keep else value, review) for i, value, review in rows]
        return header, rows

    def test_one_wrong_change_to_a_correct_value_fails_an_accurate_output(self):
        for family in VALUE_FAMILIES:
            header, rows = self.value_family_with_one_wrong_change(family)
            result = score_rows(family, header, rows)
            self.assertGreaterEqual(result["metrics"]["record_accuracy"], 0.9, family)
            self.assertEqual(result["metrics"]["wrong_changes_to_correct_values"], 1, family)
            self.assertFalse(result["passed"], family)

    def test_the_wrong_change_guard_is_what_rejects_it(self):
        relaxed = {family: dict(limits) for family, limits in score_step.THRESHOLDS.items()}
        for family in VALUE_FAMILIES:
            relaxed[family]["wrong_changes_to_correct_values"] = 99
        with mock.patch.object(score_step, "THRESHOLDS", relaxed):
            for family in VALUE_FAMILIES:
                header, rows = self.value_family_with_one_wrong_change(family)
                self.assertTrue(score_rows(family, header, rows)["passed"], family)

    def address_output_with_one_expanded_part(self):
        header, rows = perfect_rows("addresses")
        position = header.index("street")
        changed = []
        done = False
        for row in rows:
            row = list(row)
            if not done and row[position].endswith(" St"):
                row[position] = row[position][:-3] + " Street"
                done = True
            changed.append(tuple(row))
        self.assertTrue(done)
        return header, changed

    def test_one_rewritten_address_part_fails_an_accurate_output(self):
        header, rows = self.address_output_with_one_expanded_part()
        result = score_rows("addresses", header, rows)
        self.assertGreaterEqual(result["metrics"]["record_accuracy"], 0.9)
        self.assertEqual(result["metrics"]["rewritten_parts"], 1)
        self.assertFalse(result["passed"])

    def test_the_rewrite_guard_is_what_rejects_it(self):
        relaxed = {family: dict(limits) for family, limits in score_step.THRESHOLDS.items()}
        relaxed["addresses"]["rewritten_parts"] = 99
        with mock.patch.object(score_step, "THRESHOLDS", relaxed):
            header, rows = self.address_output_with_one_expanded_part()
            self.assertTrue(score_rows("addresses", header, rows)["passed"])

    def duplicates_with_one_hard_negative_merge(self):
        header, rows = perfect_rows("duplicates")
        pair = truth("duplicates")["hard_negative_pairs"][0]["pair"]
        return header, rows + [(pair[0], pair[1], "same")]

    def test_one_hard_negative_merge_fails_an_accurate_output(self):
        header, rows = self.duplicates_with_one_hard_negative_merge()
        result = score_rows("duplicates", header, rows)
        self.assertGreaterEqual(result["metrics"]["pair_f1"], 0.9)
        self.assertEqual(result["metrics"]["hard_negative_merges"], 1)
        self.assertFalse(result["passed"])

    def test_the_hard_negative_guard_is_what_rejects_it(self):
        relaxed = {family: dict(limits) for family, limits in score_step.THRESHOLDS.items()}
        relaxed["duplicates"]["hard_negative_merges"] = 99
        with mock.patch.object(score_step, "THRESHOLDS", relaxed):
            header, rows = self.duplicates_with_one_hard_negative_merge()
            self.assertTrue(score_rows("duplicates", header, rows)["passed"])


class OutcomeTests(unittest.TestCase):
    def test_a_guess_on_a_held_value_is_a_change_not_a_hold(self):
        header, rows = perfect_rows("phones")
        data = truth("phones")
        hold = next(row for row in data["rows"] if row["kind"] == "hold")
        rows = [(i, "+14155550100" if i == hold["id"] else v, "no" if i == hold["id"] else r)
                for i, v, r in rows]
        result = score_rows("phones", header, rows)
        outcome = next(item for item in result["outcomes"] if item["id"] == hold["id"])
        self.assertEqual(outcome["outcome"], "guessed_instead_of_hold")
        self.assertLess(result["metrics"]["correct_hold_rate"], 1.0)

    def test_an_unflagged_copy_of_a_held_value_is_a_missed_hold(self):
        header, rows = perfect_rows("emails")
        data = truth("emails")
        hold = next(row for row in data["rows"] if row["kind"] == "hold")
        rows = [(i, v, "no" if i == hold["id"] else r) for i, v, r in rows]
        result = score_rows("emails", header, rows)
        outcome = next(item for item in result["outcomes"] if item["id"] == hold["id"])
        self.assertEqual(outcome["outcome"], "missed_hold")

    def test_either_accepted_answer_counts_for_a_row_with_alternatives(self):
        data = truth("phones")
        row = next(row for row in data["rows"] if row["kind"] == "alternatives")
        for value, review in row["accepted"]:
            header, rows = perfect_rows("phones")
            rows = [(i, value if i == row["id"] else v, review if i == row["id"] else r)
                    for i, v, r in rows]
            result = score_rows("phones", header, rows)
            self.assertEqual(result["primary"], 1.0, value)

    def test_duplicate_pairs_are_also_scored_after_closure(self):
        header, rows = perfect_rows("duplicates")
        data = truth("duplicates")
        clusters = {}
        for record in data["rows"]:
            clusters.setdefault(record["entity"], []).append(record["id"])
        triple = next(ids for ids in clusters.values() if len(ids) == 3)
        a, b, c = sorted(triple, key=int)
        missing = score_step.pair_key(a, c)
        rows = [row for row in rows if score_step.pair_key(row[0], row[1]) != missing]
        result = score_rows("duplicates", header, rows)
        self.assertLess(result["metrics"]["pair_recall"], 1.0)
        self.assertEqual(result["metrics"]["closure_pair_recall"], 1.0)


class NewFamilyTests(unittest.TestCase):
    """Known-wrong outputs that are specific to the names and websites families."""

    def test_a_generic_title_case_of_every_name_fails(self):
        fixture = POPULATION / "names" / "known-wrong" / "python-title-case.csv"
        result = score_step.score("names", POPULATION / "names" / "truth.json", fixture)
        self.assertFalse(result["passed"])
        self.assertLess(result["primary"], 0.9)
        self.assertGreater(result["metrics"]["wrong_changes_to_correct_values"], 0)

    def test_writing_the_whole_address_in_small_letters_fails(self):
        fixture = POPULATION / "websites" / "known-wrong" / "whole-address-lower-case.csv"
        result = score_step.score("websites", POPULATION / "websites" / "truth.json", fixture)
        self.assertFalse(result["passed"])
        self.assertLess(result["primary"], 0.9)

    def test_a_decomposed_accent_is_accepted_as_the_same_name(self):
        import unicodedata
        header, rows = perfect_rows("names")
        rows = [(i, unicodedata.normalize("NFD", v), r) for i, v, r in rows]
        self.assertTrue(any(unicodedata.normalize("NFC", v) != v for _, v, _ in rows))
        result = score_rows("names", header, rows)
        self.assertEqual(result["primary"], 1.0)

    def test_a_website_path_written_in_small_letters_is_wrong(self):
        header, rows = perfect_rows("websites")
        data = truth("websites")
        row = next(r for r in data["rows"] if r["kind"] == "change" and "/About-Us" in r["expected"])
        rows = [(i, v.lower() if i == row["id"] else v, r) for i, v, r in rows]
        result = score_rows("websites", header, rows)
        outcome = next(item for item in result["outcomes"] if item["id"] == row["id"])
        self.assertEqual(outcome["outcome"], "wrong_value")

    def test_a_changed_mixed_case_name_is_a_wrong_change_that_fails_the_step(self):
        header, rows = perfect_rows("names")
        data = truth("names")
        row = next(r for r in data["rows"] if r["input"] == "eZone Games")
        rows = [(i, "Ezone Games" if i == row["id"] else v, r) for i, v, r in rows]
        result = score_rows("names", header, rows)
        self.assertEqual(result["metrics"]["wrong_changes_to_correct_values"], 1)
        self.assertFalse(result["passed"])


class PopulationTests(unittest.TestCase):
    def test_the_population_files_match_the_generator(self):
        sys.path.insert(0, str(POPULATION))
        import generate_population
        for relative, text in generate_population.build().items():
            written = (POPULATION / relative).read_text(encoding="utf-8")
            self.assertEqual(written, text, relative)

    def test_every_telephone_number_is_in_a_range_reserved_for_fiction(self):
        import re
        import unicodedata
        allowed = (re.compile(r"^\+1\d{3}5550(1\d\d)$"), re.compile(r"^\+442079460\d{3}$"),
                   re.compile(r"^\+44(113|114|115|116|117|121|131|141|151|161)4960\d{3}$"),
                   re.compile(r"^\+447700900\d{3}$"), re.compile(r"^\+6125550\d{4}$"))
        for row in truth("phones")["rows"]:
            for value, _ in row.get("accepted") or [[row["expected"], row["review"]]]:
                digits = unicodedata.normalize("NFKC", value).split(" ext ")[0]
                if row["kind"] in ("hold",) or not digits.startswith("+"):
                    continue
                self.assertTrue(any(p.match(digits) for p in allowed), value)

    def test_every_hold_and_keep_row_expects_its_own_input(self):
        for family in VALUE_FAMILIES:
            for row in truth(family)["rows"]:
                if row["kind"] in ("hold", "keep"):
                    self.assertEqual(row["expected"], row["input"], (family, row["id"]))

    def test_truth_is_never_inside_a_step_input(self):
        for family in FAMILIES:
            text = (POPULATION / family / "input.csv").read_text(encoding="utf-8")
            self.assertNotIn("expected", text)
            self.assertNotIn("case_type", text)


if __name__ == "__main__":
    unittest.main()
