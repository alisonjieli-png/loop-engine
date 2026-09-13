"""Offline address, identity, conditional, and large-space regression checks.

These controls use disclosed configuration data and allocate only requested
points. They verify proposal mechanics, not provider or task-solution quality.
"""
from __future__ import annotations

from dataclasses import replace
from itertools import islice
import json

from .model.campaign import GenerationBudget, GenerationCampaign, expand_variation_space
from .model.dimensions import ConditionalRule, VariationDimension
from .model.fragments import GenerationError
from .space import ConfigurationAxis, ConfigurationSpace


def run_checks():
    tests = []

    def check(name, value):
        tests.append({"name": name, "passed": bool(value)})

    campaign = GenerationCampaign("large", "1.0.0", "config_patch",
        search_strategy="exact_enumeration", dimensions=(
            VariationDimension("x", "integer_range", minimum=0, maximum=999999999),
            VariationDimension("harness", "categorical", values=("native", "external"))))
    space = ConfigurationSpace.from_campaign(campaign)
    check("two_billion_addresses_without_expansion", space.cardinality == 2000000000)
    for index in (0, 1, 1999999998, 1999999999):
        check(f"address_round_trip_{index}", space.index_of(space.configuration_at(index)) == index)
    check("bounded_legacy_expansion_does_not_materialize_integer_range",
          len(expand_variation_space(replace(campaign, budget=GenerationBudget(candidate_limit=3)))) == 3)
    check("lazy_shards_are_disjoint",
          [i for i, _ in islice(space.iter_configurations(start=1, stride=3), 3)] == [1, 4, 7])
    for name, changed in (("repeated_axis", replace(campaign, dimensions=campaign.dimensions * 2)),
                          ("context_override", replace(campaign, context={"x": 2})),
                          ("nonfinite_value", replace(campaign, dimensions=(
                              VariationDimension("v", "float_values", values=(float("nan"),)),)))):
        try:
            ConfigurationSpace.from_campaign(changed)
            check(name + "_refused", False)
        except GenerationError:
            check(name + "_refused", True)
    precise = ConfigurationSpace.from_campaign(replace(campaign, dimensions=(
        VariationDimension("v", "categorical", values=(False, 0, None, "0")),)))
    check("false_zero_null_and_text_have_distinct_addresses",
          [precise.index_of({"v": v}) for v in (False, 0, None, "0")] == [0, 1, 2, 3])
    value = {"tool": "read"}
    detached = ConfigurationSpace.from_campaign(replace(campaign, dimensions=(
        VariationDimension("binding", "tool_binding", values=(value,)),)))
    value["tool"] = "write"
    exported = detached.configuration_at(0)
    exported["binding"]["tool"] = "execute"
    check("configuration_bindings_are_detached", detached.configuration_at(0)["binding"]["tool"] == "read")
    conditional = ConfigurationSpace.from_campaign(replace(campaign,
        conditional_rules=(ConditionalRule("external_needs_x", {"harness": "external"},
                                           require={"x": (3,)}),)))
    check("excluded_addresses_preserve_rule_identity", conditional.exclusions(1) == ("external_needs_x",))
    check("valid_conditional_address_is_retained", conditional.exclusions(7) == ())
    check("condition_changes_space_identity", space.digest != conditional.digest)
    for bad in (-1, 2000000000, True, 1.2):
        try:
            space.configuration_at(bad)
            check(f"invalid_address_{bad}_refused", False)
        except GenerationError:
            check(f"invalid_address_{bad}_refused", True)
    check("finite_space_serialization_is_portable", json.loads(json.dumps(space.to_dict())) == space.to_dict())
    try:
        ConfigurationAxis("duplicate-json", "categorical", ('{"permission":"deny","permission":"allow"}',))
        check("duplicate_json_fields_cannot_change_a_binding", False)
    except GenerationError:
        check("duplicate_json_fields_cannot_change_a_binding", True)
    changed_version = ConfigurationSpace.from_campaign(replace(campaign, version="2.0.0"))
    check("campaign_version_changes_space_identity", changed_version.digest != space.digest)
    for name, rule in (("dead_when", ConditionalRule("dead", {"harness": "EXTERNAL"})),
                       ("impossible_require", ConditionalRule("impossible", {"harness": "external"},
                                                              require={"x": (1000000000,)})),
                       ("context_never_taken", ConditionalRule("fixed", {"fixed": "other"}))):
        try:
            ConfigurationSpace.from_campaign(replace(campaign, context={"fixed": "value"},
                                                     conditional_rules=(rule,)))
            check(f"a_{name}_rule_is_refused_at_construction", False)
        except GenerationError:
            check(f"a_{name}_rule_is_refused_at_construction", True)
    live = ConfigurationSpace.from_campaign(replace(campaign, context={"fixed": "value"},
        conditional_rules=(ConditionalRule("fixed-ok", {"fixed": "value"}, require={"harness": ("native",)}),)))
    check("a_rule_on_a_fixed_context_value_the_space_takes_is_accepted",
          live.exclusions(1) == ("fixed-ok",) and live.exclusions(0) == ())
    return {"tests": tests}
