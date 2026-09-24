"""Effects: runs the package checker with this Python and writes placed copies of the variants inside temporary folders only.

Tests that every harness variant of read-only-investigation-settings holds the
policy, that the companion names the same commands, that known-wrong variants
fail, and that any grant outside the policy fails, also after a merge into an
existing settings file. Run from the payload root:
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
POLICY = "read_only_investigation_settings"
CHECKER = ROOT / "scripts" / "check_read_only_investigation_settings.py"
VARIANTS = {"claude_code": "variants/claude_code/settings.json", "codex": "variants/codex/config.toml",
            "opencode": "variants/opencode/opencode.json", "gemini_cli": "variants/gemini_cli/settings.json"}
PLACED = {"claude_code": ".claude/settings.json", "codex": ".codex/config.toml",
          "opencode": "opencode.json", "gemini_cli": ".gemini/settings.json"}
EXPECTED_LIMITS = {"claude_code": {"unlisted_read_command"},
                   "codex": {"run_tests", "unlisted_read_command", "delegate_task"}, "opencode": set(),
                   "gemini_cli": {"git_log_output_option", "git_diff_output_option", "git_show_output_option"}}
# Commands that write, delete or change the checkout. None may be granted by a read-only step.
EXTRA_COMMANDS = ("mv *", "touch *", "git checkout *", "sed *", "find *", "rm *")


def run_checker(*arguments: str, stdin: str | None = None, cwd: Path = ROOT):
    finished = subprocess.run([sys.executable, "-I", "-B", str(CHECKER), *arguments], input=stdin,
                              capture_output=True, text=True, cwd=cwd, timeout=120)
    report = json.loads(finished.stdout) if finished.stdout.strip() else None
    return finished.returncode, report


def load_variant(harness: str):
    text = (ROOT / VARIANTS[harness]).read_text(encoding="utf-8")
    return read_codex(text) if harness == "codex" else json.loads(text)


def read_codex(text: str) -> dict:
    """Read the flat key = "value" form of the Codex variant for mutation."""
    data: dict = {}
    table = data
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("["):
            table = data.setdefault(line.strip("[]"), {})
            continue
        key, _, value = line.partition("=")
        table[key.strip()] = json.loads(value.strip().replace("'", '"'))
    return data


def write_codex(data: dict) -> str:
    lines = [f"{key} = {json.dumps(value)}" for key, value in data.items() if not isinstance(value, dict)]
    for name, table in data.items():
        if isinstance(table, dict):
            lines.append(f"[{name}]")
            lines.extend(f"{key} = {json.dumps(value)}" for key, value in table.items())
    return "\n".join(lines) + "\n"


def serialize(harness: str, document) -> str:
    return write_codex(document) if harness == "codex" else json.dumps(document)


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


def mutate_claude(change):
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


def with_extra_grant(harness: str, document, command: str):
    """Add one allow for a command, where each harness would honour it."""
    if harness == "claude_code":
        document["permissions"]["allow"].append(f"Bash({command})")
    elif harness == "opencode":
        rules = list(document["permission"]["bash"].items())
        head = [item for item in rules if not (item[1] == "deny" and item[0] != "*")]
        tail = [item for item in rules if item[1] == "deny" and item[0] != "*"]
        document["permission"]["bash"] = dict(head + [(command, "allow")] + tail)
    else:
        document["tools"]["core"].append(f"run_shell_command({command.removesuffix(' *')})")
    return document


def union_merge(existing, fragment):
    """Merge like a settings host: objects key by key, lists as a union that keeps existing items first."""
    if isinstance(existing, dict) and isinstance(fragment, dict):
        merged = dict(existing)
        for key, value in fragment.items():
            merged[key] = union_merge(existing[key], value) if key in existing else value
        return merged
    if isinstance(existing, list) and isinstance(fragment, list):
        return existing + [item for item in fragment if item not in existing]
    return fragment


# Each known-wrong variant must fail. (harness, name, mutation, text expected in a problem)
KNOWN_WRONG = [
    ("claude_code", "prompts instead of refusing",
     mutate_claude(lambda p: p.update(defaultMode="default")), "defaultMode"),
    ("claude_code", "allows web fetch",
     mutate_claude(lambda p: (p.update(deny=remove_item(p["deny"], "WebFetch")), p["allow"].append("WebFetch"))),
     "fetch_page"),
    ("claude_code", "allows edits, so a redirection writes a file",
     mutate_claude(lambda p: (p.update(deny=remove_item(p["deny"], "Edit")), p["allow"].append("Edit(/**)"))),
     "redirect_to_file"),
    ("claude_code", "accepts edits, so a redirection writes a file",
     mutate_claude(lambda p: p.update(defaultMode="acceptEdits", deny=remove_item(p["deny"], "Edit"))),
     "redirect_to_file"),
    ("claude_code", "drops the refusal of the git --output option",
     mutate_claude(lambda p: p.update(deny=remove_item(p["deny"], "Bash(git * --output*)"))),
     "git_diff_output_option"),
    ("claude_code", "drops the refusal of git ls-remote, a read-only command that uses the network",
     mutate_claude(lambda p: p.update(deny=remove_item(p["deny"], "Bash(git ls-remote *)"))), "list_remote_refs"),
    ("claude_code", "grants any python command",
     mutate_claude(lambda p: p["allow"].append("Bash(python3 *)")), "does not declare"),
    ("codex", "writable sandbox", lambda d: d.update(sandbox_mode="workspace-write") or d, "edit_source_file"),
    ("codex", "asks for approval", lambda d: d.update(approval_policy="on-request") or d, "approval_policy"),
    ("codex", "live web search", lambda d: d.update(web_search="live") or d, "search_web"),
    ("opencode", "no deny-all base rule",
     lambda d: d["permission"].pop("*") and d, "edit_source_file"),
    ("opencode", "deny-all rule placed last",
     lambda d: d.update(permission={**{k: v for k, v in d["permission"].items() if k != "*"}, "*": "deny"}) or d,
     "read_source_file"),
    ("opencode", "allows web fetch", lambda d: d["permission"].update(webfetch="allow") or d, "fetch_page"),
    ("opencode", "any shell command", lambda d: d["permission"]["bash"].update({"*": "allow"}) or d, "run_tests"),
    ("opencode", "drops the redirection guard", lambda d: d["permission"]["bash"].pop("*>*") and d,
     "redirect_to_file"),
    ("opencode", "per-tool denies leave the repeated-call prompt", per_tool_denies_without_catch_all, "catch-all"),
    ("gemini_cli", "web fetch in the allowlist", lambda d: d["tools"]["core"].append("web_fetch") or d,
     "fetch_page"),
    ("gemini_cli", "any shell command", lambda d: d["tools"]["core"].append("run_shell_command") or d,
     "run_tests"),
    ("gemini_cli", "write tool in the allowlist", lambda d: d["tools"]["core"].append("write_file") or d,
     "create_new_file"),
    ("gemini_cli", "plan mode skips the allowlist",
     lambda d: d["general"].update(defaultApprovalMode="plan") or d, "defaultApprovalMode"),
    ("gemini_cli", "no allowlist", lambda d: d["tools"].pop("core") and d, "tools.core"),
]


class VariantPolicyTests(unittest.TestCase):
    def test_every_variant_holds_the_policy(self):
        for harness, path in VARIANTS.items():
            with self.subTest(harness=harness):
                code, report = run_checker("--harness", harness, "--file", path)
                self.assertEqual(code, 0, report)
                result = report["files"][0]
                self.assertTrue(result["passed"], result["problems"])
                self.assertEqual(result["stale_known_limits"], [])
                self.assertEqual({item["probe"] for item in result["known_limits"]}, EXPECTED_LIMITS[harness])
                self.assertEqual(result["not_modeled"], [])

    def test_placed_workspace_holds_the_policy(self):
        for harness, destination in PLACED.items():
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / VARIANTS[harness]).read_bytes())
                code, report = run_checker("--root", folder)
                self.assertEqual(code, 0, report)
                self.assertEqual([item["harness"] for item in report["files"]], [harness])

    def test_empty_workspace_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
        self.assertFalse(report["passed"])
        self.assertIn("no harness settings file", report["problem"])

    def test_known_wrong_variants_fail(self):
        for harness, name, mutation, marker in KNOWN_WRONG:
            with self.subTest(harness=harness, case=name):
                document = mutation(copy.deepcopy(load_variant(harness)))
                code, report = run_checker("--harness", harness, "--stdin", stdin=serialize(harness, document))
                self.assertEqual(code, 1, report)
                problems = report["files"][0]["problems"]
                self.assertTrue(any(marker in problem for problem in problems), problems)

    def test_codex_subset_reader_agrees_with_the_default_reader(self):
        _, default = run_checker("--harness", "codex", "--file", VARIANTS["codex"])
        code, subset = run_checker("--harness", "codex", "--file", VARIANTS["codex"], "--toml-reader", "subset")
        self.assertEqual(code, 0, subset)
        self.assertEqual(default["files"][0]["decisions"], subset["files"][0]["decisions"])

    def test_claude_code_rules_never_see_a_redirection(self):
        document = load_variant("claude_code")
        document["permissions"]["deny"].append("Bash(*>*)")  # the harness removes redirections before matching
        code, report = run_checker("--harness", "claude_code", "--stdin", stdin=json.dumps(document))
        self.assertEqual(code, 0, report)
        decisions = report["files"][0]["decisions"]
        self.assertEqual(decisions["merge_error_stream"], "allow")
        self.assertEqual(decisions["redirect_to_file"], "deny")  # refused by the check of the redirection target


class ExtraGrantTests(unittest.TestCase):
    def test_any_extra_grant_fails(self):
        for harness in ("claude_code", "opencode", "gemini_cli"):
            for command in EXTRA_COMMANDS:
                with self.subTest(harness=harness, command=command):
                    document = with_extra_grant(harness, load_variant(harness), command)
                    code, report = run_checker("--harness", harness, "--stdin", stdin=json.dumps(document))
                    self.assertEqual(code, 1, report)
                    self.assertTrue(any("does not declare" in problem for problem in report["files"][0]["problems"]))

    def test_a_merge_into_an_existing_file_that_granted_more_fails(self):
        existing = {"claude_code": {"permissions": {"allow": ["Bash(git checkout *)"]}},
                    "opencode": {"permission": {"*": "deny", "bash": {"*": "deny", "git checkout *": "allow"}}},
                    "gemini_cli": {"tools": {"core": ["run_shell_command(git checkout)"]}}}
        for harness, before in existing.items():
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / PLACED[harness]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(union_merge(before, load_variant(harness))), encoding="utf-8")
                code, report = run_checker("--root", folder)
                self.assertEqual(code, 1, report)
                self.assertTrue(any("does not declare" in problem for problem in report["files"][0]["problems"]))


class ConsistencyTests(unittest.TestCase):
    def test_variants_allow_exactly_the_declared_commands(self):
        _, report = run_checker("--harness", "claude_code", "--file", VARIANTS["claude_code"])
        declared = set(report["allowed_commands"])
        for harness in ("claude_code", "opencode", "gemini_cli"):
            with self.subTest(harness=harness):
                self.assertEqual(shell_commands(harness, load_variant(harness)), declared)

    def test_companion_names_every_declared_command_and_the_redirection_forms(self):
        _, report = run_checker("--harness", "opencode", "--file", VARIANTS["opencode"])
        companion = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for text in [f"`{command}`" for command in report["allowed_commands"]] + ["`>`", "`2>&1`", "`|`", "`&&`"]:
            with self.subTest(text=text):
                self.assertIn(text, companion)


class RefusedInputTests(unittest.TestCase):
    def test_duplicate_json_key_is_refused(self):
        code, report = run_checker("--harness", "claude_code", "--stdin",
                                   stdin='{"permissions": {}, "permissions": {}}')
        self.assertEqual(code, 2)
        self.assertIn("duplicate", report["refused_input"])

    def test_path_outside_the_root_is_refused(self):
        code, report = run_checker("--harness", "opencode", "--file", "../outside.json")
        self.assertEqual(code, 2)
        self.assertIn("relative path inside the root", report["refused_input"])

    def test_invalid_toml_is_refused(self):
        code, report = run_checker("--harness", "codex", "--stdin", stdin="sandbox_mode = \n")
        self.assertEqual(code, 2)
        self.assertIn("TOML", report["refused_input"])

    def test_oversized_input_is_refused(self):
        code, report = run_checker("--harness", "claude_code", "--stdin", stdin=" " * (1024 * 1024 + 1))
        self.assertEqual(code, 2)
        self.assertIn("1 MiB", report["refused_input"])

    def test_stdin_needs_a_harness(self):
        code, report = run_checker("--stdin", stdin="{}")
        self.assertEqual(code, 2)
        self.assertIn("--harness", report["refused_input"])


if __name__ == "__main__":
    unittest.main()
