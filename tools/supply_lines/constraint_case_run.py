"""Resumable bounded case-file extension over frozen version-2 parent candidates."""
from __future__ import annotations

from collections import Counter
import fcntl
import json
from pathlib import Path
import tempfile
import time

from loop_engine.core.library_ingestion.record_rules import now_utc
from component_qualification.components import from_folder

from . import api_contract_run as atomic
from . import constraint_case_construction as construction
from . import constraint_case_exclusions as exclusions
from . import constraint_case_packages as packages
from . import constraint_case_runtime as runtime
from .records import JSON_SCHEMAS, OPERATION_CONSTRAINT_CASE_SCOPE, RUN_RECORD_TYPE

PLAN_TYPE = "api_constraint_case_plan/v2"
EVENT_TYPE = "api_constraint_case_event/v2"
RETAINED_TYPE = "api_constraint_case_retained/v1"
EVENT_FIELDS = {"record_type", "sequence", "previous_sha256", "parent_record_id", "record_path", "record_sha256",
                "case_jobs", "groups", "retained_and_candidate_bytes", "case_accounting"}
RETAINED_FIELDS = {"record_type", "parent", "accounting", "case_jobs", "groups"}
# One parent can retain hundreds of diagnostic rows. This private control
# record has its own bound; served schemas and individual cases keep theirs.
MAXIMUM_RETAINED_BYTES = 4 * 1024 * 1024
# Diagnostic path arrays can exceed a served file's traversal allowance while
# remaining well below the private byte bound. Depth and content guards stay
# unchanged; only this private control-record decoder uses the larger budget.
MAXIMUM_RETAINED_NODES = 250_000


class RetainedRecordStructureError(ValueError):
    """A private diagnostic record exceeded its depth or traversal allowance."""


def decode_retained(raw):
    try:
        return runtime.decode(raw, maximum=MAXIMUM_RETAINED_BYTES, maximum_nodes=MAXIMUM_RETAINED_NODES)
    except ValueError as error:
        if error.args == (runtime.STRUCTURE_BOUND,):
            raise RetainedRecordStructureError("constraint_retained_structure_bound") from error
        raise


def read_retained(path):
    path = atomic._safe_path(path)
    if not path.is_file() or path.stat().st_size > MAXIMUM_RETAINED_BYTES:
        raise ValueError("constraint_retained_byte_bound")
    raw = path.read_bytes()
    return raw, decode_retained(raw)


def inputs(folders, maximum):
    if type(maximum) is not int or not 1 <= maximum <= 100_000:
        raise ValueError("constraint_parent_population_bound")
    found, seen = [], set()
    for folder in sorted({str(Path(value).absolute()) for value in folders}):
        root = atomic._safe_path(folder)
        header_path = atomic._safe_path(root / "run.json")
        if not header_path.is_file() or header_path.stat().st_size > 8*1024*1024:
            raise ValueError("constraint_parent_header_not_regular_or_bounded")
        header = runtime.decode(header_path.read_bytes(), maximum=8*1024*1024)
        if header.get("plan", {}).get("record_type") != atomic.PLAN_TYPE:
            raise ValueError("constraint_parent_run_version")
        parent_root = atomic._safe_path(root / "packages")
        for path in sorted(parent_root.iterdir()):
            if len(found) >= maximum:
                raise ValueError("constraint_parent_population_exceeds_ceiling")
            atomic._safe_path(path)
            parent = from_folder(path)
            if parent.identity in seen:
                continue
            if parent.generator.get("code_revision") != header["plan"]["generator_revision"]:
                raise ValueError("constraint_parent_revision_mismatch")
            schema = runtime.decode(parent.payloads.get("contract.schema.json"))
            runtime.validate_schema(schema)
            if schema.get("x-baltor-contract", {}).get("record_type") != "api_operation_contract_atom/v2":
                raise ValueError("constraint_parent_atom_version")
            examples = runtime.decode(parent.payloads.get("cases.json"))
            if type(examples) is not dict or type(examples.get("valid")) is not list:
                raise ValueError("constraint_parent_baselines_missing")
            snapshot = {"folder": str(path), "record_id": parent.identity, "package_digest": parent.package.package_digest,
                        "candidate_sha256": runtime.sha((path / "candidate.json").read_bytes()),
                        "schema_sha256": runtime.sha(parent.payloads["contract.schema.json"])}
            found.append((snapshot, parent, examples["valid"]))
            seen.add(parent.identity)
    return sorted(found, key=lambda row: row[0]["record_id"])


def events(path):
    if not path.exists():
        return []
    if path.stat().st_size > atomic.MAXIMUM_JOURNAL_BYTES:
        raise ValueError("constraint_journal_byte_bound")
    rows, previous = [], ""
    for line in path.read_bytes().splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise ValueError("constraint_partial_journal_needs_reconciliation")
        row = runtime.decode(line, maximum=atomic.MAXIMUM_JOURNAL_BYTES)
        runtime._shape(row, EVENT_FIELDS, "constraint_journal_fields")
        if (row.get("record_type") != EVENT_TYPE or row.get("sequence") != len(rows)
                or row.get("previous_sha256") != previous or row.get("record_path") != f"retained/{len(rows):08d}.json"):
            raise ValueError("constraint_journal_chain_mismatch")
        previous = runtime.fingerprint(row)
        rows.append(row)
    return rows


def _group_reference(payload, raw):
    return {"record_id": payload["record_id"], "package_digest": payload["package_digest"],
            "candidate_sha256": runtime.sha(raw)}


def verify(folder, rows, parents, revision):
    if len(rows) > len(parents):
        raise ValueError("constraint_cursor_exceeds_parent_plan")
    seen, recorded = set(), set()
    for index, row in enumerate(rows):
        raw, retained = read_retained(folder / row["record_path"])
        if runtime.sha(raw) != row["record_sha256"]:
            raise ValueError("constraint_retained_record_changed")
        runtime._shape(retained, RETAINED_FIELDS, "constraint_retained_fields")
        snapshot, parent, _baselines = parents[index]
        if retained["record_type"] != RETAINED_TYPE or retained["parent"] != snapshot:
            raise ValueError("constraint_retained_parent_binding_changed")
        if type(retained["groups"]) is not list or type(retained["case_jobs"]) is not list:
            raise ValueError("constraint_retained_members_invalid")
        parent_binding = {"record_id": parent.identity, "package_digest": parent.package.package_digest,
            "schema_sha256": snapshot["schema_sha256"],
            "semantic_sha256": runtime.semantic_digest(runtime.decode(parent.payloads["contract.schema.json"]))}
        member_jobs, byte_count = [], len(raw)
        for reference in retained["groups"]:
            runtime._shape(reference, {"record_id", "package_digest", "candidate_sha256"}, "constraint_group_reference_fields")
            path = atomic._candidate_path(folder, reference["record_id"])
            payload, candidate_raw = atomic._checked_package(path)
            component = from_folder(path)
            if (_group_reference(payload, candidate_raw) != reference or reference["record_id"] in recorded
                    or component.generator.get("code_revision") != revision):
                raise ValueError("constraint_group_changed_or_repeated")
            group = runtime.read_group(component.payloads)
            if group["parent"] != parent_binding:
                raise ValueError("constraint_group_parent_binding_changed")
            recorded.add(reference["record_id"])
            member_jobs.extend(entry["job_id"] for entry in group["cases"])
            byte_count += len(candidate_raw) + sum(entry.size_bytes for entry in component.package.files)
        if (len(member_jobs) != len(set(member_jobs)) or seen.intersection(member_jobs)
                or sorted(member_jobs) != sorted(retained["case_jobs"])):
            raise ValueError("constraint_retained_case_membership_changed")
        seen.update(member_jobs)
        expected = {"record_type": EVENT_TYPE, "sequence": index,
            "previous_sha256": runtime.fingerprint(rows[index - 1]) if index else "",
            "parent_record_id": parent.identity, "record_path": f"retained/{index:08d}.json", "record_sha256": runtime.sha(raw),
            "case_jobs": retained["case_jobs"], "groups": retained["groups"], "retained_and_candidate_bytes": byte_count,
            "case_accounting": {key: value for key, value in retained["accounting"].items() if key != construction.DIAGNOSTICS_FIELD}}
        if runtime.encode(row) != runtime.encode(expected):
            raise ValueError("constraint_journal_retained_accounting_mismatch")
    # Inspect every output package, including a completed write whose event
    # was interrupted. Only the next exact parent may own such pending work.
    package_root = atomic._safe_path(folder / "packages")
    if package_root.exists():
        for path in package_root.iterdir():
            atomic._checked_package(path)
            if path.name not in recorded:
                if len(rows) == len(parents):
                    raise ValueError("constraint_unrecorded_group_at_completed_cursor")
                group = runtime.read_group(from_folder(path).payloads)
                next_parent = parents[len(rows)][0]
                if (group["parent"]["record_id"] != next_parent["record_id"]
                        or group["parent"]["package_digest"] != next_parent["package_digest"]
                        or group["parent"]["schema_sha256"] != next_parent["schema_sha256"]):
                    raise ValueError("constraint_unrecorded_group_parent_mismatch")


