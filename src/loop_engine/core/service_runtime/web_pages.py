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
# Only this public example may be embedded by another page on this service.
CREATIVE_PREVIEW_PATH = "/assets/creative-arena/index.html"
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
    "/demo/ashen-wilds": ("index.html", HTML_MEDIA_TYPE),
    "/assets/creative-arena/index.html": ("creative-arena/index.html", HTML_MEDIA_TYPE),
    "/assets/creative-arena/arena.js": ("creative-arena/arena.js", "text/javascript"),
    "/assets/creative-arena/arena.css": ("creative-arena/arena.css", "text/css"),
    "/assets/creative-arena/asset-briefs.json": ("creative-arena/asset-briefs.json", "application/json"),
    "/assets/creative-arena/blender-import.py": ("creative-arena/blender-import.py.txt", "text/plain"),
    "/assets/creative-arena/THREE-LICENSE.txt": ("creative-arena/THREE-LICENSE.txt", "text/plain"),
    "/": ("index.html", HTML_MEDIA_TYPE), "/app": ("index.html", HTML_MEDIA_TYPE),
    "/login": ("index.html", HTML_MEDIA_TYPE), "/signup": ("index.html", HTML_MEDIA_TYPE),
    "/account": ("index.html", HTML_MEDIA_TYPE),
    "/admin": ("index.html", HTML_MEDIA_TYPE),
    # The staff Systems view (roadmap S-6.35.11). The page holds no data; GET /api/v1/admin/systems answers staff only.
    "/admin/systems": ("index.html", HTML_MEDIA_TYPE),
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
    "/top-mcps": ("index.html", HTML_MEDIA_TYPE),
    "/assets/top-mcps.json": ("top-mcps.json", "application/json"),
    "/auth/callback": ("index.html", HTML_MEDIA_TYPE), "/auth/confirm": ("index.html", HTML_MEDIA_TYPE),
    "/oauth/consent": ("index.html", HTML_MEDIA_TYPE),
    "/assets/oauth-consent.js": ("oauth-consent.js", "text/javascript"),
    "/assets/staff-work.js": ("staff-work.js", "text/javascript"),
    "/assets/systems-view.js": ("systems-view.js", "text/javascript"),
    "/assets/public-good.js": ("public-good.js", "text/javascript"),
    "/assets/public-good.css": ("public-good.css", "text/css"),
    "/docs": ("index.html", HTML_MEDIA_TYPE), "/how-it-works": ("index.html", HTML_MEDIA_TYPE),
    "/pricing": ("index.html", HTML_MEDIA_TYPE),
    # The three hero use cases the owner named on September 23, 2026, and their hub page.
    "/use-cases": ("index.html", HTML_MEDIA_TYPE), "/overnight": ("index.html", HTML_MEDIA_TYPE),
    "/efficiency": ("index.html", HTML_MEDIA_TYPE), "/learning": ("index.html", HTML_MEDIA_TYPE),
    "/waitlist": ("index.html", HTML_MEDIA_TYPE),
    # The four audience pages of the September 23 site map, restored on September 24, 2026.
    "/for/coding-agents": ("index.html", HTML_MEDIA_TYPE), "/for/engineering-teams": ("index.html", HTML_MEDIA_TYPE),
    "/for/designers": ("index.html", HTML_MEDIA_TYPE),
    "/worker": ("index.html", HTML_MEDIA_TYPE),
    "/assets/worker-compose.yaml": ("worker-compose.yaml", "application/yaml"),
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
    "/assets/run-desk.js": ("run-desk.js", "text/javascript"),
    "/assets/run-desk-core.js": ("run-desk-core.js", "text/javascript"),
    # The shared footer's disclosure groups and its compact form in the signed-in views, on every page that carries the
    # shared header and footer. The orange design of September 26, 2026.
    "/assets/site-chrome.js": ("site-chrome.js", "text/javascript"),
    "/assets/client-recipes.json": ("client-recipes.json", "application/json"),
    # The Baltor extension for Pi, one TypeScript file the Pi recipe tells a customer to save in .pi/extensions.
    # It is served as text so a browser shows it for reading before it is saved.
    "/assets/pi/baltor.ts": ("pi/baltor.ts", "text/plain; charset=utf-8"),
    # The Baltor library skill for Claude Code, Codex, OpenCode and Pi: the six files of integrations/baltor-library
    # byte for byte, and their digests, which the protocol quickstarts install with curl and sha256sum. Its client
    # places a fetched skill byte for byte, so no model retypes a download (September 27, 2026). Every file is packaged
    # with a .txt name, so no source scanner reads the copies as source or documentation of this package. tools/test_baltor_library_integration.py holds every
    # served byte to the integration folder.
    "/assets/baltor-library/SKILL.md": ("baltor-library/SKILL.md.txt", "text/plain; charset=utf-8"),
    "/assets/baltor-library/LICENSE": ("baltor-library/LICENSE.txt", "text/plain; charset=utf-8"),
    "/assets/baltor-library/scripts/baltor.py": ("baltor-library/scripts/baltor.py.txt", "text/plain; charset=utf-8"),
    "/assets/baltor-library/references/client.md": ("baltor-library/references/client.md.txt",
                                                     "text/plain; charset=utf-8"),
    "/assets/baltor-library/assets/client.example.json": ("baltor-library/assets/client.example.json.txt",
                                                          "application/json"),
    "/assets/baltor-library/verification/test_client.py": ("baltor-library/verification/test_client.py.txt",
                                                           "text/plain; charset=utf-8"),
    "/assets/baltor-library/SHA256SUMS": ("baltor-library/SHA256SUMS.txt", "text/plain; charset=utf-8"),
    "/assets/supabase-client.js": ("supabase-client.js", "text/javascript"),
    "/assets/service.css": ("service.css", "text/css"),
    "/assets/architecture.css": ("architecture.css", "text/css"),
    "/assets/client-access.js": ("client-access.js", "text/javascript"),
    # Saved feeds for agents on the account page (customer_feeds.py); its section stays hidden unless the host
    # switches saved feeds on.
    "/assets/customer-feeds.js": ("customer-feeds.js", "text/javascript"),
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
    "/docs/component-concepts": ("index.html", HTML_MEDIA_TYPE),
    "/docs/container-worker": ("index.html", HTML_MEDIA_TYPE),
    "/docs/updates-and-withdrawals": ("index.html", HTML_MEDIA_TYPE),
    "/docs/common-questions": ("index.html", HTML_MEDIA_TYPE),
    # The setup guide is the Get set up page. This older documentation address opens it too.
    "/docs/getting-set-up": ("index.html", HTML_MEDIA_TYPE),
    # One quickstart for each harness (roadmap S-6.202), built from docs/guides/quickstart-*.md like the pages above
    # and run against the live service every night by tools/check_quickstarts.py.
    "/docs/quickstart-claude-code": ("index.html", HTML_MEDIA_TYPE),
    "/docs/quickstart-codex": ("index.html", HTML_MEDIA_TYPE),
    "/docs/quickstart-opencode": ("index.html", HTML_MEDIA_TYPE),
    "/docs/quickstart-pi": ("index.html", HTML_MEDIA_TYPE),
    "/docs/quickstart-baltor-harness": ("index.html", HTML_MEDIA_TYPE),
    "/assets/documentation-index.json": ("documentation-index.json", "application/json"),
    "/assets/documentation.js": ("documentation.js", "text/javascript"),
    "/assets/documentation.css": ("documentation.css", "text/css"),
    "/assets/docs/what-baltor-is.html": ("docs/what-baltor-is.html", HTML_MEDIA_TYPE),
    "/assets/docs/your-account.html": ("docs/your-account.html", HTML_MEDIA_TYPE),
    "/assets/docs/searching-and-retrieving.html": ("docs/searching-and-retrieving.html", HTML_MEDIA_TYPE),
    "/assets/docs/usage-and-what-you-pay-for.html": ("docs/usage-and-what-you-pay-for.html", HTML_MEDIA_TYPE),
    "/assets/docs/troubleshooting.html": ("docs/troubleshooting.html", HTML_MEDIA_TYPE),
    "/assets/docs/serving-and-connections.html": ("docs/serving-and-connections.html", HTML_MEDIA_TYPE),
    "/assets/docs/component-concepts.html": ("docs/component-concepts.html", HTML_MEDIA_TYPE),
    "/assets/docs/container-worker.html": ("docs/container-worker.html", HTML_MEDIA_TYPE),
    "/assets/docs/updates-and-withdrawals.html": ("docs/updates-and-withdrawals.html", HTML_MEDIA_TYPE),
    "/assets/docs/common-questions.html": ("docs/common-questions.html", HTML_MEDIA_TYPE),
    "/assets/docs/quickstart-claude-code.html": ("docs/quickstart-claude-code.html", HTML_MEDIA_TYPE),
    "/assets/docs/quickstart-codex.html": ("docs/quickstart-codex.html", HTML_MEDIA_TYPE),
    "/assets/docs/quickstart-opencode.html": ("docs/quickstart-opencode.html", HTML_MEDIA_TYPE),
    "/assets/docs/quickstart-pi.html": ("docs/quickstart-pi.html", HTML_MEDIA_TYPE),
    "/assets/docs/quickstart-baltor-harness.html": ("docs/quickstart-baltor-harness.html", HTML_MEDIA_TYPE),
    # The typefaces of the website, Geist and Geist Mono, served from this origin so that no
    # visitor's address reaches a font provider. Their licence travels in the notices below.
    "/assets/geist.woff2": ("geist.woff2", "font/woff2"),
    "/assets/geist-mono.woff2": ("geist-mono.woff2", "font/woff2"),
    # The mark of the website and its page icons, traced from variation 52 of the owner's logo sheet
    # of September 23, 2026. Replacing these four files changes it everywhere, because the header,
    # the footer and the icons all read them.
    "/assets/baltor-mark.svg": ("baltor-mark.svg", "image/svg+xml"),
    "/assets/procedural-bear-preview.svg": ("procedural-bear-preview.svg", "image/svg+xml"),
    "/assets/procedural-tree-preview.svg": ("procedural-tree-preview.svg", "image/svg+xml"),
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
    # The model directory at /models, /endpoints and /can-i-run: its stylesheet, its script and the two compact indexes
    # that its search and its hardware check read. The pages themselves, and one page for each model and endpoint, are
    # rendered by model_directory_pages.py from the records in model-directory/; the transport asks it for them.
    "/assets/model-directory.css": ("model-directory.css", "text/css"),
    "/assets/model-directory.js": ("model-directory.js", "text/javascript"),
    "/assets/feed-specimen.js": ("feed-specimen.js", "text/javascript"),
    "/assets/feed-profile.js": ("feed-profile.js", "text/javascript"),
    "/assets/feed-profile.css": ("feed-profile.css", "text/css"),
    "/assets/model-directory/search-index.json": ("model-directory/search-index.json", "application/json"),
    "/assets/model-directory/fit-index.json": ("model-directory/fit-index.json", "application/json"),
    # The guide pages of Agent Feeds and Harness Files (offering_guides.py) and the gallery (gallery_page.py), October 9,
    # 2026: their one stylesheet and one script, which adds copy buttons and the gallery's kind filters.
    "/assets/offering-pages.css": ("offering-pages.css", "text/css"),
    "/assets/offering-pages.js": ("offering-pages.js", "text/javascript"),
    "/assets/gallery-random.css": ("gallery-random.css", "text/css"),
    "/assets/gallery-random.js": ("gallery-random.js", "text/javascript"),
    # The pictures a shared link shows, 1200 by 630 pixels each, drawn from the brand mark, the site's own type and the
    # gallery's renders by tools/render_share_cards.mjs: the one-page site's views, Use Agent Feeds, Harness Files and
    # the gallery. Each page names its own card in its head, which with_page_head keeps.
    "/assets/share-card.png": ("share-card.png", "image/png"),
    "/assets/share-card-feeds.png": ("share-card-feeds.png", "image/png"),
    "/assets/share-card-harness-files.png": ("share-card-harness-files.png", "image/png"),
    "/assets/share-card-gallery.png": ("share-card-gallery.png", "image/png"),
}


