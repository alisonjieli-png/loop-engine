"""Known-wrong checks for the two source engines and their transports, offline.

The engines run against recorded fake transports, so no check reaches a
network. The checks require: the GitHub reader refuses anything but an
allowed read before a process starts; a file whose bytes differ from its
tree blob, a symbolic link, a submodule and a truncated tree are refused by
name; a request ceiling stops cleanly with a cursor that resumes without a
gap; a low allowance pauses within a declared bound and a longer wait stops
the run; the registry reader keeps only active latest entries, marks a
snapshot complete only at its last page, and a status change or a vanished
entry in a complete snapshot withdraws the item while an incomplete one
infers nothing; an incremental sync is reconciled with a full one; and no
request is sent without network authority.
"""
from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

from .candidates import candidate_request, read_candidate_batch
from .github_reader import GitHubResponse, ReadOnlyRequestRefused, allowed_request, parse_included_response
from .github_reader import GhCliReader
from .https_transport import HostNotDeclared, HttpsGetTransport, HttpsResponse
from .licence_checks import MIT_FIXTURE, PROPRIETARY_FIXTURE
from .fetch_cache import PinnedBlobCache
from .quarantine import Quarantine
from .record_rules import LibraryRecordError, bytes_digest, git_blob_identity
from .registry_sync import reconcile, snapshot_index, withdrawals
from .request_log import PauseExceedsBound, RequestBudget, RequestLog, RequestObservation
from .source_github import GitHubPinnedRepositoriesSource
from .source_mcp_registry import McpOfficialRegistrySource

COMMIT = "1111111111111111111111111111111111111111"
REPOSITORY = "example-owner/example-skills"


def skill_text(name: str, extra: str = "") -> str:
    return (f"---\nname: {name}\ndescription: Use when you need {name.replace('-', ' ')} done "
            f"carefully.{extra}\n---\n# {name}\n\n" + "Step one. Read the task and write down the goal. "
            * 12 + "\n")


class FakeGitHubReader:
    """Answers allowed reads from a table, through the same budget and log as the real reader."""

    transport = "gh_api"

    def __init__(self, table: dict, budget: RequestBudget, log: RequestLog, allowance=None) -> None:
        self.table, self.budget, self.log = table, budget, log
        self.allowance = list(allowance or [])

    def get(self, path: str) -> GitHubResponse:
        if not allowed_request(path):
            raise ReadOnlyRequestRefused(path)
        self.budget.admit()
        status, body = self.table.get(path, (404, b'{"message":"Not Found"}'))
        remaining, reset = self.allowance.pop(0) if self.allowance else (4000, 0)
        self.log.record(RequestObservation("gh_api", "api.github.com", path, status, body,
                                           "2026-09-22T12:00:00Z", 1.0,
                                           "ok" if status == 200 else "not_found",
                                           allowance_remaining=remaining))
        self.budget.respect_allowance(remaining, reset, "GitHub")
        return GitHubResponse(status, body, remaining, reset)


def _contents(data: bytes, sha: "str | None" = None) -> bytes:
    return json.dumps({"type": "file", "encoding": "base64", "size": len(data),
                       "sha": sha or git_blob_identity(data),
                       "content": base64.b64encode(data).decode()}).encode()


def repository_table(files: dict, *, truncated: bool = False, links=(), submodules=(),
                     wrong_bytes=()) -> dict:
    """A tree at COMMIT holding the given files, plus contents and licence answers."""
    tree = [{"path": path, "mode": "100644", "type": "blob", "sha": git_blob_identity(data),
             "size": len(data)} for path, data in files.items()]
    tree += [{"path": path, "mode": "120000", "type": "blob", "sha": "2" * 40} for path in links]
    tree += [{"path": path, "mode": "160000", "type": "commit", "sha": "3" * 40} for path in submodules]
    table = {f"repos/{REPOSITORY}/git/trees/{COMMIT}?recursive=1":
             (200, json.dumps({"sha": COMMIT, "tree": tree, "truncated": truncated}).encode())}
    for path, data in files.items():
        served = b"tampered bytes" if path in wrong_bytes else data
        table[f"repos/{REPOSITORY}/contents/{path}?ref={COMMIT}"] = (
            200, _contents(served, git_blob_identity(served)))
    if "LICENSE" in files:
        table[f"repos/{REPOSITORY}/license?ref={COMMIT}"] = (200, json.dumps({
            "path": "LICENSE", "sha": git_blob_identity(files["LICENSE"]),
            "content": base64.b64encode(files["LICENSE"]).decode(),
            "license": {"spdx_id": "MIT"}}).encode())
    return table


