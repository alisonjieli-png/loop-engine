"""Prove that the service documentation check accepts the truth and rejects drift.

The positive control runs the check against this repository, so a renamed or
removed service fact fails continuous integration. Every other case is a
known-wrong one: either a documented fact that the source never had, or a real
fact that the source stopped having. Each must be refused by name.
"""
from __future__ import annotations

import ast
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from check_service_documentation import (
    DOCUMENTED_PAGES,
    _raised_status,
    check,
    page_facts,
    source_facts,
)

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
#: A true refusal row on the troubleshooting page, and the same row with a
#: status the service does not answer with.
STATUS_PAGE = "docs/guides/service-troubleshooting.md"
TRUE_STATUS_ROW = "| `item_unavailable` | 404 |"
WRONG_STATUS_ROW = "| `item_unavailable` | 403 |"
#: The start of the branch of the transport's status function that answers
#: `item_unavailable`, and the same start with that one code moved ahead of it
#: to a status no page states.
HTTP_MODULE = "src/loop_engine/core/service_runtime/http.py"
STATUS_BRANCH = '    if code in ("item_unavailable", "managed_access_token_not_found",'
MOVED_STATUS_BRANCH = ('    if code == "item_unavailable":\n        return 410, code\n'
                       '    if code in ("managed_access_token_not_found",')
#: The default status of the transport refusal, and the same default moved.
DEFAULT_STATUS = "def __init__(self, code, status=400, *,"
MOVED_DEFAULT_STATUS = "def __init__(self, code, status=422, *,"


def build_copy(root: Path) -> Path:
    for entry in COPIED:
        source, target = REPOSITORY / entry, root / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return root


def edit(root: Path, relative: str, old: str, new: str, *, every: bool = False) -> None:
    """Replace the first occurrence, or with `every` each occurrence, of a fixture text."""
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError("the fixture text was not found in " + relative)
    path.write_text(text.replace(old, new) if every else text.replace(old, new, 1), encoding="utf-8")


