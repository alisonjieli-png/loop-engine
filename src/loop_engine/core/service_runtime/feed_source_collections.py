"""Read-only source collections for the public Feeds page.

This is a release-curated website projection, not a source collector, a new
knowledge store or a qualification result. It reads only the packaged directory
and returns source references in JSON Feed or Markdown. No upstream request,
account access, installation or model call happens while rendering a collection.
Its digest changes with the directory bytes; a request never invents freshness.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
import hashlib
from html import escape
from importlib.resources import files
import json
import re
from urllib.parse import urlsplit

from .records import ServiceRuntimeError

RECORD_TYPE = "agent_feed_source_directory/v1"
COLLECTION_RECORD_TYPE = "agent_feed_source_collection/v1"
SOURCE_RECORD_TYPE = "agent_feed_source_reference/v1"
FEED_VERSION = "https://jsonfeed.org/version/1.1"
JSON_MEDIA_TYPE, MARKDOWN_MEDIA_TYPE = "application/feed+json", "text/markdown"
DIRECTORY_PATH = "/feeds/sources"
COLLECTION_PREFIX = "/feeds/collections/"
CACHE_CONTROL = "public, max-age=300"
MAXIMUM_DIRECTORY_BYTES = 131072
MAXIMUM_OUTPUT_BYTES = 262144
MAXIMUM_SOURCES, MAXIMUM_COLLECTIONS = 128, 64
SOURCE_KINDS = frozenset(("benchmark", "evaluation_method", "provider_documentation", "directory",
                          "api_documentation", "publisher_updates"))
_SLUG = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


def _require(condition, code="feed_source_directory_invalid"):
    if not condition:
        raise ServiceRuntimeError(code)


def _text(value):
    _require(isinstance(value, str) and 0 < len(value) <= 2048
             and all(ord(character) >= 32 for character in value))
    return value


def _fields(value, expected):
    _require(type(value) is dict and set(value) == set(expected))


def _slug(value):
    _require(isinstance(value, str) and _SLUG.fullmatch(value) is not None)
    return value


def _url(value):
    _text(value)
    try:
        parsed = urlsplit(value)
        _require(parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None
                 and parsed.password is None and parsed.port is None and not parsed.query and not parsed.fragment
                 and re.fullmatch(r"[a-z0-9.-]+", parsed.hostname) is not None
                 and not any(character in value for character in ('<', '>', '"', '\\', ' ')))
    except ValueError:
        raise ServiceRuntimeError("feed_source_directory_invalid") from None
    return value


def _strings(value, maximum=32):
    _require(type(value) is list and 0 < len(value) <= maximum)
    result = tuple(_text(item) for item in value)
    _require(len(result) == len(set(result)))
    return result


@dataclass(frozen=True)
class Source:
    """A source reference and its documented access limits, not collected source content."""

    id: str
    name: str
    url: str
    kind: str
    description: str
    access: str
    reuse: str

    def record(self):
        return {"record_type": SOURCE_RECORD_TYPE, **self.__dict__}


@dataclass(frozen=True)
class Collection:
    id: str
    title: str
    group: str
    purpose: str
    source_ids: tuple[str, ...]
    compare_fields: tuple[str, ...]
    agent_task: str
    decision_question: str
    review_trigger: str

    def record(self):
        return {"record_type": COLLECTION_RECORD_TYPE, **self.__dict__,
                "source_ids": list(self.source_ids), "compare_fields": list(self.compare_fields)}


@dataclass(frozen=True)
class Directory:
    source_docs_checked_on: str
    digest: str
    limitations: tuple[str, ...]
    sources: tuple[Source, ...]
    collections: tuple[Collection, ...]


def parse_directory(body: bytes) -> Directory:
    """Refuse unknown versions, unsupported fields, invalid links and broken references."""
    _require(type(body) is bytes and len(body) <= MAXIMUM_DIRECTORY_BYTES)
    try:
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                _require(key not in result)
                result[key] = value
            return result
        data = json.loads(body, object_pairs_hook=unique_object)
    except (ValueError, UnicodeDecodeError):
        raise ServiceRuntimeError("feed_source_directory_invalid") from None
    _fields(data, ("record_type", "source_docs_checked_on", "refresh_mode", "data_scope",
                   "limitations", "sources", "collections"))
    _require(data["record_type"] == RECORD_TYPE and data["refresh_mode"] == "release_curated"
             and data["data_scope"] == "source_descriptions_only")
    checked = _text(data["source_docs_checked_on"])
    try:
        _require(date.fromisoformat(checked).isoformat() == checked)
    except ValueError:
        raise ServiceRuntimeError("feed_source_directory_invalid") from None
    limitations = _strings(data["limitations"])
    _require(type(data["sources"]) is list and 0 < len(data["sources"]) <= MAXIMUM_SOURCES)
    sources = []
    for row in data["sources"]:
        _fields(row, ("id", "name", "url", "kind", "description", "access", "reuse"))
        _require(isinstance(row["kind"], str) and row["kind"] in SOURCE_KINDS)
        sources.append(Source(_slug(row["id"]), _text(row["name"]), _url(row["url"]), row["kind"],
                              _text(row["description"]), _text(row["access"]), _text(row["reuse"])))
    source_ids = {source.id for source in sources}
    _require(len(source_ids) == len(sources) and len({source.url for source in sources}) == len(sources))
    _require(type(data["collections"]) is list and 0 < len(data["collections"]) <= MAXIMUM_COLLECTIONS)
    collections = []
    for row in data["collections"]:
        _fields(row, ("id", "title", "group", "purpose", "source_ids", "compare_fields", "agent_task",
                      "decision_question", "review_trigger"))
        references = _strings(row["source_ids"])
        _require(set(references) <= source_ids)
        collections.append(Collection(_slug(row["id"]), _text(row["title"]), _text(row["group"]),
                                      _text(row["purpose"]), references, _strings(row["compare_fields"]),
                                      _text(row["agent_task"]), _text(row["decision_question"]),
                                      _text(row["review_trigger"])))
    _require(len({collection.id for collection in collections}) == len(collections))
    _require({reference for collection in collections for reference in collection.source_ids} == source_ids)
    return Directory(checked, hashlib.sha256(body).hexdigest(), limitations, tuple(sources), tuple(collections))


@lru_cache(maxsize=1)
def directory():
    try:
        body = files("loop_engine").joinpath("core", "service_runtime", "feed_source_collections.json").read_bytes()
    except OSError:
        raise ServiceRuntimeError("feed_source_directory_invalid") from None
    return parse_directory(body)


def handles(path):
    """Classify a route without loading content or depending on directory health."""
    if not isinstance(path, str):
        return False
    if path in (DIRECTORY_PATH + ".json", DIRECTORY_PATH + ".md"):
        return True
    if not path.startswith(COLLECTION_PREFIX):
        return False
    name, separator, extension = path[len(COLLECTION_PREFIX):].rpartition(".")
    return bool(separator and extension in ("json", "md") and _SLUG.fullmatch(name))


def formats():
    paths = (DIRECTORY_PATH, *(COLLECTION_PREFIX + item.id for item in directory().collections))
    return {path + extension: media for path in paths
            for extension, media in ((".json", JSON_MEDIA_TYPE), (".md", MARKDOWN_MEDIA_TYPE))}


def _selection(path):
    _require(path in formats(), "feed_source_format_unknown")
    data = directory()
    selected = tuple(item for item in data.collections if path == DIRECTORY_PATH + ".json"
                     or path == DIRECTORY_PATH + ".md" or path.rsplit(".", 1)[0] == COLLECTION_PREFIX + item.id)
    selected_ids = {source_id for item in selected for source_id in item.source_ids}
    return data, selected, tuple(source for source in data.sources if source.id in selected_ids)


def _base(origin):
    _require(isinstance(origin, str) and re.fullmatch(r"https://[a-z0-9.-]+(?::[0-9]{1,5})?", origin) is not None)
    return origin


def render(path, origin):
    """Render a bounded release snapshot. A source's publication date is deliberately absent."""
    data, collections, sources = _selection(path)
    base = _base(origin)
    title = collections[0].title if len(collections) == 1 else "Baltor source collections"
    if path.endswith(".json"):
        document = {"version": FEED_VERSION, "title": title, "home_page_url": base + "/feeds#source-collections",
                    "feed_url": base + path, "description": data.limitations[0], "language": "en",
                    "_baltor": {"record_type": RECORD_TYPE, "directory_digest": data.digest,
                                "source_docs_checked_on": data.source_docs_checked_on,
                                "refresh_mode": "release_curated", "data_scope": "source_descriptions_only",
                                "limitations": list(data.limitations),
                                "collections": [item.record() for item in collections]},
                    "items": [{"id": f"{source.id}:{data.digest}", "url": source.url, "title": source.name,
                               "content_text": " ".join((source.description, source.access, source.reuse)),
                               "_baltor": source.record()} for source in sources]}
        text = json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = (f"# {title}\n\nCurated source collection, not a live research digest.\n\n"
                f"Source documentation checked: {data.source_docs_checked_on} (UTC). Directory digest: `{data.digest}`.\n\n"
                + "\n\n".join(data.limitations) + "\n")
        source_by_id = {source.id: source for source in sources}
        for item in collections:
            text += (f"\n## {item.title}\n\n{item.purpose}\n\nDecision question: {item.decision_question}\n\n"
                     f"When to revisit: {item.review_trigger}\n\nAgent research task: {item.agent_task}\n\nCompare:\n\n")
            text += "".join(f"- {field}\n" for field in item.compare_fields)
            text += "\nSources:\n\n"
            for source_id in item.source_ids:
                source = source_by_id[source_id]
                text += f"- [{source.name}]({source.url}): {source.description} {source.access} {source.reuse}\n"
        text += f"\n[Browse Baltor Feeds]({base}/feeds). Selecting a collection does not schedule a job or enable a service.\n"
    body = text.encode("utf-8")
    _require(len(body) <= MAXIMUM_OUTPUT_BYTES)
    return body, formats()[path]


