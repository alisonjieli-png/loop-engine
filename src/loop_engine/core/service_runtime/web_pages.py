"""The pages and files this service serves to a browser, and their addresses.

This module owns the served address table, the packaged files behind it, and
the page a reader sees at an address the service does not serve. It owns no
transport, no credential and no interface address; `http` keeps those.

It was separated from `http` on September 21, 2026, because that module had
grown past this repository's length convention and every new page made it
longer. Adding a page is now a change to a small module that serves pages.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from html import escape

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
    "/auth/callback": ("index.html", HTML_MEDIA_TYPE), "/auth/confirm": ("index.html", HTML_MEDIA_TYPE),
    "/docs": ("index.html", HTML_MEDIA_TYPE), "/how-it-works": ("index.html", HTML_MEDIA_TYPE),
    "/pricing": ("index.html", HTML_MEDIA_TYPE),
    "/waitlist": ("index.html", HTML_MEDIA_TYPE),
    "/assets/client-recipes.json": ("client-recipes.json", "application/json"),
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
    # The licence terms of the packaged browser library and the typefaces travel with them.
    "/assets/third-party-notices.txt": ("THIRD-PARTY-NOTICES.md", "text/plain"),
}
# Only declared, packaged non-page files are public cache entries. Browser
# account pages and every API response retain the transport's no-store rule.
CACHEABLE_WEB_ASSETS = frozenset(path for path, (_name, media) in WEB_ASSETS.items()
                                 if media != HTML_MEDIA_TYPE)
PUBLIC_ASSET_CACHE_CONTROL = "public, max-age=300"
MISSING_ADDRESS_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
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
                 for path in sorted(CACHEABLE_WEB_ASSETS))


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


def served_asset(path, method, display_name):
    """Return `(body, media_type)` for a served address, or None when this service serves none.

    The deployment's name is written into a served page here, so that a caller
    does not have to know which packaged files carry the placeholder.
    """
    if method not in ("GET", "HEAD") or path not in WEB_ASSETS:
        return None
    name, media_type = WEB_ASSETS[path]
    body = read_packaged_asset(name)
    if media_type == HTML_MEDIA_TYPE:
        body = body.replace(SERVICE_NAME_PLACEHOLDER, escape(display_name, quote=True).encode("utf-8"))
        body = version_asset_references(body)
    return body, media_type


def missing_address_page(display_name):
    """Return the bytes of the page a reader sees at an address this service does not serve.

    The page names no address and repeats nothing from the request, so nothing
    can be reflected into it.
    """
    return MISSING_ADDRESS_PAGE.format(name=escape(display_name)).encode("utf-8")
