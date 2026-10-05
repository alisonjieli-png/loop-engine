"""The consequence report of a catalogue change, over real local bundles and one real local service.

Kind: continuous integration check. Nothing here reads a live service or a production file.

Each consequence the report claims is checked on bundles written the way the builder writes them, and the claim
that matters most, that a replacement orphans a Public Good grant pinned to the replaced version, is checked on a
real local service as well: the service drops the grant and refuses the policy file again. Known-wrong controls:
a replacement that orphans a grant, a withdrawal of a granted and judged item, and an addition that pushes a judged
query's expected item out of its first ten must each fail the verdict; the same replacement with the grant moved
to the new version must pass.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

import plan_catalogue_change as planner
import reconcile_catalogue_bundle as reconcile
from loop_engine.core.provisioning_server import ProvisioningItemBinding
from loop_engine.core.service_runtime.catalogue_bundle import write_bundle
from loop_engine.core.service_runtime.catalogue_release_checks import SCHEMA, Fixture, bundle_line
from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema
from loop_engine.core.service_runtime.public_good import PublicGoodAccess, PublicGoodGrant, PublicGoodLimits, _matches
from loop_engine.core.service_runtime.public_good_operator import REQUEST_VERSION
from loop_engine.core.service_runtime.records import ServiceRuntimeError

#: The judged queries of these fixtures: each names the items that should come back for it.
QUERIES = (("profile a text column before cleaning", ["keeper"]),
           ("reconcile ledger totals across exports", ["ledger"]),
           ("a request no item answers", []))


def row(identity, purpose, *, text=None, effects=(), tier="verified", domain=("data",), extra=()):
    """One bundle line and its file bytes: a SKILL.md, and any extra (path, text) reference files."""
    files = [("SKILL.md", (text or purpose).encode(), "text/markdown", "skill_definition")]
    files += [(path, body.encode(), "text/markdown", "skill_reference") for path, body in extra]
    line = bundle_line(identity, files, effects=effects, purpose=purpose, attributes={"domain": list(domain)})
    line["approval"]["tier"] = tier
    return line, [data for _path, data, _media, _role in files]


class Catalogue:
    """Bundles, a request, policy files and judged queries in one temporary folder outside the repository."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.count = 0

    def bundle(self, *rows):
        self.count += 1
        folder = self.root / f"bundle-{self.count}"
        write_bundle(folder, schema=CatalogueAttributeSchema.from_dict(SCHEMA), lines=[line for line, _ in rows],
                     payloads=[data for _, payloads in rows for data in payloads])
        return reconcile.load_bundle(folder, ("MIT",))

    def request(self, base, *, additions=(), replacements=(), withdrawals=(), release="a" * 64):
        return reconcile.Changes.from_dict({
            "record_type": reconcile.REQUEST_VERSION, "base_release": release, "base_bundle_digest": base.digest,
            "additions": list(additions),
            "replacements": [{"identity": identity, "expected_version": version(base, identity)}
                             for identity in replacements],
            "withdrawals": [{"identity": identity, "expected_version": version(base, identity), "note": "Synthetic"}
                            for identity in withdrawals]})

    def policy(self, *grants, name="policy.json"):
        path = self.root / name
        path.write_text(json.dumps({"record_type": REQUEST_VERSION, "expected_release": "a" * 64, "expected_version": None,
                                    "grants": [asdict(grant) for grant in grants], "limits": asdict(PublicGoodLimits())}))
        return planner.read_policies([path])

    def judgements(self, rows=QUERIES):
        path = self.root / f"judgements-{self.count}.json"
        path.write_text(json.dumps({"record_type": planner.JUDGEMENTS_VERSION,
                                    "judgements": [{"query": query, "relevant": relevant} for query, relevant in rows]}))
        return path


def version(bundle, identity):
    return next(entry.version for entry in bundle.items if entry.identity == identity)


