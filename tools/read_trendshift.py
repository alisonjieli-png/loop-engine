"""Inspect one Trendshift selection or record a bounded read in private research.

Defaults to a plan with no network or writes. Signal requires an existing
subscription key in TRENDSHIFT_API_KEY; public mode reads only current daily
JSON-LD. Neither mode publishes data, installs a schedule or sends outreach.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "tools", ROOT):
    if str(directory) not in sys.path:sys.path.insert(0, str(directory))

from knowledge_radar.trendshift_intake import import_capture, parse_capture, read_once, reconcile_unknown
from knowledge_radar.trendshift_request import KINDS, PUBLIC, SIGNAL, TRENDING, TrendshiftError, TrendshiftRequest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=(SIGNAL, PUBLIC), default=SIGNAL)
    parser.add_argument("--kind", choices=KINDS, default=TRENDING)
    parser.add_argument("--window", choices=("daily", "weekly", "monthly", "yearly"), default="daily")
    parser.add_argument("--period", help="Historical YYYY-MM-DD, YYYY-Www, YYYY-MM or year, matching --window.")
    parser.add_argument("--language")
    parser.add_argument("--limit", type=int, default=25, help="Maximum private observations, 1-60; no automatic pagination.")
    parser.add_argument("--cursor", help="Opaque Signal cursor. Absolute rank remains unknown for cursor pages.")
    parser.add_argument("--metric", choices=("stars", "forks", "merged_prs", "issues", "closed_issues"))
    parser.add_argument("--start", help="Required inclusive YYYY-MM-DD for spikes.")
    parser.add_argument("--end", help="Required inclusive YYYY-MM-DD for spikes.")
    parser.add_argument("--min-gain", type=int, default=100)
    parser.add_argument("--max-gain", type=int)
    parser.add_argument("--state", type=Path, help="Existing host-managed private CommunityStore root; reuse it across engines and keys.")
    parser.add_argument("--execute", action="store_true", help="Make at most one read; needs both authorization flags and --state.")
    parser.add_argument("--input", type=Path, help="Parse a bounded local response instead; it is not marked transport-verified.")
    parser.add_argument("--observed-at", help="UTC timestamp for an input capture only. Live reads use the host clock.")
    parser.add_argument("--enqueue", action="store_true", help="Record private needs-research leads; grants no execution or publication.")
    parser.add_argument("--reconcile-unknown", action="store_true", help="Close a crashed read as unknown without refunding its reservation; sends nothing.")
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    args = parser.parse_args(argv)
    if args.execute and (args.input or args.observed_at or args.reconcile_unknown):parser.error("live reads cannot use capture or reconciliation flags")
    if args.reconcile_unknown and (args.input or args.enqueue):parser.error("reconciliation cannot import or enqueue a capture")
    if args.execute and not (args.authorize_network_reads and args.authorize_local_writes and args.state):
        parser.error("--execute requires --state and both authorization flags")
    if (args.enqueue or args.reconcile_unknown) and not (args.state and args.authorize_local_writes):
        parser.error("private record writes require --state and --authorize-local-writes")
    if args.enqueue and not (args.input or args.execute):parser.error("--enqueue requires --input or --execute")
    if args.observed_at and not args.input:parser.error("--observed-at is only for --input")
    os.umask(0o077)
    try:
        request = TrendshiftRequest(args.engine, args.kind, args.window, args.period, args.language, args.limit,
                                   args.cursor, args.metric, args.start, args.end, args.min_gain, args.max_gain)
        if args.reconcile_unknown:
            report = reconcile_unknown(args.state, writes_allowed=True)
        elif args.input:
            report, observations = parse_capture(request, args.input, observed_at=args.observed_at)
            if args.enqueue:report = import_capture(request, args.state, report, observations, writes_allowed=True)
        else:
            report = read_once(request, args.state, network_allowed=args.execute, writes_allowed=args.execute,
                               queue_results=args.enqueue)
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({"status": "refused", "reason": error.code if isinstance(error, TrendshiftError) else type(error).__name__}))
        return 1
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 1 if report.get("status") in ("failed", "refused", "reconcile_required", "source_hold", "needs_verified_quota_reconciliation") else 0


if __name__ == "__main__":raise SystemExit(main())
