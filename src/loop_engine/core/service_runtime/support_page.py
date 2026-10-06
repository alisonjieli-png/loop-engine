"""The support page: where a person reaches Baltor for help, at `/support`.

Kind: pure rendering over the typed site map and one host setting. The transport asks `rendered` for the page after
the status pages find nothing. Nothing here reads a request, a credential or an account, and nothing calls a model.

OpenAI's plugin guidelines require customer support contact details where end users can reach the developer, and a
submitted app with a protocol server names an HTTPS support page (docs/guides/chatgpt-app.md lists the sources). The
page names only channels that work: the postal address the privacy notice and the footer already name, the public
issue tracker the privacy notice names for questions without personal data, the request for material every connected
tool can send, and the support email address once the host file names one (`ServiceHttpConfiguration.support_email`,
set when mail to it is delivered). It promises no response time.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape

ADDRESS = "/support"
VIEW = "support"
LABELLED_BY = "support-title"
#: The operator's postal address, as the privacy notice, the terms and the footer state it.
POSTAL_ADDRESS = "Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States"
#: The label of the public issue tracker among the distribution's project addresses (pyproject.toml owns the address).
ISSUES_LABEL = "issues"


def issues_address() -> str:
    """The public issue tracker the privacy notice names for questions without personal data, from the installed
    distribution's own metadata; empty when the distribution is not installed."""
    from .library_page import _project_urls
    for entry in _project_urls():
        label, _, address = entry.partition(",")
        if label.strip().lower() == ISSUES_LABEL and address.strip():
            return address.strip()
    return ""


def handles(address: str) -> bool:
    return address == ADDRESS


def support_body(support_email: str = "") -> str:
    """The page's own words. The email paragraph appears only when the host names a delivered address."""
    from .model_directory_pages import contents
    links = [("write", "Write to Baltor"), ("questions", "Questions without personal data"),
             ("material", "Material the library lacks"), ("yourself", "Fix a connection yourself"),
             ("chatgpt", "Baltor in ChatGPT"), ("data", "Your data")]
    email = (f'<p class="md-reading">Email <a href="mailto:{escape(support_email)}">{escape(support_email)}</a> for '
             "help with your account, sign-in, a connection or a download.</p>") if support_email else ""
    intro = ('<div class="md-band md-intro"><p class="eyebrow">Support</p><h1 id="support-title">Get help with Baltor</h1>'
             '<p class="lede">How to reach Baltor about your account, connecting a harness or ChatGPT, downloads and the '
             "library.</p>" + contents(links) + "</div>")
    write = ('<div class="md-band" id="write" aria-labelledby="write-title"><h2 id="write-title">Write to Baltor</h2>'
             + email + f'<p class="md-reading">Post reaches Baltor at {escape(POSTAL_ADDRESS)}.</p>'
             '<p class="md-reading">When a request was refused, include the reference the refusal shows. It starts '
             "with ref_ and names that one request. Never send a password or an access key.</p></div>")
    issues = issues_address()
    tracker = (f'<a href="{escape(issues)}">{escape(issues.split("://", 1)[-1])}</a>' if issues
               else "the issue tracker of the repository")
    questions = ('<div class="md-band" id="questions" aria-labelledby="questions-title"><h2 id="questions-title">Questions '
                 f'without personal data</h2><p class="md-reading">Ask on the public issue tracker: {tracker}. Everyone '
                 "can read it, so leave out personal data, keys and private project files.</p></div>")
    material = ('<div class="md-band" id="material" aria-labelledby="material-title"><h2 id="material-title">Material the '
                'library lacks</h2><p class="md-reading">Ask for it from your harness or from ChatGPT. The request reaches '
                "Baltor staff with your account.</p></div>")
    yourself = ('<div class="md-band" id="yourself" aria-labelledby="yourself-title"><h2 id="yourself-title">Fix a '
                'connection yourself</h2><p class="md-reading">The <a href="/docs/troubleshooting">troubleshooting guide'
                '</a> covers the common refusals. <a href="/setup">Get set up</a> has the setup for each harness, and '
                '<a href="/status">Service status</a> shows whether the service is working now.</p></div>')
    chatgpt = ('<div class="md-band" id="chatgpt" aria-labelledby="chatgpt-title"><h2 id="chatgpt-title">Baltor in ChatGPT'
               '</h2><p class="md-reading">Add Baltor from ChatGPT, then sign in with your Baltor account and allow the '
               "access the page lists. To disconnect it, remove Baltor in ChatGPT's settings.</p></div>")
    data = ('<div class="md-band md-quiet" id="data" aria-labelledby="data-title"><h2 id="data-title">Your data</h2>'
            '<p class="md-reading">To ask for your account or what you submitted to be deleted, write as above and name '
            'the account. The <a href="/privacy">privacy notice</a> says what Baltor stores and why, and the '
            '<a href="/terms">terms of service</a> apply to every connection.</p></div>')
    return intro + write + questions + material + yourself + chatgpt + data


def support_page(site_map, display_name: str, support_email: str = "") -> str:
    """The whole page, framed like the other pages the service renders on its own."""
    from .model_directory_pages import SCHEMA_CONTEXT, Page, breadcrumbs, canonical, frame
    entry = site_map.page(ADDRESS)
    if entry is None:
        raise ValueError(f"the site map does not list {ADDRESS}")
    structured = {"@context": SCHEMA_CONTEXT, "@type": "ContactPage", "name": entry.title,
                  "url": canonical(site_map, ADDRESS), "description": entry.description,
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), (entry.title, ADDRESS)))}
    return frame(site_map, display_name, Page(ADDRESS, VIEW, entry.title, entry.description,
                                              support_body(support_email), structured, LABELLED_BY))


@lru_cache(maxsize=8)
def _framed(display_name: str, support_email: str) -> bytes:
    from .web_site_map import load_site_map
    return support_page(load_site_map(), display_name, support_email).encode("utf-8")


def rendered(path: str, method: str, display_name: str, host: "str | None" = None, support_email: str = ""):
    """`(body, media_type)` for the support page on any hostname, or None for another address or method."""
    from . import web_pages
    if method not in ("GET", "HEAD") or not handles(path):
        return None
    body = _framed(display_name, support_email or "")
    head = web_pages.page_head(web_pages.packaged_site_map(), path, host, display_name)
    if head is not None:
        body = web_pages.with_page_head(body, head)
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE
