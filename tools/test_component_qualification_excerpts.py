"""Checks for how a sampled review presents generated packages to its reviewer: data file excerpts and call limits.

On September 30, 2026 the gateway refused every review call for a data table batch before it reached the model:
twelve packages with whole data files did not fit the reviewer's context window, so no sampled table was answered.
The known-wrong controls here: a large data file sent whole, an excerpt the prompt does not label as one, a call
budget above the reviewer's window, and a planned call that does not fit it, which must refuse before any call.
"""
from __future__ import annotations

from contextlib import contextmanager
import csv
import dataclasses
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools.candidate_review import native_profile
from tools.candidate_review import prompt as prompt_module
from tools.candidate_review.native import NativeReviewFile
from tools.candidate_review.prechecks import body_binding_findings
from tools.component_qualification import controls, decisions, excerpts, sampled_review

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = "ollama.kimi-k2.6"
QUALIFIER = {"tool": "tools/component_qualification", "version": "1.0.0", "code_revision": "c" * 40,
             "uncommitted_changes": False}


def _entry(path: str, payload: bytes, media_type: str):
    return SimpleNamespace(path=path, media_type=media_type, size_bytes=len(payload),
                           digest=hashlib.sha256(payload).hexdigest())


def _csv(rows: int, *, multiline_at=None, long_at=None) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["id", "country", "value"])
    for number in range(1, rows + 1):
        country = f"country {number}"
        if number == multiline_at:
            country = "first line\nsecond line"
        if number == long_at:
            country = "x" * 1000
        writer.writerow([number, country, number * 1.5])
    return stream.getvalue().encode()


