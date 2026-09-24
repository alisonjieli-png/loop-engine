"""One sync round: from leads to stored candidates, idea records, refusals and withdrawals.

```text
Sync round (a Practitioner task of the code execution profile, started by an operator command)
├── plan: leads grouped by repository, each repository ordered by its best source, then stars
├── resolve: head commit, licence, fork and archive state of up to 100 repositories per GraphQL read
├── decide what to read
│   ├── a fork, a private or an empty repository: refused by name
│   ├── the head commit already synced: unchanged, nothing is read
│   ├── a declared or listed source: its tree is read, because a nested licence may allow a copy
│   └── a searched source whose repository licence is not on the allowlist: its searched paths
│       become idea records and its tree is not read
├── repository jobs, in parallel, each journaled before and after
│   ├── snapshot at the exact head commit (git partial clone, or the API engine as fallback)
│   ├── package plans from the tree; licence and notice files above every member
│   ├── one batched read of every member and licence file, each byte proven by its git identity
│   ├── licence per file and per package: copy, idea record or refusal
│   ├── static checks and declared effects of every package that may be copied
│   └── catalogue_package/v1 candidates, with every fetched byte kept in quarantine
├── deduplicate the whole round against the served catalogue, the candidate folders under
│   artifacts, the overnight batch, the September 23 runs and earlier import rounds
└── write: bodies to the body store, records to the catalogue store; a changed upstream package
    is a new version, a deleted one or one whose licence changed is withdrawn, history kept
```

The journal records a dispatch event before each repository job and an
outcome event after it, and every outcome is appended to the run folder, so
a stopped round restarts where it stopped without reading a repository
twice. Nothing is approved, served or published.
"""
from __future__ import annotations

import json
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from loop_engine.core.library_ingestion.provenance import GITHUB_ORIGIN, OUTLINE_ONLY, REFUSED, VERBATIM
from loop_engine.core.library_ingestion.record_rules import now_utc

from .checks import blocking_rules, package_cautions, package_effects
from .dedup import BATCH, DuplicateIndex, Subject, owner_of
from .discovery import SOURCE_PRIORITY
from .github_api import MAXIMUM_BATCH, ReadRefused, metadata_query
from .harness_kinds import (
    BLOB_TYPE, SourceScope, ancestors_licence_paths, file_role, licence_only, licence_paths, plan_packages)
from .licensing import decide_package
from .packaging import PackageRefused, build_candidate, comparison_text, fetch_identity
from .records import (
    ALLOWED_LICENCES, EMPTY_STATE, IDEA_RECORD_TYPE, IDEA_STATE, NOT_READ_STATE, READ_STATE, REFUSED_STATE,
    UNCHANGED_STATE, JOURNAL_RECORD_TYPE, REASONS, SOURCE_STATE_RECORD_TYPE,
    WITHDRAWAL_RECORD_TYPE, WITHDRAWN_LIFECYCLE, idea_record_id, refusal, source_state_record_id,
    upstream_key, withdrawal_record_id)
from .snapshots import SnapshotFailed, verify_bytes
from .storage import (
    SUPERSEDED_LIFECYCLE, candidate_store_record, idea_store_record, relabelled, state_store_record,
    withdrawal_store_record)

#: Sources whose repositories are always read, because a nested licence may allow what the
#: repository licence does not; searched sources are read only under an allowlisted licence.
REPOSITORY_STAGE = "repository"
ALWAYS_READ = frozenset({"declared_repositories", "owner_seed_resolver", "research_seed_lists", "clawhub_feeds"})
MAXIMUM_FILE_BYTES = 2 * 1024 * 1024


