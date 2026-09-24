"""Checks for the committed source declaration and its strict reader.

The committed declaration must read cleanly, carry a note for every source,
exclude the four collections the September 22 curation dropped, and name
every owner seed of September 24. The reader refuses an unknown field, a
repeated source identity, a size band that is not low..high and a kind
outside the package kinds.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import test_licensed_import_support  # noqa: F401 (sets the import path)
from loop_engine.core.library_ingestion.record_rules import LibraryRecordError

from licensed_import.sources import read_sources

DECLARATION = Path(__file__).resolve().parent / "licensed_import" / "sources.json"


class SourceDeclarationChecks(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(DECLARATION.read_text(encoding="utf-8"))

    def test_the_committed_declaration_reads_cleanly(self):
        record = read_sources(self.value)
        excluded = {row["repository"] for row in record["excluded_repositories"]}
        self.assertEqual(excluded, {"dallay/agents-skills", "sickn33/antigravity-awesome-skills",
                                    "jeremylongshore/claude-code-plugins-plus-skills", "davila7/claude-code-templates"})
        seeds = {row["seed"] for row in record["owner_seeds"]}
        for name in ("gstack", "caveman", "ponytail", "i-have-adhd", "ui-ux-pro-max", "taste-skill", "impeccable",
                     "hyperframes", "emil", "gsap", "graphify", "last30days", "agent-browser", "find-skills",
                     "claude-hud", "remotion", "marketingskills", "humanizer", "social-media-skills"):
            self.assertIn(name, seeds)
        self.assertTrue(all(row["note"].strip() for row in record["repositories"]))

    def test_known_wrong_declarations_are_refused(self):
        cases = []
        unknown = copy.deepcopy(self.value)
        unknown["repositories"][0]["licence_override"] = "MIT"
        cases.append(unknown)
        repeated = copy.deepcopy(self.value)
        repeated["repositories"].append(dict(repeated["repositories"][0]))
        cases.append(repeated)
        band = copy.deepcopy(self.value)
        band["code_search"][0]["size_bands"] = [[900, 100]]
        cases.append(band)
        kind = copy.deepcopy(self.value)
        kind["code_search"][0]["kind"] = "anything"
        cases.append(kind)
        for value in cases:
            with self.assertRaises(LibraryRecordError):
                read_sources(value)


if __name__ == "__main__":
    unittest.main()
