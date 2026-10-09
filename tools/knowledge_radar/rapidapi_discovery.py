"""Private discovery projections at the existing Executor/Parsed boundary.

The three fixed operations follow the owner's October 8 request examples and
saved sanitized access probes. Reuse: KaggleMetadataExecutor's explicit
selection, bounded projection and Parsed outcomes; public_url and clean_title
own reference/title checks. No provider SDK or new runtime is needed for these
small JSON projections. OpenWeb Ninja's own news and web-search pages were
checked on October 9 UTC; their direct API has different authentication from
the RapidAPI operations here and is not an automatic fallback:
https://www.openwebninja.com/api/real-time-news-data
https://www.openwebninja.com/api/real-time-web-search

Construct an adapter explicitly, call render({}, {}) for its fixed request,
then parse(status, bounded_body) for offline normalization. observed_at is the
caller's recorded original source-observation time, not the replay time. For
example, RealTimeWebSearch("Godot MCP", observed_at="2026-10-09T00:25:01Z").
These adapters are absent from the bulk registry() and declare available=False: no generic transport,
schedule, key resolver, customer endpoint or redistribution grant is enabled.
A later managed intake must reserve the product/account quota before dispatch,
resolve its credential only at the fixed destination, and retain only approved
metadata. Never activate the raw-response bulk runner for these sources.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re

from loop_engine.core.service_runtime.catalogue_bundle import strict_json
from query_multiplier.executors import Executor, Parsed, EMPTY, FAILED, OK, PARTIAL, RATE_LIMITED, REFUSED, WEB_KEY_PREFIX, candidate_key
from .community_intake import public_url
from .engines import clean_title
from .query_matrix import SECRET_PATTERNS, words

MAXIMUM_BYTES = 2 * 1024 * 1024
MAXIMUM_METADATA_BYTES = 128 * 1024
RIGHTS = {"delivery": "private_discovery_metadata_only", "content_is_untrusted": True,
          "licence_verified": False, "raw_republication_allowed": False,
          "customer_hosted_use_approved": False, "publication_approved": False,
          "execution_approved": False}
_INSTANT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z")
_REDACTED = re.compile(r"(?i)\[redacted|%5bredacted")
_PAGINATION_FIELDS = ("next", "nextPage", "next_page", "nextPageToken", "next_cursor", "cursor", "has_more")


def _instant(value):
    if type(value) is not str or not _INSTANT.fullmatch(value):
        raise ValueError("rapidapi_timestamp_invalid")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _stamp(value):
    return value.isoformat().replace("+00:00", "Z")


def _reference(value):
    # A sanitization placeholder is not a recovered source address. Backslashes
    # are refused rather than relying on a browser's different URL parser.
    if (type(value) is not str or _REDACTED.search(value) or any(character.isspace() for character in value)
            or any(character in value for character in "\\<>[]")
            or any(pattern.search(value) for pattern in SECRET_PATTERNS)):
        raise ValueError("rapidapi_reference_invalid")
    return public_url(value)


def _title(value):
    label, reason = clean_title(value)
    if reason or _REDACTED.search(label) or any(pattern.search(label) for pattern in SECRET_PATTERNS):
        raise ValueError("rapidapi_title_invalid")
    return label


def _failure(document):
    if any(field in document and document[field] not in (None, "")
           for field in ("error", "errors", "error_code", "error_category")):
        return True
    if "success" in document and document["success"] is not True:
        return True
    return "code" in document and (type(document["code"]) is not int or document["code"] not in (0, 200))


def _query(value):
    query = words(value)
    if re.search(r"(?i)(api[_ -]?key|access[_ -]?token|authorization|password|secret)\s*[:=]", query):
        raise ValueError("rapidapi_private_query_refused")
    return query


class _RapidApiDiscovery(Executor):
    """Explicit fixed-operation parser; the owning Loop still controls effects."""
    executor_version = "1.0.0"
    engine_kind = "search_service"
    access = "rapidapi_managed_get"
    available = False
    unavailable_reason = "managed_private_intake_and_account_quota_not_activated"
    follow_pages = 1
    expected_status = "OK"
    rows_field = "data"
    url_field = "url"
    source_time_field = None
    publisher_field = None

    def __init__(self, *, observed_at, maximum_bytes=MAXIMUM_BYTES):
        self.observed_at = _stamp(_instant(observed_at))
        if type(maximum_bytes) is not int or not 1 <= maximum_bytes <= MAXIMUM_BYTES:
            raise ValueError("rapidapi_response_bound")
        self.maximum_bytes = maximum_bytes
        self.source_rows, self.coverage = None, {}
        self.exclusions = []

    def render(self, assignment, params, *, page=1):
        if assignment != {} or params != {} or type(page) is not int or page != 1:
            raise ValueError("rapidapi_explicit_first_page_only")
        return self.request(self.path, self.parameters, page=1)

    def request_compatible(self, request):
        return type(request) is dict and request == self.render({}, {})

    def parse(self, status, body):
        self.source_rows, self.coverage, self.exclusions = None, {}, []
        if type(status) is not int:
            return Parsed(FAILED)
        if status in (401, 403):
            return Parsed(REFUSED)
        if status == 429:
            return Parsed(RATE_LIMITED)
        if status != 200 or type(body) is not bytes or len(body) > self.maximum_bytes:
            return Parsed(FAILED)
        try:
            document = strict_json(body, "rapidapi_response_json_invalid")
            if document.get("status") != self.expected_status or _failure(document):
                raise ValueError("rapidapi_provider_failure")
            rows = document.get(self.rows_field)
            if type(rows) is not list or len(rows) > self.per_page:
                raise ValueError("rapidapi_collection_changed_or_oversized")
            self.source_rows = len(rows)
            items, seen, duplicate, related, output_bytes = [], set(), 0, 0, 0
            for row in rows:
                try:
                    item, nested = self._row(row)
                    related += nested
                    if item["key"] in seen:
                        duplicate += 1
                        self.exclusions.append("duplicate_source_identity")
                        continue
                    size = len(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode())
                    if output_bytes + size > MAXIMUM_METADATA_BYTES:
                        raise ValueError("rapidapi_metadata_output_bound")
                    seen.add(item["key"])
                    output_bytes += size
                    items.append(item)
                except (ValueError, TypeError, OverflowError, OSError):
                    self.exclusions.append("invalid_or_unavailable_metadata_row")
            rejected = len(self.exclusions)
            self.coverage = {"source_rows": len(rows), "rows_considered": len(rows),
                             "accepted_rows": len(items), "duplicate_rows": duplicate,
                             "invalid_rows": rejected - duplicate, "related_rows_not_parsed": related,
                             "pagination_marker_present": any(document.get(field) not in (None, False, "") for field in _PAGINATION_FIELDS),
                             "pagination_performed": False, "source_complete": False,
                             "absence_is_not_deletion": True, "scope": "one_provider_response"}
            result = PARTIAL if rejected and items else FAILED if rejected else OK if items else EMPTY
            return Parsed(result, items, rejected=rejected)
        except (ValueError, TypeError, RecursionError):
            return Parsed(FAILED)

    def _row(self, row):
        if type(row) is not dict:
            raise ValueError("rapidapi_row_invalid")
        url, title = _reference(row.get(self.url_field)), _title(row.get("title"))
        key, kind = candidate_key(url)
        # The shared generic canonical_url omits query parameters. Article IDs
        # often live there; preserve them instead of merging unrelated stories.
        if key.startswith(WEB_KEY_PREFIX):
            key = WEB_KEY_PREFIX + url
        published = row.get(self.source_time_field) if self.source_time_field else None
        if published is not None:
            published = self._published(published)
        time_state = ("not_reported" if published is None else
                      "source_clock_ahead" if published > _instant(self.observed_at) else "source_dated")
        facts = {"provider_host": self.host, "source_operation": self.path,
                 "observed_at": self.observed_at, "source_published_at": _stamp(published) if published else None,
                 "source_time_state": time_state, "freshness_verified": False,
                 "source_access_verified_by_parser": False}
        if self.publisher_field and row.get(self.publisher_field) is not None:
            facts["publisher_reported"] = _title(row[self.publisher_field])
        if row.get("source_url") is not None:
            facts["publisher_url_reported"] = _reference(row["source_url"])
        nested = row.get("subnews", []) if self.rows_field == "items" else []
        if type(nested) is not list:
            raise ValueError("rapidapi_nested_collection_changed")
        if "hasSubnews" in row and type(row["hasSubnews"]) is not bool:
            raise ValueError("rapidapi_nested_flag_changed")
        return {"key": key, "url": url, "kind": kind, "title": title,
                "licence_reported": None, "licence_field_reported": False,
                "rights": dict(RIGHTS), "facts": facts, "source_claims_verified": False}, len(nested)

    def _published(self, value):
        return _instant(value)


class RealTimeNewsSearch(_RapidApiDiscovery):
    executor_id = "rapidapi_real_time_news_search"
    host, path = "real-time-news-data.p.rapidapi.com", "/search"
    url_field, source_time_field, publisher_field = "link", "published_datetime_utc", "source_name"

    def __init__(self, query, *, observed_at, country="US", language="en", limit=10, maximum_bytes=MAXIMUM_BYTES):
        super().__init__(observed_at=observed_at, maximum_bytes=maximum_bytes)
        query = _query(query)
        _search_scope(country, language, limit, upper=True)
        self.per_page = limit
        self.parameters = (("query", query), ("limit", str(limit)), ("time_published", "anytime"),
                           ("country", country), ("lang", language))


class RealTimeWebSearch(_RapidApiDiscovery):
    executor_id = "rapidapi_real_time_web_search"
    host, path = "real-time-web-search.p.rapidapi.com", "/search-light"

    def __init__(self, query, *, observed_at, country="us", language="en", limit=10, maximum_bytes=MAXIMUM_BYTES):
        super().__init__(observed_at=observed_at, maximum_bytes=maximum_bytes)
        query = _query(query)
        _search_scope(country, language, limit, upper=False)
        self.per_page = limit
        self.parameters = (("q", query), ("num", str(limit)), ("gl", country), ("hl", language))


class GoogleNewsLatest(_RapidApiDiscovery):
    executor_id = "rapidapi_google_news_latest"
    host, path = "google-news13.p.rapidapi.com", "/latest"
    expected_status, rows_field, url_field = "success", "items", "newsUrl"
    source_time_field, publisher_field = "timestamp", "publisher"
    per_page = 100  # Baltor's bounded first response, not a provider page-size claim.

    def __init__(self, *, observed_at, locale="en-US", maximum_bytes=MAXIMUM_BYTES):
        super().__init__(observed_at=observed_at, maximum_bytes=maximum_bytes)
        if type(locale) is not str or not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", locale):
            raise ValueError("rapidapi_locale_invalid")
        self.parameters = (("lr", locale),)

    def _published(self, value):
        if type(value) is not str or not re.fullmatch(r"[0-9]{1,15}", value) or int(value) > 253402300799999:
            raise ValueError("rapidapi_millisecond_timestamp_invalid")
        return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=int(value))


def _search_scope(country, language, limit, *, upper):
    if type(country) is not str or not re.fullmatch(r"[A-Z]{2}" if upper else r"[a-z]{2}", country):
        raise ValueError("rapidapi_country_invalid")
    if type(language) is not str or not re.fullmatch(r"[a-z]{2}", language):
        raise ValueError("rapidapi_language_invalid")
    # Qualification uses the observed ten-result operation, not an inferred
    # maximum from another provider plan or endpoint.
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("rapidapi_result_bound")


def quota_observation(headers, *, product_host, account_scope, observed_at):
    """Project counters, never grant dispatch or create another quota ledger.

    account_scope is a host-owned subscription identity, shared across all its
    keys/apps, never a caller key reference. The existing durable intake must
    bind and persist it. Missing product remaining counts or invalid counters
    hold rather than imply free requests. Quotas may represent overage
    thresholds, not prepaid permission.
    Sources checked October 9 UTC:
    https://docs.rapidapi.com/docs/keys-and-key-rotation
    https://docs.rapidapi.com/docs/response-headers
    """
    if product_host not in (RealTimeNewsSearch.host, RealTimeWebSearch.host, GoogleNewsLatest.host):
        raise ValueError("rapidapi_quota_product_invalid")
    if type(account_scope) is not str or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", account_scope):
        raise ValueError("rapidapi_quota_account_scope_invalid")
    moment = _instant(observed_at)
    groups, invalid = {"product": {}, "platform": {}}, []
    prefixes = {"x-ratelimit-requests-": "product", "x-ratelimit-rapid-free-plans-hard-limit-": "platform",
                "x-rate-limit-rapid-free-plans-hard-limit-": "platform"}
    for name, value in headers.items() if isinstance(headers, dict) else headers:
        if type(name) is not str:
            raise ValueError("rapidapi_header_name_invalid")
        name = name.lower()
        for prefix, group in prefixes.items():
            field = name[len(prefix):] if name.startswith(prefix) else ""
            if field not in ("limit", "remaining", "reset"):
                continue
            values = groups[group]
            if field in values or type(value) is not str or not re.fullmatch(r"[0-9]{1,12}", value):
                invalid.append(group + ":" + field)
                values[field] = None
            else:
                values[field] = int(value)
    for name, values in groups.items():
        for field in ("limit", "remaining", "reset"):
            values.setdefault(field, None)
        if values["limit"] is not None and values["remaining"] is not None and values["remaining"] > values["limit"]:
            invalid.append(name + ":remaining_exceeds_limit")
        try:
            values["reset_at"] = _stamp(moment + timedelta(seconds=values["reset"])) if values["reset"] else None
        except OverflowError:
            invalid.append(name + ":reset_out_of_range")
            values["reset_at"] = None
    product, platform = groups["product"], groups["platform"]
    exhausted = next((name for name in ("product", "platform") if groups[name]["remaining"] == 0), None)
    hold = ("quota_header_invalid" if invalid else
            "unknown_provider_reset" if exhausted and not groups[exhausted]["reset_at"] else
            exhausted + "_quota_exhausted" if exhausted else
            "product_quota_unknown" if product["remaining"] is None else None)
    return {"quota_scope": "rapidapi:" + account_scope + ":" + product_host,
            "scope_basis": "provider_product_and_host_bound_subscription_not_key",
            "observed_at": _stamp(moment), "product": product, "platform": platform,
            "invalid_fields": sorted(set(invalid)), "hold": hold,
            "pricing_verified": False, "authorizes_dispatch": False}
