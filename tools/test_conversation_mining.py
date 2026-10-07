"""Private intake and vocabulary regression checks; synthetic inputs only, no provider calls."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools")]
from conversation_mining import connectors, extract, integrate, mine, records
from query_multiplier import generate_dimensions as generation
from query_multiplier.programs import agent_signal_grid_v1 as program


class Intake(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        path = self.root / name
        path.write_text(value, encoding="utf-8")
        return path

    def signal(self, **changes):
        return records.Signal(**{**dict(source="prompt_log_text", locator="promptlog:fixture", intent="request",
            phrases=("reusable components",), dimensions=(), weight=1, recorded_at="2026-10-07T12:00:00Z"), **changes})

    def test_normal_title_and_distinct_turns_have_opaque_locators(self):
        document = [{"title": "Private planning / with spaces", "mapping": {
            name: {"message": {"author": {"role": "user"}, "content": {"parts": ["Please add reusable components"]}}}
            for name in ("first", "second")}}]
        path = self.write("a normal export.json", json.dumps(document))
        rows, summary = mine.mine({"chatgpt_export_json": path}, days=None)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row["locator"] for row in rows}), 2)
        self.assertNotIn("Private planning", json.dumps(rows))
        self.assertEqual(summary["read_errors"], 0)

    def test_wrong_json_shapes_do_not_abort_later_claude_turns(self):
        path = self.write("session.jsonl", '\n'.join(map(json.dumps, [[], {"type": "user", "message": []},
            {"type": "user", "message": {"content": "Please add useful files"}}])))
        rows, summary = mine.mine({"claude_code_jsonl": path}, days=None)
        self.assertEqual(len(rows), 1)
        self.assertGreaterEqual(summary["read_errors"], 1)

    def test_wrong_codex_payload_shape_and_text_blocks_do_not_abort(self):
        path = self.write("session.jsonl", '\n'.join(map(json.dumps, [[], {"payload": "wrong"},
            {"payload": {"type": "message", "role": "user", "content": [{"text": None}, {"text": "Add components"}]}}])))
        rows, summary = mine.mine({"codex_rollout_jsonl": path}, days=None)
        self.assertEqual(len(rows), 1)
        self.assertEqual(summary["read_errors"], 2)

    def test_url_only_request_survives_mining_and_queue_compilation(self):
        reference = "https://github.com/example/reusable-fixtures"
        path = self.write("prompt log.txt", reference + '\n')
        rows, _ = mine.mine({"prompt_log_text": path}, days=None)
        self.assertEqual(rows[0]["references"], [reference])
        queued = integrate.to_queue(rows)
        self.assertEqual(queued[0].record()["references"], [reference])
        self.assertFalse(queued[0].record()["publication_approved"])

    def test_signed_private_and_non_https_references_are_not_kept(self):
        self.assertEqual(extract.extract_references("https://example.com/?token=synthetic-value https://127.0.0.1/x http://example.com/x"), ())

    def test_sensitive_marker_is_refused_at_the_record_boundary(self):
        with self.assertRaises(ValueError):
            self.signal(phrases=("internal confidential",)).record()
        with patch("knowledge_radar.query_matrix.words", side_effect=lambda value: value):
            wrong = self.signal(phrases=("internal confidential",)).record()
        self.assertIn("internal confidential", wrong["phrases"])

    def test_changed_digest_and_old_version_are_refused(self):
        value = self.signal().record()
        self.assertEqual(records.read_signal(value), value)
        for wrong in ({**value, "weight": 2}, {**value, "record_type": "owner_signal_record/v1"}):
            with self.assertRaises(ValueError):
                integrate.to_queue([wrong])

    def test_shared_first_phrase_does_not_collapse_distinct_requests(self):
        values = [self.signal(phrases=("add components", phrase)).record() for phrase in ("video layers", "hardware measurements")]
        self.assertEqual(len(integrate.to_queue(values)), 2)
        self.assertEqual(integrate.to_queue([values[0], values[0]])[0].occurrences, 2)

    def test_actual_message_time_owns_the_window(self):
        now = datetime.now(timezone.utc)
        records_ = [{"type": "user", "timestamp": stamp, "message": {"content": "Add reusable components"}}
                    for stamp in ((now - timedelta(hours=40)).isoformat(), now.isoformat(), "")]
        path = self.write("recently touched.jsonl", '\n'.join(map(json.dumps, records_)))
        rows, summary = mine.mine({"claude_code_jsonl": path}, days=None, since=now-timedelta(hours=36))
        self.assertEqual(len(rows), 1)
        self.assertEqual(summary["timestamp_excluded"], 2)

    def test_notifications_are_context_but_image_prefixed_requests_survive(self):
        path = self.write("messages.jsonl", '\n'.join(json.dumps({"type": "user", "message": {"content": text}})
            for text in ("<task-notification>generated output</task-notification>", '<image name="fixture"></image> Please add useful layers')))
        rows = list(connectors.claude_code(path))
        self.assertEqual(len(rows), 1)
        self.assertIn("useful layers", rows[0].text)

    def test_oversize_export_has_an_explicit_read_error(self):
        path = self.write("conversations.json", "[]")
        with patch.object(connectors, "MAX_DOCUMENT_BYTES", 1):
            rows = list(connectors.chatgpt_export(path))
        self.assertEqual(rows[0].role, connectors.READ_ERROR)

    def test_sensitive_drops_are_counted_when_extracted_not_after_removal(self):
        path = self.write("sensitive.txt", "internal confidential\nPlease add useful components\n")
        rows, summary = mine.mine({"prompt_log_text": path}, days=None)
        self.assertEqual(len(rows), 1)
        self.assertEqual(summary["sensitive_dropped"], 1)
        self.assertNotIn("confidential", json.dumps(rows))

    def test_complete_run_counts_are_bound_by_the_run_digest(self):
        record = records.RunRecord("fixture", (), 1, 2, 3, (), "start", "finish",
                                   read_errors=4, timestamp_excluded=5, truncated_turns=6, capped_files=7).record()
        digest = record.pop("run_digest")
        self.assertEqual(digest, records._digest(record))
        record["read_errors"] += 1
        self.assertNotEqual(digest, records._digest(record))


class Dimensions(unittest.TestCase):
    def test_the_shipped_program_resolves_every_parameter_and_is_deterministic(self):
        input_ = {"families": program.FAMILIES, "derive": program.DERIVE}
        first = generation.generate(input_)
        self.assertEqual(first, generation.generate(input_))
        self.assertEqual(len(first), 6)
        self.assertTrue(all(len(row["values"]) <= generation.MAX_VALUES_PER_DIMENSION for row in first))
        self.assertNotIn("{role}", json.dumps(first))
        self.assertNotIn("{time}", json.dumps(first))

    def test_sensitive_values_are_refused_instead_of_restored(self):
        with self.assertRaises(generation.GenerationError):
            generation._mkdim("test", "Test", "topic", [("test", "internal confidential", {})])

    def test_missing_or_attribute_style_template_bindings_are_refused(self):
        family = generation.Family("test", "topic", "Test", (("a", "model"),))
        for pattern in ("{v} {time}", "{v.__class__}", "{v!r}"):
            with self.assertRaises(generation.GenerationError):
                generation.template(family, name="test", title="Test", patterns=(pattern,))

    def test_merge_preserves_input_and_refuses_curated_collisions(self):
        base = {"dimensions": [{"id": "held"}], "provenance": []}
        before = json.dumps(base)
        generation.merge(base, [{"id": "new"}])
        self.assertEqual(json.dumps(base), before)
        with self.assertRaises(generation.GenerationError):
            generation.merge(base, [{"id": "held"}])

    def test_duplicate_normalized_value_ids_do_not_silently_overwrite(self):
        with self.assertRaises(generation.GenerationError):
            generation._mkdim("test", "Test", "topic", [("same", "one", {}), ("same", "two", {})])


if __name__ == "__main__":
    unittest.main()
