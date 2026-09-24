"""Removed-guard controls for the delimited-block draft format.

Each control removes one guard in memory only and runs the named checks. A
control is detected when the checks pass on the real source and fail with the
guard removed. No provider is called: the checks use the fixture gateway.
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

from tools import generate_original_native_candidates as generation

CHECKS = "tools.test_generate_original_native_candidates.GenerationTest."
KNOWN_WRONG = "test_known_wrong_block_answers_are_refused_with_their_reason"
FENCE = "test_one_enclosing_fence_around_blocks_is_removed_and_recorded"
CONTROLS = [
    ("unterminated_block_accepted", "parse_blocks", 'refuse("draft_block_unterminated")', "break", [KNOWN_WRONG]),
    ("duplicate_path_accepted", "parse_blocks", 'if path in found:\n            refuse("draft_path_duplicate")',
     'if False:\n            refuse("draft_path_duplicate")', [KNOWN_WRONG]),
    ("escaping_path_not_checked", "parse_blocks", "            placement_path(path)\n", "            pass\n",
     [KNOWN_WRONG]),
    ("content_between_blocks_skipped", "parse_blocks", 'refuse("draft_content_outside_blocks")', "continue",
     [KNOWN_WRONG]),
    ("content_after_end_accepted", "parse_blocks",
     'if any(line.strip() for line in lines[index:]):\n        refuse("draft_content_after_end")',
     'if False:\n        refuse("draft_content_after_end")', [KNOWN_WRONG]),
    ("missing_file_not_named", "parse_blocks", 'if found != planned:\n        refuse("draft_missing_planned_files")',
     'if False:\n        refuse("draft_missing_planned_files")', [KNOWN_WRONG]),
    ("missing_end_line_accepted", "parse_blocks", 'if not ended:\n        refuse("draft_blocks_end_missing")',
     'if False:\n        refuse("draft_blocks_end_missing")', [KNOWN_WRONG]),
    ("header_not_checked", "parse_blocks",
     'if header != {"record_type": BLOCKS_TYPE, "method_id": method["id"]}:', "if False:", [KNOWN_WRONG]),
    ("empty_file_not_named", "parse_blocks", 'if not "".join(content).strip():', "if False:", [KNOWN_WRONG]),
    ("fence_removal_not_recorded", "admit_blocks",
     'strategy, body = "blocks_markdown_fence_removed", fenced.group("body")', 'body = fenced.group("body")', [FENCE]),
    ("fence_repair_absent", "admit_blocks", "fenced = BLOCKS_FENCE.fullmatch(text_value)", "fenced = None", [FENCE]),
    ("format_not_named_in_run_record", "generate",
     '"draft_format": {"name": request.draft_format, "record_type": form["record_type"]},', '"draft_format": None,',
     ["test_blocks_draft_prepares_a_candidate_and_the_run_names_its_format"]),
]


def run(names):
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(CHECKS + name) for name in names)
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    return {"passed": result.wasSuccessful(), "run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors)}


def mutant(name, before, after, names):
    source = inspect.getsource(getattr(generation, name))
    if source.count(before) != 1:
        raise RuntimeError("a control must replace exactly one guard: " + before[:60])
    namespace = dict(generation.__dict__)
    exec(compile(source.replace(before, after), generation.__file__, "exec"), namespace)  # noqa: S102 - fixed in-memory controls
    with patch.object(generation, name, namespace[name]):
        return run(names)


def main():
    rows = []
    for identity, function, before, after, names in CONTROLS:
        baseline = run(names)
        removed = mutant(function, before, after, names)
        rows.append({"guard": identity, "function": function, "checks": names, "baseline": baseline,
                     "removed": removed, "detected": baseline["passed"] and not removed["passed"]})
    report = {"record_type": "draft_blocks_removed_guards/v1", "provider_calls": 0,
              "at": datetime.now(timezone.utc).isoformat(),
              "source_sha256": hashlib.sha256(Path(generation.__file__).read_bytes()).hexdigest(),
              "all_detected": all(row["detected"] for row in rows), "controls": len(rows), "results": rows}
    output = Path(__file__).with_name(
        "removed-guards-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + ".json")
    output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(output), "all_detected": report["all_detected"], "controls": len(rows),
                      "missed": [row["guard"] for row in rows if not row["detected"]]}))
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
