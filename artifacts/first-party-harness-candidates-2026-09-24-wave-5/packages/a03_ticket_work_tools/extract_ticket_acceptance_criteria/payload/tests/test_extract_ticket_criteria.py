"""Tests for scripts/extract_ticket_criteria.py. Effects: starts the script as a subprocess with tickets on standard input or read from this package; writes no files.

Every ticket here is synthetic. Issue-template comment markers are assembled at run
time so that no file of the package holds one.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "extract_ticket_criteria.py"
OPEN_COMMENT, CLOSE_COMMENT = "<" + "!--", "--" + ">"

BUG_TICKET = """# Export drops leading zeros from product codes

When a product code starts with zero, the CSV export removes the zero.

## Steps to reproduce

1. Create a product with code `007`.
2. Run `python3 -m shop.export --format csv`.

## Acceptance criteria

- [ ] Exporting code `007` writes `007` to the CSV file.
- The export should feel faster.

Relevant code: src/shop/export.py:88 and the helper in formatting.py.
See https://example.com/docs/export.json for the format. Built with Node.js.
"""

VAGUE_TICKET = """Improve the CSV export

The export is slow and clunky. It should be faster and more reliable, and the code should be cleaner.
"""

TEXT_TICKET = """Price parser rejects comma decimals
Steps to reproduce:
1. Call parse_price("3,50").
Expected: parse_price returns 350.
Actual: ValueError is raised.
"""

SCENARIO_TICKET = """# Login lockout

## Acceptance criteria

Scenario: lock after failures
Given a user with 3 failed logins
When the user fails a fourth time
Then the login page shows "Account locked"

When I read the docs, nothing is said about unlocking.
"""

CHECKBOX_TICKET = """Cleanup task

Some notes about the work.

- [x] The old flag `--legacy` is removed from cli.py.
- [ ] README.md lists the new flag.

## Acceptance criteria

- [ ] README.md lists the new flag.
"""

SETEXT_TICKET = """Slow page
=========

Acceptance criteria
-------------------

- The page loads in under 2 seconds with 1000 rows.
"""

RICH_TICKET = {"key": "SHOP-12", "fields": {"summary": "Round totals to cents", "description": {
    "type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Totals show too many decimals."}]},
        {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Acceptance criteria"}]},
        {"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "Totals are rounded to 2 decimal places."}]}]},
            {"type": "listItem", "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": "The invoice PDF shows "},
                {"type": "text", "text": "12.35", "marks": [{"type": "code"}]},
                {"type": "text", "text": " for 12.345."}]}]}]},
        {"type": "codeBlock", "content": [{"type": "text", "text": "pytest tests/test_totals.py"}]}]}}}

FORM_TICKET = """### Describe the bug

Saving a draft with a long title fails.

### Steps to reproduce

1. Type a title of 300 characters.
2. Click Save draft.

### What is the current *bug* behavior?

An error toast appears and the draft is lost.

### Expected behavior

_No response_

### Acceptance criteria

- Titles keep two hundred characters or fewer.
- The new one looks good.
"""

EMAIL_TICKET = """Subject: **Wrong** VAT on invoices

