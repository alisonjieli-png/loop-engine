"""Engine github_pinned_repositories of the library_ingestion_source engine slot.

It reads one curated repository at one exact commit through GitHub's
versioned contents interface. It lists the tree once and refuses a
truncated tree rather than guessing, selects the declared paths whose file
name is a native harness format, refuses symbolic links and submodules,
reads the repository licence through GitHub's licence interface and every
nested licence and notice file that could govern a selected file (one that
cannot be read lowers every item it covers to an outline, never to the
licence above it), checks each file's bytes against the blob identity in
the tree, places the bytes in quarantine and returns typed candidates, each
with its provenance and licence evidence. A request ceiling or an allowance wait beyond its bound
stops the source cleanly with a cursor to resume from. It executes nothing.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import PurePosixPath

from .candidates import (
    INSTRUCTION_FILE, SKILL, candidate_batch, read_candidate_request, refusal, source_candidate)
from .https_transport import quote_part
from .licences import LicenceFile, cap_to_outline, decide_licence, is_licence_file, is_notice_file
from .provenance import GITHUB_ORIGIN, ORIGIN_HOSTS, OutsideSourceProvenance
from .record_rules import bytes_digest, git_blob_identity, now_utc
from .request_log import PauseExceedsBound, RequestCeilingReached
from .source_declarations import read_github_source, selected

#: File names that are native harness formats, and what each one is.
NATIVE_FILES = (
    (re.compile(r"skill\.md\Z", re.I), SKILL, "agent_skill"),
    (re.compile(r"[^/]+\.instructions\.md\Z", re.I), INSTRUCTION_FILE, "copilot_instructions"),
    (re.compile(r"[^/]+\.mdc\Z"), INSTRUCTION_FILE, "cursor_rules"),
)
_SYMLINK_MODE, _SUBMODULE_TYPE = "120000", "commit"
#: The curated use that allows outlines only.
OUTLINE_USE = "outline"
#: Why a verbatim decision was lowered to an outline: a licence or notice file that could
#: govern or qualify the item is in the tree, but its bytes could not be read.
LICENCE_FILE_UNREADABLE = "licence_or_notice_file_unreadable"
_SPDX_HEADER = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+(?: (?:AND|OR|WITH) [A-Za-z0-9.+-]+)*)")


def native_format(path: str):
    name = PurePosixPath(path).name
    for pattern, kind, native in NATIVE_FILES:
        if pattern.match(name):
            return kind, native
    return None


def item_name(path: str, native: str, repository: str = "") -> str:
    """A skill is named by its folder (by its repository at the root); a rule file by its stem."""
    location = PurePosixPath(path)
    if native == "copilot_instructions":
        return location.name[: -len(".instructions.md")] or location.name
    if native == "cursor_rules":
        stem = location.name[: -len(".mdc")]
        return stem[: -len("-cursorrules-prompt-file")] if stem.endswith("-cursorrules-prompt-file") else stem
    return location.parent.name or repository.rsplit("/", 1)[-1] or location.name


def frontmatter_licence(text: str) -> "str | None":
    """The licence a file's own frontmatter names, if it names one."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    import yaml

    try:
        values = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    if isinstance(values, dict) and values.get("license") not in (None, ""):
        return str(values["license"])[:512]
    return None


def spdx_headers(text: str) -> tuple:
    return tuple(match.group(1) for match in _SPDX_HEADER.finditer("\n".join(text.splitlines()[:30])))


def applies_to_folder(path: str, folder: str) -> bool:
    """True when a licence or notice file sits in the item's folder or in a folder above it."""
    parent = str(PurePosixPath(path).parent)
    return folder == parent or parent == "." or folder.startswith(parent + "/")


