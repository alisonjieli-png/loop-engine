"""Checks for tools/carry_catalogue_approvals.py, the command that carries an approval.

The comparison in ``anchor_line_only`` is the whole safety property: it decides
whether an approval given for one body still covers another. So the known-wrong
cases are the point of this file. Each one starts from a real committed body,
makes exactly one change an attacker or an accident could make, and requires the
carry to be refused with a reason that names what differed:

```text
Known-wrong bodies, each of which must refuse the carry
├── a changed sentence as well as a changed anchor line
├── the anchor line removed
├── a second anchor-looking line added
├── a changed word inside the anchor line other than the revision
├── trailing whitespace changed
└── the body unchanged, but the recorded digest does not match it
```

A mutant control runs beside them: with the comparison replaced by one that
always carries, every known-wrong case must fail. That proves the cases are
held by the comparison and not by something else.

No network, model or provider call happens here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import carry_catalogue_approvals as tool  # noqa: E402

ROOT = HERE.parent
CATALOGUE = ROOT / "examples/29_intelligence_service/starter-catalogue"
#: The date a carry in a test records. The command never reads a clock, so a
#: check compares whole records without excluding a field.
CARRIED_AT = "2026-09-21"
#: The revision a known-wrong body is anchored to, and the one it moves to. Both
#: are written as literal short revisions because the fixtures are built here.
OLD, NEW = "0abc123", "9def456"
FULL_OLD = OLD + "0" * (40 - len(OLD))
FULL_NEW = NEW + "0" * (40 - len(NEW))
BODY = ("# Do one thing\n"
        "\n"
        "## When to use it\n"
        "\n"
        "Use it when a step needs one clear method.\n"
        "\n"
        "## Source\n"
        "\n"
        "- `src/loop_engine/core/facets.py`: the declared effects.\n"
        "\n"
        "Licence: MIT. Compiled from revision {revision}.\n")


def _refresh_module():
    """The anchor tool beside the catalogue; its folder is not a package."""
    name = "starter_catalogue_refresh_for_carry"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, CATALOGUE / "refresh.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _anchored(revision: str) -> str:
    return BODY.format(revision=revision)


#: Every known-wrong carried body, with the name of the change it makes. Each one
#: is built from the body the approval covers, so the only difference is the one
#: the name states. The carry must be refused for every one of them.
KNOWN_WRONG = {
    "a changed sentence as well as a changed anchor line":
        _anchored(NEW).replace("Use it when a step needs one clear method.",
                               "Use it when a step needs two clear methods."),
    "the anchor line is removed":
        _anchored(NEW).replace("Licence: MIT. Compiled from revision " + NEW + ".\n", ""),
    "the anchor sentence is removed from the trailing line":
        _anchored(NEW).replace("Licence: MIT. Compiled from revision " + NEW + ".",
                               "Licence: MIT."),
    "a second anchor-looking line is added in place of another line":
        _anchored(NEW).replace("- `src/loop_engine/core/facets.py`: the declared effects.",
                               "Compiled from revision " + NEW + "."),
    "a word inside the anchor line other than the revision is changed":
        _anchored(NEW).replace("Licence: MIT. Compiled", "Licence: Apache-2.0. Compiled"),
    "the anchor sentence itself is reworded":
        _anchored(NEW).replace("Compiled from revision", "Compiled at revision"),
    "the body swaps one anchor sentence for the other, which changes what it claims":
        _anchored(NEW).replace("Compiled from revision " + NEW + ".",
                               "Written for this catalogue at revision " + NEW + "."),
    "trailing whitespace is changed on the anchor line":
        _anchored(NEW).replace("revision " + NEW + ".\n", "revision " + NEW + ". \n"),
    "trailing whitespace is changed on another line":
        _anchored(NEW).replace("Use it when a step needs one clear method.\n",
                               "Use it when a step needs one clear method. \n"),
    "the anchor revision moves to a line that is not the trailing line":
        _anchored(NEW).replace("Licence: MIT. Compiled from revision " + NEW + ".\n", "\n").replace(
            "# Do one thing\n", "# Do one thing. Compiled from revision " + NEW + ".\n"),
}


class AnchorLineComparisonTest(unittest.TestCase):
    """The comparison carries the anchor move and nothing else."""

    def test_the_anchor_move_alone_is_carried(self):
        proof, reason = tool.anchor_line_only(_anchored(OLD), _anchored(NEW))
        self.assertEqual(reason, "")
        self.assertIsNotNone(proof)
        self.assertEqual((proof.reviewed_revision_named, proof.carried_revision_named), (OLD, NEW))
        self.assertEqual(proof.anchor_line_number, proof.lines)
        self.assertEqual(proof.as_record()["identical_lines"], proof.lines - 1)
        self.assertEqual(proof.reviewed_anchor_line, "Licence: MIT. Compiled from revision " + OLD + ".")

    def test_the_second_anchor_sentence_is_carried_as_well(self):
        """Both sentences the anchor tool writes are covered, not only the first."""
        other = BODY.replace("Licence: MIT. Compiled from revision {revision}.",
                             "Licence: MIT. Written for this catalogue at revision {revision}.")
        proof, reason = tool.anchor_line_only(other.format(revision=OLD), other.format(revision=NEW))
        self.assertEqual(reason, "")
        self.assertEqual(proof.sentence, "Written for this catalogue at revision {revision}.")

    def test_an_unchanged_body_is_not_carried(self):
        proof, reason = tool.anchor_line_only(_anchored(OLD), _anchored(OLD))
        self.assertIsNone(proof)
        self.assertIn("same bytes", reason)

    def test_every_known_wrong_body_refuses_the_carry(self):
        approved = _anchored(OLD)
        for name, wrong in KNOWN_WRONG.items():
            with self.subTest(change=name):
                self.assertNotEqual(wrong, _anchored(NEW), "the known-wrong body must differ from the carried one")
                proof, reason = tool.anchor_line_only(approved, wrong)
                self.assertIsNone(proof, f"the carry was allowed after {name}")
                self.assertTrue(reason.strip(), name)

    def test_the_known_wrong_bodies_need_the_comparison(self):
        """The mutant control: with a comparison that always carries, every case fails."""
        approved = _anchored(OLD)
        always = lambda reviewed, carried: (  # noqa: E731
            tool.AnchorLineProof(1, 1, tool.ANCHOR_SENTENCES[0], "", "", OLD, NEW), "")
        with mock.patch.object(tool, "anchor_line_only", always):
            survived = [name for name, wrong in KNOWN_WRONG.items()
                        if tool.anchor_line_only(approved, wrong)[0] is None]
        self.assertEqual(survived, [], "a known-wrong case is held by something other than the comparison")

    def test_the_command_and_the_anchor_tool_name_the_same_sentences(self):
        """One contract for the anchor sentence, so the two tools cannot drift apart."""
        refresh = _refresh_module()
        self.assertEqual(tool.ANCHOR_SENTENCES, refresh.GROUNDING_SENTENCES)
        self.assertEqual(tool.SHORT_REVISION, refresh.SHORT_REVISION)


def _record(rows, *, reviewed=FULL_OLD, carried=FULL_NEW):
    return {"record_type": tool.REVIEW_RECORD_TYPE, "recorded_at": CARRIED_AT,
            "catalogue_folder": "folder", "catalogue_items_file": tool.ITEMS_FILE,
            "catalogue_items_record_type": tool.ITEMS_RECORD_TYPE,
            "catalogue_source_revision": reviewed, "previous_catalogue_source_revisions": [],
            "reviewed_bodies_revision": FULL_OLD, "reviewed_bodies_folder": "bodies",
            "reviewed_bodies_anchor_revision": FULL_OLD,
            "approval_ref_prefix": "reviews.json#",
            "decision_rule": "every reviewer approves", "what_an_approval_permits": "nothing by itself",
            "what_a_rejection_records": "a reason", "what_an_unreviewed_item_records": "no verdict",
            "what_a_carried_approval_records": "the proof",
            "reviewers": [{"reviewer_id": "one", "label": "Reviewer one", "lens": "correctness",
                           "produced_any_item_under_review": False}],
            "totals": {}, "rows": rows}


def _row(identity, payload: bytes, outcome="approved", state="reviewed"):
    return {"identity": identity, "body_path": f"bodies/{identity}.md",
            "body_digest": hashlib.sha256(payload).hexdigest(), "body_size_bytes": len(payload),
            "declared_license": "MIT", "source_layer": "context_intelligence",
            "decisions": [{"reviewer_id": "one", "decision": "approve", "reason": ""}],
            "outcome": outcome, "approval_state": state,
            "rule_applied": "unanimous_approval_by_every_independent_reviewer",
            "approval_ref": "reviews.json#" + identity if outcome == "approved" else ""}


class _Catalogue:
    """A small catalogue folder with one approved item, built from bytes a test chooses."""

    def __init__(self, directory: str, approved: str, current: str, *, digest_of: str | None = None):
        self.folder = Path(directory).resolve() / "starter-catalogue"
        (self.folder / "bodies").mkdir(parents=True)
        (self.folder / "reviewed").mkdir(parents=True)
        (self.folder / "bodies" / "do_one_thing.md").write_text(current, encoding="utf-8")
        (self.folder / "reviewed" / "do_one_thing.md").write_text(approved, encoding="utf-8")
        named = (digest_of if digest_of is not None else approved).encode("utf-8")
        (self.folder / tool.ITEMS_FILE).write_text(json.dumps(
            {"record_type": tool.ITEMS_RECORD_TYPE, "source_revision": FULL_NEW, "items": []}), encoding="utf-8")
        (self.folder / tool.REVIEW_FILE).write_text(json.dumps(
            _record([_row("do_one_thing", named)])), encoding="utf-8")

    def run(self, write=False):
        return tool.carry(tool.CarryRequest(self.folder, tool.ReviewedBodies.in_folder(self.folder / "reviewed"),
                                            CARRIED_AT, write))

    def review(self):
        return json.loads((self.folder / tool.REVIEW_FILE).read_text(encoding="utf-8"))


class CarriedRecordTest(unittest.TestCase):
    """What the command writes for a carried approval and for one that does not carry."""

    def test_a_carried_approval_keeps_its_reviewers_and_records_the_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            before = catalogue.review()["rows"][0]
            result = catalogue.run(write=True)
            self.assertEqual(result["carried"], ["do_one_thing"])
            self.assertEqual(result["did_not_carry"], [])
            row = catalogue.review()["rows"][0]
            self.assertEqual(row["outcome"], tool.APPROVED)
            self.assertEqual(row["approval_state"], tool.CARRIED_STATE)
            self.assertEqual(row["decisions"], before["decisions"])
            self.assertEqual(row["approval_ref"], before["approval_ref"])
            self.assertEqual(row["carry"]["reviewed_body_digest"], before["body_digest"])
            self.assertEqual(row["carry"]["reviewed_revision"], FULL_OLD)
            self.assertEqual(row["carry"]["carried_revision"], FULL_NEW)
            self.assertEqual(row["carry"]["carried_body_digest"], row["body_digest"])
            self.assertEqual(row["body_digest"],
                             hashlib.sha256(_anchored(NEW).encode("utf-8")).hexdigest())
            self.assertNotEqual(row["body_digest"], before["body_digest"])
            self.assertIs(row["carry"]["reviewed_again"], False)
            self.assertEqual(row["carry"]["proof"]["record_type"], tool.PROOF_RECORD_TYPE)
            self.assertEqual(catalogue.review()["catalogue_source_revision"], FULL_NEW)
            self.assertEqual(catalogue.review()["previous_catalogue_source_revisions"], [FULL_OLD])

    def test_a_reader_can_tell_a_carried_approval_from_a_reviewed_one(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            self.assertEqual(catalogue.review()["rows"][0]["approval_state"], tool.REVIEWED_STATE)
            self.assertNotIn("carry", catalogue.review()["rows"][0])
            catalogue.run(write=True)
            self.assertEqual(catalogue.review()["rows"][0]["approval_state"], tool.CARRIED_STATE)
            self.assertIn("carry", catalogue.review()["rows"][0])

    def test_a_second_carry_keeps_the_digest_the_reviewers_judged(self):
        """Carrying again names the first reviewed digest, not the one carried last time."""
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            first = hashlib.sha256(_anchored(OLD).encode("utf-8")).hexdigest()
            catalogue.run(write=True)
            later = "1fed321"
            (catalogue.folder / "bodies" / "do_one_thing.md").write_text(_anchored(later), encoding="utf-8")
            items = json.loads((catalogue.folder / tool.ITEMS_FILE).read_text(encoding="utf-8"))
            items["source_revision"] = later + "0" * (40 - len(later))
            (catalogue.folder / tool.ITEMS_FILE).write_text(json.dumps(items), encoding="utf-8")
            catalogue.run(write=True)
            row = catalogue.review()["rows"][0]
            self.assertEqual(row["carry"]["reviewed_body_digest"], first)
            self.assertEqual(row["carry"]["reviewed_revision"], FULL_OLD)
            self.assertEqual(row["carry"]["proof"]["carried_revision_named"], later)
            self.assertEqual(catalogue.review()["previous_catalogue_source_revisions"], [FULL_OLD, FULL_NEW])

    def test_carrying_twice_over_the_same_move_writes_the_same_record(self):
        """A repeated carry is not a second change, so a check can require a settled record."""
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            catalogue.run(write=True)
            settled = (catalogue.folder / tool.REVIEW_FILE).read_bytes()
            again = catalogue.run(write=True)
            self.assertFalse(again["changed"])
            self.assertEqual((catalogue.folder / tool.REVIEW_FILE).read_bytes(), settled)

    def test_every_known_wrong_body_returns_the_item_to_candidate_state(self):
        for name, wrong in KNOWN_WRONG.items():
            with self.subTest(change=name), tempfile.TemporaryDirectory() as directory:
                catalogue = _Catalogue(directory, _anchored(OLD), wrong)
                before = catalogue.review()["rows"][0]
                result = catalogue.run(write=True)
                self.assertEqual(result["carried"], [], name)
                self.assertEqual([entry["identity"] for entry in result["did_not_carry"]], ["do_one_thing"])
                self.assertTrue(result["did_not_carry"][0]["reason"].strip(), name)
                row = catalogue.review()["rows"][0]
                self.assertEqual(row["outcome"], tool.CARRY_REFUSED, name)
                self.assertEqual(row["approval_state"], tool.NO_STATE)
                self.assertEqual(row["approval_ref"], "")
                self.assertIsNone(row["body_digest"])
                self.assertIsNone(row["body_size_bytes"])
                self.assertNotIn("carry", row)
                self.assertEqual(row["carry_refusal"]["reviewed_body_digest"], before["body_digest"])
                self.assertTrue(row["carry_refusal"]["reason"].strip())
                self.assertEqual(row["decisions"], before["decisions"])
                self.assertEqual(catalogue.review()["totals"]["carry_refused"], 1)
                self.assertEqual(catalogue.review()["totals"]["approved"], 0)

    def test_an_unchanged_body_whose_recorded_digest_does_not_match_it_does_not_carry(self):
        """The sixth known-wrong case: the record names bytes that are not the bytes held."""
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(OLD),
                                   digest_of=_anchored(OLD) + "One more sentence.\n")
            result = catalogue.run(write=True)
            self.assertEqual(result["carried"], [])
            reason = result["did_not_carry"][0]["reason"]
            self.assertIn("what the reviewers read cannot be established", reason)
            row = catalogue.review()["rows"][0]
            self.assertEqual(row["outcome"], tool.CARRY_REFUSED)
            self.assertIsNone(row["body_digest"])

    def test_bytes_that_are_not_there_to_read_do_not_carry(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            (catalogue.folder / "reviewed" / "do_one_thing.md").unlink()
            result = catalogue.run(write=True)
            self.assertEqual(result["carried"], [])
            self.assertIn("are not in", result["did_not_carry"][0]["reason"])
            self.assertEqual(catalogue.review()["rows"][0]["outcome"], tool.CARRY_REFUSED)

    def test_a_body_that_is_the_reviewed_bytes_stays_a_reviewed_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(OLD))
            result = catalogue.run(write=True)
            self.assertEqual((result["carried"], result["did_not_carry"]), ([], []))
            self.assertEqual(result["unchanged"], ["do_one_thing"])
            self.assertEqual(catalogue.review()["rows"][0]["approval_state"], tool.REVIEWED_STATE)

    def test_a_rejected_item_is_never_carried(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            record = catalogue.review()
            record["rows"][0].update(outcome=tool.REJECTED, approval_state=tool.NO_STATE, approval_ref="")
            (catalogue.folder / tool.REVIEW_FILE).write_text(json.dumps(record), encoding="utf-8")
            before = deepcopy(catalogue.review()["rows"][0])
            result = catalogue.run(write=True)
            self.assertEqual((result["carried"], result["did_not_carry"]), ([], []))
            self.assertEqual(catalogue.review()["rows"][0], before)

    def test_without_write_authority_nothing_is_rewritten(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            before = (catalogue.folder / tool.REVIEW_FILE).read_bytes()
            result = catalogue.run()
            self.assertEqual(result["carried"], ["do_one_thing"])
            self.assertFalse(result["written"])
            self.assertEqual((catalogue.folder / tool.REVIEW_FILE).read_bytes(), before)

    def test_an_unsupported_record_version_is_refused_rather_than_reinterpreted(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            for file, key in ((tool.REVIEW_FILE, "record_type"), (tool.ITEMS_FILE, "record_type")):
                with self.subTest(file=file):
                    path = catalogue.folder / file
                    held = json.loads(path.read_text(encoding="utf-8"))
                    path.write_text(json.dumps({**held, key: "another_record/v1"}), encoding="utf-8")
                    with self.assertRaises(tool.ApprovalCarryError) as refusal:
                        catalogue.run(write=True)
                    self.assertIn("only", str(refusal.exception))
                    path.write_text(json.dumps(held), encoding="utf-8")

    def test_a_body_path_that_leaves_the_catalogue_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            for unsafe in ("../outside.md", "/etc/passwd", "bodies/do_one_thing.txt"):
                with self.subTest(path=unsafe):
                    record = catalogue.review()
                    record["rows"][0]["body_path"] = unsafe
                    (catalogue.folder / tool.REVIEW_FILE).write_text(json.dumps(record), encoding="utf-8")
                    with self.assertRaises(tool.ApprovalCarryError) as refusal:
                        catalogue.run(write=True)
                    self.assertEqual(refusal.exception.code, "unsafe_body_path")

    def test_a_planted_link_is_never_read_as_the_reviewed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            held = catalogue.folder / "reviewed" / "do_one_thing.md"
            held.unlink()
            held.symlink_to(catalogue.folder / "bodies" / "do_one_thing.md")
            result = catalogue.run(write=True)
            self.assertEqual(result["carried"], [])
            self.assertEqual(catalogue.review()["rows"][0]["outcome"], tool.CARRY_REFUSED)

    def test_a_carry_needs_an_explicit_date_and_write_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            catalogue = _Catalogue(directory, _anchored(OLD), _anchored(NEW))
            reviewed = tool.ReviewedBodies.in_folder(catalogue.folder / "reviewed")
            for bad in ("", "21 September 2026", "2026-9-21"):
                with self.subTest(date=bad), self.assertRaises(tool.ApprovalCarryError):
                    tool.CarryRequest(catalogue.folder, reviewed, bad)
            with self.assertRaises(tool.ApprovalCarryError):
                tool.CarryRequest(catalogue.folder, reviewed, CARRIED_AT, "yes")


class CommittedCatalogueTest(unittest.TestCase):
    """The committed record is a record this command would write and would not change."""

    def setUp(self):
        self.record = json.loads((CATALOGUE / "reviews.json").read_text(encoding="utf-8"))
        #: The date the committed record says its carry happened, read from the record
        #: itself so this file states no date of its own.
        self.carried_at = next(row["carry"]["carried_at"] for row in self.record["rows"] if "carry" in row)

    def _reviewed(self):
        return tool.ReviewedBodies.at_revision(ROOT, self.record["reviewed_bodies_revision"],
                                               self.record["reviewed_bodies_folder"])

    def test_the_committed_record_is_settled(self):
        """Running the command against the repository reports nothing left to carry."""
        result = tool.carry(tool.CarryRequest(CATALOGUE, self._reviewed(), self.carried_at))
        self.assertFalse(result["changed"], "the committed review record is not what a carry would write")
        self.assertEqual(result["did_not_carry"], [])

    def test_the_record_names_the_revision_the_catalogue_is_anchored_at(self):
        items = json.loads((CATALOGUE / "items.json").read_text(encoding="utf-8"))
        self.assertEqual(self.record["catalogue_source_revision"], items["source_revision"])
        self.assertEqual(sorted(row["identity"] for row in self.record["rows"]),
                         sorted(row["reference"]["identity"] for row in items["items"]))

    def test_every_carried_row_names_the_body_in_the_tree(self):
        carried = [row for row in self.record["rows"] if row["approval_state"] == tool.CARRIED_STATE]
        self.assertTrue(carried)
        for row in carried:
            with self.subTest(item=row["identity"]):
                payload = (CATALOGUE / row["body_path"]).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), row["body_digest"])
                self.assertEqual(len(payload), row["body_size_bytes"])
                self.assertNotEqual(row["carry"]["reviewed_body_digest"], row["body_digest"])

    def test_the_bytes_every_approval_names_are_in_the_repository(self):
        """The approval evidence is readable, so a later carry can be judged the same way."""
        reviewed = self._reviewed()
        approved = [row for row in self.record["rows"] if row["outcome"] == tool.APPROVED]
        self.assertEqual(len(approved), self.record["totals"]["approved"])
        for row in approved:
            with self.subTest(item=row["identity"]):
                named = (row.get("carry") or {}).get("reviewed_body_digest", row["body_digest"])
                payload = reviewed.read(row["identity"])
                self.assertIsNotNone(payload, row["identity"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), named)

    def test_a_changed_body_in_the_tree_would_lose_its_approval(self):
        """The known-wrong tree: one approved body is edited, and the carry refuses it."""
        row = next(row for row in self.record["rows"] if row["outcome"] == tool.APPROVED)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve() / "starter-catalogue"
            shutil.copytree(CATALOGUE, folder, ignore=shutil.ignore_patterns("__pycache__", "host-release"))
            target = folder / row["body_path"]
            target.write_text(target.read_text(encoding="utf-8") + "One more sentence.\n", encoding="utf-8")
            result = tool.carry(tool.CarryRequest(folder, self._reviewed(), self.carried_at))
            self.assertEqual([entry["identity"] for entry in result["did_not_carry"]], [row["identity"]])
            self.assertEqual(result["totals"]["approved"], self.record["totals"]["approved"] - 1)
            self.assertEqual(result["totals"]["carry_refused"], 1)


if __name__ == "__main__":
    unittest.main()
