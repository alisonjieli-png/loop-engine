"""Checks for tools/build_catalogue_release_bundle.py against the real starter catalogue.

The bundle it writes is read back with the service's own bundle reader and
published into a temporary service store with the service's own publish
operation, so a bundle that the service would refuse fails here first. The
known-wrong cases are a rejected item, a body changed after review, an
approval that covers only one file of a multi-file package, a kind with no
declared placement and an output folder inside this public repository.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import build_catalogue_release_bundle as tool  # noqa: E402
from build_host_catalogue_manifest import ManifestBuildError  # noqa: E402
from loop_engine.core.service_runtime.catalogue_bundle import read_bundle, write_bundle  # noqa: E402
from loop_engine.core.service_runtime.catalogue_packages import sha256_hex  # noqa: E402
from loop_engine.core.service_runtime.http_entrypoint import (  # noqa: E402
    DEFAULT_FAMILY_POLICY, DEFAULT_LICENSE_POLICY,
)

CATALOGUE = HERE.parent / "examples/29_intelligence_service/starter-catalogue"


def _review():
    return json.loads((CATALOGUE / "reviews.json").read_text("utf-8"))


def _approved():
    return sorted(row["identity"] for row in _review()["rows"] if row["outcome"] == "approved")


def _copy(directory):
    folder = Path(directory).resolve() / "catalogue"
    shutil.copytree(CATALOGUE, folder, ignore=shutil.ignore_patterns("host-release"))
    return folder


def _rewrite(folder, name, change):
    value = json.loads((folder / name).read_text("utf-8"))
    change(value)
    (folder / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class StarterBundleTest(unittest.TestCase):
    def test_the_starter_catalogue_bundles_every_approved_item_and_the_service_publishes_it(self):
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        schema, lines, payloads = tool.build(CATALOGUE, accepted_licenses=("MIT",))
        self.assertEqual(sorted(line["reference"]["identity"] for line in lines), _approved())
        self.assertTrue(all(line["package"]["body_form"] == "file" for line in lines))
        self.assertTrue(all(line["attributes"]["batch"] == "starter-catalogue" for line in lines))
        with tempfile.TemporaryDirectory(prefix="bundle-tool-") as directory:
            digest = write_bundle(Path(directory).resolve() / "bundle", schema=schema, lines=lines, payloads=payloads)
            bundle = read_bundle(Path(directory).resolve() / "bundle", license_policy=DEFAULT_LICENSE_POLICY,
                                 family_policy=DEFAULT_FAMILY_POLICY)
            self.assertEqual(bundle.digest, digest)
            case = Fixture(Path(directory) / "service")
            from loop_engine.core.service_runtime.catalogue_releases import publish
            result = publish(case.context, bundle)
            self.assertEqual((result["state"], result["items"], result["added"]), ("published", 43, 43))
            view = case.view()
            self.assertEqual(sorted(view.catalogue.items), _approved())
            sample = _approved()[0]
            self.assertEqual(view.body_reader(view.catalogue.items[sample]).encode("utf-8"),
                             (CATALOGUE / "bodies" / f"{sample}.md").read_bytes())
            shown = view.shown_attributes(sample)
            self.assertEqual(set(shown), {"cited_source", "origin_layer", "catalogued_on"})

    def test_two_sources_with_one_file_name_stay_two_files_with_their_own_digests(self):
        first, second = _approved()[:2]
        with tempfile.TemporaryDirectory(prefix="bundle-same-name-") as directory:
            folder = _copy(directory)
            (folder / "bodies" / "moved").mkdir()
            (folder / "bodies" / f"{second}.md").rename(folder / "bodies" / "moved" / f"{first}.md")
            _rewrite(folder, "items.json", lambda value: [row.update(body_path=f"bodies/moved/{first}.md")
                                                          for row in value["items"]
                                                          if row["reference"]["identity"] == second])
            _schema, lines, payloads = tool.build(folder, accepted_licenses=("MIT",), include=(first, second))
            digests = {line["reference"]["identity"]: line["package"]["files"][0]["digest"] for line in lines}
            self.assertNotEqual(digests[first], digests[second])
            self.assertEqual(sorted(digests.values()), sorted(sha256_hex(value) for value in payloads))

    def test_a_multi_file_package_needs_an_approval_of_the_whole_package(self):
        identity = _approved()[0]
        with tempfile.TemporaryDirectory(prefix="bundle-package-") as directory:
            folder = _copy(directory)
            (folder / "bodies" / "scripts").mkdir()
            (folder / "bodies" / "scripts" / "check.py").write_bytes(b"print('checked')\n")
            _rewrite(folder, "items.json", lambda value: [row.update(package_files=[
                {"source": row["body_path"], "path": "SKILL.md", "media_type": "text/markdown",
                 "role": "skill_definition"},
                {"source": "bodies/scripts/check.py", "path": "scripts/check.py", "media_type": "text/x-python",
                 "role": "skill_script"}]) for row in value["items"] if row["reference"]["identity"] == identity])
            with self.assertRaises(ManifestBuildError) as held:
                tool.build(folder, accepted_licenses=("MIT",), include=(identity,))
            self.assertEqual(held.exception.code, "body_changed_after_review")

    def test_known_wrong_inputs_are_refused(self):
        rejected = sorted(row["identity"] for row in _review()["rows"] if row["outcome"] == "rejected")[0]
        with self.assertRaises(ManifestBuildError) as held:
            tool.build(CATALOGUE, accepted_licenses=("MIT",), include=(rejected,))
        self.assertEqual(held.exception.code, "item_not_approved")
        identity = _approved()[0]
        with tempfile.TemporaryDirectory(prefix="bundle-changed-") as directory:
            folder = _copy(directory)
            body = folder / "bodies" / f"{identity}.md"
            body.write_bytes(body.read_bytes() + b"\n")
            with self.assertRaises(ManifestBuildError) as held:
                tool.build(folder, accepted_licenses=("MIT",), include=(identity,))
            self.assertEqual(held.exception.code, "body_changed_after_review")
            _rewrite(folder, "items.json", lambda value: [row["reference"].update(kind="tool")
                                                          for row in value["items"]
                                                          if row["reference"]["identity"] == identity])
            with self.assertRaises(ManifestBuildError) as held:
                tool.build(folder, accepted_licenses=("MIT",), include=(identity,))
            self.assertEqual(held.exception.code, "package_files_required")

    def test_a_bundle_inside_this_repository_is_refused(self):
        code = tool.main(["--catalogue", str(CATALOGUE), "--output", str(HERE.parent / "bundle-here"), "--write"])
        self.assertEqual(code, 2)
        self.assertFalse((HERE.parent / "bundle-here").exists())

    def test_an_items_own_attributes_join_the_line_and_known_wrong_ones_are_refused(self):
        from loop_engine.core.library_ingestion.step_functions import STEP_FUNCTIONS_ATTRIBUTE
        from loop_engine.core.service_runtime.records import ServiceRuntimeError
        identity = _approved()[0]

        def tagged(value):
            for row in value["items"]:
                if row["reference"]["identity"] == identity:
                    row["attributes"] = {"step_functions": ["verification", "reviewing"]}
        with tempfile.TemporaryDirectory(prefix="bundle-attributes-") as directory:
            folder = _copy(directory)
            _rewrite(folder, "items.json", tagged)
            # The item names an attribute its schema does not declare: refused before anything is bundled.
            with self.assertRaises(ServiceRuntimeError) as held:
                tool.build(folder, accepted_licenses=("MIT",), include=(identity,))
            self.assertEqual(held.exception.code, "attribute_not_declared")
            _rewrite(folder, "attribute-schema.json",
                     lambda value: value["attributes"].append(dict(STEP_FUNCTIONS_ATTRIBUTE)))
            _schema, lines, _payloads = tool.build(folder, accepted_licenses=("MIT",), include=(identity,))
            self.assertEqual(lines[0]["attributes"]["step_functions"], ["verification", "reviewing"])
            self.assertEqual(lines[0]["attributes"]["cited_source"], tool.cited_source(lines[0]["reference"]["source_ref"]))

            def restating(value):
                for row in value["items"]:
                    if row["reference"]["identity"] == identity:
                        row["attributes"] = {"catalogued_on": "2020-01-01"}
            _rewrite(folder, "items.json", restating)
            with self.assertRaises(ManifestBuildError) as held:
                tool.build(folder, accepted_licenses=("MIT",), include=(identity,))
            self.assertEqual(held.exception.code, "item_attribute_reserved")


if __name__ == "__main__":
    unittest.main()


class LibraryTierRowTest(unittest.TestCase):
    """The reviewed catalogue names the library tier of every row (AGENTS.md, decision "Library tiers")."""

    def _community(self, folder, identity, *, decisions=1, reviewer=None, tier="community"):
        def change(value):
            names = [row["reviewer_id"] for row in value["reviewers"]]
            for row in value["rows"]:
                if row["identity"] == identity:
                    row["tier"] = tier
                    kept = row["decisions"][:decisions]
                    if reviewer is not None:
                        kept = [{**kept[0], "reviewer_id": reviewer}]
                    row["decisions"] = kept
            self.assertTrue(names)
        _rewrite(folder, "reviews.json", change)

    def test_a_community_row_reviewed_once_becomes_a_community_bundle_line_the_service_publishes(self):
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        from loop_engine.core.service_runtime.catalogue_releases import publish
        chosen = _approved()[0]
        with tempfile.TemporaryDirectory(prefix="bundle-tier-") as directory:
            folder = _copy(directory)
            self._community(folder, chosen)
            schema, lines, payloads = tool.build(folder, accepted_licenses=("MIT",))
            tiers = {line["reference"]["identity"]: line["approval"]["tier"] for line in lines}
            self.assertEqual(tiers[chosen], "community")
            self.assertEqual({tier for identity, tier in tiers.items() if identity != chosen}, {"verified"})
            write_bundle(Path(directory).resolve() / "bundle", schema=schema, lines=lines, payloads=payloads)
            bundle = read_bundle(Path(directory).resolve() / "bundle", license_policy=DEFAULT_LICENSE_POLICY,
                                 family_policy=DEFAULT_FAMILY_POLICY)
            case = Fixture(Path(directory) / "service")
            self.assertEqual(publish(case.context, bundle)["state"], "published")
            decision = case.view().qualification_resolver.resolve(
                __import__("loop_engine.core.provisioning_server", fromlist=["x"]).ProvisioningItemBinding.from_item(
                    case.view().catalogue.items[chosen]))
            self.assertEqual(decision.library_tier, "community")

    def test_known_wrong_a_verified_row_still_needs_every_named_reviewer(self):
        chosen = _approved()[0]
        with tempfile.TemporaryDirectory(prefix="bundle-tier-") as directory:
            folder = _copy(directory)
            self._community(folder, chosen, tier="verified")
            with self.assertRaises(ManifestBuildError) as raised:
                tool.build(folder, accepted_licenses=("MIT",))
            self.assertEqual(raised.exception.code, "review_record_inconsistent")

    def test_known_wrong_a_community_decision_from_an_unnamed_reviewer_is_refused(self):
        chosen = _approved()[0]
        with tempfile.TemporaryDirectory(prefix="bundle-tier-") as directory:
            folder = _copy(directory)
            self._community(folder, chosen, reviewer="reviewer_nobody_named")
            with self.assertRaises(ManifestBuildError) as raised:
                tool.build(folder, accepted_licenses=("MIT",))
            self.assertEqual(raised.exception.code, "review_record_inconsistent")

    def test_known_wrong_an_unknown_tier_is_refused(self):
        chosen = _approved()[0]
        with tempfile.TemporaryDirectory(prefix="bundle-tier-") as directory:
            folder = _copy(directory)
            self._community(folder, chosen, tier="reviewed_by_a_friend", decisions=3)
            with self.assertRaises(ManifestBuildError) as raised:
                tool.build(folder, accepted_licenses=("MIT",))
            self.assertEqual(raised.exception.code, "library_tier_invalid")

    def test_the_packaged_image_manifest_leaves_community_items_out_and_refuses_to_include_one(self):
        import build_host_catalogue_manifest as host
        chosen = _approved()[0]
        with tempfile.TemporaryDirectory(prefix="bundle-tier-") as directory:
            folder = _copy(directory)
            self._community(folder, chosen)
            manifest, _bodies = host.build(folder, artifact_root="/opt/baltor/catalogue", accepted_licenses=("MIT",),
                                           grants=())
            identities = {row["reference"]["identity"] for row in manifest["items"]}
            self.assertNotIn(chosen, identities)
            self.assertEqual(len(identities), len(_approved()) - 1)
            with self.assertRaises(ManifestBuildError) as raised:
                host.build(folder, artifact_root="/opt/baltor/catalogue", accepted_licenses=("MIT",), grants=(),
                           include=(chosen,))
            self.assertEqual(raised.exception.code, "community_item_not_packaged")
