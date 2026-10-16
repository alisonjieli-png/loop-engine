"""Random discovery views over the gallery's finite public-preview projection.

The browser selects locally, without a model or service operation. Page bytes
are deterministic and edge-exportable; explicit selections retain the preview
digest in the address. Source downloads continue through the gallery's normal
authenticated path. This is presentation within the gallery owner, not a new
catalogue, asset store or execution component.
"""
from functools import lru_cache
from html import escape
import json

from . import gallery_media

INDEX = "/random"
ROUTES = (INDEX, *(INDEX + "/" + kind for kind in gallery_media.KINDS))
LABELS = {"all": "All previews", "image": "Images", "video": "Video", "music": "Music"}


def _media(item):
    url, title = escape(item["url"], quote=True), escape(item["title"], quote=True)
    if item["kind"] == "image":
        return f'<img src="{url}" width="{item["width"]}" height="{item["height"]}" alt="{title}">'
    tag = "video" if item["kind"] == "video" else "audio"
    return (f'<{tag} controls preload="none" aria-label="{title}"><source src="{url}" '
            f'type="{item["media_type"]}">Your browser cannot play this preview. Use the download link.</{tag}>')


def _facts(item):
    size = f'{item["bytes"] / 1024:.1f} KB'
    shape = f'{item["width"]} × {item["height"]} pixels' if item["width"] else "Audio"
    if item["duration_seconds"] is not None:
        shape += f' · {item["duration_seconds"]:.1f} seconds'
    return [("format", "Format", f'{item["format"]} · {size} · {shape}'),
            ("licence", "Preview reuse licence", item["preview_licence"] or "Not separately recorded"),
            ("source-licence", "Source licence" if item["source_kind"] == "website_example" else "Source files licence",
             item["source_licence"])]


def _access_note(item):
    if item["source_kind"] == "website_example":
        return ("Original website demo, not a library item. The MIT licence covers this preview and its editable source. "
                "No account is needed for the source ZIP.")
    return ("Public display does not grant reuse rights. Check the preview licence before reuse. Full source files use "
            "the account and plan requirements shown on the source page.")


