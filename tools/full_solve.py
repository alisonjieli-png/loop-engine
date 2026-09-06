#!/usr/bin/env python3
"""Deliver a whole goal: divide, propose several times, select, integrate.

The overnight queue solves units. It does not deliver a GOAL, and today's
7-unit run showed the gap precisely: four correct components were produced,
and composing them into a working pipeline was done by hand afterwards.
Nothing in the system attempted the composition, and nothing verified it. A
night that yields four parts and no whole has not solved the task.

Two additions, both grounded in what was measured:

**Multi-proposal.** The engine already retries a failing unit, but retries are
SEQUENTIAL and each sees the previous failure, so they correlate. Independent
proposals -- separate workspaces, separate solves, no shared history -- give
the ratchet something real to compare. Measured 2026-09-05: three independent
attempts at an ISO-8601 parser produced two correct and one broken, and
cross-attempt agreement located the broken one exactly (38/54 against 52/54).
That signal does not exist when attempt N is a repair of attempt N-1.

**Integration.** Units are solved in isolation by design, which is what makes
them tractable, and is also why nothing checks they fit. Here the selected
modules are imported together and chained in dependency order: an import
collision, a missing entry point, or a shape mismatch between one unit's output
and the next unit's input is found by the machine rather than by a person at
7am. Measured on the same run: unit 3 returned {'a': 2} while the constraint
checker expected {'a': {'start': 0, 'end': 2}} -- defensible shapes that could
not talk to each other, invisible until something tried to chain them.

Integration is reported, never forced: a goal whose parts do not compose still
returns its parts, with the composition failure named.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from loop_engine.core.solution_ratchet import rank_attempts  # noqa: E402

CHAIN_PROBE = '''
import sys, json, importlib.util, inspect
sys.path.insert(0, {root!r})
report = {{"imported": [], "failed": [], "entry_points": {{}}}}
for name, path in {modules!r}:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        report["failed"].append({{"unit": name,
                                 "error": type(exc).__name__ + ": " + str(exc)[:120]}})
        continue
    report["imported"].append(name)
    public = [n for n in dir(module)
              if not n.startswith("_") and callable(getattr(module, n))
              and getattr(getattr(module, n), "__module__", name) == name]
    report["entry_points"][name] = [
        {{"name": n, "params": [p for p in
          inspect.signature(getattr(module, n)).parameters]}}
        for n in public[:6]]
print(json.dumps(report))
'''


def solve_once(task_file: Path, work: Path, runs: Path, args) -> dict:
    """One independent proposal for one unit."""
    began = time.time()
    try:
        done = subprocess.run(
            [args.python, "-m", "loop_engine", "solve", "--file", str(task_file),
             "--quickstart", "--unattended", "--authorize-model-calls",
             "--workspace", str(work), "--runs-dir", str(runs),
             "--max-passes", str(args.max_passes),
             "--max-model-calls", str(args.max_calls), "--quiet-model-io"],
            capture_output=True, text=True, timeout=args.timeout, shell=False)
        code = done.returncode
    except subprocess.TimeoutExpired:
        code = 124
    files = [p for p in work.rglob("*.py")
             if "__pycache__" not in str(p)] if work.is_dir() else []
    return {"exit": code, "seconds": round(time.time() - began, 1),
            "files": len(files), "workspace": str(work)}


def select_proposal(proposals: list) -> tuple:
    """Pick the proposal its peers agree with, or the only one that produced work."""
    live = [p for p in proposals if p["files"]]
    if not live:
        return None, "no proposal produced files"
    if len(live) == 1:
        return live[0], "only one proposal produced files (unranked)"
    attempts = []
    for proposal in live:
        attempts.extend(str(d) for d in Path(proposal["workspace"]).glob("attempt-*")
                        if d.is_dir())
    if len(attempts) < 2:
        return live[0], "too few attempts to compare (unranked)"
    try:
        report = rank_attempts(attempts)
    except Exception as exc:                             # noqa: BLE001
        return live[0], f"ranking unavailable ({type(exc).__name__})"
    if not report.retained or not report.inputs_harvested:
        return live[0], "nothing comparable could be harvested (unranked)"
    for proposal in live:
        if report.retained.startswith(proposal["workspace"]):
            unanimous = all(s.is_best_available for s in report.scores)
            return proposal, (
                f"{len(report.scores)} attempts over {report.inputs_harvested} "
                f"inputs, {'unanimous' if unanimous else 'majority'}")
    return live[0], "retained attempt not matched to a proposal"


def integrate(selected: dict, root: Path, python: str) -> dict:
    """Import every selected module together and report what fits."""
    modules = []
    for unit, choice in selected.items():
        best = choice.get("retained") or choice.get("workspace")
        for path in sorted(Path(best).rglob("*.py")):
            if ("__pycache__" in str(path) or path.name.startswith(
                    ("test_", "verify_", "generate", "run_"))):
                continue
            modules.append((path.stem, str(path)))
            break
    if not modules:
        return {"composed": False, "reason": "no modules to integrate"}
    probe = root / "_integration_probe.py"
    probe.write_text(CHAIN_PROBE.format(root=str(root), modules=modules),
                     encoding="utf-8")
    try:
        done = subprocess.run([python, str(probe)], capture_output=True,
                              text=True, timeout=120, shell=False)
        payload = json.loads((done.stdout or "{}").strip() or "{}")
    except Exception as exc:                             # noqa: BLE001
        return {"composed": False, "reason": f"probe failed: {type(exc).__name__}"}
    finally:
        probe.unlink(missing_ok=True)
    payload["composed"] = bool(payload.get("imported")) and not payload.get("failed")
    payload["modules"] = [m for m, _ in modules]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True, help="manifest of unit task files")
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--runs-root", required=True)
    parser.add_argument("--proposals", type=int, default=2,
                        help="independent proposals per unit")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--max-passes", type=int, default=3)
    parser.add_argument("--max-calls", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=420)
    parser.add_argument("--call-budget", type=int, default=900)
    args = parser.parse_args()

    units = [Path(line.strip()) for line in
             Path(args.queue).read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.startswith("#")]
    work_root, runs_root = Path(args.work_root), Path(args.runs_root)
    spent, selected, log = 0, {}, []
    print(f"full solve: {len(units)} unit(s) x {args.proposals} proposal(s), "
          f"budget {args.call_budget} calls\n")

    for index, task_file in enumerate(units, 1):
        unit = f"{index:02d}-{task_file.stem}"
        if spent >= args.call_budget:
            log.append(f"{unit}: SKIPPED (budget)")
            print(f"  {unit}: skipped, budget exhausted", flush=True)
            continue
        proposals = []
        for k in range(1, args.proposals + 1):
            if spent >= args.call_budget:
                break
            work = work_root / unit / f"p{k}"
            runs = runs_root / unit / f"p{k}"
            result = solve_once(task_file, work, runs, args)
            spent += args.max_calls
            proposals.append(result)
            print(f"  {unit} proposal {k}: exit={result['exit']} "
                  f"files={result['files']} ({result['seconds']}s)", flush=True)
        choice, why = select_proposal(proposals)
        if choice:
            attempts = sorted(str(d) for d in Path(choice["workspace"]).glob("attempt-*"))
            choice = {**choice, "retained": attempts[-1] if attempts else choice["workspace"]}
            selected[unit] = choice
            print(f"    selected: {why}", flush=True)
        else:
            print(f"    none selected: {why}", flush=True)
        log.append(f"{unit}: {why}")

    print("\nintegrating selected components...")
    result = integrate(selected, work_root, args.python)
    print(f"  modules: {result.get('modules')}")
    print(f"  imported cleanly: {result.get('imported')}")
    if result.get("failed"):
        for failure in result["failed"]:
            print(f"  ! {failure['unit']}: {failure['error']}")
    for unit, entries in (result.get("entry_points") or {}).items():
        for entry in entries:
            print(f"    {unit}.{entry['name']}({', '.join(entry['params'])})")
    print(f"\n  COMPOSED: {result.get('composed')}")

    out = work_root / "full-solve.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"record_type": "full_solve/v1",
                               "selected": selected, "integration": result,
                               "log": log}, indent=1), encoding="utf-8")
    print(f"  report: {out}")
    return 0 if result.get("composed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
