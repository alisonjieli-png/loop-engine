"""Checks that each page and each hostname says what it is before any script runs.

Kind: service self-test module. It reads the packaged site map through its
typed reader and the pages `web_pages.served_asset` serves, and it runs one
real service on a loopback socket that answers the hostnames of the site map
with the socket's port. No provider, no public address and no credential is
used.

Until September 24, 2026 every address served the homepage's title and
description, eight hostnames served the homepage byte for byte, `HEAD` was
answered only for packaged files, and `/robots.txt` and `/sitemap.xml` answered
404. Each rule below refuses one of those states, and each has a known-wrong
case beside it that the rule must report:

- every page of the site map is served with its own title, description,
  canonical address on the canonical hostname and shared-link tags, and a page
  a search engine may not list says so;
- every page of the one-page application is served with its own view shown
  and every other view hidden, so a reader without the script and a crawler
  that does not run it read that page, not the homepage;
- each hostname of the site map shows its own page at its root address: the
  root serves exactly what that page's own address serves on the hostname,
  a hostname whose page is not the homepage never serves the homepage's
  bytes, and a hostname the site map does not name shows the homepage;
- `robots.txt` and `sitemap.xml` list exactly what the site map lists;
- a page head is written once: the title, the description and the tags the
  service writes are taken out of a page's own head first, so a page with a
  file of its own, which may carry its own title or canonical address, still
  ends with one of each, and a page without one closing head tag is refused;
- over a real socket, the Host chooses the root page, `HEAD` answers like
  `GET` without a body, the two written files carry their types and
  validators, and a documentation body is marked as not to be listed alone.
"""
from __future__ import annotations

from dataclasses import replace
from html.parser import HTMLParser
import re
from xml.etree import ElementTree

from .web_pages import (GENERATED_WEB_FILES, HTML_MEDIA_TYPE, ROBOTS_DISALLOWED_PREFIXES, PageHeadError,
                        served_asset, with_page_head)
from .web_site_map import load_site_map

DISPLAY_NAME = "Baltor"
SITEMAP_NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
#: Hostnames the site map does not name, and the forms of a named one that must not match it.
UNNAMED_HOSTS = (None, "", "127.0.0.1:8765", "[::1]:80", "localhost:8000", "evil.docs.baltor.ai",
                 "docs.baltor.ai.evil", "docs-baltor.ai")


class _Head(HTMLParser):
    """The title and the head tags of a served page, read as a browser reads them."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head, self.in_title, self.titles, self.tags = False, False, [], []

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.in_head = True
        elif tag == "title" and self.in_head:
            self.in_title = True
            self.titles.append("")
        elif self.in_head and tag in ("meta", "link"):
            self.tags.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.titles[-1] += data


def read_head(body: bytes) -> dict:
    """The page's titles, descriptions, canonical addresses and the other head values, each as a list."""
    reader = _Head()
    reader.feed(body.decode("utf-8"))
    named = lambda key, value, field: [tag.get(field, "") for tag in reader.tags if tag.get(key) == value]
    return {"titles": reader.titles, "descriptions": named("name", "description", "content"),
            "canonical": named("rel", "canonical", "href"), "og_url": named("property", "og:url", "content"),
            "og_title": named("property", "og:title", "content"), "twitter": named("name", "twitter:card", "content"),
            "robots": named("name", "robots", "content"), "root": named("name", "baltor-root-address", "content")}


def head_problems(site_map, serve) -> list:
    """Every page whose served head does not say what the site map says about it.

    `serve(address, host)` answers `(body, media_type)` or None, as the service does.
    """
    problems = []
    for page in site_map.pages:
        answer = serve(page.address, None)
        if answer is None or answer[1] != HTML_MEDIA_TYPE:
            problems.append(f"{page.address}: not served as a page")
            continue
        head, canonical = read_head(answer[0]), site_map.canonical_origin + page.address
        expected = {"titles": [DISPLAY_NAME + " | " + page.title], "descriptions": [page.description],
                    "canonical": [canonical], "og_url": [canonical], "og_title": [DISPLAY_NAME + " | " + page.title],
                    "twitter": ["summary"], "robots": [] if page.indexed else ["noindex"]}
        for field, value in expected.items():
            if head[field] != value:
                problems.append(f"{page.address}: {field} is {head[field]!r}, and the site map gives {value!r}")
    return problems


