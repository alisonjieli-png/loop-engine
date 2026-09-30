"""Read the authorized RapidAPI Reddit source into Baltor's existing research queue.

One run makes at most one request. The private managed source record holds the
reservation and provider quota. Interrupted requests remain pending until an
operator reconciles them; this command never retries them automatically.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "src", ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from knowledge_radar.community_intake import read_registry
from knowledge_radar.community import SEED_COMMUNITIES
from knowledge_radar.community_store import CommunityStore
from knowledge_radar.community_watch import ingest
from knowledge_radar.community_work import open_queue, work_once
from knowledge_radar.rapidapi_reddit import HOST, RapidApiRedditReader, RedditRequest
from loop_engine.loop.service_loop_envelope import ServiceLoopSpec, run_service_operation

SOURCE_ID = "rapidapi_reddit34"
STATE_ID = "community.source." + SOURCE_ID
COMMUNITIES = SEED_COMMUNITIES


def read_once(root, *, subreddit=None, sort="new", authorized=False, reader=None, now=None):
    if not authorized:
        return {"record_type": "reddit_research_plan/v1", "effects_performed": False,
                "host": HOST, "communities": list(COMMUNITIES), "requests": 1,
                "stores": "source metadata, quota, unverified leads and component work orders"}
    os.umask(0o077)
    store = CommunityStore(root, writes_allowed=True)
    store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = os.open(store.root / "scan.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    scheduler = None
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"record_type": "reddit_research_run/v1", "status": "already_running"}
        epoch = time.time() if now is None else now
        moment = datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace("+00:00", "Z")
        previous = store.get(STATE_ID)
        held = previous["document"]["data"] if previous else {}
        if held.get("request_pending"):
            return {"record_type": "reddit_research_run/v1", "status": "unknown_request_requires_reconciliation"}
        if epoch < held.get("next_read_at_unix", 0):
            return {"record_type": "reddit_research_run/v1", "status": "not_due",
                    "next_read_at_unix": held["next_read_at_unix"]}
        quota = held.get("quota", {})
        reset = quota.get("reset_at_unix")
        if quota.get("requests_remaining") == 0 and (reset is None or epoch < reset):
            return {"record_type": "reddit_research_run/v1", "status": "provider_quota_exhausted"}
        selected = subreddit or COMMUNITIES[(held.get("rotation", -1) + 1) % len(COMMUNITIES)]
        request = RedditRequest(selected, sort=sort)
        registry = read_registry()
        pending = {**held, "request_pending": True, "last_attempted_at": moment,
                   "requested_subreddit": selected, "requested_sort": sort}
        store.put(STATE_ID, "source", SOURCE_ID, "recorded", pending, expected=previous)
        scheduler, series = open_queue(store)
        source_reader = reader or RapidApiRedditReader()
        def operation(active):
            observation = source_reader.read(request, registry)
            result = {"record_type": "reddit_research_run/v1", "source": SOURCE_ID,
                      "subreddit": selected, "observed_at": moment, **observation.report()}
            result["source_observation_record_type"] = result.pop("record_type")
            result["record_type"] = "reddit_research_run/v1"
            result["status"] = "failed" if observation.reason else "complete"
            if not observation.reason:
                result["intake"] = ingest(store, scheduler, series, observation.leads, moment, active.loop_id)
                work = work_once(store, scheduler, series, moment, maximum=max(1, len(observation.leads)))
                result["work_orders_compiled"] = len(work)
                result["work_order_ids"] = work
            remaining = observation.quota.get("requests_remaining")
            reset_at = observation.quota.get("reset_at_unix")
            # Spread the observed remaining allowance over its actual reset window.
            interval = 86400
            if isinstance(remaining, int) and reset_at and reset_at > epoch:
                interval = max(interval, math.ceil((reset_at - epoch) / max(1, remaining)))
            final = {**pending, "request_pending": observation.reason == "source_outcome_unknown",
                     "quota": observation.quota, "next_read_at_unix": epoch + interval,
                     "rotation": COMMUNITIES.index(selected) if selected in COMMUNITIES else held.get("rotation", -1),
                     "last_result": result}
            current = store.get(STATE_ID)
            store.put(STATE_ID, "source", SOURCE_ID, "failed" if observation.reason else "recorded", final, expected=current)
            store.put("community.run.rapidapi." + store.run_id, "run", SOURCE_ID,
                      "failed" if observation.reason else "complete", result)
            return result
        return run_service_operation(store.runtime, ServiceLoopSpec("community_rapidapi_read", "practitioner.code_execution",
            "community_source_read/v1", "community_source_result/v1", ("reads_fs", "writes_fs", "reads_secret", "network"),
            "Read one authorized community window and queue source-linked research work.", "community_source_failed"), operation)
    finally:
        if scheduler is not None:
            scheduler.close()
        os.close(lock)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--subreddit")
    parser.add_argument("--sort", choices=("new", "hot", "rising"), default="new")
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    parser.add_argument("--authorize-keyring-read", action="store_true")
    args = parser.parse_args(argv)
    result = read_once(args.library, subreddit=args.subreddit, sort=args.sort,
        authorized=args.authorize_network_reads and args.authorize_local_writes and args.authorize_keyring_read)
    print(json.dumps(result, indent=2))
    return 1 if result.get("status") in ("failed", "unknown_request_requires_reconciliation") else 0


if __name__ == "__main__":
    raise SystemExit(main())
