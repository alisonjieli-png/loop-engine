"""Require a fresh passing check on the exact deployed image before public readiness.

Reads a bounded Machines listing from stdin. It calls no provider, prints no
Machine configuration, and changes nothing.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys

MAXIMUM_LISTING_BYTES = 1024 * 1024
HTTP_CHECK = "servicecheck-00-http-8080"


def exact_machine_ready(machines, image):
    """Old-image readiness and a previous boot's cached health are not this release."""
    match = re.fullmatch(r"registry\.fly\.io/([a-z0-9][a-z0-9-]{0,62})@(sha256:[0-9a-f]{64})", image)
    if not match or not isinstance(machines, list) or len(machines) != 1:
        return False
    machine = machines[0]
    if not isinstance(machine, dict) or machine.get("state") != "started":
        return False
    ref = machine.get("image_ref") or {}
    if (not isinstance(ref, dict) or ref.get("registry") != "registry.fly.io"
            or ref.get("repository") != match.group(1) or ref.get("digest") != match.group(2)):
        return False
    events = machine.get("events")
    checks = machine.get("checks")
    if not isinstance(events, list) or not isinstance(checks, list):
        return False
    starts = [event.get("timestamp") for event in events if isinstance(event, dict)
              and event.get("type") == "start" and event.get("status") == "started"
              and type(event.get("timestamp")) in (int, float) and event["timestamp"] > 0]
    if not starts:
        return False
    for check in checks:
        if not isinstance(check, dict) or check.get("name") != HTTP_CHECK or check.get("status") != "passing":
            continue
        try:
            at = datetime.datetime.fromisoformat(check["updated_at"].replace("Z", "+00:00"))
            if at.tzinfo is not None and at.timestamp() * 1000 >= max(starts):
                return True
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
            continue
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    options = parser.parse_args(argv)
    raw = sys.stdin.buffer.read(MAXIMUM_LISTING_BYTES + 1)
    if len(raw) > MAXIMUM_LISTING_BYTES:
        return 1
    try:
        machines = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return 1
    return 0 if exact_machine_ready(machines, options.image) else 1


if __name__ == "__main__":
    raise SystemExit(main())
