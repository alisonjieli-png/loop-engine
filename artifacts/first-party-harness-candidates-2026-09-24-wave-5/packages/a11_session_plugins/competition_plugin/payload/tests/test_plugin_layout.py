"""Consistency tests across the Claude Code plugin, the Gemini CLI extension and the shared skill."""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ROOT / "variants"
NAME = "competition-plugin"
SKILL = ROOT / "skills" / "pre-submission-gate" / "SKILL.md"
SKILL_SECTIONS = ["## When to use it", "## First action", "## Steps", "## Checks", "## Done when",
                  "## Stop and report when", "## Known-wrong example"]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("## ")]


def toml_prompt(path: Path) -> str:
    return re.search(r"^prompt = '''\n(.*?)'''$", path.read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL).group(1)


class PluginLayoutTests(unittest.TestCase):
    def test_manifests_name_the_same_plugin_and_version(self):
        claude = json.loads((VARIANTS / "claude_code" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        gemini = json.loads((VARIANTS / "gemini_cli" / "gemini-extension.json").read_text(encoding="utf-8"))
        self.assertEqual((claude["name"], claude["version"], claude["license"]), (NAME, "0.1.0", "MIT"))
        self.assertEqual((gemini["name"], gemini["version"]), (NAME, "0.1.0"))

    def test_session_start_hooks_run_the_packaged_script(self):
        claude = json.loads((VARIANTS / "claude_code" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entry = claude["hooks"]["SessionStart"][0]
        self.assertEqual(entry["matcher"], "startup|resume|clear|compact")
        hook = load(ROOT / "scripts" / "brief_summary.py", "layout_sources")
        self.assertEqual(entry["matcher"].split("|"), list(hook.SOURCES["claude_code"]),
                         "the script accepts exactly the sources the Claude Code matcher registers")
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/scripts/brief_summary.py" --harness claude_code', entry["hooks"][0]["command"])
        gemini = json.loads((VARIANTS / "gemini_cli" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entry = gemini["hooks"]["SessionStart"][0]
        self.assertNotIn("matcher", entry, "Gemini CLI lifecycle matchers are exact strings, so no pattern is used")
        self.assertIn('"${extensionPath}/scripts/brief_summary.py" --harness gemini_cli', entry["hooks"][0]["command"])
        self.assertGreaterEqual(entry["hooks"][0]["timeout"], 1000)

    def test_note_command_has_the_same_sections_in_both_variants(self):
        claude = (VARIANTS / "claude_code" / "commands" / "experiment-note.md").read_text(encoding="utf-8")
        gemini = toml_prompt(VARIANTS / "gemini_cli" / "commands" / "experiment-note.toml")
        self.assertEqual(headings(claude), headings(gemini))
        for text in (claude, gemini):
            self.assertIn("python3 -I -B .baltor/plugins/competition-plugin/scripts/experiment_note.py", text)
            self.assertNotIn("PLUGIN_ROOT", text, "a command body uses the placed path, not a hook variable")
            self.assertNotIn("extensionPath", text, "a command body uses the placed path, not a hook variable")

    def test_skill_front_matter_and_sections(self):
        text = SKILL.read_text(encoding="utf-8")
        front, body = text.split("\n---\n", 1)
        self.assertIn("\nname: pre-submission-gate\n", front + "\n")
        self.assertIn("license: MIT", front)
        self.assertIn('  version: "0.1.0"', front)
        description = re.search(r'^description: "(.*)"$', front, re.MULTILINE).group(1)
        self.assertLessEqual(len(description), 1024)
        self.assertEqual(headings(body), SKILL_SECTIONS)

    def test_skill_command_points_at_the_packaged_gate(self):
        text = SKILL.read_text(encoding="utf-8")
        path = re.search(r"python3 -I -B (\S+submission_gate\.py)", text).group(1)
        self.assertEqual(path, ".baltor/plugins/competition-plugin/skills/pre-submission-gate/scripts/submission_gate.py")
        self.assertTrue((ROOT / "skills" / "pre-submission-gate" / "scripts" / "submission_gate.py").is_file())

    def test_contracts_match_the_scripts(self):
        hook = load(ROOT / "scripts" / "brief_summary.py", "layout_hook")
        writer = load(ROOT / "scripts" / "experiment_note.py", "layout_writer")
        brief = json.loads((ROOT / "contracts" / "competition-brief.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(brief["required"]), hook.BRIEF_FIELDS)
        self.assertEqual(tuple(brief["properties"]["task_type"]["enum"]), hook.TASK_TYPES)
        self.assertEqual(tuple(brief["properties"]["validation"]["properties"]["scheme"]["enum"]), hook.SCHEMES)
        draft = json.loads((ROOT / "contracts" / "experiment-note-draft.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(draft["properties"]), writer.REQUIRED | writer.OPTIONAL)
        self.assertEqual(set(draft["required"]), writer.REQUIRED)


if __name__ == "__main__":
    unittest.main()
