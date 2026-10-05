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
    planted controls among them, and records each run it is asked to make; with ``answers`` false it makes no call,
    as when the provider is unavailable."""

    def __init__(self, approve=(), answers: bool = True) -> None:
        self.approve, self.answers, self.runs = set(approve), answers, []

    def run(self, request):
        self.runs.append(request)
        if not self.answers:
            return SimpleNamespace(run_id=request.run_id, items=[], calls=[], stop_reason="completed",
                                   totals=lambda: {"calls": 0})
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
        reader = SimpleNamespace(rows=lambda lines=(): [{"record_id": identity} for identity in store],
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

    def test_a_batch_the_reviewer_never_saw_stays_undecided(self):
        with self._offline(ScriptedPanel(answers=False)):
            result = sampled_review.command(self._options(), ROOT)
        self.assertEqual(result["decisions"][self.batch]["outcome"], sampling.WITHHELD)
        self.assertEqual(result["decision_ledger"]["appended_sequences"], [])
        self.assertEqual([row["batch"] for row in result["decision_ledger"]["not_asked"]], [self.batch])
        self.assertEqual(self._entries(), [])
        panel = ScriptedPanel(approve=[component.identity for component in self.components])
        with self._offline(panel):
            again = sampled_review.command(self._options(seed="a-fresh-seed-0123456789"), ROOT)
        self.assertEqual(again["decisions"][self.batch]["outcome"], sampling.ACCEPTED)

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

    def test_backfill_never_writes_into_a_file_that_is_not_a_ledger(self):
        decided = self.folder / "decided-identities.txt"
        decided.write_bytes(b"")
        with self.assertRaises(decisions.DecisionLedgerError) as caught:
            decisions.backfill(decided, self._reviews()[:1], recorded_at="2026-10-05T12:00:00Z")
        self.assertEqual(caught.exception.code, "decision_ledger_not_a_ledger")
        self.assertEqual(decided.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
