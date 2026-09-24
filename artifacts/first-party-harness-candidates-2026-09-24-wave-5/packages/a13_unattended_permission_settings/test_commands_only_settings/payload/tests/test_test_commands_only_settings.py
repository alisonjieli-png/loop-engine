"""Effects: runs the package checker with this Python and writes placed copies of the variants inside temporary folders only.

Tests that every harness variant of test-commands-only-settings holds the
policy, that a Codex settings file is reported as not covered, that the
companion names the same commands, and that known-wrong variants fail. Run from
the payload root:
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
POLICY = "test_commands_only_settings"
CHECKER = ROOT / "scripts" / "check_test_commands_only_settings.py"
VARIANTS = {"claude_code": "variants/claude_code/settings.json", "opencode": "variants/opencode/opencode.json",
            "gemini_cli": "variants/gemini_cli/settings.json"}
PLACED = {"claude_code": ".claude/settings.json", "opencode": "opencode.json", "gemini_cli": ".gemini/settings.json"}


def run_checker(*arguments: str, stdin: str | None = None, cwd: Path = ROOT):
    finished = subprocess.run([sys.executable, "-I", "-B", str(CHECKER), *arguments], input=stdin,
                              capture_output=True, text=True, cwd=cwd, timeout=120)
    report = json.loads(finished.stdout) if finished.stdout.strip() else None
    return finished.returncode, report


def load_variant(harness: str):
    return json.loads((ROOT / VARIANTS[harness]).read_text(encoding="utf-8"))


def shell_commands(harness: str, document) -> set:
    """Return the command prefixes a variant allows, normalized to the typed command."""
    commands = set()
    if harness == "claude_code":
        for rule in document["permissions"]["allow"]:
            if rule.startswith("Bash(") and rule.endswith(")"):
                commands.add(rule[5:-1].removesuffix(" *"))
    elif harness == "opencode":
        for pattern, verb in document["permission"]["bash"].items():
            if verb == "allow":
                commands.add(pattern.removesuffix(" *"))
    elif harness == "gemini_cli":
        for entry in document["tools"]["core"]:
            if entry.startswith("run_shell_command(") and entry.endswith(")"):
                commands.add(entry[len("run_shell_command("):-1])
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
    ("claude_code", "formatter may rewrite files",
     on_permissions(lambda p: p["allow"].append("Bash(ruff format *)")), "apply_ruff_format"),
    ("claude_code", "git allowed", on_permissions(lambda p: p["allow"].append("Bash(git *)")), "git_status"),
    ("claude_code", "edits allowed",
     on_permissions(lambda p: (p.update(deny=remove_item(p["deny"], "Edit")), p["allow"].append("Edit(/**)"))),
     "edit_source_file"),
    ("claude_code", "redirection allowed",
     on_permissions(lambda p: p.update(deny=remove_item(p["deny"], "Bash(*>*)"))), "redirect_output"),
    ("claude_code", "prompts instead of refusing", on_permissions(lambda p: p.update(defaultMode="default")),
     "defaultMode"),
    ("opencode", "formatter may rewrite files",
     lambda d: d["permission"]["bash"].update({"ruff format *": "allow"}) or d, "apply_ruff_format"),
    ("opencode", "edits allowed", lambda d: d["permission"].update(edit="allow") or d, "edit_source_file"),
    ("opencode", "redirection allowed", lambda d: d["permission"]["bash"].pop("*>*") and d, "redirect_output"),
    ("opencode", "any command", lambda d: d["permission"]["bash"].update({"*": "allow"}) or d, "run_other_script"),
    ("opencode", "per-tool denies leave the repeated-call prompt", per_tool_denies_without_catch_all, "catch-all"),
    ("gemini_cli", "formatter may rewrite files",
     lambda d: d["tools"]["core"].append("run_shell_command(ruff format)") or d, "apply_ruff_format"),
    ("gemini_cli", "edit tool allowed", lambda d: d["tools"]["core"].append("replace") or d, "edit_source_file"),
    ("gemini_cli", "git allowed", lambda d: d["tools"]["core"].append("run_shell_command(git)") or d, "git_status"),
    ("gemini_cli", "yolo not blocked", lambda d: d["security"].update(disableYoloMode=False) or d,
     "disableYoloMode"),
]


class VariantPolicyTests(unittest.TestCase):
    def test_every_variant_holds_the_policy(self):
        for harness, path in VARIANTS.items():
            with self.subTest(harness=harness):
                code, report = run_checker("--harness", harness, "--file", path)
                self.assertEqual(code, 0, report)
                result = report["files"][0]
                self.assertTrue(result["passed"], result["problems"])
                self.assertEqual(result["known_limits"], [])
                self.assertEqual(result["stale_known_limits"], [])

    def test_placed_workspace_holds_the_policy(self):
        for harness, destination in PLACED.items():
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / VARIANTS[harness]).read_bytes())
                code, report = run_checker("--root", folder)
                self.assertEqual(code, 0, report)

    def test_codex_settings_are_reported_as_not_covered(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / ".codex" / "config.toml"
            target.parent.mkdir(parents=True)
            target.write_text('sandbox_mode = "read-only"\napproval_policy = "never"\n', encoding="utf-8")
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
        self.assertIn("cannot refuse a command by name", report["files"][0]["problems"][0])

    def test_known_wrong_variants_fail(self):
        for harness, name, mutation, marker in KNOWN_WRONG:
            with self.subTest(harness=harness, case=name):
                document = mutation(copy.deepcopy(load_variant(harness)))
                code, report = run_checker("--harness", harness, "--stdin", stdin=json.dumps(document))
                self.assertEqual(code, 1, report)
                problems = report["files"][0]["problems"]
                self.assertTrue(any(marker in problem for problem in problems), problems)


class ConsistencyTests(unittest.TestCase):
    def test_variants_allow_exactly_the_declared_commands(self):
        _, report = run_checker("--harness", "claude_code", "--file", VARIANTS["claude_code"])
        declared = set(report["allowed_commands"])
        for harness in VARIANTS:
            with self.subTest(harness=harness):
                self.assertEqual(shell_commands(harness, load_variant(harness)), declared)

    def test_companion_names_every_declared_command(self):
        _, report = run_checker("--harness", "gemini_cli", "--file", VARIANTS["gemini_cli"])
        companion = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for command in report["allowed_commands"]:
            with self.subTest(command=command):
                self.assertIn(f"`{command}`", companion)


class RefusedInputTests(unittest.TestCase):
    def test_duplicate_json_key_is_refused(self):
        code, report = run_checker("--harness", "opencode", "--stdin", stdin='{"permission": {}, "permission": {}}')
        self.assertEqual(code, 2)
        self.assertIn("duplicate", report["refused_input"])

    def test_non_object_document_is_refused(self):
        code, report = run_checker("--harness", "claude_code", "--stdin", stdin="[]")
        self.assertEqual(code, 2)
        self.assertIn("not a JSON object", report["refused_input"])


if __name__ == "__main__":
    unittest.main()
