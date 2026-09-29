"""The real page validator accepts typed effect metadata without relaxing secret rules."""
import json
import re
import subprocess
import unittest
from pathlib import Path

from loop_engine.core.facets import EFFECTS

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "src/loop_engine/core/service_runtime/web_assets/service.js"


class RecipeEffectTests(unittest.TestCase):
    def test_effect_vocabulary_matches_the_existing_contract(self):
        for path in (PAGE, ROOT / "tools/check_service_workspace.mjs"):
            text = path.read_text()
            found = re.search(r"const recipeEffectNames\s*=\s*new Set\((\[.*?\])\)", text)
            self.assertIsNotNone(found)
            self.assertEqual(set(json.loads(found.group(1))), set(EFFECTS))

    def test_real_validator_accepts_metadata_and_refuses_credentials_and_arguments(self):
        script = r'''
const fs=require('node:fs'), vm=require('node:vm');
const source=fs.readFileSync('src/loop_engine/core/service_runtime/web_assets/service.js','utf8');
const fragment=source.slice(source.indexOf('  const recipeRecordType ='),source.indexOf('  const tomlKey ='));
const context={URL};vm.createContext(context);vm.runInContext(fragment+';globalThis.check=recipeRefusal;',context);
const original=JSON.parse(fs.readFileSync('src/loop_engine/core/service_runtime/web_assets/client-recipes.json'));
const probe=change=>{const value=structuredClone(original);change(value);return context.check(value);};
const results=[context.check(original),
probe(value=>value.recipes[0].configuration.mcp_servers.baltor.http_headers['Baltor-Step-Effects']='network, arbitrary'),
probe(value=>value.recipes[0].configuration.mcp_servers.baltor.http_headers['Baltor-Step-Effects']='pure, network'),
probe(value=>value.recipes[0].configuration.mcp_servers.baltor.http_headers['X-Other']='secret'),
probe(value=>value.recipes[3].configuration.baltor.step_effects=['reads_fs','curl --bad']),
probe(value=>value.recipes[3].configuration.baltor.args=['python','script']),
probe(value=>value.recipes[2].configuration.mcpServers.baltor.headers.Authorization='Bearer secret')];
process.stdout.write(JSON.stringify(results));
'''
        result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True,
                                timeout=20)
        decisions = json.loads(result.stdout)
        self.assertEqual(decisions[0], "")
        self.assertTrue(all(decisions[1:]), decisions)


if __name__ == "__main__":
    unittest.main()
