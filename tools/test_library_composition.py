"""The library composition targets and the export's composition mix (September 27, 2026).

The owner asked for a 100,000-component library that is "diverse well balanced ..., not overweighted with
skills.md". The targets are data (src/loop_engine/data/library_composition.json); the export draws each family up
to its quota of the slot, and a family that lacks supply leaves its quota empty instead of being refilled with
skills. The known-wrong control in each selection test is the earlier default, the balanced kind mix of September
26, 2026, whose shares drew 40 percent skills and spilled every exhausted kind's share over to the others: the same
assertion fails on it.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

from licensed_import import composition, review_export  # noqa: E402
from licensed_import.discovery import SOURCE_PRIORITY  # noqa: E402
from loop_engine.core.service_runtime.catalogue_attributes import (  # noqa: E402
    COMPONENT_FORM_KINDS, COMPONENT_FORMS, FORM_DECLARED, component_form_record)

TARGETS = composition.load_targets()
#: Forms the harness kind alone cannot tell apart are declared, the way a supply line declares them.
DERIVED = {"skill", "skill_with_scripts", "mcp_server", "plugin", "marketplace", "hook", "agent", "command",
           "instructions", "rules", "schema", "settings", "library_module"}


def _payload(form, number, *, repository=None, authoring=None):
    kind = COMPONENT_FORM_KINDS[form][0]
    files = [{"path": "README.md", "digest": "a" * 64, "size_bytes": 10, "media_type": "text/markdown",
              "role": "other"}]
    if form == "skill_with_scripts":
        files.append({"path": "scripts/run.py", "digest": "b" * 64, "size_bytes": 10, "media_type": "text/x-python",
                      "role": "skill_script"})
    payload = {"kind": kind, "name": f"{form}-{number}", "record_id": f"{form}.{number}", "native_format": kind,
               "package": {"body_form": "package", "files": files},
               "provenance": {"repository": repository or f"owner/{form}-{number}", "path": f"{form}/{number}",
                              "immutable_revision": "c" * 40},
               "repository": {"stars": 0}, "sources": ["test"], "findings": []}
    if form not in DERIVED:
        payload["component_form"] = component_form_record(form, kind, FORM_DECLARED)
    if authoring:
        payload["authoring"] = authoring
    return payload


def _stock(per_form=300, forms=COMPONENT_FORMS):
    return [_payload(form, number) for form in forms for number in range(per_form)]


def _families(payloads):
    return Counter(TARGETS.family_of(review_export.payload_form(payload)) for payload in payloads)


def _skills_share(payloads, size):
    return _families(payloads)["skills"] / size


def _compose(stock, *, target=200, limit=260, library=None, per_repository=50):
    plan = {}
    chosen, skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=limit, per_repository=per_repository,
                                           kind_mix=review_export.COMPOSITION, targets=TARGETS, library=library,
                                           target=target, plan=plan)
    kept, _refused = review_export.scan_selection(chosen, lambda digest: b"x", None, target=target,
                                                  quotas=plan["quotas"], targets=TARGETS)
    return chosen, kept, plan, skipped


def _balanced(stock, *, target=200):
    """The earlier default: the balanced kind mix, its selection cut at the slot size."""
    chosen, _skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=target + 60, per_repository=50,
                                            kind_mix=review_export.BALANCED)
    kept, _refused = review_export.scan_selection(chosen, lambda digest: b"x", None, target=target)
    return kept


class TargetsRecordTest(unittest.TestCase):
    def test_the_record_holds_the_owner_directed_shares_bounds_and_goal(self):
        self.assertEqual(TARGETS.goal, 100_000)
        self.assertEqual(TARGETS.milestones, (25_000, 50_000, 100_000))
        self.assertEqual(TARGETS.shares, {"executable_code": 0.35, "connectors_and_extensions": 0.2, "skills": 0.2,
                                          "agents_and_commands": 0.1, "instructions_and_rules": 0.08,
                                          "data_and_contracts": 0.07})
        self.assertEqual({family.name: family.bound for family in TARGETS.families if family.bound == "cap"},
                         {"skills": "cap", "instructions_and_rules": "cap"})
        for form in ("function", "library_module", "program", "api_operation", "binary_install"):
            self.assertEqual(TARGETS.family_of(form), "executable_code")
        self.assertEqual(TARGETS.family_of("mcp_server"), "connectors_and_extensions")
        self.assertEqual(TARGETS.family_of("data_table"), "data_and_contracts")
        self.assertEqual(sum(TARGETS.goal_counts().values()), 100_000)
        self.assertEqual(TARGETS.goal_counts()["executable_code"], 35_000)

    def test_known_wrong_records_are_refused_by_name(self):
        record = json.loads(composition.TARGETS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(composition.read_targets(record).digest, TARGETS.digest)

        def mutated(change):
            value = copy.deepcopy(record)
            change(value)
            return value

        def family(value, name):
            return next(row for row in value["families"] if row["family"] == name)

        wrong = {
            "targets_version_unsupported": mutated(lambda v: v.update(record_type="library_composition_targets/v2")),
            "targets_fields_invalid": mutated(lambda v: v.pop("milestones")),
            "shares_do_not_sum_to_one": mutated(lambda v: family(v, "skills").update(share=0.3)),
            "forms_not_covered_once": mutated(lambda v: family(v, "skills")["forms"].update(skill=0.2499,
                                                                                         program=0.0001)),
            "component_form_unknown": mutated(lambda v: family(v, "skills")["forms"].update(binary=0.1)),
            "bound_invalid": mutated(lambda v: family(v, "skills").update(bound="soft")),
            "milestones_invalid": mutated(lambda v: v.update(milestones=[25000, 50000])),
            "family_form_shares_invalid": mutated(lambda v: family(v, "skills")["forms"].update(skill=0.5)),
            "form_vocabulary_unsupported": mutated(lambda v: v.update(component_form_vocabulary="component_form/v2")),
            "share_invalid": mutated(lambda v: family(v, "skills").update(share=-0.2)),
        }
        for code, value in wrong.items():
            with self.assertRaises(composition.CompositionError, msg=code) as caught:
                composition.read_targets(value)
            self.assertEqual(caught.exception.code, code)


class CompositionMixTest(unittest.TestCase):
    def test_with_abundant_supply_each_family_fills_its_quota_and_skills_stay_under_their_cap(self):
        stock = _stock()
        _chosen, kept, plan, _skipped = _compose(stock)
        self.assertEqual(len(kept), 200)
        self.assertEqual(dict(_families(kept)), {name: count for name, count in plan["quotas"].items() if count})
        self.assertEqual(plan["quotas"], {"executable_code": 70, "connectors_and_extensions": 40, "skills": 40,
                                          "agents_and_commands": 20, "instructions_and_rules": 16,
                                          "data_and_contracts": 14})
        self.assertLessEqual(_skills_share(kept, 200), 0.20)
        self.assertLessEqual(_families(kept)["instructions_and_rules"] / 200, 0.08)
        # Known wrong: the balanced mix of September 26 draws 40 percent skills from the same stock.
        self.assertGreater(_skills_share(_balanced(stock), 200), 0.20)

    def test_a_family_without_supply_leaves_its_quota_empty_and_nothing_refills_it(self):
        executable = {"function", "library_module", "program", "api_operation", "binary_install"}
        stock = _stock(forms=[form for form in COMPONENT_FORMS if form not in executable])
        _chosen, kept, plan, _skipped = _compose(stock)
        self.assertEqual(len(kept), 200 - plan["quotas"]["executable_code"])
        self.assertEqual(_families(kept)["executable_code"], 0)
        self.assertEqual(plan["supply"]["executable_code"], 0)
        self.assertLessEqual(_families(kept)["skills"], plan["quotas"]["skills"])
        self.assertLessEqual(_skills_share(kept, 200), 0.20)
        # Known wrong: the balanced mix refills the slot to its size, and skills pass the cap.
        refilled = _balanced(stock)
        self.assertEqual(len(refilled), 200)
        self.assertGreater(_skills_share(refilled, 200), 0.20)

    def test_any_prefix_of_the_selection_keeps_the_mix(self):
        chosen, _kept, _plan, _skipped = _compose(_stock())
        prefix = _families(chosen[:50])
        for family in TARGETS.families:
            self.assertGreaterEqual(prefix[family.name], 1, family.name)
            self.assertLessEqual(prefix[family.name], family.share * 50 + 2, family.name)

    def test_skills_with_scripts_are_preferred_inside_the_skills_quota(self):
        _chosen, kept, plan, _skipped = _compose(_stock())
        skills = Counter(review_export.payload_form(payload) for payload in kept
                         if TARGETS.family_of(review_export.payload_form(payload)) == "skills")
        self.assertEqual(sum(skills.values()), plan["quotas"]["skills"])
        self.assertGreaterEqual(skills["skill_with_scripts"], 0.75 * plan["quotas"]["skills"] - 1)

    def test_supply_aware_shares_follow_the_remaining_need_and_reach_the_goal_mix(self):
        # The served library of September 27, 2026 by family: 42 percent skills, 30 percent instructions and rules.
        library = {"executable_code": 970, "connectors_and_extensions": 818, "skills": 5130,
                   "agents_and_commands": 1563, "instructions_and_rules": 3656, "data_and_contracts": 54}
        shares = composition.slot_shares(TARGETS, library)
        self.assertGreater(shares["executable_code"], 0.35)
        self.assertLess(shares["skills"], 0.20)
        self.assertLess(shares["instructions_and_rules"], 0.08)
        self.assertAlmostEqual(sum(shares.values()), 1.0, places=6)

        def grow(counts, rule):
            counts = dict(counts)
            while sum(counts.values()) + 2000 <= TARGETS.goal:
                for name, quota in composition.largest_remainder(rule(counts), 2000).items():
                    counts[name] += quota
            return {name: count / sum(counts.values()) for name, count in counts.items()}

        final = grow(library, lambda counts: composition.slot_shares(TARGETS, counts))
        for family in TARGETS.families:
            self.assertAlmostEqual(final[family.name], family.share, delta=0.01, msg=family.name)
        # Known wrong: drawing the target shares without the library's counts ends above the skills cap at the goal.
        self.assertGreater(grow(library, lambda counts: TARGETS.shares)["skills"], 0.21)

    def test_knowing_the_library_a_capped_family_never_takes_it_above_its_cap(self):
        # The served library of September 27, 2026 holds 42 percent skills: no slot may add a skill until the
        # library has grown past the point where skills are a fifth of it.
        library = {"executable_code": 970, "connectors_and_extensions": 818, "skills": 5130,
                   "agents_and_commands": 1563, "instructions_and_rules": 3656, "data_and_contracts": 54}
        _chosen, kept, plan, _skipped = _compose(_stock(), library=library)
        self.assertEqual(_families(kept)["skills"], 0)
        self.assertEqual(_families(kept)["instructions_and_rules"], 0)
        self.assertEqual(plan["quotas"]["skills"], 0)
        self.assertGreater(plan["capped_by_library"]["skills"], 0)
        # A library with room under the cap takes skills up to that room and no further.
        roomy = {**library, "skills": 2000, "instructions_and_rules": 0, "agents_and_commands": 9000}
        bounded = composition.bound_caps(TARGETS, {"skills": 1000, "executable_code": 0, "connectors_and_extensions": 0,
                                                   "agents_and_commands": 0, "instructions_and_rules": 0,
                                                   "data_and_contracts": 0}, roomy)
        total = sum(roomy.values()) + bounded["skills"]
        self.assertLessEqual(roomy["skills"] + bounded["skills"], 0.2 * total)
        self.assertGreater(bounded["skills"], 0)

    def test_a_capped_family_already_at_its_goal_draws_nothing(self):
        library = {"skills": 20_000, "executable_code": 100}
        shares = composition.slot_shares(TARGETS, library)
        self.assertEqual(shares["skills"], 0.0)
        _chosen, kept, _plan, _skipped = _compose(_stock(), library=library)
        self.assertEqual(_families(kept)["skills"], 0)

    def test_supply_line_packages_are_held_for_a_review_profile_and_counted(self):
        generated = [_payload("api_operation", number, authoring="generated_from_licensed_facts")
                     for number in range(40)]
        imported = [_payload("skill", number) for number in range(40)]
        chosen, _kept, plan, skipped = _compose(generated + imported)
        self.assertTrue(all(payload["kind"] == "skill" for payload in chosen))
        self.assertEqual(plan["held_for_review_profile"], {"executable_code": 40})
        self.assertEqual(skipped[review_export.AWAITING_REVIEW_PROFILE], 40)
        self.assertEqual(review_export.reviewable(generated[0]), review_export.AWAITING_REVIEW_PROFILE)

    def test_a_package_the_scanners_block_is_replaced_from_its_own_family(self):
        stock = _stock()
        plan = {}
        chosen, _skipped = review_export.select(stock, {}, SOURCE_PRIORITY, limit=260, per_repository=50,
                                                kind_mix=review_export.COMPOSITION, targets=TARGETS, target=200,
                                                plan=plan)
        blocked = {payload["record_id"] for payload in chosen
                   if TARGETS.family_of(review_export.payload_form(payload)) == "connectors_and_extensions"}
        blocked = set(sorted(blocked)[:5])

        class Checks:
            engines = ("blocker",)

            def scan(self, packages):
                return {key: ([{"rule": "test_rule", "severity": "blocking", "line": 0, "engine_id": "t",
                                "path": ""}] if key in blocked else []) for key in packages}

        kept, refused = review_export.scan_selection(chosen, lambda digest: b"x", Checks(), target=200,
                                                     scan_workers=2, quotas=plan["quotas"], targets=TARGETS)
        self.assertEqual(len(refused), 5)
        self.assertEqual(_families(kept)["connectors_and_extensions"], plan["quotas"]["connectors_and_extensions"])
        self.assertEqual(len(kept), 200)

    def test_the_repository_ceiling_holds_across_families(self):
        stock = [_payload("skill", number, repository="one/repository") for number in range(40)] + \
                [_payload("hook", number, repository="one/repository") for number in range(40)]
        chosen, _kept, _plan, skipped = _compose(stock, per_repository=5)
        self.assertEqual(len(chosen), 5)
        self.assertGreater(skipped["repository_ceiling_reached"], 0)

    def test_the_mix_needs_its_targets_and_slot_size(self):
        with self.assertRaises(ValueError):
            review_export.select(_stock(1), {}, SOURCE_PRIORITY, limit=10, per_repository=5,
                                 kind_mix=review_export.COMPOSITION)

    def test_the_export_command_defaults_to_the_composition_mix(self):
        import import_licensed_harness_files as command
        args = command.parser().parse_args(["export-review", "--run-folder", "r", "--store-root", "s",
                                            "--output", "o", "--code-revision", "c" * 40])
        self.assertEqual(args.kind_mix, review_export.COMPOSITION)
        self.assertEqual(review_export.DEFAULT_KIND_MIX, "composition")


class LibraryCountsTest(unittest.TestCase):
    def test_a_bundle_is_counted_by_form_and_family(self):
        rows = [
            {"reference": {"kind": "skill", "styles": []}, "attributes": {"harness_kind": "skill"},
             "package": {"files": [{"role": "skill_definition"}, {"role": "skill_script"}]}},
            {"reference": {"kind": "instruction_file", "styles": []}, "package": {"files": [{"role": "instruction_file"}]}},
            # Counted the way the library page counts it: the served kind, not the file role, names the harness kind.
            {"reference": {"kind": "instruction_file", "styles": ["claude"]},
             "package": {"files": [{"role": "subagent_definition"}]}},
            {"reference": {"kind": "tool", "styles": ["protocol_server_configuration", "protocol_server_configuration"]},
             "package": {"files": [{"role": "protocol_server_configuration"}]}},
            {"reference": {"kind": "tool", "styles": []}, "attributes": {"harness_kind": "code_module",
                                                                         "component_form": "api_operation"},
             "package": {"files": [{"role": "executable_tool"}]}},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "items.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            counts = composition.library_counts(Path(folder), TARGETS)
        self.assertEqual(counts["total"], 5)
        self.assertEqual(counts["forms"], {"skill_with_scripts": 1, "instructions": 2, "mcp_server": 1,
                                           "api_operation": 1})
        self.assertEqual(counts["families"], {"skills": 1, "instructions_and_rules": 2,
                                              "connectors_and_extensions": 1, "executable_code": 1})
        report = composition.composition(counts["forms"], TARGETS)
        self.assertEqual(report["skills"], {"count": 1, "share": 0.2, "target_share": 0.2, "bound": "cap"})


if __name__ == "__main__":
    unittest.main()
