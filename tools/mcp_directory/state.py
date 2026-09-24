"""The saved state of the directory build: registry entries, the sync cursor, and the other sources' snapshots.

Kind: file-backed state with atomic writes, plus the readers that fill it. The state folder lives outside
the repository (the command names it). It holds the latest registry entry for each server name, the watermark
of the last complete traversal, and, while a traversal is under way, its mode, its updated_since value and the
cursor of the next page, saved with the entries every ten pages and whenever the run stops. A stopped run resumes
from that cursor with the same mode, so a lost connection or a stopped job repeats at most ten pages. Page bytes
land in a content-addressed quarantine
(`loop_engine.core.library_ingestion.quarantine`) before they are read.

The first traversal is either a full read of the registry or the recorded pages of the September 23, 2026 research
traversal, each checked against its recorded digest. Every later run reads only the entries updated since the
watermark, minus a one hour overlap. With updated_since the registry also returns deleted entries, and the state
keeps their status so the build leaves them out.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loop_engine.core.library_ingestion.quarantine import Quarantine
from loop_engine.core.library_ingestion.request_log import PauseExceedsBound, RequestCeilingReached

from .sources import (
    DOCKER_ARCHIVE_HOST, DOCKER_REPOSITORY, GITHUB_DIRECTORY_HOST, GITHUB_DIRECTORY_PATH, OFFICIAL_META, PAGE_SIZE,
    REGISTRY_HOST, REGISTRY_LIST_PATH, read_json_page)

SYNC_RECORD_TYPE = "mcp_directory_registry_sync/v1"
SNAPSHOT_RECORD_TYPE = "mcp_directory_source_snapshot/v1"
OVERLAP = timedelta(hours=1)
CHECKPOINT_PAGES = 10
FULL, INCREMENTAL = "full", "incremental"
GITHUB_API_HOST = "api.github.com"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(value: str) -> datetime:
    return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


class DirectoryState:
    """One state folder: registry entries by name, the sync record and the other sources' snapshot records."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.quarantine = Quarantine(self.folder / "quarantine")
        self.entries: dict = {}
        self.sync: dict = {"record_type": SYNC_RECORD_TYPE, "watermark": "", "last_complete_at": "", "run": None,
                           "seeded_from": None, "pages_read": 0}
        entries_path, sync_path = self.folder / "registry-entries.jsonl", self.folder / "registry-sync.json"
        if sync_path.exists():
            value = json.loads(sync_path.read_text(encoding="utf-8"))
            if value.get("record_type") != SYNC_RECORD_TYPE:
                raise ValueError(f"the state folder's sync record is not {SYNC_RECORD_TYPE}")
            self.sync = value
        if entries_path.exists():
            for line in entries_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    self.entries[entry["server"]["name"]] = entry

    def save(self) -> None:
        lines = [json.dumps(self.entries[name], sort_keys=True, ensure_ascii=False) for name in sorted(self.entries)]
        write_atomic(self.folder / "registry-entries.jsonl", "\n".join(lines) + ("\n" if lines else ""))
        write_atomic(self.folder / "registry-sync.json", json.dumps(self.sync, indent=1, sort_keys=True) + "\n")

    def snapshot(self, name: str) -> "dict | None":
        path = self.folder / f"{name}-snapshot.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def save_snapshot(self, name: str, record: dict) -> None:
        write_atomic(self.folder / f"{name}-snapshot.json", json.dumps(record, indent=1, sort_keys=True) + "\n")

    def keep(self, entries) -> int:
        """Keep the latest version of each entry; a deleted or deprecated status replaces an older active one."""
        kept = 0
        for entry in entries:
            server = entry.get("server") if isinstance(entry, dict) else None
            meta = ((entry.get("_meta") or {}).get(OFFICIAL_META) or {}) if isinstance(entry, dict) else {}
            if not isinstance(server, dict) or not server.get("name") or meta.get("isLatest") is False:
                continue
            self.entries[str(server["name"])] = entry
            kept += 1
        return kept


def prune_quarantine(state: DirectoryState, *, keep_days: int = 14, now: "float | None" = None) -> int:
    """Remove page bytes older than keep_days, except those the saved snapshots still name; the entries stay."""
    import time
    keep = set()
    for name in ("github", "docker"):
        record = state.snapshot(name) or {}
        keep.update(record.get("pages") or ())
        if record.get("archive_sha256"):
            keep.add(record["archive_sha256"])
    limit = (now or time.time()) - keep_days * 86400
    removed = 0
    for path in (state.folder / "quarantine").glob("*/*"):
        if path.is_file() and path.name not in keep and path.stat().st_mtime < limit:
            path.chmod(0o600)
            path.unlink()
            removed += 1
    return removed