def _gallery_previews():
    """The gallery's preview images, one WebP for each public item with a recorded render, read from its record."""
    from .gallery_records import preview_assets
    from .gallery_media import media_assets
    return {**preview_assets(), **media_assets()}


WEB_ASSETS.update(_gallery_previews())
#: Packaged files whose names already carry their content digest. A page names them as they are; adding `?v=` again
#: would only repeat the digest, and the gallery's 329 previews would add 17 ms to every page render.
CONTENT_ADDRESSED_PREFIXES = ("/assets/gallery/", "/assets/gallery-media/")
#: Files written from the site map rather than packaged, with their media types.
#: Each answers GET and HEAD like a packaged file, with a strong validator.
GENERATED_WEB_FILES = {
    "/robots.txt": "text/plain; charset=utf-8",
    "/sitemap.xml": "application/xml",
    # A plain-text guide for agents (llmstxt.org): what Baltor is, how to connect, the read routes, the feeds and the
    # licence rules, written from the site map and the packaged feed directory (October 9, 2026).
    "/llms.txt": "text/plain; charset=utf-8",
}
#: Addresses a crawler is asked to leave alone besides the unlisted pages: the
#: interface routes, the protocol endpoint and its authorization metadata, and
#: the counted links of the public lists at /out/ (public_links.py), which only
#: redirect to other sites.
ROBOTS_DISALLOWED_PREFIXES = ("/api/", "/mcp", "/.well-known/", "/out/")
# These unlisted public briefs must remain fetchable by the owner's Dot.
# Their noindex metadata and sitemap exclusion, not a crawl ban, keep them unlisted.
CRAWLABLE_UNLISTED_PAGES = frozenset({"/dot-context", "/dot-feedback"})
#: Site map files written elsewhere that robots.txt names beside /sitemap.xml: the model directory's list of its model
#: and endpoint pages, which are rendered from records rather than listed in the site map record.
EXTRA_SITEMAPS = ("/models/sitemap.xml", "/gallery/sitemap.xml")
# Only declared non-page files, packaged or generated, are public cache
# entries. Browser account pages and every API response retain the transport's
# no-store rule.
CACHEABLE_WEB_ASSETS = frozenset(path for path, (_name, media) in WEB_ASSETS.items()
                                 if media != HTML_MEDIA_TYPE) | frozenset(GENERATED_WEB_FILES)
