"""The pages of the public model directory: /models, /endpoints, /can-i-run and their detail pages.

Kind: pure rendering over the packaged directory records and the typed site map. `web_pages` asks
`render` for an address; this module answers with the page bytes, or None for an address it does
not serve. It reads no request, sets no header and opens no connection.

Each page carries its own title, description, canonical address and structured data, the header and
footer from `web_chrome`, and only the site's stylesheets and one same-origin script, so the
service's content policy holds. The pages work without the script: the lists are rendered here,
and the script adds search, sorting and the in-page hardware calculation.

Listing text that other publishers wrote (model and maker names) is marked data-listing-text, which
the shared word rules of the browser checks leave out of Baltor's own copy.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from html import escape

from . import commercial_relationship as commercial
from . import model_directory as records
from . import model_directory_fit as fit
from . import model_directory_format as fmt
from .web_chrome import shared_chrome
from .web_site_map import load_site_map

PAGES = {"/models": "models", "/endpoints": "endpoints", "/can-i-run": "can-i-run"}
MODEL_PREFIX, ENDPOINT_PREFIX = "/models/", "/endpoints/"
SITEMAP_ADDRESS = "/models/sitemap.xml"
LIST_LENGTH = 40
RESULT_LENGTH = 25
DEFAULT_PRESET = "rtx-5090"
DEFAULT_CONTEXT = 8192
SEARCH_INDEX = "/assets/model-directory/search-index.json"
FIT_INDEX = "/assets/model-directory/fit-index.json"
LISTING = " data-listing-text"
SCHEMA_CONTEXT = records.SCHEME + "://schema.org"
#: How the model list is ordered, stated in words where the list is shown.
ORDER_SENTENCE = ("The list shows the models that the most providers serve first, newer models first among equals, then the models "
                  "no provider lists, most downloaded on Hugging Face first. You can order it by date, downloads or name instead. "
                  "Payment never changes the order or which models are listed.")
#: The XML namespace name of a site map file. It names a format; nothing fetches it.
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def handles(address: str) -> bool:
    """True for an address this module may answer: a page, a detail page, or the site map file."""
    if address in PAGES or address == SITEMAP_ADDRESS:
        return True
    for prefix in (MODEL_PREFIX, ENDPOINT_PREFIX):
        if address.startswith(prefix):
            slug = address[len(prefix):]
            return bool(slug) and records._SLUG.match(slug) is not None
    return False


def canonical(site_map, address: str) -> str:
    return records.SCHEME + "://" + site_map.canonical_hostname + address


def _json_ld(value: dict) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + text.replace("<", "\\u003c") + "</script>"


@lru_cache(maxsize=1)
def _template() -> str:
    from importlib.resources import files
    return files("loop_engine").joinpath("core", "service_runtime", "web_assets", records.DATA_FOLDER, "page.html").read_text(encoding="utf-8")


@dataclass(frozen=True)
class Page:
    """What one rendered page says about itself: its address, view, title, description, body and structured data."""

    address: str
    view: str
    title: str
    description: str
    body: str
    structured: dict
    labelled_by: str


def frame(site_map, name: str, page: Page) -> str:
    """One whole page: its own title, description, canonical and structured data; the header; the view; the footer."""
    address, view, title, description = page.address, page.view, page.title, page.description
    body, structured, labelled_by = page.body, page.structured, page.labelled_by
    address_text = escape(canonical(site_map, address))
    head = (f'<meta name="description" content="{escape(description)}">\n<title>{escape(name)} | {escape(title)}</title>\n'
            f'<link rel="canonical" href="{address_text}">\n<meta property="og:title" content="{escape(name)} | {escape(title)}">\n'
            f'<meta property="og:description" content="{escape(description)}">\n<meta property="og:url" content="{address_text}">\n'
            f'<meta property="og:type" content="website">\n' + _json_ld(structured))
    view_markup = (f'<section data-view="{view}" class="md-page" aria-labelledby="{labelled_by}" '
                   f'data-search-index="{SEARCH_INDEX}" data-fit-index="{FIT_INDEX}">' + body + "</section>")
    header, footer = shared_chrome(name)
    return (_template().replace("{{HEAD}}", head).replace("{{HEADER}}", header)
            .replace("{{VIEW}}", view_markup).replace("{{FOOTER}}", footer))


def media_type(address: str) -> str:
    return "application/xml" if address == SITEMAP_ADDRESS else "text/html"




def today() -> str:
    return date.today().isoformat()


def breadcrumbs(site_map, trail) -> dict:
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": index + 1, "name": name, "item": canonical(site_map, address)}
        for index, (name, address) in enumerate(trail)]}


def contents(links) -> str:
    return ('<nav class="md-contents" aria-label="On this page">'
            + "".join(f'<a href="#{anchor}">{escape(text)}</a>' for anchor, text in links) + "</nav>")


def disclosure(rows) -> str:
    """The paid links section. It states the present fact, read from every row's relationship."""
    relationships = [records.relationship_of(row) for row in rows]
    paid = sum(1 for item in relationships if item.shows_commercial_link)
    ads = sum(1 for item in relationships if item.is_sponsored_placement)
    if not paid and not ads:
        text = ("No link in this directory is a paid link or an ad, and no listing is paid for. "
                "The order and the contents of every list come from the sources named on this page.")
    else:
        text = escape(commercial.PAID_LINKS_DISCLOSURE)
    return (f'<div class="md-band md-quiet" id="{commercial.DISCLOSURE_SECTION_ID}" aria-labelledby="paid-links-title">'
            f'<h2 id="paid-links-title">Paid links</h2><p class="md-reading">{text}</p></div>')


