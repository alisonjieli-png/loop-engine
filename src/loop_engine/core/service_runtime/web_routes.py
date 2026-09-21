"""The website address table and the one branch that serves a packaged file.

`http.py` stays the single transport authority: it decides who may call an
address, applies the request limit, sets the page headers and dispatches. This
module owns only the fixed map from a public address to the packaged file that
answers it, the reading of that file, and the page a browser is given for an
address the service does not serve.

Splitting it out was the plan recorded against `core/service_runtime/http.py`
in `forbidden_paths.json`: that file passed the 800 line convention as each new
page added one row to this table, and a table of addresses is not transport
logic. Nothing here authenticates, meters or decides authority.
"""
from __future__ import annotations

HTML_MEDIA_TYPE = "text/html"
#: Every address the website serves, and the packaged file that answers it. A
#: single page application address answers with `index.html` and the browser
#: chooses the view; a page that stands on its own names its own file.
WEB_ASSETS = {
    "/": ("index.html", HTML_MEDIA_TYPE), "/app": ("index.html", HTML_MEDIA_TYPE),
    "/login": ("index.html", HTML_MEDIA_TYPE), "/signup": ("index.html", HTML_MEDIA_TYPE),
    "/account": ("index.html", HTML_MEDIA_TYPE),
    "/admin": ("index.html", HTML_MEDIA_TYPE),
    "/connect": ("index.html", HTML_MEDIA_TYPE),
    "/examples": ("index.html", HTML_MEDIA_TYPE),
    "/security": ("index.html", HTML_MEDIA_TYPE),
    "/auth/callback": ("index.html", HTML_MEDIA_TYPE), "/auth/confirm": ("index.html", HTML_MEDIA_TYPE),
    "/docs": ("index.html", HTML_MEDIA_TYPE), "/how-it-works": ("index.html", HTML_MEDIA_TYPE),
    "/pricing": ("index.html", HTML_MEDIA_TYPE),
    "/assets/client-recipes.json": ("client-recipes.json", "application/json"),
    "/assets/supabase-client.js": ("supabase-client.js", "text/javascript"),
    "/assets/service.css": ("service.css", "text/css"),
    "/assets/architecture.css": ("architecture.css", "text/css"),
    "/assets/client-access.js": ("client-access.js", "text/javascript"),
    "/assets/service.js": ("service.js", "text/javascript"),
    "/assets/architecture-story.js": ("architecture-story.js", "text/javascript"),
    # The licence terms of the packaged browser library travel with it.
    "/assets/third-party-notices.txt": ("THIRD-PARTY-NOTICES.md", "text/plain"),
}
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


def web_asset_bytes(path: str, display_name: str) -> "tuple[bytes, str]":
    """The packaged bytes and media type this address serves, with the service
    name written into a page. The caller has already decided that the address
    is served and that the caller may have it."""
    name, media_type = WEB_ASSETS[path]
    from html import escape
    from importlib.resources import files
    body = files("loop_engine").joinpath("core", "service_runtime", "web_assets", name).read_bytes()
    if media_type == HTML_MEDIA_TYPE:
        body = body.replace(b"{{SERVICE_NAME}}", escape(display_name, quote=True).encode("utf-8"))
    return body, media_type


def missing_address_page(display_name: str) -> bytes:
    """The page a browser is given for an address this service does not serve.
    It names no address and repeats nothing from the request, so nothing from
    the request can be reflected into it."""
    from html import escape
    return MISSING_ADDRESS_PAGE.format(name=escape(display_name)).encode("utf-8")
