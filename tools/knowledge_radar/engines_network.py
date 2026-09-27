"""Network engines of the radar's source edge: bounded, read-only, each under its source contract.

Every request goes through the library ingestion component's transports: the
bounded HTTPS GET transport for public interfaces and the gh command line for
GitHub, each admitted by one run budget and recorded in one request log.
The GitHub reader here keeps its own allow list of read-only resources (the
ingestion reader's list does not include search, advisories or releases),
built the same way: a request outside the list is refused before any
process starts, and the login's token never passes through this module.

Engines read titles, identifiers, links, licences, dates and counts. Prose a
source returns beside them (descriptions, abstracts, release notes, advisory
summaries) is kept in memory only as a guard: the vetting stage refuses a
brief that repeats any of it.
"""
from __future__ import annotations

import ast
import base64
import json
import re
import time
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from datetime import date, timedelta
from urllib.parse import quote, urlencode, urlsplit

from loop_engine.core.library_ingestion.github_reader import parse_included_response
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport
from loop_engine.core.library_ingestion.processes import passthrough_environment, run_command
from loop_engine.core.library_ingestion.record_rules import now_utc
from loop_engine.core.library_ingestion.request_log import (
    RequestBudget,
    RequestCeilingReached,
    RequestLog,
    RequestObservation,
)

from .engines import (
    FAILED,
    GONE,
    NOT_MODIFIED,
    OK,
    PARTIAL,
    EngineAnswer,
    RadarEngineError,
    ReadContext,
    clean_title,
    iso_time,
    limit_of,
    number,
    observation,
    parameter,
    ranked,
    text_fact,
)
from .records import https_address

GITHUB_HOST = "api.github.com"
_OWNER = r"[A-Za-z0-9][A-Za-z0-9-]{0,38}"
_REPO = r"[A-Za-z0-9._-]{1,100}"
_QUERY = r"[A-Za-z0-9%._~+=&-]{1,1500}"
_GH_ALLOWED = (
    re.compile(rf"search/repositories\?{_QUERY}\Z"),
    re.compile(rf"advisories\?{_QUERY}\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}/releases\?per_page=[1-9]\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}/commits/[A-Za-z0-9._-]{{1,100}}\Z"),
    re.compile(rf"repos/{_OWNER}/{_REPO}/contents/[A-Za-z0-9._/-]{{1,300}}\?ref=[0-9a-f]{{40}}\Z"),
)
_SINCE = re.compile(r"\{since_(\d{1,3})d\}")


class GitHubReadRefused(ValueError):
    """A GitHub request outside the radar's read-only allow list; no process was started."""


def gh_allowed(path: str) -> bool:
    return (type(path) is str and ".." not in path and "\x00" not in path
            and any(pattern.fullmatch(path) for pattern in _GH_ALLOWED))


@dataclass
class RadarNetwork:
    """One run's bounded network: a shared budget and log, and per-engine pacing and ceilings."""

    budget: RequestBudget
    log: RequestLog
    contracts: dict
    gh: str = "gh"
    sleep: object = time.sleep
    clock: object = time.monotonic
    used: dict = field(default_factory=dict)
    last: dict = field(default_factory=dict)
    transports: dict = field(default_factory=dict)
    #: Validators of earlier complete reads, by request key, sent back so an unchanged source answers 304.
    conditional: dict = field(default_factory=dict)
    #: Validators the sources sent in this run, by request key, for the next run to send back.
    observed_validators: dict = field(default_factory=dict)

    def _admit(self, engine_id: str) -> None:
        contract = self.contracts[engine_id]
        if self.used.get(engine_id, 0) >= contract.maximum_requests_per_run:
            raise RequestCeilingReached(f"{engine_id} reached its contract ceiling of "
                                        f"{contract.maximum_requests_per_run} requests")
        wait = contract.minimum_seconds_between_requests - (self.clock() - self.last.get(engine_id, -1e9))
        if wait > 0:
            self.sleep(wait)
        self.used[engine_id] = self.used.get(engine_id, 0) + 1
        self.last[engine_id] = self.clock()

    def get(self, engine_id: str, host: str, path: str, query=None, *, accept: str = "application/json"):
        contract = self.contracts[engine_id]
        if host not in contract.hosts or contract.access_method != "https_get":
            raise RadarEngineError("radar_host_not_declared", f"{engine_id} may not read {host}")
        self._admit(engine_id)
        transport = self.transports.get((engine_id, accept))
        if transport is None:
            transport = HttpsGetTransport(contract.hosts, self.budget, self.log, timeout_seconds=60.0,
                                          maximum_bytes=contract.maximum_response_bytes, accept=accept)
            self.transports[(engine_id, accept)] = transport
        key = request_key(host, path, query)
        response = transport.get(host, path, query, validators=self.conditional.get(key))
        if response.status == 200 and (response.etag or response.last_modified):
            self.observed_validators[key] = {"etag": response.etag, "last_modified": response.last_modified}
        elif response.status == 304 and key in self.conditional:
            self.observed_validators[key] = dict(self.conditional[key])
        return response

    def gh_get(self, engine_id: str, path: str):
        contract = self.contracts[engine_id]
        if contract.access_method != "gh_api" or GITHUB_HOST not in contract.hosts:
            raise RadarEngineError("radar_host_not_declared", f"{engine_id} may not read GitHub")
        if not gh_allowed(path):
            raise GitHubReadRefused(f"not an allowed read: {path[:120]}")
        self._admit(engine_id)
        self.budget.admit()
        started = now_utc()
        result = run_command((self.gh, "api", "--method", "GET", "--include", path), timeout_seconds=60.0,
                             maximum_output_bytes=8 * 1024 * 1024, environment=passthrough_environment())
        if result.exit_code is None or result.truncated or not result.stdout:
            self.log.record(RequestObservation("gh_api", GITHUB_HOST, path, None, None, started, result.elapsed_ms,
                                               "transport_error", error_class="timeout" if result.timed_out
                                               else "response_too_large" if result.truncated else "no_response"))
            return None, b""
        response = parse_included_response(result.stdout)
        outcome = ("ok" if response.status == 200 else "not_found" if response.status == 404 else
                   "rate_limited" if response.status in (403, 429) and response.allowance_remaining == 0
                   else "http_error")
        self.log.record(RequestObservation("gh_api", GITHUB_HOST, path, response.status, response.body, started,
                                           result.elapsed_ms, outcome, allowance_remaining=response.allowance_remaining))
        return response.status, response.body


