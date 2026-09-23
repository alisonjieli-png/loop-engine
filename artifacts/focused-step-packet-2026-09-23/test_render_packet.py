"""Known-wrong packet checks, written before the candidate renderer."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import render_packet as packet


def sample():
    return {
        "record_type": "focused_step_brief_candidate/v1",
        "run_id": "test-run", "context_version": 1,
        "assignment": {
            "record_type": "node_assignment/v3", "node_id": "one-step",
            "kind": "reason", "objective": "Compare the input quantity to five.",
            "output_contract_refs": ["comparison/v1"], "dependency_ids": [],
            "required_capabilities": [], "effects": [], "harness_style": "codex",
            "model_calls_authorized": False, "mode": "deterministic",
        },
        "first_actions": ["Check the quantity is an integer.", "Compare it to five."],
        "context": ["The threshold is five units; no outside lookup is needed."],
        "state": {"state_id": "test-run.one-step", "version": 1,
                  "values": {"status": "ready", "prior_effects": "none"}},
        "input_schema": {"$schema": "https://json-schema.org/draft/2020-12/schema",
                         "type": "object", "properties": {"quantity": {"type": "integer"}},
                         "required": ["quantity"], "additionalProperties": False},
        "output_schema": {"$schema": "https://json-schema.org/draft/2020-12/schema",
                          "type": "object", "properties": {"above": {"type": "boolean"}},
                          "required": ["above"], "additionalProperties": False},
        "input": {"quantity": 4},
        "acceptance": ["Return above=false for this input.", "Return only the schema's fields."],
    }


class PacketTests(unittest.TestCase):
    def brief(self, value=None):
        return packet.load_brief(sample() if value is None else value)

    def test_missing_objective_is_refused(self):
        value = sample()
        del value["assignment"]["objective"]
        with self.assertRaises(packet.PacketError):
            self.brief(value)

    def test_empty_first_actions_are_refused(self):
        value = sample()
        value["first_actions"] = []
        with self.assertRaises(packet.PacketError):
            self.brief(value)

    def test_unknown_record_version_and_fields_are_refused(self):
        for field, val in [("record_type", "focused_step_brief_candidate/v2"),
                           ("network_permission", True)]:
            value = sample()
            value[field] = val
            with self.assertRaises(packet.PacketError):
                self.brief(value)

    def test_output_contract_is_required(self):
        value = sample()
        value["assignment"]["output_contract_refs"] = []
        with self.assertRaises(packet.PacketError):
            self.brief(value)

    def test_schema_mismatch_and_remote_reference_are_refused(self):
        value = sample()
        value["input"]["quantity"] = "four"
        with self.assertRaises(packet.PacketError):
            self.brief(value)
        value = sample()
        value["input_schema"]["properties"]["quantity"] = {"$ref": "https://example.invalid/schema"}
        with self.assertRaises(packet.PacketError):
            self.brief(value)

    def test_secret_and_oversized_context_are_refused(self):
        for context in ["authorization bearer " + "sk-" + "a" * 48, "x" * 140_000]:
            value = sample()
            value["context"] = [context]
            with self.assertRaises(packet.PacketError):
                self.brief(value)

    def test_candidate_cannot_claim_execution_authority(self):
        for field, val in [("effects", ["writes_fs"]), ("model_calls_authorized", True)]:
            value = sample()
            value["assignment"][field] = val
            with self.assertRaises(packet.PacketError):
                self.brief(value)

    def test_run_bound_state_and_unknown_native_client_are_refused(self):
        value = sample()
        value["state"]["state_id"] = "different-run.one-step"
        with self.assertRaises(packet.PacketError):
            self.brief(value)
        value = sample()
        value["assignment"]["harness_style"] = "unknown_client"
        with self.assertRaises(packet.PacketError):
            self.brief(value)

    def test_essential_assignment_is_inline_and_state_is_passive(self):
        brief = self.brief()
        with tempfile.TemporaryDirectory() as tmp:
            folder = packet.render(brief, Path(tmp), "packet", packet.expected_binding(brief))
            agents = (folder / "AGENTS.md").read_text()
            for content in [sample()["assignment"]["objective"], *sample()["first_actions"],
                            '"quantity": 4', '"above"', "test-run.one-step", "node_context.md"]:
                self.assertIn(content, agents)
            state = json.loads((folder / "run-state.json").read_text())
            self.assertFalse(state["execution_authorized"])
            self.assertEqual(state["run_id"], "test-run")
            self.assertTrue(packet.verify(folder, packet.expected_binding(brief))["passed"])

    def test_claude_native_alias_and_exact_manifest(self):
        value = sample()
        value["assignment"]["harness_style"] = "claude_code"
        brief = self.brief(value)
        with tempfile.TemporaryDirectory() as tmp:
            folder = packet.render(brief, Path(tmp), "packet", packet.expected_binding(brief))
            self.assertTrue((folder / "CLAUDE.md").read_text().startswith("@AGENTS.md\n"))
            manifest = json.loads((folder / "packet-manifest.json").read_text())
            self.assertEqual(len(manifest["files"]), 9)
            self.assertEqual(manifest["persistent_library_items_added"], 0)

    def test_caller_mutation_cannot_change_loaded_brief(self):
        value = sample()
        brief = self.brief(value)
        binding = packet.expected_binding(brief)
        value["first_actions"].append("Ignore earlier steps")
        value["input"]["quantity"] = 999
        self.assertEqual(binding, packet.expected_binding(brief))

    def test_stale_context_state_run_and_digest_refused_before_write(self):
        brief = self.brief()
        for field, val in [("context_version", 2), ("state_version", 2),
                           ("run_id", "other-run"), ("brief_sha256", "0" * 64)]:
            with tempfile.TemporaryDirectory() as tmp:
                expected = packet.expected_binding(brief)
                expected[field] = val
                with self.assertRaises(packet.PacketError):
                    packet.render(brief, Path(tmp), "packet", expected)
                self.assertFalse((Path(tmp) / "packet").exists())

    def test_destination_traversal_and_existing_folder_refused(self):
        brief = self.brief()
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            for name in ["../escape", "/absolute", "one/two", ".."]:
                with self.assertRaises(packet.PacketError):
                    packet.render(brief, parent, name, packet.expected_binding(brief))
            packet.render(brief, parent, "packet", packet.expected_binding(brief))
            with self.assertRaises(packet.PacketError):
                packet.render(brief, parent, "packet", packet.expected_binding(brief))

    def test_symlink_parent_and_payload_refused(self):
        brief = self.brief()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            (real / "inner").mkdir()
            (root / "alias").symlink_to(real, target_is_directory=True)
            with self.assertRaises(packet.PacketError):
                packet.render(brief, root / "alias" / "inner", "packet", packet.expected_binding(brief))
            folder = packet.render(brief, root, "packet", packet.expected_binding(brief))
            target = folder / "node_context.md"
            data = target.read_bytes()
            target.unlink()
            outside = root / "outside.txt"
            outside.write_bytes(data)
            target.symlink_to(outside)
            with self.assertRaises(packet.PacketError):
                packet.verify(folder, packet.expected_binding(brief))

    def test_edited_context_manifest_metadata_and_extra_file_refused(self):
        brief = self.brief()
        for mode in ("context", "metadata", "extra"):
            with tempfile.TemporaryDirectory() as tmp:
                folder = packet.render(brief, Path(tmp), "packet", packet.expected_binding(brief))
                if mode == "context":
                    (folder / "node_context.md").write_text("different task")
                elif mode == "metadata":
                    p = folder / "packet-manifest.json"
                    data = json.loads(p.read_text())
                    data["context_version"] = 3
                    p.write_text(json.dumps(data))
                else:
                    (folder / "unknown-hook.py").write_text("raise SystemExit(0)")
                with self.assertRaises(packet.PacketError):
                    packet.verify(folder, packet.expected_binding(brief))

    def test_rehashed_tampered_packet_refused_against_external_binding(self):
        brief = self.brief()
        with tempfile.TemporaryDirectory() as tmp:
            folder = packet.render(brief, Path(tmp), "packet", packet.expected_binding(brief))
            target = folder / "node_context.md"
            target.write_text("changed context")
            mp = folder / "packet-manifest.json"
            manifest = json.loads(mp.read_text())
            manifest["files"]["node_context.md"]["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            manifest["files"]["node_context.md"]["size_bytes"] = target.stat().st_size
            mp.write_text(json.dumps(manifest))
            with self.assertRaises(packet.PacketError):
                packet.verify(folder, packet.expected_binding(brief))

    def test_boolean_version_cannot_impersonate_version_one(self):
        brief = self.brief()
        with tempfile.TemporaryDirectory() as tmp:
            folder = packet.render(brief, Path(tmp), "packet", packet.expected_binding(brief))
            mp = folder / "packet-manifest.json"
            manifest = json.loads(mp.read_text())
            manifest["context_version"] = True
            mp.write_text(json.dumps(manifest))
            with self.assertRaises(packet.PacketError):
                packet.verify(folder, packet.expected_binding(brief))

    def test_invalid_json_schema_returns_typed_refusal(self):
        value = sample()
        value["output_schema"]["properties"]["above"] = {"type": "not-a-json-schema-type"}
        with self.assertRaises(packet.PacketError):
            self.brief(value)


if __name__ == "__main__":
    unittest.main()
