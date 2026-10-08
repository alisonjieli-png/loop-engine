"""Trendshift public JSON-LD and documented API facts, parsed as data only.

Rankings remain Trendshift/GitHub source claims. Names and source identifiers
are not independently resolved here; historical ranks never date current
stars/forks. Source prose, advertisements and author profiles are excluded.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
import re

from .trendshift_request import GITHUB, MAXIMUM_BYTES, PUBLIC, SPIKES, TRENDING, TrendshiftError, valid_cursor
from .records import day

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}\Z")


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:raise TrendshiftError("trendshift_duplicate_json_field")
        value[key] = item
    return value


def json_data(body):
    if len(body) > MAXIMUM_BYTES:raise TrendshiftError("trendshift_response_too_large")
    try:
        return json.loads(body, object_pairs_hook=_object, parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
    except (ValueError, RecursionError, UnicodeDecodeError) as error:
        raise TrendshiftError("trendshift_json_invalid") from error


def repository(value):
    if type(value) is not str or not _NAME.fullmatch(value) or value.rsplit("/", 1)[1] in (".", ".."):
        raise TrendshiftError("trendshift_repository_invalid")
    return value, "https://github.com/" + value


def _integer(value, name, *, minimum=None):
    if type(value) is not int or not -(2**63) <= value < 2**63 or (minimum is not None and value < minimum):
        raise TrendshiftError("trendshift_invalid_" + name)
    return value


def _language(value):
    if type(value) is not str or len(value) > 80 or any(ord(character) < 32 for character in value):
        raise TrendshiftError("trendshift_language_invalid")
    return value or None


@dataclass(frozen=True)
class TrendshiftPage:
    rows: tuple
    source_date: "str | None"
    next_cursor: "str | None"
    complete: bool
    source_rows: int
    excluded: tuple = ()


class _StructuredData(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active, self.parts, self.documents = False, [], []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.active = dict(attrs).get("type", "").lower() == "application/ld+json"
            self.parts = []

    def handle_data(self, data):
        if self.active:self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            self.documents.append(json_data("".join(self.parts)))
            self.active = False


def public_page(body, request):
    if len(body) > MAXIMUM_BYTES:raise TrendshiftError("trendshift_response_too_large")
    parser = _StructuredData()
    try:parser.feed(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError) as error:raise TrendshiftError("trendshift_html_invalid") from error
    lists = [value for value in parser.documents if type(value) is dict and value.get("@type") == "ItemList"
             and value.get("url") in ("https://trendshift.io", "https://trendshift.io/")
             and value.get("@context") in ("https://schema.org", "https://schema.org/")]
    if len(lists) != 1:raise TrendshiftError("trendshift_public_list_missing_or_ambiguous")
    value = lists[0];items = value.get("itemListElement")
    if type(items) is not list or len(items) > 100 or type(value.get("numberOfItems")) is not int or value["numberOfItems"] != len(items):
        raise TrendshiftError("trendshift_public_list_shape")
    rows, excluded, seen = [], [], set()
    for position, entry in enumerate(items, 1):
        try:
            if type(entry) is not dict or entry.get("@type") != "ListItem" or type(entry.get("position")) is not int or entry["position"] != position:
                raise TrendshiftError("trendshift_rank_invalid")
            item = entry.get("item")
            if type(item) is not dict or item.get("@type") != "SoftwareSourceCode":raise TrendshiftError("trendshift_item_shape")
            name, url = repository(item.get("name"))
            if item.get("codeRepository") != url or item.get("url") != url:raise TrendshiftError("trendshift_repository_url_mismatch")
            page_url = entry.get("url")
            if type(page_url) is not str or not re.fullmatch(r"https://trendshift\.io/repositories/[1-9][0-9]{0,18}", page_url):
                raise TrendshiftError("trendshift_page_url_invalid")
            source_id = _integer(int(page_url.rsplit("/", 1)[1]), "source_id", minimum=1)
            if name.lower() in seen:raise TrendshiftError("trendshift_repository_duplicate")
            seen.add(name.lower())
            rows.append({"full_name": name, "github_url": url, "github_repository_id": None,
                         "trendshift_repository_id": source_id, "source_page": page_url,
                         "source_rank": position, "source_page_position": position, "rank_provider": "trendshift",
                         "language": _language(item.get("programmingLanguage", "")), "identity_status": "slug_only_not_rename_stable"})
        except TrendshiftError as error:excluded.append(error.code)
    if items and not rows:raise TrendshiftError("trendshift_no_valid_rows")
    return TrendshiftPage(tuple(rows[:request.limit]), None, None, False, len(items), tuple(excluded))


def signal_page(body, request):
    document = json_data(body)
    if type(document) is not dict or type(document.get("data")) is not list or len(document["data"]) > 100:
        raise TrendshiftError("trendshift_api_collection_invalid")
    source_date, cursor = None, document.get("next_cursor")
    if request.kind == GITHUB:
        if set(document) - {"$schema", "data", "trend_date", "language"}:raise TrendshiftError("trendshift_api_fields_changed")
        if "trend_date" not in document or "language" not in document:raise TrendshiftError("trendshift_github_metadata_missing")
        expected_language = None if request.language is None or request.language.lower() == "all" else request.language.lower()
        if document["language"] != expected_language:raise TrendshiftError("trendshift_list_language_mismatch")
        source_date = document["trend_date"]
        if source_date is not None:day(source_date, "trend_date")
        if document["data"] and source_date is None:raise TrendshiftError("trendshift_github_date_missing")
        if request.period is not None and source_date != request.period:raise TrendshiftError("trendshift_requested_date_mismatch")
    else:
        if set(document) - {"$schema", "data", "next_cursor"}:raise TrendshiftError("trendshift_api_fields_changed")
        if "next_cursor" not in document or (cursor is not None and not valid_cursor(cursor)):
            raise TrendshiftError("trendshift_cursor_missing_or_invalid")
    rows, excluded, seen, names, last_rank = [], [], set(), set(), 0
    for position, item in enumerate(document["data"], 1):
        try:
            if type(item) is not dict:raise TrendshiftError("trendshift_item_shape")
            name, url = repository(item.get("full_name"))
            allowed = {"id", "ghr_id", "full_name", "gain"} if request.kind == SPIKES else {"id", "ghr_id", "full_name", "language", "stars_now", "forks_now"}
            allowed |= {"rank"} if request.kind == GITHUB else {"score", "stars_gained", "forks_gained"} if request.kind == TRENDING else set()
            if set(item) != allowed:raise TrendshiftError("trendshift_api_row_fields_changed")
            github_id = _integer(item.get("ghr_id"), "github_id", minimum=1)
            source_id = _integer(item.get("id"), "source_id", minimum=1)
            if github_id in seen or name.lower() in names:raise TrendshiftError("trendshift_repository_duplicate")
            seen.add(github_id)
            names.add(name.lower())
            rank = _integer(item.get("rank"), "rank", minimum=1) if request.kind == GITHUB else (None if request.cursor else position)
            if rank is not None and rank <= last_rank:raise TrendshiftError("trendshift_rank_order_invalid")
            if rank is not None:last_rank = rank
            row = {"full_name": name, "github_url": url, "github_repository_id": github_id,
                   "trendshift_repository_id": source_id, "source_page": "https://trendshift.io/repositories/" + str(source_id),
                   "source_rank": rank, "source_page_position": position,
                   "rank_provider": "github_via_trendshift" if request.kind == GITHUB else "trendshift",
                   "identity_status": "provider_reported_github_id_not_independently_resolved"}
            fields = ("gain",) if request.kind == SPIKES else ("stars_now", "forks_now")
            if request.kind == TRENDING:fields += ("stars_gained", "forks_gained", "score")
            for name in fields:row[name] = _integer(item.get(name), name, minimum=0 if name.endswith("_now") else None)
            if request.kind == SPIKES:
                if row["gain"] < request.min_gain or (request.max_gain is not None and row["gain"] > request.max_gain):
                    raise TrendshiftError("trendshift_gain_outside_requested_band")
            else:
                row["language"] = _language(item.get("language"))
                if request.language and request.language.lower() != "all" and (row["language"] or "").lower() != request.language.lower():
                    raise TrendshiftError("trendshift_repository_language_mismatch")
            rows.append(row)
        except (TrendshiftError, ValueError) as error:
            excluded.append(error.code if isinstance(error, TrendshiftError) else "trendshift_row_invalid")
    if document["data"] and not rows:raise TrendshiftError("trendshift_no_valid_rows")
    return TrendshiftPage(tuple(rows[:request.limit]), source_date, cursor,
                         not cursor and not excluded and len(rows) <= request.limit, len(document["data"]), tuple(excluded))


def parse_page(body, request):
    return public_page(body, request) if request.engine == PUBLIC else signal_page(body, request)
