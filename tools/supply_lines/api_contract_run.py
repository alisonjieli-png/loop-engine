"""Bounded resumable local pilot, using the existing supply candidate packages.

This is a supply-line run record and journal, not a second catalogue or runtime.
Only the requested output folder is written. No import-store/admission/provider
write is available. Exact packages remain inputs to the existing qualification.
"""
from __future__ import annotations

from collections import Counter
from enum import Enum
import fcntl
import hashlib
import itertools
import json
import os
from pathlib import Path
import tempfile
import time

from loop_engine.core.library_ingestion.record_rules import now_utc
from loop_engine.core.workspace_local import _atomic_write

from . import api_contract_atoms as atom_line
from . import api_contract_sources
from .records import JSON_SCHEMAS, RUN_RECORD_TYPE, SupplyRecordError, read_supply_candidate

PLAN_TYPE = "api_contract_supply_plan/v1"
EVENT_TYPE = "api_contract_supply_event/v2"
RETAINED_TYPE = "api_contract_retained_atom/v1"
MAXIMUM_JOURNAL_BYTES = 64 * 1024 * 1024
MAXIMUM_OUTPUT_PATHS = 1_000_000


class AtomOutcome(str, Enum):
    CANDIDATE = "candidate"
    REUSED_SCHEMA = "reused_schema"
    RETAINED_FINDING = "retained_finding"


class ApiContractBatchError(RuntimeError):
    """A failed batch with its original failure class, never its source/error text."""

    def __init__(self, failure_class, execution):
        self.failure_class = failure_class
        self.loop_execution = {key: value for key, value in execution.items() if key != "events"}
        super().__init__("api_contract_supply_batch_failed:" + failure_class)


def run_as_loop(args, *, revision, licence_text, generator_digest, ledger=None):
    return run_batch_as_loop(args, revision=revision, licence_text=licence_text, generator_digest=generator_digest,
                             ledger=ledger, worker=run, request_role="api_contract_supply_request/v1")


