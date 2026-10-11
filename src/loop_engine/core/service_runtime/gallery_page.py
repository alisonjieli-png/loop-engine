"""The gallery: Baltor's own creative files with the render each one's native check recorded, at `/gallery`.

Kind: pure rendering over one packaged record, `web_assets/gallery/gallery.json`, which `tools/build_gallery.py` writes
from a published creative release, and its WebP previews beside it. Nothing here reads a request, a credential, an
account or the catalogue store, and nothing calls a model.

The owner, October 9, 2026, asked for a browsable gallery with visibility tiers: "some other components will not be
actively browsable besides maybe a title and some meta data to avoid scraping". Every item carries one tier from the
design brief, shown in words on its tile and its page:

```text
tier       label             what the web shows                                  how the files arrive
showcase   Free download     preview, summary, every detail                      a web download with a free account
listed     In your harness   summary, details and file names, never a file body  the customer's harness, with the plan
private    (none)            nothing: the address answers the standard 404       signed-in search only
```

No item is `showcase` yet, because a free web download does not exist; the state is rendered and tested so an item
turns on with its record. A listed item with a recorded render shows it as its preview: the render is a picture of what
the file makes, drawn by Baltor's own check, and the files themselves arrive only through a harness download.

```text
/gallery                  hero, kind filters, each kind's first four tiles and the rest behind "Show all",
                          what the tiers mean, one action
/gallery/{slug}           one item: render or file names, tier, summary, contract, details, how to get the files
/gallery/sitemap.xml      every public item page, named in robots.txt beside the site map
/assets/gallery/*.webp    the previews, same-origin, content-addressed by their file names
```

The filters work without the page script: each is a link to its kind's section, and "Show all" is a disclosure. With
the script they filter in place and keep the choice in the address (`?kind=`), which the canonical address leaves out.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape
import json
import re

from . import gallery_records
from .gallery_random import ROUTES as RANDOM_ROUTES
from .gallery_records import (ASSET_PREFIX, PUBLIC_TIERS, RECORD_TYPE, RECORD_FOLDER, RECORD_FILE, TIERS,
                              TIER_LABELS, GalleryRecordError, parse_record, record)

INDEX = "/gallery"
PREFIX = "/gallery/"
SITEMAP = "/gallery/sitemap.xml"
VIEW = "gallery"
ITEM_VIEW = "gallery-item"
FIRST_TILES = 4
CARD = "/assets/share-card-gallery.png"
STYLESHEET = "/assets/offering-pages.css"
SCRIPT = "/assets/offering-pages.js"
EFFECT_WORDS = {"reads_fs": "reads files", "writes_fs": "writes files", "spawns_process": "runs commands",
                "network": "uses the network", "reads_secret": "reads secrets"}


def preview_assets() -> dict:
    """The public preview table from the same record the gallery renders."""
    return gallery_records.preview_assets(record())


def public_items() -> list:
    return [item for item in record()["items"] if item["tier"] in PUBLIC_TIERS]


def item_at(path: str):
    if not path.startswith(PREFIX):
        return None
    slug = path[len(PREFIX):]
    return next((item for item in public_items() if item["slug"] == slug), None)


def handles(path: str) -> bool:
    return path in (INDEX, SITEMAP, *RANDOM_ROUTES) or item_at(path) is not None


# --- Parts -------------------------------------------------------------------------------------------------------------

def _inline(text: str) -> str:
    """Escaped text with `code` spans, as the item cards write file and node names."""
    parts = escape(text).split("`")
    return "".join(f"<code>{part}</code>" if index % 2 else part for index, part in enumerate(parts))


def _size(count: int) -> str:
    return f"{count / 1048576:.1f} MB" if count >= 1048576 else f"{count / 1024:.1f} KB" if count >= 1024 else f"{count} bytes"


def _engine(item) -> str:
    engine = item.get("engine") or {}
    name = {"godot": "Godot", "blender": "Blender", "python": "Python"}.get(engine.get("name"), engine.get("name") or "")
    return f"{name} {engine['minimum_version']} or later" if engine.get("minimum_version") else name


def _checked_with(item) -> str:
    checks = item.get("checks") or {}
    found = re.match(r"^(\w+) (\d+\.\d+(?:\.\d+)?)", checks.get("engine") or "")
    if not found:
        return ""
    name = {"godot": "Godot", "blender": "Blender", "python": "Python"}.get(found.group(1), found.group(1))
    return f"{name} {found.group(2)}"


def _in_sentence(label: str) -> str:
    """A kind's label inside a sentence: lower case, except a product name or a leading number."""
    return label if label[0].isdigit() or label.split()[0] in ("Godot", "Blender") else label[0].lower() + label[1:]


