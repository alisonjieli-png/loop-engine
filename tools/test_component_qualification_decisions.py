"""Checks for the decision ledger of generated batch admission: its records, its refusals and the review run.

The known-wrong controls, each refused before any model call could be made:

- a review that may call a model and is given no ledger: the rerun without history that once planned a withheld
  batch's generator as if it had no record;
- a missing, empty, torn, changed or relinked ledger;
- a batch whose exact frame the ledger already decided, or that holds a member of a withheld frame;
- a run whose call ceiling cannot finish its plan.

The review runs here put a scripted panel where the model would answer, with the calibration patched to report
a qualified reviewer; the provider listing is patched to fail the check if it is ever read.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tools.component_qualification import controls, decisions, sampled_review, sampling

ROOT = Path(__file__).resolve().parents[1]
#: The backfill of October 5, 2026 from the review records of September 29 and 30 (see the component's README).
BACKFILL = ROOT / "tools/component_qualification/fixtures/decision-ledger-backfill-2026-10-05.jsonl"
GENERATOR_REVISION = "a" * 40
QUALIFIER = {"tool": "tools/component_qualification", "version": "1.0.0", "code_revision": "c" * 40,
             "uncommitted_changes": False}
REVIEWER = "ollama.kimi-k2.6"
POLICY = sampling.SamplingPolicy()
CREATED = {"created_at": "2026-10-05T00:00:00Z", "created_by": "a check"}


def _records(batch: str, count: int, tag: str) -> list:
    """Qualified records of one batch, as qualification.jsonl holds them."""
    line = batch.split("/", 1)[0]
    return [{"identity": f"library.supply.{line}.{tag}{index:06d}", "outcome": "qualified", "batch": batch,
             "record_version": f"version-{tag}{index}", "qualifier": dict(QUALIFIER),
             "package_digest": hashlib.sha256(f"{batch}:{tag}:{index}".encode()).hexdigest()}
            for index in range(count)]


def _batch_entry(records: list, *, defective: int = 0, decided=None, at: str = "2026-09-30T06:00:09Z",
                 run: str = "run-1") -> dict:
    """One batch of a review record: the plan without history, the bound frame and the rule's decision."""
    batch = records[0]["batch"]
    plan = sampling.plan_for(batch, len(records), sampling.GeneratorHistory(sampling.generator_of(batch)), POLICY)
    decision = sampling.decide(plan, defective=defective, decided=plan.sample_size if decided is None else decided,
                               controls_planted=6, controls_approved=0)
    decision.update({"decided_at": at, "run_id": run, "stop_reason": "completed", "controls_rejected": 6,
                     "controls_without_verdict": 0})
    return {"plan": plan.to_dict(), "frame_sha256": sampling.frame_digest(records), "decision": decision}


def _review(batches: dict, qualification, *, admissible: bool = True, seed: str = "seed-0123456789abcdef",
            started: str = "2026-09-30T05:37:50Z", stopped: "str | None" = None) -> dict:
    """A generated_batch_sampled_review/v2 record of the given batch entries."""
    review = {"record_type": sampling.REVIEW_RECORD, "started_at": started, "qualification": str(qualification),
              "reviewer": REVIEWER, "producer_family": "anthropic", "seed": seed, "admissible": admissible,
              "admissibility_reasons": [] if admissible else ["reviewer_not_calibrated_today"],
              "policy": POLICY.to_dict(), "batches": dict(batches)}
    if stopped:
        review["stopped"] = stopped
    return review


def _append(path: Path, review: dict, frames: dict) -> dict:
    """Record a review run's decisions in the ledger, as the run itself does, in the order they were decided."""
    order = sorted(review["batches"], key=lambda batch: (review["batches"][batch]["decision"]["decided_at"], batch))
    entries = [decisions.entry_for(review, batch, frames[batch], kind=decisions.RUN_SOURCE,
                                   review_path="review.json", review_sha256=None, qualification_sha256="d" * 64,
                                   recorded_at="2026-10-05T00:00:00Z") for batch in order]
    with decisions.DecisionLedger.open(path, for_append=True) as ledger:
        return ledger.append(entries)


def _lines(path: Path) -> list:
    return path.read_bytes().splitlines(keepends=True)


class LedgerFileTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="decision-ledger-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.path = self.folder / "decisions.jsonl"
        decisions.create(self.path, **CREATED)
        self.accepted = _records("program_installs/1.0.0@3e497b809fd8", 80, "a")
        self.withheld = _records("function_extracts/1.1.0@8ebc4a99e5a6", 120, "w")
        review = _review({self.accepted[0]["batch"]: _batch_entry(self.accepted, at="2026-09-29T21:34:50Z"),
                          self.withheld[0]["batch"]: _batch_entry(self.withheld, defective=21)}, "q")
        _append(self.path, review, {self.accepted[0]["batch"]: self.accepted,
                                    self.withheld[0]["batch"]: self.withheld})

    def _refusal(self, path=None) -> str:
        with self.assertRaises(decisions.DecisionLedgerError) as caught:
            decisions.DecisionLedger.open(path or self.path, for_append=False)
        return caught.exception.code

    def _rewrite(self, number: int, change) -> None:
        """Change one line and write it back in the ledger's canonical form."""
        lines = _lines(self.path)
        value = json.loads(lines[number - 1])
        change(value)
        lines[number - 1] = json.dumps(value, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode() + b"\n"
        self.path.write_bytes(b"".join(lines))

    def test_a_ledger_reads_back_what_it_appended(self):
        ledger = decisions.DecisionLedger.open(self.path, for_append=False)
        self.assertEqual([entry["outcome"] for entry in ledger.entries], [sampling.ACCEPTED, sampling.WITHHELD])
        self.assertEqual([entry["generator"] for entry in ledger.entries],
                         ["program_installs/1.0.0", "function_extracts/1.1.0"])
        accepted, withheld = ledger.entries
        self.assertIsNone(accepted["frame"]["members"])
        self.assertEqual(withheld["frame"]["members"], [list(row) for row in sampling.frame_rows(self.withheld)])
        self.assertEqual(withheld["frame"]["qualifier"], QUALIFIER)
        self.assertEqual(ledger.summary()["generators"]["function_extracts/1.1.0"]["defective"], 21)

    def test_create_never_replaces_a_file(self):
        before = self.path.read_bytes()
        with self.assertRaises(decisions.DecisionLedgerError) as caught:
            decisions.create(self.path, **CREATED)
        self.assertEqual(caught.exception.code, "decision_ledger_exists")
        self.assertEqual(self.path.read_bytes(), before)

    def test_a_file_that_is_not_a_ledger_is_refused(self):
        empty = self.folder / "decided-identities.txt"
        empty.write_bytes(b"")
        self.assertEqual(self._refusal(empty), "decision_ledger_not_a_ledger")
        other = self.folder / "history.jsonl"
        other.write_text(json.dumps({"record_type": sampling.DECISION_RECORD}) + "\n")
        self.assertEqual(self._refusal(other), "decision_ledger_not_a_ledger")
        self.assertEqual(self._refusal(self.folder / "absent.jsonl"), "decision_ledger_missing")

    def test_a_changed_or_removed_earlier_line_breaks_the_chain(self):
        original = _lines(self.path)
        self._rewrite(2, lambda value: value["decision"].update({"decided_at": "2026-09-28T00:00:00Z"}))
        self.assertEqual(self._refusal(), "decision_ledger_chain_broken")
        self.path.write_bytes(original[0] + original[2])
        self.assertEqual(self._refusal(), "decision_ledger_chain_broken")
        self.path.write_bytes(original[0] + original[2] + original[1])
        self.assertEqual(self._refusal(), "decision_ledger_chain_broken")

    def test_withheld_members_must_hash_to_their_frame(self):
        def swap(value):
            value["frame"]["members"][0][2] = "e" * 64
        self._rewrite(3, swap)
        self.assertEqual(self._refusal(), "decision_ledger_frame_invalid")

    def test_a_torn_last_line_is_refused(self):
        with open(self.path, "ab") as stream:
            stream.write(b'{"record_type":"generated_batch_decision_entry/v1","sequence":3')
        self.assertEqual(self._refusal(), "decision_ledger_truncated")

    def test_an_unknown_field_or_a_hand_formatted_line_is_refused(self):
        original = _lines(self.path)
        self._rewrite(3, lambda value: value.update({"note": "accepted after all"}))
        self.assertEqual(self._refusal(), "decision_ledger_row_invalid")
        reformatted = json.dumps(json.loads(original[2]), indent=1).replace("\n", " ").encode() + b"\n"
        self.path.write_bytes(original[0] + original[1] + reformatted)
        self.assertEqual(self._refusal(), "decision_ledger_row_unreadable")

    def test_a_link_is_refused(self):
        link = self.folder / "linked.jsonl"
        os.symlink(self.path, link)
        self.assertEqual(self._refusal(link), "decision_ledger_unsafe")

    def test_one_writer_at_a_time(self):
        with decisions.DecisionLedger.open(self.path, for_append=True):
            with self.assertRaises(decisions.DecisionLedgerError) as caught:
                decisions.DecisionLedger.open(self.path, for_append=True)
            self.assertEqual(caught.exception.code, "decision_ledger_busy")
            self.assertEqual(len(decisions.DecisionLedger.open(self.path, for_append=False).entries), 2)

    def test_an_append_refuses_a_ledger_changed_under_its_lock(self):
        with decisions.DecisionLedger.open(self.path, for_append=True) as ledger:
            with open(self.path, "ab") as stream:
                stream.write(b"\n")
            with self.assertRaises(decisions.DecisionLedgerError) as caught:
                ledger.append([])
        self.assertEqual(caught.exception.code, "decision_ledger_changed")

    def test_a_read_only_ledger_is_never_appended(self):
        ledger = decisions.DecisionLedger.open(self.path, for_append=False)
        with self.assertRaises(decisions.DecisionLedgerError) as caught:
            ledger.append([])
        self.assertEqual(caught.exception.code, "decision_ledger_not_locked")


class RefusalTests(unittest.TestCase):
    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="decision-refusals-"))
        self.addCleanup(shutil.rmtree, folder, True)
        self.path = folder / "decisions.jsonl"
        decisions.create(self.path, **CREATED)
        self.accepted = _records("program_installs/1.0.0@3e497b809fd8", 80, "a")
        self.withheld = _records("program_installs/1.0.0@8ebc4a99e5a6", 189, "w")
        review = _review({self.accepted[0]["batch"]: _batch_entry(self.accepted),
                          self.withheld[0]["batch"]: _batch_entry(self.withheld, defective=6)}, "q")
        _append(self.path, review, {self.accepted[0]["batch"]: self.accepted,
                                    self.withheld[0]["batch"]: self.withheld})
        self.ledger = decisions.DecisionLedger.open(self.path, for_append=False)

    def test_a_decided_frame_is_refused_whatever_its_outcome(self):
        refused = self.ledger.refusals({"withheld": self.withheld, "accepted": self.accepted})
        self.assertIn("its exact frame was withheld", refused["withheld"][0])
        self.assertIn("its exact frame was accepted", refused["accepted"][0])

    def test_a_frame_holding_a_withheld_member_is_refused(self):
        """The same components qualified again beside new ones make a new frame; its old members still refuse it."""
        fresh = _records("program_installs/1.0.0@8ebc4a99e5a6", 40, "n")
        superset = self.ledger.refusals({"superset": self.withheld + fresh})["superset"]
        self.assertIn("189 of its components were in the frame of program_installs/1.0.0@8ebc4a99e5a6", superset[0])
        renamed = [dict(fresh[0], package_digest=self.withheld[5]["package_digest"])] + fresh[1:]
        self.assertIn("1 of its components", self.ledger.refusals({"renamed": renamed})["renamed"][0])

    def test_a_frame_of_new_components_is_open(self):
        self.assertEqual(self.ledger.refusals({"new": _records("program_installs/1.0.0@8ebc4a99e5a6", 40, "n")}),
                         {})


