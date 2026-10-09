"""Frozen case-job exclusions derived from exact existing candidate packages.

This is a private comparison artifact, not a catalogue, approval or runtime.
The writer verifies and replays source groups once. A generation plan binds
the complete snapshot bytes; exclusions prevent repeated jobs before grouping.
Novelty is relative to that declared corpus, never a worldwide originality claim.
"""
from pathlib import Path

from component_qualification.components import from_folder
from loop_engine.core.service_runtime.catalogue_bundle import strict_json
from . import api_contract_run as atomic
from . import constraint_case_runtime as runtime

RECORD_TYPE = "api_constraint_case_exclusions/v1"
MAXIMUM_BYTES = 256 * 1024 * 1024
MAXIMUM_JOBS = 2_000_000
MAXIMUM_GROUPS = 200_000
FIELDS = {"record_type", "job_ids", "sources"}
SOURCE_FIELDS = {"record_id", "package_digest", "case_job_set_sha256"}


def validate(record):
    runtime._shape(record, FIELDS, "case_exclusions_fields")
    if record["record_type"] != RECORD_TYPE:
        raise ValueError("case_exclusions_version")
    jobs, sources = record["job_ids"], record["sources"]
    if (type(jobs) is not list or len(jobs) > MAXIMUM_JOBS
            or any(type(job) is not str or not runtime.HEX.fullmatch(job) for job in jobs)
            or jobs != sorted(set(jobs))):
        raise ValueError("case_exclusions_job_population")
    if type(sources) is not list or len(sources) > MAXIMUM_GROUPS:
        raise ValueError("case_exclusions_source_population")
    identities = []
    for source in sources:
        runtime._shape(source, SOURCE_FIELDS, "case_exclusions_source_fields")
        name = source["record_id"]
        if (type(name) is not str or not name or len(name) > 512 or Path(name).name != name
                or name in (".", "..") or "\\" in name
                or any(type(source[key]) is not str or not runtime.HEX.fullmatch(source[key])
                       for key in ("package_digest", "case_job_set_sha256"))):
            raise ValueError("case_exclusions_source_invalid")
        identities.append((name, source["package_digest"]))
    if identities != sorted(set(identities)) or (jobs and not sources):
        raise ValueError("case_exclusions_source_population")
    return record


def _document(path):
    path = atomic._safe_path(path)
    if not path.is_file() or path.stat().st_size > MAXIMUM_BYTES:
        raise ValueError("case_exclusions_byte_bound")
    raw = path.read_bytes()
    if len(raw) > MAXIMUM_BYTES:
        raise ValueError("case_exclusions_byte_bound")
    record = validate(strict_json(raw, "case_exclusions_json"))
    return record, {"path": str(path), "sha256": runtime.sha(raw),
                    "case_jobs": len(record["job_ids"]), "groups": len(record["sources"])}


def read(path):
    if path is None:
        return set(), None
    record, binding = _document(path)
    return set(record["job_ids"]), binding


def snapshot(folders, *, previous=None, maximum_groups=MAXIMUM_GROUPS):
    """Verify each additional group and preserve the exact prior exclusion snapshot."""
    if type(maximum_groups) is not int or not 0 <= maximum_groups <= MAXIMUM_GROUPS:
        raise ValueError("case_exclusions_group_bound")
    if previous is None:
        jobs, sources = set(), {}
    else:
        old, _ = _document(previous)
        jobs = set(old["job_ids"])
        sources = {(row["record_id"], row["package_digest"]): row for row in old["sources"]}
    for index, folder in enumerate(folders):
        if index >= maximum_groups:
            raise ValueError("case_exclusions_group_bound")
        component = from_folder(atomic._safe_output_tree(folder))
        group = runtime.read_group(component.payloads, independent=True, replay_cases=True)
        row = {"record_id": component.identity, "package_digest": component.package.package_digest,
               "case_job_set_sha256": group["case_job_set_sha256"]}
        sources[(component.identity, component.package.package_digest)] = row
        jobs.update(case["job_id"] for case in group["cases"])
        if len(jobs) > MAXIMUM_JOBS or len(sources) > MAXIMUM_GROUPS:
            raise ValueError("case_exclusions_population_bound")
    result = validate({"record_type": RECORD_TYPE, "job_ids": sorted(jobs),
                       "sources": [sources[key] for key in sorted(sources)]})
    if len(runtime.encode(result)) > MAXIMUM_BYTES:
        raise ValueError("case_exclusions_byte_bound")
    return result


def write(path, record):
    raw = runtime.encode(validate(record))
    if len(raw) > MAXIMUM_BYTES:
        raise ValueError("case_exclusions_byte_bound")
    atomic._write_exact(path, raw)
    return {"path": str(Path(path).absolute()), "sha256": runtime.sha(raw),
            "case_jobs": len(record["job_ids"]), "groups": len(record["sources"])}
