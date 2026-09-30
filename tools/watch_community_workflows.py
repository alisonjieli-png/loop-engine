"""Internal recurring community discovery, research and component-work intake.

Dry runs perform no writes or network calls. Enable bounded local intake and
public reads explicitly; native web research has a separate invocation grant.
The existing knowledge radar, managed-record store, reactive scheduler and
canonical Loops own the work. No command publishes a component or social post.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "src", ROOT / "tools", ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from knowledge_radar.community_intake import REGISTRY, read_registry
from knowledge_radar.community_store import CommunityStore
from knowledge_radar.community_watch import tick


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    parser.add_argument("--authorize-native-research", action="store_true")
    parser.add_argument("--force-feed-check", action="store_true")
    parser.add_argument("--list", choices=("source", "lead", "research_brief", "run"))
    parser.add_argument("--limit", type=int, default=50)
    options = parser.parse_args(argv)
    os.umask(0o077)
    if options.list:
        rows = CommunityStore(options.library).query(kind=options.list, limit=options.limit)
        print(json.dumps({"kind": options.list, "returned": len(rows), "limit": options.limit, "records": rows}, indent=2))
        return 0
    registry = read_registry(options.registry)
    report = tick(registry, options.library, network_allowed=options.authorize_network_reads,
                  writes_allowed=options.authorize_local_writes, native_research_allowed=options.authorize_native_research,
                  force=options.force_feed_check)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
