"""The public counter separates distinct payloads from packages and repeated placements."""
import unittest

from loop_engine.core.service_runtime import web_pages


class LibraryFileCounterTests(unittest.TestCase):
    def test_distinct_files_and_packages_come_from_one_population(self):
        page = b'<b data-library-file-count>Not measured</b><span data-library-count>43</span>'
        population = {"record_type": "catalogue_file_population/v1", "packages": 20,
                      "distinct_files": 1010, "file_placements": 1500, "complete": True}
        shown = web_pages.with_file_population(page, population)
        self.assertIn(b"data-library-file-count>1,010<", shown)
        self.assertIn(b"data-library-count>20<", shown)
        self.assertNotIn(b"1,500", shown)

    def test_incomplete_unknown_or_invalid_population_never_claims_a_file_total(self):
        page = b'<b data-library-file-count>99</b><span data-library-count>43</span>'
        good = {"record_type": "catalogue_file_population/v1", "packages": 20,
                "distinct_files": 1010, "complete": True}
        for value in (None, {}, dict(good, complete=False), dict(good, distinct_files=True),
                      dict(good, record_type="catalogue_file_population/v999")):
            with self.subTest(value=value):
                self.assertIn(b"data-library-file-count>Not measured<",
                              web_pages.with_file_population(page, value))

    def test_server_render_does_not_require_javascript_for_file_count(self):
        population = {"record_type": "catalogue_file_population/v1", "packages": 20,
                      "distinct_files": 1010, "complete": True}
        page, _kind = web_pages.served_asset("/", "GET", "Baltor", library_population=lambda: population)
        self.assertIn(b"data-library-file-count>1,010<", page)
        self.assertIn(b"data-library-count>20<", page)

    def test_empty_catalogue_does_not_keep_the_packaged_seed_count(self):
        page = b'<b data-library-file-count>99</b><span data-library-count>43</span>'
        shown = web_pages.with_file_population(page, {"record_type": "catalogue_file_population/v1",
            "packages": 0, "distinct_files": 0, "complete": True})
        self.assertIn(b"data-library-file-count>0<", shown)
        self.assertIn(b"data-library-count>0<", shown)


if __name__ == "__main__":
    unittest.main()
