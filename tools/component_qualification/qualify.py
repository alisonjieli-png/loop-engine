"""Qualify a population of generated components: self-test, every check, duplicates, one record each.

```text
Qualification run (one process, separate from every generator; no model call)
├── 1. self-test: every check passes the known-good fixtures and refuses each known-wrong control;
│      one failure stops the run before any component is read
├── 2. parallel pass, one worker per core share: read the component's exact files from the store,
│      run manifest, licence and provenance, parse, schema, effects, safety, secrets and the sandbox
├── 3. population pass in this process: exact and near duplicates over the distinctive files, against
│      the population itself and any known digests (the served library, earlier admissions)
└── 4. one component_qualification/v1 record per component, with the vetting dimensions kept apart:
       source identity checked, implementation tested, compatibility tested, publication approved
       (always "not yet" here: only a batch decision can set it)
```
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gc
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import time

from . import checks
from .components import ComponentReadError, body_store, component_from_row
from .controls import self_test

QUALIFICATION_RECORD = "component_qualification/v1"
RUN_RECORD = "component_qualification_run/v1"
QUALIFIER_VERSION = "1.0.0"
QUALIFIED, REFUSED = "qualified", "refused"

_WORKER = {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


QUALIFIER_PATHS = ("tools/component_qualification", "tools/qualify_generated_components.py")


def code_revision(repository: Path) -> str:
    done = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=False)
    return done.stdout.strip()


def qualifier_changed(repository: Path) -> bool:
    """Whether the qualifier's own code differs from its commit, so a record could not name its exact code."""
    done = subprocess.run(["git", "-C", str(repository), "status", "--porcelain", "--", *QUALIFIER_PATHS],
                          capture_output=True, text=True, check=False)
    return done.returncode != 0 or bool(done.stdout.strip())


def _init_worker(repository, store_root, sandbox_settings, work_root, reuse, check_ids=None):
    _WORKER["context"] = checks.QualificationContext.load(Path(repository), sandbox_settings=sandbox_settings,
                                                          work_root=work_root)
    _WORKER["bodies"] = body_store(store_root)
    _WORKER["reuse"] = reuse or {}
    _WORKER["check_ids"] = tuple(check_ids) if check_ids else FAST_CHECKS


def reusable(record: "dict | None", row: dict, revision: str, *, check_ids=None) -> bool:
    """Whether an earlier record covers this store row: same record version and package digest, checked by
    the same committed qualifier revision and covering every requested check.
    The duplicate pass never reuses anything. A fast record cannot stand in for
    execution checks that the caller explicitly requested."""
    if not isinstance(record, dict):
        return False
    required = set(check_ids if check_ids is not None else FAST_CHECKS) - {"duplicates"}
    # v1 does not bind a reused sandbox result to interpreter, dependency and
    # sandbox image digests. Re-run execution until that environment is named.
    if required & {"sandbox", "mutation"} or not isinstance(record.get("checks"), list):
        return False
    recorded = {item.get("check_id") for item in record["checks"]
                if isinstance(item, dict) and item.get("status") in
                (checks.PASSED, checks.REFUSED, checks.NOT_APPLICABLE)}
    return (record.get("record_version") == row["record_version"]
            and record.get("package_digest") == row.get("payload", {}).get("package_digest")
            and record.get("qualifier", {}).get("code_revision") == revision
            and record.get("qualifier", {}).get("uncommitted_changes") is False
            and required <= recorded)


#: The checks that execute a component's own code, and so cost a sandbox per component. The owner, September 29,
#: 2026: "you need to stop strict overqualification of file components, if you keep trying to qualify every single
#: one we will never be able to publish correctly... once things are on the server they should be accessible... we
#: don't need to qualify everything pre-publication." These two stay available through --checks all.
#: Sampled model review reads selected packages; it does not itself run these execution checks.
EXECUTION_CHECKS = ("sandbox", "mutation")

#: The checks every component must pass before it is admitted. Each reads the bytes already on disk and decides;
#: none of them runs the component. Manifest, licence, parse, schema, effects, safety, secrets and duplicates.
FAST_CHECKS = tuple(check.check_id for check in checks.CHECKS if check.check_id not in EXECUTION_CHECKS)