class GitHubPinnedRepositoriesSource:
    """Reads one pinned repository and answers with library_candidate_batch/v1."""

    engine_id = "github_pinned_repositories"
    engine_version = "1.0.0"
    engine_kind = "pinned_repository_reader"
    effects = ("network",)
    third_party = ("gh command line, the owner's existing login, GitHub REST contents, git trees "
                   "and licence interfaces")

    def __init__(self, reader, quarantine, *, maximum_file_bytes: int = 262_144, blob_cache=None) -> None:
        self.reader, self.quarantine = reader, quarantine
        self.maximum_file_bytes = maximum_file_bytes
        self.blob_cache = blob_cache

    @classmethod
    def availability(cls, settings: dict):
        if settings.get("network_reads_authorized") is not True:
            return False, "authority_missing"
        if not settings.get("github_reader_configured"):
            return False, "not_configured"
        return True, "available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls(resources["github_reader"], resources["quarantine"], blob_cache=resources.get("blob_cache"))

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "engine_kind": self.engine_kind, "effects": list(self.effects),
                "maximum_file_bytes": self.maximum_file_bytes, "third_party": self.third_party}

    def _json(self, path: str):
        response = self.reader.get(path)
        if response.status != 200:
            return response.status, None
        try:
            return 200, json.loads(response.body)
        except ValueError:
            return None, None

    def read_candidates(self, declaration: dict, request: dict) -> dict:
        declaration = read_github_source(declaration)
        request = read_candidate_request(request)
        if request["network_reads_authorized"] is not True:
            raise PermissionError("reading a repository needs explicit network read authority")
        repository, commit = declaration["repository"], declaration["commit"]
        candidates, refusals, state = [], [], {"cursor": request["cursor"]}
        before = self.reader.budget.used

        def finish(complete, reason):
            return candidate_batch(request, self, complete=complete, next_cursor=None if complete
                                   else state["cursor"], stopped_reason=reason, candidates=candidates,
                                   refusals=refusals, requests_made=self.reader.budget.used - before)

        try:
            status, tree = self._json(f"repos/{repository}/git/trees/{commit}?recursive=1")
            if tree is None:
                refusals.append(refusal("discovery", "source_revision_unreadable",
                                        f"{repository} at {commit[:12]}: status {status}"))
                return finish(False, "source_refused")
            if tree.get("truncated"):
                refusals.append(refusal("discovery", "tree_truncated",
                                        f"{repository} at {commit[:12]} lists more than one answer holds"))
                return finish(False, "source_refused")
            blobs = {row["path"]: row for row in tree["tree"] if row.get("type") == "blob"
                     and row.get("mode") != _SYMLINK_MODE}
            chosen = []
            for row in sorted(tree["tree"], key=lambda item: item["path"]):
                path = row["path"]
                if not selected(path, declaration["include"], declaration["exclude"]) \
                        or (state["cursor"] and path <= state["cursor"]):
                    continue
                ref = {"origin": GITHUB_ORIGIN, "repository": repository, "immutable_revision": commit,
                       "path": path}
                if row.get("mode") == _SYMLINK_MODE:
                    refusals.append(refusal("discovery", "symlink_not_imported", path, source=ref))
                elif row.get("type") == _SUBMODULE_TYPE:
                    refusals.append(refusal("discovery", "submodule_not_imported", path, source=ref))
                elif row.get("type") == "blob" and native_format(path):
                    chosen.append(path)
            more = len(chosen) > request["maximum_candidates"]
            chosen = chosen[:request["maximum_candidates"]]
            licences = self._licence_files(repository, commit, blobs, chosen, declaration, refusals)
            if licences is None:
                return finish(False, "source_refused")
            licence_files, root_path, notices, unreadable = licences
            for path in chosen:
                self._read_item(declaration, path, blobs[path], blobs, licence_files, root_path, notices,
                                unreadable, candidates, refusals)
                state["cursor"] = path
        except RequestCeilingReached:
            return finish(False, "request_ceiling")
        except PauseExceedsBound:
            return finish(False, "rate_limit_pause_exceeds_bound")
        return finish(False, "candidate_ceiling") if more else finish(True, "complete")

    def _licence_files(self, repository, commit, blobs, chosen, declaration, refusals):
        """Read the repository licence and every licence or notice file above a chosen path.

        A licence or notice file whose bytes cannot be read is returned by path, so
        the items it could govern are never decided as if their folder held none.
        """
        files, root_path, notices, unreadable = {}, None, [], []
        status, answer = self._json(f"repos/{repository}/license?ref={commit}")
        if answer is not None:
            data = base64.b64decode(answer.get("content", ""))
            # The answer counts only when its bytes are the very blob the pinned tree holds
            # at that path; an answer about another revision is never read as this one's.
            tree_blob = blobs.get(answer.get("path")) or {}
            if git_blob_identity(data) == answer.get("sha") == tree_blob.get("sha"):
                self.quarantine.put(data)
                root_path = answer["path"]
                spdx = (answer.get("license") or {}).get("spdx_id")
                files[root_path] = LicenceFile(root_path, bytes_digest(data),
                                               data.decode("utf-8", "replace"), spdx)
        expected = declaration["expected_licence"]
        if expected is not None and (root_path is None or files[root_path].github_spdx_id != expected):
            found = files[root_path].github_spdx_id if root_path else "none"
            refusals.append(refusal("discovery", "curated_licence_changed",
                                    f"curation verified {expected} and the licence interface now reports "
                                    f"{found} at {commit[:12]}"))
            return None
        folders = {str(PurePosixPath(path).parent) for path in chosen}
        wanted = set()
        for folder in folders:
            current = PurePosixPath(folder)
            while True:
                wanted.add(str(current))
                if str(current) in (".", ""):
                    break
                current = current.parent
        for path in sorted(blobs):
            folder = str(PurePosixPath(path).parent)
            if folder not in wanted or path == root_path:
                continue
            if is_licence_file(path) or is_notice_file(path):
                data = self._contents(repository, commit, path, blobs[path])
                if data is None:
                    unreadable.append(path)
                    continue
                self.quarantine.put(data)
                if is_licence_file(path):
                    files[path] = LicenceFile(path, bytes_digest(data), data.decode("utf-8", "replace"))
                else:
                    notices.append((path, bytes_digest(data)))
        return files, root_path, notices, unreadable

    def _contents(self, repository, commit, path, blob) -> "bytes | None":
        if self.blob_cache is not None:
            cached = self.blob_cache.blob(blob["sha"])
            if cached is not None:
                return cached
        status, answer = self._json(f"repos/{repository}/contents/{quote_part(path, safe='/')}?ref={commit}")
        if answer is None or answer.get("encoding") != "base64":
            return None
        data = base64.b64decode(answer.get("content", ""))
        if git_blob_identity(data) != blob["sha"]:
            return None
        return data

    def _read_item(self, declaration, path, blob, blobs, licence_files, root_path, notices, unreadable,
                   candidates, refusals) -> None:
        repository, commit = declaration["repository"], declaration["commit"]
        ref = {"origin": GITHUB_ORIGIN, "repository": repository, "immutable_revision": commit, "path": path}
        if int(blob.get("size") or 0) > self.maximum_file_bytes:
            refusals.append(refusal("fetch", "source_file_too_large",
                                    f"{blob.get('size')} bytes, above {self.maximum_file_bytes}", source=ref))
            return
        cached = self.blob_cache.item(repository, commit, path, blob["sha"]) if self.blob_cache else None
        if cached is not None:
            # The earlier fetch's own facts travel with its bytes, so the provenance stays exact.
            data, facts = cached
            fetch_digest, request_digest, fetched_at = (facts["fetch_digest"], facts["request_digest"],
                                                        facts["fetched_at"])
        else:
            status, answer = self._json(f"repos/{repository}/contents/{quote_part(path, safe='/')}?ref={commit}")
            if answer is None or answer.get("encoding") != "base64":
                reason = "source_file_too_large" if answer is not None else "fetch_failed"
                refusals.append(refusal("fetch", reason, f"status {status}", source=ref))
                return
            request_row = self.reader.log.records[-1]
            fetch_digest, request_digest, fetched_at = (request_row["body_digest"], request_row["request_digest"],
                                                        now_utc())
            data = base64.b64decode(answer.get("content", ""))
        if git_blob_identity(data) != blob["sha"]:
            refusals.append(refusal("fetch", "blob_identity_mismatch",
                                    "the fetched bytes are not the blob the tree names", source=ref))
            return
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            refusals.append(refusal("fetch", "not_utf8_text", path, source=ref))
            return
        entry = self.quarantine.put(data)
        kind, native = native_format(path)
        folder = str(PurePosixPath(path).parent)
        folder_notices = [(notice_path, digest) for notice_path, digest in notices
                          if applies_to_folder(notice_path, folder)]
        evidence = decide_licence(path, licence_files, root_path=root_path,
                                  frontmatter_licence=frontmatter_licence(text) if kind == SKILL else None,
                                  item_sha256=entry.digest, spdx_headers=spdx_headers(text),
                                  notice_files=folder_notices)
        if any(applies_to_folder(other, folder) for other in unreadable):
            evidence = cap_to_outline(evidence, LICENCE_FILE_UNREADABLE)
        if declaration["use"] == OUTLINE_USE:
            evidence = cap_to_outline(evidence)
        provenance = OutsideSourceProvenance(
            GITHUB_ORIGIN, ORIGIN_HOSTS[GITHUB_ORIGIN], repository, commit, path, entry.digest,
            entry.size_bytes, blob["sha"], fetch_digest, evidence, fetched_at, request_digest)
        scope, package = "", ()
        if kind == SKILL and folder not in (".", ""):
            scope = folder
            package = tuple(other[len(folder) + 1:] for other in blobs
                            if other.startswith(folder + "/") and other != path)
        elif kind == SKILL:
            package = tuple(other for other in blobs if other != path)
        candidates.append(source_candidate(kind, native, item_name(path, native, repository), provenance,
                                           scope, package))
