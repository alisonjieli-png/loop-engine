"""The public website as static files for the edge: the `static_content_network` engine of web page delivery.

The `web_page_delivery` slot names two engine kinds, `service_process_pages` (the service renders each page per
request, as it does today) and `static_content_network`. This module is the second one's export: every page and
asset the service would send an anonymous reader, rendered by the service's own page functions, written as
content-addressed files with a manifest of the headers the service sends with each. A Worker at the edge
(`edge/site_edge_worker.js`) serves them and passes every other request to the origin, so a release of the
origin, which today keeps the website down while the catalogue view is built (85 seconds for 39,710 items on
October 5, 2026), no longer takes the website down.

```text
site_edge_manifest/v1
├── files        address -> content digest, media type, header class, whether its head names the hostname's root
├── roots        hostname -> the address its root shows; the Worker writes the root meta tag exactly as the
│                service writes it (web_pages.with_page_head), checked here against the service's own render
├── classes      the exact header sets: page, page that search engines skip, cacheable asset, creative preview
├── origin       addresses the edge never serves itself: the library page (one catalogue release), account and
│                staff pages' data, every API, the protocol endpoint, OAuth, counted links
└── unavailable  the page and the refusal record a reader gets while the origin cannot answer
```

What stays at the origin and why: a page whose bytes depend on the catalogue the service serves now (`/library`,
the served counts) is exported with each catalogue release by the release train, not at request time; the page
view counter (`public_links.viewed`) runs at the origin only, so pages served at the edge are not counted until
the counter moves to an edge-side store; every API route needs the service store.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

MANIFEST_RECORD_TYPE = "site_edge_manifest/v1"
ENGINE_ID, ENGINE_KIND = "cloudflare_static_site", "static_content_network"
ROOT_META = '  <meta name="baltor-root-address" content="{address}">\n'
_HEAD_END = re.compile(r"</head\s*>", re.IGNORECASE)
#: Addresses the edge always passes to the origin: their bytes depend on state the edge does not hold.
ORIGIN_PREFIXES = ("/api/", "/mcp", "/oauth/", "/.well-known/", "/out/", "/auth/")
ORIGIN_ADDRESSES = ("/library", "/feeds/catalogue.json", "/feeds/catalogue.rss", "/feeds/catalogue.md")
UNAVAILABLE_PAGE = "/__edge/unavailable"


class StaticExportError(ValueError):
    """An address the export cannot reproduce exactly."""


def _digest(body):
    return hashlib.sha256(body).hexdigest()


def with_root_meta(body: bytes, address: str) -> bytes:
    """The bytes the service sends for a page with a head on a hostname whose root is `address`.

    `web_pages.with_page_head` writes the root meta tag last, just before the head closes; the edge writes the same
    line in the same place, so the export stores one copy of each page for every hostname.
    """
    text = body.decode("utf-8")
    ends = _HEAD_END.findall(text)
    if len(ends) != 1:
        raise StaticExportError("a page with a head has exactly one closing head tag")
    index = text.index(ends[0])
    return (text[:index] + ROOT_META.format(address=address) + text[index:]).encode("utf-8")


def page_headers(identity_origin="", *, creative_preview=False):
    """The service's own page headers (`ServiceHttpApplication._page_headers`), for a host with this identity origin."""
    from .http import ServiceHttpApplication

    class Identity:
        class configuration:  # noqa: N801 - mirrors the adapter attribute the method reads
            project_url = identity_origin

    class Host:
        browser_identity = Identity if identity_origin else None
    return ServiceHttpApplication._page_headers(Host, creative_preview=creative_preview)


