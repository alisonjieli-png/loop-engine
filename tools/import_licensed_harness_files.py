#!/usr/bin/env python3
"""Import licensed harness files as review candidates: discover, sync and report.

See tools/licensed_import/README.md. Three commands, none of which approves,
serves, publishes or installs anything:

```text
import_licensed_harness_files.py
├── discover: run the discovery engines and append leads to a run folder
├── sync: read the leads' repositories, decide licences, check, package, deduplicate and store
└── report: the evidence of a run folder and its store, without any third-party text
```

Network reads need --authorize-network-reads and store writes need
--authorize-store-writes. Put run folders and the store outside the
repository: they hold third-party bytes.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.library_ingestion.github_reader import GhCliReader  # noqa: E402
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport  # noqa: E402
from loop_engine.core.library_ingestion.record_rules import now_utc  # noqa: E402
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog  # noqa: E402

from licensed_import import discovery, dedup  # noqa: E402
from licensed_import.checks import CiscoSkillScanner, StaticChecks  # noqa: E402
from licensed_import.github_api import ApiBudgets, GitHubApi  # noqa: E402
from licensed_import.harness_kinds import SourceScope  # noqa: E402
from licensed_import.report import build_report  # noqa: E402
from licensed_import.snapshots import GitHubApiBlobs, GitPartialClone, SnapshotFailed  # noqa: E402
from licensed_import.sources import read_sources  # noqa: E402
from licensed_import.storage import ImportStore  # noqa: E402
from licensed_import.sync import SyncRound, plan_repositories, resolve_metadata, restricted_refusals  # noqa: E402

DEFAULT_SOURCES = HERE / "licensed_import" / "sources.json"
DISCOVERY_HOSTS = ("clawhub.ai", "registry.npmjs.org", "registry.modelcontextprotocol.io")


def _append(path: Path, rows) -> None:
    with path.open("a", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def _rewrite(path: Path, rows) -> None:
    temporary = path.with_name(path.name + ".partial")
    with temporary.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def _read_jsonl(path: Path) -> list:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _api(run_folder: Path, pause_seconds: float) -> GitHubApi:
    budgets = ApiBudgets(code_search=RequestBudget(100_000, pause_seconds, reserve=0),
                         search=RequestBudget(100_000, pause_seconds, reserve=0),
                         graphql=RequestBudget(100_000, pause_seconds, reserve=200))
    return GitHubApi(budgets, RequestLog(run_folder / "requests.jsonl"))


def _git_reader(run_folder: Path):
    """Reads one file of a repository at its head through the git engine, for list sources."""
    engine = GitPartialClone(run_folder / "work", log_path=run_folder / "git-fetches.jsonl")

    def read(repository: str, path: str):
        try:
            snapshot = engine.open(repository)
        except SnapshotFailed:
            return None
        try:
            wanted = [entry.oid for entry in snapshot.entries if entry.path == path]
            found = engine.read(snapshot, wanted) if wanted else {}
            return found.get(wanted[0]) if wanted else None
        finally:
            engine.close(snapshot)
    return read


def discover(args) -> dict:
    run_folder = Path(args.run_folder).resolve()
    run_folder.mkdir(parents=True, exist_ok=True)
    (run_folder / "work").mkdir(exist_ok=True)
    declaration = read_sources(json.loads(Path(args.sources).read_text(encoding="utf-8")))
    api = _api(run_folder, args.maximum_pause_seconds)
    https = HttpsGetTransport(DISCOVERY_HOSTS, RequestBudget(args.https_request_ceiling, args.maximum_pause_seconds),
                              RequestLog(run_folder / "requests-https.jsonl"))
    cursors_path = run_folder / "cursors.json"
    cursors = json.loads(cursors_path.read_text()) if cursors_path.is_file() else {}
    wanted = set(args.engine or discovery.ENGINE_ORDER)
    report = {"record_type": "licensed_import_discovery_report/v1", "started_at": now_utc(), "engines": {}}
    runners = {
        discovery.DECLARED: lambda: discovery.declared_repositories(declaration),
        discovery.SEEDS: lambda: discovery.resolve_owner_seeds(declaration, api),
        discovery.RESEARCH: lambda: discovery.research_seed_lists(declaration, Path(args.research_root)),
        discovery.CLAWHUB: lambda: discovery.clawhub_feeds(declaration, https),
        discovery.AWESOME: lambda: discovery.awesome_lists(declaration, _git_reader(run_folder)),
        discovery.CODE_SEARCH: lambda: discovery.code_search(declaration, api, query_budget=args.code_search_queries,
                                                             cursor=cursors.get(discovery.CODE_SEARCH)),
        discovery.TOPIC_SEARCH: lambda: discovery.topic_search(declaration, api, query_budget=args.topic_queries,
                                                               cursor=cursors.get(discovery.TOPIC_SEARCH)),
        discovery.NPM: lambda: discovery.npm_search(declaration, https, request_budget=args.npm_requests),
        discovery.REGISTRY: lambda: discovery.registry_updates(declaration, https, request_budget=args.registry_requests,
                                                               cursor=cursors.get(discovery.REGISTRY)),
    }
    for engine in discovery.ENGINE_ORDER:
        if engine not in wanted:
            continue
        started = time.monotonic()
        result = runners[engine]()
        seconds = round(time.monotonic() - started, 1)
        _append(run_folder / "leads.jsonl", result.leads)
        _append(run_folder / "discovery-refusals.jsonl", result.refusals)
        if result.cursor:
            cursors[engine] = result.cursor
            cursors_path.write_text(json.dumps(cursors, indent=1, sort_keys=True))
        if engine == discovery.SEEDS:
            (run_folder / "owner-seeds.json").write_text(json.dumps(result.notes, indent=1, sort_keys=True))
        report["engines"][engine] = {
            "leads": len(result.leads), "repositories": len({row["repository"].lower() for row in result.leads}),
            "refusals": dict(Counter(row["reason"] for row in result.refusals)), "requests": result.requests,
            "seconds": seconds, "notes": result.notes if engine != discovery.SEEDS else len(result.notes)}
        print(json.dumps({"engine": engine, **report["engines"][engine]}, default=str)[:600], flush=True)
    report["finished_at"] = now_utc()
    report["requests"] = {"github": api.log.summary(), "https": https.log.summary()}
    name = f"discovery-report-{report['started_at'].replace(':', '')}.json"
    (run_folder / name).write_text(json.dumps(report, indent=1, sort_keys=True))
    return report


def _corpora(args) -> tuple:
    subjects, counts = [], {}
    if args.corpus_served:
        found = dedup.folder_subjects(dedup.SERVED, args.corpus_served, every_text_file=True)
        subjects += found
        counts[dedup.SERVED] = len(found)
    if args.corpus_artifacts:
        found = dedup.folder_subjects(dedup.ARTIFACTS, args.corpus_artifacts)
        subjects += found
        counts[dedup.ARTIFACTS] = len(found)
    if args.corpus_overnight:
        found = dedup.folder_subjects(dedup.OVERNIGHT, args.corpus_overnight, every_text_file=True)
        subjects += found
        counts[dedup.OVERNIGHT] = len(found)
    for folder in args.corpus_ls1 or ():
        found = dedup.ls1_subjects(Path(folder))
        subjects += [subject for subject in found if subject.key not in {row.key for row in subjects}]
        counts[f"{dedup.LS1}:{Path(folder).name}"] = len(found)
    return subjects, counts


def sync(args) -> dict:
    if not args.authorize_network_reads or not args.authorize_store_writes:
        raise SystemExit("sync needs --authorize-network-reads and --authorize-store-writes")
    run_folder = Path(args.run_folder).resolve()
    declaration = read_sources(json.loads(Path(args.sources).read_text(encoding="utf-8")))
    scopes = {row["source_id"]: SourceScope(tuple(row.get("kinds") or SourceScope().kinds), tuple(row.get("include", ())),
                                            tuple(row.get("exclude", ()))) for row in declaration["repositories"]}
    leads = _read_jsonl(run_folder / "leads.jsonl")
    plans = plan_repositories(leads, scopes, {row["repository"] for row in declaration["excluded_repositories"]})
    if args.max_repositories:
        keep = sorted(plans.values(), key=lambda plan: (plan.priority, -plan.stars, plan.repository.lower()))
        plans = {plan.repository.lower(): plan for plan in keep[:args.max_repositories]}
    api = _api(run_folder, args.maximum_pause_seconds)
    started = time.monotonic()
    metadata_refusals = resolve_metadata(plans, api, run_folder / "metadata.jsonl")
    metadata_seconds = round(time.monotonic() - started, 1)
    store = ImportStore(Path(args.store_root), writes_authorized=True)
    engines = [GitPartialClone(run_folder / "work", log_path=run_folder / "git-fetches.jsonl")]
    if args.api_fallback:
        rest = GhCliReader(RequestBudget(args.rest_request_ceiling, args.maximum_pause_seconds),
                           RequestLog(run_folder / "requests-rest.jsonl"))
        engines.append(GitHubApiBlobs(rest, api))
    checks = StaticChecks({})
    batch_checks = None
    if args.skillspector_program or args.cisco_scanner_program:
        extra = ([CiscoSkillScanner(args.cisco_scanner_program, str(run_folder / "work" / "cisco"))]
                 if args.cisco_scanner_program else [])
        batch_checks = StaticChecks({"skillspector_program": args.skillspector_program or "",
                                     "work_folder": str(run_folder / "work" / "scan")},
                                    extra_engines=extra, switched_off=("builtin_static_rules",))
    near_decision, near = dedup.near_engine({})
    corpora, corpus_counts = _corpora(args)
    round_ = SyncRound(run_folder=run_folder, store=store, snapshot_engines=engines, checks=checks, near=near, api=api,
                       workers=args.workers, time_limit_seconds=args.time_limit_minutes * 60, corpora=corpora,
                       batch_checks=batch_checks, scan_workers=args.scan_workers)
    reading = round_.run(plans)
    outcomes = list(round_.journal.finished().values())
    started_dedup = time.monotonic()
    resolution, candidates = round_.deduplicate(outcomes)
    dedup_seconds = round(time.monotonic() - started_dedup, 1)
    started_scan = time.monotonic()
    scan_refusals = round_.batch_scan(resolution, candidates)
    scan_seconds = round(time.monotonic() - started_scan, 1)
    _rewrite(run_folder / "batch-scan-refusals.jsonl", scan_refusals)
    started_write = time.monotonic()
    written = round_.write(outcomes, resolution, candidates)
    write_seconds = round(time.monotonic() - started_write, 1)
    # Recomputed over every outcome of the round, so a restarted round rewrites them.
    _rewrite(run_folder / "duplicates.jsonl", resolution.links)
    _rewrite(run_folder / "restricted-copies.jsonl", restricted_refusals(resolution, candidates))
    _rewrite(run_folder / "metadata-refusals.jsonl", metadata_refusals)
    summary = {"record_type": "licensed_import_sync_summary/v1", "finished_at": now_utc(),
               "workers": args.workers, "scan_workers": args.scan_workers, "repositories_planned": len(plans), "metadata_seconds": metadata_seconds, "reading": reading,
               "dedup_seconds": dedup_seconds, "batch_scan_seconds": scan_seconds,
               "batch_scan_refusals": len(scan_refusals), "write_seconds": write_seconds, "written": written,
               "kept": len(resolution.kept), "merged": len(resolution.merged_into),
               "restricted_copies": len(resolution.restricted_copies), "supersedes": len(resolution.supersedes),
               "corpora": corpus_counts, "near_duplicate_engine": near_decision["chosen"],
               "check_engines": checks.describe(),
               "batch_check_engines": batch_checks.describe() if batch_checks else None,
               "requests": api.log.summary()}
    (run_folder / f"sync-summary-{summary['finished_at'].replace(':', '')}.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True, default=str))
    store.close()
    print(json.dumps(summary, default=str)[:1500], flush=True)
    return summary


def export_review(args) -> dict:
    """Select, scan and write stored candidates as a catalogue folder the review panel can load."""
    from loop_engine.catalog.query import IntelligenceQuery
    from licensed_import import review_export
    from licensed_import.storage import NAMESPACE
    store = ImportStore(Path(args.store_root), writes_authorized=False)
    try:
        payloads = [row["payload"] for row in store.records.query(
            IntelligenceQuery(namespaces=(NAMESPACE,), lifecycle=("candidate",)))]
        earlier = review_export.exported_record_ids(args.exclude_export or ())
        stored = len(payloads)
        payloads = [payload for payload in payloads if payload["record_id"] not in earlier]
        sizes = {entry["digest"]: entry["size_bytes"] for payload in payloads for entry in payload["package"]["files"]}
        reader = lambda digest: store.bodies.read(digest, sizes[digest])  # noqa: E731
        first_source = {}
        for row in _read_jsonl(Path(args.run_folder) / "leads.jsonl"):
            key = row["repository"].lower()
            if key not in first_source or discovery.SOURCE_PRIORITY.get(row["engine_id"], 99) < \
                    discovery.SOURCE_PRIORITY.get(first_source[key], 99):
                first_source[key] = row["engine_id"]
        chosen, skipped = review_export.select(payloads, first_source, discovery.SOURCE_PRIORITY,
                                               limit=args.limit, per_repository=args.per_repository)
        checks = None
        if args.skillspector_program or args.cisco_scanner_program:
            extra = ([CiscoSkillScanner(args.cisco_scanner_program, str(Path(args.work_folder) / "cisco"))]
                     if args.cisco_scanner_program else [])
            checks = StaticChecks({"skillspector_program": args.skillspector_program or "",
                                   "work_folder": str(Path(args.work_folder) / "scan")},
                                  extra_engines=extra, switched_off=("builtin_static_rules",))
        started = time.monotonic()
        kept, refused = review_export.scan_selection(chosen, reader, checks, target=args.target,
                                                     scan_workers=args.scan_workers)
        summary = {"stored_candidates": stored, "already_exported": len(earlier),
                   "earlier_exports": sorted(Path(folder).name for folder in args.exclude_export or ()),
                   "limit": args.limit, "target": args.target,
                   "per_repository": args.per_repository, "selected": len(chosen),
                   "not_selected": dict(skipped), "scanned": len(chosen) if checks else 0,
                   "scan_seconds": round(time.monotonic() - started, 1),
                   "scan_engines": checks.describe()["engines"] if checks else [],
                   "blocked": dict(Counter(row["detail"] for row in refused).most_common()),
                   "blocked_count": len(refused)}
        report = review_export.export(kept, reader, Path(args.output), code_revision=args.code_revision,
                                      first_source=first_source, summary=summary)
        _rewrite(Path(args.output) / "scan-refusals.jsonl", refused)
    finally:
        store.close()
    print(json.dumps({key: report[key] for key in ("items", "licences", "kinds", "repositories")}, indent=1))
    return report


def report(args) -> dict:
    result = build_report(Path(args.run_folder).resolve(), Path(args.store_root).resolve(), Path(args.output).resolve(),
                          workers=args.workers, index_path=Path(args.index_output).resolve() if args.index_output else None)
    print(json.dumps(result["headline"], indent=1, sort_keys=True))
    return result


def parser() -> argparse.ArgumentParser:
    main = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = main.add_subparsers(dest="command", required=True)
    one = commands.add_parser("discover")
    one.add_argument("--run-folder", required=True)
    one.add_argument("--sources", default=str(DEFAULT_SOURCES))
    one.add_argument("--research-root", default=str(ROOT))
    one.add_argument("--engine", action="append", choices=discovery.ENGINE_ORDER)
    one.add_argument("--authorize-network-reads", action="store_true", required=True)
    one.add_argument("--code-search-queries", type=int, default=60)
    one.add_argument("--topic-queries", type=int, default=30)
    one.add_argument("--npm-requests", type=int, default=20)
    one.add_argument("--registry-requests", type=int, default=50)
    one.add_argument("--https-request-ceiling", type=int, default=500)
    one.add_argument("--maximum-pause-seconds", type=float, default=3700.0)
    two = commands.add_parser("sync")
    two.add_argument("--run-folder", required=True)
    two.add_argument("--store-root", required=True)
    two.add_argument("--sources", default=str(DEFAULT_SOURCES))
    two.add_argument("--authorize-network-reads", action="store_true")
    two.add_argument("--authorize-store-writes", action="store_true")
    two.add_argument("--workers", type=int, default=6)
    two.add_argument("--time-limit-minutes", type=float, default=60.0)
    two.add_argument("--max-repositories", type=int, default=0)
    two.add_argument("--api-fallback", action="store_true")
    two.add_argument("--rest-request-ceiling", type=int, default=1000)
    two.add_argument("--maximum-pause-seconds", type=float, default=3700.0)
    two.add_argument("--scan-workers", type=int, default=8, help="scanner chunk groups run in parallel")
    two.add_argument("--skillspector-program")
    two.add_argument("--cisco-scanner-program")
    two.add_argument("--corpus-served", action="append")
    two.add_argument("--corpus-artifacts", action="append")
    two.add_argument("--corpus-overnight", action="append")
    two.add_argument("--corpus-ls1", action="append")
    four = commands.add_parser("export-review")
    four.add_argument("--run-folder", required=True)
    four.add_argument("--store-root", required=True)
    four.add_argument("--output", required=True, help="a new folder outside the repository")
    four.add_argument("--code-revision", required=True, help="the committed revision of this tool")
    four.add_argument("--limit", type=int, default=2400)
    four.add_argument("--target", type=int, default=2000)
    four.add_argument("--per-repository", type=int, default=15)
    four.add_argument("--work-folder", default="")
    four.add_argument("--exclude-export", action="append", help="an earlier export folder whose items are skipped")
    four.add_argument("--scan-workers", type=int, default=8)
    four.add_argument("--skillspector-program")
    four.add_argument("--cisco-scanner-program")
    three = commands.add_parser("report")
    three.add_argument("--run-folder", required=True)
    three.add_argument("--store-root", required=True)
    three.add_argument("--output", required=True)
    three.add_argument("--workers", type=int, default=8, help="the parallel workers the sync ran with")
    three.add_argument("--index-output", help="write the full candidate index here, outside the repository")
    return main


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    {"discover": discover, "sync": sync, "report": report, "export-review": export_review}[args.command](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