def paid_link_notice(rows) -> str:
    """The one sentence shown directly above a list, only while a row in it shows a paid link."""
    if not commercial.shows_paid_link_notice(records.relationship_of(row) for row in rows):
        return ""
    return f'<p class="md-notice">{escape(commercial.PAID_LINK_NOTICE)}</p>'


def commercial_link(row: dict) -> str:
    """The labelled paid link or own-service link of a row, beside its plain address. Only presentation reads it."""
    attributes = commercial.link_attributes(records.relationship_of(row))
    if attributes is None:
        return ""
    return (f'<p class="md-paid"><a href="{escape(attributes["href"])}" rel="{escape(attributes["rel"])}">Visit</a> '
            f'<span class="md-label">{escape(attributes["label"])}</span> '
            f'<span class="md-basis">{escape(attributes["plain_address"])}</span></p>')


def ads_band(rows) -> str:
    """Ads in their own band headed Ads, at most the schema's limit, never inside a ranked list."""
    placed = [row for row in rows if records.relationship_of(row).is_sponsored_placement][:commercial.MAXIMUM_ADS]
    if not placed:
        return ""
    items = "".join(_ad_item(row) for row in placed)
    return (f'<div class="md-band md-ads" aria-labelledby="ads-title"><h2 id="ads-title">{escape(commercial.AD_BAND_HEADING)}</h2>'
            f'<p class="md-reading">These placements are paid for. They are not part of the lists on this page.</p><ul>{items}</ul></div>')


def _ad_item(row: dict) -> str:
    relationship = records.relationship_of(row)
    return (f'<li><span{LISTING}>{escape(row["name"])}</span> <a href="{escape(relationship.outbound_link)}" '
            f'rel="{escape(commercial.LINK_REL)}">Visit</a> <span class="md-label">{escape(relationship.disclosure_label)}</span> '
            f'<span class="md-basis">{escape(relationship.canonical_address)}</span></li>')


