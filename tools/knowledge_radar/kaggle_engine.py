"""Kaggle metadata adapter at the existing Executor/Parsed edge; no source-content export.

The adapter is selected explicitly by read_kaggle.py, not added to the bulk
runner that stores raw responses. Published-page prose and account fields
are discarded. EVERYONE is the SDK's public listing view; missing per-row
visibility and licence evidence remain unknown in each private lead.
"""
from hashlib import sha256
from html import unescape
import json
import re
from urllib.parse import urlsplit

from loop_engine.core.service_runtime.catalogue_bundle import strict_json
from query_multiplier.executors import Executor, Parsed, EMPTY, FAILED, OK, PARTIAL, RATE_LIMITED, REFUSED
from .engines import clean_title
from .kaggle_request import AUTH, COMPETITION, COMPETITIONS, ENGINE, HOST, KEY_VARIABLE, MAXIMUM_BYTES, NOTEBOOKS, PAGES, PATHS, RIGHTS, KaggleError, safe_cursor

ORIGIN = "https://www.kaggle.com"
_COMPETITION_URL = re.compile(r"https://(?:www\.)?kaggle\.com/competitions/([a-z0-9][a-z0-9-]{1,119})/?\Z")
_NOTEBOOK_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,49}/[A-Za-z0-9][A-Za-z0-9_-]{0,149}\Z")
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z\Z")


def title(value):
    text, refusal = clean_title(value)
    if refusal:raise KaggleError("kaggle_title_refused")
    return text


def whole(value, field, *, positive=False):
    if type(value) is not int or not (1 if positive else 0) <= value < 2**63:raise KaggleError("kaggle_" + field + "_invalid")
    return value


def dated(value):
    if value is None:return None
    if type(value) is not str or not _TIME.fullmatch(value):raise KaggleError("kaggle_time_invalid")
    from datetime import datetime
    try:datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:raise KaggleError("kaggle_time_invalid") from None
    return value


def competition_url(value):
    match = _COMPETITION_URL.fullmatch(value) if type(value) is str else None
    if not match:raise KaggleError("kaggle_competition_url_invalid")
    return ORIGIN + "/competitions/" + match.group(1), match.group(1)


def notebook_url(value):
    if type(value) is not str:raise KaggleError("kaggle_notebook_ref_invalid")
    for prefix in (ORIGIN + "/code/", "https://kaggle.com/code/"):
        if value.startswith(prefix):value = value[len(prefix):]
    if not _NOTEBOOK_REF.fullmatch(value):raise KaggleError("kaggle_notebook_ref_invalid")
    return ORIGIN + "/code/" + value, value


def page_references(content):
    """Only passive public source links, never text, scripts, data downloads or account routes."""
    if type(content) is not str:raise KaggleError("kaggle_page_content_invalid")
    urls = set()
    for value in re.findall(r'https://[^\s<>"\)\]\}]+', unescape(content)):
        part = urlsplit(value.rstrip(".,;"))
        if part.username or part.password or part.query or part.fragment or part.port not in (None, 443):continue
        segments = part.path.strip("/").split("/")
        if any(segment in (".", "..") for segment in segments):continue
        if segments[0] in ("login", "logout", "settings", "account", "signup", "join", "sessions", "orgs", "organizations", "apps", "users"):continue
        if part.hostname == "github.com" and re.fullmatch(r"/[A-Za-z0-9_.-]{1,50}/[A-Za-z0-9_.-]{1,150}(?:/[A-Za-z0-9_.-]+)*", part.path):
            urls.add("https://github.com" + part.path)
        elif part.hostname in ("www.kaggle.com", "kaggle.com") and re.fullmatch(r"/(?:competitions|code)/[A-Za-z0-9_/-]{1,220}", part.path):
            urls.add(ORIGIN + part.path)
    return sorted(urls)[:20]


