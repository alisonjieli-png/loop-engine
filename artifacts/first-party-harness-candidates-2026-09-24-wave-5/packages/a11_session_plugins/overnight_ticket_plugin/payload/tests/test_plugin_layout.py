"""Consistency tests across the Claude Code and Cursor variants of the overnight ticket plugin."""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ROOT / "variants"
NAME = "overnight-ticket-plugin"
PLACED_SCRIPTS = f".baltor/plugins/{NAME}/scripts/"


def load(script: str):
    spec = importlib.util.spec_from_file_location(f"layout_{script}", ROOT / "scripts" / script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def front_matter(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", path
    end = lines.index("---", 1)
    values = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        values[key.strip()] = value.strip().strip('"')
    return values


def headings(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("## ")]


def markdown_files() -> list[Path]:
    return sorted(VARIANTS.glob("*/commands/*.md")) + sorted(VARIANTS.glob("*/agents/*.md"))


class PluginLayoutTests(unittest.TestCase):
    def test_both_manifests_name_the_same_plugin_and_version(self):
        claude = json.loads((VARIANTS / "claude_code" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        cursor = json.loads((VARIANTS / "cursor" / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        for manifest in (claude, cursor):
            self.assertEqual((manifest["name"], manifest["version"], manifest["license"]), (NAME, "0.1.0", "MIT"))

    def test_claude_code_hook_runs_the_packaged_session_start_script(self):
        hooks = json.loads((VARIANTS / "claude_code" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entry = hooks["hooks"]["SessionStart"][0]
        self.assertEqual(entry["matcher"], "startup|resume|clear|compact")
        self.assertEqual(entry["matcher"].split("|"), list(load("session_start.py").CLAUDE_SOURCES))
        command = entry["hooks"][0]["command"]
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/scripts/session_start.py" --harness claude_code', command)
        self.assertTrue(command.startswith("python3 -I -B "))

    def test_cursor_hook_runs_the_packaged_session_start_script(self):
        hooks = json.loads((VARIANTS / "cursor" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(hooks["version"], 1)
        entry = hooks["hooks"]["sessionStart"][0]
        self.assertIn('"${CURSOR_PLUGIN_ROOT}/scripts/session_start.py" --harness cursor', entry["command"])
        self.assertLessEqual(entry["timeout"], 10)

    def test_commands_and_agents_run_existing_scripts_by_their_placed_path(self):
        for path in markdown_files():
            text = path.read_text(encoding="utf-8")
            named = re.findall(r"scripts/([a-z_]+\.py)", text)
            self.assertTrue(named, path)
            for script in named:
                self.assertTrue((ROOT / "scripts" / script).is_file(), f"{path} names {script}")
                self.assertIn(PLACED_SCRIPTS + script, text)
            self.assertNotIn("PLUGIN_ROOT", text, f"{path}: a Markdown body uses the placed path, not a variable")

    def test_variants_keep_the_same_sections_and_steps(self):
        for kind, name in (("commands", "night-status.md"), ("agents", "ticket-closer.md")):
            claude, cursor = VARIANTS / "claude_code" / kind / name, VARIANTS / "cursor" / kind / name
            self.assertEqual(headings(claude), headings(cursor))
            body = [line for line in claude.read_text(encoding="utf-8").split("---", 2)[2].splitlines()]
            other = [line for line in cursor.read_text(encoding="utf-8").split("---", 2)[2].splitlines()]
            self.assertEqual(body, other, f"{name}: the two variants differ only in front matter")

    def test_ticket_closer_has_no_file_editing_tool(self):
        claude = front_matter(VARIANTS / "claude_code" / "agents" / "ticket-closer.md")
        self.assertEqual({tool.strip() for tool in claude["tools"].split(",")}, {"Read", "Grep", "Glob", "Bash"})
        cursor = front_matter(VARIANTS / "cursor" / "agents" / "ticket-closer.md")
        self.assertEqual(cursor["name"], claude["name"])

    def test_draft_contract_matches_the_closing_script(self):
        closer = load("close_ticket.py")
        contract = json.loads((ROOT / "contracts" / "ticket-result-draft.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(contract["properties"]), closer.DRAFT_FIELDS)
        self.assertEqual(set(contract["required"]), closer.DRAFT_FIELDS)
        evidence = contract["properties"]["evidence"]["items"]
        self.assertEqual(set(evidence["properties"]), closer.EVIDENCE_FIELDS)

    def test_record_contract_matches_the_reader(self):
        reader = load("night_status.py")
        contract = json.loads((ROOT / "contracts" / "ticket-result-record.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(contract["properties"]), reader.RESULT_FIELDS)
        self.assertEqual(set(contract["required"]), reader.RESULT_FIELDS)
        self.assertEqual(contract["properties"]["record_type"]["const"], reader.RESULT_TYPE)

    def test_queue_contract_names_the_fields_the_reader_uses(self):
        reader = load("night_status.py")
        contract = json.loads((ROOT / "contracts" / "night-queue.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["properties"]["record_type"]["const"], reader.QUEUE_TYPE)
        self.assertEqual(set(contract["required"]), {"record_type", "items"})
        self.assertEqual(set(contract["$defs"]["item"]["required"]), {"id", "title"})
        queue = reader.load_queue(ROOT / "examples" / "night")
        self.assertEqual([ticket["ticket_id"] for ticket in queue["tickets"]], ["T-101", "T-102", "T-103"])


if __name__ == "__main__":
    unittest.main()
