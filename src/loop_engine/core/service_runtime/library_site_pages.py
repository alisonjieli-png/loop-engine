"""The library sites: deterministicskills.baltor.ai, tools.baltor.ai and cornercases.baltor.ai, and the component
pages on baltor.ai that their lists link to.

Kind: pure rendering over two packaged records (`library_site_records`) and the typed site map. Nothing here reads a request
beyond its address and hostname, a credential, an account or the catalogue store, and nothing calls a model.

The owner, October 16, 2026, asked for subdomain websites that showcase deterministic skills, harness tools and corner
cases, mostly static at the edge, with sign-ups sent to the main site. Each hostname holds a canonical section of the
site map: its pages name their own hostname as their canonical address, and their header and footer name the canonical
hostname's pages by whole addresses, so a reader who signs up does so on baltor.ai.

```text
https://<host>/                      the section's hub, the site map page at the section's address
https://<host><address>/<category>   one page for each category: what to watch for and the components it holds
https://<host><page>.md              the same page as Markdown, never listed by a search engine
https://<host>/robots.txt            the section's own files, served from <address>/robots.txt, /sitemap.xml and /llms.txt
https://baltor.ai/components/<slug>  one page for each listed item without a gallery page, canonical on baltor.ai
https://baltor.ai/components/sitemap.xml   the component pages a search engine may list, named in robots.txt
```

A component page shows what the item's record states: its summary, its contract facts, the cases its tests cover, its
files by name and size, its licence, its declared effects and its exact identity and version. It never shows a file
body. A component page with fewer than three facts and no cases or notes is marked noindex, so the library's thinner
records never stand as pages a search engine lists on their own.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape
import json
import re

from . import library_site_records as records
from .web_site_map import SCHEME, SECTION_ROOT_FILES

COMPONENTS = "/components/"
COMPONENTS_SITEMAP = "/components/sitemap.xml"
CATEGORY_VIEW, COMPONENT_VIEW = "library-site-category", "component"
STYLESHEETS = ("/assets/offering-pages.css", "/assets/library-sites.css")
SCRIPTS = ("/assets/offering-pages.js", "/assets/library-sites.js")
#: Each host's own picture for a shared link, 1200 by 630 pixels, drawn by tools/render_share_cards.mjs.
CARDS = {"deterministic-skills": "/assets/share-card-deterministic-skills.png", "harness-tools": "/assets/share-card-tools.png",
         "corner-cases": "/assets/share-card-corner-cases.png"}
COMPONENT_CARD = "/assets/share-card-harness-files.png"
#: The main-site pages each host links to: the pages for the people who arrive with that problem, and the guides.
FUNNELS = {"deterministic-skills": ("/for/coding-agents", "/efficiency", "/harness-files", "/gallery", "/case-studies/pi-and-gemma-4"),
           "harness-tools": ("/for/coding-agents", "/harness-files", "/setup", "/top-mcps", "/docs/quickstart-claude-code"),
           "corner-cases": ("/case-studies/data-cleanup", "/for/engineering-teams", "/for/comparing-tools", "/harness-files",
                            "/gallery")}
#: The library feed a reader can follow instead of an email list; the transport serves these at the canonical hostname.
UPDATE_FEEDS = (("RSS", "/feeds/catalogue.rss"), ("JSON Feed", "/feeds/catalogue.json"), ("Markdown", "/feeds/catalogue.md"))
EFFECT_WORDS = {"reads_fs": "reads files", "writes_fs": "writes files", "spawns_process": "runs commands",
                "network": "uses the network", "reads_secret": "reads secrets"}
KIND_LABELS = {"skill": "Skill", "code_module": "Code module", "contract_schema": "Contract schema", "command": "Command",
               "hook": "Hook", "protocol_server_configuration": "MCP server settings", "harness_settings": "Harness settings",
               "three_d_model": "3D model"}
LANGUAGES = {".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript", ".sh": "Shell", ".gd": "GDScript"}
CODE_LICENCE = re.compile(r"^[A-Za-z0-9.+-]+(?: (?:AND|OR) [A-Za-z0-9.+-]+)*$")
INDEX_FACTS = 3
#: The schema.org type of an item whose family is not code: a data table is a dataset. Code is SoftwareSourceCode, and
#: any other item, such as settings or a saved prompt, is a CreativeWork.
SCHEMA_TYPES = {"data_tables": "Dataset"}
#: The kinds of address that are a page's Markdown version, and a section's own root file.
ALTERNATES = frozenset({"hub_markdown", "category_markdown"})
SECTION_FILES = frozenset({"section_file"})
#: What a category's list is called on each host; a host not named here lists components.
LIST_HEADINGS = {"corner-cases": "Test packs and checks"}


# --- The records, joined to the site map ----------------------------------------------------------------------------

def _site_map():
    from . import web_pages
    return web_pages.packaged_site_map()


@lru_cache(maxsize=1)
def hosts() -> tuple:
    """(host record, canonical section) for each library site; a host whose section the site map lacks is refused."""
    site_map = _site_map()
    sections = {surface.address: surface for surface in site_map.canonical_sections()}
    paired = []
    for host in records.hosts_record()["hosts"]:
        surface = sections.get(host["address"])
        if surface is None or site_map.page(host["address"]) is None:
            raise records.LibrarySiteRecordError(f"the site map holds no canonical section at {host['address']}")
        paired.append((host, surface))
    return tuple(paired)


def _category_address(host, category):
    return host["address"] + "/" + category["slug"]


def component_address(item):
    return COMPONENTS + item["slug"]


def item_url(item):
    """The canonical page of an item: its gallery page when it has one, else its component page on baltor.ai."""
    site_map = _site_map()
    return site_map.canonical_url("/gallery/" + item["gallery"] if item["gallery"] else component_address(item))


def _items():
    return records.items_by_identity()


@lru_cache(maxsize=1)
def _pages() -> dict:
    """Every address this module answers, with what it shows: (kind, host, category or item)."""
    pages = {}
    for host, _surface in hosts():
        pages[host["address"]] = ("hub", host, None)
        pages[host["address"] + ".md"] = ("hub_markdown", host, None)
        for name in SECTION_ROOT_FILES:
            pages[host["address"] + name] = ("section_file", host, name)
        for category in host["categories"]:
            pages[_category_address(host, category)] = ("category", host, category)
            pages[_category_address(host, category) + ".md"] = ("category_markdown", host, category)
    for item in _items().values():
        if not item["gallery"]:
            pages[component_address(item)] = ("component", None, item)
    pages[COMPONENTS_SITEMAP] = ("components_sitemap", None, None)
    return pages


def addresses() -> tuple:
    """Every address this module renders on the canonical hostname, in a stable order, for the edge export."""
    return tuple(_pages())


def handles(path: str) -> bool:
    return path in _pages()


def is_alternate(path: str) -> bool:
    """A Markdown version of a page, which a search engine must not list beside the page itself."""
    return _pages().get(path, ("",))[0] in ALTERNATES


def is_section_file(path: str) -> bool:
    """A section's own robots.txt, sitemap.xml or llms.txt at its address, which is cached like the shared files."""
    return _pages().get(path, ("",))[0] in SECTION_FILES


