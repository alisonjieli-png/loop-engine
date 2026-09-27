"""Check check_support_window against a fixed calendar, including known-wrong answers. No network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_support_window  # noqa: E402

VERIFICATION = HERE.parent / "verification"


def main() -> int:
    calendar = json.loads((VERIFICATION / "fixture-calendar.json").read_text(encoding="utf-8"))
    record = json.loads((VERIFICATION / "cases.json").read_text(encoding="utf-8"))
    passed = failed = known_wrong_rejected = 0
    for case in record["cases"]:
        today = case.get("today", record["today"])
        try:
            result, error = check_support_window.run(case["request"], calendar, today), None
        except check_support_window.RequestInvalid:
            result, error = None, "request_invalid"
        if "known_wrong" in case:
            ok = result is not None and result["state"] != case["known_wrong"]["state"]
            known_wrong_rejected += 1 if ok else 0
        else:
            expect = case["expect"]
            ok = (("error" not in expect or error == expect["error"])
                  and ("state" not in expect or (result is not None and result["state"] == expect["state"]))
                  and ("cycle" not in expect or (result is not None and result["cycle"] == expect["cycle"])))
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        if not ok:
            print(f"failed: {case['name']}", file=sys.stderr)
    print(json.dumps({"passed": passed, "failed": failed, "known_wrong_rejected": known_wrong_rejected}))
    return 0 if failed == 0 and known_wrong_rejected >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