def static_addresses(*, include_model_details=True):
    """Every address the export renders, in a stable order."""
    from . import catalogue_feed, dot_pages, feed_source_collections, model_directory_pages, public_good_page, red_team_page, status_pages
    from .web_pages import GENERATED_WEB_FILES, WEB_ASSETS
    addresses = list(WEB_ASSETS) + list(GENERATED_WEB_FILES)
    addresses += list(model_directory_pages.PAGES) + [model_directory_pages.SITEMAP_ADDRESS]
    if include_model_details:
        rendered = model_directory_pages.rendered_page(model_directory_pages.SITEMAP_ADDRESS, "GET", "Baltor", None)
        for location in re.findall(r"<loc>([^<]+)</loc>", rendered[0].decode("utf-8")):
            path = "/" + location.split("://", 1)[1].split("/", 1)[1] if "://" in location else location
            if path.startswith((model_directory_pages.MODEL_PREFIX, model_directory_pages.ENDPOINT_PREFIX)):
                addresses.append(path)
    addresses += [catalogue_feed.PAGE, public_good_page.ADDRESS, red_team_page.ADDRESS,
                  *dot_pages.ROUTES, *status_pages.ADDRESSES]
    addresses += list(feed_source_collections.formats())
    seen, ordered = set(), []
    for address in addresses:
        # The OAuth consent page and the sign-in callbacks stay with the origin, beside the routes they call.
        if address not in seen and address not in ORIGIN_ADDRESSES and not address.startswith(ORIGIN_PREFIXES):
            seen.add(address)
            ordered.append(address)
    return ordered


def render(address, host, display_name, library_population=None):
    """(bytes, media type) as the service's web route renders `address` for `host`, or None; the same order."""
    from . import catalogue_feed, dot_pages, feed_source_collections, public_good_page, red_team_page, status_pages
    from .model_directory_pages import rendered_page
    from .web_pages import packaged_site_map, served_asset
    if address in feed_source_collections.formats():
        from .model_directory_pages import canonical
        return feed_source_collections.render(address, canonical(packaged_site_map(), ""))
    asset = served_asset(address, "GET", display_name, host, library_population=library_population)
    for renderer in (rendered_page, public_good_page.rendered, dot_pages.rendered, red_team_page.rendered,
                     status_pages.rendered, catalogue_feed.rendered_page):
        if asset is not None:
            break
        asset = renderer(address, "GET", display_name, host)
    return asset


def wire_content_type(media_type):
    """The Content-Type the service's web framework sends for a media type: text types gain the UTF-8 charset."""
    if media_type.startswith("text/") and "charset=" not in media_type.lower():
        return media_type + "; charset=utf-8"
    return media_type


def header_class(address, media_type):
    from . import dot_pages, feed_source_collections
    from .web_pages import CACHEABLE_WEB_ASSETS, CREATIVE_PREVIEW_PATH, HTML_MEDIA_TYPE
    if address == CREATIVE_PREVIEW_PATH:
        return "creative_preview"
    if address in dot_pages.ROUTES:
        return "page_private"
    if address in feed_source_collections.formats():
        return "feed_source"
    if media_type == HTML_MEDIA_TYPE and address.startswith("/assets/"):
        return "page_fragment"
    if address in CACHEABLE_WEB_ASSETS:
        return "asset"
    return "page"


def header_classes(identity_origin):
    """Each class's exact headers: the page headers, the robots rule, the cache rule and the validator rule."""
    from .web_pages import PUBLIC_ASSET_CACHE_CONTROL
    from .feed_source_collections import CACHE_CONTROL as SOURCE_CACHE_CONTROL
    page = {**page_headers(identity_origin), "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    return {"page": {"headers": page, "etag": False},
            "page_fragment": {"headers": {**page, "X-Robots-Tag": "noindex"}, "etag": False},
            "page_private": {"headers": {**page, "X-Robots-Tag": "noindex, nofollow, noarchive"}, "etag": True},
            "feed_source": {"headers": {**page, "Cache-Control": SOURCE_CACHE_CONTROL}, "etag": True},
            # The creative preview is an HTML file under /assets/, so it also carries the fragment's robots rule.
            "creative_preview": {"headers": {**page_headers(identity_origin, creative_preview=True),
                                             "X-Robots-Tag": "noindex", "Cache-Control": "no-store",
                                             "X-Content-Type-Options": "nosniff"},
                                 "etag": False},
            "asset": {"headers": {**page, "Cache-Control": PUBLIC_ASSET_CACHE_CONTROL}, "etag": True}}


@dataclass(frozen=True)
class SiteExport:
    manifest: dict
    files: dict

    @property
    def export_id(self):
        return self.manifest["export_id"]