def request_key(host: str, path: str, query=None) -> str:
    """One stable name for a request, so validators of one read are sent back only to the same request."""
    return host + path + ("?" + urlencode(sorted((str(key), str(value)) for key, value in query.items())) if query else "")


def _resolve_since(text: str, today: str) -> str:
    return _SINCE.sub(lambda match: (date.fromisoformat(today) - timedelta(days=int(match.group(1)))).isoformat(), text)


def _json(body: bytes):
    try:
        return json.loads(body)
    except ValueError:
        return None


def _status_answer(status, what: str) -> EngineAnswer:
    """The answer for a read that did not return a usable page. Only a 304 to sent validators means "no change"."""
    if status == 304:
        return EngineAnswer(NOT_MODIFIED, f"{what} answered 304: unchanged since the last complete read")
    if status in (404, 410):
        return EngineAnswer(GONE, f"{what} answered {status}: the source is gone or moved")
    if status in (401, 403):
        return EngineAnswer(GONE, f"{what} answered {status}: access to the source changed or is refused")
    if status is None:
        return EngineAnswer(FAILED, f"{what} could not be reached")
    return EngineAnswer(FAILED, f"{what} answered {status}")


def _licence_of(spdx) -> "tuple[str | None, str]":
    if isinstance(spdx, str) and spdx and spdx != "NOASSERTION":
        return spdx, "the licence GitHub detects in the repository, not verified"
    if spdx == "NOASSERTION":
        return None, "GitHub found a licence file it could not classify"
    return None, "GitHub detects no licence file"


class GitHubSearch:
    engine_id, engine_version = "github_search", "1.0.0"
    material_facts = ("licence", "archived")

    def read(self, context: ReadContext) -> EngineAnswer:
        query = _resolve_since(parameter(context, "q", kind=str), context.today)
        per_page = parameter(context, "per_page", 20, kind=int)
        if not 1 <= per_page <= 30:
            raise RadarEngineError("radar_parameter_invalid", "per_page is 1 to 30")
        sort = parameter(context, "sort", "stars", kind=str, choices=("stars", "updated", "forks"))
        path = "search/repositories?" + urlencode({"q": query, "sort": sort, "order": "desc", "per_page": per_page})
        try:
            status, body = context.network.gh_get(self.engine_id, path)
        except (GitHubReadRefused, RequestCeilingReached) as error:
            return EngineAnswer(FAILED, str(error), requests=0)
        data = _json(body) if status == 200 else None
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            answer = _status_answer(status, "GitHub search")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        rows, guards, excluded = [], [], []
        for item in data["items"]:
            if not isinstance(item, dict) or not isinstance(item.get("full_name"), str):
                continue
            title, reason = clean_title(item["full_name"])
            if reason:
                excluded.append((str(item.get("full_name")), reason))
                continue
            if isinstance(item.get("description"), str):
                guards.append(item["description"])
            try:
                url = https_address(item.get("html_url"), "html_url")
            except ValueError:
                continue
            licence, basis = _licence_of((item.get("license") or {}).get("spdx_id"))
            topics = [topic for topic in item.get("topics", []) if isinstance(topic, str)][:5]
            rows.append(observation(
                context, self, key="github:" + title.lower(), origin="github:" + title.lower(), title=title, url=url,
                source_address="https://api.github.com/search/repositories", licence=licence, licence_basis=basis,
                facts={"stars": number(item.get("stargazers_count")), "forks": number(item.get("forks_count")),
                       "language": text_fact(item.get("language")), "archived": item.get("archived"),
                       "topics": ", ".join(topics) if topics else None},
                event_at=iso_time(item.get("created_at")), source_published_at=iso_time(item.get("pushed_at"))))
        chosen = ranked(rows, parameter(context, "rank_by", "stars", kind=str))
        status_value = PARTIAL if data.get("incomplete_results") else OK
        reason = "GitHub marked the search incomplete" if status_value == PARTIAL else ""
        return EngineAnswer(status_value, reason, tuple(chosen[:limit_of(context)]), 1, tuple(guards), tuple(excluded))