def model_item(row: dict) -> str:
    """One row of the model list: name and maker, then the facts people compare first."""
    cheapest = fmt.cheapest_input(row)
    price_text = fmt.price(cheapest["input"]) if cheapest else fmt.UNKNOWN
    licence = fmt.fact_value(row, "licence")
    tags = ", ".join(fmt.uses(row))
    return (f'<li class="md-row"><a class="md-row-link" href="/models/{row["slug"]}"><span class="md-name"{LISTING}>{escape(row["name"])}</span>'
            f'<span class="md-maker"{LISTING}>{escape(row["maker"])}</span></a><dl class="md-facts">'
            f'<div><dt>Parameters</dt><dd>{escape(fmt.short_parameters(fmt.fact_value(row, "parameters")))}</dd></div>'
            f'<div><dt>Context</dt><dd>{escape(fmt.tokens(fmt.largest(row, "context")))}</dd></div>'
            f'<div><dt>Licence</dt><dd{LISTING}>{escape(licence) if isinstance(licence, str) else fmt.UNKNOWN}</dd></div>'
            f'<div><dt>Input, per million tokens</dt><dd>{escape(price_text)}</dd></div></dl>'
            + (f'<p class="md-tags">{escape(tags)}</p>' if tags else "") + commercial_link(row) + "</li>")


def sources_band(directory, anchor: str = "sources") -> str:
    manifest = directory.manifest
    rows = "".join(
        f'<tr><th scope="row">{fmt.link(item["address"], item["name"])}</th><td>{escape(item["use"])}</td>'
        f'<td>{fmt.link(item["terms_address"], "Terms")}</td><td>{fmt.number(item.get("rows"))}</td>'
        f'<td>{escape(item.get("newest_read") or fmt.UNKNOWN)}</td></tr>' for item in manifest.get("sources") or ())
    linked = "".join(f'<li>{fmt.link(item["address"], item["name"])}: {escape(item["use"])} {fmt.link(item["terms_address"], "Terms")}</li>'
                     for item in manifest.get("linked_only") or ())
    return (f'<div class="md-band" id="{anchor}" aria-labelledby="{anchor}-title"><h2 id="{anchor}-title">Sources and dates</h2>'
            f'<p class="md-reading">Every row keeps the address of each source it uses and the day it was read. A fact no source states is '
            f'shown as {fmt.UNKNOWN}. The directory was built on <time datetime="{escape(manifest["built_at"])}">{escape(manifest["built_at"][:10])}</time>.</p>'
            f'<div class="md-table-wrap"><table class="md-table"><thead><tr><th scope="col">Source</th><th scope="col">What it gives</th>'
            f'<th scope="col">Terms</th><th scope="col">Rows</th><th scope="col">Last read</th></tr></thead><tbody>{rows}</tbody></table></div>'
            + (f'<ul class="md-plain">{linked}</ul>' if linked else "") + "</div>")