class ExcerptRuleTests(unittest.TestCase):
    def test_a_small_file_a_file_outside_a_data_folder_and_a_binary_file_are_sent_whole(self):
        small = _csv(10)
        self.assertLessEqual(len(small), excerpts.THRESHOLD_BYTES)
        self.assertIsNone(excerpts.excerpt_for(_entry("data/t.csv", small, "text/csv"), small, ("data",)))
        large = _csv(2000)
        self.assertIsNone(excerpts.excerpt_for(_entry("reference/t.csv", large, "text/csv"), large, ("data",)))
        tsv = large.replace(b",", b"\t")
        self.assertIsNone(excerpts.excerpt_for(_entry("data/t.tsv", tsv, "application/octet-stream"), tsv,
                                               ("data",)))

    def test_a_large_csv_shows_its_header_and_both_ends_as_the_file_holds_them(self):
        payload = _csv(1000, multiline_at=5, long_at=995)
        entry = _entry("data/t.csv", payload, "text/csv")
        excerpt = excerpts.excerpt_for(entry, payload, ("data",))
        lines = payload.decode().split("\n")
        self.assertEqual(excerpt.rule, "data_file_excerpt/v1")
        self.assertTrue(excerpt.text.startswith("id,country,value\n1,country 1,1.5\n"))
        self.assertIn('5,"first line\nsecond line",7.5\n', excerpt.text)  # one record spanning two lines, whole
        self.assertIn("<<< 960 data records not shown: 21 to 980 >>>", excerpt.text)
        self.assertTrue(excerpt.text.endswith(lines[-2]))  # the last record, as the file holds it
        self.assertIn("<<< cut here: ", excerpt.text)
        self.assertNotIn("country 500,", excerpt.text)
        for fact in (f"{len(payload):,} bytes", entry.digest, "1,000 data records", "3 columns: id, country, value",
                     "Shown: the header record and data records 1 to 20 and 981 to 1,000",
                     "960 data records are not shown"):
            self.assertIn(fact, excerpt.statement)

    def test_a_large_json_array_and_object_show_both_ends_and_every_field(self):
        rows = [{"id": number, "name": f"name {number}", "score": None if number % 7 == 0 else number / 3}
                for number in range(1, 701)]
        payload = json.dumps(rows, indent=1).encode()
        excerpt = excerpts.excerpt_for(_entry("data/t.json", payload, "application/json"), payload, ("data",))
        self.assertIn("a JSON array of 700 elements", excerpt.statement)
        self.assertIn("3 fields: id (integer), name (string), score (number, null)", excerpt.statement)
        self.assertIn('{"id":1,"name":"name 1","score":0.3333333333333333}', excerpt.text)
        self.assertIn('"id":700', excerpt.text)
        self.assertNotIn('"id":350,', excerpt.text)
        mapping = json.dumps({f"key {number}": f"value {number}" for number in range(1, 2001)}).encode()
        excerpt = excerpts.excerpt_for(_entry("data/m.json", mapping, "application/json"), mapping, ("data",))
        self.assertIn("a JSON object of 2,000 members; value types: string 2,000", excerpt.statement)
        self.assertTrue(excerpt.text.startswith('"key 1":"value 1"\n'))
        self.assertTrue(excerpt.text.endswith('"key 2000":"value 2000"'))

    def test_other_text_and_an_unreadable_table_show_lines(self):
        notes = "".join(f"line {number}\n" for number in range(1, 3001)).encode()
        excerpt = excerpts.excerpt_for(_entry("data/notes.txt", notes, "text/plain"), notes, ("data",))
        self.assertIn("text of 3,000 lines", excerpt.statement)
        broken = b"id,text\n1,\"" + b"y" * 200_000 + b"\"\n"  # one field above the csv module's field limit
        excerpt = excerpts.excerpt_for(_entry("data/b.csv", broken, "text/csv"), broken, ("data",))
        self.assertIn("text of 2 lines", excerpt.statement)

    def test_the_excerpt_is_deterministic_and_bounded_whatever_the_file(self):
        payload = b"\n".join(b"z" * 5000 for _ in range(50)) + b"\n"
        entry = _entry("data/wide.txt", payload, "text/plain")
        first = excerpts.excerpt_for(entry, payload, ("data",))
        self.assertEqual(first, excerpts.excerpt_for(entry, payload, ("data",)))
        self.assertLessEqual(len(first.text), excerpts.MAXIMUM_EXCERPT_CHARACTERS)
        wide = _csv(3000, long_at=1)
        excerpt = excerpts.excerpt_for(_entry("data/w.csv", wide, "text/csv"), wide, ("data",))
        self.assertLessEqual(len(excerpt.text), excerpts.MAXIMUM_EXCERPT_CHARACTERS)

    def test_the_policy_data_folders_are_the_qualification_ones(self):
        self.assertEqual(excerpts.policy_data_folders(), ("data",))


def _table(tag: str, rows: int):
    """A data table component whose data file holds ``rows`` rows (the qualification code fixture, enlarged)."""
    base = controls.code_fixture("a" * 40)
    table = json.dumps([{"language": f"l{tag}{number}", "greeting": f"hello {number}"}
                        for number in range(rows)]).encode()
    component = base.replaced(payloads=dict(base.payloads) | {"data/greetings.json": table})
    return component.replaced(identity=f"library.supply.data_tables.{tag:0>24}.{component.package.package_digest[:16]}")