class GitHubAdvisories:
    engine_id, engine_version = "github_advisories", "1.0.0"
    material_facts = ("severity", "fixed_version", "withdrawn")

    def read(self, context: ReadContext) -> EngineAnswer:
        kind = parameter(context, "type", "reviewed", kind=str, choices=("reviewed", "malware"))
        query = {"type": kind, "per_page": parameter(context, "per_page", 20, kind=int), "sort": "published",
                 "direction": "desc"}
        severity = parameter(context, "severity", "", kind=str)
        if severity:
            query["severity"] = severity
        ecosystem = parameter(context, "ecosystem", "", kind=str)
        if ecosystem:
            query["ecosystem"] = ecosystem
        window = parameter(context, "window_days", 0, kind=int)
        if window:
            query["published"] = ">=" + (date.fromisoformat(context.today) - timedelta(days=window)).isoformat()
        try:
            status, body = context.network.gh_get(self.engine_id, "advisories?" + urlencode(query))
        except (GitHubReadRefused, RequestCeilingReached) as error:
            return EngineAnswer(FAILED, str(error))
        data = _json(body) if status == 200 else None
        if not isinstance(data, list):
            answer = _status_answer(status, "the GitHub Advisory Database")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        rows, guards = [], []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("ghsa_id"), str):
                continue
            for name in ("summary", "description"):
                if isinstance(item.get(name), str):
                    guards.append(item[name])
            vulnerable = [entry for entry in item.get("vulnerabilities") or [] if isinstance(entry, dict)]
            packages = [(str((entry.get("package") or {}).get("ecosystem")), str((entry.get("package") or {}).get("name")))
                        for entry in vulnerable]
            first = vulnerable[0] if vulnerable else {}
            names = sorted({f"{name} ({ecosystem})" for ecosystem, name in packages})
            label = names[0] if names else "a package"
            title, reason = clean_title(f"{item['ghsa_id']} in {label}")
            if reason:
                continue
            cve = item.get("cve_id") if isinstance(item.get("cve_id"), str) else None
            try:
                url = https_address(item.get("html_url"), "html_url")
            except ValueError:
                continue
            rows.append(observation(
                context, self, key="advisory:" + item["ghsa_id"], origin="vulnerability:" + (cve or item["ghsa_id"]),
                title=title, url=url, source_address="https://api.github.com/advisories",
                licence="CC-BY-4.0", licence_basis="the GitHub Advisory Database licence for its advisory data",
                facts={"severity": text_fact(item.get("severity")), "cve": cve, "type": kind,
                       "packages": ", ".join(names[:3]) if names else None, "affected_packages": len(names),
                       "affected_range": text_fact(first.get("vulnerable_version_range")),
                       "fixed_version": text_fact(first.get("first_patched_version")),
                       "withdrawn": bool(item.get("withdrawn_at"))},
                event_at=iso_time(item.get("published_at")), source_published_at=iso_time(item.get("updated_at"))))
        chosen = ranked(rows, "event_at")
        return EngineAnswer(OK, "", tuple(chosen[:limit_of(context)]), 1, tuple(guards))


_MAJOR = re.compile(r"^(?:[A-Za-z_-]*?)v?(\d+)[.]")


class GitHubReleases:
    engine_id, engine_version = "github_releases", "1.0.0"
    material_facts = ("tag",)

    def read(self, context: ReadContext) -> EngineAnswer:
        repositories = parameter(context, "repositories", kind=list)
        per_page = parameter(context, "per_page", 5, kind=int)
        allow_pre = parameter(context, "include_prereleases", False, kind=bool)
        rows, guards, failures, gone, requests = [], [], [], [], 0
        for name in repositories:
            if not isinstance(name, str) or not re.fullmatch(rf"{_OWNER}/{_REPO}", name):
                raise RadarEngineError("radar_parameter_invalid", "repositories are owner/name pairs")
            try:
                status, body = context.network.gh_get(self.engine_id, f"repos/{name}/releases?per_page={per_page}")
            except (GitHubReadRefused, RequestCeilingReached) as error:
                failures.append(f"{name}: {error}")
                continue
            requests += 1
            data = _json(body) if status == 200 else None
            if not isinstance(data, list):
                (gone if status in (404, 410, 401, 403) else failures).append(f"{name}: answered {status}")
                continue
            releases = [item for item in data if isinstance(item, dict) and not item.get("draft")
                        and (allow_pre or not item.get("prerelease")) and isinstance(item.get("tag_name"), str)]
            for item in releases:
                if isinstance(item.get("body"), str):
                    guards.append(item["body"])
            if not releases:
                failures.append(f"{name}: no published release in the newest {per_page}")
                continue
            latest, previous = releases[0], releases[1] if len(releases) > 1 else None
            major = _MAJOR.match(latest["tag_name"])
            before = _MAJOR.match(previous["tag_name"]) if previous else None
            changed = bool(major and before and major.group(1) != before.group(1))
            title, reason = clean_title(f"{name} {latest['tag_name']}")
            if reason:
                continue
            try:
                url = https_address(latest.get("html_url"), "html_url")
            except ValueError:
                continue
            rows.append(observation(
                context, self, key=f"release:{name.lower()}", origin="github:" + name.lower(), title=title, url=url,
                source_address=f"https://api.github.com/repos/{name}/releases",
                facts={"tag": text_fact(latest["tag_name"]), "previous_tag": text_fact(previous["tag_name"]) if previous
                       else None, "major_version_changed": changed, "prerelease": bool(latest.get("prerelease"))},
                event_at=iso_time(latest.get("published_at")), source_published_at=iso_time(latest.get("published_at"))))
        chosen = ranked(rows, "event_at")
        if not rows:
            status = GONE if gone and not failures else FAILED
            return EngineAnswer(status, "; ".join(gone + failures) or "no release was read", requests=requests)
        problems = gone + failures
        return EngineAnswer(PARTIAL if problems else OK, "; ".join(problems), tuple(chosen[:limit_of(context)]),
                            requests, tuple(guards))


