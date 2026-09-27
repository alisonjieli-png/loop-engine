"""Check choose_model against a fixed table, including known-wrong answers it must not give. No network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import choose_model  # noqa: E402

VERIFICATION = HERE.parent / "verification"


def main() -> int:
    table = json.loads((VERIFICATION / "fixture-table.json").read_text(encoding="utf-8"))
    cases = json.loads((VERIFICATION / "cases.json").read_text(encoding="utf-8"))["cases"]
    passed = failed = known_wrong_rejected = 0
    for case in cases:
        try:
            result = choose_model.run(case["request"], table)
            error = None
        except choose_model.RequestInvalid:
            result, error = None, "request_invalid"
        first = result["chosen"][0]["title"] if result and result["chosen"] else None
        names = [row["title"] for row in result["chosen"]] if result else []
        if "known_wrong" in case:
            wrong = case["known_wrong"]
            ok = result is not None and first != wrong["first"]
            known_wrong_rejected += 1 if ok else 0
        else:
            expect = case["expect"]
            ok = (("error" not in expect or error == expect["error"])
                  and ("state" not in expect or (result is not None and result["state"] == expect["state"]))
                  and ("first" not in expect or first == expect["first"])
                  and ("absent" not in expect or expect["absent"] not in names))
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        if not ok:
            print(f"failed: {case['name']}", file=sys.stderr)
    print(json.dumps({"passed": passed, "failed": failed, "known_wrong_rejected": known_wrong_rejected}))
    return 0 if failed == 0 and known_wrong_rejected >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
