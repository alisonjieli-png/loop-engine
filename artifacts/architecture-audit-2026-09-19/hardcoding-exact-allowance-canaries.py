"""Check exact hardcoding allowances without changing source or detector rules.

Canary source trees exist only in memory. The existing literal visitor and
exact allowlist loader classify them at their actual owning source paths.
This does not execute the described generated project or call a model.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

from loop_engine_devtools.assurance.hardcoding import (
    _PythonLiteralVisitor, _load_allowlist, self_test,
)

RESOURCE_PATH = "src/loop_engine/strings/capability_resources.py"
RESOURCE_FINDING = "hardcoding.0c9114d720b507d67cc4afd0"
EXPECTED_NEW = {
    "hardcoding.53438b7213f3f26b6e4d37f6",
    "hardcoding.7c8caf2630173802d1c64cd9",
    "hardcoding.86322e44eb95347b74b539aa",
    RESOURCE_FINDING,
}


def classify(root, relative, text):
    tree = ast.parse(text)
    visitor = _PythonLiteralVisitor(root, root / relative, tree, "in_memory_canary", False, {})
    visitor.visit(tree)
    findings = {row.finding_id: row for row in visitor.findings}
    allowed, problems = _load_allowlist(root / "devtools/hardcoding-allowlist.yaml", findings,
                                      require_present=False)
    high = [row for row in findings.values() if row.severity in ("high", "critical")]
    return {"high": [row.finding_id for row in high],
            "suppressed_high": [row.finding_id for row in high if row.finding_id in allowed],
            "unsuppressed_high": [row.finding_id for row in high if row.finding_id not in allowed],
            "allowlist_problems": problems}


def main():
    root = Path.cwd()
    source = (root / RESOURCE_PATH).read_text()
    baseline = classify(root, RESOURCE_PATH, source)
    changed = classify(root, RESOURCE_PATH, source.replace(
        "Create files, execute Python commands", "Create different files, execute Python commands", 1))
    planted = classify(root, RESOURCE_PATH, source + "\nUNREVIEWED_SYSTEM_PROMPT = " + repr(
        "You are a candidate instruction with no registered resource identity. Do not execute anything. " * 8) + "\n")
    moved = classify(root, "src/loop_engine/strings/another_resource.py", source)
    observations_path = "src/loop_engine/core/practitioner_runtime/observations.py"
    observations = classify(root, observations_path, (root / observations_path).read_text() +
        "\ndef newly_planted_raw_state(status):\n    return status == 'unreviewed_state'\n")
    old = yaml.safe_load(subprocess.check_output(
        ["git", "show", "HEAD:devtools/hardcoding-allowlist.yaml"], text=True))
    current = yaml.safe_load((root / "devtools/hardcoding-allowlist.yaml").read_text())
    by_id = {row["finding_id"]: row for row in current["entries"]}
    old_ids = {row["finding_id"] for row in old["entries"]}
    added = set(by_id) - old_ids
    detector = self_test()
    checks = {
        "exact_reviewed_resource_only_is_suppressed": baseline["suppressed_high"] == [RESOURCE_FINDING]
        and not baseline["unsuppressed_high"],
        "changed_text_loses_exception": bool(changed["unsuppressed_high"])
        and RESOURCE_FINDING not in changed["suppressed_high"],
        "unreviewed_prompt_in_same_file_remains_blocking": len(planted["unsuppressed_high"]) == 1
        and planted["suppressed_high"] == [RESOURCE_FINDING],
        "same_text_at_another_path_remains_blocking": bool(moved["unsuppressed_high"])
        and not moved["suppressed_high"],
        "new_state_branch_in_allowed_owner_remains_blocking": bool(observations["unsuppressed_high"]),
        "exactly_four_entries_added": added == EXPECTED_NEW,
        "all_previous_entries_preserved_exactly": all(by_id.get(row["finding_id"]) == row for row in old["entries"]),
        "file_exclusions_unchanged": old.get("excluded_paths") == current.get("excluded_paths"),
        "no_duplicate_finding_entries": len(by_id) == len(current["entries"]),
        "all_existing_detector_canaries_pass": detector["all_passed"],
        "no_allowlist_problems_in_canaries": not any(row["allowlist_problems"]
            for row in (baseline, changed, planted, moved, observations)),
    }
    paths = (RESOURCE_PATH, observations_path, "devtools/hardcoding-allowlist.yaml",
             "devtools/hardcoding-ci-baseline.json", "devtools/src/loop_engine_devtools/assurance/hardcoding.py")
    result = {"record_type": "hardcoding_exact_allowance_canaries/v1", "checks": checks,
              "passed": all(checks.values()), "added_finding_ids": sorted(added),
              "source_cases": {"reviewed": baseline, "changed_text": changed,
                               "additional_unreviewed_prompt": planted, "another_path": moved,
                               "additional_state_branch": observations},
              "existing_detector_checks": {"passed": detector["passed"], "total": detector["total"]},
              "source_sha256": {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
