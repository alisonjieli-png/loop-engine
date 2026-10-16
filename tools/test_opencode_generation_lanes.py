"""Known-wrong checks for the OpenCode generation lanes. No model is called and no outside host is contacted."""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import tempfile
import threading
import unittest
import urllib.request
from importlib.util import find_spec
from unittest import mock
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools import opencode_generation_lanes as lanes  # noqa: E402
from tools import private_endpoints  # noqa: E402
from tools.opencode_generation_lanes import (  # noqa: E402
    DECLARED_ENDPOINTS,
    FORBIDDEN_URL_PATTERNS,
    FORWARDER_API_KEY_PLACEHOLDER,
    FORWARDER_URL_ENVIRONMENT,
    Lane,
    LaneError,
    LaneRunner,
    _extract_message_text,
    _looks_like_candidate,
    _render_prompt,
    build_lanes,
)

#: Invented settings for the Tactical lane; the real ones are private configuration.
TACTICAL_ENVIRONMENT = {"LOOP_ENGINE_TACTICAL_BASE_URL": "https://origin.fixture.invalid:6969/v1",
                        "LOOP_ENGINE_TACTICAL_TLS_SERVER_NAME": "origin.fixture.test",
                        "TACTICAL_API_KEY": "stand-in-tactical-value"}