def page_section():
    """Server-rendered source cards work without JavaScript and expose real download paths."""
    data = directory()
    by_id = {source.id: source for source in data.sources}
    body = ('<section class="md-band" id="source-collections"><p class="eyebrow">Curated source collections</p>'
            '<h2>Start with the decision your agent needs to make.</h2>'
            f'<p class="md-reading">{len(data.collections)} collections with {len(data.sources)} source references. '
            'Each download includes a decision question, comparison fields, a review trigger and source-access notes. '
            'These are source directories, not live digests or current benchmark rankings.</p>'
            f'<p class="md-reading">Source documentation checked <time datetime="{data.source_docs_checked_on}">'
            f'{data.source_docs_checked_on}</time> (UTC). Updates follow website releases; no daily refresh is promised.</p>'
            '<div class="md-actions"><a class="button secondary" href="/feeds/sources.json">All sources as JSON Feed</a>'
            '<a class="button secondary" href="/feeds/sources.md">All sources as Markdown</a></div>'
            '<nav class="md-contents" aria-label="Source collection groups">')
    groups = tuple(dict.fromkeys(item.group for item in data.collections))
    body += "".join(f'<a href="#source-group-{index}">{escape(group)}</a>' for index, group in enumerate(groups))
    body += '</nav>'
    for index, group in enumerate(groups):
        body += f'<h3 id="source-group-{index}">{escape(group)}</h3><ul class="md-cards">'
        for item in (item for item in data.collections if item.group == group):
            body += (f'<li class="md-card feed-source-card" id="collection-{item.id}"><h4>{escape(item.title)}</h4>'
                     f'<p>{escape(item.purpose)}</p><p>Sources: '
                     + ", ".join(f'<a href="{escape(by_id[source_id].url, quote=True)}" rel="noreferrer" '
                                 f'data-listing-text>{escape(by_id[source_id].name)}</a>' for source_id in item.source_ids)
                     + '</p><details><summary>Decision and review checklist</summary>'
                     f'<p>{escape(item.decision_question)}</p><p>When to revisit: {escape(item.review_trigger)}</p>'
                     f'<p>{escape(item.agent_task)}</p><ul>'
                     + "".join(f'<li>{escape(field)}</li>' for field in item.compare_fields)
                     + '</ul></details><div class="md-actions">'
                     f'<a class="button secondary" href="{COLLECTION_PREFIX}{item.id}.json" '
                     f'aria-label="{escape(item.title)} as JSON Feed">JSON Feed</a>'
                     f'<a class="button secondary" href="{COLLECTION_PREFIX}{item.id}.md" '
                     f'aria-label="{escape(item.title)} as Markdown">Markdown</a></div></li>')
        body += '</ul>'
    return body + ('<p class="md-reading">Source links do not authorize copying, installing, connecting accounts or sending '
                   'messages. Review each provider\'s terms and each item\'s licence. Product Hunt commercial API ingestion '
                   'requires its permission and is not enabled here.</p></section>')