PUBLIC_ASSET_CACHE_CONTROL = "public, max-age=300"
#: The frame of the two pages the service writes for a reader in a browser when it cannot show the page asked for: the
#: missing address and the failure on the service's side. Both carry the orange design of September 26, 2026: the brand
#: mark and name above, the status number, one plain sentence, the way back, and the operator's line below. They load
#: only the site's own stylesheets, because their Content-Security-Policy allows no inline style, and no script, so they
#: read the same when the page script cannot load.
_STATUS_PAGE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{name} | {title}</title><link rel="stylesheet" href="/assets/service.css"><link rel="stylesheet" href="/assets/architecture.css">
<link rel="icon" type="image/svg+xml" href="/assets/baltor-mark.svg"></head>
<body class="status-page-body"><div class="status-page-top"><a class="status-page-brand" href="/"><img src="/assets/baltor-mark.svg" width="30" height="30" alt=""><span>{name}</span></a></div>
<main id="main" class="status-page" data-status-page="{kind}">
<p class="status-page-code">{code}</p>
{body}
</main>
<div class="status-page-foot"><p>\u00a9 2026 Baltor.AI \u00b7 1428 Bryn Mawr St, Saxton, PA 16678</p>
<p class="status-page-links"><a href="/status">Status</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a></p></div>
</body></html>
"""
MISSING_ADDRESS_PAGE = """<h1>There is no page at this address.</h1>
<p class="lede">The address in your browser is not one {name} serves. It may have been
mistyped, or it may be an older address that has since changed. Nothing is wrong with
your account or your key.</p>
<div class="actions"><a class="button" href="/">Go home</a>
<a class="button" href="/docs">Search the docs</a></div>
<p class="caption">If you followed a link from {name} to get here, the link is wrong and
we would like to know. Tell the person who runs this service which page you came from.</p>
"""
#: The page at an address the website served once and has removed on purpose. It says why, in words the caller wrote
#: from its own record, and gives the way back to the list the page belonged to.
GONE_ADDRESS_PAGE = """<h1>{heading}</h1>
<p class="lede">{reason}</p>
<div class="actions"><a class="button" href="{back}">{back_label}</a>
<a class="button" href="/">Go home</a></div>
"""
#: The page for a failure on the service's side. Its sentences are the refusal wording of refusals.py for the exact code
#: and status, so the page and the record a program reads say the same thing. The reference is the one the service
#: issued for this request and recorded before answering; the page repeats nothing from the request.
SERVER_ERROR_PAGE = """<h1>Something broke on our side.</h1>
<p class="lede">{message} Nothing ran on your computer.</p>
<p>{action}</p>
<div class="actions"><a class="button" href="/status">Check the service status</a>
<a class="button" href="/">Go to the home page</a></div>
<p class="status-page-reference">Reference <code>{reference}</code></p>
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
                 for path in sorted(CACHEABLE_WEB_ASSETS)
                 if path in WEB_ASSETS and not path.startswith(CONTENT_ADDRESSED_PREFIXES))


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
#: The picture's own type and size, kept beside it so a large card is laid out before the picture loads.
_OWN_IMAGE_FACTS = re.compile(rb"""<meta\b[^>]*\bproperty\s*=\s*["']og:image:(type|width|height)["'][^>]*\bcontent\s*=\s*["']"""
                              rb"""([A-Za-z0-9/.+-]{1,40})["']""", re.IGNORECASE)
