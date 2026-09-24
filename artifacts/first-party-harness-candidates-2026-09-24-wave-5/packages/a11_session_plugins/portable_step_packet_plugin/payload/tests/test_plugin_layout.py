"""Consistency tests for the Agent Plugins manifest, both server configurations, the skills and the contracts."""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "portable-step-packet-plugin"
SERVER_KEY = "portable_step_packet_plugin"
PLACED = f".baltor/plugins/{NAME}/"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
SKILLS = {"read-step-assignment": "read_assignment.py", "write-step-result": "write_result.py"}
SKILL_SECTIONS = ["## When to use it", "## First action", "## Steps", "## Checks", "## Done when",
                  "## Stop and report when", "## Known-wrong example"]
CODE = [ROOT / "server" / "step_packet_server.py"] + [ROOT / "skills" / skill / "scripts" / script
                                                       for skill, script in SKILLS.items()]


def load_server():
    spec = importlib.util.spec_from_file_location("layout_server", ROOT / "server" / "step_packet_server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def server_entry(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    return document["mcpServers"][SERVER_KEY] if list(document["mcpServers"]) == [SERVER_KEY] else {}


class PluginLayoutTests(unittest.TestCase):
    def test_manifest_targets_the_agent_plugins_schema(self):
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["$schema"], SCHEMA)
        self.assertEqual((manifest["name"], manifest["version"], manifest["license"]), (NAME, "0.1.0", "MIT"))
        self.assertLessEqual(set(manifest), {"$schema", "name", "version", "description", "license", "keywords"})

    def test_portable_configuration_starts_the_packaged_server_through_the_plugin_root(self):
        entry = server_entry(ROOT / "mcp.json")
        self.assertEqual(entry["command"], "python3")
        self.assertEqual(entry["args"], ["-I", "-B", "${PLUGIN_ROOT}/server/step_packet_server.py"])
        self.assertTrue((ROOT / "server" / "step_packet_server.py").is_file())

    def test_cursor_configuration_uses_the_placed_path_because_cursor_leaves_plugin_root_unexpanded(self):
        entry = server_entry(ROOT / "variants" / "cursor" / "mcp.json")
        self.assertEqual(entry["args"], ["-I", "-B", PLACED + "server/step_packet_server.py"])
        self.assertNotIn("PLUGIN_ROOT", json.dumps(entry))
        portable = server_entry(ROOT / "mcp.json")
        self.assertEqual({**entry, "args": entry["args"][:2]}, {**portable, "args": portable["args"][:2]},
                         "the two configurations differ only in the script path")

    def test_skills_are_portable_folders_with_the_standard_sections(self):
        for skill, script in SKILLS.items():
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            front, body = text[4:].split("\n---\n", 1)
            self.assertIn(f'\nname: {skill}\n', "\n" + front + "\n")
            self.assertIn("license: MIT", front)
            self.assertIn('  version: "0.1.0"', front)
            description = re.search(r'^description: "(.*)"$', front, re.MULTILINE).group(1)
            self.assertLessEqual(len(description), 1024)
            self.assertEqual([line for line in body.splitlines() if line.startswith("## ")], SKILL_SECTIONS)
            self.assertIn(f"python3 -I -B {PLACED}skills/{skill}/scripts/{script}", body)
            self.assertTrue((ROOT / "skills" / skill / "scripts" / script).is_file())

    def test_one_contract_per_tool_and_the_examples_follow_them(self):
        server = load_server()
        contracts = sorted(path.name for path in (ROOT / "contracts").glob("*.input.schema.json"))
        self.assertEqual(contracts, sorted(f"{name}.input.schema.json" for name in server.DESCRIPTIONS))
        for name in server.DESCRIPTIONS:
            schema = json.loads((ROOT / "contracts" / f"{name}.input.schema.json").read_text(encoding="utf-8"))
            example = json.loads((ROOT / "examples" / f"{name}-arguments.json").read_text(encoding="utf-8"))
            self.assertEqual(server.argument_problem(schema, example), "", name)
            self.assertIs(schema.get("additionalProperties"), False)

    def test_code_has_no_network_process_or_dynamic_evaluation(self):
        refused_modules = {"socket", "ssl", "http", "urllib", "subprocess", "multiprocessing", "ftplib", "smtplib"}
        for path in CODE:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    names = []
                for name in names:
                    self.assertNotIn(name.split(".")[0], refused_modules, f"{path.name} imports {name}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "compile", "__import__"}, path.name)


if __name__ == "__main__":
    unittest.main()
