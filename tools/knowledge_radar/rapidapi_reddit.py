"""Authenticated Reddit metadata intake through the owner's selected RapidAPI source.

The endpoint, header destination and operation are fixed. Replies become the
same Lead records as other community sources. Bodies are used transiently for
classification; profiles, comments, credentials and copied code are not stored.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
import hashlib
import http.client
import json
import re
import time
from urllib.parse import urlencode, urlsplit

from .community_intake import MAXIMUM_BODY, Lead, make_lead, public_url

HOST = "reddit34.p.rapidapi.com"
PATH = "/getPostsBySubreddit"
REFERENCE = {"application": "loop-engine", "service": HOST, "account": "owner", "purpose": "research-api"}
RESPONSE_VERSION = "rapidapi_reddit_observation/v1"


@dataclass(frozen=True)
class RedditRequest:
    subreddit: str
    sort: str = "new"
    timeout_seconds: float = 25.0
    maximum_bytes: int = MAXIMUM_BODY

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_]{3,21}", self.subreddit):
            raise ValueError("invalid_subreddit")
        if self.sort not in ("new", "hot", "rising"):
            raise ValueError("unsupported_subreddit_sort")
        if not 0 < self.timeout_seconds <= 60 or type(self.maximum_bytes) is not int or self.maximum_bytes < 1:
            raise ValueError("invalid_source_resource_allocation")


@dataclass(frozen=True)
class RedditObservation:
    status: int
    elapsed_seconds: float
    response_bytes: int
    body_sha256: str
    leads: tuple[Lead, ...] = ()
    coverage: dict = field(default_factory=dict)
    quota: dict = field(default_factory=dict)
    reason: str = ""
    record_type: str = RESPONSE_VERSION

    def report(self):
        return {"record_type": self.record_type, "status": self.status,
                "elapsed_seconds": self.elapsed_seconds, "response_bytes": self.response_bytes,
                "body_sha256": self.body_sha256, "coverage": self.coverage,
                "quota": self.quota, "reason": self.reason, "leads": len(self.leads),
                "raw_bodies_stored": False, "author_profiles_stored": False,
                "automatic_retries": 0, "components_published": 0}


def credential():
    """Resolve one named Secret Service entry without exporting its value."""
    import secretstorage
    collection = secretstorage.get_default_collection(secretstorage.dbus_init())
    if collection.is_locked():
        raise RuntimeError("research_keyring_locked")
    items = list(collection.search_items(REFERENCE))
    if len(items) != 1:
        raise RuntimeError("research_credential_missing_or_ambiguous")
    value = items[0].get_secret().decode()
    if not value or not value.isascii() or any(c.isspace() for c in value):
        raise RuntimeError("invalid_research_credential")
    return value


def quota_from_headers(headers, now):
    values = {name.lower(): value for name, value in headers}
    def number(name):
        value = values.get(name, "")
        return int(value) if re.fullmatch(r"\d{1,12}", value) else None
    reset = number("x-ratelimit-requests-reset")
    return {"requests_limit": number("x-ratelimit-requests-limit"),
            "requests_remaining": number("x-ratelimit-requests-remaining"),
            "reset_after_seconds": reset,
            "reset_at_unix": now + reset if reset is not None else None,
            "pricing_verified": False}


def parse_posts(body, request, registry):
    if len(body) > request.maximum_bytes:
        raise ValueError("source_response_too_large")
    try:
        document = json.loads(body)
    except (ValueError, UnicodeError):
        raise ValueError("source_response_not_json") from None
    if (not isinstance(document, dict) or document.get("success") is not True
            or not isinstance(document.get("data"), dict)
            or not isinstance(document["data"].get("posts"), list)):
        raise ValueError("unsupported_reddit_source_response")
    posts = document["data"]["posts"]
    leads, seen, refused, irrelevant, duplicate = [], set(), 0, 0, 0
    for envelope in posts:
        row = envelope.get("data") if isinstance(envelope, dict) else None
        if not isinstance(row, dict):
            refused += 1
            continue
        try:
            if str(row.get("subreddit", "")).casefold() != request.subreddit.casefold():
                raise ValueError("subreddit_binding_mismatch")
            url = public_url(row.get("permalink", ""), "https://www.reddit.com")
            part = urlsplit(url)
            expected = "/r/" + request.subreddit.casefold() + "/comments/"
            if part.hostname != "www.reddit.com" or not part.path.casefold().startswith(expected):
                raise ValueError("post_identity_refused")
            if url in seen:
                duplicate += 1
                continue
            seen.add(url)
            title, content = row.get("title"), row.get("selftext", "")
            if not isinstance(title, str) or not isinstance(content, str):
                raise ValueError("invalid_post_text")
            if row.get("removed_by_category") or content in ("[removed]", "[deleted]"):
                raise ValueError("removed_post")
            links = re.findall(r"https://[^\s<>\"']+", content)
            links.append(row.get("url", ""))
            safe = []
            for link in links:
                try:
                    normalized = public_url(link)
                except ValueError:
                    continue
                if normalized != url:
                    safe.append(normalized)
            text = escape(content) + " ".join('<a href="' + escape(link, quote=True) + '">source</a>' for link in sorted(set(safe)))
            created = row.get("created_utc")
            published = (datetime.fromtimestamp(created, timezone.utc).isoformat()
                         if type(created) in (int, float) else "")
            lead = make_lead("rapidapi_reddit_" + request.subreddit.lower(), url, title,
                             text, published, registry)
            if lead is None:
                irrelevant += 1
            else:
                leads.append(lead)
        except (ValueError, TypeError, OverflowError, OSError):
            refused += 1
    return tuple(leads), {"posts_returned": len(posts), "posts_considered": len(posts),
                          "leads": len(leads), "refused": refused, "without_signal_hints": irrelevant,
                          "duplicate_posts": duplicate, "historical_coverage": "one_provider_response",
                          "pagination_performed": False, "absence_is_not_deletion": True}


class RapidApiRedditReader:
    """One fixed-host GET; redirects, retries and body retention are absent."""
    def __init__(self, resolve_credential=credential, connect=http.client.HTTPSConnection, clock=time.perf_counter):
        self.resolve_credential, self.connect, self.clock = resolve_credential, connect, clock

    def read(self, request, registry):
        token = self.resolve_credential()
        connection = self.connect(HOST, timeout=request.timeout_seconds)
        started = self.clock()
        try:
            connection.request("GET", PATH + "?" + urlencode({"sort": request.sort, "subreddit": request.subreddit + "/"}),
                               headers={"x-rapidapi-key": token, "x-rapidapi-host": HOST, "Accept": "application/json"})
            response = connection.getresponse()
            body = response.read(request.maximum_bytes + 1)
            quota = quota_from_headers(response.getheaders(), time.time())
            status = response.status
            digest = hashlib.sha256(body).hexdigest()
            leads, coverage, reason = (), {}, ""
            if status != 200:
                reason = "source_http_" + str(status)
            else:
                try:
                    leads, coverage = parse_posts(body, request, registry)
                except ValueError as error:
                    reason = str(error)
            return RedditObservation(status, round(self.clock() - started, 3), len(body), digest, leads, coverage, quota, reason)
        except (OSError, http.client.HTTPException):
            # Headers and exception strings can contain credentials. Return a fixed diagnostic.
            return RedditObservation(0, round(self.clock() - started, 3), 0, "", reason="source_outcome_unknown")
        finally:
            connection.close()
