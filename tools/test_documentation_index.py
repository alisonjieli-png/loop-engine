"""Known-wrong controls for the documentation index, routes and exact built bodies."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from build_documentation_index import INDEX_FILE, DocumentationBuildError, load_index

ROOT = Path(__file__).resolve().parents[1]


class IndexContract(unittest.TestCase):
    def index(self):
        return json.loads((ROOT / INDEX_FILE).read_text())

    def read(self, content):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / INDEX_FILE
            path.parent.mkdir(parents=True)
            path.write_text(content if isinstance(content, str) else json.dumps(content))
            return load_index(root)

    def test_current_index_is_valid(self):
        self.assertEqual(len(self.read(self.index())["sections"]), 4)

    def test_unknown_version_and_fields_are_refused(self):
        for field, value in (("record_type", "website_documentation_index/v99"), ("extra", True)):
            with self.subTest(field=field):
                changed = self.index()
                changed[field] = value
                with self.assertRaises(DocumentationBuildError):
                    self.read(changed)

    def test_trailing_newline_identity_and_invalid_date_are_refused(self):
        for change in (lambda x: x["sections"][0].__setitem__("id", "start-here\n"),
                       lambda x: x.__setitem__("reviewed_at", "2026-02-31")):
            changed = self.index()
            change(changed)
            with self.assertRaises(DocumentationBuildError):
                self.read(changed)

    def test_duplicate_json_members_are_refused(self):
        text = json.dumps(self.index()).replace('"reviewed_at":', '"reviewed_at": "2026-09-22", "reviewed_at":')
        with self.assertRaises(DocumentationBuildError):
            self.read(text)

    def test_repository_paths_cannot_escape_or_name_another_tree(self):
        for path in ("/tmp/private.md", "../../../private.md", "docs/guides/../private.md", "secrets/private.md"):
            with self.subTest(path=path):
                changed = self.index()
                changed["sections"][0]["pages"][1]["repository_path"] = path
                with self.assertRaises(DocumentationBuildError):
                    self.read(changed)

    def test_alias_objects_are_typed_refusals(self):
        changed = self.index()
        changed["sections"][0]["pages"][0]["aliases"] = [{}]
        with self.assertRaises(DocumentationBuildError):
            self.read(changed)

    def test_builder_rejects_shapes_the_browser_cannot_render(self):
        changes = [lambda x: x["sections"][0]["pages"][0].__setitem__("address", "/security"),
                   lambda x: x["sections"][0]["pages"][0].__setitem__("aliases", ["/docs/nested/path"]),
                   lambda x: x["sections"][0]["pages"][0].__setitem__("repository_path", None),
                   lambda x: x["sections"][0]["pages"][0].__setitem__("title", "x" * 201)]
        for position, change in enumerate(changes):
            with self.subTest(position=position):
                changed = self.index()
                change(changed)
                with self.assertRaises(DocumentationBuildError):
                    self.read(changed)

    def test_foreign_body_and_duplicate_page_are_refused(self):
        for change in (lambda x: x["sections"][0]["pages"][1].__setitem__("body", "https://foreign.invalid/body"),
                       lambda x: x["sections"][0]["pages"].append(copy.deepcopy(x["sections"][0]["pages"][0]))):
            changed = self.index()
            change(changed)
            with self.assertRaises(DocumentationBuildError):
                self.read(changed)

class DocumentationAgreement(unittest.TestCase):
    """An isolated mirror changes only the named files; source facts stay real."""
    def report(self, overrides):
        from check_documentation_index import check
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            real = {"", "docs", "docs/guides", "src", "src/loop_engine", "src/loop_engine/core",
                    "src/loop_engine/core/service_runtime", "src/loop_engine/core/service_runtime/web_assets",
                    "src/loop_engine/core/service_runtime/web_assets/docs"}
            for relative in overrides:
                real.update(str(p) for p in Path(relative).parents if str(p) != ".")
            def mirror(relative):
                (target / relative).mkdir(exist_ok=True)
                for path in (ROOT / relative).iterdir():
                    child = str(Path(relative) / path.name)
                    if child in overrides:
                        continue
                    if child in real:
                        mirror(child)
                    else:
                        (target / child).symlink_to(path)
            mirror("")
            for relative, text in overrides.items():
                if text is not None:
                    (target / relative).write_text(text)
            return check(target)

    def test_complete_current_docs_pass(self):
        result = self.report({})
        self.assertTrue(result["passed"], result["findings"])
        self.assertEqual(result["pages"], 7)

    def test_removed_guards_have_discriminating_known_wrong_cases(self):
        from build_documentation_index import BODY_DIRECTORY, PAGE_TABLE_MODULE
        guide = "docs/guides/service-troubleshooting.md"
        cases = [
            (guide, (ROOT / guide).read_text() + "\nChanged page.\n", "stale_pages"),
            (BODY_DIRECTORY + "/orphan.html", "<p>Unlisted</p>", "stale_pages"),
            (PAGE_TABLE_MODULE, (ROOT / PAGE_TABLE_MODULE).read_text().replace('"/docs/what-baltor-is"', '"/docs/forgotten"'), "route"),
            ("docs/guides/README.md", (ROOT / "docs/guides/README.md").read_text().replace("| [Your account]", "| [Not listed](service-absent.md) | Missing |\n| [Your account]"), "customer_coverage"),
            ("src/loop_engine/core/service_runtime/web_assets/service.js", (ROOT / "src/loop_engine/core/service_runtime/web_assets/service.js").read_text().replace('"/docs/getting-set-up":"setup"', '"/docs/getting-set-up":"home"'), "alias_view"),
            (INDEX_FILE, (ROOT / INDEX_FILE).read_text().replace('"title": "Your account"', '"title": "Private beta account"'), "terminology"),
            (guide, (ROOT / guide).read_text().replace("| `item_unavailable` | 404 |", "| `item_unavailable` | 403 |"), "refusal_status"),
            (guide, (ROOT / guide).read_text() + "\nSee [absent](service-absent.md).\n", "build"),
        ]
        for relative, text, expected in cases:
            with self.subTest(expected=expected):
                result = self.report({relative: text})
                self.assertIn(expected, {row["kind"] for row in result["findings"]})
                self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