def _without_keyring(reference):
    raise LookupError("no keyring in these checks")


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
            if endpoint.get("private_endpoint"):
                # A private endpoint has no URL in the repository; its URL is checked when it is read.
                self.assertNotIn("base_url", endpoint)
                self.assertEqual(endpoint["transport"], "verified_forwarder")
                continue
            for pattern in FORBIDDEN_URL_PATTERNS:
                self.assertIsNone(pattern.search(endpoint["base_url"]),
                                  f"{name} must not be local")

    def test_a_local_private_upstream_is_refused_before_any_key_is_read(self):
        environment = {**TACTICAL_ENVIRONMENT, "LOOP_ENGINE_TACTICAL_BASE_URL": "https://127.0.0.1:9/v1"}
        with mock.patch.dict(os.environ, environment), \
                mock.patch.object(private_endpoints, "_keyring_value", _without_keyring), \
                mock.patch.object(lanes, "_resolve_key", side_effect=AssertionError("key read")), \
                tempfile.TemporaryDirectory() as temporary:
            lane = _lane("tactical", "gemma-4-coding-abliterated", Path(temporary) / "lane")
            with self.assertRaisesRegex(LaneError, "local_endpoint_refused"):
                lane.environment()
        self.assertEqual(lanes._FORWARDERS, {})

    def test_the_pinned_tactical_root_is_the_committed_file(self):
        endpoint = DECLARED_ENDPOINTS["tactical"]
        raw = (ROOT / endpoint["tls_ca_file"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), endpoint["tls_ca_sha256"])

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
                options = config["provider"][provider]["options"]
                if provider == "tactical":
                    # No upstream, port or key in the file: the forwarder's base arrives by environment and
                    # the forwarder replaces the placeholder key.
                    self.assertEqual(options, {"baseURL": "{env:%s}" % FORWARDER_URL_ENVIRONMENT,
                                               "apiKey": FORWARDER_API_KEY_PLACEHOLDER})
                    continue
                self.assertTrue(options["baseURL"].startswith("https://"))
                self.assertEqual(options["apiKey"], "{env:%s}" % DECLARED_ENDPOINTS[provider]["key_environment"])

    def test_environment_is_scrubbed_and_isolated(self):
        # The lane passes its provider's key through by name. The test supplies a stand-in value, so it runs the
        # same on a machine that holds no real key, such as continuous integration, where it failed on September 24, 2026.
        with mock.patch.dict(os.environ, {"SNEAKY_SECRET": "leaked", "OLLAMA_API_KEY": "stand-in-value"}):
            with tempfile.TemporaryDirectory() as temporary:
                lane = _lane("ollama-cloud", "gpt-oss:20b", Path(temporary) / "lane")
                lane.write_config()
                environment = lane.environment()
                self.assertNotIn("SNEAKY_SECRET", environment)
                self.assertEqual(environment["OPENCODE_CONFIG_DIR"],
                                 str(lane.config_directory))
                self.assertEqual(environment["XDG_DATA_HOME"], str(lane.data_home))
                self.assertEqual(environment["OLLAMA_API_KEY"], "stand-in-value")

    def test_an_ollama_lane_carries_only_its_own_key(self):
        with mock.patch.dict(os.environ, {"OLLAMA_API_KEY": "stand-in-value", **TACTICAL_ENVIRONMENT}):
            with tempfile.TemporaryDirectory() as temporary:
                lane = _lane("ollama-cloud", "gpt-oss:20b", Path(temporary) / "lane")
                environment = lane.environment()
        self.assertNotIn("TACTICAL_API_KEY", environment)
        self.assertNotIn(TACTICAL_ENVIRONMENT["TACTICAL_API_KEY"], json.dumps(environment))

    def test_the_tactical_lane_reaches_a_verified_forwarder_and_never_holds_the_key(self):
        parent = {**TACTICAL_ENVIRONMENT, "NODE_TLS_REJECT_UNAUTHORIZED": "0", "NODE_EXTRA_CA_CERTS": "/x.pem"}
        self.addCleanup(lanes.stop_forwarders)
        with mock.patch.dict(os.environ, parent), \
                mock.patch.object(private_endpoints, "_keyring_value", _without_keyring), \
                tempfile.TemporaryDirectory() as temporary:
            lane = _lane("tactical", "gemma-4-coding-abliterated", Path(temporary) / "lane")
            lane.write_config()
            environment = lane.environment()
            again = lane.environment()
            record = lanes.endpoint_record("tactical")
        for name in ("NODE_TLS_REJECT_UNAUTHORIZED", "NODE_EXTRA_CA_CERTS", "TACTICAL_API_KEY"):
            self.assertNotIn(name, environment)
        self.assertNotIn(TACTICAL_ENVIRONMENT["TACTICAL_API_KEY"], json.dumps(environment))
        self.assertTrue(environment[FORWARDER_URL_ENVIRONMENT].startswith("http://127.0.0.1:"))
        self.assertTrue(environment[FORWARDER_URL_ENVIRONMENT].endswith("/v1"))
        self.assertEqual(again[FORWARDER_URL_ENVIRONMENT], environment[FORWARDER_URL_ENVIRONMENT],
                         "one forwarder per endpoint and process")
        forwarder = lanes._FORWARDERS["tactical"]
        self.assertEqual(forwarder.authorization, "Bearer " + TACTICAL_ENVIRONMENT["TACTICAL_API_KEY"])
        self.assertEqual(forwarder.tls_server_name, "origin.fixture.test")
        self.assertEqual((forwarder.context.verify_mode, forwarder.context.check_hostname), (ssl.CERT_REQUIRED, True))
        for private in ("origin.fixture", TACTICAL_ENVIRONMENT["TACTICAL_API_KEY"]):
            self.assertNotIn(private, json.dumps(record))
        self.assertEqual(record["private_endpoint"]["private_endpoint"], "tactical")
        self.assertEqual(lanes.endpoint_record("ollama-cloud"), {"base_url": "https://ollama.com/v1"})

    def test_an_unconfigured_tactical_endpoint_refuses_before_the_key_or_a_process(self):
        environment = {key: value for key, value in os.environ.items() if not key.startswith("LOOP_ENGINE_TACTICAL")}
        with mock.patch.dict(os.environ, environment, clear=True), \
                mock.patch.object(private_endpoints, "_keyring_value", _without_keyring), \
                mock.patch.object(lanes, "_resolve_key", side_effect=AssertionError("key read")), \
                tempfile.TemporaryDirectory() as temporary:
            lane = _lane("tactical", "gemma-4-coding-abliterated", Path(temporary) / "lane")
            lane.write_config()
            runner = LaneRunner(lane, executable=Path(sys.executable))
            ledger = Path(temporary) / "ledger.jsonl"
            with self.assertRaisesRegex(LaneError, "private_endpoint_unconfigured.*LOOP_ENGINE_TACTICAL_BASE_URL"):
                runner.run(_idea(), ledger)
            self.assertFalse(ledger.exists(), "nothing is recorded as dispatched")
        self.assertEqual(lanes._FORWARDERS, {})

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

    def test_a_seed_excerpt_enters_the_prompt_between_markers_and_an_idea_without_one_is_unchanged(self):
        plain = _render_prompt(_idea())
        self.assertNotIn("<<<SEED>>>", plain)
        seeded = _idea()
        seeded["applicability"] = {**seeded["applicability"],
                                   "seed_excerpt": "README:\nResize every image in a folder.\n\nModules:\nmodule "
                                                   "resize.py\n  def resize(path, width)"}
        prompt = _render_prompt(seeded)
        self.assertTrue(prompt.startswith(plain))
        self.assertIn("<<<SEED>>>\nREADME:\nResize every image", prompt)
        self.assertTrue(prompt.endswith("\n<<<END SEED>>>"))
        self.assertIn("owner's own project", prompt)
        blank = _idea()
        blank["applicability"] = {**blank["applicability"], "seed_excerpt": "  "}
        self.assertEqual(_render_prompt(blank), plain)

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

    def test_plugin_manifest_shape_check(self):
        idea = {**_idea(), "file_kind": "plugin_manifest"}
        good = json.dumps({
            "name": idea["id"], "version": "1.0.0", "description": "d",
            "schema": "https://agentplugins.io/schema/v1",
            "skills": [{"name": idea["id"], "description": "d"}],
            "mcpServers": {"one": {"command": "run"}}})
        bad_name = json.dumps({
            "name": "other-id", "description": "d",
            "schema": "https://agentplugins.io/schema/v1",
            "skills": [{"name": "x", "description": "d"}], "mcpServers": {}})
        bad_json = "{not json"
        self.assertTrue(_looks_like_candidate(good, idea))
        self.assertFalse(_looks_like_candidate(bad_name, idea))
        self.assertFalse(_looks_like_candidate(bad_json, idea))

    def test_hook_shape_check(self):
        idea = {**_idea(), "file_kind": "hook"}
        good = json.dumps({"hooks": {"Stop": [{"matcher": "*",
            "hooks": [{"type": "command", "command": "true"}]}]}})
        self.assertTrue(_looks_like_candidate(good, idea))
        self.assertFalse(_looks_like_candidate(json.dumps({"hooks": {}}), idea))
        self.assertFalse(_looks_like_candidate("no json", idea))

    def test_rules_shape_check(self):
        idea = {**_idea(), "file_kind": "rules"}
        good = f"# {idea['id']}\n\n## Must never do\n- a\n\n## Must do\n- b\n\n## When unsure\n- c\n"
        self.assertTrue(_looks_like_candidate(good, idea))
        self.assertFalse(_looks_like_candidate("## Must never do\n- a\n", idea))

    def test_workflow_and_subagent_shape_checks(self):
        idea = {**_idea(), "file_kind": "workflow"}
        workflow = (f"---\nname: {idea['id']}\ndescription: d\n---\n"
                    "## Goal\ng\n## Steps\n1. s\n## Success criteria\nc\n")
        self.assertTrue(_looks_like_candidate(workflow, idea))
        self.assertFalse(_looks_like_candidate(f"---\nname: {idea['id']}\n---\nbody", idea))
        subagent_idea = {**_idea(), "file_kind": "subagent"}
        subagent = (f"---\nname: {subagent_idea['id']}\ndescription: d\ntools: [Read]\n---\n"
                    "## How you work\nh\n## What you never do\nn\n")
        self.assertTrue(_looks_like_candidate(subagent, subagent_idea))

    def test_undeclared_file_kind_is_refused(self):
        from tools.opencode_generation_lanes import LaneError, _idea_file_kind
        with self.assertRaises(LaneError):
            _idea_file_kind({"file_kind": "telepathy"})
        self.assertEqual(_idea_file_kind({}), "skill")

    def test_prompt_names_the_file_kind_contract(self):
        manifest_idea = {**_idea(), "file_kind": "plugin_manifest"}
        prompt = _render_prompt(manifest_idea)
        self.assertIn("Agent Plugins manifest", prompt)
        self.assertIn('"mcpServers"', prompt)
        self.assertIn("no secrets", prompt)

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


