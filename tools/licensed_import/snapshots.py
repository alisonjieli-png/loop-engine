"""The repository snapshot edge: one repository at one commit, its tree and the bytes asked for.

`licensed_import_snapshot/v1` is one fixed edge with two engines behind it,
selected by declared order:

```text
Repository snapshot (functional component)
├── Edge: open(repository, revision) -> tree at an exact commit; read(oids) -> verified bytes
├── git_partial_clone (initial choice)
│   ├── a shallow fetch of one commit with no blobs: the commit and its trees only
│   ├── the tree is listed without sizes, so no blob is fetched to list it
│   ├── the selected blobs arrive in one batched fetch by object identity
│   └── no GitHub API allowance is spent; git runs with no user configuration
└── github_api_blobs (fallback)
    ├── the tree through the REST interface, one request a repository
    └── blob text through GraphQL, up to 100 a request; a binary, truncated or
        mismatched blob is read through the REST contents interface instead
```

Every byte handed back is proven to be the object the tree names: git
checks its own objects, and the API engine recomputes each blob's git
identity. A truncated tree, a tree above the entry ceiling, a missing
object or a fetch that failed is reported, never guessed around. Nothing is
checked out, so nothing is written as a working file, no symbolic link is
followed and nothing runs.
"""
from __future__ import annotations

import base64
import json
import secrets
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlunsplit

from loop_engine.core.library_ingestion.record_rules import git_blob_identity, now_utc

from .github_api import OID, blob_query
from .harness_kinds import BLOB_TYPE, TreeEntry
from .processes import GIT_SAFETY, git_environment, run

SNAPSHOT_EDGE = "licensed_import_snapshot/v1"
GIT_FETCH_RECORD_TYPE = "licensed_import_git_fetch/v1"
GIT_ENGINE, API_ENGINE = "git_partial_clone", "github_api_blobs"
ENGINE_ORDER = (GIT_ENGINE, API_ENGINE)
_OBJECT_BATCH = 2000