Hi team, since the last release the invoice shows the wrong rate. It should be 19% but it shows 16%.
"""

LIST_TICKET = {"title": "Keep zeros",
               "acceptance_criteria": [{"text": "Code 007 stays 007 after export."}, {"text": "The export looks good."}],
               "steps_to_reproduce": ["Export product 007.", "Open the file."]}


class ExtractTicketCriteria(unittest.TestCase):
    def run_script(self, data, *arguments):
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments],
                              input=data.encode("utf-8") if isinstance(data, str) else data,
                              capture_output=True, cwd=str(PAYLOAD), timeout=60)
        return done.returncode, json.loads(done.stdout.decode("utf-8"))

    def test_markdown_bug_ticket(self):
        code, result = self.run_script(BUG_TICKET)
        self.assertEqual((code, result["status"]), (0, "ok"))
        self.assertEqual(result["title"], "Export drops leading zeros from product codes")
        texts = [item["text"] for item in result["acceptance_criteria"]]
        self.assertEqual(texts, ["Exporting code `007` writes `007` to the CSV file.", "The export should feel faster."])
        self.assertEqual(result["acceptance_criteria"][0]["line"], 12)
        self.assertTrue(result["acceptance_criteria"][0]["checkable"])
        self.assertFalse(result["acceptance_criteria"][1]["checkable"])
        self.assertEqual(result["acceptance_criteria"][1]["vague_terms"], ["faster", "feel"])
        self.assertEqual([step["id"] for step in result["reproduction_steps"]], ["R1", "R2"])
        files = {item["path"]: item for item in result["named_files"]}
        self.assertEqual(sorted(files), ["formatting.py", "src/shop/export.py"])
        self.assertEqual(files["src/shop/export.py"]["line_in_file"], 88)
        self.assertEqual(result["commands"], ["python3 -m shop.export --format csv"])
        self.assertIn("some_criteria_not_checkable", result["flags"])
        self.assertIn("2. [ ] The export should feel faster. (not checkable as written)", result["checklist_markdown"])

    def test_example_json_ticket_matches_the_example_output(self):
        code, result = self.run_script("", "examples/ticket.json", "--root", ".")
        self.assertEqual(code, 0)
        expected = json.loads((PAYLOAD / "examples" / "ticket-output.json").read_text(encoding="utf-8"))
        self.assertEqual(result, expected)

    def test_known_wrong_vague_ticket_is_flagged_not_filled_in(self):
        code, result = self.run_script(VAGUE_TICKET)
        self.assertEqual((code, result["status"]), (1, "no_checkable_outcome"))
        self.assertIn("no_checkable_outcome", result["flags"])
        self.assertEqual(len(result["acceptance_criteria"]), 1)
        criterion = result["acceptance_criteria"][0]
        self.assertFalse(criterion["checkable"])
        self.assertEqual(criterion["source"], "modal_statement")
        self.assertEqual(criterion["vague_terms"], ["cleaner", "faster", "reliable"])

    def test_plain_text_label_lines(self):
        code, result = self.run_script(TEXT_TICKET)
        self.assertEqual(code, 0)
        self.assertEqual(result["title"], "Price parser rejects comma decimals")
        self.assertEqual(result["acceptance_criteria"][0]["text"], "parse_price returns 350.")
        self.assertIn("number", result["acceptance_criteria"][0]["signals"])
        self.assertEqual(result["reproduction_steps"][0]["text"], 'Call parse_price("3,50").')
        self.assertEqual(result["actual_behavior"], ["ValueError is raised."])

    def test_rich_text_json_document(self):
        code, result = self.run_script(RICH_TICKET)
        self.assertEqual(code, 0)
        self.assertEqual(result["title"], "Round totals to cents")
        texts = [item["text"] for item in result["acceptance_criteria"]]
        self.assertEqual(texts, ["Totals are rounded to 2 decimal places.", "The invoice PDF shows `12.35` for 12.345."])
        self.assertEqual(result["acceptance_criteria"][0]["field"], "description")
        self.assertEqual(result["commands"], ["pytest tests/test_totals.py"])

    def test_json_criteria_given_as_objects_and_steps_as_strings(self):
        code, result = self.run_script(LIST_TICKET)
        self.assertEqual(code, 0)
        checkable = [item["checkable"] for item in result["acceptance_criteria"]]
        self.assertEqual(checkable, [True, False])
        self.assertEqual([step["text"] for step in result["reproduction_steps"]], ["Export product 007.", "Open the file."])

    def test_scenario_is_one_criterion_and_commentary_is_left_out(self):
        code, result = self.run_script(SCENARIO_TICKET)
        self.assertEqual(code, 0)
        self.assertEqual(len(result["acceptance_criteria"]), 1)
        criterion = result["acceptance_criteria"][0]
        self.assertEqual(criterion["source"], "scenario")
        self.assertTrue(criterion["text"].startswith("Given a user with 3 failed logins When"))

    def test_checkboxes_outside_the_section_and_duplicates(self):
        code, result = self.run_script(CHECKBOX_TICKET)
        self.assertEqual(code, 0)
        criteria = result["acceptance_criteria"]
        self.assertEqual(len(criteria), 2)
        self.assertEqual(criteria[0]["source"], "checkbox")
        self.assertTrue(criteria[0]["already_checked"])
        self.assertFalse(criteria[1]["already_checked"])

    def test_form_fields_number_words_and_empty_placeholders(self):
        code, result = self.run_script(FORM_TICKET)
        self.assertEqual(code, 0)
        self.assertEqual(result["actual_behavior"], ["An error toast appears and the draft is lost."])
        self.assertEqual(result["expected_behavior"], [])
        criteria = {item["text"]: item for item in result["acceptance_criteria"]}
        self.assertEqual(sorted(criteria), ["The new one looks good.", "Titles keep two hundred characters or fewer."])
        self.assertTrue(criteria["Titles keep two hundred characters or fewer."]["checkable"])
        self.assertEqual(criteria["The new one looks good."]["signals"], [])
        self.assertFalse(criteria["The new one looks good."]["checkable"])
        self.assertNotIn("No response", json.dumps(result))

    def test_subject_line_is_the_title_of_a_text_ticket(self):
        code, result = self.run_script(EMAIL_TICKET)
        self.assertEqual(code, 0)
        self.assertEqual(result["title"], "Wrong VAT on invoices")
        self.assertEqual(result["acceptance_criteria"][0]["source"], "modal_statement")
        self.assertEqual(result["acceptance_criteria"][0]["text"], "It should be 19% but it shows 16%.")

    def test_setext_headings(self):
        code, result = self.run_script(SETEXT_TICKET)
        self.assertEqual(code, 0)
        self.assertEqual(result["title"], "Slow page")
        self.assertEqual(result["acceptance_criteria"][0]["source"], "acceptance_section")

    def test_issue_template_comments_are_removed(self):
        ticket = (f"## Describe the bug\n{OPEN_COMMENT} Tell us what happened. It must include logs. {CLOSE_COMMENT}\n"
                  f"The app crashes on start.\n\n## Expected behavior\n{OPEN_COMMENT} What should happen? {CLOSE_COMMENT}\n"
                  "The app opens the main window.\n")
        code, result = self.run_script(ticket)
        self.assertEqual(code, 0)
        self.assertEqual([item["text"] for item in result["acceptance_criteria"]], ["The app opens the main window."])
        self.assertNotIn("include logs", json.dumps(result))
        self.assertIn("bug_without_reproduction_steps", result["flags"])

    def test_named_files_are_checked_under_the_root(self):
        ticket = ("# Files\n\n- [ ] SKILL.md and scripts/extract_ticket_criteria.py stay in sync.\n"
                  "- [ ] extract_ticket_criteria.py, missing/file.py and ../escape.py are named.\n"
                  "See https://example.com/a.py and Node.js.\n")
        code, result = self.run_script(ticket, "--root", str(PAYLOAD))
        self.assertEqual(code, 0)
        files = {item["path"]: item for item in result["named_files"]}
        self.assertEqual(sorted(files), ["../escape.py", "SKILL.md", "extract_ticket_criteria.py", "missing/file.py",
                                         "scripts/extract_ticket_criteria.py"])
        self.assertTrue(files["SKILL.md"]["exists"])
        self.assertTrue(files["scripts/extract_ticket_criteria.py"]["exists"])
        self.assertFalse(files["extract_ticket_criteria.py"]["exists"])
        self.assertEqual(files["extract_ticket_criteria.py"]["matches"], ["scripts/extract_ticket_criteria.py"])
        self.assertIsNone(files["../escape.py"]["exists"])
        self.assertNotIn("matches", files["missing/file.py"])

    def test_no_file_check_leaves_existence_unknown(self):
        code, result = self.run_script(BUG_TICKET, "--no-file-check")
        self.assertEqual(code, 0)
        self.assertTrue(all(item["exists"] is None for item in result["named_files"]))

    def test_refused_inputs(self):
        cases = [(b"\xff\xfe not text", ()), (json.dumps([{"title": "a"}, {"title": "b"}]), ()),
                 ("", ("../ticket.md",)), ("x" * 100, ("--max-bytes", "10")), ('{"title": "a", "title": "b"}', ()),
                 ("   \n", ()), ("", (str(PAYLOAD / "SKILL.md"), "--root", str(PAYLOAD / "scripts")))]
        for data, arguments in cases:
            with self.subTest(arguments=arguments, data=data[:20]):
                code, result = self.run_script(data, *arguments)
                self.assertEqual((code, result["status"]), (2, "refused"))
                self.assertTrue(result["reason"])

    def test_skill_file_names_this_script(self):
        text = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/extract_ticket_criteria.py", text)
        self.assertIn("examples/ticket-output.json", text)


if __name__ == "__main__":
    unittest.main()