class ReviewPromptTests(unittest.TestCase):
    def setUp(self):
        self.criteria, self.instructions = native_profile.resources()

    def test_the_prompt_labels_the_excerpt_and_keeps_every_other_file_exact(self):
        component = _table("1", 4000)
        request = sampled_review.review_request(component, self.criteria, self.instructions.sha256, "anthropic")
        material = prompt_module.member_parts(request)
        self.assertIn("EXCERPT, NOT THE WHOLE FILE: data/greetings.json (data_file_excerpt/v1).", material)
        self.assertIn("4,000 elements", material)
        self.assertNotIn("Exact file data/greetings.json", material)  # known wrong: an excerpt passed off as exact
        self.assertNotIn('"language":"l12000"', material)
        self.assertIn("Exact file greeting_table.py", material)
        self.assertEqual(body_binding_findings(request), [])  # the request still carries every byte
        self.assertLess(len(material), len(component.payloads["data/greetings.json"]) // 4)

    def test_a_package_without_a_large_data_file_is_prompted_exactly_as_before(self):
        component = controls.code_fixture("a" * 40)
        request = sampled_review.review_request(component, self.criteria, self.instructions.sha256, "anthropic")
        whole = dataclasses.replace(request, files=tuple(NativeReviewFile(file.entry, file.payload)
                                                         for file in request.files))
        self.assertTrue(all(file.excerpt is None for file in request.files))
        self.assertEqual(prompt_module.member_parts(request), prompt_module.member_parts(whole))


class CallLimitTests(unittest.TestCase):
    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="limits-"))
        self.addCleanup(shutil.rmtree, folder, True)
        self.configuration, self.criteria, self.instructions, _panel = sampled_review._panel(
            ROOT, folder / "ledger.jsonl", False, None)
        self.installation = self.configuration.installation(REVIEWER)

    def _words(self, installation) -> int:
        """The batch instructions and the batch prompt's own words, which a call's room leaves out."""
        return (prompt_module.estimate_tokens(prompt_module.batch_system(installation, self.instructions))
                + sampled_review.BATCH_WORDS_TOKENS + sampled_review.MEMBER_WORDS_TOKENS * sampled_review.MAXIMUM_BATCH)

    def test_the_members_room_follows_the_reviewer_context_window(self):
        room, window, allowance = sampled_review._call_limits(self.configuration, self.installation,
                                                              self.instructions)
        self.assertEqual((window, allowance), (131_072, 8_192))
        # The room is the call allowance (the window less the answer allowance, over the observed ratio of
        # provider-reported to estimated tokens) less the batch instructions and the prompt's own words.
        self.assertEqual(room, int((window - allowance) / sampled_review.TOKEN_ESTIMATE_RATIO)
                         - self._words(self.installation))
        self.assertLess(room, window - allowance - self._words(self.installation))
        # Known wrong: the fixed budget the September 30 calls were planned under exceeds what the window holds.
        self.assertGreater(sampled_review.CALL_TOKEN_BUDGET - sampled_review.CONTROL_RESERVE_TOKENS, room)

    def test_a_reviewer_without_a_declared_window_keeps_the_fixed_budget(self):
        tactical = self.configuration.installation("tactical.gemma-4-coding-abliterated")
        self.assertEqual(sampled_review._call_limits(self.configuration, tactical, self.instructions),
                         (sampled_review.CALL_TOKEN_BUDGET - self._words(tactical), None, None))


class ScriptedPanel:
    """Where the model would answer: every listed identity approved, every other package rejected."""

    def __init__(self, approve=()) -> None:
        self.approve, self.runs = set(approve), []

    def run(self, request):
        self.runs.append(request)
        items = [SimpleNamespace(identity=member.identity, verdicts=[{
            "reviewer_id": REVIEWER, "decision": "approve" if member.identity in self.approve else "reject",
            "findings": [], "reasons": [], "run_id": request.run_id, "sequence": number,
            "body_sha256": member.body_sha256}]) for number, member in enumerate(request.requests, 1)]
        calls = [{"outcome": "answered"} for _group in request.batch_groups.get(REVIEWER, ((),))]
        return SimpleNamespace(run_id=request.run_id, items=items, calls=calls, stop_reason="completed",
                               totals=lambda: {"calls": len(calls)})


