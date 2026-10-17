"""The website serves exactly the pages, header, footer and sections that its site map names.

Kind: development check over packaged files. It reads the site map record through its typed reader
(`loop_engine.core.service_runtime.web_site_map`), the pages that `web_pages.served_asset` serves for each
address, and the dated inventories under `artifacts/website-audit-*`. It starts no server, opens no
connection and needs no credential.

On September 23, 2026 a redesign of the website dropped header links, footer links and whole pages, and no
check noticed. The owner asked for checks that catch missing pages, lost pages and regressions. Each rule
below refuses one way to lose something:

- a page of the site map that the served address table does not serve, or whose view does not show
  exactly one h1;
- a header entry, for a visitor who is signed out, a signed-in person or an operator, that is missing,
  extra, out of order or labelled differently from the site map;
- a footer group or link that is missing, extra or out of order, and a base row without the mark, the
  operator, the operator's postal line or the year;
- an internal address, or a part of a page, that the served pages name and nothing serves;
- a served page that the site map does not name, a page that no link reaches without a written reason,
  and a page the site map calls unlinked that something links to;
- a page, header link, footer link or section that a dated inventory recorded and that is gone without a
  dated removal row in the site map;
- a customer page that writes the price any way but "$49 a month".

Every rule has known-wrong sites beside it, built from a small fixture site that passes every rule, and a
mutant control that removes the rule and requires its named check to fail.

This module holds the rules, their known-wrong cases and their mutant controls, which pass on their own and
run with the other tools tests. The comparison of the served website with the site map is
`tools/check_website_site_map.py`. On 243a8811, live as Fly release 20, it failed until the pages that the
target site map of September 23, 2026 restores were served; its failing output is saved as
`artifacts/website-audit-2026-09-23/site-map-check-on-main-243a8811.txt`. Roadmap step S-6.67 served them on
September 24, 2026 and the check joined the continuous integration list. Three of its rules were corrected
then, each keeping a known-wrong case: a packaged file's content version (`?v=` and its SHA-256) is not part of
its address, a documentation body under /assets/ is part of a page rather than a page, and a page that only
earlier links reach is a way in, so what it links to is reached. Do not weaken a rule to make it pass:
change the pages, or change the site map together with a dated removal row.

Run the rules alone:

    PYTHONPATH=src:tools python -m unittest tools/test_website_site_map.py

Write the inventory of the served website, for a new release:

    PYTHONPATH=src python tools/test_website_site_map.py --write-inventory NEW_PATH --release NAME --revision SHA
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Callable
import unittest
from unittest import mock

from loop_engine.core.service_runtime import web_pages, web_site_map
from loop_engine.core.service_runtime.web_site_map import (
    HEADER_STATES, SiteMap, SiteMapError, layout_standard_from_record, load_layout_standard, load_site_map,
    site_map_from_record,
)

ROOT = Path(__file__).resolve().parents[1]
#: Every dated inventory of the served website. A release that changes the website adds its own.
INVENTORY_GLOB = "artifacts/website-audit-*/site-inventory-*.json"
INVENTORY_RECORD_TYPE = "website_site_inventory/v1"
KNOWN_WRONG_OUTPUT = "artifacts/website-audit-2026-09-23/site-map-check-on-main-243a8811.txt"
HTML = web_pages.HTML_MEDIA_TYPE
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
YEAR = re.compile(r"\b20[0-9]{2}\b")
#: The content version the service appends to a packaged file's address in a served page, since September 23, 2026.
#: Only this exact query is read as the same address; any other query is a different address.
ASSET_VERSION = re.compile(r"\?v=[0-9a-f]{64}$")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


class Element:
    """One element of a parsed page, with its text and its elements in order."""

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children = tag, attrs, parent, []

    def walk(self):
        yield self
        for item in self.children:
            if isinstance(item, Element):
                yield from item.walk()

    def text(self):
        parts = []

        def gather(node):
            for item in node.children:
                if isinstance(item, Element):
                    gather(item)
                else:
                    parts.append(item)
        gather(self)
        return " ".join(" ".join(parts).split())

    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def ancestors(self, stop=None):
        node = self.parent
        while node is not None and node is not stop:
            yield node
            node = node.parent

    def label(self):
        """The visible words of an entry, as a reader sees them."""
        return re.sub(r"\s+([↗→])?$", "", self.text()).strip()


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("#document", {}, None)
        self.open = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs), self.open[-1])
        self.open[-1].children.append(node)
        if tag not in VOID:
            self.open.append(node)

    def handle_startendtag(self, tag, attrs):
        self.open[-1].children.append(Element(tag, dict(attrs), self.open[-1]))

    def handle_endtag(self, tag):
        for index in range(len(self.open) - 1, 0, -1):
            if self.open[index].tag == tag:
                del self.open[index:]
                return

    def handle_data(self, data):
        self.open[-1].children.append(data)


def parse(page):
    builder = _TreeBuilder()
    builder.feed(page)
    builder.close()
    return builder.root


def first(node, test):
    return next((item for item in node.walk() if test(item)), None)


def unversioned(value):
    """An address as the site map names it: a packaged file's content version is not part of its address, whether the
    file is named from the root or by its whole address."""
    if not isinstance(value, str):
        return value
    path = value if value.startswith("/") else "/" + value.split("://", 1)[-1].partition("/")[2]
    return ASSET_VERSION.sub("", value) if path.startswith("/assets/") else value


@dataclass
class Site:
    """What a rule reads: the site map, the served pages, the served address table and the inventories."""

    site_map: SiteMap
    serve: Callable
    table: tuple
    inventories: tuple
    layout: object = None
    parsed: dict = field(default_factory=dict)
    fragment_bodies: dict = field(default_factory=dict)

    def answer(self, address):
        return self.serve(address)

    def document(self, address):
        answer = self.serve(address)
        if answer is None or answer[1] != HTML:
            return None
        if answer[0] not in self.parsed:
            self.parsed[answer[0]] = parse(answer[0])
        return self.parsed[answer[0]]

    def page_documents(self):
        """Each distinct served page among the site map's addresses, with the addresses that serve it."""
        seen = {}
        for page in self.site_map.pages:
            document = self.document(page.address)
            if document is not None:
                seen.setdefault(id(document), (document, []))[1].append(page.address)
        return list(seen.values())

    def fragment_documents(self, address):
        """The page shell and the exact documentation body its client loads."""
        targets = (address, self.fragment_bodies.get(address))
        return tuple(document for target in targets if target is not None
                     if (document := self.document(target)) is not None)


def view_of(document, view):
    return first(document, lambda item: item.attrs.get("data-view") == view) if document is not None else None


def shown_headings(view, tag):
    """Headings of a view that are not inside a hidden alternative of that view."""
    return [item for item in view.walk() if item.tag == tag
            and not any("hidden" in node.attrs for node in [item, *item.ancestors(view)])]


def header_entries(document, state):
    """The header entries a person in one state sees, read from the markup's state markers.

    `data-signed-out` shows an entry to a visitor; `data-signed-in` to a signed-in person and an operator;
    `data-operator`, or `hidden` with neither marker, to an operator alone; no marker to everyone.
    """
    header = first(document, lambda item: item.tag == "header")
    if header is None:
        return None
    # A button that shows or hides the header's own navigation, the phone menu button, folds the entries; it is not one of them.
    folded = {item.attrs.get("id") for item in header.walk() if item.tag == "nav" and item.attrs.get("id")}
    entries = []
    for item in header.walk():
        if not (item.tag == "button" or (item.tag == "a" and "href" in item.attrs)):
            continue
        if item.tag == "button" and item.attrs.get("aria-controls") in folded:
            continue
        chain = [item, *item.ancestors(header)]
        marked = lambda name: any(name in node.attrs for node in chain)
        if marked("data-signed-out"):
            states = {"signed_out"}
        elif marked("data-signed-in"):
            states = {"signed_in", "operator"}
        elif marked("data-operator") or marked("hidden"):
            states = {"operator"}
        else:
            states = set(HEADER_STATES)
        if state in states:
            role = ("brand" if "brand" in item.classes() else "primary" if "primary" in item.classes()
                    else "button" if item.tag == "button" else "link")
            entries.append((role, item.label(), item.attrs.get("href")))
    return entries