def models_page(directory, site_map, name: str) -> str:
    ordered = fmt.order_models(directory.models)
    shown = ordered[:LIST_LENGTH]
    count = len(directory.models)
    use_options = "".join(f'<option value="{value}">{value.capitalize()}</option>' for value in records.USE_CASES)
    body = ('<div class="md-band md-intro"><p class="eyebrow">Directory</p><h1 id="models-title">Models, open and hosted</h1>'
            f'<p class="lede">Context windows, prices, licences, quantizations and hardware needs for {count:,} models. '
            'Every fact names its source and the day it was read, and a fact no source states says Unknown.</p>'
            + contents((("browse", "Browse the models"), ("sources", "Sources and dates"), (commercial.DISCLOSURE_SECTION_ID, "Paid links")))
            + '<div class="md-actions"><a class="button secondary" href="/can-i-run">Check what your hardware runs</a>'
            '<a class="button secondary" href="/endpoints">Compare endpoints and runtimes</a>'
            '<a class="button secondary" href="/setup">Get set up</a></div></div>'
            '<div class="md-band" id="browse" aria-labelledby="browse-title"><h2 id="browse-title">Browse the models</h2>'
            '<form class="md-filters" data-models-filter><label class="md-field"><span>Search</span>'
            '<input type="search" name="q" autocomplete="off" placeholder="Name or maker"></label>'
            f'<label class="md-field"><span>Good for</span><select name="use"><option value="">Any use</option>{use_options}</select></label>'
            '<label class="md-field"><span>Weights</span><select name="weights"><option value="all">Open and hosted</option>'
            '<option value="open">Open weights</option><option value="hosted">Hosted with a price</option></select></label>'
            '<label class="md-field"><span>Order</span><select name="order"><option value="providers">Most providers first</option>'
            '<option value="newest">Newest first</option><option value="downloads">Most downloaded</option>'
            '<option value="name">By name</option></select></label></form>'
            f'<p class="md-order">{ORDER_SENTENCE}</p>{paid_link_notice(shown)}'
            f'<p class="md-count" data-models-count aria-live="polite">Showing the first {len(shown)} of {count:,} models.</p>'
            f'<ol class="md-list" data-models-list>{"".join(model_item(row) for row in shown)}</ol>'
            f'<p class="md-more"><button class="quiet" type="button" data-models-more{"" if count > len(shown) else " hidden"}>Show more</button></p></div>'
            + ads_band(directory.models) + sources_band(directory) + disclosure(directory.models))
    structured = {"@context": SCHEMA_CONTEXT, "@type": "CollectionPage", "name": "Models, open and hosted",
                  "url": canonical(site_map, "/models"), "description": f"A directory of {count:,} open and hosted models with sourced facts.",
                  "mainEntity": {"@type": "ItemList", "numberOfItems": count, "itemListElement": [
                      {"@type": "ListItem", "position": index + 1, "url": canonical(site_map, "/models/" + row["slug"]), "name": row["name"]}
                      for index, row in enumerate(shown)]},
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Models", "/models")))}
    return frame(site_map, name, Page("/models", "models", site_map.page("/models").title,
                 f"Context windows, prices, licences, quantizations and hardware needs for {count:,} open and hosted models, each fact with its source and date.",
                 body, structured, "models-title"))


def rendered_page(path: str, method: str, display_name: str, host: "str | None" = None):
    """Return `(body, media_type)` for a page this module renders, or None for any other address or method.

    The three list pages are pages of the site map, so `web_pages` writes their head from it as it does for
    every page; a model or endpoint page carries the head its renderer wrote. Asset references carry their
    release versions, as on every other page.
    """
    from . import web_pages
    if method not in ("GET", "HEAD") or not handles(path):
        return None
    body = _render_cached(path, display_name, today())
    if body is None:
        return None
    if media_type(path) != web_pages.HTML_MEDIA_TYPE:
        return body, media_type(path)
    head = web_pages.page_head(web_pages.packaged_site_map(), path, host, display_name)
    if head is not None:
        body = web_pages.with_page_head(body, head)
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE


def render(address: str, display_name: str) -> "bytes | None":
    """The rendered bytes of the page at an address, before the served head and asset versions are written."""
    return _render_cached(address, display_name, today()) if handles(address) else None


@lru_cache(maxsize=128)
def _render_cached(address: str, display_name: str, day: str) -> "bytes | None":
    from . import model_directory_hub as hub
    from . import model_directory_views as views
    directory, site_map = records.load_directory(), load_site_map()
    if address == "/models":
        text = models_page(directory, site_map, display_name)
    elif address == "/endpoints":
        text = hub.endpoints_page(directory, site_map, display_name)
    elif address == "/can-i-run":
        text = hub.can_i_run_page(directory, site_map, display_name)
    elif address == SITEMAP_ADDRESS:
        return sitemap(directory, site_map).encode("utf-8")
    elif address.startswith(MODEL_PREFIX):
        row = directory.model(address[len(MODEL_PREFIX):])
        text = None if row is None else views.model_page(row, directory, site_map, display_name)
    else:
        row = directory.endpoint(address[len(ENDPOINT_PREFIX):])
        text = None if row is None else views.endpoint_page(row, directory, site_map, display_name)
    return None if text is None else text.encode("utf-8")


def sitemap(directory, site_map) -> str:
    """The addresses of every directory page, for search engines."""
    addresses = list(PAGES) + ["/models/" + row["slug"] for row in directory.models] + ["/endpoints/" + row["slug"] for row in directory.endpoints]
    day = directory.manifest["built_at"][:10]
    items = "".join(f"<url><loc>{escape(canonical(site_map, address))}</loc><lastmod>{day}</lastmod></url>" for address in addresses)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="{SITEMAP_NAMESPACE}">{items}</urlset>\n'
