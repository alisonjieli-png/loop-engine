"""Ratchet and source-of-truth tests for tools/surface_inventory.py."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import surface_inventory  # noqa: E402


class SurfaceInventoryTests(unittest.TestCase):
    """Verify the eight-category surface inventory and its baseline ratchet."""

    inventory: dict
    baseline: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = surface_inventory.build_inventory()
        baseline_path = ROOT / "tools" / "surface_inventory_baseline.json"
        cls.baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    def test_all_eight_categories_are_populated(self) -> None:
        self.assertEqual(
            tuple(self.inventory["items"].keys()),
            surface_inventory.CATEGORIES,
        )
        for category in surface_inventory.CATEGORIES:
            items = self.inventory["items"][category]
            self.assertTrue(items, f"category {category} must not be empty")
            for item in items:
                self.assertEqual(item["category"], category)
                self.assertTrue(item["id"])
                self.assertTrue(item["source_file"])
                self.assertTrue(
                    item["component_guide"],
                    f"item {category}:{item['id']} must map to a component guide",
                )

    def test_sources_of_truth_match_live_repository(self) -> None:
        site_map = json.loads(
            (ROOT / "src/loop_engine/core/service_runtime/web_site_map.json").read_text(
                encoding="utf-8"
            )
        )
        screens = self.inventory["items"]["screens"]
        hostnames = [i for i in screens if i["subcategory"] == "baltor_hostname"]
        pages = [i for i in screens if i["subcategory"] == "baltor_site_map_page"]
        spa_views = [i for i in screens if i["subcategory"] == "spa_view"]
        self.assertEqual(len(hostnames), len(site_map["hostnames"]))
        self.assertEqual(len(pages), len(site_map["pages"]))
        self.assertGreaterEqual(len(spa_views), 36)

        forbidden = json.loads(
            (ROOT / "src/loop_engine/forbidden_paths.json").read_text(encoding="utf-8")
        )
        prod_net_modules = {
            m if m.startswith("src/") else f"src/loop_engine/{m}"
            for m in forbidden["network_allowed_modules"]
            if not m.endswith(("_checks.py", "_fake.py", "_test_fixtures.py"))
        }
        transfers = self.inventory["items"]["data_transfer"]
        outbound = [i for i in transfers if i["subcategory"] == "outbound_network_module"]
        self.assertEqual(len(outbound), len(prod_net_modules))

        storage = self.inventory["items"]["data_storage"]
        record_kinds = [i for i in storage if i["subcategory"] == "record_kind"]
        stores = [i for i in storage if i["subcategory"] == "store_backend"]
        self.assertEqual(len(record_kinds), 53)
        self.assertEqual(len(stores), 6)

        workflows = sorted((ROOT / ".github/workflows").glob("*.yml"))
        bg = self.inventory["items"]["background_work"]
        bg_workflows = [i for i in bg if i["subcategory"] == "github_workflow"]
        bg_tasks = [i for i in bg if i["subcategory"] == "service_lifespan_task"]
        self.assertEqual(len(bg_workflows), len(workflows))
        self.assertEqual(len(bg_tasks), 4)

    def test_baseline_ratchet_passes_on_current_repo(self) -> None:
        errors = surface_inventory.check_against_baseline(self.inventory, self.baseline)
        self.assertEqual(errors, [])

    def test_markdown_report_is_up_to_date(self) -> None:
        report_path = ROOT / "docs/verification/SURFACE-COVERAGE-2026-10-16.md"
        self.assertTrue(report_path.is_file(), "verification report must exist")
        expected = surface_inventory.render_markdown_report(self.inventory)
        actual = report_path.read_text(encoding="utf-8")
        self.assertEqual(actual, expected)

    def test_mutant_control_rejects_dropped_item_and_new_gaps(self) -> None:
        # Mutant 1: remove a covered screen item.
        dropped = copy.deepcopy(self.inventory)
        removed_item = dropped["items"]["screens"].pop(0)
        errors_dropped = surface_inventory.check_against_baseline(dropped, self.baseline)
        self.assertTrue(
            any("item count dropped" in err for err in errors_dropped),
            errors_dropped,
        )
        self.assertTrue(
            any(removed_item["id"] in err and "was removed" in err for err in errors_dropped),
            errors_dropped,
        )

        # Mutant 2: regress a covered function item so it loses test coverage.
        regressed = copy.deepcopy(self.inventory)
        target = regressed["items"]["functions"][0]
        target["has_gap"] = True
        target["gap_reasons"] = ["missing_unit_or_integration_test"]
        errors_regressed = surface_inventory.check_against_baseline(regressed, self.baseline)
        self.assertTrue(
            any("regressed with gaps" in err and target["id"] in err for err in errors_regressed),
            errors_regressed,
        )
        self.assertTrue(
            any("new unbaselined surface gap" in err for err in errors_regressed),
            errors_regressed,
        )

        # Mutant 3: add a new unbaselined item with a gap.
        unbaselined = copy.deepcopy(self.inventory)
        unbaselined["items"]["data_computation"].append(
            {
                "category": "data_computation",
                "subcategory": "mutant",
                "id": "mutant:untested_calculation",
                "label": "Synthetic untested calculation",
                "source_file": "src/loop_engine/core/service_runtime/runtime.py",
                "component_guide": "docs/components/service-runtime/README.md",
                "unit_integration_tests": [],
                "browser_tests": [],
                "live_checks": [],
                "has_gap": True,
                "gap_reasons": ["missing_unit_or_integration_test"],
                "metadata": {},
            }
        )
        errors_unbaselined = surface_inventory.check_against_baseline(unbaselined, self.baseline)
        self.assertTrue(
            any(
                "new unbaselined surface gap data_computation:mutant:untested_calculation" in err
                for err in errors_unbaselined
            ),
            errors_unbaselined,
        )

        # Mutant 4: add an extra gap reason to an existing known gap.
        expanded_gap = copy.deepcopy(self.inventory)
        for item in expanded_gap["items"]["background_work"]:
            if item["has_gap"]:
                item["gap_reasons"] = [*item["gap_reasons"], "missing_component_guide"]
                break
        errors_expanded = surface_inventory.check_against_baseline(expanded_gap, self.baseline)
        self.assertTrue(
            any("added new gap reasons" in err for err in errors_expanded),
            errors_expanded,
        )

        # Mutant 5: corrupt baseline schema version.
        bad_baseline = {**self.baseline, "schema": "wrong_schema/v0"}
        self.assertEqual(
            surface_inventory.check_against_baseline(self.inventory, bad_baseline),
            ["baseline schema is not surface_inventory_baseline/v1"],
        )


if __name__ == "__main__":
    unittest.main()
