"""Run the existing offline suite and bind its report to exact source bytes.

Run this from a frozen source export for release evidence. A changing tree is
retained as a failed capture, never silently accepted as a qualified snapshot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from architecture_audit_evidence import source_identity


def main() -> int:
    from loop_engine import _self_test

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    expected = repository / "src/loop_engine/_self_test.py"
    if Path(_self_test.__file__).resolve() != expected:
        raise ValueError("the imported test suite is not the selected source tree")
    before = source_identity(repository)
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    report = _self_test.self_test()
    after = source_identity(repository)
    result = {"record_type": "architecture_check_capture/v1", "started_at": started,
              "elapsed_seconds": time.monotonic() - clock,
              "source_before": before, "source_after": after,
              "source_unchanged": before == after, "suite": report,
              "provider_calls_authorized": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"output": str(args.output), "source_unchanged": before == after,
                      "passed": report["passed"], "total": report["total"],
                      "not_tested": report.get("not_tested"),
                      "elapsed_seconds": result["elapsed_seconds"]}))
    return 0 if before == after and report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