class KaggleMetadataExecutor(Executor):
    executor_id, executor_version = ENGINE, "1.0.0"
    engine_kind, host, access = "catalogue_api", HOST, "https_post_key"
    key_variable, minimum_interval, daily_ceiling, follow_pages = KEY_VARIABLE, 1.0, 20, 1

    def __init__(self, selection):
        self.selection = selection
        self.per_page = selection.page_size
        self.source_rows = None
        self.exclusions = []

    def render(self, assignment, params, *, page=1):
        if assignment or params != self.selection.to_record() or page != self.selection.page:
            raise KaggleError("kaggle_explicit_selection_required")
        return self.request(PATHS[self.selection.operation], [], page=page, method="POST", body=self.selection.body())

    def request_compatible(self, request):
        return request == self.render({}, self.selection.to_record(), page=self.selection.page)

    def parse(self, status, body):
        self.source_rows, self.exclusions = None, []
        if status in (401, 403):return Parsed(REFUSED)
        if status == 429:return Parsed(RATE_LIMITED)
        if status != 200 or len(body) > MAXIMUM_BYTES:return Parsed(FAILED)
        try:
            data = strict_json(body, "kaggle_json_invalid")
            if type(data.get("code")) is int and data["code"] >= 400:
                return Parsed(REFUSED if data["code"] in (401, 403) else RATE_LIMITED if data["code"] == 429 else FAILED)
            op = self.selection.operation
            if op == AUTH:raise KaggleError("kaggle_auth_result_is_not_content")
            name = "competitions" if op == COMPETITIONS else "pages" if op == PAGES else "kernels"
            rows = [data] if op == COMPETITION else data.get(name)
            if type(rows) is not list or len(rows) > (64 if op == PAGES else self.selection.page_size):
                raise KaggleError("kaggle_collection_invalid")
            self.source_rows = len(rows)
            cursor = data.get("nextPageToken") or None if op != COMPETITION else None
            if cursor is not None and not safe_cursor(cursor):raise KaggleError("kaggle_cursor_invalid")
            seen, items, output_bytes = set(), [], 0
            for row in rows:
                try:
                    if type(row) is not dict:raise KaggleError("kaggle_row_invalid")
                    item = self._row(row)
                    if item["key"] in seen:raise KaggleError("kaggle_duplicate_identity")
                    item_bytes = len(json.dumps(item, sort_keys=True, separators=(",", ":")).encode())
                    if output_bytes + item_bytes > 32768:raise KaggleError("kaggle_metadata_output_bound")
                    output_bytes += item_bytes
                    seen.add(item["key"]);items.append(item)
                except (KaggleError, ValueError, TypeError):self.exclusions.append("invalid_or_private_metadata_row")
            return Parsed(PARTIAL if self.exclusions else OK if items else EMPTY, items, rejected=len(self.exclusions), next_cursor=cursor)
        except (ValueError, RecursionError, TypeError):return Parsed(FAILED)

    def _row(self, row):
        op, facts, links = self.selection.operation, {}, []
        if op in (COMPETITION, COMPETITIONS):
            url, slug = competition_url(row.get("url") or row.get("ref"))
            if row.get("ref") and competition_url(row["ref"])[0] != url:raise KaggleError("kaggle_url_mismatch")
            if op == COMPETITION and slug != self.selection.competition:raise KaggleError("kaggle_competition_mismatch")
            key, kind, label = "kaggle-competition:" + str(whole(row.get("id"), "id", positive=True)), "competition", title(row.get("title"))
            facts.update(competition_slug=slug, deadline=dated(row.get("deadline")),
                         numeric_identity_basis="provider_reported_not_independently_resolved")
            for field in ("teamCount", "kernelCount"):
                if field in row:facts[field] = whole(row[field], "count")
        elif op == NOTEBOOKS:
            privacy = row.get("isPrivate")
            if privacy is not None and type(privacy) is not bool:raise KaggleError("kaggle_visibility_invalid")
            if privacy is True:raise KaggleError("kaggle_private_row_refused")
            url, ref = notebook_url(row.get("ref"))
            key, kind, label = "kaggle-notebook-ref:" + ref.lower(), "notebook", title(row.get("title"))
            facts.update(notebook_ref=ref, listing_scope="sdk_everyone_view", visibility_field_reported=privacy is not None,
                visibility_evidence="provider_public_flag" if privacy is False else "listing_scope_only",
                per_row_visibility_verified=False, rename_stable_identity=False, last_run_time=dated(row.get("lastRunTime")))
            for field in ("totalVotes", "currentVersionNumber"):
                if field in row:facts[field] = whole(row[field], "count")
        else:
            label = title(row.get("name"))
            if self.selection.page_name is not None and row["name"] != self.selection.page_name:raise KaggleError("kaggle_page_mismatch")
            url = ORIGIN + "/competitions/" + self.selection.competition + "/overview"
            key, kind = "kaggle-page:" + self.selection.competition + ":" + sha256(row["name"].encode()).hexdigest(), "competition_page"
            facts.update(page_name=row["name"], content_retained=False, specific_page_permalink_known=False)
            links = page_references(row.get("content", ""))
        licence = title(row["licenseName"]) if type(row.get("licenseName")) is str and row["licenseName"] else None
        return {"key": key, "url": url, "kind": kind, "title": label, "licence_reported": licence,
                "licence_field_reported": licence is not None, "rights": dict(RIGHTS), "linked_sources": links,
                "facts": {name: value for name, value in facts.items() if value is not None}, "source_claims_verified": False}