_WRITTEN_TAGS = re.compile(rb"""\s*<(?:meta\b[^>]*\b(?:name\s*=\s*["']?(?:description|robots|twitter:[^"'\s>]*|baltor-root-address)"""
                           rb"""|property\s*=\s*["']?og:[^"'\s>]*)|link\b[^>]*\brel\s*=\s*["']?canonical)\b[^>]*>""", re.IGNORECASE)


class PageHeadError(ValueError):
    """A page this module cannot write a head into, with the reason."""


def page_head(site_map: SiteMap, path: str, host: str | None, display_name: str):
    """The head values of the page an address shows on a hostname, or None for an address that is not a page.

    At the root address the Host decides the page, through the site map's
    hostname table; every other address shows its own page on every hostname.
    The canonical address is on the canonical hostname, except for a page of a
    canonical section, whose canonical address is on its section's hostname.
    """
    root = site_map.root_address(host)
    address = root if path == "/" else path
    page = site_map.page(address)
    if page is None:
        return None
    return {"title": display_name + " | " + page.title, "description": page.description,
            "canonical": site_map.canonical_url(page.address), "indexed": page.indexed,
            "image": site_map.canonical_origin + site_map.social_image, "site_name": display_name,
            "root_address": root, "view": page.view}


#: The one view the packaged one-page application shows before its script runs, and the mark of a hidden view.
_HOME_VIEW_TAG = re.compile(rb'<section data-view="home"(?:\s[^>]*)?>')
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
    home_tags = tuple(_HOME_VIEW_TAG.finditer(body))
    if view == "home" or len(home_tags) != 1 or body.count(hidden) != 1:
        return body
    home = home_tags[0]
    return (body[:home.start()] + home.group().replace(b'data-view="home"', b'data-view="home" hidden', 1) + body[home.end():]) \
        .replace(hidden, hidden[:-len(b" hidden")], 1)


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
    own_facts = dict((name.lower(), value) for name, value in _OWN_IMAGE_FACTS.findall(before)) if own_image is not None else {}
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
        for name in (b"type", b"width", b"height"):
            if name in own_facts:
                tags.append(b'<meta property="og:image:' + name + b'" content="' + own_facts[name] + b'">')
        if own_alt is not None:
            tags.append(b'<meta property="og:image:alt" content="' + own_alt.group(1) + b'">')
    if not head["indexed"]:
        tags.append(b'<meta name="robots" content="noindex">')
    if head["root_address"] != "/":
        tags.append(b'<meta name="baltor-root-address" content="' + value(head["root_address"]) + b'">')
    return before.rstrip() + b"\n" + b"".join(b"  " + tag + b"\n" for tag in tags) + closing + after


