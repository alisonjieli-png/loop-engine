"""Write or check the digests that freeze the design before any model call.

    python runner/freeze.py            # write design-freeze.json
    python runner/freeze.py --check    # exit 1 when a frozen file changed

The freeze covers the design record, the population and its generator, the
scorer and its tests, the runner and the proxy, and the exact bytes of every
catalogue item the material arms use. Only the Python standard library is
used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
REPOSITORY = STUDY.parent.parent
CATALOGUE = REPOSITORY / "examples" / "29_intelligence_service" / "starter-catalogue"
FREEZE = STUDY / "design-freeze.json"
FROZEN_FILES = (
    "design.json",
    "population/generate_population.py",
    "scorer/score_step.py",
    "scorer/test_score_step.py",
    "runner/meter.py",
    "runner/test_meter.py",
    "runner/run_trials.py",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current():
    files = {name: digest(STUDY / name) for name in FROZEN_FILES}
    for path in sorted((STUDY / "population").rglob("*")):
        if path.is_file() and path.suffix in (".csv", ".json", ".txt"):
            files[path.relative_to(STUDY).as_posix()] = digest(path)
    design = json.loads((STUDY / "design.json").read_text(encoding="utf-8"))
    items = {}
    for identities in design["material"].values():
        for identity in identities:
            path = CATALOGUE / "bodies" / f"{identity}.md"
            items[identity] = {"path": path.relative_to(REPOSITORY).as_posix(),
                               "sha256": digest(path)}
    return {"record_type": "data_cleanup_design_freeze/v1", "files": files, "items": items}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    now = current()
    if args.check:
        frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
        changed = sorted(name for name in set(frozen["files"]) | set(now["files"])
                         if frozen["files"].get(name) != now["files"].get(name))
        changed += sorted(name for name in set(frozen["items"]) | set(now["items"])
                          if frozen["items"].get(name) != now["items"].get(name))
        for name in changed:
            print(f"changed since the freeze: {name}")
        return 1 if changed else 0
    FREEZE.write_text(json.dumps(now, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {FREEZE.relative_to(STUDY)}: {len(now['files'])} files, {len(now['items'])} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
