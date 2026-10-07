"""Generate bounded discovery vocabularies from curated bases.

The owner asked for over a thousand dimensions, each with tens to hundreds of
options, across search engines, keywords, mechanisms, APIs and browsers. Doing
that by hand is unmaintainable and unreviewable. This module *generates* the
library from a small set of curated bases plus declarative derivation rules, so
the count grows by composition while every generated row still carries a
deterministic id, a source and a licence, and the whole library stays
digest-bound (a changed base changes the plan digest, which stops a silent
query drift).

Derivation rules are data:
- ``cross``: the cartesian product of two base dimensions' values, with a
  cap, a screen through the multiplier's ``words()`` and a dedup. Used for
  "role x task", "domain x format", "platform x change-type" families.
- ``template``: one base value rendered through a set of text templates
  ("top {v}", "{v} 2026", "best {v} for {role}").

Output is a `research_dimension_library/v1`-shaped fragment (a `dimensions`
list plus provenance) that is *merged* into `dimensions-v1.json`, never
written over the curated rows. The merged file is what the planner validates;
this generator's output cannot be loaded on its own.

Everything is deterministic and offline. No model, no network.
"""
from __future__ import annotations

import hashlib
import json
import re
import copy
from itertools import product
from string import Formatter
from dataclasses import dataclass

from knowledge_radar.query_matrix import words

#: Hard caps so a careless base edit cannot produce an unbounded library.
MAX_GENERATED_DIMENSIONS = 2000
MAX_VALUES_PER_DIMENSION = 400
MAX_CROSS_PAIRS = 400

_ID = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
_VALUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:+#-]{0,79}\Z")
GEN_SOURCE = {"title": "Baltor discovery-grid generated vocabulary (derived from curated bases, October 6, 2026)",
              "licence": "MIT", "note": "Derived by template/cross from curated Baltor-owned bases; no external table."}


class GenerationError(ValueError):
    pass


def _value_id(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "value"
    return slug


@dataclass(frozen=True)
class Family:
    """One base dimension of curated values, from which derived dimensions are made."""
    id: str
    kind: str
    title: str
    values: tuple  # of (id, text) pairs


def _mkdim(dim_id, title, kind, values, null_share=60):
    if not _ID.fullmatch(dim_id):
        raise GenerationError("dimension_id:" + dim_id)
    rows, seen, seen_text = [], set(), set()
    for vid, text, attrs in values:
        try:
            clean = words(text)
        except ValueError:
            raise GenerationError("dimension_value_refused") from None
        if not _VALUE_ID.match(vid):
            vid = _value_id(vid) + "-" + hashlib.sha256(vid.encode()).hexdigest()[:12]
        if clean in seen_text or len(rows) >= MAX_VALUES_PER_DIMENSION:
            continue
        if vid in seen:
            raise GenerationError("dimension_value_id_collision")
        seen.add(vid)
        seen_text.add(clean)
        rows.append({"id": vid, "text": clean, "weight": 1, "attributes": attrs})
    if not rows:
        raise GenerationError("dimension_empty:" + dim_id)
    return {"id": dim_id, "title": title, "kind": kind, "null_share": null_share, "source": GEN_SOURCE,
            "values": rows}


def cross(family_a: Family, family_b: Family, *, name: str, title: str, cap: int = MAX_CROSS_PAIRS) -> dict:
    """Cartesian product of two families' values into a new topic dimension."""
    if type(cap) is not int or not 1 <= cap <= MAX_CROSS_PAIRS:
        raise GenerationError("cross_cap_invalid")
    pairs = []
    for a_id, a_text in family_a.values:
        for b_id, b_text in family_b.values:
            if len(pairs) >= cap:
                break
            pairs.append((f"{a_id}_x_{b_id}", f"{a_text} {b_text}", {}))
    return _mkdim(name, title, "topic", pairs, null_share=50)


def template(family: Family, *, name: str, title: str, patterns: tuple, kind: str = "qualifier", bindings=None) -> dict:
    """Render one family through text templates, e.g. 'top {v}', '{v} 2026'."""
    rows = []
    bindings = bindings or {}
    for v_id, v_text in family.values:
        for index, pattern in enumerate(patterns):
            if len(rows) >= MAX_VALUES_PER_DIMENSION:
                break
            parsed = list(Formatter().parse(pattern))
            names = sorted({field for _, field, _, _ in parsed if field is not None and field != "v"})
            if (any(spec or conversion for _, _, spec, conversion in parsed)
                    or any(name not in bindings or not _ID.fullmatch(name) for name in names)):
                raise GenerationError("template_binding_missing_or_invalid")
            for chosen in product(*(bindings[name].values for name in names)):
                if len(rows) >= MAX_VALUES_PER_DIMENSION:
                    break
                values = {name: pair[1] for name, pair in zip(names, chosen)}
                identity = "_".join(name + "_" + pair[0] for name, pair in zip(names, chosen))
                text = pattern.format(v=v_text, **values)
                rows.append((f"{v_id}__t{index}_{identity}", text, {"derived_from": v_id}))
    return _mkdim(name, title, kind, rows, null_share=60)


def generate(program: dict) -> list:
    """Run a generation program and return a list of dimension dicts."""
    families = {fid: Family(fid, spec["kind"], spec["title"], tuple((v[0], v[1]) for v in spec["values"]))
                for fid, spec in (program.get("families") or {}).items()}
    out = []
    for step in program.get("derive", []):
        kind = step.get("op")
        if kind == "cross":
            a = families[step["a"]]; b = families[step["b"]]
            out.append(cross(a, b, name=step["name"], title=step["title"], cap=step.get("cap", MAX_CROSS_PAIRS)))
        elif kind == "template":
            base = families[step["family"]]
            out.append(template(base, name=step["name"], title=step["title"],
                                patterns=tuple(step["patterns"]), kind=step.get("kind", "qualifier"),
                                bindings={key: families[value] for key, value in step.get("bindings", {}).items()}))
        else:
            raise GenerationError("derive_op_unknown:" + str(kind))
        if len(out) > MAX_GENERATED_DIMENSIONS:
            raise GenerationError("generation_cap_exceeded")
      # dedup by id across the whole run
    seen, unique = set(), []
    for dim in out:
        if dim["id"] in seen:
            raise GenerationError("dimension_id_collision")
        seen.add(dim["id"])
        unique.append(dim)
    return unique


def merge(base_library: dict, generated: list) -> dict:
    """Append generated dimensions to the curated library; refuse a collision with a curated id."""
    base_library = copy.deepcopy(base_library)
    curated = {d["id"] for d in base_library["dimensions"]}
    if any(d["id"] in curated for d in generated):
        raise GenerationError("curated_dimension_collision")
    to_add = [d for d in generated if d["id"] not in curated]
    base_library["dimensions"].extend(to_add)
    base_library.setdefault("provenance", []).append(
        {"date": "2026-10-06", "by": "tools/query_multiplier/generate_dimensions.py",
         "change": f"Append {len(to_add)} generated dimensions from curated bases (template/cross), capped and screened."})
    return base_library