def _kinds() -> dict:
    return {kind["id"]: kind for kind in record()["kinds"]}


def _tier_label(item) -> str:
    return f'<span class="gl-tier" data-tier="{item["tier"]}">{TIER_LABELS[item["tier"]]}</span>'


def _tile(item, kinds) -> str:
    kind = kinds[item["kind"]]
    preview = item.get("preview")
    if preview:
        picture = (f'<img src="{ASSET_PREFIX}{preview["file"]}" width="{preview["width"]}" height="{preview["height"]}" '
                   f'loading="lazy" decoding="async" alt="Render of {escape(item["title"], quote=True)}">')
    else:
        names = [entry["path"] for entry in item["files"] if "/" not in entry["path"]][:4]
        picture = ('<span class="gl-files" aria-hidden="true">'
                   + "".join(f"<span>{escape(name)}</span>" for name in names) + "<span>Full files in your harness</span></span>")
    return (f'<li class="gl-tile" data-kind="{item["kind"]}"><a class="gl-link" href="{PREFIX}{item["slug"]}">'
            f'<span class="gl-picture">{picture}</span><span class="gl-title">{escape(item["title"])}</span></a>'
            f'<p class="gl-meta"><span>{escape(kind["single"])}</span><span>{escape(item["licence"])}</span></p>'
            f"{_tier_label(item)}</li>")


def _frame(site_map, display_name, address, view, title, description, body, structured, labelled_by, extra_head=""):
    from .model_directory_pages import Page, frame
    page = frame(site_map, display_name, Page(address, view, title, description, body, structured, labelled_by))
    return page.replace("</head>", f'<link rel="stylesheet" href="{STYLESHEET}">\n<script defer src="{SCRIPT}"></script>\n'
                                   f"{extra_head}</head>", 1)


# --- /gallery ----------------------------------------------------------------------------------------------------------

