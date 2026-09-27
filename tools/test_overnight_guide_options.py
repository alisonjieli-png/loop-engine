"""Every engine option the overnight local-model guide names is one the engine's command line defines.

docs/guides/overnight-solving-on-local-models.md told readers to turn on `--allow-sandbox-commands` for generated
code. No parser of this repository has ever defined that option: typing it ends the command with "unrecognized
arguments". What it stood for is not an option at all: a solve writes in its workspace and runs sandboxed commands
when the settings file's `operating.construction_and_execution_mode` is `sandbox_generate` (the default) or
`promotion_authorized`. The September 27, 2026 audit of the September 23 branch archive found the defect still on
main; the archive's full rework of the guide waits for its own builder, and this check holds the one rule now.

The rule reads the guide itself: every option written in an inline code span, and every option of a `loop-engine`
command in a `bash` block, must be declared by an `add_argument` call somewhere in src/loop_engine. The set of
declared options is read from the source with the ast module; nothing is run, parsed as a command or sent anywhere.
A known-wrong control plants the old sentence back and an invented option beside it.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import shlex
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guides" / "overnight-solving-on-local-models.md"
SOURCE = ROOT / "src" / "loop_engine"
INLINE_OPTION = re.compile(r"`(--[a-z0-9][a-z0-9-]*)(?:[ =][^`]*)?`")
FENCE = re.compile(r"^```([A-Za-z0-9_-]*)\n(.*?)^```", re.M | re.S)
#: A floor on the options the rule must find, so a guide whose spans stopped matching cannot pass by checking nothing.
MINIMUM_OPTIONS = 10


def declared_options(source: Path = SOURCE) -> set:
    """Every option string an `add_argument` call in the package declares."""
    found = set()
    for path in sorted(source.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"):
                found.update(argument.value for argument in node.args
                             if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
                             and argument.value.startswith("--"))
    return found


def named_options(text: str) -> set:
    """The options the guide names: inline code spans, and the options of each `loop-engine` command it prints."""
    options = set(INLINE_OPTION.findall(text))
    for language, body in ((match.group(1), match.group(2)) for match in FENCE.finditer(text)):
        if language != "bash":
            continue
        for line in body.replace("\\\n", " ").splitlines():
            words = shlex.split(line, comments=True)
            if words[:1] == ["loop-engine"]:
                options.update(word.split("=", 1)[0] for word in words[1:] if word.startswith("--"))
    return options


def undefined_options(text: str, declared: set) -> list:
    return sorted(option for option in named_options(text) if option not in declared)


class OvernightGuideOptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = GUIDE.read_text(encoding="utf-8")
        cls.declared = declared_options()

    def test_every_option_the_guide_names_is_declared(self):
        self.assertGreaterEqual(len(named_options(self.text)), MINIMUM_OPTIONS)
        self.assertEqual(undefined_options(self.text, self.declared), [])

    def test_the_guide_says_where_the_sandbox_authority_comes_from(self):
        self.assertIn("operating.construction_and_execution_mode", self.text)
        self.assertNotIn("--allow-sandbox-commands", self.text)

    def test_the_declared_options_are_read_from_the_real_parsers(self):
        for option in ("--authorize-model-calls", "--allow-local-execution", "--allow-model-failover",
                       "--unattended", "--workspace", "--max-model-calls"):
            self.assertIn(option, self.declared)

    def test_known_wrong_the_old_sentence_and_an_invented_option_are_found(self):
        planted = self.text + ("\nThree more are off by default: `--allow-sandbox-commands` for generated code.\n"
                               "\n```bash\nloop-engine solve --text \"x\" --invented-night-option\n```\n")
        self.assertEqual(undefined_options(planted, self.declared),
                         ["--allow-sandbox-commands", "--invented-night-option"])


if __name__ == "__main__":
    unittest.main()
