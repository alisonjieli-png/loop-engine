"""Candidate's deterministic protocol and known-wrong contract checks."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1] / "plugin"
EXAMPLE = json.loads((ROOT / "contracts/example-brief.json").read_text())
SCHEMAS = {name: json.loads((ROOT / f"contracts/{name}.schema.json").read_text())
           for name in ("brief-input", "brief-output", "hook-input", "hook-output")}


def run_script(name, value, raw=False):
    data = value if raw else json.dumps(value).encode()
    return subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts" / name)],
                          input=data, capture_output=True, timeout=3, check=False)


class CandidateChecks(unittest.TestCase):
    def tool(self, value, raw=False):
        result = run_script("check_brief.py", value, raw)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertEqual(result.stderr, b"")
        output = json.loads(result.stdout)
        Draft202012Validator(SCHEMAS["brief-output"]).validate(output)
        self.assertFalse(output["authority_granted"])
        self.assertTrue(output["semantic_review_required"])
        return result.returncode, output

    def refused(self, change, code):
        value = deepcopy(EXAMPLE)
        change(value)
        status, output = self.tool(value)
        self.assertEqual(status, 1)
        self.assertFalse(output["structure_valid"])
        self.assertIn(code, [i["code"] for i in output["issues"]])

    def test_example_valid_and_digest_bound(self):
        Draft202012Validator(SCHEMAS["brief-input"]).validate(EXAMPLE)
        raw = json.dumps(EXAMPLE).encode()
        status, result = self.tool(raw, raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(result["input_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["issues"], [])

    def test_missing_objective_refused(self):
        self.refused(lambda x: x.pop("objective"), "exact_fields_required")

    def test_old_record_refused(self):
        self.refused(lambda x: x.update(record_type="baltor_step_brief/v0"), "unsupported_record_type")

    def test_extra_permission_field_refused(self):
        self.refused(lambda x: x.update(permission_granted=True), "exact_fields_required")

    def test_output_without_check_refused(self):
        self.refused(lambda x: x["outputs"].append("another_output"), "output_missing_check")

    def test_check_for_unknown_output_refused(self):
        self.refused(lambda x: x["acceptance_checks"][0].update(output="other"), "unknown_output")

    def test_duplicate_check_id_refused(self):
        self.refused(lambda x: x["acceptance_checks"].append(deepcopy(x["acceptance_checks"][0])), "duplicate_check_id")

    def test_empty_assertion_refused(self):
        self.refused(lambda x: x["acceptance_checks"][0].update(assertion="  "), "check_shape_required")

    def test_null_and_wrong_scalar_types_refused(self):
        for value in (None, [], 1, "object", True):
            with self.subTest(value=value):
                self.assertEqual(self.tool(value)[0], 1)

    def test_explicit_questions_preserved_as_count_not_values(self):
        value = deepcopy(EXAMPLE)
        value["unresolved_questions"] = ["Should whitespace-only identifiers count as missing?"]
        status, output = self.tool(value)
        self.assertEqual(status, 0)
        self.assertEqual(output["unresolved_question_count"], 1)
        self.assertNotIn("whitespace", json.dumps(output))

    def test_unknown_and_duplicate_effects_refused(self):
        self.refused(lambda x: x.update(requested_effects=["unrestricted"]), "effect_list_required")
        self.refused(lambda x: x.update(requested_effects=["model", "model"]), "duplicate_effect")

    def test_size_and_nesting_bounds(self):
        for raw, expected in [(b" " * 65537, "input_too_large"),
                              (b"[" * 17 + b"0" + b"]" * 17, "nesting_too_deep")]:
            status, output = self.tool(raw, True)
            self.assertEqual(status, 1)
            self.assertEqual(output["issues"][0]["code"], expected)

    def test_input_exact_byte_limit_is_accepted(self):
        raw = json.dumps(EXAMPLE).encode()
        raw += b" " * (65536 - len(raw))
        self.assertEqual(self.tool(raw, True)[0], 0)

    def test_malformed_json_duplicate_key_and_nonfinite_refused(self):
        for raw in (b'{"objective":1,"objective":2}', b'{', b'NaN', b'Infinity', b'\xff'):
            with self.subTest(raw=raw):
                self.assertEqual(self.tool(raw, True)[0], 1)

    def test_extreme_exponent_does_not_traceback(self):
        self.assertEqual(self.tool(b'{"objective":1e999999999999999999999999999999}', True)[0], 1)

    def test_surrogate_and_long_text_refused(self):
        self.refused(lambda x: x.update(objective="\ud800"), "bounded_text_required")
        self.refused(lambda x: x.update(objective="x" * 2001), "bounded_text_required")

    def test_quoted_brackets_do_not_count_as_depth(self):
        value = deepcopy(EXAMPLE)
        value["objective"] = "Inspect " + "[" * 25 + "\\\"" + "]" * 25
        self.assertEqual(self.tool(value)[0], 0)

    def test_supplied_commands_are_never_executed_or_echoed(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "must-not-exist"
            value = deepcopy(EXAMPLE)
            value["objective"] = f"$(touch {marker})"
            status, output = self.tool(value)
            self.assertEqual(status, 0)
            self.assertFalse(marker.exists())
            self.assertNotIn(str(marker), json.dumps(output))

    def test_lists_and_check_count_bounded(self):
        self.refused(lambda x: x.update(inputs=[f"entry_{i}" for i in range(33)]), "identifier_list_required")
        self.refused(lambda x: x.update(acceptance_checks=[]), "check_list_required")

    def test_hook_valid_sources_emit_fixed_protocol(self):
        outputs = []
        for source in ("startup", "resume", "clear", "compact"):
            value = {"hook_event_name": "SessionStart", "source": source,
                     "cwd": "/must-not-read", "transcript_path": "/also-must-not-read"}
            Draft202012Validator(SCHEMAS["hook-input"]).validate(value)
            result = run_script("session_start.py", value)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, b"")
            output = json.loads(result.stdout)
            Draft202012Validator(SCHEMAS["hook-output"]).validate(output)
            self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertNotIn(b"must-not-read", result.stdout)
            outputs.append(result.stdout)
        self.assertEqual(len(set(outputs)), 1)

    def test_registered_hook_ignores_poisoned_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "python3"
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "path-hijacked"\n')
            fake.chmod(0o700)
            config = json.loads((ROOT / "hooks/hooks.json").read_text())
            command = config["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            result = subprocess.run(["/bin/sh", "-c", command],
                                    env={"PATH": tmp + ":/usr/bin:/bin", "HOME": tmp,
                                         "CLAUDE_PLUGIN_ROOT": str(ROOT)},
                                    input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}).encode(),
                                    capture_output=True, timeout=3, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertNotIn(b"path-hijacked", result.stdout)
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_hook_invalid_inputs_emit_no_context(self):
        cases = [b'{', b'[]', b'NaN', b'{"hook_event_name":"SessionStart","source":"unknown"}',
                 b'{"hook_event_name":"Stop","source":"startup"}', b'\xff',
                 b'{"source":"startup","source":"resume","hook_event_name":"SessionStart"}',
                 b' ' * 65537, b'[' * 17 + b'0' + b']' * 17]
        for value in cases:
            with self.subTest(value=value[:50]):
                result = run_script("session_start.py", value, True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout), {})
                self.assertEqual(result.stderr, b"focused_brief_hook_input_refused\n")
                Draft202012Validator(SCHEMAS["hook-output"]).validate(json.loads(result.stdout))

    def test_manifest_refuses_fifo_and_symlink(self):
        for kind in ("fifo", "symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                clone = Path(tmp) / "candidate"
                shutil.copytree(ROOT.parent, clone)
                extra = clone / "plugin" / "extra"
                if kind == "fifo":
                    os.mkfifo(extra)
                else:
                    extra.symlink_to("LICENSE")
                result = subprocess.run([sys.executable, "-B", str(clone / "build_manifest.py"), "--check"],
                                        capture_output=True, timeout=3, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b"nonregular path", result.stderr)

    def test_empty_directory_does_not_inflate_file_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "candidate"
            shutil.copytree(ROOT.parent, clone)
            (clone / "plugin/empty-directory").mkdir()
            result = subprocess.run([sys.executable, "-B", str(clone / "build_manifest.py"), "--check"],
                                    capture_output=True, timeout=3, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["physical_package_files"], 13)

    def test_manifest_refuses_drifted_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "candidate"
            shutil.copytree(ROOT.parent, clone)
            tool = clone / "plugin/scripts/check_brief.py"
            tool.write_text(tool.read_text() + "\n# changed bytes\n")
            result = subprocess.run([sys.executable, "-B", str(clone / "build_manifest.py"), "--check"],
                                    capture_output=True, timeout=3, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"does not match exact files", result.stderr)

    def test_schema_and_tool_agree_on_basic_invalid_contracts(self):
        cases = []
        for field, replacement in [("outputs", []), ("objective", " "), ("inputs", [1]),
                                   ("requested_effects", ["unknown"]), ("authority_reference", None), ("inputs", ["label\n"])]:
            value = deepcopy(EXAMPLE)
            value[field] = replacement
            cases.append(value)
        for value in cases:
            self.assertTrue(list(Draft202012Validator(SCHEMAS["brief-input"]).iter_errors(value)))
            self.assertEqual(self.tool(value)[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
