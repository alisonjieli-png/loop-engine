"""Shared fakes for the licensed import checks: licence texts, an in-memory snapshot engine and a fake API.

This module holds no test of its own. The snapshot engine answers from
dictionaries of paths and bytes, names every blob by its real git identity
and records every call, so a check can prove that a repository was or was
not read. No network, process or model is used.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for path in (HERE, HERE.parent / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from loop_engine.core.library_ingestion import engines as ingestion_engines  # noqa: E402
from loop_engine.core.library_ingestion.licence_checks import MIT_FIXTURE, PROPRIETARY_FIXTURE  # noqa: E402
from loop_engine.core.library_ingestion.licences import load_templates  # noqa: E402
from loop_engine.core.library_ingestion.record_rules import git_blob_identity, now_utc  # noqa: E402

from licensed_import.harness_kinds import BLOB_TYPE, TreeEntry  # noqa: E402
from licensed_import.snapshots import Snapshot, SnapshotFailed  # noqa: E402


def licence_text(spdx: str) -> str:
    """A text whose word set is exactly the stored template's, so the gate recognizes it."""
    return " ".join(sorted(load_templates()[spdx].words)) + ".\n"


MIT = MIT_FIXTURE
APACHE = licence_text("Apache-2.0")
GPL = licence_text("GPL-3.0")
SHARE_ALIKE = licence_text("CC-BY-SA-4.0")
ZERO_BSD = licence_text("0BSD")
UNLICENSE = licence_text("Unlicense")
PROPRIETARY = PROPRIETARY_FIXTURE
SKILL_BODY = ("---\nname: {name}\ndescription: Checks a table join before its result is trusted.\n---\n"
              "# {name}\n\nCompare the row counts on both sides of the join, list the keys that match "
              "more than once, and report the duplicated keys before the joined table is used.\n")


def skill(name: str, extra: str = "") -> bytes:
    return (SKILL_BODY.format(name=name) + extra).encode("utf-8")


def builtin_near_engine():
    """The declared fallback near-duplicate engine, taken from the factory table by its identity."""
    slot = ingestion_engines.NEAR_DUPLICATE_SLOT
    return ingestion_engines.FACTORIES[slot.slot_id]["builtin_minhash_lsh"].from_settings({}, {})


class FakeSnapshotEngine:
    """Repositories as {name: {"commit": ..., "files": {path: bytes}, "modes": {path: mode}}}."""

    engine_id = "fake_snapshot"
    engine_version = "1.0.0"

    def __init__(self, repositories: dict, *, fail=()) -> None:
        self.repositories, self.fail = repositories, set(fail)
        self.opened, self.reads = [], []

    def open(self, repository, revision=None):
        self.opened.append(repository)
        if repository in self.fail:
            raise SnapshotFailed("fetch_failed", "a fake failure")
        state = self.repositories[repository]
        if revision is not None and revision != state["commit"]:
            raise SnapshotFailed("fetch_failed", "the fetched commit is not the one asked for")
        modes = state.get("modes", {})
        entries = tuple(TreeEntry(path, modes.get(path, "100644"), BLOB_TYPE, git_blob_identity(payload))
                        for path, payload in sorted(state["files"].items()))
        return Snapshot(repository, state["commit"], entries, self.engine_id, now_utc(), state)

    def read(self, snapshot, oids):
        self.reads.append((snapshot.repository, len(set(oids))))
        wanted = set(oids)
        return {git_blob_identity(payload): payload for payload in snapshot.handle["files"].values()
                if git_blob_identity(payload) in wanted}

    def close(self, snapshot):
        return None


def metadata(name: str, commit: str, licence: "str | None" = "MIT", *, fork=False, stars=10) -> dict:
    return {"declared_excluded": False, "name": name, "fork": fork, "archived": False, "private": False,
            "empty": False, "stars": stars, "disk_kb": 10, "pushed_at": "2026-09-24T00:00:00Z", "licence": licence,
            "head": commit, "parent": None}


class FakeApi:
    """GraphQL metadata from a dictionary, and canned search pages; every call is kept."""

    def __init__(self, repositories: "dict | None" = None, searches: "dict | None" = None) -> None:
        self.repositories, self.searches = repositories or {}, searches or {}
        self.calls = []

    def graphql(self, query):
        self.calls.append(("graphql", query.template))
        data = {}
        for index, name in enumerate(self._names(query.text)):
            facts = self.repositories.get(name)
            data[f"r{index}"] = None if facts is None else {
                "nameWithOwner": name, "isFork": facts.get("fork", False), "isArchived": False,
                "isPrivate": False, "isEmpty": False, "stargazerCount": facts.get("stars", 1), "diskUsage": 1,
                "pushedAt": "2026-09-24T00:00:00Z", "licenseInfo": {"spdxId": facts.get("licence")},
                "defaultBranchRef": {"name": "main", "target": {"oid": facts["commit"]}}, "parent": None}
        return {"status": 200, "body": {"data": data}}

    @staticmethod
    def _names(text):
        import re
        return [f"{owner}/{name}" for owner, name in re.findall(r'repository\(owner: "([^"]+)", name: "([^"]+)"\)', text)]

    def code_search(self, query, page):
        self.calls.append(("code_search", query, page))
        return self.searches.get(("code", query, page), {"status": 200, "body": {"items": [], "total_count": 0}})

    def repository_search(self, query, page):
        self.calls.append(("repository_search", query, page))
        return self.searches.get(("repository", query, page), {"status": 200, "body": {"items": []}})
