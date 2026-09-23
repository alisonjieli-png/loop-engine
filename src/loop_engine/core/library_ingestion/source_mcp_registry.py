"""Engine mcp_official_registry of the library_ingestion_source engine slot, in link mode.

It pages through the official Model Context Protocol registry's list of
latest server versions, keeps each page's exact bytes and each entry's
canonical bytes in quarantine, and returns one candidate per active, latest
entry. An entry is link-only: Baltor later writes the harness connection
files from its facts, and the author's text is never copied. The licence
evidence of a link-only entry records the licence of the upstream code
repository when the entry names a GitHub repository and a GitHub reader is
supplied; otherwise the licence stays unknown, never assumed. A status other
than active, an entry that is not the latest, and a declared copy are
refused by name. The last page marks the snapshot complete; a ceiling stops
it with the registry cursor to resume from.
"""
from __future__ import annotations

import base64
import json
import re

from .candidates import TOOL, candidate_batch, read_candidate_request, refusal, source_candidate
from .https_transport import quote_part, split_address
from .licences import match_licence
from .provenance import (
    LICENCE_EVIDENCE_RECORD_TYPE, LINK_ONLY, NO_ASSERTION, NO_LICENCE, ORIGIN_HOSTS, REGISTRY_ORIGIN,
    OutsideSourceProvenance)
from .record_rules import LibraryRecordError, bytes_digest, canonical_json, git_blob_identity, now_utc
from .request_log import PauseExceedsBound, RequestCeilingReached
from .source_declarations import read_registry_source

REGISTRY_LIST_PATH = "/v0.1/servers"
OFFICIAL_META = "io.modelcontextprotocol.registry/official"
ACTIVE = "active"
_GITHUB_REPOSITORY = re.compile(r"/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9._-]{1,100}?)(?:\.git)?/?\Z")


def entry_bytes(entry: dict) -> bytes:
    """The canonical bytes of one entry: the digest a provenance record names."""
    return canonical_json(entry).encode("utf-8")


def upstream_github_repository(server: dict) -> "str | None":
    url = str(((server.get("repository") or {}).get("url")) or "")
    parts = split_address(url)
    if parts.hostname != "github.com":
        return None
    match = _GITHUB_REPOSITORY.match(parts.path)
    return f"{match.group(1)}/{match.group(2)}" if match else None


