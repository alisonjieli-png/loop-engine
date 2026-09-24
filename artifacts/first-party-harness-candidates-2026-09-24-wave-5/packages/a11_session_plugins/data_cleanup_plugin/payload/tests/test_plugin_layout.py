"""Consistency tests across the Claude Code plugin and the Gemini CLI extension variants."""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ROOT / "variants"
NAME = "data-cleanup-plugin"
RISKS = ["merges_distinct_values", "drops_rows", "changes_source_file", "ambiguous_format", "no_example",
         "order_dependent", "not_reversible"]


def toml_strings(path: Path) -> dict:
    """Read the two top-level strings of a command file without tomllib, which Python 3.10 lacks."""
    text = path.read_text(encoding="utf-8")
    description = re.search(r'^description = "([^"\n]*)"$', text, re.MULTILINE)
    prompt = re.search(r"^prompt = '''\n(.*?)'''$", text, re.MULTILINE | re.DOTALL)
    return {"description": description.group(1), "prompt": prompt.group(1)}


def headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("## ")]


def body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("\n---\n", 1)[1]


class PluginLayoutTests(unittest.TestCase):
    def test_manifests_name_the_same_plugin_and_version(self):
        claude = json.loads((VARIANTS / "claude_code" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        gemini = json.loads((VARIANTS / "gemini_cli" / "gemini-extension.json").read_text(encoding="utf-8"))
        self.assertEqual((claude["name"], claude["version"], claude["license"]), (NAME, "0.1.0", "MIT"))
        self.assertEqual((gemini["name"], gemini["version"]), (NAME, "0.1.0"))
        self.assertRegex(gemini["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_hooks_run_the_packaged_script_after_file_writes(self):
        claude = json.loads((VARIANTS / "claude_code" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entry = claude["hooks"]["PostToolUse"][0]
        self.assertEqual(entry["matcher"], "Write|Edit")
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/scripts/check_cleaned_counts.py" --harness claude_code',
                      entry["hooks"][0]["command"])
        gemini = json.loads((VARIANTS / "gemini_cli" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entry = gemini["hooks"]["AfterTool"][0]
        self.assertEqual(entry["matcher"], "write_file|replace")
        self.assertIn('"${extensionPath}/scripts/check_cleaned_counts.py" --harness gemini_cli',
                      entry["hooks"][0]["command"])
        self.assertGreaterEqual(entry["hooks"][0]["timeout"], 1000, "Gemini CLI timeouts are milliseconds")
        self.assertTrue((ROOT / "scripts" / "check_cleaned_counts.py").is_file())

    def test_status_command_has_the_same_body_in_both_variants(self):
        claude = body(VARIANTS / "claude_code" / "commands" / "cleanup-status.md")
        gemini = toml_strings(VARIANTS / "gemini_cli" / "commands" / "cleanup-status.toml")
        self.assertEqual(headings(claude), headings(gemini["prompt"]))
        self.assertEqual(claude.strip(), gemini["prompt"].strip())
        for text in (claude, gemini["prompt"]):
            # The Markdown and TOML bodies name the placed path; only hook files use a root variable.
            self.assertIn(f".baltor/plugins/{NAME}/scripts/check_cleaned_counts.py --all", text)
            self.assertNotIn("PLUGIN_ROOT", text)
            self.assertNotIn("extensionPath", text)

    def test_critic_is_read_only_and_uses_the_same_risk_names(self):
        claude = (VARIANTS / "claude_code" / "agents" / "cleaning-rule-critic.md").read_text(encoding="utf-8")
        gemini = (VARIANTS / "gemini_cli" / "agents" / "cleaning-rule-critic.md").read_text(encoding="utf-8")
        tools = re.search(r"^tools: (.*)$", claude, re.MULTILINE).group(1)
        self.assertEqual({tool.strip() for tool in tools.split(",")}, {"Read", "Grep", "Glob"})
        listed = re.findall(r"^  - ([a-z_]+)$", gemini, re.MULTILINE)
        self.assertEqual(set(listed), {"read_file", "grep_search", "glob", "list_directory"})
        for text in (claude, gemini):
            self.assertEqual(re.findall(r"^   - `([a-z_]+)`:", text, re.MULTILINE), RISKS)
        self.assertEqual(headings(body(VARIANTS / "claude_code" / "agents" / "cleaning-rule-critic.md")),
                         headings(body(VARIANTS / "gemini_cli" / "agents" / "cleaning-rule-critic.md")))

    def test_pairs_contract_matches_the_script(self):
        spec = importlib.util.spec_from_file_location("counts_under_test", ROOT / "scripts" / "check_cleaned_counts.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        contract = json.loads((ROOT / "contracts" / "cleanup-pairs.schema.json").read_text(encoding="utf-8"))
        pair = contract["$defs"]["pair"]
        self.assertEqual(set(pair["properties"]), module.PAIR_REQUIRED | module.PAIR_OPTIONAL)
        self.assertEqual(set(pair["required"]), module.PAIR_REQUIRED)
        self.assertEqual(tuple(pair["properties"]["delimiter"]["enum"]), module.DELIMITERS)
        self.assertEqual(contract["properties"]["record_type"]["const"], module.PAIRS_TYPE)


if __name__ == "__main__":
    unittest.main()
