"""Ingest outside harness material with provenance, and stage it as review-only candidates.

Three commands. None of them approves, serves, publishes or installs anything.

collect reads the curated sources (core/library_ingestion/outside_sources.yaml)
through their source engines with bounded, recorded, read-only requests, runs
the ingestion pipeline and writes one new run folder: the quarantine of
fetched bytes, the request log, each source's batch, the refusals, outlines,
duplicate links and model calls, the specification populations of at most
fifty rows and the run report. It stages nothing.

stage stages a run folder's populations into an isolated candidate database
through the existing staging contract (tools/stage_intelligence_candidates.py),
one atomic batch per population. An identical rerun adds nothing; a changed
candidate stops the run, because a changed candidate is a new review subject.

curate reads the head commit and licence of named repositories, for the
person curating the source list. It changes nothing.

    PYTHONPATH=src python tools/ingest_outside_material.py collect \\
        --run-folder RUN --authorize-network-reads
    PYTHONPATH=src python tools/ingest_outside_material.py stage \\
        --run-folder RUN --database RUN/candidates.db --namespace library.outside \\
        --authorize-isolated-staging

Input rules, limits and the meaning of each count: tools/INGEST-OUTSIDE-MATERIAL.md
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.catalog.query import IntelligenceQuery  # noqa: E402
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore  # noqa: E402
from loop_engine.core.library_ingestion.candidates import candidate_request  # noqa: E402
from loop_engine.core.library_ingestion.engines import (  # noqa: E402
    FACTORIES, FORMAT_SLOT, NEAR_DUPLICATE_SLOT, OUTLINE_SLOT, SAFETY_SLOT, SOURCE_SLOT)
from loop_engine.core.library_ingestion.fetch_cache import PinnedBlobCache  # noqa: E402
from loop_engine.core.library_ingestion.github_reader import GhCliReader  # noqa: E402
from loop_engine.core.library_ingestion.https_transport import HttpsGetTransport  # noqa: E402
from loop_engine.core.library_ingestion.licences import match_licence  # noqa: E402
from loop_engine.core.library_ingestion.package_resolver import NPM_HOST, PYPI_HOST, PackageResolver  # noqa: E402
from loop_engine.core.library_ingestion.pipeline import PipelineEngines, PipelineSettings, run_pipeline  # noqa: E402
from loop_engine.core.library_ingestion.quarantine import Quarantine  # noqa: E402
from loop_engine.core.library_ingestion.record_rules import bytes_digest, canonical_digest, now_utc  # noqa: E402
from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog  # noqa: E402
from loop_engine.core.library_ingestion.selection import select_engines  # noqa: E402
from loop_engine.core.library_ingestion.source_declarations import (  # noqa: E402
    GITHUB_ENGINE, load_sources, read_sources)
from loop_engine.core.library_ingestion.staging_rows import populations  # noqa: E402
from tools.stage_intelligence_candidates import (  # noqa: E402
    CandidateStageRequest, compile_candidates, review_search, stage_candidates)

RUN_REPORT_RECORD_TYPE = "library_ingestion_run_report/v1"
STAGING_REPORT_RECORD_TYPE = "library_ingestion_staging_report/v1"
CURATION_RECORD_TYPE = "library_source_curation/v1"
LIMITS = ("Candidates only. Nothing here is approved, served or published; every staged row needs an "
          "independent review of its exact bytes. Licence decisions are engineering rules, not legal "
          "advice. A registry entry is link-only and its upstream code was not read. Scanner findings are "
          "triage for reviewers, not safety proof.")


class StagingConflict(RuntimeError):
    """A population was partly staged, or a staged candidate changed; nothing continues automatically."""


@dataclass(frozen=True)
class CollectOptions:
    """One collect run: its new folder, its authority and its ceilings."""

    run_folder: Path
    network_reads_authorized: bool = False
    source_ids: tuple = ()
    maximum_candidates_per_source: int = 5000
    github_request_ceiling: int = 4000
    https_request_ceiling: int = 400
    maximum_pause_seconds: float = 900.0
    upstream_licence_lookups: int = 0
    package_checks: bool = False
    skillspector_program: str = ""
    model_calls_authorized: bool = False
    outline_model: str = ""
    model_call_ceiling: int = 0
    near_duplicate_threshold: float = 0.85
    reuse_run_folders: tuple = ()


COMPONENT_FOLDER = Path("src/loop_engine/core/library_ingestion")
COMPONENT_TOOLS = (Path("tools/ingest_outside_material.py"), Path("tools/stage_intelligence_candidates.py"))


def code_identity(repository: Path) -> dict:
    """Which code produced a run: the revision, a digest of the component's files and whether they differ.

    The digest covers every file of the component folder and the two tools by
    path and bytes, so two runs with the same digest ran the same code even
    when the revision alone would not say so.
    """
    files = sorted(path for path in (repository / COMPONENT_FOLDER).iterdir()
                   if path.is_file() and path.suffix in (".py", ".json", ".yaml"))
    files += [repository / path for path in COMPONENT_TOOLS]
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(repository)).encode() + b"\0" + path.read_bytes() + b"\0")

    def git(*arguments):
        try:
            return subprocess.run(["git", "-C", str(repository), *arguments], capture_output=True,
                                  check=False, timeout=30).stdout.decode("utf-8", "replace").strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    changed = git("status", "--porcelain", "--", str(COMPONENT_FOLDER), *(str(path) for path in COMPONENT_TOOLS))
    return {"revision": git("rev-parse", "HEAD") or None, "component_digest": digest.hexdigest(),
            "component_files": len(files), "uncommitted_changes": bool(changed)}


def _write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=False)
        stream.write("\n")


def _write_lines(path: Path, rows) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def _schemas(record: dict, github_reader, https_transport, quarantine) -> tuple:
    """Read each pinned connection schema; a changed digest is recorded, never used."""
    resources, digests = {}, {}
    for row in record["schemas"]:
        data = None
        if row["repository"] and github_reader is not None:
            answer = github_reader.get(f"repos/{row['repository']}/contents/{row['path']}?ref={row['commit']}")
            if answer.status == 200:
                data = base64.b64decode(json.loads(answer.body).get("content", ""))
        elif https_transport is not None and row["host"] in https_transport.hosts:
            answer = https_transport.get(row["host"], "/" + row["path"])
            data = answer.body if answer.status == 200 else None
        observed = bytes_digest(data) if data is not None else None
        digests[row["schema_id"]] = {"expected": row["sha256"], "observed": observed, "licence": row["licence"]}
        if data is not None:
            quarantine.put(data)
            resources[row["schema_id"]] = {"bytes": data, "sha256": row["sha256"]}
    return resources, digests


def _select(settings: dict, resources: dict) -> tuple:
    decisions, engines = [], {}
    for slot in (SOURCE_SLOT, FORMAT_SLOT, SAFETY_SLOT, NEAR_DUPLICATE_SLOT, OUTLINE_SLOT):
        decision, chosen = select_engines(slot, FACTORIES[slot.slot_id], settings)
        decisions.append(decision)
        engines[slot.slot_id] = [factory.from_settings(settings, resources) for factory in chosen]
    return decisions, engines


def collect(sources_record: dict, options: CollectOptions, *, github_reader=None, registry_transport=None,
            request_log=None) -> dict:
    """Read the sources, run the pipeline and write one new run folder. Stages nothing."""
    record = read_sources(sources_record)
    run = Path(options.run_folder)
    run.mkdir(parents=True, exist_ok=False)
    started = now_utc()
    # Read before anything else runs, so the record names the code that did the work.
    code = code_identity(Path(__file__).resolve().parents[1])
    log = request_log or RequestLog(run / "requests.jsonl")
    github_budget = RequestBudget(options.github_request_ceiling, options.maximum_pause_seconds, reserve=300)
    https_budget = RequestBudget(options.https_request_ceiling, options.maximum_pause_seconds)
    quarantine = Quarantine(run / "quarantine")
    registry_hosts = {row["host"] for row in record["sources"] if row["engine"] != GITHUB_ENGINE}
    schema_hosts = {row["host"] for row in record["schemas"] if not row["repository"]}
    if options.network_reads_authorized:
        github_reader = github_reader or GhCliReader(github_budget, log)
        hosts = registry_hosts | schema_hosts | ({NPM_HOST, PYPI_HOST} if options.package_checks else set())
        registry_transport = registry_transport or HttpsGetTransport(sorted(hosts), https_budget, log)
    schema_resources, schema_digests = _schemas(record, github_reader, registry_transport, quarantine)
    settings = {"network_reads_authorized": options.network_reads_authorized,
                "github_reader_configured": github_reader is not None,
                "registry_transport_configured": registry_transport is not None,
                "upstream_licence_lookups": options.upstream_licence_lookups,
                "schema_digests": schema_digests, "skillspector_program": options.skillspector_program,
                "work_folder": str(run / "work"), "model_calls_authorized": options.model_calls_authorized,
                "outline_model": options.outline_model, "model_call_ceiling": options.model_call_ceiling,
                "maximum_pause_seconds": options.maximum_pause_seconds,
                "model_call_log": str(run / "model-calls.jsonl")}
    blob_cache = PinnedBlobCache.from_run_folders(options.reuse_run_folders) if options.reuse_run_folders else None
    resources = {"github_reader": github_reader, "registry_transport": registry_transport,
                 "quarantine": quarantine, "schemas": schema_resources, "blob_cache": blob_cache}
    decisions, engines = _select(settings, resources)
    sources = {engine.engine_id: engine for engine in engines[SOURCE_SLOT.slot_id]}
    (run / "batches").mkdir()
    batches, source_rows = [], []
    for declaration in record["sources"]:
        if options.source_ids and declaration["source_id"] not in options.source_ids:
            continue
        engine = sources.get(declaration["engine"])
        if engine is None:
            source_rows.append({"source_id": declaration["source_id"], "read": False,
                                "reason": "its source engine is not eligible in this run"})
            continue
        request = candidate_request(declaration["source_id"], requested_at=now_utc(),
                                    maximum_candidates=options.maximum_candidates_per_source,
                                    maximum_requests=options.github_request_ceiling + options.https_request_ceiling,
                                    network_reads_authorized=options.network_reads_authorized)
        batch = engine.read_candidates(declaration, request)
        _write_json(run / "batches" / f"{declaration['source_id']}.json", batch)
        batches.append(batch)
        source_rows.append({"source_id": declaration["source_id"], "engine": declaration["engine"],
                            "repository": declaration.get("repository") or declaration.get("host"),
                            "commit": declaration.get("commit"), "use": declaration["use"],
                            "complete": batch["complete"], "stopped_reason": batch["stopped_reason"],
                            "next_cursor": batch["next_cursor"], "candidates": len(batch["candidates"]),
                            "refusals": len(batch["refusals"]), "requests_made": batch["requests_made"]})
    resolver = PackageResolver(registry_transport) if options.package_checks and registry_transport else None
    outline_engines = engines[OUTLINE_SLOT.slot_id]
    # The last engine of the declared order is the fallback: it needs no authority and
    # is named here only through the factory table, like every other engine.
    fallback = FACTORIES[OUTLINE_SLOT.slot_id][OUTLINE_SLOT.declared_order[-1]].from_settings(settings, resources)
    pipeline_engines = PipelineEngines(
        validators=tuple(engines[FORMAT_SLOT.slot_id]), scanners=tuple(engines[SAFETY_SLOT.slot_id]),
        near_duplicate=engines[NEAR_DUPLICATE_SLOT.slot_id][0], outline=outline_engines[0],
        fallback_outline=fallback, package_resolver=resolver, decisions=tuple(decisions))
    order = tuple(row["source_id"] for row in record["sources"])
    result = run_pipeline(batches, quarantine, pipeline_engines,
                          PipelineSettings(near_duplicate_threshold=options.near_duplicate_threshold,
                                           source_order=order))
    (run / "populations").mkdir()
    documents = populations(result["rows"])
    for document in documents:
        _write_json(run / "populations" / f"specifications-{document['population']:03d}.json", document)
    _write_lines(run / "refusals.jsonl", result["refusals"])
    _write_lines(run / "outlines.jsonl", result["outlines"])
    _write_lines(run / "duplicates.jsonl", result["duplicates"])
    calls_file = run / "model-calls.jsonl"
    if calls_file.exists():
        # The outline engine wrote each call down as it returned; the file must hold exactly those calls.
        written = [json.loads(line) for line in calls_file.read_text(encoding="utf-8").splitlines()]
        if written != result["model_calls"]:
            raise RuntimeError("the model call log does not hold exactly the calls this run made")
    else:
        _write_lines(calls_file, result["model_calls"])
    _write_json(run / "engine-decisions.json", decisions)
    calls = result["model_calls"]
    report = {"record_type": RUN_REPORT_RECORD_TYPE, "started_at": started, "finished_at": now_utc(),
              "code": code,
              "sources_record_digest": canonical_digest(record), "sources": source_rows,
              "counts": result["counts"],
              "requests": {**log.summary(), "github": {"ceiling": github_budget.maximum_requests,
                                                      "used": github_budget.used, "pauses": github_budget.pauses},
                           "https": {"ceiling": https_budget.maximum_requests, "used": https_budget.used,
                                     "pauses": https_budget.pauses}},
              "engines": {"decisions": [{key: decision[key] for key in ("slot_id", "chosen", "eligibility",
                                                                         "decision_digest")}
                                        for decision in decisions],
                          "described": {slot: [engine.describe() for engine in chosen]
                                        for slot, chosen in engines.items()}},
              "schemas": schema_digests,
              "reused_fetches": blob_cache.describe() if blob_cache is not None else None,
              "model_calls": model_call_summary(calls, options),
              "populations": [{"file": f"populations/specifications-{document['population']:03d}.json",
                               "rows": len(document["specifications"])} for document in documents],
              "approved": False, "hosted_publication": False, "limits": LIMITS}
    _write_json(run / "run-report.json", report)
    return report


def model_call_summary(calls, options: CollectOptions) -> dict:
    """Counts of the run's model calls. Token sums cover only calls whose usage the provider reported.

    A call without reported usage is counted apart and makes the sums a lower
    bound, which usage_complete says; it is never added as zero.
    """
    reported = [row for row in calls if row["usage_reported"]]
    return {"calls": len(calls), "ceiling": options.model_call_ceiling, "model": options.outline_model or None,
            "outcomes": dict(Counter(row["outcome"] for row in calls)),
            "calls_with_reported_usage": len(reported), "calls_without_reported_usage": len(calls) - len(reported),
            "usage_complete": len(reported) == len(calls),
            "prompt_tokens_of_reported_calls": sum(row["usage"]["prompt_tokens"] for row in reported)
            if reported else None,
            "completion_tokens_of_reported_calls": sum(row["usage"]["completion_tokens"] for row in reported)
            if reported else None}


def stage_populations(store, documents, request: CandidateStageRequest) -> list:
    """Stage each population as one atomic batch; an identical rerun adds nothing, a change stops."""
    results = []
    for document in documents:
        records = compile_candidates(document, request)
        existing = [store.get(row["record_id"]) for row in records]
        if all(item is None for item in existing):
            acknowledgment = stage_candidates(store, records, request)
            results.append({"population": document["population"], "state": "staged", "records": len(records),
                            "batch_digest": acknowledgment.batch_digest})
        elif all(item == row for item, row in zip(existing, records)):
            results.append({"population": document["population"], "state": "already_staged",
                            "records": len(records), "batch_digest": None})
        else:
            raise StagingConflict(f"population {document['population']} was partly staged or a staged "
                                  "candidate changed; a changed candidate is a new review subject and needs "
                                  "a decision, so staging does not continue")
    return results


def stage(run_folder: Path, database: Path, namespace: str, repository: Path) -> dict:
    documents = [json.loads(path.read_text(encoding="utf-8"))
                 for path in sorted((run_folder / "populations").glob("specifications-*.json"))]
    request = CandidateStageRequest(repository, namespace, True)
    with closing(SQLiteRecordStore(str(database))) as store:
        results = stage_populations(store, documents, request)
        staged = store.query(IntelligenceQuery(namespaces=(namespace,), lifecycle=("candidate",)))
    probes = hits = excluded = 0
    for start in range(0, len(staged), 50):
        search = review_search(staged[start:start + 50])
        hits += search["normal_search_hits"]
        excluded += search["normal_search_excluded"]
        probes += sum(1 for row in search["probes"] if row["found_in_first_three"])
    report = {"record_type": STAGING_REPORT_RECORD_TYPE, "staged_at": now_utc(), "database": str(database),
              "namespace": namespace, "populations": results, "records_in_namespace": len(staged),
              "normal_search_hits": hits, "normal_search_excluded": excluded,
              "title_probes_found_in_first_three": probes, "approved": False, "hosted_publication": False}
    target = run_folder / f"staging-report-{report['staged_at'].replace(':', '')}.json"
    _write_json(target, report)
    return report


def curate(repositories, reader) -> list:
    """The head commit and the licence evidence of each repository, for a person curating sources."""
    rows = []
    for repository in repositories:
        meta = reader.get(f"repos/{repository}")
        if meta.status != 200:
            rows.append({"repository": repository, "readable": False})
            continue
        branch = json.loads(meta.body)["default_branch"]
        head = json.loads(reader.get(f"repos/{repository}/commits/{branch}").body)["sha"]
        answer = reader.get(f"repos/{repository}/license?ref={head}")
        row = {"record_type": CURATION_RECORD_TYPE, "repository": repository, "readable": True,
               "branch": branch, "commit": head, "licence_file": None, "github_spdx_id": None,
               "matched_spdx": None, "similarity": None}
        if answer.status == 200:
            body = json.loads(answer.body)
            text = base64.b64decode(body.get("content", "")).decode("utf-8", "replace")
            match = match_licence(text)
            row.update(licence_file=body.get("path"), licence_sha256=bytes_digest(text.encode()),
                       github_spdx_id=(body.get("license") or {}).get("spdx_id"),
                       matched_spdx=match.spdx, similarity=match.similarity)
        rows.append(row)
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    gather = commands.add_parser("collect", help="read sources, run the pipeline, write a new run folder")
    gather.add_argument("--run-folder", type=Path, required=True)
    gather.add_argument("--sources", type=Path, help="a library_outside_sources/v1 file; the curated list by default")
    gather.add_argument("--source-id", action="append", default=[])
    gather.add_argument("--authorize-network-reads", action="store_true")
    gather.add_argument("--maximum-candidates-per-source", type=int, default=5000)
    gather.add_argument("--github-request-ceiling", type=int, default=4000)
    gather.add_argument("--https-request-ceiling", type=int, default=400)
    gather.add_argument("--maximum-pause-seconds", type=float, default=900.0)
    gather.add_argument("--upstream-licence-lookups", type=int, default=0)
    gather.add_argument("--package-checks", action="store_true")
    gather.add_argument("--skillspector-program", default="")
    gather.add_argument("--authorize-model-calls", action="store_true")
    gather.add_argument("--outline-model", default="")
    gather.add_argument("--model-call-ceiling", type=int, default=0)
    gather.add_argument("--reuse-fetched-bytes-from", type=Path, action="append", default=[],
                        help="an earlier run folder whose verified pinned bytes may be reused; repeatable")
    put = commands.add_parser("stage", help="stage a run folder's populations into an isolated database")
    put.add_argument("--run-folder", type=Path, required=True)
    put.add_argument("--database", type=Path, required=True)
    put.add_argument("--namespace", required=True)
    put.add_argument("--authorize-isolated-staging", action="store_true")
    look = commands.add_parser("curate", help="read head commits and licences for curation")
    look.add_argument("--repository", action="append", required=True)
    look.add_argument("--authorize-network-reads", action="store_true")
    options = parser.parse_args(argv)
    if options.command == "collect":
        if not options.authorize_network_reads:
            parser.error("collect reads public sources over the network; pass --authorize-network-reads")
        record = load_sources(options.sources) if options.sources else load_sources()
        report = collect(record, CollectOptions(
            options.run_folder, True, tuple(options.source_id), options.maximum_candidates_per_source,
            options.github_request_ceiling, options.https_request_ceiling, options.maximum_pause_seconds,
            options.upstream_licence_lookups, options.package_checks, options.skillspector_program,
            options.authorize_model_calls, options.outline_model, options.model_call_ceiling,
            reuse_run_folders=tuple(options.reuse_fetched_bytes_from)))
        print(json.dumps({"counts": report["counts"], "requests": report["requests"]["requests"]}, indent=2))
        return 0
    if options.command == "stage":
        if not options.authorize_isolated_staging:
            parser.error("staging writes an isolated database; pass --authorize-isolated-staging")
        report = stage(options.run_folder, options.database, options.namespace,
                       Path(__file__).resolve().parents[1])
        print(json.dumps({key: report[key] for key in ("records_in_namespace", "normal_search_hits",
                                                       "title_probes_found_in_first_three")}))
        return 0 if report["normal_search_hits"] == 0 else 1
    if not options.authorize_network_reads:
        parser.error("curate reads public repositories; pass --authorize-network-reads")
    log = RequestLog()
    rows = curate(options.repository, GhCliReader(RequestBudget(4 * len(options.repository) + 4), log))
    print(json.dumps({"curation": rows, "requests": log.summary()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