def _literal(node):
    """A constant, a list of constants or an enum member name from the directory source, never executed."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
        return node.value
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.attr
    if isinstance(node, (ast.List, ast.Tuple)):
        values = [_literal(item) for item in node.elts]
        return [value for value in values if isinstance(value, (str, int, float, bool))]
    return None


def directory_rows(source: str) -> list:
    """The Provider(...) calls of a PROVIDERS list, read with the abstract syntax tree only."""
    tree = ast.parse(source)
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) and len(node.targets) == 1 else None)
        if isinstance(target, ast.Name) and target.id == "PROVIDERS" and isinstance(node.value, ast.List):
            rows = []
            for call in node.value.elts:
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "Provider":
                    rows.append({keyword.arg: _literal(keyword.value) for keyword in call.keywords if keyword.arg})
            return rows
    return []


class OwnerDirectory:
    """The owner's own public directory repositories, read at an exact commit and parsed without running."""

    engine_id, engine_version = "owner_directory", "1.0.0"
    material_facts = ("tier", "category")

    def read(self, context: ReadContext) -> EngineAnswer:
        repository = parameter(context, "repository", kind=str)
        branch = parameter(context, "branch", "main", kind=str)
        path = parameter(context, "path", "providers.py", kind=str)
        categories = [str(item) for item in parameter(context, "categories", [], kind=list)]
        tiers = [str(item) for item in parameter(context, "tiers", [], kind=list)]
        if not re.fullmatch(rf"{_OWNER}/{_REPO}", repository):
            raise RadarEngineError("radar_parameter_invalid", "repository is an owner/name pair")
        try:
            status, body = context.network.gh_get(self.engine_id, f"repos/{repository}/commits/{branch}")
            commit = _json(body) if status == 200 else None
            if not isinstance(commit, dict) or not re.fullmatch(r"[0-9a-f]{40}", str(commit.get("sha"))):
                answer = _status_answer(status, f"{repository} commit")
                return EngineAnswer(answer.status, answer.reason, requests=1)
            status, body = context.network.gh_get(
                self.engine_id, f"repos/{repository}/contents/{quote(path)}?ref={commit['sha']}")
        except (GitHubReadRefused, RequestCeilingReached) as error:
            return EngineAnswer(FAILED, str(error))
        content = _json(body) if status == 200 else None
        if not isinstance(content, dict) or content.get("encoding") != "base64":
            answer = _status_answer(status, f"{repository}/{path}")
            return EngineAnswer(answer.status, answer.reason, requests=2)
        try:
            providers = directory_rows(base64.b64decode(content.get("content", "")).decode("utf-8"))
        except (ValueError, SyntaxError, UnicodeDecodeError) as error:
            return EngineAnswer(FAILED, f"{repository}/{path} could not be parsed: {type(error).__name__}", requests=2)
        committed = iso_time(((commit.get("commit") or {}).get("committer") or {}).get("date"))
        rows, excluded = [], []
        for provider in providers:
            if categories and provider.get("category") not in categories:
                continue
            if tiers and provider.get("tier") not in tiers:
                continue
            title, reason = clean_title(provider.get("name"))
            if reason:
                excluded.append((str(provider.get("name")), reason))
                continue
            url = next((provider[name] for name in ("github_url", "signup_url") if isinstance(provider.get(name), str)
                        and provider[name].startswith("https://")), None)
            try:
                url = https_address(url, "provider address")
            except ValueError:
                excluded.append((title, "the directory row names no public https address"))
                continue
            host = urlsplit(url).hostname or ""
            rows.append(observation(
                context, self, key=f"owner-directory:{repository.lower()}:{title.lower()}",
                origin="site:" + host.lower() + ("/" + urlsplit(url).path.strip("/").lower()
                                                   if host == "github.com" else ""),
                title=title, url=url,
                source_address=f"https://github.com/{repository}/blob/{commit['sha']}/{path}",
                facts={"tier": text_fact(provider.get("tier")), "category": text_fact(provider.get("category")),
                       "openai_compatible": provider.get("openai_compatible") if isinstance(
                           provider.get("openai_compatible"), bool) else None,
                       "supports_mcp": provider.get("supports_mcp") if isinstance(provider.get("supports_mcp"), bool)
                       else None,
                       "free_tier_as_recorded": text_fact(provider.get("free_limits"), 80),
                       "directory": repository},
                licence_basis="the owner's directory lists services and projects, not their licences",
                source_published_at=committed, claim_dated_by_source=True))
        if not rows:
            return EngineAnswer(OK, "no directory row matched the declared filter", (), 2, (), tuple(excluded))
        return EngineAnswer(OK, "", tuple(rows[:limit_of(context)]), 2, (), tuple(excluded))


class HuggingFaceModels:
    engine_id, engine_version = "huggingface_models", "1.0.0"
    material_facts = ("licence", "gated")
    SORTS = {"downloads": "downloads", "likes": "likes", "trendingScore": "trending_score",
             "lastModified": "source_published_at", "createdAt": "event_at"}

    def read(self, context: ReadContext) -> EngineAnswer:
        sort = parameter(context, "sort", "downloads", kind=str, choices=tuple(self.SORTS))
        query = {"sort": sort, "direction": -1, "limit": limit_of(context, 30)}
        for name in ("pipeline_tag", "search", "filter", "author"):
            value = parameter(context, name, "", kind=str)
            if value:
                query[name] = value
        try:
            response = context.network.get(self.engine_id, "huggingface.co", "/api/models", query)
        except (RadarEngineError, RequestCeilingReached, OSError) as error:
            return EngineAnswer(FAILED, str(error))
        data = _json(response.body) if response.status == 200 else None
        if not isinstance(data, list):
            answer = _status_answer(response.status, "the Hugging Face model listing")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        rows = []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            title, reason = clean_title(item["id"])
            if reason or not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", item["id"]):
                continue
            tags = [tag for tag in item.get("tags", []) if isinstance(tag, str)]
            licence = next((tag.split(":", 1)[1] for tag in tags if tag.startswith("license:")), None)
            results = sorted({sibling.get("rfilename", "").split("/", 1)[1].rsplit(".", 1)[0]
                              for sibling in item.get("siblings", []) or []
                              if isinstance(sibling, dict) and str(sibling.get("rfilename", "")).startswith(".eval_results/")})
            rows.append(observation(
                context, self, key="hf:" + item["id"].lower(), origin="hf:" + item["id"].lower(), title=title,
                url="https://huggingface.co/" + item["id"], source_address="https://huggingface.co/api/models",
                licence=licence, licence_basis="the licence tag on the model repository" if licence else
                "no licence tag on the model repository",
                facts={"downloads": number(item.get("downloads")), "likes": number(item.get("likes")),
                       "trending_score": number(item.get("trendingScore")),
                       "pipeline_tag": text_fact(item.get("pipeline_tag")),
                       "library": text_fact(item.get("library_name")),
                       "gated": item.get("gated") if isinstance(item.get("gated"), bool) else bool(item.get("gated")),
                       "arxiv_papers": sum(1 for tag in tags if tag.startswith("arxiv:")) or None,
                       "published_results": ", ".join(results[:6]) if results else None},
                event_at=iso_time(item.get("createdAt")), source_published_at=iso_time(item.get("lastModified"))))
        chosen = ranked(rows, parameter(context, "rank_by", self.SORTS[sort], kind=str))
        return EngineAnswer(OK, "", tuple(chosen[:limit_of(context)]), 1)