_VIEW_TAG = re.compile(r'<section data-view="([a-z0-9-]+)"( hidden)?')


def view_problems(site_map, serve) -> list:
    """Every page whose served bytes do not show exactly its own view."""
    problems = []
    for page in site_map.pages:
        answer = serve(page.address, None)
        if answer is None or answer[1] != HTML_MEDIA_TYPE:
            continue
        shown = [view for view, hidden in _VIEW_TAG.findall(answer[0].decode("utf-8")) if not hidden]
        if shown != [page.view]:
            problems.append(f"{page.address}: the served page shows the views {shown}, and the site map gives {page.view!r}")
    return problems


def hostname_problems(site_map, serve) -> list:
    """Every hostname whose root does not show the page the site map names, and every unnamed one that is not the homepage."""
    problems, home = [], serve("/", None)
    if home is None:
        return ["the homepage is not served"]
    for surface in site_map.hostnames:
        answer = serve("/", surface.hostname)
        if answer is None:
            problems.append(f"{surface.hostname}: the root address is not served")
            continue
        head, canonical = read_head(answer[0]), site_map.canonical_origin + surface.address
        if head["canonical"] != [canonical]:
            problems.append(f"{surface.hostname}: the root names {head['canonical']}, and the site map gives {canonical}")
        own = serve(surface.address, surface.hostname)
        if own is None or own[0] != answer[0]:
            problems.append(f"{surface.hostname}: the root does not serve what {surface.address} serves on this hostname")
        if surface.address == "/":
            if answer[0] != home[0] or head["root"]:
                problems.append(f"{surface.hostname}: the root is not the homepage the site map gives it")
        else:
            if answer[0] == home[0]:
                problems.append(f"{surface.hostname}: the root serves the homepage byte for byte")
            if head["root"] != [surface.address]:
                problems.append(f"{surface.hostname}: the root does not tell the page script to show {surface.address}")
            other = serve(site_map.pages[1].address, surface.hostname)
            if other is None or read_head(other[0])["root"] != [surface.address]:
                problems.append(f"{surface.hostname}: a page other than the root does not name the hostname's root")
    for host in UNNAMED_HOSTS:
        answer = serve("/", host)
        if answer is None or answer[0] != home[0]:
            problems.append(f"{host!r}: a hostname the site map does not name shows something other than the homepage")
    return problems


def listing_problems(site_map, serve) -> list:
    """Differences between `robots.txt` and `sitemap.xml` as served and what the site map lists."""
    problems = []
    robots, sitemap = serve("/robots.txt", None), serve("/sitemap.xml", None)
    if robots is None or sitemap is None:
        return ["robots.txt or sitemap.xml is not served"]
    listed = [element.findtext(SITEMAP_NAMESPACE + "loc") for element in
              ElementTree.fromstring(sitemap[0]).findall(SITEMAP_NAMESPACE + "url")]
    wanted = [site_map.canonical_origin + page.address for page in site_map.indexed_pages()]
    if listed != wanted:
        problems.append(f"sitemap.xml lists {sorted(set(listed) ^ set(wanted))} differently from the site map")
    lines = robots[0].decode("utf-8").splitlines()
    disallowed = [line.split(":", 1)[1].strip() for line in lines if line.startswith("Disallow:")]
    expected = [*ROBOTS_DISALLOWED_PREFIXES, *(page.address for page in site_map.pages if not page.indexed)]
    if disallowed != expected:
        problems.append(f"robots.txt leaves out {sorted(set(disallowed) ^ set(expected))} differently from the site map")
    if "Sitemap: " + site_map.canonical_origin + "/sitemap.xml" not in lines or "User-agent: *" not in lines:
        problems.append("robots.txt does not name the site map for every crawler")
    if (robots[1], sitemap[1]) != (GENERATED_WEB_FILES["/robots.txt"], GENERATED_WEB_FILES["/sitemap.xml"]):
        problems.append("robots.txt or sitemap.xml is served with another media type")
    return problems


def _served(site_map=None):
    return lambda address, host: served_asset(address, "GET", DISPLAY_NAME, host, site_map)


