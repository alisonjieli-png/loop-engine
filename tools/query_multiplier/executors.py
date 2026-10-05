"""The research_query_executor slot: one engine per source, each mapping a query onto that source's own language.

Every engine answers the same edge. In: an assignment (a value or null per dimension) and a page. Out of
`render`: one request record (method, host, path, parameters, body) or the reason it cannot be rendered. Out of
`parse`: the status of the answer and normalised result rows (url, kind, the licence exactly as the source reports
it, and the source's own identifiers). The "dork" qualifiers live here: `license:`, `language:`, `pushed:`,
`stars:` for GitHub repositories; `filename:`, `extension:`, `path:` for GitHub code; licence and task tags on the
Hugging Face Hub; filters on OpenAlex, Openverse, GBIF and data.europa.eu; `cat:` and `submittedDate:` on arXiv.

```text
research_query_executor (engine kind search_service unless noted)
├── github_repositories   api.github.com search/repositories through the gh login (30 a minute shared)
├── github_code           api.github.com search/code through the gh login (10 a minute shared)
├── huggingface_models    huggingface.co/api/models            (500 per 5 minutes anonymous)
├── huggingface_datasets  huggingface.co/api/datasets
├── openalex_works        api.openalex.org/works               (1,000 credits a day anonymous: a filter
│                                                               costs 1, a search 10)
├── openverse_images      api.openverse.org/v1/images          (20 a minute, 200 a day anonymous)
├── openverse_audio       api.openverse.org/v1/audio
├── gbif_datasets         api.gbif.org/v1/dataset/search
├── data_europa_datasets  data.europa.eu/api/hub/search/search
├── datagov_datasets      api.gsa.gov/technology/datagov/v4/search with the documented DEMO_KEY
│                         (catalog.data.gov's CKAN interface answers 404 since data.gov retired it)
├── arxiv                 export.arxiv.org/api/query           (one request every three seconds)
├── npm_search            registry.npmjs.org/-/v1/search
├── ollama_web_search     ollama.com/api/web_search, POST, the owner's existing Ollama key from the environment,
│                         a declared daily ceiling
└── pypi_search           unavailable: PyPI has no search interface (its XML-RPC search was switched off and
                          its HTML search page is not an automated interface); PyPI's JSON API reads one named
                          project and is not a search
```

An engine is an adapter that a run uses, never a runtime type. It holds no credential: GitHub reads go through
`gh`, which holds the login, and the Ollama key is read from the environment at send time by the transport and
never enters a request record, a stored response or a report. Result licences are leads; every supply line decides
the licence again from the licence text when it generates.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from urllib.parse import urlencode, urlsplit, urlunsplit

from knowledge_radar.query_matrix import digest

from .dimensions import Dimension, Value

TOPIC_DIMENSIONS = ("sdg_goal", "sdg_target", "onet_occupation", "onet_task", "industry", "harness_kind",
                    "step_function", "creative_domain", "algorithm")
OK, EMPTY, PARTIAL, FAILED, REFUSED, RATE_LIMITED = "ok", "empty", "partial", "failed", "refused", "rate_limited"
_REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}\Z")
MAXIMUM_TEXT = 300


@dataclass
class Parsed:
    status: str
    items: list = field(default_factory=list)
    total_count: "int | None" = None
    rejected: int = 0
    next_cursor: "str | None" = None


def _clip(text, limit=MAXIMUM_TEXT):
    if not isinstance(text, str):
        return None
    text = " ".join(text.split())
    return text[:limit] if text else None


def _phrase(value: Value) -> str:
    return '"' + value.text + '"'


def _json(body: bytes):
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None


def canonical_url(url: str) -> "str | None":
    """Scheme, lower-case host and path without a trailing slash, query and fragment: one address per page."""
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if not host:
        return None
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, "", ""))


_GITHUB_REPOSITORY_PAGE = re.compile(r"https://(?:www\.)?github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})(?:/.*)?\Z")
_HF_PAGE = re.compile(r"https://huggingface\.co/(datasets/|spaces/)?([A-Za-z0-9-_.]{1,96}/[A-Za-z0-9-_.]{1,96})(?:/.*)?\Z")
_ARXIV_PAGE = re.compile(r"https://(?:www\.)?arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v[0-9]+)?(?:\.pdf)?\Z")
_DOI_PAGE = re.compile(r"https://(?:dx\.)?doi\.org/(10\.[0-9]{4,9}/\S+)\Z")


def candidate_key(url: str) -> "tuple[str, str] | None":
    """The cross-source identity of the thing a result points at, and its kind when the address alone says it.

    A GitHub repository page, a Hugging Face model or dataset, an arXiv paper and a DOI keep one identity
    whichever source found them, so one item found by two queries or two sources is one candidate.
    """
    canonical = canonical_url(url)
    if canonical is None:
        return None
    match = _GITHUB_REPOSITORY_PAGE.match(canonical)
    if match and match.group(1).lower() not in ("orgs", "topics", "search", "collections", "features", "sponsors", "marketplace"):
        return "github:" + match.group(1).lower() + "/" + match.group(2).lower().removesuffix(".git"), "repository"
    match = _HF_PAGE.match(canonical)
    if match:
        prefix = {"datasets/": "hf-dataset:", "spaces/": "hf-space:"}.get(match.group(1) or "", "hf-model:")
        kind = {"hf-dataset:": "dataset", "hf-space:": "web_page"}.get(prefix, "model")
        return prefix + match.group(2).lower(), kind
    match = _ARXIV_PAGE.match(canonical)
    if match:
        return "doi:10.48550/arxiv." + match.group(1).lower(), "paper"
    match = _DOI_PAGE.match(canonical)
    if match:
        return "doi:" + match.group(1).lower(), "paper"
    return "web:" + canonical, "web_page"


class Executor:
    """Base engine: declared host, pacing, ceilings, the dimensions it renders and the values it can express."""

    executor_id = ""
    executor_version = "1.0.0"
    engine_kind = "search_service"
    host = ""
    access = "https_get"
    available = True
    unavailable_reason = ""
    #: Seconds between two requests of this engine; the source's own limit with headroom for other agents.
    minimum_interval = 2.0
    #: Requests per UTC day this engine may make; None means bounded only by the interval and the provider.
    daily_ceiling: "int | None" = None
    refresh_days = 30
    follow_pages = 2
    per_page = 100
    #: The dimension ids this engine renders.
    renders = frozenset()
    accept = "application/json"
    #: What a request costs in the provider's own units, when the provider meters something other than requests.
    cost_unit = "request"
    #: Fixed public headers the transport adds; never a credential.
    static_headers: dict = {}

    def identity(self) -> dict:
        return {"executor": self.executor_id, "version": self.executor_version, "host": self.host,
                "access": self.access, "per_page": self.per_page}

    def supports_dimension(self, dimension: Dimension) -> bool:
        return dimension.id in self.renders

    def accepts(self, dimension: Dimension, value: Value) -> bool:
        return True

    def check_params(self, params: dict) -> None:
        if params:
            raise ValueError("executor_params_unknown:" + self.executor_id)

    def render(self, assignment: dict, params: dict, *, page: int = 1):  # pragma: no cover - interface
        raise NotImplementedError

    def parse(self, status: "int | None", body: bytes) -> Parsed:  # pragma: no cover - interface
        raise NotImplementedError

    def request(self, path: str, params: list, *, page: int, method: str = "GET", body=None) -> dict:
        return {"method": method, "host": self.host, "path": path, "params": [[str(k), str(v)] for k, v in params],
                "body": body, "page": page}

    def cost(self, request: dict) -> int:
        return 1

    def describe(self) -> dict:
        return {"executor_id": self.executor_id, "executor_version": self.executor_version, "engine_kind": self.engine_kind,
                "host": self.host, "access": self.access, "available": self.available,
                "unavailable_reason": self.unavailable_reason, "minimum_interval_seconds": self.minimum_interval,
                "daily_ceiling": self.daily_ceiling, "refresh_days": self.refresh_days, "follow_pages": self.follow_pages,
                "renders": sorted(self.renders), "cost_unit": self.cost_unit}


def _topic_phrases(assignment: dict, names=TOPIC_DIMENSIONS + ("geography", "natural_language", "natural_language_endonym")) -> list:
    return [value for name, value in assignment.items() if value is not None and name in names]


def _status(status, items, rejected) -> str:
    if status != 200:
        return FAILED
    if rejected and items:
        return PARTIAL
    return OK if items else (PARTIAL if rejected else EMPTY)


# ------------------------------------------------------------------------------------------------------ GitHub
def github_repository_row(item) -> "dict | None":
    """A public repository row, or None. The review rule of October 1: an explicit private=false, no contradictory
    visibility, and a canonical github.com URL equal to full_name; a rejected row keeps no name or description."""
    if type(item) is not dict or item.get("private") is not False:
        return None
    if item.get("visibility") not in (None, "public"):
        return None
    full_name = item.get("full_name")
    if type(full_name) is not str or not _REPOSITORY.fullmatch(full_name):
        return None
    if item.get("html_url") != "https://github.com/" + full_name:
        return None
    return {"full_name": full_name, "html_url": item["html_url"]}


class GitHubRepositories(Executor):
    executor_id, host, access = "github_repositories", "api.github.com", "gh_api"
    minimum_interval = 3.0  # at most 20 a minute of the shared 30
    refresh_days = 30
    follow_pages = 3
    renders = frozenset(TOPIC_DIMENSIONS + ("file_format", "programming_language", "licence", "time_window",
                                            "geography", "natural_language_endonym", "github_stars", "github_match"))

    def check_params(self, params):
        if set(params) - {"time_field"} or params.get("time_field", "pushed") not in ("pushed", "created"):
            raise ValueError("executor_params:" + self.executor_id)

    def accepts(self, dimension, value):
        if dimension.id in ("licence", "programming_language", "github_stars", "github_match"):
            return bool(value.attributes.get("github"))
        return True

    def render(self, assignment, params, *, page=1):
        terms = [_phrase(value) for value in _topic_phrases(assignment, TOPIC_DIMENSIONS + (
            "geography", "natural_language_endonym", "file_format"))]
        qualifiers = []
        for name in ("programming_language", "licence", "github_stars", "github_match"):
            value = assignment.get(name)
            if value is None:
                continue
            rendered = value.attributes["github"]
            if name == "programming_language":
                rendered = "language:" + ('"' + rendered + '"' if " " in rendered else rendered)
            elif name == "licence":
                rendered = "license:" + rendered
            qualifiers.append(rendered)
        window = assignment.get("time_window")
        if window is not None:
            qualifiers.append(f"{params.get('time_field', 'pushed')}:{window.attributes['from']}..{window.attributes['to']}")
        if not terms and len(qualifiers) < 2:
            return "empty_query"
        query = " ".join(terms + qualifiers + ["is:public", "archived:false"])
        if len(query) > 250:
            return "query_too_long"
        return self.request("/search/repositories", [("q", query), ("per_page", self.per_page), ("page", page)], page=page)

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("items")) is not list:
            return Parsed(FAILED if status != 422 else REFUSED)
        items, rejected = [], 0
        for item in document["items"]:
            row = github_repository_row(item)
            if row is None:
                rejected += 1
                continue
            licence = item.get("license") if type(item.get("license")) is dict else {}
            topics = [topic for topic in item.get("topics") or [] if type(topic) is str][:20]
            items.append({"key": "github:" + row["full_name"].lower(), "url": row["html_url"], "kind": "repository",
                          "title": row["full_name"], "description": _clip(item.get("description")),
                          "licence_reported": licence.get("spdx_id"), "licence_field": "github license.spdx_id",
                          "extra": {"language": item.get("language"), "topics": topics,
                                    "stars": item.get("stargazers_count"), "pushed_at": item.get("pushed_at"),
                                    "default_branch": item.get("default_branch"), "size_kb": item.get("size"),
                                    "fork": item.get("fork"), "archived": item.get("archived"),
                                    "homepage": _clip(item.get("homepage"), 200)}})
        parsed = Parsed(_status(status, items, rejected), items, document.get("total_count"), rejected)
        if document.get("incomplete_results") is True and parsed.status == OK:
            parsed.status = PARTIAL
        return parsed


_COMMIT_IN_URL = re.compile(r"https://github\.com/[^/]+/[^/]+/blob/([0-9a-f]{40})/")


class GitHubCode(Executor):
    executor_id, host, access = "github_code", "api.github.com", "gh_api"
    minimum_interval = 15.0  # at most 4 a minute of the shared 10
    refresh_days = 45
    follow_pages = 2
    renders = frozenset(TOPIC_DIMENSIONS + ("file_format", "programming_language", "github_code_size"))

    def accepts(self, dimension, value):
        if dimension.id == "file_format":
            return bool(value.attributes.get("code"))
        if dimension.id in ("programming_language", "github_code_size"):
            return bool(value.attributes.get("github"))
        return True

    def render(self, assignment, params, *, page=1):
        terms = [_phrase(value) for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        parts = []
        fmt = assignment.get("file_format")
        if fmt is not None:
            parts.append(fmt.attributes["code"])
        language = assignment.get("programming_language")
        if language is not None:
            name = language.attributes["github"]
            parts.append("language:" + ('"' + name + '"' if " " in name else name))
        size = assignment.get("github_code_size")
        if size is not None:
            parts.append(size.attributes["github"])
        query = " ".join(terms + parts)
        keywords = [token for token in query.split() if ":" not in token]
        if not keywords:
            return "code_search_needs_a_keyword"
        if len(query) > 250:
            return "query_too_long"
        return self.request("/search/code", [("q", query), ("per_page", self.per_page), ("page", page)], page=page)

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("items")) is not list:
            return Parsed(FAILED if status != 422 else REFUSED)
        items, rejected = [], 0
        for item in document["items"]:
            repository = github_repository_row(item.get("repository") if type(item) is dict else None)
            path = item.get("path") if type(item) is dict else None
            if repository is None or type(path) is not str or not path or ".." in path.split("/"):
                rejected += 1
                continue
            commit = _COMMIT_IN_URL.match(item.get("html_url") or "")
            items.append({"key": "github-file:" + repository["full_name"].lower() + "/" + path, "url": item.get("html_url"),
                          "kind": "file", "title": repository["full_name"] + "/" + path,
                          "description": _clip((item.get("repository") or {}).get("description")),
                          "licence_reported": None, "licence_field": "github code search reports no licence",
                          "extra": {"repository": repository["full_name"], "path": path, "name": item.get("name"),
                                    "blob_sha": item.get("sha"), "commit": commit.group(1) if commit else None}})
        parsed = Parsed(_status(status, items, rejected), items, document.get("total_count"), rejected)
        if document.get("incomplete_results") is True and parsed.status == OK:
            parsed.status = PARTIAL
        return parsed


# ------------------------------------------------------------------------------------------------ Hugging Face
def _hf_licence(tags) -> "str | None":
    for tag in tags or ():
        if isinstance(tag, str) and tag.startswith("license:"):
            return tag[len("license:"):]
    return None


class HuggingFaceModels(Executor):
    executor_id, host = "huggingface_models", "huggingface.co"
    minimum_interval = 2.0  # 150 per 5 minutes of the anonymous 500
    refresh_days = 14
    follow_pages = 0  # the Hub pages by an opaque cursor; first pages only
    renders = frozenset(TOPIC_DIMENSIONS + ("licence", "hf_model_task", "hf_model_library", "natural_language"))
    path = "/api/models"
    kind = "model"
    prefix = "hf-model:"
    task_filter = "hf_model_task"

    def accepts(self, dimension, value):
        if dimension.id in ("licence", "hf_model_task", "hf_model_library", "hf_dataset_task", "hf_dataset_modality", "file_format"):
            return bool(value.attributes.get("hf"))
        if dimension.id == "natural_language":
            return bool(value.attributes.get("iso639_1"))
        return True

    def filters(self, assignment) -> list:
        out = []
        licence = assignment.get("licence")
        if licence is not None:
            out.append(("filter", "license:" + licence.attributes["hf"]))
        task = assignment.get(self.task_filter)
        if task is not None:
            out.append(("filter", task.attributes["hf"]))
        library = assignment.get("hf_model_library")
        if library is not None:
            out.append(("filter", library.attributes["hf"]))
        language = assignment.get("natural_language")
        if language is not None:
            out.append(("filter", language.attributes["iso639_1"]))
        return out

    def render(self, assignment, params, *, page=1):
        if page != 1:
            return "cursor_pagination_first_page_only"
        topics = [value.text for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        filters = self.filters(assignment)
        if not topics and not filters:
            return "empty_query"
        query = ([("search", " ".join(topics))] if topics else []) + filters + [("limit", self.per_page)]
        return self.request(self.path, query, page=page)

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        for item in document:
            identity = item.get("id") if type(item) is dict else None
            if type(identity) is not str or "/" not in identity or item.get("private") is True or item.get("gated") not in (None, False):
                rejected += 1
                continue
            url = "https://huggingface.co/" + ("datasets/" if self.kind == "dataset" else "") + identity
            tags = [tag for tag in item.get("tags") or [] if isinstance(tag, str)][:40]
            items.append({"key": self.prefix + identity.lower(), "url": url, "kind": self.kind, "title": identity,
                          "description": _clip(item.get("description")),
                          "licence_reported": _hf_licence(tags), "licence_field": "hub tag license:",
                          "extra": {"tags": tags, "downloads": item.get("downloads"), "likes": item.get("likes"),
                                    "last_modified": item.get("lastModified"), "pipeline_tag": item.get("pipeline_tag"),
                                    "library": item.get("library_name")}})
        return Parsed(_status(status, items, rejected), items, None, rejected)


class HuggingFaceDatasets(HuggingFaceModels):
    executor_id = "huggingface_datasets"
    renders = frozenset(TOPIC_DIMENSIONS + ("licence", "hf_dataset_task", "hf_dataset_modality", "natural_language", "file_format"))
    path, kind, prefix = "/api/datasets", "dataset", "hf-dataset:"
    task_filter = "hf_dataset_task"

    def filters(self, assignment):
        out = []
        licence = assignment.get("licence")
        if licence is not None:
            out.append(("filter", "license:" + licence.attributes["hf"]))
        task = assignment.get("hf_dataset_task")
        if task is not None:
            out.append(("filter", "task_categories:" + task.attributes["hf"]))
        modality = assignment.get("hf_dataset_modality")
        if modality is not None:
            out.append(("filter", "modality:" + modality.attributes["hf"]))
        fmt = assignment.get("file_format")
        if fmt is not None:
            out.append(("filter", "format:" + fmt.attributes["hf"]))
        language = assignment.get("natural_language")
        if language is not None:
            out.append(("filter", "language:" + language.attributes["iso639_1"]))
        return out


# ---------------------------------------------------------------------------------------------------- OpenAlex
class OpenAlexWorks(Executor):
    executor_id, host = "openalex_works", "api.openalex.org"
    minimum_interval = 4.0
    daily_ceiling = 700  # credits; anonymous allowance is 1,000 a day, the rest stays for other agents
    cost_unit = "openalex_credit"
    refresh_days = 60
    follow_pages = 2
    per_page = 200
    renders = frozenset(TOPIC_DIMENSIONS + ("licence", "openalex_type", "natural_language", "geography", "time_window"))

    def accepts(self, dimension, value):
        if dimension.id in ("licence", "openalex_type"):
            return bool(value.attributes.get("openalex"))
        if dimension.id == "geography":
            return bool(value.attributes.get("iso2"))  # institutions carry a country code, not a region
        if dimension.id == "natural_language":
            return bool(value.attributes.get("iso639_1"))
        return True

    def render(self, assignment, params, *, page=1):
        filters, search = [], []
        for name, value in assignment.items():
            if value is None:
                continue
            if name == "sdg_goal":
                filters.append("sustainable_development_goals.id:https://metadata.un.org/sdg/" + value.attributes["goal"])
            elif name in TOPIC_DIMENSIONS:
                search.append(value.text)
            elif name == "licence":
                filters.append("best_oa_location.license:" + value.attributes["openalex"])
            elif name == "openalex_type":
                filters.append("type:" + value.attributes["openalex"])
            elif name == "natural_language":
                filters.append("language:" + value.attributes["iso639_1"])
            elif name == "geography":
                filters.append("authorships.institutions.country_code:" + value.attributes["iso2"])
            elif name == "time_window":
                filters.append("from_publication_date:" + value.attributes["from"])
                filters.append("to_publication_date:" + value.attributes["to"])
        if search:
            filters.append("title_and_abstract.search:" + " ".join(search))
        if not filters:
            return "empty_query"
        query = [("filter", ",".join(sorted(filters))), ("per-page", self.per_page), ("page", page),
                 ("select", "id,doi,title,type,publication_year,best_oa_location,open_access")]
        return self.request("/works", query, page=page)

    def cost(self, request):
        return 10 if any(".search:" in value for key, value in request["params"] if key == "filter") else 1

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("results")) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        for item in document["results"]:
            if type(item) is not dict or not isinstance(item.get("id"), str):
                rejected += 1
                continue
            location = item.get("best_oa_location") if type(item.get("best_oa_location")) is dict else {}
            doi = item.get("doi")
            key = "doi:" + doi.lower().removeprefix("https://doi.org/") if isinstance(doi, str) and doi else "openalex:" + item["id"].rsplit("/", 1)[-1]
            url = location.get("landing_page_url") or doi or item["id"]
            kind = "dataset" if item.get("type") == "dataset" else "paper"
            items.append({"key": key, "url": url, "kind": kind, "title": _clip(item.get("title")), "description": None,
                          "licence_reported": location.get("license"), "licence_field": "openalex best_oa_location.license",
                          "extra": {"openalex": item["id"], "type": item.get("type"), "year": item.get("publication_year"),
                                    "pdf_url": location.get("pdf_url"),
                                    "source": ((location.get("source") or {}).get("display_name") if type(location.get("source")) is dict else None)}})
        meta = document.get("meta") if type(document.get("meta")) is dict else {}
        return Parsed(_status(status, items, rejected), items, meta.get("count"), rejected)


# --------------------------------------------------------------------------------------------------- Openverse
def openverse_licence(code, version) -> "str | None":
    if not isinstance(code, str):
        return None
    code, version = code.lower(), str(version or "")
    if code == "cc0":
        return "CC0-1.0"
    if code == "pdm":
        return "public-domain-mark"
    return "CC-" + code.upper() + ("-" + version if version else "")


class OpenverseImages(Executor):
    executor_id, host = "openverse_images", "api.openverse.org"
    minimum_interval = 20.0
    daily_ceiling = 70  # the anonymous allowance is 200 a day across images and audio and other agents
    refresh_days = 90
    follow_pages = 1
    per_page = 20  # the anonymous maximum
    path = "/v1/images/"
    category = "openverse_image_category"
    renders = frozenset(TOPIC_DIMENSIONS + ("licence", "openverse_image_category", "file_format"))

    def accepts(self, dimension, value):
        if dimension.id in ("licence", self.category, "file_format"):
            return bool(value.attributes.get("openverse"))
        return True

    def render(self, assignment, params, *, page=1):
        topics = [value.text for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        if not topics:
            return "empty_query"
        query = [("q", " ".join(topics)), ("page_size", self.per_page), ("page", page)]
        licence = assignment.get("licence")
        query.append(("license", licence.attributes["openverse"] if licence is not None else "cc0,by"))
        category = assignment.get(self.category)
        if category is not None:
            query.append(("category", category.attributes["openverse"]))
        fmt = assignment.get("file_format")
        if fmt is not None:
            query.append(("extension", fmt.attributes["openverse"]))
        return self.request(self.path, query, page=page)

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("results")) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        kind = "image" if "images" in self.path else "audio"
        for item in document["results"]:
            if type(item) is not dict or not isinstance(item.get("id"), str) or item.get("mature") is True:
                rejected += 1
                continue
            items.append({"key": "openverse:" + item["id"], "url": item.get("foreign_landing_url") or item.get("url"),
                          "kind": "media", "title": _clip(item.get("title")), "description": None,
                          "licence_reported": openverse_licence(item.get("license"), item.get("license_version")),
                          "licence_field": "openverse license + license_version",
                          "extra": {"media": kind, "file_url": item.get("url"), "filetype": item.get("filetype"),
                                    "provider": item.get("provider"), "source": item.get("source"),
                                    "licence_url": item.get("license_url"), "creator": _clip(item.get("creator"), 120)}})
        return Parsed(_status(status, items, rejected), items, document.get("result_count"), rejected)


class OpenverseAudio(OpenverseImages):
    executor_id = "openverse_audio"
    path = "/v1/audio/"
    category = "openverse_audio_category"
    renders = frozenset(TOPIC_DIMENSIONS + ("licence", "openverse_audio_category", "file_format"))


# -------------------------------------------------------------------------------------------------------- GBIF
_CC_URL = (("publicdomain/zero/1.0", "CC0-1.0"), ("licenses/by/4.0", "CC-BY-4.0"), ("licenses/by-nc/4.0", "CC-BY-NC-4.0"),
           ("licenses/by-sa/4.0", "CC-BY-SA-4.0"))


def licence_from_url(url) -> "str | None":
    if not isinstance(url, str):
        return None
    lowered = url.lower()
    for fragment, spdx in _CC_URL:
        if fragment in lowered:
            return spdx
    return url[:200]


class GbifDatasets(Executor):
    executor_id, host = "gbif_datasets", "api.gbif.org"
    minimum_interval = 3.0
    refresh_days = 60
    follow_pages = 2
    renders = frozenset(TOPIC_DIMENSIONS + ("licence", "gbif_dataset_type", "geography"))

    def accepts(self, dimension, value):
        if dimension.id in ("licence", "gbif_dataset_type"):
            return bool(value.attributes.get("gbif"))
        if dimension.id == "geography":
            # GBIF answers 400 for a reserved code such as AC (Ascension); a country or area with an M49 code is
            # one GBIF knows.
            return bool(value.attributes.get("iso2")) and bool(value.attributes.get("m49"))
        return True

    def render(self, assignment, params, *, page=1):
        topics = [value.text for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        query = []
        if topics:
            query.append(("q", " ".join(topics)))
        for name, key in (("licence", "license"), ("gbif_dataset_type", "type")):
            value = assignment.get(name)
            if value is not None:
                query.append((key, value.attributes["gbif"]))
        geography = assignment.get("geography")
        if geography is not None:
            query.append(("publishingCountry", geography.attributes["iso2"]))
        if not query:
            return "empty_query"
        query += [("limit", self.per_page), ("offset", (page - 1) * self.per_page)]
        return self.request("/v1/dataset/search", query, page=page)

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("results")) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        for item in document["results"]:
            if type(item) is not dict or not isinstance(item.get("key"), str):
                rejected += 1
                continue
            doi = item.get("doi")
            key = "doi:" + doi.lower() if isinstance(doi, str) and doi.startswith("10.") else "gbif-dataset:" + item["key"]
            items.append({"key": key, "url": "https://www.gbif.org/dataset/" + item["key"], "kind": "dataset",
                          "title": _clip(item.get("title")), "description": None,
                          "licence_reported": licence_from_url(item.get("license")), "licence_field": "gbif license",
                          "extra": {"gbif_key": item["key"], "type": item.get("type"), "records": item.get("recordCount"),
                                    "publishing_country": item.get("publishingCountry"),
                                    "publisher": _clip(item.get("publishingOrganizationTitle"), 160)}})
        return Parsed(_status(status, items, rejected), items, document.get("count"), rejected)


# ---------------------------------------------------------------------------------------------- data.europa.eu
def _first_text(value) -> "str | None":
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("en") or next((text for text in value.values() if isinstance(text, str)), None)
    return None


EU_MEMBER_CODES = frozenset("AT BE BG HR CY CZ DK EE FI FR DE GR IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS LI NO CH GB UA RS MD AL BA ME MK XK TR".split())


class DataEuropaDatasets(Executor):
    executor_id, host = "data_europa_datasets", "data.europa.eu"
    minimum_interval = 3.0
    per_page = 50  # a hundred multilingual records can pass the 4 MiB response bound
    refresh_days = 30
    follow_pages = 2
    renders = frozenset(TOPIC_DIMENSIONS + ("file_format", "europa_theme", "geography"))

    def accepts(self, dimension, value):
        if dimension.id in ("file_format", "europa_theme"):
            return bool(value.attributes.get("europa"))
        if dimension.id == "geography":
            return value.attributes.get("iso2") in EU_MEMBER_CODES
        return True

    def render(self, assignment, params, *, page=1):
        topics = [value.text for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        facets = {}
        fmt = assignment.get("file_format")
        if fmt is not None:
            facets["format"] = [fmt.attributes["europa"]]
        theme = assignment.get("europa_theme")
        if theme is not None:
            facets["categories"] = [theme.attributes["europa"]]
        geography = assignment.get("geography")
        if geography is not None:
            facets["country"] = [geography.attributes["iso2"].lower()]
        if not topics and not facets:
            return "empty_query"
        query = [("filter", "dataset"), ("limit", self.per_page), ("page", page - 1),
                 ("includes", "id,title,distributions,country")]
        if topics:
            query.insert(0, ("q", " ".join(topics)))
        if facets:
            query.append(("facets", json.dumps(facets, sort_keys=True, separators=(",", ":"))))
        return self.request("/api/hub/search/search", query, page=page)

    def parse(self, status, body):
        document = _json(body)
        result = document.get("result") if type(document) is dict else None
        if status != 200 or type(result) is not dict or type(result.get("results")) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        for item in result["results"]:
            if type(item) is not dict or not isinstance(item.get("id"), str):
                rejected += 1
                continue
            licences, formats, files = set(), set(), []
            for distribution in item.get("distributions") or []:
                if type(distribution) is not dict:
                    continue
                licence = distribution.get("license") if type(distribution.get("license")) is dict else {}
                reported = licence.get("resource") or licence.get("id")
                if reported:
                    licences.add(str(reported)[:200])
                fmt = distribution.get("format") if type(distribution.get("format")) is dict else {}
                if fmt.get("id"):
                    formats.add(str(fmt["id"])[:40])
                for address in (distribution.get("download_url") or distribution.get("access_url") or [])[:1]:
                    if isinstance(address, str) and len(files) < 5:
                        files.append({"url": address[:300], "format": fmt.get("id")})
            items.append({"key": "europa:" + item["id"], "url": "https://data.europa.eu/data/datasets/" + item["id"],
                          "kind": "dataset", "title": _clip(_first_text(item.get("title"))), "description": None,
                          "licence_reported": " | ".join(sorted(licences)) if licences else None,
                          "licence_field": "data.europa.eu distributions[].license",
                          "extra": {"formats": sorted(formats)[:10], "files": files,
                                    "country": (item.get("country") or {}).get("id") if type(item.get("country")) is dict else None}})
        return Parsed(_status(status, items, rejected), items, result.get("count"), rejected)


# ---------------------------------------------------------------------------------------------------- data.gov
class DataGovDatasets(Executor):
    executor_id, host = "datagov_datasets", "api.gsa.gov"
    #: api.data.gov's documented public demonstration key, sent by the transport; not a credential of the owner.
    static_headers = {"X-Api-Key": "DEMO_KEY"}
    minimum_interval = 400.0  # DEMO_KEY: 10 an hour per address
    daily_ceiling = 40  # DEMO_KEY: 50 a day per address
    refresh_days = 60
    follow_pages = 0
    per_page = 50
    renders = frozenset(TOPIC_DIMENSIONS)

    def render(self, assignment, params, *, page=1):
        topics = [value.text for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        if not topics or page != 1:
            return "empty_query" if not topics else "cursor_pagination_first_page_only"
        return self.request("/technology/datagov/v4/search", [("q", " ".join(topics)), ("per_page", self.per_page)],
                            page=page)

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("results")) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        for item in document["results"]:
            dcat = item.get("dcat") if type(item) is dict and type(item.get("dcat")) is dict else None
            identifier = item.get("identifier") if type(item) is dict else None
            if dcat is None or not isinstance(identifier, str):
                rejected += 1
                continue
            files = [{"url": str(row.get("downloadURL") or row.get("accessURL") or "")[:300],
                      "format": row.get("mediaType") or row.get("format")}
                     for row in (dcat.get("distribution") or [])[:5] if type(row) is dict]
            items.append({"key": "datagov:" + identifier[:300], "url": dcat.get("landingPage") or identifier, "kind": "dataset",
                          "title": _clip(dcat.get("title")), "description": None,
                          "licence_reported": dcat.get("license") if isinstance(dcat.get("license"), str) else None,
                          "licence_field": "data.gov dcat license",
                          "extra": {"files": files, "publisher": _clip((dcat.get("publisher") or {}).get("name"), 160) if type(dcat.get("publisher")) is dict else None,
                                    "access_level": dcat.get("accessLevel")}})
        return Parsed(_status(status, items, rejected), items, None, rejected)


# ------------------------------------------------------------------------------------------------------- arXiv
_ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom",
         "opensearch": "http://a9.com/-/spec/opensearch/1.1/"}


class Arxiv(Executor):
    executor_id, host = "arxiv", "export.arxiv.org"
    minimum_interval = 3.5  # arXiv asks for one request every three seconds
    refresh_days = 30
    follow_pages = 1
    per_page = 50
    accept = "application/atom+xml"
    renders = frozenset(TOPIC_DIMENSIONS + ("arxiv_category", "time_window"))

    def accepts(self, dimension, value):
        if dimension.id == "arxiv_category":
            return bool(value.attributes.get("arxiv"))
        return True

    def render(self, assignment, params, *, page=1):
        parts = ['all:"' + value.text + '"' for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        category = assignment.get("arxiv_category")
        if category is not None:
            parts.append("cat:" + category.attributes["arxiv"])
        window = assignment.get("time_window")
        if window is not None:
            parts.append("submittedDate:[" + window.attributes["from"].replace("-", "") + "0000 TO "
                         + window.attributes["to"].replace("-", "") + "2359]")
        if not parts:
            return "empty_query"
        return self.request("/api/query", [("search_query", " AND ".join(parts)), ("start", (page - 1) * self.per_page),
                                           ("max_results", self.per_page)], page=page)

    def parse(self, status, body):
        if status != 200:
            return Parsed(FAILED)
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError:
            return Parsed(FAILED)
        items, rejected = [], 0
        for entry in root.findall("atom:entry", _ATOM):
            address = (entry.findtext("atom:id", default="", namespaces=_ATOM) or "").strip()
            key = candidate_key(address.replace("http://", "https://"))
            if key is None or not key[0].startswith("doi:10.48550/arxiv."):
                rejected += 1
                continue
            category = entry.find("arxiv:primary_category", _ATOM)
            items.append({"key": key[0], "url": address.replace("http://", "https://"), "kind": "paper",
                          "title": _clip(entry.findtext("atom:title", default="", namespaces=_ATOM)), "description": None,
                          "licence_reported": None, "licence_field": "arxiv api reports no licence",
                          "extra": {"published": entry.findtext("atom:published", default="", namespaces=_ATOM),
                                    "category": category.get("term") if category is not None else None}})
        total = root.findtext("opensearch:totalResults", default="", namespaces=_ATOM)
        return Parsed(_status(status, items, rejected), items, int(total) if total.isdigit() else None, rejected)


# --------------------------------------------------------------------------------------------------------- npm
class NpmSearch(Executor):
    executor_id, host = "npm_search", "registry.npmjs.org"
    minimum_interval = 3.0
    refresh_days = 30
    follow_pages = 1
    per_page = 100
    renders = frozenset(TOPIC_DIMENSIONS + ("file_format",))

    def accepts(self, dimension, value):
        if dimension.id == "file_format":
            return bool(value.attributes.get("npm"))
        return True

    def render(self, assignment, params, *, page=1):
        words_ = [value.text for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        fmt = assignment.get("file_format")
        if fmt is not None:
            words_.append("keywords:" + fmt.attributes["npm"])
        if not words_:
            return "empty_query"
        return self.request("/-/v1/search", [("text", " ".join(words_)), ("size", self.per_page),
                                              ("from", (page - 1) * self.per_page)], page=page)

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("objects")) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        for item in document["objects"]:
            package = item.get("package") if type(item) is dict and type(item.get("package")) is dict else None
            name = package.get("name") if package else None
            if not isinstance(name, str) or not re.fullmatch(r"(?:@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*", name):
                rejected += 1
                continue
            links = package.get("links") if type(package.get("links")) is dict else {}
            # Maintainer and publisher names and addresses stay in the stored response only; never copied here.
            items.append({"key": "npm:" + name, "url": "https://www.npmjs.com/package/" + name, "kind": "package",
                          "title": name, "description": _clip(package.get("description")),
                          "licence_reported": package.get("license") if isinstance(package.get("license"), str) else None,
                          "licence_field": "npm package license",
                          "extra": {"version": package.get("version"), "repository": _clip(links.get("repository"), 300),
                                    "homepage": _clip(links.get("homepage"), 300),
                                    "keywords": [word for word in package.get("keywords") or [] if isinstance(word, str)][:15]}})
        return Parsed(_status(status, items, rejected), items, document.get("total"), rejected)


# ------------------------------------------------------------------------------------------- Ollama web search
class OllamaWebSearch(Executor):
    executor_id, host, access = "ollama_web_search", "ollama.com", "https_post_key"
    engine_kind = "search_service"
    minimum_interval = 4.0
    daily_ceiling = 300  # declared ceiling within the owner's existing Ollama subscription
    refresh_days = 30
    follow_pages = 0
    per_page = 10  # the documented maximum
    key_variable = "OLLAMA_API_KEY"
    renders = frozenset(TOPIC_DIMENSIONS + ("file_format", "geography", "natural_language", "natural_language_endonym"))

    def check_params(self, params):
        if set(params) - {"suffix"} or not isinstance(params.get("suffix", ""), str) or len(params.get("suffix", "")) > 60:
            raise ValueError("executor_params:" + self.executor_id)

    def render(self, assignment, params, *, page=1):
        if page != 1:
            return "no_pagination"
        parts = [value.text for value in _topic_phrases(assignment, TOPIC_DIMENSIONS)]
        fmt = assignment.get("file_format")
        if fmt is not None:
            parts.append(fmt.text)
        for name in ("geography", "natural_language_endonym", "natural_language"):
            value = assignment.get(name)
            if value is not None:
                parts.append(value.text)
        if not parts:
            return "empty_query"
        if params.get("suffix"):
            parts.append(params["suffix"])
        return self.text_request(" ".join(parts))

    def text_request(self, text: str) -> dict:
        return self.request("/api/web_search", [], page=1, method="POST",
                            body={"query": text[:400], "max_results": self.per_page})

    def parse(self, status, body):
        document = _json(body)
        if status != 200 or type(document) is not dict or type(document.get("results")) is not list:
            return Parsed(FAILED)
        items, rejected = [], 0
        for item in document["results"]:
            url = item.get("url") if type(item) is dict else None
            key = candidate_key(url) if isinstance(url, str) else None
            if key is None:
                rejected += 1
                continue
            items.append({"key": key[0], "url": canonical_url(url), "kind": key[1], "title": _clip(item.get("title")),
                          "description": None, "licence_reported": None, "licence_field": "web search reports no licence",
                          "extra": {"host": urlsplit(url).hostname}})
        return Parsed(_status(status, items, rejected), items, None, rejected)


class PypiSearch(Executor):
    executor_id, host, access = "pypi_search", "pypi.org", "unsupported"
    available = False
    unavailable_reason = ("PyPI offers no search interface: its XML-RPC search was switched off, its HTML search page is "
                          "not an automated interface, and its JSON API reads one named project")
    renders = frozenset(TOPIC_DIMENSIONS)

    def render(self, assignment, params, *, page=1):
        return "executor_unavailable"

    def parse(self, status, body):
        return Parsed(REFUSED)


ENGINES = (GitHubRepositories, GitHubCode, HuggingFaceModels, HuggingFaceDatasets, OpenAlexWorks, OpenverseImages,
           OpenverseAudio, GbifDatasets, DataEuropaDatasets, DataGovDatasets, Arxiv, NpmSearch, OllamaWebSearch,
           PypiSearch)


def registry() -> dict:
    """The slot's factory table: executor id -> a new engine instance."""
    return {engine.executor_id: engine() for engine in ENGINES}


def request_url(request: dict) -> str:
    """The request as an address, for evidence: never carries a credential (headers are kept apart)."""
    query = urlencode([(str(name), str(value)) for name, value in request["params"]]) if request["params"] else ""
    return urlunsplit(("https", request["host"], request["path"], query, ""))


def request_digest(request: dict) -> str:
    return digest(request)