def index_body() -> str:
    from .web_site_map import load_layout_standard
    from .model_directory_pages import contents
    items, kinds = public_items(), _kinds()
    price = str(load_layout_standard().price.get("phrase") or "")
    shown = [kind for kind in record()["kinds"] if any(item["kind"] == kind["id"] for item in items)]
    renders = sum(1 for item in items if item.get("preview"))
    intro = ('<div class="md-band md-intro og-hero gl-hero"><p class="eyebrow">Gallery</p>'
             '<h1 id="gallery-title">See what each creative file makes.</h1>'
             f'<p class="lede">Browse {len(items):,} creative tools and assets from Baltor: Godot shaders, procedural textures, meshes, '
             f'Blender tools and four-dimensional geometry. {renders:,} of them show the render their check recorded in '
             'the engine.</p>'
             f'<p class="md-reading og-price">Your harness downloads the exact files with <strong>Pro, '
             f'{escape(price)}</strong>.</p><div class="md-actions"><a class="button primary" href="/get-started">Get started'
             '</a><a class="lib-text-link" href="#get-files">How to get the files</a>'
             '<a class="lib-text-link" href="/random">Find a random preview</a></div></div>')
    chips = (f'<a class="gl-chip" href="#gallery-kinds" data-kind-filter="" aria-current="true">All <span>{len(items):,}'
             '</span></a>' + "".join(
                 f'<a class="gl-chip" href="#kind-{kind["id"]}" data-kind-filter="{kind["id"]}">{escape(kind["label"])} '
                 f'<span>{sum(1 for item in items if item["kind"] == kind["id"]):,}</span></a>' for kind in shown))
    filters = (f'<nav class="gl-filters" aria-label="Filter by kind">{chips}</nav>'
               '<p class="gl-count" id="gallery-count" role="status" aria-live="polite"></p>')
    sections = ""
    for kind in shown:
        group = [item for item in items if item["kind"] == kind["id"]]
        first, rest = group[:FIRST_TILES], group[FIRST_TILES:]
        more = (f'<details class="gl-more"><summary>Show all {len(group):,} {escape(_in_sentence(kind["label"]))}</summary>'
                f'<ul class="gl-grid">{"".join(_tile(item, kinds) for item in rest)}</ul></details>') if rest else ""
        sections += (f'<section class="gl-kind" id="kind-{kind["id"]}" data-kind="{kind["id"]}" '
                     f'aria-labelledby="kind-{kind["id"]}-title"><div class="gl-kind-head"><h2 id="kind-{kind["id"]}-title">'
                     f'{escape(kind["label"])}</h2><p>{escape(kind["description"])}</p></div>'
                     f'<ul class="gl-grid">{"".join(_tile(item, kinds) for item in first)}</ul>{more}</section>')
    browse = f'<div class="md-band gl-browse" id="gallery-kinds">{filters}{sections}</div>'
    tiers = ("".join(f'<li><span class="gl-tier" data-tier="{tier}">{TIER_LABELS[tier]}</span> {text}</li>' for tier, text in (
        ("showcase", "The preview and every detail are open, and a free account downloads the full files on this site."),
        ("listed", "The summary, details and file names are open. Your harness downloads the files with Agent Feeds + "
                   "Harness Files."),
        ("private", "Not shown here. It appears only in a signed-in search for accounts allowed to see it."))))
    get_files = ('<section class="md-band md-quiet" id="get-files" aria-labelledby="get-files-title">'
                 '<h2 id="get-files-title">How to get the files</h2><p class="md-reading">Some files show only a summary '
                 'here. Your harness gets the full files through your Baltor connection. This keeps every download exact '
                 'and checks your account access. Every item in this gallery is <strong>In your harness</strong> today.</p>'
                 f'<ul class="md-plain gl-tiers">{tiers}</ul><p class="og-links"><a href="/harness-files#harnesses">Set up '
                 'your harness</a><a href="/security">How access works</a></p></section>')
    closing = ('<section class="md-band og-closing" aria-labelledby="og-closing-title"><div class="og-closing-row"><div>'
               '<h2 id="og-closing-title">Give your harness every creative file</h2><p class="md-reading">'
               f'Pro, {escape(price)}. Cancel any time from your account page.</p></div>'
               '<a class="button primary" href="/get-started">Get started</a></div></section>')
    return intro + browse + get_files + closing


# --- /gallery/{slug} ---------------------------------------------------------------------------------------------------

def _get_panel(item, price: str) -> str:
    if item["tier"] == "showcase":
        return ('<aside class="gl-panel" aria-labelledby="gl-panel-title"><p class="eyebrow">Free download</p>'
                '<h2 id="gl-panel-title">Download the full files</h2><p>Create a free Baltor account to download them: your '
                'email, a link, a password.</p><div class="md-actions"><a class="button primary" href="/get-started">'
                'Sign in free to download</a><a class="lib-text-link" href="/login">Sign in</a></div></aside>')
    prompt = f'Search Baltor for "{item["title"]}" and show me its files before downloading.'
    return ('<aside class="gl-panel" aria-labelledby="gl-panel-title"><p class="eyebrow">In your harness</p>'
            '<h2 id="gl-panel-title">Get it in your harness</h2>'
            f'<p>Included with Pro, {escape(price)}. With the plan, your agent can download all '
            f'{len(item["files"])} files at this exact version. Ask it:</p>'
            f'<div class="og-code"><pre class="md-code md-code-wrap" tabindex="0" aria-label="A request for your agent">'
            f'{escape(prompt)}</pre><button class="quiet og-copy" type="button" data-copy-code hidden>Copy</button>'
            '<span class="og-copy-status" role="status" aria-live="polite"></span></div>'
            '<div class="md-actions"><a class="button primary" href="/get-started">Get started</a>'
            '<a class="lib-text-link" href="/harness-files#harnesses">Set up your harness</a></div></aside>')


