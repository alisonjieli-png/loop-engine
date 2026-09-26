"""Run one shard of the tools test modules, as the checked-in manifest divides them.

Roadmap step S-6.200. Continuous integration used to run every tools test module in one step on each Python
version, about 450 to 520 seconds per job. The manifest tools/ci_test_shards.json divides the modules into
named shards so that each shard runs as its own job. This runner loads a shard's modules the way
`python -m unittest discover -s tools -p 'test_*.py'` loads them: the tools folder first on sys.path, each
module imported by its bare name, and the load_tests protocol honoured. Nothing about a test changes; only the
process that runs it does. tools/test_ci_test_shards.py checks that every module sits in exactly one shard.

Usage:
    PYTHONPATH=src:tools python tools/run_test_shard.py --shard a
    python tools/run_test_shard.py --list
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MANIFEST = TOOLS / "ci_test_shards.json"


def load_manifest(path: Path = MANIFEST) -> dict:
    """The manifest as a dict; its shards map shard name to a sorted list of module names."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("shards"), dict):
        raise SystemExit(f"{path} is not a version 1 shard manifest")
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


def shard_modules(name: str, manifest: dict) -> list:
    """The module names of one shard, in the order the manifest lists them."""
    try:
        return list(manifest["shards"][name])
    except KeyError:
        raise SystemExit(f"no shard named {name!r}; the manifest has {', '.join(sorted(manifest['shards']))}")


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
    parser.add_argument("--list", action="store_true", help="print each shard name and its module count")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--verbose", "-v", action="store_true")
    arguments = parser.parse_args(argv)
    manifest = load_manifest(arguments.manifest)
    if arguments.list:
        for name in manifest["shards"]:
            print(f"{name} {len(manifest['shards'][name])}")
        return 0
    if not arguments.shard:
        parser.error("--shard NAME or --list is required")
    modules = shard_modules(arguments.shard, manifest)
    print(f"shard {arguments.shard}: {len(modules)} modules", flush=True)
    suite = build_suite(modules)
    result = unittest.TextTestRunner(verbosity=2 if arguments.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
