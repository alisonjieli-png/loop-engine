"""Check the watched model listings once: an internal operator command meant to run every hour.

It reads the bindings of the registry's hourly question (the OpenRouter model
listing and the newest model repositories of major labs on Hugging Face),
compares each with its last successful snapshot, records four freshness times
per source, and marks for re-evaluation only the questions that read a
source in which a model appeared, disappeared or changed. It never reads a
model card, never rebuilds a brief and makes no model call.

    PYTHONPATH=src:tools python tools/watch_model_releases.py \\
      --library /home/username/baltor-library/radar --authorize-network-reads --authorize-local-writes

Without both authorizations it prints what it would read and stops.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT, ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog  # noqa: E402

from knowledge_radar.engines_network import RadarNetwork  # noqa: E402
from knowledge_radar.model_watch import WATCHED_QUESTION, now_utc, tick  # noqa: E402
from knowledge_radar.pipeline import CONTRACTS, REGISTRY, read_json  # noqa: E402
from knowledge_radar.records import read_contracts, read_registry  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the watched model listings once.")
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--maximum-requests", type=int, default=30)
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    options = parser.parse_args(argv)
    repository = options.repository.resolve()
    registry = read_registry(read_json(repository / REGISTRY))
    contracts = read_contracts(read_json(repository / CONTRACTS))
    question = registry.question(WATCHED_QUESTION)
    if not (options.authorize_network_reads and options.authorize_local_writes):
        print(json.dumps({"preview": True, "sources": [binding.to_dict() for binding in question.sources]}))
        return 0
    moment = now_utc()
    log_path = options.library / "model-watch" / moment[:10] / f"requests-{moment.replace(':', '')}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    network = RadarNetwork(RequestBudget(options.maximum_requests, maximum_pause_seconds=60, reserve=20),
                           RequestLog(log_path), contracts)
    record = tick(registry, contracts, repository, options.library, network, now=moment)
    print(json.dumps({key: record[key] for key in ("status", "at", "invalidated") if key in record}
                     | {"sources": [{name: row[name] for name in ("source", "outcome", "observations", "added", "removed",
                                                                 "changed", "baseline")} for row in record.get("sources", [])]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