def run_checks(check, root):
    site_map = load_site_map()
    serve = _served()
    check("every_site_map_page_is_served_with_its_own_head", not head_problems(site_map, serve))
    # Known-wrong case: every address serves the homepage's head, as every release up to 24 did.
    home_everywhere = lambda address, host: serve("/", None)
    check("head_check_rejects_every_address_serving_the_homepage_head",
          len(head_problems(site_map, home_everywhere)) >= len(site_map.pages) - 1)
    check("every_page_is_served_with_its_own_view_shown", not view_problems(site_map, serve))
    # Known-wrong case: every address served with the homepage shown, as every release up to 24 was.
    from .web_pages import HOME_VIEW
    homepage_shown = lambda address, host: (lambda answer: answer and (answer[0].replace(b"<section data-view=\"home\" hidden>", HOME_VIEW)
        .replace(b'data-view="' + site_map.page(address).view.encode() + b'"', b'data-view="' + site_map.page(address).view.encode() + b'" hidden', 1)
        if site_map.page(address) and site_map.page(address).view != "home" else answer[0], answer[1]))(serve(address, host))
    check("view_check_rejects_a_page_served_with_the_homepage_shown",
          len(view_problems(site_map, homepage_shown)) >= len([page for page in site_map.pages if page.view != "home"]) - 1)
    check("each_hostname_shows_its_own_page_at_its_root", not hostname_problems(site_map, serve))
    # Known-wrong cases: a service that ignores the Host, so the documentation, status, examples and
    # demonstration hostnames serve the homepage byte for byte (roadmap S-6.33), and one that matches a
    # hostname by its ending, so a stranger's subdomain would show the documentation.
    ignoring = lambda address, host: serve(address, None)
    surfaces = [surface for surface in site_map.hostnames if surface.address != "/"]
    by_ending = lambda address, host: serve(address, next((surface.hostname for surface in surfaces
                                                           if (host or "").endswith(surface.hostname)), host))
    check("hostname_check_rejects_a_service_that_ignores_the_host_or_matches_an_ending",
          len(surfaces) >= 4 and sum("byte for byte" in problem for problem in hostname_problems(site_map, ignoring))
          == len(surfaces) and any("evil.docs.baltor.ai" in problem for problem in hostname_problems(site_map, by_ending)))
    check("hostname_reading_ignores_the_port_the_case_and_a_final_dot",
          site_map.root_address("DOCS.Baltor.AI:443") == site_map.root_address("docs.baltor.ai.") == "/docs"
          and all(site_map.root_address(host) == "/" for host in UNNAMED_HOSTS))
    check("robots_and_sitemap_list_exactly_what_the_site_map_lists", not listing_problems(site_map, serve))
    # Known-wrong cases: a sitemap written from a site map that lost one listed page, and a robots
    # file written from one where an unlisted page became listed.
    lost = replace(site_map, pages=tuple(page for page in site_map.pages if page.address != "/status"))
    flipped = replace(site_map, pages=tuple(replace(page, indexed=True) if page.address == "/signup" else page
                                            for page in site_map.pages))
    check("listing_check_rejects_a_lost_page_and_a_page_that_became_listed",
          any("sitemap.xml" in problem for problem in listing_problems(site_map, _served(lost)))
          and any("robots.txt" in problem for problem in listing_problems(site_map, _served(flipped))))
    _head_written_once(check)
    _real_socket(check, site_map)


def _head_written_once(check):
    """A page's own title, description and head tags are replaced, not repeated; a page without a head is refused."""
    page = (b'<html><head><meta charset="utf-8"><TITLE>Own title</TITLE><meta content="Own words" name="description">'
            b"<link href='/own' rel='canonical'><meta property=\"og:title\" content=\"Own\"><title>Second</title>"
            b'<link rel="stylesheet" href="/assets/site.css"></head><body><h1>Page</h1></body></html>')
    head = {"title": "Baltor | T", "description": "D", "canonical": "https://baltor.ai/t", "indexed": False,
            "image": "https://baltor.ai/assets/favicon-192.png", "site_name": "Baltor", "root_address": "/"}
    written = with_page_head(page, head)
    shown = read_head(written)
    check("a_page_head_is_written_once_over_the_page_own_head",
          shown["titles"] == ["Baltor | T"] and shown["descriptions"] == ["D"] and shown["canonical"] == ["https://baltor.ai/t"]
          and shown["og_title"] == ["Baltor | T"] and shown["robots"] == ["noindex"] and b'href="/assets/site.css"' in written
          and b"<h1>Page</h1>" in written)
    # Known-wrong cases: a writer that adds the tags and leaves the page's own ones, and a page without one closing head tag.
    appended = page.replace(b"</head>", b'<title>Baltor | T</title><link rel="canonical" href="https://baltor.ai/t"></head>')
    repeated = read_head(appended)
    refused = 0
    for wrong in (page.replace(b"</head>", b""), page.replace(b"</head>", b"</head></head>")):
        try:
            with_page_head(wrong, head)
        except PageHeadError:
            refused += 1
    check("head_check_rejects_a_repeated_title_and_canonical_address_and_a_page_without_one_head",
          len(repeated["titles"]) == 3 and len(repeated["canonical"]) == 2 and refused == 2)