def indexable(item) -> bool:
    return len(item["facts"]) >= INDEX_FACTS or bool(item["cases"]) or bool(item["notes"])


# --- Shared parts ---------------------------------------------------------------------------------------------------

def _price() -> str:
    from .web_site_map import load_layout_standard
    return str(load_layout_standard().price.get("phrase") or "")


def _main(path):
    """A whole address on the canonical hostname, for a link that must leave the library site."""
    return _site_map().canonical_origin + path


def _effects(item):
    return ", ".join(EFFECT_WORDS.get(effect, effect) for effect in item["effects"]) or "none declared"


def _kind(item):
    return KIND_LABELS.get(item["kind"], "Component")


def _size(count):
    return f"{count / 1048576:.1f} MB" if count >= 1048576 else f"{count / 1024:.1f} KB" if count >= 1024 else f"{count} bytes"


def _sentence(text):
    found = re.match(r"(.+?[.!?])(?=\s+[A-Z`(]|$)", " ".join(text.split()))
    return found.group(1) if found else text


def _description(text):
    text = " ".join(text.split())
    return text if len(text) <= 160 else text[:159].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _released():
    """The day the served release was confirmed, as a reader writes it."""
    from datetime import date
    day = date.fromisoformat(records.items_record()["built_from"]["confirmed_at"][:10])
    return f"{day.strftime('%B')} {day.day}, {day.year}"