def item_body(item) -> str:
    from .web_site_map import load_layout_standard
    kinds = _kinds()
    kind = kinds[item["kind"]]
    price = str(load_layout_standard().price.get("phrase") or "")
    preview = item.get("preview")
    checked = _checked_with(item)
    if preview:
        picture = (f'<figure class="gl-figure"><img src="{ASSET_PREFIX}{preview["file"]}" width="{preview["width"]}" '
                   f'height="{preview["height"]}" alt="Render of {escape(item["title"], quote=True)}"><figcaption>The render '
                   f'its check recorded{" in " + escape(checked) if checked else ""}, {preview["width"]} by '
                   f'{preview["height"]} pixels.</figcaption></figure>')
    else:
        picture = ('<div class="gl-figure gl-figure-files"><p class="og-meta">Files, names only</p><ul class="md-plain">'
                   + "".join(f"<li><code>{escape(entry['path'])}</code></li>" for entry in item["files"])
                   + "</ul><p>Full files in your harness.</p></div>")
    chips = (f'{_tier_label(item)}<span class="gl-chip-static">{escape(kind["single"])}</span>'
             f'<span class="gl-chip-static">{escape(item["licence"])}</span>')
    intro = (f'<div class="md-band md-intro og-hero gl-item-hero"><p class="eyebrow"><a href="{INDEX}">Gallery</a> / '
             f'<a href="{INDEX}#kind-{kind["id"]}">{escape(kind["label"])}</a></p>'
             f'<h1 id="gallery-item-title">{escape(item["title"])}</h1><p class="gl-chips">{chips}</p>'
             f'<p class="lede">{_inline(item["summary"])}</p></div>')
    top = (f'<div class="md-band gl-item-top">{picture}{_get_panel(item, price)}</div>')
    contract = ""
    if item["contract"]:
        contract = ('<section class="md-band" id="contract" aria-labelledby="contract-title"><h2 id="contract-title">'
                    'What it takes and gives</h2><dl class="md-dl">'
                    + "".join(f"<div><dt>{escape(label)}</dt><dd>{_inline(text)}</dd></div>" for label, text in item["contract"])
                    + "</dl>" + (f'<p class="md-reading gl-limits"><strong>Limits.</strong> {_inline(item["limits"])}</p>'
                                 if item["limits"] else "") + "</section>")
    effects = ", ".join(EFFECT_WORDS.get(effect, effect) for effect in item["declared_effects"]) or "None declared"
    checks = item.get("checks") or {}
    facts = [("Kind", kind["single"]), ("Engine", _engine(item)), ("Files", f'{len(item["files"])} files, {_size(item["bytes"])}'),
             ("Licence", item["licence"]), ("Declared effects", effects),
             ("Checked with", (checked + (f', {checks["renderer"]}' if checks.get("renderer") else "")) if checked else ""),
             ("Checks", ", ".join(name.replace("_", " ") for name in checks.get("names") or [])),
             ("Techniques", ", ".join(item["techniques"])), ("Tags", ", ".join(item["tags"])),
             ("Identity", f'<code>{escape(item["identity"])}</code>'), ("Version", f'<code>{escape(item["version"])}</code>')]
    rows = "".join(f"<div><dt>{name}</dt><dd>{value if name in ('Identity', 'Version') else escape(value)}</dd></div>"
                   for name, value in facts if value)
    details = ('<section class="md-band md-quiet" id="details" aria-labelledby="details-title"><h2 id="details-title">'
               f'Details</h2><dl class="md-dl">{rows}</dl><p class="md-reading">The version is the SHA-256 of the item your '
               'harness downloads; every file in it names its own checksum.</p></section>')
    by_slug = {other["slug"]: other for other in public_items()}
    related = [by_slug[slug] for slug in item["related"] if slug in by_slug]
    more = ""
    if related:
        more = ('<section class="md-band" id="related" aria-labelledby="related-title"><h2 id="related-title">Related files'
                f'</h2><ul class="gl-grid">{"".join(_tile(other, kinds) for other in related)}</ul></section>')
    report = ('<section class="md-band gl-report" aria-label="Report this item"><p class="md-reading">Something wrong with '
              'this item, its rights or its safety? Report it on the <a href="/support">support page</a>, or from your '
              'harness after a download.</p></section>')
    return intro + top + contract + details + more + report