_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"


class ArxivListing:
    engine_id, engine_version = "arxiv_listing", "1.0.0"
    material_facts = ()

    def read(self, context: ReadContext) -> EngineAnswer:
        categories = [str(item) for item in parameter(context, "categories", kind=list)]
        if not categories or any(not re.fullmatch(r"[a-z-]+(?:\.[A-Za-z*-]+)?", item) for item in categories):
            raise RadarEngineError("radar_parameter_invalid", "categories are arXiv category names")
        search = " OR ".join("cat:" + item for item in categories)
        query = {"search_query": search, "sortBy": "submittedDate", "sortOrder": "descending",
                 "max_results": limit_of(context, 30)}
        try:
            response = context.network.get(self.engine_id, "export.arxiv.org", "/api/query", query,
                                           accept="application/atom+xml")
        except (RadarEngineError, RequestCeilingReached, OSError) as error:
            return EngineAnswer(FAILED, str(error))
        if response.status != 200:
            answer = _status_answer(response.status, "the arXiv query interface")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        try:
            feed = ElementTree.fromstring(response.body)
        except ElementTree.ParseError:
            return EngineAnswer(FAILED, "the arXiv answer is not a readable Atom feed", requests=1)
        rows, guards = [], []
        for entry in feed.findall(_ATOM + "entry"):
            identity = (entry.findtext(_ATOM + "id") or "").rsplit("/abs/", 1)[-1]
            match = re.fullmatch(r"(\d{4}\.\d{4,5})(v\d+)?", identity)
            if not match:
                continue
            summary = entry.findtext(_ATOM + "summary")
            if summary:
                guards.append(summary)
            title, reason = clean_title(entry.findtext(_ATOM + "title"))
            if reason:
                continue
            tags = [item.get("term") for item in entry.findall(_ATOM + "category") if item.get("term")]
            primary = entry.find(_ARXIV + "primary_category")
            rows.append(observation(
                context, self, key="arxiv:" + match.group(1), origin="arxiv:" + match.group(1), title=title,
                url="https://arxiv.org/abs/" + match.group(1), source_address="https://export.arxiv.org/api/query",
                licence_basis="the arXiv listing does not state the licence; the abstract page does",
                facts={"primary_category": primary.get("term") if primary is not None else None,
                       "categories": ", ".join(tags[:4]) if tags else None,
                       "authors": len(entry.findall(_ATOM + "author")) or None,
                       "version": match.group(2) or None},
                event_at=iso_time(entry.findtext(_ATOM + "published")),
                source_published_at=iso_time(entry.findtext(_ATOM + "updated"))))
        return EngineAnswer(OK, "", tuple(rows[:limit_of(context)]), 1, tuple(guards))


class OpenAlexWorks:
    engine_id, engine_version = "openalex_works", "1.0.0"
    material_facts = ("licence",)

    def read(self, context: ReadContext) -> EngineAnswer:
        field_id = parameter(context, "field", kind=str)
        if not re.fullmatch(r"fields/\d{1,3}", field_id):
            raise RadarEngineError("radar_parameter_invalid", "field is an OpenAlex field such as fields/27")
        window = parameter(context, "window_days", 180, kind=int)
        start = (date.fromisoformat(context.today) - timedelta(days=window)).isoformat()
        # Journal sources only: a repository re-deposit of an old, much-cited article carries a new date.
        query = {"filter": f"from_publication_date:{start},primary_topic.field.id:{field_id},type:article,"
                           "primary_location.source.type:journal",
                 "sort": "cited_by_count:desc", "per_page": limit_of(context, 25),
                 "select": "id,doi,display_name,publication_date,cited_by_count,open_access,primary_location,primary_topic"}
        try:
            response = context.network.get(self.engine_id, "api.openalex.org", "/works", query)
        except (RadarEngineError, RequestCeilingReached, OSError) as error:
            return EngineAnswer(FAILED, str(error))
        data = _json(response.body) if response.status == 200 else None
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            answer = _status_answer(response.status, "the OpenAlex works listing")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        rows = []
        for item in data["results"]:
            if not isinstance(item, dict):
                continue
            title, reason = clean_title(item.get("display_name"))
            if reason:
                continue
            doi = item.get("doi") if isinstance(item.get("doi"), str) else None
            identity = str(item.get("id", ""))
            url = doi if doi and doi.startswith("https://doi.org/") else identity
            try:
                url = https_address(url, "work address")
            except ValueError:
                continue
            location = item.get("primary_location") or {}
            topic = item.get("primary_topic") or {}
            licence = location.get("license") if isinstance(location.get("license"), str) else None
            rows.append(observation(
                context, self, key="openalex:" + identity.rsplit("/", 1)[-1],
                origin=("doi:" + doi.split("doi.org/", 1)[1].lower()) if doi and "doi.org/" in doi else "openalex:" + identity,
                title=title, url=url, source_address="https://api.openalex.org/works", licence=licence,
                licence_basis="the licence OpenAlex records for the primary location" if licence else
                "OpenAlex records no licence for the primary location",
                facts={"cited_by": number(item.get("cited_by_count")),
                       "open_access": text_fact((item.get("open_access") or {}).get("oa_status")),
                       "venue": text_fact((location.get("source") or {}).get("display_name")),
                       "field": text_fact((topic.get("field") or {}).get("display_name")),
                       "subfield": text_fact((topic.get("subfield") or {}).get("display_name"))},
                event_at=iso_time(item.get("publication_date")), source_published_at=iso_time(item.get("publication_date"))))
        chosen = ranked(rows, "cited_by")
        return EngineAnswer(OK, "", tuple(chosen[:limit_of(context)]), 1)


