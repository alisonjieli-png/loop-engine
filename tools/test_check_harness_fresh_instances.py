"""Tests for the offline fresh instance check, run against a fixture harness.

The fixture harness discovers material the way Codex does: its configuration
folder, the skills of its home folder, the instruction files up to its git
root and its declared protocol servers. It sends what it loaded to the
loopback endpoint. The tests need Bubblewrap and run no real harness.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_harness_fresh_instances as tool  # noqa: E402

FIXTURE_HARNESS = r'''#!/usr/bin/python3
import json, os, pwd, subprocess, sys, tomllib, urllib.request
from pathlib import Path
arguments = sys.argv[1:]
if arguments == ["--version"]:
    print("fixture 1.0.0")
    sys.exit(0)
if "--exit-quietly" in arguments:
    sys.exit(0)
home = Path(pwd.getpwuid(os.getuid()).pw_dir) if "--use-passwd-home" in arguments else Path(os.environ["HOME"])
config = tomllib.loads((Path(os.environ["CODEX_HOME"]) / "config.toml").read_text())
provider = config["model_providers"][config["model_provider"]]
cwd = Path.cwd()
root = next((folder for folder in (cwd, *cwd.parents) if (folder / ".git").exists()), cwd)
folders = [folder for folder in (cwd, *cwd.parents) if folder == root or root in folder.parents]
instructions = [(folder / "AGENTS.md").read_text() for folder in folders if (folder / "AGENTS.md").is_file()]
roots = [home / ".agents" / "skills"] + [folder / ".agents" / "skills" for folder in folders]
skills = [path.read_text() for base in roots if base.is_dir() for path in sorted(base.glob("*/SKILL.md"))]
tools = []
for server in config.get("mcp_servers", {}).values():
    process = subprocess.Popen([server["command"], *server.get("args", [])], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, text=True)
    for message in ({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        if "id" in message:
            reply = json.loads(process.stdout.readline())
            if message["method"] == "tools/list":
                tools += [item["description"] for item in reply["result"]["tools"]]
    process.stdin.close()
    process.wait(timeout=5)
body = json.dumps({"model": config["model"], "instructions": instructions, "skills": skills,
                   "tools": tools}).encode()
credential = os.environ.get(provider["env_key"], "")
request = urllib.request.Request(provider["base_url"] + "/responses", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + credential})
try:
    urllib.request.urlopen(request, timeout=10)
except Exception:
    sys.exit(1)
'''

RECIPE = {
    "record_type": "harness_fresh_instance_recipe/v1", "recipe_id": "fixture.fresh_instance",
    "harness": "fixture", "launch_mode": "customer_process", "order": 1, "candidate": False,
    "source": {"upstream": "https://github.com/example/fixture", "revision": None, "licence": "MIT"},
    "executable": "fixture-harness", "version_arguments": ["--version"],
    "version_pattern": r"^fixture (\S+)$", "pinned_version": "1.0.0",
    "configuration_variable": "CODEX_HOME",
    "environment": {"HOME": "{empty_home}", "CODEX_HOME": "{configuration_folder}",
                    "TMPDIR": "{configuration_folder}",
                    "BALTOR_STEP_MODEL_CREDENTIAL": "{model_credential}"},
    "arguments": ["exec", "{probe_prompt}"],
    "instruction_files": [{"name": "AGENTS.md", "body": "step_instructions"}],
    "skills_directory": ".agents/skills", "configuration_writer": "codex_configuration_toml",
    "global_locations": [".agents/skills/decoy-agents-skill/SKILL.md", ".codex/AGENTS.md"],
    "bundled_items": [], "support_claim": "material_loading",
    "material": {"instruction_file": "loaded", "skills": "loaded", "protocol_servers": "loaded"},
    "evidence": ["docs/research/HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md"],
}


def _sandbox_available() -> bool:
    if not all(Path(path).is_file() for path in (tool.BUBBLEWRAP, tool.GIT, tool.PYTHON)):
        return False
    probe = subprocess.run([tool.BUBBLEWRAP, "--unshare-net", "--ro-bind", "/", "/", "--dev", "/dev",
                            "--", "/usr/bin/true"], capture_output=True)
    return probe.returncode == 0


class FreshInstanceCheckTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="fresh-instance-test-"))
        self.harness = self.folder / "fixture-harness"
        self.harness.write_text(FIXTURE_HARNESS)
        self.harness.chmod(0o755)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _run(self, **changes):
        from loop_engine.core.harness_fresh_instances import FreshInstanceRecipe
        recipe = FreshInstanceRecipe.from_dict({**RECIPE, **changes})
        return tool.check_recipe(recipe, self.folder / "runs" / os.urandom(3).hex(),
                                 executable=str(self.harness), timeout=30)

    def test_software_paths_mount_the_package_folder_or_the_program(self):
        self.assertEqual(tool.software_paths(Path("/opt/lib/node_modules/@scope/tool/bin/cli.js")),
                         ["/opt/lib/node_modules/@scope/tool"])
        self.assertEqual(tool.software_paths(Path("/opt/lib/node_modules/tool/dist/cli.js")),
                         ["/opt/lib/node_modules/tool"])
        self.assertEqual(tool.software_paths(Path("/opt/bin/program")), ["/opt/bin/program"])

    def test_evidence_named_by_a_release_claim_exists_in_the_repository(self):
        from loop_engine.core.harness_recipes import release_recipe_catalog
        missing = [(item.recipe_id, path) for item in release_recipe_catalog().fresh_instance_recipes
                   for path in item.evidence if not (tool.ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_a_missing_program_is_not_tested_with_its_dependency(self):
        from loop_engine.core.harness_fresh_instances import FreshInstanceRecipe
        recipe = FreshInstanceRecipe.from_dict({**RECIPE, "executable": "no-such-harness-program"})
        result = tool.check_recipe(recipe, self.folder / "missing", timeout=5)
        self.assertEqual(result["status"], "not_tested")
        self.assertEqual(result["missing_optional_dependencies"], ["no-such-harness-program"])

    @unittest.skipUnless(_sandbox_available(), "Bubblewrap with a network namespace is required")
    def test_a_recipe_with_an_empty_home_loads_only_the_step_material(self):
        result = self._run()
        self.assertEqual(result["status"], "passed", result["launches"]["recipe"]["reasons"])
        self.assertEqual(result["installed_version"], "1.0.0")
        self.assertEqual(result["launches"]["recipe"]["rung"], "material_loaded")
        self.assertTrue(result["launches"]["recipe"]["credential_delivered"],
                        "the credential reaches the endpoint through the process environment")
        kept = result["launches"]["home_folder_kept"]
        self.assertFalse(kept["passed"])
        self.assertTrue(kept["decoys_found"], "the decoy skill of a kept home folder must be caught")
        self.assertFalse(result["launches"]["instruction_file_missing"]["passed"])
        self.assertEqual(result["controls_failed_as_expected"],
                         {"home_folder_kept": True, "instruction_file_missing": True})

    @unittest.skipUnless(_sandbox_available(), "Bubblewrap with a network namespace is required")
    def test_a_harness_that_reads_the_real_home_folder_is_caught(self):
        result = self._run(arguments=["exec", "--use-passwd-home", "{probe_prompt}"])
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["launches"]["recipe"]["decoys_found"])

    @unittest.skipUnless(_sandbox_available(), "Bubblewrap with a network namespace is required")
    def test_an_exit_without_a_request_is_not_loading(self):
        result = self._run(arguments=["exec", "--exit-quietly", "{probe_prompt}"])
        launch = result["launches"]["recipe"]
        self.assertEqual((result["status"], launch["rung"], launch["exit_code"]), ("failed", "none", 0))

    @unittest.skipUnless(_sandbox_available(), "Bubblewrap with a network namespace is required")
    def test_every_run_writes_a_new_folder_and_keeps_the_earlier_one(self):
        from loop_engine.core.harness_recipes import HarnessRecipeCatalog
        catalog = HarnessRecipeCatalog.from_dict({
            "record_type": "harness_recipe_catalog/v1", "version": "1.0.0", "wire_codecs": [],
            "recipes": [], "fresh_instance_recipes": [RECIPE]}, module_directory=str(self.folder))
        first = tool.run(output_root=self.folder / "out", catalog=catalog,
                         executables={"fixture.fresh_instance": str(self.harness)}, timeout=30)
        second = tool.run(output_root=self.folder / "out", catalog=catalog,
                          executables={"fixture.fresh_instance": str(self.harness)}, timeout=30)
        self.assertNotEqual(first["result_path"], second["result_path"])
        self.assertTrue(Path(first["result_path"]).is_file() and Path(second["result_path"]).is_file())
        self.assertEqual(second["model_calls"], 0)
        self.assertEqual(second["summary"], {"passed": 1, "failed": 0, "not_tested": 0})


if __name__ == "__main__":
    unittest.main()
