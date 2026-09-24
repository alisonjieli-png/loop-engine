"""Checks for harness file classification and normalization into catalogue_package/v1.

```text
Classification and packaging
├── every native kind is found by its path, and a vendored or fixture copy is not
├── a nested skill is its own package, never part of the folder above it
├── a plugin is imported as parts: each part names its plugin, no file is in two packages
├── schemas and code modules are found only where a source declares them
├── a symbolic link or submodule inside a package is a problem, never a silent omission
└── a copied package holds every member byte for byte, the licence text, an attribution file,
    a valid outside provenance record and a process effect when it holds an executable file
```

Known-wrong packages refused by name: a path the catalogue refuses (a
space in a file name), a primary file that is not text, a primary file too
short to be material. No network, process or model is used.
"""
from __future__ import annotations

import json
import unittest

import test_licensed_import_support as support
from loop_engine.core.library_ingestion.provenance import read_outside_provenance
from loop_engine.core.library_ingestion.record_rules import git_blob_identity
from loop_engine.core.service_runtime.catalogue_packages import parse_package_document

from licensed_import.checks import package_effects
from licensed_import.harness_kinds import (
    BLOB_TYPE, SYMLINK_MODE, SourceScope, TreeEntry, file_role, placements, plan_packages)
from licensed_import.licensing import decide_package
from licensed_import.packaging import PackageRefused, build_candidate, fetch_identity
from licensed_import.records import (
    CODE_MODULE, COMMAND, CONTRACT_SCHEMA, HOOK, INSTRUCTION_FILE, MARKETPLACE, PLUGIN_MANIFEST, PROTOCOL_SERVER,
    RULES, SKILL, SUBAGENT)

TREE = ["LICENSE", "README.md", "AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md",
        "skills/pdf/SKILL.md", "skills/pdf/scripts/extract.py", "skills/pdf/references/api.md",
        "skills/pdf/sub/SKILL.md", "plugins/review/.claude-plugin/plugin.json", "plugins/review/agents/reviewer.md",
        "plugins/review/commands/review.md", "plugins/review/hooks/hooks.json", "plugins/review/hooks/check.sh",
        "plugins/review/skills/lint/SKILL.md", ".claude/agents/planner.md", ".claude/commands/deploy.md",
        ".cursor/rules/python.mdc", "prompts/tests.prompt.md", "agents/security.agent.md", ".mcp.json",
        ".claude-plugin/marketplace.json", ".opencode/tool/lookup.ts", "node_modules/x/SKILL.md",
        "tests/fixtures/y/SKILL.md", "schemas/a.json", "docs/agents/notes.md"]


def _entries(paths, modes=None):
    modes = modes or {}
    return [TreeEntry(path, modes.get(path, "100644"), BLOB_TYPE, git_blob_identity(path.encode())) for path in paths]


class ClassificationChecks(unittest.TestCase):
    def setUp(self):
        self.plans, _skipped = plan_packages(_entries(TREE), repository="acme/tools")
        self.by_primary = {plan.primary: plan for plan in self.plans}

    def test_every_native_kind_is_found_by_its_path(self):
        expected = {"AGENTS.md": INSTRUCTION_FILE, "CLAUDE.md": INSTRUCTION_FILE,
                    ".github/copilot-instructions.md": INSTRUCTION_FILE, "skills/pdf/SKILL.md": SKILL,
                    "plugins/review/.claude-plugin/plugin.json": PLUGIN_MANIFEST,
                    "plugins/review/agents/reviewer.md": SUBAGENT, "plugins/review/commands/review.md": COMMAND,
                    "plugins/review/hooks/hooks.json": HOOK, ".claude/agents/planner.md": SUBAGENT,
                    ".claude/commands/deploy.md": COMMAND, ".cursor/rules/python.mdc": RULES,
                    "prompts/tests.prompt.md": COMMAND, "agents/security.agent.md": SUBAGENT,
                    ".mcp.json": PROTOCOL_SERVER, ".claude-plugin/marketplace.json": MARKETPLACE,
                    ".opencode/tool/lookup.ts": CODE_MODULE}
        for primary, kind in expected.items():
            self.assertIn(primary, self.by_primary, primary)
            self.assertEqual(self.by_primary[primary].kind, kind, primary)

    def test_vendored_fixture_and_unrelated_files_are_not_packages(self):
        for path in ("node_modules/x/SKILL.md", "tests/fixtures/y/SKILL.md", "docs/agents/notes.md", "README.md",
                     "schemas/a.json", "LICENSE"):
            self.assertNotIn(path, self.by_primary, path)

    def test_a_nested_skill_is_its_own_package(self):
        outer = self.by_primary["skills/pdf/SKILL.md"]
        self.assertNotIn("skills/pdf/sub/SKILL.md", outer.members)
        self.assertEqual(self.by_primary["skills/pdf/sub/SKILL.md"].root, "skills/pdf/sub")

    def test_a_plugin_is_imported_as_parts_and_no_file_is_in_two_packages(self):
        members = [path for plan in self.plans for path in plan.members]
        self.assertEqual(len(members), len(set(members)))
        for primary in ("plugins/review/agents/reviewer.md", "plugins/review/skills/lint/SKILL.md",
                        "plugins/review/hooks/hooks.json"):
            self.assertEqual(self.by_primary[primary].plugin["root"], "plugins/review", primary)
        self.assertEqual(self.by_primary["plugins/review/hooks/hooks.json"].members,
                         ("plugins/review/hooks/check.sh", "plugins/review/hooks/hooks.json"))

    def test_schemas_and_code_modules_are_found_only_where_declared(self):
        declared = SourceScope((CONTRACT_SCHEMA,), ("schemas/*.json",))
        plans, _ = plan_packages(_entries(TREE), declared, "acme/tools")
        self.assertEqual([plan.primary for plan in plans], ["schemas/a.json"])

    def test_a_symbolic_link_in_a_skill_folder_is_a_problem(self):
        plans, _ = plan_packages(_entries(TREE + ["skills/pdf/link"], {"skills/pdf/link": SYMLINK_MODE}),
                                 repository="acme/tools")
        plan = next(plan for plan in plans if plan.primary == "skills/pdf/SKILL.md")
        self.assertEqual(plan.problems, ("symbolic_link_in_package",))

    def test_roles_and_placements(self):
        plan = self.by_primary["skills/pdf/SKILL.md"]
        roles = {path: file_role(plan.kind, plan.root, path) for path in plan.members}
        self.assertEqual(roles, {"skills/pdf/SKILL.md": "skill_definition", "skills/pdf/scripts/extract.py":
                                 "skill_script", "skills/pdf/references/api.md": "skill_reference"})
        harnesses = {row["harness"] for row in placements(plan)}
        self.assertTrue({"upstream", "claude-code", "codex", "opencode"} <= harnesses)


