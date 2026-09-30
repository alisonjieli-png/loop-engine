"""Complete packages follow byte budgets and real pagination, not a file-count cutoff."""
from __future__ import annotations

import unittest
from unittest import mock

from loop_engine.core.service_runtime import catalogue_packages as packages
from loop_engine.core.service_runtime.http import protocol_tool_schema
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from licensed_import.harness_kinds import TreeEntry, plan_packages
from install_selected_material import NativePackageProjection


class PackageResourceChecks(unittest.TestCase):
    def files(self, count=79):
        return tuple(packages.CataloguePackageFile(f"scripts/tool_{index}.py", "a" * 64, 100,
                                                   "text/x-python", "skill_script")
                     for index in range(count))

    def test_a_complete_79_file_package_round_trips_and_keeps_every_path(self):
        package = packages.CataloguePackage(self.files())
        parsed = packages.parse_package_document(package.document())
        self.assertEqual(parsed, package)
        self.assertEqual(len(parsed.files), 79)
        self.assertEqual(parsed.file("scripts/tool_78.py").size_bytes, 100)

    def test_manifest_bytes_are_checked_before_json_decoding(self):
        with mock.patch.object(packages, "MAXIMUM_PACKAGE_MANIFEST_BYTES", 100), \
                mock.patch.object(packages.json, "loads", side_effect=AssertionError("must not parse oversized input")):
            with self.assertRaises(ServiceRuntimeError) as caught:
                packages.parse_package_document(b" " * 101)
        self.assertEqual(caught.exception.code, "package_manifest_too_large")

    def test_payload_and_single_file_resource_guards_remain_enforced(self):
        with self.assertRaises(ServiceRuntimeError):
            packages.CataloguePackageFile("huge", "a" * 64, packages.MAXIMUM_FILE_BYTES + 1, "text/plain", "other")
        files = tuple(packages.CataloguePackageFile(f"part{index}", "a" * 64, packages.MAXIMUM_FILE_BYTES,
                                                   "text/plain", "other") for index in range(5))
        with self.assertRaises(ServiceRuntimeError) as caught:
            packages.CataloguePackage(files)
        self.assertEqual(caught.exception.code, "package_too_large")

    def test_import_planning_keeps_complete_skill_helpers_and_contracts(self):
        names = ["SKILL.md", "LICENSE", "package.json", "docs/contract.md", "mcp/server.py"]
        names += [f"scripts/tool_{index}.py" for index in range(79)]
        plans, _ = plan_packages([TreeEntry(name, "100644", "blob", "a" * 40) for name in names],
                                 repository="example/complete-skill")
        skill = next(plan for plan in plans if plan.primary == "SKILL.md")
        self.assertEqual(set(skill.members), set(names))
        self.assertEqual(skill.problems, ())

    def test_native_projection_and_read_offset_do_not_reintroduce_the_64_file_limit(self):
        projection = NativePackageProjection("large-skill", "a" * 64, (),
            tuple((file.path, 0o644) for file in self.files()))
        self.assertEqual(len(projection.file_modes), 79)
        self.assertNotIn("maximum", protocol_tool_schema("read")["properties"]["file_offset"])


if __name__ == "__main__":
    unittest.main()
