"""Local mixed-format candidate-search integrity and no-answer controls."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import search_format_candidates as subject

ROOT = Path(__file__).resolve().parent


class MixedFormatSearchChecks(unittest.TestCase):
    def test_six_logical_items_with_digest_bound_non_markdown_paths(self) -> None:
        items, _, _, _ = subject.validated_catalogue()
        self.assertEqual(len(items), 6)
        result = subject.search(item_id="baltor.connection.json-shape-stdio.v1",
                                client="codex")
        self.assertEqual(result["outcome"], "matches")
        card = result["matches"][0]
        self.assertEqual(card["kind"], "local_protocol_server_connection")
        self.assertTrue(any(row["path"].endswith(".toml") for row in card["delivery_files"]))
        self.assertTrue(any(row["path"].endswith(".py") for row in card["delivery_files"]))
        self.assertFalse(any(row["path"].endswith(".mcp.json") for row in card["delivery_files"]))
        self.assertFalse(any(row["path"].endswith("opencode.json") for row in card["delivery_files"]))
        self.assertNotIn("body", card)
        without_client = subject.search(item_id="baltor.connection.json-shape-stdio.v1")
        self.assertTrue(without_client["matches"][0]["variant_selection_required"])
        self.assertNotIn("delivery_files", without_client["matches"][0])

    def test_task_query_and_client_filter(self) -> None:
        result = subject.search(query="audit CSV duplicate headers")
        self.assertEqual(result["outcome"], "matches")
        self.assertEqual(result["matches"][0]["id"], "baltor.tool.audit-csv-structure.v1")
        filtered = subject.search(item_id="baltor.connection.json-shape-stdio.v1", client="pi")
        self.assertEqual(filtered["outcome"], "no_match")
        tool = subject.search(item_id="baltor.tool.audit-jsonl-identities.v1", client="codex")
        self.assertEqual(tool["outcome"], "matches")
        self.assertTrue(any(row["path"].endswith("confined_input.py")
                            for row in tool["matches"][0]["delivery_files"]))

    def test_singular_query_matches_plural_identity_metadata(self) -> None:
        result = subject.search(query="identity audit JSON Lines")
        self.assertEqual(result["outcome"], "matches")
        self.assertEqual(result["matches"][0]["id"], "baltor.tool.audit-jsonl-identities.v1")

    def test_unrelated_query_abstains(self) -> None:
        result = subject.search(query="bake sourdough rye bread")
        self.assertEqual(result["outcome"], "no_match")

    def test_changed_instruction_bytes_are_refused_before_search(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "batch"
            shutil.copytree(ROOT, copied)
            path = copied / "context" / "profile-one-csv" / "codex" / "work" / "AGENTS.md"
            path.write_text(path.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
            with (
                patch.object(subject, "ROOT", copied),
                patch.object(subject, "CATALOG", copied / "candidate-items.json"),
                patch.object(subject, "MANIFEST", copied / "manifest.json"),
                self.assertRaisesRegex(subject.FormatCandidateSearchError,
                                       "source manifest differs"),
            ):
                subject.search(item_id="baltor.context.profile-one-csv.v1")

    def test_changed_catalogue_state_and_missing_helper_are_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "batch"
            shutil.copytree(ROOT, copied)
            catalog_path = copied / "candidate-items.json"
            data = json.loads(catalog_path.read_text(encoding="utf-8"))
            data["approval_state"] = "approved"
            catalog_path.write_text(json.dumps(data), encoding="utf-8")
            with (
                patch.object(subject, "ROOT", copied),
                patch.object(subject, "CATALOG", catalog_path),
                patch.object(subject, "MANIFEST", copied / "manifest.json"),
                self.assertRaisesRegex(subject.FormatCandidateSearchError,
                                       "unsupported logical candidate catalogue"),
            ):
                subject.validated_catalogue()
            data["approval_state"] = "none"
            data["items"][3]["delivery_variants"]["codex"] = [
                path for path in data["items"][3]["delivery_variants"]["codex"]
                if not path.endswith("confined_input.py")
            ]
            catalog_path.write_text(json.dumps(data), encoding="utf-8")
            with (
                patch.object(subject, "ROOT", copied),
                patch.object(subject, "CATALOG", catalog_path),
                patch.object(subject, "MANIFEST", copied / "manifest.json"),
                self.assertRaisesRegex(subject.FormatCandidateSearchError,
                                       "local Python dependency missing"),
            ):
                subject.validated_catalogue()

    def test_secret_bearing_metadata_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "batch"
            shutil.copytree(ROOT, copied)
            catalog_path = copied / "candidate-items.json"
            data = json.loads(catalog_path.read_text(encoding="utf-8"))
            data["items"][0]["description"] = "Bearer planted-secret-value"
            catalog_path.write_text(json.dumps(data), encoding="utf-8")
            with (
                patch.object(subject, "ROOT", copied),
                patch.object(subject, "CATALOG", catalog_path),
                patch.object(subject, "MANIFEST", copied / "manifest.json"),
                self.assertRaisesRegex(subject.FormatCandidateSearchError,
                                       "unsafe or empty candidate metadata"),
            ):
                subject.validated_catalogue()

    def test_review_notes_and_test_receipts_cannot_be_delivery_files(self) -> None:
        planted = (
            ("baltor.context.profile-one-csv.v1", "codex",
             "context/profile-one-csv/review-note.json"),
            ("baltor.tool.audit-csv-structure.v1", "codex", "tools/REVIEW-NOTE.md"),
            ("baltor.connection.json-shape-stdio.v1", "opencode",
             "connections/json-shape-stdio/tests/test_server.py"),
        )
        for item_id, client, path in planted:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                copied = Path(directory) / "batch"
                shutil.copytree(ROOT, copied)
                catalog_path = copied / "candidate-items.json"
                data = json.loads(catalog_path.read_text(encoding="utf-8"))
                item = next(row for row in data["items"] if row["id"] == item_id)
                item["delivery_variants"][client].append(path)
                catalog_path.write_text(json.dumps(data), encoding="utf-8")
                with (
                    patch.object(subject, "ROOT", copied),
                    patch.object(subject, "CATALOG", catalog_path),
                    patch.object(subject, "MANIFEST", copied / "manifest.json"),
                    self.assertRaisesRegex(subject.FormatCandidateSearchError,
                                           "non-payload delivery file"),
                ):
                    subject.validated_catalogue()

    def test_one_client_cannot_receive_another_clients_layout(self) -> None:
        planted = (
            ("baltor.context.profile-one-csv.v1",
             "context/profile-one-csv/claude/work/AGENTS.md"),
            ("baltor.connection.json-shape-stdio.v1",
             "connections/json-shape-stdio/layouts/claude/work/.mcp.json"),
        )
        for item_id, path in planted:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                copied = Path(directory) / "batch"
                shutil.copytree(ROOT, copied)
                catalog_path = copied / "candidate-items.json"
                data = json.loads(catalog_path.read_text(encoding="utf-8"))
                item = next(row for row in data["items"] if row["id"] == item_id)
                item["delivery_variants"]["codex"].append(path)
                catalog_path.write_text(json.dumps(data), encoding="utf-8")
                with (
                    patch.object(subject, "ROOT", copied),
                    patch.object(subject, "CATALOG", catalog_path),
                    patch.object(subject, "MANIFEST", copied / "manifest.json"),
                    self.assertRaisesRegex(subject.FormatCandidateSearchError,
                                           "wrong client layout"),
                ):
                    subject.validated_catalogue()


if __name__ == "__main__":
    unittest.main()