def seed_from_research(state: DirectoryState, acquisitions, request_logs) -> dict:
    """Load the recorded registry pages of the research traversal, each checked against its recorded digest."""
    if state.entries or state.sync.get("watermark"):
        raise ValueError("a seed starts an empty state folder only")
    started, pages = [], []
    registry_digests = set()
    for path in acquisitions:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
        for source in record.get("sources") or ():
            if source.get("host") != REGISTRY_HOST or source.get("path") != REGISTRY_LIST_PATH:
                continue
            body = Path(source["quarantine_file"]).read_bytes()
            stored = state.quarantine.put(body)
            if stored.digest != source["sha256"]:
                raise ValueError(f"page {source['name']} does not hold the bytes its record names")
            entries, _cursor = read_json_page(body)
            state.keep(entries)
            registry_digests.add(stored.digest)
            pages.append({"name": source["name"], "sha256": stored.digest, "bytes": stored.size_bytes})
    for path in request_logs:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            row = json.loads(line) if line.strip() else {}
            if row.get("host") == REGISTRY_HOST and row.get("body_digest") in registry_digests:
                started.append(row["started_at"])
    if not pages or not started:
        raise ValueError("the research records hold no registry page with a request time")
    watermark = min(started)
    state.sync.update({"watermark": watermark, "last_complete_at": max(started), "run": None, "pages_read": len(pages),
                       "seeded_from": {"pages": len(pages), "first_request_at": watermark, "last_request_at": max(started),
                                       "acquisition_records": [str(path) for path in acquisitions]}})
    state.save()
    return state.sync["seeded_from"]


def sync_registry(state: DirectoryState, transport, *, now: str = "", maximum_pages: int = 2000) -> dict:
    """Read the registry from the saved cursor, a full traversal first and then only what changed.

    Returns a summary with complete true, or with the reason the run stopped; a stopped run resumes next time.
    """
    now = now or utc_now()
    run = state.sync.get("run")
    if not run:
        if state.sync.get("watermark"):
            since = (_parse_time(state.sync["watermark"]) - OVERLAP).strftime("%Y-%m-%dT%H:%M:%SZ")
            run = {"mode": INCREMENTAL, "updated_since": since, "cursor": None, "pages": 0, "entries": 0, "started_at": now}
        else:
            run = {"mode": FULL, "updated_since": None, "cursor": None, "pages": 0, "entries": 0, "started_at": now}
        state.sync["run"] = run
    stopped = ""
    try:
        for _page in range(maximum_pages):
            query = {"limit": str(PAGE_SIZE), "version": "latest"}
            if run["updated_since"]:
                query["updated_since"] = run["updated_since"]
            if run["cursor"]:
                query["cursor"] = run["cursor"]
            response = transport.get(REGISTRY_HOST, REGISTRY_LIST_PATH, query)
            if response.status != 200:
                stopped = f"status {response.status}"
                break
            state.quarantine.put(response.body)
            try:
                entries, cursor = read_json_page(response.body)
            except ValueError as error:
                stopped = str(error)
                break
            run["entries"] += state.keep(entries)
            run["pages"] += 1
            state.sync["pages_read"] = int(state.sync.get("pages_read") or 0) + 1
            if cursor and cursor == run["cursor"]:
                stopped = "the registry repeated a cursor"
                break
            run["cursor"] = cursor
            if not cursor:
                state.sync.update({"watermark": run["started_at"], "last_complete_at": now, "run": None,
                                   "last_run": {key: run[key] for key in ("mode", "updated_since", "pages", "entries",
                                                                          "started_at")}})
                state.save()
                return {"complete": True, **state.sync["last_run"]}
            if run["pages"] % CHECKPOINT_PAGES == 0:
                state.save()
        else:
            stopped = "page ceiling"
    except (RequestCeilingReached, PauseExceedsBound) as error:
        stopped = type(error).__name__
    state.save()
    return {"complete": False, "stopped": stopped, **{key: run[key] for key in ("mode", "pages", "entries", "cursor")}}


