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


def reusable(record: "dict | None", row: dict, revision: str) -> bool:
    """Whether an earlier record covers this store row: same record version and package digest, checked by
    the same committed qualifier revision. The duplicate pass never reuses anything."""
    return (isinstance(record, dict) and record.get("record_version") == row["record_version"]
            and record.get("package_digest") == row.get("payload", {}).get("package_digest")
            and record.get("qualifier", {}).get("code_revision") == revision
            and record.get("qualifier", {}).get("uncommitted_changes") is False)


#: The checks that execute a component's own code, and so cost a sandbox per component. The owner, September 29,
#: 2026: "you need to stop strict overqualification of file components, if you keep trying to qualify every single
#: one we will never be able to publish correctly... once things are on the server they should be accessible... we
#: don't need to qualify everything pre-publication." These two stay available and are run by the sampled review,
#: but the per-component pass runs the cheap deterministic checks only, so a whole line qualifies in minutes.
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
                "checks": [row for row in earlier["checks"] if row["check_id"] != "duplicates"],
                "distinctive": checks.distinctive_text(component, context.policy),
                "job_key": checks.job_key(component, context.policy), "reused_from": earlier["qualified_at"],
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
            "generator": component.generator, "checks": results,
            "distinctive": checks.distinctive_text(component, context.policy),
            "job_key": checks.job_key(component, context.policy),
            "seconds": round(time.monotonic() - started, 3)}


def _duplicates(rows, policy, known_digests) -> dict:
    return checks.duplicate_findings_from(((row["identity"], row["package_digest"], row["distinctive"],
                                            row["job_key"]) for row in rows), policy, known_digests=known_digests)


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
        implementation = ("tests_passed_in_sandbox" if all(passed(name) for name in
                                                          ("parse", "schema", "effects", "sandbox")) else "failed")
        compatibility = {"state": "imports_in_sandbox" if passed("sandbox") else "failed",
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
             if reusable(earlier.get(row["record_id"]), row, revision)}
    checked, unreadable = [], []
    pool_started = time.monotonic()
    with multiprocessing.get_context("fork").Pool(
            processes=max(1, workers), initializer=_init_worker,
            initargs=(str(repository), str(store_root), sandbox_settings, str(work_root), reuse, check_ids)) as pool:
        for number, row in enumerate(pool.imap_unordered(_check_one, rows, chunksize=4), 1):
            (unreadable if "unreadable" in row else checked).append(row)
            if progress and number % 500 == 0:
                progress(number, len(rows), time.monotonic() - pool_started)
    pool_seconds = time.monotonic() - pool_started
    duplicates = _duplicates(checked, context.policy, known_digests)
    stamp = _now()
    counts, reasons, environment_refused = Counter(), Counter(), 0
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as stream:
        for row in sorted(checked, key=lambda item: item["identity"]):
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
    total_seconds = time.monotonic() - started
    summary = {
        "record_type": RUN_RECORD, "started_at": stamp, "qualifier_revision": revision,
        "qualifier_uncommitted_changes": uncommitted,
        "self_test": {"sha256": test_record["sha256"], "known_wrong_controls": len(test_record["known_wrong"]),
                      "known_good_rows": len(test_record["known_good"]), "seconds": self_test_seconds},
        "sandbox": {"engine": sandbox_settings.engine, "limits": sandbox_settings.limits.to_dict()},
        "workers": workers, "components": len(rows), "checked": len(checked), "unreadable": len(unreadable),
        "reused": sum(1 for row in checked if "reused_from" in row),
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
        "records": str(output), "records_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    return summary


def _nested(counts: Counter) -> dict:
    result = {}
    for (batch, line, form, outcome), count in sorted(counts.items()):
        row = result.setdefault(batch, {"line": line, "form": form, QUALIFIED: 0, REFUSED: 0})
        row[outcome] += count
    return result


def default_workers() -> int:
    return max(1, (os.cpu_count() or 2) * 3 // 4)