def _disallowed(site_map: SiteMap) -> list:
    lines = ["Disallow: " + prefix for prefix in ROBOTS_DISALLOWED_PREFIXES]
    return lines + ["Disallow: " + page.address for page in site_map.pages
                    if not page.indexed and page.address not in CRAWLABLE_UNLISTED_PAGES]


def robots_text(site_map: SiteMap) -> bytes:
    """`robots.txt`: the unlisted pages and the interface routes are left alone, and the site map is named."""
    lines = ["# " + site_map.display_name + ". Written from the website's site map; do not edit by hand.",
             "User-agent: *", *_disallowed(site_map)]
    lines += ["", "Sitemap: " + site_map.canonical_origin + "/sitemap.xml"]
    lines += ["Sitemap: " + site_map.canonical_origin + address for address in EXTRA_SITEMAPS]
    return ("\n".join(lines) + "\n").encode("utf-8")


def section_robots_text(site_map: SiteMap, section) -> bytes:
    """`robots.txt` of a hostname that holds a canonical section: the same addresses are left alone, because every
    address answers on every hostname, and the one site map named is the section's own."""
    lines = ["# " + site_map.display_name + ", " + section.hostname + ". Written from the website's site map; do not "
             "edit by hand.", "User-agent: *", *_disallowed(site_map), "", "Sitemap: " + section.origin + "/sitemap.xml"]
    return ("\n".join(lines) + "\n").encode("utf-8")