@dataclass
class RepositoryPlan:
    repository: str
    sources: set = field(default_factory=set)
    engines: set = field(default_factory=set)
    paths: dict = field(default_factory=dict)
    scope: "SourceScope | None" = None
    priority: int = 99
    stars: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class RepositoryOutcome:
    repository: str
    commit: "str | None" = None
    engine_id: "str | None" = None
    candidates: list = field(default_factory=list)
    ideas: list = field(default_factory=list)
    refusals: list = field(default_factory=list)
    texts: dict = field(default_factory=dict)
    restricted: dict = field(default_factory=dict)
    counts: Counter = field(default_factory=Counter)
    elapsed_seconds: float = 0.0
    state: str = READ_STATE

    def to_record(self) -> dict:
        return {"repository": self.repository, "commit": self.commit, "engine_id": self.engine_id,
                "candidates": self.candidates, "ideas": self.ideas, "refusals": self.refusals, "texts": self.texts,
                "restricted": self.restricted, "counts": dict(self.counts), "elapsed_seconds": self.elapsed_seconds,
                "state": self.state}

    @classmethod
    def from_record(cls, value: dict) -> "RepositoryOutcome":
        return cls(value["repository"], value["commit"], value["engine_id"], value["candidates"], value["ideas"],
                   value["refusals"], value["texts"], value["restricted"], Counter(value["counts"]),
                   value["elapsed_seconds"], value["state"])


