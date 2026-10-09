"""Bounded multi-cohort driver over the existing constraint-case supply Loop.

Each child is a canonical Starting Practitioner batch. This adapter adds no
runtime, catalogue, model call or publication path. Frozen source populations,
cross-shard exclusions and cumulative limits survive clean restarts. An
unanswered dispatch is held for reconciliation, never automatically replayed.
"""
from datetime import datetime, timezone
from contextlib import contextmanager
from enum import Enum
import fcntl
from pathlib import Path
import shutil
import signal
import time
from types import SimpleNamespace

from loop_engine.core.service_runtime.catalogue_bundle import strict_json
from . import api_contract_run as atomic
from . import constraint_case_exclusions as exclusions
from . import constraint_case_run as cases
from . import constraint_case_runtime as runtime

PLAN_TYPE = "api_constraint_campaign_plan/v1"
EVENT_TYPE = "api_constraint_campaign_event/v1"
REPORT_TYPE = "api_constraint_campaign_report/v1"
MAXIMUM_RECORD_BYTES = 16 * 1024 * 1024


class CampaignEventKind(str, Enum):
    DISPATCH = "dispatch"
    RESULT = "result"
    CHECKPOINT = "checkpoint"
    HELD = "held"


@contextmanager
def batch_deadline(seconds):
    """A POSIX main-process deadline; never replace an already active timer."""
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise ValueError("campaign_timer_already_owned")
    previous = signal.getsignal(signal.SIGALRM)
    def expired(_signum, _frame):
        raise TimeoutError("campaign_batch_wall_deadline")
    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def read_record(path, maximum=MAXIMUM_RECORD_BYTES):
    path = atomic._safe_path(path)
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError("campaign_record_bound")
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError("campaign_record_bound")
    return strict_json(raw, "campaign_record_json")


def plan(args, revision, generator_digest):
    integers = ((args.shard_size, 1, 1000), (args.maximum_contracts, 1, 100_000),
                (args.maximum_cases, 1, exclusions.MAXIMUM_JOBS),
                (args.maximum_invocations, 1, 10_000), (args.maximum_campaign_seconds, 1, 43_200),
                (args.maximum_candidate_bytes, 1, 128 * 1024 ** 3), (args.batch_size, 1, 1000),
                (args.max_batches, 1, 10_000))
    if any(type(value) is not int or not low <= value <= high for value, low, high in integers):
        raise ValueError("campaign_bounds_invalid")
    if not 0 < args.maximum_seconds <= 3600 or not 0 < args.minimum_free_gigabytes <= 10000:
        raise ValueError("campaign_time_or_disk_bound")
    wall_seconds = getattr(args, "maximum_batch_wall_seconds", 180)
    if type(wall_seconds) is not int or not 1 <= wall_seconds <= 3600:
        raise ValueError("campaign_batch_wall_bound")
    sources, shards, total = [], [], 0
    root = atomic._safe_path(args.run_folder)
    if root in (Path(root.anchor), Path.home()):
        raise ValueError("campaign_explicit_output_folder_required")
    for folder in sorted({str(atomic._safe_path(value)) for value in args.parent_run}):
        source = Path(folder)
        if root == source or root in source.parents or source in root.parents:
            raise ValueError("campaign_output_overlaps_source")
        parents = cases.inputs([source], args.maximum_contracts)
        total += len(parents)
        if total > args.maximum_contracts:
            raise ValueError("campaign_parent_population_bound")
        digest = runtime.fingerprint([row[0] for row in parents])
        sources.append({"folder": folder, "parents": len(parents), "population_sha256": digest})
        for offset in range(0, len(parents), args.shard_size):
            shards.append({"index": len(shards), "source": len(sources) - 1,
                           "offset": offset, "parents": min(args.shard_size, len(parents) - offset)})
    _, known = exclusions.read(args.exclude_case_jobs)
    if args.maximum_cases + (known["case_jobs"] if known else 0) > exclusions.MAXIMUM_JOBS:
        raise ValueError("campaign_exclusion_capacity_exceeded")
    result = {"record_type": PLAN_TYPE, "generator_revision": revision, "generator_digest": generator_digest,
              "sources": sources, "shards": shards, "source_contracts": total, "initial_exclusions": known,
              "maximum_cases": args.maximum_cases, "maximum_candidate_bytes": args.maximum_candidate_bytes,
              "maximum_invocations": args.maximum_invocations, "maximum_campaign_seconds": args.maximum_campaign_seconds,
              "minimum_free_gigabytes": args.minimum_free_gigabytes,
              "batch_size": args.batch_size, "batch_seconds": args.maximum_seconds,
              "batch_wall_seconds": wall_seconds,
              "network_calls_authorized": 0, "model_calls_authorized": 0, "publication_authorized": False}
    if len(runtime.encode(result)) > MAXIMUM_RECORD_BYTES:
        raise ValueError("campaign_plan_byte_bound")
    return result