# --- Pages -------------------------------------------------------------------------------------------------------------

def _description(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= 160 else text[:159].rsplit(" ", 1)[0].rstrip(",;:") + "…"


@lru_cache(maxsize=4)
def _index_page(display_name: str) -> bytes:
    from .model_directory_pages import SCHEMA_CONTEXT, breadcrumbs, canonical
    from .web_site_map import load_site_map
    site_map = load_site_map()
    entry = site_map.page(INDEX)
    if entry is None:
        raise ValueError(f"the site map does not list {INDEX}")
    items = public_items()
    structured = {"@context": SCHEMA_CONTEXT, "@type": "CollectionPage", "name": entry.title,
                  "url": canonical(site_map, INDEX), "description": entry.description,
                  "mainEntity": {"@type": "ItemList", "numberOfItems": len(items)},
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), (entry.title, INDEX)))}
    from .offering_guides import share_card_head
    card = share_card_head(canonical(site_map, CARD), "Baltor Gallery. See what each creative file makes.")
    return _frame(site_map, display_name, INDEX, VIEW, entry.title, entry.description, index_body(), structured,
                  "gallery-title", card).encode("utf-8")


@lru_cache(maxsize=512)
def _item_page(display_name: str, slug: str) -> bytes:
    from .model_directory_pages import SCHEMA_CONTEXT, breadcrumbs, canonical
    from .web_site_map import load_site_map
    site_map = load_site_map()
    item = item_at(PREFIX + slug)
    address = PREFIX + slug
    description = _description(item["summary"])
    structured = {"@context": SCHEMA_CONTEXT, "@type": "CreativeWork", "name": item["title"],
                  "url": canonical(site_map, address), "description": description, "license": item["licence"],
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Gallery", INDEX), (item["title"], address)))}
    extra = '<meta name="twitter:card" content="summary">\n'
    if item.get("preview"):
        image = escape(canonical(site_map, ASSET_PREFIX + item["preview"]["file"]), quote=True)
        structured["image"] = canonical(site_map, ASSET_PREFIX + item["preview"]["file"])
        extra = (f'<meta property="og:image" content="{image}">\n<meta property="og:image:width" content="'
                 f'{item["preview"]["width"]}">\n<meta property="og:image:height" content="{item["preview"]["height"]}">\n'
                 f'<meta property="og:image:alt" content="Render of {escape(item["title"], quote=True)}">\n'
                 f'<meta name="twitter:card" content="summary">\n<meta name="twitter:image" content="{image}">\n')
    return _frame(site_map, display_name, address, ITEM_VIEW, item["title"], description, item_body(item), structured,
                  "gallery-item-title", extra).encode("utf-8")


def sitemap_xml(site_map) -> bytes:
    from .model_directory_pages import canonical
    rows = "".join(f"  <url><loc>{escape(canonical(site_map, PREFIX + item['slug']), quote=False)}</loc></url>\n"
                   for item in public_items())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + rows + "</urlset>\n").encode("utf-8")


def rendered(path: str, method: str, display_name: str, host: "str | None" = None):
    """`(body, media_type)` for the gallery, an item page or the gallery's site map; None for any other address.

    A private item's address, and an address no item holds, answer None, so the transport serves the standard 404."""
    from . import web_pages
    if method not in ("GET", "HEAD"):
        return None
    if path in RANDOM_ROUTES:
        from .gallery_random import rendered as random_rendered
        return random_rendered(path, method, display_name, host)
    if path == SITEMAP:
        return sitemap_xml(web_pages.packaged_site_map()), "application/xml"
    if path == INDEX:
        body = _index_page(display_name)
        head = web_pages.page_head(web_pages.packaged_site_map(), path, host, display_name)
        if head is not None:
            body = web_pages.with_page_head(body, head)
    else:
        item = item_at(path)
        if item is None:
            return None
        body = _item_page(display_name, item["slug"])
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE
