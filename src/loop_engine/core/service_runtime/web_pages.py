"""The pages and files this service serves to a browser, and their addresses.

This module owns the served address table, the packaged files behind it, and
the page a reader sees at an address the service does not serve. It owns no
transport, no credential and no interface address; `http` keeps those.

It was separated from `http` on September 21, 2026, because that module had
grown past this repository's length convention and every new page made it
longer. Adding a page is now a change to a small module that serves pages.

Since September 24, 2026 it also writes what a page says about itself before
it runs any script: its own title and description, its canonical address on
the canonical hostname, the tags a shared link shows, whether a search engine
may list it, and, on a hostname whose root is another page, which page that
root shows. It reads all of that from the typed site map (`web_site_map`), the
one record of the website's pages, and writes `robots.txt` and `sitemap.xml`
from the same record, so no second list of pages or hostnames exists.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from html import escape
import re

from .web_site_map import SiteMap, load_site_map

HTML_MEDIA_TYPE = "text/html"
#: The name of this deployment is written into a served page here. A packaged
#: page carries the placeholder; no packaged file carries a deployment's name.
SERVICE_NAME_PLACEHOLDER = b"{{SERVICE_NAME}}"
#: The directory inside the installed package that holds every served file.
PACKAGED_ASSET_DIRECTORY = ("core", "service_runtime", "web_assets")
#: Every address the website answers, with the packaged file it returns. A
#: single page application address answers with `index.html` and the browser
#: chooses the view; a page that stands on its own names its own file; an
#: `/assets/` address returns one named stylesheet, script or data file. The
#: service serves nothing else: not the repository, the source inventory, the
#: host configuration or an internal report.
WEB_ASSETS = {
    "/": ("index.html", HTML_MEDIA_TYPE), "/app": ("index.html", HTML_MEDIA_TYPE),
    "/login": ("index.html", HTML_MEDIA_TYPE), "/signup": ("index.html", HTML_MEDIA_TYPE),
    "/account": ("index.html", HTML_MEDIA_TYPE),
    "/admin": ("index.html", HTML_MEDIA_TYPE),
    "/connect": ("index.html", HTML_MEDIA_TYPE),
    # The guide, Get set up, and the sign-up funnel, Get started. "/connect" above stays the guide's older address.
    "/setup": ("index.html", HTML_MEDIA_TYPE), "/get-started": ("index.html", HTML_MEDIA_TYPE),
    "/examples": ("index.html", HTML_MEDIA_TYPE),
    "/security": ("index.html", HTML_MEDIA_TYPE),
    # The privacy notice the owner approved on September 22, 2026. Its words are
    # docs/legal/PRIVACY-NOTICE.md, and a browser check compares the two.
    "/privacy": ("index.html", HTML_MEDIA_TYPE),
    # The terms of service the owner approved on September 23, 2026. Their words
    # are docs/legal/TERMS-OF-SERVICE.md, and a browser check compares the two.
    "/terms": ("index.html", HTML_MEDIA_TYPE),
    # The deck the owner asked for on September 24, 2026, a page with a file of its own. deck.baltor.ai opens it at its
    # root once the hostname table routes that name; tools/test_deck_page.py holds every number on it to a saved record.
    "/deck": ("deck.html", HTML_MEDIA_TYPE),
    # The free public directory of MCP servers and agent APIs, a page that stands on its own outside the one-page
    # app; /mcp-directory is its second address. tools/build_mcp_directory.py writes its data files and the
    # generated parts of the page, and the page script reads the files listed at the end of this table.
    "/directory": ("directory.html", HTML_MEDIA_TYPE), "/mcp-directory": ("directory.html", HTML_MEDIA_TYPE),
    "/auth/callback": ("index.html", HTML_MEDIA_TYPE), "/auth/confirm": ("index.html", HTML_MEDIA_TYPE),
    "/docs": ("index.html", HTML_MEDIA_TYPE), "/how-it-works": ("index.html", HTML_MEDIA_TYPE),
    "/pricing": ("index.html", HTML_MEDIA_TYPE),
    # The three hero use cases the owner named on September 23, 2026, and their hub page.
    "/use-cases": ("index.html", HTML_MEDIA_TYPE), "/overnight": ("index.html", HTML_MEDIA_TYPE),
    "/efficiency": ("index.html", HTML_MEDIA_TYPE), "/learning": ("index.html", HTML_MEDIA_TYPE),
    "/waitlist": ("index.html", HTML_MEDIA_TYPE),
    # The four audience pages of the September 23 site map, restored on September 24, 2026.
    "/for/coding-agents": ("index.html", HTML_MEDIA_TYPE), "/for/engineering-teams": ("index.html", HTML_MEDIA_TYPE),
    "/for/comparing-tools": ("index.html", HTML_MEDIA_TYPE), "/for/protocol-and-client": ("index.html", HTML_MEDIA_TYPE),
    # The showcase of September 24, 2026: one task shown step by step, three case studies written from saved
    # evidence, and the service status read live. demo.baltor.ai and status.baltor.ai open two of them at their root.
    "/demo": ("index.html", HTML_MEDIA_TYPE), "/status": ("index.html", HTML_MEDIA_TYPE),
    # The second demonstration, a Kaggle competition from the metric to the submission, one of the three the homepage links.
    "/demo/kaggle": ("index.html", HTML_MEDIA_TYPE),
    "/case-studies/data-cleanup": ("index.html", HTML_MEDIA_TYPE),
    "/case-studies/pi-and-gemma-4": ("index.html", HTML_MEDIA_TYPE),
    "/case-studies/sign-up-protection": ("index.html", HTML_MEDIA_TYPE),
    "/assets/public-pages.css": ("public-pages.css", "text/css"),
    "/assets/public-pages.js": ("public-pages.js", "text/javascript"),
    "/assets/client-recipes.json": ("client-recipes.json", "application/json"),
    # The Baltor extension for Pi, one TypeScript file the Pi recipe tells a customer to save in .pi/extensions.
    # It is served as text so a browser shows it for reading before it is saved.
    "/assets/pi/baltor.ts": ("pi/baltor.ts", "text/plain; charset=utf-8"),
    "/assets/supabase-client.js": ("supabase-client.js", "text/javascript"),
    "/assets/service.css": ("service.css", "text/css"),
    "/assets/architecture.css": ("architecture.css", "text/css"),
    "/assets/client-access.js": ("client-access.js", "text/javascript"),
    "/assets/catalogue-browser.js": ("catalogue-browser.js", "text/javascript"),
    "/assets/service.js": ("service.js", "text/javascript"),
    "/assets/architecture-story.js": ("architecture-story.js", "text/javascript"),
    # The Documentation view. `documentation-index.json` decides which pages exist, their order, titles and
    # addresses; `tools/build_documentation_index.py` builds each page's body under `docs/` from the Markdown
    # guide the index names, and `tools/check_documentation_index.py` fails when this table, the index and the
    # built bodies disagree. Every page address opens the one page, so each keeps the site's header and footer.
    "/docs/what-baltor-is": ("index.html", HTML_MEDIA_TYPE),
    "/docs/your-account": ("index.html", HTML_MEDIA_TYPE),
    "/docs/searching-and-retrieving": ("index.html", HTML_MEDIA_TYPE),
    "/docs/usage-and-what-you-pay-for": ("index.html", HTML_MEDIA_TYPE),
    "/docs/troubleshooting": ("index.html", HTML_MEDIA_TYPE),
    "/docs/serving-and-connections": ("index.html", HTML_MEDIA_TYPE),
    # The setup guide is the Get set up page. This older documentation address opens it too.
    "/docs/getting-set-up": ("index.html", HTML_MEDIA_TYPE),
    "/assets/documentation-index.json": ("documentation-index.json", "application/json"),
    "/assets/documentation.js": ("documentation.js", "text/javascript"),
    "/assets/documentation.css": ("documentation.css", "text/css"),
    "/assets/docs/what-baltor-is.html": ("docs/what-baltor-is.html", HTML_MEDIA_TYPE),
    "/assets/docs/your-account.html": ("docs/your-account.html", HTML_MEDIA_TYPE),
    "/assets/docs/searching-and-retrieving.html": ("docs/searching-and-retrieving.html", HTML_MEDIA_TYPE),
    "/assets/docs/usage-and-what-you-pay-for.html": ("docs/usage-and-what-you-pay-for.html", HTML_MEDIA_TYPE),
    "/assets/docs/troubleshooting.html": ("docs/troubleshooting.html", HTML_MEDIA_TYPE),
    "/assets/docs/serving-and-connections.html": ("docs/serving-and-connections.html", HTML_MEDIA_TYPE),
    # The typefaces of the website, Geist and Geist Mono, served from this origin so that no
    # visitor's address reaches a font provider. Their licence travels in the notices below.
    "/assets/geist.woff2": ("geist.woff2", "font/woff2"),
    "/assets/geist-mono.woff2": ("geist-mono.woff2", "font/woff2"),
    # The mark of the website and its page icons, traced from variation 52 of the owner's logo sheet
    # of September 23, 2026. Replacing these four files changes it everywhere, because the header,
    # the footer and the icons all read them.
    "/assets/baltor-mark.svg": ("baltor-mark.svg", "image/svg+xml"),
    "/assets/favicon-32.png": ("favicon-32.png", "image/png"),
    "/assets/favicon-192.png": ("favicon-192.png", "image/png"),
    "/assets/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
    # The deck's stylesheet, script and the picture a shared link to it shows. tools/render_deck_card.mjs draws the picture.
    "/assets/deck.css": ("deck.css", "text/css"),
    "/assets/deck.js": ("deck.js", "text/javascript"),
    "/assets/deck-card.png": ("deck-card.png", "image/png"),
    # The licence terms of the packaged browser library and the typefaces travel with them.
    "/assets/third-party-notices.txt": ("THIRD-PARTY-NOTICES.md", "text/plain"),
    # The directory page's stylesheet, script and data: a manifest that names the columns and labels, and eight row
    # files. Their number is PART_COUNT in tools/mcp_directory/build.py, and `build_mcp_directory.py check` compares them.
    "/assets/directory.css": ("directory.css", "text/css"),
    "/assets/directory.js": ("directory.js", "text/javascript"),
    "/assets/directory/manifest.json": ("directory/manifest.json", "application/json"),
    "/assets/directory/rows-0.json": ("directory/rows-0.json", "application/json"),
    "/assets/directory/rows-1.json": ("directory/rows-1.json", "application/json"),
    "/assets/directory/rows-2.json": ("directory/rows-2.json", "application/json"),
    "/assets/directory/rows-3.json": ("directory/rows-3.json", "application/json"),
    "/assets/directory/rows-4.json": ("directory/rows-4.json", "application/json"),
    "/assets/directory/rows-5.json": ("directory/rows-5.json", "application/json"),
    "/assets/directory/rows-6.json": ("directory/rows-6.json", "application/json"),
    "/assets/directory/rows-7.json": ("directory/rows-7.json", "application/json"),
}
#: Files written from the site map rather than packaged, with their media types.
#: Each answers GET and HEAD like a packaged file, with a strong validator.
GENERATED_WEB_FILES = {
    "/robots.txt": "text/plain; charset=utf-8",
    "/sitemap.xml": "application/xml",
}
#: Addresses a crawler is asked to leave alone besides the unlisted pages: the
#: interface routes, the protocol endpoint and its authorization metadata, and
#: the counted links of the public lists at /out/ (public_links.py), which only
#: redirect to other sites.
ROBOTS_DISALLOWED_PREFIXES = ("/api/", "/mcp", "/.well-known/", "/out/")
# Only declared non-page files, packaged or generated, are public cache
# entries. Browser account pages and every API response retain the transport's
# no-store rule.
CACHEABLE_WEB_ASSETS = frozenset(path for path, (_name, media) in WEB_ASSETS.items()
                                 if media != HTML_MEDIA_TYPE) | frozenset(GENERATED_WEB_FILES)
PUBLIC_ASSET_CACHE_CONTROL = "public, max-age=300"
MISSING_ADDRESS_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{name} | Address not found</title><link rel="stylesheet" href="/assets/service.css"></head>
<body><main id="main" class="reading" style="padding:4rem 4vw">
<p class="eyebrow">Address not found</p>
<h1>This service has no page at that address.</h1>
<p class="lede">The address in your browser is not one {name} serves. It may have been
mistyped, or it may be an older address that has since changed. Nothing is wrong with
your account or your key.</p>
<div class="actions"><a class="button primary" href="/">Go to the home page</a>
<a class="button quiet" href="/docs">Open the setup guide</a></div>
<p class="caption">If you followed a link from {name} to get here, the link is wrong and
we would like to know. Tell the person who runs this service which page you came from.</p>
</main></body></html>
"""


