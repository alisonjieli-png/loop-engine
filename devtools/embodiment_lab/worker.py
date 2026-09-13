"""Bounded JSON-lines worker; one fresh canonical Loop for every request."""

from __future__ import annotations

import json
import sys

from .contracts import MAX_PACKET_BYTES, WorkPacket, canonical
from .runtime import execute


def main() -> int:
    for line in iter(lambda: sys.stdin.buffer.readline(MAX_PACKET_BYTES + 2), b""):
        try:
            if len(line) > MAX_PACKET_BYTES or not line.endswith(b"\n"):
                raise ValueError("packet size or framing refused")
            packet = WorkPacket.from_dict(json.loads(line))
            result = execute(packet)
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            result = {
                "record_type": "embodiment_worker_refusal/v1",
                "error": type(exc).__name__,
                "reason": str(exc)[:200],
            }
        encoded = canonical(result).encode() + b"\n"
        if len(encoded) > MAX_PACKET_BYTES:
            encoded = b'{"record_type":"embodiment_worker_refusal/v1","reason":"response_too_large"}\n'
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
