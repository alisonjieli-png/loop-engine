"""Conform a messy company file, then export a solution that runs without Loop Engine.

The solutioning side profiles the columns, proposes typed conformance rules
from the evidence, runs them with a confidence per correction, and stages
the low-confidence cells for escalation. The solutions side exports the
chosen rules, the merged exception catalogs, and the operations module as a
standalone package, then verifies that package in an isolated interpreter
that cannot import loop_engine.

Run:
    python3 examples/26_export_a_standalone_solution/run.py [--out DIR]

No network, no external service, no model calls. The export is written to a
temporary directory unless --out names one.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path

from loop_engine import LoopLedger
from loop_engine.code_nodes import text_conformance_operations as operations
from loop_engine.code_nodes.solution_export import export_solution, text_conformance_export_spec, verify_export
from loop_engine.code_nodes.text_conformance import (ConformancePolicy, ConformanceRule, load_packaged_catalogs,
                                                     merge_layers, propose_rules, run_conformance)
from loop_engine.loop.encapsulate import as_practitioner_loop

HERE = Path(__file__).resolve().parent
INPUT = HERE / "inputs" / "companies.csv"


def load_rows() -> list[dict]:
    with INPUT.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def solutioning(rows: list[dict], catalogs: dict) -> dict:
    """Profile, propose, and run: the deterministic part of the solutioning space."""
    columns = list(rows[0])
    profiles = {column: operations.profile_column([row[column] for row in rows], catalogs)
                for column in columns}
    proposals = propose_rules(profiles)
    rules = []
    for proposal in proposals:
        rule = proposal.rule
        if rule.operation == "phone_normalize":
            rule = ConformanceRule(rule.rule_id, rule.operation, rule.columns,
                                   {"default_country_code": "1"})
        rules.append(rule)
    run = run_conformance(rows, rules, ConformancePolicy(), catalogs)
    return {"profiles": profiles, "proposals": [item.to_dict() for item in proposals],
            "rules": rules, "run": run}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="", help="directory for the exported package")
    args = parser.parse_args()
    ledger = LoopLedger()
    catalogs = merge_layers([load_packaged_catalogs()])
    rows = load_rows()
    outcome = as_practitioner_loop("conform the company file and export the solution",
                                   lambda _inputs=None: solutioning(rows, catalogs), ledger=ledger)
    result = outcome["value"]
    run = result["run"]

    print("STANDALONE SOLUTION EXPORT")
    print(f"loop: {outcome['loop_id']}  ledger events: {len(ledger.events)}")
    print()
    print("COLUMN PROFILES")
    for column, profile in result["profiles"].items():
        shares = ", ".join(f"{key}={value:.0%}" for key, value in profile["shares"].items())
        print(f"  {column:<8} {shares}")
    print()
    print("PROPOSED RULES")
    for proposal in result["proposals"]:
        print(f"  {proposal['rule']['rule_id']:<18} {proposal['reasons'][0]}")
    print()
    print("CORRECTIONS")
    for item in run.corrections:
        arrow = "->" if item.outcome == "applied" else "?>"
        print(f"  row {item.row_ref:<3} {item.column:<8} {item.outcome:<9} {item.confidence:.2f}  "
              f"{item.input_value!r} {arrow} {item.output_value!r}  [{', '.join(item.reasons)}]")
    print()
    print("REPORT")
    print(f"  rows: {run.report.rows}  {json.dumps(run.report.overall)}  idempotent: {run.report.idempotent}")
    print(f"  escalations: {len(run.escalations)}")
    for escalation in run.escalations:
        print(f"    row {escalation.row_ref} {escalation.column}: {escalation.question()[:110]}...")
    if run.evidence_layer is not None:
        print(f"  column evidence layer: {run.evidence_layer.to_dict()['digest'][:16]} "
              f"({len(run.evidence_layer.catalogs['surname_exceptions'])} learned casings)")
    print()

    spec = text_conformance_export_spec(result["rules"], ConformancePolicy(), catalogs,
                                        package_name="company_conformance",
                                        summary="Conform company names, phones, emails, and websites.",
                                        solution_ref=run.report.to_dict()["content_digest"][:16])
    target = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="loop-engine-export-")) / "company_conformance"
    record = export_solution(spec, str(target))
    (target / "input.csv").write_text(INPUT.read_text("utf-8"), "utf-8")
    verification = verify_export(str(target), run_arguments=("--input", "input.csv", "--output-dir", "out"),
                                 expected_artifacts=("out/conformed.csv", "out/report.json",
                                                     "out/corrections.jsonl", "out/escalations.jsonl"))
    print("EXPORT")
    print(f"  package: {record.package_name} {record.version}  files: {record.file_count}")
    print(f"  target: {record.target}")
    print(f"  manifest digest: {record.manifest_digest[:16]}")
    print("VERIFICATION (isolated interpreter, loop_engine not importable)")
    for check in verification.checks:
        print(f"  {'ok  ' if check['passed'] else 'FAIL'} {check['check']}")
    if verification.passed:
        exported = json.loads((target / "out" / "report.json").read_text("utf-8"))
        print(f"  exported run: rows {exported['rows']} {json.dumps(exported['overall'])}")
    print(f"  passed: {verification.passed}")
    return 0 if verification.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
