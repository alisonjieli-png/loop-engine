"""Plan one public Greenhouse metadata read; effects require explicit operator flags.

Reuse the host's quota policy and state across every board and invocation.
This command creates no scheduler and never stores job-description bodies.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "tools", ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from loop_engine.core.web_research_quota import DurableSearchQuota, QuotaRefused, SearchQuotaPolicy
from knowledge_radar.greenhouse_intake import read_once
from knowledge_radar.greenhouse_source import GreenhouseError, GreenhouseRequest
from query_multiplier.transport import RequestRefused


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--state", type=Path, help="Host-managed private CommunityStore root.")
    parser.add_argument("--quota-state", type=Path, help="Existing host-selected shared .sqlite quota path; never reset to bypass a hold.")
    parser.add_argument("--quota-policy", type=Path, help="Existing web_research_quota_policy/v1 binding for greenhouse:public-job-board.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--enqueue", action="store_true")
    parser.add_argument("--prepare-work", action="store_true", help="Prepare deferred research work orders; title hints need task evidence.")
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    args = parser.parse_args(argv)
    if args.execute and not (args.state and args.quota_state and args.quota_policy
                             and args.authorize_network_reads and args.authorize_local_writes):
        parser.error("--execute requires state, shared quota paths and both authorization flags")
    if (args.enqueue or args.prepare_work) and not args.execute:
        parser.error("record preparation requires --execute and its grants")
    if args.prepare_work and not args.enqueue:
        parser.error("--prepare-work requires --enqueue")
    os.umask(0o077)
    try:
        request = GreenhouseRequest(args.board, args.limit)
        quota = None
        if args.execute:
            if args.quota_policy.is_symlink() or args.quota_policy.stat().st_size > 65536:
                raise ValueError("quota_policy_file_invalid")
            policy = SearchQuotaPolicy.from_record(json.loads(args.quota_policy.read_text()))
            quota = DurableSearchQuota(args.quota_state, policy, allow_writes=True)
        report = read_once(request, args.state, quota=quota, network_allowed=args.execute,
                           writes_allowed=args.execute, queue_results=args.enqueue, prepare_work=args.prepare_work)
    except (ValueError, OSError, RuntimeError) as error:
        reason = str(error) if isinstance(error, (GreenhouseError, QuotaRefused, RequestRefused)) else type(error).__name__
        print(json.dumps({"status": "refused", "reason": reason}))
        return 1
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 1 if report.get("status") in ("failed", "refused") else 0


if __name__ == "__main__":
    raise SystemExit(main())
