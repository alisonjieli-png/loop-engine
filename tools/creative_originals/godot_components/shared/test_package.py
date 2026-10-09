"""Check this Baltor Godot component package without an engine.

    python3 -m unittest test_package

The component script must match the contract in component.json (class, base, signals, exports, properties,
methods, enums), the GDScript engine tests must be present, and every listed file must match its digest. The
declaration reader is held to known answers, and known-wrong copies (a renamed method, a removed signal or
export, another class name, a changed byte) must be refused. Running the GDScript tests needs Godot; see README.md.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import inspect_gdscript as inspector

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
IDENTITY = CARD["job"]["identity"]
CONTRACT = CARD["contract"]
SCRIPT = ROOT / f"{IDENTITY}.gd"
TESTS = ROOT / "tests" / f"test_{IDENTITY}.gd"

SAMPLE = r'''@tool
class_name SampleThing extends Node2D
## A sample for the reader.

signal moved(from_point: Vector2, to_point: Vector2)
signal reset

enum Mode { IDLE, RUN = 4, JUMP }
enum { LOOSE_A, LOOSE_B }
const LIMIT: int = 3
const _HIDDEN := "x # not a comment"

@export_group("Motion")
@export var speed: float = 120.5
@export_range(0, 10, 1) var lives: int = 3
## Shown on the label.
@export
var label: String = "a # b, \"quoted\""
@export var offset: Vector2 = Vector2(1, -2):
	set(value):
		offset = value
@export var mode: Mode = Mode.RUN
var count: int = 0
static var shared_total: int = 0
var _secret: int = 1


## Walks.
func walk(direction: Vector2,
		step_scale: float = 1.0, # trailing comment
		tags: Array[String] = []) -> Vector2:
	var text := """
