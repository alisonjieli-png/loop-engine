"""The served homepage shows the count of packages the service serves now, not the count it was packaged with.

The homepage marks its library count with `data-library-count`. The packaged page holds 43, the count of the first
release, and until September 27, 2026 the service sent it unchanged: only the page script wrote the live count, after
asking the service. A shared-link preview, a crawler and a reader without the script therefore read 43 while the
service served 12,191. The service now writes the count of the active catalogue into the page as it serves it
(src/loop_engine/core/service_runtime/web_pages.py, called by the transport in http.py). Each rule has a known-wrong
control. Nothing here reaches the network: the end-to-end rule runs the service on loopback over a temporary database.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime import web_pages  # noqa: E402

PACKAGED_PAGE = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets" / "index.html"


class _CountReader(HTMLParser):
    """The text of every element that carries the data-library-count attribute."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth, self.shown, self.current = 0, [], None

    def handle_starttag(self, tag, attrs):
        if self.current is not None:
            self.depth += 1
        elif "data-library-count" in dict(attrs):
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


def shown_counts(body):
    reader = _CountReader()
    reader.feed(body.decode("utf-8") if isinstance(body, bytes) else body)
    return reader.shown


class WrittenCountTests(unittest.TestCase):
    def setUp(self):
        self.page = PACKAGED_PAGE.read_bytes()
        self.packaged = shown_counts(self.page)

    def test_the_packaged_page_marks_one_count(self):
        self.assertEqual(len(self.packaged), 1, self.packaged)
        self.assertTrue(self.packaged[0].replace(",", "").isdigit(), self.packaged)

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
                                                  library_count=lambda: asked.append(1) or 12191)
        self.assertEqual(media_type, web_pages.HTML_MEDIA_TYPE)
        self.assertEqual(shown_counts(body), ["12,191"])
        self.assertEqual(len(asked), 1)

    def test_known_wrong_a_page_served_without_the_count_keeps_the_packaged_number(self):
        body, _media_type = web_pages.served_asset("/", "GET", "Fixture Service")
        self.assertEqual(shown_counts(body), shown_counts(PACKAGED_PAGE.read_bytes()))
        self.assertNotEqual(shown_counts(body), ["12,191"])

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

    def test_the_page_and_the_capabilities_record_state_the_same_count(self):
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
        self.assertIsInstance(served, int)
        # The fixture approves three of its four items; the packaged page says 43, so the two cannot agree by chance.
        self.assertEqual(served, 3)
        self.assertNotIn(f"{served:,}", shown_counts(PACKAGED_PAGE.read_bytes()))
        for address, page in pages.items():
            with self.subTest(address=address):
                self.assertEqual(page.status_code, 200)
                self.assertEqual(shown_counts(page.text), [f"{served:,}"])


if __name__ == "__main__":
    unittest.main()
