"""Prove that the service documentation check accepts the truth and rejects drift.

The positive control runs the check against this repository, so a renamed or
removed service fact fails continuous integration. Every other case is a
known-wrong one: either a documented fact that the source never had, or a real
fact that the source stopped having. Each must be refused by name.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from check_service_documentation import DOCUMENTED_PAGES, check, page_facts, source_facts

REPOSITORY = Path(__file__).resolve().parents[1]
#: The files the check reads. A temporary repository holds copies of these.
COPIED = (
    "src/loop_engine/core/service_runtime",
    "src/loop_engine/core/provisioning_server.py",
    "src/loop_engine/core/provisioning_mcp.py",
    "src/loop_engine/core/harness_intelligence.py",
    "src/loop_engine/core/retrieval.py",
    "src/loop_engine/service_cli.py",
    "src/loop_engine/cli_help.py",
    *DOCUMENTED_PAGES,
)


def build_copy(root: Path) -> Path:
    for entry in COPIED:
        source, target = REPOSITORY / entry, root / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return root


def edit(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError("the fixture text was not found in " + relative)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


class ServiceDocumentationCheck(unittest.TestCase):
    """The check must follow the source, not the pages, in both directions."""

    def kinds(self, report):
        return sorted({finding["kind"] for finding in report["findings"]})

    def values(self, report):
        return sorted(finding["value"] for finding in report["findings"])

    def test_the_committed_pages_match_the_committed_source(self):
        report = check(REPOSITORY)
        self.assertEqual(report["findings"], [], msg=(
            "the service pages name facts the service source does not have; "
            "run tools/check_service_documentation.py for the list"))
        self.assertGreater(report["facts_checked"], 200)

    def test_every_documented_page_exists(self):
        for page in DOCUMENTED_PAGES:
            self.assertTrue((REPOSITORY / page).is_file(), page)

    def test_a_refusal_code_no_source_raises_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-serving-and-connections.md",
                 "| `service_busy` | 503 |", "| `service_exhausted` | 503 |")
            report = check(root)
            self.assertIn("refusal_code", self.kinds(report))
            self.assertIn("service_exhausted", self.values(report))

    def test_a_refusal_code_the_source_stops_raising_is_refused(self):
        """The real drift case: the page is untouched and the source renames a code."""
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            self.assertEqual(check(root)["findings"], [])
            edit(root, "src/loop_engine/core/service_runtime/http.py",
                 'ServiceHttpError("download_requires_read")',
                 'ServiceHttpError("download_needs_read")')
            report = check(root)
            self.assertIn("refusal_code", self.kinds(report))
            self.assertIn("download_requires_read", self.values(report))

    def test_an_address_the_service_does_not_serve_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-serving-and-connections.md",
                 "| `/api/v1/usage` | GET |", "| `/api/v1/invoices` | GET |")
            report = check(root)
            self.assertIn("address", self.kinds(report))
            self.assertIn("/api/v1/invoices", self.values(report))

    def test_an_address_the_service_stops_serving_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "src/loop_engine/core/service_runtime/http.py",
                 '"/api/v1/usage"', '"/api/v1/consumption"')
            report = check(root)
            self.assertIn("address", self.kinds(report))
            self.assertIn("/api/v1/usage", self.values(report))

    def test_a_record_version_the_source_does_not_declare_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-searching-and-retrieving.md",
                 "service_retrieval_request/v1", "service_retrieval_request/v4")
            report = check(root)
            self.assertIn("record_type", self.kinds(report))
            self.assertIn("service_retrieval_request/v4", self.values(report))

    def test_a_field_name_the_source_does_not_use_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-searching-and-retrieving.md",
                 "`body_allowed`", "`body_permitted`")
            report = check(root)
            self.assertIn("name", self.kinds(report))
            self.assertIn("body_permitted", self.values(report))

    def test_a_scope_outside_the_vocabulary_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-troubleshooting.md",
                 "`provisioning:read`", "`provisioning:write`")
            report = check(root)
            self.assertIn("scope", self.kinds(report))
            self.assertIn("provisioning:write", self.values(report))

    def test_a_command_the_interface_does_not_have_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            page = root / DOCUMENTED_PAGES[0]
            page.write_text(page.read_text(encoding="utf-8")
                            + "\n```bash\nloop-engine service explode --config /absolute/path/host.json\n```\n",
                            encoding="utf-8")
            report = check(root)
            self.assertIn("command", self.kinds(report))

    def test_a_client_command_no_recipe_publishes_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, DOCUMENTED_PAGES[0], "codex mcp list", "codex mcp inspect")
            report = check(root)
            self.assertIn("command", self.kinds(report))
            self.assertIn("codex mcp inspect", self.values(report))

    def test_a_served_recipe_that_no_page_documents_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, DOCUMENTED_PAGES[0], "```bash\ncodex mcp list\n```\n\n", "")
            report = check(root)
            self.assertIn("recipe", self.kinds(report))
            self.assertIn("codex", self.values(report))

    def test_a_missing_page_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            (root / DOCUMENTED_PAGES[3]).unlink()
            report = check(root)
            self.assertIn("page", self.kinds(report))

    def test_the_source_reader_finds_a_real_service_surface(self):
        facts = source_facts(REPOSITORY)
        for code in ("unauthorized", "insufficient_scope", "item_unavailable",
                     "failed_attempt_limit_reached", "item_license_not_accepted"):
            self.assertIn(code, facts["refusal_codes"], code)
        for address in ("/mcp", "/api/v1/session", "/api/v1/download", "/connect"):
            self.assertIn(address, facts["addresses"], address)
        self.assertEqual(facts["credential_variable"], "BALTOR_SERVICE_TOKEN")
        self.assertIn("service", facts["root_commands"])
        self.assertLessEqual({"serve", "configure", "issue-key", "smoke"}, facts["service_commands"])

    def test_the_page_reader_separates_tables_blocks_and_spans(self):
        found = page_facts("| Code | Status |\n|---|---|\n| `example_code` | 400 |\n"
                           "\ntext with `inline_name` here.\n"
                           "\n```bash\nloop-engine service serve --config /absolute/path/host.json\n```\n"
                           "\n| Field | Meaning |\n|---|---|\n| `not_a_code` | text |\n")
        self.assertEqual(found["refusal_codes"], ["example_code"])
        self.assertIn("inline_name", found["tokens"])
        self.assertEqual(found["commands"],
                         ["loop-engine service serve --config /absolute/path/host.json"])


if __name__ == "__main__":
    unittest.main()
