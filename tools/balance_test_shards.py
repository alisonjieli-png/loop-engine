"""Divide the tools test modules into shards of about equal measured time, or place new modules.

Roadmap step S-6.200. The manifest tools/ci_test_shards.json is checked in, so a run is reproducible: the same
revision always runs the same modules in the same shard. This tool writes that manifest. It never runs a test.

Two ways to use it:

    # Rebalance every shard from a timing record (module name to {"seconds": ...}), longest module first
    python tools/balance_test_shards.py --timings artifacts/ci-speed-2026-09-26/module-times-2026-09-26.json \
        --shards 4 --write

    # Place any module that discovery finds but the manifest does not name, into the lightest shard
    python tools/balance_test_shards.py --add-missing --write

Without --write the tool prints the manifest it would write. tools/test_ci_test_shards.py fails when a module
is missing from the manifest or listed twice, and names this tool in its message.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_test_shard import MANIFEST, TOOLS, discovered_test_modules, load_manifest  # noqa: E402

#: Seconds assumed for a module that has no timing record yet, so that it still lands in the lightest shard.
UNMEASURED_SECONDS = 1.0


def balance(timings: dict, modules: list, shard_names: list) -> dict:
    """Longest-processing-time-first assignment: each module, heaviest first, goes to the lightest shard."""
    loads = {name: 0.0 for name in shard_names}
    shards = {name: [] for name in shard_names}
    weighted = sorted(modules, key=lambda module: (-float(timings.get(module, {}).get("seconds", UNMEASURED_SECONDS)), module))
    for module in weighted:
        lightest = min(shard_names, key=lambda name: (loads[name], name))
        shards[lightest].append(module)
        loads[lightest] += float(timings.get(module, {}).get("seconds", UNMEASURED_SECONDS))
    return {name: sorted(shards[name]) for name in shard_names}, {name: round(loads[name], 1) for name in shard_names}


def add_missing(manifest: dict, modules: list) -> dict:
    """Place every unlisted module into the shard with the lowest measured seconds; leave the rest alone."""
    shards = {name: list(members) for name, members in manifest["shards"].items()}
    seconds = dict(manifest.get("measured_seconds", {name: 0.0 for name in shards}))
    listed = {module for members in shards.values() for module in members}
    for module in sorted(set(modules) - listed):
        lightest = min(shards, key=lambda name: (seconds.get(name, 0.0), name))
        shards[lightest] = sorted(shards[lightest] + [module])
        seconds[lightest] = round(seconds.get(lightest, 0.0) + UNMEASURED_SECONDS, 1)
    return shards, seconds


def render(shards: dict, seconds: dict, basis: str, balanced_on: str) -> dict:
    return {
        "record_type": "tools_test_shard_manifest/v1",
        "version": 1,
        "discovery": {"start": "tools", "pattern": "test_*.py"},
        "balanced_on": balanced_on,
        "basis": basis,
        "measured_seconds": seconds,
        "shards": shards,
    }


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--timings", type=Path, help="JSON map of module name to a record with a seconds field")
    parser.add_argument("--shards", type=int, default=4, help="how many shards to balance into (default 4)")
    parser.add_argument("--add-missing", action="store_true", help="keep the shards and place unlisted modules")
    parser.add_argument("--basis", default="", help="one sentence on where the timings came from")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--write", action="store_true", help="write the manifest instead of printing it")
    arguments = parser.parse_args(argv)
    modules = discovered_test_modules(TOOLS)
    today = dt.date.today().isoformat()
    if arguments.add_missing:
        manifest = load_manifest(arguments.manifest)
        shards, seconds = add_missing(manifest, modules)
        result = render(shards, seconds, manifest.get("basis", ""), manifest.get("balanced_on", today))
    elif arguments.timings:
        timings = json.loads(arguments.timings.read_text(encoding="utf-8"))
        names = [chr(ord("a") + index) for index in range(arguments.shards)]
        shards, seconds = balance(timings, modules, names)
        result = render(shards, seconds, arguments.basis, today)
    else:
        parser.error("--timings FILE or --add-missing is required")
    text = json.dumps(result, indent=2) + "\n"
    if arguments.write:
        arguments.manifest.write_text(text, encoding="utf-8")
        print(f"wrote {arguments.manifest}: " + ", ".join(f"{name} {len(members)} modules {seconds[name]}s" for name, members in shards.items()))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
