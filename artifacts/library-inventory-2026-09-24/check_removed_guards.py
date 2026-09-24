"""Remove each counting guard of the inventory in a disposable copy.

Each mutant changes one guard in a temporary copy of
tools/inventory_harness_library.py, runs tools/test_inventory_harness_library.py
against that copy, and records which named checks failed. The production file
is never edited. A new dated report is written each time; an existing report
is never replaced.

    python3 -B artifacts/library-inventory-2026-09-24/check_removed_guards.py
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "tools" / "inventory_harness_library.py"
TESTS = ROOT / "tools" / "test_inventory_harness_library.py"

MUTANTS = (
    ("journal line still being written is parsed",
     'cut = data.rfind(b"\\n") + 1', "cut = len(data)",
     "test_counts_journaled_candidates_not_files_on_disk"),
    ("an idea without a candidate_written outcome becomes a unit",
     'if outcome != "candidate_written":', "if False:",
     "test_counts_journaled_candidates_not_files_on_disk"),
    ("an unmapped declared value defaults to skill",
     "return KIND_VOCABULARIES[vocabulary].get(value, UNKNOWN)",
     "return KIND_VOCABULARIES[vocabulary].get(value, SKILL)",
     "test_an_unmapped_declared_value_stays_unknown"),
    ("the kind is taken from a SKILL.md file name",
     'kind=map_kind("wave 5 file class", wave.get("file_class")),',
     'kind=SKILL if (payload_root / "SKILL.md").exists() else '
     'map_kind("wave 5 file class", wave.get("file_class")),',
     "test_kind_comes_from_the_record_and_state_from_the_newest_report"),
    ("the oldest check-all report wins",
     "reports.sort(key=lambda row: (row[0], row[1]))",
     "reports.sort(key=lambda row: (row[0], row[1]), reverse=True)",
     "test_kind_comes_from_the_record_and_state_from_the_newest_report"),
    ("identities are compared without normalization",
     'return re.sub(r"[^a-z0-9]+", "_", text).strip("_")', "return raw",
     "test_an_identity_in_two_sources_counts_once"),
    ("the first record of a group is counted instead of the most advanced",
     "best = min(group, key=lambda pair: (STATE_RANK[pair[1].state], order[pair[0]]))",
     "best = group[0]",
     "test_an_identity_in_two_sources_counts_once"),
    ("declared aliases are ignored",
     "for alias in unit.aliases:\n                union(unit.key, identity_key(alias))",
     "for alias in ():\n                union(unit.key, identity_key(alias))",
     "test_a_declared_alias_joins_two_names"),
)


def run_tests(module_text: str) -> tuple[int, list[str], str]:
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        (folder / MODULE.name).write_text(module_text, encoding="utf-8")
        (folder / TESTS.name).write_text(TESTS.read_text(encoding="utf-8"), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "-v", TESTS.stem],
            cwd=folder, capture_output=True, text=True, timeout=300,
            env={"PYTHONPATH": str(folder), "PATH": "/usr/bin:/bin"})
        failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+)", completed.stderr, re.M)))
        tail = "\n".join(completed.stderr.strip().splitlines()[-3:])
        return completed.returncode, failed, tail


def main() -> int:
    source = MODULE.read_text(encoding="utf-8")
    baseline_code, baseline_failed, baseline_tail = run_tests(source)
    results = []
    for name, old, new, expected in MUTANTS:
        count = source.count(old)
        if count != 1:
            results.append({"guard": name, "control_error": f"pattern found {count} times"})
            continue
        code, failed, tail = run_tests(source.replace(old, new))
        results.append({"guard": name, "expected_failing_check": expected,
                        "suite_exit_code": code, "failed_checks": failed,
                        "detected": code != 0 and expected in failed, "suite_tail": tail})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = Path(__file__).resolve().parent / f"removed-guards-{stamp}.json"
    if report_path.exists():
        print(f"refusing to replace {report_path}", file=sys.stderr)
        return 2
    report = {
        "record_type": "inventory_removed_guard_checks/v1",
        "module": str(MODULE.relative_to(ROOT)), "tests": str(TESTS.relative_to(ROOT)),
        "python": sys.version.split()[0],
        "baseline": {"suite_exit_code": baseline_code, "failed_checks": baseline_failed,
                     "suite_tail": baseline_tail},
        "mutants": results,
        "all_detected": baseline_code == 0 and all(r.get("detected") for r in results),
    }
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "all_detected": report["all_detected"]}))
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