def grant(bundle, identity, **fields):
    """A Public Good grant pinned to the exact version of one item of a bundle."""
    entry = next(entry for entry in bundle.items if entry.identity == identity)
    return PublicGoodGrant(ProvisioningItemBinding.from_item(entry.item), entry.version, entry.approval_ref,
                           "fixture-rights", (3,), "Synthetic public benefit", 4102444800, **fields)


class ConsequenceReport(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="plan-catalogue-change-")
        self.addCleanup(folder.cleanup)
        self.catalogue = Catalogue(folder.name)
        self.base = self.catalogue.bundle(
            row("keeper", "Profile a text column before cleaning it"),
            row("ledger", "Reconcile ledger totals across exports", tier="community", effects=("reads_fs",),
                extra=(("references/notes.md", "Totals must match."),)),
            row("spare", "Draw a chart of monthly sales", tier="community"))
        self.judged = planner.read_judgements(self.catalogue.judgements())

    def report(self, updates, changes, policies=()):
        sha256, rows = self.judged
        return planner.plan(self.base, tuple(updates), changes, policies=list(policies), judgements=rows,
                            judgements_sha256=sha256)

    def test_an_additions_only_change_lists_what_it_adds_and_passes(self):
        update = self.catalogue.bundle(row("rates", "Fetch exchange rates for a ledger", tier="community",
                                           effects=("network",)))
        report = self.report([update], self.catalogue.request(self.base, additions=("rates",)),
                             self.catalogue.policy(grant(self.base, "ledger")))
        self.assertEqual(report["verdict"], planner.CONSERVATIVE)
        self.assertTrue(report["additions_only"])
        self.assertEqual([(row["identity"], row["version"]) for row in report["items"]["added"]],
                         [("rates", version(update, "rates"))])
        self.assertEqual((report["items"]["base_items"], report["items"]["result_items"], report["items"]["unchanged"]),
                         (3, 4, 3))
        added = report["files"]["placements"]["added"]
        self.assertEqual([(row["identity"], [file["path"] for file in row["files"]]) for row in added], [("rates", ["SKILL.md"])])
        self.assertEqual((report["files"]["new_blobs"], report["files"]["new_blob_bytes"]),
                         (1, len("Fetch exchange rates for a ledger")))
        self.assertEqual(report["files"]["blobs_no_longer_referenced"], [])
        self.assertEqual((report["public_good"]["serving_before_and_after"], report["public_good"]["orphaned"]), (1, []))
        self.assertEqual(report["effects"]["held_until_declared"], ["rates"])
        self.assertEqual(report["effects"]["added"][0]["effects_to_declare"], ["network"])
        self.assertEqual(report["search"]["entries"], {"added": ["rates"], "changed": [], "removed": []})
        self.assertEqual(report["search"]["expected_items_lost"], [])
        self.assertEqual(report["search"]["queries_with_an_expected_item_listed_before"], 2)
        # The result is the release the reconciler would write: its content digest is the one the proof predicts.
        changes = self.catalogue.request(self.base, additions=("rates",))
        output = self.catalogue.root / "written"
        reconcile.write_reconciled(self.base, (update,), changes, output, {
            "record_type": "service_catalogue_view/v1", "release_id": "a" * 64,
            "content_digest": reconcile.bundle_content(self.base), "schema_digest": self.base.schema.digest,
            "items": 3, "withdrawn_left_out": 0})
        proof = json.loads((output / reconcile.PROOF_FILE).read_text())
        self.assertEqual(report["result_content_digest"], proof["result_content_digest"])

    def test_a_replacement_that_orphans_a_public_good_grant_fails_the_verdict(self):
        fix = self.catalogue.bundle(row("ledger", "Reconcile ledger totals across exports", tier="community",
                                        effects=("reads_fs", "writes_fs"), text="Reconcile ledger totals, second version",
                                        extra=(("references/notes.md", "Totals must match."),)))
        changes = self.catalogue.request(self.base, replacements=("ledger",))
        report = self.report([fix], changes, self.catalogue.policy(grant(self.base, "ledger")))
        self.assertEqual(report["verdict"], planner.NOT_CONSERVATIVE)
        self.assertFalse(report["additions_only"])
        (orphan,) = report["public_good"]["orphaned"]
        self.assertEqual((orphan["identity"], orphan["item_version"], orphan["listed_version_after"]),
                         ("ledger", version(self.base, "ledger"), version(fix, "ledger")))
        (replaced,) = report["items"]["replaced"]
        self.assertEqual((replaced["base_version"], replaced["version"]), (version(self.base, "ledger"), version(fix, "ledger")))
        (moved,) = report["files"]["placements"]["replaced"]
        self.assertEqual(([row["path"] for row in moved["changed"]], moved["added"], moved["removed"]), (["SKILL.md"], [], []))
        self.assertEqual([row["digest"] for row in report["files"]["blobs_no_longer_referenced"]],
                         [moved["changed"][0]["before"]["digest"]])
        # The new version also declares writing files, which a step holding only the default effects must add.
        self.assertEqual(report["effects"]["replaced"][0]["after"]["effects_to_declare"], ["writes_fs"])
        self.assertEqual(report["effects"]["held_until_declared"], ["ledger"])
        self.assertEqual(report["search"]["entries"]["changed"], [])
        # Control: the same replacement with the grant moved to the new version orphans nothing and passes.
        moved_grant = grant(fix, "ledger")
        passed = self.report([fix], changes, self.catalogue.policy(moved_grant, name="moved.json"))
        self.assertEqual((passed["verdict"], passed["public_good"]["orphaned"]), (planner.CONSERVATIVE, []))
        self.assertEqual([row["identity"] for row in passed["public_good"]["serving_only_after"]], ["ledger"])

    def test_a_grant_pinned_to_a_replaced_version_is_orphaned_even_when_inactive_or_not_serving(self):
        # The service refuses a policy file holding any grant that does not serve, active or not, so a grant that
        # names the replaced version is orphaned even when it never served (here it names a path the item lacks).
        fix = self.catalogue.bundle(row("ledger", "Reconcile ledger totals across exports", tier="community",
                                        effects=("reads_fs",), text="Second version",
                                        extra=(("references/notes.md", "Totals must match."),)))
        changes = self.catalogue.request(self.base, replacements=("ledger",))
        for name, pinned in (("inactive", grant(self.base, "ledger", active=False)),
                             ("never serving", grant(self.base, "ledger", useful_paths=("references/absent.md",)))):
            with self.subTest(name):
                report = self.report([fix], changes, self.catalogue.policy(pinned, name=name + ".json"))
                self.assertEqual(report["verdict"], planner.NOT_CONSERVATIVE)
                self.assertEqual([row["identity"] for row in report["public_good"]["orphaned"]], ["ledger"])
        # The second rule alone, a grant that served before and does not after, finds the orphan too.
        before = planner.served_view(self.base.items, self.base.schema)
        after = planner.served_view(planner.result_items(self.base, (fix,), changes), self.base.schema)
        rows = planner.grant_consequences(self.catalogue.policy(grant(self.base, "ledger")), before, after, {})
        self.assertEqual([row["identity"] for row in rows["orphaned"]], ["ledger"])

    def test_a_withdrawal_of_a_granted_and_judged_item_fails_the_verdict(self):
        report = self.report([], self.catalogue.request(self.base, withdrawals=("ledger",)),
                             self.catalogue.policy(grant(self.base, "ledger")))
        self.assertEqual(report["verdict"], planner.NOT_CONSERVATIVE)
        self.assertEqual([row["identity"] for row in report["items"]["withdrawn"]], ["ledger"])
        self.assertEqual([row["identity"] for row in report["public_good"]["orphaned"]], ["ledger"])
        self.assertEqual([(row["query"], row["identity"]) for row in report["search"]["expected_items_lost"]],
                         [("reconcile ledger totals across exports", "ledger")])
        self.assertEqual([row["identity"] for row in report["files"]["placements"]["removed"]], ["ledger"])
        self.assertEqual(len(report["files"]["blobs_no_longer_referenced"]), 2)
        self.assertEqual(report["search"]["entries"]["removed"], ["ledger"])

    def test_additions_that_push_an_expected_item_out_of_the_first_ten_fail_the_verdict(self):
        # An additions-only change is not conservative by definition: verified items rank before community ones, so
        # ten verified additions that answer the same request push the community item it expects out of the first ten.
        crowd = [row(f"ledger_tool_{index:02d}", "Reconcile ledger totals across exports", text=f"Ledger tool {index}")
                 for index in range(10)]
        update = self.catalogue.bundle(*crowd)
        changes = self.catalogue.request(self.base, additions=[line["reference"]["identity"] for line, _ in crowd])
        report = self.report([update], changes)
        self.assertTrue(report["additions_only"])
        self.assertEqual(report["verdict"], planner.NOT_CONSERVATIVE)
        (lost,) = report["search"]["expected_items_lost"]
        self.assertEqual((lost["query"], lost["identity"]), ("reconcile ledger totals across exports", "ledger"))
        (changed,) = [row for row in report["search"]["first_results_changed"] if row["query"] == lost["query"]]
        self.assertEqual(changed["expected_ranks"]["ledger"][1], None)
        self.assertEqual(len(changed["after"]), 10)

    def test_a_purpose_change_is_a_changed_search_entry(self):
        fix = self.catalogue.bundle(row("spare", "Draw a chart of weekly sales", tier="community"))
        report = self.report([fix], self.catalogue.request(self.base, replacements=("spare",)))
        self.assertEqual(report["search"]["entries"]["changed"], ["spare"])
        self.assertEqual(report["verdict"], planner.CONSERVATIVE)

    def test_a_change_the_reconciler_refuses_has_no_report(self):
        update = self.catalogue.bundle(row("rates", "Fetch exchange rates for a ledger"))
        with self.assertRaisesRegex(ValueError, "update identities differ"):
            self.report([update], self.catalogue.request(self.base))


