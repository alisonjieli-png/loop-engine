"""Discovery engines: where harness files are found, each answering with typed leads.

A lead names a repository and, when the source knows it, the path, the git
object identity and the commit of one file. Discovery reads metadata only:
it never copies a body and never runs anything. Every engine of the
`library_ingestion_source` slot's kinds (public repository reader, skill
directory reader, registry reader) answers with `licensed_import_lead/v1`:

```text
Discovery engines, in the order their leads are processed
├── declared_repositories: the curated high-yield repositories and the owner's seed repositories
├── owner_seed_resolver: a name the owner gave, resolved to one exact repository, or recorded as
│   ambiguous or not found with its candidates; never guessed
├── research_seed_lists: the September 23 research lists of skills and plugins
├── clawhub_feeds: ClawHub's two public feeds, which its robots file allows; entries that name a
│   GitHub repository, path and commit become leads, hosted bundles are recorded as not on GitHub
├── awesome_lists: GitHub repository links in curated awesome lists
├── github_code_search: harness file names and paths, partitioned by size band to pass the
│   1,000-result cap of one query
├── github_topic_search: repositories by topic, partitioned by creation date
├── npm_search: packages by keyword, through their declared GitHub repository
└── mcp_registry_updates: the official registry's entries changed since a recorded time, by cursor;
    each entry's upstream GitHub repository becomes a lead
```

Every engine records the requests it sent and the cursor to resume from, so
a scheduled round continues where the last one stopped.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from loop_engine.core.library_ingestion.record_rules import now_utc

from .github_api import MAXIMUM_PAGE, NAME, OWNER, ReadRefused
from .records import LEAD_RECORD_TYPE, REASONS, refusal

DECLARED, SEEDS, RESEARCH, CLAWHUB, AWESOME, CODE_SEARCH, TOPIC_SEARCH, NPM, REGISTRY = (
    "declared_repositories", "owner_seed_resolver", "research_seed_lists", "clawhub_feeds", "awesome_lists",
    "github_code_search", "github_topic_search", "npm_search", "mcp_registry_updates")
ENGINE_ORDER = (DECLARED, SEEDS, RESEARCH, CLAWHUB, AWESOME, CODE_SEARCH, TOPIC_SEARCH, NPM, REGISTRY)
#: The order a repository's leads are processed in: the lower of its sources wins.
SOURCE_PRIORITY = {engine: index for index, engine in enumerate(ENGINE_ORDER)}
_GITHUB_LINK = re.compile(r"github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100})")
_NOT_REPOSITORIES = frozenset({"topics", "sponsors", "orgs", "features", "marketplace", "apps", "settings",
                               "about", "login", "explore", "collections", "trending", "site", "search"})


def lead(source_id: str, engine_id: str, repository: str, *, revision=None, path=None, blob_sha=None,
         kind_hint=None, detail=None) -> dict:
    return {"record_type": LEAD_RECORD_TYPE, "source_id": source_id, "engine_id": engine_id,
            "repository": repository, "revision": revision, "path": path, "blob_sha": blob_sha,
            "kind_hint": kind_hint, "found_at": now_utc(), "detail": detail or {}}


def repository_name(value: str) -> "str | None":
    """owner/name from a GitHub address or an owner/name string, or None when it is neither."""
    text = str(value or "").strip()
    if text.startswith(("git+", "git:")):
        text = text.split("+", 1)[-1]
    if "github.com" in text:
        match = _GITHUB_LINK.search(text)
        if not match:
            return None
        owner, name = match.group(1), match.group(2)
    else:
        owner, _, name = text.partition("/")
    name = re.sub(r"\.git\Z", "", name).rstrip(".")
    if not OWNER.match(owner) or not NAME.match(name) or owner.lower() in _NOT_REPOSITORIES or name in (".", ".."):
        return None
    return f"{owner}/{name}"


@dataclass
class DiscoveryResult:
    leads: list = field(default_factory=list)
    refusals: list = field(default_factory=list)
    cursor: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    requests: int = 0


def declared_repositories(declaration: dict) -> DiscoveryResult:
    """Leads for every curated repository, carrying its declared scope."""
    result = DiscoveryResult()
    for row in declaration.get("repositories", ()):
        repository = repository_name(row["repository"])
        if repository is None:
            result.refusals.append(refusal("discovery", "source_unavailable", repository=row["repository"],
                                           detail="not a repository name", source_ids=(row["source_id"],)))
            continue
        result.leads.append(lead(row["source_id"], DECLARED, repository,
                                 detail={"scope": {key: row[key] for key in ("kinds", "include", "exclude") if key in row}}))
    return result


def resolve_owner_seeds(declaration: dict, api) -> DiscoveryResult:
    """Each seed name to one exact repository, or a recorded ambiguity; a name is never guessed.

    A seed with a declared repository is taken as declared. Otherwise each
    declared query runs as a repository search sorted by stars. A result
    whose repository name equals one of the seed's accepted names is a match.
    One match resolves the seed; several resolve it only when the first has at
    least ten times the stars of the second and at least 100 stars; anything
    else is recorded as ambiguous or not found, with the candidates seen.
    """
    result = DiscoveryResult()
    for seed in declaration.get("owner_seeds", ()):
        if seed.get("repository"):
            repository = repository_name(seed["repository"])
            result.leads.append(lead(seed["source_id"], SEEDS, repository, path=seed.get("path"),
                                     detail={"seed": seed["seed"], "resolution": "declared"}))
            result.notes.append({"seed": seed["seed"], "state": "declared", "repository": repository})
            continue
        accepted = {name.lower() for name in seed.get("names", ())}
        seen = {}
        for query in seed.get("queries", ()):
            answer = api.repository_search(query, 1)
            result.requests += 1
            for item in ((answer.get("body") or {}).get("items") or [])[:30]:
                seen.setdefault(item["full_name"], item.get("stargazers_count") or 0)
        matches = sorted(((stars, name) for name, stars in seen.items()
                          if name.rsplit("/", 1)[-1].lower() in accepted), reverse=True)
        candidates = [{"repository": name, "stars": stars} for stars, name in matches[:5]] or \
            [{"repository": name, "stars": stars} for name, stars in sorted(seen.items(), key=lambda row: -row[1])[:5]]
        clear = matches and (len(matches) == 1 or (matches[0][0] >= 100 and matches[0][0] >= 10 * matches[1][0]))
        if clear:
            repository = matches[0][1]
            result.leads.append(lead(seed["source_id"], SEEDS, repository,
                                     detail={"seed": seed["seed"], "resolution": "search"}))
            result.notes.append({"seed": seed["seed"], "state": "resolved", "repository": repository,
                                 "candidates": candidates})
        else:
            reason = "ambiguous_seed_name" if matches else "seed_name_not_found"
            result.refusals.append(refusal("discovery", reason, detail=seed["seed"], source_ids=(seed["source_id"],)))
            result.notes.append({"seed": seed["seed"], "state": reason, "candidates": candidates})
    return result


def research_seed_lists(declaration: dict, root) -> DiscoveryResult:
    """Leads from the research lists: repository, revision and path of each ranked record."""
    result = DiscoveryResult()
    for row in declaration.get("research_seeds", ()):
        path = root / row["file"]
        if not path.is_file():
            result.refusals.append(refusal("discovery", "source_unavailable", detail=row["file"],
                                           source_ids=(row["source_id"],)))
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            repository = repository_name(record.get("canonical_repository") or record.get("repository") or "")
            if repository is None:
                continue
            result.leads.append(lead(row["source_id"], RESEARCH, repository, path=record.get("source_path"),
                                     detail={"research_id": record.get("research_id"), "rank": record.get("rank")}))
    return result


def clawhub_feeds(declaration: dict, transport) -> DiscoveryResult:
    """GitHub-backed entries of ClawHub's public feeds; hosted bundles are recorded, not fetched."""
    result = DiscoveryResult()
    for feed in declaration.get("feeds", ()):
        response = transport.get(feed["host"], feed["path"])
        result.requests += 1
        if response.status != 200:
            result.refusals.append(refusal("discovery", "source_unavailable", detail=feed["path"],
                                           source_ids=(feed["source_id"],)))
            continue
        for entry in json.loads(response.body).get("entries", ()):
            placed = False
            for candidate in (entry.get("install") or {}).get("candidates", ()):
                github = candidate.get("github") or {}
                repository = repository_name(github.get("repo") or "")
                if repository and re.fullmatch(r"[0-9a-f]{40}", str(github.get("commit") or "")):
                    result.leads.append(lead(feed["source_id"], CLAWHUB, repository, revision=None,
                                             path=github.get("path"), detail={"entry": entry.get("id"),
                                                                             "listed_revision": github["commit"]}))
                    placed = True
                    break
            if not placed:
                result.refusals.append(refusal("discovery", "feed_entry_not_on_github", detail=str(entry.get("id")),
                                               source_ids=(feed["source_id"],)))
    return result