def _check_one(row: dict) -> dict:
    """Every per-component check for one store row; the duplicate pass comes later in the parent."""
    context, started = _WORKER["context"], time.monotonic()
    try:
        component = component_from_row(row, _WORKER["bodies"])
    except ComponentReadError as error:
        return {"identity": row["record_id"], "unreadable": error.code, "seconds": 0.0,
                "line": row.get("payload", {}).get("line", "")}
    earlier = _WORKER["reuse"].get(component.identity)
    if earlier is not None:
        return {"identity": component.identity, "record_version": component.record_version,
                "package_digest": component.package.package_digest, "batch": component.batch,
                "line": component.line, "form": component.form, "kind": component.kind,
                "licence_expression": component.licence_expression,
                "declared_effects": list(component.candidate.get("declared_effects", [])),
                "generator": component.generator,
                "checks": [row for row in earlier["checks"]
                           if row["check_id"] in _WORKER["check_ids"] and row["check_id"] != "duplicates"],
                **_comparison(component, context.policy), "reused_from": earlier["qualified_at"],
                "seconds": round(time.monotonic() - started, 3)}
    results = []
    selected = _WORKER.get("check_ids") or FAST_CHECKS
    for check in checks.CHECKS:
        # The duplicate pass is population-level: it needs every component in the run at once, so the parent
        # adds its result to each row afterwards. Running it here would answer "not decided" for every row.
        if check.check_id not in selected or check.check_id == "duplicates":
            continue
        try:
            results.append(check.run(component, context).to_dict())
        except Exception as error:  # noqa: BLE001 - a failing check refuses, it is never read as a pass
            results.append(checks.CheckResult(check.check_id, checks.VERSION, check.kind, check.dimension,
                                              checks.REFUSED, (("check_failed", type(error).__name__),)).to_dict())
    return {"identity": component.identity, "record_version": component.record_version,
            "package_digest": component.package.package_digest, "batch": component.batch, "line": component.line,
            "form": component.form, "kind": component.kind, "licence_expression": component.licence_expression,
            "declared_effects": list(component.candidate.get("declared_effects", [])),
            "generator": component.generator, "checks": results, **_comparison(component, context.policy),
            "seconds": round(time.monotonic() - started, 3)}


def _comparison(component, policy) -> dict:
    """What the population's duplicate pass reads of one component, made in the worker: the digest of its
    normalized distinctive text, its shingle hashes as bytes and its job key. The text itself never reaches the
    parent, which held every one until October 5, 2026 (about 38 KB each for a generated API client)."""
    text_digest, tokens = checks.comparison_parts(checks.distinctive_text(component, policy))
    return {"text_digest": text_digest, "tokens": tokens.tobytes(), "job_key": checks.job_key(component, policy)}


def _subject(row: dict) -> tuple:
    """The duplicate pass's subject of one checked row, its shingle hashes read back from their bytes."""
    import numpy
    return (row["identity"], row["package_digest"], row["text_digest"],
            numpy.frombuffer(row["tokens"], dtype=numpy.uint64), row["job_key"])


def _duplicates(subjects, policy, known_digests) -> dict:
    return checks.duplicate_findings_hashed(subjects, policy, known_digests=known_digests)


def vetting(check_rows: list, policy: dict, line: str) -> dict:
    by_id = {row["check_id"]: row for row in check_rows}
    passed = lambda name: by_id.get(name, {}).get("status") == checks.PASSED  # noqa: E731
    shape = policy["lines"].get(line, {}).get("shape")
    sandbox = by_id.get("sandbox", {})
    notes = sandbox.get("notes") or []
    summary = json.loads(notes[0]) if notes and sandbox.get("status") == checks.PASSED else {}
    if shape == "configuration":
        implementation = ("static_configuration_validated" if all(passed(name) for name in
                                                                  ("parse", "schema", "effects")) else "failed")
        harnesses = [note for note in by_id.get("schema", {}).get("notes", []) if note.startswith("harness")]
        compatibility = {"state": "harness_formats_validated" if passed("schema") else "failed",
                         "evidence": harnesses, "runtime_started": False}
    else:
        prerequisite_failure = any(by_id.get(name, {}).get("status") == checks.REFUSED
                                   for name in ("parse", "schema", "effects"))
        implementation = ("failed" if prerequisite_failure else "not_tested" if "sandbox" not in by_id
                          else "tests_passed_in_sandbox" if all(passed(name) for name in
                                                               ("parse", "schema", "effects", "sandbox"))
                          else "failed")
        compatibility = {"state": ("not_tested" if "sandbox" not in by_id else
                                    "imports_in_sandbox" if passed("sandbox") else "failed"),
                         "interpreter": summary.get("interpreter"), "runtime_started": passed("sandbox")}
    return {"source_identity_checked": passed("manifest") and passed("licence_provenance"),
            "implementation_tested": implementation, "tests": summary.get("tests"),
            "compatibility_tested": compatibility,
            "publication_safety_checked": all(passed(name) for name in ("safety", "secrets", "duplicates")),
            "publication_approved": {"state": "not_yet", "scope": None,
                                     "reason": "only a sampled batch decision approves publication"}}


