"""The frozen factor catalog may plan implementations it does not have, but a
level recorded as installed or awaiting qualification must name code that
exists, so a maturity label can never claim more than the tree holds."""
from __future__ import annotations

import importlib
import unittest

from embodiment_lab.systematic_catalog import levels


def resolve(spec: str):
    """Resolve 'package.module.attr' under loop_engine or embodiment_lab."""
    parts = spec.split(".")
    for root in ("loop_engine", "embodiment_lab"):
        for cut in range(len(parts), 0, -1):
            name = root + "." + ".".join(parts[:cut])
            try:
                target = importlib.import_module(name)
            except ImportError:
                continue
            try:
                for attribute in parts[cut:]:
                    target = getattr(target, attribute)
            except AttributeError:
                break
            return target
    return None


class CatalogImplementationChecks(unittest.TestCase):
    def test_installed_and_qualification_levels_name_existing_code(self):
        missing = [(item.factor, item.level_id, item.implementation)
                   for item in levels() if item.maturity != "planned"
                   and resolve(item.implementation) is None]
        self.assertEqual(missing, [], "a non-planned level names code the tree lacks")

    def test_planned_levels_that_lack_code_stay_visible_as_planned(self):
        unresolved = [item for item in levels() if resolve(item.implementation) is None]
        self.assertTrue(all(item.maturity == "planned" for item in unresolved))
        self.assertGreater(len(unresolved), 0,
                           "the catalog is expected to plan ahead of the tree; "
                           "if every level resolves, this assertion should be retired")

    def test_the_layering_dimensions_resolve_to_their_records(self):
        by_key = {(item.factor, item.level_id): item for item in levels()}
        for key in (("wrapper_composition", "direct"), ("native_control", "owning_loop")):
            self.assertEqual(by_key[key].maturity, "installed_configuration_not_qualification")
            self.assertIsNotNone(resolve(by_key[key].implementation))
        for key in (("wrapper_composition", "instruction_preparation_then_direct"),
                    ("native_control", "supervised_planning")):
            self.assertEqual(by_key[key].maturity, "planned")


if __name__ == "__main__":
    unittest.main()