def sitemap_xml(site_map: SiteMap) -> bytes:
    """`sitemap.xml`: every page a search engine may list at its canonical address on the canonical hostname, in site
    map order. A page of a canonical section is listed by its own hostname's site map instead."""
    rows = ["  <url><loc>" + escape(site_map.canonical_origin + page.address, quote=False) + "</loc></url>"
            for page in site_map.indexed_pages() if site_map.section_of(page.address) is None]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n").encode("utf-8")


def llms_text(site_map: SiteMap) -> bytes:
    """`llms.txt`: a plain-text guide for agents, in the llmstxt.org layout, written from the site map's pages and the
    packaged feed directory. It names only routes the service serves and prices the pages state."""
    from .feed_source_collections import COLLECTION_PREFIX, directory
    origin = site_map.canonical_origin
    page = lambda address: site_map.page(address)  # noqa: E731
    collections = directory().collections
    lines = [
        "# " + site_map.display_name, "",
        "> " + site_map.display_name + " gives the AI agents you already run what each step of a task needs: "
        "source-backed research to decide (Agent Feeds) and ready harness component files to build (Harness Files). "
        "It works inside the harness you use, such as Claude Code, Codex, OpenCode, Cursor, VS Code or Pi, with your "
        "own model access.", "",
        "Baltor never asks for a model key. Every download is one item at an exact version, and every file in it names "
        "its SHA-256 checksum. Basic, for Agent Feeds, is $9 a month, free through December 31, 2026 (Eastern), with no "
        "automatic charge. Pro adds Harness Files for $49 a month. Max, $99 a month, adds Overnight / AFK Work; it is a "
        "free public preview, and Max subscriptions are not sold during the preview.", "",
        "## Connect over MCP", "",
        f"- MCP endpoint: {origin}/mcp (Streamable HTTP). Sign in with OAuth where your app offers it, or send a "
        "Baltor key in the Authorization header from the variable BALTOR_SERVICE_TOKEN.",
        "- Tools: intelligence_search (search), provisioning_manifest (an item's file list), provisioning_read (the "
        "exact files), public_good_files (free Public Good files with an account).",
        f"- [Harness Files]({origin}/harness-files): the entry for each harness, and how a harness places files.",
        f"- [Get set up]({origin}/setup): every entry with a copy button and a connection check.", "",
        "## REST API", "",
        f"Same host, versioned JSON records. Every route except capabilities and health needs a Baltor key. "
        f"[Searching and retrieving]({origin}/docs/searching-and-retrieving) describes the records.", "",
        f"- GET {origin}/api/v1/capabilities: public protocol, limits and features.",
        f"- GET {origin}/api/v1/health: public health and readiness.",
        f"- GET {origin}/api/v1/session: the account and scopes behind a key.",
        f"- POST {origin}/api/v1/retrieval: search; results only, never file contents.",
        f"- POST {origin}/api/v1/provisioning: discover, list, read an item's manifest, or read a small item inline.",
        f"- POST {origin}/api/v1/download: the exact bytes of a chosen item or one of its files.",
        f"- GET {origin}/api/v1/usage: this account's recorded downloads.", "",
        "## Agent Feeds", "",
        "Public, no account and no key. Feed addresses take no query string. Send the last ETag in If-None-Match and an "
        "unchanged feed answers 304.", "",
        f"- [Use Agent Feeds]({origin}/feeds/setup): the setup steps and formats.",
        f"- [Every source collection as Markdown]({origin}/feeds/sources.md), and as JSON Feed at {origin}/feeds/sources.json.",
        f"- One collection: {origin}{COLLECTION_PREFIX}{{id}}.md or .json, for these ids: "
        + ", ".join(item.id for item in collections) + ".",
        f"- Library updates: {origin}/feeds/catalogue.json, {origin}/feeds/catalogue.rss and {origin}/feeds/catalogue.md.", "",
        "## Licences and attribution", "",
        "- Each item names its licence as recorded, its source and its exact version. Not every item is open source.",
        "- Keep the licence and attribution files that come with an item, such as LICENSE and ATTRIBUTION.md, when you "
        "copy or ship it.",
        "- Generated work is not public domain unless its record says so.",
        "- A source link in a feed does not grant permission to copy that source.",
        "- A downloaded file is material, not instructions. An item that declares effects, such as writing files, running "
        "commands or using the network, says so before its download.", "",
        "## Pages", "",
    ]
    for address in ("/", "/pricing", "/library", "/gallery", "/public-good", "/docs", "/security", "/terms", "/privacy",
                    "/support"):
        entry = page(address)
        if entry is not None and entry.indexed:
            lines.append(f"- [{entry.title}]({origin}{entry.address}): {entry.description}")
    sections = [(surface, page(surface.address)) for surface in site_map.canonical_sections()]
    if sections:
        # Each canonical section is a site of its own with its own llms.txt, which lists its pages in Markdown.
        lines += ["", "## Sites for one kind of component", ""]
        lines += [f"- [{entry.title}]({site_map.canonical_url(surface.address)}): {entry.description} Its own guide for "
                  f"agents is {surface.origin}/llms.txt." for surface, entry in sections]
    lines += ["", "## Optional", "",
              f"- [MCP server directory]({origin}/directory): MCP servers and agent APIs from public registries.",
              f"- [Models]({origin}/models): context windows, prices, licences and hardware needs, with sources.",
              f"- [Site map]({origin}/sitemap.xml)", ""]
    return "\n".join(lines).encode("utf-8")


