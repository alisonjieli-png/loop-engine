"""Run one shard of the tools test modules, with the modules placed in shards at run time from recorded timings.

Roadmap step S-6.200. Continuous integration used to run every tools test module in one step on each Python
version, about 450 to 520 seconds per job, so the modules are divided into named shards and each shard runs as its own
job. Until September 27, 2026 the manifest tools/ci_test_shards.json listed every module under its shard, with the
estimated seconds of each shard. Every new test module had to be added to a list and to a total, and two lines of work
that each added a module conflicted in that file whenever they were merged. The manifest now holds only the shard
names and where the timings are recorded; the placement is computed here, the same way on every machine:

- every module that `python -m unittest discover -s tools -p 'test_*.py'` would load is placed, and nothing else;
- a module weighs its recorded seconds, the newest timing record that names it winning, and a module no record names
  weighs the median of the recorded modules;
- longest processing time first: the heaviest module goes to the shard with the least estimated time, ties broken by
  module name and then by shard name.

Adding a test module therefore changes no committed file. This runner loads a shard's modules the way discovery loads
them: the tools folder first on sys.path, each module imported by its bare name, the load_tests protocol honoured.
tools/test_ci_test_shards.py holds the manifest, the placement and the workflow to these rules.

Usage:
    PYTHONPATH=src:tools python tools/run_test_shard.py --shard a
    python tools/run_test_shard.py --list        # each shard, its module count and estimated seconds
    python tools/run_test_shard.py --plan        # the whole placement as JSON
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MANIFEST = TOOLS / "ci_test_shards.json"
MANIFEST_RECORD_TYPE = "tools_test_shard_manifest/v2"


def load_manifest(path: Path = MANIFEST) -> dict:
    """The version 2 manifest: shard names, discovery and the timing records; module lists are refused."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("record_type") != MANIFEST_RECORD_TYPE or data.get("version") != 2:
        raise SystemExit(f"{path} is not a {MANIFEST_RECORD_TYPE} manifest")
    shards = data.get("shards")
    if not isinstance(shards, list) or not shards or len(set(shards)) != len(shards) \
            or not all(isinstance(name, str) and name for name in shards):
        raise SystemExit(f"{path} names its shards as a list of distinct names")
    return data


def discovered_test_modules(start: Path = TOOLS, pattern: str = "test_*.py") -> list:
    """The module names `unittest discover -s tools -p 'test_*.py'` would load, in sorted order.

    Discovery takes the matching files of the start folder and descends only into packages (folders with an
    __init__.py), naming their modules with dots. A folder without __init__.py is not searched.
    """
    found = []

    def walk(folder: Path, prefix: str) -> None:
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.match(pattern) and path.suffix == ".py":
                found.append(prefix + path.stem)
            elif path.is_dir() and (path / "__init__.py").is_file():
                walk(path, prefix + path.name + ".")

    walk(start, "")
    return sorted(found)


def recorded_seconds(manifest: dict, root: Path = ROOT) -> dict:
    """{module: seconds} from every timing record the manifest's pattern names, a later record overriding an earlier."""
    seconds = {}
    for path in sorted(root.glob(manifest["timings"])):
        for module, row in json.loads(path.read_text(encoding="utf-8")).items():
            value = row.get("seconds") if isinstance(row, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                seconds[module] = float(value)
    return seconds


def plan(modules, shards, seconds) -> tuple:
    """({shard: sorted modules}, {shard: estimated seconds}, {module: weight}) by longest processing time first."""
    known = sorted(seconds.values())
    unmeasured = statistics.median(known) if known else 1.0
    weights = {module: seconds.get(module, unmeasured) for module in modules}
    loads = {name: 0.0 for name in shards}
    placed = {name: [] for name in shards}
    for module in sorted(modules, key=lambda name: (-weights[name], name)):
        lightest = min(shards, key=lambda name: (loads[name], shards.index(name)))
        placed[lightest].append(module)
        loads[lightest] += weights[module]
    return ({name: sorted(placed[name]) for name in shards}, {name: round(loads[name], 1) for name in shards}, weights)


def current_plan(manifest: dict | None = None, root: Path = ROOT) -> tuple:
    """The placement of this checkout's discovered modules under its manifest and timing records."""
    manifest = manifest or load_manifest(root / "tools" / "ci_test_shards.json")
    return plan(discovered_test_modules(root / "tools"), manifest["shards"], recorded_seconds(manifest, root))


def shard_modules(name: str, manifest: dict) -> list:
    """The module names of one shard, computed at run time."""
    placed, _estimates, _weights = current_plan(manifest)
    try:
        return placed[name]
    except KeyError:
        raise SystemExit(f"no shard named {name!r}; the manifest has {', '.join(manifest['shards'])}")


def build_suite(modules: list, loader: unittest.TestLoader | None = None) -> unittest.TestSuite:
    """One suite holding every test of the named modules, imported from the tools folder."""
    loader = loader or unittest.defaultTestLoader
    # `python -m unittest discover` runs with the working directory (the repository root) first on sys.path
    # and inserts the tools folder in front of it. Running this file as a script puts only the tools folder
    # there, so a module that imports `tools.something` would fail. Both are placed, in that order.
    for entry in (str(ROOT), str(TOOLS)):
        if entry in sys.path:
            sys.path.remove(entry)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(TOOLS))
    suite = unittest.TestSuite()
    for module in modules:
        suite.addTests(loader.loadTestsFromName(module))
    return suite


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--shard", help="the shard to run, by manifest name")
    parser.add_argument("--list", action="store_true", help="print each shard, its module count and estimated seconds")
    parser.add_argument("--plan", action="store_true", help="print the whole placement as JSON")
    parser.add_argument("--module", help="run one discovered module alone, as a shard would (for timing it)")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--verbose", "-v", action="store_true")
    arguments = parser.parse_args(argv)
    manifest = load_manifest(arguments.manifest)
    placed, estimates, weights = current_plan(manifest)
    if arguments.list:
        for name in manifest["shards"]:
            print(f"{name} {len(placed[name])} {estimates[name]}")
        return 0
    if arguments.plan:
        print(json.dumps({"shards": placed, "estimated_seconds": estimates, "weights": weights}, indent=1))
        return 0
    if arguments.module:
        if arguments.module not in discovered_test_modules(TOOLS):
            parser.error(f"{arguments.module} is not a module that discovery loads")
        result = unittest.TextTestRunner(verbosity=1).run(build_suite([arguments.module]))
        return 0 if result.wasSuccessful() else 1
    if not arguments.shard:
        parser.error("--shard NAME, --list, --plan or --module is required")
    modules = shard_modules(arguments.shard, manifest)
    print(f"shard {arguments.shard}: {len(modules)} modules, about {estimates[arguments.shard]} seconds recorded",
          flush=True)
    suite = build_suite(modules)
    result = unittest.TextTestRunner(verbosity=2 if arguments.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