def entry_key(role, label, href):
    return href if href else "button:" + label


def order_problems(where, expected, actual):
    """Missing, extra and out of order entries, compared by address, then any changed label or role."""
    wanted, found = [entry_key(*entry) for entry in expected], [entry_key(*entry) for entry in actual]
    problems = []
    missing = [key for key in wanted if key not in found]
    extra = [key for key in found if key not in wanted]
    if missing:
        problems.append(f"{where}: missing {missing}")
    if extra:
        problems.append(f"{where}: extra {extra}")
    shared_wanted, shared_found = [key for key in wanted if key in found], [key for key in found if key in wanted]
    if shared_wanted != shared_found:
        problems.append(f"{where}: out of order; the site map has {shared_wanted} and the page has {shared_found}")
    written = {entry_key(*entry): entry for entry in actual}
    for entry in expected:
        shown = written.get(entry_key(*entry))
        if shown and (shown[0], shown[1]) != (entry[0], entry[1]):
            problems.append(f"{where}: {entry_key(*entry)} is a {shown[0]} labelled {shown[1]!r}, "
                            f"and the site map has a {entry[0]} labelled {entry[1]!r}")
    return problems


def pages_are_served_with_one_h1(site):
    problems = []
    for page in site.site_map.pages:
        answer = site.answer(page.address)
        if answer is None:
            problems.append(f"{page.address}: the served address table does not serve it")
            continue
        if answer[1] != HTML:
            problems.append(f"{page.address}: served as {answer[1]}, not as a page")
            continue
        view = view_of(site.document(page.address), page.view)
        if view is None:
            problems.append(f"{page.address}: the served page has no view {page.view!r}")
            continue
        count = len(shown_headings(view, "h1"))
        if count != 1:
            problems.append(f"{page.address}: the view {page.view!r} shows {count} h1 headings; a page shows exactly one")
    return problems


def chrome_href(site_map, addresses, href):
    """The address a page's header or footer must name for a site map entry.

    A page of a canonical section names every page of the canonical hostname by its whole address, because a link from
    the root would keep the reader on the section's hostname, where sign-in and sign-up do not run. A packaged file under
    /assets/ is the same on every hostname, so it stays named from the root. Every other page names everything from the
    root, as the site map writes it.
    """
    if (href and href.startswith("/") and not href.startswith("/assets/") and addresses
            and all(site_map.section_of(address) for address in addresses)):
        return site_map.canonical_origin + href
    return href


def header_matches_the_site_map(site):
    problems = []
    for document, addresses in site.page_documents():
        for state in HEADER_STATES:
            expected = [(entry.role, entry.label, chrome_href(site.site_map, addresses, entry.href))
                        for entry in site.site_map.header[state]]
            actual = header_entries(document, state)
            where = f"header, {state}, on {addresses[0]}"
            problems.extend([f"{where}: the page has no header"] if actual is None else order_problems(where, expected, actual))
    return problems


def _footer_links(nav):
    return [("link", item.label(), unversioned(item.attrs["href"])) for item in nav.walk() if item.tag == "a" and "href" in item.attrs]


def footer_matches_the_site_map(site):
    problems, site_map = [], site.site_map
    base = site_map.footer_base_row
    for document, addresses in site.page_documents():
        where = f"footer on {addresses[0]}"
        footer = first(document, lambda item: item.tag == "footer")
        if footer is None:
            problems.append(f"{where}: the page has no footer")
            continue
        navs = [item for item in footer.walk() if item.tag == "nav"]
        shown = [nav for nav in navs if "hidden" not in nav.attrs]
        names = [nav.attrs.get("aria-label", "") for nav in shown]
        wanted = [group.name for group in site_map.footer_groups]
        problems.extend(order_problems(where + " groups", [("group", name, name) for name in wanted],
                                       [("group", name, name) for name in names]))
        for group in site_map.footer_groups:
            nav = next((item for item in shown if item.attrs.get("aria-label") == group.name), None)
            if nav is None:
                continue
            heading = first(nav, lambda item: "footer-heading" in item.classes())
            if heading is not None and heading.text() != group.name:
                problems.append(f"{where}: the group {group.name!r} is headed {heading.text()!r}")
            expected = [(link.role, link.label, chrome_href(site_map, addresses, link.href)) for link in group.links]
            problems.extend(order_problems(f"{where}, group {group.name!r}", expected, _footer_links(nav)))
        outside = [item for item in footer.walk() if item.tag == "a" and "href" in item.attrs
                   and not any(node.tag == "nav" for node in item.ancestors(footer))]
        brands = [item for item in outside if "brand" in item.classes()]
        if [item.attrs["href"] for item in brands] != [chrome_href(site_map, addresses, site_map.footer_brand)]:
            problems.append(f"{where}: the footer brand links to {[item.attrs['href'] for item in brands]}")
        extra = [item.attrs["href"] for item in outside if "brand" not in item.classes()]
        if extra:
            problems.append(f"{where}: links outside the four groups {extra}")
        rows = [item for item in footer.walk() if item is not footer and base.operator in item.text()
                and base.operator_line in item.text() and not any(node.tag == "nav" for node in item.ancestors(footer))]
        # The base row is the smallest element that holds both, so a wrapper around the whole footer is not taken for it.
        row = min(rows, key=lambda item: sum(1 for _node in item.walk()), default=None)
        if row is None:
            problems.append(f"{where}: no base row names {base.operator!r} and {base.operator_line!r}")
        else:
            if not any(item.tag == "img" and unversioned(item.attrs.get("src")) == base.mark for item in row.walk()):
                problems.append(f"{where}: the base row {row.text()!r} does not show the mark {base.mark}")
            if not YEAR.search(row.text()):
                problems.append(f"{where}: the base row {row.text()!r} does not name the year")
    privacy = site_map.page("/privacy")
    if privacy is not None:
        view = view_of(site.document("/privacy"), privacy.view)
        if view is not None and base.operator_line not in view.text():
            problems.append(f"the privacy notice does not publish the operator line {base.operator_line!r} of the base row")
    return problems


def _addresses(document):
    for item in document.walk():
        if any(node.tag == "template" for node in item.ancestors()):
            continue
        for name in ("href", "src"):
            value = item.attrs.get(name)
            if value is not None and item.tag in ("a", "area", "link", "script", "img", "source", "iframe"):
                yield item, name, value


def internal_addresses_are_served(site):
    problems = []
    for document, addresses in site.page_documents():
        ids = {item.attrs.get("id") for item in document.walk()}
        for item, name, value in _addresses(document):
            where = f"<{item.tag} {name}={value!r}> on {addresses[0]}"
            if not value.strip():
                problems.append(f"{where}: an empty address")
                continue
            path, _, fragment = value.partition("#")
            if EXTERNAL.match(value):
                # A whole address of this website, such as a canonical section's link to the canonical hostname, is
                # checked like an address from the root; any other site's address is not this check's to make.
                path = site.site_map.address_of(path)
                if path is None:
                    continue
            path = path.split("?", 1)[0]
            if not path:
                if fragment and fragment not in ids:
                    problems.append(f"{where}: the page has no element with the id {fragment!r}")
                continue
            if not path.startswith("/"):
                problems.append(f"{where}: a relative address; name the address from the root")
                continue
            if site.answer(path) is None:
                problems.append(f"{where}: no route serves {path}")
                continue
            targets = site.fragment_documents(path)
            if fragment and targets and not any(node.attrs.get("id") == fragment
                                                for target in targets for node in target.walk()):
                problems.append(f"{where}: the page at {path} has no element with the id {fragment!r}")
    for surface in site.site_map.hostnames:
        page = site.site_map.page(surface.address)
        view = view_of(site.document(surface.address), page.view)
        if surface.anchor and (view is None or not any(item.attrs.get("id") == surface.anchor for item in view.walk())):
            problems.append(f"hostname {surface.hostname}: the view {page.view!r} has no element {surface.anchor!r} to open at")
    return problems


