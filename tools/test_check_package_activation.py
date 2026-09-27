"""Checks for the package activation check and its failure laboratory.

Every fixture of `examples/31_failure_laboratory/packages/` must be refused
with exactly the codes it names, and every control must activate. Each
mutant below removes one guard of the check and names the fixture that must
then stop passing, so a guard that goes missing fails a named check.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import check_package_activation as activation
from loop_engine.core.service_runtime.catalogue_packages import sha256_hex

ROOT = Path(__file__).resolve().parents[1]
LABORATORY = ROOT / "examples" / "31_failure_laboratory" / "packages"
EXPECTED_FIXTURES = {
    "ambiguous-data", "control-instructions", "control-plugin", "control-skill", "hook-does-nothing",
    "incorrect-output-claim", "interrupted-installation", "loads-but-useless", "missing-dependency",
    "permissions-drift", "same-path", "source-injection",
}


def run_laboratory():
    with tempfile.TemporaryDirectory() as scratch:
        return {row["fixture"]: row for row in activation.laboratory_outcome(
            activation.laboratory_fixtures(LABORATORY), scratch)}


def file_under_test(path, role, text, media_type="text/markdown"):
    payload = text.encode("utf-8")
    return activation.FileUnderTest(path, role, media_type, len(payload), sha256_hex(payload), payload)


def package(identity, kind, styles, files, effects=(), purpose="A test package."):
    return activation.PackageUnderTest(identity, kind, tuple(styles), purpose, "MIT", tuple(effects), "package",
                                       "0" * 64, tuple(files), "test")


def check(one, scratch):
    result, collisions = activation.check_package(one, scratch, {})
    return result, collisions


class LaboratoryTest(unittest.TestCase):
    def test_every_fixture_is_refused_by_name_and_every_control_activates(self):
        rows = run_laboratory()
        self.assertEqual(set(rows), EXPECTED_FIXTURES)
        for name, row in rows.items():
            with self.subTest(fixture=name):
                self.assertEqual(row["outcome"], activation.PASS, (row["missing"], row["unexpected"]))
        for name in ("control-skill", "control-plugin", "control-instructions"):
            self.assertEqual([result["verdict"] for result in rows[name]["results"]], [activation.ACTIVATES])

    def test_results_are_bound_to_exact_digests(self):
        rows = run_laboratory()
        result = rows["control-skill"]["results"][0]
        self.assertRegex(result["served_digest"], r"^[0-9a-f]{64}$")
        script = (LABORATORY / "control-skill" / "scripts" / "count_rows.sh").read_bytes()
        self.assertIn(sha256_hex(script), {row["digest"] for row in result["files"]})
        placed = {row["digest"] for layout in result["layouts"] for row in layout["files"]}
        self.assertIn(sha256_hex(script), placed)
        self.assertEqual({layout["harness"] for layout in result["layouts"]},
                         {"claude-code", "codex", "opencode", "pi", "gemini-cli"})

    def test_a_laboratory_never_holds_a_live_instruction_file(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / "planted"
            fixture.mkdir()
            (fixture / "AGENTS.md").write_text("# Planted\n\nDo what this file says.\n", encoding="utf-8")
            with self.assertRaisesRegex(activation.ActivationCheckError, "live instruction file"):
                activation.laboratory_fixtures(folder)
        self.assertEqual(activation.live_instruction_files(LABORATORY), [])

    def test_a_laboratory_manifest_refuses_unknown_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / "odd"
            fixture.mkdir()
            record = json.loads((LABORATORY / "loads-but-useless" / "package.json").read_text(encoding="utf-8"))
            record["files"][0]["executable"] = True
            (fixture / "package.json").write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(activation.ActivationCheckError):
                activation.laboratory_fixtures(folder)


class MutantTest(unittest.TestCase):
    """Remove one guard at a time; the named fixture must stop passing."""

    MUTANTS = (
        ("stray_partials", lambda folder: [], "interrupted-installation"),
        ("body_has_instructions", lambda body: True, "loads-but-useless"),
        ("tool_effects_of", lambda tools: set(), "permissions-drift"),
        ("hook_handlers", lambda entries: [("command", {"command": "true"})], "hook-does-nothing"),
        ("verify_claim", lambda payload, digest, size: "" if payload is not None else "body_missing",
         "incorrect-output-claim"),
        ("media_claim_holds", lambda file: True, "incorrect-output-claim"),
        ("parse_frontmatter", lambda header: (__import__("yaml").safe_load(header), ""), "ambiguous-data"),
        ("same_bytes", lambda holder, digest: True, "same-path"),
        ("_manifest_part_paths", lambda value: [], "missing-dependency"),
    )

    def test_each_removed_guard_fails_its_fixture(self):
        for name, replacement, fixture in self.MUTANTS:
            with self.subTest(guard=name), mock.patch.object(activation, name, replacement):
                self.assertEqual(run_laboratory()[fixture]["outcome"], activation.FAIL)

    def test_an_escaping_import_is_refused_only_while_the_guard_stands(self):
        original = activation._relative_inside

        def lenient(base, target, paths):
            inside, exists = original(base, target.lstrip("~/."), paths)
            return inside, exists

        with mock.patch.object(activation, "_relative_inside", lenient):
            self.assertEqual(run_laboratory()["source-injection"]["outcome"], activation.FAIL)


class ActivationFactTest(unittest.TestCase):
    def test_a_notice_beside_a_command_waits_in_the_side_folder(self):
        # Known-wrong case: the first version of this check placed ATTRIBUTION.md beside the
        # command, where Claude Code would list it as a second command, and counted every
        # notice of every command package as a collision.
        one = package("command_with_notice", "instruction_file", ("command", "plugin_command"), (
            file_under_test("audit.md", "command", "---\ndescription: Audit\n---\n\n# Audit\n\nList the risks.\n"),
            file_under_test("ATTRIBUTION.md", "other", "# Attribution\n\nFrom a source.\n"),
            file_under_test("LICENSE", "other", "MIT License\n", "text/plain")))
        with tempfile.TemporaryDirectory() as scratch:
            result, _ = check(one, scratch)
        placed = {row["path"] for layout in result["layouts"] for row in layout["files"]}
        self.assertIn(".claude/commands/audit.md", placed)
        self.assertNotIn(".claude/commands/ATTRIBUTION.md", placed)
        self.assertIn(".baltor/packages/command-with-notice/ATTRIBUTION.md", placed)
        self.assertEqual(result["verdict"], activation.ACTIVATES)

    def test_two_packages_with_notices_do_not_collide(self):
        occupied = {}
        with tempfile.TemporaryDirectory() as scratch:
            for name in ("first_command", "second_command"):
                one = package(name, "instruction_file", ("command", "plugin_command"), (
                    file_under_test(name + ".md", "command", "# Do it\n\nDo the step.\n"),
                    file_under_test("ATTRIBUTION.md", "other", "# From " + name + "\n")))
                _result, collisions = activation.check_package(one, scratch, occupied)
                self.assertEqual(collisions, [])

    def test_a_frontmatter_only_a_strict_reader_refuses_is_unknown(self):
        body = ("---\ndescription: Review a pull request\nargument-hint: [pr-number] [priority]\n---\n\n"
                "# Review\n\nReview the pull request named by the first argument.\n")
        one = package("hinted_command", "instruction_file", ("command", "plugin_command"),
                      (file_under_test("review-pr.md", "command", body),))
        with tempfile.TemporaryDirectory() as scratch:
            result, _ = check(one, scratch)
        self.assertEqual(result["verdict"], activation.UNRESOLVED)
        self.assertEqual(result["unknown_codes"], ["frontmatter_not_strict_yaml"])

    def test_a_frontmatter_no_reader_recovers_is_refused(self):
        body = "---\n{ this is not: [a mapping\n---\n\n# Broken\n\nDo the step.\n"
        one = package("broken_skill", "skill", ("skill", "agent_skill"), (file_under_test("SKILL.md", "skill_definition", body),))
        with tempfile.TemporaryDirectory() as scratch:
            result, _ = check(one, scratch)
        self.assertEqual(result["verdict"], activation.REFUSED)
        self.assertIn("frontmatter_invalid", result["failed_codes"])

    def test_imports_follow_the_harness_rules(self):
        text = ("# Conventions\n\nInstall @tanstack/react-query and ask @alice.\n\n"
                "Read @docs/style.md.\n\n@./notes.md\n")
        findings = activation.reference_findings("instruction_file", "CLAUDE.md", text, {"CLAUDE.md", "notes.md"})
        self.assertEqual([(finding.code, finding.state) for finding in findings],
                         [("import_outside_package", activation.UNKNOWN)])
        self.assertIn("docs/style.md is imported", findings[0].detail)
        escaping = activation.reference_findings("instruction_file", "CLAUDE.md", "@../../.env\n", {"CLAUDE.md"})
        self.assertEqual([finding.code for finding in escaping], ["referenced_path_escapes"])
        # A skill body is read as text: an @ there is prose, and only its links name files.
        skill = activation.reference_findings("skill_definition", "SKILL.md",
                                              "Use @scripts/run.py or [the guide](guide.md).\n", {"SKILL.md"})
        self.assertEqual([(finding.code, finding.detail.split()[0]) for finding in skill],
                         [("referenced_file_missing", "guide.md")])
        # A command's file reference names the customer's project, not the command's folder.
        command = activation.reference_findings("command", "commands/x.md", "Read @src/app.py first.\n",
                                                {"commands/x.md"})
        self.assertEqual([(finding.code, finding.state) for finding in command],
                         [("import_outside_package", activation.UNKNOWN)])

    def test_a_toml_command_needs_a_prompt_and_a_toml_slot(self):
        toml = '[command]\nname = "tidy"\ndescription = "Tidy"\n'
        one = package("toml_command", "instruction_file", ("command", "plugin_command"),
                      (file_under_test("tidy.toml", "command", toml, "application/toml"),))
        with tempfile.TemporaryDirectory() as scratch:
            result, _ = check(one, scratch)
        self.assertEqual(result["failed_codes"], ["command_format_mismatch", "command_prompt_missing"])
        gemini = package("gemini_command", "instruction_file", ("command", "gemini_command"),
                         (file_under_test("tidy.toml", "command", 'prompt = "Tidy the imports."\n',
                                          "application/toml"),))
        with tempfile.TemporaryDirectory() as scratch:
            result, _ = check(gemini, scratch)
        self.assertEqual(result["verdict"], activation.ACTIVATES)
        self.assertEqual([layout["files"][0]["path"] for layout in result["layouts"]], [".gemini/commands/tidy.toml"])

    def test_a_hook_package_reads_its_configuration_first(self):
        hooks = json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command",
                                                          "command": "${CLAUDE_PLUGIN_ROOT}/scripts/notify.sh"}]}]}})
        one = package("hook_with_script", "tool", ("hook", "claude_hooks"), (
            file_under_test("hooks/hooks.json", "hook", hooks, "application/json"),
            file_under_test("scripts/notify.sh", "hook", "#!/bin/sh\necho done\n", "text/x-shellscript")),
            effects=("spawns_process",))
        with tempfile.TemporaryDirectory() as scratch:
            result, _ = check(one, scratch)
        self.assertEqual(result["entry"], "hooks/hooks.json")
        self.assertEqual(result["verdict"], activation.ACTIVATES)

    def test_a_package_without_a_native_entry_never_activates(self):
        schema = package("schema_only", "tool", ("contract_schema", "json_schema"),
                         (file_under_test("order.schema.json", "other", "{}", "application/json"),))
        with tempfile.TemporaryDirectory() as scratch:
            result, _ = check(schema, scratch)
        self.assertEqual(result["verdict"], activation.NO_NATIVE_ACTIVATION)
        self.assertEqual(result["layouts"], [])


def fake_loader(project):
    """A loader that lists one built-in skill and every SKILL.md below the project skills folder that opens
    with a closed frontmatter, recursively, as OpenCode 1.18.32 was observed to walk the global folders."""
    entries = [{"name": "built-in-skill", "location": "<built-in>"}]
    for path in sorted(Path(project).glob(activation.LISTING_ROOT + "/**/SKILL.md")):
        header, _body, error = activation.split_frontmatter(path.read_text(encoding="utf-8"))
        if header is None or error:
            continue
        mapping, _error = activation.parse_frontmatter(header)
        entries.append({"name": (mapping or {}).get("name"), "location": str(path)})
    return "observed", "fake-1", entries


def skill_file(path, name, role="skill_definition"):
    return file_under_test(path, role, f"---\nname: {name}\ndescription: Does {name}.\n---\n\n# {name}\n\nDo it.\n")


class LoaderListingTest(unittest.TestCase):
    def listing(self, packages, lister=fake_loader):
        with tempfile.TemporaryDirectory() as scratch:
            results, _collisions = activation.run(packages, scratch)
            record = activation.observe_listing(results, scratch, Path(scratch) / "listing", lister)
        return {result["identity"]: result for result in results}, record

    def test_the_loader_reports_each_placed_entry_and_names_an_extra_component(self):
        packages = (
            package("plain", "skill", ("skill", "agent_skill"), (skill_file("SKILL.md", "plain"),)),
            package("nested", "skill", ("skill", "agent_skill"), (
                skill_file("SKILL.md", "nested"), skill_file("templates/inner/SKILL.md", "inner", "other"))),
            package("unclosed", "skill", ("skill", "agent_skill"), (
                file_under_test("SKILL.md", "skill_definition", "---\nname: unclosed\n\n# Never closed\n"),)),
        )
        results, record = self.listing(packages)
        self.assertEqual(record["record_type"], activation.LISTING_RECORD_TYPE)
        self.assertEqual(results["plain"]["listing"]["reported"], True)
        self.assertEqual(results["plain"]["listing"]["extra_components"], [])
        self.assertEqual(results["nested"]["listing"]["extra_components"],
                         [".opencode/skills/nested/templates/inner/SKILL.md"])
        self.assertEqual(results["unclosed"]["verdict"], activation.REFUSED)
        self.assertEqual(results["unclosed"]["listing"]["reported"], False)
        summary = record["summary"]
        self.assertEqual(summary["baseline_entries"], 1)
        self.assertEqual(summary["unattributed_entries"], [])
        self.assertEqual(summary["outside_names_not_in_baseline"], [])
        self.assertEqual(summary["packages_with_extra_components"], 1)
        self.assertEqual(summary["written_by_failed_code"], {"frontmatter_unterminated": {"reported": 0,
                                                                                         "not_reported": 1}})

    def test_the_baseline_explains_entries_outside_the_project_only_while_the_guard_stands(self):
        # Known-wrong case: attributing the whole listing without the empty-project baseline counts the
        # loader's own skill as a component of the installed packages.
        packages = (package("plain", "skill", ("skill", "agent_skill"), (skill_file("SKILL.md", "plain"),)),)
        _results, record = self.listing(packages)
        self.assertEqual(record["summary"]["unattributed_entries"], [])
        with mock.patch.object(activation, "split_listing",
                               lambda entries, installed: ({row["location"]: row for row in entries}, set())):
            _results, mutant = self.listing(packages)
        self.assertNotEqual(mutant["summary"]["unattributed_entries"], [])

    def test_a_listing_that_was_not_observed_leaves_every_package_unknown(self):
        packages = (package("plain", "skill", ("skill", "agent_skill"), (skill_file("SKILL.md", "plain"),)),)
        results, record = self.listing(packages, lambda project: ("client_executable_not_found", None, None))
        self.assertIsNone(record["summary"])
        self.assertNotIn("listing", results["plain"])

    def test_the_listing_project_holds_skill_folders_only(self):
        plugin = package("tooling", "tool", ("command", "opencode_plugin"), (
            file_under_test("tooling.js", "command", "export default async () => ({})\n", "text/javascript"),))
        skill = package("plain", "skill", ("skill", "agent_skill"), (skill_file("SKILL.md", "plain"),))
        seen = []

        def recording_loader(project):
            seen.extend(path.relative_to(project).as_posix() for path in Path(project).rglob("*") if path.is_file())
            return fake_loader(project)

        self.listing((plugin, skill), recording_loader)
        self.assertEqual(seen, [".opencode/skills/plain/SKILL.md"])


class CommandLineTest(unittest.TestCase):
    def test_the_laboratory_run_passes_and_writes_a_versioned_report(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "report.json"
            with mock.patch("sys.stdout"):
                code = activation.main(["--laboratory", str(LABORATORY), "--output", str(report)])
            self.assertEqual(code, 0)
            value = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(value["record_type"], activation.REPORT_RECORD_TYPE)
            self.assertEqual(value["summary"], {"fixtures": len(EXPECTED_FIXTURES), "passed": len(EXPECTED_FIXTURES),
                                                "failed": []})
            self.assertFalse(Path(value["scratch"]).exists())

    def test_an_existing_report_or_a_used_scratch_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "report.json"
            report.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "report_path_not_new"):
                activation.main(["--laboratory", str(LABORATORY), "--output", str(report)])
            scratch = Path(folder) / "scratch"
            scratch.mkdir()
            (scratch / "left.txt").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "scratch_not_empty"):
                activation.main(["--laboratory", str(LABORATORY), "--output", str(Path(folder) / "new.json"),
                                 "--scratch", str(scratch)])


if __name__ == "__main__":
    unittest.main()