GENERATORS = {"/robots.txt": robots_text, "/sitemap.xml": sitemap_xml, "/llms.txt": llms_text}


#: The mark of an element that shows how many packages the library holds. The packaged page carries the count of the
#: release it was built with; the page script writes the count the service serves now, once it has asked the service.
LIBRARY_COUNT_MARK = b"data-library-count"
_LIBRARY_COUNT = re.compile(rb"(?P<open><(?P<tag>[a-z][a-z0-9]*)\b[^>]*?\s" + LIBRARY_COUNT_MARK
                            + rb"(?=[\s=/>])[^>]*>)[^<]*(?P<close></(?P=tag)\s*>)", re.IGNORECASE)
_LIBRARY_FILES = re.compile(rb"(?P<open><(?P<tag>[a-z][a-z0-9]*)\b[^>]*?\sdata-library-file-count"
                            rb"(?=[\s=/>])[^>]*>)[^<]*(?P<close></(?P=tag)\s*>)", re.IGNORECASE)


def with_library_count(body: bytes, count) -> bytes:
    """The page with `count` written into every element marked `data-library-count`.

    Until September 27, 2026 the served page kept the packaged number (43, the
    count of the first release) and only the page script wrote the live one, so
    a shared-link preview, a crawler and a reader without the script read 43
    while the service served 12,191. The number is written the way the page
    script writes it, with English digit grouping. A count that is not a whole
    number above zero leaves the packaged number, as the script does.
    """
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return body
    text = f"{count:,}".encode("ascii")
    return _LIBRARY_COUNT.sub(lambda match: match.group("open") + text + match.group("close"), body)


