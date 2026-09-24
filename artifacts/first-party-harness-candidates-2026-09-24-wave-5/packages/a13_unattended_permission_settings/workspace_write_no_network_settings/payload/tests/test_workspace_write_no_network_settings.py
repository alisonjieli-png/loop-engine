"""Effects: runs the package checker with this Python and writes placed copies of the variants inside temporary folders only.

Tests that every harness variant of workspace-write-no-network-settings holds
the policy, that an OpenCode settings file is reported as not covered, that the
companion names the same commands and folders, that known-wrong variants fail,
and that any grant outside the policy fails, also after a merge into an existing
settings file. Run from the payload root:
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
POLICY = "workspace_write_no_network_settings"
CHECKER = ROOT / "scripts" / "check_workspace_write_no_network_settings.py"
VARIANTS = {"claude_code": "variants/claude_code/settings.json", "codex": "variants/codex/config.toml",
            "gemini_cli": "variants/gemini_cli/settings.json"}
PLACED = {"claude_code": ".claude/settings.json", "codex": ".codex/config.toml", "gemini_cli": ".gemini/settings.json"}
PROTECTED_EDITS = {"edit_git_metadata", "edit_claude_settings", "edit_codex_settings", "edit_opencode_settings",
                   "edit_gemini_settings", "edit_package_checker"}
EXPECTED_LIMITS = {
    "claude_code": {"unlisted_read_command"},
    "codex": PROTECTED_EDITS | {"redirect_into_settings", "test_code_writes_settings", "run_other_script",
                                "unlisted_read_command", "delegate_task"},
    "gemini_cli": PROTECTED_EDITS | {"test_code_writes_settings"},
}
# Commands outside the policy. None may be granted by a fix step.
EXTRA_COMMANDS = ("rm *", "git checkout *", "npm *", "python3 *", "git push *")


def run_checker(*arguments: str, stdin: str | None = None, cwd: Path = ROOT):
    finished = subprocess.run([sys.executable, "-I", "-B", str(CHECKER), *arguments], input=stdin,
                              capture_output=True, text=True, cwd=cwd, timeout=120)
    report = json.loads(finished.stdout) if finished.stdout.strip() else None
    return finished.returncode, report


def load_variant(harness: str):
    text = (ROOT / VARIANTS[harness]).read_text(encoding="utf-8")
    return read_codex(text) if harness == "codex" else json.loads(text)


def read_codex(text: str) -> dict:
    """Read the flat key = value form of the Codex variant for mutation."""
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
        table[key.strip()] = json.loads(value.strip())
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
    elif harness == "gemini_cli":
        for entry in document["tools"]["core"]:
            if entry.startswith("run_shell_command(") and entry.endswith(")"):
                commands.add(entry[len("run_shell_command("):-1])
    return commands


def remove_item(items: list, item: str) -> list:
    return [value for value in items if value != item]


def mutate_claude(change):
    def apply(document):
        change(document)
        return document
    return apply


def with_extra_grant(harness: str, document, command: str):
    if harness == "claude_code":
        document["permissions"]["allow"].append(f"Bash({command})")
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
     mutate_claude(lambda d: d["permissions"].update(defaultMode="acceptEdits")), "defaultMode"),
    ("claude_code", "sandbox switched off",
     mutate_claude(lambda d: d["sandbox"].update(enabled=False)), "test_code_network"),
    ("claude_code", "sandboxed commands allowed without a rule",
     mutate_claude(lambda d: d["sandbox"].update(autoAllowBashIfSandboxed=True)), "run_other_script"),
    ("claude_code", "network domains opened",
     mutate_claude(lambda d: d["sandbox"]["network"].update(allowedDomains=["*"])), "sandbox must set"),
    ("claude_code", "escape from the sandbox allowed",
     mutate_claude(lambda d: d["sandbox"].update(allowUnsandboxedCommands=True)), "sandbox must set"),
    ("claude_code", "a command excluded from the sandbox",
     mutate_claude(lambda d: d["sandbox"].update(excludedCommands=["python3"])), "excludedCommands"),
    ("claude_code", "harness settings editable",
     mutate_claude(lambda d: d["permissions"].update(deny=remove_item(d["permissions"]["deny"], "Edit(/.claude/**)"))),
     "edit_claude_settings"),
    ("claude_code", "harness settings writable by a redirection",
     mutate_claude(lambda d: d["permissions"].update(deny=remove_item(d["permissions"]["deny"], "Edit(/.claude/**)"))),
     "redirect_into_settings"),
    ("claude_code", "drops the refusal of git ls-remote, a read-only command that uses the network",
     mutate_claude(lambda d: d["permissions"].update(deny=remove_item(d["permissions"]["deny"],
                                                                      "Bash(git ls-remote *)"))),
     "list_remote_refs"),
    ("claude_code", "opens a folder outside the workspace",
     mutate_claude(lambda d: d["permissions"].update(additionalDirectories=["/srv/data"])), "additionalDirectories"),
    ("codex", "network opened", lambda d: d["sandbox_workspace_write"].update(network_access=True) or d, "download"),
    ("codex", "full access sandbox", lambda d: d.update(sandbox_mode="danger-full-access") or d,
     "edit_outside_workspace"),
    ("codex", "asks for approval", lambda d: d.update(approval_policy="on-failure") or d, "approval_policy"),
    ("codex", "extra writable root", lambda d: d["sandbox_workspace_write"].update(writable_roots=["/srv"]) or d,
     "writable_roots"),
    ("gemini_cli", "web fetch in the allowlist", lambda d: d["tools"]["core"].append("web_fetch") or d,
     "fetch_page"),
    ("gemini_cli", "any shell command", lambda d: d["tools"]["core"].append("run_shell_command") or d,
     "run_other_script"),
    ("gemini_cli", "confirmation prompt", lambda d: d["tools"].update(confirmationRequired=["replace"]) or d,
     "confirmationRequired"),
    ("gemini_cli", "auto edit mode", lambda d: d["general"].update(defaultApprovalMode="auto_edit") or d,
     "defaultApprovalMode"),
    ("gemini_cli", "tool sandbox switched off", lambda d: d["security"].update(toolSandboxing=False) or d,
     "test_code_network"),
    ("gemini_cli", "network opened to the tool sandbox", lambda d: d["tools"].update(sandboxNetworkAccess=True) or d,
     "sandboxNetworkAccess"),
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

    def test_placed_workspace_holds_the_policy(self):
        for harness, destination in PLACED.items():
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / VARIANTS[harness]).read_bytes())
                code, report = run_checker("--root", folder)
                self.assertEqual(code, 0, report)
                self.assertEqual([item["harness"] for item in report["files"]], [harness])

    def test_opencode_settings_are_reported_as_not_covered(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "opencode.json").write_text('{"permission": {"*": "deny"}}', encoding="utf-8")
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
        self.assertIn("no process sandbox", report["files"][0]["problems"][0])

    def test_empty_workspace_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            code, report = run_checker("--root", folder)
        self.assertEqual(code, 1)
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


class ExtraGrantTests(unittest.TestCase):
    def test_any_extra_grant_fails(self):
        for harness in ("claude_code", "gemini_cli"):
            for command in EXTRA_COMMANDS:
                with self.subTest(harness=harness, command=command):
                    document = with_extra_grant(harness, load_variant(harness), command)
                    code, report = run_checker("--harness", harness, "--stdin", stdin=json.dumps(document))
                    self.assertEqual(code, 1, report)
                    self.assertTrue(any("does not declare" in problem for problem in report["files"][0]["problems"]))

    def test_a_merge_into_an_existing_file_that_granted_more_fails(self):
        existing = {"claude_code": {"permissions": {"allow": ["Bash(npm *)"]}},
                    "gemini_cli": {"tools": {"core": ["run_shell_command(npm)"]}}}
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
        for harness in ("claude_code", "gemini_cli"):
            with self.subTest(harness=harness):
                self.assertEqual(shell_commands(harness, load_variant(harness)), declared)

    def test_companion_names_every_declared_command_and_the_redirection_forms(self):
        _, report = run_checker("--harness", "claude_code", "--file", VARIANTS["claude_code"])
        companion = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for text in [f"`{command}`" for command in report["allowed_commands"]] + ["`>`", "`2>&1`", "`|`", "`&&`"]:
            with self.subTest(text=text):
                self.assertIn(text, companion)

    def test_companion_names_every_protected_folder(self):
        companion = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for name in (".git", ".claude", ".codex", ".gemini", ".opencode", ".baltor", "opencode.json"):
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", companion)


class RefusedInputTests(unittest.TestCase):
    def test_duplicate_json_key_is_refused(self):
        code, report = run_checker("--harness", "gemini_cli", "--stdin", stdin='{"tools": {}, "tools": {}}')
        self.assertEqual(code, 2)
        self.assertIn("duplicate", report["refused_input"])

    def test_path_outside_the_root_is_refused(self):
        code, report = run_checker("--harness", "claude_code", "--file", "../settings.json")
        self.assertEqual(code, 2)
        self.assertIn("relative path inside the root", report["refused_input"])

    def test_repeated_toml_table_is_refused_by_the_subset_reader(self):
        text = "[sandbox_workspace_write]\nnetwork_access = false\n[sandbox_workspace_write]\n"
        code, report = run_checker("--harness", "codex", "--stdin", "--toml-reader", "subset", stdin=text)
        self.assertEqual(code, 2)
        self.assertIn("repeated table", report["refused_input"])


if __name__ == "__main__":
    unittest.main()
