"""Build one day's knowledge radar candidates: an internal local operator command.

The command reads the question registry, runs the planned questions' source
engines (local files always; bounded read-only network reads only with
--authorize-network-reads), writes dated briefs, data tables, decision helpers
and tools as a candidate catalogue in the existing native package format, and
vets every package along separate dimensions. It approves, stages, serves and
publishes nothing, and it makes no model call.

    PYTHONPATH=src:tools python tools/build_knowledge_radar.py \\
      --library /home/username/baltor-library/radar --as-of 2026-09-27 \\
      --collector-state /home/username/baltor-private/source-discovery-2026-09-26/state \\
      --authorize-network-reads --authorize-local-writes

Without --authorize-local-writes the command prints the plan and stops. A
second run of the same day with the same revision, registry and options
resumes the first one's unfinished stages; a finished day answers
already_complete. See tools/knowledge_radar/README.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT, ROOT / "tools"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from knowledge_radar import planner  # noqa: E402
from knowledge_radar.pipeline import REGISTRY, RadarRunError, RunRequest, read_json, run  # noqa: E402
from knowledge_radar.records import read_registry  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build one day's knowledge radar candidate catalogue.")
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--library", type=Path, required=True, help="The radar library folder, for example "
                        "/home/username/baltor-library/radar; the day folder and the shared state live under it.")
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--output", type=Path, help="The day folder; defaults to <library>/<as-of>.")
    parser.add_argument("--collector-state", type=Path, help="The source discovery collector's state folder (read only).")
    parser.add_argument("--only", action="append", default=[], help="Answer only this question; repeatable.")
    parser.add_argument("--maximum-requests", type=int, default=400)
    parser.add_argument("--demand", type=Path, help="A JSON object mapping question identities to demand weights.")
    parser.add_argument("--skip-link-checks", action="store_true")
    parser.add_argument("--skip-sandbox-tests", action="store_true")
    parser.add_argument("--stop-after", default="", help="Stop after this stage (used to prove a resume works).")
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--authorize-local-writes", action="store_true")
    options = parser.parse_args(argv)
    request = RunRequest(options.repository.resolve(), options.library, options.as_of, options.output,
                         options.collector_state, options.authorize_network_reads, options.authorize_local_writes,
                         options.maximum_requests, tuple(options.only), not options.skip_link_checks,
                         not options.skip_sandbox_tests, options.demand, options.stop_after)
    if not options.authorize_local_writes:
        registry = read_registry(read_json(request.repository / REGISTRY))
        preview = planner.plan(registry, {}, options.as_of, only=tuple(options.only) or None)
        print(json.dumps({"preview": True, "selected": [row["question_id"] for row in preview["selected"]],
                          "deferred": len(preview["deferred"]), "network_reads": options.authorize_network_reads}))
        return 0
    try:
        result = run(request)
    except RadarRunError as error:
        print(json.dumps({"status": "refused", "code": error.code, "detail": str(error)}))
        return 1
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
