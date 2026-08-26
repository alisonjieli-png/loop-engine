"""loop-dev: the Development Assurance Plane command line.

Local, CI, and OpenCode all call the same assurance LoopNode
definitions. There is no separate shell-script review system.
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="loop-dev")
    parser.add_argument("--bootstrap", action="store_true",
                        help="run the bootstrap verifier without importing "
                             "Loop Engine")
    parser.add_argument("--assurance", action="store_true",
                        help="run the Repository Assurance Practitioner")
    parser.add_argument("--scope", default="full",
                        choices=("full", "changed", "precommit",
                                 "pull_request", "release"))
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as blocking")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable output")
    args = parser.parse_args(argv)

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
        from loop_engine_devtools.assurance import run_repository_assurance
        report = run_repository_assurance(scope=args.scope,
                                          strict=args.strict)
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
