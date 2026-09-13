#!/usr/bin/env python3
"""One artifact an engineer reads at 7am to decide what to look at.

A night produces workspaces, run histories, checkpoints and queue state spread
across a dozen directories. None of them answers the only question that matters
in the morning: what should I look at, and in what order?

The ordering principle here is REVIEW COST, not engine verdict, because today's
measurements say the engine's verdict is unreliable in a specific direction: it
produced correct artifacts and reported them as failures three separate times
(2-of-3 reported as 1-of-3; three correct scheduling attempts reported as a
failure). A report that sorted by exit code would hide exactly the work most
worth seeing.

So each unit is placed by what the reviewer must do:

  READY        verified, and independent evidence agrees -- skim it
  CHECK ME     artifacts exist and independent evidence supports them, but the
               engine said no. This is where the recovered work lives.
  DISAGREEMENT engine said yes, independent evidence says no. Read first: it is
               the only class that can ship something wrong.
  NOTHING      no artifacts. Nothing to review; read the blocker instead.

Evidence shown is always the kind the model did not author: cross-attempt
agreement on inputs harvested from its own tests, and engine-owned constraint
checks. A verdict is never reported without saying what backs it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from loop_engine.core.solution_ratchet import rank_attempts  # noqa: E402


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def unit_evidence(workspace: Path) -> dict:
    """Independent evidence about a unit, or an honest absence of it."""
    attempts = sorted(str(p) for p in workspace.glob("attempt-*") if p.is_dir())
    files = sorted(p for p in workspace.rglob("*.py")
                   if "__pycache__" not in str(p))
    evidence = {"attempts": len(attempts), "files": len(files),
                "agreement": "", "retained": "", "unanimous": None}
    if len(attempts) >= 2:
        try:
            report = rank_attempts(attempts)
            if report.inputs_harvested:
                evidence["retained"] = report.retained
                evidence["unanimous"] = all(s.is_best_available
                                            for s in report.scores)
                worst = max((s.dissents for s in report.scores), default=0)
                stuck = max((s.undecided for s in report.scores), default=0)
                if evidence["unanimous"]:
                    state = "unanimous"
                elif worst:
                    state = f"{worst} dissent(s)"
                else:
                    state = (f"{stuck} input(s) undecided - attempts disagree "
                             "with each other, so nothing was confirmed")
                evidence["agreement"] = (
                    f"{len(report.scores)} attempts, "
                    f"{report.inputs_harvested} inputs harvested, {state}")
        except Exception:                                # noqa: BLE001
            evidence["agreement"] = "ranking unavailable"
    elif len(attempts) == 1:
        evidence["retained"] = attempts[0]
        evidence["agreement"] = "single attempt - nothing to compare"
    return evidence


def constraint_findings(runs_dir: Path) -> list:
    """Engine-owned constraint results recorded for this unit."""
    findings = []
    for record in runs_dir.rglob("adaptive-result.json"):
        data = read_json(record)
        for attempt in (data.get("project_attempts") or []):
            for artifact in (attempt.get("artifacts") or []):
                if artifact.get("constraint"):
                    findings.append({
                        "path": artifact.get("path"),
                        "check": artifact.get("constraint"),
                        "satisfied": bool(artifact.get("constraint_satisfied")),
                        "violations": artifact.get("constraint_violations") or [],
                    })
    return findings


def classify(engine_ok: bool, evidence: dict, constraints: list) -> tuple:
    """Place a unit by what the reviewer has to do about it."""
    has_work = evidence["files"] > 0
    broken_constraint = any(not c["satisfied"] for c in constraints)
    supported = (evidence.get("unanimous") is True) or bool(constraints) and not broken_constraint
    if not has_work:
        return "NOTHING", "no artifacts were produced"
    if engine_ok and (broken_constraint or evidence.get("unanimous") is False):
        return "DISAGREEMENT", ("the engine accepted this but independent "
                                "evidence does not support it")
    if engine_ok:
        return "READY", "verified, and nothing contradicts it"
    if supported:
        return "CHECK ME", ("the engine reported failure but independent "
                            "evidence supports the artifacts")
    return "NOTHING", "artifacts exist but nothing independent supports them"


ORDER = {"DISAGREEMENT": 0, "CHECK ME": 1, "READY": 2, "NOTHING": 3}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    ws_root = Path(args.workspace_root)
    runs_root = Path(args.runs_root)
    state = read_json(runs_root / "overnight-queue.json")
    completed = state.get("completed") or {}

    units = []
    recorded = [v for v in completed.values() if v.get("workspace")]
    if recorded:
        # Preferred: the queue told us where each task ran, including the ones
        # that produced no directory at all. Those matter most in a morning
        # report -- a task that vanished without a workspace is exactly the
        # one a reviewer would otherwise never hear about.
        entries = [(Path(v["workspace"]), Path(v.get("runs_dir") or ""), v)
                   for v in sorted(recorded, key=lambda x: x.get("index", 0))]
    else:
        entries = [(w, runs_root / w.name, {})
                   for w in sorted(p for p in ws_root.iterdir() if p.is_dir())]
    for workspace, runs, info in entries:
        name = (Path(info.get("task_file") or workspace.name).stem
                if info else workspace.name)
        engine_ok = info.get("exit") == 0
        evidence = (unit_evidence(workspace) if workspace.is_dir()
                    else {"attempts": 0, "files": 0, "agreement": "",
                          "retained": "", "unanimous": None})
        constraints = constraint_findings(runs) if runs and runs.is_dir() else []
        bucket, why = classify(engine_ok, evidence, constraints)
        units.append({"name": name, "bucket": bucket, "why": why,
                      "engine": "success" if engine_ok else "failure",
                      "seconds": info.get("seconds"),
                      "evidence": evidence, "constraints": constraints,
                      "workspace": str(workspace)})

    units.sort(key=lambda u: (ORDER[u["bucket"]], u["name"]))
    lines = ["# Overnight report", ""]
    counts = {}
    for unit in units:
        counts[unit["bucket"]] = counts.get(unit["bucket"], 0) + 1
    lines.append("| outcome | units | what it means for you |")
    lines.append("|---|---|---|")
    for bucket, meaning in (
            ("DISAGREEMENT", "**read first** - accepted but unsupported"),
            ("CHECK ME", "recovered work the engine called a failure"),
            ("READY", "verified; skim"),
            ("NOTHING", "no artifacts; read the blocker")):
        if counts.get(bucket):
            lines.append(f"| {bucket} | {counts[bucket]} | {meaning} |")
    lines.append("")

    for unit in units:
        ev = unit["evidence"]
        lines.append(f"## {unit['bucket']} - {unit['name']}")
        lines.append(f"{unit['why']}.")
        lines.append("")
        lines.append(f"- engine verdict: **{unit['engine']}**"
                     + (f" ({unit['seconds']}s)" if unit.get("seconds") else ""))
        lines.append(f"- artifacts: {ev['files']} file(s) across "
                     f"{ev['attempts']} attempt(s)")
        if ev["agreement"]:
            lines.append(f"- independent agreement: {ev['agreement']}")
        for finding in unit["constraints"]:
            mark = "satisfied" if finding["satisfied"] else "**VIOLATED**"
            lines.append(f"- constraint `{finding['check']}` on "
                         f"`{finding['path']}`: {mark}")
            for violation in finding["violations"][:3]:
                lines.append(f"    - {violation}")
        if ev["retained"]:
            lines.append(f"- best attempt: `{ev['retained']}`")
        lines.append(f"- workspace: `{unit['workspace']}`")
        lines.append("")

    lines.append("---")
    lines.append("Evidence shown is independent of the model: cross-attempt "
                 "agreement on inputs harvested from its own tests (expected "
                 "values ignored), and engine-owned constraint checks the "
                 "model cannot author. The engine's own verdict is reported "
                 "but never used to order this list.")
    text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written: {args.out}")
    print(text if not args.out else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