def body(kind="all"):
    all_items = gallery_media.public_previews()
    items = [item for item in all_items if kind == "all" or item["kind"] == kind]
    first = items[0] if items else None
    counts = {key: sum(item["kind"] == key for item in all_items) for key in gallery_media.KINDS}
    counts["all"] = len(all_items)
    chips = "".join(
        f'<a class="gl-chip" href="{INDEX if key == "all" else INDEX + "/" + key}"'
        + (' aria-current="page"' if key == kind else "") + f'>{label} <span>{counts[key]}</span></a>'
        for key, label in LABELS.items())
    title = "Find a creative starting point." if kind == "all" else {
        "image": "Discover an image.", "video": "Discover a video.", "music": "Discover a music cue."}[kind]
    intro = ('<div class="md-band md-intro ra-intro"><p class="eyebrow"><a href="/gallery">Gallery</a> / Random discovery</p>'
             f'<h1 id="random-title">{title}</h1><p class="lede">Explore public previews with their source, '
             'licence and file details. Choose another to find a different starting point.</p>'
             f'<nav class="gl-filters" aria-label="Preview kind">{chips}</nav>'
             '<div class="md-actions"><button class="button primary" type="button" data-show-another hidden>'
             'Show another</button><a class="lib-text-link" href="/gallery">Browse the full gallery</a></div>'
             '<p class="ra-status" data-selection-status role="status" aria-live="polite" aria-atomic="true"></p></div>')
    if first:
        website = first["source_kind"] == "website_example"
        facts = "".join(f'<div><dt data-asset-{key}-label>{label}</dt><dd data-asset-{key}>{escape(value)}</dd></div>'
                        for key, label, value in _facts(first))
        selection = (f'<article class="ra-card" data-asset-card hidden aria-labelledby="asset-title">'
                     f'<div class="ra-picture" data-asset-media>{_media(first)}</div><div class="ra-detail">'
                     f'<p class="eyebrow" data-asset-kind>{LABELS[first["kind"]]} / '
                     f'{"original website demo" if website else "public preview"}</p>'
                     f'<h2 id="asset-title" data-asset-title>{escape(first["title"])}</h2>'
                     f'<p data-asset-summary>{escape(first["summary"])}</p><dl class="ra-facts">{facts}</dl>'
                     f'<div class="ra-links"><a class="button secondary" data-asset-download download '
                     f'href="{first["url"]}">Save public preview</a><a data-asset-source href="{first["source_page"]}"'
                     f'{" download" if website else ""}>{"Download editable source ZIP" if website else "Source and editable files"}</a>'
                     f'<a data-asset-permalink href="/random/{first["kind"]}?asset={first["id"]}">'
                     f'Link to this preview</a></div><p class="ra-access" data-asset-access>{_access_note(first)}</p>'
                     '<details class="ra-provenance"><summary>Provenance and exact version</summary>'
                     f'<p data-asset-provenance>{escape(first["provenance"])}</p><dl class="ra-facts">'
                     f'<div><dt>Source identity</dt><dd><code data-asset-identity>{escape(first["source_identity"])}</code></dd></div>'
                     f'<div><dt data-asset-version-label>{"Source ZIP SHA-256" if website else "Source version"}</dt>'
                     f'<dd><code data-asset-version>{first["source_version"]}</code></dd></div>'
                     f'<div><dt>Preview SHA-256</dt><dd><code data-asset-digest>{first["sha256"]}</code></dd></div>'
                     '</dl></details></div></article>')
        empty = ('<section class="ra-empty" data-asset-unavailable hidden aria-labelledby="unavailable-title">'
                 '<h2 id="unavailable-title">This preview is unavailable.</h2><p>The selected preview is missing, '
                 'has changed or is no longer public. Choose another or browse the gallery.</p></section>')
        fallback = ('<noscript><section class="ra-empty" data-sample-preview aria-labelledby="sample-title">'
                    '<h2 id="sample-title">A sample preview</h2><p>Random selection and exact preview links '
                    'need JavaScript. This fixed sample is not the selection in your address.</p>'
                    f'<div class="ra-picture">{_media(first)}</div><p><a href="{first["source_page"]}">'
                    + ('Download the editable source ZIP' if website else f'Open {escape(first["title"])} in the gallery')
                    + '</a></p></section></noscript>')
    else:
        selection, fallback = "", ""
        label = "media" if kind == "all" else kind
        empty = ('<section class="ra-empty" data-asset-unavailable aria-labelledby="unavailable-title">'
                 f'<h2 id="unavailable-title">No public {label} previews are available.</h2>'
                 '<p>This category has no reviewed preview to show. Nothing has been substituted for it.</p>'
                 '<a class="button secondary" href="/random/image">Explore image previews</a></section>')
    payload = json.dumps({"record_type": "gallery_random_projection/v2", "kind": kind, "items": items},
                         ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace("&", "\\u0026")
    return (intro + f'<div class="md-band ra-browse" data-random-discovery>{selection}{empty}{fallback}</div>'
            f'<script type="application/json" id="random-preview-data">{payload}</script>')


@lru_cache(maxsize=16)
def _page(path, display_name):
    from .gallery_page import _frame
    from .model_directory_pages import SCHEMA_CONTEXT, canonical
    from .web_site_map import load_site_map
    site_map = load_site_map()
    entry = site_map.page(path)
    kind = "all" if path == INDEX else path.rsplit("/", 1)[1]
    structured = {"@context": SCHEMA_CONTEXT, "@type": "CollectionPage", "name": entry.title,
                  "description": entry.description, "url": canonical(site_map, path)}
    head = ('<link rel="stylesheet" href="/assets/gallery-random.css">'
            '<script type="module" src="/assets/gallery-random.js"></script>')
    return _frame(site_map, display_name, path, entry.view, entry.title, entry.description, body(kind), structured,
                  "random-title", head).encode("utf-8")


def rendered(path, method, display_name, host=None):
    from . import web_pages
    if path not in ROUTES or method not in ("GET", "HEAD"):
        return None
    content = _page(path, display_name)
    head = web_pages.page_head(web_pages.packaged_site_map(), path, host, display_name)
    if head is not None:
        content = web_pages.with_page_head(content, head)
    return web_pages.version_asset_references(content), web_pages.HTML_MEDIA_TYPE
