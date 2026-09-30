"""Bounded community metadata parsing behind the radar's source edge.

RSS/Atom and explicit research batches produce the same passive Lead record.
Bodies are transient data used for keyword hints and link extraction, never
instructions, executable material or a licence grant. No author profile,
comment archive, media download, automatic link follow or code execution occurs.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

from .engines import clean_title

REGISTRY = Path(__file__).with_name("community-watch-v1.json")
LEAD_VERSION = "community_workflow_lead/v1"
MAXIMUM_BODY = 2 * 1024 * 1024
_FORBIDDEN_QUERY = re.compile(r"(?i)(token|password|secret|api.?key|authorization|signature)")


def public_url(value: str, base: str = "") -> str:
    """Canonical public HTTPS reference. A reference is not permission to fetch it."""
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise ValueError("invalid_reference")
    part = urlsplit(urljoin(base, unescape(value)))
    host = (part.hostname or "").lower()
    if (part.scheme != "https" or not host or part.username or part.password or part.port not in (None, 443)
            or "." not in host or host.endswith((".local", ".internal", ".localhost"))):
        raise ValueError("nonpublic_reference")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("literal_address_refused")
    query = parse_qsl(part.query, keep_blank_values=True)
    if any(_FORBIDDEN_QUERY.search(key) for key, _value in query):
        raise ValueError("credential_shaped_reference")
    query = [(key, value) for key, value in query if not key.lower().startswith("utm_")]
    return urlunsplit(("https", host, part.path or "/", urlencode(query), ""))


def read_registry(path: Path = REGISTRY) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    fields = {"record_type", "revision", "maximum_reads_per_tick", "maximum_entries_per_source",
              "maximum_harness_runs_per_day", "maximum_work_items_per_tick", "sources", "research_topics", "tools", "signals"}
    if set(value) != fields or value["record_type"] != "community_watch_registry/v1":
        raise ValueError("unsupported_community_registry")
    for name in ("maximum_reads_per_tick", "maximum_entries_per_source", "maximum_harness_runs_per_day",
                 "maximum_work_items_per_tick"):
        if type(value[name]) is not int or not 1 <= value[name] <= 100:
            raise ValueError("invalid_community_limit")
    seen = set()
    for source in value["sources"]:
        if (set(source) != {"id", "engine", "url", "interval_seconds", "terms_url", "use", "enabled"}
                or source["engine"] != "rss_atom" or source["use"] != "internal_link_discovery"
                or type(source["enabled"]) is not bool or type(source["interval_seconds"]) is not int
                or source["interval_seconds"] < 3600 or not re.fullmatch(r"[a-z][a-z0-9_]{0,60}", source["id"])
                or source["id"] in seen):
            raise ValueError("invalid_community_source")
        seen.add(source["id"])
        public_url(source["url"])
        public_url(source["terms_url"])
        keys = [key for key, _value in parse_qsl(urlsplit(source["url"]).query, keep_blank_values=True)]
        if len(keys) != len(set(keys)):
            raise ValueError("ambiguous_source_query")
        # Public web research is separate. Do not silently switch it to a Reddit data feed.
        host = urlsplit(source["url"]).hostname
        if host == "reddit.com" or host.endswith(".reddit.com"):
            raise ValueError("reddit_feed_requires_separate_access_adapter")
    for group in ("tools", "signals"):
        if not isinstance(value[group], dict) or any(not isinstance(v, list) or not v
                or any(not isinstance(term, str) or not 1 <= len(term) <= 100 for term in v)
                for v in value[group].values()):
            raise ValueError("invalid_signal_dictionary")
    topic_ids = set()
    for topic in value["research_topics"]:
        if (set(topic) != {"id", "query", "domains", "interval_seconds"}
                or not re.fullmatch(r"[a-z][a-z0-9_]{0,60}", topic["id"]) or topic["id"] in topic_ids
                or not isinstance(topic["query"], str) or not 1 <= len(topic["query"]) <= 1500
                or type(topic["interval_seconds"]) is not int or topic["interval_seconds"] < 3600
                or not isinstance(topic["domains"], list) or not 1 <= len(topic["domains"]) <= 10):
            raise ValueError("invalid_research_topic")
        for domain in topic["domains"]:
            if not isinstance(domain, str) or public_url("https://" + domain + "/") != "https://" + domain + "/":
                raise ValueError("invalid_research_domain")
        topic_ids.add(topic["id"])
    return value


class _Content(HTMLParser):
    """Transient text and href values only; no script, style, media or executable HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.hidden = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag == "a" and not self.hidden:
            self.links.extend(value for name, value in attrs if name == "href" and value)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def hints(text: str, dictionary: dict) -> tuple[str, ...]:
    return tuple(sorted(key for key, terms in dictionary.items()
                        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE) for term in terms)))


