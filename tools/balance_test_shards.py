"""Show the placement of the tools test modules in shards, and record new module timings for it.

Roadmap step S-6.200. Since September 27, 2026 the placement is computed at run time by tools/run_test_shard.py from
the timing records that tools/ci_test_shards.json names; nothing lists modules any more, so there is nothing to
rebalance by hand and no module list to merge. This tool shows the placement and records timings:

    # The placement this checkout computes, with the estimated seconds of each shard
    python tools/balance_test_shards.py

    # The placement a timing record would give, before it is committed
    python tools/balance_test_shards.py --timings artifacts/ci-speed-2026-09-27/module-times-2026-09-27.json

    # Time the modules no record names, each alone in its own process, and write a new dated timing record
    python tools/balance_test_shards.py --measure unmeasured \
        --output artifacts/ci-speed-2026-09-27/module-times-2026-09-27.json

A new record is picked up because its name matches the manifest's pattern; a module it names takes its new time. The
old --add-missing mode is kept and does nothing, because a new module is placed when the shards run.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_test_shard import (  # noqa: E402
    MANIFEST, ROOT, TOOLS, discovered_test_modules, load_manifest, plan, recorded_seconds,
)


def measure(modules: list, python: str = sys.executable) -> dict:
    """{module: {"seconds", "result"}} for each module run alone in its own process, the way discovery loads it."""
    rows = {}
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), str(TOOLS)])}
    for module in modules:
        started = time.monotonic()
        completed = subprocess.run([python, str(TOOLS / "run_test_shard.py"), "--module", module], cwd=ROOT,
                                   env=environment, capture_output=True, text=True, check=False)
        rows[module] = {"seconds": round(time.monotonic() - started, 1),
                        "result": "OK" if completed.returncode == 0 else "FAILED"}
        print(f"{module:60} {rows[module]['seconds']:7.1f}s {rows[module]['result']}", flush=True)
    return rows


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--timings", type=Path, help="show the placement with this timing record added last")
    parser.add_argument("--measure", choices=("unmeasured", "all"), help="time modules alone and write a record")
    parser.add_argument("--output", type=Path, help="where --measure writes its timing record")
    parser.add_argument("--add-missing", action="store_true", help="kept for old instructions; does nothing")
    parser.add_argument("--write", action="store_true", help="kept for old instructions; does nothing")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    arguments = parser.parse_args(argv)
    manifest = load_manifest(arguments.manifest)
    modules = discovered_test_modules(TOOLS)
    seconds = recorded_seconds(manifest)
    if arguments.add_missing or arguments.write:
        print("nothing to write: tools/run_test_shard.py places every discovered module when the shards run")
    if arguments.measure:
        if not arguments.output:
            parser.error("--measure needs --output, a new dated record under artifacts/ci-speed-*/")
        if arguments.output.exists():
            parser.error(f"{arguments.output} exists; a timing record is written once under a new name")
        chosen = [module for module in modules if arguments.measure == "all" or module not in seconds]
        rows = measure(chosen)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {arguments.output}: {len(rows)} modules")
        seconds.update({module: row["seconds"] for module, row in rows.items()})
    if arguments.timings:
        extra = json.loads(arguments.timings.read_text(encoding="utf-8"))
        seconds.update({module: float(row["seconds"]) for module, row in extra.items() if "seconds" in row})
    placed, estimates, _weights = plan(modules, manifest["shards"], seconds)
    for name in manifest["shards"]:
        print(f"{name}: {len(placed[name])} modules, {estimates[name]} seconds estimated")
    unmeasured = [module for module in modules if module not in seconds]
    print(f"{len(modules)} modules, {len(unmeasured)} without a recorded time")
    return 0


if __name__ == "__main__":
    sys.exit(main())
