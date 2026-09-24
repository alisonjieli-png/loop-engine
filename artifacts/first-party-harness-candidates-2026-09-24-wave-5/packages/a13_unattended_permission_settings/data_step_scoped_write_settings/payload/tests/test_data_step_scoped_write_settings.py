"""Effects: runs the package checker with this Python and writes placed copies of the variants inside temporary folders only.

Tests that the Claude Code and OpenCode variants of data-step-scoped-write-settings
hold the policy, that Codex and Gemini CLI settings are reported as not covered,
that the companion names the folders and commands, and that known-wrong variants
fail. Run from the payload root:
    python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = "data_step_scoped_write_settings"
CHECKER = ROOT / "scripts" / "check_data_step_scoped_write_settings.py"
VARIANTS = {"claude_code": "variants/claude_code/settings.json", "opencode": "variants/opencode/opencode.json"}
PLACED = {"claude_code": ".claude/settings.json", "opencode": "opencode.json"}
EXPECTED_COMMANDS = {
    "claude_code": {"ls", "wc", "head", "python3 -I -B .baltor/*", "python3 -I -B .claude/skills/*"},
    "opencode": {"ls", "wc", "head", "python3 -I -B .baltor/*", "python3 -I -B .opencode/skills/*"},
}


def run_checker(*arguments: str, stdin: str | None = None, cwd: Path = ROOT):
    finished = subprocess.run([sys.executable, "-I", "-B", str(CHECKER), *arguments], input=stdin,
                              capture_output=True, text=True, cwd=cwd, timeout=120)
    report = json.loads(finished.stdout) if finished.stdout.strip() else None
    return finished.returncode, report


def load_variant(harness: str):
    return json.loads((ROOT / VARIANTS[harness]).read_text(encoding="utf-8"))


def shell_commands(harness: str, document) -> set:
    commands = set()
    if harness == "claude_code":
        for rule in document["permissions"]["allow"]:
            if rule.startswith("Bash(") and rule.endswith(")"):
                commands.add(rule[5:-1].removesuffix(" *"))
    else:
        for pattern, verb in document["permission"]["bash"].items():
            if verb == "allow":
                commands.add(pattern.removesuffix(" *"))
    return commands


def remove_item(items: list, item: str) -> list:
    return [value for value in items if value != item]


def on_permissions(change):
    def apply(document):
        change(document["permissions"])
        return document
    return apply


def per_tool_denies_without_catch_all(document):
    """Replace OpenCode's "*": "deny" with one deny per tool, which leaves the OpenCode defaults that ask."""
    permission = {key: value for key, value in document["permission"].items() if key != "*"}
    for name in ("edit", "bash", "webfetch", "websearch", "task", "external_directory", "question"):
        permission.setdefault(name, "deny")
    document["permission"] = permission
    return document


# Each known-wrong variant must fail. (harness, name, mutation, text expected in a problem)
KNOWN_WRONG = [
    ("claude_code", "raw data writable",
     on_permissions(lambda p: (p.update(deny=remove_item(p["deny"], "Edit(/data/raw/**)")),
                               p["allow"].append("Edit(/data/**)"))), "edit_raw_data"),
    ("claude_code", "parent paths allowed in commands",
     on_permissions(lambda p: p.update(deny=remove_item(p["deny"], "Bash(*..*)"))), "run_script_from_output"),
    ("claude_code", "python files writable in output",
     on_permissions(lambda p: p.update(deny=remove_item(p["deny"], "Edit(**/*.py)"))), "write_code_into_output"),
    ("claude_code", "any python command", on_permissions(lambda p: p["allow"].append("Bash(python3 *)")),
     "run_inline_code"),
    ("claude_code", "copy allowed", on_permissions(lambda p: p["allow"].append("Bash(cp *)")), "copy_over_raw_file"),
    ("claude_code", "redirection allowed",
     on_permissions(lambda p: p.update(deny=remove_item(p["deny"], "Bash(*>*)"))), "redirect_into_raw"),
    ("opencode", "every file writable", lambda d: d["permission"]["edit"].update({"*": "allow"}) or d,
     "edit_top_level_file"),
    ("opencode", "parent paths allowed in commands", lambda d: d["permission"]["bash"].pop("*..*") and d,
     "run_script_from_output"),
    ("opencode", "python files writable in output", lambda d: d["permission"]["edit"].pop("*.py") and d,
     "write_code_into_output"),
    ("opencode", "any python command", lambda d: d["permission"]["bash"].update({"python3 *": "allow"}) or d,
     "run_inline_code"),
    ("opencode", "raw data writable", lambda d: d["permission"]["edit"].update({"data/raw/*": "allow"}) or d,
     "edit_raw_data"),
    ("opencode", "per-tool denies leave the repeated-call prompt", per_tool_denies_without_catch_all, "catch-all"),
]