class Journal:
    """Dispatch and outcome events of one round, appended in order; the recovery source of truth."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        self.path = self.folder / "journal.jsonl"
        self.outcomes = self.folder / "outcomes.jsonl"
        self._lock = threading.Lock()

    def event(self, event: str, repository: str = "", **detail) -> None:
        row = {"record_type": JOURNAL_RECORD_TYPE, "event": event, "repository": repository, "at": now_utc(),
               "detail": detail}
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")

    def outcome(self, outcome: RepositoryOutcome) -> None:
        with self._lock, self.outcomes.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(outcome.to_record(), sort_keys=True) + "\n")

    def finished(self) -> dict:
        """Outcomes already recorded, by repository: these repositories are not read again."""
        found = {}
        if self.outcomes.is_file():
            for line in self.outcomes.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    outcome = RepositoryOutcome.from_record(json.loads(line))
                    found[outcome.repository.lower()] = outcome
        return found


def plan_repositories(leads, declared_scopes: dict, excluded=frozenset()) -> dict:
    """Leads grouped by repository, case-insensitively, each with its sources, paths and scope.

    A repository the declaration excludes (a collection whose root licence
    cannot stand for the copies of other authors' work it holds) keeps its
    plan so the refusal is counted, but it is never read.
    """
    plans = {}
    excluded = {name.lower() for name in excluded}
    for row in leads:
        key = row["repository"].lower()
        plan = plans.setdefault(key, RepositoryPlan(row["repository"]))
        plan.sources.add(row["source_id"])
        plan.engines.add(row["engine_id"])
        plan.priority = min(plan.priority, SOURCE_PRIORITY.get(row["engine_id"], 99))
        plan.stars = max(plan.stars, int((row.get("detail") or {}).get("stars") or 0))
        if row.get("path"):
            plan.paths.setdefault(row["path"], {"blob_sha": row.get("blob_sha"), "kind_hint": row.get("kind_hint"),
                                                "source_id": row["source_id"]})
        if row["source_id"] in declared_scopes:
            plan.scope = declared_scopes[row["source_id"]]
        if key in excluded:
            plan.metadata["declared_excluded"] = True
    return plans


def _facts(facts: dict, plan: RepositoryPlan) -> dict:
    return {"declared_excluded": plan.metadata.get("declared_excluded", False),
            "name": facts["nameWithOwner"], "fork": facts["isFork"], "archived": facts["isArchived"],
            "private": facts["isPrivate"], "empty": facts["isEmpty"], "stars": facts["stargazerCount"],
            "disk_kb": facts["diskUsage"], "pushed_at": facts["pushedAt"],
            "licence": (facts.get("licenseInfo") or {}).get("spdxId"),
            "head": (((facts.get("defaultBranchRef") or {}).get("target")) or {}).get("oid"),
            "parent": (facts.get("parent") or {}).get("nameWithOwner")}


def resolve_metadata(plans: dict, api, cache_path: "Path | None" = None) -> list:
    """GraphQL metadata for every planned repository, 100 to a read; refusals for the missing.

    Each resolved chunk is appended to the run's metadata cache, so a round
    that stops restarts without reading those repositories' metadata again.
    A whole read that fails is read again once, then in halves; a read the
    request shapes refuse is split down to one repository, and only that
    repository is refused.
    """
    refusals = []
    cached = {}
    if cache_path is not None and Path(cache_path).is_file():
        for line in Path(cache_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                cached[row["key"]] = row["facts"]
    keys = sorted(key for key in plans if key not in cached)
    for key, facts in cached.items():
        if key in plans:
            plans[key].metadata = ({**facts, "declared_excluded": plans[key].metadata.get("declared_excluded", False)}
                                   if facts else {"unavailable": True,
                                                  "declared_excluded": plans[key].metadata.get("declared_excluded", False)})
            if facts:
                plans[key].stars = max(plans[key].stars, facts.get("stars") or 0)
            else:
                refusals.append(refusal("repository", "repository_unavailable", repository=plans[key].repository,
                                        source_ids=plans[key].sources))
    pending = [keys[start:start + MAXIMUM_BATCH] for start in range(0, len(keys), MAXIMUM_BATCH)]
    while pending:
        chunk = pending.pop(0)
        try:
            answer = api.graphql(metadata_query([plans[key].repository for key in chunk]))
        except ReadRefused:
            if len(chunk) > 1:
                middle = len(chunk) // 2
                pending[:0] = [chunk[:middle], chunk[middle:]]
                continue
            answer = {"status": None, "body": None}
        if answer.get("status") != 200 or not isinstance((answer.get("body") or {}).get("data"), dict):
            # A whole read failed (a timeout or a server error): read it again once, then in halves,
            # so one bad read never marks a hundred repositories unavailable.
            retried = api.graphql(metadata_query([plans[key].repository for key in chunk])) \
                if answer.get("status") is not None else answer
            if retried.get("status") == 200 and isinstance((retried.get("body") or {}).get("data"), dict):
                answer = retried
            elif len(chunk) > 1:
                middle = len(chunk) // 2
                pending[:0] = [chunk[:middle], chunk[middle:]]
                continue
        data = ((answer.get("body") or {}).get("data")) or {}
        rows = []
        for index, key in enumerate(chunk):
            facts = data.get(f"r{index}")
            if not facts:
                plans[key].metadata = {"unavailable": True,
                                       "declared_excluded": plans[key].metadata.get("declared_excluded", False)}
                refusals.append(refusal("repository", "repository_unavailable", repository=plans[key].repository,
                                        source_ids=plans[key].sources))
                rows.append({"key": key, "facts": None})
                continue
            plans[key].metadata = _facts(facts, plans[key])
            plans[key].stars = max(plans[key].stars, facts["stargazerCount"] or 0)
            rows.append({"key": key, "facts": {name: value for name, value in plans[key].metadata.items()
                                               if name != "declared_excluded"}})
        if cache_path is not None:
            with Path(cache_path).open("a", encoding="utf-8") as stream:
                for row in rows:
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
    return refusals


def ordered(plans: dict) -> list:
    return sorted(plans.values(), key=lambda plan: (plan.priority, -plan.stars, plan.repository.lower()))


class SyncRound:
    """One restartable round over planned repositories, then deduplication and one write."""

    def __init__(self, *, run_folder: Path, store, snapshot_engines, checks, near, api=None, workers: int = 6,
                 time_limit_seconds: float = 3600.0, imported_on: str = "", corpora=(),
                 maximum_file_bytes: int = MAXIMUM_FILE_BYTES, clock=time.monotonic, batch_checks=None,
                 scan_workers: int = 1) -> None:
        self.run_folder, self.store, self.engines = Path(run_folder), store, list(snapshot_engines)
        self.checks, self.near, self.api, self.workers = checks, near, api, workers
        self.batch_checks, self.scan_workers = batch_checks, max(1, int(scan_workers))
        self.time_limit_seconds, self.imported_on = time_limit_seconds, imported_on or now_utc()[:10]
        self.corpora, self.maximum_file_bytes, self.clock = list(corpora), maximum_file_bytes, clock
        self.journal = Journal(self.run_folder)
        self._quarantine_lock = threading.Lock()

    def previous_state(self, repository: str) -> "dict | None":
        record = self.store.get(source_state_record_id(repository))
        return record["payload"] if record else None

    def decide_reading(self, plan: RepositoryPlan) -> "tuple | None":
        """(stage, reason) when a repository is not read, or None to read it."""
        facts = plan.metadata
        if facts.get("declared_excluded"):
            return (REPOSITORY_STAGE, "repository_declared_excluded")
        if facts.get("unavailable"):
            return (REPOSITORY_STAGE, "repository_unavailable")
        if facts.get("fork"):
            return (REPOSITORY_STAGE, "repository_is_fork")
        if facts.get("private"):
            return (REPOSITORY_STAGE, "repository_is_private")
        if facts.get("empty") or not facts.get("head"):
            return (REPOSITORY_STAGE, "repository_empty")
        if not (plan.engines & ALWAYS_READ) and facts.get("licence") not in ALLOWED_LICENCES:
            return (IDEA_STATE, "repository_licence_not_on_allowlist")
        return None

    def search_ideas(self, plan: RepositoryPlan) -> list:
        """Idea records for the searched paths of a repository whose licence allows no copy; no bytes read."""
        ideas = []
        roots = {}
        for path, facts in sorted(plan.paths.items()):
            kind = facts.get("kind_hint")
            if kind is None:
                continue
            root = str(Path(path).parent) if kind == "skill" else path
            root = "" if root == "." else root
            key = upstream_key(GITHUB_ORIGIN, plan.metadata.get("name") or plan.repository, root, kind)
            if key in roots:
                continue
            roots[key] = True
            ideas.append(self._idea(key, kind, Path(root).name or Path(path).name, plan, path, facts.get("blob_sha"),
                                    None, {"spdx_expression": plan.metadata.get("licence") or "NOASSERTION",
                                           "decision": OUTLINE_ONLY,
                                           "reason": "repository_licence_not_on_allowlist"}))
        return ideas

    def _idea(self, key, kind, name, plan, path, blob, commit, licence) -> dict:
        return {"record_type": IDEA_RECORD_TYPE, "record_id": idea_record_id(key), "upstream_key": key,
                "kind": kind, "name": name, "repository": plan.metadata.get("name") or plan.repository,
                "revision": commit, "path": path, "git_blob_sha": blob, "licence": licence,
                "sources": sorted(plan.sources), "found_on": self.imported_on}

    def read_repository(self, plan: RepositoryPlan) -> RepositoryOutcome:
        started = self.clock()
        repository = plan.metadata.get("name") or plan.repository
        outcome = RepositoryOutcome(repository)
        snapshot, engine, failure = None, None, None
        for candidate in self.engines:
            try:
                snapshot = candidate.open(repository, plan.metadata["head"])
                engine = candidate
                break
            except SnapshotFailed as error:
                failure = error
        if snapshot is None:
            reason = failure.code if failure and failure.code in REASONS["repository"] else "fetch_failed"
            outcome.refusals.append(refusal("repository", reason, repository=repository,
                                            detail=(failure.detail if failure else "")[:200],
                                            source_ids=plan.sources))
            outcome.state = REFUSED_STATE
            outcome.elapsed_seconds = round(self.clock() - started, 3)
            return outcome
        try:
            self._read_snapshot(plan, snapshot, engine, outcome)
        except SnapshotFailed as error:
            reason = error.code if error.code in REASONS["repository"] else "fetch_failed"
            outcome.refusals.append(refusal("repository", reason, repository=repository, revision=snapshot.commit,
                                            detail=error.detail[:200], source_ids=plan.sources))
            outcome.state = REFUSED_STATE
        except Exception as error:  # one repository's unexpected failure never stops the round
            outcome.candidates, outcome.ideas, outcome.texts, outcome.restricted = [], [], {}, {}
            outcome.refusals.append(refusal("repository", "repository_job_failed", repository=repository,
                                            revision=snapshot.commit, detail=f"{type(error).__name__}: {error}"[:200],
                                            source_ids=plan.sources))
            outcome.state = REFUSED_STATE
        finally:
            engine.close(snapshot)
        outcome.elapsed_seconds = round(self.clock() - started, 3)
        return outcome

    def _read_snapshot(self, plan, snapshot, engine, outcome) -> None:
        outcome.commit, outcome.engine_id = snapshot.commit, engine.engine_id
        repository = snapshot.repository
        package_plans, _skipped = plan_packages(snapshot.entries, plan.scope or SourceScope(), repository)
        outcome.counts["tree_entries"] = len(snapshot.entries)
        outcome.counts["packages_planned"] = len(package_plans)
        if not package_plans:
            outcome.refusals.append(refusal("repository", "no_harness_files", repository=repository,
                                            revision=snapshot.commit, source_ids=plan.sources))
            outcome.state = EMPTY_STATE
            return
        oids = {entry.path: entry.oid for entry in snapshot.entries if entry.object_type == BLOB_TYPE}
        # A package's primary file is harness material even when its name looks like a licence
        # file (a command named license-check.md), so it never governs its neighbours.
        primaries = {package.primary for package in package_plans if not licence_only(package.primary)}
        licence_index = {path: oid for path, oid in licence_paths(snapshot.entries).items() if path not in primaries}
        wanted = set()
        for package in package_plans:
            if not package.problems:
                wanted.update(oids[path] for path in package.members if path in oids)
                wanted.update(licence_index[path] for path in ancestors_licence_paths(package.members, licence_index))
        found = verify_bytes(engine.read(snapshot, wanted)) if wanted else {}
        outcome.counts["blobs_read"] = len(found)
        outcome.counts["bytes_read"] = sum(len(payload) for payload in found.values())
        with self._quarantine_lock:
            for payload in found.values():
                self.store.quarantine.put(payload)
        fetch_digest, request_digest = fetch_identity(engine.engine_id, repository, snapshot.commit)
        ready = {}
        for package in package_plans:
            if licence_only(package.primary):
                # A unit that is only a licence text is no material to copy; its text still
                # governs the files beside it through the licence gate.
                outcome.refusals.append(refusal("package", "unit_is_only_a_licence_file", repository=repository,
                                                revision=snapshot.commit, path=package.primary, source_ids=plan.sources))
                continue
            if package.problems:
                outcome.refusals.append(refusal("package", package.problems[0], repository=repository,
                                                revision=snapshot.commit, path=package.primary, source_ids=plan.sources))
                continue
            members = {path: found.get(oids.get(path)) for path in package.members}
            missing = [path for path, payload in members.items() if payload is None]
            if missing:
                outcome.refusals.append(refusal("package", "file_bytes_mismatch", repository=repository,
                                                revision=snapshot.commit, path=missing[0], source_ids=plan.sources))
                continue
            if any(len(payload) > self.maximum_file_bytes for payload in members.values()):
                outcome.refusals.append(refusal("package", "file_above_fetch_limit", repository=repository,
                                                revision=snapshot.commit, path=package.primary, source_ids=plan.sources))
                continue
            licence_bytes = {path: found[licence_index[path]]
                             for path in ancestors_licence_paths(package.members, licence_index)
                             if licence_index[path] in found}
            decision = decide_package(members, package.primary, licence_bytes,
                                      github_spdx=plan.metadata.get("licence"))
            key = upstream_key(GITHUB_ORIGIN, repository, package.root, package.kind)
            if decision.decision == REFUSED:
                reason = decision.reason if decision.reason in REASONS["licence"] else "licence_prohibits_derivatives"
                outcome.refusals.append(refusal("licence", reason, repository=repository, revision=snapshot.commit,
                                                path=package.primary, source_ids=plan.sources))
                outcome.restricted[key] = comparison_text(package.primary, members[package.primary])
                continue
            if decision.decision != VERBATIM:
                outcome.ideas.append(self._idea(key, package.kind, package.name, plan, package.primary,
                                                oids.get(package.primary), snapshot.commit,
                                                {"spdx_expression": decision.spdx_expression,
                                                 "decision": decision.decision, "reason": decision.reason}))
                outcome.restricted[key] = comparison_text(package.primary, members[package.primary])
                continue
            ready[key] = (package, members, decision, licence_bytes)
        scanned = self.checks.scan({key: sorted(value[1].items()) for key, value in ready.items()})
        for key, (package, members, decision, licence_bytes) in sorted(ready.items()):
            findings = scanned.get(key, []) + package_cautions(package.kind, members)
            blocked = blocking_rules(findings)
            if blocked:
                outcome.refusals.append(refusal("check", "blocked_by_static_check", repository=repository,
                                                revision=snapshot.commit, path=package.primary,
                                                detail=",".join(blocked), source_ids=plan.sources))
                continue
            roles = {path: file_role(package.kind, package.root, path) for path in members}
            effects, evidence = package_effects(package.kind, members, roles)
            try:
                built = build_candidate(
                    plan=package, repository=repository, commit=snapshot.commit, fetched_at=snapshot.fetched_at,
                    member_bytes=members, oids=oids, licence=decision, licence_bytes=licence_bytes,
                    findings=findings, effects=effects, effect_evidence=evidence, sources=plan.sources,
                    fetch_digest=fetch_digest, request_digest=request_digest, imported_on=self.imported_on,
                    repository_facts={"name": repository, "commit": snapshot.commit,
                                      "stars": plan.metadata.get("stars"), "archived": plan.metadata.get("archived"),
                                      "licence_signal": plan.metadata.get("licence"),
                                      "priority": plan.priority, "snapshot_engine": engine.engine_id})
            except PackageRefused as error:
                code = error.code if error.code in REASONS["package"] else "package_path_invalid"
                outcome.refusals.append(refusal("package", code, repository=repository, revision=snapshot.commit,
                                                path=package.primary, detail=error.detail, source_ids=plan.sources))
                continue
            with self._quarantine_lock:
                for payload in built.bodies.values():
                    self.store.quarantine.put(payload)
            outcome.candidates.append(built.payload)
            outcome.texts[built.payload["record_id"]] = built.comparison_text
        outcome.counts["candidates_built"] = len(outcome.candidates)
        outcome.counts["ideas"] = len(outcome.ideas)

    def run(self, plans: dict) -> dict:
        """Read every repository not yet read in this round, within the time limit."""
        finished = self.journal.finished()
        started = self.clock()
        pending, skipped = [], []
        for plan in ordered(plans):
            if plan.repository.lower() in finished or (plan.metadata.get("name") or "").lower() in finished:
                continue
            decision = self.decide_reading(plan)
            if decision is not None:
                skipped.append((plan, decision))
                continue
            previous = self.previous_state(plan.metadata.get("name") or plan.repository)
            if previous and previous.get("commit") == plan.metadata.get("head"):
                skipped.append((plan, (UNCHANGED_STATE, "head_commit_already_synced")))
                continue
            pending.append(plan)
        for plan, (stage, reason) in skipped:
            outcome = RepositoryOutcome(plan.metadata.get("name") or plan.repository,
                                        state=stage if stage in (IDEA_STATE, UNCHANGED_STATE) else NOT_READ_STATE)
            if stage == IDEA_STATE:
                outcome.ideas = self.search_ideas(plan)
            elif stage == REPOSITORY_STAGE:
                outcome.refusals.append(refusal("repository", reason, repository=outcome.repository,
                                                source_ids=plan.sources))
            outcome.counts[f"not_read_{reason}"] = 1
            self.journal.outcome(outcome)
        stopped = False
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            running = {}
            queue = list(pending)
            while queue or running:
                while queue and len(running) < self.workers * 2:
                    if self.clock() - started > self.time_limit_seconds:
                        stopped = True
                        queue.clear()
                        break
                    plan = queue.pop(0)
                    self.journal.event("dispatch", plan.repository)
                    running[pool.submit(self.read_repository, plan)] = plan
                if not running:
                    break
                done = next(as_completed(running))
                plan = running.pop(done)
                outcome = done.result()
                self.journal.event("outcome", plan.repository, state=outcome.state,
                                   candidates=len(outcome.candidates), ideas=len(outcome.ideas),
                                   refusals=len(outcome.refusals), seconds=outcome.elapsed_seconds)
                self.journal.outcome(outcome)
        self.journal.event("phase", "", phase="reading_finished", stopped_by_time_limit=stopped,
                           seconds=round(self.clock() - started, 1))
        return {"pending": len(pending), "skipped": len(skipped), "stopped_by_time_limit": stopped,
                "reading_seconds": round(self.clock() - started, 1)}

    def deduplicate(self, outcomes) -> tuple:
        """The duplicate resolution of this round's candidates against every corpus and each other."""
        index = DuplicateIndex(self.near)
        for subject in self.corpora:
            index.add(subject)
        candidates = {}
        for outcome in outcomes:
            for payload in outcome.candidates:
                repository = payload["repository"]
                order = (repository.get("priority", 99), -(repository.get("stars") or 0),
                         payload["provenance"]["repository"].lower(), payload["provenance"]["path"])
                index.add(Subject(payload["record_id"], BATCH, payload["record_id"], order,
                                  outcome.texts.get(payload["record_id"], ""),
                                  blob=payload["provenance"]["git_blob_sha"],
                                  owner=owner_of(payload["provenance"]["repository"])))
                candidates[payload["record_id"]] = payload
            for key, text in outcome.restricted.items():
                index.add(Subject(f"restricted:{key}", BATCH, f"restricted:{outcome.repository}:{key}",
                                  (-1, 0, key, ""), text, restricted=True, owner=owner_of(outcome.repository)))
        return index.resolve(), candidates

    def batch_scan(self, resolution, candidates) -> list:
        """Slow scanners, run once over the kept packages after deduplication, in chunks.

        A scanner that starts a process for every call (SkillSpector) would
        cost minutes per repository inside the repository jobs, so it runs
        here over every kept candidate at once. A blocking finding removes
        the candidate from the kept list and becomes a refusal; a caution
        finding joins the candidate's findings.
        """
        if self.batch_checks is None or not self.batch_checks.engines:
            return []
        packages = {}
        for key in resolution.kept:
            payload = candidates[key]
            packages[key] = [(entry["path"], self.store.quarantine.get(entry["digest"]))
                             for entry in payload["package"]["files"]]
        # Each scanner starts one sandboxed process per chunk, so groups of packages are scanned
        # in parallel; every package is in exactly one group and every finding is kept.
        keys = sorted(packages)
        groups = [keys[index::self.scan_workers] for index in range(self.scan_workers) if keys[index::self.scan_workers]]
        found = {}
        with ThreadPoolExecutor(max_workers=max(1, len(groups))) as pool:
            for result in pool.map(lambda group: self.batch_checks.scan({key: packages[key] for key in group}), groups):
                found.update(result)
        refused = []
        for key, findings in found.items():
            blocked = blocking_rules(findings)
            if blocked:
                resolution.kept.remove(key)
                source = candidates[key]["provenance"]
                refused.append(refusal("check", "blocked_by_static_check", repository=source["repository"],
                                       revision=source["immutable_revision"], path=source["path"],
                                       detail=",".join(blocked), source_ids=candidates[key]["sources"]))
            elif findings:
                candidates[key]["findings"] = candidates[key]["findings"] + [
                    {**finding, "path": finding.get("path", "")} for finding in findings]
        return refused

    def write(self, outcomes, resolution, candidates) -> dict:
        """Bodies to the body store and records to the catalogue store, with versions and withdrawals."""
        kept = {key: dict(candidates[key]) for key in resolution.kept}
        for merged, into in resolution.merged_into.items():
            if into in kept and merged in candidates:
                source = candidates[merged]["provenance"]
                kept[into]["merged"].append({"repository": source["repository"], "revision":
                                             source["immutable_revision"], "path": source["path"],
                                             "git_blob_sha": source["git_blob_sha"],
                                             "record_id": candidates[merged]["record_id"]})
        for key, refs in resolution.supersedes.items():
            kept[key]["version"]["supersedes"] = refs
        records, expected, relabels = [], {}, []
        bodies = {}
        states = defaultdict(lambda: {"packages": {}, "ideas": {}})
        for payload in kept.values():
            for entry in payload["package"]["files"]:
                bodies[entry["digest"]] = self.store.quarantine.get(entry["digest"])
        for outcome in outcomes:
            state = states[outcome.repository.lower()]
            state["repository"], state["commit"], state["engine"] = outcome.repository, outcome.commit, outcome.engine_id
            state["read"] = outcome.state == READ_STATE
            for payload in outcome.candidates:
                if payload["record_id"] in kept:
                    state["packages"][payload["upstream_key"]] = {"record_id": payload["record_id"],
                                                                 "package_digest": payload["package_digest"],
                                                                 "kind": payload["kind"]}
            for idea in outcome.ideas:
                state["ideas"][idea["upstream_key"]] = {"kind": idea["kind"], "reason": idea["licence"]["reason"]}
        written_ideas = 0
        for outcome in outcomes:
            for idea in outcome.ideas:
                current = self.store.get(idea["record_id"])
                record = idea_store_record(idea)
                if current is None:
                    records.append(record)
                    written_ideas += 1
                elif current["record_version"] != record["record_version"] and current["payload"].get("revision") != idea.get("revision"):
                    expected[record["record_id"]] = current["record_version"]
                    records.append(record)
        withdrawals = []
        for key, state in states.items():
            if not state.get("read") or not state.get("commit"):
                continue
            previous = self.previous_state(state["repository"]) or {"packages": {}}
            for upstream, old in (previous.get("packages") or {}).items():
                new = state["packages"].get(upstream)
                if new and new["package_digest"] == old["package_digest"]:
                    continue
                current = self.store.get(old["record_id"])
                if current is None:
                    continue
                if new:
                    kept_payload = next(payload for payload in kept.values() if payload["record_id"] == new["record_id"])
                    kept_payload["version"]["previous_record_id"] = old["record_id"]
                    relabels.append((current, SUPERSEDED_LIFECYCLE))
                else:
                    reason = "licence_changed" if upstream in state["ideas"] else "upstream_deleted"
                    payload = {"record_type": WITHDRAWAL_RECORD_TYPE, "upstream_key": upstream,
                               "withdrawn_record_id": old["record_id"], "reason": reason,
                               "repository": state["repository"], "revision": state["commit"], "at": now_utc()}
                    withdrawals.append(withdrawal_store_record(
                        payload, withdrawal_record_id(upstream, old["package_digest"])))
                    relabels.append((current, WITHDRAWN_LIFECYCLE))
        for payload in kept.values():
            if self.store.get(payload["record_id"]) is None:
                records.append(candidate_store_record(payload))
        for current, lifecycle in relabels:
            updated = relabelled(current, lifecycle)
            expected[updated["record_id"]] = current["record_version"]
            records.append(updated)
        for withdrawal in withdrawals:
            if self.store.get(withdrawal["record_id"]) is None:
                records.append(withdrawal)
        for state in states.values():
            if not state.get("commit"):
                continue
            payload = {"record_type": SOURCE_STATE_RECORD_TYPE, "repository": state["repository"],
                       "commit": state["commit"], "snapshot_engine": state["engine"], "synced_at": now_utc(),
                       "packages": state["packages"], "ideas": state["ideas"]}
            record = state_store_record(payload, source_state_record_id(state["repository"]))
            current = self.store.get(record["record_id"])
            if current is not None:
                expected[record["record_id"]] = current["record_version"]
            records.append(record)
        body_result = self.store.put_bodies(bodies)
        self.store.apply(records, expected=expected)
        return {"bodies": body_result, "records_written": len(records), "candidates_written": len(kept),
                "ideas_written": written_ideas, "withdrawals": len(withdrawals),
                "superseded": sum(1 for _record, lifecycle in relabels if lifecycle == SUPERSEDED_LIFECYCLE)}


def restricted_refusals(resolution, candidates) -> list:
    rows = []
    for key, source in resolution.restricted_copies.items():
        payload = candidates.get(key)
        if payload is None:
            continue
        rows.append(refusal("duplicate", "copy_of_restricted_source", repository=payload["provenance"]["repository"],
                            revision=payload["provenance"]["immutable_revision"], path=payload["provenance"]["path"],
                            detail=str(source)[:200], source_ids=payload["sources"]))
    return rows