def _site_links(site_map, element):
    """The addresses of this website that the links inside `element` open: from the root, or as whole addresses of the
    canonical hostname or of a canonical section's hostname."""
    links = set()
    for item in element.walk():
        if item.tag != "a" or "href" not in item.attrs:
            continue
        href = item.attrs["href"].split("#", 1)[0]
        address = href if href.startswith("/") else site_map.address_of(href) if EXTERNAL.match(href) else None
        if address is not None:
            links.add(address)
    return links


def _content_links(site, page):
    view = view_of(site.document(page.address), page.view)
    return set() if view is None else _site_links(site.site_map, view)


def _chrome_links(site_map, document, tag):
    part = first(document, lambda item: item.tag == tag)
    return set() if part is None else _site_links(site_map, part)


def every_page_is_reached_or_has_a_reason(site):
    problems, site_map = [], site.site_map
    pages = {page.address: page for page in site_map.pages}
    for address in site.table:
        answer = site.answer(address)
        # A file under /assets/ is part of a page, such as a documentation body the page script draws, not a page.
        if answer is not None and answer[1] == HTML and address not in pages and not address.startswith("/assets/"):
            problems.append(f"{address}: served as a page and absent from the site map")
    header, footer, content = set(), set(), {}
    for document, addresses in site.page_documents():
        header |= _chrome_links(site_map, document, "header")
        footer |= _chrome_links(site_map, document, "footer")
    for page in site_map.pages:
        content[page.address] = _content_links(site, page)
    # A page nothing links to is still a way in: an earlier link, a message or the identity provider opens it, and the
    # site map writes down which. What such a page links to is reached from there.
    reached, waiting = set(), ["/", *(surface.address for surface in site_map.hostnames),
                               *(page.address for page in site_map.pages if page.unlinked_reason)]
    while waiting:
        address = waiting.pop()
        if address in reached or address not in pages or site.document(address) is None:
            continue
        reached.add(address)
        waiting.extend(sorted(header | footer | content[address]))
    for page in site_map.pages:
        from_pages = sorted(source for source, links in content.items() if page.address in links and source != page.address)
        places = {"header": page.address in header, "footer": page.address in footer, "page": bool(from_pages)}
        if not page.linked_from:
            sources = [place for place, linked in places.items() if linked]
            if sources:
                problems.append(f"{page.address}: the site map calls it unlinked ({page.unlinked_reason}), and the "
                                f"{', '.join(sources)} links to it" + (f" (from {from_pages})" if from_pages else ""))
            continue
        if page.address not in reached:
            problems.append(f"{page.address}: no link from the homepage or a hostname reaches it")
        for place in page.linked_from:
            if not places[place]:
                problems.append(f"{page.address}: the site map says the {place} links to it, and the served {place} does not")
    return problems


def site_sections(site):
    """Every section a served page holds: its bands and its headings with an id."""
    sections = set()
    for document, _addresses in site.page_documents():
        for item in document.walk():
            if "data-band" in item.attrs:
                sections.add("band:" + item.attrs["data-band"])
            if item.tag == "h2" and item.attrs.get("id"):
                sections.add("heading:" + item.attrs["id"])
    return sections


def _kept(site, item, sections):
    site_map = site.site_map
    if item["kind"] == "page":
        return site_map.page(item["subject"]) is not None
    if item["kind"] == "header_link":
        return item["subject"] in {entry_key(entry.role, entry.label, entry.href) for entry in site_map.header[item["state"]]}
    if item["kind"] == "footer_link":
        return item["subject"] in {link.href for group in site_map.footer_groups for link in group.links} | {site_map.footer_brand}
    return item["subject"] in sections


def nothing_in_an_inventory_is_lost(site):
    problems, sections = [], site_sections(site)
    for inventory in site.inventories:
        for item in inventory["items"]:
            removed = any(row.kind == item["kind"] and row.subject == item["subject"] and row.state == item.get("state", "")
                          for row in site.site_map.removed)
            if not removed and not _kept(site, item, sections):
                state = f" ({item['state']})" if item.get("state") else ""
                problems.append(f"{inventory['release']}: the {item['kind'].replace('_', ' ')} {item['subject']}{state} is gone, "
                                "and the site map has no dated removal row that gives the reason")
    return problems


def customer_pages_write_the_price_one_way(site):
    problems, price = [], (site.layout or load_layout_standard()).price
    for document, addresses in site.page_documents():
        text = document.text()
        for phrase in price["refused_phrases"]:
            for found in re.finditer(re.escape(phrase), text):
                problems.append(f"{addresses[0]}: writes {text[max(0, found.start() - 30):found.end() + 12]!r}; "
                                f"a customer page writes the price as {price['phrase']!r}")
        for found in re.finditer(re.escape(price["marker"]), text):
            if text[found.start():found.start() + len(price["phrase"])] != price["phrase"]:
                problems.append(f"{addresses[0]}: writes {text[found.start():found.start() + 24]!r}; "
                                f"the price is written {price['phrase']!r}")
    return problems


#: Every rule, by the name its checks report.
RULES = {
    "pages_are_served_with_one_h1": pages_are_served_with_one_h1,
    "header_matches_the_site_map": header_matches_the_site_map,
    "footer_matches_the_site_map": footer_matches_the_site_map,
    "internal_addresses_are_served": internal_addresses_are_served,
    "every_page_is_reached_or_has_a_reason": every_page_is_reached_or_has_a_reason,
    "nothing_in_an_inventory_is_lost": nothing_in_an_inventory_is_lost,
    "customer_pages_write_the_price_one_way": customer_pages_write_the_price_one_way,
}


def load_inventories():
    inventories = []
    for path in sorted(ROOT.glob(INVENTORY_GLOB)):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("record_type") != INVENTORY_RECORD_TYPE:
            raise ValueError(f"{path}: this check reads {INVENTORY_RECORD_TYPE}")
        inventories.append(record)
    return tuple(inventories)


#: What the service answers for a counted link of a public list, `/out/<list>/<link>/<row>`: a redirect to the
#: address that list's packaged link table holds (`public_links.py`). A link the tables do not hold is not served.
COUNTED_LINK_ANSWER = "redirect"


def served_site():
    """The website this checkout serves, read through the service's own served address table."""
    from urllib.parse import unquote

    from loop_engine.core.service_runtime import (catalogue_feed, dot_pages, feed_source_collections, gallery_page,
                                                  library_page, offering_guides, openapi_tool_server, public_good_page, red_team_page,
                                                  library_site_pages, status_pages, support_page)
    from loop_engine.core.service_runtime.model_directory_pages import rendered_page
    from loop_engine.core.service_runtime.public_links import PublicListLinks
    site_map = load_site_map()
    counted_links = PublicListLinks()

    def serve(address):
        if address == openapi_tool_server.DOCUMENT_PATH and "GET" in openapi_tool_server.ROUTES.get(address, ()):
            # An exact public data route, not a wildcard exception for API paths.
            # test_openapi_tool_server checks the actual HTTP response and document against the transport routes.
            return "", "application/json"
        if address in feed_source_collections.formats():
            body, media_type = feed_source_collections.render(address, "https://" + site_map.canonical_hostname)
            return body.decode("utf-8"), media_type
        if address in catalogue_feed.FORMATS:
            # Route declaration only. The actual anonymous HTTP, HEAD,
            # conditional-read and unavailable states run in test_catalogue_feed.
            return "", catalogue_feed.FORMATS[address]
        # The transport answers the model directory's rendered pages after the served address table, then the library
        # page from the catalogue it serves; no catalogue runs here, so the library page is rendered from an empty view.
        # The decision red team page and the three pages nothing links to (changelog, features, open work) come next,
        # each from its packaged record, then the support page, the two guide pages and the gallery.
        answer = (web_pages.served_asset(address, "GET", site_map.display_name)
                  or rendered_page(address, "GET", site_map.display_name)
                  or library_page.rendered(library_page.empty_view(), address, "GET", site_map.display_name)
                  or public_good_page.rendered(address, "GET", site_map.display_name)
                  or catalogue_feed.rendered_page(address, "GET", site_map.display_name)
                  or dot_pages.rendered(address, "GET", site_map.display_name)
                  or red_team_page.rendered(address, "GET", site_map.display_name)
                  or status_pages.rendered(address, "GET", site_map.display_name)
                  or support_page.rendered(address, "GET", site_map.display_name)
                  or offering_guides.rendered(address, "GET", site_map.display_name, None, library_page.empty_view())
                  or gallery_page.rendered(address, "GET", site_map.display_name)
                  or library_site_pages.rendered(address, "GET", site_map.display_name))
        if answer is None:
            return ("", COUNTED_LINK_ANSWER) if counted_links.destination(unquote(address)) else None
        return (answer[0].decode("utf-8"), answer[1]) if answer[1] == HTML else ("", answer[1])
    index = json.loads(web_pages.read_packaged_asset("documentation-index.json"))
    bodies = {address: page["body"] for section in index["sections"] for page in section["pages"]
              if "body" in page for address in (page["address"], *page.get("aliases", ()))}
    return Site(site_map, serve, tuple(web_pages.WEB_ASSETS), load_inventories(), load_layout_standard(),
                fragment_bodies=bodies)


