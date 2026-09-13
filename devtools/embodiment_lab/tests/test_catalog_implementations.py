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

    def test_layering_level_maturity_agrees_with_the_availability_projection(self):
        """A layering level is installed only if the address it implies
        executes today by the runtime's own projection; a level whose
        address no executor runs stays planned, whatever its label says."""
        from loop_engine.core.harness_fallback import HarnessFailureKind, HarnessFallbackPolicy
        from loop_engine.core.harness_layering import (
            ControlOwnership, NativeControl, NativeControlPolicy, WrapperComposition, WrapperLayer)
        from loop_engine.core.harness_layering_availability import EXECUTABLE_NOW, classify_address
        from loop_engine.core.harness_layering_space import (
            CompositionSpace, ControlPolicySpace, LayeringSpace)
        preparation = WrapperLayer("instruction-preparation", "1", ("instruction_preparation",))
        space = LayeringSpace(
            "assignment:catalog-guard", CompositionSpace("codex", (preparation,), 1),
            ControlPolicySpace(("planning_and_continuation",)),
            HarnessFallbackPolicy(("codex", "opencode"), (HarnessFailureKind.UNAVAILABLE,)))
        supervised = NativeControlPolicy({
            **NativeControlPolicy.owning_loop_for_everything().ownership,
            NativeControl.PLANNING: ControlOwnership.SUPERVISED})
        compositions = {
            "direct": 0,
            "instruction_preparation_then_direct": space.compositions.index_of(
                WrapperComposition("prepared", "codex", (preparation,))),
        }
        policies = {
            "owning_loop": space.policies.index_of(NativeControlPolicy.owning_loop_for_everything()),
            "supervised_planning": space.policies.index_of(supervised),
        }
        by_key = {(item.factor, item.level_id): item for item in levels()}
        for composition_level, composition_index in compositions.items():
            for policy_level, policy_index in policies.items():
                address = space.encode(composition_index, policy_index)
                for declared in ((), ("planning_and_continuation",)):
                    state = classify_address(space, address, declared)["state"]
                    installed = (by_key[("wrapper_composition", composition_level)].maturity != "planned"
                                 and by_key[("native_control", policy_level)].maturity != "planned")
                    self.assertEqual(
                        state == EXECUTABLE_NOW, installed,
                        f"{composition_level} + {policy_level} (adapter declares {declared}): "
                        f"projection says {state}, catalog says installed={installed}")


if __name__ == "__main__":
    unittest.main()
