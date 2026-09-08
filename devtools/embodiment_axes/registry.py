"""Discover every embodiment, check it, run it, and write the catalogue.

The folder is the interface. Anything matching `<family>/<NN-name>/manifest.json`
with an `embodiment.py` beside it is an embodiment, and nothing has to be
registered anywhere for it to be found. Add a folder and it appears; delete a
folder and it disappears. That is deliberate: a central list is the thing that
goes stale first, and a stale list is how an option quietly stops existing.

Subcommands:

  list      every embodiment, grouped by family
  check     manifests are complete, modules import, self-checks pass
  run       run one or more families through their own harness
  catalog   regenerate CATALOG.md and each embodiment's README.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_MANIFEST_FIELDS = (
    "id", "family", "name", "status", "one_line", "how_it_works",
    "pros", "cons", "pick_this_when", "avoid_when",
)
#: A folder that says nothing about when not to use it is not a real option;
#: it is an advertisement. So both sides are required, and both must be
#: non-empty.
BALANCED_FIELDS = ("pros", "cons", "pick_this_when", "avoid_when")

STATUSES = ("measured", "implemented", "specified", "quarantined")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def families() -> list:
    found = []
    for descriptor in sorted(ROOT.glob("*/family.json")):
        body = json.loads(descriptor.read_text())
        body["path"] = descriptor.parent
        body["harness_path"] = descriptor.parent / body.get("harness",
                                                            "harness.py")
        found.append(body)
    return found


def discover(family_filter=None, load_modules: bool = True) -> list:
    """Every embodiment on disk, in family and folder order."""
    found = []
    for manifest_path in sorted(ROOT.glob("*/*/manifest.json")):
        folder = manifest_path.parent
        family = folder.parent.name
        if family_filter and family not in family_filter:
            continue
        manifest = json.loads(manifest_path.read_text())
        entry = {"id": f"{family}/{folder.name}", "family": family,
                 "folder": folder, "manifest": manifest, "module": None,
                 "error": ""}
        if load_modules:
            try:
                entry["module"] = _load(folder / "embodiment.py",
                                        f"emb_{family}_{folder.name}".replace(
                                            "-", "_"))
            except Exception:
                entry["error"] = traceback.format_exc(limit=3)
        found.append(entry)
    return found


# --- check ---------------------------------------------------------------

def check(family_filter=None) -> int:
    problems = []
    known = {body["family"] for body in families()}
    entries = discover(family_filter)
    for entry in entries:
        where = entry["id"]
        if entry["error"]:
            problems.append(f"{where}: embodiment.py did not import\n"
                            f"{entry['error']}")
            continue
        manifest = entry["manifest"]
        for field in REQUIRED_MANIFEST_FIELDS:
            if field not in manifest:
                problems.append(f"{where}: manifest is missing {field!r}")
        for field in BALANCED_FIELDS:
            value = manifest.get(field) or []
            if not isinstance(value, list) or not value:
                problems.append(
                    f"{where}: {field!r} must list at least one entry; an "
                    f"option with no stated cost is not an option")
        if manifest.get("id") != where:
            problems.append(f"{where}: manifest id says {manifest.get('id')!r}")
        if manifest.get("family") not in known:
            problems.append(f"{where}: family {manifest.get('family')!r} has "
                            f"no family.json")
        if manifest.get("status") not in STATUSES:
            problems.append(f"{where}: status {manifest.get('status')!r} is "
                            f"not one of {STATUSES}")
        if not hasattr(entry["module"], "ARM"):
            problems.append(f"{where}: embodiment.py defines no ARM")
        elif entry["module"].ARM.get("name") != manifest.get("name"):
            problems.append(
                f"{where}: ARM name {entry['module'].ARM.get('name')!r} does "
                f"not match manifest name {manifest.get('name')!r}")
        check_fn = getattr(entry["module"], "self_check", None)
        if check_fn is not None:
            try:
                check_fn()
            except Exception as exc:
                problems.append(f"{where}: self_check failed: "
                                f"{type(exc).__name__}: {exc}")
    for body in families():
        if not body["harness_path"].exists():
            problems.append(f"{body['family']}: no harness at "
                            f"{body['harness_path'].name}")
    print(f"\n{len(entries)} embodiments in "
          f"{len({e['family'] for e in entries})} families")
    for problem in problems:
        print(f"  PROBLEM {problem}")
    print("check: ok" if not problems else f"check: {len(problems)} problems")
    return 1 if problems else 0


# --- run -----------------------------------------------------------------

def run(family_filter=None, spec=None, out=None) -> int:
    spec = spec or {}
    all_rows = []
    for body in families():
        if family_filter and body["family"] not in family_filter:
            continue
        entries = [entry for entry in discover([body["family"]])
                   if not entry["error"]]
        harness = _load(body["harness_path"],
                        f"harness_{body['family']}".replace("-", "_"))
        print(f"\n== {body['family']}: {body['question']}")
        print(f"   varies: {body['varies']}")
        rows = harness.run_family(entries, spec.get(body["family"], {}))
        for line in harness.summarise(rows):
            print(line)
        all_rows.extend(rows)
    if out:
        record = {"record_type": "embodiment_catalog_run/v1",
                  "families": [body["family"] for body in families()
                               if not family_filter
                               or body["family"] in family_filter],
                  "spec": spec, "rows": all_rows}
        Path(out).write_text(json.dumps(record, indent=1) + "\n")
        print(f"\nwrote {out}: {len(all_rows)} rows")
    return 0


# --- catalogue -----------------------------------------------------------

def _bullets(items) -> str:
    return "\n".join(f"- {item}" for item in items or [])


def _readme(entry) -> str:
    manifest = entry["manifest"]
    return "\n".join([
        f"# {manifest['name']}",
        "",
        manifest["one_line"],
        "",
        f"Family: `{manifest['family']}`  |  Status: {manifest['status']}",
        "",
        "## How it works",
        "",
        _bullets(manifest.get("how_it_works")),
        "",
        "## What it gives you",
        "",
        _bullets(manifest.get("pros")),
        "",
        "## What it costs you",
        "",
        _bullets(manifest.get("cons")),
        "",
        "## Pick this when",
        "",
        _bullets(manifest.get("pick_this_when")),
        "",
        "## Avoid it when",
        "",
        _bullets(manifest.get("avoid_when")),
        "",
        "## Run it",
        "",
        "```bash",
        f"python3 {manifest['id']}/embodiment.py        # its own self-check",
        f"python3 registry.py run --family {manifest['family']}",
        "```",
        "",
        "Generated from `manifest.json` by `registry.py catalog`. Edit the",
        "manifest, not this file.",
        "",
    ])


def catalog() -> int:
    entries = discover(load_modules=False)
    for entry in entries:
        (entry["folder"] / "README.md").write_text(_readme(entry))

    lines = [
        "# Catalogue of embodiments",
        "",
        "Every folder here is one way of building this system. They are not",
        "drafts of each other and none is deprecated. Each one is a design",
        "someone could reasonably choose, with what it gives you and what it",
        "costs you stated next to each other, and measured where a",
        "measurement is possible.",
        "",
        "The organising claim is that these are independent axes. A design is",
        "one choice from each family, and the choices compose: bounded state,",
        "in a container, verified by recomputation, remembering through a",
        "governed journal, driven by an adaptive batch. Nothing here forces a",
        "bundle.",
        "",
        "```bash",
        "python3 registry.py list                  # everything, by family",
        "python3 registry.py check                 # manifests, imports, self-checks",
        "python3 registry.py run                   # every family through its harness",
        "python3 registry.py run --family memory   # one family",
        "python3 registry.py catalog               # regenerate this file",
        "```",
        "",
        f"{len(entries)} embodiments across {len(families())} families.",
        "",
    ]
    for body in families():
        mine = [entry for entry in entries if entry["family"] == body["family"]]
        lines += [
            f"## {body['family']}",
            "",
            f"**{body['question']}**",
            "",
            f"Varies: {body['varies']}.  ",
            f"Held constant: {body['held_constant']}.  ",
            f"Decides: {body['decides']}.  ",
            f"Read first: {body['read_first']}.",
            "",
            "| # | Embodiment | In one line | Status |",
            "|---|---|---|---|",
        ]
        for entry in mine:
            manifest = entry["manifest"]
            number = entry["folder"].name.split("-")[0]
            lines.append(
                f"| {number} | [`{manifest['name']}`]({entry['id']}/README.md) "
                f"| {manifest['one_line']} | {manifest['status']} |")
        lines.append("")
        for entry in mine:
            manifest = entry["manifest"]
            lines += [
                f"### {manifest['name']}",
                "",
                f"*{manifest['one_line']}*",
                "",
                "**Gives you**",
                "",
                _bullets(manifest.get("pros")),
                "",
                "**Costs you**",
                "",
                _bullets(manifest.get("cons")),
                "",
                f"**Pick it when** {'; '.join(manifest.get('pick_this_when') or [])}",
                "",
                f"**Avoid it when** {'; '.join(manifest.get('avoid_when') or [])}",
                "",
            ]
    lines += [
        "## Adding one",
        "",
        "1. Make `<family>/<NN-name>/`, choosing the family whose question",
        "   your idea answers differently. A new question is a new family,",
        "   which needs its own `family.json` and `harness.py`.",
        "2. Write `embodiment.py` with an `ARM` dict and a `self_check()`.",
        "3. Write `manifest.json`. Both `cons` and `avoid_when` are required",
        "   and must be non-empty. An option with no stated cost does not",
        "   help anyone choose.",
        "4. Run `python3 registry.py check`, then `catalog`.",
        "",
        "Nothing has to be added to a list. Discovery is by folder, so the",
        "catalogue cannot go stale against what is on disk.",
        "",
        "Generated by `registry.py catalog`. Edit the manifests, not this file.",
        "",
    ]
    Path(ROOT / "CATALOG.md").write_text("\n".join(lines))
    print(f"wrote CATALOG.md and {len(entries)} README.md files")
    return 0


def listing(family_filter=None) -> int:
    entries = discover(family_filter, load_modules=False)
    current = ""
    for entry in entries:
        if entry["family"] != current:
            current = entry["family"]
            body = next(item for item in families()
                        if item["family"] == current)
            print(f"\n{current}  ({body['question']})")
        manifest = entry["manifest"]
        print(f"  {entry['folder'].name:26s} {manifest['name']:22s} "
              f"{manifest['status']:12s} {manifest['one_line']}")
    print(f"\n{len(entries)} embodiments")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",
                        choices=("list", "check", "run", "catalog"))
    parser.add_argument("--family", action="append",
                        help="limit to one family; repeatable")
    parser.add_argument("--horizons",
                        help="comma separated horizons for families that "
                             "sweep them")
    parser.add_argument("--out", help="write a run record to this path")
    args = parser.parse_args(argv)

    spec = {}
    if args.horizons:
        horizons = [int(item) for item in args.horizons.split(",")
                    if item.strip()]
        spec = {body["family"]: {"horizons": horizons}
                for body in families()}

    if args.command == "list":
        return listing(args.family)
    if args.command == "check":
        return check(args.family)
    if args.command == "run":
        return run(args.family, spec, args.out)
    return catalog()


if __name__ == "__main__":
    raise SystemExit(main())
