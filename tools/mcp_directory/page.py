"""The generated parts of the directory page: facts, category chips, the first rows and the structured data.

Kind: pure rendering. The page itself, `web_assets/directory.html`, is written by hand; this module replaces
only the regions between `<!-- generated:NAME -->` and `<!-- /generated:NAME -->`, so a reviewer reads the
page as it is served and a rebuild changes only what the data changed. The first rows are rendered here, in the
default order, so a reader without the page script and a search engine see real listings; the page script draws
the same rows with the same markup once the data files load.

Third-party text (a listing's name, publisher, description and addresses) carries data-listing-text, so the
website's word rules read only Baltor's own words on this page.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from html import escape

from loop_engine.core.service_runtime.commercial_relationship import DISCLOSURE_SECTION_ID

from .records import AUTH_BITS, OFFERING_BITS, TRANSPORT_BITS

#: How many rows the served page holds before the page script runs.
FIRST_ROWS = 40
#: Every label the page shows for a coded value. The manifest carries this table, so the page script and this
#: renderer read one list.
LABELS = {
    "location_kinds": {"remote-http": "Remote endpoint", "remote-sse": "Remote endpoint, server-sent events", "npm": "npm",
                       "pypi": "PyPI", "oci": "Container image", "nuget": "NuGet", "cargo": "crates.io",
                       "mcpb": "MCP bundle", "api": "Agent API"},
    "offering": {"remote": "Remote MCP endpoint", "package": "MCP server package", "source": "Source code only",
                 "api": "Agent API or SDK"},
    "origins": {"maker": "Publisher", "other": "Community", "unknown": "Not matched"},
    "transports": {"stdio": "Local process (stdio)", "streamable-http": "Streamable HTTP", "sse": "Server-sent events"},
    "auth": {"none": "No sign-in declared", "key": "API key or token", "oauth": "OAuth", "payment": "Pays per call"},
    "publisher_kinds": {"domain": "verified domain", "github": "GitHub account", "repository": "code owner", "unknown": ""},
    "licence_bases": {"": "", "repository": "as the code host reports it", "package": "as the package registry reports it"},
    "repository_states": {"unknown": "", "found": "", "missing": "not found on GitHub when last checked",
                          "archived": "archived on GitHub"},
    "sources": {"registry": "Official MCP Registry", "codex": "Baltor research of September 23, 2026",
                "docs": "Publisher documentation", "github": "GitHub MCP directory", "docker": "Docker MCP Catalog"},
    #: The page of a package on its registry, without the scheme; the page script adds the package name.
    "package_pages": {"npm": "www.npmjs.com/package/", "pypi": "pypi.org/project/", "nuget": "www.nuget.org/packages/",
                      "cargo": "crates.io/crates/"},
}
_REGION = "<!-- generated:{name} -->"
_REGION_END = "<!-- /generated:{name} -->"
SECURE_SCHEME = "https"
SECURE = SECURE_SCHEME + "://"
SCHEMA_ORG = SECURE + "schema.org"


def replace_region(html: str, name: str, content: str) -> str:
    """The page with one generated region replaced; a missing or repeated region is refused."""
    start, end = _REGION.format(name=name), _REGION_END.format(name=name)
    if html.count(start) != 1 or html.count(end) != 1 or html.index(start) > html.index(end):
        raise ValueError(f"the page needs exactly one generated region {name!r}")
    head, rest = html.split(start, 1)
    _old, tail = rest.split(end, 1)
    return head + start + content + end + tail


def region(html: str, name: str) -> str:
    start, end = _REGION.format(name=name), _REGION_END.format(name=name)
    return html.split(start, 1)[1].split(end, 1)[0]


def chrome_from_index(index_html: str) -> "tuple[str, str]":
    """The shared header and footer markup of the one-page app, taken as they are served."""
    header = re.search(r"<header class=\"header\">[\s\S]*?</header>", index_html)
    footer = re.search(r"<footer class=\"site-footer\">[\s\S]*?</footer>", index_html)
    if not header or not footer:
        raise ValueError("index.html has no shared header or footer to copy")
    return header.group(0), footer.group(0)


def _bits(value: int, table: dict) -> list:
    return [name for name, bit in table.items() if value & bit]


def row_html(row: dict, manifest: dict) -> str:
    """One listing row. The page script's drawRow builds the same markup from the same row."""
    labels = manifest["labels"]
    kinds = manifest["location_kinds"]
    identity = escape(row["id"], quote=True)
    offering = ", ".join(labels["offering"][name] for name in _bits(row["offering"], OFFERING_BITS))
    transports = ", ".join(labels["transports"][name] for name in _bits(row["transports"], TRANSPORT_BITS))
    auth = ", ".join(labels["auth"][name] for name in _bits(row["auth"], AUTH_BITS))
    origin = manifest["origins"][row["origin"]]
    publisher_kind = labels["publisher_kinds"][manifest["publisher_kinds"][row["publisher_kind"]]]
    location = row["locations"][0] if row["locations"] else None
    where = (f'<span class="row-where-kind">{escape(labels["location_kinds"][kinds[location[0]]])}</span> '
             f'<code class="row-where-value" data-listing-text>{escape(location[1])}</code>') if location else (
        '<span class="row-where-kind">Code repository</span> '
        f'<code class="row-where-value" data-listing-text>{escape(row["repository"])}</code>')
    more = len(row["locations"]) - 1 if row["locations"] else 0
    licence = manifest["licences"][row["licence"]] or "Licence not known"
    docs = row["website"] or row["repository"]
    docs_link = (f'<a class="row-docs" href="{escape(SECURE + docs, quote=True)}" rel="noopener" '
                 f'data-row-docs>Documentation</a>') if docs else ""
    sources = [entry["id"] for entry in manifest["sources"] if row["sources"] & entry["bit"]]
    return (
        f'<div class="directory-row" role="listitem" id="{identity}" data-row>'
        f'<div class="row-main"><h3 class="row-name"><a class="row-link" href="#{identity}">'
        f'<span data-listing-text>{escape(row["name"])}</span></a></h3>'
        f'<p class="row-publisher"><span data-listing-text>{escape(row["publisher"] or "Publisher not named")}</span>'
        + (f' <span class="row-note">{escape(publisher_kind)}</span>' if publisher_kind and row["publisher"] else "")
        + f'</p><p class="row-description" data-listing-text>{escape(row["description"] or "")}</p></div>'
        f'<div class="row-get"><p class="row-offering">{escape(offering)}</p><p class="row-where">{where}'
        + (f' <span class="row-more">and {more} more</span>' if more > 0 else "") + '</p></div>'
        f'<div class="row-connect"><p class="row-transport">{escape(transports or "Connection not declared")}</p>'
        f'<p class="row-auth">{escape(auth)}</p></div>'
        f'<div class="row-facts"><p class="row-origin" data-origin="{escape(origin)}">{escape(labels["origins"][origin])}</p>'
        f'<p class="row-licence">{escape(licence)}</p><p class="row-sources">{escape(", ".join(labels["sources"][name] for name in sources))}</p>'
        f'{docs_link}</div></div>')