class GeneratorHistoryTests(unittest.TestCase):
    """The recorded rate belongs to the generator, so it reaches every later batch of the same line and version."""

    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="decision-history-"))
        self.addCleanup(shutil.rmtree, folder, True)
        path = folder / "decisions.jsonl"
        decisions.create(path, **CREATED)
        functions = _records("function_extracts/1.1.0@8ebc4a99e5a6", 1767, "f")
        tables = _records("data_tables/1.1.0@8ebc4a99e5a6", 381, "t")
        review = _review({functions[0]["batch"]: _batch_entry(functions, defective=21),
                          tables[0]["batch"]: _batch_entry(tables, decided=0)}, "q")
        _append(path, review, {functions[0]["batch"]: functions, tables[0]["batch"]: tables})
        self.rows = decisions.DecisionLedger.open(path, for_append=False).history_rows()

    def _plan(self, batch: str, size: int, rows) -> sampling.SamplingPlan:
        history = sampling.GeneratorHistory.from_decisions(sampling.generator_of(batch), rows)
        return sampling.plan_for(batch, size, history, POLICY)

    def test_the_recorded_rate_plans_every_component_at_a_later_revision(self):
        plan = self._plan("function_extracts/1.1.0@c625853a0000", 1295, self.rows)
        self.assertEqual((plan.mode, plan.sample_size), (sampling.GENERATOR_ABOVE_TOLERANCE, 1295))
        self.assertEqual((plan.history.sampled, plan.history.defective), (58, 21))
        verdict = sampling.decide(plan, defective=0, decided=plan.sample_size, controls_planted=6, controls_approved=0)
        self.assertEqual(verdict["outcome"], sampling.WITHHELD)

    def test_without_the_recorded_rate_the_same_batch_would_be_sampled(self):
        """Known-wrong control: the plan the optional history file allowed when it was left out."""
        plan = self._plan("function_extracts/1.1.0@c625853a0000", 1295, [])
        self.assertEqual(plan.mode, sampling.ZERO_ACCEPTANCE)
        self.assertLess(plan.sample_size, 60)

    def test_a_repaired_generator_version_starts_a_new_history(self):
        plan = self._plan("function_extracts/1.2.0@c625853a0000", 1295, self.rows)
        self.assertEqual(plan.mode, sampling.ZERO_ACCEPTANCE)

    def test_unanswered_components_are_unknown_in_the_history_not_defective(self):
        """Known wrong: a history that took the batch's counted defects. A batch of 381 whose 52 sampled components
        went unanswered, as on September 30, 2026, is withheld, because the rule counts each as defective for that
        batch; a history that kept those 52 would flag the generator and plan its next batch for review of every
        component. The history counts only complete samples, so the next batch keeps the plan with no history."""
        unanswered = _batch_entry(_records("data_tables/1.2.0@8ebc4a99e5a6", 381, "u"), decided=0)
        self.assertEqual((unanswered["decision"]["outcome"], unanswered["decision"]["defective"],
                          unanswered["decision"]["counted_defective"]), (sampling.WITHHELD, 0, 52))
        partial_records = _records("data_tables/1.2.0@aaaaaaaaaaaa", 381, "p")
        partial = _batch_entry(partial_records, decided=30, defective=1)
        self.assertEqual(partial["decision"]["counted_defective"], 23)
        # The decisions as the review records hold them, every field included.
        whole = [dict(value["decision"], generator="data_tables/1.2.0") for value in (unanswered, partial)]
        plan = self._plan("data_tables/1.2.0@c625853a0000", 1295, whole)
        self.assertEqual((plan.mode, plan.history.sampled, plan.history.defective), (sampling.ZERO_ACCEPTANCE, 0, 0))
        # Through the ledger: the partly answered decision settles its frame and still adds nothing to the rate.
        folder = Path(tempfile.mkdtemp(prefix="decision-history-partial-"))
        self.addCleanup(shutil.rmtree, folder, True)
        decisions.create(folder / "decisions.jsonl", **CREATED)
        _append(folder / "decisions.jsonl", _review({partial_records[0]["batch"]: partial}, "q"),
                {partial_records[0]["batch"]: partial_records})
        rows = decisions.DecisionLedger.open(folder / "decisions.jsonl", for_append=False).history_rows()
        self.assertEqual(self._plan("data_tables/1.2.0@c625853a0000", 1295, rows).history.sampled, 0)
        mixed = [dict(row, sample_complete=True, defective=row["counted_defective"]) for row in whole]
        self.assertEqual(self._plan("data_tables/1.2.0@c625853a0000", 1295, mixed).mode,
                         sampling.GENERATOR_ABOVE_TOLERANCE)  # what mixing them would have done

    def test_a_sample_without_verdicts_adds_no_rate(self):
        plan = self._plan("data_tables/1.1.0@c625853a0000", 400, self.rows)
        self.assertEqual((plan.mode, plan.history.batches), (sampling.ZERO_ACCEPTANCE, 0))

    def test_the_generator_is_the_line_and_version(self):
        self.assertEqual(sampling.generator_of("program_installs/1.0.0@3e497b809fd8"), "program_installs/1.0.0")
        with self.assertRaises(sampling.SamplingError):
            sampling.generator_of("")


def _components(count: int, revision: str = GENERATOR_REVISION, tag: str = "a") -> list:
    """Distinct generated components of one batch: one supply line, generator version and code revision."""
    base = controls.code_fixture(revision)
    made = []
    for index in range(count):
        variant = base.replaced(payloads=dict(base.payloads) | {
            "README.md": f"# Greeting table {tag}{index}\n\nA reference table of greetings.\n".encode()})
        made.append(variant.replaced(identity=f"library.supply.data_tables.{tag}{index:023x}."
                                              f"{variant.package.package_digest[:16]}"))
    return made


class ScriptedPanel:
    """The review panel's place in a run. It approves the listed identities and rejects every other package, the
    planted controls among them, and records each run it is asked to make. With ``answers`` false it makes no call,
    as when the provider is unavailable; with ``refused`` it makes its calls and every one is refused unanswered,
    as the gateway refused the September 30, 2026 data table calls for the context window."""

    def __init__(self, approve=(), answers: bool = True, refused: bool = False) -> None:
        self.approve, self.answers, self.refused, self.runs = set(approve), answers, refused, []

    def run(self, request):
        self.runs.append(request)
        if not self.answers:
            return SimpleNamespace(run_id=request.run_id, items=[], calls=[], stop_reason="completed",
                                   totals=lambda: {"calls": 0})
        if self.refused:
            calls = [{"outcome": "context_window_exceeded"} for _group in request.batch_groups.get(REVIEWER, ((),))]
            items = [SimpleNamespace(identity=member.identity, verdicts=[]) for member in request.requests]
            return SimpleNamespace(run_id=request.run_id, items=items, calls=calls, stop_reason="completed",
                                   totals=lambda: {"calls": len(calls)})
        items = []
        for sequence, member in enumerate(request.requests, 1):
            decision = "approve" if member.identity in self.approve else "reject"
            items.append(SimpleNamespace(identity=member.identity, verdicts=[{
                "reviewer_id": REVIEWER, "decision": decision, "findings": [],
                "reasons": [] if decision == "approve" else ["a scripted objection"], "run_id": request.run_id,
                "sequence": sequence, "body_sha256": member.body_sha256}]))
        calls = [{"outcome": "answered"} for _group in request.batch_groups.get(REVIEWER, ((),))]
        return SimpleNamespace(run_id=request.run_id, items=items, calls=calls, stop_reason="completed",
                               totals=lambda: {"calls": len(calls)})


class ReviewRunTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="sampled-review-run-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.components = _components(8)
        self.batch = self.components[0].batch
        self.qualification = self.folder / "qualification"
        self.qualification.mkdir()
        (self.qualification / "qualification.jsonl").write_text("".join(json.dumps({
            "identity": component.identity, "outcome": "qualified", "batch": component.batch,
            "record_version": component.record_version, "package_digest": component.package.package_digest,
            "qualifier": dict(QUALIFIER), "checks": []}) + "\n" for component in self.components))
        self.decisions = self.folder / "decisions.jsonl"
        decisions.create(self.decisions, **CREATED)

    def _options(self, **changes):
        values = {"qualification": self.qualification, "store_root": self.folder / "store",
                  "ledger": self.folder / "review-ledger.jsonl", "decisions": self.decisions,
                  "output": self.folder / "review.json", "reviewer": REVIEWER, "producer_family": "anthropic",
                  "batch": [], "controls_per_call": 1, "call_ceiling": 100, "token_ceiling": 0, "calibrate": True,
                  "authorize_model_calls": True, "measurement_only": "", "seed": "seed-0123456789abcdef"}
        values.update(changes)
        return SimpleNamespace(**values)

    @contextmanager
    def _offline(self, panel):
        """The run with the scripted panel; the provider listing fails the check if it is ever read."""
        store = {component.identity: component for component in self.components}

        def every_row(lines=()):
            raise AssertionError("a sampled review reads each component by its key, never every supply candidate")

        reader = SimpleNamespace(rows=every_row, row=lambda identity: {"record_id": identity},
                                 component=lambda row: store[row["record_id"]], close=lambda: None)
        real, built = sampled_review._panel, []

        def panel_for(root, ledger, authorized, prechecks):
            built.append(authorized)
            configuration, criteria, instructions, _unused = real(root, ledger, False, prechecks)
            return configuration, criteria, instructions, panel

        with mock.patch.object(sampled_review, "_panel", panel_for), \
                mock.patch.object(sampled_review, "_listed_model_versions",
                                  side_effect=AssertionError("no provider listing")), \
                mock.patch.object(sampled_review, "StoreReader", return_value=reader), \
                mock.patch.object(sampled_review, "calibrate", return_value={"status": "qualified", "calls": 5}) \
                as single, \
                mock.patch.object(sampled_review, "calibrate_mixed",
                                  return_value={"status": "qualified", "calls": 1, "real_verdicts": {}}) as mixed:
            yield SimpleNamespace(built=built, single=single, mixed=mixed)

    def _refused(self, options, panel=None) -> str:
        """Run and expect a refusal before any model call: no panel built, no calibration, no review run."""
        panel = panel or ScriptedPanel()
        with self._offline(panel) as run:
            with self.assertRaises(decisions.DecisionLedgerError) as caught:
                sampled_review.command(options, ROOT)
        self.assertEqual((run.built, panel.runs), ([], []))
        run.single.assert_not_called()
        run.mixed.assert_not_called()
        return caught.exception.code

    def _entries(self) -> list:
        return decisions.DecisionLedger.open(self.decisions, for_append=False).entries

    def test_a_run_that_may_call_a_model_refuses_without_the_ledger(self):
        """Known-wrong control: the rerun without history, refused before the qualification is even read."""
        with mock.patch.object(sampled_review, "_load_qualified") as load, \
                mock.patch.object(sampled_review, "_panel") as panel:
            with self.assertRaises(decisions.DecisionLedgerError) as caught:
                sampled_review.command(self._options(decisions=None), ROOT)
        self.assertEqual(caught.exception.code, "decision_ledger_required")
        load.assert_not_called()
        panel.assert_not_called()

    def test_a_missing_or_unreadable_ledger_refuses_before_any_model_call(self):
        empty = self.folder / "decided-identities.txt"
        empty.write_bytes(b"")
        torn = self.folder / "torn.jsonl"
        torn.write_bytes(self.decisions.read_bytes() + b'{"record_type":"generated_batch_decision_entry/v1"')
        for code, path in (("decision_ledger_missing", self.folder / "absent.jsonl"),
                           ("decision_ledger_not_a_ledger", empty), ("decision_ledger_truncated", torn)):
            with self.subTest(code):
                with mock.patch.object(sampled_review, "_load_qualified") as load, \
                        mock.patch.object(sampled_review, "_panel") as panel:
                    with self.assertRaises(decisions.DecisionLedgerError) as caught:
                        sampled_review.command(self._options(decisions=path), ROOT)
                self.assertEqual(caught.exception.code, code)
                load.assert_not_called()
                panel.assert_not_called()

    def test_a_withheld_frame_is_never_sampled_again(self):
        panel = ScriptedPanel(approve=[component.identity for component in self.components[1:]])
        with self._offline(panel):
            result = sampled_review.command(self._options(), ROOT)
        self.assertEqual(result["decisions"][self.batch]["outcome"], sampling.WITHHELD)
        self.assertEqual(result["decision_ledger"]["appended_sequences"], [1])
        (entry,) = self._entries()
        self.assertEqual((entry["batch"], entry["generator"], entry["outcome"]),
                         (self.batch, "data_tables/1.0.0", sampling.WITHHELD))
        self.assertEqual(len(entry["frame"]["members"]), len(self.components))
        self.assertEqual(entry["source"]["seed"], "seed-0123456789abcdef")
        review = json.loads((self.folder / "review.json").read_text())
        self.assertEqual(review["decision_ledger"]["sha256_after"],
                         decisions.DecisionLedger.open(self.decisions, for_append=False).sha256)
        # Known-wrong control: the same frame with a fresh seed, which once could be drawn until a sample passed.
        everything = ScriptedPanel(approve=[component.identity for component in self.components])
        self.assertEqual(self._refused(self._options(seed="a-fresh-seed-0123456789"), everything),
                         "batch_already_decided")
        # Known-wrong control: the same rerun leaving the ledger out.
        self.assertEqual(self._refused(self._options(decisions=None, seed="a-fresh-seed-0123456789"), everything),
                         "decision_ledger_required")
        # A run that calls no model plans nothing for a decided frame either.
        self.assertEqual(self._refused(self._options(authorize_model_calls=False, seed="a-fresh-seed-0123456789")),
                         "batch_already_decided")
        self.assertEqual(len(self._entries()), 1)

    def test_an_accepted_frame_is_recorded_and_settled(self):
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        with self._offline(panel):
            result = sampled_review.command(self._options(), ROOT)
        self.assertEqual(result["decisions"][self.batch]["outcome"], sampling.ACCEPTED)
        (entry,) = self._entries()
        self.assertEqual(entry["outcome"], sampling.ACCEPTED)
        self.assertIsNone(entry["frame"]["members"])
        self.assertEqual(self._refused(self._options(seed="a-fresh-seed-0123456789")), "batch_already_decided")

    def test_a_batch_without_a_valid_verdict_stays_undecided(self):
        """No call made, or every call refused unanswered: the batch is withheld by the written rule, which counts
        an unanswered component as defective, but nothing about its components was learned, so the ledger records
        nothing and the frame may be sampled again."""
        for label, panel in (("no call", ScriptedPanel(answers=False)), ("refused calls", ScriptedPanel(refused=True))):
            with self.subTest(label), self._offline(panel):
                result = sampled_review.command(self._options(), ROOT)
                self.assertEqual(result["decisions"][self.batch]["outcome"], sampling.WITHHELD)
                self.assertEqual(result["decisions"][self.batch]["defective"], 0)
                self.assertEqual(result["decision_ledger"]["appended_sequences"], [])
                self.assertEqual([row["batch"] for row in result["decision_ledger"]["unanswered"]], [self.batch])
                self.assertEqual(self._entries(), [])
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        with self._offline(panel):
            again = sampled_review.command(self._options(seed="a-fresh-seed-0123456789"), ROOT)
        self.assertEqual(again["decisions"][self.batch]["outcome"], sampling.ACCEPTED)
        self.assertEqual(len(self._entries()), 1)

    def test_a_ceiling_that_cannot_finish_the_plan_refuses_before_any_model_call(self):
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        with self._offline(panel) as run:
            with self.assertRaisesRegex(ValueError, "call ceiling"):
                sampled_review.command(self._options(call_ceiling=3), ROOT)
        run.single.assert_not_called()
        self.assertEqual(panel.runs, [])
        self.assertEqual(self._entries(), [])

    def test_a_measurement_records_no_decision(self):
        with self._offline(ScriptedPanel(approve=[component.identity for component in self.components])):
            result = sampled_review.command(self._options(measurement_only="a reviewer trial"), ROOT)
        self.assertEqual(result["decisions"][self.batch]["outcome"], sampling.WITHHELD)
        self.assertEqual(self._entries(), [])

    def _with_readme(self, index: int, size: int):
        """The batch with one component's README grown to ``size`` bytes, its qualification record rewritten."""
        base = self.components[index]
        grown = base.replaced(payloads=dict(base.payloads) | {"README.md": b"# Greeting table\n\n"
                                                                          + b"A greeting row.\n" * (size // 16)})
        grown = grown.replaced(identity=f"library.supply.data_tables.{'f' * 23}{index}.{grown.package.package_digest[:16]}")
        self.components[index] = grown
        (self.qualification / "qualification.jsonl").write_text("".join(json.dumps({
            "identity": component.identity, "outcome": "qualified", "batch": component.batch,
            "record_version": component.record_version, "package_digest": component.package.package_digest,
            "qualifier": dict(QUALIFIER), "checks": []}) + "\n" for component in self.components))
        return grown

    def test_the_call_allowance_is_the_reviewer_window_less_its_output(self):
        configuration = sampled_review._panel(ROOT, self.folder / "unused-ledger.jsonl", False, None)[0]
        kimi, glm = configuration.installation(REVIEWER), configuration.installation("ollama.glm-5.3")
        self.assertEqual(sampled_review.call_allowance(configuration, kimi), int((131_072 - 8_192) / 1.35))
        self.assertEqual(sampled_review.call_allowance(configuration, glm), int((131_072 - 32_768) / 1.35))
        self.assertLess(sampled_review.call_allowance(configuration, kimi), sampled_review.CALL_TOKEN_BUDGET)

    def test_a_large_member_gets_its_own_call_and_a_control_that_fits(self):
        from tools.candidate_review.prompt import build_batch_prompt
        large = self._with_readme(3, 240_000)
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        with self._offline(panel):
            sampled_review.command(self._options(), ROOT)
        record = json.loads((self.folder / "review.json").read_text())
        configuration, _criteria, instructions, _panel = sampled_review._panel(ROOT, self.folder / "unused.jsonl",
                                                                               False, None)
        installation = configuration.installation(REVIEWER)
        self.assertEqual(record["calls_that_do_not_fit"], [])
        planted = {row["identity"] for row in record["batches"][self.batch]["controls"]}
        requests = {request.identity: request for run in panel.runs for request in run.requests}
        groups = [group for run in panel.runs for group in run.batch_groups.get(REVIEWER, ())]
        self.assertGreater(len(groups), 1)
        for group in groups:
            prompt = build_batch_prompt([requests[identity] for identity in group], installation, instructions)
            self.assertLessEqual(prompt.estimated_input_tokens, record["call_allowance"])
            self.assertEqual(sum(1 for identity in group if identity in planted), 1)
        alone = next(group for group in groups if large.identity in group)
        self.assertEqual(sorted(identity for identity in alone if identity not in planted), [large.identity])

    def test_a_member_too_large_for_one_call_refuses_before_any_model_call(self):
        """Known-wrong control: the fixed 150,000-token plan sent calls over the reviewer's 131,072-token window,
        which the gateway refused unsent, leaving the sample incomplete and the batch withheld."""
        self._with_readme(5, 520_000)
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        with self._offline(panel) as run:
            with self.assertRaisesRegex(ValueError, "do not fit"):
                sampled_review.command(self._options(), ROOT)
        run.single.assert_not_called()
        run.mixed.assert_not_called()
        self.assertEqual((panel.runs, self._entries()), ([], []))
        with self._offline(ScriptedPanel()):
            sampled_review.command(self._options(authorize_model_calls=False), ROOT)
        unfit = json.loads((self.folder / "review.json").read_text())["calls_that_do_not_fit"]
        self.assertEqual([row["planted_controls"] for row in unfit], [0])

    def test_the_plan_reads_the_generator_rate_from_the_ledger(self):
        earlier = _records("data_tables/1.0.0@" + "e" * 12, 1767, "e")
        _append(self.decisions, _review({earlier[0]["batch"]: _batch_entry(earlier, defective=21)}, "q"),
                {earlier[0]["batch"]: earlier})
        with self._offline(ScriptedPanel()):
            sampled_review.command(self._options(authorize_model_calls=False), ROOT)
        plan = json.loads((self.folder / "review.json").read_text())["batches"][self.batch]["plan"]
        self.assertEqual((plan["mode"], plan["sample_size"]), (sampling.GENERATOR_ABOVE_TOLERANCE, 8))
        self.assertEqual((plan["history"]["sampled"], plan["history"]["defective"]), (58, 21))
        with self._offline(ScriptedPanel()):
            sampled_review.command(self._options(authorize_model_calls=False, decisions=None), ROOT)
        plan = json.loads((self.folder / "review.json").read_text())["batches"][self.batch]["plan"]
        self.assertNotEqual(plan["mode"], sampling.GENERATOR_ABOVE_TOLERANCE)
        self.assertEqual(plan["history"]["sampled"], 0)


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="decision-backfill-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.qualification = self.folder / "qualification"
        self.qualification.mkdir()
        self.accepted = _records("program_installs/1.0.0@3e497b809fd8", 80, "a")
        self.withheld = _records("function_extracts/1.1.0@8ebc4a99e5a6", 120, "w")
        self.stopped = _records("mcp_registry/1.0.0@dd0ec734d39a", 70, "m")
        refused = [dict(_records("mcp_registry/1.0.0@dd0ec734d39a", 1, "r")[0], outcome="refused")]
        (self.qualification / "qualification.jsonl").write_text("".join(
            json.dumps(row) + "\n" for row in self.accepted + self.withheld + self.stopped + refused))
        self.path = self.folder / "decision-ledger.jsonl"

    def _write(self, name: str, review: dict) -> Path:
        path = self.folder / name
        path.write_text(json.dumps(review, indent=1))
        return path

    def _reviews(self) -> list:
        decided = self._write("review-v2.json", _review({
            self.accepted[0]["batch"]: _batch_entry(self.accepted, at="2026-09-29T21:34:50Z"),
            self.withheld[0]["batch"]: _batch_entry(self.withheld, defective=21)}, self.qualification))
        frame = _batch_entry(self.stopped)
        del frame["decision"]
        stopped = self._write("review-stopped.json", _review({self.stopped[0]["batch"]: frame}, self.qualification,
                                                              admissible=False, stopped="reviewer_not_calibrated"))
        measured = self._write("review-measured.json", _review({
            self.stopped[0]["batch"]: _batch_entry(self.stopped, defective=1)}, self.qualification, admissible=False,
            seed="measurement-seed-0123456789"))
        return [decided, stopped, measured]

    def test_backfill_records_each_complete_decision_once(self):
        reviews = self._reviews()
        result = decisions.backfill(self.path, reviews, recorded_at="2026-10-05T12:00:00Z")
        self.assertTrue(result["created"])
        self.assertEqual([(row["batch"], row["outcome"]) for row in result["appended"]],
                         [(self.accepted[0]["batch"], sampling.ACCEPTED),
                          (self.withheld[0]["batch"], sampling.WITHHELD)])
        self.assertEqual([row["review"] for row in result["skipped"]], [str(reviews[1]), str(reviews[2])])
        ledger = decisions.DecisionLedger.open(self.path, for_append=False)
        source = ledger.entries[1]["source"]
        self.assertEqual((source["kind"], source["review_sha256"]),
                         (decisions.BACKFILL_SOURCE, hashlib.sha256(reviews[0].read_bytes()).hexdigest()))
        self.assertEqual(source["qualification_sha256"],
                         hashlib.sha256((self.qualification / "qualification.jsonl").read_bytes()).hexdigest())
        before = self.path.read_bytes()
        again = decisions.backfill(self.path, reviews + reviews[:1], recorded_at="2026-10-06T12:00:00Z")
        self.assertEqual((again["created"], again["appended"], again["already_recorded"]), (False, [], 2))
        self.assertEqual(self.path.read_bytes(), before)

    def test_backfill_checks_every_frame_before_it_writes(self):
        review = _review({self.withheld[0]["batch"]: _batch_entry(self.withheld, defective=21)}, self.qualification)
        review["batches"][self.withheld[0]["batch"]]["frame_sha256"] = "0" * 64
        with self.assertRaises(decisions.DecisionLedgerError) as caught:
            decisions.backfill(self.path, [self._write("changed.json", review)], recorded_at="2026-10-05T12:00:00Z")
        self.assertEqual(caught.exception.code, "frame_mismatch")
        self.assertFalse(self.path.exists())

    def test_backfill_refuses_a_review_without_an_exact_population(self):
        review = _review({self.withheld[0]["batch"]: _batch_entry(self.withheld)}, self.qualification)
        review["record_type"] = "generated_batch_sampled_review/v1"
        with self.assertRaises(decisions.DecisionLedgerError) as caught:
            decisions.backfill(self.path, [self._write("v1.json", review)], recorded_at="2026-10-05T12:00:00Z")
        self.assertEqual(caught.exception.code, "review_version_unsupported")
        self.assertFalse(self.path.exists())

    def test_backfill_leaves_a_decision_without_a_valid_verdict_undecided(self):
        unanswered = _batch_entry(self.withheld, decided=0)
        unanswered["sample"] = [row["identity"] for row in self.withheld[:unanswered["plan"]["sample_size"]]]
        partial = _batch_entry(self.accepted, decided=3, defective=1)
        review = _review({self.withheld[0]["batch"]: unanswered, self.accepted[0]["batch"]: partial},
                         self.qualification)
        result = decisions.backfill(self.path, [self._write("unanswered.json", review)],
                                    recorded_at="2026-10-05T12:00:00Z")
        self.assertEqual([row["batch"] for row in result["appended"]], [self.accepted[0]["batch"]])
        self.assertEqual([(row["batch"], row["reason"]) for row in result["skipped"]],
                         [(self.withheld[0]["batch"], decisions.UNANSWERED_REASON)])
        # A verdict given in the mixed calibration batch is a valid verdict on the batch's component.
        calibrated = _review({self.withheld[0]["batch"]: unanswered}, self.qualification,
                             seed="calibrated-seed-0123456789")
        calibrated["calibration"] = {"mixed_batch_of_12": {"real_verdicts": {unanswered["sample"][0]: ["approve"]}}}
        again = decisions.backfill(self.path, [self._write("calibrated.json", calibrated)],
                                   recorded_at="2026-10-05T12:00:00Z")
        self.assertEqual([row["batch"] for row in again["appended"]], [self.withheld[0]["batch"]])

    def test_backfill_never_writes_into_a_file_that_is_not_a_ledger(self):
        decided = self.folder / "decided-identities.txt"
        decided.write_bytes(b"")
        with self.assertRaises(decisions.DecisionLedgerError) as caught:
            decisions.backfill(decided, self._reviews()[:1], recorded_at="2026-10-05T12:00:00Z")
        self.assertEqual(caught.exception.code, "decision_ledger_not_a_ledger")
        self.assertEqual(decided.read_bytes(), b"")


class RecordedBackfillTests(unittest.TestCase):
    """The ledger backfilled on October 5, 2026 from the review records that decided generated batches."""

    def setUp(self):
        self.ledger = decisions.DecisionLedger.open(BACKFILL, for_append=False)

    def test_it_holds_the_three_answered_decisions_of_september_29_and_30(self):
        """The September 30 data_tables/1.1.0@8ebc4a99e5a6 decision is not here: the gateway refused all three of its
        calls before they reached the model, so none of its 52 sampled tables had a verdict."""
        self.assertEqual([(entry["batch"], entry["outcome"], entry["frame"]["size"]) for entry in self.ledger.entries],
                         [("program_installs/1.0.0@3e497b809fd8", sampling.ACCEPTED, 3910),
                          ("function_extracts/1.1.0@8ebc4a99e5a6", sampling.WITHHELD, 1767),
                          ("program_installs/1.0.0@8ebc4a99e5a6", sampling.WITHHELD, 189)])
        self.assertEqual({entry["source"]["review_sha256"] for entry in self.ledger.entries},
                         {"26c14c3cc869a043625c95f8666572af1acb6f0f41a030cd5532b62c7b8724a2",
                          "cb9af93b2a73a67ec0f88419f00a15d39590cfeb1cd38071cd64650adfb1c22f"})
        self.assertEqual({entry["source"]["kind"] for entry in self.ledger.entries}, {decisions.BACKFILL_SOURCE})

    def test_each_withheld_frame_is_refused_when_qualified_again(self):
        for entry in self.ledger.entries[1:]:
            records = [{"identity": identity, "record_version": version, "package_digest": digest}
                       for identity, version, digest in entry["frame"]["members"]]
            refused = self.ledger.refusals({entry["batch"]: records})
            self.assertIn("its exact frame was withheld", refused[entry["batch"]][0], entry["batch"])

    def test_the_recorded_rates_hold_back_both_generators_above_the_tolerance(self):
        generators = self.ledger.summary()["generators"]
        self.assertEqual({name: (row["sampled"], row["defective"], row["at_or_above_tolerance"])
                          for name, row in generators.items()},
                         {"function_extracts/1.1.0": (58, 21, True), "program_installs/1.0.0": (106, 6, True)})
        history = sampling.GeneratorHistory.from_decisions("function_extracts/1.1.0", self.ledger.history_rows())
        plan = sampling.plan_for("function_extracts/1.1.0@c625853a0000", 1295, history, POLICY)
        self.assertEqual((plan.mode, plan.sample_size), (sampling.GENERATOR_ABOVE_TOLERANCE, 1295))


if __name__ == "__main__":
    unittest.main()


class QualifiedAdmissionTests(unittest.TestCase):
    """admit-qualified: deterministic qualification admits, independent review ongoing (October 5, 2026)."""

    def setUp(self):
        from tools.component_qualification import qualified_admission
        self.route = qualified_admission
        self.folder = Path(tempfile.mkdtemp(prefix="qualified-admission-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.components = _components(4, tag="q")
        self.generator = sampling.generator_of(self.components[0].batch)
        self.qualification = self.folder / "qualification"
        self.qualification.mkdir()
        (self.qualification / "qualification.jsonl").write_text("".join(json.dumps({
            "identity": component.identity, "outcome": "qualified", "batch": component.batch, "line": component.line,
            "record_version": component.record_version, "package_digest": component.package.package_digest,
            "qualifier": dict(QUALIFIER), "vetting": {"implementation_tested": "fixture"},
            "self_test_sha256": "0" * 64, "checks": []}) + "\n" for component in self.components))
        self.decisions = self.folder / "decisions.jsonl"
        decisions.create(self.decisions, **CREATED)
        self.held = self.folder / "held.json"
        self._hold()

    def _hold(self, *generators):
        self.held.write_text(json.dumps({"record_type": self.route.HELD_RECORD, "held": [
            {"generator": generator, "reason": "a check", "held_at": "2026-10-05", "held_by": "a check"}
            for generator in generators]}))

    def _admit(self, name="admitted"):
        store = {component.identity: component for component in self.components}
        return self.route.admit_qualified(self.qualification, None, self.decisions, self.held, self.folder / name,
                                          "2026-10-05", ROOT, components=store)

    def _decided(self, defective: int, rejected=()):
        """A complete decision about another batch of the same generator, recorded in the ledger."""
        batch = self.generator + "@" + "e" * 12
        records = _records(batch, 1767, "e")
        entry = _batch_entry(records, defective=defective)
        if rejected:
            entry["decision"]["rejected_members"] = [[component.identity, component.record_version,
                                                      component.package.package_digest] for component in rejected]
        _append(self.decisions, _review({batch: entry}, "q"), {batch: records})

    def test_every_qualified_component_of_an_unheld_version_is_admitted_as_qualified(self):
        from build_host_catalogue_manifest import _review_index
        result = self._admit()
        self.assertEqual(result["admitted"], 4)
        output = self.folder / "admitted"
        review = json.loads((output / "reviews.json").read_text())
        self.assertEqual({(row["approval_state"], row["tier"], row["independent_review"]) for row in review["rows"]},
                         {("qualified", "community", "ongoing")})
        self.assertEqual((review["totals"]["approved_as_reviewed"], review["totals"]["approved_by_qualification"]),
                         (0, 4))
        self.assertEqual([reviewer["family"] for reviewer in review["reviewers"]], ["deterministic_process"])
        # The release tools' shared reader accepts every row as an approved community row.
        _record, index = _review_index(output)
        self.assertEqual({row["outcome"] for row in index.values()}, {"approved"})
        self.assertEqual(len((output / "decided.txt").read_text().splitlines()), 4)
        # Every attribute an item carries is declared, so the bundle builder can serve the folder as written.
        declared = {item["name"] for item in json.loads((output / "attribute-schema.json").read_text())["attributes"]}
        items = json.loads((output / "items.json").read_text())["items"]
        self.assertLessEqual({name for item in items for name in item["attributes"]}, declared)
        self.assertFalse(list(self.folder.glob("admitted.partial-*")))

    def test_a_version_the_held_file_names_is_left_out(self):
        for held in (self.generator, self.generator.split("/")[0] + "/*"):
            with self.subTest(held=held):
                self._hold(held)
                with self.assertRaises(self.route.QualifiedAdmissionError) as caught:
                    self._admit("held-" + held.replace("/", "-").replace("*", "all"))
                self.assertEqual(caught.exception.code, "nothing_admitted")

    def test_a_generator_at_the_tolerance_in_the_ledger_is_held(self):
        """Known-wrong control: without the ledger's rate, function_extracts 1.1.0 would be admitted again."""
        self._decided(defective=21)
        with self.assertRaises(self.route.QualifiedAdmissionError) as caught:
            self._admit()
        self.assertEqual(caught.exception.code, "nothing_admitted")
        held = self.route.held_generators(decisions.DecisionLedger.open(self.decisions, for_append=False), {},
                                          [self.generator])
        self.assertIn("at or above the tolerance", held[self.generator])

    def test_a_component_a_reviewer_rejected_is_never_admitted(self):
        self._decided(defective=1, rejected=self.components[:1])
        result = self._admit()
        self.assertEqual((result["admitted"], result["left_out"]), (3, {"rejected_by_a_reviewer": 1}))
        ledger = decisions.DecisionLedger.open(self.decisions, for_append=False)
        self.assertIsNotNone(ledger.rejected("another-identity", self.components[0].package.package_digest))

    def test_rejected_members_must_match_the_defective_count(self):
        batch = self.generator + "@" + "e" * 12
        records = _records(batch, 1767, "e")
        entry = _batch_entry(records, defective=2)
        entry["decision"]["rejected_members"] = [[self.components[0].identity, "v", "d" * 64]]
        with self.assertRaises(decisions.DecisionLedgerError):
            _append(self.decisions, _review({batch: entry}, "q"), {batch: records})


class AuditTests(unittest.TestCase):
    """The ongoing audit: published batches sampled after publication, withdrawals written, versions held."""

    def setUp(self):
        from tools.component_qualification import audit, qualified_admission
        self.audit, self.route = audit, qualified_admission
        self.folder = Path(tempfile.mkdtemp(prefix="generated-audit-"))
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.components = _components(4, tag="u")
        self.batch = self.components[0].batch
        self.generator = sampling.generator_of(self.batch)
        self.qualification = self.folder / "qualification"
        self.qualification.mkdir()
        (self.qualification / "qualification.jsonl").write_text("".join(json.dumps({
            "identity": component.identity, "outcome": "qualified", "batch": component.batch, "line": component.line,
            "record_version": component.record_version, "package_digest": component.package.package_digest,
            "qualifier": dict(QUALIFIER), "vetting": {"implementation_tested": "fixture"},
            "self_test_sha256": "0" * 64, "checks": []}) + "\n" for component in self.components))
        self.decisions = self.folder / "decisions.jsonl"
        decisions.create(self.decisions, **CREATED)
        self.held = self.folder / "held.json"
        self.held.write_text(json.dumps({"record_type": self.route.HELD_RECORD, "held": []}))
        store = {component.identity: component for component in self.components}
        self.admitted = self.folder / "admitted"
        self.route.admit_qualified(self.qualification, None, self.decisions, self.held, self.admitted, "2026-10-05",
                                   ROOT, components=store)
        self.config = self.folder / "audit.json"
        self.config.write_text(json.dumps({
            "record_type": self.audit.CONFIG_RECORD, "reviewer": REVIEWER, "producer_family": "anthropic",
            "daily_call_ceiling": 60, "admission_folders": [str(self.admitted)],
            "decision_ledger": str(self.decisions), "held_versions": str(self.held), "store_root": "unused",
            "state": str(self.folder / "state"), "host_config": "/data/host.json"}))
        self.calls = []

    def _review(self, rejected=1, admissible=True, calls=2):
        """The sampled review's place: a plan pass, then a decided run that records its calls and verdicts."""
        def review(options, root):
            self.calls.append(options)
            if not options.authorize_model_calls:
                Path(options.output).write_text(json.dumps({"batches": {
                    batch: {"calls_planned": calls} for batch in options.batch}, "calls_that_do_not_fit": []}))
                return {}
            with open(options.ledger, "a") as stream:
                for number in range(6 + calls):
                    stream.write(json.dumps({"record_type": "candidate_review_batch_call/v1", "sequence": number},
                                            separators=(",", ":")) + "\n")
            verdicts = [{"identity": component.identity, "decision": "reject" if index < rejected else "approve",
                         "reason": "the schema check accepts an empty document" if index < rejected else "",
                         "criteria": ["contracts_and_checks"] if index < rejected else [],
                         "call_ref": f"run#{index}", "body_sha256": component.package.package_digest}
                        for index, component in enumerate(self.components)]
            Path(options.output).write_text(json.dumps({"reviewer": REVIEWER, "admissible": admissible,
                                                        "batches": {self.batch: {"verdicts": verdicts}}}))
            return {"calls_used": 6 + calls}
        return review

    def test_a_rejected_component_gets_a_ready_withdrawal_request(self):
        result = self.audit.run(self.config, review=self._review(rejected=1))
        self.assertEqual(result["withdrawal_requests"], 1)
        [request_path] = (self.folder / "state" / "withdrawals").glob("*.json")
        request = json.loads(request_path.read_text())
        self.assertEqual(request["identity"], self.components[0].identity)
        self.assertTrue(request["command"].startswith(
            "loop-engine service withdraw-catalogue-item --config /data/host.json --identity "))
        self.assertIn("the schema check accepts an empty document", request["command"])
        self.assertFalse(request["executed"])
        self.assertEqual([options.authorize_model_calls for options in self.calls], [False, True])
        self.assertEqual(self.calls[1].call_ceiling, 6 + 2 + self.audit.RETRY_SLACK)
        status = json.loads((self.folder / "state" / "status.json").read_text())
        self.assertEqual(status["calls_spent_today_after"], 8)

    def test_a_spent_daily_ceiling_leaves_the_batch_waiting(self):
        runs = self.folder / "state" / "runs" / (datetime_now_day() + "T000000Z-earlier")
        runs.mkdir(parents=True)
        (runs / "panel-ledger.jsonl").write_text("".join(json.dumps(
            {"record_type": "candidate_review_batch_call/v1", "sequence": number}, separators=(",", ":")) + "\n"
            for number in range(58)))
        result = self.audit.run(self.config, review=self._review())
        self.assertEqual(self.calls, [])
        self.assertIn(self.batch, result["waiting"])

    def test_a_generator_at_the_tolerance_is_held_after_the_audit(self):
        other = self.generator + "@" + "e" * 12
        records = _records(other, 1767, "e")
        _append(self.decisions, _review({other: _batch_entry(records, defective=21)}, "q"), {other: records})
        self.audit.run(self.config, review=self._review(rejected=0))
        held = self.route.read_held(self.held)
        self.assertIn(self.generator, held)
        self.assertIn("at or above the tolerance", held[self.generator]["reason"])


def datetime_now_day() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
