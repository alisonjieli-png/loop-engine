"""The evidence of one import round, without any third-party text.

The report is written into a folder that the repository keeps: counts by
source, kind and licence, refusals and idea records by reason, duplicates by
signal and corpus, the measured rates of each phase, the store's size and a
projection of the time to one million distinct licence-cleared files. The
compact candidate index lists each candidate's identity, kind, digests,
upstream repository, commit, path and licence, never a body or a
description.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore

from .records import CANDIDATE_LIFECYCLE, IDEA_LIFECYCLE, READ_STATE, REPORT_RECORD_TYPE, SKILL, UPSTREAM_FILE

HOUR = 3600.0
TARGET = 1_000_000


def _jsonl(path: Path) -> list:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


IDLE_GAP_SECONDS = 300.0


def active_seconds(times) -> float:
    """Seconds of work between journal events, leaving out every gap longer than five minutes.

    A round that stopped and restarted (a crash, a usage limit) is measured by
    the time it worked, not by the hours it waited.
    """
    stamps = sorted(datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ") for value in times)
    total = 0.0
    for earlier, later in zip(stamps, stamps[1:]):
        gap = (later - earlier).total_seconds()
        if gap <= IDLE_GAP_SECONDS:
            total += gap
    return total


def _latest(folder: Path, prefix: str) -> list:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob(f"{prefix}*.json"))]


def per_source_rates(kept, outcomes, leads, discovery_reports, workers: int) -> dict:
    """Yield and rate per source: each repository counts once, for its best source.

    A repository found by several sources is credited to the one processed
    first (the declared order of the discovery engines). Its reading time is
    the sum of its jobs' elapsed seconds divided by the parallel workers, and
    the source's discovery time is added, so the rate is licence-cleared,
    deduplicated upstream files per hour of the round's own time.
    """
    from .discovery import SOURCE_PRIORITY
    engines_of = defaultdict(set)
    for row in leads:
        engines_of[row["repository"].lower()].add(row["engine_id"])
    first = {name: min(found, key=lambda engine: SOURCE_PRIORITY.get(engine, 99))
             for name, found in engines_of.items()}
    rows = defaultdict(lambda: {"repositories": 0, "repositories_read": 0, "candidates": 0, "upstream_files": 0,
                                "reading_seconds": 0.0, "discovery_seconds": 0.0, "discovery_requests": 0})
    for name, engine in first.items():
        rows[engine]["repositories"] += 1
    for outcome in outcomes:
        engine = first.get(outcome["repository"].lower())
        if engine is None:
            continue
        if outcome["state"] == READ_STATE:
            rows[engine]["repositories_read"] += 1
        rows[engine]["reading_seconds"] += float(outcome.get("elapsed_seconds") or 0.0)
    seen = set()
    for payload in kept:
        engine = first.get(payload["provenance"]["repository"].lower())
        if engine is None:
            continue
        rows[engine]["candidates"] += 1
        for entry in payload["files"]:
            if entry["origin"] == UPSTREAM_FILE and entry["digest"] not in seen:
                seen.add(entry["digest"])
                rows[engine]["upstream_files"] += 1
    for report in discovery_reports:
        for engine, facts in report["engines"].items():
            rows[engine]["discovery_seconds"] += float(facts.get("seconds") or 0.0)
            rows[engine]["discovery_requests"] += int(facts.get("requests") or 0)
    result = {}
    for engine, row in sorted(rows.items(), key=lambda item: SOURCE_PRIORITY.get(item[0], 99)):
        hours = (row["discovery_seconds"] + row["reading_seconds"] / max(1, workers)) / HOUR
        result[engine] = {**row, "reading_seconds": round(row["reading_seconds"], 1),
                          "discovery_seconds": round(row["discovery_seconds"], 1),
                          "files_per_hour": round(row["upstream_files"] / hours, 1) if hours else None}
    return result


def build_report(run_folder: Path, store_root: Path, output: Path, *, workers: int = 8,
                 index_path: "Path | None" = None) -> dict:
    """Write the evidence files of one round and return the batch report.

    The compact candidate index is written to `index_path` when one is given
    (the store folder, outside git, for a round too large to commit), and the
    report records its row count and SHA-256 either way.
    """
    output.mkdir(parents=True, exist_ok=True)
    store = SQLiteRecordStore(str(store_root / "records.db"), read_only=True)
    try:
        candidates = [row for row in store.query(IntelligenceQuery(namespaces=("library.import",),
                                                                   lifecycle=(CANDIDATE_LIFECYCLE,)))]
        ideas = [row for row in store.query(IntelligenceQuery(namespaces=("library.import",),
                                                              lifecycle=(IDEA_LIFECYCLE,)))]
    finally:
        store.close()
    outcomes = _jsonl(run_folder / "outcomes.jsonl")
    journal = _jsonl(run_folder / "journal.jsonl")
    leads = _jsonl(run_folder / "leads.jsonl")
    duplicates = _jsonl(run_folder / "duplicates.jsonl")
    restricted = _jsonl(run_folder / "restricted-copies.jsonl")
    refusals = [row for outcome in outcomes for row in outcome["refusals"]]
    refusals += _jsonl(run_folder / "metadata-refusals.jsonl") + _jsonl(run_folder / "discovery-refusals.jsonl")
    refusals += restricted + _jsonl(run_folder / "batch-scan-refusals.jsonl")
    discovery_reports = _latest(run_folder, "discovery-report-")
    sync_summaries = _latest(run_folder, "sync-summary-")
    kept = [row["payload"] for row in candidates]
    lead_sources = defaultdict(set)
    for row in leads:
        lead_sources[row["repository"].lower()].add(row["engine_id"])
    by_engine = Counter()
    first_engine = Counter()
    from .discovery import SOURCE_PRIORITY  # noqa: F811
    for payload in kept:
        engines = lead_sources.get(payload["provenance"]["repository"].lower(), set())
        for engine in engines:
            by_engine[engine] += 1
        if engines:
            first_engine[min(engines, key=lambda name: SOURCE_PRIORITY.get(name, 99))] += 1
    files = sum(len(payload["package"]["files"]) for payload in kept)
    upstream_files = sum(1 for payload in kept for entry in payload["files"] if entry["origin"] == UPSTREAM_FILE)
    unique_bodies = {entry["digest"] for payload in kept for entry in payload["package"]["files"]}
    body_bytes = sum(entry["size_bytes"] for payload in kept for entry in payload["package"]["files"]
                     if entry["digest"] in unique_bodies)
    reading_seconds = active_seconds(row["at"] for row in journal if row["event"] in ("dispatch", "outcome"))
    discovery_seconds = sum(engine.get("seconds", 0) for report in discovery_reports
                            for engine in report["engines"].values())
    sync_seconds = sum(summary.get("metadata_seconds", 0) + summary.get("dedup_seconds", 0)
                       + summary.get("batch_scan_seconds", 0) + summary.get("write_seconds", 0)
                       for summary in sync_summaries) + reading_seconds
    elapsed = discovery_seconds + sync_seconds
    read_repositories = sum(1 for outcome in outcomes if outcome["state"] == READ_STATE)
    per_hour = len(kept) / (elapsed / HOUR) if elapsed else 0.0
    unique_upstream = len({entry["digest"] for payload in kept for entry in payload["files"]
                           if entry["origin"] == UPSTREAM_FILE})
    files_per_hour = unique_upstream / (elapsed / HOUR) if elapsed else 0.0
    store_size = _store_size(store_root)
    bytes_per_file = store_size["bodies"]["bytes"] / store_size["bodies"]["files"] if store_size["bodies"]["files"] else 0
    headline = {
        "candidates_kept": len(kept), "candidate_files": files, "upstream_files": upstream_files,
        "superseding_september_23_rows": sum(1 for payload in kept if payload["version"]["supersedes"]),
        "idea_records": len(ideas), "refusals": len(refusals), "duplicates_removed": len(duplicates),
        "repositories_read": read_repositories, "repositories_with_candidates":
            len({payload["provenance"]["repository"].lower() for payload in kept}),
        "unique_upstream_files": unique_upstream,
        "elapsed_seconds": round(elapsed, 1), "candidates_per_hour": round(per_hour, 1),
        "unique_upstream_files_per_hour": round(files_per_hour, 1),
        "hours_to_one_million_files_at_this_rate": round(TARGET / files_per_hour, 1) if files_per_hour else None}
    report = {
        "record_type": REPORT_RECORD_TYPE, "run_folder": run_folder.name, "headline": headline,
        "kinds": dict(Counter(payload["kind"] for payload in kept).most_common()),
        "licences": dict(Counter(payload["licence"]["spdx_expression"] for payload in kept).most_common()),
        "declared_effects": dict(Counter(effect for payload in kept for effect in payload["declared_effects"])),
        "caution_findings": dict(Counter(finding["rule"] for payload in kept for finding in payload["findings"])),
        "skills_whose_declared_name_differs_from_folder": sum(
            1 for payload in kept if payload["kind"] == SKILL and isinstance(payload.get("declared_name"), str)
            and payload["declared_name"].strip() != payload["name"]),
        "yield_by_first_source": dict(first_engine.most_common()),
        "rates_by_source": per_source_rates(kept, outcomes, leads, discovery_reports, workers),
        "yield_found_by_source": dict(by_engine.most_common()),
        "leads_by_source": dict(Counter(row["engine_id"] for row in leads).most_common()),
        "repositories_by_source": {engine: len({row["repository"].lower() for row in leads
                                                if row["engine_id"] == engine})
                                   for engine in sorted({row["engine_id"] for row in leads})},
        "refusals_by_reason": dict(Counter(f"{row['stage']}:{row['reason']}" for row in refusals).most_common()),
        "ideas_by_reason": dict(Counter(row["payload"]["licence"]["reason"] for row in ideas).most_common()),
        "ideas_by_kind": dict(Counter(row["payload"]["kind"] for row in ideas).most_common()),
        "duplicates_by_signal": dict(Counter(row["match"] for row in duplicates).most_common()),
        "duplicates_by_corpus": dict(Counter(row["corpus"] for row in duplicates).most_common()),
        "repository_states": dict(Counter(outcome["state"] for outcome in outcomes).most_common()),
        "phases_seconds": {"discovery": round(discovery_seconds, 1), "sync": round(sync_seconds, 1),
                           "reading": round(reading_seconds, 1)},
        "discovery": [{"engines": report["engines"], "requests": report.get("requests")}
                      for report in discovery_reports],
        "sync": sync_summaries,
        "store": {**store_size, "bytes_per_body_file": round(bytes_per_file, 1),
                  "projected_bodies_bytes_per_100000_files": round(bytes_per_file * 100_000),
                  "projected_records_bytes_per_100000_candidates":
                      round(store_size["records_db"]["bytes"] / max(1, len(kept) + len(ideas)) * 100_000),
                  "unique_body_bytes_of_kept_candidates": body_bytes}}
    index_path = Path(index_path) if index_path else output / "candidate-index.jsonl"
    with index_path.open("w", encoding="utf-8") as stream:
        for payload in sorted(kept, key=lambda row: row["record_id"]):
            source = payload["provenance"]
            stream.write(json.dumps({
                "record_id": payload["record_id"], "kind": payload["kind"], "name": payload["name"],
                "package_digest": payload["package_digest"], "files": len(payload["package"]["files"]),
                "bytes": sum(entry["size_bytes"] for entry in payload["package"]["files"]),
                "repository": source["repository"], "commit": source["immutable_revision"], "path": source["path"],
                "primary_sha256": source["source_digest"], "licence": payload["licence"]["spdx_expression"],
                "effects": payload["declared_effects"], "cautions": len(payload["findings"]),
                "merged_sources": len(payload["merged"]), "supersedes": payload["version"]["supersedes"]},
                sort_keys=True) + "\n")
    import hashlib
    report["candidate_index"] = {"rows": len(kept), "sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
                                 "location": "store folder, outside the repository" if index_path.parent != output
                                 else index_path.name}
    (output / "batch-report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    return report


def _store_size(root: Path) -> dict:
    report = {}
    for part in ("bodies", "quarantine"):
        files = total = 0
        for path in (root / part).rglob("*"):
            if path.is_file() and not path.name.endswith(".partial"):
                files += 1
                total += path.stat().st_size
        report[part] = {"files": files, "bytes": total}
    database = root / "records.db"
    report["records_db"] = {"bytes": database.stat().st_size if database.is_file() else 0}
    return report
