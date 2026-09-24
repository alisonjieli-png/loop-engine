"""Effects: runs the package checker with this Python and writes placed copies of the variants inside temporary folders only.

Tests that each variant of deny-env-file-reads-settings refuses environment and
key files and grants nothing, that the refusals survive a merge with a base
policy, that a merge in the wrong key order is caught, and that known-wrong
variants fail. The file names used here are empty examples; no secret value is
written. Run from the payload root:
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
POLICY = "deny_env_file_reads_settings"
NATIVE = POLICY.replace("_", "-")
CHECKER = ROOT / "scripts" / "check_deny_env_file_reads_settings.py"
IGNORE_FILE = "variants/gemini_cli/ignore-patterns.txt"
PLACED_IGNORE_FILE = f".baltor/{NATIVE}/ignore-patterns.txt"
VARIANTS = {"claude_code": "variants/claude_code/settings.json", "opencode": "variants/opencode/opencode.json",
            "gemini_cli": "variants/gemini_cli/settings.json"}
PLACED = {"claude_code": ".claude/settings.json", "opencode": "opencode.json", "gemini_cli": ".gemini/settings.json"}
GEMINI_LIMITS = {"edit_env_file", "create_key_file", "print_env_file", "search_env_file", "print_key_file"}

# Small base policies of the kind this fragment is merged into.
BASES = {
    "claude_code": {"permissions": {"defaultMode": "dontAsk", "allow": ["Read(/**)", "Bash(cat *)", "Bash(grep *)"]}},
    "opencode": {"permission": {"*": "deny", "read": {"*": "allow"}, "edit": {"*": "allow"},
                                "bash": {"*": "deny", "cat *": "allow", "grep *": "allow", "head *": "allow"}}},
    "gemini_cli": {"tools": {"core": ["read_file", "grep_search", "run_shell_command(cat)"]}},
}
# An OpenCode base that opens each tool with its own "*" pattern and has no top-level rule.
OPEN_BASE = {"permission": {"read": {"*": "allow"}, "edit": {"*": "allow"}, "bash": {"*": "allow"}}}


def run_checker(*arguments: str, stdin: str | None = None, cwd: Path = ROOT):
    finished = subprocess.run([sys.executable, "-I", "-B", str(CHECKER), *arguments], input=stdin,
                              capture_output=True, text=True, cwd=cwd, timeout=120)
    report = json.loads(finished.stdout) if finished.stdout.strip() else None
    return finished.returncode, report


def load_variant(harness: str) -> dict:
    return json.loads((ROOT / VARIANTS[harness]).read_text(encoding="utf-8"))


def merge(base, fragment):
    """Merge like a settings host: objects key by key with new keys last, lists as a union."""
    if isinstance(base, dict) and isinstance(fragment, dict):
        merged = dict(base)
        for key, value in fragment.items():
            merged[key] = merge(base[key], value) if key in base else value
        return merged
    if isinstance(base, list) and isinstance(fragment, list):
        return base + [item for item in fragment if item not in base]
    return fragment


def place(folder: str, harness: str, document: dict, ignore_text: str | None = None) -> None:
    target = Path(folder) / PLACED[harness]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document), encoding="utf-8")
    if harness == "gemini_cli":
        ignore = Path(folder) / PLACED_IGNORE_FILE
        ignore.parent.mkdir(parents=True, exist_ok=True)
        ignore.write_text(ignore_text if ignore_text is not None else (ROOT / IGNORE_FILE).read_text(encoding="utf-8"),
                          encoding="utf-8")


def fragment_arguments(harness: str) -> list:
    extra = ["--ignore-file", IGNORE_FILE] if harness == "gemini_cli" else []
    return ["--harness", harness, *extra]


# Each known-wrong variant must fail. (harness, name, mutation, text expected in a problem)
KNOWN_WRONG = [
    ("claude_code", "env reads not refused",
     lambda d: d["permissions"].update(deny=[r for r in d["permissions"]["deny"] if r != "Read(**/.env*)"]) or d,
     "read_env_file"),
    ("claude_code", "fragment grants reads", lambda d: d["permissions"].update(allow=["Read(/**)"]) or d,
     "grants nothing"),
    ("claude_code", "shell may print env files",
     lambda d: d["permissions"].update(deny=[r for r in d["permissions"]["deny"] if r != "Bash(*.env*)"]) or d,
     "print_env_file"),
    ("opencode", "env reads not refused", lambda d: d["permission"]["read"].pop(".env*") and d, "read_env_file"),
    ("opencode", "asks instead of refusing", lambda d: d["permission"]["edit"].update({".env*": "ask"}) or d,
     "grants nothing"),
    ("opencode", "shell may print key files", lambda d: d["permission"]["bash"].pop("*.pem*") and d,
     "print_key_file"),
    ("gemini_cli", "ignore file not named",
     lambda d: d["context"]["fileFiltering"].update(customIgnoreFilePaths=[]) or d, "customIgnoreFilePaths"),
    ("gemini_cli", "ignore files switched off",
     lambda d: d["context"]["fileFiltering"].update(respectGeminiIgnore=False) or d, "respectGeminiIgnore"),
    ("gemini_cli", "fragment changes tools", lambda d: d.update(tools={"core": ["read_file"]}) or d,
     "grants nothing"),
]


class FragmentTests(unittest.TestCase):
    def test_every_variant_refuses_and_grants_nothing(self):
        for harness, path in VARIANTS.items():
            with self.subTest(harness=harness):
                code, report = run_checker(*fragment_arguments(harness), "--file", path)
                self.assertEqual(code, 0, report)
                result = report["files"][0]
                self.assertTrue(result["passed"], result["problems"])
                expected = GEMINI_LIMITS if harness == "gemini_cli" else set()
                self.assertEqual({item["probe"] for item in result["known_limits"]}, expected)
                self.assertEqual(result["stale_known_limits"], [])
                self.assertEqual(report["allowed_commands"], [])

    def test_known_wrong_variants_fail(self):
        for harness, name, mutation, marker in KNOWN_WRONG:
            with self.subTest(harness=harness, case=name):
                document = mutation(copy.deepcopy(load_variant(harness)))
                code, report = run_checker(*fragment_arguments(harness), "--stdin", stdin=json.dumps(document))
                self.assertEqual(code, 1, report)
                problems = report["files"][0]["problems"]
                self.assertTrue(any(marker in problem for problem in problems), problems)

    def test_ignore_file_without_key_patterns_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            place(folder, "gemini_cli", load_variant("gemini_cli"), ignore_text=".env*\n")
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
        self.assertTrue(any("read_pem_file" in problem for problem in report["files"][0]["problems"]))

    def test_missing_ignore_file_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / PLACED["gemini_cli"]
            target.parent.mkdir(parents=True)
            target.write_bytes((ROOT / VARIANTS["gemini_cli"]).read_bytes())
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
        self.assertTrue(any("read_env_file" in problem for problem in report["files"][0]["problems"]))


class CompositionTests(unittest.TestCase):
    def test_refusals_hold_after_a_merge_with_a_base_policy(self):
        for harness in VARIANTS:
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as folder:
                place(folder, harness, merge(BASES[harness], load_variant(harness)))
                code, report = run_checker("--root", folder)
                self.assertEqual(code, 0, report)

    def test_opencode_merge_order_decides_the_result(self):
        fragment = load_variant("opencode")
        with tempfile.TemporaryDirectory() as folder:
            place(folder, "opencode", merge(OPEN_BASE, fragment))  # refusals after the base patterns
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 0, report)
        with tempfile.TemporaryDirectory() as folder:
            place(folder, "opencode", merge(fragment, OPEN_BASE))  # the base's "*" patterns land last
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
        problems = report["files"][0]["problems"]
        for probe in ("read_env_file", "edit_env_file", "print_env_file"):
            self.assertTrue(any(probe in problem for problem in problems), problems)

    def test_claude_refusals_hold_in_either_merge_order(self):
        with tempfile.TemporaryDirectory() as folder:
            place(folder, "claude_code", merge(load_variant("claude_code"), BASES["claude_code"]))
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 0, report)

    def test_codex_settings_are_reported_as_not_covered(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / ".codex" / "config.toml"
            target.parent.mkdir(parents=True)
            target.write_text('sandbox_mode = "read-only"\n', encoding="utf-8")
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
        self.assertIn("deny_read", report["files"][0]["problems"][0])


class ConsistencyTests(unittest.TestCase):
    def test_companion_names_every_refused_name(self):
        companion = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for name in ("`.env`", "`.env.example`", "`.envrc`", "`.pem`", "`.key`", "`.p12`", "`.pfx`"):
            with self.subTest(name=name):
                self.assertIn(name, companion)

    def test_ignore_file_lists_every_pattern(self):
        lines = {line.strip() for line in (ROOT / IGNORE_FILE).read_text(encoding="utf-8").splitlines()}
        self.assertTrue({".env*", "*.pem", "*.key", "*.p12", "*.pfx"} <= lines)

    def test_gemini_settings_name_the_placed_ignore_file(self):
        paths = load_variant("gemini_cli")["context"]["fileFiltering"]["customIgnoreFilePaths"]
        self.assertEqual(paths, [PLACED_IGNORE_FILE])


class RefusedInputTests(unittest.TestCase):
    def test_ignore_file_outside_the_root_is_refused(self):
        code, report = run_checker("--harness", "gemini_cli", "--file", VARIANTS["gemini_cli"],
                                   "--ignore-file", "../ignore-patterns.txt")
        self.assertEqual(code, 2)
        self.assertIn("relative path inside the root", report["refused_input"])

    def test_duplicate_json_key_is_refused(self):
        code, report = run_checker("--harness", "opencode", "--stdin", stdin='{"permission": {"read": {}, "read": {}}}')
        self.assertEqual(code, 2)
        self.assertIn("duplicate", report["refused_input"])


if __name__ == "__main__":
    unittest.main()
