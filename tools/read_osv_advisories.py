"""Plan or parse a bounded OSV batch advisory query.

Default invocation prints the querybatch plan with zero network calls or writes.
Use --input-capture <file> --observed-on YYYY-MM-DD to evaluate a local capture.
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
from knowledge_radar.osv_advisories import MAXIMUM_RESPONSE_BYTES
from knowledge_radar.osv_advisories import OSVBatchRequest, OSVQueryError, PackagePin, parse_batch_response


def _parse_pin(spec: str) -> PackagePin:
    # Expected format: Ecosystem:package@version (e.g. PyPI:pydantic@2.9.2)
    if ":" not in spec or "@" not in spec:
        raise OSVQueryError("osv_pin_spec_invalid")
    eco, rest = spec.split(":", 1)
    pkg, ver = rest.rsplit("@", 1)
    return PackagePin(ecosystem=eco, name=pkg, version=ver)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pin", action="append", required=True, help="Package pin as Ecosystem:package@version")
    parser.add_argument("--input-capture", type=Path, help="Local OSV querybatch JSON response to parse offline.")
    parser.add_argument("--observed-on", help="Capture date (required when parsing a file).")
    args = parser.parse_args(argv)
    try:
        pins = tuple(_parse_pin(item) for item in args.pin)
        request = OSVBatchRequest(pins=pins)
        if args.input_capture is None:
            print(json.dumps(request.plan(), sort_keys=True, indent=2, allow_nan=False))
            return 0
        if args.observed_on is None:
            raise ValueError("source_capture_date_required")
        if args.input_capture.is_symlink():
            raise OSVQueryError("osv_capture_symlink_refused")
        observation = parse_batch_response(read_capture(args.input_capture, MAXIMUM_RESPONSE_BYTES), request, observed_on=args.observed_on)
        print(json.dumps(observation, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (OSVQueryError, OSError, ValueError) as exc:
        code = getattr(exc, "code", type(exc).__name__)
        print(json.dumps({"status": "refused", "reason": code}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
