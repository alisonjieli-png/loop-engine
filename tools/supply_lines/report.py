"""The supply of the library by family and form, and the projected composition at each milestone.

```text
Supply report (library_supply_report/v1)
├── library: the served release's packages per family and form (a release bundle's items.jsonl)
├── supply, from the import store
│   ├── imported (library.import): candidates not yet handed to review that the imported profile can read
│   └── generated (library.supply): the supply lines' candidates, held until a review profile reads them
├── approval: the share of exported packages the daily reviews approved (their counts.json records)
├── projection: slot after slot of the composition mix (supply-aware shares, no refill), each slot's
│   kept packages approved at that share, until the library passes each milestone or the supply ends
│   ├── scenario imported_only: today's review path
│   └── scenario with_generated: once a review profile reads the supply lines' packages
└── needs: per family and milestone, the approved packages the target mix asks for, the candidates
    that takes at the approval share, and the gap to the supply on hand
```

Nothing here approves or serves anything; the projection is arithmetic on
counts, stated with its assumptions.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from licensed_import.composition import CompositionTargets, largest_remainder, payload_form, slot_quotas
from licensed_import.review_export import exported_record_ids, reviewable

REPORT_RECORD_TYPE = "library_supply_report/v1"


def approval_share(daily_folder: Path) -> dict:
    """Approved over exported in every daily counts record, and the records read."""
    exported = approved = 0
    days = []
    for path in sorted(Path(daily_folder).glob("*/counts.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("exported") and record.get("approved") is not None:
            exported += int(record["exported"])
            approved += int(record["approved"])
            days.append(record.get("day"))
    return {"share": round(approved / exported, 4) if exported else None, "exported": exported,
            "approved": approved, "slots": days}


def store_supply(store, targets: CompositionTargets, exported: set) -> dict:
    """Candidates per family and form: imported and reviewable, and generated (held)."""
    from loop_engine.catalog.query import IntelligenceQuery
    from licensed_import.storage import NAMESPACE, SUPPLY_NAMESPACE
    result = {}
    for label, namespace in (("imported", NAMESPACE), ("generated", SUPPLY_NAMESPACE)):
        forms, lines, not_reviewable = Counter(), Counter(), Counter()
        for row in store.records.query(IntelligenceQuery(namespaces=(namespace,), lifecycle=("candidate",))):
            payload = row["payload"]
            if payload.get("record_id") in exported:
                continue
            if label == "imported":
                reason = reviewable(payload)
                if reason:
                    not_reviewable[reason] += 1
                    continue
            forms[payload_form(payload)] += 1
            if label == "generated":
                lines[payload.get("line", "")] += 1
        families = Counter()
        for form, count in forms.items():
            families[targets.family_of(form)] += count
        result[label] = {"total": sum(forms.values()), "families": dict(families), "forms": dict(forms),
                         **({"lines": dict(lines)} if label == "generated" else {}),
                         **({"not_reviewable": dict(not_reviewable)} if label == "imported" else {})}
    return result


def project(targets: CompositionTargets, library: dict, supply: dict, approval: float, *, slot: int = 2000,
            maximum_slots: int = 2000) -> dict:
    """Slots of the composition mix until every milestone is passed or the supply ends; the mix at each milestone."""
    counts = {family.name: int(library.get(family.name, 0)) for family in targets.families}
    remaining = {family.name: int(supply.get(family.name, 0)) for family in targets.families}
    reached, slots, approved_total = {}, 0, 0
    milestones = [milestone for milestone in targets.milestones if milestone > sum(counts.values())]
    while milestones and slots < maximum_slots:
        quotas = slot_quotas(targets, slot, counts, remaining)
        kept = {name: min(quotas[name], remaining[name]) for name in counts}
        if not any(kept.values()):
            break
        slots += 1
        for name, value in kept.items():
            remaining[name] -= value
            gained = int(round(value * approval))
            counts[name] += gained
            approved_total += gained
        total = sum(counts.values())
        while milestones and total >= milestones[0]:
            reached[str(milestones.pop(0))] = {"slots": slots, "library": total,
                                               "families": {name: {"count": value, "share": round(value / total, 4)}
                                                            for name, value in counts.items()}}
    total = sum(counts.values())
    return {"slot_size": slot, "approval_share": approval, "slots_run": slots, "reached": reached,
            "not_reached": [str(milestone) for milestone in milestones],
            "end": {"library": total, "families": {name: {"count": value, "share": round(value / total, 4)}
                                                   for name, value in counts.items()},
                    "supply_left": remaining}}


def needs(targets: CompositionTargets, library: dict, supply: dict, approval: float) -> dict:
    """Per milestone and family: approved packages the target mix asks for, candidates that takes, and the gap."""
    rows = {}
    for milestone in targets.milestones:
        goal = largest_remainder(targets.shares, milestone)
        rows[str(milestone)] = {}
        for family in targets.families:
            approved_needed = max(0, goal[family.name] - int(library.get(family.name, 0)))
            candidates = math.ceil(approved_needed / approval) if approval else None
            have = int(supply.get(family.name, 0))
            rows[str(milestone)][family.name] = {
                "target": goal[family.name], "bound": family.bound, "approved_needed": approved_needed,
                "candidates_needed": candidates, "supply": have,
                "gap": max(0, candidates - have) if candidates is not None else None}
    return rows


def build_report(store, targets: CompositionTargets, library: dict, *, review_batches: Path, daily: Path,
                 slot: int = 2000) -> dict:
    earlier = [folder for folder in sorted(Path(review_batches).glob("*")) if (folder / "export-report.json").is_file()]
    exported = exported_record_ids(earlier)
    supply = store_supply(store, targets, exported)
    approval = approval_share(daily)
    share = approval["share"] or 0.75
    combined = Counter(supply["imported"]["families"])
    combined.update(supply["generated"]["families"])
    return {"record_type": REPORT_RECORD_TYPE, "targets_digest": targets.digest, "goal": targets.goal,
            "milestones": list(targets.milestones), "library": library,
            "exported_to_review_already": len(exported), "supply": supply, "approval": approval,
            "projection": {"imported_only": project(targets, library["families"], supply["imported"]["families"],
                                                    share, slot=slot),
                           "with_generated": project(targets, library["families"], dict(combined), share, slot=slot)},
            "needs": {"imported_only": needs(targets, library["families"], supply["imported"]["families"], share),
                      "with_generated": needs(targets, library["families"], dict(combined), share)},
            "assumptions": [
                "Each slot draws the composition mix with supply-aware shares and refills nothing.",
                "Every family is approved at the same share, the mean of the daily slots so far.",
                "No new supply arrives; the imported supply is what the import store holds today.",
                "with_generated assumes a review profile for the supply lines' packages exists."]}
