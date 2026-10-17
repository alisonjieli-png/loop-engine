"""The library sites' pages say what they are, link where they must, and give a visitor something real.

Kind: development check over the pages `library_site_pages` renders from the packaged records and the typed site map. It
starts no server and opens no connection; the edge kit (`static_site_checks`) compares the same pages through the edge
Worker with the running service, and `tools/check_website_site_map.py` holds the hub pages to the site map.

Each rule below has known-wrong pages beside it that the rule must report:

- every hub, category and component page carries one h1, its own title and description, the canonical address the
  typed reader gives it, the shared-link tags, structured data that parses, and a Markdown version on a library site;
- an item reference names an item the library's catalogue data holds and links to that item's canonical page;
- a library site page sends sign-in and sign-up to the canonical hostname, every link of this website on it opens a page,
  and it carries at most one call to action, one dismissible bar and no modal dialog;
- every library site answers its own robots.txt, sitemap.xml, llms.txt and Markdown versions, and the component
  site map lists exactly the component pages a search engine may list;
- the words a visitor reads follow the public wording rules and write the price one way, and every page stays small.

    PYTHONPATH=src:tools python -m unittest tools/test_library_site_pages.py
"""
from __future__ import annotations

from functools import lru_cache
from html.parser import HTMLParser
import json
import re
import unittest
from xml.etree import ElementTree

from loop_engine.core.service_runtime import library_site_pages as pages
from loop_engine.core.service_runtime import library_site_records as records
from loop_engine.core.service_runtime import web_pages
from loop_engine.core.service_runtime.web_site_map import SECTION_ROOT_FILES, load_layout_standard

import build_library_sites as builder

NAME = "Baltor"
#: Every library site page measured under this on October 16, 2026, header and footer included; a page that grows past it
#: has stopped being a quick page.
PAGE_BYTES_MAX = 120_000
SIGN_IN = ("/get-started", "/login", "/signup", "/account", "/app")
SITEMAP_NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
WHOLE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