def _json_ld(value):
    return '<script type="application/ld+json">' + json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c") + "</script>"


def _social(image, alt, name):
    url = escape(_main(image), quote=True)
    return (f'<meta property="og:site_name" content="{escape(name, quote=True)}">\n<meta property="og:image" content="{url}">\n'
            '<meta property="og:image:type" content="image/png">\n<meta property="og:image:width" content="1200">\n'
            f'<meta property="og:image:height" content="630">\n<meta property="og:image:alt" content="{escape(alt, quote=True)}">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="{url}">\n')


def _frame(page, display_name, extra_head, section):
    from .model_directory_pages import frame
    site_map = _site_map()
    text = frame(site_map, display_name, page, chrome_origin=site_map.canonical_origin if section else "")
    assets = "".join(f'<link rel="stylesheet" href="{sheet}">\n' for sheet in STYLESHEETS)
    assets += "".join(f'<script defer src="{script}"></script>\n' for script in SCRIPTS)
    return text.replace("</head>", assets + extra_head + "</head>", 1)


def _cta():
    price = escape(_price())
    return ('<section class="md-band og-closing ls-cta" aria-labelledby="ls-cta-title"><div class="og-closing-row"><div>'
            '<h2 id="ls-cta-title">Give your agent these components</h2><p class="md-reading">Your harness downloads them '
            f'through Baltor with Pro, {price}. Cancel any time from your account page.</p></div>'
            f'<a class="button primary" href="{_main("/get-started")}">Get started</a></div>'
            f'<p class="og-links"><a href="{_main("/pricing")}">Compare the plans</a>'
            f'<a href="{_main("/harness-files#harnesses")}">Set up your harness</a></p></section>')


def _bar():
    links = ", ".join(f'<a href="{_main(path)}">{label}</a>' for label, path in UPDATE_FEEDS)
    return ('<aside class="ls-bar" data-library-site-bar hidden aria-label="Follow library updates"><p>New components reach '
            f'the library in releases. Follow them by {links}.</p><button class="quiet" type="button" data-library-site-bar-close>'
            'Dismiss</button></aside>')


def _funnels(host):
    site_map = _site_map()
    rows = []
    for path in FUNNELS[host["id"]]:
        page = site_map.page(path)
        if page is None:
            raise records.LibrarySiteRecordError(f"{host['id']} links to {path}, which the site map does not hold")
        rows.append(f'<li><a href="{_main(path)}">{escape(page.title)}</a><span>{escape(page.description)}</span></li>')
    return "".join(rows)


def _other_hosts(host):
    site_map = _site_map()
    return "".join(f'<li><a href="{site_map.canonical_url(other["address"])}">{escape(other["name"])}</a>'
                   f'<span>{escape(other["headline"])}.</span></li>' for other, _surface in hosts() if other is not host)


def _counted(host, category):
    rule = category["library_count"]
    if not rule:
        return ""
    number = records.items_record()["counts"][f"{host['id']}/{category['slug']}"]
    return f"{number:,} {rule['label']}"


def _row(item):
    facts = "".join(f"<div><dt>{escape(label)}</dt><dd><code>{escape(value)}</code></dd></div>"
                    if label in ("Command", "Replay", "Test") else f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"
                    for label, value in item["facts"][:2])
    return (f'<li class="ls-row" id="{escape(item["slug"])}"><h3 class="ls-row-title"><a href="{item_url(item)}">'
            f'{escape(item["title"])}</a></h3><p class="ls-row-name"><code>{escape(item["name"])}</code></p>'
            f'<p class="ls-row-text" data-listing-text>{escape(_sentence(item["summary"]))}</p>'
            + (f'<dl class="ls-row-facts">{facts}</dl>' if facts else "")
            + f'<p class="ls-row-meta"><span>{escape(_kind(item))}</span><span data-listing-text>{escape(item["licence"])}</span>'
            f'<span>{len(item["files"])} files, {_size(item["bytes"])}</span><span>{escape(_effects(item))}</span></p></li>')


def _item_list(entries):
    """ItemList structured data: each entry's canonical page, in the order the page shows them."""
    return {"@type": "ItemList", "numberOfItems": len(entries), "itemListElement": [
        {"@type": "ListItem", "position": index + 1, "url": item_url(item), "name": item["title"]}
        for index, item in enumerate(entries)]}