def awesome_lists(declaration: dict, read_file) -> DiscoveryResult:
    """Repository links in curated awesome lists, read through the snapshot engine."""
    result = DiscoveryResult()
    for row in declaration.get("awesome_lists", ()):
        payload = read_file(row["repository"], row.get("path", "README.md"))
        result.requests += 1
        if payload is None:
            result.refusals.append(refusal("discovery", "source_unavailable", repository=row["repository"],
                                           source_ids=(row["source_id"],)))
            continue
        found = set()
        for match in _GITHUB_LINK.finditer(payload.decode("utf-8", "replace")):
            repository = repository_name(f"{match.group(1)}/{match.group(2)}")
            if repository and repository.lower() != row["repository"].lower() and repository.lower() not in found:
                found.add(repository.lower())
                result.leads.append(lead(row["source_id"], AWESOME, repository, detail={"list": row["repository"]}))
    return result


def code_search(declaration: dict, api, *, query_budget: int, cursor: "dict | None" = None) -> DiscoveryResult:
    """Harness files by name and path, each spec partitioned by size band, breadth first by page.

    Page one of every spec and band is read before page two of any, so a
    small query budget still covers every harness kind. A band is finished
    when a page comes back short or the band's result count is reached.
    """
    result = DiscoveryResult(cursor=dict(cursor or {}))
    lanes = []
    for spec in declaration.get("code_search", ()):
        for low, high in spec.get("size_bands") or [[None, None]]:
            band = f"{low}..{high}" if low is not None else "all"
            lanes.append((spec, low, high, band, f"{spec['source_id']}|{band}"))
    sent = 0
    for page in range(1, MAXIMUM_PAGE + 1):
        for spec, low, high, band, state_key in lanes:
            done = result.cursor.get(state_key, 0)
            if done == -1 or done >= page or page > spec.get("pages", MAXIMUM_PAGE):
                continue
            if sent >= query_budget:
                result.notes.append({"stopped": "query_budget", "at": state_key, "page": page})
                return result
            terms = list(spec["terms"]) + ([f"size:{low}..{high}"] if low is not None else [])
            try:
                answer = api.code_search(" ".join(terms), page)
            except ReadRefused as error:
                result.refusals.append(refusal("discovery", "query_failed", detail=str(error),
                                               source_ids=(spec["source_id"],)))
                result.cursor[state_key] = -1
                continue
            sent += 1
            result.requests += 1
            body = answer.get("body") or {}
            items = body.get("items") or []
            if answer.get("status") != 200:
                result.refusals.append(refusal("discovery", "query_failed", detail=f"{state_key} page {page}",
                                               source_ids=(spec["source_id"],)))
                result.cursor[state_key] = -1
                continue
            for item in items:
                repository = repository_name((item.get("repository") or {}).get("full_name") or "")
                if repository and not (item.get("repository") or {}).get("fork"):
                    result.leads.append(lead(spec["source_id"], CODE_SEARCH, repository, path=item.get("path"),
                                             blob_sha=item.get("sha"), kind_hint=spec.get("kind"),
                                             detail={"band": band, "page": page}))
            finished = len(items) < 100 or page * 100 >= min(1000, body.get("total_count") or 0)
            result.cursor[state_key] = -1 if finished else page
    return result