class McpOfficialRegistrySource:
    """Reads the registry's latest entries and answers with library_candidate_batch/v1."""

    engine_id = "mcp_official_registry"
    engine_version = "1.0.0"
    engine_kind = "registry_link_reader"
    effects = ("network",)
    third_party = "official Model Context Protocol registry, list interface v0.1"

    def __init__(self, transport, quarantine, *, github_reader=None, page_size: int = 100,
                 maximum_upstream_lookups: int = 0) -> None:
        self.transport, self.quarantine = transport, quarantine
        self.github_reader, self.page_size = github_reader, page_size
        self.maximum_upstream_lookups = maximum_upstream_lookups
        self.upstream: dict = {}

    @classmethod
    def availability(cls, settings: dict):
        if settings.get("network_reads_authorized") is not True:
            return False, "authority_missing"
        if not settings.get("registry_transport_configured"):
            return False, "not_configured"
        return True, "available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls(resources["registry_transport"], resources["quarantine"],
                   github_reader=resources.get("github_reader"),
                   maximum_upstream_lookups=int(settings.get("upstream_licence_lookups") or 0))

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "engine_kind": self.engine_kind, "effects": list(self.effects),
                "page_size": self.page_size, "maximum_upstream_lookups": self.maximum_upstream_lookups,
                "third_party": self.third_party}

    def read_candidates(self, declaration: dict, request: dict) -> dict:
        declaration = read_registry_source(declaration)
        request = read_candidate_request(request)
        if request["network_reads_authorized"] is not True:
            raise PermissionError("reading the registry needs explicit network read authority")
        candidates, refusals = [], []
        state = {"cursor": request["cursor"], "seen": 0, "requests": 0}
        budget = self.transport.budget
        before = budget.used
        limit = min(declaration["maximum_entries"], request["maximum_candidates"])

        def finish(complete, reason):
            return candidate_batch(request, self, complete=complete,
                                   next_cursor=None if complete else state["cursor"],
                                   stopped_reason=reason, candidates=candidates, refusals=refusals,
                                   requests_made=budget.used - before)

        try:
            while True:
                query = {"version": "latest", "limit": str(self.page_size)}
                if state["cursor"]:
                    query["cursor"] = state["cursor"]
                response = self.transport.get(declaration["host"], REGISTRY_LIST_PATH, query)
                if response.status != 200:
                    refusals.append(refusal("registry", "entry_unreadable",
                                            f"list page answered status {response.status}"))
                    return finish(False, "source_refused")
                page_digest = self.quarantine.put(response.body).digest
                request_digest = self.transport.log.records[-1]["request_digest"]
                try:
                    page = json.loads(response.body)
                    entries = list(page["servers"])
                    next_cursor = (page.get("metadata") or {}).get("nextCursor")
                except (ValueError, KeyError, TypeError):
                    refusals.append(refusal("registry", "entry_unreadable", "a list page is not the "
                                                                            "documented shape"))
                    return finish(False, "source_refused")
                for entry in entries:
                    if state["seen"] >= limit:
                        return finish(False, "candidate_ceiling")
                    self._read_entry(declaration, entry, page_digest, request_digest, candidates, refusals)
                    state["seen"] += 1
                    server = entry.get("server") if isinstance(entry, dict) else None
                    if isinstance(server, dict) and server.get("name") and server.get("version"):
                        state["cursor"] = f"{server['name']}:{server['version']}"
                if not next_cursor:
                    return finish(True, "complete")
                state["cursor"] = next_cursor
        except RequestCeilingReached:
            return finish(False, "request_ceiling")
        except PauseExceedsBound:
            return finish(False, "rate_limit_pause_exceeds_bound")

    def _read_entry(self, declaration, entry, page_digest, request_digest, candidates, refusals) -> None:
        try:
            server = entry["server"]
            meta = entry["_meta"][OFFICIAL_META]
            name, version = str(server["name"]), str(server["version"])
            published = str(meta["publishedAt"])
        except (KeyError, TypeError):
            refusals.append(refusal("registry", "entry_unreadable", "an entry lacks its name, version "
                                                                   "or official metadata"))
            return
        ref = {"origin": REGISTRY_ORIGIN, "repository": name[:512],
               "immutable_revision": f"version:{version};published:{published}"[:512],
               "path": f"v0.1/servers/{quote_part(name)}/versions/{quote_part(version)}"[:512]}
        if any(name.startswith(prefix) for prefix in declaration["exclude_name_prefixes"]):
            refusals.append(refusal("registry", "excluded_by_declaration",
                                    "a declared copy of another registry entry", source=ref))
            return
        if meta.get("status") != ACTIVE:
            refusals.append(refusal("registry", "registry_status_not_active",
                                    f"status {meta.get('status')}", source=ref))
            return
        if meta.get("isLatest") is not True:
            refusals.append(refusal("registry", "registry_entry_not_latest", version, source=ref))
            return
        evidence = self._link_evidence(server)
        if evidence is None:
            refusals.append(refusal("registry", "upstream_repository_unreadable",
                                    "the entry names a GitHub repository that does not answer", source=ref))
            return
        data = entry_bytes(entry)
        stored = self.quarantine.put(data)
        try:
            provenance = OutsideSourceProvenance(
                REGISTRY_ORIGIN, ORIGIN_HOSTS[REGISTRY_ORIGIN], name, ref["immutable_revision"],
                ref["path"], stored.digest, stored.size_bytes, None, page_digest, evidence, now_utc(),
                request_digest)
            candidates.append(source_candidate(TOOL, "mcp_server_entry", name, provenance))
        except LibraryRecordError as error:
            refusals.append(refusal("registry", "server_name_unusable", error.code, source=ref))

    def _link_evidence(self, server: dict) -> "dict | None":
        """The upstream code repository's licence, read only when a GitHub reader is supplied.

        None means the entry names a GitHub repository that does not answer at all.
        """
        repository = upstream_github_repository(server)
        spdx, reason, part = NO_ASSERTION, "upstream_licence_not_checked", None
        if repository is None:
            reason = "upstream_repository_not_on_github"
        elif self.github_reader is not None and (repository in self.upstream
                                                 or len(self.upstream) < self.maximum_upstream_lookups):
            if repository not in self.upstream:
                try:
                    self.upstream[repository] = self._upstream_licence(repository)
                except RequestCeilingReached:
                    # The GitHub allowance of this run is spent; the listing goes on and
                    # every later entry keeps its upstream licence unknown.
                    self.maximum_upstream_lookups = len(self.upstream)
                    self.upstream[repository] = (NO_ASSERTION, "upstream_licence_not_checked", None)
            if self.upstream[repository] is None:
                return None
            spdx, reason, part = self.upstream[repository]
        return {"record_type": LICENCE_EVIDENCE_RECORD_TYPE, "spdx_expression": spdx, "decision": LINK_ONLY,
                "reason": reason, "detector": "GitHub licence interface for the upstream code repository",
                "repository_licence": part, "governing_file": None, "file_level_notices": []}

    def _upstream_licence(self, repository: str):
        response = self.github_reader.get(f"repos/{repository}/license")
        if response.status == 404:
            if self.github_reader.get(f"repos/{repository}").status == 404:
                return None
            return NO_LICENCE, "upstream_repository_has_no_licence_file", None
        if response.status != 200:
            return NO_ASSERTION, f"upstream_licence_status_{response.status}", None
        try:
            answer = json.loads(response.body)
            data = base64.b64decode(answer.get("content", ""))
        except (ValueError, TypeError):
            return NO_ASSERTION, "upstream_licence_unreadable", None
        if git_blob_identity(data) != answer.get("sha") or not answer.get("path"):
            return NO_ASSERTION, "upstream_licence_unreadable", None
        github = (answer.get("license") or {}).get("spdx_id") or NO_ASSERTION
        matched = match_licence(data.decode("utf-8", "replace"))
        part = {"path": answer["path"], "sha256": bytes_digest(data), "github_spdx_id": github,
                "matched_spdx": matched.spdx, "similarity": matched.similarity}
        return (github if github != "NOASSERTION" else NO_ASSERTION), "upstream_repository_licence", part