def read_github_directory(state: DirectoryState, transport, *, now: str = "") -> dict:
    """Every entry of GitHub's MCP directory, through its public list interface."""
    entries, cursor, pages, digests = [], None, 0, []
    while True:
        query = {"limit": str(PAGE_SIZE)}
        if cursor:
            query["cursor"] = cursor
        response = transport.get(GITHUB_DIRECTORY_HOST, GITHUB_DIRECTORY_PATH, query)
        if response.status != 200:
            raise ValueError(f"GitHub's directory answered status {response.status}")
        digests.append(state.quarantine.put(response.body).digest)
        page, following = read_json_page(response.body)
        entries.extend(page)
        pages += 1
        if not following or following == cursor or pages > 100:
            break
        cursor = following
    record = {"record_type": SNAPSHOT_RECORD_TYPE, "source": "github", "checked_at": now or utc_now(),
              "pages": digests, "entries": len(entries)}
    state.save_snapshot("github", {**record, "items": entries})
    return record


def read_docker_catalog(state: DirectoryState, transport, *, now: str = "") -> dict:
    """The Docker MCP Catalog repository at the commit its main branch names now, as one source archive."""
    response = transport.get(GITHUB_API_HOST, f"/repos/{DOCKER_REPOSITORY}/commits/main")
    if response.status != 200:
        raise ValueError(f"the catalog's commit lookup answered status {response.status}")
    commit = str(json.loads(response.body).get("sha") or "")
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("the catalog's commit lookup did not name a full commit")
    archive = transport.get(DOCKER_ARCHIVE_HOST, f"/{DOCKER_REPOSITORY}/tar.gz/{commit}")
    if archive.status != 200:
        raise ValueError(f"the catalog archive answered status {archive.status}")
    stored = state.quarantine.put(archive.body)
    record = {"record_type": SNAPSHOT_RECORD_TYPE, "source": "docker", "checked_at": now or utc_now(), "commit": commit,
              "archive_sha256": stored.digest, "archive_bytes": stored.size_bytes}
    state.save_snapshot("docker", record)
    return record


LICENCE_QUERY_FIELDS = "licenseInfo { spdxId } isArchived"


def github_licences(state: DirectoryState, repositories, *, runner=None, batch: int = 100, maximum: int = 30000,
                    refresh_days: int = 30, now: str = "") -> dict:
    """The licence GitHub reports for each public repository, read in batches through gh's GraphQL interface.

    The query is built only from owner and name pairs that match GitHub's naming rules, reads two fields and
    changes nothing. Results are cached in the state folder and read again after refresh_days.
    """
    import re
    now = now or utc_now()
    cache_path = state.folder / "licences.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    pattern = re.compile(r"^github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})$")
    stale_before = (_parse_time(now) - timedelta(days=refresh_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    wanted = []
    for repository in sorted(set(repositories)):
        match = pattern.match(repository)
        if match and (repository not in cache or cache[repository].get("checked_at", "") < stale_before):
            wanted.append((repository, match.group(1), match.group(2)))
    wanted = wanted[:maximum]
    runner = runner or _gh_graphql
    asked = answered = 0
    for start in range(0, len(wanted), batch):
        chunk = wanted[start:start + batch]
        parts = [f'r{index}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {LICENCE_QUERY_FIELDS} }}'
                 for index, (_repository, owner, name) in enumerate(chunk)]
        data = runner("query { " + " ".join(parts) + " }")
        if not data:
            break
        asked += len(chunk)
        for index, (repository, _owner, _name) in enumerate(chunk):
            node = (data or {}).get(f"r{index}")
            if node is None:
                cache[repository] = {"spdx": "", "archived": False, "found": False, "checked_at": now}
                continue
            spdx = ((node.get("licenseInfo") or {}).get("spdxId") or "")
            cache[repository] = {"spdx": "" if spdx == "NOASSERTION" else spdx, "archived": bool(node.get("isArchived")),
                                 "found": True, "checked_at": now}
            answered += 1
        write_atomic(cache_path, json.dumps(cache, indent=0, sort_keys=True) + "\n")
    return {"asked": asked, "answered": answered, "cached": len(cache)}


def _gh_graphql(query: str) -> dict:
    """One read-only GraphQL query through the gh login; the token never passes through this process's arguments."""
    completed = subprocess.run(("gh", "api", "graphql", "-f", "query=" + query), capture_output=True, text=True,
                               timeout=120, check=False)
    value = json.loads(completed.stdout or "{}")
    return value.get("data") or {}


def licence_cache(state: DirectoryState) -> dict:
    path = state.folder / "licences.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