def events(path):
    if not path.exists():
        return []
    if path.stat().st_size > atomic.MAXIMUM_JOURNAL_BYTES:
        raise ValueError("campaign_journal_byte_bound")
    rows = []
    with path.open("rb") as stream:
        for raw in stream:
            if len(raw) > MAXIMUM_RECORD_BYTES or not raw.endswith(b"\n"):
                raise ValueError("campaign_journal_incomplete")
            row = strict_json(raw, "campaign_event_json")
            if (row.get("record_type") != EVENT_TYPE or row.get("sequence") != len(rows)
                    or row.get("previous_sha256") != (runtime.fingerprint(rows[-1]) if rows else "")
                    or row.get("kind") not in tuple(CampaignEventKind)):
                raise ValueError("campaign_journal_chain")
            rows.append(row)
    return rows


def append(path, rows, kind, **fields):
    atomic._append(path, rows, {"record_type": EVENT_TYPE, "kind": CampaignEventKind(kind).value,
                               "at": datetime.now(timezone.utc).isoformat(), **fields})


def state(root, rows, source_plan, verified_snapshots=None):
    """Reconcile report bindings and dispatch/result ordering before more work."""
    starts, latest, checkpoints, pending, held, invocations = {}, {}, {}, None, None, 0
    for row in rows:
        shard = row.get("shard")
        if type(shard) is not int or not 0 <= shard < len(source_plan["shards"]):
            raise ValueError("campaign_shard_invalid")
        kind = CampaignEventKind(row["kind"])
        if held is not None:
            raise ValueError("campaign_event_after_hold")
        if kind is CampaignEventKind.DISPATCH:
            if pending is not None or shard in checkpoints or shard != len(checkpoints):
                raise ValueError("campaign_dispatch_order")
            if row.get("invocation") != invocations + 1:
                raise ValueError("campaign_invocation_order")
            invocations += 1
            starts.setdefault(shard, row)
            first = starts[shard]
            if any(row[key] != first[key] for key in ("case_budget", "byte_budget", "exclusions")):
                raise ValueError("campaign_shard_budget_changed")
            if row["case_budget"] > source_plan["maximum_cases"] or row["byte_budget"] > source_plan["maximum_candidate_bytes"]:
                raise ValueError("campaign_budget_exceeds_plan")
            pending = row
        elif kind is CampaignEventKind.RESULT:
            if pending is None or row.get("invocation") != pending["invocation"] or shard != pending["shard"]:
                raise ValueError("campaign_result_without_dispatch")
            path = root / "receipts" / (str(row["invocation"]).zfill(8) + ".json")
            report = read_record(path)
            if runtime.fingerprint(report) != row.get("report_sha256"):
                raise ValueError("campaign_receipt_changed")
            if (report["case_jobs"] > pending["case_budget"] or report["retained_and_candidate_bytes"] > pending["byte_budget"]
                    or report["approved"] or report["published"] or report["model_calls"] or report["network_calls"]
                    or report["loop_execution"]["failed"]):
                raise ValueError("campaign_child_outside_scope")
            latest[shard], pending = report, None
        elif kind is CampaignEventKind.CHECKPOINT:
            if pending is not None or shard in checkpoints or not latest.get(shard, {}).get("complete"):
                raise ValueError("campaign_checkpoint_order")
            path = root / "exclusions" / (str(shard).zfill(6) + ".json")
            atomic._safe_path(path)
            info = path.stat()
            stamp = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            cached = verified_snapshots.get(str(path)) if verified_snapshots is not None else None
            if cached is not None and cached[0] == stamp:
                binding = cached[1]
            else:
                _, binding = exclusions.read(path)
                if verified_snapshots is not None:
                    verified_snapshots[str(path)] = (stamp, binding)
            if binding != row.get("exclusions"):
                raise ValueError("campaign_exclusion_snapshot_changed")
            checkpoints[shard] = row
        else:
            held, pending = row, None
    if sum(row["case_jobs"] for row in latest.values()) > source_plan["maximum_cases"] or sum(
            row["retained_and_candidate_bytes"] for row in latest.values()) > source_plan["maximum_candidate_bytes"]:
        raise ValueError("campaign_cumulative_budget_exceeded")
    return starts, latest, checkpoints, pending, held, invocations