class EndOfLifeCalendar:
    engine_id, engine_version = "endoflife_calendar", "1.0.0"
    material_facts = ("eol_from", "latest", "eoas_from")

    def read(self, context: ReadContext) -> EngineAnswer:
        products = [str(item) for item in parameter(context, "products", kind=list)]
        keep_days = parameter(context, "ended_within_days", 180, kind=int)
        horizon = (date.fromisoformat(context.today) - timedelta(days=keep_days)).isoformat()
        rows, failures, gone, requests = [], [], [], 0
        for product in products:
            if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,60}", product):
                raise RadarEngineError("radar_parameter_invalid", "products are endoflife.date product names")
            try:
                response = context.network.get(self.engine_id, "endoflife.date", f"/api/v1/products/{product}/")
            except (RadarEngineError, RequestCeilingReached, OSError) as error:
                failures.append(f"{product}: {error}")
                continue
            requests += 1
            data = _json(response.body) if response.status == 200 else None
            result = data.get("result") if isinstance(data, dict) else None
            if not isinstance(result, dict) or not isinstance(result.get("releases"), list):
                (gone if response.status in (404, 410) else failures).append(f"{product}: answered {response.status}")
                continue
            label = text_fact(result.get("label")) or product
            modified = iso_time(data.get("last_modified"))
            for release in result["releases"]:
                if not isinstance(release, dict) or not isinstance(release.get("name"), str):
                    continue
                eol = release.get("eolFrom") if isinstance(release.get("eolFrom"), str) else None
                if not release.get("isMaintained") and (eol is None or eol < horizon):
                    continue
                latest = release.get("latest") if isinstance(release.get("latest"), dict) else {}
                title, reason = clean_title(f"{label} {release['name']}")
                if reason:
                    continue
                rows.append(observation(
                    context, self, key=f"eol:{product}:{release['name']}", origin=f"product:{product}@{release['name']}",
                    title=title, url=f"https://endoflife.date/{product}",
                    source_address=f"https://endoflife.date/api/v1/products/{product}/",
                    licence="MIT", licence_basis="endoflife.date publishes its data under the MIT licence",
                    facts={"product": product, "cycle": release["name"], "lts": bool(release.get("isLts")),
                           "maintained": bool(release.get("isMaintained")), "latest": text_fact(latest.get("name")),
                           "latest_date": latest.get("date") if isinstance(latest.get("date"), str) else None,
                           "eoas_from": release.get("eoasFrom") if isinstance(release.get("eoasFrom"), str) else None,
                           "eol_from": eol},
                    event_at=iso_time(release.get("releaseDate")), effective_from=iso_time(release.get("releaseDate")),
                    effective_until=iso_time(eol), source_published_at=modified))
        if not rows:
            return EngineAnswer(GONE if gone and not failures else FAILED, "; ".join(gone + failures) or "no release read",
                                requests=requests)
        chosen = ranked(rows, "effective_until", descending=False)
        problems = gone + failures
        return EngineAnswer(PARTIAL if problems else OK, "; ".join(problems), tuple(chosen[:limit_of(context)]), requests)


class FederalRegister:
    engine_id, engine_version = "federal_register", "1.0.0"
    material_facts = ("type", "comments_close_on")
    TYPES = ("RULE", "PRORULE", "NOTICE", "PRESDOCU")

    def read(self, context: ReadContext) -> EngineAnswer:
        term = parameter(context, "term", kind=str)
        types = [str(item) for item in parameter(context, "types", ["RULE", "PRORULE"], kind=list)]
        if any(item not in self.TYPES for item in types) or not re.fullmatch(r"[A-Za-z0-9 \"-]{2,80}", term):
            raise RadarEngineError("radar_parameter_invalid", "federal_register needs a plain term and known types")
        window = parameter(context, "window_days", 90, kind=int)
        since = (date.fromisoformat(context.today) - timedelta(days=window)).isoformat()
        pairs = [("conditions[term]", term), *[("conditions[type][]", item) for item in types],
                 ("conditions[publication_date][gte]", since), ("order", "newest"),
                 ("per_page", str(limit_of(context, 20)))]
        pairs += [("fields[]", name) for name in ("title", "type", "publication_date", "effective_on", "agencies",
                                                  "html_url", "document_number", "comments_close_on")]
        path = "/api/v1/documents.json?" + urlencode(pairs)
        try:
            response = context.network.get(self.engine_id, "www.federalregister.gov", path)
        except (RadarEngineError, RequestCeilingReached, OSError) as error:
            return EngineAnswer(FAILED, str(error))
        data = _json(response.body) if response.status == 200 else None
        if not isinstance(data, dict):
            answer = _status_answer(response.status, "the FederalRegister.gov documents interface")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        rows = []
        for item in data.get("results") or []:
            if not isinstance(item, dict) or not isinstance(item.get("document_number"), str):
                continue
            title, reason = clean_title(item.get("title"))
            if reason:
                continue
            try:
                url = https_address(item.get("html_url"), "html_url")
            except ValueError:
                continue
            agencies = [text_fact(agency.get("name")) for agency in item.get("agencies") or [] if isinstance(agency, dict)]
            rows.append(observation(
                context, self, key="federal-register:" + item["document_number"],
                origin="federal-register:" + item["document_number"], title=title, url=url,
                source_address="https://www.federalregister.gov/api/v1/documents.json",
                licence_basis="a United States government document; the FederalRegister.gov web rendition is not "
                              "the official legal edition",
                facts={"type": text_fact(item.get("type")), "document_number": item["document_number"],
                       "agencies": ", ".join(name for name in agencies[:3] if name) or None,
                       "comments_close_on": item.get("comments_close_on") if isinstance(item.get("comments_close_on"), str)
                       else None},
                event_at=iso_time(item.get("publication_date")), source_published_at=iso_time(item.get("publication_date")),
                effective_from=iso_time(item.get("effective_on"))))
        return EngineAnswer(OK, "" if rows else "no document matched in the window", tuple(rows), 1)


