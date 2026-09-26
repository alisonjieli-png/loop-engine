"""Combine reviewed catalogue folders into one folder, the full snapshot one catalogue release is built from.

A catalogue release is a full snapshot built from one reviewed catalogue folder
(``tools/build_catalogue_release_bundle.py``). Its items may come from reviews
by different reviewer sets: the starter panel of September 21, 2026 approved
the served starter items, and the review panel later approved Community items.
This command writes one new folder, outside this public repository, that holds
every row of a base folder and of each added folder:

- each row keeps its tier; a base row is Verified and names the base's reviewer
  group, so the release tools require every reviewer of that group, and only
  that group, to have judged it;
- each row keeps its own decisions, digests and approval reference, and the
  folder names every reviewer once;
- a withdrawn identity is left out of the snapshot and listed with its note, so
  the release that publishes the folder can withdraw it durably;
- an added folder's source revision can be relabelled to the public commit that
  holds the same cited bytes; the command refuses unless every cited file has
  identical bytes at both revisions;
- the attribute schema declares the tier, so a served item shows its tier and a
  search can filter on it;
- each row keeps the date of the review that covered it as ``catalogued_on``.

It approves nothing and changes no verdict.

    PYTHONPATH=src:tools python tools/combine_reviewed_catalogues.py \\
        --base examples/29_intelligence_service/starter-catalogue --base-group starter-panel-2026-09-21 \\
        --add /home/username/baltor-library/reviewed-2026-09-25/community-overnight-v2 \\
        --withdraw normalize_phone_numbers="REASON" --relabel-revision OLD=NEW \\
        --output /home/username/baltor-library/release-folders/NAME
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent
for entry in (str(REPOSITORY / "src"),):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from loop_engine.core.service_runtime.catalogue_attributes import TIER_ATTRIBUTE, declare  # noqa: E402

REVIEW_FILE, ITEMS_FILE, SCHEMA_FILE = "reviews.json", "items.json", "attribute-schema.json"
REVIEW_RECORD = "starter_catalogue_independent_review/v2"
ITEMS_RECORD = "starter_catalogue_candidate_items/v2"
JUDGED = ("approved", "rejected", "carry_refused")


class CombineError(ValueError):
    """A stable refusal code for folders that cannot be combined as declared."""


def refuse(code: str, message: str = "") -> None:
    raise CombineError(f"{code}: {message}" if message else code)


def _json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git_bytes(revision: str, path: str) -> bytes:
    finished = subprocess.run(["git", "-C", str(REPOSITORY), "show", f"{revision}:{path}"], capture_output=True,
                              check=False, timeout=60)
    if finished.returncode != 0:
        refuse("revision_unreadable", f"{path} at {revision[:12]} cannot be read")
    return finished.stdout


def _relabel(rows: list, old: str, new: str) -> dict:
    """Move every source reference from one revision to another that holds the same cited bytes."""
    checked = {}
    for row in rows:
        path, _separator, revision = row["reference"]["source_ref"].rpartition("@")
        if revision != old:
            continue
        if path not in checked:
            before, after = _git_bytes(old, path), _git_bytes(new, path)
            if before != after:
                refuse("relabel_changes_bytes", f"{path} differs between {old[:12]} and {new[:12]}")
            checked[path] = hashlib.sha256(after).hexdigest()
        row["reference"]["source_ref"] = f"{path}@{new}"
        provenance = row.get("provenance")
        if isinstance(provenance, dict) and provenance.get("source_revision") == old:
            provenance["source_revision"] = new
    return checked


def _copy_bodies(source: Path, rows: list, output: Path) -> None:
    for row in rows:
        paths = [row["body_path"]] + [entry["source"] for entry in row.get("package_files", [])]
        for relative in paths:
            origin, target = source / relative, output / relative
            if not origin.is_file() or origin.is_symlink():
                refuse("body_missing", f"{relative} is not a regular file in {source}")
            if target.exists():
                if target.read_bytes() != origin.read_bytes():
                    refuse("body_path_collision", f"{relative} names two different bodies")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)


def combine(options) -> dict:
    output = Path(options.output).resolve()
    if output == REPOSITORY or REPOSITORY in output.parents:
        refuse("folder_inside_repository", "library bodies never go into this public repository")
    if output.exists():
        refuse("output_exists", "the combined folder is written once, into a new folder")
    withdrawn = {}
    for value in options.withdraw:
        identity, separator, note = value.partition("=")
        if not separator or not identity or not note.strip():
            refuse("invalid_withdrawal", "a withdrawal is written IDENTITY=NOTE")
        withdrawn[identity] = note.strip()
    base = Path(options.base).resolve()
    base_items, base_review = _json(base / ITEMS_FILE), _json(base / REVIEW_FILE)
    if base_items.get("record_type") != ITEMS_RECORD or base_review.get("record_type") != REVIEW_RECORD:
        refuse("record_unsupported", "the base folder holds items v2 and reviews v2")
    missing = sorted(set(withdrawn) - {row["identity"] for row in base_review["rows"]})
    if missing:
        refuse("withdrawal_unknown", f"the base folder does not hold {missing}")
    group = [reviewer["reviewer_id"] for reviewer in base_review["reviewers"]]
    items = [row for row in base_items["items"] if row["reference"]["identity"] not in withdrawn]
    rows = []
    for row in base_review["rows"]:
        if row["identity"] in withdrawn:
            continue
        row = dict(row)
        if row["outcome"] in JUDGED:
            row["tier"] = "verified"
            row["reviewer_group"] = options.base_group
        row.setdefault("catalogued_on", str(base_review["recorded_at"])[:10])
        rows.append(row)
    reviewers = {reviewer["reviewer_id"]: reviewer for reviewer in base_review["reviewers"]}
    source_digests = dict(base_items["source_digests"])
    previous = list(base_items.get("previous_source_revisions", []))
    combined_from = [{"folder": str(base), "items_sha256": _sha(base / ITEMS_FILE),
                      "reviews_sha256": _sha(base / REVIEW_FILE), "rows": len(rows)}]
    output.mkdir(parents=True)
    _copy_bodies(base, items, output)
    relabels = {}
    for index, folder in enumerate(options.add):
        folder = Path(folder).resolve()
        added_items, added_review = _json(folder / ITEMS_FILE), _json(folder / REVIEW_FILE)
        if added_items.get("record_type") != ITEMS_RECORD or added_review.get("record_type") != REVIEW_RECORD:
            refuse("record_unsupported", f"{folder} holds items v2 and reviews v2")
        known = {row["identity"] for row in rows}
        clash = sorted(known & {row["identity"] for row in added_review["rows"]})
        if clash:
            refuse("identity_repeated", f"identities appear in two folders: {clash[:5]}")
        for reviewer in added_review["reviewers"]:
            earlier = reviewers.get(reviewer["reviewer_id"])
            if earlier is not None and earlier != reviewer:
                refuse("reviewer_conflict", f"{reviewer['reviewer_id']} is named twice with different details")
            reviewers[reviewer["reviewer_id"]] = reviewer
        added_rows = [dict(row, reference=dict(row["reference"]),
                           **({"provenance": dict(row["provenance"])} if "provenance" in row else {}))
                      for row in added_items["items"]]
        if options.relabel_revision:
            old, _separator, new = options.relabel_revision.partition("=")
            relabels.update(_relabel(added_rows, old, new))
        for key, value in added_items["source_digests"].items():
            if key in source_digests and source_digests[key] != value:
                refuse("source_digest_conflict", f"{key} is pinned to two digests")
            source_digests[key] = value
        previous.append(added_items["source_revision"])
        _copy_bodies(folder, added_items["items"], output)
        items.extend(added_rows)
        rows.extend(dict(row, catalogued_on=row.get("catalogued_on", str(added_review["recorded_at"])[:10]))
                    for row in added_review["rows"])
        combined_from.append({"folder": str(folder), "items_sha256": _sha(folder / ITEMS_FILE),
                              "reviews_sha256": _sha(folder / REVIEW_FILE), "rows": len(added_review["rows"])})
    counted = {outcome: sum(1 for row in rows if row["outcome"] == outcome)
               for outcome in ("approved", "rejected", "not_reviewed", "carry_refused")}
    review = dict(base_review)
    review.update({
        "catalogue_folder": str(output), "reviewers": list(reviewers.values()),
        "reviewer_groups": {options.base_group: group}, "rows": rows, "combined_from": combined_from,
        "withdrawn": [{"identity": identity, "note": note} for identity, note in sorted(withdrawn.items())],
        "decision_rule": ("A Verified row is approved only when every reviewer of its reviewer group approves it; a "
                          "Community row only when its named reviewer, from a family that did not produce it, "
                          "approves it and every automated check passes. One written objection withholds approval. "
                          "No reviewer of an item's producer family judged it."),
        "totals": {"items_in_catalogue": len(rows), "items_reviewed": len(rows) - counted["not_reviewed"],
                   "approved": counted["approved"],
                   "approved_as_reviewed": sum(1 for row in rows if row["outcome"] == "approved"
                                               and row["approval_state"] == "reviewed"),
                   "approved_by_carry": sum(1 for row in rows if row["outcome"] == "approved"
                                            and row["approval_state"] == "carried"),
                   "rejected": counted["rejected"], "carry_refused": counted["carry_refused"],
                   "not_reviewed": counted["not_reviewed"]}})
    items_record = dict(base_items)
    items_record.update({"items": items, "source_digests": source_digests,
                         "previous_source_revisions": previous, "publication": "not_published"})
    # The snapshot's schema declares every well-known served attribute (the tier, the harness kind and the step
    # functions), so a row written with them is served with them and a row written before them carries none.
    schema = declare(_json(base / SCHEMA_FILE))
    (output / ITEMS_FILE).write_text(json.dumps(items_record, indent=1, sort_keys=True) + "\n")
    (output / REVIEW_FILE).write_text(json.dumps(review, indent=1, sort_keys=True) + "\n")
    (output / SCHEMA_FILE).write_text(json.dumps(schema, indent=2) + "\n")
    summary = {"output": str(output), "rows": len(rows), "approved": counted["approved"],
               "verified_approved": sum(1 for row in rows if row["outcome"] == "approved"
                                        and row.get("tier", "verified") == "verified"),
               "community_approved": sum(1 for row in rows if row["outcome"] == "approved"
                                         and row.get("tier") == "community"),
               "withdrawn": sorted(withdrawn), "relabelled_sources": len(relabels)}
    (output / "combine-report.json").write_text(json.dumps({**summary, "relabelled": relabels}, indent=1,
                                                           sort_keys=True) + "\n")
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--base-group", required=True, help="The name of the base folder's reviewer group.")
    parser.add_argument("--add", action="append", default=[], required=True)
    parser.add_argument("--withdraw", action="append", default=[], help="IDENTITY=NOTE, left out of the snapshot.")
    parser.add_argument("--relabel-revision", default="", help="OLD=NEW for the added folders' cited sources.")
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args(argv)
    try:
        summary = combine(options)
    except CombineError as error:
        print(json.dumps({"refused": True, "message": str(error)}))
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
