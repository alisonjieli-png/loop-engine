"""The original transport comparison, kept working after the folder split.

This entry point predates the catalogue. Its flags are unchanged and its
output record still says `embodiment_comparison/v1`, so anything that read the
old records keeps reading. What changed underneath is that the arms now live
in `context-transport/<NN-name>/` and are discovered rather than imported by
name, so adding an arm adds it here too.

`registry.py run --family context-transport` is the same measurement with the
catalogue's own output. Use whichever you already have in your fingers.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "shared"))

import registry
from port import DEFAULT_CONTEXT_LIMIT

FAMILY = "context-transport"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", default="4,16,64",
                        help="comma separated horizons to sweep")
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--backend", default="fixture",
                        choices=("fixture", "local", "cloud"))
    parser.add_argument("--model", default="glm-5.3-flash:cloud")
    parser.add_argument("--context-limit", type=int,
                        default=DEFAULT_CONTEXT_LIMIT)
    parser.add_argument("--max-steps", type=int, default=6000,
                        help="ceiling per arm; raise it so a ceiling is not "
                             "mistaken for an architectural wall")
    parser.add_argument("--out", default="comparison.json")
    parser.add_argument("--arm", action="append",
                        help="an arm name; repeatable. Names come from "
                             "`registry.py list`.")
    args = parser.parse_args(argv)

    entries = [entry for entry in registry.discover([FAMILY])
               if not entry["error"]]
    if args.arm:
        wanted = set(args.arm)
        known = {entry["manifest"]["name"] for entry in entries}
        unknown = wanted - known
        if unknown:
            parser.error(f"unknown arm(s) {sorted(unknown)}; "
                         f"have {sorted(known)}")
        entries = [entry for entry in entries
                   if entry["manifest"]["name"] in wanted]

    horizons = [int(item) for item in args.shards.split(",") if item.strip()]
    harness = registry._load(Path(__file__).resolve().parent / FAMILY
                             / "harness.py", "harness_context_transport")
    rows = harness.run_family(entries, {
        "horizons": horizons, "seed": args.seed, "backend": args.backend,
        "model": args.model, "context_limit": args.context_limit,
        "max_steps": args.max_steps})
    for line in harness.summarise(rows):
        print(line)

    record = {
        "record_type": "embodiment_comparison/v1",
        "backend": args.backend,
        "model": args.model if args.backend != "fixture" else "",
        "context_limit_bytes": args.context_limit,
        "seed": args.seed,
        "max_steps": args.max_steps,
        "horizons": horizons,
        "arms": [{"name": entry["manifest"]["name"],
                  "idea": entry["module"].ARM.get("idea", ""),
                  "carries": entry["module"].ARM.get("carries", "")}
                 for entry in entries],
        "rows": rows,
        "limitations": [
            "the fixture backend plays perfectly, so this measures transport "
            "and not whether a model reasons well with it",
            "one task shape, one seed per horizon unless swept",
            "bytes are counted, not provider tokens",
        ],
    }
    Path(args.out).write_text(json.dumps(record, indent=1) + "\n")
    print(f"\nwrote {args.out}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