def read_packaged_asset(name):
    """Return the exact bytes of one file packaged beside this module."""
    from importlib.resources import files
    return files("loop_engine").joinpath(*PACKAGED_ASSET_DIRECTORY, name).read_bytes()


def asset_etag(body):
    """A strong validator for the exact bytes, independent of filesystem dates."""
    return '"' + sha256(body).hexdigest() + '"'


@lru_cache(maxsize=1)
def packaged_asset_versions():
    """One immutable release's asset identities; a new image starts a new process."""
    return tuple((path, sha256(read_packaged_asset(WEB_ASSETS[path][0])).hexdigest())
                 for path in sorted(CACHEABLE_WEB_ASSETS) if path in WEB_ASSETS)


@lru_cache(maxsize=1)
def packaged_site_map():
    """The packaged site map, read once by its typed reader; a new release starts a new process."""
    return load_site_map()


#: The head elements this module writes into every page the site map lists, whether the page is a view of the one
#: page application or a file of its own. Any of them a page already carries, in any attribute order or quoting, is
#: taken out first, so a page never ends up with two titles, two descriptions or two canonical addresses.
_HEAD_END = re.compile(rb"</head\s*>", re.IGNORECASE)
_TITLE = re.compile(rb"\s*<title\b[^>]*>.*?</title\s*>", re.IGNORECASE | re.DOTALL)
#: A page file that carries its own shared-link picture (the deck's card) keeps it, shown as a large card.
_OWN_IMAGE = re.compile(rb"""<meta\b[^>]*\bproperty\s*=\s*["']og:image["'][^>]*\bcontent\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_OWN_IMAGE_ALT = re.compile(rb"""<meta\b[^>]*\bproperty\s*=\s*["']og:image:alt["'][^>]*\bcontent\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_WRITTEN_TAGS = re.compile(rb"""\s*<(?:meta\b[^>]*\b(?:name\s*=\s*["']?(?:description|robots|twitter:[^"'\s>]*|baltor-root-address)"""
                           rb"""|property\s*=\s*["']?og:[^"'\s>]*)|link\b[^>]*\brel\s*=\s*["']?canonical)\b[^>]*>""", re.IGNORECASE)


class PageHeadError(ValueError):
    """A page this module cannot write a head into, with the reason."""


def page_head(site_map: SiteMap, path: str, host: str | None, display_name: str):
    """The head values of the page an address shows on a hostname, or None for an address that is not a page.

    At the root address the Host decides the page, through the site map's
    hostname table; every other address shows its own page on every hostname.
    The canonical address is always on the canonical hostname.
    """
    root = site_map.root_address(host)
    address = root if path == "/" else path
    page = site_map.page(address)
    if page is None:
        return None
    return {"title": display_name + " | " + page.title, "description": page.description,
            "canonical": site_map.canonical_origin + page.address, "indexed": page.indexed,
            "image": site_map.canonical_origin + site_map.social_image, "site_name": display_name,
            "root_address": root, "view": page.view}


#: The one view the packaged one-page application shows before its script runs, and the mark of a hidden view.
HOME_VIEW = b'<section data-view="home">'
_HIDDEN_VIEW = b'<section data-view="%s" hidden'


def with_view_shown(body: bytes, view: str) -> bytes:
    """The one-page application with the page's own view shown and the homepage hidden, before any script runs.

    Until September 24, 2026 every address was served with the homepage shown,
    so a reader without the script and a crawler that does not run it saw the
    homepage at every address, and a reader with the script saw it flash first.
    A page that is not a view of the one-page application, or whose markers are
    not each found once, is returned unchanged.
    """
    hidden = _HIDDEN_VIEW % view.encode("ascii")
    if view == "home" or body.count(HOME_VIEW) != 1 or body.count(hidden) != 1:
        return body
    return body.replace(HOME_VIEW, b'<section data-view="home" hidden>', 1).replace(hidden, hidden[:-len(b" hidden")], 1)


def with_page_head(body: bytes, head) -> bytes:
    """The page bytes with its own title, description, canonical address and shared-link tags.

    The title, the description and every tag this module writes are taken out
    of the page's head wherever they stand, and written once just before the
    head closes. A page without exactly one closing head tag is refused, so a
    fragment or a broken page is never given a head in the wrong place.
    """
    ends = _HEAD_END.findall(body)
    if len(ends) != 1:
        raise PageHeadError("a page carries exactly one closing head tag")
    before, closing, after = body.partition(ends[0])
    own_image, own_alt = _OWN_IMAGE.search(before), _OWN_IMAGE_ALT.search(before)
    before = _WRITTEN_TAGS.sub(b"", _TITLE.sub(b"", before))
    value = lambda text: escape(text, quote=True).encode("utf-8")
    image = value(head["image"]) if own_image is None else own_image.group(1)
    tags = [b"<title>" + value(head["title"]) + b"</title>",
            b'<meta name="description" content="' + value(head["description"]) + b'">',
            b'<link rel="canonical" href="' + value(head["canonical"]) + b'">',
            b'<meta property="og:type" content="website">',
            b'<meta property="og:site_name" content="' + value(head["site_name"]) + b'">',
            b'<meta property="og:title" content="' + value(head["title"]) + b'">',
            b'<meta property="og:description" content="' + value(head["description"]) + b'">',
            b'<meta property="og:url" content="' + value(head["canonical"]) + b'">',
            b'<meta property="og:image" content="' + image + b'">',
            b'<meta name="twitter:card" content="' + (b"summary" if own_image is None else b"summary_large_image") + b'">']
    if own_image is not None:
        tags.append(b'<meta name="twitter:image" content="' + image + b'">')
        if own_alt is not None:
            tags.append(b'<meta property="og:image:alt" content="' + own_alt.group(1) + b'">')
    if not head["indexed"]:
        tags.append(b'<meta name="robots" content="noindex">')
    if head["root_address"] != "/":
        tags.append(b'<meta name="baltor-root-address" content="' + value(head["root_address"]) + b'">')
    return before.rstrip() + b"\n" + b"".join(b"  " + tag + b"\n" for tag in tags) + closing + after


def robots_text(site_map: SiteMap) -> bytes:
    """`robots.txt`: the unlisted pages and the interface routes are left alone, and the site map is named."""
    lines = ["# " + site_map.display_name + ". Written from the website's site map; do not edit by hand.",
             "User-agent: *"]
    lines += ["Disallow: " + prefix for prefix in ROBOTS_DISALLOWED_PREFIXES]
    lines += ["Disallow: " + page.address for page in site_map.pages if not page.indexed]
    lines += ["", "Sitemap: " + site_map.canonical_origin + "/sitemap.xml"]
    return ("\n".join(lines) + "\n").encode("utf-8")


def sitemap_xml(site_map: SiteMap) -> bytes:
    """`sitemap.xml`: every page a search engine may list, at its canonical address, in site map order."""
    rows = ["  <url><loc>" + escape(site_map.canonical_origin + page.address, quote=False) + "</loc></url>"
            for page in site_map.indexed_pages()]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n").encode("utf-8")


GENERATORS = {"/robots.txt": robots_text, "/sitemap.xml": sitemap_xml}


def version_asset_references(body):
    """Fresh pages select fresh assets even while browsers cache the earlier release."""
    for path, version in packaged_asset_versions():
        body = body.replace(('"' + path + '"').encode(),
                            ('"' + path + '?v=' + version + '"').encode())
    return body


def validator_matches(value, etag):
    """GET/HEAD If-None-Match uses weak comparison and permits a validator list."""
    return any(part.strip() == "*" or part.strip().removeprefix("W/") == etag
               for part in value.split(","))


def served_asset(path, method, display_name, host=None, site_map=None):
    """Return `(body, media_type)` for a served address, or None when this service serves none.

    The deployment's name is written into a served page here, so that a caller
    does not have to know which packaged files carry the placeholder. So are the
    page's own head values, for the page the address shows on the request's
    Host. `site_map` replaces the packaged site map for a check only.
    """
    if method not in ("GET", "HEAD"):
        return None
    site_map = site_map or packaged_site_map()
    if path in GENERATED_WEB_FILES:
        return GENERATORS[path](site_map), GENERATED_WEB_FILES[path]
    if path not in WEB_ASSETS:
        return None
    # A hostname whose root is another page serves that page's own file at its root, so a page with a file of its
    # own opens there as surely as a view of the one page application does.
    root = site_map.root_address(host) if path == "/" else path
    name, media_type = WEB_ASSETS[root if root in WEB_ASSETS else path]
    body = read_packaged_asset(name)
    if media_type == HTML_MEDIA_TYPE:
        body = body.replace(SERVICE_NAME_PLACEHOLDER, escape(display_name, quote=True).encode("utf-8"))
        body = version_asset_references(body)
        head = page_head(site_map, path, host, display_name)
        if head is not None:
            body = with_view_shown(with_page_head(body, head), head["view"])
    return body, media_type


def missing_address_page(display_name):
    """Return the bytes of the page a reader sees at an address this service does not serve.

    The page names no address and repeats nothing from the request, so nothing
    can be reflected into it.
    """
    return MISSING_ADDRESS_PAGE.format(name=escape(display_name)).encode("utf-8")