def _breadcrumbs(trail):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": index + 1, "name": name, "item": url} for index, (name, url) in enumerate(trail)]}


# --- Hub --------------------------------------------------------------------------------------------------------------

def _hub_body(host):
    site_map = _site_map()
    shown = {identity for category in host["categories"] for identity in category["items"]}
    cards = "".join(
        f'<li class="ls-card"><a href="{site_map.canonical_url(_category_address(host, category))}">'
        f'<span class="ls-card-title">{escape(category["title"])}</span>'
        f'<span class="ls-card-text">{escape(_sentence(category["lede"]))}</span>'
        f'<span class="ls-card-meta">{len(category["items"])} shown'
        + (f", {escape(_counted(host, category))} in the library" if category["library_count"] else "")
        + "</span></a></li>" for category in host["categories"])
    view = site_map.page(host["address"]).view
    steps = ("Your agent searches Baltor for the step it is on and gets names, sizes and licences, never file bodies.",
             "It picks one component at an exact version and reads its file list, where every file names its SHA-256 checksum.",
             "It downloads exactly those files into your project, where your harness finds them, and checks each one against its checksum.")
    return (f'<div class="md-band md-intro og-hero ls-hero"><p class="eyebrow">{escape(host["name"])}</p>'
            f'<h1 id="{view}-title">{escape(host["headline"])}</h1><p class="lede">{escape(host["lede"])}</p>'
            f'<p class="md-reading ls-facts">{len(shown)} components in {len(host["categories"])} groups, each at the exact '
            f'version the library release of {_released()} serves.</p>'
            f'<div class="md-actions"><a class="button primary" href="{_main("/get-started")}">Get started</a>'
            '<a class="lib-text-link" href="#browse">Browse the groups</a>'
            f'<a class="lib-text-link" href="{_main("/harness-files")}">How your harness gets files</a></div></div>'
            '<section class="md-band" id="browse" aria-labelledby="browse-title"><h2 id="browse-title">Browse by job</h2>'
            f'<ul class="ls-cards">{cards}</ul></section>'
            '<section class="md-band md-quiet" id="how" aria-labelledby="how-title"><h2 id="how-title">How your agent uses '
            f'them</h2><ol class="ls-steps">{"".join(f"<li>{escape(step)}</li>" for step in steps)}</ol></section>'
            f'<section class="md-band" id="why" aria-labelledby="why-title"><h2 id="why-title">Why it matters</h2>'
            f'<p class="md-reading">{escape(host["why"])}</p></section>'
            + _cta()
            + '<section class="md-band md-quiet" id="more" aria-labelledby="more-title"><h2 id="more-title">More from Baltor'
            f'</h2><ul class="ls-links">{_other_hosts(host)}{_funnels(host)}</ul></section>' + _bar())


@lru_cache(maxsize=8)
def _hub_page(host_id: str, display_name: str) -> str:
    from .model_directory_pages import Page
    site_map = _site_map()
    host = next(host for host, _surface in hosts() if host["id"] == host_id)
    entry = site_map.page(host["address"])
    url = site_map.canonical_url(host["address"])
    entries = [_items()[identity] for category in host["categories"] for identity in category["items"]]
    unique = list({item["identity"]: item for item in entries}.values())
    structured = {"@context": SCHEME + "://schema.org", "@type": "CollectionPage", "name": entry.title, "url": url,
                  "description": entry.description, "isPartOf": {"@type": "WebSite", "name": display_name,
                                                                 "url": site_map.canonical_origin + "/"},
                  "hasPart": [{"@type": "CollectionPage", "name": category["title"],
                               "url": site_map.canonical_url(_category_address(host, category))}
                              for category in host["categories"]],
                  "mainEntity": _item_list(unique),
                  "breadcrumb": _breadcrumbs(((display_name, site_map.canonical_origin + "/"), (entry.title, url)))}
    extra = (f'<link rel="alternate" type="text/markdown" href="{escape(_markdown_url(host, host["address"]))}">\n'
             + _social(CARDS[host["id"]], host["card_alt"], display_name))
    return _frame(Page(host["address"], entry.view, entry.title, entry.description, _hub_body(host), structured,
                       f"{entry.view}-title", canonical_url=url), display_name, extra, True)


