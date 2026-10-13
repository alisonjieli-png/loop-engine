"""Plan or parse a bounded PyPI Simple Index v1 JSON metadata read.

Default invocation prints a deterministic plan with zero network calls or writes.
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
from knowledge_radar.pypi_releases import MAXIMUM_RESPONSE_BYTES
from knowledge_radar.pypi_releases import PyPIReadError, PyPIRequest, parse_simple_index


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--pinned-version", default=None)
    parser.add_argument("--target-platform", default="manylinux")
    parser.add_argument("--max-releases", type=int, default=20)
    parser.add_argument("--input-capture", type=Path, help="Local PyPI Simple v1 JSON capture to parse offline.")
    parser.add_argument("--observed-on", help="Capture date (required when parsing a file).")
    args = parser.parse_args(argv)
    try:
        request = PyPIRequest(
            project=args.project,
            pinned_version=args.pinned_version,
            target_platform=args.target_platform,
            max_releases=args.max_releases,
        )
        if args.input_capture is None:
            print(json.dumps(request.plan(), sort_keys=True, indent=2, allow_nan=False))
            return 0
        if args.observed_on is None:
            raise ValueError("source_capture_date_required")
        if args.input_capture.is_symlink():
            raise PyPIReadError("pypi_capture_symlink_refused")
        observation = parse_simple_index(read_capture(args.input_capture, MAXIMUM_RESPONSE_BYTES), request, observed_on=args.observed_on)
        print(json.dumps(observation, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (PyPIReadError, OSError, ValueError) as exc:
        code = getattr(exc, "code", type(exc).__name__)
        print(json.dumps({"status": "refused", "reason": code}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