class HuggingFaceNewModels:
    """The newest model repositories of named publishers on the Hugging Face Hub, one listing per publisher."""

    engine_id, engine_version = "huggingface_new_models", "1.0.0"
    material_facts = ("licence", "gated")

    def read(self, context: ReadContext) -> EngineAnswer:
        authors = [str(item) for item in parameter(context, "authors", kind=list)]
        per_author = parameter(context, "per_author", 10, kind=int)
        if not 1 <= per_author <= 30 or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", item) for item in authors):
            raise RadarEngineError("radar_parameter_invalid", "authors are Hugging Face account names; per_author is 1 to 30")
        rows, failures, gone, unchanged, requests = [], [], [], [], 0
        for author in authors:
            query = {"author": author, "sort": "createdAt", "direction": -1, "limit": per_author}
            try:
                response = context.network.get(self.engine_id, "huggingface.co", "/api/models", query)
            except (RadarEngineError, RequestCeilingReached, OSError) as error:
                failures.append(f"{author}: {error}")
                continue
            requests += 1
            if response.status == 304:
                unchanged.append(author)
                continue
            data = _json(response.body) if response.status == 200 else None
            if not isinstance(data, list):
                (gone if response.status in (404, 410, 401, 403) else failures).append(f"{author}: answered {response.status}")
                continue
            for item in data:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    continue
                title, reason = clean_title(item["id"])
                if reason or not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", item["id"]):
                    continue
                tags = [tag for tag in item.get("tags", []) if isinstance(tag, str)]
                licence = next((tag.split(":", 1)[1] for tag in tags if tag.startswith("license:")), None)
                rows.append(observation(
                    context, self, key="hf:" + item["id"].lower(), origin="hf:" + item["id"].lower(), title=title,
                    url="https://huggingface.co/" + item["id"], source_address="https://huggingface.co/api/models",
                    licence=licence, licence_basis="the licence tag on the model repository" if licence else
                    "no licence tag on the model repository",
                    facts={"publisher": author, "downloads": number(item.get("downloads")), "likes": number(item.get("likes")),
                           "pipeline_tag": text_fact(item.get("pipeline_tag")),
                           "gated": item.get("gated") if isinstance(item.get("gated"), bool) else bool(item.get("gated"))},
                    event_at=iso_time(item.get("createdAt")), source_published_at=iso_time(item.get("lastModified"))))
        problems = gone + failures
        if not rows and unchanged and not problems:
            return EngineAnswer(NOT_MODIFIED, "every publisher answered 304", requests=requests)
        if not rows and not unchanged:
            return EngineAnswer(GONE if gone and not failures else FAILED, "; ".join(problems) or "no model read",
                                requests=requests)
        chosen = ranked(rows, "event_at")
        return EngineAnswer(PARTIAL if problems else OK, "; ".join(problems), tuple(chosen[:limit_of(context)]),
                            requests, complete=not (problems or unchanged))


_MODEL_ORIGIN = re.compile(r"[^a-z0-9._-]+")


def model_origin(identifier: str) -> str:
    """The common origin of a model across hosts: its name without the host or publisher prefix."""
    return "model:" + _MODEL_ORIGIN.sub("-", identifier.rsplit("/", 1)[-1].lower()).strip("-")


def _price(value):
    return round(float(value), 6) if type(value) in (int, float) and value >= 0 else None


def _cheapest_per_origin(rows: list) -> list:
    """Keep one row per model origin: the lowest listed output price, then input price, then key."""
    best = {}
    for row in rows:
        key = (row.facts.get("output_price") is None, row.facts.get("output_price") or 0,
               row.facts.get("input_price") or 0, row.key)
        if row.origin not in best or key < best[row.origin][0]:
            best[row.origin] = (key, row)
    return [value[1] for value in best.values()]


def _capability_filters(context: ReadContext, facts: dict) -> bool:
    """True when a row meets the binding's declared capability, context and price filters."""
    for flag in parameter(context, "require", [], kind=list):
        if facts.get(str(flag)) is not True:
            return False
    maximum = parameter(context, "max_output_price", None, kind=(int, float))
    if maximum is not None and (facts.get("output_price") is None or facts["output_price"] > maximum):
        return False
    minimum = parameter(context, "min_context", None, kind=int)
    if minimum is not None and (not isinstance(facts.get("context"), int) or facts["context"] < minimum):
        return False
    if parameter(context, "open_weights_only", False, kind=bool) and facts.get("open_weights") is not True:
        return False
    return True