def declaration(**overrides) -> dict:
    row = {"source_id": "github.example.skills", "engine": "github_pinned_repositories",
           "repository": REPOSITORY, "commit": COMMIT, "use": "verbatim",
           "content_origin": "first_party", "expected_licence": "MIT",
           "include": ["skills/*/SKILL.md"], "exclude": [], "note": "fixture"}
    row.update(overrides)
    return row


def _request(source_id="github.example.skills", **options) -> dict:
    return candidate_request(source_id, requested_at="2026-09-22T12:00:00Z",
                             network_reads_authorized=options.pop("network", True), **options)


def registry_entry(name: str, status: str = "active", latest: bool = True, version: str = "1.0.0") -> dict:
    return {"server": {"name": name, "description": "Author text that is never copied.",
                       "version": version, "remotes": [{"type": "streamable-http",
                                                        "url": f"https://{name.split('/')[-1]}.example/mcp"}]},
            "_meta": {"io.modelcontextprotocol.registry/official": {
                "status": status, "publishedAt": "2026-09-01T10:00:00.000001Z",
                "updatedAt": "2026-09-01T10:00:00.000001Z", "isLatest": latest}}}


class FakeRegistry:
    """Serves registry pages from a list, through the same budget and log as the real transport."""

    transport = "https_get"

    def __init__(self, pages, budget, log) -> None:
        self.pages, self.budget, self.log = list(pages), budget, log
        self.hosts = frozenset({"registry.modelcontextprotocol.io"})

    def get(self, host, path, query=None) -> HttpsResponse:
        if host not in self.hosts:
            raise HostNotDeclared(host)
        self.budget.admit()
        index = int((query or {}).get("cursor", "page-0").split("-")[1])
        entries = self.pages[index]
        metadata = {"count": len(entries)}
        if index + 1 < len(self.pages):
            metadata["nextCursor"] = f"page-{index + 1}"
        body = json.dumps({"servers": entries, "metadata": metadata}).encode()
        self.log.record(RequestObservation("https_get", host, path, 200, body, "2026-09-22T12:00:00Z", 1.0,
                                           "ok"))
        return HttpsResponse(200, body)