func fake() -> void:
signal fake_signal
"""
	return direction * step_scale * float(tags.size() + text.length())


static func make(values: Dictionary = {"a": [1, 2]}) -> SampleThing:
	return null if values.is_empty() else SampleThing.new()


func _private() -> void:
	pass


class Inner:
	signal inner_signal
	func hidden() -> void:
		pass
'''


def script_text() -> str:
    """The component script as text."""
    return SCRIPT.read_text(encoding="utf-8")


def drop_lines(source: str, first: int, last: int) -> str:
    """``source`` without physical lines ``first`` to ``last`` (counted from 1, inclusive)."""
    lines = source.split("\n")
    return "\n".join(lines[: first - 1] + lines[last:])


class ContractTests(unittest.TestCase):
    def test_card_lists_every_file_with_its_digest(self):
        listed = {row["path"] for row in CARD["files"]}
        self.assertIn(SCRIPT.name, listed)
        self.assertIn(f"tests/{TESTS.name}", listed)
        for row in CARD["files"]:
            with self.subTest(path=row["path"]):
                self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"])

    def test_script_matches_the_contract(self):
        self.assertEqual(inspector.compare_contract(CONTRACT, inspector.parse_file(SCRIPT)), [])

    def test_contract_is_rebuilt_from_the_script(self):
        rebuilt = inspector.contract_from_parse(inspector.parse_file(SCRIPT), CONTRACT["placement"],
                                                CONTRACT["depends_on"])
        self.assertEqual(rebuilt, CONTRACT)

    def test_placement_class_and_surface(self):
        self.assertEqual(CONTRACT["placement"], f"res://baltor/godot_components/{IDENTITY}/")
        self.assertTrue(CONTRACT["class_name"].startswith("Baltor"), CONTRACT["class_name"])
        self.assertTrue(CONTRACT["methods"], "a component has at least one public method")
        for row in CONTRACT["methods"]:
            self.assertIsNotNone(row["returns"], f"{row['name']} declares its return type")
        for row in CONTRACT["exports"]:
            self.assertIsNotNone(row["type"], f"{row['name']} declares its type")

    def test_engine_tests_are_present(self):
        tested = inspector.parse_file(TESTS)
        names = [row["name"] for row in tested["methods"] if row["name"].startswith("test_")]
        self.assertGreaterEqual(len(names), inspector.MINIMUM_TESTS)
        self.assertEqual(tested["extends"], inspector.TEST_BASE)
        self.assertIn(f'preload("../{SCRIPT.name}")', TESTS.read_text(encoding="utf-8"))
        for shared in ("run_tests.gd", "baltor_test.gd"):
            self.assertTrue((ROOT / shared).is_file(), shared)

    def test_check_package_is_clean(self):
        report = inspector.check_package(ROOT)
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["identity"], IDENTITY)
        self.assertEqual(report["class_name"], CONTRACT["class_name"])
        self.assertGreaterEqual(len(report["tests"]), inspector.MINIMUM_TESTS)

    def test_command_line_prints_json(self):
        for target, key, value in ((ROOT, "identity", IDENTITY), (SCRIPT, "class_name", CONTRACT["class_name"])):
            with self.subTest(target=target.name):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = inspector.main([str(target)])
                self.assertEqual(status, 0)
                self.assertEqual(json.loads(output.getvalue())[key], value)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(inspector.main([]), 2)


class ReaderKnownAnswerTests(unittest.TestCase):
    def setUp(self):
        self.parsed = inspector.parse_source(SAMPLE)

    def test_header_signals_and_enums(self):
        parsed = self.parsed
        self.assertEqual((parsed["class_name"], parsed["extends"], parsed["tool"]), ("SampleThing", "Node2D", True))
        self.assertEqual(parsed["class_doc"], "A sample for the reader.")
        self.assertEqual([(row["name"], row["arguments"]) for row in parsed["signals"]],
                         [("moved", ["from_point: Vector2", "to_point: Vector2"]), ("reset", [])])
        self.assertEqual([(row["name"], row["values"]) for row in parsed["enums"]],
                         [("Mode", ["IDLE", "RUN", "JUMP"]), (None, ["LOOSE_A", "LOOSE_B"])])
        self.assertEqual([(row["name"], row["value"]) for row in parsed["constants"]],
                         [("LIMIT", 3), ("_HIDDEN", "x # not a comment")])
        self.assertEqual([row["name"] for row in parsed["inner_classes"]], ["Inner"])

    def test_exports_and_properties(self):
        exports = {row["name"]: row for row in self.parsed["exports"]}
        self.assertEqual(list(exports), ["speed", "lives", "label", "offset", "mode"])
        self.assertEqual((exports["speed"]["type"], exports["speed"]["default"]), ("float", 120.5))
        self.assertEqual(exports["lives"]["annotation"], "@export_range(0, 10, 1)")
        self.assertEqual(exports["label"]["default"], 'a # b, "quoted"')
        self.assertEqual(exports["label"]["doc"], "Shown on the label.")
        self.assertEqual(exports["offset"]["default"], "Vector2(1, -2)")
        self.assertEqual((exports["mode"]["type"], exports["mode"]["default"]), ("Mode", "Mode.RUN"))
        contract = inspector.contract_from_parse(self.parsed, "res://sample/")
        self.assertEqual(contract["properties"], [{"name": "count", "type": "int"},
                                                  {"name": "shared_total", "type": "int", "static": True}])
        self.assertEqual(contract["enums"], [{"name": "Mode", "values": ["IDLE", "RUN", "JUMP"]}])

    def test_methods_skip_bodies_strings_and_inner_classes(self):
        methods = {row["name"]: row for row in self.parsed["methods"]}
        self.assertEqual(list(methods), ["walk", "make", "_private"])
        self.assertEqual(methods["walk"]["arguments"],
                         ["direction: Vector2", "step_scale: float = 1.0", "tags: Array[String] = []"])
        self.assertEqual((methods["walk"]["returns"], methods["walk"]["doc"]), ("Vector2", "Walks."))
        self.assertEqual((methods["make"]["arguments"], methods["make"]["static"]),
                         (['values: Dictionary = {"a": [1, 2]}'], True))
        contract = inspector.contract_from_parse(self.parsed, "res://sample/")
        self.assertEqual([row["name"] for row in contract["methods"]], ["walk", "make"])
        self.assertEqual([row["name"] for row in contract["signals"]], ["moved", "reset"])

    def test_literals_and_logical_lines(self):
        answers = {"0x1F": 31, "1_000": 1000, "-2.5": -2.5, "true": True, "null": None, "'single'": "single",
                   "Vector2.ZERO": "Vector2.ZERO", "1e999": "1e999", '&"name"': '&"name"'}
        for text, value in answers.items():
            with self.subTest(text=text):
                self.assertEqual(inspector.literal_value(text), value)
        rows = inspector.logical_lines("var a = [1,\n  2] # c\n## d\nfunc f() -> void:\n\tpass\n")
        self.assertEqual([(row["line"], row["end_line"], row["indent"]) for row in rows],
                         [(1, 2, ""), (4, 4, ""), (5, 5, "\t")])
        self.assertTrue(rows[0]["code"].startswith("var a = [1,") and rows[0]["code"].endswith("2]"))
        self.assertEqual((rows[1]["code"], rows[1]["doc"]), ("func f() -> void:", ["d"]))


class KnownWrongTests(unittest.TestCase):
    def setUp(self):
        self.source = script_text()
        self.parsed = inspector.parse_source(self.source)

    def test_renamed_method_is_refused(self):
        method = next(row for row in self.parsed["methods"] if not row["name"].startswith("_"))
        lines = self.source.split("\n")
        line = lines[method["line"] - 1]
        renamed = re.sub(rf"\bfunc\s+{method['name']}\s*\(", f"func {method['name']}_renamed(", line, count=1)
        self.assertNotEqual(renamed, line)
        lines[method["line"] - 1] = renamed
        problems = inspector.compare_contract(CONTRACT, inspector.parse_source("\n".join(lines)))
        self.assertTrue(any(method["name"] in problem for problem in problems), problems)

    def test_removed_or_added_signal_is_refused(self):
        if self.parsed["signals"]:
            row = self.parsed["signals"][0]
            mutated = drop_lines(self.source, row["line"], row["end_line"])
            expected = f"signals: {row['name']} is in the card but not in the script"
        else:
            mutated = self.source + "\nsignal unexpected_signal(value: int)\n"
            expected = "signals: unexpected_signal is in the script but not in the card"
        self.assertIn(expected, inspector.compare_contract(CONTRACT, inspector.parse_source(mutated)))

    def test_removed_export_or_changed_class_name_is_refused(self):
        renamed = self.source.replace(f"class_name {CONTRACT['class_name']}", "class_name BaltorSomethingElse", 1)
        problems = inspector.compare_contract(CONTRACT, inspector.parse_source(renamed))
        self.assertTrue(any(problem.startswith("class_name:") for problem in problems), problems)
        if self.parsed["exports"]:
            row = self.parsed["exports"][0]
            mutated = drop_lines(self.source, row["line"], row["end_line"])
            self.assertIn(f"exports: {row['name']} is in the card but not in the script",
                          inspector.compare_contract(CONTRACT, inspector.parse_source(mutated)))

    def test_wrong_card_and_changed_byte_are_refused(self):
        wrong = json.loads(json.dumps(CONTRACT))
        wrong["methods"][0]["returns"] = "NotAType"
        wrong["placement"] = "baltor/"
        problems = inspector.compare_contract(wrong, self.parsed)
        self.assertTrue(any(problem.startswith("methods:") for problem in problems), problems)
        self.assertTrue(any(problem.startswith("placement:") for problem in problems), problems)
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / IDENTITY
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / SCRIPT.name).write_text(self.source + "\n# changed\n", encoding="utf-8")
            report = inspector.check_package(copy)
        self.assertIn(f"{SCRIPT.name} does not match its digest in the card", report["problems"])


if __name__ == "__main__":
    unittest.main()
