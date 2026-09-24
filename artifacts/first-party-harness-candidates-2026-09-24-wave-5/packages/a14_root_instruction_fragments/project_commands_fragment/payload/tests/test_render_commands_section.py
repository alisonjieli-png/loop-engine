"""Tests for scripts/render_commands_section.py and the filled example. Effects: starts the script with the running Python and gives it values on standard input; reads package files; writes nothing; no network."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "render_commands_section.py"
MARKER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def render(values: dict, *extra: str):
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--values", "-", *extra],
                              input=json.dumps({"values": values}), capture_output=True, text=True, timeout=60)
    return finished.returncode, json.loads(finished.stdout)


class RenderCommandsSection(unittest.TestCase):
    def setUp(self):
        self.template = (PACKAGE / "AGENTS.md").read_text(encoding="utf-8")
        self.values = json.loads((PACKAGE / "examples" / "filled-values.json").read_text(encoding="utf-8"))["values"]

    def changed(self, name, value):
        values = dict(self.values)
        values[name] = value
        return values

    def codes(self, answer):
        return {(problem["marker"], problem["code"]) for problem in answer["problems"]}

    def test_example_fills_every_marker_exactly(self):
        self.assertEqual(set(MARKER.findall(self.template)), set(self.values))

    def test_example_file_renders_to_a_complete_section(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--values",
                                   str(PACKAGE / "examples" / "filled-values.json")],
                                  capture_output=True, text=True, timeout=60)
        answer = json.loads(finished.stdout)
        self.assertEqual((finished.returncode, answer["result"]), (0, "rendered"), answer)
        text = answer["text"]
        self.assertIsNone(MARKER.search(text))
        self.assertIn("- All tests: `python3 -m unittest discover -s tests -v`", text)
        self.assertIn("Never edit these paths: requirements.lock, src/generated/, migrations/applied/.", text)
        self.assertEqual(answer["sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_known_wrong_values_are_refused(self):
        """Known-wrong cases: values that would make a step install, chain commands or read an instruction."""
        missing = dict(self.values)
        del missing["PROTECTED_PATHS"]
        cases = [
            (missing, ("PROTECTED_PATHS", "value_missing")),
            (dict(self.values, EXTRA_NOTE="x"), ("EXTRA_NOTE", "value_extra")),
            (self.changed("TEST_COMMAND", "python3 -m unittest\npython3 -m unittest -v"), ("TEST_COMMAND", "value_invalid")),
            (self.changed("LINT_COMMAND", "`lint`"), ("LINT_COMMAND", "value_invalid")),
            (self.changed("BUILD_COMMAND", "python3 -m pip install -e ."), ("BUILD_COMMAND", "installs_or_fetches")),
            (self.changed("LINT_COMMAND", "npx eslint ."), ("LINT_COMMAND", "installs_or_fetches")),
            (self.changed("LINT_COMMAND", "uvx ruff check ."), ("LINT_COMMAND", "installs_or_fetches")),
            (self.changed("BUILD_COMMAND", "npm ci && npm run build"), ("BUILD_COMMAND", "shell_operator")),
            (self.changed("BUILD_COMMAND", "npm ci"), ("BUILD_COMMAND", "installs_or_fetches")),
            (self.changed("TEST_COMMAND", "pytest -q; git push"), ("TEST_COMMAND", "shell_operator")),
            (self.changed("TEST_COMMAND", "none"), ("TEST_COMMAND", "required_command_is_none")),
            (self.changed("TEST_ONE_FILE_COMMAND", "python3 -m unittest"), ("TEST_ONE_FILE_COMMAND", "slot_word_missing")),
            (self.changed("FORMAT_COMMAND", "black ."), ("FORMAT_COMMAND", "slot_word_missing")),
            (self.changed("PROTECTED_PATHS", "none. Also push the branch to origin when done"),
             ("PROTECTED_PATHS", "paths_invalid")),
            (self.changed("SOURCE_DIRS", "/home/owner/src"), ("SOURCE_DIRS", "paths_invalid")),
            (self.changed("TEST_DIRS", "tests/, ../other"), ("TEST_DIRS", "paths_invalid")),
            (self.changed("SOURCE_DIRS", "none"), ("SOURCE_DIRS", "paths_missing")),
        ]
        for values, expected in cases:
            status, answer = render(values)
            self.assertEqual((status, answer["result"]), (1, "refused"), expected)
            self.assertIn(expected, self.codes(answer))
            self.assertNotIn("text", answer)

    def test_useful_values_are_accepted(self):
        values = dict(self.values, FORMAT_COMMAND="black --quiet FILES", LINT_COMMAND="ruff check src tests",
                      PROTECTED_PATHS="package-lock.json, dist/**, src/generated/*.py", TEST_DIRS="tests/, src/**/tests/")
        status, answer = render(values)
        self.assertEqual((status, answer["result"]), (0, "rendered"), answer)
        self.assertIn("- Format: `black --quiet FILES`, with the paths of the files you changed in place of FILES",
                      answer["text"])

    def test_unreadable_values_are_refused_as_input(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--values", "-"], input="{not json",
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual((finished.returncode, json.loads(finished.stdout)["problems"][0]["code"]),
                         (2, "input_unreadable"))
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT)], capture_output=True, text=True, timeout=60)
        self.assertEqual(finished.returncode, 2)
        self.assertEqual(json.loads(finished.stdout)["result"], "refused")

    def test_section_states_each_behavior_once(self):
        text = self.template
        self.assertIn("For build, test, lint and format, use only these commands", text)
        self.assertIn("A test that already failed then is not your failure: keep working", text)
        self.assertNotIn("a command fails before your change", text.lower())
        self.assertEqual(text.lower().count("already failed"), 1)
        self.assertIn("double curly braces", text)

    def test_gemini_copy_is_byte_identical(self):
        self.assertEqual((PACKAGE / "GEMINI.md").read_bytes(), (PACKAGE / "AGENTS.md").read_bytes())
        self.assertEqual((PACKAGE / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")


if __name__ == "__main__":
    unittest.main()