def topic_search(declaration: dict, api, *, query_budget: int, cursor: "dict | None" = None) -> DiscoveryResult:
    """Repositories by topic, sorted by stars, partitioned by creation date."""
    result = DiscoveryResult(cursor=dict(cursor or {}))
    spec = declaration.get("topic_search") or {}
    sent = 0
    for topic in spec.get("topics", ()):
        for start, end in spec.get("created_ranges") or [[None, None]]:
            state_key = f"{topic}|{start}..{end}"
            page = int(result.cursor.get(state_key, 0)) + 1
            while page <= min(MAXIMUM_PAGE, spec.get("pages", MAXIMUM_PAGE)):
                if sent >= query_budget:
                    result.notes.append({"stopped": "query_budget", "at": state_key})
                    return result
                terms = [f"topic:{topic}", "fork:false"]
                if start:
                    terms.append(f"created:{start}..{end}")
                if spec.get("minimum_stars"):
                    terms.append(f"stars:>={spec['minimum_stars']}")
                answer = api.repository_search(" ".join(terms), page)
                sent += 1
                result.requests += 1
                body = answer.get("body") or {}
                items = body.get("items") or []
                for item in items:
                    repository = repository_name(item.get("full_name") or "")
                    if repository:
                        result.leads.append(lead(f"topic.{topic}", TOPIC_SEARCH, repository,
                                                 detail={"stars": item.get("stargazers_count"), "topic": topic}))
                result.cursor[state_key] = page
                if len(items) < 100:
                    break
                page += 1
    return result


