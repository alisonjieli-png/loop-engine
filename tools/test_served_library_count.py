"""The homepage serves a measured distinct-file count without a package headline.

The generic technical package-counter projection remains supported. The
public homepage uses the versioned file population instead. No JavaScript
or external provider is needed; end-to-end checks use an owned loopback fixture.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime import web_pages  # noqa: E402

PACKAGED_PAGE = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets" / "index.html"


class _CountReader(HTMLParser):
    """The text of every element that carries the data-library-count attribute."""

    def __init__(self, mark="data-library-count"):
        super().__init__(convert_charrefs=True)
        self.mark = mark
        self.depth, self.shown, self.current = 0, [], None

    def handle_starttag(self, tag, attrs):
        if self.current is not None:
            self.depth += 1
        elif self.mark in dict(attrs):
            self.current, self.depth = "", 0

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if self.depth:
            self.depth -= 1
            return
        self.shown.append(self.current.strip())
        self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current += data


def shown_counts(body, mark="data-library-count"):
    reader = _CountReader(mark)
    reader.feed(body.decode("utf-8") if isinstance(body, bytes) else body)
    return reader.shown


class WrittenCountTests(unittest.TestCase):
    def setUp(self):
        self.page = b'<p><span data-library-count>43</span></p>'
        self.packaged = shown_counts(self.page)

    def test_the_generic_counter_marks_one_count_but_homepage_uses_files(self):
        self.assertEqual(len(self.packaged), 1, self.packaged)
        self.assertTrue(self.packaged[0].replace(",", "").isdigit(), self.packaged)
        self.assertEqual(shown_counts(PACKAGED_PAGE.read_bytes()), [])
        self.assertEqual(shown_counts(PACKAGED_PAGE.read_bytes(), "data-library-file-count"), ["Not measured"])

    def test_the_count_is_written_with_the_grouping_the_page_script_uses(self):
        self.assertEqual(shown_counts(web_pages.with_library_count(self.page, 12191)), ["12,191"])
        self.assertEqual(shown_counts(web_pages.with_library_count(self.page, 7)), ["7"])
        page = b'<p><span class="n" data-library-count>43</span> and <b data-library-count="">9</b></p>'
        self.assertEqual(shown_counts(web_pages.with_library_count(page, 1234567)), ["1,234,567", "1,234,567"])

    def test_a_count_that_is_not_a_whole_number_above_zero_leaves_the_packaged_number(self):
        for count in (None, 0, -3, True, "12191", 12.5):
            with self.subTest(count=count):
                self.assertEqual(web_pages.with_library_count(self.page, count), self.page)

    def test_only_the_marked_elements_change(self):
        page = (b'<table data-library-counts><td>43</td></table><span data-library-count-note>43</span>'
                b'<span data-library-count>43</span>')
        written = web_pages.with_library_count(page, 12191)
        self.assertEqual(written, page.replace(b"<span data-library-count>43<", b"<span data-library-count>12,191<"))


class ServedPageTests(unittest.TestCase):
    def test_the_served_homepage_shows_the_count_served_now(self):
        asked = []
        body, media_type = web_pages.served_asset("/", "GET", "Fixture Service",
            library_count=lambda: self.fail("no package-counter request for the file-only homepage"),
            library_population=lambda: asked.append(1) or {"record_type": "catalogue_file_population/v1", "complete": True,
                                                         "packages": 17, "distinct_files": 12191})
        self.assertEqual(media_type, web_pages.HTML_MEDIA_TYPE)
        self.assertEqual(shown_counts(body, "data-library-file-count"), ["12,191"])
        self.assertEqual(shown_counts(body), [])
        self.assertEqual(len(asked), 1)

    def test_known_wrong_a_page_served_without_the_count_keeps_the_packaged_number(self):
        body, _media_type = web_pages.served_asset("/", "GET", "Fixture Service")
        self.assertEqual(shown_counts(body, "data-library-file-count"), ["Not measured"])
        self.assertNotEqual(shown_counts(body, "data-library-file-count"), ["12,191"])

    def test_the_count_is_asked_only_for_a_page_that_shows_it(self):
        asked = []
        count = lambda: asked.append(1) or 12191  # noqa: E731
        script = web_pages.served_asset("/assets/service.js", "GET", "Fixture Service", library_count=count)
        self.assertIsNotNone(script)
        pages = [path for path, (name, media) in web_pages.WEB_ASSETS.items()
                 if media == web_pages.HTML_MEDIA_TYPE and web_pages.LIBRARY_COUNT_MARK not in
                 web_pages.read_packaged_asset(name)]
        self.assertTrue(pages)
        for path in pages:
            web_pages.served_asset(path, "GET", "Fixture Service", library_count=count)
        self.assertEqual(asked, [])


class LoopbackServiceTests(unittest.TestCase):
    """The service writes the count its own capabilities record reports, on every address that shows the homepage."""

    def test_the_page_and_the_capabilities_record_agree_on_files_or_unknown(self):
        import httpx
        from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
        with tempfile.TemporaryDirectory() as folder:
            fixture = HttpDomainFixture(Path(folder))
            with running_http(fixture) as (base, service):
                served = service.served_item_count()
                capabilities = httpx.get(base + "/api/v1/capabilities", trust_env=False, timeout=5)
                pages = {address: httpx.get(base + address, trust_env=False, timeout=5) for address in ("/", "/app")}
        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(capabilities.json()["result"]["library"]["served_items"], served)
        population = capabilities.json()["result"]["library"]["file_population"]
        self.assertIsInstance(served, int)
        # The fixture approves three of its four items; the packaged page says 43, so the two cannot agree by chance.
        self.assertEqual(served, 3)
        expected = f"{population['distinct_files']:,}" if population["complete"] is True else "Not measured"
        for address, page in pages.items():
            with self.subTest(address=address):
                self.assertEqual(page.status_code, 200)
                self.assertEqual(shown_counts(page.text), [])
                self.assertEqual(shown_counts(page.text, "data-library-file-count"), [expected])


class FilePopulationTests(unittest.TestCase):
    def setUp(self):
        from loop_engine.core.harness_intelligence import HarnessIntelligenceCatalogue, HarnessIntelligenceItem
        from loop_engine.core.provisioning_server import ProvisioningQualification, ProvisioningQualificationResolver
        from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile, sha256_hex
        from loop_engine.core.service_runtime.catalogue_serving import CatalogueView

        def entry(name, body):
            return CataloguePackageFile(name, sha256_hex(body), len(body), "text/plain", "skill_reference")

        common = entry("references/shared.txt", b"shared")
        self.packages = {"alpha": CataloguePackage((common, entry("a.txt", b"alpha"))),
                         "beta": CataloguePackage((common, entry("b.txt", b"beta"))),
                         "candidate": CataloguePackage((entry("c.txt", b"candidate"),))}
        catalogue = HarnessIntelligenceCatalogue()
        for identity, package in self.packages.items():
            catalogue.register(HarnessIntelligenceItem(identity=identity, kind="skill", purpose=identity,
                digest=package.served_digest, size_bytes=package.served_size, source_layer="harness_local",
                source_ref="fixture:" + identity, license_name="MIT"))
        resolver = ProvisioningQualificationResolver("fixture:population", lambda binding:
            ProvisioningQualification(binding, "unknown", "host_attested") if binding.identity == "candidate" else
            ProvisioningQualification(binding, "approved", "host_attested", "fixture:review", "verified"))
        self.view = CatalogueView(catalogue, resolver, lambda _item: self.fail("counting must not read bodies"),
                                  packages=self.packages)

    def test_counts_distinct_files_separately_from_packages_and_placements(self):
        result = self.view.file_population()
        self.assertEqual(result["packages"], 2)
        self.assertEqual(result["file_placements"], 4)
        self.assertEqual(result["distinct_files"], 3)
        self.assertEqual(result["distinct_file_bytes"], 15)
        self.assertTrue(result["complete"])
        # Package inventory documents and the unapproved candidate are not counted as delivered files.
        self.assertEqual(result["duplicate_file_placements"], 1)

    def test_public_library_renders_the_measured_distinct_files_and_packages(self):
        from loop_engine.core.service_runtime.library_page import library_body
        html = library_body(replace(self.view, body_reader=lambda _item: "Allowed fixture sample"))
        self.assertIn('<span class="lib-total">3</span> <span class="lib-title-words">files, ready for your harness', html)
        self.assertIn("3 distinct files. Identical shared files are counted once.", html)
        self.assertIn("Technical grouping by kind", html)
        self.assertIn('<th scope="col" class="lib-num">Packages</th>', html)
        # Four placements share one exact file; the unapproved candidate stays out.
        changed = self.view.without({("beta", self.packages["beta"].served_digest)}, state_revision=1)
        html = library_body(replace(changed, body_reader=lambda _item: "Allowed fixture sample"))
        self.assertIn("2 distinct files. Identical shared files are counted once.", html)

    def test_withdrawal_removes_files_not_used_by_another_approved_package(self):
        self.view.file_population()
        updated = self.view.without({("beta", self.packages["beta"].served_digest)}, state_revision=1)
        self.assertEqual(updated.file_population()["distinct_files"], 2)
        self.assertEqual(updated.file_population()["packages"], 1)

    def test_missing_manifest_is_unknown_not_an_invented_file(self):
        result = replace(self.view, packages={"alpha": self.packages["alpha"]}).file_population()
        self.assertFalse(result["complete"])
        self.assertEqual(result["packages_without_file_manifest"], 1)
        self.assertIsNone(result["distinct_files"])
        self.assertEqual(result["observed_distinct_files"], 2)


if __name__ == "__main__":
    unittest.main()