class _Page(HTMLParser):
    """The parts of a page these rules read."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1, self.meta, self.links, self.anchors, self.json_ld, self.text = 0, {}, [], [], [], []
        self.title, self.dialogs, self.bars, self.ctas = "", 0, 0, 0
        self._stack, self._title, self._json = [], False, None

    def _hidden(self):
        return any(skipped for _tag, skipped in self._stack)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in ("meta", "link", "img", "input", "br", "hr", "source"):
            self._stack.append((tag, tag in ("script", "style") or "data-listing-text" in attrs))
        self.h1 += tag == "h1"
        self._title = self._title or tag == "title"
        if tag == "meta" and (attrs.get("name") or attrs.get("property")):
            self.meta.setdefault(attrs.get("name") or attrs.get("property"), []).append(attrs.get("content", ""))
        if tag == "link":
            self.links.append(attrs)
        if tag == "a" and "href" in attrs:
            self.anchors.append(attrs["href"])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._json = []
        self.dialogs += tag == "dialog" or attrs.get("role") == "dialog" or "aria-modal" in attrs
        self.bars += "data-library-site-bar" in attrs
        self.ctas += "ls-cta" in (attrs.get("class") or "").split()

    def handle_endtag(self, tag):
        while self._stack:
            if self._stack.pop()[0] == tag:
                break
        if tag == "title":
            self._title = False
        if tag == "script" and self._json is not None:
            self.json_ld.append(json.loads("".join(self._json)))
            self._json = None

    def handle_data(self, data):
        if self._title:
            self.title += data
        if self._json is not None:
            self._json.append(data)
        elif not self._hidden():
            self.text.append(data)


def parse(body: bytes) -> _Page:
    page = _Page()
    page.feed(body.decode("utf-8"))
    return page


def serve(address, host=None):
    return pages.rendered(address, "GET", NAME, host)


@lru_cache(maxsize=None)
def _served_path(path: str) -> bool:
    from loop_engine.core.service_runtime import (catalogue_feed, dot_pages, gallery_page, library_page,
                                                  model_directory_pages, offering_guides, public_good_page,
                                                  red_team_page, status_pages, support_page)
    return bool(web_pages.served_asset(path, "GET", NAME) or pages.handles(path)
                or model_directory_pages.rendered_page(path, "GET", NAME)
                or public_good_page.rendered(path, "GET", NAME)
                or catalogue_feed.rendered_page(path, "GET", NAME)
                or dot_pages.rendered(path, "GET", NAME)
                or gallery_page.rendered(path, "GET", NAME)
                or library_page.handles(path) or offering_guides.handles(path) or path in catalogue_feed.FORMATS
                or red_team_page.rendered(path, "GET", NAME) or status_pages.rendered(path, "GET", NAME)
                or support_page.rendered(path, "GET", NAME))


def _served(address):
    """True when the transport serves the address: its page table, a page renderer, or a library feed it routes."""
    return _served_path(address.split("#", 1)[0].split("?", 1)[0])


def head_problems(body: bytes, canonical: str, markdown: bool) -> list:
    """What a page lacks of the head every library site page carries."""
    page, problems = parse(body), []
    if page.h1 != 1:
        problems.append(f"{page.h1} h1 headings")
    if not page.title.startswith(NAME + " | ") or len(page.title) <= len(NAME) + 3:
        problems.append("no title of its own")
    descriptions = page.meta.get("description") or []
    if len(descriptions) != 1 or not descriptions[0].strip() or len(descriptions[0]) > 160:
        problems.append("no single description of at most 160 characters")
    canonicals = [link.get("href") for link in page.links if link.get("rel") == "canonical"]
    if canonicals != [canonical]:
        problems.append(f"the canonical address is {canonicals}, not {canonical}")
    for name in ("og:title", "og:description", "og:url", "og:image", "twitter:card"):
        if not page.meta.get(name):
            problems.append(f"no {name}")
    if page.meta.get("og:url", [canonical])[0] != canonical:
        problems.append("og:url is not the canonical address")
    if not page.json_ld or not all(row.get("@context", "").endswith("schema.org") and row.get("url") == canonical
                                   for row in page.json_ld):
        problems.append("no structured data naming the canonical address")
    alternates = [link.get("href") for link in page.links if link.get("rel") == "alternate"
                  and link.get("type") == "text/markdown"]
    if markdown and len(alternates) != 1:
        problems.append("no Markdown version named")
    return problems


def link_problems(body: bytes, site_map, section: bool) -> list:
    """Links that keep sign-in on a library site, links of this website that open nothing, and more than one call
    to action or bar, or any dialog."""
    page, problems = parse(body), []
    for href in page.anchors:
        whole = WHOLE.match(href)
        address = site_map.address_of(href.split("#", 1)[0]) if whole else href.split("#", 1)[0]
        if section and not whole and address.split("?", 1)[0] in SIGN_IN:
            problems.append(f"{href} keeps sign-in or sign-up on the library site")
        if address and address.startswith("/") and not _served(address):
            problems.append(f"{href}: nothing serves it")
    if page.ctas > 1 or page.bars > 1 or page.dialogs:
        problems.append(f"{page.ctas} calls to action, {page.bars} bars and {page.dialogs} dialogs")
    return problems


def wording_problems(body: bytes) -> list:
    """The public wording rules and the one way to write the price, on the words a visitor reads."""
    text = " ".join(" ".join(parse(body).text).split())
    problems = [f"the {name} rule refuses it" for name in builder.refused_words(text, builder.wording_rules())]
    price = load_layout_standard().price
    for found in re.finditer(re.escape(price["marker"]), text):
        if text[found.start():found.start() + len(price["phrase"])] != price["phrase"]:
            problems.append(f"writes the price as {text[found.start():found.start() + 24]!r}")
    for phrase in price["refused_phrases"]:
        if phrase in text:
            problems.append(f"writes {phrase!r}")
    if re.search("[–—]", " ".join(text.split())):
        problems.append("an em or en dash in Baltor's own words")
    return problems


def every_page():
    """(address, kind, body) for every HTML page the module renders."""
    for address in pages.addresses():
        answer = serve(address)
        if answer is not None and answer[1] == web_pages.HTML_MEDIA_TYPE:
            yield address, pages._pages()[address][0], answer[0]


class LibrarySitePages(unittest.TestCase):
    def test_every_page_carries_its_own_head_and_canonical_address(self):
        site_map = web_pages.packaged_site_map()
        count = 0
        for address, kind, body in every_page():
            with self.subTest(address=address):
                self.assertEqual(head_problems(body, site_map.canonical_url(address), kind in ("hub", "category")), [])
                count += 1
        self.assertGreater(count, 200)

    def test_a_page_without_a_canonical_address_or_description_is_refused(self):
        site_map = web_pages.packaged_site_map()
        host = records.hosts_record()["hosts"][0]
        body = serve(host["address"])[0]
        canonical = site_map.canonical_url(host["address"])
        self.assertEqual(head_problems(body, canonical, True), [])
        for wrong in (re.sub(rb'<link rel="canonical"[^>]*>', b"", body), re.sub(rb'<meta name="description"[^>]*>', b"", body),
                      body.replace(canonical.encode(), b"https://baltor.ai/deterministic-skills"),
                      re.sub(rb'<link rel="alternate" type="text/markdown"[^>]*>', b"", body),
                      re.sub(rb'<script type="application/ld\+json">.*?</script>', b"", body, flags=re.S)):
            with self.subTest(change=len(wrong)):
                self.assertTrue(head_problems(wrong, canonical, True))

    def test_library_site_pages_are_canonical_on_their_own_hostname_and_components_on_baltor(self):
        site_map = web_pages.packaged_site_map()
        for host in records.hosts_record()["hosts"]:
            section = next(surface for surface in site_map.canonical_sections() if surface.address == host["address"])
            self.assertEqual(site_map.canonical_url(host["address"]), section.origin + "/")
            for category in host["categories"]:
                self.assertTrue(site_map.canonical_url(host["address"] + "/" + category["slug"]).startswith(section.origin + "/"))
        for item in records.items_record()["items"]:
            if not item["gallery"]:
                self.assertEqual(site_map.canonical_url(pages.component_address(item)),
                                 site_map.canonical_origin + pages.component_address(item))

    def test_links_go_to_served_pages_and_sign_up_leaves_for_the_canonical_hostname(self):
        site_map = web_pages.packaged_site_map()
        for address, kind, body in every_page():
            with self.subTest(address=address):
                self.assertEqual(link_problems(body, site_map, kind in ("hub", "category")), [])
                if kind in ("hub", "category"):
                    self.assertIn(site_map.canonical_origin + "/get-started", parse(body).anchors)

    def test_a_link_that_keeps_sign_up_on_the_library_site_or_opens_nothing_is_refused(self):
        site_map = web_pages.packaged_site_map()
        body = serve(records.hosts_record()["hosts"][1]["address"])[0]
        self.assertEqual(link_problems(body, site_map, True), [])
        for wrong in (body.replace(site_map.canonical_origin.encode() + b"/get-started", b"/get-started", 1),
                      body.replace(b"</main>", b'<a href="/nowhere-at-all">x</a></main>', 1),
                      body.replace(b"</main>", b'<dialog open>Subscribe</dialog></main>', 1),
                      body.replace(b'<section class="md-band og-closing ls-cta"', b'<section class="ls-cta"></section>'
                                   b'<section class="md-band og-closing ls-cta"', 1)):
            with self.subTest(change=len(wrong)):
                self.assertTrue(link_problems(wrong, site_map, True))

    def test_every_item_reference_is_an_item_of_the_catalogue_data_at_its_canonical_page(self):
        items = records.items_by_identity()
        for host in records.hosts_record()["hosts"]:
            for category in host["categories"]:
                body = serve(host["address"] + "/" + category["slug"])[0]
                page = parse(body)
                listed = [element["url"] for row in page.json_ld if row.get("@type") == "CollectionPage"
                          for element in row["mainEntity"]["itemListElement"]]
                expected = [pages.item_url(items[identity]) for identity in category["items"]]
                with self.subTest(category=category["slug"]):
                    self.assertEqual(listed, expected)
                    self.assertTrue(all(url in page.anchors for url in expected))

    def test_a_category_that_names_an_item_the_catalogue_data_lacks_cannot_render(self):
        hosts, items = json.loads(json.dumps(records.hosts_record())), json.loads(json.dumps(records.items_record()))
        hosts["hosts"][0]["categories"][0]["items"][0] = "library.supply.creative_originals.000000000000000000000000.0000000000000000"
        with self.assertRaises(records.LibrarySiteRecordError):
            records.parse_items(json.dumps(items), records.parse_hosts(json.dumps(hosts)))

    def test_every_page_follows_the_wording_rules_and_stays_small(self):
        for address, _kind, body in every_page():
            with self.subTest(address=address):
                self.assertEqual(wording_problems(body), [])
                self.assertLessEqual(len(body), PAGE_BYTES_MAX)

    def test_the_wording_check_refuses_a_known_wrong_page(self):
        body = serve(records.hosts_record()["hosts"][2]["address"])[0]
        for planted in (b"<p>Join the beta.</p>", b"<p>Pro, $49 per month.</p>", b"<p>Coming soon</p>",
                        "<p>Fast — and free.</p>".encode()):
            with self.subTest(planted=planted):
                self.assertTrue(wording_problems(body.replace(b"</main>", planted + b"</main>", 1)))

    def test_each_library_site_answers_its_own_root_files(self):
        site_map = web_pages.packaged_site_map()
        for surface in site_map.canonical_sections():
            host = next(host for host in records.hosts_record()["hosts"] if host["address"] == surface.address)
            robots = serve("/robots.txt", surface.hostname)[0].decode()
            self.assertIn(f"Sitemap: {surface.origin}/sitemap.xml", robots.splitlines())
            listed = [element.findtext(SITEMAP_NAMESPACE + "loc") for element in
                      ElementTree.fromstring(serve("/sitemap.xml", surface.hostname)[0]).findall(SITEMAP_NAMESPACE + "url")]
            self.assertEqual(listed, [site_map.canonical_url(surface.address)]
                             + [site_map.canonical_url(surface.address + "/" + category["slug"]) for category in host["categories"]])
            guide = serve("/llms.txt", surface.hostname)[0].decode()
            for category in host["categories"]:
                markdown = f"{surface.origin}{surface.address}/{category['slug']}.md"
                self.assertIn(markdown, guide)
                answer = serve(f"{surface.address}/{category['slug']}.md")
                self.assertEqual(answer[1], "text/markdown; charset=utf-8")
                self.assertTrue(pages.is_alternate(f"{surface.address}/{category['slug']}.md"))
            # The canonical hostname keeps the shared files; only the section's own hostname answers with its copies.
            self.assertIsNone(serve("/robots.txt", site_map.canonical_hostname))
            self.assertEqual(web_pages.served_asset("/robots.txt", "GET", NAME, site_map.canonical_hostname)[0],
                             web_pages.robots_text(site_map))
            self.assertIsNone(web_pages.served_asset("/robots.txt", "GET", NAME, surface.hostname))

    def test_the_component_site_map_lists_exactly_the_pages_a_search_engine_may_list(self):
        site_map = web_pages.packaged_site_map()
        listed = {element.findtext(SITEMAP_NAMESPACE + "loc") for element in
                  ElementTree.fromstring(serve(pages.COMPONENTS_SITEMAP)[0]).findall(SITEMAP_NAMESPACE + "url")}
        for item in records.items_record()["items"]:
            if item["gallery"]:
                continue
            url = site_map.canonical_url(pages.component_address(item))
            body = serve(pages.component_address(item))[0]
            noindex = b'<meta name="robots" content="noindex">' in body
            with self.subTest(item=item["slug"]):
                self.assertEqual(url in listed, pages.indexable(item))
                self.assertEqual(noindex, not pages.indexable(item))
        self.assertIn(f"Sitemap: {site_map.canonical_origin}{pages.COMPONENTS_SITEMAP}",
                      web_pages.robots_text(site_map).decode().splitlines())

    def test_a_hostname_root_shows_its_hub_and_the_hub_names_the_root(self):
        site_map = web_pages.packaged_site_map()
        for surface in site_map.canonical_sections():
            root, own = serve("/", surface.hostname), serve(surface.address, surface.hostname)
            self.assertEqual(root, own)
            self.assertIn(f'<meta name="baltor-root-address" content="{surface.address}">'.encode(), root[0])
            self.assertNotIn(b"baltor-root-address", serve(surface.address)[0])


if __name__ == "__main__":
    unittest.main()
