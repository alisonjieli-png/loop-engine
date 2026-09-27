"""The library's composition targets and the supply-aware quotas one export draws from them.

The owner, September 27, 2026: "We need to increase our goal to 100K library
components, and a diverse well balanced library, not overweighted with
skills.md, we should have more functions, tools, programs, binaries, plugins,
etc". The served library then held 12,191 packages, 42 percent of them skills
and 26 percent instruction files, and the import store's supply was mostly the
same two kinds, so a mix of kind shares that spilled an exhausted kind's share
over to the others kept refilling the library with skills.

The targets are data (`src/loop_engine/data/library_composition.json`,
`library_composition_targets/v1`), so the weekly number, the daily counts and
this export read one record. Each family groups component forms
(`component_form/v1`) and has a share of the goal, bounded as a target or as a
cap:

```text
One export of S packages (the slot)
├── shares: the target shares, or, given the served library's counts, each family's remaining
│   need to the goal over the total need (supply-aware: the library reaches the target mix at
│   the goal); a capped family never draws more than its cap share of a slot
├── quota of a family: its share of S, whole packages by the largest remainder; knowing the
│   library's counts, a capped family also never takes the library above its cap share after
│   the slot, so a library short of other supply is not refilled with skills slot after slot
├── draw: families in a weighted round robin by quota, forms inside a family by their shares,
│   so any prefix of the selection keeps the mix
└── a family that lacks supply leaves its quota empty: the slot exports fewer packages; no
    other family, and never a capped one, refills it
```

Nothing here approves or serves anything; it only decides which candidates an
export hands to review, and records why.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from loop_engine.core.service_runtime.catalogue_attributes import (
    COMPONENT_FORM_VERSION, COMPONENT_FORMS, ComponentFormError, component_form_of, harness_kind_of,
    read_component_form)

TARGETS_RECORD_TYPE = "library_composition_targets/v1"
TARGETS_FILE = Path(__file__).resolve().parents[2] / "src" / "loop_engine" / "data" / "library_composition.json"
BOUNDS = ("target", "cap")
TARGET, CAP = BOUNDS
_FIELDS = {"record_type", "decided_on", "owner_direction", "component_form_vocabulary", "goal_components",
           "milestones", "bounds", "families"}
_FAMILY_FIELDS = {"family", "label", "share", "bound", "forms"}
#: Shares are written to two decimals; their sum may differ from one by rounding only.
_TOLERANCE = 1e-9


class CompositionError(ValueError):
    """A targets record that cannot be true, with a stable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


@dataclass(frozen=True)
class Family:
    name: str
    label: str
    share: float
    bound: str
    forms: tuple  # (form, share inside the family), in declared order


@dataclass(frozen=True)
class CompositionTargets:
    goal: int
    milestones: tuple
    families: tuple
    digest: str

    @property
    def shares(self) -> dict:
        return {family.name: family.share for family in self.families}

    def family(self, name: str) -> Family:
        for family in self.families:
            if family.name == name:
                return family
        raise KeyError(name)

    def family_of(self, form: str) -> str:
        for family in self.families:
            if any(name == form for name, _share in family.forms):
                return family.name
        raise CompositionError("component_form_without_family", f"{form!r} belongs to no family")

    def goal_counts(self, total: "int | None" = None) -> dict:
        """Packages per family at a library size (the goal by default), whole packages by the largest remainder."""
        return largest_remainder(self.shares, total if total is not None else self.goal)


def _share(value, name: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool) or not 0 < value <= 1:
        raise CompositionError("share_invalid", f"{name} is a fraction above 0 and at most 1")
    return float(value)