def inventory_of(site, release, revision):
    """What the served website holds, as a dated inventory: pages, header and footer links, sections."""
    items = [{"kind": "page", "subject": address} for address in site.table
             if (site.answer(address) or ("", ""))[1] == HTML]
    document = site.document("/")
    for state in HEADER_STATES:
        items.extend({"kind": "header_link", "state": state, "subject": entry_key(*entry)}
                     for entry in header_entries(document, state) or [])
    footer = first(document, lambda item: item.tag == "footer")
    items.extend({"kind": "footer_link", "subject": href} for href in dict.fromkeys(
        item.attrs["href"] for item in footer.walk() if item.tag == "a" and "href" in item.attrs))
    items.extend({"kind": "section", "subject": name} for name in sorted(site_sections(site)))
    return {"record_type": INVENTORY_RECORD_TYPE, "release": release, "revision": revision,
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_by": "tools/test_website_site_map.py --write-inventory", "items": items}


# The fixture site: a small website that passes every rule, so that each known-wrong case changes one thing.
FIXTURE_MAP = {
    "record_type": "service_web_site_map/v4", "decided_on": "2026-09-23", "decided_by": "the fixture",
    "display_name": "Example", "canonical_hostname": "example.com", "social_image": "/assets/mark.svg",
    "groups": ["Product", "Company", "Account"],
    "pages": [
        {"address": "/", "view": "home", "title": "Home", "description": "The fixture homepage.", "group": "Product", "linked_from": ["header", "footer"],
         "unlinked_reason": "", "scroll_budget": "long", "price_in_first_screen": True, "indexed": True},
        {"address": "/pricing", "view": "pricing", "title": "Pricing", "description": "What the fixture costs.", "group": "Product", "linked_from": ["header", "footer"],
         "unlinked_reason": "", "scroll_budget": "page", "price_in_first_screen": True, "indexed": True},
        {"address": "/start", "view": "start", "title": "Start", "description": "Start with the fixture.", "group": "Product", "linked_from": ["header"],
         "unlinked_reason": "", "scroll_budget": "page", "price_in_first_screen": False, "indexed": True},
        {"address": "/guide", "view": "guide", "title": "Guide", "description": "How to use the fixture.", "group": "Product", "linked_from": ["page"],
         "unlinked_reason": "", "scroll_budget": "documentation", "price_in_first_screen": False, "indexed": True},
        {"address": "/old", "view": "pricing", "title": "Pricing", "description": "The earlier address of the fixture's pricing.", "group": "Product", "linked_from": [],
         "unlinked_reason": "old address kept so earlier links work", "scroll_budget": "page", "price_in_first_screen": False, "indexed": False},
        {"address": "/login", "view": "login", "title": "Sign in", "description": "Sign in to the fixture.", "group": "Company", "linked_from": ["header", "footer"],
         "unlinked_reason": "", "scroll_budget": "page", "price_in_first_screen": False, "indexed": True},
        {"address": "/app", "view": "workspace", "title": "Workspace", "description": "The fixture's workspace.", "group": "Account", "linked_from": ["header"],
         "unlinked_reason": "", "scroll_budget": "page", "price_in_first_screen": False, "indexed": False},
        {"address": "/admin", "view": "admin", "title": "Administration", "description": "The fixture's administration.", "group": "Account", "linked_from": ["header"],
         "unlinked_reason": "", "scroll_budget": "page", "price_in_first_screen": False, "indexed": False}],
    "header": {
        "signed_out": [{"role": "brand", "label": "Example", "href": "/"}, {"role": "link", "label": "Pricing", "href": "/pricing"},
                       {"role": "link", "label": "Sign in", "href": "/login"}, {"role": "primary", "label": "Get started", "href": "/start"}],
        "signed_in": [{"role": "brand", "label": "Example", "href": "/"}, {"role": "link", "label": "Pricing", "href": "/pricing"},
                      {"role": "link", "label": "Workspace", "href": "/app"}, {"role": "button", "label": "Sign out", "href": None}],
        "operator": [{"role": "brand", "label": "Example", "href": "/"}, {"role": "link", "label": "Pricing", "href": "/pricing"},
                     {"role": "link", "label": "Workspace", "href": "/app"}, {"role": "link", "label": "Administration", "href": "/admin"},
                     {"role": "button", "label": "Sign out", "href": None}]},
    "footer": {"brand_href": "/", "groups": [
        {"name": "Product", "links": [{"role": "link", "label": "Pricing", "href": "/pricing"},
                                      {"role": "link", "label": "Library", "href": "/#library"}]},
        {"name": "Company", "links": [{"role": "link", "label": "Sign in", "href": "/login"},
                                      {"role": "link", "label": "Notices", "href": "/assets/notices.txt"}]}],
        "base_row": {"operator": "Example.AI", "operator_line": "1 Example Street", "mark": "/assets/mark.svg"}},
    "hostnames": [{"hostname": "example.com", "address": "/", "anchor": "", "canonical_section": False},
                  {"hostname": "demo.example.com", "address": "/", "anchor": "demo", "canonical_section": False}],
    "removed": [{"date": "2026-09-23", "kind": "header_link", "state": "signed_out", "subject": "/retired",
                 "reason": "the fixture retired it", "decided_by": "the fixture"}],
}
FIXTURE_PARTS = {
    "head": '<!doctype html><html lang="en"><head><link rel="stylesheet" href="/assets/site.css"></head><body>',
    "header": ('<header><a class="brand" href="/"><img src="/assets/mark.svg" alt=""><span>Example</span></a>'
               '<button type="button" aria-label="Menu" aria-expanded="false" aria-controls="menu"></button><nav id="menu">'
               '<a href="/pricing">Pricing</a><a href="/app" data-signed-in hidden>Workspace</a>'
               '<a href="/admin" hidden>Administration</a><a href="/login" data-signed-out>Sign in</a>'
               '<button type="button" data-signed-in hidden>Sign out</button></nav>'
               '<a class="button primary" href="/start" data-signed-out>Get started</a></header>'),
    "home": ('<section data-view="home"><div data-band="hero"><h1>Home</h1><p>One plan, $49 a month.</p>'
             '<a href="/guide">Read the guide</a><div id="demo"></div></div>'
             '<div data-band="library" id="library"><h2 id="library-title">Library</h2></div></section>'),
    "pricing": '<section data-view="pricing" hidden><h1>Pricing</h1><p>$49 a month.</p></section>',
    "start": '<section data-view="start" hidden><h1>Start</h1></section>',
    "guide": '<section data-view="guide" hidden><h1>Guide</h1><h2 id="guide-steps">Steps</h2></section>',
    "login": '<section data-view="login" hidden><h1>Sign in</h1><div hidden><h1>Signed in</h1></div></section>',
    "workspace": '<section data-view="workspace" hidden><h1>Workspace</h1></section>',
    "admin": '<section data-view="admin" hidden><h1>Administration</h1></section>',
    "footer": ('<footer><div><a class="brand" href="/">Example</a></div>'
               '<nav aria-label="Product"><p class="footer-heading">Product</p><a href="/pricing">Pricing</a>'
               '<a href="/#library">Library</a></nav>'
               '<nav aria-label="Company"><p class="footer-heading">Company</p><a href="/login">Sign in</a>'
               '<a href="/assets/notices.txt?v=0000000000000000000000000000000000000000000000000000000000000000">Notices</a></nav>'
               '<div><p><img src="/assets/mark.svg?v=0000000000000000000000000000000000000000000000000000000000000000" alt="">© 2026 Example.AI · 1 Example Street</p></div></footer>'),
    "tail": "</body></html>",
}
FIXTURE_FILES = {"/assets/site.css": "text/css", "/assets/notices.txt": "text/plain", "/assets/mark.svg": "image/svg+xml"}
FIXTURE_INVENTORY = {"record_type": INVENTORY_RECORD_TYPE, "release": "fixture release", "revision": "fixture", "items": [
    {"kind": "page", "subject": "/"}, {"kind": "page", "subject": "/pricing"},
    {"kind": "header_link", "state": "signed_out", "subject": "/pricing"},
    {"kind": "header_link", "state": "signed_out", "subject": "/retired"},
    {"kind": "header_link", "state": "signed_in", "subject": "button:Sign out"},
    {"kind": "footer_link", "subject": "/#library"},
    {"kind": "section", "subject": "band:library"}, {"kind": "section", "subject": "heading:guide-steps"}]}


@dataclass(frozen=True)
class Fixture:
    """The parts of the fixture site, each one replaceable by a known-wrong case."""

    record: dict
    parts: dict
    addresses: tuple
    inventory: dict

    def site(self):
        page = "".join(self.parts[name] for name in ("head", "header")) + "<main>" + "".join(
            self.parts[name] for name in ("home", "pricing", "start", "guide", "login", "workspace", "admin")) + "</main>" + \
            self.parts["footer"] + self.parts["tail"]

        def serve(address):
            if address in FIXTURE_FILES and address in self.addresses:
                return "", FIXTURE_FILES[address]
            return (page, HTML) if address in self.addresses else None
        return Site(site_map_from_record(self.record), serve, self.addresses, (self.inventory,), load_layout_standard())


def fixture():
    pages = tuple(row["address"] for row in FIXTURE_MAP["pages"])
    return Fixture(json.loads(json.dumps(FIXTURE_MAP)), dict(FIXTURE_PARTS), pages + tuple(FIXTURE_FILES),
                   json.loads(json.dumps(FIXTURE_INVENTORY)))


def _part(name, old, new):
    """A known-wrong case that changes one part of the fixture page."""
    def change(state):
        if old not in state.parts[name]:
            raise AssertionError(f"the fixture part {name} has no {old!r}")
        return replace(state, parts={**state.parts, name: state.parts[name].replace(old, new, 1)})
    return change


def _served(add=(), drop=()):
    def change(state):
        return replace(state, addresses=tuple(address for address in state.addresses if address not in drop) + tuple(add))
    return change


def _inventory(*items):
    def change(state):
        return replace(state, inventory={**state.inventory, "items": state.inventory["items"] + list(items)})
    return change


def _no_removals(state):
    return replace(state, record={**state.record, "removed": []})


KNOWN_WRONG = {
    "pages_are_served_with_one_h1": (
        ("the served address table drops a page", _served(drop=("/guide",))),
        ("the page loses the view a page names", _part("guide", 'data-view="guide"', 'data-view="guidance"')),
        ("a view shows two h1 headings", _part("pricing", "<p>", "<h1>Plans</h1><p>")),
        ("a view shows no h1", _part("start", "<h1>Start</h1>", "<h2>Start</h2>"))),
    "header_matches_the_site_map": (
        ("a header link is missing", _part("header", '<a href="/pricing">Pricing</a>', "")),
        ("two header links are out of order", _part(
            "header", '<nav id="menu"><a href="/pricing">Pricing</a><a href="/app" data-signed-in hidden>Workspace</a>'
                      '<a href="/admin" hidden>Administration</a><a href="/login" data-signed-out>Sign in</a>',
            '<nav id="menu"><a href="/app" data-signed-in hidden>Workspace</a><a href="/admin" hidden>Administration</a>'
            '<a href="/login" data-signed-out>Sign in</a><a href="/pricing">Pricing</a>')),
        # The menu button is left out only because it controls the header's own navigation.
        ("a header button that controls something else is an entry",
         _part("header", "</nav>", '</nav><button type="button" aria-controls="elsewhere">Help</button>')),
        ("the header gains a link", _part("header", "</nav>", '<a href="/guide">Guide</a></nav>')),
        ("the primary action opens another page", _part("header", 'href="/start" data-signed-out', 'href="/pricing" data-signed-out')),
        ("the operator's entry is shown to everyone", _part("header", '<a href="/admin" hidden>', '<a href="/admin">')),
        ("a header label changes", _part("header", ">Sign in<", ">Log in<"))),
    "footer_matches_the_site_map": (
        ("a footer group is missing", _part("footer", '<nav aria-label="Company"><p class="footer-heading">Company</p>'
                                                     '<a href="/login">Sign in</a><a href="/assets/notices.txt?v=0000000000000000000000000000000000000000000000000000000000000000">Notices</a></nav>', "")),
        ("a footer group is hidden", _part("footer", '<nav aria-label="Product">', '<nav aria-label="Product" hidden>')),
        ("a footer link is missing", _part("footer", '<a href="/#library">Library</a>', "")),
        ("footer links are out of order", _part("footer", '<a href="/pricing">Pricing</a><a href="/#library">Library</a>',
                                                '<a href="/#library">Library</a><a href="/pricing">Pricing</a>')),
        ("a footer group gains a link", _part("footer", '<a href="/#library">Library</a>', '<a href="/#library">Library</a><a href="/guide">Guide</a>')),
        ("the base row loses the mark", _part("footer", '<p><img src="/assets/mark.svg?v=0000000000000000000000000000000000000000000000000000000000000000" alt="">', "<p>")),
        ("a packaged file's link carries a query other than its content version",
         _part("footer", '<a href="/assets/notices.txt?v=0000000000000000000000000000000000000000000000000000000000000000">', '<a href="/assets/notices.txt?x=1">')),
        ("the base row loses the operator line", _part("footer", " · 1 Example Street", ""))),
    "internal_addresses_are_served": (
        ("a link names an address nothing serves", _part("home", '<a href="/guide">', '<a href="/guide">Guide</a><a href="/nowhere">')),
        ("a link names a part of a page that does not exist", _part("pricing", "<p>", '<p><a href="/#missing">Library</a>')),
        ("the stylesheet is not served", _served(drop=("/assets/site.css",))),
        ("a relative address", _part("pricing", "<p>", '<p><a href="guide">Guide</a>')),
        ("a hostname opens a part of a page that does not exist", _part("home", 'id="demo"', 'id="demonstration"'))),
    "every_page_is_reached_or_has_a_reason": (
        ("a served page is absent from the site map", _served(add=("/extra",))),
        ("nothing links to a page", _part("home", '<a href="/guide">Read the guide</a>', "")),
        ("a page the site map calls unlinked is linked", _part("pricing", "<p>", '<p><a href="/old">Old</a>')),
        ("the footer does not link a page the site map says it links", _part("footer", '<a href="/login">Sign in</a>', ""))),
    "nothing_in_an_inventory_is_lost": (
        ("an inventoried page is gone", _inventory({"kind": "page", "subject": "/vanished"})),
        ("an inventoried header link is gone", _inventory({"kind": "header_link", "state": "signed_in", "subject": "/login"})),
        ("an inventoried footer link is gone", _inventory({"kind": "footer_link", "subject": "/examples"})),
        ("an inventoried section is gone", _part("guide", '<h2 id="guide-steps">Steps</h2>', "<h2>Steps</h2>")),
        ("the removal row that gave the reason is deleted", _no_removals)),
    "customer_pages_write_the_price_one_way": (
        ("a page writes United States dollars", _part("pricing", "<p>$49 a month.</p>", "<p>29 United States dollars each month.</p>")),
        ("the price is followed by other words", _part("home", "$49 a month", "$49 per month"))),
}


def report(found):
    lines = []
    for name, problems in found.items():
        lines.append(f"{name}: {len(problems)} problem{'s' if len(problems) != 1 else ''}")
        lines.extend("  - " + problem for problem in problems)
    return "\n".join(lines)


class SiteMapRules(unittest.TestCase):
    def test_documentation_fragments_require_the_heading_in_the_declared_body(self):
        held = fixture()
        held = replace(held, parts={**held.parts, "home": held.parts["home"] +
                                   '<a href="/pricing#plan-details">Plan details</a>'})
        site = held.site()
        serve = site.serve
        body = '<h2 id="plan-details">Plan details</h2>'
        site.fragment_bodies = {"/pricing": "/assets/plan-details.html"}
        site.serve = lambda address: (body, HTML) if address == "/assets/plan-details.html" else serve(address)
        self.assertEqual(internal_addresses_are_served(site), [])
        body = '<h2 id="other-details">Plan details</h2>'
        self.assertTrue(any("plan-details" in problem for problem in internal_addresses_are_served(site)))
        site.serve = serve
        self.assertTrue(any("plan-details" in problem for problem in internal_addresses_are_served(site)))

    """Each rule reports its known-wrong sites, and the fixture site passes every rule."""

    def test_the_fixture_site_passes_every_rule(self):
        site = fixture().site()
        found = {name: rule(site) for name, rule in RULES.items()}
        self.assertEqual({name: problems for name, problems in found.items() if problems}, {})

    def test_every_rule_has_known_wrong_cases(self):
        self.assertEqual(set(KNOWN_WRONG), set(RULES))
        self.assertTrue(all(len(cases) >= 2 for cases in KNOWN_WRONG.values()))

    def check_rule(self, name):
        for description, change in KNOWN_WRONG[name]:
            with self.subTest(case=description):
                self.assertTrue(RULES[name](change(fixture()).site()), f"{name} did not report: {description}")

    def test_a_removed_rule_fails_its_named_check(self):
        """The mutant control: with one rule patched away, its own named check must fail once for each case."""
        for name, cases in KNOWN_WRONG.items():
            check = f"test_{name}_rejects_its_known_wrong_cases"
            with self.subTest(rule=name):
                intact = unittest.TestResult()
                SiteMapRules(check).run(intact)
                self.assertTrue(intact.wasSuccessful() and intact.testsRun == 1, f"{check} fails with its rule in place")
                with mock.patch.dict(RULES, {name: lambda site: []}):
                    mutant = unittest.TestResult()
                    SiteMapRules(check).run(mutant)
                self.assertEqual(len(mutant.failures), len(cases), f"{check} survived the removal of {name}")
                self.assertEqual(mutant.errors, [])


for _name in RULES:
    setattr(SiteMapRules, f"test_{_name}_rejects_its_known_wrong_cases",
            lambda self, name=_name: self.check_rule(name))


def _record_change(path, value):
    """A known-wrong record: the fixture record with one field set, path as a tuple of keys and indexes."""
    def change(record):
        target = record
        for key in path[:-1]:
            target = target[key]
        if value is _DELETE:
            del target[path[-1]]
        else:
            target[path[-1]] = value
        return record
    return change


_DELETE = object()
KNOWN_WRONG_RECORDS = {
    "a record version this reader was not written for": _record_change(("record_type",), "service_web_site_map/v1"),
    "a page without a description": _record_change(("pages", 1, "description"), _DELETE),
    "a description a search engine would cut short": _record_change(("pages", 1, "description"), "Pricing. " * 20),
    "a description on two lines": _record_change(("pages", 1, "description"), "What the fixture costs.\nAnd more."),
    "a page only earlier links reach that asks to be listed": _record_change(("pages", 4, "indexed"), True),
    "two listed pages with one description": _record_change(("pages", 1, "description"), "The fixture homepage."),
    "two listed pages with one title": _record_change(("pages", 2, "title"), "Pricing"),
    "a hostname whose root only earlier links reach": _record_change(("hostnames", 1, "address"), "/old"),
    "a canonical hostname whose root is not the homepage": _record_change(("hostnames", 0, "address"), "/pricing"),
    "a shared-link picture outside the packaged files": _record_change(("social_image",), "https://example.com/mark.svg"),
    "an unknown field": _record_change(("colour",), "blue"),
    "a missing field": _record_change(("hostnames",), _DELETE),
    "a repeated page address": lambda record: {**record, "pages": record["pages"] + [record["pages"][1]]},
    "a page nothing links to, without a reason": _record_change(("pages", 4, "unlinked_reason"), ""),
    "a page with both places and a reason": _record_change(("pages", 1, "unlinked_reason"), "no reason needed"),
    "a page that says the footer links it when the footer does not": _record_change(("pages", 2, "linked_from"), ["header", "footer"]),
    "a header link to an address that is not a page": _record_change(("header", "signed_out", 1, "href"), "/nowhere"),
    "a header state that does not open with the brand": _record_change(("header", "signed_in", 0, "role"), "link"),
    "a header state with two primary actions": _record_change(("header", "signed_out", 2, "role"), "primary"),
    "a button with an address": _record_change(("header", "signed_in", 3, "href"), "/logout"),
    "a removal without a reason": _record_change(("removed", 0, "reason"), ""),
    "a removed header link without its state": _record_change(("removed", 0, "state"), ""),
    "a hostname that opens an address that is not a page": _record_change(("hostnames", 1, "address"), "/demo"),
    "a view name that is not a lowercase token": _record_change(("pages", 0, "view"), "Home View"),
    "a hostname without its section choice": _record_change(("hostnames", 1, "canonical_section"), _DELETE),
    "a section choice that is not true or false": _record_change(("hostnames", 1, "canonical_section"), "yes"),
    "the canonical hostname holding a canonical section": _record_change(("hostnames", 0, "canonical_section"), True),
    "a canonical section at the homepage": _record_change(("hostnames", 1, "canonical_section"), True),
    "a canonical section on another domain": lambda record: _with_section(record, "guide.example.org", "/guide"),
    "a canonical section whose page search engines may not list": lambda record: _with_section(record, "app.example.com", "/app"),
    "a canonical section that opens a part of its page": lambda record: _with_section(record, "guide.example.com", "/guide",
                                                                                      "guide-steps"),
    "two canonical sections that overlap": lambda record: _with_section(_with_section(record, "guide.example.com", "/guide"),
                                                                        "guides.example.com", "/guide"),
}
GUARDED_RECORD_CASES = {
    "_consistency": ("a page that says the footer links it when the footer does not",
                     "a header link to an address that is not a page",
                     "a hostname that opens an address that is not a page",
                     "a hostname whose root only earlier links reach",
                     "a canonical hostname whose root is not the homepage",
                     "two listed pages with one description"),
    "_unique": ("a repeated page address",),
    "_sections": ("the canonical hostname holding a canonical section", "a canonical section at the homepage",
                  "a canonical section on another domain", "a canonical section whose page search engines may not list",
                  "a canonical section that opens a part of its page", "two canonical sections that overlap"),
}


def _with_section(record, hostname, address, anchor=""):
    """The record with one more hostname that holds the canonical section at `address`."""
    return {**record, "hostnames": record["hostnames"] + [
        {"hostname": hostname, "address": address, "anchor": anchor, "canonical_section": True}]}


class SiteMapRecords(unittest.TestCase):
    """The typed reader accepts the packaged records and refuses each known-wrong record."""

    def test_case_studies_have_a_finite_budget_without_relaxing_the_homepage(self):
        site_map, layout = load_site_map(), load_layout_standard()
        pages = {page.address: page for page in site_map.pages}
        self.assertEqual(layout.page_height_max_px["case-study"], 6000)
        self.assertEqual(layout.page_height_max_px["long"], 4000)
        self.assertEqual(layout.page_height_max_px["page"], 2700)
        self.assertEqual(pages["/"].scroll_budget, "long")
        self.assertEqual(pages["/how-it-works"].scroll_budget, "long")
        for address in ("/case-studies/data-cleanup", "/case-studies/pi-and-gemma-4",
                        "/case-studies/sign-up-protection"):
            with self.subTest(address=address):
                self.assertEqual(pages[address].scroll_budget, "case-study")
        self.assertEqual(pages["/case-studies/decision-red-team"].scroll_budget, "documentation")

    def test_site_map_refuses_versions_without_the_current_budget_contract(self):
        for version in ("service_web_site_map/v3", "service_web_site_map/v5"):
            with self.subTest(version=version), self.assertRaises(SiteMapError):
                site_map_from_record({**json.loads(json.dumps(FIXTURE_MAP)), "record_type": version})

    def test_the_packaged_records_are_read_by_the_typed_reader(self):
        site_map, layout = load_site_map(), load_layout_standard()
        self.assertEqual(site_map.record_type, "service_web_site_map/v4")
        self.assertEqual(layout.record_type, "service_web_layout_standard/v2")
        self.assertEqual([group.name for group in site_map.footer_groups], ["Product", "Library", "Use cases", "Documentation", "Company"])
        self.assertEqual(max(layout.section_padding_px["desktop"]), 64)
        self.assertEqual(max(layout.section_padding_px["phone"]), 40)

    def test_the_fixture_record_is_accepted(self):
        self.assertEqual(site_map_from_record(json.loads(json.dumps(FIXTURE_MAP))).display_name, "Example")

    def test_a_canonical_section_names_its_own_hostname_for_its_pages_and_root_files(self):
        site_map = site_map_from_record(_with_section(json.loads(json.dumps(FIXTURE_MAP)), "guide.example.com", "/guide"))
        self.assertEqual(site_map.canonical_url("/guide"), "https://guide.example.com/")
        self.assertEqual(site_map.canonical_url("/guide/steps"), "https://guide.example.com/guide/steps")
        # A longer name that only starts like the section is not below it.
        self.assertEqual(site_map.canonical_url("/guides"), "https://example.com/guides")
        self.assertEqual(site_map.canonical_url("/pricing"), "https://example.com/pricing")
        self.assertEqual(site_map.section_file("guide.example.com:443", "/robots.txt"), "/guide/robots.txt")
        self.assertIsNone(site_map.section_file("example.com", "/robots.txt"))
        self.assertIsNone(site_map.section_file("guide.example.com", "/pricing"))
        self.assertEqual(site_map.address_of("https://guide.example.com/"), "/guide")
        self.assertEqual(site_map.address_of("https://guide.example.com/sitemap.xml"), "/guide/sitemap.xml")
        self.assertEqual(site_map.address_of("https://guide.example.com/guide/steps?x=1#top"), "/guide/steps")
        self.assertEqual(site_map.address_of("https://example.com/pricing?x=1#plans"), "/pricing")
        for other in ("http://example.com/pricing", "https://example.org/", "https://user@example.com/",
                      "https://example.com:8443/", "https://demo.example.com/", "mailto:someone@example.com"):
            with self.subTest(address=other):
                self.assertIsNone(site_map.address_of(other))
        # Without the section every page keeps its canonical address on the canonical hostname.
        plain = site_map_from_record(json.loads(json.dumps(FIXTURE_MAP)))
        self.assertEqual(plain.canonical_url("/guide"), "https://example.com/guide")
        self.assertIsNone(plain.section_file("guide.example.com", "/robots.txt"))

    def test_the_reader_refuses_each_known_wrong_record(self):
        for description, change in KNOWN_WRONG_RECORDS.items():
            with self.subTest(case=description):
                with self.assertRaises(SiteMapError):
                    site_map_from_record(change(json.loads(json.dumps(FIXTURE_MAP))))

    def test_the_layout_reader_refuses_known_wrong_records(self):
        record = json.loads((Path(web_site_map.__file__).parent / web_site_map.LAYOUT_STANDARD_FILE).read_text(encoding="utf-8"))
        for description, change in {
                "an older version": lambda row: {**row, "record_type": "service_web_layout_standard/v1"},
                "a future version": lambda row: {**row, "record_type": "service_web_layout_standard/v3"},
                "a missing case-study budget": lambda row: {**row, "page_height_max_px": {key: value for key, value in row["page_height_max_px"].items() if key != "case-study"}},
                "an unlimited case-study budget": lambda row: {**row, "page_height_max_px": {**row["page_height_max_px"], "case-study": None}},
                "a zero case-study budget": lambda row: {**row, "page_height_max_px": {**row["page_height_max_px"], "case-study": 0}},
                "padding values without zero": lambda row: {**row, "section_padding_px": {"desktop": [32, 64], "phone": [0, 40]}},
                "a contrast ratio that is not a ratio": lambda row: {**row, "text_contrast_min": 0.5},
                "a price phrase that does not start with its marker": lambda row: {**row, "price": {**row["price"], "phrase": "29 a month"}},
                "an unknown field": lambda row: {**row, "spacing": 8}}.items():
            with self.subTest(case=description):
                with self.assertRaises(SiteMapError):
                    layout_standard_from_record(change(json.loads(json.dumps(record))))

    def test_a_removed_reader_guard_lets_its_known_wrong_record_through(self):
        """The mutant control for the reader: without a guard, the records it refused are read."""
        for guard, cases in GUARDED_RECORD_CASES.items():
            for description in cases:
                with self.subTest(guard=guard, case=description), mock.patch.object(web_site_map, guard, lambda *given: None):
                    site_map_from_record(KNOWN_WRONG_RECORDS[description](json.loads(json.dumps(FIXTURE_MAP))))


def _section_fixture(absolute):
    """The fixture site with /guide as the canonical section of guide.example.com, served as a page of its own whose
    header and footer name the canonical hostname's pages by their whole addresses, or from the root."""
    state = fixture()
    whole = lambda part: re.sub(r'href="/(?!assets/)', 'href="https://example.com/', part)  # noqa: E731
    header, footer = ((whole(state.parts[name]) if absolute else state.parts[name]) for name in ("header", "footer"))
    guide = (state.parts["head"] + header + "<main>" + state.parts["guide"].replace(" hidden", "", 1) + "</main>"
             + footer + state.parts["tail"])
    site = replace(state, record=_with_section(state.record, "guide.example.com", "/guide")).site()
    serve = site.serve
    site.serve = lambda address: (guide, HTML) if address == "/guide" else serve(address)
    return site


class CanonicalSectionChrome(unittest.TestCase):
    """A page of a canonical section links the canonical hostname's pages by their whole addresses, so a reader who
    signs up from it does so on the canonical hostname; every other page links them from the root."""

    def test_a_section_page_with_whole_addresses_passes_every_rule(self):
        site = _section_fixture(absolute=True)
        found = {name: rule(site) for name, rule in RULES.items()}
        self.assertEqual({name: problems for name, problems in found.items() if problems}, {})

    def test_a_section_page_that_links_from_the_root_is_refused(self):
        site = _section_fixture(absolute=False)
        for rule in (header_matches_the_site_map, footer_matches_the_site_map):
            with self.subTest(rule=rule.__name__):
                self.assertTrue(any("/guide" in problem for problem in rule(site)))

    def test_a_page_outside_a_section_that_links_by_whole_addresses_is_refused(self):
        whole = lambda part: re.sub(r'href="/(?!assets/)', 'href="https://example.com/', part)  # noqa: E731
        state = fixture()
        site = replace(state, parts={**state.parts, "header": whole(state.parts["header"])}).site()
        self.assertTrue(header_matches_the_site_map(site))

    def test_a_whole_address_of_this_website_that_nothing_serves_is_refused(self):
        state = fixture()
        site = replace(state, parts={**state.parts, "home": state.parts["home"].replace(
            '<a href="/guide">', '<a href="https://example.com/nowhere">Nowhere</a><a href="/guide">', 1)}).site()
        self.assertTrue(any("/nowhere" in problem for problem in internal_addresses_are_served(site)))
        # Another site's address is not this check's to make.
        site = replace(state, parts={**state.parts, "home": state.parts["home"].replace(
            '<a href="/guide">', '<a href="https://example.org/nowhere">Elsewhere</a><a href="/guide">', 1)}).site()
        self.assertEqual(internal_addresses_are_served(site), [])


SERVICE_SCRIPT = ROOT / "src/loop_engine/core/service_runtime/web_assets/service.js"
_VIEW_TITLES = re.compile(r"const viewTitle = (\{.*?\})\[name\]", re.S)
_VIEW_TITLE = re.compile(r'(?:"([^"]+)"|([A-Za-z_][A-Za-z0-9_]*))\s*:\s*"([^"]*)"')
_ROUTE_TABLE = re.compile(r"const routeNames = (\{.*?\});", re.S)
_ROUTE_ADDED = re.compile(r'routeNames\["([^"]+)"\]\s*=\s*"([^"]+)"')
_ROUTES_MERGED = re.compile(r"Object\.assign\(routeNames,\s*(\{.*?\})\)", re.S)


def browser_title_problems(script, site_map):
    """Each page the one-page app routes shows, in the browser tab, the title its site map entry names.

    The served head carries the site map's title, and `service.js` writes the title again from its own table whenever
    it shows a view. On October 16, 2026 that table lacked the worker and Top MCP views, so `/worker` and `/top-mcps`
    showed "Baltor | undefined" as soon as the script ran; no check read the table.
    """
    table = _VIEW_TITLES.search(script)
    if table is None:
        return ["service.js has no view title table"]
    titles = {quoted or bare: title for quoted, bare, title in _VIEW_TITLE.findall(table.group(1))}
    routes = {}
    for match in _ROUTE_TABLE.finditer(script):
        routes.update(json.loads(match.group(1)))
    routes.update(dict(_ROUTE_ADDED.findall(script)))
    for match in _ROUTES_MERGED.finditer(script):
        routes.update(json.loads(match.group(1)))
    return [f"{page.address} (view {routes[page.address]}) shows {titles.get(routes[page.address])!r}, and the site map has "
            f"{page.title!r}" for page in site_map.pages
            if page.address in routes and titles.get(routes[page.address]) != page.title]


class BrowserTitlesFollowTheSiteMap(unittest.TestCase):
    """The title a routed view writes into the browser tab is the site map's title for its address."""

    def test_every_routed_view_shows_its_site_map_title(self):
        self.assertEqual(browser_title_problems(SERVICE_SCRIPT.read_text("utf-8"), load_site_map()), [])

    def test_a_missing_or_changed_view_title_is_refused(self):
        script, site_map = SERVICE_SCRIPT.read_text("utf-8"), load_site_map()
        for old, new, address in ((', worker:"Run Baltor on your own computer"', "", "/worker"),
                                  ('"top-mcps":"Top MCP servers", ', "", "/top-mcps"),
                                  ('pricing:"Pricing"', 'pricing:"Prices"', "/pricing")):
            with self.subTest(address=address):
                known_wrong = script.replace(old, new)
                self.assertNotEqual(known_wrong, script, "the known-wrong case no longer changes service.js")
                self.assertTrue(any(problem.startswith(address + " ")
                                    for problem in browser_title_problems(known_wrong, site_map)))
        self.assertEqual(browser_title_problems("const route = 1;", site_map), ["service.js has no view title table"])


def footer_status_problems(site, read_script):
    """A served page that shows the footer's status line loads a script that fills it.

    The footer starts with "Checking service availability". On October 16, 2026 the deck loaded no script that replaced
    it, so the line stayed on every visit; the other pages fill it from the capabilities record.
    """
    problems = []
    for document, addresses in site.page_documents():
        if not any(item.attrs.get("id") == "service-status" for item in document.walk()):
            continue
        scripts = [unversioned(item.attrs["src"]) for item in document.walk() if item.tag == "script" and item.attrs.get("src")]
        if not any('"service-status"' in read_script(address) or "#service-status" in read_script(address)
                   for address in scripts):
            problems.append(f"{addresses[0]} shows the footer status line, and none of its scripts {scripts} fills it")
    return problems


def served_script(address):
    answer = web_pages.served_asset(address, "GET", load_site_map().display_name)
    return answer[0].decode("utf-8") if answer is not None else ""


class FooterStatusLinesAreFilled(unittest.TestCase):
    """No page leaves the footer's status line at its served placeholder."""

    @classmethod
    def setUpClass(cls):
        cls.site = served_site()

    def test_every_page_with_a_status_line_loads_a_script_that_fills_it(self):
        self.assertEqual(footer_status_problems(self.site, served_script), [])

    def test_a_page_whose_scripts_leave_the_line_alone_is_refused(self):
        def without_deck_status(address):
            source = served_script(address)
            return source.replace('"service-status"', '"another-element"') if address == "/assets/deck.js" else source
        problems = footer_status_problems(self.site, without_deck_status)
        self.assertTrue(any(problem.startswith("/deck ") for problem in problems), problems)


def fragment_id_problems(site):
    """A documentation body repeats no id of the page that loads it.

    The one-page app holds every view in one document, and the documentation script scrolls to
    `document.getElementById(hash)`. On October 16, 2026 the protocol audience view and the Serving and connections guide
    both had `protocol-versions`, so the guide's own contents link reached the hidden audience card and did not move.
    """
    problems = []
    for address, body in sorted(site.fragment_bodies.items()):
        shell, fragment = site.document(address), site.document(body)
        if shell is None or fragment is None:
            continue
        shell_ids = {item.attrs["id"] for item in shell.walk() if item.attrs.get("id")}
        repeated = sorted({item.attrs["id"] for item in fragment.walk() if item.attrs.get("id")} & shell_ids)
        if repeated:
            problems.append(f"{address}: the documentation body repeats the page's ids {repeated}")
    return problems


class DocumentationBodiesKeepTheirOwnIds(unittest.TestCase):
    """A link to a part of a documentation page lands on that page's heading."""

    @classmethod
    def setUpClass(cls):
        cls.site = served_site()

    def test_no_documentation_body_repeats_an_id_of_its_page(self):
        self.assertEqual(fragment_id_problems(self.site), [])

    def test_a_repeated_id_is_refused(self):
        def serve(address):
            answer = self.site.serve(address)
            if address == "/docs/serving-and-connections" and answer is not None:
                return answer[0].replace('id="protocol-version-choice"', 'id="protocol-versions"'), answer[1]
            return answer
        problems = fragment_id_problems(replace(self.site, serve=serve, parsed={}))
        self.assertTrue(any(problem.startswith("/docs/serving-and-connections:") and "protocol-versions" in problem
                            for problem in problems), problems)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--write-inventory", type=Path, help="write the inventory of the served website to a new file")
    parser.add_argument("--release", default="")
    parser.add_argument("--revision", default="")
    arguments, rest = parser.parse_known_args(argv)
    if arguments.write_inventory is None:
        return unittest.main(argv=[sys.argv[0], *rest])
    if not arguments.release or not arguments.revision:
        parser.error("an inventory names its release and its revision")
    inventory = inventory_of(served_site(), arguments.release, arguments.revision)
    with arguments.write_inventory.open("x", encoding="utf-8") as stream:
        json.dump(inventory, stream, indent=1)
        stream.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
