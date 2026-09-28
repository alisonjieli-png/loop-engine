"""Counts of a release by component family and form, against the library composition targets.

The families and target shares are builder e's library_composition_targets/v1 (executable code 35 percent,
connectors and extensions 20, skills at most 20, agents and commands 10, instruction files and rules at most
8, data and contracts 7). A served item's family comes from its component form when the admission recorded
one, otherwise from its harness kind. Reading a bundle is read-only.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

COMPOSITION_RECORD = "generated_admission_composition/v1"


def _targets(policy: dict, root: Path) -> dict:
    composition = policy["composition"]
    path = root / composition["targets_file"]
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        return {row["family"]: (row["share"], row["bound"]) for row in value["families"]}, str(path)
    return {family: tuple(pair) for family, pair in composition["targets"].items()}, "policy copy"


def family_of(policy: dict, form: "str | None", harness_kind: "str | None") -> str:
    composition = policy["composition"]
    return (composition["family_by_form"].get(form or "") or composition["family_by_harness_kind"].get(
        harness_kind or "") or "other")


def bundle_counts(bundle: Path, policy: dict) -> Counter:
    """(family, form or harness kind) to served items of a release bundle."""
    counts = Counter()
    with open(Path(bundle) / "items.jsonl", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            attributes = row.get("attributes") or {}
            kind = attributes.get("harness_kind") or (row.get("reference") or {}).get("kind")
            form = attributes.get("component_form")
            counts[(family_of(policy, form, kind), form or kind)] += 1
    return counts


def admitted_counts(folder: Path, policy: dict) -> Counter:
    """(family, form) to approved rows of an admission folder."""
    counts = Counter()
    items = json.loads((Path(folder) / "items.json").read_text(encoding="utf-8"))["items"]
    approved = {row["identity"] for row in json.loads((Path(folder) / "reviews.json").read_text(encoding="utf-8"))
                ["rows"] if row["outcome"] == "approved"}
    for item in items:
        if item["reference"]["identity"] in approved:
            form = item["provenance"].get("component_form")
            counts[(family_of(policy, form, item["attributes"].get("harness_kind")), form)] += 1
    return counts


def report(policy: dict, root: Path, *, served: Counter, admitted: Counter) -> dict:
    targets, source = _targets(policy, root)
    total_served, total_admitted = sum(served.values()), sum(admitted.values())
    rows = {}
    for family in sorted(set(targets) | {family for family, _form in served} | {family for family, _form in admitted}):
        now = sum(count for (name, _form), count in served.items() if name == family)
        added = sum(count for (name, _form), count in admitted.items() if name == family)
        share, bound = targets.get(family, (None, None))
        after = (now + added) / (total_served + total_admitted) if total_served + total_admitted else 0.0
        rows[family] = {"served": now, "admitted": added,
                        "share_served": round(now / total_served, 4) if total_served else 0.0,
                        "share_after": round(after, 4), "target_share": share, "bound": bound,
                        "cap_exceeded_after": bound == "cap" and share is not None and after > share}
    return {"record_type": COMPOSITION_RECORD, "targets_from": source, "served": total_served,
            "admitted": total_admitted, "families": rows,
            "admitted_by_form": {f"{family}/{form}": count for (family, form), count in sorted(admitted.items())}}