class ServiceDocumentationCheck(unittest.TestCase):
    """The check must follow the source, not the pages, in both directions."""

    def kinds(self, report):
        return sorted({finding["kind"] for finding in report["findings"]})

    def values(self, report):
        return sorted(finding["value"] for finding in report["findings"])

    def test_local_refusal_helper_is_followed_but_a_nonraising_helper_is_not(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            path = root / "src/loop_engine/core/service_runtime/documentation_helper_fixture.py"
            path.write_text('def named_refusal(code):\n    raise ServiceRuntimeError(code)\n'
                            'def work():\n    named_refusal("documentation_helper_refusal")\n')
            facts = source_facts(root)
            self.assertEqual(facts["refusal_statuses"].get("documentation_helper_refusal"), {400})
            path.write_text('def named_refusal(code):\n    return code\n'
                            'def work():\n    named_refusal("documentation_helper_refusal")\n')
            facts = source_facts(root)
            self.assertNotIn("documentation_helper_refusal", facts["refusal_statuses"])

    def test_the_committed_pages_match_the_committed_source(self):
        report = check(REPOSITORY)
        self.assertEqual(report["findings"], [], msg=(
            "the service pages name facts the service source does not have; "
            "run tools/check_service_documentation.py for the list"))
        self.assertGreater(report["facts_checked"], 200)

    def test_every_documented_page_exists(self):
        for page in DOCUMENTED_PAGES:
            self.assertTrue((REPOSITORY / page).is_file(), page)

    def test_every_customer_page_the_guides_index_lists_is_held_to_the_source(self):
        """A customer page the index lists and this check skips could say anything."""
        text = (REPOSITORY / "docs/guides/README.md").read_text(encoding="utf-8")
        section = text.split("## For a paying customer of the hosted service", 1)[1].split("\n## ", 1)[0]
        listed = {"docs/guides/" + name for line in section.splitlines() if line.startswith("| [")
                  for name in re.findall(r"\]\(([a-z0-9-]+\.md)\)", line)}
        self.assertEqual(listed, set(DOCUMENTED_PAGES))

    def test_a_fact_on_the_usage_page_the_source_does_not_declare_is_refused(self):
        """The pages restored from the documentation branch are held like the first four."""
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-usage-and-what-you-pay-for.md",
                 "`durable_tenant_usage/v1`", "`durable_tenant_usage/v2`")
            edit(root, "docs/guides/service-your-account.md",
                 "`service_client_access_options/v1`", "`service_client_access_options/v7`")
            edit(root, "docs/guides/service-what-baltor-is.md",
                 "`catalogue_package/v1`", "`catalogue_package/v3`")
            report = check(root)
            self.assertIn("record_type", self.kinds(report))
            self.assertLessEqual({"durable_tenant_usage/v2", "service_client_access_options/v7",
                                  "catalogue_package/v3"}, set(self.values(report)))

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
                 'ServiceHttpError("package_file_requires_download")',
                 'ServiceHttpError("package_file_needs_download")')
            report = check(root)
            self.assertIn("refusal_code", self.kinds(report))
            self.assertIn("package_file_requires_download", self.values(report))

    def test_an_address_the_service_does_not_serve_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-serving-and-connections.md",
                 "| `/api/v1/usage` | GET |", "| `/api/v1/invoices` | GET |")
            report = check(root)
            self.assertIn("address", self.kinds(report))
            self.assertIn("/api/v1/invoices", self.values(report))

    def test_an_address_the_service_stops_serving_is_refused(self):
        # The address is named twice in the transport: in the route table read
        # before authentication and in the branch that answers it. The service
        # stops serving it only when both are renamed, so the known-wrong
        # source renames every occurrence.
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "src/loop_engine/core/service_runtime/http.py",
                 '"/api/v1/usage"', '"/api/v1/consumption"', every=True)
            report = check(root)
            self.assertIn("address", self.kinds(report))
            self.assertIn("/api/v1/usage", self.values(report))

    def test_a_page_address_the_page_table_stops_serving_is_refused(self):
        """The website addresses live in the page table, not in the transport."""
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            self.assertEqual(check(root)["findings"], [])
            edit(root, "src/loop_engine/core/service_runtime/web_pages.py",
                 '"/connect"', '"/join"', every=True)
            report = check(root)
            self.assertIn("address", self.kinds(report))
            self.assertIn("/connect", self.values(report))

    def test_the_privacy_notice_address_is_held_to_the_page_table(self):
        """The setup guide names the privacy notice address, so the page table must keep serving it."""
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            self.assertEqual(check(root)["findings"], [])
            edit(root, "src/loop_engine/core/service_runtime/web_pages.py",
                 '"/privacy"', '"/privacy-notice"', every=True)
            report = check(root)
            self.assertIn("address", self.kinds(report))
            self.assertIn("/privacy", self.values(report))

    def test_the_terms_of_service_address_is_held_to_the_page_table(self):
        """The setup guide names the terms of service address, so the page table must keep serving it."""
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            self.assertEqual(check(root)["findings"], [])
            edit(root, "src/loop_engine/core/service_runtime/web_pages.py",
                 '"/terms"', '"/terms-of-service"', every=True)
            report = check(root)
            self.assertIn("address", self.kinds(report))
            self.assertIn("/terms", self.values(report))

    def test_a_record_version_the_source_does_not_declare_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            edit(root, "docs/guides/service-searching-and-retrieving.md",
                 "service_retrieval_request/v2", "service_retrieval_request/v4")
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
            edit(root, "docs/guides/service-your-account.md",
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
        for address in ("/mcp", "/api/v1/session", "/api/v1/download", "/connect", "/privacy", "/terms"):
            self.assertIn(address, facts["addresses"], address)
        self.assertEqual(facts["credential_variable"], "BALTOR_SERVICE_TOKEN")
        self.assertIn("service", facts["root_commands"])
        self.assertLessEqual({"serve", "configure", "issue-key", "smoke"}, facts["service_commands"])

    def test_a_page_promises_a_status_the_service_does_not_answer(self):
        """Known-wrong: the refusal is real and the status beside it is not."""
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            self.assertEqual(check(root)["findings"], [])
            edit(root, STATUS_PAGE, TRUE_STATUS_ROW, WRONG_STATUS_ROW)
            report = check(root)
            self.assertIn("refusal_status", self.kinds(report))
            self.assertIn("item_unavailable 403", self.values(report))
            self.assertTrue(any("404" in finding["note"] for finding in report["findings"]),
                            report["findings"])

    def test_the_service_changes_the_status_a_refusal_answers_with(self):
        """Known-wrong: the source moves and the untouched pages become false.

        This is the case that proves the check asks the transport rather than
        comparing the pages with a second copy of the same table.
        """
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            self.assertEqual(check(root)["findings"], [])
            edit(root, HTTP_MODULE, STATUS_BRANCH, MOVED_STATUS_BRANCH)
            report = check(root)
            self.assertIn("refusal_status", self.kinds(report))
            self.assertIn("item_unavailable 404", self.values(report))

    def test_the_default_status_of_a_transport_refusal_is_read_from_the_source(self):
        """Known-wrong: the transport refusal's default status moves, and every
        page row for a refusal raised without a status of its own becomes false."""
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            self.assertEqual(check(root)["findings"], [])
            edit(root, HTTP_MODULE, DEFAULT_STATUS, MOVED_DEFAULT_STATUS)
            report = check(root)
            self.assertIn("refusal_status", self.kinds(report))
            self.assertIn("unknown_request_field 400", self.values(report))

    def test_a_page_promises_a_status_for_a_refusal_with_no_raise_site(self):
        """Known-wrong: a promise this check cannot hold to the source at all.

        `item_license_unknown` is a real refusal code, named by a constant, but
        no transport refusal is raised with it in the service source, so the
        status beside it cannot be asked of the transport.
        """
        with tempfile.TemporaryDirectory() as folder:
            root = build_copy(Path(folder))
            page = root / STATUS_PAGE
            page.write_text(page.read_text(encoding="utf-8") + (
                "\n## A refusal with no raise site\n\n| Code | Status | Meaning |\n|---|---|---|\n"
                "| `item_license_unknown` | 400 | The licence is not one the host accepts. |\n"),
                encoding="utf-8")
            report = check(root)
            self.assertIn("refusal_status_unknown", self.kinds(report))
            self.assertIn("item_license_unknown 400", self.values(report))

    def test_the_status_guard_holds_a_real_number_of_rows(self):
        """A guard that read no row would let every status case above pass."""
        facts = source_facts(REPOSITORY)
        self.assertGreater(len(facts["refusal_statuses"]), 50)
        rows = [row for page in DOCUMENTED_PAGES
                for row in page_facts((REPOSITORY / page).read_text(encoding="utf-8"))["refusal_statuses"]]
        self.assertGreater(len(rows), 50)
        for code, status in rows:
            self.assertIn(status, facts["refusal_statuses"].get(code, set()), code)

    def test_a_status_is_read_from_the_position_or_the_keyword(self):
        """A `status=` keyword must not silently fall back to the class default."""
        def raised(text):
            return _raised_status(ast.parse(text, mode="eval").body)
        self.assertEqual(raised('ServiceHttpError("example_code", 418)'), 418)
        self.assertEqual(raised('ServiceHttpError("example_code", status=418)'), 418)
        self.assertIsNone(raised('ServiceHttpError("example_code")'))

    def test_the_page_reader_separates_tables_blocks_and_spans(self):
        found = page_facts("| Code | Status |\n|---|---|\n| `example_code` | 400 |\n"
                           "\ntext with `inline_name` here.\n"
                           "\n```bash\nloop-engine service serve --config /absolute/path/host.json\n```\n"
                           "\n| Field | Meaning |\n|---|---|\n| `not_a_code` | text |\n")
        self.assertEqual(found["refusal_codes"], ["example_code"])
        self.assertEqual(found["refusal_statuses"], [("example_code", 400)])
        self.assertIn("inline_name", found["tokens"])
        self.assertEqual(found["commands"],
                         ["loop-engine service serve --config /absolute/path/host.json"])


if __name__ == "__main__":
    unittest.main()