def _build(files, licences, *, primary="skills/demo/SKILL.md", repository="acme/tools"):
    files = {path: value if isinstance(value, bytes) else value.encode() for path, value in files.items()}
    licence_bytes = {path: value.encode() for path, value in licences.items()}
    plans, _ = plan_packages(_entries(sorted(files)), repository=repository)
    plan = next(plan for plan in plans if plan.primary == primary)
    decision = decide_package(files, plan.primary, licence_bytes, github_spdx="MIT")
    oids = {path: git_blob_identity(payload) for path, payload in {**files, **licence_bytes}.items()}
    roles = {path: file_role(plan.kind, plan.root, path) for path in files}
    effects, evidence = package_effects(plan.kind, files, roles)
    fetch, request = fetch_identity("fake_snapshot", repository, "c" * 40)
    return build_candidate(plan=plan, repository=repository, commit="c" * 40, fetched_at="2026-09-24T00:00:00Z",
                           member_bytes=files, oids=oids, licence=decision, licence_bytes=licence_bytes, findings=[],
                           effects=effects, effect_evidence=evidence, sources=["test"], fetch_digest=fetch,
                           request_digest=request, imported_on="2026-09-24", repository_facts={"name": repository})


class PackagingChecks(unittest.TestCase):
    def test_a_copied_package_is_complete_and_valid(self):
        script = b"import sys\nprint(sys.argv)\n"
        built = _build({"skills/demo/SKILL.md": support.skill("demo"), "skills/demo/scripts/run.py": script},
                       {"LICENSE": support.MIT})
        payload = built.payload
        paths = {entry["path"]: entry for entry in payload["package"]["files"]}
        self.assertEqual(set(paths), {"SKILL.md", "scripts/run.py", "LICENSE", "ATTRIBUTION.md"})
        self.assertEqual(paths["SKILL.md"]["digest"], built.package.file("SKILL.md").digest)
        self.assertEqual(parse_package_document(built.package.document()).package_digest, payload["package_digest"])
        self.assertEqual(read_outside_provenance(payload["provenance"]).decision, "verbatim_permitted")
        self.assertIn("spawns_process", payload["declared_effects"])
        attribution = built.bodies[paths["ATTRIBUTION.md"]["digest"]].decode()
        for entry in payload["files"]:
            if entry["upstream_path"]:
                self.assertIn(entry["upstream_path"], attribution)
        self.assertEqual({entry["origin"] for entry in payload["files"]}, {"upstream", "licence_text", "attribution"})

    def test_known_wrong_packages_are_refused_by_name(self):
        cases = {"package_path_invalid": {"skills/demo/SKILL.md": support.skill("demo"),
                                          "skills/demo/my notes.md": b"notes"},
                 "primary_file_not_text": {"skills/demo/SKILL.md": b"\xff\xfe\x00binary"},
                 "primary_file_too_short": {"skills/demo/SKILL.md": b"---\nname: x\n---\nhi\n"}}
        for code, files in cases.items():
            with self.assertRaises(PackageRefused) as raised:
                _build(files, {"LICENSE": support.MIT})
            self.assertEqual(raised.exception.code, code)

    def test_a_file_that_names_another_upstream_gets_a_caution(self):
        body = support.skill("demo").decode().replace("description:", "source: github.com/other/original\ndescription:")
        built = _build({"skills/demo/SKILL.md": body}, {"LICENSE": support.MIT})
        self.assertIn("names_another_upstream_source", {row["rule"] for row in built.payload["findings"]})

    def test_import_claims_only_the_evidence_states_it_establishes(self):
        built = _build({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": support.MIT})
        self.assertEqual(built.payload["evidence"], {"resolved": True, "materialized": True, "available": False,
                                                     "loaded": False, "used": False, "verified": False})
        self.assertEqual(built.payload["compatibility"]["package_format"], "catalogue_package/v1")
        self.assertEqual({row["support"] for row in built.payload["placements"]}, {"unverified"})
        self.assertEqual({row["scope"] for row in built.payload["placements"]}, {"upstream", "project"})

    def test_the_record_carries_no_state_that_could_approve_it(self):
        built = _build({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": support.MIT})
        text = json.dumps(built.payload)
        self.assertEqual(built.payload["lifecycle"], "candidate")
        self.assertEqual(built.payload["qualification"], "not_independently_reviewed")
        self.assertNotIn("approved", text.replace("not reviewed or approved", ""))


if __name__ == "__main__":
    unittest.main()
