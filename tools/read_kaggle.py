"""Plan or run one metadata-only Kaggle read, never a notebook or dataset download.

The default is a no-effect plan. Execution needs network and private-write
grants, a persistent state root and an existing keyring credential reference.
check_auth proves active account-token status without retaining identity.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "src", ROOT / "tools"):
    if str(directory) not in sys.path:sys.path.insert(0, str(directory))

from knowledge_radar.kaggle_intake import KaggleReadOptions, read_once, reconcile_unknown
from knowledge_radar.kaggle_request import MAXIMUM_REQUESTS, OPERATIONS, SORTS, KaggleError, KaggleRequest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=OPERATIONS)
    parser.add_argument("--competition")
    parser.add_argument("--query", help="Public, non-confidential search words only.")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=10, help="1-20 for lists; no automatic pagination.")
    parser.add_argument("--cursor", help="Opaque returned page token; not a URL or credential.")
    parser.add_argument("--sort", choices=tuple(SORTS), default="votes", help="Notebook list order, not a quality or adoption score.")
    parser.add_argument("--page-name", help="Exact published page name; metadata/references only, no body export.")
    parser.add_argument("--state", type=Path, help="Reuse one private CommunityStore root across operations and credentials.")
    parser.add_argument("--credential-reference", default="kaggle-research-primary")
    parser.add_argument("--credential-manifest", type=Path, help="Trusted host-managed reference manifest, never a token file.")
    parser.add_argument("--request-ceiling", type=int, default=MAXIMUM_REQUESTS, help="Persistent session ceiling, 1-20. Cannot change an existing scope.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--enqueue", action="store_true", help="Save unapproved private leads in the existing managed queue.")
    parser.add_argument("--reconcile-unknown", action="store_true", help="Close an unknown read without retry or refund; retains holds.")
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    args = parser.parse_args(argv)
    if args.execute and not (args.state and args.authorize_network_reads and args.authorize_local_writes):
        parser.error("--execute requires --state and both authorization flags")
    if args.enqueue and not args.execute:parser.error("--enqueue requires --execute")
    if args.reconcile_unknown and (args.execute or args.enqueue):parser.error("reconciliation cannot send or enqueue")
    if args.reconcile_unknown and not (args.state and args.authorize_local_writes):parser.error("reconciliation requires private state and local-write authority")
    os.umask(0o077)
    try:
        request = KaggleRequest(args.operation, args.competition, args.query, args.page, args.page_size, args.cursor, args.sort, args.page_name)
        options = KaggleReadOptions(args.state, args.execute, args.execute or args.reconcile_unknown, args.enqueue,
                                   args.credential_reference, args.credential_manifest, args.request_ceiling)
        report = reconcile_unknown(options) if args.reconcile_unknown else read_once(request, options)
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({"state": "refused", "reason": error.code if isinstance(error, KaggleError) else type(error).__name__}))
        return 1
    print(json.dumps({key: value for key, value in report.items() if key != "items"}, sort_keys=True, indent=2))
    return 0 if report.get("state") in ("plan", "ok", "empty", "partial", "closed_unknown", "nothing_to_reconcile") else 1


if __name__ == "__main__":raise SystemExit(main())