class SnapshotFailed(RuntimeError):
    """The engine could not produce an exact snapshot; the reason is a closed code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class Snapshot:
    """One repository at one exact commit: its tree entries and the engine that read them."""

    repository: str
    commit: str
    entries: tuple
    engine_id: str
    fetched_at: str
    handle: object = None


def _github_address(repository: str) -> str:
    owner, _, name = repository.partition("/")
    return urlunsplit(("https", "github.com", f"/{quote(owner)}/{quote(name)}.git", "", ""))


def parse_ls_tree(output: bytes, maximum_entries: int) -> tuple:
    """Entries of `git ls-tree -r -z`: mode, type, object identity and path, NUL separated."""
    entries = []
    for record in output.split(b"\0"):
        if not record:
            continue
        head, _, path = record.partition(b"\t")
        fields = head.split(b" ")
        if len(fields) != 3 or not path:
            raise SnapshotFailed("tree_unreadable", "a tree line did not have its four parts")
        entries.append(TreeEntry(path.decode("utf-8", "surrogateescape"), fields[0].decode(),
                                 fields[1].decode(), fields[2].decode()))
        if len(entries) > maximum_entries:
            raise SnapshotFailed("tree_too_large", f"more than {maximum_entries} entries")
    return tuple(entries)


def parse_cat_file(output: bytes) -> dict:
    """Objects of `git cat-file --batch`: identity to bytes; a missing object is left out."""
    found, position = {}, 0
    while position < len(output):
        end = output.index(b"\n", position)
        header = output[position:end].split(b" ")
        position = end + 1
        if len(header) == 2 and header[1] == b"missing":
            continue
        if len(header) != 3:
            raise SnapshotFailed("object_unreadable", "an object header did not have three parts")
        size = int(header[2])
        found[header[0].decode()] = output[position:position + size]
        position += size + 1
    return found


class GitPartialClone:
    """Engine git_partial_clone: a blob-less shallow fetch, then only the blobs asked for."""

    engine_id = GIT_ENGINE
    engine_version = "1.0.0"
    effects = ("network", "writes_fs")

    def __init__(self, work_root: Path, *, maximum_entries: int = 200_000, fetch_timeout_seconds: float = 240.0,
                 maximum_bytes: int = 256 * 1024 * 1024, git: str = "git", log_path: "Path | None" = None) -> None:
        self.work_root = Path(work_root)
        self.maximum_entries, self.fetch_timeout_seconds = maximum_entries, fetch_timeout_seconds
        self.maximum_bytes, self.git, self.log_path = maximum_bytes, git, log_path
        self.records: list = []

    def _git(self, folder: Path, *arguments, timeout: float = 120.0, input_bytes: "bytes | None" = None,
             maximum: "int | None" = None):
        return run((self.git, *GIT_SAFETY, "-C", str(folder), *arguments), timeout_seconds=timeout,
                   maximum_output_bytes=maximum or self.maximum_bytes,
                   environment=git_environment(str(self.work_root)), input_bytes=input_bytes)

    def _record(self, repository: str, operation: str, result, objects: int, received: int) -> None:
        row = {"record_type": GIT_FETCH_RECORD_TYPE, "repository": repository, "operation": operation,
               "objects": objects, "bytes": received, "elapsed_ms": round(result.elapsed_ms, 1),
               "outcome": "ok" if result.exit_code == 0 else "timed_out" if result.timed_out else "failed",
               "at": now_utc()}
        self.records.append(row)
        if self.log_path is not None:
            with self.log_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")

    def open(self, repository: str, revision: "str | None" = None) -> Snapshot:
        if revision is not None and not OID.match(revision):
            raise SnapshotFailed("revision_invalid", "a pinned revision is a full commit identity")
        folder = self.work_root / f"{repository.replace('/', '__')}__{secrets.token_hex(4)}"
        folder.mkdir(parents=True, exist_ok=False)
        try:
            for arguments in (("init", "--quiet", "--bare"), ("remote", "add", "origin", _github_address(repository))):
                result = self._git(folder, *arguments)
                if result.exit_code != 0:
                    raise SnapshotFailed("fetch_failed", f"git {arguments[0]} failed")
            result = self._git(folder, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "--no-tags",
                               "--no-write-fetch-head", "origin", f"{revision or 'HEAD'}:refs/snapshot/head",
                               timeout=self.fetch_timeout_seconds)
            self._record(repository, "fetch_commit_and_trees", result, 0, _folder_bytes(folder))
            if result.exit_code != 0:
                raise SnapshotFailed("fetch_failed", result.stderr_tail[-160:])
            head = self._git(folder, "rev-parse", "--verify", "refs/snapshot/head^{commit}")
            commit = head.stdout.decode().strip()
            if head.exit_code != 0 or not OID.match(commit) or (revision is not None and commit != revision):
                raise SnapshotFailed("fetch_failed", "the fetched commit is not the one asked for")
            listing = self._git(folder, "ls-tree", "-r", "-z", "--full-tree", commit, timeout=180.0)
            if listing.exit_code != 0 or listing.truncated:
                raise SnapshotFailed("tree_too_large" if listing.truncated else "fetch_failed", "ls-tree failed")
            entries = parse_ls_tree(listing.stdout, self.maximum_entries)
            return Snapshot(repository, commit, entries, self.engine_id, now_utc(), folder)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise

    def read(self, snapshot: Snapshot, oids) -> dict:
        """The exact bytes of the named blobs, fetched in batches; git verifies every object."""
        wanted = sorted({oid for oid in oids if OID.match(oid)})
        found = {}
        folder = snapshot.handle
        for start in range(0, len(wanted), _OBJECT_BATCH):
            chunk = wanted[start:start + _OBJECT_BATCH]
            before = _folder_bytes(folder)
            result = self._git(folder, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "--quiet", "--no-tags",
                               "--no-write-fetch-head", "--recurse-submodules=no", "--filter=blob:none",
                               "--stdin", "origin", timeout=self.fetch_timeout_seconds,
                               input_bytes=("\n".join(chunk) + "\n").encode())
            self._record(snapshot.repository, "fetch_blobs", result, len(chunk), _folder_bytes(folder) - before)
            if result.exit_code != 0:
                raise SnapshotFailed("blob_fetch_incomplete", result.stderr_tail[-160:])
            objects = self._git(folder, "cat-file", "--batch", timeout=180.0,
                                input_bytes=("\n".join(chunk) + "\n").encode())
            if objects.exit_code != 0 or objects.truncated:
                raise SnapshotFailed("blob_fetch_incomplete", "cat-file failed or its output was too large")
            found.update(parse_cat_file(objects.stdout))
        return found

    def close(self, snapshot: Snapshot) -> None:
        if snapshot.handle is not None:
            shutil.rmtree(snapshot.handle, ignore_errors=True)


def _folder_bytes(folder: Path) -> int:
    return sum(path.stat().st_size for path in Path(folder).rglob("*") if path.is_file())


class GitHubApiBlobs:
    """Engine github_api_blobs: the REST tree, GraphQL blob text, REST contents for the rest."""

    engine_id = API_ENGINE
    engine_version = "1.0.0"
    effects = ("network",)

    def __init__(self, rest_reader, api, *, maximum_entries: int = 200_000) -> None:
        self.rest, self.api, self.maximum_entries = rest_reader, api, maximum_entries

    def open(self, repository: str, revision: str) -> Snapshot:
        if revision is None or not OID.match(revision):
            raise SnapshotFailed("revision_invalid", "the API engine reads an exact commit only")
        response = self.rest.get(f"repos/{repository}/git/trees/{revision}?recursive=1")
        if response.status != 200:
            raise SnapshotFailed("fetch_failed", f"tree status {response.status}")
        tree = json.loads(response.body)
        if tree.get("truncated"):
            raise SnapshotFailed("tree_too_large", "GitHub truncated the tree")
        entries = tuple(TreeEntry(row["path"], row["mode"], row["type"], row["sha"]) for row in tree.get("tree", ()))
        if len(entries) > self.maximum_entries:
            raise SnapshotFailed("tree_too_large", f"more than {self.maximum_entries} entries")
        return Snapshot(repository, revision, entries, self.engine_id, now_utc(), None)

    def read(self, snapshot: Snapshot, oids) -> dict:
        wanted = sorted({oid for oid in oids if OID.match(oid)})
        found, rest = {}, []
        for start in range(0, len(wanted), 100):
            chunk = wanted[start:start + 100]
            answer = self.api.graphql(blob_query(snapshot.repository, chunk))
            data = ((answer.get("body") or {}).get("data") or {}).get("r") or {}
            for index, oid in enumerate(chunk):
                blob = data.get(f"b{index}") or {}
                text = blob.get("text")
                if blob.get("isBinary") or blob.get("isTruncated") or text is None:
                    rest.append(oid)
                    continue
                payload = text.encode("utf-8")
                if git_blob_identity(payload) == oid:
                    found[oid] = payload
                else:
                    rest.append(oid)
        by_oid = {entry.oid: entry.path for entry in snapshot.entries if entry.object_type == BLOB_TYPE}
        for oid in rest:
            path = by_oid.get(oid)
            if path is None:
                continue
            response = self.rest.get(f"repos/{snapshot.repository}/contents/{quote(path)}?ref={snapshot.commit}")
            if response.status != 200:
                continue
            payload = base64.b64decode(json.loads(response.body).get("content") or "")
            if git_blob_identity(payload) == oid:
                found[oid] = payload
        return found

    def close(self, snapshot: Snapshot) -> None:
        return None


def verify_bytes(found: dict) -> dict:
    """Keep only bytes whose git identity is the identity they were read under."""
    return {oid: payload for oid, payload in found.items() if git_blob_identity(payload) == oid}


def wall_clock() -> float:
    return time.monotonic()
