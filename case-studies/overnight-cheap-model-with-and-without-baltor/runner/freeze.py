"""Snapshot the material, then write or check the digests that freeze the design.

    python runner/freeze.py --snapshot-material   # copy the approved item bytes into material/
    python runner/freeze.py                       # write design-freeze.json
    python runner/freeze.py --check               # exit 1 when a frozen file changed without an amendment
    python runner/freeze.py --check --catalogue   # also say whether the catalogue still serves the same bytes

The material is a copy of the exact approved bytes, taken from the starter
catalogue with its approval row. The data cleanup study froze the digests of
the catalogue files themselves; on September 23, 2026 the catalogue re-anchored
every body (a carried approval that changes only the last line), and that
study's own `freeze.py --check` has failed since. Here the frozen bytes live in
the study folder, so the check keeps working when the catalogue moves on, and
`--catalogue` reports the difference without failing.

The freeze covers the design record, the population and its generator, the
item reference, the scorer, the runner, the proxy, the supervisor, the
analysis, every test and the material. Only the Python standard library is
used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
REPOSITORY = STUDY.parent.parent
CATALOGUE = REPOSITORY / "examples" / "29_intelligence_service" / "starter-catalogue"
FREEZE = STUDY / "design-freeze.json"
MATERIAL = STUDY / "material"
FROZEN_FILES = (
    "design.json",
    "population/generate_population.py",
    "population/item-reference.json",
    "scorer/score_step.py",
    "scorer/test_score_step.py",
    "runner/meter.py",
    "runner/test_meter.py",
    "runner/run_trials.py",
    "runner/test_runner.py",
    "runner/overnight.sh",
    "runner/item_reference.py",
    "runner/summarize.py",
    "runner/use_signals.py",
    "material/approvals.json",
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def design():
    return json.loads((STUDY / "design.json").read_text(encoding="utf-8"))


def identities():
    seen = []
    for items in design()["material"].values():
        for identity in items:
            if identity not in seen:
                seen.append(identity)
    return seen


def catalogue_rows():
    reviews = json.loads((CATALOGUE / "reviews.json").read_text(encoding="utf-8"))
    return reviews, {row["identity"]: row for row in reviews["rows"]}


def snapshot_material():
    reviews, rows = catalogue_rows()
    queries = json.loads((CATALOGUE / "search-queries.json").read_text(encoding="utf-8"))["queries"]
    revision = subprocess.run(["git", "-C", str(REPOSITORY), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    selection = design()["material_queries"]
    items = []
    MATERIAL.mkdir(exist_ok=True)
    for identity in identities():
        row = rows[identity]
        body = (CATALOGUE / row["body_path"]).read_bytes()
        if row["outcome"] != "approved" or digest(CATALOGUE / row["body_path"]) != row["body_digest"]:
            raise SystemExit(f"refused: {identity} is not an approved item with matching bytes")
        (MATERIAL / f"{identity}.md").write_bytes(body)
        fixtures = [query for query in queries if query["expected"] == identity]
        items.append({
            "identity": identity,
            "body_digest": row["body_digest"],
            "body_size_bytes": row["body_size_bytes"],
            "declared_license": row["declared_license"],
            "outcome": row["outcome"],
            "approval_state": row["approval_state"],
            "approval_ref": row["approval_ref"],
            "decisions": row["decisions"],
            "carry": {key: row["carry"][key] for key in ("reviewed_body_digest", "reviewed_revision",
                                                          "carried_revision", "decisions_unchanged",
                                                          "reviewed_again")}
            if row.get("carry") else None,
            "selected_by_queries": [query for family, texts in selection.items()
                                    for query in fixtures if query["query"] in texts],
        })
    record = {"record_type": "overnight_material_snapshot/v1",
              "catalogue_folder": CATALOGUE.relative_to(REPOSITORY).as_posix(),
              "catalogue_record_type": reviews["record_type"],
              "catalogue_decision_rule": reviews["decision_rule"],
              "repository_revision_at_snapshot": revision,
              "items": items}
    (MATERIAL / "approvals.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(f"copied {len(items)} approved items into material/ at revision {revision[:8]}")


def current():
    files = {name: digest(STUDY / name) for name in FROZEN_FILES}
    for identity in identities():
        files[f"material/{identity}.md"] = digest(MATERIAL / f"{identity}.md")
    for path in sorted((STUDY / "population").rglob("*")):
        if path.is_file() and path.suffix in (".csv", ".json", ".txt"):
            files[path.relative_to(STUDY).as_posix()] = digest(path)
    return {"record_type": "overnight_design_freeze/v1", "files": files}


def check_catalogue():
    _, rows = catalogue_rows()
    approvals = json.loads((MATERIAL / "approvals.json").read_text(encoding="utf-8"))
    for item in approvals["items"]:
        row = rows.get(item["identity"])
        if row is None:
            print(f"catalogue: {item['identity']} is no longer in the catalogue")
        elif row["outcome"] != "approved":
            print(f"catalogue: {item['identity']} is now {row['outcome']}")
        elif row["body_digest"] != item["body_digest"]:
            print(f"catalogue: {item['identity']} is approved at a newer digest "
                  f"{row['body_digest'][:12]}; the study keeps {item['body_digest'][:12]}")
        else:
            print(f"catalogue: {item['identity']} is unchanged")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--catalogue", action="store_true")
    parser.add_argument("--snapshot-material", action="store_true")
    args = parser.parse_args(argv)
    if args.snapshot_material:
        snapshot_material()
        return 0
    now = current()
    if args.check:
        frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
        amendments = STUDY / "amendments.json"
        amended = dict(frozen["files"])
        if amendments.is_file():
            for amendment in json.loads(amendments.read_text(encoding="utf-8"))["amendments"]:
                for name, change in amendment["files"].items():
                    if amended.get(name) != change["from"]:
                        print(f"amendment {amendment['id']} does not start from the recorded "
                              f"digest of {name}")
                        return 1
                    amended[name] = change["to"]
        changed = sorted(name for name in set(amended) | set(now["files"])
                         if amended.get(name) != now["files"].get(name))
        for name in changed:
            print(f"changed since the freeze: {name}")
        if args.catalogue:
            check_catalogue()
        return 1 if changed else 0
    FREEZE.write_text(json.dumps(now, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {FREEZE.relative_to(STUDY)}: {len(now['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
