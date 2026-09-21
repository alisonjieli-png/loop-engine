"""The served website addresses and the one response that serves them.

This module owns the table of public addresses the service answers with a
packaged file, and the single function that reads that file and returns it
with the browser protections every served page carries. It holds no tenant,
usage, authority or protocol decision: `http.ServiceHttpApplication` keeps
all of those and calls `web_asset_response` for the static branch alone.

Split out of `http.py` on 2026-09-21, when that module reached the 800-line
cap and a new page could not be added without moving this table first. The
move changed no address, no media type, no header and no byte of any page.
"""
from __future__ import annotations

from html import escape
from importlib.resources import files

HTML_MEDIA_TYPE = "text/html"
WEB_ASSETS = {
    "/": ("index.html", HTML_MEDIA_TYPE), "/app": ("index.html", HTML_MEDIA_TYPE),
    "/login": ("index.html", HTML_MEDIA_TYPE), "/signup": ("index.html", HTML_MEDIA_TYPE),
    "/account": ("index.html", HTML_MEDIA_TYPE),
    "/admin": ("index.html", HTML_MEDIA_TYPE),
    "/connect": ("index.html", HTML_MEDIA_TYPE),
    "/examples": ("index.html", HTML_MEDIA_TYPE),
    "/security": ("index.html", HTML_MEDIA_TYPE),
    "/auth/callback": ("index.html", HTML_MEDIA_TYPE),
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


def web_asset_headers(identity_origin: str = "") -> dict:
    """The browser protections every served file carries, with the one extra
    origin a configured browser identity provider is allowed to be called on."""
    return {
        "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'"
                                   + identity_origin + "; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
        "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}


def web_asset_body(path: str, display_name: str) -> tuple[bytes, str]:
    """The packaged bytes for a served address and their media type.

    An HTML page carries the host's configured service name in place of the
    `{{SERVICE_NAME}}` mark, escaped for an attribute as well as for text.
    """
    name, media_type = WEB_ASSETS[path]
    body = files("loop_engine").joinpath("core", "service_runtime", "web_assets", name).read_bytes()
    if media_type == HTML_MEDIA_TYPE:
        body = body.replace(b"{{SERVICE_NAME}}", escape(display_name, quote=True).encode("utf-8"))
    return body, media_type
