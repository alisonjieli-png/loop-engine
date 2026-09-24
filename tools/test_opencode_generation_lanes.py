"""Known-wrong checks for the OpenCode generation lanes. No model is called."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.opencode_generation_lanes import (  # noqa: E402
    DECLARED_ENDPOINTS,
    FORBIDDEN_URL_PATTERNS,
    Lane,
    LaneError,
    LaneRunner,
    _extract_message_text,
    _looks_like_candidate,
    _render_prompt,
    build_lanes,
)


def _lane(provider: str, model: str, root: Path, lane_id: str = "lane-test") -> Lane:
    return Lane(lane_id=lane_id, provider=provider, model=model, root=root)


def _idea() -> dict:
    return {
        "record_type": "harness_idea_record/v1",
        "id": "string-standardization-data-cleaning",
        "datatype": "string",
        "operation": "standardization",
        "use_case": "data_cleaning",
        "lifecycle": "candidate",
        "applicability": {
            "occupation_code": "13-1081.00",
            "occupation_title": "Logisticians",
            "task_reference": "Verify entered values against the source document.",
            "facet_dimensions": ["job_title"],
            "facet": "job_title",
        },
        "method_signature": "string|standardization|data_cleaning",
        "brief": "brief",
        "known_wrong": "A record with leading and trailing whitespace is treated as clean already.",
    }


class ProviderDeclarationChecks(unittest.TestCase):
    def test_declared_endpoints_are_remote_only(self):
        for name, endpoint in DECLARED_ENDPOINTS.items():
            for pattern in FORBIDDEN_URL_PATTERNS:
                self.assertIsNone(pattern.search(endpoint["base_url"]),
                                  f"{name} must not be local")

    def test_undeclared_provider_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(LaneError):
                _lane("ollama-local", "llama3", Path(temporary))

    def test_model_not_declared_for_provider_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(LaneError):
                _lane("ollama-cloud", "gemma-4-coding-abliterated", Path(temporary))
            with self.assertRaises(LaneError):
                _lane("tactical", "gpt-oss:20b", Path(temporary))

    def test_lane_id_is_validated(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(LaneError):
                _lane("ollama-cloud", "gpt-oss:20b", Path(temporary), lane_id="../escape")


class LaneSetupChecks(unittest.TestCase):
    def test_each_lane_writes_its_own_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = _lane("ollama-cloud", "gpt-oss:20b", root / "a", lane_id="lane-a")
            second = _lane("tactical", "gemma-4-coding-abliterated", root / "b", lane_id="lane-b")
            first.write_config()
            second.write_config()
            for lane, provider in ((first, "ollama-cloud"), (second, "tactical")):
                config = json.loads((lane.config_directory / "opencode.jsonc").read_text())
                self.assertEqual(config["model"], f"{provider}/{lane.model}")
                self.assertIn(provider, config["provider"])
                base_url = config["provider"][provider]["options"]["baseURL"]
                self.assertTrue(base_url.startswith("https://"))
                self.assertEqual(config["provider"][provider]["options"]["apiKey"],
                                 "{env:%s}" % DECLARED_ENDPOINTS[provider]["key_environment"])

    def test_environment_is_scrubbed_and_isolated(self):
        os.environ["SNEAKY_SECRET"] = "leaked"
        try:
            with tempfile.TemporaryDirectory() as temporary:
                lane = _lane("ollama-cloud", "gpt-oss:20b", Path(temporary) / "lane")
                lane.write_config()
                environment = lane.environment()
                self.assertNotIn("SNEAKY_SECRET", environment)
                self.assertEqual(environment["OPENCODE_CONFIG_DIR"],
                                 str(lane.config_directory))
                self.assertEqual(environment["XDG_DATA_HOME"], str(lane.data_home))
                self.assertIn("OLLAMA_API_KEY", environment)
        finally:
            del os.environ["SNEAKY_SECRET"]

    def test_lane_roots_do_not_share_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = _lane("ollama-cloud", "gpt-oss:20b", root / "one", lane_id="lane-one")
            second = _lane("ollama-cloud", "gpt-oss:20b", root / "two", lane_id="lane-two")
            first.write_config()
            second.write_config()
            self.assertNotEqual(first.config_directory, second.config_directory)
            self.assertNotEqual(first.data_home, second.data_home)
            self.assertNotEqual(first.workspace, second.workspace)


class IdeaAndPromptChecks(unittest.TestCase):
    def test_write_idea_refuses_unknown_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            lane = _lane("ollama-cloud", "gpt-oss:20b", Path(temporary) / "lane")
            runner = LaneRunner(lane, executable=Path("/nonexistent"))
            with self.assertRaises(LaneError):
                runner.write_idea({"record_type": "something_else/v9"})

    def test_prompt_carries_identity_and_known_wrong(self):
        prompt = _render_prompt(_idea())
        self.assertIn("string-standardization-data-cleaning", prompt)
        self.assertIn("known-wrong", prompt)
        self.assertIn("whitespace", prompt)

    def test_candidate_shape_check_requires_frontmatter_and_identity(self):
        idea = _idea()
        good = ("---\nname: string-standardization-data-cleaning\n"
                "description: x\nlicense: MIT\n---\nbody")
        bad_missing_name = "---\ndescription: x\nlicense: MIT\n---\nbody"
        bad_no_frontmatter = "just text"
        self.assertTrue(_looks_like_candidate(good, idea))
        self.assertFalse(_looks_like_candidate(bad_missing_name, idea))
        self.assertFalse(_looks_like_candidate(bad_no_frontmatter, idea))

    def test_fenced_candidate_is_accepted_after_stripping(self):
        idea = _idea()
        fenced = ("```markdown\n---\nname: string-standardization-data-cleaning\n"
                  "description: x\nlicense: MIT\n---\nbody\n```")
        from tools.opencode_generation_lanes import _strip_code_fence
        self.assertTrue(_looks_like_candidate(_strip_code_fence(fenced), idea))

    def test_extract_message_text_takes_last_message_event(self):
        events = "\n".join([
            '{"type":"text","part":{"type":"text","text":"first"}}',
            '{"type":"other"}',
            '{"type":"text","part":{"type":"text","text":"second"}}',
        ])
        self.assertEqual(_extract_message_text(events), "second")
        self.assertEqual(_extract_message_text("no json here"), "")


class BuildLanesChecks(unittest.TestCase):
    def test_build_lanes_materializes_all_setups(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            specs = [
                {"lane_id": "lane-a", "provider": "ollama-cloud", "model": "gpt-oss:20b"},
                {"lane_id": "lane-b", "provider": "tactical",
                 "model": "gemma-4-coding-abliterated"},
            ]
            lanes = build_lanes(root, specs)
            self.assertEqual(len(lanes), 2)
            for lane in lanes:
                self.assertTrue((lane.config_directory / "opencode.jsonc").is_file())
                self.assertTrue(lane.data_home.is_dir())
                self.assertTrue(lane.workspace.is_dir())

    def test_no_lanes_declared_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(LaneError):
                build_lanes(Path(temporary), [])


if __name__ == "__main__":
    unittest.main()