def environment_codes(record: dict, policy_codes) -> set:
    return {finding["code"] for check in record.get("checks", []) for finding in check.get("findings", [])
            if finding["code"] in policy_codes}


def load_reuse(paths, revision: str, environment_findings=()) -> dict:
    """Identity to the newest earlier record made by this committed qualifier revision; a record refused for an
    environment reason (a timeout, a sandbox that did not start) is never reused."""
    records = {}
    for path in paths:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                qualifier = record.get("qualifier", {})
                if environment_codes(record, environment_findings):
                    continue
                if qualifier.get("code_revision") == revision and qualifier.get("uncommitted_changes") is False:
                    if record["identity"] not in records or record["qualified_at"] > records[record["identity"]]["qualified_at"]:
                        records[record["identity"]] = record
    return records


def qualify_rows(rows, *, repository: Path, store_root: Path, sandbox_settings, work_root: Path, workers: int,
                 known_digests=None, output: Path, progress=None, reuse_paths=(), check_ids=None) -> dict:
    """Qualify the named store rows; write one JSON line per component and return the run summary."""
    repository, work_root = Path(repository), Path(work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    revision = code_revision(repository)
    uncommitted = qualifier_changed(repository)
    context = checks.QualificationContext.load(repository, sandbox_settings=sandbox_settings, work_root=work_root)
    started = time.monotonic()
    test_record = self_test(context, revision)
    self_test_seconds = round(time.monotonic() - started, 1)
    environment_findings = tuple(context.policy["environment_findings"])
    earlier = load_reuse(reuse_paths, revision, environment_findings) if not uncommitted else {}
    reuse = {row["record_id"]: earlier[row["record_id"]] for row in rows
             if reusable(earlier.get(row["record_id"]), row, revision, check_ids=check_ids)}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Every checked row goes to a spool file beside the output as it arrives, and the parent keeps only each row's
    # place there and its duplicate subject (digests, job key, shingle hashes). Until October 5, 2026 the parent held
    # every checked row with its distinctive text and then every shingle string: the 118,106-component API client
    # line reached 35 GB in the duplicate pass and was killed with nothing written.
    spool_path = output.with_name(f".{output.name}.checked-{os.getpid()}")
    places, subjects, unreadable, reused = {}, [], [], 0
    # A forked worker that collects garbage writes to every inherited object's header and so copies the pages that
    # hold the parent's rows; frozen objects are left alone (gc.freeze, Python 3.7 and later).
    gc.collect()
    gc.freeze()
    pool_started = time.monotonic()
    try:
        with open(spool_path, "w+b") as spool:
            try:
                with multiprocessing.get_context("fork").Pool(
                        processes=max(1, workers), initializer=_init_worker,
                        initargs=(str(repository), str(store_root), sandbox_settings, str(work_root), reuse,
                                  check_ids)) as pool:
                    for number, row in enumerate(pool.imap_unordered(_check_one, rows, chunksize=4), 1):
                        if "unreadable" in row:
                            unreadable.append(row)
                        else:
                            subjects.append(_subject(row))
                            reused += "reused_from" in row
                            data = (json.dumps({key: value for key, value in row.items()
                                                if key not in ("tokens", "text_digest")}) + "\n").encode("utf-8")
                            places[row["identity"]] = (spool.tell(), len(data))
                            spool.write(data)
                        if progress and number % 500 == 0:
                            progress(number, len(rows), time.monotonic() - pool_started)
            finally:
                gc.unfreeze()
            pool_seconds = time.monotonic() - pool_started
            duplicates = _duplicates(subjects, context.policy, known_digests)
            checked = len(subjects)
            subjects.clear()
            records = _spooled(spool, places)
            summary_rows = _write_records(records, output, duplicates, context, revision, uncommitted, test_record,
                                          environment_findings)
    finally:
        spool_path.unlink(missing_ok=True)
    counts, reasons, environment_refused, stamp = summary_rows
    total_seconds = time.monotonic() - started
    summary = {
        "record_type": RUN_RECORD, "started_at": stamp, "qualifier_revision": revision,
        "qualifier_uncommitted_changes": uncommitted,
        "self_test": {"sha256": test_record["sha256"], "known_wrong_controls": len(test_record["known_wrong"]),
                      "known_good_rows": len(test_record["known_good"]), "seconds": self_test_seconds},
        "sandbox": {"engine": sandbox_settings.engine, "limits": sandbox_settings.limits.to_dict()},
        "workers": workers, "components": len(rows), "checked": checked, "unreadable": len(unreadable),
        "reused": reused,
        "refused_for_environment_reasons": environment_refused,
        "unreadable_reasons": dict(Counter(row["unreadable"] for row in unreadable)),
        "qualified": sum(value for key, value in counts.items() if key[3] == QUALIFIED),
        "refused": sum(value for key, value in counts.items() if key[3] == REFUSED),
        "by_batch": _nested(counts), "refusal_reasons": {f"{line} {reason}": count for (line, reason), count
                                                          in reasons.most_common()},
        "seconds": {"total": round(total_seconds, 1), "parallel_pass": round(pool_seconds, 1)},
        "throughput": {"components_per_second": round(len(rows) / pool_seconds, 2) if pool_seconds else None,
                       "components_per_day_at_this_rate": int(len(rows) / pool_seconds * 86400) if pool_seconds
                       else None},
        "records": str(output), "records_sha256": _file_sha256(output)}
    return summary


def _spooled(spool, places: dict):
    """The spooled checked rows, read back one at a time in identity order."""
    for identity in sorted(places):
        offset, length = places[identity]
        spool.seek(offset)
        yield json.loads(spool.read(length))


def _write_records(rows, output: Path, duplicates: dict, context, revision: str, uncommitted: bool, test_record: dict,
                   environment_findings) -> tuple:
    """Write one component_qualification/v1 record per checked row, in the order given; return the counts."""
    stamp = _now()
    counts, reasons, environment_refused = Counter(), Counter(), 0
    with open(output, "w", encoding="utf-8") as stream:
        for row in rows:
            found = duplicates.get(row["identity"], [])
            duplicate = checks.CheckResult("duplicates", checks.VERSION, "duplicates", checks.PUBLICATION,
                                           checks.REFUSED if found else checks.PASSED, tuple(found)).to_dict()
            check_rows = row["checks"] + [duplicate]
            refused = [f"{item['check_id']}:{finding['code']}" for item in check_rows
                       if item["status"] == checks.REFUSED for finding in item["findings"]]
            outcome = REFUSED if refused else QUALIFIED
            record = {"record_type": QUALIFICATION_RECORD, "identity": row["identity"],
                      "record_version": row["record_version"], "package_digest": row["package_digest"],
                      "batch": row["batch"], "line": row["line"], "form": row["form"], "kind": row["kind"],
                      "licence_expression": row["licence_expression"], "declared_effects": row["declared_effects"],
                      "generator": row["generator"], "outcome": outcome, "reasons": refused,
                      "checks": check_rows, "vetting": vetting(check_rows, context.policy, row["line"]),
                      "qualifier": {"tool": "tools/component_qualification", "version": QUALIFIER_VERSION,
                                    "code_revision": revision, "uncommitted_changes": uncommitted},
                      "self_test_sha256": test_record["sha256"],
                      "qualified_at": row.get("reused_from") or stamp, "checked_in_run": stamp,
                      "reused": "reused_from" in row, "seconds": row["seconds"]}
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            counts[(row["batch"], row["line"], row["form"], outcome)] += 1
            environment_refused += bool(environment_codes({"checks": check_rows}, environment_findings))
            for reason in sorted(set(refused)):
                reasons[(row["line"], reason)] += 1
    return counts, reasons, environment_refused, stamp


def _file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nested(counts: Counter) -> dict:
    result = {}
    for (batch, line, form, outcome), count in sorted(counts.items()):
        row = result.setdefault(batch, {"line": line, "form": form, QUALIFIED: 0, REFUSED: 0})
        row[outcome] += count
    return result


def default_workers() -> int:
    return max(1, (os.cpu_count() or 2) * 3 // 4)
