"""List private receipt identities or show one private newsletter safely.

Defaults to a plan without credentials or network. No command follows links,
sends mail, changes provider storage, or admits research. Keep private views
out of terminal recordings, shared logs, public reports and model prompts.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    sys.path.insert(0, str(folder))

from knowledge_radar.community_store import CommunityStore
from knowledge_radar.newsletter_intake import NewsletterRefusal, read_private_receipt, quarantine
from knowledge_radar.newsletter_reader import (NewsletterR2Reader, load_binding, private_mail_view,
                                             transport_main, RECEIPT_KEY)


def main(argv=None):
    args_in = sys.argv[1:] if argv is None else argv
    if args_in == ["--transport"]:
        return transport_main()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("list", "show", "import"))
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--receipt-key")
    parser.add_argument("--after", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--library", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    parser.add_argument("--show-private", action="store_true", help="Print private text and token-bearing manual links as inert JSON.")
    args = parser.parse_args(args_in)
    os.umask(0o077)
    try:
        binding = load_binding(args.binding)
        if args.operation in ("show", "import") and (not args.receipt_key or not RECEIPT_KEY.fullmatch(args.receipt_key)):
            raise NewsletterRefusal("newsletter_reader_receipt_required")
        if args.operation == "show" and args.execute and not args.show_private:
            raise NewsletterRefusal("newsletter_reader_private_view_grant_required")
        if args.operation == "import" and args.execute and (not args.library or not args.authorize_local_writes):
            raise NewsletterRefusal("newsletter_reader_local_write_grant_required")
        if not args.execute:
            print(json.dumps({"record_type": "newsletter_reader_plan/v1", "operation": args.operation,
                              "account_id": binding.account_id, "bucket": binding.bucket,
                              "network_reads": 0, "credential_reads": 0, "writes": 0}))
            return 0
        if not args.authorize_network_reads:
            raise NewsletterRefusal("newsletter_reader_network_grant_required")
        from operator_credentials import resolve
        reader = NewsletterR2Reader(binding, resolve)
        if args.operation == "list":
            result = reader.list_receipts(limit=args.limit, after=args.after)
        else:
            message = read_private_receipt(args.receipt_key, reader, bucket=binding.bucket)
            result = (private_mail_view(message) if args.operation == "show"
                      else quarantine(CommunityStore(args.library, writes_allowed=True), message,
                                      ingress_provenance="host_authenticated_private_object_read"))
        # ASCII JSON escapes terminal controls, newlines and directional marks.
        # It is text, never HTML or terminal hyperlink escape sequences.
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"refused": str(error) if isinstance(error, NewsletterRefusal) else "newsletter_reader_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