def run_batch_as_loop(args, *, revision, licence_text, generator_digest, worker, request_role, ledger=None):
    """One canonical Starting Practitioner Loop per batch, never one per atom.

    Preview stays local discovery without output writes. The generation path
    executes exactly once; a refused batch is not retried by this wrapper.
    The caller still owns a wall-clock supervisor over the whole invocation.
    """
    if not args.authorize_output_writes:
        return worker(args, revision=revision, licence_text=licence_text, generator_digest=generator_digest)
    from loop_engine.loop.loop_contract import contract_for_code_loop
    from loop_engine.loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome

    contract = contract_for_code_loop("api_contract_supply_batch/v1",
        input_roles=(request_role,), output_roles=(RUN_RECORD_TYPE,),
        effects=("reads_fs", "writes_fs", "spawns_process"), role="practitioner.code_execution")
    loop = Loop("Prepare one bounded batch of API contract candidates.",
        LoopConfig(framework="custom", custom_steps=("generate",), allowable_modes=("deterministic",),
                   preferred_modes=("deterministic",), delegated_modes=("deterministic",),
                   max_iterations=1, exit_condition="accepted_success"), contract=contract, ledger=ledger,
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.code_execution"), relationship=LoopRelationship.starting())
    held = {}

    def handler(_loop, _step, _context):
        if held:
            raise RuntimeError("supply_batch_must_not_retry")
        held["attempted"] = True
        try:
            held["result"] = worker(args, revision=revision, licence_text=licence_text, generator_digest=generator_digest)
        except Exception as error:
            # Retain only the failure class. Parser/provider text is not a
            # safe error record; cancellation and system exits remain outside
            # this catch. The single failed attempt cannot become acceptance.
            held["failure_class"] = type(error).__name__
            return StepOutcome(output="supply batch failed:" + held["failure_class"],
                               mode="deterministic", confidence=0.0, failed=True)
        return StepOutcome(output="supply batch attempt reported", mode="deterministic", confidence=1.0)

    completed = loop.run(handler=handler, max_steps=1)
    execution = {"record_type": "api_contract_supply_loop_execution/v1", "loop_id": completed.loop_id,
                 "relationship": "starting", "role": "practitioner", "mode": "deterministic",
                 "attempts": completed.attempts, "model_calls": completed.model_calls,
                 "accepted_successes": completed.accepted_successes, "loop_terminal_code": completed.terminal_code,
                 "failed": "failure_class" in held, "failure_class": held.get("failure_class"),
                 "batch_report_produced": "result" in held, "candidate_approval": False,
                 "effects": list(contract.effects), "events": loop.ledger.events}
    folder = _safe_path(args.run_folder)
    if folder.is_dir():
        _write_exact(folder / ("loop-invocation-" + str(time.time_ns()) + ".json"), atom_line.json_bytes(execution))
    if "failure_class" in held:
        raise ApiContractBatchError(held["failure_class"], execution) from None
    return {**held["result"], "loop_execution": {key: value for key, value in execution.items() if key != "events"}}


def _safe_path(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError("run_path_must_not_follow_symlinks")
    return path


def _safe_output_tree(folder):
    """Refuse aliases/special files anywhere, not just paths a journal names.

    This is a preflight for an exclusively owned output tree, not a sandbox
    against a concurrent privileged filesystem writer.
    """
    folder = _safe_path(folder)
    if not folder.exists():
        return folder
    if not folder.is_dir():
        raise ValueError("run_output_must_be_directory")
    count = 0
    for root, directories, files in os.walk(folder, followlinks=False):
        for name in (*directories, *files):
            path = _safe_path(Path(root) / name)
            count += 1
            if count > MAXIMUM_OUTPUT_PATHS or not (path.is_file() or path.is_dir()):
                raise ValueError("run_output_tree_not_regular_or_bounded")
    return folder


def _staging_directory(folder):
    staging = _safe_path(folder / "staging")
    staging.mkdir(exist_ok=True)
    if not staging.is_dir():
        raise ValueError("run_staging_must_be_directory")
    return _safe_path(staging)


def _candidate_path(folder, name):
    if (not isinstance(name, str) or not name or Path(name).name != name
            or name in (".", "..") or "\\" in name):
        raise ValueError("journal_candidate_path_invalid")
    return _safe_path(folder / "packages" / name)


def _write_exact(path, body):
    """A restart may reconcile identical bytes, never replace a different result."""
    path = _safe_path(path)
    if path.exists():
        if not path.is_file() or path.read_bytes() != body:
            raise ValueError("existing_output_bytes_differ")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, body)


def _journal(path):
    if not path.exists():
        return []
    if path.stat().st_size > MAXIMUM_JOURNAL_BYTES:
        raise ValueError("journal_byte_bound")
    rows, previous = [], ""
    for line in path.read_bytes().splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise ValueError("partial_journal_needs_reconciliation")
        row = json.loads(line)
        if (type(row) is not dict or row.get("record_type") != EVENT_TYPE or row.get("sequence") != len(rows)
                or row.get("previous_sha256") != previous
                or row.get("record_path") != f"retained/{len(rows):08d}.json"
                or row.get("outcome") not in tuple(AtomOutcome)):
            raise ValueError("journal_chain_mismatch")
        for key in ("candidate_id", "reuse_candidate_id"):
            if key in row and (not isinstance(row[key], str) or Path(row[key]).name != row[key]
                               or row[key] in (".", "..") or "\\" in row[key]):
                raise ValueError("journal_candidate_path_invalid")
        previous = atom_line.digest(row)
        rows.append(row)
    return rows


def _append(path, rows, row):
    path = _safe_path(path)
    event = {"record_type": EVENT_TYPE, "sequence": len(rows),
             "previous_sha256": atom_line.digest(rows[-1]) if rows else "", **row}
    raw = json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    if (path.stat().st_size if path.exists() else 0) + len(raw) > MAXIMUM_JOURNAL_BYTES:
        raise ValueError("journal_byte_bound")
    with path.open("ab") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    rows.append(event)


def _materialize(folder, payload, bodies):
    for entry in payload["package"]["files"]:
        _write_exact(folder / entry["path"], bodies[entry["digest"]])
    _write_exact(folder / "candidate.json", atom_line.json_bytes(payload))


def _checked_package(candidate):
    from component_qualification.components import ComponentReadError, from_folder
    candidate = _safe_path(candidate)
    try:
        component = from_folder(candidate)
    except ComponentReadError:
        raise ValueError("candidate_file_changed") from None
    record_path = _safe_path(candidate / "candidate.json")
    raw = record_path.read_bytes()
    payload = read_supply_candidate(dict(component.candidate))
    if payload["record_id"] != candidate.name:
        raise ValueError("candidate_folder_identity_changed")
    expected = {"candidate.json", *(entry["path"] for entry in payload["package"]["files"])}
    paths = list(candidate.rglob("*"))
    if any(_safe_path(path) != path for path in paths):
        raise ValueError("candidate_symlink_refused")
    actual = {path.relative_to(candidate).as_posix() for path in paths if path.is_file()}
    if actual != expected:
        raise ValueError("candidate_file_inventory_changed")
    return payload, raw


def _verify_existing(folder, rows, specifications, bindings):
    """Derive each event from its retained source-bound record and actual bytes."""
    source_stream, seen, recorded = iter(_stream(specifications)), {}, set()
    for index, row in enumerate(rows):
        source_index, source_atom = next(source_stream, (None, None))
        raw = _safe_path(folder / row["record_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["record_sha256"]:
            raise ValueError("retained_atom_changed")
        retained = json.loads(raw)
        if (retained.get("record_type") != RETAINED_TYPE or source_index is None
                or retained.get("source") != bindings[source_index] or retained.get("atom") != source_atom):
            raise ValueError("retained_atom_source_binding_changed")
        event = retained.get("event")
        if not isinstance(event, dict) or event.get("source_index") != source_index or event.get("source_pointer") != source_atom["pointer"]:
            raise ValueError("retained_atom_event_binding_changed")
        outcome = event.get("outcome")
        common = {"source_index", "source_pointer", "outcome"}
        size = len(raw)
        if outcome == AtomOutcome.CANDIDATE:
            if set(event) != common | {"semantic_sha256", "candidate_id", "package_digest", "tests_run"}:
                raise ValueError("retained_atom_candidate_fields")
            payload, candidate_bytes = _checked_package(_candidate_path(folder, event["candidate_id"]))
            if (payload["package_digest"] != event["package_digest"]
                    or hashlib.sha256(candidate_bytes).hexdigest() != retained.get("candidate_sha256")
                    or event["tests_run"] != payload["tests"]["tests_run"]):
                raise ValueError("candidate_digest_changed")
            size += len(candidate_bytes) + sum(entry["size_bytes"] for entry in payload["package"]["files"])
            seen[event["semantic_sha256"]] = event["candidate_id"]
            recorded.add(event["candidate_id"])
        elif outcome == AtomOutcome.REUSED_SCHEMA:
            if (set(event) != common | {"semantic_sha256", "reuse_candidate_id"}
                    or seen.get(event["semantic_sha256"]) != event["reuse_candidate_id"]):
                raise ValueError("retained_atom_reuse_binding_changed")
        elif outcome == AtomOutcome.RETAINED_FINDING:
            if set(event) not in (common | {"finding"}, common | {"finding", "semantic_sha256"}):
                raise ValueError("retained_atom_finding_fields")
        else:
            raise ValueError("retained_atom_outcome_invalid")
        if "semantic_sha256" in event and atom_line.semantic_digest(retained["normalized_schema"]) != event["semantic_sha256"]:
            raise ValueError("retained_atom_semantics_changed")
        expected = {"record_type": EVENT_TYPE, "sequence": index,
            "previous_sha256": atom_line.digest(rows[index - 1]) if index else "", **event,
            "record_path": f"retained/{index:08d}.json", "record_sha256": hashlib.sha256(raw).hexdigest(),
            "retained_and_candidate_bytes": size}
        if atom_line.json_bytes(row) != atom_line.json_bytes(expected):
            raise ValueError("journal_retained_event_accounting_mismatch")
    # Complete candidates from a crash before its event can be reconciled on
    # the next iteration, but never skipped at an exhausted source cursor.
    package_root = _safe_path(folder / "packages")
    pending_source = next(source_stream, None)
    unrecorded = []
    if package_root.exists():
        for candidate in package_root.iterdir():
            _checked_package(candidate)
            if candidate.name not in recorded:
                unrecorded.append(candidate)
                if pending_source is None or len(unrecorded) > 1:
                    raise ValueError("unrecorded_candidate_at_unexpected_cursor")
                index, atom = pending_source
                metadata = json.loads(_safe_path(candidate / "contract.schema.json").read_bytes())["x-baltor-contract"]
                if (metadata["logical_selector"] != atom["pointer"]
                        or metadata["source_sha256"] != bindings[index]["sha256"]):
                    raise ValueError("unrecorded_candidate_parent_mismatch")


def _stream(specifications):
    # Round-robin sources so a pilot covers each declared provider, without
    # multiplying a job by a persona, language, label or arbitrary parameter.
    iterators = [(index, iter(atom_line.atoms(spec["document"]))) for index, (_source, spec) in enumerate(specifications)]
    while iterators:
        following = []
        for source_index, iterator in iterators:
            try:
                yield source_index, next(iterator)
                following.append((source_index, iterator))
            except StopIteration:
                pass
        iterators = following


def run(args, *, revision, licence_text, generator_digest):
    if (not 1 <= args.maximum_atoms <= 100_000 or not 1 <= args.maximum_attempts <= 1_000_000
            or not 1 <= args.batch_size <= 10_000 or not 0 < args.maximum_seconds <= 43_200
            or type(args.maximum_candidate_bytes) is not int or args.maximum_candidate_bytes < 1):
        raise ValueError("bounded_atomic_run_required")
    wanted = sorted(set(args.source))
    reader = atom_line.CachedFacts(args.cache_folder, cache_directory=getattr(args, "cache_directory", None))
    mode = getattr(args, "source_mode", api_contract_sources.ApiContractSourceMode.CURATED.value)
    maximum_specs = getattr(args, "maximum_source_specifications", 25)
    maximum_source_bytes = getattr(args, "maximum_source_bytes", 32 * 1024 * 1024)
    specifications, source_findings = api_contract_sources.load(reader, mode, wanted,
        maximum_specifications=maximum_specs, maximum_source_bytes=maximum_source_bytes)
    bindings = [{"source_id": source["source_id"], "repository": spec["repository"], "path": spec["path"],
                 "revision": spec["commit"], "sha256": spec["sha256"], "retrieved_at": spec["retrieved_at"],
                 "licence": spec["licence"].spdx, "licence_sha256": spec["licence"].sha256,
                 "origin": spec.get("origin", "github_repository"), "normalized_view_sha256": spec["normalized_view_sha256"],
                 "pointer_basis": spec.get("pointer_basis", "pinned_openapi_document"), "conversion": spec.get("conversion", "none")}
                for source, spec in specifications]
    for binding, (_source, spec) in zip(bindings, specifications):
        population = Counter(row.get("phase", "source_finding") for row in atom_line.atoms(spec["document"]))
        binding["enumerable_source_atoms"] = sum(population.values())
        binding["source_atoms_by_phase"] = dict(population)
    plan = {"record_type": PLAN_TYPE, "line": JSON_SCHEMAS, "scope": atom_line.STATE_SCOPE,
            "source_mode": mode, "requested_sources": wanted,
            "maximum_source_specifications": maximum_specs, "maximum_source_bytes": maximum_source_bytes,
            "generator_revision": revision, "generator_digest": generator_digest, "sources": bindings,
            "source_findings": source_findings, "receipts": reader.receipts,
            "maximum_atoms": args.maximum_atoms, "maximum_attempts": args.maximum_attempts,
            "maximum_candidate_bytes": args.maximum_candidate_bytes,
            "semantic_dedup": "normalized_assertions_with_labels_dates_and_provenance_removed",
            "network_requests_authorized": 0, "model_calls_authorized": 0,
            "publication_authorized": False, "admission_authorized": False}
    if not args.authorize_output_writes:
        return {"record_type": RUN_RECORD_TYPE, "line": JSON_SCHEMAS, "scope": atom_line.STATE_SCOPE,
                "plan": plan, "written": False, "candidates": 0, "network_requests": 0}
    folder = _safe_output_tree(args.run_folder)
    folder.mkdir(parents=True, exist_ok=True)
    lock_path = _safe_path(folder / "run.lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        header_path = _safe_path(folder / "run.json")
        if header_path.exists():
            header = json.loads(header_path.read_bytes())
            if header["plan"] != plan:
                raise ValueError("resume_plan_changed")
        else:
            header = {"plan": plan, "started_at": now_utc()}
            _write_exact(header_path, atom_line.json_bytes(header))
        generated_on = header["started_at"][:10]
        events_path = _safe_path(folder / "events.jsonl")
        rows = _journal(events_path)
        _verify_existing(folder, rows, specifications, bindings)
        seen = {row["semantic_sha256"]: row["candidate_id"] for row in rows if row["outcome"] == AtomOutcome.CANDIDATE}
        existing = len(seen)
        started, attempted, exhausted = time.monotonic(), 0, False
        accounted_bytes = sum(row["retained_and_candidate_bytes"] for row in rows)
        stopped_by_bytes = False
        iterator = itertools.islice(_stream(specifications), len(rows), None)
        _staging_directory(folder)
        while (len(seen) < args.maximum_atoms and len(rows) < args.maximum_attempts
               and attempted < args.batch_size and time.monotonic() - started < args.maximum_seconds):
            try:
                source_index, atom = next(iterator)
            except StopIteration:
                exhausted = True
                break
            _source, spec = specifications[source_index]
            retained = {"source": bindings[source_index], "atom": atom}
            event = {"source_index": source_index, "source_pointer": atom["pointer"], "outcome": AtomOutcome.RETAINED_FINDING}
            pending = None
            try:
                if "finding" in atom:
                    raise ValueError(atom["finding"])
                schema = atom_line.normalize_schema(atom["schema"], spec["document"])
                semantic = atom_line.semantic_digest(schema)
                retained["normalized_schema"] = schema
                event["semantic_sha256"] = semantic
                if semantic in seen:
                    event.update(outcome=AtomOutcome.REUSED_SCHEMA, reuse_candidate_id=seen[semantic])
                else:
                    examples = atom_line.cases(atom, schema)
                    retained["cases"] = examples
                    with tempfile.TemporaryDirectory(prefix="contract-", dir=_staging_directory(folder)) as temporary:
                        _safe_path(temporary)
                        payload, bodies = atom_line.package(atom, schema, examples, spec, revision=revision,
                            generated_on=generated_on, licence_text=licence_text, staging=Path(temporary))
                    pending = (payload, bodies)
                    event.update(outcome=AtomOutcome.CANDIDATE, candidate_id=payload["record_id"],
                                 package_digest=payload["package_digest"], tests_run=payload["tests"]["tests_run"])
            except (ValueError, LookupError, KeyError, TypeError, RecursionError, SupplyRecordError) as error:
                event["finding"] = getattr(error, "code", type(error).__name__)
                retained["diagnostic"] = str(error)[:400]
            retained.update(record_type=RETAINED_TYPE, event=event)
            if pending:
                retained["candidate_sha256"] = hashlib.sha256(atom_line.json_bytes(pending[0])).hexdigest()
            record_path = f"retained/{len(rows):08d}.json"
            raw = atom_line.json_bytes(retained)
            size = len(raw) + (sum(entry["size_bytes"] for entry in pending[0]["package"]["files"])
                               + len(atom_line.json_bytes(pending[0])) if pending else 0)
            if accounted_bytes + size > args.maximum_candidate_bytes:
                stopped_by_bytes = True
                break
            if pending:
                _materialize(folder / "packages" / pending[0]["record_id"], *pending)
            _write_exact(folder / record_path, raw)
            _append(events_path, rows, {**event, "record_path": record_path, "record_sha256": hashlib.sha256(raw).hexdigest(),
                                       "retained_and_candidate_bytes": size})
            accounted_bytes += size
            if pending:
                seen[event["semantic_sha256"]] = pending[0]["record_id"]
            attempted += 1
        _verify_existing(folder, rows, specifications, bindings)
        seconds = time.monotonic() - started
        files, useful, sizes = [], set(), {}
        for row in rows:
            if row["outcome"] != AtomOutcome.CANDIDATE:
                continue
            payload = json.loads((folder / "packages" / row["candidate_id"] / "candidate.json").read_bytes())
            for entry in payload["package"]["files"]:
                files.append(entry["digest"])
                sizes[entry["digest"]] = entry["size_bytes"]
                if entry["path"] == "contract.schema.json":
                    useful.add(entry["digest"])
        report = {"record_type": RUN_RECORD_TYPE, "line": JSON_SCHEMAS, "scope": atom_line.STATE_SCOPE,
            "started_at": header["started_at"], "finished_at": now_utc(), "elapsed_seconds_this_invocation": round(seconds, 6),
            "source_specifications": len(specifications), "source_findings": source_findings,
            "attempts_total": len(rows), "attempts_this_invocation": attempted,
            "outcomes": dict(Counter(row["outcome"] for row in rows)), "candidates": len(seen),
            "new_candidates_this_invocation": len(seen) - existing, "source_stream_exhausted": exhausted,
            "enumerable_source_atoms": sum(row["enumerable_source_atoms"] for row in bindings),
            "retained_and_candidate_bytes": accounted_bytes, "stopped_by_candidate_byte_ceiling": stopped_by_bytes,
            "computed_atom_not_recorded_due_to_byte_ceiling": int(stopped_by_bytes),
            "payload_file_placements": len(files), "distinct_payload_digests": len(sizes),
            "distinct_payload_bytes": sum(sizes.values()), "useful_schema_digests": len(useful),
            "package_tests_passed": sum(row.get("tests_run", 0) for row in rows),
            "candidate_generation_per_second": round((len(seen) - existing) / seconds, 6) if seconds else None,
            "next_cursor": len(rows), "network_requests": 0, "model_calls": 0,
            "approved": False, "published": False, "store_written": False,
            "limits": ["Generation and local contract checks only, not admission or provider execution.",
                       "Distinct payloads include support files; useful schemas are reported separately.",
                       "Within-run assertion deduplication only; global semantic and served-byte reconciliation remain required.",
                       "Imperfect and equivalent source atoms remain in retained records with source bindings and diagnostic or reuse links."]}
        path = folder / ("report-" + str(len(rows)).zfill(8) + "-" + str(time.time_ns()) + ".json")
        _write_exact(path, atom_line.json_bytes(report))
        return report