def npm_search(declaration: dict, transport, *, request_budget: int) -> DiscoveryResult:
    """Packages found by keyword, through the GitHub repository each one declares."""
    result = DiscoveryResult()
    spec = declaration.get("npm_search") or {}
    for text in spec.get("texts", ()):
        for page in range(spec.get("pages", 1)):
            if result.requests >= request_budget:
                return result
            response = transport.get("registry.npmjs.org", "/-/v1/search",
                                     {"text": text, "size": 250, "from": page * 250})
            result.requests += 1
            if response.status != 200:
                break
            objects = json.loads(response.body).get("objects") or []
            for item in objects:
                package = item.get("package") or {}
                repository = repository_name(((package.get("links") or {}).get("repository")) or "")
                if repository:
                    result.leads.append(lead(f"npm.{text}", NPM, repository,
                                             detail={"package": package.get("name"), "version": package.get("version")}))
            if len(objects) < 250:
                break
    return result


def registry_updates(declaration: dict, transport, *, request_budget: int, cursor: "dict | None" = None) -> DiscoveryResult:
    """Entries of the official registry updated since a recorded time, followed by cursor."""
    spec = declaration.get("registry") or {}
    result = DiscoveryResult(cursor=dict(cursor or {}))
    next_cursor = result.cursor.get("cursor")
    updated_since = result.cursor.get("updated_since") or spec.get("updated_since")
    seen = 0
    while result.requests < request_budget and seen < spec.get("maximum_entries", 5000):
        query = {"limit": spec.get("page_size", 100), "updated_since": updated_since}
        if next_cursor:
            query["cursor"] = next_cursor
        response = transport.get(spec["host"], "/v0.1/servers", query)
        result.requests += 1
        if response.status != 200:
            result.refusals.append(refusal("discovery", "source_unavailable", detail=f"registry {response.status}",
                                           source_ids=("registry.mcp.official",)))
            break
        page = json.loads(response.body)
        for entry in page.get("servers", ()):
            seen += 1
            server = entry.get("server") or {}
            official = (entry.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}
            repository = repository_name(((server.get("repository") or {}).get("url")) or "")
            if repository and official.get("isLatest"):
                result.leads.append(lead("registry.mcp.official", REGISTRY, repository,
                                         detail={"server": server.get("name"), "version": server.get("version"),
                                                 "updated_at": official.get("updatedAt")}))
        next_cursor = (page.get("metadata") or {}).get("nextCursor")
        result.cursor["cursor"] = next_cursor
        if not next_cursor:
            result.cursor["complete"] = True
            break
    result.cursor["updated_since"] = updated_since
    return result


def discovery_reasons() -> tuple:
    return REASONS["discovery"]