def _markdown_url(host, address):
    """The whole address of a page's Markdown version on its section's hostname."""
    section = next(surface for other, surface in hosts() if other is host)
    return section.origin + address + ".md"


# --- Category -------------------------------------------------------------------------------------------------------

def _category_body(host, category):
    site_map = _site_map()
    items = [_items()[identity] for identity in category["items"]]
    counted = _counted(host, category)
    watch = "".join(f"<li>{escape(line)}</li>" for line in category["watch_for"])
    others = "".join(f'<li><a href="{site_map.canonical_url(_category_address(host, other))}">{escape(other["title"])}</a>'
                     f'<span>{escape(_sentence(other["lede"]))}</span></li>'
                     for other in host["categories"] if other is not category)
    heading = LIST_HEADINGS.get(host["id"], "Components")
    return (f'<div class="md-band md-intro og-hero ls-hero"><p class="eyebrow"><a href="{site_map.canonical_url(host["address"])}">'
            f'{escape(host["name"])}</a></p><h1 id="library-site-category-title">{escape(category["title"])}</h1>'
            f'<p class="lede">{escape(category["lede"])}</p><p class="md-reading ls-facts">{len(items)} shown here'
            + (f", from {escape(counted)} in the library release of {_released()}" if counted else
               f", each at the exact version the library release of {_released()} serves") + ".</p></div>"
            '<section class="md-band md-quiet" id="watch-for" aria-labelledby="watch-for-title"><h2 id="watch-for-title">'
            f'What to watch for</h2><ul class="md-plain ls-watch">{watch}</ul></section>'
            f'<section class="md-band" id="components" aria-labelledby="components-title"><h2 id="components-title">{heading}</h2>'
            f'<ol class="ls-list">{"".join(_row(item) for item in items)}</ol></section>'
            + _cta()
            + f'<section class="md-band md-quiet" id="more" aria-labelledby="more-title"><h2 id="more-title">More from '
            f'{escape(host["name"])}</h2><ul class="ls-links">{others}{_other_hosts(host)}{_funnels(host)}</ul></section>' + _bar())


@lru_cache(maxsize=64)
def _category_page(host_id: str, slug: str, display_name: str) -> str:
    from .model_directory_pages import Page
    site_map = _site_map()
    host = next(host for host, _surface in hosts() if host["id"] == host_id)
    category = next(category for category in host["categories"] if category["slug"] == slug)
    address = _category_address(host, category)
    url = site_map.canonical_url(address)
    items = [_items()[identity] for identity in category["items"]]
    structured = {"@context": SCHEME + "://schema.org", "@type": "CollectionPage", "name": category["title"], "url": url,
                  "description": category["description"], "mainEntity": _item_list(items),
                  "breadcrumb": _breadcrumbs(((display_name, site_map.canonical_origin + "/"),
                                              (host["name"], site_map.canonical_url(host["address"])),
                                              (category["title"], url)))}
    extra = (f'<link rel="alternate" type="text/markdown" href="{escape(_markdown_url(host, address))}">\n'
             + _social(CARDS[host["id"]], host["card_alt"], display_name))
    title = f'{category["title"]} | {host["name"]}'
    return _frame(Page(address, CATEGORY_VIEW, title, category["description"], _category_body(host, category), structured,
                       "library-site-category-title", canonical_url=url), display_name, extra, True)


# --- Component --------------------------------------------------------------------------------------------------------

def _shown_in(item):
    """Every category that shows the item, as (host, category)."""
    return [(host, category) for host, _surface in hosts() for category in host["categories"] if item["identity"] in category["items"]]