@unittest.skipUnless(find_spec("cryptography"), "cryptography creates the throwaway certificate authority")
class TacticalLaneThroughTheForwarderChecks(unittest.TestCase):
    """The Tactical lane end to end against a local origin whose certificate names another host than 127.0.0.1."""

    def test_a_request_through_the_lane_reaches_the_origin_verified_with_the_held_key(self):
        from tools.test_custom_endpoint_tls_trust import NAME, _certificates
        from tools.test_verified_forwarder import EVENTS, PLACEHOLDER, _OriginServer

        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        certificates = _certificates(Path(folder.name))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificates["leaf"], certificates["key"])
        origin = _OriginServer(context)
        threading.Thread(target=origin.serve_forever, daemon=True).start()
        self.addCleanup(origin.server_close)
        self.addCleanup(origin.shutdown)
        self.addCleanup(lanes.stop_forwarders)
        anchor = Path(certificates["anchor"])
        declared = {**DECLARED_ENDPOINTS["tactical"], "tls_ca_file": str(anchor),
                    "tls_ca_sha256": hashlib.sha256(anchor.read_bytes()).hexdigest()}
        environment = {**TACTICAL_ENVIRONMENT, "LOOP_ENGINE_TACTICAL_TLS_SERVER_NAME": NAME,
                       "LOOP_ENGINE_TACTICAL_BASE_URL": f"https://127.0.0.1:{origin.server_port}/v1"}
        # The fixture origin is local by necessity; the refusal of local upstreams has its own check above.
        with mock.patch.dict(os.environ, environment), mock.patch.dict(DECLARED_ENDPOINTS, {"tactical": declared}), \
                mock.patch.object(lanes, "FORBIDDEN_URL_PATTERNS", ()), \
                mock.patch.object(private_endpoints, "_keyring_value", _without_keyring), \
                tempfile.TemporaryDirectory() as temporary:
            lane_environment = _lane("tactical", "gemma-4-coding-abliterated", Path(temporary) / "lane").environment()
        request = urllib.request.Request(lane_environment[FORWARDER_URL_ENVIRONMENT] + "/chat/completions",
                                         data=b'{"model": "gemma-4-coding-abliterated", "stream": true}',
                                         headers={"Authorization": "Bearer " + PLACEHOLDER})
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.read(), b"".join(EVENTS))
        [sent] = origin.requests
        self.assertEqual(sent["path"], "/v1/chat/completions")
        self.assertEqual(sent["headers"]["Authorization"], "Bearer " + TACTICAL_ENVIRONMENT["TACTICAL_API_KEY"])


if __name__ == "__main__":
    unittest.main()