def _real_socket(check, site_map):
    import httpx
    from .access_checks import prepared
    from .http import ServiceHttpApplication
    from .http_test_fixtures import running_http
    import tempfile
    from pathlib import Path
    names = tuple(surface.hostname for surface in site_map.hostnames)
    with tempfile.TemporaryDirectory(prefix="service-web-surfaces-") as folder:
        (Path(folder) / "intelligence").mkdir()
        held = prepared(Path(folder) / "intelligence")
        factory = lambda config: ServiceHttpApplication(held.runtime, held.provisioning, config)
        with running_http(held, application_factory=factory, display_name=DISPLAY_NAME, hostnames=names) as (base, _):
            port = base.rsplit(":", 1)[1]
            fetch = lambda method, path, host=None, headers=None: httpx.request(
                method, base + path, trust_env=False, timeout=10,
                headers={**({"Host": f"{host}:{port}"} if host else {}), **(headers or {})})
            roots = {name: read_head(fetch("GET", "/", name).content)["canonical"] for name in names}
            loopback = read_head(fetch("GET", "/").content)["canonical"]
            check("hostname_roots_answer_over_a_real_socket",
                  all(roots[surface.hostname] == [site_map.canonical_origin + surface.address]
                      for surface in site_map.hostnames) and loopback == [site_map.canonical_origin + "/"])
            paths = ("/", "/status", "/demo", "/robots.txt", "/sitemap.xml", "/assets/service.css")
            pairs = [(fetch("GET", path, "docs.baltor.ai"), fetch("HEAD", path, "docs.baltor.ai")) for path in paths]
            check("head_answers_like_get_without_a_body", all(head_matches_get(got, head) for got, head in pairs))
            # Known-wrong case: a HEAD answer that carries the body, and one whose length disagrees.
            got, head = pairs[0]
            check("head_comparison_rejects_a_body_and_a_different_length",
                  not head_matches_get(got, _Answer(head.status_code, head.headers, b"x"))
                  and not head_matches_get(got, _Answer(head.status_code, {**head.headers, "content-length": "1"}, b"")))
            robots, sitemap = fetch("GET", "/robots.txt"), fetch("GET", "/sitemap.xml")
            again = fetch("GET", "/sitemap.xml", headers={"If-None-Match": sitemap.headers.get("etag", "")})
            check("robots_and_sitemap_are_served_with_their_types_and_validators",
                  robots.status_code == sitemap.status_code == 200
                  and robots.headers["content-type"].startswith("text/plain")
                  and sitemap.headers["content-type"].startswith("application/xml")
                  and bool(sitemap.headers.get("etag")) and again.status_code == 304
                  and sitemap.headers.get("cache-control") == "public, max-age=300")
            body = fetch("GET", "/assets/docs/what-baltor-is.html")
            page = fetch("GET", "/docs")
            check("a_documentation_body_is_not_listed_alone",
                  body.status_code == 200 and body.headers.get("x-robots-tag") == "noindex"
                  and "x-robots-tag" not in page.headers)


class _Answer:
    """A stand-in answer for a known-wrong case of the HEAD comparison."""

    def __init__(self, status_code, headers, content):
        self.status_code, self.headers, self.content = status_code, headers, content


def head_matches_get(got, head) -> bool:
    """HEAD answers with the status, type, length and validator of GET, and no body."""
    return (head.status_code == got.status_code == 200 and head.content == b""
            and head.headers.get("content-type") == got.headers.get("content-type")
            and head.headers.get("content-length") == str(len(got.content))
            and head.headers.get("etag") == got.headers.get("etag"))