def run(args, *, revision, licence_text, generator_digest):
    if (type(args.maximum_cases) is not int or args.maximum_cases < 1 or args.maximum_candidate_bytes < 1
            or not 1 <= args.batch_size <= 10_000 or not 0 < args.maximum_seconds <= 43_200):
        raise ValueError("constraint_run_bounds_invalid")
    parents = inputs(args.parent_run, args.maximum_contracts)
    population = len(parents)
    population_digest = runtime.fingerprint([row[0] for row in parents])
    offset, limit = getattr(args, "parent_offset", 0), getattr(args, "parent_limit", None)
    if (type(offset) is not int or not 0 <= offset <= population
            or limit is not None and (type(limit) is not int or not 1 <= limit <= 100_000)):
        raise ValueError("constraint_parent_selection_invalid")
    expected = getattr(args, "expected_parent_population", None)
    if expected is not None and expected != population_digest:
        raise ValueError("constraint_parent_population_changed")
    parents = parents[offset:None if limit is None else offset + limit]
    excluded, exclusion_binding = exclusions.read(getattr(args, "exclude_case_jobs", None))
    output_path = atomic._safe_path(args.run_folder)
    for source in args.parent_run:
        source_path = atomic._safe_path(source)
        if output_path == source_path or output_path in source_path.parents or source_path in output_path.parents:
            raise ValueError("constraint_output_overlaps_source")
    if any(parent.payloads.get("LICENSE") != licence_text for _snapshot, parent, _baselines in parents):
        raise ValueError("constraint_parent_generated_licence_changed")
    plan = {"record_type": PLAN_TYPE, "generator_revision": revision, "generator_digest": generator_digest,
            "scope": OPERATION_CONSTRAINT_CASE_SCOPE, "producer_family": packages.PRODUCER_FAMILY,
            "parent_selection": {"population": population, "population_sha256": population_digest,
                                 "offset": offset, "limit": limit}, "case_exclusions": exclusion_binding,
            "independent_oracle_version": construction.ORACLE_VERSION,
            "inputs": [row[0] for row in parents], "maximum_cases": args.maximum_cases,
            "maximum_candidate_bytes": args.maximum_candidate_bytes, "maximum_files_per_group": runtime.MAX_FILES,
            "network_calls_authorized": 0, "model_calls_authorized": 0, "publication_authorized": False}
    # Refuse a plan that cannot be read on restart. Use explicit shards, never
    # silently drop parents or raise the individual case-file byte bound.
    runtime.decode(runtime.encode({"plan": plan}), maximum=8 * 1024 * 1024)
    if not args.authorize_output_writes:
        return {"record_type": RUN_RECORD_TYPE, "line": JSON_SCHEMAS, "scope": OPERATION_CONSTRAINT_CASE_SCOPE,
                "plan": plan, "written": False, "candidate_files": 0}
    folder = atomic._safe_output_tree(args.run_folder)
    folder.mkdir(parents=True, exist_ok=True)
    with atomic._safe_path(folder / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        header_path = atomic._safe_path(folder / "run.json")
        if header_path.exists():
            header = runtime.decode(header_path.read_bytes(), maximum=8*1024*1024)
            if header["plan"] != plan:
                raise ValueError("constraint_resume_plan_changed")
        else:
            header = {"plan": plan, "started_at": now_utc()}
            atomic._write_exact(header_path, runtime.encode(header))
        event_path = atomic._safe_path(folder / "events.jsonl")
        rows = events(event_path)
        verify(folder, rows, parents, revision)
        seen = {job for row in rows for job in row["case_jobs"]}
        used_bytes = sum(row["retained_and_candidate_bytes"] for row in rows)
        prior_cases, prior_groups = len(seen), sum(len(row["groups"]) for row in rows)
        started, processed, ceiling = time.monotonic(), 0, ""
        atomic._staging_directory(folder)
        for snapshot, parent, baselines in parents[len(rows):]:
            if processed >= args.batch_size or time.monotonic() - started >= args.maximum_seconds:
                break
            cases, baseline_bodies, accounting = construction.construct(parent.payloads["contract.schema.json"], baselines)
            unique = [case for case in cases if case["job_id"] not in seen and case["job_id"] not in excluded]
            accounting["case_jobs_already_generated"] = sum(case["job_id"] in seen for case in cases)
            accounting["case_jobs_previously_known"] = sum(case["job_id"] in excluded for case in cases)
            with tempfile.TemporaryDirectory(prefix="case-groups-", dir=atomic._staging_directory(folder)) as staging:
                atomic._safe_path(staging)
                built = packages.generate(parent, unique, baseline_bodies, revision=revision,
                    generated_on=header["started_at"][:10], staging=Path(staging))
            # No source write occurred, and no output is committed until the
            # frozen parent's current exact bytes still agree.
            checked = from_folder(Path(snapshot["folder"]))
            if (checked.package.package_digest != snapshot["package_digest"]
                    or runtime.sha((Path(snapshot["folder"]) / "candidate.json").read_bytes()) != snapshot["candidate_sha256"]):
                raise ValueError("constraint_parent_changed_during_generation")
            retained = {"record_type": RETAINED_TYPE, "parent": snapshot, "accounting": accounting,
                "case_jobs": [case["job_id"] for case in unique],
                "groups": [_group_reference(payload, runtime.encode(payload)) for payload, _ in built]}
            raw = runtime.encode(retained)
            # Refuse an unreadable retained record before any candidate/cursor
            # write, using the same bounded reader policy as restart.
            decode_retained(raw)
            byte_count = len(raw) + sum(sum(file["size_bytes"] for file in payload["package"]["files"])
                                       + len(runtime.encode(payload)) for payload, _bodies in built)
            if len(seen) + len(unique) > args.maximum_cases or used_bytes + byte_count > args.maximum_candidate_bytes:
                ceiling = "case_count_or_byte_ceiling"
                break
            for payload, bodies in built:
                atomic._materialize(folder / "packages" / payload["record_id"], payload, bodies)
            record_path = f"retained/{len(rows):08d}.json"
            atomic._write_exact(folder / record_path, raw)
            event = {"record_type": EVENT_TYPE, "parent_record_id": parent.identity, "record_path": record_path,
                "record_sha256": runtime.sha(raw), "case_jobs": [case["job_id"] for case in unique],
                "groups": retained["groups"],
                "retained_and_candidate_bytes": byte_count, "case_accounting": {key: value for key, value in accounting.items()
                    if key != construction.DIAGNOSTICS_FIELD}}
            atomic._append(event_path, rows, event)
            seen.update(event["case_jobs"])
            used_bytes += byte_count
            processed += 1
        verify(folder, rows, parents, revision)
        sizes, role_digests, placements = {}, {}, 0
        for row in rows:
            for group in row["groups"]:
                parent = from_folder(folder / "packages" / group["record_id"])
                for file in parent.package.files:
                    sizes[file.digest] = file.size_bytes
                    role = "case" if file.path.startswith("cases/") else "shared_or_support"
                    role_digests.setdefault(role, set()).add(file.digest)
                    placements += 1
        counter = Counter()
        findings = Counter()
        for row in rows:
            for key in ("supported_jobs", "accepted_cases", "probe_attempts", "case_jobs_already_generated", "case_jobs_previously_known"):
                counter[key] += row["case_accounting"].get(key, 0)
            findings.update(row["case_accounting"].get("findings", {}))
        for snapshot, _parent, _baselines in parents:
            checked = from_folder(Path(snapshot["folder"]))
            if (checked.package.package_digest != snapshot["package_digest"]
                    or runtime.sha((Path(snapshot["folder"]) / "candidate.json").read_bytes()) != snapshot["candidate_sha256"]):
                raise ValueError("constraint_parent_changed_during_generation")
        if exclusions.read(getattr(args, "exclude_case_jobs", None))[1] != exclusion_binding:
            raise ValueError("constraint_exclusions_changed_during_generation")
        report = {"record_type": RUN_RECORD_TYPE, "line": JSON_SCHEMAS, "scope": OPERATION_CONSTRAINT_CASE_SCOPE,
            "producer_family": packages.PRODUCER_FAMILY, "source_contracts": len(parents), "parents_processed": len(rows),
            "parent_population": population, "parent_selection": plan["parent_selection"],
            "excluded_known_case_jobs": len(excluded),
            "independent_oracle_version": construction.ORACLE_VERSION,
            "parents_this_invocation": processed, "case_jobs": len(seen), "new_case_jobs": len(seen) - prior_cases,
            "groups": sum(len(row["groups"]) for row in rows), "new_groups": sum(len(row["groups"]) for row in rows) - prior_groups,
            "elapsed_seconds": round(time.monotonic() - started, 6), "next_cursor": len(rows),
            "complete": len(rows) == len(parents), "ceiling": ceiling, "accounting": dict(counter),
            "findings": dict(findings), "parents_without_case_files": sum(not row["case_jobs"] for row in rows),
            "payload_placements": placements, "distinct_payload_digests": len(sizes), "distinct_payload_bytes": sum(sizes.values()),
            "distinct_case_digests": len(role_digests.get("case", ())), "retained_and_candidate_bytes": used_bytes,
            "approved": False, "published": False, "model_calls": 0, "network_calls": 0,
            "input_bytes_unchanged": True, "limits": "Case replay and candidate generation only; not global duplicate clearance, admission or API execution."}
        atomic._write_exact(folder / ("report-" + str(len(rows)).zfill(8) + "-" + str(time.time_ns()) + ".json"), runtime.encode(report))
        return report


def run_as_loop(args, *, revision, licence_text, generator_digest, ledger=None):
    return atomic.run_batch_as_loop(args, revision=revision, licence_text=licence_text, generator_digest=generator_digest,
        worker=run, request_role="api_constraint_case_request/v1", ledger=ledger)
