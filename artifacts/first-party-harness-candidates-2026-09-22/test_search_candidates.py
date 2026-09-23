"""Focused checks for the isolated, candidate-only local search tool."""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import search_candidates as search

ROOT = Path(__file__).resolve().parent


class CandidateSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.batch = Path(self.temporary.name)
        for group in search.GROUPS:
            (self.batch / "packages" / group).mkdir(parents=True)
        (self.batch / "review-notes").mkdir()
        self._candidate(
            "data", "check-invoice-units",
            "Check measurement units and approved conversions before totaling invoice lines.",
            "A kilogram to gram mismatch can distort a reported invoice amount.",
        )
        self._candidate(
            "project", "map-onboarding-friction",
            "Map observed customer onboarding friction across a product journey.",
            "Look for repeated signup confusion in supplied customer observations.",
        )
        self._candidate(
            "software", "audit-protocol-fallback",
            "Check whether protocol fallback loses required authorization behavior.",
            "A missing approval receipt is a known-wrong protocol downgrade.",
        )
        self._candidate(
            "project", "review-generic-policy-request",
            "Review whether a policy request has enough authorization evidence.",
            "Protocol fallback is one possible context for policy requests.",
        )
        shutil.copyfile(ROOT / "make_manifest.py", self.batch / "make_manifest.py")
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, str(self.batch / "make_manifest.py"),
             "--write", "--base-revision", "a" * 40],
            cwd=self.batch, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def _candidate(self, group: str, name: str, description: str, note: str) -> None:
        folder = self.batch / "packages" / group / name
        folder.mkdir()
        (folder / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n"
            f"# {name}\n\nUse only for the stated analysis.\n",
            encoding="utf-8",
        )
        (self.batch / "review-notes" / f"{name}.md").write_text(
            f"# Candidate review: {name}\n\n- Known-good example: {note}\n", encoding="utf-8",
        )

    def test_exact_name_returns_metadata_without_body(self) -> None:
        result = search.search_candidates(name="check-invoice-units", root=self.batch)
        self.assertEqual(result["outcome"], "matches")
        self.assertEqual([row["name"] for row in result["matches"]], ["check-invoice-units"])
        self.assertIn("package_path", result["matches"][0])
        self.assertEqual(len(result["matches"][0]["package_sha256"]), 64)
        self.assertEqual(len(result["matches"][0]["manifest_sha256"]), 64)
        self.assertNotIn("body", result["matches"][0])
        self.assertNotIn("A kilogram", str(result["matches"]))

    def test_natural_query_uses_note_only_as_supporting_evidence(self) -> None:
        result = search.search_candidates(query="invoice units mismatch", root=self.batch)
        self.assertEqual(result["outcome"], "matches")
        self.assertEqual(result["matches"][0]["name"], "check-invoice-units")
        self.assertIn("mismatch", result["matches"][0]["matched_terms"])

    def test_task_queries_across_groups(self) -> None:
        project = search.search_candidates(query="onboarding customer journey confusion", root=self.batch)
        self.assertEqual(project["matches"][0]["name"], "map-onboarding-friction")
        software = search.search_candidates(query="protocol fallback authorization", root=self.batch)
        self.assertEqual(software["matches"][0]["name"], "audit-protocol-fallback")

    def test_weak_secondary_match_is_suppressed(self) -> None:
        result = search.search_candidates(
            query="protocol fallback authorization", limit=10, root=self.batch,
        )
        self.assertEqual([row["name"] for row in result["matches"]], ["audit-protocol-fallback"])

    def test_unrelated_query_abstains(self) -> None:
        result = search.search_candidates(query="tectonic magma plate boundaries", root=self.batch)
        self.assertEqual(result["outcome"], "no_match")
        self.assertEqual(result["matches"], [])
        result = search.search_candidates(query="restaurant dinner reservations", root=self.batch)
        self.assertEqual(result["outcome"], "no_match")
        mixed = search.search_candidates(query="protocol fallback financial invoices", root=self.batch)
        self.assertEqual(mixed["outcome"], "no_match")

    def test_required_effect_refuses_unqualified_candidates(self) -> None:
        result = search.search_candidates(
            query="protocol fallback authorization", required_effect="external_mutation",
            root=self.batch,
        )
        self.assertEqual(result["outcome"], "no_match")
        self.assertEqual(result["effect_qualification"], "none")
        self.assertIn("cannot be matched", result["scope_warning"])

    def test_group_filter_and_bound(self) -> None:
        result = search.search_candidates(
            query="protocol fallback authorization", group="software", limit=1, root=self.batch,
        )
        self.assertEqual([row["name"] for row in result["matches"]], ["audit-protocol-fallback"])
        wrong_group = search.search_candidates(
            query="protocol fallback authorization", group="data", root=self.batch,
        )
        self.assertEqual(wrong_group["outcome"], "no_match")
        with self.assertRaisesRegex(search.CandidateSearchError, "limit"):
            search.search_candidates(query="protocol fallback", limit=11, root=self.batch)

    def test_changed_skill_or_review_note_refuses_before_search(self) -> None:
        skill = self.batch / "packages/data/check-invoice-units/SKILL.md"
        skill.write_text(skill.read_text() + "Changed after manifest.\n", encoding="utf-8")
        with self.assertRaisesRegex(search.CandidateSearchError, "exact package"):
            search.search_candidates(name="check-invoice-units", root=self.batch)
        skill.write_text(skill.read_text().replace("Changed after manifest.\n", ""), encoding="utf-8")
        note = self.batch / "review-notes/check-invoice-units.md"
        note.write_text(note.read_text() + "Changed after manifest.\n", encoding="utf-8")
        with self.assertRaisesRegex(search.CandidateSearchError, "exact package"):
            search.search_candidates(query="invoice units", root=self.batch)

    def test_manifest_status_tampering_refuses(self) -> None:
        manifest = self.batch / "manifest.json"
        manifest.write_text(
            manifest.read_text().replace('"approval_state": "none"', '"approval_state": "approved"'),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(search.CandidateSearchError, "exact package"):
            search.search_candidates(name="check-invoice-units", root=self.batch)

    def test_fts_syntax_and_sql_injection_are_literal_terms(self) -> None:
        result = search.search_candidates(query="' OR 1=1 --", root=self.batch)
        self.assertEqual(result["outcome"], "no_match")
        result = search.search_candidates(query="invoice' OR docs MATCH '*' --", root=self.batch)
        self.assertLessEqual(len(result["matches"]), 1)
        self.assertNotIn("audit-protocol-fallback", [row["name"] for row in result["matches"]])

    def test_missing_fts5_is_explicit(self) -> None:
        class NoFts:
            def execute(self, *args: object) -> None:
                raise sqlite3.OperationalError("no such module: fts5")

            def close(self) -> None:
                pass

        with patch.object(search.sqlite3, "connect", return_value=NoFts()):
            with self.assertRaisesRegex(search.CandidateSearchError, "FTS5 is unavailable"):
                search.search_candidates(query="invoice units", root=self.batch)
            with self.assertRaisesRegex(search.CandidateSearchError, "FTS5 is unavailable"):
                search.search_candidates(name="check-invoice-units", root=self.batch)


if __name__ == "__main__":
    unittest.main()
