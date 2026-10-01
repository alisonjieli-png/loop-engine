"""Unlisted, editorially reviewed handoffs within the existing website renderer.

These packaged public records are distinct from the private feedback store.
Reading a page grants no authority and neither claims nor completes a task.
The page and JSON representation share exact content and revision identity.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from html import escape
import json

ADDRESSES = {"/dot-context": "context", "/dot-feedback": "feedback"}
ROUTES = (*ADDRESSES, *(address + ".json" for address in ADDRESSES))
RECORD_TYPE = "baltor_dot_brief/v1"
FIELDS = {"record_type", "title", "updated_at", "review_after", "summary", "sections", "tasks", "links"}
TASK_FIELDS = {"id", "title", "status", "assignment", "deliverable", "acceptance"}
STATUSES = {"ready", "needs_retest", "research", "awaiting_evidence", "complete"}


def validate_record(value):
    """Validate only the public editorial contract; personal-data review is also required."""
    def text(value):
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 6000
    if not isinstance(value, dict) or set(value) != FIELDS or value["record_type"] != RECORD_TYPE:
        raise ValueError("invalid dot brief fields or version")
    if not text(value["title"]) or not text(value["summary"]):
        raise ValueError("invalid dot brief text")
    moments = []
    for name in ("updated_at", "review_after"):
        if not isinstance(value[name], str) or len(value[name]) > 64:
            raise ValueError("invalid dot brief time")
        moment = datetime.fromisoformat(value[name].replace("Z", "+00:00"))
        if moment.tzinfo is None:
            raise ValueError("dot brief times require a timezone")
        moments.append(moment)
    if moments[1] <= moments[0]:
        raise ValueError("dot brief review follows its update")
    for name in ("sections", "tasks", "links"):
        if not isinstance(value[name], list) or len(value[name]) > 100:
            raise ValueError("invalid dot brief collection")
    identifiers = set()
    for row in value["tasks"]:
        if (not isinstance(row, dict) or set(row) != TASK_FIELDS or not all(text(v) for v in row.values())
                or row["status"] not in STATUSES or row["id"] in identifiers
                or not all(ch.isascii() and (ch.isalnum() or ch == "-") for ch in row["id"])):
            raise ValueError("invalid dot brief task")
        identifiers.add(row["id"])
    for row in value["sections"]:
        if (not isinstance(row, dict) or set(row) != {"title", "items"} or not text(row["title"])
                or not isinstance(row["items"], list) or not 1 <= len(row["items"]) <= 30
                or not all(text(item) for item in row["items"])):
            raise ValueError("invalid dot brief section")
    for row in value["links"]:
        if (not isinstance(row, dict) or set(row) != {"label", "url"} or not all(text(v) for v in row.values())
                or row["url"].startswith("//") or "\\" in row["url"]
                or any(ch.isspace() or ord(ch) < 32 for ch in row["url"])):
            raise ValueError("invalid dot brief link")
        from .http_auth import validate_public_url
        from .web_pages import packaged_site_map
        validate_public_url(packaged_site_map().canonical_origin + row["url"]
                            if row["url"].startswith("/") else row["url"])
    return value


@lru_cache(maxsize=2)
def load_record(name):
    from .web_pages import read_packaged_asset
    if name not in ADDRESSES.values():
        raise ValueError("unknown dot brief")
    return validate_record(json.loads(read_packaged_asset("dot/" + name + ".json")))


def encoded(record):
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def revision(record):
    return sha256(encoded(record)).hexdigest()


def page_body(record, address):
    esc = escape
    tasks = "".join('<article class="md-band" id="' + esc(row["id"]) + '">'
        + '<p class="eyebrow">' + esc(row["id"]) + ' · ' + esc(row["status"].replace("_", " ")) + '</p>'
        + '<h2>' + esc(row["title"]) + '</h2><p class="md-reading">' + esc(row["assignment"]) + '</p>'
        + '<p class="md-reading"><strong>Deliver:</strong> ' + esc(row["deliverable"]) + '</p>'
        + '<p class="md-reading"><strong>Acceptance:</strong> ' + esc(row["acceptance"]) + '</p></article>'
        for row in record["tasks"])
    sections = "".join('<section class="md-band"><h2>' + esc(row["title"]) + '</h2><ul class="md-plain">'
        + "".join('<li>' + esc(line) + '</li>' for line in row["items"]) + '</ul></section>'
        for row in record["sections"])
    links = "".join('<li><a href="' + esc(row["url"], quote=True) + '">' + esc(row["label"]) + '</a></li>'
        for row in record["links"])
    return ('<div class="md-band md-intro"><p class="eyebrow">Unlisted working brief · Public content</p>'
        '<h1 id="dot-title">' + esc(record["title"]) + '</h1><p class="lede">' + esc(record["summary"]) + '</p>'
        '<p class="md-reading">Updated <time datetime="' + esc(record["updated_at"]) + '">'
        + esc(record["updated_at"]) + '</time>. Review due <time datetime="' + esc(record["review_after"]) + '">'
        + esc(record["review_after"]) + '</time>.</p><p class="md-reading"><a href="' + address
        + '.json">Read the same brief as JSON</a></p><details><summary>Content revision</summary><p class="md-reading">'
        + revision(record) + '</p></details></div>' + sections + tasks
        + '<section class="md-band"><h2>Working links</h2><ul class="md-plain">' + links + '</ul></section>')


def rendered(path, method, display_name, host=None):
    from . import web_pages
    from .model_directory_pages import Page, frame
    address = path.removesuffix(".json")
    if method not in ("GET", "HEAD") or address not in ADDRESSES:
        return None
    record = load_record(ADDRESSES[address])
    if path.endswith(".json"):
        return encoded(record), "application/json"
    site_map = web_pages.packaged_site_map()
    page = Page(address, ADDRESSES[address], record["title"], record["summary"],
                page_body(record, address), {}, "dot-title")
    body = frame(site_map, display_name, page).encode("utf-8")
    body = web_pages.with_page_head(body, web_pages.page_head(site_map, address, host, display_name))
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE
