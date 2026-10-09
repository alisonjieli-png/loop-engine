"""Tests every dataset package of the kaggle_public_good line runs, driven by its component.json and schema.json.

The schema contract and the loader declare the same tables, columns, types and required columns; every synthetic
fixture reads with typed values; every data file the package copies is the recorded bytes and reads under the
schema. Known-wrong controls: a value of the wrong type, a missing column, an unknown column, a ragged record and a
changed data file are each refused with their reason, and an unknown table is refused on the command line. When the
loader's public functions are replaced by ones that raise, these tests fail.
"""
from __future__ import annotations

import csv
import importlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
LOADER = importlib.import_module(CARD["loader"]["module"])
FIXTURES = CARD["fixtures"]


def rewrite(source: Path, target: Path, table: str, change) -> None:
    """Write ``source`` to ``target`` with ``change(header, rows)`` applied, in the table's own format."""
    spec = LOADER.TABLES[table]
    if spec["format"] == LOADER.DELIMITED:
        with open(source, encoding="utf-8-sig", newline="") as handle:
            records = list(csv.reader(handle, delimiter=spec["delimiter"]))
        header, rows = change(records[0], [dict(zip(records[0], record)) for record in records[1:]])
        out = io.StringIO()
        writer = csv.writer(out, delimiter=spec["delimiter"], lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow([row.get(name, "") for name in header] + row.get("__extra__", []))
        target.write_text(out.getvalue(), encoding="utf-8")
        return
    if spec["format"] == LOADER.JSON_LINES:
        rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        rows = json.loads(source.read_text(encoding="utf-8"))
    header = list(rows[0]) if rows else []
    _header, rows = change(header, rows)
    rows = [{key: value for key, value in row.items() if key != "__extra__"} for row in rows]
    if spec["format"] == LOADER.JSON_LINES:
        target.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    else:
        target.write_text(json.dumps(rows), encoding="utf-8")


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.folder)

    def refused(self, table: str, path: Path, reason: str) -> None:
        with self.assertRaises(LOADER.SchemaError) as caught:
            LOADER.read_table(table, path)
        self.assertEqual(caught.exception.reason, reason, caught.exception.detail)

    def test_schema_contract_and_loader_declare_the_same_tables(self):
        self.assertEqual(sorted(SCHEMA["$defs"]), LOADER.table_names())
        self.assertEqual(sorted(FIXTURES), LOADER.table_names())
        for name, spec in LOADER.TABLES.items():
            definition = SCHEMA["$defs"][name]
            self.assertEqual(sorted(definition["required"]), sorted(spec["required"]))
            self.assertEqual(sorted(definition["properties"]), sorted(spec["fields"]))
            for column, field in spec["fields"].items():
                declared = definition["properties"][column]["type"]
                self.assertEqual(sorted(declared if isinstance(declared, list) else [declared]),
                                 sorted(field["type"]), (name, column))
                self.assertEqual(definition["properties"][column].get("format"), field.get("format"))

    def test_every_fixture_reads_with_typed_values(self):
        for name, fixture in FIXTURES.items():
            rows = LOADER.read_table(name, ROOT / fixture["path"])
            self.assertEqual(len(rows), fixture["rows"], name)
            for row in rows:
                self.assertEqual(LOADER.check_row(name, row), row)
            self.assertEqual(LOADER.validate_file(name, ROOT / fixture["path"])["rows"], fixture["rows"])

    def test_known_wrong_a_value_of_the_wrong_type_is_refused(self):
        for name, fixture in FIXTURES.items():
            wrong = fixture["wrong"]
            target = self.folder / Path(fixture["path"]).name

            def change(header, rows, wrong=wrong):
                if wrong["reason"] == "ragged_record":
                    rows[0]["__extra__"] = ["an extra cell"]
                else:
                    rows[0][wrong["column"]] = wrong["value"]
                return header, rows

            rewrite(ROOT / fixture["path"], target, name, change)
            self.refused(name, target, wrong["reason"])

    def test_known_wrong_a_missing_column_is_refused(self):
        for name, fixture in FIXTURES.items():
            required = LOADER.TABLES[name]["required"]
            if not required:
                continue
            target = self.folder / Path(fixture["path"]).name

            def change(header, rows, column=required[0]):
                return [item for item in header if item != column], [
                    {key: value for key, value in row.items() if key != column} for row in rows]

            rewrite(ROOT / fixture["path"], target, name, change)
            self.refused(name, target, "missing_column")

    def test_known_wrong_an_unknown_column_is_refused(self):
        for name, fixture in FIXTURES.items():
            target = self.folder / Path(fixture["path"]).name

            def change(header, rows):
                return header + ["not_a_column_of_this_table"], [
                    {**row, "not_a_column_of_this_table": "1"} for row in rows]

            rewrite(ROOT / fixture["path"], target, name, change)
            self.refused(name, target, "unknown_column")

    def test_copied_data_files_are_the_recorded_bytes_and_read(self):
        for file_name, recorded in LOADER.DATA_FILES.items():
            path = ROOT / "data" / file_name
            self.assertEqual(LOADER.check_data_file(path), recorded["sha256"])
            self.assertEqual(LOADER.validate_file(recorded["table"], path)["rows"], recorded["rows"])
            changed = self.folder / file_name
            changed.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaises(LOADER.SchemaError) as caught:
                LOADER.check_data_file(changed)
            self.assertEqual(caught.exception.reason, "changed_file")

    def test_command_line_checks_a_file_and_refuses_an_unknown_table(self):
        name = sorted(FIXTURES)[0]
        out = io.StringIO()
        self.assertEqual(LOADER.main([name, str(ROOT / FIXTURES[name]["path"])], out), 0)
        self.assertEqual(json.loads(out.getvalue())["rows"], FIXTURES[name]["rows"])
        out = io.StringIO()
        self.assertEqual(LOADER.main(["not_a_table_of_this_dataset", str(ROOT / FIXTURES[name]["path"])], out), 2)
        self.assertEqual(json.loads(out.getvalue())["reason"], "unknown_table")


if __name__ == "__main__":
    unittest.main()