def run(args, *, revision, licence_text, generator_digest):
    frozen = plan(args, revision, generator_digest)
    if not args.authorize_output_writes:
        return {"record_type": REPORT_TYPE, "plan": frozen, "written": False}
    if "+uncommitted" in revision:
        raise ValueError("campaign_committed_generator_required")
    root = atomic._safe_path(args.run_folder)
    root.mkdir(parents=True, exist_ok=True)
    with atomic._safe_path(root / "campaign.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        header = root / "campaign.json"
        if header.exists():
            record = read_record(header)
            if record["plan"] != frozen:
                raise ValueError("campaign_resume_plan_changed")
        else:
            if any(path.name != "campaign.lock" for path in root.iterdir()):
                raise ValueError("campaign_output_already_contains_unowned_files")
            started = datetime.now(timezone.utc)
            record = {"plan": frozen, "started_at": started.isoformat(),
                      "deadline_epoch": started.timestamp() + frozen["maximum_campaign_seconds"]}
            atomic._write_exact(header, runtime.encode(record))
        started = datetime.fromisoformat(record["started_at"])
        if (started.tzinfo is None or record["deadline_epoch"] != started.timestamp() + frozen["maximum_campaign_seconds"]):
            raise ValueError("campaign_deadline_binding_changed")
        journal = atomic._safe_path(root / "campaign-events.jsonl")
        rows = events(journal)
        if rows and started > datetime.fromisoformat(rows[0]["at"]):
            raise ValueError("campaign_start_after_first_dispatch")
        # These campaign outputs have an exclusive writer and are immutable.
        # Recheck changed filesystem identities and start with an empty cache
        # on every invocation; do not repeatedly parse all earlier job sets.
        verified_snapshots = {}
        attempts, reason = 0, "invocation_batch_limit"
        while True:
            starts, latest, checkpoints, pending, held, invocation = state(root, rows, frozen, verified_snapshots)
            if pending is not None:
                raise ValueError("campaign_unanswered_dispatch_requires_reconciliation")
            if held is not None:
                reason = "held_child"; break
            if len(checkpoints) == len(frozen["shards"]):
                reason = "complete"; break
            shard = frozen["shards"][len(checkpoints)]
            number, last = shard["index"], latest.get(shard["index"])
            prior = frozen["initial_exclusions"] if not checkpoints else checkpoints[number - 1]["exclusions"]
            folder = root / "shards" / str(number).zfill(6)
            if last is not None and last["complete"]:
                package_root = folder / "packages"
                groups = sorted(package_root.iterdir()) if package_root.exists() else []
                snapshot = exclusions.snapshot(groups, previous=prior["path"] if prior else None)
                target = root / "exclusions" / (str(number).zfill(6) + ".json")
                binding = exclusions.write(target, snapshot)
                append(journal, rows, CampaignEventKind.CHECKPOINT, shard=number, exclusions=binding)
                continue
            if attempts >= args.max_batches:
                break
            if time.time() >= record["deadline_epoch"]:
                reason = "campaign_deadline"; break
            if invocation >= frozen["maximum_invocations"]:
                reason = "campaign_invocation_ceiling"; break
            if shutil.disk_usage(root).free < args.minimum_free_gigabytes * 1024 ** 3:
                reason = "free_space_floor"; break
            used_cases = sum(value["case_jobs"] for value in latest.values())
            used_bytes = sum(value["retained_and_candidate_bytes"] for value in latest.values())
            first = starts.get(number)
            case_budget = first["case_budget"] if first else frozen["maximum_cases"] - used_cases
            byte_budget = first["byte_budget"] if first else frozen["maximum_candidate_bytes"] - used_bytes
            if min(case_budget, byte_budget) <= 0:
                reason = "campaign_case_or_byte_ceiling"; break
            source = frozen["sources"][shard["source"]]
            child = SimpleNamespace(parent_run=[source["folder"]], run_folder=folder,
                maximum_contracts=source["parents"], parent_offset=shard["offset"], parent_limit=shard["parents"],
                expected_parent_population=source["population_sha256"], exclude_case_jobs=prior["path"] if prior else None,
                maximum_cases=case_budget, maximum_candidate_bytes=byte_budget, batch_size=args.batch_size,
                maximum_seconds=min(args.maximum_seconds, max(0.001, record["deadline_epoch"] - time.time())),
                authorize_output_writes=True)
            append(journal, rows, CampaignEventKind.DISPATCH, shard=number, invocation=invocation + 1,
                   case_budget=case_budget, byte_budget=byte_budget, exclusions=prior)
            attempts += 1
            try:
                with batch_deadline(min(frozen["batch_wall_seconds"], max(0.001, record["deadline_epoch"] - time.time()))):
                    report = cases.run_as_loop(child, revision=revision, licence_text=licence_text, generator_digest=generator_digest)
            except Exception as error:
                append(journal, rows, CampaignEventKind.HELD, shard=number, failure_class=type(error).__name__)
                reason = "held_child"; break
            target = root / "receipts" / (str(invocation + 1).zfill(8) + ".json")
            atomic._write_exact(target, runtime.encode(report))
            append(journal, rows, CampaignEventKind.RESULT, shard=number, invocation=invocation + 1, report_sha256=runtime.fingerprint(report))
            print(runtime.encode({"shard": number, "invocation": invocation + 1, "cursor": report["next_cursor"],
                                  "case_jobs": report["case_jobs"], "complete": report["complete"]}).decode(), flush=True)
            if report["ceiling"] or (not report["complete"] and report["parents_this_invocation"] == 0):
                append(journal, rows, CampaignEventKind.HELD, shard=number, failure_class="native_bound_or_no_progress")
                reason = "held_child"; break
        _, latest, checkpoints, pending, held, invocation = state(root, rows, frozen, verified_snapshots)
        result = {"record_type": REPORT_TYPE, "complete": reason == "complete", "stopped_by": reason,
                  "source_contracts": frozen["source_contracts"], "shards": len(frozen["shards"]),
                  "completed_shards": len(checkpoints), "invocations": invocation, "invocations_this_call": attempts,
                  "new_case_jobs": sum(row["case_jobs"] for row in latest.values()),
                  "candidate_groups": sum(row["groups"] for row in latest.values()),
                  "retained_and_candidate_bytes": sum(row["retained_and_candidate_bytes"] for row in latest.values()),
                  "cross_shard_case_jobs_excluded": True, "distinct_total_payloads": None,
                  "payload_count_limit": "Global file-digest accounting is separate; shard totals must not be added as unique files",
                  "model_calls": 0, "network_calls": 0, "admitted": False, "published": False,
                  "novelty_scope": "New case jobs relative to the frozen initial exclusions and earlier shards, not universal originality"}
        atomic._write_exact(root / ("campaign-report-" + str(time.time_ns()) + ".json"), runtime.encode(result))
        return result
