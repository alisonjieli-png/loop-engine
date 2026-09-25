"""The shared header and footer of a page that stands on its own, copied from the one-page app as it is served.

Kind: pure function over one packaged file. `index.html` holds the website's header and footer, and the
typed site map's checks hold both to the site map. A page the service renders on its own (the model
directory, the endpoint directory and the can-I-run tool) copies both from `index.html` here, byte for byte
apart from the deployment's name, so it shows the same header, the same phone menu and the same footer as
every other page, and a change to them reaches it at once. The page's own script drives the menu button,
the appearance button and the status line the way the site's scripts do.

Nothing here serves a page, reads a request or opens a connection.
"""
from __future__ import annotations

import re
from functools import lru_cache
from html import escape

SERVICE_NAME_PLACEHOLDER = "{{SERVICE_NAME}}"
_HEADER = re.compile(r'<header class="header">[\s\S]*?</header>')
_FOOTER = re.compile(r'<footer class="site-footer">[\s\S]*?</footer>')


class SharedChromeError(ValueError):
    """The one-page app no longer holds exactly one shared header and one shared footer to copy."""


def chrome_from_index(index_html: str, display_name: str) -> "tuple[str, str]":
    """The header and footer of index.html, with the deployment's name written in."""
    headers, footers = _HEADER.findall(index_html), _FOOTER.findall(index_html)
    if len(headers) != 1 or len(footers) != 1:
        raise SharedChromeError("index.html holds one shared header and one shared footer to copy")
    name = escape(display_name, quote=True)
    return headers[0].replace(SERVICE_NAME_PLACEHOLDER, name), footers[0].replace(SERVICE_NAME_PLACEHOLDER, name)


@lru_cache(maxsize=4)
def shared_chrome(display_name: str) -> "tuple[str, str]":
    """The packaged index.html's header and footer, read once per deployment name."""
    from importlib.resources import files
    index_html = files("loop_engine").joinpath("core", "service_runtime", "web_assets", "index.html").read_text(encoding="utf-8")
    return chrome_from_index(index_html, display_name)
