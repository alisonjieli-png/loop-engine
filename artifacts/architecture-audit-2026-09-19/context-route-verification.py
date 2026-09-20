"""Offline context-route checks and known-wrong guard replacements, without source edits."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path.cwd()
spec = importlib.util.spec_from_file_location("context_checks", ROOT / "tools/test_context_routes.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def run(suite):
    result = unittest.TestResult()
    suite.run(result)
    return {"checks": result.testsRun, "failures": [str(test) for test, _ in result.failures],
            "errors": [str(test) for test, _ in result.errors], "skipped": len(result.skipped)}


def main():
    baseline = run(unittest.defaultTestLoader.loadTestsFromTestCase(checks.ContextRouteTests))
    mutants = []
    for name, attribute, replacement, tests in (
            ("ignore_stale_context_and_missing_routes", "route_findings", lambda _: [],
             ("test_old_publish_instruction_is_detected", "test_old_outcome_reader_promise_is_detected",
              "test_lost_current_route_is_detected")),
            ("ignore_changed_snapshot_bytes", "snapshot_findings", lambda *_: [],
             ("test_changed_snapshot_is_detectable",)),
            ("ignore_broken_local_targets_and_anchors", "local_link_findings", lambda *_args, **_kwargs: {"findings": []},
             ("test_missing_file_and_fragment_controls_are_detected",)),
            ("ignore_removed_owner_behavior", "owner_explanation", lambda _: "same",
             ("test_removing_owner_behavior_from_the_explanation_is_detectable",))):
        with patch.object(checks, attribute, replacement):
            observed = run(unittest.TestSuite(checks.ContextRouteTests(test) for test in tests))
        mutants.append({"name": name, "detected": bool(observed["failures"]), **observed})
    links = checks.local_link_findings(ROOT, checks.documentation_scope(ROOT))
    manifest = json.loads((ROOT / checks.SNAPSHOT / "manifest.json").read_text())
    paths = [*checks.ACTIVE, "tools/test_context_routes.py", checks.SNAPSHOT + "/manifest.json"]
    sizes = []
    for row in manifest["files"]:
        before = (ROOT / row["snapshot_path"]).read_text()
        after = (ROOT / row["original_path"]).read_text()
        sizes.append({"path": row["original_path"], "before_lines": len(before.splitlines()),
                      "after_lines": len(after.splitlines())})
    output = {"record_type": "context_route_verification/v1", "date": "2026-09-19",
              "baseline": baseline, "mutants": mutants, "local_links": links,
              "snapshot_bytes_verified": not checks.snapshot_findings(manifest, lambda path: (ROOT / path).read_bytes()),
              "document_sizes": sizes,
              "source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths},
              "passed": not (baseline["failures"] or baseline["errors"] or baseline["skipped"] or links["findings"])
              and all(row["detected"] and not row["errors"] for row in mutants),
              "limits": ["Documentation and local-link checks do not qualify runtime behavior or a deployed service.",
                         "Remote URLs, dynamic HTML, JavaScript routes, and example execution are outside this check.",
                         "Other inventory candidates remain unchanged and need separate coordinated remediation."]}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