def read_targets(record: dict) -> CompositionTargets:
    """Typed targets, or a refusal of another version, a missing or unknown field, or shares that cannot hold."""
    found = record.get("record_type") if isinstance(record, dict) else None
    if found != TARGETS_RECORD_TYPE:
        raise CompositionError("targets_version_unsupported", f"expected {TARGETS_RECORD_TYPE}, found {found!r}")
    if set(record) != _FIELDS:
        raise CompositionError("targets_fields_invalid", f"the record names exactly {sorted(_FIELDS)}")
    if record["component_form_vocabulary"] != COMPONENT_FORM_VERSION:
        raise CompositionError("form_vocabulary_unsupported", f"the targets are written in {COMPONENT_FORM_VERSION}")
    goal = record["goal_components"]
    if type(goal) is not int or goal <= 0:
        raise CompositionError("goal_invalid", "the goal is a positive whole number of components")
    milestones = record["milestones"]
    if (not isinstance(milestones, list) or not milestones or any(type(value) is not int for value in milestones)
            or milestones != sorted(set(milestones)) or milestones[-1] != goal):
        raise CompositionError("milestones_invalid", "milestones rise strictly and end at the goal")
    if set(record["bounds"]) != set(BOUNDS):
        raise CompositionError("bounds_invalid", f"the bounds explained are {BOUNDS}")
    families, seen_forms, names = [], [], set()
    for row in record["families"]:
        if not isinstance(row, dict) or set(row) != _FAMILY_FIELDS:
            raise CompositionError("family_fields_invalid", f"a family names exactly {sorted(_FAMILY_FIELDS)}")
        if row["family"] in names:
            raise CompositionError("family_duplicate", row["family"])
        names.add(row["family"])
        if row["bound"] not in BOUNDS:
            raise CompositionError("bound_invalid", f"{row['family']}: a bound is one of {BOUNDS}")
        forms = row["forms"]
        if not isinstance(forms, dict) or not forms:
            raise CompositionError("family_forms_invalid", f"{row['family']} names its forms with their shares")
        for form, share in forms.items():
            if form not in COMPONENT_FORMS:
                raise CompositionError("component_form_unknown", f"{form!r} is not in {COMPONENT_FORM_VERSION}")
            _share(share, f"{row['family']}.{form}")
        if abs(sum(forms.values()) - 1) > 1e-6:
            raise CompositionError("family_form_shares_invalid", f"the form shares of {row['family']} sum to one")
        seen_forms += list(forms)
        families.append(Family(row["family"], str(row["label"]), _share(row["share"], row["family"]), row["bound"],
                               tuple(forms.items())))
    if sorted(seen_forms) != sorted(COMPONENT_FORMS):
        raise CompositionError("forms_not_covered_once", "every component form belongs to exactly one family")
    if abs(sum(family.share for family in families) - 1) > 1e-6:
        raise CompositionError("shares_do_not_sum_to_one", "the family shares sum to one")
    digest = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return CompositionTargets(goal, tuple(milestones), tuple(families), digest)


def load_targets(path: "Path | str" = TARGETS_FILE) -> CompositionTargets:
    return read_targets(json.loads(Path(path).read_text(encoding="utf-8")))


def largest_remainder(shares: dict, total: int) -> dict:
    """Whole counts in proportion to the shares that add up to the floor of the shares' sum times the total."""
    total_share = sum(shares.values())
    whole = math.floor(total_share * total + _TOLERANCE)
    exact = {name: share * total for name, share in shares.items()}
    counts = {name: math.floor(value + _TOLERANCE) for name, value in exact.items()}
    left = whole - sum(counts.values())
    for name in sorted(exact, key=lambda key: (-(exact[key] - counts[key]), key))[:max(0, left)]:
        counts[name] += 1
    return counts


def slot_shares(targets: CompositionTargets, library: "dict | None" = None) -> dict:
    """The share of one slot each family draws.

    Without the served library's counts these are the target shares. With them
    they are supply-aware: each family's remaining need to its goal count over
    the total remaining need, so a slot draws most from the families furthest
    behind and the library reaches the target mix at the goal. A capped family
    never draws more than its cap share of a slot, and nothing is renormalized
    after that bound: the slot is smaller instead."""
    shares = targets.shares
    if not library:
        return dict(shares)
    goal = targets.goal_counts()
    need = {name: max(0, goal[name] - int(library.get(name, 0))) for name in shares}
    total = sum(need.values())
    if total == 0:
        return {name: 0.0 for name in shares}
    result = {}
    for family in targets.families:
        share = need[family.name] / total
        result[family.name] = min(share, family.share) if family.bound == CAP else share
    return result