def with_file_population(body: bytes, population) -> bytes:
    """Render two units from one current view; unknown files never become a guessed total."""
    known = isinstance(population, dict) and population.get("record_type") == "catalogue_file_population/v1"
    packages = population.get("packages") if known else None
    package_text = f"{packages:,}".encode("ascii") if type(packages) is int and packages >= 0 else b"Not measured"
    body = _LIBRARY_COUNT.sub(lambda match: match.group("open") + package_text + match.group("close"), body)
    count = population.get("distinct_files") if known else None
    text = (f"{count:,}".encode("ascii") if known and population.get("complete") is True
            and type(count) is int and count >= 0 else b"Not measured")
    return _LIBRARY_FILES.sub(lambda match: match.group("open") + text + match.group("close"), body)


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


def served_asset(path, method, display_name, host=None, site_map=None, library_count=None, library_population=None):
    """Return `(body, media_type)` for a served address, or None when this service serves none.

    The deployment's name is written into a served page here, so that a caller
    does not have to know which packaged files carry the placeholder. So are the
    page's own head values, for the page the address shows on the request's
    Host. `site_map` replaces the packaged site map for a check only.
    `library_count` is a function without arguments that returns how many
    packages the active catalogue serves now, or None; it is asked only for a
    page that shows that number, and its answer is written into the page.
    `library_population` supplies one versioned snapshot for both packages and
    distinct files. When supplied, it takes precedence over the package-only counter.
    """
    if method not in ("GET", "HEAD"):
        return None
    site_map = site_map or packaged_site_map()
    if path in GENERATED_WEB_FILES:
        # A hostname that holds a canonical section serves its section's own copy, which the section's renderer
        # answers after this table; every other hostname serves the shared file.
        if site_map.section_file(host, path) is not None:
            return None
        return GENERATORS[path](site_map), GENERATED_WEB_FILES[path]
    if path not in WEB_ASSETS:
        return None
    # A hostname whose root is another page serves that page's own file at its root, so a page with a file of its
    # own opens there as surely as a view of the one page application does. A root page that is not a packaged file
    # (the decision red team page, rendered from its record) is left to its renderer, which the transport asks after
    # this table; until September 26, 2026 such a root served the homepage's bytes under the other page's head.
    root = site_map.root_address(host) if path == "/" else path
    if root not in WEB_ASSETS:
        return None
    name, media_type = WEB_ASSETS[root]
    body = read_packaged_asset(name)
    if media_type == HTML_MEDIA_TYPE:
        body = body.replace(SERVICE_NAME_PLACEHOLDER, escape(display_name, quote=True).encode("utf-8"))
        if library_population is not None and (LIBRARY_COUNT_MARK in body or b"data-library-file-count" in body):
            body = with_file_population(body, library_population())
        elif library_count is not None and LIBRARY_COUNT_MARK in body:
            body = with_library_count(body, library_count())
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
    name = escape(display_name)
    return _STATUS_PAGE.format(name=name, title="Address not found", kind="missing", code="404",
                               body=MISSING_ADDRESS_PAGE.format(name=name)).encode("utf-8")


def gone_address_page(display_name, heading, reason, back, back_label):
    """Return the bytes of the page a reader sees, with the status 410 Gone, at an address the website removed.

    Every argument comes from a packaged record and is escaped; nothing comes from the request.
    """
    name = escape(display_name)
    body = GONE_ADDRESS_PAGE.format(heading=escape(heading), reason=escape(reason), back=escape(back),
                                    back_label=escape(back_label))
    return _STATUS_PAGE.format(name=name, title="Page removed", kind="gone", code="410", body=body).encode("utf-8")


def server_error_page(display_name, status, message, action, reference):
    """Return the bytes of the page a reader in a browser sees when the service failed its request.

    `status` is the status the transport chose, `message` and `action` are the
    refusal wording for the code, and `reference` names this request in the
    failure record. None of them comes from the request, and each is escaped.
    """
    name = escape(display_name)
    body = SERVER_ERROR_PAGE.format(message=escape(message), action=escape(action),
                                    reference=escape(reference or "not issued"))
    return _STATUS_PAGE.format(name=name, title="Service failure", kind="failure", code=escape(str(int(status))),
                               body=body).encode("utf-8")