def _cache_checks(check, files) -> None:
    """A rerun takes a pinned blob from an earlier run only when the bytes are that very blob."""
    table = repository_table(files)
    with tempfile.TemporaryDirectory(prefix="library-cache-") as folder:
        earlier = Path(folder) / "earlier"
        first = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            table, RequestBudget(maximum_requests=50), RequestLog()), Quarantine(earlier / "quarantine")
        ).read_candidates(declaration(), _request())
        (earlier / "batches").mkdir()
        (earlier / "batches" / "github.example.skills.json").write_text(json.dumps(first), encoding="utf-8")
        cache = PinnedBlobCache.from_run_folders([earlier])
        log = RequestLog()
        second_quarantine = Quarantine(Path(folder) / "second")
        second = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            table, RequestBudget(maximum_requests=50), log), second_quarantine, blob_cache=cache
        ).read_candidates(declaration(), _request())
        fetched = [row["target"] for row in log.records if "/contents/" in row["target"]]
        check("a_rerun_reuses_verified_pinned_bytes_without_fetching_them_again",
              second["candidates"] == first["candidates"] and not fetched and cache.hits > 0
              and all(second_quarantine.has(row["provenance"]["source_digest"]) for row in second["candidates"]),
              (len(fetched), cache.hits))

        alpha = next(row for row in first["candidates"] if row["name"] == "alpha")
        digest = alpha["provenance"]["source_digest"]
        stored = earlier / "quarantine" / digest[:2] / digest
        stored.chmod(0o600)
        stored.write_bytes(b"bytes that are not the pinned blob any more")
        spoiled = PinnedBlobCache.from_run_folders([earlier])
        spoiled_log = RequestLog()
        third = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            table, RequestBudget(maximum_requests=50), spoiled_log), Quarantine(Path(folder) / "third"),
            blob_cache=spoiled).read_candidates(declaration(), _request())
        refetched = [row["target"] for row in spoiled_log.records if "/contents/" in row["target"]]
        # A fresh fetch has fresh fetch facts; the bytes, and so the candidate keys, are the same.
        check("a_cached_file_that_is_not_the_pinned_blob_is_fetched_again",
              [row["candidate_key"] for row in third["candidates"]]
              == [row["candidate_key"] for row in first["candidates"]]
              and any("skills/alpha/" in target for target in refetched) and spoiled.skipped == 1,
              (refetched, spoiled.skipped))


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:300]})

    with tempfile.TemporaryDirectory(prefix="library-sources-") as folder:
        quarantine = Quarantine(Path(folder) / "quarantine")

        refused = [path for path in (f"repos/{REPOSITORY}/contents/SKILL.md?ref=main",
                                     f"repos/{REPOSITORY}/contents/../secret?ref={COMMIT}",
                                     f"repos/{REPOSITORY}/issues", "user", "graphql",
                                     f"repos/{REPOSITORY}/git/trees/{COMMIT}?recursive=1&x=1")
                   if not allowed_request(path)]
        budget = RequestBudget(maximum_requests=5)
        reader = GhCliReader(budget, RequestLog(), gh="gh-that-is-never-started")
        try:
            reader.get(f"repos/{REPOSITORY}/pulls")
            started = True
        except ReadOnlyRequestRefused:
            started = False
        check("the_github_reader_refuses_anything_but_an_allowed_read_before_a_process_starts",
              len(refused) == 6 and not started and budget.used == 0
              and allowed_request(f"repos/{REPOSITORY}/contents/skills/a/SKILL.md?ref={COMMIT}"), refused)

        parsed = parse_included_response(b"HTTP/2.0 200 OK\nX-Oauth-Scopes: repo, delete_repo\n"
                                         b"X-Ratelimit-Remaining: 42\nX-Ratelimit-Reset: 99\n\n{\"a\": 1}")
        check("an_included_response_keeps_the_status_the_body_and_the_allowance_only",
              (parsed.status, parsed.body, parsed.allowance_remaining, parsed.allowance_reset)
              == (200, b'{"a": 1}', 42, 99) and "scope" not in repr(parsed).lower())

        files = {"LICENSE": MIT_FIXTURE.encode(),
                 "skills/alpha/SKILL.md": skill_text("alpha").encode(),
                 "skills/beta/SKILL.md": skill_text("beta").encode(),
                 "skills/beta/references/notes.md": b"# Notes\n",
                 "skills/closed/SKILL.md": skill_text("closed").encode(),
                 "skills/closed/LICENSE.txt": PROPRIETARY_FIXTURE.encode()}
        log = RequestLog()
        budget = RequestBudget(maximum_requests=50)
        engine = GitHubPinnedRepositoriesSource(
            FakeGitHubReader(repository_table(files, links=("skills/linked/SKILL.md",),
                                              submodules=("skills/vendored",)), budget, log), quarantine)
        batch = read_candidate_batch(engine.read_candidates(declaration(), _request()))
        decisions = {row["name"]: row["provenance"]["licence_evidence"]["decision"]
                     for row in batch["candidates"]}
        reasons = sorted(row["reason"] for row in batch["refusals"])
        beta = [row for row in batch["candidates"] if row["name"] == "beta"][0]
        check("a_pinned_repository_yields_candidates_with_provenance_and_licence_evidence",
              batch["complete"] and decisions == {"alpha": "verbatim_permitted", "beta": "verbatim_permitted",
                                                  "closed": "refused"}
              and reasons == ["symlink_not_imported"]
              and beta["package_paths"] == ["references/notes.md"]
              and all(quarantine.has(row["provenance"]["source_digest"]) for row in batch["candidates"]),
              (decisions, reasons))

        # A licence or notice file that cannot be read is still in the tree: the item beside it
        # must not fall back to the repository licence as if its folder held none.
        unreadable = repository_table({**files, "skills/alpha/NOTICE": b"Notices for alpha.\n"})
        unreadable[f"repos/{REPOSITORY}/contents/skills/closed/LICENSE.txt?ref={COMMIT}"] = (500, b"{}")
        unreadable[f"repos/{REPOSITORY}/contents/skills/alpha/NOTICE?ref={COMMIT}"] = (502, b"{}")
        unread = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            unreadable, RequestBudget(maximum_requests=50), RequestLog()), quarantine
        ).read_candidates(declaration(), _request())
        unread_evidence = {row["name"]: row["provenance"]["licence_evidence"] for row in unread["candidates"]}
        check("a_licence_or_notice_file_that_cannot_be_read_blocks_a_verbatim_copy",
              unread_evidence["closed"]["decision"] == "outline_only"
              and unread_evidence["alpha"]["decision"] == "outline_only"
              and unread_evidence["beta"]["decision"] == "verbatim_permitted",
              {name: (row["decision"], row["reason"]) for name, row in unread_evidence.items()})

        drifted = repository_table(files)
        other_licence = (MIT_FIXTURE + "\nA line the pinned commit does not hold.\n").encode()
        drifted[f"repos/{REPOSITORY}/license?ref={COMMIT}"] = (200, json.dumps({
            "path": "LICENSE", "sha": git_blob_identity(other_licence),
            "content": base64.b64encode(other_licence).decode(), "license": {"spdx_id": "MIT"}}).encode())
        drift_batch = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            drifted, RequestBudget(maximum_requests=50), RequestLog()), quarantine).read_candidates(
            declaration(), _request())
        check("a_licence_answer_that_is_not_the_blob_at_the_pinned_commit_is_not_trusted",
              not drift_batch["candidates"] and drift_batch["stopped_reason"] == "source_refused"
              and [row["reason"] for row in drift_batch["refusals"]] == ["curated_licence_changed"],
              [row["reason"] for row in drift_batch["refusals"]])

        outlined = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            repository_table(files), RequestBudget(maximum_requests=50), RequestLog()), quarantine
        ).read_candidates(declaration(use="outline", expected_licence=None), _request())
        outlined_decisions = {row["provenance"]["licence_evidence"]["decision"] for row in outlined["candidates"]}
        check("a_source_curated_for_outlines_never_yields_a_verbatim_candidate",
              outlined["candidates"] and outlined_decisions <= {"outline_only", "refused"}
              and "verbatim_permitted" not in outlined_decisions
              and {row["provenance"]["licence_evidence"]["reason"] for row in outlined["candidates"]
                   if row["provenance"]["licence_evidence"]["decision"] == "outline_only"}
              == {"source_curated_for_outlines"}, outlined_decisions)

        _cache_checks(check, files)

        submodule_batch = engine.read_candidates(declaration(include=["skills/**"]), _request())
        check("a_symbolic_link_and_a_submodule_are_never_imported",
              {"symlink_not_imported", "submodule_not_imported"}
              <= {row["reason"] for row in submodule_batch["refusals"]})

        tampered = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            repository_table(files, wrong_bytes=("skills/alpha/SKILL.md",)),
            RequestBudget(maximum_requests=50), RequestLog()), quarantine)
        tampered_batch = tampered.read_candidates(declaration(), _request())
        check("a_file_whose_bytes_differ_from_its_tree_blob_is_refused",
              "alpha" not in {row["name"] for row in tampered_batch["candidates"]}
              and "blob_identity_mismatch" in {row["reason"] for row in tampered_batch["refusals"]})

        truncated = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            repository_table(files, truncated=True), RequestBudget(maximum_requests=50), RequestLog()),
            quarantine).read_candidates(declaration(), _request())
        check("a_truncated_tree_stops_the_source_instead_of_guessing",
              not truncated["candidates"] and truncated["stopped_reason"] == "source_refused"
              and [row["reason"] for row in truncated["refusals"]] == ["tree_truncated"])

        table = repository_table(files)
        first = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            table, RequestBudget(maximum_requests=5), RequestLog()), quarantine).read_candidates(
            declaration(), _request())
        rest = GitHubPinnedRepositoriesSource(FakeGitHubReader(
            table, RequestBudget(maximum_requests=50), RequestLog()), quarantine).read_candidates(
            declaration(), _request(cursor=first["next_cursor"]))
        names = [row["name"] for row in first["candidates"]] + [row["name"] for row in rest["candidates"]]
        check("a_request_ceiling_stops_cleanly_and_the_cursor_resumes_without_a_gap",
              not first["complete"] and first["stopped_reason"] == "request_ceiling"
              and rest["complete"] and sorted(names) == ["alpha", "beta", "closed"]
              and len(names) == len(set(names)), (first["next_cursor"], names))

        clock, slept = [1000.0], []
        paced = RequestBudget(maximum_requests=50, maximum_pause_seconds=30, reserve=100,
                              sleep=slept.append, clock=lambda: clock[0])
        allowance = [(4000, 0), (50, 1010), (4000, 0), (40, 2000)]
        stopped = GitHubPinnedRepositoriesSource(FakeGitHubReader(table, paced, RequestLog(), allowance),
                                                 quarantine).read_candidates(declaration(), _request())
        check("a_low_allowance_pauses_within_its_bound_and_a_longer_wait_stops_the_run",
              slept == [11.0] and [row["taken"] for row in paced.pauses] == [True, False]
              and stopped["stopped_reason"] == "rate_limit_pause_exceeds_bound"
              and not stopped["complete"], (slept, paced.pauses))

        blocked = RequestBudget(maximum_requests=50)
        try:
            GitHubPinnedRepositoriesSource(FakeGitHubReader(table, blocked, RequestLog()),
                                           quarantine).read_candidates(declaration(), _request(network=False))
            sent_without_authority = True
        except PermissionError:
            sent_without_authority = False
        check("no_request_is_sent_without_network_authority",
              not sent_without_authority and blocked.used == 0)

        pages = [[registry_entry("io.github.one/alpha"), registry_entry("io.github.two/beta", "deprecated"),
                  registry_entry("ai.smithery/copy-of-alpha")],
                 [registry_entry("io.github.three/gamma", latest=False), registry_entry("io.github.four/delta")]]
        registry_log = RequestLog()
        registry = McpOfficialRegistrySource(FakeRegistry(pages, RequestBudget(maximum_requests=10),
                                                          registry_log), quarantine)
        registry_declaration = {"source_id": "registry.mcp.official", "engine": "mcp_official_registry",
                                "host": "registry.modelcontextprotocol.io", "use": "link",
                                "maximum_entries": 100, "exclude_name_prefixes": ["ai.smithery/"],
                                "note": "fixture"}
        registry_batch = read_candidate_batch(registry.read_candidates(
            registry_declaration, _request("registry.mcp.official")))
        kept = sorted(row["name"] for row in registry_batch["candidates"])
        refused_reasons = sorted(row["reason"] for row in registry_batch["refusals"])
        check("the_registry_reader_keeps_only_active_latest_entries",
              kept == ["io.github.four/delta", "io.github.one/alpha"]
              and refused_reasons == ["excluded_by_declaration", "registry_entry_not_latest",
                                      "registry_status_not_active"]
              and all(row["provenance"]["licence_evidence"]["decision"] == "link_only"
                      for row in registry_batch["candidates"]), (kept, refused_reasons))
        check("the_registry_snapshot_is_complete_only_after_its_last_page",
              registry_batch["complete"] and registry_batch["requests_made"] == 2
              and len(registry_log.records) == 2)

        partial = McpOfficialRegistrySource(FakeRegistry(pages, RequestBudget(maximum_requests=1),
                                                         RequestLog()), quarantine).read_candidates(
            registry_declaration, _request("registry.mcp.official"))
        before = snapshot_index([registry_entry("io.github.one/alpha"), registry_entry("io.github.two/beta"),
                                 registry_entry("io.github.five/epsilon")])
        now = snapshot_index([registry_entry("io.github.one/alpha"),
                              registry_entry("io.github.two/beta", "deprecated")])
        complete_changes = withdrawals(before, now, current_complete=True)
        partial_changes = withdrawals(before, now, current_complete=False)
        check("withdrawal_follows_the_source_and_an_incomplete_snapshot_infers_no_absence",
              not partial["complete"] and partial["next_cursor"] == "page-1"
              and [(row["name"], row["reason"]) for row in complete_changes]
              == [("io.github.five/epsilon", "vanished_from_complete_snapshot"),
                  ("io.github.two/beta", "status_changed")]
              and [(row["name"], row["reason"]) for row in partial_changes]
              == [("io.github.two/beta", "status_changed")], complete_changes)

        full = snapshot_index([registry_entry("io.github.one/alpha"), registry_entry("io.github.four/delta")])
        incremental = snapshot_index([registry_entry("io.github.one/alpha")])
        difference = reconcile(incremental, full)
        check("an_incremental_sync_is_reconciled_with_a_full_sync",
              difference["missing_in_incremental"] == ["io.github.four/delta"]
              and not difference["equal"] and reconcile(full, full)["equal"])

        https_budget = RequestBudget(maximum_requests=3)
        transport = HttpsGetTransport(("registry.modelcontextprotocol.io",), https_budget, RequestLog())
        try:
            transport.get("registry.example.invalid", "/v0.1/servers")
            undeclared = False
        except HostNotDeclared:
            undeclared = True
        check("the_https_transport_refuses_an_undeclared_host_before_sending",
              undeclared and https_budget.used == 0)

        approved_claims = []
        for claim in ({"approved": True}, {"lifecycle": "active"}, {"approval_ref": "review/1"}):
            claimed = json.loads(json.dumps(registry_batch))
            claimed["candidates"][0].update(claim)
            try:
                read_candidate_batch(claimed)
                approved_claims.append(("accepted", sorted(claim)))
            except LibraryRecordError as error:
                approved_claims.append((error.code, sorted(claim)))
        check("an_ingested_item_stays_a_candidate_until_independent_review",
              [code for code, _ in approved_claims] == ["unknown_record_fields"] * 3, approved_claims)

        entry = registry_batch["candidates"][0]
        stored = json.loads(quarantine.get(entry["provenance"]["source_digest"]))
        check("a_registry_entry_is_quarantined_as_the_exact_canonical_entry",
              bytes_digest(json.dumps(stored, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()) == entry["provenance"]["source_digest"])

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "library_source_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