def _component_body(item):
    site_map = _site_map()
    price = escape(_price())
    files = "".join(f"<li><code>{escape(path)}</code> <span>{_size(size)}</span></li>" for path, size in item["files"][:24])
    more = len(item["files"]) - 24
    if more > 0:
        files += f"<li>and {more} more files</li>"
    prompt = f'Search Baltor for "{item["title"]}" and show me its files before downloading.'
    panel = ('<aside class="gl-panel" aria-labelledby="gl-panel-title"><p class="eyebrow">In your harness</p>'
             '<h2 id="gl-panel-title">Get it in your harness</h2>'
             f'<p>Included with Pro, {price}. With the plan, your agent can download all {len(item["files"])} files at this '
             'exact version. Ask it:</p><div class="og-code"><pre class="md-code md-code-wrap" tabindex="0" '
             f'aria-label="A request for your agent">{escape(prompt)}</pre><button class="quiet og-copy" type="button" '
             'data-copy-code hidden>Copy</button><span class="og-copy-status" role="status" aria-live="polite"></span></div>'
             '<div class="md-actions"><a class="button primary" href="/get-started">Get started</a>'
             '<a class="lib-text-link" href="/harness-files#harnesses">Set up your harness</a></div></aside>')
    top = (f'<div class="md-band gl-item-top"><div class="gl-figure gl-figure-files"><p class="og-meta">Files, names only</p>'
           f'<ul class="md-plain ls-files">{files}</ul><p>Full files in your harness.</p></div>{panel}</div>')
    facts = ""
    if item["facts"]:
        rows = "".join(f"<div><dt>{escape(label)}</dt><dd>" + (f"<code>{escape(value)}</code>" if label in ("Command", "Replay", "Test", "Function", "File", "Module", "Wrapper", "Data file") else escape(value))
                       + "</dd></div>" for label, value in item["facts"])
        facts = ('<section class="md-band" id="contract" aria-labelledby="contract-title"><h2 id="contract-title">What it '
                 f'takes and gives</h2><dl class="md-dl">{rows}</dl></section>')
    cases = ""
    if item["cases"]:
        rows = "".join(f"<li><strong>{escape(name)}</strong>" + (f": <span data-listing-text>{escape(detail)}</span>" if detail else "")
                       + "</li>" for name, detail in item["cases"])
        cases = ('<section class="md-band md-quiet" id="cases" aria-labelledby="cases-title"><h2 id="cases-title">Cases it '
                 f'covers</h2><ul class="md-plain ls-cases">{rows}</ul></section>')
    notes = ""
    if item["notes"]:
        rows = "".join(f"<div><dt>{escape(label)}</dt><dd data-listing-text>{escape(value)}</dd></div>" for label, value in item["notes"])
        notes = ('<section class="md-band" id="limits" aria-labelledby="limits-title"><h2 id="limits-title">Limits and '
                 f'scope</h2><dl class="md-dl">{rows}</dl></section>')
    details = [("Kind", _kind(item)), ("Licence", item["licence"]), ("Declared effects", _effects(item)),
               ("Placed for", ", ".join(item["harnesses"])), ("Source", item["source"]),
               ("Size", f'{len(item["files"])} files, {_size(item["bytes"])}')]
    rows = "".join(f'<div><dt>{name}</dt><dd{" data-listing-text" if name in ("Licence", "Source") else ""}>{escape(value)}</dd></div>'
                   for name, value in details if value)
    rows += (f'<div><dt>Identity</dt><dd><code>{escape(item["identity"])}</code></dd></div>'
             f'<div><dt>Version</dt><dd><code>{escape(item["version"])}</code></dd></div>')
    detail = ('<section class="md-band md-quiet" id="details" aria-labelledby="details-title"><h2 id="details-title">Details'
              f'</h2><dl class="md-dl">{rows}</dl><p class="md-reading">The version is the SHA-256 of the item your harness '
              'downloads; every file in it names its own checksum.</p></section>')
    shown = _shown_in(item)
    links = "".join(f'<li><a href="{site_map.canonical_url(_category_address(host, category))}">{escape(category["title"])}</a>'
                    f'<span>{escape(host["name"])}</span></li>' for host, category in shown)
    related = []
    for _host, category in shown:
        for identity in category["items"]:
            other = _items()[identity]
            if other["identity"] != item["identity"] and other not in related:
                related.append(other)
    related_rows = "".join(f'<li><a href="{item_url(other)}">{escape(other["title"])}</a></li>' for other in related[:6])
    more_band = ('<section class="md-band" id="shown-in" aria-labelledby="shown-in-title"><h2 id="shown-in-title">Where it '
                 f'is shown</h2><ul class="ls-links">{links}</ul>'
                 + (f'<h3>Related components</h3><ul class="md-plain ls-related">{related_rows}</ul>' if related_rows else "")
                 + "</section>")
    report = ('<section class="md-band gl-report" aria-label="Report this item"><p class="md-reading">Something wrong with '
              'this item, its rights or its safety? Report it on the <a href="/support">support page</a>, or from your '
              'harness after a download.</p></section>')
    intro = (f'<div class="md-band md-intro og-hero ls-hero"><p class="eyebrow"><a href="/library">Library</a> / '
             f'{escape(_kind(item))}</p><h1 id="component-title">{escape(item["title"])}</h1>'
             f'<p class="ls-row-name"><code>{escape(item["name"])}</code></p>'
             f'<p class="lede" data-listing-text>{escape(item["summary"])}</p></div>')
    return intro + top + facts + cases + notes + detail + more_band + report