class ModelsDevCatalogue:
    """models.dev (MIT): one catalogue of hosted models with capabilities, limits, prices and dates."""

    engine_id, engine_version = "models_dev_catalogue", "1.0.0"
    material_facts = ("output_price", "input_price", "context", "structured_output", "tool_calling")

    def read(self, context: ReadContext) -> EngineAnswer:
        try:
            response = context.network.get(self.engine_id, "models.dev", "/api.json")
        except (RadarEngineError, RequestCeilingReached, OSError) as error:
            return EngineAnswer(FAILED, str(error))
        data = _json(response.body) if response.status == 200 else None
        if not isinstance(data, dict):
            answer = _status_answer(response.status, "the models.dev catalogue")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        excluded = {name.lower() for name in context.contract.excluded_upstreams}
        wanted = {str(name).lower() for name in parameter(context, "providers", [], kind=list)}
        rows, guards = [], []
        for provider_id, provider in sorted(data.items()):
            if not isinstance(provider, dict) or not isinstance(provider.get("models"), dict):
                continue
            if provider_id.lower() in excluded or (wanted and provider_id.lower() not in wanted):
                continue
            documentation = provider.get("doc") if isinstance(provider.get("doc"), str) else ""
            try:
                address = https_address(documentation, "provider documentation")
            except ValueError:
                address = "https://models.dev"
            for model_id, model in sorted(provider["models"].items()):
                if not isinstance(model, dict):
                    continue
                title, reason = clean_title(model.get("name") or model_id)
                if reason:
                    continue
                if isinstance(model.get("description"), str):
                    guards.append(model["description"])
                limit = model.get("limit") if isinstance(model.get("limit"), dict) else {}
                cost = model.get("cost") if isinstance(model.get("cost"), dict) else {}
                facts = {"provider": text_fact(provider.get("name")) or provider_id, "model_id": text_fact(model_id),
                         "family": text_fact(model.get("family")),
                         "tool_calling": model.get("tool_call") if isinstance(model.get("tool_call"), bool) else None,
                         "structured_output": model.get("structured_output")
                         if isinstance(model.get("structured_output"), bool) else None,
                         "reasoning": model.get("reasoning") if isinstance(model.get("reasoning"), bool) else None,
                         "open_weights": model.get("open_weights") if isinstance(model.get("open_weights"), bool) else None,
                         "context": number(limit.get("context")), "max_output": number(limit.get("output")),
                         "input_price": _price(cost.get("input")), "output_price": _price(cost.get("output"))}
                if not _capability_filters(context, facts):
                    continue
                rows.append(observation(
                    context, self, key=f"models.dev:{provider_id}/{model_id}", origin=model_origin(str(model_id)),
                    title=f"{title} ({facts['provider']})", url=address, source_address="https://models.dev/api.json",
                    licence_basis="models.dev (MIT) lists the model; the model's own terms apply", facts=facts,
                    event_at=iso_time(model.get("release_date")), source_published_at=iso_time(model.get("last_updated"))))
        if parameter(context, "one_per_model", True, kind=bool):
            rows = _cheapest_per_origin(rows)
        rank = parameter(context, "rank_by", "output_price", kind=str)
        chosen = ranked(rows, rank, descending=not parameter(context, "ascending", rank == "output_price", kind=bool))
        return EngineAnswer(OK, "" if rows else "no model matched the declared filter",
                            tuple(chosen[:limit_of(context)]), 1, tuple(guards[:2000]))


LITELLM_PATH = "/BerriAI/litellm/main/model_prices_and_context_window.json"
LITELLM_PAGE = "https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json"


class LiteLLMPrices:
    """The LiteLLM price map (MIT): per-token prices, limits, capability flags and retirement dates."""

    engine_id, engine_version = "litellm_prices", "1.0.0"
    material_facts = ("output_price", "input_price", "deprecation_date", "structured_output")
    FLAGS = {"supports_function_calling": "tool_calling", "supports_response_schema": "structured_output",
             "supports_reasoning": "reasoning"}

    def read(self, context: ReadContext) -> EngineAnswer:
        try:
            response = context.network.get(self.engine_id, "raw.githubusercontent.com", LITELLM_PATH)
        except (RadarEngineError, RequestCeilingReached, OSError) as error:
            return EngineAnswer(FAILED, str(error))
        data = _json(response.body) if response.status == 200 else None
        if not isinstance(data, dict):
            answer = _status_answer(response.status, "the LiteLLM price map")
            return EngineAnswer(answer.status, answer.reason, requests=1)
        excluded = {name.lower() for name in context.contract.excluded_upstreams}
        mode = parameter(context, "mode", "chat", kind=str)
        deprecating = parameter(context, "only_deprecating", False, kind=bool)
        rows, guards = [], []
        for key, row in sorted(data.items()):
            if key == "sample_spec" or not isinstance(row, dict) or (mode and row.get("mode") != mode):
                continue
            provider = str(row.get("litellm_provider") or "")
            if provider.lower() in excluded or key.split("/", 1)[0].lower() in excluded:
                continue
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if isinstance(metadata.get("notes"), str):
                guards.append(metadata["notes"])
            retires = row.get("deprecation_date") if isinstance(row.get("deprecation_date"), str) else None
            if deprecating and not retires:
                continue
            title, reason = clean_title(key)
            if reason:
                continue
            per_token_in, per_token_out = row.get("input_cost_per_token"), row.get("output_cost_per_token")
            facts = {"provider": text_fact(provider), "model_id": text_fact(key),
                     "context": number(row.get("max_input_tokens")), "max_output": number(row.get("max_output_tokens")),
                     "input_price": _price(per_token_in * 1_000_000) if type(per_token_in) in (int, float) else None,
                     "output_price": _price(per_token_out * 1_000_000) if type(per_token_out) in (int, float) else None,
                     "deprecation_date": retires}
            facts.update({name: row.get(flag) if isinstance(row.get(flag), bool) else None
                          for flag, name in self.FLAGS.items()})
            if not _capability_filters(context, facts):
                continue
            source = row.get("source") if isinstance(row.get("source"), str) else ""
            try:
                address = https_address(source, "price source")
            except ValueError:
                address = LITELLM_PAGE
            rows.append(observation(
                context, self, key="litellm:" + key, origin=model_origin(key), title=title, url=address,
                source_address=LITELLM_PAGE, facts=facts,
                licence_basis="the LiteLLM price map (MIT) lists the model; the model's own terms apply",
                effective_until=iso_time(retires)))
        if parameter(context, "one_per_model", not deprecating, kind=bool):
            rows = _cheapest_per_origin(rows)
        rank = parameter(context, "rank_by", "effective_until" if deprecating else "output_price", kind=str)
        chosen = ranked(rows, rank, descending=False)
        return EngineAnswer(OK, "" if rows else "no model matched the declared filter",
                            tuple(chosen[:limit_of(context)]), 1, tuple(guards[:2000]))


ENGINES = (GitHubSearch(), GitHubAdvisories(), GitHubReleases(), OwnerDirectory(), HuggingFaceModels(),
           ArxivListing(), OpenAlexWorks(), EndOfLifeCalendar(), FederalRegister(), HuggingFaceNewModels(),
           ModelsDevCatalogue(), LiteLLMPrices())