class CommandLine(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="plan-catalogue-change-cli-")
        self.addCleanup(folder.cleanup)
        self.catalogue = Catalogue(folder.name)
        self.base = self.catalogue.bundle(row("keeper", "Profile a text column before cleaning it"),
                                          row("ledger", "Reconcile ledger totals across exports", tier="community"))
        self.fix = self.catalogue.bundle(row("ledger", "Reconcile ledger totals across exports", tier="community",
                                             text="Second version"))
        self.changes = self.catalogue.root / "request.json"
        self.changes.write_text(json.dumps(self.catalogue.request(self.base, replacements=("ledger",)).to_dict()))
        self.catalogue.policy(grant(self.base, "ledger"))
        self.judgements = self.catalogue.judgements()

    def run_main(self, *arguments):
        printed = io.StringIO()
        with redirect_stdout(printed):
            status = planner.main(["--base-bundle", str(self.base.folder), "--update-bundle", str(self.fix.folder),
                                   "--changes", str(self.changes), "--judgements", str(self.judgements), *arguments])
        return status, json.loads(printed.getvalue())

    def test_the_report_is_a_new_private_file_and_the_status_follows_the_verdict(self):
        output = self.catalogue.root / "consequences.json"
        status, summary = self.run_main("--public-good-policy", str(self.catalogue.root / "policy.json"),
                                        "--consequences", str(output))
        self.assertEqual((status, summary["verdict"], summary["grants_orphaned"]), (1, planner.NOT_CONSERVATIVE, 1))
        report = json.loads(output.read_text())
        self.assertEqual((report["record_type"], report["request_sha256"]),
                         (planner.PLAN_VERSION, hashlib.sha256(self.changes.read_bytes()).hexdigest()))
        self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)
        status, summary = self.run_main("--public-good-policy", str(self.catalogue.root / "policy.json"),
                                        "--consequences", str(output))
        self.assertEqual((status, summary["refused"]), (2, True))
        status, summary = self.run_main("--no-public-good-policy", "--consequences", str(self.catalogue.root / "none.json"))
        self.assertEqual((status, summary["verdict"]), (0, planner.CONSERVATIVE))
        self.assertTrue(json.loads((self.catalogue.root / "none.json").read_text())["public_good"]["stated_no_policy"])

    def test_a_grant_source_must_be_named_and_the_report_stays_outside_the_repository(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            planner.main(["--base-bundle", str(self.base.folder), "--changes", str(self.changes),
                          "--consequences", str(self.catalogue.root / "unnamed.json")])
        self.assertFalse((self.catalogue.root / "unnamed.json").exists())
        inside = reconcile.REPOSITORY / "consequences-must-not-land-here.json"
        status, summary = self.run_main("--no-public-good-policy", "--consequences", str(inside))
        self.assertEqual((status, summary["refused"]), (2, True))
        self.assertFalse(inside.exists())


class AgainstARealLocalService(unittest.TestCase):
    """The report's view is the view a store serves, and its orphaned grant is one the service really drops."""

    def test_the_planned_view_matches_the_service_and_a_reported_orphan_is_dropped_by_it(self):
        from loop_engine.core.service_runtime.catalogue_releases import publish
        with tempfile.TemporaryDirectory(prefix="plan-catalogue-change-service-") as folder:
            catalogue, case = Catalogue(folder), Fixture(Path(folder) / "service")
            base = catalogue.bundle(row("keeper", "Profile a text column before cleaning it"),
                                    row("ledger", "Reconcile ledger totals across exports", tier="community",
                                        extra=(("references/notes.md", "Totals must match."),)),
                                    row("spare", "Draw a chart of monthly sales", tier="community", domain=("charts",)))
            first = publish(case.context, base)
            served, planned = case.view(), planner.served_view(base.items, base.schema)
            self.assertEqual(planned.item_versions, served.item_versions)
            self.assertEqual(planned.bindings, served.bindings)
            self.assertEqual(planned.content_digest, served.content_digest)
            for query in ("ledger totals", "chart of sales", "profile column", "charts", "data"):
                with self.subTest(query=query):
                    self.assertEqual(planner.first_results(planned, query), planner.first_results(served, query))
            pinned = grant(base, "ledger", useful_paths=("references/notes.md",))
            self.assertTrue(_matches(pinned, planned) and _matches(pinned, served))
            access = PublicGoodAccess(case.runtime)
            access.configure(served, (pinned,))
            self.assertEqual([entry.binding.identity for entry in access.snapshot(served).grants], ["ledger"])

            fix = catalogue.bundle(row("ledger", "Reconcile ledger totals across exports", tier="community",
                                       text="Second version", extra=(("references/notes.md", "Totals must match."),)))
            changes = catalogue.request(base, replacements=("ledger",), release=first["release_id"])
            sha256, rows = planner.read_judgements(catalogue.judgements())
            report = planner.plan(base, (fix,), changes, policies=catalogue.policy(pinned), judgements=rows,
                                  judgements_sha256=sha256)
            self.assertEqual([row["identity"] for row in report["public_good"]["orphaned"]], ["ledger"])
            output = Path(folder) / "reconciled"
            reconcile.write_reconciled(base, (fix,), changes, output, served.summary())
            publish(case.context, reconcile.load_bundle(output, ("MIT",)), expected_release=first["release_id"])
            after = case.view()
            self.assertEqual(after.content_digest, report["result_content_digest"])
            # The service no longer serves the grant, and it refuses the same policy file until it names the new version.
            self.assertEqual(access.snapshot(after).grants, ())
            with self.assertRaises(ServiceRuntimeError) as refused:
                access.configure(after, (pinned,), expected_version=access.snapshot(after).version)
            self.assertEqual(refused.exception.code, "public_good_grant_not_current")


if __name__ == "__main__":
    unittest.main()