def _component_structured(item, url, display_name):
    site_map = _site_map()
    languages = sorted({LANGUAGES[suffix] for path, _size in item["files"] for suffix in LANGUAGES if path.endswith(suffix)})
    code = bool(languages) and item["family"] not in SCHEMA_TYPES
    schema_type = SCHEMA_TYPES.get(item["family"]) or ("SoftwareSourceCode" if code else "CreativeWork")
    value = {"@context": SCHEME + "://schema.org", "@type": schema_type, "name": item["title"], "url": url,
             "description": _description(item["summary"]), "version": item["version"], "identifier": item["identity"],
             "breadcrumb": _breadcrumbs(((display_name, site_map.canonical_origin + "/"),
                                         ("Library", site_map.canonical_origin + "/library"), (item["title"], url)))}
    if CODE_LICENCE.match(item["licence"]):
        value["license"] = item["licence"]
    if code:
        value["programmingLanguage"] = languages
        repository = re.match(r"^(github\.com/[^/]+/[^/]+)", item["source"])
        if repository:
            value["codeRepository"] = SCHEME + "://" + repository.group(1)
    return value


@lru_cache(maxsize=512)
def _component_page(slug: str, display_name: str) -> str:
    from .model_directory_pages import Page
    site_map = _site_map()
    item = next(item for item in _items().values() if item["slug"] == slug and not item["gallery"])
    address = component_address(item)
    url = site_map.canonical_url(address)
    extra = _social(COMPONENT_CARD, f"Baltor library component. {item['title']}", display_name)
    if not indexable(item):
        extra += '<meta name="robots" content="noindex">\n'
    return _frame(Page(address, COMPONENT_VIEW, item["title"], _description(item["summary"]), _component_body(item),
                       _component_structured(item, url, display_name), "component-title"), display_name, extra, False)


# --- Markdown, site maps and the guide for agents -------------------------------------------------------------------

def _markdown_row(item):
    return (f'- [{item["title"]}]({item_url(item)}): {_sentence(item["summary"])} Name `{item["name"]}`, licence '
            f'{item["licence"]}, {len(item["files"])} files.')


def hub_markdown(host) -> str:
    site_map = _site_map()
    lines = [f'# {host["name"]}: {host["headline"]}', "", host["lede"], "", host["why"], "", "## Groups", ""]
    for category in host["categories"]:
        lines.append(f'- [{category["title"]}]({site_map.canonical_url(_category_address(host, category))}): '
                     f'{category["description"]}')
    lines += ["", f'Every component is the exact version the Baltor library release of {_released()} serves. Your agent '
              f'downloads it through Baltor with Pro, {_price()}: {_main("/get-started")}', ""]
    return "\n".join(lines)


def category_markdown(host, category) -> str:
    items = [_items()[identity] for identity in category["items"]]
    lines = [f'# {category["title"]}', "", f'Part of {host["name"]} by Baltor.', "", category["lede"], "",
             "## What to watch for", "", *(f"- {line}" for line in category["watch_for"]), "", "## Components", "",
             *(_markdown_row(item) for item in items), "",
             f'Your agent downloads these through Baltor with Pro, {_price()}: {_main("/get-started")}', ""]
    return "\n".join(lines)


