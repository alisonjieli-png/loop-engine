"""The website address table and the packaged files each address returns.

This module owns which addresses the website serves and which packaged file
each one returns. It does not decide who may call, what a refusal says or how
a response is built: `ServiceHttpApplication` in `http.py` remains the single
transport authority and keeps its route dispatch.

Nothing here reads a request. `serve_web_asset` takes an address and the host's
display name and returns bytes with their media type, so that the transport
stays the only module that touches Starlette.
"""
from __future__ import annotations

HTML_MEDIA_TYPE = "text/html"
#: Every address the website answers, with the packaged file it returns. A page
#: address returns the single-page application; an `/assets/` address returns
#: one named stylesheet, script or data file. The adapter serves nothing else:
#: not the repository, the source inventory, the host configuration or an
#: internal report.
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


def serve_web_asset(path, display_name):
    """Return the bytes and media type one website address serves, or None.

    The host's display name replaces the one placeholder in a page, escaped for
    an attribute, so that a self-hosted installation shows its own name. A file
    that is not a page is returned unchanged.
    """
    selected = WEB_ASSETS.get(path)
    if selected is None:
        return None
    from html import escape
    from importlib.resources import files
    name, media_type = selected
    body = files("loop_engine").joinpath("core", "service_runtime", "web_assets", name).read_bytes()
    if media_type == HTML_MEDIA_TYPE:
        body = body.replace(b"{{SERVICE_NAME}}", escape(display_name, quote=True).encode("utf-8"))
    return body, media_type


def missing_address_page(display_name):
    """Return the page a browser gets for an address this service does not serve."""
    from html import escape
    return MISSING_ADDRESS_PAGE.format(name=escape(display_name)).encode("utf-8")
