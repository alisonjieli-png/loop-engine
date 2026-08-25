"""One-task DS-1000 evaluator entrypoint for the locked sandbox image.

The host sends one JSON object over stdin. The image contains the exact pinned
upstream execution helper, but it contains no benchmark data, reference
solution, task prompt, or generated answer. Network and writable-root controls
are applied by the host runner.
"""
from __future__ import annotations

import hashlib
import json
import sys

import execution


EXPECTED_KEYS = {"problem_id", "library", "code_context", "candidate"}


def main() -> int:
    payload = json.load(sys.stdin)
    if set(payload) != EXPECTED_KEYS:
        raise ValueError(
            "evaluator input must contain only problem_id, library, "
            "code_context, and candidate")
    problem_id = int(payload["problem_id"])
    library = str(payload["library"])
    code_context = str(payload["code_context"])
    candidate = str(payload["candidate"])
    if not candidate.strip():
        raise ValueError("candidate code is empty")
    if "def test_execution" not in code_context:
        raise ValueError("pinned task context has no test_execution function")

    test_program = (
        code_context
        + "\n"
        + f"code = {candidate!r}\n"
        + "test_execution(code)\n"
        + ("test_string(code)\n" if "test_string(" in code_context else "\n")
    )
    result = execution.check_correctness(
        test_program, timeout=120, completion_id=problem_id)
    print(json.dumps({
        "record_type": "ds1000_upstream_evaluation/v1",
        "problem_id": problem_id,
        "library": library,
        "passed": bool(result["passed"]),
        "result": str(result["result"]),
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "test_execution": True,
        "test_string": "test_string(" in code_context,
        "upstream_timeout_seconds": 120,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