def section_llms(host) -> str:
    site_map = _site_map()
    lines = [f'# Baltor {host["name"]}', "", f'> {host["lede"]}', "", host["why"], "",
             "Each component below is one exact version from the Baltor library. An agent connects to Baltor's MCP "
             f'server at {_main("/mcp")} or its REST API, both described in {_main("/llms.txt")}, and downloads a '
             "component's files after reading its file list.", "", "## Groups", ""]
    for category in host["categories"]:
        address = _category_address(host, category)
        lines.append(f'- [{category["title"]}]({site_map.canonical_url(address)}): {category["description"]} '
                     f'Markdown: {_markdown_url(host, address)}')
    for category in host["categories"]:
        lines += ["", f'## {category["title"]}', ""]
        lines += [_markdown_row(_items()[identity]) for identity in category["items"]]
    lines += ["", "## Optional", "", f'- [Baltor for agents]({_main("/llms.txt")}): the main guide for agents.',
              f'- [Get started]({_main("/get-started")}): create an account; Pro is {_price()}.',
              f'- [Site map]({next(surface for other, surface in hosts() if other is host).origin}/sitemap.xml)', ""]
    return "\n".join(lines)


def section_sitemap(host) -> str:
    site_map = _site_map()
    urls = [site_map.canonical_url(host["address"])] + [site_map.canonical_url(_category_address(host, category))
                                                        for category in host["categories"]]
    rows = "".join(f"  <url><loc>{escape(url, quote=False)}</loc></url>\n" for url in urls)
    return _urlset(rows)


def components_sitemap() -> str:
    site_map = _site_map()
    rows = "".join(f"  <url><loc>{escape(site_map.canonical_url(component_address(item)), quote=False)}</loc></url>\n"
                   for item in sorted(_items().values(), key=lambda item: item["slug"]) if not item["gallery"] and indexable(item))
    return _urlset(rows)


def _urlset(rows):
    from .model_directory_pages import SITEMAP_NAMESPACE
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="{SITEMAP_NAMESPACE}">\n' + rows + "</urlset>\n"


# --- The transport's question -----------------------------------------------------------------------------------------

def rendered(path: str, method: str, display_name: str, host: "str | None" = None):
    """`(body, media_type)` for a library site address, a section's root file on its own hostname or a section's hub at its
    hostname's root; None for any other address or method."""
    from . import web_pages
    if method not in ("GET", "HEAD"):
        return None
    site_map = web_pages.packaged_site_map()
    if path in SECTION_ROOT_FILES:
        own = site_map.section_file(host, path)
        if own is None:
            return None
        path = own
    address = site_map.root_address(host) if path == "/" else path
    page = _pages().get(address)
    if page is None:
        return None
    kind, site, subject = page
    return _ANSWERS[kind](site, subject, path, host, display_name)


def _html(text):
    from . import web_pages
    return web_pages.version_asset_references(text.encode("utf-8")), web_pages.HTML_MEDIA_TYPE


def _hub_answer(site, _subject, path, host, display_name):
    """The hub, with the head the site map writes for the request's address and hostname, as every site map page has."""
    from . import web_pages
    site_map = web_pages.packaged_site_map()
    body = _hub_page(site["id"], display_name).encode("utf-8")
    head = web_pages.page_head(site_map, path, host, display_name)
    body = web_pages.with_page_head(body, head) if head is not None else body
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE


def _section_file(site, name, _path, _host, _display_name):
    from . import web_pages
    site_map = web_pages.packaged_site_map()
    surface = next(surface for other, surface in hosts() if other is site)
    texts = {"/robots.txt": lambda: web_pages.section_robots_text(site_map, surface),
             "/sitemap.xml": lambda: section_sitemap(site).encode("utf-8"),
             "/llms.txt": lambda: section_llms(site).encode("utf-8")}
    return texts[name](), web_pages.GENERATED_WEB_FILES[name]


MARKDOWN = "text/markdown; charset=utf-8"
_ANSWERS = {
    "hub": _hub_answer,
    "category": lambda host, category, _path, _host, name: _html(_category_page(host["id"], category["slug"], name)),
    "component": lambda _host_record, item, _path, _host, name: _html(_component_page(item["slug"], name)),
    "hub_markdown": lambda host, _subject, _path, _host, _name: (hub_markdown(host).encode("utf-8"), MARKDOWN),
    "category_markdown": lambda host, category, _path, _host, _name: (category_markdown(host, category).encode("utf-8"), MARKDOWN),
    "components_sitemap": lambda _host_record, _subject, _path, _host, _name: (components_sitemap().encode("utf-8"),
                                                                                "application/xml"),
    "section_file": _section_file,
}
