"""Consistency tests across the Gemini CLI extension, the Cursor plugin, the scripts and the manifest contract."""
from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANTS = ROOT / "variants"
NAME = "step-status-plugin"
PLACED_SCRIPTS = f".baltor/plugins/{NAME}/scripts/"


def headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("## ")]


def toml_prompt(path: Path) -> str:
    return re.search(r"^prompt = '''\n(.*?)'''$", path.read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL).group(1)


def load_checker():
    spec = importlib.util.spec_from_file_location("layout_checker", ROOT / "scripts" / "check_step_packet.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PluginLayoutTests(unittest.TestCase):
    def test_manifests_name_the_same_plugin_and_version(self):
        gemini = json.loads((VARIANTS / "gemini_cli" / "gemini-extension.json").read_text(encoding="utf-8"))
        cursor = json.loads((VARIANTS / "cursor" / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual((gemini["name"], gemini["version"]), (NAME, "0.1.0"))
        self.assertRegex(gemini["name"], r"^[a-zA-Z0-9-]+$", "Gemini CLI extension names use letters, digits and dashes")
        self.assertEqual((cursor["name"], cursor["version"], cursor["license"]), (NAME, "0.1.0", "MIT"))
        self.assertTrue((VARIANTS / "gemini_cli" / gemini["contextFileName"]).is_file())

    def test_cursor_rule_carries_the_gemini_context_text(self):
        context = (VARIANTS / "gemini_cli" / "STEP-STATUS.md").read_text(encoding="utf-8")
        rule = (VARIANTS / "cursor" / "rules" / "step-status.mdc").read_text(encoding="utf-8")
        self.assertTrue(rule.startswith("---\n"))
        front, body = rule[4:].split("\n---\n", 1)
        keys = dict(line.split(": ", 1) for line in front.splitlines())
        self.assertEqual(set(keys), {"description", "alwaysApply"})
        self.assertEqual(keys["alwaysApply"], "true")
        self.assertEqual(body.lstrip("\n"), context)

    def test_context_text_is_short_and_starts_with_the_packet_check(self):
        context = (VARIANTS / "gemini_cli" / "STEP-STATUS.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(context.split()), 150, "the context file is loaded in every session")
        first_step = context.split("\n1. ", 1)[1].split("\n2. ", 1)[0]
        self.assertIn(PLACED_SCRIPTS + "check_step_packet.py", first_step)
        self.assertIn(".baltor/step/", context.splitlines()[2], "the text says at once when it applies")

    def test_status_command_is_the_same_in_both_variants(self):
        prompt = toml_prompt(VARIANTS / "gemini_cli" / "commands" / "step-status.toml")
        cursor = (VARIANTS / "cursor" / "commands" / "step-status.md").read_text(encoding="utf-8")
        self.assertEqual(cursor.split("\n---\n", 1)[1].lstrip("\n"), prompt)
        self.assertEqual(headings(prompt), ["## Purpose", "## First action", "## Steps", "## Output",
                                            "## Stop and report when"])
        self.assertIn("python3 -I -B " + PLACED_SCRIPTS + "step_status.py", prompt)

    def test_every_named_script_exists_and_uses_the_placed_path(self):
        for path in sorted(VARIANTS.rglob("*")):
            if path.is_file() and path.suffix in (".md", ".mdc", ".toml"):
                text = path.read_text(encoding="utf-8")
                for script in re.findall(r"scripts/([a-z_]+\.py)", text):
                    self.assertTrue((ROOT / "scripts" / script).is_file(), f"{path.name} names {script}")
                    self.assertIn(PLACED_SCRIPTS + script, text)
                self.assertNotIn("PLUGIN_ROOT", text)
                self.assertNotIn("extensionPath", text)

    def test_manifest_contract_names_the_fields_the_check_requires(self):
        checker = load_checker()
        contract = json.loads((ROOT / "contracts" / "packet-manifest.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(contract["required"]), checker.MANIFEST_FIELDS)
        self.assertEqual(set(contract["properties"]), checker.MANIFEST_FIELDS)
        self.assertEqual(contract["properties"]["record_type"]["const"], checker.MANIFEST_TYPE)
        self.assertEqual(contract["properties"]["files"]["maxProperties"], checker.MAX_FILES)

    def test_example_manifest_follows_the_contract_fields(self):
        checker = load_checker()
        manifest = json.loads((ROOT / "examples" / "packet" / ".baltor" / "step" / "packet-manifest.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(set(checker.check_manifest_shape(manifest)), set(manifest["files"]))


if __name__ == "__main__":
    unittest.main()
