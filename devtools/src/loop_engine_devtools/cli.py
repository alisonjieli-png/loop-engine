"""loop-dev: the Development Assurance Plane command line.

Local, CI, and coding harnesses all call the same assurance Loop
definitions. There is no separate shell-script review system.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="loop-dev")
    parser.add_argument("--bootstrap", action="store_true",
                        help="run the bootstrap verifier without importing "
                             "Loop Engine")
    parser.add_argument("--assurance", action="store_true",
                        help="run the Repository Assurance Practitioner")
    parser.add_argument("--orientation", action="store_true",
                        help="build a digest-bound repository orientation snapshot")
    parser.add_argument("--validate-orientation", metavar="PATH",
                        help="validate a saved orientation snapshot")
    parser.add_argument("--hardcoding-audit", action="store_true",
                        help="run the contextual hardcoding audit in report mode")
    parser.add_argument("--self-test", action="store_true",
                        help="run Development Assurance Plane canaries")
    parser.add_argument("--scope", default="full",
                        choices=("full", "changed", "precommit",
                                 "pull_request", "release"))
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as blocking")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable output")
    parser.add_argument("--output", metavar="PATH",
                        help="write orientation JSON or hardcoding JSONL evidence")
    parser.add_argument("--allowlist", metavar="PATH",
                        help="exact owned hardcoding allowlist")
    parser.add_argument("--include-low-risk", action="store_true",
                        help="include intentional local and other low-risk findings")
    parser.add_argument("--baseline", metavar="PATH",
                        help="compare a hardcoding audit with saved JSON or JSONL")
    parser.add_argument("--fail-on-new", default="none",
                        choices=("none", "medium", "high", "critical"),
                        help="block on new findings at or above this severity")
    args = parser.parse_args(argv)

    if args.self_test:
        from loop_engine_devtools.assurance.hardcoding import (
            self_test as hardcoding_self_test)
        from loop_engine_devtools.assurance.orientation import (
            self_test as orientation_self_test)
        reports = (orientation_self_test(), hardcoding_self_test())
        value = {
            "record_type": "development_assurance_self_test/v1",
            "reports": reports,
            "passed": sum(report["passed"] for report in reports),
            "total": sum(report["total"] for report in reports),
            "all_passed": all(report["all_passed"] for report in reports),
        }
        if args.json:
            print(json.dumps(value, indent=1))
        else:
            for report in reports:
                for test in report["tests"]:
                    print(("PASS" if test["passed"] else "FAIL")
                          + f" {test['test']}")
            print("DEVTOOLS SELF-TEST PASS" if value["all_passed"]
                  else "DEVTOOLS SELF-TEST FAILED")
        return 0 if value["all_passed"] else 1

    if args.orientation:
        from loop_engine_devtools.assurance.orientation import (
            run_orientation_as_loop, write_orientation_snapshot)
        snapshot, run_record = run_orientation_as_loop(Path.cwd())
        if args.output:
            write_orientation_snapshot(snapshot, args.output)
        value = snapshot.to_dict()
        if args.json:
            print(json.dumps(value, indent=1))
        else:
            print(f"ORIENTATION {snapshot.snapshot_id}")
            print(f"  commit: {snapshot.repository_commit}")
            print(f"  package roots: {', '.join(snapshot.package_roots)}")
            print(f"  authority bindings: {len(snapshot.authority_bindings)}")
            print(f"  Loop run: {run_record['loop_id']}")
            print(f"  unresolved: {len(snapshot.unresolved_questions)}")
            print(f"  contradictions: {len(snapshot.contradictions)}")
            if args.output:
                print(f"  evidence: {Path(args.output).resolve()}")
        return 0 if not snapshot.unresolved_questions else 1

    if args.validate_orientation:
        from loop_engine_devtools.assurance.orientation import (
            snapshot_from_dict, validate_orientation_snapshot)
        source = Path(args.validate_orientation)
        snapshot = snapshot_from_dict(json.loads(
            source.read_text(encoding="utf-8")))
        drift = validate_orientation_snapshot(snapshot, Path.cwd())
        if args.json:
            print(json.dumps(drift.to_dict(), indent=1))
        else:
            print("ORIENTATION FRESH" if drift.fresh
                  else "ORIENTATION STALE")
            for path in (*drift.changed_dependencies,
                         *drift.missing_dependencies):
                print(f"  {path}")
        return 0 if drift.fresh else 1

    if args.hardcoding_audit:
        from loop_engine_devtools.assurance.hardcoding import (
            AuditRequest, compare_with_baseline, load_audit_finding_ids,
            new_findings_at_or_above, run_hardcoding_audit_as_loop,
            write_audit_jsonl)
        report, run_record = run_hardcoding_audit_as_loop(AuditRequest(
            Path.cwd(), include_low_risk=args.include_low_risk,
            allowlist_path=Path(args.allowlist) if args.allowlist else None))
        delta = None
        blocking = ()
        if args.baseline:
            delta = compare_with_baseline(
                report, load_audit_finding_ids(args.baseline))
            if args.fail_on_new != "none":
                blocking = new_findings_at_or_above(
                    delta, report, args.fail_on_new)
        if args.output:
            target = Path(args.output)
            if target.suffix == ".jsonl":
                write_audit_jsonl(report, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(
                    report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
        value = {"summary": report["summary"], "run_record": run_record}
        if delta is not None:
            value["delta"] = delta
        value["blocking_new_finding_ids"] = list(blocking)
        if args.json:
            print(json.dumps(value, indent=1))
        else:
            summary = report["summary"]
            print(f"HARDCODING AUDIT {report['audit_id']}")
            print(f"  files: {summary['files_scanned']}")
            print(f"  literal candidates: {summary['literal_candidates_scanned']}")
            print(f"  material findings: {summary['unsuppressed_findings']}")
            print(f"  Loop run: {run_record['loop_id']}")
            print(f"  severity: {summary['by_severity']}")
            if delta is not None:
                print(f"  new: {len(delta['new_finding_ids'])}")
                print(f"  resolved: {len(delta['resolved_finding_ids'])}")
            if args.output:
                print(f"  evidence: {Path(args.output).resolve()}")
        invalid_allowlist = bool(report["summary"]["allowlist_problems"])
        return 1 if blocking or invalid_allowlist else 0

    if args.bootstrap:
        from loop_engine_devtools.bootstrap import run_bootstrap
        report = run_bootstrap()
        if args.json:
            print(json.dumps(report, indent=1))
        else:
            for problem in report["problems"]:
                print(f"{problem['rule']}: "
                      f"{problem.get('file', problem.get('path', ''))} - "
                      f"{problem.get('detail', problem.get('class', ''))}")
            print("BOOTSTRAP PASS" if report["passed"]
                  else "BOOTSTRAP FAILED")
        return 0 if report["passed"] else 1

    if args.assurance:
        from loop_engine_devtools.assurance import (
            RepositoryAssuranceRequest, run_repository_assurance)
        report = run_repository_assurance(RepositoryAssuranceRequest(
            Path.cwd().resolve(), scope=args.scope, strict=args.strict))
        if args.json:
            print(json.dumps(report, indent=1))
        else:
            print(f"REPOSITORY ASSURANCE: {report['verdict']}")
            for finding in report["findings"]:
                print(f"  [{finding['severity']}] {finding['rule']}: "
                      f"{finding['path']} - {finding['detail']}")
            print(f"  evidence: {report['evidence']}")
        return 0 if report["verdict"] != "BLOCKED" else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
