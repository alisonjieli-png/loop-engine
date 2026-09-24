"""Removed-guard controls for the generator's draft admission step.

Each control removes one guard in memory only and runs the named check. A
control is detected when the check passes on the real source and fails with
the guard removed. No provider is called: the checks use the fixture gateway.
"""
from __future__ import annotations

import hashlib
import inspect
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "tools")]

from loop_engine.core.model_response_admission import (
    ModelResponseAdmissionPolicy,
    ModelResponseContract,
)
from tools import generate_original_native_candidates as generation

CHECKS = "tools.test_generate_original_native_candidates.GenerationTest."


def run(names):
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(CHECKS + name) for name in names)
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    return {"passed": result.wasSuccessful(), "run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors)}


def function_mutant(name, before, after, names):
    source = inspect.getsource(getattr(generation, name))
    if source.count(before) != 1:
        raise RuntimeError("a control must replace exactly one guard: " + before[:60])
    namespace = dict(generation.__dict__)
    exec(compile(source.replace(before, after), generation.__file__, "exec"), namespace)  # noqa: S102 - fixed in-memory controls
    with patch.object(generation, name, namespace[name]):
        return run(names)


def main():
    strict_only = ModelResponseContract(generation.DRAFT_TYPE, json.dumps(generation.DRAFT_SCHEMA),
                                        ModelResponseAdmissionPolicy(allowed_strategies=("strict_json",)))
    controls = [
        ("fence_repair_not_permitted", lambda names: _patched("DRAFT_ADMISSION", strict_only, names),
         ["test_exact_markdown_json_fence_is_admitted_and_recorded_not_silent"]),
        ("draft_schema_not_checked", lambda names: function_mutant(
            "admit_draft", "DRAFT_ADMISSION.content_digest, DRAFT_SCHEMA,", "DRAFT_ADMISSION.content_digest, None,",
            names), ["test_other_wrappers_and_invalid_or_extended_drafts_are_not_admitted"]),
        ("unadmitted_draft_reaches_the_parser", lambda names: function_mutant(
            "generate", "if not admitted.admitted:\n                            refuse(\"draft_json_not_admitted\")",
            "if False:\n                            refuse(\"draft_json_not_admitted\")", names),
         ["test_other_wrappers_and_invalid_or_extended_drafts_are_not_admitted"]),
        ("repair_not_recorded", lambda names: function_mutant(
            "generate", "\"response_admission\": admission_record}", "\"response_admission\": None}", names),
         ["test_exact_markdown_json_fence_is_admitted_and_recorded_not_silent"]),
    ]
    rows = []
    for identity, remove, names in controls:
        baseline = run(names)
        removed = remove(names)
        rows.append({"guard": identity, "checks": names, "baseline": baseline, "removed": removed,
                     "detected": baseline["passed"] and not removed["passed"]})
    report = {"record_type": "draft_admission_removed_guards/v1", "provider_calls": 0,
              "at": datetime.now(timezone.utc).isoformat(),
              "source_sha256": hashlib.sha256(Path(generation.__file__).read_bytes()).hexdigest(),
              "all_detected": all(row["detected"] for row in rows), "controls": len(rows), "results": rows}
    output = Path(__file__).with_name(
        "removed-guards-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + ".json")
    output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(output), "all_detected": report["all_detected"], "controls": len(rows),
                      "missed": [row["guard"] for row in rows if not row["detected"]]}))
    return 0 if report["all_detected"] else 1


def _patched(name, value, names):
    with patch.object(generation, name, value):
        return run(names)


if __name__ == "__main__":
    raise SystemExit(main())