def export_site(*, display_name="Baltor", identity_origin="", library_population=None, include_model_details=True,
                hosts=None):
    """Render every static address once for the canonical hostname, and prove the edge's root rule for every other."""
    from .refusals import guidance
    from .web_pages import packaged_site_map, server_error_page
    site_map = packaged_site_map()
    canonical = site_map.canonical_hostname
    # The service always hands its pages a population reader, and a reader that answers None writes "Not measured";
    # the export hands the same, so a page shows exactly what the service would show for this snapshot.
    population = lambda: library_population  # noqa: E731
    roots = {entry["hostname"]: entry["address"] for entry in json.loads(
        Path(__file__).with_name("web_site_map.json").read_text("utf-8"))["hostnames"]}
    roots = {host: address for host, address in roots.items() if hosts is None or host in hosts}
    files, entries = {}, {}
    probe = next((host for host, address in roots.items() if address != "/"), None)
    for address in static_addresses(include_model_details=include_model_details):
        rendered = render(address, canonical, display_name, population)
        if rendered is None:
            continue
        body, media_type = rendered
        head = False
        # At the root address the hostname chooses the page; the roots are proved separately below.
        if probe is not None and media_type.startswith("text/html") and address != "/":
            other = render(address, probe, display_name, population)
            if other is None:
                raise StaticExportError(f"{address} renders on one hostname and not on another")
            if other[0] != body:
                if with_root_meta(body, roots[probe]) != other[0]:
                    raise StaticExportError(f"{address} differs between hostnames beyond the root meta tag")
                head = True
        digest = _digest(body)
        files[digest] = body
        entries[address] = {"sha256": digest, "media_type": wire_content_type(media_type),
                            "class": header_class(address, media_type),
                            "head": head, "bytes": len(body)}
    for host, root in roots.items():
        if root == "/":
            continue
        rendered = render("/", host, display_name, population)
        source = entries.get(root)
        if rendered is None or source is None or (with_root_meta(files[source["sha256"]], root) if source["head"]
                                                  else files[source["sha256"]]) != rendered[0]:
            raise StaticExportError(f"the root of {host} is not its root page with the root meta tag")
    message, action = guidance("service_unavailable", 503)
    unavailable = server_error_page(display_name, 503, message, action, None)
    files[_digest(unavailable)] = unavailable
    entries[UNAVAILABLE_PAGE] = {"sha256": _digest(unavailable), "media_type": "text/html; charset=utf-8",
                                 "class": "page", "head": False, "bytes": len(unavailable)}
    body = {"canonical_hostname": canonical, "roots": roots, "classes": header_classes(identity_origin),
            "files": entries, "origin_prefixes": list(ORIGIN_PREFIXES), "origin_addresses": list(ORIGIN_ADDRESSES),
            "unavailable": {"page": UNAVAILABLE_PAGE, "code": "service_unavailable", "status": 503,
                            "message": message, "next_action": action, "retry_after_seconds": 30}}
    export_id = _digest(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return SiteExport({"record_type": MANIFEST_RECORD_TYPE, "export_id": export_id, **body}, files)


def write_export(export, folder):
    """The manifest and the content-addressed files, as the edge Worker and a static assets upload read them."""
    folder = Path(folder)
    (folder / "files").mkdir(parents=True, exist_ok=True)
    for digest, body in export.files.items():
        (folder / "files" / digest).write_bytes(body)
    (folder / "manifest.json").write_text(json.dumps(export.manifest, sort_keys=True, indent=1), "utf-8")
    return folder


LOAD_MAGIC = b"BALTORS1"


def kv_entries(export):
    """The keys and bytes of one export in a KV namespace: the manifest and each content-addressed file."""
    entries = [(f"{export.export_id}/manifest", json.dumps(export.manifest, sort_keys=True).encode("utf-8"))]
    entries += [(f"{export.export_id}/f/{digest}", body) for digest, body in sorted(export.files.items())]
    return entries


def load_payload(export_id, entries):
    """One signed load of KV entries: a magic word, a JSON header of keys, sizes and digests, then the bytes."""
    header = json.dumps({"export_id": export_id, "files": [{"key": key, "bytes": len(body), "sha256": _digest(body)}
                                                          for key, body in entries]},
                        sort_keys=True, separators=(",", ":")).encode("utf-8")
    return LOAD_MAGIC + len(header).to_bytes(4, "little") + header + b"".join(body for _key, body in entries)