class LargePackageRunTests(unittest.TestCase):
    """Whole review runs over packages large enough that the old plan put calls past the reviewer's window."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="large-package-run-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        base = controls.code_fixture("a" * 40)
        notes = "".join(f"reference note {number}: a sentence about the table.\n" for number in range(1200))
        self.components = []
        for index in range(14):
            variant = base.replaced(payloads=dict(base.payloads) | {
                "reference/notes.txt": (f"table {index}\n" + notes).encode()})
            self.components.append(variant.replaced(
                identity=f"library.supply.data_tables.{index:024x}.{variant.package.package_digest[:16]}"))
        qualification = self.folder / "qualification"
        qualification.mkdir()
        (qualification / "qualification.jsonl").write_text("".join(json.dumps({
            "identity": component.identity, "outcome": "qualified", "batch": component.batch,
            "record_version": component.record_version, "package_digest": component.package.package_digest,
            "qualifier": dict(QUALIFIER), "checks": []}) + "\n" for component in self.components))
        decisions.create(self.folder / "decisions.jsonl", created_at="2026-10-05T00:00:00Z", created_by="a check")
        self.options = SimpleNamespace(
            qualification=qualification, store_root=self.folder / "store", ledger=self.folder / "review-ledger.jsonl",
            decisions=self.folder / "decisions.jsonl", output=self.folder / "review.json", reviewer=REVIEWER,
            producer_family="anthropic", batch=[], controls_per_call=1, call_ceiling=200, token_ceiling=0,
            calibrate=True, authorize_model_calls=True, measurement_only="", seed="seed-0123456789abcdef")

    @contextmanager
    def _offline(self, panel):
        store = {component.identity: component for component in self.components}
        def every_row(lines=()):
            raise AssertionError("a sampled review reads each component by its key, never every supply candidate")

        reader = SimpleNamespace(rows=every_row, row=lambda identity: {"record_id": identity},
                                 component=lambda row: store[row["record_id"]], close=lambda: None)
        real = sampled_review._panel

        def panel_for(root, ledger, authorized, prechecks):
            configuration, criteria, instructions, _unused = real(root, ledger, False, prechecks)
            return configuration, criteria, instructions, panel

        with mock.patch.object(sampled_review, "_panel", panel_for), \
                mock.patch.object(sampled_review, "_listed_model_versions",
                                  side_effect=AssertionError("no provider listing")), \
                mock.patch.object(sampled_review, "StoreReader", return_value=reader), \
                mock.patch.object(sampled_review, "calibrate", return_value={"status": "qualified", "calls": 5}) \
                as single, \
                mock.patch.object(sampled_review, "calibrate_mixed",
                                  return_value={"status": "qualified", "calls": 1, "real_verdicts": {}}):
            yield single

    def test_every_planned_call_fits_the_reviewer_window(self):
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        with self._offline(panel):
            result = sampled_review.command(self.options, ROOT)
        record = json.loads(self.options.output.read_text())
        limits = record["call_limits"]
        tokens = [value for entry in record["batches"].values() for value in entry["call_input_tokens"]]
        self.assertGreater(len(tokens), 1)
        self.assertTrue(all(value + limits["answer_allowance_tokens"] <= limits["context_window_tokens"]
                            for value in tokens), tokens)
        self.assertEqual(record["calls_over_context_window"], [])
        self.assertEqual(len(panel.runs), 1)
        self.assertEqual(result["decisions"][self.components[0].batch]["outcome"], "accepted")

    def test_a_call_past_the_window_refuses_before_any_model_call(self):
        """Known wrong: the fixed 150,000-token budget the September 30 data table calls were planned under."""
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        fixed = lambda configuration, installation, instructions: (  # noqa: E731
            sampled_review.CALL_TOKEN_BUDGET, 131_072, 8_192)
        with self._offline(panel) as single, mock.patch.object(sampled_review, "_call_limits", fixed):
            with self.assertRaisesRegex(ValueError, "that do not fit ollama.kimi-k2.6's context window"):
                sampled_review.command(self.options, ROOT)
        single.assert_not_called()
        self.assertEqual(panel.runs, [])
        self.assertEqual(decisions.DecisionLedger.open(self.options.decisions, for_append=False).entries, [])


if __name__ == "__main__":
    unittest.main()