class VariantPolicyTests(unittest.TestCase):
    def test_every_variant_holds_the_policy(self):
        for harness, path in VARIANTS.items():
            with self.subTest(harness=harness):
                code, report = run_checker("--harness", harness, "--file", path)
                self.assertEqual(code, 0, report)
                result = report["files"][0]
                self.assertTrue(result["passed"], result["problems"])
                self.assertEqual({item["probe"] for item in result["known_limits"]}, {"script_writes_raw_data"})
                self.assertEqual(result["stale_known_limits"], [])

    def test_placed_workspace_holds_the_policy(self):
        for harness, destination in PLACED.items():
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / VARIANTS[harness]).read_bytes())
                code, report = run_checker("--root", folder)
                self.assertEqual(code, 0, report)

    def test_uncovered_harnesses_are_reported(self):
        for harness, destination, text, marker in (
                ("codex", ".codex/config.toml", 'sandbox_mode = "workspace-write"\n', "whole workspace writable"),
                ("gemini_cli", ".gemini/settings.json", '{"tools": {"core": ["read_file"]}}', "cannot limit")):
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / destination
                target.parent.mkdir(parents=True)
                target.write_text(text, encoding="utf-8")
                code, report = run_checker("--root", folder)
                self.assertEqual(code, 1)
                self.assertIn(marker, report["files"][0]["problems"][0])

    def test_known_wrong_variants_fail(self):
        for harness, name, mutation, marker in KNOWN_WRONG:
            with self.subTest(harness=harness, case=name):
                document = mutation(copy.deepcopy(load_variant(harness)))
                code, report = run_checker("--harness", harness, "--stdin", stdin=json.dumps(document))
                self.assertEqual(code, 1, report)
                problems = report["files"][0]["problems"]
                self.assertTrue(any(marker in problem for problem in problems), problems)


class ConsistencyTests(unittest.TestCase):
    def test_variants_allow_exactly_the_expected_commands(self):
        for harness in VARIANTS:
            with self.subTest(harness=harness):
                self.assertEqual(shell_commands(harness, load_variant(harness)), EXPECTED_COMMANDS[harness])

    def test_companion_names_the_folders_and_commands(self):
        companion = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for text in ("`data/raw/`", "`data/output/`", "`reports/`", "`ls`", "`wc`", "`head`", "`python3 -I -B`",
                     "`.baltor/`", "`..`", "`>`"):
            with self.subTest(text=text):
                self.assertIn(text, companion)

    def test_report_lists_the_writable_paths(self):
        _, report = run_checker("--harness", "opencode", "--file", VARIANTS["opencode"])
        self.assertEqual(report["writable_paths"], ["data/output/", "reports/"])


class RefusedInputTests(unittest.TestCase):
    def test_duplicate_json_key_is_refused(self):
        code, report = run_checker("--harness", "claude_code", "--stdin",
                                   stdin='{"permissions": {"allow": [], "allow": []}}')
        self.assertEqual(code, 2)
        self.assertIn("duplicate", report["refused_input"])

    def test_unknown_opencode_verb_is_refused(self):
        code, report = run_checker("--harness", "opencode", "--stdin", stdin='{"permission": {"edit": "sometimes"}}')
        self.assertEqual(code, 2)
        self.assertIn("unknown verb", report["refused_input"])


if __name__ == "__main__":
    unittest.main()