@dataclass(frozen=True)
class Lead:
    source_id: str
    url: str
    title: str
    published_at: str | None
    content_digest: str
    tools_mentioned: tuple[str, ...]
    signals: tuple[str, ...]
    linked_sources: tuple[str, ...]
    priority: int
    record_type: str = LEAD_VERSION

    def to_dict(self):
        return {**asdict(self), "evidence_class": "unverified_community_report", "reproduced": False,
                "reuse_rights": "not_established", "component_approved": False,
                "classification": "deterministic_keyword_hints_not_verified_workflow_steps"}

    @property
    def identity(self):
        return "community.lead." + hashlib.sha256(self.url.encode()).hexdigest()


def _time(text):
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00")) if re.match(r"^\d{4}-\d{2}-\d{2}T", text) else parsedate_to_datetime(text)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value.tzinfo else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def make_lead(source_id, url, title, content, published_at, registry) -> Lead | None:
    url = public_url(url)
    title, refusal = clean_title(title)
    if refusal:
        return None
    parser = _Content()
    parser.feed(content[:100_000])
    text = title + " " + " ".join(parser.text)
    tools, signals = hints(text, registry["tools"]), hints(text, registry["signals"])
    if not signals:
        return None
    links = set()
    for raw in parser.links[:100]:
        try:
            link = public_url(raw, url)
        except ValueError:
            continue
        if link != url:
            links.add(link)
    score = len(tools) + 2 * len(set(signals) & {"workflow_detail", "failure_report", "agent_control"})
    score += 3 * any(urlsplit(link).hostname == "github.com" for link in links)
    material = {"title": title, "tools": tools, "signals": signals, "links": sorted(links)[:20],
                "body_digest": hashlib.sha256(content.encode()).hexdigest()}
    return Lead(source_id, url, title, _time(published_at),
                hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest(),
                tools, signals, tuple(sorted(links)[:20]), score)


def parse_feed(body: bytes, source: dict, registry: dict) -> tuple[list[Lead], dict]:
    if len(body) > MAXIMUM_BODY:
        raise ValueError("feed_too_large")
    text = body.decode("utf-8-sig")
    if "\x00" in text or re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
        raise ValueError("xml_entity_or_encoding_refused")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        raise ValueError("malformed_feed_xml") from error
    local = lambda tag: tag.rsplit("}", 1)[-1]
    if local(root.tag) not in ("rss", "feed", "RDF"):
        raise ValueError("not_a_feed")
    items = [row for row in root.iter() if local(row.tag) in ("item", "entry")]
    limit = registry["maximum_entries_per_source"]
    leads, skipped = [], 0
    for item in items[:limit]:
        fields, links = {}, []
        for child in item:
            name = local(child.tag)
            fields[name] = "".join(child.itertext())
            if name == "link" and child.get("rel", "alternate") == "alternate":
                links.append(child.get("href") or (child.text or ""))
        try:
            lead = make_lead(source["id"], public_url(links[0], source["url"]), fields.get("title", ""),
                             fields.get("encoded") or fields.get("content") or fields.get("description") or fields.get("summary", ""),
                             fields.get("published") or fields.get("pubDate") or fields.get("updated", ""), registry)
        except (ValueError, IndexError):
            lead = None
        if lead is None:
            skipped += 1
        else:
            leads.append(lead)
    return leads, {"entries_seen": len(items), "entries_considered": min(len(items), limit),
                   "irrelevant_or_refused": skipped, "truncated": len(items) > limit,
                   "historical_coverage": "latest_feed_window_only", "absence_is_not_deletion": True}
