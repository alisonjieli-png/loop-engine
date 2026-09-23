"""Known-wrong controls for local connection candidate config files."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from check_configs import check


class CandidateConfigurationChecks(unittest.TestCase):
    def test_three_candidate_layouts_have_expected_local_commands(self) -> None:
        self.assertEqual(check()["clients"], ["claude", "codex", "opencode"])

    def test_broadened_tool_permission_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "candidate"
            shutil.copytree(ROOT, copied)
            path = copied / "layouts" / "opencode" / "work" / "opencode.json"
            config = json.loads(path.read_text(encoding="utf-8"))
            config["permission"]["baltor_json_shape_*"] = "allow"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "permission differs"):
                check(copied)

    def test_embedded_credential_field_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "candidate"
            shutil.copytree(ROOT, copied)
            path = copied / "layouts" / "claude" / "work" / ".mcp.json"
            config = json.loads(path.read_text(encoding="utf-8"))
            config["mcpServers"]["baltor_json_shape"]["env"] = {"API_KEY": "wrong"}
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected server fields"):
                check(copied)

    def test_unlisted_auth_field_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "candidate"
            shutil.copytree(ROOT, copied)
            path = copied / "layouts" / "codex" / "work" / ".codex" / "config.toml"
            with path.open("a", encoding="utf-8") as target:
                target.write('bearer_token = "wrong"\n')
            with self.assertRaisesRegex(ValueError, "unexpected server fields"):
                check(copied)


if __name__ == "__main__":
    unittest.main()