def decode_row(values: list, manifest: dict) -> dict:
    return dict(zip(manifest["columns"], values))


def facts_html(manifest: dict) -> str:
    registry = next(entry for entry in manifest["sources"] if entry["id"] == "registry")
    checked = registry.get("checked") or manifest["generated_at"][:10]
    shown = date.fromisoformat(checked[:10])
    used = sum(1 for entry in manifest["sources"] if entry["rows"])
    return (f'<span data-directory-count>{manifest["row_count"]:,}</span> listings from {used} sources. '
            f'The list was last checked on <time datetime="{shown.isoformat()}">{shown.strftime("%B")} {shown.day}, {shown.year}</time>.')


def chips_html(manifest: dict) -> str:
    chips = ['<button type="button" class="directory-chip" data-category="" aria-pressed="true">All '
             f'<span class="chip-count">{manifest["row_count"]:,}</span></button>']
    for entry in sorted(manifest["categories"], key=lambda item: (item["id"] == "other", -item["rows"], item["label"])):
        if entry["rows"]:
            chips.append(f'<button type="button" class="directory-chip" data-category="{escape(entry["id"], quote=True)}" '
                         f'aria-pressed="false">{escape(entry["label"])} <span class="chip-count">{entry["rows"]:,}</span></button>')
    return "".join(chips)


def structured_data(manifest: dict, first_rows: list, canonical: str) -> str:
    """A CollectionPage with the Dataset it publishes and the first listings, as JSON-LD."""
    registry = next(entry for entry in manifest["sources"] if entry["id"] == "registry")
    modified = (registry.get("checked") or manifest["generated_at"])[:10]
    origin = canonical.split("/", 3)
    site = "/".join(origin[:3])
    value = {
        "@context": SCHEMA_ORG,
        "@graph": [
            {"@type": "CollectionPage", "@id": canonical, "url": canonical, "name": "MCP server and agent API directory",
             "description": "A free, searchable list of the companies, products and projects that offer a Model Context Protocol "
                            "server or an API for agents, with where to get each one, how it connects and how it signs in.",
             "isAccessibleForFree": True, "dateModified": modified, "inLanguage": "en",
             "isPartOf": {"@type": "WebSite", "name": "Baltor", "url": site + "/"},
             "mainEntity": {"@type": "ItemList", "numberOfItems": manifest["row_count"], "itemListOrder": SCHEMA_ORG + "/ItemListUnordered",
                            "itemListElement": [{"@type": "ListItem", "position": index + 1, "name": row["name"],
                                                 "url": canonical + "#" + row["id"]} for index, row in enumerate(first_rows)]}},
            {"@type": "Dataset", "@id": canonical + "#dataset", "name": "MCP server and agent API directory",
             "description": "One row for each offering, merged from public sources, with its category, offering kind, "
                            "place to get it, transport, sign-in, licence when known and sources.",
             "url": canonical, "isAccessibleForFree": True, "dateModified": modified,
             "creator": {"@type": "Organization", "name": "Baltor.AI", "url": site + "/"},
             "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                               "contentUrl": site + "/assets/directory/manifest.json"}]},
        ],
    }
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("</", "<\\/")


def last_checked_label(manifest: dict) -> str:
    registry = next(entry for entry in manifest["sources"] if entry["id"] == "registry")
    return (registry.get("checked") or manifest["generated_at"])[:10]


def days_to_date(days: int, day_zero: str) -> str:
    return (date.fromisoformat(day_zero) + timedelta(days=days)).isoformat() if days else ""


__all__ = ["FIRST_ROWS", "LABELS", "DISCLOSURE_SECTION_ID", "chips_html", "chrome_from_index", "decode_row", "facts_html",
           "region", "replace_region", "row_html", "structured_data"]
