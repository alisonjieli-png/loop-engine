"""Plan or parse a bounded endoflife.date v1 release cycle check.

Default invocation prints the request plan with zero network calls or writes.
Use --input-capture <file> --as-of YYYY-MM-DD to evaluate a local capture.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "tools", ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from knowledge_radar.source_capture import read_capture
from knowledge_radar.endoflife_cycles import MAXIMUM_RESPONSE_BYTES
from knowledge_radar.endoflife_cycles import EndOfLifeReadError, EndOfLifeRequest, parse_product_cycles


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", required=True)
    parser.add_argument("--pinned-cycle", default=None)
    parser.add_argument("--warning-window-days", type=int, default=90)
    parser.add_argument("--input-capture", type=Path, help="Local endoflife.date JSON capture to parse offline.")
    parser.add_argument("--as-of", help="Capture date (required when parsing a file).")
    args = parser.parse_args(argv)
    try:
        request = EndOfLifeRequest(
            product=args.product,
            pinned_cycle=args.pinned_cycle,
            warning_window_days=args.warning_window_days,
        )
        if args.input_capture is None:
            print(json.dumps(request.plan(), sort_keys=True, indent=2, allow_nan=False))
            return 0
        if args.as_of is None:
            raise ValueError("source_capture_date_required")
        if args.input_capture.is_symlink():
            raise EndOfLifeReadError("endoflife_capture_symlink_refused")
        observation = parse_product_cycles(read_capture(args.input_capture, MAXIMUM_RESPONSE_BYTES), request, as_of=args.as_of)
        print(json.dumps(observation, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (EndOfLifeReadError, OSError, ValueError) as exc:
        code = getattr(exc, "code", type(exc).__name__)
        print(json.dumps({"status": "refused", "reason": code}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
