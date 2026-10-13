"""Inspect one local email, or explicitly write it to private quarantine.

No command creates mail routing, subscribes, sends, follows links or queues
research. Dry inspection reports only counts and a digest, never raw content.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "tools"):
    sys.path.insert(0, str(directory))

from knowledge_radar.community_store import CommunityStore
from knowledge_radar.newsletter_intake import NewsletterEmail, NewsletterRefusal, RECIPIENT, inspect_mime, quarantine, read_local_mime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", type=Path)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--delivery-id", required=True)
    parser.add_argument("--envelope-sender", required=True)
    parser.add_argument("--received-at", required=True, help="Exact UTC receipt time, YYYY-MM-DDTHH:MM:SSZ; preserve it on retries.")
    parser.add_argument("--authorize-local-writes", action="store_true")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        message = NewsletterEmail(args.delivery_id, RECIPIENT, args.envelope_sender, args.received_at, read_local_mime(args.message))
        inspection = inspect_mime(message.raw)
        if args.authorize_local_writes:
            result = quarantine(CommunityStore(args.library, writes_allowed=True), message)
        else:
            result = {"record_type": "newsletter_inspection_plan/v1", "raw_sha256": message.raw_sha256,
                      "raw_bytes": len(message.raw), "mime_parts": inspection["mime_parts"], "writes": 0,
                      "sender_authentication": "not_verified", "research_admitted": False}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (NewsletterRefusal, OSError) as error:
        print(json.dumps({"refused": str(error) if isinstance(error, NewsletterRefusal) else "newsletter_file_unavailable"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