def bound_caps(targets: CompositionTargets, quotas: dict, library: dict, supply: "dict | None" = None) -> dict:
    """The quotas with each capped family bounded so the library stays at or under its cap after the slot.

    A per-slot cap alone lets a library whose other families lack supply fill up with the capped family: a slot
    of skills only is small, but it is all skills. So, knowing the library's counts, a capped family takes at
    most what keeps it under its cap share of the library as it will be after the slot (the other families'
    draws, limited by their supply, and the capped families' own). Solved by a rising fixed point."""
    drawn = {name: (min(quota, int(supply.get(name, 0))) if supply is not None else quota)
             for name, quota in quotas.items()}
    capped = [family for family in targets.families if family.bound == CAP]
    others = sum(drawn[family.name] for family in targets.families if family.bound != CAP)
    base = sum(int(library.get(family.name, 0)) for family in targets.families)
    taken = {family.name: 0 for family in capped}
    for _round in range(100):
        total = base + others + sum(taken.values())
        changed = False
        for family in capped:
            room = max(0, math.floor(family.share * total + _TOLERANCE) - int(library.get(family.name, 0)))
            value = min(drawn[family.name], room)
            if value != taken[family.name]:
                taken[family.name], changed = value, True
        if not changed:
            break
    return {**quotas, **taken}


def slot_quotas(targets: CompositionTargets, size: int, library: "dict | None" = None,
                supply: "dict | None" = None) -> dict:
    """Whole packages per family for a slot of this size; with the library's counts, capped families are bounded
    at the library level too."""
    quotas = largest_remainder(slot_shares(targets, library), size)
    return bound_caps(targets, quotas, library, supply) if library else quotas


def payload_form(payload: dict) -> str:
    """The component form of one stored candidate: its component_form/v1 record, else derived by rule."""
    kind = payload.get("kind", "")
    record = payload.get("component_form")
    if record is not None:
        return read_component_form(record, kind)
    roles = [entry.get("role", "") for entry in (payload.get("package") or {}).get("files", ())]
    return component_form_of(kind, roles, payload.get("native_format", ""))


def payload_family(payload: dict, targets: CompositionTargets) -> str:
    return targets.family_of(payload_form(payload))


def served_form(row: dict) -> str:
    """The component form of one served item (a release bundle row or a combined catalogue row).

    The harness kind is derived the way the library page derives it (the declared kind, else the styles, else
    the served kind; library_page.py passes no file roles), so these counts match what a customer sees; the
    file roles then refine the form (a skill that holds a script)."""
    attributes = row.get("attributes") or {}
    reference = row.get("reference") or {}
    styles = tuple(reference.get("styles") or ())
    roles = tuple(entry.get("role", "") for entry in (row.get("package") or {}).get("files", ())) or tuple(
        entry.get("role", "") for entry in row.get("package_files", ()))
    declared_kind = attributes.get("harness_kind") or (row.get("provenance") or {}).get("harness_kind") or ""
    kind = harness_kind_of(reference.get("kind", ""), styles, (), declared_kind)
    form = attributes.get("component_form", "")
    if form:
        try:
            return component_form_of(kind, roles, "", form)
        except ComponentFormError:
            pass
    native = styles[1] if len(styles) >= 2 and styles[0] == kind else ""
    return component_form_of(kind, roles, native)


def library_counts(bundle: "Path | str", targets: CompositionTargets) -> dict:
    """Served packages per family and per form, read from a release bundle folder's items.jsonl."""
    path = Path(bundle)
    path = path / "items.jsonl" if path.is_dir() else path
    forms = Counter()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                forms[served_form(json.loads(line))] += 1
    families = Counter()
    for form, count in forms.items():
        families[targets.family_of(form)] += count
    return {"total": sum(forms.values()), "families": dict(families), "forms": dict(forms)}


def composition(counts_by_form: dict, targets: CompositionTargets) -> dict:
    """Per family: the count, its share of the total and the target share, for a report."""
    families = defaultdict(int)
    for form, count in counts_by_form.items():
        families[targets.family_of(form)] += count
    total = sum(families.values())
    return {family.name: {"count": families.get(family.name, 0),
                          "share": round(families.get(family.name, 0) / total, 4) if total else 0.0,
                          "target_share": family.share, "bound": family.bound} for family in targets.families}
