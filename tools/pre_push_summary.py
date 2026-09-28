"""Print the pre-push table, a warning for everything continuous integration runs that this run did not, and one result.

Kind: development tool, called by tools/pre_push_check.sh at the end of a run. A local run is never equal to
continuous integration by default: some steps need Docker or a browser, the public language and link checks need
vale and lychee, --only runs a subset, the workflow runs the tools shards and runtime checks on three Python versions,
and a working tree with changes checks files a push would not send. Until September 27, 2026 such a gap was one line
among the passes. Now each gap is a warning printed after the table, and the last line says NOT EQUIVALENT TO CI
whenever anything continuous integration runs did not run here. The warnings come in two groups, because they need
different answers: what this run skipped (a missing tool, --only, uncommitted changes, a missing command), which the
person pushing can usually repair, and what a local run never covers (Docker, a browser, the other Python versions),
which only continuous integration runs. The result line counts both, so "0 skipped in this run" is the one to look for.

A gate that exits 127 found a command missing from the local environment. It ran no check, so it is neither a pass
nor a failure of the code: its row says so, it counts as not run, and the run exits 3 when nothing failed. A local
gate (the pristine check) runs something continuous integration does not; it can fail the run but never makes it
equivalent.

Usage: python tools/pre_push_summary.py RUN_FOLDER [--only a,b] [--python 3.10] [--dirty] [--workflow PATH]
The run folder holds results.txt ("code seconds name" lines), declined.txt ("step | reason" lines) and local.txt (one
local gate name a line). Exit status: 0 every gate that ran passed, 1 a gate failed, 3 no gate failed but one could
not run. It reads files and prints; it writes nothing.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
#: The exit status a shell gives when it cannot find a command.
COMMAND_NOT_FOUND = 127
NOT_FOUND_NOTE = "command not found in the local environment: NOT A CODE FAILURE"
#: A declined step whose reason starts so had nothing to check in this run; it is not a gap.
NOTHING_TO_CHECK = "nothing to check:"
#: A declined step whose reason starts so is one a local run never covers, such as a step that needs Docker.
CI_ONLY = "continuous integration only:"
#: The jobs whose matrix names the Python versions every local gate is compared with.
MATRIX_JOBS = ("unit-tests", "runtime-checks")
#: The log lines shown under a failed gate.
FAILURE_LINES = ("FAILED ", "FAIL: ", "ERROR: ")


def _lines(path: Path) -> list:
    return path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []


def read_rows(folder: Path) -> tuple:
    """(results, declined, local names) from a run folder; results sorted by gate name."""
    results = []
    for line in _lines(folder / "results.txt"):
        code, seconds, name = line.split(" ", 2)
        results.append((int(code), int(seconds), name))
    declined = []
    for line in _lines(folder / "declined.txt"):
        step, _, reason = line.partition("|")
        declined.append((step.strip(), reason.strip()))
    local = {line.strip() for line in _lines(folder / "local.txt") if line.strip()}
    return sorted(results, key=lambda row: row[2]), declined, local


def workflow_versions(workflow: Path = WORKFLOW):
    """The Python versions the workflow's matrix jobs run, in order, or None when the workflow cannot be read."""
    try:
        import yaml
    except ImportError:  # an interpreter without the project's extras still prints the table
        return None
    try:
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    found = []
    for job in MATRIX_JOBS:
        matrix = (((data.get("jobs") or {}).get(job) or {}).get("strategy") or {}).get("matrix") or {}
        for version in matrix.get("python-version") or []:
            if str(version) not in found:
                found.append(str(version))
    return found


def summarize(folder: Path, *, only=(), python="", dirty=False, workflow: Path = WORKFLOW) -> tuple:
    """(lines to print, exit status) for one run."""
    results, declined, local = read_rows(folder)
    lines, skipped, standing = [], [], []
    failed = not_run = 0
    for code, seconds, name in results:
        log = folder / f"{name}.log"
        marker = "  (local only)" if name in local else ""
        if code == 0:
            lines.append(f"  pass  {seconds:5}s  {name}{marker}")
        elif code == COMMAND_NOT_FOUND:
            not_run += 1
            lines.append(f"  ----  {seconds:5}s  {name}  {NOT_FOUND_NOTE} (exit 127, log {log}){marker}")
            lines += [f"          {line}" for line in _lines(log) if "not found" in line][:3]
            if name not in local:
                skipped.append(f"{name}: {NOT_FOUND_NOTE}")
        else:
            failed += 1
            lines.append(f"  FAIL  {seconds:5}s  {name}  (exit {code}, log {log}){marker}")
            lines += [f"          {line}" for line in _lines(log) if line.startswith(FAILURE_LINES)][:5]
    for step, reason in declined:
        lines.append(f"  skip         {step}: {reason}")
        if reason.startswith(CI_ONLY):
            standing.append(f"{step}: {reason[len(CI_ONLY):].strip()}")
        elif not reason.startswith(NOTHING_TO_CHECK):
            skipped.append(f"{step}: {reason}")
    if only:
        skipped.append(f"--only ran {', '.join(only)}; every other gate was left out")
    if dirty:
        skipped.append("the working tree differs from HEAD, so the gates checked files a push would not send")
    versions = workflow_versions(workflow)
    if versions is None:
        skipped.append(f"the Python versions of {workflow} could not be read, so none were compared")
    elif python and versions and versions != [python]:
        others = ", ".join(version for version in versions if version != python)
        standing.append(f"every gate here ran on Python {python}; continuous integration also runs {others}")
    if skipped:
        lines.append("WARNING: continuous integration runs these, and this run skipped them:")
        lines += [f"  - {gap}" for gap in skipped]
    if standing:
        lines.append("Continuous integration also runs these, which a local run never covers:")
        lines += [f"  - {gap}" for gap in standing]
    ran = len(results)
    if failed:
        verdict = f"{failed} of {ran} gates FAILED"
    elif not_run:
        verdict = f"no gate failed, but {not_run} of {ran} could not run ({NOT_FOUND_NOTE})"
    else:
        verdict = f"all {ran} gates passed"
    if skipped or standing:
        equivalence = (f"NOT EQUIVALENT TO CI ({len(skipped)} skipped in this run, {len(standing)} only in "
                       "continuous integration; listed above)")
    else:
        equivalence = "equivalent to CI"
    lines.append(f"RESULT: {verdict}; {equivalence}")
    return lines, (1 if failed else 3 if not_run else 0)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--only", default="")
    parser.add_argument("--python", default="")
    parser.add_argument("--dirty", action="store_true")
    parser.add_argument("--workflow", type=Path, default=WORKFLOW)
    arguments = parser.parse_args(argv)
    lines, status = summarize(arguments.folder, only=tuple(name for name in arguments.only.split(",") if name),
                              python=arguments.python, dirty=arguments.dirty, workflow=arguments.workflow)
    print("\n".join(lines))
    return status


if __name__ == "__main__":
    sys.exit(main())
